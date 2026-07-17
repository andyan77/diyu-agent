#!/usr/bin/env python3
"""Fail-closed verifier for the Package 10 honest-stop evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from collections.abc import Callable, Iterable
from typing import Any


if not __debug__:
    print("check_internal_pilot_release_evaluation refuses python -O", file=sys.stderr)
    raise SystemExit(2)


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
TASK_ID = "DIYU_INTERNAL_PILOT_RELEASE_EVALUATION_001"
FROZEN_COMMIT = "82b253c2b0ac362f1c5397bafb789ee400453944"
FORMAL_EVIDENCE_SHA256 = (
    "46147ee16d9ae70a1d93d0f0689ae5e8de229608978d299fc0d312998e991cea"
)
FROZEN_REPO_PATH_SHA256 = {
    Path("20_internal_pilot/release_evaluation_001/evaluation_plan.v1.json"):
        "d91b113bcac71913769c35a7a82285c4518647e6d21c07c51f80e8e166bf0363",
    Path("20_internal_pilot/release_evaluation_001/package10_evaluation.py"):
        "73c3187ed053098fd70b70e2e13731fa4005e4dd244d8b4d73a8cb1ed4737678",
    Path("20_internal_pilot/release_evaluation_001/package10_material_alignment.py"):
        "3d041adcace61017efde7e6f679351147ffa6bbaacd789db808cce3e74da89c3",
    Path("17_dify_runtime/dify_end_to_end_001/content_capability_mapping.v1.yaml"):
        "d3882635ffdf7140f1960102b8bee071e5b6268e86f6e3715868f1ae397445b4",
    Path("17_dify_runtime/dify_end_to_end_001/dify_app.v1.yaml"):
        "4739f284df5e99d79e657312335777faa4ecbefce02217ef43fe5d3fb3cdb25a",
    Path("17_dify_runtime/dify_end_to_end_001/dify_chat.py"):
        "9c033b2cb150c85eb01ed9dfaae7e1d346ad15e856b2deb54a89ae529e650681",
    Path("17_dify_runtime/dify_end_to_end_001/runtime_service.py"):
        "4a5231a16251f33333292dad5dadb2e9aeef6f58034e189ae1d0ebf207b690ac",
}
READINESS_KEYS = {
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
}
EVIDENCE_PATHS = {
    "freeze": Path("evidence/freeze_manifest.v1.json"),
    "transport": Path("evidence/formal_transport_attempt.v1.json"),
    "formal": Path("evidence/formal_run_summary.v1.json"),
    "diagnostics": Path("evidence/formal_runtime_diagnostics.v1.json"),
    "chronological": Path("evidence/chronological_evaluation_summary.v1.json"),
    "novice": Path("evidence/novice_session_summary.v1.json"),
    "capability": Path("evidence/capability_and_material_gap_summary.v1.json"),
    "comparison": Path("evidence/public_reference_comparison.v1.json"),
    "brand": Path("evidence/second_brand_real_brand_readiness.v1.json"),
    "operations": Path("evidence/operations_cost_recovery.v1.json"),
}
RESULT_PATH = Path("result/internal_pilot_release_evaluation_result.v1.json")
DELIVERY_PATH = Path("delivery/execution_review_request.v1.yaml")
REVIEW_PATHS = (
    Path("review/content_novice_experience_review.v1.json"),
    Path("review/trust_isolation_operations_review.v1.json"),
)
FORBIDDEN_PRIVATE_KEYS = {
    "answer",
    "body",
    "spoken_lines",
    "execution_payload",
    "candidate_user_visible_surfaces",
    "provider_response",
}


class CheckFailure(RuntimeError):
    """One deterministic Package 10 validation failure."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CheckFailure(code)


def read_json(root: Path, relative: Path) -> JsonObject:
    path = root / relative
    require(path.is_file(), f"E_MISSING:{relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"E_JSON_OBJECT:{relative}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_frozen_repo_bytes(repo_root: Path) -> None:
    for relative, expected in FROZEN_REPO_PATH_SHA256.items():
        path = repo_root / relative
        require(path.is_file(), f"E_FROZEN_FILE_MISSING:{relative}")
        require(sha256_file(path) == expected, f"E_FROZEN_FILE_BYTES:{relative}")


def nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            child
            for nested in value.values()
            for child in nested_keys(nested)
        }
    if isinstance(value, list):
        return {child for nested in value for child in nested_keys(nested)}
    return set()


