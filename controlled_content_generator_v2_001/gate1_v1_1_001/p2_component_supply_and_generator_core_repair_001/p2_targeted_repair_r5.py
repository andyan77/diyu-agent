#!/usr/bin/env python3
"""Build the composable-operator P2 r5 targeted-review packet."""

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
from p2_generator_core_r5 import (
    AXIS_OUTPUT_KIND_BY_AXIS,
    build_axis_structural_output,
    build_component_structural_output,
    build_local_typed_material,
    digest_object,
    shared_material_binding,
)
from p2_path_semantics_r5 import AXIS_NAMES, lane_axis_programs
from p2_targeted_repair import CP_PATH_DESIGNS
from p2_targeted_repair_r2 import (
    AXIS_OPERATOR_IDS,
    _binding_for,
    _catalog,
    _component_pool,
    _profile_binding,
    build_supply_r2,
)
from p2_targeted_repair_r3 import SELECTED_COMPONENTS
from p2_targeted_repair_r4 import (
    ADDITION_CANDIDATES_R4_PATH,
    FINAL_EDGE_CANDIDATES_R4_PATH,
    REVISED_COMPONENTS_R4_PATH,
    REVISED_RULES_R4_PATH,
)


if not __debug__:
    sys.stderr.write("P2 targeted repair r5 refuses python -O\n")
    raise SystemExit(2)


REVISED_COMPONENTS_R5_PATH = TASK_ROOT / "component/revised_component_candidates.r5.jsonl"
ADDITION_CANDIDATES_R5_PATH = TASK_ROOT / "component/necessary_addition_candidates.r5.jsonl"
REVISED_RULES_R5_PATH = TASK_ROOT / "component/revised_control_rules.r5.jsonl"
FINAL_EDGE_CANDIDATES_R5_PATH = TASK_ROOT / "component/final_edge_candidates.r5.jsonl"
REVISED_SUPPLY_R5_PATH = TASK_ROOT / "component/revised_candidate_supply_matrix.r5.yaml"
REPAIR_ASSESSMENT_R5_PATH = TASK_ROOT / "component/targeted_repair_assessment.r5.yaml"
REVISED_AB_R5_PATH = TASK_ROOT / "ab/revised_ab_path_candidates.r5.jsonl"
TARGETED_REVIEW_PACKET_R5_PATH = TASK_ROOT / "review/targeted_repair_review_packet.r5.jsonl"
TARGETED_REVIEW_JOB_R5_PATH = TASK_ROOT / "review/targeted_repair_review_job.r5.yaml"
TARGETED_RESULT_R5_PATH = TASK_ROOT / "result/p2_targeted_repair_checkpoint_result.r5.yaml"
GENERATOR_CORE_R5_PATH = TASK_ROOT / "p2_generator_core_r5.py"
PATH_SEMANTICS_R5_PATH = TASK_ROOT / "p2_path_semantics_r5.py"
GENERATOR_EVIDENCE_R5_PATH = TASK_ROOT / "p2_final_documents_r5.py"

OPERATOR_PRIMITIVE_BY_AXIS = {
    "narrative_mechanism": "LINK_INFORMATION_NODES",
    "information_order": "ORDER_EXACT_FACT_NODES",
    "visual_subject": "FOCUS_EXACT_FACT_ROLES",
    "sound_subject": "MAP_AUTHORIZED_FACT_CUES",
    "rhythm": "GROUP_INFORMATION_NODE_POSITIONS",
    "ending": "EMIT_BOUNDARY_ACTION_NODES",
}
PATH_FIELDS_BY_AXIS = {
    "narrative_mechanism": [
        "operator_primitive",
        "information_order_dependency",
        "relation_mode",
    ],
    "information_order": ["operator_primitive", "ordered_fact_slots"],
    "visual_subject": [
        "operator_primitive",
        "lead_fact_slot",
        "supporting_fact_slots",
        "focus_mode",
    ],
    "sound_subject": [
        "operator_primitive",
        "cue_fact_slots",
        "cue_source_class",
        "missing_source_behavior",
    ],
    "rhythm": [
        "operator_primitive",
        "information_order_dependency",
        "beat_node_position_groups",
        "cadence_mode",
    ],
    "ending": [
        "operator_primitive",
        "boundary_fact_slots",
        "action_nodes",
        "claims_resolved",
        "may_add_commitment",
    ],
}


