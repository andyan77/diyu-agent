"""Tests for async DB session factory with RLS context injection.

Wave 1-1: Verifies that:
- create_db_engine() returns an AsyncEngine configured for asyncpg
- get_db_session() yields an AsyncSession
- get_db_session() executes SET LOCAL app.current_org_id before yielding
- get_db_session() raises if org_id is missing
"""

from __future__ import annotations

import uuid

import pytest

from tests.fakes import FakeAsyncSession, FakeSessionFactory


@pytest.mark.unit
class TestCreateDbEngine:
    """Verify engine factory produces an async engine."""

    def test_returns_async_engine(self) -> None:
        from src.infra.db import create_db_engine

        engine = create_db_engine("postgresql+asyncpg://u:p@localhost/test")
        # Should have async engine attributes
        assert hasattr(engine, "begin")
        assert hasattr(engine, "dispose")
        # URL scheme should be asyncpg
        assert "asyncpg" in str(engine.url)

    def test_pool_size_configurable(self) -> None:
        from src.infra.db import create_db_engine

        engine = create_db_engine(
            "postgresql+asyncpg://u:p@localhost/test",
            pool_size=5,
            max_overflow=10,
        )
        assert engine.pool.size() == 5

    def test_echo_defaults_to_false(self) -> None:
        from src.infra.db import create_db_engine

        engine = create_db_engine("postgresql+asyncpg://u:p@localhost/test")
        assert engine.echo is False


@pytest.mark.unit
class TestCreateSessionFactory:
    """Verify session factory configuration."""

    def test_returns_async_sessionmaker(self) -> None:
        from src.infra.db import create_db_engine, create_session_factory

        engine = create_db_engine("postgresql+asyncpg://u:p@localhost/test")
        factory = create_session_factory(engine)
        # Should be callable (sessionmaker)
        assert callable(factory)

    def test_session_expire_on_commit_false(self) -> None:
        from src.infra.db import create_db_engine, create_session_factory

        engine = create_db_engine("postgresql+asyncpg://u:p@localhost/test")
        factory = create_session_factory(engine)
        assert factory.kw.get("expire_on_commit") is False


@pytest.mark.unit
class TestGetDbSession:
    """Verify RLS context injection in session lifecycle."""

    @pytest.mark.asyncio
    async def test_executes_set_local_with_org_id(self) -> None:
        """Session must SET LOCAL app.current_org_id before yielding."""
        from src.infra.db import get_db_session

        org_id = uuid.uuid4()

        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)

        async for yielded_session in get_db_session(session_factory=factory, org_id=org_id):
            assert yielded_session is session
            break

        # Verify SET LOCAL was called
        assert len(session.execute_calls) == 1
        sql_text = str(session.execute_calls[0][0])
        assert "SET LOCAL" in sql_text
        assert "app.current_org_id" in sql_text

    @pytest.mark.asyncio
    async def test_raises_without_org_id(self) -> None:
        """Must reject sessions without org_id (RLS bypass prevention)."""
        from src.infra.db import get_db_session

        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)

        with pytest.raises(ValueError, match="org_id"):
            async for _session in get_db_session(session_factory=factory, org_id=None):
                pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_session_closed_on_exit(self) -> None:
        """Session must be closed after context manager exits."""
        from src.infra.db import get_db_session

        org_id = uuid.uuid4()
        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)

        async for _session in get_db_session(session_factory=factory, org_id=org_id):
            pass

        assert session.close_count == 1

    @pytest.mark.asyncio
    async def test_session_closed_on_exception(self) -> None:
        """Session must be closed even if caller raises."""
        from src.infra.db import get_db_session

        org_id = uuid.uuid4()
        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)

        gen = get_db_session(session_factory=factory, org_id=org_id)
        _session = await gen.__anext__()
        # Simulate caller exception by throwing into the generator
        with pytest.raises(RuntimeError, match="boom"):
            await gen.athrow(RuntimeError("boom"))

        assert session.close_count == 1
