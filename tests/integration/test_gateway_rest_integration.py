"""Integration test for Gateway REST API (WF2-B3).

Tests full conversation flow through the Gateway:
  HTTP request -> JWT auth -> ConversationEngine -> LLM -> Response

Uses in-memory adapters (no external services required).
"""

from __future__ import annotations

import fnmatch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.brain.engine.conversation import ConversationEngine
from src.gateway.api.conversations import _reset_stores, create_conversation_router
from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.storage_port import StoragePort

_JWT_SECRET = "test-integration-gateway-rest-secret-32b"  # noqa: S105


class InMemoryStorage(StoragePort):
    """In-memory storage for integration testing."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    async def put(self, key, value, ttl=None):
        self._data[key] = value

    async def get(self, key):
        return self._data.get(key)

    async def delete(self, key):
        self._data.pop(key, None)

    async def list_keys(self, pattern):
        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]


class FakeLLMPort(LLMCallPort):
    """Fake LLM for integration testing."""

    def __init__(self) -> None:
        self.call_count = 0

    async def call(self, prompt, model_id, content_parts=None, parameters=None):
        self.call_count += 1
        return LLMResponse(
            text=f"Integration response #{self.call_count}",
            tokens_used={"input": 20, "output": 10},
            model_id=model_id,
        )


@pytest.fixture(autouse=True)
def _clean():
    _reset_stores()
    yield
    _reset_stores()


@pytest.fixture()
def engine():
    storage = InMemoryStorage()
    memory_core = PgMemoryCoreAdapter(storage=storage)
    llm = FakeLLMPort()
    return ConversationEngine(llm=llm, memory_core=memory_core, default_model="gpt-4o")


@pytest.fixture()
async def client(engine):
    app = create_app(jwt_secret=_JWT_SECRET)
    app.include_router(create_conversation_router(engine=engine))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
def user():
    return {"user_id": uuid4(), "org_id": uuid4()}


@pytest.fixture()
def auth_headers(user):
    token = encode_token(user_id=user["user_id"], org_id=user["org_id"], secret=_JWT_SECRET)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestGatewayRestIntegration:
    """End-to-end REST conversation flow through Gateway -> Brain -> LLM."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, client: AsyncClient, auth_headers):
        """Create conversation, send message, verify response and history."""
        # Step 1: Create conversation
        resp = await client.post("/api/v1/conversations/", headers=auth_headers, json={})
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        # Step 2: Send message (hits real ConversationEngine -> FakeLLM)
        resp = await client.post(
            f"/api/v1/conversations/{session_id}/messages",
            headers=auth_headers,
            json={"message": "Hello, integration test!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Integration response" in data["assistant_response"]
        assert data["tokens_used"]["input"] == 20
        assert data["tokens_used"]["output"] == 10
        assert data["model_id"] == "gpt-4o"

        # Step 3: Verify message history
        resp = await client.get(
            f"/api/v1/conversations/{session_id}/messages",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        msgs = resp.json()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello, integration test!"
        assert msgs[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, client: AsyncClient, auth_headers):
        """Multiple messages in same conversation preserve history."""
        session_id = uuid4()

        # Turn 1
        resp = await client.post(
            f"/api/v1/conversations/{session_id}/messages",
            headers=auth_headers,
            json={"message": "First message"},
        )
        assert resp.status_code == 200

        # Turn 2
        resp = await client.post(
            f"/api/v1/conversations/{session_id}/messages",
            headers=auth_headers,
            json={"message": "Second message"},
        )
        assert resp.status_code == 200

        # Verify 4 messages (2 user + 2 assistant)
        resp = await client.get(
            f"/api/v1/conversations/{session_id}/messages",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 4

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, client: AsyncClient):
        """Requests without JWT are rejected at gateway level."""
        resp = await client.post(
            f"/api/v1/conversations/{uuid4()}/messages",
            json={"message": "Should fail"},
        )
        assert resp.status_code == 401
