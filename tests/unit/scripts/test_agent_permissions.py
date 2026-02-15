"""Tests for agent permission consistency -- GAP-H3.

Verifies that agent tool permissions match their declared role:
- Read-only agents (security reviewer) must NOT have Write/Edit tools
- All agents must declare tools as a list
"""

from pathlib import Path

import pytest
import yaml

AGENTS_DIR = Path(".claude/agents")


def _load_agent_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from agent markdown file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        pytest.fail(f"{path} has no YAML frontmatter")
    end = text.index("---", 3)
    return yaml.safe_load(text[3:end])


def _extract_role_claim(path: Path) -> str:
    """Extract the role claim (read-only, etc.) from agent body."""
    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    if "read-only" in lower or "read only" in lower:
        return "read-only"
    return "read-write"


class TestAgentToolPermissions:
    """GAP-H3: Tool permissions must match role declarations."""

    @pytest.fixture
    def agent_files(self) -> list[Path]:
        if not AGENTS_DIR.exists():
            pytest.skip("No .claude/agents/ directory")
        files = list(AGENTS_DIR.glob("*.md"))
        if not files:
            pytest.skip("No agent files found")
        return files

    def test_all_agents_have_tools_list(self, agent_files: list[Path]) -> None:
        for path in agent_files:
            fm = _load_agent_frontmatter(path)
            assert "tools" in fm, f"{path.name} missing 'tools' in frontmatter"
            assert isinstance(fm["tools"], list), f"{path.name} tools must be a list"

    def test_readonly_agents_have_no_write_tools(self, agent_files: list[Path]) -> None:
        write_tools = {"Write", "Edit", "NotebookEdit"}
        for path in agent_files:
            role = _extract_role_claim(path)
            if role != "read-only":
                continue
            fm = _load_agent_frontmatter(path)
            tools = set(fm.get("tools", []))
            overlap = tools & write_tools
            assert not overlap, f"{path.name} claims read-only but has write tools: {overlap}"

    def test_security_reviewer_is_readonly(self) -> None:
        path = AGENTS_DIR / "diyu-security-reviewer.md"
        if not path.exists():
            pytest.skip("diyu-security-reviewer.md not found")
        fm = _load_agent_frontmatter(path)
        tools = set(fm.get("tools", []))
        write_tools = {"Write", "Edit", "NotebookEdit"}
        overlap = tools & write_tools
        assert not overlap, f"Security reviewer must be read-only but has: {overlap}"

    def test_security_reviewer_has_review_tools(self) -> None:
        path = AGENTS_DIR / "diyu-security-reviewer.md"
        if not path.exists():
            pytest.skip("diyu-security-reviewer.md not found")
        fm = _load_agent_frontmatter(path)
        tools = set(fm.get("tools", []))
        required = {"Read", "Grep", "Glob"}
        missing = required - tools
        assert not missing, f"Security reviewer missing review tools: {missing}"
