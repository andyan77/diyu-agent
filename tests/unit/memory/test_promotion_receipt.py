"""MC3-2: Promotion receipt + cross-SSOT consistency tests.

Tests: receipt schema, promotion flow with knowledge writer, status tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.graph.neo4j_adapter import GraphNode
from src.infra.vector.qdrant_adapter import VectorPoint
from src.knowledge.api.write import KnowledgeWriteService
from src.knowledge.registry.entity_type import EntityTypeRegistry
from src.knowledge.sync.fk_registry import FKRegistry
from src.memory.promotion.pipeline import PromotionPipeline
from src.shared.types import MemoryItem, PromotionReceipt

# -- Fake adapters --


@dataclass
class FakeNeo4j:
    _nodes: dict[str, GraphNode] = field(default_factory=dict)

    async def create_node(
        self,
        entity_type: str,
        node_id: UUID,
        properties: dict[str, Any],
        *,
        org_id: UUID | None = None,
    ) -> GraphNode:
        node = GraphNode(
            node_id=node_id,
            entity_type=entity_type,
            properties=properties,
            org_id=org_id,
        )
        self._nodes[str(node_id)] = node
        return node

    async def mark_sync_status(self, node_id: UUID, status: str) -> None:
        pass

    async def delete_node(self, node_id: UUID) -> bool:
        return self._nodes.pop(str(node_id), None) is not None


@dataclass
class FakeQdrant:
    _points: dict[str, VectorPoint] = field(default_factory=dict)

    async def upsert_point(
        self,
        point_id: UUID,
        vector: list[float],
        payload: dict[str, Any] | None = None,
        *,
        graph_node_id: UUID | None = None,
    ) -> VectorPoint:
        pt = VectorPoint(
            point_id=point_id,
            vector=vector,
            payload=payload or {},
            graph_node_id=graph_node_id,
        )
        self._points[str(point_id)] = pt
        return pt

    async def delete_point(self, point_id: UUID) -> bool:
        return self._points.pop(str(point_id), None) is not None


def _make_memory(
    *,
    content: str = "Silk blends work well for formal occasions",
    confidence: float = 0.9,
) -> MemoryItem:
    return MemoryItem(
        memory_id=uuid4(),
        user_id=uuid4(),
        memory_type="preference",
        content=content,
        valid_at=datetime.now(tz=UTC) - timedelta(days=30),
        confidence=confidence,
    )


def _make_writer() -> KnowledgeWriteService:
    neo4j = FakeNeo4j()
    qdrant = FakeQdrant()
    fk = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]
    registry = EntityTypeRegistry()
    return KnowledgeWriteService(fk, registry)


class TestPromotionReceiptSchema:
    def test_receipt_has_required_fields(self) -> None:
        receipt = PromotionReceipt(
            proposal_id=uuid4(),
            source_memory_id=uuid4(),
            target_knowledge_id=None,
            status="promoted",
        )
        assert receipt.proposal_id is not None
        assert receipt.source_memory_id is not None
        assert receipt.status == "promoted"

    def test_receipt_rejection_reason(self) -> None:
        receipt = PromotionReceipt(
            proposal_id=uuid4(),
            source_memory_id=uuid4(),
            target_knowledge_id=None,
            status="sanitize_failed",
            rejection_reason="PII detected: email_detected",
        )
        assert receipt.rejection_reason is not None
        assert "PII" in receipt.rejection_reason

    def test_receipt_immutable(self) -> None:
        receipt = PromotionReceipt(
            proposal_id=uuid4(),
            source_memory_id=uuid4(),
            target_knowledge_id=None,
            status="promoted",
        )
        with pytest.raises(AttributeError):
            receipt.status = "rejected"  # type: ignore[misc]


class TestPromotionWithKnowledgeWriter:
    @pytest.mark.asyncio
    async def test_approve_writes_to_knowledge(self) -> None:
        writer = _make_writer()
        pipeline = PromotionPipeline(knowledge_writer=writer)

        memory = _make_memory()
        receipt = await pipeline.create_proposal(
            memory,
            target_org_id=uuid4(),
            target_visibility="brand",
        )
        assert receipt.status == "promoted"

        approval = await pipeline.approve_proposal(
            receipt.proposal_id,
            approver_id=uuid4(),
        )
        assert approval.status == "promoted"
        assert approval.target_knowledge_id is not None

    @pytest.mark.asyncio
    async def test_approve_receipt_has_knowledge_id(self) -> None:
        writer = _make_writer()
        pipeline = PromotionPipeline(knowledge_writer=writer)

        memory = _make_memory()
        receipt = await pipeline.create_proposal(
            memory,
            target_org_id=uuid4(),
        )
        approval = await pipeline.approve_proposal(
            receipt.proposal_id,
            approver_id=uuid4(),
        )
        assert approval.target_knowledge_id is not None
        assert approval.promoted_at is not None


class TestPromotionStatusTracking:
    @pytest.mark.asyncio
    async def test_full_flow_receipts(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory()
        org_id = uuid4()

        # Create proposal
        r1 = await pipeline.create_proposal(memory, target_org_id=org_id)
        assert r1.status == "promoted"

        # Approve
        r2 = await pipeline.approve_proposal(r1.proposal_id, approver_id=uuid4())
        assert r2.status == "promoted"

        # Check all receipts
        all_receipts = pipeline.get_receipts()
        assert len(all_receipts) == 2

    @pytest.mark.asyncio
    async def test_sanitize_fail_tracked(self) -> None:
        pipeline = PromotionPipeline()
        memory = _make_memory(content="Send to user@example.com")

        receipt = await pipeline.create_proposal(memory, target_org_id=uuid4())
        assert receipt.status == "sanitize_failed"

        all_receipts = pipeline.get_receipts()
        statuses = {r.status for r in all_receipts}
        assert "sanitize_failed" in statuses
