"""PostgreSQL adapter implementing MemoryCorePort via SQLAlchemy.

Task card: MC2-1, MC2-4
- Replaces KV-backed stub with real PG/SQLAlchemy implementation
- Uses async_sessionmaker for database access
- RLS SET LOCAL is handled by src.infra.db.get_db_session (not here)
- Adapter implements Port interface; consumers unchanged
- Hybrid retrieval: pgvector semantic search + ILIKE keyword, fused via RRF

Architecture: Section 2.1 (PostgreSQL as Memory Core primary storage)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

import sqlalchemy as sa

from src.infra.models import MemoryItemModel
from src.ports.memory_core_port import MemoryCorePort
from src.shared.types import MemoryItem, Observation, PromotionReceipt, WriteReceipt

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from src.memory.vector_search import PgVectorSearchEngine

logger = logging.getLogger(__name__)


class QueryEmbedderProtocol(Protocol):
    """Protocol for query text -> embedding vector conversion."""

    async def embed(self, text: str) -> list[float]: ...


class PgMemoryCoreAdapter(MemoryCorePort):
    """PostgreSQL-backed implementation of MemoryCorePort.

    Uses SQLAlchemy async sessions for persistence.
    Queries filter by user_id and org_id; RLS provides defense-in-depth.

    When a PgVectorSearchEngine and query_embedder are provided, the main
    retrieval path uses hybrid search (pgvector + ILIKE via RRF fusion).
    Falls back to ILIKE-only when vector search is unavailable.
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        vector_engine: PgVectorSearchEngine | None = None,
        query_embedder: QueryEmbedderProtocol | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._vector_engine = vector_engine
        self._query_embedder = query_embedder

    async def read_personal_memories(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 10,
        *,
        org_id: UUID | None = None,
    ) -> list[MemoryItem]:
        """Retrieve personal memories by user using hybrid search.

        Primary path (MC2-4): RRF fusion of pgvector semantic + ILIKE keyword.
        Fallback: ILIKE keyword-only when vector engine is unavailable.
        """
        # Primary path: hybrid search when vector engine + embedder are available
        if self._vector_engine and self._query_embedder and org_id and query:
            try:
                return await self._hybrid_retrieval(
                    user_id=user_id,
                    query=query,
                    org_id=org_id,
                    top_k=top_k,
                )
            except Exception:
                logger.warning(
                    "Hybrid search failed, falling back to keyword-only",
                    exc_info=True,
                )

        # Fallback: ILIKE keyword-only
        return await self._keyword_retrieval(
            user_id=user_id,
            query=query,
            org_id=org_id,
            top_k=top_k,
        )

    async def _hybrid_retrieval(
        self,
        *,
        user_id: UUID,
        query: str,
        org_id: UUID,
        top_k: int,
    ) -> list[MemoryItem]:
        """RRF-fused hybrid retrieval: pgvector + ILIKE."""
        assert self._vector_engine is not None
        assert self._query_embedder is not None

        embedding = await self._query_embedder.embed(query)
        fused = await self._vector_engine.hybrid_search(
            embedding=embedding,
            query=query,
            org_id=org_id,
            user_id=user_id,
            top_k=top_k,
        )

        if not fused:
            return []

        # Fetch full MemoryItemModel rows for the fused IDs
        fused_ids = [f.memory_id for f in fused]
        stmt = sa.select(MemoryItemModel).where(MemoryItemModel.id.in_(fused_ids))
        async with self._session_factory() as session:
            result = await session.scalars(stmt)
            rows_by_id = {row.id: row for row in result.all()}

        # Return in RRF rank order
        return [_row_to_memory_item(rows_by_id[mid]) for mid in fused_ids if mid in rows_by_id]

    async def _keyword_retrieval(
        self,
        *,
        user_id: UUID,
        query: str,
        org_id: UUID | None,
        top_k: int,
    ) -> list[MemoryItem]:
        """ILIKE keyword-only retrieval (fallback path)."""
        stmt = (
            sa.select(MemoryItemModel)
            .where(
                MemoryItemModel.user_id == user_id,
                MemoryItemModel.superseded_by.is_(None),
                sa.or_(
                    MemoryItemModel.invalid_at.is_(None),
                    MemoryItemModel.invalid_at > datetime.now(UTC),
                ),
            )
            .order_by(MemoryItemModel.confidence.desc())
            .limit(top_k)
        )

        if org_id is not None:
            stmt = stmt.where(MemoryItemModel.org_id == org_id)

        if query:
            # Extract key terms for ILIKE matching rather than using the full query
            # (full query as substring match is too restrictive)
            terms = [w for w in query.lower().split() if len(w) > 3]
            if terms:
                conditions = [MemoryItemModel.content.ilike(f"%{t}%") for t in terms[:5]]
                stmt = stmt.where(sa.or_(*conditions))

        async with self._session_factory() as session:
            result = await session.scalars(stmt)
            rows = result.all()

        return [_row_to_memory_item(row) for row in rows]

    async def write_observation(
        self,
        user_id: UUID,
        observation: Observation,
        *,
        org_id: UUID | None = None,
    ) -> WriteReceipt:
        """Write a new observation as a MemoryItemModel row."""
        if org_id is None:
            msg = "org_id is required for PG write operations"
            raise ValueError(msg)

        now = datetime.now(UTC)
        memory_id = uuid4()
        model = MemoryItemModel(
            id=memory_id,
            org_id=org_id,
            user_id=user_id,
            memory_type=observation.memory_type,
            content=observation.content,
            confidence=observation.confidence,
            epistemic_type="fact",
            version=1,
            source_sessions=(
                [observation.source_session_id] if observation.source_session_id else []
            ),
            valid_at=now,
        )

        async with self._session_factory() as session:
            session.add(model)
            await session.commit()

        return WriteReceipt(
            memory_id=model.id,
            version=1,
            written_at=now,
        )

    async def get_session(self, session_id: UUID) -> object:
        """Retrieve a conversation session by ID.

        Placeholder: session retrieval is handled by ConversationEventStore.
        """
        return None

    async def archive_session(self, session_id: UUID) -> object:
        """Archive a completed session.

        Placeholder: session archival is handled by ConversationEventStore.
        """
        return None

    async def promote_to_knowledge(
        self,
        memory_id: UUID,
        target_org_id: UUID,
        target_visibility: str,
        *,
        user_id: UUID | None = None,
    ) -> PromotionReceipt:
        """Promote a personal memory to organizational knowledge.

        Placeholder stub: Phase 3 implementation will integrate with
        Knowledge Stores via the Promotion Pipeline.
        """
        return PromotionReceipt(
            proposal_id=memory_id,
            source_memory_id=memory_id,
            target_knowledge_id=None,
            status="promoted",
            promoted_at=datetime.now(UTC),
        )


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
