#!/usr/bin/env python3
"""Close P3 from frozen evidence and isolated signed reviews."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from p3_common import (
    AUTHORIZED_AUTHOR_IDENTITY,
    BASELINE_COMMIT,
    CURRENT_CHECKER_PATH,
    CURRENT_OWNER_PATH,
    P2_RESULT_PATH,
    ROOT,
    TASK_ID,
    TASK_ROOT,
    load_jsonl,
    load_yaml,
    object_digest,
    readiness_false,
    require,
    sha256_file,
    yaml_bytes,
)
from p3_open_core import (
    AUTHOR_RUN_RECEIPT_PATH,
    MACHINE_REPORT_PATH,
    ROUTE_ACTUAL_PATH,
    ROUTE_COMPARISON_PATH,
    build_machine_report,
    build_route_actuals,
    build_route_comparisons,
    validate_positive_file,
)
from p3_prepare import (
    AUTHOR_INSTRUCTION_PATH,
    AUTHOR_MODEL_PATH,
    AUTHOR_REQUEST_PATH,
    HISTORICAL_MANIFEST_PATH,
    check_prepare,
)
from p3_review import (
    ADJUDICATION_PATH,
    REVIEW_ONE_PATH,
    REVIEW_TWO_PATH,
    load_and_validate_reports,
    substantive_disagreements,
)
from p3_structure import (
    DIFFERENCE_PATH,
    GAP_PATH,
    REMOVAL_PATH,
    STRUCTURE_PATH,
    check_structure,
)


RESULT_PATH = TASK_ROOT / "result/p3_open_probe40_result.v0.1.yaml"
HANDOFF_PATH = TASK_ROOT / "result/p4_sealed_probe_handoff.v0.1.yaml"
DELIVERY_RECEIPT_PATH = TASK_ROOT / "result/p3_delivery_receipt.v0.1.yaml"
COMPAT_RECEIPT_PATH = TASK_ROOT / "compatibility/p2_historical_compatibility_receipt.v0.1.yaml"

P2_OWNER_DIGEST = "ac4fe6c1ccdf8af787eb51d04f085883c27660690ccee6dfb996a90d89d4f7a7"
FREEZE_COMMIT = "bb598b0"


def verify_historical_integrity(root: Path = ROOT) -> dict[str, Any]:
    rows = load_jsonl(root / HISTORICAL_MANIFEST_PATH)
    changed: list[dict[str, str]] = []
    for row in rows:
        path = root / str(row["path"])
        require(path.is_file(), "E_P3_HISTORICAL_FILE_MISSING", str(row["path"]))
        actual = sha256_file(path)
        if actual != row["sha256_at_p3_baseline"]:
            changed.append(
                {
                    "path": str(row["path"]),
                    "before": str(row["sha256_at_p3_baseline"]),
                    "after": actual,
                    "protection": str(row["protection"]),
                }
            )
    unauthorized = [
        row
        for row in changed
        if row["protection"] != "CONDITIONALLY_MUTABLE_COMPATIBILITY_PIN_ONLY"
    ]
    require(not unauthorized, "E_P3_HISTORICAL_MUTATION", json.dumps(unauthorized, ensure_ascii=False))
    if changed:
        require(len(changed) == 1, "E_P3_COMPATIBILITY_MUTATION_COUNT")
        receipt = load_yaml(root / COMPAT_RECEIPT_PATH).get("p2_historical_compatibility_receipt")
        require(isinstance(receipt, dict), "E_P3_COMPATIBILITY_RECEIPT")
        mutation = changed[0]
        require(
            receipt.get("path") == mutation["path"]
            and receipt.get("sha256_before") == mutation["before"]
            and receipt.get("sha256_after") == mutation["after"]
            and receipt.get("p2_generated_output_mutation_count") == 0
            and receipt.get("accepts_arbitrary_future_owner") is False
            and receipt.get("p2_historical_tamper_detection_retained") is True,
            "E_P3_COMPATIBILITY_RECEIPT_FIELDS",
        )
        require(receipt.get("receipt_digest") == object_digest(receipt, "receipt_digest"), "E_P3_COMPATIBILITY_RECEIPT_DIGEST")
    return {
        "manifest_record_count": len(rows),
        "unauthorized_mutation_count": len(unauthorized),
        "authorized_compatibility_mutation_count": len(changed),
        "authorized_compatibility_mutations": changed,
    }


def _resolved_review_metrics(root: Path) -> dict[str, Any]:
    review_one, review_two = load_and_validate_reports(root)
    disagreements = substantive_disagreements(review_one, review_two)
    adjudication = None
    if disagreements:
        require((root / ADJUDICATION_PATH).is_file(), "E_P3_ADJUDICATION_REQUIRED")
        adjudication = json.loads((root / ADJUDICATION_PATH).read_text(encoding="utf-8"))
        require(adjudication.get("task_id") == TASK_ID, "E_P3_ADJUDICATION_TASK")
        require(adjudication.get("targeted_items") == disagreements, "E_P3_ADJUDICATION_SCOPE")
        require(adjudication.get("full_batch_rereviewed") is False, "E_P3_ADJUDICATION_FULL_RERUN")
        require(adjudication.get("adjudicator_identity") not in {review_one["reviewer_identity"], review_two["reviewer_identity"], AUTHORIZED_AUTHOR_IDENTITY}, "E_P3_ADJUDICATOR_COLLISION")
        require(adjudication.get("adjudication_digest") == object_digest(adjudication, "adjudication_digest"), "E_P3_ADJUDICATION_DIGEST")
        require(adjudication.get("all_substantive_disagreements_closed") is True, "E_P3_ADJUDICATION_OPEN")
    both_pass = review_one["overall_verdict"] == review_two["overall_verdict"] == "PASS"
    return {
        "review_one": review_one,
        "review_two": review_two,
        "substantive_disagreements": disagreements,
        "adjudication": adjudication,
        "both_pass": both_pass,
    }


def build_final_documents(root: Path = ROOT) -> dict[Path, bytes]:
    check_structure(root)
    check_prepare(root, include_current_pointer=False)
    historical = verify_historical_integrity(root)
    outputs = validate_positive_file(root)
    expected_actuals = build_route_actuals(root)
    actuals = load_jsonl(root / ROUTE_ACTUAL_PATH)
    require(actuals == expected_actuals, "E_P3_ROUTE_ACTUAL_DRIFT")
    expected_comparisons = build_route_comparisons(root)
    comparisons = load_jsonl(root / ROUTE_COMPARISON_PATH)
    require(comparisons == expected_comparisons, "E_P3_ROUTE_COMPARISON_DRIFT")
    machine = build_machine_report(root)
    stored_machine = load_yaml(root / MACHINE_REPORT_PATH).get("machine_acceptance_report")
    require(stored_machine == machine, "E_P3_MACHINE_REPORT_DRIFT")
    reviews = _resolved_review_metrics(root)
    review_one = reviews["review_one"]
    review_two = reviews["review_two"]
    route_pass = all(
        row["primary_action_matches_gold"]
        and row["primary_reason_matches_gold"]
        and not row["audience_content_created"]
        for row in comparisons
    )
    structure_pass = (
        len(load_jsonl(root / STRUCTURE_PATH)) == 80
        and len(load_jsonl(root / DIFFERENCE_PATH)) == 80
        and len(load_jsonl(root / REMOVAL_PATH)) == 480
        and load_yaml(root / GAP_PATH).get("conclusion") == "NO_ACTUAL_COMPONENT_SUPPLY_GAP"
    )
    pass_state = bool(
        structure_pass
        and route_pass
        and reviews["both_pass"]
        and not reviews["substantive_disagreements"]
        and machine["exact_duplicate_pair_count"] == 0
        and machine["exit_audit"]["external_provider_request_count"] == 0
        and machine["exit_audit"]["external_api_call_count"] == 0
        and machine["exit_audit"]["credential_read_count"] == 0
    )
    result_state = (
        "PASS_TO_P4_SEALED_HIDDEN_PROBE"
        if pass_state
        else "STOPPED_OPEN_QUALIFICATION_FAILED"
    )
    result: dict[str, Any] = {
        "schema_version": "gate1-p3-open-result-v0.1",
        "task_id": TASK_ID,
        "prompt_revision": "r0",
        "result_state": result_state,
        "p3_complete": pass_state,
        "p4_allowed": pass_state,
        "generator_qualified": False,
        "generation_allowed": False,
        "runtime_ingest_ready": False,
        "production_ready": False,
        "counts_toward_300": 0,
        "baseline_commit": BASELINE_COMMIT,
        "freeze_commit": FREEZE_COMMIT,
        "structure_attempt_0_preserved": True,
        "final_structure_record_count": len(load_jsonl(root / STRUCTURE_PATH)),
        "targeted_component_window_used": False,
        "component_addition_count": 0,
        "positive_first_output_count": len(outputs),
        "positive_first_output_profile_count": len({row["profile_id"] for row in outputs}),
        "route_case_count": len(comparisons),
        "route_action_match_count": sum(row["primary_action_matches_gold"] for row in comparisons),
        "route_reason_match_count": sum(row["primary_reason_matches_gold"] for row in comparisons),
        "route_audience_content_count": sum(row["audience_content_created"] for row in comparisons),
        "review_one_score": review_one["p3_score"],
        "review_two_score": review_two["p3_score"],
        "review_one_first_acceptance_rate": review_one["first_acceptance_rate"],
        "review_two_first_acceptance_rate": review_two["first_acceptance_rate"],
        "review_one_blind_top1_accuracy": review_one["blind_top1_accuracy"],
        "review_two_blind_top1_accuracy": review_two["blind_top1_accuracy"],
        "substantive_disagreement_count": len(reviews["substantive_disagreements"]),
        "adjudication_used": reviews["adjudication"] is not None,
        "machine_exact_duplicate_pair_count": machine["exact_duplicate_pair_count"],
        "machine_similarity_review_queue_count": machine["machine_similarity_review_queue_count"],
        "hard_error_profile_ids": sorted(
            set(review_one["hard_error_profile_ids"]).union(review_two["hard_error_profile_ids"])
        ),
        "external_exit_audit": machine["exit_audit"],
        "historical_integrity": historical,
        "open_core_repair_window_used": False,
        "open_probe_rerun_count": 0,
        "p4_hidden_material_access_count": 0,
        "core_number_impact": {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "readiness": readiness_false(),
    }
    result["result_digest"] = object_digest(result, "result_digest")
    handoff: dict[str, Any] = {
        "schema_version": "gate1-p3-to-p4-handoff-v0.1",
        "task_id": TASK_ID,
        "handoff_state": "P4_BRIEF_MAY_BE_DRAFTED_NOT_EXECUTED" if pass_state else "P4_NOT_ALLOWED",
        "p4_allowed": pass_state,
        "p4_execution_authorized": False,
        "p3_result_path": RESULT_PATH.as_posix(),
        "p3_result_digest": result["result_digest"],
        "frozen_generator_core": {
            "p2_core_path": (TASK_ROOT.parent / "p2_component_supply_and_generator_core_repair_001/p2_generator_core_r6.py").as_posix(),
            "p2_core_sha256": "e15eab89cef2cb9b2a35d76ca3550b67f2c49c583fc9efe107ebaf062f527015",
            "p3_author_instruction_path": AUTHOR_INSTRUCTION_PATH.as_posix(),
            "p3_author_instruction_sha256": sha256_file(root / AUTHOR_INSTRUCTION_PATH),
            "p3_author_model_path": AUTHOR_MODEL_PATH.as_posix(),
            "p3_author_request_path": AUTHOR_REQUEST_PATH.as_posix(),
        },
        "current_positive_outputs_are_open_development_evidence_only": True,
        "counts_toward_300": 0,
        "generator_qualified": False,
        "readiness": readiness_false(),
    }
    handoff["handoff_digest"] = object_digest(handoff, "handoff_digest")
    receipt: dict[str, Any] = {
        "schema_version": "gate1-p3-delivery-receipt-v0.1",
        "task_id": TASK_ID,
        "repository_before": BASELINE_COMMIT,
        "freeze_commit": FREEZE_COMMIT,
        "repository_after": "RECORDED_IN_GIT_COMMIT_AND_DELIVERY_RESPONSE",
        "branch": "agent/gate1-v1-1-retrospective-recovery-plan",
        "merge_request_14_must_remain_draft": True,
        "p1a_p1b_p2_historical_integrity": historical,
        "p2_compatibility_pin_used": historical["authorized_compatibility_mutation_count"] == 1,
        "structure_attempt_0_preserved": True,
        "targeted_component_window_used": False,
        "final_structure_80_result": structure_pass,
        "positive_20_first_output_result": reviews["both_pass"],
        "route_20_action_and_reason_result": route_pass,
        "independent_review_reports": [
            {"path": REVIEW_ONE_PATH.as_posix(), "score": review_one["p3_score"], "verdict": review_one["overall_verdict"]},
            {"path": REVIEW_TWO_PATH.as_posix(), "score": review_two["p3_score"], "verdict": review_two["overall_verdict"]},
        ],
        "author_run_receipt_path": AUTHOR_RUN_RECEIPT_PATH.as_posix(),
        "result_state": result_state,
        "p4_allowed": pass_state,
        "counts_toward_300": 0,
        "core_number_impact": result["core_number_impact"],
        "readiness_all_remain_false": True,
    }
    receipt["receipt_digest"] = object_digest(receipt, "receipt_digest")
    documents: dict[Path, bytes] = {
        RESULT_PATH: yaml_bytes({"p3_open_probe40_result": result}),
        HANDOFF_PATH: yaml_bytes({"p4_sealed_probe_handoff": handoff}),
        DELIVERY_RECEIPT_PATH: yaml_bytes({"p3_delivery_receipt": receipt}),
    }
    if pass_state:
        owner: dict[str, Any] = {
            "schema_version": "v0.1",
            "owner_id": "GATE1_V11_P3_OPEN_PROBE_FINAL_OWNER",
            "task_id": TASK_ID,
            "current_task_root": TASK_ROOT.as_posix(),
            "current_checker": CURRENT_CHECKER_PATH.as_posix(),
            "result_state": result_state,
            "p3_complete": True,
            "p4_allowed": True,
            "current_generator": {
                "entrypoint": (TASK_ROOT / "run_p3_open_probe.py").as_posix(),
                "author_instruction": AUTHOR_INSTRUCTION_PATH.as_posix(),
                "author_model_config": AUTHOR_MODEL_PATH.as_posix(),
                "active_component_count": 68,
                "active_edge_count": 85,
                "active_control_rule_count": 8,
                "p3_component_addition_count": 0,
                "historical_generator_entrypoints_consumed": [],
            },
            "predecessor": {
                "owner_id": "GATE1_V11_P2_FINAL_OWNER",
                "owner_digest": P2_OWNER_DIGEST,
                "p2_result_path": P2_RESULT_PATH.as_posix(),
                "p2_result_sha256": sha256_file(root / P2_RESULT_PATH),
            },
            "core_numbers": {
                "target_total": 300,
                "reference_inventory": 120,
                "historical_component_inventory": 86,
                "all_unchanged": True,
            },
            "readiness": readiness_false(),
        }
        owner["owner_digest"] = object_digest(owner, "owner_digest")
        documents[CURRENT_OWNER_PATH] = yaml_bytes({"current_gate1_owner": owner})
    return documents


def materialize_final(root: Path = ROOT) -> list[Path]:
    documents = build_final_documents(root)
    changed: list[Path] = []
    for relative, payload in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
            changed.append(path)
    return changed


def check_final(root: Path = ROOT) -> None:
    documents = build_final_documents(root)
    for relative, expected in documents.items():
        path = root / relative
        require(path.is_file(), "E_P3_FINAL_FILE_MISSING", relative.as_posix())
        require(path.read_bytes() == expected, "E_P3_FINAL_FILE_DRIFT", relative.as_posix())


__all__ = [
    "COMPAT_RECEIPT_PATH",
    "DELIVERY_RECEIPT_PATH",
    "HANDOFF_PATH",
    "RESULT_PATH",
    "build_final_documents",
    "check_final",
    "materialize_final",
    "verify_historical_integrity",
]
