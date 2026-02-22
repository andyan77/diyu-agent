"""Adapter bridging Gateway's KnowledgeWritePort protocol to Knowledge layer.

Composition root creates this adapter and passes it to the Knowledge Admin
API router. This adapter satisfies the structural typing protocol defined
in ``src.gateway.api.admin.knowledge.KnowledgeWritePort``.

When Neo4j/Qdrant are unavailable (local dev without docker-compose),
the adapter operates in degraded mode with in-process storage.
When the adapters are provided, it delegates to FK-consistent dual-write
via ``FKRegistry``.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


def _semantic_text(entity_type: str, properties: dict[str, Any]) -> str:
    """Extract a semantic text string from entity properties for embedding.

    Concatenates all string-valued properties into a single text blob
    prefixed by entity_type.  Non-string values are JSON-serialised.
    """
    parts = [entity_type]
    for key, val in sorted(properties.items()):
        if key.startswith("_") or key in ("created_by", "updated_by"):
            continue
        if isinstance(val, str):
            parts.append(val)
        else:
            parts.append(json.dumps(val, ensure_ascii=False, default=str))
    return " ".join(parts)


class KnowledgeWriteAdapter:
    """Gateway-facing adapter for knowledge CRUD operations.

    Satisfies ``KnowledgeWritePort`` protocol via structural typing.

    When ``neo4j``, ``qdrant``, and ``fk_registry`` are provided the adapter
    delegates to the FK-consistent dual-write path.
    Otherwise it falls back to in-process dict storage (degraded mode).

    Constructor accepts duck-typed adapters (Any) to avoid importing
    Infrastructure layer types -- preserving the layer boundary rule.
    """

    def __init__(
        self,
        neo4j: Any = None,
        qdrant: Any = None,
        fk_registry: Any = None,
        embedder: Any = None,
    ) -> None:
        self._neo4j = neo4j
        self._qdrant = qdrant
        self._fk_registry = fk_registry
        self._embedder = embedder
        # In-memory fallback when external stores are unavailable
        self._store: dict[UUID, dict[str, Any]] = {}

    @property
    def _has_stores(self) -> bool:
        """True only if external stores are wired AND connected."""
        if self._neo4j is None or self._fk_registry is None:
            return False
        # Neo4j driver is None until connect() succeeds
        return self._neo4j._driver is not None

    # -- CREATE --

    async def create_entry(
        self,
        *,
        org_id: UUID,
        entity_type: str,
        properties: dict[str, Any],
        user_id: UUID,
    ) -> dict[str, Any]:
        entry_id = uuid4()

        if self._has_stores:
            # Build semantic content + embedding for Qdrant dual-write
            semantic = _semantic_text(entity_type, properties)
            embedding = self._embedder.embed(semantic) if self._embedder else None

            result = await self._fk_registry.write_with_fk(
                entity_type=entity_type,
                node_id=entry_id,
                properties={**properties, "created_by": str(user_id)},
                org_id=org_id,
                semantic_content=semantic,
                embedding=embedding,
            )
            entry = {
                "entry_id": entry_id,
                "entity_type": entity_type,
                "properties": properties,
                "org_id": org_id,
                "created_by": user_id,
                "sync_status": result.sync_status,
            }
            logger.info(
                "Knowledge entry created (dual-write): %s (type=%s, org=%s, sync=%s)",
                entry_id,
                entity_type,
                org_id,
                result.sync_status,
            )
        else:
            entry = {
                "entry_id": entry_id,
                "entity_type": entity_type,
                "properties": properties,
                "org_id": org_id,
                "created_by": user_id,
            }
            self._store[entry_id] = entry
            logger.info(
                "Knowledge entry created (in-memory): %s (type=%s, org=%s)",
                entry_id,
                entity_type,
                org_id,
            )

        return entry

    # -- READ single --

    async def get_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
    ) -> dict[str, Any] | None:
        if self._has_stores:
            node = await self._neo4j.get_node(entry_id)
            if node is None or node.org_id != org_id:
                return None
            return {
                "entry_id": node.node_id,
                "entity_type": node.entity_type,
                "properties": node.properties,
                "org_id": node.org_id,
            }

        entry = self._store.get(entry_id)
        if entry and entry.get("org_id") == org_id:
            return entry
        return None

    # -- UPDATE --

    async def update_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
        properties: dict[str, Any],
        user_id: UUID,
    ) -> dict[str, Any] | None:
        if self._has_stores:
            existing = await self._neo4j.get_node(entry_id)
            if existing is None or existing.org_id != org_id:
                return None

            # Merge properties for the update
            merged_props = {**existing.properties, **properties}

            # Use FK registry for consistent dual-write update
            semantic = _semantic_text(existing.entity_type, merged_props)
            embedding = self._embedder.embed(semantic) if self._embedder else None

            result = await self._fk_registry.update_with_fk(
                node_id=entry_id,
                properties={**properties, "updated_by": str(user_id)},
                semantic_content=semantic,
                embedding=embedding,
            )
            updated = result.graph_node
            return {
                "entry_id": updated.node_id,
                "entity_type": updated.entity_type,
                "properties": updated.properties,
                "org_id": updated.org_id,
            }

        entry = self._store.get(entry_id)
        if entry is None or entry.get("org_id") != org_id:
            return None
        entry["properties"] = {**entry.get("properties", {}), **properties}
        entry["updated_by"] = user_id
        return entry

    # -- DELETE --

    async def delete_entry(
        self,
        *,
        org_id: UUID,
        entry_id: UUID,
        user_id: UUID,
    ) -> bool:
        if self._has_stores:
            existing = await self._neo4j.get_node(entry_id)
            if existing is None or existing.org_id != org_id:
                return False
            deleted: bool = await self._fk_registry.delete_with_fk(entry_id)
            if deleted:
                logger.info(
                    "Knowledge entry deleted (dual-write): %s by user %s",
                    entry_id,
                    user_id,
                )
            return deleted

        entry = self._store.get(entry_id)
        if entry is None or entry.get("org_id") != org_id:
            return False
        del self._store[entry_id]
        logger.info(
            "Knowledge entry deleted (in-memory): %s by user %s",
            entry_id,
            user_id,
        )
        return True

    # -- LIST --

    async def list_entries(
        self,
        *,
        org_id: UUID,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if self._has_stores:
            nodes = await self._neo4j.find_by_org(
                org_id,
                entity_type,
                limit=limit + offset,
            )
            results = [
                {
                    "entry_id": n.node_id,
                    "entity_type": n.entity_type,
                    "properties": n.properties,
                    "org_id": n.org_id,
                }
                for n in nodes
            ]
            return results[offset : offset + limit]

        results = [
            e
            for e in self._store.values()
            if e.get("org_id") == org_id
            and (entity_type is None or e.get("entity_type") == entity_type)
        ]
        return results[offset : offset + limit]
