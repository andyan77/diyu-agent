"""Create tool_usage_records table for Tool independent billing.

Milestone: I3-4
ADR: ADR-047 (Tool independent billing)

Supports multi-modal Tool billing (per_call / per_image / per_minute)
separate from LLM token billing (llm_usage_records).

Revision ID: 006_tool_usage_records
Revises: 005_user_password_hash
Create Date: 2026-02-20

Rollback: alembic downgrade -1

See: docs/architecture/06-基础设施层 Section 9 (DDL)
     docs/architecture/04-Tool Section 5 (Tool billing)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006_tool_usage_records"
down_revision = "005_user_password_hash"
branch_labels = None
depends_on = None

reversible_type = "full"  # DDL fully reversible via downgrade()
rollback_artifact = "alembic downgrade -1"
drill_evidence_id = "pending"  # to be filled after upgrade->downgrade->upgrade drill


def upgrade() -> None:
    op.create_table(
        "tool_usage_records",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "org_id",
            sa.Uuid,
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid, nullable=False),
        sa.Column("brand_id", sa.Uuid, nullable=True),
        sa.Column("tool_name", sa.Text, nullable=False),
        sa.Column("tool_version", sa.Text, nullable=False),
        sa.Column("skill_id", sa.Text, nullable=True),
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "cost_amount", sa.Numeric(precision=12, scale=6), nullable=False
        ),
        sa.Column("billing_unit", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Text,
            sa.CheckConstraint(
                "status IN ('success', 'error', 'rate_limited')",
                name="ck_tool_usage_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # RLS: org_id isolation (matching existing pattern)
    op.execute(
        "ALTER TABLE tool_usage_records ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "CREATE POLICY org_isolation ON tool_usage_records "
        "USING (org_id = current_setting('app.current_org_id')::uuid)"
    )

    # Performance indexes
    op.create_index(
        "ix_tool_usage_org_created",
        "tool_usage_records",
        ["org_id", "created_at"],
    )
    op.create_index(
        "ix_tool_usage_user_created",
        "tool_usage_records",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_tool_usage_user_created", table_name="tool_usage_records")
    op.drop_index("ix_tool_usage_org_created", table_name="tool_usage_records")
    op.execute("DROP POLICY IF EXISTS org_isolation ON tool_usage_records")
    op.execute(
        "ALTER TABLE tool_usage_records DISABLE ROW LEVEL SECURITY"
    )
    op.drop_table("tool_usage_records")
