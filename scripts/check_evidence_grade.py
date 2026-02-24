#!/usr/bin/env python3
"""Evidence Grade Classification Script.

Grades evidence quality for every gate exit_criteria using A-F taxonomy:
  A: Runtime-verified (integration test with real DB + actual HTTP calls, or E2E)
  B: Integration-tested (docker-compose + pytest with real services)
  C: Unit-tested (isolated pytest with mocks/fixtures)
  D: Static-verified (AST/grep/file-existence/`test -f` check only)
  F: No evidence (gate exists in milestone-matrix but no test or check)

Parses milestone-matrix.yaml exit_criteria commands and classifies each
by analyzing what it actually executes.

Usage:
    python scripts/check_evidence_grade.py --json
    python scripts/check_evidence_grade.py --json --verbose
    python scripts/check_evidence_grade.py --json --phase 2

Exit codes:
    0: PASS (all criteria graded)
    1: FAIL (configuration error)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")
TESTS_DIR = Path("tests")

# Patterns to classify evidence grade
# A: E2E or integration with real services
_GRADE_A_PATTERNS = [
    re.compile(r"tests/e2e/"),
    re.compile(r"playwright\s+test"),
    re.compile(r"tests/integration/.*test_.*integration"),
    re.compile(r"--.*real.*service"),
]

# B: Integration tests (pytest with service containers)
_GRADE_B_PATTERNS = [
    re.compile(r"tests/integration/"),
    re.compile(r"tests/isolation/"),
    re.compile(r"tests/perf/"),
]

# C: Unit tests (pytest with mocks)
_GRADE_C_PATTERNS = [
    re.compile(r"pytest\s+tests/unit/"),
    re.compile(r"pytest\s+tests/"),
    re.compile(r"pnpm\s+run\s+test"),
    re.compile(r"pnpm\s+--filter\s+\S+\s+run\s+test"),
]

# D: Static checks (grep, test -f, AST scan, lint)
_GRADE_D_PATTERNS = [
    re.compile(r"^test\s+-[fedrx]\s+"),
    re.compile(r"^grep\s+"),
    re.compile(r"^ls\s+"),
    re.compile(r"^wc\s+"),
    re.compile(r"ruff\s+check"),
    re.compile(r"ruff\s+format"),
    re.compile(r"pnpm\s+run\s+lint"),
    re.compile(r"pnpm\s+run\s+build"),
    re.compile(r"pnpm\s+run\s+typecheck"),
    re.compile(r"python.*import\s+"),
    re.compile(r"python.*assert\s+"),
    re.compile(r"python.*yaml\.safe_load"),
    re.compile(r"python.*json\.load"),
    re.compile(r"python.*tomllib\.load"),
    re.compile(r"^bash\s+scripts/check_"),
    re.compile(r"^bash\s+scripts/generate_sbom"),
    re.compile(r"^bash\s+scripts/security_scan"),
    re.compile(r"^bash\s+scripts/sign_sbom"),
    re.compile(r"^bash\s+scripts/drill_"),
    re.compile(r"^bash\s+scripts/check_openapi_sync"),
    re.compile(r"^bash\s+scripts/check_ssot_drift"),
    re.compile(r"^bash\s+scripts/check_ha_validation"),
    re.compile(r"^bash\s+scripts/diyu_diagnose"),
    re.compile(r"^bash\s+scripts/rotate_secrets"),
    re.compile(r"^python3?\s+scripts/check_"),
    re.compile(r"^uv\s+run\s+python\s+scripts/check_"),
    re.compile(r"make\s+lint"),
    re.compile(r"^node\s+scripts/"),
    re.compile(r"mypy\s+"),
    re.compile(r"lhci\s+autorun"),
    re.compile(r"axe-core"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GradedCriteria:
    """An exit criteria with its evidence grade."""

    phase: str
    criteria_id: str
    description: str
    check_command: str
    gate_type: str  # hard or soft
    grade: str  # A, B, C, D, F
    grade_reason: str
    xnodes: list[str]

    def to_dict(self) -> dict:
        d: dict = {
            "phase": self.phase,
            "criteria_id": self.criteria_id,
            "description": self.description,
            "check_command": self.check_command,
            "gate_type": self.gate_type,
            "grade": self.grade,
            "grade_reason": self.grade_reason,
        }
        if self.xnodes:
            d["xnodes"] = self.xnodes
        return d


# ---------------------------------------------------------------------------
# Grading logic
# ---------------------------------------------------------------------------


def classify_grade(check_command: str) -> tuple[str, str]:
    """Classify a check command into A-F evidence grade.

    Returns (grade, reason).
    """
    if not check_command or not check_command.strip():
        return "F", "Empty check command"

    cmd = check_command.strip()

    # Grade A: E2E or full integration
    for pattern in _GRADE_A_PATTERNS:
        if pattern.search(cmd):
            return "A", f"E2E/runtime-verified: matches '{pattern.pattern}'"

    # Grade B: Integration tests
    for pattern in _GRADE_B_PATTERNS:
        if pattern.search(cmd):
            return "B", f"Integration-tested: matches '{pattern.pattern}'"

    # Grade C: Unit tests
    for pattern in _GRADE_C_PATTERNS:
        if pattern.search(cmd):
            return "C", f"Unit-tested: matches '{pattern.pattern}'"

    # Grade D: Static checks
    for pattern in _GRADE_D_PATTERNS:
        if pattern.search(cmd):
            return "D", f"Static-verified: matches '{pattern.pattern}'"

    # If it runs pytest but we can't tell the type, assume C
    if "pytest" in cmd:
        return "C", "pytest detected but test type unclear"

    # Default to D for any scripted check
    if "scripts/" in cmd or "bash " in cmd or "python" in cmd:
        return "D", "Script-based check (assumed static)"

    return "F", f"Unclassifiable command: {cmd[:60]}"


def _parse_exit_criteria(
    phase_data: dict,
    phase_name: str,
) -> list[GradedCriteria]:
    """Parse exit_criteria from a phase and grade each."""
    results: list[GradedCriteria] = []

    ec = phase_data.get("exit_criteria", {})
    for gate_type in ("hard", "soft"):
        criteria_list = ec.get(gate_type, [])
        if not criteria_list:
            continue
        for item in criteria_list:
            cid = item.get("id", "unknown")
            desc = item.get("description", "")
            check = item.get("check", "")
            xnodes = item.get("xnodes", [])

            grade, reason = classify_grade(check)

            results.append(
                GradedCriteria(
                    phase=phase_name,
                    criteria_id=cid,
                    description=desc,
                    check_command=check,
                    gate_type=gate_type,
                    grade=grade,
                    grade_reason=reason,
                    xnodes=xnodes if isinstance(xnodes, list) else [],
                )
            )

    return results


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------


def analyze(
    *,
    matrix_path: Path | None = None,
    target_phase: str | None = None,
) -> list[GradedCriteria]:
    """Analyze all exit_criteria and grade them."""
    effective_path = matrix_path if matrix_path is not None else MATRIX_PATH

    if not effective_path.exists():
        return []

    with effective_path.open(encoding="utf-8") as f:
        matrix = yaml.safe_load(f)

    if not matrix or "phases" not in matrix:
        return []

    results: list[GradedCriteria] = []

    for phase_key, phase_data in matrix["phases"].items():
        if target_phase and phase_key != target_phase:
            continue
        results.extend(_parse_exit_criteria(phase_data, phase_key))

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    graded: list[GradedCriteria],
    *,
    verbose: bool = False,
) -> dict:
    """Build the JSON report with distribution histogram."""
    total = len(graded)

    # Distribution
    dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for g in graded:
        dist[g.grade] = dist.get(g.grade, 0) + 1

    # Per-phase distribution
    phase_dist: dict[str, dict[str, int]] = {}
    for g in graded:
        if g.phase not in phase_dist:
            phase_dist[g.phase] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        phase_dist[g.phase][g.grade] += 1

    # Calculate coverage rate (graded / total)
    classified = sum(1 for g in graded if g.grade != "F")
    coverage_pct = (classified / total * 100) if total > 0 else 0

    # Upgrade recommendations (D -> C, F -> D at minimum)
    upgrades: list[dict] = []
    for g in graded:
        if g.grade in ("D", "F"):
            rec = "Add unit test" if g.grade == "D" else "Add any verification"
            upgrades.append(
                {
                    "criteria_id": g.criteria_id,
                    "phase": g.phase,
                    "current_grade": g.grade,
                    "recommendation": rec,
                }
            )

    status = "PASS"  # grading itself always succeeds if matrix is parseable

    report: dict = {
        "status": status,
        "summary": {
            "total_criteria": total,
            "distribution": dist,
            "coverage_rate": round(coverage_pct, 1),
            "phase_distribution": phase_dist,
        },
        "upgrade_recommendations": upgrades[:20],  # cap to avoid noise
    }

    if verbose:
        report["all_criteria"] = [g.to_dict() for g in graded]

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    use_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv

    target_phase = None
    if "--phase" in sys.argv:
        idx = sys.argv.index("--phase")
        if idx + 1 < len(sys.argv):
            phase_arg = sys.argv[idx + 1]
            target_phase = f"phase_{phase_arg}" if not phase_arg.startswith("phase_") else phase_arg

    if not use_json:
        print("=== Evidence Grade Classification ===")

    graded = analyze(target_phase=target_phase)

    if not graded:
        if use_json:
            print(json.dumps({"status": "FAIL", "error": "No exit_criteria found"}, indent=2))
        else:
            print("ERROR: No exit_criteria found in milestone-matrix.yaml")
        sys.exit(1)

    report = generate_report(graded, verbose=verbose)

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        d = s["distribution"]
        print(f"\nTotal criteria: {s['total_criteria']}")
        print(f"Coverage rate: {s['coverage_rate']}%")
        print("\nGrade distribution:")
        for grade in ("A", "B", "C", "D", "F"):
            bar = "#" * d.get(grade, 0)
            print(f"  {grade}: {d.get(grade, 0):3d} {bar}")

        print("\nPer-phase distribution:")
        for phase, pdist in sorted(s["phase_distribution"].items()):
            grades_str = " ".join(f"{g}={c}" for g, c in sorted(pdist.items()) if c > 0)
            print(f"  {phase}: {grades_str}")

        if report["upgrade_recommendations"]:
            print(f"\nUpgrade recommendations ({len(report['upgrade_recommendations'])}):")
            for rec in report["upgrade_recommendations"][:10]:
                print(f"  {rec['criteria_id']} ({rec['current_grade']}): {rec['recommendation']}")

        print(f"\n=== Result: {report['status']} ===")

    if report["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
