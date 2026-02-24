"""Tests for scripts/lib/xnode_utils.py -- X-Node Registry utilities."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from lib.xnode_utils import (  # noqa: E402
    VALID_GUARD_STATUSES,
    _extract_phase_from_id,
    get_xnode_ids_by_phase,
    get_xnode_ids_by_status,
    load_matrix,
    load_xnode_registry,
    validate_registry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_matrix(tmp_path: Path, content: str) -> Path:
    """Write a milestone-matrix.yaml and return its path."""
    matrix = tmp_path / "delivery" / "milestone-matrix.yaml"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text(content, encoding="utf-8")
    return matrix


MINIMAL_MATRIX = textwrap.dedent("""\
    schema_version: "1.2"
    current_phase: "phase_2"
    phases:
      phase_2:
        name: "Core Conversation"
        exit_criteria:
          hard:
            - id: "p2-conv"
              check: "echo ok"
              xnodes: [X2-1, X2-2]
          soft: []
        go_no_go:
          hard_pass_rate: 1.0
          approver: "architect"
    xnode_registry:
      X2-1:
        phase: 2
        guard_status: in_progress
        summary: "Brain→MemoryCore round-trip"
      X2-2:
        phase: 2
        guard_status: done
        summary: "Brain→Knowledge retrieval"
      X5-1:
        phase: 5
        guard_status: pending
        summary: "Future node"
