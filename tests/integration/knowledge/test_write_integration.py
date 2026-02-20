"""K3-4 Integration: Knowledge Write end-to-end via FK registry.

Tests: full write chain (entity type → idempotency → FK double-write → receipt).
Uses in-memory Fake adapters to verify the complete flow without external services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.graph.neo4j_adapter import GraphNode
from src.infra.vector.qdrant_adapter import VectorPoint
from src.knowledge.api.write import KnowledgeWriteRequest, KnowledgeWriteService
from src.knowledge.registry.entity_type import EntityTypeDefinition, EntityTypeRegistry
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
            node_id=node_id,
            entity_type=entity_type,
            properties=properties,
            org_id=org_id,
        )
        self._nodes[str(node_id)] = node
        return node

    async def mark_sync_status(self, node_id: UUID, status: str) -> None:
        existing = self._nodes.get(str(node_id))
        if existing:
            updated = GraphNode(
                node_id=existing.node_id,
                entity_type=existing.entity_type,
                properties=existing.properties,
                org_id=existing.org_id,
                sync_status=status,
            )
            self._nodes[str(node_id)] = updated

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


def _build_service() -> tuple[KnowledgeWriteService, FakeNeo4j, FakeQdrant]:
    neo4j = FakeNeo4j()
    qdrant = FakeQdrant()
    fk = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]
    registry = EntityTypeRegistry()
    svc = KnowledgeWriteService(fk, registry)
    return svc, neo4j, qdrant


class TestEndToEndWrite:
    @pytest.mark.asyncio
    async def test_write_creates_graph_and_vector(self) -> None:
        svc, neo4j, qdrant = _build_service()
        org_id = uuid4()
        req = KnowledgeWriteRequest(
            entity_type="BrandKnowledge",
            properties={"content": "Integration test knowledge"},
            org_id=org_id,
            visibility="brand",
            idempotency_key="int-1",
            source="admin",
            semantic_content="Integration test knowledge",
        )
        resp = await svc.write(req, embedding=[0.1] * 10)

        # Verify graph node created
        assert resp.graph_node_id is not None
        assert str(resp.graph_node_id) in neo4j._nodes

        # Verify vector point created (with FK)
        assert len(qdrant._points) == 1
        point = next(iter(qdrant._points.values()))
        assert point.graph_node_id == resp.graph_node_id

    @pytest.mark.asyncio
    async def test_write_receipt_matches_stores(self) -> None:
        svc, neo4j, _qdrant = _build_service()
        org_id = uuid4()
        req = KnowledgeWriteRequest(
            entity_type="GlobalKnowledge",
            properties={"content": "Global info"},
            org_id=org_id,
            visibility="global",
            idempotency_key="int-2",
            source="erp",
            semantic_content="Global info",
        )
        resp = await svc.write(req)
        receipt = resp.write_receipt

        # Receipt entity type and org_id match
        assert receipt.entity_type == "GlobalKnowledge"
        assert receipt.org_id == org_id
        assert receipt.sync_status == "synced"

        # Graph node has matching properties
        node = neo4j._nodes[str(resp.graph_node_id)]
        assert node.entity_type == "GlobalKnowledge"
        assert node.properties["content"] == "Global info"

    @pytest.mark.asyncio
    async def test_multiple_writes_different_keys(self) -> None:
        svc, neo4j, _qdrant = _build_service()
        org_id = uuid4()

        for i in range(3):
            req = KnowledgeWriteRequest(
                entity_type="BrandKnowledge",
                properties={"content": f"Item {i}"},
                org_id=org_id,
                visibility="brand",
                idempotency_key=f"multi-{i}",
                source="batch",
            )
            await svc.write(req)

        assert len(neo4j._nodes) == 3


class TestIdempotencyEndToEnd:
    @pytest.mark.asyncio
    async def test_idempotent_write_no_duplicate_nodes(self) -> None:
        svc, neo4j, _qdrant = _build_service()
        org_id = uuid4()
        req = KnowledgeWriteRequest(
            entity_type="BrandKnowledge",
            properties={"content": "Same content"},
            org_id=org_id,
            visibility="brand",
            idempotency_key="dup-check",
            source="admin",
        )
        r1 = await svc.write(req)
        r2 = await svc.write(req)

        assert r1.graph_node_id == r2.graph_node_id
        # Only 1 node created despite 2 write calls
        assert len(neo4j._nodes) == 1


class TestCustomEntityType:
    @pytest.mark.asyncio
    async def test_write_custom_entity_type(self) -> None:
        svc, neo4j, _qdrant = _build_service()

        # Register a custom type
        svc._entity_registry.register(
            EntityTypeDefinition(
                entity_type_id="Product",
                label="Product",
                registered_by="skill:merchandising",
                schema={"required_properties": ["name", "sku"]},
            )
        )

        org_id = uuid4()
        req = KnowledgeWriteRequest(
            entity_type="Product",
            properties={"name": "Silk Scarf", "sku": "SKU-001"},
            org_id=org_id,
            visibility="brand",
            idempotency_key="prod-1",
            source="erp",
        )
        resp = await svc.write(req)
        assert resp.graph_node_id is not None

        node = neo4j._nodes[str(resp.graph_node_id)]
        assert node.entity_type == "Product"
        assert node.properties["name"] == "Silk Scarf"

    @pytest.mark.asyncio
    async def test_write_custom_type_missing_required(self) -> None:
        svc, _, _ = _build_service()

        svc._entity_registry.register(
            EntityTypeDefinition(
                entity_type_id="Product",
                label="Product",
                registered_by="skill:merchandising",
                schema={"required_properties": ["name", "sku"]},
            )
        )

        req = KnowledgeWriteRequest(
            entity_type="Product",
            properties={"name": "Missing SKU"},  # sku missing
            org_id=uuid4(),
            visibility="brand",
            idempotency_key="prod-2",
            source="erp",
        )
        with pytest.raises(ValueError, match="Missing required property"):
            await svc.write(req)
