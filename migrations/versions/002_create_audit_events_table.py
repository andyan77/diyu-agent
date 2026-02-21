"""Create audit_events table.

Phase 1 (Security & Tenant Foundation): I1-5, OS1-3

Revision ID: 002_audit_events
Revises: 001_organization
Create Date: 2026-02-14

Rollback: drop audit_events table and its RLS policies.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_audit_events"
down_revision = "001_organization"
branch_labels = None
depends_on = None

# -- Migration metadata (治理规范 v1.1 Section 8) --
reversible_type = "full"  # DDL fully reversible via downgrade()
rollback_artifact = "alembic downgrade -1"
drill_evidence_id = None  # populated after upgrade->downgrade->upgrade drill

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")
_GEN_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "audit_events",
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
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "action",
            sa.String(128),
            nullable=False,
            comment="e.g. user.login, org.update, data.export",
        ),
        sa.Column(
            "resource_type",
            sa.String(128),
            nullable=True,
            comment="e.g. organization, user, conversation",
        ),
        sa.Column("resource_id", _UUID, nullable=True),
        sa.Column(
            "detail",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
    )

    # Indexes for efficient querying
    op.create_index(
        "ix_audit_events_org_id",
        "audit_events",
        ["org_id"],
    )
    op.create_index(
        "ix_audit_events_user_id",
        "audit_events",
        ["user_id"],
    )
    op.create_index(
        "ix_audit_events_action",
        "audit_events",
        ["action"],
    )
    op.create_index(
        "ix_audit_events_created_at",
        "audit_events",
        ["created_at"],
    )
    # Composite index for org-scoped audit queries
    op.create_index(
        "ix_audit_events_org_action_time",
        "audit_events",
        ["org_id", "action", "created_at"],
    )

    # RLS
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY audit_events_isolation ON audit_events
        USING (org_id = current_setting('app.current_org_id')::uuid)
    """)


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS audit_events_isolation ON audit_events",
    )
    op.drop_table("audit_events")
