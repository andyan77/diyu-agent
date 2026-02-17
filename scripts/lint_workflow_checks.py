#!/usr/bin/env python3
"""Validate that workflow check commands use only whitelisted prefixes.

Prevents accidental introduction of arbitrary shell commands in workflow YAML.
All check `cmd` values must start with one of the approved prefixes.

Usage:
    uv run python scripts/lint_workflow_checks.py delivery/v4-phase2-workflows.yaml
    uv run python scripts/lint_workflow_checks.py --json delivery/v4-phase2-workflows.yaml

Exit codes:
    0 - All checks use whitelisted prefixes
    1 - Unauthorized commands detected
    2 - Usage error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

# Whitelisted command prefixes. A check `cmd` must start with one of these.
ALLOWED_PREFIXES = [
    "uv run pytest",
    "uv run python scripts/",
    "uv run mypy",
    "uv run ruff",
    "bash scripts/",
    "bash .claude/skills/",
    "cd frontend && pnpm",
    "cd frontend && node",
    "docker compose exec postgres",
    "docker compose exec redis",
    "make lint",
    "make test",
    "make audit",
]


def validate_workflow_file(filepath: Path) -> list[dict[str, str]]:
    if not filepath.exists():
        return [{"workflow": "-", "desc": "-", "cmd": str(filepath), "reason": "file not found"}]

    with filepath.open() as f:
        data = yaml.safe_load(f)

    violations: list[dict[str, str]] = []
    for wf in data.get("workflows", []):
        wf_id = wf.get("id", "unknown")
        for check in wf.get("checks", []):
            cmd = check.get("cmd", "")
            desc = check.get("desc", "unnamed")
            if not cmd:
                continue

            allowed = any(cmd.startswith(prefix) for prefix in ALLOWED_PREFIXES)
            if not allowed:
                violations.append(
                    {
                        "workflow": wf_id,
                        "desc": desc,
                        "cmd": cmd,
                        "reason": "command prefix not in whitelist",
                    }
                )

    return violations


def main() -> None:
    args = sys.argv[1:]
    json_output = "--json" in args
    files = [a for a in args if not a.startswith("--")]

    if not files:
        print(
            "Usage: lint_workflow_checks.py [--json] <workflow.yaml>",
            file=sys.stderr,
        )
        sys.exit(2)

    all_violations: list[dict[str, str]] = []
    for f in files:
        all_violations.extend(validate_workflow_file(Path(f)))

    if json_output:
        print(
            json.dumps(
                {
                    "tool": "lint_workflow_checks",
                    "files": files,
                    "allowed_prefixes": ALLOWED_PREFIXES,
                    "violations": all_violations,
                    "count": len(all_violations),
                    "status": "fail" if all_violations else "pass",
                },
                indent=2,
            )
        )
    else:
        if all_violations:
            print(f"FAIL: {len(all_violations)} unauthorized command(s):\n")
            for v in all_violations:
                print(f"  [{v['workflow']}] {v['desc']}")
                print(f"    cmd: {v['cmd']}")
                print(f"    reason: {v['reason']}\n")
            print("Allowed prefixes:")
            for p in ALLOWED_PREFIXES:
                print(f"  - {p}")
        else:
            print(f"PASS: All workflow checks use whitelisted prefixes ({len(files)} file(s))")

    sys.exit(1 if all_violations else 0)


if __name__ == "__main__":
    main()
