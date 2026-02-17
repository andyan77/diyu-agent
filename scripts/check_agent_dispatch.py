#!/usr/bin/env python3
"""Audit agent dispatch completeness for Phase 2 workflows.

Compares required agent_dispatch entries from workflow YAML against
actual dispatch evidence in the JSONL log file.

This is an AUDIT ASSIST tool (warns on gaps), not a security gate.
WF2-A2 invokes this as the final dispatch completeness check.

Usage:
    uv run python scripts/check_agent_dispatch.py \
        evidence/v4-phase2/agent-dispatch.jsonl \
        delivery/v4-phase2-workflows.yaml

    uv run python scripts/check_agent_dispatch.py --json \
        evidence/v4-phase2/agent-dispatch.jsonl \
        delivery/v4-phase2-workflows.yaml

Exit codes:
    0 - All required dispatches have evidence
    1 - Missing dispatch evidence detected
    2 - Usage error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def load_required_dispatches(workflow_path: Path) -> list[dict[str, str]]:
    """Extract all required agent dispatches from workflow YAML."""
    with workflow_path.open() as f:
        data = yaml.safe_load(f)

    required: list[dict[str, str]] = []
    for wf in data.get("workflows", []):
        wf_id = wf.get("id", "")
        for dispatch in wf.get("agent_dispatch", []):
            agent = dispatch.get("agent", "")
            scope = dispatch.get("scope", "all cards")
            required.append(
                {
                    "workflow": wf_id,
                    "agent": agent,
                    "scope": scope,
                }
            )
    return required


def load_actual_dispatches(jsonl_path: Path) -> list[dict]:
    """Load dispatch evidence from JSONL file."""
    if not jsonl_path.exists():
        return []

    dispatches: list[dict] = []
    for line in jsonl_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            dispatches.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return dispatches


def check_completeness(
    required: list[dict[str, str]],
    actual: list[dict],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return (covered, missing) lists."""
    # Build a set of (workflow, agent) pairs from actual evidence
    actual_pairs = set()
    for d in actual:
        wf = d.get("workflow", "")
        agent = d.get("agent", "")
        actual_pairs.add((wf, agent))

    covered: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []

    for req in required:
        key = (req["workflow"], req["agent"])
        if key in actual_pairs:
            covered.append(req)
        else:
            missing.append(req)

    return covered, missing


def main() -> None:
    args = sys.argv[1:]
    json_output = "--json" in args
    positional = [a for a in args if not a.startswith("--")]

    if len(positional) != 2:
        print(
            "Usage: check_agent_dispatch.py [--json] <dispatch.jsonl> <workflows.yaml>",
            file=sys.stderr,
        )
        sys.exit(2)

    jsonl_path = Path(positional[0])
    workflow_path = Path(positional[1])

    if not workflow_path.exists():
        print(f"ERROR: {workflow_path} not found", file=sys.stderr)
        sys.exit(2)

    required = load_required_dispatches(workflow_path)
    actual = load_actual_dispatches(jsonl_path)
    covered, missing = check_completeness(required, actual)

    if json_output:
        print(
            json.dumps(
                {
                    "tool": "check_agent_dispatch",
                    "jsonl_file": str(jsonl_path),
                    "workflow_file": str(workflow_path),
                    "required_count": len(required),
                    "covered_count": len(covered),
                    "missing_count": len(missing),
                    "missing": missing,
                    "status": "fail" if missing else "pass",
                },
                indent=2,
            )
        )
    else:
        total = len(required)
        print(f"Agent Dispatch Audit: {len(covered)}/{total} dispatches have evidence\n")

        if missing:
            print(f"WARN: {len(missing)} missing dispatch(es):\n")
            for m in missing:
                print(f"  [{m['workflow']}] {m['agent']} (scope: {m['scope']})")
            print(f"\nExpected evidence in: {jsonl_path}")
        else:
            print("All required agent dispatches have evidence.")

        if not jsonl_path.exists():
            print(f"\nNOTE: {jsonl_path} does not exist yet (no dispatches logged).")

    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
