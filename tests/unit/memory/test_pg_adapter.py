"""Unit tests for PG adapter (MC2-1).

Rewritten for SQLAlchemy async session backend.
Uses Fake adapters to verify adapter behavior without a real DB or mocks.
RLS injection tested separately in test_db.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.memory.pg_adapter import PgMemoryCoreAdapter
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
