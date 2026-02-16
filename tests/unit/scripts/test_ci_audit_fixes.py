"""Tests for Batch 1+2 audit fixes: CI hardening + security baseline.

TDD RED phase: These tests verify the fixes for audit findings
C1, H2, H4, H5, S1, M3.

Covers:
  C1:  Security scanning jobs exist in CI (gitleaks, SAST, dep audit)
  H2:  No continue-on-error in CI quality gates
  H4:  change_impact_router outputs consumed by downstream jobs
  H5:  tee pipe failures propagated (3 fix points)
  S1:  uv.lock tracked in git, CI uses --frozen
  M3:  user_prompt_guard blocks on secret detection
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import ClassVar

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
TASK_CARD_CHECK_YML = ROOT / ".github" / "workflows" / "task-card-check.yml"
GITIGNORE = ROOT / ".gitignore"
PROMPT_GUARD = ROOT / "scripts" / "hooks" / "user_prompt_guard.sh"


@pytest.fixture
def ci_text() -> str:
    return CI_YML.read_text()


@pytest.fixture
def ci_yaml() -> dict:
    return yaml.safe_load(CI_YML.read_text())


@pytest.fixture
def task_card_text() -> str:
    return TASK_CARD_CHECK_YML.read_text()


@pytest.fixture
def task_card_yaml() -> dict:
    return yaml.safe_load(TASK_CARD_CHECK_YML.read_text())


# ---------------------------------------------------------------------------
# C1: Security scanning jobs must exist in CI
# ---------------------------------------------------------------------------
class TestC1SecurityGates:
    """CI must have security scanning jobs that block PRs."""

    def test_security_scan_job_exists(self, ci_yaml):
        """A security-scan job must exist in ci.yml."""
        jobs = ci_yaml.get("jobs", {})
        security_jobs = [
            name for name in jobs if "security" in name.lower() or "secret" in name.lower()
        ]
        assert len(security_jobs) > 0, (
            "ci.yml has no security scanning job. "
            "Expected a job like 'security-scan' per governance H-4/H-5."
        )

    def test_secret_scanning_step_exists(self, ci_yaml):
        """Security job must include a secret scanning step (gitleaks or similar)."""
        jobs = ci_yaml.get("jobs", {})
        found = False
        for _job_name, job_config in jobs.items():
            for step in job_config.get("steps", []):
                run_cmd = step.get("run", "")
                step_name = step.get("name", "")
                uses = step.get("uses", "")
                if any(
                    kw in (run_cmd + step_name + uses).lower()
                    for kw in ["gitleaks", "trufflehog", "secret", "detect-secrets"]
                ):
                    found = True
                    break
        assert found, "No secret scanning step found in any CI job."

    def test_sast_step_exists(self, ci_yaml):
        """Security job must include a SAST step (semgrep or similar)."""
        jobs = ci_yaml.get("jobs", {})
        found = False
        for _job_name, job_config in jobs.items():
            for step in job_config.get("steps", []):
                run_cmd = step.get("run", "")
                step_name = step.get("name", "")
                uses = step.get("uses", "")
                if any(
                    kw in (run_cmd + step_name + uses).lower()
                    for kw in ["semgrep", "sast", "codeql", "bandit"]
                ):
                    found = True
                    break
        assert found, "No SAST step found in any CI job."

    def test_dependency_audit_step_exists(self, ci_yaml):
        """Security job must include dependency vulnerability scanning."""
        jobs = ci_yaml.get("jobs", {})
        found = False
        for _job_name, job_config in jobs.items():
            for step in job_config.get("steps", []):
                run_cmd = step.get("run", "")
                step_name = step.get("name", "")
                if any(
                    kw in (run_cmd + step_name).lower()
                    for kw in ["pip-audit", "uv audit", "pnpm audit", "dependency"]
                ):
                    found = True
                    break
        assert found, "No dependency audit step found in any CI job."

    def test_security_job_not_continue_on_error(self, ci_yaml):
        """Security scanning job must NOT have continue-on-error (except SARIF upload)."""
        # SARIF upload is an optional result upload, not a security gate itself.
        # It may fail if GitHub Code Scanning is not enabled on the repo.
        sarif_upload_exceptions = {"Upload SARIF to GitHub Code Scanning"}
        jobs = ci_yaml.get("jobs", {})
        for job_name, job_config in jobs.items():
            if "security" in job_name.lower() or "secret" in job_name.lower():
                for step in job_config.get("steps", []):
                    step_name = step.get("name", "")
                    if step_name in sarif_upload_exceptions:
                        continue
                    assert step.get("continue-on-error") is not True, (
                        f"Security job '{job_name}' step '{step_name}' "
                        "has continue-on-error: true. Security gates must block."
                    )


# ---------------------------------------------------------------------------
# H2: No continue-on-error on quality gate jobs
# ---------------------------------------------------------------------------
class TestH2NoContinueOnError:
    """Quality gate steps must not use continue-on-error: true."""

    QUALITY_GATE_JOBS: ClassVar[list[str]] = [
        "lint-backend",
        "lint-frontend",
        "typecheck-backend",
        "typecheck-frontend",
        "test-backend",
        "test-frontend",
        "guard-checks",
    ]

    def test_no_continue_on_error_in_quality_gates(self, ci_yaml):
        """None of the L1 quality gate jobs should have continue-on-error on run steps."""
        jobs = ci_yaml.get("jobs", {})
        violations = []
        for job_name in self.QUALITY_GATE_JOBS:
            job = jobs.get(job_name, {})
            for step in job.get("steps", []):
                if step.get("continue-on-error") is True:
                    violations.append(
                        f"{job_name}: step '{step.get('name', step.get('run', '?')[:50])}'"
                    )
        assert len(violations) == 0, (
            "continue-on-error: true found in quality gates:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ---------------------------------------------------------------------------
# H4: Change impact router outputs consumed by downstream jobs
# ---------------------------------------------------------------------------
class TestH4ChangeImpactConsumed:
    """change-impact job outputs must be consumed by at least one downstream job."""

    def test_change_impact_has_outputs(self, ci_yaml):
        """change-impact job must declare outputs."""
        jobs = ci_yaml.get("jobs", {})
        impact_job = jobs.get("change-impact", {})
        outputs = impact_job.get("outputs", {})
        assert len(outputs) > 0, (
            "change-impact job has no outputs declared. "
            "triggered_gates should be exposed for downstream consumption."
        )

    def test_downstream_job_references_impact_outputs(self, ci_text):
        """At least one job must reference change-impact outputs."""
        pattern = r"needs\.change-impact\.outputs"
        matches = re.findall(pattern, ci_text)
        assert len(matches) > 0, (
            "No downstream job references change-impact outputs. "
            "Impact routing is decorative without consumption."
        )


# ---------------------------------------------------------------------------
# H5: tee pipe failures must be propagated (3 fix points)
# ---------------------------------------------------------------------------
class TestH5PipeFailurePropagation:
    """Card census, phase-gate, scaffold must not silently swallow failures."""

    def _get_step_run_block(self, yaml_data: dict, job_name: str, step_name_prefix: str) -> str:
        """Extract the 'run' block for a specific step."""
        jobs = yaml_data.get("jobs", {})
        job = jobs.get(job_name, {})
        for step in job.get("steps", []):
            name = step.get("name", "")
            if name.lower().startswith(step_name_prefix.lower()):
                return step.get("run", "")
        return ""

    def test_card_census_not_swallowed(self, task_card_yaml):
        """Card census step must propagate failure (second execution or pipefail)."""
        run_block = self._get_step_run_block(task_card_yaml, "schema-check", "card census")
        has_fix = "set -o pipefail" in run_block or run_block.count("count_task_cards") >= 2
        assert has_fix, (
            "Card census step uses 'tee' pipe without failure propagation. "
            "Need either 'set -o pipefail' or a second execution without pipe."
        )

    def test_phase_gate_not_swallowed(self, task_card_yaml):
        """Phase gate step must propagate failure."""
        run_block = self._get_step_run_block(task_card_yaml, "phase-gate", "phase gate")
        has_fix = "set -o pipefail" in run_block or run_block.count("verify_phase") >= 2
        assert has_fix, (
            "Phase gate step uses 'tee' pipe without failure propagation. "
            "Need either 'set -o pipefail' or a second execution without pipe."
        )

    def test_scaffold_not_swallowed(self, task_card_yaml):
        """Scaffold integrity step must propagate failure."""
        run_block = self._get_step_run_block(task_card_yaml, "phase-gate", "scaffold")
        has_fix = "set -o pipefail" in run_block or run_block.count("scaffold_phase0") >= 2
        assert has_fix, (
            "Scaffold step uses 'tee' pipe without failure propagation. "
            "Need either 'set -o pipefail' or a second execution without pipe."
        )


# ---------------------------------------------------------------------------
# S1: uv.lock must be tracked in version control
# ---------------------------------------------------------------------------
class TestS1UvLockTracked:
    """uv.lock must not be in .gitignore and CI must use --frozen."""

    def test_uv_lock_not_in_gitignore(self):
        """uv.lock must not be listed in .gitignore."""
        gitignore_text = GITIGNORE.read_text()
        lines = [
            line.strip()
            for line in gitignore_text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert "uv.lock" not in lines, (
            ".gitignore still contains 'uv.lock'. "
            "Lock file must be tracked for reproducible builds."
        )

    def test_ci_uses_frozen_flag(self, ci_text):
        """All 'uv sync' calls in CI must use --frozen."""
        sync_lines = [line.strip() for line in ci_text.splitlines() if "uv sync" in line]
        for line in sync_lines:
            assert "--frozen" in line, (
                f"CI 'uv sync' without --frozen: '{line}'. Must use --frozen to enforce lock file."
            )


# ---------------------------------------------------------------------------
# M3: user_prompt_guard must block on secret detection
# ---------------------------------------------------------------------------
class TestM3PromptGuardBlocks:
    """user_prompt_guard.sh must exit 2 when secrets are detected."""

    def _run_guard(self, json_input: str) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
        """Helper to run user_prompt_guard.sh with given input."""
        return subprocess.run(
            ["bash", str(PROMPT_GUARD)],
            input=json_input,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=ROOT,
        )

    def test_guard_blocks_on_secret_pattern(self):
        """Feeding a secret pattern must cause exit code 2 (block)."""
        result = self._run_guard('{"prompt":"my key is sk-abcdefghijklmnopqrstuvwxyz1234567890"}')
        assert result.returncode == 2, (
            f"user_prompt_guard.sh returned {result.returncode} on secret input, "
            "expected exit 2 (block). Guard is not blocking secret leakage."
        )

    def test_guard_allows_normal_input(self):
        """Normal prompt without secrets must exit 0 (allow)."""
        result = self._run_guard('{"prompt":"hello world, how are you today?"}')
        assert result.returncode == 0, (
            f"user_prompt_guard.sh returned {result.returncode} on normal input, "
            "expected exit 0 (allow)."
        )

    def test_guard_blocks_aws_key_pattern(self):
        """AWS access key pattern must also be blocked."""
        result = self._run_guard('{"prompt":"my aws key is AKIAIOSFODNN7EXAMPLE"}')
        assert result.returncode == 2, (
            f"user_prompt_guard.sh returned {result.returncode} on AWS key, "
            "expected exit 2 (block)."
        )

    def test_guard_blocks_private_key_pattern(self):
        """PEM private key pattern must also be blocked."""
        result = self._run_guard('{"prompt":"-----BEGIN RSA PRIVATE KEY-----"}')
        assert result.returncode == 2, (
            f"user_prompt_guard.sh returned {result.returncode} on private key, "
            "expected exit 2 (block)."
        )


# ---------------------------------------------------------------------------
# Batch 1+2 pre-existing CI fixes (mypy, frontend typecheck, gitleaks,
# audit system check, skills governance)
# ---------------------------------------------------------------------------
TYPES_INIT = ROOT / "src" / "shared" / "types" / "__init__.py"
GITLEAKS_TOML = ROOT / ".gitleaks.toml"
FE_API_CLIENT_TSCONFIG = ROOT / "frontend" / "packages" / "api-client" / "tsconfig.json"
FE_SHARED_TSCONFIG = ROOT / "frontend" / "packages" / "shared" / "tsconfig.json"
SKILLS_VALIDATE = ROOT / "scripts" / "skills" / "validate_skills_governance.py"


class TestMypyDictGenericParams:
    """All dict annotations in types/__init__.py must have generic parameters."""

    def test_no_bare_dict_annotations(self):
        """mypy strict mode requires dict[K, V], not bare dict."""
        text = TYPES_INIT.read_text()
        # Check that there are no bare 'dict' in annotations (quick heuristic)
        # A bare dict appears as `: dict` or `dict |` without `[` after it
        lines = text.splitlines()
        bare_dicts = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip imports
            if stripped.startswith(("from ", "import ", "#", '"""', "if ")):
                continue
            # Match patterns like `: dict |`, `: dict =`, `list[dict]`
            import re as _re

            # Bare dict as type annotation (not dict[...])
            matches = _re.findall(r"\bdict\b(?!\[)", stripped)
            if matches and "default_factory=dict" not in stripped:
                bare_dicts.append((i, stripped))
        assert len(bare_dicts) == 0, (
            f"Found {len(bare_dicts)} bare dict annotations (need generic params):\n"
            + "\n".join(f"  L{ln}: {s}" for ln, s in bare_dicts)
        )


