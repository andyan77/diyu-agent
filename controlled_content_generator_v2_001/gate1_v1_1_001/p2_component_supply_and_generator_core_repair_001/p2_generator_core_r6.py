#!/usr/bin/env python3
"""R6 Gate 1 core with executable slot and path-program contracts."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

import p2_generator_core_r5 as r5


TASK_ID = r5.TASK_ID
GENERATOR_VERSION = "gate1-v1.1-p2-composable-successor-v0.4"
REQUEST_SCHEMA_VERSION = "gate1-typed-author-request-v0.4"

ExternalProviderExitAudit = r5.ExternalProviderExitAudit
Gate1ValidationError = r5.Gate1ValidationError
build_axis_structural_output = r5.build_axis_structural_output
build_component_structural_output = r5.build_component_structural_output
build_local_typed_material = r5.build_local_typed_material
canonical_json = r5.canonical_json
digest_object = r5.digest_object
evaluate_route = r5.evaluate_route
object_digest = r5.object_digest
shared_material_binding = r5.shared_material_binding
validate_typed_material = r5.validate_typed_material


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise Gate1ValidationError(f"{code}:{detail}" if detail else code)


def _as_r5_request(request: Mapping[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(dict(request))
    normalized["schema_version"] = r5.REQUEST_SCHEMA_VERSION
    normalized["generator_version"] = r5.GENERATOR_VERSION
    normalized["request_digest"] = object_digest(normalized, "request_digest")
    return normalized


def _binding_slots(binding: Mapping[str, Any], kind: str) -> list[str]:
    exact = binding.get("exact_typed_object_bindings")
    require(isinstance(exact, Mapping), "E_COMPONENT_EXACT_BINDING")
    rows = exact.get(kind)
    require(isinstance(rows, list), "E_COMPONENT_BINDING_SLOT_LIST", kind)
    require(
        all(isinstance(row, Mapping) and isinstance(row.get("slot_id"), str) for row in rows),
        "E_COMPONENT_BINDING_SLOT_OBJECT",
        kind,
    )
    return [str(row["slot_id"]) for row in rows]


def _validate_component_required_slots(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    bindings = request.get("component_bindings")
    require(isinstance(bindings, list), "E_REQUEST_COMPONENT_BINDINGS")
    for binding in bindings:
        require(isinstance(binding, Mapping), "E_COMPONENT_BINDING_OBJECT")
        component_id = str(binding.get("component_id"))
        component = component_by_id.get(component_id)
        require(component is not None, "E_COMPONENT_NOT_APPROVED", component_id)
        for kind, required_key in (
            ("input", "required_input_slots"),
            ("fact", "required_fact_slots"),
            ("authorization", "required_authorization_slots"),
        ):
            declared = list(map(str, component.get(required_key, [])))
            bound = _binding_slots(binding, kind)
            require(
                bound == declared,
                "E_COMPONENT_REQUIRED_SLOT_MISMATCH",
                f"{component_id}:{kind}",
            )
            require(
                len(bound) == len(set(bound)),
                "E_COMPONENT_REQUIRED_SLOT_DUPLICATE",
                f"{component_id}:{kind}",
            )


def _fact_slots(material: Mapping[str, Any]) -> set[str]:
    return {str(row.get("slot_id")) for row in material.get("facts", [])}


def _validate_program_fact_slots(
    axis: str,
    program: Mapping[str, Any],
    material_slots: set[str],
) -> None:
    referenced: list[str] = []
    for key in (
        "ordered_fact_slots",
        "supporting_fact_slots",
        "cue_fact_slots",
        "boundary_fact_slots",
    ):
        value = program.get(key)
        if isinstance(value, list):
            referenced.extend(map(str, value))
    if isinstance(program.get("lead_fact_slot"), str):
        referenced.append(str(program["lead_fact_slot"]))
    for action in program.get("action_nodes", []):
        if isinstance(action, Mapping):
            referenced.extend(map(str, action.get("fact_slots", [])))
    require(
        set(referenced).issubset(material_slots),
        "E_AXIS_PROGRAM_FACT_BOUNDARY",
        axis,
    )


def _validate_path_programs(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    lane = request.get("lane")
    material = request.get("typed_material")
    contracts = request.get("axis_realization_contracts")
    require(isinstance(lane, Mapping), "E_REQUEST_LANE")
    require(isinstance(material, Mapping), "E_REQUEST_MATERIAL")
    require(isinstance(contracts, list), "E_REQUEST_AXIS_CONTRACTS")
    programs = lane.get("axis_programs")
    require(isinstance(programs, Mapping), "E_REQUEST_AXIS_PROGRAMS")
    contract_by_axis = {
        str(contract.get("axis")): contract
        for contract in contracts
        if isinstance(contract, Mapping)
    }
    material_slots = _fact_slots(material)
    require(set(contract_by_axis) == set(r5.AXIS_NAMES), "E_REQUEST_SIX_AXIS_SET")
    for axis in r5.AXIS_NAMES:
        contract = contract_by_axis[axis]
        operator_id = str(contract.get("operator_component_id"))
        operator = component_by_id.get(operator_id)
        require(operator is not None, "E_REQUEST_AXIS_OPERATOR", axis)
        schema = operator.get("mechanism", {}).get("path_program_schema")
        require(isinstance(schema, Mapping), "E_AXIS_PROGRAM_SCHEMA", axis)
        required_fields = schema.get("required_fields")
        require(
            isinstance(required_fields, list)
            and all(isinstance(field, str) for field in required_fields),
            "E_AXIS_PROGRAM_REQUIRED_FIELDS",
            axis,
        )
        program = programs.get(axis)
        require(isinstance(program, Mapping), "E_AXIS_PROGRAM_OBJECT", axis)
        require(
            set(program) == set(required_fields),
            "E_AXIS_PROGRAM_FIELD_SET",
            axis,
        )
        require(
            schema.get("unknown_field_behavior") == "REJECT"
            and program.get("operator_primitive")
            == operator.get("mechanism", {}).get("operator_primitive"),
            "E_AXIS_PROGRAM_OPERATOR_PRIMITIVE",
            axis,
        )
        if axis in {"narrative_mechanism", "rhythm"}:
            require(
                program.get("information_order_dependency") == "information_order",
                "E_AXIS_PROGRAM_DEPENDENCY",
                axis,
            )
        _validate_program_fact_slots(axis, program, material_slots)


def build_author_request(
    profile: Mapping[str, Any],
    material: Mapping[str, Any],
    lane_id: str,
    approved_path: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    control_rule_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    request = r5.build_author_request(
        profile,
        material,
        lane_id,
        approved_path,
        component_by_id,
        control_rule_by_id,
    )
    request["schema_version"] = REQUEST_SCHEMA_VERSION
    request["generator_version"] = GENERATOR_VERSION
    request["request_id"] = str(request["request_id"]).replace("P2-R5-", "P2-R6-")
    request["request_digest"] = object_digest(request, "request_digest")
    return request


def validate_author_request(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    approved_path_by_profile_id: Mapping[str, Mapping[str, Any]],
    control_rule_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    require(request.get("schema_version") == REQUEST_SCHEMA_VERSION, "E_REQUEST_SCHEMA")
    require(request.get("generator_version") == GENERATOR_VERSION, "E_GENERATOR_VERSION")
    require(
        request.get("request_digest") == object_digest(dict(request), "request_digest"),
        "E_REQUEST_DIGEST",
    )
    r5.validate_author_request(
        _as_r5_request(request),
        component_by_id,
        approved_path_by_profile_id,
        control_rule_by_id,
    )
    _validate_component_required_slots(request, component_by_id)
    _validate_path_programs(request, component_by_id)


def realize_request(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    approved_path_by_profile_id: Mapping[str, Mapping[str, Any]],
    control_rule_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    validate_author_request(
        request,
        component_by_id,
        approved_path_by_profile_id,
        control_rule_by_id,
    )
    realization = r5.realize_request(
        _as_r5_request(request),
        component_by_id,
        approved_path_by_profile_id,
        control_rule_by_id,
    )
    realization["generator_version"] = GENERATOR_VERSION
    realization["request_digest"] = str(request["request_digest"])
    realization["realization_digest"] = object_digest(
        realization, "realization_digest"
    )
    return realization


__all__ = [
    "ExternalProviderExitAudit",
    "GENERATOR_VERSION",
    "Gate1ValidationError",
    "build_author_request",
    "build_axis_structural_output",
    "build_component_structural_output",
    "build_local_typed_material",
    "canonical_json",
    "digest_object",
    "evaluate_route",
    "object_digest",
    "realize_request",
    "shared_material_binding",
    "validate_author_request",
    "validate_typed_material",
]
