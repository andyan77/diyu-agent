"""S3-3: Skill lifecycle management tests.

Tests: 5 state transitions (draft->active->deprecated->disabled + disabled->active),
registration, deregistration, invalid transitions, execution gating.
"""

from __future__ import annotations

import pytest

from src.ports.skill_registry import SkillDefinition, SkillStatus
from src.skill.registry.lifecycle import (
    InvalidTransitionError,
    LifecycleRegistry,
    SkillNotFoundError,
)


@pytest.fixture
def registry() -> LifecycleRegistry:
    return LifecycleRegistry()


def _make_definition(skill_id: str = "test-skill") -> SkillDefinition:
    return SkillDefinition(
        skill_id=skill_id,
        name="Test Skill",
        description="A test skill",
        intent_types=["test_intent"],
        version="1.0.0",
    )


class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_returns_draft_status(self, registry: LifecycleRegistry) -> None:
        defn = _make_definition()
        result = await registry.register(defn)
        assert result.status == SkillStatus.DRAFT
        assert result.skill_id == "test-skill"

    @pytest.mark.asyncio
    async def test_register_forces_draft_regardless_of_input(
        self, registry: LifecycleRegistry
    ) -> None:
        defn = SkillDefinition(
            skill_id="sneaky",
            name="Sneaky",
            description="Tries to register as active",
            intent_types=["x"],
            status=SkillStatus.ACTIVE,
        )
        result = await registry.register(defn)
        assert result.status == SkillStatus.DRAFT

    @pytest.mark.asyncio
    async def test_deregister_removes_skill(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        await registry.deregister("test-skill")
        assert registry.get_definition("test-skill") is None

    @pytest.mark.asyncio
    async def test_deregister_unknown_skill_raises(self, registry: LifecycleRegistry) -> None:
        with pytest.raises(SkillNotFoundError):
            await registry.deregister("nonexistent")


class TestStateTransitions:
    """Cover all 5 state transitions per task card."""

    @pytest.mark.asyncio
    async def test_draft_to_active(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        result = await registry.update_status("test-skill", SkillStatus.ACTIVE)
        assert result.status == SkillStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_active_to_deprecated(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        result = await registry.update_status("test-skill", SkillStatus.DEPRECATED)
        assert result.status == SkillStatus.DEPRECATED

    @pytest.mark.asyncio
    async def test_deprecated_to_disabled(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        await registry.update_status("test-skill", SkillStatus.DEPRECATED)
        result = await registry.update_status("test-skill", SkillStatus.DISABLED)
        assert result.status == SkillStatus.DISABLED

    @pytest.mark.asyncio
    async def test_active_to_disabled(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        result = await registry.update_status("test-skill", SkillStatus.DISABLED)
        assert result.status == SkillStatus.DISABLED

    @pytest.mark.asyncio
    async def test_disabled_to_active_reenable(self, registry: LifecycleRegistry) -> None:
        """5th transition: re-enable a disabled skill."""
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        await registry.update_status("test-skill", SkillStatus.DISABLED)
        result = await registry.update_status("test-skill", SkillStatus.ACTIVE)
        assert result.status == SkillStatus.ACTIVE


class TestInvalidTransitions:
    @pytest.mark.asyncio
    async def test_draft_to_deprecated_rejected(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        with pytest.raises(InvalidTransitionError):
            await registry.update_status("test-skill", SkillStatus.DEPRECATED)

    @pytest.mark.asyncio
    async def test_draft_to_disabled_rejected(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        with pytest.raises(InvalidTransitionError):
            await registry.update_status("test-skill", SkillStatus.DISABLED)

    @pytest.mark.asyncio
    async def test_deprecated_to_active_rejected(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        await registry.update_status("test-skill", SkillStatus.DEPRECATED)
        with pytest.raises(InvalidTransitionError):
            await registry.update_status("test-skill", SkillStatus.ACTIVE)

    @pytest.mark.asyncio
    async def test_update_unknown_skill_raises(self, registry: LifecycleRegistry) -> None:
        with pytest.raises(SkillNotFoundError):
            await registry.update_status("nonexistent", SkillStatus.ACTIVE)


class TestFindSkill:
    @pytest.mark.asyncio
    async def test_find_active_skill(self, registry: LifecycleRegistry) -> None:
        from uuid import UUID

        from src.shared.types import OrganizationContext

        org = OrganizationContext(
            user_id=UUID(int=1),
            org_id=UUID(int=2),
            org_tier="brand_hq",
            org_path="root.brand",
        )
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        result = await registry.find_skill("test_intent", org)
        assert result is not None
        assert result.skill_id == "test-skill"

    @pytest.mark.asyncio
    async def test_find_skill_returns_none_for_draft(self, registry: LifecycleRegistry) -> None:
        from uuid import UUID

        from src.shared.types import OrganizationContext

        org = OrganizationContext(
            user_id=UUID(int=1),
            org_id=UUID(int=2),
            org_tier="brand_hq",
            org_path="root.brand",
        )
        await registry.register(_make_definition())
        result = await registry.find_skill("test_intent", org)
        assert result is None

    @pytest.mark.asyncio
    async def test_find_skill_returns_none_for_unknown_intent(
        self, registry: LifecycleRegistry
    ) -> None:
        from uuid import UUID

        from src.shared.types import OrganizationContext

        org = OrganizationContext(
            user_id=UUID(int=1),
            org_id=UUID(int=2),
            org_tier="brand_hq",
            org_path="root.brand",
        )
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        result = await registry.find_skill("unknown_intent", org)
        assert result is None


class TestListSkills:
    @pytest.mark.asyncio
    async def test_list_all(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition("a"))
        await registry.register(_make_definition("b"))
        assert len(registry.list_skills()) == 2

    @pytest.mark.asyncio
    async def test_list_by_status(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition("a"))
        await registry.register(_make_definition("b"))
        await registry.update_status("a", SkillStatus.ACTIVE)
        active = registry.list_skills(status=SkillStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].skill_id == "a"


class TestCanHandle:
    @pytest.mark.asyncio
    async def test_active_skill_can_handle(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        conf = await registry.can_handle("test_intent", "test-skill")
        assert conf == 1.0

    @pytest.mark.asyncio
    async def test_inactive_skill_cannot_handle(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        conf = await registry.can_handle("test_intent", "test-skill")
        assert conf == 0.0

    @pytest.mark.asyncio
    async def test_wrong_intent_cannot_handle(self, registry: LifecycleRegistry) -> None:
        await registry.register(_make_definition())
        await registry.update_status("test-skill", SkillStatus.ACTIVE)
        conf = await registry.can_handle("wrong_intent", "test-skill")
        assert conf == 0.0
