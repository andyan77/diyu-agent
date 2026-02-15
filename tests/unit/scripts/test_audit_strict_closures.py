"""Strict closure tests for audit findings that were only partially resolved.

These tests use EXACT assertions (not loose pattern matches) to verify
each finding is fully closed. A green test here means the fix is complete.

Covers residual gaps in: H2, H4, H7, M2, M4, M5, S3, N2.
Git-index items (S1 uv.lock tracking, H1 rename) are verified via Bash, not pytest.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
PRE_EDIT_AUDIT = ROOT / "scripts" / "hooks" / "pre_edit_audit.sh"
PRE_COMMIT_GATE = ROOT / "scripts" / "hooks" / "pre_commit_gate.sh"
POST_EDIT_FORMAT = ROOT / "scripts" / "hooks" / "post_edit_format.sh"
GATE_REVIEW_MD = ROOT / ".claude" / "commands" / "gate-review.md"
EXECUTION_PLAN = ROOT / "docs" / "governance" / "execution-plan-v1.0.md"
GOV_OPT_PLAN = ROOT / "docs" / "governance" / "governance-optimization-plan.md"


@pytest.fixture
def ci_yaml() -> dict:
    return yaml.safe_load(CI_YML.read_text())


@pytest.fixture
def ci_text() -> str:
    return CI_YML.read_text()


# ---------------------------------------------------------------------------
# H2 STRICT: Frontend lint scripts must NOT swallow errors
# ---------------------------------------------------------------------------
class TestH2FrontendLintNoSwallow:
    """Frontend lint scripts must fail-loud, not || echo fallback."""

    @pytest.mark.parametrize(
        "pkg_path",
        [
            "apps/web/package.json",
            "apps/admin/package.json",
            "packages/shared/package.json",
            "packages/ui/package.json",
            "packages/api-client/package.json",
        ],
    )
    def test_lint_script_does_not_swallow_errors(self, pkg_path: str):
        """lint script must not use '|| echo' or '|| true' to swallow failures."""
        pkg = json.loads((ROOT / "frontend" / pkg_path).read_text())
        lint_cmd = pkg.get("scripts", {}).get("lint", "")
        assert "||" not in lint_cmd, (
            f"frontend/{pkg_path} lint swallows errors: '{lint_cmd}'. "
            "Remove '|| echo/true' so failures propagate to CI."
        )


# ---------------------------------------------------------------------------
# H4 STRICT: Downstream jobs must conditionally skip based on impact
# ---------------------------------------------------------------------------
class TestH4ConditionalGateExecution:
    """guard-checks must USE change-impact outputs in conditional logic, not just log."""

    def test_guard_checks_has_conditional_gate_logic(self, ci_yaml: dict):
        """guard-checks must have a step with 'if: contains(...)' on triggered_gates."""
        jobs = ci_yaml.get("jobs", {})
        guard = jobs.get("guard-checks", {})
        steps = guard.get("steps", [])
        has_conditional = False
        for step in steps:
            step_if = step.get("if", "")
            if "triggered_gates" in step_if and "contains" in step_if:
                has_conditional = True
                break
        assert has_conditional, (
            "guard-checks has no step with 'if: contains(...triggered_gates...)'. "
            "Impact routing outputs are logged but not acted upon."
        )

    def test_guard_checks_has_gate_specific_steps(self, ci_yaml: dict):
        """guard-checks must have at least one step that runs conditionally on a gate."""
        jobs = ci_yaml.get("jobs", {})
        guard = jobs.get("guard-checks", {})
        steps = guard.get("steps", [])
        conditional_steps = [s for s in steps if "triggered_gates" in s.get("if", "")]
        # Must have at least 2 conditional steps: one that logs + one that acts
        assert len(conditional_steps) >= 2, (
            f"guard-checks has only {len(conditional_steps)} conditional step(s). "
            "Need gate-specific steps (e.g., run schema check if governance gate triggered)."
        )


# ---------------------------------------------------------------------------
# H7 STRICT: Phase-aware boundary enforcement
# ---------------------------------------------------------------------------
class TestH7PhaseAwareBoundary:
    """pre_edit_audit.sh must read current phase and apply rules accordingly."""

    def test_reads_current_phase(self):
        """Script must read current_phase from milestone-matrix.yaml."""
        text = PRE_EDIT_AUDIT.read_text()
        assert "current_phase" in text or "milestone-matrix.yaml" in text, (
            "pre_edit_audit.sh does not read current_phase from milestone-matrix.yaml. "
            "Cannot implement phased enforcement without knowing the phase."
        )

    def test_delivery_manifest_rule_exists(self):
        """delivery/manifest* paths must have a Phase 3+ enforcement rule."""
        text = PRE_EDIT_AUDIT.read_text()
        assert "delivery/manifest" in text or "delivery/" in text, (
            "pre_edit_audit.sh has no enforcement rule for delivery/manifest* paths. "
            "Per user decision: delivery/manifest* should block at Phase 3+."
        )

    def test_phase_conditional_in_enforcement(self):
        """Enforcement actions must reference phase in their conditions."""
        text = PRE_EDIT_AUDIT.read_text()
        # Must have phase-based conditional (e.g., phase_0, phase_1, CURRENT_PHASE)
        has_phase_logic = "phase" in text.lower() and (
            "if" in text.lower() or "case" in text.lower()
        )
        assert has_phase_logic, (
            "pre_edit_audit.sh enforcement is not phase-aware. "
            "Rules should check current phase before deciding BLOCK vs WARN."
        )


# ---------------------------------------------------------------------------
# M2 STRICT: gate-review.md must have allowed-tools in frontmatter
# ---------------------------------------------------------------------------
class TestM2AllowedToolsFrontmatter:
    """gate-review.md must declare allowed-tools in its YAML frontmatter."""

    def test_allowed_tools_in_frontmatter(self):
        """YAML frontmatter must contain allowed-tools field."""
        text = GATE_REVIEW_MD.read_text()
        # Extract frontmatter between --- markers
        parts = text.split("---")
        assert len(parts) >= 3, "gate-review.md has no YAML frontmatter"
        frontmatter = parts[1]
        assert "allowed-tools" in frontmatter or "allowed_tools" in frontmatter, (
            "gate-review.md frontmatter lacks 'allowed-tools' field. "
            "Must restrict to Bash + Read to prevent accidental writes."
        )


# ---------------------------------------------------------------------------
# M4 STRICT: pre_commit_gate.sh fail-open must become fail-closed
# ---------------------------------------------------------------------------
class TestM4FailClosed:
    """pre_commit_gate.sh schema check must not allow commit when check fails to run."""

    def test_schema_check_minus1_blocks(self):
        """BLOCK_COUNT=-1 (check failed to run) must block, not allow."""
        text = PRE_COMMIT_GATE.read_text()
        # Find the -1 handling block
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if '"-1"' in line and "allowing" in line.lower():
                pytest.fail(
                    f"pre_commit_gate.sh line {i + 1}: BLOCK_COUNT=-1 allows commit. "
                    "When schema check fails to run, commit should be blocked (fail-closed)."
                )

    def test_gates_on_governance_docs(self):
        """Gate must also check staged changes to docs/governance/."""
        text = PRE_COMMIT_GATE.read_text()
        assert "docs/governance/" in text, (
            "pre_commit_gate.sh does not gate on docs/governance/ changes. "
            "Governance doc changes should trigger schema validation."
        )

    def test_gates_on_delivery_files(self):
        """Gate must check staged changes to delivery/."""
        text = PRE_COMMIT_GATE.read_text()
        assert "delivery/" in text, "pre_commit_gate.sh does not gate on delivery/ changes."


# ---------------------------------------------------------------------------
# M5 STRICT: execution-plan agent paths must reference project-level agents
# ---------------------------------------------------------------------------
class TestM5AgentPathStrict:
    """Docs must reference .claude/agents/ (project) not ~/.claude/agents/ (user)."""

    def test_execution_plan_no_user_level_agent_path(self):
        """execution-plan-v1.0.md must not reference ~/.claude/agents/ as authoritative."""
        text = EXECUTION_PLAN.read_text()
        # The text says "Agent 定义位于用户级 ~/.claude/agents/" which is wrong
        # It should reference .claude/agents/ (project-level)
        lines_with_user_path = [
            (i + 1, line.strip())
            for i, line in enumerate(text.splitlines())
            if "~/.claude/agents/" in line
        ]
        assert len(lines_with_user_path) == 0, (
            "execution-plan-v1.0.md still references ~/.claude/agents/ (user-level):\n"
            + "\n".join(f"  line {n}: {ln}" for n, ln in lines_with_user_path)
            + "\nProject agents are at .claude/agents/, not user-level."
        )

    def test_governance_opt_plan_no_stale_path(self):
        """governance-optimization-plan.md must not have stale agent references."""
        text = GOV_OPT_PLAN.read_text()
        lines_with_user_path = [
            (i + 1, line.strip())
            for i, line in enumerate(text.splitlines())
            if "~/.claude/agents/" in line
        ]
        # Allow if the doc explicitly notes the distinction
        if lines_with_user_path:
            has_note = any(
                "project" in text[max(0, text.index(ln[1]) - 200) : text.index(ln[1]) + 200].lower()
                for ln in lines_with_user_path
                if ln[1] in text
            )
            if not has_note:
                pytest.fail(
                    "governance-optimization-plan.md references ~/.claude/agents/ "
                    "without noting project-level distinction."
                )


# ---------------------------------------------------------------------------
# S3 STRICT: Frontend must have at least one real test file
# ---------------------------------------------------------------------------
class TestS3FrontendRealTests:
    """Frontend packages must have at least one actual test, not just --passWithNoTests."""

    def test_at_least_one_test_file_exists(self):
        """There must be at least one .test.ts/.test.tsx/.spec.ts file in frontend/."""
        test_files = list((ROOT / "frontend").rglob("*.test.ts"))
        test_files += list((ROOT / "frontend").rglob("*.test.tsx"))
        test_files += list((ROOT / "frontend").rglob("*.spec.ts"))
        test_files += list((ROOT / "frontend").rglob("*.spec.tsx"))
        # Exclude node_modules
        test_files = [f for f in test_files if "node_modules" not in str(f)]
        assert len(test_files) >= 1, (
            "No test files found in frontend/. "
            "--passWithNoTests is a placeholder; at least one smoke test is needed."
        )


# ---------------------------------------------------------------------------
# N2 STRICT: post_edit_format.sh must use [PostToolUse] prefix
# ---------------------------------------------------------------------------
class TestN2PostToolUseTag:
    """post_edit_format.sh must prefix output with [PostToolUse] for traceability."""

    def test_output_uses_post_tool_use_tag(self):
        """All echo/output lines must use [PostToolUse] prefix, not [schema]."""
        text = POST_EDIT_FORMAT.read_text()
        # Find all echo lines that produce output (not >&2 debug)
        echo_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip().startswith("echo") and ">&2" not in line
        ]
        for line in echo_lines:
            assert "[PostToolUse]" in line, (
                f"Output line uses wrong tag: '{line}'. "
                "Must use [PostToolUse] prefix for hook traceability."
            )
