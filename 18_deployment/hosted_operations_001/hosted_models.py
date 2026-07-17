#!/usr/bin/env python3
"""Package 8 operational metadata stored beside the Package 7 runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


JsonObject = dict[str, Any]


class HostedBase(DeclarativeBase):
    """Metadata root for deployment state, revisions, and audit receipts."""


class HostedSchemaState(HostedBase):
    __tablename__ = "hosted_schema_state"

    namespace: Mapped[str] = mapped_column(String(128), primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    application_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class HostedBrandRevision(HostedBase):
    __tablename__ = "hosted_brand_revisions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "revision_number",
            name="uq_hosted_brand_revision",
        ),
    )

    revision_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class HostedOperationAudit(HostedBase):
    __tablename__ = "hosted_operation_audit"

    operation_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    command: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    object_ref: Mapped[str] = mapped_column(Text, nullable=False)
    object_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
