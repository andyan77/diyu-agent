#!/usr/bin/env python3
"""Detect vacuous pass (all-skip) patterns in gate-critical test directories.

A "vacuous pass" occurs when a test file or directory reports PASS because
ALL tests are skipped (0 executed = 0 failures = PASS). This gives false
confidence that tests are passing.

This script scans Python test files for pytest.skip() calls and Playwright
test files for test.skip() calls, and flags any file where ALL test
functions/cases are skipped.

Usage:
    uv run python scripts/check_no_vacuous_pass.py tests/e2e/cross/
    uv run python scripts/check_no_vacuous_pass.py --json tests/e2e/cross/ frontend/tests/e2e/cross/
    uv run python scripts/check_no_vacuous_pass.py --strict tests/  # any skip = fail

Exit codes:
    0 - No vacuous pass detected
    1 - Vacuous pass detected (all tests skipped in at least one file)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Python skip patterns (inside function body, not in fixtures)
PY_SKIP_PATTERNS = [
    r"pytest\.skip\(",
    r"@pytest\.mark\.skip\b",
    r"@pytest\.mark\.skipif\b",
    r"@unittest\.skip\b",
]

# TypeScript/Playwright skip patterns
TS_SKIP_PATTERNS = [
    r"test\.skip\(",
    r"describe\.skip\(",
    r"it\.skip\(",
    r"test\.fixme\(",
    r"test\.todo\(",
]

PY_TEST_FUNC_RE = re.compile(r"^\s*(async\s+)?def\s+(test_\w+)")
TS_TEST_FUNC_RE = re.compile(r"""test\(\s*["']""")


def check_python_file(path: Path) -> dict:
    """Check a Python test file for vacuous pass."""
    content = path.read_text()
    lines = content.split("\n")

    test_funcs = []
    skip_funcs = []

    current_func = None
    for line in lines:
        m = PY_TEST_FUNC_RE.match(line)
        if m:
            current_func = m.group(2)
            test_funcs.append(current_func)

        if current_func:
            for pattern in PY_SKIP_PATTERNS:
                if re.search(pattern, line) and current_func not in skip_funcs:
                    skip_funcs.append(current_func)

    # Also check for class-level describe.skip at top of class
    if re.search(r"test\.skip\(", content):
        for pat in PY_SKIP_PATTERNS:
            if re.search(pat, content):
                skip_funcs = test_funcs[:]
                break

    return {
        "file": str(path),
        "total_tests": len(test_funcs),
        "skipped_tests": len(skip_funcs),
        "executed_tests": len(test_funcs) - len(skip_funcs),
        "vacuous": len(test_funcs) > 0 and len(skip_funcs) == len(test_funcs),
        "skip_details": skip_funcs,
    }


def check_ts_file(path: Path) -> dict:
    """Check a TypeScript/Playwright test file for vacuous pass."""
    content = path.read_text()
    lines = content.split("\n")

    # Count test cases
    test_cases = len(TS_TEST_FUNC_RE.findall(content))

    # Check for describe-level skip (entire block skipped)
    describe_skip = bool(re.search(r"test\.skip\(", content))

    # Check for individual test skips
    individual_skips = 0
    for line in lines:
        for pattern in TS_SKIP_PATTERNS:
            if re.search(pattern, line):
                individual_skips += 1
                break

    # If describe-level skip, ALL tests are skipped
    skipped = test_cases if describe_skip else min(individual_skips, test_cases)

    return {
        "file": str(path),
        "total_tests": test_cases,
        "skipped_tests": skipped,
        "executed_tests": test_cases - skipped,
        "vacuous": test_cases > 0 and skipped == test_cases,
        "skip_details": ["describe-level skip"] if describe_skip else [],
    }


def main() -> int:
    args = sys.argv[1:]
    json_mode = "--json" in args
    strict_mode = "--strict" in args
    args = [a for a in args if not a.startswith("--")]

    if not args:
        print("Usage: check_no_vacuous_pass.py [--json] [--strict] <path> ...")
        return 1

    results = []
    for arg in args:
        p = Path(arg)
        files = [p] if p.is_file() else sorted(p.rglob("*.py")) + sorted(p.rglob("*.spec.ts"))

        for f in files:
            if f.suffix == ".py" and f.name.startswith("test_"):
                results.append(check_python_file(f))
            elif f.suffix == ".ts" and ".spec." in f.name:
                results.append(check_ts_file(f))

    vacuous = [r for r in results if r["vacuous"]]
    any_skip = [r for r in results if r["skipped_tests"] > 0]

    if json_mode:
        output = {
            "total_files": len(results),
            "vacuous_files": len(vacuous),
            "any_skip_files": len(any_skip),
            "verdict": "FAIL" if vacuous or (strict_mode and any_skip) else "PASS",
            "details": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Scanned {len(results)} test files")
        for r in results:
            status = "VACUOUS" if r["vacuous"] else "OK"
            if strict_mode and r["skipped_tests"] > 0:
                status = "HAS_SKIP"
            skip_info = (
                f" ({r['skipped_tests']}/{r['total_tests']} skipped)" if r["skipped_tests"] else ""
            )
            print(f"  [{status}] {r['file']}{skip_info}")

        if vacuous:
            print(f"\nFAIL: {len(vacuous)} file(s) have ALL tests skipped (vacuous pass)")
            for v in vacuous:
                print(f"  - {v['file']}")
            return 1

        if strict_mode and any_skip:
            print(f"\nFAIL (strict): {len(any_skip)} file(s) have skipped tests")
            return 1

        print("\nPASS: No vacuous pass detected")

    return 1 if vacuous or (strict_mode and any_skip) else 0


if __name__ == "__main__":
    sys.exit(main())
