"""Negative feedback fuse -- suppress memories after repeated user negation.

Task card: B3-4
- 3 consecutive negative feedback events -> confidence drops to 0
- Fused memory no longer injected into context
- Threshold configurable

Architecture: docs/architecture/01-Brain Section 2.3 (Memory Quality)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class FeedbackRecord:
    """Tracks negative feedback count for a memory item."""

    memory_id: UUID
    negative_count: int = 0
    fused: bool = False


@dataclass(frozen=True)
class FuseResult:
    """Result of processing a feedback event."""

    memory_id: UUID
    negative_count: int
    fused: bool
    confidence: float


class NegativeFeedbackFuse:
    """Track negative feedback and suppress memories that fail repeatedly.

    When a user negates a memory N times (default 3), the memory's effective
    confidence drops to 0.0 and it is excluded from context assembly.

    Thread-safe for single-process operation. For multi-process,
    use external store (PG-backed in Phase 4).
    """

    def __init__(self, *, threshold: int = 3) -> None:
        self._threshold = threshold
        self._records: dict[UUID, FeedbackRecord] = {}

    def record_negative(self, memory_id: UUID) -> FuseResult:
        """Record a negative feedback event for a memory.

        Args:
            memory_id: The memory that was negated.

        Returns:
            FuseResult with updated state.
        """
        record = self._records.get(memory_id)
        if record is None:
            record = FeedbackRecord(memory_id=memory_id)
            self._records[memory_id] = record

        record.negative_count += 1

        if record.negative_count >= self._threshold and not record.fused:
            record.fused = True
            logger.info(
                "Memory %s fused after %d negative feedbacks",
                memory_id,
                record.negative_count,
            )

        confidence = 0.0 if record.fused else max(0.0, 1.0 - record.negative_count * 0.2)

        return FuseResult(
            memory_id=memory_id,
            negative_count=record.negative_count,
            fused=record.fused,
            confidence=confidence,
        )

    def is_fused(self, memory_id: UUID) -> bool:
        """Check if a memory is fused (should not be injected).

        Args:
            memory_id: Memory to check.

        Returns:
            True if the memory has been fused.
        """
        record = self._records.get(memory_id)
        return record is not None and record.fused

    def get_effective_confidence(
        self,
        memory_id: UUID,
        original_confidence: float,
    ) -> float:
        """Get the effective confidence for a memory, accounting for fuse state.

        Args:
            memory_id: Memory to check.
            original_confidence: The memory's original confidence score.

        Returns:
            0.0 if fused, otherwise original_confidence.
        """
        if self.is_fused(memory_id):
            return 0.0
        return original_confidence

    def reset(self, memory_id: UUID) -> None:
        """Reset feedback tracking for a memory (e.g., after memory update).

        Args:
            memory_id: Memory to reset.
        """
        self._records.pop(memory_id, None)

    @property
    def fused_memories(self) -> frozenset[UUID]:
        """Return set of all fused memory IDs."""
        return frozenset(record.memory_id for record in self._records.values() if record.fused)
