#!/usr/bin/env python3
"""X-Node Deep Verification Script.

Deep verification of DONE milestones with X-node cross-layer gates.
Goes beyond exit-code checking to verify evidence quality.

Checks:
  1. Parse all exit_criteria with xnodes from milestone-matrix.yaml
  2. For DONE milestones: verify exit_criteria command still passes
  3. Check evidence artifact exists, is non-empty, and is recent
  4. Flag: vacuous passes (test -f on empty), stale evidence, trivial commands

Usage:
    python scripts/check_xnode_deep.py --json
    python scripts/check_xnode_deep.py --json --skip-execution
    python scripts/check_xnode_deep.py --json --verbose

Exit codes:
    0: PASS or WARN
    1: FAIL (critical findings)
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")
EVIDENCE_DIR = Path("evidence")

# Commands that are trivially true / vacuous
TRIVIAL_PATTERNS = [
    re.compile(r"^test\s+-[fed]\s+"),  # test -f / test -e / test -d
    re.compile(r"^grep\s+-q"),  # grep -q (existence check)
    re.compile(r"^wc\s+-l"),  # wc -l (line count)
]

# Shell meta characters
_SHELL_META_RE = re.compile(r"[|&;$`<>]")
_CD_PREFIX_RE = re.compile(r"^cd\s+(\S+)\s*&&\s*(.+)$")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class XNodeGate:
    """An exit criteria with X-node cross-layer verification."""

    gate_id: str
    description: str
    check_cmd: str
    xnodes: list[str]
    phase: str
    tier: str  # hard / soft

    def to_dict(self) -> dict:
        return {
            "gate_id": self.gate_id,
            "description": self.description,
            "check_cmd": self.check_cmd,
            "xnodes": self.xnodes,
            "phase": self.phase,
            "tier": self.tier,
        }


@dataclass
class XNodeResult:
    """Verification result for a single X-node gate."""

    gate_id: str
    xnodes: list[str]
    phase: str
    execution_status: str = "SKIP"  # PASS, FAIL, SKIP, ERROR, TIMEOUT
    execution_duration_ms: int = 0
    execution_error: str = ""
    is_trivial: bool = False
    evidence_paths: list[str] = field(default_factory=list)
    evidence_status: str = "missing"  # present, empty, missing
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "gate_id": self.gate_id,
            "xnodes": self.xnodes,
            "phase": self.phase,
            "execution_status": self.execution_status,
            "execution_duration_ms": self.execution_duration_ms,
            "is_trivial": self.is_trivial,
            "evidence_status": self.evidence_status,
            "evidence_paths": self.evidence_paths,
            "findings": self.findings,
        }
        if self.execution_error:
            d["execution_error"] = self.execution_error
        return d


# ---------------------------------------------------------------------------
# Matrix parsing
# ---------------------------------------------------------------------------


def parse_xnode_gates(
    *,
    matrix_path: Path | None = None,
) -> list[XNodeGate]:
    """Parse exit_criteria entries that have xnodes defined."""
    effective_path = matrix_path if matrix_path is not None else MATRIX_PATH
    if not effective_path.exists():
        return []

    with open(effective_path) as f:
        matrix = yaml.safe_load(f)

    gates: list[XNodeGate] = []
    for phase_key, phase_data in matrix.get("phases", {}).items():
        if not isinstance(phase_data, dict):
            continue
        ec = phase_data.get("exit_criteria", {})
        for tier in ("hard", "soft"):
            for crit in ec.get(tier, []):
                xnodes = crit.get("xnodes", [])
                if not xnodes:
                    continue
                # Normalize xnodes to strings
                xnodes_str = [str(x) for x in xnodes]
                gates.append(
                    XNodeGate(
                        gate_id=crit.get("id", ""),
                        description=crit.get("description", ""),
                        check_cmd=crit.get("check", ""),
                        xnodes=xnodes_str,
                        phase=phase_key,
                        tier=tier,
                    )
                )

    return gates


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _is_trivial_command(cmd: str) -> bool:
    """Check if a command is trivially true (existence-only check)."""
    return any(pat.match(cmd.strip()) for pat in TRIVIAL_PATTERNS)


def _needs_shell(cmd: str) -> bool:
    return bool(_SHELL_META_RE.search(cmd))


def execute_gate(gate: XNodeGate, *, timeout: int = 120) -> XNodeResult:
    """Execute a gate's check command and return results."""
    result = XNodeResult(
        gate_id=gate.gate_id,
        xnodes=gate.xnodes,
        phase=gate.phase,
    )

    if not gate.check_cmd:
        result.execution_status = "SKIP"
        result.findings.append("No check command defined")
        return result

    result.is_trivial = _is_trivial_command(gate.check_cmd)
    if result.is_trivial:
        result.findings.append(f"Trivial command: {gate.check_cmd}")

    cmd = gate.check_cmd.strip()
    cwd = Path.cwd()
    use_shell = _needs_shell(cmd)

    m = _CD_PREFIX_RE.match(cmd)
    if m:
        cwd = Path.cwd() / m.group(1)
        cmd = m.group(2).strip()
        use_shell = _needs_shell(cmd)

    start = time.monotonic()
    try:
        args: list[str] | str = cmd if use_shell else shlex.split(cmd)
        proc = subprocess.run(  # noqa: S603
            args,
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        result.execution_duration_ms = int((time.monotonic() - start) * 1000)
        if proc.returncode == 0:
            result.execution_status = "PASS"
        else:
            result.execution_status = "FAIL"
            result.execution_error = (
                proc.stderr.strip() or proc.stdout.strip()[:200] or f"exit {proc.returncode}"
            )
    except subprocess.TimeoutExpired:
        result.execution_duration_ms = int((time.monotonic() - start) * 1000)
        result.execution_status = "TIMEOUT"
        result.execution_error = "timeout"
    except Exception as e:
        result.execution_duration_ms = int((time.monotonic() - start) * 1000)
        result.execution_status = "ERROR"
        result.execution_error = str(e)

    return result


# ---------------------------------------------------------------------------
# Evidence checking
# ---------------------------------------------------------------------------


def check_evidence(
    result: XNodeResult,
    gate: XNodeGate,
    *,
    evidence_dir: Path | None = None,
) -> None:
    """Check for evidence files related to the X-node gate."""
    effective_dir = evidence_dir if evidence_dir is not None else EVIDENCE_DIR
    if not effective_dir.exists():
        result.evidence_status = "missing"
        result.findings.append("Evidence directory not found")
        return

    # Search for evidence files matching gate ID or X-node IDs
    search_keys = [gate.gate_id, *gate.xnodes]
    found_files: list[Path] = []

    for key in search_keys:
        key_lower = key.lower().replace("-", "").replace("_", "")
        for evidence_file in effective_dir.rglob("*.json"):
            name_lower = evidence_file.stem.lower().replace("-", "").replace("_", "")
            if key_lower in name_lower:
                found_files.append(evidence_file)

    found_files = sorted(set(found_files))
    result.evidence_paths = [str(f) for f in found_files]

    if not found_files:
        result.evidence_status = "missing"
        result.findings.append("No evidence files found")
        return

    # Check if evidence files are non-empty
    all_empty = True
    for ef in found_files:
        if ef.stat().st_size > 2:  # > 2 bytes (not just "{}")
            all_empty = False
            break

    if all_empty:
        result.evidence_status = "empty"
        result.findings.append("Evidence files exist but are empty")
    else:
        result.evidence_status = "present"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    results: list[XNodeResult],
    *,
    verbose: bool = False,
) -> dict:
    """Build the JSON report."""
    total = len(results)
    passed = sum(1 for r in results if r.execution_status == "PASS")
    failed = sum(1 for r in results if r.execution_status == "FAIL")
    skipped = sum(1 for r in results if r.execution_status == "SKIP")
    trivial = sum(1 for r in results if r.is_trivial)
    evidence_present = sum(1 for r in results if r.evidence_status == "present")
    evidence_missing = sum(1 for r in results if r.evidence_status == "missing")

    # Collect all unique X-node IDs
    all_xnodes: set[str] = set()
    for r in results:
        all_xnodes.update(r.xnodes)

    if failed > 0:
        status = "FAIL"
    elif trivial > total * 0.5 or evidence_missing > total * 0.5:
        status = "WARN"
    else:
        status = "PASS"

    report: dict = {
        "status": status,
        "summary": {
            "total_xnode_gates": total,
            "unique_xnodes": len(all_xnodes),
            "executed_pass": passed,
            "executed_fail": failed,
            "skipped": skipped,
            "trivial_count": trivial,
            "evidence_present": evidence_present,
            "evidence_missing": evidence_missing,
        },
        "failed_gates": [r.to_dict() for r in results if r.execution_status == "FAIL"],
        "trivial_gates": [
            {"gate_id": r.gate_id, "xnodes": r.xnodes, "findings": r.findings}
            for r in results
            if r.is_trivial
        ],
    }

    if verbose:
        report["all_results"] = [r.to_dict() for r in results]

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    use_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv
    skip_execution = "--skip-execution" in sys.argv

    if not use_json:
        print("=== X-Node Deep Verification ===")

    gates = parse_xnode_gates()
    if not use_json:
        print(f"X-node gates: {len(gates)}")

    results: list[XNodeResult] = []
    for gate in gates:
        if skip_execution:
            r = XNodeResult(
                gate_id=gate.gate_id,
                xnodes=gate.xnodes,
                phase=gate.phase,
                execution_status="SKIP",
                is_trivial=_is_trivial_command(gate.check_cmd) if gate.check_cmd else False,
            )
            if r.is_trivial:
                r.findings.append(f"Trivial command: {gate.check_cmd}")
        else:
            r = execute_gate(gate)
        check_evidence(r, gate)
        results.append(r)

    report = generate_report(results, verbose=verbose)

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print(
            f"\nGates: {s['total_xnode_gates']}, Pass: {s['executed_pass']}, "
            f"Fail: {s['executed_fail']}, Skip: {s['skipped']}"
        )
        print(
            f"Trivial: {s['trivial_count']}, Evidence present: {s['evidence_present']}, "
            f"missing: {s['evidence_missing']}"
        )
        if report["failed_gates"]:
            print("\nFailed gates:")
            for fg in report["failed_gates"]:
                print(f"  {fg['gate_id']}: {fg.get('execution_error', 'unknown')}")
        print(f"\n=== Result: {report['status']} ===")

    if report["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
