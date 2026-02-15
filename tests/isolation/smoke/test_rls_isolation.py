"""RLS isolation smoke tests.

Phase 1 gate check: p1-rls
Validates that Row-Level Security policies are correctly enforced
for all tenant-scoped tables.

These tests verify migration DDL correctness without requiring
a running PostgreSQL instance -- they parse the migration files
and assert RLS policy declarations exist.

For live DB isolation tests, see tests/isolation/test_rls_live.py (Phase 2+).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations" / "versions"

# Tables that MUST have RLS enabled (Phase 1 scope)
PHASE1_RLS_TABLES = [
    "organizations",
    "org_members",
    "org_settings",
    "audit_events",
]


def _read_migration_sources() -> str:
    """Read all migration .py files and return concatenated source."""
    sources = []
    for f in sorted(MIGRATIONS_DIR.glob("*.py")):
        sources.append(f.read_text())
    return "\n".join(sources)


@pytest.mark.unit
class TestRLSPolicyDeclarations:
    """Verify RLS policies are declared in migration files."""

    @pytest.fixture(autouse=True)
    def _load_migrations(self) -> None:
        self.migration_source = _read_migration_sources()

    @pytest.mark.smoke
    def test_migrations_directory_exists(self) -> None:
        assert MIGRATIONS_DIR.exists(), f"Migrations directory not found: {MIGRATIONS_DIR}"

    def test_migration_files_exist(self) -> None:
        files = list(MIGRATIONS_DIR.glob("*.py"))
        assert len(files) >= 2, f"Expected at least 2 migration files, found {len(files)}"

    @pytest.mark.smoke
    @pytest.mark.parametrize("table", PHASE1_RLS_TABLES)
    def test_rls_enabled_for_table(self, table: str) -> None:
        pattern = (
            rf"ENABLE ROW LEVEL SECURITY.*{table}"
            rf"|{table}.*ENABLE ROW LEVEL SECURITY"
            rf"|_enable_rls\(['\"]?{table}"
        )
        assert re.search(
            pattern,
            self.migration_source,
            re.IGNORECASE | re.DOTALL,
        ), f"RLS not enabled for table '{table}' in migrations"

    @pytest.mark.smoke
    @pytest.mark.parametrize("table", PHASE1_RLS_TABLES)
    def test_rls_forced_for_table(self, table: str) -> None:
        pattern = (
            rf"FORCE ROW LEVEL SECURITY.*{table}"
            rf"|{table}.*FORCE ROW LEVEL SECURITY"
            rf"|_enable_rls\(['\"]?{table}"
        )
        assert re.search(
            pattern,
            self.migration_source,
            re.IGNORECASE | re.DOTALL,
        ), f"RLS not forced for table '{table}' in migrations"

    @pytest.mark.parametrize("table", PHASE1_RLS_TABLES)
    def test_isolation_policy_exists(self, table: str) -> None:
        pattern = rf"CREATE POLICY.*{table}"
        assert re.search(pattern, self.migration_source, re.IGNORECASE), (
            f"No isolation policy found for table '{table}'"
        )

    def test_org_members_policy_uses_org_id(self) -> None:
        pattern = r"org_members.*org_id.*current_setting|current_setting.*org_id.*org_members"
        assert re.search(pattern, self.migration_source, re.IGNORECASE | re.DOTALL), (
            "org_members RLS policy must filter on org_id via current_setting"
        )

    def test_audit_events_policy_uses_org_id(self) -> None:
        pattern = r"audit_events.*org_id.*current_setting|current_setting.*org_id.*audit_events"
        assert re.search(pattern, self.migration_source, re.IGNORECASE | re.DOTALL), (
            "audit_events RLS policy must filter on org_id via current_setting"
        )


@pytest.mark.unit
class TestMigrationStructure:
    """Verify migration files follow DIYU conventions."""

    def test_organization_migration_exists(self) -> None:
        files = list(MIGRATIONS_DIR.glob("*organization*"))
        assert len(files) >= 1, "No organization migration file found"

    def test_audit_events_migration_exists(self) -> None:
        files = list(MIGRATIONS_DIR.glob("*audit_events*"))
        assert len(files) >= 1, "No audit_events migration file found"

    def test_all_migrations_have_downgrade(self) -> None:
        for f in sorted(MIGRATIONS_DIR.glob("*.py")):
            source = f.read_text()
            assert "def downgrade" in source, (
                f"Migration {f.name} missing downgrade() function (rollback plan required)"
            )

    def test_all_rls_tables_have_org_id(self) -> None:
        """Tables with RLS (except organizations itself) must have org_id column."""
        source = _read_migration_sources()
        for table in ["org_members", "org_settings", "audit_events"]:
            pattern = rf"create_table.*{table}.*org_id|{table}.*Column.*org_id"
            assert re.search(pattern, source, re.IGNORECASE | re.DOTALL), (
                f"Table '{table}' missing org_id column (required for RLS)"
            )
