"""Tests for scripts/check_milestone_ruling.py -- Full milestone delivery guard ruling.

Ruling model:
  - Each milestone is judged by 3 dimensions:
    1. status_claim: YAML-annotated status field
    2. gate_evidence: phase-level gate pass rate + evidence grade
    3. guard_ruling: composite verdict (delivered / guarded / unguarded / no_claim)

  - guard_ruling logic:
    - status=done + phase gates pass + best evidence_grade >= C → delivered
    - status=done + phase gates pass + best evidence_grade < C  → guarded
    - status=done + no gate coverage                           → unguarded
    - no status                                                → no_claim
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_matrix(tmp_path: Path, content: str) -> Path:
    matrix = tmp_path / "delivery" / "milestone-matrix.yaml"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text(content, encoding="utf-8")
    return matrix


# Phase 1: done milestones + 1 hard gate (echo ok → static → D grade)
# Phase 2: 2 done + 1 no_status + xnode-bound gate (pytest e2e → A grade)
# Phase 3: 1 done milestone but NO gates at all
FULL_MATRIX = textwrap.dedent("""\
    schema_version: "1.2"
    current_phase: "phase_2"
    phases:
      phase_1:
        name: "Security Foundation"
        milestones:
          - id: "B1-1"
            layer: "Brain"
            summary: "Port stubs"
            status: done
          - id: "B1-2"
            layer: "Brain"
            summary: "LLM integration"
            status: done
        exit_criteria:
          hard:
            - id: "p1-ports"
              check: "test -f src/ports.py"
          soft: []
        go_no_go:
          hard_pass_rate: 1.0
          approver: "architect"
      phase_2:
        name: "Core Conversation"
        milestones:
          - id: "MC2-1"
            layer: "MemoryCore"
            summary: "Memory CRUD"
            status: done
          - id: "MC2-2"
            layer: "MemoryCore"
            summary: "Memory search"
          - id: "B2-1"
            layer: "Brain"
            summary: "Conversation loop"
            status: done
        exit_criteria:
          hard:
            - id: "p2-conv"
              check: "uv run pytest tests/e2e/cross/test_conversation_loop.py -v"
              xnodes: [X2-1]
            - id: "p2-unit"
              check: "uv run pytest tests/unit/brain/ -q"
          soft: []
        go_no_go:
          hard_pass_rate: 1.0
          approver: "architect"
      phase_3:
        name: "Knowledge"
        milestones:
          - id: "K3-1"
            layer: "Knowledge"
            summary: "Knowledge CRUD"
            status: done
        exit_criteria:
          hard: []
          soft: []
        go_no_go:
          hard_pass_rate: 1.0
          approver: "architect"
    xnode_registry:
      X2-1:
        phase: 2
        guard_status: in_progress
        summary: "Conversation round-trip"
        gate_result: pass
        deep_verdict: unverified
        evidence_grade: A
