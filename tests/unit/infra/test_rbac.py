"""Tests for I1-4: RBAC 5 roles / 11 permissions complete matrix.

Acceptance: pytest tests/unit/infra/test_rbac.py -v
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.infra.auth.rbac import (
    ROLE_PERMISSION_MATRIX,
    Permission,
    Role,
    check_permission,
    get_role_permissions,
    resolve_role,
)


class TestRolePermissionMatrix:
    """RBAC matrix completeness and correctness."""

    def test_exactly_5_roles(self):
        assert len(Role) == 5

    def test_exactly_11_permissions(self):
        assert len(Permission) == 11

    def test_all_roles_have_matrix_entries(self):
        for role in Role:
            assert role in ROLE_PERMISSION_MATRIX, f"Missing matrix for {role}"

    def test_super_admin_has_all_permissions(self):
        perms = ROLE_PERMISSION_MATRIX[Role.SUPER_ADMIN]
        assert perms == frozenset(Permission)

    def test_org_admin_has_10_permissions(self):
        perms = ROLE_PERMISSION_MATRIX[Role.ORG_ADMIN]
        assert len(perms) == 10
        assert Permission.ADMIN_SYSTEM not in perms

    def test_manager_has_6_permissions(self):
        perms = ROLE_PERMISSION_MATRIX[Role.MANAGER]
        assert len(perms) == 6
        assert Permission.ADMIN_ACCESS not in perms
        assert Permission.MANAGE_MEMBERS in perms

    def test_member_has_4_permissions(self):
        perms = ROLE_PERMISSION_MATRIX[Role.MEMBER]
        assert len(perms) == 4
        assert Permission.MANAGE_MEMBERS not in perms
        assert Permission.WRITE_CONVERSATION in perms

    def test_viewer_has_2_permissions(self):
        perms = ROLE_PERMISSION_MATRIX[Role.VIEWER]
        assert len(perms) == 2
        assert perms == frozenset({Permission.READ_CONVERSATION, Permission.READ_KNOWLEDGE})

    def test_role_hierarchy_is_subset_chain(self):
        """Each lower role is a strict subset of the role above."""
        viewer = ROLE_PERMISSION_MATRIX[Role.VIEWER]
        member = ROLE_PERMISSION_MATRIX[Role.MEMBER]
        manager = ROLE_PERMISSION_MATRIX[Role.MANAGER]
        org_admin = ROLE_PERMISSION_MATRIX[Role.ORG_ADMIN]
        super_admin = ROLE_PERMISSION_MATRIX[Role.SUPER_ADMIN]

        assert viewer < member < manager < org_admin < super_admin

    def test_matrix_is_frozen(self):
        """Role permissions are frozensets (immutable)."""
        for role in Role:
            perms = ROLE_PERMISSION_MATRIX[role]
            assert isinstance(perms, frozenset)


class TestCheckPermission:
    """check_permission correctly evaluates access."""

    def test_admin_allowed_all(self):
        user_id = uuid4()
        for perm in Permission:
            result = check_permission(
                user_id=user_id,
                role=Role.SUPER_ADMIN,
                required=perm,
            )
            assert result.allowed is True

    def test_viewer_denied_write(self):
        result = check_permission(
            user_id=uuid4(),
            role=Role.VIEWER,
            required=Permission.WRITE_CONVERSATION,
        )
        assert result.allowed is False

    def test_member_allowed_read(self):
        result = check_permission(
            user_id=uuid4(),
            role=Role.MEMBER,
            required=Permission.READ_CONVERSATION,
        )
        assert result.allowed is True

    def test_extra_permissions_extend_role(self):
        result = check_permission(
            user_id=uuid4(),
            role=Role.VIEWER,
            required=Permission.WRITE_CONVERSATION,
            extra_permissions=frozenset({Permission.WRITE_CONVERSATION}),
        )
        assert result.allowed is True

    def test_result_contains_context(self):
        uid = uuid4()
        result = check_permission(
            user_id=uid,
            role=Role.MEMBER,
            required=Permission.READ_CONVERSATION,
        )
        assert result.user_id == uid
        assert result.role == Role.MEMBER
        assert result.required == Permission.READ_CONVERSATION
        assert Permission.READ_CONVERSATION in result.has_permissions


class TestGetRolePermissions:
    """get_role_permissions returns correct sets."""

    def test_known_role(self):
        perms = get_role_permissions(Role.MEMBER)
        assert len(perms) == 4

    def test_returns_frozenset(self):
        perms = get_role_permissions(Role.VIEWER)
        assert isinstance(perms, frozenset)


class TestResolveRole:
    """resolve_role parses role strings."""

    @pytest.mark.parametrize(
        "role_str,expected",
        [
            ("super_admin", Role.SUPER_ADMIN),
            ("org_admin", Role.ORG_ADMIN),
            ("manager", Role.MANAGER),
            ("member", Role.MEMBER),
            ("viewer", Role.VIEWER),
        ],
    )
    def test_valid_roles(self, role_str: str, expected: Role):
        assert resolve_role(role_str) == expected

    def test_invalid_role_returns_none(self):
        assert resolve_role("invalid_role") is None

    def test_empty_string_returns_none(self):
        assert resolve_role("") is None