class TestFrontendTsconfigLib:
    """Frontend packages must include 'dom' in tsconfig lib for Vite compatibility."""

    @pytest.mark.parametrize(
        "tsconfig_path",
        [FE_API_CLIENT_TSCONFIG, FE_SHARED_TSCONFIG],
        ids=["api-client", "shared"],
    )
    def test_tsconfig_includes_dom_lib(self, tsconfig_path: Path):
        import json as _json

        config = _json.loads(tsconfig_path.read_text())
        lib = config.get("compilerOptions", {}).get("lib", [])
        assert "dom" in [entry.lower() for entry in lib], (
            f"{tsconfig_path.name} lib={lib} missing 'dom'. "
            "Vite type definitions require Web Worker globals from 'dom'."
        )


class TestGitleaksConfig:
    """Gitleaks must have a config file to manage false positives."""

    def test_gitleaks_toml_exists(self):
        assert GITLEAKS_TOML.exists(), (
            ".gitleaks.toml missing. Required for managing test fixture false positives."
        )

    def test_gitleaks_toml_has_allowlist(self):
        text = GITLEAKS_TOML.read_text()
        assert "[allowlist]" in text, ".gitleaks.toml must have an [allowlist] section"

    def test_ci_references_gitleaks_config(self, ci_text):
        """CI gitleaks step must reference config file via GITLEAKS_CONFIG env."""
        assert "GITLEAKS_CONFIG" in ci_text, (
            "CI gitleaks step does not reference GITLEAKS_CONFIG. "
            "Must set env var to pick up .gitleaks.toml."
        )


