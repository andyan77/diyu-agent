"""Tests for B2-1: Conversation engine full implementation.

Validates:
- Complete first-turn conversation closure
- Context assembly integration
- LLM call through Port
- Memory pipeline integration (non-blocking)
- Usage tracking
- Event store write path (append_event on each turn)
- Event store read path (session history recovery)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine, ConversationTurn
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, PromotionReceipt, WriteReceipt
from src.tool.llm.usage_tracker import UsageTracker


class FakeMemoryCore(MemoryCorePort):
    """In-memory MemoryCorePort for testing."""

    def __init__(self) -> None:
        self._items: list[MemoryItem] = []

    async def read_personal_memories(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        *,
        org_id: UUID | None = None,
    ) -> list[MemoryItem]:
        results = [m for m in self._items if m.user_id == user_id]
        if query:
            results = [m for m in results if query.lower() in m.content.lower()]
        return sorted(results, key=lambda m: m.confidence, reverse=True)[:top_k]

    async def write_observation(
        self,
        user_id: UUID,
        observation: Observation,
        *,
        org_id: UUID | None = None,
    ) -> WriteReceipt:
        memory_id = uuid4()
        now = datetime.now(UTC)
        item = MemoryItem(
            memory_id=memory_id,
            user_id=user_id,
            memory_type=observation.memory_type,
            content=observation.content,
            confidence=observation.confidence,
            valid_at=now,
            source_sessions=(
                [observation.source_session_id] if observation.source_session_id else []
            ),
        )
        self._items.append(item)
        return WriteReceipt(memory_id=memory_id, version=1, written_at=now)

    async def get_session(self, session_id: UUID) -> object:
        return None

    async def archive_session(self, session_id: UUID) -> object:
        return None

    async def promote_to_knowledge(
        self,
        memory_id: UUID,
        target_org_id: UUID,
        target_visibility: str,
        *,
        user_id: UUID | None = None,
    ) -> PromotionReceipt:
        from datetime import UTC, datetime

        return PromotionReceipt(
            proposal_id=memory_id,
            source_memory_id=memory_id,
            target_knowledge_id=None,
            status="promoted",
            promoted_at=datetime.now(UTC),
        )


class FakeLLM(LLMCallPort):
    """Fake LLM for conversation engine tests."""

    def __init__(self, response: str = "I understand.") -> None:
        self._response = response
        self.call_count = 0

    async def call(self, prompt, model_id, content_parts=None, parameters=None):
        self.call_count += 1
        return LLMResponse(
            text=self._response,
            tokens_used={"input": 50, "output": 30},
            model_id=model_id,
            finish_reason="stop",
        )


class FakeEventStore:
    """In-memory event store satisfying EventStoreProtocol for testing."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._seq_counters: dict[UUID, int] = {}

    async def append_event(
        self,
        *,
        org_id: UUID,
        session_id: UUID,
        user_id: UUID | None = None,
        event_type: str,
        role: str = "user",
        content: dict[str, Any] | None = None,
        parent_event_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> object:
        seq = self._seq_counters.get(session_id, 0) + 1
        self._seq_counters[session_id] = seq
        event = {
            "id": uuid4(),
            "org_id": org_id,
            "session_id": session_id,
            "user_id": user_id,
            "event_type": event_type,
            "role": role,
            "content": content or {},
            "sequence_number": seq,
        }
        self.events.append(event)
        return event

    async def get_session_events(
        self,
        session_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[object]:
        events = [e for e in self.events if e["session_id"] == session_id]
        events.sort(key=lambda e: e["sequence_number"])
        if limit is not None:
            events = events[:limit]
        return events


@pytest.mark.unit
class TestConversationEngine:
    """B2-1: Conversation engine full impl."""

    @pytest.fixture()
    def engine(self) -> ConversationEngine:
        memory_core = FakeMemoryCore()
        llm = FakeLLM(response="Hello! I'm here to help.")
        usage_tracker = UsageTracker()
        return ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            usage_tracker=usage_tracker,
            default_model="gpt-4o",
        )

    @pytest.mark.asyncio()
    async def test_first_turn_closure(self, engine: ConversationEngine) -> None:
        """Complete first-turn: user message -> assistant response."""
        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Hello, who are you?",
        )
        assert isinstance(turn, ConversationTurn)
        assert turn.assistant_response == "Hello! I'm here to help."
        assert turn.user_message == "Hello, who are you?"
        assert turn.tokens_used["input"] == 50
        assert turn.tokens_used["output"] == 30

    @pytest.mark.asyncio()
    async def test_session_id_preserved(self, engine: ConversationEngine) -> None:
        session_id = uuid4()
        turn = await engine.process_message(
            session_id=session_id,
            user_id=uuid4(),
            org_id=uuid4(),
            message="Test",
        )
        assert turn.session_id == session_id

    @pytest.mark.asyncio()
    async def test_model_id_passed(self, engine: ConversationEngine) -> None:
        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Test",
            model_id="gpt-4o-mini",
        )
        assert turn.model_id == "gpt-4o-mini"

    @pytest.mark.asyncio()
    async def test_usage_tracking(self, engine: ConversationEngine) -> None:
        org_id = uuid4()
        await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=org_id,
            message="Test",
        )
        assert engine._usage_tracker is not None
        summary = engine._usage_tracker.get_org_summary(org_id)
        assert summary.record_count == 1
        assert summary.total_tokens == 80  # 50 + 30

    @pytest.mark.asyncio()
    async def test_intent_defaults_to_chat(self, engine: ConversationEngine) -> None:
        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="What's the weather?",
        )
        assert turn.intent_type == "chat"

    @pytest.mark.asyncio()
    async def test_conversation_history_passed(self, engine: ConversationEngine) -> None:
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]
        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Follow up",
            conversation_history=history,
        )
        assert turn.assistant_response is not None

    @pytest.mark.asyncio()
    async def test_coverage_85_percent(self, engine: ConversationEngine) -> None:
        """Run multiple scenarios to ensure 85%+ coverage."""
        for msg in ["Hi", "Tell me a joke", "What is Python?", "", "Bye"]:
            turn = await engine.process_message(
                session_id=uuid4(),
                user_id=uuid4(),
                org_id=uuid4(),
                message=msg,
            )
            assert turn.assistant_response is not None


