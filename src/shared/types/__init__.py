"""Shared domain types used across layers.

These types flow through Port interfaces and must remain stable.
Schema changes follow Expand-Contract migration (Section 12.5).

See: docs/architecture/01-Brain Section 2.3.1 (MemoryItem)
     docs/architecture/02-Knowledge Section 5.4.1 (KnowledgeBundle)
     docs/architecture/05-Gateway Section 4.2 (OrganizationContext)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

# -- Memory Core types (SSOT-A) --


@dataclass(frozen=True)
class MemoryItem:
    """Personal memory record (Schema v1).

    See: 01-Brain Section 2.3.1
    """

    memory_id: UUID
    user_id: UUID
    memory_type: str  # observation | preference | pattern | summary | agent_experience
    content: str
    valid_at: datetime
    invalid_at: datetime | None = None
    confidence: float = 1.0
    source_sessions: list[UUID] = field(default_factory=list)
    superseded_by: UUID | None = None
    version: int = 1
    provenance: dict[str, Any] | None = None
    epistemic_type: str = "fact"  # fact | opinion | preference | outdated (v3.5.2)


@dataclass(frozen=True)
class Observation:
    """Input observation to be written to memory."""

    content: str
    memory_type: str = "observation"
    source_session_id: UUID | None = None
    confidence: float = 1.0


@dataclass(frozen=True)
class WriteReceipt:
    """Receipt from a memory write operation."""

    memory_id: UUID
    version: int
    written_at: datetime


# -- Knowledge Store DTOs (shared between Knowledge + Infrastructure) --


@dataclass(frozen=True)
class GraphNode:
    """Representation of a knowledge graph node."""

    node_id: UUID
    entity_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    org_id: UUID | None = None
    sync_status: str = "synced"  # synced | pending_vector_sync


@dataclass(frozen=True)
class GraphRelationship:
    """Representation of a knowledge graph relationship."""

    source_id: UUID
    target_id: UUID
    rel_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorPoint:
    """Representation of a vector store point."""

    point_id: UUID
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)
    graph_node_id: UUID | None = None  # FK to Neo4j node
    score: float = 0.0


# -- Knowledge types (SSOT-B) --


@dataclass(frozen=True)
class KnowledgeBundle:
    """Resolved knowledge package (Schema v1).

    See: 02-Knowledge Section 5.4.1
    """

    entities: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    semantic_contents: list[dict[str, Any]] = field(default_factory=list)
    media_contents: list[dict[str, Any]] = field(default_factory=list)  # v3.6 optional
    org_context: dict[str, Any] | None = None
    metadata: ResolutionMetadata | None = None


@dataclass(frozen=True)
class ResolutionMetadata:
    """Metadata about knowledge resolution."""

    resolved_at: datetime | None = None
    profile_id: str = ""
    completeness_score: float = 0.0
    org_chain_used: list[UUID] = field(default_factory=list)
    graph_hits: int = 0
    vector_hits: int = 0
    fk_enrichments: int = 0
    warnings: list[dict[str, Any]] = field(default_factory=list)


# -- Organization context types --


@dataclass(frozen=True)
class ModelAccess:
    """Model access configuration for an organization."""

    allowed_models: list[str] = field(default_factory=list)
    default_model: str = ""
    budget_monthly_tokens: int = 0
    budget_tool_amount: float = 0.0  # v3.6 new


@dataclass(frozen=True)
class OrganizationContext:
    """Organization context assembled by Gateway (Schema v1).

    See: 05-Gateway Section 4.2
    """

    user_id: UUID
    org_id: UUID
    org_tier: str  # platform | brand_hq | brand_dept | regional_agent | franchise_store
    org_path: str  # ltree path string
    org_chain: list[UUID] = field(default_factory=list)
    brand_id: UUID | None = None
    role: str = ""
    permissions: frozenset[str] = field(default_factory=frozenset)
    org_settings: dict[str, Any] | None = None
    model_access: ModelAccess | None = None
    experiment_context: dict[str, Any] | None = None


# -- Promotion types (Cross-SSOT: Memory Core -> Knowledge Stores) --


@dataclass(frozen=True)
class PromotionReceipt:
    """Receipt from a memory-to-knowledge promotion operation.

    See: 02-Knowledge Section 7.2 (Promotion Pipeline)
    """

    proposal_id: UUID
    source_memory_id: UUID
    target_knowledge_id: UUID | None  # None if promotion failed/rejected
    status: str  # promoted | sanitize_failed | expired | rejected | write_failed
    promoted_at: datetime | None = None
    rejection_reason: str | None = None


# -- Object Storage types (v3.6 Extension Port) --


@dataclass(frozen=True)
class PresignedUploadURL:
    """Presigned URL for object upload.

    See: 00-Overview Section 12.3.1 (ObjectStoragePort)
    """

    url: str
    expires_at: datetime
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PresignedDownloadURL:
    """Presigned URL for object download."""

    url: str
    expires_at: datetime


@dataclass(frozen=True)
class BatchDeleteResult:
    """Result of a batch delete operation."""

    deleted: list[str] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ObjectMetadata:
    """Metadata about a stored object."""

    size_bytes: int
    mime_type: str
    checksum_sha256: str
    last_modified: datetime
    storage_class: str = "STANDARD"


__all__ = [
    "BatchDeleteResult",
    "GraphNode",
    "GraphRelationship",
    "KnowledgeBundle",
    "MemoryItem",
    "ModelAccess",
    "ObjectMetadata",
    "Observation",
    "OrganizationContext",
    "PresignedDownloadURL",
    "PresignedUploadURL",
    "PromotionReceipt",
    "ResolutionMetadata",
    "VectorPoint",
    "WriteReceipt",
]
