"""Memory injection/retrieval receipts.

Task card: MC2-6
- memory_receipts table records 5-tuple per injection:
  candidate_score, decision_reason, policy_version, guardrail_hit, context_position

Architecture: ADR-038 (Receipt structure for Confidence Calibration feedback)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class MemoryReceipt:
    """Receipt recording a memory injection or retrieval event.

    The 5-tuple provides feedback data for Confidence Calibration
    and experiment engine.
    """

    id: UUID
    memory_item_id: UUID
    org_id: UUID
    receipt_type: str  # "injection" | "retrieval"
    candidate_score: float
    decision_reason: str
    policy_version: str
    guardrail_hit: bool
    context_position: int | None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ReceiptStore:
    """In-memory receipt store for unit testing.

    Production uses memory_receipts table via SQLAlchemy.
    """

    def __init__(self) -> None:
        self._receipts: dict[UUID, MemoryReceipt] = {}
        self._by_memory_item: dict[UUID, list[UUID]] = {}

    def record_injection(
        self,
        *,
        memory_item_id: UUID,
        org_id: UUID,
        candidate_score: float,
        decision_reason: str,
        policy_version: str = "v1",
        guardrail_hit: bool = False,
        context_position: int | None = None,
    ) -> MemoryReceipt:
        """Record an injection receipt (memory written to context)."""
        return self._record(
            memory_item_id=memory_item_id,
            org_id=org_id,
            receipt_type="injection",
            candidate_score=candidate_score,
            decision_reason=decision_reason,
            policy_version=policy_version,
            guardrail_hit=guardrail_hit,
            context_position=context_position,
        )

    def record_retrieval(
        self,
        *,
        memory_item_id: UUID,
        org_id: UUID,
        candidate_score: float,
        decision_reason: str,
        policy_version: str = "v1",
        guardrail_hit: bool = False,
        context_position: int | None = None,
    ) -> MemoryReceipt:
        """Record a retrieval receipt (memory retrieved for ranking)."""
        return self._record(
            memory_item_id=memory_item_id,
            org_id=org_id,
            receipt_type="retrieval",
            candidate_score=candidate_score,
            decision_reason=decision_reason,
            policy_version=policy_version,
            guardrail_hit=guardrail_hit,
            context_position=context_position,
        )

    def get_receipts_for_item(
        self,
        memory_item_id: UUID,
    ) -> list[MemoryReceipt]:
        """Get all receipts for a given memory item."""
        receipt_ids = self._by_memory_item.get(memory_item_id, [])
        return [self._receipts[rid] for rid in receipt_ids if rid in self._receipts]

    def count_by_type(
        self,
        memory_item_id: UUID,
    ) -> dict[str, int]:
        """Count receipts grouped by type for a memory item."""
        receipts = self.get_receipts_for_item(memory_item_id)
        counts: dict[str, int] = {"injection": 0, "retrieval": 0}
        for r in receipts:
            counts[r.receipt_type] = counts.get(r.receipt_type, 0) + 1
        return counts

    def _record(
        self,
        *,
        memory_item_id: UUID,
        org_id: UUID,
        receipt_type: str,
        candidate_score: float,
        decision_reason: str,
        policy_version: str,
        guardrail_hit: bool,
        context_position: int | None,
    ) -> MemoryReceipt:
        receipt = MemoryReceipt(
            id=uuid4(),
            memory_item_id=memory_item_id,
            org_id=org_id,
            receipt_type=receipt_type,
            candidate_score=candidate_score,
            decision_reason=decision_reason,
            policy_version=policy_version,
            guardrail_hit=guardrail_hit,
            context_position=context_position,
        )
        self._receipts[receipt.id] = receipt
        self._by_memory_item.setdefault(memory_item_id, []).append(receipt.id)
        return receipt
