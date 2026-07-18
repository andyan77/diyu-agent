#!/usr/bin/env python3
"""Package 7 persistence adapters and transactional repository."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import (
    Engine,
    MetaData,
    Table,
    UniqueConstraint,
    create_engine,
    event,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Connection
from sqlalchemy.schema import AddConstraint, DropConstraint
from sqlalchemy.orm import Session, sessionmaker


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_2_ROOT = (
    REPOSITORY_ROOT / "12_expression_service/expression_runtime_adapter_001"
)
if str(PACKAGE_2_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_2_ROOT))

from light_expression_service import PlanFactory, PlanRecord  # type: ignore[import-not-found]  # noqa: E402

from runtime_models import (  # noqa: E402
    Base,
    RuntimeAccount,
    RuntimeAuthorization,
    RuntimeBrowserSession,
    RuntimeCandidate,
    RuntimeDifyConversation,
    RuntimeDifyInvocation,
    RuntimeFeedback,
    RuntimeModelRun,
    RuntimeNarrativeFragment,
    RuntimePlan,
    RuntimePreciseFact,
    RuntimePrincipal,
    RuntimeRequirement,
    RuntimeSetting,
    RuntimeSubjectConfirmation,
    RuntimeValidation,
)


@dataclass(frozen=True)
class TrustedDatabaseScope:
    """Server-confirmed database scope; browser fields never construct this value."""

    tenant_id: str
    brand_id: str | None = None
    organization_id: str | None = None
    store_id: str | None = None
    account_id: str | None = None
    principal_id: str | None = None
    browser_session_id: str | None = None


_TRUSTED_DATABASE_SCOPE: ContextVar[TrustedDatabaseScope | None] = ContextVar(
    "diyu_trusted_database_scope",
    default=None,
)
_RUNTIME_BROWSER_SESSION_ID: ContextVar[str | None] = ContextVar(
    "diyu_runtime_browser_session_id",
    default=None,
)
LOCAL_TEST_BROWSER_SESSION_ID = "BRS-LOCAL-UNIT-TEST"
_DIFY_BUDGET_RESERVATION_LOCK = threading.Lock()


@contextmanager
def trusted_database_scope(scope: TrustedDatabaseScope) -> Iterator[None]:
    """Apply one trusted scope to every transaction opened in this context."""

    if not scope.tenant_id.strip():
        raise ValueError("A trusted tenant scope is required")
    token = _TRUSTED_DATABASE_SCOPE.set(scope)
    try:
        yield
    finally:
        _TRUSTED_DATABASE_SCOPE.reset(token)


@contextmanager
def runtime_browser_session(browser_session_id: str) -> Iterator[None]:
    """Bind direct runtime calls to one server-issued browser session."""

    normalized = browser_session_id.strip()
    if not normalized or len(normalized) > 160:
        raise ValueError("A valid browser session id is required")
    token = _RUNTIME_BROWSER_SESSION_ID.set(normalized)
    try:
        yield
    finally:
        _RUNTIME_BROWSER_SESSION_ID.reset(token)


def current_browser_session_id() -> str:
    scope = _TRUSTED_DATABASE_SCOPE.get()
    if scope is not None and scope.browser_session_id:
        return scope.browser_session_id
    browser_session_id = _RUNTIME_BROWSER_SESSION_ID.get()
    if browser_session_id is None:
        raise RuntimeError("A trusted browser session scope is required")
    return browser_session_id


def current_trusted_database_scope() -> TrustedDatabaseScope:
    scope = _TRUSTED_DATABASE_SCOPE.get()
    if scope is None:
        raise RuntimeError("A trusted database scope is required")
    return scope


class _ScopedRuntimeSession(Session):
    """Session class that installs transaction-local PostgreSQL RLS settings."""


@event.listens_for(_ScopedRuntimeSession, "after_begin")
def _install_trusted_scope(
    session: Session,
    transaction: Any,
    connection: Connection,
) -> None:
    del session, transaction
    if connection.dialect.name != "postgresql":
        return
    scope = _TRUSTED_DATABASE_SCOPE.get()
    values = {
        "app.tenant_id": None if scope is None else scope.tenant_id,
        "app.brand_id": None if scope is None else scope.brand_id,
        "app.organization_id": None if scope is None else scope.organization_id,
        "app.store_id": None if scope is None else scope.store_id,
        "app.account_id": None if scope is None else scope.account_id,
        "app.principal_id": None if scope is None else scope.principal_id,
        "app.browser_session_id": (None if scope is None else scope.browser_session_id),
    }
    for name, value in values.items():
        connection.execute(select(func.set_config(name, value or "", True)))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
    def serialize(item: object) -> str:
        if isinstance(item, datetime):
            normalized = (
                item if item.tzinfo is not None else item.replace(tzinfo=timezone.utc)
            )
            return normalized.astimezone(timezone.utc).isoformat()
        return str(item)

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=serialize,
    )


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def create_runtime_engine(database_url: str) -> Engine:
    """Build a reconnect-safe engine without embedding environment defaults."""

    if not database_url or "://" not in database_url:
        raise ValueError("A valid runtime database URL is required")
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        class_=_ScopedRuntimeSession,
        expire_on_commit=False,
        future=True,
    )


class SqlAlchemyPlanStore:
    """Persistent implementation of the Package 2 plan-store boundary."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    @staticmethod
    def _key_text(key: tuple[str, str, str, int]) -> str:
        return canonical_json(list(key))

    def materialize(
        self,
        key: tuple[str, str, str, int],
        input_digest: str,
        factory: PlanFactory,
    ) -> JsonObject:
        key_text = self._key_text(key)
        with self.sessions.begin() as session:
            row = session.scalar(
                select(RuntimePlan)
                .where(RuntimePlan.plan_key == key_text)
                .with_for_update()
            )
            if row is not None and row.input_digest == input_digest:
                return copy.deepcopy(row.plan_payload)
            revision = 1 if row is None else row.plan_revision + 1
            plan = copy.deepcopy(factory(revision))
            if row is None:
                row = RuntimePlan(
                    plan_key=key_text,
                    plan_ref=str(plan["composition_plan_ref"]),
                    input_digest=input_digest,
                    plan_revision=revision,
                    plan_payload=plan,
                    source_request={},
                    updated_at=utc_now(),
                )
                session.add(row)
            else:
                row.plan_ref = str(plan["composition_plan_ref"])
                row.input_digest = input_digest
                row.plan_revision = revision
                row.plan_payload = plan
                row.source_request = {}
                row.updated_at = utc_now()
            session.flush()
            return copy.deepcopy(plan)

    def attach_source(self, plan_ref: str, source_request: JsonObject) -> None:
        with self.sessions.begin() as session:
            row = session.scalar(
                select(RuntimePlan)
                .where(RuntimePlan.plan_ref == plan_ref)
                .with_for_update()
            )
            if row is None:
                raise KeyError(plan_ref)
            row.source_request = copy.deepcopy(source_request)
            row.updated_at = utc_now()

    def get(self, plan_ref: str) -> PlanRecord | None:
        with self.sessions() as session:
            row = session.scalar(
                select(RuntimePlan).where(RuntimePlan.plan_ref == plan_ref)
            )
            if row is None:
                return None
            key_value = json.loads(row.plan_key)
            if not isinstance(key_value, list) or len(key_value) != 4:
                raise ValueError("Stored plan key is invalid")
            key = (
                str(key_value[0]),
                str(key_value[1]),
                str(key_value[2]),
                int(key_value[3]),
            )
            return PlanRecord(
                key=key,
                input_digest=row.input_digest,
                plan=copy.deepcopy(row.plan_payload),
                source_request=copy.deepcopy(row.source_request),
            )


