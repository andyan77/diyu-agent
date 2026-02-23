"""Deletion pipeline 8-state FSM.

Task card: MC4-1 / ADR-039
States:
  ACTIVE → PENDING_DELETE → TOMBSTONE → ARCHIVED →
  PURGE_QUEUED → PURGING → PURGED
                           ↘ FAILED → (retry) PURGE_QUEUED

- Each transition emits an auditable DeletionEvent
- Tombstone retention: configurable (default 30 days)
- PURGED is terminal; FAILED can retry back to PURGE_QUEUED

Architecture: Section 2.1 (Memory Core Deletion Pipeline)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID  # noqa: TC003 -- used at runtime in dataclass fields


class DeletionState(enum.Enum):
    """8-state deletion lifecycle."""

    ACTIVE = "active"
    PENDING_DELETE = "pending_delete"
    TOMBSTONE = "tombstone"
    ARCHIVED = "archived"
    PURGE_QUEUED = "purge_queued"
    PURGING = "purging"
    PURGED = "purged"
    FAILED = "failed"


# Valid transitions: (from_state, to_state) -> True
_TRANSITIONS: set[tuple[DeletionState, DeletionState]] = {
    (DeletionState.ACTIVE, DeletionState.PENDING_DELETE),
    (DeletionState.PENDING_DELETE, DeletionState.TOMBSTONE),
    (DeletionState.TOMBSTONE, DeletionState.ARCHIVED),
    (DeletionState.ARCHIVED, DeletionState.PURGE_QUEUED),
    (DeletionState.PURGE_QUEUED, DeletionState.PURGING),
    (DeletionState.PURGING, DeletionState.PURGED),
    (DeletionState.PURGING, DeletionState.FAILED),
    (DeletionState.FAILED, DeletionState.PURGE_QUEUED),
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: DeletionState, to_state: DeletionState) -> None:
        super().__init__(f"Invalid transition: {from_state.value} → {to_state.value}")
        self.from_state = from_state
        self.to_state = to_state


@dataclass(frozen=True)
class DeletionEvent:
    """Auditable event for a state transition."""

    memory_id: UUID
    org_id: UUID
    from_state: DeletionState
    to_state: DeletionState
    timestamp: datetime
    reason: str = ""
    error: str = ""


class DeletionFSM:
    """8-state deletion pipeline FSM.

    Each memory item has its own FSM instance. Transitions are validated
    against the allowed transition set. Every transition emits an event
    for audit purposes.
    """

    def __init__(
        self,
        *,
        memory_id: UUID,
        org_id: UUID,
        initial_state: DeletionState = DeletionState.ACTIVE,
        tombstone_retention_days: int = 30,
    ) -> None:
        self._memory_id = memory_id
        self._org_id = org_id
        self._state = initial_state
        self._tombstone_retention_days = tombstone_retention_days
        self._tombstone_at: datetime | None = None
        self._events: list[DeletionEvent] = []

    @property
    def memory_id(self) -> UUID:
        return self._memory_id

    @property
    def org_id(self) -> UUID:
        return self._org_id

    @property
    def state(self) -> DeletionState:
        return self._state

    @property
    def events(self) -> list[DeletionEvent]:
        return list(self._events)

    @property
    def is_purge_eligible(self) -> bool:
        """True if item is in TOMBSTONE/ARCHIVED and retention period has elapsed."""
        if self._state not in (DeletionState.TOMBSTONE, DeletionState.ARCHIVED):
            return False
        if self._tombstone_at is None:
            return False
        cutoff = datetime.now(UTC) - timedelta(days=self._tombstone_retention_days)
        return self._tombstone_at <= cutoff

    def _transition(
        self,
        to_state: DeletionState,
        *,
        reason: str = "",
        error: str = "",
    ) -> None:
        """Validate and execute a state transition."""
        if (self._state, to_state) not in _TRANSITIONS:
            raise InvalidTransitionError(self._state, to_state)

        event = DeletionEvent(
            memory_id=self._memory_id,
            org_id=self._org_id,
            from_state=self._state,
            to_state=to_state,
            timestamp=datetime.now(UTC),
            reason=reason,
            error=error,
        )
        self._state = to_state
        self._events.append(event)

    def request_delete(self, *, reason: str = "") -> None:
        """ACTIVE → PENDING_DELETE."""
        self._transition(DeletionState.PENDING_DELETE, reason=reason)

    def confirm_tombstone(self) -> None:
        """PENDING_DELETE → TOMBSTONE. Records tombstone timestamp."""
        self._transition(DeletionState.TOMBSTONE)
        self._tombstone_at = datetime.now(UTC)

    def archive(self) -> None:
        """TOMBSTONE → ARCHIVED."""
        self._transition(DeletionState.ARCHIVED)

    def queue_purge(self) -> None:
        """ARCHIVED → PURGE_QUEUED."""
        self._transition(DeletionState.PURGE_QUEUED)

    def start_purge(self) -> None:
        """PURGE_QUEUED → PURGING."""
        self._transition(DeletionState.PURGING)

    def complete_purge(self) -> None:
        """PURGING → PURGED (terminal)."""
        self._transition(DeletionState.PURGED)

    def fail(self, *, error: str = "") -> None:
        """PURGING → FAILED."""
        self._transition(DeletionState.FAILED, error=error)

    def retry(self) -> None:
        """FAILED → PURGE_QUEUED (retry path)."""
        self._transition(DeletionState.PURGE_QUEUED, reason="retry")
