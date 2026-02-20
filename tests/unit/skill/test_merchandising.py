"""S3-2: MerchandisingSkill tests.

Tests: combination generation, scoring, output format, empty results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.skill.implementations.merchandising import MerchandisingSkill


@dataclass(frozen=True)
class FakeKnowledgeBundle:
    """Fake KnowledgeBundle for testing."""

    entities: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


@pytest.fixture
def skill() -> MerchandisingSkill:
    return MerchandisingSkill()


def _make_knowledge_with_rules() -> FakeKnowledgeBundle:
    return FakeKnowledgeBundle(
        entities={
            "StylingRule": [
                {
                    "source_sku": "SKU-001",
                    "target_sku": "SKU-002",
                    "compatibility_score": 0.9,
                    "target_category": "pants",
                    "name": "classic-combo",
                },
                {
                    "source_sku": "SKU-001",
                    "target_sku": "SKU-003",
                    "compatibility_score": 0.7,
                    "target_category": "shoes",
                    "name": "shoe-match",
                },
                {
                    "source_sku": "SKU-001",
                    "target_sku": "SKU-004",
                    "compatibility_score": 0.4,
                    "target_category": "accessories",
                    "name": "low-match",
                },
                {
                    "source_sku": "SKU-999",
                    "target_sku": "SKU-005",
                    "compatibility_score": 0.8,
                    "name": "other-combo",
                },
            ],
        }
    )


class TestMerchandisingProperties:
    def test_skill_id(self, skill: MerchandisingSkill) -> None:
        assert skill.skill_id == "merchandising"

    def test_intent_types(self, skill: MerchandisingSkill) -> None:
        assert "merchandising" in skill.intent_types

    def test_describe(self, skill: MerchandisingSkill) -> None:
        assert "outfit" in skill.describe().lower() or "combination" in skill.describe().lower()


class TestMerchandisingValidation:
    def test_valid_params(self, skill: MerchandisingSkill) -> None:
        result = skill.validate_params({"sku_id": "SKU-001"})
        assert result.valid is True

    def test_missing_sku(self, skill: MerchandisingSkill) -> None:
        result = skill.validate_params({})
        assert result.valid is False
        assert result.errors[0].field == "sku_id"


class TestMerchandisingExecution:
    @pytest.mark.asyncio
    async def test_returns_combinations(self, skill: MerchandisingSkill) -> None:
        """Task card: at least 1 combination returned."""
        knowledge = _make_knowledge_with_rules()
        result = await skill.execute(
            {"sku_id": "SKU-001"},
            knowledge,
            {},
        )
        assert result.success is True
        assert result.output is not None
        # Should find SKU-002 (0.9) and SKU-003 (0.7), not SKU-004 (0.4 < 0.6)
        assert result.output.metadata["combinations_count"] >= 1

    @pytest.mark.asyncio
    async def test_combinations_sorted_by_score(self, skill: MerchandisingSkill) -> None:
        knowledge = _make_knowledge_with_rules()
        result = await skill.execute(
            {"sku_id": "SKU-001"},
            knowledge,
            {},
        )
        assert result.output is not None
        artifacts = result.output.artifacts
        scores = [a["compatibility_score"] for a in artifacts]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_min_score_filter(self, skill: MerchandisingSkill) -> None:
        knowledge = _make_knowledge_with_rules()
        result = await skill.execute(
            {"sku_id": "SKU-001", "min_score": 0.8},
            knowledge,
            {},
        )
        assert result.output is not None
        for artifact in result.output.artifacts:
            assert artifact["compatibility_score"] >= 0.8

    @pytest.mark.asyncio
    async def test_category_filter(self, skill: MerchandisingSkill) -> None:
        knowledge = _make_knowledge_with_rules()
        result = await skill.execute(
            {"sku_id": "SKU-001", "category": "pants"},
            knowledge,
            {},
        )
        assert result.output is not None
        assert result.output.metadata["combinations_count"] == 1
        assert result.output.artifacts[0]["category"] == "pants"

    @pytest.mark.asyncio
    async def test_max_combinations_limit(self, skill: MerchandisingSkill) -> None:
        knowledge = _make_knowledge_with_rules()
        result = await skill.execute(
            {"sku_id": "SKU-001", "max_combinations": 1},
            knowledge,
            {},
        )
        assert result.output is not None
        assert result.output.metadata["combinations_count"] <= 1

    @pytest.mark.asyncio
    async def test_no_matches_returns_message(self, skill: MerchandisingSkill) -> None:
        knowledge = _make_knowledge_with_rules()
        result = await skill.execute(
            {"sku_id": "NONEXISTENT"},
            knowledge,
            {},
        )
        assert result.success is True
        assert result.output is not None
        assert result.output.metadata["combinations_count"] == 0
        assert "No matching" in result.output.content

    @pytest.mark.asyncio
    async def test_empty_knowledge_handled(self, skill: MerchandisingSkill) -> None:
        result = await skill.execute(
            {"sku_id": "SKU-001"},
            FakeKnowledgeBundle(),
            {},
        )
        assert result.success is True
        assert result.output is not None
        assert result.output.metadata["combinations_count"] == 0

    @pytest.mark.asyncio
    async def test_none_knowledge_handled(self, skill: MerchandisingSkill) -> None:
        result = await skill.execute(
            {"sku_id": "SKU-001"},
            None,
            {},
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_output_content_format(self, skill: MerchandisingSkill) -> None:
        knowledge = _make_knowledge_with_rules()
        result = await skill.execute(
            {"sku_id": "SKU-001"},
            knowledge,
            {},
        )
        assert result.output is not None
        assert "SKU-001" in result.output.content
        assert "%" in result.output.content  # score as percentage
