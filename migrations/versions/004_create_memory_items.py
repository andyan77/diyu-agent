"""Create memory_items and memory_receipts tables with pgvector.

Phase 2 (Core Conversation + Knowledge): I2-5

Revision ID: 004_memory_items
Revises: 003_conversation_events
Create Date: 2026-02-17

Rollback: alembic downgrade -1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "004_memory_items"
down_revision = "003_conversation_events"
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
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- memory_items ---
    op.create_table(
        "memory_items",
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
            "memory_type",
            sa.String(64),
            nullable=False,
            comment="observation | preference | pattern | summary | agent_experience",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "epistemic_type",
            sa.String(32),
            nullable=False,
            server_default="fact",
            comment="fact | opinion | preference | outdated (v3.5.2)",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "superseded_by",
            _UUID,
            nullable=True,
            comment="Points to newer version of this memory",
        ),
        sa.Column(
            "source_sessions",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "provenance",
            postgresql.JSONB,
            nullable=True,
            comment="Provenance metadata for traceability",
        ),
        # Note: embedding (vector) column added via raw SQL below
        sa.Column(
            "valid_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
        sa.Column(
            "invalid_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_validated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time this memory was validated/confirmed",
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

    # Add pgvector embedding column (not supported by sa.Column directly)
    op.execute("ALTER TABLE memory_items ADD COLUMN embedding vector(1536)")

    # Indexes
    op.create_index(
        "ix_memory_items_org_id",
        "memory_items",
        ["org_id"],
    )
    op.create_index(
        "ix_memory_items_user_id",
        "memory_items",
        ["user_id"],
    )
    op.create_index(
        "ix_memory_items_org_user",
        "memory_items",
        ["org_id", "user_id"],
    )
    op.create_index(
        "ix_memory_items_memory_type",
        "memory_items",
        ["memory_type"],
    )
    op.create_index(
        "ix_memory_items_valid_at",
        "memory_items",
        ["valid_at"],
    )
    op.create_index(
        "ix_memory_items_superseded_by",
        "memory_items",
        ["superseded_by"],
    )

    # HNSW index for vector similarity search
    op.execute("""
        CREATE INDEX ix_memory_items_embedding_hnsw
        ON memory_items
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # RLS
    op.execute("ALTER TABLE memory_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_items FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY memory_items_isolation ON memory_items
        USING (org_id = current_setting('app.current_org_id')::uuid)
    """)

    # --- memory_receipts ---
    op.create_table(
        "memory_receipts",
        sa.Column("id", _UUID, primary_key=True, server_default=_GEN_UUID),
        sa.Column(
            "org_id",
            _UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "memory_item_id",
            _UUID,
            sa.ForeignKey("memory_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "receipt_type",
            sa.String(32),
            nullable=False,
            comment="injection | retrieval",
        ),
        sa.Column(
            "candidate_score",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "decision_reason",
            sa.String(256),
            nullable=True,
        ),
        sa.Column(
            "policy_version",
            sa.String(16),
            nullable=True,
        ),
        sa.Column(
            "guardrail_hit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "context_position",
            sa.Integer(),
            nullable=True,
            comment="Position in the prompt context window",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=_NOW,
        ),
    )

    op.create_index(
        "ix_memory_receipts_org_id",
        "memory_receipts",
        ["org_id"],
    )
    op.create_index(
        "ix_memory_receipts_memory_item_id",
        "memory_receipts",
        ["memory_item_id"],
    )

    # RLS
    op.execute("ALTER TABLE memory_receipts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_receipts FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY memory_receipts_isolation ON memory_receipts
        USING (org_id = current_setting('app.current_org_id')::uuid)
    """)


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS memory_receipts_isolation ON memory_receipts",
    )
    op.drop_table("memory_receipts")

    op.execute(
        "DROP POLICY IF EXISTS memory_items_isolation ON memory_items",
    )
    op.drop_table("memory_items")

    # Note: We do NOT drop the vector extension as other tables may use it
