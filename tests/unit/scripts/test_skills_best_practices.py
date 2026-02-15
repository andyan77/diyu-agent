"""Tests for skills official best practices (D7 requirements).

Covers:
- SKILL.md frontmatter contains only name + description (no metadata)
- description includes trigger semantics
- agents/openai.yaml exists with required fields
- openai.yaml default_prompt includes $skill-name
- String fields in openai.yaml are quoted
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = ROOT / ".claude" / "skills"

ALL_SKILLS = [
    "taskcard-governance",
    "systematic-review",
    "cross-reference-audit",
    "adversarial-fix-verification",
    "guard-layer-boundary",
    "guard-port-compat",
    "guard-migration-safety",
    "guard-taskcard-schema",
]


class TestFrontmatterCompliance:
    """SKILL.md frontmatter must contain only name + description."""

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_frontmatter_starts_with_delimiter(self, skill: str) -> None:
        path = SKILLS_DIR / skill / "SKILL.md"
        text = path.read_text()
        assert text.startswith("---"), f"{skill}/SKILL.md missing frontmatter delimiter"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_frontmatter_has_name(self, skill: str) -> None:
        text = (SKILLS_DIR / skill / "SKILL.md").read_text()
        fm = text.split("---")[1]
        assert "name:" in fm, f"{skill} frontmatter missing name"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_frontmatter_has_description(self, skill: str) -> None:
        text = (SKILLS_DIR / skill / "SKILL.md").read_text()
        fm = text.split("---")[1]
        assert "description:" in fm, f"{skill} frontmatter missing description"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_frontmatter_no_metadata(self, skill: str) -> None:
        text = (SKILLS_DIR / skill / "SKILL.md").read_text()
        fm = text.split("---")[1]
        assert "metadata:" not in fm, f"{skill} frontmatter contains forbidden 'metadata'"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_description_has_trigger_semantics(self, skill: str) -> None:
        """Description must include when-to-trigger language."""
        text = (SKILLS_DIR / skill / "SKILL.md").read_text()
        fm = text.split("---")[1]
        # Extract description: handle both single-line and block scalar (>-, |-)
        desc_match = re.search(r"description:\s*[>|]-?\s*\n((?:\s+.+\n?)+)", fm)
        if not desc_match:
            desc_match = re.search(r"description:\s*(.+)", fm)
        assert desc_match, f"{skill} could not extract description"
        desc = desc_match.group(1).lower()
        trigger_words = ["use when", "use after", "use before", "invokes", "use for"]
        has_trigger = any(tw in desc for tw in trigger_words)
        assert has_trigger, f"{skill} description lacks trigger semantics"


class TestOpenAIYamlCompliance:
    """agents/openai.yaml must exist with required interface fields."""

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_openai_yaml_exists(self, skill: str) -> None:
        path = SKILLS_DIR / skill / "agents" / "openai.yaml"
        assert path.exists(), f"{skill}/agents/openai.yaml missing"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_has_display_name(self, skill: str) -> None:
        text = (SKILLS_DIR / skill / "agents" / "openai.yaml").read_text()
        assert "display_name" in text, f"{skill} openai.yaml missing display_name"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_has_short_description(self, skill: str) -> None:
        text = (SKILLS_DIR / skill / "agents" / "openai.yaml").read_text()
        assert "short_description" in text, f"{skill} openai.yaml missing short_description"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_has_default_prompt(self, skill: str) -> None:
        text = (SKILLS_DIR / skill / "agents" / "openai.yaml").read_text()
        assert "default_prompt" in text, f"{skill} openai.yaml missing default_prompt"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_default_prompt_has_skill_ref(self, skill: str) -> None:
        """default_prompt must include $skill-name."""
        text = (SKILLS_DIR / skill / "agents" / "openai.yaml").read_text()
        assert "$" in text, f"{skill} openai.yaml default_prompt missing $skill-name"

    @pytest.mark.parametrize("skill", ALL_SKILLS)
    def test_string_fields_quoted(self, skill: str) -> None:
        """All string value fields must be quoted."""
        text = (SKILLS_DIR / skill / "agents" / "openai.yaml").read_text()
        for line in text.strip().splitlines():
            if ":" in line and not line.strip().startswith("#"):
                key, _, val = line.partition(":")
                val = val.strip()
                # Skip nested keys (no value) and empty values
                if not val or val.endswith(":"):
                    continue
                is_quoted = val.startswith('"') or val.startswith("'")
                assert is_quoted, f"{skill} openai.yaml: unquoted value for '{key.strip()}': {val}"
