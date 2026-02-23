"""Tests for scripts/check_cross_validation.py -- Cross-Validation Diagnostic."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_cross_validation.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
cv = importlib.import_module("check_cross_validation")


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


# ---------------------------------------------------------------------------
# Check 4: Architecture Boundary (AST-based, independent, testable first)
# ---------------------------------------------------------------------------


class TestArchitectureBoundary:
    """Check 4: AST-based layer import validation."""

    def test_no_violations_in_clean_tree(self, tmp_path: Path) -> None:
        """A clean src/ with no cross-layer imports produces 0 violations."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "engine.py").write_text("from src.ports.memory import MemoryCorePort\n")

        ctx = cv.ValidationContext()
        result = cv.check_architecture_boundary(ctx, src_dir=src)

        assert result.to_dict()["violations"] == []

    def test_detects_brain_importing_infra(self, tmp_path: Path) -> None:
        """Brain importing infra should be a violation."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "bad.py").write_text("from src.infra.db import engine\n")

        ctx = cv.ValidationContext()
        result = cv.check_architecture_boundary(ctx, src_dir=src)

        violations = result.to_dict()["violations"]
        assert len(violations) == 1
        assert violations[0]["layer"] == "brain"
        assert violations[0]["forbidden_prefix"] == "src.infra"

    def test_privacy_boundary_knowledge_memory(self, tmp_path: Path) -> None:
        """Knowledge importing memory violates privacy boundary."""
        src = tmp_path / "src"
        knowledge = src / "knowledge"
        knowledge.mkdir(parents=True)
        (knowledge / "__init__.py").write_text("")
        (knowledge / "leak.py").write_text("from src.memory.core import MemoryCore\n")

        ctx = cv.ValidationContext()
        result = cv.check_architecture_boundary(ctx, src_dir=src)

        data = result.to_dict()
        assert data["privacy_boundary_intact"] is False
        assert len(data["violations"]) >= 1

    def test_valid_ports_import_allowed(self, tmp_path: Path) -> None:
        """Importing from src.ports should not trigger violations."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "ok.py").write_text(
            "from src.ports.llm import LLMCallPort\nfrom src.ports.memory import MemoryCorePort\n"
        )

        ctx = cv.ValidationContext()
        result = cv.check_architecture_boundary(ctx, src_dir=src)

        assert result.to_dict()["violations"] == []

    def test_missing_src_dir_returns_empty(self) -> None:
        """Missing src/ directory should return clean result."""
        ctx = cv.ValidationContext()
        result = cv.check_architecture_boundary(ctx, src_dir=Path("/nonexistent/src"))

        data = result.to_dict()
        assert data["violations"] == []
        assert data["privacy_boundary_intact"] is True


# ---------------------------------------------------------------------------
# Check 1: Gate Coverage
# ---------------------------------------------------------------------------


class TestGateCoverage:
    """Check 1: Gate coverage of done milestones."""

    def test_all_covered(self) -> None:
        """All done milestones covered by exit criteria."""
        matrix = {
            "phases": {
                "phase_0": {
                    "milestones": [
                        {
                            "id": "B0-1",
                            "layer": "Brain",
                            "summary": "Brain skeleton",
                            "status": "done",
                        },
                    ],
                    "exit_criteria": {
                        "hard": [
                            {
                                "id": "p0-brain",
                                "description": "Brain skeleton B0-1 exists",
                                "check": "test -f src/brain/__init__.py",
                            },
                        ],
                        "soft": [],
                    },
                },
            },
        }
        ctx = cv.ValidationContext(matrix=matrix)
        result = cv.check_gate_coverage(ctx)
        data = result.to_dict()
        assert data["coverage_rate"] == 1.0
        assert data["uncovered"] == []

    def test_uncovered_milestone(self) -> None:
        """A done milestone with no matching criterion is uncovered."""
        matrix = {
            "phases": {
                "phase_0": {
                    "milestones": [
                        {
                            "id": "Z9-9",
                            "layer": "Unknown",
                            "summary": "orphan node",
                            "status": "done",
                        },
                    ],
                    "exit_criteria": {"hard": [], "soft": []},
                },
            },
        }
        ctx = cv.ValidationContext(matrix=matrix)
        result = cv.check_gate_coverage(ctx)
        data = result.to_dict()
        assert data["coverage_rate"] == 0.0
        assert len(data["uncovered"]) == 1
        assert data["uncovered"][0]["id"] == "Z9-9"

    def test_pending_milestones_excluded(self) -> None:
        """Non-done milestones should not be checked."""
        matrix = {
            "phases": {
                "phase_0": {
                    "milestones": [
                        {"id": "B0-1", "layer": "Brain", "summary": "pending"},
                    ],
                    "exit_criteria": {"hard": [], "soft": []},
                },
            },
        }
        ctx = cv.ValidationContext(matrix=matrix)
        result = cv.check_gate_coverage(ctx)
        data = result.to_dict()
        assert data["total_done_milestones"] == 0