class TestAuditSystemCheckGraceful:
    """Audit system check must not hard-fail when evidence/ is missing (gitignored)."""

    def test_audit_check_no_exit_1_on_missing_evidence(self, ci_text):
        """The audit artifact validation step must not 'exit 1' when evidence is missing."""
        # Find the audit artifact validation block
        in_audit_block = False
        found_graceful = False
        for line in ci_text.splitlines():
            if "Run audit artifact validation" in line:
                in_audit_block = True
            elif in_audit_block:
                if line.strip().startswith("- name:"):
                    break
                if "exit 1" in line:
                    pytest.fail(
                        "Audit artifact validation still has 'exit 1' for missing evidence. "
                        "Should gracefully skip since evidence/ is gitignored."
                    )
                if "warning" in line.lower() or "skip" in line.lower():
                    found_graceful = True
        assert found_graceful, (
            "Audit artifact validation block should emit a warning/skip message "
            "when evidence is not present."
        )


class TestSkillsValidateCIAware:
    """skills governance validator must handle CI environment gracefully."""

    def test_validator_imports_os(self):
        """Validator must import os to check CI environment variable."""
        text = SKILLS_VALIDATE.read_text()
        assert "import os" in text, (
            "validate_skills_governance.py must import os to detect CI environment"
        )

    def test_validator_checks_ci_env(self):
        """Validator must check CI environment variable."""
        text = SKILLS_VALIDATE.read_text()
        assert 'os.environ.get("CI"' in text or "os.environ.get('CI'" in text, (
            "validate_skills_governance.py must check CI env var for session-log check"
        )

    def test_validator_supports_warn_status(self):
        """check_result must support warn status for CI-only checks."""
        text = SKILLS_VALIDATE.read_text()
        assert '"warn"' in text, (
            "validate_skills_governance.py must support 'warn' status for CI-degraded checks"
        )


