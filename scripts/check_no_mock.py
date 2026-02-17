#!/usr/bin/env python3
"""Detect banned runtime mock patterns in Python source files.

Banned patterns (runtime patch):
  - unittest.mock.patch / mock.patch / @patch
  - MagicMock / AsyncMock (direct usage)
  - monkeypatch.setattr

Allowed patterns (Port DI adapters):
  - Classes implementing Port ABCs with preset return values
  - Fixture functions returning dataclass instances

Line-level exemption:
  Add ``# no-mock-exempt`` (optionally followed by ``: <reason>``) to any
  source line to suppress violations on that line.

Usage:
    uv run python scripts/check_no_mock.py src/ tests/
    uv run python scripts/check_no_mock.py --json src/ tests/

Exit codes:
    0 - No banned patterns found
    1 - Banned patterns detected
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

BANNED_IMPORTS = {
    "unittest.mock",
    "mock",
}

BANNED_NAMES = {
    "MagicMock",
    "AsyncMock",
    "patch",
    "mock_open",
}

BANNED_ATTR_CALLS = {
    "monkeypatch.setattr",
    "monkeypatch.delattr",
    "mock.patch",
    "unittest.mock.patch",
}


EXEMPT_MARKER = "# no-mock-exempt"


class MockDetector(ast.NodeVisitor):
    def __init__(self, filepath: str, source_lines: list[str]) -> None:
        self.filepath = filepath
        self.source_lines = source_lines
        self.violations: list[dict[str, object]] = []

    def _is_exempt(self, lineno: int) -> bool:
        """Return True if the source line contains the exemption marker."""
        if 1 <= lineno <= len(self.source_lines):
            return EXEMPT_MARKER in self.source_lines[lineno - 1]
        return False

    def _add_violation(self, lineno: int, pattern: str, rule: str) -> None:
        if not self._is_exempt(lineno):
            self.violations.append(
                {
                    "file": self.filepath,
                    "line": lineno,
                    "pattern": pattern,
                    "rule": rule,
                }
            )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in BANNED_IMPORTS or alias.name.startswith("unittest.mock"):
                self._add_violation(node.lineno, f"import {alias.name}", "banned-import")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module in BANNED_IMPORTS or module.startswith("unittest.mock"):
            for alias in node.names:
                self._add_violation(
                    node.lineno,
                    f"from {module} import {alias.name}",
                    "banned-import",
                )
        # Check for `from X import MagicMock` even from other modules
        for alias in node.names:
            if alias.name in BANNED_NAMES:
                self._add_violation(
                    node.lineno,
                    f"from {module} import {alias.name}",
                    "banned-name",
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Detect monkeypatch.setattr, mock.patch, etc.
        if isinstance(node.value, ast.Name):
            full = f"{node.value.id}.{node.attr}"
            if full in BANNED_ATTR_CALLS:
                self._add_violation(node.lineno, full, "banned-call")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in BANNED_NAMES:
            self._add_violation(node.lineno, node.id, "banned-name")
        self.generic_visit(node)


def scan_file(filepath: Path) -> list[dict[str, object]]:
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    detector = MockDetector(str(filepath), source.splitlines())
    detector.visit(tree)
    return detector.violations


def scan_dirs(
    directories: list[str],
    *,
    skip_conftest: bool = True,
) -> list[dict[str, object]]:
    all_violations: list[dict[str, object]] = []
    for d in directories:
        root = Path(d)
        if not root.exists():
            continue
        for py_file in sorted(root.rglob("*.py")):
            if skip_conftest and py_file.name == "conftest.py":
                continue
            all_violations.extend(scan_file(py_file))
    return all_violations


def main() -> None:
    args = sys.argv[1:]
    json_output = "--json" in args
    dirs = [a for a in args if not a.startswith("--")]

    if not dirs:
        print("Usage: check_no_mock.py [--json] <dir1> [dir2] ...", file=sys.stderr)
        sys.exit(2)

    violations = scan_dirs(dirs)

    if json_output:
        print(
            json.dumps(
                {
                    "tool": "check_no_mock",
                    "directories": dirs,
                    "violations": violations,
                    "count": len(violations),
                    "status": "fail" if violations else "pass",
                },
                indent=2,
            )
        )
    else:
        if violations:
            print(f"FAIL: {len(violations)} banned mock pattern(s) detected:\n")
            for v in violations:
                print(f"  {v['file']}:{v['line']} [{v['rule']}] {v['pattern']}")
            print(
                "\nAllowed alternative: implement Port ABC with preset return values "
                "(DI adapter pattern)."
            )
        else:
            print(f"PASS: No banned mock patterns in {', '.join(dirs)}")

    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
