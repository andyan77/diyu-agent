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

    from src.shared.types import MemoryItem, Observation, PromotionReceipt, WriteReceipt


class MemoryCorePort(ABC):
    """Port: Memory Core read/write operations."""

    @abstractmethod
    async def read_personal_memories(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        *,
        org_id: UUID | None = None,
    ) -> list[MemoryItem]:
        """Retrieve personal memories relevant to query.

        Args:
            user_id: Owner of the memories.
            query: Semantic query string.
            top_k: Maximum number of results.
            org_id: Organization scope (required for PG adapter, optional for tests).

        Returns:
            List of MemoryItem sorted by relevance.
        """

    @abstractmethod
    async def write_observation(
        self,
        user_id: UUID,
        observation: Observation,
        *,
        org_id: UUID | None = None,
    ) -> WriteReceipt:
        """Write a new observation to memory.

        Args:
            user_id: Owner of the memory.
            observation: Observation to persist.
            org_id: Organization scope (required for PG adapter, optional for tests).

        Returns:
            WriteReceipt with memory_id and version.
        """

    @abstractmethod
    async def get_session(self, session_id: UUID) -> object:
        """Retrieve a conversation session by ID."""

    @abstractmethod
    async def archive_session(self, session_id: UUID) -> object:
        """Archive a completed session."""

    # -- Phase 3 promotion method (MC3-1: Memory -> Knowledge) --

    @abstractmethod
    async def promote_to_knowledge(
        self,
        memory_id: UUID,
        target_org_id: UUID,
        target_visibility: str,
        *,
        user_id: UUID | None = None,
    ) -> PromotionReceipt:
        """Promote a personal memory to organizational knowledge.

        This is a cross-SSOT operation (Memory Core -> Knowledge Stores)
        via the Promotion Pipeline. The memory content is sanitized,
        scanned, and submitted for approval before writing to Knowledge.

        Args:
            memory_id: Source memory item to promote.
            target_org_id: Target organization for the knowledge entry.
            target_visibility: Visibility level (store|region|brand|global).
            user_id: Promoting user (for audit trail).

        Returns:
            PromotionReceipt with proposal status and target knowledge ID.

        See: docs/architecture/02-Knowledge Section 7.2
        """