# ---------------------------------------------------------------------------
# Check 5: Design Claim Audit
# ---------------------------------------------------------------------------


class TestDesignClaimAudit:
    """Check 5: Design claim verification."""

    def test_claims_with_matching_criteria(self) -> None:
        """Claims matched by gate criteria descriptions should be verified."""
        matrix = {
            "phases": {
                "phase_1": {
                    "exit_criteria": {
                        "hard": [
                            {
                                "id": "p1-rls",
                                "description": "RLS org_id isolation verified",
                                "check": "bash scripts/check_rls.sh",
                            },
                        ],
                        "soft": [],
                    },
                },
            },
        }
        ctx = cv.ValidationContext(matrix=matrix)
        result = cv.check_design_claims(ctx)
        data = result.to_dict()
        # DC-2 (RLS) should be verified
        verified_ids = [c["id"] for c in data["verified_details"]]
        assert "DC-2" in verified_ids

    def test_unverified_claim_reported(self) -> None:
        """Claims with no matching gate or test should be unverified."""
        matrix = {"phases": {}}
        ctx = cv.ValidationContext(matrix=matrix)
        # With empty matrix, most claims should be unverified
        result = cv.check_design_claims(ctx)
        data = result.to_dict()
        assert len(data["unverified"]) > 0


# ---------------------------------------------------------------------------
# Check 2: Acceptance Command Execution
# ---------------------------------------------------------------------------


class TestAcceptanceExecution:
    """Check 2: Acceptance command extraction and execution."""

    def test_extract_backtick_command(self) -> None:
        cmd = cv._extract_command("`uv run pytest tests/unit/ -v`")
        assert cmd == "uv run pytest tests/unit/ -v"

    def test_skip_env_dep(self) -> None:
        cmd = cv._extract_command("[ENV-DEP] `docker compose up`")
        assert cmd is None

    def test_skip_manual_verify(self) -> None:
        cmd = cv._extract_command("[MANUAL-VERIFY] check logs manually")
        assert cmd is None

    def test_skip_empty(self) -> None:
        cmd = cv._extract_command("")
        assert cmd is None

    def test_bare_command_extraction(self) -> None:
        cmd = cv._extract_command("uv run pytest tests/smoke/ -v")
        assert cmd == "uv run pytest tests/smoke/ -v"

    def test_skip_execution_mode(self) -> None:
        """When skip_execution=True, all commands should be skipped."""
        ctx = cv.ValidationContext(
            task_cards=[
                {
                    "task_id": "TASK-TEST-1",
                    "acceptance": "`echo hello`",
                    "gate_refs": [],
                },
            ],
            skip_execution=True,
        )
        result = cv.check_acceptance_execution(ctx)
        data = result.to_dict()
        assert data["executed"] == 0
        assert data["skipped"] == 1


# ---------------------------------------------------------------------------
# Check 3: Consistency
# ---------------------------------------------------------------------------


