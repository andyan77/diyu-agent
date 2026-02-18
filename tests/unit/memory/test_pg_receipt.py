"""Unit tests for PgReceiptStore (MC2-6 PG backend).

Tests PgReceiptStore using Fake adapters.
Verifies: record_injection, record_retrieval, get_receipts_for_item, count_by_type.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.memory.receipt import MemoryReceipt
from tests.fakes import FakeAsyncSession, FakeOrmRow, FakeSessionFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orm_receipt(
    *,
    memory_item_id=None,
    org_id=None,
    receipt_type="injection",
    candidate_score=0.85,
    decision_reason="high relevance",
    policy_version="v1",
    guardrail_hit=False,
    context_position=None,
):
    """Create a FakeOrmRow simulating a MemoryReceiptModel row."""
    return FakeOrmRow(
        id=uuid4(),
        memory_item_id=memory_item_id or uuid4(),
        org_id=org_id or uuid4(),
        receipt_type=receipt_type,
        candidate_score=candidate_score,
        decision_reason=decision_reason,
        policy_version=policy_version,
        guardrail_hit=guardrail_hit,
        context_position=context_position,
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
class TestPgReceiptStore:
    """MC2-6: PG-backed receipt store."""

    async def test_record_injection_adds_and_commits(
        self,
        org_id,
        memory_item_id,
    ) -> None:
        from src.memory.receipt import PgReceiptStore

        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)
        store = PgReceiptStore(session_factory=factory)

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
        assert receipt.memory_item_id == memory_item_id
        assert receipt.org_id == org_id
        assert len(session.added) == 1
        assert session.commit_count == 1

    async def test_record_retrieval_adds_and_commits(
        self,
        org_id,
        memory_item_id,
    ) -> None:
        from src.memory.receipt import PgReceiptStore

        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)
        store = PgReceiptStore(session_factory=factory)

        receipt = await store.record_retrieval(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.72,
            decision_reason="moderate match",
        )

        assert isinstance(receipt, MemoryReceipt)
        assert receipt.receipt_type == "retrieval"
        assert receipt.memory_item_id == memory_item_id
        assert receipt.org_id == org_id
        assert len(session.added) == 1
        assert session.commit_count == 1

    async def test_get_receipts_for_item_returns_list(
        self,
        org_id,
        memory_item_id,
    ) -> None:
        from src.memory.receipt import PgReceiptStore

        rows = [
            _make_orm_receipt(
                memory_item_id=memory_item_id,
                org_id=org_id,
                receipt_type=rt,
            )
            for rt in ("injection", "retrieval", "injection")
        ]
        session = FakeAsyncSession()
        session.set_scalars_result(rows)
        factory = FakeSessionFactory(session)
        store = PgReceiptStore(session_factory=factory)

        receipts = await store.get_receipts_for_item(memory_item_id)

        assert len(receipts) == 3
        for r in receipts:
            assert isinstance(r, MemoryReceipt)

    async def test_get_receipts_for_item_empty_returns_empty_list(self) -> None:
        from src.memory.receipt import PgReceiptStore

        session = FakeAsyncSession()
        session.set_scalars_result([])
        factory = FakeSessionFactory(session)
        store = PgReceiptStore(session_factory=factory)

        receipts = await store.get_receipts_for_item(uuid4())
        assert receipts == []

    async def test_count_by_type_returns_int_dict(
        self,
        org_id,
        memory_item_id,
    ) -> None:
        from src.memory.receipt import PgReceiptStore

        rows = [
            _make_orm_receipt(
                memory_item_id=memory_item_id,
                org_id=org_id,
                receipt_type="injection",
            ),
            _make_orm_receipt(
                memory_item_id=memory_item_id,
                org_id=org_id,
                receipt_type="injection",
            ),
            _make_orm_receipt(
                memory_item_id=memory_item_id,
                org_id=org_id,
                receipt_type="retrieval",
            ),
        ]
        session = FakeAsyncSession()
        session.set_scalars_result(rows)
        factory = FakeSessionFactory(session)
        store = PgReceiptStore(session_factory=factory)

        counts = await store.count_by_type(memory_item_id)

        assert isinstance(counts, dict)
        assert counts["injection"] == 2
        assert counts["retrieval"] == 1
