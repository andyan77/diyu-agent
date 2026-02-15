#!/usr/bin/env python3
"""Workflow role enforcement -- GAP-M2.

Validates that WORKFLOW_ROLE matches the expected step.
Used by run_w*.sh scripts to prevent cross-step execution.

Usage:
    python3 scripts/enforce_workflow_role.py --expected W1 --actual "$WORKFLOW_ROLE"

Exit codes:
    0: role matches
    1: role mismatch (script should abort)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_ROLES = {"W1", "W2", "W3", "W4"}
UTC = timezone.utc


def main() -> None:
    expected = None
    actual = None
    session_id = "unknown"
    log_dir = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--expected" and i + 1 < len(args):
            expected = args[i + 1]
            i += 2
        elif args[i] == "--actual" and i + 1 < len(args):
            actual = args[i + 1]
            i += 2
        elif args[i] == "--session" and i + 1 < len(args):
            session_id = args[i + 1]
            i += 2
        elif args[i] == "--log-dir" and i + 1 < len(args):
            log_dir = Path(args[i + 1])
            i += 2
        else:
            i += 1

    if not expected or not actual:
        msg = "Usage: enforce_workflow_role.py --expected W1 --actual $WORKFLOW_ROLE"
        print(msg, file=sys.stderr)
        sys.exit(1)

    if expected not in VALID_ROLES:
        print(f"ERROR: invalid expected role '{expected}' (valid: {VALID_ROLES})", file=sys.stderr)
        sys.exit(1)

    match = actual == expected

    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "role_check",
        "expected": expected,
        "actual": actual,
        "match": match,
        "session": session_id,
    }

    # Log to session log if log_dir provided
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"role-enforcement-{session_id}.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    if not match:
        print(
            f"ROLE MISMATCH: expected={expected} actual={actual} session={session_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