""")


# ---------------------------------------------------------------------------
# load_matrix
# ---------------------------------------------------------------------------


class TestLoadMatrix:
    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        data = load_matrix(matrix_path=mp)
        assert data["schema_version"] == "1.2"
        assert "xnode_registry" in data

    def test_returns_empty_for_missing(self, tmp_path: Path) -> None:
        data = load_matrix(matrix_path=tmp_path / "nonexistent.yaml")
        assert data == {}

    def test_returns_empty_for_non_dict(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, "- just a list")
        data = load_matrix(matrix_path=mp)
        assert data == {}


# ---------------------------------------------------------------------------
# load_xnode_registry
# ---------------------------------------------------------------------------


class TestLoadXnodeRegistry:
    def test_loads_registry(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        reg = load_xnode_registry(matrix_path=mp)
        assert "X2-1" in reg
        assert "X2-2" in reg
        assert "X5-1" in reg
        assert reg["X2-1"]["guard_status"] == "in_progress"

    def test_empty_when_no_registry(self, tmp_path: Path) -> None:
        mp = _write_matrix(
            tmp_path,
            textwrap.dedent("""\
                schema_version: "1.1"
                phases: {}
            """),
        )
        reg = load_xnode_registry(matrix_path=mp)
        assert reg == {}


# ---------------------------------------------------------------------------
# get_xnode_ids_by_status
# ---------------------------------------------------------------------------


class TestGetXnodeIdsByStatus:
    def test_filter_done(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        reg = load_xnode_registry(matrix_path=mp)
        done = get_xnode_ids_by_status(reg, {"done"})
        assert done == {"X2-2"}

    def test_filter_pending(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        reg = load_xnode_registry(matrix_path=mp)
        pending = get_xnode_ids_by_status(reg, {"pending"})
        assert pending == {"X5-1"}

    def test_filter_multiple_statuses(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        reg = load_xnode_registry(matrix_path=mp)
        active = get_xnode_ids_by_status(reg, {"in_progress", "done"})
        assert active == {"X2-1", "X2-2"}

    def test_empty_registry(self) -> None:
        assert get_xnode_ids_by_status({}, {"done"}) == set()


# ---------------------------------------------------------------------------
# get_xnode_ids_by_phase
# ---------------------------------------------------------------------------


class TestGetXnodeIdsByPhase:
    def test_filter_phase_2(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        reg = load_xnode_registry(matrix_path=mp)
        p2 = get_xnode_ids_by_phase(reg, 2)
        assert p2 == {"X2-1", "X2-2"}

    def test_filter_phase_5(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        reg = load_xnode_registry(matrix_path=mp)
        p5 = get_xnode_ids_by_phase(reg, 5)
        assert p5 == {"X5-1"}

    def test_nonexistent_phase(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        reg = load_xnode_registry(matrix_path=mp)
        assert get_xnode_ids_by_phase(reg, 99) == set()


# ---------------------------------------------------------------------------
# _extract_phase_from_id
# ---------------------------------------------------------------------------


class TestExtractPhaseFromId:
    @pytest.mark.parametrize(
        ("xid", "expected"),
        [
            ("X0-1", 0),
            ("X2-3", 2),
            ("X4-1", 4),
            ("XF4-1", 4),
            # XM prefix: M-track batch number, NOT phase number.
            # _extract_phase_from_id returns None so Rule 2 skips key-phase check.
            ("XM0-1", None),
            ("XM1-1", None),
            ("XM3-2", None),
            ("invalid", None),
            ("", None),
        ],
    )
    def test_extraction(self, xid: str, expected: int | None) -> None:
        assert _extract_phase_from_id(xid) == expected


# ---------------------------------------------------------------------------
# validate_registry
# ---------------------------------------------------------------------------


class TestValidateRegistry:
    def _make_registry_and_matrix(self, tmp_path: Path) -> tuple[dict, dict]:
        mp = _write_matrix(tmp_path, MINIMAL_MATRIX)
        matrix = load_matrix(matrix_path=mp)
        registry = matrix.get("xnode_registry", {})
        return registry, matrix

    def test_no_issues_when_valid(self, tmp_path: Path) -> None:
        reg, matrix = self._make_registry_and_matrix(tmp_path)
        issues = validate_registry(reg, matrix, crosscutting_ids={"X2-1", "X2-2", "X5-1"})
        # Should have no ERROR issues (may have WARN for cross-phase)
        errors = [i for i in issues if i.startswith("ERROR:")]
        assert errors == []

    def test_rule1_completeness_detects_missing(self, tmp_path: Path) -> None:
        reg, matrix = self._make_registry_and_matrix(tmp_path)
        crosscutting = {"X2-1", "X2-2", "X5-1", "X9-1"}  # X9-1 not in registry
        issues = validate_registry(reg, matrix, crosscutting_ids=crosscutting)
        errors = [i for i in issues if "X9-1" in i and "missing from registry" in i]
        assert len(errors) == 1

    def test_rule1_skipped_when_no_crosscutting(self, tmp_path: Path) -> None:
        reg, matrix = self._make_registry_and_matrix(tmp_path)
        issues = validate_registry(reg, matrix, crosscutting_ids=None)
        # No rule 1 errors since crosscutting_ids is None
        assert not any("missing from registry" in i for i in issues)

    def test_rule2_key_phase_inconsistency(self, tmp_path: Path) -> None:
        registry = {
            "X4-1": {"phase": 3, "guard_status": "in_progress"},  # 4 != 3
        }
        matrix = {"phases": {}}
        issues = validate_registry(registry, matrix)
        errors = [i for i in issues if "X4-1" in i and "phase=" in i]
        assert len(errors) == 1

    def test_rule2_xm_exempt_from_key_phase_check(self) -> None:
        """XM prefix uses M-track batch number, not phase number.

        XM1-1 has phase=3 (actual execution phase), but the '1' in XM1
        is the M-track batch. Rule 2 must NOT flag this as inconsistent.
        """
        registry = {
            "XM1-1": {"phase": 3, "guard_status": "in_progress"},
            "XM2-1": {"phase": 4, "guard_status": "in_progress"},
            "XM3-2": {"phase": 5, "guard_status": "pending"},
        }
        matrix = {"phases": {}}
        issues = validate_registry(registry, matrix)
        phase_errors = [i for i in issues if "phase=" in i and i.startswith("ERROR:")]
        assert phase_errors == [], f"XM nodes should be exempt: {phase_errors}"

    def test_rule2_valid_status(self, tmp_path: Path) -> None:
        registry = {
            "X2-1": {"phase": 2, "guard_status": "invalid_status"},
        }
        matrix = {"phases": {}}
        issues = validate_registry(registry, matrix)
        errors = [i for i in issues if "guard_status=" in i]
        assert len(errors) == 1

    def test_rule3_reference_validity(self, tmp_path: Path) -> None:
        registry = {
            "X2-1": {"phase": 2, "guard_status": "in_progress"},
            # X2-2 is NOT in registry but referenced in gate
        }
        matrix = {
            "phases": {
                "phase_2": {
                    "exit_criteria": {
                        "hard": [
                            {"id": "p2-conv", "check": "echo ok", "xnodes": ["X2-1", "X2-2"]},
                        ],
                        "soft": [],
                    },
                },
            },
        }
        issues = validate_registry(registry, matrix)
        errors = [i for i in issues if "X2-2" in i and "not in xnode_registry" in i]
        assert len(errors) == 1

    def test_rule4_cross_phase_warning(self, tmp_path: Path) -> None:
        registry = {
            "X2-1": {"phase": 2, "guard_status": "in_progress"},
        }
        matrix = {
            "phases": {
                "phase_3": {
                    "exit_criteria": {
                        "hard": [
                            {"id": "p3-gate", "check": "echo ok", "xnodes": ["X2-1"]},
                        ],
                        "soft": [],
                    },
                },
            },
        }
        issues = validate_registry(registry, matrix)
        warns = [i for i in issues if i.startswith("WARN:") and "X2-1" in i]
        assert len(warns) == 1

    def test_all_valid_statuses_accepted(self) -> None:
        """Every value in VALID_GUARD_STATUSES should pass rule 2."""
        for status in VALID_GUARD_STATUSES:
            registry = {"X1-1": {"phase": 1, "guard_status": status}}
            matrix = {"phases": {}}
            issues = validate_registry(registry, matrix)
            errors = [i for i in issues if i.startswith("ERROR:")]
            assert errors == [], f"Status {status!r} should be valid but got: {errors}"
