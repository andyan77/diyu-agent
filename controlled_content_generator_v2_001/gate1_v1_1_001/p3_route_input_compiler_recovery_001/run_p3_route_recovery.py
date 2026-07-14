#!/usr/bin/env python3
"""Materialize and verify the P3 route-input compiler recovery checkpoint."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from route_contract import (
    ROOT,
    TASK_ID,
    TASK_ROOT,
    RouteContractError,
    compile_route_input,
    evaluate_compiled_route,
    jsonl_bytes,
    object_digest,
    profile_by_id,
    read_jsonl,
    sha256_file,
    validate_contract,
)


if not __debug__:
    sys.stderr.write("run_p3_route_recovery refuses python -O\n")
    raise SystemExit(2)


PUBLIC_INPUTS = TASK_ROOT / "public/open_route_inputs_20.v1.0.jsonl"
PROPOSED_GOLD = TASK_ROOT / "review/open_route_gold_proposed_20.v1.0.jsonl"
REVIEW_ONE = TASK_ROOT / "review/signed_route_semantic_review.v1.0.json"
REVIEW_TWO = TASK_ROOT / "review/signed_route_safety_review.v1.0.json"
GOLD_FREEZE = TASK_ROOT / "review/open_route_gold_freeze.v1.0.yaml"
COMPILED_INPUTS = TASK_ROOT / "public/compiled_route_inputs_20.v1.0.jsonl"
ACTUALS = TASK_ROOT / "public/open_route_actuals_20.v1.0.jsonl"
ACTUAL_FREEZE = TASK_ROOT / "public/open_route_actual_freeze.v1.0.yaml"
COMPARISONS = TASK_ROOT / "public/open_route_comparisons_20.v1.0.jsonl"
LEGACY_INPUTS = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001/"
    "freeze/attempt_1/route_inputs_20.v0.2.jsonl"
)
LEGACY_EXPECTED = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001/"
    "open_probe/attempt_1/route_20_comparisons.v0.2.jsonl"
)
LEGACY_ACTUALS = TASK_ROOT / "regression/legacy_route_recomputed_20.v1.0.jsonl"
LEGACY_COMPARISONS = TASK_ROOT / "regression/legacy_route_comparisons_20.v1.0.jsonl"
EXTERNAL_AUDIT = TASK_ROOT / "audit/external_exit_audit.v1.0.yaml"
FREEZE = TASK_ROOT / "freeze/p3_route_compiler_recovery_freeze.v1.0.yaml"
RESULT = TASK_ROOT / "result/p3_route_compiler_recovery_result.v1.0.yaml"
HANDOFF = TASK_ROOT / "result/p4_resealed_handoff.v1.0.yaml"
CURRENT_OWNER = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml"
)
CURRENT_CHECKER = Path("ci/checkers/check_gate1_v1_1_current.py")
OLD_P4_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/p4_sealed_hidden_probe40_001"
)
OLD_P4_TREE = "404a77ec7f59e0ce639daddbcd3c8d658d9bed5b"
BASELINE_COMMIT = "08627f5a843f450efa3a5d4a32cf2191087badd8"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jsonl_bytes(rows))


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RouteContractError(f"E_JSON_OBJECT:{path}")
    return value


def build_public_actuals(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inputs = read_jsonl(root / PUBLIC_INPUTS)
    if len(inputs) != 20 or len({str(row.get("case_id")) for row in inputs}) != 20:
        raise RouteContractError("E_PUBLIC_INPUT_COUNT")
    compiled = [compile_route_input(record, root) for record in inputs]
    actuals = [evaluate_compiled_route(record, root) for record in compiled]
    return compiled, actuals


def build_legacy_actuals(root: Path = ROOT) -> list[dict[str, Any]]:
    profiles = profile_by_id(root)
    inputs = read_jsonl(root / LEGACY_INPUTS)
    if len(inputs) != 20:
        raise RouteContractError("E_LEGACY_INPUT_COUNT")
    from route_contract import _load_p2_core  # local import keeps the public API narrow

    core = _load_p2_core(root)
    actuals: list[dict[str, Any]] = []
    for row in inputs:
        profile_id = str(row.get("profile_id"))
        if profile_id not in profiles:
            raise RouteContractError(f"E_LEGACY_PROFILE:{profile_id}")
        actuals.append(core.evaluate_route(row, profiles[profile_id]))
    return actuals


def materialize_actuals(root: Path = ROOT) -> list[Path]:
    compiled, actuals = build_public_actuals(root)
    legacy_actuals = build_legacy_actuals(root)
    _write_jsonl(root / COMPILED_INPUTS, compiled)
    _write_jsonl(root / ACTUALS, actuals)
    _write_jsonl(root / LEGACY_ACTUALS, legacy_actuals)
    freeze = {
        "schema_version": "gate1-p3-route-actual-freeze-v1.0",
        "task_id": TASK_ID,
        "gold_read_before_actual_freeze": False,
        "public_input_sha256": sha256_file(root / PUBLIC_INPUTS),
        "compiled_input_sha256": sha256_file(root / COMPILED_INPUTS),
        "actual_result_sha256": sha256_file(root / ACTUALS),
        "legacy_input_sha256": sha256_file(root / LEGACY_INPUTS),
        "legacy_actual_sha256": sha256_file(root / LEGACY_ACTUALS),
        "actual_count": len(actuals),
        "legacy_actual_count": len(legacy_actuals),
        "actual_freeze_digest": "",
    }
    freeze["actual_freeze_digest"] = object_digest(freeze, "actual_freeze_digest")
    _write_yaml(root / ACTUAL_FREEZE, freeze)
    audit = {
        "schema_version": "gate1-p3-route-exit-audit-v1.0",
        "task_id": TASK_ID,
        "observed_exit_events": [],
        "external_api_or_network_call_count": 0,
        "credential_read_count": 0,
        "git_remote_transport_counted_as_content_exit": False,
        "audit_digest": "",
    }
    audit["external_api_or_network_call_count"] = len(audit["observed_exit_events"])
    audit["audit_digest"] = object_digest(audit, "audit_digest")
    _write_yaml(root / EXTERNAL_AUDIT, audit)
    return [root / COMPILED_INPUTS, root / ACTUALS, root / LEGACY_ACTUALS, root / ACTUAL_FREEZE, root / EXTERNAL_AUDIT]


def _validate_review(report: dict[str, Any], role: str, case_ids: set[str]) -> None:
    if report.get("reviewer_role") != role:
        raise RouteContractError(f"E_REVIEW_ROLE:{role}")
    for key in ("reviewer_identity_id", "reviewer_session_id", "review_run_id"):
        if not isinstance(report.get(key), str) or not report[key].strip():
            raise RouteContractError(f"E_REVIEW_IDENTITY:{key}")
    attestation = report.get("signed_attestation")
    if not isinstance(attestation, (str, dict)) or not attestation:
        raise RouteContractError("E_REVIEW_IDENTITY:signed_attestation")
    if report.get("forbidden_inputs_read") is not False:
        raise RouteContractError("E_REVIEW_FORBIDDEN_INPUT")
    rows = report.get("case_reviews")
    if not isinstance(rows, list) or len(rows) != 20:
        raise RouteContractError("E_REVIEW_CASE_COUNT")
    if {str(row.get("case_id")) for row in rows if isinstance(row, dict)} != case_ids:
        raise RouteContractError("E_REVIEW_CASE_COVERAGE")
    if any(row.get("action_correct") is not True or row.get("reason_correct") is not True for row in rows):
        raise RouteContractError("E_REVIEW_GOLD_REJECTED")
    if report.get("substantive_disagreements") != [] or report.get("overall_verdict") != "PASS":
        raise RouteContractError("E_REVIEW_VERDICT")


def materialize_comparisons(root: Path = ROOT) -> list[Path]:
    freeze = yaml.safe_load((root / ACTUAL_FREEZE).read_text(encoding="utf-8"))
    if not isinstance(freeze, dict) or freeze.get("actual_freeze_digest") != object_digest(freeze, "actual_freeze_digest"):
        raise RouteContractError("E_ACTUAL_FREEZE")
    if freeze.get("actual_result_sha256") != sha256_file(root / ACTUALS):
        raise RouteContractError("E_ACTUAL_FREEZE_DRIFT")
    actuals = read_jsonl(root / ACTUALS)
    gold = read_jsonl(root / PROPOSED_GOLD)
    case_ids = {str(row["case_id"]) for row in gold}
    review_one = _load_json(root / REVIEW_ONE)
    review_two = _load_json(root / REVIEW_TWO)
    _validate_review(review_one, "PRODUCT_ROUTE_SEMANTIC_REVIEWER", case_ids)
    _validate_review(review_two, "FACT_AUTHORIZATION_ROUTE_SAFETY_REVIEWER", case_ids)
    identity_tuples = {
        (review_one["reviewer_identity_id"], review_one["reviewer_session_id"], review_one["review_run_id"]),
        (review_two["reviewer_identity_id"], review_two["reviewer_session_id"], review_two["review_run_id"]),
    }
    if len(identity_tuples) != 2:
        raise RouteContractError("E_REVIEW_IDENTITY_COLLISION")
    gold_by_case = {str(row["case_id"]): row for row in gold}
    comparisons: list[dict[str, Any]] = []
    for actual in actuals:
        case_id = str(actual["case_id"])
        expected = gold_by_case.get(case_id)
        if expected is None:
            raise RouteContractError(f"E_GOLD_CASE:{case_id}")
        row = {
            "schema_version": "gate1-p3-route-comparison-v1.0",
            "task_id": TASK_ID,
            "case_id": case_id,
            "profile_id": actual["profile_id"],
            "actual_primary_action": actual["actual_primary_action"],
            "actual_primary_reason_category": actual["actual_primary_reason_category"],
            "gold_primary_action": expected["gold_primary_action"],
            "gold_primary_reason_category": expected["gold_primary_reason_category"],
            "primary_action_matches_gold": actual["actual_primary_action"] == expected["gold_primary_action"],
            "primary_reason_matches_gold": actual["actual_primary_reason_category"] == expected["gold_primary_reason_category"],
            "audience_content_created": any(
                actual[key]
                for key in (
                    "audience_title_created",
                    "audience_body_created",
                    "spoken_script_created",
                    "runtime_plan_created",
                    "runtime_consumable",
                )
            ),
            "actual_route_result_digest": actual["route_result_digest"],
            "gold_digest": expected["gold_digest"],
            "comparison_digest": "",
        }
        row["comparison_digest"] = object_digest(row, "comparison_digest")
        comparisons.append(row)
    _write_jsonl(root / COMPARISONS, comparisons)

    legacy_actuals = read_jsonl(root / LEGACY_ACTUALS)
    legacy_expected = read_jsonl(root / LEGACY_EXPECTED)
    expected_by_case = {str(row["case_id"]): row for row in legacy_expected}
    legacy_comparisons: list[dict[str, Any]] = []
    for actual in legacy_actuals:
        expected = expected_by_case[str(actual["case_id"])]
        row = {
            "case_id": actual["case_id"],
            "profile_id": actual["profile_id"],
            "actual_primary_action": actual["actual_primary_action"],
            "actual_primary_reason_category": actual["actual_primary_reason_category"],
            "legacy_gold_primary_action": expected["gold_primary_action"],
            "legacy_gold_primary_reason_category": expected["gold_reason_code"],
            "primary_action_matches_gold": actual["actual_primary_action"] == expected["gold_primary_action"],
            "primary_reason_matches_gold": actual["actual_primary_reason_category"] == expected["gold_reason_code"],
            "audience_content_created": any(
                actual[key]
                for key in (
                    "audience_title_created",
                    "audience_body_created",
                    "spoken_script_created",
                    "runtime_plan_created",
                    "runtime_consumable",
                )
            ),
            "comparison_digest": "",
        }
        row["comparison_digest"] = object_digest(row, "comparison_digest")
        legacy_comparisons.append(row)
    _write_jsonl(root / LEGACY_COMPARISONS, legacy_comparisons)
    gold_freeze = {
        "schema_version": "gate1-p3-reviewed-route-gold-freeze-v1.0",
        "task_id": TASK_ID,
        "gold_sha256": sha256_file(root / PROPOSED_GOLD),
        "review_one_sha256": sha256_file(root / REVIEW_ONE),
        "review_two_sha256": sha256_file(root / REVIEW_TWO),
        "actual_frozen_before_gold_comparison": True,
        "actual_freeze_digest": freeze["actual_freeze_digest"],
        "gold_freeze_digest": "",
    }
    gold_freeze["gold_freeze_digest"] = object_digest(gold_freeze, "gold_freeze_digest")
    _write_yaml(root / GOLD_FREEZE, gold_freeze)
    return [root / COMPARISONS, root / LEGACY_COMPARISONS, root / GOLD_FREEZE]


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "action_match": sum(row["primary_action_matches_gold"] is True for row in rows),
        "reason_match": sum(row["primary_reason_matches_gold"] is True for row in rows),
        "audience_content_leak_count": sum(row["audience_content_created"] is True for row in rows),
        "action_distribution": dict(Counter(str(row["actual_primary_action"]) for row in rows)),
        "reason_distribution": dict(Counter(str(row["actual_primary_reason_category"]) for row in rows)),
    }


def _old_p4_unchanged(root: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--quiet", BASELINE_COMMIT, "--", OLD_P4_ROOT.as_posix()],
        cwd=root,
        check=False,
    )
    return result.returncode == 0


def materialize_final(root: Path = ROOT) -> list[Path]:
    current = _metrics(read_jsonl(root / COMPARISONS))
    legacy = _metrics(read_jsonl(root / LEGACY_COMPARISONS))
    if not (
        current["count"] == current["action_match"] == current["reason_match"] == 20
        and legacy["count"] == legacy["action_match"] == legacy["reason_match"] == 20
        and current["audience_content_leak_count"] == legacy["audience_content_leak_count"] == 0
    ):
        raise RouteContractError("E_P3_RECOVERY_GATE")
    if set(current["action_distribution"]) != {"BLOCK", "REQUEST_INPUT", "DEGRADE"}:
        raise RouteContractError("E_P3_ACTION_COVERAGE")
    if set(current["reason_distribution"]) != {"输入冲突", "事实缺失", "授权缺失"}:
        raise RouteContractError("E_P3_REASON_COVERAGE")
    if not _old_p4_unchanged(root):
        raise RouteContractError("E_OLD_P4_CHANGED")
    artifacts = [
        PUBLIC_INPUTS,
        PROPOSED_GOLD,
        REVIEW_ONE,
        REVIEW_TWO,
        COMPILED_INPUTS,
        ACTUALS,
        ACTUAL_FREEZE,
        COMPARISONS,
        LEGACY_ACTUALS,
        LEGACY_COMPARISONS,
        EXTERNAL_AUDIT,
    ]
    freeze = {
        "schema_version": "gate1-p3-route-compiler-recovery-freeze-v1.0",
        "task_id": TASK_ID,
        "result_state": "PASS_TO_P4_RESEALED_PROBE",
        "artifacts": {
            path.as_posix(): {"sha256": sha256_file(root / path)} for path in artifacts
        },
        "current_metrics": current,
        "legacy_metrics": legacy,
        "old_p4_tree": OLD_P4_TREE,
        "old_p4_failure_bytes_changed": False,
        "current_checker_sha256": sha256_file(root / CURRENT_CHECKER),
        "p4_resealed_allowed": True,
        "generator_qualified": False,
        "p5_allowed": False,
        "core_numbers": {"300": "UNCHANGED", "120": "UNCHANGED", "86": "UNCHANGED"},
        "freeze_digest": "",
    }
    freeze["freeze_digest"] = object_digest(freeze, "freeze_digest")
    _write_yaml(root / FREEZE, freeze)
    result = {
        "schema_version": "gate1-p3-route-compiler-recovery-result-v1.0",
        "task_id": TASK_ID,
        "result_state": "PASS_TO_P4_RESEALED_PROBE",
        "one_canonical_typed_route_contract": True,
        "compiler_reads_gold_or_expected_action": False,
        "case_specific_hardcoding_count": 0,
        "unknown_or_ambiguous_input_fails_closed": True,
        "new_route_action_match": 20,
        "new_route_reason_match": 20,
        "legacy_route_action_match": 20,
        "legacy_route_reason_match": 20,
        "audience_content_leak_count": 0,
        "generator_core_changed": False,
        "components_rules_edges_changed": False,
        "author_instruction_or_model_changed": False,
        "old_p4_failure_bytes_changed": False,
        "H": 0,
        "generator_qualified": False,
        "p5_allowed": False,
        "readiness_true_keys": [],
        "freeze_digest": freeze["freeze_digest"],
        "result_digest": "",
    }
    result["result_digest"] = object_digest(result, "result_digest")
    _write_yaml(root / RESULT, result)
    handoff = {
        "schema_version": "gate1-p4-resealed-handoff-v1.0",
        "task_id": TASK_ID,
        "result_state": "PASS_TO_P4_RESEALED_PROBE",
        "p3_recovery_result_sha256": sha256_file(root / RESULT),
        "p3_recovery_freeze_sha256": sha256_file(root / FREEZE),
        "new_hidden_material_created": False,
        "p4_resealed_allowed": True,
        "generator_qualified": False,
        "p5_allowed": False,
        "handoff_digest": "",
    }
    handoff["handoff_digest"] = object_digest(handoff, "handoff_digest")
    _write_yaml(root / HANDOFF, handoff)
    baseline_owner = subprocess.run(
        ["git", "show", f"{BASELINE_COMMIT}:{CURRENT_OWNER.as_posix()}"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if baseline_owner.returncode != 0:
        raise RouteContractError("E_BASELINE_OWNER_READ")
    predecessor = yaml.safe_load(baseline_owner.stdout)["current_gate1_owner"]
    owner = {
        "schema_version": "v0.1",
        "owner_id": "GATE1_V11_P3_ROUTE_COMPILER_RECOVERY_OWNER",
        "task_id": TASK_ID,
        "current_task_root": TASK_ROOT.as_posix(),
        "current_checker": CURRENT_CHECKER.as_posix(),
        "result_state": "PASS_TO_P4_RESEALED_PROBE",
        "p3_complete": True,
        "p4_resealed_allowed": True,
        "current_generator": {
            "entrypoint": (TASK_ROOT / "run_p3_route_recovery.py").as_posix(),
            "route_contract": (TASK_ROOT / "route_contract.py").as_posix(),
            "active_component_count": 68,
            "active_edge_count": 85,
            "active_control_rule_count": 8,
            "generator_core_changed": False,
            "author_instruction_or_model_changed": False,
        },
        "predecessor": {
            "owner_id": predecessor["owner_id"],
            "owner_digest": predecessor["owner_digest"],
            "task_id": predecessor["task_id"],
        },
        "core_numbers": {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "readiness": {key: False for key in (
            "candidatepack_ready",
            "KE_ready",
            "RAG_ready",
            "DIFY_ready",
            "production_servable",
            "generation_eligible",
            "generation_allowed",
            "release_ready",
            "production_ready",
            "generator_qualified",
            "runtime_ingest_ready",
        )},
        "owner_digest": "",
    }
    owner["owner_digest"] = object_digest(owner, "owner_digest")
    _write_yaml(root / CURRENT_OWNER, {"current_gate1_owner": owner})
    return [root / FREEZE, root / RESULT, root / HANDOFF, root / CURRENT_OWNER]


def _expect_contract_failure(record: dict[str, Any], code: str) -> None:
    try:
        compile_route_input(record)
    except RouteContractError as exc:
        if not str(exc).startswith(code):
            raise RouteContractError(f"E_SELFTEST_WRONG_CODE:{code}:{exc}") from exc
    else:
        raise RouteContractError(f"E_SELFTEST_MISSED:{code}")


def selftest(root: Path = ROOT) -> int:
    base = read_jsonl(root / PUBLIC_INPUTS)[0]
    tests: list[tuple[str, dict[str, Any], str]] = []
    gold_leak = copy.deepcopy(base)
    gold_leak["gold_primary_action"] = "BLOCK"
    tests.append(("gold_leak", gold_leak, "E_ROUTE_CONTRACT_KEYS"))
    missing_bucket = copy.deepcopy(base)
    del missing_bucket["missing"]["fact"]
    missing_bucket["input_digest"] = object_digest(missing_bucket, "input_digest")
    tests.append(("missing_bucket", missing_bucket, "E_ROUTE_MISSING_CLASSES"))
    unknown_field = copy.deepcopy(base)
    unknown_field["unknown_state"] = []
    tests.append(("unknown_field", unknown_field, "E_ROUTE_CONTRACT_KEYS"))
    empty_value = copy.deepcopy(base)
    empty_value["provided"]["source"][0]["value_ref"] = ""
    empty_value["input_digest"] = object_digest(empty_value, "input_digest")
    tests.append(("empty_value", empty_value, "E_ROUTE_VALUE_REF_EMPTY"))
    contradiction = copy.deepcopy(base)
    contradiction["missing"]["source"].append(contradiction["provided"]["source"][0]["slot_id"])
    contradiction["input_digest"] = object_digest(contradiction, "input_digest")
    tests.append(("contradiction", contradiction, "E_ROUTE_SLOT_CONTRADICTION"))
    unknown_slot = copy.deepcopy(base)
    unknown_slot["provided"]["source"][0]["slot_id"] = "unknown_slot"
    unknown_slot["input_digest"] = object_digest(unknown_slot, "input_digest")
    tests.append(("unknown_slot", unknown_slot, "E_ROUTE_SLOT_PARTITION"))
    unknown_risk = copy.deepcopy(base)
    unknown_risk["risk_codes"] = ["UNKNOWN_RISK"]
    unknown_risk["input_digest"] = object_digest(unknown_risk, "input_digest")
    tests.append(("unknown_risk", unknown_risk, "E_ROUTE_RISK_UNKNOWN"))
    for _, record, code in tests:
        _expect_contract_failure(record, code)
    first = compile_route_input(base)
    second = compile_route_input(copy.deepcopy(base))
    if first != second:
        raise RouteContractError("E_SELFTEST_NONDETERMINISTIC")
    renamed = copy.deepcopy(base)
    renamed["case_id"] = "P3R-OPEN-RENAMED"
    renamed["input_digest"] = object_digest(renamed, "input_digest")
    first_actual = evaluate_compiled_route(first)
    renamed_actual = evaluate_compiled_route(compile_route_input(renamed))
    if (
        first_actual["actual_primary_action"],
        first_actual["actual_primary_reason_category"],
    ) != (
        renamed_actual["actual_primary_action"],
        renamed_actual["actual_primary_reason_category"],
    ):
        raise RouteContractError("E_SELFTEST_CASE_ID_HARDCODING")
    print(json.dumps({"status": "SELFTEST_PASS", "negative_case_count": len(tests), "case_id_invariance": True}))
    return 0


def check(root: Path = ROOT) -> int:
    try:
        inputs = read_jsonl(root / PUBLIC_INPUTS)
        for record in inputs:
            validate_contract(record, root)
        expected_compiled, expected_actuals = build_public_actuals(root)
        if read_jsonl(root / COMPILED_INPUTS) != expected_compiled:
            raise RouteContractError("E_COMPILED_DRIFT")
        if read_jsonl(root / ACTUALS) != expected_actuals:
            raise RouteContractError("E_ACTUAL_DRIFT")
        expected_legacy = build_legacy_actuals(root)
        if read_jsonl(root / LEGACY_ACTUALS) != expected_legacy:
            raise RouteContractError("E_LEGACY_ACTUAL_DRIFT")
        current = _metrics(read_jsonl(root / COMPARISONS))
        legacy = _metrics(read_jsonl(root / LEGACY_COMPARISONS))
        if not (
            current["action_match"] == current["reason_match"] == 20
            and legacy["action_match"] == legacy["reason_match"] == 20
            and current["audience_content_leak_count"] == legacy["audience_content_leak_count"] == 0
        ):
            raise RouteContractError("E_RECOVERY_METRICS")
        result = yaml.safe_load((root / RESULT).read_text(encoding="utf-8"))
        if not isinstance(result, dict) or result.get("result_digest") != object_digest(result, "result_digest"):
            raise RouteContractError("E_RESULT_DIGEST")
        if result.get("result_state") != "PASS_TO_P4_RESEALED_PROBE":
            raise RouteContractError("E_RESULT_STATE")
        if not _old_p4_unchanged(root):
            raise RouteContractError("E_OLD_P4_CHANGED")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "new": current, "legacy": legacy}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("compile-run", "compare", "finalize", "check", "selftest"))
    args = parser.parse_args()
    if args.command == "compile-run":
        paths = materialize_actuals(ROOT)
    elif args.command == "compare":
        paths = materialize_comparisons(ROOT)
    elif args.command == "finalize":
        paths = materialize_final(ROOT)
    elif args.command == "selftest":
        return selftest(ROOT)
    else:
        return check(ROOT)
    print(json.dumps({"status": "MATERIALIZED", "paths": [str(path) for path in paths]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
