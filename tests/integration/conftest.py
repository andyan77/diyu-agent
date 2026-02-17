"""Integration test conftest - fixtures requiring live services.

These fixtures connect to real PostgreSQL, Redis, and the FastAPI server.
They are skeleton stubs to be implemented by Phase 2 task cards.

Requires:
    - PostgreSQL (diyu_test database)
    - Redis (DB 15, prefix diyu_test:)
    - FastAPI test server

Usage:
    pytest tests/integration/ -m integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from httpx import AsyncClient
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
async def live_db() -> AsyncGenerator[AsyncSession, None]:
    """Async SQLAlchemy session connected to diyu_test database.

    Implementation deferred to task card I2-4 (conversation_events table).
    """
    pytest.skip("live_db not yet implemented (Phase 2 task card I2-4)")
    yield  # type: ignore[misc]


@pytest.fixture(scope="session")
async def live_redis() -> AsyncGenerator[Redis, None]:
    """Async Redis client on DB 15 with diyu_test: prefix.

    Implementation deferred to task card I2-1 (Redis cache + session).
    """
    pytest.skip("live_redis not yet implemented (Phase 2 task card I2-1)")
    yield  # type: ignore[misc]


@pytest.fixture
async def live_server(live_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient pointed at a running FastAPI test instance.

    Implementation deferred to task card G2-1 (Conversation REST API).
    """
    pytest.skip("live_server not yet implemented (Phase 2 task card G2-1)")
    yield  # type: ignore[misc]
