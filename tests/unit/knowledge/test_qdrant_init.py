"""K3-2: Qdrant collection init + seed vectors tests.

Tests: vector seed generation, FK references, seeding.
Uses Fake adapter pattern (no unittest.mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.infra.vector.qdrant_adapter import VectorPoint
from src.knowledge.vector.init import (
    _make_deterministic_vector,
    generate_seed_vectors,
    seed_vectors,
)

# -- Fake adapter --


@dataclass
class FakeQdrantAdapter:
    """In-memory fake for Qdrant tests."""

    _points: dict[str, VectorPoint] = field(default_factory=dict)

    async def upsert_point(
        self,
        point_id: UUID,
        vector: list[float],
        payload: dict[str, Any] | None = None,
        *,
        graph_node_id: UUID | None = None,
    ) -> VectorPoint:
        point = VectorPoint(
            point_id=point_id,
            vector=vector,
            payload=payload or {},
            graph_node_id=graph_node_id,
        )
        self._points[str(point_id)] = point
        return point

    @property
    def point_count(self) -> int:
        return len(self._points)


# -- Tests --


class TestDeterministicVector:
    def test_correct_dimension(self) -> None:
        vec = _make_deterministic_vector(42)
        assert len(vec) == 1536

    def test_normalized(self) -> None:
        import math

        vec = _make_deterministic_vector(1)
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_deterministic(self) -> None:
        v1 = _make_deterministic_vector(99)
        v2 = _make_deterministic_vector(99)
        assert v1 == v2

    def test_different_seeds_differ(self) -> None:
        v1 = _make_deterministic_vector(1)
        v2 = _make_deterministic_vector(2)
        assert v1 != v2


class TestSeedVectorGeneration:
    def test_generates_correct_count(self) -> None:
        graph_nodes = [(uuid4(), "Product", f"Product {i}") for i in range(50)]
        seed = generate_seed_vectors(graph_nodes)
        assert len(seed.vectors) == 50

    def test_vectors_have_fk(self) -> None:
        nid = uuid4()
        graph_nodes = [(nid, "Product", "Test product")]
        seed = generate_seed_vectors(graph_nodes)
        assert seed.vectors[0].graph_node_id == nid

    def test_payload_contains_entity_type(self) -> None:
        graph_nodes = [(uuid4(), "Category", "Tops")]
        seed = generate_seed_vectors(graph_nodes)
        assert seed.vectors[0].payload["entity_type"] == "Category"

    def test_org_id_in_payload(self) -> None:
        org_id = uuid4()
        graph_nodes = [(uuid4(), "Product", "Test")]
        seed = generate_seed_vectors(graph_nodes, org_id=org_id)
        assert seed.vectors[0].payload["org_id"] == str(org_id)


class TestSeedVectors:
    @pytest.mark.asyncio
    async def test_seed_creates_vectors(self) -> None:
        adapter = FakeQdrantAdapter()
        graph_nodes = [(uuid4(), "Product", f"Product {i}") for i in range(50)]
        seed = generate_seed_vectors(graph_nodes)
        count = await seed_vectors(adapter, seed)  # type: ignore[arg-type]
        assert count >= 50
        assert adapter.point_count >= 50

    @pytest.mark.asyncio
    async def test_seed_returns_correct_count(self) -> None:
        adapter = FakeQdrantAdapter()
        graph_nodes = [(uuid4(), "Product", "Single")]
        seed = generate_seed_vectors(graph_nodes)
        count = await seed_vectors(adapter, seed)  # type: ignore[arg-type]
        assert count == 1
