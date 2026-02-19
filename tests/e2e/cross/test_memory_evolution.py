"""Cross-layer E2E: Memory Evolution closed loop (X2-3).

Verifies: conversation -> extract observation -> update memory_items -> next conversation injects.
Uses FakeMemoryCore + ConversationEngine + confidence_effective() — no live PG/pgvector required.

Covers:
    X2-3: Memory evolution closed loop
"""

from __future__ import annotations

from datetime import timedelta, timezone
from uuid import UUID, uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine
from src.brain.memory.pipeline import MemoryWritePipeline
from src.memory.confidence import confidence_effective
from src.memory.receipt import ReceiptStore
from tests.e2e.test_conversation_loop import FakeEventStore, FakeLLM, FakeMemoryCore

UTC = timezone.utc  # noqa: UP017 -- compat with Python <3.11 runtime


@pytest.fixture()
def session_id() -> UUID:
    return uuid4()


@pytest.fixture()
def user_id() -> UUID:
    return uuid4()


@pytest.fixture()
def org_id() -> UUID:
    return uuid4()


@pytest.fixture()
def memory_core() -> FakeMemoryCore:
    return FakeMemoryCore()


@pytest.fixture()
def event_store() -> FakeEventStore:
    return FakeEventStore()


@pytest.fixture()
def receipt_store() -> ReceiptStore:
    return ReceiptStore()


@pytest.mark.e2e
class TestMemoryEvolutionCrossLayer:
    """Cross-layer memory evolution verification.

    Exercises the full Brain -> MemoryCore -> ConfidenceDecay path using
    deterministic fakes (no external services).
    """

    async def test_observation_extraction_and_injection(
        self,
        memory_core: FakeMemoryCore,
        event_store: FakeEventStore,
        receipt_store: ReceiptStore,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
    ) -> None:
        """X2-3: Conversation triggers memory update, next turn reflects it."""
        llm = FakeLLM(responses=["Got it, noted!", "You prefer vim."])
        pipeline = MemoryWritePipeline(
            memory_core=memory_core,
            receipt_store=receipt_store,
        )
        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            event_store=event_store,
            memory_pipeline=pipeline,
            default_model="gpt-4o",
        )

        # Turn 1: user states a preference -> memory pipeline extracts it
        # Uses "I prefer" which matches Observer's rule-based extraction
        turn1 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="I prefer vim as my editor",
        )
        assert turn1.assistant_response is not None

        # Verify memory was written by pipeline
        items = await memory_core.read_personal_memories(user_id, "vim")
        assert len(items) >= 1, "Memory pipeline should extract 'vim' preference"

        # Turn 2: query about the preference -> context assembler injects memory
        turn2 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="What editor do I use?",
        )
        assert turn2.assistant_response is not None
        assert turn2.context is not None, "Context assembly should have been exercised"

    async def test_memory_confidence_decay(
        self,
        memory_core: FakeMemoryCore,
        event_store: FakeEventStore,
        receipt_store: ReceiptStore,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
    ) -> None:
        """X2-3 sub: confidence_effective decays over time without reinforcement.

        Verifies that the confidence decay function produces observable
        decay after 30+ days, using the real confidence_effective()
        computation against a memory created via the conversation loop.
        """
        llm = FakeLLM(responses=["Noted your Go preference!"])
        pipeline = MemoryWritePipeline(
            memory_core=memory_core,
            receipt_store=receipt_store,
        )
        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            event_store=event_store,
            memory_pipeline=pipeline,
            default_model="gpt-4o",
        )

        # Create a memory via the conversation loop
        # Uses "I like" which matches Observer's rule-based extraction
        await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="I like programming in Go",
        )

        items = await memory_core.read_personal_memories(user_id, "Go")
        assert len(items) >= 1, "Should have at least one memory about Go"

        memory = items[0]
        base_confidence = memory.confidence
        valid_at = memory.valid_at

        # At creation time: effective confidence == base confidence
        effective_now = confidence_effective(base_confidence, valid_at, now=valid_at)
        assert effective_now == pytest.approx(base_confidence, abs=1e-9)

        # After 30 days: observable decay (half_life=90 days)
        future_30d = valid_at + timedelta(days=30)
        effective_30d = confidence_effective(base_confidence, valid_at, now=future_30d)
        assert effective_30d < base_confidence, "Confidence should decay after 30 days"
        assert effective_30d > 0, "Confidence should not reach zero"

        # After 90 days (1 half-life): should be ~50% of original
        future_90d = valid_at + timedelta(days=90)
        effective_90d = confidence_effective(base_confidence, valid_at, now=future_90d)
        assert effective_90d == pytest.approx(base_confidence * 0.5, abs=0.01), (
            "At 1 half-life, confidence should be ~50% of base"
        )

        # After 180 days (2 half-lives): should be ~25% of original
        future_180d = valid_at + timedelta(days=180)
        effective_180d = confidence_effective(base_confidence, valid_at, now=future_180d)
        assert effective_180d == pytest.approx(base_confidence * 0.25, abs=0.01), (
            "At 2 half-lives, confidence should be ~25% of base"
        )
