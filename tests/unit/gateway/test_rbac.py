"""RBAC permission check tests.

Phase 1 gate check: p1-rbac
Task card: G1-3

Validates:
- Admin API returns 403 (AuthorizationError) for non-admin users
- Admin API allows admin role
- Regular API does not require admin permission
- Unknown roles get no permissions
"""

from __future__ import annotations

import pytest

from src.gateway.middleware.rbac import Permission, RBACMiddleware, Role
from src.shared.errors import AuthorizationError


@pytest.mark.unit
class TestRoleDefinitions:
    """Role and permission constants."""

    def test_admin_role(self) -> None:
        assert Role.ADMIN == "admin"

    def test_member_role(self) -> None:
        assert Role.MEMBER == "member"

    def test_viewer_role(self) -> None:
        assert Role.VIEWER == "viewer"

    def test_admin_permission(self) -> None:
        assert Permission.ADMIN_ACCESS == "admin:access"

    def test_read_permission(self) -> None:
        assert Permission.READ == "read"

    def test_write_permission(self) -> None:
        assert Permission.WRITE == "write"


@pytest.mark.unit
class TestRBACMiddleware:
    """Enforce role-based access on admin paths."""

    @pytest.fixture
    def rbac(self) -> RBACMiddleware:
        return RBACMiddleware(admin_path_prefix="/api/v1/admin/")

    @pytest.mark.smoke
    def test_admin_api_denied_for_member(self, rbac: RBACMiddleware) -> None:
        with pytest.raises(AuthorizationError):
            rbac.check_access(
                path="/api/v1/admin/users",
                role=Role.MEMBER,
                permissions=frozenset({Permission.READ, Permission.WRITE}),
            )

    @pytest.mark.smoke
    def test_admin_api_denied_for_viewer(self, rbac: RBACMiddleware) -> None:
        with pytest.raises(AuthorizationError):
            rbac.check_access(
                path="/api/v1/admin/users",
                role=Role.VIEWER,
                permissions=frozenset({Permission.READ}),
            )

    def test_admin_api_allowed_for_admin(self, rbac: RBACMiddleware) -> None:
        rbac.check_access(
            path="/api/v1/admin/users",
            role=Role.ADMIN,
            permissions=frozenset({Permission.READ, Permission.WRITE, Permission.ADMIN_ACCESS}),
        )

    def test_regular_api_allowed_for_member(self, rbac: RBACMiddleware) -> None:
        rbac.check_access(
            path="/api/v1/conversations",
            role=Role.MEMBER,
            permissions=frozenset({Permission.READ, Permission.WRITE}),
        )

    def test_regular_api_allowed_for_viewer(self, rbac: RBACMiddleware) -> None:
        rbac.check_access(
            path="/api/v1/conversations",
            role=Role.VIEWER,
            permissions=frozenset({Permission.READ}),
        )

    def test_error_includes_required_permission(self, rbac: RBACMiddleware) -> None:
        with pytest.raises(AuthorizationError) as exc_info:
            rbac.check_access(
                path="/api/v1/admin/settings",
                role=Role.MEMBER,
                permissions=frozenset({Permission.READ}),
            )
        assert "admin:access" in str(exc_info.value)

    def test_get_role_permissions_admin(self) -> None:
        perms = RBACMiddleware.get_role_permissions(Role.ADMIN)
        assert Permission.ADMIN_ACCESS in perms
        assert Permission.READ in perms
        assert Permission.WRITE in perms

    def test_get_role_permissions_member(self) -> None:
        perms = RBACMiddleware.get_role_permissions(Role.MEMBER)
        assert Permission.READ in perms
        assert Permission.WRITE in perms
        assert Permission.ADMIN_ACCESS not in perms

    def test_get_role_permissions_viewer(self) -> None:
        perms = RBACMiddleware.get_role_permissions(Role.VIEWER)
        assert Permission.READ in perms
        assert Permission.WRITE not in perms

    def test_unknown_role_gets_empty_permissions(self) -> None:
        perms = RBACMiddleware.get_role_permissions("unknown")
        assert len(perms) == 0
