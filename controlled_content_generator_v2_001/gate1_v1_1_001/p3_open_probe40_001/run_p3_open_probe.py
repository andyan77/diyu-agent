#!/usr/bin/env python3
"""Single deterministic entrypoint for the Gate 1 v1.1 P3 open probe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from p3_common import ROOT, P3ValidationError, canonical_json
from p3_final import check_final, materialize_final
from p3_open_core import (
    materialize_machine_report,
    materialize_route_actuals,
    materialize_route_comparisons,
    validate_positive_file,
)
from p3_prepare import check_prepare, materialize_prepare
from p3_review import load_and_validate_reports, materialize_review_packet
from p3_structure import check_structure, materialize_structure


def _paths(rows: list[Path]) -> list[str]:
    return [path.relative_to(ROOT).as_posix() for path in rows]


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument("--prepare", action="store_true")
    commands.add_argument("--check-prepare", action="store_true")
    commands.add_argument("--route-actuals", action="store_true")
    commands.add_argument("--route-compare", action="store_true")
    commands.add_argument("--validate-positive", action="store_true")
    commands.add_argument("--machine", action="store_true")
    commands.add_argument("--review-packet", action="store_true")
    commands.add_argument("--validate-reviews", action="store_true")
    commands.add_argument("--finalize", action="store_true")
    commands.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.prepare:
            changed = materialize_structure() + materialize_prepare()
            payload = {"status": "PREPARED", "changed": _paths(changed)}
        elif args.check_prepare:
            check_structure()
            check_prepare()
            payload = {"status": "PREPARE_PASS"}
        elif args.route_actuals:
            payload = {
                "status": "ROUTE_ACTUALS_FROZEN",
                "changed": _paths(materialize_route_actuals()),
            }
        elif args.route_compare:
            payload = {
                "status": "ROUTE_COMPARISON_FROZEN",
                "path": materialize_route_comparisons().relative_to(ROOT).as_posix(),
            }
        elif args.validate_positive:
            payload = {
                "status": "POSITIVE_OUTPUT_PASS",
                "count": len(validate_positive_file()),
            }
        elif args.machine:
            payload = {
                "status": "MACHINE_REPORT_MATERIALIZED",
                "path": materialize_machine_report().relative_to(ROOT).as_posix(),
            }
        elif args.review_packet:
            payload = {
                "status": "REVIEW_PACKET_MATERIALIZED",
                "changed": _paths(materialize_review_packet()),
            }
        elif args.validate_reviews:
            first, second = load_and_validate_reports()
            payload = {
                "status": "REVIEWS_PASS",
                "review_one_score": first["p3_score"],
                "review_two_score": second["p3_score"],
            }
        elif args.finalize:
            payload = {
                "status": "FINALIZED",
                "changed": _paths(materialize_final()),
            }
        else:
            check_final()
            payload = {"status": "PASS", "phase": "P3_FINAL"}
    except (OSError, KeyError, TypeError, ValueError, P3ValidationError) as exc:
        sys.stderr.write(canonical_json({"status": "FAIL", "error": str(exc)}) + "\n")
        return 1
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
