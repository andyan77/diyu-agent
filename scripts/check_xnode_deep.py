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
    python scripts/check_xnode_deep.py --json --all-phases

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

# Ensure scripts/ root is importable for lib.xnode_utils
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.xnode_utils import load_xnode_registry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")
EVIDENCE_DIR = Path("evidence")
SRC_DIR = Path("src")

# Evidence older than this many hours is considered stale
STALE_THRESHOLD_HOURS = 168  # 7 days

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
    evidence_status: str = "missing"  # present, empty, missing, stale
    evidence_age_hours: float = -1  # hours since evidence last modified
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
            "evidence_age_hours": round(self.evidence_age_hours, 1),
            "findings": self.findings,
        }
        if self.execution_error:
            d["execution_error"] = self.execution_error
        return d


@dataclass
class XNodeVerification:
    """Per-X-node aggregated verification result."""

    node_id: str
    phase: str
    gate_ids: list[str] = field(default_factory=list)
    execution_status: str = "SKIP"  # best gate status
    evidence_path: str = ""
    evidence_age_hours: float = -1
    evidence_status: str = "missing"
    verdict: str = "unverified"  # pass, fail, stale, unverified
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "phase": self.phase,
            "gate_ids": self.gate_ids,
            "execution_status": self.execution_status,
            "evidence_path": self.evidence_path,
            "evidence_age_hours": round(self.evidence_age_hours, 1),
            "evidence_status": self.evidence_status,
            "verdict": self.verdict,
            "findings": self.findings,
        }


# ---------------------------------------------------------------------------
# Matrix parsing
# ---------------------------------------------------------------------------


def get_done_phases(matrix: dict) -> set[str]:
    """Return set of phase keys where ALL milestones have status='done'.

    Phase 0 milestones may lack an explicit status field (implicitly done
    if phase_1 depends on it and has been started).

    .. deprecated::
        Prefer registry-based filtering via ``done_only_registry``.
        Retained for backward compatibility with callers that do not yet
        use xnode_registry.
    """
    done_phases: set[str] = set()
    current = matrix.get("current_phase", "")

    for phase_key, phase_data in matrix.get("phases", {}).items():
        if not isinstance(phase_data, dict):
            continue
        milestones = phase_data.get("milestones", [])
        if not milestones:
            continue

        # A phase is done if all milestones have status="done"
        all_done = all(
            m.get("status", "").lower() == "done" for m in milestones if isinstance(m, dict)
        )
        # Phase 0 special case: milestones may lack status field if
        # the project has moved past phase 0
        if not all_done and phase_key == "phase_0" and current and current != "phase_0":
            all_done = True

        if all_done:
            done_phases.add(phase_key)

    return done_phases


def _get_done_xnode_ids(registry: dict[str, dict]) -> set[str]:
    """Return X-node IDs with guard_status='done' from registry."""
    return {
        xid
        for xid, entry in registry.items()
        if isinstance(entry, dict) and entry.get("guard_status") == "done"
    }


def parse_xnode_gates(
    *,
    matrix_path: Path | None = None,
    done_only: bool = False,
    done_only_registry: bool = False,
) -> list[XNodeGate]:
    """Parse exit_criteria entries that have xnodes defined.

    Args:
        matrix_path: Override path to milestone-matrix.yaml.
        done_only: If True, only return gates from phases where ALL
                   milestones have status='done' (legacy phase-level filter).
        done_only_registry: If True, only return gates whose ALL referenced
                            xnodes have guard_status='done' in xnode_registry.
                            This is the preferred X-node-level filter.
    """
    effective_path = matrix_path if matrix_path is not None else MATRIX_PATH
    if not effective_path.exists():
        return []

    with open(effective_path) as f:
        matrix = yaml.safe_load(f)

    done_phases = get_done_phases(matrix) if done_only else None

    # Registry-based filter
    done_xnode_ids: set[str] | None = None
    if done_only_registry:
        registry = matrix.get("xnode_registry", {})
        if not registry:
            registry = load_xnode_registry(matrix_path=effective_path)
        done_xnode_ids = _get_done_xnode_ids(registry)

    gates: list[XNodeGate] = []
    for phase_key, phase_data in matrix.get("phases", {}).items():
        if not isinstance(phase_data, dict):
            continue
        if done_phases is not None and phase_key not in done_phases:
            continue
        ec = phase_data.get("exit_criteria", {})
        for tier in ("hard", "soft"):
            for crit in ec.get(tier, []):
                xnodes = crit.get("xnodes", [])
                if not xnodes:
                    continue
                # Normalize xnodes to strings
                xnodes_str = [str(x) for x in xnodes]

                # Registry filter: skip gate if any referenced xnode is not done
                if done_xnode_ids is not None and not all(
                    xid in done_xnode_ids for xid in xnodes_str
                ):
                    continue

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


