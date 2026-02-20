"""Skill orchestrator -- end-to-end skill execution flow.

Task card: B3-2
- Full flow: conversation triggers Skill -> Resolver pre-fetches KnowledgeBundle
  -> Skill.execute() -> result returned to user
- Pure chat path unaffected
- Success rate >= 90%

Architecture: docs/architecture/01-Brain Section 1.5
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.brain.skill.router import RouteResult, SkillRouter
    from src.ports.knowledge_port import KnowledgePort
    from src.ports.skill_registry import SkillRegistry, SkillResult
    from src.shared.types import KnowledgeBundle, OrganizationContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrchestrationResult:
    """Result of the skill orchestration pipeline."""

    executed: bool
    skill_id: str | None = None
    skill_result: SkillResult | None = None
    knowledge_used: bool = False
    route_result: RouteResult | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillOrchestrator:
    """Orchestrate the full skill execution pipeline.

    Pipeline:
    1. SkillRouter decides if intent maps to a skill
    2. If routed: resolve knowledge via KnowledgePort
    3. Execute skill via SkillRegistry
    4. Return structured result

    Brain owns this orchestration; Skill layer only handles execution.
    """

    def __init__(
        self,
        *,
        router: SkillRouter,
        registry: SkillRegistry,
        knowledge: KnowledgePort | None = None,
        default_profile: str = "core:brand_context",
    ) -> None:
        self._router = router
        self._registry = registry
        self._knowledge = knowledge
        self._default_profile = default_profile

    async def orchestrate(
        self,
        *,
        intent_type: str,
        org_context: OrganizationContext,
        user_message: str,
        params: dict[str, Any] | None = None,
        matched_skill_hint: str | None = None,
    ) -> OrchestrationResult:
        """Run the full skill orchestration pipeline.

        Args:
            intent_type: Classified intent type.
            org_context: Organization context.
            user_message: Original user message (for knowledge resolution).
            params: Skill execution parameters.
            matched_skill_hint: Optional hint from intent classifier.

        Returns:
            OrchestrationResult with execution outcome.
        """
        # Step 1: Route
        route = await self._router.route(
            intent_type,
            org_context,
            matched_skill_hint=matched_skill_hint,
        )

        if not route.routed or route.skill is None:
            return OrchestrationResult(
                executed=False,
                route_result=route,
                metadata={"reason": route.reason},
            )

        skill_id = route.skill.skill_id

        # Step 2: Resolve knowledge (soft dependency, degradable)
        knowledge_bundle = await self._resolve_knowledge(user_message, org_context)

        # Step 3: Execute skill
        context: dict[str, Any] = {
            "params": params or {},
            "user_message": user_message,
            "org_id": str(org_context.org_id),
            "user_id": str(org_context.user_id),
        }

        try:
            skill_result = await self._registry.execute(skill_id, knowledge_bundle, context)
        except Exception as exc:
            logger.exception("Skill execution error: %s", skill_id)
            return OrchestrationResult(
                executed=True,
                skill_id=skill_id,
                route_result=route,
                knowledge_used=knowledge_bundle is not None,
                error=str(exc),
            )

        return OrchestrationResult(
            executed=True,
            skill_id=skill_id,
            skill_result=skill_result,
            knowledge_used=knowledge_bundle is not None,
            route_result=route,
            metadata={
                "confidence": route.confidence,
                "route_reason": route.reason,
            },
        )

    async def _resolve_knowledge(
        self,
        query: str,
        org_context: OrganizationContext,
    ) -> Any:
        """Resolve knowledge bundle (soft dependency).

        Returns None if knowledge port unavailable.
        """
        if self._knowledge is None:
            logger.debug("Knowledge port unavailable, proceeding without knowledge")
            return None

        try:
            bundle: KnowledgeBundle = await self._knowledge.resolve(
                self._default_profile,
                query,
                org_context,
            )
            return bundle
        except Exception:
            logger.warning("Knowledge resolution failed, proceeding without", exc_info=True)
            return None
