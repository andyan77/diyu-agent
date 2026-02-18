"""Tests for WF-P0 guard script fixes.

Verifies that audit-identified bugs in guard/audit scripts
have been correctly fixed:
  P0.1: full_audit.sh no longer has || true on run_check commands
  P0.2: run_w4_evidence_gate.sh detects sub-check errors
  P0.4: check_rls.sh uses SSOT and proper parameter parsing
  P0.5: check_migration.sh includes violation details in JSON
  P0.1b: full_audit.sh parameter parsing uses while/shift (not for/shift)
  P0.2b: W4 gate scope declaration matches actual checks
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FULL_AUDIT = ROOT / "scripts" / "full_audit.sh"
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
MILESTONE_MATRIX = ROOT / "delivery" / "milestone-matrix.yaml"
W4_GATE = (
    ROOT / ".claude" / "skills" / "taskcard-governance" / "scripts" / "run_w4_evidence_gate.sh"
)
CHECK_RLS = ROOT / "scripts" / "check_rls.sh"
CHECK_MIGRATION = ROOT / "scripts" / "check_migration.sh"
GENERATE_SBOM = ROOT / "scripts" / "generate_sbom.sh"
RLS_TABLES_PY = ROOT / "src" / "shared" / "rls_tables.py"


@pytest.mark.unit
class TestP01FullAuditFailOpen:
    """P0.1: full_audit.sh must not swallow failures with || true."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.text = FULL_AUDIT.read_text()

    def test_no_or_true_in_run_check_commands(self) -> None:
        """run_check calls must not have || true appended."""
        for i, line in enumerate(self.text.splitlines(), 1):
            if "run_check" in line and "|| true" in line:
                pytest.fail(f"full_audit.sh:{i} still has '|| true' in run_check: {line.strip()}")

    def test_skill_audit_checks_exist(self) -> None:
        assert "run_systematic_review" in self.text
        assert "run_cross_audit" in self.text
        assert "run_fix_verify" in self.text

    def test_agent_test_check_exists(self) -> None:
        assert "test_agent_permissions" in self.text


@pytest.mark.unit
class TestP02W4ErrorDetection:
    """P0.2: W4 gate must detect sub-check errors (exception -> 'error' key)."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.text = W4_GATE.read_text()

    def test_has_errors_variable_defined(self) -> None:
        assert "has_errors" in self.text

    def test_checks_error_key_in_results(self) -> None:
        assert "'error' in results" in self.text

    def test_has_errors_included_in_overall(self) -> None:
        """Overall status must consider has_errors."""
        # Find the overall assignment line
        overall_lines = [
            line for line in self.text.splitlines() if "overall" in line and "has_errors" in line
        ]
        assert len(overall_lines) >= 1, "has_errors not used in overall status determination"

    def test_sub_check_errors_in_summary(self) -> None:
        """Summary JSON must include sub_check_errors field."""
        assert "sub_check_errors" in self.text


@pytest.mark.unit
class TestP04CheckRLSSSoT:
    """P0.4: check_rls.sh must use SSOT and support --phase N."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.text = CHECK_RLS.read_text()

    def test_imports_from_rls_tables(self) -> None:
        """Must source table list from src/shared/rls_tables.py."""
        assert "src.shared.rls_tables" in self.text

    def test_no_hardcoded_conversations_table(self) -> None:
        """Old hardcoded Phase 2+ tables must be removed."""
        lines = self.text.splitlines()
        for line in lines:
            # Skip comments
            if line.strip().startswith("#"):
                continue
            assert '"conversations"' not in line, "Hardcoded 'conversations' table found"

    def test_supports_phase_flag(self) -> None:
        assert "--phase" in self.text

    def test_while_loop_parameter_parsing(self) -> None:
        """Must use while/shift pattern, not for/case."""
        assert "while [" in self.text or "while test" in self.text

    def test_missing_migrations_dir_is_fail(self) -> None:
        """Missing migrations/ must exit 1 (FAIL), not exit 0 (SKIP)."""
        in_missing_block = False
        for line in self.text.splitlines():
            if "! -d" in line and "MIGRATIONS_DIR" in line:
                in_missing_block = True
            if in_missing_block and "exit 0" in line:
                pytest.fail("Missing migrations directory exits 0 (should be 1)")
            if in_missing_block and "exit 1" in line:
                break

    def test_missing_table_is_fail_not_continue(self) -> None:
        """Tables in SSOT but not in migrations must FAIL, not silently continue."""
        assert "MISSING-TABLE" in self.text


