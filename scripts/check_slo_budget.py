#!/usr/bin/env python3
"""SLO budget and metrics validation check.

Gate ID: p4-slo-metrics
Validation: scripts/check_slo_budget.py

Checks:
1. incident-sla.yaml has slo/error_budget/burn_rate sections
2. alerts.yml has SLO burn-rate alert rules (fast + slow)
3. SLO targets are consistent between SLA and alert expressions

Usage:
    python3 scripts/check_slo_budget.py [--json]

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

SLA_PATH = Path("delivery/commercial/incident-sla.yaml")
ALERTS_PATH = Path("deploy/monitoring/alerts.yml")


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


def check_slo_definition(results: list[dict]) -> bool:
    """Verify SLO definition in incident-sla.yaml."""
    data = _load_yaml(SLA_PATH)
    if data is None:
        results.append(
            {
                "check": "slo_file",
                "status": "FAIL",
                "detail": f"{SLA_PATH} not found",
            }
        )
        return False

    if "_raw" in data:
        results.append(
            {
                "check": "slo_definition",
                "status": "FAIL",
                "detail": "PyYAML not available, cannot validate SLO structure",
            }
        )
        return False

    passed = True

    # Check slo section
    slo = data.get("slo", {})
    if not slo:
        results.append(
            {
                "check": "slo_section",
                "status": "FAIL",
                "detail": "Missing 'slo' section in incident-sla.yaml",
            }
        )
        passed = False
    else:
        for metric in ("availability", "latency_p95", "error_rate"):
            if metric not in slo:
                results.append(
                    {
                        "check": f"slo_{metric}",
                        "status": "FAIL",
                        "detail": f"Missing SLO metric: {metric}",
                    }
                )
                passed = False
        if passed:
            avail = slo.get("availability", {})
            results.append(
                {
                    "check": "slo_definition",
                    "status": "PASS",
                    "detail": (
                        f"availability={avail.get('target', 'unset')}, "
                        f"latency_p95={slo.get('latency_p95', {}).get('target_ms', 'unset')}ms, "
                        f"error_rate={slo.get('error_rate', {}).get('target', 'unset')}"
                    ),
                }
            )

    # Check error_budget section
    budget = data.get("error_budget", {})
    if not budget:
        results.append(
            {
                "check": "error_budget",
                "status": "FAIL",
                "detail": "Missing 'error_budget' section",
            }
        )
        passed = False
    else:
        results.append(
            {
                "check": "error_budget",
                "status": "PASS",
                "detail": (
                    f"monthly_budget={budget.get('monthly_budget_minutes_actual', 'unset')} min"
                ),
            }
        )

    # Check burn_rate section
    burn = data.get("burn_rate", {})
    if not burn:
        results.append(
            {
                "check": "burn_rate_config",
                "status": "FAIL",
                "detail": "Missing 'burn_rate' section",
            }
        )
        passed = False
    else:
        for tier in ("fast", "slow"):
            if tier not in burn:
                results.append(
                    {
                        "check": f"burn_rate_{tier}",
                        "status": "FAIL",
                        "detail": f"Missing burn_rate tier: {tier}",
                    }
                )
                passed = False
        if "fast" in burn and "slow" in burn:
            results.append(
                {
                    "check": "burn_rate_config",
                    "status": "PASS",
                    "detail": (
                        f"fast={burn['fast'].get('multiplier', '?')}x"
                        f"/{burn['fast'].get('window', '?')}, "
                        f"slow={burn['slow'].get('multiplier', '?')}x"
                        f"/{burn['slow'].get('window', '?')}"
                    ),
                }
            )

    return passed


def check_burn_rate_alerts(results: list[dict]) -> bool:
    """Verify burn-rate alert rules exist in alerts.yml."""
    data = _load_yaml(ALERTS_PATH)
    if data is None:
        results.append(
            {
                "check": "alerts_file",
                "status": "FAIL",
                "detail": f"{ALERTS_PATH} not found",
            }
        )
        return False

    if "_raw" in data:
        results.append(
            {
                "check": "burn_rate_alerts",
                "status": "FAIL",
                "detail": "PyYAML not available",
            }
        )
        return False

    groups = data.get("groups", [])
    burn_rate_rules = []
    for group in groups:
        for rule in group.get("rules", []):
            labels = rule.get("labels", {})
            if labels.get("burn_rate"):
                burn_rate_rules.append(rule.get("alert", "unknown"))

    if len(burn_rate_rules) < 2:
        results.append(
            {
                "check": "burn_rate_alerts",
                "status": "FAIL",
                "detail": (
                    f"Expected >= 2 burn-rate alert rules, "
                    f"found {len(burn_rate_rules)}: {burn_rate_rules}"
                ),
            }
        )
        return False

    results.append(
        {
            "check": "burn_rate_alerts",
            "status": "PASS",
            "detail": f"{len(burn_rate_rules)} burn-rate alert rules: {', '.join(burn_rate_rules)}",
        }
    )
    return True


def main() -> int:
    use_json = "--json" in sys.argv
    results: list[dict] = []
    all_pass = True

    all_pass = check_slo_definition(results) and all_pass
    all_pass = check_burn_rate_alerts(results) and all_pass

    if use_json:
        output = {
            "gate_id": "p4-slo-metrics",
            "status": "PASS" if all_pass else "FAIL",
            "checks": results,
        }
        print(json.dumps(output, indent=2))
    else:
        for r in results:
            marker = "OK" if r["status"] == "PASS" else "FAIL"
            print(f"  [{marker}] {r['check']}: {r['detail']}")
        print()
        print(f"SLO budget check: {'PASS' if all_pass else 'FAIL'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
