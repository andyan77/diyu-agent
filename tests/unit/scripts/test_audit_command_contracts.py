"""Tests for audit command contracts (R9 requirement).

Covers:
  - Command frontmatter contains allowed-tools
  - Skill SKILL.md references existing commands (no dangling)
  - Entry scripts do not swallow errors (no || true, no exit 0 forced)
  - Commands declare output paths
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
COMMANDS_DIR = ROOT / ".claude" / "commands"
SKILLS_DIR = ROOT / ".claude" / "skills"
SCRIPTS_DIR = ROOT / "scripts"

AUDIT_COMMANDS = [
    "systematic-review.md",
    "cross-reference-audit.md",
    "adversarial-fix-verify.md",
]

AUDIT_SKILLS = [
    "systematic-review",
    "cross-reference-audit",
    "adversarial-fix-verification",
]

ENTRY_SCRIPTS = [
    "run_systematic_review.sh",
    "run_cross_audit.sh",
    "run_fix_verify.sh",
]


class TestCommandFrontmatter:
    """Each audit command must have YAML frontmatter with allowed-tools."""

    @pytest.mark.parametrize("cmd_file", AUDIT_COMMANDS)
    def test_has_frontmatter(self, cmd_file: str) -> None:
        path = COMMANDS_DIR / cmd_file
        assert path.exists(), f"Command file missing: {path}"
        text = path.read_text()
        assert text.startswith("---"), f"{cmd_file} missing YAML frontmatter"
        # Must have closing ---
        parts = text.split("---", 2)
        assert len(parts) >= 3, f"{cmd_file} frontmatter not properly closed"

    @pytest.mark.parametrize("cmd_file", AUDIT_COMMANDS)
    def test_has_allowed_tools(self, cmd_file: str) -> None:
        path = COMMANDS_DIR / cmd_file
        text = path.read_text()
        frontmatter = text.split("---")[1]
        assert "allowed-tools" in frontmatter, f"{cmd_file} frontmatter missing 'allowed-tools'"

    @pytest.mark.parametrize("cmd_file", AUDIT_COMMANDS)
    def test_declares_output_path(self, cmd_file: str) -> None:
        path = COMMANDS_DIR / cmd_file
        text = path.read_text()
        assert "evidence/" in text, f"{cmd_file} does not declare output path in evidence/"


class TestSkillCommandReferences:
    """Skill SKILL.md must reference commands that actually exist."""

    @pytest.mark.parametrize("skill_name", AUDIT_SKILLS)
    def test_skill_exists(self, skill_name: str) -> None:
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_path.exists(), f"Skill missing: {skill_path}"

    @pytest.mark.parametrize("skill_name", AUDIT_SKILLS)
    def test_no_dangling_command_references(self, skill_name: str) -> None:
        """Every /command-name in skill must have a .claude/commands/<name>.md file."""
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        text = skill_path.read_text()
        # Find all /word-word patterns that look like command references
        # Exclude markdown paths like /src/... and URLs
        refs = re.findall(r"(?:^|\s)/([\w][\w-]*)", text)
        for ref in refs:
            # Skip common false positives
            if ref in ("src", "home", "usr", "bin", "etc", "tmp"):
                continue
            cmd_path = COMMANDS_DIR / f"{ref}.md"
            assert cmd_path.exists(), (
                f"Skill '{skill_name}' references /{ref} but "
                f"{cmd_path.relative_to(ROOT)} does not exist"
            )


class TestEntryScriptsNoErrorSwallowing:
    """Entry scripts must not swallow errors."""

    @pytest.mark.parametrize("script_name", ENTRY_SCRIPTS)
    def test_script_exists(self, script_name: str) -> None:
        path = SCRIPTS_DIR / script_name
        assert path.exists(), f"Entry script missing: {path}"

    @pytest.mark.parametrize("script_name", ENTRY_SCRIPTS)
    def test_no_pipe_true(self, script_name: str) -> None:
        """Scripts must not use || true to swallow errors."""
        text = (SCRIPTS_DIR / script_name).read_text()
        assert "|| true" not in text, f"{script_name} swallows errors with '|| true'"

    @pytest.mark.parametrize("script_name", ENTRY_SCRIPTS)
    def test_no_forced_exit_zero(self, script_name: str) -> None:
        """Scripts must not use 'exit 0' to force success."""
        text = (SCRIPTS_DIR / script_name).read_text()
        # Allow 'exit 0' only in comments
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            assert "exit 0" not in stripped, f"{script_name}:{i} forces success with 'exit 0'"

    @pytest.mark.parametrize("script_name", ENTRY_SCRIPTS)
    def test_uses_set_e(self, script_name: str) -> None:
        """Scripts must use set -e or set -euo pipefail."""
        text = (SCRIPTS_DIR / script_name).read_text()
        has_strict = "set -e" in text or "set -euo" in text
        assert has_strict, f"{script_name} does not use 'set -e' for error propagation"


class TestRootSkillMd:
    """Root .claude/skills/SKILL.md must exist and be valid."""

    def test_root_skill_exists(self) -> None:
        path = SKILLS_DIR / "SKILL.md"
        assert path.exists(), f"Root skill file missing: {path}"

    def test_root_skill_has_frontmatter(self) -> None:
        path = SKILLS_DIR / "SKILL.md"
        text = path.read_text()
        assert text.startswith("---"), "Root SKILL.md missing YAML frontmatter"
        parts = text.split("---", 2)
        assert len(parts) >= 3, "Root SKILL.md frontmatter not properly closed"

    def test_root_skill_has_name(self) -> None:
        path = SKILLS_DIR / "SKILL.md"
        text = path.read_text()
        frontmatter = text.split("---")[1]
        assert "name:" in frontmatter, "Root SKILL.md missing 'name' in frontmatter"

    def test_root_skill_references_existing_skills(self) -> None:
        """Cross-reference: skill names mentioned in root SKILL.md should exist as subdirs."""
        path = SKILLS_DIR / "SKILL.md"
        text = path.read_text()
        # Check that referenced skill names (adversarial-fix-verification, etc.) have dirs
        for skill_name in AUDIT_SKILLS:
            if skill_name in text:
                skill_dir = SKILLS_DIR / skill_name
                assert skill_dir.is_dir(), (
                    f"Root SKILL.md references '{skill_name}' but "
                    f"directory {skill_dir.relative_to(ROOT)} does not exist"
                )

    def test_root_skill_no_dangling_command_references(self) -> None:
        """Any /command-name in root SKILL.md must have a matching command file."""
        path = SKILLS_DIR / "SKILL.md"
        text = path.read_text()
        # Strip fenced code blocks to avoid false positives
        import re as _re

        text_clean = _re.sub(r"```.*?```", "", text, flags=_re.DOTALL)
        refs = _re.findall(r"(?:^|\s)/([\w][\w-]*)", text_clean)
        for ref in refs:
            if ref in ("src", "home", "usr", "bin", "etc", "tmp"):
                continue
            cmd_path = COMMANDS_DIR / f"{ref}.md"
            assert cmd_path.exists(), (
                f"Root SKILL.md references /{ref} but {cmd_path.relative_to(ROOT)} does not exist"
            )


class TestGateReviewNotBroken:
    """gate-review.md must still exist and be functional (R11)."""

    def test_gate_review_exists(self) -> None:
        path = COMMANDS_DIR / "gate-review.md"
        assert path.exists(), "gate-review.md was deleted or moved"

    def test_gate_review_has_frontmatter(self) -> None:
        text = (COMMANDS_DIR / "gate-review.md").read_text()
        assert text.startswith("---")
        assert "allowed-tools" in text.split("---")[1]

    def test_gate_review_independent_of_audit_commands(self) -> None:
        """gate-review must not depend on audit commands to function."""
        text = (COMMANDS_DIR / "gate-review.md").read_text()
        # gate-review should not reference the new audit commands
        assert "/systematic-review" not in text
        assert "/adversarial-fix-verify" not in text
