#!/usr/bin/env python3
"""Postmortem template and CAPA register validation check.

Gate ID: p4-postmortem-capa
Validation: scripts/check_postmortem_capa.py

Checks:
1. Postmortem template exists and has required sections
2. CAPA register exists and is valid YAML with required schema
3. Post-incident config in incident-sla.yaml references both files

Usage:
    python3 scripts/check_postmortem_capa.py [--json]

Exit codes:
    0: All checks pass
    1: One or more checks failed
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

POSTMORTEM_TEMPLATE = Path("delivery/commercial/postmortem-template.md")
CAPA_REGISTER = Path("delivery/commercial/capa-register.yaml")
SLA_PATH = Path("delivery/commercial/incident-sla.yaml")

REQUIRED_TEMPLATE_SECTIONS = [
    "## Incident Summary",
    "## Timeline",
    "## Root Cause",
    "## Impact",
    "## Action Items",
    "## Lessons Learned",
]


def check_postmortem_template(results: list[dict]) -> bool:
    """Verify postmortem template exists and has required sections."""
    if not POSTMORTEM_TEMPLATE.exists():
        results.append(
            {
                "check": "postmortem_template",
                "status": "FAIL",
                "detail": f"{POSTMORTEM_TEMPLATE} not found",
            }
        )
        return False

    content = POSTMORTEM_TEMPLATE.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED_TEMPLATE_SECTIONS if s not in content]

    if missing:
        results.append(
            {
                "check": "postmortem_template_sections",
                "status": "FAIL",
                "detail": f"Missing sections: {', '.join(missing)}",
            }
        )
        return False

    results.append(
        {
            "check": "postmortem_template",
            "status": "PASS",
            "detail": f"Template has all {len(REQUIRED_TEMPLATE_SECTIONS)} required sections",
        }
    )
    return True


def check_capa_register(results: list[dict]) -> bool:
    """Verify CAPA register exists and has valid schema."""
    if not CAPA_REGISTER.exists():
        results.append(
            {
                "check": "capa_register",
                "status": "FAIL",
                "detail": f"{CAPA_REGISTER} not found",
            }
        )
        return False

    if yaml is None:
        # Fallback: just check file is non-empty
        content = CAPA_REGISTER.read_text()
        if content.strip():
            results.append(
                {
                    "check": "capa_register",
                    "status": "PASS",
                    "detail": "File exists (PyYAML unavailable, schema not validated)",
                }
            )
            return True
        results.append(
            {
                "check": "capa_register",
                "status": "FAIL",
                "detail": "File is empty",
            }
        )
        return False

    try:
        with open(CAPA_REGISTER) as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        results.append(
            {
                "check": "capa_register_parse",
                "status": "FAIL",
                "detail": f"Failed to parse: {exc}",
            }
        )
        return False

    if not isinstance(data, dict):
        results.append(
            {
                "check": "capa_register_schema",
                "status": "FAIL",
                "detail": "Expected top-level dict",
            }
        )
        return False

    # Verify required top-level keys
    required_keys = {"version", "entries"}
    missing = required_keys - set(data.keys())
    if missing:
        results.append(
            {
                "check": "capa_register_schema",
                "status": "FAIL",
                "detail": f"Missing top-level keys: {sorted(missing)}",
            }
        )
        return False

    entries = data.get("entries", [])
    results.append(
        {
            "check": "capa_register",
            "status": "PASS",
            "detail": f"CAPA register valid, {len(entries)} entries",
        }
    )
    return True


def check_sla_references(results: list[dict]) -> bool:
    """Verify incident-sla.yaml references postmortem + CAPA files."""
    if yaml is None or not SLA_PATH.exists():
        results.append(
            {
                "check": "sla_references",
                "status": "FAIL",
                "detail": f"{SLA_PATH} not found or PyYAML unavailable",
            }
        )
        return False

    try:
        with open(SLA_PATH) as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        results.append(
            {
                "check": "sla_references",
                "status": "FAIL",
                "detail": f"Failed to parse SLA: {exc}",
            }
        )
        return False

    post = data.get("post_incident", {})
    has_template = "postmortem_template" in post
    has_capa = "capa_register" in post

    if not (has_template and has_capa):
        missing = []
        if not has_template:
            missing.append("postmortem_template")
        if not has_capa:
            missing.append("capa_register")
        results.append(
            {
                "check": "sla_references",
                "status": "FAIL",
                "detail": f"post_incident missing references: {', '.join(missing)}",
            }
        )
        return False

    results.append(
        {
            "check": "sla_references",
            "status": "PASS",
            "detail": (
                f"SLA references: template={post['postmortem_template']}, "
                f"capa={post['capa_register']}"
            ),
        }
    )
    return True


def main() -> int:
    use_json = "--json" in sys.argv
    results: list[dict] = []
    all_pass = True

    all_pass = check_postmortem_template(results) and all_pass
    all_pass = check_capa_register(results) and all_pass
    all_pass = check_sla_references(results) and all_pass

    if use_json:
        output = {
            "gate_id": "p4-postmortem-capa",
            "status": "PASS" if all_pass else "FAIL",
            "checks": results,
        }
        print(json.dumps(output, indent=2))
    else:
        for r in results:
            marker = "OK" if r["status"] == "PASS" else "FAIL"
            print(f"  [{marker}] {r['check']}: {r['detail']}")
        print()
        print(f"Postmortem + CAPA check: {'PASS' if all_pass else 'FAIL'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
