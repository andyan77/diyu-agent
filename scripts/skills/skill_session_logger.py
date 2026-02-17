#!/usr/bin/env python3
"""Skill Session Logger - writes JSONL audit entries for skill executions.

Usage:
    # Log a skill step
    python scripts/skills/skill_session_logger.py \\
        --skill taskcard-governance --step W1 --status pass \\
        --artifacts evidence/skills/taskcard-governance/20260215T120000/W1/

    # Log from environment (used by run_all.sh)
    SESSION_ID=20260215T120000 python scripts/skills/skill_session_logger.py \\
        --skill taskcard-governance --step W1 --status pass

Output:
    Appends one JSONL line to .audit/skill-session-<timestamp>.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def get_session_log_path() -> Path:
    """Determine the session log file path."""
    audit_dir = Path(".audit")
    audit_dir.mkdir(exist_ok=True)

    # Use SESSION_ID env var or generate from current time
    session_id = os.environ.get("SESSION_ID", datetime.now().strftime("%Y%m%dT%H%M%S"))
    return audit_dir / f"skill-session-{session_id}.jsonl"


def log_step(
    skill: str,
    step: str,
    status: str,
    artifacts_dir: str | None = None,
    details: dict | None = None,
) -> Path:
    """Append a step entry to the session JSONL log."""
    log_path = get_session_log_path()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017 - runs on system Python 3.10
        "skill": skill,
        "step": step,
        "status": status,
        "session_id": os.environ.get("SESSION_ID", "unknown"),
    }

    if artifacts_dir:
        entry["artifacts_dir"] = artifacts_dir
        # Check which handoff files exist
        art_path = Path(artifacts_dir)
        entry["handoff_files"] = {
            "input": (art_path / "input.json").exists(),
            "output": (art_path / "output.json").exists(),
            "failure": (art_path / "failure.md").exists(),
            "next_step": (art_path / "next-step.md").exists(),
        }

    if details:
        entry["details"] = details

    with open(log_path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return log_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill Session Logger")
    parser.add_argument("--skill", required=True, help="Skill name")
    parser.add_argument("--step", required=True, help="Step name (e.g., W1, W2)")
    parser.add_argument(
        "--status", required=True, choices=["pass", "fail", "skip"], help="Step result"
    )
    parser.add_argument("--artifacts", default=None, help="Path to artifacts directory")
    parser.add_argument("--detail", default=None, help="JSON string with extra details")
    args = parser.parse_args()

    details = json.loads(args.detail) if args.detail else None
    log_path = log_step(args.skill, args.step, args.status, args.artifacts, details)
    print(f"Logged: {args.skill}/{args.step} -> {args.status} in {log_path}")


if __name__ == "__main__":
    main()
