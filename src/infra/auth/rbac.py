"""RBAC permission matrix: 5 roles x 11 permission codes.

Task card: I1-4
- 5 roles: super_admin, org_admin, manager, member, viewer
- 11 permission codes mapped to roles
- Permission check formula: user_permissions union role_permissions
- LAW constraint: role definitions are immutable at runtime

Architecture: 06 Section 1.3-1.4
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from uuid import UUID  # noqa: TC003 -- used at runtime in dataclass fields


@unique
class Permission(Enum):
    """11 permission codes for Phase 1 RBAC."""

    # Read
    READ_CONVERSATION = "conversation:read"
    READ_KNOWLEDGE = "knowledge:read"
    READ_AUDIT = "audit:read"

    # Write
    WRITE_CONVERSATION = "conversation:write"
    WRITE_KNOWLEDGE = "knowledge:write"

    # Manage
    MANAGE_MEMBERS = "members:manage"
    MANAGE_SETTINGS = "settings:manage"
    MANAGE_ROLES = "roles:manage"

    # Admin
    ADMIN_ACCESS = "admin:access"
    ADMIN_BILLING = "admin:billing"
    ADMIN_SYSTEM = "admin:system"


@unique
class Role(Enum):
    """5 RBAC roles (LAW constraint: immutable at runtime)."""

    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


# LAW: Role-Permission matrix is frozen. Changes require a migration.
ROLE_PERMISSION_MATRIX: dict[Role, frozenset[Permission]] = {
    Role.SUPER_ADMIN: frozenset(Permission),  # all 11 permissions
    Role.ORG_ADMIN: frozenset(
        {
            Permission.READ_CONVERSATION,
            Permission.READ_KNOWLEDGE,
            Permission.READ_AUDIT,
            Permission.WRITE_CONVERSATION,
            Permission.WRITE_KNOWLEDGE,
            Permission.MANAGE_MEMBERS,
            Permission.MANAGE_SETTINGS,
            Permission.MANAGE_ROLES,
            Permission.ADMIN_ACCESS,
            Permission.ADMIN_BILLING,
        }
    ),
    Role.MANAGER: frozenset(
        {
            Permission.READ_CONVERSATION,
            Permission.READ_KNOWLEDGE,
            Permission.READ_AUDIT,
            Permission.WRITE_CONVERSATION,
            Permission.WRITE_KNOWLEDGE,
            Permission.MANAGE_MEMBERS,
        }
    ),
    Role.MEMBER: frozenset(
        {
            Permission.READ_CONVERSATION,
            Permission.READ_KNOWLEDGE,
            Permission.WRITE_CONVERSATION,
            Permission.WRITE_KNOWLEDGE,
        }
    ),
    Role.VIEWER: frozenset(
        {
            Permission.READ_CONVERSATION,
            Permission.READ_KNOWLEDGE,
        }
    ),
}


@dataclass(frozen=True)
class PermissionCheckResult:
    """Result of a permission check."""

    allowed: bool
    user_id: UUID
    required: Permission
    role: Role
    has_permissions: frozenset[Permission]


def get_role_permissions(role: Role) -> frozenset[Permission]:
    """Return the permission set for a given role."""
    return ROLE_PERMISSION_MATRIX.get(role, frozenset())


def check_permission(
    *,
    user_id: UUID,
    role: Role,
    required: Permission,
    extra_permissions: frozenset[Permission] | None = None,
) -> PermissionCheckResult:
    """Check whether a user with a given role has a required permission.

    Args:
        user_id: The user performing the action.
        role: The user's assigned role.
        required: The permission needed for the action.
        extra_permissions: Additional permissions granted to the user
                          beyond their role (e.g. per-user overrides).

    Returns:
        PermissionCheckResult indicating allowed/denied.
    """
    role_perms = get_role_permissions(role)
    all_perms = role_perms | (extra_permissions or frozenset())

    return PermissionCheckResult(
        allowed=required in all_perms,
        user_id=user_id,
        required=required,
        role=role,
        has_permissions=all_perms,
    )


def resolve_role(role_str: str) -> Role | None:
    """Parse a role string into a Role enum, returning None if invalid."""
    try:
        return Role(role_str)
    except ValueError:
        return None
