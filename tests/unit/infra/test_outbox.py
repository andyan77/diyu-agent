"""Tests for I1-6: event_outbox pattern (at-least-once delivery).

Acceptance: pytest tests/unit/infra/test_outbox.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.infra.events.outbox import EventOutbox, EventStatus, OutboxEvent


@pytest.fixture()
def outbox():
    return EventOutbox()


@pytest.fixture()
def org_id():
    return uuid4()


class TestEventOutboxAppend:
    """EventOutbox.append creates events correctly."""

    def test_append_returns_event(self, outbox, org_id):
        event = outbox.append(
            org_id=org_id,
            event_type="user.created",
            payload={"email": "test@example.com"},
        )
        assert isinstance(event, OutboxEvent)
        assert event.org_id == org_id
        assert event.event_type == "user.created"
        assert event.status == EventStatus.PENDING

    def test_append_assigns_unique_ids(self, outbox, org_id):
        e1 = outbox.append(org_id=org_id, event_type="a", payload={})
        e2 = outbox.append(org_id=org_id, event_type="b", payload={})
        assert e1.id != e2.id

    def test_append_preserves_payload(self, outbox, org_id):
        payload = {"key": "value", "nested": {"a": 1}}
        event = outbox.append(org_id=org_id, event_type="test", payload=payload)
        assert event.payload == payload


class TestEventOutboxGetPending:
    """EventOutbox.get_pending returns pending events in order."""

    def test_empty_outbox_returns_empty(self, outbox):
        assert outbox.get_pending() == []

    def test_returns_pending_events(self, outbox, org_id):
        outbox.append(org_id=org_id, event_type="a", payload={})
        outbox.append(org_id=org_id, event_type="b", payload={})
        pending = outbox.get_pending()
        assert len(pending) == 2
        assert pending[0].event_type == "a"
        assert pending[1].event_type == "b"

    def test_respects_limit(self, outbox, org_id):
        for i in range(10):
            outbox.append(org_id=org_id, event_type=f"e{i}", payload={})
        assert len(outbox.get_pending(limit=3)) == 3


class TestEventOutboxLifecycle:
    """Full lifecycle: PENDING -> PROCESSING -> DELIVERED."""

    def test_happy_path(self, outbox, org_id):
        event = outbox.append(org_id=org_id, event_type="test", payload={})
        assert event.status == EventStatus.PENDING

        assert outbox.mark_processing(event.id) is True
        assert event.status == EventStatus.PROCESSING

        assert outbox.mark_delivered(event.id) is True
        assert event.status == EventStatus.DELIVERED
        assert event.processed_at is not None

    def test_delivered_event_not_in_pending(self, outbox, org_id):
        event = outbox.append(org_id=org_id, event_type="test", payload={})
        outbox.mark_processing(event.id)
        outbox.mark_delivered(event.id)
        assert outbox.get_pending() == []


class TestEventOutboxRetry:
    """Failed events retry up to max_retries then permanently fail."""

    def test_retry_returns_to_pending(self, outbox, org_id):
        event = outbox.append(org_id=org_id, event_type="test", payload={}, max_retries=3)
        outbox.mark_processing(event.id)
        outbox.mark_failed(event.id, error="timeout")

        assert event.status == EventStatus.PENDING
        assert event.retry_count == 1
        assert event.error_message == "timeout"

    def test_exceeds_max_retries_becomes_failed(self, outbox, org_id):
        event = outbox.append(org_id=org_id, event_type="test", payload={}, max_retries=2)
        # Attempt 1
        outbox.mark_processing(event.id)
        outbox.mark_failed(event.id, error="err1")
        assert event.status == EventStatus.PENDING

        # Attempt 2 (reaches max)
        outbox.mark_processing(event.id)
        outbox.mark_failed(event.id, error="err2")
        assert event.status == EventStatus.FAILED
        assert event.retry_count == 2


class TestEventOutboxStateGuards:
    """Invalid state transitions are rejected."""

    def test_cannot_process_nonexistent_event(self, outbox):
        assert outbox.mark_processing(uuid4()) is False

    def test_cannot_deliver_pending_event(self, outbox, org_id):
        event = outbox.append(org_id=org_id, event_type="test", payload={})
        assert outbox.mark_delivered(event.id) is False

    def test_cannot_fail_pending_event(self, outbox, org_id):
        event = outbox.append(org_id=org_id, event_type="test", payload={})
        assert outbox.mark_failed(event.id) is False

    def test_cannot_process_delivered_event(self, outbox, org_id):
        event = outbox.append(org_id=org_id, event_type="test", payload={})
        outbox.mark_processing(event.id)
        outbox.mark_delivered(event.id)
        assert outbox.mark_processing(event.id) is False


class TestEventOutboxCountByStatus:
    """count_by_status returns correct aggregation."""

    def test_all_statuses_present(self, outbox, org_id):
        outbox.append(org_id=org_id, event_type="a", payload={})
        counts = outbox.count_by_status()
        assert counts[EventStatus.PENDING] == 1
        assert counts[EventStatus.DELIVERED] == 0

    def test_mixed_statuses(self, outbox, org_id):
        e1 = outbox.append(org_id=org_id, event_type="a", payload={})
        outbox.append(org_id=org_id, event_type="b", payload={})
        outbox.mark_processing(e1.id)
        outbox.mark_delivered(e1.id)

        counts = outbox.count_by_status()
        assert counts[EventStatus.DELIVERED] == 1
        assert counts[EventStatus.PENDING] == 1
