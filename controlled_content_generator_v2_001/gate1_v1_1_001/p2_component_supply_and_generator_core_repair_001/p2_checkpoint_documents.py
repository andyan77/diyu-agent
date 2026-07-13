from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from p2_component_model import (
    AB_PATH,
    ADDITION_PATH,
    BASELINE_COMMIT,
    COMPAT_PATH,
    COMPONENT_CANDIDATES_PATH,
    COMPONENT_SOURCE_PATH,
    CONTROL_RULES_PATH,
    CURRENT_CHECKER_AFTER_SHA256,
    CURRENT_CHECKER_PATH,
    CURRENT_OWNER_PATH,
    EDGE_PATH,
    P1B_CHECKER_AS_BUILT_SHA256,
    P1B_MATERIALIZER_AFTER_SHA256,
    P1B_MATERIALIZER_BEFORE_SHA256,
    P1B_MATERIALIZER_PATH,
    P1B_OWNER_AS_BUILT_SHA256,
    P1B_RESULT_PATH,
    P1B_ROUTE_GOLD_PATH,
    PROFILE_PATH,
    READY_KEYS,
    RESULT_PATH,
    REVIEW_JOB_PATH,
    REVIEW_PACKET_PATH,
    SUCCESSOR_PATH,
    STANDARD_PATH,
    SUPPLY_PATH,
    TASK_ID,
    TASK_ROOT,
    apply_activation_proposals,
    build_ab_paths,
    build_component_candidates,
    build_control_rules,
    build_edges,
    build_successor_dispositions,
    build_supply,
    jsonl_bytes,
    object_digest,
    require,
    sha256_bytes,
    source_state,
    yaml_bytes,
)


