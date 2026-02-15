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

from src.shared.errors import AuthorizationError


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
    """Enforce role-based access control on admin paths."""

    def __init__(self, *, admin_path_prefix: str = "/api/v1/admin/") -> None:
        self._admin_prefix = admin_path_prefix

    def check_access(
        self,
        *,
        path: str,
        role: str,
        permissions: frozenset[str],
    ) -> None:
        """Check access. Raises AuthorizationError if denied."""
        if path.startswith(self._admin_prefix):
            if Permission.ADMIN_ACCESS not in permissions:
                raise AuthorizationError(Permission.ADMIN_ACCESS)

    @staticmethod
    def get_role_permissions(role: str) -> frozenset[str]:
        """Return permission set for a given role."""
        return _ROLE_PERMISSIONS.get(role, frozenset())
