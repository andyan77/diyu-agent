"""Tests for Hook behavior compliance -- Section 12.2 / 12.1.

Every hook script (scripts/hooks/*.sh) must:
  (1) Be registered in .claude/settings.json
  (2) Follow 12.1 exit code semantics
  (3) Write audit logs to .audit/ (where applicable)
  (4) Be referenced in /full-audit verification chain
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = ROOT / "scripts" / "hooks"
SETTINGS_PATH = ROOT / ".claude" / "settings.json"


def _load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        pytest.skip("settings.json not found")
    return json.loads(SETTINGS_PATH.read_text())


def _discover_hooks() -> list[Path]:
    if not HOOKS_DIR.exists():
        return []
    return sorted(HOOKS_DIR.glob("*.sh"))


def _extract_registered_hooks(settings: dict) -> set[str]:
    """Extract all hook script filenames from settings.json."""
    registered = set()
    hooks_config = settings.get("hooks", {})
    for _event_type, entries in hooks_config.items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                # Extract script name from command string
                for part in cmd.split():
                    if part.endswith(".sh") and "hooks/" in part:
                        registered.add(Path(part).name)
    return registered


class TestAllHooksRegistered:
    """12.2: Every hook script must be registered in settings.json."""

    def test_hooks_exist(self) -> None:
        hooks = _discover_hooks()
        assert len(hooks) >= 7, f"Expected at least 7 hook scripts, found {len(hooks)}"

    @pytest.mark.parametrize(
        "hook_script",
        _discover_hooks(),
        ids=[h.name for h in _discover_hooks()],
    )
    def test_hook_is_registered(self, hook_script: Path) -> None:
        settings = _load_settings()
        registered = _extract_registered_hooks(settings)
        assert hook_script.name in registered, (
            f"Hook {hook_script.name} exists but is not registered in settings.json. "
            f"Registered hooks: {sorted(registered)}"
        )


class TestHookExitCodeSemantics:
    """12.1: Hooks must use correct exit code patterns."""

    @pytest.mark.parametrize(
        "hook_script",
        _discover_hooks(),
        ids=[h.name for h in _discover_hooks()],
    )
    def test_hook_has_explicit_exit(self, hook_script: Path) -> None:
        text = hook_script.read_text()
        has_exit = "exit 0" in text or "exit 1" in text or "exit 2" in text
        assert has_exit, (
            f"Hook {hook_script.name} has no explicit exit code. "
            f"Must use exit 0/1/2 per Section 12.1"
        )

    def test_pre_edit_audit_can_block(self) -> None:
        """pre_edit_audit.sh must be able to exit 2 for Tier 4 files."""
        path = HOOKS_DIR / "pre_edit_audit.sh"
        if not path.exists():
            pytest.skip("pre_edit_audit.sh not found")
        text = path.read_text()
        assert "exit 2" in text, "pre_edit_audit.sh must support exit 2 (hard block)"

    def test_pre_commit_gate_can_block(self) -> None:
        """pre_commit_gate.sh must exit 2 on gate failure."""
        path = HOOKS_DIR / "pre_commit_gate.sh"
        if not path.exists():
            pytest.skip("pre_commit_gate.sh not found")
        text = path.read_text()
        assert "exit 2" in text, "pre_commit_gate.sh must support exit 2 (hard block)"

    def test_user_prompt_guard_can_block(self) -> None:
        """user_prompt_guard.sh must exit 2 on secret detection."""
        path = HOOKS_DIR / "user_prompt_guard.sh"
        if not path.exists():
            pytest.skip("user_prompt_guard.sh not found")
        text = path.read_text()
        assert "exit 2" in text, "user_prompt_guard.sh must support exit 2 (hard block)"

    def test_post_tool_failure_log_never_blocks(self) -> None:
        """post_tool_failure_log.sh must always exit 0 (observability only)."""
        path = HOOKS_DIR / "post_tool_failure_log.sh"
        if not path.exists():
            pytest.skip("post_tool_failure_log.sh not found")
        text = path.read_text()
        assert "exit 2" not in text, (
            "post_tool_failure_log.sh must NOT exit 2 (observability only, never blocks)"
        )


class TestHookAuditLogging:
    """12.2: Hooks that audit must write to .audit/ directory."""

    AUDIT_HOOKS: ClassVar[set[str]] = {
        "pre_edit_audit.sh",
        "pre_commit_gate.sh",
        "post_tool_failure_log.sh",
    }

    @pytest.mark.parametrize("hook_name", sorted(AUDIT_HOOKS))
    def test_hook_writes_audit_log(self, hook_name: str) -> None:
        path = HOOKS_DIR / hook_name
        if not path.exists():
            pytest.skip(f"{hook_name} not found")
        text = path.read_text()
        assert ".audit/" in text or ".audit" in text, (
            f"{hook_name} must write audit logs to .audit/ directory"
        )


class TestPreCommitSecurityEnforcement:
    """G1-security: pre_commit_gate must hard-block on security violations."""

    def test_migration_gate_blocks_on_failure(self) -> None:
        """Gate 4 must exit 2 (not just WARNING) when migration check fails."""
        path = HOOKS_DIR / "pre_commit_gate.sh"
        if not path.exists():
            pytest.skip("pre_commit_gate.sh not found")
        text = path.read_text()
        # Find the migration check section (between Gate 4 and Gate 5)
        lines = text.splitlines()
        in_migration_gate = False
        migration_blocks = False
        for line in lines:
            if "Gate 4" in line and "igration" in line:
                in_migration_gate = True
                continue
            if in_migration_gate and line.strip().startswith("# Gate 5"):
                break
            if in_migration_gate and "exit 2" in line:
                migration_blocks = True
                break
        assert migration_blocks, (
            "pre_commit_gate.sh Gate 4 (migration) must exit 2 on failure, "
            "not just WARNING (security enforcement)"
        )

    def test_rls_check_in_commit_gate(self) -> None:
        """pre_commit_gate.sh must run check_rls.sh when migrations staged."""
        path = HOOKS_DIR / "pre_commit_gate.sh"
        if not path.exists():
            pytest.skip("pre_commit_gate.sh not found")
        text = path.read_text()
        assert "check_rls" in text, (
            "pre_commit_gate.sh must run check_rls.sh for RLS policy enforcement "
            "when migrations are staged (G1-security)"
        )

    def test_rls_gate_blocks_on_failure(self) -> None:
        """RLS gate must exit 2 when check_rls.sh fails."""
        path = HOOKS_DIR / "pre_commit_gate.sh"
        if not path.exists():
            pytest.skip("pre_commit_gate.sh not found")
        text = path.read_text()
        # Must have both check_rls reference and exit 2 in that context
        if "check_rls" not in text:
            pytest.skip("check_rls not in pre_commit_gate.sh yet")
        lines = text.splitlines()
        in_rls_gate = False
        rls_blocks = False
        for line in lines:
            if "check_rls" in line:
                in_rls_gate = True
            if in_rls_gate and "exit 2" in line:
                rls_blocks = True
                break
            if in_rls_gate and line.startswith("# Gate"):
                break
        assert rls_blocks, (
            "pre_commit_gate.sh RLS gate must exit 2 on failure (security enforcement)"
        )


class TestPreCommitCoverageEnforcement:
    """G1-tdd: pre_commit_gate must enforce coverage threshold."""

    def test_coverage_gate_exists(self) -> None:
        """pre_commit_gate.sh must have a coverage check gate."""
        path = HOOKS_DIR / "pre_commit_gate.sh"
        if not path.exists():
            pytest.skip("pre_commit_gate.sh not found")
        text = path.read_text()
        assert "--cov" in text, (
            "pre_commit_gate.sh must include --cov for coverage enforcement (G1-tdd)"
        )

    def test_coverage_threshold_is_80(self) -> None:
        """Coverage threshold must be 80%."""
        path = HOOKS_DIR / "pre_commit_gate.sh"
        if not path.exists():
            pytest.skip("pre_commit_gate.sh not found")
        text = path.read_text()
        assert "cov-fail-under" in text and "80" in text, (
            "pre_commit_gate.sh must enforce --cov-fail-under=80 (G1-tdd)"
        )

    def test_coverage_gate_blocks_on_failure(self) -> None:
        """Coverage gate must exit 2 when below threshold."""
        path = HOOKS_DIR / "pre_commit_gate.sh"
        if not path.exists():
            pytest.skip("pre_commit_gate.sh not found")
        text = path.read_text()
        if "--cov" not in text:
            pytest.skip("coverage gate not in pre_commit_gate.sh yet")
        lines = text.splitlines()
        in_cov_gate = False
        cov_blocks = False
        for line in lines:
            if "--cov" in line or "coverage" in line.lower():
                in_cov_gate = True
            if in_cov_gate and "exit 2" in line:
                cov_blocks = True
                break
        assert cov_blocks, "pre_commit_gate.sh coverage gate must exit 2 when below threshold"

    def test_coverage_only_when_src_staged(self) -> None:
        """Coverage gate should only run when src/ files are staged."""
        path = HOOKS_DIR / "pre_commit_gate.sh"
        if not path.exists():
            pytest.skip("pre_commit_gate.sh not found")
        text = path.read_text()
        if "--cov" not in text:
            pytest.skip("coverage gate not in pre_commit_gate.sh yet")
        assert ("src/" in text and "staged" in text.lower()) or "STAGED" in text, (
            "Coverage gate should be conditional on src/ files being staged"
        )


class TestPostToolUseLayerCheck:
    """12.4: PostToolUse must have layer check hook."""

    def test_post_edit_layer_check_exists(self) -> None:
        path = HOOKS_DIR / "post_edit_layer_check.sh"
        assert path.exists(), "scripts/hooks/post_edit_layer_check.sh must exist (Section 12.4)"

    def test_calls_check_layer_deps(self) -> None:
        path = HOOKS_DIR / "post_edit_layer_check.sh"
        if not path.exists():
            pytest.skip("post_edit_layer_check.sh not found")
        text = path.read_text()
        assert "check_layer_deps" in text, "post_edit_layer_check.sh must call check_layer_deps.sh"

    def test_is_non_blocking_phase0(self) -> None:
        """Phase 0: exit 0 only (log, no block)."""
        path = HOOKS_DIR / "post_edit_layer_check.sh"
        if not path.exists():
            pytest.skip("post_edit_layer_check.sh not found")
        text = path.read_text()
        # Must have exit 0 as default path
        assert "exit 0" in text, "post_edit_layer_check.sh must exit 0 in Phase 0 (log only)"

    def test_registered_in_settings(self) -> None:
        settings = _load_settings()
        registered = _extract_registered_hooks(settings)
        assert "post_edit_layer_check.sh" in registered, (
            "post_edit_layer_check.sh must be registered in settings.json PostToolUse"
        )


class TestPostToolUsePortCheck:
    """12.4: PostToolUse must have port compatibility check hook."""

    def test_post_edit_port_check_exists(self) -> None:
        path = HOOKS_DIR / "post_edit_port_check.sh"
        assert path.exists(), "scripts/hooks/post_edit_port_check.sh must exist"

    def test_calls_check_port_compat(self) -> None:
        path = HOOKS_DIR / "post_edit_port_check.sh"
        if not path.exists():
            pytest.skip("post_edit_port_check.sh not found")
        text = path.read_text()
        assert "check_port_compat" in text, "post_edit_port_check.sh must call check_port_compat.sh"

    def test_filters_ports_directory(self) -> None:
        path = HOOKS_DIR / "post_edit_port_check.sh"
        if not path.exists():
            pytest.skip("post_edit_port_check.sh not found")
        text = path.read_text()
        assert "src/ports/" in text, "post_edit_port_check.sh must filter for src/ports/*.py files"

    def test_is_non_blocking_phase0(self) -> None:
        path = HOOKS_DIR / "post_edit_port_check.sh"
        if not path.exists():
            pytest.skip("post_edit_port_check.sh not found")
        text = path.read_text()
        assert "exit 0" in text, "post_edit_port_check.sh must exit 0 in Phase 0"
        assert "exit 2" not in text, "post_edit_port_check.sh must NOT hard-block in Phase 0"

    def test_writes_audit_log(self) -> None:
        path = HOOKS_DIR / "post_edit_port_check.sh"
        if not path.exists():
            pytest.skip("post_edit_port_check.sh not found")
        text = path.read_text()
        assert ".audit/" in text, "post_edit_port_check.sh must write to .audit/ directory"

    def test_registered_in_settings(self) -> None:
        settings = _load_settings()
        registered = _extract_registered_hooks(settings)
        assert "post_edit_port_check.sh" in registered, (
            "post_edit_port_check.sh must be registered in settings.json PostToolUse"
        )


class TestPostToolUseMigrationCheck:
    """12.4: PostToolUse must have migration safety check hook."""

    def test_post_edit_migration_check_exists(self) -> None:
        path = HOOKS_DIR / "post_edit_migration_check.sh"
        assert path.exists(), "scripts/hooks/post_edit_migration_check.sh must exist"

    def test_calls_check_migration(self) -> None:
        path = HOOKS_DIR / "post_edit_migration_check.sh"
        if not path.exists():
            pytest.skip("post_edit_migration_check.sh not found")
        text = path.read_text()
        assert "check_migration" in text, (
            "post_edit_migration_check.sh must call check_migration.sh"
        )

    def test_filters_migrations_directory(self) -> None:
        path = HOOKS_DIR / "post_edit_migration_check.sh"
        if not path.exists():
            pytest.skip("post_edit_migration_check.sh not found")
        text = path.read_text()
        assert "migrations/versions/" in text, (
            "post_edit_migration_check.sh must filter for migrations/versions/*.py files"
        )

    def test_is_non_blocking_phase0(self) -> None:
        path = HOOKS_DIR / "post_edit_migration_check.sh"
        if not path.exists():
            pytest.skip("post_edit_migration_check.sh not found")
        text = path.read_text()
        assert "exit 0" in text, "post_edit_migration_check.sh must exit 0 in Phase 0"
        assert "exit 2" not in text, "post_edit_migration_check.sh must NOT hard-block in Phase 0"

    def test_writes_audit_log(self) -> None:
        path = HOOKS_DIR / "post_edit_migration_check.sh"
        if not path.exists():
            pytest.skip("post_edit_migration_check.sh not found")
        text = path.read_text()
        assert ".audit/" in text, "post_edit_migration_check.sh must write to .audit/ directory"

    def test_registered_in_settings(self) -> None:
        settings = _load_settings()
        registered = _extract_registered_hooks(settings)
        assert "post_edit_migration_check.sh" in registered, (
            "post_edit_migration_check.sh must be registered in settings.json PostToolUse"
        )


class TestSemanticKeywordSuggestion:
    """12.7: user_prompt_guard.sh must suggest components via semantic keywords."""

    def test_user_prompt_guard_has_keyword_detection(self) -> None:
        path = HOOKS_DIR / "user_prompt_guard.sh"
        if not path.exists():
            pytest.skip("user_prompt_guard.sh not found")
        text = path.read_text()
        assert "SUGGEST" in text or "suggest" in text.lower(), (
            "user_prompt_guard.sh must output SUGGEST lines for semantic keywords (Section 12.7)"
        )

    def test_semantic_keywords_cover_agents(self) -> None:
        """Must detect keywords for at least security and architecture agents."""
        path = HOOKS_DIR / "user_prompt_guard.sh"
        if not path.exists():
            pytest.skip("user_prompt_guard.sh not found")
        text = path.read_text().lower()
        has_security = ("rls" in text or "security" in text) if "suggest" in text else "rls" in text
        has_arch = "layer" in text or "architect" in text or "port" in text
        assert has_security or has_arch, (
            "user_prompt_guard.sh must detect semantic keywords "
            "for security/architecture (Section 12.7)"
        )

    def test_semantic_keywords_cover_tdd(self) -> None:
        """Must suggest diyu-tdd-guide for test/tdd/coverage keywords."""
        path = HOOKS_DIR / "user_prompt_guard.sh"
        if not path.exists():
            pytest.skip("user_prompt_guard.sh not found")
        text = path.read_text()
        suggest_lines = [line for line in text.splitlines() if "SUGGEST" in line]
        has_tdd = any("tdd" in line.lower() or "test" in line.lower() for line in suggest_lines)
        assert has_tdd, (
            "user_prompt_guard.sh must suggest diyu-tdd-guide "
            "for test/tdd/coverage keywords (Section 12.7)"
        )

    def test_semantic_keywords_cover_audit(self) -> None:
        """Must suggest audit skills for audit/review keywords."""
        path = HOOKS_DIR / "user_prompt_guard.sh"
        if not path.exists():
            pytest.skip("user_prompt_guard.sh not found")
        text = path.read_text()
        suggest_lines = [line for line in text.splitlines() if "SUGGEST" in line]
        has_audit = any(
            "audit" in line.lower() or "systematic" in line.lower() for line in suggest_lines
        )
        assert has_audit, (
            "user_prompt_guard.sh must suggest systematic-review/cross-reference-audit "
            "for audit/review keywords (Section 12.7)"
        )

    def test_semantic_keywords_cover_port_compat(self) -> None:
        """Must suggest guard-port-compat for port contract keywords."""
        path = HOOKS_DIR / "user_prompt_guard.sh"
        if not path.exists():
            pytest.skip("user_prompt_guard.sh not found")
        text = path.read_text()
        suggest_lines = [line for line in text.splitlines() if "SUGGEST" in line]
        has_port = any(
            "port" in line.lower() and "compat" in line.lower() for line in suggest_lines
        )
        assert has_port, (
            "user_prompt_guard.sh must suggest guard-port-compat "
            "for port contract/breaking change keywords (Section 12.7)"
        )