def build_review_packet(
    components: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    ab_paths: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component in components:
        if component["activation_proposal"].startswith("PROPOSED"):
            rows.append(
                {
                    "packet_item_id": f"P2-COMPONENT-{component['component_id']}",
                    "object_type": "PROPOSED_ACTIVE_COMPONENT",
                    "review_subject": component,
                    "required_review_roles": [
                        "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                        "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
                    ],
                    "prefilled_score": None,
                    "prefilled_decision": None,
                }
            )
    for rule in rules:
        rows.append(
            {
                "packet_item_id": f"P2-CONTROL-{rule['control_rule_id']}",
                "object_type": "CONTROL_RULE_SEPARATION",
                "review_subject": rule,
                "required_review_roles": [
                    "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                    "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
                ],
                "prefilled_score": None,
                "prefilled_decision": None,
            }
        )
    for edge in edges:
        rows.append(
            {
                "packet_item_id": f"P2-{edge['edge_id']}",
                "object_type": "PROPOSED_COMPONENT_CP_EDGE",
                "review_subject": edge,
                "required_review_roles": [
                    "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                    "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
                ],
                "prefilled_score": None,
                "prefilled_decision": None,
            }
        )
    for path in ab_paths:
        rows.append(
            {
                "packet_item_id": f"P2-AB-{path['content_product_type_id']}",
                "object_type": "AB_STRUCTURAL_PATH_CAPABILITY",
                "review_subject": path,
                "required_review_roles": [
                    "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                    "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
                ],
                "prefilled_score": None,
                "prefilled_decision": None,
            }
        )
    return rows


def owner_document(proposed_component_count: int, edge_count: int) -> dict[str, Any]:
    return {
        "current_gate1_owner": {
            "schema_version": "v0.1",
            "owner_id": "GATE1_V11_P2_COMPONENT_REVIEW_CHECKPOINT_OWNER",
            "task_id": TASK_ID,
            "baseline_commit": BASELINE_COMMIT,
            "current_task_root": TASK_ROOT.as_posix(),
            "current_checker": CURRENT_CHECKER_PATH.as_posix(),
            "predecessor": {
                "task_id": "GATE1_V11_SIGNED_REVIEW_CLOSEOUT_AND_BASELINE_FREEZE_001",
                "result_state": "STOPPED_COMPONENT_SUPPLY_GAP",
                "p2_allowed_by_p1b": False,
                "historical_owner_sha256": P1B_OWNER_AS_BUILT_SHA256,
                "historical_checker_sha256": P1B_CHECKER_AS_BUILT_SHA256,
            },
            "protected_inputs": {
                "standard_source": STANDARD_PATH.as_posix(),
                "p1b_result": P1B_RESULT_PATH.as_posix(),
                "p1b_route_gold": P1B_ROUTE_GOLD_PATH.as_posix(),
                "historical_component_source": COMPONENT_SOURCE_PATH.as_posix(),
                "profile_source": PROFILE_PATH.as_posix(),
            },
            "checkpoint": {
                "state": "PENDING_INDEPENDENT_COMPONENT_REVIEW",
                "p2_final_complete": False,
                "proposed_component_count": proposed_component_count,
                "proposed_edge_count": edge_count,
                "active_component_count": 0,
                "active_edge_count": 0,
                "self_approval_count": 0,
                "p3_allowed": False,
            },
            "core_numbers": {
                "target_total": 300,
                "reference_inventory": 120,
                "historical_component_inventory": 86,
            },
            "current_ledger_authority": {
                "checker_path": "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001/phase_0/check_current_ledger_owner.py",
                "shared_horizon_modified": False,
                "terminal_derivation": "delegated_to_existing_owner",
            },
            "readiness": {
                "changed": False,
                "generation_allowed": False,
                "generator_qualified": False,
                "runtime_ingest_ready": False,
                "production_ready": False,
            },
        }
    }


def build_documents(root: Path) -> dict[Path, bytes]:
    state = source_state(root)
    components = build_component_candidates(state)
    rules = build_control_rules(state)
    edges, selected = build_edges(components, state["profiles"])
    apply_activation_proposals(components, edges)
    successors = build_successor_dispositions(state, components, rules)
    supply = build_supply(state["profiles"], edges)
    ab_paths = build_ab_paths(state["profiles"], selected)
    selected_ids = {row["component_id"] for row in edges}
    review_packet = build_review_packet(components, rules, edges, ab_paths)
    packet_sha = sha256_bytes(jsonl_bytes(review_packet))
    addition: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "historical_starting_inventory": 86,
        "content_successor_candidate_count": len(components),
        "control_rule_candidate_count": len(rules),
        "proposed_activation_component_count": len(selected_ids),
        "candidate_complete_profile_count": supply["candidate_supply_matrix"][
            "candidate_complete_profile_count"
        ],
        "ab_structural_candidate_profile_count": len(ab_paths),
        "necessary_addition_count": 0,
        "necessary_additions": [],
        "finding": "NO_VERIFIED_GAP_AFTER_REPAIR_AND_NEED_DRIVEN_SELECTION",
        "future_addition_policy": "ALLOW_ONLY_AFTER_INDEPENDENT_REVIEW_CONFIRMS_A_REAL_ROLE_OR_AB_GAP",
        "number_target_used": False,
    }
    addition["assessment_digest"] = object_digest(addition, "assessment_digest")
    review_job: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_INDEPENDENT_COMPONENT_REVIEW",
        "review_packet_path": REVIEW_PACKET_PATH.as_posix(),
        "review_packet_sha256": packet_sha,
        "packet_item_counts": dict(
            Counter(row["object_type"] for row in review_packet)
        ),
        "review_identity_policy": {
            "reviewer_count": 2,
            "reviewers_must_be_different_instances_or_sessions": True,
            "reviewers_must_differ_from_component_author_and_p2_executor": True,
            "reviewers_must_differ_from_final_activator": True,
            "third_review_only_for_real_disagreements": True,
        },
        "review_roles": {
            "primary": "content value, atomicity, composability, CP fit, and AB capability",
            "secondary": "provenance, evidence span, fact and authorization boundary, compatibility, and edge truth",
        },
        "scoring_contract": "FROZEN_V1_1_COMMON_80_PLUS_TYPE_20_WITH_EXISTING_VETOES",
        "self_approval_allowed": False,
        "component_activation_allowed_before_closeout": False,
    }
    review_job["review_job_digest"] = object_digest(review_job, "review_job_digest")
    compatibility: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "p1b_materializer": {
            "path": P1B_MATERIALIZER_PATH.as_posix(),
            "sha256_before": P1B_MATERIALIZER_BEFORE_SHA256,
            "sha256_after": P1B_MATERIALIZER_AFTER_SHA256,
            "historical_task_outputs_changed": False,
            "historical_owner_sha256": P1B_OWNER_AS_BUILT_SHA256,
            "historical_checker_sha256": P1B_CHECKER_AS_BUILT_SHA256,
            "global_owner_managed_by_p1b_after_successor": False,
        },
        "current_checker": {
            "path": CURRENT_CHECKER_PATH.as_posix(),
            "sha256_before": P1B_CHECKER_AS_BUILT_SHA256,
            "sha256_after": CURRENT_CHECKER_AFTER_SHA256,
            "recursive_checker_chain": False,
        },
        "shared_ledger_modified": False,
        "readiness_changed": False,
    }
    compatibility["receipt_digest"] = object_digest(compatibility, "receipt_digest")
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_INDEPENDENT_COMPONENT_REVIEW",
        "p2_final_complete": False,
        "components_active": False,
        "active_component_count": 0,
        "active_edge_count": 0,
        "historical_86_successor_disposition_complete": True,
        "content_successor_candidate_count": len(components),
        "control_rule_candidate_count": len(rules),
        "proposed_activation_component_count": len(selected_ids),
        "proposed_edge_count": len(edges),
        "candidate_supply_complete_profile_count": supply["candidate_supply_matrix"][
            "candidate_complete_profile_count"
        ],
        "approved_supply_complete_profile_count": 0,
        "ab_path_candidate_profile_count": len(ab_paths),
        "necessary_addition_count": 0,
        "review_packet_sha256": packet_sha,
        "self_approval_count": 0,
        "generator_core_stage": "BLOCKED_UNTIL_MATCHING_INDEPENDENT_COMPONENT_REVIEWS",
        "p3_allowed": False,
        "core_number_impact": {
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
    owner = owner_document(len(selected_ids), len(edges))
    return {
        SUCCESSOR_PATH: jsonl_bytes(successors),
        COMPONENT_CANDIDATES_PATH: jsonl_bytes(components),
        CONTROL_RULES_PATH: jsonl_bytes(rules),
        EDGE_PATH: jsonl_bytes(edges),
        SUPPLY_PATH: yaml_bytes(supply),
        ADDITION_PATH: yaml_bytes({"necessary_addition_assessment": addition}),
        AB_PATH: jsonl_bytes(ab_paths),
        REVIEW_PACKET_PATH: jsonl_bytes(review_packet),
        REVIEW_JOB_PATH: yaml_bytes({"independent_component_review_job": review_job}),
        COMPAT_PATH: yaml_bytes({"p1b_successor_compatibility_receipt": compatibility}),
        RESULT_PATH: yaml_bytes({"p2_component_review_checkpoint_result": result}),
        CURRENT_OWNER_PATH: yaml_bytes(owner),
    }


def validate_documents(documents: dict[Path, bytes]) -> None:
    components = [
        json.loads(line)
        for line in documents[COMPONENT_CANDIDATES_PATH].decode().splitlines()
    ]
    rules = [
        json.loads(line) for line in documents[CONTROL_RULES_PATH].decode().splitlines()
    ]
    edges = [json.loads(line) for line in documents[EDGE_PATH].decode().splitlines()]
    successors = [
        json.loads(line) for line in documents[SUCCESSOR_PATH].decode().splitlines()
    ]
    ab_paths = [json.loads(line) for line in documents[AB_PATH].decode().splitlines()]
    packet = [
        json.loads(line) for line in documents[REVIEW_PACKET_PATH].decode().splitlines()
    ]
    result = yaml.safe_load(documents[RESULT_PATH])[
        "p2_component_review_checkpoint_result"
    ]
    owner = yaml.safe_load(documents[CURRENT_OWNER_PATH])["current_gate1_owner"]
    supply = yaml.safe_load(documents[SUPPLY_PATH])["candidate_supply_matrix"]
    addition = yaml.safe_load(documents[ADDITION_PATH])["necessary_addition_assessment"]
    require(
        len(successors) == 86 and len(components) == 78 and len(rules) == 8, "E_COUNTS"
    )
    require(
        all(not row["active"] for row in successors + rules + edges + ab_paths),
        "E_ACTIVE_BEFORE_REVIEW",
    )
    require(
        all(not row["new_generator_consumable"] for row in components),
        "E_CONSUMABLE_BEFORE_REVIEW",
    )
    require(
        all(
            row["component_digest"] == object_digest(row, "component_digest")
            for row in components
        ),
        "E_COMPONENT_DIGEST",
    )
    require(
        all(
            row["provenance"].get("source_type")
            == "FOUNDER_AUTHORIZED_DESIGN_COMPONENT"
            or bool(row["provenance"].get("parent_assets"))
            for row in components
        ),
        "E_COMPONENT_PROVENANCE",
    )
    require(
        all(row["contributes_component_supply"] is False for row in rules),
        "E_RULE_SUPPLY",
    )
    require(
        all(
            row["provenance"].get("source_type")
            in {"SOURCE_DERIVED", "FOUNDER_AUTHORIZED_DESIGN_COMPONENT"}
            for row in components
        ),
        "E_PROVENANCE_TYPE",
    )
    selected_ids = {
        row["component_id"]
        for row in components
        if row["activation_proposal"].startswith("PROPOSED")
    }
    component_by_id = {row["component_id"]: row for row in components}
    require(
        all(
            row["edge_digest"] == object_digest(row, "edge_digest")
            and row["component_id"] in selected_ids
            and row["component_digest"]
            == component_by_id[row["component_id"]]["component_digest"]
            and row["historical_edge_reactivated"] is False
            for row in edges
        ),
        "E_EDGE_BINDING",
    )
    require(
        all(row["observable_difference_axis_count"] >= 4 for row in ab_paths),
        "E_AB_DIFFERENCE",
    )
    require(
        all(
            row["lane_a"]["session_policy"] != row["lane_b"]["session_policy"]
            for row in ab_paths
        ),
        "E_AB_SESSION",
    )
    require(supply["candidate_complete_profile_count"] == 20, "E_SUPPLY_PROFILE_COUNT")
    require(supply["approved_complete_profile_count"] == 0, "E_APPROVED_BEFORE_REVIEW")
    require(
        addition["necessary_addition_count"] == 0
        and addition["necessary_additions"] == []
        and addition["number_target_used"] is False,
        "E_ADDITION_POLICY",
    )
    require(
        all(
            row["prefilled_score"] is None and row["prefilled_decision"] is None
            for row in packet
        ),
        "E_REVIEW_PREFILLED",
    )
    require(
        result["checkpoint_state"] == "PENDING_INDEPENDENT_COMPONENT_REVIEW",
        "E_RESULT_STATE",
    )
    require(
        result["p3_allowed"] is False and result["self_approval_count"] == 0,
        "E_SELF_APPROVAL",
    )
    require(
        result["core_number_impact"]
        == {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "E_CORE_NUMBERS",
    )
    require(
        owner["task_id"] == TASK_ID and owner["checkpoint"]["p3_allowed"] is False,
        "E_OWNER",
    )
    serialized = b"".join(documents.values())
    require(
        not any(f"{key}: true".encode() in serialized for key in READY_KEYS),
        "E_READINESS_TRUE",
    )
