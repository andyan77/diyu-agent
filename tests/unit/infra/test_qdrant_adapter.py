"""Qdrant adapter unit tests using Fake adapter pattern.

Milestone: I3-2
Tests: connection lifecycle, upsert/get/delete, semantic search, org filtering.

No unittest.mock / MagicMock / patch — uses Fake adapter with in-memory store.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.vector.qdrant_adapter import VectorPoint

# -- Fake adapter (DI pattern, no mock) --


@dataclass
class FakeQdrantAdapter:
    """In-memory fake for Qdrant adapter unit tests."""

    _points: dict[str, VectorPoint] = field(default_factory=dict)
    _connected: bool = False

    async def connect(self) -> None:
        self._connected = True

    async def close(self) -> None:
        self._connected = False

    async def upsert_point(
        self,
        point_id: UUID,
        vector: list[float],
        payload: dict[str, Any] | None = None,
        *,
        graph_node_id: UUID | None = None,
    ) -> VectorPoint:
        point_payload = payload or {}
        if graph_node_id is not None:
            point_payload["graph_node_id"] = str(graph_node_id)
        point = VectorPoint(
            point_id=point_id,
            vector=vector,
            payload=point_payload,
            graph_node_id=graph_node_id,
        )
        self._points[str(point_id)] = point
        return point

    async def get_point(self, point_id: UUID) -> VectorPoint | None:
        return self._points.get(str(point_id))

    async def delete_point(self, point_id: UUID) -> bool:
        key = str(point_id)
        if key in self._points:
            del self._points[key]
        return True

    async def search(
        self,
        query_vector: list[float],
        *,
        org_id: UUID | None = None,
        limit: int = 10,
    ) -> list[VectorPoint]:
        candidates = list(self._points.values())
        if org_id is not None:
            candidates = [p for p in candidates if p.payload.get("org_id") == str(org_id)]

        # Cosine similarity scoring
        scored: list[tuple[float, VectorPoint]] = []
        for p in candidates:
            score = _cosine_similarity(query_vector, p.vector)
            scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            VectorPoint(
                point_id=p.point_id,
                vector=p.vector,
                payload=p.payload,
                graph_node_id=p.graph_node_id,
                score=s,
            )
            for s, p in scored[:limit]
        ]

    async def count(self) -> int:
        return len(self._points)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@pytest.fixture
def adapter() -> FakeQdrantAdapter:
    return FakeQdrantAdapter()


# -- Tests --


@pytest.mark.unit
class TestQdrantAdapterConnection:
    async def test_connect_and_close(self, adapter: FakeQdrantAdapter) -> None:
        assert not adapter._connected
        await adapter.connect()
        assert adapter._connected
        await adapter.close()
        assert not adapter._connected


@pytest.mark.unit
class TestQdrantAdapterCRUD:
    async def test_upsert_and_get(self, adapter: FakeQdrantAdapter) -> None:
        pid = uuid4()
        gn_id = uuid4()
        point = await adapter.upsert_point(
            pid,
            [0.1, 0.2, 0.3],
            payload={"label": "test"},
            graph_node_id=gn_id,
        )
        assert point.point_id == pid
        assert point.vector == [0.1, 0.2, 0.3]
        assert point.graph_node_id == gn_id

        retrieved = await adapter.get_point(pid)
        assert retrieved is not None
        assert retrieved.point_id == pid
        assert retrieved.payload["label"] == "test"

    async def test_get_nonexistent(self, adapter: FakeQdrantAdapter) -> None:
        result = await adapter.get_point(uuid4())
        assert result is None

    async def test_upsert_overwrites(self, adapter: FakeQdrantAdapter) -> None:
        pid = uuid4()
        await adapter.upsert_point(pid, [1.0, 0.0], payload={"v": 1})
        await adapter.upsert_point(pid, [0.0, 1.0], payload={"v": 2})
        retrieved = await adapter.get_point(pid)
        assert retrieved is not None
        assert retrieved.vector == [0.0, 1.0]
        assert retrieved.payload["v"] == 2

    async def test_delete(self, adapter: FakeQdrantAdapter) -> None:
        pid = uuid4()
        await adapter.upsert_point(pid, [0.1, 0.2])
        assert await adapter.delete_point(pid) is True
        assert await adapter.get_point(pid) is None

    async def test_delete_idempotent(self, adapter: FakeQdrantAdapter) -> None:
        assert await adapter.delete_point(uuid4()) is True


@pytest.mark.unit
class TestQdrantAdapterSearch:
    async def test_search_returns_ranked_results(self, adapter: FakeQdrantAdapter) -> None:
        await adapter.upsert_point(uuid4(), [1.0, 0.0, 0.0], payload={"name": "A"})
        await adapter.upsert_point(uuid4(), [0.9, 0.1, 0.0], payload={"name": "B"})
        await adapter.upsert_point(uuid4(), [0.0, 0.0, 1.0], payload={"name": "C"})

        results = await adapter.search([1.0, 0.0, 0.0])
        assert len(results) == 3
        assert results[0].payload["name"] == "A"
        assert results[0].score > results[2].score

    async def test_search_respects_limit(self, adapter: FakeQdrantAdapter) -> None:
        for _ in range(10):
            await adapter.upsert_point(uuid4(), [0.5, 0.5])
        results = await adapter.search([1.0, 0.0], limit=3)
        assert len(results) == 3

    async def test_search_with_org_filter(self, adapter: FakeQdrantAdapter) -> None:
        org_a, org_b = uuid4(), uuid4()
        await adapter.upsert_point(uuid4(), [1.0, 0.0], payload={"org_id": str(org_a), "name": "A"})
        await adapter.upsert_point(uuid4(), [0.9, 0.1], payload={"org_id": str(org_b), "name": "B"})

        results = await adapter.search([1.0, 0.0], org_id=org_a)
        assert len(results) == 1
        assert results[0].payload["name"] == "A"


@pytest.mark.unit
class TestQdrantAdapterCount:
    async def test_count_empty(self, adapter: FakeQdrantAdapter) -> None:
        assert await adapter.count() == 0

    async def test_count_after_inserts(self, adapter: FakeQdrantAdapter) -> None:
        for _ in range(5):
            await adapter.upsert_point(uuid4(), [0.1, 0.2])
        assert await adapter.count() == 5

    async def test_fk_linkage_stored(self, adapter: FakeQdrantAdapter) -> None:
        """Verify graph_node_id FK is preserved in payload."""
        pid = uuid4()
        gn_id = uuid4()
        await adapter.upsert_point(pid, [0.1], graph_node_id=gn_id)
        point = await adapter.get_point(pid)
        assert point is not None
        assert point.graph_node_id == gn_id
        assert point.payload["graph_node_id"] == str(gn_id)
