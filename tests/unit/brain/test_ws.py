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
from src.shared.types import MemoryItem, Observation, WriteReceipt


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


class FakeLLM(LLMCallPort):
    """Fake LLM for WS tests."""

    async def call(self, prompt, model_id, content_parts=None, parameters=None):
        return LLMResponse(
            text="WS response",
            tokens_used={"input": 10, "output": 15},
            model_id=model_id,
        )


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
    def handler(self) -> WSChatHandler:
        memory_core = FakeMemoryCore()
        llm = FakeLLM()
        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,
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

        # Turn 2 -- should have history from turn 1
        msg2 = WSMessage(
            type="message",
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            content="Follow up",
        )
        await handler.handle_message(msg2, sender)

        assert session_id in handler._sessions
        assert len(handler._sessions[session_id]) == 4  # 2 user + 2 assistant

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
