"""Memory items CRUD with versioning.

Task card: MC2-3
- Create -> Update (version+1) -> Read latest -> Query history
- Version chain must be complete and traceable

Architecture: ADR-033, Section 2.3.1 (MemoryItem versioning)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.shared.types import MemoryItem


class MemoryItemStore:
    """In-memory versioned memory item store for unit testing.

    Production implementation will use SQLAlchemy + memory_items table.
    """

    def __init__(self) -> None:
        self._items: dict[UUID, MemoryItem] = {}
        self._version_chains: dict[UUID, list[UUID]] = {}

    def create(
        self,
        *,
        user_id: UUID,
        memory_type: str,
        content: str,
        confidence: float = 1.0,
        epistemic_type: str = "fact",
        source_session_id: UUID | None = None,
    ) -> MemoryItem:
        """Create a new memory item (version 1)."""
        memory_id = uuid4()
        now = datetime.now(UTC)

        item = MemoryItem(
            memory_id=memory_id,
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            confidence=confidence,
            valid_at=now,
            source_sessions=[source_session_id] if source_session_id else [],
            version=1,
            epistemic_type=epistemic_type,
        )

        self._items[memory_id] = item
        self._version_chains[memory_id] = [memory_id]
        return item

    def update(
        self,
        memory_id: UUID,
        *,
        content: str | None = None,
        confidence: float | None = None,
        epistemic_type: str | None = None,
    ) -> MemoryItem:
        """Create a new version of an existing memory item.

        The old version is superseded; the new version gets version+1.

        Raises:
            KeyError: If memory_id not found.
            ValueError: If memory is already superseded.
        """
        old = self._items.get(memory_id)
        if old is None:
            msg = f"MemoryItem {memory_id} not found"
            raise KeyError(msg)
        if old.superseded_by is not None:
            msg = f"MemoryItem {memory_id} already superseded by {old.superseded_by}"
            raise ValueError(msg)

        new_id = uuid4()
        now = datetime.now(UTC)

        new_item = MemoryItem(
            memory_id=new_id,
            user_id=old.user_id,
            memory_type=old.memory_type,
            content=content if content is not None else old.content,
            confidence=confidence if confidence is not None else old.confidence,
            valid_at=now,
            invalid_at=None,
            source_sessions=list(old.source_sessions),
            superseded_by=None,
            version=old.version + 1,
            provenance=old.provenance,
            epistemic_type=(epistemic_type if epistemic_type is not None else old.epistemic_type),
        )

        # Mark old as superseded (frozen dataclass, so create a replacement)
        superseded_old = MemoryItem(
            memory_id=old.memory_id,
            user_id=old.user_id,
            memory_type=old.memory_type,
            content=old.content,
            confidence=old.confidence,
            valid_at=old.valid_at,
            invalid_at=now,
            source_sessions=list(old.source_sessions),
            superseded_by=new_id,
            version=old.version,
            provenance=old.provenance,
            epistemic_type=old.epistemic_type,
        )

        self._items[old.memory_id] = superseded_old
        self._items[new_id] = new_item

        # Extend version chain
        root_id = self._find_root(old.memory_id)
        self._version_chains[root_id].append(new_id)

        return new_item

    def get(self, memory_id: UUID) -> MemoryItem | None:
        """Get a memory item by ID (any version)."""
        return self._items.get(memory_id)

    def get_latest(self, memory_id: UUID) -> MemoryItem | None:
        """Get the latest version following the version chain."""
        root_id = self._find_root(memory_id)
        chain = self._version_chains.get(root_id, [])
        if not chain:
            return self._items.get(memory_id)
        return self._items.get(chain[-1])

    def get_version_history(self, memory_id: UUID) -> list[MemoryItem]:
        """Get all versions of a memory item, oldest first."""
        root_id = self._find_root(memory_id)
        chain = self._version_chains.get(root_id, [])
        return [self._items[mid] for mid in chain if mid in self._items]

    def list_active(self, user_id: UUID) -> list[MemoryItem]:
        """List all active (non-superseded) items for a user."""
        return [
            item
            for item in self._items.values()
            if item.user_id == user_id and item.superseded_by is None
        ]

    def _find_root(self, memory_id: UUID) -> UUID:
        """Find the root ID for a version chain."""
        for root, chain in self._version_chains.items():
            if memory_id in chain:
                return root
        return memory_id
