"""Integration test: KnowledgeWriteAdapter + DeterministicEmbedder + FKRegistry.

Validates the full dual-write chain end-to-end:
  - create_entry produces both Neo4j node AND Qdrant vector (embedding present)
  - update_entry re-syncs Qdrant via update_with_fk
  - delete_entry cascades to both stores via delete_with_fk
  - Embedding is deterministic and non-zero

No external services required -- uses in-process structural test doubles
(no unittest.mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.knowledge.api.write_adapter import KnowledgeWriteAdapter
from src.knowledge.embedding import DeterministicEmbedder
from src.knowledge.sync.fk_registry import FKRegistry
from src.shared.types import GraphNode, VectorPoint

# -- Structural test doubles (NOT mocks) --


@dataclass
class InMemoryNeo4j:
    """Structural double for Neo4jAdapter — stores nodes in-memory."""

    _nodes: dict[str, GraphNode] = field(default_factory=dict)
    _driver: object = field(default_factory=object)  # non-None = "connected"

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
        self, node_id: UUID, properties: dict[str, Any]
    ) -> GraphNode | None:
        existing = self._nodes.get(str(node_id))
        if existing is None:
            return None
        merged = {**existing.properties, **properties}
        updated = GraphNode(
            node_id=existing.node_id,
            entity_type=existing.entity_type,
            properties=merged,
            org_id=existing.org_id,
        )
        self._nodes[str(node_id)] = updated
        return updated

    async def delete_node(self, node_id: UUID) -> bool:
        return self._nodes.pop(str(node_id), None) is not None

    async def find_by_org(
        self,
        org_id: UUID,
        entity_type: str | None = None,
        *,
        limit: int = 100,
    ) -> list[GraphNode]:
        results = [
            n
            for n in self._nodes.values()
            if n.org_id == org_id
            and (entity_type is None or n.entity_type == entity_type)
        ]
        return results[:limit]

    async def mark_sync_status(self, node_id: UUID, status: str) -> None:
        existing = self._nodes.get(str(node_id))
        if existing:
            self._nodes[str(node_id)] = GraphNode(
                node_id=existing.node_id,
                entity_type=existing.entity_type,
                properties=existing.properties,
                org_id=existing.org_id,
                sync_status=status,
            )


@dataclass
class InMemoryQdrant:
    """Structural double for QdrantAdapter — stores points in-memory."""

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


def _build_adapter() -> tuple[KnowledgeWriteAdapter, InMemoryNeo4j, InMemoryQdrant]:
    neo4j = InMemoryNeo4j()
    qdrant = InMemoryQdrant()
    fk = FKRegistry(neo4j=neo4j, qdrant=qdrant)
    embedder = DeterministicEmbedder()
    adapter = KnowledgeWriteAdapter(
        neo4j=neo4j,
        qdrant=qdrant,
        fk_registry=fk,
        embedder=embedder,
    )
    return adapter, neo4j, qdrant


@pytest.mark.integration
class TestDualWriteCreateChain:
    """create_entry -> FKRegistry.write_with_fk -> Neo4j + Qdrant."""

    @pytest.mark.asyncio
    async def test_create_writes_both_stores(self) -> None:
        adapter, neo4j, qdrant = _build_adapter()
        org_id = uuid4()

        result = await adapter.create_entry(
            org_id=org_id,
            entity_type="product",
            properties={"name": "Silk Scarf", "price": 99},
            user_id=uuid4(),
        )

        entry_id = result["entry_id"]
        assert result["sync_status"] == "synced"

        # Neo4j node exists
        assert str(entry_id) in neo4j._nodes
        node = neo4j._nodes[str(entry_id)]
        assert node.entity_type == "product"
        assert node.org_id == org_id

        # Qdrant point exists with FK
        assert len(qdrant._points) == 1
        point = next(iter(qdrant._points.values()))
        assert point.graph_node_id == entry_id
        assert len(point.vector) == 1536
        assert point.payload["entity_type"] == "product"

    @pytest.mark.asyncio
    async def test_embedding_is_deterministic(self) -> None:
        adapter1, _, qdrant1 = _build_adapter()
        adapter2, _, qdrant2 = _build_adapter()
        org_id = uuid4()
        user_id = uuid4()
        props = {"name": "Same Product"}

        await adapter1.create_entry(
            org_id=org_id,
            entity_type="product",
            properties=props,
            user_id=user_id,
        )
        await adapter2.create_entry(
            org_id=org_id,
            entity_type="product",
            properties=props,
            user_id=user_id,
        )

        v1 = next(iter(qdrant1._points.values())).vector
        v2 = next(iter(qdrant2._points.values())).vector
        assert v1 == v2, "Same input must produce same embedding"


@pytest.mark.integration
class TestDualWriteUpdateChain:
    """update_entry -> FKRegistry.update_with_fk -> Neo4j + Qdrant."""

    @pytest.mark.asyncio
    async def test_update_syncs_both_stores(self) -> None:
        adapter, _neo4j, qdrant = _build_adapter()
        org_id = uuid4()
        user_id = uuid4()

        created = await adapter.create_entry(
            org_id=org_id,
            entity_type="product",
            properties={"name": "Original"},
            user_id=user_id,
        )
        entry_id = created["entry_id"]
        assert len(qdrant._points) == 1

        # Update
        updated = await adapter.update_entry(
            org_id=org_id,
            entry_id=entry_id,
            properties={"name": "Updated"},
            user_id=user_id,
        )
        assert updated is not None
        assert updated["properties"]["name"] == "Updated"

        # Qdrant should still have exactly 1 point (upserted, not duplicated)
        assert len(qdrant._points) == 1
        point = next(iter(qdrant._points.values()))
        assert point.payload["text"]  # semantic content populated

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self) -> None:
        adapter, _, _ = _build_adapter()
        result = await adapter.update_entry(
            org_id=uuid4(),
            entry_id=uuid4(),
            properties={"name": "Ghost"},
            user_id=uuid4(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_wrong_org_returns_none(self) -> None:
        adapter, _, _ = _build_adapter()
        org_id = uuid4()
        other_org = uuid4()

        created = await adapter.create_entry(
            org_id=org_id,
            entity_type="article",
            properties={"title": "Org Isolation"},
            user_id=uuid4(),
        )

        result = await adapter.update_entry(
            org_id=other_org,
            entry_id=created["entry_id"],
            properties={"title": "Hacked"},
            user_id=uuid4(),
        )
        assert result is None, "Cross-org update must be blocked"


@pytest.mark.integration
class TestDualWriteDeleteChain:
    """delete_entry -> FKRegistry.delete_with_fk -> Neo4j + Qdrant."""

    @pytest.mark.asyncio
    async def test_delete_removes_both_stores(self) -> None:
        adapter, neo4j, qdrant = _build_adapter()
        org_id = uuid4()

        created = await adapter.create_entry(
            org_id=org_id,
            entity_type="product",
            properties={"name": "Doomed"},
            user_id=uuid4(),
        )
        entry_id = created["entry_id"]
        assert len(neo4j._nodes) == 1
        assert len(qdrant._points) == 1

        deleted = await adapter.delete_entry(
            org_id=org_id,
            entry_id=entry_id,
            user_id=uuid4(),
        )
        assert deleted is True
        assert len(neo4j._nodes) == 0
        assert len(qdrant._points) == 0

    @pytest.mark.asyncio
    async def test_delete_wrong_org_blocked(self) -> None:
        adapter, neo4j, _ = _build_adapter()
        org_id = uuid4()

        created = await adapter.create_entry(
            org_id=org_id,
            entity_type="brand",
            properties={"name": "Protected"},
            user_id=uuid4(),
        )

        deleted = await adapter.delete_entry(
            org_id=uuid4(),
            entry_id=created["entry_id"],
            user_id=uuid4(),
        )
        assert deleted is False
        assert len(neo4j._nodes) == 1


@pytest.mark.integration
class TestDualWriteListChain:
    """list_entries scoped by org_id + entity_type."""

    @pytest.mark.asyncio
    async def test_list_filtered_by_org(self) -> None:
        adapter, _, _ = _build_adapter()
        org_a = uuid4()
        org_b = uuid4()

        await adapter.create_entry(
            org_id=org_a,
            entity_type="product",
            properties={"name": "A"},
            user_id=uuid4(),
        )
        await adapter.create_entry(
            org_id=org_b,
            entity_type="product",
            properties={"name": "B"},
            user_id=uuid4(),
        )

        results = await adapter.list_entries(org_id=org_a)
        assert len(results) == 1
        assert results[0]["properties"]["name"] == "A"
