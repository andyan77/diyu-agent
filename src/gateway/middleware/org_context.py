"""OrgContext middleware - extracts and validates organization context.

Task card: G1-2
- Extract org_id from JWT payload
- Set app.current_org_id for RLS enforcement
- Provide OrgContext to downstream request handlers
- Reject requests with missing/invalid org context

Dependencies: I1-1 (org DDL), G1-5 (app factory)
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID  # noqa: TC003 -- used at runtime in dataclass fields

from src.shared.errors import AuthenticationError, OrgIsolationError


@dataclass(frozen=True)
class OrgContext:
    """Minimal organization context extracted from JWT.

    Used by Gateway middleware to scope all downstream operations
    to a single tenant. The full OrganizationContext (with settings,
    model access, etc.) is assembled by OrgContextPort.
    """

    user_id: UUID
    org_id: UUID
    role: str = "member"


class OrgContextMiddleware:
    """Extract and validate organization context from request state.

    After JWTAuthMiddleware sets request.state.user_id and
    request.state.org_id, this middleware creates an OrgContext
    and validates the org_id is present.

    Exempt paths (healthz, docs) skip context extraction.
    """

    def __init__(
        self,
        *,
        exempt_paths: list[str] | None = None,
    ) -> None:
        self._exempt_paths = set(exempt_paths or [])

    def extract_context(
        self,
        *,
        user_id: UUID | None,
        org_id: UUID | None,
        path: str,
        role: str = "member",
    ) -> OrgContext | None:
        """Extract OrgContext from request state.

        Args:
            user_id: Authenticated user ID (from JWT).
            org_id: Organization ID (from JWT).
            path: Request path.
            role: User role within the organization.

        Returns:
            OrgContext if path is not exempt, None for exempt paths.

        Raises:
            AuthenticationError: If user_id is missing on non-exempt path.
            OrgIsolationError: If org_id is missing on non-exempt path.
        """
        if path in self._exempt_paths:
            return None

        if user_id is None:
            raise AuthenticationError("User ID not found in request context")

        if org_id is None:
            raise OrgIsolationError("Organization ID is required")

        return OrgContext(
            user_id=user_id,
            org_id=org_id,
            role=role,
        )
