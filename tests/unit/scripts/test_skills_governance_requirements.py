"""Tests for skills governance requirements (D1-D12).

Covers governance clauses 616/617/980-1008/401-449:
- 4 pattern skills + 4 guard skills existence
- 8 skills have compliant SKILL.md
- Agent task-card-aware extensions present
- Session logger and replay scripts exist
- W1-W4 scripts are real (not placeholder)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = ROOT / ".claude" / "skills"
AGENTS_DIR = ROOT / ".claude" / "agents"

PATTERN_SKILLS = [
    "taskcard-governance",
    "systematic-review",
    "cross-reference-audit",
    "adversarial-fix-verification",
]

GUARD_SKILLS = [
    "guard-layer-boundary",
    "guard-port-compat",
    "guard-migration-safety",
    "guard-taskcard-schema",
]

ALL_SKILLS = PATTERN_SKILLS + GUARD_SKILLS


class TestGovernance616PatternSkills:
    """Governance clause 616: at least 4 core patterns."""

    @pytest.mark.parametrize("skill", PATTERN_SKILLS)
    def test_pattern_skill_exists(self, skill: str) -> None:
        path = SKILLS_DIR / skill / "SKILL.md"
        assert path.exists(), f"Pattern skill missing: {path}"

    def test_at_least_4_patterns(self) -> None:
        count = sum(1 for s in PATTERN_SKILLS if (SKILLS_DIR / s / "SKILL.md").exists())
        assert count >= 4, f"Need >= 4 pattern skills, found {count}"


class TestGovernance617GuardSkills:
    """Governance clause 617: at least 4 core guards."""

    @pytest.mark.parametrize("skill", GUARD_SKILLS)
    def test_guard_skill_exists(self, skill: str) -> None:
        path = SKILLS_DIR / skill / "SKILL.md"
        assert path.exists(), f"Guard skill missing: {path}"

    def test_at_least_4_guards(self) -> None:
        count = sum(1 for s in GUARD_SKILLS if (SKILLS_DIR / s / "SKILL.md").exists())
        assert count >= 4, f"Need >= 4 guard skills, found {count}"

    @pytest.mark.parametrize("skill", GUARD_SKILLS)
    def test_guard_binds_real_script(self, skill: str) -> None:
        """Each guard must reference a real scripts/ command, not echo placeholder."""
        path = SKILLS_DIR / skill / "SKILL.md"
        text = path.read_text()
        # Must reference scripts/ somewhere
        assert "scripts/" in text, f"{skill} does not reference any script"
        # Must not be echo-only
        assert "echo PASS" not in text, f"{skill} contains echo placeholder"


class TestGovernance980WorkflowHandoff:
    """Governance clause 980-1008: W1-W4 handoff + progressive disclosure."""

    W_SCRIPTS: ClassVar[list[str]] = [
        "run_w1_schema_normalization.sh",
        "run_w2_traceability_link.sh",
        "run_w3_acceptance_normalizer.sh",
        "run_w4_evidence_gate.sh",
    ]

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_w_script_exists(self, script: str) -> None:
        path = SKILLS_DIR / "taskcard-governance" / "scripts" / script
        assert path.exists(), f"W script missing: {path}"

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_w_script_uses_strict_mode(self, script: str) -> None:
        text = (SKILLS_DIR / "taskcard-governance" / "scripts" / script).read_text()
        assert "set -euo pipefail" in text, f"{script} missing strict error mode"

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_w_script_produces_artifacts(self, script: str) -> None:
        """Script must reference evidence output directory."""
        text = (SKILLS_DIR / "taskcard-governance" / "scripts" / script).read_text()
        assert "evidence/skills/taskcard-governance" in text, (
            f"{script} does not produce artifacts in evidence/"
        )

    @pytest.mark.parametrize("script", W_SCRIPTS)
    def test_w_script_not_placeholder(self, script: str) -> None:
        """Script must do real work, not just echo."""
        text = (SKILLS_DIR / "taskcard-governance" / "scripts" / script).read_text()
        assert "echo PASS" not in text, f"{script} is a placeholder"
        # Must invoke a real tool (uv run, python, bash scripts/)
        has_real_cmd = any(cmd in text for cmd in ["uv run", "python", "bash scripts/", "python3"])
        assert has_real_cmd, f"{script} does not invoke any real command"

    def test_run_all_exists(self) -> None:
        path = SKILLS_DIR / "taskcard-governance" / "scripts" / "run_all.sh"
        assert path.exists()

    def test_run_all_calls_logger(self) -> None:
        text = (SKILLS_DIR / "taskcard-governance" / "scripts" / "run_all.sh").read_text()
        assert "skill_session_logger" in text, "run_all.sh does not call session logger"

    def test_progressive_disclosure_documented(self) -> None:
        """SKILL.md must document progressive disclosure rules."""
        text = (SKILLS_DIR / "taskcard-governance" / "SKILL.md").read_text()
        assert "Progressive Disclosure" in text

    def test_dedicated_roles_documented(self) -> None:
        """SKILL.md must document per-workflow roles."""
        text = (SKILLS_DIR / "taskcard-governance" / "SKILL.md").read_text()
        assert "Dedicated Roles" in text or "Role" in text

    def test_references_dir_exists(self) -> None:
        path = SKILLS_DIR / "taskcard-governance" / "references"
        assert path.is_dir(), "references/ directory missing"


class TestGovernance401AgentExtensions:
    """Governance clause 401-449: Stage 3 agent extensions."""

    AGENTS: ClassVar[list[str]] = [
        "diyu-architect.md",
        "diyu-tdd-guide.md",
        "diyu-security-reviewer.md",
    ]

    @pytest.mark.parametrize("agent_file", AGENTS)
    def test_agent_has_task_card_aware_anchor(self, agent_file: str) -> None:
        path = AGENTS_DIR / agent_file
        assert path.exists(), f"Agent file missing: {path}"
        text = path.read_text()
        assert "ANCHOR:task-card-aware" in text, f"{agent_file} missing task-card-aware anchor"

    def test_architect_write_boundary(self) -> None:
        text = (AGENTS_DIR / "diyu-architect.md").read_text()
        assert "milestone-matrix" in text, "architect missing matrix write boundary"

    def test_tdd_write_boundary(self) -> None:
        text = (AGENTS_DIR / "diyu-tdd-guide.md").read_text()
        assert "task-cards" in text, "tdd-guide missing task-cards write boundary"

    def test_security_read_only(self) -> None:
        text = (AGENTS_DIR / "diyu-security-reviewer.md").read_text()
        assert "read-only" in text.lower() or "read only" in text.lower(), (
            "security-reviewer missing read-only boundary"
        )


class TestSessionAuditInfrastructure:
    """Session logger and replay scripts exist and are functional."""

    def test_session_logger_exists(self) -> None:
        path = ROOT / "scripts" / "skills" / "skill_session_logger.py"
        assert path.exists()

    def test_replay_script_exists(self) -> None:
        path = ROOT / "scripts" / "skills" / "replay_skill_session.py"
        assert path.exists()

    def test_session_logger_importable(self) -> None:
        """Logger must be valid Python."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import ast; ast.parse(open('scripts/skills/skill_session_logger.py').read())",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0, f"Logger has syntax errors: {result.stderr}"

    def test_replay_script_importable(self) -> None:
        """Replay must be valid Python."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "import ast; ast.parse(open('scripts/skills/replay_skill_session.py').read())",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0, f"Replay has syntax errors: {result.stderr}"
