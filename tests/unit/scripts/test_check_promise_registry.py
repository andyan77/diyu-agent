"""Tests for scripts/check_promise_registry.py -- Promise Traceability Audit."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_promise_registry.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
pr = importlib.import_module("check_promise_registry")


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


def _make_arch_doc(tmp_path: Path, content: str) -> Path:
    """Create a minimal architecture doc."""
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    doc = arch_dir / "01-Brain.md"
    doc.write_text(content, encoding="utf-8")
    return arch_dir


# ---------------------------------------------------------------------------
# Architecture Promise Parsing
# ---------------------------------------------------------------------------


class TestParseArchitecturePromises:
    """Test extraction of promises from architecture docs."""

    def test_extracts_section_headers(self, tmp_path: Path) -> None:
        arch_dir = _make_arch_doc(
            tmp_path,
            textwrap.dedent("""\
            ## 1.0 Overview
            Some text here.

            ## 2.1 Memory Engine
            Phase 2 implementation details.

            ### 3.1 MemoryCorePort
            LAW constraint: no bypass.
        """),
        )
        promises = pr.parse_architecture_promises(arch_dir)
        ids = [p.promise_id for p in promises]
        assert "01-§1.0" in ids
        assert "01-§2.1" in ids
        assert "01-§3.1" in ids

    def test_extracts_phase_markers(self, tmp_path: Path) -> None:
        arch_dir = _make_arch_doc(
            tmp_path,
            textwrap.dedent("""\
            ## 2.1 Memory Engine
            This is for Phase 2. See ADR-018.
        """),
        )
        promises = pr.parse_architecture_promises(arch_dir)
        assert promises[0].phase_markers == [2]
        assert "ADR-018" in promises[0].adr_refs

    def test_extracts_constraint_level(self, tmp_path: Path) -> None:
        arch_dir = _make_arch_doc(
            tmp_path,
            textwrap.dedent("""\
            ## 1.6 Settings
            LAW constraints apply to tier depth.
        """),
        )
        promises = pr.parse_architecture_promises(arch_dir)
        assert promises[0].constraint_level == "LAW"

    def test_skips_deep_subsections(self, tmp_path: Path) -> None:
        arch_dir = _make_arch_doc(
            tmp_path,
            textwrap.dedent("""\
            ##### 1.2.3.4.5 Very Deep
            Should be skipped (level > 4).
        """),
        )
        promises = pr.parse_architecture_promises(arch_dir)
        assert len(promises) == 0


# ---------------------------------------------------------------------------
# Delivery Map Parsing
# ---------------------------------------------------------------------------


class TestParseDeliveryMap:
    """Test parsing the delivery map Table 2."""

    def test_parses_delivery_rows(self, tmp_path: Path) -> None:
        map_file = tmp_path / "delivery-map.md"
        map_file.write_text(
            textwrap.dedent("""\
            | 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
            |-------------|---------|----------|-----------|
            | 01 §6 | B0-1 | TASK-B0-1 | Brain module skeleton |
            | 02 §1 | K0-1 | TASK-K0-1 | KnowledgePort interface |
        """),
            encoding="utf-8",
        )
        entries = pr.parse_delivery_map(map_file)
        assert len(entries) == 2
        assert entries[0].task_card_id == "TASK-B0-1"
        assert entries[1].arch_section == "02 §1"


# ---------------------------------------------------------------------------
# Task Card Parsing
# ---------------------------------------------------------------------------


class TestParseTaskCards:
    """Test task card extraction."""

    def test_extracts_task_ids(self, tmp_path: Path) -> None:
        tc_dir = tmp_path / "task-cards"
        tc_dir.mkdir()
        (tc_dir / "brain.md").write_text(
            textwrap.dedent("""\
            ### TASK-B0-1: Brain Skeleton
            验收命令: test -f src/brain/__init__.py

            ### TASK-B2-1: Conversation Engine
            Some description.
        """)
        )
        cards = pr.parse_task_cards(tc_dir)
        task_ids = {c.task_id for c in cards}
        assert "TASK-B0-1" in task_ids
        assert "TASK-B2-1" in task_ids

    def test_detects_acceptance_cmd(self, tmp_path: Path) -> None:
        tc_dir = tmp_path / "task-cards"
        tc_dir.mkdir()
        (tc_dir / "brain.md").write_text("### TASK-B0-1: Test\n验收命令: pytest tests/\n")
        cards = pr.parse_task_cards(tc_dir)
        assert cards[0].has_acceptance_cmd


# ---------------------------------------------------------------------------
# Section Key Normalization
# ---------------------------------------------------------------------------


class TestNormalizeSectionKey:
    """Test section key normalization for matching."""

    def test_basic_normalization(self) -> None:
        assert pr._normalize_section_key("01 §6") == "01§6"
        assert pr._normalize_section_key("01-§6") == "01§6"
        assert pr._normalize_section_key("FE-01 §1") == "FE-01§1"
        assert pr._normalize_section_key("05a §1.1") == "05a§1.1"


# ---------------------------------------------------------------------------
# Owner Derivation
# ---------------------------------------------------------------------------


class TestDeriveOwner:
    """Test owner/layer derivation from doc names."""

    def test_brain_owner(self) -> None:
        assert pr._derive_owner("01-§2", "01-对话Agent层-Brain.md") == "Brain"

    def test_knowledge_owner(self) -> None:
        assert pr._derive_owner("02-§1", "02-Knowledge层.md") == "Knowledge"

    def test_gateway_owner(self) -> None:
        assert pr._derive_owner("05-§1", "05-Gateway层.md") == "Gateway"

    def test_frontend_owner(self) -> None:
        assert pr._derive_owner("FE-01-§1", "01-monorepo-infrastructure.md") == "Frontend"

    def test_infra_owner(self) -> None:
        assert pr._derive_owner("06-§1", "06-基础设施层.md") == "Infrastructure"


# ---------------------------------------------------------------------------
# Evidence Finding
# ---------------------------------------------------------------------------


class TestFindEvidence:
    """Test evidence file lookup."""

    def test_finds_matching_evidence(self, tmp_path: Path) -> None:
        ev_dir = tmp_path / "evidence"
        ev_dir.mkdir()
        (ev_dir / "drill-release-20260223.json").write_text("{}")
        # Gate ID that partially matches
        paths = pr._find_evidence(["drill-release"], ev_dir)
        assert len(paths) == 1

    def test_no_evidence_dir(self, tmp_path: Path) -> None:
        paths = pr._find_evidence(["p1-rls"], tmp_path / "nonexistent")
        assert paths == []


# ---------------------------------------------------------------------------
# Traceability Engine
# ---------------------------------------------------------------------------


class TestBuildTrace:
    """Test the traceability chain builder."""

    def test_mapped_promise_gets_grade_b(self) -> None:
        """Promise with task + gate but no evidence = grade B."""
        promises = [
            pr.ArchPromise("01-§6", "01-Brain.md", "6", "Ports", phase_markers=[0]),
        ]
        delivery = [
            pr.DeliveryMapEntry("01 §6", "B0-1", "TASK-B0-1", "Brain skeleton"),
        ]
        cards = [
            pr.TaskCard("TASK-B0-1", 0, "B", "brain.md", has_acceptance_cmd=True),
        ]
        gates = {"phase_0": ["p0-backend-skeleton"]}

        results = pr.build_trace(promises, delivery, cards, gates)
        assert len(results) == 1
        assert results[0].coverage_grade == "B"
        assert "TASK-B0-1" in results[0].mapped_task_cards

    def test_no_ac_downgrades_to_b_minus(self) -> None:
        """Promise with task + gate but NO acceptance command = grade B-."""
        promises = [
            pr.ArchPromise("01-§6", "01-Brain.md", "6", "Ports", phase_markers=[0]),
        ]
        delivery = [
            pr.DeliveryMapEntry("01 §6", "B0-1", "TASK-B0-1", "Brain skeleton"),
        ]
        cards = [
            pr.TaskCard("TASK-B0-1", 0, "B", "brain.md", has_acceptance_cmd=False),
        ]
        gates = {"phase_0": ["p0-backend-skeleton"]}

        results = pr.build_trace(promises, delivery, cards, gates)
        assert results[0].coverage_grade == "B-"
        assert "TASK-B0-1" in results[0].missing_acceptance_cmds

    def test_unmapped_promise_gets_grade_f(self) -> None:
        """Promise with no delivery map entry = grade F."""
        promises = [
            pr.ArchPromise("00-§7.3", "00-Overview.md", "7.3", "Kernel self-sufficiency"),
        ]
        results = pr.build_trace(promises, [], [], {})
        assert results[0].coverage_grade == "F"

    def test_detects_phase_mismatch(self) -> None:
        """Architecture says Phase 2, task card is Phase 0 -> mismatch."""
        promises = [
            pr.ArchPromise("01-§3.1", "01-Brain.md", "3.1", "MemoryCorePort", phase_markers=[2]),
        ]
        delivery = [
            pr.DeliveryMapEntry("01 §3.1", "MC0-1", "TASK-MC0-1", "MemoryCorePort def"),
        ]
        cards = [
            pr.TaskCard("TASK-MC0-1", 0, "MC", "memory-core.md"),
        ]
        results = pr.build_trace(promises, delivery, cards, {})
        assert len(results[0].phase_mismatches) == 1
        assert "Phase 0" in results[0].phase_mismatches[0]

    def test_owner_populated(self) -> None:
        promises = [
            pr.ArchPromise("01-§6", "01-对话Agent层-Brain.md", "6", "Ports"),
        ]
        results = pr.build_trace(promises, [], [], {})
        assert results[0].owner == "Brain"


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """Test report structure and content."""

    def test_report_has_phase_mismatches(self) -> None:
        results = [
            pr.PromiseTraceResult(
                "01-§3.1",
                "01-Brain.md",
                "3.1",
                "MemoryCorePort",
                mapped_task_cards=["TASK-MC0-1"],
                phase_mismatches=["TASK-MC0-1 is Phase 0, arch says Phase [2]"],
                coverage_grade="C",
            ),
        ]
        report = pr.generate_report(results, [], [])
        assert report["summary"]["phase_mismatches"] == 1
        assert len(report["phase_mismatches"]) == 1

    def test_report_has_missing_acceptance_cmds(self) -> None:
        results = [
            pr.PromiseTraceResult(
                "01-§6",
                "01-Brain.md",
                "6",
                "Ports",
                mapped_task_cards=["TASK-B0-1"],
                missing_acceptance_cmds=["TASK-B0-1"],
                coverage_grade="B-",
            ),
        ]
        report = pr.generate_report(results, [], [])
        assert report["summary"]["missing_acceptance_cmds"] == 1
        assert len(report["missing_acceptance_cmds"]) == 1
        assert report["missing_acceptance_cmds"][0]["missing_ac_tasks"] == ["TASK-B0-1"]

    def test_verbose_includes_evidence_owner_and_ac(self) -> None:
        results = [
            pr.PromiseTraceResult(
                "01-§6",
                "01-Brain.md",
                "6",
                "Ports",
                mapped_task_cards=["TASK-B0-1"],
                mapped_gates=["p0-backend"],
                evidence_paths=["evidence/release.json"],
                owner="Brain",
                coverage_grade="A",
            ),
        ]
        report = pr.generate_report(results, [], [], verbose=True)
        r = report["all_results"][0]
        assert r["evidence_paths"] == ["evidence/release.json"]
        assert r["owner"] == "Brain"
        assert r["phase_mismatches"] == []
        assert r["missing_acceptance_cmds"] == []


# ---------------------------------------------------------------------------
# Integration: actual codebase
# ---------------------------------------------------------------------------


class TestValidationFixtures:
    """Validate against baseline codebase per guardian-system-completion-plan-v1.0.md."""

    def test_script_runs_json_mode(self) -> None:
        """Script produces valid JSON output."""
        result = _run_script("--json")
        data = json.loads(result.stdout)
        assert "status" in data
        assert "summary" in data

    def test_summary_has_all_required_fields(self) -> None:
        result = _run_script("--json")
        data = json.loads(result.stdout)
        s = data["summary"]
        assert "total_promises" in s
        assert "grade_distribution" in s
        assert "unmapped_count" in s
        assert "orphaned_task_cards" in s
        assert "phase_mismatches" in s
        assert "missing_acceptance_cmds" in s

    def test_detects_unmapped_promises(self) -> None:
        """Must detect unmapped promises (plan line 137/334)."""
        result = _run_script("--json")
        data = json.loads(result.stdout)
        assert data["summary"]["unmapped_count"] > 0

    def test_detects_phase_mismatches(self) -> None:
        """Must detect phase mismatches (plan line 137)."""
        result = _run_script("--json")
        data = json.loads(result.stdout)
        assert data["summary"]["phase_mismatches"] > 0

    def test_verbose_output_has_evidence_owner_and_ac(self) -> None:
        """Verbose output must include evidence_paths, owner, and missing_acceptance_cmds."""
        result = _run_script("--json", "--verbose")
        data = json.loads(result.stdout)
        assert "all_results" in data
        first = data["all_results"][0]
        assert "evidence_paths" in first
        assert "owner" in first
        assert "phase_mismatches" in first
        assert "missing_acceptance_cmds" in first
