"""Tests for scripts/check_xnode_deep.py -- X-Node Deep Verification."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_xnode_deep.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
xn = importlib.import_module("check_xnode_deep")


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


def _make_matrix(tmp_path: Path, content: str) -> Path:
    """Create a milestone-matrix.yaml."""
    matrix = tmp_path / "delivery" / "milestone-matrix.yaml"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text(content, encoding="utf-8")
    return matrix


def _make_evidence(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create evidence files."""
    ev_dir = tmp_path / "evidence"
    for rel, content in files.items():
        f = ev_dir / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    return ev_dir


# ---------------------------------------------------------------------------
# Matrix Parsing
# ---------------------------------------------------------------------------


class TestParseXNodeGates:
    """Test X-node gate extraction from milestone-matrix."""

    def test_extracts_xnode_gates(self, tmp_path: Path) -> None:
        matrix = _make_matrix(
            tmp_path,
            textwrap.dedent("""\
                phases:
                  phase_2:
                    exit_criteria:
                      hard:
                        - id: "p2-x2-1"
                          description: "Full conversation loop"
                          check: "uv run pytest tests/e2e/cross/test_conv.py -v"
                          xnodes: [X2-1, X2-2]
                      soft:
                        - id: "p2-x2-3"
                          description: "Memory evolution"
                          check: "uv run pytest tests/e2e/cross/test_mem.py -v"
                          xnodes: [X2-3]
            """),
        )
        gates = xn.parse_xnode_gates(matrix_path=matrix)
        assert len(gates) == 2
        assert gates[0].gate_id == "p2-x2-1"
        assert gates[0].xnodes == ["X2-1", "X2-2"]
        assert gates[0].tier == "hard"
        assert gates[1].xnodes == ["X2-3"]
        assert gates[1].tier == "soft"

    def test_skips_non_xnode_gates(self, tmp_path: Path) -> None:
        matrix = _make_matrix(
            tmp_path,
            textwrap.dedent("""\
                phases:
                  phase_2:
                    exit_criteria:
                      hard:
                        - id: "p2-test"
                          description: "Unit tests"
                          check: "uv run pytest tests/unit/"
                      soft: []
            """),
        )
        gates = xn.parse_xnode_gates(matrix_path=matrix)
        assert len(gates) == 0

    def test_missing_matrix(self, tmp_path: Path) -> None:
        gates = xn.parse_xnode_gates(matrix_path=tmp_path / "nonexistent.yaml")
        assert gates == []


# ---------------------------------------------------------------------------
# Trivial Command Detection
# ---------------------------------------------------------------------------


class TestTrivialDetection:
    """Test detection of trivially-passing commands."""

    def test_test_f_is_trivial(self) -> None:
        assert xn._is_trivial_command("test -f src/brain/__init__.py")

    def test_grep_q_is_trivial(self) -> None:
        assert xn._is_trivial_command("grep -q pattern file.txt")

    def test_wc_l_is_trivial(self) -> None:
        assert xn._is_trivial_command("wc -l file.txt")

    def test_pytest_not_trivial(self) -> None:
        assert not xn._is_trivial_command("uv run pytest tests/unit/ -v")

    def test_empty_not_trivial(self) -> None:
        assert not xn._is_trivial_command("")


# ---------------------------------------------------------------------------
# Evidence Checking
# ---------------------------------------------------------------------------


