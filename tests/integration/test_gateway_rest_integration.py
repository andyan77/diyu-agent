"""Integration test for Gateway REST API (WF2-B3).

Tests full conversation flow through the Gateway:
  HTTP request -> JWT auth -> ConversationEngine -> LLM -> Response

Uses in-memory adapters (no external services required).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.brain.engine.conversation import ConversationEngine
from src.gateway.api.conversations import _reset_stores, create_conversation_router
from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.ports.llm_call_port import LLMCallPort, LLMResponse
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, WriteReceipt

_JWT_SECRET = "test-integration-gateway-rest-secret-32b"  # noqa: S105


class FakeMemoryCore(MemoryCorePort):
    """In-memory MemoryCorePort for integration testing."""

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


class FakeEventStore:
    """In-memory event store satisfying EventStoreProtocol for integration tests."""

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


@pytest.fixture(autouse=True)
def _clean():
    _reset_stores()
    yield
    _reset_stores()


@pytest.fixture()
def engine():
    memory_core = FakeMemoryCore()
    llm = FakeLLMPort()
    event_store = FakeEventStore()
    return ConversationEngine(
        llm=llm,
        memory_core=memory_core,
        event_store=event_store,
        default_model="gpt-4o",
    )


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
