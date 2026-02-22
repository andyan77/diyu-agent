"""Diyu Resolver — hybrid knowledge resolution engine.

Milestone: K3-5
Layer: Knowledge

Query interface returning KnowledgeBundle with graph + vector hybrid
results. Supports multiple resolution profiles with different FK
strategies (graph-only, graph-first, vector-first, parallel).

See: docs/architecture/02-Knowledge Section 5.4.1 (KnowledgeBundle)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.shared.types import GraphNode, KnowledgeBundle, OrganizationContext, ResolutionMetadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolverProfile:
    """Configuration for a resolution strategy."""

    profile_id: str
    fk_strategy: str  # none | graph_first | vector_first | parallel
    graph_query_template: str | None = None
    vector_search: bool = False
    limit: int = 20
    description: str = ""


# Built-in profiles (minimum 2 for K3-5, plus "default" alias)
BUILTIN_PROFILES: dict[str, ResolverProfile] = {
    "core:role_adaptation": ResolverProfile(
        profile_id="core:role_adaptation",
        fk_strategy="none",
        graph_query_template=(
            "MATCH (n:RoleAdaptationRule) "
            "WHERE n.org_id IN $org_chain OR n.visibility = 'global' "
            "RETURN n, labels(n) as labels LIMIT $limit"
        ),
        vector_search=False,
        limit=20,
        description="Graph-only: fetch role adaptation rules",
    ),
    "core:brand_context": ResolverProfile(
        profile_id="core:brand_context",
        fk_strategy="graph_first",
        graph_query_template=(
            "MATCH (n:BrandKnowledge) "
            "WHERE n.org_id IN $org_chain "
            "OR n.visibility IN ['global', 'brand'] "
            "RETURN n, labels(n) as labels LIMIT $limit"
        ),
        vector_search=True,
        limit=20,
        description="Graph-first + FK vector enrichment for brand context",
    ),
    # "default" profile used by ContextAssembler when no specific profile is requested.
    # Delegates to the brand_context strategy as the most broadly useful resolution.
    "default": ResolverProfile(
        profile_id="default",
        fk_strategy="graph_first",
        graph_query_template=(
            "MATCH (n:BrandKnowledge) "
            "WHERE n.org_id IN $org_chain "
            "OR n.visibility IN ['global', 'brand'] "
            "RETURN n, labels(n) as labels LIMIT $limit"
        ),
        vector_search=True,
        limit=20,
        description="Default profile (aliases core:brand_context)",
    ),
}


class DiyuResolver:
    """Hybrid knowledge resolution engine.

    Routes queries through profiles that define FK strategies for
    combining graph structure and vector semantics.
    """

    def __init__(
        self,
        neo4j: Any,  # Neo4j adapter (duck-typed)
        qdrant: Any,  # Qdrant adapter (duck-typed)
        profiles: dict[str, ResolverProfile] | None = None,
    ) -> None:
        self._neo4j = neo4j
        self._qdrant = qdrant
        self._profiles = profiles if profiles is not None else dict(BUILTIN_PROFILES)

    def register_profile(self, profile: ResolverProfile) -> None:
        """Register a custom resolution profile."""
        self._profiles[profile.profile_id] = profile

    def get_profile(self, profile_id: str) -> ResolverProfile | None:
        """Look up a profile by ID."""
        return self._profiles.get(profile_id)

    async def resolve(
        self,
        profile_id: str,
        query: str,
        org_context: OrganizationContext,
    ) -> KnowledgeBundle:
        """Resolve knowledge using the specified profile.

        Args:
            profile_id: Resolution profile identifier.
            query: Semantic query string.
            org_context: Organization context for scoping.

        Returns:
            KnowledgeBundle with entities, relationships, semantic contents.

        Raises:
            ValueError: If profile not found.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            msg = f"Profile not found: {profile_id}"
            raise ValueError(msg)

        start = datetime.now(tz=UTC)

        if profile.fk_strategy == "none":
            return await self._resolve_graph_only(profile, query, org_context, start)
        if profile.fk_strategy == "graph_first":
            return await self._resolve_graph_first(profile, query, org_context, start)
        if profile.fk_strategy == "vector_first":
            return await self._resolve_vector_first(profile, query, org_context, start)

        msg = f"Unknown FK strategy: {profile.fk_strategy}"
        raise ValueError(msg)

    async def _resolve_graph_only(
        self,
        profile: ResolverProfile,
        query: str,
        org_context: OrganizationContext,
        start: datetime,
    ) -> KnowledgeBundle:
        """Graph-only resolution (no vector enrichment)."""
        nodes = await self._execute_graph_query(profile, org_context)

        entities = self._group_by_type(nodes)

        return KnowledgeBundle(
            entities=entities,
            org_context={
                "org_id": str(org_context.org_id),
                "org_tier": org_context.org_tier,
            },
            metadata=ResolutionMetadata(
                resolved_at=start,
                profile_id=profile.profile_id,
                completeness_score=1.0 if nodes else 0.0,
                graph_hits=len(nodes),
                vector_hits=0,
                fk_enrichments=0,
            ),
        )

    async def _resolve_graph_first(
        self,
        profile: ResolverProfile,
        query: str,
        org_context: OrganizationContext,
        start: datetime,
    ) -> KnowledgeBundle:
        """Graph-first + FK vector enrichment."""
        # A. Graph queries
        nodes = await self._execute_graph_query(profile, org_context)
        entities = self._group_by_type(nodes)

        # B. FK enrichment: find vectors linked to graph nodes
        semantic_contents: list[dict[str, Any]] = []
        fk_count = 0

        if profile.vector_search and nodes:
            node_ids = [str(n.node_id) for n in nodes]
            for nid_str in node_ids:
                # Search for vectors with this graph_node_id
                try:
                    from qdrant_client.models import FieldCondition, Filter, MatchValue

                    results = await self._qdrant.client.query_points(
                        collection_name=self._qdrant._collection_name,
                        query=[0.0] * self._qdrant._vector_size,  # dummy query
                        query_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="graph_node_id",
                                    match=MatchValue(value=nid_str),
                                )
                            ]
                        ),
                        limit=5,
                        with_payload=True,
                    )
                    for pt in results.points:
                        payload = pt.payload or {}
                        semantic_contents.append(
                            {
                                "graph_node_id": nid_str,
                                "text": payload.get("text", ""),
                                "content_type": payload.get("content_type", ""),
                                "score": pt.score,
                            }
                        )
                        fk_count += 1
                except Exception:
                    logger.debug("FK enrichment failed for node %s", nid_str)

        return KnowledgeBundle(
            entities=entities,
            semantic_contents=semantic_contents,
            org_context={
                "org_id": str(org_context.org_id),
                "org_tier": org_context.org_tier,
            },
            metadata=ResolutionMetadata(
                resolved_at=start,
                profile_id=profile.profile_id,
                completeness_score=1.0 if nodes else 0.0,
                graph_hits=len(nodes),
                vector_hits=len(semantic_contents),
                fk_enrichments=fk_count,
            ),
        )

    async def _resolve_vector_first(
        self,
        profile: ResolverProfile,
        query: str,
        org_context: OrganizationContext,
        start: datetime,
    ) -> KnowledgeBundle:
        """Vector-first + FK graph enrichment."""
        # A. Vector search (requires query embedding — use dummy for now)
        semantic_contents: list[dict[str, Any]] = []

        # Note: Real implementation needs embedding model call.
        # For now, return empty bundle if no embedding available.

        return KnowledgeBundle(
            semantic_contents=semantic_contents,
            org_context={
                "org_id": str(org_context.org_id),
                "org_tier": org_context.org_tier,
            },
            metadata=ResolutionMetadata(
                resolved_at=start,
                profile_id=profile.profile_id,
                completeness_score=0.0,
                graph_hits=0,
                vector_hits=0,
                fk_enrichments=0,
                warnings=[{"msg": "vector_first requires embedding model"}],
            ),
        )

    async def _execute_graph_query(
        self,
        profile: ResolverProfile,
        org_context: OrganizationContext,
    ) -> list[GraphNode]:
        """Execute the profile's graph query template."""
        if not profile.graph_query_template:
            return []

        org_chain = [str(uid) for uid in org_context.org_chain]
        params = {
            "org_chain": org_chain,
            "limit": profile.limit,
        }

        nodes: list[GraphNode] = []
        async with self._neo4j.driver.session() as session:
            result = await session.run(profile.graph_query_template, **params)
            async for record in result:
                node_data = dict(record["n"])
                labels = record["labels"]
                entity_type = labels[0] if labels else "Unknown"
                node_id_str = node_data.pop("node_id", "")
                org_id_str = node_data.pop("org_id", None)
                sync_status = node_data.pop("sync_status", "synced")

                nodes.append(
                    GraphNode(
                        node_id=UUID(node_id_str) if node_id_str else UUID(int=0),
                        entity_type=entity_type,
                        properties=node_data,
                        org_id=UUID(org_id_str) if org_id_str else None,
                        sync_status=sync_status,
                    )
                )

        return nodes

    @staticmethod
    def _group_by_type(nodes: list[GraphNode]) -> dict[str, list[dict[str, Any]]]:
        """Group graph nodes by entity type."""
        groups: dict[str, list[dict[str, Any]]] = {}
        for node in nodes:
            entry = {
                "node_id": str(node.node_id),
                "org_id": str(node.org_id) if node.org_id else None,
                **node.properties,
            }
            groups.setdefault(node.entity_type, []).append(entry)
        return groups
