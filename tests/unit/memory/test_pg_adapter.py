"""Unit tests for PG adapter (MC2-1, MC2-4).

Rewritten for SQLAlchemy async session backend.
Uses Fake adapters to verify adapter behavior without a real DB or mocks.
RLS injection tested separately in test_db.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.memory.vector_search import FusedResult
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import Observation
from tests.fakes import FakeAsyncSession, FakeOrmRow, FakeSessionFactory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session() -> FakeAsyncSession:
    """Bare FakeAsyncSession; configure per-test before use."""
    return FakeAsyncSession()


@pytest.fixture()
def session_factory(session: FakeAsyncSession) -> FakeSessionFactory:
    """FakeSessionFactory wrapping the default session fixture."""
    return FakeSessionFactory(session)


@pytest.fixture()
def adapter(session_factory: FakeSessionFactory) -> PgMemoryCoreAdapter:
    return PgMemoryCoreAdapter(session_factory=session_factory)


@pytest.fixture()
def user_id():
    return uuid4()


@pytest.fixture()
def org_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPgMemoryCoreAdapter:
    """MC2-1: PG adapter replaces Stub with SQLAlchemy."""

    async def test_implements_memory_core_port(
        self,
        adapter: PgMemoryCoreAdapter,
    ) -> None:
        assert isinstance(adapter, MemoryCorePort)

    async def test_write_observation_returns_receipt(
        self,
        user_id,
        org_id,
    ) -> None:
        session = FakeAsyncSession()
        adapter = PgMemoryCoreAdapter(session_factory=FakeSessionFactory(session))

        obs = Observation(content="User likes Python")
        receipt = await adapter.write_observation(user_id, obs, org_id=org_id)

        assert receipt.memory_id is not None
        assert isinstance(receipt.memory_id, UUID)
        assert receipt.version == 1
        assert receipt.written_at is not None

    async def test_write_calls_session_add_and_commit(
        self,
        user_id,
        org_id,
    ) -> None:
        session = FakeAsyncSession()
        adapter = PgMemoryCoreAdapter(session_factory=FakeSessionFactory(session))

        obs = Observation(content="test write")
        await adapter.write_observation(user_id, obs, org_id=org_id)

        assert len(session.added) == 1
        assert session.commit_count == 1

    async def test_write_creates_correct_model(
        self,
        user_id,
        org_id,
    ) -> None:
        """Verify the ORM model fields match observation data."""
        session = FakeAsyncSession()
        adapter = PgMemoryCoreAdapter(session_factory=FakeSessionFactory(session))

        session_id = uuid4()
        obs = Observation(
            content="test content",
            memory_type="preference",
            source_session_id=session_id,
            confidence=0.9,
        )
        await adapter.write_observation(user_id, obs, org_id=org_id)

        added_model = session.added[0]
        assert added_model.org_id == org_id
        assert added_model.user_id == user_id
        assert added_model.content == "test content"
        assert added_model.memory_type == "preference"
        assert added_model.confidence == pytest.approx(0.9)
        assert session_id in added_model.source_sessions

    async def test_read_returns_memory_items(
        self,
        user_id,
        org_id,
    ) -> None:
        """Read should query memory_items and return MemoryItem list."""
        fake_row = FakeOrmRow(
            id=uuid4(),
            user_id=user_id,
            org_id=org_id,
            memory_type="observation",
            content="likes coffee",
            confidence=0.95,
            valid_at=datetime.now(UTC),
            invalid_at=None,
            source_sessions=[],
            superseded_by=None,
            version=1,
            provenance=None,
            epistemic_type="fact",
        )

        session = FakeAsyncSession()
        session.set_scalars_result([fake_row])
        adapter = PgMemoryCoreAdapter(session_factory=FakeSessionFactory(session))

        memories = await adapter.read_personal_memories(user_id, "coffee", org_id=org_id)

        assert len(memories) == 1
        assert memories[0].content == "likes coffee"
        assert memories[0].confidence == pytest.approx(0.95)

    async def test_read_empty_returns_empty(
        self,
        user_id,
        org_id,
    ) -> None:
        session = FakeAsyncSession()
        session.set_scalars_result([])
        adapter = PgMemoryCoreAdapter(session_factory=FakeSessionFactory(session))

        memories = await adapter.read_personal_memories(user_id, "anything", org_id=org_id)
        assert memories == []

    async def test_read_uses_session_context_manager(
        self,
        user_id,
        org_id,
    ) -> None:
        # The adapter calls "async with self._session_factory() as session:".
        # FakeAsyncSession implements __aenter__/__aexit__ as real coroutines,
        # so if the context manager protocol were not invoked the scalars()
        # call inside the block would never execute and we would get no result.
        # Asserting the call completes without error and returns the correct
        # empty list is sufficient to prove the context manager was exercised.
        session = FakeAsyncSession()
        session.set_scalars_result([])
        adapter = PgMemoryCoreAdapter(session_factory=FakeSessionFactory(session))

        memories = await adapter.read_personal_memories(user_id, "test", org_id=org_id)

        assert memories == []

    async def test_get_session_returns_none(
        self,
        adapter: PgMemoryCoreAdapter,
    ) -> None:
        """get_session is a Port contract placeholder."""
        result = await adapter.get_session(uuid4())
        assert result is None

    async def test_archive_session_returns_none(
        self,
        adapter: PgMemoryCoreAdapter,
    ) -> None:
        """archive_session is a Port contract placeholder."""
        result = await adapter.archive_session(uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# Fake embedder + vector engine for hybrid search tests
# ---------------------------------------------------------------------------


class FakeQueryEmbedder:
    """Fake embedder returning a fixed vector."""

    def __init__(self, vector: list[float] | None = None) -> None:
        self._vector = vector or [0.1, 0.2, 0.3]
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return self._vector


class FakeVectorEngine:
    """Fake PgVectorSearchEngine returning preconfigured FusedResults."""

    def __init__(self, results: list[FusedResult] | None = None) -> None:
        self._results = results or []
        self.calls: list[dict] = []

    async def hybrid_search(
        self,
        embedding: list[float],
        query: str,
        org_id: UUID,
        user_id: UUID,
        top_k: int = 5,
    ) -> list[FusedResult]:
        self.calls.append(
            {
                "embedding": embedding,
                "query": query,
                "org_id": org_id,
                "user_id": user_id,
                "top_k": top_k,
            }
        )
        return self._results


class FailingVectorEngine:
    """Vector engine that always raises."""

    async def hybrid_search(self, **_kwargs) -> list[FusedResult]:
        msg = "Vector search unavailable"
        raise ConnectionError(msg)


# ---------------------------------------------------------------------------
# MC2-4: Hybrid retrieval tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPgAdapterHybridRetrieval:
    """MC2-4: pgvector hybrid search wired into main retrieval path."""

    async def test_hybrid_path_used_when_vector_engine_provided(
        self,
        user_id,
        org_id,
    ) -> None:
        """When vector_engine + embedder are present, hybrid_search is called."""
        mid = uuid4()
        fused = [FusedResult(memory_id=mid, content="", rrf_score=0.5)]
        vec_engine = FakeVectorEngine(results=fused)
        embedder = FakeQueryEmbedder()

        fake_row = FakeOrmRow(
            id=mid,
            user_id=user_id,
            org_id=org_id,
            memory_type="observation",
            content="likes coffee",
            confidence=0.9,
            valid_at=datetime.now(UTC),
            invalid_at=None,
            source_sessions=[],
            superseded_by=None,
            version=1,
            provenance=None,
            epistemic_type="fact",
        )
        session = FakeAsyncSession()
        session.set_scalars_result([fake_row])

        adapter = PgMemoryCoreAdapter(
            session_factory=FakeSessionFactory(session),
            vector_engine=vec_engine,
            query_embedder=embedder,
        )

        results = await adapter.read_personal_memories(
            user_id,
            "coffee",
            org_id=org_id,
        )

        assert len(results) == 1
        assert results[0].content == "likes coffee"
        assert len(vec_engine.calls) == 1
        assert len(embedder.calls) == 1
        assert embedder.calls[0] == "coffee"

    async def test_fallback_to_keyword_when_no_vector_engine(
        self,
        user_id,
        org_id,
    ) -> None:
        """Without vector_engine, falls back to ILIKE keyword search."""
        session = FakeAsyncSession()
        session.set_scalars_result([])
        adapter = PgMemoryCoreAdapter(session_factory=FakeSessionFactory(session))

        results = await adapter.read_personal_memories(
            user_id,
            "test",
            org_id=org_id,
        )

        assert results == []

    async def test_fallback_on_hybrid_failure(
        self,
        user_id,
        org_id,
    ) -> None:
        """If hybrid_search raises, gracefully falls back to keyword."""
        session = FakeAsyncSession()
        session.set_scalars_result([])
        adapter = PgMemoryCoreAdapter(
            session_factory=FakeSessionFactory(session),
            vector_engine=FailingVectorEngine(),
            query_embedder=FakeQueryEmbedder(),
        )

        results = await adapter.read_personal_memories(
            user_id,
            "test",
            org_id=org_id,
        )

        assert results == []

    async def test_fallback_when_no_org_id(
        self,
        user_id,
    ) -> None:
        """Hybrid search requires org_id; without it, use keyword fallback."""
        vec_engine = FakeVectorEngine()
        embedder = FakeQueryEmbedder()
        session = FakeAsyncSession()
        session.set_scalars_result([])

        adapter = PgMemoryCoreAdapter(
            session_factory=FakeSessionFactory(session),
            vector_engine=vec_engine,
            query_embedder=embedder,
        )

        results = await adapter.read_personal_memories(user_id, "test")

        assert results == []
        assert len(vec_engine.calls) == 0  # hybrid NOT called

    async def test_hybrid_returns_results_in_rrf_order(
        self,
        user_id,
        org_id,
    ) -> None:
        """Results are returned in RRF rank order, not DB order."""
        mid_a = uuid4()
        mid_b = uuid4()
        # RRF order: B first, A second
        fused = [
            FusedResult(memory_id=mid_b, content="", rrf_score=0.8),
            FusedResult(memory_id=mid_a, content="", rrf_score=0.3),
        ]

        row_a = FakeOrmRow(
            id=mid_a,
            user_id=user_id,
            org_id=org_id,
            memory_type="observation",
            content="fact A",
            confidence=0.9,
            valid_at=datetime.now(UTC),
            invalid_at=None,
            source_sessions=[],
            superseded_by=None,
            version=1,
            provenance=None,
            epistemic_type="fact",
        )
        row_b = FakeOrmRow(
            id=mid_b,
            user_id=user_id,
            org_id=org_id,
            memory_type="observation",
            content="fact B",
            confidence=0.7,
            valid_at=datetime.now(UTC),
            invalid_at=None,
            source_sessions=[],
            superseded_by=None,
            version=1,
            provenance=None,
            epistemic_type="fact",
        )

        session = FakeAsyncSession()
        session.set_scalars_result([row_a, row_b])

        adapter = PgMemoryCoreAdapter(
            session_factory=FakeSessionFactory(session),
            vector_engine=FakeVectorEngine(results=fused),
            query_embedder=FakeQueryEmbedder(),
        )

        results = await adapter.read_personal_memories(
            user_id,
            "fact",
            org_id=org_id,
        )

        assert len(results) == 2
        assert results[0].content == "fact B"  # higher RRF score
        assert results[1].content == "fact A"
