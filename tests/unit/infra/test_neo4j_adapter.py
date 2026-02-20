"""Neo4j adapter unit tests using Fake adapter pattern.

Milestone: I3-1
Tests: connection lifecycle, CRUD operations, org scoping, sync status.

No unittest.mock / MagicMock / patch — uses Fake adapter with in-memory store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.graph.neo4j_adapter import GraphNode, GraphRelationship

# -- Fake adapter (DI pattern, no mock) --


@dataclass
class FakeNeo4jAdapter:
    """In-memory fake for Neo4j adapter unit tests."""

    _nodes: dict[str, GraphNode] = field(default_factory=dict)
    _relationships: list[GraphRelationship] = field(default_factory=list)
    _connected: bool = False

    async def connect(self) -> None:
        self._connected = True

    async def close(self) -> None:
        self._connected = False

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

    async def get_node(self, node_id: UUID) -> GraphNode | None:
        return self._nodes.get(str(node_id))

    async def update_node(
        self,
        node_id: UUID,
        properties: dict[str, Any],
    ) -> GraphNode | None:
        existing = self._nodes.get(str(node_id))
        if existing is None:
            return None
        updated = GraphNode(
            node_id=existing.node_id,
            entity_type=existing.entity_type,
            properties={**existing.properties, **properties},
            org_id=existing.org_id,
            sync_status=existing.sync_status,
        )
        self._nodes[str(node_id)] = updated
        return updated

    async def delete_node(self, node_id: UUID) -> bool:
        key = str(node_id)
        if key in self._nodes:
            del self._nodes[key]
            self._relationships = [
                r for r in self._relationships if r.source_id != node_id and r.target_id != node_id
            ]
            return True
        return False

    async def create_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphRelationship:
        rel = GraphRelationship(
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            properties=properties or {},
        )
        self._relationships.append(rel)
        return rel

    async def find_by_org(
        self,
        org_id: UUID,
        entity_type: str | None = None,
        *,
        limit: int = 100,
    ) -> list[GraphNode]:
        results = []
        for node in self._nodes.values():
            if node.org_id == org_id and (entity_type is None or node.entity_type == entity_type):
                results.append(node)
                if len(results) >= limit:
                    break
        return results

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


@pytest.fixture
def adapter() -> FakeNeo4jAdapter:
    return FakeNeo4jAdapter()


# -- Tests --


@pytest.mark.unit
class TestNeo4jAdapterConnection:
    async def test_connect_and_close(self, adapter: FakeNeo4jAdapter) -> None:
        assert not adapter._connected
        await adapter.connect()
        assert adapter._connected
        await adapter.close()
        assert not adapter._connected


@pytest.mark.unit
class TestNeo4jAdapterCRUD:
    async def test_create_and_get_node(self, adapter: FakeNeo4jAdapter) -> None:
        node_id = uuid4()
        org_id = uuid4()
        node = await adapter.create_node("Product", node_id, {"name": "Test"}, org_id=org_id)
        assert node.node_id == node_id
        assert node.entity_type == "Product"
        assert node.properties["name"] == "Test"
        assert node.org_id == org_id

        retrieved = await adapter.get_node(node_id)
        assert retrieved is not None
        assert retrieved.node_id == node_id

    async def test_get_nonexistent_node(self, adapter: FakeNeo4jAdapter) -> None:
        result = await adapter.get_node(uuid4())
        assert result is None

    async def test_update_node(self, adapter: FakeNeo4jAdapter) -> None:
        node_id = uuid4()
        await adapter.create_node("Product", node_id, {"name": "Old"})
        updated = await adapter.update_node(node_id, {"name": "New", "price": 100})
        assert updated is not None
        assert updated.properties["name"] == "New"
        assert updated.properties["price"] == 100

    async def test_update_nonexistent_node(self, adapter: FakeNeo4jAdapter) -> None:
        result = await adapter.update_node(uuid4(), {"x": 1})
        assert result is None

    async def test_delete_node(self, adapter: FakeNeo4jAdapter) -> None:
        node_id = uuid4()
        await adapter.create_node("Product", node_id, {"name": "Test"})
        assert await adapter.delete_node(node_id) is True
        assert await adapter.get_node(node_id) is None

    async def test_delete_nonexistent_node(self, adapter: FakeNeo4jAdapter) -> None:
        assert await adapter.delete_node(uuid4()) is False

    async def test_delete_removes_relationships(self, adapter: FakeNeo4jAdapter) -> None:
        n1, n2 = uuid4(), uuid4()
        await adapter.create_node("A", n1, {})
        await adapter.create_node("B", n2, {})
        await adapter.create_relationship(n1, n2, "RELATES_TO")
        assert len(adapter._relationships) == 1
        await adapter.delete_node(n1)
        assert len(adapter._relationships) == 0


@pytest.mark.unit
class TestNeo4jAdapterRelationships:
    async def test_create_relationship(self, adapter: FakeNeo4jAdapter) -> None:
        n1, n2 = uuid4(), uuid4()
        await adapter.create_node("A", n1, {})
        await adapter.create_node("B", n2, {})
        rel = await adapter.create_relationship(n1, n2, "HAS_STYLE", {"weight": 0.9})
        assert rel.source_id == n1
        assert rel.target_id == n2
        assert rel.rel_type == "HAS_STYLE"
        assert rel.properties["weight"] == 0.9


@pytest.mark.unit
class TestNeo4jAdapterOrgScoping:
    async def test_find_by_org(self, adapter: FakeNeo4jAdapter) -> None:
        org_a, org_b = uuid4(), uuid4()
        await adapter.create_node("Product", uuid4(), {"name": "P1"}, org_id=org_a)
        await adapter.create_node("Product", uuid4(), {"name": "P2"}, org_id=org_a)
        await adapter.create_node("Product", uuid4(), {"name": "P3"}, org_id=org_b)

        results = await adapter.find_by_org(org_a)
        assert len(results) == 2

    async def test_find_by_org_with_type_filter(self, adapter: FakeNeo4jAdapter) -> None:
        org = uuid4()
        await adapter.create_node("Product", uuid4(), {}, org_id=org)
        await adapter.create_node("Style", uuid4(), {}, org_id=org)

        products = await adapter.find_by_org(org, entity_type="Product")
        assert len(products) == 1
        assert products[0].entity_type == "Product"

    async def test_find_by_org_respects_limit(self, adapter: FakeNeo4jAdapter) -> None:
        org = uuid4()
        for _ in range(5):
            await adapter.create_node("Product", uuid4(), {}, org_id=org)

        results = await adapter.find_by_org(org, limit=3)
        assert len(results) == 3


@pytest.mark.unit
class TestNeo4jAdapterSyncStatus:
    async def test_mark_sync_status(self, adapter: FakeNeo4jAdapter) -> None:
        node_id = uuid4()
        await adapter.create_node("Product", node_id, {})
        node = await adapter.get_node(node_id)
        assert node is not None
        assert node.sync_status == "synced"

        await adapter.mark_sync_status(node_id, "pending_vector_sync")
        node = await adapter.get_node(node_id)
        assert node is not None
        assert node.sync_status == "pending_vector_sync"
