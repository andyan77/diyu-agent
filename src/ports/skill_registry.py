"""SkillRegistry - Skill discovery, dispatch, and lifecycle interface.

Soft dependency. When empty, Brain operates without skills.
Day-1 implementation: Empty registry, always returns None.
Real implementation: YAML registration + dynamic loading.

See: docs/architecture/03-Skill
     docs/architecture/00-*.md Section 12.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.types import KnowledgeBundle, OrganizationContext


class SkillStatus(Enum):
    """Skill lifecycle states (4-state machine).

    See: docs/architecture/03-Skill Section "Skill 生命周期状态机"

    Transitions:
        draft -> active:       passed review (capabilities + entity_types validated)
        active -> deprecated:  deprecation_date set
        deprecated -> disabled: reached deprecation_date or manual disable
        disabled -> active:    re-enabled (requires re-review)
    """

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


@dataclass(frozen=True)
class SkillDefinition:
    """Metadata describing a registered skill."""

    skill_id: str
    name: str
    description: str
    intent_types: list[str]
    version: str = "1.0.0"
    status: SkillStatus = SkillStatus.DRAFT


@dataclass(frozen=True)
class SkillResult:
    """Result of skill execution."""

    skill_id: str
    output: Any = None
    artifacts: list[dict[str, Any]] | None = None
    success: bool = True
    error: str | None = None


class SkillRegistry(ABC):
    """Port: Skill discovery, dispatch, and lifecycle management."""

    # -- Day-1 discovery/dispatch methods --

    @abstractmethod
    async def find_skill(
        self,
        intent_type: str,
        org_context: OrganizationContext,
    ) -> SkillDefinition | None:
        """Find a skill matching the intent type within org context.

        Args:
            intent_type: Intent classification string.
            org_context: Organization context for scoping.

        Returns:
            SkillDefinition if found, None otherwise.
        """

    @abstractmethod
    async def can_handle(
        self,
        intent_type: str,
        skill_id: str,
    ) -> float:
        """Return confidence (0.0-1.0) that skill can handle intent.

        Args:
            intent_type: Intent classification string.
            skill_id: Skill identifier.

        Returns:
            Confidence score between 0.0 and 1.0.
        """

    @abstractmethod
    async def execute(
        self,
        skill_id: str,
        knowledge: KnowledgeBundle,
        context: dict[str, Any],
    ) -> SkillResult:
        """Execute a skill with knowledge and context.

        Args:
            skill_id: Skill to execute.
            knowledge: Resolved knowledge bundle.
            context: Execution context.

        Returns:
            SkillResult with output and artifacts.
        """

    # -- Phase 3 lifecycle methods (S3-3 五态转换) --

    @abstractmethod
    async def register(
        self,
        definition: SkillDefinition,
    ) -> SkillDefinition:
        """Register a new skill in the registry.

        The skill starts in DRAFT status. Capabilities and entity_types
        must be validated before transitioning to ACTIVE.

        Args:
            definition: Skill metadata to register.

        Returns:
            Registered SkillDefinition (may include server-assigned fields).
        """

    @abstractmethod
    async def deregister(self, skill_id: str) -> None:
        """Remove a skill from the registry.

        After deregistration:
        - Knowledge Stores entity types marked registered_by="skill:<id>(removed)"
        - Existing data retained (not deleted)
        - Brain Router no longer matches this skill

        Args:
            skill_id: Skill identifier to remove.
        """

    @abstractmethod
    async def update_status(
        self,
        skill_id: str,
        new_status: SkillStatus,
    ) -> SkillDefinition:
        """Update the lifecycle status of a skill.

        Enforces valid state transitions per the 4-state machine.

        Args:
            skill_id: Skill identifier.
            new_status: Target status.

        Returns:
            Updated SkillDefinition.

        Raises:
            ValueError: If the transition is not allowed.
        """
