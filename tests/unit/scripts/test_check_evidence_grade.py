"""Tests for scripts/check_evidence_grade.py -- Evidence Grade Classification."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_evidence_grade.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
eg = importlib.import_module("check_evidence_grade")


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


# ---------------------------------------------------------------------------
# Grade classification
# ---------------------------------------------------------------------------


class TestClassifyGrade:
    """Test individual command grade classification."""

    def test_grade_a_e2e(self) -> None:
        """E2E test commands should get grade A."""
        grade, _ = eg.classify_grade("uv run pytest tests/e2e/cross/test_conversation_loop.py -v")
        assert grade == "A"

    def test_grade_a_playwright(self) -> None:
        """Playwright test commands should get grade A."""
        grade, _ = eg.classify_grade("cd frontend && pnpm exec playwright test tests/e2e/web/")
        assert grade == "A"

    def test_grade_b_integration(self) -> None:
        """Integration test commands should get grade B."""
        grade, _ = eg.classify_grade("uv run pytest tests/integration/ -q --tb=short")
        assert grade == "B"

    def test_grade_b_isolation(self) -> None:
        """Isolation test commands should get grade B."""
        grade, _ = eg.classify_grade("uv run pytest tests/isolation/smoke/ --tb=short -q")
        assert grade == "B"

    def test_grade_c_unit(self) -> None:
        """Unit test commands should get grade C."""
        grade, _ = eg.classify_grade("uv run pytest tests/unit/brain/ -q --tb=short")
        assert grade == "C"

    def test_grade_c_pnpm_test(self) -> None:
        """pnpm run test should get grade C."""
        grade, _ = eg.classify_grade("cd frontend && pnpm run test")
        assert grade == "C"

    def test_grade_d_test_f(self) -> None:
        """test -f commands should get grade D."""
        grade, _ = eg.classify_grade("test -f CLAUDE.md && [ $(wc -l < CLAUDE.md) -le 80 ]")
        assert grade == "D"

    def test_grade_d_lint(self) -> None:
        """Lint commands should get grade D."""
        grade, _ = eg.classify_grade("make lint")
        assert grade == "D"

    def test_grade_d_grep(self) -> None:
        """Grep commands should get grade D."""
        grade, _ = eg.classify_grade("test -f Makefile && grep -q 'bootstrap' Makefile")
        assert grade == "D"

    def test_grade_d_python_import(self) -> None:
        """Python import checks should get grade D."""
        grade, _ = eg.classify_grade('uv run python -c "import scripts.check_task_schema"')
        assert grade == "D"

    def test_grade_d_bash_check(self) -> None:
        """Bash check scripts should get grade D."""
        grade, _ = eg.classify_grade("bash scripts/check_layer_deps.sh --json")
        assert grade == "D"

    def test_grade_d_security_scan(self) -> None:
        """Security scan scripts should get grade D."""
        grade, _ = eg.classify_grade("bash scripts/security_scan.sh --full")
        assert grade == "D"

    def test_grade_f_empty(self) -> None:
        """Empty command should get grade F."""
        grade, _ = eg.classify_grade("")
        assert grade == "F"

    def test_grade_c_pytest_generic(self) -> None:
        """Generic pytest command should get grade C."""
        grade, _ = eg.classify_grade("uv run pytest tests/ --cov=src --cov-fail-under=80 -q")
        assert grade == "C"


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


class TestAnalyze:
    """Test full analysis pipeline."""

    def test_parse_simple_matrix(self, tmp_path: Path) -> None:
        """Should parse exit_criteria from a simple matrix."""
        _make_matrix(
            tmp_path,
            textwrap.dedent("""\
                schema_version: "1.1"
                current_phase: "phase_0"
                phases:
                  phase_0:
                    name: "Test Phase"
                    exit_criteria:
                      hard:
                        - id: "p0-test"
                          description: "Unit tests pass"
                          check: "uv run pytest tests/unit/ -q"
                      soft:
                        - id: "p0-lint"
                          description: "Lint passes"
                          check: "make lint"
            """),
        )

        graded = eg.analyze(matrix_path=tmp_path / "delivery" / "milestone-matrix.yaml")
        assert len(graded) == 2
        # Unit test should get C
        unit_g = next(g for g in graded if g.criteria_id == "p0-test")
        assert unit_g.grade == "C"
        # Lint should get D
        lint_g = next(g for g in graded if g.criteria_id == "p0-lint")
        assert lint_g.grade == "D"

    def test_phase_filter(self, tmp_path: Path) -> None:
        """Should filter by target phase."""
        _make_matrix(
            tmp_path,
            textwrap.dedent("""\
                schema_version: "1.1"
                current_phase: "phase_1"
                phases:
                  phase_0:
                    name: "Phase 0"
                    exit_criteria:
                      hard:
                        - id: "p0-test"
                          description: "Test"
                          check: "uv run pytest tests/unit/ -q"
                      soft: []
                  phase_1:
                    name: "Phase 1"
                    exit_criteria:
                      hard:
                        - id: "p1-test"
                          description: "Test"
                          check: "uv run pytest tests/integration/ -q"
                      soft: []
            """),
        )

        graded = eg.analyze(
            matrix_path=tmp_path / "delivery" / "milestone-matrix.yaml",
            target_phase="phase_1",
        )
        assert len(graded) == 1
        assert graded[0].criteria_id == "p1-test"
        assert graded[0].grade == "B"

    def test_xnodes_extracted(self, tmp_path: Path) -> None:
        """Should extract xnodes from criteria."""
        _make_matrix(
            tmp_path,
            textwrap.dedent("""\
                schema_version: "1.1"
                current_phase: "phase_2"
                phases:
                  phase_2:
                    name: "Phase 2"
                    exit_criteria:
                      hard:
                        - id: "p2-x2-1"
                          description: "Cross-layer E2E"
                          check: "uv run pytest tests/e2e/cross/test_conversation_loop.py -v"
                          xnodes: [X2-1, X2-2]
                      soft: []
            """),
        )

        graded = eg.analyze(matrix_path=tmp_path / "delivery" / "milestone-matrix.yaml")
        assert len(graded) == 1
        assert graded[0].xnodes == ["X2-1", "X2-2"]

    def test_missing_matrix(self, tmp_path: Path) -> None:
        """Should return empty list for missing matrix."""
        graded = eg.analyze(matrix_path=tmp_path / "nonexistent.yaml")
        assert graded == []


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


class TestReportGeneration:
    """Test report structure."""

    def test_distribution(self) -> None:
        """Report should have correct grade distribution."""
        graded = [
            eg.GradedCriteria("p0", "p0-1", "d1", "cmd1", "hard", "A", "reason", []),
            eg.GradedCriteria("p0", "p0-2", "d2", "cmd2", "hard", "C", "reason", []),
            eg.GradedCriteria("p0", "p0-3", "d3", "cmd3", "soft", "D", "reason", []),
        ]
        report = eg.generate_report(graded)
        assert report["status"] == "PASS"
        assert report["summary"]["distribution"]["A"] == 1
        assert report["summary"]["distribution"]["C"] == 1
        assert report["summary"]["distribution"]["D"] == 1
        assert report["summary"]["coverage_rate"] == 100.0

    def test_upgrade_recommendations(self) -> None:
        """D and F grades should generate upgrade recommendations."""
        graded = [
            eg.GradedCriteria("p0", "p0-1", "d1", "cmd1", "hard", "D", "reason", []),
            eg.GradedCriteria("p0", "p0-2", "d2", "", "hard", "F", "empty", []),
        ]
        report = eg.generate_report(graded)
        assert len(report["upgrade_recommendations"]) == 2

    def test_verbose(self) -> None:
        """Verbose mode should include all criteria."""
        graded = [
            eg.GradedCriteria("p0", "p0-1", "d1", "cmd1", "hard", "A", "reason", []),
        ]
        report = eg.generate_report(graded, verbose=True)
        assert "all_criteria" in report
        assert len(report["all_criteria"]) == 1


# ---------------------------------------------------------------------------
# Integration: script runs on real repo
# ---------------------------------------------------------------------------


class TestScriptExecution:
    """Test the script runs end-to-end on the real repository."""

    def test_json_output(self) -> None:
        """Script should produce valid JSON output."""
        result = _run_script("--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "status" in data
        assert "summary" in data
        assert "distribution" in data["summary"]

    def test_classifies_all_criteria(self) -> None:
        """Script should classify 100% of exit_criteria."""
        result = _run_script("--json")
        data = json.loads(result.stdout)
        dist = data["summary"]["distribution"]
        total = sum(dist.values())
        assert total > 0, "Expected at least one exit_criteria"
        # Coverage should be > 0 (all criteria get a grade)
        assert data["summary"]["coverage_rate"] > 0

    def test_phase_filter(self) -> None:
        """Script should support --phase filter."""
        result = _run_script("--json", "--phase", "0")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        # The summary should have phase_distribution
        assert "phase_distribution" in data["summary"]