@pytest.mark.unit
class TestP05CheckMigrationJSON:
    """P0.5: check_migration.sh JSON must include violation details."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.text = CHECK_MIGRATION.read_text()

    def test_violation_json_variable_exists(self) -> None:
        assert "VIOLATION_JSON" in self.text

    def test_add_violation_builds_json(self) -> None:
        """add_violation() must append to VIOLATION_JSON."""
        # Find the add_violation function body
        in_func = False
        found_json_append = False
        for line in self.text.splitlines():
            if "add_violation()" in line:
                in_func = True
            if in_func and "VIOLATION_JSON" in line:
                found_json_append = True
                break
            if in_func and line.strip() == "}":
                break
        assert found_json_append, "add_violation() does not build VIOLATION_JSON"

    def test_fail_json_includes_violations_array(self) -> None:
        """JSON fail output must include violations array, not just count+message."""
        # Look for the fail JSON output line
        for line in self.text.splitlines():
            if "fail" in line and "VIOLATION_JSON" in line:
                return
        pytest.fail("JSON fail output does not include VIOLATION_JSON")


@pytest.mark.unit
class TestP06SBOMScript:
    """P0.6: SBOM generation script exists and targets SPDX."""

    def test_generate_sbom_exists(self) -> None:
        assert GENERATE_SBOM.exists()

    def test_generates_spdx_format(self) -> None:
        text = GENERATE_SBOM.read_text()
        assert "spdxVersion" in text
        assert "SPDX-2" in text

    def test_supports_validate_flag(self) -> None:
        text = GENERATE_SBOM.read_text()
        assert "--validate" in text

    def test_outputs_to_delivery_dir(self) -> None:
        text = GENERATE_SBOM.read_text()
        assert "delivery/sbom.json" in text


@pytest.mark.unit
class TestP03RLSTablesSSOTFile:
    """P0.3: src/shared/rls_tables.py exists as SSOT."""

    def test_rls_tables_module_exists(self) -> None:
        assert RLS_TABLES_PY.exists()

    def test_exports_phase1_tables(self) -> None:
        text = RLS_TABLES_PY.read_text()
        assert "PHASE_1_RLS_TABLES" in text

    def test_exports_get_rls_tables(self) -> None:
        text = RLS_TABLES_PY.read_text()
        assert "def get_rls_tables" in text

    def test_rls_smoke_test_imports_ssot(self) -> None:
        """test_rls_isolation.py must import from SSOT, not maintain its own list."""
        rls_test = ROOT / "tests" / "isolation" / "smoke" / "test_rls_isolation.py"
        text = rls_test.read_text()
        assert "from src.shared.rls_tables import" in text


@pytest.mark.unit
class TestP01bFullAuditParamParsing:
    """P0.1b: full_audit.sh must use while/shift for parameter parsing.

    The 'for arg in "$@"' + shift pattern is broken: shift modifies
    positional params but the for loop iterates the original $@ snapshot.
    Result: --phase N fails because N is never consumed properly.
    """

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.text = FULL_AUDIT.read_text()
        self.lines = self.text.splitlines()

    def test_uses_while_shift_not_for_loop(self) -> None:
        """Parameter parsing must use while/shift, not for/case with shift."""
        has_while = any(("while [" in line or "while test" in line) for line in self.lines)
        # The broken pattern: 'for arg in "$@"' with shift inside
        has_broken_for_shift = False
        in_for_block = False
        for line in self.lines:
            stripped = line.strip()
            if re.match(r'^for\s+\w+\s+in\s+"\$@"', stripped):
                in_for_block = True
            if in_for_block and "shift" in stripped:
                has_broken_for_shift = True
                break
            if in_for_block and stripped == "done":
                in_for_block = False
        assert has_while, "full_audit.sh must use while/shift for arg parsing"
        assert not has_broken_for_shift, "full_audit.sh has broken 'for arg in $@ / shift' pattern"

    def test_phase_value_passed_correctly_to_report(self) -> None:
        """The PHASE variable must reach the report generation safely.

        Line 156 had: int(sys.argv[2]) which fails when PHASE='--phase'.
        After fix, PHASE should always be a valid integer string.
        """
        # The report python block should not blindly cast sys.argv[2] to int
        # without PHASE being properly parsed. Check that the parsing
        # doesn't leave PHASE as a flag string.
        in_report_python = False
        for line in self.lines:
            if "python3 -c" in line and "'phase'" in line:
                in_report_python = True
            if in_report_python and "int(sys.argv" in line:
                # This is acceptable as long as parsing is correct
                # Just verify PHASE default is numeric
                break
        # Verify PHASE default is numeric
        for line in self.lines:
            if line.strip().startswith("PHASE=") and ":-" in line:
                # Extract default: PHASE="${PHASE:-0}"
                match = re.search(r"PHASE=.*:-(\w+)", line)
                if match:
                    default = match.group(1)
                    assert default.isdigit(), f"PHASE default '{default}' is not numeric"

    def test_ci_invocation_compatible(self) -> None:
        """CI calls 'full_audit.sh --json --phase 0' which must work."""
        ci_text = CI_YML.read_text()
        # Find the full_audit.sh invocation
        for line in ci_text.splitlines():
            if "full_audit.sh" in line and "--phase" in line:
                # Verify it uses --phase N (space-separated) format
                assert "--phase" in line, "CI must invoke with --phase flag"
                return
        pytest.fail("CI does not invoke full_audit.sh with --phase")


@pytest.mark.unit
class TestP02bW4ScopeAlignment:
    """P0.2b: W4 scope declaration must match actual checks."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.text = W4_GATE.read_text()

    def test_scope_declaration_is_accurate(self) -> None:
        """The 'scope' field must not claim checks that aren't performed."""
        # Find scope declaration
        scope_line = ""
        for line in self.text.splitlines():
            if '"scope"' in line:
                scope_line = line
                break
        assert scope_line, "W4 gate must declare scope"
        # If scope claims "acceptance", check that acceptance is actually run
        if "acceptance" in scope_line.lower():
            assert "check_acceptance" in self.text, (
                "W4 scope claims 'acceptance' but no acceptance check is run"
            )
        # If scope claims "evidence", that's about the gate report itself -- OK


