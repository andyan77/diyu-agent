#!/usr/bin/env python3
"""Close P3 from the single repaired run and isolated signed reviews."""

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
from p3_final import verify_historical_integrity
from p3_open_r1 import (
    AUTHOR_RECEIPT_R1_PATH,
    MACHINE_REPORT_R1_PATH,
    POSITIVE_OUTPUT_R1_PATH,
    ROUTE_COMPARISON_R1_PATH,
    check_all_r1 as check_open_r1,
)
from p3_repair import (
    ATTEMPT_0_FAILURE_COMMIT,
    AUTHOR_INSTRUCTION_R1_PATH,
    AUTHOR_MODEL_R1_PATH,
    AUTHOR_REQUEST_R1_PATH,
    DIFFERENCE_R1_PATH,
    FREEZE_MANIFEST_R1_PATH,
    GAP_R1_PATH,
    REMOVAL_R1_PATH,
    STRUCTURE_R1_PATH,
    check as check_repair,
)
from p3_review_r1 import (
    ADJUDICATION_R1_PATH,
    BLIND_PACKET_R1_PATH,
    REVIEW_ONE_R1_PATH,
    REVIEW_TWO_R1_PATH,
    load_and_validate_reports,
    substantive_disagreements,
)


RESULT_R1_PATH = TASK_ROOT / "result/p3_open_probe40_result.v0.2.yaml"
HANDOFF_R1_PATH = TASK_ROOT / "result/p4_sealed_probe_handoff.v0.2.yaml"
DELIVERY_RECEIPT_R1_PATH = TASK_ROOT / "result/p3_delivery_receipt.v0.2.yaml"
RUNNER_R1_PATH = TASK_ROOT / "run_p3_open_probe_r1.py"
P2_OWNER_DIGEST = "ac4fe6c1ccdf8af787eb51d04f085883c27660690ccee6dfb996a90d89d4f7a7"
REPAIR_FREEZE_COMMIT = "817d35105be95f027465951e524496728f9bcaa5"


def _review_metrics(root: Path) -> dict[str, Any]:
    one, two = load_and_validate_reports(root)
    disagreements = substantive_disagreements(one, two)
    adjudication: dict[str, Any] | None = None
    if disagreements:
        require((root / ADJUDICATION_R1_PATH).is_file(), "E_P3_R1_ADJUDICATION_REQUIRED")
        adjudication = json.loads((root / ADJUDICATION_R1_PATH).read_text(encoding="utf-8"))
        require(adjudication.get("schema_version") == "gate1-p3-targeted-adjudication-v0.2", "E_P3_R1_ADJUDICATION_SCHEMA")
        require(adjudication.get("task_id") == TASK_ID, "E_P3_R1_ADJUDICATION_TASK")
        require(adjudication.get("targeted_items") == disagreements, "E_P3_R1_ADJUDICATION_SCOPE")
        require(adjudication.get("full_batch_rereviewed") is False, "E_P3_R1_ADJUDICATION_FULL_BATCH")
        excluded = {
            one["reviewer_identity"],
            two["reviewer_identity"],
            one["reviewer_platform_agent_id"],
            two["reviewer_platform_agent_id"],
            AUTHORIZED_AUTHOR_IDENTITY,
        }
        require(adjudication.get("adjudicator_identity") not in excluded, "E_P3_R1_ADJUDICATOR_COLLISION")
        require(adjudication.get("adjudicator_platform_agent_id") not in excluded, "E_P3_R1_ADJUDICATOR_COLLISION")
        require(adjudication.get("all_substantive_disagreements_closed") is True, "E_P3_R1_ADJUDICATION_OPEN")
        require(adjudication.get("adjudication_digest") == object_digest(adjudication, "adjudication_digest"), "E_P3_R1_ADJUDICATION_DIGEST")
    return {
        "one": one,
        "two": two,
        "disagreements": disagreements,
        "adjudication": adjudication,
        "all_disagreements_closed": not disagreements or adjudication is not None,
        "both_pass": one["overall_verdict"] == two["overall_verdict"] == "PASS",
    }


