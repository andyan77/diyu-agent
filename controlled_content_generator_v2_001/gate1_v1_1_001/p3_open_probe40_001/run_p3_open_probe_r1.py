#!/usr/bin/env python3
"""Deterministic successor entrypoint for the single repaired P3 run."""

from __future__ import annotations

import argparse
import json
import sys

from p3_common import P3ValidationError, canonical_json
from p3_final_r1 import check_final, materialize_final
from p3_open_r1 import check_all_r1 as check_open_r1
from p3_repair import check as check_repair
from p3_review_r1 import load_and_validate_reports


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-evidence", action="store_true")
    group.add_argument("--validate-reviews", action="store_true")
    group.add_argument("--finalize", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_evidence:
            check_repair()
            check_open_r1()
            payload: dict[str, object] = {"status": "P3_R1_EVIDENCE_PASS"}
        elif args.validate_reviews:
            one, two = load_and_validate_reports()
            payload = {
                "status": "P3_R1_REVIEWS_VALID",
                "review_one_score": one["p3_score"],
                "review_two_score": two["p3_score"],
            }
        elif args.finalize:
            payload = {
                "status": "P3_R1_FINALIZED",
                "changed": [path.as_posix() for path in materialize_final()],
            }
        else:
            check_final()
            payload = {"status": "PASS", "phase": "P3_R1_FINAL"}
    except (OSError, KeyError, TypeError, ValueError, P3ValidationError) as exc:
        sys.stderr.write(canonical_json({"status": "FAIL", "error": str(exc)}) + "\n")
        return 1
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