class TestConsistency:
    """Check 3: Gate-vs-acceptance consistency."""

    def test_matching_paths_consistent(self) -> None:
        matrix = {
            "phases": {
                "phase_0": {
                    "exit_criteria": {
                        "hard": [
                            {
                                "id": "p0-test",
                                "description": "test",
                                "check": "uv run pytest tests/unit/brain/test_engine.py",
                            },
                        ],
                        "soft": [],
                    },
                },
            },
        }
        cards = [
            {
                "task_id": "TASK-T-1",
                "acceptance": "`uv run pytest tests/unit/brain/test_engine.py -v`",
                "gate_refs": ["p0-test"],
                "matrix_refs": [],
            },
        ]
        ctx = cv.ValidationContext(matrix=matrix, task_cards=cards)
        result = cv.check_consistency(ctx)
        data = result.to_dict()
        assert data["consistent"] == 1
        assert data["mismatched"] == []

    def test_different_paths_mismatch(self) -> None:
        matrix = {
            "phases": {
                "phase_0": {
                    "exit_criteria": {
                        "hard": [
                            {
                                "id": "p0-test",
                                "description": "test",
                                "check": "uv run pytest tests/unit/brain/test_engine.py",
                            },
                        ],
                        "soft": [],
                    },
                },
            },
        }
        cards = [
            {
                "task_id": "TASK-T-1",
                "acceptance": "`uv run pytest tests/unit/gateway/test_auth.py -v`",
                "gate_refs": ["p0-test"],
                "matrix_refs": [],
            },
        ]
        ctx = cv.ValidationContext(matrix=matrix, task_cards=cards)
        result = cv.check_consistency(ctx)
        data = result.to_dict()
        assert len(data["mismatched"]) == 1


# ---------------------------------------------------------------------------
# Check 6: Call Graph (Business -> Infra)
# ---------------------------------------------------------------------------


class TestCallGraph:
    """Check 6: Business layers should not import infra directly."""

    def test_clean_src_no_violations(self, tmp_path: Path) -> None:
        """Business layers using ports only = 0 violations."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "engine.py").write_text("from src.ports.memory import MemoryCorePort\n")

        ctx = cv.ValidationContext()
        result = cv.check_call_graph(ctx, src_dir=src)
        data = result.to_dict()
        assert data["violations"] == []

    def test_brain_importing_infra_db(self, tmp_path: Path) -> None:
        """Brain importing src.infra.db should be a call graph violation."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "bad.py").write_text("from src.infra.db import get_session\n")

        ctx = cv.ValidationContext()
        result = cv.check_call_graph(ctx, src_dir=src)
        data = result.to_dict()
        assert len(data["violations"]) == 1
        assert data["violations"][0]["layer"] == "brain"
        assert "infra" in data["violations"][0]["infra_module"]

    def test_skill_importing_infra_cache(self, tmp_path: Path) -> None:
        """Skill importing infra.cache is a violation."""
        src = tmp_path / "src"
        skill = src / "skill"
        skill.mkdir(parents=True)
        (skill / "__init__.py").write_text("")
        (skill / "handler.py").write_text("from src.infra.cache import redis_client\n")

        ctx = cv.ValidationContext()
        result = cv.check_call_graph(ctx, src_dir=src)
        data = result.to_dict()
        assert len(data["violations"]) == 1

    def test_missing_src_empty(self) -> None:
        """Missing src/ returns empty result."""
        ctx = cv.ValidationContext()
        result = cv.check_call_graph(ctx, src_dir=Path("/nonexistent"))
        assert result.to_dict()["violations"] == []

    def test_layers_checked_listed(self, tmp_path: Path) -> None:
        """Existing layers are reported in layers_checked."""
        src = tmp_path / "src"
        for layer in ("brain", "knowledge"):
            d = src / layer
            d.mkdir(parents=True)
            (d / "__init__.py").write_text("")
            (d / "mod.py").write_text("import os\n")

        ctx = cv.ValidationContext()
        result = cv.check_call_graph(ctx, src_dir=src)
        data = result.to_dict()
        assert "brain" in data["layers_checked"]
        assert "knowledge" in data["layers_checked"]


