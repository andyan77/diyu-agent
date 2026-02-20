"""Qdrant adapter for Knowledge Vector Store operations.

Milestone: I3-2
Layer: Infrastructure (implements KnowledgePort vector-side operations)

Provides connection management and CRUD for Qdrant vector collections.
Used by Knowledge layer via KnowledgePort for semantic search.

See: docs/architecture/02-Knowledge Section 4 (Qdrant schema)
     docs/architecture/06-基础设施层 Section 9 (DDL)
"""

from __future__ import annotations

import logging
import os
from typing import Any, cast
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from src.shared.types import VectorPoint

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["QdrantAdapter", "VectorPoint"]


class QdrantAdapter:
    """Infrastructure adapter for Qdrant vector store.

    Manages connection lifecycle and provides CRUD operations
    for knowledge vector collections.
    """

    DEFAULT_COLLECTION = "knowledge_vectors"
    DEFAULT_VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small dimension

    def __init__(
        self,
        url: str | None = None,
        collection_name: str | None = None,
        vector_size: int | None = None,
    ) -> None:
        self._url = url or os.environ.get("QDRANT_URL", "http://localhost:6333")
        self._collection_name = collection_name or self.DEFAULT_COLLECTION
        self._vector_size = vector_size or self.DEFAULT_VECTOR_SIZE
        self._client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        """Establish connection to Qdrant and ensure collection exists."""
        self._client = AsyncQdrantClient(url=self._url)

        collections = await self._client.get_collections()
        existing = {c.name for c in collections.collections}
        if self._collection_name not in existing:
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "Created Qdrant collection: %s (dim=%d)",
                self._collection_name,
                self._vector_size,
            )

        logger.info("Qdrant connected: %s", self._url)

    async def close(self) -> None:
        """Close the Qdrant connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Qdrant connection closed")

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            msg = "Qdrant not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._client

    async def upsert_point(
        self,
        point_id: UUID,
        vector: list[float],
        payload: dict[str, Any] | None = None,
        *,
        graph_node_id: UUID | None = None,
    ) -> VectorPoint:
        """Insert or update a vector point.

        Args:
            point_id: Unique point identifier.
            vector: Embedding vector.
            payload: Associated metadata.
            graph_node_id: FK reference to Neo4j node.

        Returns:
            Upserted VectorPoint.
        """
        point_payload = payload or {}
        if graph_node_id is not None:
            point_payload["graph_node_id"] = str(graph_node_id)

        await self.client.upsert(
            collection_name=self._collection_name,
            points=[
                PointStruct(
                    id=str(point_id),
                    vector=vector,
                    payload=point_payload,
                ),
            ],
        )

        return VectorPoint(
            point_id=point_id,
            vector=vector,
            payload=point_payload,
            graph_node_id=graph_node_id,
        )

    async def get_point(self, point_id: UUID) -> VectorPoint | None:
        """Retrieve a point by ID.

        Args:
            point_id: Point identifier.

        Returns:
            VectorPoint if found, None otherwise.
        """
        results = await self.client.retrieve(
            collection_name=self._collection_name,
            ids=[str(point_id)],
            with_vectors=True,
            with_payload=True,
        )
        if not results:
            return None

        point = results[0]
        payload = point.payload or {}
        gn_id = payload.pop("graph_node_id", None)

        return VectorPoint(
            point_id=point_id,
            vector=cast("list[float]", point.vector) if point.vector else [],
            payload=payload,
            graph_node_id=UUID(gn_id) if gn_id else None,
        )

    async def delete_point(self, point_id: UUID) -> bool:
        """Delete a vector point.

        Args:
            point_id: Point identifier.

        Returns:
            True (Qdrant delete is idempotent).
        """
        await self.client.delete(
            collection_name=self._collection_name,
            points_selector=[str(point_id)],
        )
        return True

    async def search(
        self,
        query_vector: list[float],
        *,
        org_id: UUID | None = None,
        limit: int = 10,
    ) -> list[VectorPoint]:
        """Semantic search for similar vectors.

        Args:
            query_vector: Query embedding.
            org_id: Optional org filter for tenant isolation.
            limit: Maximum results.

        Returns:
            List of VectorPoints ordered by relevance.
        """
        query_filter = None
        if org_id is not None:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="org_id",
                        match=MatchValue(value=str(org_id)),
                    )
                ]
            )

        results = await self.client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=True,
        )

        points: list[VectorPoint] = []
        for scored in results.points:
            payload = scored.payload or {}
            gn_id = payload.pop("graph_node_id", None)
            points.append(
                VectorPoint(
                    point_id=UUID(str(scored.id)),
                    vector=cast("list[float]", scored.vector) if scored.vector else [],
                    payload=payload,
                    graph_node_id=UUID(gn_id) if gn_id else None,
                    score=scored.score,
                )
            )

        return points

    async def count(self) -> int:
        """Return total number of points in the collection."""
        info = await self.client.get_collection(self._collection_name)
        return info.points_count or 0
