#!/usr/bin/env python3
"""Build the explicit semantic-program P2 r4 targeted-review packet."""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from p2_axis_semantics_r4 import REVIEWED_VALUE_PROGRAMS
from p2_component_model import (
    TASK_ID,
    TASK_ROOT,
    jsonl_bytes,
    load_jsonl,
    object_digest,
    require,
    sha256_bytes,
    sha256_file,
    source_state,
    yaml_bytes,
)
from p2_generator_core_r4 import (
    AXIS_OUTPUT_KIND_BY_AXIS,
    build_axis_structural_output,
    build_local_typed_material,
    digest_object,
    shared_material_binding,
)
from p2_targeted_repair import AXIS_NAMES, CP_PATH_DESIGNS
from p2_targeted_repair_r2 import (
    AXIS_OPERATOR_IDS,
    _binding_for,
    _catalog,
    _component_pool,
    _profile_binding,
    build_supply_r2,
)
from p2_targeted_repair_r3 import (
    ADDITION_CANDIDATES_R3_PATH,
    FINAL_EDGE_CANDIDATES_R3_PATH,
    REVISED_COMPONENTS_R3_PATH,
    REVISED_RULES_R3_PATH,
    SELECTED_COMPONENTS,
)


if not __debug__:
    sys.stderr.write("P2 targeted repair r4 refuses python -O\n")
    raise SystemExit(2)


REVISED_COMPONENTS_R4_PATH = TASK_ROOT / "component/revised_component_candidates.r4.jsonl"
ADDITION_CANDIDATES_R4_PATH = TASK_ROOT / "component/necessary_addition_candidates.r4.jsonl"
REVISED_RULES_R4_PATH = TASK_ROOT / "component/revised_control_rules.r4.jsonl"
FINAL_EDGE_CANDIDATES_R4_PATH = TASK_ROOT / "component/final_edge_candidates.r4.jsonl"
REVISED_SUPPLY_R4_PATH = TASK_ROOT / "component/revised_candidate_supply_matrix.r4.yaml"
REPAIR_ASSESSMENT_R4_PATH = TASK_ROOT / "component/targeted_repair_assessment.r4.yaml"
REVISED_AB_R4_PATH = TASK_ROOT / "ab/revised_ab_path_candidates.r4.jsonl"
TARGETED_REVIEW_PACKET_R4_PATH = TASK_ROOT / "review/targeted_repair_review_packet.r4.jsonl"
TARGETED_REVIEW_JOB_R4_PATH = TASK_ROOT / "review/targeted_repair_review_job.r4.yaml"
TARGETED_RESULT_R4_PATH = TASK_ROOT / "result/p2_targeted_repair_checkpoint_result.r4.yaml"
GENERATOR_CORE_R4_PATH = TASK_ROOT / "p2_generator_core_r4.py"
AXIS_SEMANTICS_R4_PATH = TASK_ROOT / "p2_axis_semantics_r4.py"
GENERATOR_EVIDENCE_R4_PATH = TASK_ROOT / "p2_final_documents_r4.py"

AXIS_ALLOWED_VALUES = {
    axis: sorted(
        {
            value
            for profile_programs in REVIEWED_VALUE_PROGRAMS[axis].values()
            for value in profile_programs
        }
    )
    for axis in AXIS_NAMES
}


