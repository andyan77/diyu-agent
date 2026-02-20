"""B3-2: Skill orchestration tests.

Tests: end-to-end flow, knowledge resolution, skill execution, error handling,
success rate >= 90%.
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
    """Fake KnowledgePort that returns a static bundle."""

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def resolve(
        self,
        profile_id: str,
        query: str,
        org_context: OrganizationContext,
    ) -> KnowledgeBundle:
        if self._fail:
            msg = "Knowledge unavailable"
            raise RuntimeError(msg)
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
    reg = LifecycleRegistry()
    defn = SkillDefinition(
        skill_id="content_writer",
        name="Content Writer",
        description="Generate content",
        intent_types=["generate_content"],
    )
    await reg.register(defn)
    await reg.update_status("content_writer", SkillStatus.ACTIVE)
    reg.bind_implementation("content_writer", ContentWriterSkill())
    return reg


class TestOrchestrationPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, org_context: OrganizationContext) -> None:
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
            user_message="generate marketing content",
            params={"topic": "summer sale", "platform": "xiaohongshu"},
            matched_skill_hint="generate_content",
        )

        assert result.executed is True
        assert result.skill_id == "content_writer"
        assert result.skill_result is not None
        assert result.skill_result.success is True
        assert result.knowledge_used is True

    @pytest.mark.asyncio
    async def test_chat_intent_not_orchestrated(self, org_context: OrganizationContext) -> None:
        reg = await _setup_registry()
        router = SkillRouter(registry=reg)
        orch = SkillOrchestrator(router=router, registry=reg)

        result = await orch.orchestrate(
            intent_type="chat",
            org_context=org_context,
            user_message="hello",
        )

        assert result.executed is False
        assert result.skill_id is None


class TestKnowledgeDegradation:
    @pytest.mark.asyncio
    async def test_executes_without_knowledge_port(self, org_context: OrganizationContext) -> None:
        reg = await _setup_registry()
        router = SkillRouter(registry=reg)
        orch = SkillOrchestrator(router=router, registry=reg, knowledge=None)

        result = await orch.orchestrate(
            intent_type="skill",
            org_context=org_context,
            user_message="generate content",
            params={"topic": "test", "platform": "douyin"},
            matched_skill_hint="generate_content",
        )

        assert result.executed is True
        assert result.knowledge_used is False
        assert result.skill_result is not None
        assert result.skill_result.success is True

    @pytest.mark.asyncio
    async def test_executes_when_knowledge_fails(self, org_context: OrganizationContext) -> None:
        reg = await _setup_registry()
        router = SkillRouter(registry=reg)
        orch = SkillOrchestrator(
            router=router,
            registry=reg,
            knowledge=FakeKnowledgePort(fail=True),
        )

        result = await orch.orchestrate(
            intent_type="skill",
            org_context=org_context,
            user_message="generate content",
            params={"topic": "test", "platform": "wechat"},
            matched_skill_hint="generate_content",
        )

        assert result.executed is True
        assert result.knowledge_used is False
        assert result.skill_result is not None
        assert result.skill_result.success is True


class TestOrchestrationSuccessRate:
    """Task card: success rate >= 90%."""

    @pytest.mark.asyncio
    async def test_success_rate(self, org_context: OrganizationContext) -> None:
        reg = await _setup_registry()
        router = SkillRouter(registry=reg)
        orch = SkillOrchestrator(
            router=router,
            registry=reg,
            knowledge=FakeKnowledgePort(),
        )

        scenarios = [
            {"topic": "summer", "platform": "xiaohongshu"},
            {"topic": "winter", "platform": "douyin"},
            {"topic": "spring", "platform": "wechat"},
            {"topic": "autumn", "platform": "xiaohongshu"},
            {"topic": "new year", "platform": "douyin"},
            {"topic": "valentine", "platform": "wechat"},
            {"topic": "black friday", "platform": "xiaohongshu"},
            {"topic": "singles day", "platform": "douyin"},
            {"topic": "mid autumn", "platform": "wechat"},
            {"topic": "christmas", "platform": "xiaohongshu"},
        ]

        successes = 0
        for params in scenarios:
            result = await orch.orchestrate(
                intent_type="skill",
                org_context=org_context,
                user_message=f"generate content about {params['topic']}",
                params=params,
                matched_skill_hint="generate_content",
            )
            if result.executed and result.skill_result and result.skill_result.success:
                successes += 1

        rate = successes / len(scenarios)
        assert rate >= 0.90, f"Success rate {rate:.0%} < 90%"
