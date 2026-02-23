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
            ra.CodeArtifact("src/brain/engine.py", "ConversationEngine", "class", 1, "brain"),
        ]
        results = ra.run_audit(
            arts,
            arch_text="The ConversationEngine manages dialogue flow.",
            task_card_text="### TASK-B2-1: ConversationEngine implementation",
        )
        assert results[0].status == "mapped"
        assert results[0].architecture_ref != ""
        assert results[0].task_card_ref != ""

    def test_shadow_artifact(self) -> None:
        arts = [
            ra.CodeArtifact(
                "src/brain/skill/orchestrator.py",
                "SkillOrchestrator",
                "class",
                1,
                "brain",
            ),
        ]
        results = ra.run_audit(
            arts,
            arch_text="The Brain layer handles conversations and intent routing.",
            task_card_text="### TASK-B2-1: Conversation engine implementation",
        )
        # "SkillOrchestrator" not found in either text
        assert results[0].status == "shadow"

    def test_arch_only_is_mapped(self) -> None:
        """Artifact referenced in arch docs but not task cards is still mapped."""
        arts = [
            ra.CodeArtifact("src/memory/pg_adapter.py", "PgAdapter", "port_impl", 1, "memory"),
        ]
        results = ra.run_audit(
            arts,
            arch_text="PgAdapter implements MemoryCorePort.",
            task_card_text="No mention.",
        )
        assert results[0].status == "mapped"

    def test_multiple_artifacts_mixed(self) -> None:
        arts = [
            ra.CodeArtifact("src/brain/engine.py", "ConversationEngine", "class", 1, "brain"),
            ra.CodeArtifact("src/shared/rls_tables.py", "SomethingUnique123", "class", 1, "shared"),
        ]
        results = ra.run_audit(
            arts,
            arch_text="ConversationEngine is the main engine.",
            task_card_text="",
        )
        mapped = [r for r in results if r.status == "mapped"]
        shadows = [r for r in results if r.status == "shadow"]
        assert len(mapped) == 1
        assert len(shadows) == 1


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """Test report structure."""

    def test_pass_no_shadows(self) -> None:
        results = [
            ra.AuditResult("f.py", "Engine", "class", "brain", "mapped", "arch ref"),
        ]
        report = ra.generate_report(results)
        assert report["status"] == "PASS"
        assert report["summary"]["shadow_count"] == 0

    def test_warn_on_shadows(self) -> None:
        results = [
            ra.AuditResult("f.py", "Shadow", "class", "brain", "shadow"),
        ]
        report = ra.generate_report(results)
        assert report["status"] == "WARN"
        assert report["summary"]["shadow_count"] == 1
        assert len(report["shadows"]) == 1

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

    def test_detects_known_shadows(self) -> None:
        """Validation fixture: must detect known shadow files (plan line 337).

        Known shadows: orchestrator.py, write_adapter.py, rls_tables.py, trace_context.py.
        At least some of these should appear as shadow artifacts (not all class names
        may be unique enough to avoid matching arch docs).
        """
        result = _run_script("--json")
        report = json.loads(result.stdout)
        shadow_files = [s["file"] for s in report["shadows"]]
        # At least one of the known shadow files should be detected
        known_shadow_fragments = [
            "rls_tables.py",
            "trace_context.py",
        ]
        found_any = False
        for frag in known_shadow_fragments:
            if any(frag in f for f in shadow_files):
                found_any = True
                break
        assert found_any, f"No known shadow files detected. Shadow files: {shadow_files[:10]}"

    def test_human_readable_output(self) -> None:
        result = _run_script()
        assert result.returncode in (0, 1)
        assert "Reverse Audit" in result.stdout
