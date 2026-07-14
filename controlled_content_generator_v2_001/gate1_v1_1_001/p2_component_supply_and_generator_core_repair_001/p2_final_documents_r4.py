#!/usr/bin/env python3
"""Build P2 r4 generator evidence against an authoritative path registry."""

from __future__ import annotations

import copy
from typing import Any

from p2_component_model import canonical_json, object_digest
from p2_final_documents import _typed_material_catalog
from p2_generator_core_r4 import (
    Gate1ValidationError,
    build_author_request,
    build_axis_structural_output,
    build_local_typed_material,
    digest_object,
    realize_request,
)


def build_generator_evidence_r4(
    profiles: list[dict[str, Any]],
    components: list[dict[str, Any]],
    control_rules: list[dict[str, Any]],
    paths: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    component_by_id = {str(row["component_id"]): row for row in components}
    path_by_cp = {str(row["content_product_type_id"]): row for row in paths}
    control_rule_ids = [str(row["control_rule_id"]) for row in control_rules]
    requests: list[dict[str, Any]] = []
    realizations: list[dict[str, Any]] = []
    pair_results: list[dict[str, Any]] = []
    axis_body_pairs: list[dict[str, Any]] = []
    lane_binding_tampers: list[dict[str, Any]] = []
    contract_tampers: list[dict[str, Any]] = []
    ablations: list[dict[str, Any]] = []
    digest_tampers: list[dict[str, Any]] = []
    first_request_by_component: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        cp_id = str(profile["content_product_type_id"])
        path = path_by_cp[cp_id]
        path_component_ids = set(path["lane_a"]["component_ids"]).union(
            path["lane_b"]["component_ids"]
        )
        material = build_local_typed_material(
            profile,
            [component_by_id[component_id] for component_id in path_component_ids],
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
                control_rule_ids,
            )
            realization = realize_request(request, component_by_id, path_by_cp)
            requests.append(request)
            realizations.append(realization)
            lane_requests[lane_id] = request
            lane_realizations[lane_id] = realization
            for binding in request["component_bindings"]:
                component_id = str(binding["component_id"])
                first_request_by_component.setdefault(component_id, request)
                reduced = copy.deepcopy(request)
                reduced["component_bindings"] = [
                    row
                    for row in reduced["component_bindings"]
                    if row["component_id"] != component_id
                ]
                reduced["request_digest"] = object_digest(reduced, "request_digest")
                try:
                    reduced_realization = realize_request(
                        reduced, component_by_id, path_by_cp
                    )
                    reduced_digest = str(reduced_realization["realization_digest"])
                    rejected = False
                    error_code = ""
                except Gate1ValidationError as exc:
                    reduced_digest = "REJECTED_BEFORE_REALIZATION"
                    rejected = True
                    error_code = str(exc).split(":", 1)[0]
                row: dict[str, Any] = {
                    "case_id": f"ABLATE-{request['request_id']}-{component_id}",
                    "request_id": request["request_id"],
                    "component_id": component_id,
                    "baseline_realization_digest": realization["realization_digest"],
                    "ablated_realization_digest": reduced_digest,
                    "ablation_rejected": rejected,
                    "ablation_error_code": error_code,
                    "implementation_changed": (
                        realization["realization_digest"] != reduced_digest
                    ),
                }
                row["case_digest"] = object_digest(row, "case_digest")
                ablations.append(row)
        lane_a_realization = lane_realizations["A"]
        lane_b_realization = lane_realizations["B"]
        a_axis = {
            str(row["axis"]): row for row in lane_a_realization["lane_axis_realizations"]
        }
        b_axis = {
            str(row["axis"]): row for row in lane_b_realization["lane_axis_realizations"]
        }
        differing_axes = [
            axis
            for axis in path["observable_difference_axes"]
            if a_axis[axis]["structural_body_digest"]
            != b_axis[axis]["structural_body_digest"]
        ]
        for axis in path["observable_difference_axes"]:
            pair: dict[str, Any] = {
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
            pair["case_digest"] = object_digest(pair, "case_digest")
            axis_body_pairs.append(pair)
        pair_row: dict[str, Any] = {
            "pair_id": f"P2-R4-PAIR-{cp_id}",
            "content_product_type_id": cp_id,
            "lane_a_request_id": lane_requests["A"]["request_id"],
            "lane_b_request_id": lane_requests["B"]["request_id"],
            "same_material_digest": (
                lane_requests["A"]["typed_material"]["material_digest"]
                == lane_requests["B"]["typed_material"]["material_digest"]
            ),
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
            "content_quality_proven": False,
        }
        pair_row["pair_digest"] = object_digest(pair_row, "pair_digest")
        pair_results.append(pair_row)

        base_request = lane_requests["A"]
        for contract_row in path["axis_realization_contracts"]:
            axis = str(contract_row["axis"])
            tampered = copy.deepcopy(base_request)
            alternate_value = str(contract_row["lane_b_value"])
            tampered["lane"]["axes"][axis] = alternate_value
            tampered["lane"]["axis_operator_parameters"][axis][
                "parameter_value"
            ] = alternate_value
            operator = component_by_id[str(contract_row["operator_component_id"])]
            program = operator["mechanism"]["parameter_schema"][
                "reviewed_value_programs"
            ][cp_id][alternate_value]
            tampered_contract = next(
                row
                for row in tampered["lane"]["axis_realization_contracts"]
                if row["axis"] == axis
            )
            tampered_contract["lane_a_structural_output"] = (
                build_axis_structural_output(
                    axis, alternate_value, tampered["typed_material"], program
                )
            )
            tampered["request_digest"] = object_digest(tampered, "request_digest")
            rejected = False
            error_code = ""
            try:
                realize_request(tampered, component_by_id, path_by_cp)
            except Gate1ValidationError as exc:
                rejected = True
                error_code = str(exc).split(":", 1)[0]
            tamper_row: dict[str, Any] = {
                "case_id": f"KNOWN-ENUM-SUBSTITUTION-{cp_id}-{axis}",
                "content_product_type_id": cp_id,
                "axis": axis,
                "designated_value": contract_row["lane_a_value"],
                "substituted_reviewed_value": alternate_value,
                "substitution_rejected": rejected,
                "error_code": error_code,
            }
            tamper_row["case_digest"] = object_digest(tamper_row, "case_digest")
            lane_binding_tampers.append(tamper_row)
        for lane_id, original_request in lane_requests.items():
            tamper_cases: list[tuple[str, dict[str, Any]]] = []
            missing_axis = copy.deepcopy(original_request)
            missing_axis["lane"]["axis_realization_contracts"] = missing_axis[
                "lane"
            ]["axis_realization_contracts"][:-1]
            tamper_cases.append(("MISSING_AXIS_CONTRACT", missing_axis))

            component_boundary = copy.deepcopy(original_request)
            component_boundary["component_bindings"][0][
                "claim_boundary"
            ] = "TAMPERED_BOUNDARY"
            tamper_cases.append(("COMPONENT_CLAIM_BOUNDARY", component_boundary))

            material_boundary = copy.deepcopy(original_request)
            material_boundary["typed_material"][
                "claim_boundary"
            ] = "TAMPERED_BOUNDARY"
            material_boundary["typed_material"]["material_digest"] = object_digest(
                material_boundary["typed_material"], "material_digest"
            )
            tamper_cases.append(("MATERIAL_CLAIM_BOUNDARY", material_boundary))

            binding_digest = copy.deepcopy(original_request)
            binding_digest["lane"]["axis_realization_contracts"][0][
                "operator_component_binding"
            ]["binding_digest"] = "0" * 64
            tamper_cases.append(("OPERATOR_BINDING_DIGEST", binding_digest))

            enum_digest = copy.deepcopy(original_request)
            enum_digest["lane"]["axis_realization_contracts"][0][
                "allowed_values_digest"
            ] = "0" * 64
            tamper_cases.append(("ALLOWED_VALUES_DIGEST", enum_digest))

            target = copy.deepcopy(original_request)
            target["lane"]["axis_realization_contracts"][0][
                "realization_target"
            ] = "/untrusted/target"
            tamper_cases.append(("REALIZATION_TARGET", target))

            for case_name, tampered in tamper_cases:
                tampered["request_digest"] = object_digest(
                    tampered, "request_digest"
                )
                rejected = False
                error_code = ""
                try:
                    realize_request(tampered, component_by_id, path_by_cp)
                except Gate1ValidationError as exc:
                    rejected = True
                    error_code = str(exc).split(":", 1)[0]
                row = {
                    "case_id": f"{case_name}-{cp_id}-{lane_id}",
                    "content_product_type_id": cp_id,
                    "lane_id": lane_id,
                    "tamper_class": case_name,
                    "tamper_rejected": rejected,
                    "error_code": error_code,
                }
                row["case_digest"] = object_digest(row, "case_digest")
                contract_tampers.append(row)
    for component_id, request in sorted(first_request_by_component.items()):
        tampered = copy.deepcopy(request)
        binding = next(
            row
            for row in tampered["component_bindings"]
            if row["component_id"] == component_id
        )
        binding["component_digest"] = "0" * 64
        tampered["request_digest"] = object_digest(tampered, "request_digest")
        rejected = False
        error_code = ""
        try:
            realize_request(tampered, component_by_id, path_by_cp)
        except Gate1ValidationError as exc:
            rejected = True
            error_code = str(exc).split(":", 1)[0]
        row = {
            "case_id": f"TAMPER-COMPONENT-DIGEST-{component_id}",
            "component_id": component_id,
            "tamper_rejected": rejected,
            "error_code": error_code,
        }
        row["case_digest"] = object_digest(row, "case_digest")
        digest_tampers.append(row)
    return {
        "requests": requests,
        "realizations": realizations,
        "pair_results": pair_results,
        "axis_body_pairs": axis_body_pairs,
        "lane_binding_tampers": lane_binding_tampers,
        "contract_tampers": contract_tampers,
        "ablations": ablations,
        "digest_tampers": digest_tampers,
    }


__all__ = ["build_generator_evidence_r4"]
