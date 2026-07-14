#!/usr/bin/env python3
"""Fail-closed guard for the resealed Gate 1 P4 qualification batch."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from p3_recovery_guard_current import validate_p3_recovery_current
from p4_resealed import (
    AUTHOR_RECEIPT,
    AUTHOR_REQUESTS,
    BLIND_CATALOG,
    BLIND_MAPPING,
    BLIND_PACKET,
    CHECKPOINT_RESULT,
    COMPILED_ROUTES,
    CURRENT_OWNER,
    CURATED_POSITIVE,
    CURATED_ROUTE_GOLD,
    CURATED_ROUTE_INPUTS,
    CURATION_CONTRACT,
    CURATOR_RECEIPT,
    DELIVERY_RECEIPT,
    EXTERNAL_AUDIT,
    FROZEN_SHA256,
    HIDDEN_FREEZE,
    LIFECYCLE,
    OLD_P4_ROOT,
    OLD_P4_TREE,
    P3_RECOVERY_BASELINE,
    POSITIVE_OUTPUTS,
    PREFREEZE_REPORT,
    REVIEW_CONTRACT,
    REVIEW_ONE,
    REVIEW_ONE_STAGE,
    REVIEW_TWO,
    REVIEW_TWO_STAGE,
    ROOT,
    ROUTE_ACTUALS,
    ROUTE_ACTUAL_FREEZE,
    ROUTE_COMPARISONS,
    ROUTE_GOLD,
    ROUTE_INPUTS,
    RUN_ORDER,
    TASK_ID,
    TASK_ROOT,
    TOOL_COMMIT_BINDING,
    TOOL_FREEZE,
    _git,
    _route_metrics,
    _validate_hidden_artifacts,
    load_yaml,
    object_digest,
    review_metrics,
    selftest as tool_selftest,
    sha256_file,
    validate_author_outputs,
)


if not __debug__:
    sys.stderr.write("p4_resealed_guard refuses python -O\n")
    raise SystemExit(2)


def _add(errors: list[dict[str, str]], code: str, detail: str = "") -> None:
    errors.append({"code": code, "detail": detail})


def _owner(root: Path) -> dict[str, Any]:
    value = load_yaml(root / CURRENT_OWNER).get("current_gate1_owner")
    if not isinstance(value, dict):
        raise TypeError("current owner")
    return value


def _validate_tool_freeze(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        freeze = load_yaml(root / TOOL_FREEZE).get("p4_resealed_tool_freeze")
        if not isinstance(freeze, dict):
            raise TypeError("tool freeze")
        if freeze.get("freeze_digest") != object_digest(freeze, "freeze_digest"):
            _add(errors, "E_P4R_TOOL_FREEZE_DIGEST")
        if freeze.get("task_id") != TASK_ID:
            _add(errors, "E_P4R_TOOL_TASK")
        for path, expected in freeze.get("tool_files", {}).items():
            candidate = root / Path(path)
            if not candidate.is_file() or sha256_file(candidate) != expected:
                _add(errors, "E_P4R_TOOL_DRIFT", path)
        for path, expected in freeze.get("contract_files", {}).items():
            candidate = root / Path(path)
            if not candidate.is_file() or sha256_file(candidate) != expected:
                _add(errors, "E_P4R_CONTRACT_DRIFT", path)
        for path, expected in freeze.get("frozen_business_files", {}).items():
            candidate = root / Path(path)
            if not candidate.is_file() or sha256_file(candidate) != expected:
                _add(errors, "E_P4R_BUSINESS_FREEZE_DRIFT", path)
    except (OSError, TypeError, ValueError, KeyError, yaml.YAMLError) as exc:
        _add(errors, "E_P4R_TOOL_FREEZE_PARSE", str(exc))


def _validate_history(root: Path, errors: list[dict[str, str]]) -> None:
    for path, expected in FROZEN_SHA256.items():
        if not (root / path).is_file() or sha256_file(root / path) != expected:
            _add(errors, "E_P4R_FROZEN_SHA", path.as_posix())
    tree = _git("rev-parse", f"{P3_RECOVERY_BASELINE}:{OLD_P4_ROOT.as_posix()}")
    if tree.returncode != 0 or tree.stdout.strip() != OLD_P4_TREE:
        _add(errors, "E_P4R_OLD_P4_TREE", tree.stdout.strip())
    if _git("diff", "--quiet", P3_RECOVERY_BASELINE, "--", OLD_P4_ROOT.as_posix()).returncode != 0:
        _add(errors, "E_P4R_OLD_P4_MUTATION")
    errors.extend(validate_p3_recovery_current(root))


def _hidden_commit(root: Path) -> str:
    result = _git("log", "--format=%H", "--diff-filter=A", "--", HIDDEN_FREEZE.as_posix())
    return result.stdout.splitlines()[0] if result.returncode == 0 and result.stdout.splitlines() else ""


def _validate_hidden_stage(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        _validate_hidden_artifacts()
        binding = load_yaml(root / TOOL_COMMIT_BINDING).get("p4_tool_commit_binding")
        freeze = load_yaml(root / HIDDEN_FREEZE).get("p4_resealed_hidden_input_freeze")
        if not isinstance(binding, dict) or binding.get("binding_digest") != object_digest(binding, "binding_digest"):
            _add(errors, "E_P4R_TOOL_BINDING")
            return
        if not isinstance(freeze, dict) or freeze.get("freeze_digest") != object_digest(freeze, "freeze_digest"):
            _add(errors, "E_P4R_HIDDEN_FREEZE")
            return
        tool_commit = str(binding.get("tool_freeze_commit", ""))
        hidden_commit = _hidden_commit(root)
        if not tool_commit or not hidden_commit:
            _add(errors, "E_P4R_COMMIT_DISCOVERY")
            return
        if _git("merge-base", "--is-ancestor", tool_commit, hidden_commit).returncode != 0:
            _add(errors, "E_P4R_FREEZE_ORDER", f"{tool_commit}:{hidden_commit}")
        for path in (CURATED_POSITIVE, CURATED_ROUTE_INPUTS, CURATED_ROUTE_GOLD, HIDDEN_FREEZE):
            if _git("cat-file", "-e", f"{tool_commit}:{path.as_posix()}").returncode == 0:
                _add(errors, "E_P4R_HIDDEN_IN_TOOL_COMMIT", path.as_posix())
        forbidden_at_hidden = (
            POSITIVE_OUTPUTS,
            AUTHOR_RECEIPT,
            COMPILED_ROUTES,
            ROUTE_ACTUALS,
            ROUTE_ACTUAL_FREEZE,
            ROUTE_COMPARISONS,
            REVIEW_ONE_STAGE,
            REVIEW_TWO_STAGE,
            REVIEW_ONE,
            REVIEW_TWO,
            CHECKPOINT_RESULT,
        )
        for path in forbidden_at_hidden:
            if _git("cat-file", "-e", f"{hidden_commit}:{path.as_posix()}").returncode == 0:
                _add(errors, "E_P4R_RESULT_IN_HIDDEN_COMMIT", path.as_posix())
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        _add(errors, "E_P4R_HIDDEN_STAGE", str(exc))


def _validate_final_stage(root: Path, errors: list[dict[str, str]]) -> None:
    required = (
        POSITIVE_OUTPUTS,
        AUTHOR_RECEIPT,
        ROUTE_ACTUALS,
        ROUTE_ACTUAL_FREEZE,
        ROUTE_COMPARISONS,
        BLIND_PACKET,
        BLIND_CATALOG,
        BLIND_MAPPING,
        REVIEW_ONE_STAGE,
        REVIEW_TWO_STAGE,
        REVIEW_ONE,
        REVIEW_TWO,
        EXTERNAL_AUDIT,
        CHECKPOINT_RESULT,
        DELIVERY_RECEIPT,
    )
    for path in required:
        if not (root / path).is_file():
            _add(errors, "E_P4R_FINAL_REQUIRED", path.as_posix())
    if errors:
        return
    try:
        validate_author_outputs()
        reviews = review_metrics()
        routes = _route_metrics()
        if reviews["reviewer_one"]["first_acceptable"] < 18 or reviews["reviewer_two"]["first_acceptable"] < 18:
            _add(errors, "E_P4R_ACCEPTANCE_GATE")
        if reviews["reviewer_one"]["blind_correct"] < 17 or reviews["reviewer_two"]["blind_correct"] < 17:
            _add(errors, "E_P4R_BLIND_GATE")
        if len(reviews["formula_union"]) > 2:
            _add(errors, "E_P4R_FORMULA_GATE", str(reviews["formula_union"]))
        if reviews["hard_error_union"]:
            _add(errors, "E_P4R_HARD_ERRORS", str(reviews["hard_error_union"]))
        if not (routes["count"] == routes["action_match"] == routes["reason_match"] == 20):
            _add(errors, "E_P4R_ROUTE_GATE", str(routes))
        if routes["audience_content_leak_count"] != 0 or set(routes["actions"]) != {"BLOCK", "REQUEST_INPUT", "DEGRADE"}:
            _add(errors, "E_P4R_ROUTE_BOUNDARY", str(routes))
        audit = load_yaml(root / EXTERNAL_AUDIT).get("p4_resealed_external_exit_audit")
        if not isinstance(audit, dict) or audit.get("audit_digest") != object_digest(audit, "audit_digest"):
            _add(errors, "E_P4R_EXIT_AUDIT")
        elif audit.get("external_api_or_network_call_count") != len(audit.get("observed_content_exit_events", [])) or audit.get("external_api_or_network_call_count") != 0:
            _add(errors, "E_P4R_EXTERNAL_EXIT")
        result = load_yaml(root / CHECKPOINT_RESULT).get("p4_resealed_checkpoint_result")
        if not isinstance(result, dict) or result.get("result_digest") != object_digest(result, "result_digest"):
            _add(errors, "E_P4R_RESULT_DIGEST")
        elif (
            result.get("result_state") != "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION"
            or result.get("generator_qualified") is not False
            or result.get("p5_allowed") is not False
            or result.get("H_admitted_count") != 0
            or result.get("readiness_true_keys") != []
        ):
            _add(errors, "E_P4R_RESULT_BOUNDARY", str(result))
        owner = _owner(root)
        if (
            owner.get("owner_id") != "GATE1_V11_P4_RESEALED_PENDING_OWNER"
            or owner.get("result_state") != "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION"
            or owner.get("generator_qualified") is not False
            or owner.get("p5_allowed") is not False
            or owner.get("owner_digest") != object_digest(owner, "owner_digest")
        ):
            _add(errors, "E_P4R_OWNER_BOUNDARY")
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        _add(errors, "E_P4R_FINAL_STAGE", str(exc))


def validate_p4_resealed(root: Path = ROOT) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required_tools = (
        TASK_ROOT / "p4_resealed.py",
        TASK_ROOT / "p4_resealed_guard.py",
        TASK_ROOT / "p3_recovery_guard_current.py",
        TOOL_FREEZE,
        CURATION_CONTRACT,
        REVIEW_CONTRACT,
        LIFECYCLE,
    )
    for path in required_tools:
        if not (root / path).is_file():
            _add(errors, "E_P4R_REQUIRED_TOOL", path.as_posix())
    if errors:
        return errors
    _validate_tool_freeze(root, errors)
    _validate_history(root, errors)
    hidden_any = any((root / path).exists() for path in (CURATED_POSITIVE, CURATED_ROUTE_INPUTS, CURATED_ROUTE_GOLD, HIDDEN_FREEZE))
    hidden_all = all((root / path).is_file() for path in (CURATED_POSITIVE, CURATED_ROUTE_INPUTS, CURATED_ROUTE_GOLD, CURATOR_RECEIPT, PREFREEZE_REPORT, AUTHOR_REQUESTS, ROUTE_INPUTS, ROUTE_GOLD, RUN_ORDER, HIDDEN_FREEZE, TOOL_COMMIT_BINDING))
    if hidden_any and not hidden_all:
        _add(errors, "E_P4R_PARTIAL_HIDDEN_STAGE")
    elif hidden_all:
        _validate_hidden_stage(root, errors)
    result_any = any((root / path).exists() for path in (POSITIVE_OUTPUTS, ROUTE_ACTUALS, REVIEW_ONE, REVIEW_TWO, CHECKPOINT_RESULT))
    if result_any:
        _validate_final_stage(root, errors)
    else:
        try:
            owner = _owner(root)
            if owner.get("owner_id") != "GATE1_V11_P3_ROUTE_COMPILER_RECOVERY_OWNER":
                _add(errors, "E_P4R_EARLY_OWNER_ADVANCE", str(owner.get("owner_id")))
        except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
            _add(errors, "E_P4R_OWNER_PARSE", str(exc))
    return errors


def selftest(root: Path = ROOT) -> int:
    try:
        tool_selftest()
        freeze = load_yaml(root / TOOL_FREEZE)["p4_resealed_tool_freeze"]
        tampered = dict(freeze)
        tampered["hidden_material_absent"] = False
        if tampered.get("freeze_digest") == object_digest(tampered, "freeze_digest"):
            raise ValueError("tool freeze tamper accepted")
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "SELFTEST_FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "SELFTEST_PASS", "real_load_bearing_tamper_suite": True}, ensure_ascii=False))
    return 0


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        return selftest(ROOT)
    errors = validate_p4_resealed(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "task_id": TASK_ID}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
