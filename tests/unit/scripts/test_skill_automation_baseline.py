"""Tests for Skill automation baseline -- Section 12.2 compliance.

Every Skill (.claude/skills/*/SKILL.md) must have:
  (1) A corresponding script entry point (scripts/run_*.sh or scripts/skills/*.sh)
  (2) Script produces JSON output conforming to scripts/schemas/*.schema.json
  (3) Script is executable and exits with 12.1 exit codes (0/1/2)
  (4) /full-audit can invoke it
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = ROOT / ".claude" / "skills"
SCRIPTS_DIR = ROOT / "scripts"
SCHEMAS_DIR = SCRIPTS_DIR / "schemas"


def _discover_skills() -> list[Path]:
    """Find all SKILL.md files."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _is_guard_skill(skill_dir: Path) -> bool:
    """Guard skills use scripts/check_*.sh as their entry point."""
    return skill_dir.name.startswith("guard-")


_GUARD_SCRIPT_MAP: dict[str, str] = {
    "guard-layer-boundary": "check_layer_deps",
    "guard-port-compat": "check_port_compat",
    "guard-migration-safety": "check_migration",
    "guard-taskcard-schema": "check_task_schema",
}


def _find_script_entry(skill_dir: Path) -> Path | None:
    """Find the automation script for a skill."""
    name = skill_dir.name
    # Guard skills map to scripts/check_*.sh via explicit mapping
    if _is_guard_skill(skill_dir):
        base = _GUARD_SCRIPT_MAP.get(name)
        if base is None:
            suffix = name.replace("guard-", "").replace("-", "_")
            base = f"check_{suffix}"
        candidates = [
            SCRIPTS_DIR / f"{base}.sh",
            SCRIPTS_DIR / f"{base}.py",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None
    # Non-guard skills map to scripts/run_*.sh (some have short aliases)
    skill_script_map = {
        "cross-reference-audit": "run_cross_audit",
        "adversarial-fix-verification": "run_fix_verify",
    }
    slug = name.replace("-", "_")
    base = skill_script_map.get(name, f"run_{slug}")
    candidates = [
        SCRIPTS_DIR / f"{base}.sh",
        SCRIPTS_DIR / f"{base}.py",
        # Taskcard governance uses its own scripts dir
        skill_dir / "scripts" / "run_all.sh",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


class TestAllSkillsHaveScriptEntry:
    """12.2: Every Skill must have a corresponding executable script."""

    def test_skills_exist(self) -> None:
        skills = _discover_skills()
        assert len(skills) >= 4, f"Expected at least 4 skills, found {len(skills)}"

    @pytest.mark.parametrize(
        "skill_md",
        _discover_skills(),
        ids=[p.parent.name for p in _discover_skills()],
    )
    def test_skill_has_script_entry(self, skill_md: Path) -> None:
        skill_dir = skill_md.parent
        script = _find_script_entry(skill_dir)
        assert script is not None, (
            f"Skill '{skill_dir.name}' has no automation script entry point. "
            f"Expected scripts/run_{skill_dir.name.replace('-', '_')}.sh "
            f"or {skill_dir}/scripts/run_all.sh"
        )

    @pytest.mark.parametrize(
        "skill_md",
        _discover_skills(),
        ids=[p.parent.name for p in _discover_skills()],
    )
    def test_script_is_executable(self, skill_md: Path) -> None:
        skill_dir = skill_md.parent
        script = _find_script_entry(skill_dir)
        if script is None:
            pytest.skip(f"No script found for {skill_dir.name}")
        st = os.stat(script)
        assert st.st_mode & stat.S_IXUSR, f"Script {script} is not executable (chmod +x needed)"


class TestGuardSkillsHaveJsonOutput:
    """12.2: Guard scripts must produce JSON output."""

    @pytest.mark.parametrize(
        "skill_md",
        [s for s in _discover_skills() if _is_guard_skill(s.parent)],
        ids=[s.parent.name for s in _discover_skills() if _is_guard_skill(s.parent)],
    )
    def test_guard_script_supports_json_flag(self, skill_md: Path) -> None:
        skill_dir = skill_md.parent
        script = _find_script_entry(skill_dir)
        if script is None:
            pytest.skip(f"No script for {skill_dir.name}")
        text = script.read_text()
        assert "--json" in text, (
            f"Guard script {script.name} must support --json flag for CI consumption"
        )


class TestAuditSkillsHaveJsonSchema:
    """12.2: Audit skills (non-guard) must have corresponding JSON schema."""

    AUDIT_SKILLS: ClassVar[set[str]] = {
        "systematic-review",
        "cross-reference-audit",
        "adversarial-fix-verification",
    }

    @pytest.mark.parametrize("skill_name", sorted(AUDIT_SKILLS))
    def test_schema_file_exists(self, skill_name: str) -> None:
        slug = skill_name.replace("-", "_")
        # Try common naming patterns
        candidates = [
            SCHEMAS_DIR / f"{slug}.schema.json",
            SCHEMAS_DIR / f"{skill_name}.schema.json",
            SCHEMAS_DIR / "review-report.schema.json",
            SCHEMAS_DIR / "cross-audit-report.schema.json",
            SCHEMAS_DIR / "fix-verification-report.schema.json",
        ]
        found = any(c.exists() for c in candidates)
        assert found, (
            f"Skill '{skill_name}' has no JSON schema in {SCHEMAS_DIR}/. "
            f"Checked: {[c.name for c in candidates]}"
        )

    @pytest.mark.parametrize("skill_name", sorted(AUDIT_SKILLS))
    def test_schema_is_valid_json(self, skill_name: str) -> None:
        schema_files = list(SCHEMAS_DIR.glob("*.schema.json")) if SCHEMAS_DIR.exists() else []
        if not schema_files:
            pytest.skip("No schema files found")
        for sf in schema_files:
            data = json.loads(sf.read_text())
            assert isinstance(data, dict), f"{sf.name} is not a valid JSON object"


class TestFullAuditCanInvokeAllSkills:
    """12.6: /full-audit must be able to invoke all skill scripts."""

    def test_full_audit_script_exists(self) -> None:
        script = SCRIPTS_DIR / "full_audit.sh"
        assert script.exists(), "scripts/full_audit.sh must exist (Section 12.6)"

    def test_full_audit_references_all_audit_skills(self) -> None:
        script = SCRIPTS_DIR / "full_audit.sh"
        if not script.exists():
            pytest.skip("full_audit.sh not found")
        text = script.read_text()
        expected_refs = [
            "run_systematic_review",
            "run_cross_audit",
            "run_fix_verify",
        ]
        for ref in expected_refs:
            assert ref in text, f"full_audit.sh must reference {ref} (Section 12.6)"

    def test_full_audit_references_guard_checks(self) -> None:
        script = SCRIPTS_DIR / "full_audit.sh"
        if not script.exists():
            pytest.skip("full_audit.sh not found")
        text = script.read_text()
        expected_guards = [
            "check_layer_deps",
            "check_port_compat",
            "check_rls",
        ]
        for guard in expected_guards:
            assert guard in text, f"full_audit.sh must reference {guard} (Section 12.6)"

    def test_full_audit_references_agent_tests(self) -> None:
        script = SCRIPTS_DIR / "full_audit.sh"
        if not script.exists():
            pytest.skip("full_audit.sh not found")
        text = script.read_text()
        assert "test_agent_permissions" in text, (
            "full_audit.sh must include Agent verification (Section 12.6)"
        )

    def test_full_audit_produces_json_report(self) -> None:
        script = SCRIPTS_DIR / "full_audit.sh"
        if not script.exists():
            pytest.skip("full_audit.sh not found")
        text = script.read_text()
        assert "full-audit" in text and ".json" in text, (
            "full_audit.sh must produce evidence/full-audit-*.json (Section 12.6)"
        )


class TestFullAuditReportSchema:
    """12.6: full-audit JSON output must have a schema definition."""

    def test_schema_exists(self) -> None:
        schema = SCHEMAS_DIR / "full-audit-report.schema.json"
        assert schema.exists(), (
            "scripts/schemas/full-audit-report.schema.json must exist (Section 12.6)"
        )

    def test_schema_has_required_fields(self) -> None:
        schema_path = SCHEMAS_DIR / "full-audit-report.schema.json"
        if not schema_path.exists():
            pytest.skip("Schema not found")
        schema = json.loads(schema_path.read_text())
        props = schema.get("properties", {})
        required_keys = {"timestamp", "phase", "results", "summary", "status"}
        actual_keys = set(props.keys())
        missing = required_keys - actual_keys
        assert not missing, f"Schema missing required properties: {missing}"
