#!/usr/bin/env python3
"""DIYU Agent development environment diagnostics.

Usage:
    python3 scripts/doctor.py          # Human-readable output
    python3 scripts/doctor.py --json   # JSON output for CI

Exit codes:
    0 - All checks passed (0 FAIL)
    1 - One or more checks failed
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    status: str  # OK, WARN, FAIL
    detail: str
    required_phase: int = 0  # Phase at which this becomes FAIL instead of WARN


@dataclass
class DoctorReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.status == "OK")

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.status == "WARN")

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.status == "FAIL")

    def to_dict(self) -> dict:
        return {
            "checks": [
                {
                    "name": r.name,
                    "status": r.status,
                    "detail": r.detail,
                    "required_phase": r.required_phase,
                }
                for r in self.results
            ],
            "summary": {
                "ok": self.ok_count,
                "warn": self.warn_count,
                "fail": self.fail_count,
                "total": len(self.results),
            },
        }


def _get_version(cmd: list[str]) -> str | None:
    """Run a command and return its stripped stdout, or None on failure."""
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse version string into comparable tuple.

    Examples:
        '3.12.1' -> (3, 12, 1)
        'v20.19.4' -> (20, 19, 4)
        '22' -> (22,)
    """
    cleaned = version_str.lstrip("v")
    parts = re.findall(r"\d+", cleaned)
    return tuple(int(p) for p in parts) if parts else (0,)


def _check_nvm_node(
    version_args: list[str],
    required: tuple[int, ...],
    system_version: str,
    required_phase: int,
    name: str,
) -> CheckResult | None:
    """Try to find a suitable Node.js version via nvm.

    Checks .nvmrc, nvm default alias, and iterates installed versions.
    Returns CheckResult if a suitable version is found, None otherwise.
    """
    import os

    nvm_dir = os.environ.get("NVM_DIR", os.path.expanduser("~/.nvm"))
    versions_dir = Path(nvm_dir) / "versions" / "node"
    if not versions_dir.exists():
        return None

    # Strategy 1: Check .nvmrc in current directory
    nvmrc = Path(".nvmrc")
    target_major = None
    if nvmrc.exists():
        target_major = nvmrc.read_text().strip().lstrip("v")

    # Strategy 2: Find best matching installed version
    candidates: list[tuple[tuple[int, ...], Path]] = []
    for d in versions_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("v"):
            continue
        ver = _parse_version(d.name)
        if ver >= required:
            candidates.append((ver, d))

    if not candidates:
        return None

    # Sort descending, prefer .nvmrc target if specified
    candidates.sort(key=lambda x: x[0], reverse=True)

    if target_major:
        target_tuple = _parse_version(target_major)
        # Find candidate matching .nvmrc major
        for ver, d in candidates:
            if ver[0] == target_tuple[0]:
                node_bin = d / "bin" / "node"
                if node_bin.exists():
                    nvm_output = _get_version([str(node_bin), *version_args])
                    if nvm_output:
                        nvm_ver = nvm_output.split()[-1].lstrip("v")
                        return CheckResult(
                            name,
                            "OK",
                            f"{nvm_ver} (via nvm; system {system_version})",
                            required_phase,
                        )

    # Fallback: use highest version that meets requirement
    ver, d = candidates[0]
    node_bin = d / "bin" / "node"
    if node_bin.exists():
        nvm_output = _get_version([str(node_bin), *version_args])
        if nvm_output:
            nvm_ver = nvm_output.split()[-1].lstrip("v")
            return CheckResult(
                name,
                "OK",
                f"{nvm_ver} (via nvm; system {system_version})",
                required_phase,
            )

    return None


