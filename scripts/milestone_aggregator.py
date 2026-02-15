#!/usr/bin/env python3
"""Milestone aggregator: summarise milestone coverage per phase.

Reads delivery/milestone-matrix.yaml, counts milestones per layer per phase,
and optionally cross-references task-card directories for traceability.

Usage:
    python3 scripts/milestone_aggregator.py          # human-readable
    python3 scripts/milestone_aggregator.py --json   # JSON output
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import yaml

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")


def load_matrix() -> dict:
    if not MATRIX_PATH.exists():
        print(f"ERROR: {MATRIX_PATH} not found", file=sys.stderr)
        sys.exit(2)
    with MATRIX_PATH.open() as f:
        return yaml.safe_load(f)


def aggregate(data: dict) -> list[dict]:
    """Return per-phase summary with layer breakdown."""
    results = []
    phases = data.get("phases", {})
    for phase_key in sorted(phases):
        phase = phases[phase_key]
        milestones = phase.get("milestones", [])
        layer_counts: Counter[str] = Counter()
        for m in milestones:
            layer_counts[m.get("layer", "unknown")] += 1

        exit_hard = len(phase.get("exit_criteria", {}).get("hard", []))
        exit_soft = len(phase.get("exit_criteria", {}).get("soft", []))

        results.append(
            {
                "phase": phase_key,
                "name": phase.get("name", ""),
                "total_milestones": len(milestones),
                "by_layer": dict(sorted(layer_counts.items())),
                "exit_criteria_hard": exit_hard,
                "exit_criteria_soft": exit_soft,
            }
        )
    return results


def print_human(results: list[dict]) -> None:
    print("=== Milestone Aggregation Report ===\n")
    grand_total = 0
    for r in results:
        grand_total += r["total_milestones"]
        print(f"  {r['phase']}: {r['name']}")
        print(
            f"    Milestones: {r['total_milestones']}  "
            f"(exit: {r['exit_criteria_hard']} hard + "
            f"{r['exit_criteria_soft']} soft)"
        )
        if r["by_layer"]:
            layers = ", ".join(f"{k}={v}" for k, v in r["by_layer"].items())
            print(f"    Layers: {layers}")
        print()
    print(f"  Grand Total: {grand_total} milestones across {len(results)} phases")


def main() -> None:
    json_mode = "--json" in sys.argv
    data = load_matrix()
    results = aggregate(data)

    if json_mode:
        output = {
            "schema_version": data.get("schema_version", "1.0"),
            "current_phase": data.get("current_phase", "unknown"),
            "phases": results,
            "grand_total": sum(r["total_milestones"] for r in results),
        }
        json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print_human(results)


if __name__ == "__main__":
    main()
