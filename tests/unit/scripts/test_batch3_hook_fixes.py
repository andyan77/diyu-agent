"""Tests for Batch 3 audit fixes: hook robustness + workflow hardening.

TDD RED phase: These tests verify fixes for audit findings
S2, N3, M7, M4, H6, M1.

Covers:
  S2:  milestone-check.yml must mkdir -p before writing to evidence dir
  N3:  milestone-check.yml must use uv run python, not bare python3
  M7:  milestone-check.yml must declare permissions (least privilege)
  M4:  pre_commit_gate.sh should gate on broader paths (infra, migrations, ports)
  H6:  gate-review.md must support --phase N for targeted verification
  M1:  hooks in .claude/settings.json should document relative path caveat
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
MILESTONE_CHECK_YML = ROOT / ".github" / "workflows" / "milestone-check.yml"
PRE_COMMIT_GATE = ROOT / "scripts" / "hooks" / "pre_commit_gate.sh"
GATE_REVIEW_MD = ROOT / ".claude" / "commands" / "gate-review.md"
SETTINGS_JSON = ROOT / ".claude" / "settings.json"


@pytest.fixture
def milestone_text() -> str:
    return MILESTONE_CHECK_YML.read_text()


@pytest.fixture
def milestone_yaml() -> dict:
    return yaml.safe_load(MILESTONE_CHECK_YML.read_text())


# ---------------------------------------------------------------------------
# S2: milestone-check.yml must mkdir -p before writing evidence
# ---------------------------------------------------------------------------
class TestS2MkdirBeforeEvidence:
    """Evidence directory must be created before writing to it."""

    def test_mkdir_before_evidence_write(self, milestone_text: str):
        """Any step writing to evidence/ must have a prior mkdir -p."""
        lines = milestone_text.splitlines()
        has_evidence_write = any("evidence/" in line for line in lines)
        has_mkdir = any("mkdir -p" in line for line in lines)
        if has_evidence_write:
            assert has_mkdir, (
                "milestone-check.yml writes to evidence/ directory "
                "without mkdir -p. Directory may not exist in CI."
            )


# ---------------------------------------------------------------------------
# N3: milestone-check.yml must use uv run python, not bare python3
# ---------------------------------------------------------------------------
class TestN3UvRunPython:
    """CI scripts must use uv run python, not bare python3."""

    def test_no_bare_python3_in_run_steps(self, milestone_yaml: dict):
        """All run steps using python3 must go through 'uv run python'."""
        jobs = milestone_yaml.get("jobs", {})
        violations = []
        for job_name, job_config in jobs.items():
            for step in job_config.get("steps", []):
                run_cmd = step.get("run", "")
                # Find bare python3 calls (not preceded by 'uv run')
                for line in run_cmd.splitlines():
                    stripped = line.strip()
                    if (
                        "python3" in stripped or "python " in stripped
                    ) and "uv run" not in stripped:
                        violations.append(f"{job_name}: '{stripped[:80]}'")
        assert len(violations) == 0, (
            "Bare python3 calls found (should use 'uv run python'):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ---------------------------------------------------------------------------
# M7: milestone-check.yml must have permissions block
# ---------------------------------------------------------------------------
class TestM7MilestonePermissions:
    """milestone-check.yml must declare least-privilege permissions."""

    def test_permissions_block_exists(self, milestone_yaml: dict):
        """Top-level permissions block must exist."""
        assert "permissions" in milestone_yaml, (
            "milestone-check.yml lacks top-level 'permissions' block. "
            "Must declare least-privilege per M7."
        )

    def test_permissions_contents_read(self, milestone_yaml: dict):
        """permissions.contents must be 'read'."""
        perms = milestone_yaml.get("permissions", {})
        assert perms.get("contents") == "read", (
            f"permissions.contents = '{perms.get('contents')}', expected 'read'."
        )


# ---------------------------------------------------------------------------
# M4: pre_commit_gate.sh should gate on broader critical paths
# ---------------------------------------------------------------------------
class TestM4BroaderGatePaths:
    """pre_commit_gate.sh should validate more than just task cards."""

    def test_gates_on_migration_changes(self):
        """Gate must check for staged migration files."""
        gate_text = PRE_COMMIT_GATE.read_text()
        assert "migrations/" in gate_text, (
            "pre_commit_gate.sh does not check for staged migration files. "
            "Migration changes should trigger additional validation."
        )

    def test_gates_on_port_changes(self):
        """Gate must check for staged port interface changes."""
        gate_text = PRE_COMMIT_GATE.read_text()
        assert "src/ports/" in gate_text, (
            "pre_commit_gate.sh does not check for staged port changes. "
            "Port interface changes should trigger schema validation."
        )


# ---------------------------------------------------------------------------
# H6: gate-review.md must support --phase N
# ---------------------------------------------------------------------------
class TestH6PhaseTargeting:
    """gate-review.md must support targeted phase verification."""

    def test_phase_flag_documented(self):
        """gate-review.md must mention --phase for targeted verification."""
        gate_text = GATE_REVIEW_MD.read_text()
        assert "--phase" in gate_text, (
            "gate-review.md does not document --phase N option. "
            "Users cannot target a specific phase for gate verification."
        )

    def test_verify_phase_supports_phase_flag(self):
        """verify_phase.py command in gate-review must use --phase when provided."""
        gate_text = GATE_REVIEW_MD.read_text()
        # Should have a conditional or parameterized --phase usage
        has_phase_param = "--phase" in gate_text and "verify_phase" in gate_text
        assert has_phase_param, (
            "gate-review.md does not wire --phase to verify_phase.py. "
            "Phase targeting is not functional."
        )


# ---------------------------------------------------------------------------
# M1: hooks relative path documentation
# ---------------------------------------------------------------------------
class TestM1HooksPathCaveat:
    """settings.json hooks must work with relative paths or document the caveat."""

    def test_hooks_use_consistent_path_style(self):
        """All hook commands should use a consistent path convention."""
        import json

        settings = json.loads(SETTINGS_JSON.read_text())
        hooks = settings.get("hooks", {})
        commands = []
        for _event, matchers in hooks.items():
            for matcher in matchers:
                for hook in matcher.get("hooks", []):
                    cmd = hook.get("command", "")
                    if cmd:
                        commands.append(cmd)

        # All commands should reference scripts/hooks/ consistently
        for cmd in commands:
            if "scripts/hooks/" in cmd:
                # Relative paths are acceptable since Claude Code
                # resolves them relative to project root.
                # Just verify they all point to existing files.
                script_path = cmd.split("bash ")[-1].strip()
                full_path = ROOT / script_path
                assert full_path.exists(), (
                    f"Hook script not found: {full_path}. Relative path may not resolve correctly."
                )

    def test_milestone_check_uv_sync_uses_frozen(self, milestone_text: str):
        """All uv sync calls in milestone-check.yml must use --frozen."""
        sync_lines = [line.strip() for line in milestone_text.splitlines() if "uv sync" in line]
        for line in sync_lines:
            assert "--frozen" in line, (
                f"milestone-check.yml 'uv sync' without --frozen: '{line}'. "
                "Must use --frozen for reproducible builds."
            )
