"""Tests for 4 gap closures identified in consistency audit.

Gap 1: enforce_workflow_role.py must be called by W1-W4 scripts
Gap 2: check_acceptance_commands.sh must have Makefile target
Gap 3: replay_skill_session.py must have Makefile target
Gap 4: evidence/ directory must use consistent naming (hyphen only)

TDD: These tests are written FIRST (RED), then implementation follows (GREEN).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_SCRIPTS_DIR = ROOT / ".claude" / "skills" / "taskcard-governance" / "scripts"
MAKEFILE = ROOT / "Makefile"
EVIDENCE_DIR = ROOT / "evidence"


# ---------------------------------------------------------------------------
# Gap 1: enforce_workflow_role.py must be called by W1-W4 workflow scripts
# ---------------------------------------------------------------------------
class TestGap1EnforceWorkflowRoleIntegration:
    """W1-W4 scripts must delegate role enforcement to enforce_workflow_role.py."""

    WORKFLOW_SCRIPTS = sorted(WORKFLOW_SCRIPTS_DIR.glob("run_w[1-4]*.sh"))

    @pytest.mark.parametrize(
        "script",
        WORKFLOW_SCRIPTS,
        ids=[s.name for s in WORKFLOW_SCRIPTS],
    )
    def test_calls_enforce_workflow_role(self, script: Path) -> None:
        """Each W1-W4 script must call enforce_workflow_role.py for auditable role check."""
        text = script.read_text()
        assert "enforce_workflow_role.py" in text, (
            f"{script.name} must call scripts/enforce_workflow_role.py "
            f"for auditable role enforcement (Gap 1)"
        )

    @pytest.mark.parametrize(
        "script",
        WORKFLOW_SCRIPTS,
        ids=[s.name for s in WORKFLOW_SCRIPTS],
    )
    def test_passes_expected_role_flag(self, script: Path) -> None:
        """enforce_workflow_role.py must be called with --expected WN matching the script."""
        text = script.read_text()
        # Extract which W this script is for from filename (run_w1_*, run_w2_*, etc.)
        match = re.search(r"run_w(\d)", script.name)
        if not match:
            pytest.skip(f"Cannot determine workflow number from {script.name}")
        expected_role = f"W{match.group(1)}"
        assert f"--expected {expected_role}" in text, (
            f"{script.name} must pass --expected {expected_role} to enforce_workflow_role.py"
        )

    @pytest.mark.parametrize(
        "script",
        WORKFLOW_SCRIPTS,
        ids=[s.name for s in WORKFLOW_SCRIPTS],
    )
    def test_passes_session_flag(self, script: Path) -> None:
        """enforce_workflow_role.py must receive --session for audit trail."""
        text = script.read_text()
        assert "--session" in text, (
            f"{script.name} must pass --session to enforce_workflow_role.py for audit trail"
        )

    @pytest.mark.parametrize(
        "script",
        WORKFLOW_SCRIPTS,
        ids=[s.name for s in WORKFLOW_SCRIPTS],
    )
    def test_passes_log_dir_flag(self, script: Path) -> None:
        """enforce_workflow_role.py must receive --log-dir for structured logging."""
        text = script.read_text()
        assert "--log-dir" in text, f"{script.name} must pass --log-dir to enforce_workflow_role.py"


# ---------------------------------------------------------------------------
# Gap 2: check_acceptance_commands.sh must have Makefile target
# ---------------------------------------------------------------------------
class TestGap2MakefileAcceptanceCommands:
    """Makefile must expose check_acceptance_commands.sh as a target."""

    def test_makefile_has_check_acceptance_commands_target(self) -> None:
        text = MAKEFILE.read_text()
        assert re.search(r"^check-acceptance-commands:", text, re.MULTILINE), (
            "Makefile must have 'check-acceptance-commands' target "
            "to expose scripts/check_acceptance_commands.sh (Gap 2)"
        )

    def test_makefile_target_calls_correct_script(self) -> None:
        text = MAKEFILE.read_text()
        assert "check_acceptance_commands.sh" in text, (
            "Makefile check-acceptance-commands target must call "
            "scripts/check_acceptance_commands.sh"
        )

    def test_makefile_phony_includes_target(self) -> None:
        text = MAKEFILE.read_text()
        # Check the .PHONY line includes the new target
        phony_match = re.search(r"\.PHONY:(.+?)(?:\n\S|\Z)", text, re.DOTALL)
        if phony_match:
            phony_text = phony_match.group(1)
            assert "check-acceptance-commands" in phony_text, (
                ".PHONY must include check-acceptance-commands"
            )


# ---------------------------------------------------------------------------
# Gap 3: replay_skill_session.py must have Makefile target
# ---------------------------------------------------------------------------
class TestGap3MakefileReplaySkillSession:
    """Makefile must expose replay_skill_session.py as a target."""

    def test_makefile_has_replay_session_target(self) -> None:
        text = MAKEFILE.read_text()
        assert re.search(r"^replay-skill-session:", text, re.MULTILINE), (
            "Makefile must have 'replay-skill-session' target "
            "to expose scripts/skills/replay_skill_session.py (Gap 3)"
        )

    def test_makefile_target_calls_correct_script(self) -> None:
        text = MAKEFILE.read_text()
        assert "replay_skill_session.py" in text, (
            "Makefile replay-skill-session target must call scripts/skills/replay_skill_session.py"
        )


# ---------------------------------------------------------------------------
# Gap 4: evidence/ directory must use consistent naming
# ---------------------------------------------------------------------------
class TestGap4EvidenceDirectoryNaming:
    """evidence/ subdirectories must use hyphen-only naming (phase-N, not phase_N)."""

    def test_no_underscore_phase_directories(self) -> None:
        if not EVIDENCE_DIR.exists():
            pytest.skip("evidence/ directory not found")
        bad_dirs = [
            d.name for d in EVIDENCE_DIR.iterdir() if d.is_dir() and re.match(r"phase_\d+", d.name)
        ]
        assert not bad_dirs, (
            f"evidence/ contains underscore-named directories {bad_dirs}; "
            f"must use hyphen format (phase-N) for consistency (Gap 4)"
        )

    def test_hyphen_phase_directories_exist(self) -> None:
        """At least phase-0 through phase-5 should exist with hyphen format."""
        if not EVIDENCE_DIR.exists():
            pytest.skip("evidence/ directory not found")
        # Only assert when phase dirs are actually present (local dev).
        # CI creates evidence/<sha> but not the phase-N subdirs.
        phase_dirs = [
            d for d in EVIDENCE_DIR.iterdir() if d.is_dir() and d.name.startswith("phase-")
        ]
        if not phase_dirs:
            pytest.skip("No phase-* directories present (CI or fresh clone)")
        for i in range(6):
            phase_dir = EVIDENCE_DIR / f"phase-{i}"
            assert phase_dir.exists(), f"evidence/phase-{i} must exist (hyphen format)"
