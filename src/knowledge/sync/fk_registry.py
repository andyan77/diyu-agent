"""FK linkage registry for Neo4j <-> Qdrant consistency.

Milestone: K3-3
Layer: Knowledge

Implements write-through FK consistency: every graph node creation
triggers a corresponding vector upsert with graph_node_id FK.

See: docs/architecture/02-Knowledge Section 4 (FK protocol)
     ADR-024 (FK consistency decision)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from src.shared.types import GraphNode, VectorPoint

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


@dataclass(frozen=True)
class FKMapping:
    """Mapping between a graph node and its vector points."""

    graph_node_id: UUID
    vector_ids: list[UUID] = field(default_factory=list)
    sync_status: str = "synced"  # synced | pending_vector_sync | pending_graph_sync
    version: int = 1
    last_sync_at: datetime | None = None


@dataclass(frozen=True)
class DoubleWriteResult:
    """Result of a FK-consistent double write."""

    graph_node: GraphNode
    vector_point: VectorPoint | None
    sync_status: str
    fk_mapping: FKMapping


class FKRegistry:
    """FK consistency registry coordinating Neo4j and Qdrant writes.

    All knowledge writes go through this registry to ensure FK
    consistency between graph nodes and vector points.
    """

    def __init__(self, neo4j: Any, qdrant: Any) -> None:
        self._neo4j = neo4j
        self._qdrant = qdrant
        self._mappings: dict[str, FKMapping] = {}

    async def write_with_fk(
        self,
        entity_type: str,
        node_id: UUID,
        properties: dict[str, Any],
        *,
        org_id: UUID | None = None,
        semantic_content: str | None = None,
        embedding: list[float] | None = None,
        vector_payload: dict[str, Any] | None = None,
    ) -> DoubleWriteResult:
        """Write to Neo4j and Qdrant with FK consistency.

        Graph-first protocol:
        1. Create/update Neo4j node -> get graph_node_id
        2. If semantic content provided, upsert Qdrant with FK
        3. On Qdrant failure: mark pending_vector_sync

        Args:
            entity_type: Node label.
            node_id: Unique node identifier.
            properties: Node properties.
            org_id: Organization scope.
            semantic_content: Text for vector embedding.
            embedding: Pre-computed embedding vector.
            vector_payload: Additional Qdrant payload fields.

        Returns:
            DoubleWriteResult with both graph node and vector point.
        """
        # Step 1: Write Neo4j (graph-first)
        graph_node = await self._neo4j.create_node(
            entity_type=entity_type,
            node_id=node_id,
            properties=properties,
            org_id=org_id,
        )

        # Step 2: Write Qdrant (if semantic content provided)
        vector_point = None
        sync_status = "synced"

        if embedding is not None:
            payload = {
                "entity_type": entity_type,
                "text": semantic_content or "",
                **(vector_payload or {}),
            }
            if org_id is not None:
                payload["org_id"] = str(org_id)

            point_id = uuid4()
            retries = 0
            while retries < _MAX_RETRIES:
                try:
                    vector_point = await self._qdrant.upsert_point(
                        point_id=point_id,
                        vector=embedding,
                        payload=payload,
                        graph_node_id=node_id,
                    )
                    break
                except Exception:
                    retries += 1
                    if retries >= _MAX_RETRIES:
                        logger.warning(
                            "Qdrant write failed after %d retries for node %s",
                            _MAX_RETRIES,
                            node_id,
                        )
                        sync_status = "pending_vector_sync"
                        await self._neo4j.mark_sync_status(node_id, "pending_vector_sync")

        # Step 3: Record FK mapping
        now = datetime.now(tz=UTC)
        mapping = FKMapping(
            graph_node_id=node_id,
            vector_ids=[vector_point.point_id] if vector_point else [],
            sync_status=sync_status,
            version=1,
            last_sync_at=now if sync_status == "synced" else None,
        )
        self._mappings[str(node_id)] = mapping

        return DoubleWriteResult(
            graph_node=graph_node,
            vector_point=vector_point,
            sync_status=sync_status,
            fk_mapping=mapping,
        )

    async def update_with_fk(
        self,
        node_id: UUID,
        properties: dict[str, Any],
        *,
        semantic_content: str | None = None,
        embedding: list[float] | None = None,
    ) -> DoubleWriteResult:
        """Update Neo4j node and re-sync Qdrant vector with FK consistency.

        Graph-first protocol:
        1. Update Neo4j node properties
        2. If embedding provided, upsert Qdrant (re-use existing FK mapping point_id)
        3. On Qdrant failure: mark pending_vector_sync

        Args:
            node_id: Node to update.
            properties: Properties to set/merge.
            semantic_content: Updated text for vector payload.
            embedding: Updated embedding vector.

        Returns:
            DoubleWriteResult with updated graph node and vector point.
        """
        # Step 1: Update Neo4j (graph-first)
        updated_node = await self._neo4j.update_node(node_id, properties)
        if updated_node is None:
            msg = f"Node {node_id} not found in Neo4j during update_with_fk"
            raise ValueError(msg)

        # Step 2: Update Qdrant (if embedding provided)
        vector_point = None
        sync_status = "synced"

        if embedding is not None:
            # Re-use existing point_id if we have a mapping, otherwise create new
            existing_mapping = self._mappings.get(str(node_id))
            point_id = (
                existing_mapping.vector_ids[0]
                if existing_mapping and existing_mapping.vector_ids
                else uuid4()
            )

            payload: dict[str, Any] = {
                "entity_type": updated_node.entity_type,
                "text": semantic_content or "",
            }
            if updated_node.org_id is not None:
                payload["org_id"] = str(updated_node.org_id)

            retries = 0
            while retries < _MAX_RETRIES:
                try:
                    vector_point = await self._qdrant.upsert_point(
                        point_id=point_id,
                        vector=embedding,
                        payload=payload,
                        graph_node_id=node_id,
                    )
                    break
                except Exception:
                    retries += 1
                    if retries >= _MAX_RETRIES:
                        logger.warning(
                            "Qdrant update failed after %d retries for node %s",
                            _MAX_RETRIES,
                            node_id,
                        )
                        sync_status = "pending_vector_sync"
                        await self._neo4j.mark_sync_status(node_id, "pending_vector_sync")

        # Step 3: Update FK mapping
        now = datetime.now(tz=UTC)
        mapping = FKMapping(
            graph_node_id=node_id,
            vector_ids=[vector_point.point_id] if vector_point else (
                existing_mapping.vector_ids if existing_mapping else []
            ),
            sync_status=sync_status,
            version=(existing_mapping.version + 1) if existing_mapping else 1,
            last_sync_at=now if sync_status == "synced" else None,
        )
        self._mappings[str(node_id)] = mapping

        return DoubleWriteResult(
            graph_node=updated_node,
            vector_point=vector_point,
            sync_status=sync_status,
            fk_mapping=mapping,
        )

    async def delete_with_fk(self, node_id: UUID) -> bool:
        """Delete a node from both Neo4j and Qdrant.

        Args:
            node_id: Node to delete.

        Returns:
            True if graph node was deleted.
        """
        mapping = self._mappings.get(str(node_id))
        if mapping:
            for vid in mapping.vector_ids:
                await self._qdrant.delete_point(vid)
            del self._mappings[str(node_id)]

        result: bool = await self._neo4j.delete_node(node_id)
        return result

    def get_mapping(self, node_id: UUID) -> FKMapping | None:
        """Look up FK mapping for a node."""
        return self._mappings.get(str(node_id))

    def get_pending_sync(self) -> list[FKMapping]:
        """Return all mappings with pending sync status."""
        return [m for m in self._mappings.values() if m.sync_status != "synced"]
