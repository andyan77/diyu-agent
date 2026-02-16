"""Event Outbox pattern for reliable at-least-once event delivery.

Task card: I1-6
- Business write + outbox insert in same transaction
- Poller reads pending events and publishes them
- Idempotency via event_id dedup
- Delivery success rate target: >= 99.9%

Architecture: 06 Section 1.6 (Outbox Pattern)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


class EventStatus(enum.Enum):
    """Outbox event lifecycle states."""

    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class OutboxEvent:
    """An event in the outbox table."""

    id: UUID
    org_id: UUID
    event_type: str
    payload: dict[str, Any]
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    max_retries: int = 5
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None
    error_message: str | None = None


class EventOutbox:
    """In-memory outbox for unit testing and light usage.

    Production adapter will use the event_outbox SQL table
    via SQLAlchemy AsyncSession (same transaction as business write).
    """

    def __init__(self) -> None:
        self._events: dict[UUID, OutboxEvent] = {}

    def append(
        self,
        *,
        org_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        max_retries: int = 5,
    ) -> OutboxEvent:
        """Append a new event to the outbox.

        Must be called within the same transaction as the business write
        to guarantee at-least-once delivery.

        Args:
            org_id: Organization scope for RLS.
            event_type: Event type identifier (e.g. "user.created").
            payload: JSON-serializable event data.
            max_retries: Maximum delivery attempts.

        Returns:
            The created OutboxEvent.
        """
        event = OutboxEvent(
            id=uuid4(),
            org_id=org_id,
            event_type=event_type,
            payload=payload,
            max_retries=max_retries,
        )
        self._events[event.id] = event
        return event

    def get_pending(self, *, limit: int = 100) -> list[OutboxEvent]:
        """Fetch pending events for delivery, ordered by creation time.

        Args:
            limit: Max number of events to return.

        Returns:
            List of pending OutboxEvents.
        """
        pending = [e for e in self._events.values() if e.status == EventStatus.PENDING]
        pending.sort(key=lambda e: e.created_at)
        return pending[:limit]

    def mark_processing(self, event_id: UUID) -> bool:
        """Transition event from PENDING to PROCESSING.

        Returns False if event not found or not in PENDING state.
        """
        event = self._events.get(event_id)
        if not event or event.status != EventStatus.PENDING:
            return False
        event.status = EventStatus.PROCESSING
        return True

    def mark_delivered(self, event_id: UUID) -> bool:
        """Transition event to DELIVERED.

        Returns False if event not found or not in PROCESSING state.
        """
        event = self._events.get(event_id)
        if not event or event.status != EventStatus.PROCESSING:
            return False
        event.status = EventStatus.DELIVERED
        event.processed_at = datetime.now(UTC)
        return True

    def mark_failed(self, event_id: UUID, *, error: str = "") -> bool:
        """Mark event as FAILED or return to PENDING for retry.

        If retry_count < max_retries, returns to PENDING.
        Otherwise marks as FAILED permanently.

        Returns False if event not found or not in PROCESSING state.
        """
        event = self._events.get(event_id)
        if not event or event.status != EventStatus.PROCESSING:
            return False

        event.retry_count += 1
        event.error_message = error

        if event.retry_count >= event.max_retries:
            event.status = EventStatus.FAILED
            event.processed_at = datetime.now(UTC)
        else:
            event.status = EventStatus.PENDING

        return True

    def count_by_status(self) -> dict[EventStatus, int]:
        """Return event count grouped by status."""
        counts: dict[EventStatus, int] = dict.fromkeys(EventStatus, 0)
        for event in self._events.values():
            counts[event.status] += 1
        return counts
