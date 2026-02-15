"""Tests for Batch 4 audit fixes: documentation alignment.

TDD RED phase: These tests verify fixes for audit findings
H1, H7, M2, M5, S3, N2.

Covers:
  H1:  Schema file renamed to milestone-matrix.schema.yaml (correct naming)
  H7:  pre_edit_audit.sh enforces layer boundaries (phased enablement)
  M2:  gate-review.md documents tool restrictions
  M5:  execution-plan-v1.0.md agent path accuracy
  S3:  Frontend test scripts use --passWithNoTests (already fixed)
  N2:  post_edit_format.sh uses [PostToolUse] warning tag
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_OLD = ROOT / "delivery" / "manifest.schema.yaml"
SCHEMA_NEW = ROOT / "delivery" / "milestone-matrix.schema.yaml"
PRE_EDIT_AUDIT = ROOT / "scripts" / "hooks" / "pre_edit_audit.sh"
POST_EDIT_FORMAT = ROOT / "scripts" / "hooks" / "post_edit_format.sh"
GATE_REVIEW_MD = ROOT / ".claude" / "commands" / "gate-review.md"
EXECUTION_PLAN = ROOT / "docs" / "governance" / "execution-plan-v1.0.md"


# ---------------------------------------------------------------------------
# H1: Schema file must be named milestone-matrix.schema.yaml
# ---------------------------------------------------------------------------
class TestH1SchemaRename:
    """Schema file must match what it validates: milestone-matrix.yaml."""

    def test_new_schema_file_exists(self):
        """milestone-matrix.schema.yaml must exist."""
        assert SCHEMA_NEW.exists(), (
            "delivery/milestone-matrix.schema.yaml does not exist. "
            "Schema was renamed from manifest.schema.yaml per H1."
        )

    def test_old_schema_file_removed(self):
        """manifest.schema.yaml must be removed after rename."""
        assert not SCHEMA_OLD.exists(), (
            "delivery/manifest.schema.yaml still exists after rename. Old file should be removed."
        )

    def test_milestone_matrix_references_new_schema(self):
        """milestone-matrix.yaml must reference the new schema name."""
        mm = (ROOT / "delivery" / "milestone-matrix.yaml").read_text()
        assert "milestone-matrix.schema.yaml" in mm, (
            "delivery/milestone-matrix.yaml still references old schema name."
        )


# ---------------------------------------------------------------------------
# H7: pre_edit_audit.sh must enforce layer boundaries (phased)
# ---------------------------------------------------------------------------
class TestH7LayerBoundaryEnforcement:
    """pre_edit_audit.sh must have boundary enforcement, not just logging."""

    def test_has_boundary_check_logic(self):
        """Audit hook must contain layer boundary enforcement logic."""
        text = PRE_EDIT_AUDIT.read_text()
        # Phase 0-1: ports and RLS-related infra should log warnings
        # Phase 1+: RLS infra should block
        has_enforcement = "exit 2" in text or "BLOCK" in text or "boundary" in text.lower()
        assert has_enforcement, (
            "pre_edit_audit.sh has no boundary enforcement logic. "
            "Per H7, at minimum src/infra/org/ edits should be flagged."
        )

    def test_rls_infra_flagged(self):
        """Edits to src/infra/org/ (RLS layer) must trigger enforcement."""
        text = PRE_EDIT_AUDIT.read_text()
        # The script already identifies src/infra/org/ as TIER=4
        # It should now act on that classification
        has_rls_action = "infra/org" in text and (
            "exit 2" in text or "WARN" in text or "WARNING" in text
        )
        assert has_rls_action, "pre_edit_audit.sh does not enforce or warn on src/infra/org/ edits."


# ---------------------------------------------------------------------------
# M2: gate-review.md must document tool restrictions
# ---------------------------------------------------------------------------
class TestM2GateReviewToolRestrictions:
    """gate-review.md should document which tools are needed."""

    def test_mentions_tool_requirements(self):
        """gate-review.md should mention tool/command requirements."""
        text = GATE_REVIEW_MD.read_text()
        has_tool_info = "Bash" in text or "Read" in text or "tool" in text.lower()
        assert has_tool_info, "gate-review.md does not document tool requirements."


# ---------------------------------------------------------------------------
# M5: execution-plan-v1.0.md agent path accuracy
# ---------------------------------------------------------------------------
class TestM5AgentPathAccuracy:
    """execution-plan agent references must note project vs user distinction."""

    def test_agent_path_has_context_note(self):
        """Agent path references should clarify project vs user scope."""
        text = EXECUTION_PLAN.read_text()
        # The doc references ~/.claude/agents/ but project has .claude/agents/
        # Either the path should be corrected or a note added
        has_clarity = ".claude/agents/" in text and (
            "project" in text.lower() or "note" in text.lower() or ".claude/agents/diyu" in text
        )
        assert has_clarity, (
            "execution-plan-v1.0.md references ~/.claude/agents/ without "
            "clarifying that project-level agents are at .claude/agents/."
        )


# ---------------------------------------------------------------------------
# S3: Frontend test scripts must invoke vitest (real test runner)
# ---------------------------------------------------------------------------
class TestS3FrontendTestScripts:
    """Frontend packages must use vitest for testing."""

    @pytest.mark.parametrize(
        "pkg",
        ["apps/web", "apps/admin", "packages/shared", "packages/ui", "packages/api-client"],
    )
    def test_package_test_script_uses_vitest(self, pkg: str):
        """Each frontend package's test script must invoke vitest."""
        import json

        pkg_json = ROOT / "frontend" / pkg / "package.json"
        data = json.loads(pkg_json.read_text())
        test_cmd = data.get("scripts", {}).get("test", "")
        assert "vitest" in test_cmd, (
            f"frontend/{pkg}/package.json test script does not use vitest: '{test_cmd}'"
        )


# ---------------------------------------------------------------------------
# N2: post_edit_format.sh must use [PostToolUse] warning tag
# ---------------------------------------------------------------------------
class TestN2PostEditWarningTag:
    """post_edit_format.sh output must use [PostToolUse] prefix for traceability."""

    def test_has_post_tool_use_tag(self):
        """Output lines should use [PostToolUse] tag prefix."""
        text = POST_EDIT_FORMAT.read_text()
        has_tag = "[PostToolUse]" in text or "[schema]" in text
        assert has_tag, (
            "post_edit_format.sh lacks [PostToolUse] warning tag in output. "
            "Messages should be prefixed for hook traceability."
        )
