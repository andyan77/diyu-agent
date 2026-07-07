#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

VALID_STATUSES = {"not_started", "draft_generated", "alignment_passed", "review_pending", "failed"}


@dataclass(frozen=True)
class RunnerResult:
    passed: bool
    mode: str
    batch_id: str
    micro_batch_id: str | None
    gate_summary_path: str
    validation_report_path: str
    generation_executed: bool
    errors: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic local gate runner for GKB intake batches.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--lockfile", required=True, type=Path)
    parser.add_argument("--gate-only", action="store_true")
    parser.add_argument("--report-dir", type=Path, default=Path("knowledge_intake/gpt55_gkb_enrichment_v1/11_reports"))
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def validate_lockfile(lockfile: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if not lockfile.exists():
        return None, [f"batch lockfile missing: {lockfile}"]
    lock = load_yaml(lockfile)
    for field in ("batch_id", "run_status", "allowed_output_files", "expected_checker_set"):
        if field not in lock:
            errors.append(f"lockfile missing required field: {field}")
    if lock.get("run_status") not in VALID_STATUSES:
        errors.append(f"unsupported run_status: {lock.get('run_status')}")
    return lock, errors


def run_command(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    if not args.workspace.exists():
        errors.append(f"workspace missing: {args.workspace}")
    lock, lock_errors = validate_lockfile(args.lockfile)
    errors.extend(lock_errors)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    gate_summary_path = args.report_dir / "gkb_intake_gate_summary.json"
    validation_report_path = args.report_dir / "gkb_intake_validation_report.json"
    if not errors:
        validation_command = [
            sys.executable,
            str(Path(__file__).resolve().parent / "validate_batch.py"),
            "--workspace",
            str(args.workspace),
            "--scaffold-only",
            "--report-json",
            str(validation_report_path),
        ]
        validation_code, _stdout, stderr = run_command(validation_command)
        if validation_code != 0:
            errors.append(f"validation failed; see {validation_report_path}")
        if stderr:
            errors.append(stderr.strip())
        gate_command = [
            sys.executable,
            str(Path(__file__).resolve().parent / "run_gates.py"),
            "--workspace",
            str(args.workspace),
            "--selftest",
            "--summary-json",
            str(gate_summary_path),
        ]
        gate_code, _stdout, stderr = run_command(gate_command)
        if gate_code != 0:
            errors.append(f"gate suite failed; see {gate_summary_path}")
        if stderr:
            errors.append(stderr.strip())
    if not args.gate_only:
        errors.append("generation is outside this local gate runner; rerun with --gate-only")
    result = RunnerResult(
        passed=not errors,
        mode="gate_only",
        batch_id=str(lock.get("batch_id")) if lock else "",
        micro_batch_id=str(lock.get("micro_batch_id")) if lock and lock.get("micro_batch_id") else None,
        gate_summary_path=str(gate_summary_path),
        validation_report_path=str(validation_report_path),
        generation_executed=False,
        errors=errors,
    )
    text = json.dumps(result.__dict__, indent=2, sort_keys=True, ensure_ascii=False)
    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
