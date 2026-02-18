"""Memory items CRUD with versioning.

Task card: MC2-3
- Create -> Update (version+1) -> Read latest -> Query history
- Version chain must be complete and traceable

Architecture: ADR-033, Section 2.3.1 (MemoryItem versioning)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa

from src.infra.models import MemoryItemModel
from src.shared.types import MemoryItem

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


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


class PgMemoryItemStore:
    """PostgreSQL-backed memory item store using SQLAlchemy.

    All methods are async. Uses async_sessionmaker for DB access.
    RLS SET LOCAL is handled externally by src.infra.db.get_db_session.
    """

    def __init__(self, *, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add_item(
        self,
        *,
        user_id: UUID,
        org_id: UUID,
        memory_type: str,
        content: str,
        confidence: float = 1.0,
        epistemic_type: str = "fact",
        source_session_id: UUID | None = None,
    ) -> MemoryItem:
        """Create a new memory item row (version 1) and return domain object."""
        memory_id = uuid4()
        now = datetime.now(UTC)
        source_sessions = [source_session_id] if source_session_id else []

        model = MemoryItemModel(
            id=memory_id,
            org_id=org_id,
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            confidence=confidence,
            epistemic_type=epistemic_type,
            version=1,
            superseded_by=None,
            source_sessions=source_sessions,
            provenance=None,
            valid_at=now,
            invalid_at=None,
        )

        async with self._session_factory() as session:
            session.add(model)
            await session.commit()

        return MemoryItem(
            memory_id=memory_id,
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            confidence=confidence,
            valid_at=now,
            invalid_at=None,
            source_sessions=source_sessions,
            superseded_by=None,
            version=1,
            provenance=None,
            epistemic_type=epistemic_type,
        )

    async def get_item(self, memory_id: UUID) -> MemoryItem | None:
        """Get a memory item by ID. Returns None if not found."""
        stmt = sa.select(MemoryItemModel).where(MemoryItemModel.id == memory_id)
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

        if row is None:
            return None
        return _row_to_memory_item(row)

    async def get_items_for_user(
        self,
        user_id: UUID,
        *,
        active_only: bool = False,
    ) -> list[MemoryItem]:
        """Get all memory items for a user.

        Args:
            user_id: The user whose items to fetch.
            active_only: If True, only return non-superseded items.
        """
        stmt = sa.select(MemoryItemModel).where(MemoryItemModel.user_id == user_id)
        if active_only:
            stmt = stmt.where(MemoryItemModel.superseded_by.is_(None))

        async with self._session_factory() as session:
            result = await session.scalars(stmt)
            rows = result.all()

        return [_row_to_memory_item(row) for row in rows]

    async def update_item(
        self,
        memory_id: UUID,
        *,
        content: str | None = None,
        confidence: float | None = None,
        epistemic_type: str | None = None,
    ) -> MemoryItem:
        """Create a new version of an existing memory item.

        Fetches the existing row, inserts a new row with version+1,
        and marks the old row as superseded.

        Raises:
            KeyError: If memory_id is not found.
        """
        stmt = sa.select(MemoryItemModel).where(MemoryItemModel.id == memory_id)

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            old_row = result.scalar_one_or_none()

            if old_row is None:
                msg = f"MemoryItem {memory_id} not found"
                raise KeyError(msg)

            new_id = uuid4()
            now = datetime.now(UTC)

            new_model = MemoryItemModel(
                id=new_id,
                org_id=old_row.org_id,
                user_id=old_row.user_id,
                memory_type=old_row.memory_type,
                content=content if content is not None else old_row.content,
                confidence=confidence if confidence is not None else old_row.confidence,
                epistemic_type=(
                    epistemic_type if epistemic_type is not None else old_row.epistemic_type
                ),
                version=old_row.version + 1,
                superseded_by=None,
                source_sessions=list(old_row.source_sessions or []),
                provenance=old_row.provenance,
                valid_at=now,
                invalid_at=None,
            )

            # Mark old row as superseded
            old_row.superseded_by = new_id
            old_row.invalid_at = now

            session.add(new_model)
            await session.commit()

        return MemoryItem(
            memory_id=new_id,
            user_id=new_model.user_id,
            memory_type=new_model.memory_type,
            content=new_model.content,
            confidence=new_model.confidence,
            valid_at=now,
            invalid_at=None,
            source_sessions=list(new_model.source_sessions or []),
            superseded_by=None,
            version=new_model.version,
            provenance=new_model.provenance,
            epistemic_type=new_model.epistemic_type,
        )

    async def supersede_item(
        self,
        memory_id: UUID,
        *,
        new_memory_id: UUID,
    ) -> None:
        """Mark an existing memory item as superseded by new_memory_id.

        Sets superseded_by and invalid_at on the target row.

        Raises:
            KeyError: If memory_id is not found.
        """
        stmt = sa.select(MemoryItemModel).where(MemoryItemModel.id == memory_id)

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row is None:
                msg = f"MemoryItem {memory_id} not found"
                raise KeyError(msg)

            now = datetime.now(UTC)
            row.superseded_by = new_memory_id
            row.invalid_at = now
            await session.commit()


def _row_to_memory_item(row: MemoryItemModel) -> MemoryItem:
    """Convert an ORM row to a domain MemoryItem."""
    return MemoryItem(
        memory_id=row.id,
        user_id=row.user_id,
        memory_type=row.memory_type,
        content=row.content,
        confidence=row.confidence,
        valid_at=row.valid_at,
        invalid_at=row.invalid_at,
        source_sessions=list(row.source_sessions) if row.source_sessions else [],
        superseded_by=row.superseded_by,
        version=row.version,
        provenance=row.provenance,
        epistemic_type=row.epistemic_type,
    )
