#!/usr/bin/env python3
"""Build the executable-axis P2 r3 targeted-review packet."""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

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
from p2_generator_core import (
    AXIS_OUTPUT_KIND_BY_AXIS,
    build_axis_structural_output,
    build_local_typed_material,
    digest_object,
    shared_material_binding,
)
from p2_targeted_repair import AXIS_NAMES, CP_PATH_DESIGNS
from p2_targeted_repair_r2 import (
    ADDITION_CANDIDATES_R2_PATH,
    AXIS_OPERATOR_IDS,
    FINAL_EDGE_CANDIDATES_R2_PATH,
    REVISED_COMPONENTS_R2_PATH,
    REVISED_RULES_R2_PATH,
    SELECTED_COMPONENTS as R2_SELECTED_COMPONENTS,
    _binding_for,
    _catalog,
    _component_pool,
    _design_component,
    _profile_binding,
    _role_intent,
    build_supply_r2,
)


if not __debug__:
    sys.stderr.write("P2 targeted repair r3 refuses python -O\n")
    raise SystemExit(2)


REVISED_COMPONENTS_R3_PATH = TASK_ROOT / "component/revised_component_candidates.r3.jsonl"
ADDITION_CANDIDATES_R3_PATH = TASK_ROOT / "component/necessary_addition_candidates.r3.jsonl"
REVISED_RULES_R3_PATH = TASK_ROOT / "component/revised_control_rules.r3.jsonl"
FINAL_EDGE_CANDIDATES_R3_PATH = TASK_ROOT / "component/final_edge_candidates.r3.jsonl"
REVISED_SUPPLY_R3_PATH = TASK_ROOT / "component/revised_candidate_supply_matrix.r3.yaml"
REPAIR_ASSESSMENT_R3_PATH = TASK_ROOT / "component/targeted_repair_assessment.r3.yaml"
REVISED_AB_R3_PATH = TASK_ROOT / "ab/revised_ab_path_candidates.r3.jsonl"
TARGETED_REVIEW_PACKET_R3_PATH = TASK_ROOT / "review/targeted_repair_review_packet.r3.jsonl"
TARGETED_REVIEW_JOB_R3_PATH = TASK_ROOT / "review/targeted_repair_review_job.r3.yaml"
TARGETED_RESULT_R3_PATH = TASK_ROOT / "result/p2_targeted_repair_checkpoint_result.r3.yaml"
GENERATOR_CORE_PATH = TASK_ROOT / "p2_generator_core.py"

CP16_TRIGGER_ID = "G1V11-P2-TRIGGER-AUTHORIZED-SERVICE-NEED"
AXIS_ALLOWED_VALUES = {
    axis: sorted(
        {
            value
            for design in CP_PATH_DESIGNS.values()
            for value in (
                dict(zip(AXIS_NAMES, design["a"], strict=True))[axis],
                dict(zip(AXIS_NAMES, design["b"], strict=True))[axis],
            )
        }
    )
    for axis in AXIS_NAMES
}

SELECTED_COMPONENTS = copy.deepcopy(R2_SELECTED_COMPONENTS)
SELECTED_COMPONENTS["CP16"]["trigger"] = CP16_TRIGGER_ID


def _cp16_trigger_spec() -> dict[str, Any]:
    return {
        "role": "trigger",
        "asset_class": "narrative_operator",
        "profiles": ["CP16"],
        "function": (
            "Trigger a service review only from an authorized customer task or need "
            "and its supplied service feedback or unfinished state."
        ),
        "inputs": ["safe_next_step_policy"],
        "facts": ["customer_task_truth", "service_feedback_or_unfinished_state"],
        "authorizations": ["customer_privacy_consent", "service_capture_scope"],
        "gap": (
            "CP16 required a real authorized service-need trigger; explanation "
            "complexity was a production condition rather than service-case evidence."
        ),
        "nearest_difference": (
            "Unlike the outfit-complexity trigger, this component cannot run without "
            "customer-task truth, service state, privacy consent, and service scope."
        ),
        "parameter_schema": None,
    }


