#!/usr/bin/env python3
"""Provider-free P2 r5 core with path-owned semantics and small operators."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from p2_generator_core import (
    ExternalProviderExitAudit,
    Gate1ValidationError,
    build_local_typed_material,
    canonical_json,
    digest_object,
    evaluate_route,
    object_digest,
    validate_typed_material,
)
from p2_path_semantics_r5 import AXIS_NAMES


TASK_ID = "GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001"
GENERATOR_VERSION = "gate1-v1.1-p2-composable-successor-v0.3"
REQUEST_SCHEMA_VERSION = "gate1-typed-author-request-v0.3"

AXIS_OPERATOR_ROLE_BY_AXIS = {
    "narrative_mechanism": "narrative_mechanism_operator",
    "information_order": "information_order_operator",
    "visual_subject": "visual_subject_operator",
    "sound_subject": "sound_subject_operator",
    "rhythm": "rhythm_operator",
    "ending": "ending_operator",
}
AXIS_OUTPUT_KIND_BY_AXIS = {
    "narrative_mechanism": "NARRATIVE_RELATION_GRAPH",
    "information_order": "INFORMATION_NODE_SEQUENCE",
    "visual_subject": "VISUAL_FOCUS_MAP",
    "sound_subject": "SOUND_CUE_MAP",
    "rhythm": "STRUCTURAL_BEAT_MAP",
    "ending": "BOUNDARY_ACTION_GRAPH",
}
ROLE_EFFECT_OPERATION = {
    "scene": "FRAME_BOUND_CONTEXT",
    "trigger": "OPEN_ON_BOUND_CONDITION",
    "observable_action": "SEQUENCE_BOUND_ACTION",
    "transition": "CONNECT_BOUND_STATES",
    "visual_beat": "MAP_BOUND_VISIBLE_STATE",
    "capture_instruction": "CAPTURE_BOUND_EVIDENCE_WINDOW",
    "professional_judgment": "MAP_EVIDENCE_TO_AUTHORIZED_SCOPE",
    "audience_facing_reasoning_move": "ORDER_BOUND_EVIDENCE_BEFORE_CONCLUSION",
    "closing": "CLOSE_AT_BOUND_EVIDENCE",
}


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise Gate1ValidationError(f"{code}:{detail}" if detail else code)


def shared_material_binding(material: Mapping[str, Any]) -> dict[str, Any]:
    facts = [
        {
            "fact_id": str(row["fact_id"]),
            "slot_id": str(row["slot_id"]),
            "fact_value_digest": str(row["fact_value_digest"]),
            "claim_boundary": str(row["claim_boundary"]),
        }
        for row in material.get("facts", [])
    ]
    authorizations = [
        {
            "authorization_id": str(row["authorization_id"]),
            "slot_id": str(row["slot_id"]),
            "subject_id": str(row["subject_id"]),
            "purpose": str(row["purpose"]),
            "scope": row["scope"],
            "validity_condition": str(row["validity_condition"]),
        }
        for row in material.get("authorizations", [])
    ]
    document = {
        "material_id": str(material.get("material_id")),
        "material_digest": str(material.get("material_digest")),
        "fact_object_ids": [row["fact_id"] for row in facts],
        "fact_set_digest": digest_object(facts),
        "authorization_object_ids": [
            row["authorization_id"] for row in authorizations
        ],
        "authorization_set_digest": digest_object(authorizations),
        "claim_boundary_digest": digest_object(material.get("claim_boundary")),
    }
    document["binding_digest"] = digest_object(document)
    return document


def _object_maps(material: Mapping[str, Any]) -> dict[str, dict[str, Mapping[str, Any]]]:
    return {
        "input": {
            str(row["input_id"]): row for row in material.get("component_inputs", [])
        },
        "fact": {str(row["fact_id"]): row for row in material.get("facts", [])},
        "authorization": {
            str(row["authorization_id"]): row
            for row in material.get("authorizations", [])
        },
    }


def _typed_refs(
    material: Mapping[str, Any], bindings: Mapping[str, Any], kind: str
) -> list[dict[str, str]]:
    maps = _object_maps(material)
    rows = bindings.get(kind)
    require(isinstance(rows, list), "E_TYPED_BINDING_LIST", kind)
    refs: list[dict[str, str]] = []
    for row in rows:
        require(isinstance(row, Mapping), "E_TYPED_BINDING_OBJECT", kind)
        object_id = str(row.get("object_id"))
        slot_id = str(row.get("slot_id"))
        source = maps[kind].get(object_id)
        require(source is not None, "E_TYPED_BINDING_OBJECT_ID", object_id)
        require(source.get("slot_id") == slot_id, "E_TYPED_BINDING_SLOT", object_id)
        refs.append({"object_id": object_id, "slot_id": slot_id})
    return refs


def build_component_structural_output(
    component: Mapping[str, Any],
    component_binding: Mapping[str, Any],
    material: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize one ordinary component as an independently addressable node."""

    component_id = str(component.get("component_id"))
    role = str(component.get("component_role"))
    require(role in ROLE_EFFECT_OPERATION, "E_COMPONENT_ROLE_EFFECT", role)
    require(
        component.get("component_digest") == object_digest(dict(component), "component_digest"),
        "E_COMPONENT_DIGEST",
        component_id,
    )
    require(
        component_binding.get("component_id") == component_id
        and component_binding.get("component_digest") == component.get("component_digest")
        and component_binding.get("component_role") == role,
        "E_COMPONENT_BINDING_IDENTITY",
        component_id,
    )
    exact = component_binding.get("exact_typed_object_bindings")
    require(isinstance(exact, Mapping), "E_COMPONENT_EXACT_BINDING", component_id)
    require(
        component_binding.get("binding_digest") == digest_object(exact),
        "E_COMPONENT_BINDING_DIGEST",
        component_id,
    )
    input_refs = _typed_refs(material, exact, "input")
    fact_refs = _typed_refs(material, exact, "fact")
    authorization_refs = _typed_refs(material, exact, "authorization")
    require(fact_refs, "E_COMPONENT_FACT_EFFECT_EMPTY", component_id)
    body = {
        "operation": ROLE_EFFECT_OPERATION[role],
        "component_role": role,
        "fact_role_nodes": [
            {"node_index": index, **reference}
            for index, reference in enumerate(fact_refs)
        ],
        "parameter_nodes": input_refs,
        "authorization_scope_nodes": authorization_refs,
        "mechanism_digest": digest_object(component.get("mechanism", {})),
        "claim_boundary_digest": digest_object(component.get("claim_boundary")),
    }
    document: dict[str, Any] = {
        "output_kind": "COMPONENT_STRUCTURAL_EFFECT",
        "component_id": component_id,
        "component_digest": str(component["component_digest"]),
        "component_binding_digest": str(component_binding["binding_digest"]),
        "structural_body": body,
        "structural_body_digest": digest_object(body),
    }
    document["structural_output_digest"] = digest_object(document)
    return document


