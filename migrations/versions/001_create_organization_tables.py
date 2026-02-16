"""Create organization, users, and org_members tables.

Phase 1 (Security & Tenant Foundation): G1-2, I1-1, I1-2

Revision ID: 001_organization
Revises: None
Create Date: 2026-02-14

Rollback: reverse-drop org_settings, org_members, users, organizations
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001_organization"
down_revision = None
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")
_GEN_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", _UUID, primary_key=True, server_default=_GEN_UUID),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column(
            "tier",
            sa.String(64),
            nullable=False,
            server_default="brand_hq",
        ),
        sa.Column(
            "org_path",
            sa.String(1024),
            nullable=False,
            comment="ltree-style hierarchy path",
        ),
        sa.Column(
            "parent_id",
            _UUID,
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
    )
    op.create_index(
        "ix_organizations_slug",
        "organizations",
        ["slug"],
        unique=True,
    )
    op.create_index(
        "ix_organizations_parent_id",
        "organizations",
        ["parent_id"],
    )
    op.create_index("ix_organizations_tier", "organizations", ["tier"])

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", _UUID, primary_key=True, server_default=_GEN_UUID),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- org_members ---
    op.create_table(
        "org_members",
        sa.Column("id", _UUID, primary_key=True, server_default=_GEN_UUID),
        sa.Column(
            "org_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            _UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(64),
            nullable=False,
            server_default="member",
        ),
        sa.Column(
            "permissions",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.UniqueConstraint(
            "org_id",
            "user_id",
            name="uq_org_members_org_user",
        ),
    )
    op.create_index("ix_org_members_org_id", "org_members", ["org_id"])
    op.create_index("ix_org_members_user_id", "org_members", ["user_id"])

    # --- org_settings ---
    op.create_table(
        "org_settings",
        sa.Column("id", _UUID, primary_key=True, server_default=_GEN_UUID),
        sa.Column(
            "org_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "settings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "model_access",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "inherit_parent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
    )
    op.create_index(
        "ix_org_settings_org_id",
        "org_settings",
        ["org_id"],
        unique=True,
    )

    # --- RLS policies ---
    _enable_rls("organizations")
    _enable_rls("org_members")
    _enable_rls("org_settings")

    op.execute("""
        CREATE POLICY org_members_isolation ON org_members
        USING (org_id = current_setting('app.current_org_id')::uuid)
    """)

    op.execute("""
        CREATE POLICY org_settings_isolation ON org_settings
        USING (org_id = current_setting('app.current_org_id')::uuid)
    """)

    op.execute("""
        CREATE POLICY organizations_isolation ON organizations
        USING (
            id = current_setting('app.current_org_id')::uuid
            OR id IN (
                SELECT parent_id FROM organizations
                WHERE id = current_setting('app.current_org_id')::uuid
            )
        )
    """)


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS organizations_isolation ON organizations",
    )
    op.execute(
        "DROP POLICY IF EXISTS org_settings_isolation ON org_settings",
    )
    op.execute(
        "DROP POLICY IF EXISTS org_members_isolation ON org_members",
    )
    op.drop_table("org_settings")
    op.drop_table("org_members")
    op.drop_table("users")
    op.drop_table("organizations")


_RLS_TABLES = frozenset({"organizations", "users", "org_members", "org_settings"})


def _enable_rls(table: str) -> None:
    if table not in _RLS_TABLES:
        msg = f"Unexpected table for RLS: {table}"
        raise ValueError(msg)
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
