#!/usr/bin/env python3
"""SQLAlchemy models for the Package 7 isolated, non-production runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


JsonObject = dict[str, Any]


class Base(DeclarativeBase):
    """Package-owned metadata root."""


class RuntimeTenant(Base):
    __tablename__ = "runtime_tenants"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeBrand(Base):
    __tablename__ = "runtime_brands"

    brand_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeOrganization(Base):
    __tablename__ = "runtime_organizations"

    organization_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeStore(Base):
    __tablename__ = "runtime_stores"

    store_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimePrincipal(Base):
    __tablename__ = "runtime_principals"

    principal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    allowed_account_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeBrowserSession(Base):
    __tablename__ = "runtime_browser_sessions"

    browser_session_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeAccount(Base):
    __tablename__ = "runtime_content_accounts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "display_name",
            name="uq_runtime_account_tenant_display_name",
        ),
    )

    account_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand_id: Mapped[str] = mapped_column(String(128), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    store_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    maker_role_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeAuthorization(Base):
    __tablename__ = "runtime_authorizations"

    authorization_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeSubjectConfirmation(Base):
    __tablename__ = "runtime_subject_confirmations"

    confirmation_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeNarrativeFragment(Base):
    __tablename__ = "runtime_narrative_fragments"

    fragment_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    authorization_state: Mapped[str] = mapped_column(String(32), nullable=False)
    authorization_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocation_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    dify_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    index_content_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeSource(Base):
    __tablename__ = "runtime_sources"

    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimePreciseFact(Base):
    __tablename__ = "runtime_precise_facts"

    fact_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fact_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    authorization_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocation_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeSetting(Base):
    __tablename__ = "runtime_settings"

    setting_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    setting_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    source_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeRequirement(Base):
    __tablename__ = "runtime_requirements"
    __table_args__ = (UniqueConstraint("requirement_id", "requirement_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[str] = mapped_column(String(160), nullable=False)
    requirement_version: Mapped[int] = mapped_column(Integer, nullable=False)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    browser_session_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimePlan(Base):
    __tablename__ = "runtime_plans"

    plan_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    plan_ref: Mapped[str] = mapped_column(String(240), nullable=False, unique=True)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    source_request: Mapped[JsonObject] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeCandidate(Base):
    __tablename__ = "runtime_candidates"
    __table_args__ = (UniqueConstraint("run_id", "ordinal"),)

    candidate_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    plan_ref: Mapped[str | None] = mapped_column(String(240), nullable=True, index=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    browser_session_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    candidate_payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    used_fact_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    used_material_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeValidation(Base):
    __tablename__ = "runtime_validations"

    validation_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeFeedback(Base):
    __tablename__ = "runtime_feedback"

    feedback_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(160), nullable=False)
    browser_session_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    candidate_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    requirement_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    role_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    storyline_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    column_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    previous_content_ref: Mapped[str | None] = mapped_column(String(240), nullable=True)
    fact_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    material_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    review_state: Mapped[str] = mapped_column(String(64), nullable=False, default="RECORDED")
    short_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeModelRun(Base):
    __tablename__ = "runtime_model_runs"

    run_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(160), nullable=False)
    browser_session_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_ref: Mapped[str | None] = mapped_column(String(240), nullable=True)
    prompt_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    model_output_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_output_preserved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeDifyInvocation(Base):
    __tablename__ = "runtime_dify_invocations"

    invocation_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    model_call_upper_bound: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_price: Mapped[str] = mapped_column(String(64), nullable=False, default="0")
    currency: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    response_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuntimeDifyConversation(Base):
    __tablename__ = "runtime_dify_conversations"
    __table_args__ = (
        UniqueConstraint(
            "principal_id",
            "account_id",
            "browser_session_id",
            name="uq_runtime_dify_conversation_scope",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    browser_session_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    dify_user_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    conversation_id: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
