"""Tests for check_acceptance_gate.py -- GAP-H1 acceptance hard gate."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

SCRIPT = Path("scripts/check_acceptance_gate.py")


def _run_gate(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _write_card(tmp_path: Path, content: str) -> Path:
    d = tmp_path / "task-cards"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "test.md"
    f.write_text(textwrap.dedent(content))
    return f


class TestAcceptanceGateBlocking:
    """GAP-H1: acceptance-not-executable / acceptance-empty / manual-verify-no-alt must BLOCK."""

    def test_acceptance_empty_blocks(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-1: Empty acceptance
            > 矩阵条目: T0-1
            | **目标** | something |
            | **验收命令** |  |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
        report = json.loads(result.stdout)
        rules = [v["rule"] for v in report["violations"]]
        assert "acceptance-empty" in rules

    def test_acceptance_not_executable_blocks(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-2: Natural language acceptance
            > 矩阵条目: T0-2
            | **验收命令** | input credentials and click submit |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 1
        report = json.loads(result.stdout)
        rules = [v["rule"] for v in report["violations"]]
        assert "acceptance-not-executable" in rules

    def test_manual_verify_no_alt_blocks(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-3: Manual verify without alt
            > 矩阵条目: T0-3
            | **验收命令** | [MANUAL-VERIFY] ok |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 1
        report = json.loads(result.stdout)
        rules = [v["rule"] for v in report["violations"]]
        assert "manual-verify-no-alt" in rules

    def test_env_dep_no_mapping_blocks(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-4: ENV-DEP without CI mapping
            > 矩阵条目: T0-4
            | **验收命令** | [ENV-DEP] some random thing without CI ref |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 1
        report = json.loads(result.stdout)
        rules = [v["rule"] for v in report["violations"]]
        assert "env-dep-no-mapping" in rules


class TestAcceptanceGatePass:
    """Acceptance commands that should pass validation."""

    def test_backtick_command_passes(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-5: Good backtick command
            > 矩阵条目: T0-5
            | **验收命令** | `make test` |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["status"] == "PASS"
        assert report["total_violations"] == 0

    def test_env_dep_with_docker_passes(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-6: ENV-DEP with docker mapping
            > 矩阵条目: T0-6
            | **验收命令** | [ENV-DEP] `docker compose up -d && curl localhost:8000/health` |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 0

    def test_manual_verify_with_sufficient_alt_passes(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-7: Manual verify with good alt
            > 矩阵条目: T0-7
            | **验收命令** | [MANUAL-VERIFY] Conversation complete (evidence in evidence/) |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 0

    def test_e2e_tag_passes(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-8: E2E tagged
            > 矩阵条目: T0-8
            | **验收命令** | [E2E] `pnpm exec playwright test tests/e2e/login.spec.ts` |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 0

    def test_excepted_acceptance_passes(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-9: Exception declared
            > 矩阵条目: T0-9
            > EXCEPTION: EXC-T09 | Field: 验收命令 | Owner: Faye | Deadline: Phase 2 | Alt: check
            | **验收命令** |  |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        assert result.returncode == 0


class TestAcceptanceGateFailClosed:
    """Fail-closed: parse errors must exit 2."""

    def test_nonexistent_file_exits_2(self) -> None:
        result = _run_gate("--json", "--filter-file", "/nonexistent/path.md")
        assert result.returncode == 2

    def test_nonexistent_base_dir_exits_2(self) -> None:
        result = _run_gate("--json", "--base-dir", "/nonexistent/dir")
        assert result.returncode == 2


class TestAcceptanceGateReport:
    """JSON report format validation."""

    def test_json_report_structure(self, tmp_path: Path) -> None:
        card_file = _write_card(
            tmp_path,
            """\
            ### TASK-TEST-0-10: For report test
            > 矩阵条目: T0-10
            | **验收命令** | `pytest tests/` |
        """,
        )
        result = _run_gate("--json", "--filter-file", str(card_file))
        report = json.loads(result.stdout)
        assert "total_cards" in report
        assert "total_violations" in report
        assert "violations_by_rule" in report
        assert "violations" in report
        assert "status" in report
        assert isinstance(report["violations"], list)
