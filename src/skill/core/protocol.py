"""SkillProtocol - Unified contract for all Skill implementations.

Task card: S0-1
- execute(): Run skill with knowledge bundle and context
- describe(): Return human-readable description
- validate_params(): Validate input parameters before execution

Architecture: docs/architecture/03-Skill Section 2
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.types import KnowledgeBundle


@dataclass(frozen=True)
class SkillOutput:
    """Standard output from skill execution."""

    content: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillExecutionResult:
    """Full result of skill execution including status."""

    skill_id: str
    output: SkillOutput | None = None
    success: bool = True
    error: str | None = None


@dataclass(frozen=True)
class ValidationError:
    """A single parameter validation error."""

    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    """Result of parameter validation."""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)


class SkillProtocol(ABC):
    """Base protocol for all Skill implementations.

    Skills receive pre-assembled KnowledgeBundle from Brain orchestrator.
    Skills MUST NOT directly call Resolver or access Knowledge stores.

    Lifecycle: draft -> active -> deprecated -> disabled (+ disabled -> active)
    """

    @property
    @abstractmethod
    def skill_id(self) -> str:
        """Unique identifier for this skill."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable skill name."""

    @property
    @abstractmethod
    def intent_types(self) -> list[str]:
        """Intent types this skill handles."""

    @abstractmethod
    async def execute(
        self,
        params: dict[str, Any],
        knowledge: KnowledgeBundle,
        context: dict[str, Any],
    ) -> SkillExecutionResult:
        """Execute the skill with validated parameters and pre-fetched knowledge.

        Args:
            params: Validated input parameters.
            knowledge: Pre-assembled KnowledgeBundle from Brain orchestrator.
            context: Execution context (org_id, user_id, etc.).

        Returns:
            SkillExecutionResult with output or error.
        """

    @abstractmethod
    def describe(self) -> str:
        """Return human-readable description of this skill's capabilities."""

    @abstractmethod
    def validate_params(self, params: dict[str, Any]) -> ValidationResult:
        """Validate input parameters before execution.

        Args:
            params: Raw input parameters to validate.

        Returns:
            ValidationResult with valid flag and error details.
        """

    @property
    def version(self) -> str:
        """Skill version. Override in subclass if needed."""
        return "1.0.0"

    @property
    def required_params(self) -> list[str]:
        """List of required parameter names. Override in subclass."""
        return []
