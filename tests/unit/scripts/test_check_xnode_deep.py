"""Tests for scripts/check_xnode_deep.py -- X-Node Deep Verification."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import textwrap
import time
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


def _make_evidence(
    tmp_path: Path,
    files: dict[str, str],
    *,
    mtime_offset: float = 0,
) -> Path:
    """Create evidence files. mtime_offset shifts mtime (negative = older)."""
    ev_dir = tmp_path / "evidence"
    for rel, content in files.items():
        f = ev_dir / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
        if mtime_offset != 0:
            t = time.time() + mtime_offset
            os.utime(f, (t, t))
    return ev_dir


def _make_src(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create src/ files for stale evidence testing."""
    src = tmp_path / "src"
    for rel, content in files.items():
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    return src


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

    def test_done_only_filters_to_done_phases(self, tmp_path: Path) -> None:
        """done_only=True only returns gates from phases with all milestones done."""
        matrix = _make_matrix(
            tmp_path,
            textwrap.dedent("""\
                schema_version: "1.1"
                current_phase: "phase_2"
                phases:
                  phase_1:
                    milestones:
                      - {id: "G1-1", summary: "JWT", status: "done"}
                      - {id: "G1-2", summary: "Org", status: "done"}
                    exit_criteria:
                      hard:
                        - id: "p1-x1-1"
                          check: "echo ok"
                          xnodes: [X1-1]
                      soft: []
                  phase_2:
                    milestones:
                      - {id: "B2-1", summary: "Conv engine"}
                    exit_criteria:
                      hard:
                        - id: "p2-x2-1"
                          check: "echo ok"
                          xnodes: [X2-1]
                      soft: []
            """),
        )
        # Without filter: returns both phases
        all_gates = xn.parse_xnode_gates(matrix_path=matrix, done_only=False)
        assert len(all_gates) == 2

        # With filter: only phase_1 (all milestones done)
        done_gates = xn.parse_xnode_gates(matrix_path=matrix, done_only=True)
        assert len(done_gates) == 1
        assert done_gates[0].phase == "phase_1"

    def test_done_only_phase0_implicit(self, tmp_path: Path) -> None:
        """Phase 0 milestones without status are treated as done when current > 0."""
        matrix = _make_matrix(
            tmp_path,
            textwrap.dedent("""\
                schema_version: "1.1"
                current_phase: "phase_1"
                phases:
                  phase_0:
                    milestones:
                      - {id: "B0-1", summary: "Brain skeleton"}
                    exit_criteria:
                      hard:
                        - id: "p0-x0-1"
                          check: "echo ok"
                          xnodes: [X0-1]
                      soft: []
            """),
        )
        done_gates = xn.parse_xnode_gates(matrix_path=matrix, done_only=True)
        assert len(done_gates) == 1
        assert done_gates[0].phase == "phase_0"


