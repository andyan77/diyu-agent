"""Unit tests for PgVectorSearchEngine (MC2-4 pgvector backend).

Tests PgVectorSearchEngine using Fake adapters (no unittest.mock).
Verifies: search_by_embedding, search_by_keyword, hybrid_search, empty results.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.fakes import FakeAsyncSession, FakeOrmRow, FakeSessionFactory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def org_id():
    return uuid4()


@pytest.fixture()
def user_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPgVectorSearchEngine:
    """MC2-4: PgVector-backed search engine tests."""

    async def test_search_by_embedding_executes_sql(self, org_id, user_id) -> None:
        """search_by_embedding executes a SQL query with cosine distance operator."""
        from src.memory.vector_search import PgVectorSearchEngine

        mid = uuid4()
        row = FakeOrmRow(id=mid, content="hello world", distance=0.05)

        session = FakeAsyncSession()
        session.set_execute_result(fetchall_rows=[row])
        factory = FakeSessionFactory(session)

        engine = PgVectorSearchEngine(session_factory=factory)
        embedding = [0.1, 0.2, 0.3]

        results = await engine.search_by_embedding(
            embedding=embedding, org_id=org_id, user_id=user_id, top_k=5
        )

        # execute was called once
        assert len(session.execute_calls) == 1
        sql_text = str(session.execute_calls[0][0])
        # The SQL string must contain cosine distance operator or embedding reference
        assert "<=>" in sql_text or "embedding" in sql_text.lower()

        assert len(results) == 1
        assert results[0][0] == mid

    async def test_search_by_embedding_empty_returns_empty(self, org_id, user_id) -> None:
        """search_by_embedding returns [] when no rows match."""
        from src.memory.vector_search import PgVectorSearchEngine

        session = FakeAsyncSession()
        session.set_execute_result(fetchall_rows=[])
        factory = FakeSessionFactory(session)

        engine = PgVectorSearchEngine(session_factory=factory)
        results = await engine.search_by_embedding(
            embedding=[0.1, 0.2], org_id=org_id, user_id=user_id, top_k=5
        )
        assert results == []

    async def test_search_by_keyword_uses_ilike(self, org_id, user_id) -> None:
        """search_by_keyword executes SQL with ILIKE on content column."""
        from src.memory.vector_search import PgVectorSearchEngine

        mid = uuid4()
        row = FakeOrmRow(id=mid, content="python is great", distance=1.0)

        session = FakeAsyncSession()
        session.set_execute_result(fetchall_rows=[row])
        factory = FakeSessionFactory(session)

        engine = PgVectorSearchEngine(session_factory=factory)
        results = await engine.search_by_keyword(
            query="python", org_id=org_id, user_id=user_id, top_k=5
        )

        assert len(session.execute_calls) == 1
        sql_text = str(session.execute_calls[0][0]).upper()
        assert "ILIKE" in sql_text

        assert len(results) == 1
        assert results[0][0] == mid

    async def test_search_by_keyword_empty_returns_empty(self, org_id, user_id) -> None:
        """search_by_keyword returns [] when no rows match."""
        from src.memory.vector_search import PgVectorSearchEngine

        session = FakeAsyncSession()
        session.set_execute_result(fetchall_rows=[])
        factory = FakeSessionFactory(session)

        engine = PgVectorSearchEngine(session_factory=factory)
        results = await engine.search_by_keyword(
            query="nonexistent", org_id=org_id, user_id=user_id, top_k=5
        )
        assert results == []

    async def test_hybrid_search_calls_both_methods(self, org_id, user_id) -> None:
        """hybrid_search calls both search_by_embedding and search_by_keyword."""
        from src.memory.vector_search import FusedResult, PgVectorSearchEngine

        mid1 = uuid4()
        mid2 = uuid4()
        row1 = FakeOrmRow(id=mid1, content="python vector", distance=0.05)
        row2 = FakeOrmRow(id=mid2, content="python keyword", distance=1.0)

        # hybrid_search opens two separate session contexts (one per sub-search)
        session1 = FakeAsyncSession()
        session1.set_execute_result(fetchall_rows=[row1])
        session2 = FakeAsyncSession()
        session2.set_execute_result(fetchall_rows=[row2])

        factory = FakeSessionFactory.sequence([session1, session2])
        engine = PgVectorSearchEngine(session_factory=factory)

        results = await engine.hybrid_search(
            embedding=[0.1, 0.2, 0.3],
            query="python",
            org_id=org_id,
            user_id=user_id,
            top_k=5,
        )

        # Each sub-search must have issued exactly one execute call
        assert len(session1.execute_calls) == 1
        assert len(session2.execute_calls) == 1
        assert len(results) >= 1
        assert all(isinstance(r, FusedResult) for r in results)

    async def test_hybrid_search_empty_both_returns_empty(self, org_id, user_id) -> None:
        """hybrid_search returns [] when both sub-searches return nothing."""
        from src.memory.vector_search import PgVectorSearchEngine

        session1 = FakeAsyncSession()
        session1.set_execute_result(fetchall_rows=[])
        session2 = FakeAsyncSession()
        session2.set_execute_result(fetchall_rows=[])

        factory = FakeSessionFactory.sequence([session1, session2])
        engine = PgVectorSearchEngine(session_factory=factory)

        results = await engine.hybrid_search(
            embedding=[0.1, 0.2],
            query="nothing",
            org_id=org_id,
            user_id=user_id,
            top_k=5,
        )
        assert results == []

    async def test_search_by_embedding_respects_top_k(self, org_id, user_id) -> None:
        """search_by_embedding honours the top_k limit via SQL LIMIT."""
        from src.memory.vector_search import PgVectorSearchEngine

        rows = [FakeOrmRow(id=uuid4(), content=f"item {i}", distance=0.01 * i) for i in range(3)]

        session = FakeAsyncSession()
        session.set_execute_result(fetchall_rows=rows)
        factory = FakeSessionFactory(session)

        engine = PgVectorSearchEngine(session_factory=factory)
        results = await engine.search_by_embedding(
            embedding=[0.1], org_id=org_id, user_id=user_id, top_k=3
        )

        sql_text = str(session.execute_calls[0][0]).upper()
        assert "LIMIT" in sql_text
        assert len(results) == 3

    async def test_search_by_keyword_respects_top_k(self, org_id, user_id) -> None:
        """search_by_keyword honours the top_k limit via SQL LIMIT."""
        from src.memory.vector_search import PgVectorSearchEngine

        rows = [FakeOrmRow(id=uuid4(), content=f"item {i}", distance=1.0) for i in range(2)]

        session = FakeAsyncSession()
        session.set_execute_result(fetchall_rows=rows)
        factory = FakeSessionFactory(session)

        engine = PgVectorSearchEngine(session_factory=factory)
        results = await engine.search_by_keyword(
            query="item", org_id=org_id, user_id=user_id, top_k=2
        )

        sql_text = str(session.execute_calls[0][0]).upper()
        assert "LIMIT" in sql_text
        assert len(results) == 2
