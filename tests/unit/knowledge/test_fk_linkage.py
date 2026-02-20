"""K3-3: FK linkage (Neo4j <-> Qdrant) tests.

Tests: double-write consistency, sync status tracking, retry on failure.
Uses Fake adapter pattern (no unittest.mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.graph.neo4j_adapter import GraphNode
from src.infra.vector.qdrant_adapter import VectorPoint
from src.knowledge.sync.fk_registry import FKRegistry

# -- Fake adapters --


@dataclass
class FakeNeo4j:
    """In-memory fake Neo4j."""

    _nodes: dict[str, GraphNode] = field(default_factory=dict)
    _sync_statuses: dict[str, str] = field(default_factory=dict)

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
        self._sync_statuses[str(node_id)] = status

    async def delete_node(self, node_id: UUID) -> bool:
        key = str(node_id)
        if key in self._nodes:
            del self._nodes[key]
            return True
        return False


@dataclass
class FakeQdrant:
    """In-memory fake Qdrant."""

    _points: dict[str, VectorPoint] = field(default_factory=dict)
    fail_count: int = 0  # Number of consecutive failures to simulate

    async def upsert_point(
        self,
        point_id: UUID,
        vector: list[float],
        payload: dict[str, Any] | None = None,
        *,
        graph_node_id: UUID | None = None,
    ) -> VectorPoint:
        if self.fail_count > 0:
            self.fail_count -= 1
            msg = "Simulated Qdrant failure"
            raise ConnectionError(msg)
        point = VectorPoint(
            point_id=point_id,
            vector=vector,
            payload=payload or {},
            graph_node_id=graph_node_id,
        )
        self._points[str(point_id)] = point
        return point

    async def delete_point(self, point_id: UUID) -> bool:
        self._points.pop(str(point_id), None)
        return True


# -- Tests --


class TestDoubleWrite:
    @pytest.mark.asyncio
    async def test_graph_only_write(self) -> None:
        neo4j = FakeNeo4j()
        qdrant = FakeQdrant()
        registry = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]

        result = await registry.write_with_fk(
            entity_type="Product",
            node_id=uuid4(),
            properties={"name": "Test"},
        )

        assert result.graph_node is not None
        assert result.vector_point is None
        assert result.sync_status == "synced"

    @pytest.mark.asyncio
    async def test_double_write_with_embedding(self) -> None:
        neo4j = FakeNeo4j()
        qdrant = FakeQdrant()
        registry = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]
        node_id = uuid4()

        result = await registry.write_with_fk(
            entity_type="Product",
            node_id=node_id,
            properties={"name": "Test Product"},
            semantic_content="A nice test product",
            embedding=[0.1] * 1536,
        )

        assert result.graph_node is not None
        assert result.vector_point is not None
        assert result.sync_status == "synced"
        assert result.vector_point.graph_node_id == node_id

    @pytest.mark.asyncio
    async def test_fk_mapping_created(self) -> None:
        neo4j = FakeNeo4j()
        qdrant = FakeQdrant()
        registry = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]
        node_id = uuid4()

        await registry.write_with_fk(
            entity_type="Product",
            node_id=node_id,
            properties={"name": "Test"},
            embedding=[0.1] * 10,
        )

        mapping = registry.get_mapping(node_id)
        assert mapping is not None
        assert mapping.graph_node_id == node_id
        assert len(mapping.vector_ids) == 1
        assert mapping.sync_status == "synced"


class TestSyncStatusTracking:
    @pytest.mark.asyncio
    async def test_pending_on_qdrant_failure(self) -> None:
        neo4j = FakeNeo4j()
        qdrant = FakeQdrant()
        qdrant.fail_count = 3  # Fail all 3 retries
        registry = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]
        node_id = uuid4()

        result = await registry.write_with_fk(
            entity_type="Product",
            node_id=node_id,
            properties={"name": "Test"},
            embedding=[0.1] * 10,
        )

        assert result.sync_status == "pending_vector_sync"
        assert result.vector_point is None
        assert neo4j._sync_statuses.get(str(node_id)) == "pending_vector_sync"

    @pytest.mark.asyncio
    async def test_get_pending_sync(self) -> None:
        neo4j = FakeNeo4j()
        qdrant = FakeQdrant()
        qdrant.fail_count = 3  # Fail all 3 retries
        registry = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]

        await registry.write_with_fk(
            entity_type="Product",
            node_id=uuid4(),
            properties={"name": "Test"},
            embedding=[0.1] * 10,
        )

        pending = registry.get_pending_sync()
        assert len(pending) == 1
        assert pending[0].sync_status == "pending_vector_sync"


class TestDeleteWithFK:
    @pytest.mark.asyncio
    async def test_delete_removes_both(self) -> None:
        neo4j = FakeNeo4j()
        qdrant = FakeQdrant()
        registry = FKRegistry(neo4j, qdrant)  # type: ignore[arg-type]
        node_id = uuid4()

        await registry.write_with_fk(
            entity_type="Product",
            node_id=node_id,
            properties={"name": "Test"},
            embedding=[0.1] * 10,
        )

        assert len(qdrant._points) == 1
        deleted = await registry.delete_with_fk(node_id)
        assert deleted
        assert len(qdrant._points) == 0
        assert str(node_id) not in neo4j._nodes
