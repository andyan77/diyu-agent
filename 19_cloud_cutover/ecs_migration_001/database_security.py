#!/usr/bin/env python3
"""Package 9 PostgreSQL role separation and row-level security."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg import sql


MIGRATION_ROLE = "diyu_pkg9_migrator"
RUNTIME_ROLE = "diyu_pkg9_runtime"
LEGACY_ROLE = "diyu_pkg7_runtime"
DATABASE_NAME = "diyu_pkg7_runtime"
POLICY_NAME = "diyu_pkg9_scope"
IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,62}$")


def _setting(name: str) -> str:
    return f"NULLIF(current_setting('app.{name}', true), '')"


TENANT = _setting("tenant_id")
BRAND = _setting("brand_id")
ORGANIZATION = _setting("organization_id")
STORE = _setting("store_id")
ACCOUNT = _setting("account_id")
PRINCIPAL = _setting("principal_id")


def _optional(column: str, setting: str) -> str:
    return f"({setting} IS NULL OR {column} = {setting})"


def _account_scope(alias: str, account_column: str) -> str:
    account = f"{alias}.{account_column}"
    return (
        "EXISTS (SELECT 1 FROM runtime_content_accounts AS scope_account "
        f"WHERE scope_account.account_id = {account} "
        f"AND scope_account.tenant_id = {TENANT} "
        f"AND ({BRAND} IS NULL OR scope_account.brand_id = {BRAND}) "
        f"AND ({ORGANIZATION} IS NULL OR scope_account.organization_id = {ORGANIZATION}) "
        f"AND ({STORE} IS NULL OR scope_account.store_id IS NOT DISTINCT FROM {STORE}) "
        f"AND ({ACCOUNT} IS NULL OR scope_account.account_id = {ACCOUNT}) "
        f"AND ({PRINCIPAL} IS NULL OR EXISTS ("
        "SELECT 1 FROM runtime_principals AS scope_principal "
        f"WHERE scope_principal.principal_id = {PRINCIPAL} "
        f"AND scope_principal.tenant_id = {TENANT} "
        "AND scope_account.account_id IN ("
        "SELECT jsonb_array_elements_text(scope_principal.allowed_account_ids::jsonb)"
        "))))"
    )


def _principal_scope(alias: str, principal_column: str) -> str:
    principal = f"{alias}.{principal_column}"
    return (
        "EXISTS (SELECT 1 FROM runtime_principals AS scope_principal "
        f"WHERE scope_principal.principal_id = {principal} "
        f"AND scope_principal.tenant_id = {TENANT} "
        f"AND ({PRINCIPAL} IS NULL OR scope_principal.principal_id = {PRINCIPAL}))"
    )


TABLE_POLICIES: dict[str, str] = {
    "runtime_tenants": f"tenant_id = {TENANT}",
    "runtime_brands": (
        f"tenant_id = {TENANT} AND {_optional('brand_id', BRAND)}"
    ),
    "runtime_organizations": (
        f"tenant_id = {TENANT} AND {_optional('organization_id', ORGANIZATION)}"
    ),
    "runtime_stores": (
        "EXISTS (SELECT 1 FROM runtime_organizations AS scope_organization "
        "WHERE scope_organization.organization_id = runtime_stores.organization_id "
        f"AND scope_organization.tenant_id = {TENANT} "
        f"AND ({ORGANIZATION} IS NULL "
        f"OR scope_organization.organization_id = {ORGANIZATION})) "
        f"AND {_optional('store_id', STORE)}"
    ),
    "runtime_principals": (
        f"tenant_id = {TENANT} AND {_optional('principal_id', PRINCIPAL)}"
    ),
    "runtime_content_accounts": (
        f"tenant_id = {TENANT} "
        f"AND {_optional('brand_id', BRAND)} "
        f"AND {_optional('organization_id', ORGANIZATION)} "
        f"AND ({STORE} IS NULL OR store_id IS NOT DISTINCT FROM {STORE}) "
        f"AND {_optional('account_id', ACCOUNT)} "
        f"AND ({PRINCIPAL} IS NULL OR EXISTS ("
        "SELECT 1 FROM runtime_principals AS scope_principal "
        f"WHERE scope_principal.principal_id = {PRINCIPAL} "
        f"AND scope_principal.tenant_id = {TENANT} "
        "AND runtime_content_accounts.account_id IN ("
        "SELECT jsonb_array_elements_text(scope_principal.allowed_account_ids::jsonb)"
        ")))"
    ),
    "runtime_authorizations": f"tenant_id = {TENANT}",
    "runtime_narrative_fragments": (
        f"tenant_id = {TENANT} AND {_optional('brand_id', BRAND)}"
    ),
    "runtime_precise_facts": (
        f"tenant_id = {TENANT} AND {_optional('brand_id', BRAND)}"
    ),
    "runtime_subject_confirmations": f"tenant_id = {TENANT}",
    "runtime_settings": (
        "setting_key = 'neutral_expression_profile' "
        f"OR setting_key = 'identity_authority:' || {TENANT} "
        f"OR ({BRAND} IS NOT NULL "
        f"AND setting_key = 'brand_expression_profile:' || {BRAND})"
    ),
    "runtime_requirements": (
        _principal_scope("runtime_requirements", "principal_id")
        + " AND "
        + _account_scope("runtime_requirements", "account_id")
    ),
    "runtime_plans": (
        f"plan_key::jsonb ->> 0 = {TENANT} AND "
        + _account_scope("runtime_plans", "plan_key::jsonb ->> 1")
    ),
    "runtime_model_runs": (
        _principal_scope("runtime_model_runs", "principal_id")
        + " AND "
        + _account_scope("runtime_model_runs", "account_id")
    ),
    "runtime_candidates": _account_scope("runtime_candidates", "account_id"),
    "runtime_validations": (
        "EXISTS (SELECT 1 FROM runtime_candidates AS scope_candidate "
        "WHERE scope_candidate.candidate_id = runtime_validations.candidate_id "
        "AND "
        + _account_scope("scope_candidate", "account_id")
        + ")"
    ),
    "runtime_feedback": (
        _principal_scope("runtime_feedback", "principal_id")
        + " AND "
        + _account_scope("runtime_feedback", "account_id")
    ),
    "runtime_dify_invocations": _principal_scope(
        "runtime_dify_invocations", "principal_id"
    ),
    "runtime_dify_conversations": (
        _principal_scope("runtime_dify_conversations", "principal_id")
        + " AND "
        + _account_scope("runtime_dify_conversations", "account_id")
    ),
}


RUNTIME_WRITE_TABLES = frozenset(TABLE_POLICIES)
MIGRATION_ONLY_TABLES = frozenset(
    {
        "runtime_sources",
        "hosted_brand_revisions",
        "hosted_operation_audit",
        "hosted_schema_state",
    }
)


@dataclass(frozen=True)
class DatabaseScope:
    tenant_id: str
    brand_id: str | None = None
    organization_id: str | None = None
    store_id: str | None = None
    account_id: str | None = None
    principal_id: str | None = None

    def settings(self) -> dict[str, str]:
        return {
            "app.tenant_id": self.tenant_id,
            "app.brand_id": self.brand_id or "",
            "app.organization_id": self.organization_id or "",
            "app.store_id": self.store_id or "",
            "app.account_id": self.account_id or "",
            "app.principal_id": self.principal_id or "",
        }


def _validate_identifier(value: str) -> str:
    if IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError("PostgreSQL identifier is outside the Package 9 contract")
    return value


def render_security_sql(
    *,
    migration_role: str = MIGRATION_ROLE,
    runtime_role: str = RUNTIME_ROLE,
    legacy_role: str = LEGACY_ROLE,
) -> str:
    """Render the deterministic role grants, ownership, and RLS policy migration."""

    migration_role = _validate_identifier(migration_role)
    runtime_role = _validate_identifier(runtime_role)
    legacy_role = _validate_identifier(legacy_role)
    all_tables = sorted(RUNTIME_WRITE_TABLES | MIGRATION_ONLY_TABLES)
    lines = [
        "BEGIN;",
        f"ALTER DATABASE {DATABASE_NAME} OWNER TO {migration_role};",
        f"ALTER SCHEMA public OWNER TO {migration_role};",
        f"REASSIGN OWNED BY {legacy_role} TO {migration_role};",
        "REVOKE ALL ON SCHEMA public FROM PUBLIC;",
        f"GRANT USAGE ON SCHEMA public TO {runtime_role};",
        f"GRANT ALL ON SCHEMA public TO {migration_role};",
    ]
    for table in all_tables:
        lines.append(f"ALTER TABLE {table} OWNER TO {migration_role};")
    lines.extend(
        [
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
            f"{', '.join(sorted(RUNTIME_WRITE_TABLES))} TO {runtime_role};",
            f"REVOKE ALL ON TABLE "
            f"{', '.join(sorted(MIGRATION_ONLY_TABLES))} FROM {runtime_role};",
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {runtime_role};",
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {migration_role} IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {runtime_role};",
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {migration_role} IN SCHEMA public "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {runtime_role};",
        ]
    )
    for table, expression in sorted(TABLE_POLICIES.items()):
        lines.extend(
            [
                f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;",
                f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;",
                f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table};",
                f"CREATE POLICY {POLICY_NAME} ON {table} FOR ALL TO {runtime_role} "
                f"USING ({expression}) WITH CHECK ({expression});",
            ]
        )
    lines.extend(
        [
            f"ALTER ROLE {runtime_role} NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOINHERIT NOBYPASSRLS;",
            f"ALTER ROLE {migration_role} NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOINHERIT BYPASSRLS;",
            f"ALTER ROLE {legacy_role} NOLOGIN NOBYPASSRLS;",
            "COMMIT;",
            "",
        ]
    )
    return "\n".join(lines)


def render_rollback_sql() -> str:
    lines = ["BEGIN;"]
    for table in sorted(TABLE_POLICIES):
        lines.extend(
            [
                f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table};",
                f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;",
                f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;",
            ]
        )
    lines.extend(
        [
            f"REASSIGN OWNED BY {MIGRATION_ROLE} TO {LEGACY_ROLE};",
            f"ALTER SCHEMA public OWNER TO {LEGACY_ROLE};",
            f"ALTER DATABASE {DATABASE_NAME} OWNER TO {LEGACY_ROLE};",
            f"ALTER ROLE {LEGACY_ROLE} LOGIN;",
            f"ALTER ROLE {RUNTIME_ROLE} NOLOGIN;",
            "COMMIT;",
            "",
        ]
    )
    return "\n".join(lines)


def _ensure_role(
    connection: psycopg.Connection[Any],
    role_name: str,
    password: str,
    *,
    bypass_rls: bool,
) -> None:
    if len(password) < 32:
        raise ValueError("Package 9 database role passwords must be at least 32 characters")
    role_name = _validate_identifier(role_name)
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
        if cursor.fetchone() is None:
            cursor.execute(
                sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role_name))
            )
        cursor.execute(
            sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(role_name),
                sql.Literal(password),
            )
        )
        cursor.execute(
            sql.SQL("ALTER ROLE {} {}").format(
                sql.Identifier(role_name),
                sql.SQL("BYPASSRLS" if bypass_rls else "NOBYPASSRLS"),
            )
        )


def apply_database_security(
    *,
    admin_database_url: str,
    migration_password: str,
    runtime_password: str,
) -> dict[str, Any]:
    with psycopg.connect(admin_database_url, autocommit=True) as connection:
        if connection.info.dbname != DATABASE_NAME:
            raise ValueError("Package 9 can only harden the adopted runtime database")
        _ensure_role(
            connection,
            MIGRATION_ROLE,
            migration_password,
            bypass_rls=True,
        )
        _ensure_role(
            connection,
            RUNTIME_ROLE,
            runtime_password,
            bypass_rls=False,
        )
        with connection.cursor() as cursor:
            cursor.execute(render_security_sql())
    return {
        "state": "DATABASE_SECURITY_APPLIED",
        "database": DATABASE_NAME,
        "migration_role": MIGRATION_ROLE,
        "runtime_role": RUNTIME_ROLE,
        "rls_table_count": len(TABLE_POLICIES),
        "migration_only_table_count": len(MIGRATION_ONLY_TABLES),
        "runtime_bypass_rls": False,
    }


def rollback_database_security(*, admin_database_url: str) -> dict[str, Any]:
    with psycopg.connect(admin_database_url, autocommit=True) as connection:
        if connection.info.dbname != DATABASE_NAME:
            raise ValueError("Package 9 rollback database is invalid")
        with connection.cursor() as cursor:
            cursor.execute(render_rollback_sql())
    return {
        "state": "DATABASE_SECURITY_ROLLED_BACK",
        "database": DATABASE_NAME,
        "legacy_role_restored": True,
    }


def set_scope(connection: psycopg.Connection[Any], scope: DatabaseScope) -> None:
    with connection.cursor() as cursor:
        for name, value in scope.settings().items():
            cursor.execute("SELECT set_config(%s, %s, false)", (name, value))
