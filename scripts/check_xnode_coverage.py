#!/usr/bin/env python3
"""Cross-layer XNode Coverage Check.

Validates that X/XF/XM verification nodes from milestone-matrix-crosscutting.md
Section 4 are covered by exit_criteria xnodes fields in milestone-matrix.yaml.

Dual-metric output:
  - direct_coverage: explicit xnodes field matches (structural binding)
  - semantic_coverage: direct + deterministic path-prefix heuristic (advisory only)

When --verify-results is passed, adds result_coverage:
  - result_coverage: xnodes whose ALL bound gates actually PASS when executed
  - Gate decision uses result_coverage instead of direct_coverage

Usage:
    python3 scripts/check_xnode_coverage.py --phase N [--json]
    python3 scripts/check_xnode_coverage.py --phase N --verify-results [--json]
    python3 scripts/check_xnode_coverage.py --current [--json]
    python3 scripts/check_xnode_coverage.py --all [--json]

Exit codes:
    0 - Coverage meets threshold (or --all mode, which never blocks)
    1 - Coverage below threshold
    2 - Configuration error
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

UTC = timezone.utc  # noqa: UP017 -- compat with Python <3.11 runtime

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")
CROSSCUTTING_PATH = Path("docs/governance/milestone-matrix-crosscutting.md")

XNODE_RE = re.compile(r"\|\s*(X[FM]?\d+-\d+)\s*\|")
PHASE_RE = re.compile(r"^###\s+4\.(\d+)\s+Phase\s+(\d+)")


def load_xnodes_by_phase(
    *,
    crosscutting_path: Path | None = None,
) -> dict[int, list[str]]:
    """Extract X/XF/XM node IDs grouped by phase from crosscutting.md Section 4."""
    path = crosscutting_path or CROSSCUTTING_PATH
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(2)

    result: dict[int, list[str]] = {}
    current_phase: int | None = None
    in_section4 = False

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## 4."):
            in_section4 = True
        elif line.startswith("## ") and not line.startswith("## 4.") and in_section4:
            break

        if not in_section4:
            continue

        phase_match = PHASE_RE.match(line)
        if phase_match:
            current_phase = int(phase_match.group(2))
            if current_phase not in result:
                result[current_phase] = []

        if current_phase is not None:
            for m in XNODE_RE.finditer(line):
                node_id = m.group(1)
                if node_id not in result[current_phase]:
                    result[current_phase].append(node_id)

    return result


def load_yaml_data(
    *,
    matrix_path: Path | None = None,
) -> dict:
    """Load milestone-matrix.yaml."""
    path = matrix_path or MATRIX_PATH
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(2)
    with path.open() as f:
        return yaml.safe_load(f)


def get_phase_xnode_bindings(yaml_data: dict, phase_key: str) -> dict[str, list[str]]:
    """Extract xnode bindings from a phase's exit_criteria.

    Returns: {node_id: [criterion_ids...]}
    """
    bindings: dict[str, list[str]] = {}
    phase = yaml_data.get("phases", {}).get(phase_key, {})
    for level in ("hard", "soft"):
        criteria = phase.get("exit_criteria", {}).get(level, []) or []
        for criterion in criteria:
            crit_id = criterion.get("id", "")
            for node_id in criterion.get("xnodes", []):
                bindings.setdefault(node_id, []).append(crit_id)
    return bindings


SEMANTIC_RULES = [
    {
        "name": "path_prefix",
        "description": "check command test path shares prefix with node verification method path",
    },
]


def _extract_test_path(check_cmd: str) -> str | None:
    """Extract test file path from check command."""
    patterns = [
        r"pytest\s+(tests/\S+)",
        r"playwright\s+test\s+(tests/\S+)",
        r"bash\s+(scripts/\S+)",
    ]
    for p in patterns:
        m = re.search(p, check_cmd)
        if m:
            return m.group(1)
    return None


def semantic_match(yaml_data: dict, phase_key: str, missing_nodes: list[str]) -> list[dict]:
    """Apply deterministic semantic rules to find additional coverage."""
    additional = []
    phase = yaml_data.get("phases", {}).get(phase_key, {})
    criteria = []
    for level in ("hard", "soft"):
        criteria.extend(phase.get("exit_criteria", {}).get(level, []) or [])

    for node_id in missing_nodes:
        node_lower = node_id.lower().replace("-", "_")
        for criterion in criteria:
            check_cmd = criterion.get("check", "")
            test_path = _extract_test_path(check_cmd)
            if test_path and node_lower in test_path.lower().replace("-", "_"):
                additional.append(
                    {
                        "node": node_id,
                        "matched_check": criterion.get("id", ""),
                        "rule": "path_prefix",
                    }
                )
                break
    return additional


def get_untagged_checks(yaml_data: dict, phase_key: str) -> list[str]:
    """Find criteria that have check commands but no xnodes field."""
    untagged = []
    phase = yaml_data.get("phases", {}).get(phase_key, {})
    for level in ("hard", "soft"):
        criteria = phase.get("exit_criteria", {}).get(level, []) or []
        for criterion in criteria:
            if criterion.get("check") and not criterion.get("xnodes"):
                untagged.append(criterion.get("id", ""))
    return untagged


_CD_PREFIX_RE = re.compile(r"^cd\s+(\S+)\s*&&\s*(.+)$")
_SHELL_META_RE = re.compile(r"[|&;$`<>]")


def _needs_shell(cmd: str) -> bool:
    """Detect whether a command requires shell interpretation."""
    return bool(_SHELL_META_RE.search(cmd))


def _run_gate_check(check_cmd: str) -> tuple[bool, int]:
    """Execute a single gate check command. Returns (passed, duration_ms)."""
    cmd = check_cmd.strip()
    cwd = Path.cwd()
    use_shell = _needs_shell(cmd)

    m = _CD_PREFIX_RE.match(cmd)
    if m:
        cwd = Path.cwd() / m.group(1)
        cmd = m.group(2).strip()
        use_shell = _needs_shell(cmd)

    args: list[str] | str = cmd if use_shell else shlex.split(cmd)
    start = time.monotonic()
    try:
        result = subprocess.run(  # noqa: S603 -- commands from trusted milestone-matrix.yaml
            args,
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=cwd,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return result.returncode == 0, duration_ms
    except (subprocess.TimeoutExpired, Exception):
        duration_ms = int((time.monotonic() - start) * 1000)
        return False, duration_ms


def run_gate_checks(
    yaml_data: dict,
    phase_key: str,
    gate_ids: set[str],
) -> dict[str, dict]:
    """Execute specified gate check commands and return results.

    Returns: {gate_id: {"passed": bool, "duration_ms": int}}
    """
    results: dict[str, dict] = {}
    phase = yaml_data.get("phases", {}).get(phase_key, {})
    for level in ("hard", "soft"):
        criteria = phase.get("exit_criteria", {}).get(level, []) or []
        for criterion in criteria:
            crit_id = criterion.get("id", "")
            if crit_id not in gate_ids:
                continue
            check_cmd = criterion.get("check", "")
            if not check_cmd:
                results[crit_id] = {"passed": False, "duration_ms": 0}
                continue
            passed, duration_ms = _run_gate_check(check_cmd)
            results[crit_id] = {"passed": passed, "duration_ms": duration_ms}
    return results


def check_phase(
    yaml_data: dict,
    xnodes_by_phase: dict[int, list[str]],
    phase_num: int,
    *,
    verify_results: bool = False,
) -> dict:
    """Check xnode coverage for a single phase.

    When verify_results=True, also executes bound gate checks and computes
    result_coverage: only xnodes whose ALL bound gates PASS count as covered.
    Gate decision uses result_coverage instead of direct_coverage.
    """
    phase_key = f"phase_{phase_num}"
    phase_nodes = xnodes_by_phase.get(phase_num, [])
    bindings = get_phase_xnode_bindings(yaml_data, phase_key)

    covered = sorted(n for n in phase_nodes if n in bindings)
    missing = sorted(n for n in phase_nodes if n not in bindings)

    total = len(phase_nodes)
    direct_rate = len(covered) / total if total > 0 else 0.0

    # Semantic coverage
    sem_additional = semantic_match(yaml_data, phase_key, missing)
    sem_covered_ids = {item["node"] for item in sem_additional}
    sem_total_covered = len(covered) + len(sem_covered_ids)
    sem_rate = sem_total_covered / total if total > 0 else 0.0

    # Orphan xnodes: referenced in YAML but not defined in crosscutting
    all_defined = set()
    for nodes in xnodes_by_phase.values():
        all_defined.update(nodes)
    yaml_xnodes = set(bindings.keys())
    orphan_xnodes = sorted(yaml_xnodes - all_defined)

    untagged = get_untagged_checks(yaml_data, phase_key)

    # Threshold from go_no_go
    go_no_go = yaml_data.get("phases", {}).get(phase_key, {}).get("go_no_go", {})
    threshold = go_no_go.get("xnode_coverage_min")

    # Result coverage: execute gate checks and verify xnodes pass
    result_coverage_data: dict | None = None
    effective_rate = direct_rate  # default: use structural binding rate

    if verify_results and covered:
        # Collect all gate IDs bound to covered xnodes
        all_gate_ids: set[str] = set()
        for node_id in covered:
            all_gate_ids.update(bindings.get(node_id, []))

        # Execute gate checks
        print(
            f"  Executing {len(all_gate_ids)} gate checks for result coverage...", file=sys.stderr
        )
        gate_results = run_gate_checks(yaml_data, phase_key, all_gate_ids)

        # Determine which xnodes have ALL bound gates passing
        result_covered = []
        result_failed = []
        node_details: list[dict] = []
        for node_id in covered:
            bound_gates = bindings.get(node_id, [])
            all_pass = all(gate_results.get(gid, {}).get("passed", False) for gid in bound_gates)
            detail = {
                "node": node_id,
                "bound_gates": bound_gates,
                "gate_results": {
                    gid: gate_results.get(gid, {"passed": False, "duration_ms": 0})
                    for gid in bound_gates
                },
                "all_pass": all_pass,
            }
            node_details.append(detail)
            if all_pass:
                result_covered.append(node_id)
            else:
                result_failed.append(node_id)

        result_rate = len(result_covered) / total if total > 0 else 0.0
        effective_rate = result_rate  # use result rate for gate decision

        result_coverage_data = {
            "rate": round(result_rate, 4),
            "covered": sorted(result_covered),
            "failed": sorted(result_failed),
            "unbound": missing,  # same as direct_coverage.missing
            "node_details": node_details,
        }

    gate_decision = "NO-THRESHOLD"
    basis = "result" if verify_results and covered else "direct"
    if threshold is not None:
        gate_decision = "GO" if effective_rate >= threshold else "NO-GO"
    elif total > 0:
        print(
            f"WARN: {phase_key} has {total} xnodes but no xnode_coverage_min threshold",
            file=sys.stderr,
        )

    report: dict = {
        "phase": phase_key,
        "timestamp": datetime.now(UTC).isoformat(),
        "nodes": {
            "total": total,
            "phase_nodes": sorted(phase_nodes),
        },
        "direct_coverage": {
            "rate": round(direct_rate, 4),
            "covered": covered,
            "missing": missing,
        },
        "semantic_coverage": {
            "rate": round(sem_rate, 4),
            "additional": sem_additional,
            "rules_applied": list({item["rule"] for item in sem_additional}),
        },
        "validation": {
            "orphan_xnodes": orphan_xnodes,
            "untagged_checks": untagged,
        },
        "gate": {
            "threshold": threshold,
            "decision": gate_decision,
            "basis": basis,
        },
    }

    if result_coverage_data is not None:
        report["result_coverage"] = result_coverage_data

    return report


def main() -> None:
    json_mode = "--json" in sys.argv
    all_mode = "--all" in sys.argv
    current_mode = "--current" in sys.argv
    verify_results = "--verify-results" in sys.argv
    phase_num: int | None = None

    if "--phase" in sys.argv:
        idx = sys.argv.index("--phase")
        if idx + 1 < len(sys.argv):
            try:
                phase_num = int(sys.argv[idx + 1])
            except ValueError:
                print("ERROR: --phase requires integer", file=sys.stderr)
                sys.exit(2)

    yaml_data = load_yaml_data()
    xnodes_by_phase = load_xnodes_by_phase()

    if all_mode:
        # --all: informational only, NEVER blocks
        reports = []
        for p in sorted(xnodes_by_phase.keys()):
            report = check_phase(
                yaml_data,
                xnodes_by_phase,
                p,
                verify_results=verify_results,
            )
            reports.append(report)
        if json_mode:
            print(json.dumps(reports, indent=2, ensure_ascii=False))
        else:
            for r in reports:
                dc = r["direct_coverage"]
                sc = r["semantic_coverage"]
                g = r["gate"]
                rc = r.get("result_coverage")
                line = f"{r['phase']}: direct={dc['rate']:.0%} semantic={sc['rate']:.0%} "
                if rc:
                    line += f"result={rc['rate']:.0%} "
                line += f"threshold={g['threshold']} decision={g['decision']}"
                print(line)
                if dc["missing"]:
                    print(f"  missing: {', '.join(dc['missing'])}")
                if rc and rc["failed"]:
                    print(f"  result-failed: {', '.join(rc['failed'])}")
        sys.exit(0)  # ALWAYS 0 -- --all is informational only, NEVER blocks

    if current_mode:
        current_phase = yaml_data.get("current_phase", "phase_0")
        phase_num = int(current_phase.replace("phase_", ""))

    if phase_num is None:
        print("ERROR: specify --phase N, --current, or --all", file=sys.stderr)
        sys.exit(2)

    report = check_phase(
        yaml_data,
        xnodes_by_phase,
        phase_num,
        verify_results=verify_results,
    )

    if json_mode:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        dc = report["direct_coverage"]
        sc = report["semantic_coverage"]
        g = report["gate"]
        rc = report.get("result_coverage")
        line = f"{report['phase']}: direct={dc['rate']:.0%} semantic={sc['rate']:.0%} "
        if rc:
            line += f"result={rc['rate']:.0%} "
        line += f"threshold={g['threshold']} decision={g['decision']} (basis={g['basis']})"
        print(line)
        if dc["missing"]:
            print(f"  missing: {', '.join(dc['missing'])}")
        if rc and rc["failed"]:
            print(f"  result-failed: {', '.join(rc['failed'])}")
        if report["validation"]["orphan_xnodes"]:
            print(f"  orphan xnodes: {', '.join(report['validation']['orphan_xnodes'])}")
        if report["validation"]["untagged_checks"]:
            print(f"  untagged checks: {', '.join(report['validation']['untagged_checks'])}")

    if report["gate"]["decision"] == "NO-GO":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
