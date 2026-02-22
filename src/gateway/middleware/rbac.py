"""RBAC permission check middleware.

Task card: G1-3
- No admin permission + admin path -> 403
- Admin role + admin path -> allowed
- Regular paths -> no admin check required

Role hierarchy:
  admin  -> read, write, admin:access
  member -> read, write
  viewer -> read
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse, Response

from src.shared.errors import AuthorizationError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request


class Role:
    """Role constants."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission:
    """Permission constants."""

    READ = "read"
    WRITE = "write"
    ADMIN_ACCESS = "admin:access"


_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.ADMIN: frozenset({Permission.READ, Permission.WRITE, Permission.ADMIN_ACCESS}),
    Role.MEMBER: frozenset({Permission.READ, Permission.WRITE}),
    Role.VIEWER: frozenset({Permission.READ}),
}


class RBACMiddleware:
    """Enforce role-based access control on admin paths.

    Can be used as a standalone checker (check_access) or as a
    PostAuthMiddleware callable for the gateway middleware chain.
    """

    def __init__(self, *, admin_path_prefix: str = "/api/v1/admin/") -> None:
        self._admin_prefix = admin_path_prefix

    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """PostAuthMiddleware entry point.

        Reads role from request.state (set by JWT middleware),
        checks RBAC, and either passes through or returns 403.
        """
        path = request.url.path
        role = getattr(request.state, "role", "member")
        permissions = self.get_role_permissions(role)

        try:
            self.check_access(path=path, role=role, permissions=permissions)
        except AuthorizationError:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "FORBIDDEN",
                    "message": f"Admin access required (role={role})",
                },
            )

        return await call_next(request)

    def check_access(
        self,
        *,
        path: str,
        role: str,
        permissions: frozenset[str],
    ) -> None:
        """Check access. Raises AuthorizationError if denied."""
        if path.startswith(self._admin_prefix) and Permission.ADMIN_ACCESS not in permissions:
            raise AuthorizationError(Permission.ADMIN_ACCESS)

    @staticmethod
    def get_role_permissions(role: str) -> frozenset[str]:
        """Return permission set for a given role."""
        return _ROLE_PERMISSIONS.get(role, frozenset())
