"""Tests for B2-8: WebSocket real-time conversation.

Validates:
- WS message handling (message, ping, close)
- Session persistence across turns
- Stream start/end signaling
- First-byte latency (< 500ms in test env)
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine
from src.brain.engine.ws_handler import WSChatHandler, WSMessage
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.storage_port import StoragePort


class FakeStoragePort(StoragePort):
    """In-memory storage for testing."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    async def put(self, key, value, ttl=None):
        self._data[key] = value

    async def get(self, key):
        return self._data.get(key)

    async def delete(self, key):
        self._data.pop(key, None)

    async def list_keys(self, pattern):
        import fnmatch

        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]


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
        storage = FakeStoragePort()
        memory_core = PgMemoryCoreAdapter(storage=storage)
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