def _r4_operator(row: dict[str, Any], axis: str) -> dict[str, Any]:
    updated = copy.deepcopy(row)
    updated["component_version"] = "v1.1-p2-r4-semantic"
    updated["supersedes_targeted_r3_component_digest"] = updated[
        "component_digest"
    ]
    updated["mechanism"]["parameter_schema"] = {
        "axis": axis,
        "value_type": "PROFILE_AND_LANE_REVIEWED_SEMANTIC_PROGRAM",
        "allowed_values": AXIS_ALLOWED_VALUES[axis],
        "allowed_values_by_profile": {
            cp_id: sorted(programs)
            for cp_id, programs in REVIEWED_VALUE_PROGRAMS[axis].items()
        },
        "reviewed_value_programs": REVIEWED_VALUE_PROGRAMS[axis],
        "unknown_value_behavior": "REJECT",
        "known_but_wrong_lane_value_behavior": "REJECT",
        "known_but_wrong_profile_value_behavior": "REJECT",
        "output_kind": AXIS_OUTPUT_KIND_BY_AXIS[axis],
        "output_must_reference_exact_fact_object_ids": True,
        "structural_effect_digest_source": "STRUCTURAL_BODY_ONLY",
    }
    updated["mechanism"]["execution_contract"] = {
        "input": "EXACT_SHARED_TYPED_MATERIAL_AND_APPROVED_PATH_BINDING",
        "semantic_program_authority": "COMPONENT_REVIEWED_VALUE_PROGRAMS",
        "selection_by_hash_or_token_inference_allowed": False,
        "approved_path_is_runtime_trust_root": True,
        "output_kind": AXIS_OUTPUT_KIND_BY_AXIS[axis],
        "output_location": f"/structural_realization/lane_{{lane_id}}/axes/{axis}",
        "unknown_or_wrong_lane_action": "REJECT_BEFORE_REALIZATION",
        "may_add_or_change_fact": False,
        "may_add_or_change_authorization": False,
    }
    updated["activation_proposal"] = "REVISED_R4_FOR_TARGETED_TWO_REVIEW"
    updated["independent_review_state"] = "PENDING_TARGETED_R4_TWO_REVIEWS"
    updated["component_digest"] = object_digest(updated, "component_digest")
    return updated


def build_additions_r4(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    additions = [copy.deepcopy(row) for row in load_jsonl(root / ADDITION_CANDIDATES_R3_PATH)]
    changed: list[dict[str, Any]] = []
    operator_by_id = {operator_id: axis for axis, operator_id in AXIS_OPERATOR_IDS.items()}
    for index, row in enumerate(additions):
        axis = operator_by_id.get(str(row["component_id"]))
        if axis is None:
            continue
        updated = _r4_operator(row, axis)
        additions[index] = updated
        changed.append(updated)
    return additions, changed


def _material_for_cp(
    profile: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]], list[str]]:
    cp_id = str(profile["content_product_type_id"])
    component_ids = list(SELECTED_COMPONENTS[cp_id].values()) + list(
        AXIS_OPERATOR_IDS.values()
    )
    require(len(component_ids) == len(set(component_ids)), "E_R4_COMPONENT_DUPLICATE", cp_id)
    material = build_local_typed_material(
        profile, [component_by_id[component_id] for component_id in component_ids]
    )
    return material, _catalog(material), component_ids