def _facts_by_slot(material: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for fact in material.get("facts", []):
        require(isinstance(fact, Mapping), "E_AXIS_FACT_OBJECT")
        slot_id = str(fact.get("slot_id"))
        require(slot_id not in rows, "E_AXIS_FACT_SLOT_DUPLICATE", slot_id)
        rows[slot_id] = fact
    require(bool(rows), "E_AXIS_FACT_SET_EMPTY")
    return rows


def _fact_ref(by_slot: Mapping[str, Mapping[str, Any]], slot_id: str) -> dict[str, str]:
    fact = by_slot.get(slot_id)
    require(fact is not None, "E_AXIS_PROGRAM_SLOT_MISSING", slot_id)
    return {"fact_object_id": str(fact["fact_id"]), "fact_slot_id": slot_id}


def build_axis_structural_output(
    axis: str,
    value: str,
    material: Mapping[str, Any],
    program: Mapping[str, Any],
    prior_outputs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Execute one exact path-owned program with a reusable axis operator."""

    require(axis in AXIS_OUTPUT_KIND_BY_AXIS, "E_AXIS_UNKNOWN", axis)
    by_slot = _facts_by_slot(material)
    body: dict[str, Any]
    if axis == "information_order":
        slots = list(map(str, program.get("ordered_fact_slots", [])))
        require(slots, "E_AXIS_PROGRAM_EMPTY", axis)
        body = {
            "ordered_nodes": [
                {"position": index, **_fact_ref(by_slot, slot_id)}
                for index, slot_id in enumerate(slots)
            ]
        }
    elif axis == "narrative_mechanism":
        information = prior_outputs.get("information_order")
        require(information is not None, "E_AXIS_DEPENDENCY", axis)
        nodes = information["structural_body"]["ordered_nodes"]
        body = {
            "information_order_output_digest": information["structural_output_digest"],
            "relation_mode": str(program.get("relation_mode")),
            "relation_edges": [
                {
                    "from_position": index,
                    "to_position": index + 1,
                    "relation": str(program.get("relation_mode")),
                }
                for index in range(max(0, len(nodes) - 1))
            ],
        }
    elif axis == "visual_subject":
        support = list(map(str, program.get("supporting_fact_slots", [])))
        require(support, "E_AXIS_PROGRAM_EMPTY", axis)
        body = {
            "focus_mode": str(program.get("focus_mode")),
            "lead_fact_ref": _fact_ref(by_slot, str(program.get("lead_fact_slot"))),
            "supporting_fact_refs": [_fact_ref(by_slot, slot) for slot in support],
        }
    elif axis == "sound_subject":
        cue_slots = list(map(str, program.get("cue_fact_slots", [])))
        require(cue_slots, "E_AXIS_PROGRAM_EMPTY", axis)
        authorization_ids = [
            str(row["authorization_id"])
            for row in material.get("authorizations", [])
        ]
        require(authorization_ids, "E_AXIS_SOUND_AUTHORIZATION_EMPTY")
        body = {
            "cue_source_class": str(program.get("cue_source_class")),
            "cues": [
                {"cue_index": index, **_fact_ref(by_slot, slot_id)}
                for index, slot_id in enumerate(cue_slots)
            ],
            "missing_source_behavior": str(program.get("missing_source_behavior")),
            "authorization_object_ids": authorization_ids,
        }
    elif axis == "rhythm":
        information = prior_outputs.get("information_order")
        require(information is not None, "E_AXIS_DEPENDENCY", axis)
        nodes = information["structural_body"]["ordered_nodes"]
        groups = program.get("beat_node_position_groups")
        require(isinstance(groups, list) and groups, "E_AXIS_PROGRAM_EMPTY", axis)
        flattened: list[int] = []
        beat_groups: list[dict[str, Any]] = []
        for beat_index, group in enumerate(groups):
            require(isinstance(group, list) and group, "E_AXIS_BEAT_GROUP", axis)
            positions = [int(position) for position in group]
            require(
                all(0 <= position < len(nodes) for position in positions),
                "E_AXIS_BEAT_POSITION",
                axis,
            )
            flattened.extend(positions)
            beat_groups.append(
                {
                    "beat_index": beat_index,
                    "information_node_positions": positions,
                }
            )
        require(flattened == list(range(len(nodes))), "E_AXIS_BEAT_COVERAGE", axis)
        body = {
            "information_order_output_digest": information["structural_output_digest"],
            "cadence_mode": str(program.get("cadence_mode")),
            "beat_groups": beat_groups,
        }
    else:
        action_nodes = program.get("action_nodes")
        require(isinstance(action_nodes, list) and action_nodes, "E_AXIS_PROGRAM_EMPTY", axis)
        realized_actions: list[dict[str, Any]] = []
        for index, action in enumerate(action_nodes):
            require(isinstance(action, Mapping), "E_ENDING_ACTION_OBJECT")
            slots = list(map(str, action.get("fact_slots", [])))
            realized_actions.append(
                {
                    "action_index": index,
                    "action_type": str(action.get("action_type")),
                    "fact_refs": [_fact_ref(by_slot, slot_id) for slot_id in slots],
                    "closure_mode": action.get("closure_mode"),
                    "policy": action.get("policy"),
                }
            )
        body = {
            "action_nodes": realized_actions,
            "claims_resolved": program.get("claims_resolved"),
            "may_add_commitment": program.get("may_add_commitment"),
        }
    document: dict[str, Any] = {
        "output_kind": AXIS_OUTPUT_KIND_BY_AXIS[axis],
        "axis": axis,
        "reviewed_path_value": value,
        "path_program_digest": digest_object(program),
        "shared_material_binding": shared_material_binding(material),
        "structural_body": body,
        "structural_body_digest": digest_object(body),
    }
    document["structural_output_digest"] = digest_object(document)
    return document


def _lane_axes(lane: Mapping[str, Any]) -> dict[str, str]:
    axes = lane.get("axes")
    require(isinstance(axes, Mapping), "E_PATH_AXES")
    return {str(key): str(value) for key, value in axes.items()}


def build_author_request(
    profile: Mapping[str, Any],
    material: Mapping[str, Any],
    lane_id: str,
    approved_path: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    control_rule_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    validate_typed_material(material, profile)
    require(lane_id in {"A", "B"}, "E_LANE_ID")
    profile_id = str(profile.get("content_product_type_id"))
    require(
        profile.get("profile_digest") == object_digest(dict(profile), "profile_digest"),
        "E_PROFILE_DIGEST",
        profile_id,
    )
    require(
        approved_path.get("content_product_type_id") == profile_id
        and canonical_json(approved_path.get("trusted_profile_contract"))
        == canonical_json(profile),
        "E_PATH_PROFILE",
        profile_id,
    )
    lane_key = "lane_a" if lane_id == "A" else "lane_b"
    lane = approved_path.get(lane_key)
    require(isinstance(lane, Mapping), "E_PATH_LANE", lane_key)
    material_contract = approved_path.get("shared_typed_material_contract")
    require(isinstance(material_contract, Mapping), "E_PATH_MATERIAL_CONTRACT")
    component_binding_by_id = {
        str(row["component_id"]): row
        for row in material_contract.get("component_exact_bindings", [])
    }
    component_ids = list(map(str, lane.get("component_ids", [])))
    require(
        set(component_ids) == set(component_binding_by_id),
        "E_PATH_COMPONENT_BINDING_SET",
    )
    for component_id in component_ids:
        require(component_id in component_by_id, "E_COMPONENT_NOT_APPROVED", component_id)
    controls = approved_path.get("author_request_control_contract")
    require(isinstance(controls, Mapping), "E_PATH_CONTROL_CONTRACT")
    expected_control_bindings = list(controls.get("control_rule_bindings", []))
    for binding in expected_control_bindings:
        rule_id = str(binding.get("control_rule_id"))
        rule = control_rule_by_id.get(rule_id)
        require(rule is not None, "E_CONTROL_RULE_NOT_APPROVED", rule_id)
        require(
            binding.get("control_rule_digest") == rule.get("control_rule_digest")
            == object_digest(dict(rule), "control_rule_digest"),
            "E_CONTROL_RULE_DIGEST",
            rule_id,
        )
    path_binding: dict[str, Any] = {
        "content_product_type_id": profile_id,
        "profile_digest": str(profile["profile_digest"]),
        "path_digest": str(approved_path["path_digest"]),
        "lane_key": lane_key,
    }
    path_binding["binding_digest"] = digest_object(path_binding)
    request: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "task_id": TASK_ID,
        "generator_version": GENERATOR_VERSION,
        "request_id": f"P2-R5-LOCAL-{profile_id}-LANE-{lane_id}",
        "user_goal": "Validate composable structural authoring without audience content",
        "content_product_type_id": profile_id,
        "audience": "SYNTHETIC_LOCAL_TEST_AUDIENCE",
        "platform": list(profile.get("target_platforms", [])),
        "account_expression_identity": list(profile.get("target_account_roles", [])),
        "capture_conditions": list(profile.get("visual_audio_requirement_refs", [])),
        "profile_contract": dict(profile),
        "typed_material": dict(material),
        "approved_path_binding": path_binding,
        "lane": dict(lane),
        "axis_realization_contracts": list(
            approved_path.get("axis_realization_contracts", [])
        ),
        "component_realization_contracts": list(
            approved_path.get("component_realization_contracts", [])
        ),
        "component_bindings": [
            component_binding_by_id[component_id] for component_id in component_ids
        ],
        "control_rule_bindings": expected_control_bindings,
        "hard_prohibitions": controls.get("hard_prohibitions"),
        "expected_output_structure": controls.get("expected_output_structure"),
        "external_provider_allowed": False,
        "development_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "may_enter_300": False,
    }
    request["request_digest"] = object_digest(request, "request_digest")
    return request


def _material_catalog(material: Mapping[str, Any]) -> dict[str, list[dict[str, str]]]:
    return {
        "source": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["source_id"])}
            for row in material.get("sources", [])
        ],
        "input": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["input_id"])}
            for row in material.get("component_inputs", [])
        ],
        "fact": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["fact_id"])}
            for row in material.get("facts", [])
        ],
        "authorization": [
            {
                "slot_id": str(row["slot_id"]),
                "object_id": str(row["authorization_id"]),
            }
            for row in material.get("authorizations", [])
        ],
    }


def validate_author_request(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    approved_path_by_profile_id: Mapping[str, Mapping[str, Any]],
    control_rule_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    require(
        request.get("request_digest") == object_digest(dict(request), "request_digest"),
        "E_REQUEST_DIGEST",
    )
    require(request.get("schema_version") == REQUEST_SCHEMA_VERSION, "E_REQUEST_SCHEMA")
    require(request.get("generator_version") == GENERATOR_VERSION, "E_GENERATOR_VERSION")
    for key in ("external_provider_allowed", "publishable", "runtime_consumable", "may_enter_300"):
        require(request.get(key) is False, "E_REQUEST_BOUNDARY", key)
    profile = request.get("profile_contract")
    material = request.get("typed_material")
    require(isinstance(profile, Mapping), "E_REQUEST_PROFILE")
    require(isinstance(material, Mapping), "E_REQUEST_MATERIAL")
    profile_id = str(request.get("content_product_type_id"))
    require(
        profile.get("content_product_type_id") == profile_id
        and profile.get("profile_digest") == object_digest(dict(profile), "profile_digest"),
        "E_REQUEST_PROFILE_DIGEST",
        profile_id,
    )
    validate_typed_material(material, profile)
    path = approved_path_by_profile_id.get(profile_id)
    require(path is not None, "E_REQUEST_APPROVED_PATH", profile_id)
    require(path.get("path_digest") == object_digest(dict(path), "path_digest"), "E_PATH_DIGEST")
    require(
        canonical_json(path.get("trusted_profile_contract")) == canonical_json(profile),
        "E_REQUEST_TRUSTED_PROFILE",
    )
    contract = path.get("shared_typed_material_contract")
    require(isinstance(contract, Mapping), "E_PATH_MATERIAL_CONTRACT")
    catalog = _material_catalog(material)
    require(
        contract.get("material_id") == material.get("material_id")
        and contract.get("material_digest") == material.get("material_digest")
        and canonical_json(contract.get("typed_object_catalog")) == canonical_json(catalog)
        and contract.get("typed_object_catalog_digest") == digest_object(catalog)
        and contract.get("claim_boundary_digest")
        == digest_object(material.get("claim_boundary"))
        and canonical_json(contract.get("shared_material_binding"))
        == canonical_json(shared_material_binding(material)),
        "E_PATH_MATERIAL_CONTRACT",
    )
    path_binding = request.get("approved_path_binding")
    require(isinstance(path_binding, Mapping), "E_REQUEST_PATH_BINDING")
    require(
        path_binding.get("binding_digest") == digest_object(
            {key: value for key, value in path_binding.items() if key != "binding_digest"}
        ),
        "E_REQUEST_PATH_BINDING_DIGEST",
    )
    lane = request.get("lane")
    require(isinstance(lane, Mapping), "E_REQUEST_LANE")
    lane_id = str(lane.get("lane_id"))
    require(lane_id in {"A", "B"}, "E_LANE_ID")
    lane_key = "lane_a" if lane_id == "A" else "lane_b"
    trusted_lane = path.get(lane_key)
    require(isinstance(trusted_lane, Mapping), "E_PATH_LANE")
    require(
        path_binding.get("content_product_type_id") == profile_id
        and path_binding.get("profile_digest") == profile.get("profile_digest")
        and path_binding.get("path_digest") == path.get("path_digest")
        and path_binding.get("lane_key") == lane_key,
        "E_REQUEST_PATH_BINDING",
    )
    require(canonical_json(lane) == canonical_json(trusted_lane), "E_REQUEST_LANE_AUTHORITY")
    require(
        lane.get("session_id") == f"P2-R5-INDEPENDENT-AUTHOR-SESSION-{profile_id}-{lane_id}"
        and lane.get("session_policy") == f"INDEPENDENT_SESSION_{lane_id}"
        and lane.get("other_lane_visible") is False,
        "E_REQUEST_SESSION_POLICY",
    )
    trusted_bindings = list(contract.get("component_exact_bindings", []))
    require(
        canonical_json(request.get("component_bindings")) == canonical_json(trusted_bindings),
        "E_REQUEST_COMPONENT_BINDINGS",
    )
    component_ids = list(map(str, lane.get("component_ids", [])))
    require(
        component_ids == [str(row.get("component_id")) for row in trusted_bindings],
        "E_REQUEST_COMPONENT_SET",
    )
    for binding in trusted_bindings:
        component_id = str(binding.get("component_id"))
        component = component_by_id.get(component_id)
        require(component is not None, "E_COMPONENT_NOT_APPROVED", component_id)
        require(
            component.get("component_digest") == object_digest(dict(component), "component_digest")
            and binding.get("component_digest") == component.get("component_digest")
            and binding.get("component_role") == component.get("component_role"),
            "E_COMPONENT_IDENTITY",
            component_id,
        )
        exact = binding.get("exact_typed_object_bindings")
        require(isinstance(exact, Mapping), "E_COMPONENT_EXACT_BINDING", component_id)
        require(binding.get("binding_digest") == digest_object(exact), "E_COMPONENT_BINDING_DIGEST", component_id)
        for kind in ("input", "fact", "authorization"):
            _typed_refs(material, exact, kind)
    controls = path.get("author_request_control_contract")
    require(isinstance(controls, Mapping), "E_PATH_CONTROL_CONTRACT")
    require(
        canonical_json(request.get("control_rule_bindings"))
        == canonical_json(controls.get("control_rule_bindings"))
        and canonical_json(request.get("hard_prohibitions"))
        == canonical_json(controls.get("hard_prohibitions"))
        and canonical_json(request.get("expected_output_structure"))
        == canonical_json(controls.get("expected_output_structure")),
        "E_REQUEST_CONTROL_CONTRACT",
    )
    for binding in request.get("control_rule_bindings", []):
        rule_id = str(binding.get("control_rule_id"))
        rule = control_rule_by_id.get(rule_id)
        require(rule is not None, "E_CONTROL_RULE_NOT_APPROVED", rule_id)
        require(
            rule.get("control_rule_digest") == object_digest(dict(rule), "control_rule_digest")
            == binding.get("control_rule_digest"),
            "E_CONTROL_RULE_DIGEST",
            rule_id,
        )
    require(
        canonical_json(request.get("axis_realization_contracts"))
        == canonical_json(path.get("axis_realization_contracts"))
        and canonical_json(request.get("component_realization_contracts"))
        == canonical_json(path.get("component_realization_contracts")),
        "E_REQUEST_REALIZATION_CONTRACT",
    )
    axes = _lane_axes(lane)
    programs = lane.get("axis_programs")
    require(isinstance(programs, Mapping), "E_REQUEST_AXIS_PROGRAMS")
    require(set(axes) == set(programs) == set(AXIS_NAMES), "E_REQUEST_SIX_AXIS_SET")
    contracts = path.get("axis_realization_contracts")
    require(isinstance(contracts, list) and len(contracts) == 6, "E_REQUEST_AXIS_CONTRACTS")
    for axis_contract in contracts:
        require(isinstance(axis_contract, Mapping), "E_REQUEST_AXIS_CONTRACT")
        axis = str(axis_contract.get("axis"))
        operator_id = str(axis_contract.get("operator_component_id"))
        operator = component_by_id.get(operator_id)
        require(operator is not None, "E_REQUEST_AXIS_OPERATOR", axis)
        require(
            operator.get("component_role") == AXIS_OPERATOR_ROLE_BY_AXIS[axis]
            and operator.get("mechanism", {}).get("operator_primitive")
            == programs[axis].get("operator_primitive")
            and operator.get("mechanism", {}).get("path_program_authority")
            == "APPROVED_PROFILE_LANE_PATH_ONLY",
            "E_REQUEST_AXIS_OPERATOR_ROLE",
            axis,
        )
        require(
            axis_contract.get("operator_component_digest") == operator.get("component_digest")
            and axis_contract.get("operator_mechanism_digest")
            == digest_object(operator.get("mechanism", {}))
            and axis_contract.get("lane_a_program_digest")
            == digest_object(path["lane_a"]["axis_programs"][axis])
            and axis_contract.get("lane_b_program_digest")
            == digest_object(path["lane_b"]["axis_programs"][axis]),
            "E_REQUEST_AXIS_CONTRACT_BINDING",
            axis,
        )


def realize_request(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    approved_path_by_profile_id: Mapping[str, Mapping[str, Any]],
    control_rule_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    validate_author_request(
        request, component_by_id, approved_path_by_profile_id, control_rule_by_id
    )
    lane = request["lane"]
    lane_id = str(lane["lane_id"])
    axis_operator_ids = {
        str(row["operator_component_id"])
        for row in request["axis_realization_contracts"]
    }
    binding_by_id = {
        str(row["component_id"]): row for row in request["component_bindings"]
    }
    generic_outputs: dict[str, dict[str, Any]] = {}
    contributions: list[dict[str, Any]] = []
    expected_generic = {
        str(row["component_id"]): row
        for row in request["component_realization_contracts"]
    }
    for component_id in lane["component_ids"]:
        if component_id in axis_operator_ids:
            continue
        component = component_by_id[str(component_id)]
        output = build_component_structural_output(
            component, binding_by_id[str(component_id)], request["typed_material"]
        )
        contract = expected_generic.get(str(component_id))
        require(contract is not None, "E_COMPONENT_OUTPUT_CONTRACT", str(component_id))
        require(
            canonical_json(contract.get("expected_structural_output"))
            == canonical_json(output),
            "E_COMPONENT_OBSERVABLE_EFFECT",
            str(component_id),
        )
        generic_outputs[str(component_id)] = output
        contributions.append(
            {
                "component_id": str(component_id),
                "component_digest": str(component["component_digest"]),
                "implementation_pointer": (
                    f"/structural_realization/lane_{lane_id}/components/{component_id}"
                ),
                "structural_body_digest": output["structural_body_digest"],
                "structural_output_digest": output["structural_output_digest"],
            }
        )
    outputs: dict[str, dict[str, Any]] = {}
    axis_realizations: list[dict[str, Any]] = []
    contract_by_axis = {
        str(row["axis"]): row for row in request["axis_realization_contracts"]
    }
    execution_order = (
        "information_order",
        "narrative_mechanism",
        "visual_subject",
        "sound_subject",
        "rhythm",
        "ending",
    )
    for axis in execution_order:
        value = str(lane["axes"][axis])
        program = lane["axis_programs"][axis]
        output = build_axis_structural_output(
            axis, value, request["typed_material"], program, outputs
        )
        contract = contract_by_axis[axis]
        expected_key = (
            "lane_a_structural_output" if lane_id == "A" else "lane_b_structural_output"
        )
        require(
            canonical_json(contract.get(expected_key)) == canonical_json(output),
            "E_AXIS_EXPECTED_OUTPUT",
            axis,
        )
        outputs[axis] = output
        operator_id = str(contract["operator_component_id"])
        contributions.append(
            {
                "component_id": operator_id,
                "component_digest": str(component_by_id[operator_id]["component_digest"]),
                "implementation_pointer": (
                    f"/structural_realization/lane_{lane_id}/axes/{axis}"
                ),
                "structural_body_digest": output["structural_body_digest"],
                "structural_output_digest": output["structural_output_digest"],
            }
        )
        axis_realizations.append(
            {
                "axis": axis,
                "axis_value": value,
                "operator_component_id": operator_id,
                "path_program_digest": output["path_program_digest"],
                "structural_body_digest": output["structural_body_digest"],
                "structural_output_digest": output["structural_output_digest"],
                "implementation_pointer": (
                    f"/structural_realization/lane_{lane_id}/axes/{axis}"
                ),
            }
        )
    selected_ids = list(map(str, lane["component_ids"]))
    require(
        {str(row["component_id"]) for row in contributions} == set(selected_ids),
        "E_COMPONENT_REALIZATION_COVERAGE",
    )
    structural_realization = {
        f"lane_{lane_id}": {"components": generic_outputs, "axes": outputs}
    }
    realization: dict[str, Any] = {
        "schema_version": "v0.3",
        "task_id": TASK_ID,
        "generator_version": GENERATOR_VERSION,
        "request_id": request["request_id"],
        "request_digest": request["request_digest"],
        "approved_path_binding": request["approved_path_binding"],
        "profile_id": request["content_product_type_id"],
        "lane_id": lane_id,
        "component_contributions": contributions,
        "lane_axis_realizations": axis_realizations,
        "structural_realization": structural_realization,
        "selected_component_count": len(selected_ids),
        "realized_component_count": len(contributions),
        "unrealized_component_count": 0,
        "audience_title": "",
        "audience_body": [],
        "spoken_script": [],
        "development_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "may_enter_300": False,
    }
    realization["realization_digest"] = object_digest(realization, "realization_digest")
    return realization


__all__ = [
    "AXIS_OPERATOR_ROLE_BY_AXIS",
    "AXIS_OUTPUT_KIND_BY_AXIS",
    "ExternalProviderExitAudit",
    "GENERATOR_VERSION",
    "Gate1ValidationError",
    "ROLE_EFFECT_OPERATION",
    "build_author_request",
    "build_axis_structural_output",
    "build_component_structural_output",
    "build_local_typed_material",
    "digest_object",
    "evaluate_route",
    "realize_request",
    "shared_material_binding",
]
