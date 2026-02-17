"""Tests for check_no_mock.py conftest skip and scan_dirs DI.

TDD RED: Verify that:
  - conftest.py files are skipped by default
  - skip_conftest=False scans conftest files
  - scan_dirs accepts skip_conftest parameter
  - scan_file still detects violations in non-conftest files

Uses DI (direct function calls + tmp_path) -- no runtime mocking.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import check_no_mock


class TestConftestSkip:
    """Verify conftest.py files are skipped by default."""

    def test_scan_dirs_skips_conftest_by_default(self, tmp_path: Path):
        """conftest.py with banned patterns must not produce violations by default."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        conftest = test_dir / "conftest.py"
        conftest.write_text("from unittest.mock import patch\n")

        violations = check_no_mock.scan_dirs(
            [str(test_dir)],
        )
        assert len(violations) == 0, f"conftest.py should be skipped by default, got {violations}"

    def test_scan_dirs_includes_conftest_when_opt_in(self, tmp_path: Path):
        """conftest.py must be scanned when skip_conftest=False."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        conftest = test_dir / "conftest.py"
        conftest.write_text("from unittest.mock import patch\n")

        violations = check_no_mock.scan_dirs(
            [str(test_dir)],
            skip_conftest=False,
        )
        assert len(violations) > 0, "conftest.py should be scanned with skip_conftest=False"

    def test_scan_dirs_still_catches_non_conftest(self, tmp_path: Path):
        """Regular test files with banned patterns must still be caught."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_example.py"
        test_file.write_text("from unittest.mock import MagicMock\n")

        violations = check_no_mock.scan_dirs([str(test_dir)])
        assert len(violations) >= 1

    def test_nested_conftest_skipped(self, tmp_path: Path):
        """conftest.py in subdirectories must also be skipped."""
        sub = tmp_path / "tests" / "unit"
        sub.mkdir(parents=True)
        conftest = sub / "conftest.py"
        conftest.write_text("import unittest.mock\n")

        violations = check_no_mock.scan_dirs([str(tmp_path / "tests")])
        assert len(violations) == 0


class TestNoMockExempt:
    """Verify # no-mock-exempt line-level exemption."""

    def test_exempt_import_skipped(self, tmp_path: Path):
        """Line with # no-mock-exempt must not produce a violation."""
        f = tmp_path / "test_ex.py"
        f.write_text("from unittest.mock import patch  # no-mock-exempt: legacy SDK\n")

        violations = check_no_mock.scan_file(f)
        assert len(violations) == 0

    def test_exempt_name_skipped(self, tmp_path: Path):
        """MagicMock usage with # no-mock-exempt must be skipped."""
        f = tmp_path / "test_ex.py"
        f.write_text(
            "from unittest.mock import MagicMock  # no-mock-exempt: third-party\n"
            "x = MagicMock()  # no-mock-exempt: no DI available\n"
        )

        violations = check_no_mock.scan_file(f)
        assert len(violations) == 0

    def test_non_exempt_still_caught(self, tmp_path: Path):
        """Lines WITHOUT # no-mock-exempt must still produce violations."""
        f = tmp_path / "test_ex.py"
        f.write_text(
            "from unittest.mock import patch  # no-mock-exempt: ok\n"
            "from unittest.mock import MagicMock\n"
        )

        violations = check_no_mock.scan_file(f)
        assert len(violations) >= 1
        assert all(v["line"] == 2 for v in violations)

    def test_exempt_attr_call_skipped(self, tmp_path: Path):
        """monkeypatch.setattr with # no-mock-exempt must be skipped."""
        f = tmp_path / "test_ex.py"
        f.write_text("monkeypatch.setattr(obj, 'x', 1)  # no-mock-exempt: fixture\n")

        violations = check_no_mock.scan_file(f)
        assert len(violations) == 0

    def test_exempt_requires_reason(self, tmp_path: Path):
        """Bare # no-mock-exempt (no colon+reason) must still suppress."""
        f = tmp_path / "test_ex.py"
        f.write_text("from unittest.mock import patch  # no-mock-exempt\n")

        violations = check_no_mock.scan_file(f)
        assert len(violations) == 0
