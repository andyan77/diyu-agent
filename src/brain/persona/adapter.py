"""Role adaptation module -- adjust reply style based on organization context.

Task card: B3-3
- Adjust response style based on OrgContext role (brand HQ vs store staff)
- Data-driven from Knowledge Stores or defaults
- No config -> default style (graceful degradation)

Architecture: docs/architecture/01-Brain Section 1.4 (Role Adaptation)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared.types import KnowledgeBundle, OrganizationContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PersonaConfig:
    """Configuration for a role-based persona."""

    role_key: str
    tone: str  # formal | casual | professional | friendly
    formality_level: int  # 1-5 (1=very casual, 5=very formal)
    language_style: str  # concise | detailed | storytelling
    greeting_template: str = ""
    sign_off_template: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# Default persona configurations per org tier
DEFAULT_PERSONAS: dict[str, PersonaConfig] = {
    "platform": PersonaConfig(
        role_key="platform",
        tone="professional",
        formality_level=4,
        language_style="detailed",
        greeting_template="Hello,",
        sign_off_template="Best regards,",
    ),
    "brand_hq": PersonaConfig(
        role_key="brand_hq",
        tone="professional",
        formality_level=4,
        language_style="detailed",
        greeting_template="Hello,",
        sign_off_template="Best regards,",
    ),
    "brand_dept": PersonaConfig(
        role_key="brand_dept",
        tone="professional",
        formality_level=3,
        language_style="concise",
    ),
    "regional_agent": PersonaConfig(
        role_key="regional_agent",
        tone="friendly",
        formality_level=2,
        language_style="concise",
    ),
    "franchise_store": PersonaConfig(
        role_key="franchise_store",
        tone="casual",
        formality_level=1,
        language_style="storytelling",
        greeting_template="Hi there!",
    ),
}

# Fallback for unknown roles
_DEFAULT_PERSONA = PersonaConfig(
    role_key="default",
    tone="professional",
    formality_level=3,
    language_style="concise",
)


class RoleAdapter:
    """Adapt Brain responses based on organization role context.

    Resolution order:
    1. Knowledge Stores (dynamic persona config from graph)
    2. Default persona map (static config)
    3. Fallback default
    """

    def __init__(
        self,
        *,
        custom_personas: dict[str, PersonaConfig] | None = None,
    ) -> None:
        self._custom_personas = custom_personas or {}

    def resolve_persona(
        self,
        org_context: OrganizationContext | None,
        knowledge: KnowledgeBundle | None = None,
    ) -> PersonaConfig:
        """Resolve the persona config for the given organization context.

        Args:
            org_context: Organization context with role/tier info.
            knowledge: Optional knowledge bundle with dynamic persona data.

        Returns:
            PersonaConfig for the resolved role.
        """
        if org_context is None:
            return _DEFAULT_PERSONA

        tier = org_context.org_tier

        # 1. Try knowledge-driven persona
        if knowledge is not None:
            kb_persona = self._extract_persona_from_knowledge(knowledge, tier)
            if kb_persona is not None:
                return kb_persona

        # 2. Try custom personas
        if tier in self._custom_personas:
            return self._custom_personas[tier]

        # 3. Try default personas
        if tier in DEFAULT_PERSONAS:
            return DEFAULT_PERSONAS[tier]

        # 4. Fallback
        logger.debug("No persona config for tier '%s', using default", tier)
        return _DEFAULT_PERSONA

    def adapt_system_prompt(
        self,
        base_prompt: str,
        persona: PersonaConfig,
    ) -> str:
        """Inject persona instructions into the system prompt.

        Args:
            base_prompt: Original system prompt.
            persona: Resolved persona configuration.

        Returns:
            Enhanced system prompt with role adaptation instructions.
        """
        persona_instruction = (
            f"\n\n[Role Adaptation]\n"
            f"Tone: {persona.tone}\n"
            f"Formality: {persona.formality_level}/5\n"
            f"Style: {persona.language_style}"
        )

        if persona.greeting_template:
            persona_instruction += f"\nGreeting: {persona.greeting_template}"

        return base_prompt + persona_instruction

    def _extract_persona_from_knowledge(
        self,
        knowledge: KnowledgeBundle,
        tier: str,
    ) -> PersonaConfig | None:
        """Try to extract persona config from Knowledge bundle.

        Looks for RoleAdaptationRule entities matching the tier.
        """
        entities = getattr(knowledge, "entities", {})
        if not isinstance(entities, dict):
            return None

        rules = entities.get("RoleAdaptationRule", [])
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            rule_tier = rule.get("org_tier") or rule.get("role_key", "")
            if rule_tier == tier:
                return PersonaConfig(
                    role_key=tier,
                    tone=rule.get("tone", "professional"),
                    formality_level=int(rule.get("formality_level", 3)),
                    language_style=rule.get("language_style", "concise"),
                    greeting_template=rule.get("greeting_template", ""),
                    sign_off_template=rule.get("sign_off_template", ""),
                )

        return None
