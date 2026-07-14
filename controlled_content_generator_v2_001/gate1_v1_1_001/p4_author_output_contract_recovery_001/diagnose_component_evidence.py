#!/usr/bin/env python3
"""Report eligible author-owned component evidence pointers without changing output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from author_contract import (
    ROLE_ALLOWED_SURFACE_KINDS,
    canonical_json,
    read_jsonl,
    write_jsonl,
)


if not __debug__:
    sys.stderr.write("diagnose_component_evidence refuses python -O\n")
    raise SystemExit(2)


def diagnose(requests_path: Path, raws_path: Path) -> list[dict[str, Any]]:
    requests = {row["request_id"]: row for row in read_jsonl(requests_path)}
    rows: list[dict[str, Any]] = []
    for raw in read_jsonl(raws_path):
        request = requests[raw["request_id"]]
        components = {row["component_id"]: row for row in request["approved_components"]}
        core_fact_ids = {
            fact_id
            for requirement in request["product_core_requirements"]
            for fact_id in requirement["fact_ids"]
        }
        fact_slots = {
            fact["fact_id"]: fact["slot_id"] for fact in request["typed_material"]["facts"]
        }
        usage_by_id = {
            row["component_id"]: row for row in raw["semantic_component_usage"]
        }
        for component_id, component in components.items():
            usage = usage_by_id[component_id]
            allowed_fact_ids = core_fact_ids | {
                fact_id
                for fact_id, slot_id in fact_slots.items()
                if slot_id in component.get("required_fact_slots", [])
            }
            allowed_kinds = set(
                ROLE_ALLOWED_SURFACE_KINDS[component["component_role"]]
            )
            eligible = [
                index
                for index, surface in enumerate(raw["semantic_surfaces"], 1)
                if surface["surface_kind"] in allowed_kinds
                and allowed_fact_ids.intersection(surface["fact_ids"])
            ]
            current = list(usage["surface_ordinals"])
            satisfied = bool(set(current).intersection(eligible))
            rows.append(
                {
                    "request_id": raw["request_id"],
                    "profile_id": request["profile_id"],
                    "component_id": component_id,
                    "component_role": component["component_role"],
                    "current_surface_ordinals": current,
                    "eligible_surface_ordinals": eligible,
                    "evidence_rule_satisfied": satisfied,
                    "diagnostic_only_no_output_mutation": True,
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--raws", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = diagnose(args.requests, args.raws)
        write_jsonl(args.output, rows)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        sys.stderr.write(f"FAIL {exc}\n")
        return 1
    failed = sum(not row["evidence_rule_satisfied"] for row in rows)
    print(canonical_json({"status": "PASS", "component_count": len(rows), "unsatisfied_count": failed}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