def _r5_operator(row: dict[str, Any], axis: str) -> dict[str, Any]:
    updated = copy.deepcopy(row)
    updated["component_version"] = "v1.1-p2-r5-composable"
    updated["supersedes_targeted_r4_component_digest"] = updated[
        "component_digest"
    ]
    updated["mechanism"] = {
        "kind": f"small_reusable_axis_operator:{axis}",
        "function": (
            f"Execute the {axis} primitive against exact path-owned typed bindings."
        ),
        "actual_mechanism": (
            f"Apply {OPERATOR_PRIMITIVE_BY_AXIS[axis]} without owning product, "
            "profile, lane, fact, or authorization payloads."
        ),
        "operator_primitive": OPERATOR_PRIMITIVE_BY_AXIS[axis],
        "path_program_authority": "APPROVED_PROFILE_LANE_PATH_ONLY",
        "path_program_schema": {
            "required_fields": PATH_FIELDS_BY_AXIS[axis],
            "unknown_field_behavior": "REJECT",
            "profile_or_lane_payload_in_component_allowed": False,
            "component_reviewed_value_registry_allowed": False,
        },
        "execution_contract": {
            "input": "EXACT_APPROVED_PATH_PROGRAM_AND_TYPED_MATERIAL",
            "output_kind": AXIS_OUTPUT_KIND_BY_AXIS[axis],
            "output_location": f"/structural_realization/lane_{{lane_id}}/axes/{axis}",
            "selection_by_hash_token_or_field_name_allowed": False,
            "unknown_or_substituted_path_program_action": "REJECT_BEFORE_REALIZATION",
            "may_add_or_change_fact": False,
            "may_add_or_change_authorization": False,
        },
    }
    updated["activation_proposal"] = "REVISED_R5_FOR_TARGETED_TWO_REVIEW"
    updated["independent_review_state"] = "PENDING_TARGETED_R5_TWO_REVIEWS"
    updated["component_digest"] = object_digest(updated, "component_digest")
    return updated


