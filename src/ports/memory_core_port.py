"""MemoryCorePort - Memory Core read/write interface.

Brain hard dependency. Encapsulates personal memory CRUD.
Day-1 implementation: SQLite in-memory.
Real implementation: PostgreSQL + pgvector.

See: docs/architecture/01-Brain Section 2.3 (MemoryItem schema)
     docs/architecture/00-*.md Section 12.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from src.shared.types import MemoryItem, Observation, WriteReceipt


class MemoryCorePort(ABC):
    """Port: Memory Core read/write operations."""

    @abstractmethod
    async def read_personal_memories(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 10,
    ) -> list[MemoryItem]:
        """Retrieve personal memories relevant to query.

        Args:
            user_id: Owner of the memories.
            query: Semantic query string.
            top_k: Maximum number of results.

        Returns:
            List of MemoryItem sorted by relevance.
        """

    @abstractmethod
    async def write_observation(
        self,
        user_id: UUID,
        observation: Observation,
    ) -> WriteReceipt:
        """Write a new observation to memory.

        Args:
            user_id: Owner of the memory.
            observation: Observation to persist.

        Returns:
            WriteReceipt with memory_id and version.
        """

    @abstractmethod
    async def get_session(self, session_id: UUID) -> object:
        """Retrieve a conversation session by ID."""

    @abstractmethod
    async def archive_session(self, session_id: UUID) -> object:
        """Archive a completed session."""