""")


# ---------------------------------------------------------------------------
# Import after path setup
# ---------------------------------------------------------------------------


import check_milestone_ruling as cmr  # noqa: E402

# ---------------------------------------------------------------------------
# Tests: compute_phase_gate_profile
# ---------------------------------------------------------------------------


class TestComputePhaseGateProfile:
    """Test phase-level gate evidence computation."""

    def test_returns_profiles_for_all_phases(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        assert "phase_1" in profiles
        assert "phase_2" in profiles
        assert "phase_3" in profiles

    def test_profile_has_required_fields(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        p = profiles["phase_1"]
        assert "total_gates" in p
        assert "gate_ids" in p
        assert "best_evidence_grade" in p
        assert "has_xnode_coverage" in p

    def test_phase1_profile(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        p = profiles["phase_1"]
        assert p["total_gates"] == 1
        assert p["best_evidence_grade"] == "D"  # test -f is static
        assert p["has_xnode_coverage"] is False

    def test_phase2_profile(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        p = profiles["phase_2"]
        assert p["total_gates"] == 2
        assert p["best_evidence_grade"] == "A"  # pytest e2e
        assert p["has_xnode_coverage"] is True

    def test_phase3_no_gates(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        p = profiles["phase_3"]
        assert p["total_gates"] == 0
        assert p["best_evidence_grade"] == "F"
        assert p["has_xnode_coverage"] is False


# ---------------------------------------------------------------------------
# Tests: classify_evidence_grade
# ---------------------------------------------------------------------------


class TestClassifyEvidenceGrade:
    """Test gate command -> evidence grade classification."""

    @pytest.mark.parametrize(
        ("cmd", "expected"),
        [
            ("uv run pytest tests/e2e/cross/test_conv.py -v", "A"),
            ("cd frontend && pnpm exec playwright test tests/e2e/web/chat.spec.ts", "A"),
            ("uv run pytest tests/integration/test_memory.py -q", "B"),
            ("uv run pytest tests/unit/brain/ -q", "C"),
            ("test -f src/ports.py", "D"),
            ("grep -q 'class Brain' src/brain/engine.py", "D"),
            ("ruff check src/", "D"),
            ("bash scripts/check_layer_deps.sh --json", "D"),
            ("", "F"),
        ],
    )
    def test_grade_classification(self, cmd: str, expected: str) -> None:
        assert cmr.classify_evidence_grade(cmd) == expected


# ---------------------------------------------------------------------------
# Tests: rule_milestone (core ruling logic)
# ---------------------------------------------------------------------------


class TestRuleMilestone:
    """Test per-milestone guard ruling logic."""

    def test_delivered_done_with_strong_evidence(self, tmp_path: Path) -> None:
        """status=done + phase gate evidence_grade >= C -> delivered."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        ruling = cmr.rule_milestone(
            status="done",
            phase_key="phase_2",
            phase_profiles=profiles,
        )
        assert ruling["guard_ruling"] == "delivered"

    def test_guarded_done_with_weak_evidence(self, tmp_path: Path) -> None:
        """status=done + phase gate evidence_grade < C (D only) -> guarded."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        ruling = cmr.rule_milestone(
            status="done",
            phase_key="phase_1",
            phase_profiles=profiles,
        )
        assert ruling["guard_ruling"] == "guarded"

    def test_unguarded_done_with_no_gates(self, tmp_path: Path) -> None:
        """status=done + no gate coverage -> unguarded."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        ruling = cmr.rule_milestone(
            status="done",
            phase_key="phase_3",
            phase_profiles=profiles,
        )
        assert ruling["guard_ruling"] == "unguarded"

    def test_no_claim_when_no_status(self, tmp_path: Path) -> None:
        """No status -> no_claim regardless of gate coverage."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        ruling = cmr.rule_milestone(
            status="no_status",
            phase_key="phase_2",
            phase_profiles=profiles,
        )
        assert ruling["guard_ruling"] == "no_claim"

    def test_ruling_includes_guard_fields_v1(self, tmp_path: Path) -> None:
        """Ruling must include all 12 fields (5 core + 7 V1 guard)."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        ruling = cmr.rule_milestone(
            status="done",
            phase_key="phase_2",
            phase_profiles=profiles,
        )
        # 5 core fields
        assert "guard_ruling" in ruling
        assert "best_evidence_grade" in ruling
        assert "phase_gate_count" in ruling
        assert "has_xnode_coverage" in ruling
        assert "ruling_basis" in ruling
        # 7 V1 guard fields
        assert "gate_result" in ruling
        assert "deep_verdict" in ruling
        assert "evidence_scope" in ruling
        assert "evidence_grade" in ruling
        assert "status_basis" in ruling
        assert "verdict_reason" in ruling
        assert "promotion_rule" in ruling

    def test_gate_result_enum_valid(self, tmp_path: Path) -> None:
        """gate_result must be one of the schema-defined enum values."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        valid_enum = {"pass", "fail", "not_bound", "not_executed"}
        for status, phase in [
            ("done", "phase_1"),
            ("done", "phase_2"),
            ("done", "phase_3"),
            ("no_status", "phase_2"),
        ]:
            ruling = cmr.rule_milestone(
                status=status,
                phase_key=phase,
                phase_profiles=profiles,
            )
            assert ruling["gate_result"] in valid_enum, (
                f"gate_result={ruling['gate_result']} not in {valid_enum}"
            )

    def test_status_basis_is_proxy(self, tmp_path: Path) -> None:
        """V1: status_basis must indicate phase_gate_profile_proxy."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        ruling = cmr.rule_milestone(
            status="done",
            phase_key="phase_2",
            phase_profiles=profiles,
        )
        assert "proxy" in ruling["status_basis"]

    def test_verdict_reason_present(self, tmp_path: Path) -> None:
        """verdict_reason must be non-empty for all ruling types."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        for status, phase in [
            ("done", "phase_1"),
            ("done", "phase_2"),
            ("done", "phase_3"),
            ("no_status", "phase_2"),
        ]:
            ruling = cmr.rule_milestone(
                status=status,
                phase_key=phase,
                phase_profiles=profiles,
            )
            assert ruling["verdict_reason"], (
                f"verdict_reason empty for status={status}, phase={phase}"
            )

    def test_unguarded_gate_result_is_not_bound(self, tmp_path: Path) -> None:
        """Phase with 0 gates -> gate_result must be not_bound."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        ruling = cmr.rule_milestone(
            status="done",
            phase_key="phase_3",
            phase_profiles=profiles,
        )
        assert ruling["gate_result"] == "not_bound"

    def test_gated_phase_gate_result_is_not_executed(self, tmp_path: Path) -> None:
        """Phase with gates -> gate_result is not_executed (V1: no live exec)."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        profiles = cmr.compute_phase_gate_profiles(matrix_path=mp)
        ruling = cmr.rule_milestone(
            status="done",
            phase_key="phase_2",
            phase_profiles=profiles,
        )
        assert ruling["gate_result"] == "not_executed"


# ---------------------------------------------------------------------------
# Tests: parse_milestones (full pipeline)
# ---------------------------------------------------------------------------


class TestParseMilestones:
    def test_returns_all_milestones(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        assert len(milestones) == 6  # 2 + 3 + 1

    def test_milestone_has_all_17_fields(self, tmp_path: Path) -> None:
        """Every milestone must carry all 17 fields (5 base + 5 core + 7 V1 guard)."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        expected_fields = {
            # 5 base
            "id",
            "phase",
            "layer",
            "summary",
            "status",
            # 5 core ruling
            "guard_ruling",
            "best_evidence_grade",
            "phase_gate_count",
            "has_xnode_coverage",
            "ruling_basis",
            # 7 V1 guard
            "gate_result",
            "deep_verdict",
            "evidence_scope",
            "evidence_grade",
            "status_basis",
            "verdict_reason",
            "promotion_rule",
        }
        for m in milestones:
            actual = set(m.keys())
            missing = expected_fields - actual
            assert not missing, f"Milestone {m.get('id')} missing fields: {missing}"

    def test_phase2_done_milestone_is_delivered(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        mc2_1 = next(m for m in milestones if m["id"] == "MC2-1")
        assert mc2_1["guard_ruling"] == "delivered"
        assert mc2_1["best_evidence_grade"] == "A"

    def test_phase1_done_milestone_is_guarded(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        b1_1 = next(m for m in milestones if m["id"] == "B1-1")
        assert b1_1["guard_ruling"] == "guarded"
        assert b1_1["best_evidence_grade"] == "D"

    def test_phase3_done_milestone_is_unguarded(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        k3_1 = next(m for m in milestones if m["id"] == "K3-1")
        assert k3_1["guard_ruling"] == "unguarded"

    def test_no_status_milestone_is_no_claim(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        mc2_2 = next(m for m in milestones if m["id"] == "MC2-2")
        assert mc2_2["guard_ruling"] == "no_claim"


# ---------------------------------------------------------------------------
# Tests: generate_report
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_report_has_required_keys(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        report = cmr.generate_report(milestones)
        assert "status" in report
        assert "summary" in report
        assert "milestones" in report
        assert "findings" in report

    def test_summary_has_ruling_distribution(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        report = cmr.generate_report(milestones)
        s = report["summary"]
        assert s["total_milestones"] == 6
        assert s["delivered_count"] == 2  # MC2-1, B2-1 (phase_2 = A grade)
        assert s["guarded_count"] == 2  # B1-1, B1-2 (phase_1 = D grade)
        assert s["unguarded_count"] == 1  # K3-1 (phase_3 = no gates)
        assert s["no_claim_count"] == 1  # MC2-2

    def test_findings_include_non_delivered(self, tmp_path: Path) -> None:
        """Findings = guarded + unguarded + no_claim (everything not delivered)."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        report = cmr.generate_report(milestones)
        assert len(report["findings"]) == 4  # 2 guarded + 1 unguarded + 1 no_claim

    def test_phase_breakdown_has_ruling_counts(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        report = cmr.generate_report(milestones)
        pb = report["summary"]["phase_breakdown"]
        assert pb["phase_1"]["delivered"] == 0
        assert pb["phase_1"]["guarded"] == 2
        assert pb["phase_2"]["delivered"] == 2
        assert pb["phase_2"]["no_claim"] == 1
        assert pb["phase_3"]["unguarded"] == 1

    def test_milestones_only_in_verbose(self, tmp_path: Path) -> None:
        """milestones array populated only when verbose=True."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        report_brief = cmr.generate_report(milestones, verbose=False)
        report_full = cmr.generate_report(milestones, verbose=True)
        assert report_brief["milestones"] == []
        assert len(report_full["milestones"]) == 6

    def test_status_fail_on_unguarded(self, tmp_path: Path) -> None:
        """Report status = FAIL when unguarded milestones exist."""
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        report = cmr.generate_report(milestones)
        assert report["status"] == "FAIL"  # K3-1 is unguarded

    def test_summary_has_findings_count(self, tmp_path: Path) -> None:
        mp = _write_matrix(tmp_path, FULL_MATRIX)
        milestones = cmr.parse_milestones(matrix_path=mp)
        report = cmr.generate_report(milestones)
        assert report["summary"]["findings_count"] == 4


# ---------------------------------------------------------------------------
# Integration: Script execution on real matrix
# ---------------------------------------------------------------------------


class TestScriptExecution:
    def test_json_output_valid(self) -> None:
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_milestone_ruling.py", "--json"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        assert result.returncode in (0, 1), f"Exit {result.returncode}: {result.stderr}"
        report = json.loads(result.stdout)
        assert "status" in report
        assert "summary" in report
        assert "findings" in report

    def test_total_milestones_matches(self) -> None:
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_milestone_ruling.py", "--json"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        report = json.loads(result.stdout)
        assert report["summary"]["total_milestones"] >= 200

    def test_summary_has_new_ruling_fields(self) -> None:
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_milestone_ruling.py", "--json"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        report = json.loads(result.stdout)
        s = report["summary"]
        assert "delivered_count" in s
        assert "guarded_count" in s
        assert "unguarded_count" in s
        assert "no_claim_count" in s

    def test_findings_have_all_guard_fields(self) -> None:
        """Each finding must have all 17 fields (5 base + 5 core + 7 V1 guard)."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_milestone_ruling.py", "--json"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        report = json.loads(result.stdout)
        v1_guard_fields = {
            "gate_result",
            "deep_verdict",
            "evidence_scope",
            "evidence_grade",
            "status_basis",
            "verdict_reason",
            "promotion_rule",
        }
        for f in report["findings"][:5]:  # spot check first 5
            assert "guard_ruling" in f
            assert "best_evidence_grade" in f
            assert "phase_gate_count" in f
            assert "ruling_basis" in f
            for field in v1_guard_fields:
                assert field in f, f"Finding {f.get('id')} missing {field}"


# ---------------------------------------------------------------------------
# Tests: apply_ci_baseline
# ---------------------------------------------------------------------------


class TestApplyCiBaseline:
    """Test CI baseline logic for gradual convergence."""

    def test_no_claim_within_baseline_passes(self, tmp_path: Path) -> None:
        """no_claim_count <= baseline -> PASS (when no unguarded)."""
        report = {
            "status": "FAIL",
            "summary": {"unguarded_count": 0, "no_claim_count": 10},
        }
        assert cmr.apply_ci_baseline(report, baseline=10) == "PASS"
        assert cmr.apply_ci_baseline(report, baseline=100) == "PASS"

    def test_no_claim_exceeds_baseline_fails(self, tmp_path: Path) -> None:
        """no_claim_count > baseline -> FAIL."""
        report = {
            "status": "FAIL",
            "summary": {"unguarded_count": 0, "no_claim_count": 10},
        }
        assert cmr.apply_ci_baseline(report, baseline=9) == "FAIL"

    def test_unguarded_always_fails_regardless_of_baseline(self, tmp_path: Path) -> None:
        """unguarded_count > 0 -> FAIL even if no_claim within baseline."""
        report = {
            "status": "FAIL",
            "summary": {"unguarded_count": 1, "no_claim_count": 5},
        }
        assert cmr.apply_ci_baseline(report, baseline=100) == "FAIL"


# ---------------------------------------------------------------------------
# V2 fixture: milestones with gate_criteria
# ---------------------------------------------------------------------------

FULL_MATRIX_V2 = textwrap.dedent("""\
    schema_version: "1.3"
    current_phase: "phase_2"
    phases:
      phase_1:
        name: "Security Foundation"
        milestones:
          - id: "G1-1"
            layer: "Gateway"
            summary: "JWT auth middleware"
            status: done
            gate_criteria: ["p1-gateway-auth"]
          - id: "G1-2"
            layer: "Gateway"
            summary: "OrgContext middleware"
            status: done
          - id: "G1-3"
            layer: "Gateway"
            summary: "RBAC check"
            status: done
            gate_criteria: ["p1-gateway-auth", "p1-rls"]
        exit_criteria:
          hard:
            - id: "p1-gateway-auth"
              check: "uv run pytest tests/unit/gateway/test_jwt_auth.py -q"
            - id: "p1-rls"
              check: "uv run pytest tests/isolation/smoke/ --tb=short -q"
              xnodes: [X1-1]
          soft: []
        go_no_go:
          hard_pass_rate: 1.0
          approver: "architect"
      phase_2:
        name: "Core Conversation"
        milestones:
          - id: "B2-1"
            layer: "Brain"
            summary: "Conversation engine"
            status: done
            gate_criteria: ["p2-brain-engine", "p2-conv"]
          - id: "MC2-1"
            layer: "MemoryCore"
            summary: "Memory CRUD"
            status: done
            gate_criteria: ["p2-unit"]
          - id: "MC2-2"
            layer: "MemoryCore"
            summary: "Memory search"
        exit_criteria:
          hard:
            - id: "p2-brain-engine"
              check: "uv run pytest tests/unit/brain/ -q"
            - id: "p2-conv"
              check: "uv run pytest tests/e2e/cross/test_conversation_loop.py -v"
              xnodes: [X2-1]
            - id: "p2-unit"
              check: "uv run pytest tests/unit/memory/ -q"
          soft: []
        go_no_go:
          hard_pass_rate: 1.0
          approver: "architect"
    xnode_registry:
      X1-1:
        phase: 1
        guard_status: in_progress
        summary: "RLS isolation round-trip"
        gate_result: pass
        deep_verdict: pass
        evidence_grade: A
      X2-1:
        phase: 2
        guard_status: in_progress
        summary: "Conversation round-trip"
        gate_result: pass
        deep_verdict: unverified
        evidence_grade: A
""")


# ---------------------------------------------------------------------------
# Tests: V2 resolve_milestone_gates
# ---------------------------------------------------------------------------


class TestResolveMilestoneGates:
    """Test gate_criteria -> exit_criteria resolution."""

    def test_resolve_with_valid_binding(self) -> None:
        """gate_criteria IDs resolve to matching exit_criteria entries."""
        ms = {"gate_criteria": ["p2-brain-engine", "p2-conv"]}
        ec = {
            "hard": [
                {"id": "p2-brain-engine", "check": "uv run pytest tests/unit/brain/ -q"},
                {"id": "p2-conv", "check": "pytest e2e", "xnodes": ["X2-1"]},
                {"id": "p2-unit", "check": "pytest unit"},
            ],
            "soft": [],
        }
        result = cmr.resolve_milestone_gates(ms, ec)
        assert len(result) == 2
        assert result[0]["id"] == "p2-brain-engine"
        assert result[1]["id"] == "p2-conv"

    def test_resolve_without_binding(self) -> None:
        """Milestone without gate_criteria returns empty list."""
        ms = {"id": "B1-1"}
        ec = {"hard": [{"id": "p1-x", "check": "echo ok"}], "soft": []}
        result = cmr.resolve_milestone_gates(ms, ec)
        assert result == []

    def test_resolve_skips_unknown_ids(self) -> None:
        """Unknown gate_criteria IDs are silently skipped."""
        ms = {"gate_criteria": ["p2-nonexistent", "p2-brain-engine"]}
        ec = {
            "hard": [{"id": "p2-brain-engine", "check": "pytest"}],
            "soft": [],
        }
        result = cmr.resolve_milestone_gates(ms, ec)
        assert len(result) == 1
        assert result[0]["id"] == "p2-brain-engine"


# ---------------------------------------------------------------------------
# Tests: V2 lookup_xnode_verdicts
# ---------------------------------------------------------------------------


class TestLookupXnodeVerdicts:
    """Test gate -> xnodes -> xnode_registry chain."""

    def test_lookup_with_xnode_chain(self) -> None:
        """Gates with xnodes resolve through xnode_registry."""
        bound_gates = [
            {"id": "p2-conv", "check": "pytest e2e", "xnodes": ["X2-1"]},
        ]
        xnode_registry = {
            "X2-1": {
                "phase": 2,
                "guard_status": "in_progress",
                "gate_result": "pass",
                "deep_verdict": "unverified",
            },
        }
        result = cmr.lookup_xnode_verdicts(bound_gates, xnode_registry)
        assert result["gate_result"] == "pass"
        assert result["deep_verdict"] == "unverified"
        assert result["xnode_ids"] == ["X2-1"]

    def test_lookup_without_xnodes(self) -> None:
        """Gates without xnodes return None values."""
        bound_gates = [
            {"id": "p2-unit", "check": "pytest unit"},
        ]
        result = cmr.lookup_xnode_verdicts(bound_gates, {})
        assert result["gate_result"] is None
        assert result["deep_verdict"] is None
        assert result["xnode_ids"] == []

    def test_worst_verdict_wins(self) -> None:
        """Multiple xnodes -> worst verdict/gate_result wins."""
        bound_gates = [
            {"id": "g1", "xnodes": ["X1", "X2"]},
        ]
        xnode_registry = {
            "X1": {"gate_result": "pass", "deep_verdict": "pass"},
            "X2": {"gate_result": "fail", "deep_verdict": "stale"},
        }
        result = cmr.lookup_xnode_verdicts(bound_gates, xnode_registry)
        assert result["gate_result"] == "fail"
        assert result["deep_verdict"] == "stale"


# ---------------------------------------------------------------------------
# Tests: V2 derive_guard_fields_v2
# ---------------------------------------------------------------------------


class TestDeriveGuardFieldsV2:
    """Test V2 guard field derivation from per-milestone binding."""

    def test_v2_with_xnode_chain(self) -> None:
        """V2 milestone with xnode chain uses xnode_registry basis."""
        bound_gates = [
            {"id": "p2-conv", "check": "pytest e2e", "xnodes": ["X2-1"]},
        ]
        xnode_lookup = {
            "gate_result": "pass",
            "deep_verdict": "unverified",
            "xnode_ids": ["X2-1"],
        }
        fields = cmr._derive_guard_fields_v2(
            guard_ruling="delivered",
            bound_gates=bound_gates,
            xnode_lookup=xnode_lookup,
            ruling_basis="test",
        )
        assert fields["status_basis"] == "xnode_registry"
        assert fields["gate_result"] == "pass"
        assert fields["deep_verdict"] == "unverified"
        assert "X2-1" in fields["verdict_reason"]

    def test_v2_without_xnode_chain(self) -> None:
        """V2 milestone without xnodes uses milestone_gate_binding basis."""
        bound_gates = [
            {"id": "p2-unit", "check": "uv run pytest tests/unit/brain/ -q"},
        ]
        xnode_lookup = {
            "gate_result": None,
            "deep_verdict": None,
            "xnode_ids": [],
        }
        fields = cmr._derive_guard_fields_v2(
            guard_ruling="delivered",
            bound_gates=bound_gates,
            xnode_lookup=xnode_lookup,
            ruling_basis="test",
        )
        assert fields["status_basis"] == "milestone_gate_binding"
        assert fields["gate_result"] == "not_executed"
        assert fields["evidence_grade"] == "C"
        assert "milestone-bound" in fields["evidence_scope"]

    def test_v2_evidence_grade_per_milestone(self) -> None:
        """V2 evidence_grade is based on bound gate commands, not phase-level."""
        # Only bind to a unit test gate -> grade should be C
        bound_gates = [
            {"id": "p2-unit", "check": "uv run pytest tests/unit/memory/ -q"},
        ]
        xnode_lookup = {"gate_result": None, "deep_verdict": None, "xnode_ids": []}
        fields = cmr._derive_guard_fields_v2(
            guard_ruling="delivered",
            bound_gates=bound_gates,
            xnode_lookup=xnode_lookup,
            ruling_basis="test",
        )
        assert fields["evidence_grade"] == "C"

        # Bind to an E2E gate -> grade should be A
        bound_gates_e2e = [
            {"id": "p2-conv", "check": "uv run pytest tests/e2e/cross/test_conv.py -v"},
        ]
        fields_e2e = cmr._derive_guard_fields_v2(
            guard_ruling="delivered",
            bound_gates=bound_gates_e2e,
            xnode_lookup=xnode_lookup,
            ruling_basis="test",
        )
        assert fields_e2e["evidence_grade"] == "A"


# ---------------------------------------------------------------------------
# Tests: V2 validate_gate_bindings
# ---------------------------------------------------------------------------


class TestValidateGateBindings:
    """Test gate_criteria binding validation."""

    def test_valid_bindings_produce_no_findings(self) -> None:
        """All gate_criteria referencing same-phase exit_criteria -> no findings."""
        phases = {
            "phase_1": {
                "exit_criteria": {
                    "hard": [{"id": "p1-auth"}, {"id": "p1-rls"}],
                    "soft": [],
                },
            },
        }
        milestones_raw = [
            ({"id": "G1-1", "gate_criteria": ["p1-auth"]}, "phase_1"),
            ({"id": "G1-2", "gate_criteria": ["p1-rls"]}, "phase_1"),
        ]
        findings = cmr.validate_gate_bindings(milestones_raw, phases)
        assert findings == []

    def test_cross_phase_binding_produces_finding(self) -> None:
        """gate_criteria referencing different phase exit_criteria -> invalid_binding."""
        phases = {
            "phase_1": {
                "exit_criteria": {
                    "hard": [{"id": "p1-auth"}],
                    "soft": [],
                },
            },
        }
        milestones_raw = [
            ({"id": "G1-1", "gate_criteria": ["p2-brain-engine"]}, "phase_1"),
        ]
        findings = cmr.validate_gate_bindings(milestones_raw, phases)
        assert len(findings) == 1
        assert findings[0]["type"] == "invalid_binding"
        assert "p2-brain-engine" in findings[0]["message"]

    def test_duplicate_binding_produces_finding(self) -> None:
        """Duplicate gate_criteria entries -> duplicate_binding finding."""
        phases = {
            "phase_1": {
                "exit_criteria": {
                    "hard": [{"id": "p1-auth"}],
                    "soft": [],
                },
            },
        }
        milestones_raw = [
            ({"id": "G1-1", "gate_criteria": ["p1-auth", "p1-auth"]}, "phase_1"),
        ]
        findings = cmr.validate_gate_bindings(milestones_raw, phases)
        assert len(findings) == 1
        assert findings[0]["type"] == "duplicate_binding"


# ---------------------------------------------------------------------------
# Tests: V2 parse_milestones with gate_criteria
# ---------------------------------------------------------------------------


class TestParseMilestonesV2:
    """Test full pipeline with V2 gate_criteria bindings."""

    def test_v2_milestone_with_binding_uses_milestone_basis(self, tmp_path: Path) -> None:
        """Milestone with gate_criteria -> V2 guard fields."""
        mp = _write_matrix(tmp_path, FULL_MATRIX_V2)
        milestones = cmr.parse_milestones(matrix_path=mp)
        g1_1 = next(m for m in milestones if m["id"] == "G1-1")
        # G1-1 binds to p1-gateway-auth (no xnodes) -> milestone_gate_binding
        assert g1_1["status_basis"] == "milestone_gate_binding"
        assert g1_1["evidence_grade"] == "C"  # pytest unit -> C

    def test_v2_milestone_with_xnode_uses_xnode_basis(self, tmp_path: Path) -> None:
        """Milestone binding to xnode-bearing gate -> xnode_registry basis."""
        mp = _write_matrix(tmp_path, FULL_MATRIX_V2)
        milestones = cmr.parse_milestones(matrix_path=mp)
        b2_1 = next(m for m in milestones if m["id"] == "B2-1")
        # B2-1 binds to p2-conv (xnodes: [X2-1]) -> xnode_registry
        assert b2_1["status_basis"] == "xnode_registry"
        assert b2_1["gate_result"] == "pass"  # from X2-1 registry entry
        assert b2_1["deep_verdict"] == "unverified"  # from X2-1 registry

    def test_v2_milestone_without_binding_uses_proxy(self, tmp_path: Path) -> None:
        """Milestone without gate_criteria -> V1 proxy fields."""
        mp = _write_matrix(tmp_path, FULL_MATRIX_V2)
        milestones = cmr.parse_milestones(matrix_path=mp)
        g1_2 = next(m for m in milestones if m["id"] == "G1-2")
        assert g1_2["status_basis"] == "phase_gate_profile_proxy"

    def test_v2_xnode_deep_verdict_pass_propagates(self, tmp_path: Path) -> None:
        """X-node with deep_verdict=pass propagates to V2 milestone."""
        mp = _write_matrix(tmp_path, FULL_MATRIX_V2)
        milestones = cmr.parse_milestones(matrix_path=mp)
        # G1-3 binds to p1-gateway-auth + p1-rls; p1-rls has X1-1 (deep_verdict=pass)
        g1_3 = next(m for m in milestones if m["id"] == "G1-3")
        assert g1_3["status_basis"] == "xnode_registry"
        assert g1_3["deep_verdict"] == "pass"  # from X1-1
        assert g1_3["gate_result"] == "pass"  # from X1-1

    def test_v2_report_shows_v2_bound_count(self, tmp_path: Path) -> None:
        """Report summary includes v2_bound_count > 0."""
        mp = _write_matrix(tmp_path, FULL_MATRIX_V2)
        milestones = cmr.parse_milestones(matrix_path=mp)
        report = cmr.generate_report(milestones)
        # 4 milestones have gate_criteria: G1-1, G1-3, B2-1, MC2-1
        assert report["summary"]["v2_bound_count"] == 4

    def test_v2_mixed_output_all_17_fields(self, tmp_path: Path) -> None:
        """Both V1 and V2 milestones have all 17 fields."""
        mp = _write_matrix(tmp_path, FULL_MATRIX_V2)
        milestones = cmr.parse_milestones(matrix_path=mp)
        expected_fields = {
            "id",
            "phase",
            "layer",
            "summary",
            "status",
            "guard_ruling",
            "best_evidence_grade",
            "phase_gate_count",
            "has_xnode_coverage",
            "ruling_basis",
            "gate_result",
            "deep_verdict",
            "evidence_scope",
            "evidence_grade",
            "status_basis",
            "verdict_reason",
            "promotion_rule",
        }
        for m in milestones:
            actual = set(m.keys())
            missing = expected_fields - actual
            assert not missing, f"Milestone {m.get('id')} missing fields: {missing}"


# ---------------------------------------------------------------------------
# Integration: V2 on real matrix
# ---------------------------------------------------------------------------


class TestScriptExecutionV2:
    """Test V2 behavior on the real milestone-matrix.yaml."""

    def test_v2_bound_count_positive(self) -> None:
        """Real matrix must have v2_bound_count > 0 after migration."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_milestone_ruling.py", "--json"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        report = json.loads(result.stdout)
        assert report["summary"]["v2_bound_count"] > 0

    def test_binding_findings_empty(self) -> None:
        """Real matrix must have 0 binding validation findings."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_milestone_ruling.py", "--json"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        report = json.loads(result.stdout)
        assert report.get("binding_findings", []) == []
