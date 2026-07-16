"""Digest-closed qualification request builder for v4 recovery."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import contract, material_policy, test_allocator


def _stable_scenario_digest(scenario: Mapping[str, Any]) -> str:
    return test_allocator.scenario_digest_for_case(scenario)


def build_request(
    scenario: Mapping[str, Any],
    material: Mapping[str, Any],
    assignment: Mapping[str, Any],
    *,
    batch_id: str,
    run_id: str,
    author_identity: str,
    model_config_ref: str,
) -> dict[str, Any]:
    """Build one first-attempt-only request.

    ``batch_id`` is runtime metadata and cannot affect ``assignment`` because
    the assignment is supplied, validated, and copied byte-for-byte.
    """
    batch_id = contract.as_text(batch_id, "E_V4_BATCH_ID")
    run_id = contract.as_text(run_id, "E_V4_RUN_ID")
    author_identity = contract.as_text(author_identity, "E_V4_AUTHOR_ID")
    model_config_ref = contract.as_text(model_config_ref, "E_V4_MODEL_CONFIG_REF")
    scenario_id = contract.as_text(scenario.get("scenario_id"), "E_V4_SCENARIO_ID")
    profile_id = contract.as_text(scenario.get("profile_id"), "E_V4_PROFILE_ID")
    scenario_digest = _stable_scenario_digest(scenario)
    test_allocator.validate_assignment(assignment)
    material_policy.validate_material(material)
    policy = material_policy.compile_surface_policy(material)
    contract.require(assignment["scenario_id"] == scenario_id and
                     assignment["profile_id"] == profile_id,
                     "E_V4_ASSIGNMENT_SCENARIO_JOIN")
    contract.require(assignment["scenario_digest"] == scenario_digest,
                     "E_V4_ASSIGNMENT_SCENARIO_DIGEST")
    contract.require(material["scenario_id"] == scenario_id and
                     material["profile_id"] == profile_id,
                     "E_V4_MATERIAL_SCENARIO_JOIN")
    contract.require(assignment["material_packet_digest"] == material["material_digest"],
                     "E_V4_ASSIGNMENT_MATERIAL_JOIN")
    request: dict[str, Any] = {
        "schema_version": contract.REQUEST_SCHEMA,
        "task_id": contract.TASK_ID,
        "generator_version": contract.GENERATOR_VERSION,
        "rule_version": contract.RULE_VERSION,
        "request_id": f"V4REQ-{batch_id}-{scenario_id}",
        "batch_id": batch_id,
        "run_id": run_id,
        "qualification_mode": True,
        "scenario_id": scenario_id,
        "scenario_digest": scenario_digest,
        "profile_id": profile_id,
        "author_identity": author_identity,
        "model_config_ref": model_config_ref,
        "gate1_test_assignment": copy.deepcopy(dict(assignment)),
        "assignment_digest": assignment["assignment_digest"],
        "typed_material": copy.deepcopy(dict(material)),
        "material_digest": material["material_digest"],
        "surface_policy": policy,
        "policy_digest": policy["policy_digest"],
        "attempt_policy": {
            "max_attempts": 1,
            "first_attempt_only": True,
            "feedback_before_submission_forbidden": True,
            "replacement_candidates_forbidden": True,
            "failed_attempt_retained_in_denominator": True,
        },
        "author_output_contract": {
            "synthetic_disclosure_required": True,
            "surface_fact_ids_must_exist": True,
            "must_surface_coverage_required": True,
            "control_only_surface_forbidden": True,
            "author_claim_list_is_not_safety_evidence": True,
            "independent_claim_extraction_required_downstream": True,
            "publishable": False,
            "runtime_consumable": False,
            "counts_toward_300": False,
        },
        "prior_feedback": [],
        "request_digest": "",
    }
    contract.close_digest(request, "request_digest")
    validate_request(request)
    return request


def validate_request(request: Mapping[str, Any]) -> None:
    expected = {
        "schema_version", "task_id", "generator_version", "rule_version",
        "request_id", "batch_id", "run_id", "qualification_mode", "scenario_id",
        "scenario_digest", "profile_id", "author_identity", "model_config_ref",
        "gate1_test_assignment", "assignment_digest", "typed_material",
        "material_digest", "surface_policy", "policy_digest", "attempt_policy",
        "author_output_contract", "prior_feedback", "request_digest",
    }
    contract.exact_fields(request, expected, "E_V4_REQUEST_FIELDS")
    contract.require(request["schema_version"] == contract.REQUEST_SCHEMA,
                     "E_V4_REQUEST_SCHEMA")
    contract.require(request["task_id"] == contract.TASK_ID, "E_V4_REQUEST_TASK")
    contract.require(request["generator_version"] == contract.GENERATOR_VERSION,
                     "E_V4_REQUEST_GENERATOR")
    contract.require(request["rule_version"] == contract.RULE_VERSION,
                     "E_V4_REQUEST_RULE")
    for field in ("request_id", "batch_id", "run_id", "scenario_id", "profile_id",
                  "author_identity", "model_config_ref"):
        contract.as_text(request[field], f"E_V4_REQUEST_TEXT:{field}")
    contract.require(request["qualification_mode"] is True,
                     "E_V4_REQUEST_QUALIFICATION_MODE")
    assignment = contract.as_mapping(request["gate1_test_assignment"],
                                     "E_V4_REQUEST_ASSIGNMENT")
    test_allocator.validate_assignment(assignment)
    contract.require("batch_id" not in assignment, "E_V4_ASSIGNMENT_BATCH_CONTAMINATION")
    contract.require(request["assignment_digest"] == assignment["assignment_digest"],
                     "E_V4_REQUEST_ASSIGNMENT_DIGEST")
    contract.require(request["scenario_id"] == assignment["scenario_id"] and
                     request["profile_id"] == assignment["profile_id"] and
                     request["scenario_digest"] == assignment["scenario_digest"],
                     "E_V4_REQUEST_ASSIGNMENT_JOIN")
    material = contract.as_mapping(request["typed_material"], "E_V4_REQUEST_MATERIAL")
    material_policy.validate_material(material)
    contract.require(request["material_digest"] == material["material_digest"],
                     "E_V4_REQUEST_MATERIAL_DIGEST")
    contract.require(assignment["material_packet_digest"] == material["material_digest"],
                     "E_V4_REQUEST_ASSIGNMENT_MATERIAL_DIGEST")
    assignment_policy = {
        row["reference_assertion_id"]: row["policy"]
        for row in assignment["evidence_surface_policy"]
    }
    material_policy_map = {fact["fact_id"]: fact["surface_policy"]
                           for fact in material["facts"]}
    contract.require(assignment_policy == material_policy_map,
                     "E_V4_REQUEST_ASSIGNMENT_POLICY_JOIN")
    contract.require(request["scenario_id"] == material["scenario_id"] and
                     request["profile_id"] == material["profile_id"],
                     "E_V4_REQUEST_MATERIAL_JOIN")
    policy = contract.as_mapping(request["surface_policy"], "E_V4_REQUEST_POLICY")
    material_policy.validate_surface_policy(policy, material)
    contract.require(request["policy_digest"] == policy["policy_digest"],
                     "E_V4_REQUEST_POLICY_DIGEST")
    attempt = contract.as_mapping(request["attempt_policy"], "E_V4_ATTEMPT_POLICY")
    contract.exact_fields(
        attempt, {"max_attempts", "first_attempt_only",
                  "feedback_before_submission_forbidden",
                  "replacement_candidates_forbidden",
                  "failed_attempt_retained_in_denominator"},
        "E_V4_ATTEMPT_POLICY_FIELDS")
    contract.require(attempt["max_attempts"] == 1 and
                     all(attempt[key] is True for key in attempt if key != "max_attempts"),
                     "E_V4_ATTEMPT_POLICY")
    output_contract = contract.as_mapping(request["author_output_contract"],
                                          "E_V4_OUTPUT_CONTRACT")
    contract.exact_fields(
        output_contract,
        {"synthetic_disclosure_required", "surface_fact_ids_must_exist",
         "must_surface_coverage_required", "control_only_surface_forbidden",
         "author_claim_list_is_not_safety_evidence",
         "independent_claim_extraction_required_downstream", "publishable",
         "runtime_consumable", "counts_toward_300"},
        "E_V4_OUTPUT_CONTRACT_FIELDS",
    )
    for field in ("synthetic_disclosure_required", "surface_fact_ids_must_exist",
                  "must_surface_coverage_required", "control_only_surface_forbidden",
                  "author_claim_list_is_not_safety_evidence",
                  "independent_claim_extraction_required_downstream"):
        contract.require(output_contract.get(field) is True,
                         "E_V4_OUTPUT_CONTRACT", field)
    for field in ("publishable", "runtime_consumable", "counts_toward_300"):
        contract.require(output_contract.get(field) is False,
                         "E_V4_OUTPUT_BOUNDARY", field)
    contract.require(request["prior_feedback"] == [], "E_V4_FEEDBACK_FORBIDDEN")
    contract.validate_digest(request, "request_digest", "E_V4_REQUEST_DIGEST")


def build_batch(
    scenarios: Sequence[Mapping[str, Any]],
    materials: Sequence[Mapping[str, Any]],
    assignments: Sequence[Mapping[str, Any]],
    *,
    batch_id: str,
    run_id: str,
    authors_by_profile: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    scenario_by_id = contract.unique_by(scenarios, "scenario_id", "E_V4_SCENARIO_DUP")
    material_by_id = contract.unique_by(materials, "scenario_id", "E_V4_MATERIAL_DUP")
    assignment_by_id = contract.unique_by(assignments, "scenario_id", "E_V4_ASSIGNMENT_DUP")
    contract.require(set(scenario_by_id) == set(material_by_id) == set(assignment_by_id),
                     "E_V4_BATCH_JOIN")
    requests: list[dict[str, Any]] = []
    for scenario_id in sorted(scenario_by_id):
        scenario = scenario_by_id[scenario_id]
        profile_id = str(scenario["profile_id"])
        author = contract.as_mapping(authors_by_profile.get(profile_id),
                                     "E_V4_AUTHOR_ASSIGNMENT")
        requests.append(build_request(
            scenario, material_by_id[scenario_id], assignment_by_id[scenario_id],
            batch_id=batch_id, run_id=run_id,
            author_identity=contract.as_text(author.get("author_identity"),
                                             "E_V4_AUTHOR_ID"),
            model_config_ref=contract.as_text(author.get("model_config_ref"),
                                              "E_V4_MODEL_CONFIG_REF"),
        ))
    contract.unique_by(requests, "request_id", "E_V4_REQUEST_DUP")
    return requests


__all__ = ["build_batch", "build_request", "validate_request"]
