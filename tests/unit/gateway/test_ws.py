"""Tests for WebSocket streaming endpoint (G2-2).

Acceptance: pytest tests/unit/gateway/test_ws.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from src.brain.engine.ws_handler import WSChatHandler
from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.gateway.ws.conversation import create_ws_router
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.storage_port import StoragePort

_JWT_SECRET = "test-secret-for-g2-2"  # noqa: S105


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
    """Fake LLM that returns a fixed response."""

    async def call(self, prompt, model_id, content_parts=None, parameters=None):
        return LLMResponse(
            text="Hello! How can I help?",
            tokens_used={"input": 5, "output": 7},
            model_id=model_id or "gpt-4o",
        )


@pytest.fixture()
def ws_handler():
    storage = FakeStoragePort()
    memory_core = PgMemoryCoreAdapter(storage=storage)
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
