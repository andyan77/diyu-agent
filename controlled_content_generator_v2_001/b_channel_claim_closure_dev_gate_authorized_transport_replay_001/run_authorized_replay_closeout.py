#!/usr/bin/env python3
"""Freeze and verify the authorized replay development-gate outcome."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


if not __debug__:
    print("authorized replay closeout refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_DIR = Path(__file__).resolve().parent
TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_CLAIM_CLOSURE_DEV_GATE_AUTHORIZED_TRANSPORT_REPLAY_001"
MACHINE_PATH = TASK_DIR / "machine/development_machine_result.v0.1.json"
PERSISTENCE_PATH = TASK_DIR / "replay/persisted_batch/atomic_persistence_receipt.v0.1.json"
T0_PATH = TASK_DIR / "t0/transport_t0_result.v0.1.json"
FREEZE_PATH = TASK_DIR / "freeze/transport_freeze_manifest.v0.1.json"
REVIEW_FAILURE_PATH = TASK_DIR / "review/review_execution_failure.v0.1.json"
CANDIDATE_PATH = TASK_DIR / "generator/development_candidates.v0.1.jsonl"
VALIDATION_PATH = TASK_DIR / "claim_closure/candidate_validation_results.v0.1.jsonl"
PAIR_PATH = TASK_DIR / "machine/pair_surface_independence_audits.v0.1.jsonl"
RESULT_PATH = TASK_DIR / "result/development_gate_result.v0.1.json"
GUARDIAN_PATH = TASK_DIR / "guardian/guardian_review_packet.v0.1.json"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected object in {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if any(not isinstance(row, dict) for row in rows):
        raise TypeError(f"expected object rows in {path}")
    return rows


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, got {actual!r}")


def _verify_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    machine = load_json(MACHINE_PATH)
    persistence = load_json(PERSISTENCE_PATH)
    review_failure = load_json(REVIEW_FAILURE_PATH)
    t0 = load_json(T0_PATH)
    freeze = load_json(FREEZE_PATH)
    candidates = load_jsonl(CANDIDATE_PATH)
    validations = load_jsonl(VALIDATION_PATH)
    pairs = load_jsonl(PAIR_PATH)

    _require_equal(machine.get("machine_result_digest"), object_digest(machine, "machine_result_digest"), "machine digest")
    _require_equal(
        persistence.get("persistence_receipt_digest"),
        object_digest(persistence, "persistence_receipt_digest"),
        "persistence digest",
    )
    _require_equal(
        review_failure.get("failure_digest"),
        object_digest(review_failure, "failure_digest"),
        "review failure digest",
    )
    _require_equal(t0.get("t0_result_digest"), object_digest(t0, "t0_result_digest"), "T0 digest")
    _require_equal(freeze.get("freeze_manifest_digest"), object_digest(freeze, "freeze_manifest_digest"), "freeze digest")

    expected_counts = {
        "physical_author_invocation_total": 80,
        "content_evaluable_attempt_count": 40,
        "persisted_raw_response_count": 40,
        "content_reroll_count": 0,
        "replacement_count": 0,
        "selective_retry_count": 0,
        "hidden_count": 0,
        "accepted_baseline_count": 120,
        "generator_qualified": False,
    }
    for key, expected in expected_counts.items():
        _require_equal(persistence.get(key), expected, f"persistence {key}")
    _require_equal(persistence.get("third_attempt_allowed"), False, "third attempt")
    _require_equal(persistence.get("atomic_batch_persistence"), True, "atomic persistence")
    _require_equal(len(candidates), 40, "candidate count")
    _require_equal(len(validations), 40, "validation count")
    _require_equal(len(pairs), 20, "pair count")
    _require_equal(len({row.get("candidate_id") for row in candidates}), 40, "candidate identity count")
    _require_equal(
        review_failure.get("status"),
        "INDEPENDENT_REVIEW_EXECUTION_FAILED",
        "review execution status",
    )
    if (TASK_DIR / "review/persisted_reviews").exists():
        raise ValueError("partial or late review outputs may not coexist with the failure receipt")

    for group in ("prior_frozen_file_digests", "transport_core_file_digests"):
        for relative, expected in freeze[group].items():
            _require_equal(sha256_file(TASK_DIR.parents[1] / relative), expected, f"frozen {relative}")
    for relative, expected in freeze["generated_file_digests"].items():
        _require_equal(sha256_file(TASK_DIR / relative), expected, f"checkpoint {relative}")
    return machine, persistence, review_failure


def _build_result(
    machine: Mapping[str, Any],
    persistence: Mapping[str, Any],
    review_failure: Mapping[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "verdict": "STOPPED_BEFORE_HIDDEN",
        "task_status": "STOPPED_BEFORE_HIDDEN_CONTENT_GATE_FAILED",
        "dev_gate_pass": False,
        "dev_gate_pass_candidate": False,
        "blocking_items": [
            "INDEPENDENT_REVIEW_EXECUTION_FAILED",
            "INVENTED_ACTION",
            "INVENTED_CAUSALITY",
            "INVENTED_NUMBER",
            "AUTHORIAL_EXACT_LINE_OVERLAP",
        ],
        "phase_0": {
            "pr_12_reviewed_head_sha": "e0f004e403a1947691178d42c0a33e32f0ecd767",
            "pr_12_merge_commit_sha": "f5e458730aca52e63748f597e007352b72d7bb63",
            "expected_parents_pass": True,
            "tree_identity_pass": True,
            "master_ci_green": True,
            "branch_protection_unchanged": True,
        },
        "prior_failure": {
            "initial_author_invocation_count": 40,
            "initial_transport_valid_response_count": 0,
            "initial_persisted_raw_response_count": 0,
            "initial_candidate_count": 0,
            "initial_semantic_review_count": 0,
        },
        "transport_fix": {
            "root_cause": "AUTHOR_PAYLOAD_ECHO_USED_AS_AUTHORITATIVE_TRANSPORT_IDENTITY",
            "identity_authority": "DISPATCHER",
            "old_transport_digest": "623b5f27a496cda360110acec5a66a9183a205fa3007aae8db278fb3f5b2846b",
            "new_transport_digest": "0dc7a007dd563f5b2e17a61e3de5b4e503e0b9611e5a23ebc65c2fd5515c08c8",
            "semantic_author_instruction_unchanged": True,
            "material_plan_source_unchanged": True,
            "T0_positive_pass": True,
            "T0_negative_pass": True,
        },
        "authorized_replay": {
            "batch_replay_count": 1,
            "request_replay_count": 40,
            "physical_author_invocation_total": persistence["physical_author_invocation_total"],
            "content_evaluable_attempt_count": persistence["content_evaluable_attempt_count"],
            "content_reroll_count": 0,
            "replacement_count": 0,
            "selective_retry_count": 0,
            "third_attempt_allowed": False,
            "persisted_raw_response_count": persistence["persisted_raw_response_count"],
            "candidate_materialization_attempt_count": machine["candidate_materialization_attempt_count"],
            "candidate_count": machine["candidate_count"],
            "candidate_schema_failure_count": machine["candidate_schema_failure_count"],
        },
        "structural_regression": {
            "registry_total_count": 86,
            "accepted_new_component_loaded_count": 22,
            "component_conformance_positive_pass_count": 22,
            "component_ineligible_negative_pass_count": 22,
            "component_binding_removal_fail_closed_count": 22,
            "orch_plan_count": 40,
            "identical_fact_set_pair_count": 20,
            "at_least_four_real_plan_axis_pair_count": 20,
            "route_case_count": 60,
            "route_recomputation_mismatch_count": 0,
            "fake_degrade_count": 0,
        },
        "claim_closure": {
            "reviewed_surface_unit_count": machine["reviewed_surface_unit_count"],
            "undeclared_assertion_count": machine["undeclared_assertion_count"],
            "unsupported_fact_count": machine["unsupported_fact_count"],
            "invented_number_count": machine["invented_number_count"],
            "invented_action_count": machine["invented_action_count"],
            "invented_causality_count": machine["invented_causality_count"],
            "invented_result_count": machine["invented_result_count"],
            "invented_entity_count": machine["invented_entity_count"],
            "invalid_source_span_count": machine["invalid_source_span_count"],
            "post_author_source_change_count": machine["post_author_source_change_count"],
            "component_as_fact_source_count": machine["component_as_fact_source_count"],
            "machine_final_semantic_claim": False,
            "machine_final_quality_claim": False,
        },
        "independent_review": {
            "execution_status": review_failure["status"],
            "error_code": review_failure["error_code"],
            "completed_primary_candidate_review_count": 0,
            "completed_fact_candidate_review_count": 0,
            "completed_pair_review_count": 0,
            "quality_evaluation_completed": False,
            "candidate_edit_count": 0,
            "content_reroll_count": 0,
        },
        "development_gate": {
            "first_acceptance_total": None,
            "first_acceptance_A": None,
            "first_acceptance_B": None,
            "fully_accepted_pair_count": None,
            "cp_with_zero_acceptable_output_count": None,
            "semantically_independent_pair_count": None,
            "pair_with_at_least_four_real_axes_count": machine["pair_with_at_least_four_real_axes_count"],
            "authorial_exact_line_overlap_pair_count": machine["authorial_exact_line_overlap_pair_count"],
            "cross_lane_fact_leak_count": machine["cross_lane_fact_leak_count"],
            "structural_failure_count": 1,
            "unresolved_formulaic_finding_count": None,
            "near_duplicate_rate": None,
            "meta_scaffold_leak_count": machine["meta_scaffold_leak_count"],
            "quality_evaluation_completed": False,
            "dev_gate_pass": False,
        },
        "boundaries": {
            "accepted_baseline_count": 120,
            "baseline_increment_count": 0,
            "hidden_count": 0,
            "generator_qualified": False,
            "runtime_provider_adapter_qualified": False,
            "runtime_generation_eligible_profile_count": 0,
            "runtime_ingest_ready": False,
            "published_content_count": 0,
            "production_candidate_count": 0,
            "generation_600_allowed": False,
            "expand_3600_allowed": False,
            "readiness_all_false": True,
            "external_provider_API_call_count": 0,
            "KE_truth_change_count": 0,
            "RAG_change_count": 0,
            "DIFY_change_count": 0,
            "Serving_change_count": 0,
        },
        "ledger": {
            "previous_horizon": 33,
            "new_horizon": 34,
            "route_migration_34_appended": True,
            "route_migration_35_allowed": False,
        },
        "recommended_next_task": {
            "exactly_one_task_id": "CONTROLLED_V2_GENERATOR_ARCHITECTURE_STOP_AND_DECISION_004",
            "merge_current_PR_as_phase_0": False,
        },
    }
    result["result_digest"] = object_digest(result, "result_digest")
    return result


def _build_guardian_packet(result: Mapping[str, Any]) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "review_scope": "TRANSPORT_REPLAY_AND_INCOMPLETE_CONTENT_REVIEW_EVIDENCE",
        "guardian_verdict": "PENDING",
        "candidate_full_surface_review_possible": True,
        "candidate_full_surface_review_completed_by_execution": False,
        "candidate_full_surface_review_reason": "PRIMARY_REVIEWER_TIMEOUT_NO_PARTIAL_REVIEW_PERSISTED",
        "candidate_count_available_for_guardian_readback": 40,
        "required_checks": [
            "phase_0_pr12_merge_identity",
            "prior_zero_persistence_failure_identity",
            "dispatcher_owned_transport_identity",
            "transport_core_commit_1_freeze",
            "single_full_batch_replay_only",
            "physical_80_evaluable_40_counting",
            "forty_candidate_full_surface_readback",
            "machine_claim_closure_findings",
            "twenty_pair_semantic_independence",
            "independent_review_execution_failure_integrity",
            "baseline_hidden_and_readiness_boundaries",
            "route_34_bounded_ledger",
        ],
        "machine_blocking_findings": list(result["blocking_items"]),
        "eligible_to_open_sealed_hidden": False,
        "recommended_next_task_id": "CONTROLLED_V2_GENERATOR_ARCHITECTURE_STOP_AND_DECISION_004",
    }
    packet["packet_digest"] = object_digest(packet, "packet_digest")
    return packet


def materialize() -> None:
    if RESULT_PATH.exists() or GUARDIAN_PATH.exists():
        raise ValueError("closeout outputs already exist; use --check")
    machine, persistence, review_failure = _verify_inputs()
    result = _build_result(machine, persistence, review_failure)
    packet = _build_guardian_packet(result)
    write_json(RESULT_PATH, result)
    write_json(GUARDIAN_PATH, packet)


def check() -> None:
    machine, persistence, review_failure = _verify_inputs()
    expected_result = _build_result(machine, persistence, review_failure)
    expected_packet = _build_guardian_packet(expected_result)
    _require_equal(load_json(RESULT_PATH), expected_result, "development result")
    _require_equal(load_json(GUARDIAN_PATH), expected_packet, "guardian packet")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        materialize()
    print(json.dumps({"status": "PASS", "task_status": "STOPPED_BEFORE_HIDDEN_CONTENT_GATE_FAILED"}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"E_AUTHORIZED_REPLAY_CLOSEOUT: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
