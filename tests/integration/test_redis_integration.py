"""Integration test for Redis storage adapter (I2-1).

Connects to live Redis via Docker on port 6380.
Uses DB 15 with test prefix to avoid data conflicts.
"""

from __future__ import annotations

import os

import pytest

from src.infra.cache.redis import RedisStorageAdapter

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6380/15")


@pytest.fixture()
async def adapter():
    a = RedisStorageAdapter(REDIS_URL)
    yield a
    # Cleanup: delete test keys
    client = await a._get_client()
    keys = await client.keys("inttest:*")
    if keys:
        await client.delete(*keys)
    await a.close()


def _can_connect() -> bool:
    """Check if Redis is reachable."""
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


@pytest.mark.integration
@skip_no_redis
class TestRedisIntegration:
    """Integration: RedisStorageAdapter against live Redis."""

    async def test_put_and_get(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("inttest:k1", {"hello": "world"})
        result = await adapter.get("inttest:k1")
        assert result == {"hello": "world"}

    async def test_delete(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("inttest:del", "value")
        await adapter.delete("inttest:del")
        assert await adapter.get("inttest:del") is None

    async def test_list_keys(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("inttest:a", 1)
        await adapter.put("inttest:b", 2)
        keys = await adapter.list_keys("inttest:*")
        assert "inttest:a" in keys
        assert "inttest:b" in keys

    async def test_ttl(self, adapter: RedisStorageAdapter) -> None:
        import asyncio

        await adapter.put("inttest:ttl", "val", ttl=1)
        assert await adapter.get("inttest:ttl") == "val"
        await asyncio.sleep(1.1)
        assert await adapter.get("inttest:ttl") is None
