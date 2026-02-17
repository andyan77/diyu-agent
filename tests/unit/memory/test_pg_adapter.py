"""Unit tests for PG adapter (MC2-1).

Uses FakeStoragePort (async in-memory). No external dependencies.
Complies with no-mock policy.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from src.memory.pg_adapter import PgMemoryCoreAdapter
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import Observation

# ---------------------------------------------------------------------------
# FakeStoragePort: async in-memory stub
# ---------------------------------------------------------------------------


class FakeStoragePort:
    """Async in-memory storage for testing MemoryCorePort adapters."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._store[key] = value

    async def get(self, key: str) -> Any | None:
        return self._store.get(key)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def list_keys(self, pattern: str) -> list[str]:
        import fnmatch

        return [k for k in self._store if fnmatch.fnmatch(k, pattern)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def storage() -> FakeStoragePort:
    return FakeStoragePort()


@pytest.fixture()
def adapter(storage: FakeStoragePort) -> PgMemoryCoreAdapter:
    return PgMemoryCoreAdapter(storage)  # type: ignore[arg-type]


@pytest.fixture()
def user_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPgMemoryCoreAdapter:
    """MC2-1: PG adapter replaces Stub."""

    async def test_implements_memory_core_port(
        self,
        adapter: PgMemoryCoreAdapter,
    ) -> None:
        assert isinstance(adapter, MemoryCorePort)

    async def test_write_observation_returns_receipt(
        self,
        adapter: PgMemoryCoreAdapter,
        user_id,
    ) -> None:
        obs = Observation(content="User likes Python")
        receipt = await adapter.write_observation(user_id, obs)

        assert receipt.memory_id is not None
        assert receipt.version == 1
        assert receipt.written_at is not None

    async def test_write_and_read_observation(
        self,
        adapter: PgMemoryCoreAdapter,
        user_id,
    ) -> None:
        obs = Observation(content="User prefers dark mode")
        await adapter.write_observation(user_id, obs)

        memories = await adapter.read_personal_memories(user_id, "dark mode")
        assert len(memories) == 1
        assert "dark mode" in memories[0].content

    async def test_read_empty_returns_empty(
        self,
        adapter: PgMemoryCoreAdapter,
        user_id,
    ) -> None:
        memories = await adapter.read_personal_memories(user_id, "anything")
        assert memories == []

    async def test_read_respects_top_k(
        self,
        adapter: PgMemoryCoreAdapter,
        user_id,
    ) -> None:
        for i in range(5):
            obs = Observation(content=f"memory item {i}")
            await adapter.write_observation(user_id, obs)

        memories = await adapter.read_personal_memories(user_id, "memory", top_k=3)
        assert len(memories) == 3

    async def test_read_filters_by_query(
        self,
        adapter: PgMemoryCoreAdapter,
        user_id,
    ) -> None:
        await adapter.write_observation(user_id, Observation(content="likes coffee"))
        await adapter.write_observation(user_id, Observation(content="works at Acme"))

        results = await adapter.read_personal_memories(user_id, "coffee")
        assert len(results) == 1
        assert "coffee" in results[0].content

    async def test_session_store_and_retrieve(
        self,
        adapter: PgMemoryCoreAdapter,
        storage: FakeStoragePort,
    ) -> None:
        session_id = uuid4()
        session_data = {"user_id": str(uuid4()), "messages": []}
        await storage.put(f"session:{session_id}", session_data)

        result = await adapter.get_session(session_id)
        assert result is not None
        assert result["messages"] == []

    async def test_session_get_nonexistent_returns_none(
        self,
        adapter: PgMemoryCoreAdapter,
    ) -> None:
        result = await adapter.get_session(uuid4())
        assert result is None

    async def test_archive_session(
        self,
        adapter: PgMemoryCoreAdapter,
        storage: FakeStoragePort,
    ) -> None:
        session_id = uuid4()
        await storage.put(f"session:{session_id}", {"messages": ["hello"]})

        result = await adapter.archive_session(session_id)
        assert result is not None
        assert result["archived"] is True

    async def test_archive_nonexistent_returns_none(
        self,
        adapter: PgMemoryCoreAdapter,
    ) -> None:
        result = await adapter.archive_session(uuid4())
        assert result is None

    async def test_write_with_source_session(
        self,
        adapter: PgMemoryCoreAdapter,
        user_id,
    ) -> None:
        session_id = uuid4()
        obs = Observation(
            content="test memory",
            source_session_id=session_id,
        )
        await adapter.write_observation(user_id, obs)

        memories = await adapter.read_personal_memories(user_id, "test memory")
        assert len(memories) == 1
        assert session_id in memories[0].source_sessions
