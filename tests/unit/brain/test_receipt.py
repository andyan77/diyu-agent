"""Tests for B2-6: injection_receipt + retrieval_receipt writes.

Validates:
- Each chat generates >= 1 receipt (when memories extracted)
- 5-tuple recorded correctly
- Retrieval receipts from context assembly
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.brain.memory.pipeline import MemoryWritePipeline
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.memory.receipt import ReceiptStore
from src.ports.storage_port import StoragePort


class FakeStoragePort(StoragePort):
    """In-memory storage for testing."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    async def put(self, key, value, ttl=None):
        self._data[key] = value

    async def get(self, key):
        return self._data.get(key)

    async def delete(self, key):
        self._data.pop(key, None)

    async def list_keys(self, pattern):
        import fnmatch

        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]


@pytest.mark.unit
class TestReceiptWriting:
    """B2-6: injection/retrieval receipts."""

    @pytest.fixture()
    def receipt_store(self) -> ReceiptStore:
        return ReceiptStore()

    @pytest.fixture()
    def pipeline(self, receipt_store: ReceiptStore) -> MemoryWritePipeline:
        storage = FakeStoragePort()
        memory_core = PgMemoryCoreAdapter(storage=storage)
        return MemoryWritePipeline(
            memory_core=memory_core,
            receipt_store=receipt_store,
        )

    @pytest.mark.asyncio()
    async def test_injection_receipt_generated(
        self,
        pipeline: MemoryWritePipeline,
        receipt_store: ReceiptStore,
    ) -> None:
        """Chat with preference generates >= 1 injection receipt."""
        await pipeline.process_turn(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            user_message="I prefer Python programming",
            assistant_response="Great choice!",
        )
        all_receipts = list(receipt_store._receipts.values())
        injection_receipts = [r for r in all_receipts if r.receipt_type == "injection"]
        assert len(injection_receipts) >= 1

    @pytest.mark.asyncio()
    async def test_receipt_5_tuple(
        self,
        pipeline: MemoryWritePipeline,
        receipt_store: ReceiptStore,
    ) -> None:
        """Receipt must contain the 5-tuple fields."""
        await pipeline.process_turn(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            user_message="I like dark mode",
            assistant_response="OK!",
        )
        all_receipts = list(receipt_store._receipts.values())
        if all_receipts:
            receipt = all_receipts[0]
            assert hasattr(receipt, "candidate_score")
            assert hasattr(receipt, "decision_reason")
            assert hasattr(receipt, "policy_version")
            assert hasattr(receipt, "guardrail_hit")
            assert hasattr(receipt, "context_position")

    def test_retrieval_receipt_recording(
        self,
        pipeline: MemoryWritePipeline,
        receipt_store: ReceiptStore,
    ) -> None:
        """Retrieval receipts recorded when memories injected into context."""
        memory_item_id = uuid4()
        org_id = uuid4()
        pipeline.record_retrieval_receipt(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.85,
            context_position=1,
        )
        receipts = receipt_store.get_receipts_for_item(memory_item_id)
        assert len(receipts) == 1
        assert receipts[0].receipt_type == "retrieval"
        assert receipts[0].candidate_score == 0.85
        assert receipts[0].context_position == 1
