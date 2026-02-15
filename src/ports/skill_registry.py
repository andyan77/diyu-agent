"""SkillRegistry - Skill discovery and dispatch interface.

Soft dependency. When empty, Brain operates without skills.
Day-1 implementation: Empty registry, always returns None.
Real implementation: YAML registration + dynamic loading.

See: docs/architecture/03-Skill
     docs/architecture/00-*.md Section 12.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.types import KnowledgeBundle, OrganizationContext


@dataclass(frozen=True)
class SkillDefinition:
    """Metadata describing a registered skill."""

    skill_id: str
    name: str
    description: str
    intent_types: list[str]
    version: str = "1.0.0"


@dataclass(frozen=True)
class SkillResult:
    """Result of skill execution."""

    skill_id: str
    output: Any = None
    artifacts: list[dict[str, Any]] | None = None
    success: bool = True
    error: str | None = None


class SkillRegistry(ABC):
    """Port: Skill discovery and dispatch."""

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
