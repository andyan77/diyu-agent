"""Unit tests for injection/retrieval receipts (MC2-6).

Tests 5-tuple completeness for each receipt.
Complies with no-mock policy.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.memory.receipt import MemoryReceipt, ReceiptStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store() -> ReceiptStore:
    return ReceiptStore()


@pytest.fixture()
def org_id():
    return uuid4()


@pytest.fixture()
def memory_item_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReceiptStore:
    """MC2-6: injection/retrieval receipts with 5-tuple."""

    async def test_record_injection_receipt(
        self,
        store: ReceiptStore,
        org_id,
        memory_item_id,
    ) -> None:
        receipt = await store.record_injection(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.85,
            decision_reason="high relevance",
            policy_version="v1",
            guardrail_hit=False,
            context_position=3,
        )
        assert isinstance(receipt, MemoryReceipt)
        assert receipt.receipt_type == "injection"
        assert receipt.candidate_score == 0.85
        assert receipt.decision_reason == "high relevance"
        assert receipt.policy_version == "v1"
        assert receipt.guardrail_hit is False
        assert receipt.context_position == 3

    async def test_record_retrieval_receipt(
        self,
        store: ReceiptStore,
        org_id,
        memory_item_id,
    ) -> None:
        receipt = await store.record_retrieval(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.72,
            decision_reason="moderate match",
        )
        assert receipt.receipt_type == "retrieval"

    async def test_five_tuple_completeness(
        self,
        store: ReceiptStore,
        org_id,
        memory_item_id,
    ) -> None:
        """Every receipt must have all 5 tuple fields."""
        receipt = await store.record_injection(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.9,
            decision_reason="exact match",
            policy_version="v2",
            guardrail_hit=True,
            context_position=1,
        )
        assert receipt.candidate_score is not None
        assert receipt.decision_reason is not None
        assert receipt.policy_version is not None
        assert receipt.guardrail_hit is not None
        assert receipt.context_position is not None

    async def test_get_receipts_for_item(
        self,
        store: ReceiptStore,
        org_id,
        memory_item_id,
    ) -> None:
        await store.record_injection(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.8,
            decision_reason="r1",
        )
        await store.record_retrieval(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.7,
            decision_reason="r2",
        )
        receipts = await store.get_receipts_for_item(memory_item_id)
        assert len(receipts) == 2

    async def test_get_receipts_empty(self, store: ReceiptStore) -> None:
        assert await store.get_receipts_for_item(uuid4()) == []

    async def test_count_by_type(
        self,
        store: ReceiptStore,
        org_id,
        memory_item_id,
    ) -> None:
        await store.record_injection(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.8,
            decision_reason="r1",
        )
        await store.record_injection(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.7,
            decision_reason="r2",
        )
        await store.record_retrieval(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.6,
            decision_reason="r3",
        )
        counts = await store.count_by_type(memory_item_id)
        assert counts["injection"] == 2
        assert counts["retrieval"] == 1

    async def test_guardrail_hit_recorded(
        self,
        store: ReceiptStore,
        org_id,
        memory_item_id,
    ) -> None:
        receipt = await store.record_injection(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.9,
            decision_reason="blocked",
            guardrail_hit=True,
        )
        assert receipt.guardrail_hit is True

    async def test_receipts_isolated_between_items(
        self,
        store: ReceiptStore,
        org_id,
    ) -> None:
        mid1 = uuid4()
        mid2 = uuid4()
        await store.record_injection(
            memory_item_id=mid1,
            org_id=org_id,
            candidate_score=0.8,
            decision_reason="r1",
        )
        await store.record_injection(
            memory_item_id=mid2,
            org_id=org_id,
            candidate_score=0.7,
            decision_reason="r2",
        )
        assert len(await store.get_receipts_for_item(mid1)) == 1
        assert len(await store.get_receipts_for_item(mid2)) == 1
