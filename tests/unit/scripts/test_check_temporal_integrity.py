"""Tests for scripts/check_temporal_integrity.py -- Temporal Integrity."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_report_includes_mode_static(self) -> None:
        """Report should include mode field (static)."""
        findings = [ti.IntegrityFinding("chain", "info", "(all)", "OK")]
        report = ti.generate_report(findings, [], mode="static")
        assert report["mode"] == "static"
        assert "idempotency" not in report["summary"]["checks_run"]

    def test_report_includes_mode_db(self) -> None:
        """Report should include mode field (db) with idempotency in checks_run."""
        findings = [ti.IntegrityFinding("chain", "info", "(all)", "OK")]
        report = ti.generate_report(findings, [], mode="db")
        assert report["mode"] == "db"
        assert "idempotency" in report["summary"]["checks_run"]

    def test_report_checks_run_field(self) -> None:
        """Report should list all checks that were run."""
        findings = [ti.IntegrityFinding("chain", "info", "(all)", "OK")]
        report = ti.generate_report(findings, [], mode="static")
        assert "checks_run" in report["summary"]
        assert set(report["summary"]["checks_run"]) == {
            "chain",
            "rollback",
            "symmetry",
            "version",
        }


# ---------------------------------------------------------------------------
# Mode Resolution
# ---------------------------------------------------------------------------


class TestResolveMode:
    """Test mode resolution logic."""

    def test_skip_db_flag(self) -> None:
        """--skip-db should always produce static mode."""
        mode, url = ti.resolve_mode(skip_db=True)
        assert mode == "static"
        assert url is None

    def test_no_database_url(self) -> None:
        """Missing DATABASE_URL should produce static mode."""
        with patch.dict("os.environ", {}, clear=True):
            mode, url = ti.resolve_mode(skip_db=False)
        assert mode == "static"
        assert url is None

    def test_empty_database_url(self) -> None:
        """Empty DATABASE_URL should produce static mode."""
        with patch.dict("os.environ", {"DATABASE_URL": ""}):
            mode, url = ti.resolve_mode(skip_db=False)
        assert mode == "static"
        assert url is None

    def test_unreachable_database_url(self) -> None:
        """DATABASE_URL set but unreachable should produce static mode."""
        with (
            patch.dict(
                "os.environ",
                {"DATABASE_URL": "postgresql://bad:bad@localhost:59999/nonexistent"},
            ),
            patch.object(ti, "_try_connect", return_value=None),
        ):
            mode, url = ti.resolve_mode(skip_db=False)
        assert mode == "static"
        assert url is None

    def test_reachable_database_url(self) -> None:
        """DATABASE_URL set and reachable should produce db mode."""
        mock_conn = MagicMock()
        db_url = "postgresql://user:pass@localhost:5432/test"
        with (
            patch.dict("os.environ", {"DATABASE_URL": db_url}),
            patch.object(ti, "_try_connect", return_value=(MagicMock(), mock_conn)),
        ):
            mode, url = ti.resolve_mode(skip_db=False)
        assert mode == "db"
        assert url == db_url
        mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# SchemaSnapshot
# ---------------------------------------------------------------------------


class TestSchemaSnapshot:
    """Test SchemaSnapshot equality and diff."""

    def test_equal_snapshots(self) -> None:
        """Identical snapshots should be equal."""
        a = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid")],
            indexes=[("idx_users_id", "users", "CREATE INDEX ...")],
            constraints=[("users", "users_pkey", "PRIMARY KEY", "id")],
        )
        b = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid")],
            indexes=[("idx_users_id", "users", "CREATE INDEX ...")],
            constraints=[("users", "users_pkey", "PRIMARY KEY", "id")],
        )
        assert a == b

    def test_different_snapshots(self) -> None:
        """Different snapshots should not be equal."""
        a = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid")],
            indexes=[],
            constraints=[],
        )
        b = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid"), ("users", "name", "varchar")],
            indexes=[],
            constraints=[],
        )
        assert a != b

    def test_diff_shows_changes(self) -> None:
        """Diff should show added and removed items."""
        a = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid"), ("users", "old_col", "text")],
            indexes=[],
            constraints=[],
        )
        b = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid"), ("users", "new_col", "text")],
            indexes=[],
            constraints=[],
        )
        diff = a.diff(b)
        assert "columns" in diff
        assert any("old_col" in c for c in diff["columns"])
        assert any("new_col" in c for c in diff["columns"])

    def test_diff_empty_for_equal(self) -> None:
        """Equal snapshots should produce empty diff."""
        a = ti.SchemaSnapshot(columns=[("t", "c", "int")], indexes=[], constraints=[])
        b = ti.SchemaSnapshot(columns=[("t", "c", "int")], indexes=[], constraints=[])
        assert a.diff(b) == {}


# ---------------------------------------------------------------------------
# IntegrityFinding details field
# ---------------------------------------------------------------------------


class TestIntegrityFindingDetails:
    """Test IntegrityFinding details serialization."""

    def test_finding_without_details(self) -> None:
        """Finding without details should not include details key."""
        f = ti.IntegrityFinding("chain", "info", "(all)", "OK")
        d = f.to_dict()
        assert "details" not in d

    def test_finding_with_details(self) -> None:
        """Finding with details should include details key."""
        f = ti.IntegrityFinding(
            "idempotency",
            "error",
            "(schema)",
            "Drift",
            details={"columns": ["+ new_col"]},
        )
        d = f.to_dict()
        assert "details" in d
        assert d["details"] == {"columns": ["+ new_col"]}


# ---------------------------------------------------------------------------
# DB Idempotency Check (mocked)
# ---------------------------------------------------------------------------


class TestCheckDbIdempotency:
    """Test DB idempotency check with mocked subprocess and DB."""

    def test_idempotent_migrations(self) -> None:
        """Identical snapshots after up-down-up should produce info."""
        snapshot = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid")],
            indexes=[],
            constraints=[],
        )
        ok_result = MagicMock()
        ok_result.returncode = 0
        ok_result.stderr = ""

        mock_conn = MagicMock()
        mock_engine = MagicMock()

        with (
            patch.object(ti, "_run_alembic", return_value=ok_result),
            patch.object(ti, "_try_connect", return_value=(mock_engine, mock_conn)),
            patch.object(ti, "_snapshot_schema", return_value=snapshot),
        ):
            findings = ti.check_db_idempotency("postgresql://test")

        info = [f for f in findings if f.severity == "info"]
        errors = [f for f in findings if f.severity == "error"]
        assert len(info) == 1
        assert len(errors) == 0
        assert "idempotency OK" in info[0].message

    def test_non_idempotent_migrations(self) -> None:
        """Different snapshots should produce error with diff details."""
        snap_a = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid")],
            indexes=[],
            constraints=[],
        )
        snap_b = ti.SchemaSnapshot(
            columns=[("users", "id", "uuid"), ("users", "extra", "text")],
            indexes=[],
            constraints=[],
        )
        ok_result = MagicMock()
        ok_result.returncode = 0
        ok_result.stderr = ""

        mock_engine = MagicMock()

        def side_effect_connect(url: str):
            return (mock_engine, MagicMock())

        snap_call = 0

        def side_effect_snapshot(conn):
            nonlocal snap_call
            snap_call += 1
            return snap_a if snap_call == 1 else snap_b

        with (
            patch.object(ti, "_run_alembic", return_value=ok_result),
            patch.object(ti, "_try_connect", side_effect=side_effect_connect),
            patch.object(ti, "_snapshot_schema", side_effect=side_effect_snapshot),
        ):
            findings = ti.check_db_idempotency("postgresql://test")

        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 1
        assert "idempotency FAILED" in errors[0].message
        assert errors[0].details is not None
        assert "columns" in errors[0].details

    def test_alembic_downgrade_failure(self) -> None:
        """Failed alembic downgrade should produce error."""
        fail_result = MagicMock()
        fail_result.returncode = 1
        fail_result.stderr = "ERROR: cannot downgrade"

        with patch.object(ti, "_run_alembic", return_value=fail_result):
            findings = ti.check_db_idempotency("postgresql://test")

        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 1
        assert "downgrade base failed" in errors[0].message

    def test_alembic_first_upgrade_failure(self) -> None:
        """Failed first upgrade should produce error."""
        results = iter(
            [
                MagicMock(returncode=0, stderr=""),  # downgrade ok
                MagicMock(returncode=1, stderr="ERROR: upgrade failed"),  # upgrade fail
            ]
        )

        with patch.object(ti, "_run_alembic", side_effect=lambda *a, **k: next(results)):
            findings = ti.check_db_idempotency("postgresql://test")

        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 1
        assert "First upgrade head failed" in errors[0].message

    def test_connection_failure_after_first_upgrade(self) -> None:
        """Connection failure after first upgrade should produce error."""
        ok_result = MagicMock(returncode=0, stderr="")

        with (
            patch.object(ti, "_run_alembic", return_value=ok_result),
            patch.object(ti, "_try_connect", return_value=None),
        ):
            findings = ti.check_db_idempotency("postgresql://test")

        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 1
        assert "Cannot connect" in errors[0].message


# ---------------------------------------------------------------------------
# Integration: script runs on real repo
# ---------------------------------------------------------------------------


class TestScriptExecution:
    """Test the script runs end-to-end on the real repository."""

    def test_json_output(self) -> None:
        """Script should produce valid JSON output."""
        result = _run_script("--json", "--skip-db")
        assert result.returncode in (0, 1)
        data = json.loads(result.stdout)
        assert "status" in data
        assert "summary" in data
        assert "total_migrations" in data["summary"]

    def test_real_repo_chain(self) -> None:
        """Real repo should have valid migration chain."""
        result = _run_script("--json", "--skip-db")
        data = json.loads(result.stdout)
        assert data["summary"]["total_migrations"] >= 6

    def test_real_repo_rollback(self) -> None:
        """Real repo migrations should all have non-empty downgrade()."""
        result = _run_script("--json", "--verbose", "--skip-db")
        data = json.loads(result.stdout)
        # Check no rollback errors
        rollback_errors = [e for e in data.get("errors", []) if e["check_type"] == "rollback"]
        assert len(rollback_errors) == 0, f"Rollback errors: {rollback_errors}"

    def test_skip_db_produces_static_mode(self) -> None:
        """--skip-db should produce mode: static in report."""
        result = _run_script("--json", "--skip-db")
        assert result.returncode in (0, 1)
        data = json.loads(result.stdout)
        assert data["mode"] == "static"
        assert "idempotency" not in data["summary"]["checks_run"]

    def test_no_db_url_produces_static_mode(self) -> None:
        """Without DATABASE_URL, script should fall back to static mode."""
        env = {k: v for k, v in __import__("os").environ.items() if k != "DATABASE_URL"}
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(_REPO_ROOT),
            env=env,
        )
        assert result.returncode in (0, 1)
        data = json.loads(result.stdout)
        assert data["mode"] == "static"

    def test_report_has_checks_run(self) -> None:
        """Report should include checks_run list."""
        result = _run_script("--json", "--skip-db")
        data = json.loads(result.stdout)
        assert "checks_run" in data["summary"]
        assert "chain" in data["summary"]["checks_run"]
        assert "rollback" in data["summary"]["checks_run"]
        assert "symmetry" in data["summary"]["checks_run"]
        assert "version" in data["summary"]["checks_run"]
