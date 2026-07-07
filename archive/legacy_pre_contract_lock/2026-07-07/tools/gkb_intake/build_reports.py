#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local GKB intake manifest and gate report summary.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--gate-summary", type=Path)
    parser.add_argument("--output-json", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_manifest(root: Path) -> list[str]:
    ignored_parts = {"__pycache__"}
    return [
        str(path.relative_to(root))
        for path in sorted(root.rglob("*"))
        if path.is_file() and not any(part in ignored_parts for part in path.parts)
    ]


def protected_hashes(root: Path) -> dict[str, str]:
    protected = [
        "AGENTS.md",
        "knowledge_intake/AGENTS.md",
        "knowledge_intake/gpt55_gkb_enrichment_v1/AGENTS.md",
        "SKILL/diyu-gkb-draft-intake.md",
        "tools.txt",
        "落盘总方案.txt",
    ]
    return {relative: sha256(root / relative) for relative in protected if (root / relative).exists()}


def load_json_if_present(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def main() -> int:
    args = parse_args()
    if not args.root.exists() or not args.workspace.exists():
        print(json.dumps({"passed": False, "error": "root and workspace must exist"}, indent=2))
        return 1
    manifest = file_manifest(args.root)
    payload: dict[str, Any] = {
        "passed": True,
        "root": str(args.root),
        "workspace": str(args.workspace),
        "file_count": len(manifest),
        "workspace_file_count": len(file_manifest(args.workspace)),
        "protected_hashes": protected_hashes(args.root),
        "gate_summary": load_json_if_present(args.gate_summary),
    }
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