# ---------------------------------------------------------------------------
# Check 7: Stub Detection
# ---------------------------------------------------------------------------


class TestStubDetection:
    """Check 7: AST scan for stubs/placeholders."""

    def test_detects_pass_only_body(self, tmp_path: Path) -> None:
        """Function with only `pass` body is a stub."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "stub.py").write_text("def placeholder():\n    pass\n")

        ctx = cv.ValidationContext()
        result = cv.check_stub_detection(ctx, src_dir=src)
        data = result.to_dict()
        assert data["total_stubs"] >= 1
        stub_types = [s["type"] for s in data["stubs"]]
        assert "pass_body" in stub_types

    def test_detects_not_implemented(self, tmp_path: Path) -> None:
        """Function raising NotImplementedError is a stub."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "wip.py").write_text("def future_feature():\n    raise NotImplementedError()\n")

        ctx = cv.ValidationContext()
        result = cv.check_stub_detection(ctx, src_dir=src)
        data = result.to_dict()
        stub_types = [s["type"] for s in data["stubs"]]
        assert "not_implemented" in stub_types

    def test_detects_todo_comment(self, tmp_path: Path) -> None:
        """# TODO comments are flagged as stubs."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "todo.py").write_text(
            "def real_function():\n    # TODO: implement this properly\n    return 42\n"
        )

        ctx = cv.ValidationContext()
        result = cv.check_stub_detection(ctx, src_dir=src)
        data = result.to_dict()
        stub_types = [s["type"] for s in data["stubs"]]
        assert "comment_stub" in stub_types

    def test_real_function_not_stub(self, tmp_path: Path) -> None:
        """A function with real logic is not flagged."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "real.py").write_text("def compute(x: int) -> int:\n    return x * 2\n")

        ctx = cv.ValidationContext()
        result = cv.check_stub_detection(ctx, src_dir=src)
        data = result.to_dict()
        assert data["total_stubs"] == 0

    def test_pass_with_docstring_is_stub(self, tmp_path: Path) -> None:
        """Function with docstring + pass is still a stub."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "doc_stub.py").write_text(
            'def documented_stub():\n    """Does nothing yet."""\n    pass\n'
        )

        ctx = cv.ValidationContext()
        result = cv.check_stub_detection(ctx, src_dir=src)
        data = result.to_dict()
        assert data["total_stubs"] >= 1

    def test_missing_src_empty(self) -> None:
        """Missing src/ returns empty result."""
        ctx = cv.ValidationContext()
        result = cv.check_stub_detection(ctx, src_dir=Path("/nonexistent"))
        assert result.to_dict()["total_stubs"] == 0


# ---------------------------------------------------------------------------
# Check 8: LLM Call Verification
# ---------------------------------------------------------------------------


class TestLLMCallVerification:
    """Check 8: Direct LLM library imports in business layers."""

    def test_clean_no_violations(self, tmp_path: Path) -> None:
        """No direct LLM imports = no violations."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "engine.py").write_text("from src.ports.llm import LLMCallPort\n")

        ctx = cv.ValidationContext()
        result = cv.check_llm_calls(ctx, src_dir=src)
        data = result.to_dict()
        assert data["violations"] == []

    def test_detects_openai_import(self, tmp_path: Path) -> None:
        """Direct openai import in brain layer is a violation."""
        src = tmp_path / "src"
        brain = src / "brain"
        brain.mkdir(parents=True)
        (brain / "__init__.py").write_text("")
        (brain / "direct.py").write_text("import openai\n")

        ctx = cv.ValidationContext()
        result = cv.check_llm_calls(ctx, src_dir=src)
        data = result.to_dict()
        assert len(data["violations"]) == 1
        assert data["violations"][0]["layer"] == "brain"

    def test_detects_anthropic_from_import(self, tmp_path: Path) -> None:
        """from anthropic.client import... in knowledge is a violation."""
        src = tmp_path / "src"
        knowledge = src / "knowledge"
        knowledge.mkdir(parents=True)
        (knowledge / "__init__.py").write_text("")
        (knowledge / "bad.py").write_text("from anthropic.client import Client\n")

        ctx = cv.ValidationContext()
        result = cv.check_llm_calls(ctx, src_dir=src)
        data = result.to_dict()
        assert len(data["violations"]) == 1

    def test_detects_httpx_import(self, tmp_path: Path) -> None:
        """httpx import in skill layer is a violation."""
        src = tmp_path / "src"
        skill = src / "skill"
        skill.mkdir(parents=True)
        (skill / "__init__.py").write_text("")
        (skill / "caller.py").write_text("import httpx\n")

        ctx = cv.ValidationContext()
        result = cv.check_llm_calls(ctx, src_dir=src)
        data = result.to_dict()
        assert len(data["violations"]) == 1

    def test_tool_layer_not_checked(self, tmp_path: Path) -> None:
        """Tool layer is allowed to import LLM libraries directly."""
        src = tmp_path / "src"
        tool = src / "tool"
        tool.mkdir(parents=True)
        (tool / "__init__.py").write_text("")
        (tool / "llm_wrapper.py").write_text("import openai\nimport anthropic\n")

        ctx = cv.ValidationContext()
        result = cv.check_llm_calls(ctx, src_dir=src)
        data = result.to_dict()
        assert data["violations"] == []

    def test_missing_src_empty(self) -> None:
        """Missing src/ returns empty result."""
        ctx = cv.ValidationContext()
        result = cv.check_llm_calls(ctx, src_dir=Path("/nonexistent"))
        assert result.to_dict()["violations"] == []