def _r3_operator(row: dict[str, Any], axis: str) -> dict[str, Any]:
    updated = copy.deepcopy(row)
    old_digest = str(updated["component_digest"])
    updated["component_version"] = "v1.1-p2-r3-new"
    updated["supersedes_targeted_r2_component_digest"] = old_digest
    updated["mechanism"]["parameter_schema"] = {
        "axis": axis,
        "value_type": "PROFILE_REVIEWED_ENUM",
        "allowed_values": AXIS_ALLOWED_VALUES[axis],
        "unknown_value_behavior": "REJECT",
        "output_kind": AXIS_OUTPUT_KIND_BY_AXIS[axis],
        "output_must_reference_exact_fact_object_ids": True,
    }
    updated["mechanism"]["execution_contract"] = {
        "input": "EXACT_SHARED_TYPED_MATERIAL_BINDING",
        "output_kind": AXIS_OUTPUT_KIND_BY_AXIS[axis],
        "output_location": f"/structural_realization/lane_{{lane_id}}/axes/{axis}",
        "unknown_value_action": "REJECT_BEFORE_REALIZATION",
        "may_add_or_change_fact": False,
        "may_add_or_change_authorization": False,
    }
    updated["activation_proposal"] = "REVISED_R3_FOR_TARGETED_TWO_REVIEW"
    updated["independent_review_state"] = "PENDING_TARGETED_R3_TWO_REVIEWS"
    updated["component_digest"] = object_digest(updated, "component_digest")
    return updated


def build_additions_r3(state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    additions = [copy.deepcopy(row) for row in load_jsonl(state["root"] / ADDITION_CANDIDATES_R2_PATH)]
    changed: list[dict[str, Any]] = []
    for index, row in enumerate(additions):
        component_id = str(row["component_id"])
        axis = next(
            (axis for axis, operator_id in AXIS_OPERATOR_IDS.items() if operator_id == component_id),
            None,
        )
        if axis is None:
            continue
        updated = _r3_operator(row, axis)
        additions[index] = updated
        changed.append(updated)
    cp16 = _design_component(CP16_TRIGGER_ID, _cp16_trigger_spec(), state["profile_by_id"])
    cp16["component_version"] = "v1.1-p2-r3-new"
    cp16["activation_proposal"] = "NECESSARY_R3_ADDITION_PENDING_TWO_REVIEWS"
    cp16["independent_review_state"] = "PENDING_TARGETED_R3_TWO_REVIEWS"
    cp16["component_digest"] = object_digest(cp16, "component_digest")
    additions.append(cp16)
    changed.append(cp16)
    return additions, changed


def _material_for_cp(
    profile: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]], list[str]]:
    cp_id = str(profile["content_product_type_id"])
    component_ids = list(SELECTED_COMPONENTS[cp_id].values()) + list(
        AXIS_OPERATOR_IDS.values()
    )
    require(len(component_ids) == len(set(component_ids)), "E_R3_COMPONENT_DUPLICATE", cp_id)
    material = build_local_typed_material(
        profile, [component_by_id[component_id] for component_id in component_ids]
    )
    return material, _catalog(material), component_ids


