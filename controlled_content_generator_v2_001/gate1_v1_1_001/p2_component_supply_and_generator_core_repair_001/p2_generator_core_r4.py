#!/usr/bin/env python3
"""Profile-grounded, provider-free P2 r4 structural generator successor."""

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


TASK_ID = "GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001"
GENERATOR_VERSION = "gate1-v1.1-p2-semantic-successor-v0.2"
REQUEST_SCHEMA_VERSION = "gate1-typed-author-request-v0.2"

AXIS_OPERATOR_ROLE_BY_AXIS = {
    "narrative_mechanism": "narrative_mechanism_operator",
    "information_order": "information_order_operator",
    "visual_subject": "visual_subject_operator",
    "sound_subject": "sound_subject_operator",
    "rhythm": "rhythm_operator",
    "ending": "ending_operator",
}
AXIS_OUTPUT_KIND_BY_AXIS = {
    "narrative_mechanism": "NARRATIVE_SEGMENT_GRAPH",
    "information_order": "INFORMATION_NODE_SEQUENCE",
    "visual_subject": "VISUAL_FOCUS_MAP",
    "sound_subject": "SOUND_CUE_MAP",
    "rhythm": "STRUCTURAL_BEAT_MAP",
    "ending": "BOUNDARY_CLOSURE_MAP",
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


def _facts_by_slot(material: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    by_slot: dict[str, dict[str, Any]] = {}
    for fact in material.get("facts", []):
        require(isinstance(fact, dict), "E_AXIS_FACT_OBJECT")
        slot_id = str(fact.get("slot_id"))
        require(slot_id not in by_slot, "E_AXIS_FACT_SLOT_DUPLICATE", slot_id)
        by_slot[slot_id] = fact
    require(bool(by_slot), "E_AXIS_FACT_SET_EMPTY")
    return by_slot


def _fact_ref(by_slot: Mapping[str, Mapping[str, Any]], slot_id: str) -> dict[str, str]:
    require(slot_id in by_slot, "E_AXIS_PROGRAM_SLOT_MISSING", slot_id)
    fact = by_slot[slot_id]
    return {"fact_object_id": str(fact["fact_id"]), "fact_slot_id": slot_id}


def build_axis_structural_output(
    axis: str,
    value: str,
    material: Mapping[str, Any],
    program: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute an exact reviewed value program without token or hash inference."""

    require(axis in AXIS_OUTPUT_KIND_BY_AXIS, "E_AXIS_UNKNOWN", axis)
    require(program.get("axis") == axis, "E_AXIS_PROGRAM_AXIS", axis)
    require(
        program.get("reviewed_parameter_value") == value,
        "E_AXIS_PROGRAM_VALUE",
        axis,
    )
    require(
        program.get("applicable_profile_id") == material.get("profile_id"),
        "E_AXIS_PROGRAM_PROFILE",
        axis,
    )
    require(
        program.get("unknown_or_other_profile_behavior") == "REJECT",
        "E_AXIS_PROGRAM_FAIL_CLOSED",
        axis,
    )
    by_slot = _facts_by_slot(material)
    body: dict[str, Any]
    if axis == "narrative_mechanism":
        ordered_slots = list(map(str, program.get("ordered_fact_slots", [])))
        stop_slots = list(map(str, program.get("stop_boundary_slots", [])))
        require(ordered_slots and stop_slots, "E_AXIS_PROGRAM_EMPTY", axis)
        body = {
            "relation_mode": str(program["relation_mode"]),
            "segments": [
                {
                    "segment_index": index,
                    **_fact_ref(by_slot, slot_id),
                    "relation_to_next": str(program["relation_mode"]),
                }
                for index, slot_id in enumerate(ordered_slots)
            ],
            "stop_boundary_fact_refs": [
                _fact_ref(by_slot, slot_id) for slot_id in stop_slots
            ],
        }
    elif axis == "information_order":
        ordered_slots = list(map(str, program.get("ordered_fact_slots", [])))
        require(ordered_slots, "E_AXIS_PROGRAM_EMPTY", axis)
        body = {
            "ordering_is_authoritative": program.get("ordering_is_authoritative"),
            "ordered_nodes": [
                {"position": index, **_fact_ref(by_slot, slot_id)}
                for index, slot_id in enumerate(ordered_slots)
            ],
        }
    elif axis == "visual_subject":
        lead_slot = str(program.get("lead_fact_slot"))
        support_slots = list(map(str, program.get("supporting_fact_slots", [])))
        require(support_slots, "E_AXIS_PROGRAM_EMPTY", axis)
        body = {
            "focus_mode": str(program["focus_mode"]),
            "lead_fact_ref": _fact_ref(by_slot, lead_slot),
            "supporting_fact_refs": [
                _fact_ref(by_slot, slot_id) for slot_id in support_slots
            ],
            "all_facts_remain_available": True,
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
            "cue_source_class": str(program["cue_source_class"]),
            "cues": [
                {
                    "cue_index": index,
                    **_fact_ref(by_slot, slot_id),
                    "source_policy": str(program["missing_source_behavior"]),
                }
                for index, slot_id in enumerate(cue_slots)
            ],
            "authorization_object_ids": authorization_ids,
            "authorization_set_digest": shared_material_binding(material)[
                "authorization_set_digest"
            ],
        }
    elif axis == "rhythm":
        groups = program.get("beat_fact_slot_groups")
        require(isinstance(groups, list) and groups, "E_AXIS_PROGRAM_EMPTY", axis)
        flattened: list[str] = []
        beat_groups: list[dict[str, Any]] = []
        for index, group in enumerate(groups):
            require(isinstance(group, list) and group, "E_AXIS_BEAT_GROUP", axis)
            slots = list(map(str, group))
            flattened.extend(slots)
            beat_groups.append(
                {
                    "beat_index": index,
                    "fact_refs": [_fact_ref(by_slot, slot_id) for slot_id in slots],
                }
            )
        require(len(flattened) == len(set(flattened)), "E_AXIS_BEAT_DUPLICATE", axis)
        body = {
            "cadence_mode": str(program["cadence_mode"]),
            "chronology_policy": str(program["chronology_policy"]),
            "beat_groups": beat_groups,
        }
    else:
        boundary_slots = list(map(str, program.get("boundary_fact_slots", [])))
        require(boundary_slots, "E_AXIS_PROGRAM_EMPTY", axis)
        body = {
            "closure_mode": str(program["closure_mode"]),
            "boundary_fact_refs": [
                _fact_ref(by_slot, slot_id) for slot_id in boundary_slots
            ],
            "next_step_policy": str(program["next_step_policy"]),
            "claims_resolved": program.get("claims_resolved"),
            "may_add_commitment": program.get("may_add_commitment"),
        }
    document: dict[str, Any] = {
        "output_kind": AXIS_OUTPUT_KIND_BY_AXIS[axis],
        "axis": axis,
        "reviewed_parameter_value": value,
        "semantic_program_digest": digest_object(program),
        "shared_material_binding": shared_material_binding(material),
        "structural_body": body,
        "structural_body_digest": digest_object(body),
    }
    document["structural_effect_digest"] = document["structural_body_digest"]
    document["structural_output_digest"] = digest_object(document)
    return document


def _component_binding(
    component: Mapping[str, Any],
    material: Mapping[str, Any],
) -> dict[str, Any]:
    input_ids = {
        str(row["slot_id"]): str(row["input_id"])
        for row in material.get("component_inputs", [])
    }
    fact_ids = {
        str(row["slot_id"]): str(row["fact_id"])
        for row in material.get("facts", [])
    }
    authorization_ids = {
        str(row["slot_id"]): str(row["authorization_id"])
        for row in material.get("authorizations", [])
    }
    input_slots = list(map(str, component.get("required_input_slots", [])))
    fact_slots = list(map(str, component.get("required_fact_slots", [])))
    authorization_slots = list(
        map(str, component.get("required_authorization_slots", []))
    )
    require(set(input_slots).issubset(input_ids), "E_COMPONENT_INPUT_BINDING_MISSING")
    require(set(fact_slots).issubset(fact_ids), "E_COMPONENT_FACT_BINDING_MISSING")
    require(
        set(authorization_slots).issubset(authorization_ids),
        "E_COMPONENT_AUTHORIZATION_BINDING_MISSING",
    )
    return {
        "object_type": "COMPONENT_BINDING",
        "component_id": str(component["component_id"]),
        "component_digest": str(component["component_digest"]),
        "component_role": str(component["component_role"]),
        "required_input_slots": input_slots,
        "required_fact_slots": fact_slots,
        "required_authorization_slots": authorization_slots,
        "input_object_ids": [input_ids[slot_id] for slot_id in input_slots],
        "fact_object_ids": [fact_ids[slot_id] for slot_id in fact_slots],
        "authorization_object_ids": [
            authorization_ids[slot_id] for slot_id in authorization_slots
        ],
        "claim_boundary": component.get("claim_boundary"),
    }


def _lane_axes(lane: Mapping[str, Any]) -> dict[str, str]:
    excluded = {
        "component_ids",
        "lane_id",
        "session_policy",
        "other_lane_visible",
        "axis_operator_parameters",
    }
    return {
        str(key): str(value)
        for key, value in lane.items()
        if key not in excluded
    }


def build_author_request(
    profile: Mapping[str, Any],
    material: Mapping[str, Any],
    lane_id: str,
    approved_path: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    control_rule_ids: list[str],
) -> dict[str, Any]:
    validate_typed_material(material, profile)
    require(lane_id in {"A", "B"}, "E_LANE_ID")
    profile_id = str(profile["content_product_type_id"])
    require(
        approved_path.get("content_product_type_id") == profile_id,
        "E_PATH_PROFILE",
    )
    require(
        approved_path.get("path_digest") == object_digest(approved_path, "path_digest"),
        "E_PATH_DIGEST",
    )
    lane_key = "lane_a" if lane_id == "A" else "lane_b"
    lane_contract = approved_path.get(lane_key)
    require(isinstance(lane_contract, Mapping), "E_PATH_LANE")
    component_ids = list(map(str, lane_contract.get("component_ids", [])))
    bindings = [
        _component_binding(component_by_id[component_id], material)
        for component_id in component_ids
    ]
    axes = _lane_axes(lane_contract)
    request: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "task_id": TASK_ID,
        "generator_version": GENERATOR_VERSION,
        "request_id": f"P2-R4-LOCAL-{profile_id}-LANE-{lane_id}",
        "user_goal": "Validate profile-grounded structural authoring without audience content",
        "content_product_type_id": profile_id,
        "audience": "SYNTHETIC_LOCAL_TEST_AUDIENCE",
        "platform": list(profile.get("target_platforms", [])),
        "account_expression_identity": list(profile.get("target_account_roles", [])),
        "capture_conditions": list(profile.get("visual_audio_requirement_refs", [])),
        "profile_contract": dict(profile),
        "typed_material": dict(material),
        "approved_path_binding": {
            "content_product_type_id": profile_id,
            "path_digest": str(approved_path["path_digest"]),
            "lane_key": lane_key,
        },
        "lane": {
            "lane_id": lane_id,
            "session_id": f"P2-R4-INDEPENDENT-AUTHOR-SESSION-{profile_id}-{lane_id}",
            "other_lane_visible": False,
            "session_policy": lane_contract.get("session_policy"),
            "axes": axes,
            "axis_operator_parameters": dict(
                lane_contract.get("axis_operator_parameters", {})
            ),
            "axis_realization_contracts": list(
                approved_path.get("axis_realization_contracts", [])
            ),
        },
        "component_bindings": bindings,
        "control_rule_bindings": [
            {"object_type": "CONTROL_RULE_BINDING", "control_rule_id": rule_id}
            for rule_id in control_rule_ids
        ],
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
        "external_provider_allowed": False,
        "development_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "may_enter_300": False,
    }
    request["request_digest"] = object_digest(request, "request_digest")
    return request


def _validate_component_bindings(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    material = request["typed_material"]
    object_maps = {
        "input": {
            str(row["input_id"]): row for row in material.get("component_inputs", [])
        },
        "fact": {str(row["fact_id"]): row for row in material.get("facts", [])},
        "authorization": {
            str(row["authorization_id"]): row
            for row in material.get("authorizations", [])
        },
    }
    bindings = request.get("component_bindings")
    require(isinstance(bindings, list) and bindings, "E_COMPONENT_BINDING_EMPTY")
    by_id: dict[str, Mapping[str, Any]] = {}
    for binding in bindings:
        require(isinstance(binding, Mapping), "E_COMPONENT_BINDING_OBJECT")
        component_id = str(binding.get("component_id"))
        require(component_id not in by_id, "E_COMPONENT_BINDING_DUPLICATE", component_id)
        component = component_by_id.get(component_id)
        require(component is not None, "E_COMPONENT_NOT_APPROVED", component_id)
        require(
            binding.get("component_digest") == component.get("component_digest")
            and binding.get("component_role") == component.get("component_role"),
            "E_COMPONENT_IDENTITY",
            component_id,
        )
        require(
            canonical_json(binding.get("claim_boundary"))
            == canonical_json(component.get("claim_boundary")),
            "E_COMPONENT_CLAIM_BOUNDARY",
            component_id,
        )
        for kind, slot_key, object_key in (
            ("input", "required_input_slots", "input_object_ids"),
            ("fact", "required_fact_slots", "fact_object_ids"),
            ("authorization", "required_authorization_slots", "authorization_object_ids"),
        ):
            expected_slots = list(map(str, component.get(slot_key, [])))
            bound_slots = list(map(str, binding.get(slot_key, [])))
            object_ids = list(map(str, binding.get(object_key, [])))
            require(bound_slots == expected_slots, "E_COMPONENT_SLOT_CONTRACT", component_id)
            require(len(object_ids) == len(bound_slots), "E_COMPONENT_TYPED_BINDING_COUNT", component_id)
            require(
                all(object_id in object_maps[kind] for object_id in object_ids),
                "E_COMPONENT_TYPED_BINDING_OBJECT",
                component_id,
            )
            require(
                [str(object_maps[kind][object_id]["slot_id"]) for object_id in object_ids]
                == bound_slots,
                "E_COMPONENT_TYPED_BINDING_SLOT",
                component_id,
            )
        by_id[component_id] = binding
    return by_id


def validate_author_request(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    approved_path_by_profile_id: Mapping[str, Mapping[str, Any]],
) -> None:
    require(
        request.get("request_digest") == object_digest(request, "request_digest"),
        "E_REQUEST_DIGEST",
    )
    require(request.get("schema_version") == REQUEST_SCHEMA_VERSION, "E_REQUEST_SCHEMA")
    require(request.get("generator_version") == GENERATOR_VERSION, "E_GENERATOR_VERSION")
    require(request.get("external_provider_allowed") is False, "E_PROVIDER_ALLOWED")
    require(request.get("publishable") is False, "E_REQUEST_PUBLISHABLE")
    require(request.get("runtime_consumable") is False, "E_REQUEST_RUNTIME")
    require(request.get("may_enter_300") is False, "E_REQUEST_BASELINE")
    profile = request.get("profile_contract")
    material = request.get("typed_material")
    require(isinstance(profile, Mapping), "E_REQUEST_PROFILE")
    require(isinstance(material, Mapping), "E_REQUEST_MATERIAL")
    profile_id = str(request.get("content_product_type_id"))
    require(
        profile.get("content_product_type_id") == profile_id == material.get("profile_id"),
        "E_REQUEST_PROFILE_BINDING",
    )
    validate_typed_material(material, profile)
    path = approved_path_by_profile_id.get(profile_id)
    require(path is not None, "E_REQUEST_APPROVED_PATH", profile_id)
    require(path.get("path_digest") == object_digest(path, "path_digest"), "E_PATH_DIGEST")
    require(
        path.get("profile_digest") == profile.get("profile_digest"),
        "E_REQUEST_PROFILE_DIGEST",
    )
    material_contract = path.get("shared_typed_material_contract")
    require(isinstance(material_contract, Mapping), "E_PATH_MATERIAL_CONTRACT")
    material_catalog = {
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
    require(
        material_contract.get("material_id") == material.get("material_id")
        and material_contract.get("material_digest") == material.get("material_digest")
        and canonical_json(material_contract.get("typed_object_catalog"))
        == canonical_json(material_catalog)
        and material_contract.get("typed_object_catalog_digest")
        == digest_object(material_catalog)
        and material_contract.get("claim_boundary_digest")
        == digest_object(material.get("claim_boundary"))
        and canonical_json(material_contract.get("shared_material_binding"))
        == canonical_json(shared_material_binding(material)),
        "E_PATH_MATERIAL_CONTRACT",
    )
    path_binding = request.get("approved_path_binding")
    require(isinstance(path_binding, Mapping), "E_REQUEST_PATH_BINDING")
    lane = request.get("lane")
    require(isinstance(lane, Mapping), "E_REQUEST_LANE")
    lane_id = str(lane.get("lane_id"))
    require(lane_id in {"A", "B"}, "E_LANE_ID")
    lane_key = "lane_a" if lane_id == "A" else "lane_b"
    trusted_lane = path.get(lane_key)
    require(isinstance(trusted_lane, Mapping), "E_PATH_LANE")
    require(
        path_binding.get("path_digest") == path.get("path_digest")
        and path_binding.get("lane_key") == lane_key,
        "E_REQUEST_PATH_BINDING",
    )
    trusted_axes = _lane_axes(trusted_lane)
    require(
        set(trusted_axes) == set(AXIS_OPERATOR_ROLE_BY_AXIS),
        "E_REQUEST_SIX_AXIS_SET",
    )
    require(canonical_json(lane.get("axes")) == canonical_json(trusted_axes), "E_REQUEST_LANE_AUTHORITY")
    require(
        canonical_json(lane.get("axis_operator_parameters"))
        == canonical_json(trusted_lane.get("axis_operator_parameters")),
        "E_REQUEST_LANE_AUTHORITY",
    )
    require(
        canonical_json(lane.get("axis_realization_contracts"))
        == canonical_json(path.get("axis_realization_contracts")),
        "E_REQUEST_LANE_AUTHORITY",
    )
    binding_by_id = _validate_component_bindings(request, component_by_id)
    require(
        set(binding_by_id) == set(map(str, trusted_lane.get("component_ids", []))),
        "E_REQUEST_COMPONENT_SET",
    )
    expected_material_binding = shared_material_binding(material)
    contracts = lane.get("axis_realization_contracts")
    require(isinstance(contracts, list) and len(contracts) == 6, "E_REQUEST_AXIS_CONTRACTS")
    parameters = lane.get("axis_operator_parameters")
    require(isinstance(parameters, Mapping), "E_REQUEST_AXIS_PARAMETERS")
    require(
        set(map(str, parameters)) == set(AXIS_OPERATOR_ROLE_BY_AXIS)
        and {str(row.get("axis")) for row in contracts if isinstance(row, Mapping)}
        == set(AXIS_OPERATOR_ROLE_BY_AXIS),
        "E_REQUEST_SIX_AXIS_SET",
    )
    for contract in contracts:
        require(isinstance(contract, Mapping), "E_REQUEST_AXIS_CONTRACT")
        axis = str(contract.get("axis"))
        value = trusted_axes.get(axis)
        require(value is not None, "E_REQUEST_AXIS_VALUE", axis)
        designated = contract.get("lane_a_value" if lane_id == "A" else "lane_b_value")
        require(value == designated, "E_REQUEST_LANE_VALUE_NOT_DESIGNATED", axis)
        operator_id = str(contract.get("operator_component_id"))
        operator = component_by_id.get(operator_id)
        require(operator is not None, "E_REQUEST_AXIS_OPERATOR", axis)
        require(
            operator.get("component_role") == AXIS_OPERATOR_ROLE_BY_AXIS.get(axis),
            "E_REQUEST_AXIS_OPERATOR_ROLE",
            axis,
        )
        schema = operator.get("mechanism", {}).get("parameter_schema")
        require(isinstance(schema, Mapping), "E_REQUEST_AXIS_SCHEMA", axis)
        programs = schema.get("reviewed_value_programs")
        profile_programs = (
            programs.get(profile_id) if isinstance(programs, Mapping) else None
        )
        require(
            isinstance(profile_programs, Mapping) and value in profile_programs,
            "E_REQUEST_AXIS_PARAMETER_NOT_REVIEWED",
            axis,
        )
        program = profile_programs[value]
        require(isinstance(program, Mapping), "E_REQUEST_AXIS_PROGRAM", axis)
        operator_contract_binding = contract.get("operator_component_binding")
        require(
            isinstance(operator_contract_binding, Mapping),
            "E_REQUEST_AXIS_OPERATOR_BINDING",
            axis,
        )
        exact_bindings = operator_contract_binding.get("exact_typed_object_bindings")
        require(
            isinstance(exact_bindings, Mapping)
            and operator_contract_binding.get("binding_digest")
            == digest_object(exact_bindings),
            "E_REQUEST_AXIS_OPERATOR_BINDING_DIGEST",
            axis,
        )
        require(
            contract.get("operator_mechanism_digest") == digest_object(operator.get("mechanism", {}))
            and contract.get("lane_a_program_digest")
            == digest_object(profile_programs[str(contract["lane_a_value"])])
            and contract.get("lane_b_program_digest")
            == digest_object(profile_programs[str(contract["lane_b_value"])])
            and contract.get("operator_component_binding", {}).get("component_id")
            == operator_id,
            "E_REQUEST_AXIS_OPERATOR_CONTRACT",
            axis,
        )
        require(
            contract.get("allowed_values_digest")
            == digest_object(schema.get("allowed_values"))
            and contract.get("realization_target")
            == f"/structural_realization/lane_{{lane_id}}/axes/{axis}",
            "E_REQUEST_AXIS_RECEIPT_CONTRACT",
            axis,
        )
        parameter = parameters.get(axis)
        require(
            isinstance(parameter, Mapping)
            and parameter.get("operator_component_id") == operator_id
            and parameter.get("parameter_value") == value,
            "E_REQUEST_AXIS_PARAMETER_VALUE",
            axis,
        )
        require(
            canonical_json(contract.get("shared_material_binding"))
            == canonical_json(expected_material_binding),
            "E_REQUEST_AXIS_MATERIAL_BINDING",
            axis,
        )
        output_key = "lane_a_structural_output" if lane_id == "A" else "lane_b_structural_output"
        expected_output = build_axis_structural_output(axis, value, material, program)
        require(
            canonical_json(contract.get(output_key)) == canonical_json(expected_output),
            "E_REQUEST_AXIS_EXECUTION_CONTRACT",
            axis,
        )


def realize_request(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    approved_path_by_profile_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    validate_author_request(request, component_by_id, approved_path_by_profile_id)
    lane = request["lane"]
    contributions: list[dict[str, Any]] = []
    for index, binding in enumerate(request["component_bindings"]):
        component = component_by_id[str(binding["component_id"])]
        contributions.append(
            {
                "component_id": binding["component_id"],
                "component_digest": binding["component_digest"],
                "implementation_pointer": (
                    f"/structural_realization/lane_{lane['lane_id']}/"
                    f"{binding['component_role']}/{index}"
                ),
                "observable_structural_effect": {
                    "component_role": binding["component_role"],
                    "mechanism_digest": digest_object(component.get("mechanism", {})),
                    "typed_binding_digest": digest_object(
                        {
                            "input_object_ids": binding["input_object_ids"],
                            "fact_object_ids": binding["fact_object_ids"],
                            "authorization_object_ids": binding["authorization_object_ids"],
                        }
                    ),
                },
            }
        )
    axes: dict[str, dict[str, Any]] = {}
    axis_realizations: list[dict[str, Any]] = []
    for contract in lane["axis_realization_contracts"]:
        axis = str(contract["axis"])
        value = str(lane["axes"][axis])
        operator = component_by_id[str(contract["operator_component_id"])]
        program = operator["mechanism"]["parameter_schema"][
            "reviewed_value_programs"
        ][request["content_product_type_id"]][value]
        output = build_axis_structural_output(axis, value, request["typed_material"], program)
        axes[axis] = output
        axis_realizations.append(
            {
                "axis": axis,
                "axis_value": value,
                "supporting_component_ids": contract["supporting_component_ids"],
                "operator_component_id": contract["operator_component_id"],
                "operator_mechanism_digest": digest_object(operator["mechanism"]),
                "operator_binding_digest": digest_object(
                    contract["operator_component_binding"]["exact_typed_object_bindings"]
                ),
                "semantic_program_digest": output["semantic_program_digest"],
                "structural_body_digest": output["structural_body_digest"],
                "structural_output_digest": output["structural_output_digest"],
                "implementation_pointer": contract["realization_target"].format(lane_id=lane["lane_id"]),
            }
        )
    realization: dict[str, Any] = {
        "schema_version": "v0.2",
        "task_id": TASK_ID,
        "generator_version": GENERATOR_VERSION,
        "request_id": request["request_id"],
        "request_digest": request["request_digest"],
        "approved_path_binding": request["approved_path_binding"],
        "profile_id": request["content_product_type_id"],
        "lane_id": lane["lane_id"],
        "component_contributions": contributions,
        "lane_axis_realizations": axis_realizations,
        "structural_realization": {f"lane_{lane['lane_id']}": {"axes": axes}},
        "selected_component_count": len(request["component_bindings"]),
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
    "build_author_request",
    "build_axis_structural_output",
    "build_local_typed_material",
    "digest_object",
    "evaluate_route",
    "realize_request",
    "shared_material_binding",
]
