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


__all__ = [
    "KnowledgeBundle",
    "MemoryItem",
    "ModelAccess",
    "Observation",
    "OrganizationContext",
    "ResolutionMetadata",
    "WriteReceipt",
]
