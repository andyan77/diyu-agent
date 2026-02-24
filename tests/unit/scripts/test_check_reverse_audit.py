"""Tests for scripts/check_reverse_audit.py -- Reverse Audit (Code -> Design)."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_reverse_audit.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
ra = importlib.import_module("check_reverse_audit")


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


def _make_src(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a src/ directory with Python files."""
    src = tmp_path / "src"
    for rel, content in files.items():
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    return src


def _make_docs(tmp_path: Path, content: str) -> Path:
    """Create architecture docs."""
    docs = tmp_path / "docs" / "architecture"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "01-Brain.md").write_text(content, encoding="utf-8")
    return docs


def _make_task_cards(tmp_path: Path, content: str) -> Path:
    """Create task card docs."""
    tc = tmp_path / "docs" / "task-cards"
    tc.mkdir(parents=True, exist_ok=True)
    (tc / "brain.md").write_text(content, encoding="utf-8")
    return tc


# ---------------------------------------------------------------------------
# AST Scanning
# ---------------------------------------------------------------------------


class TestScanFile:
    """Test AST-based code artifact scanning."""

    def test_detects_class(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "brain/engine.py": textwrap.dedent("""\
                class ConversationEngine:
                    def run(self): pass
            """),
            },
        )
        arts = ra.scan_file(src / "brain" / "engine.py", src_dir=src)
        assert len(arts) == 1
        assert arts[0].name == "ConversationEngine"
        assert arts[0].artifact_type == "class"
        assert arts[0].layer == "brain"

    def test_detects_port_impl(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "memory/pg_adapter.py": textwrap.dedent("""\
                from abc import ABC
                class PgAdapter(MemoryCorePort):
                    def store(self): pass
            """),
            },
        )
        arts = ra.scan_file(src / "memory" / "pg_adapter.py", src_dir=src)
        names = [a.name for a in arts]
        assert "PgAdapter" in names
        port_art = next(a for a in arts if a.name == "PgAdapter")
        assert port_art.artifact_type == "port_impl"

    def test_detects_router_decorator(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "gateway/api/auth.py": textwrap.dedent("""\
                from fastapi import APIRouter
                router = APIRouter()
                @router.post("/login")
                async def login(): pass
            """),
            },
        )
        arts = ra.scan_file(src / "gateway" / "api" / "auth.py", src_dir=src)
        routers = [a for a in arts if a.artifact_type == "router"]
        assert len(routers) == 1
        assert routers[0].name == "login"

    def test_detects_model_class(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "infra/models.py": textwrap.dedent("""\
                class Organization(Base):
                    __tablename__ = "organizations"
            """),
            },
        )
        arts = ra.scan_file(src / "infra" / "models.py", src_dir=src)
        models = [a for a in arts if a.artifact_type == "model"]
        assert len(models) == 1
        assert models[0].name == "Organization"

    def test_detects_top_level_function(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "shared/rls_tables.py": textwrap.dedent("""\
                PHASE_1_TABLES = ["organizations"]
                def get_rls_tables(phase="all"):
                    return PHASE_1_TABLES
            """),
            },
        )
        arts = ra.scan_file(src / "shared" / "rls_tables.py", src_dir=src)
        funcs = [a for a in arts if a.artifact_type == "function"]
        assert len(funcs) == 1
        assert funcs[0].name == "get_rls_tables"

    def test_skips_private_functions(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "shared/helpers.py": textwrap.dedent("""\
                def _internal(): pass
                def public_api(): pass
            """),
            },
        )
        arts = ra.scan_file(src / "shared" / "helpers.py", src_dir=src)
        names = [a.name for a in arts]
        assert "public_api" in names
        assert "_internal" not in names

    def test_handles_syntax_error(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "brain/broken.py": "def broken(:\n  pass\n",
            },
        )
        arts = ra.scan_file(src / "brain" / "broken.py", src_dir=src)
        assert arts == []

    def test_skips_init_files(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "brain/__init__.py": "class Brain: pass\n",
                "brain/engine.py": "class Engine: pass\n",
            },
        )
        arts = ra.scan_src(src_dir=src)
        names = [a.name for a in arts]
        assert "Engine" in names
        assert "Brain" not in names  # __init__.py skipped


class TestScanSrc:
    """Test full src/ scanning."""

    def test_scans_multiple_layers(self, tmp_path: Path) -> None:
        src = _make_src(
            tmp_path,
            {
                "brain/engine.py": "class BrainEngine: pass\n",
                "knowledge/resolver.py": "class Resolver: pass\n",
                "shared/trace.py": "class TraceContext: pass\n",
            },
        )
        arts = ra.scan_src(src_dir=src)
        layers = {a.layer for a in arts}
        assert "brain" in layers
        assert "knowledge" in layers
        assert "shared" in layers

    def test_empty_src(self, tmp_path: Path) -> None:
        arts = ra.scan_src(src_dir=tmp_path / "nonexistent")
        assert arts == []


