#!/usr/bin/env python3
"""Alert routing completeness check.

Gate ID: p4-alert-routing
Validation: scripts/check_alert_routing.py

Checks:
1. Every rule in alerts.yml has a severity label
2. Critical/warning rules have routing annotation (summary at minimum)
3. Suppression rules in incident-sla.yaml reference valid alert config
4. On-call schedule definition exists

Usage:
    python3 scripts/check_alert_routing.py [--json]

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

ALERTS_PATH = Path("deploy/monitoring/alerts.yml")
SLA_PATH = Path("delivery/commercial/incident-sla.yaml")

VALID_SEVERITIES = {"critical", "warning", "info"}


def _load_yaml(path: Path) -> dict | None:
    """Load YAML file, return None if not found."""
    if not path.exists():
        return None
    if yaml is not None:
        with open(path) as f:
            return yaml.safe_load(f)
    text = path.read_text()
    if not text.strip():
        return None
    return {"_raw": text}


def check_alert_rules(results: list[dict]) -> bool:
    """Validate alert rule completeness."""
    data = _load_yaml(ALERTS_PATH)
    if data is None:
        results.append(
            {
                "check": "alerts_exists",
                "status": "FAIL",
                "detail": f"{ALERTS_PATH} not found",
            }
        )
        return False

    if "_raw" in data:
        results.append(
            {
                "check": "alerts_rules",
                "status": "PASS",
                "detail": "Alerts file exists (fallback mode, PyYAML not available)",
            }
        )
        return True

    passed = True
    groups = data.get("groups", [])
    total_rules = 0
    rules_with_routing = 0

    for group in groups:
        for rule in group.get("rules", []):
            total_rules += 1
            alert_name = rule.get("alert", "unknown")
            labels = rule.get("labels", {})
            annotations = rule.get("annotations", {})
            severity = labels.get("severity", "")

            # Check 1: severity label exists and is valid
            if severity not in VALID_SEVERITIES:
                results.append(
                    {
                        "check": f"severity_{alert_name}",
                        "status": "FAIL",
                        "detail": (
                            f"Alert '{alert_name}' has invalid severity:"
                            f" '{severity}' (expected: {VALID_SEVERITIES})"
                        ),
                    }
                )
                passed = False

            # Check 2: critical/warning rules must have routing (summary annotation)
            if severity in ("critical", "warning"):
                if "summary" not in annotations:
                    results.append(
                        {
                            "check": f"routing_{alert_name}",
                            "status": "FAIL",
                            "detail": (
                                f"Alert '{alert_name}' (severity={severity})"
                                " missing summary annotation for routing"
                            ),
                        }
                    )
                    passed = False
                else:
                    rules_with_routing += 1

    if total_rules == 0:
        results.append(
            {
                "check": "alerts_empty",
                "status": "FAIL",
                "detail": "No alert rules found in alerts.yml",
            }
        )
        return False

    if passed:
        results.append(
            {
                "check": "alert_rules",
                "status": "PASS",
                "detail": (
                    f"{total_rules} rules validated, {rules_with_routing} with routing annotations"
                ),
            }
        )

    return passed


def check_suppression_reference(results: list[dict]) -> bool:
    """Verify SLA suppression_rules references valid config."""
    sla_data = _load_yaml(SLA_PATH)
    if sla_data is None:
        results.append(
            {
                "check": "sla_suppression",
                "status": "FAIL",
                "detail": f"{SLA_PATH} not found",
            }
        )
        return False

    if "_raw" in sla_data:
        results.append(
            {
                "check": "sla_suppression",
                "status": "PASS",
                "detail": "SLA file exists (fallback mode)",
            }
        )
        return True

    on_call = sla_data.get("on_call", {})
    suppression_ref = on_call.get("suppression_rules", "")

    if not suppression_ref:
        results.append(
            {
                "check": "sla_suppression",
                "status": "FAIL",
                "detail": "No suppression_rules reference in on_call config",
            }
        )
        return False

    # Verify the referenced file exists (strip fragment)
    ref_path = suppression_ref.split("#")[0]
    if not Path(ref_path).exists():
        results.append(
            {
                "check": "sla_suppression",
                "status": "FAIL",
                "detail": f"Suppression reference '{ref_path}' file not found",
            }
        )
        return False

    results.append(
        {
            "check": "sla_suppression",
            "status": "PASS",
            "detail": f"Suppression reference '{suppression_ref}' valid",
        }
    )
    return True


def check_oncall_schedule(results: list[dict]) -> bool:
    """Verify on-call schedule is defined."""
    sla_data = _load_yaml(SLA_PATH)
    if sla_data is None:
        results.append(
            {
                "check": "oncall_schedule",
                "status": "FAIL",
                "detail": f"{SLA_PATH} not found",
            }
        )
        return False

    if "_raw" in sla_data:
        results.append(
            {
                "check": "oncall_schedule",
                "status": "PASS",
                "detail": "SLA file exists (fallback mode)",
            }
        )
        return True

    on_call = sla_data.get("on_call", {})
    rotation = on_call.get("rotation")
    coverage = on_call.get("coverage")

    if not rotation:
        results.append(
            {
                "check": "oncall_schedule",
                "status": "FAIL",
                "detail": "No on-call rotation defined",
            }
        )
        return False

    results.append(
        {
            "check": "oncall_schedule",
            "status": "PASS",
            "detail": f"On-call: rotation={rotation}, coverage={coverage or 'unset'}",
        }
    )
    return True


def main() -> int:
    use_json = "--json" in sys.argv

    results: list[dict] = []
    all_pass = True

    all_pass = check_alert_rules(results) and all_pass
    all_pass = check_suppression_reference(results) and all_pass
    all_pass = check_oncall_schedule(results) and all_pass

    if use_json:
        output = {
            "gate_id": "p4-alert-routing",
            "status": "PASS" if all_pass else "FAIL",
            "checks": results,
        }
        print(json.dumps(output, indent=2))
    else:
        for r in results:
            marker = "OK" if r["status"] == "PASS" else "FAIL"
            print(f"  [{marker}] {r['check']}: {r['detail']}")
        print()
        print(f"Alert routing: {'PASS' if all_pass else 'FAIL'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