def _latest_src_mtime(*, src_dir: Path | None = None) -> float:
    """Return the most recent mtime among src/**/*.py files, or 0."""
    effective = src_dir if src_dir is not None else SRC_DIR
    if not effective.exists():
        return 0.0
    latest = 0.0
    for py in effective.rglob("*.py"):
        try:
            mt = py.stat().st_mtime
            if mt > latest:
                latest = mt
        except OSError:
            continue
    return latest


def check_evidence(
    result: XNodeResult,
    gate: XNodeGate,
    *,
    evidence_dir: Path | None = None,
    src_dir: Path | None = None,
    stale_threshold_hours: float | None = None,
) -> None:
    """Check for evidence files related to the X-node gate.

    Checks:
      - Evidence file exists and is non-empty
      - Evidence mtime vs latest src/ mtime (stale detection)
      - Evidence age in hours
    """
    effective_dir = evidence_dir if evidence_dir is not None else EVIDENCE_DIR
    threshold = (
        stale_threshold_hours if stale_threshold_hours is not None else STALE_THRESHOLD_HOURS
    )
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
    newest_mtime = 0.0
    for ef in found_files:
        try:
            st = ef.stat()
            if st.st_size > 2:  # > 2 bytes (not just "{}")
                all_empty = False
            if st.st_mtime > newest_mtime:
                newest_mtime = st.st_mtime
        except OSError:
            continue

    if all_empty:
        result.evidence_status = "empty"
        result.findings.append("Evidence files exist but are empty")
        return

    # Compute evidence age
    now = time.time()
    if newest_mtime > 0:
        result.evidence_age_hours = (now - newest_mtime) / 3600

    # Check stale: evidence older than threshold OR older than src/ changes
    src_mtime = _latest_src_mtime(src_dir=src_dir)
    if newest_mtime > 0 and src_mtime > 0 and newest_mtime < src_mtime:
        result.evidence_status = "stale"
        result.findings.append("Evidence is older than latest source code change")
    elif result.evidence_age_hours > threshold:
        result.evidence_status = "stale"
        result.findings.append(
            f"Evidence age ({result.evidence_age_hours:.0f}h) exceeds threshold ({threshold:.0f}h)"
        )
    else:
        result.evidence_status = "present"


# ---------------------------------------------------------------------------
# Per-X-node aggregation
# ---------------------------------------------------------------------------


_EXEC_STATUS_RANK = {"PASS": 0, "FAIL": 1, "TIMEOUT": 2, "ERROR": 3, "SKIP": 4}


