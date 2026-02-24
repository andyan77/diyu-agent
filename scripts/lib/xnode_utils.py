"""X-Node Registry utilities.

SSOT loader, validator, and filter for the xnode_registry section in
delivery/milestone-matrix.yaml.

Public API
----------
- load_matrix(matrix_path) -> dict
- load_xnode_registry(matrix_path) -> dict[str, dict]
- get_xnode_ids_by_status(registry, statuses) -> set[str]
- get_xnode_ids_by_phase(registry, phase_num) -> set[str]
- validate_registry(registry, matrix, crosscutting_ids) -> list[str]

Validation rules (4):
  1. Completeness: registry keys >= crosscutting_ids (no missing X-nodes)
  2. Key-phase consistency: X4-1 must have phase=4
  3. Reference validity: exit_criteria xnode refs must exist in registry
  4. Cross-phase reference: WARN if gate in phase_N references X-node from phase_M
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

MATRIX_PATH = Path("delivery/milestone-matrix.yaml")

# Pattern to extract phase number from X-node ID: X4-1 -> 4, XF4-1 -> 4
# XM prefix is EXCLUDED: XM's digit is the M-track batch number, not the phase.
# E.g. XM1-1 means "Multimodal batch 1, node 1" and may belong to phase 3.
_XNODE_PHASE_RE = re.compile(r"^XF?(\d+)-\d+$")

# Valid guard_status values (must match schema enum)
VALID_GUARD_STATUSES = frozenset({"done", "in_progress", "blocked_env", "pending", "skipped"})


def load_matrix(*, matrix_path: Path | None = None) -> dict:
    """Load milestone-matrix.yaml and return the parsed dict."""
    path = matrix_path or MATRIX_PATH
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def load_xnode_registry(*, matrix_path: Path | None = None) -> dict[str, dict]:
    """Load the xnode_registry section from milestone-matrix.yaml.

    Returns a dict keyed by X-node ID (e.g. "X2-1") with value dicts
    containing at minimum {phase, guard_status}.
    Returns empty dict if registry is absent.
    """
    matrix = load_matrix(matrix_path=matrix_path)
    registry = matrix.get("xnode_registry", {})
    return registry if isinstance(registry, dict) else {}


def get_xnode_ids_by_status(
    registry: dict[str, dict],
    statuses: set[str] | frozenset[str],
) -> set[str]:
    """Return X-node IDs whose guard_status is in the given set.

    Example:
        done_ids = get_xnode_ids_by_status(reg, {"done"})
        actionable = get_xnode_ids_by_status(reg, {"in_progress", "done"})
    """
    return {
        xid
        for xid, entry in registry.items()
        if isinstance(entry, dict) and entry.get("guard_status") in statuses
    }


def get_xnode_ids_by_phase(
    registry: dict[str, dict],
    phase_num: int,
) -> set[str]:
    """Return X-node IDs belonging to the given phase number."""
    return {
        xid
        for xid, entry in registry.items()
        if isinstance(entry, dict) and entry.get("phase") == phase_num
    }


def _extract_phase_from_id(xnode_id: str) -> int | None:
    """Extract phase number from X-node ID string.

    X4-1 -> 4, XF4-1 -> 4, XM3-2 -> 3
    """
    m = _XNODE_PHASE_RE.match(xnode_id)
    return int(m.group(1)) if m else None


def _collect_gate_xnode_refs(matrix: dict) -> list[tuple[str, str, str]]:
    """Collect all (phase_key, gate_id, xnode_id) triples from exit_criteria."""
    refs: list[tuple[str, str, str]] = []
    for phase_key, phase_data in matrix.get("phases", {}).items():
        if not isinstance(phase_data, dict):
            continue
        ec = phase_data.get("exit_criteria", {})
        for tier in ("hard", "soft"):
            for crit in ec.get(tier, []):
                gate_id = crit.get("id", "")
                for xid in crit.get("xnodes", []):
                    refs.append((phase_key, gate_id, str(xid)))
    return refs


def validate_registry(
    registry: dict[str, dict],
    matrix: dict,
    crosscutting_ids: set[str] | None = None,
) -> list[str]:
    """Validate xnode_registry against 4 rules.

    Args:
        registry: The xnode_registry dict from YAML.
        matrix: The full milestone-matrix dict (for exit_criteria refs).
        crosscutting_ids: Full set of X-node IDs from crosscutting.md.
            If None, rule 1 is skipped.

    Returns:
        List of error/warning strings. Errors start with "ERROR:",
        warnings start with "WARN:".
    """
    issues: list[str] = []

    # Rule 1: Completeness (registry >= crosscutting full set)
    if crosscutting_ids is not None:
        missing = crosscutting_ids - set(registry.keys())
        if missing:
            for xid in sorted(missing):
                issues.append(
                    f"ERROR: X-node {xid} defined in crosscutting.md but missing from registry"
                )

    # Rule 2: Key-phase consistency (X4-1 must have phase=4)
    for xid, entry in registry.items():
        if not isinstance(entry, dict):
            issues.append(f"ERROR: registry[{xid}] is not a dict")
            continue
        expected_phase = _extract_phase_from_id(xid)
        actual_phase = entry.get("phase")
        if expected_phase is not None and actual_phase != expected_phase:
            issues.append(
                f"ERROR: registry[{xid}] phase={actual_phase} but ID implies phase={expected_phase}"
            )
        # Also validate guard_status value
        gs = entry.get("guard_status")
        if gs not in VALID_GUARD_STATUSES:
            issues.append(
                f"ERROR: registry[{xid}] guard_status={gs!r} not in {sorted(VALID_GUARD_STATUSES)}"
            )

    # Rule 3: Reference validity (exit_criteria xnode refs must exist in registry)
    refs = _collect_gate_xnode_refs(matrix)
    for _phase_key, gate_id, xid in refs:
        if xid not in registry:
            issues.append(f"ERROR: gate {gate_id} references {xid} but it is not in xnode_registry")

    # Rule 4: Cross-phase reference policy (WARN if gate in phase_N references X-node from phase_M)
    for phase_key, gate_id, xid in refs:
        gate_phase_num = (
            int(phase_key.replace("phase_", "")) if phase_key.startswith("phase_") else None
        )
        node_phase = _extract_phase_from_id(xid)
        if gate_phase_num is not None and node_phase is not None and gate_phase_num != node_phase:
            issues.append(
                f"WARN: gate {gate_id} in {phase_key} references {xid} (phase {node_phase})"
            )

    return issues
