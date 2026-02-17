"""Tests for B2-2: Intent understanding module.

Validates:
- Binary classification: chat vs skill
- Phase 2 default: all pure chat
- 10-case test set accuracy >= 90%
"""

from __future__ import annotations

import pytest

from src.brain.intent.classifier import (
    INTENT_CHAT,
    INTENT_SKILL,
    IntentClassifier,
    IntentResult,
)


@pytest.mark.unit
class TestIntentClassifier:
    """B2-2: Intent understanding module -- 10-case accuracy >= 90%."""

    @pytest.fixture()
    def classifier(self) -> IntentClassifier:
        return IntentClassifier()

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("message", "expected_intent"),
        [
            # Chat messages (should classify as chat)
            ("Hello, how are you?", INTENT_CHAT),
            ("What's the weather like?", INTENT_CHAT),
            ("Tell me about Python", INTENT_CHAT),
            ("Can you explain quantum physics?", INTENT_CHAT),
            ("Good morning!", INTENT_CHAT),
            ("I prefer dark mode", INTENT_CHAT),
            ("Thank you for your help", INTENT_CHAT),
            # Skill messages (should classify as skill)
            ("Generate content for our blog", INTENT_SKILL),
            ("Create article about summer collection", INTENT_SKILL),
            ("Write product description for shoes", INTENT_SKILL),
        ],
        ids=[
            "greeting",
            "weather",
            "explain",
            "science",
            "morning",
            "preference",
            "thanks",
            "generate",
            "create",
            "write_product",
        ],
    )
    async def test_10_case_accuracy(
        self,
        classifier: IntentClassifier,
        message: str,
        expected_intent: str,
    ) -> None:
        result = await classifier.classify(message)
        assert result == expected_intent

    @pytest.mark.asyncio()
    async def test_empty_message_is_chat(self, classifier: IntentClassifier) -> None:
        result = await classifier.classify("")
        assert result == INTENT_CHAT

    @pytest.mark.asyncio()
    async def test_detailed_result(self, classifier: IntentClassifier) -> None:
        result = await classifier.classify_detailed("Hello")
        assert isinstance(result, IntentResult)
        assert result.intent_type == INTENT_CHAT
        assert result.confidence > 0.0
        assert result.reasoning != ""

    @pytest.mark.asyncio()
    async def test_skill_result_has_matched_skill(
        self,
        classifier: IntentClassifier,
    ) -> None:
        result = await classifier.classify_detailed("Generate content for blog")
        assert result.intent_type == INTENT_SKILL
        assert result.matched_skill is not None

    @pytest.mark.asyncio()
    async def test_chat_confidence_high(self, classifier: IntentClassifier) -> None:
        result = await classifier.classify_detailed("How are you?")
        assert result.confidence >= 0.8