def validate_no_private_surfaces(values: Iterable[JsonObject]) -> None:
    for value in values:
        require(
            not (nested_keys(value) & FORBIDDEN_PRIVATE_KEYS),
            "E_PRIVATE_SURFACE_COMMITTED",
        )


def validate_freeze(data: JsonObject) -> None:
    require(data.get("state") == "FROZEN_BEFORE_FORMAL_RUN", "E_FREEZE_STATE")
    implementation = data.get("implementation", {})
    require(
        implementation.get("frozen_commit") == FROZEN_COMMIT,
        "E_FREEZE_COMMIT",
    )
    remote = data.get("remote_candidate", {})
    require(remote.get("bridge_status") == "healthy", "E_FREEZE_BRIDGE")
    require(remote.get("readonly_rootfs") is True, "E_FREEZE_ROOTFS")
    require(remote.get("cap_drop") == ["ALL"], "E_FREEZE_CAPS")
    require(remote.get("dify_document_mapping_count") == 110, "E_FREEZE_DIFY")
    evaluation = data.get("evaluation", {})
    require(evaluation.get("chronological_task_count") == 30, "E_FREEZE_TASKS")
    require(evaluation.get("preflight_model_required_count") == 28, "E_FREEZE_PREFLIGHT")
    require(evaluation.get("preflight_action_card_count") == 2, "E_FREEZE_GAPS")
    budget = data.get("budget_before_formal_run", {})
    require(budget.get("historical_invocation_count") == 92, "E_FREEZE_CALLS")
    require(budget.get("historical_model_call_upper_bound") == 96, "E_FREEZE_BOUND")
    require(budget.get("bridge_absolute_model_call_limit") == 1096, "E_FREEZE_LIMIT")
    readiness = data.get("readiness", {})
    require(READINESS_KEYS <= set(readiness), "E_FREEZE_READINESS_FIELDS")
    require(all(readiness[key] is False for key in READINESS_KEYS), "E_FREEZE_READY")


def validate_transport(data: JsonObject) -> None:
    require(data.get("state") == "ABORTED_BEFORE_MODEL_DISPATCH", "E_TRANSPORT_STATE")
    require(data.get("cause") == "SECURE_COOKIE_NOT_SENT_OVER_INTERNAL_HTTP", "E_TRANSPORT_CAUSE")
    require(data.get("login_200_count") == 3, "E_TRANSPORT_LOGIN")
    require(data.get("portal_chat_400_count") == 33, "E_TRANSPORT_CHAT")
    require(data.get("new_dify_invocation_count") == 0, "E_TRANSPORT_CALL")
    require(data.get("new_candidate_count") == 0, "E_TRANSPORT_CANDIDATE")
    require(data.get("formal_content_batch_started") is False, "E_TRANSPORT_FORMAL")
    require(data.get("rerun_or_sample_replacement") is False, "E_TRANSPORT_RERUN")


