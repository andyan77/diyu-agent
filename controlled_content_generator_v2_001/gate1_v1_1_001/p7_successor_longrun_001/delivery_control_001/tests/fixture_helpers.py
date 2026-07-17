"""攻击矩阵 / launcher / closure 测试共用的合成里程碑关闭 fixture（v2 原生）。

v2 fixture 产出：signer 回执 v2（绑 milestone/产品域/三 manifest）、
HANDOFF v2（全引用可复算）、MILESTONE_EXIT_EVIDENCE、READY_SET_RESULT、
ORIGIN_ANCHOR v2（供 renderer 绑定 CONTROL_PLANE_COMMIT）。
typed 回执沿用 v1 schema（未变更）。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
DC_REL = str(DC.relative_to(DC.parents[3]))

M1_EXIT_KEYS = (
    "INDEPENDENT_CLAUDE_FABLE_REVIEW_ACCEPT",
    "CODEX_GPT_REVIEW_ACCEPT",
    "D0_TEXT_AND_INDEPENDENT_REVIEW_VALID",
    "M0_REMAINS_HONESTLY_NOT_QUALIFIED",
    "V1_1_REMAINS_HONESTLY_NOT_QUALIFIED",
    "RUN_JOURNAL_CHAIN_VALID",
    "FULL_TEST_SUITE_GREEN",
    "REPOSITORY_WIDE_RESIDUAL_SCAN_PASS",
)


def load_tool(name: str):
    spec = importlib.util.spec_from_file_location(
        f"p7_fixture_{name}", DC / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = load_tool("receipts")
journal_mod = load_tool("run_journal")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_init_commit(tmp: Path) -> str:
    """把 tmp 变成含单提交的 git 仓；返回该提交 SHA。"""
    for args in (["git", "init", "-q", "-b", "main"],
                 ["git", "config", "user.email", "t@t"],
                 ["git", "config", "user.name", "t"],
                 ["git", "add", "-A"],
                 ["git", "commit", "-qm", "fixture"]):
        proc = subprocess.run(args, cwd=str(tmp), capture_output=True,
                              text=True)
        assert proc.returncode == 0, (args, proc.stderr)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tmp),
                          capture_output=True, text=True).stdout.strip()


def build_launch_fixture(tmp: Path, **kwargs) -> Path:
    """launcher 测试用 fixture：候选=真实首提交（launch 的 HEAD/祖先校验需要）。"""
    (tmp / "seed.txt").write_text("seed\n", encoding="utf-8")
    candidate = git_init_commit(tmp)
    dc = build_m1_closeout_fixture(tmp, candidate_commit=candidate, **kwargs)
    for args in (["git", "add", "-A"], ["git", "commit", "-qm", "fixture"]):
        proc = subprocess.run(args, cwd=str(tmp), capture_output=True,
                              text=True)
        assert proc.returncode == 0, (args, proc.stderr)
    return dc


def build_final_fixture(tmp: Path, **kwargs) -> tuple[Path, str]:
    """FINAL 检查用完整 fixture：真实 git 仓 + DC_REL 布局 + 全绑定 v2 工件。

    candidate = 首个提交；关闭工件在第二个提交（模拟关闭晚于候选）。"""
    (tmp / "impl.py").write_text("x = 1\n", encoding="utf-8")
    candidate = git_init_commit(tmp)
    dc = build_m1_closeout_fixture(tmp, candidate_commit=candidate,
                                   dc_rel=DC_REL, full=True, **kwargs)
    for args in (["git", "add", "-A"], ["git", "commit", "-qm", "closeout"]):
        proc = subprocess.run(args, cwd=str(tmp), capture_output=True,
                              text=True)
        assert proc.returncode == 0, (args, proc.stderr)
    return dc, candidate


def build_m1_closeout_fixture(tmp: Path, *, predecessor_result: str = "PASS",
                              with_reviews: bool = True,
                              journal_state: str = "CLOSED_PASS",
                              flags: dict | None = None,
                              candidate_commit: str | None = None,
                              dc_rel: str = "delivery_control_001",
                              signer_schema: str = "v2",
                              signer_overrides: dict | None = None,
                              full: bool = False) -> Path:
    """构造带完整八件套 + 出口证据 + journal 的合成控制面；返回 dc 目录。

    full=True 时 HANDOFF v2 的每个摘要字段都与 fixture 内文件真实一致
    （contract set 冻结、模板摘要、ready-set 摘要、出口证据摘要），
    可通过 closure.validate_handoff_full 的全引用复算。
    """
    candidate = candidate_commit or ("c" * 40)
    dc = tmp / dc_rel
    for sub in ("schema", "prompts", "tools", "journal", "milestones/M1",
                "milestones/M1/snapshots", "state", "contracts"):
        (dc / sub).mkdir(parents=True, exist_ok=True)
    for name in ("typed_receipt.v1.schema.json",
                 "signer_receipt.v1.schema.json",
                 "signer_receipt.v2.schema.json",
                 "handoff.v1.schema.json", "handoff.v2.schema.json",
                 "launch_record.v1.schema.json", "launch_record.v2.schema.json",
                 "launch_outcome.v1.schema.json",
                 "milestone_exit_evidence.v1.schema.json",
                 "origin_anchor.v2.schema.json"):
        shutil.copy(DC / "schema" / name, dc / "schema" / name)
    shutil.copy(DC / "PROMPT_REGISTRY.v1.json", dc / "PROMPT_REGISTRY.v1.json")
    shutil.copy(DC / "MILESTONE_DAG.v1.json", dc / "MILESTONE_DAG.v1.json")
    shutil.copy(DC / "contracts/MILESTONE_EXIT_CONTRACT.v1.json",
                dc / "contracts/MILESTONE_EXIT_CONTRACT.v1.json")
    for template in (DC / "prompts").glob("P*.template.md"):
        shutil.copy(template, dc / "prompts" / template.name)
    for tool in ("receipts.py", "closure.py", "contract_set.py",
                 "run_journal.py"):
        shutil.copy(DC / "tools" / tool, dc / "tools" / tool)

    mdir = dc / "milestones/M1"
    anchor_doc = mdir / "MILESTONE_CONTRACT.v1.md"
    anchor_doc.write_text("contract", encoding="utf-8")
    entry_row = [{"path": str(anchor_doc.relative_to(tmp)),
                  "sha256": _sha(b"contract")}]

    def manifest(name: str) -> dict:
        value = receipts.close_record({
            "schema_version": "p7-manifest-v1", "entry_count": len(entry_row),
            "entries": entry_row, "manifest_digest": ""}, "manifest_digest")
        (mdir / name).write_text(json.dumps(value, ensure_ascii=False),
                                 encoding="utf-8")
        return value

    in_manifest = manifest("INPUT_MANIFEST.v1.json")
    out_manifest = manifest("OUTPUT_MANIFEST.v1.json")
    ev_manifest = manifest("EVIDENCE_MANIFEST.v1.json")

    reviews = []
    if with_reviews:
        for i, kind in enumerate((
                "INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER",
                "CODEX_GPT_EXTERNAL_REVIEW_SIGNER")):
            if signer_schema == "v1":
                base = {
                    "schema_version": "p7-signer-receipt-v1",
                    "reviewer_kind": kind, "provider": f"prov{i}",
                    "actual_model_id": f"model-{i}", "model_version": "v",
                    "task_thread_session_id": f"reviewer-session-{i}",
                    "input_commit": candidate,
                    "input_manifest_digest": in_manifest["manifest_digest"],
                    "prompt_digest": "e" * 64, "config_digest": "cfg",
                    "tool_summary": "read-only recompute",
                    "output_report_digest": "f" * 64,
                    "call_receipt": "receipt-evidence", "exit_status": 0,
                    "signed_at": "T",
                    "session_isolation_attestation": {
                        "fresh_session_not_fork_not_resume": True,
                        "did_not_author_reviewed_scope": True,
                        "auto_memory_disabled_or_not_applicable": True,
                        "isolation_evidence": "fresh"},
                    "verdict": "ACCEPT", "receipt_digest": ""}
            else:
                base = {
                    "schema_version": "p7-signer-receipt-v2",
                    "reviewer_kind": kind, "provider": f"prov{i}",
                    "actual_model_id": f"model-{i}", "model_version": "v",
                    "task_thread_session_id": f"reviewer-session-{i}",
                    "milestone_id": "M1", "product_scope": "SHARED",
                    "input_commit": candidate,
                    "input_manifest_digest": in_manifest["manifest_digest"],
                    "output_manifest_digest": out_manifest["manifest_digest"],
                    "evidence_manifest_digest": ev_manifest["manifest_digest"],
                    "prompt_digest": "e" * 64, "config_digest": "cfg",
                    "tool_summary": "read-only recompute",
                    "output_report_digest": "f" * 64,
                    "call_receipt": "receipt-evidence", "exit_status": 0,
                    "signed_at": "T",
                    "session_isolation_attestation": {
                        "fresh_session_not_fork_not_resume": True,
                        "did_not_author_reviewed_scope": True,
                        "auto_memory_disabled_or_not_applicable": True,
                        "auto_memory_disabled_before_launch": True,
                        "isolation_evidence": "fresh"},
                    "verdict": "ACCEPT", "receipt_digest": ""}
            base.update(signer_overrides or {})
            signer = receipts.close_record(base, "receipt_digest")
            rp = mdir / f"review_{i}.signer_receipt.json"
            rp.write_text(json.dumps(signer, ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":")),
                          encoding="utf-8")
            reviews.append({
                "receipt_path": str(rp.relative_to(tmp)),
                "receipt_digest": _sha(rp.read_bytes()),
                "reviewer_kind": kind, "verdict": "ACCEPT"})

    closeout = receipts.close_record({
        "schema_version": "p7-typed-receipt-v1",
        "receipt_kind": "CLOSEOUT_RECEIPT", "milestone_id": "M1",
        "product_scope": "SHARED", "result": predecessor_result,
        "terminal": True, "qualification_flags": flags or {},
        "candidate_commit": candidate,
        "output_manifest_digest": out_manifest["manifest_digest"],
        "evidence_manifest_digest": ev_manifest["manifest_digest"],
        "review_bindings": reviews, "issued_at": "T",
        "issued_by_role": "M1_PRINCIPAL", "receipt_digest": ""},
        "receipt_digest")
    decision = dict(closeout)
    decision["receipt_kind"] = "STAGE_DECISION"
    decision = receipts.close_record(decision, "receipt_digest")
    (mdir / "CLOSEOUT_RECEIPT.v1.json").write_text(
        json.dumps(closeout, ensure_ascii=False), encoding="utf-8")
    (mdir / "STAGE_DECISION.v1.json").write_text(
        json.dumps(decision, ensure_ascii=False), encoding="utf-8")
    (mdir / "CLOSEOUT_REPORT.v1.md").write_text("report", encoding="utf-8")

    # 出口证据：M1 全部必需键，逐键指向真实存在的证据文件
    exit_keys = {}
    evidence_sources = {
        "INDEPENDENT_CLAUDE_FABLE_REVIEW_ACCEPT":
            reviews[0]["receipt_path"] if reviews else None,
        "CODEX_GPT_REVIEW_ACCEPT":
            reviews[1]["receipt_path"] if len(reviews) > 1 else None,
    }
    for key in M1_EXIT_KEYS:
        rel = evidence_sources.get(key)
        if rel is None:
            evidence = mdir / "snapshots" / f"{key}.evidence.json"
            evidence.write_text(json.dumps({"key": key, "state": "PASS"}),
                                encoding="utf-8")
            rel = str(evidence.relative_to(tmp))
        exit_keys[key] = {"satisfied": True, "evidence_path": rel,
                          "evidence_sha256": _sha((tmp / rel).read_bytes())}
    exit_evidence = receipts.close_record({
        "schema_version": "p7-milestone-exit-evidence-v1",
        "milestone_id": "M1", "candidate_commit": candidate,
        "closeout_receipt_digest": closeout["receipt_digest"],
        "exit_keys": exit_keys, "issued_at": "T",
        "record_digest": ""}, "record_digest")
    exit_path = mdir / "MILESTONE_EXIT_EVIDENCE.v1.json"
    exit_path.write_text(json.dumps(exit_evidence, ensure_ascii=False),
                         encoding="utf-8")

    # ready-set 结果 + 活跃合同集合（full 时真实冻结）
    rs_path = mdir / "READY_SET_RESULT.v2.json"
    rs_path.write_text(json.dumps({"M2": {"status": "READY", "ready": True}},
                                  ensure_ascii=False), encoding="utf-8")
    acs_digest = "a" * 64
    if full:
        member = tmp / "plan.md"
        member.write_text("PLAN", encoding="utf-8")
        set_spec = {"active_plan": {"path": str(member.relative_to(tmp))},
                    "active_members": []}
        set_path = dc / "ACTIVE_CONTRACT_SET.v1.json"
        set_path.write_text(json.dumps(set_spec, ensure_ascii=False),
                            encoding="utf-8")
        contract_set = load_tool("contract_set")
        frozen = contract_set.compute(set_path, tmp, allow_pending=False)
        (dc / "state/ACTIVE_CONTRACT_DIGESTS.v1.json").write_text(
            json.dumps(frozen, ensure_ascii=False), encoding="utf-8")
        acs_digest = frozen["active_contract_set_digest"]

    template_digest = _sha((dc / "prompts/P2.M2.template.md").read_bytes())
    handoff = receipts.close_record({
        "schema_version": "p7-handoff-v2", "from_milestone": "M1",
        "to_milestone": ["M2"],
        "accepted_candidate_commit": candidate,
        "active_contract_set_digest": acs_digest,
        "input_manifest_digest": in_manifest["manifest_digest"],
        "output_manifest_digest": out_manifest["manifest_digest"],
        "evidence_manifest_digest": ev_manifest["manifest_digest"],
        "exit_evidence_digest": _sha(exit_path.read_bytes()),
        "last_green_test_summary": "all green",
        "review_receipt_bindings": reviews or [
            {"receipt_path": "x", "receipt_digest": "0" * 64,
             "reviewer_kind": "K", "verdict": "ACCEPT"},
            {"receipt_path": "y", "receipt_digest": "0" * 64,
             "reviewer_kind": "K2", "verdict": "ACCEPT"}],
        "qualification_flags": flags or {},
        "route_binding": None,
        "next_entry_contract": "prompts/P2.M2.template.md",
        "next_prompt_template_digest": template_digest,
        "ready_set_result_digest": _sha(rs_path.read_bytes()),
        "closure_rule": ("关闭提交不自指：由 ORIGIN_ANCHOR.v2 锚定——锚提交的"
                         "第一父提交必须等于锚文件内记录的 closeout_commit；"
                         "tools/closure.py verify_closure 从分支头零外部知识"
                         "机械重建 anchor→closeout→candidate 全链"),
        "issued_at": "T", "handoff_digest": ""}, "handoff_digest")
    (mdir / "HANDOFF.v2.json").write_text(
        json.dumps(handoff, ensure_ascii=False), encoding="utf-8")

    # renderer 绑定 CONTROL_PLANE_COMMIT 的来源（closure selftest 会以真提交覆盖）
    origin_anchor = receipts.close_record({
        "schema_version": "p7-origin-anchor-v2", "milestone_id": "M1",
        "remote": "origin = synthetic", "branch": "main",
        "candidate_commit": candidate, "closeout_commit": candidate,
        "anchor_rule": ("引入本文件的提交（锚提交）的第一父提交必须 == "
                        "closeout_commit；closeout_commit 树内工件字节摘要必须"
                        " == closeout_artifact_digests 逐项；candidate_commit "
                        "必须为 closeout_commit 祖先且 == 该树内 "
                        "HANDOFF.accepted_candidate_commit"),
        "plan_anchors": {"input": candidate},
        "closeout_artifact_digests": {
            str((mdir / name).relative_to(tmp)): _sha((mdir / name).read_bytes())
            for name in ("MILESTONE_CONTRACT.v1.md", "INPUT_MANIFEST.v1.json",
                         "OUTPUT_MANIFEST.v1.json", "EVIDENCE_MANIFEST.v1.json",
                         "STAGE_DECISION.v1.json", "CLOSEOUT_REPORT.v1.md",
                         "CLOSEOUT_RECEIPT.v1.json", "HANDOFF.v2.json",
                         "MILESTONE_EXIT_EVIDENCE.v1.json",
                         "READY_SET_RESULT.v2.json")
        } | ({rev["receipt_path"]: rev["receipt_digest"] for rev in reviews}
             if reviews else {"r1.signer_receipt.json": "0" * 64,
                              "r2.signer_receipt.json": "1" * 64}),
        "handoff_digest": handoff["handoff_digest"],
        "closeout_receipt_digest": closeout["receipt_digest"],
        "remote_verification": {
            "method": "synthetic fixture（无远端）",
            "remote_head": candidate,
            "matches_closeout_commit": True,
            "verified_at": "T"},
        "forbidden_actions_honored": "零 tag/force-push/rebase",
        "record_digest": ""}, "record_digest")
    (mdir / "ORIGIN_ANCHOR.v2.json").write_text(
        json.dumps(origin_anchor, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    journal_mod.append_record(dc / "journal/RUN_JOURNAL.v1.jsonl", {
        "session_id": "author-session-M1", "run_id": "R",
        "input_commit": candidate, "dirty_tree_digest": "d" * 64,
        "capsule": "CLOSE", "state": journal_state,
        "requested_model": "fable", "actual_model": "claude-fable-5",
        "subagent_ids": [], "last_green_commit": candidate,
        "verification_state": "GREEN", "next_action": "exit",
        "stop_reason": None}, None)
    return dc
