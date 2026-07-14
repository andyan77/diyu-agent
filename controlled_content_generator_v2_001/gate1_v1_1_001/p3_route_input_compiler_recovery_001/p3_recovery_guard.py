#!/usr/bin/env python3
"""Fail-closed guard for the P3 route compiler recovery checkpoint."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from route_contract import ROOT, TASK_ID, TASK_ROOT, object_digest, sha256_file
from run_p3_route_recovery import (
    ACTUALS,
    COMPARISONS,
    FREEZE,
    HANDOFF,
    LEGACY_COMPARISONS,
    OLD_P4_ROOT,
    RESULT,
    selftest as contract_selftest,
)


if not __debug__:
    sys.stderr.write("p3_recovery_guard refuses python -O\n")
    raise SystemExit(2)


BASELINE_COMMIT = "08627f5a843f450efa3a5d4a32cf2191087badd8"
OLD_P4_TREE = "404a77ec7f59e0ce639daddbcd3c8d658d9bed5b"
CURRENT_CHECKER = Path("ci/checkers/check_gate1_v1_1_current.py")
FROZEN_SHA256 = {
    Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/p2_generator_core.py"
    ): "e7765148ee0a8ffb374488d53aa4fada164ce175e89ebac7973b7332f68e3b3d",
    Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/p2_generator_core_r6.py"
    ): "e15eab89cef2cb9b2a35d76ca3550b67f2c49c583fc9efe107ebaf062f527015",
    Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001/"
        "freeze/attempt_1/controlled_author_instruction.v0.2.md"
    ): "5962400130fd59ed8b94611cb4c2d46a9f10b3672041369325e3acf417b5a98e",
    Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001/"
        "freeze/attempt_1/author_model_and_session.v0.2.yaml"
    ): "516bc60467bfe30991ea9228ff34b3c753d96410f74424ca5dbffc74d91283d3",
}


def _error(errors: list[dict[str, str]], code: str, detail: str = "") -> None:
    errors.append({"code": code, "detail": detail})


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(path)
            rows.append(value)
    return rows


def validate_p3_recovery(root: Path = ROOT) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = (
        TASK_ROOT / "route_contract.py",
        TASK_ROOT / "run_p3_route_recovery.py",
        TASK_ROOT / "p3_recovery_guard.py",
        FREEZE,
        RESULT,
        HANDOFF,
        ACTUALS,
        COMPARISONS,
        LEGACY_COMPARISONS,
    )
    for path in required:
        if not (root / path).is_file():
            _error(errors, "E_P3R_REQUIRED", path.as_posix())
    if errors:
        return errors
    for path, expected in FROZEN_SHA256.items():
        if not (root / path).is_file() or sha256_file(root / path) != expected:
            _error(errors, "E_P3R_FROZEN_SHA", path.as_posix())
    old_p4_diff = subprocess.run(
        ["git", "diff", "--quiet", BASELINE_COMMIT, "--", OLD_P4_ROOT.as_posix()],
        cwd=root,
        check=False,
    )
    if old_p4_diff.returncode != 0:
        _error(errors, "E_P3R_OLD_P4_MUTATION")
    baseline_tree = subprocess.run(
        ["git", "rev-parse", f"{BASELINE_COMMIT}:{OLD_P4_ROOT.as_posix()}"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if baseline_tree.returncode != 0 or baseline_tree.stdout.strip() != OLD_P4_TREE:
        _error(errors, "E_P3R_OLD_P4_TREE", baseline_tree.stdout.strip())
    try:
        current = _jsonl(root / COMPARISONS)
        legacy = _jsonl(root / LEGACY_COMPARISONS)
        if len(current) != 20 or len(legacy) != 20:
            _error(errors, "E_P3R_ROUTE_COUNTS")
        if sum(row.get("primary_action_matches_gold") is True for row in current) != 20:
            _error(errors, "E_P3R_CURRENT_ACTION")
        if sum(row.get("primary_reason_matches_gold") is True for row in current) != 20:
            _error(errors, "E_P3R_CURRENT_REASON")
        if sum(row.get("primary_action_matches_gold") is True for row in legacy) != 20:
            _error(errors, "E_P3R_LEGACY_ACTION")
        if sum(row.get("primary_reason_matches_gold") is True for row in legacy) != 20:
            _error(errors, "E_P3R_LEGACY_REASON")
        if any(row.get("audience_content_created") is not False for row in current + legacy):
            _error(errors, "E_P3R_AUDIENCE_CONTENT")
        freeze = yaml.safe_load((root / FREEZE).read_text(encoding="utf-8"))
        result = yaml.safe_load((root / RESULT).read_text(encoding="utf-8"))
        handoff = yaml.safe_load((root / HANDOFF).read_text(encoding="utf-8"))
        if not isinstance(freeze, dict) or freeze.get("freeze_digest") != object_digest(freeze, "freeze_digest"):
            _error(errors, "E_P3R_FREEZE_DIGEST")
        if freeze.get("current_checker_sha256") != sha256_file(root / CURRENT_CHECKER):
            _error(errors, "E_P3R_CURRENT_CHECKER_BINDING")
        if not isinstance(result, dict) or result.get("result_digest") != object_digest(result, "result_digest"):
            _error(errors, "E_P3R_RESULT_DIGEST")
        if not isinstance(handoff, dict) or handoff.get("handoff_digest") != object_digest(handoff, "handoff_digest"):
            _error(errors, "E_P3R_HANDOFF_DIGEST")
        if result.get("result_state") != "PASS_TO_P4_RESEALED_PROBE":
            _error(errors, "E_P3R_RESULT_STATE")
        if result.get("generator_qualified") is not False or result.get("p5_allowed") is not False:
            _error(errors, "E_P3R_EARLY_QUALIFICATION")
        if result.get("readiness_true_keys") != []:
            _error(errors, "E_P3R_READINESS")
        if freeze.get("old_p4_tree") != OLD_P4_TREE or freeze.get("old_p4_failure_bytes_changed") is not False:
            _error(errors, "E_P3R_OLD_P4_CLAIM")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        _error(errors, "E_P3R_PARSE", str(exc))
    return errors


def selftest(root: Path = ROOT) -> int:
    try:
        contract_selftest(root)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "SELFTEST_FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "SELFTEST_PASS", "real_contract_tamper_suite": True}))
    return 0


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        return selftest(ROOT)
    errors = validate_p3_recovery(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "task_id": TASK_ID}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
