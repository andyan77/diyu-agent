"""Knowledge Write API — controlled write with ACL, idempotency, audit.

Milestone: K3-4
Layer: Knowledge

POST endpoint for knowledge entry creation with double-write FK
consistency, idempotency keys, and audit receipts.

See: docs/architecture/02-Knowledge Section 5.4.2 (Write API)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from src.knowledge.registry.entity_type import EntityTypeRegistry
    from src.knowledge.sync.fk_registry import FKRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnowledgeWriteRequest:
    """Request to create a knowledge entry."""

    entity_type: str
    properties: dict[str, Any]
    org_id: UUID
    visibility: str  # global | brand | region | store
    idempotency_key: str
    source: str  # admin | erp | skill | batch | promotion
    semantic_content: str | None = None
    relationships: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class KnowledgeWriteReceipt:
    """Audit receipt for a knowledge write."""

    write_id: UUID
    graph_node_id: UUID
    entity_type: str
    org_id: UUID
    visibility: str
    idempotency_key: str
    source: str
    timestamp: datetime
    sync_status: str
    properties_hash: str


@dataclass(frozen=True)
class KnowledgeWriteResponse:
    """Response from a knowledge write."""

    graph_node_id: UUID
    version: int
    write_receipt: KnowledgeWriteReceipt


def _hash_properties(properties: dict[str, Any]) -> str:
    """Create a deterministic hash of properties for idempotency."""
    import json

    canonical = json.dumps(properties, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class KnowledgeWriteService:
    """Service for controlled knowledge writes.

    Validates ACL, enforces idempotency, writes through FK registry,
    and generates audit receipts.
    """

    def __init__(
        self,
        fk_registry: FKRegistry,
        entity_registry: EntityTypeRegistry,
    ) -> None:
        self._fk_registry = fk_registry
        self._entity_registry = entity_registry
        self._receipts: dict[str, KnowledgeWriteResponse] = {}

    async def write(
        self,
        request: KnowledgeWriteRequest,
        *,
        user_id: UUID | None = None,
        embedding: list[float] | None = None,
    ) -> KnowledgeWriteResponse:
        """Execute a controlled knowledge write.

        Args:
            request: Write request with entity data.
            user_id: Requesting user (for audit).
            embedding: Pre-computed vector embedding.

        Returns:
            KnowledgeWriteResponse with node ID and receipt.

        Raises:
            ValueError: If validation fails.
            PermissionError: If entity type is not writable.
        """
        # 1. Entity type validation
        if not self._entity_registry.is_writable(request.entity_type):
            msg = f"Entity type not writable: {request.entity_type}"
            raise PermissionError(msg)

        # 2. Idempotency check
        props_hash = _hash_properties(request.properties)
        idempotency_hash = f"{request.entity_type}:{request.org_id}:{request.idempotency_key}"

        cached = self._receipts.get(idempotency_hash)
        if cached is not None:
            if cached.write_receipt.properties_hash == props_hash:
                return cached  # Idempotent return
            msg = "Idempotency key conflict: same key, different properties"
            raise ValueError(msg)

        # 3. Schema validation
        entity_def = self._entity_registry.get(request.entity_type)
        if entity_def and entity_def.schema:
            required = entity_def.schema.get("required_properties", [])
            for prop_name in required:
                if prop_name not in request.properties:
                    msg = f"Missing required property: {prop_name}"
                    raise ValueError(msg)

        # 4. Write via FK registry
        node_id = uuid4()
        write_props = {
            **request.properties,
            "visibility": request.visibility,
        }

        result = await self._fk_registry.write_with_fk(
            entity_type=request.entity_type,
            node_id=node_id,
            properties=write_props,
            org_id=request.org_id,
            semantic_content=request.semantic_content,
            embedding=embedding,
        )

        # 5. Generate receipt
        now = datetime.now(tz=UTC)
        receipt = KnowledgeWriteReceipt(
            write_id=uuid4(),
            graph_node_id=result.graph_node.node_id,
            entity_type=request.entity_type,
            org_id=request.org_id,
            visibility=request.visibility,
            idempotency_key=request.idempotency_key,
            source=request.source,
            timestamp=now,
            sync_status=result.sync_status,
            properties_hash=props_hash,
        )

        response = KnowledgeWriteResponse(
            graph_node_id=result.graph_node.node_id,
            version=1,
            write_receipt=receipt,
        )

        # 6. Cache for idempotency
        self._receipts[idempotency_hash] = response

        logger.info(
            "Knowledge write: %s/%s org=%s sync=%s",
            request.entity_type,
            result.graph_node.node_id,
            request.org_id,
            result.sync_status,
        )
        return response
