"""Tests for scripts/check_frontend_depth.py -- Frontend Depth Audit."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = _REPO_ROOT / "scripts" / "check_frontend_depth.py"

# Ensure scripts/ is importable
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
fd = importlib.import_module("check_frontend_depth")


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


def _make_task_cards(tmp_path: Path, content: str) -> Path:
    """Create a minimal frontend task card file."""
    tc_dir = tmp_path / "docs" / "task-cards" / "frontend"
    tc_dir.mkdir(parents=True, exist_ok=True)
    (tc_dir / "test-cards.md").write_text(content, encoding="utf-8")
    return tc_dir


def _make_frontend(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a minimal frontend directory structure with files."""
    fe_dir = tmp_path / "frontend"
    for rel_path, content in files.items():
        f = fe_dir / rel_path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    return fe_dir


# ---------------------------------------------------------------------------
# Task card parsing
# ---------------------------------------------------------------------------


class TestParseTaskCards:
    """Test frontend task card parsing."""

    def test_parse_single_card(self, tmp_path: Path) -> None:
        tc_dir = _make_task_cards(
            tmp_path,
            textwrap.dedent("""\
                ### TASK-FW2-1: Chat page dual-pane layout

                | Field | Value |
                |-------|-------|
                | **验收命令** | `test -f frontend/apps/web/app/chat/page.tsx` |
            """),
        )
        cards = fd.parse_frontend_task_cards(task_cards_dir=tc_dir)
        assert len(cards) == 1
        assert cards[0].task_id == "TASK-FW2-1"
        assert "chat/page.tsx" in cards[0].acceptance

    def test_parse_multiple_cards(self, tmp_path: Path) -> None:
        tc_dir = _make_task_cards(
            tmp_path,
            textwrap.dedent("""\
                ### TASK-FW1-1: Login page

                | **验收命令** | `test -f frontend/apps/web/app/login/page.tsx` |

                ### TASK-FW2-1: Chat page

                | **验收命令** | `test -f frontend/apps/web/app/chat/page.tsx` |
            """),
        )
        cards = fd.parse_frontend_task_cards(task_cards_dir=tc_dir)
        assert len(cards) == 2
        ids = [c.task_id for c in cards]
        assert "TASK-FW1-1" in ids
        assert "TASK-FW2-1" in ids

    def test_empty_dir(self, tmp_path: Path) -> None:
        cards = fd.parse_frontend_task_cards(task_cards_dir=tmp_path / "nonexistent")
        assert cards == []


# ---------------------------------------------------------------------------
# Depth grading
# ---------------------------------------------------------------------------


