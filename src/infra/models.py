"""SQLAlchemy ORM models for DIYU Agent.

Maps to migration DDL in migrations/versions/:
  001_create_organization_tables.py  -> Organization, User, OrgMember, OrgSettings
  002_create_audit_events_table.py   -> AuditEvent

These models live in the Infrastructure layer and implement
persistence for Port interfaces. Brain/Knowledge/Skill layers
MUST NOT import this module directly.

See: docs/architecture/00-*.md Section 6 (Infrastructure)
"""

from __future__ import annotations

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

    id: Mapped[sa.Uuid] = mapped_column(
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
    parent_id: Mapped[sa.Uuid | None] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
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

    id: Mapped[sa.Uuid] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    email: Mapped[str] = mapped_column(sa.String(320), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
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

    id: Mapped[sa.Uuid] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[sa.Uuid] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[sa.Uuid] = mapped_column(
        _UUID,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        server_default="member",
    )
    permissions: Mapped[dict] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=_NOW,
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
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

    id: Mapped[sa.Uuid] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[sa.Uuid] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    settings: Mapped[dict] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    model_access: Mapped[dict] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    inherit_parent: Mapped[bool] = mapped_column(
        sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
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

    id: Mapped[sa.Uuid] = mapped_column(
        _UUID,
        primary_key=True,
        server_default=_GEN_UUID,
    )
    org_id: Mapped[sa.Uuid] = mapped_column(
        _UUID,
        sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[sa.Uuid | None] = mapped_column(
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
    resource_id: Mapped[sa.Uuid | None] = mapped_column(_UUID, nullable=True)
    detail: Mapped[dict] = mapped_column(
        postgresql.JSONB,
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    ip_address: Mapped[str | None] = mapped_column(sa.String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
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


__all__ = [
    "AuditEvent",
    "Base",
    "OrgMember",
    "OrgSettings",
    "Organization",
    "User",
]
