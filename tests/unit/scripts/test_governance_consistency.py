"""Tests for governance document consistency.

TDD RED phase: These tests verify that governance documents remain
internally consistent and match actual repository state.

Covers:
  - HIGH-1:   Success criteria marks match verify_phase output
  - HIGH-2:   Traceability threshold is explicitly defined with metric name
  - HIGH-3:   execution-plan "missing assets" list is current
  - MEDIUM-2: gate-review command references valid JSON paths
  - D0-9:     .commitlintrc.yml existence and schema correctness
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[3]
GOV_PLAN = ROOT / "docs" / "governance" / "governance-optimization-plan.md"
EXEC_PLAN = ROOT / "docs" / "governance" / "execution-plan-v1.0.md"
GATE_REVIEW = ROOT / ".claude" / "commands" / "gate-review.md"


# ---------------------------------------------------------------------------
# HIGH-1: Success criteria marks must reflect reality
# ---------------------------------------------------------------------------
class TestSuccessCriteriaTruthfulness:
    """Verify governance-optimization-plan.md Section 6 success criteria."""

    @pytest.fixture(autouse=True)
    def load_gov_plan(self):
        self.text = GOV_PLAN.read_text()

    def _extract_success_block(self) -> str:
        """Extract the code block under '## 6. 成功标准'."""
        # Find section 6
        pattern = r"## 6\.\s*成功标准.*?```(.*?)```"
        match = re.search(pattern, self.text, re.DOTALL)
        assert match is not None, "Section 6 '成功标准' not found in governance plan"
        return match.group(1)

    def _extract_checked_items(self, day_label: str) -> list[str]:
        """Extract [x] items under a Day N label."""
        block = self._extract_success_block()
        items = []
        in_section = False
        for line in block.splitlines():
            if day_label in line:
                in_section = True
                continue
            if in_section and line.strip().startswith("Day "):
                break  # next section
            if in_section and "[x]" in line:
                items.append(line.strip())
        return items

    def _extract_unchecked_items(self, day_label: str) -> list[str]:
        """Extract [ ] items under a Day N label."""
        block = self._extract_success_block()
        items = []
        in_section = False
        for line in block.splitlines():
            if day_label in line:
                in_section = True
                continue
            if in_section and line.strip().startswith("Day "):
                break
            if in_section and "[ ]" in line:
                items.append(line.strip())
        return items

    def test_day30_verify_phase0_marked_complete(self):
        """verify-phase-0 全绿 must be [x] since Phase 0 is GO 10/10."""
        checked = self._extract_checked_items("Day 30")
        found = any("verify-phase-0" in item and "全绿" in item for item in checked)
        assert found, "Day 30 should mark verify-phase-0 全绿 as [x] (Phase 0 is GO)"

    def test_day30_bootstrap_doctor_marked_complete(self):
        """make bootstrap && make doctor must be [x] since doctor passes."""
        checked = self._extract_checked_items("Day 30")
        found = any(
            "bootstrap" in item and "doctor" in item and "可运行" in item for item in checked
        )
        assert found, "Day 30 should mark bootstrap+doctor as [x] (doctor passes)"

    def test_day60_items_present(self):
        """Day 60 must have at least the expected success criteria items."""
        checked = self._extract_checked_items("Day 60")
        unchecked = self._extract_unchecked_items("Day 60")
        total = len(checked) + len(unchecked)
        assert total >= 4, f"Day 60 should have at least 4 success criteria items, found {total}"

    def test_day90_all_not_marked_complete(self):
        """Day 90 items must NOT all be [x] while Phase 2+ is not started."""
        checked = self._extract_checked_items("Day 90")
        unchecked = self._extract_unchecked_items("Day 90")
        assert len(unchecked) > 0, (
            f"Day 90 has {len(checked)} [x] items and 0 [ ] items, but Phase 2 is not started"
        )


# ---------------------------------------------------------------------------
# HIGH-2: Traceability threshold must name the metric explicitly
# ---------------------------------------------------------------------------
class TestTraceabilityThresholdDefinition:
    """Verify governance plan explicitly names which coverage metric is used."""

    @pytest.fixture(autouse=True)
    def load_gov_plan(self):
        self.text = GOV_PLAN.read_text()

    def _extract_block_conditions(self) -> str:
        """Extract the BLOCK if: section."""
        # Find the block around traceability_coverage
        pattern = r"BLOCK if:.*?(?=\n\n|\n落地|$)"
        match = re.search(pattern, self.text, re.DOTALL)
        assert match is not None, "BLOCK if: section not found"
        return match.group(0)

    def test_traceability_metric_explicitly_named(self):
        """The threshold rule must specify which metric (all_coverage or main_coverage)."""
        block = self._extract_block_conditions()
        # Must contain explicit metric name, not bare 'traceability_coverage'
        has_explicit = "all_coverage" in block or "main_coverage" in block
        assert has_explicit, (
            "BLOCK conditions use 'traceability_coverage' without specifying "
            "whether it means main_coverage or all_coverage. "
            f"Actual block:\n{block}"
        )

    def test_main_coverage_warning_documented(self):
        """When main_coverage is not the blocking metric, a WARNING rule should exist."""
        # Search for a note/warning about main_coverage being auxiliary
        has_main_note = bool(
            re.search(
                r"main_coverage.*(?:WARNING|辅助|auxiliary|advisory|non-blocking)",
                self.text,
                re.IGNORECASE,
            )
        )
        assert has_main_note, (
            "No documentation found for main_coverage WARNING behavior. "
            "The governance plan should document that main_coverage is an "
            "auxiliary (non-blocking) metric."
        )


# ---------------------------------------------------------------------------
# HIGH-3: execution-plan "missing assets" must be current
# ---------------------------------------------------------------------------
class TestExecutionPlanSSOTCurrency:
    """Verify execution-plan-v1.0.md Section 0.4 reflects actual repo state."""

    @pytest.fixture(autouse=True)
    def load_exec_plan(self):
        self.text = EXEC_PLAN.read_text()

    def _extract_missing_assets_table(self) -> list[str]:
        """Extract file paths listed in the 'missing assets' section."""
        # Find section 0.4
        pattern = r"### 0\.4.*?(?=\n---|\n##|\Z)"
        match = re.search(pattern, self.text, re.DOTALL)
        if match is None:
            return []
        section = match.group(0)
        # Extract backtick-quoted paths from table rows
        paths = re.findall(r"`([^`]+)`", section)
        return paths

    def test_missing_assets_section_has_currency_note(self):
        """Section 0.4 must have a note indicating snapshot date or current status."""
        pattern = r"### 0\.4.*?(?=\n---|\n##|\Z)"
        match = re.search(pattern, self.text, re.DOTALL)
        assert match is not None, "Section 0.4 not found"
        section = match.group(0)
        # Must contain a date stamp or "已落盘" note or [NOTE] marker
        has_currency = (
            "已落盘" in section
            or "NOTE" in section
            or "snapshot" in section.lower()
            or "快照" in section
            or "截至" in section
        )
        assert has_currency, (
            "Section 0.4 lists 'missing' assets but has no currency note. "
            "Files like Makefile, pyproject.toml are now present in the repo."
        )

    def test_baseline_line_counts_not_stale(self):
        """Section 0.2 script line counts should not be wildly stale."""
        pattern = r"### 0\.2.*?(?=\n###|\n---|\Z)"
        match = re.search(pattern, self.text, re.DOTALL)
        assert match is not None, "Section 0.2 not found"
        section = match.group(0)

        # Extract reported line counts: "NNN 行"
        line_counts = re.findall(r"(\d+)\s*行", section)
        if not line_counts:
            pytest.skip("No line counts found in section 0.2")

        # Extract script file paths
        scripts = re.findall(r"`scripts/(\S+\.py)`", section)
        for script_name in scripts:
            script_path = ROOT / "scripts" / script_name
            if script_path.exists():
                actual = len(script_path.read_text().splitlines())
                # Find the reported count for this script
                row_pattern = rf"`scripts/{re.escape(script_name)}`.*?(\d+)\s*行"
                row_match = re.search(row_pattern, section)
                if row_match:
                    reported = int(row_match.group(1))
                    drift = abs(actual - reported)
                    assert drift <= 20, (
                        f"{script_name}: reported {reported} lines, "
                        f"actual {actual} lines (drift={drift}). "
                        "Baseline data in execution-plan is stale."
                    )


# ---------------------------------------------------------------------------
# MEDIUM-2: gate-review command must reference correct JSON paths
# ---------------------------------------------------------------------------
class TestGateReviewContract:
    """Verify gate-review.md references match actual JSON output structure."""

    @pytest.fixture(autouse=True)
    def load_gate_review(self):
        self.text = GATE_REVIEW.read_text()

    def test_card_census_reference_has_path_guidance(self):
        """Step 2 must guide how to extract tier_a/tier_b/orphan from nested JSON."""
        # The old reference said "Record: total, tier_a, tier_b, orphan counts"
        # but these are nested under summary.by_tier and summary.gaps
        step2_pattern = r"## Step 2.*?(?=## Step 3|\Z)"
        match = re.search(step2_pattern, self.text, re.DOTALL)
        assert match is not None, "Step 2 not found in gate-review.md"
        step2 = match.group(0)

        # Must mention either the correct path or the summary structure
        has_path = "summary" in step2 or "by_tier" in step2 or "gaps" in step2
        assert has_path, (
            "gate-review Step 2 references tier_a/tier_b/orphan but doesn't "
            "document that these are nested under summary.by_tier and summary.gaps. "
            f"Actual step 2:\n{step2}"
        )


# ---------------------------------------------------------------------------
# D0-9: .commitlintrc.yml existence and schema correctness
# ---------------------------------------------------------------------------
class TestCommitlintConfig:
    """Verify .commitlintrc.yml exists and matches governance Conventional Commits spec.

    治理规范.md Section 4 defines:
      format: <type>(<scope>): <description>
      type:   feat | fix | refactor | test | docs | chore | perf | security
      scope:  brain | knowledge | skill | tool | gateway | infra | ports |
              shared | migration | delivery
    """

    COMMITLINT_PATH = ROOT / ".commitlintrc.yml"
    REQUIRED_TYPES: ClassVar[set[str]] = {
        "feat",
        "fix",
        "refactor",
        "test",
        "docs",
        "chore",
        "perf",
        "security",
    }
    REQUIRED_SCOPES: ClassVar[set[str]] = {
        "brain",
        "knowledge",
        "skill",
        "tool",
        "gateway",
        "infra",
        "ports",
        "shared",
        "migration",
        "delivery",
    }

    def test_commitlintrc_file_exists(self):
        """TASK-D0-9 acceptance: .commitlintrc.yml must exist at repo root."""
        assert self.COMMITLINT_PATH.exists(), (
            f".commitlintrc.yml not found at {self.COMMITLINT_PATH}. "
            "Required by TASK-D0-9 (PR template + CODEOWNERS + commit lint)."
        )

    def test_commitlintrc_is_valid_yaml(self):
        """Config must be parseable YAML."""
        import yaml

        text = self.COMMITLINT_PATH.read_text()
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            pytest.fail(f".commitlintrc.yml is not valid YAML: {e}")
        assert isinstance(data, dict), ".commitlintrc.yml root must be a YAML mapping"

    def test_commitlintrc_has_rules_section(self):
        """Config must contain a 'rules' key."""
        import yaml

        data = yaml.safe_load(self.COMMITLINT_PATH.read_text())
        assert "rules" in data, ".commitlintrc.yml must have a 'rules' section"

    def test_type_enum_matches_governance(self):
        """type-enum must include all 8 types from 治理规范.md Section 4."""
        import yaml

        data = yaml.safe_load(self.COMMITLINT_PATH.read_text())
        rules = data.get("rules", {})
        type_enum = rules.get("type-enum")
        assert type_enum is not None, "rules.type-enum not found in .commitlintrc.yml"
        # commitlint format: [severity, applicability, [values]]
        assert isinstance(type_enum, list) and len(type_enum) == 3, (
            f"type-enum must be [severity, applicability, [values]], got: {type_enum}"
        )
        configured_types = set(type_enum[2])
        missing = self.REQUIRED_TYPES - configured_types
        assert not missing, (
            f"type-enum missing types required by governance: {missing}. "
            f"Configured: {sorted(configured_types)}"
        )

    def test_scope_enum_matches_governance(self):
        """scope-enum must include all 10 scopes from 治理规范.md Section 4."""
        import yaml

        data = yaml.safe_load(self.COMMITLINT_PATH.read_text())
        rules = data.get("rules", {})
        scope_enum = rules.get("scope-enum")
        assert scope_enum is not None, "rules.scope-enum not found in .commitlintrc.yml"
        assert isinstance(scope_enum, list) and len(scope_enum) == 3, (
            f"scope-enum must be [severity, applicability, [values]], got: {scope_enum}"
        )
        configured_scopes = set(scope_enum[2])
        missing = self.REQUIRED_SCOPES - configured_scopes
        assert not missing, (
            f"scope-enum missing scopes required by governance: {missing}. "
            f"Configured: {sorted(configured_scopes)}"
        )

    def test_scope_is_optional(self):
        """scope-empty must allow empty (scope is optional in Conventional Commits)."""
        import yaml

        data = yaml.safe_load(self.COMMITLINT_PATH.read_text())
        rules = data.get("rules", {})
        scope_empty = rules.get("scope-empty")
        if scope_empty is not None:
            # severity 0 means rule disabled (scope is optional)
            # or [severity, 'never'] means empty is allowed
            severity = scope_empty[0] if len(scope_empty) >= 1 else None
            applicability = scope_empty[1] if len(scope_empty) >= 2 else None
            is_optional = severity == 0 or applicability == "never"
            assert is_optional, (
                f"scope-empty should allow empty scope (scope is optional). Got: {scope_empty}"
            )

    def test_subject_case_not_sentence(self):
        """subject-case should not enforce sentence-case (governance uses lowercase)."""
        import yaml

        data = yaml.safe_load(self.COMMITLINT_PATH.read_text())
        rules = data.get("rules", {})
        subject_case = rules.get("subject-case")
        if subject_case is not None and len(subject_case) == 3 and subject_case[1] == "always":
            assert subject_case[2] != "sentence-case", (
                "subject-case should not enforce sentence-case. "
                "Governance examples use lowercase descriptions."
            )
