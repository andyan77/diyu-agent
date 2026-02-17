"""Unit tests for conversation events CRUD (MC2-2).

Complies with no-mock policy.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.memory.events import ConversationEvent, ConversationEventStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store() -> ConversationEventStore:
    return ConversationEventStore()


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
class TestConversationEventStore:
    """MC2-2: conversation_events CRUD with time-ordering."""

    def test_append_event_returns_event(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        event = store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="user_message",
            role="user",
            content={"text": "hello"},
        )
        assert isinstance(event, ConversationEvent)
        assert event.org_id == org_id
        assert event.session_id == session_id
        assert event.sequence_number == 1

    def test_sequence_auto_increments(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        e1 = store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="user_message",
            role="user",
        )
        e2 = store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="assistant_message",
            role="assistant",
        )
        assert e1.sequence_number == 1
        assert e2.sequence_number == 2

    def test_get_session_events_ordered(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        for i in range(5):
            store.append_event(
                org_id=org_id,
                session_id=session_id,
                event_type="user_message",
                role="user",
                content={"text": f"msg {i}"},
            )
        events = store.get_session_events(session_id)
        assert len(events) == 5
        for i, event in enumerate(events):
            assert event.sequence_number == i + 1

    def test_get_session_events_with_limit(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        for _ in range(10):
            store.append_event(
                org_id=org_id,
                session_id=session_id,
                event_type="user_message",
                role="user",
            )
        events = store.get_session_events(session_id, limit=3)
        assert len(events) == 3

    def test_get_session_events_empty(
        self,
        store: ConversationEventStore,
    ) -> None:
        events = store.get_session_events(uuid4())
        assert events == []

    def test_get_event_by_id(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        event = store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="user_message",
            role="user",
        )
        found = store.get_event(event.id)
        assert found is not None
        assert found.id == event.id

    def test_get_event_nonexistent(
        self,
        store: ConversationEventStore,
    ) -> None:
        assert store.get_event(uuid4()) is None

    def test_count_session_events(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        for _ in range(7):
            store.append_event(
                org_id=org_id,
                session_id=session_id,
                event_type="user_message",
                role="user",
            )
        assert store.count_session_events(session_id) == 7

    def test_delete_session(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        for _ in range(3):
            store.append_event(
                org_id=org_id,
                session_id=session_id,
                event_type="user_message",
                role="user",
            )
        count = store.delete_session(session_id)
        assert count == 3
        assert store.get_session_events(session_id) == []

    def test_separate_sessions_independent(
        self,
        store: ConversationEventStore,
        org_id,
    ) -> None:
        s1 = uuid4()
        s2 = uuid4()
        store.append_event(org_id=org_id, session_id=s1, event_type="msg", role="user")
        store.append_event(org_id=org_id, session_id=s2, event_type="msg", role="user")
        store.append_event(org_id=org_id, session_id=s1, event_type="msg", role="user")

        assert store.count_session_events(s1) == 2
        assert store.count_session_events(s2) == 1

    def test_content_schema_version_default(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        event = store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="user_message",
            role="user",
        )
        assert event.content_schema_version == "v3.6"

    def test_parent_event_id(
        self,
        store: ConversationEventStore,
        org_id,
        session_id,
    ) -> None:
        parent = store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="user_message",
            role="user",
        )
        child = store.append_event(
            org_id=org_id,
            session_id=session_id,
            event_type="tool_call",
            role="tool",
            parent_event_id=parent.id,
        )
        assert child.parent_event_id == parent.id
