"""Tests for WebSocket streaming endpoint (G2-2).

Acceptance: pytest tests/unit/gateway/test_ws.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from starlette.testclient import TestClient

from src.brain.engine.ws_handler import WSChatHandler
from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.gateway.ws.conversation import create_ws_router
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, PromotionReceipt, WriteReceipt

_JWT_SECRET = "test-secret-for-g2-2"  # noqa: S105


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
    """Fake LLM that returns a fixed response."""

    async def call(self, prompt, model_id, content_parts=None, parameters=None):
        return LLMResponse(
            text="Hello! How can I help?",
            tokens_used={"input": 5, "output": 7},
            model_id=model_id or "gpt-4o",
        )


@pytest.fixture()
def ws_handler():
    memory_core = FakeMemoryCore()
    llm = FakeLLM()
    from src.brain.engine.conversation import ConversationEngine

    engine = ConversationEngine(llm=llm, memory_core=memory_core, default_model="gpt-4o")
    return WSChatHandler(engine)


@pytest.fixture()
def app(ws_handler: WSChatHandler):
    app = create_app(jwt_secret=_JWT_SECRET)
    ws_router = create_ws_router(handler=ws_handler, jwt_secret=_JWT_SECRET)
    app.include_router(ws_router)
    return app


@pytest.fixture()
def sync_client(app):
    """Sync test client for WebSocket tests."""
    return TestClient(app)


@pytest.fixture()
def valid_token():
    return encode_token(
        user_id=uuid4(),
        org_id=uuid4(),
        secret=_JWT_SECRET,
    )


class TestWebSocketAuth:
    """WS authentication tests."""

    def test_no_token_rejected(self, sync_client: TestClient):
        with (
            pytest.raises(Exception),  # noqa: B017
            sync_client.websocket_connect(f"/ws/conversations/{uuid4()}"),
        ):
            pass

    def test_invalid_token_rejected(self, sync_client: TestClient):
        with (
            pytest.raises(Exception),  # noqa: B017
            sync_client.websocket_connect(f"/ws/conversations/{uuid4()}?token=invalid"),
        ):
            pass

    def test_valid_token_connects(self, sync_client: TestClient, valid_token: str):
        session_id = uuid4()
        with sync_client.websocket_connect(
            f"/ws/conversations/{session_id}?token={valid_token}"
        ) as ws:
            # Send ping to verify connection
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"


class TestWebSocketMessages:
    """WS message handling tests."""

    def test_ping_pong(self, sync_client: TestClient, valid_token: str):
        with sync_client.websocket_connect(
            f"/ws/conversations/{uuid4()}?token={valid_token}"
        ) as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_message_response(self, sync_client: TestClient, valid_token: str):
        session_id = uuid4()
        with sync_client.websocket_connect(
            f"/ws/conversations/{session_id}?token={valid_token}"
        ) as ws:
            ws.send_json({"type": "message", "content": "Hi"})

            # Should receive stream_start, message, stream_end
            start = ws.receive_json()
            assert start["type"] == "stream_start"

            msg = ws.receive_json()
            assert msg["type"] == "message"
            assert msg["content"] == "Hello! How can I help?"
            assert "turn_id" in msg
            assert "tokens_used" in msg

            end = ws.receive_json()
            assert end["type"] == "stream_end"

    def test_close_message(self, sync_client: TestClient, valid_token: str):
        with sync_client.websocket_connect(
            f"/ws/conversations/{uuid4()}?token={valid_token}"
        ) as ws:
            ws.send_json({"type": "close"})
            # Connection should close gracefully
