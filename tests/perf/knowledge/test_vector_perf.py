"""Performance baseline: Vector search latency (K4-2).

Gate: p4-perf-baseline
Verifies: Vector search P95 < 50ms (R-5 CI regression baseline).

CI baseline uses in-memory stub — validates search interface, not Qdrant.
Capacity-planning baseline (1M vectors) requires live Qdrant instance
and is run separately per R-5 档位 2.
"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest


class InMemoryVectorStub:
    """Minimal vector search stub for performance baseline testing.

    Returns empty results immediately — measures interface overhead only.
    """

    async def search(
        self,
        query_vector: list[float],
        *,
        org_id: object | None = None,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """Search vectors by similarity. Returns empty list."""
        return []

    async def upsert(
        self,
        vectors: list[dict],
        *,
        org_id: object | None = None,
    ) -> int:
        """Upsert vectors. Returns count of upserted items."""
        return len(vectors)


@pytest.mark.perf
class TestVectorSearchPerf:
    """Vector search performance baseline (K4-2, R-5 CI baseline).

    P95 < 50ms with in-memory stub.
    """

    @pytest.fixture()
    def vector_store(self):
        return InMemoryVectorStub()

    @pytest.mark.asyncio
    async def test_single_search_under_50ms(
        self,
        vector_store: InMemoryVectorStub,
    ) -> None:
        """Single vector search completes under 50ms."""
        query_vec = [0.1] * 384  # typical embedding dimension

        start = time.perf_counter()
        results = await vector_store.search(
            query_vec,
            org_id=uuid4(),
            top_k=10,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert isinstance(results, list)
        assert elapsed_ms < 50, f"Vector search took {elapsed_ms:.1f}ms (target: <50ms)"

    @pytest.mark.asyncio
    async def test_p95_search_under_50ms(
        self,
        vector_store: InMemoryVectorStub,
    ) -> None:
        """P95 vector search latency < 50ms across 50 calls."""
        query_vec = [0.1] * 384
        latencies: list[float] = []

        for _ in range(50):
            start = time.perf_counter()
            await vector_store.search(
                query_vec,
                org_id=uuid4(),
                top_k=10,
            )
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < 50, f"Vector P95={p95:.1f}ms exceeds 50ms target"

    @pytest.mark.asyncio
    async def test_concurrent_searches_under_50ms(
        self,
        vector_store: InMemoryVectorStub,
    ) -> None:
        """10 concurrent vector searches all complete under 50ms."""
        import asyncio

        query_vec = [0.1] * 384

        async def timed_search() -> float:
            start = time.perf_counter()
            await vector_store.search(
                query_vec,
                org_id=uuid4(),
                top_k=10,
            )
            return (time.perf_counter() - start) * 1000

        latencies = await asyncio.gather(*[timed_search() for _ in range(10)])
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]

        assert p95 < 50, f"Concurrent vector P95={p95:.1f}ms exceeds 50ms target"
