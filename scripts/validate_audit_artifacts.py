#!/usr/bin/env python3
"""Validate audit evidence artifacts against their JSON schemas.

Performs:
  1. Schema validation for each artifact file.
  2. Cross-artifact consistency checks (finding counts, evidence presence).

Usage:
  # Validate all artifacts in evidence/
  python scripts/validate_audit_artifacts.py

  # Validate a single file against a specific schema
  python scripts/validate_audit_artifacts.py --file evidence/review-report.json \
      --schema scripts/schemas/review-report.schema.json

Exit codes:
  0 = all validations pass
  1 = validation failure or missing required artifact
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema package required. Install: uv add jsonschema", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "evidence"
SCHEMA_DIR = ROOT / "scripts" / "schemas"

# Mapping: artifact basename -> schema basename
ARTIFACT_MAP: dict[str, str] = {
    "review-report.json": "review-report.schema.json",
    "cross-audit-report.json": "cross-audit-report.schema.json",
    "fix-verification-report.json": "fix-verification-report.schema.json",
}


def validate_file(artifact_path: Path, schema_path: Path) -> list[str]:
    """Validate a JSON artifact against its schema. Returns list of errors."""
    errors: list[str] = []

    if not artifact_path.exists():
        errors.append(f"Artifact not found: {artifact_path}")
        return errors

    if not schema_path.exists():
        errors.append(f"Schema not found: {schema_path}")
        return errors

    try:
        data = json.loads(artifact_path.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in {artifact_path}: {e}")
        return errors

    try:
        schema = json.loads(schema_path.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in schema {schema_path}: {e}")
        return errors

    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(data):
        path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "(root)"
        errors.append(f"Schema violation at {path}: {error.message}")

    return errors


def cross_validate(evidence_dir: Path) -> list[str]:
    """Cross-validate artifact consistency. Returns list of errors."""
    errors: list[str] = []

    review_path = evidence_dir / "review-report.json"
    fix_path = evidence_dir / "fix-verification-report.json"

    if not review_path.exists() or not fix_path.exists():
        # Cannot cross-validate if artifacts are missing
        if not review_path.exists():
            errors.append(f"Cannot cross-validate: {review_path} missing")
        if not fix_path.exists():
            errors.append(f"Cannot cross-validate: {fix_path} missing")
        return errors

    try:
        review_data = json.loads(review_path.read_text())
        fix_data = json.loads(fix_path.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"Cannot cross-validate: JSON parse error: {e}")
        return errors

    # Check 1: finding count consistency
    review_ids = {f["id"] for f in review_data.get("findings", [])}
    fix_ids = {f["id"] for f in fix_data.get("findings", [])}

    missing_in_fix = review_ids - fix_ids
    if missing_in_fix:
        errors.append(
            f"Dropped findings: {sorted(missing_in_fix)} exist in review "
            f"but not in fix-verification (count mismatch: "
            f"review={len(review_ids)}, fix={len(fix_ids)})"
        )

    # Check 2: every CLOSED finding must have evidence
    for finding in fix_data.get("findings", []):
        if finding.get("verdict") == "CLOSED":
            evidence = finding.get("evidence", {})
            if not evidence.get("command") or not evidence.get("output_summary"):
                errors.append(f"Finding {finding['id']} is CLOSED but has empty evidence")

    # Check 3: summary counts must match actual findings
    fix_findings = fix_data.get("findings", [])
    summary = fix_data.get("summary", {})
    actual_total = len(fix_findings)
    declared_total = summary.get("total", -1)
    if actual_total != declared_total:
        errors.append(f"Summary total ({declared_total}) != actual findings count ({actual_total})")

    actual_closed = sum(1 for f in fix_findings if f.get("verdict") == "CLOSED")
    declared_closed = summary.get("closed", -1)
    if actual_closed != declared_closed:
        errors.append(
            f"Summary closed ({declared_closed}) != actual CLOSED count ({actual_closed})"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate audit evidence artifacts")
    parser.add_argument(
        "--file",
        type=Path,
        help="Validate a single artifact file",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        help="Schema to validate against (required with --file)",
    )
    args = parser.parse_args()

    all_errors: list[str] = []

    if args.file:
        # Single-file mode
        if not args.schema:
            print("ERROR: --schema required when using --file", file=sys.stderr)
            return 1
        errors = validate_file(args.file, args.schema)
        all_errors.extend(errors)
    else:
        # Full validation mode
        found_any = False
        for artifact_name, schema_name in ARTIFACT_MAP.items():
            artifact_path = EVIDENCE_DIR / artifact_name
            schema_path = SCHEMA_DIR / schema_name
            if artifact_path.exists():
                found_any = True
                errors = validate_file(artifact_path, schema_path)
                if errors:
                    all_errors.extend(errors)
                else:
                    print(f"PASS: {artifact_name}")
            else:
                print(f"SKIP: {artifact_name} (not yet generated)")

        if not found_any:
            print(
                "ERROR: No evidence artifacts found in evidence/. "
                "Run /systematic-review, /cross-reference-audit, "
                "and /adversarial-fix-verify first.",
                file=sys.stderr,
            )
            return 1

        # Cross-validation (only if both review + fix exist)
        cross_errors = cross_validate(EVIDENCE_DIR)
        all_errors.extend(cross_errors)

    if all_errors:
        print(f"\nFAILED: {len(all_errors)} error(s):", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("\nAll validations passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
