"""Skill lifecycle registry -- real implementation replacing Stub.

Task card: S3-3
- Register -> Enable -> Execute -> Disable -> Re-enable (5 transitions)
- Replaces Stub registry; Port interface (SkillRegistry) unchanged
- State machine: draft -> active -> deprecated -> disabled (+ disabled -> active)

Architecture: docs/architecture/03-Skill Section 8
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.ports.skill_registry import SkillDefinition, SkillRegistry, SkillResult, SkillStatus

if TYPE_CHECKING:
    from src.shared.types import KnowledgeBundle, OrganizationContext
    from src.skill.core.protocol import SkillProtocol

logger = logging.getLogger(__name__)

# Valid state transitions (current_status -> set of allowed next statuses)
VALID_TRANSITIONS: dict[SkillStatus, set[SkillStatus]] = {
    SkillStatus.DRAFT: {SkillStatus.ACTIVE},
    SkillStatus.ACTIVE: {SkillStatus.DEPRECATED, SkillStatus.DISABLED},
    SkillStatus.DEPRECATED: {SkillStatus.DISABLED},
    SkillStatus.DISABLED: {SkillStatus.ACTIVE},
}


class InvalidTransitionError(ValueError):
    """Raised when a skill state transition is not allowed."""

    def __init__(self, skill_id: str, current: SkillStatus, target: SkillStatus) -> None:
        self.skill_id = skill_id
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid transition for skill '{skill_id}': {current.value} -> {target.value}"
        )


class SkillNotFoundError(KeyError):
    """Raised when a skill is not found in the registry."""

    def __init__(self, skill_id: str) -> None:
        self.skill_id = skill_id
        super().__init__(f"Skill not found: {skill_id}")


class LifecycleRegistry(SkillRegistry):
    """Real SkillRegistry implementation with lifecycle management.

    Stores skill definitions and their implementations in-memory.
    Enforces state machine transitions per architecture spec.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, SkillDefinition] = {}
        self._implementations: dict[str, SkillProtocol] = {}

    # -- Day-1 discovery/dispatch methods --

    async def find_skill(
        self,
        intent_type: str,
        org_context: OrganizationContext,
    ) -> SkillDefinition | None:
        """Find an active skill matching the intent type."""
        for defn in self._definitions.values():
            if defn.status == SkillStatus.ACTIVE and intent_type in defn.intent_types:
                return defn
        return None

    async def can_handle(
        self,
        intent_type: str,
        skill_id: str,
    ) -> float:
        """Return confidence (0.0-1.0) that skill can handle intent."""
        defn = self._definitions.get(skill_id)
        if defn is None or defn.status != SkillStatus.ACTIVE:
            return 0.0
        if intent_type in defn.intent_types:
            return 1.0
        return 0.0

    async def execute(
        self,
        skill_id: str,
        knowledge: KnowledgeBundle,
        context: dict[str, Any],
    ) -> SkillResult:
        """Execute a skill with knowledge and context.

        Delegates to the registered SkillProtocol implementation.
        """
        defn = self._definitions.get(skill_id)
        if defn is None:
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error=f"Skill not found: {skill_id}",
            )

        if defn.status != SkillStatus.ACTIVE:
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error=f"Skill '{skill_id}' is not active (status={defn.status.value})",
            )

        impl = self._implementations.get(skill_id)
        if impl is None:
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error=f"No implementation registered for skill: {skill_id}",
            )

        params = context.get("params", {})

        # Validate params
        validation = impl.validate_params(params)
        if not validation.valid:
            error_msgs = [f"{e.field}: {e.message}" for e in validation.errors]
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error=f"Validation failed: {'; '.join(error_msgs)}",
            )

        try:
            result = await impl.execute(params, knowledge, context)
            return SkillResult(
                skill_id=skill_id,
                output=result.output.content if result.output else None,
                artifacts=[
                    *(result.output.artifacts if result.output else []),
                ],
                success=result.success,
                error=result.error,
            )
        except Exception as exc:
            logger.exception("Skill execution failed: %s", skill_id)
            return SkillResult(
                skill_id=skill_id,
                success=False,
                error=str(exc),
            )

    # -- Phase 3 lifecycle methods --

    async def register(
        self,
        definition: SkillDefinition,
    ) -> SkillDefinition:
        """Register a new skill definition.

        The skill starts in DRAFT status regardless of input status.
        """
        # Force DRAFT status on registration
        registered = SkillDefinition(
            skill_id=definition.skill_id,
            name=definition.name,
            description=definition.description,
            intent_types=definition.intent_types,
            version=definition.version,
            status=SkillStatus.DRAFT,
        )
        self._definitions[registered.skill_id] = registered
        logger.info("Registered skill: %s (status=draft)", registered.skill_id)
        return registered

    async def deregister(self, skill_id: str) -> None:
        """Remove a skill from the registry."""
        if skill_id not in self._definitions:
            raise SkillNotFoundError(skill_id)

        del self._definitions[skill_id]
        self._implementations.pop(skill_id, None)
        logger.info("Deregistered skill: %s", skill_id)

    async def update_status(
        self,
        skill_id: str,
        new_status: SkillStatus,
    ) -> SkillDefinition:
        """Update the lifecycle status of a skill.

        Enforces valid state transitions per the 4-state machine.
        """
        defn = self._definitions.get(skill_id)
        if defn is None:
            raise SkillNotFoundError(skill_id)

        allowed = VALID_TRANSITIONS.get(defn.status, set())
        if new_status not in allowed:
            raise InvalidTransitionError(skill_id, defn.status, new_status)

        updated = SkillDefinition(
            skill_id=defn.skill_id,
            name=defn.name,
            description=defn.description,
            intent_types=defn.intent_types,
            version=defn.version,
            status=new_status,
        )
        self._definitions[skill_id] = updated
        logger.info(
            "Skill '%s' status: %s -> %s",
            skill_id,
            defn.status.value,
            new_status.value,
        )
        return updated

    # -- Implementation binding --

    def bind_implementation(self, skill_id: str, impl: SkillProtocol) -> None:
        """Bind a SkillProtocol implementation to a registered skill."""
        if skill_id not in self._definitions:
            raise SkillNotFoundError(skill_id)
        self._implementations[skill_id] = impl

    # -- Query helpers --

    def get_definition(self, skill_id: str) -> SkillDefinition | None:
        """Get a skill definition by ID."""
        return self._definitions.get(skill_id)

    def list_skills(self, *, status: SkillStatus | None = None) -> list[SkillDefinition]:
        """List all skills, optionally filtered by status."""
        if status is None:
            return list(self._definitions.values())
        return [d for d in self._definitions.values() if d.status == status]
