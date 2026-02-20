"""Add password_hash column to users table.

E2E chain fix: enable login endpoint with password authentication.

Revision ID: 005_user_password_hash
Revises: 004_memory_items
Create Date: 2026-02-20

Rollback: alembic downgrade -1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005_user_password_hash"
down_revision = "004_memory_items"
branch_labels = None
depends_on = None

reversible_type = "full"  # DDL fully reversible via downgrade()
rollback_artifact = "alembic downgrade -1"
drill_evidence_id = "pending"  # to be filled after upgrade->downgrade->upgrade drill


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")