def validate_formal(summary: JsonObject, diagnostics: JsonObject) -> None:
    require(summary.get("restricted_evidence_sha256") == FORMAL_EVIDENCE_SHA256, "E_FORMAL_DIGEST")
    require(summary.get("chronological_task_count") == 30, "E_FORMAL_TASKS")
    require(summary.get("model_candidate_count") == 0, "E_FORMAL_CANDIDATES")
    require(summary.get("action_card_count") == 30, "E_FORMAL_ACTIONS")
    require(summary.get("http_failure_count") == 0, "E_FORMAL_HTTP")
    require(summary.get("all_http_steps_succeeded") is True, "E_FORMAL_HTTP_STEPS")
    require(summary.get("login_session_count") == 3, "E_FORMAL_SESSIONS")
    require(summary.get("novice_step_count") == 3, "E_FORMAL_NOVICE")
    require(summary.get("full_private_bodies_committed_to_repository") is False, "E_FORMAL_PRIVATE")
    formats = summary.get("format_outcomes", {})
    require(len(formats) == 7, "E_FORMAL_FORMATS")
    require(sum(row.get("task_count", 0) for row in formats.values()) == 30, "E_FORMAL_FORMAT_TOTAL")
    require(all(row.get("model_candidate_count") == 0 for row in formats.values()), "E_FORMAL_FORMAT_CANDIDATE")
    require(diagnostics.get("formal_evidence_sha256") == FORMAL_EVIDENCE_SHA256, "E_DIAGNOSTIC_DIGEST")
    require(diagnostics.get("new_invocation_count") == 61, "E_DIAGNOSTIC_CALLS")
    require(diagnostics.get("new_model_call_upper_bound") == 61, "E_DIAGNOSTIC_BOUND")
    require(diagnostics.get("new_failed_or_unknown_billing_count") == 0, "E_DIAGNOSTIC_FAILED_CALL")
    require(diagnostics.get("formal_model_run_count") == 31, "E_DIAGNOSTIC_RUNS")
    require(diagnostics.get("formal_chat_or_inspiration_accepted_count") == 3, "E_DIAGNOSTIC_CHAT")
    require(diagnostics.get("formal_confirmed_generation_run_count") == 28, "E_DIAGNOSTIC_GENERATION")
    require(diagnostics.get("formal_parse_error_count") == 20, "E_DIAGNOSTIC_PARSE")
    require(diagnostics.get("formal_non_parse_rejected_count") == 8, "E_DIAGNOSTIC_REJECTION")
    require(diagnostics.get("formal_candidate_count") == 0, "E_DIAGNOSTIC_CANDIDATE")
    require(diagnostics.get("formal_validation_count") == 0, "E_DIAGNOSTIC_VALIDATION")
    require(diagnostics.get("formal_rerun_forbidden") is True, "E_DIAGNOSTIC_RERUN")
    require(diagnostics.get("product_gate_verdict") == "FAIL_RETURN_TO_PACKAGE7", "E_DIAGNOSTIC_VERDICT")
    indicators = diagnostics.get("non_parse_rejection_indicators", {})
    require(indicators.get("run_count") == 8, "E_DIAGNOSTIC_NONPARSE_RUNS")
    require(indicators.get("candidate_count") == 24, "E_DIAGNOSTIC_NONPARSE_CANDIDATES")
    require(indicators.get("format_match_run_count") == 8, "E_DIAGNOSTIC_FORMAT_MATCH")
    require(indicators.get("claim_binding_count") == 0, "E_DIAGNOSTIC_BINDINGS")


def validate_supporting_evidence(values: dict[str, JsonObject]) -> None:
    chronological = values["chronological"]
    require(chronological.get("task_count") == 30, "E_CHRONOLOGICAL_TASKS")
    require(chronological.get("model_candidate_count") == 0, "E_CHRONOLOGICAL_CANDIDATES")
    require(chronological.get("action_card_count") == 30, "E_CHRONOLOGICAL_ACTIONS")
    require(chronological.get("material_gap_task_ids") == ["DAY-09", "DAY-13"], "E_CHRONOLOGICAL_GAPS")
    require(len(chronological.get("product_output_rejection_task_ids", [])) == 28, "E_CHRONOLOGICAL_REJECTIONS")
    results = chronological.get("results", [])
    require(len(results) == 30, "E_CHRONOLOGICAL_ROWS")
    require(all(row.get("private_answer_committed") is False for row in results), "E_CHRONOLOGICAL_PRIVATE")
    novice = values["novice"]
    require(novice.get("content_creation_candidate_count") == 0, "E_NOVICE_CANDIDATE")
    require(novice.get("novice_chat_or_inspiration_accepted_count") == 3, "E_NOVICE_CHAT")
    require(novice.get("verdict") == "PARTIAL_INTERACTION_ONLY_CONTENT_GATE_FAILED", "E_NOVICE_VERDICT")
    capability = values["capability"]
    require(capability.get("format_with_positive_model_candidate_count") == 0, "E_CAPABILITY_FORMAT")
    require(capability.get("diyu_material_gap_task_ids") == ["DAY-09", "DAY-13"], "E_CAPABILITY_GAPS")
    require(capability.get("product_output_contract_failure_task_count") == 28, "E_CAPABILITY_REJECTIONS")
    require(capability.get("system_support_verdict") == "FORMAL_POSITIVE_PROOF_FAILED", "E_CAPABILITY_VERDICT")
    comparison = values["comparison"]
    require(comparison.get("anonymous_comparison_performed") is False, "E_COMPARISON_PERFORMED")
    require(comparison.get("competitive_quality_claim_allowed") is False, "E_COMPARISON_CLAIM")
    brand = values["brand"]
    require(brand.get("package10_second_brand_full_cycle_executed") is False, "E_BRAND_CYCLE")
    require(brand.get("reason_not_executed") == "FORMAL_PRODUCT_GATE_FAILED_BEFORE_PHASE_E", "E_BRAND_REASON")
    operations = values["operations"]
    require(operations.get("cost_limit_pass") is True, "E_OPERATIONS_COST")
    require(operations.get("call_limit_pass") is True, "E_OPERATIONS_CALLS")
    require(operations.get("current_cloud_safe") is True, "E_OPERATIONS_CLOUD")
    require(operations.get("capacity_or_recovery_claim_allowed") is False, "E_OPERATIONS_CLAIM")
    require(operations.get("package10_restart_backup_restore_rollback_executed") is False, "E_OPERATIONS_RECOVERY")