def build_final_documents(root: Path = ROOT) -> dict[Path, bytes]:
    check_repair(root)
    check_open_r1(root)
    historical = verify_historical_integrity(root)
    reviews = _review_metrics(root)
    one = reviews["one"]
    two = reviews["two"]
    machine = load_yaml(root / MACHINE_REPORT_R1_PATH)["machine_acceptance_report"]
    outputs = load_jsonl(root / POSITIVE_OUTPUT_R1_PATH)
    comparisons = load_jsonl(root / ROUTE_COMPARISON_R1_PATH)
    route_pass = len(comparisons) == 20 and all(
        row["primary_action_matches_gold"]
        and row["primary_reason_matches_gold"]
        and not row["audience_content_created"]
        for row in comparisons
    )
    structure_pass = (
        len(load_jsonl(root / STRUCTURE_R1_PATH)) == 80
        and len(load_jsonl(root / DIFFERENCE_R1_PATH)) == 80
        and len(load_jsonl(root / REMOVAL_R1_PATH)) == 480
        and load_yaml(root / GAP_R1_PATH)["p3_structure_gap_assessment"]["conclusion"]
        == "NO_ACTUAL_COMPONENT_SUPPLY_GAP_AFTER_P3_INPUT_ALIGNMENT"
    )
    exit_audit = machine["exit_audit"]
    boundary_pass = all(
        exit_audit[key] == 0
        for key in (
            "external_provider_request_count",
            "external_api_call_count",
            "credential_read_count",
            "network_dispatch_count",
        )
    )
    pass_state = bool(
        structure_pass
        and route_pass
        and reviews["both_pass"]
        and reviews["all_disagreements_closed"]
        and machine["exact_duplicate_pair_count"] == 0
        and boundary_pass
    )
    result_state = "PASS_TO_P4_SEALED_HIDDEN_PROBE" if pass_state else "STOPPED_OPEN_QUALIFICATION_FAILED"
    hard_ids = sorted(set(one["hard_error_profile_ids"]).union(two["hard_error_profile_ids"]))
    result: dict[str, Any] = {
        "schema_version": "gate1-p3-open-result-v0.2",
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
        "attempt_0_failure_commit": ATTEMPT_0_FAILURE_COMMIT,
        "repair_freeze_commit": REPAIR_FREEZE_COMMIT,
        "attempt_0_failure_evidence_preserved": True,
        "final_structure_record_count": len(load_jsonl(root / STRUCTURE_R1_PATH)),
        "targeted_component_window_used": False,
        "component_addition_count": 0,
        "open_core_repair_window_used": True,
        "open_core_repair_window_remaining": 0,
        "open_probe_full_run_count": 2,
        "positive_first_output_count": len(outputs),
        "positive_first_output_profile_count": len({row["profile_id"] for row in outputs}),
        "route_case_count": len(comparisons),
        "route_action_match_count": sum(row["primary_action_matches_gold"] for row in comparisons),
        "route_reason_match_count": sum(row["primary_reason_matches_gold"] for row in comparisons),
        "route_audience_content_count": sum(row["audience_content_created"] for row in comparisons),
        "review_one_score": one["p3_score"],
        "review_two_score": two["p3_score"],
        "review_one_first_acceptance_rate": one["first_acceptance_rate"],
        "review_two_first_acceptance_rate": two["first_acceptance_rate"],
        "review_one_blind_top1_accuracy": one["blind_top1_accuracy"],
        "review_two_blind_top1_accuracy": two["blind_top1_accuracy"],
        "substantive_disagreement_count": len(reviews["disagreements"]),
        "adjudication_used": reviews["adjudication"] is not None,
        "all_substantive_disagreements_closed": reviews["all_disagreements_closed"],
        "human_formula_profile_ids_union": sorted(
            set(one["human_confirmed_formula_or_near_duplicate_profile_ids"]).union(
                two["human_confirmed_formula_or_near_duplicate_profile_ids"]
            )
        ),
        "hard_error_profile_ids": hard_ids,
        "machine_exact_duplicate_pair_count": machine["exact_duplicate_pair_count"],
        "machine_similarity_is_not_human_verdict": True,
        "external_exit_audit": exit_audit,
        "historical_integrity": historical,
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
        "schema_version": "gate1-p3-to-p4-handoff-v0.2",
        "task_id": TASK_ID,
        "handoff_state": "P4_BRIEF_MAY_BE_DRAFTED_NOT_EXECUTED" if pass_state else "P4_NOT_ALLOWED",
        "p4_allowed": pass_state,
        "p4_execution_authorized": False,
        "p4_hidden_material_created_or_accessed": False,
        "p3_result_path": RESULT_R1_PATH.as_posix(),
        "p3_result_digest": result["result_digest"],
        "frozen_generator_core": {
            "p2_core_path": (TASK_ROOT.parent / "p2_component_supply_and_generator_core_repair_001/p2_generator_core_r6.py").as_posix(),
            "p2_core_sha256": "e15eab89cef2cb9b2a35d76ca3550b67f2c49c583fc9efe107ebaf062f527015",
            "p3_author_instruction_path": AUTHOR_INSTRUCTION_R1_PATH.as_posix(),
            "p3_author_instruction_sha256": sha256_file(root / AUTHOR_INSTRUCTION_R1_PATH),
            "p3_author_model_path": AUTHOR_MODEL_R1_PATH.as_posix(),
            "p3_author_model_sha256": sha256_file(root / AUTHOR_MODEL_R1_PATH),
            "p3_author_request_path": AUTHOR_REQUEST_R1_PATH.as_posix(),
            "p3_author_request_sha256": sha256_file(root / AUTHOR_REQUEST_R1_PATH),
            "repair_freeze_path": FREEZE_MANIFEST_R1_PATH.as_posix(),
            "repair_freeze_sha256": sha256_file(root / FREEZE_MANIFEST_R1_PATH),
        },
        "open_outputs_are_development_evidence_only": True,
        "counts_toward_300": 0,
        "generator_qualified": False,
        "readiness": readiness_false(),
    }
    handoff["handoff_digest"] = object_digest(handoff, "handoff_digest")
    receipt: dict[str, Any] = {
        "schema_version": "gate1-p3-delivery-receipt-v0.2",
        "task_id": TASK_ID,
        "repository_before": BASELINE_COMMIT,
        "attempt_0_failure_commit": ATTEMPT_0_FAILURE_COMMIT,
        "repair_freeze_commit": REPAIR_FREEZE_COMMIT,
        "repository_after": "RECORDED_IN_GIT_COMMIT_AND_DELIVERY_RESPONSE",
        "branch": "agent/gate1-v1-1-retrospective-recovery-plan",
        "merge_request_14_must_remain_draft": True,
        "p1a_p1b_p2_historical_integrity": historical,
        "structure_attempt_0_preserved": True,
        "single_repair_window_used": True,
        "second_repair_window_opened": False,
        "targeted_component_window_used": False,
        "final_structure_80_result": structure_pass,
        "positive_20_first_output_result": reviews["both_pass"],
        "route_20_action_and_reason_result": route_pass,
        "blind_product_identification_result": {
            "review_one": one["blind_top1_accuracy"],
            "review_two": two["blind_top1_accuracy"],
        },
        "independent_review_reports": [
            {"path": REVIEW_ONE_R1_PATH.as_posix(), "score": one["p3_score"], "verdict": one["overall_verdict"]},
            {"path": REVIEW_TWO_R1_PATH.as_posix(), "score": two["p3_score"], "verdict": two["overall_verdict"]},
        ],
        "blind_packet_path": BLIND_PACKET_R1_PATH.as_posix(),
        "author_run_receipt_path": AUTHOR_RECEIPT_R1_PATH.as_posix(),
        "result_state": result_state,
        "p4_allowed": pass_state,
        "p4_hidden_material_access_count": 0,
        "counts_toward_300": 0,
        "core_number_impact": result["core_number_impact"],
        "readiness_all_remain_false": True,
    }
    receipt["receipt_digest"] = object_digest(receipt, "receipt_digest")
    documents: dict[Path, bytes] = {
        RESULT_R1_PATH: yaml_bytes({"p3_open_probe40_result": result}),
        HANDOFF_R1_PATH: yaml_bytes({"p4_sealed_probe_handoff": handoff}),
        DELIVERY_RECEIPT_R1_PATH: yaml_bytes({"p3_delivery_receipt": receipt}),
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
                "entrypoint": RUNNER_R1_PATH.as_posix(),
                "author_instruction": AUTHOR_INSTRUCTION_R1_PATH.as_posix(),
                "author_model_config": AUTHOR_MODEL_R1_PATH.as_posix(),
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
            "core_numbers": result["core_number_impact"],
            "readiness": readiness_false(),
        }
        owner["owner_digest"] = object_digest(owner, "owner_digest")
        documents[CURRENT_OWNER_PATH] = yaml_bytes({"current_gate1_owner": owner})
    return documents


def materialize_final(root: Path = ROOT) -> list[Path]:
    changed: list[Path] = []
    for relative, payload in build_final_documents(root).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
            changed.append(path)
    return changed


def check_final(root: Path = ROOT) -> None:
    for relative, payload in build_final_documents(root).items():
        require((root / relative).is_file(), "E_P3_R1_FINAL_MISSING", relative.as_posix())
        require((root / relative).read_bytes() == payload, "E_P3_R1_FINAL_DRIFT", relative.as_posix())