# ---------------------------------------------------------------------------
# Report Assembly (updated for 8 checks)
# ---------------------------------------------------------------------------


class TestReportAssembly:
    """Report status determination."""

    @staticmethod
    def _clean_checks(**overrides: dict) -> dict:
        """Build a clean (all-pass) checks dict, then apply overrides."""
        base: dict[str, dict] = {
            "gate_coverage": {"coverage_rate": 0.95, "uncovered": []},
            "architecture_boundary": {"violations": [], "privacy_boundary_intact": True},
            "acceptance_execution": {"failed": 0},
            "design_claims": {"unverified": []},
            "consistency": {"mismatched": []},
            "call_graph": {"violations": []},
            "stub_detection": {"total_stubs": 0},
            "llm_call_verification": {"violations": []},
        }
        base.update(overrides)
        return base

    def test_pass_status(self) -> None:
        checks = self._clean_checks()
        status, critical, _ = cv.determine_status(checks)
        assert status == "PASS"
        assert critical == 0

    def test_fail_on_arch_violations(self) -> None:
        checks = self._clean_checks(
            architecture_boundary={
                "violations": [{"file": "x.py", "line": 1}],
                "privacy_boundary_intact": True,
            },
        )
        status, critical, _ = cv.determine_status(checks)
        assert status == "FAIL"
        assert critical >= 1

    def test_fail_on_privacy_violation(self) -> None:
        checks = self._clean_checks(
            architecture_boundary={"violations": [], "privacy_boundary_intact": False},
        )
        status, _critical, _ = cv.determine_status(checks)
        assert status == "FAIL"
        assert _critical >= 1

    def test_fail_on_unverified_high_risk(self) -> None:
        checks = self._clean_checks(
            design_claims={"unverified": [{"id": "DC-X", "risk": "HIGH"}]},
        )
        status, _critical, _ = cv.determine_status(checks)
        assert status == "FAIL"

    def test_warn_on_low_coverage(self) -> None:
        checks = self._clean_checks(
            gate_coverage={"coverage_rate": 0.65, "uncovered": [{"id": "X"}]},
        )
        status, _critical, recs = cv.determine_status(checks)
        assert status == "WARN"
        assert any("coverage" in r.lower() for r in recs)

    def test_fail_on_call_graph_violations(self) -> None:
        checks = self._clean_checks(
            call_graph={"violations": [{"file": "x.py", "line": 1}]},
        )
        status, critical, recs = cv.determine_status(checks)
        assert status == "FAIL"
        assert critical >= 1
        assert any("call-graph" in r for r in recs)

    def test_warn_on_stubs(self) -> None:
        checks = self._clean_checks(
            stub_detection={"total_stubs": 5},
        )
        status, _critical, recs = cv.determine_status(checks)
        assert status == "WARN"
        assert any("stub" in r.lower() for r in recs)

    def test_fail_on_llm_violations(self) -> None:
        checks = self._clean_checks(
            llm_call_verification={"violations": [{"file": "x.py"}]},
        )
        status, critical, recs = cv.determine_status(checks)
        assert status == "FAIL"
        assert critical >= 1
        assert any("LLMCallPort" in r for r in recs)


