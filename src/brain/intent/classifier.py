"""Intent understanding module.

Task card: B2-2
- Binary classification: pure chat vs skill execution needed
- Phase 2 default: all pure chat
- 10-case test set accuracy >= 90%

Architecture: Section 2.1 (Intent Classification)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)

# Intent types
INTENT_CHAT = "chat"
INTENT_SKILL = "skill"


@dataclass(frozen=True)
class IntentResult:
    """Result of intent classification."""

    intent_type: str  # "chat" | "skill"
    confidence: float  # 0.0 - 1.0
    matched_skill: str | None = None
    reasoning: str = ""


class IntentClassifier:
    """Binary intent classifier: chat vs skill execution.

    Phase 2 implementation uses rule-based classification.
    All messages default to pure chat unless strong skill signals detected.

    Skill signals (reserved for Phase 3):
    - Explicit commands: "generate", "create", "write"
    - Content creation patterns
    - Data query patterns
    """

    # Trigger keyword -> normalized intent_type for SkillRegistry lookup.
    # Keys are matched against lowercased user message; values are the
    # intent_type strings registered in SkillDefinition.intent_types.
    _TRIGGER_TO_INTENT: ClassVar[dict[str, str]] = {
        "generate content": "content_writing",
        "create article": "content_writing",
        "write product": "content_writing",
        "merchandising": "merchandising",
        "product description": "product_recommendation",
    }

    # Ordered trigger list for matching priority
    _SKILL_TRIGGERS: ClassVar[list[str]] = list(_TRIGGER_TO_INTENT.keys())

    async def classify(self, message: str) -> str:
        """Classify user message intent.

        Returns intent type string: "chat" or "skill".
        Phase 2: defaults to "chat" for all messages.
        """
        result = await self.classify_detailed(message)
        return result.intent_type

    async def classify_detailed(self, message: str) -> IntentResult:
        """Classify with full result details.

        Returns IntentResult with confidence and reasoning.
        """
        message_lower = message.lower().strip()

        if not message_lower:
            return IntentResult(
                intent_type=INTENT_CHAT,
                confidence=1.0,
                reasoning="Empty message defaults to chat",
            )

        # Check for skill trigger patterns
        for trigger in self._SKILL_TRIGGERS:
            if trigger in message_lower:
                normalized = self._TRIGGER_TO_INTENT[trigger]
                return IntentResult(
                    intent_type=INTENT_SKILL,
                    confidence=0.7,
                    matched_skill=normalized,
                    reasoning=f"Matched skill trigger: {trigger} -> {normalized}",
                )

        # Default: pure chat
        return IntentResult(
            intent_type=INTENT_CHAT,
            confidence=0.9,
            reasoning="No skill triggers detected, defaulting to chat",
        )
