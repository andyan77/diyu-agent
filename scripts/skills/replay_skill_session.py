#!/usr/bin/env python3
"""Replay Skill Session - reads JSONL audit log and outputs step summaries.

Usage:
    # Replay the latest session
    python scripts/skills/replay_skill_session.py --latest

    # Replay a specific session file
    python scripts/skills/replay_skill_session.py --file .audit/skill-session-20260215T120000.jsonl

    # JSON output
    python scripts/skills/replay_skill_session.py --latest --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def find_latest_session() -> Path | None:
    """Find the most recent skill session log."""
    audit_dir = Path(".audit")
    if not audit_dir.exists():
        return None
    logs = sorted(audit_dir.glob("skill-session-*.jsonl"), reverse=True)
    return logs[0] if logs else None


def replay(log_path: Path, as_json: bool = False) -> dict:
    """Replay a session log and return summary."""
    if not log_path.exists():
        print(f"ERROR: Log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    entries = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARNING: Skipping malformed line: {e}", file=sys.stderr)

    if not entries:
        print(f"WARNING: No entries in {log_path}", file=sys.stderr)
        return {"file": str(log_path), "entries": 0, "steps": []}

    # Build summary
    steps = []
    for entry in entries:
        step_info = {
            "timestamp": entry.get("timestamp", "?"),
            "skill": entry.get("skill", "?"),
            "step": entry.get("step", "?"),
            "status": entry.get("status", "?"),
        }
        handoff = entry.get("handoff_files", {})
        if handoff:
            step_info["handoff_complete"] = all(
                handoff.get(k, False) for k in ["input", "output", "next_step"]
            )
        if entry.get("artifacts_dir"):
            step_info["artifacts_dir"] = entry["artifacts_dir"]
        steps.append(step_info)

    summary = {
        "file": str(log_path),
        "session_id": entries[0].get("session_id", "unknown"),
        "entries": len(entries),
        "steps": steps,
        "passed": sum(1 for s in steps if s["status"] == "pass"),
        "failed": sum(1 for s in steps if s["status"] == "fail"),
        "skipped": sum(1 for s in steps if s["status"] == "skip"),
    }

    if as_json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"Session: {summary['session_id']}")
        print(f"Log:     {summary['file']}")
        print(f"Steps:   {summary['entries']}")
        p, f, sk = summary["passed"], summary["failed"], summary["skipped"]
        print(f"Passed:  {p}  Failed: {f}  Skipped: {sk}")
        print()
        for s in steps:
            marker = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}.get(s["status"], "?")
            handoff = ""
            if "handoff_complete" in s:
                handoff = " [handoff OK]" if s["handoff_complete"] else " [handoff INCOMPLETE]"
            print(f"  [{marker}] {s['skill']}/{s['step']} @ {s['timestamp']}{handoff}")
            if s.get("artifacts_dir"):
                print(f"         artifacts: {s['artifacts_dir']}")
        print()
        overall = "PASS" if summary["failed"] == 0 and summary["entries"] > 0 else "FAIL"
        print(f"Overall: {overall}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay Skill Session")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="Replay latest session")
    group.add_argument("--file", type=Path, help="Replay specific session file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.latest:
        log_path = find_latest_session()
        if not log_path:
            print("No skill session logs found in .audit/", file=sys.stderr)
            sys.exit(1)
    else:
        log_path = args.file

    summary = replay(log_path, as_json=args.json)
    sys.exit(0 if summary.get("failed", 0) == 0 and summary.get("entries", 0) > 0 else 1)


if __name__ == "__main__":
    main()
