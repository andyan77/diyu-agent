"""Tests for SSE notification endpoint (G2-7).

Acceptance: pytest tests/unit/gateway/test_sse.py -v
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.gateway.app import create_app
from src.gateway.middleware.auth import encode_token
from src.gateway.sse.events import EVENT_TYPES, SSEBroadcaster, create_sse_router

_JWT_SECRET = "test-secret-for-g2-7"  # noqa: S105


@pytest.fixture()
def broadcaster():
    return SSEBroadcaster()


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
async def client(broadcaster):
    app = create_app(jwt_secret=_JWT_SECRET)
    app.include_router(create_sse_router(broadcaster=broadcaster, jwt_secret=_JWT_SECRET))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestSSEBroadcaster:
    """Unit tests for SSEBroadcaster."""

    def test_subscribe_returns_queue(self):
        b = SSEBroadcaster()
        org_id = uuid4()
        sub_id, queue = b.subscribe(org_id)
        assert isinstance(sub_id, str)
        assert isinstance(queue, asyncio.Queue)
        assert b.subscriber_count == 1

    def test_unsubscribe_removes(self):
        b = SSEBroadcaster()
        org_id = uuid4()
        sub_id, _ = b.subscribe(org_id)
        b.unsubscribe(org_id, sub_id)
        assert b.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_publish_reaches_subscriber(self):
        b = SSEBroadcaster()
        org_id = uuid4()
        _, queue = b.subscribe(org_id)

        count = await b.publish(org_id, "system_notification", {"message": "hello"})
        assert count == 1

        event = queue.get_nowait()
        assert event["event"] == "system_notification"
        assert event["data"]["message"] == "hello"

    @pytest.mark.asyncio
    async def test_publish_tenant_isolation(self):
        b = SSEBroadcaster()
        org_a = uuid4()
        org_b = uuid4()
        _, queue_a = b.subscribe(org_a)
        _, queue_b = b.subscribe(org_b)

        await b.publish(org_a, "budget_warning", {"remaining": 100})

        assert queue_b.empty() is not False  # queue_b should be empty
        assert queue_b.qsize() == 0
        assert queue_a.qsize() == 1

    @pytest.mark.asyncio
    async def test_publish_unknown_event_type(self):
        b = SSEBroadcaster()
        org_id = uuid4()
        b.subscribe(org_id)

        count = await b.publish(org_id, "unknown_event", {})
        assert count == 0

    @pytest.mark.asyncio
    async def test_shutdown_signals_subscribers(self):
        b = SSEBroadcaster()
        org_id = uuid4()
        _, queue = b.subscribe(org_id)

        await b.shutdown()
        event = queue.get_nowait()
        assert event is None  # Shutdown signal
        assert b.subscriber_count == 0

    def test_all_six_event_types_registered(self):
        assert len(EVENT_TYPES) == 6
        assert "task_status_update" in EVENT_TYPES
        assert "system_notification" in EVENT_TYPES
        assert "budget_warning" in EVENT_TYPES
        assert "knowledge_update" in EVENT_TYPES
        assert "media_event" in EVENT_TYPES
        assert "experiment_update" in EVENT_TYPES


class TestSSEPublishEndpoint:
    """POST /api/v1/events/publish"""

    @pytest.mark.asyncio
    async def test_publish_success(
        self,
        client: AsyncClient,
        auth_headers,
        broadcaster: SSEBroadcaster,
        test_user,
    ):
        # Subscribe first
        broadcaster.subscribe(test_user["org_id"])

        resp = await client.post(
            "/api/v1/events/publish",
            headers=auth_headers,
            json={
                "event_type": "system_notification",
                "data": {"message": "Test notification"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["published"] is True
        assert data["subscribers_notified"] == 1

    @pytest.mark.asyncio
    async def test_publish_unknown_event_type(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/events/publish",
            headers=auth_headers,
            json={"event_type": "invalid_type", "data": {}},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_publish_no_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/events/publish",
            json={"event_type": "system_notification", "data": {}},
        )
        assert resp.status_code == 401