def aggregate_per_node(results: list[XNodeResult]) -> list[XNodeVerification]:
    """Aggregate gate-level results into per-X-node verifications."""
    node_map: dict[str, XNodeVerification] = {}
    node_has_fail: dict[str, bool] = {}

    for r in results:
        for node_id in r.xnodes:
            if node_id not in node_map:
                node_map[node_id] = XNodeVerification(
                    node_id=node_id,
                    phase=r.phase,
                )
                node_has_fail[node_id] = False
            nv = node_map[node_id]
            nv.gate_ids.append(r.gate_id)

            # Track failures explicitly
            if r.execution_status == "FAIL":
                node_has_fail[node_id] = True

            # Best execution status (PASS > FAIL > TIMEOUT > ERROR > SKIP)
            cur_rank = _EXEC_STATUS_RANK.get(nv.execution_status, 99)
            new_rank = _EXEC_STATUS_RANK.get(r.execution_status, 99)
            if new_rank < cur_rank:
                nv.execution_status = r.execution_status

            # Evidence: take the best (present > stale > empty > missing)
            ev_rank = {"present": 0, "stale": 1, "empty": 2, "missing": 3}
            cur_ev = ev_rank.get(nv.evidence_status, 99)
            new_ev = ev_rank.get(r.evidence_status, 99)
            if new_ev < cur_ev:
                nv.evidence_status = r.evidence_status
                nv.evidence_age_hours = r.evidence_age_hours
                if r.evidence_paths:
                    nv.evidence_path = r.evidence_paths[0]

            nv.findings.extend(r.findings)

    # Determine verdict per node
    for node_id, nv in node_map.items():
        if node_has_fail[node_id]:
            nv.verdict = "fail"
        elif nv.evidence_status == "stale":
            nv.verdict = "stale"
        elif nv.evidence_status == "missing":
            nv.verdict = "unverified"
        elif nv.execution_status == "PASS" and nv.evidence_status == "present":
            nv.verdict = "pass"
        elif nv.execution_status == "SKIP":
            nv.verdict = "unverified"
        else:
            nv.verdict = "unverified"

    return sorted(node_map.values(), key=lambda v: v.node_id)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    results: list[XNodeResult],
    *,
    verbose: bool = False,
) -> dict:
    """Build the JSON report with per-X-node output."""
    total_gates = len(results)
    passed = sum(1 for r in results if r.execution_status == "PASS")
    failed = sum(1 for r in results if r.execution_status == "FAIL")
    skipped = sum(1 for r in results if r.execution_status == "SKIP")
    trivial = sum(1 for r in results if r.is_trivial)
    evidence_present = sum(1 for r in results if r.evidence_status == "present")
    evidence_missing = sum(1 for r in results if r.evidence_status == "missing")
    evidence_stale = sum(1 for r in results if r.evidence_status == "stale")

    # Per-node aggregation
    nodes = aggregate_per_node(results)

    node_pass = sum(1 for n in nodes if n.verdict == "pass")
    node_fail = sum(1 for n in nodes if n.verdict == "fail")
    node_stale = sum(1 for n in nodes if n.verdict == "stale")
    node_unverified = sum(1 for n in nodes if n.verdict == "unverified")

    if failed > 0 or node_fail > 0:
        status = "FAIL"
    elif (
        node_stale > 0
        or evidence_stale > 0
        or trivial > total_gates * 0.5
        or evidence_missing > total_gates * 0.5
    ):
        status = "WARN"
    else:
        status = "PASS"

    report: dict = {
        "status": status,
        "summary": {
            "total_xnode_gates": total_gates,
            "unique_xnodes": len(nodes),
            "executed_pass": passed,
            "executed_fail": failed,
            "skipped": skipped,
            "trivial_count": trivial,
            "evidence_present": evidence_present,
            "evidence_missing": evidence_missing,
            "evidence_stale": evidence_stale,
            "node_pass": node_pass,
            "node_fail": node_fail,
            "node_stale": node_stale,
            "node_unverified": node_unverified,
        },
        "nodes": [n.to_dict() for n in nodes],
        "failed_gates": [r.to_dict() for r in results if r.execution_status == "FAIL"],
        "trivial_gates": [
            {
                "gate_id": r.gate_id,
                "xnodes": r.xnodes,
                "findings": r.findings,
            }
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
    all_phases = "--all-phases" in sys.argv

    if not use_json:
        print("=== X-Node Deep Verification ===")

    # Default: filter to X-nodes with guard_status='done' (registry-based).
    # --all-phases: include all gates regardless of status.
    gates = parse_xnode_gates(done_only_registry=not all_phases)
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
            f"Trivial: {s['trivial_count']}, "
            f"Evidence: present={s['evidence_present']}, "
            f"missing={s['evidence_missing']}, stale={s['evidence_stale']}"
        )
        print(
            f"\nX-Nodes: {s['unique_xnodes']} total, "
            f"pass={s['node_pass']}, fail={s['node_fail']}, "
            f"stale={s['node_stale']}, unverified={s['node_unverified']}"
        )
        for node in report["nodes"]:
            marker = {"pass": "+", "fail": "!", "stale": "~", "unverified": "?"}
            m = marker.get(node["verdict"], "?")
            print(
                f"  [{m}] {node['node_id']}: "
                f"{node['verdict']} "
                f"(evidence={node['evidence_status']}, "
                f"age={node['evidence_age_hours']}h)"
            )
        if report["failed_gates"]:
            print("\nFailed gates:")
            for fg in report["failed_gates"]:
                err = fg.get("execution_error", "unknown")
                print(f"  {fg['gate_id']}: {err}")
        print(f"\n=== Result: {report['status']} ===")

    if report["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
