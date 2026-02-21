"""Cross-layer E2E: Skill complete loop (X3-1).

Verifies: Intent -> SkillRouter -> Orchestrator -> ContentWriterSkill -> Response.
Uses Fake adapters (no external services required).

This is the HARD GATE test for Phase 3 cross-layer integration (TASK-INT-P3-SKILL).
All tests MUST pass without skip for the gate to be GO.

Covers:
    X3-1: Full skill invocation loop (intent match -> route -> execute -> result)
"""

from __future__ import annotations

from uuid import UUID

import pytest

from src.brain.skill.orchestrator import SkillOrchestrator
from src.brain.skill.router import SkillRouter
from src.ports.skill_registry import SkillDefinition, SkillStatus
from src.shared.types import KnowledgeBundle, OrganizationContext, ResolutionMetadata
from src.skill.implementations.content_writer import ContentWriterSkill
from src.skill.registry.lifecycle import LifecycleRegistry


@pytest.fixture
def org_context() -> OrganizationContext:
    return OrganizationContext(
        user_id=UUID(int=1),
        org_id=UUID(int=2),
        org_tier="brand_hq",
        org_path="root.brand",
    )


class FakeKnowledgePort:
    """Fake KnowledgePort for E2E skill tests."""

    async def resolve(
        self,
        profile_id: str,
        query: str,
        org_context: OrganizationContext,
    ) -> KnowledgeBundle:
        return KnowledgeBundle(
            entities={
                "BrandKnowledge": [
                    {"name": "Test Brand", "node_id": "1"},
                ]
            },
            metadata=ResolutionMetadata(profile_id=profile_id),
        )

    async def capabilities(self) -> set[str]:
        return {"resolve"}


async def _setup_registry() -> LifecycleRegistry:
    """Create a registry with content_writer skill registered and active."""
    reg = LifecycleRegistry()
    defn = SkillDefinition(
        skill_id="content_writer",
        name="Content Writer",
        description="Generate content",
        intent_types=["generate_content", "write_content", "create_article"],
    )
    await reg.register(defn)
    await reg.update_status("content_writer", SkillStatus.ACTIVE)
    reg.bind_implementation("content_writer", ContentWriterSkill())
    return reg


@pytest.mark.e2e
class TestSkillE2ECrossLayer:
    """Cross-layer skill complete loop verification (X3-1).

    Exercises: Intent -> SkillRouter -> SkillOrchestrator -> ContentWriterSkill
    using deterministic fakes (no external services).
    """

    async def test_intent_to_skill_route_and_execute(
        self,
        org_context: OrganizationContext,
    ) -> None:
        """X3-1: Intent match -> route -> execute -> result round-trip."""
        reg = await _setup_registry()
        router = SkillRouter(registry=reg)

        # Step 1: Route intent to skill
        route_result = await router.route(
            "skill",
            org_context,
            matched_skill_hint="generate_content",
        )
        assert route_result.routed is True
        assert route_result.skill.skill_id == "content_writer"

    async def test_full_orchestration_pipeline(
        self,
        org_context: OrganizationContext,
    ) -> None:
        """X3-1: Full orchestration pipeline (route + resolve knowledge + execute)."""
        reg = await _setup_registry()
        router = SkillRouter(registry=reg)
        orch = SkillOrchestrator(
            router=router,
            registry=reg,
            knowledge=FakeKnowledgePort(),
        )

        result = await orch.orchestrate(
            intent_type="skill",
            org_context=org_context,
            user_message="generate marketing content for summer sale",
            params={"topic": "summer sale", "platform": "xiaohongshu"},
            matched_skill_hint="generate_content",
        )

        assert result.executed is True
        assert result.skill_id == "content_writer"
        assert result.skill_result.success is True

    async def test_unregistered_skill_returns_not_routed(
        self,
        org_context: OrganizationContext,
    ) -> None:
        """X3-1: Unknown intent type should not route."""
        reg = await _setup_registry()
        router = SkillRouter(registry=reg)

        route_result = await router.route(
            "skill",
            org_context,
            matched_skill_hint="nonexistent_intent",
        )
        assert route_result.routed is False

    async def test_inactive_skill_not_routable(
        self,
        org_context: OrganizationContext,
    ) -> None:
        """X3-1: Inactive skill should not be routed to."""
        reg = LifecycleRegistry()
        defn = SkillDefinition(
            skill_id="disabled_skill",
            name="Disabled",
            description="Disabled skill",
            intent_types=["some_intent"],
        )
        await reg.register(defn)
        # Don't activate — stays in REGISTERED status

        router = SkillRouter(registry=reg)
        route_result = await router.route(
            "skill",
            org_context,
            matched_skill_hint="some_intent",
        )
        assert route_result.routed is False