class TestGetDonePhases:
    """Test done phase detection from milestone-matrix."""

    def test_all_done(self) -> None:
        matrix = {
            "current_phase": "phase_2",
            "phases": {
                "phase_1": {
                    "milestones": [
                        {"id": "G1-1", "status": "done"},
                        {"id": "G1-2", "status": "done"},
                    ],
                },
            },
        }
        assert "phase_1" in xn.get_done_phases(matrix)

    def test_not_done_when_missing_status(self) -> None:
        matrix = {
            "current_phase": "phase_2",
            "phases": {
                "phase_2": {
                    "milestones": [
                        {"id": "B2-1", "summary": "Conv engine"},
                    ],
                },
            },
        }
        assert "phase_2" not in xn.get_done_phases(matrix)

    def test_partial_done_excluded(self) -> None:
        matrix = {
            "current_phase": "phase_2",
            "phases": {
                "phase_2": {
                    "milestones": [
                        {"id": "B2-1", "status": "done"},
                        {"id": "B2-2"},
                    ],
                },
            },
        }
        assert "phase_2" not in xn.get_done_phases(matrix)


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
            {"cross/x2-1-conversation.json": '{"status": "pass"}'},
        )
        gate = xn.XNodeGate(
            "p2-x2-1",
            "conv loop",
            "echo ok",
            ["X2-1"],
            "phase_2",
            "hard",
        )
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(result, gate, evidence_dir=ev_dir)
        assert result.evidence_status == "present"
        assert len(result.evidence_paths) >= 1
        assert result.evidence_age_hours >= 0

    def test_empty_evidence_file(self, tmp_path: Path) -> None:
        ev_dir = _make_evidence(
            tmp_path,
            {"cross/x2-1-conversation.json": "{}"},
        )
        gate = xn.XNodeGate(
            "p2-x2-1",
            "conv loop",
            "echo ok",
            ["X2-1"],
            "phase_2",
            "hard",
        )
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(result, gate, evidence_dir=ev_dir)
        assert result.evidence_status == "empty"

    def test_missing_evidence_dir(self, tmp_path: Path) -> None:
        gate = xn.XNodeGate(
            "p2-x2-1",
            "conv loop",
            "echo ok",
            ["X2-1"],
            "phase_2",
            "hard",
        )
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(result, gate, evidence_dir=tmp_path / "nonexistent")
        assert result.evidence_status == "missing"

    def test_no_matching_evidence(self, tmp_path: Path) -> None:
        ev_dir = _make_evidence(
            tmp_path,
            {"other/unrelated.json": '{"data": true}'},
        )
        gate = xn.XNodeGate(
            "p2-x2-1",
            "conv loop",
            "echo ok",
            ["X2-1"],
            "phase_2",
            "hard",
        )
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(result, gate, evidence_dir=ev_dir)
        assert result.evidence_status == "missing"

    def test_stale_evidence_older_than_src(self, tmp_path: Path) -> None:
        """Evidence older than src/ changes is stale."""
        # Create evidence first (older)
        ev_dir = _make_evidence(
            tmp_path,
            {"cross/x2-1-result.json": '{"ok": true}'},
            mtime_offset=-3600,  # 1 hour ago
        )
        # Create src file (newer — just now)
        _make_src(tmp_path, {"brain/engine.py": "class Engine: pass\n"})
        gate = xn.XNodeGate(
            "p2-x2-1",
            "conv",
            "echo ok",
            ["X2-1"],
            "phase_2",
            "hard",
        )
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(
            result,
            gate,
            evidence_dir=ev_dir,
            src_dir=tmp_path / "src",
        )
        assert result.evidence_status == "stale"
        assert any("older than" in f for f in result.findings)

    def test_stale_evidence_exceeds_threshold(self, tmp_path: Path) -> None:
        """Evidence older than threshold is stale."""
        ev_dir = _make_evidence(
            tmp_path,
            {"cross/x2-1-result.json": '{"ok": true}'},
            mtime_offset=-3600 * 200,  # 200 hours ago
        )
        gate = xn.XNodeGate(
            "p2-x2-1",
            "conv",
            "echo ok",
            ["X2-1"],
            "phase_2",
            "hard",
        )
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(
            result,
            gate,
            evidence_dir=ev_dir,
            src_dir=tmp_path / "nonexistent_src",
            stale_threshold_hours=168,
        )
        assert result.evidence_status == "stale"
        assert result.evidence_age_hours > 168

    def test_fresh_evidence_not_stale(self, tmp_path: Path) -> None:
        """Recent evidence newer than src/ is not stale."""
        # Create src first (older)
        src = _make_src(tmp_path, {"brain/engine.py": "class E: pass\n"})
        time.sleep(0.05)
        # Create evidence after (newer)
        ev_dir = _make_evidence(
            tmp_path,
            {"cross/x2-1-result.json": '{"ok": true}'},
        )
        gate = xn.XNodeGate(
            "p2-x2-1",
            "conv",
            "echo ok",
            ["X2-1"],
            "phase_2",
            "hard",
        )
        result = xn.XNodeResult(gate_id="p2-x2-1", xnodes=["X2-1"], phase="phase_2")
        xn.check_evidence(
            result,
            gate,
            evidence_dir=ev_dir,
            src_dir=src,
        )
        assert result.evidence_status == "present"


# ---------------------------------------------------------------------------
# Per-X-node Aggregation
# ---------------------------------------------------------------------------


