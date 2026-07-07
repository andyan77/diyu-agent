#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gkb_intake_common import (
    Finding,
    build_result,
    emit_result,
    has_source_anchor,
    is_true,
    iter_candidate_objects,
    iter_data_files,
    load_structured,
)

GATE_ID = "check_source_anchor_coverage"
SCANNED_DIRS = ("03_raw_drafts", "04_aligned_candidates", "08_outbox")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fail when CandidatePack eligibility lacks source anchors.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        for candidate in iter_candidate_objects(load_structured(path)):
            candidate_id = str(candidate.get("candidate_id", "<missing>"))
            readiness = candidate.get("readiness") if isinstance(candidate.get("readiness"), dict) else {}
            eligibility = is_true(candidate.get("candidatepack_eligibility")) or is_true(readiness.get("candidatepack_ready"))
            if eligibility and not has_source_anchor(candidate):
                findings.append(
                    Finding(
                        code="KIG_SOURCE_ANCHOR_MISSING",
                        path=str(path),
                        object_id=candidate_id,
                        message="CandidatePack eligibility requires source_pack_refs, source_excerpt_refs, and excerpt_digests",
                    )
                )
            if candidate.get("source_origin") == "gpt_generated_candidate" and (
                is_true(readiness.get("production_ready")) or is_true(readiness.get("RAG_ready"))
            ):
                findings.append(
                    Finding(
                        code="KIG_GPT_OUTPUT_CLAIMS_RUNTIME_READINESS",
                        path=str(path),
                        object_id=candidate_id,
                        message="gpt_generated_candidate cannot claim production_ready or RAG_ready",
                    )
                )
    return findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_candidate_with_source_anchor.yaml")
    negative = Path("fixtures/gkb_intake/negative/missing_source_anchor.yaml")
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
                    message="positive fixture must pass and missing source anchor fixture must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
