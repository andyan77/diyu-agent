"""Tests for scripts/check_contract_alignment.py -- Contract Alignment (6-type)."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_contract_alignment.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
ca = importlib.import_module("check_contract_alignment")


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


def _make_port_file(tmp_path: Path, name: str, content: str) -> Path:
    """Create a port file."""
    ports = tmp_path / "src" / "ports"
    ports.mkdir(parents=True, exist_ok=True)
    f = ports / name
    f.write_text(content, encoding="utf-8")
    return f


def _make_impl_file(tmp_path: Path, rel_path: str, content: str) -> Path:
    """Create an implementation file."""
    f = tmp_path / "src" / rel_path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    return f


def _make_gateway_file(tmp_path: Path, name: str, content: str) -> Path:
    """Create a gateway Python file."""
    gw = tmp_path / "src" / "gateway"
    gw.mkdir(parents=True, exist_ok=True)
    f = gw / name
    f.write_text(content, encoding="utf-8")
    return f


def _make_frontend_file(tmp_path: Path, rel_path: str, content: str) -> Path:
    """Create a frontend TypeScript file."""
    f = tmp_path / "frontend" / rel_path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    return f


def _make_migration_file(tmp_path: Path, name: str, content: str) -> Path:
    """Create a migration file."""
    mig = tmp_path / "migrations" / "versions"
    mig.mkdir(parents=True, exist_ok=True)
    f = mig / name
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# Check 1: Port Contracts
# ---------------------------------------------------------------------------


class TestPortContracts:
    """Test Port interface <-> implementation alignment."""

    def test_aligned_port(self, tmp_path: Path) -> None:
        """Port with matching implementation should be aligned."""
        _make_port_file(
            tmp_path,
            "storage_port.py",
            textwrap.dedent("""\
                from abc import ABC, abstractmethod

                class StoragePort(ABC):
                    @abstractmethod
                    async def get(self, key: str) -> str: ...
                    @abstractmethod
                    async def put(self, key: str, value: str) -> None: ...
            """),
        )
        _make_impl_file(
            tmp_path,
            "infra/cache/redis.py",
            textwrap.dedent("""\
                class RedisAdapter(StoragePort):
                    async def get(self, key: str) -> str:
                        return ""
                    async def put(self, key: str, value: str) -> None:
                        pass
            """),
        )

        findings = ca.check_port_contracts(
            ports_dir=tmp_path / "src" / "ports",
            impl_dirs=[tmp_path / "src" / "infra"],
        )
        aligned = [f for f in findings if f.status == "aligned"]
        assert len(aligned) == 1
        assert aligned[0].contract_type == "port"

    def test_drifted_port_missing_method(self, tmp_path: Path) -> None:
        """Implementation missing a Port method should be drifted."""
        _make_port_file(
            tmp_path,
            "storage_port.py",
            textwrap.dedent("""\
                from abc import ABC, abstractmethod

                class StoragePort(ABC):
                    @abstractmethod
                    async def get(self, key: str) -> str: ...
                    @abstractmethod
                    async def put(self, key: str, value: str) -> None: ...
                    @abstractmethod
                    async def delete(self, key: str) -> None: ...
            """),
        )
        _make_impl_file(
            tmp_path,
            "infra/cache/redis.py",
            textwrap.dedent("""\
                class RedisAdapter(StoragePort):
                    async def get(self, key: str) -> str:
                        return ""
                    async def put(self, key: str, value: str) -> None:
                        pass
            """),
        )

        findings = ca.check_port_contracts(
            ports_dir=tmp_path / "src" / "ports",
            impl_dirs=[tmp_path / "src" / "infra"],
        )
        drifted = [f for f in findings if f.status == "drifted"]
        assert len(drifted) == 1
        assert "delete" in drifted[0].diff_details

    def test_no_impl_no_findings(self, tmp_path: Path) -> None:
        """Port with no implementation should produce no findings."""
        _make_port_file(
            tmp_path,
            "storage_port.py",
            textwrap.dedent("""\
                from abc import ABC, abstractmethod

                class StoragePort(ABC):
                    @abstractmethod
                    async def get(self, key: str) -> str: ...
            """),
        )
        findings = ca.check_port_contracts(
            ports_dir=tmp_path / "src" / "ports",
            impl_dirs=[tmp_path / "src" / "infra"],
        )
        assert len(findings) == 0

    def test_param_mismatch(self, tmp_path: Path) -> None:
        """Implementation with different param names should be drifted."""
        _make_port_file(
            tmp_path,
            "storage_port.py",
            textwrap.dedent("""\
                from abc import ABC, abstractmethod

                class StoragePort(ABC):
                    @abstractmethod
                    async def get(self, key: str) -> str: ...
            """),
        )
        _make_impl_file(
            tmp_path,
            "infra/cache/redis.py",
            textwrap.dedent("""\
                class RedisAdapter(StoragePort):
                    async def get(self, cache_key: str) -> str:
                        return ""
            """),
        )

        findings = ca.check_port_contracts(
            ports_dir=tmp_path / "src" / "ports",
            impl_dirs=[tmp_path / "src" / "infra"],
        )
        drifted = [f for f in findings if f.status == "drifted"]
        assert len(drifted) == 1
        assert "param_diffs" in drifted[0].diff_details


# ---------------------------------------------------------------------------
# Check 4: DDL Contracts
# ---------------------------------------------------------------------------


class TestDDLContracts:
    """Test migration DDL <-> SQLAlchemy model alignment."""

    def test_aligned_ddl(self, tmp_path: Path) -> None:
        """Migration and model with same columns should be aligned."""
        _make_migration_file(
            tmp_path,
            "001_create_users.py",
            textwrap.dedent("""\
                from alembic import op
                import sqlalchemy as sa

                revision = "001_users"
                down_revision = None

                def upgrade():
                    op.create_table(
                        "users",
                        sa.Column("id", sa.String()),
                        sa.Column("email", sa.String()),
                        sa.Column("name", sa.String()),
                    )

                def downgrade():
                    op.drop_table("users")
            """),
        )
        _make_impl_file(
            tmp_path,
            "infra/models.py",
            textwrap.dedent("""\
                import sqlalchemy as sa

                class Base:
                    pass

                class User(Base):
                    __tablename__ = "users"
                    id = sa.Column(sa.String())
                    email = sa.Column(sa.String())
                    name = sa.Column(sa.String())
            """),
        )

        findings = ca.check_ddl_contracts(
            migrations_dir=tmp_path / "migrations" / "versions",
            src_dir=tmp_path / "src",
        )
        aligned = [f for f in findings if f.status == "aligned"]
        assert len(aligned) == 1

    def test_drifted_ddl(self, tmp_path: Path) -> None:
        """Migration with column not in model should be drifted."""
        _make_migration_file(
            tmp_path,
            "001_create_users.py",
            textwrap.dedent("""\
                from alembic import op
                import sqlalchemy as sa

                revision = "001_users"
                down_revision = None

                def upgrade():
                    op.create_table(
                        "users",
                        sa.Column("id", sa.String()),
                        sa.Column("email", sa.String()),
                        sa.Column("phone", sa.String()),
                    )

                def downgrade():
                    op.drop_table("users")
            """),
        )
        _make_impl_file(
            tmp_path,
            "infra/models.py",
            textwrap.dedent("""\
                import sqlalchemy as sa

                class Base:
                    pass

                class User(Base):
                    __tablename__ = "users"
                    id = sa.Column(sa.String())
                    email = sa.Column(sa.String())
            """),
        )

        findings = ca.check_ddl_contracts(
            migrations_dir=tmp_path / "migrations" / "versions",
            src_dir=tmp_path / "src",
        )
        drifted = [f for f in findings if f.status == "drifted"]
        assert len(drifted) == 1
        assert "phone" in drifted[0].diff_details

    def test_missing_model(self, tmp_path: Path) -> None:
        """Migration table with no ORM model should be missing."""
        _make_migration_file(
            tmp_path,
            "001_create_users.py",
            textwrap.dedent("""\
                from alembic import op
                import sqlalchemy as sa

                revision = "001_users"
                down_revision = None

                def upgrade():
                    op.create_table(
                        "users",
                        sa.Column("id", sa.String()),
                    )

                def downgrade():
                    op.drop_table("users")
            """),
        )
        # No models.py
        findings = ca.check_ddl_contracts(
            migrations_dir=tmp_path / "migrations" / "versions",
            src_dir=tmp_path / "src",
        )
        missing = [f for f in findings if f.status == "missing"]
        assert len(missing) == 1


# ---------------------------------------------------------------------------
# Check 2: API Contracts
# ---------------------------------------------------------------------------


class TestAPIContracts:
    """Test Backend Pydantic <-> Frontend TypeScript alignment."""

    def test_aligned_api(self, tmp_path: Path) -> None:
        """Backend model matching frontend TS type should be aligned."""
        _make_gateway_file(
            tmp_path,
            "routes.py",
            textwrap.dedent("""\
                from pydantic import BaseModel

                class UserResponse(BaseModel):
                    id: str
                    email: str
                    name: str
            """),
        )
        _make_frontend_file(
            tmp_path,
            "api/types.ts",
            textwrap.dedent("""\
                export interface UserResponse {
                    id: string;
                    email: string;
                    name: string;
                }
            """),
        )

        findings = ca.check_api_contracts(
            gateway_dir=tmp_path / "src" / "gateway",
            api_client_dir=tmp_path / "frontend" / "api",
        )
        aligned = [f for f in findings if f.status == "aligned"]
        assert len(aligned) == 1
        assert aligned[0].contract_type == "api"

    def test_drifted_api_missing_field(self, tmp_path: Path) -> None:
        """Frontend type missing a backend field should be drifted."""
        _make_gateway_file(
            tmp_path,
            "routes.py",
            textwrap.dedent("""\
                from pydantic import BaseModel

                class UserResponse(BaseModel):
                    id: str
                    email: str
                    name: str
                    avatar_url: str
            """),
        )
        _make_frontend_file(
            tmp_path,
            "api/types.ts",
            textwrap.dedent("""\
                export interface UserResponse {
                    id: string;
                    email: string;
                    name: string;
                }
            """),
        )

        findings = ca.check_api_contracts(
            gateway_dir=tmp_path / "src" / "gateway",
            api_client_dir=tmp_path / "frontend" / "api",
        )
        drifted = [f for f in findings if f.status == "drifted"]
        assert len(drifted) == 1
        assert "avatar_url" in drifted[0].diff_details


# ---------------------------------------------------------------------------
# Check 3: Event Contracts
# ---------------------------------------------------------------------------


class TestEventContracts:
    """Test event producer <-> consumer alignment."""

    def test_aligned_event(self, tmp_path: Path) -> None:
        """Event type with both producer and consumer should be aligned."""
        _make_impl_file(
            tmp_path,
            "brain/service.py",
            textwrap.dedent("""\
                class BrainService:
                    def process(self):
                        outbox.append(event_type="user_created", payload={})
            """),
        )
        _make_impl_file(
            tmp_path,
            "skill/handler.py",
            textwrap.dedent("""\
                class EventHandler:
                    def handle_event(self):
                        if event_type="user_created":
                            pass
            """),
        )

        findings = ca.check_event_contracts(src_dir=tmp_path / "src")
        aligned = [f for f in findings if f.status == "aligned"]
        assert len(aligned) == 1
        assert aligned[0].contract_type == "event"

    def test_missing_consumer(self, tmp_path: Path) -> None:
        """Event type with producer but no consumer should be missing."""
        _make_impl_file(
            tmp_path,
            "brain/service.py",
            textwrap.dedent("""\
                class BrainService:
                    def emit(self):
                        outbox.append(event_type="orphan_event", payload={})
            """),
        )

        findings = ca.check_event_contracts(src_dir=tmp_path / "src")
        missing = [f for f in findings if f.status == "missing"]
        assert len(missing) == 1
        assert "orphan_event" in missing[0].diff_details


# ---------------------------------------------------------------------------
# Check 5: ACL Contracts
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Check 6: Payload Contracts
# ---------------------------------------------------------------------------


class TestPayloadContracts:
    """Test backend response payload <-> frontend type alignment."""

    def test_aligned_payload(self, tmp_path: Path) -> None:
        """Response model referenced in frontend should be aligned."""
        _make_gateway_file(
            tmp_path,
            "api.py",
            textwrap.dedent("""\
                from pydantic import BaseModel

                class ChatResponse(BaseModel):
                    message: str
                    tokens: int
            """),
        )
        _make_frontend_file(
            tmp_path,
            "components/Chat.tsx",
            textwrap.dedent("""\
                import { ChatResponse } from '../api/types';

                function Chat() {
                    const data: ChatResponse = await fetch('/api/chat');
                }
            """),
        )

        findings = ca.check_payload_contracts(
            gateway_dir=tmp_path / "src" / "gateway",
            frontend_dir=tmp_path / "frontend",
        )
        aligned = [f for f in findings if f.status == "aligned"]
        assert len(aligned) == 1
        assert aligned[0].contract_type == "payload"

    def test_no_frontend_reference(self, tmp_path: Path) -> None:
        """Response model not referenced in frontend produces no finding."""
        _make_gateway_file(
            tmp_path,
            "api.py",
            textwrap.dedent("""\
                from pydantic import BaseModel

                class InternalResponse(BaseModel):
                    status: str
            """),
        )
        # Frontend exists but doesn't reference InternalResponse
        _make_frontend_file(
            tmp_path,
            "components/App.tsx",
            textwrap.dedent("""\
                function App() { return <div>Hello</div>; }
            """),
        )

        findings = ca.check_payload_contracts(
            gateway_dir=tmp_path / "src" / "gateway",
            frontend_dir=tmp_path / "frontend",
        )
        # InternalResponse not referenced — no finding produced (by design)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Check 5: ACL Contracts (continued)
# ---------------------------------------------------------------------------


class TestACLContracts:
    """Test RLS policies <-> Gateway RBAC alignment."""

    def test_rls_detected(self, tmp_path: Path) -> None:
        """Migration with RLS should produce ACL findings."""
        _make_migration_file(
            tmp_path,
            "001_rls.py",
            textwrap.dedent("""\
                from alembic import op
                import sqlalchemy as sa

                revision = "001_rls"
                down_revision = None

                def upgrade():
                    op.create_table("orgs", sa.Column("id", sa.String()))
                    op.execute("ALTER TABLE orgs ENABLE ROW LEVEL SECURITY")
                    op.execute(
                        "CREATE POLICY org_isolation ON orgs "
                        "USING (org_id = current_setting('app.current_org_id')::uuid)"
                    )

                def downgrade():
                    op.drop_table("orgs")
            """),
        )

        findings = ca.check_acl_contracts(
            migrations_dir=tmp_path / "migrations" / "versions",
            gateway_dir=tmp_path / "src" / "gateway",
        )
        assert len(findings) >= 1
        assert findings[0].contract_type == "acl"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


class TestReportGeneration:
    """Test report structure and status determination."""

    def test_pass_report(self) -> None:
        """All aligned findings should produce PASS status."""
        findings = [
            ca.ContractFinding("port", "a", "b", "aligned"),
            ca.ContractFinding("ddl", "c", "d", "aligned"),
        ]
        report = ca.generate_report(findings)
        assert report["status"] == "PASS"
        assert report["summary"]["aligned"] == 2

    def test_fail_report(self) -> None:
        """Drifted findings should produce FAIL status."""
        findings = [
            ca.ContractFinding("port", "a", "b", "aligned"),
            ca.ContractFinding("ddl", "c", "d", "drifted", "mismatch"),
        ]
        report = ca.generate_report(findings)
        assert report["status"] == "FAIL"
        assert report["summary"]["drifted"] == 1
        assert len(report["drifted"]) == 1

    def test_warn_report(self) -> None:
        """Missing-only findings should produce WARN status."""
        findings = [
            ca.ContractFinding("event", "a", "b", "missing", "no consumer"),
        ]
        report = ca.generate_report(findings)
        assert report["status"] == "WARN"
        assert report["summary"]["missing"] == 1

    def test_verbose_includes_all(self) -> None:
        """Verbose mode should include all findings."""
        findings = [
            ca.ContractFinding("port", "a", "b", "aligned"),
        ]
        report = ca.generate_report(findings, verbose=True)
        assert "all_findings" in report
        assert len(report["all_findings"]) == 1


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
        assert "total_contracts" in data["summary"]

    def test_verbose_output(self) -> None:
        """Script with --verbose should include all_findings."""
        result = _run_script("--json", "--verbose")
        assert result.returncode in (0, 1)
        data = json.loads(result.stdout)
        assert "all_findings" in data

    def test_covers_all_6_types(self) -> None:
        """Script should report all 6 contract types in by_type."""
        result = _run_script("--json", "--verbose")
        data = json.loads(result.stdout)
        by_type = data["summary"].get("by_type", {})
        expected_types = {"port", "api", "event", "ddl", "acl", "payload"}
        assert expected_types.issubset(set(by_type.keys())), (
            f"by_type missing types: {expected_types - set(by_type.keys())}"
        )
