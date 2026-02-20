"""SQLAlchemy ORM models for DIYU Agent.

Maps to migration DDL in migrations/versions/:
  001_create_organization_tables.py  -> Organization, User, OrgMember, OrgSettings
  002_create_audit_events_table.py   -> AuditEvent
  003_create_conversation_events.py  -> ConversationEvent
  004_create_memory_items.py         -> MemoryItemModel, MemoryReceiptModel

These models live in the Infrastructure layer and implement
persistence for Port interfaces. Brain/Knowledge/Skill layers
MUST NOT import this module directly.

See: docs/architecture/00-*.md Section 6 (Infrastructure)
"""

from __future__ import annotations

import uuid as _uuid  # noqa: TC003 -- SQLAlchemy resolves Mapped[] annotations at runtime
from datetime import datetime  # noqa: TC003
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")
_GEN_UUID = sa.text("gen_random_uuid()")


class Base(DeclarativeBase):
    """Declarative base for all DIYU ORM models."""


class Organization(Base):
    """Multi-tenant organization (5-tier hierarchy).

    See: 001_create_organization_tables migration
    """

    __tablename__ = "organizations"

    id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(128), nullable=False, unique=True)
    tier: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        server_default="brand_hq",
    )
    org_path: Mapped[str] = mapped_column(
        sa.String(1024),
        nullable=False,
        comment="ltree-style hierarchy path",
    )
    parent_id: Mapped[_uuid.UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )

    # Relationships
    parent: Mapped[Organization | None] = relationship(
        "Organization",
        remote_side="Organization.id",
        lazy="select",
    )
    members: Mapped[list[OrgMember]] = relationship(
        "OrgMember",
        back_populates="organization",
        lazy="select",
    )
    settings: Mapped[OrgSettings | None] = relationship(
        "OrgSettings",
        back_populates="organization",
        uselist=False,
        lazy="select",
    )

    __table_args__ = (
        sa.Index("ix_organizations_slug", "slug", unique=True),
        sa.Index("ix_organizations_parent_id", "parent_id"),
        sa.Index("ix_organizations_tier", "tier"),
    )


class User(Base):
    """Platform user (cross-org identity).

    See: 001_create_organization_tables migration
    """

    __tablename__ = "users"

    id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    email: Mapped[str] = mapped_column(sa.String(320), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )

    memberships: Mapped[list[OrgMember]] = relationship(
        "OrgMember",
        back_populates="user",
        lazy="select",
    )

    __table_args__ = (sa.Index("ix_users_email", "email", unique=True),)


class OrgMember(Base):
    """Organization membership (user <-> org join with role).

    See: 001_create_organization_tables migration
    """

    __tablename__ = "org_members"

    id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        server_default="member",
    )
    permissions: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="members",
        lazy="select",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="memberships",
        lazy="select",
    )

    __table_args__ = (
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_members_org_user"),
        sa.Index("ix_org_members_org_id", "org_id"),
        sa.Index("ix_org_members_user_id", "user_id"),
    )


class OrgSettings(Base):
    """Organization-level settings with tier inheritance.

    See: 001_create_organization_tables migration
    """

    __tablename__ = "org_settings"

    id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    model_access: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    inherit_parent: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )

    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="settings",
        lazy="select",
    )

    __table_args__ = (sa.Index("ix_org_settings_org_id", "org_id", unique=True),)


