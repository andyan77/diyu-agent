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
        """Security scanning job must NOT have continue-on-error."""
        jobs = ci_yaml.get("jobs", {})
        for job_name, job_config in jobs.items():
            if "security" in job_name.lower() or "secret" in job_name.lower():
                for step in job_config.get("steps", []):
                    assert step.get("continue-on-error") is not True, (
                        f"Security job '{job_name}' step '{step.get('name', '')}' "
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
