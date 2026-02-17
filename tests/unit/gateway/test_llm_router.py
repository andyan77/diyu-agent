"""Tests for LLM Gateway router (G2-3).

Acceptance: pytest tests/unit/gateway/test_llm_router.py -v
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.gateway.app import create_app
from src.gateway.llm.router import create_llm_router
from src.gateway.middleware.auth import encode_token
from src.ports.llm_call_port import LLMCallPort, LLMResponse

_JWT_SECRET = "test-secret-for-g2-3"  # noqa: S105

_FIXED_RESPONSE = LLMResponse(
    text="The answer is 42.",
    tokens_used={"input": 10, "output": 5},
    model_id="gpt-4o",
    finish_reason="stop",
)


class FakeLLMAdapter(LLMCallPort):
    """Fake LLM adapter implementing LLMCallPort."""

    def __init__(self, response: LLMResponse = _FIXED_RESPONSE) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []
        self.should_fail: bool = False

    async def call(
        self,
        prompt: str,
        model_id: str,
        content_parts: Any = None,
        parameters: dict[str, Any] | None = None,
    ) -> LLMResponse:
        if self.should_fail:
            msg = "Provider down"
            raise RuntimeError(msg)
        self.calls.append({"prompt": prompt, "model_id": model_id, "parameters": parameters})
        return self._response


class FakeUsageTracker:
    """Fake usage tracker that records calls."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def record_usage(
        self,
        *,
        org_id: UUID,
        user_id: UUID,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self.calls.append(
            {
                "org_id": org_id,
                "user_id": user_id,
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )


@pytest.fixture()
def test_user():
    return {"user_id": uuid4(), "org_id": uuid4()}


@pytest.fixture()
def auth_headers(test_user):
    token = encode_token(
        user_id=test_user["user_id"],
        org_id=test_user["org_id"],
        secret=_JWT_SECRET,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def fake_llm():
    return FakeLLMAdapter()


@pytest.fixture()
def fake_tracker():
    return FakeUsageTracker()


@pytest.fixture()
async def client(fake_llm, fake_tracker):
    app = create_app(jwt_secret=_JWT_SECRET)
    app.include_router(create_llm_router(llm_adapter=fake_llm, usage_tracker=fake_tracker))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestListModels:
    """GET /api/v1/llm/models"""

    @pytest.mark.asyncio
    async def test_list_models(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/v1/llm/models", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert len(data["models"]) > 0
        assert any(m["id"] == "gpt-4o" for m in data["models"])

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/llm/models")
        assert resp.status_code == 401


class TestCallLLM:
    """POST /api/v1/llm/call"""

    @pytest.mark.asyncio
    async def test_call_success(
        self,
        client: AsyncClient,
        auth_headers,
        fake_llm: FakeLLMAdapter,
        fake_tracker: FakeUsageTracker,
        test_user,
    ):
        resp = await client.post(
            "/api/v1/llm/call",
            headers=auth_headers,
            json={"prompt": "What is 6 * 7?", "model_id": "gpt-4o"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "The answer is 42."
        assert data["tokens_used"] == {"input": 10, "output": 5}
        assert data["model_id"] == "gpt-4o"
        assert data["finish_reason"] == "stop"

        # Verify LLM was called
        assert len(fake_llm.calls) == 1

        # Verify usage tracking
        assert len(fake_tracker.calls) == 1
        kw = fake_tracker.calls[0]
        assert kw["org_id"] == test_user["org_id"]
        assert kw["input_tokens"] == 10
        assert kw["output_tokens"] == 5

    @pytest.mark.asyncio
    async def test_call_default_model(
        self, client: AsyncClient, auth_headers, fake_llm: FakeLLMAdapter
    ):
        resp = await client.post(
            "/api/v1/llm/call",
            headers=auth_headers,
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 200
        assert fake_llm.calls[0]["model_id"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_call_failure_returns_502(
        self, client: AsyncClient, auth_headers, fake_llm: FakeLLMAdapter
    ):
        fake_llm.should_fail = True
        resp = await client.post(
            "/api/v1/llm/call",
            headers=auth_headers,
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/llm/call",
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 401
