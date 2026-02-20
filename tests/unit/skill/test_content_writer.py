"""S3-1: ContentWriterSkill tests.

Tests: output format, required fields, brand context extraction, validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.skill.implementations.content_writer import ContentWriterSkill


@dataclass(frozen=True)
class FakeKnowledgeBundle:
    """Fake KnowledgeBundle for testing without importing full types."""

    entities: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    semantic_contents: list[dict[str, Any]] = field(default_factory=list)


@pytest.fixture
def skill() -> ContentWriterSkill:
    return ContentWriterSkill()


class TestContentWriterProperties:
    def test_skill_id(self, skill: ContentWriterSkill) -> None:
        assert skill.skill_id == "content_writer"

    def test_name(self, skill: ContentWriterSkill) -> None:
        assert skill.name == "Content Writer"

    def test_intent_types(self, skill: ContentWriterSkill) -> None:
        assert "generate_content" in skill.intent_types

    def test_describe(self, skill: ContentWriterSkill) -> None:
        desc = skill.describe()
        assert "marketing content" in desc.lower()


class TestContentWriterValidation:
    def test_valid_params(self, skill: ContentWriterSkill) -> None:
        result = skill.validate_params({"topic": "summer sale", "platform": "xiaohongshu"})
        assert result.valid is True

    def test_missing_topic(self, skill: ContentWriterSkill) -> None:
        result = skill.validate_params({"platform": "douyin"})
        assert result.valid is False
        assert any(e.field == "topic" for e in result.errors)

    def test_missing_platform(self, skill: ContentWriterSkill) -> None:
        result = skill.validate_params({"topic": "sale"})
        assert result.valid is False
        assert any(e.field == "platform" for e in result.errors)

    def test_missing_both(self, skill: ContentWriterSkill) -> None:
        result = skill.validate_params({})
        assert result.valid is False
        assert len(result.errors) == 2


class TestContentWriterExecution:
    @pytest.mark.asyncio
    async def test_success_output_has_content(self, skill: ContentWriterSkill) -> None:
        knowledge = FakeKnowledgeBundle()
        result = await skill.execute(
            {"topic": "summer collection", "platform": "xiaohongshu"},
            knowledge,
            {},
        )
        assert result.success is True
        assert result.output is not None
        assert "summer collection" in result.output.content
        assert "XIAOHONGSHU" in result.output.content

    @pytest.mark.asyncio
    async def test_output_has_artifacts(self, skill: ContentWriterSkill) -> None:
        result = await skill.execute(
            {"topic": "test", "platform": "douyin"},
            FakeKnowledgeBundle(),
            {},
        )
        assert result.output is not None
        assert len(result.output.artifacts) >= 1
        artifact = result.output.artifacts[0]
        assert artifact["type"] == "marketing_content"
        assert artifact["platform"] == "douyin"

    @pytest.mark.asyncio
    async def test_output_has_metadata(self, skill: ContentWriterSkill) -> None:
        result = await skill.execute(
            {"topic": "test", "platform": "wechat", "persona": "casual"},
            FakeKnowledgeBundle(),
            {},
        )
        assert result.output is not None
        assert result.output.metadata["platform"] == "wechat"
        assert result.output.metadata["persona"] == "casual"

    @pytest.mark.asyncio
    async def test_brand_context_used(self, skill: ContentWriterSkill) -> None:
        knowledge = FakeKnowledgeBundle(
            entities={
                "BrandKnowledge": [
                    {"name": "Luxe Brand", "node_id": "1"},
                ]
            }
        )
        result = await skill.execute(
            {"topic": "new arrivals", "platform": "xiaohongshu"},
            knowledge,
            {},
        )
        assert result.output is not None
        assert "Luxe Brand" in result.output.content

    @pytest.mark.asyncio
    async def test_default_persona(self, skill: ContentWriterSkill) -> None:
        result = await skill.execute(
            {"topic": "test", "platform": "douyin"},
            FakeKnowledgeBundle(),
            {},
        )
        assert result.output is not None
        assert "Professional" in result.output.content

    @pytest.mark.asyncio
    async def test_none_knowledge_handled(self, skill: ContentWriterSkill) -> None:
        result = await skill.execute(
            {"topic": "test", "platform": "wechat"},
            None,
            {},
        )
        assert result.success is True