class TestAggregatePerNode:
    """Test aggregation of gate results into per-X-node verifications."""

    def test_single_gate_single_node(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
        ]
        nodes = xn.aggregate_per_node(results)
        assert len(nodes) == 1
        assert nodes[0].node_id == "X2-1"
        assert nodes[0].verdict == "pass"
        assert nodes[0].execution_status == "PASS"

    def test_multiple_gates_same_node(self) -> None:
        """Multiple gates referencing same X-node are merged."""
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
            xn.XNodeResult(
                "g2",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
        ]
        nodes = xn.aggregate_per_node(results)
        assert len(nodes) == 1
        assert nodes[0].gate_ids == ["g1", "g2"]
        assert nodes[0].verdict == "pass"

    def test_fail_verdict_on_any_failure(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
            xn.XNodeResult(
                "g2",
                ["X2-1"],
                "p2",
                "FAIL",
                evidence_status="present",
            ),
        ]
        nodes = xn.aggregate_per_node(results)
        assert nodes[0].verdict == "fail"

    def test_stale_verdict(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="stale",
                evidence_age_hours=200.0,
            ),
        ]
        nodes = xn.aggregate_per_node(results)
        assert nodes[0].verdict == "stale"
        assert nodes[0].evidence_age_hours == 200.0

    def test_unverified_when_skip(self) -> None:
        results = [
            xn.XNodeResult("g1", ["X2-1"], "p2", "SKIP"),
        ]
        nodes = xn.aggregate_per_node(results)
        assert nodes[0].verdict == "unverified"

    def test_unverified_when_missing_evidence(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="missing",
            ),
        ]
        nodes = xn.aggregate_per_node(results)
        assert nodes[0].verdict == "unverified"

    def test_multi_node_gate_splits(self) -> None:
        """A gate with xnodes=[X2-1, X2-2] creates entries for both."""
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1", "X2-2"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
        ]
        nodes = xn.aggregate_per_node(results)
        assert len(nodes) == 2
        node_ids = [n.node_id for n in nodes]
        assert "X2-1" in node_ids
        assert "X2-2" in node_ids

    def test_sorted_by_node_id(self) -> None:
        results = [
            xn.XNodeResult("g1", ["X3-1"], "p3", "PASS"),
            xn.XNodeResult("g2", ["X2-1"], "p2", "PASS"),
        ]
        nodes = xn.aggregate_per_node(results)
        assert nodes[0].node_id == "X2-1"
        assert nodes[1].node_id == "X3-1"

    def test_to_dict_includes_all_fields(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
                evidence_age_hours=5.0,
            ),
        ]
        nodes = xn.aggregate_per_node(results)
        d = nodes[0].to_dict()
        assert "node_id" in d
        assert "phase" in d
        assert "gate_ids" in d
        assert "execution_status" in d
        assert "evidence_age_hours" in d
        assert "evidence_status" in d
        assert "verdict" in d
        assert "findings" in d


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


class TestReportGeneration:
    """Test report structure and status determination."""

    def test_pass_status(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
        ]
        report = xn.generate_report(results)
        assert report["status"] == "PASS"

    def test_fail_on_execution_failure(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "FAIL",
                execution_error="test failed",
            ),
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

    def test_warn_on_stale_evidence(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="stale",
                evidence_age_hours=200.0,
            ),
        ]
        report = xn.generate_report(results)
        assert report["status"] == "WARN"
        assert report["summary"]["evidence_stale"] == 1

    def test_verbose_includes_all(self) -> None:
        results = [
            xn.XNodeResult("g1", ["X2-1"], "p2", "PASS"),
        ]
        report = xn.generate_report(results, verbose=True)
        assert "all_results" in report

    def test_summary_counts(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
            xn.XNodeResult("g2", ["X2-2"], "p2", "SKIP"),
            xn.XNodeResult(
                "g3",
                ["X3-1"],
                "p3",
                "FAIL",
                evidence_status="missing",
            ),
        ]
        report = xn.generate_report(results)
        s = report["summary"]
        assert s["total_xnode_gates"] == 3
        assert s["executed_pass"] == 1
        assert s["executed_fail"] == 1
        assert s["skipped"] == 1
        assert s["unique_xnodes"] == 3

    def test_report_has_nodes_section(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
        ]
        report = xn.generate_report(results)
        assert "nodes" in report
        assert len(report["nodes"]) == 1
        node = report["nodes"][0]
        assert node["node_id"] == "X2-1"
        assert node["verdict"] == "pass"
        assert "evidence_age_hours" in node

    def test_summary_node_counts(self) -> None:
        results = [
            xn.XNodeResult(
                "g1",
                ["X2-1"],
                "p2",
                "PASS",
                evidence_status="present",
            ),
            xn.XNodeResult(
                "g2",
                ["X2-2"],
                "p2",
                "FAIL",
                evidence_status="present",
            ),
            xn.XNodeResult(
                "g3",
                ["X3-1"],
                "p3",
                "PASS",
                evidence_status="stale",
                evidence_age_hours=200.0,
            ),
        ]
        report = xn.generate_report(results)
        s = report["summary"]
        assert s["node_pass"] == 1
        assert s["node_fail"] == 1
        assert s["node_stale"] == 1


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
        assert "nodes" in report

    def test_summary_has_required_fields(self) -> None:
        result = _run_script("--json", "--skip-execution")
        report = json.loads(result.stdout)
        s = report["summary"]
        assert "total_xnode_gates" in s
        assert "unique_xnodes" in s
        assert "executed_pass" in s
        assert "trivial_count" in s
        assert "evidence_present" in s
        assert "evidence_stale" in s
        assert "node_pass" in s
        assert "node_fail" in s
        assert "node_stale" in s
        assert "node_unverified" in s

    def test_nodes_have_required_fields(self) -> None:
        """Each node in 'nodes' must have node_id, evidence_age, verdict."""
        result = _run_script("--json", "--skip-execution")
        report = json.loads(result.stdout)
        for node in report["nodes"]:
            assert "node_id" in node
            assert "evidence_age_hours" in node
            assert "verdict" in node
            assert "evidence_status" in node
            assert "gate_ids" in node

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
        assert "X-Nodes:" in result.stdout
