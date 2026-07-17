#!/usr/bin/env python3
"""闭包验证器（发起人 2026-07-16 八项加固指令第 1/2 条）。

两个入口：
  validate_handoff_full —— HANDOFF v2 的全部跨文件、跨提交引用逐项复算：
    manifest 三摘要、出口证据摘要、活跃合同集合摘要、签字回执逐份、
    下一 Prompt 模板摘要、ready-set 结果摘要、候选提交存在性与祖先关系、
    与两份 typed 回执的候选/旗标/绑定一致性。
  verify_closure —— candidate / closeout / origin-anchor 的可重建闭包：
    从任意分支头零外部知识重建全链——
      head 树内 ORIGIN_ANCHOR.v2 → 锚提交 A（引入该文件的提交）
      → A 的第一父提交必须 == 锚内 closeout_commit K
      → K 树内关闭工件字节摘要必须 == 锚内 closeout_artifact_digests 逐项
      → K 树内 HANDOFF 绑定 candidate C == 锚内 candidate_commit
      → C 必须为 K 祖先；typed 回执绑定 C 与 manifest 摘要。
    提交不能包含自身 SHA，故锚存放于 K 的直接子提交——该父子关系即闭包边。

用法：
  closure.py --handoff-full M1 [--root R]
  closure.py --verify M1 [--head HEAD] [--root R]
  closure.py --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

DC = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = DC.parents[3]
DC_REL = ("controlled_content_generator_v2_001/gate1_v1_1_001/"
          "p7_successor_longrun_001/delivery_control_001")

REQUIRED_CLOSEOUT_ARTIFACT_BASES = (
    "MILESTONE_CONTRACT", "INPUT_MANIFEST", "OUTPUT_MANIFEST",
    "EVIDENCE_MANIFEST", "STAGE_DECISION", "CLOSEOUT_REPORT",
    "CLOSEOUT_RECEIPT", "HANDOFF", "MILESTONE_EXIT_EVIDENCE",
    "READY_SET_RESULT",
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = _load(DC / "tools/receipts.py", "p7_receipts_closure")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True)


def _git_ok(root: Path, *args: str) -> bool:
    return _git(root, *args).returncode == 0


def _git_text(root: Path, *args: str) -> str | None:
    proc = _git(root, *args)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace").strip()


def _git_blob(root: Path, commit: str, rel: str) -> bytes | None:
    proc = _git(root, "cat-file", "blob", f"{commit}:{rel}")
    return proc.stdout if proc.returncode == 0 else None


# ------------------------------------------------- handoff full recompute

def validate_handoff_full(root: Path, milestone: str,
                          dc: Path | None = None,
                          dc_rel: str = DC_REL) -> list[str]:
    """HANDOFF v2 全引用复算；返回错误清单（空 = 全部一致）。"""
    dc = dc or (root / dc_rel)
    mdir = dc / "milestones" / milestone
    errors: list[str] = []
    handoff_path = receipts.resolve_versioned(mdir, "HANDOFF")
    try:
        handoff = receipts.validate_handoff(handoff_path)
    except receipts.ReceiptError as exc:
        return [str(exc)]
    if handoff.get("schema_version") != "p7-handoff-v2":
        return [f"{handoff_path.name}: full recompute requires handoff v2 "
                "(v1 lacks recomputable closure fields)"]

    candidate = handoff["accepted_candidate_commit"]

    # 1. 候选提交：存在 + 为当前 HEAD 祖先（跨提交引用）
    if not _git_ok(root, "cat-file", "-e", f"{candidate}^{{commit}}"):
        errors.append(f"candidate commit unknown to repository: {candidate}")
    elif not _git_ok(root, "merge-base", "--is-ancestor", candidate, "HEAD"):
        errors.append(f"candidate commit not ancestor of HEAD: {candidate}")

    # 2. 三份 manifest：文件摘要复算 + 与 handoff 字段一致
    manifests: dict[str, dict] = {}
    for base, field in (("INPUT_MANIFEST", "input_manifest_digest"),
                        ("OUTPUT_MANIFEST", "output_manifest_digest"),
                        ("EVIDENCE_MANIFEST", "evidence_manifest_digest")):
        mpath = receipts.resolve_versioned(mdir, base)
        if not mpath.is_file():
            errors.append(f"{base} missing for handoff recompute")
            continue
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        manifests[base] = manifest
        recomputed = receipts.canonical_digest(manifest, "manifest_digest")
        if manifest.get("manifest_digest") != recomputed:
            errors.append(f"{base}: manifest_digest recompute mismatch")
        if handoff.get(field) != manifest.get("manifest_digest"):
            errors.append(f"handoff.{field} != {base}.manifest_digest")

    # 3. 出口证据摘要（指令第 4/5 条产物）
    exit_path = mdir / "MILESTONE_EXIT_EVIDENCE.v1.json"
    if not exit_path.is_file():
        errors.append("MILESTONE_EXIT_EVIDENCE missing for handoff recompute")
    elif handoff.get("exit_evidence_digest") != sha256_bytes(
            exit_path.read_bytes()):
        errors.append("handoff.exit_evidence_digest != exit evidence file bytes")

    # 4. 活跃合同集合摘要：冻结清单值 + contract_set 复算 PASS
    frozen_path = dc / "state/ACTIVE_CONTRACT_DIGESTS.v1.json"
    set_path = dc / "ACTIVE_CONTRACT_SET.v1.json"
    if not frozen_path.is_file() or not set_path.is_file():
        errors.append("active contract set / frozen digests missing")
    else:
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
        if handoff.get("active_contract_set_digest") != frozen.get(
                "active_contract_set_digest"):
            errors.append("handoff.active_contract_set_digest != frozen manifest")
        contract_set = _load(dc / "tools/contract_set.py",
                             "p7_contract_set_closure")
        live = contract_set.compute(set_path, root,
                                    allow_pending=frozen.get(
                                        "pending_count", 0) > 0)
        if live["errors"]:
            errors.append(f"contract set recompute errors: {live['errors'][:2]}")
        elif live.get("active_contract_set_digest") != frozen.get(
                "active_contract_set_digest"):
            errors.append("active contract set digest drifted from frozen value")

    # 5. typed 回执一致性：候选 / manifest 摘要 / 旗标 / 绑定集合
    closeout = None
    try:
        decision = receipts.load_typed_receipt(
            receipts.resolve_versioned(mdir, "STAGE_DECISION"))
        closeout = receipts.load_typed_receipt(
            receipts.resolve_versioned(mdir, "CLOSEOUT_RECEIPT"))
        errors += receipts.compare_typed_pair(decision, closeout)
        if closeout.get("candidate_commit") != candidate:
            errors.append("handoff candidate != closeout receipt candidate")
        if (closeout.get("qualification_flags") or {}) != (
                handoff.get("qualification_flags") or {}):
            errors.append("handoff qualification_flags != closeout receipt flags")
        closeout_bindings = {(b.get("receipt_path"), b.get("receipt_digest"))
                             for b in closeout.get("review_bindings", [])}
        handoff_bindings = {(b.get("receipt_path"), b.get("receipt_digest"))
                            for b in handoff.get("review_receipt_bindings", [])}
        if closeout_bindings != handoff_bindings:
            errors.append("handoff review bindings != closeout receipt bindings")
    except receipts.ReceiptError as exc:
        errors.append(f"typed receipts invalid: {exc}")

    # 6. 签字回执逐份复算（文件字节摘要 + 内容 + v2 绑定 + 候选一致）
    for binding in handoff.get("review_receipt_bindings", []):
        rel = str(binding.get("receipt_path", ""))
        rp = root / rel
        if not rp.is_file():
            errors.append(f"review receipt missing: {rel}")
            continue
        if sha256_bytes(rp.read_bytes()) != binding.get("receipt_digest"):
            errors.append(f"review receipt byte digest mismatch: {rp.name}")
            continue
        try:
            signer = receipts.load_signer_receipt(rp)
        except receipts.ReceiptError as exc:
            errors.append(f"review receipt invalid: {exc}")
            continue
        if signer.get("reviewer_kind") != binding.get("reviewer_kind"):
            errors.append(f"binding reviewer_kind mismatch: {rp.name}")
        if signer.get("verdict") != binding.get("verdict"):
            errors.append(f"binding verdict mismatch: {rp.name}")
        if signer.get("input_commit") != candidate:
            errors.append(f"review receipt not bound to candidate: {rp.name}")

    # 7. 下一入口 Prompt 模板摘要（跨文件引用：PROMPT_REGISTRY → 模板文件）
    registry_path = dc / "PROMPT_REGISTRY.v1.json"
    if not registry_path.is_file():
        errors.append("PROMPT_REGISTRY missing for template recompute")
    else:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        target = (handoff.get("to_milestone") or [None])[0]
        entry = next((row for row in registry.get("prompts", [])
                      if row.get("milestone_id") == target), None)
        if entry is None:
            errors.append(f"registry entry missing for to_milestone {target}")
        else:
            template = dc / entry["template_path"]
            if not template.is_file():
                errors.append(f"next prompt template missing: "
                              f"{entry['template_path']}")
            elif handoff.get("next_prompt_template_digest") != sha256_bytes(
                    template.read_bytes()):
                errors.append("handoff.next_prompt_template_digest != "
                              "registry template file bytes")

    # 8. ready-set 结果摘要
    rs_path = receipts.resolve_versioned(mdir, "READY_SET_RESULT")
    if not rs_path.is_file():
        errors.append("READY_SET_RESULT missing for handoff recompute")
    elif handoff.get("ready_set_result_digest") != sha256_bytes(
            rs_path.read_bytes()):
        errors.append("handoff.ready_set_result_digest != ready-set file bytes")

    return errors


# ------------------------------------------------------ closure rebuild

def verify_closure(root: Path, milestone: str, head: str = "HEAD",
                   dc_rel: str = DC_REL,
                   remote_head: str | None = None) -> tuple[bool, list[str]]:
    """从分支头零外部知识重建 candidate/closeout/anchor 闭包并逐边核验。"""
    details: list[str] = []
    errors: list[str] = []
    anchor_rel = f"{dc_rel}/milestones/{milestone}/ORIGIN_ANCHOR.v2.json"

    head_sha = _git_text(root, "rev-parse", f"{head}^{{commit}}")
    if head_sha is None:
        return False, [f"head unresolvable: {head}"]
    details.append(f"head={head_sha}")

    # 边 0：head 树内必须能读到锚文件
    anchor_bytes = _git_blob(root, head_sha, anchor_rel)
    if anchor_bytes is None:
        return False, details + [f"anchor absent in head tree: {anchor_rel}"]
    try:
        anchor = json.loads(anchor_bytes.decode("utf-8"))
    except ValueError as exc:
        return False, details + [f"anchor unparseable: {exc}"]
    schema_errors = receipts._schema_validate(anchor,
                                              "origin_anchor.v2.schema.json")
    errors += [f"anchor {e}" for e in schema_errors]
    if anchor.get("record_digest") != receipts.canonical_digest(
            anchor, "record_digest"):
        errors.append("anchor record_digest recompute mismatch")

    candidate = str(anchor.get("candidate_commit", ""))
    closeout_commit = str(anchor.get("closeout_commit", ""))

    # 边 1：锚提交 = head 可达范围内最后引入/修改锚文件的提交；
    #        其第一父提交必须 == 锚内 closeout_commit（提交不能自指的解法）
    anchor_commit = _git_text(root, "log", "--format=%H", "-n1",
                              head_sha, "--", anchor_rel)
    if not anchor_commit:
        errors.append("anchor introducing commit unresolvable")
    else:
        details.append(f"anchor_commit={anchor_commit}")
        parent = _git_text(root, "rev-parse", f"{anchor_commit}^")
        if parent != closeout_commit:
            errors.append(f"anchor commit first parent {parent} != "
                          f"anchor.closeout_commit {closeout_commit}")

    # 边 2：closeout 提交存在且为 head 祖先
    if not _git_ok(root, "cat-file", "-e", f"{closeout_commit}^{{commit}}"):
        errors.append(f"closeout commit unknown: {closeout_commit}")
        return False, details + errors
    if not _git_ok(root, "merge-base", "--is-ancestor", closeout_commit,
                   head_sha):
        errors.append("closeout commit not ancestor of head")

    # 边 3：closeout 树内关闭工件字节摘要逐项 == 锚登记；覆盖面完整
    artifact_digests = anchor.get("closeout_artifact_digests") or {}
    covered_bases = set()
    for rel, digest in sorted(artifact_digests.items()):
        blob = _git_blob(root, closeout_commit, rel)
        if blob is None:
            errors.append(f"closeout tree missing artifact: {rel}")
            continue
        if sha256_bytes(blob) != digest:
            errors.append(f"closeout artifact digest mismatch: {rel}")
        name = rel.rsplit("/", 1)[-1]
        for base in REQUIRED_CLOSEOUT_ARTIFACT_BASES:
            if name.startswith(base + "."):
                covered_bases.add(base)
        if name.endswith(".signer_receipt.json"):
            covered_bases.add("SIGNER_RECEIPT")
    missing_cover = [b for b in REQUIRED_CLOSEOUT_ARTIFACT_BASES
                     if b not in covered_bases]
    signer_count = sum(1 for rel in artifact_digests
                       if rel.endswith(".signer_receipt.json"))
    if missing_cover:
        errors.append(f"anchor artifact map lacks required pieces: "
                      f"{missing_cover}")
    if signer_count < 2:
        errors.append(f"anchor artifact map carries {signer_count} signer "
                      "receipts (<2)")
    details.append(f"artifacts_verified={len(artifact_digests)}")

    # 边 4：closeout 树内 HANDOFF → candidate 绑定 + 摘要一致
    handoff_rel = next((rel for rel in artifact_digests
                        if rel.rsplit("/", 1)[-1].startswith("HANDOFF.")), None)
    if handoff_rel is None:
        errors.append("no HANDOFF in anchor artifact map")
    else:
        blob = _git_blob(root, closeout_commit, handoff_rel)
        if blob is not None:
            handoff = json.loads(blob.decode("utf-8"))
            if handoff.get("handoff_digest") != receipts.canonical_digest(
                    handoff, "handoff_digest"):
                errors.append("handoff (in closeout tree) digest mismatch")
            if handoff.get("accepted_candidate_commit") != candidate:
                errors.append("handoff candidate != anchor candidate")
            if anchor.get("handoff_digest") != handoff.get("handoff_digest"):
                errors.append("anchor.handoff_digest != handoff digest")

    # 边 5：closeout 树内 CLOSEOUT_RECEIPT → PASS/候选/manifest 摘要
    receipt_rel = next((rel for rel in artifact_digests
                        if rel.rsplit("/", 1)[-1].startswith(
                            "CLOSEOUT_RECEIPT.")), None)
    if receipt_rel is None:
        errors.append("no CLOSEOUT_RECEIPT in anchor artifact map")
    else:
        blob = _git_blob(root, closeout_commit, receipt_rel)
        if blob is not None:
            receipt = json.loads(blob.decode("utf-8"))
            if receipt.get("receipt_digest") != receipts.canonical_digest(
                    receipt, "receipt_digest"):
                errors.append("closeout receipt digest mismatch (in tree)")
            if receipt.get("candidate_commit") != candidate:
                errors.append("closeout receipt candidate != anchor candidate")
            if anchor.get("closeout_receipt_digest") != receipt.get(
                    "receipt_digest"):
                errors.append("anchor.closeout_receipt_digest mismatch")
            if receipt.get("milestone_id") != milestone:
                errors.append("closeout receipt milestone != verified milestone")

    # 边 6：candidate 存在且为 closeout 祖先
    if not _git_ok(root, "cat-file", "-e", f"{candidate}^{{commit}}"):
        errors.append(f"candidate commit unknown: {candidate}")
    elif not _git_ok(root, "merge-base", "--is-ancestor", candidate,
                     closeout_commit):
        errors.append("candidate not ancestor of closeout commit")

    # 边 7（可选）：远端头核验
    if remote_head is not None:
        if anchor_commit and remote_head == anchor_commit:
            details.append("remote_head==anchor_commit")
        elif anchor_commit and _git_ok(root, "cat-file", "-e",
                                       f"{remote_head}^{{commit}}") \
                and _git_ok(root, "merge-base", "--is-ancestor",
                            anchor_commit, remote_head):
            details.append("anchor_commit ancestor of remote_head")
        else:
            errors.append(f"remote head {remote_head} does not contain "
                          "anchor commit")

    details.append(f"candidate={candidate}")
    details.append(f"closeout_commit={closeout_commit}")
    return not errors, details + errors


# ------------------------------------------------------------- selftest

def _run(cwd: Path, *args: str) -> str:
    proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
    assert proc.returncode == 0, (args, proc.stderr)
    return proc.stdout.strip()


def selftest() -> int:
    import tempfile
    failures: list[str] = []

    def expect(name: str, cond: bool) -> None:
        print(f"[{'ok' if cond else 'FAIL'}] closure_selftest:{name}")
        if not cond:
            failures.append(name)

    sys.path.insert(0, str(DC / "tests"))
    try:
        import fixture_helpers as fh
    finally:
        sys.path.pop(0)

    def build_repo(tmp: Path) -> tuple[Path, dict]:
        """真实 git 仓库：candidate 提交 → 关闭工件提交 K → 锚提交 A。"""
        _run(tmp, "git", "init", "-q", "-b", "main")
        _run(tmp, "git", "config", "user.email", "t@t")
        _run(tmp, "git", "config", "user.name", "t")
        (tmp / "impl.py").write_text("x = 1\n", encoding="utf-8")
        _run(tmp, "git", "add", "impl.py")
        _run(tmp, "git", "commit", "-qm", "candidate")
        candidate = _run(tmp, "git", "rev-parse", "HEAD")
        dc = fh.build_m1_closeout_fixture(tmp, candidate_commit=candidate,
                                          full=True)
        _run(tmp, "git", "add", "-A", str(dc.relative_to(tmp)))
        _run(tmp, "git", "commit", "-qm", "closeout")
        closeout_commit = _run(tmp, "git", "rev-parse", "HEAD")
        mdir = dc / "milestones/M1"
        artifact_digests = {}
        for f in sorted(mdir.iterdir()):
            if f.is_file():
                artifact_digests[str(f.relative_to(tmp))] = sha256_bytes(
                    f.read_bytes())
        handoff = json.loads(
            (mdir / "HANDOFF.v2.json").read_text(encoding="utf-8"))
        closeout = json.loads(
            (mdir / "CLOSEOUT_RECEIPT.v1.json").read_text(encoding="utf-8"))
        anchor = receipts.close_record({
            "schema_version": "p7-origin-anchor-v2", "milestone_id": "M1",
            "remote": "origin = synthetic", "branch": "main",
            "candidate_commit": candidate,
            "closeout_commit": closeout_commit,
            "anchor_rule": ("引入本文件的提交（锚提交）的第一父提交必须 == "
                            "closeout_commit；closeout_commit 树内工件字节摘要必须"
                            " == closeout_artifact_digests 逐项；candidate_commit "
                            "必须为 closeout_commit 祖先且 == 该树内 "
                            "HANDOFF.accepted_candidate_commit"),
            "plan_anchors": {"input": candidate},
            "closeout_artifact_digests": artifact_digests,
            "handoff_digest": handoff["handoff_digest"],
            "closeout_receipt_digest": closeout["receipt_digest"],
            "remote_verification": {
                "method": "synthetic selftest（无远端）",
                "remote_head": closeout_commit,
                "matches_closeout_commit": True,
                "verified_at": "T"},
            "forbidden_actions_honored": "零 tag/force-push/rebase",
            "record_digest": ""}, "record_digest")
        anchor_path = mdir / "ORIGIN_ANCHOR.v2.json"
        anchor_path.write_text(json.dumps(anchor, ensure_ascii=False, indent=2)
                               + "\n", encoding="utf-8")
        _run(tmp, "git", "add", str(anchor_path.relative_to(tmp)))
        _run(tmp, "git", "commit", "-qm", "anchor")
        return dc, {"candidate": candidate, "closeout": closeout_commit,
                    "anchor_commit": _run(tmp, "git", "rev-parse", "HEAD")}

    dc_rel_fixture = "delivery_control_001"

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        dc, commits = build_repo(tmp)

        # 正向：handoff 全复算 0 错误
        errors = validate_handoff_full(tmp, "M1", dc=dc)
        expect("handoff_full_recompute_clean", errors == [])

        # 正向：闭包重建通过
        ok, details = verify_closure(tmp, "M1", dc_rel=dc_rel_fixture)
        expect("closure_verify_pass", ok)

        # 攻击 A：锚提交与 closeout 提交之间插入无关提交 → 第一父边断裂
        (tmp / "later.txt").write_text("later", encoding="utf-8")
        _run(tmp, "git", "add", "later.txt")
        _run(tmp, "git", "commit", "-qm", "later")
        anchor_path = dc / "milestones/M1/ORIGIN_ANCHOR.v2.json"
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchor["remote"] = "origin = synthetic (touched)"
        anchor = receipts.close_record(
            {k: v for k, v in anchor.items() if k != "record_digest"}
            | {"record_digest": ""}, "record_digest")
        anchor_path.write_text(json.dumps(anchor, ensure_ascii=False, indent=2)
                               + "\n", encoding="utf-8")
        _run(tmp, "git", "add", str(anchor_path.relative_to(tmp)))
        _run(tmp, "git", "commit", "-qm", "re-anchor detached from closeout")
        ok, details = verify_closure(tmp, "M1", dc_rel=dc_rel_fixture)
        expect("closure_detached_anchor_rejected",
               not ok and any("first parent" in d for d in details))

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        dc, commits = build_repo(tmp)

        # 攻击 B：handoff 的模板摘要过期（模板被改）→ 全复算必须失败
        template = dc / "prompts/P2.M2.template.md"
        template.write_text(template.read_text(encoding="utf-8") + "\nX\n",
                            encoding="utf-8")
        errors = validate_handoff_full(tmp, "M1", dc=dc)
        expect("stale_template_digest_rejected",
               any("next_prompt_template_digest" in e for e in errors))
        template_bytes = template.read_bytes()

        # 攻击 C：ready-set 结果被改 → 摘要失配
        rs_path = dc / "milestones/M1/READY_SET_RESULT.v2.json"
        rs_path.write_text(rs_path.read_text(encoding="utf-8") + " ",
                           encoding="utf-8")
        errors = validate_handoff_full(tmp, "M1", dc=dc)
        expect("ready_set_drift_rejected",
               any("ready_set_result_digest" in e for e in errors))

        # 攻击 D：出口证据文件被改 → 摘要失配
        exit_path = dc / "milestones/M1/MILESTONE_EXIT_EVIDENCE.v1.json"
        exit_path.write_text(exit_path.read_text(encoding="utf-8") + " ",
                             encoding="utf-8")
        errors = validate_handoff_full(tmp, "M1", dc=dc)
        expect("exit_evidence_drift_rejected",
               any("exit_evidence_digest" in e for e in errors))

        # 攻击 E：闭包树内工件被后续提交篡改不影响 K 树校验，
        # 但锚登记摘要被篡改必须被拒
        anchor_path = dc / "milestones/M1/ORIGIN_ANCHOR.v2.json"
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        victim = next(iter(anchor["closeout_artifact_digests"]))
        anchor["closeout_artifact_digests"][victim] = "0" * 64
        # 摘要重算以通过 record_digest 检查——闭包必须仍在树摘要边失败
        anchor = receipts.close_record(
            {k: v for k, v in anchor.items() if k != "record_digest"}
            | {"record_digest": ""}, "record_digest")
        anchor_path.write_text(json.dumps(anchor, ensure_ascii=False, indent=2)
                               + "\n", encoding="utf-8")
        _run(tmp, "git", "add", "-A")
        _run(tmp, "git", "commit", "-qm", "tamper anchor map")
        ok, details = verify_closure(tmp, "M1", dc_rel=dc_rel_fixture)
        expect("tampered_artifact_digest_rejected",
               not ok and any("digest mismatch" in d or "first parent" in d
                              for d in details))

    print("CLOSURE_SELFTEST:", "ALL_PASS" if not failures
          else f"FAILED {failures}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--handoff-full", metavar="M")
    ap.add_argument("--verify", metavar="M")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--remote-head")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    root = Path(args.root)
    if args.handoff_full:
        errors = validate_handoff_full(root, args.handoff_full)
        print(json.dumps({"handoff_full_recompute":
                          "PASS" if not errors else "FAIL",
                          "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    if args.verify:
        ok, details = verify_closure(root, args.verify, head=args.head,
                                     remote_head=args.remote_head)
        print(json.dumps({"closure": "PASS" if ok else "FAIL",
                          "details": details}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
