#!/usr/bin/env python3
"""Temporal Integrity Verification Script.

Verifies migration chain integrity + rollback coverage:
  1. Migration chain: Alembic versions have no gaps, no orphaned heads, linear chain
  2. Rollback coverage: Every upgrade() has a corresponding non-empty downgrade()
  3. Idempotency check: Static analysis of up/down symmetry (--skip-db mode)
  4. Schema version monotonicity: Version fields only increment, never decrement

Red line alignment: "NO migrations without rollback plan" (CLAUDE.md)

Usage:
    python scripts/check_temporal_integrity.py --json
    python scripts/check_temporal_integrity.py --json --verbose
    python scripts/check_temporal_integrity.py --json --skip-db

Exit codes:
    0: PASS (all checks pass)
    1: FAIL (integrity violations detected)
"""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIGRATIONS_DIR = Path("migrations/versions")

# Pattern to detect empty function body (pass-only)
_PASS_ONLY_BODY = {"pass"}

# Pattern to detect migration metadata
_REVISION_RE = re.compile(r'^revision\s*=\s*["\'](.+)["\']', re.MULTILINE)
_DOWN_REVISION_RE = re.compile(r"^down_revision\s*=\s*(.+)$", re.MULTILINE)
_REVERSIBLE_RE = re.compile(r'^reversible_type\s*=\s*["\'](.+)["\']', re.MULTILINE)
_ROLLBACK_RE = re.compile(r'^rollback_artifact\s*=\s*["\'](.+)["\']', re.MULTILINE)

# Pattern to detect version-related columns
_VERSION_COL_RE = re.compile(
    r"(?:content_schema_version|payload_version|version|schema_version)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MigrationInfo:
    """Parsed migration file information."""

    file: str
    revision: str
    down_revision: str | None
    reversible_type: str
    rollback_artifact: str
    has_upgrade: bool
    has_downgrade: bool
    downgrade_is_empty: bool  # pass-only body
    upgrade_ops: list[str]  # operation types (create_table, add_column, etc.)
    downgrade_ops: list[str]

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "revision": self.revision,
            "down_revision": self.down_revision,
            "reversible_type": self.reversible_type,
            "rollback_artifact": self.rollback_artifact,
            "has_upgrade": self.has_upgrade,
            "has_downgrade": self.has_downgrade,
            "downgrade_is_empty": self.downgrade_is_empty,
            "upgrade_ops": self.upgrade_ops,
            "downgrade_ops": self.downgrade_ops,
        }


