#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gkb_intake_common import Finding, build_result, emit_result, is_true, iter_data_files, load_structured, walk

GATE_ID = "check_serving_spec_no_passage_text"
SCANNED_DIRS = ("09_serving_specs",)
FORBIDDEN_KEYS = {"approved_passage_text", "rendered_body", "passage_text", "context_bundle_item"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure serving spec candidates do not contain generated passage text.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        data = load_structured(path)
        for key, value, location in walk(data):
            if key in FORBIDDEN_KEYS:
                findings.append(Finding("KIG_SERVING_TEXT_GENERATED", str(path), f"forbidden serving text key present: {key}", location=location))
            if key == "passage_text_generated" and is_true(value):
                findings.append(Finding("KIG_SERVING_TEXT_GENERATED", str(path), "passage_text_generated is true", location=location))
    return findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_serving_spec_candidate.yaml")
    negative = Path("fixtures/gkb_intake/negative/serving_passage_text_generated.yaml")
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
                    message="serving spec positive fixture must pass and generated passage fixture must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
