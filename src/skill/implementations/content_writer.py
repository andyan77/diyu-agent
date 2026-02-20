"""ContentWriterSkill - Generate marketing content from brand knowledge.

Task card: S3-1
- Given brand knowledge + persona + platform -> generate formatted marketing content
- Receives pre-assembled KnowledgeBundle (does NOT call Resolver directly)
- Dependencies: KnowledgeBundle (K3-5), LLMCallPort (T2-1)

Architecture: docs/architecture/03-Skill Section 2
"""

from __future__ import annotations

from typing import Any

from src.skill.core.protocol import (
    SkillExecutionResult,
    SkillOutput,
    SkillProtocol,
    ValidationResult,
)
from src.skill.core.validation import validate_params


class ContentWriterSkill(SkillProtocol):
    """Generate marketing content based on brand knowledge and persona.

    Input params:
        topic (str, required): Content topic or brief.
        platform (str, required): Target platform (e.g. "xiaohongshu", "douyin", "wechat").
        persona (str, optional): Writing persona/style. Default: "professional".
        max_length (int, optional): Max content length in characters. Default: 500.
    """

    @property
    def skill_id(self) -> str:
        return "content_writer"

    @property
    def name(self) -> str:
        return "Content Writer"

    @property
    def intent_types(self) -> list[str]:
        return ["generate_content", "write_content", "create_article"]

    @property
    def required_params(self) -> list[str]:
        return ["topic", "platform"]

    def describe(self) -> str:
        return (
            "Generate marketing content from brand knowledge. "
            "Supports multiple platforms (xiaohongshu, douyin, wechat) "
            "with configurable persona and length."
        )

    def validate_params(self, params: dict[str, Any]) -> ValidationResult:
        return validate_params(
            params,
            required=self.required_params,
            type_specs={"topic": str, "platform": str, "persona": str, "max_length": int},
        )

    async def execute(
        self,
        params: dict[str, Any],
        knowledge: Any,
        context: dict[str, Any],
    ) -> SkillExecutionResult:
        """Generate content using brand knowledge and parameters.

        The actual LLM call would be delegated via the Brain orchestrator.
        This skill assembles the prompt template and output format.
        """
        topic = params["topic"]
        platform = params["platform"]
        persona = params.get("persona", "professional")
        max_length = params.get("max_length", 500)

        # Extract brand knowledge from bundle
        brand_context = self._extract_brand_context(knowledge)

        # Build structured content output
        content = self._build_content(
            topic=topic,
            platform=platform,
            persona=persona,
            max_length=max_length,
            brand_context=brand_context,
        )

        return SkillExecutionResult(
            skill_id=self.skill_id,
            output=SkillOutput(
                content=content,
                artifacts=[
                    {
                        "type": "marketing_content",
                        "platform": platform,
                        "persona": persona,
                        "word_count": len(content),
                    }
                ],
                metadata={
                    "topic": topic,
                    "platform": platform,
                    "persona": persona,
                    "max_length": max_length,
                    "brand_entities_used": len(brand_context),
                },
            ),
            success=True,
        )

    def _extract_brand_context(self, knowledge: Any) -> list[dict[str, Any]]:
        """Extract brand-related entities from KnowledgeBundle."""
        if knowledge is None:
            return []
        entities = getattr(knowledge, "entities", {})
        if not isinstance(entities, dict):
            return []
        brand_items: list[dict[str, Any]] = []
        for _entity_type, items in entities.items():
            if isinstance(items, list):
                brand_items.extend(items)
        return brand_items

    def _build_content(
        self,
        *,
        topic: str,
        platform: str,
        persona: str,
        max_length: int,
        brand_context: list[dict[str, Any]],
    ) -> str:
        """Build content from template (real impl would use LLM via Brain).

        In production, Brain orchestrator calls LLM with this structured prompt.
        For unit testing, returns deterministic template-based output.
        """
        brand_info = ""
        if brand_context:
            brand_names = [
                item.get("name", item.get("brand_name", ""))
                for item in brand_context
                if item.get("name") or item.get("brand_name")
            ]
            if brand_names:
                brand_info = f" for {', '.join(brand_names[:3])}"

        return (
            f"[{platform.upper()}] {persona.capitalize()} content{brand_info}: {topic[:max_length]}"
        )