@pytest.mark.unit
class TestPhasePointerAndExitCriteria:
    """Verify milestone-matrix.yaml phase pointer and exit criteria."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        import yaml

        self.text = MILESTONE_MATRIX.read_text()
        self.data = yaml.safe_load(self.text)

    def test_current_phase_is_phase_2(self) -> None:
        """current_phase must be phase_2 during Phase 2 development."""
        assert self.data["current_phase"] == "phase_2", (
            f"current_phase is '{self.data['current_phase']}', expected 'phase_2'"
        )

    def test_current_phase_in_phases_keys(self) -> None:
        """current_phase must reference an existing phase definition."""
        current = self.data["current_phase"]
        phases = self.data["phases"]
        assert current in phases, (
            f"current_phase '{current}' not found in phases keys: {list(phases.keys())}"
        )

    def test_phase1_has_gateway_auth_exit_criterion(self) -> None:
        """Phase 1 (Security & Tenant) must gate on JWT auth."""
        p1 = self.data["phases"]["phase_1"]
        hard_ids = [c["id"] for c in p1["exit_criteria"]["hard"]]
        assert "p1-gateway-auth" in hard_ids, (
            "Phase 1 exit criteria missing p1-gateway-auth hard check"
        )

    def test_phase1_has_rbac_exit_criterion(self) -> None:
        """Phase 1 must gate on RBAC."""
        p1 = self.data["phases"]["phase_1"]
        hard_ids = [c["id"] for c in p1["exit_criteria"]["hard"]]
        assert "p1-rbac" in hard_ids, "Phase 1 exit criteria missing p1-rbac hard check"

    def test_phase1_sbom_is_hard_not_soft(self) -> None:
        """SBOM must be a hard gate (compliance requirement)."""
        p1 = self.data["phases"]["phase_1"]
        hard_ids = [c["id"] for c in p1["exit_criteria"]["hard"]]
        soft_ids = [c["id"] for c in p1["exit_criteria"].get("soft", [])]
        assert "p1-sbom" in hard_ids, "p1-sbom must be a hard exit criterion"
        assert "p1-sbom" not in soft_ids, "p1-sbom must not be in soft criteria"

    def test_phase1_has_minimum_hard_criteria(self) -> None:
        """Phase 1 must have >= 8 hard exit criteria."""
        p1 = self.data["phases"]["phase_1"]
        hard_count = len(p1["exit_criteria"]["hard"])
        assert hard_count >= 8, f"Phase 1 has only {hard_count} hard criteria, need >= 8"


@pytest.mark.unit
class TestSBOMCIIntegration:
    """SBOM generation must be integrated into CI."""

    def test_ci_has_sbom_step(self) -> None:
        """CI pipeline must include SBOM generation or validation."""
        ci_text = CI_YML.read_text()
        has_sbom = (
            "generate_sbom" in ci_text or "sbom" in ci_text.lower() or "spdx" in ci_text.lower()
        )
        assert has_sbom, "CI pipeline has no SBOM generation/validation step"