def _build_cp16_trigger_edge(
    state: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    profile = state["profile_by_id"]["CP16"]
    material, catalog, _ = _material_for_cp(profile, component_by_id)
    component = component_by_id[CP16_TRIGGER_ID]
    row: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "edge_id": "P2R3-EDGE-CP16-trigger-01",
        "content_product_type_id": "CP16",
        "component_id": CP16_TRIGGER_ID,
        "component_digest": component["component_digest"],
        "required_component_role": "trigger",
        "selection_purpose": "AUTHORIZED_SERVICE_NEED_AND_TYPED_OBJECT_CLOSED_SUPPLY",
        "fit_basis": {
            "product_label": profile["chinese_label"],
            "business_purpose": profile["business_purpose"],
            "exact_required_role": "trigger",
            "required_role_intent": _role_intent(profile, "trigger"),
            "component_function": component["mechanism"]["function"],
            "component_nearest_difference": component["provenance"][
                "nearest_component_difference"
            ],
            "profile_narrative_operators": profile["narrative_constraints"][
                "allowed_narrative_operator_families"
            ],
            "profile_hard_guards": profile["founder_hard_guards"],
            "customer_task_or_need_must_be_real_and_authorized": True,
            "product_label_or_historical_applicability_is_not_evidence": True,
        },
        "shared_material_contract": {
            "material_id": material["material_id"],
            "material_digest": material["material_digest"],
            "typed_object_catalog_digest": digest_object(catalog),
        },
        "component_exact_binding": _binding_for(component, catalog),
        "profile_exact_binding": _profile_binding(profile, catalog),
        "forbidden_combinations": component["forbidden_combinations"],
        "missing_input_behavior": component["missing_input_behavior"],
        "historical_edge_reactivated": False,
        "proposed_new_edge": True,
        "active": False,
        "independent_review_state": "PENDING_TARGETED_R3_TWO_REVIEWS",
    }
    row["edge_digest"] = object_digest(row, "edge_digest")
    return row


