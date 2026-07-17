#!/usr/bin/env python3
"""会话外里程碑监督器（P1 §十五）。

职责仅限：读磁盘状态 → 复算前序 typed 结果 → 验八件套 → 验审核签字 →
算 Y 图 ready-set → 渲染 Prompt → 建启动记录 → 以全新顶层 Fable 5 会话
启动下一里程碑 → 登记实际模型/会话/摘要/退出状态；上一会话结束后才启动。

不得：改验收标准；把 REVIEW_READY 改成 PASS；伪造审核回执；上一会话活跃时
启动；把子代理当新顶层会话；绕过路线约束；自动处理停止线；发布/部署/merge。

若无法创建真正独立的顶层会话：不用子代理代替、不伪造 session ID；
写 READY_TO_START 工件 + 可复制冻结 Prompt + AUTO_LAUNCH_CAPABILITY_UNAVAILABLE。

用法：
  launcher.py --status | --compute-ready-set | --render M2 [--out F]
  launcher.py --dry-run M2 | --start M2 | --resume-from-journal | --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DC = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = DC.parents[3]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = _load(DC / "tools/receipts.py", "p7_receipts_launcher")
ready_set_mod = _load(DC / "tools/ready_set.py", "p7_ready_set_launcher")
closeout_mod = _load(DC / "tools/closeout.py", "p7_closeout_launcher")
renderer_mod = _load(DC / "tools/renderer.py", "p7_renderer_launcher")
journal_mod = _load(DC / "tools/run_journal.py", "p7_journal_launcher")


class LaunchRefused(RuntimeError):
    pass


def _registry(dc: Path) -> dict:
    return json.loads((dc / "PROMPT_REGISTRY.v1.json").read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, text: str) -> None:
    """原子落盘协议（指令第 6 条）：同目录 tmp + fsync + rename + 目录 fsync。"""
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
    dir_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _git_head(root: Path) -> str | None:
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    head = proc.stdout.strip()
    return head if proc.returncode == 0 and len(head) == 40 else None


def in_claude_session(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("CLAUDE_CODE_SESSION_ID") or env.get("CLAUDECODE"))


def previous_session_exited(root: Path, dc: Path, predecessor: str) -> tuple[bool, str]:
    """上一会话退出证据：journal 头记录非 ACTIVE + 前序关闭回执在盘。"""
    state = journal_mod.parse_journal(dc / "journal/RUN_JOURNAL.v1.jsonl")
    if state["status"] != "VALID" or not state["records"]:
        return False, f"journal not VALID ({state['status']})"
    head = state["records"][-1]
    if str(head.get("state", "")).upper() == "ACTIVE":
        return False, (f"journal head still ACTIVE (capsule={head.get('capsule')}) "
                       "-> previous session may be live")
    receipt_path = receipts.resolve_versioned(
        dc / "milestones" / predecessor, "CLOSEOUT_RECEIPT")
    if not receipt_path.is_file():
        return False, f"{predecessor} closeout receipt absent"
    return True, f"journal head state={head.get('state')}, closeout present"


def validate_entry(root: Path, milestone: str, dc: Path | None = None,
                   env: dict | None = None,
                   author_session_ids: set[str] | None = None) -> dict:
    """--dry-run 的核心：全部入口机械校验；任何一条不满足 → LaunchRefused。"""
    dc = dc or DC
    registry = _registry(dc)
    entry = next((row for row in registry["prompts"]
                  if row["milestone_id"] == milestone), None)
    if entry is None:
        raise LaunchRefused(f"unknown milestone {milestone}")
    if milestone == "M1":
        raise LaunchRefused("M1 launches via founder P1 record, not supervisor")
    predecessor = entry["predecessor_milestone"]
    checks: list[str] = []

    # 1. 同会话拒绝：监督器必须在会话外运行
    if in_claude_session(env):
        raise LaunchRefused(
            "supervisor invoked from inside a Claude session "
            "(CLAUDE_CODE_SESSION_ID/CLAUDECODE present); same-session "
            "cross-milestone continuation is a stop line")
    checks.append("OK not_inside_claude_session")

    # 2. 上一会话已退出
    exited, why = previous_session_exited(root, dc, predecessor)
    if not exited:
        raise LaunchRefused(f"previous session not proven exited: {why}")
    checks.append(f"OK previous_session_exited ({why})")

    # 3. 前序八件套
    ok, details = closeout_mod.validate_eight_pieces(
        root, dc / "milestones" / predecessor)
    if not ok:
        raise LaunchRefused(f"{predecessor} eight-piece closeout invalid: "
                            + "; ".join(d for d in details if "OK" not in d)[:300])
    checks.append(f"OK {predecessor}_eight_pieces")

    # 4. 前序 typed 回执 + 两份独立签字
    try:
        receipt = receipts.milestone_result(root, predecessor,
                                            milestones_dir=dc / "milestones")
    except receipts.ReceiptError as exc:
        raise LaunchRefused(f"{predecessor} typed receipt invalid: {exc}")
    if receipt is None:
        raise LaunchRefused(f"{predecessor} typed receipt absent")
    bindings = receipt.get("review_bindings", [])
    if receipt.get("result") == "PASS":
        if len(bindings) < 2 or len({b.get("reviewer_kind")
                                     for b in bindings}) < 2:
            raise LaunchRefused(
                f"{predecessor} PASS lacks two independent review signatures")
        for binding in bindings:
            rp = root / str(binding.get("receipt_path", ""))
            if not rp.is_file():
                raise LaunchRefused(f"review receipt missing: {binding.get('receipt_path')}")
            digest = hashlib.sha256(rp.read_bytes()).hexdigest()
            if digest != binding.get("receipt_digest"):
                raise LaunchRefused(f"review receipt digest mismatch: {rp.name}")
            if author_session_ids:
                signer = json.loads(rp.read_text(encoding="utf-8"))
                sid = signer.get("task_thread_session_id")
                if isinstance(sid, str) and sid in author_session_ids:
                    raise LaunchRefused(
                        f"reviewer session equals author session ({rp.name}): "
                        "author may not sign own work")
    checks.append(f"OK {predecessor}_typed_receipt_and_signatures")

    # 5. Y 图 ready-set（按值匹配，含路线约束；禁编号串行）
    rs = ready_set_mod.compute_ready_set(root, milestones_dir=dc / "milestones")
    node = rs.get(milestone, {})
    if not node.get("ready"):
        raise LaunchRefused(f"{milestone} not in ready-set: "
                            + "; ".join(node.get("reasons", []))[:300])
    checks.append(f"OK ready_set[{milestone}]")

    return {"milestone": milestone, "entry": entry, "receipt": receipt,
            "ready_set": rs, "checks": checks}


def verify_launch_binding(root: Path, milestone: str,
                          dc: Path | None = None) -> list[str]:
    """启动记录的事后核验（HEAD 绑定不自证的补全面）：

    ①validate_launch_record(repo_root=…)——提交存在 + 分支祖先关系；
    ②哈希链 journal 交叉绑定——链内 LAUNCH_<M> 记录的独立采集 git_head
      必须逐字等于记录的 launched_at_head，且登记同一 record_digest。
    伪造 launched_at_head 为任何其他真实提交都会与链内 git_head 失配。"""
    dc = dc or DC
    record_path = dc / "milestones" / milestone / "LAUNCH_RECORD.v2.json"
    if not record_path.is_file():
        return [f"launch record missing: {record_path}"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    errors = receipts.validate_launch_record(record, repo_root=root)
    state = journal_mod.parse_journal(dc / "journal/RUN_JOURNAL.v1.jsonl")
    if state["status"] != "VALID":
        return errors + [f"journal not VALID ({state['status']}) -> "
                         "launch binding unverifiable"]
    matches = [rec for rec in state["records"]
               if rec.get("launch_record_digest") == record.get("record_digest")
               and rec.get("capsule") == f"LAUNCH_{milestone}"]
    if not matches:
        errors.append("launch record not registered in hash-chained journal "
                      "(pre-spawn registration missing or digest mismatch)")
    else:
        chained = matches[-1]
        if chained.get("git_head") != record.get("launched_at_head"):
            errors.append(
                f"journal-chained git_head {str(chained.get('git_head'))[:12]}"
                f" != record launched_at_head "
                f"{str(record.get('launched_at_head'))[:12]} "
                "(forged HEAD binding)")
    return errors


def spawn_via_claude_cli(rendered_path: Path, model: str = "fable") -> dict:
    """默认 spawn：claude CLI 全新顶层会话。返回会话身份回执（best-effort）。"""
    if shutil.which("claude") is None:
        return {"capability": "AUTO_LAUNCH_CAPABILITY_UNAVAILABLE",
                "reason": "claude CLI not on PATH"}
    env = dict(os.environ)
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    result = subprocess.run(
        ["claude", "-p", "--model", model, "--output-format", "json"],
        stdin=open(rendered_path, "rb"), capture_output=True, text=True,
        env=env)
    session_id: object = {"value": "UNAVAILABLE",
                          "unavailable_reason": "claude CLI output not parseable",
                          "evidence_ref": "launcher stdout capture"}
    actual_model = "UNKNOWN_SEE_SESSION_IDENTITY"
    try:
        payload = json.loads(result.stdout)
        session_id = payload.get("session_id") or session_id
        actual_model = payload.get("model") or actual_model
    except ValueError:
        pass
    return {"capability": "AUTO_LAUNCHED", "session_id": session_id,
            "session_kind": "TOP_LEVEL_FRESH", "actual_model": actual_model,
            "exit_status": result.returncode,
            "auto_memory_disabled": True}


def start(root: Path, milestone: str, dc: Path | None = None,
          env: dict | None = None, spawn=spawn_via_claude_cli,
          author_session_ids: set[str] | None = None) -> dict:
    """启动流程（指令第 6 条重设计）：

    校验入口 → 渲染 Prompt → 绑定实际 HEAD → LAUNCH_RECORD.v2 原子落盘
    （先于任何 spawn 动作）→ spawn → LAUNCH_OUTCOME.v1 落盘（回绑记录摘要）。
    子代理伪装 / 会话复用在 outcome 中登记 REFUSED_* 后拒绝。"""
    dc = dc or DC
    context = validate_entry(root, milestone, dc=dc, env=env,
                             author_session_ids=author_session_ids)
    entry = context["entry"]
    registry = _registry(dc)
    bindings = renderer_mod.build_bindings(root, milestone, registry,
                                           milestones_dir=dc / "milestones")
    rendered = renderer_mod.render(dc / entry["template_path"], bindings)
    out_dir = dc / "milestones" / milestone
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered_path = out_dir / "RENDERED_PROMPT.v1.md"
    _atomic_write(rendered_path, rendered["text"])

    head = _git_head(root)
    if head is None:
        raise LaunchRefused("workspace HEAD unresolvable; launch record "
                            "must bind the actual HEAD (no repo, no launch)")

    record = {
        "schema_version": "p7-launch-record-v2",
        "prompt_id": entry["prompt_id"],
        "milestone_id": milestone,
        "workspace": str(root),
        "input_commit": bindings["INPUT_COMMIT"],
        "launched_at_head": head,
        "rendered_prompt_path": str(rendered_path.relative_to(root))
            if rendered_path.is_relative_to(root) else str(rendered_path),
        "rendered_prompt_digest": rendered["rendered_digest"],
        "template_digest": rendered["template_digest"],
        "predecessor_receipt_digest": context["receipt"]["receipt_digest"],
        "handoff_digest": bindings["HANDOFF_DIGEST"],
        "route_binding": (bindings["ROUTE"]
                          if bindings["ROUTE"] in ("a", "b") else None),
        "write_surface_allowlist": entry["write_surface_allowlist"],
        "write_surface_denylist": entry["write_surface_denylist"],
        "allowed_git_actions": entry["allowed_git_actions"],
        "allowed_repo_and_remote_creation": entry.get(
            "allowed_repo_and_remote_creation", []),
        "allowed_models_and_materials": [
            entry["roles_and_models"]["principal"],
            "matrix: " + entry["roles_and_models"]["matrix"]],
        "session_kind": "TOP_LEVEL_FRESH",
        "requested_model": "fable (Fable 5)",
        "auto_memory_disabled": True,
        "auto_memory_disabled_before_spawn": True,
        "record_written_before_spawn": True,
        "write_protocol": "ATOMIC_WRITE_TMP_FSYNC_RENAME",
        "launched_by": "SESSION_EXTERNAL_SUPERVISOR",
        "launched_at": _now(),
        "previous_session_exited_evidence": context["checks"][1],
        "record_digest": "",
    }
    record = receipts.close_record(record, "record_digest")
    # HEAD 绑定三重锚（Codex R4 BLOCKING 修复）：
    # ①启动现场逐字比对 expected_head；②对仓库复核存在性与祖先关系
    errors = receipts.validate_launch_record(record, repo_root=root,
                                             expected_head=head)
    if errors:
        raise LaunchRefused(f"launch record invalid: {errors}")
    record_path = out_dir / "LAUNCH_RECORD.v2.json"
    # 指令第 6 条：记录先于 spawn 原子落盘
    _atomic_write(record_path, json.dumps(record, ensure_ascii=False,
                                          indent=2) + "\n")
    # ③spawn 前把记录摘要交叉登记进哈希链 journal：git_head 由 journal 独立
    # 采集，事后改写 launched_at_head（即便重算 record_digest）也会与链内
    # git_head 失配 → verify_launch_binding 拒绝
    journal_mod.append_record(dc / "journal/RUN_JOURNAL.v1.jsonl", {
        "session_id": "SESSION_EXTERNAL_SUPERVISOR",
        "run_id": {"value": "UNAVAILABLE",
                   "unavailable_reason": "supervisor process, not a session",
                   "evidence_ref": str(record_path)},
        "input_commit": bindings["INPUT_COMMIT"],
        "dirty_tree_digest": journal_mod.git_facts(str(root))[
            "dirty_tree_digest"],
        "capsule": f"LAUNCH_{milestone}",
        "state": "LAUNCH_RECORDED",
        "requested_model": "fable",
        "actual_model": "PENDING_SPAWN",
        "subagent_ids": [],
        "last_green_commit": bindings["INPUT_COMMIT"],
        "verification_state": "ENTRY_VALIDATED",
        "next_action": f"spawn {milestone} fresh top-level session",
        "stop_reason": None,
        "launch_record_digest": record["record_digest"],
    }, str(root))

    spawn_result = spawn(rendered_path)
    capability = spawn_result.get("capability")
    refusal: tuple[str, str] | None = None
    if capability == "AUTO_LAUNCHED":
        if spawn_result.get("session_kind") != "TOP_LEVEL_FRESH":
            refusal = ("REFUSED_SUBAGENT_IMPERSONATION",
                       f"spawn returned session_kind="
                       f"{spawn_result.get('session_kind')} — subagent "
                       "impersonation of a top-level session is forbidden")
        elif (author_session_ids
              and isinstance(spawn_result.get("session_id"), str)
              and spawn_result["session_id"] in author_session_ids):
            refusal = ("REFUSED_SESSION_REUSE",
                       "spawned session id equals author session id "
                       "(reuse forbidden)")

    outcome = {
        "schema_version": "p7-launch-outcome-v1",
        "milestone_id": milestone,
        "launch_record_digest": record["record_digest"],
        "launch_capability": (refusal[0] if refusal else
                              capability or
                              "AUTO_LAUNCH_CAPABILITY_UNAVAILABLE"),
        "session_id": spawn_result.get("session_id") or {
            "value": "UNAVAILABLE",
            "unavailable_reason": f"capability={capability}",
            "evidence_ref": "launcher spawn result"},
        "session_kind": spawn_result.get("session_kind", "NOT_APPLICABLE"),
        "actual_model": str(spawn_result.get(
            "actual_model", "PENDING_SESSION_IDENTITY_RECEIPT")),
        "exit_status": spawn_result.get("exit_status"),
        "auto_memory_disabled": True,
        "completed_at": _now(),
        "outcome_digest": "",
    }
    if refusal:
        outcome["refusal_reason"] = refusal[1]
    outcome = receipts.close_record(outcome, "outcome_digest")
    _atomic_write(out_dir / "LAUNCH_OUTCOME.v1.json",
                  json.dumps(outcome, ensure_ascii=False, indent=2) + "\n")
    if refusal:
        raise LaunchRefused(refusal[1])
    outcome_errors = receipts.validate_launch_outcome(outcome, record)
    if outcome_errors:
        raise LaunchRefused(f"launch outcome invalid: {outcome_errors}")

    if capability != "AUTO_LAUNCHED":
        _atomic_write(out_dir / "READY_TO_START.v1.json", json.dumps({
            "milestone": milestone,
            "status": "READY_TO_START",
            "launch_capability": "AUTO_LAUNCH_CAPABILITY_UNAVAILABLE",
            "reason": spawn_result.get("reason", "unknown"),
            "frozen_prompt_path": record["rendered_prompt_path"],
            "frozen_prompt_digest": rendered["rendered_digest"],
            "instruction": "复制冻结 Prompt 到全新 Fable 5 顶层会话手动启动",
        }, ensure_ascii=False, indent=2) + "\n")
    return {"record": record, "outcome": outcome, "spawn": spawn_result}


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    import tempfile
    failures: list[str] = []

    def expect(name: str, cond: bool) -> None:
        print(f"[{'ok' if cond else 'FAIL'}] launcher_selftest:{name}")
        if not cond:
            failures.append(name)

    sys.path.insert(0, str(DC / "tests"))
    try:
        import fixture_helpers as fh
    finally:
        sys.path.pop(0)

    def _git(cwd: Path, *args: str) -> str:
        proc = subprocess.run(["git", *args], cwd=str(cwd),
                              capture_output=True, text=True)
        assert proc.returncode == 0, (args, proc.stderr)
        return proc.stdout.strip()

    make_fixture = fh.build_launch_fixture

    def spawn_ok_factory(dc: Path, seen: dict):
        def fake_spawn_ok(path: Path) -> dict:
            # 指令第 6 条的顺序证明：spawn 时启动记录必须已在盘
            seen["record_on_disk_before_spawn"] = (
                dc / "milestones/M2/LAUNCH_RECORD.v2.json").is_file()
            return {"capability": "AUTO_LAUNCHED",
                    "session_id": "fresh-new-session-0001",
                    "session_kind": "TOP_LEVEL_FRESH",
                    "actual_model": "claude-fable-5",
                    "exit_status": 0, "auto_memory_disabled": True}
        return fake_spawn_ok

    fake_spawn_subagent = lambda path: {
        "capability": "AUTO_LAUNCHED", "session_id": "subagent-77",
        "session_kind": "SUBAGENT", "actual_model": "claude-fable-5",
        "exit_status": 0, "auto_memory_disabled": True}
    fake_spawn_unavailable = lambda path: {
        "capability": "AUTO_LAUNCH_CAPABILITY_UNAVAILABLE",
        "reason": "no claude CLI in test"}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        dc = make_fixture(tmp_root)
        head = _git(tmp_root, "rev-parse", "HEAD")
        # 正常启动（外部环境 + 新会话身份）
        seen: dict = {}
        result = start(tmp_root, "M2", dc=dc, env={},
                       spawn=spawn_ok_factory(dc, seen),
                       author_session_ids={"author-session-M1"})
        record, outcome = result["record"], result["outcome"]
        expect("record_written_before_spawn",
               seen.get("record_on_disk_before_spawn") is True)
        expect("record_bound_to_actual_head",
               record["launched_at_head"] == head)
        expect("fresh_session_identity_in_outcome",
               outcome["session_id"] == "fresh-new-session-0001"
               and outcome["session_kind"] == "TOP_LEVEL_FRESH"
               and outcome["launch_capability"] == "AUTO_LAUNCHED")
        expect("outcome_bound_to_record",
               outcome["launch_record_digest"] == record["record_digest"]
               and not receipts.validate_launch_outcome(outcome, record))
        expect("launch_record_schema_valid",
               not receipts.validate_launch_record(record))
        expect("rendered_prompt_digest_bound",
               len(record["rendered_prompt_digest"]) == 64)

        # 篡改 HEAD 绑定 → 记录摘要复算失败
        forged = dict(record)
        forged["launched_at_head"] = "0" * 40
        expect("forged_head_binding_rejected",
               bool(receipts.validate_launch_record(forged)))
        # 重算摘要的伪造（Codex R4 BLOCKING 攻击重放）→ 仓库态复核拒绝
        reclosed = receipts.close_record(
            {k: v for k, v in forged.items() if k != "record_digest"}
            | {"record_digest": ""}, "record_digest")
        expect("reclosed_forged_head_rejected_by_repo_check",
               any("unknown to repository" in e for e in
                   receipts.validate_launch_record(reclosed,
                                                   repo_root=tmp_root)))
        # 事后核验：哈希链 journal 交叉绑定通过（正常记录）
        expect("launch_binding_journal_verified",
               not verify_launch_binding(tmp_root, "M2", dc=dc))

        # 同会话启动拒绝
        try:
            validate_entry(tmp_root, "M2", dc=dc,
                           env={"CLAUDE_CODE_SESSION_ID": "author-session-M1"})
            expect("same_session_refused", False)
        except LaunchRefused as exc:
            expect("same_session_refused", "same-session" in str(exc))

        # 子代理伪装拒绝 + 结果文件登记 REFUSED
        try:
            start(tmp_root, "M2", dc=dc, env={}, spawn=fake_spawn_subagent)
            expect("subagent_impersonation_refused", False)
        except LaunchRefused as exc:
            outcome_file = json.loads(
                (dc / "milestones/M2/LAUNCH_OUTCOME.v1.json").read_text(
                    encoding="utf-8"))
            expect("subagent_impersonation_refused",
                   "impersonation" in str(exc)
                   and outcome_file["launch_capability"]
                   == "REFUSED_SUBAGENT_IMPERSONATION")

        # spawn 能力不可用 → READY_TO_START + 诚实登记
        result = start(tmp_root, "M2", dc=dc, env={},
                       spawn=fake_spawn_unavailable)
        expect("honest_ready_to_start",
               result["outcome"]["launch_capability"]
               == "AUTO_LAUNCH_CAPABILITY_UNAVAILABLE"
               and (dc / "milestones/M2/READY_TO_START.v1.json").is_file())

        # 伪造 launched_at_head 为另一真实提交 + 重算摘要
        # → 仓库态复核无法拦（提交真实存在），必须被 journal 交叉绑定拒绝
        (tmp_root / "later.txt").write_text("later", encoding="utf-8")
        _git(tmp_root, "add", "-A")
        _git(tmp_root, "commit", "-qm", "later")
        later_head = _git(tmp_root, "rev-parse", "HEAD")
        record_path = dc / "milestones/M2/LAUNCH_RECORD.v2.json"
        current = json.loads(record_path.read_text(encoding="utf-8"))
        forged_real = receipts.close_record(
            {k: v for k, v in current.items() if k != "record_digest"}
            | {"launched_at_head": later_head, "record_digest": ""},
            "record_digest")
        record_path.write_text(json.dumps(forged_real, ensure_ascii=False,
                                          indent=2) + "\n", encoding="utf-8")
        binding_errors = verify_launch_binding(tmp_root, "M2", dc=dc)
        expect("forged_real_head_rejected_by_journal_chain",
               any("journal" in e or "git_head" in e
                   for e in binding_errors))

    with tempfile.TemporaryDirectory() as tmp:
        # 不合格前序（FAIL）拒绝
        tmp_root = Path(tmp)
        dc = make_fixture(tmp_root, predecessor_result="FAIL")
        try:
            validate_entry(tmp_root, "M2", dc=dc, env={})
            expect("unqualified_predecessor_refused", False)
        except LaunchRefused:
            expect("unqualified_predecessor_refused", True)

    with tempfile.TemporaryDirectory() as tmp:
        # 缺审核签字拒绝
        tmp_root = Path(tmp)
        dc = make_fixture(tmp_root, with_reviews=False)
        try:
            validate_entry(tmp_root, "M2", dc=dc, env={})
            expect("missing_signatures_refused", False)
        except LaunchRefused as exc:
            # PASS 且零签字在 typed schema 层即无效 → 八件套或签字环节均可拦截
            expect("missing_signatures_refused", True)
            print(f"    refused: {str(exc)[:120]}")

    with tempfile.TemporaryDirectory() as tmp:
        # 上一会话仍活跃拒绝
        tmp_root = Path(tmp)
        dc = make_fixture(tmp_root, journal_state="ACTIVE")
        try:
            validate_entry(tmp_root, "M2", dc=dc, env={})
            expect("live_previous_session_refused", False)
        except LaunchRefused as exc:
            expect("live_previous_session_refused", "ACTIVE" in str(exc)
                   or "exited" in str(exc))

    with tempfile.TemporaryDirectory() as tmp:
        # Y 分叉：M2 后按编号启动 M4 必须拒绝（ready-set 不含 M4）
        tmp_root = Path(tmp)
        dc = make_fixture(tmp_root)
        # 回执移植伪造：把 M1 关闭目录整体复制为 M2 → 必须被 milestone_id 匹配拒绝
        shutil.copytree(dc / "milestones/M1", dc / "milestones/M2")
        try:
            validate_entry(tmp_root, "M3", dc=dc, env={})
            expect("transplanted_receipt_refused", False)
        except LaunchRefused as exc:
            expect("transplanted_receipt_refused",
                   "transplant" in str(exc) or "invalid" in str(exc))
        # 按编号串行启动 M4（M3 从未关闭）→ 必须拒绝
        try:
            validate_entry(tmp_root, "M4", dc=dc, env={})
            expect("numbered_serialism_refused_m4", False)
        except LaunchRefused:
            expect("numbered_serialism_refused_m4", True)
        # 路线未冻结 → M6 拒绝
        try:
            validate_entry(tmp_root, "M6", dc=dc, env={})
            expect("route_unfrozen_m6_refused", False)
        except LaunchRefused:
            expect("route_unfrozen_m6_refused", True)

    print("LAUNCHER_SELFTEST:", "ALL_PASS" if not failures
          else f"FAILED {failures}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--compute-ready-set", action="store_true")
    ap.add_argument("--render", metavar="M")
    ap.add_argument("--dry-run", metavar="M")
    ap.add_argument("--start", metavar="M")
    ap.add_argument("--resume-from-journal", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    root = Path(args.root)
    if args.selftest:
        return selftest()
    if args.status:
        registry = _registry(DC)
        rs = ready_set_mod.compute_ready_set(root)
        print(json.dumps({
            "prompts": {row["prompt_id"]: row["status"]
                        for row in registry["prompts"]},
            "ready_set": {m: v for m, v in rs.items()
                          if not m.startswith("_")},
            "route": rs.get("_route")}, ensure_ascii=False, indent=2))
        return 0
    if args.compute_ready_set:
        print(json.dumps(ready_set_mod.compute_ready_set(root),
                         ensure_ascii=False, indent=2))
        return 0
    if args.resume_from_journal:
        state = journal_mod.parse_journal(DC / "journal/RUN_JOURNAL.v1.jsonl")
        head = state["records"][-1] if state["records"] else None
        print(json.dumps({"journal_status": state["status"],
                          "resume_point": head}, ensure_ascii=False, indent=2))
        return 0 if state["status"] == "VALID" else 1
    try:
        if args.dry_run:
            context = validate_entry(root, args.dry_run)
            print(json.dumps({"dry_run": args.dry_run, "would_launch": True,
                              "checks": context["checks"]},
                             ensure_ascii=False, indent=2))
            return 0
        if args.render:
            registry = _registry(DC)
            bindings = renderer_mod.build_bindings(root, args.render, registry)
            entry = next(row for row in registry["prompts"]
                         if row["milestone_id"] == args.render)
            rendered = renderer_mod.render(DC / entry["template_path"], bindings)
            if args.out:
                Path(args.out).write_text(rendered["text"], encoding="utf-8")
            print(json.dumps({"rendered_digest": rendered["rendered_digest"],
                              "template_digest": rendered["template_digest"]},
                             ensure_ascii=False, indent=2))
            return 0
        if args.start:
            result = start(root, args.start)
            print(json.dumps(result["record"], ensure_ascii=False, indent=2))
            return 0
    except (LaunchRefused, receipts.ReceiptError) as exc:
        print(json.dumps({"refused": True, "reason": str(exc)},
                         ensure_ascii=False, indent=2))
        return 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
