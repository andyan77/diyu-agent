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
from pathlib import Path

DC = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = _load(DC / "tools/receipts.py", "p7_receipts_closeout")

EIGHT_PIECES = (
    "MILESTONE_CONTRACT.v1.md",
    "INPUT_MANIFEST.v1.json",
    "OUTPUT_MANIFEST.v1.json",
    "EVIDENCE_MANIFEST.v1.json",
    "STAGE_DECISION.v1.json",
    "CLOSEOUT_REPORT.v1.md",
    "CLOSEOUT_RECEIPT.v1.json",
    "HANDOFF.v1.json",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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
        if rel.endswith((".signer_receipt.json", "CLOSEOUT_RECEIPT.v1.json",
                         "STAGE_DECISION.v1.json")):
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
            errors.append(f"{path.name}: digest drift {rel}")
    digest = value.get("manifest_digest")
    if digest != receipts.canonical_digest(value, "manifest_digest"):
        errors.append(f"{path.name}: manifest_digest recompute mismatch")
    return errors


def validate_eight_pieces(root: Path, milestone_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    details: list[str] = []
    missing = [name for name in EIGHT_PIECES
               if not (milestone_dir / name).is_file()]
    if missing:
        return False, [f"eight-piece set incomplete; missing: {missing}"]
    details.append("eight_pieces_present=8/8")

    for name in ("INPUT_MANIFEST.v1.json", "OUTPUT_MANIFEST.v1.json",
                 "EVIDENCE_MANIFEST.v1.json"):
        self_rel = str((milestone_dir / name).relative_to(root))
        errors += _verify_manifest(root, milestone_dir / name, self_rel)

    try:
        decision = receipts.load_typed_receipt(
            milestone_dir / "STAGE_DECISION.v1.json")
        closeout = receipts.load_typed_receipt(
            milestone_dir / "CLOSEOUT_RECEIPT.v1.json")
        if decision.get("result") != closeout.get("result"):
            errors.append("STAGE_DECISION and CLOSEOUT_RECEIPT result mismatch")
        if decision.get("candidate_commit") != closeout.get("candidate_commit"):
            errors.append("candidate commit mismatch between typed receipts")
        details.append(f"typed_result={closeout.get('result')}")
        out_manifest = json.loads(
            (milestone_dir / "OUTPUT_MANIFEST.v1.json").read_text(
                encoding="utf-8"))
        ev_manifest = json.loads(
            (milestone_dir / "EVIDENCE_MANIFEST.v1.json").read_text(
                encoding="utf-8"))
        if closeout.get("output_manifest_digest") != out_manifest.get(
                "manifest_digest"):
            errors.append("closeout not bound to OUTPUT_MANIFEST digest")
        if closeout.get("evidence_manifest_digest") != ev_manifest.get(
                "manifest_digest"):
            errors.append("closeout not bound to EVIDENCE_MANIFEST digest")
    except receipts.ReceiptError as exc:
        errors.append(str(exc))

    try:
        handoff = receipts.validate_handoff(milestone_dir / "HANDOFF.v1.json")
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