@dataclass
class IntegrityFinding:
    """A single integrity finding."""

    check_type: str  # chain, rollback, symmetry, version
    severity: str  # error, warning
    file: str
    message: str

    def to_dict(self) -> dict:
        return {
            "check_type": self.check_type,
            "severity": self.severity,
            "file": self.file,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# AST analysis helpers
# ---------------------------------------------------------------------------


def _extract_func_ops(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract operation type names from a function body.

    Looks for op.create_table, op.drop_table, op.add_column, etc.
    """
    ops: list[str] = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            # Filter to known Alembic operations
            if (isinstance(node.func.value, ast.Name) and node.func.value.id == "op") or attr in (
                "create_table",
                "drop_table",
                "add_column",
                "drop_column",
                "alter_column",
                "create_index",
                "drop_index",
                "create_unique_constraint",
                "drop_constraint",
                "execute",
                "rename_table",
                "create_foreign_key",
                "create_check_constraint",
            ):
                ops.append(attr)
    return ops


def _is_empty_body(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function body is empty (just 'pass' or docstring + pass)."""
    stmts = func_node.body
    # Filter out docstrings
    non_doc = [
        s
        for s in stmts
        if not (
            isinstance(s, ast.Expr)
            and isinstance(s.value, ast.Constant)
            and isinstance(s.value.value, str)
        )
    ]
    if not non_doc:
        return True
    return len(non_doc) == 1 and isinstance(non_doc[0], ast.Pass)


# ---------------------------------------------------------------------------
# Migration parsing
# ---------------------------------------------------------------------------


def parse_migration(filepath: Path) -> MigrationInfo | None:
    """Parse a single migration file."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return None

    # Extract metadata via regex (more reliable for string constants)
    rev_match = _REVISION_RE.search(source)
    down_match = _DOWN_REVISION_RE.search(source)
    rev_type_match = _REVERSIBLE_RE.search(source)
    rollback_match = _ROLLBACK_RE.search(source)

    revision = rev_match.group(1) if rev_match else filepath.stem
    down_rev_raw = down_match.group(1).strip() if down_match else "None"
    down_revision = None if down_rev_raw == "None" else down_rev_raw.strip("'\"")

    reversible_type = rev_type_match.group(1) if rev_type_match else "unknown"
    rollback_artifact = rollback_match.group(1) if rollback_match else ""

    # Find upgrade() and downgrade() functions
    has_upgrade = False
    has_downgrade = False
    downgrade_empty = True
    upgrade_ops: list[str] = []
    downgrade_ops: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "upgrade":
                has_upgrade = True
                upgrade_ops = _extract_func_ops(node)
            elif node.name == "downgrade":
                has_downgrade = True
                downgrade_empty = _is_empty_body(node)
                downgrade_ops = _extract_func_ops(node)

    return MigrationInfo(
        file=str(filepath),
        revision=revision,
        down_revision=down_revision,
        reversible_type=reversible_type,
        rollback_artifact=rollback_artifact,
        has_upgrade=has_upgrade,
        has_downgrade=has_downgrade,
        downgrade_is_empty=downgrade_empty,
        upgrade_ops=upgrade_ops,
        downgrade_ops=downgrade_ops,
    )


def parse_all_migrations(
    *,
    migrations_dir: Path | None = None,
) -> list[MigrationInfo]:
    """Parse all migration files in order."""
    effective_dir = migrations_dir if migrations_dir is not None else MIGRATIONS_DIR

    if not effective_dir.exists():
        return []

    migrations: list[MigrationInfo] = []
    for py in sorted(effective_dir.glob("*.py")):
        if py.name == "__init__.py" or py.name.startswith("__"):
            continue
        info = parse_migration(py)
        if info:
            migrations.append(info)

    return migrations


# ---------------------------------------------------------------------------
# Check 1: Chain Integrity
# ---------------------------------------------------------------------------


def check_chain_integrity(migrations: list[MigrationInfo]) -> list[IntegrityFinding]:
    """Verify migration chain has no gaps or orphaned heads."""
    findings: list[IntegrityFinding] = []

    if not migrations:
        findings.append(
            IntegrityFinding(
                check_type="chain",
                severity="warning",
                file="(none)",
                message="No migration files found",
            )
        )
        return findings

    # Build revision map
    rev_map: dict[str, MigrationInfo] = {}
    for m in migrations:
        if m.revision in rev_map:
            findings.append(
                IntegrityFinding(
                    check_type="chain",
                    severity="error",
                    file=m.file,
                    message=(
                        f"Duplicate revision '{m.revision}' (also in {rev_map[m.revision].file})"
                    ),
                )
            )
        rev_map[m.revision] = m

    # Check chain linkage
    all_revisions = set(rev_map.keys())
    all_down_revisions = {m.down_revision for m in migrations if m.down_revision is not None}

    # Roots (down_revision = None)
    roots = [m for m in migrations if m.down_revision is None]
    if len(roots) == 0:
        findings.append(
            IntegrityFinding(
                check_type="chain",
                severity="error",
                file="(none)",
                message="No root migration found (all migrations have down_revision)",
            )
        )
    elif len(roots) > 1:
        root_files = [r.file for r in roots]
        findings.append(
            IntegrityFinding(
                check_type="chain",
                severity="error",
                file=root_files[0],
                message=f"Multiple root migrations (should be exactly 1): {root_files}",
            )
        )

    # Heads (revisions not referenced as down_revision by anyone)
    heads = all_revisions - all_down_revisions
    if len(heads) > 1:
        head_files = [rev_map[h].file for h in heads if h in rev_map]
        findings.append(
            IntegrityFinding(
                check_type="chain",
                severity="error",
                file=head_files[0] if head_files else "(unknown)",
                message=f"Multiple heads detected (branch): {sorted(heads)}",
            )
        )

    # Check for broken links (down_revision points to non-existent revision)
    for m in migrations:
        if m.down_revision is not None and m.down_revision not in rev_map:
            findings.append(
                IntegrityFinding(
                    check_type="chain",
                    severity="error",
                    file=m.file,
                    message=f"Broken chain: down_revision '{m.down_revision}' does not exist",
                )
            )

    # Walk the chain from root to head to verify connectivity
    if len(roots) == 1:
        visited: set[str] = set()
        current: str | None = roots[0].revision
        while current:
            if current in visited:
                findings.append(
                    IntegrityFinding(
                        check_type="chain",
                        severity="error",
                        file=rev_map.get(current, migrations[0]).file,
                        message=f"Cycle detected at revision '{current}'",
                    )
                )
                break
            visited.add(current)
            # Find next revision that has this as down_revision
            next_rev = None
            for m in migrations:
                if m.down_revision == current:
                    next_rev = m.revision
                    break
            current = next_rev

        unreachable = all_revisions - visited
        if unreachable:
            for rev in sorted(unreachable):
                findings.append(
                    IntegrityFinding(
                        check_type="chain",
                        severity="error",
                        file=rev_map[rev].file,
                        message=f"Orphaned revision '{rev}' not reachable from root",
                    )
                )

    if not findings:
        findings.append(
            IntegrityFinding(
                check_type="chain",
                severity="info",
                file="(all)",
                message=f"Chain integrity OK: {len(migrations)} migrations, linear chain",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Check 2: Rollback Coverage
# ---------------------------------------------------------------------------


def check_rollback_coverage(migrations: list[MigrationInfo]) -> list[IntegrityFinding]:
    """Verify every upgrade() has a non-empty downgrade()."""
    findings: list[IntegrityFinding] = []

    for m in migrations:
        if not m.has_upgrade:
            findings.append(
                IntegrityFinding(
                    check_type="rollback",
                    severity="error",
                    file=m.file,
                    message=f"Migration '{m.revision}' has no upgrade() function",
                )
            )
            continue

        if not m.has_downgrade:
            findings.append(
                IntegrityFinding(
                    check_type="rollback",
                    severity="error",
                    file=m.file,
                    message=(
                        f"Migration '{m.revision}' has no downgrade() function "
                        f"(Red Line: NO migrations without rollback plan)"
                    ),
                )
            )
        elif m.downgrade_is_empty:
            findings.append(
                IntegrityFinding(
                    check_type="rollback",
                    severity="error",
                    file=m.file,
                    message=f"Migration '{m.revision}' has empty downgrade() (pass-only body)",
                )
            )
        else:
            # Check metadata consistency
            if m.reversible_type == "unknown":
                findings.append(
                    IntegrityFinding(
                        check_type="rollback",
                        severity="warning",
                        file=m.file,
                        message=f"Migration '{m.revision}' missing reversible_type metadata",
                    )
                )
            if not m.rollback_artifact:
                findings.append(
                    IntegrityFinding(
                        check_type="rollback",
                        severity="warning",
                        file=m.file,
                        message=f"Migration '{m.revision}' missing rollback_artifact metadata",
                    )
                )

    if not any(f.severity == "error" for f in findings if f.check_type == "rollback"):
        findings.append(
            IntegrityFinding(
                check_type="rollback",
                severity="info",
                file="(all)",
                message=(
                    f"Rollback coverage OK: {len(migrations)} migrations, "
                    f"all have non-empty downgrade()"
                ),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Check 3: Up/Down Symmetry (Static Analysis)
# ---------------------------------------------------------------------------

# Map upgrade ops to expected downgrade ops
_SYMMETRIC_OPS = {
    "create_table": "drop_table",
    "add_column": "drop_column",
    "create_index": "drop_index",
    "create_unique_constraint": "drop_constraint",
    "create_foreign_key": "drop_constraint",
    "create_check_constraint": "drop_constraint",
}


def check_symmetry(migrations: list[MigrationInfo]) -> list[IntegrityFinding]:
    """Check upgrade/downgrade operation symmetry."""
    findings: list[IntegrityFinding] = []

    for m in migrations:
        if not m.upgrade_ops or not m.downgrade_ops:
            continue

        # Count expected reverse operations
        expected_down: dict[str, int] = {}
        for op in m.upgrade_ops:
            reverse = _SYMMETRIC_OPS.get(op)
            if reverse:
                expected_down[reverse] = expected_down.get(reverse, 0) + 1

        # Count actual downgrade operations
        actual_down: dict[str, int] = {}
        for op in m.downgrade_ops:
            actual_down[op] = actual_down.get(op, 0) + 1

        # Compare
        for expected_op, expected_count in expected_down.items():
            actual_count = actual_down.get(expected_op, 0)
            if actual_count < expected_count:
                findings.append(
                    IntegrityFinding(
                        check_type="symmetry",
                        severity="warning",
                        file=m.file,
                        message=(
                            f"Migration '{m.revision}': upgrade has "
                            f"{expected_count} "
                            f"{list(_SYMMETRIC_OPS.keys())[list(_SYMMETRIC_OPS.values()).index(expected_op)]}"
                            f" but downgrade has only {actual_count} {expected_op}"
                        ),
                    )
                )

    if not findings:
        findings.append(
            IntegrityFinding(
                check_type="symmetry",
                severity="info",
                file="(all)",
                message="Up/down symmetry OK: all migrations have symmetric operations",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Check 4: Version Monotonicity
# ---------------------------------------------------------------------------


def check_version_monotonicity(
    migrations: list[MigrationInfo],
) -> list[IntegrityFinding]:
    """Check that version-related columns are only added/incremented, never decremented."""
    findings: list[IntegrityFinding] = []

    for m in migrations:
        # Check if any downgrade operation alters version columns
        # This is a static approximation - we look for version-related
        # column names in the migration source
        filepath = Path(m.file)
        try:
            source = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # In downgrade, check for version column manipulation
        in_downgrade = False
        for line in source.splitlines():
            if "def downgrade" in line:
                in_downgrade = True
            elif line.startswith("def ") and in_downgrade:
                in_downgrade = False

            if in_downgrade and _VERSION_COL_RE.search(line):
                # It's OK to drop_column a version col in downgrade (reversing an add_column)
                if "drop_column" in line:
                    continue
                # But altering or decrementing is suspicious
                if "alter_column" in line:
                    findings.append(
                        IntegrityFinding(
                            check_type="version",
                            severity="warning",
                            file=m.file,
                            message=(
                                f"Migration '{m.revision}': downgrade() alters a version column"
                            ),
                        )
                    )

    if not findings:
        findings.append(
            IntegrityFinding(
                check_type="version",
                severity="info",
                file="(all)",
                message="Version monotonicity OK: no version column decrements detected",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    findings: list[IntegrityFinding],
    migrations: list[MigrationInfo],
    *,
    verbose: bool = False,
) -> dict:
    """Build the JSON report."""
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    by_check: dict[str, dict[str, int]] = {}
    for f in findings:
        if f.check_type not in by_check:
            by_check[f.check_type] = {"error": 0, "warning": 0, "info": 0}
        by_check[f.check_type][f.severity] += 1

    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    report: dict = {
        "status": status,
        "summary": {
            "total_migrations": len(migrations),
            "total_findings": len(findings),
            "errors": len(errors),
            "warnings": len(warnings),
            "by_check": by_check,
        },
        "errors": [f.to_dict() for f in errors],
        "warnings": [f.to_dict() for f in warnings],
    }

    if verbose:
        report["all_findings"] = [f.to_dict() for f in findings]
        report["migrations"] = [m.to_dict() for m in migrations]

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    use_json = "--json" in sys.argv
    verbose = "--verbose" in sys.argv
    skip_db = "--skip-db" in sys.argv

    if not use_json:
        print("=== Temporal Integrity Verification ===")
        if skip_db:
            print("Mode: static analysis (--skip-db)")
        else:
            # DB mode not yet implemented; default to static analysis
            print("Mode: static analysis (DB mode not yet implemented)")

    # Parse migrations
    migrations = parse_all_migrations()

    if not use_json:
        print(f"Found {len(migrations)} migration files")

    # Run all checks
    findings: list[IntegrityFinding] = []

    if not use_json:
        print("\n[1/4] Chain integrity...")
    findings.extend(check_chain_integrity(migrations))

    if not use_json:
        print("[2/4] Rollback coverage...")
    findings.extend(check_rollback_coverage(migrations))

    if not use_json:
        print("[3/4] Up/down symmetry...")
    findings.extend(check_symmetry(migrations))

    if not use_json:
        print("[4/4] Version monotonicity...")
    findings.extend(check_version_monotonicity(migrations))

    report = generate_report(findings, migrations, verbose=verbose)

    if use_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print(
            f"\nMigrations: {s['total_migrations']}, "
            f"Findings: {s['total_findings']} "
            f"(errors={s['errors']}, warnings={s['warnings']})"
        )
        if report["errors"]:
            print("\nErrors:")
            for e in report["errors"]:
                print(f"  [{e['check_type']}] {e['file']}: {e['message']}")
        if report["warnings"]:
            print("\nWarnings:")
            for w in report["warnings"]:
                print(f"  [{w['check_type']}] {w['file']}: {w['message']}")
        print(f"\n=== Result: {report['status']} ===")

    if report["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
