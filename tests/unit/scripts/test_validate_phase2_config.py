"""Tests for validate_phase2_config.py TCP probe and DI.

TDD RED: Verify that:
  - validate() accepts optional tcp_prober for service reachability
  - When tcp_prober is provided, unreachable services produce errors
  - When tcp_prober is None (default), no TCP checks run (existing behavior)
  - Config path can be injected via config_path parameter

Uses DI (tcp_prober callable, config_path) -- no runtime mocking.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import validate_phase2_config


class TestValidateExistingBehavior:
    """Existing validation behavior must be preserved."""

    def test_valid_config_passes(self, tmp_path: Path):
        """A fully valid config must produce zero errors."""
        config = _make_valid_config()
        errors = validate_phase2_config.validate(config)
        assert len(errors) == 0, f"Valid config should pass, got: {errors}"

    def test_missing_primary_llm_fails(self, tmp_path: Path):
        config = _make_valid_config()
        config["llm"]["primary"] = None
        errors = validate_phase2_config.validate(config)
        assert any(e["section"] == "llm" for e in errors)


class TestTcpProbe:
    """Verify TCP probe integration via DI."""

    def test_validate_with_tcp_prober_checks_services(self, tmp_path: Path):
        """When tcp_prober returns False, validation must report error."""
        config = _make_valid_config()

        def failing_prober(host: str, port: int) -> bool:
            return False

        errors = validate_phase2_config.validate(config, tcp_prober=failing_prober)
        tcp_errors = [
            e
            for e in errors
            if "reachable" in e.get("message", "").lower()
            or "unreachable" in e.get("message", "").lower()
        ]
        assert len(tcp_errors) > 0, "TCP probe failures should produce errors"

    def test_validate_with_tcp_prober_passes_when_reachable(self, tmp_path: Path):
        """When tcp_prober returns True, no TCP-related errors."""
        config = _make_valid_config()

        def ok_prober(host: str, port: int) -> bool:
            return True

        errors = validate_phase2_config.validate(config, tcp_prober=ok_prober)
        tcp_errors = [
            e
            for e in errors
            if "reachable" in e.get("message", "").lower()
            or "unreachable" in e.get("message", "").lower()
        ]
        assert len(tcp_errors) == 0

    def test_validate_without_tcp_prober_no_tcp_errors(self, tmp_path: Path):
        """Default (no tcp_prober) must not produce TCP errors."""
        config = _make_valid_config()
        errors = validate_phase2_config.validate(config)
        tcp_errors = [
            e
            for e in errors
            if "reachable" in e.get("message", "").lower()
            or "unreachable" in e.get("message", "").lower()
        ]
        assert len(tcp_errors) == 0


class TestConfigPathDI:
    """Verify config_path DI for load_config."""

    def test_load_config_with_custom_path(self, tmp_path: Path):
        """load_config must accept config_path parameter."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text(yaml.dump(_make_valid_config()))

        result = validate_phase2_config.load_config(config_path=config_file)
        assert "_error" not in result
        assert "llm" in result

    def test_load_config_missing_file_returns_error(self, tmp_path: Path):
        """Missing config file must return _error dict."""
        result = validate_phase2_config.load_config(
            config_path=tmp_path / "nonexistent.yaml",
        )
        assert "_error" in result


def _make_valid_config() -> dict:
    """Create a minimal valid Phase 2 config."""
    return {
        "llm": {
            "primary": "openai",
            "fallback_chain": [],
            "providers": {
                "openai": {
                    "env_key": "OPENAI_API_KEY",
                    "models": ["gpt-4o"],
                },
            },
        },
        "billing": {
            "enforcement": {
                "pre_check": True,
                "post_settle": True,
            },
        },
        "realtime": {"primary": "websocket"},
        "storage": {"file_upload": {"flow": "3-step"}},
        "embedding": {"ddl_dimension": 1024},
        "database": {"primary": {"env_key": "DATABASE_URL"}},
        "redis": {"env_key": "REDIS_URL", "test": {"db": 15}},
    }
