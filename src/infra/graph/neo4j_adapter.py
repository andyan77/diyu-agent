"""Neo4j adapter for Knowledge Graph operations.

Milestone: I3-1
Layer: Infrastructure (implements KnowledgePort graph-side operations)

Provides connection management and CRUD for Neo4j knowledge graph nodes
and relationships. Used by Knowledge layer via KnowledgePort.

See: docs/architecture/02-Knowledge Section 4 (Neo4j schema)
     docs/architecture/06-基础设施层 Section 9 (DDL)
"""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

from neo4j import AsyncDriver, AsyncGraphDatabase

from src.shared.types import GraphNode, GraphRelationship

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["GraphNode", "GraphRelationship", "Neo4jAdapter"]


class Neo4jAdapter:
    """Infrastructure adapter for Neo4j knowledge graph.

    Manages connection lifecycle and provides CRUD operations
    for knowledge graph nodes and relationships.
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self._uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.environ.get("NEO4J_USER", "neo4j")
        self._password = password or os.environ.get("NEO4J_PASSWORD", "")
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
        )
        await self._driver.verify_connectivity()
        logger.info("Neo4j connected: %s", self._uri)

    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            msg = "Neo4j not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._driver

    async def create_node(
        self,
        entity_type: str,
        node_id: UUID,
        properties: dict[str, Any],
        *,
        org_id: UUID | None = None,
    ) -> GraphNode:
        """Create a knowledge graph node.

        Args:
            entity_type: Node label / entity type.
            node_id: Unique node identifier.
            properties: Node properties.
            org_id: Organization scope for RLS.

        Returns:
            Created GraphNode.
        """
        props = {**properties, "node_id": str(node_id), "sync_status": "synced"}
        if org_id is not None:
            props["org_id"] = str(org_id)

        query = f"CREATE (n:{entity_type} $props) RETURN n"
        async with self.driver.session() as session:
            result = await session.run(query, props=props)
            await result.consume()

        return GraphNode(
            node_id=node_id,
            entity_type=entity_type,
            properties=properties,
            org_id=org_id,
        )

    async def get_node(self, node_id: UUID) -> GraphNode | None:
        """Retrieve a node by its ID.

        Args:
            node_id: Node identifier.

        Returns:
            GraphNode if found, None otherwise.
        """
        query = "MATCH (n {node_id: $node_id}) RETURN n, labels(n) as labels"
        async with self.driver.session() as session:
            result = await session.run(query, node_id=str(node_id))
            record = await result.single()
            if record is None:
                return None

            node_data = dict(record["n"])
            labels = record["labels"]
            entity_type = labels[0] if labels else "Unknown"

            org_id_str = node_data.pop("org_id", None)
            sync_status = node_data.pop("sync_status", "synced")
            node_data.pop("node_id", None)

            return GraphNode(
                node_id=node_id,
                entity_type=entity_type,
                properties=node_data,
                org_id=UUID(org_id_str) if org_id_str else None,
                sync_status=sync_status,
            )

    async def update_node(
        self,
        node_id: UUID,
        properties: dict[str, Any],
    ) -> GraphNode | None:
        """Update properties of an existing node.

        Args:
            node_id: Node identifier.
            properties: Properties to set/update.

        Returns:
            Updated GraphNode, or None if not found.
        """
        query = "MATCH (n {node_id: $node_id}) SET n += $props RETURN n, labels(n) as labels"
        async with self.driver.session() as session:
            result = await session.run(query, node_id=str(node_id), props=properties)
            record = await result.single()
            if record is None:
                return None

            node_data = dict(record["n"])
            labels = record["labels"]
            entity_type = labels[0] if labels else "Unknown"

            org_id_str = node_data.pop("org_id", None)
            sync_status = node_data.pop("sync_status", "synced")
            node_data.pop("node_id", None)

            return GraphNode(
                node_id=node_id,
                entity_type=entity_type,
                properties=node_data,
                org_id=UUID(org_id_str) if org_id_str else None,
                sync_status=sync_status,
            )

    async def delete_node(self, node_id: UUID) -> bool:
        """Delete a node and its relationships.

        Args:
            node_id: Node identifier.

        Returns:
            True if deleted, False if not found.
        """
        query = "MATCH (n {node_id: $node_id}) DETACH DELETE n RETURN count(n) as deleted"
        async with self.driver.session() as session:
            result = await session.run(query, node_id=str(node_id))
            record = await result.single()
            return record is not None and record["deleted"] > 0

    async def create_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> GraphRelationship:
        """Create a relationship between two nodes.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            rel_type: Relationship type.
            properties: Relationship properties.

        Returns:
            Created GraphRelationship.
        """
        props = properties or {}
        query = (
            "MATCH (a {node_id: $source_id}), (b {node_id: $target_id}) "
            f"CREATE (a)-[r:{rel_type} $props]->(b) "
            "RETURN r"
        )
        async with self.driver.session() as session:
            result = await session.run(
                query,
                source_id=str(source_id),
                target_id=str(target_id),
                props=props,
            )
            await result.consume()

        return GraphRelationship(
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            properties=props,
        )

    async def find_by_org(
        self,
        org_id: UUID,
        entity_type: str | None = None,
        *,
        limit: int = 100,
    ) -> list[GraphNode]:
        """Find nodes belonging to an organization.

        Args:
            org_id: Organization ID.
            entity_type: Optional entity type filter.
            limit: Maximum results.

        Returns:
            List of matching GraphNodes.
        """
        if entity_type:
            query = (
                f"MATCH (n:{entity_type} {{org_id: $org_id}}) "
                "RETURN n, labels(n) as labels LIMIT $limit"
            )
        else:
            query = "MATCH (n {org_id: $org_id}) RETURN n, labels(n) as labels LIMIT $limit"

        nodes: list[GraphNode] = []
        async with self.driver.session() as session:
            result = await session.run(query, org_id=str(org_id), limit=limit)
            async for record in result:
                node_data = dict(record["n"])
                labels = record["labels"]
                et = labels[0] if labels else "Unknown"
                node_id_str = node_data.pop("node_id", "")
                org_id_str = node_data.pop("org_id", None)
                sync_status = node_data.pop("sync_status", "synced")

                nodes.append(
                    GraphNode(
                        node_id=UUID(node_id_str),
                        entity_type=et,
                        properties=node_data,
                        org_id=UUID(org_id_str) if org_id_str else None,
                        sync_status=sync_status,
                    )
                )

        return nodes

    async def mark_sync_status(self, node_id: UUID, status: str) -> None:
        """Mark sync status for FK consistency tracking.

        Args:
            node_id: Node identifier.
            status: One of 'synced', 'pending_vector_sync', 'pending_graph_sync'.
        """
        query = "MATCH (n {node_id: $node_id}) SET n.sync_status = $status"
        async with self.driver.session() as session:
            await session.run(query, node_id=str(node_id), status=status)
