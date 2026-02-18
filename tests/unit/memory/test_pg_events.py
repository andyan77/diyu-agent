"""Unit tests for PG conversation event store (MC2-2).

Tests PgConversationEventStore using Fake adapters (no unittest.mock).
Verifies: append_event, get_session_events, get_event, count, delete.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.memory.events import ConversationEvent
from tests.fakes import FakeAsyncSession, FakeOrmRow, FakeSessionFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orm_event(
    *,
    org_id=None,
    session_id=None,
    user_id=None,
    event_type="user_message",
    role="user",
    sequence_number=1,
) -> FakeOrmRow:
    """Create a FakeOrmRow with all attributes that _row_to_event() reads."""
    return FakeOrmRow(
        id=uuid4(),
        org_id=org_id or uuid4(),
        session_id=session_id or uuid4(),
        user_id=user_id,
        event_type=event_type,
        role=role,
        content={"text": "hello"},
        content_schema_version="v3.6",
        sequence_number=sequence_number,
        parent_event_id=None,
        metadata_={},
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def org_id():
    return uuid4()


@pytest.fixture()
def session_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPgConversationEventStore:
    """MC2-2: PG-backed conversation event store."""

    async def test_append_event_adds_and_commits(
        self,
        org_id,
        session_id,
    ) -> None:
        from src.memory.events import PgConversationEventStore

        session = FakeAsyncSession()
        session.set_execute_result(scalar_value=0)
        store = PgConversationEventStore(session_factory=FakeSessionFactory(session))

        event = await store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="user_message",
            role="user",
            content={"text": "hello"},
        )

        assert isinstance(event, ConversationEvent)
        assert event.org_id == org_id
        assert event.session_id == session_id
        assert event.event_type == "user_message"
        assert len(session.added) == 1
        assert session.commit_count == 1

    async def test_append_event_sets_sequence_number(
        self,
        org_id,
        session_id,
    ) -> None:
        from src.memory.events import PgConversationEventStore

        # Simulate existing count of 3 events
        session = FakeAsyncSession()
        session.set_execute_result(scalar_value=3)
        store = PgConversationEventStore(session_factory=FakeSessionFactory(session))

        event = await store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="user_message",
            role="user",
        )

        assert event.sequence_number == 4

    async def test_get_session_events_returns_ordered_list(
        self,
        org_id,
        session_id,
    ) -> None:
        from src.memory.events import PgConversationEventStore

        rows = [
            _make_orm_event(org_id=org_id, session_id=session_id, sequence_number=i)
            for i in range(1, 4)
        ]
        session = FakeAsyncSession()
        session.set_scalars_result(rows)
        store = PgConversationEventStore(session_factory=FakeSessionFactory(session))

        events = await store.get_session_events(session_id)

        assert len(events) == 3
        for event in events:
            assert isinstance(event, ConversationEvent)

    async def test_get_session_events_empty(self) -> None:
        from src.memory.events import PgConversationEventStore

        session = FakeAsyncSession()
        session.set_scalars_result([])
        store = PgConversationEventStore(session_factory=FakeSessionFactory(session))

        events = await store.get_session_events(uuid4())
        assert events == []

    async def test_get_event_by_id(
        self,
        org_id,
        session_id,
    ) -> None:
        from src.memory.events import PgConversationEventStore

        row = _make_orm_event(org_id=org_id, session_id=session_id)
        session = FakeAsyncSession()
        session.set_execute_result(scalar_one_or_none_value=row)
        store = PgConversationEventStore(session_factory=FakeSessionFactory(session))

        event = await store.get_event(row.id)
        assert event is not None
        assert event.id == row.id

    async def test_get_event_nonexistent(self) -> None:
        from src.memory.events import PgConversationEventStore

        session = FakeAsyncSession()
        session.set_execute_result(scalar_one_or_none_value=None)
        store = PgConversationEventStore(session_factory=FakeSessionFactory(session))

        event = await store.get_event(uuid4())
        assert event is None

    async def test_count_session_events(
        self,
        session_id,
    ) -> None:
        from src.memory.events import PgConversationEventStore

        session = FakeAsyncSession()
        session.set_execute_result(scalar_value=7)
        store = PgConversationEventStore(session_factory=FakeSessionFactory(session))

        count = await store.count_session_events(session_id)
        assert count == 7

    async def test_delete_session(
        self,
        session_id,
    ) -> None:
        from src.memory.events import PgConversationEventStore

        session = FakeAsyncSession()
        session.set_execute_result(rowcount=5)
        store = PgConversationEventStore(session_factory=FakeSessionFactory(session))

        count = await store.delete_session(session_id)
        assert count == 5
        assert session.commit_count == 1
