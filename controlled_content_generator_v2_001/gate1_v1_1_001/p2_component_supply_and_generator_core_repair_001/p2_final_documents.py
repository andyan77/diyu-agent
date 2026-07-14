#!/usr/bin/env python3
"""Build P2 closeout documents from signed reviews and frozen inputs."""

from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any

from p2_component_model import TASK_ID, canonical_json, object_digest, sha256_file
from p2_generator_core import (
    GENERATOR_VERSION,
    ExternalProviderExitAudit,
    Gate1ValidationError,
    build_author_request,
    build_local_typed_material,
    digest_object,
    evaluate_route,
    realize_request,
)


def approved_packet_ids(combined: list[dict[str, Any]]) -> set[str]:
    return {
        str(row["packet_item_id"])
        for row in combined
        if row.get("combined_disposition") == "APPROVE"
    }


def _typed_material_catalog(material: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    return {
        "source": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["source_id"])}
            for row in material["sources"]
        ],
        "input": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["input_id"])}
            for row in material["component_inputs"]
        ],
        "fact": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["fact_id"])}
            for row in material["facts"]
        ],
        "authorization": [
            {
                "slot_id": str(row["slot_id"]),
                "object_id": str(row["authorization_id"]),
            }
            for row in material["authorizations"]
        ],
    }


def build_review_closeout(
    combined: list[dict[str, Any]],
    primary_summary: dict[str, Any],
    secondary_summary: dict[str, Any],
) -> dict[str, Any]:
    counts = Counter(row["combined_disposition"] for row in combined)
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "reviewed_checkpoint_commit": "c37a894930025aac99db18a055d5a79294fa89dc",
        "review_packet_sha256": "67751ab60e6ee8e227c4aaff3dccd4c7f3c5d027ceda2f910f4ea1a600231095",
        "reviewer_identities": {
            "primary": primary_summary,
            "secondary": secondary_summary,
        },
        "reviewer_identity_collision": (
            primary_summary["reviewer_identity_id"]
            == secondary_summary["reviewer_identity_id"]
            or primary_summary["reviewer_instance_or_session_id"]
            == secondary_summary["reviewer_instance_or_session_id"]
        ),
        "executor_self_approval_count": 0,
        "record_count_per_review": 244,
        "combined_decision_counts": dict(sorted(counts.items())),
        "unresolved_disagreement_count": sum(
            row.get("requires_targeted_adjudication") is True for row in combined
        ),
    }
    document["review_closeout_digest"] = object_digest(
        document, "review_closeout_digest"
    )
    return {"independent_component_review_closeout": document}


