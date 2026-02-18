"""Async database session factory with RLS context injection.

Wave 1-1: Infrastructure layer DB primitives.

Provides:
- create_db_engine(): AsyncEngine factory (asyncpg)
- create_session_factory(): async_sessionmaker bound to engine
- get_db_session(): async generator that injects SET LOCAL app.current_org_id
  before yielding the session, ensuring RLS policies are enforced.

All tables using RLS rely on current_setting('app.current_org_id')::uuid.
This module is the ONLY place that sets that GUC variable.

See: migrations/versions/001..004 for RLS policy definitions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    import uuid
    from collections.abc import AsyncGenerator


def create_db_engine(
    url: str,
    *,
    pool_size: int = 10,
    max_overflow: int = 20,
    echo: bool = False,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine for asyncpg.

    Args:
        url: Database URL (must use postgresql+asyncpg:// scheme).
        pool_size: Connection pool size.
        max_overflow: Max overflow connections beyond pool_size.
        echo: Whether to log SQL statements.

    Returns:
        Configured AsyncEngine instance.
    """
    return create_async_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=echo,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine.

    Sessions are configured with expire_on_commit=False to allow
    accessing attributes after commit without re-fetching.

    Args:
        engine: AsyncEngine to bind sessions to.

    Returns:
        Configured async_sessionmaker.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    org_id: uuid.UUID | None,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session with RLS context injected.

    Executes SET LOCAL app.current_org_id = '<org_id>' before yielding,
    which scopes all subsequent queries to the given tenant via RLS policies.

    SET LOCAL is transaction-scoped: the GUC resets when the transaction ends,
    preventing leakage across requests.

    Args:
        session_factory: async_sessionmaker to create the session.
        org_id: Organization UUID for RLS scoping. Required.

    Yields:
        AsyncSession with RLS context set.

    Raises:
        ValueError: If org_id is None (RLS bypass prevention).
    """
    if org_id is None:
        msg = "org_id is required for RLS-scoped database sessions"
        raise ValueError(msg)

    session = session_factory()
    try:
        await session.execute(
            sa.text("SET LOCAL app.current_org_id = :org_id"),
            {"org_id": str(org_id)},
        )
        yield session
    finally:
        await session.close()