def validate_reviews(root: Path) -> list[JsonObject]:
    reviews = [read_json(root, path) for path in REVIEW_PATHS]
    identities = [review.get("reviewer_identity") for review in reviews]
    sessions = [review.get("reviewer_session") for review in reviews]
    require(all(isinstance(value, str) and value for value in identities), "E_REVIEW_IDENTITY")
    require(all(isinstance(value, str) and value for value in sessions), "E_REVIEW_SESSION")
    require(len(set(identities)) == 2 and len(set(sessions)) == 2, "E_REVIEW_INDEPENDENCE")
    for review in reviews:
        bound = review.get("bound_snapshot", {})
        require(bound.get("frozen_commit") == FROZEN_COMMIT, "E_REVIEW_COMMIT")
        require(bound.get("formal_evidence_sha256") == FORMAL_EVIDENCE_SHA256, "E_REVIEW_DIGEST")
        require(review.get("verdict") == "FAIL", "E_REVIEW_VERDICT")
        require(review.get("hard_veto") is True, "E_REVIEW_VETO")
        score = review.get("score_0_to_100")
        require(isinstance(score, int) and 0 <= score < 90, "E_REVIEW_SCORE")
        blockers = review.get("blockers")
        require(isinstance(blockers, list) and blockers, "E_REVIEW_BLOCKERS")
        require(review.get("recommended_route") == "DIYU_DIFY_END_TO_END_001", "E_REVIEW_ROUTE")
    return reviews


def validate_result(root: Path, reviews: list[JsonObject]) -> None:
    result = read_json(root, RESULT_PATH)
    require(result.get("task_id") == TASK_ID, "E_RESULT_TASK")
    require(result.get("state") == "STOPPED_RETURN_TO_PACKAGE7", "E_RESULT_STATE")
    require(result.get("execution_integrity") == "PASS_HONEST_STOP", "E_RESULT_INTEGRITY")
    require(result.get("product_gate_pass") is False, "E_RESULT_PRODUCT_GATE")
    require(result.get("formal_rerun_allowed") is False, "E_RESULT_RERUN")
    require(result.get("merge_requested") is False, "E_RESULT_MERGE")
    require(result.get("next_existing_package") == "DIYU_DIFY_END_TO_END_001", "E_RESULT_ROUTE")
    require(result.get("formal_model_candidate_count") == 0, "E_RESULT_CANDIDATES")
    require(result.get("formal_parse_error_count") == 20, "E_RESULT_PARSE")
    require(result.get("formal_non_parse_rejected_count") == 8, "E_RESULT_REJECTIONS")
    require(result.get("independent_review_count") == 2, "E_RESULT_REVIEWS")
    require(result.get("review_scores") == [review["score_0_to_100"] for review in reviews], "E_RESULT_SCORES")
    core = result.get("core_numbers", {})
    require(core == {"300": "UNCHANGED", "120": "UNCHANGED", "86": "UNCHANGED"}, "E_RESULT_CORE")
    readiness = result.get("readiness", {})
    require(READINESS_KEYS <= set(readiness), "E_RESULT_READINESS_FIELDS")
    require(all(readiness[key] is False for key in READINESS_KEYS), "E_RESULT_READY")
    require(result.get("real_customer_data_used") is False, "E_RESULT_REAL_DATA")
    require(result.get("automatic_publish_enabled") is False, "E_RESULT_PUBLISH")


