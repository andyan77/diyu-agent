"""Tests for MC4-1: Deletion FSM 8-state.

Task card: MC4-1
States: ACTIVE → PENDING_DELETE → TOMBSTONE → ARCHIVED →
        PURGE_QUEUED → PURGING → PURGED | FAILED
- Each transition is auditable (event emitted)
- Invalid transitions raise InvalidTransitionError
- Tombstone retention: 30 days before purge
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.memory.deletion.fsm import (
    DeletionFSM,
    DeletionState,
    InvalidTransitionError,
)


@pytest.fixture
def fsm() -> DeletionFSM:
    return DeletionFSM(
        memory_id=uuid4(),
        org_id=uuid4(),
        tombstone_retention_days=30,
    )


class TestDeletionState:
    """8 states exist and are ordered."""

    def test_all_states_exist(self) -> None:
        states = list(DeletionState)
        assert len(states) == 8
        assert DeletionState.ACTIVE in states
        assert DeletionState.PENDING_DELETE in states
        assert DeletionState.TOMBSTONE in states
        assert DeletionState.ARCHIVED in states
        assert DeletionState.PURGE_QUEUED in states
        assert DeletionState.PURGING in states
        assert DeletionState.PURGED in states
        assert DeletionState.FAILED in states


class TestInitialState:
    """FSM starts in ACTIVE state."""

    def test_initial_state_is_active(self, fsm: DeletionFSM) -> None:
        assert fsm.state == DeletionState.ACTIVE

    def test_has_memory_id(self, fsm: DeletionFSM) -> None:
        assert fsm.memory_id is not None

    def test_events_empty(self, fsm: DeletionFSM) -> None:
        assert fsm.events == []


class TestHappyPath:
    """Full deletion lifecycle: ACTIVE -> ... -> PURGED."""

    def test_request_delete(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        assert fsm.state == DeletionState.PENDING_DELETE

    def test_confirm_tombstone(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        fsm.confirm_tombstone()
        assert fsm.state == DeletionState.TOMBSTONE

    def test_archive(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        fsm.confirm_tombstone()
        fsm.archive()
        assert fsm.state == DeletionState.ARCHIVED

    def test_queue_purge(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        assert fsm.state == DeletionState.PURGE_QUEUED

    def test_start_purge(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        assert fsm.state == DeletionState.PURGING

    def test_complete_purge(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        fsm.complete_purge()
        assert fsm.state == DeletionState.PURGED

    def test_full_lifecycle_events(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        fsm.complete_purge()

        assert len(fsm.events) == 6
        transitions = [(e.from_state, e.to_state) for e in fsm.events]
        assert transitions == [
            (DeletionState.ACTIVE, DeletionState.PENDING_DELETE),
            (DeletionState.PENDING_DELETE, DeletionState.TOMBSTONE),
            (DeletionState.TOMBSTONE, DeletionState.ARCHIVED),
            (DeletionState.ARCHIVED, DeletionState.PURGE_QUEUED),
            (DeletionState.PURGE_QUEUED, DeletionState.PURGING),
            (DeletionState.PURGING, DeletionState.PURGED),
        ]


class TestFailedState:
    """Transition to FAILED from PURGING."""

    def test_fail_from_purging(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        fsm.fail(error="storage timeout")
        assert fsm.state == DeletionState.FAILED

    def test_retry_from_failed(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="user_request")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        fsm.fail(error="timeout")
        fsm.retry()
        assert fsm.state == DeletionState.PURGE_QUEUED


class TestInvalidTransitions:
    """Invalid state transitions raise errors."""

    def test_cannot_tombstone_from_active(self, fsm: DeletionFSM) -> None:
        with pytest.raises(InvalidTransitionError):
            fsm.confirm_tombstone()

    def test_cannot_purge_from_active(self, fsm: DeletionFSM) -> None:
        with pytest.raises(InvalidTransitionError):
            fsm.start_purge()

    def test_cannot_complete_from_tombstone(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="test")
        fsm.confirm_tombstone()
        with pytest.raises(InvalidTransitionError):
            fsm.complete_purge()

    def test_cannot_delete_from_purged(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="test")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        fsm.complete_purge()
        with pytest.raises(InvalidTransitionError):
            fsm.request_delete(reason="again")


class TestAuditEvents:
    """Each transition produces an auditable DeletionEvent."""

    def test_event_has_timestamp(self, fsm: DeletionFSM) -> None:
        before = datetime.now(UTC)
        fsm.request_delete(reason="audit_test")
        after = datetime.now(UTC)

        event = fsm.events[0]
        assert before <= event.timestamp <= after

    def test_event_has_reason(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="gdpr_request")
        event = fsm.events[0]
        assert event.reason == "gdpr_request"

    def test_event_has_memory_id(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="test")
        assert fsm.events[0].memory_id == fsm.memory_id


class TestTombstoneRetention:
    """Tombstone retention period."""

    def test_purge_eligible_after_retention(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="test")
        fsm.confirm_tombstone()
        # Simulate time passing
        fsm._tombstone_at = datetime.now(UTC) - timedelta(days=31)
        assert fsm.is_purge_eligible

    def test_not_eligible_within_retention(self, fsm: DeletionFSM) -> None:
        fsm.request_delete(reason="test")
        fsm.confirm_tombstone()
        assert not fsm.is_purge_eligible

    def test_not_eligible_if_not_tombstone(self, fsm: DeletionFSM) -> None:
        assert not fsm.is_purge_eligible
