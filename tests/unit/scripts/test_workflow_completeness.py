"""Tests for Workflow completeness -- Section 12.2 compliance.

Every Workflow (run_w*.sh) must:
  (1) Be independently runnable
  (2) Support WORKFLOW_ROLE environment variable for role isolation
  (3) Have trap mechanism for failure state files
  (4) Be invocable via run_all.sh (orchestration)
  (5) Have corresponding test coverage
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_SCRIPTS_DIR = ROOT / ".claude" / "skills" / "taskcard-governance" / "scripts"
MAKEFILE = ROOT / "Makefile"


def _discover_workflow_scripts() -> list[Path]:
    if not WORKFLOW_SCRIPTS_DIR.exists():
        return []
    return sorted(WORKFLOW_SCRIPTS_DIR.glob("run_w*.sh"))


class TestWorkflowScriptsExist:
    """12.2: W1-W4 workflow scripts must exist."""

    def test_at_least_four_workflows(self) -> None:
        scripts = _discover_workflow_scripts()
        assert len(scripts) >= 4, (
            f"Expected at least 4 workflow scripts (W1-W4), found {len(scripts)}"
        )

    def test_run_all_exists(self) -> None:
        run_all = WORKFLOW_SCRIPTS_DIR / "run_all.sh"
        assert run_all.exists(), "run_all.sh orchestrator must exist"


class TestWorkflowRoleIsolation:
    """12.2: Each workflow must support WORKFLOW_ROLE isolation."""

    @pytest.mark.parametrize(
        "script",
        _discover_workflow_scripts(),
        ids=[s.name for s in _discover_workflow_scripts()],
    )
    def test_checks_workflow_role(self, script: Path) -> None:
        text = script.read_text()
        assert "WORKFLOW_ROLE" in text, (
            f"{script.name} must reference WORKFLOW_ROLE for role isolation"
        )

    def test_run_all_sets_role_per_step(self) -> None:
        run_all = WORKFLOW_SCRIPTS_DIR / "run_all.sh"
        if not run_all.exists():
            pytest.skip("run_all.sh not found")
        text = run_all.read_text()
        assert "WORKFLOW_ROLE=" in text, "run_all.sh must set WORKFLOW_ROLE for each workflow step"


class TestWorkflowTrapMechanism:
    """12.2: Workflows must have trap for failure state files."""

    @pytest.mark.parametrize(
        "script",
        _discover_workflow_scripts(),
        ids=[s.name for s in _discover_workflow_scripts()],
    )
    def test_has_trap(self, script: Path) -> None:
        text = script.read_text()
        assert "trap " in text, f"{script.name} must use trap for failure handling"

    @pytest.mark.parametrize(
        "script",
        _discover_workflow_scripts(),
        ids=[s.name for s in _discover_workflow_scripts()],
    )
    def test_produces_output_json(self, script: Path) -> None:
        text = script.read_text()
        assert "output.json" in text, f"{script.name} must produce output.json on completion"


class TestWorkflowExecutability:
    """12.2: All workflow scripts must be executable."""

    @pytest.mark.parametrize(
        "script",
        _discover_workflow_scripts(),
        ids=[s.name for s in _discover_workflow_scripts()],
    )
    def test_script_is_executable(self, script: Path) -> None:
        st = os.stat(script)
        assert st.st_mode & stat.S_IXUSR, f"{script.name} is not executable (chmod +x needed)"

    def test_run_all_is_executable(self) -> None:
        run_all = WORKFLOW_SCRIPTS_DIR / "run_all.sh"
        if not run_all.exists():
            pytest.skip("run_all.sh not found")
        st = os.stat(run_all)
        assert st.st_mode & stat.S_IXUSR, "run_all.sh must be executable"


class TestMakefileFullAudit:
    """12.6: Makefile must have full-audit target."""

    def test_full_audit_target_exists(self) -> None:
        assert MAKEFILE.exists(), "Makefile must exist"
        text = MAKEFILE.read_text()
        assert "full-audit" in text, "Makefile must have full-audit target (Section 12.6)"

    def test_full_audit_calls_script(self) -> None:
        if not MAKEFILE.exists():
            pytest.skip("Makefile not found")
        text = MAKEFILE.read_text()
        assert "full_audit" in text or "full-audit" in text, (
            "Makefile full-audit target must call scripts/full_audit.sh"
        )


class TestFullAuditCommandExists:
    """12.6: /full-audit slash command must be defined."""

    def test_command_file_exists(self) -> None:
        cmd_path = ROOT / ".claude" / "commands" / "full-audit.md"
        assert cmd_path.exists(), ".claude/commands/full-audit.md must exist (Section 12.6)"

    def test_command_references_make_target(self) -> None:
        cmd_path = ROOT / ".claude" / "commands" / "full-audit.md"
        if not cmd_path.exists():
            pytest.skip("full-audit.md not found")
        text = cmd_path.read_text()
        assert "full-audit" in text or "full_audit" in text, (
            "/full-audit command must reference make full-audit or scripts/full_audit.sh"
        )
