#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from gkb_intake_common import Finding, build_result, emit_result, iter_data_files, load_structured

GATE_ID = "check_declared_semantics_alignment"
SCANNED_DIRS = ("03_raw_drafts", "04_aligned_candidates")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate declared semantics preservation from raw draft to aligned candidate.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def iter_declared_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        matches: list[dict[str, Any]] = []
        if "candidate_id" in value and ("declared_layer" in value or "declared_semantics" in value):
            matches.append(value)
        for child in value.values():
            matches.extend(iter_declared_objects(child))
        return matches
    if isinstance(value, list):
        matches = []
        for child in value:
            matches.extend(iter_declared_objects(child))
        return matches
    return []


def collect_contextual_objects(path: Path, data: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    declared: list[dict[str, Any]] = []
    aligned: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if "raw_drafts" in data or "aligned_candidates" in data:
            declared.extend(iter_declared_objects(data.get("raw_drafts")))
            aligned.extend(iter_declared_objects(data.get("aligned_candidates")))
            return declared, aligned
    objects = iter_declared_objects(data)
    if "raw" in path.parts or "draft" in path.name:
        declared.extend(objects)
    else:
        aligned.extend(objects)
    return declared, aligned


def declared_layer_of(item: dict[str, Any]) -> str:
    if isinstance(item.get("declared_semantics"), dict):
        value = item["declared_semantics"].get("declared_layer")
        if value:
            return str(value)
    return str(item.get("declared_layer", ""))


def object_type_of(item: dict[str, Any]) -> str:
    if isinstance(item.get("declared_semantics"), dict):
        value = item["declared_semantics"].get("object_type")
        if value:
            return str(value)
    return str(item.get("object_type", ""))


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    declared_by_candidate: dict[str, dict[str, Any]] = {}
    aligned_by_candidate: dict[str, dict[str, Any]] = {}
    for path in paths:
        data = load_structured(path)
        declared_items, aligned_items = collect_contextual_objects(path, data)
        for item in declared_items:
            candidate_id = str(item.get("candidate_id", ""))
            if not candidate_id:
                findings.append(Finding("KIG_DECLARED_SEMANTICS_ID_MISSING", str(path), "declared semantics item lacks candidate_id"))
                continue
            declared_by_candidate[candidate_id] = item
        for item in aligned_items:
            candidate_id = str(item.get("candidate_id", ""))
            if not candidate_id:
                findings.append(Finding("KIG_DECLARED_SEMANTICS_ID_MISSING", str(path), "aligned semantics item lacks candidate_id"))
                continue
            aligned_by_candidate[candidate_id] = item
    for candidate_id, raw_item in declared_by_candidate.items():
        aligned_item = aligned_by_candidate.get(candidate_id)
        if aligned_item is None:
            findings.append(
                Finding("KIG_DECLARED_SEMANTICS_ALIGNMENT_MISSING", "<workspace>", "raw declared item lacks aligned candidate", candidate_id)
            )
            continue
        raw_layer = declared_layer_of(raw_item)
        aligned_layer = declared_layer_of(aligned_item)
        if raw_layer and aligned_layer and raw_layer != aligned_layer:
            findings.append(
                Finding(
                    "KIG_DECLARED_LAYER_CHANGED",
                    "<workspace>",
                    f"declared_layer changed from {raw_layer} to {aligned_layer}",
                    candidate_id,
                )
            )
        raw_type = object_type_of(raw_item)
        aligned_type = object_type_of(aligned_item)
        if raw_type and aligned_type and raw_type != aligned_type:
            findings.append(
                Finding("KIG_DECLARED_OBJECT_TYPE_CHANGED", "<workspace>", f"object_type changed from {raw_type} to {aligned_type}", candidate_id)
            )
        mapping = aligned_item.get("field_mapping")
        enum_alignment = aligned_item.get("enum_alignment")
        if not isinstance(mapping, dict) or not mapping:
            findings.append(Finding("KIG_FIELD_MAPPING_MISSING", "<workspace>", "aligned candidate lacks field_mapping", candidate_id))
        if not isinstance(enum_alignment, dict) or not enum_alignment:
            findings.append(Finding("KIG_ENUM_ALIGNMENT_MISSING", "<workspace>", "aligned candidate lacks enum_alignment", candidate_id))
    return findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_declared_semantics_alignment.yaml")
    negative = Path("fixtures/gkb_intake/negative/declared_semantics_mismatch.yaml")
    return not check_paths([positive]) and bool(check_paths([negative]))


def main() -> int:
    args = parse_args()
    files = iter_data_files(args.root, SCANNED_DIRS)
    findings = check_paths(files)
    result = build_result(GATE_ID, len(files), findings)
    if args.selftest and not run_selftest():
        result = build_result(
            GATE_ID,
            len(files),
            findings
            + [
                Finding(
                    code="KIG_SELFTEST_FAILED",
                    path="fixtures/gkb_intake",
                    message="declared semantics positive fixture must pass and mismatch fixture must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
