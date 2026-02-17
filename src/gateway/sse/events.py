"""SSE notification endpoint.

Task card: G2-7
- 6 event types: task_status_update, system_notification,
  budget_warning, knowledge_update, media_event, experiment_update
- Tenant-isolated push
- SaaS: via BFF proxy; Private: direct + token param

Architecture: 05a-API-Contract Section 5.2
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.gateway.middleware.auth import decode_token
from src.shared.errors import AuthenticationError

logger = logging.getLogger(__name__)

EVENT_TYPES = frozenset(
    {
        "task_status_update",
        "system_notification",
        "budget_warning",
        "knowledge_update",
        "media_event",
        "experiment_update",
    }
)


class SSEBroadcaster:
    """Manages SSE connections and event broadcast per tenant.

    Each connected client gets its own asyncio.Queue.
    Events are broadcast to all clients of the same org.
    """

    def __init__(self) -> None:
        self._subscribers: dict[UUID, dict[str, asyncio.Queue[dict[str, Any] | None]]] = (
            defaultdict(dict)
        )

    def subscribe(self, org_id: UUID) -> tuple[str, asyncio.Queue[dict[str, Any] | None]]:
        """Register a new SSE subscriber.

        Returns:
            Tuple of (subscriber_id, event_queue).
        """
        sub_id = str(uuid4())
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._subscribers[org_id][sub_id] = queue
        logger.info("SSE subscriber added sub_id=%s org_id=%s", sub_id, org_id)
        return sub_id, queue

    def unsubscribe(self, org_id: UUID, sub_id: str) -> None:
        """Remove an SSE subscriber."""
        org_subs = self._subscribers.get(org_id, {})
        org_subs.pop(sub_id, None)
        if not org_subs:
            self._subscribers.pop(org_id, None)
        logger.info("SSE subscriber removed sub_id=%s org_id=%s", sub_id, org_id)

    async def publish(
        self,
        org_id: UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """Publish an event to all subscribers of an org.

        Returns:
            Number of subscribers notified.
        """
        if event_type not in EVENT_TYPES:
            logger.warning("Unknown SSE event type: %s", event_type)
            return 0

        event = {
            "id": str(uuid4()),
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        org_subs = self._subscribers.get(org_id, {})
        count = 0
        for queue in org_subs.values():
            try:
                queue.put_nowait(event)
                count += 1
            except asyncio.QueueFull:
                logger.warning("SSE queue full for org_id=%s", org_id)
        return count

    async def shutdown(self) -> None:
        """Signal all subscribers to disconnect."""
        for org_subs in self._subscribers.values():
            for queue in org_subs.values():
                with contextlib.suppress(asyncio.QueueFull):
                    queue.put_nowait(None)
        self._subscribers.clear()

    @property
    def subscriber_count(self) -> int:
        return sum(len(subs) for subs in self._subscribers.values())


def create_sse_router(
    *,
    broadcaster: SSEBroadcaster,
    jwt_secret: str,
) -> APIRouter:
    """Create SSE event router with dependency injection."""
    router = APIRouter(prefix="/api/v1/events", tags=["events"])

    @router.get("/stream")
    async def event_stream(request: Request) -> StreamingResponse:
        """SSE event stream for authenticated user.

        Supports token via Authorization header (normal) or
        query param ?token=... (Private deploy / EventSource).
        """
        # Extract org_id from request state (set by JWT middleware)
        org_id: UUID | None = getattr(request.state, "org_id", None)

        # Fallback: token query param for EventSource (no custom headers)
        if org_id is None:
            token = request.query_params.get("token")
            if not token:
                raise HTTPException(status_code=401, detail="Authentication required")
            try:
                payload = decode_token(token, secret=jwt_secret)
                org_id = payload.org_id
            except AuthenticationError:
                raise HTTPException(status_code=401, detail="Invalid token") from None

        sub_id, queue = broadcaster.subscribe(org_id)

        async def generate() -> Any:
            try:
                while True:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        break

                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    except TimeoutError:
                        # Send keepalive comment
                        yield ": keepalive\n\n"
                        continue

                    if event is None:
                        # Shutdown signal
                        break

                    yield (
                        f"id: {event['id']}\n"
                        f"event: {event['event']}\n"
                        f"data: {json.dumps(event['data'])}\n\n"
                    )
            finally:
                broadcaster.unsubscribe(org_id, sub_id)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post("/publish")
    async def publish_event(request: Request) -> dict[str, Any]:
        """Publish an event (internal/admin use only)."""
        org_id: UUID = request.state.org_id
        body = await request.json()

        event_type = body.get("event_type", "")
        if event_type not in EVENT_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown event type: {event_type}. Allowed: {sorted(EVENT_TYPES)}",
            )

        data = body.get("data", {})
        count = await broadcaster.publish(org_id, event_type, data)

        return {"published": True, "subscribers_notified": count}

    return router
