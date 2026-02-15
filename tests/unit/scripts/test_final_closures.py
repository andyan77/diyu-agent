"""Tests for final closure of partially-resolved audit findings.

TDD RED phase: These tests verify full closure for:
  H2 full closure: All 5 frontend lint scripts must invoke a real linter
  H4 full closure: CI must consume ALL gates from the router
  S3 full closure: All 5 frontend packages must have real test files
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import ClassVar

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
CHANGE_IMPACT_ROUTER = ROOT / "scripts" / "change_impact_router.sh"
FRONTEND = ROOT / "frontend"


@pytest.fixture
def ci_yaml() -> dict:
    return yaml.safe_load(CI_YML.read_text())


# -------------------------------------------------------------------
# H2 FULL CLOSURE: All 5 lint scripts must run a real linter
# -------------------------------------------------------------------
class TestH2RealLinter:
    """Every frontend package must run a real linter, not an echo stub."""

    ALL_PACKAGES: ClassVar[list[str]] = [
        "apps/web/package.json",
        "apps/admin/package.json",
        "packages/shared/package.json",
        "packages/ui/package.json",
        "packages/api-client/package.json",
    ]

    @pytest.mark.parametrize("pkg_path", ALL_PACKAGES)
    def test_lint_script_is_not_echo_stub(self, pkg_path: str):
        """lint script must not be an echo placeholder."""
        pkg = json.loads((FRONTEND / pkg_path).read_text())
        lint_cmd = pkg.get("scripts", {}).get("lint", "")
        assert not lint_cmd.startswith("echo"), (
            f"frontend/{pkg_path} lint is still a placeholder: "
            f"'{lint_cmd}'. Must invoke a real linter."
        )

    @pytest.mark.parametrize("pkg_path", ALL_PACKAGES)
    def test_lint_script_no_error_swallowing(self, pkg_path: str):
        """lint script must not use || to swallow errors."""
        pkg = json.loads((FRONTEND / pkg_path).read_text())
        lint_cmd = pkg.get("scripts", {}).get("lint", "")
        assert "||" not in lint_cmd, f"frontend/{pkg_path} lint swallows errors: '{lint_cmd}'."

    def test_eslint_is_a_declared_dependency(self):
        """eslint must be declared somewhere in the monorepo deps."""
        root_pkg = json.loads((FRONTEND / "package.json").read_text())
        root_dev = root_pkg.get("devDependencies", {})
        root_dep = root_pkg.get("dependencies", {})

        # Check root-level or any package-level
        found = "eslint" in root_dev or "eslint" in root_dep
        if not found:
            for pkg_path in self.ALL_PACKAGES:
                pkg = json.loads((FRONTEND / pkg_path).read_text())
                if "eslint" in pkg.get("devDependencies", {}) or "eslint" in pkg.get(
                    "dependencies", {}
                ):
                    found = True
                    break

        assert found, (
            "eslint is not declared as a dependency in any "
            "frontend package.json. Install it to enable real linting."
        )


# -------------------------------------------------------------------
# H4 FULL CLOSURE: CI must consume ALL router gates
# -------------------------------------------------------------------
class TestH4AllGatesConsumed:
    """Every gate produced by the router must be consumed in CI."""

    def _extract_router_gate_names(self) -> set[str]:
        """Parse all gate names from change_impact_router.sh."""
        text = CHANGE_IMPACT_ROUTER.read_text()
        return set(re.findall(r'add_gate\s+"([^"]+)"', text))

    def _extract_ci_gate_conditions(self) -> set[str]:
        """Extract all gate names consumed in ci.yml conditions."""
        text = CI_YML.read_text()
        return set(
            re.findall(
                r"contains\(.*triggered_gates.*,\s*'([^']+)'\)",
                text,
            )
        )

    def test_every_router_gate_consumed_in_ci(self):
        """CI must have a contains() condition for every router gate."""
        router_gates = self._extract_router_gate_names()
        ci_gates = self._extract_ci_gate_conditions()

        assert len(router_gates) > 0, "No gates found in router"

        unconsumed = router_gates - ci_gates
        assert len(unconsumed) == 0, (
            f"Router produces gates not consumed in CI: "
            f"{sorted(unconsumed)}. "
            f"CI consumes: {sorted(ci_gates)}. "
            "Add conditional steps in guard-checks for each."
        )

    def test_ci_gate_conditions_at_least_match_router(self):
        """CI must not reference gates the router does not produce."""
        router_gates = self._extract_router_gate_names()
        ci_gates = self._extract_ci_gate_conditions()

        phantom = ci_gates - router_gates
        assert len(phantom) == 0, f"CI references gates not in router: {sorted(phantom)}."


# -------------------------------------------------------------------
# S3 FULL CLOSURE: Every frontend package must have real test files
# -------------------------------------------------------------------
class TestS3RealTests:
    """Every frontend package must have at least one real test file."""

    PACKAGES_WITH_SRC: ClassVar[list[str]] = [
        "packages/shared",
        "packages/ui",
        "packages/api-client",
    ]

    APP_PACKAGES: ClassVar[list[str]] = [
        "apps/web",
        "apps/admin",
    ]

    @pytest.mark.parametrize("pkg_dir", PACKAGES_WITH_SRC)
    def test_library_package_has_test_file(self, pkg_dir: str):
        """Library packages (shared, ui, api-client) must have tests."""
        pkg_path = FRONTEND / pkg_dir
        test_files = (
            list(pkg_path.rglob("*.test.ts"))
            + list(pkg_path.rglob("*.test.tsx"))
            + list(pkg_path.rglob("*.spec.ts"))
            + list(pkg_path.rglob("*.spec.tsx"))
        )
        test_files = [f for f in test_files if "node_modules" not in str(f)]
        assert len(test_files) >= 1, (
            f"frontend/{pkg_dir} has no test files. Write at least one .test.ts/.test.tsx file."
        )

    @pytest.mark.parametrize("pkg_dir", APP_PACKAGES)
    def test_app_package_has_test_file(self, pkg_dir: str):
        """App packages (web, admin) must have at least one test."""
        pkg_path = FRONTEND / pkg_dir
        test_files = (
            list(pkg_path.rglob("*.test.ts"))
            + list(pkg_path.rglob("*.test.tsx"))
            + list(pkg_path.rglob("*.spec.ts"))
            + list(pkg_path.rglob("*.spec.tsx"))
        )
        test_files = [f for f in test_files if "node_modules" not in str(f)]
        assert len(test_files) >= 1, (
            f"frontend/{pkg_dir} has no test files. Write at least one smoke test."
        )

    @pytest.mark.parametrize(
        "pkg_path",
        [
            "packages/shared/package.json",
            "packages/ui/package.json",
            "packages/api-client/package.json",
        ],
    )
    def test_library_test_script_no_pass_with_no_tests(self, pkg_path: str):
        """Library packages with real tests should not need
        --passWithNoTests."""
        pkg = json.loads((FRONTEND / pkg_path).read_text())
        test_cmd = pkg.get("scripts", {}).get("test", "")
        assert "--passWithNoTests" not in test_cmd, (
            f"frontend/{pkg_path} test still uses "
            f"--passWithNoTests: '{test_cmd}'. "
            "Remove the flag now that real tests exist."
        )