# ---------------------------------------------------------------------------
# Integration: Script execution
# ---------------------------------------------------------------------------


class TestScriptExecution:
    """Integration tests running the script as a subprocess."""

    def test_json_output_valid(self) -> None:
        """Script produces valid JSON with --json --skip-execution."""
        result = _run_script("--json", "--skip-execution")
        # Should not crash (exit 0 or 1 both acceptable)
        assert result.returncode in (0, 1), f"Unexpected exit {result.returncode}: {result.stderr}"
        report = json.loads(result.stdout)
        assert "checks" in report
        assert "summary" in report
        assert report["summary"]["status"] in ("PASS", "WARN", "FAIL")

    def test_json_has_all_eight_checks(self) -> None:
        """All 8 checks are present in output."""
        result = _run_script("--json", "--skip-execution")
        report = json.loads(result.stdout)
        expected_checks = {
            "gate_coverage",
            "acceptance_execution",
            "consistency",
            "architecture_boundary",
            "design_claims",
            "call_graph",
            "stub_detection",
            "llm_call_verification",
        }
        assert set(report["checks"].keys()) == expected_checks

    def test_archive_creates_file(self, tmp_path: Path) -> None:
        """--archive creates an evidence file."""
        result = _run_script("--json", "--skip-execution", "--archive")
        assert result.returncode in (0, 1)
        report = json.loads(result.stdout)
        assert "checks" in report
        # Verify evidence directory was created
        evidence_dir = _REPO_ROOT / "evidence" / "cross-validation"
        if evidence_dir.exists():
            files = list(evidence_dir.glob("cross-validation-*.json"))
            assert len(files) >= 1

    def test_human_readable_output(self) -> None:
        """Without --json, script produces human-readable output."""
        result = _run_script("--skip-execution")
        assert result.returncode in (0, 1)
        assert "Cross-Validation Diagnostic" in result.stdout
        assert "[1/8]" in result.stdout
        assert "[8/8]" in result.stdout


# ---------------------------------------------------------------------------
# Task card parsing
# ---------------------------------------------------------------------------


class TestTaskCardParsing:
    """parse_task_cards() correctly extracts fields."""

    def test_parse_single_card(self, tmp_path: Path) -> None:
        cards_dir = tmp_path / "docs" / "task-cards"
        cards_dir.mkdir(parents=True)
        (cards_dir / "test.md").write_text(
            textwrap.dedent("""\
            ### TASK-INT-P0-TEST: Test card

            > 矩阵条目: B0-1
            > Gate: p0-brain

            | Field | Value |
            |-------|-------|
            | **验收命令** | `uv run pytest tests/unit/brain/ -v` |
        """)
        )

        cards = cv.parse_task_cards(task_cards_dir=cards_dir)

        assert len(cards) == 1
        assert cards[0]["task_id"] == "TASK-INT-P0-TEST"
        assert cards[0]["matrix_refs"] == ["B0-1"]
        assert cards[0]["gate_refs"] == ["p0-brain"]
        assert "uv run pytest" in cards[0]["acceptance"]
