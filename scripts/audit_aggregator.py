#!/usr/bin/env python3
"""Aggregate .audit/ session JSONL files into a summary report.

Usage:
    python3 scripts/audit_aggregator.py .audit/
    python3 scripts/audit_aggregator.py .audit/ --json
"""

from __future__ import annotations

import contextlib
import json
import sys
from collections import Counter
from pathlib import Path


def load_entries(audit_dir: Path) -> list[dict]:
    entries: list[dict] = []
    for f in sorted(audit_dir.glob("session-*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            with contextlib.suppress(json.JSONDecodeError):
                entries.append(json.loads(line))
    return entries


def aggregate(entries: list[dict]) -> dict:
    files = Counter(e.get("file", "unknown") for e in entries)
    tools = Counter(e.get("tool", "unknown") for e in entries)
    governance_count = sum(1 for e in entries if e.get("governance"))
    sessions = {e.get("session", "no-session") for e in entries}
    # GAP-M1: flag any entries that still have unknown/no-session
    unknown_sessions = sum(
        1 for e in entries if e.get("session") in (None, "unknown", "no-session")
    )

    dates = sorted({e.get("timestamp", "")[:10] for e in entries if e.get("timestamp")})

    return {
        "total_entries": len(entries),
        "governance_entries": governance_count,
        "non_governance_entries": len(entries) - governance_count,
        "unique_files": len(files),
        "unique_sessions": len(sessions),
        "date_range": {"first": dates[0] if dates else None, "last": dates[-1] if dates else None},
        "top_files": dict(files.most_common(10)),
        "tool_breakdown": dict(tools),
        "unknown_session_count": unknown_sessions,
    }


def print_text_report(report: dict) -> None:
    print("=" * 60)
    print("  DIYU Agent Audit Report")
    print("=" * 60)
    print(f"  Total entries:       {report['total_entries']}")
    print(f"  Governance entries:  {report['governance_entries']}")
    print(f"  Non-governance:      {report['non_governance_entries']}")
    print(f"  Unique files:        {report['unique_files']}")
    print(f"  Unique sessions:     {report['unique_sessions']}")
    dr = report["date_range"]
    if dr["first"]:
        print(f"  Date range:          {dr['first']} .. {dr['last']}")
    else:
        print("  Date range:          (no data)")
    print()
    print("  Tool breakdown:")
    for tool, count in report["tool_breakdown"].items():
        print(f"    {tool:20s}  {count}")
    print()
    print("  Top 10 edited files:")
    for path, count in report["top_files"].items():
        print(f"    {count:4d}  {path}")
    print("=" * 60)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <audit-dir> [--json]", file=sys.stderr)
        sys.exit(1)

    audit_dir = Path(sys.argv[1])
    use_json = "--json" in sys.argv

    if not audit_dir.is_dir():
        print(f"ERROR: {audit_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    entries = load_entries(audit_dir)
    report = aggregate(entries)

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)


if __name__ == "__main__":
    main()
