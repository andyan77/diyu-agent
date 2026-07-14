#!/usr/bin/env python3
"""Reference-safe successor wrapper for the frozen P3 recovery guard."""

from __future__ import annotations

import sys
from pathlib import Path

from p4_resealed import (
    CURRENT_CHECKER,
    P3_RECOVERY_COMMIT,
    P3_RECOVERY_ROOT,
    ROOT,
    TOOL_FREEZE,
    load_yaml,
    sha256_file,
    _git,
)


if not __debug__:
    sys.stderr.write("p3_recovery_guard_current refuses python -O\n")
    raise SystemExit(2)


def validate_p3_recovery_current(root: Path = ROOT) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    recovery_root = root / P3_RECOVERY_ROOT
    if str(recovery_root) not in sys.path:
        sys.path.insert(0, str(recovery_root))
    try:
        from p3_recovery_guard import validate_p3_recovery

        frozen_errors = validate_p3_recovery(root)
        unexpected = [
            item
            for item in frozen_errors
            if item.get("code") != "E_P3R_CURRENT_CHECKER_BINDING"
        ]
        if unexpected:
            errors.extend(unexpected)
        binding_errors = [
            item
            for item in frozen_errors
            if item.get("code") == "E_P3R_CURRENT_CHECKER_BINDING"
        ]
        if len(binding_errors) > 1:
            errors.append({"code": "E_P3R_COMPAT_BINDING_COUNT", "detail": str(len(binding_errors))})
    except (ImportError, OSError, TypeError, ValueError) as exc:
        return [{"code": "E_P3R_COMPAT_IMPORT", "detail": str(exc)}]

    unchanged = _git(
        "diff",
        "--quiet",
        P3_RECOVERY_COMMIT,
        "--",
        P3_RECOVERY_ROOT.as_posix(),
    )
    if unchanged.returncode != 0:
        errors.append({"code": "E_P3R_COMPAT_HISTORY_MUTATION", "detail": "P3 recovery root"})
    try:
        freeze = load_yaml(root / TOOL_FREEZE).get("p4_resealed_tool_freeze")
        if not isinstance(freeze, dict):
            raise TypeError("tool freeze root")
        expected = freeze.get("tool_files", {}).get(CURRENT_CHECKER.as_posix())
        if not isinstance(expected, str) or sha256_file(root / CURRENT_CHECKER) != expected:
            errors.append({"code": "E_P3R_COMPAT_CURRENT_CHECKER", "detail": str(expected)})
        if freeze.get("p3_recovery_commit") != _git("rev-parse", P3_RECOVERY_COMMIT).stdout.strip():
            errors.append({"code": "E_P3R_COMPAT_COMMIT", "detail": str(freeze.get("p3_recovery_commit"))})
    except (OSError, TypeError, ValueError, KeyError) as exc:
        errors.append({"code": "E_P3R_COMPAT_TOOL_FREEZE", "detail": str(exc)})
    return errors


def main() -> int:
    errors = validate_p3_recovery_current(ROOT)
    if errors:
        print({"status": "FAIL", "errors": errors})
        return 1
    print({"status": "PASS", "reference_safe_successor": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
