"""OrgContextPort - Organization context assembly interface.

Soft dependency. When unavailable, degrades to default single-tenant context.
Day-1 implementation: Returns default single-tenant stub.
Real implementation: Gateway JWT parsing + org model query.

See: docs/architecture/05-Gateway Section 4.2 (OrganizationContext schema)
     docs/architecture/00-*.md Section 12.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from src.shared.types import OrganizationContext


class OrgContextPort(ABC):
    """Port: Organization context assembly."""

    @abstractmethod
    async def get_org_context(
        self,
        user_id: UUID,
        org_id: UUID,
        token: str,
    ) -> OrganizationContext:
        """Assemble organization context from auth token.

        Args:
            user_id: Authenticated user ID.
            org_id: Target organization ID.
            token: JWT or session token.

        Returns:
            OrganizationContext with permissions, settings, model access.
        """
