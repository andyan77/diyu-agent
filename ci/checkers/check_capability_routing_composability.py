#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from gkb_intake_common import Finding, build_result, emit_result, iter_candidate_objects, iter_data_files, load_structured

GATE_ID = "check_capability_routing_composability"
SCANNED_DIRS = ("04_aligned_candidates", "08_outbox")
CAPABILITY_ID_PATTERN = re.compile(r"^P0-\d{2}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate capability refs and consumption hints.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def has_effect_hint(candidate: dict[str, Any]) -> bool:
    for key in ("capability_consumption_hint", "output_effect"):
        container = candidate.get(key)
        if not isinstance(container, dict):
            continue
        if container.get("affects") or container.get("likely_output_assets") or container.get("checker_need"):
            return True
    return False


def check_candidate(path: Path, candidate: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    candidate_id = str(candidate.get("candidate_id", "<missing>"))
    refs = candidate.get("capability_group_refs")
    if not isinstance(refs, list) or not refs:
        findings.append(Finding("KIG_CAPABILITY_ROUTE_MISSING", str(path), "missing capability_group_refs", candidate_id))
    else:
        for ref in refs:
            if not isinstance(ref, str) or not CAPABILITY_ID_PATTERN.match(ref):
                findings.append(Finding("KIG_CAPABILITY_REF_INVALID", str(path), f"invalid capability ref: {ref}", candidate_id))
    if not isinstance(candidate.get("capability_consumption_hint"), dict):
        findings.append(Finding("KIG_CAPABILITY_HINT_MISSING", str(path), "missing capability_consumption_hint", candidate_id))
    if not has_effect_hint(candidate):
        findings.append(
            Finding(
                "KIG_CAPABILITY_EFFECT_MISSING",
                str(path),
                "missing affects, likely_output_assets, or checker_need in capability_consumption_hint/output_effect",
                candidate_id,
            )
        )
    return findings


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        for candidate in iter_candidate_objects(load_structured(path)):
            findings.extend(check_candidate(path, candidate))
    return findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_candidate_with_source_anchor.yaml")
    negative = Path("fixtures/gkb_intake/negative/missing_capability_consumption_hint.yaml")
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
                    message="positive candidate fixture must pass and missing capability fixture must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