def validate_delivery(root: Path) -> None:
    path = root / DELIVERY_PATH
    require(path.is_file(), f"E_MISSING:{DELIVERY_PATH}")
    text = path.read_text(encoding="utf-8")
    require("ACKNOWLEDGE_PACKAGE10_STOP_AND_AUTHORIZE_PACKAGE7_REPAIR" in text, "E_DELIVERY_DECISION")
    require("merge_requested: false" in text, "E_DELIVERY_MERGE")
    require("APPROVE_PACKAGE_10_MERGE_AND_INTERNAL_PILOT_RELEASE_DECISION" not in text, "E_DELIVERY_FALSE_APPROVAL")


def validate(root: Path = PACKAGE_ROOT, repo_root: Path | None = None) -> JsonObject:
    effective_repo_root = repo_root if repo_root is not None else root.parents[1]
    validate_frozen_repo_bytes(effective_repo_root)
    values = {name: read_json(root, path) for name, path in EVIDENCE_PATHS.items()}
    validate_no_private_surfaces(values.values())
    validate_freeze(values["freeze"])
    validate_transport(values["transport"])
    validate_formal(values["formal"], values["diagnostics"])
    validate_supporting_evidence(values)
    reviews = validate_reviews(root)
    validate_result(root, reviews)
    validate_delivery(root)
    require(not (root / "evidence/formal_full_run.private.json").exists(), "E_PRIVATE_FILE_COMMITTED")
    return {
        "state": "PASS_HONEST_STOP",
        "task_id": TASK_ID,
        "product_gate_pass": False,
        "next_existing_package": "DIYU_DIFY_END_TO_END_001",
        "formal_model_candidate_count": 0,
        "formal_parse_error_count": 20,
        "formal_non_parse_rejected_count": 8,
        "independent_review_count": 2,
    }


def expect_failure(
    root: Path,
    mutation: Callable[[], None],
    repo_root: Path | None = None,
) -> None:
    mutation()
    try:
        validate(root, repo_root)
    except CheckFailure:
        return
    raise CheckFailure("E_SELFTEST_FALSE_NEGATIVE")


def copy_selftest_repo(destination: Path) -> tuple[Path, Path]:
    repo_root = destination / "repo"
    package_root = repo_root / PACKAGE_ROOT.relative_to(REPO_ROOT)
    shutil.copytree(PACKAGE_ROOT, package_root)
    for relative in FROZEN_REPO_PATH_SHA256:
        target = repo_root / relative
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, target)
    return repo_root, package_root


def selftest() -> JsonObject:
    validate(PACKAGE_ROOT)
    tests = 0
    mutations = (
        (EVIDENCE_PATHS["formal"], lambda value: value.__setitem__("model_candidate_count", 1)),
        (EVIDENCE_PATHS["transport"], lambda value: value.__setitem__("new_dify_invocation_count", 1)),
        (EVIDENCE_PATHS["diagnostics"], lambda value: value.__setitem__("formal_parse_error_count", 19)),
        (EVIDENCE_PATHS["chronological"], lambda value: value.__setitem__("answer", "hidden")),
        (EVIDENCE_PATHS["freeze"], lambda value: value["readiness"].__setitem__("production_ready", True)),
        (RESULT_PATH, lambda value: value.__setitem__("state", "PASS_TO_RELEASE")),
        (REVIEW_PATHS[0], lambda value: value["bound_snapshot"].__setitem__("formal_evidence_sha256", "0" * 64)),
    )
    for relative, mutate in mutations:
        with tempfile.TemporaryDirectory(prefix="package10-selftest-") as temporary:
            repo_root, root = copy_selftest_repo(Path(temporary))
            value = read_json(root, relative)
            mutate(value)
            (root / relative).write_text(
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            expect_failure(root, lambda: None, repo_root)
            tests += 1
    with tempfile.TemporaryDirectory(prefix="package10-frozen-selftest-") as temporary:
        repo_root, root = copy_selftest_repo(Path(temporary))
        frozen_path = (
            repo_root
            / "20_internal_pilot/release_evaluation_001/package10_evaluation.py"
        )
        frozen_path.write_bytes(frozen_path.read_bytes() + b"\n")
        expect_failure(root, lambda: None, repo_root)
        tests += 1
    return {"state": "SELFTEST_PASS", "negative_test_count": tests}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        result = selftest() if arguments.selftest else validate()
    except (CheckFailure, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
