#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gkb_intake_common import Finding, READINESS_FLAGS, build_result, emit_result, is_true, iter_data_files, load_structured, walk

GATE_ID = "check_no_readiness_leak"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fail if readiness, production, release, or generation flags are true.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        data = load_structured(path)
        for key, value, location in walk(data):
            if key in READINESS_FLAGS and is_true(value):
                findings.append(
                    Finding(
                        code="KIG_READINESS_LEAK",
                        path=str(path),
                        location=location,
                        message=f"{key} is true",
                    )
                )
    return findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_candidate_with_source_anchor.yaml")
    negative = Path("fixtures/gkb_intake/negative/readiness_true.yaml")
    return not check_paths([positive]) and bool(check_paths([negative]))


def main() -> int:
    args = parse_args()
    files = iter_data_files(args.root)
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
                    message="positive fixture must pass and negative readiness fixture must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
