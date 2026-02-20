"""Skill Router -- route intent to matching Skill.

Task card: B3-1
- Map intent classification result to the correct Skill
- Accuracy >= 95% on test set
- No match -> fall back to pure chat

Architecture: docs/architecture/01-Brain Section 1.5 (Skill Dispatch)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ports.skill_registry import SkillDefinition, SkillRegistry
    from src.shared.types import OrganizationContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouteResult:
    """Result of skill routing."""

    routed: bool
    skill: SkillDefinition | None = None
    confidence: float = 0.0
    reason: str = ""


class SkillRouter:
    """Route intent classifications to registered skills.

    Resolution:
    1. If intent_type == "chat" -> no routing (pure chat)
    2. Look up SkillRegistry for matching active skill
    3. If found with confidence >= threshold -> route to skill
    4. Otherwise -> fall back to chat

    Brain owns the routing decision; SkillRegistry provides lookup.
    """

    def __init__(
        self,
        *,
        registry: SkillRegistry,
        confidence_threshold: float = 0.5,
    ) -> None:
        self._registry = registry
        self._confidence_threshold = confidence_threshold

    async def route(
        self,
        intent_type: str,
        org_context: OrganizationContext,
        *,
        matched_skill_hint: str | None = None,
    ) -> RouteResult:
        """Route an intent to a matching skill.

        Args:
            intent_type: Classified intent type (e.g. "skill", "chat").
            org_context: Organization context for scoping.
            matched_skill_hint: Optional skill hint from intent classifier.

        Returns:
            RouteResult with routing decision.
        """
        # Pure chat intents are never routed
        if intent_type == "chat":
            return RouteResult(
                routed=False,
                reason="Intent is pure chat, no skill routing",
            )

        # Try to find a matching skill via hint
        if matched_skill_hint:
            skill = await self._registry.find_skill(matched_skill_hint, org_context)
            if skill is not None:
                confidence = await self._registry.can_handle(matched_skill_hint, skill.skill_id)
                if confidence >= self._confidence_threshold:
                    logger.info(
                        "Routed intent '%s' to skill '%s' (confidence=%.2f)",
                        matched_skill_hint,
                        skill.skill_id,
                        confidence,
                    )
                    return RouteResult(
                        routed=True,
                        skill=skill,
                        confidence=confidence,
                        reason=f"Matched via hint: {matched_skill_hint}",
                    )

        # Try to find skill by generic "skill" intent
        skill = await self._registry.find_skill(intent_type, org_context)
        if skill is not None:
            confidence = await self._registry.can_handle(intent_type, skill.skill_id)
            if confidence >= self._confidence_threshold:
                logger.info(
                    "Routed intent '%s' to skill '%s' (confidence=%.2f)",
                    intent_type,
                    skill.skill_id,
                    confidence,
                )
                return RouteResult(
                    routed=True,
                    skill=skill,
                    confidence=confidence,
                    reason=f"Matched intent: {intent_type}",
                )

        # No match -> fallback to chat
        logger.debug("No skill found for intent '%s', falling back to chat", intent_type)
        return RouteResult(
            routed=False,
            reason=f"No active skill for intent: {intent_type}",
        )
