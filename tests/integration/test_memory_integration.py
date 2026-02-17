"""Integration test for Memory Core adapter with Redis storage (MC2-1).

Tests PgMemoryCoreAdapter using RedisStorageAdapter against live Redis.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from src.infra.cache.redis import RedisStorageAdapter
from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.shared.types import Observation

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/15")


def _can_connect() -> bool:
    import socket

    try:
        host = "localhost"
        port = int(REDIS_URL.split(":")[-1].split("/")[0])
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        return True
    except (OSError, ValueError):
        return False


skip_no_redis = pytest.mark.skipif(
    not _can_connect(),
    reason="Redis not available",
)


@pytest.fixture()
async def adapter():
    storage = RedisStorageAdapter(REDIS_URL)
    a = PgMemoryCoreAdapter(storage)  # type: ignore[arg-type]
    yield a
    # Cleanup
    client = await storage._get_client()
    keys = await client.keys("memory:*")
    if keys:
        await client.delete(*keys)
    session_keys = await client.keys("session:*")
    if session_keys:
        await client.delete(*session_keys)
    await storage.close()


@pytest.mark.integration
@skip_no_redis
class TestMemoryIntegration:
    """Integration: MemoryCore adapter with live Redis."""

    async def test_write_and_read(self, adapter: PgMemoryCoreAdapter) -> None:
        user_id = uuid4()
        obs = Observation(content="User likes integration tests")
        receipt = await adapter.write_observation(user_id, obs)

        assert receipt.version == 1

        memories = await adapter.read_personal_memories(user_id, "integration")
        assert len(memories) == 1
        assert "integration" in memories[0].content

    async def test_session_lifecycle(self, adapter: PgMemoryCoreAdapter) -> None:
        session_id = uuid4()
        # Store session via underlying storage
        storage = adapter._storage
        await storage.put(f"session:{session_id}", {"messages": ["hello"]})

        session = await adapter.get_session(session_id)
        assert session is not None

        archived = await adapter.archive_session(session_id)
        assert archived is not None
        assert archived["archived"] is True
