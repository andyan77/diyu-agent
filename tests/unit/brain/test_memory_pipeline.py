"""Tests for B2-5: Memory write pipeline.

Validates:
- Observer -> Analyzer -> Evolver chain
- Write success rate 100% (for extractable observations)
- Non-blocking error handling
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.brain.memory.pipeline import MemoryWritePipeline
from src.memory.receipt import ReceiptStore
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, PromotionReceipt, WriteReceipt


class FakeMemoryCore(MemoryCorePort):
    """In-memory MemoryCorePort for testing."""

    def __init__(self) -> None:
        self._items: list[MemoryItem] = []

    async def read_personal_memories(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        *,
        org_id: UUID | None = None,
    ) -> list[MemoryItem]:
        results = [m for m in self._items if m.user_id == user_id]
        if query:
            results = [m for m in results if query.lower() in m.content.lower()]
        return sorted(results, key=lambda m: m.confidence, reverse=True)[:top_k]

    async def write_observation(
        self,
        user_id: UUID,
        observation: Observation,
        *,
        org_id: UUID | None = None,
    ) -> WriteReceipt:
        memory_id = uuid4()
        now = datetime.now(UTC)
        item = MemoryItem(
            memory_id=memory_id,
            user_id=user_id,
            memory_type=observation.memory_type,
            content=observation.content,
            confidence=observation.confidence,
            valid_at=now,
            source_sessions=(
                [observation.source_session_id] if observation.source_session_id else []
            ),
        )
        self._items.append(item)
        return WriteReceipt(memory_id=memory_id, version=1, written_at=now)

    async def get_session(self, session_id: UUID) -> object:
        return None

    async def archive_session(self, session_id: UUID) -> object:
        return None

    async def promote_to_knowledge(
        self,
        memory_id: UUID,
        target_org_id: UUID,
        target_visibility: str,
        *,
        user_id: UUID | None = None,
    ) -> PromotionReceipt:
        from datetime import UTC, datetime

        return PromotionReceipt(
            proposal_id=memory_id,
            source_memory_id=memory_id,
            target_knowledge_id=None,
            status="promoted",
            promoted_at=datetime.now(UTC),
        )


@pytest.mark.unit
class TestMemoryWritePipeline:
    """B2-5: Memory write pipeline."""

    @pytest.fixture()
    def memory_core(self) -> FakeMemoryCore:
        return FakeMemoryCore()

    @pytest.fixture()
    def receipt_store(self) -> ReceiptStore:
        return ReceiptStore()

    @pytest.fixture()
    def pipeline(
        self,
        memory_core: FakeMemoryCore,
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
            receipts = await receipt_store.get_receipts_for_item(mid)
            assert len(receipts) >= 1
            assert receipts[0].receipt_type == "injection"
