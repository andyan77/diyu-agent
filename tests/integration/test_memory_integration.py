"""Integration test for Memory Core adapter (MC2-1).

Tests PgMemoryCoreAdapter using Fake session adapters.
Real DB integration is covered by test_db.py with live PostgreSQL.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.shared.types import Observation
from tests.fakes import FakeAsyncSession, FakeOrmRow, FakeSessionFactory


@pytest.fixture()
def session_factory() -> FakeSessionFactory:
    """Fake async_sessionmaker for integration tests."""
    return FakeSessionFactory(FakeAsyncSession())


@pytest.fixture()
def adapter(session_factory: FakeSessionFactory) -> PgMemoryCoreAdapter:
    return PgMemoryCoreAdapter(session_factory=session_factory)


@pytest.mark.integration
class TestMemoryIntegration:
    """Integration: MemoryCore adapter with Fake session factory."""

    @pytest.mark.asyncio()
    async def test_write_and_read(self) -> None:
        user_id = uuid4()
        org_id = uuid4()

        write_session = FakeAsyncSession()

        fake_row = FakeOrmRow(
            id=uuid4(),
            user_id=user_id,
            org_id=org_id,
            memory_type="observation",
            content="User likes integration tests",
            confidence=0.8,
            valid_at=datetime.now(UTC),
            invalid_at=None,
            source_sessions=[],
            superseded_by=None,
            version=1,
            provenance=None,
            epistemic_type="fact",
        )

        read_session = FakeAsyncSession()
        read_session.set_scalars_result([fake_row])

        factory = FakeSessionFactory.sequence([write_session, read_session])
        adapter = PgMemoryCoreAdapter(session_factory=factory)

        obs = Observation(content="User likes integration tests")
        receipt = await adapter.write_observation(user_id, obs, org_id=org_id)

        assert receipt.version == 1
        assert receipt.memory_id is not None

        memories = await adapter.read_personal_memories(user_id, "integration", org_id=org_id)
        assert len(memories) == 1
        assert "integration" in memories[0].content

    @pytest.mark.asyncio()
    async def test_get_session_returns_none(self, adapter: PgMemoryCoreAdapter) -> None:
        session_id = uuid4()
        result = await adapter.get_session(session_id)
        assert result is None

    @pytest.mark.asyncio()
    async def test_archive_session_returns_none(self, adapter: PgMemoryCoreAdapter) -> None:
        session_id = uuid4()
        result = await adapter.archive_session(session_id)
        assert result is None

    @pytest.mark.asyncio()
    async def test_write_requires_org_id(self, adapter: PgMemoryCoreAdapter) -> None:
        """write_observation raises ValueError when org_id is not provided."""
        user_id = uuid4()
        obs = Observation(content="test")
        with pytest.raises(ValueError, match="org_id is required"):
            await adapter.write_observation(user_id, obs)