class TestEvidenceCheck:
    """Test evidence file lookup and validation."""

    def test_finds_matching_evidence(self, tmp_path: Path) -> None:
        ev_dir = _make_evidence(
            tmp_path,
            {
                "cross/x2-1-conversation.json": '{"status": "pass", "duration_ms": 1200}',
            },
        )
        gate = xn.XNodeGate("p2-x2-1", "conv loop", "echo ok", ["X2-1"], "phase_2", "hard")
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(result, gate, evidence_dir=ev_dir)
        assert result.evidence_status == "present"
        assert len(result.evidence_paths) >= 1

    def test_empty_evidence_file(self, tmp_path: Path) -> None:
        ev_dir = _make_evidence(
            tmp_path,
            {
                "cross/x2-1-conversation.json": "{}",
            },
        )
        gate = xn.XNodeGate("p2-x2-1", "conv loop", "echo ok", ["X2-1"], "phase_2", "hard")
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(result, gate, evidence_dir=ev_dir)
        assert result.evidence_status == "empty"

    def test_missing_evidence_dir(self, tmp_path: Path) -> None:
        gate = xn.XNodeGate("p2-x2-1", "conv loop", "echo ok", ["X2-1"], "phase_2", "hard")
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(result, gate, evidence_dir=tmp_path / "nonexistent")
        assert result.evidence_status == "missing"

    def test_no_matching_evidence(self, tmp_path: Path) -> None:
        ev_dir = _make_evidence(
            tmp_path,
            {
                "other/unrelated.json": '{"data": true}',
            },
        )
        gate = xn.XNodeGate("p2-x2-1", "conv loop", "echo ok", ["X2-1"], "phase_2", "hard")
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(result, gate, evidence_dir=ev_dir)
        assert result.evidence_status == "missing"


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


class TestReportGeneration:
    """Test report structure and status determination."""

    def test_pass_status(self) -> None:
        results = [
            xn.XNodeResult("g1", ["X2-1"], "p2", "PASS", evidence_status="present"),
        ]
        report = xn.generate_report(results)
        assert report["status"] == "PASS"

    def test_fail_on_execution_failure(self) -> None:
        results = [
            xn.XNodeResult("g1", ["X2-1"], "p2", "FAIL", execution_error="test failed"),
        ]
        report = xn.generate_report(results)
        assert report["status"] == "FAIL"
        assert len(report["failed_gates"]) == 1

    def test_warn_on_many_trivial(self) -> None:
        results = [
            xn.XNodeResult("g1", ["X2-1"], "p2", "PASS", is_trivial=True),
            xn.XNodeResult("g2", ["X2-2"], "p2", "PASS", is_trivial=True),
        ]
        report = xn.generate_report(results)
        assert report["status"] == "WARN"

    def test_verbose_includes_all(self) -> None:
        results = [
            xn.XNodeResult("g1", ["X2-1"], "p2", "PASS"),
        ]
        report = xn.generate_report(results, verbose=True)
        assert "all_results" in report

    def test_summary_counts(self) -> None:
        results = [
            xn.XNodeResult("g1", ["X2-1"], "p2", "PASS", evidence_status="present"),
            xn.XNodeResult("g2", ["X2-2"], "p2", "SKIP"),
            xn.XNodeResult("g3", ["X3-1"], "p3", "FAIL", evidence_status="missing"),
        ]
        report = xn.generate_report(results)
        s = report["summary"]
        assert s["total_xnode_gates"] == 3
        assert s["executed_pass"] == 1
        assert s["executed_fail"] == 1
        assert s["skipped"] == 1
        assert s["unique_xnodes"] == 3


# ---------------------------------------------------------------------------
# Integration: Script execution
# ---------------------------------------------------------------------------


class TestScriptExecution:
    """Integration tests running the script as subprocess."""

    def test_json_output_valid(self) -> None:
        result = _run_script("--json", "--skip-execution")
        assert result.returncode in (0, 1), f"Exit {result.returncode}: {result.stderr}"
        report = json.loads(result.stdout)
        assert "status" in report
        assert "summary" in report

    def test_summary_has_required_fields(self) -> None:
        result = _run_script("--json", "--skip-execution")
        report = json.loads(result.stdout)
        s = report["summary"]
        assert "total_xnode_gates" in s
        assert "unique_xnodes" in s
        assert "executed_pass" in s
        assert "trivial_count" in s
        assert "evidence_present" in s

    def test_detects_xnode_gates(self) -> None:
        """Must find X-node gates in the real milestone-matrix."""
        result = _run_script("--json", "--skip-execution")
        report = json.loads(result.stdout)
        assert report["summary"]["total_xnode_gates"] > 0
        assert report["summary"]["unique_xnodes"] > 0

    def test_human_readable_output(self) -> None:
        result = _run_script("--skip-execution")
        assert result.returncode in (0, 1)
        assert "X-Node Deep Verification" in result.stdout
