"""Unit tests for pgvector semantic search (MC2-4).

Tests in-memory vector search engine with cosine similarity and RRF fusion.
Complies with no-mock policy.
"""

from __future__ import annotations

import math
from uuid import uuid4

import pytest

from src.memory.vector_search import (
    FusedResult,
    SearchResult,
    VectorSearchEngine,
    cosine_similarity,
    rrf_fuse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine() -> VectorSearchEngine:
    return VectorSearchEngine()


def _make_embedding(dims: int = 8, seed: float = 1.0) -> list[float]:
    """Create a simple deterministic embedding for testing."""
    return [math.sin(seed * (i + 1)) for i in range(dims)]


# ---------------------------------------------------------------------------
# Tests: cosine_similarity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCosineSimilarity:
    """Cosine similarity function tests."""

    def test_identical_vectors(self) -> None:
        v = [1.0, 2.0, 3.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(cosine_similarity(a, b)) < 1e-9

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) + 1.0) < 1e-9

    def test_dimension_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="mismatch"):
            cosine_similarity([1.0], [1.0, 2.0])

    def test_zero_vector(self) -> None:
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


# ---------------------------------------------------------------------------
# Tests: RRF fusion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRRFFusion:
    """RRF fusion ranking tests."""

    def test_single_list(self) -> None:
        mid = uuid4()
        results = [
            SearchResult(memory_id=mid, content="test", score=0.9, source="vector"),
        ]
        fused = rrf_fuse([results], top_n=1)
        assert len(fused) == 1
        assert fused[0].memory_id == mid

    def test_two_lists_boost_shared_item(self) -> None:
        shared = uuid4()
        only_vec = uuid4()
        only_kw = uuid4()

        vec_list = [
            SearchResult(memory_id=shared, content="shared", score=0.9, source="vector"),
            SearchResult(memory_id=only_vec, content="vec", score=0.8, source="vector"),
        ]
        kw_list = [
            SearchResult(memory_id=shared, content="shared", score=0.7, source="keyword"),
            SearchResult(memory_id=only_kw, content="kw", score=0.6, source="keyword"),
        ]

        fused = rrf_fuse([vec_list, kw_list], top_n=3)
        assert fused[0].memory_id == shared
        assert fused[0].vector_rank == 1
        assert fused[0].keyword_rank == 1

    def test_top_n_limit(self) -> None:
        results = [
            SearchResult(memory_id=uuid4(), content=f"r{i}", score=0.5, source="vector")
            for i in range(10)
        ]
        fused = rrf_fuse([results], top_n=3)
        assert len(fused) == 3


# ---------------------------------------------------------------------------
# Tests: VectorSearchEngine
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVectorSearchEngine:
    """MC2-4: pgvector semantic search (in-memory)."""

    def test_index_and_search(self, engine: VectorSearchEngine) -> None:
        mid = uuid4()
        emb = _make_embedding(seed=1.0)
        engine.index(mid, "test content", emb)

        results = engine.search_vector(emb, top_k=1)
        assert len(results) == 1
        assert results[0].memory_id == mid
        assert results[0].score > 0.99  # same vector

    def test_search_ranks_by_similarity(
        self,
        engine: VectorSearchEngine,
    ) -> None:
        query_emb = _make_embedding(seed=1.0)

        close_id = uuid4()
        far_id = uuid4()
        engine.index(close_id, "close item", _make_embedding(seed=1.01))
        engine.index(far_id, "far item", _make_embedding(seed=5.0))

        results = engine.search_vector(query_emb, top_k=2)
        assert results[0].memory_id == close_id

    def test_keyword_search(self, engine: VectorSearchEngine) -> None:
        mid = uuid4()
        engine.index(mid, "python programming language", _make_embedding())

        results = engine.search_keyword("python")
        assert len(results) == 1
        assert results[0].memory_id == mid

    def test_keyword_search_no_match(
        self,
        engine: VectorSearchEngine,
    ) -> None:
        engine.index(uuid4(), "java spring boot", _make_embedding())
        results = engine.search_keyword("python")
        assert results == []

    def test_hybrid_search_combines_sources(
        self,
        engine: VectorSearchEngine,
    ) -> None:
        query_emb = _make_embedding(seed=1.0)

        m1 = uuid4()
        m2 = uuid4()
        engine.index(m1, "python is great", _make_embedding(seed=1.01))
        engine.index(m2, "java is also good", _make_embedding(seed=5.0))

        results = engine.hybrid_search("python", query_emb, top_k=2)
        assert len(results) >= 1
        assert isinstance(results[0], FusedResult)

    def test_top5_recall(self, engine: VectorSearchEngine) -> None:
        """Top-5 recall >= 80%: 4/5 relevant items must appear in top 5."""
        query_emb = _make_embedding(seed=1.0)

        relevant_ids = []
        for i in range(5):
            mid = uuid4()
            relevant_ids.append(mid)
            engine.index(mid, f"relevant item {i}", _make_embedding(seed=1.0 + i * 0.01))

        for i in range(20):
            engine.index(uuid4(), f"irrelevant {i}", _make_embedding(seed=10.0 + i))

        results = engine.search_vector(query_emb, top_k=5)
        result_ids = {r.memory_id for r in results}
        recall = len(result_ids & set(relevant_ids)) / len(relevant_ids)
        assert recall >= 0.8, f"Top-5 recall {recall:.0%} < 80%"