# ---------------------------------------------------------------------------
# Governance sync: Makefile bootstrap, dependency-groups documentation
# ---------------------------------------------------------------------------
MAKEFILE = ROOT / "Makefile"
PYPROJECT = ROOT / "pyproject.toml"
EXECUTION_PLAN = ROOT / "docs" / "governance" / "execution-plan-v1.0.md"


class TestMakefileBootstrapDevDeps:
    """Makefile bootstrap must install dev dependencies via uv sync --dev."""

    def test_bootstrap_uses_uv_sync_dev(self):
        """make bootstrap must run 'uv sync --dev' not bare 'uv sync'."""
        text = MAKEFILE.read_text()
        # Find the bootstrap target block
        in_bootstrap = False
        found_dev = False
        for line in text.splitlines():
            if line.startswith("bootstrap:"):
                in_bootstrap = True
                continue
            if in_bootstrap:
                if not line.startswith("\t") and line.strip():
                    break
                if "uv sync" in line:
                    found_dev = "--dev" in line
                    break
        assert found_dev, (
            "Makefile bootstrap 'uv sync' must include --dev flag. "
            "Without it, [dependency-groups] dev deps are not installed."
        )


class TestDependencyGroupsConfig:
    """pyproject.toml must use [dependency-groups] for dev deps."""

    def test_dependency_groups_dev_exists(self):
        """[dependency-groups] dev section must exist in pyproject.toml."""
        text = PYPROJECT.read_text()
        assert "[dependency-groups]" in text, (
            "pyproject.toml missing [dependency-groups]. "
            "PEP 735 dependency groups required for 'uv sync --dev'."
        )

    def test_optional_deps_no_dev(self):
        """[project.optional-dependencies] must NOT have a 'dev' key."""
        text = PYPROJECT.read_text()
        # Check that optional-dependencies section doesn't contain dev
        in_optional = False
        for line in text.splitlines():
            if line.strip() == "[project.optional-dependencies]":
                in_optional = True
                continue
            if in_optional:
                if line.strip().startswith("["):
                    break
                if line.strip().startswith("dev"):
                    pytest.fail(
                        "pyproject.toml has 'dev' in [project.optional-dependencies]. "
                        "Dev deps must be in [dependency-groups] for 'uv sync --dev' to work."
                    )

    def test_dev_group_has_core_tools(self):
        """[dependency-groups] dev must include pytest, ruff, mypy."""
        text = PYPROJECT.read_text()
        in_dev = False
        dev_content = ""
        for line in text.splitlines():
            if line.strip() == "dev = [":
                in_dev = True
                continue
            if in_dev:
                if line.strip() == "]":
                    break
                dev_content += line
        for tool in ("pytest", "ruff", "mypy"):
            assert tool in dev_content, (
                f"[dependency-groups] dev missing '{tool}'. "
                "Core dev tools must be in dependency-groups."
            )


class TestDependencyGroupsDocumented:
    """execution-plan must document the [dependency-groups] technical decision."""

    def test_execution_plan_has_adr_e1(self):
        """execution-plan-v1.0.md must contain ADR-E1 dependency-groups decision."""
        text = EXECUTION_PLAN.read_text()
        assert "dependency-groups" in text and "optional-dependencies" in text, (
            "execution-plan-v1.0.md must document the [dependency-groups] vs "
            "[project.optional-dependencies] technical decision (ADR-E1)."
        )
