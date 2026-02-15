"""Regression tests for GAP audit findings.

Ensures previously identified gaps remain closed after code changes.
Each test is named after the GAP ID for traceability.
"""

import json
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# GAP-H3: Security reviewer read-only
# ---------------------------------------------------------------------------


class TestGapH3SecurityReviewerReadOnly:
    def test_no_write_edit_tools(self) -> None:
        path = Path(".claude/agents/diyu-security-reviewer.md")
        if not path.exists():
            pytest.skip("agent file not found")
        text = path.read_text()
        end = text.index("---", 3)
        fm = yaml.safe_load(text[3:end])
        tools = set(fm.get("tools", []))
        assert "Write" not in tools, "Security reviewer must not have Write tool"
        assert "Edit" not in tools, "Security reviewer must not have Edit tool"


# ---------------------------------------------------------------------------
# GAP-M1: Session ID never "unknown"
# ---------------------------------------------------------------------------


class TestGapM1SessionTracking:
    def test_pre_edit_audit_no_unknown_fallback(self) -> None:
        path = Path("scripts/hooks/pre_edit_audit.sh")
        if not path.exists():
            pytest.skip("hook not found")
        text = path.read_text()
        # Must not have session=unknown as literal default
        assert "SESSION_ID:-unknown" not in text, (
            "pre_edit_audit.sh must not default session to 'unknown'"
        )

    def test_post_tool_failure_log_no_unknown_session(self) -> None:
        path = Path("scripts/hooks/post_tool_failure_log.sh")
        if not path.exists():
            pytest.skip("hook not found")
        text = path.read_text()
        assert "'session': 'unknown'" not in text, (
            "post_tool_failure_log.sh must not hardcode session='unknown'"
        )

    def test_pre_commit_gate_writes_audit_log(self) -> None:
        path = Path("scripts/hooks/pre_commit_gate.sh")
        if not path.exists():
            pytest.skip("hook not found")
        text = path.read_text()
        assert "LOGFILE" in text, "pre_commit_gate must write to audit LOGFILE"
        assert "session" in text.lower(), "pre_commit_gate must track session"


# ---------------------------------------------------------------------------
# GAP-M2: Role isolation enforced
# ---------------------------------------------------------------------------


class TestGapM2RoleIsolation:
    @pytest.mark.parametrize("step", ["W1", "W2", "W3", "W4"])
    def test_workflow_script_checks_role(self, step: str) -> None:
        script_map = {
            "W1": "run_w1_schema_normalization.sh",
            "W2": "run_w2_traceability_link.sh",
            "W3": "run_w3_acceptance_normalizer.sh",
            "W4": "run_w4_evidence_gate.sh",
        }
        path = Path(f".claude/skills/taskcard-governance/scripts/{script_map[step]}")
        if not path.exists():
            pytest.skip(f"{path} not found")
        text = path.read_text()
        assert "WORKFLOW_ROLE" in text, f"{step} script must reference WORKFLOW_ROLE"
        assert f'!= "{step}"' in text or f'!= "{step}"' not in text, (
            f"{step} script must check role matches"
        )

    def test_run_all_passes_workflow_role(self) -> None:
        path = Path(".claude/skills/taskcard-governance/scripts/run_all.sh")
        if not path.exists():
            pytest.skip("run_all.sh not found")
        text = path.read_text()
        assert "WORKFLOW_ROLE=" in text, "run_all.sh must set WORKFLOW_ROLE per step"


# ---------------------------------------------------------------------------
# GAP-M5: W4 trap-based failure handling
# ---------------------------------------------------------------------------


class TestGapM5W4FailureHandling:
    def test_w4_has_trap(self) -> None:
        path = Path(".claude/skills/taskcard-governance/scripts/run_w4_evidence_gate.sh")
        if not path.exists():
            pytest.skip("W4 script not found")
        text = path.read_text()
        assert "trap " in text, "W4 must use trap for failure handling"
        assert "output.json" in text, "W4 trap must ensure output.json exists"
        assert "failure.md" in text, "W4 trap must ensure failure.md exists"


# ---------------------------------------------------------------------------
# GAP-M6: verify_phase.py --archive
# ---------------------------------------------------------------------------


class TestGapM6EvidenceArchival:
    def test_verify_phase_has_archive_flag(self) -> None:
        path = Path("scripts/verify_phase.py")
        if not path.exists():
            pytest.skip("verify_phase.py not found")
        text = path.read_text()
        assert "--archive" in text, "verify_phase.py must support --archive flag"
        assert "archive_report" in text, "verify_phase.py must have archive_report function"


# ---------------------------------------------------------------------------
# GAP-M8: PR template has risk score fields
# ---------------------------------------------------------------------------


class TestGapM8PRTemplate:
    def test_pr_template_has_risk_fields(self) -> None:
        path = Path(".github/PULL_REQUEST_TEMPLATE.md")
        if not path.exists():
            pytest.skip("PR template not found")
        text = path.read_text()
        assert "Risk Score" in text, "PR template must have Risk Score field"
        assert "Triggered Gates" in text, "PR template must have Triggered Gates field"
        assert "risk_scorer.sh" in text, "PR template must reference risk_scorer.sh"


# ---------------------------------------------------------------------------
# GAP-M10: Permissions in settings.json
# ---------------------------------------------------------------------------


class TestGapM10Permissions:
    def test_settings_has_permissions(self) -> None:
        path = Path(".claude/settings.json")
        if not path.exists():
            pytest.skip("settings.json not found")
        data = json.loads(path.read_text())
        assert "permissions" in data, "settings.json must have permissions key"
        assert "allow" in data["permissions"], "permissions must have allow list"
        assert "deny" in data["permissions"], "permissions must have deny list"


# ---------------------------------------------------------------------------
# GAP-M11: Hook renamed from post_edit_format to post_edit_schema_check
# ---------------------------------------------------------------------------


class TestGapM11HookNaming:
    def test_new_hook_exists(self) -> None:
        path = Path("scripts/hooks/post_edit_schema_check.sh")
        assert path.exists(), "post_edit_schema_check.sh must exist"

    def test_settings_references_new_hook(self) -> None:
        path = Path(".claude/settings.json")
        if not path.exists():
            pytest.skip("settings.json not found")
        text = path.read_text()
        assert "post_edit_schema_check.sh" in text, (
            "settings.json must reference post_edit_schema_check.sh"
        )


# ---------------------------------------------------------------------------
# GAP-H2: W2 no grep fallback
# ---------------------------------------------------------------------------


class TestGapH2NoGrepFallback:
    def test_w2_no_grep_fallback_default(self) -> None:
        path = Path(".claude/skills/taskcard-governance/scripts/run_w2_traceability_link.sh")
        if not path.exists():
            pytest.skip("W2 script not found")
        text = path.read_text()
        assert "grep-fallback" not in text or "FORBIDDEN" in text, (
            "W2 must not use grep-fallback as default method"
        )
        assert "fallback-failed" in text, "W2 must report fallback-failed when json-parser fails"
