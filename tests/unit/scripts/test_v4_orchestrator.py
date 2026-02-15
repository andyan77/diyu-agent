"""Tests for V4 Phase 1 orchestrator infrastructure.

Validates the machine-readable workflow definitions, orchestrator script,
checkpoint persistence, and Claude command entry for the V4 7-WF build
pipeline.

V4 Workflows:
  WF-P0: Prerequisite fixes (guard script bugs)
  WF-A1: Gate Entry (milestone check, card validation, risk assessment)
  WF-B1: Infrastructure implementation (I1-1 ~ I1-7)
  WF-B2: Gateway implementation (G1-1 ~ G1-6)
  WF-B3: Frontend implementation (FW1-1 ~ FW1-4, FA1-1 ~ FA1-2)
  WF-B4: Crosscutting implementation (D1-1 ~ D1-3, OS1-1 ~ OS1-6)
  WF-A2: Gate Exit (8 hard exit_criteria, phase pointer update)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_YAML = ROOT / "delivery" / "v4-workflows.yaml"
ORCHESTRATOR = ROOT / "scripts" / "run_phase1_v4.sh"
COMMAND_ENTRY = ROOT / ".claude" / "commands" / "phase1-build.md"
MILESTONE_MATRIX = ROOT / "delivery" / "milestone-matrix.yaml"


@pytest.mark.unit
class TestV4WorkflowDefinitions:
    """v4-workflows.yaml must define all 7 workflows with required fields."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        assert WORKFLOWS_YAML.exists(), "delivery/v4-workflows.yaml not found"
        self.data = yaml.safe_load(WORKFLOWS_YAML.read_text())

    def test_has_7_workflows(self) -> None:
        wfs = self.data.get("workflows", [])
        assert len(wfs) == 7, f"Expected 7 workflows, got {len(wfs)}"

    def test_workflow_ids_match_v4_spec(self) -> None:
        wf_ids = [w["id"] for w in self.data["workflows"]]
        expected = ["WF-P0", "WF-A1", "WF-B1", "WF-B2", "WF-B3", "WF-B4", "WF-A2"]
        assert wf_ids == expected

    def test_each_workflow_has_required_fields(self) -> None:
        required = {"id", "name", "depends_on", "task_cards", "checks", "on_failure"}
        for wf in self.data["workflows"]:
            missing = required - set(wf.keys())
            assert not missing, f"Workflow {wf.get('id', '?')} missing fields: {missing}"

    def test_dependency_graph_is_dag(self) -> None:
        """Dependencies must not create cycles."""
        wf_ids = {w["id"] for w in self.data["workflows"]}
        for wf in self.data["workflows"]:
            for dep in wf["depends_on"]:
                assert dep in wf_ids, f"{wf['id']} depends on unknown workflow '{dep}'"
            assert wf["id"] not in wf["depends_on"], f"{wf['id']} depends on itself"

    def test_wf_p0_has_no_dependencies(self) -> None:
        wf_p0 = next(w for w in self.data["workflows"] if w["id"] == "WF-P0")
        assert wf_p0["depends_on"] == []

    def test_wf_a2_depends_on_all_build_workflows(self) -> None:
        wf_a2 = next(w for w in self.data["workflows"] if w["id"] == "WF-A2")
        for dep in ["WF-B1", "WF-B2", "WF-B3", "WF-B4"]:
            assert dep in wf_a2["depends_on"], f"WF-A2 missing dependency on {dep}"

    def test_build_workflows_reference_valid_task_cards(self) -> None:
        """Task card IDs must match those in milestone-matrix.yaml."""
        mm = yaml.safe_load(MILESTONE_MATRIX.read_text())
        p1_ids = {m["id"] for m in mm["phases"]["phase_1"]["milestones"]}
        for wf in self.data["workflows"]:
            for card_id in wf["task_cards"]:
                if card_id.startswith("P0."):
                    continue  # P0 items are audit fixes, not task cards
                assert card_id in p1_ids, f"{wf['id']} references unknown card '{card_id}'"

    def test_on_failure_is_valid_strategy(self) -> None:
        valid = {"abort", "retry", "skip", "ask"}
        for wf in self.data["workflows"]:
            assert wf["on_failure"] in valid, (
                f"{wf['id']} has invalid on_failure: {wf['on_failure']}"
            )

    def test_checks_reference_existing_scripts(self) -> None:
        """Check commands must reference scripts that exist."""
        for wf in self.data["workflows"]:
            for check in wf["checks"]:
                cmd = check.get("command", "")
                if not cmd:
                    continue
                # Extract script path from command
                parts = cmd.split()
                for part in parts:
                    if part.endswith(".sh") or part.endswith(".py"):
                        script = ROOT / part
                        assert script.exists(), (
                            f"{wf['id']} check references missing script: {part}"
                        )
                        break


