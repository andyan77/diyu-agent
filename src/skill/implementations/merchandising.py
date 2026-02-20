"""MerchandisingSkill - Recommend outfit combinations from SKU + inventory.

Task card: S3-2
- Given SKU + inventory -> recommend outfit combinations + compatibility score
- Uses StylingRule graph data from Neo4j (K3-1)
- Receives pre-assembled KnowledgeBundle (does NOT call Resolver directly)

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


class MerchandisingSkill(SkillProtocol):
    """Recommend outfit combinations based on SKU and styling rules.

    Input params:
        sku_id (str, required): Primary SKU to find matches for.
        category (str, optional): Product category filter.
        max_combinations (int, optional): Max combos to return. Default: 5.
        min_score (float, optional): Minimum compatibility score (0-1). Default: 0.6.
    """

    @property
    def skill_id(self) -> str:
        return "merchandising"

    @property
    def name(self) -> str:
        return "Merchandising Assistant"

    @property
    def intent_types(self) -> list[str]:
        return ["merchandising", "product_recommendation", "outfit_suggestion"]

    @property
    def required_params(self) -> list[str]:
        return ["sku_id"]

    def describe(self) -> str:
        return (
            "Recommend outfit combinations based on product SKU and styling rules. "
            "Uses graph-based matching for compatibility scoring."
        )

    def validate_params(self, params: dict[str, Any]) -> ValidationResult:
        return validate_params(
            params,
            required=self.required_params,
            type_specs={"sku_id": str, "category": str, "max_combinations": int},
        )

    async def execute(
        self,
        params: dict[str, Any],
        knowledge: Any,
        context: dict[str, Any],
    ) -> SkillExecutionResult:
        """Generate outfit recommendations using styling rules from knowledge graph."""
        sku_id = params["sku_id"]
        category = params.get("category")
        max_combinations = params.get("max_combinations", 5)
        min_score = params.get("min_score", 0.6)

        # Extract styling rules from knowledge bundle
        styling_rules = self._extract_styling_rules(knowledge)
        products = self._extract_products(knowledge)

        # Generate combinations
        combinations = self._generate_combinations(
            sku_id=sku_id,
            category=category,
            max_combinations=max_combinations,
            min_score=min_score,
            styling_rules=styling_rules,
            products=products,
        )

        if not combinations:
            return SkillExecutionResult(
                skill_id=self.skill_id,
                output=SkillOutput(
                    content=f"No matching combinations found for SKU {sku_id}",
                    metadata={"sku_id": sku_id, "combinations_count": 0},
                ),
                success=True,
            )

        content = self._format_combinations(sku_id, combinations)

        return SkillExecutionResult(
            skill_id=self.skill_id,
            output=SkillOutput(
                content=content,
                artifacts=[
                    {
                        "type": "outfit_combination",
                        "sku_id": combo["sku_id"],
                        "compatibility_score": combo["score"],
                        "category": combo.get("category", ""),
                    }
                    for combo in combinations
                ],
                metadata={
                    "sku_id": sku_id,
                    "combinations_count": len(combinations),
                    "styling_rules_used": len(styling_rules),
                    "min_score": min_score,
                },
            ),
            success=True,
        )

    def _extract_styling_rules(self, knowledge: Any) -> list[dict[str, Any]]:
        """Extract StylingRule entities from KnowledgeBundle."""
        if knowledge is None:
            return []
        entities = getattr(knowledge, "entities", {})
        if not isinstance(entities, dict):
            return []
        result: list[dict[str, Any]] = entities.get("StylingRule", [])
        return result

    def _extract_products(self, knowledge: Any) -> list[dict[str, Any]]:
        """Extract product entities from KnowledgeBundle."""
        if knowledge is None:
            return []
        entities = getattr(knowledge, "entities", {})
        if not isinstance(entities, dict):
            return []
        products: list[dict[str, Any]] = []
        for key in ("Product", "SKU", "Item"):
            products.extend(entities.get(key, []))
        return products

    def _generate_combinations(
        self,
        *,
        sku_id: str,
        category: str | None,
        max_combinations: int,
        min_score: float,
        styling_rules: list[dict[str, Any]],
        products: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate scored outfit combinations.

        Uses styling rules to compute compatibility scores.
        In production, would use graph traversal; for now rule-based.
        """
        combinations: list[dict[str, Any]] = []

        for rule in styling_rules:
            source = rule.get("source_sku") or rule.get("source_id", "")
            target = rule.get("target_sku") or rule.get("target_id", "")
            score = float(rule.get("compatibility_score", rule.get("score", 0.7)))

            if str(source) == str(sku_id) and score >= min_score:
                target_category = rule.get("target_category", "")
                if category and target_category and target_category != category:
                    continue
                combinations.append(
                    {
                        "sku_id": str(target),
                        "score": score,
                        "category": target_category,
                        "rule_name": rule.get("name", ""),
                    }
                )

        # Sort by score descending
        combinations.sort(key=lambda c: c["score"], reverse=True)
        return combinations[:max_combinations]

    def _format_combinations(
        self,
        sku_id: str,
        combinations: list[dict[str, Any]],
    ) -> str:
        """Format combinations into human-readable content."""
        lines = [f"Outfit recommendations for SKU {sku_id}:"]
        for i, combo in enumerate(combinations, 1):
            score_pct = int(combo["score"] * 100)
            cat = f" ({combo['category']})" if combo.get("category") else ""
            lines.append(f"  {i}. SKU {combo['sku_id']}{cat} - {score_pct}% match")
        return "\n".join(lines)
