"""Tests for residual audit findings from the merge review.

TDD RED phase: These tests verify the remaining fixes for:
  H2 regression: apps/web+admin lint must not crash when ESLint absent
  H4 residual:   CI gate name mapping must match router output names
  M1:            Hook commands must use defensive path resolution
  M5 residual:   governance-optimization-plan Stage 3 must not be "Pending"
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
SETTINGS_JSON = ROOT / ".claude" / "settings.json"
GOV_OPT_PLAN = ROOT / "docs" / "governance" / "governance-optimization-plan.md"
CHANGE_IMPACT_ROUTER = ROOT / "scripts" / "change_impact_router.sh"


@pytest.fixture
def ci_yaml() -> dict:
    return yaml.safe_load(CI_YML.read_text())


@pytest.fixture
def ci_text() -> str:
    return CI_YML.read_text()


# ---------------------------------------------------------------------------
# H2 RESIDUAL: Frontend lint must not crash CI (Phase 0 tolerance)
# ---------------------------------------------------------------------------
class TestH2FrontendLintNoCrash:
    """All frontend lint scripts must either run a real linter or use echo placeholder.

    They must NEVER use '|| echo' to swallow real lint errors (original H2 issue),
    AND they must not invoke a linter that is not installed (regression).
    Phase 0 packages without a linter should use 'echo' placeholder.
    """

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
    def test_lint_script_no_error_swallowing(self, pkg_path: str):
        """lint script must not use '|| echo' or '|| true' to swallow failures."""
        pkg = json.loads((ROOT / "frontend" / pkg_path).read_text())
        lint_cmd = pkg.get("scripts", {}).get("lint", "")
        assert "||" not in lint_cmd, (
            f"frontend/{pkg_path} lint swallows errors: '{lint_cmd}'. "
            "Remove '|| echo/true' so failures propagate to CI."
        )

    @pytest.mark.parametrize(
        "pkg_path",
        [
            "apps/web/package.json",
            "apps/admin/package.json",
        ],
    )
    def test_apps_lint_script_is_viable(self, pkg_path: str):
        """apps/web and apps/admin lint must use echo placeholder if ESLint not installed."""
        pkg_dir = ROOT / "frontend" / Path(pkg_path).parent
        pkg = json.loads((ROOT / "frontend" / pkg_path).read_text())
        lint_cmd = pkg.get("scripts", {}).get("lint", "")

        # Check if eslint is available as a dependency
        has_eslint = "eslint" in pkg.get("devDependencies", {}) or "eslint" in pkg.get(
            "dependencies", {}
        )
        eslint_installed = (pkg_dir / "node_modules" / ".bin" / "eslint").exists() or (
            ROOT / "frontend" / "node_modules" / ".bin" / "eslint"
        ).exists()

        if not has_eslint and not eslint_installed:
            # No ESLint available: lint script must be a placeholder (echo), not a real linter call
            assert lint_cmd.startswith("echo"), (
                f"frontend/{pkg_path} lint invokes '{lint_cmd}' but ESLint is not "
                "declared as a dependency. Use echo placeholder until FW0-6 installs ESLint."
            )


# ---------------------------------------------------------------------------
# H4 RESIDUAL: CI gate conditions must match router output names
# ---------------------------------------------------------------------------
class TestH4GateNameMapping:
    """CI 'contains(triggered_gates, ...)' conditions must use the exact gate
    names produced by change_impact_router.sh, not invented aliases."""

    def _extract_router_gate_names(self) -> set[str]:
        """Parse all gate names from change_impact_router.sh add_gate calls."""
        text = CHANGE_IMPACT_ROUTER.read_text()
        # Pattern: add_gate "gate_name" <phase>
        return set(re.findall(r'add_gate\s+"([^"]+)"', text))

    def _extract_ci_gate_conditions(self) -> list[tuple[int, str]]:
        """Extract all triggered_gates contains() values from ci.yml."""
        text = CI_YML.read_text()
        results = []
        for i, line in enumerate(text.splitlines(), 1):
            match = re.search(r"contains\(.*triggered_gates.*,\s*'([^']+)'\)", line)
            if match:
                results.append((i, match.group(1)))
        return results

    def test_all_ci_gate_names_exist_in_router(self):
        """Every gate name checked in CI must exist in the router's add_gate calls."""
        router_names = self._extract_router_gate_names()
        ci_conditions = self._extract_ci_gate_conditions()

        assert len(ci_conditions) > 0, "No triggered_gates conditions found in ci.yml"

        mismatches = []
        for lineno, gate_name in ci_conditions:
            if gate_name not in router_names:
                mismatches.append(
                    f"  ci.yml:{lineno} checks '{gate_name}' but router only produces: "
                    f"{sorted(router_names)}"
                )

        assert len(mismatches) == 0, (
            "CI gate conditions do not match router output names:\n"
            + "\n".join(mismatches)
            + "\n\nFix: use exact gate names from change_impact_router.sh in ci.yml conditions."
        )


# ---------------------------------------------------------------------------
# M1: Hook commands must handle path resolution defensively
# ---------------------------------------------------------------------------
class TestM1HookPathResolution:
    """Hook commands in .claude/settings.json must resolve project root defensively."""

    def test_hooks_use_defensive_path(self):
        """All hook commands must either use absolute paths or cd to project root first."""
        settings = json.loads(SETTINGS_JSON.read_text())
        hooks = settings.get("hooks", {})
        violations = []

        for event_type, matchers in hooks.items():
            for matcher_block in matchers:
                for hook in matcher_block.get("hooks", []):
                    cmd = hook.get("command", "")
                    if not cmd:
                        continue
                    # Check: command must use CLAUDE_PROJECT_DIR or absolute path, or
                    # have a cd prefix that resolves to project root
                    has_absolute = cmd.startswith("/")
                    has_project_dir = "CLAUDE_PROJECT_DIR" in cmd
                    has_cd_prefix = "cd " in cmd.split("&&")[0] if "&&" in cmd else False

                    if not (has_absolute or has_project_dir or has_cd_prefix):
                        violations.append(f"  {event_type}: '{cmd}'")

        assert len(violations) == 0, (
            "Hook commands use bare relative paths without defensive resolution:\n"
            + "\n".join(violations)
            + '\nFix: prepend cd "${CLAUDE_PROJECT_DIR:-.}" && to each command.'
        )


# ---------------------------------------------------------------------------
# M5 RESIDUAL: Stage 3 must not still say "Pending" when artifacts exist
# ---------------------------------------------------------------------------
class TestM5Stage3StatusUpdated:
    """governance-optimization-plan.md Stage 3 row must reflect actual progress."""

    def test_stage3_not_pending(self):
        """Stage 3 row in the roadmap table must not say 'Pending' if artifacts exist."""
        text = GOV_OPT_PLAN.read_text()
        # Find the Stage 3 SKILLS line
        for i, line in enumerate(text.splitlines(), 1):
            if "Stage 3" in line and "SKILLS" in line:
                assert "Pending" not in line, (
                    f"governance-optimization-plan.md line {i}: "
                    "Stage 3 SKILLS still marked 'Pending' but "
                    ".claude/skills/, .claude/commands/, "
                    ".claude/settings.json already exist. "
                    "Update to 'In Progress' or 'Partial'."
                )
                return
        pytest.fail("Could not find Stage 3 SKILLS row in governance-optimization-plan.md")