def build_ab_paths_r4(
    state: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in state["profiles"]:
        cp_id = str(profile["content_product_type_id"])
        material, catalog, component_ids = _material_for_cp(profile, component_by_id)
        design = CP_PATH_DESIGNS[cp_id]
        lanes: dict[str, dict[str, Any]] = {}
        for lane_id, key in (("A", "a"), ("B", "b")):
            axis_values = dict(zip(AXIS_NAMES, design[key], strict=True))
            lanes[lane_id] = {
                **axis_values,
                "lane_id": lane_id,
                "session_policy": f"INDEPENDENT_SESSION_{lane_id}",
                "other_lane_visible": False,
                "component_ids": component_ids,
                "axis_operator_parameters": {
                    axis: {
                        "operator_component_id": AXIS_OPERATOR_IDS[axis],
                        "parameter_value": axis_values[axis],
                    }
                    for axis in AXIS_NAMES
                },
            }
        component_bindings = [
            _binding_for(component_by_id[component_id], catalog)
            for component_id in component_ids
        ]
        binding_by_id = {
            str(binding["component_id"]): binding for binding in component_bindings
        }
        material_binding = shared_material_binding(material)
        contracts: list[dict[str, Any]] = []
        for axis in AXIS_NAMES:
            operator_id = AXIS_OPERATOR_IDS[axis]
            a_value = str(lanes["A"][axis])
            b_value = str(lanes["B"][axis])
            a_program = REVIEWED_VALUE_PROGRAMS[axis][cp_id][a_value]
            b_program = REVIEWED_VALUE_PROGRAMS[axis][cp_id][b_value]
            a_output = build_axis_structural_output(
                axis, a_value, material, a_program
            )
            b_output = build_axis_structural_output(
                axis, b_value, material, b_program
            )
            require(
                a_output["structural_body_digest"]
                != b_output["structural_body_digest"],
                "E_R4_BODY_DIVERGENCE",
                f"{cp_id}:{axis}",
            )
            contracts.append(
                {
                    "axis": axis,
                    "lane_a_value": a_value,
                    "lane_b_value": b_value,
                    "lane_a_program_digest": digest_object(a_program),
                    "lane_b_program_digest": digest_object(b_program),
                    "allowed_values_digest": digest_object(AXIS_ALLOWED_VALUES[axis]),
                    "operator_component_id": operator_id,
                    "supporting_component_ids": [operator_id],
                    "operator_component_binding": binding_by_id[operator_id],
                    "operator_mechanism_digest": digest_object(
                        component_by_id[operator_id]["mechanism"]
                    ),
                    "shared_material_binding": material_binding,
                    "lane_a_structural_output": a_output,
                    "lane_b_structural_output": b_output,
                    "realization_target": (
                        f"/structural_realization/lane_{{lane_id}}/axes/{axis}"
                    ),
                    "values_must_differ": True,
                    "structural_bodies_must_differ": True,
                    "same_fact_set_must_be_preserved": True,
                    "approved_lane_value_is_authoritative": True,
                }
            )
        row: dict[str, Any] = {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "content_product_type_id": cp_id,
            "profile_digest": profile["profile_digest"],
            "shared_typed_material_contract": {
                "material_id": material["material_id"],
                "material_digest": material["material_digest"],
                "typed_object_catalog": catalog,
                "typed_object_catalog_digest": digest_object(catalog),
                "profile_exact_binding": _profile_binding(profile, catalog),
                "component_exact_bindings": component_bindings,
                "claim_boundary_digest": digest_object(material["claim_boundary"]),
                "shared_material_binding": material_binding,
                "same_exact_object_required_for_both_lanes": True,
            },
            "lane_a": lanes["A"],
            "lane_b": lanes["B"],
            "axis_realization_contracts": contracts,
            "observable_difference_axes": list(AXIS_NAMES),
            "observable_difference_axis_count": len(AXIS_NAMES),
            "body_level_difference_axis_count": len(AXIS_NAMES),
            "structural_candidate_only": True,
            "content_quality_proven": False,
            "active": False,
            "independent_review_state": "PENDING_TARGETED_R4_TWO_REVIEWS",
        }
        row["path_digest"] = object_digest(row, "path_digest")
        rows.append(row)
    return rows


def _packet_item(item_id: str, object_type: str, subject: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_item_id": item_id,
        "object_type": object_type,
        "review_subject": subject,
        "required_review_roles": [
            "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
            "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        ],
        "prefilled_score": None,
        "prefilled_decision": None,
    }


def build_targeted_repair_r4_documents(root: Path) -> dict[Path, bytes]:
    state = source_state(root)
    state["root"] = root
    revised = load_jsonl(root / REVISED_COMPONENTS_R3_PATH)
    rules = load_jsonl(root / REVISED_RULES_R3_PATH)
    edges = load_jsonl(root / FINAL_EDGE_CANDIDATES_R3_PATH)
    additions, changed_components = build_additions_r4(root)
    component_by_id = _component_pool(root, revised, additions)
    paths = build_ab_paths_r4(state, component_by_id)
    supply = build_supply_r2(state, edges)
    packet = [
        _packet_item(
            f"P2R4-COMPONENT-{row['component_id']}",
            "REVISED_SEMANTIC_AXIS_COMPONENT",
            row,
        )
        for row in changed_components
    ]
    packet.extend(
        _packet_item(
            f"P2R4-AB-{row['content_product_type_id']}",
            "REVISED_SEMANTIC_AB_STRUCTURAL_PATH_CAPABILITY",
            row,
        )
        for row in paths
    )
    packet.append(
        _packet_item(
            "P2R4-GENERATOR-CORE",
            "SEMANTIC_GENERATOR_CORE_CONTRACT_REPAIR",
            {
                "path": GENERATOR_CORE_R4_PATH.as_posix(),
                "sha256": sha256_file(root / GENERATOR_CORE_R4_PATH),
                "axis_semantics_source": {
                    "path": AXIS_SEMANTICS_R4_PATH.as_posix(),
                    "sha256": sha256_file(root / AXIS_SEMANTICS_R4_PATH),
                },
                "evidence_harness": {
                    "path": GENERATOR_EVIDENCE_R4_PATH.as_posix(),
                    "sha256": sha256_file(root / GENERATOR_EVIDENCE_R4_PATH),
                    "known_enum_substitution_case_count": 120,
                    "contract_tamper_case_count": 240,
                },
                "legacy_r3_core_remains_historical_non_active": True,
                "required_repairs": [
                    "EXECUTE_EXPLICIT_PER_VALUE_FACT_ROLE_PROGRAMS",
                    "REMOVE_HASH_AND_TOKEN_DERIVED_AXIS_SELECTION",
                    "BIND_REQUEST_TO_APPROVED_PATH_DIGEST_AND_DESIGNATED_LANE_VALUE",
                    "REJECT_KNOWN_ENUM_SUBSTITUTION",
                    "MEASURE_DIVERGENCE_FROM_STRUCTURAL_BODY_ONLY",
                ],
                "audience_content_allowed": False,
                "external_provider_allowed": False,
                "readiness_transition_allowed": False,
            },
        )
    )
    packet_bytes = jsonl_bytes(packet)
    packet_sha = sha256_bytes(packet_bytes)
    assessment: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "r1_r2_r3_failure_evidence_preserved": True,
        "r4_repairs": [
            "SIX_AXIS_OPERATORS_CONTAIN_EXPLICIT_PROFILE_AND_LANE_PROGRAMS",
            "NO_HASH_OR_TOKEN_INFERENCE_IN_ACTIVE_R4_CORE",
            "KNOWN_REVIEWED_ENUM_SUBSTITUTION_REJECTED_BY_APPROVED_PATH_BINDING",
            "ALL_120_AXIS_PAIRS_DIFFER_AT_STRUCTURAL_BODY_LEVEL",
        ],
        "historical_inventory": 86,
        "historical_inventory_target_used": False,
        "changed_component_count": len(changed_components),
        "changed_path_count": len(paths),
        "number_target_used": False,
    }
    assessment["assessment_digest"] = object_digest(assessment, "assessment_digest")
    job: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "prompt_revision": "r4",
        "checkpoint_state": "PENDING_TARGETED_R4_TWO_REVIEW",
        "review_packet_path": TARGETED_REVIEW_PACKET_R4_PATH.as_posix(),
        "review_packet_sha256": packet_sha,
        "packet_item_count": len(packet),
        "packet_item_counts": dict(Counter(row["object_type"] for row in packet)),
        "reviewer_policy": {
            "reuse_original_identity_isolated_primary_and_secondary_reviewers": True,
            "review_actual_payload_and_executable_outputs": True,
            "r1_r2_r3_failure_records_remain_visible_and_immutable": True,
            "self_approval_allowed": False,
        },
        "activation_before_matching_approvals_allowed": False,
    }
    job["review_job_digest"] = object_digest(job, "review_job_digest")
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_TARGETED_R4_TWO_REVIEW",
        "p2_complete": False,
        "p3_allowed": False,
        "review_packet_sha256": packet_sha,
        "review_item_count": len(packet),
        "active_component_count": 0,
        "active_edge_count": 0,
        "self_approval_count": 0,
        "core_numbers": {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "readiness": {
            "generator_qualified": False,
            "generation_allowed": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        },
    }
    result["result_digest"] = object_digest(result, "result_digest")
    return {
        REVISED_COMPONENTS_R4_PATH: jsonl_bytes(revised),
        ADDITION_CANDIDATES_R4_PATH: jsonl_bytes(additions),
        REVISED_RULES_R4_PATH: jsonl_bytes(rules),
        FINAL_EDGE_CANDIDATES_R4_PATH: jsonl_bytes(edges),
        REVISED_SUPPLY_R4_PATH: yaml_bytes(supply),
        REPAIR_ASSESSMENT_R4_PATH: yaml_bytes({"targeted_repair_assessment": assessment}),
        REVISED_AB_R4_PATH: jsonl_bytes(paths),
        TARGETED_REVIEW_PACKET_R4_PATH: packet_bytes,
        TARGETED_REVIEW_JOB_R4_PATH: yaml_bytes({"targeted_repair_review_job": job}),
        TARGETED_RESULT_R4_PATH: yaml_bytes({"p2_targeted_repair_checkpoint_result": result}),
    }


