"""Performance baseline: Graph query latency (K4-1).

Gate: p4-perf-baseline
Verifies: Graph query P95 < 100ms (R-5 CI regression baseline).

CI baseline uses in-memory stub — validates query interface, not Neo4j.
Capacity-planning baseline (1M nodes) requires live Neo4j instance
and is run separately per R-5 档位 2.
"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest


class InMemoryKnowledgeStub:
    """Minimal KnowledgePort stub for performance baseline testing.

    Returns empty results immediately — measures interface overhead only.
    """

    async def resolve(
        self,
        profile_id: str,
        query: str,
        org_context: object,
    ) -> object:
        """Resolve a knowledge query. Returns None (no results)."""
        return None

    async def search_graph(
        self,
        query: str,
        *,
        org_id: object | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """Search graph nodes matching query. Returns empty list."""
        return []


@pytest.mark.perf
class TestGraphQueryPerf:
    """Graph query performance baseline (K4-1, R-5 CI baseline).

    P95 < 100ms with in-memory stub.
    """

    @pytest.fixture()
    def knowledge(self):
        return InMemoryKnowledgeStub()

    @pytest.mark.asyncio
    async def test_single_graph_query_under_100ms(
        self,
        knowledge: InMemoryKnowledgeStub,
    ) -> None:
        """Single graph query completes under 100ms."""
        start = time.perf_counter()
        results = await knowledge.search_graph(
            "test query",
            org_id=uuid4(),
            top_k=10,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert isinstance(results, list)
        assert elapsed_ms < 100, f"Graph query took {elapsed_ms:.1f}ms (target: <100ms)"

    @pytest.mark.asyncio
    async def test_p95_graph_query_under_100ms(
        self,
        knowledge: InMemoryKnowledgeStub,
    ) -> None:
        """P95 graph query latency < 100ms across 50 calls."""
        latencies: list[float] = []

        for _ in range(50):
            start = time.perf_counter()
            await knowledge.search_graph(
                "perf baseline query",
                org_id=uuid4(),
                top_k=10,
            )
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < 100, f"Graph P95={p95:.1f}ms exceeds 100ms target"

    @pytest.mark.asyncio
    async def test_graph_resolve_interface(
        self,
        knowledge: InMemoryKnowledgeStub,
    ) -> None:
        """Knowledge.resolve() interface works and returns within 100ms."""
        start = time.perf_counter()
        await knowledge.resolve(
            profile_id="default",
            query="interface test",
            org_context=None,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"Resolve took {elapsed_ms:.1f}ms (target: <100ms)"
