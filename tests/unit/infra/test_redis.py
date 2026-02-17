"""Unit tests for Redis storage adapter (I2-1).

Uses FakeRedis in-memory implementation to test RedisStorageAdapter
without requiring a real Redis connection. Complies with no-mock policy.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from src.infra.cache.redis import RedisStorageAdapter
from src.ports.storage_port import StoragePort

# ---------------------------------------------------------------------------
# FakeRedis: thin in-memory stub (no unittest.mock)
# ---------------------------------------------------------------------------


class FakeRedis:
    """In-memory Redis stub for unit testing."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self._expiry: dict[str, float] = {}

    def _evict(self, key: str) -> None:
        if key in self._expiry and time.monotonic() > self._expiry[key]:
            self._store.pop(key, None)
            self._expiry.pop(key, None)

    async def set(self, key: str, value: bytes, *, ex: int | None = None) -> None:
        self._store[key] = value
        if ex is not None:
            self._expiry[key] = time.monotonic() + ex
        else:
            self._expiry.pop(key, None)

    async def get(self, key: str) -> bytes | None:
        self._evict(key)
        return self._store.get(key)

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                self._expiry.pop(k, None)
                count += 1
        return count

    async def keys(self, pattern: str = "*") -> list[bytes]:
        now = time.monotonic()
        expired = [k for k, exp in self._expiry.items() if now > exp]
        for k in expired:
            self._store.pop(k, None)
            self._expiry.pop(k, None)

        if pattern == "*":
            return [k.encode() for k in self._store]

        import fnmatch

        return [k.encode() for k in self._store if fnmatch.fnmatch(k, pattern)]

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture()
def adapter(fake_redis: FakeRedis) -> RedisStorageAdapter:
    a = RedisStorageAdapter("redis://localhost:6379")
    a._client = fake_redis  # type: ignore[assignment]
    return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRedisStorageAdapterPhase2:
    """RedisStorageAdapter unit tests (phase2)."""

    async def test_implements_storage_port(self, adapter: RedisStorageAdapter) -> None:
        assert isinstance(adapter, StoragePort)

    async def test_put_and_get_string(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("k", "hello")
        assert await adapter.get("k") == "hello"

    async def test_put_and_get_dict(self, adapter: RedisStorageAdapter) -> None:
        data: dict[str, Any] = {"a": 1, "nested": {"b": [2, 3]}}
        await adapter.put("dk", data)
        assert await adapter.get("dk") == data

    async def test_put_and_get_list(self, adapter: RedisStorageAdapter) -> None:
        data = [1, "two", {"three": 3}]
        await adapter.put("lk", data)
        assert await adapter.get("lk") == data

    async def test_put_and_get_int(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("ik", 42)
        assert await adapter.get("ik") == 42

    async def test_get_nonexistent_returns_none(self, adapter: RedisStorageAdapter) -> None:
        assert await adapter.get("missing") is None

    async def test_delete_removes_key(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("del_me", "v")
        assert await adapter.get("del_me") == "v"
        await adapter.delete("del_me")
        assert await adapter.get("del_me") is None

    async def test_delete_nonexistent_is_noop(self, adapter: RedisStorageAdapter) -> None:
        await adapter.delete("nope")  # should not raise

    async def test_list_keys_all(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("a", 1)
        await adapter.put("b", 2)
        keys = await adapter.list_keys("*")
        assert set(keys) == {"a", "b"}

    async def test_list_keys_pattern(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("session:1", "s1")
        await adapter.put("session:2", "s2")
        await adapter.put("cache:x", "cx")
        keys = await adapter.list_keys("session:*")
        assert set(keys) == {"session:1", "session:2"}

    async def test_ttl_expires(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("ttl_k", "val", ttl=1)
        assert await adapter.get("ttl_k") == "val"
        await asyncio.sleep(1.1)
        assert await adapter.get("ttl_k") is None

    async def test_ttl_not_yet_expired(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("ttl_k2", "val", ttl=5)
        await asyncio.sleep(0.1)
        assert await adapter.get("ttl_k2") == "val"

    async def test_session_lifecycle(self, adapter: RedisStorageAdapter) -> None:
        """Full session store / retrieve / list / delete cycle."""
        session = {
            "user_id": "u1",
            "org_id": "o1",
            "perms": ["read", "write"],
        }
        await adapter.put("session:s1", session, ttl=60)
        assert await adapter.get("session:s1") == session

        await adapter.put("session:s2", {"user_id": "u2"}, ttl=60)
        keys = await adapter.list_keys("session:*")
        assert len(keys) == 2

        await adapter.delete("session:s1")
        assert await adapter.get("session:s1") is None

    async def test_overwrite_existing_key(self, adapter: RedisStorageAdapter) -> None:
        await adapter.put("ow", "first")
        await adapter.put("ow", "second")
        assert await adapter.get("ow") == "second"