def validate_targeted_repair_r4_documents(documents: dict[Path, bytes]) -> None:
    def rows(path: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in documents[path].decode("utf-8").splitlines()
            if line
        ]

    revised = rows(REVISED_COMPONENTS_R4_PATH)
    additions = rows(ADDITION_CANDIDATES_R4_PATH)
    rules = rows(REVISED_RULES_R4_PATH)
    edges = rows(FINAL_EDGE_CANDIDATES_R4_PATH)
    paths = rows(REVISED_AB_R4_PATH)
    packet = rows(TARGETED_REVIEW_PACKET_R4_PATH)
    result = yaml.safe_load(documents[TARGETED_RESULT_R4_PATH])[
        "p2_targeted_repair_checkpoint_result"
    ]
    require(len(revised) == 19, "E_R4_REVISED_COUNT")
    require(len(additions) == 30, "E_R4_ADDITION_COUNT")
    require(len(rules) == 8, "E_R4_RULE_COUNT")
    require(len(edges) == 85, "E_R4_EDGE_COUNT")
    require(len(paths) == 20, "E_R4_PATH_COUNT")
    require(len(packet) == 27, "E_R4_PACKET_COUNT")
    require(result["p2_complete"] is False and result["p3_allowed"] is False, "E_R4_EARLY_ACTIVATION")
    require(not any(result["readiness"].values()), "E_R4_READINESS")
    operators = {
        row["component_id"]: row
        for row in additions
        if row["component_id"] in set(AXIS_OPERATOR_IDS.values())
    }
    require(len(operators) == 6, "E_R4_OPERATOR_COUNT")
    for axis, operator_id in AXIS_OPERATOR_IDS.items():
        schema = operators[operator_id]["mechanism"]["parameter_schema"]
        require(schema["allowed_values"] == AXIS_ALLOWED_VALUES[axis], "E_R4_ALLOWED_VALUES", axis)
        require(schema["reviewed_value_programs"] == REVIEWED_VALUE_PROGRAMS[axis], "E_R4_PROGRAMS", axis)
        require(schema["known_but_wrong_lane_value_behavior"] == "REJECT", "E_R4_LANE_REJECT", axis)
    for path in paths:
        require(len(path["axis_realization_contracts"]) == 6, "E_R4_AXIS_COUNT")
        require(path["body_level_difference_axis_count"] == 6, "E_R4_BODY_COUNT")
        for contract in path["axis_realization_contracts"]:
            a_output = contract["lane_a_structural_output"]
            b_output = contract["lane_b_structural_output"]
            require(
                a_output["structural_body_digest"] != b_output["structural_body_digest"],
                "E_R4_BODY_DIVERGENCE",
            )
            require(
                a_output["structural_effect_digest"] == a_output["structural_body_digest"]
                and b_output["structural_effect_digest"] == b_output["structural_body_digest"],
                "E_R4_EFFECT_SOURCE",
            )
            require(contract["approved_lane_value_is_authoritative"] is True, "E_R4_LANE_AUTHORITY")
    require(
        all(row["component_digest"] == object_digest(row, "component_digest") for row in revised + additions),
        "E_R4_COMPONENT_DIGEST",
    )
    require(all(row["edge_digest"] == object_digest(row, "edge_digest") for row in edges), "E_R4_EDGE_DIGEST")
    require(all(row["path_digest"] == object_digest(row, "path_digest") for row in paths), "E_R4_PATH_DIGEST")


__all__ = [
    "ADDITION_CANDIDATES_R4_PATH",
    "FINAL_EDGE_CANDIDATES_R4_PATH",
    "REVISED_AB_R4_PATH",
    "REVISED_COMPONENTS_R4_PATH",
    "REVISED_RULES_R4_PATH",
    "TARGETED_REVIEW_PACKET_R4_PATH",
    "TARGETED_RESULT_R4_PATH",
    "build_targeted_repair_r4_documents",
    "validate_targeted_repair_r4_documents",
]
