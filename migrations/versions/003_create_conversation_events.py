"""Create conversation_events table with content_schema_version.

Phase 2 (Core Conversation + Knowledge): I2-4

Revision ID: 003_conversation_events
Revises: 002_audit_events
Create Date: 2026-02-17

Rollback: alembic downgrade -1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003_conversation_events"
down_revision = "002_audit_events"
branch_labels = None
depends_on = None

# -- Migration metadata (治理规范 v1.1 Section 8) --
reversible_type = "full"  # DDL fully reversible via downgrade()
rollback_artifact = "alembic downgrade -1"
drill_evidence_id = "3b15a26bb5cc5e4b"  # upgrade->downgrade->upgrade 20260218T074302Z

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")
_GEN_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "conversation_events",
        sa.Column("id", _UUID, primary_key=True, server_default=_GEN_UUID),
        sa.Column(
            "org_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            _UUID,
            nullable=False,
            comment="Conversation session grouping key",
        ),
        sa.Column(
            "user_id",
            _UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_type",
            sa.String(64),
            nullable=False,
            comment="e.g. user_message, assistant_message, tool_call, system",
        ),
        sa.Column(
            "role",
            sa.String(32),
            nullable=False,
            server_default="user",
            comment="Message role: user, assistant, system, tool",
        ),
        sa.Column(
            "content",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Message content (text, tool_calls, etc.)",
        ),
        sa.Column(
            "content_schema_version",
            sa.String(16),
            nullable=False,
            server_default="v3.6",
            comment="Schema version for content field (M-Track MM0-5)",
        ),
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
            comment="Ordering within session (monotonically increasing)",
        ),
        sa.Column(
            "parent_event_id",
            _UUID,
            nullable=True,
            comment="For threaded replies / tool call responses",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Model info, token counts, latency, etc.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
    )

    # Indexes
    op.create_index(
        "ix_conversation_events_org_id",
        "conversation_events",
        ["org_id"],
    )
    op.create_index(
        "ix_conversation_events_session_id",
        "conversation_events",
        ["session_id"],
    )
    op.create_index(
        "ix_conversation_events_user_id",
        "conversation_events",
        ["user_id"],
    )
    # Unique ordering within a session
    op.create_index(
        "ix_conversation_events_session_seq",
        "conversation_events",
        ["session_id", "sequence_number"],
        unique=True,
    )
    op.create_index(
        "ix_conversation_events_created_at",
        "conversation_events",
        ["created_at"],
    )

    # RLS
    op.execute("ALTER TABLE conversation_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE conversation_events FORCE ROW LEVEL SECURITY")
    # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query
    op.execute("""
        CREATE POLICY conversation_events_isolation ON conversation_events
        USING (org_id = current_setting('app.current_org_id')::uuid)
    """)


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS conversation_events_isolation ON conversation_events",
    )
    op.drop_table("conversation_events")
