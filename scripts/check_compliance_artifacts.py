#!/usr/bin/env python3
"""Compliance artifact existence and completeness check.

Gate ID: p4-compliance-artifacts
Validation: scripts/check_compliance_artifacts.py

Checks that required compliance documents exist and are non-empty.

Required artifacts:
  - delivery/commercial/runbook/data-breach-response.md
  - delivery/commercial/runbook/supply-chain-response.md
  - delivery/commercial/runbook/key-leak-response.md
  - delivery/commercial/runbook/release-rollback.md
  - delivery/commercial/runbook/dr-restore.md
  - delivery/commercial/incident-sla.yaml
  - delivery/commercial/sla-template.md
  - delivery/sbom.json (SBOM)

Future (Phase 5, not yet required):
  - delivery/commercial/dpa-template.md (Data Processing Agreement)
  - delivery/commercial/privacy-policy.md
  - delivery/commercial/data-retention-policy.md
  - delivery/commercial/data-deletion-proof-template.md

Usage:
    python3 scripts/check_compliance_artifacts.py [--json] [--strict]

Exit codes:
    0: All required checks pass (future items are warnings only unless --strict)
    1: One or more required checks failed
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Required now (Phase 4)
REQUIRED_ARTIFACTS = [
    "delivery/commercial/runbook/data-breach-response.md",
    "delivery/commercial/runbook/supply-chain-response.md",
    "delivery/commercial/runbook/key-leak-response.md",
    "delivery/commercial/runbook/release-rollback.md",
    "delivery/commercial/runbook/dr-restore.md",
    "delivery/commercial/incident-sla.yaml",
    "delivery/commercial/sla-template.md",
]

# SBOM is generated, may not be committed
SBOM_PATHS = [
    "delivery/sbom.json",
    "delivery/sbom.spdx.json",
]

# Phase 5 future artifacts (warn only unless --strict)
FUTURE_ARTIFACTS = [
    "delivery/commercial/dpa-template.md",
    "delivery/commercial/privacy-policy.md",
    "delivery/commercial/data-retention-policy.md",
    "delivery/commercial/data-deletion-proof-template.md",
]

MIN_FILE_SIZE = 50  # bytes - files smaller than this are considered empty stubs


def check_artifact(path_str: str, results: list[dict], required: bool = True) -> bool:
    """Check if an artifact exists and is non-empty."""
    path = Path(path_str)
    if not path.exists():
        results.append(
            {
                "check": f"artifact_{path.name}",
                "status": "FAIL" if required else "WARN",
                "detail": f"{'Missing' if required else 'Future'}: {path_str}",
                "required": required,
            }
        )
        return False

    size = path.stat().st_size
    if size < MIN_FILE_SIZE:
        results.append(
            {
                "check": f"artifact_{path.name}",
                "status": "FAIL" if required else "WARN",
                "detail": f"File too small ({size} bytes): {path_str}",
                "required": required,
            }
        )
        return False

    results.append(
        {
            "check": f"artifact_{path.name}",
            "status": "PASS",
            "detail": f"Present ({size} bytes): {path_str}",
            "required": required,
        }
    )
    return True


def check_sbom(results: list[dict]) -> bool:
    """Check SBOM exists (any of the known paths)."""
    for sbom_path in SBOM_PATHS:
        if Path(sbom_path).exists():
            size = Path(sbom_path).stat().st_size
            results.append(
                {
                    "check": "sbom",
                    "status": "PASS",
                    "detail": f"SBOM present ({size} bytes): {sbom_path}",
                    "required": True,
                }
            )
            return True

    # SBOM is generated at build time, not always committed
    results.append(
        {
            "check": "sbom",
            "status": "WARN",
            "detail": (
                f"SBOM not found at {SBOM_PATHS} (generated at build time via generate_sbom.sh)"
            ),
            "required": False,
        }
    )
    return True  # Not a hard failure since it's build-time generated


def main() -> int:
    use_json = "--json" in sys.argv
    strict = "--strict" in sys.argv

    results: list[dict] = []
    all_pass = True

    # Check required artifacts
    for artifact in REQUIRED_ARTIFACTS:
        if not check_artifact(artifact, results, required=True):
            all_pass = False

    # Check SBOM
    check_sbom(results)

    # Check future artifacts (warn only unless --strict)
    future_pass = True
    for artifact in FUTURE_ARTIFACTS:
        if not check_artifact(artifact, results, required=strict):
            future_pass = False
    if strict and not future_pass:
        all_pass = False

    # Summary
    required_count = len(REQUIRED_ARTIFACTS)
    required_pass = sum(1 for r in results if r.get("required") and r["status"] == "PASS")
    future_count = len(FUTURE_ARTIFACTS)
    future_present = sum(
        1
        for r in results
        if not r.get("required") and r["status"] == "PASS" and r["check"].startswith("artifact_")
    )

    if use_json:
        output = {
            "gate_id": "p4-compliance-artifacts",
            "status": "PASS" if all_pass else "FAIL",
            "summary": {
                "required": f"{required_pass}/{required_count}",
                "future": f"{future_present}/{future_count}",
                "strict_mode": strict,
            },
            "checks": results,
        }
        print(json.dumps(output, indent=2))
    else:
        for r in results:
            if r["status"] == "PASS":
                marker = "OK"
            elif r["status"] == "WARN":
                marker = "WARN"
            else:
                marker = "FAIL"
            print(f"  [{marker}] {r['check']}: {r['detail']}")
        print()
        print(f"Required: {required_pass}/{required_count}")
        print(f"Future (Phase 5): {future_present}/{future_count}")
        print(f"Compliance artifacts: {'PASS' if all_pass else 'FAIL'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
