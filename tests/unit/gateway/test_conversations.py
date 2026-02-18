"""Tests for Conversation REST API (G2-1).

Acceptance: pytest tests/unit/gateway/test_conversations.py -v
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.brain.engine.context_assembler import AssembledContext
from src.brain.engine.conversation import ConversationTurn
from src.gateway.api.conversations import _reset_stores, create_conversation_router
from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token

_JWT_SECRET = "test-secret-for-g2-1"  # noqa: S105

_FIXED_TURN = ConversationTurn(
    turn_id=uuid4(),
    session_id=uuid4(),
    user_message="Hello",
    assistant_response="Hi there! How can I help?",
    context=AssembledContext(),
    tokens_used={"input": 12, "output": 8},
    model_id="gpt-4o",
    intent_type="chat",
)


class FakeConversationEngine:
    """Fake ConversationPort implementation that records calls."""

    def __init__(self, turn: ConversationTurn = _FIXED_TURN) -> None:
        self._turn = turn
        self.calls: list[dict[str, Any]] = []
        self._history: dict[UUID, list[dict[str, str]]] = {}

    async def process_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
        message: str,
        org_context: Any = None,
        conversation_history: list[dict[str, Any]] | None = None,
        model_id: str | None = None,
    ) -> ConversationTurn:
        self.calls.append(
            {
                "session_id": session_id,
                "user_id": user_id,
                "org_id": org_id,
                "message": message,
                "conversation_history": conversation_history,
                "model_id": model_id,
            }
        )
        self._history.setdefault(session_id, [])
        self._history[session_id].append({"role": "user", "content": message})
        self._history[session_id].append(
            {"role": "assistant", "content": self._turn.assistant_response}
        )
        return self._turn

    async def get_session_history(self, session_id: UUID) -> list[dict[str, Any]]:
        return list(self._history.get(session_id, []))


@pytest.fixture(autouse=True)
def _clean_stores():
    """Reset in-memory stores before each test."""
    _reset_stores()
    yield
    _reset_stores()


@pytest.fixture()
def test_user():
    return {"user_id": uuid4(), "org_id": uuid4()}


@pytest.fixture()
def auth_headers(test_user: dict[str, UUID]):
    token = encode_token(
        user_id=test_user["user_id"],
        org_id=test_user["org_id"],
        secret=_JWT_SECRET,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def fake_engine():
    return FakeConversationEngine()


@pytest.fixture()
async def client(fake_engine: FakeConversationEngine):
    app = create_app(jwt_secret=_JWT_SECRET)
    app.include_router(create_conversation_router(engine=fake_engine))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestSendMessage:
    """POST /api/v1/conversations/{id}/messages"""

    @pytest.mark.asyncio
    async def test_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        fake_engine: FakeConversationEngine,
        test_user: dict[str, UUID],
    ):
        sid = uuid4()
        resp = await client.post(
            f"/api/v1/conversations/{sid}/messages",
            headers=auth_headers,
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["assistant_response"] == "Hi there! How can I help?"
        assert data["tokens_used"] == {"input": 12, "output": 8}
        assert data["model_id"] == "gpt-4o"
        assert data["intent_type"] == "chat"
        assert "turn_id" in data
        assert "session_id" in data

        assert len(fake_engine.calls) == 1
        kw = fake_engine.calls[0]
        assert kw["session_id"] == sid
        assert kw["user_id"] == test_user["user_id"]
        assert kw["org_id"] == test_user["org_id"]
        assert kw["message"] == "Hello"

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.post(
            f"/api/v1/conversations/{uuid4()}/messages",
            json={"message": "Hello"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_message_returns_422(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"/api/v1/conversations/{uuid4()}/messages",
            headers=auth_headers,
            json={"message": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_message_field_returns_422(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"/api/v1/conversations/{uuid4()}/messages",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_with_model_id(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        fake_engine: FakeConversationEngine,
    ):
        resp = await client.post(
            f"/api/v1/conversations/{uuid4()}/messages",
            headers=auth_headers,
            json={"message": "Hello", "model_id": "gpt-3.5-turbo"},
        )
        assert resp.status_code == 200
        kw = fake_engine.calls[0]
        assert kw["model_id"] == "gpt-3.5-turbo"


class TestConversationCRUD:
    """POST / and GET / and GET /{id}/messages"""

    @pytest.mark.asyncio
    async def test_create_conversation(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.post(
            "/api/v1/conversations/",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        UUID(data["session_id"])  # valid UUID
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_list_conversations(self, client: AsyncClient, auth_headers: dict[str, str]):
        # Create two conversations
        await client.post("/api/v1/conversations/", headers=auth_headers, json={})
        await client.post("/api/v1/conversations/", headers=auth_headers, json={})

        resp = await client.get("/api/v1/conversations/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_messages_empty(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.get(
            f"/api/v1/conversations/{uuid4()}/messages",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_messages_after_send(self, client: AsyncClient, auth_headers: dict[str, str]):
        sid = uuid4()
        await client.post(
            f"/api/v1/conversations/{sid}/messages",
            headers=auth_headers,
            json={"message": "Hello"},
        )
        resp = await client.get(
            f"/api/v1/conversations/{sid}/messages",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        msgs = resp.json()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello"
        assert msgs[1]["role"] == "assistant"
