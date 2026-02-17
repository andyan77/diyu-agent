"""PostgreSQL adapter implementing MemoryCorePort.

Task card: MC2-1
- Replaces SQLite stub with real PG implementation
- All Stub tests must pass against PG adapter
- Adapter implements Port interface; consumers unchanged

Architecture: Section 2.1 (PostgreSQL as Memory Core primary storage)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, WriteReceipt

if TYPE_CHECKING:
    from src.ports.storage_port import StoragePort


class PgMemoryCoreAdapter(MemoryCorePort):
    """PostgreSQL-backed implementation of MemoryCorePort.

    Uses StoragePort for persistence, allowing in-memory testing
    without a real database connection.
    """

    def __init__(self, storage: StoragePort) -> None:
        self._storage = storage

    async def read_personal_memories(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 10,
    ) -> list[MemoryItem]:
        """Retrieve personal memories by user, optionally filtered by query.

        Simple keyword matching for Day-1. MC2-4 adds vector search.
        """
        all_keys = await self._storage.list_keys(f"memory:{user_id}:*")
        results: list[MemoryItem] = []

        for key in all_keys:
            raw = await self._storage.get(key)
            if raw is None:
                continue
            item = _dict_to_memory_item(raw)
            if item.superseded_by is not None:
                continue
            if item.invalid_at is not None and item.invalid_at <= datetime.now(UTC):
                continue
            if query and query.lower() not in item.content.lower():
                continue
            results.append(item)

        results.sort(key=lambda m: m.confidence, reverse=True)
        return results[:top_k]

    async def write_observation(
        self,
        user_id: UUID,
        observation: Observation,
    ) -> WriteReceipt:
        """Write a new observation as a MemoryItem."""
        memory_id = uuid4()
        now = datetime.now(UTC)

        item_dict: dict[str, Any] = {
            "memory_id": str(memory_id),
            "user_id": str(user_id),
            "memory_type": observation.memory_type,
            "content": observation.content,
            "confidence": observation.confidence,
            "valid_at": now.isoformat(),
            "invalid_at": None,
            "source_sessions": (
                [str(observation.source_session_id)] if observation.source_session_id else []
            ),
            "superseded_by": None,
            "version": 1,
            "provenance": None,
            "epistemic_type": "fact",
        }

        key = f"memory:{user_id}:{memory_id}"
        await self._storage.put(key, item_dict)

        return WriteReceipt(
            memory_id=memory_id,
            version=1,
            written_at=now,
        )

    async def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        """Retrieve a conversation session by ID."""
        result = await self._storage.get(f"session:{session_id}")
        return result if isinstance(result, dict) else None

    async def archive_session(self, session_id: UUID) -> dict[str, Any] | None:
        """Archive a completed session."""
        session = await self._storage.get(f"session:{session_id}")
        if session is None:
            return None
        if isinstance(session, dict):
            session["archived"] = True
            session["archived_at"] = datetime.now(UTC).isoformat()
            await self._storage.put(f"session:{session_id}", session)
        return session if isinstance(session, dict) else None


def _dict_to_memory_item(raw: Any) -> MemoryItem:
    """Convert a stored dict back to MemoryItem."""
    if not isinstance(raw, dict):
        msg = f"Expected dict, got {type(raw)}"
        raise TypeError(msg)

    return MemoryItem(
        memory_id=UUID(raw["memory_id"]),
        user_id=UUID(raw["user_id"]),
        memory_type=raw["memory_type"],
        content=raw["content"],
        confidence=raw.get("confidence", 1.0),
        valid_at=datetime.fromisoformat(raw["valid_at"]),
        invalid_at=(datetime.fromisoformat(raw["invalid_at"]) if raw.get("invalid_at") else None),
        source_sessions=[UUID(s) for s in raw.get("source_sessions", [])],
        superseded_by=(UUID(raw["superseded_by"]) if raw.get("superseded_by") else None),
        version=raw.get("version", 1),
        provenance=raw.get("provenance"),
        epistemic_type=raw.get("epistemic_type", "fact"),
    )
