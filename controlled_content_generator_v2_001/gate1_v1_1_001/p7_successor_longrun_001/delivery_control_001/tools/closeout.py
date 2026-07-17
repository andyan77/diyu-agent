#!/usr/bin/env python3
"""关闭八件套校验器（P1 §二十三）。

八件套：MILESTONE_CONTRACT / INPUT_MANIFEST / OUTPUT_MANIFEST /
EVIDENCE_MANIFEST / STAGE_DECISION / CLOSEOUT_RECEIPT / CLOSEOUT_REPORT / HANDOFF。
manifest 采用有界摘要闭包：不得递归包含自身摘要或后生成的签字。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

DC = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = _load(DC / "tools/receipts.py", "p7_receipts_closeout")

# 八件套按基名登记；文件名经 receipts.resolve_versioned 解析（v2 优先，回退 v1）
EIGHT_PIECES = (
    ("MILESTONE_CONTRACT", "md"),
    ("INPUT_MANIFEST", "json"),
    ("OUTPUT_MANIFEST", "json"),
    ("EVIDENCE_MANIFEST", "json"),
    ("STAGE_DECISION", "json"),
    ("CLOSEOUT_REPORT", "md"),
    ("CLOSEOUT_RECEIPT", "json"),
    ("HANDOFF", "json"),
)

# 后生成的关闭工件：不得被 manifest 递归包含（有界摘要闭包）
LATER_GENERATED_PREFIXES = (
    "CLOSEOUT_RECEIPT.", "STAGE_DECISION.", "HANDOFF.",
    "MILESTONE_EXIT_EVIDENCE.", "READY_SET_RESULT.", "ORIGIN_ANCHOR.",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _bound_blob_matches(root: Path, manifest: dict, rel: str,
                        expected_sha256: str) -> bool:
    """普通条目的候选时点回退比对。

    manifest 的绑定语义是 bound_candidate_commit 时点的树，而非活树；
    关闭阶段按合同在双签后合法演进个别被钉扎的活体文件（如阶段登记后
    重建的 spine 候选清单，见 M2 CLOSEOUT_REPORT「spine 候选清单闭环
    重建」）。git 历史不可改写：条目摘要必须等于绑定提交处的 blob 才放行，
    篡改活文件且不匹配候选 blob 依旧两路皆败 = fail-closed 不降。"""
    bound = str(manifest.get("bound_candidate_commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", bound):
        return False
    proc = subprocess.run(
        ["git", "-C", str(root), "show", f"{bound}:{rel}"],
        capture_output=True)
    if proc.returncode != 0:
        return False
    return hashlib.sha256(proc.stdout).hexdigest() == expected_sha256


def _verify_manifest(root: Path, path: Path, self_rel: str) -> list[str]:
    """manifest：逐条 path+sha256 复算；有界闭包（不含自身、不含签字回执）。"""
    errors: list[str] = []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{path.name}: unreadable {exc}"]
    entries = value.get("entries")
    if not isinstance(entries, list) or not entries:
        return [f"{path.name}: entries missing/empty"]
    if value.get("entry_count") != len(entries):
        errors.append(f"{path.name}: entry_count mismatch")
    seen: set[str] = set()
    for entry in entries:
        rel = str(entry.get("path", ""))
        if rel in seen:
            errors.append(f"{path.name}: duplicate entry {rel}")
        seen.add(rel)
        if rel == self_rel:
            errors.append(f"{path.name}: recursive self-inclusion ({rel})")
            continue
        base_name = rel.rsplit("/", 1)[-1]
        if rel.endswith(".signer_receipt.json") or any(
                base_name.startswith(prefix)
                for prefix in LATER_GENERATED_PREFIXES):
            errors.append(f"{path.name}: includes later-generated signature/"
                          f"receipt {rel} (bounded closure breach)")
            continue
        # 活体演进文件（journal/状态/注册表）：manifest 锚定候选时点冻结快照，
        # 原路径继续演进不构成漂移（快照必须位于本里程碑 snapshots/ 下）。
        snapshot_rel = entry.get("frozen_snapshot")
        if snapshot_rel:
            # 路径遍历加固（Fable R2 ADVISORY）：解析后必须落在本里程碑
            # snapshots/ 目录内，子串判断不作数
            allowed_dir = (path.parent / "snapshots").resolve()
            target = (root / str(snapshot_rel)).resolve()
            try:
                contained = target.is_relative_to(allowed_dir)
            except AttributeError:  # <py3.9 回退
                contained = str(target).startswith(str(allowed_dir) + "/")
            if not contained:
                errors.append(f"{path.name}: frozen_snapshot escapes "
                              f"snapshots/ dir: {snapshot_rel}")
                continue
            if not (root / rel).exists():
                errors.append(f"{path.name}: live file missing for "
                              f"snapshotted entry {rel}")
        else:
            target = root / rel
        if not target.is_file():
            errors.append(f"{path.name}: missing file {rel}")
            continue
        if sha256_file(target) != entry.get("sha256"):
            # 无快照的普通条目：活树不匹配时回退到绑定候选提交处的 blob
            #（快照条目不回退——快照本身就是其冻结基准）
            if snapshot_rel or not _bound_blob_matches(
                    root, value, rel, str(entry.get("sha256", ""))):
                errors.append(f"{path.name}: digest drift {rel}")
    digest = value.get("manifest_digest")
    if digest != receipts.canonical_digest(value, "manifest_digest"):
        errors.append(f"{path.name}: manifest_digest recompute mismatch")
    return errors


def validate_eight_pieces(root: Path, milestone_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    details: list[str] = []
    paths = {base: receipts.resolve_versioned(milestone_dir, base, ext)
             for base, ext in EIGHT_PIECES}
    missing = [base for base, path in paths.items() if not path.is_file()]
    if missing:
        return False, [f"eight-piece set incomplete; missing: {missing}"]
    details.append("eight_pieces_present=8/8")

    for base in ("INPUT_MANIFEST", "OUTPUT_MANIFEST", "EVIDENCE_MANIFEST"):
        self_rel = str(paths[base].relative_to(root))
        errors += _verify_manifest(root, paths[base], self_rel)

    try:
        decision = receipts.load_typed_receipt(paths["STAGE_DECISION"])
        closeout = receipts.load_typed_receipt(paths["CLOSEOUT_RECEIPT"])
        # 指令第 4 条：两份 typed 回执强制逐字段比对（任何分叉 = 关闭无效）
        errors += receipts.compare_typed_pair(decision, closeout)
        details.append(f"typed_result={closeout.get('result')}")
        out_manifest = json.loads(
            paths["OUTPUT_MANIFEST"].read_text(encoding="utf-8"))
        ev_manifest = json.loads(
            paths["EVIDENCE_MANIFEST"].read_text(encoding="utf-8"))
        if closeout.get("output_manifest_digest") != out_manifest.get(
                "manifest_digest"):
            errors.append("closeout not bound to OUTPUT_MANIFEST digest")
        if closeout.get("evidence_manifest_digest") != ev_manifest.get(
                "manifest_digest"):
            errors.append("closeout not bound to EVIDENCE_MANIFEST digest")
    except receipts.ReceiptError as exc:
        errors.append(str(exc))

    try:
        handoff = receipts.validate_handoff(paths["HANDOFF"])
        details.append(f"handoff_to={handoff.get('to_milestone')}")
    except receipts.ReceiptError as exc:
        errors.append(str(exc))

    return not errors, details + errors


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DC.parents[3]))
    ap.add_argument("--milestone", required=True)
    args = ap.parse_args()
    ok, details = validate_eight_pieces(
        Path(args.root), DC / "milestones" / args.milestone)
    print(json.dumps({"ok": ok, "details": details}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
