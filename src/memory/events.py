"""Conversation events CRUD operations.

Task card: MC2-2
- Write conversation event -> query by session_id -> return time-ordered list
- Events are append-mostly, ordered by sequence_number within session

Architecture: Section 2.1 (conversation_events table)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class ConversationEvent:
    """A single event in a conversation session."""

    id: UUID
    org_id: UUID
    session_id: UUID
    user_id: UUID | None
    event_type: str
    role: str
    content: dict[str, Any]
    sequence_number: int
    content_schema_version: str = "v3.6"
    parent_event_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ConversationEventStore:
    """In-memory conversation event store for unit testing.

    Production implementation will use SQLAlchemy + conversation_events table.
    """

    def __init__(self) -> None:
        self._events: dict[UUID, ConversationEvent] = {}
        self._session_index: dict[UUID, list[UUID]] = {}
        self._sequence_counters: dict[UUID, int] = {}

    def append_event(
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
    ) -> ConversationEvent:
        """Append a new event to a conversation session.

        Sequence numbers are auto-incremented per session.
        """
        seq = self._sequence_counters.get(session_id, 0) + 1
        self._sequence_counters[session_id] = seq

        event = ConversationEvent(
            id=uuid4(),
            org_id=org_id,
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            role=role,
            content=content or {},
            sequence_number=seq,
            parent_event_id=parent_event_id,
            metadata=metadata or {},
        )

        self._events[event.id] = event
        self._session_index.setdefault(session_id, []).append(event.id)
        return event

    def get_session_events(
        self,
        session_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[ConversationEvent]:
        """Get events for a session, ordered by sequence_number."""
        event_ids = self._session_index.get(session_id, [])
        events = [self._events[eid] for eid in event_ids if eid in self._events]
        events.sort(key=lambda e: e.sequence_number)
        if limit is not None:
            events = events[:limit]
        return events

    def get_event(self, event_id: UUID) -> ConversationEvent | None:
        """Get a single event by ID."""
        return self._events.get(event_id)

    def count_session_events(self, session_id: UUID) -> int:
        """Count events in a session."""
        return len(self._session_index.get(session_id, []))

    def delete_session(self, session_id: UUID) -> int:
        """Delete all events for a session. Returns count deleted."""
        event_ids = self._session_index.pop(session_id, [])
        count = 0
        for eid in event_ids:
            if eid in self._events:
                del self._events[eid]
                count += 1
        self._sequence_counters.pop(session_id, None)
        return count