def build_edges_r3(
    state: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = [copy.deepcopy(row) for row in load_jsonl(state["root"] / FINAL_EDGE_CANDIDATES_R2_PATH)]
    replacement = _build_cp16_trigger_edge(state, component_by_id)
    rows = [
        row
        for row in rows
        if not (
            row["content_product_type_id"] == "CP16"
            and row["required_component_role"] == "trigger"
        )
    ]
    rows.append(replacement)
    rows.sort(key=lambda row: (row["content_product_type_id"], row["required_component_role"]))
    return rows, [replacement]


def build_ab_paths_r3(
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
        binding_by_id = {str(row["component_id"]): row for row in component_bindings}
        material_binding = shared_material_binding(material)
        contracts: list[dict[str, Any]] = []
        for axis in AXIS_NAMES:
            operator_id = AXIS_OPERATOR_IDS[axis]
            contracts.append(
                {
                    "axis": axis,
                    "lane_a_value": lanes["A"][axis],
                    "lane_b_value": lanes["B"][axis],
                    "allowed_values_digest": digest_object(AXIS_ALLOWED_VALUES[axis]),
                    "operator_component_id": operator_id,
                    "supporting_component_ids": [operator_id],
                    "operator_component_binding": binding_by_id[operator_id],
                    "operator_mechanism_digest": digest_object(
                        component_by_id[operator_id]["mechanism"]
                    ),
                    "shared_material_binding": material_binding,
                    "lane_a_structural_output": build_axis_structural_output(
                        axis, str(lanes["A"][axis]), material
                    ),
                    "lane_b_structural_output": build_axis_structural_output(
                        axis, str(lanes["B"][axis]), material
                    ),
                    "realization_target": (
                        f"/structural_realization/lane_{{lane_id}}/axes/{axis}"
                    ),
                    "values_must_differ": True,
                    "same_fact_set_must_be_preserved": True,
                }
            )
        row: dict[str, Any] = {
            "schema_version": "v0.1",
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
            "structural_candidate_only": True,
            "content_quality_proven": False,
            "active": False,
            "independent_review_state": "PENDING_TARGETED_R3_TWO_REVIEWS",
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


def build_targeted_repair_r3_documents(root: Path) -> dict[Path, bytes]:
    state = source_state(root)
    state["root"] = root
    revised = load_jsonl(root / REVISED_COMPONENTS_R2_PATH)
    rules = load_jsonl(root / REVISED_RULES_R2_PATH)
    additions, changed_components = build_additions_r3(state)
    component_by_id = _component_pool(root, revised, additions)
    edges, changed_edges = build_edges_r3(state, component_by_id)
    paths = build_ab_paths_r3(state, component_by_id)
    supply = build_supply_r2(state, edges)
    packet = [
        _packet_item(
            f"P2R3-COMPONENT-{row['component_id']}",
            "REVISED_OR_NECESSARY_COMPONENT",
            row,
        )
        for row in changed_components
    ]
    packet.extend(
        _packet_item(row["edge_id"], "REVISED_COMPONENT_CP_EDGE", row)
        for row in changed_edges
    )
    packet.extend(
        _packet_item(
            f"P2R3-AB-{row['content_product_type_id']}",
            "REVISED_AB_STRUCTURAL_PATH_CAPABILITY",
            row,
        )
        for row in paths
    )
    packet.append(
        _packet_item(
            "P2R3-GENERATOR-CORE",
            "GENERATOR_CORE_CONTRACT_REPAIR",
            {
                "path": GENERATOR_CORE_PATH.as_posix(),
                "sha256": sha256_file(root / GENERATOR_CORE_PATH),
                "required_repairs": [
                    "REVALIDATE_TYPED_MATERIAL_AT_REALIZATION_ENTRY",
                    "MATCH_BINDING_SLOTS_TO_AUTHORITATIVE_COMPONENT_CONTRACT",
                    "REJECT_UNKNOWN_AXIS_VALUES",
                    "BIND_ACTUAL_SHARED_MATERIAL_DIGESTS",
                    "EMIT_RESOLVABLE_AXIS_SPECIFIC_STRUCTURAL_OUTPUTS",
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
        "r2_failure_evidence_preserved": True,
        "r3_repairs": [
            "SIX_AXIS_OPERATORS_HAVE_REVIEWED_ENUMS_AND_EXECUTABLE_OUTPUT_SCHEMAS",
            "AXIS_OUTPUTS_RESOLVE_TO_STRUCTURAL_REALIZATION_OBJECTS",
            "AXIS_OPERATORS_BIND_ACTUAL_SHARED_MATERIAL_FACT_AND_AUTHORIZATION_DIGESTS",
            "UNKNOWN_AXIS_VALUES_REJECTED",
            "CP16_TRIGGER_BOUND_TO_AUTHORIZED_SERVICE_NEED",
        ],
        "historical_inventory": 86,
        "historical_inventory_target_used": False,
        "changed_component_count": len(changed_components),
        "changed_edge_count": len(changed_edges),
        "changed_path_count": len(paths),
        "number_target_used": False,
    }
    assessment["assessment_digest"] = object_digest(assessment, "assessment_digest")
    job: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "prompt_revision": "r3",
        "checkpoint_state": "PENDING_TARGETED_R3_TWO_REVIEW",
        "review_packet_path": TARGETED_REVIEW_PACKET_R3_PATH.as_posix(),
        "review_packet_sha256": packet_sha,
        "packet_item_count": len(packet),
        "packet_item_counts": dict(Counter(row["object_type"] for row in packet)),
        "reviewer_policy": {
            "reuse_original_identity_isolated_primary_and_secondary_reviewers": True,
            "review_actual_payload_and_executable_outputs": True,
            "r1_and_r2_failure_records_remain_visible_and_immutable": True,
            "self_approval_allowed": False,
        },
        "activation_before_matching_approvals_allowed": False,
    }
    job["review_job_digest"] = object_digest(job, "review_job_digest")
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_TARGETED_R3_TWO_REVIEW",
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
        REVISED_COMPONENTS_R3_PATH: jsonl_bytes(revised),
        ADDITION_CANDIDATES_R3_PATH: jsonl_bytes(additions),
        REVISED_RULES_R3_PATH: jsonl_bytes(rules),
        FINAL_EDGE_CANDIDATES_R3_PATH: jsonl_bytes(edges),
        REVISED_SUPPLY_R3_PATH: yaml_bytes(supply),
        REPAIR_ASSESSMENT_R3_PATH: yaml_bytes({"targeted_repair_assessment": assessment}),
        REVISED_AB_R3_PATH: jsonl_bytes(paths),
        TARGETED_REVIEW_PACKET_R3_PATH: packet_bytes,
        TARGETED_REVIEW_JOB_R3_PATH: yaml_bytes({"targeted_repair_review_job": job}),
        TARGETED_RESULT_R3_PATH: yaml_bytes({"p2_targeted_repair_checkpoint_result": result}),
    }


def validate_targeted_repair_r3_documents(documents: dict[Path, bytes]) -> None:
    def rows(path: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in documents[path].decode("utf-8").splitlines()
            if line
        ]

    revised = rows(REVISED_COMPONENTS_R3_PATH)
    additions = rows(ADDITION_CANDIDATES_R3_PATH)
    rules = rows(REVISED_RULES_R3_PATH)
    edges = rows(FINAL_EDGE_CANDIDATES_R3_PATH)
    paths = rows(REVISED_AB_R3_PATH)
    packet = rows(TARGETED_REVIEW_PACKET_R3_PATH)
    result = yaml.safe_load(documents[TARGETED_RESULT_R3_PATH])[
        "p2_targeted_repair_checkpoint_result"
    ]
    require(len(revised) == 19, "E_R3_REVISED_COUNT")
    require(len(additions) == 30, "E_R3_ADDITION_COUNT")
    require(len(rules) == 8, "E_R3_RULE_COUNT")
    require(len(edges) == 85, "E_R3_EDGE_COUNT")
    require(len(paths) == 20, "E_R3_PATH_COUNT")
    require(len(packet) == 29, "E_R3_PACKET_COUNT")
    require(result["p2_complete"] is False and result["p3_allowed"] is False, "E_R3_EARLY_ACTIVATION")
    require(not any(result["readiness"].values()), "E_R3_READINESS")
    operator_by_id = {
        row["component_id"]: row
        for row in additions
        if row["component_id"] in set(AXIS_OPERATOR_IDS.values())
    }
    require(len(operator_by_id) == 6, "E_R3_OPERATOR_COUNT")
    for axis, operator_id in AXIS_OPERATOR_IDS.items():
        schema = operator_by_id[operator_id]["mechanism"]["parameter_schema"]
        require(schema["allowed_values"] == AXIS_ALLOWED_VALUES[axis], "E_R3_ALLOWED_VALUES", axis)
        require(schema["unknown_value_behavior"] == "REJECT", "E_R3_UNKNOWN_VALUE", axis)
    cp16_edge = [row for row in edges if row["content_product_type_id"] == "CP16" and row["required_component_role"] == "trigger"]
    require(len(cp16_edge) == 1 and cp16_edge[0]["component_id"] == CP16_TRIGGER_ID, "E_R3_CP16_TRIGGER")
    for path in paths:
        require(len(path["axis_realization_contracts"]) == 6, "E_R3_AXIS_COUNT")
        for contract in path["axis_realization_contracts"]:
            require(
                contract["shared_material_binding"]
                == path["shared_typed_material_contract"]["shared_material_binding"],
                "E_R3_MATERIAL_BINDING",
            )
            require(
                contract["lane_a_structural_output"]["structural_effect_digest"]
                != contract["lane_b_structural_output"]["structural_effect_digest"],
                "E_R3_STRUCTURAL_DIVERGENCE",
            )
            require(
                contract["realization_target"].startswith(
                    "/structural_realization/lane_{lane_id}/axes/"
                ),
                "E_R3_RESOLVABLE_TARGET",
            )
    require(
        all(row["component_digest"] == object_digest(row, "component_digest") for row in revised + additions),
        "E_R3_COMPONENT_DIGEST",
    )
    require(
        all(row["edge_digest"] == object_digest(row, "edge_digest") for row in edges),
        "E_R3_EDGE_DIGEST",
    )
    require(
        all(row["path_digest"] == object_digest(row, "path_digest") for row in paths),
        "E_R3_PATH_DIGEST",
    )


__all__ = [
    "ADDITION_CANDIDATES_R3_PATH",
    "FINAL_EDGE_CANDIDATES_R3_PATH",
    "REVISED_AB_R3_PATH",
    "REVISED_COMPONENTS_R3_PATH",
    "REVISED_RULES_R3_PATH",
    "TARGETED_REVIEW_PACKET_R3_PATH",
    "TARGETED_RESULT_R3_PATH",
    "build_targeted_repair_r3_documents",
    "validate_targeted_repair_r3_documents",
]
