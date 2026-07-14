#!/usr/bin/env python3
"""Build R6 evidence for executable slot and path-program contracts."""

from __future__ import annotations

import copy
from typing import Any

from p2_component_model import canonical_json, object_digest
from p2_final_documents import _typed_material_catalog
from p2_generator_core_r6 import (
    Gate1ValidationError,
    build_author_request,
    build_component_structural_output,
    build_local_typed_material,
    digest_object,
    realize_request,
)


def _attempt(
    request: dict[str, Any],
    components: dict[str, dict[str, Any]],
    paths: dict[str, dict[str, Any]],
    rules: dict[str, dict[str, Any]],
) -> tuple[bool, str]:
    try:
        realize_request(request, components, paths, rules)
    except Gate1ValidationError as exc:
        return True, str(exc).split(":", 1)[0]
    return False, ""


def _pointer_output(
    realization: dict[str, Any], pointer: str
) -> dict[str, Any] | None:
    parts = [part for part in pointer.split("/") if part]
    value: Any = realization
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value if isinstance(value, dict) else None


def build_generator_evidence_r6(
    profiles: list[dict[str, Any]],
    components: list[dict[str, Any]],
    control_rules: list[dict[str, Any]],
    paths: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    component_by_id = {str(row["component_id"]): row for row in components}
    path_by_cp = {str(row["content_product_type_id"]): row for row in paths}
    rule_by_id = {str(row["control_rule_id"]): row for row in control_rules}
    requests: list[dict[str, Any]] = []
    realizations: list[dict[str, Any]] = []
    pair_results: list[dict[str, Any]] = []
    axis_body_pairs: list[dict[str, Any]] = []
    pointer_cases: list[dict[str, Any]] = []
    ablations: list[dict[str, Any]] = []
    observable_effect_tampers: list[dict[str, Any]] = []
    bound_fact_effect_cases: list[dict[str, Any]] = []
    required_slot_tampers: list[dict[str, Any]] = []
    path_program_schema_tampers: list[dict[str, Any]] = []
    path_program_tampers: list[dict[str, Any]] = []
    trust_contract_tampers: list[dict[str, Any]] = []
    first_generic_case: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for profile in profiles:
        cp_id = str(profile["content_product_type_id"])
        path = path_by_cp[cp_id]
        component_ids = list(map(str, path["lane_a"]["component_ids"]))
        material = build_local_typed_material(
            profile, [component_by_id[component_id] for component_id in component_ids]
        )
        contract = path["shared_typed_material_contract"]
        catalog = _typed_material_catalog(material)
        if (
            contract["material_id"] != material["material_id"]
            or contract["material_digest"] != material["material_digest"]
            or contract["typed_object_catalog"] != catalog
            or contract["typed_object_catalog_digest"] != digest_object(catalog)
        ):
            raise Gate1ValidationError(f"E_PATH_MATERIAL_CONTRACT:{cp_id}")
        lane_requests: dict[str, dict[str, Any]] = {}
        lane_realizations: dict[str, dict[str, Any]] = {}
        for lane_id in ("A", "B"):
            request = build_author_request(
                profile,
                material,
                lane_id,
                path,
                component_by_id,
                rule_by_id,
            )
            realization = realize_request(
                request, component_by_id, path_by_cp, rule_by_id
            )
            requests.append(request)
            realizations.append(realization)
            lane_requests[lane_id] = request
            lane_realizations[lane_id] = realization
            for contribution in realization["component_contributions"]:
                resolved = _pointer_output(
                    realization, str(contribution["implementation_pointer"])
                )
                row: dict[str, Any] = {
                    "case_id": (
                        f"POINTER-{request['request_id']}-{contribution['component_id']}"
                    ),
                    "request_id": request["request_id"],
                    "component_id": contribution["component_id"],
                    "implementation_pointer": contribution["implementation_pointer"],
                    "pointer_resolved": resolved is not None,
                    "resolved_structural_body_digest": (
                        resolved.get("structural_body_digest") if resolved else None
                    ),
                    "declared_structural_body_digest": contribution[
                        "structural_body_digest"
                    ],
                    "digest_matches": (
                        resolved is not None
                        and resolved.get("structural_body_digest")
                        == contribution["structural_body_digest"]
                    ),
                }
                row["case_digest"] = object_digest(row, "case_digest")
                pointer_cases.append(row)
            for binding in request["component_bindings"]:
                component_id = str(binding["component_id"])
                reduced = copy.deepcopy(request)
                reduced["component_bindings"] = [
                    row
                    for row in reduced["component_bindings"]
                    if row["component_id"] != component_id
                ]
                reduced["request_digest"] = object_digest(reduced, "request_digest")
                rejected, error_code = _attempt(
                    reduced, component_by_id, path_by_cp, rule_by_id
                )
                row = {
                    "case_id": f"ABLATE-{request['request_id']}-{component_id}",
                    "request_id": request["request_id"],
                    "component_id": component_id,
                    "ablation_rejected": rejected,
                    "ablation_error_code": error_code,
                    "required_output_dependency_preserved": rejected,
                }
                row["case_digest"] = object_digest(row, "case_digest")
                ablations.append(row)
                if component_id not in {
                    str(contract_row["operator_component_id"])
                    for contract_row in request["axis_realization_contracts"]
                }:
                    first_generic_case.setdefault(component_id, (request, binding))
        lane_a = lane_realizations["A"]
        lane_b = lane_realizations["B"]
        a_axis = {
            str(row["axis"]): row for row in lane_a["lane_axis_realizations"]
        }
        b_axis = {
            str(row["axis"]): row for row in lane_b["lane_axis_realizations"]
        }
        differing_axes = [
            axis
            for axis in path["observable_difference_axes"]
            if a_axis[axis]["structural_body_digest"]
            != b_axis[axis]["structural_body_digest"]
        ]
        for axis in path["observable_difference_axes"]:
            row = {
                "case_id": f"BODY-DIVERGENCE-{cp_id}-{axis}",
                "content_product_type_id": cp_id,
                "axis": axis,
                "lane_a_structural_body_digest": a_axis[axis][
                    "structural_body_digest"
                ],
                "lane_b_structural_body_digest": b_axis[axis][
                    "structural_body_digest"
                ],
                "body_level_difference": (
                    a_axis[axis]["structural_body_digest"]
                    != b_axis[axis]["structural_body_digest"]
                ),
            }
            row["case_digest"] = object_digest(row, "case_digest")
            axis_body_pairs.append(row)
        pair_row: dict[str, Any] = {
            "pair_id": f"P2-R6-PAIR-{cp_id}",
            "content_product_type_id": cp_id,
            "lane_a_request_id": lane_requests["A"]["request_id"],
            "lane_b_request_id": lane_requests["B"]["request_id"],
            "same_source_fact_authorization_boundary": (
                canonical_json(lane_requests["A"]["typed_material"])
                == canonical_json(lane_requests["B"]["typed_material"])
            ),
            "independent_session_ids": (
                lane_requests["A"]["lane"]["session_id"]
                != lane_requests["B"]["lane"]["session_id"]
            ),
            "observable_difference_axes": differing_axes,
            "observable_difference_axis_count": len(differing_axes),
            "minimum_four_axes_pass": len(differing_axes) >= 4,
            "all_six_structural_bodies_differ": len(differing_axes) == 6,
            "ending_action_topology_differs": (
                len(
                    lane_a["structural_realization"]["lane_A"]["axes"]["ending"]
                    ["structural_body"]["action_nodes"]
                )
                != len(
                    lane_b["structural_realization"]["lane_B"]["axes"]["ending"]
                    ["structural_body"]["action_nodes"]
                )
            ),
            "content_quality_proven": False,
        }
        pair_row["pair_digest"] = object_digest(pair_row, "pair_digest")
        pair_results.append(pair_row)

        base_request = lane_requests["A"]
        for axis in path["observable_difference_axes"]:
            tampered = copy.deepcopy(base_request)
            tampered["lane"]["axes"][axis] = path["lane_b"]["axes"][axis]
            tampered["lane"]["axis_programs"][axis] = copy.deepcopy(
                path["lane_b"]["axis_programs"][axis]
            )
            tampered["request_digest"] = object_digest(tampered, "request_digest")
            rejected, error_code = _attempt(
                tampered, component_by_id, path_by_cp, rule_by_id
            )
            row = {
                "case_id": f"PATH-PROGRAM-SUBSTITUTION-{cp_id}-{axis}",
                "content_product_type_id": cp_id,
                "axis": axis,
                "substitution_rejected": rejected,
                "error_code": error_code,
            }
            row["case_digest"] = object_digest(row, "case_digest")
            path_program_tampers.append(row)

        trust_cases: list[tuple[str, dict[str, Any]]] = []
        stale_profile = copy.deepcopy(base_request)
        stale_profile["profile_contract"]["founder_hard_guards"] = []
        trust_cases.append(("PROFILE_STALE_DIGEST", stale_profile))

        recomputed_profile = copy.deepcopy(base_request)
        recomputed_profile["profile_contract"]["founder_hard_guards"] = []
        recomputed_profile["profile_contract"]["profile_digest"] = object_digest(
            recomputed_profile["profile_contract"], "profile_digest"
        )
        trust_cases.append(("PROFILE_RECOMPUTED_DIGEST", recomputed_profile))

        path_profile = copy.deepcopy(base_request)
        path_profile["approved_path_binding"]["content_product_type_id"] = "CP99"
        path_profile["approved_path_binding"]["binding_digest"] = digest_object(
            {
                key: value
                for key, value in path_profile["approved_path_binding"].items()
                if key != "binding_digest"
            }
        )
        trust_cases.append(("PATH_PROFILE_ID", path_profile))

        session_id = copy.deepcopy(base_request)
        session_id["lane"]["session_id"] = "TAMPERED-SESSION"
        trust_cases.append(("SESSION_ID", session_id))

        session_policy = copy.deepcopy(base_request)
        session_policy["lane"]["session_policy"] = "SHARED_SESSION"
        trust_cases.append(("SESSION_POLICY", session_policy))

        visibility = copy.deepcopy(base_request)
        visibility["lane"]["other_lane_visible"] = True
        trust_cases.append(("OTHER_LANE_VISIBILITY", visibility))

        control = copy.deepcopy(base_request)
        control["control_rule_bindings"][0]["control_rule_digest"] = "0" * 64
        trust_cases.append(("CONTROL_RULE_DIGEST", control))

        prohibition = copy.deepcopy(base_request)
        prohibition["hard_prohibitions"]["no_unbound_fact"] = False
        trust_cases.append(("HARD_PROHIBITION", prohibition))

        output_contract = copy.deepcopy(base_request)
        output_contract["expected_output_structure"]["audience_body_allowed"] = True
        trust_cases.append(("OUTPUT_CONTRACT", output_contract))

        for case_name, tampered in trust_cases:
            tampered["request_digest"] = object_digest(tampered, "request_digest")
            rejected, error_code = _attempt(
                tampered, component_by_id, path_by_cp, rule_by_id
            )
            row = {
                "case_id": f"TRUST-{case_name}-{cp_id}",
                "content_product_type_id": cp_id,
                "tamper_class": case_name,
                "tamper_rejected": rejected,
                "error_code": error_code,
            }
            row["case_digest"] = object_digest(row, "case_digest")
            trust_contract_tampers.append(row)

        ordinary_ids = set(component_ids).difference(
            str(contract["operator_component_id"])
            for contract in path["axis_realization_contracts"]
        )
        slot_component_id = next(
            component_id
            for component_id in component_ids
            if component_id in ordinary_ids
            and component_by_id[component_id].get("required_fact_slots")
        )
        slot_path = copy.deepcopy(path)
        slot_binding = next(
            binding
            for binding in slot_path["shared_typed_material_contract"][
                "component_exact_bindings"
            ]
            if binding["component_id"] == slot_component_id
        )
        current_slots = {
            str(reference["slot_id"])
            for reference in slot_binding["exact_typed_object_bindings"]["fact"]
        }
        replacement_fact = next(
            fact
            for fact in material["facts"]
            if str(fact["slot_id"]) not in current_slots
        )
        slot_reference = slot_binding["exact_typed_object_bindings"]["fact"][0]
        slot_reference["object_id"] = replacement_fact["fact_id"]
        slot_reference["slot_id"] = replacement_fact["slot_id"]
        slot_binding["binding_digest"] = digest_object(
            slot_binding["exact_typed_object_bindings"]
        )
        slot_contract = next(
            contract
            for contract in slot_path["component_realization_contracts"]
            if contract["component_id"] == slot_component_id
        )
        slot_contract["exact_binding_digest"] = slot_binding["binding_digest"]
        slot_contract["expected_structural_output"] = build_component_structural_output(
            component_by_id[slot_component_id], slot_binding, material
        )
        slot_path["path_digest"] = object_digest(slot_path, "path_digest")
        slot_request = build_author_request(
            profile,
            material,
            "A",
            slot_path,
            component_by_id,
            rule_by_id,
        )
        slot_rejected, slot_error = _attempt(
            slot_request,
            component_by_id,
            {**path_by_cp, cp_id: slot_path},
            rule_by_id,
        )
        slot_row = {
            "case_id": f"REQUIRED-SLOT-TRUST-ROOT-{cp_id}",
            "content_product_type_id": cp_id,
            "component_id": slot_component_id,
            "recomputed_path_digest": slot_path["path_digest"],
            "tamper_rejected": slot_rejected,
            "error_code": slot_error,
        }
        slot_row["case_digest"] = object_digest(slot_row, "case_digest")
        required_slot_tampers.append(slot_row)

        missing_field_by_axis = {
            "information_order": "ordered_fact_slots",
            "narrative_mechanism": "information_order_dependency",
            "visual_subject": "focus_mode",
            "sound_subject": "missing_source_behavior",
            "rhythm": "information_order_dependency",
            "ending": "boundary_fact_slots",
        }
        for axis in path["observable_difference_axes"]:
            for mutation_class in ("UNKNOWN_FIELD", "MISSING_REQUIRED_FIELD"):
                schema_path = copy.deepcopy(path)
                program = schema_path["lane_a"]["axis_programs"][axis]
                if mutation_class == "UNKNOWN_FIELD":
                    program["unexpected_r6_field"] = "MUST_REJECT"
                else:
                    program.pop(missing_field_by_axis[axis])
                contract = next(
                    contract
                    for contract in schema_path["axis_realization_contracts"]
                    if contract["axis"] == axis
                )
                contract["lane_a_program_digest"] = digest_object(program)
                schema_path["path_digest"] = object_digest(
                    schema_path, "path_digest"
                )
                schema_request = build_author_request(
                    profile,
                    material,
                    "A",
                    schema_path,
                    component_by_id,
                    rule_by_id,
                )
                schema_rejected, schema_error = _attempt(
                    schema_request,
                    component_by_id,
                    {**path_by_cp, cp_id: schema_path},
                    rule_by_id,
                )
                schema_row = {
                    "case_id": f"PROGRAM-SCHEMA-{mutation_class}-{cp_id}-{axis}",
                    "content_product_type_id": cp_id,
                    "axis": axis,
                    "mutation_class": mutation_class,
                    "recomputed_path_digest": schema_path["path_digest"],
                    "tamper_rejected": schema_rejected,
                    "error_code": schema_error,
                }
                schema_row["case_digest"] = object_digest(
                    schema_row, "case_digest"
                )
                path_program_schema_tampers.append(schema_row)

    for component_id, (request, binding) in sorted(first_generic_case.items()):
        original = component_by_id[component_id]
        baseline_output = build_component_structural_output(
            original, binding, request["typed_material"]
        )
        tampered_component = copy.deepcopy(original)
        tampered_component["mechanism"]["actual_mechanism"] = "TAMPERED_MECHANISM"
        tampered_component["component_digest"] = object_digest(
            tampered_component, "component_digest"
        )
        tampered_binding = copy.deepcopy(binding)
        tampered_binding["component_digest"] = tampered_component["component_digest"]
        changed_output = build_component_structural_output(
            tampered_component, tampered_binding, request["typed_material"]
        )
        tampered_registry = dict(component_by_id)
        tampered_registry[component_id] = tampered_component
        rejected, error_code = _attempt(
            request, tampered_registry, path_by_cp, rule_by_id
        )
        row = {
            "case_id": f"OBSERVABLE-EFFECT-TAMPER-{component_id}",
            "component_id": component_id,
            "baseline_structural_body_digest": baseline_output[
                "structural_body_digest"
            ],
            "tampered_structural_body_digest": changed_output[
                "structural_body_digest"
            ],
            "mechanism_metadata_changed": True,
            "nonmetadata_structure_change_claimed": False,
            "registry_identity_rejected": rejected,
            "error_code": error_code,
        }
        row["case_digest"] = object_digest(row, "case_digest")
        observable_effect_tampers.append(row)
        changed_material = copy.deepcopy(request["typed_material"])
        changed_binding = copy.deepcopy(binding)
        fact_reference = changed_binding["exact_typed_object_bindings"]["fact"][0]
        source_fact = next(
            fact
            for fact in changed_material["facts"]
            if fact["fact_id"] == fact_reference["object_id"]
        )
        source_fact["fact_id"] = f"{source_fact['fact_id']}-ALTERNATE"
        fact_reference["object_id"] = source_fact["fact_id"]
        changed_binding["binding_digest"] = digest_object(
            changed_binding["exact_typed_object_bindings"]
        )
        bound_output = build_component_structural_output(
            original, changed_binding, changed_material
        )
        baseline_body = copy.deepcopy(baseline_output["structural_body"])
        bound_body = copy.deepcopy(bound_output["structural_body"])
        for body in (baseline_body, bound_body):
            body.pop("mechanism_digest", None)
            body.pop("claim_boundary_digest", None)
        bound_row = {
            "case_id": f"BOUND-FACT-EFFECT-{component_id}",
            "component_id": component_id,
            "same_required_slot_preserved": (
                fact_reference["slot_id"] == source_fact["slot_id"]
            ),
            "nonmetadata_structure_changed": (
                canonical_json(baseline_body) != canonical_json(bound_body)
            ),
        }
        bound_row["case_digest"] = object_digest(bound_row, "case_digest")
        bound_fact_effect_cases.append(bound_row)
    return {
        "requests": requests,
        "realizations": realizations,
        "pair_results": pair_results,
        "axis_body_pairs": axis_body_pairs,
        "pointer_cases": pointer_cases,
        "ablations": ablations,
        "observable_effect_tampers": observable_effect_tampers,
        "bound_fact_effect_cases": bound_fact_effect_cases,
        "required_slot_tampers": required_slot_tampers,
        "path_program_schema_tampers": path_program_schema_tampers,
        "path_program_tampers": path_program_tampers,
        "trust_contract_tampers": trust_contract_tampers,
    }


__all__ = ["build_generator_evidence_r6"]