class TestDepthGrading:
    """Test depth level assignment."""

    def test_l0_no_files(self, tmp_path: Path) -> None:
        """Task with no matching files gets L0."""
        card = fd.TaskCardAC(
            task_id="TASK-FW99-1",
            title="Nonexistent feature",
            acceptance="test -f frontend/apps/web/app/nowhere/page.tsx",
            source_file="test.md",
        )
        result = fd.grade_depth(card, frontend_dir=tmp_path / "frontend")
        assert result.depth_grade == "L0"

    def test_l1_file_exists(self, tmp_path: Path) -> None:
        """File exists but no exports -> L1."""
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/app/chat/page.tsx": "// empty file\n",
            },
        )
        card = fd.TaskCardAC(
            task_id="TASK-FW2-1",
            title="Chat page",
            acceptance="test -f frontend/apps/web/app/chat/page.tsx",
            source_file="test.md",
        )
        result = fd.grade_depth(card, frontend_dir=fe)
        assert result.depth_grade == "L1"

    def test_l2_has_exports(self, tmp_path: Path) -> None:
        """File with exports but no logic -> L2."""
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/app/chat/page.tsx": (
                    "export default function ChatPage() {\n  return <div>Hello</div>;\n}\n"
                ),
            },
        )
        card = fd.TaskCardAC(
            task_id="TASK-FW2-1",
            title="Chat page",
            acceptance="test -f frontend/apps/web/app/chat/page.tsx",
            source_file="test.md",
        )
        result = fd.grade_depth(card, frontend_dir=fe)
        assert result.depth_grade == "L2"

    def test_l3_has_logic(self, tmp_path: Path) -> None:
        """File with exports + state/effects logic -> L3."""
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/app/chat/page.tsx": textwrap.dedent("""\
                import { useState, useEffect } from "react";
                export default function ChatPage() {
                  const [msg, setMsg] = useState<string>("");
                  useEffect(() => {
                    fetch("/api/messages");
                  }, []);
                  return <div>{msg}</div>;
                }
            """),
            },
        )
        card = fd.TaskCardAC(
            task_id="TASK-FW2-1",
            title="Chat page",
            acceptance="test -f frontend/apps/web/app/chat/page.tsx",
            source_file="test.md",
        )
        result = fd.grade_depth(card, frontend_dir=fe)
        assert result.depth_grade == "L3"

    def test_l4_has_test(self, tmp_path: Path) -> None:
        """File with exports + logic + test file -> L4."""
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/app/chat/page.tsx": textwrap.dedent("""\
                import { useState, useEffect } from "react";
                export default function ChatPage() {
                  const [msg, setMsg] = useState<string>("");
                  useEffect(() => { fetch("/api"); }, []);
                  return <div>{msg}</div>;
                }
            """),
                "apps/web/app/chat/page.test.tsx": textwrap.dedent("""\
                import { render } from "@testing-library/react";
                import ChatPage from "./page";
                test("renders", () => { render(<ChatPage />); });
            """),
            },
        )
        card = fd.TaskCardAC(
            task_id="TASK-FW2-1",
            title="Chat page",
            acceptance="test -f frontend/apps/web/app/chat/page.tsx",
            source_file="test.md",
        )
        result = fd.grade_depth(card, frontend_dir=fe)
        assert result.depth_grade == "L4"
        assert result.has_test is True


# ---------------------------------------------------------------------------
# Security: Stub detection
# ---------------------------------------------------------------------------


class TestStubDetection:
    """Test stub/placeholder detection in production code."""

    def test_detects_placeholder_comment(self, tmp_path: Path) -> None:
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/app/chat/page.tsx": (
                    "// Placeholder: would call G2-6 3-step upload\nreturn crypto.randomUUID();\n"
                ),
            },
        )
        findings = fd.check_stubs(frontend_dir=fe)
        assert len(findings) >= 1
        assert any("Placeholder" in f.message or "randomUUID" in f.message for f in findings)

    def test_ignores_test_files(self, tmp_path: Path) -> None:
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/app/chat/page.test.tsx": "// Placeholder in test is OK\n",
            },
        )
        findings = fd.check_stubs(frontend_dir=fe)
        assert len(findings) == 0

    def test_clean_code_no_stubs(self, tmp_path: Path) -> None:
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/app/chat/page.tsx": (
                    "export default function ChatPage() {\n  return <div>Clean code</div>;\n}\n"
                ),
            },
        )
        findings = fd.check_stubs(frontend_dir=fe)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Security: Auth consistency
# ---------------------------------------------------------------------------


class TestAuthConsistency:
    """Test auth token key consistency detection."""

    def test_detects_key_mismatch(self, tmp_path: Path) -> None:
        """Login uses 'diyu_admin_token' but monitoring uses 'admin_token'."""
        fe = _make_frontend(
            tmp_path,
            {
                "apps/admin/app/login/page.tsx": (
                    'sessionStorage.setItem("diyu_admin_token", data.token);\n'
                ),
                "apps/admin/app/monitoring/page.tsx": (
                    'const token = sessionStorage.getItem("admin_token");\n'
                    'sessionStorage.removeItem("admin_token");\n'
                ),
            },
        )
        findings = fd.check_auth_consistency(frontend_dir=fe)
        assert len(findings) >= 1
        assert any(f.category == "auth_inconsistency" for f in findings)
        assert any(f.severity == "critical" for f in findings)

    def test_consistent_keys_ok(self, tmp_path: Path) -> None:
        """Same key used everywhere -> no findings."""
        fe = _make_frontend(
            tmp_path,
            {
                "apps/admin/app/login/page.tsx": (
                    'sessionStorage.setItem("diyu_admin_token", data.token);\n'
                ),
                "apps/admin/app/monitoring/page.tsx": (
                    'const token = sessionStorage.getItem("diyu_admin_token");\n'
                ),
            },
        )
        findings = fd.check_auth_consistency(frontend_dir=fe)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Security: XSS surfaces
# ---------------------------------------------------------------------------


class TestXSSSurfaces:
    """Test XSS surface detection."""

    def test_detects_dangerous_html_without_sanitize(self, tmp_path: Path) -> None:
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/components/content.tsx": (
                    "function Content({ html }) {\n"
                    "  return <div dangerouslySetInnerHTML={{ __html: html }} />;\n"
                    "}\n"
                ),
            },
        )
        findings = fd.check_xss_surfaces(frontend_dir=fe)
        assert any(f.category == "xss_surface" for f in findings)

    def test_no_finding_when_sanitize_present(self, tmp_path: Path) -> None:
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/components/content.tsx": (
                    'import { sanitizeHTML } from "@/lib/sanitize";\n'
                    "function Content({ html }) {\n"
                    "  const clean = sanitizeHTML(html);\n"
                    "  return <div dangerouslySetInnerHTML={{ __html: clean }} />;\n"
                    "}\n"
                ),
            },
        )
        findings = fd.check_xss_surfaces(frontend_dir=fe)
        xss = [f for f in findings if f.category == "xss_surface" and f.severity == "critical"]
        assert len(xss) == 0


# ---------------------------------------------------------------------------
# Security: Sanitize coverage
# ---------------------------------------------------------------------------


class TestSanitizeCoverage:
    """Test sanitize.ts existence and DOMPurify check."""

    def test_detects_missing_sanitize_ts(self, tmp_path: Path) -> None:
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/lib/placeholder.ts": "// no sanitize\n",
            },
        )
        findings = fd.check_sanitize_coverage(frontend_dir=fe)
        assert any(f.category == "missing_sanitize" for f in findings)

    def test_detects_sanitize_without_dompurify(self, tmp_path: Path) -> None:
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/lib/sanitize.ts": "export function clean(s: string) { return s; }\n",
            },
        )
        findings = fd.check_sanitize_coverage(frontend_dir=fe)
        assert any("DOMPurify" in f.message for f in findings)

    def test_valid_sanitize_ts(self, tmp_path: Path) -> None:
        fe = _make_frontend(
            tmp_path,
            {
                "apps/web/lib/sanitize.ts": (
                    'import DOMPurify from "dompurify";\n'
                    "export function sanitizeHTML(s: string) { return DOMPurify.sanitize(s); }\n"
                ),
            },
        )
        findings = fd.check_sanitize_coverage(frontend_dir=fe)
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


class TestReportGeneration:
    """Test report structure and status."""

    def test_pass_status(self) -> None:
        results = [
            fd.DepthResult("TASK-1", "L3"),
            fd.DepthResult("TASK-2", "L4", has_test=True),
        ]
        report = fd.generate_report(results, [])
        assert report["status"] == "PASS"
        assert report["summary"]["total_task_cards"] == 2

    def test_fail_on_critical_security(self) -> None:
        results = [fd.DepthResult("TASK-1", "L3")]
        findings = [
            fd.SecurityFinding("auth_inconsistency", "critical", "a.tsx", 1, "mismatch"),
        ]
        report = fd.generate_report(results, findings)
        assert report["status"] == "FAIL"

    def test_warn_on_security_findings(self) -> None:
        results = [fd.DepthResult("TASK-1", "L3")]
        findings = [
            fd.SecurityFinding("stub", "warning", "a.tsx", 1, "placeholder"),
        ]
        report = fd.generate_report(results, findings)
        assert report["status"] == "WARN"

    def test_verbose_includes_all_results(self) -> None:
        results = [fd.DepthResult("TASK-1", "L3")]
        report = fd.generate_report(results, [], verbose=True)
        assert "all_results" in report
        assert report["all_results"][0]["task_id"] == "TASK-1"

    def test_report_has_findings_key(self) -> None:
        """Report must include a standardized 'findings' array."""
        results = [fd.DepthResult("TASK-1", "L3")]
        sf = [fd.SecurityFinding("stub", "warning", "a.tsx", 1, "placeholder")]
        report = fd.generate_report(results, sf)
        assert "findings" in report
        assert len(report["findings"]) == len(report["security_findings"])

    def test_findings_equals_security_findings(self) -> None:
        """findings array must mirror security_findings content."""
        results = [fd.DepthResult("TASK-1", "L3")]
        report = fd.generate_report(results, [])
        assert report["findings"] == report["security_findings"]

    def test_summary_has_findings_count(self) -> None:
        """summary must include a findings_count field."""
        results = [fd.DepthResult("TASK-1", "L3")]
        sf = [fd.SecurityFinding("stub", "warning", "a.tsx", 1, "placeholder")]
        report = fd.generate_report(results, sf)
        assert report["summary"]["findings_count"] == 1


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
        assert "security_findings" in report

    def test_summary_has_required_fields(self) -> None:
        result = _run_script("--json")
        report = json.loads(result.stdout)
        s = report["summary"]
        assert "total_task_cards" in s
        assert "grade_distribution" in s
        assert "security_findings_count" in s

    def test_detects_chat_upload_stub(self) -> None:
        """Validation fixture: must detect handleUpload stub (plan line 336)."""
        result = _run_script("--json")
        report = json.loads(result.stdout)
        stubs = [f for f in report["security_findings"] if f["category"] == "stub"]
        stub_files = [f["file"] for f in stubs]
        assert any("chat/page.tsx" in f for f in stub_files), (
            f"handleUpload stub not detected in chat/page.tsx. Found stubs: {stub_files}"
        )

    def test_detects_auth_token_inconsistency(self) -> None:
        """Validation fixture: must detect admin_token vs diyu_admin_token (plan line 336)."""
        result = _run_script("--json")
        report = json.loads(result.stdout)
        auth_findings = [
            f for f in report["security_findings"] if f["category"] == "auth_inconsistency"
        ]
        assert len(auth_findings) >= 1, "Auth token key inconsistency not detected"

    def test_human_readable_output(self) -> None:
        result = _run_script()
        assert result.returncode in (0, 1)
        assert "Frontend Depth Audit" in result.stdout
        assert "Grade distribution" in result.stdout
