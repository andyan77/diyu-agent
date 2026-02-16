#!/usr/bin/env python3
"""DIYU Agent Phase gate verification.

Reads exit criteria from delivery/milestone-matrix.yaml and runs each check.
Outputs JSON evidence for CI archiving.

Usage:
    python3 scripts/verify_phase.py --phase 0 --json
    python3 scripts/verify_phase.py --current --json

Exit codes:
    0 - Go (all hard criteria passed)
    1 - Blocked (one or more hard criteria failed)
    2 - Configuration error
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

UTC = timezone.utc  # noqa: UP017 -- compat with Python <3.11 runtime

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")


@dataclass
class CriterionResult:
    id: str
    status: str  # PASS, FAIL, SKIP, ERROR
    duration_ms: int = 0
    error: str | None = None
    reason: str | None = None


@dataclass
class PhaseReport:
    phase: str
    timestamp: str = ""
    results: dict[str, list[dict]] = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "results": self.results,
            "summary": self.summary,
        }


def _run_check(check_cmd: str) -> CriterionResult:
    """Execute a single check command and return result."""
    start = time.monotonic()
    try:
        result = subprocess.run(  # noqa: S603 -- check_cmd from trusted YAML config
            shlex.split(check_cmd),
            shell=False,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path.cwd(),
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        if result.returncode == 0:
            return CriterionResult(id="", status="PASS", duration_ms=duration_ms)
        return CriterionResult(
            id="",
            status="FAIL",
            duration_ms=duration_ms,
            error=result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}",
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CriterionResult(id="", status="ERROR", duration_ms=duration_ms, error="timeout")
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return CriterionResult(id="", status="ERROR", duration_ms=duration_ms, error=str(e))


def verify_phase(phase_key: str, matrix: dict) -> PhaseReport:
    """Verify all exit criteria for a given phase."""
    report = PhaseReport(
        phase=phase_key,
        timestamp=datetime.now(UTC).isoformat(),
    )

    phases = matrix.get("phases", {})
    phase_data = phases.get(phase_key)
    if phase_data is None:
        report.summary = {"error": f"Phase '{phase_key}' not found in matrix"}
        return report

    exit_criteria = phase_data.get("exit_criteria", {})
    hard_results: list[dict] = []
    soft_results: list[dict] = []

    # Check hard criteria
    for criterion in exit_criteria.get("hard", []):
        cid = criterion["id"]
        check_cmd = criterion["check"]
        result = _run_check(check_cmd)
        result.id = cid
        hard_results.append(
            {
                "id": cid,
                "status": result.status,
                "duration_ms": result.duration_ms,
                **({"error": result.error} if result.error else {}),
            }
        )

    # Check soft criteria
    for criterion in exit_criteria.get("soft", []):
        cid = criterion["id"]
        check_cmd = criterion["check"]
        result = _run_check(check_cmd)
        result.id = cid
        entry: dict = {
            "id": cid,
            "status": result.status,
            "duration_ms": result.duration_ms,
        }
        if result.status == "FAIL":
            entry["status"] = "SKIP"
            entry["reason"] = result.error or "soft criterion not met"
        soft_results.append(entry)

    report.results = {"hard": hard_results, "soft": soft_results}

    # Compute summary
    hard_total = len(hard_results)
    hard_pass = sum(1 for r in hard_results if r["status"] == "PASS")
    hard_fail = hard_total - hard_pass
    soft_total = len(soft_results)
    soft_pass = sum(1 for r in soft_results if r["status"] == "PASS")
    soft_skip = sum(1 for r in soft_results if r["status"] == "SKIP")
    pass_rate = hard_pass / hard_total if hard_total > 0 else 1.0

    go_no_go_config = phase_data.get("go_no_go", {})
    required_rate = go_no_go_config.get("hard_pass_rate", 1.0)
    is_go = pass_rate >= required_rate

    blocking_items = [r["id"] for r in hard_results if r["status"] != "PASS"]

    report.summary = {
        "hard_total": hard_total,
        "hard_pass": hard_pass,
        "hard_fail": hard_fail,
        "soft_total": soft_total,
        "soft_pass": soft_pass,
        "soft_skip": soft_skip,
        "pass_rate": round(pass_rate, 4),
        "go_no_go": "GO" if is_go else "BLOCKED",
        "blocking_items": blocking_items,
    }

    return report


def load_matrix() -> dict:
    """Load the milestone matrix YAML."""
    if not MATRIX_PATH.exists():
        print(f"ERROR: {MATRIX_PATH} not found", file=sys.stderr)
        sys.exit(2)
    with open(MATRIX_PATH) as f:
        return yaml.safe_load(f)


def archive_report(report: PhaseReport, evidence_dir: Path | None = None) -> Path:
    """Archive a phase report to evidence/ directory. GAP-M6."""
    if evidence_dir is None:
        # Normalize phase_N -> phase-N for consistent directory naming
        dir_name = report.phase.replace("_", "-")
        evidence_dir = Path("evidence") / dir_name
    evidence_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    filename = f"verify-{report.phase}-{ts}.json"
    out_path = evidence_dir / filename
    with open(out_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    return out_path


def main() -> None:
    use_json = "--json" in sys.argv
    use_archive = "--archive" in sys.argv
    phase_arg = None
    use_current = "--current" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--phase" and i + 1 < len(sys.argv):
            phase_arg = sys.argv[i + 1]
            break

    if phase_arg is None and not use_current:
        print("Usage: verify_phase.py --phase N [--json] [--archive]", file=sys.stderr)
        print("       verify_phase.py --current [--json] [--archive]", file=sys.stderr)
        sys.exit(2)

    matrix = load_matrix()

    phase_key = matrix.get("current_phase", "phase_0") if use_current else f"phase_{phase_arg}"

    report = verify_phase(phase_key, matrix)

    # GAP-M6: archive to evidence/ if requested
    if use_archive:
        archive_path = archive_report(report)
        print(f"Archived: {archive_path}", file=sys.stderr)

    if use_json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Phase: {report.phase}")
        print(f"Timestamp: {report.timestamp}")
        print()
        for category in ["hard", "soft"]:
            results = report.results.get(category, [])
            if results:
                print(f"  [{category.upper()}]")
                for r in results:
                    icon = {"PASS": "OK", "FAIL": "FAIL", "SKIP": "SKIP", "ERROR": "ERR"}
                    status = icon.get(r["status"], r["status"])
                    print(f"    [{status:4s}] {r['id']} ({r['duration_ms']}ms)")
                    if r.get("error"):
                        print(f"           {r['error']}")
                    if r.get("reason"):
                        print(f"           {r['reason']}")
        print()
        s = report.summary
        print(f"  Hard: {s.get('hard_pass', 0)}/{s.get('hard_total', 0)} passed")
        print(f"  Soft: {s.get('soft_pass', 0)}/{s.get('soft_total', 0)} passed")
        print(f"  Go/No-Go: {s.get('go_no_go', 'UNKNOWN')}")
        if s.get("blocking_items"):
            print(f"  Blocking: {', '.join(s['blocking_items'])}")

    go_no_go = report.summary.get("go_no_go", "BLOCKED")
    sys.exit(0 if go_no_go == "GO" else 1)


if __name__ == "__main__":
    main()
