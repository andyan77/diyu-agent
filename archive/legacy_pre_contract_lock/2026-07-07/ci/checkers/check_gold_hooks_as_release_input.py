#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from gkb_intake_common import Finding, build_result, emit_result, is_true, iter_data_files, load_structured

GATE_ID = "check_gold_hooks_as_release_input"
SCANNED_DIRS = ("10_gold_hooks",)
REQUIRED_CONSUMERS = {"Step_20_Gold_Hooks_Rebaseline", "Step_21_Release_Gate"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure gold hook candidates are release inputs, not an independent system.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def iter_gold_hooks(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        hooks: list[dict[str, Any]] = []
        if "gold_hook_id" in value or "independent_gold_system" in value:
            hooks.append(value)
        for child in value.values():
            hooks.extend(iter_gold_hooks(child))
        return hooks
    if isinstance(value, list):
        hooks = []
        for child in value:
            hooks.extend(iter_gold_hooks(child))
        return hooks
    return []


def check_hook(path: Path, hook: dict[str, Any]) -> list[Finding]:
    hook_id = str(hook.get("gold_hook_id", "<missing>"))
    findings: list[Finding] = []
    if not is_true(hook.get("is_release_input_candidate")):
        findings.append(Finding("KIG_GOLD_HOOK_NOT_RELEASE_INPUT", str(path), "gold hook must be a release input candidate", hook_id))
    if is_true(hook.get("independent_gold_system")):
        findings.append(Finding("KIG_GOLD_SYSTEM_FORK", str(path), "independent_gold_system must be false", hook_id))
    consumers = set(hook.get("consumed_by") or [])
    missing = REQUIRED_CONSUMERS - consumers
    if missing:
        findings.append(Finding("KIG_GOLD_STEP_BINDING_MISSING", str(path), f"missing consumers: {sorted(missing)}", hook_id))
    readiness = hook.get("readiness") if isinstance(hook.get("readiness"), dict) else {}
    if is_true(readiness.get("release_ready")) or is_true(readiness.get("production_ready")) or is_true(readiness.get("generation_allowed")):
        findings.append(Finding("KIG_GOLD_HOOK_CLAIMS_RUNTIME_READINESS", str(path), "gold hook cannot claim readiness", hook_id))
    return findings


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        hooks = iter_gold_hooks(load_structured(path))
        for hook in hooks:
            findings.extend(check_hook(path, hook))
    return findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_gold_hook_candidate.yaml")
    negative = Path("fixtures/gkb_intake/negative/independent_gold_system.yaml")
    return not check_paths([positive]) and bool(check_paths([negative]))


def main() -> int:
    args = parse_args()
    files = iter_data_files(args.root, SCANNED_DIRS)
    findings = check_paths(files)
    result = build_result(GATE_ID, len(files), findings)
    if args.selftest and not run_selftest():
        result = build_result(
            GATE_ID,
            len(files),
            findings
            + [
                Finding(
                    code="KIG_SELFTEST_FAILED",
                    path="fixtures/gkb_intake",
                    message="gold hook positive fixture must pass and independent gold fixture must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