# ---------------------------------------------------------------------------
# Audit Engine
# ---------------------------------------------------------------------------


class TestRunAudit:
    """Test reverse audit cross-referencing."""

    def test_mapped_artifact(self) -> None:
        arts = [
            ra.CodeArtifact(
                "src/brain/engine.py",
                "ConversationEngine",
                "class",
                1,
                "brain",
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="The ConversationEngine manages dialogue flow.",
            task_card_text="### TASK-B2-1: ConversationEngine implementation",
        )
        code_results = [r for r in results if r.status != "dead"]
        assert code_results[0].status == "mapped"
        assert code_results[0].architecture_ref != ""
        assert code_results[0].task_card_ref != ""

    def test_shadow_artifact(self) -> None:
        arts = [
            ra.CodeArtifact(
                "src/brain/skill/orchestrator.py",
                "Xyzzy",
                "class",
                1,
                "brain",
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="The Brain layer handles conversations.",
            task_card_text="### TASK-B2-1: Conversation engine",
        )
        code_results = [r for r in results if r.status != "dead"]
        assert code_results[0].status == "shadow"

    def test_arch_only_is_mapped(self) -> None:
        """Artifact referenced in arch docs but not task cards."""
        arts = [
            ra.CodeArtifact(
                "src/memory/pg_adapter.py",
                "PgAdapter",
                "port_impl",
                1,
                "memory",
                bases=["MemoryCorePort"],
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="PgAdapter implements MemoryCorePort.",
            task_card_text="No mention.",
        )
        code_results = [r for r in results if r.status != "dead"]
        assert code_results[0].status == "mapped"

    def test_multiple_artifacts_mixed(self) -> None:
        arts = [
            ra.CodeArtifact(
                "src/brain/engine.py",
                "ConversationEngine",
                "class",
                1,
                "brain",
            ),
            ra.CodeArtifact(
                "src/shared/rls_tables.py",
                "SomethingUnique123",
                "class",
                1,
                "shared",
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="ConversationEngine is the main engine.",
            task_card_text="",
        )
        code_results = [r for r in results if r.status != "dead"]
        mapped = [r for r in code_results if r.status == "mapped"]
        shadows = [r for r in code_results if r.status == "shadow"]
        assert len(mapped) == 1
        assert len(shadows) == 1

    def test_drift_detected(self, tmp_path: Path) -> None:
        """Port impl missing required methods is drift."""
        src = _make_src(
            tmp_path,
            {
                "ports/memory_port.py": textwrap.dedent("""\
                from abc import ABC, abstractmethod
                class MemoryPort(ABC):
                    @abstractmethod
                    def read(self): pass
                    @abstractmethod
                    def write(self): pass
            """),
                "memory/adapter.py": textwrap.dedent("""\
                class MyAdapter(MemoryPort):
                    def read(self): return []
            """),
            },
        )
        contracts = ra.build_port_contracts(src_dir=src)
        arts = [
            ra.CodeArtifact(
                str(src / "memory/adapter.py"),
                "MyAdapter",
                "port_impl",
                1,
                "memory",
                bases=["MemoryPort"],
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="MyAdapter implements MemoryPort.",
            port_contracts=contracts,
        )
        code_results = [r for r in results if r.status != "dead"]
        assert code_results[0].status == "drift"
        assert "write" in code_results[0].drift_detail

    def test_no_drift_when_all_methods_present(self, tmp_path: Path) -> None:
        """Complete Port implementation is not drift."""
        src = _make_src(
            tmp_path,
            {
                "ports/storage_port.py": textwrap.dedent("""\
                from abc import ABC, abstractmethod
                class StoragePort(ABC):
                    @abstractmethod
                    def save(self): pass
            """),
                "infra/s3.py": textwrap.dedent("""\
                class S3Adapter(StoragePort):
                    def save(self): return True
            """),
            },
        )
        contracts = ra.build_port_contracts(src_dir=src)
        arts = [
            ra.CodeArtifact(
                str(src / "infra/s3.py"),
                "S3Adapter",
                "port_impl",
                1,
                "infra",
                bases=["StoragePort"],
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="S3Adapter implements StoragePort.",
            port_contracts=contracts,
        )
        code_results = [r for r in results if r.status != "dead"]
        assert code_results[0].status == "mapped"

    def test_dead_reference_detected(self) -> None:
        """Arch doc mentions artifact not present in code."""
        arts = [
            ra.CodeArtifact(
                "src/brain/engine.py",
                "RealEngine",
                "class",
                1,
                "brain",
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="The FooBarHandler processes incoming requests.",
        )
        dead = [r for r in results if r.status == "dead"]
        dead_names = [d.name for d in dead]
        assert "FooBarHandler" in dead_names

    def test_no_dead_when_artifact_exists(self) -> None:
        """Arch doc references that exist in code are not dead."""
        arts = [
            ra.CodeArtifact(
                "src/brain/engine.py",
                "ConversationEngine",
                "class",
                1,
                "brain",
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="ConversationEngine manages dialogue.",
        )
        dead = [r for r in results if r.status == "dead"]
        dead_names = [d.name for d in dead]
        assert "ConversationEngine" not in dead_names


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """Test report structure."""

    def test_pass_no_findings(self) -> None:
        results = [
            ra.AuditResult("f.py", "Engine", "class", "brain", "mapped", "ref"),
        ]
        report = ra.generate_report(results)
        assert report["status"] == "PASS"
        assert report["summary"]["shadow_count"] == 0
        assert report["summary"]["drift_count"] == 0
        assert report["summary"]["dead_count"] == 0

    def test_warn_on_shadows(self) -> None:
        results = [
            ra.AuditResult("f.py", "Shadow", "class", "brain", "shadow"),
        ]
        report = ra.generate_report(results)
        assert report["status"] == "WARN"
        assert report["summary"]["shadow_count"] == 1
        assert len(report["shadows"]) == 1

    def test_fail_on_drift(self) -> None:
        results = [
            ra.AuditResult(
                "f.py",
                "Adapter",
                "port_impl",
                "memory",
                "drift",
                drift_detail="Missing methods from FooPort: bar",
            ),
        ]
        report = ra.generate_report(results)
        assert report["status"] == "FAIL"
        assert report["summary"]["drift_count"] == 1
        assert len(report["drifted"]) == 1

    def test_fail_on_dead(self) -> None:
        results = [
            ra.AuditResult(
                "(not found)",
                "GhostHandler",
                "unknown",
                "unknown",
                "dead",
                "ref in arch",
            ),
        ]
        report = ra.generate_report(results)
        assert report["status"] == "FAIL"
        assert report["summary"]["dead_count"] == 1
        assert len(report["dead"]) == 1

    def test_verbose_includes_all(self) -> None:
        results = [
            ra.AuditResult("f.py", "Engine", "class", "brain", "mapped"),
            ra.AuditResult("g.py", "Shadow", "class", "shared", "shadow"),
        ]
        report = ra.generate_report(results, verbose=True)
        assert "all_results" in report
        assert len(report["all_results"]) == 2

    def test_shadow_by_layer(self) -> None:
        results = [
            ra.AuditResult("f.py", "A", "class", "brain", "shadow"),
            ra.AuditResult("g.py", "B", "class", "brain", "shadow"),
            ra.AuditResult("h.py", "C", "class", "shared", "shadow"),
        ]
        report = ra.generate_report(results)
        assert report["summary"]["shadow_by_layer"]["brain"] == 2
        assert report["summary"]["shadow_by_layer"]["shared"] == 1


# ---------------------------------------------------------------------------
# Integration: Script execution
# ---------------------------------------------------------------------------


class TestScriptExecution:
    """Integration tests running the script as subprocess."""

    def test_json_output_valid(self) -> None:
        result = _run_script("--json")
        assert result.returncode in (0, 1), f"Exit {result.returncode}: {result.stderr}"
        report = json.loads(result.stdout)
        assert "status" in report
        assert "summary" in report
        assert "shadows" in report

    def test_summary_has_required_fields(self) -> None:
        result = _run_script("--json")
        report = json.loads(result.stdout)
        s = report["summary"]
        assert "total_artifacts" in s
        assert "mapped_count" in s
        assert "shadow_count" in s
        assert "drift_count" in s
        assert "dead_count" in s

    def test_report_has_all_sections(self) -> None:
        result = _run_script("--json")
        report = json.loads(result.stdout)
        assert "shadows" in report
        assert "drifted" in report
        assert "dead" in report

    def test_detects_known_shadows(self) -> None:
        """Validation fixture: must detect known shadow baseline set.

        Known shadow baseline (plan §C2):
          - src/brain/skill/orchestrator.py
          - src/knowledge/api/write_adapter.py
          - src/shared/rls_tables.py
          - src/shared/trace_context.py

        Must detect all 4 known shadow files at baseline commit.
        """
        result = _run_script("--json")
        report = json.loads(result.stdout)
        shadow_files = [s["file"] for s in report["shadows"]]
        known_shadow_fragments = [
            "orchestrator.py",
            "write_adapter.py",
            "rls_tables.py",
            "trace_context.py",
        ]
        missing = [
            frag for frag in known_shadow_fragments if not any(frag in f for f in shadow_files)
        ]
        assert not missing, (
            f"Known shadow files not detected: {missing}. "
            f"Shadow files (first 15): {shadow_files[:15]}"
        )

    def test_human_readable_output(self) -> None:
        result = _run_script()
        assert result.returncode in (0, 1)
        assert "Reverse Audit" in result.stdout
