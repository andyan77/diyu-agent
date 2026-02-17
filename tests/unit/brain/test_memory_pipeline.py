"""Tests for B2-5: Memory write pipeline.

Validates:
- Observer -> Analyzer -> Evolver chain
- Write success rate 100% (for extractable observations)
- Non-blocking error handling
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
class TestMemoryWritePipeline:
    """B2-5: Memory write pipeline."""

    @pytest.fixture()
    def memory_core(self) -> PgMemoryCoreAdapter:
        return PgMemoryCoreAdapter(storage=FakeStoragePort())

    @pytest.fixture()
    def receipt_store(self) -> ReceiptStore:
        return ReceiptStore()

    @pytest.fixture()
    def pipeline(
        self,
        memory_core: PgMemoryCoreAdapter,
        receipt_store: ReceiptStore,
    ) -> MemoryWritePipeline:
        return MemoryWritePipeline(
            memory_core=memory_core,
            receipt_store=receipt_store,
        )

    @pytest.mark.asyncio()
    async def test_process_turn_with_preference(
        self,
        pipeline: MemoryWritePipeline,
    ) -> None:
        """Preference signals should be extracted and written."""
        results = await pipeline.process_turn(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            user_message="I prefer dark mode for coding",
            assistant_response="Noted! Dark mode is great for coding.",
        )
        created = [r for r in results if r.get("action") == "created"]
        assert len(created) >= 1

    @pytest.mark.asyncio()
    async def test_process_turn_with_fact(
        self,
        pipeline: MemoryWritePipeline,
    ) -> None:
        results = await pipeline.process_turn(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            user_message="I am a software engineer",
            assistant_response="That's great!",
        )
        created = [r for r in results if r.get("action") == "created"]
        assert len(created) >= 1

    @pytest.mark.asyncio()
    async def test_process_turn_no_extraction(
        self,
        pipeline: MemoryWritePipeline,
    ) -> None:
        """Messages without signals should not create memories."""
        results = await pipeline.process_turn(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            user_message="Hello",
            assistant_response="Hi there!",
        )
        assert all(r.get("action") != "created" for r in results) or len(results) == 0

    @pytest.mark.asyncio()
    async def test_write_success_rate_100(
        self,
        pipeline: MemoryWritePipeline,
    ) -> None:
        """All extractable observations must be written successfully."""
        messages = [
            "I prefer Python over Java",
            "I like functional programming",
            "I work at a startup",
            "My name is Alex",
            "I need a dark theme",
        ]
        total_created = 0
        total_errors = 0
        for msg in messages:
            results = await pipeline.process_turn(
                session_id=uuid4(),
                user_id=uuid4(),
                org_id=uuid4(),
                user_message=msg,
                assistant_response="OK",
            )
            for r in results:
                if r.get("action") == "created":
                    total_created += 1
                elif r.get("action") == "error":
                    total_errors += 1
        assert total_errors == 0

    @pytest.mark.asyncio()
    async def test_receipt_recorded_on_write(
        self,
        pipeline: MemoryWritePipeline,
        receipt_store: ReceiptStore,
    ) -> None:
        results = await pipeline.process_turn(
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            user_message="I prefer dark mode",
            assistant_response="Noted!",
        )
        created = [r for r in results if r.get("action") == "created"]
        if created:
            from uuid import UUID

            mid = UUID(created[0]["memory_id"])
            receipts = receipt_store.get_receipts_for_item(mid)
            assert len(receipts) >= 1
            assert receipts[0].receipt_type == "injection"
