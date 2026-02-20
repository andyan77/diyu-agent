"""B3-3: Role adaptation tests.

Tests: two roles produce distinguishable output, knowledge-driven override,
default fallback, system prompt adaptation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.brain.persona.adapter import DEFAULT_PERSONAS, PersonaConfig, RoleAdapter
from src.shared.types import OrganizationContext


@dataclass(frozen=True)
class FakeKnowledgeBundle:
    entities: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


def _make_org(tier: str) -> OrganizationContext:
    return OrganizationContext(
        user_id=UUID(int=1),
        org_id=UUID(int=2),
        org_tier=tier,
        org_path="root.brand",
    )


class TestRoleResolution:
    def test_brand_hq_persona(self) -> None:
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("brand_hq"))
        assert persona.tone == "professional"
        assert persona.formality_level >= 3

    def test_franchise_store_persona(self) -> None:
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("franchise_store"))
        assert persona.tone == "casual"
        assert persona.formality_level <= 2

    def test_two_roles_are_distinguishable(self) -> None:
        """Task card requirement: two roles must produce distinguishable output."""
        adapter = RoleAdapter()
        hq = adapter.resolve_persona(_make_org("brand_hq"))
        store = adapter.resolve_persona(_make_org("franchise_store"))
        assert hq.tone != store.tone
        assert hq.formality_level != store.formality_level

    def test_unknown_tier_uses_default(self) -> None:
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("unknown_tier"))
        assert persona.role_key == "default"

    def test_none_org_context_uses_default(self) -> None:
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(None)
        assert persona.role_key == "default"


class TestCustomPersonas:
    def test_custom_persona_override(self) -> None:
        custom = PersonaConfig(
            role_key="brand_hq",
            tone="enthusiastic",
            formality_level=2,
            language_style="storytelling",
        )
        adapter = RoleAdapter(custom_personas={"brand_hq": custom})
        persona = adapter.resolve_persona(_make_org("brand_hq"))
        assert persona.tone == "enthusiastic"
        assert persona.formality_level == 2


class TestKnowledgeDrivenPersona:
    def test_knowledge_override_takes_priority(self) -> None:
        knowledge = FakeKnowledgeBundle(
            entities={
                "RoleAdaptationRule": [
                    {
                        "org_tier": "brand_hq",
                        "tone": "warm",
                        "formality_level": 2,
                        "language_style": "storytelling",
                        "greeting_template": "Welcome!",
                    },
                ]
            }
        )
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("brand_hq"), knowledge=knowledge)
        assert persona.tone == "warm"
        assert persona.formality_level == 2

    def test_knowledge_miss_falls_back_to_defaults(self) -> None:
        knowledge = FakeKnowledgeBundle(
            entities={
                "RoleAdaptationRule": [
                    {"org_tier": "other_tier", "tone": "x"},
                ]
            }
        )
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("brand_hq"), knowledge=knowledge)
        assert persona.tone == DEFAULT_PERSONAS["brand_hq"].tone

    def test_empty_knowledge_falls_back(self) -> None:
        knowledge = FakeKnowledgeBundle()
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("brand_hq"), knowledge=knowledge)
        assert persona.tone == DEFAULT_PERSONAS["brand_hq"].tone


class TestSystemPromptAdaptation:
    def test_prompt_includes_tone(self) -> None:
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("franchise_store"))
        result = adapter.adapt_system_prompt("You are an assistant.", persona)
        assert "casual" in result
        assert "Role Adaptation" in result

    def test_prompt_includes_greeting(self) -> None:
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("franchise_store"))
        result = adapter.adapt_system_prompt("Base prompt.", persona)
        assert "Hi there!" in result

    def test_prompt_preserves_base(self) -> None:
        adapter = RoleAdapter()
        persona = adapter.resolve_persona(_make_org("brand_hq"))
        result = adapter.adapt_system_prompt("Original prompt text.", persona)
        assert result.startswith("Original prompt text.")
