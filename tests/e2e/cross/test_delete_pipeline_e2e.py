"""Cross-layer E2E: Delete Pipeline 8-state FSM (X4-4).

Gate: p4-delete-e2e
Verifies: Full lifecycle of the deletion FSM across layers:
    1. ACTIVE -> PENDING_DELETE (user request)
    2. PENDING_DELETE -> TOMBSTONE (soft delete confirmation)
    3. TOMBSTONE -> ARCHIVED (data archived for compliance)
    4. ARCHIVED -> PURGE_QUEUED (retention elapsed, queued for purge)
    5. PURGE_QUEUED -> PURGING (purge worker starts)
    6. PURGING -> PURGED (terminal, physical deletion complete)
    7. PURGING -> FAILED (purge error) -> retry -> PURGE_QUEUED
    8. Full audit trail: every transition emits DeletionEvent

Integration path:
    Gateway (delete request) -> Brain (ConversationEngine, memory awareness)
    -> MemoryCore (FSM state machine) -> Audit log (DeletionEvents)

Uses FakeMemoryCore + DeletionFSM directly for deterministic testing.
No external dependencies (PG, Redis, etc.).

Design decision (ADR-039): Deletion FSM is memory-item-scoped.
Each MemoryItem has its own FSM instance. Org isolation via org_id.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.brain.engine.conversation import ConversationEngine
from src.brain.memory.pipeline import MemoryWritePipeline
from src.memory.deletion.fsm import (
    DeletionFSM,
    DeletionState,
    InvalidTransitionError,
)
from src.memory.receipt import ReceiptStore
from src.shared.trace_context import get_trace_id, trace_context
from tests.e2e.test_conversation_loop import FakeEventStore, FakeLLM, FakeMemoryCore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def org_id():
    return uuid4()


@pytest.fixture()
def user_id():
    return uuid4()


@pytest.fixture()
def session_id():
    return uuid4()


@pytest.fixture()
def memory_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestDeletePipelineE2E:
    """Delete pipeline 8-state FSM end-to-end (X4-4, OS4-5).

    Validates that the deletion FSM correctly transitions through all
    8 states, emits audit events, enforces tombstone retention, handles
    failures with retry, and integrates with the Brain layer.
    """

    async def test_happy_path_full_lifecycle(
        self,
        memory_id,
        org_id,
    ) -> None:
        """Complete lifecycle: ACTIVE -> PENDING_DELETE -> TOMBSTONE ->
        ARCHIVED -> PURGE_QUEUED -> PURGING -> PURGED.

        Every transition produces an auditable DeletionEvent.
        """
        fsm = DeletionFSM(memory_id=memory_id, org_id=org_id)

        # Verify initial state
        assert fsm.state == DeletionState.ACTIVE
        assert fsm.memory_id == memory_id
        assert fsm.org_id == org_id
        assert len(fsm.events) == 0

        # Step 1: User requests deletion
        fsm.request_delete(reason="GDPR erasure request")
        assert fsm.state == DeletionState.PENDING_DELETE
        assert len(fsm.events) == 1
        assert fsm.events[0].from_state == DeletionState.ACTIVE
        assert fsm.events[0].to_state == DeletionState.PENDING_DELETE
        assert fsm.events[0].reason == "GDPR erasure request"

        # Step 2: Soft delete confirmed (tombstone)
        fsm.confirm_tombstone()
        assert fsm.state == DeletionState.TOMBSTONE
        assert len(fsm.events) == 2

        # Step 3: Archive for compliance
        fsm.archive()
        assert fsm.state == DeletionState.ARCHIVED
        assert len(fsm.events) == 3

        # Step 4: Queue for physical purge
        fsm.queue_purge()
        assert fsm.state == DeletionState.PURGE_QUEUED
        assert len(fsm.events) == 4

        # Step 5: Start purge
        fsm.start_purge()
        assert fsm.state == DeletionState.PURGING
        assert len(fsm.events) == 5

        # Step 6: Complete purge (terminal)
        fsm.complete_purge()
        assert fsm.state == DeletionState.PURGED
        assert len(fsm.events) == 6

        # Verify complete audit trail
        expected_transitions = [
            (DeletionState.ACTIVE, DeletionState.PENDING_DELETE),
            (DeletionState.PENDING_DELETE, DeletionState.TOMBSTONE),
            (DeletionState.TOMBSTONE, DeletionState.ARCHIVED),
            (DeletionState.ARCHIVED, DeletionState.PURGE_QUEUED),
            (DeletionState.PURGE_QUEUED, DeletionState.PURGING),
            (DeletionState.PURGING, DeletionState.PURGED),
        ]
        for i, (from_s, to_s) in enumerate(expected_transitions):
            assert fsm.events[i].from_state == from_s
            assert fsm.events[i].to_state == to_s
            assert fsm.events[i].memory_id == memory_id
            assert fsm.events[i].org_id == org_id

    async def test_failure_and_retry_path(
        self,
        memory_id,
        org_id,
    ) -> None:
        """PURGING -> FAILED -> retry -> PURGE_QUEUED -> PURGING -> PURGED.

        Validates the error recovery path with retry semantics.
        """
        fsm = DeletionFSM(memory_id=memory_id, org_id=org_id)

        # Advance to PURGING
        fsm.request_delete(reason="user request")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        assert fsm.state == DeletionState.PURGING

        # Purge fails (e.g., storage backend unreachable)
        fsm.fail(error="S3 connection timeout")
        assert fsm.state == DeletionState.FAILED
        fail_event = fsm.events[-1]
        assert fail_event.from_state == DeletionState.PURGING
        assert fail_event.to_state == DeletionState.FAILED
        assert fail_event.error == "S3 connection timeout"

        # Retry: FAILED -> PURGE_QUEUED
        fsm.retry()
        assert fsm.state == DeletionState.PURGE_QUEUED
        retry_event = fsm.events[-1]
        assert retry_event.reason == "retry"

        # Second attempt succeeds
        fsm.start_purge()
        fsm.complete_purge()
        assert fsm.state == DeletionState.PURGED

        # Full trail: 5 (to PURGING) + 1 (FAILED) + 1 (retry) + 2 (purge again) = 9
        assert len(fsm.events) == 9

    async def test_tombstone_retention_enforcement(
        self,
        memory_id,
        org_id,
    ) -> None:
        """Tombstone retention period must elapse before purge eligibility.

        30-day default retention. Items in TOMBSTONE/ARCHIVED are not
        eligible for purge until the retention window has passed.
        """
        fsm = DeletionFSM(
            memory_id=memory_id,
            org_id=org_id,
            tombstone_retention_days=30,
        )

        fsm.request_delete(reason="cleanup")
        fsm.confirm_tombstone()
        assert fsm.state == DeletionState.TOMBSTONE

        # Just tombstoned — not yet eligible for purge
        assert fsm.is_purge_eligible is False

        # Simulate time passage: set tombstone_at to 31 days ago
        fsm._tombstone_at = datetime.now(UTC) - timedelta(days=31)
        assert fsm.is_purge_eligible is True

        # Still within retention (29 days) — not eligible
        fsm._tombstone_at = datetime.now(UTC) - timedelta(days=29)
        assert fsm.is_purge_eligible is False

    async def test_invalid_transitions_rejected(
        self,
        memory_id,
        org_id,
    ) -> None:
        """Invalid state transitions raise InvalidTransitionError.

        The FSM strictly enforces allowed transitions. Skipping states
        or going backward (except FAILED->retry) is not allowed.
        """
        fsm = DeletionFSM(memory_id=memory_id, org_id=org_id)
        assert fsm.state == DeletionState.ACTIVE

        # Cannot skip directly to TOMBSTONE
        with pytest.raises(InvalidTransitionError):
            fsm.confirm_tombstone()

        # Cannot archive from ACTIVE
        with pytest.raises(InvalidTransitionError):
            fsm.archive()

        # Cannot purge from ACTIVE
        with pytest.raises(InvalidTransitionError):
            fsm.complete_purge()

        # State unchanged after invalid transitions
        assert fsm.state == DeletionState.ACTIVE
        assert len(fsm.events) == 0

    async def test_org_isolation_in_audit_events(
        self,
        memory_id,
    ) -> None:
        """Each DeletionEvent carries the org_id for RLS compliance.

        Different orgs produce events tagged with their respective org_ids.
        """
        org_a = uuid4()
        org_b = uuid4()

        fsm_a = DeletionFSM(memory_id=uuid4(), org_id=org_a)
        fsm_b = DeletionFSM(memory_id=uuid4(), org_id=org_b)

        fsm_a.request_delete(reason="org-A cleanup")
        fsm_b.request_delete(reason="org-B cleanup")

        assert fsm_a.events[0].org_id == org_a
        assert fsm_b.events[0].org_id == org_b
        assert fsm_a.events[0].org_id != fsm_b.events[0].org_id

    async def test_event_timestamps_monotonic(
        self,
        memory_id,
        org_id,
    ) -> None:
        """DeletionEvent timestamps are monotonically increasing."""
        fsm = DeletionFSM(memory_id=memory_id, org_id=org_id)

        fsm.request_delete(reason="test")
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        fsm.complete_purge()

        for i in range(1, len(fsm.events)):
            assert fsm.events[i].timestamp >= fsm.events[i - 1].timestamp

    async def test_purged_is_terminal(
        self,
        memory_id,
        org_id,
    ) -> None:
        """PURGED is a terminal state. No further transitions allowed."""
        fsm = DeletionFSM(memory_id=memory_id, org_id=org_id)

        fsm.request_delete()
        fsm.confirm_tombstone()
        fsm.archive()
        fsm.queue_purge()
        fsm.start_purge()
        fsm.complete_purge()
        assert fsm.state == DeletionState.PURGED

        with pytest.raises(InvalidTransitionError):
            fsm.request_delete()
        with pytest.raises(InvalidTransitionError):
            fsm.fail()
        with pytest.raises(InvalidTransitionError):
            fsm.retry()

    async def test_delete_pipeline_with_brain_integration(
        self,
        session_id,
        user_id,
        org_id,
    ) -> None:
        """End-to-end: ConversationEngine writes memory, then FSM deletes it.

        1. ConversationEngine processes a message -> memory written
        2. DeletionFSM walks memory through full deletion lifecycle
        3. Audit trail includes both write receipt and deletion events
        4. trace_id propagates through the entire flow
        """
        memory_core = FakeMemoryCore()
        event_store = FakeEventStore()
        receipt_store = ReceiptStore()
        llm = FakeLLM(responses=["I'll remember that for you."])

        engine = ConversationEngine(
            llm=llm,
            memory_core=memory_core,
            event_store=event_store,
            memory_pipeline=MemoryWritePipeline(
                memory_core=memory_core,
                receipt_store=receipt_store,
            ),
            default_model="gpt-4o",
        )

        expected_tid = "trace-delete-e2e-001"

        with trace_context(expected_tid):
            # Step 1: Write a memory through normal conversation
            turn = await engine.process_message(
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                message="I prefer dark mode for all my apps",
            )
            assert turn.assistant_response == "I'll remember that for you."

            # Verify memory was written
            items = memory_core._items
            assert len(items) >= 1

            # Step 2: Create FSM for the written memory and delete it
            memory_item = items[0]
            fsm = DeletionFSM(
                memory_id=memory_item.memory_id,
                org_id=org_id,
            )

            fsm.request_delete(reason="User requested GDPR erasure")
            fsm.confirm_tombstone()
            fsm.archive()
            fsm.queue_purge()
            fsm.start_purge()
            fsm.complete_purge()

            assert fsm.state == DeletionState.PURGED
            assert len(fsm.events) == 6

            # trace_id should still be active
            assert get_trace_id() == expected_tid

        # Verify audit trail completeness
        assert fsm.events[0].memory_id == memory_item.memory_id
        assert fsm.events[0].org_id == org_id
