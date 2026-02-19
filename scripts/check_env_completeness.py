#!/usr/bin/env python3
"""Environment Variable Completeness Check.

Scans source code for runtime config references (os.environ, os.getenv,
settings.*) and verifies all keys exist in .env.example.

Usage:
    python3 scripts/check_env_completeness.py [--json]

Exit codes:
    0: All runtime keys covered by .env.example
    1: Missing keys found
    2: Configuration error
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SRC_DIR = Path("src")
ENV_EXAMPLE = Path(".env.example")

# Patterns to extract env var names from Python source
ENV_PATTERNS = [
    re.compile(r'os\.environ\[(["\'])([A-Z_][A-Z0-9_]*)\1\]'),
    re.compile(r'os\.environ\.get\(\s*(["\'])([A-Z_][A-Z0-9_]*)\1'),
    re.compile(r'os\.getenv\(\s*(["\'])([A-Z_][A-Z0-9_]*)\1'),
    re.compile(r'env\s*:\s*str\s*=\s*Field\(.+env\s*=\s*(["\'])([A-Z_][A-Z0-9_]*)\1'),
]

# Keys that are always available (system / Python runtime)
BUILTIN_KEYS = {
    "HOME",
    "PATH",
    "USER",
    "LANG",
    "SHELL",
    "TERM",
    "PWD",
    "PYTHONPATH",
    "VIRTUAL_ENV",
}


def load_env_example_keys(path: Path | None = None) -> set[str]:
    """Extract key names from .env.example."""
    p = path or ENV_EXAMPLE
    if not p.exists():
        print(f"ERROR: {p} not found", file=sys.stderr)
        sys.exit(2)

    keys: set[str] = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            if key:
                keys.add(key)
    return keys


def scan_source_env_refs(src_dir: Path | None = None) -> dict[str, list[str]]:
    """Scan source for env var references.

    Returns: {VAR_NAME: [file:line, ...]}
    """
    base = src_dir or SRC_DIR
    if not base.exists():
        return {}

    refs: dict[str, list[str]] = {}
    for py_file in base.rglob("*.py"):
        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, PermissionError):
            continue
        for i, line in enumerate(lines, 1):
            for pattern in ENV_PATTERNS:
                for match in pattern.finditer(line):
                    var_name = match.group(2)
                    if var_name not in BUILTIN_KEYS:
                        loc = f"{py_file}:{i}"
                        refs.setdefault(var_name, []).append(loc)
    return refs


def main() -> None:
    json_mode = "--json" in sys.argv

    example_keys = load_env_example_keys()
    source_refs = scan_source_env_refs()

    referenced_keys = set(source_refs.keys())
    missing = sorted(referenced_keys - example_keys)
    extra = sorted(example_keys - referenced_keys - BUILTIN_KEYS)

    result = {
        "status": "FAIL" if missing else "PASS",
        "env_example_keys": len(example_keys),
        "source_referenced_keys": len(referenced_keys),
        "missing_from_env_example": missing,
        "extra_in_env_example": extra,
    }

    if missing:
        result["missing_details"] = {k: source_refs[k] for k in missing}

    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if missing:
            print(f"FAIL: {len(missing)} keys referenced in source but missing from .env.example:")
            for k in missing:
                locs = source_refs[k][:3]
                print(f"  {k} (referenced in: {', '.join(locs)})")
        else:
            print(f"PASS: All {len(referenced_keys)} source-referenced keys found in .env.example")
        if extra:
            print(f"  INFO: {len(extra)} extra keys in .env.example (not referenced in source)")

    sys.exit(0 if not missing else 1)


if __name__ == "__main__":
    main()
