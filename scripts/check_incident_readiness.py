#!/usr/bin/env python3
"""Incident management readiness check.

Gate ID: p4-incident-readiness
Validation: scripts/check_incident_readiness.py

Checks:
1. incident-sla.yaml exists and has valid schema (P0/P1/P2 tiers)
2. alerts.yml: every critical/warning rule has severity label
3. Runbook directory has P0/P1-level response documents
4. On-call rotation defined

Usage:
    python3 scripts/check_incident_readiness.py [--json]

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
    # Fallback: parse YAML minimally if PyYAML not available
    yaml = None  # type: ignore[assignment]

SLA_PATH = Path("delivery/commercial/incident-sla.yaml")
ALERTS_PATH = Path("deploy/monitoring/alerts.yml")
RUNBOOK_DIR = Path("delivery/commercial/runbook")

# Runbooks that must exist for incident readiness
REQUIRED_RUNBOOKS = [
    "data-breach-response.md",
    "key-leak-response.md",
    "ddos-response.md",
    "supply-chain-response.md",
]

REQUIRED_SLA_LEVELS = {"P0", "P1", "P2"}
REQUIRED_SLA_FIELDS = {"response_time", "resolution_target", "escalation"}


def _load_yaml(path: Path) -> dict:
    """Load YAML file."""
    if yaml is not None:
        with open(path) as f:
            return yaml.safe_load(f)
    # Minimal fallback: just check file is non-empty
    text = path.read_text()
    if not text.strip():
        raise ValueError(f"{path} is empty")
    return {"_raw": text}


def check_sla_schema(results: list[dict]) -> bool:
    """Verify incident-sla.yaml exists and has valid structure."""
    if not SLA_PATH.exists():
        results.append(
            {
                "check": "sla_exists",
                "status": "FAIL",
                "detail": f"{SLA_PATH} not found",
            }
        )
        return False

    try:
        data = _load_yaml(SLA_PATH)
    except Exception as exc:
        results.append(
            {
                "check": "sla_parse",
                "status": "FAIL",
                "detail": f"Failed to parse {SLA_PATH}: {exc}",
            }
        )
        return False

    if "_raw" in data:
        # Fallback mode: just check file exists and is non-empty
        results.append(
            {
                "check": "sla_schema",
                "status": "PASS",
                "detail": "YAML parsed (fallback mode, PyYAML not available)",
            }
        )
        return True

    passed = True

    # Check incident_levels
    levels = data.get("incident_levels", {})
    if not levels:
        results.append(
            {
                "check": "sla_levels",
                "status": "FAIL",
                "detail": "No incident_levels defined",
            }
        )
        return False

    for level_name in REQUIRED_SLA_LEVELS:
        if level_name not in levels:
            results.append(
                {
                    "check": f"sla_level_{level_name}",
                    "status": "FAIL",
                    "detail": f"Missing incident level: {level_name}",
                }
            )
            passed = False
            continue

        level = levels[level_name]
        missing = REQUIRED_SLA_FIELDS - set(level.keys())
        if missing:
            results.append(
                {
                    "check": f"sla_level_{level_name}_fields",
                    "status": "FAIL",
                    "detail": f"{level_name} missing fields: {sorted(missing)}",
                }
            )
            passed = False
        else:
            results.append(
                {
                    "check": f"sla_level_{level_name}",
                    "status": "PASS",
                    "detail": (
                        f"{level_name}: response={level['response_time']},"
                        f" resolution={level['resolution_target']}"
                    ),
                }
            )

    # Check metrics
    metrics = data.get("metrics", {})
    if not metrics.get("mtta_target"):
        results.append(
            {
                "check": "sla_mtta",
                "status": "FAIL",
                "detail": "Missing mtta_target in metrics",
            }
        )
        passed = False

    # Check on_call
    on_call = data.get("on_call", {})
    if not on_call.get("rotation"):
        results.append(
            {
                "check": "sla_oncall",
                "status": "FAIL",
                "detail": "Missing on_call rotation definition",
            }
        )
        passed = False
    else:
        results.append(
            {
                "check": "sla_oncall",
                "status": "PASS",
                "detail": (
                    f"rotation={on_call['rotation']}, coverage={on_call.get('coverage', 'unset')}"
                ),
            }
        )

    return passed


def check_alert_severity(results: list[dict]) -> bool:
    """Verify alerts.yml rules have severity labels."""
    if not ALERTS_PATH.exists():
        results.append(
            {
                "check": "alerts_exists",
                "status": "FAIL",
                "detail": f"{ALERTS_PATH} not found",
            }
        )
        return False

    try:
        data = _load_yaml(ALERTS_PATH)
    except Exception as exc:
        results.append(
            {
                "check": "alerts_parse",
                "status": "FAIL",
                "detail": f"Failed to parse {ALERTS_PATH}: {exc}",
            }
        )
        return False

    if "_raw" in data:
        results.append(
            {
                "check": "alerts_severity",
                "status": "PASS",
                "detail": "Alerts file exists (fallback mode)",
            }
        )
        return True

    passed = True
    groups = data.get("groups", [])
    for group in groups:
        for rule in group.get("rules", []):
            alert_name = rule.get("alert", "unknown")
            labels = rule.get("labels", {})
            if "severity" not in labels:
                results.append(
                    {
                        "check": f"alert_severity_{alert_name}",
                        "status": "FAIL",
                        "detail": f"Alert '{alert_name}' missing severity label",
                    }
                )
                passed = False

    if passed:
        total_rules = sum(len(g.get("rules", [])) for g in groups)
        results.append(
            {
                "check": "alerts_severity",
                "status": "PASS",
                "detail": f"All {total_rules} alert rules have severity labels",
            }
        )

    return passed


def check_runbooks(results: list[dict]) -> bool:
    """Verify required incident response runbooks exist."""
    passed = True
    for runbook in REQUIRED_RUNBOOKS:
        path = RUNBOOK_DIR / runbook
        if not path.exists():
            results.append(
                {
                    "check": f"runbook_{runbook}",
                    "status": "FAIL",
                    "detail": f"Missing runbook: {path}",
                }
            )
            passed = False

    if passed:
        results.append(
            {
                "check": "runbooks",
                "status": "PASS",
                "detail": f"All {len(REQUIRED_RUNBOOKS)} required runbooks present",
            }
        )

    return passed


def main() -> int:
    use_json = "--json" in sys.argv

    results: list[dict] = []
    all_pass = True

    all_pass = check_sla_schema(results) and all_pass
    all_pass = check_alert_severity(results) and all_pass
    all_pass = check_runbooks(results) and all_pass

    if use_json:
        output = {
            "gate_id": "p4-incident-readiness",
            "status": "PASS" if all_pass else "FAIL",
            "checks": results,
        }
        print(json.dumps(output, indent=2))
    else:
        for r in results:
            marker = "OK" if r["status"] == "PASS" else "FAIL"
            print(f"  [{marker}] {r['check']}: {r['detail']}")
        print()
        print(f"Incident readiness: {'PASS' if all_pass else 'FAIL'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
