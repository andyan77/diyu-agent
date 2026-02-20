"""K3-4: Knowledge Write API tests.

Tests: controlled write, idempotency, schema validation, audit receipts.
Uses Fake adapter pattern (no unittest.mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.graph.neo4j_adapter import GraphNode
from src.infra.vector.qdrant_adapter import VectorPoint
from src.knowledge.api.write import KnowledgeWriteRequest, KnowledgeWriteService
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


def _make_service() -> KnowledgeWriteService:
    neo4j = FakeNeo4j()
    qdrant = FakeQdrant()
    fk = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]
    registry = EntityTypeRegistry()
    return KnowledgeWriteService(fk, registry)


# -- Tests --


class TestKnowledgeWrite:
    @pytest.mark.asyncio
    async def test_basic_write(self) -> None:
        svc = _make_service()
        req = KnowledgeWriteRequest(
            entity_type="BrandKnowledge",
            properties={"content": "Test knowledge"},
            org_id=uuid4(),
            visibility="brand",
            idempotency_key="test-1",
            source="admin",
        )
        resp = await svc.write(req)
        assert resp.graph_node_id is not None
        assert resp.version == 1
        assert resp.write_receipt.sync_status == "synced"

    @pytest.mark.asyncio
    async def test_write_receipt_fields(self) -> None:
        svc = _make_service()
        org_id = uuid4()
        req = KnowledgeWriteRequest(
            entity_type="GlobalKnowledge",
            properties={"content": "Global info"},
            org_id=org_id,
            visibility="global",
            idempotency_key="test-2",
            source="erp",
        )
        resp = await svc.write(req)
        receipt = resp.write_receipt
        assert receipt.entity_type == "GlobalKnowledge"
        assert receipt.org_id == org_id
        assert receipt.source == "erp"
        assert receipt.properties_hash


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_same_key_same_props_returns_cached(self) -> None:
        svc = _make_service()
        org_id = uuid4()
        req = KnowledgeWriteRequest(
            entity_type="BrandKnowledge",
            properties={"content": "Idempotent test"},
            org_id=org_id,
            visibility="brand",
            idempotency_key="idem-1",
            source="admin",
        )
        r1 = await svc.write(req)
        r2 = await svc.write(req)
        assert r1.graph_node_id == r2.graph_node_id

    @pytest.mark.asyncio
    async def test_same_key_different_props_raises(self) -> None:
        svc = _make_service()
        org_id = uuid4()
        r1 = KnowledgeWriteRequest(
            entity_type="BrandKnowledge",
            properties={"content": "Version A"},
            org_id=org_id,
            visibility="brand",
            idempotency_key="idem-2",
            source="admin",
        )
        r2 = KnowledgeWriteRequest(
            entity_type="BrandKnowledge",
            properties={"content": "Version B"},
            org_id=org_id,
            visibility="brand",
            idempotency_key="idem-2",
            source="admin",
        )
        await svc.write(r1)
        with pytest.raises(ValueError, match="Idempotency key conflict"):
            await svc.write(r2)


class TestSchemaValidation:
    @pytest.mark.asyncio
    async def test_missing_required_property(self) -> None:
        svc = _make_service()
        req = KnowledgeWriteRequest(
            entity_type="RoleAdaptationRule",
            properties={"role": "admin"},  # Missing prompt_template
            org_id=uuid4(),
            visibility="global",
            idempotency_key="schema-1",
            source="admin",
        )
        with pytest.raises(ValueError, match="Missing required property"):
            await svc.write(req)

    @pytest.mark.asyncio
    async def test_deprecated_type_rejected(self) -> None:
        svc = _make_service()
        from src.knowledge.registry.entity_type import EntityTypeDefinition

        svc._entity_registry.register(
            EntityTypeDefinition(
                entity_type_id="OldType",
                label="OldType",
                registered_by="skill:old",
                status="deprecated",
            )
        )
        req = KnowledgeWriteRequest(
            entity_type="OldType",
            properties={"name": "test"},
            org_id=uuid4(),
            visibility="brand",
            idempotency_key="depr-1",
            source="admin",
        )
        with pytest.raises(PermissionError, match="not writable"):
            await svc.write(req)