class AuditEvent(Base):
    """Append-only audit event record.

    Immutable by design: no updated_at column, no update/delete operations.
    RLS enforced via org_id + current_setting('app.current_org_id').

    See: 002_create_audit_events_table migration
    """

    __tablename__ = "audit_events"

    id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[_uuid.UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        sa.String(128),
        nullable=False,
        comment="e.g. user.login, org.update, data.export",
    )
    resource_type: Mapped[str | None] = mapped_column(
        sa.String(128),
        nullable=True,
        comment="e.g. organization, user, conversation",
    )
    resource_id: Mapped[_uuid.UUID | None] = mapped_column(_UUID, nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    ip_address: Mapped[str | None] = mapped_column(sa.String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )

    __table_args__ = (
        sa.Index("ix_audit_events_org_id", "org_id"),
        sa.Index("ix_audit_events_user_id", "user_id"),
        sa.Index("ix_audit_events_action", "action"),
        sa.Index("ix_audit_events_created_at", "created_at"),
        sa.Index(
            "ix_audit_events_org_action_time",
            "org_id",
            "action",
            "created_at",
        ),
    )


class ConversationEvent(Base):
    """Conversation event (message/turn record).

    See: 003_create_conversation_events migration
    """

    __tablename__ = "conversation_events"

    id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[_uuid.UUID] = mapped_column(_UUID, nullable=False)
    user_id: Mapped[_uuid.UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    role: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        server_default="user",
    )
    content: Mapped[dict[str, Any]] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    content_schema_version: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        server_default="v3.6",
    )
    sequence_number: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    parent_event_id: Mapped[_uuid.UUID | None] = mapped_column(_UUID, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )

    __table_args__ = (
        sa.Index("ix_conversation_events_org_id", "org_id"),
        sa.Index("ix_conversation_events_session_id", "session_id"),
        sa.Index("ix_conversation_events_user_id", "user_id"),
        sa.UniqueConstraint(
            "session_id",
            "sequence_number",
            name="ix_conversation_events_session_seq",
        ),
        sa.Index("ix_conversation_events_created_at", "created_at"),
    )


class MemoryItemModel(Base):
    """Persistent memory item with optional pgvector embedding.

    See: 004_create_memory_items migration
    """

    __tablename__ = "memory_items"

    id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    memory_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    confidence: Mapped[float] = mapped_column(
        sa.Float(),
        nullable=False,
        server_default=sa.text("1.0"),
    )
    epistemic_type: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        server_default="fact",
    )
    version: Mapped[int] = mapped_column(
        sa.Integer(),
        nullable=False,
        server_default=sa.text("1"),
    )
    superseded_by: Mapped[_uuid.UUID | None] = mapped_column(_UUID, nullable=True)
    source_sessions: Mapped[list[_uuid.UUID]] = mapped_column(
        postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
        nullable=False,
        server_default=sa.text("'{}'::uuid[]"),
    )
    provenance: Mapped[dict[str, Any] | None] = mapped_column(
        postgresql.JSONB,
        nullable=True,
    )
    # Note: embedding column is vector(1536), managed via raw SQL in migration 004.
    # Access via raw SQL or pgvector-sqlalchemy extension.
    valid_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )
    invalid_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    last_validated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )

    receipts: Mapped[list[MemoryReceiptModel]] = relationship(
        "MemoryReceiptModel",
        back_populates="memory_item",
        lazy="select",
    )

    __table_args__ = (
        sa.Index("ix_memory_items_org_id", "org_id"),
        sa.Index("ix_memory_items_user_id", "user_id"),
        sa.Index("ix_memory_items_org_user", "org_id", "user_id"),
        sa.Index("ix_memory_items_memory_type", "memory_type"),
        sa.Index("ix_memory_items_valid_at", "valid_at"),
        sa.Index("ix_memory_items_superseded_by", "superseded_by"),
    )


class MemoryReceiptModel(Base):
    """Receipt for memory injection/retrieval (confidence calibration).

    See: 004_create_memory_items migration
    """

    __tablename__ = "memory_receipts"

    id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    memory_item_id: Mapped[_uuid.UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("memory_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    receipt_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    candidate_score: Mapped[float | None] = mapped_column(sa.Float(), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(sa.String(256), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    guardrail_hit: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )
    context_position: Mapped[int | None] = mapped_column(sa.Integer(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )

    memory_item: Mapped[MemoryItemModel] = relationship(
        "MemoryItemModel",
        back_populates="receipts",
        lazy="select",
    )

    __table_args__ = (
        sa.Index("ix_memory_receipts_org_id", "org_id"),
        sa.Index("ix_memory_receipts_memory_item_id", "memory_item_id"),
    )


__all__ = [
    "AuditEvent",
    "Base",
    "ConversationEvent",
    "MemoryItemModel",
    "MemoryReceiptModel",
    "OrgMember",
    "OrgSettings",
    "Organization",
    "User",
]
