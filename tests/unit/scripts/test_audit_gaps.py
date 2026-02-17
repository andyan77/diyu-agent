"""Tests for audit gap items #5, #9, #14, #16, #17.

TDD RED: Verify that:
  - #5:  V4 workflows YAML contains skills governance check
  - #9:  CI YAML contains verify_phase --phase 2 step
  - #14: run_phase2_v4.sh evidence uses wf-{id}-{ts}.json naming
  - #16: Makefile has v4p2-validate-config target
  - #17: evidence/v4-phase2/.gitkeep is git-tracked

Uses file-based assertions -- no runtime mocking.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


class TestSkillsGovernanceInV4:
    """#5: V4 workflows YAML must include skills governance."""

    def test_v4_workflows_has_skills_governance_check(self):
        """At least one workflow check must reference skills governance."""
        wf_path = ROOT / "delivery" / "v4-phase2-workflows.yaml"
        assert wf_path.exists(), f"{wf_path} not found"

        with wf_path.open() as f:
            data = yaml.safe_load(f)

        all_cmds = []
        for wf in data.get("workflows", []):
            for check in wf.get("checks", []):
                all_cmds.append(check.get("cmd", ""))

        has_skills = any(
            "skills" in cmd and ("governance" in cmd or "validate" in cmd) for cmd in all_cmds
        )
        assert has_skills, (
            "V4 workflows must include a skills governance validation check. "
            f"Found commands: {all_cmds}"
        )


class TestVerifyPhase2InCI:
    """#9: CI must run verify_phase --phase 2."""

    def test_ci_yaml_has_verify_phase_2(self):
        """ci.yml must contain a verify_phase.py --phase 2 step."""
        ci_path = ROOT / ".github" / "workflows" / "ci.yml"
        assert ci_path.exists()
        content = ci_path.read_text()
        assert re.search(r"verify_phase\.py\s+--phase\s+2", content), (
            "ci.yml must include 'verify_phase.py --phase 2' step"
        )


class TestEvidenceFileNaming:
    """#14: Evidence files must use wf-{id}-{ts}.json naming."""

    def test_run_phase2_uses_wf_id_ts_naming(self):
        """run_phase2_v4.sh must write evidence as wf-{id}-*.json, not checks.json."""
        sh_path = ROOT / "scripts" / "run_phase2_v4.sh"
        assert sh_path.exists()
        content = sh_path.read_text()

        # Must NOT contain the old flat checks.json pattern
        assert "checks.json" not in content, (
            "Evidence files should use wf-{id}-{ts}.json naming, not checks.json"
        )

        # Must contain the new naming pattern
        assert re.search(r"wf-.*\.json", content), (
            "run_phase2_v4.sh must use wf-{id}-{timestamp}.json evidence naming"
        )


class TestMakefileValidateConfig:
    """#16: Makefile must have v4p2-validate-config target."""

    def test_makefile_has_validate_config_target(self):
        """Makefile must define v4p2-validate-config target."""
        makefile = ROOT / "Makefile"
        assert makefile.exists()
        content = makefile.read_text()
        assert re.search(r"^v4p2-validate-config:", content, re.MULTILINE), (
            "Makefile must define 'v4p2-validate-config:' target"
        )


class TestGitkeepTracked:
    """#17: evidence/v4-phase2/.gitkeep must be git-tracked."""

    def test_gitkeep_exists(self):
        """evidence/v4-phase2/.gitkeep must exist."""
        gitkeep = ROOT / "evidence" / "v4-phase2" / ".gitkeep"
        assert gitkeep.exists(), f"{gitkeep} does not exist"

    def test_gitkeep_is_tracked(self):
        """evidence/v4-phase2/.gitkeep must be tracked by git."""
        result = subprocess.run(
            ["git", "ls-files", "evidence/v4-phase2/.gitkeep"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=5,
        )
        assert result.stdout.strip() == "evidence/v4-phase2/.gitkeep", (
            "evidence/v4-phase2/.gitkeep is not tracked by git"
        )
