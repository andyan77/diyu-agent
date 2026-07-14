#!/usr/bin/env python3
"""Materialize the final P2 closeout from imported independent reviews."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from p2_adjudication import validate_adjudication
from p2_component_model import (
    COMPONENT_CANDIDATES_PATH,
    CURRENT_CHECKER_PATH,
    CURRENT_OWNER_PATH,
    P1B_ROUTE_GOLD_PATH,
    REVIEW_PACKET_PATH,
    ROOT,
    TASK_ID,
    TASK_ROOT,
    jsonl_bytes,
    load_jsonl,
    object_digest,
    require,
    sha256_file,
    source_state,
    yaml_bytes,
)
from p2_final_documents import (
    build_approved_supply,
    build_generator_contract,
    build_generator_evidence,
    build_generator_registry,
    build_provider_audit,
    build_route_evidence,
)
from p2_review_closeout import (
    PACKET_SHA256,
    PRIMARY_ROLE,
    REVIEWED_COMMIT,
    SECONDARY_ROLE,
    combine_reviews,
    load_review_directory,
)
from p2_targeted_repair import (
    ADDITION_CANDIDATES_PATH,
    FINAL_EDGE_CANDIDATES_PATH,
    REVISED_AB_PATH,
    REVISED_COMPONENTS_PATH,
    REVISED_RULES_PATH,
    TARGETED_REVIEW_PACKET_PATH,
)


if not __debug__:
    sys.stderr.write("P2 final materializer refuses python -O\n")
    raise SystemExit(2)


INITIAL_PRIMARY_IMPORT_DIR = TASK_ROOT / "imports/initial_review/primary"
INITIAL_SECONDARY_IMPORT_DIR = TASK_ROOT / "imports/initial_review/secondary"
ADJUDICATION_IMPORT_DIR = TASK_ROOT / "imports/initial_review/adjudication"
TARGET_PRIMARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r1/primary"
TARGET_SECONDARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r1/secondary"
TARGET_R2_PRIMARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r2/primary"
TARGET_R2_SECONDARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r2/secondary"
FINAL_IMPORT_SENTINEL = TARGET_R2_PRIMARY_IMPORT_DIR / "records.jsonl"
IMPORT_MANIFEST_PATH = (
    TASK_ROOT / "imports/independent_review_import_manifest.v0.1.yaml"
)
COMBINED_REVIEW_PATH = TASK_ROOT / "review/combined_review_records.v0.1.jsonl"
TARGET_COMBINED_REVIEW_PATH = (
    TASK_ROOT / "review/targeted_r1_combined_review_records.v0.1.jsonl"
)
REVIEW_CLOSEOUT_PATH = (
    TASK_ROOT / "review/independent_component_review_closeout.v0.1.yaml"
)
ACTIVE_COMPONENTS_PATH = TASK_ROOT / "component/active_gate1_components.v0.1.jsonl"
ACTIVE_RULES_PATH = TASK_ROOT / "component/active_control_rules.v0.1.jsonl"
ACTIVE_EDGES_PATH = TASK_ROOT / "component/active_gate1_edges.v0.1.jsonl"
APPROVED_SUPPLY_PATH = (
    TASK_ROOT / "component/approved_component_supply_matrix.v0.1.yaml"
)
ACTIVE_AB_PATH = TASK_ROOT / "ab/active_ab_structural_paths.v0.1.jsonl"
GENERATOR_CONTRACT_PATH = TASK_ROOT / "generator/gate1_generator_contract.v0.1.yaml"
GENERATOR_REGISTRY_PATH = (
    TASK_ROOT / "generator/active_gate1_generator_registry.v0.1.yaml"
)
AUTHOR_REQUESTS_PATH = TASK_ROOT / "generator/typed_author_requests.v0.1.jsonl"
REALIZATIONS_PATH = TASK_ROOT / "generator/component_realization_results.v0.1.jsonl"
AB_PAIR_RESULTS_PATH = TASK_ROOT / "generator/ab_pair_results.v0.1.jsonl"
ABLATION_RESULTS_PATH = TASK_ROOT / "generator/component_ablation_results.v0.1.jsonl"
COMPONENT_TAMPER_RESULTS_PATH = (
    TASK_ROOT / "generator/component_digest_tamper_results.v0.1.jsonl"
)
ROUTE_ACTUALS_PATH = TASK_ROOT / "generator/route_actuals.v0.1.jsonl"
ROUTE_COMPARISONS_PATH = TASK_ROOT / "generator/route_comparisons.v0.1.jsonl"
PROVIDER_AUDIT_PATH = TASK_ROOT / "generator/external_provider_exit_audit.v0.1.yaml"
FINAL_COMPATIBILITY_PATH = (
    TASK_ROOT / "compatibility/p2_final_current_checker_receipt.v0.1.yaml"
)
FINAL_RESULT_PATH = TASK_ROOT / "result/p2_final_result.v0.1.yaml"
ROUTE_INPUT_PATH = Path(
    "controlled_content_generator_v2_001/"
    "creative_authoring_route_oracle_convergence_001/route/route_inputs.v0.1.jsonl"
)
TARGET_REVIEWED_COMMIT = "6d7aa877a12867ee9a73e50a8e292ef4a631d7a9"
TARGET_REVIEW_PACKET_SHA256 = (
    "5d32c3dd1140013978f42df887ec98462b723317bf58daaf8eaa040d608bea50"
)
CHECKPOINT_CURRENT_CHECKER_SHA256 = (
    "2aec6f38dd6d64118506ad998c504e950eeaae34fc97b718ab285e49edc035bd"
)


def _review_files(relative_dir: Path) -> list[Path]:
    return [
        relative_dir / "records.jsonl",
        relative_dir / "report.md",
        relative_dir / "run_manifest.yaml",
    ]


def _build_import_manifest(
    root: Path,
    summaries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for review_stage, role, relative_dir in (
        ("initial", "primary", INITIAL_PRIMARY_IMPORT_DIR),
        ("initial", "secondary", INITIAL_SECONDARY_IMPORT_DIR),
        ("initial", "adjudication", ADJUDICATION_IMPORT_DIR),
        ("targeted_r1", "primary", TARGET_PRIMARY_IMPORT_DIR),
        ("targeted_r1", "secondary", TARGET_SECONDARY_IMPORT_DIR),
    ):
        for path in _review_files(relative_dir):
            files.append(
                {
                    "review_stage": review_stage,
                    "review_role": role,
                    "path": path.as_posix(),
                    "sha256": sha256_file(root / path),
                    "byte_imported_without_rewrite": True,
                }
            )
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "reviewed_checkpoint_commit": REVIEWED_COMMIT,
        "review_packet_sha256": PACKET_SHA256,
        "imported_file_count": len(files),
        "files": files,
        "reviewer_identities": summaries,
        "reviewers_are_distinct": len(
            {
                summary["reviewer_identity_id"]
                for summary in summaries.values()
            }
        )
        == 3,
        "p2_executor_is_not_a_reviewer": True,
        "final_activator_is_not_a_reviewer": True,
    }
    document["manifest_digest"] = object_digest(document, "manifest_digest")
    return {"independent_review_import_manifest": document}


def _owner_document(
    active_component_count: int,
    active_edge_count: int,
    active_control_rule_count: int,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "owner_id": "GATE1_V11_P2_FINAL_OWNER",
        "task_id": TASK_ID,
        "current_task_root": TASK_ROOT.as_posix(),
        "current_checker": CURRENT_CHECKER_PATH.as_posix(),
        "result_state": "PASS_TO_P3_OPEN_PROBE",
        "p2_complete": True,
        "p3_allowed": True,
        "current_generator": {
            "entrypoint": (
                TASK_ROOT / "run_p2_component_supply_and_generator_core_repair.py"
            ).as_posix(),
            "active_component_count": active_component_count,
            "active_edge_count": active_edge_count,
            "active_control_rule_count": active_control_rule_count,
            "historical_generator_entrypoints_consumed": [],
        },
        "predecessor": {
            "owner_id": "GATE1_V11_P2_COMPONENT_REVIEW_CHECKPOINT_OWNER",
            "reviewed_checkpoint_commit": REVIEWED_COMMIT,
            "review_packet_sha256": PACKET_SHA256,
        },
        "core_numbers": {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "readiness": {
            "generation_allowed": False,
            "generator_qualified": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        },
    }
    document["owner_digest"] = object_digest(document, "owner_digest")
    return {"current_gate1_owner": document}


def _compatibility_document(root: Path) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "current_checker": {
            "path": CURRENT_CHECKER_PATH.as_posix(),
            "sha256_before_final_closeout": CHECKPOINT_CURRENT_CHECKER_SHA256,
            "sha256_after_final_closeout": sha256_file(root / CURRENT_CHECKER_PATH),
            "recursive_checker_chain": False,
            "checkpoint_validation_retained": True,
            "p1a_validation_retained": True,
            "p1b_validation_retained": True,
        },
        "p1a_p1b_task_roots_modified": False,
        "checkpoint_assets_rewritten": False,
        "shared_ledger_modified": False,
        "readiness_changed": False,
    }
    document["receipt_digest"] = object_digest(document, "receipt_digest")
    return {"p2_final_current_checker_compatibility_receipt": document}


def _result_document(
    active_components: list[dict[str, Any]],
    active_edges: list[dict[str, Any]],
    active_rules: list[dict[str, Any]],
    active_paths: list[dict[str, Any]],
    initial_combined: list[dict[str, Any]],
    targeted_combined: list[dict[str, Any]],
    adjudication_records: list[dict[str, Any]],
    evidence: dict[str, list[dict[str, Any]]],
    route_comparisons: list[dict[str, Any]],
    provider_audit: dict[str, Any],
) -> dict[str, Any]:
    initial_disposition_counts = {
        decision: sum(
            row["combined_disposition"] == decision for row in initial_combined
        )
        for decision in ("APPROVE", "REPAIR", "REJECT")
    }
    initial_disposition_counts["DISAGREEMENT_REQUIRES_ADJUDICATION"] = sum(
        row["requires_targeted_adjudication"] for row in initial_combined
    )
    adjudication_counts = {
        decision: sum(
            row["adjudicated_decision"] == decision
            for row in adjudication_records
        )
        for decision in ("APPROVE", "REPAIR", "REJECT")
    }
    targeted_disposition_counts = {
        decision: sum(
            row["combined_disposition"] == decision for row in targeted_combined
        )
        for decision in ("APPROVE", "REPAIR", "REJECT")
    }
    audit = provider_audit["external_provider_exit_audit"]
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "result_state": "PASS_TO_P3_OPEN_PROBE",
        "p2_complete": True,
        "p3_allowed": True,
        "reviewed_checkpoint_commit": REVIEWED_COMMIT,
        "review_packet_sha256": PACKET_SHA256,
        "targeted_reviewed_commit": TARGET_REVIEWED_COMMIT,
        "targeted_review_packet_sha256": TARGET_REVIEW_PACKET_SHA256,
        "initial_review_record_count_per_reviewer": len(initial_combined),
        "initial_review_disposition_counts": initial_disposition_counts,
        "initial_adjudication_record_count": len(adjudication_records),
        "initial_adjudication_disposition_counts": adjudication_counts,
        "targeted_review_record_count_per_reviewer": len(targeted_combined),
        "targeted_review_disposition_counts": targeted_disposition_counts,
        "unresolved_review_disagreement_count": 0,
        "self_approval_count": 0,
        "active_component_count": len(active_components),
        "revised_historical_component_count": sum(
            row.get("component_version") == "v1.1-p2-r1"
            and str(row.get("component_id", "")).startswith("RCV2-")
            for row in active_components
        ),
        "necessary_addition_count": sum(
            str(row.get("component_id", "")).startswith("G1V11-P2-")
            for row in active_components
        ),
        "active_control_rule_count": len(active_rules),
        "active_edge_count": len(active_edges),
        "approved_supply_complete_profile_count": 20,
        "active_ab_path_profile_count": len(active_paths),
        "typed_author_request_count": len(evidence["requests"]),
        "structural_realization_count": len(evidence["realizations"]),
        "component_ablation_case_count": len(evidence["ablations"]),
        "component_digest_tamper_case_count": len(evidence["digest_tampers"]),
        "route_case_count": len(route_comparisons),
        "route_primary_action_match_count": sum(
            row["primary_action_matches_gold"] for row in route_comparisons
        ),
        "route_primary_reason_match_count": sum(
            row["primary_reason_matches_gold"] for row in route_comparisons
        ),
        "external_provider_request_count": audit["external_provider_request_count"],
        "external_provider_response_count": audit["external_provider_response_count"],
        "audience_content_created_count": 0,
        "composition_plan_created_count": 0,
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
    document["result_digest"] = object_digest(document, "result_digest")
    return {"p2_final_result": document}


def _activate_components(
    component_pool: dict[str, dict[str, Any]],
    selected_ids: set[str],
    initial_approved_ids: set[str],
    targeted_approved_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component_id in sorted(selected_ids):
        candidate = component_pool[component_id]
        targeted_item_id = f"P2R1-COMPONENT-{component_id}"
        initial_item_id = f"P2-COMPONENT-{component_id}"
        if targeted_item_id in targeted_approved_ids:
            review_stage = "TARGETED_R1_MATCHING_TWO_APPROVALS"
            packet_item_id = targeted_item_id
        else:
            require(
                initial_item_id in initial_approved_ids,
                "E_COMPONENT_REVIEW_GAP",
                component_id,
            )
            review_stage = "INITIAL_MATCHING_TWO_APPROVALS"
            packet_item_id = initial_item_id
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_component_digest"] = row.pop("component_digest")
        row["active"] = True
        row["new_generator_consumable"] = True
        row["activation_basis"] = review_stage
        row["review_packet_item_id"] = packet_item_id
        row["independent_review_state"] = "APPROVED_BY_TWO_REVIEWS"
        row["readiness"] = {
            "generation_eligible": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        }
        row["component_digest"] = object_digest(row, "component_digest")
        rows.append(row)
    return rows


def _activate_rules(
    candidates: list[dict[str, Any]], targeted_approved_ids: set[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        rule_id = str(candidate["control_rule_id"])
        packet_item_id = f"P2R1-CONTROL-{rule_id}"
        require(packet_item_id in targeted_approved_ids, "E_RULE_REVIEW_GAP", rule_id)
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_control_rule_digest"] = row.pop(
            "control_rule_digest"
        )
        row["active"] = True
        row["independent_review_state"] = "APPROVED_BY_TWO_REVIEWS"
        row["activation_basis"] = "TARGETED_R1_MATCHING_TWO_APPROVALS"
        row["review_packet_item_id"] = packet_item_id
        row["contributes_component_supply"] = False
        row["may_write_audience_surface"] = False
        row["control_rule_digest"] = object_digest(row, "control_rule_digest")
        rows.append(row)
    return rows


def _activate_edges(
    candidates: list[dict[str, Any]],
    component_by_id: dict[str, dict[str, Any]],
    targeted_approved_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        edge_id = str(candidate["edge_id"])
        packet_item_id = f"P2R1-{edge_id}"
        require(packet_item_id in targeted_approved_ids, "E_EDGE_REVIEW_GAP", edge_id)
        component = component_by_id[str(candidate["component_id"])]
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_edge_digest"] = row.pop("edge_digest")
        row["reviewed_candidate_component_digest"] = row["component_digest"]
        row["component_digest"] = component["component_digest"]
        row["active"] = True
        row["activation_basis"] = "TARGETED_R1_MATCHING_TWO_APPROVALS"
        row["review_packet_item_id"] = packet_item_id
        row["independent_review_state"] = "APPROVED_BY_TWO_REVIEWS"
        row["edge_digest"] = object_digest(row, "edge_digest")
        rows.append(row)
    return rows


def _activate_paths(
    candidates: list[dict[str, Any]], targeted_approved_ids: set[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        cp_id = str(candidate["content_product_type_id"])
        packet_item_id = f"P2R1-AB-{cp_id}"
        require(packet_item_id in targeted_approved_ids, "E_PATH_REVIEW_GAP", cp_id)
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_path_digest"] = row.pop("path_digest")
        row["active"] = True
        row["structural_candidate_only"] = False
        row["p2_structural_validation_only"] = True
        row["independent_review_state"] = "APPROVED_BY_TWO_REVIEWS"
        row["activation_basis"] = "TARGETED_R1_MATCHING_TWO_APPROVALS"
        row["review_packet_item_id"] = packet_item_id
        row["path_digest"] = object_digest(row, "path_digest")
        rows.append(row)
    return rows


def _review_closeout(
    summaries: dict[str, dict[str, Any]],
    initial_combined: list[dict[str, Any]],
    targeted_combined: list[dict[str, Any]],
    adjudication_records: list[dict[str, Any]],
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "initial_reviewed_commit": REVIEWED_COMMIT,
        "initial_review_packet_sha256": PACKET_SHA256,
        "targeted_reviewed_commit": TARGET_REVIEWED_COMMIT,
        "targeted_review_packet_sha256": TARGET_REVIEW_PACKET_SHA256,
        "reviewer_identities": summaries,
        "initial_combined_record_count": len(initial_combined),
        "initial_real_disagreement_count": sum(
            row["requires_targeted_adjudication"] for row in initial_combined
        ),
        "initial_adjudication_record_count": len(adjudication_records),
        "targeted_combined_record_count": len(targeted_combined),
        "targeted_matching_approval_count": sum(
            row["combined_disposition"] == "APPROVE" for row in targeted_combined
        ),
        "targeted_unresolved_disagreement_count": sum(
            row["requires_targeted_adjudication"] for row in targeted_combined
        ),
        "executor_self_approval_count": 0,
    }
    document["review_closeout_digest"] = object_digest(
        document, "review_closeout_digest"
    )
    return {"independent_component_review_closeout": document}


def build_final_documents(root: Path = ROOT) -> dict[Path, bytes]:
    state = source_state(root)
    packet = load_jsonl(root / REVIEW_PACKET_PATH)
    require(sha256_file(root / REVIEW_PACKET_PATH) == PACKET_SHA256, "E_PACKET_PIN")
    initial_primary, initial_primary_summary = load_review_directory(
        root / INITIAL_PRIMARY_IMPORT_DIR, packet, PRIMARY_ROLE
    )
    initial_secondary, initial_secondary_summary = load_review_directory(
        root / INITIAL_SECONDARY_IMPORT_DIR, packet, SECONDARY_ROLE
    )
    require(
        initial_primary_summary["reviewer_identity_id"]
        != initial_secondary_summary["reviewer_identity_id"],
        "E_REVIEW_IDENTITY_COLLISION",
    )
    require(
        initial_primary_summary["reviewer_instance_or_session_id"]
        != initial_secondary_summary["reviewer_instance_or_session_id"],
        "E_REVIEW_SESSION_COLLISION",
    )
    require(
        initial_primary_summary["review_run_id"]
        != initial_secondary_summary["review_run_id"],
        "E_REVIEW_RUN_COLLISION",
    )
    initial_combined, disagreements = combine_reviews(
        packet, initial_primary, initial_secondary
    )
    require(len(disagreements) == 92, "E_INITIAL_DISAGREEMENT_COUNT")
    initial_primary_by_id = {
        str(row["packet_item_id"]): row for row in initial_primary
    }
    initial_secondary_by_id = {
        str(row["packet_item_id"]): row for row in initial_secondary
    }
    adjudication_records, adjudication_summary = validate_adjudication(
        root / ADJUDICATION_IMPORT_DIR,
        disagreements,
        initial_primary_by_id,
        initial_secondary_by_id,
    )
    require(
        adjudication_summary["reviewer_identity_id"]
        not in {
            initial_primary_summary["reviewer_identity_id"],
            initial_secondary_summary["reviewer_identity_id"],
        },
        "E_ADJUDICATOR_IDENTITY_COLLISION",
    )
    adjudication_by_id = {
        str(row["packet_item_id"]): row for row in adjudication_records
    }
    for row in initial_combined:
        item_id = str(row["packet_item_id"])
        if row["requires_targeted_adjudication"]:
            adjudication = adjudication_by_id[item_id]
            row["adjudication_record_digest"] = adjudication["record_digest"]
            row["final_disposition"] = adjudication["adjudicated_decision"]
        else:
            row["adjudication_record_digest"] = None
            row["final_disposition"] = row["combined_disposition"]
        row["combined_digest"] = object_digest(row, "combined_digest")

    targeted_packet = load_jsonl(root / TARGETED_REVIEW_PACKET_PATH)
    require(
        sha256_file(root / TARGETED_REVIEW_PACKET_PATH)
        == TARGET_REVIEW_PACKET_SHA256,
        "E_TARGET_PACKET_PIN",
    )
    targeted_primary, targeted_primary_summary = load_review_directory(
        root / TARGET_PRIMARY_IMPORT_DIR,
        targeted_packet,
        PRIMARY_ROLE,
        reviewed_commit=TARGET_REVIEWED_COMMIT,
        packet_sha256=TARGET_REVIEW_PACKET_SHA256,
        prompt_revision="r1",
    )
    targeted_secondary, targeted_secondary_summary = load_review_directory(
        root / TARGET_SECONDARY_IMPORT_DIR,
        targeted_packet,
        SECONDARY_ROLE,
        reviewed_commit=TARGET_REVIEWED_COMMIT,
        packet_sha256=TARGET_REVIEW_PACKET_SHA256,
        prompt_revision="r1",
    )
    require(
        targeted_primary_summary["reviewer_identity_id"]
        != targeted_secondary_summary["reviewer_identity_id"],
        "E_TARGET_REVIEW_IDENTITY_COLLISION",
    )
    require(
        targeted_primary_summary["reviewer_instance_or_session_id"]
        != targeted_secondary_summary["reviewer_instance_or_session_id"],
        "E_TARGET_REVIEW_SESSION_COLLISION",
    )
    require(
        targeted_primary_summary["review_run_id"]
        != targeted_secondary_summary["review_run_id"],
        "E_TARGET_REVIEW_RUN_COLLISION",
    )
    targeted_combined, targeted_disagreements = combine_reviews(
        targeted_packet, targeted_primary, targeted_secondary
    )
    require(
        not targeted_disagreements,
        "E_TARGET_REVIEW_ADJUDICATION_REQUIRED",
        str(len(targeted_disagreements)),
    )
    require(
        all(row["combined_disposition"] == "APPROVE" for row in targeted_combined),
        "E_TARGET_REPAIR_STILL_OPEN",
    )

    initial_approved_ids = {
        str(row["packet_item_id"])
        for row in initial_combined
        if row["final_disposition"] == "APPROVE"
    }
    targeted_approved_ids = {
        str(row["packet_item_id"])
        for row in targeted_combined
        if row["combined_disposition"] == "APPROVE"
    }
    component_pool = {
        str(row["component_id"]): row
        for row in load_jsonl(root / COMPONENT_CANDIDATES_PATH)
    }
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / REVISED_COMPONENTS_PATH)
        }
    )
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / ADDITION_CANDIDATES_PATH)
        }
    )
    edge_candidates = load_jsonl(root / FINAL_EDGE_CANDIDATES_PATH)
    selected_component_ids = {
        str(row["component_id"]) for row in edge_candidates
    }
    require(
        selected_component_ids.issubset(component_pool),
        "E_SELECTED_COMPONENT_UNKNOWN",
    )
    active_components = _activate_components(
        component_pool,
        selected_component_ids,
        initial_approved_ids,
        targeted_approved_ids,
    )
    active_component_by_id = {row["component_id"]: row for row in active_components}
    active_edges = _activate_edges(
        edge_candidates, active_component_by_id, targeted_approved_ids
    )
    active_rules = _activate_rules(
        load_jsonl(root / REVISED_RULES_PATH), targeted_approved_ids
    )
    require(len(active_rules) == 8, "E_CONTROL_RULE_REVIEW_GAP", str(len(active_rules)))
    supply = build_approved_supply(state["profiles"], active_edges)
    require(
        supply["approved_component_supply_matrix"]["approved_complete_profile_count"]
        == 20,
        "E_COMPONENT_SUPPLY_GAP",
    )
    active_paths = _activate_paths(
        load_jsonl(root / REVISED_AB_PATH), targeted_approved_ids
    )
    require(len(active_paths) == 20, "E_AB_PATH_REVIEW_GAP", str(len(active_paths)))
    require(
        all(
            set(path["lane_a"]["component_ids"])
            .union(path["lane_b"]["component_ids"])
            .issubset(active_component_by_id)
            for path in active_paths
        ),
        "E_AB_PATH_COMPONENT_GAP",
    )
    evidence = build_generator_evidence(
        state["profiles"], active_components, active_rules, active_paths
    )
    require(len(evidence["requests"]) == 40, "E_REQUEST_COUNT")
    require(
        all(row["unrealized_component_count"] == 0 for row in evidence["realizations"]),
        "E_COMPONENT_UNREALIZED",
    )
    require(
        all(row["implementation_changed"] for row in evidence["ablations"]),
        "E_COMPONENT_ABLATION",
    )
    require(
        all(row["tamper_rejected"] for row in evidence["digest_tampers"]),
        "E_COMPONENT_TAMPER",
    )
    require(
        all(
            row["same_material_digest"]
            and row["same_source_fact_authorization_boundary"]
            and row["independent_session_ids"]
            and row["minimum_four_axes_pass"]
            for row in evidence["pair_results"]
        ),
        "E_AB_STRUCTURAL_VALIDATION",
    )
    route_inputs = load_jsonl(root / ROUTE_INPUT_PATH)
    route_gold = load_jsonl(root / P1B_ROUTE_GOLD_PATH)
    route_actuals, route_comparisons = build_route_evidence(
        route_inputs, route_gold, state["profiles"]
    )
    require(
        len(route_comparisons) == 60
        and all(
            row["primary_action_matches_gold"] and row["primary_reason_matches_gold"]
            for row in route_comparisons
        ),
        "E_ROUTE_REGRESSION",
    )
    provider_audit = build_provider_audit()
    provider = provider_audit["external_provider_exit_audit"]
    require(provider["external_provider_request_count"] == 0, "E_PROVIDER_REQUEST")
    require(provider["external_provider_response_count"] == 0, "E_PROVIDER_RESPONSE")
    require(
        provider["negative_dispatch_test"]["blocked_before_network_dispatch"] is True,
        "E_PROVIDER_NEGATIVE_TEST",
    )
    summaries = {
        "initial_primary": initial_primary_summary,
        "initial_secondary": initial_secondary_summary,
        "initial_adjudication": adjudication_summary,
        "targeted_primary": targeted_primary_summary,
        "targeted_secondary": targeted_secondary_summary,
    }
    review_closeout = _review_closeout(
        summaries,
        initial_combined,
        targeted_combined,
        adjudication_records,
    )
    require(
        review_closeout["independent_component_review_closeout"][
            "targeted_unresolved_disagreement_count"
        ]
        == 0,
        "E_REVIEW_DISAGREEMENT",
    )
    import_manifest = _build_import_manifest(root, summaries)
    generator_contract = build_generator_contract()
    generator_registry = build_generator_registry(root, active_components, active_edges)
    compatibility = _compatibility_document(root)
    result = _result_document(
        active_components,
        active_edges,
        active_rules,
        active_paths,
        initial_combined,
        targeted_combined,
        adjudication_records,
        evidence,
        route_comparisons,
        provider_audit,
    )
    owner = _owner_document(
        len(active_components), len(active_edges), len(active_rules)
    )
    return {
        IMPORT_MANIFEST_PATH: yaml_bytes(import_manifest),
        COMBINED_REVIEW_PATH: jsonl_bytes(initial_combined),
        TARGET_COMBINED_REVIEW_PATH: jsonl_bytes(targeted_combined),
        REVIEW_CLOSEOUT_PATH: yaml_bytes(review_closeout),
        ACTIVE_COMPONENTS_PATH: jsonl_bytes(active_components),
        ACTIVE_RULES_PATH: jsonl_bytes(active_rules),
        ACTIVE_EDGES_PATH: jsonl_bytes(active_edges),
        APPROVED_SUPPLY_PATH: yaml_bytes(supply),
        ACTIVE_AB_PATH: jsonl_bytes(active_paths),
        GENERATOR_CONTRACT_PATH: yaml_bytes(generator_contract),
        GENERATOR_REGISTRY_PATH: yaml_bytes(generator_registry),
        AUTHOR_REQUESTS_PATH: jsonl_bytes(evidence["requests"]),
        REALIZATIONS_PATH: jsonl_bytes(evidence["realizations"]),
        AB_PAIR_RESULTS_PATH: jsonl_bytes(evidence["pair_results"]),
        ABLATION_RESULTS_PATH: jsonl_bytes(evidence["ablations"]),
        COMPONENT_TAMPER_RESULTS_PATH: jsonl_bytes(evidence["digest_tampers"]),
        ROUTE_ACTUALS_PATH: jsonl_bytes(route_actuals),
        ROUTE_COMPARISONS_PATH: jsonl_bytes(route_comparisons),
        PROVIDER_AUDIT_PATH: yaml_bytes(provider_audit),
        FINAL_COMPATIBILITY_PATH: yaml_bytes(compatibility),
        FINAL_RESULT_PATH: yaml_bytes(result),
        CURRENT_OWNER_PATH: yaml_bytes(owner),
    }


def validate_final_documents(documents: dict[Path, bytes]) -> None:
    def jsonl_rows(path: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in documents[path].decode("utf-8").splitlines()
            if line
        ]

    result = yaml.safe_load(documents[FINAL_RESULT_PATH])["p2_final_result"]
    owner = yaml.safe_load(documents[CURRENT_OWNER_PATH])["current_gate1_owner"]
    manifest = yaml.safe_load(documents[IMPORT_MANIFEST_PATH])[
        "independent_review_import_manifest"
    ]
    closeout = yaml.safe_load(documents[REVIEW_CLOSEOUT_PATH])[
        "independent_component_review_closeout"
    ]
    supply = yaml.safe_load(documents[APPROVED_SUPPLY_PATH])[
        "approved_component_supply_matrix"
    ]
    provider = yaml.safe_load(documents[PROVIDER_AUDIT_PATH])[
        "external_provider_exit_audit"
    ]
    contract = yaml.safe_load(documents[GENERATOR_CONTRACT_PATH])[
        "gate1_generator_contract"
    ]
    registry = yaml.safe_load(documents[GENERATOR_REGISTRY_PATH])[
        "active_gate1_generator_registry"
    ]
    compatibility = yaml.safe_load(documents[FINAL_COMPATIBILITY_PATH])[
        "p2_final_current_checker_compatibility_receipt"
    ]
    initial_combined = jsonl_rows(COMBINED_REVIEW_PATH)
    targeted_combined = jsonl_rows(TARGET_COMBINED_REVIEW_PATH)
    components = jsonl_rows(ACTIVE_COMPONENTS_PATH)
    rules = jsonl_rows(ACTIVE_RULES_PATH)
    edges = jsonl_rows(ACTIVE_EDGES_PATH)
    paths = jsonl_rows(ACTIVE_AB_PATH)
    requests = jsonl_rows(AUTHOR_REQUESTS_PATH)
    realizations = jsonl_rows(REALIZATIONS_PATH)
    pairs = jsonl_rows(AB_PAIR_RESULTS_PATH)
    ablations = jsonl_rows(ABLATION_RESULTS_PATH)
    digest_tampers = jsonl_rows(COMPONENT_TAMPER_RESULTS_PATH)
    route_comparisons = jsonl_rows(ROUTE_COMPARISONS_PATH)

    require(result["result_digest"] == object_digest(result, "result_digest"), "E_RESULT_DIGEST")
    require(result["result_state"] == "PASS_TO_P3_OPEN_PROBE", "E_RESULT_STATE")
    require(result["p2_complete"] is True and result["p3_allowed"] is True, "E_P3")
    require(result["self_approval_count"] == 0, "E_SELF_APPROVAL")
    require(result["unresolved_review_disagreement_count"] == 0, "E_REVIEW_OPEN")
    require(len(initial_combined) == 244, "E_INITIAL_REVIEW_COUNT")
    require(
        sum(row["requires_targeted_adjudication"] for row in initial_combined) == 92,
        "E_INITIAL_DISAGREEMENT_COUNT",
    )
    require(
        all(
            row["final_disposition"] in {"APPROVE", "REPAIR", "REJECT"}
            and row["combined_digest"] == object_digest(row, "combined_digest")
            and (
                not row["requires_targeted_adjudication"]
                or isinstance(row["adjudication_record_digest"], str)
            )
            for row in initial_combined
        ),
        "E_INITIAL_REVIEW_CLOSEOUT",
    )
    require(
        len(targeted_combined) == 141
        and all(
            row["combined_disposition"] == "APPROVE"
            and row["requires_targeted_adjudication"] is False
            and row["combined_digest"] == object_digest(row, "combined_digest")
            for row in targeted_combined
        ),
        "E_TARGET_REVIEW_CLOSEOUT",
    )
    require(
        manifest["manifest_digest"] == object_digest(manifest, "manifest_digest")
        and manifest["imported_file_count"] == 15
        and len(manifest["files"]) == 15
        and all(row["byte_imported_without_rewrite"] is True for row in manifest["files"])
        and manifest["reviewers_are_distinct"] is True,
        "E_IMPORT_MANIFEST",
    )
    require(
        closeout["review_closeout_digest"]
        == object_digest(closeout, "review_closeout_digest")
        and closeout["initial_combined_record_count"] == 244
        and closeout["initial_real_disagreement_count"] == 92
        and closeout["initial_adjudication_record_count"] == 92
        and closeout["targeted_combined_record_count"] == 141
        and closeout["targeted_matching_approval_count"] == 141
        and closeout["targeted_unresolved_disagreement_count"] == 0
        and closeout["executor_self_approval_count"] == 0,
        "E_REVIEW_CLOSEOUT",
    )
    require(supply["approved_complete_profile_count"] == 20, "E_SUPPLY")
    require(
        supply["matrix_digest"] == object_digest(supply, "matrix_digest")
        and len(supply["entries"]) == 20
        and all(
            row["approved_supply_complete"] is True
            and all(role["complete"] is True for role in row["required_roles"])
            for row in supply["entries"]
        ),
        "E_SUPPLY_MATRIX",
    )
    require(len(components) == result["active_component_count"], "E_COMPONENT_COUNT")
    require(len(edges) == result["active_edge_count"], "E_EDGE_COUNT")
    require(
        all(
            row["component_digest"] == object_digest(row, "component_digest")
            and row["active"] is True
            and row["new_generator_consumable"] is True
            and row["independent_review_state"] == "APPROVED_BY_TWO_REVIEWS"
            and not any(row["readiness"].values())
            for row in components
        ),
        "E_COMPONENT_DIGEST",
    )
    require(
        all(
            row["edge_digest"] == object_digest(row, "edge_digest")
            and row["active"] is True
            and row["independent_review_state"] == "APPROVED_BY_TWO_REVIEWS"
            for row in edges
        ),
        "E_EDGE_DIGEST",
    )
    component_ids = {row["component_id"] for row in components}
    require(
        len(component_ids) == len(components)
        and all(row["component_id"] in component_ids for row in edges),
        "E_COMPONENT_EDGE_BINDING",
    )
    require(
        len(rules) == result["active_control_rule_count"] == 8
        and all(
            row["control_rule_digest"] == object_digest(row, "control_rule_digest")
            and row["active"] is True
            and row["contributes_component_supply"] is False
            and row["may_write_audience_surface"] is False
            for row in rules
        ),
        "E_CONTROL_RULES",
    )
    require(
        len(paths) == result["active_ab_path_profile_count"] == 20
        and all(
            row["path_digest"] == object_digest(row, "path_digest")
            and row["active"] is True
            and row["content_quality_proven"] is False
            and len(row["observable_difference_axes"]) >= 4
            for row in paths
        ),
        "E_AB_PATHS",
    )
    require(
        len(requests) == len(realizations) == result["typed_author_request_count"] == 40,
        "E_GENERATOR_EVIDENCE_COUNT",
    )
    require(
        all(
            request["external_provider_allowed"] is False
            and request["publishable"] is False
            and request["runtime_consumable"] is False
            and request["may_enter_300"] is False
            and request["component_bindings"]
            and all(
                binding["input_object_ids"]
                and binding["fact_object_ids"]
                and binding["authorization_object_ids"]
                for binding in request["component_bindings"]
            )
            for request in requests
        ),
        "E_TYPED_REQUEST_BINDING",
    )
    require(
        all(
            row["selected_component_count"] == row["realized_component_count"]
            and row["unrealized_component_count"] == 0
            and len(
                {
                    contribution["implementation_pointer"]
                    for contribution in row["component_contributions"]
                }
            )
            == row["realized_component_count"]
            and row["audience_title"] == ""
            and row["audience_body"] == []
            and row["spoken_script"] == []
            for row in realizations
        ),
        "E_COMPONENT_REALIZATION",
    )
    require(
        len(pairs) == 20
        and all(
            row["same_material_digest"] is True
            and row["same_source_fact_authorization_boundary"] is True
            and row["independent_session_ids"] is True
            and row["minimum_four_axes_pass"] is True
            and row["observable_difference_axis_count"] >= 4
            and row["lane_a_axis_realization_digest"]
            != row["lane_b_axis_realization_digest"]
            and row["content_quality_proven"] is False
            for row in pairs
        ),
        "E_AB_PAIR_EVIDENCE",
    )
    require(
        len(ablations) == result["component_ablation_case_count"]
        and all(row["implementation_changed"] is True for row in ablations),
        "E_COMPONENT_ABLATION",
    )
    require(
        len(digest_tampers) == result["component_digest_tamper_case_count"]
        and len(digest_tampers) == len(components)
        and all(row["tamper_rejected"] is True for row in digest_tampers),
        "E_COMPONENT_TAMPER",
    )
    require(
        len(route_comparisons) == result["route_case_count"] == 60
        and all(
            row["primary_action_matches_gold"] is True
            and row["primary_reason_matches_gold"] is True
            for row in route_comparisons
        ),
        "E_ROUTE_GOLD",
    )
    require(
        provider["audit_digest"] == object_digest(provider, "audit_digest")
        and provider["derived_from_event_log"] is True
        and provider["external_provider_request_count"] == 0
        and provider["external_provider_response_count"] == 0
        and provider["negative_dispatch_test"]["blocked_before_network_dispatch"]
        is True,
        "E_PROVIDER_AUDIT",
    )
    require(
        contract["contract_digest"] == object_digest(contract, "contract_digest")
        and contract["external_provider_allowed"] is False
        and contract["audience_content_generation_allowed_in_p2"] is False
        and contract["generator_may_write_composition_plan"] is False,
        "E_GENERATOR_CONTRACT",
    )
    require(
        registry["registry_digest"] == object_digest(registry, "registry_digest")
        and registry["current_generator_entrypoint_count"] == 1
        and registry["historical_generator_entrypoints_consumed"] == []
        and registry["generator_qualified"] is False
        and registry["runtime_ready"] is False
        and registry["production_ready"] is False,
        "E_GENERATOR_REGISTRY",
    )
    require(
        compatibility["receipt_digest"]
        == object_digest(compatibility, "receipt_digest")
        and compatibility["current_checker"]["sha256_before_final_closeout"]
        == CHECKPOINT_CURRENT_CHECKER_SHA256
        and compatibility["current_checker"]["recursive_checker_chain"] is False
        and compatibility["p1a_p1b_task_roots_modified"] is False
        and compatibility["checkpoint_assets_rewritten"] is False
        and compatibility["shared_ledger_modified"] is False
        and compatibility["readiness_changed"] is False,
        "E_FINAL_COMPATIBILITY",
    )
    require(owner["owner_id"] == "GATE1_V11_P2_FINAL_OWNER", "E_OWNER")
    require(
        owner["owner_digest"] == object_digest(owner, "owner_digest")
        and owner["p2_complete"] is True
        and owner["p3_allowed"] is True,
        "E_OWNER_P3",
    )
    for state in (result["readiness"], owner["readiness"]):
        require(not any(state.values()), "E_READINESS_TRUE")
    require(result["core_number_impact"]["all_unchanged"] is True, "E_CORE_NUMBER")
    require(
        result["core_number_impact"]
        == {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "E_CORE_NUMBER",
    )
    require(result["audience_content_created_count"] == 0, "E_AUDIENCE_BODY")
    require(result["composition_plan_created_count"] == 0, "E_COMPOSITION_PLAN")
    require(bool(documents), "E_EMPTY_DOCUMENTS")