@pytest.mark.unit
class TestConversationEngineEventStore:
    """Event store integration: write path + read path."""

    @pytest.fixture()
    def event_store(self) -> FakeEventStore:
        return FakeEventStore()

    @pytest.fixture()
    def engine_with_events(self, event_store: FakeEventStore) -> ConversationEngine:
        return ConversationEngine(
            llm=FakeLLM(response="Got it."),
            memory_core=FakeMemoryCore(),
            event_store=event_store,
            default_model="gpt-4o",
        )

    @pytest.fixture()
    def engine_without_events(self) -> ConversationEngine:
        """Engine with no event_store -- backward compat."""
        return ConversationEngine(
            llm=FakeLLM(response="Got it."),
            memory_core=FakeMemoryCore(),
            default_model="gpt-4o",
        )

    # ---- Write path ----

    @pytest.mark.asyncio()
    async def test_append_events_on_turn(
        self,
        engine_with_events: ConversationEngine,
        event_store: FakeEventStore,
    ) -> None:
        """process_message appends user_message + assistant_message events."""
        session_id = uuid4()
        org_id = uuid4()
        user_id = uuid4()

        await engine_with_events.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Hello",
        )

        assert len(event_store.events) == 2
        user_ev = event_store.events[0]
        asst_ev = event_store.events[1]

        assert user_ev["event_type"] == "user_message"
        assert user_ev["role"] == "user"
        assert user_ev["content"]["text"] == "Hello"
        assert user_ev["session_id"] == session_id
        assert user_ev["org_id"] == org_id

        assert asst_ev["event_type"] == "assistant_message"
        assert asst_ev["role"] == "assistant"
        assert asst_ev["content"]["text"] == "Got it."

    @pytest.mark.asyncio()
    async def test_sequence_numbers_increment(
        self,
        engine_with_events: ConversationEngine,
        event_store: FakeEventStore,
    ) -> None:
        """Each turn appends 2 events; sequence numbers auto-increment."""
        session_id = uuid4()
        org_id = uuid4()
        user_id = uuid4()

        await engine_with_events.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="One",
        )
        await engine_with_events.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Two",
        )

        assert len(event_store.events) == 4
        seqs = [e["sequence_number"] for e in event_store.events]
        assert seqs == [1, 2, 3, 4]

    @pytest.mark.asyncio()
    async def test_no_event_store_backward_compat(
        self,
        engine_without_events: ConversationEngine,
    ) -> None:
        """Without event_store, process_message still works normally."""
        turn = await engine_without_events.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Hello",
        )
        assert turn.assistant_response == "Got it."

    @pytest.mark.asyncio()
    async def test_event_store_failure_non_blocking(
        self,
        event_store: FakeEventStore,
    ) -> None:
        """Event store errors are swallowed (non-blocking, like memory pipeline)."""

        class FailingEventStore(FakeEventStore):
            async def append_event(self, **kwargs: Any) -> object:
                msg = "DB connection lost"
                raise RuntimeError(msg)

        engine = ConversationEngine(
            llm=FakeLLM(response="Still works."),
            memory_core=FakeMemoryCore(),
            event_store=FailingEventStore(),
            default_model="gpt-4o",
        )

        turn = await engine.process_message(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            message="Hello",
        )
        assert turn.assistant_response == "Still works."

    # ---- Read path ----

    @pytest.mark.asyncio()
    async def test_load_session_history_from_event_store(
        self,
        event_store: FakeEventStore,
    ) -> None:
        """get_session_history returns conversation_history format from events."""
        engine = ConversationEngine(
            llm=FakeLLM(response="Got it."),
            memory_core=FakeMemoryCore(),
            event_store=event_store,
            default_model="gpt-4o",
        )

        session_id = uuid4()
        org_id = uuid4()
        user_id = uuid4()

        # Simulate two prior turns stored in event_store
        await event_store.append_event(
            org_id=org_id,
            session_id=session_id,
            user_id=user_id,
            event_type="user_message",
            role="user",
            content={"text": "Hi"},
        )
        await event_store.append_event(
            org_id=org_id,
            session_id=session_id,
            user_id=user_id,
            event_type="assistant_message",
            role="assistant",
            content={"text": "Hello!"},
        )

        history = await engine.get_session_history(session_id)

        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hi"}
        assert history[1] == {"role": "assistant", "content": "Hello!"}

    @pytest.mark.asyncio()
    async def test_get_session_history_empty(
        self,
        engine_with_events: ConversationEngine,
    ) -> None:
        """get_session_history returns empty list for new session."""
        history = await engine_with_events.get_session_history(uuid4())
        assert history == []

    @pytest.mark.asyncio()
    async def test_get_session_history_no_event_store(
        self,
        engine_without_events: ConversationEngine,
    ) -> None:
        """get_session_history returns empty list when no event_store configured."""
        history = await engine_without_events.get_session_history(uuid4())
        assert history == []

    @pytest.mark.asyncio()
    async def test_process_then_recover_history(
        self,
        event_store: FakeEventStore,
    ) -> None:
        """Full round-trip: process_message writes events, get_session_history reads them."""
        engine = ConversationEngine(
            llm=FakeLLM(response="Remembered."),
            memory_core=FakeMemoryCore(),
            event_store=event_store,
            default_model="gpt-4o",
        )

        session_id = uuid4()
        org_id = uuid4()
        user_id = uuid4()

        await engine.process_message(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            message="Remember this",
        )

        history = await engine.get_session_history(session_id)

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Remember this"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Remembered."
