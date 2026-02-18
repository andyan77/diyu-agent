"""pgvector semantic search with RRF fusion.

Task card: MC2-4
- Write embedding -> similarity query Top-5 -> RRF fusion ranking
- Top-5 recall >= 80%

Architecture: ADR-042 (pgvector as Day-1 default vector search)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import sqlalchemy as sa

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True)
class SearchResult:
    """A single search result with score."""

    memory_id: UUID
    content: str
    score: float
    source: str  # "vector" | "keyword"


@dataclass(frozen=True)
class FusedResult:
    """RRF-fused search result combining multiple retrieval sources."""

    memory_id: UUID
    content: str
    rrf_score: float
    vector_rank: int | None = None
    keyword_rank: int | None = None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        msg = f"Vector dimension mismatch: {len(a)} vs {len(b)}"
        raise ValueError(msg)

    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def rrf_fuse(
    ranked_lists: list[list[SearchResult]],
    k: int = 60,
    top_n: int = 5,
) -> list[FusedResult]:
    """Reciprocal Rank Fusion across multiple result lists.

    RRF score = sum(1 / (k + rank_i)) for each list where item appears.

    Args:
        ranked_lists: Multiple ranked result lists to fuse.
        k: RRF constant (default 60, standard value).
        top_n: Number of top results to return.

    Returns:
        Top-N fused results sorted by RRF score descending.
    """
    scores: dict[UUID, float] = {}
    content_map: dict[UUID, str] = {}
    vector_ranks: dict[UUID, int] = {}
    keyword_ranks: dict[UUID, int] = {}

    for _list_idx, result_list in enumerate(ranked_lists):
        for rank, result in enumerate(result_list, start=1):
            scores[result.memory_id] = scores.get(result.memory_id, 0.0) + 1.0 / (k + rank)
            content_map[result.memory_id] = result.content

            if result.source == "vector":
                vector_ranks[result.memory_id] = rank
            elif result.source == "keyword":
                keyword_ranks[result.memory_id] = rank

    sorted_ids = sorted(scores, key=lambda mid: scores[mid], reverse=True)

    return [
        FusedResult(
            memory_id=mid,
            content=content_map[mid],
            rrf_score=scores[mid],
            vector_rank=vector_ranks.get(mid),
            keyword_rank=keyword_ranks.get(mid),
        )
        for mid in sorted_ids[:top_n]
    ]


class VectorSearchEngine:
    """In-memory vector search engine for unit testing.

    Production uses pgvector HNSW index via SQLAlchemy.
    """

    def __init__(self) -> None:
        self._embeddings: dict[UUID, list[float]] = {}
        self._content: dict[UUID, str] = {}

    def index(self, memory_id: UUID, content: str, embedding: list[float]) -> None:
        """Index a memory item with its embedding."""
        self._embeddings[memory_id] = embedding
        self._content[memory_id] = content

    def search_vector(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Search by vector similarity (cosine)."""
        scored: list[tuple[UUID, float]] = []
        for mid, emb in self._embeddings.items():
            sim = cosine_similarity(query_embedding, emb)
            scored.append((mid, sim))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [
            SearchResult(
                memory_id=mid,
                content=self._content[mid],
                score=sim,
                source="vector",
            )
            for mid, sim in scored[:top_k]
        ]

    def search_keyword(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Simple keyword search (for RRF fusion with vector)."""
        scored: list[tuple[UUID, float]] = []
        query_lower = query.lower()

        for mid, content in self._content.items():
            content_lower = content.lower()
            if query_lower in content_lower:
                # Simple TF-based scoring
                count = content_lower.count(query_lower)
                score = count / max(len(content_lower.split()), 1)
                scored.append((mid, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [
            SearchResult(
                memory_id=mid,
                content=self._content[mid],
                score=score,
                source="keyword",
            )
            for mid, score in scored[:top_k]
        ]

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[FusedResult]:
        """RRF-fused hybrid search combining vector and keyword."""
        vector_results = self.search_vector(query_embedding, top_k=top_k * 2)
        keyword_results = self.search_keyword(query, top_k=top_k * 2)
        return rrf_fuse([vector_results, keyword_results], top_n=top_k)


class PgVectorSearchEngine:
    """PostgreSQL-backed vector search engine using pgvector.

    Uses the <=> cosine distance operator from pgvector for embedding search
    and ILIKE for keyword search.  Results from both are combined via RRF fusion
    in hybrid_search.

    Args:
        session_factory: An async_sessionmaker[AsyncSession] that produces async
            database sessions as context managers.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Embedding search
    # ------------------------------------------------------------------

    async def search_by_embedding(
        self,
        embedding: list[float],
        org_id: UUID,
        user_id: UUID,
        top_k: int = 5,
    ) -> list[tuple[UUID, float]]:
        """Search memory items by cosine distance using pgvector.

        Args:
            embedding: Query embedding vector.
            org_id: Tenant organisation UUID (RLS scope).
            user_id: User UUID (RLS scope).
            top_k: Maximum number of results to return.

        Returns:
            List of (memory_item_id, cosine_distance) tuples, ordered by
            ascending distance (most similar first).
        """
        embedding_literal = f"[{', '.join(str(v) for v in embedding)}]"
        sql = sa.text(
            """
            SELECT id, content, embedding <=> CAST(:query_embedding AS vector) AS distance
            FROM memory_items
            WHERE org_id = :org_id
              AND user_id = :user_id
              AND embedding IS NOT NULL
              AND invalid_at IS NULL
            ORDER BY distance ASC
            LIMIT :top_k
            """
        )
        async with self._session_factory() as session:
            cursor = await session.execute(
                sql,
                {
                    "query_embedding": embedding_literal,
                    "org_id": str(org_id),
                    "user_id": str(user_id),
                    "top_k": top_k,
                },
            )
            rows = cursor.fetchall()

        return [(row[0], float(row[2])) for row in rows]

    # ------------------------------------------------------------------
    # Keyword search
    # ------------------------------------------------------------------

    async def search_by_keyword(
        self,
        query: str,
        org_id: UUID,
        user_id: UUID,
        top_k: int = 5,
    ) -> list[tuple[UUID, float]]:
        """Search memory items by keyword using ILIKE on the content column.

        Args:
            query: Keyword or phrase to search for.
            org_id: Tenant organisation UUID (RLS scope).
            user_id: User UUID (RLS scope).
            top_k: Maximum number of results to return.

        Returns:
            List of (memory_item_id, score) tuples.  Score is a fixed 1.0 for
            all matches (presence-only relevance; ranking relies on RRF fusion).
        """
        sql = sa.text(
            """
            SELECT id, content
            FROM memory_items
            WHERE org_id = :org_id
              AND user_id = :user_id
              AND content ILIKE :pattern
              AND invalid_at IS NULL
            LIMIT :top_k
            """
        )
        async with self._session_factory() as session:
            cursor = await session.execute(
                sql,
                {
                    "org_id": str(org_id),
                    "user_id": str(user_id),
                    "pattern": f"%{query}%",
                    "top_k": top_k,
                },
            )
            rows = cursor.fetchall()

        return [(row[0], 1.0) for row in rows]

    # ------------------------------------------------------------------
    # Hybrid search
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        embedding: list[float],
        query: str,
        org_id: UUID,
        user_id: UUID,
        top_k: int = 5,
    ) -> list[FusedResult]:
        """RRF-fused hybrid search combining pgvector and keyword retrieval.

        Runs search_by_embedding and search_by_keyword concurrently (sequential
        DB calls), then fuses the ranked lists with rrf_fuse.

        Args:
            embedding: Query embedding vector.
            query: Keyword or phrase for keyword search.
            org_id: Tenant organisation UUID (RLS scope).
            user_id: User UUID (RLS scope).
            top_k: Maximum number of fused results to return.

        Returns:
            Top-N FusedResult items sorted by RRF score descending.
        """
        fetch_k = top_k * 2

        vec_pairs = await self.search_by_embedding(
            embedding=embedding, org_id=org_id, user_id=user_id, top_k=fetch_k
        )
        kw_pairs = await self.search_by_keyword(
            query=query, org_id=org_id, user_id=user_id, top_k=fetch_k
        )

        # Build SearchResult lists for rrf_fuse.
        # Content is not available after the raw SQL query; use empty string as
        # placeholder so FusedResult can be constructed.  Callers that need
        # content should fetch the full MemoryItemModel separately.
        vec_results: list[SearchResult] = [
            SearchResult(memory_id=mid, content="", score=score, source="vector")
            for mid, score in vec_pairs
        ]
        kw_results: list[SearchResult] = [
            SearchResult(memory_id=mid, content="", score=score, source="keyword")
            for mid, score in kw_pairs
        ]

        if not vec_results and not kw_results:
            return []

        return rrf_fuse([vec_results, kw_results], top_n=top_k)
