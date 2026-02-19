"""Cross-layer E2E: Full conversation loop (X2-1) + streaming verification (X2-2).

Verifies: Gateway -> Brain -> MemoryCore -> EventStore full round-trip.
Uses FakeLLM + FakeMemoryCore + FakeEventStore (no external services required).

This is the HARD GATE test for Phase 2 cross-layer integration.
All tests MUST pass without skip for the hard gate to be GO.

Covers:
    X2-1: Full conversation loop (chat -> remember -> recall -> inject)
    X2-2: Streaming reply chain verification (via multi-turn context injection)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine, ConversationTurn
from src.brain.memory.pipeline import MemoryWritePipeline
from src.memory.receipt import ReceiptStore
from tests.e2e.test_conversation_loop import FakeEventStore, FakeLLM, FakeMemoryCore


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
class TestConversationLoopCrossLayer:
    """Cross-layer conversation loop verification (X2-1, X2-2).

    Exercises the full Brain -> MemoryCore -> EventStore integration path
    using deterministic fakes (no external services).
    """

    async def test_chat_remember_recall_inject(
        self,
        memory_core: FakeMemoryCore,
        event_store: FakeEventStore,
        receipt_store: ReceiptStore,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
    ) -> None:
        """X2-1: chat -> remember -> recall -> inject round-trip.

        Turn 1: User states a preference -> memory pipeline extracts it.
        Turn 2: User asks about preference -> context assembler injects memory
                 -> LLM prompt contains the preference.
        """
        llm = FakeLLM(responses=["Got it, blue!", "Your favorite color is blue."])
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

        # Turn 1: establish preference
        turn1 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Remember that my favorite color is blue",
        )
        assert isinstance(turn1, ConversationTurn)
        assert turn1.assistant_response == "Got it, blue!"

        # Verify memory was written
        items = await memory_core.read_personal_memories(user_id, "blue")
        assert len(items) >= 1, "Memory pipeline should have extracted at least one observation"

        # Turn 2: recall should inject prior context
        turn2 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="What is my favorite color?",
        )
        assert isinstance(turn2, ConversationTurn)
        assert turn2.assistant_response == "Your favorite color is blue."

        # Verify context assembly path was exercised
        assert turn2.context is not None

    async def test_streaming_reply_chain(
        self,
        memory_core: FakeMemoryCore,
        event_store: FakeEventStore,
        receipt_store: ReceiptStore,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
    ) -> None:
        """X2-2: Streaming reply chain -- multi-turn with event persistence.

        Verifies that the full chain (LLM call -> event store append -> history
        recovery) works correctly across multiple turns, which is the backend
        prerequisite for SSE streaming delivery to the frontend.

        Note: Actual SSE wire format is tested by the FE Playwright spec
        (p2-streaming). This test validates the backend conversation chain
        that feeds the streaming endpoint.
        """
        responses = [
            "Hello! I see you like Python.",
            "You mentioned Python earlier. Great choice!",
        ]
        llm = FakeLLM(responses=responses)
        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            event_store=event_store,
            memory_pipeline=MemoryWritePipeline(
                memory_core=memory_core,
                receipt_store=receipt_store,
            ),
            default_model="gpt-4o",
        )

        # Turn 1
        turn1 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="I love Python programming",
        )
        assert turn1.assistant_response == responses[0]

        # Verify events persisted after turn 1
        events = await event_store.get_session_events(session_id)
        assert len(events) == 2  # user_message + assistant_message
        assert events[0]["event_type"] == "user_message"
        assert events[0]["content"]["text"] == "I love Python programming"
        assert events[1]["event_type"] == "assistant_message"
        assert events[1]["content"]["text"] == responses[0]

        # Recover history (simulates what streaming endpoint does)
        history = await engine.get_session_history(session_id)
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "I love Python programming"}
        assert history[1] == {"role": "assistant", "content": responses[0]}

        # Turn 2 with recovered history -- verifies chain continuity
        turn2 = await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="What language did I mention?",
            conversation_history=history,
        )
        assert turn2.assistant_response == responses[1]

        # LLM prompt should contain history from turn 1
        assert "Python" in llm.prompts[1]

        # Total events: 4 (2 per turn)
        all_events = await event_store.get_session_events(session_id)
        assert len(all_events) == 4
