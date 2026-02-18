"""Conversation events CRUD operations.

Task card: MC2-2
- Write conversation event -> query by session_id -> return time-ordered list
- Events are append-mostly, ordered by sequence_number within session

Provides:
- ConversationEvent: domain dataclass
- ConversationEventStore: in-memory store (for tests / Day-1)
- PgConversationEventStore: SQLAlchemy async store (production)

Architecture: Section 2.1 (conversation_events table)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import sqlalchemy as sa

from src.infra.models import ConversationEvent as ConversationEventModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


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


class PgConversationEventStore:
    """PostgreSQL-backed conversation event store using SQLAlchemy.

    All methods are async. Uses async_sessionmaker for DB access.
    RLS SET LOCAL is handled externally by src.infra.db.get_db_session.
    """

    def __init__(self, *, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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
    ) -> ConversationEvent:
        """Append a new event to a conversation session.

        Determines next sequence_number by counting existing events.
        """
        async with self._session_factory() as session:
            # Get current max sequence number for this session
            count_stmt = sa.select(sa.func.count()).where(
                ConversationEventModel.session_id == session_id,
            )
            result = await session.execute(count_stmt)
            current_count = result.scalar_one()
            seq = current_count + 1

            event_id = uuid4()
            now = datetime.now(UTC)
            model = ConversationEventModel(
                id=event_id,
                org_id=org_id,
                session_id=session_id,
                user_id=user_id,
                event_type=event_type,
                role=role,
                content=content or {},
                content_schema_version="v3.6",
                sequence_number=seq,
                parent_event_id=parent_event_id,
                metadata_=metadata or {},
                created_at=now,
            )
            session.add(model)
            await session.commit()

        return ConversationEvent(
            id=event_id,
            org_id=org_id,
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            role=role,
            content=content or {},
            sequence_number=seq,
            parent_event_id=parent_event_id,
            metadata=metadata or {},
            created_at=now,
        )

    async def get_session_events(
        self,
        session_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[ConversationEvent]:
        """Get events for a session, ordered by sequence_number."""
        stmt = (
            sa.select(ConversationEventModel)
            .where(ConversationEventModel.session_id == session_id)
            .order_by(ConversationEventModel.sequence_number)
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        async with self._session_factory() as session:
            result = await session.scalars(stmt)
            rows = result.all()

        return [_row_to_event(row) for row in rows]

    async def get_event(self, event_id: UUID) -> ConversationEvent | None:
        """Get a single event by ID."""
        stmt = sa.select(ConversationEventModel).where(
            ConversationEventModel.id == event_id,
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

        if row is None:
            return None
        return _row_to_event(row)

    async def count_session_events(self, session_id: UUID) -> int:
        """Count events in a session."""
        stmt = sa.select(sa.func.count()).where(
            ConversationEventModel.session_id == session_id,
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return result.scalar_one()

    async def delete_session(self, session_id: UUID) -> int:
        """Delete all events for a session. Returns count deleted."""
        stmt = sa.delete(ConversationEventModel).where(
            ConversationEventModel.session_id == session_id,
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
            count: int = result.rowcount  # type: ignore[attr-defined]
            return count


def _row_to_event(row: ConversationEventModel) -> ConversationEvent:
    """Convert an ORM row to domain ConversationEvent."""
    return ConversationEvent(
        id=row.id,
        org_id=row.org_id,
        session_id=row.session_id,
        user_id=row.user_id,
        event_type=row.event_type,
        role=row.role,
        content=row.content,
        sequence_number=row.sequence_number,
        content_schema_version=row.content_schema_version,
        parent_event_id=row.parent_event_id,
        metadata=row.metadata_,
        created_at=row.created_at,
    )