def _check_command(
    name: str,
    cmd: str,
    version_args: list[str],
    min_version_prefix: str,
    required_phase: int = 0,
) -> CheckResult:
    """Check if a command exists and meets minimum version.

    For Python: falls back to ``uv run python3`` when system python3
    is below the required version (common in WSL/system-Python setups
    where the project venv has the correct version).
    """
    path = shutil.which(cmd)
    if path is None:
        status = "FAIL" if required_phase == 0 else "WARN"
        return CheckResult(name, status, f"{cmd} not found", required_phase)

    version_output = _get_version([cmd, *version_args])
    if version_output is None:
        return CheckResult(name, "WARN", f"{cmd} found but version check failed", required_phase)

    # Extract version number from output (find first semver-like token)
    version_clean = "unknown"
    if version_output:
        match = re.search(r"v?(\d+\.\d+[\.\d]*)", version_output)
        version_clean = match.group(1) if match else version_output.split()[-1].lstrip("v")

    actual = _parse_version(version_clean)
    required = _parse_version(min_version_prefix)

    if actual >= required:
        return CheckResult(name, "OK", f"{version_clean}", required_phase)

    # Fallback: try uv-managed Python when system python3 is too old
    if cmd == "python3" and shutil.which("uv"):
        uv_output = _get_version(["uv", "run", cmd, *version_args])
        if uv_output:
            uv_ver_str = uv_output.split()[-1].lstrip("v")
            uv_actual = _parse_version(uv_ver_str)
            if uv_actual >= required:
                return CheckResult(
                    name,
                    "OK",
                    f"{uv_ver_str} (via uv; system {version_clean})",
                    required_phase,
                )

    # Fallback: try nvm-managed Node when system node is too old
    if cmd == "node":
        nvm_result = _check_nvm_node(version_args, required, version_clean, required_phase, name)
        if nvm_result is not None:
            return nvm_result

    return CheckResult(
        name,
        "FAIL" if required_phase == 0 else "WARN",
        f"{version_clean} (expected {min_version_prefix}+)",
        required_phase,
    )


def _check_file(name: str, path: str, required_phase: int = 0) -> CheckResult:
    """Check if a file exists."""
    if Path(path).exists():
        return CheckResult(name, "OK", f"{path} exists", required_phase)
    status = "FAIL" if required_phase == 0 else "WARN"
    return CheckResult(name, status, f"{path} not found", required_phase)


def _check_service(name: str, host: str, port: int, required_phase: int = 1) -> CheckResult:
    """Check if a network service is reachable."""
    import socket

    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return CheckResult(name, "OK", f"{host}:{port} reachable", required_phase)
    except (ConnectionRefusedError, TimeoutError, OSError):
        return CheckResult(
            name,
            "WARN",
            f"{host}:{port} not reachable (needed for Phase {required_phase}+)",
            required_phase,
        )


def run_doctor() -> DoctorReport:
    """Run all diagnostic checks."""
    report = DoctorReport()

    # Phase 0: Required toolchain
    report.results.append(_check_command("Python", "python3", ["--version"], "3.12"))
    report.results.append(_check_command("uv", "uv", ["--version"], "0.5"))
    report.results.append(_check_command("Node.js", "node", ["--version"], "22"))
    report.results.append(_check_command("pnpm", "pnpm", ["--version"], "9"))

    # Phase 0: Required files
    report.results.append(_check_file("pyproject.toml", "pyproject.toml"))
    report.results.append(_check_file("Makefile", "Makefile"))
    report.results.append(_check_file("CLAUDE.md", "CLAUDE.md"))
    report.results.append(_check_file("pnpm-workspace", "frontend/pnpm-workspace.yaml"))

    # Phase 1+: External services
    report.results.append(_check_command("Docker", "docker", ["--version"], "24", 1))
    report.results.append(
        _check_command("Docker Compose", "docker", ["compose", "version"], "2", 1)
    )
    report.results.append(_check_service("PostgreSQL", "localhost", 5432, 1))
    report.results.append(_check_service("Redis", "localhost", 6379, 1))

    # Phase 1+: Security tooling (WARN if missing, CI will catch)
    report.results.append(_check_command("semgrep", "semgrep", ["--version"], "1", 1))
    report.results.append(_check_command("gitleaks", "gitleaks", ["version"], "8", 1))

    # Phase 2+: Optional tooling
    report.results.append(_check_command("gh (GitHub CLI)", "gh", ["--version"], "2", 2))

    return report


def main() -> None:
    use_json = "--json" in sys.argv
    report = run_doctor()

    if use_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for r in report.results:
            icon = {"OK": "[OK]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[r.status]
            print(f"  {icon:8s} {r.name}: {r.detail}")
        print()
        print(
            f"  Summary: {report.ok_count} OK, {report.warn_count} WARN, {report.fail_count} FAIL"
        )

    sys.exit(1 if report.fail_count > 0 else 0)


if __name__ == "__main__":
    main()
