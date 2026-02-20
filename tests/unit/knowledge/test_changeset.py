"""K3-7: ERP/PIM ChangeSet batch import tests.

Tests: batch processing, idempotency deduplication, audit trail.
Uses Fake adapter pattern (no unittest.mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.graph.neo4j_adapter import GraphNode
from src.infra.vector.qdrant_adapter import VectorPoint
from src.knowledge.api.write import KnowledgeWriteService
from src.knowledge.importer.changeset import (
    ChangeSet,
    ChangeSetEntry,
    ChangeSetProcessor,
)
from src.knowledge.registry.entity_type import EntityTypeRegistry
from src.knowledge.sync.fk_registry import FKRegistry

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
            node_id=node_id, entity_type=entity_type, properties=properties, org_id=org_id
        )
        self._nodes[str(node_id)] = node
        return node

    async def update_node(self, node_id: UUID, properties: dict[str, Any]) -> GraphNode | None:
        existing = self._nodes.get(str(node_id))
        if not existing:
            return None
        updated = GraphNode(
            node_id=existing.node_id,
            entity_type=existing.entity_type,
            properties={**existing.properties, **properties},
            org_id=existing.org_id,
        )
        self._nodes[str(node_id)] = updated
        return updated

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
            point_id=point_id, vector=vector, payload=payload or {}, graph_node_id=graph_node_id
        )
        self._points[str(point_id)] = pt
        return pt

    async def delete_point(self, point_id: UUID) -> bool:
        return self._points.pop(str(point_id), None) is not None


def _make_processor() -> ChangeSetProcessor:
    neo4j = FakeNeo4j()
    qdrant = FakeQdrant()
    fk = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]
    registry = EntityTypeRegistry()
    write_svc = KnowledgeWriteService(fk, registry)
    return ChangeSetProcessor(write_svc)


# -- Tests --


class TestBatchProcessing:
    @pytest.mark.asyncio
    async def test_process_creates(self) -> None:
        proc = _make_processor()
        cs = ChangeSet(
            changeset_id=uuid4(),
            source_system="erp",
            org_id=uuid4(),
            entries=[
                ChangeSetEntry(
                    operation="create",
                    entity_type="BrandKnowledge",
                    properties={"content": f"Item {i}"},
                    idempotency_key=f"erp#item-{i}",
                )
                for i in range(5)
            ],
        )
        result = await proc.process(cs)
        assert result.processed == 5
        assert result.failed == 0
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_audit_trail(self) -> None:
        proc = _make_processor()
        cs_id = uuid4()
        cs = ChangeSet(
            changeset_id=cs_id,
            source_system="pim",
            org_id=uuid4(),
            entries=[
                ChangeSetEntry(
                    operation="create",
                    entity_type="BrandKnowledge",
                    properties={"content": "Test"},
                    idempotency_key="pim#1",
                )
            ],
        )
        await proc.process(cs)
        audit = proc.get_audit(cs_id)
        assert audit is not None
        assert audit.entries_total == 1
        assert audit.entries_processed == 1
        assert audit.started_at is not None
        assert audit.completed_at is not None


class TestIdempotencyDedup:
    @pytest.mark.asyncio
    async def test_duplicate_keys_skipped(self) -> None:
        proc = _make_processor()
        org_id = uuid4()

        # First batch
        cs1 = ChangeSet(
            changeset_id=uuid4(),
            source_system="erp",
            org_id=org_id,
            entries=[
                ChangeSetEntry(
                    operation="create",
                    entity_type="BrandKnowledge",
                    properties={"content": "Original"},
                    idempotency_key="erp#dup-1",
                )
            ],
        )
        r1 = await proc.process(cs1)
        assert r1.processed == 1

        # Second batch with same key
        cs2 = ChangeSet(
            changeset_id=uuid4(),
            source_system="erp",
            org_id=org_id,
            entries=[
                ChangeSetEntry(
                    operation="create",
                    entity_type="BrandKnowledge",
                    properties={"content": "Duplicate"},
                    idempotency_key="erp#dup-1",
                )
            ],
        )
        r2 = await proc.process(cs2)
        assert r2.skipped == 1
        assert r2.processed == 0


class TestUpdateAndDelete:
    @pytest.mark.asyncio
    async def test_update_requires_node_id(self) -> None:
        proc = _make_processor()
        cs = ChangeSet(
            changeset_id=uuid4(),
            source_system="erp",
            org_id=uuid4(),
            entries=[
                ChangeSetEntry(
                    operation="update",
                    entity_type="BrandKnowledge",
                    properties={"content": "Updated"},
                    idempotency_key="erp#upd-1",
                    graph_node_id=None,  # Missing
                )
            ],
        )
        result = await proc.process(cs)
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_delete_requires_node_id(self) -> None:
        proc = _make_processor()
        cs = ChangeSet(
            changeset_id=uuid4(),
            source_system="erp",
            org_id=uuid4(),
            entries=[
                ChangeSetEntry(
                    operation="delete",
                    entity_type="BrandKnowledge",
                    properties={},
                    idempotency_key="erp#del-1",
                    graph_node_id=None,
                )
            ],
        )
        result = await proc.process(cs)
        assert result.failed == 1
