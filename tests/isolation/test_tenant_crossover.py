"""OS3-6: Tenant isolation runtime verification (p3-tenant-isolation-runtime).

Tests that cross-org queries are blocked by RLS policies.
Validates:
- cross_org_select_blocked
- rls_scoped_join
- concurrent_org_isolation

Source: production-delivery-gate-plan-v1.0.md:417

These tests verify RLS correctness via static analysis of migration DDL
(no live DB required). For live-DB crossover tests, run with --integration flag.

Test path: `uv run pytest tests/isolation/test_tenant_crossover.py -q`
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.shared.rls_tables import PHASE_1_RLS_TABLES

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / ".." / "migrations" / "versions"
MIGRATIONS_DIR = MIGRATIONS_DIR.resolve()

# All tenant-scoped tables that MUST enforce isolation
ALL_RLS_TABLES = PHASE_1_RLS_TABLES


def _read_all_migrations() -> str:
    """Concatenate all migration source files."""
    sources = []
    for f in sorted(MIGRATIONS_DIR.glob("*.py")):
        sources.append(f.read_text())
    return "\n".join(sources)


@pytest.mark.unit
class TestCrossOrgSelectBlocked:
    """Verify RLS policies prevent cross-org SELECT queries.

    Each tenant-scoped table must have:
    1. RLS enabled (ENABLE ROW LEVEL SECURITY)
    2. RLS forced (FORCE ROW LEVEL SECURITY -- prevents superuser bypass)
    3. A policy filtering on org_id via current_setting
    """

    @pytest.fixture(autouse=True)
    def _load_migrations(self) -> None:
        self.source = _read_all_migrations()

    @pytest.mark.parametrize("table", ALL_RLS_TABLES)
    def test_rls_enabled(self, table: str) -> None:
        """RLS must be enabled for each tenant table."""
        pattern = (
            rf"ENABLE ROW LEVEL SECURITY.*{table}"
            rf"|{table}.*ENABLE ROW LEVEL SECURITY"
            rf"|_enable_rls\(['\"]?{table}"
        )
        assert re.search(pattern, self.source, re.IGNORECASE | re.DOTALL), (
            f"RLS not enabled for '{table}': cross-org SELECT would leak data"
        )

    @pytest.mark.parametrize("table", ALL_RLS_TABLES)
    def test_rls_forced(self, table: str) -> None:
        """RLS must be forced (prevents superuser/owner bypass)."""
        pattern = (
            rf"FORCE ROW LEVEL SECURITY.*{table}"
            rf"|{table}.*FORCE ROW LEVEL SECURITY"
            rf"|_enable_rls\(['\"]?{table}"
        )
        assert re.search(pattern, self.source, re.IGNORECASE | re.DOTALL), (
            f"RLS not forced for '{table}': table owner could bypass isolation"
        )

    @pytest.mark.parametrize("table", ALL_RLS_TABLES)
    def test_isolation_policy_exists(self, table: str) -> None:
        """Each table must have a CREATE POLICY for row isolation."""
        pattern = rf"CREATE POLICY.*{table}"
        assert re.search(pattern, self.source, re.IGNORECASE), (
            f"No isolation policy for '{table}': cross-org access unprotected"
        )


@pytest.mark.unit
class TestRLSScopedJoin:
    """Verify that tables with foreign key joins also enforce RLS.

    When tables are joined (e.g., org_members JOIN audit_events),
    both sides must have RLS, otherwise the join leaks data.
    """

    @pytest.fixture(autouse=True)
    def _load_migrations(self) -> None:
        self.source = _read_all_migrations()

    def test_org_members_has_org_id_policy(self) -> None:
        """org_members must filter on org_id."""
        pattern = (
            r"org_members.*org_id.*current_setting"
            r"|current_setting.*org_id.*org_members"
        )
        assert re.search(pattern, self.source, re.IGNORECASE | re.DOTALL), (
            "org_members RLS policy must scope by org_id via current_setting"
        )

    def test_audit_events_has_org_id_policy(self) -> None:
        """audit_events must filter on org_id."""
        pattern = (
            r"audit_events.*org_id.*current_setting"
            r"|current_setting.*org_id.*audit_events"
        )
        assert re.search(pattern, self.source, re.IGNORECASE | re.DOTALL), (
            "audit_events RLS policy must scope by org_id via current_setting"
        )

    def test_all_rls_tables_have_org_id_column(self) -> None:
        """Every RLS table (except organizations) needs an org_id column."""
        tables_needing_org_id = [t for t in ALL_RLS_TABLES if t != "organizations"]
        for table in tables_needing_org_id:
            pattern = rf"create_table.*{table}.*org_id|{table}.*Column.*org_id"
            assert re.search(pattern, self.source, re.IGNORECASE | re.DOTALL), (
                f"Table '{table}' missing org_id column (required for RLS scoped joins)"
            )


@pytest.mark.unit
class TestConcurrentOrgIsolation:
    """Verify that RLS policies use session-level org_id, not query params.

    current_setting('app.current_org_id') ensures isolation is
    enforced at the connection level, preventing concurrent request
    cross-contamination.
    """

    @pytest.fixture(autouse=True)
    def _load_migrations(self) -> None:
        self.source = _read_all_migrations()

    def test_uses_current_setting_not_parameter(self) -> None:
        """Policies must use current_setting(), not query parameters."""
        # current_setting is the PostgreSQL mechanism for session-level variables
        assert re.search(
            r"current_setting\s*\(\s*['\"]app\.current_org_id['\"]",
            self.source,
            re.IGNORECASE,
        ), (
            "RLS policies must use current_setting('app.current_org_id') "
            "for session-level isolation, not query parameters"
        )

    def test_no_hardcoded_org_ids_in_policies(self) -> None:
        """Policies must not contain hardcoded org UUIDs."""
        # Find CREATE POLICY statements and check they don't contain UUID literals
        policies = re.findall(
            r"CREATE POLICY.*?;",
            self.source,
            re.IGNORECASE | re.DOTALL,
        )
        uuid_pattern = re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            re.IGNORECASE,
        )
        for policy in policies:
            assert not uuid_pattern.search(policy), (
                f"Hardcoded UUID found in RLS policy: {policy[:100]}..."
            )

    @pytest.mark.parametrize("table", ALL_RLS_TABLES)
    def test_policy_count_at_least_one(self, table: str) -> None:
        """Each RLS table must have at least one policy."""
        matches = re.findall(
            rf"CREATE POLICY\s+\S+\s+ON\s+{table}",
            self.source,
            re.IGNORECASE,
        )
        # Also count the _enable_rls helper pattern
        helper_matches = re.findall(
            rf"_enable_rls\(['\"]?{table}",
            self.source,
            re.IGNORECASE,
        )
        total = len(matches) + len(helper_matches)
        assert total >= 1, (
            f"Table '{table}' has no isolation policies — concurrent org access not prevented"
        )
