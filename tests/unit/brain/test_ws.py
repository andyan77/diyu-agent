"""Tests for B2-8: WebSocket real-time conversation.

Validates:
- WS message handling (message, ping, close)
- Session persistence across turns
- Stream start/end signaling
- First-byte latency (< 500ms in test env)
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine
from src.brain.engine.ws_handler import WSChatHandler, WSMessage
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, PromotionReceipt, WriteReceipt


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
    """Fake LLM for WS tests."""

    async def call(self, prompt, model_id, content_parts=None, parameters=None):
        return LLMResponse(
            text="WS response",
            tokens_used={"input": 10, "output": 15},
            model_id=model_id,
        )


class FakeEventStore:
    """In-memory event store satisfying EventStoreProtocol for WS tests."""

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
    ) -> dict[str, Any]:
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
    ) -> list[dict[str, Any]]:
        result = [e for e in self.events if e["session_id"] == session_id]
        result.sort(key=lambda e: e["sequence_number"])
        if limit:
            result = result[:limit]
        return result


class FakeWSsender:
    """Captures sent WebSocket messages."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send(self, data: dict[str, Any]) -> None:
        self.sent.append(data)


@pytest.mark.unit
class TestWSChatHandler:
    """B2-8: WebSocket real-time chat."""

    @pytest.fixture()
    def event_store(self) -> FakeEventStore:
        return FakeEventStore()

    @pytest.fixture()
    def handler(self, event_store: FakeEventStore) -> WSChatHandler:
        memory_core = FakeMemoryCore()
        llm = FakeLLM()
        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            event_store=event_store,
            default_model="gpt-4o",
        )
        return WSChatHandler(engine=engine)

    @pytest.fixture()
    def sender(self) -> FakeWSsender:
        return FakeWSsender()

    @pytest.mark.asyncio()
    async def test_handle_ping(
        self,
        handler: WSChatHandler,
        sender: FakeWSsender,
    ) -> None:
        msg = WSMessage(
            type="ping",
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
        )
        response = await handler.handle_message(msg, sender)
        assert response.type == "pong"
        assert sender.sent[0]["type"] == "pong"

    @pytest.mark.asyncio()
    async def test_handle_close(
        self,
        handler: WSChatHandler,
        sender: FakeWSsender,
    ) -> None:
        session_id = uuid4()
        msg = WSMessage(
            type="close",
            session_id=session_id,
            user_id=uuid4(),
            org_id=uuid4(),
        )
        response = await handler.handle_message(msg, sender)
        assert response.type == "close"

    @pytest.mark.asyncio()
    async def test_handle_message(
        self,
        handler: WSChatHandler,
        sender: FakeWSsender,
    ) -> None:
        msg = WSMessage(
            type="message",
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            content="Hello via WS",
        )
        response = await handler.handle_message(msg, sender)
        assert response.type == "message"
        assert response.content == "WS response"
        # Should send: stream_start, message, stream_end
        types = [s["type"] for s in sender.sent]
        assert "stream_start" in types
        assert "message" in types
        assert "stream_end" in types

    @pytest.mark.asyncio()
    async def test_session_persistence(
        self,
        handler: WSChatHandler,
        sender: FakeWSsender,
        event_store: FakeEventStore,
    ) -> None:
        session_id = uuid4()
        user_id = uuid4()
        org_id = uuid4()

        # Turn 1
        msg1 = WSMessage(
            type="message",
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            content="Hello",
        )
        await handler.handle_message(msg1, sender)

        # Turn 2 -- should have history from turn 1 via event_store
        msg2 = WSMessage(
            type="message",
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            content="Follow up",
        )
        await handler.handle_message(msg2, sender)

        # Verify events persisted in event_store (2 turns x 2 events each)
        events = await event_store.get_session_events(session_id)
        assert len(events) == 4
        assert events[0]["role"] == "user"
        assert events[1]["role"] == "assistant"

    @pytest.mark.asyncio()
    async def test_history_recoverable_after_restart(
        self,
        event_store: FakeEventStore,
        sender: FakeWSsender,
    ) -> None:
        """History should be available via event_store even with a new handler."""
        session_id = uuid4()
        user_id = uuid4()
        org_id = uuid4()

        # Turn 1 with original handler
        engine1 = ConversationEngine(
            llm=FakeLLM(),
            memory_core=FakeMemoryCore(),
            event_store=event_store,
            default_model="gpt-4o",
        )
        handler1 = WSChatHandler(engine=engine1)
        msg1 = WSMessage(
            type="message",
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            content="Hello",
        )
        await handler1.handle_message(msg1, sender)

        # Simulate restart: new engine, same event_store
        engine2 = ConversationEngine(
            llm=FakeLLM(),
            memory_core=FakeMemoryCore(),
            event_store=event_store,
            default_model="gpt-4o",
        )
        history = await engine2.get_session_history(session_id)
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "WS response"}

    @pytest.mark.asyncio()
    async def test_first_byte_latency(
        self,
        handler: WSChatHandler,
        sender: FakeWSsender,
    ) -> None:
        """First-byte latency must be < 500ms."""
        msg = WSMessage(
            type="message",
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            content="Speed test",
        )
        start = time.monotonic()
        await handler.handle_message(msg, sender)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500, f"First-byte latency {elapsed_ms:.0f}ms exceeds 500ms"
