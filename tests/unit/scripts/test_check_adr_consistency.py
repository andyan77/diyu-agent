"""Tests for scripts/check_adr_consistency.py -- ADR Consistency Audit."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_adr_consistency.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
adr = importlib.import_module("check_adr_consistency")


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


def _make_appendix(tmp_path: Path, rows: str) -> Path:
    """Create a minimal 08-附录.md with ADR table rows."""
    appendix = tmp_path / "docs" / "architecture" / "08-附录.md"
    appendix.parent.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent(f"""\
        # 附录

        ## 附录 B: 架构决策记录 (ADR)

        | ADR | 决策 | 版本 |
        |-----|------|------|
        {rows}
    """)
    appendix.write_text(content, encoding="utf-8")
    return appendix


# ---------------------------------------------------------------------------
# Index Parsing
# ---------------------------------------------------------------------------


class TestParseADRIndex:
    """Test parsing the ADR index table from 08-附录.md."""

    def test_parse_basic_entries(self, tmp_path: Path) -> None:
        rows = textwrap.dedent("""\
            | ADR-001 | Prompt templates belong to Skill | v2.0 |
            | ADR-002 | Knowledge uses Profile | v2.0 |
        """)
        appendix = _make_appendix(tmp_path, rows)
        index = adr.parse_adr_index(appendix)
        assert "ADR-001" in index
        assert "ADR-002" in index
        assert index["ADR-001"].adr_num == 1
        assert not index["ADR-001"].is_deprecated

    def test_parse_deprecated_entry(self, tmp_path: Path) -> None:
        rows = "| ~~ADR-003~~ | ~~\u5e9f\u5f03\uff0c\u89c1 ADR-017~~ | ~~v2.0~~ |"
        appendix = _make_appendix(tmp_path, rows)
        index = adr.parse_adr_index(appendix)
        assert "ADR-003" in index
        assert index["ADR-003"].is_deprecated

    def test_parse_amends_entry(self, tmp_path: Path) -> None:
        rows = "| **ADR-038** | **Runtime Governance (amends ADR-036)** | **v3.5** |"
        appendix = _make_appendix(tmp_path, rows)
        index = adr.parse_adr_index(appendix)
        assert "ADR-038" in index
        assert "ADR-036" in index["ADR-038"].amends

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        index = adr.parse_adr_index(tmp_path / "nonexistent.md")
        assert index == {}


# ---------------------------------------------------------------------------
# Task Card Linkage
# ---------------------------------------------------------------------------


class TestTaskCardADRRefs:
    """Test finding ADR references in task cards."""

    def test_finds_adr_refs_in_task_cards(self, tmp_path: Path) -> None:
        tc_dir = tmp_path / "task-cards"
        tc_dir.mkdir()
        (tc_dir / "brain.md").write_text("### TASK-B1-1\nImplement ADR-018 privacy boundary\n")
        refs = adr.find_task_card_adr_refs(tc_dir)
        assert "ADR-018" in refs
        assert any("brain.md" in r for r in refs["ADR-018"])

    def test_empty_dir(self, tmp_path: Path) -> None:
        refs = adr.find_task_card_adr_refs(tmp_path / "nonexistent")
        assert refs == {}


# ---------------------------------------------------------------------------
# Gate Linkage
# ---------------------------------------------------------------------------


class TestGateADRRefs:
    """Test finding ADR references in milestone-matrix gates."""

    def test_finds_adr_in_gate_check(self, tmp_path: Path) -> None:
        matrix = tmp_path / "milestone-matrix.yaml"
        matrix.write_text(
            textwrap.dedent("""\
            phases:
              phase_2:
                milestones:
                  - {id: "K2-1", layer: "Knowledge", summary: "FK Registry (ADR-024)"}
                exit_criteria:
                  hard:
                    - id: "p2-fk-registry"
                      description: "FK linkage per ADR-024"
                      check: "uv run pytest tests/ -k fk"
        """),
            encoding="utf-8",
        )
        refs = adr.find_gate_adr_refs(matrix)
        assert "ADR-024" in refs
        assert "p2-fk-registry" in refs["ADR-024"]

    def test_finds_adr_in_milestone_summary(self, tmp_path: Path) -> None:
        matrix = tmp_path / "milestone-matrix.yaml"
        matrix.write_text(
            textwrap.dedent("""\
            phases:
              phase_0:
                milestones:
                  - id: "MM0-6"
                    layer: "Multimodal"
                    summary: "LLMCallPort content_parts (ADR-046)"
                exit_criteria: {}
        """),
            encoding="utf-8",
        )
        refs = adr.find_gate_adr_refs(matrix)
        assert "ADR-046" in refs


# ---------------------------------------------------------------------------
# Test File Linkage
# ---------------------------------------------------------------------------


class TestTestADRRefs:
    """Test finding ADR references in test files."""

    def test_finds_adr_in_test(self, tmp_path: Path) -> None:
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_privacy.py").write_text('"""Verifies ADR-018 privacy boundary."""\n')
        refs = adr.find_test_adr_refs(test_dir)
        assert "ADR-018" in refs


# ---------------------------------------------------------------------------
# Code Violations
# ---------------------------------------------------------------------------


class TestCodeViolations:
    """Test code pattern violation detection."""

    def test_detects_knowledge_importing_memory(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "knowledge"
        src.mkdir(parents=True)
        (src / "bad.py").write_text("from src.memory.core import MemoryCore\n")
        violations = adr.check_code_violations(tmp_path / "src")
        assert "ADR-018" in violations
        assert any("Knowledge layer imports src.memory" in v for v in violations["ADR-018"])

    def test_no_violations_clean_code(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "knowledge"
        src.mkdir(parents=True)
        (src / "clean.py").write_text("from src.ports.knowledge import KnowledgePort\n")
        violations = adr.check_code_violations(tmp_path / "src")
        assert "ADR-018" not in violations


# ---------------------------------------------------------------------------
# Full Audit
# ---------------------------------------------------------------------------


class TestRunAudit:
    """Test the full audit engine."""

    def test_detects_zero_gate_coverage(self) -> None:
        index = {
            "ADR-005": adr.ADREntry("ADR-005", 5, "Knowledge inheritance", "v2.0"),
        }
        findings, _results = adr.run_audit(
            index=index,
            standalone_files={},
            references=[],
            task_card_refs={},
            gate_refs={},
            test_refs={},
            code_violations={},
        )
        zero_gate = [f for f in findings if f.category == "zero_gate_coverage"]
        assert any("ADR-005" in f.message for f in zero_gate)

    def test_deprecated_skips_gate_check(self) -> None:
        index = {
            "ADR-003": adr.ADREntry(
                "ADR-003",
                3,
                "Deprecated",
                "v2.0",
                is_deprecated=True,
                superseded_by="ADR-017",
            ),
        }
        findings, _results = adr.run_audit(
            index=index,
            standalone_files={},
            references=[],
            task_card_refs={},
            gate_refs={},
            test_refs={},
            code_violations={},
        )
        zero_gate = [
            f for f in findings if f.category == "zero_gate_coverage" and "ADR-003" in f.message
        ]
        assert len(zero_gate) == 0

    def test_detects_orphaned_adr(self) -> None:
        """ADR in review docs only (not in index) should be flagged orphaned."""
        index = {
            "ADR-039": adr.ADREntry("ADR-039", 39, "Data lifecycle", "v3.5"),
            "ADR-042": adr.ADREntry("ADR-042", 42, "CE Optimization", "v3.5.1"),
        }
        # ADR-040 only referenced in reviews
        references = [
            adr.ADRReference("ADR-040", "docs/reviews/memory-review.md", 10, "ADR-040"),
        ]
        findings, _results = adr.run_audit(
            index=index,
            standalone_files={},
            references=references,
            task_card_refs={},
            gate_refs={},
            test_refs={},
            code_violations={},
        )
        orphaned = [f for f in findings if f.category == "orphaned"]
        assert any("ADR-040" in f.message for f in orphaned)


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """Test report structure."""

    def test_report_has_required_summary_fields(self) -> None:
        findings = [
            adr.Finding("warning", "zero_gate_coverage", "ADR-005 no gate"),
            adr.Finding("warning", "orphaned", "ADR-040 orphaned"),
            adr.Finding("error", "code_violation", "ADR-018 violation"),
        ]
        adr_results = [
            adr.ADRAuditResult("ADR-005", "indexed", "08-附录.md"),
        ]
        report = adr.generate_report(
            index={},
            standalone_files={},
            references=[],
            findings=findings,
            adr_results=adr_results,
        )
        assert "zero_gate_coverage" in report["summary"]
        assert "orphaned_adrs" in report["summary"]
        assert "code_violations" in report["summary"]
        assert report["summary"]["zero_gate_coverage"] == 1
        assert report["summary"]["orphaned_adrs"] == 1
        assert report["summary"]["code_violations"] == 1

    def test_verbose_includes_adr_results(self) -> None:
        adr_results = [
            adr.ADRAuditResult(
                "ADR-018",
                "indexed",
                "08-附录.md",
                task_card_refs=["task-cards/brain.md"],
                gate_refs=["p2-privacy"],
                test_refs=["tests/test_privacy.py"],
            ),
        ]
        report = adr.generate_report(
            index={},
            standalone_files={},
            references=[],
            findings=[],
            adr_results=adr_results,
            verbose=True,
        )
        assert "adr_results" in report
        r = report["adr_results"][0]
        assert r["task_card_refs"] == ["task-cards/brain.md"]
        assert r["gate_refs"] == ["p2-privacy"]
        assert r["test_refs"] == ["tests/test_privacy.py"]


# ---------------------------------------------------------------------------
# Integration: actual codebase (validation fixtures from plan)
# ---------------------------------------------------------------------------


class TestValidationFixtures:
    """Validate against baseline codebase per guardian-system-completion-plan-v1.0.md."""

    def test_script_runs_json_mode(self) -> None:
        """Script produces valid JSON output."""
        result = _run_script("--json")
        data = json.loads(result.stdout)
        assert "status" in data
        assert "findings" in data

    def test_detects_adr040_041_orphaned(self) -> None:
        """ADR-040/041 must be flagged as orphaned (plan line 152)."""
        result = _run_script("--json")
        data = json.loads(result.stdout)
        orphaned = [f for f in data["findings"] if f["category"] == "orphaned"]
        orphaned_ids = [f["details"]["adr_id"] for f in orphaned]
        assert "ADR-040" in orphaned_ids, f"ADR-040 not found in orphaned: {orphaned_ids}"
        assert "ADR-041" in orphaned_ids, f"ADR-041 not found in orphaned: {orphaned_ids}"

    def test_detects_adr005_016_zero_gate(self) -> None:
        """ADR-005~016 must be flagged as zero-gate-coverage (plan line 152/335)."""
        result = _run_script("--json")
        data = json.loads(result.stdout)
        zero_gate_ids = [
            f["details"]["adr_id"]
            for f in data["findings"]
            if f["category"] == "zero_gate_coverage"
        ]
        for i in range(5, 17):
            adr_id = f"ADR-{i:03d}"
            assert adr_id in zero_gate_ids, f"{adr_id} not flagged as zero-gate-coverage"
