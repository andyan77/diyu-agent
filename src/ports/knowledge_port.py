"""KnowledgePort - Knowledge Stores read interface.

Soft dependency (degradable). When unavailable, Brain continues
with personal memory only, losing domain knowledge depth.
Day-1 implementation: Returns empty KnowledgeBundle.
Real implementation: Diyu Resolver (Neo4j + Qdrant).

See: docs/architecture/02-Knowledge Section 5.4.1 (KnowledgeBundle schema)
     docs/architecture/00-*.md Section 12.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.types import KnowledgeBundle, OrganizationContext


class KnowledgePort(ABC):
    """Port: Knowledge Stores read operations."""

    @abstractmethod
    async def resolve(
        self,
        profile_id: str,
        query: str,
        org_context: OrganizationContext,
    ) -> KnowledgeBundle:
        """Resolve knowledge relevant to query within org context.

        Args:
            profile_id: Knowledge profile identifier.
            query: Semantic query string.
            org_context: Organization context for scoping.

        Returns:
            KnowledgeBundle with entities, relationships, semantic contents.
        """

    @abstractmethod
    async def capabilities(self) -> set[str]:
        """Return set of capabilities this knowledge provider supports."""
