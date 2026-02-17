"""Redis implementation of StoragePort for caching and session management.

Task card: I2-1
- Write to cache -> TTL expiration -> auto-cleanup
- Session management unified in Redis
- Non-persistent cache (losable; rebuilding acceptable)
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from src.ports.storage_port import StoragePort


class RedisStorageAdapter(StoragePort):
    """Redis adapter implementing the StoragePort interface.

    Provides async cache storage with TTL support and JSON serialization.
    Suitable for session management and general caching needs.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        self._redis_url = redis_url
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=False)  # type: ignore[no-untyped-call]
        return self._client

    async def put(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Store a value with optional TTL (seconds)."""
        client = await self._get_client()
        encoded = json.dumps(value).encode("utf-8")
        if ttl is not None:
            await client.set(key, encoded, ex=ttl)
        else:
            await client.set(key, encoded)

    async def get(self, key: str) -> Any | None:
        """Retrieve a value by key, returning None if absent or expired."""
        client = await self._get_client()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def delete(self, key: str) -> None:
        """Delete a value by key (no-op if absent)."""
        client = await self._get_client()
        await client.delete(key)

    async def list_keys(self, pattern: str) -> list[str]:
        """List keys matching a glob pattern."""
        client = await self._get_client()
        raw_keys = await client.keys(pattern)
        return [k.decode("utf-8") if isinstance(k, bytes) else k for k in raw_keys]

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
