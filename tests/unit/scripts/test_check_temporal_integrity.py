"""Tests for scripts/check_temporal_integrity.py -- Temporal Integrity."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_temporal_integrity.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
ti = importlib.import_module("check_temporal_integrity")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_script(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(_REPO_ROOT),
    )


def _make_migration(tmp_path: Path, name: str, content: str) -> Path:
    """Create a migration file."""
    mig_dir = tmp_path / "migrations" / "versions"
    mig_dir.mkdir(parents=True, exist_ok=True)
    f = mig_dir / name
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# Migration Parsing
# ---------------------------------------------------------------------------


class TestParseMigration:
    """Test individual migration file parsing."""

    def test_parse_basic_migration(self, tmp_path: Path) -> None:
        """Should parse revision, down_revision, and functions."""
        _make_migration(
            tmp_path,
            "001_create_users.py",
            textwrap.dedent("""\
                from alembic import op
                import sqlalchemy as sa

                revision = "001_users"
                down_revision = None
                reversible_type = "full"
                rollback_artifact = "alembic downgrade -1"

                def upgrade() -> None:
                    op.create_table("users", sa.Column("id", sa.String()))

                def downgrade() -> None:
                    op.drop_table("users")
            """),
        )

        info = ti.parse_migration(tmp_path / "migrations" / "versions" / "001_create_users.py")
        assert info is not None
        assert info.revision == "001_users"
        assert info.down_revision is None
        assert info.reversible_type == "full"
        assert info.has_upgrade is True
        assert info.has_downgrade is True
        assert info.downgrade_is_empty is False
        assert "create_table" in info.upgrade_ops
        assert "drop_table" in info.downgrade_ops

    def test_parse_empty_downgrade(self, tmp_path: Path) -> None:
        """Should detect empty (pass-only) downgrade."""
        _make_migration(
            tmp_path,
            "002_bad.py",
            textwrap.dedent("""\
                revision = "002_bad"
                down_revision = "001_users"

                def upgrade() -> None:
                    pass

                def downgrade() -> None:
                    pass
            """),
        )

        info = ti.parse_migration(tmp_path / "migrations" / "versions" / "002_bad.py")
        assert info is not None
        assert info.downgrade_is_empty is True

    def test_parse_chained_revisions(self, tmp_path: Path) -> None:
        """Should parse chained down_revision."""
        _make_migration(
            tmp_path,
            "002_events.py",
            textwrap.dedent("""\
                from alembic import op
                import sqlalchemy as sa

                revision = "002_events"
                down_revision = "001_users"

                def upgrade() -> None:
                    op.create_table("events", sa.Column("id", sa.String()))

                def downgrade() -> None:
                    op.drop_table("events")
            """),
        )

        info = ti.parse_migration(tmp_path / "migrations" / "versions" / "002_events.py")
        assert info is not None
        assert info.down_revision == "001_users"


# ---------------------------------------------------------------------------
# Chain Integrity
# ---------------------------------------------------------------------------


class TestChainIntegrity:
    """Test migration chain integrity checks."""

    def test_linear_chain(self, tmp_path: Path) -> None:
        """Linear chain should produce no errors."""
        _make_migration(
            tmp_path,
            "001_a.py",
            textwrap.dedent("""\
                from alembic import op
                revision = "001_a"
                down_revision = None
                def upgrade(): op.create_table("a")
                def downgrade(): op.drop_table("a")
            """),
        )
        _make_migration(
            tmp_path,
            "002_b.py",
            textwrap.dedent("""\
                from alembic import op
                revision = "002_b"
                down_revision = "001_a"
                def upgrade(): op.create_table("b")
                def downgrade(): op.drop_table("b")
            """),
        )

        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_chain_integrity(migrations)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0

    def test_broken_chain(self, tmp_path: Path) -> None:
        """Missing link in chain should produce error."""
        _make_migration(
            tmp_path,
            "001_a.py",
            textwrap.dedent("""\
                revision = "001_a"
                down_revision = None
                def upgrade(): pass
                def downgrade(): pass
            """),
        )
        _make_migration(
            tmp_path,
            "003_c.py",
            textwrap.dedent("""\
                revision = "003_c"
                down_revision = "002_b"
                def upgrade(): pass
                def downgrade(): pass
            """),
        )

        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_chain_integrity(migrations)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) >= 1
        assert any("002_b" in e.message for e in errors)

    def test_multiple_roots(self, tmp_path: Path) -> None:
        """Multiple roots should produce error."""
        _make_migration(
            tmp_path,
            "001_a.py",
            textwrap.dedent("""\
                revision = "001_a"
                down_revision = None
                def upgrade(): pass
                def downgrade(): pass
            """),
        )
        _make_migration(
            tmp_path,
            "001_b.py",
            textwrap.dedent("""\
                revision = "001_b"
                down_revision = None
                def upgrade(): pass
                def downgrade(): pass
            """),
        )

        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_chain_integrity(migrations)
        errors = [f for f in findings if f.severity == "error"]
        assert any("Multiple root" in e.message for e in errors)

    def test_empty_dir(self, tmp_path: Path) -> None:
        """Empty migrations dir should produce warning."""
        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_chain_integrity(migrations)
        warnings = [f for f in findings if f.severity == "warning"]
        assert len(warnings) >= 1


# ---------------------------------------------------------------------------
# Rollback Coverage
# ---------------------------------------------------------------------------


class TestRollbackCoverage:
    """Test rollback coverage checks."""

    def test_full_rollback(self, tmp_path: Path) -> None:
        """Migration with proper downgrade should pass."""
        _make_migration(
            tmp_path,
            "001_a.py",
            textwrap.dedent("""\
                from alembic import op
                revision = "001_a"
                down_revision = None
                reversible_type = "full"
                rollback_artifact = "alembic downgrade -1"
                def upgrade(): op.create_table("a")
                def downgrade(): op.drop_table("a")
            """),
        )

        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_rollback_coverage(migrations)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0

    def test_missing_downgrade(self, tmp_path: Path) -> None:
        """Migration without downgrade should fail."""
        _make_migration(
            tmp_path,
            "001_bad.py",
            textwrap.dedent("""\
                revision = "001_bad"
                down_revision = None
                def upgrade():
                    pass
            """),
        )

        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_rollback_coverage(migrations)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) >= 1
        assert any("no downgrade" in e.message for e in errors)

    def test_empty_downgrade(self, tmp_path: Path) -> None:
        """Migration with pass-only downgrade should fail."""
        _make_migration(
            tmp_path,
            "001_empty.py",
            textwrap.dedent("""\
                revision = "001_empty"
                down_revision = None
                def upgrade():
                    pass
                def downgrade():
                    pass
            """),
        )

        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_rollback_coverage(migrations)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) >= 1
        assert any("empty downgrade" in e.message for e in errors)

    def test_missing_metadata(self, tmp_path: Path) -> None:
        """Migration without reversible_type should produce warning."""
        _make_migration(
            tmp_path,
            "001_no_meta.py",
            textwrap.dedent("""\
                from alembic import op
                revision = "001_no_meta"
                down_revision = None
                def upgrade(): op.create_table("t")
                def downgrade(): op.drop_table("t")
            """),
        )

        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_rollback_coverage(migrations)
        warnings = [f for f in findings if f.severity == "warning"]
        assert len(warnings) >= 1


# ---------------------------------------------------------------------------
# Symmetry
# ---------------------------------------------------------------------------


class TestSymmetry:
    """Test up/down operation symmetry checks."""

    def test_symmetric_ops(self, tmp_path: Path) -> None:
        """Symmetric create_table/drop_table should pass."""
        _make_migration(
            tmp_path,
            "001_sym.py",
            textwrap.dedent("""\
                from alembic import op
                import sqlalchemy as sa
                revision = "001_sym"
                down_revision = None
                def upgrade():
                    op.create_table("t", sa.Column("id", sa.String()))
                def downgrade():
                    op.drop_table("t")
            """),
        )

        migrations = ti.parse_all_migrations(migrations_dir=tmp_path / "migrations" / "versions")
        findings = ti.check_symmetry(migrations)
        # No warnings expected for symmetric ops
        warnings = [f for f in findings if f.severity == "warning"]
        assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


class TestReportGeneration:
    """Test report structure and status determination."""

    def test_pass_report(self) -> None:
        """No errors should produce PASS status."""
        findings = [
            ti.IntegrityFinding("chain", "info", "(all)", "Chain OK"),
        ]
        migrations: list[ti.MigrationInfo] = []
        report = ti.generate_report(findings, migrations)
        assert report["status"] == "PASS"

    def test_fail_report(self) -> None:
        """Errors should produce FAIL status."""
        findings = [
            ti.IntegrityFinding("chain", "error", "file.py", "Broken chain"),
        ]
        migrations: list[ti.MigrationInfo] = []
        report = ti.generate_report(findings, migrations)
        assert report["status"] == "FAIL"
        assert report["summary"]["errors"] == 1

    def test_warn_report(self) -> None:
        """Warnings only should produce WARN status."""
        findings = [
            ti.IntegrityFinding("rollback", "warning", "file.py", "Missing metadata"),
        ]
        migrations: list[ti.MigrationInfo] = []
        report = ti.generate_report(findings, migrations)
        assert report["status"] == "WARN"

    def test_verbose_includes_all(self) -> None:
        """Verbose mode should include all findings."""
        findings = [
            ti.IntegrityFinding("chain", "info", "(all)", "OK"),
        ]
        migrations: list[ti.MigrationInfo] = []
        report = ti.generate_report(findings, migrations, verbose=True)
        assert "all_findings" in report
        assert "migrations" in report


# ---------------------------------------------------------------------------
# Integration: script runs on real repo
# ---------------------------------------------------------------------------


class TestScriptExecution:
    """Test the script runs end-to-end on the real repository."""

    def test_json_output(self) -> None:
        """Script should produce valid JSON output."""
        result = _run_script("--json")
        assert result.returncode in (0, 1)
        data = json.loads(result.stdout)
        assert "status" in data
        assert "summary" in data
        assert "total_migrations" in data["summary"]

    def test_real_repo_chain(self) -> None:
        """Real repo should have valid migration chain."""
        result = _run_script("--json")
        data = json.loads(result.stdout)
        assert data["summary"]["total_migrations"] >= 6

    def test_real_repo_rollback(self) -> None:
        """Real repo migrations should all have non-empty downgrade()."""
        result = _run_script("--json", "--verbose")
        data = json.loads(result.stdout)
        # Check no rollback errors
        rollback_errors = [e for e in data.get("errors", []) if e["check_type"] == "rollback"]
        assert len(rollback_errors) == 0, f"Rollback errors: {rollback_errors}"