def build_additions_r5(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    additions = [
        copy.deepcopy(row) for row in load_jsonl(root / ADDITION_CANDIDATES_R4_PATH)
    ]
    changed: list[dict[str, Any]] = []
    operator_by_id = {
        operator_id: axis for axis, operator_id in AXIS_OPERATOR_IDS.items()
    }
    for index, row in enumerate(additions):
        axis = operator_by_id.get(str(row["component_id"]))
        if axis is None:
            continue
        updated = _r5_operator(row, axis)
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
    require(len(component_ids) == len(set(component_ids)), "E_R5_COMPONENT_DUPLICATE", cp_id)
    material = build_local_typed_material(
        profile, [component_by_id[component_id] for component_id in component_ids]
    )
    return material, _catalog(material), component_ids


def _control_contract(
    profile: dict[str, Any], rules: list[dict[str, Any]]
) -> dict[str, Any]:
    bindings = [
        {
            "control_rule_id": str(row["control_rule_id"]),
            "control_rule_digest": str(row["control_rule_digest"]),
        }
        for row in rules
    ]
    return {
        "control_rule_bindings": bindings,
        "control_rule_set_digest": digest_object(bindings),
        "hard_prohibitions": {
            "profile_hard_guards": profile.get("founder_hard_guards", []),
            "no_unbound_fact": True,
            "no_unbound_authorization": True,
            "no_component_as_fact_or_authorization": True,
            "no_external_provider": True,
            "no_audience_content_in_p2": True,
        },
        "expected_output_structure": {
            "kind": "STRUCTURAL_REALIZATION_EVIDENCE_ONLY",
            "audience_title_allowed": False,
            "audience_body_allowed": False,
            "spoken_script_allowed": False,
        },
    }


def _execute_lane_axis_outputs(
    lane: dict[str, Any], material: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    execution_order = (
        "information_order",
        "narrative_mechanism",
        "visual_subject",
        "sound_subject",
        "rhythm",
        "ending",
    )
    for axis in execution_order:
        outputs[axis] = build_axis_structural_output(
            axis,
            str(lane["axes"][axis]),
            material,
            lane["axis_programs"][axis],
            outputs,
        )
    return outputs


def build_ab_paths_r5(
    state: dict[str, Any],
    component_by_id: dict[str, dict[str, Any]],
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    axis_operator_ids = set(AXIS_OPERATOR_IDS.values())
    for profile in state["profiles"]:
        cp_id = str(profile["content_product_type_id"])
        material, catalog, component_ids = _material_for_cp(profile, component_by_id)
        design = CP_PATH_DESIGNS[cp_id]
        lanes: dict[str, dict[str, Any]] = {}
        for lane_id, design_key in (("A", "a"), ("B", "b")):
            axis_values = dict(zip(AXIS_NAMES, design[design_key], strict=True))
            programs = lane_axis_programs(cp_id, lane_id)
            require(set(programs) == set(AXIS_NAMES), "E_R5_AXIS_PROGRAM_SET", cp_id)
            lanes[lane_id] = {
                "lane_id": lane_id,
                "session_id": f"P2-R5-INDEPENDENT-AUTHOR-SESSION-{cp_id}-{lane_id}",
                "session_policy": f"INDEPENDENT_SESSION_{lane_id}",
                "other_lane_visible": False,
                "component_ids": component_ids,
                "axes": axis_values,
                "axis_programs": programs,
            }
        component_bindings = [
            _binding_for(component_by_id[component_id], catalog)
            for component_id in component_ids
        ]
        binding_by_id = {
            str(binding["component_id"]): binding for binding in component_bindings
        }
        generic_contracts: list[dict[str, Any]] = []
        for component_id in component_ids:
            if component_id in axis_operator_ids:
                continue
            output = build_component_structural_output(
                component_by_id[component_id], binding_by_id[component_id], material
            )
            generic_contracts.append(
                {
                    "component_id": component_id,
                    "component_digest": component_by_id[component_id]["component_digest"],
                    "component_role": component_by_id[component_id]["component_role"],
                    "exact_binding_digest": binding_by_id[component_id]["binding_digest"],
                    "expected_structural_output": output,
                    "realization_target": (
                        f"/structural_realization/lane_{{lane_id}}/components/{component_id}"
                    ),
                    "required_for_both_lanes": True,
                }
            )
        lane_outputs = {
            lane_id: _execute_lane_axis_outputs(lane, material)
            for lane_id, lane in lanes.items()
        }
        axis_contracts: list[dict[str, Any]] = []
        for axis in AXIS_NAMES:
            operator_id = AXIS_OPERATOR_IDS[axis]
            a_output = lane_outputs["A"][axis]
            b_output = lane_outputs["B"][axis]
            require(
                a_output["structural_body_digest"]
                != b_output["structural_body_digest"],
                "E_R5_BODY_DIVERGENCE",
                f"{cp_id}:{axis}",
            )
            axis_contracts.append(
                {
                    "axis": axis,
                    "operator_component_id": operator_id,
                    "operator_component_digest": component_by_id[operator_id][
                        "component_digest"
                    ],
                    "operator_mechanism_digest": digest_object(
                        component_by_id[operator_id]["mechanism"]
                    ),
                    "operator_component_binding": binding_by_id[operator_id],
                    "lane_a_value": lanes["A"]["axes"][axis],
                    "lane_b_value": lanes["B"]["axes"][axis],
                    "lane_a_program_digest": digest_object(
                        lanes["A"]["axis_programs"][axis]
                    ),
                    "lane_b_program_digest": digest_object(
                        lanes["B"]["axis_programs"][axis]
                    ),
                    "lane_a_structural_output": a_output,
                    "lane_b_structural_output": b_output,
                    "realization_target": (
                        f"/structural_realization/lane_{{lane_id}}/axes/{axis}"
                    ),
                    "same_fact_set_must_be_preserved": True,
                    "path_program_is_authoritative": True,
                    "component_contains_profile_lane_payload": False,
                }
            )
        ending_a_count = len(
            lane_outputs["A"]["ending"]["structural_body"]["action_nodes"]
        )
        ending_b_count = len(
            lane_outputs["B"]["ending"]["structural_body"]["action_nodes"]
        )
        require(ending_a_count != ending_b_count, "E_R5_ENDING_TOPOLOGY", cp_id)
        material_binding = shared_material_binding(material)
        row: dict[str, Any] = {
            "schema_version": "v0.3",
            "task_id": TASK_ID,
            "content_product_type_id": cp_id,
            "profile_digest": profile["profile_digest"],
            "trusted_profile_contract": profile,
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
            "author_request_control_contract": _control_contract(profile, rules),
            "lane_a": lanes["A"],
            "lane_b": lanes["B"],
            "component_realization_contracts": generic_contracts,
            "axis_realization_contracts": axis_contracts,
            "observable_difference_axes": list(AXIS_NAMES),
            "observable_difference_axis_count": len(AXIS_NAMES),
            "body_level_difference_axis_count": len(AXIS_NAMES),
            "all_selected_components_have_addressable_output_contract": True,
            "structural_candidate_only": True,
            "content_quality_proven": False,
            "active": False,
            "independent_review_state": "PENDING_TARGETED_R5_TWO_REVIEWS",
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


def build_targeted_repair_r5_documents(root: Path) -> dict[Path, bytes]:
    state = source_state(root)
    state["root"] = root
    revised = load_jsonl(root / REVISED_COMPONENTS_R4_PATH)
    rules = load_jsonl(root / REVISED_RULES_R4_PATH)
    edges = load_jsonl(root / FINAL_EDGE_CANDIDATES_R4_PATH)
    additions, changed_components = build_additions_r5(root)
    component_by_id = _component_pool(root, revised, additions)
    paths = build_ab_paths_r5(state, component_by_id, rules)
    supply = build_supply_r2(state, edges)
    packet = [
        _packet_item(
            f"P2R5-COMPONENT-{row['component_id']}",
            "SMALL_REUSABLE_AXIS_OPERATOR_COMPONENT",
            row,
        )
        for row in changed_components
    ]
    packet.extend(
        _packet_item(
            f"P2R5-AB-{row['content_product_type_id']}",
            "PATH_OWNED_SEMANTIC_AB_STRUCTURAL_CAPABILITY",
            row,
        )
        for row in paths
    )
    packet.append(
        _packet_item(
            "P2R5-GENERATOR-CORE",
            "COMPOSABLE_GENERATOR_CORE_AND_TRUST_CONTRACT_REPAIR",
            {
                "path": GENERATOR_CORE_R5_PATH.as_posix(),
                "sha256": sha256_file(root / GENERATOR_CORE_R5_PATH),
                "path_semantics_source": {
                    "path": PATH_SEMANTICS_R5_PATH.as_posix(),
                    "sha256": sha256_file(root / PATH_SEMANTICS_R5_PATH),
                },
                "evidence_harness": {
                    "path": GENERATOR_EVIDENCE_R5_PATH.as_posix(),
                    "sha256": sha256_file(root / GENERATOR_EVIDENCE_R5_PATH),
                    "all_component_pointer_resolution_required": True,
                    "observable_component_effect_tamper_required": True,
                    "full_profile_path_control_binding_tamper_required": True,
                },
                "legacy_r4_core_remains_historical_non_active": True,
                "required_repairs": [
                    "MOVE_PROFILE_LANE_PROGRAMS_FROM_COMPONENTS_TO_REVIEWED_PATHS",
                    "REMOVE_CROSS_AXIS_SLOT_OWNERSHIP_DUPLICATION",
                    "MATERIALIZE_EVERY_SELECTED_COMPONENT_AS_ADDRESSABLE_STRUCTURAL_EFFECT",
                    "BIND_COMPLETE_PROFILE_PATH_SESSION_CONTROL_AND_OUTPUT_CONTRACT",
                    "EMIT_EXPLICIT_DIFFERENT_ENDING_ACTION_TOPOLOGIES",
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
        "r1_r2_r3_r4_failure_evidence_preserved": True,
        "r5_repairs": [
            "SIX_OPERATORS_ARE_SMALL_AND_CARRY_ZERO_PROFILE_LANE_PROGRAMS",
            "PROFILE_LANE_PROGRAMS_ARE_REVIEWED_PATH_BINDINGS",
            "NARRATIVE_AND_RHYTHM_REFERENCE_INFORMATION_OUTPUT_WITHOUT_SLOT_DUPLICATION",
            "ALL_SELECTED_COMPONENTS_HAVE_RESOLVABLE_STRUCTURAL_OUTPUTS",
            "FULL_TRUST_CONTRACT_REJECTS_STALE_DIGEST_RECOMPUTATION_TAMPERS",
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
        "prompt_revision": "r5",
        "checkpoint_state": "PENDING_TARGETED_R5_TWO_REVIEW",
        "review_packet_path": TARGETED_REVIEW_PACKET_R5_PATH.as_posix(),
        "review_packet_sha256": packet_sha,
        "packet_item_count": len(packet),
        "packet_item_counts": dict(Counter(row["object_type"] for row in packet)),
        "reviewer_policy": {
            "reuse_identity_isolated_primary_and_secondary_reviewers": True,
            "review_actual_payload_and_executable_outputs": True,
            "r1_r2_r3_r4_failure_records_remain_visible_and_immutable": True,
            "self_approval_allowed": False,
        },
        "activation_before_matching_approvals_allowed": False,
    }
    job["review_job_digest"] = object_digest(job, "review_job_digest")
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_TARGETED_R5_TWO_REVIEW",
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
        REVISED_COMPONENTS_R5_PATH: jsonl_bytes(revised),
        ADDITION_CANDIDATES_R5_PATH: jsonl_bytes(additions),
        REVISED_RULES_R5_PATH: jsonl_bytes(rules),
        FINAL_EDGE_CANDIDATES_R5_PATH: jsonl_bytes(edges),
        REVISED_SUPPLY_R5_PATH: yaml_bytes(supply),
        REPAIR_ASSESSMENT_R5_PATH: yaml_bytes(
            {"targeted_repair_assessment": assessment}
        ),
        REVISED_AB_R5_PATH: jsonl_bytes(paths),
        TARGETED_REVIEW_PACKET_R5_PATH: packet_bytes,
        TARGETED_REVIEW_JOB_R5_PATH: yaml_bytes(
            {"targeted_repair_review_job": job}
        ),
        TARGETED_RESULT_R5_PATH: yaml_bytes(
            {"p2_targeted_repair_checkpoint_result": result}
        ),
    }


def validate_targeted_repair_r5_documents(documents: dict[Path, bytes]) -> None:
    def rows(path: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in documents[path].decode("utf-8").splitlines()
            if line
        ]

    revised = rows(REVISED_COMPONENTS_R5_PATH)
    additions = rows(ADDITION_CANDIDATES_R5_PATH)
    rules = rows(REVISED_RULES_R5_PATH)
    edges = rows(FINAL_EDGE_CANDIDATES_R5_PATH)
    paths = rows(REVISED_AB_R5_PATH)
    packet = rows(TARGETED_REVIEW_PACKET_R5_PATH)
    result = yaml.safe_load(documents[TARGETED_RESULT_R5_PATH])[
        "p2_targeted_repair_checkpoint_result"
    ]
    require(len(revised) == 19, "E_R5_REVISED_COUNT")
    require(len(additions) == 30, "E_R5_ADDITION_COUNT")
    require(len(rules) == 8, "E_R5_RULE_COUNT")
    require(len(edges) == 85, "E_R5_EDGE_COUNT")
    require(len(paths) == 20, "E_R5_PATH_COUNT")
    require(len(packet) == 27, "E_R5_PACKET_COUNT")
    require(
        result["p2_complete"] is False and result["p3_allowed"] is False,
        "E_R5_EARLY_ACTIVATION",
    )
    require(not any(result["readiness"].values()), "E_R5_READINESS")
    operators = {
        row["component_id"]: row
        for row in additions
        if row["component_id"] in set(AXIS_OPERATOR_IDS.values())
    }
    require(len(operators) == 6, "E_R5_OPERATOR_COUNT")
    for axis, operator_id in AXIS_OPERATOR_IDS.items():
        mechanism = operators[operator_id]["mechanism"]
        require(
            mechanism["operator_primitive"] == OPERATOR_PRIMITIVE_BY_AXIS[axis],
            "E_R5_OPERATOR_PRIMITIVE",
            axis,
        )
        require(
            "reviewed_value_programs" not in json.dumps(mechanism, ensure_ascii=False)
            and "allowed_values_by_profile" not in json.dumps(
                mechanism, ensure_ascii=False
            ),
            "E_R5_OPERATOR_PAYLOAD_REGISTRY",
            axis,
        )
    for path in paths:
        require(len(path["axis_realization_contracts"]) == 6, "E_R5_AXIS_COUNT")
        require(path["body_level_difference_axis_count"] == 6, "E_R5_BODY_COUNT")
        require(
            path["trusted_profile_contract"]["profile_digest"]
            == object_digest(path["trusted_profile_contract"], "profile_digest"),
            "E_R5_PROFILE_DIGEST",
        )
        for lane_key in ("lane_a", "lane_b"):
            lane = path[lane_key]
            require(set(lane["axis_programs"]) == set(AXIS_NAMES), "E_R5_PROGRAM_SET")
            require(
                "ordered_fact_slots"
                not in lane["axis_programs"]["narrative_mechanism"],
                "E_R5_NARRATIVE_SLOT_DUPLICATION",
            )
            require(
                "fact_slots" not in lane["axis_programs"]["rhythm"],
                "E_R5_RHYTHM_SLOT_DUPLICATION",
            )
        require(
            len(path["lane_a"]["axis_programs"]["ending"]["action_nodes"])
            != len(path["lane_b"]["axis_programs"]["ending"]["action_nodes"]),
            "E_R5_ENDING_TOPOLOGY",
        )
        selected = set(path["lane_a"]["component_ids"])
        generic = {
            row["component_id"] for row in path["component_realization_contracts"]
        }
        axis_ids = {
            row["operator_component_id"] for row in path["axis_realization_contracts"]
        }
        require(generic.union(axis_ids) == selected, "E_R5_COMPONENT_OUTPUT_COVERAGE")
    require(
        all(
            row["component_digest"] == object_digest(row, "component_digest")
            for row in revised + additions
        ),
        "E_R5_COMPONENT_DIGEST",
    )
    require(
        all(row["edge_digest"] == object_digest(row, "edge_digest") for row in edges),
        "E_R5_EDGE_DIGEST",
    )
    require(
        all(row["path_digest"] == object_digest(row, "path_digest") for row in paths),
        "E_R5_PATH_DIGEST",
    )


__all__ = [
    "ADDITION_CANDIDATES_R5_PATH",
    "FINAL_EDGE_CANDIDATES_R5_PATH",
    "REVISED_AB_R5_PATH",
    "REVISED_COMPONENTS_R5_PATH",
    "REVISED_RULES_R5_PATH",
    "TARGETED_REVIEW_PACKET_R5_PATH",
    "TARGETED_RESULT_R5_PATH",
    "build_targeted_repair_r5_documents",
    "validate_targeted_repair_r5_documents",
]