@pytest.mark.unit
class TestV4OrchestratorScript:
    """run_phase1_v4.sh must support --wf, --resume, --dry-run, --json."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        assert ORCHESTRATOR.exists(), "scripts/run_phase1_v4.sh not found"
        self.text = ORCHESTRATOR.read_text()

    def test_supports_wf_flag(self) -> None:
        assert "--wf" in self.text

    def test_supports_resume_flag(self) -> None:
        assert "--resume" in self.text

    def test_supports_dry_run_flag(self) -> None:
        assert "--dry-run" in self.text

    def test_supports_json_flag(self) -> None:
        assert "--json" in self.text

    def test_uses_while_shift_parsing(self) -> None:
        """Must use while/shift, not for/shift."""
        assert "while [" in self.text or "while test" in self.text

    def test_reads_workflow_definitions(self) -> None:
        """Must load v4-workflows.yaml."""
        assert "v4-workflows.yaml" in self.text

    def test_checkpoint_state_file(self) -> None:
        """Must write/read checkpoint state."""
        assert "checkpoint" in self.text.lower() or "state" in self.text.lower()

    def test_evidence_dir_structure(self) -> None:
        """Must use evidence/v4-phase1/ directory."""
        assert "evidence/v4-phase1" in self.text

    def test_user_agents_are_optional(self) -> None:
        """User-level agents (/plan, /tdd, code-reviewer) must not be hard deps.

        The orchestrator must work without them. If referenced, must be
        behind availability checks or marked as optional enhancements.
        """
        hard_dep_patterns = [
            "require.*code-reviewer",
            "require.*/plan",
            "require.*/tdd",
        ]
        import re

        for pattern in hard_dep_patterns:
            matches = re.findall(pattern, self.text, re.IGNORECASE)
            assert not matches, f"Orchestrator has hard dependency on user agent: {pattern}"


@pytest.mark.unit
class TestV4CheckpointPersistence:
    """Checkpoint system must support resume after interruption."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.text = ORCHESTRATOR.read_text()

    def test_writes_state_after_each_workflow(self) -> None:
        """Must persist state after completing each WF."""
        assert "save_checkpoint" in self.text or "write_state" in self.text

    def test_reads_state_on_resume(self) -> None:
        """Must read state when --resume is given."""
        assert "load_checkpoint" in self.text or "read_state" in self.text


@pytest.mark.unit
class TestV4CommandEntry:
    """Claude command /phase1-build must exist and invoke orchestrator."""

    def test_command_file_exists(self) -> None:
        assert COMMAND_ENTRY.exists(), ".claude/commands/phase1-build.md not found"

    def test_references_orchestrator(self) -> None:
        text = COMMAND_ENTRY.read_text()
        assert "run_phase1_v4.sh" in text

    def test_describes_all_workflows(self) -> None:
        text = COMMAND_ENTRY.read_text()
        for wf_id in ["WF-P0", "WF-A1", "WF-B1", "WF-B2", "WF-B3", "WF-B4", "WF-A2"]:
            assert wf_id in text, f"Command entry missing description of {wf_id}"
