"""B3-1: Skill Router tests.

Tests: routing accuracy >= 95%, chat fallback, confidence threshold, hint matching.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from src.brain.skill.router import SkillRouter
from src.ports.skill_registry import SkillDefinition, SkillStatus
from src.shared.types import OrganizationContext
from src.skill.registry.lifecycle import LifecycleRegistry


@pytest.fixture
def org_context() -> OrganizationContext:
    return OrganizationContext(
        user_id=UUID(int=1),
        org_id=UUID(int=2),
        org_tier="brand_hq",
        org_path="root.brand",
    )


@pytest.fixture
async def registry_with_skills() -> LifecycleRegistry:
    reg = LifecycleRegistry()
    for skill_id, intents in [
        ("content_writer", ["generate_content", "write_content", "create_article"]),
        ("merchandising", ["merchandising", "product_recommendation"]),
    ]:
        await reg.register(
            SkillDefinition(
                skill_id=skill_id,
                name=skill_id.replace("_", " ").title(),
                description=f"{skill_id} skill",
                intent_types=intents,
            )
        )
        await reg.update_status(skill_id, SkillStatus.ACTIVE)
    return reg


class TestChatFallback:
    @pytest.mark.asyncio
    async def test_chat_intent_not_routed(
        self, registry_with_skills: LifecycleRegistry, org_context: OrganizationContext
    ) -> None:
        router = SkillRouter(registry=registry_with_skills)
        result = await router.route("chat", org_context)
        assert result.routed is False
        assert "chat" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_unknown_intent_not_routed(
        self, registry_with_skills: LifecycleRegistry, org_context: OrganizationContext
    ) -> None:
        router = SkillRouter(registry=registry_with_skills)
        result = await router.route("unknown_type", org_context)
        assert result.routed is False


class TestSkillRouting:
    @pytest.mark.asyncio
    async def test_route_to_content_writer(
        self, registry_with_skills: LifecycleRegistry, org_context: OrganizationContext
    ) -> None:
        router = SkillRouter(registry=registry_with_skills)
        result = await router.route(
            "skill",
            org_context,
            matched_skill_hint="generate_content",
        )
        assert result.routed is True
        assert result.skill is not None
        assert result.skill.skill_id == "content_writer"

    @pytest.mark.asyncio
    async def test_route_to_merchandising(
        self, registry_with_skills: LifecycleRegistry, org_context: OrganizationContext
    ) -> None:
        router = SkillRouter(registry=registry_with_skills)
        result = await router.route(
            "skill",
            org_context,
            matched_skill_hint="merchandising",
        )
        assert result.routed is True
        assert result.skill is not None
        assert result.skill.skill_id == "merchandising"


class TestConfidenceThreshold:
    @pytest.mark.asyncio
    async def test_high_confidence_routed(
        self, registry_with_skills: LifecycleRegistry, org_context: OrganizationContext
    ) -> None:
        router = SkillRouter(registry=registry_with_skills, confidence_threshold=0.5)
        result = await router.route("skill", org_context, matched_skill_hint="generate_content")
        assert result.routed is True
        assert result.confidence >= 0.5


class TestRoutingAccuracy:
    """Test routing accuracy across a test set (>= 95% per task card)."""

    @pytest.mark.asyncio
    async def test_routing_accuracy_on_test_set(
        self, registry_with_skills: LifecycleRegistry, org_context: OrganizationContext
    ) -> None:
        router = SkillRouter(registry=registry_with_skills)
        test_cases = [
            # (intent_type, hint, expected_skill_id_or_none)
            ("chat", None, None),
            ("chat", "generate_content", None),  # chat always wins
            ("skill", "generate_content", "content_writer"),
            ("skill", "write_content", "content_writer"),
            ("skill", "create_article", "content_writer"),
            ("skill", "merchandising", "merchandising"),
            ("skill", "product_recommendation", "merchandising"),
            ("skill", "unknown_skill", None),
            ("skill", None, None),
            ("unknown", None, None),
            ("skill", "generate_content", "content_writer"),
            ("skill", "merchandising", "merchandising"),
            ("chat", None, None),
            ("skill", "create_article", "content_writer"),
            ("skill", "product_recommendation", "merchandising"),
            ("chat", None, None),
            ("skill", "write_content", "content_writer"),
            ("skill", "merchandising", "merchandising"),
            ("skill", "generate_content", "content_writer"),
            ("chat", "merchandising", None),
        ]

        correct = 0
        for intent, hint, expected in test_cases:
            result = await router.route(intent, org_context, matched_skill_hint=hint)
            actual = result.skill.skill_id if result.routed and result.skill else None
            if actual == expected:
                correct += 1

        accuracy = correct / len(test_cases)
        assert accuracy >= 0.95, f"Routing accuracy {accuracy:.0%} < 95%"


class TestEmptyRegistry:
    @pytest.mark.asyncio
    async def test_empty_registry_fallback(self, org_context: OrganizationContext) -> None:
        router = SkillRouter(registry=LifecycleRegistry())
        result = await router.route("skill", org_context, matched_skill_hint="anything")
        assert result.routed is False
