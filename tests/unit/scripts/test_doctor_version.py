"""Tests for doctor.py version comparison logic.

TDD RED: These tests verify semantic version comparison,
not just major version prefix matching.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import doctor


class TestVersionComparison:
    """Verify _check_command correctly compares semantic versions."""

    def test_version_below_minimum_is_not_ok(self):
        """A version below min must return FAIL, not OK."""
        from unittest.mock import patch

        # Mock _get_version to return "Python 3.10.12"
        with patch.object(doctor, "_get_version", return_value="Python 3.10.12"):
            result = doctor._check_command("Python", "python3", ["--version"], "3.12")
        assert result.status != "OK", f"3.10.12 should not pass >=3.12 check, got {result.status}"

    def test_version_at_minimum_is_ok(self):
        """A version at min must return OK."""
        from unittest.mock import patch

        with patch.object(doctor, "_get_version", return_value="Python 3.12.0"):
            result = doctor._check_command("Python", "python3", ["--version"], "3.12")
        assert result.status == "OK"

    def test_version_above_minimum_is_ok(self):
        """A version above min must return OK."""
        from unittest.mock import patch

        with patch.object(doctor, "_get_version", return_value="v22.5.1"):
            result = doctor._check_command("Node.js", "node", ["--version"], "22")
        assert result.status == "OK"


class TestParseVersion:
    """Test the version parsing helper."""

    @pytest.mark.smoke
    def test_parse_version_exists(self):
        """doctor module must have _parse_version function."""
        assert hasattr(doctor, "_parse_version")

    def test_parse_simple(self):
        assert doctor._parse_version("3.12.1") == (3, 12, 1)

    def test_parse_two_part(self):
        assert doctor._parse_version("3.12") == (3, 12)

    def test_parse_single(self):
        assert doctor._parse_version("22") == (22,)

    def test_parse_with_v_prefix(self):
        assert doctor._parse_version("v20.19.4") == (20, 19, 4)

    def test_compare_310_vs_312(self):
        assert doctor._parse_version("3.10.12") < doctor._parse_version("3.12")

    def test_compare_312_vs_312(self):
        assert doctor._parse_version("3.12.0") >= doctor._parse_version("3.12")

    def test_compare_313_vs_312(self):
        assert doctor._parse_version("3.13.1") >= doctor._parse_version("3.12")

    def test_compare_20_vs_22(self):
        assert doctor._parse_version("20.19.4") < doctor._parse_version("22")


class TestPythonUvFallback:
    """doctor must try 'uv run python3' when system python3 is too old."""

    def test_python_check_uses_uv_fallback(self):
        """If python3 < 3.12 but uv run python3 >= 3.12, result should be OK."""
        from unittest.mock import patch

        call_log = []

        def mock_get_version(cmd):
            call_log.append(cmd)
            if cmd == ["python3", "--version"]:
                return "Python 3.10.12"
            if cmd == ["uv", "run", "python3", "--version"]:
                return "Python 3.12.10"
            return None

        with (
            patch.object(doctor, "_get_version", side_effect=mock_get_version),
            patch("shutil.which", return_value="/usr/bin/python3"),
        ):
            result = doctor._check_command("Python", "python3", ["--version"], "3.12")

        assert result.status == "OK", (
            f"Expected OK from uv fallback, got {result.status}: {result.detail}"
        )
        assert any("uv" in str(c) for c in call_log), "doctor did not try uv fallback"

    def test_python_check_fails_when_both_too_old(self):
        """If both python3 and uv run python3 are < 3.12, result should be FAIL."""
        from unittest.mock import patch

        def mock_get_version(cmd):
            if cmd == ["python3", "--version"]:
                return "Python 3.10.12"
            if cmd == ["uv", "run", "python3", "--version"]:
                return "Python 3.10.12"
            return None

        with (
            patch.object(doctor, "_get_version", side_effect=mock_get_version),
            patch("shutil.which", return_value="/usr/bin/python3"),
        ):
            result = doctor._check_command("Python", "python3", ["--version"], "3.12")

        assert result.status == "FAIL"


class TestNodeNvmrcFallback:
    """doctor must detect .nvmrc and check nvm-managed node."""

    def test_nvmrc_file_created(self):
        """Project root must have .nvmrc pinning Node >= 22."""
        nvmrc_path = Path(__file__).resolve().parents[3] / ".nvmrc"
        assert nvmrc_path.exists(), ".nvmrc not found in project root"
        version = nvmrc_path.read_text().strip()
        major = int(version.split(".")[0].lstrip("v"))
        assert major >= 22, f".nvmrc pins Node {version}, expected >= 22"

    def test_python_version_file_created(self):
        """Project root must have .python-version pinning >= 3.12."""
        pv_path = Path(__file__).resolve().parents[3] / ".python-version"
        assert pv_path.exists(), ".python-version not found in project root"
        version = pv_path.read_text().strip()
        parts = version.split(".")
        assert int(parts[0]) >= 3 and int(parts[1]) >= 12, (
            f".python-version is {version}, expected >= 3.12"
        )