def build_active_components(
    components: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    combined: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    approved = approved_packet_ids(combined)
    approved_edges = [edge for edge in edges if f"P2-{edge['edge_id']}" in approved]
    active_ids = {str(edge["component_id"]) for edge in approved_edges}
    rows: list[dict[str, Any]] = []
    for candidate in components:
        component_id = str(candidate["component_id"])
        if component_id not in active_ids:
            continue
        if f"P2-COMPONENT-{component_id}" not in approved:
            continue
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_component_digest"] = row.pop("component_digest")
        row["active"] = True
        row["new_generator_consumable"] = True
        row["activation_basis"] = "MATCHING_TWO_INDEPENDENT_APPROVALS_AND_APPROVED_EDGE"
        row["review_packet_item_id"] = f"P2-COMPONENT-{component_id}"
        row["candidate_payload_path"] = (
            f"component/successor_component_candidates.v0.1.jsonl#{component_id}"
        )
        row["independent_review_state"] = "APPROVED_BY_TWO_REVIEWS"
        row["readiness"] = {
            "generation_eligible": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        }
        row["component_digest"] = object_digest(row, "component_digest")
        rows.append(row)
    return rows


def build_active_edge_lifecycle(
    approved_edges: list[dict[str, Any]],
    active_component_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for edge in approved_edges:
        component_id = str(edge["component_id"])
        component = active_component_by_id.get(component_id)
        if component is None:
            continue
        row = copy.deepcopy(edge)
        row["reviewed_candidate_edge_digest"] = row.pop("edge_digest")
        row["reviewed_candidate_component_digest"] = row["component_digest"]
        row["component_digest"] = component["component_digest"]
        row["active"] = True
        row["review_packet_item_id"] = f"P2-{edge['edge_id']}"
        row["activation_basis"] = "MATCHING_TWO_INDEPENDENT_APPROVALS"
        row["independent_review_state"] = "APPROVED_BY_TWO_REVIEWS"
        row["edge_digest"] = object_digest(row, "edge_digest")
        rows.append(row)
    return rows


def build_active_control_rules(
    control_rules: list[dict[str, Any]],
    combined: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    approved = approved_packet_ids(combined)
    rows: list[dict[str, Any]] = []
    for candidate in control_rules:
        rule_id = str(candidate["control_rule_id"])
        if f"P2-CONTROL-{rule_id}" not in approved:
            continue
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_control_rule_digest"] = row.pop("control_rule_digest")
        row["active"] = True
        row["independent_review_state"] = "APPROVED_BY_TWO_REVIEWS"
        row["activation_basis"] = "MATCHING_TWO_INDEPENDENT_APPROVALS"
        row["review_packet_item_id"] = f"P2-CONTROL-{rule_id}"
        row["contributes_component_supply"] = False
        row["may_write_audience_surface"] = False
        row["control_rule_digest"] = object_digest(row, "control_rule_digest")
        rows.append(row)
    return rows


def build_approved_supply(
    profiles: list[dict[str, Any]],
    active_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for profile in profiles:
        cp_id = str(profile["content_product_type_id"])
        roles: list[dict[str, Any]] = []
        for requirement in profile["required_component_roles"]:
            role = str(requirement["role"])
            matches = [
                edge
                for edge in active_edges
                if edge["content_product_type_id"] == cp_id
                and edge["required_component_role"] == role
            ]
            roles.append(
                {
                    "role": role,
                    "minimum": requirement["min_count"],
                    "approved_count": len(matches),
                    "approved_component_ids": [
                        edge["component_id"] for edge in matches
                    ],
                    "complete": len(matches) >= requirement["min_count"],
                }
            )
        entries.append(
            {
                "content_product_type_id": cp_id,
                "approved_supply_complete": all(row["complete"] for row in roles),
                "required_roles": roles,
            }
        )
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "approved_complete_profile_count": sum(
            row["approved_supply_complete"] for row in entries
        ),
        "entries": entries,
    }
    document["matrix_digest"] = object_digest(document, "matrix_digest")
    return {"approved_component_supply_matrix": document}


def build_active_ab_paths(
    paths: list[dict[str, Any]],
    active_component_ids: set[str],
    combined: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    approved = approved_packet_ids(combined)
    rows: list[dict[str, Any]] = []
    for path in paths:
        cp_id = str(path["content_product_type_id"])
        if f"P2-AB-{cp_id}" not in approved:
            continue
        lane_ids = set(path["lane_a"]["component_ids"]).union(
            path["lane_b"]["component_ids"]
        )
        if not lane_ids.issubset(active_component_ids):
            continue
        row = copy.deepcopy(path)
        row["reviewed_candidate_path_digest"] = row.pop("path_digest")
        row["active"] = True
        row["independent_review_state"] = "APPROVED_BY_TWO_REVIEWS"
        row["structural_candidate_only"] = False
        row["p2_structural_validation_only"] = True
        row["path_digest"] = object_digest(row, "path_digest")
        rows.append(row)
    return rows


def build_generator_contract() -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "generator_version": GENERATOR_VERSION,
        "scope": "P2_LOCAL_STRUCTURAL_VALIDATION_ONLY",
        "single_current_entrypoint": (
            "controlled_content_generator_v2_001/gate1_v1_1_001/"
            "p2_component_supply_and_generator_core_repair_001/"
            "run_p2_component_supply_and_generator_core_repair.py"
        ),
        "typed_input_classes": [
            "SOURCE_OBJECT",
            "FACT_OBJECT",
            "AUTHORIZATION_OBJECT",
            "COMPONENT_BINDING",
            "CONTROL_RULE_BINDING",
        ],
        "field_name_or_path_guessing_allowed": False,
        "first_match_binding_allowed": False,
        "generator_may_write_composition_plan": False,
        "composition_plan_owner": "ORCH",
        "external_provider_allowed": False,
        "audience_content_generation_allowed_in_p2": False,
        "review_resume_policy": "APPEND_ONLY_BATCH_RECORDS_WITH_STABLE_IDS",
        "readiness": {
            "generator_qualified": False,
            "generation_allowed": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        },
    }
    document["contract_digest"] = object_digest(document, "contract_digest")
    return {"gate1_generator_contract": document}


def build_generator_registry(
    root: Path,
    active_components: list[dict[str, Any]],
    active_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    task_root = Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001"
    )
    core_path = task_root / "p2_generator_core.py"
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "current_generator_entrypoint_count": 1,
        "generator_version": GENERATOR_VERSION,
        "entrypoint": (
            task_root / "run_p2_component_supply_and_generator_core_repair.py"
        ).as_posix(),
        "core_module": {
            "path": core_path.as_posix(),
            "sha256": sha256_file(root / core_path),
        },
        "active_component_count": len(active_components),
        "active_edge_count": len(active_edges),
        "historical_generator_entrypoints_consumed": [],
        "external_provider_exit": "ExternalProviderExitAudit.dispatch",
        "generator_qualified": False,
        "runtime_ready": False,
        "production_ready": False,
    }
    document["registry_digest"] = object_digest(document, "registry_digest")
    return {"active_gate1_generator_registry": document}


def build_generator_evidence(
    profiles: list[dict[str, Any]],
    components: list[dict[str, Any]],
    control_rules: list[dict[str, Any]],
    active_paths: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    component_by_id = {row["component_id"]: row for row in components}
    path_by_cp = {row["content_product_type_id"]: row for row in active_paths}
    control_rule_ids = [row["control_rule_id"] for row in control_rules]
    requests: list[dict[str, Any]] = []
    realizations: list[dict[str, Any]] = []
    pair_results: list[dict[str, Any]] = []
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
        material_contract = path["shared_typed_material_contract"]
        material_catalog = _typed_material_catalog(material)
        if (
            material_contract["material_id"] != material["material_id"]
            or material_contract["material_digest"] != material["material_digest"]
            or material_contract["typed_object_catalog"] != material_catalog
            or material_contract["typed_object_catalog_digest"]
            != digest_object(material_catalog)
        ):
            raise Gate1ValidationError(f"E_PATH_MATERIAL_CONTRACT:{cp_id}")
        lane_requests: dict[str, dict[str, Any]] = {}
        lane_realizations: dict[str, dict[str, Any]] = {}
        for lane_id, lane_key in (("A", "lane_a"), ("B", "lane_b")):
            lane_path = copy.deepcopy(path[lane_key])
            lane_path["axis_realization_contracts"] = path[
                "axis_realization_contracts"
            ]
            request = build_author_request(
                profile,
                material,
                lane_id,
                lane_path,
                component_by_id,
                control_rule_ids,
            )
            realization = realize_request(request, component_by_id)
            requests.append(request)
            realizations.append(realization)
            lane_requests[lane_id] = request
            lane_realizations[lane_id] = realization
            for binding in request["component_bindings"]:
                first_request_by_component.setdefault(binding["component_id"], request)
                reduced = copy.deepcopy(request)
                reduced["component_bindings"] = [
                    row
                    for row in reduced["component_bindings"]
                    if row["component_id"] != binding["component_id"]
                ]
                reduced["request_digest"] = object_digest(reduced, "request_digest")
                ablation_rejected = False
                ablation_error_code = ""
                try:
                    reduced_realization = realize_request(reduced, component_by_id)
                    reduced_digest = reduced_realization["realization_digest"]
                except Gate1ValidationError as exc:
                    ablation_rejected = True
                    ablation_error_code = str(exc).split(":", 1)[0]
                    reduced_digest = "REJECTED_BEFORE_REALIZATION"
                ablation: dict[str, Any] = {
                    "case_id": f"ABLATE-{request['request_id']}-{binding['component_id']}",
                    "request_id": request["request_id"],
                    "component_id": binding["component_id"],
                    "baseline_realization_digest": realization["realization_digest"],
                    "ablated_realization_digest": reduced_digest,
                    "ablation_rejected": ablation_rejected,
                    "ablation_error_code": ablation_error_code,
                    "implementation_changed": (
                        realization["realization_digest"]
                        != reduced_digest
                    ),
                }
                ablation["case_digest"] = object_digest(ablation, "case_digest")
                ablations.append(ablation)
        lane_a = lane_requests["A"]
        lane_b = lane_requests["B"]
        lane_a_realization = lane_realizations["A"]
        lane_b_realization = lane_realizations["B"]
        lane_a_axis_values = {
            row["axis"]: row["axis_value"]
            for row in lane_a_realization["lane_axis_realizations"]
        }
        lane_b_axis_values = {
            row["axis"]: row["axis_value"]
            for row in lane_b_realization["lane_axis_realizations"]
        }
        axes = path["observable_difference_axes"]
        differing = [
            axis
            for axis in axes
            if lane_a_axis_values.get(axis) != lane_b_axis_values.get(axis)
        ]
        pair: dict[str, Any] = {
            "pair_id": f"P2-PAIR-{cp_id}",
            "content_product_type_id": cp_id,
            "lane_a_request_id": lane_a["request_id"],
            "lane_b_request_id": lane_b["request_id"],
            "same_material_digest": (
                lane_a["typed_material"]["material_digest"]
                == lane_b["typed_material"]["material_digest"]
            ),
            "same_source_fact_authorization_boundary": (
                canonical_json(lane_a["typed_material"])
                == canonical_json(lane_b["typed_material"])
            ),
            "independent_session_ids": (
                lane_a["lane"]["session_id"] != lane_b["lane"]["session_id"]
            ),
            "observable_difference_axes": differing,
            "observable_difference_axis_count": len(differing),
            "minimum_four_axes_pass": len(differing) >= 4,
            "lane_a_axis_realization_digest": digest_object(
                lane_a_realization["lane_axis_realizations"]
            ),
            "lane_b_axis_realization_digest": digest_object(
                lane_b_realization["lane_axis_realizations"]
            ),
            "content_quality_proven": False,
        }
        pair["pair_digest"] = object_digest(pair, "pair_digest")
        pair_results.append(pair)
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
            realize_request(tampered, component_by_id)
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
        "ablations": ablations,
        "digest_tampers": digest_tampers,
    }


def build_route_evidence(
    route_inputs: list[dict[str, Any]],
    gold_answers: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    profile_by_id = {row["content_product_type_id"]: row for row in profiles}
    gold_by_case = {row["case_id"]: row for row in gold_answers}
    actuals = [
        evaluate_route(row, profile_by_id[row["profile_id"]]) for row in route_inputs
    ]
    comparisons: list[dict[str, Any]] = []
    for actual in actuals:
        gold = gold_by_case[actual["case_id"]]
        row: dict[str, Any] = {
            "case_id": actual["case_id"],
            "actual_route_result_digest": actual["route_result_digest"],
            "gold_answer_digest": gold["gold_answer_digest"],
            "actual_primary_action": actual["actual_primary_action"],
            "gold_primary_action": gold["gold_primary_action"],
            "primary_action_matches_gold": (
                actual["actual_primary_action"] == gold["gold_primary_action"]
            ),
            "actual_primary_reason_category": actual["actual_primary_reason_category"],
            "gold_reason_code": gold["gold_reason_code"],
            "primary_reason_matches_gold": (
                actual["actual_primary_reason_category"] == gold["gold_reason_code"]
            ),
        }
        row["comparison_digest"] = object_digest(row, "comparison_digest")
        comparisons.append(row)
    return actuals, comparisons


def build_provider_audit() -> dict[str, Any]:
    audit = ExternalProviderExitAudit()
    blocked = False
    error_code = ""
    try:
        audit.dispatch("SYNTHETIC_NEGATIVE_TEST_PROVIDER", "0" * 64)
    except Gate1ValidationError as exc:
        blocked = True
        error_code = str(exc).split(":", 1)[0]
    document = audit.summary()
    document["negative_dispatch_test"] = {
        "synthetic_test_only": True,
        "blocked_before_network_dispatch": blocked,
        "error_code": error_code,
    }
    document["audit_digest"] = object_digest(document, "audit_digest")
    return {"external_provider_exit_audit": document}