class RuntimeRepository:
    """Small transaction boundary for identity, evidence and user choices."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def initialize_schema(self, engine: Engine) -> None:
        Base.metadata.create_all(engine)
        if engine.dialect.name == "postgresql":
            self._migrate_account_display_scope(engine)
        self.migrate_browser_session_scope(engine)
        fragment_columns = {
            str(column["name"])
            for column in inspect(engine).get_columns("runtime_narrative_fragments")
        }
        if "index_content_digest" not in fragment_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE runtime_narrative_fragments "
                        "ADD COLUMN index_content_digest VARCHAR(64)"
                    )
                )

    @staticmethod
    def migrate_browser_session_scope(engine: Engine) -> None:
        """Add the browser-session boundary without rewriting historical rows."""

        inspector = inspect(engine)
        scoped_tables = {
            "runtime_requirements": ("browser_session_id",),
            "runtime_candidates": ("principal_id", "browser_session_id"),
            "runtime_feedback": ("browser_session_id",),
            "runtime_model_runs": ("browser_session_id",),
            "runtime_dify_conversations": ("browser_session_id",),
        }
        with engine.begin() as connection:
            for table_name, required_columns in scoped_tables.items():
                if table_name not in inspector.get_table_names():
                    continue
                existing = {
                    str(column["name"]) for column in inspector.get_columns(table_name)
                }
                for column_name in required_columns:
                    if column_name in existing:
                        continue
                    width = 128 if column_name == "principal_id" else 160
                    fallback = (
                        "PRINCIPAL-HISTORICAL"
                        if column_name == "principal_id"
                        else "BRS-HISTORICAL"
                    )
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} ADD COLUMN {column_name} "
                            f"VARCHAR({width}) NOT NULL DEFAULT '{fallback}'"
                        )
                    )
        if engine.dialect.name != "postgresql":
            return
        metadata = MetaData()
        conversations = Table(
            RuntimeDifyConversation.__tablename__,
            metadata,
            autoload_with=engine,
        )
        constraints = [
            constraint
            for constraint in conversations.constraints
            if isinstance(constraint, UniqueConstraint)
        ]
        old_constraints = [
            constraint
            for constraint in constraints
            if [column.name for column in constraint.columns]
            == ["principal_id", "account_id"]
        ]
        replacement_exists = any(
            [column.name for column in constraint.columns]
            == ["principal_id", "account_id", "browser_session_id"]
            for constraint in constraints
        )
        if not old_constraints and replacement_exists:
            return
        with engine.begin() as connection:
            for constraint in old_constraints:
                connection.execute(DropConstraint(constraint))  # type: ignore[no-untyped-call]
            if not replacement_exists:
                replacement = UniqueConstraint(
                    conversations.c.principal_id,
                    conversations.c.account_id,
                    conversations.c.browser_session_id,
                    name="uq_runtime_dify_conversation_scope",
                )
                conversations.append_constraint(replacement)
                connection.execute(AddConstraint(replacement))  # type: ignore[no-untyped-call]

    @staticmethod
    def _migrate_account_display_scope(engine: Engine) -> None:
        """Replace the Package 7 global account label key with a tenant key."""

        metadata = MetaData()
        accounts = Table(RuntimeAccount.__tablename__, metadata, autoload_with=engine)
        unique_constraints = [
            constraint
            for constraint in accounts.constraints
            if isinstance(constraint, UniqueConstraint)
        ]
        global_label_constraints = [
            constraint
            for constraint in unique_constraints
            if [column.name for column in constraint.columns] == ["display_name"]
        ]
        composite_exists = any(
            [column.name for column in constraint.columns]
            == ["tenant_id", "display_name"]
            for constraint in unique_constraints
        )
        if not global_label_constraints and composite_exists:
            return
        with engine.begin() as connection:
            for constraint in global_label_constraints:
                connection.execute(DropConstraint(constraint))  # type: ignore[no-untyped-call]
            if not composite_exists:
                replacement = UniqueConstraint(
                    accounts.c.tenant_id,
                    accounts.c.display_name,
                    name="uq_runtime_account_tenant_display_name",
                )
                accounts.append_constraint(replacement)
                connection.execute(AddConstraint(replacement))  # type: ignore[no-untyped-call]

    def principal_by_username(self, username: str) -> RuntimePrincipal | None:
        with self.sessions() as session:
            return session.scalar(
                select(RuntimePrincipal).where(RuntimePrincipal.username == username)
            )

    def principal_by_id(self, principal_id: str) -> RuntimePrincipal | None:
        with self.sessions() as session:
            return session.get(RuntimePrincipal, principal_id)

    def start_browser_session(
        self,
        *,
        browser_session_id: str,
        principal_id: str,
        expires_at: datetime,
    ) -> None:
        with self.sessions.begin() as session:
            principal = session.get(RuntimePrincipal, principal_id)
            if principal is None or principal.status != "ACTIVE":
                raise ValueError("Browser session principal is unavailable")
            if session.get(RuntimeBrowserSession, browser_session_id) is not None:
                raise ValueError("Browser session identity already exists")
            now = utc_now()
            session.add(
                RuntimeBrowserSession(
                    browser_session_id=browser_session_id,
                    principal_id=principal_id,
                    state="ACTIVE",
                    expires_at=expires_at,
                    created_at=now,
                    updated_at=now,
                )
            )

    def require_browser_session(
        self,
        *,
        browser_session_id: str,
        principal_id: str,
    ) -> None:
        with self.sessions() as session:
            row = session.get(RuntimeBrowserSession, browser_session_id)
            principal = session.get(RuntimePrincipal, principal_id)
            expires_at = None if row is None else row.expires_at
            if (
                row is None
                or principal is None
                or principal.status != "ACTIVE"
                or row.principal_id != principal_id
                or row.state != "ACTIVE"
                or expires_at is None
                or (
                    expires_at
                    if expires_at.tzinfo is not None
                    else expires_at.replace(tzinfo=timezone.utc)
                )
                < utc_now()
            ):
                raise ValueError("Browser session is inactive or expired")

    def revoke_browser_session(
        self,
        *,
        browser_session_id: str,
        principal_id: str,
    ) -> None:
        with self.sessions.begin() as session:
            row = session.get(
                RuntimeBrowserSession,
                browser_session_id,
                with_for_update=True,
            )
            if row is None or row.principal_id != principal_id:
                raise ValueError("Browser session is outside the principal scope")
            row.state = "REVOKED"
            row.updated_at = utc_now()

    def active_browser_sessions(
        self,
        principal_id: str,
    ) -> tuple[JsonObject, ...]:
        """Return a non-secret lifecycle projection for isolation audits."""

        now = utc_now()
        with self.sessions() as session:
            rows = list(
                session.scalars(
                    select(RuntimeBrowserSession)
                    .where(
                        RuntimeBrowserSession.principal_id == principal_id,
                        RuntimeBrowserSession.state == "ACTIVE",
                    )
                    .order_by(RuntimeBrowserSession.created_at)
                ).all()
            )
        return tuple(
            {
                "browser_session_id": row.browser_session_id,
                "principal_id": row.principal_id,
                "state": row.state,
                "expires_at": row.expires_at.isoformat(),
            }
            for row in rows
            if self._aware(row.expires_at) >= now
        )

    def account_by_display_name(self, display_name: str) -> RuntimeAccount | None:
        with self.sessions() as session:
            rows = list(
                session.scalars(
                    select(RuntimeAccount).where(
                        RuntimeAccount.display_name == display_name
                    )
                ).all()
            )
            return rows[0] if len(rows) == 1 else None

    def account_by_id(self, account_id: str) -> RuntimeAccount | None:
        with self.sessions() as session:
            return session.get(RuntimeAccount, account_id)

    def require_active_scope(
        self,
        principal_id: str,
        account_id: str,
    ) -> tuple[RuntimePrincipal, RuntimeAccount]:
        """Revalidate server-owned identity and account scope in one transaction."""

        with self.sessions() as session:
            principal = session.get(RuntimePrincipal, principal_id)
            account = session.get(RuntimeAccount, account_id)
            if (
                principal is None
                or principal.status != "ACTIVE"
                or account is None
                or account.status != "ACTIVE"
                or principal.tenant_id != account.tenant_id
                or account_id not in principal.allowed_account_ids
            ):
                raise ValueError("Current principal and account scope is not active")
            return principal, account

    def require_active_scope_by_display_name(
        self,
        principal_id: str,
        display_name: str,
    ) -> tuple[RuntimePrincipal, RuntimeAccount]:
        """Resolve an account label and revalidate it against current authority."""

        with self.sessions() as session:
            principal = session.get(RuntimePrincipal, principal_id)
            if principal is None or principal.status != "ACTIVE":
                raise ValueError("Current principal and account scope is not active")
            accounts = list(
                session.scalars(
                    select(RuntimeAccount).where(
                        RuntimeAccount.display_name == display_name,
                        RuntimeAccount.tenant_id == principal.tenant_id,
                        RuntimeAccount.account_id.in_(principal.allowed_account_ids),
                    )
                ).all()
            )
            account = accounts[0] if len(accounts) == 1 else None
            if (
                account is None
                or account.status != "ACTIVE"
                or principal.tenant_id != account.tenant_id
                or account.account_id not in principal.allowed_account_ids
            ):
                raise ValueError("Current principal and account scope is not active")
            return principal, account

    def all_accounts(self) -> tuple[RuntimeAccount, ...]:
        with self.sessions() as session:
            return tuple(
                session.scalars(
                    select(RuntimeAccount).order_by(RuntimeAccount.account_id)
                ).all()
            )

    def identity_payloads(self, tenant_id: str | None = None) -> JsonObject:
        with self.sessions() as session:
            principal_statement = select(RuntimePrincipal)
            account_statement = select(RuntimeAccount)
            authorization_statement = select(RuntimeAuthorization)
            confirmation_statement = select(RuntimeSubjectConfirmation)
            if tenant_id is not None:
                principal_statement = principal_statement.where(
                    RuntimePrincipal.tenant_id == tenant_id
                )
                account_statement = account_statement.where(
                    RuntimeAccount.tenant_id == tenant_id
                )
                authorization_statement = authorization_statement.where(
                    RuntimeAuthorization.tenant_id == tenant_id
                )
                confirmation_statement = confirmation_statement.where(
                    RuntimeSubjectConfirmation.tenant_id == tenant_id
                )
            return {
                "principals": [
                    copy.deepcopy(row.payload)
                    for row in session.scalars(principal_statement).all()
                ],
                "accounts": [
                    copy.deepcopy(row.payload)
                    for row in session.scalars(account_statement).all()
                ],
                "authorizations": [
                    copy.deepcopy(row.payload)
                    for row in session.scalars(authorization_statement).all()
                ],
                "subject_confirmations": [
                    copy.deepcopy(row.payload)
                    for row in session.scalars(confirmation_statement).all()
                ],
            }

    def narrative_fragments(
        self,
        fragment_ids: list[str] | None = None,
        *,
        tenant_id: str | None = None,
        brand_id: str | None = None,
    ) -> tuple[JsonObject, ...]:
        with self.sessions() as session:
            statement = select(RuntimeNarrativeFragment)
            if fragment_ids is not None:
                statement = statement.where(
                    RuntimeNarrativeFragment.fragment_id.in_(fragment_ids)
                )
            if tenant_id is not None:
                statement = statement.where(
                    RuntimeNarrativeFragment.tenant_id == tenant_id
                )
            if brand_id is not None:
                statement = statement.where(
                    RuntimeNarrativeFragment.brand_id == brand_id
                )
            rows = session.scalars(
                statement.order_by(RuntimeNarrativeFragment.fragment_id)
            ).all()
            return tuple(copy.deepcopy(row.payload) for row in rows)

    def precise_facts(
        self,
        *,
        tenant_id: str | None = None,
        brand_id: str | None = None,
    ) -> tuple[JsonObject, ...]:
        with self.sessions() as session:
            statement = select(RuntimePreciseFact)
            if tenant_id is not None:
                statement = statement.where(RuntimePreciseFact.tenant_id == tenant_id)
            if brand_id is not None:
                statement = statement.where(RuntimePreciseFact.brand_id == brand_id)
            rows = session.scalars(statement.order_by(RuntimePreciseFact.fact_id)).all()
            return tuple(copy.deepcopy(row.payload) for row in rows)

    def bind_dify_documents(self, mapping: dict[str, JsonObject]) -> None:
        with self.sessions.begin() as session:
            known_ids = set(
                session.scalars(
                    select(RuntimeNarrativeFragment.fragment_id).where(
                        RuntimeNarrativeFragment.fragment_id.in_(mapping)
                    )
                ).all()
            )
            if known_ids != set(mapping):
                raise ValueError("Dify document mapping contains an unknown fragment")
            stale_rows = session.scalars(
                select(RuntimeNarrativeFragment).where(
                    RuntimeNarrativeFragment.fragment_id.not_in(mapping)
                )
            ).all()
            for stale_row in stale_rows:
                stale_row.dify_document_id = None
                stale_row.index_content_digest = None
                stale_row.updated_at = utc_now()
            for fragment_id, binding in mapping.items():
                row = session.get(RuntimeNarrativeFragment, fragment_id)
                if row is None:
                    raise RuntimeError("unreachable")
                document_id = binding.get("document_id")
                source_digest = binding.get("source_content_sha256")
                index_digest = binding.get("index_content_sha256")
                if (
                    not isinstance(document_id, str)
                    or not isinstance(source_digest, str)
                    or not isinstance(index_digest, str)
                    or len(source_digest) != 64
                    or len(index_digest) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in source_digest
                    )
                    or any(
                        character not in "0123456789abcdef"
                        for character in index_digest
                    )
                ):
                    raise ValueError("Dify document binding is invalid")
                if source_digest != row.content_digest:
                    raise ValueError(
                        "Dify document binding does not match the frozen source text"
                    )
                row.dify_document_id = document_id
                row.index_content_digest = index_digest
                row.updated_at = utc_now()

    def set_fragment_state(
        self,
        fragment_id: str,
        *,
        status: str,
        revocation_ref: str | None,
    ) -> None:
        with self.sessions.begin() as session:
            row = session.get(
                RuntimeNarrativeFragment, fragment_id, with_for_update=True
            )
            if row is None:
                raise KeyError(fragment_id)
            row.status = status
            row.revocation_ref = revocation_ref
            payload = copy.deepcopy(row.payload)
            payload["status"] = status
            payload["revocation_ref"] = revocation_ref
            row.payload = payload
            row.updated_at = utc_now()

    def setting(self, key: str) -> JsonObject:
        with self.sessions() as session:
            row = session.get(RuntimeSetting, key)
            if row is None:
                raise KeyError(key)
            return copy.deepcopy(row.payload)

    def reserve_dify_invocation(
        self,
        *,
        invocation_id: str,
        principal_id: str,
        model_call_upper_bound: int = 2,
        maximum_model_calls: int = 40,
    ) -> None:
        if model_call_upper_bound < 1:
            raise ValueError("A positive model-call upper bound is required")
        with _DIFY_BUDGET_RESERVATION_LOCK:
            with self.sessions.begin() as session:
                if session.get_bind().dialect.name == "postgresql":
                    session.execute(select(func.pg_advisory_xact_lock(744970071)))
                used = sum(
                    session.scalars(
                        select(RuntimeDifyInvocation.model_call_upper_bound)
                    ).all()
                )
                if used + model_call_upper_bound > maximum_model_calls:
                    raise ValueError("Package 7 model-call budget is exhausted")
                if session.get(RuntimeDifyInvocation, invocation_id) is not None:
                    raise ValueError("Dify invocation identity was reused")
                now = utc_now()
                session.add(
                    RuntimeDifyInvocation(
                        invocation_id=invocation_id,
                        principal_id=principal_id,
                        state="RESERVED",
                        model_call_upper_bound=model_call_upper_bound,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        total_price="0",
                        currency="UNKNOWN",
                        response_digest=None,
                        failure_class=None,
                        created_at=now,
                        updated_at=now,
                    )
                )

    def complete_dify_invocation(
        self,
        invocation_id: str,
        *,
        account_id: str,
        usage: JsonObject,
        response_digest: str,
        dify_user_key: str,
        conversation_id: str,
        persist_conversation: bool = True,
    ) -> None:
        if not dify_user_key or not conversation_id:
            raise ValueError("Dify conversation binding is incomplete")
        browser_session_id = current_browser_session_id()
        with self.sessions.begin() as session:
            row = session.get(
                RuntimeDifyInvocation, invocation_id, with_for_update=True
            )
            if row is None or row.state not in {
                "RESERVED",
                "RESPONSE_STAGED",
                "SUCCEEDED",
            }:
                raise ValueError("Unknown or completed Dify invocation")
            if row.state in {"RESPONSE_STAGED", "SUCCEEDED"} and (
                row.response_digest != response_digest
                or row.prompt_tokens != int(usage.get("prompt_tokens", 0))
                or row.completion_tokens
                != int(usage.get("completion_tokens", 0))
                or row.total_tokens != int(usage.get("total_tokens", 0))
                or row.total_price != str(usage.get("total_price", "0"))
                or row.currency != str(usage.get("currency", "UNKNOWN"))
            ):
                raise ValueError("Staged Dify response identity changed")
            principal = session.get(RuntimePrincipal, row.principal_id)
            account = session.get(RuntimeAccount, account_id)
            if (
                principal is None
                or account is None
                or account_id not in principal.allowed_account_ids
            ):
                raise ValueError(
                    "Dify conversation account is outside the principal scope"
                )
            if persist_conversation:
                binding = session.scalar(
                    select(RuntimeDifyConversation)
                    .where(
                        RuntimeDifyConversation.principal_id == row.principal_id,
                        RuntimeDifyConversation.account_id == account_id,
                        RuntimeDifyConversation.browser_session_id
                        == browser_session_id,
                    )
                    .with_for_update()
                )
                if binding is None:
                    now = utc_now()
                    session.add(
                        RuntimeDifyConversation(
                            principal_id=row.principal_id,
                            account_id=account_id,
                            browser_session_id=browser_session_id,
                            dify_user_key=dify_user_key,
                            conversation_id=conversation_id,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                elif (
                    binding.dify_user_key != dify_user_key
                    or binding.conversation_id != conversation_id
                ):
                    raise ValueError("Dify conversation identity changed unexpectedly")
            if row.state == "SUCCEEDED":
                return
            row.state = "SUCCEEDED"
            row.prompt_tokens = int(usage.get("prompt_tokens", 0))
            row.completion_tokens = int(usage.get("completion_tokens", 0))
            row.total_tokens = int(usage.get("total_tokens", 0))
            row.total_price = str(usage.get("total_price", "0"))
            row.currency = str(usage.get("currency", "UNKNOWN"))
            row.response_digest = response_digest
            row.updated_at = utc_now()

    def stage_dify_response(
        self,
        invocation_id: str,
        *,
        run_id: str,
        account_id: str,
        response_payload: JsonObject,
        response_digest: str,
        dify_user_key: str,
        conversation_id: str,
        persist_conversation: bool,
    ) -> None:
        """Durably stage one paid author response before downstream processing."""

        answer = response_payload.get("answer")
        usage = response_payload.get("usage")
        if not isinstance(answer, str) or not answer or not isinstance(usage, dict):
            raise ValueError("Dify response staging payload is invalid")
        if response_digest != digest_object({"answer": answer, "usage": usage}):
            raise ValueError("Dify response staging digest is invalid")
        browser_session_id = current_browser_session_id()
        with self.sessions.begin() as session:
            invocation = session.get(
                RuntimeDifyInvocation, invocation_id, with_for_update=True
            )
            if invocation is None or invocation.state != "RESERVED":
                raise ValueError("Unknown or completed Dify response staging target")
            run = session.scalar(
                select(RuntimeModelRun)
                .where(
                    RuntimeModelRun.run_id == run_id,
                    RuntimeModelRun.principal_id == invocation.principal_id,
                    RuntimeModelRun.account_id == account_id,
                    RuntimeModelRun.browser_session_id == browser_session_id,
                )
                .with_for_update()
            )
            if run is None:
                raise ValueError("Unknown or completed Dify response staging target")
            if run.state != "AWAITING_FIRST_MODEL_OUTPUT" or run.first_output_preserved:
                raise ValueError("Model run cannot accept a staged provider response")
            principal = session.get(RuntimePrincipal, invocation.principal_id)
            account = session.get(RuntimeAccount, account_id)
            if (
                principal is None
                or account is None
                or account_id not in principal.allowed_account_ids
            ):
                raise ValueError("Staged Dify response is outside the principal scope")
            invocation.state = "RESPONSE_STAGED"
            invocation.prompt_tokens = int(usage.get("prompt_tokens", 0))
            invocation.completion_tokens = int(usage.get("completion_tokens", 0))
            invocation.total_tokens = int(usage.get("total_tokens", 0))
            invocation.total_price = str(usage.get("total_price", "0"))
            invocation.currency = str(usage.get("currency", "UNKNOWN"))
            invocation.response_digest = response_digest
            invocation.updated_at = utc_now()
            merged_payload = copy.deepcopy(run.payload)
            merged_payload["provider_response_staging"] = {
                "invocation_id": invocation_id,
                "account_id": account_id,
                "answer": answer,
                "answer_digest": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
                "usage": copy.deepcopy(usage),
                "response_digest": response_digest,
                "dify_user_key": dify_user_key,
                "conversation_id": conversation_id,
                "persist_conversation": persist_conversation,
            }
            run.payload = merged_payload
            run.state = "PROVIDER_RESPONSE_STAGED"
            run.updated_at = utc_now()

    def recoverable_staged_model_output(
        self,
        *,
        principal_id: str,
        account_id: str,
    ) -> JsonObject | None:
        """Return the sole scoped paid response awaiting deterministic finalization."""

        browser_session_id = current_browser_session_id()
        with self.sessions() as session:
            rows = list(
                session.scalars(
                    select(RuntimeModelRun)
                    .where(
                        RuntimeModelRun.principal_id == principal_id,
                        RuntimeModelRun.account_id == account_id,
                        RuntimeModelRun.browser_session_id == browser_session_id,
                        RuntimeModelRun.state.in_(
                            ("PROVIDER_RESPONSE_STAGED", "FIRST_OUTPUT_RECEIVED")
                        ),
                    )
                    .order_by(RuntimeModelRun.created_at)
                ).all()
            )
        recoverable: list[JsonObject] = []
        for row in rows:
            staging = row.payload.get("provider_response_staging")
            if not isinstance(staging, dict):
                continue
            answer = staging.get("answer")
            answer_digest = staging.get("answer_digest")
            usage = staging.get("usage")
            response_digest = staging.get("response_digest")
            if (
                not isinstance(answer, str)
                or not answer
                or answer_digest != hashlib.sha256(answer.encode("utf-8")).hexdigest()
                or not isinstance(usage, dict)
                or response_digest
                != digest_object({"answer": answer, "usage": usage})
                or staging.get("account_id") != account_id
                or not all(
                    isinstance(staging.get(key), str) and staging[key]
                    for key in (
                        "invocation_id",
                        "account_id",
                        "dify_user_key",
                        "conversation_id",
                    )
                )
                or not isinstance(staging.get("persist_conversation"), bool)
            ):
                raise ValueError("Staged provider response integrity failed")
            recoverable.append({"run_id": row.run_id, **copy.deepcopy(staging)})
        if len(recoverable) > 1:
            raise ValueError("Multiple staged provider responses require operator review")
        return recoverable[0] if recoverable else None

    def dify_conversation(
        self, principal_id: str, account_id: str
    ) -> tuple[str, str] | None:
        browser_session_id = current_browser_session_id()
        with self.sessions() as session:
            row = session.scalar(
                select(RuntimeDifyConversation).where(
                    RuntimeDifyConversation.principal_id == principal_id,
                    RuntimeDifyConversation.account_id == account_id,
                    RuntimeDifyConversation.browser_session_id == browser_session_id,
                )
            )
            if row is None:
                return None
            return row.dify_user_key, row.conversation_id

    def adopt_dify_conversation(
        self,
        *,
        principal_id: str,
        account_id: str,
        dify_user_key: str,
        conversation_id: str,
    ) -> None:
        """Bind one current-app conversation when no runtime binding exists yet."""

        if not dify_user_key or not conversation_id:
            raise ValueError("Dify conversation binding is incomplete")
        browser_session_id = current_browser_session_id()
        with self.sessions.begin() as session:
            principal = session.get(RuntimePrincipal, principal_id)
            account = session.get(RuntimeAccount, account_id)
            if (
                principal is None
                or account is None
                or account_id not in principal.allowed_account_ids
            ):
                raise ValueError(
                    "Dify conversation account is outside the principal scope"
                )
            row = session.scalar(
                select(RuntimeDifyConversation)
                .where(
                    RuntimeDifyConversation.principal_id == principal_id,
                    RuntimeDifyConversation.account_id == account_id,
                    RuntimeDifyConversation.browser_session_id == browser_session_id,
                )
                .with_for_update()
            )
            if row is not None:
                if (
                    row.dify_user_key != dify_user_key
                    or row.conversation_id != conversation_id
                ):
                    raise ValueError("Existing Dify conversation binding is immutable")
                return
            now = utc_now()
            session.add(
                RuntimeDifyConversation(
                    principal_id=principal_id,
                    account_id=account_id,
                    browser_session_id=browser_session_id,
                    dify_user_key=dify_user_key,
                    conversation_id=conversation_id,
                    created_at=now,
                    updated_at=now,
                )
            )

    def fail_dify_invocation(self, invocation_id: str, *, failure_class: str) -> None:
        with self.sessions.begin() as session:
            row = session.get(
                RuntimeDifyInvocation, invocation_id, with_for_update=True
            )
            if row is None or row.state != "RESERVED":
                raise ValueError("Unknown or completed Dify invocation")
            row.state = "FAILED_OR_UNKNOWN_BILLING"
            row.failure_class = failure_class[:80]
            row.updated_at = utc_now()

    def dify_invocation_audit(self) -> JsonObject:
        with self.sessions() as session:
            rows = list(
                session.scalars(
                    select(RuntimeDifyInvocation).order_by(
                        RuntimeDifyInvocation.created_at
                    )
                ).all()
            )
            return {
                "invocation_count": len(rows),
                "model_call_upper_bound": sum(
                    row.model_call_upper_bound for row in rows
                ),
                "known_total_tokens": sum(row.total_tokens for row in rows),
                "known_prices": [
                    {"total_price": row.total_price, "currency": row.currency}
                    for row in rows
                    if row.state == "SUCCEEDED"
                ],
                "failed_or_unknown_billing_count": sum(
                    row.state == "FAILED_OR_UNKNOWN_BILLING" for row in rows
                ),
            }

    def save_requirement(
        self, payload: JsonObject, principal_id: str, account_id: str
    ) -> None:
        requirement_id = str(payload["requirement_id"])
        version = int(payload["requirement_version"])
        with self.sessions.begin() as session:
            existing = session.scalar(
                select(RuntimeRequirement).where(
                    RuntimeRequirement.requirement_id == requirement_id,
                    RuntimeRequirement.requirement_version == version,
                )
            )
            if existing is not None:
                if digest_object(existing.payload) != digest_object(payload):
                    raise ValueError(
                        "Requirement identity was reused with different content"
                    )
                return
            session.add(
                RuntimeRequirement(
                    requirement_id=requirement_id,
                    requirement_version=version,
                    principal_id=principal_id,
                    account_id=account_id,
                    browser_session_id=current_browser_session_id(),
                    status=str(payload["status"]),
                    payload=copy.deepcopy(payload),
                    created_at=utc_now(),
                )
            )

    def start_model_run(
        self,
        *,
        run_id: str,
        principal_id: str,
        account_id: str,
        operation: str,
        plan_ref: str | None,
        prompt_digest: str,
        payload: JsonObject,
    ) -> None:
        with self.sessions.begin() as session:
            if session.get(RuntimeModelRun, run_id) is not None:
                raise ValueError("Model run already exists")
            now = utc_now()
            session.add(
                RuntimeModelRun(
                    run_id=run_id,
                    principal_id=principal_id,
                    account_id=account_id,
                    browser_session_id=current_browser_session_id(),
                    operation=operation,
                    state="AWAITING_FIRST_MODEL_OUTPUT",
                    plan_ref=plan_ref,
                    prompt_digest=prompt_digest,
                    model_output_digest=None,
                    first_output_preserved=False,
                    payload=copy.deepcopy(payload),
                    created_at=now,
                    updated_at=now,
                )
            )

    def model_run(self, run_id: str) -> RuntimeModelRun | None:
        with self.sessions() as session:
            return session.get(RuntimeModelRun, run_id)

    def model_run_for_request(
        self,
        run_id: str,
        *,
        principal_id: str,
        account_id: str | None,
        browser_session_id: str,
    ) -> RuntimeModelRun | None:
        conditions = [
            RuntimeModelRun.run_id == run_id,
            RuntimeModelRun.principal_id == principal_id,
            RuntimeModelRun.browser_session_id == browser_session_id,
        ]
        if account_id is not None:
            conditions.append(RuntimeModelRun.account_id == account_id)
        with self.sessions() as session:
            return session.scalar(select(RuntimeModelRun).where(*conditions))

    def recent_chat_turns(
        self,
        *,
        principal_id: str,
        account_id: str,
        limit: int = 6,
    ) -> tuple[JsonObject, ...]:
        """Return only accepted, sanitized chat surfaces for bounded continuity."""

        if limit < 1 or limit > 12:
            raise ValueError("Chat continuity limit must be between 1 and 12")
        browser_session_id = current_browser_session_id()
        with self.sessions() as session:
            rows = list(
                session.scalars(
                    select(RuntimeModelRun)
                    .where(
                        RuntimeModelRun.principal_id == principal_id,
                        RuntimeModelRun.account_id == account_id,
                        RuntimeModelRun.browser_session_id == browser_session_id,
                        RuntimeModelRun.operation.in_(("普通聊天", "找灵感")),
                        RuntimeModelRun.state == "FIRST_OUTPUT_ACCEPTED",
                    )
                    .order_by(RuntimeModelRun.created_at.desc())
                    .limit(limit)
                ).all()
            )
        turns: list[JsonObject] = []
        for row in reversed(rows):
            prompt = row.payload.get("prompt")
            envelope = row.payload.get("envelope")
            user_message = (
                prompt.get("user_message") if isinstance(prompt, dict) else None
            )
            reply = envelope.get("reply") if isinstance(envelope, dict) else None
            if isinstance(user_message, str) and isinstance(reply, str):
                turns.append({"user_message": user_message, "assistant_reply": reply})
        return tuple(turns)

    def receive_first_output(
        self,
        run_id: str,
        *,
        output_digest: str,
        output_size_bytes: int,
    ) -> RuntimeModelRun:
        scope = current_trusted_database_scope()
        if not all(
            isinstance(value, str) and value
            for value in (
                scope.principal_id,
                scope.account_id,
                scope.browser_session_id,
            )
        ):
            raise RuntimeError("A complete trusted runtime scope is required")
        with self.sessions.begin() as session:
            row = session.scalar(
                select(RuntimeModelRun)
                .where(
                    RuntimeModelRun.run_id == run_id,
                    RuntimeModelRun.principal_id == scope.principal_id,
                    RuntimeModelRun.account_id == scope.account_id,
                    RuntimeModelRun.browser_session_id == scope.browser_session_id,
                )
                .with_for_update()
            )
            if row is None:
                raise KeyError(run_id)
            if row.first_output_preserved:
                raise ValueError("Content reroll is forbidden for a completed run")
            if row.state not in {
                "AWAITING_FIRST_MODEL_OUTPUT",
                "PROVIDER_RESPONSE_STAGED",
            }:
                raise ValueError("Model run is not awaiting first output")
            staging = row.payload.get("provider_response_staging")
            if isinstance(staging, dict) and staging.get("answer_digest") != output_digest:
                raise ValueError("Staged provider response digest changed")
            row.model_output_digest = output_digest
            row.first_output_preserved = True
            row.state = "FIRST_OUTPUT_RECEIVED"
            merged_payload = copy.deepcopy(row.payload)
            merged_payload["first_output_receipt"] = {
                "sha256": output_digest,
                "size_bytes": output_size_bytes,
                "raw_content_persisted": isinstance(staging, dict),
            }
            row.payload = merged_payload
            row.updated_at = utc_now()
            session.flush()
            return row

    def fail_model_run_before_output(
        self,
        run_id: str,
        *,
        failure_stage: str,
        error_type: str,
    ) -> RuntimeModelRun:
        """Close one scoped model run when its provider returns no output."""

        scope = current_trusted_database_scope()
        if not all(
            isinstance(value, str) and value
            for value in (
                scope.principal_id,
                scope.account_id,
                scope.browser_session_id,
            )
        ):
            raise RuntimeError("A complete trusted runtime scope is required")
        with self.sessions.begin() as session:
            row = session.scalar(
                select(RuntimeModelRun)
                .where(
                    RuntimeModelRun.run_id == run_id,
                    RuntimeModelRun.principal_id == scope.principal_id,
                    RuntimeModelRun.account_id == scope.account_id,
                    RuntimeModelRun.browser_session_id == scope.browser_session_id,
                )
                .with_for_update()
            )
            if row is None:
                raise KeyError(run_id)
            if row.state != "AWAITING_FIRST_MODEL_OUTPUT" or row.first_output_preserved:
                raise ValueError("Model run is no longer awaiting provider output")
            row.state = "PROVIDER_FAILED_BEFORE_OUTPUT"
            merged_payload = copy.deepcopy(row.payload)
            merged_payload.update(
                {
                    "result_class": "SYSTEM_OR_PROVIDER_ERROR",
                    "failure_stage": failure_stage,
                    "error_type": error_type,
                    "first_output_preserved": False,
                }
            )
            row.payload = merged_payload
            row.updated_at = utc_now()
            session.flush()
            return row

    def preserve_first_output(
        self,
        run_id: str,
        output_digest: str,
        state: str,
        payload: JsonObject,
    ) -> RuntimeModelRun:
        scope = current_trusted_database_scope()
        if not all(
            isinstance(value, str) and value
            for value in (
                scope.principal_id,
                scope.account_id,
                scope.browser_session_id,
            )
        ):
            raise RuntimeError("A complete trusted runtime scope is required")
        with self.sessions.begin() as session:
            row = session.scalar(
                select(RuntimeModelRun)
                .where(
                    RuntimeModelRun.run_id == run_id,
                    RuntimeModelRun.principal_id == scope.principal_id,
                    RuntimeModelRun.account_id == scope.account_id,
                    RuntimeModelRun.browser_session_id == scope.browser_session_id,
                )
                .with_for_update()
            )
            if row is None:
                raise KeyError(run_id)
            if row.first_output_preserved and not (
                row.state == "FIRST_OUTPUT_RECEIVED"
                and row.model_output_digest == output_digest
            ):
                raise ValueError("Content reroll is forbidden for a completed run")
            row.model_output_digest = output_digest
            row.first_output_preserved = True
            row.state = state
            merged_payload = copy.deepcopy(row.payload)
            merged_payload.pop("provider_response_staging", None)
            merged_payload.update(copy.deepcopy(payload))
            row.payload = merged_payload
            row.updated_at = utc_now()
            session.flush()
            return row

    def save_candidate_set(
        self,
        *,
        run_id: str,
        account_id: str,
        plan_ref: str,
        candidates: list[JsonObject],
        validations: list[JsonObject],
        preserved_revalidation_digest: str | None = None,
        preserved_revalidation_payload: JsonObject | None = None,
    ) -> None:
        if len(candidates) != len(validations):
            raise ValueError("Every candidate needs one validation")
        if (preserved_revalidation_digest is None) != (
            preserved_revalidation_payload is None
        ):
            raise ValueError("Preserved revalidation fields must be supplied together")
        scope = current_trusted_database_scope()
        with self.sessions.begin() as session:
            source_run = session.scalar(
                select(RuntimeModelRun).where(
                    RuntimeModelRun.run_id == run_id,
                    RuntimeModelRun.principal_id == scope.principal_id,
                    RuntimeModelRun.account_id == account_id,
                    RuntimeModelRun.browser_session_id == scope.browser_session_id,
                )
            )
            if (
                source_run is None
                or source_run.account_id != account_id
                or source_run.browser_session_id != current_browser_session_id()
            ):
                raise ValueError("Candidate run is outside the browser session scope")
            revalidated_run = None
            if preserved_revalidation_digest is not None:
                revalidated_run = session.get(
                    RuntimeModelRun,
                    run_id,
                    with_for_update=True,
                )
                if (
                    revalidated_run is None
                    or not revalidated_run.first_output_preserved
                    or revalidated_run.state != "FIRST_OUTPUT_REJECTED"
                    or revalidated_run.model_output_digest
                    != preserved_revalidation_digest
                ):
                    raise ValueError(
                        "Preserved model output is not eligible for revalidation"
                    )
                existing_candidate = session.scalar(
                    select(RuntimeCandidate.candidate_id)
                    .where(RuntimeCandidate.run_id == run_id)
                    .limit(1)
                )
                if existing_candidate is not None:
                    raise ValueError("Preserved model output was already materialized")
            for ordinal, (candidate, validation) in enumerate(
                zip(candidates, validations, strict=True), 1
            ):
                candidate_id = str(candidate["candidate_id"])
                session.add(
                    RuntimeCandidate(
                        candidate_id=candidate_id,
                        run_id=run_id,
                        plan_ref=plan_ref,
                        principal_id=source_run.principal_id,
                        account_id=account_id,
                        browser_session_id=source_run.browser_session_id,
                        ordinal=ordinal,
                        selected=False,
                        candidate_payload=copy.deepcopy(candidate),
                        used_fact_refs=list(candidate["used_fact_refs"]),
                        used_material_refs=list(candidate["used_material_refs"]),
                        created_at=utc_now(),
                    )
                )
                session.add(
                    RuntimeValidation(
                        validation_id=str(validation["decision_id"]),
                        candidate_id=candidate_id,
                        decision=str(validation["decision"]),
                        payload=copy.deepcopy(validation),
                        created_at=utc_now(),
                    )
                )
            if revalidated_run is not None:
                merged_payload = copy.deepcopy(revalidated_run.payload)
                merged_payload["deterministic_revalidation"] = copy.deepcopy(
                    preserved_revalidation_payload
                )
                revalidated_run.payload = merged_payload
                revalidated_run.state = (
                    "FIRST_OUTPUT_ACCEPTED_AFTER_DETERMINISTIC_REVALIDATION"
                )
                revalidated_run.updated_at = utc_now()

    def latest_candidates(
        self,
        principal_id: str,
        account_id: str,
    ) -> tuple[RuntimeCandidate, ...]:
        browser_session_id = current_browser_session_id()
        with self.sessions() as session:
            latest_run = session.scalar(
                select(RuntimeCandidate.run_id)
                .where(
                    RuntimeCandidate.principal_id == principal_id,
                    RuntimeCandidate.account_id == account_id,
                    RuntimeCandidate.browser_session_id == browser_session_id,
                )
                .order_by(RuntimeCandidate.created_at.desc())
                .limit(1)
            )
            if latest_run is None:
                return ()
            rows = session.scalars(
                select(RuntimeCandidate)
                .where(RuntimeCandidate.run_id == latest_run)
                .order_by(RuntimeCandidate.ordinal)
            ).all()
            return tuple(
                row for row in rows if self._candidate_is_current(session, row)
            )

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @classmethod
    def _authorization_allows(
        cls,
        session: Session,
        authorization_ref: str,
        account: RuntimeAccount,
        now: datetime,
    ) -> bool:
        authorization = session.get(RuntimeAuthorization, authorization_ref)
        if (
            authorization is None
            or authorization.tenant_id != account.tenant_id
            or authorization.status != "GRANTED"
            or cls._aware(authorization.valid_from) > now
            or cls._aware(authorization.valid_until) < now
        ):
            return False
        payload = authorization.payload
        return bool(
            payload.get("brand_id") == account.brand_id
            and account.account_id in payload.get("permitted_content_account_ids", [])
            and account.organization_id in payload.get("permitted_organization_ids", [])
            and account.store_id in payload.get("permitted_store_ids", [])
        )

    @classmethod
    def _candidate_is_current(
        cls,
        session: Session,
        candidate: RuntimeCandidate,
    ) -> bool:
        account = session.get(RuntimeAccount, candidate.account_id)
        if account is None or account.status != "ACTIVE":
            return False
        now = utc_now()
        for reference in candidate.used_material_refs:
            material = session.get(RuntimeNarrativeFragment, reference)
            if (
                material is None
                or material.tenant_id != account.tenant_id
                or material.brand_id != account.brand_id
                or material.status != "ACTIVE"
                or material.authorization_state != "GRANTED"
                or material.revocation_ref is not None
                or cls._aware(material.valid_from) > now
                or cls._aware(material.valid_until) < now
                or account.account_id
                not in material.payload.get("applicable_content_account_ids", [])
                or account.organization_id
                not in material.payload.get("applicable_organization_ids", [])
                or account.store_id
                not in material.payload.get("applicable_store_ids", [])
                or not cls._authorization_allows(
                    session,
                    material.authorization_ref,
                    account,
                    now,
                )
            ):
                return False
        for reference in candidate.used_fact_refs:
            fact = session.get(RuntimePreciseFact, reference)
            if (
                fact is None
                or fact.tenant_id != account.tenant_id
                or fact.brand_id != account.brand_id
                or fact.status != "ACTIVE"
                or fact.revocation_ref is not None
                or cls._aware(fact.valid_from) > now
                or cls._aware(fact.valid_until) < now
                or account.account_id
                not in fact.payload.get("applicable_content_account_ids", [])
                or not cls._authorization_allows(
                    session,
                    fact.authorization_ref,
                    account,
                    now,
                )
            ):
                return False
        return True

    def select_candidate(
        self,
        principal_id: str,
        account_id: str,
        ordinal: int,
    ) -> RuntimeCandidate:
        browser_session_id = current_browser_session_id()
        with self.sessions.begin() as session:
            candidates = list(
                session.scalars(
                    select(RuntimeCandidate)
                    .where(
                        RuntimeCandidate.principal_id == principal_id,
                        RuntimeCandidate.account_id == account_id,
                        RuntimeCandidate.browser_session_id == browser_session_id,
                    )
                    .order_by(
                        RuntimeCandidate.created_at.desc(), RuntimeCandidate.ordinal
                    )
                ).all()
            )
            if not candidates:
                raise KeyError("No candidate set exists")
            latest_run = candidates[0].run_id
            current = [row for row in candidates if row.run_id == latest_run]
            chosen = next((row for row in current if row.ordinal == ordinal), None)
            if chosen is None:
                raise KeyError("Candidate number is unavailable")
            if not self._candidate_is_current(session, chosen):
                raise ValueError("Candidate references are no longer current")
            for row in current:
                row.selected = row.candidate_id == chosen.candidate_id
            self._append_candidate_activity(
                chosen,
                operation="SELECT",
                principal_id=principal_id,
                browser_session_id=browser_session_id,
            )
            session.flush()
            return chosen

    def selected_candidate(
        self,
        principal_id: str,
        account_id: str,
    ) -> RuntimeCandidate | None:
        browser_session_id = current_browser_session_id()
        with self.sessions() as session:
            row = session.scalar(
                select(RuntimeCandidate)
                .where(
                    RuntimeCandidate.principal_id == principal_id,
                    RuntimeCandidate.account_id == account_id,
                    RuntimeCandidate.browser_session_id == browser_session_id,
                    RuntimeCandidate.selected.is_(True),
                )
                .order_by(RuntimeCandidate.created_at.desc())
                .limit(1)
            )
            return (
                row
                if row is not None and self._candidate_is_current(session, row)
                else None
            )

    def candidate_belongs_to_account(
        self,
        candidate_id: str,
        principal_id: str,
        account_id: str,
    ) -> bool:
        with self.sessions() as session:
            row = session.get(RuntimeCandidate, candidate_id)
            return bool(
                row is not None
                and row.principal_id == principal_id
                and row.account_id == account_id
                and row.browser_session_id == current_browser_session_id()
                and self._candidate_is_current(session, row)
            )

    def candidate_context(
        self,
        candidate_id: str,
        principal_id: str,
        account_id: str,
    ) -> JsonObject:
        """Return a minimal continuity projection, never a new fact source."""

        with self.sessions() as session:
            row = session.get(RuntimeCandidate, candidate_id)
            if (
                row is None
                or row.principal_id != principal_id
                or row.account_id != account_id
                or row.browser_session_id != current_browser_session_id()
            ):
                raise ValueError("Previous candidate is outside the current account")
            if not self._candidate_is_current(session, row):
                raise ValueError("Previous candidate references are no longer current")
            surfaces = row.candidate_payload.get("candidate_user_visible_surfaces", {})
            production = (
                surfaces.get("execution_payload", {})
                if isinstance(surfaces, dict)
                else {}
            )
            return {
                "title": str(surfaces.get("title", ""))
                if isinstance(surfaces, dict)
                else "",
                "core_idea": str(production.get("core_idea", ""))
                if isinstance(production, dict)
                else "",
                "content_direction": (
                    str(production.get("content_direction", ""))
                    if isinstance(production, dict)
                    else ""
                ),
                "ending_and_action": (
                    str(production.get("ending_and_action", ""))
                    if isinstance(production, dict)
                    else ""
                ),
                "continuity_only_not_a_fact_source": True,
            }

    def latest_candidate(
        self,
        principal_id: str,
        account_id: str,
    ) -> RuntimeCandidate | None:
        browser_session_id = current_browser_session_id()
        with self.sessions() as session:
            row = session.scalar(
                select(RuntimeCandidate)
                .where(
                    RuntimeCandidate.principal_id == principal_id,
                    RuntimeCandidate.account_id == account_id,
                    RuntimeCandidate.browser_session_id == browser_session_id,
                )
                .order_by(RuntimeCandidate.created_at.desc(), RuntimeCandidate.ordinal)
                .limit(1)
            )
            return (
                row
                if row is not None and self._candidate_is_current(session, row)
                else None
            )

    def requirement_id_for_run(self, run_id: str) -> str | None:
        with self.sessions() as session:
            run = session.get(RuntimeModelRun, run_id)
            if run is None or run.plan_ref is None:
                return None
            plan = session.scalar(
                select(RuntimePlan).where(RuntimePlan.plan_ref == run.plan_ref)
            )
            if plan is None:
                return None
            requirement = plan.source_request.get("confirmed_requirement")
            if not isinstance(requirement, dict):
                return None
            value = requirement.get("requirement_id")
            return value if isinstance(value, str) else None

    def requirement_context_for_run(self, run_id: str) -> JsonObject:
        with self.sessions() as session:
            run = session.get(RuntimeModelRun, run_id)
            if run is None or run.plan_ref is None:
                return {}
            plan = session.scalar(
                select(RuntimePlan).where(RuntimePlan.plan_ref == run.plan_ref)
            )
            if plan is None:
                return {}
            requirement = plan.source_request.get("confirmed_requirement")
            return copy.deepcopy(requirement) if isinstance(requirement, dict) else {}

    def save_feedback(
        self,
        *,
        principal_id: str,
        account_id: str,
        candidate_id: str | None,
        requirement_id: str | None,
        role_id: str | None,
        storyline_id: str | None,
        column_id: str | None,
        previous_content_ref: str | None,
        fact_refs: list[str],
        material_refs: list[str],
        short_reason: str,
    ) -> str:
        seed = [
            principal_id,
            account_id,
            candidate_id,
            short_reason,
            utc_now().isoformat(),
        ]
        feedback_id = f"FEEDBACK-{digest_object(seed)[:20].upper()}"
        with self.sessions.begin() as session:
            session.add(
                RuntimeFeedback(
                    feedback_id=feedback_id,
                    principal_id=principal_id,
                    account_id=account_id,
                    browser_session_id=current_browser_session_id(),
                    candidate_id=candidate_id,
                    requirement_id=requirement_id,
                    role_id=role_id,
                    storyline_id=storyline_id,
                    column_id=column_id,
                    previous_content_ref=previous_content_ref,
                    fact_refs=list(fact_refs),
                    material_refs=list(material_refs),
                    review_state="PENDING_REVIEW",
                    short_reason=short_reason,
                    created_at=utc_now(),
                )
            )
        return feedback_id

    @staticmethod
    def _append_candidate_activity(
        candidate: RuntimeCandidate,
        *,
        operation: str,
        principal_id: str,
        browser_session_id: str,
    ) -> None:
        payload = copy.deepcopy(candidate.candidate_payload)
        events = payload.get("runtime_activity")
        if not isinstance(events, list):
            events = []
        event_number = len(events) + 1
        events.append(
            {
                "event_version": event_number,
                "operation": operation,
                "principal_id": principal_id,
                "browser_session_id": browser_session_id,
                "recorded_at": utc_now().isoformat(),
            }
        )
        payload["runtime_activity"] = events
        candidate.candidate_payload = payload

    def record_selected_candidate_activity(
        self,
        *,
        principal_id: str,
        account_id: str,
        operation: str,
    ) -> RuntimeCandidate:
        browser_session_id = current_browser_session_id()
        with self.sessions.begin() as session:
            row = session.scalar(
                select(RuntimeCandidate)
                .where(
                    RuntimeCandidate.principal_id == principal_id,
                    RuntimeCandidate.account_id == account_id,
                    RuntimeCandidate.browser_session_id == browser_session_id,
                    RuntimeCandidate.selected.is_(True),
                )
                .order_by(RuntimeCandidate.created_at.desc())
                .limit(1)
                .with_for_update()
            )
            if row is None or not self._candidate_is_current(session, row):
                raise KeyError("No current selected candidate exists")
            self._append_candidate_activity(
                row,
                operation=operation,
                principal_id=principal_id,
                browser_session_id=browser_session_id,
            )
            session.flush()
            return row

    def transactional_probe(self, mutation: Callable[[Session], None]) -> None:
        """Exercise rollback behavior without permitting a partial commit."""

        session = self.sessions()
        try:
            mutation(session)
            raise RuntimeError("intentional rollback probe")
        except RuntimeError:
            session.rollback()
        finally:
            session.close()
