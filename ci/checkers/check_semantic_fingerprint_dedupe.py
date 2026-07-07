#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from gkb_intake_common import Finding, build_result, emit_result, iter_candidate_objects, iter_csv_files, iter_data_files, load_csv_rows, load_structured

GATE_ID = "check_semantic_fingerprint_dedupe"
SCANNED_DIRS = ("04_aligned_candidates", "07_fingerprints")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate semantic fingerprints are present and unresolved duplicates are blocked.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def duplicate_status(candidate: dict[str, object]) -> str:
    control = candidate.get("duplicate_control")
    if isinstance(control, dict):
        return str(control.get("status", "")).lower()
    return str(candidate.get("duplicate_status", "")).lower()


def collect_candidates(paths: list[Path]) -> tuple[dict[str, dict[str, list[str]]], list[Finding]]:
    fingerprints: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    findings: list[Finding] = []
    for path in paths:
        for candidate in iter_candidate_objects(load_structured(path)):
            candidate_id = str(candidate.get("candidate_id", "<missing>"))
            fingerprint = str(candidate.get("semantic_fingerprint", "")).strip()
            if not fingerprint:
                findings.append(Finding("KIG_SEMANTIC_FINGERPRINT_MISSING", str(path), "candidate lacks semantic_fingerprint", candidate_id))
                continue
            fingerprints[fingerprint][candidate_id].append(duplicate_status(candidate))
    return fingerprints, findings


def collect_registry(paths: list[Path]) -> tuple[dict[str, dict[str, list[str]]], list[Finding]]:
    fingerprints: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    findings: list[Finding] = []
    for path in paths:
        for row in load_csv_rows(path):
            fingerprint = (row.get("semantic_fingerprint") or "").strip()
            if not fingerprint:
                continue
            candidate_id = row.get("candidate_id") or "<missing>"
            status = (row.get("status") or row.get("conflict_status") or "").lower()
            fingerprints[fingerprint][candidate_id].append(status)
    return fingerprints, findings


def unresolved(status: str) -> bool:
    return status in {"", "unchecked", "unresolved", "conflict_unresolved"}


def check_root(root: Path) -> tuple[int, list[Finding]]:
    data_files = iter_data_files(root, ("04_aligned_candidates",))
    csv_files = iter_csv_files(root, ("07_fingerprints",))
    fingerprints, findings = collect_candidates(data_files)
    registry, registry_findings = collect_registry(csv_files)
    findings.extend(registry_findings)
    for fingerprint, entries_by_candidate in registry.items():
        for candidate_id, statuses in entries_by_candidate.items():
            fingerprints[fingerprint][candidate_id].extend(statuses)
    for fingerprint, entries_by_candidate in fingerprints.items():
        if len(entries_by_candidate) > 1 and any(
            unresolved(status) for statuses in entries_by_candidate.values() for status in statuses
        ):
            joined = ", ".join(sorted(entries_by_candidate))
            findings.append(
                Finding(
                    "KIG_DUPLICATE_UNRESOLVED",
                    "<workspace>",
                    f"duplicate semantic_fingerprint {fingerprint!r} is assigned to multiple candidates: {joined}",
                )
            )
    return len(data_files) + len(csv_files), findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_fingerprint_registry.yaml")
    negative = Path("fixtures/gkb_intake/negative/duplicate_fingerprint.yaml")
    positive_fingerprints, positive_findings = collect_candidates([positive])
    negative_fingerprints, negative_findings = collect_candidates([negative])
    for fingerprint, entries_by_candidate in positive_fingerprints.items():
        if len(entries_by_candidate) > 1 and any(
            unresolved(status) for statuses in entries_by_candidate.values() for status in statuses
        ):
            positive_findings.append(Finding("KIG_DUPLICATE_UNRESOLVED", str(positive), fingerprint))
    for fingerprint, entries_by_candidate in negative_fingerprints.items():
        if len(entries_by_candidate) > 1 and any(
            unresolved(status) for statuses in entries_by_candidate.values() for status in statuses
        ):
            negative_findings.append(Finding("KIG_DUPLICATE_UNRESOLVED", str(negative), fingerprint))
    return not positive_findings and bool(negative_findings)


def main() -> int:
    args = parse_args()
    checked_files, findings = check_root(args.root)
    result = build_result(GATE_ID, checked_files, findings)
    if args.selftest and not run_selftest():
        result = build_result(
            GATE_ID,
            checked_files,
            findings
            + [
                Finding(
                    code="KIG_SELFTEST_FAILED",
                    path="fixtures/gkb_intake",
                    message="fingerprint positive fixture must pass and duplicate fixture must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
