"""Performance tests for Knowledge graph queries.

Phase 3 soft gate: p3-graph-perf
Validates that Knowledge resolver queries meet p95 < 200ms threshold.
Uses Fake adapters for unit-level performance measurement.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from src.knowledge.resolver.resolver import DiyuResolver, ResolverProfile
from src.shared.types import OrganizationContext

# -- Fake adapters for performance testing --


class FakeSession:
    """Fake Neo4j session that returns pre-configured results."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    async def run(self, query: str, **kwargs: Any) -> FakeResult:
        return FakeResult(self._records)

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class FakeResult:
    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records
        self._idx = 0

    def __aiter__(self) -> FakeResult:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._idx >= len(self._records):
            raise StopAsyncIteration
        record = self._records[self._idx]
        self._idx += 1
        return record


@dataclass
class FakeDriver:
    _records: list[dict[str, Any]] = field(default_factory=list)

    def session(self) -> FakeSession:
        return FakeSession(self._records)


@dataclass
class FakeNeo4jAdapter:
    _driver: FakeDriver = field(default_factory=FakeDriver)

    @property
    def driver(self) -> FakeDriver:
        return self._driver


@dataclass
class FakeQdrantAdapter:
    _collection_name: str = "knowledge_vectors"
    _vector_size: int = 1536


# -- Performance tests --


@pytest.mark.perf
class TestKnowledgeQueryPerformance:
    """Performance tests for Knowledge resolver queries."""

    @pytest.mark.asyncio
    async def test_single_entity_lookup_performance(self, perf_threshold_ms: int) -> None:
        """Single entity lookup should complete within p95 < 200ms."""
        # Setup: Create fake adapter with a single entity
        nid = uuid4()
        records = [
            {
                "n": {
                    "node_id": str(nid),
                    "org_id": str(uuid4()),
                    "sync_status": "synced",
                    "role": "admin",
                    "prompt_template": "You are an admin",
                },
                "labels": ["RoleAdaptationRule"],
            }
        ]
        neo4j = FakeNeo4jAdapter(_driver=FakeDriver(_records=records))
        qdrant = FakeQdrantAdapter()
        resolver = DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]
        org = OrganizationContext(
            user_id=uuid4(), org_id=uuid4(), org_tier="brand_hq", org_path="root"
        )

        # Measure: Run query and time it
        start = time.perf_counter()
        bundle = await resolver.resolve("core:role_adaptation", "test query", org)
        duration_ms = (time.perf_counter() - start) * 1000

        # Assert: Query completed within threshold
        assert duration_ms < perf_threshold_ms, (
            f"Single entity lookup took {duration_ms:.2f}ms, expected < {perf_threshold_ms}ms"
        )
        assert bundle.metadata is not None
        assert bundle.metadata.graph_hits == 1

    @pytest.mark.asyncio
    async def test_multi_hop_traversal_performance(self, perf_threshold_ms: int) -> None:
        """Multi-hop graph traversal should complete within p95 < 200ms."""
        # Setup: Create fake adapter with multiple connected entities
        # Use graph-only profile to avoid vector search overhead in perf test
        records = [
            {
                "n": {
                    "node_id": str(uuid4()),
                    "org_id": str(uuid4()),
                    "sync_status": "synced",
                    "role": f"role_{i}",
                    "prompt_template": f"You are role {i}",
                },
                "labels": ["RoleAdaptationRule"],
            }
            for i in range(10)  # 10 nodes for multi-hop simulation
        ]
        neo4j = FakeNeo4jAdapter(_driver=FakeDriver(_records=records))
        qdrant = FakeQdrantAdapter()
        resolver = DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]
        org = OrganizationContext(
            user_id=uuid4(), org_id=uuid4(), org_tier="brand_hq", org_path="root"
        )

        # Measure: Run query and time it
        start = time.perf_counter()
        bundle = await resolver.resolve("core:role_adaptation", "test query", org)
        duration_ms = (time.perf_counter() - start) * 1000

        # Assert: Query completed within threshold
        assert duration_ms < perf_threshold_ms, (
            f"Multi-hop traversal took {duration_ms:.2f}ms, expected < {perf_threshold_ms}ms"
        )
        assert bundle.metadata is not None
        assert bundle.metadata.graph_hits == 10

    @pytest.mark.asyncio
    async def test_empty_result_performance(self, perf_threshold_ms: int) -> None:
        """Empty query result should complete within p95 < 200ms."""
        # Setup: Create fake adapter with no records
        neo4j = FakeNeo4jAdapter()
        qdrant = FakeQdrantAdapter()
        resolver = DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]
        org = OrganizationContext(
            user_id=uuid4(), org_id=uuid4(), org_tier="brand_hq", org_path="root"
        )

        # Measure: Run query and time it
        start = time.perf_counter()
        bundle = await resolver.resolve("core:role_adaptation", "test query", org)
        duration_ms = (time.perf_counter() - start) * 1000

        # Assert: Query completed within threshold
        assert duration_ms < perf_threshold_ms, (
            f"Empty result query took {duration_ms:.2f}ms, expected < {perf_threshold_ms}ms"
        )
        assert bundle.metadata is not None
        assert bundle.metadata.graph_hits == 0

    @pytest.mark.asyncio
    async def test_custom_profile_performance(self, perf_threshold_ms: int) -> None:
        """Custom profile resolution should complete within p95 < 200ms."""
        # Setup: Create resolver with custom profile
        neo4j = FakeNeo4jAdapter()
        qdrant = FakeQdrantAdapter()
        resolver = DiyuResolver(neo4j, qdrant)  # type: ignore[arg-type]

        custom_profile = ResolverProfile(
            profile_id="perf:test",
            fk_strategy="none",
            graph_query_template=(
                "MATCH (n:TestNode) "
                "WHERE n.org_id IN $org_chain "
                "RETURN n, labels(n) as labels LIMIT $limit"
            ),
            limit=5,
            description="Performance test profile",
        )
        resolver.register_profile(custom_profile)

        org = OrganizationContext(
            user_id=uuid4(), org_id=uuid4(), org_tier="brand_hq", org_path="root"
        )

        # Measure: Run query and time it
        start = time.perf_counter()
        bundle = await resolver.resolve("perf:test", "test query", org)
        duration_ms = (time.perf_counter() - start) * 1000

        # Assert: Query completed within threshold
        assert duration_ms < perf_threshold_ms, (
            f"Custom profile query took {duration_ms:.2f}ms, expected < {perf_threshold_ms}ms"
        )
        assert bundle.metadata is not None
        assert bundle.metadata.profile_id == "perf:test"
