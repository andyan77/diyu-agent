#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CHECKERS = (
    "check_no_readiness_leak.py",
    "check_source_anchor_coverage.py",
    "check_declared_semantics_alignment.py",
    "check_hard_claim_and_brand_fact_leak.py",
    "check_rich_body_structure_consistency.py",
    "check_semantic_fingerprint_dedupe.py",
    "check_capability_routing_composability.py",
    "check_serving_spec_no_passage_text.py",
    "check_gold_hooks_as_release_input.py",
)


@dataclass(frozen=True)
class CheckerRun:
    checker: str
    command: list[str]
    returncode: int
    report_path: str
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "checker": self.checker,
            "command": self.command,
            "returncode": self.returncode,
            "passed": self.passed,
            "report_path": self.report_path,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the complete local GKB intake gate suite.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--report-dir", type=Path, default=Path("knowledge_intake/gpt55_gkb_enrichment_v1/11_reports/gates"))
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--summary-json", type=Path)
    return parser.parse_args()


def run_checker(checker_dir: Path, checker: str, workspace: Path, report_dir: Path, selftest: bool) -> CheckerRun:
    report_path = report_dir / f"{Path(checker).stem}.json"
    command = [
        sys.executable,
        str(checker_dir / checker),
        "--root",
        str(workspace),
        "--report-json",
        str(report_path),
    ]
    if selftest:
        command.append("--selftest")
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return CheckerRun(
        checker=checker,
        command=command,
        returncode=completed.returncode,
        report_path=str(report_path),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    checker_dir = root / "ci" / "checkers"
    if not args.workspace.exists():
        print(json.dumps({"passed": False, "error": f"workspace missing: {args.workspace}"}, indent=2))
        return 1
    args.report_dir.mkdir(parents=True, exist_ok=True)
    runs = [run_checker(checker_dir, checker, args.workspace, args.report_dir, args.selftest) for checker in CHECKERS]
    summary = {
        "gate_suite": "gkb_intake_local_gates",
        "workspace": str(args.workspace),
        "selftest": args.selftest,
        "passed": all(run.passed for run in runs),
        "runs": [run.as_dict() for run in runs],
    }
    text = json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False)
    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
