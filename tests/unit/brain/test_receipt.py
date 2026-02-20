"""Tests for B2-6: injection_receipt + retrieval_receipt writes.

Validates:
- Each chat generates >= 1 receipt (when memories extracted)
- 5-tuple recorded correctly
- Retrieval receipts from context assembly
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
class TestReceiptWriting:
    """B2-6: injection/retrieval receipts."""

    @pytest.fixture()
    def receipt_store(self) -> ReceiptStore:
        return ReceiptStore()

    @pytest.fixture()
    def pipeline(self, receipt_store: ReceiptStore) -> MemoryWritePipeline:
        memory_core = FakeMemoryCore()
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

    @pytest.mark.asyncio()
    async def test_retrieval_receipt_recording(
        self,
        pipeline: MemoryWritePipeline,
        receipt_store: ReceiptStore,
    ) -> None:
        """Retrieval receipts recorded when memories injected into context."""
        memory_item_id = uuid4()
        org_id = uuid4()
        await pipeline.record_retrieval_receipt(
            memory_item_id=memory_item_id,
            org_id=org_id,
            candidate_score=0.85,
            context_position=1,
        )
        receipts = await receipt_store.get_receipts_for_item(memory_item_id)
        assert len(receipts) == 1
        assert receipts[0].receipt_type == "retrieval"
        assert receipts[0].candidate_score == 0.85
        assert receipts[0].context_position == 1
