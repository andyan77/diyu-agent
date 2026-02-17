"""Tests for V4 Phase 2 orchestrator -- inter-workflow CI gate.

Validates that the Phase 2 orchestrator (run_phase2_v4.sh) runs the
repository's existing CI gate (make lint && make test) after each
WF2-B* build workflow completes, before advancing to the next workflow.

This closes the quality gap where B-series workflows only verify
functional correctness but not code quality (lint/format/typecheck).
The repo CI gate is already defined in Makefile (make lint, make test);
the orchestrator must invoke it between build steps.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_P2 = ROOT / "scripts" / "run_phase2_v4.sh"
WORKFLOWS_P2_YAML = ROOT / "delivery" / "v4-phase2-workflows.yaml"


@pytest.mark.unit
class TestPhase2InterWorkflowCIGate:
    """run_phase2_v4.sh must run repo CI gate after each WF2-B* workflow."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        assert ORCHESTRATOR_P2.exists(), "scripts/run_phase2_v4.sh not found"
        self.text = ORCHESTRATOR_P2.read_text()

    def test_has_ci_gate_function_or_block(self) -> None:
        """Orchestrator must contain a CI gate invocation for B-series."""
        assert "make lint" in self.text, (
            "run_phase2_v4.sh missing 'make lint' for inter-workflow CI gate"
        )
        assert "make test" in self.text, (
            "run_phase2_v4.sh missing 'make test' for inter-workflow CI gate"
        )

    def test_ci_gate_is_conditional_on_b_series(self) -> None:
        """CI gate must only trigger for WF2-B* workflows, not A* or P*."""
        assert "WF2-B" in self.text, "run_phase2_v4.sh missing WF2-B* pattern match for CI gate"

    def test_ci_gate_failure_marks_workflow_failed(self) -> None:
        """If CI gate fails, workflow must be marked as failed."""
        # The CI gate block must call save_checkpoint with "failed" on error
        lines = self.text.splitlines()
        found_ci_gate = False
        found_failure_handling = False
        for i, line in enumerate(lines):
            if "make lint" in line and "make test" in line:
                found_ci_gate = True
                # Look within surrounding 10 lines for failure handling
                context = "\n".join(lines[max(0, i - 5) : i + 10])
                if "save_checkpoint" in context and "failed" in context:
                    found_failure_handling = True
                break
            # Also check chained form: make lint && make test
            if "make lint" in line:
                found_ci_gate = True
                context = "\n".join(lines[max(0, i - 5) : i + 10])
                if "save_checkpoint" in context and "failed" in context:
                    found_failure_handling = True
                break

        assert found_ci_gate, "CI gate block not found in orchestrator"
        assert found_failure_handling, (
            "CI gate block does not mark workflow as failed on lint/test failure"
        )

    def test_ci_gate_runs_after_checks_pass(self) -> None:
        """CI gate must run after run_wf_checks succeeds, not before."""
        lines = self.text.splitlines()
        checks_pass_line = None
        ci_gate_line = None
        for i, line in enumerate(lines):
            if "run_wf_checks" in line and checks_pass_line is None:
                checks_pass_line = i
            if "make lint" in line and "WF2-B" not in line and ci_gate_line is None:
                ci_gate_line = i

        # If both found, CI gate must come after checks
        if checks_pass_line is not None and ci_gate_line is not None:
            assert ci_gate_line > checks_pass_line, (
                f"CI gate (line {ci_gate_line}) runs before run_wf_checks (line {checks_pass_line})"
            )


@pytest.mark.unit
class TestPhase2OrchestratorBasics:
    """Basic structural tests for the Phase 2 orchestrator."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        assert ORCHESTRATOR_P2.exists()
        self.text = ORCHESTRATOR_P2.read_text()

    def test_reads_phase2_workflow_yaml(self) -> None:
        assert "v4-phase2-workflows.yaml" in self.text

    def test_evidence_dir_is_phase2(self) -> None:
        assert "evidence/v4-phase2" in self.text

    def test_supports_standard_flags(self) -> None:
        for flag in ["--wf", "--resume", "--dry-run", "--json", "--status", "--reset"]:
            assert flag in self.text, f"Missing flag support: {flag}"

    def test_checkpoint_persistence(self) -> None:
        assert "save_checkpoint" in self.text
        assert "load_checkpoint" in self.text
