#!/usr/bin/env python3
"""Materialize the final P2 closeout from imported independent reviews."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from p2_component_model import (
    AB_PATH,
    COMPONENT_CANDIDATES_PATH,
    CONTROL_RULES_PATH,
    CURRENT_CHECKER_PATH,
    CURRENT_OWNER_PATH,
    EDGE_PATH,
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
    build_active_ab_paths,
    build_active_components,
    build_active_control_rules,
    build_active_edge_lifecycle,
    build_approved_supply,
    build_generator_contract,
    build_generator_evidence,
    build_generator_registry,
    build_provider_audit,
    build_review_closeout,
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


if not __debug__:
    sys.stderr.write("P2 final materializer refuses python -O\n")
    raise SystemExit(2)


PRIMARY_IMPORT_DIR = TASK_ROOT / "imports/independent_reviews/primary"
SECONDARY_IMPORT_DIR = TASK_ROOT / "imports/independent_reviews/secondary"
IMPORT_MANIFEST_PATH = (
    TASK_ROOT / "imports/independent_review_import_manifest.v0.1.yaml"
)
COMBINED_REVIEW_PATH = TASK_ROOT / "review/combined_review_records.v0.1.jsonl"
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
FINAL_RESULT_PATH = TASK_ROOT / "result/p2_final_result.v0.1.yaml"
ROUTE_INPUT_PATH = Path(
    "controlled_content_generator_v2_001/"
    "creative_authoring_route_oracle_convergence_001/route/route_inputs.v0.1.jsonl"
)


def _review_files(relative_dir: Path) -> list[Path]:
    return [
        relative_dir / "records.jsonl",
        relative_dir / "report.md",
        relative_dir / "run_manifest.yaml",
    ]


def _build_import_manifest(
    root: Path,
    primary_summary: dict[str, Any],
    secondary_summary: dict[str, Any],
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for role, relative_dir in (
        ("primary", PRIMARY_IMPORT_DIR),
        ("secondary", SECONDARY_IMPORT_DIR),
    ):
        for path in _review_files(relative_dir):
            files.append(
                {
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
        "reviewer_identities": {
            "primary": primary_summary,
            "secondary": secondary_summary,
        },
        "reviewers_are_distinct": (
            primary_summary["reviewer_identity_id"]
            != secondary_summary["reviewer_identity_id"]
            and primary_summary["reviewer_instance_or_session_id"]
            != secondary_summary["reviewer_instance_or_session_id"]
            and primary_summary["review_run_id"] != secondary_summary["review_run_id"]
        ),
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
    return {
        "current_gate1_owner": {
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
    }


def _result_document(
    active_components: list[dict[str, Any]],
    active_edges: list[dict[str, Any]],
    active_rules: list[dict[str, Any]],
    active_paths: list[dict[str, Any]],
    combined: list[dict[str, Any]],
    evidence: dict[str, list[dict[str, Any]]],
    route_comparisons: list[dict[str, Any]],
    provider_audit: dict[str, Any],
) -> dict[str, Any]:
    disposition_counts = {
        decision: sum(row["combined_disposition"] == decision for row in combined)
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
        "independent_review_record_count_per_reviewer": 244,
        "independent_review_disposition_counts": disposition_counts,
        "unresolved_review_disagreement_count": 0,
        "self_approval_count": 0,
        "active_component_count": len(active_components),
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


def build_final_documents(root: Path = ROOT) -> dict[Path, bytes]:
    state = source_state(root)
    packet = load_jsonl(root / REVIEW_PACKET_PATH)
    require(sha256_file(root / REVIEW_PACKET_PATH) == PACKET_SHA256, "E_PACKET_PIN")
    primary, primary_summary = load_review_directory(
        root / PRIMARY_IMPORT_DIR, packet, PRIMARY_ROLE
    )
    secondary, secondary_summary = load_review_directory(
        root / SECONDARY_IMPORT_DIR, packet, SECONDARY_ROLE
    )
    require(
        primary_summary["reviewer_identity_id"]
        != secondary_summary["reviewer_identity_id"],
        "E_REVIEW_IDENTITY_COLLISION",
    )
    require(
        primary_summary["reviewer_instance_or_session_id"]
        != secondary_summary["reviewer_instance_or_session_id"],
        "E_REVIEW_SESSION_COLLISION",
    )
    require(
        primary_summary["review_run_id"] != secondary_summary["review_run_id"],
        "E_REVIEW_RUN_COLLISION",
    )
    combined, disagreements = combine_reviews(packet, primary, secondary)
    require(
        not disagreements, "E_REVIEW_ADJUDICATION_REQUIRED", str(len(disagreements))
    )
    components = load_jsonl(root / COMPONENT_CANDIDATES_PATH)
    control_rules = load_jsonl(root / CONTROL_RULES_PATH)
    edge_candidates = load_jsonl(root / EDGE_PATH)
    path_candidates = load_jsonl(root / AB_PATH)
    active_components = build_active_components(components, edge_candidates, combined)
    active_component_by_id = {row["component_id"]: row for row in active_components}
    approved_packet_ids = {
        row["packet_item_id"]
        for row in combined
        if row["combined_disposition"] == "APPROVE"
    }
    approved_edge_candidates = [
        row
        for row in edge_candidates
        if f"P2-{row['edge_id']}" in approved_packet_ids
        and row["component_id"] in active_component_by_id
    ]
    active_edges = build_active_edge_lifecycle(
        approved_edge_candidates, active_component_by_id
    )
    active_rules = build_active_control_rules(control_rules, combined)
    require(len(active_rules) == 8, "E_CONTROL_RULE_REVIEW_GAP", str(len(active_rules)))
    supply = build_approved_supply(state["profiles"], active_edges)
    require(
        supply["approved_component_supply_matrix"]["approved_complete_profile_count"]
        == 20,
        "E_COMPONENT_SUPPLY_GAP",
    )
    active_paths = build_active_ab_paths(
        path_candidates, set(active_component_by_id), combined
    )
    require(len(active_paths) == 20, "E_AB_PATH_REVIEW_GAP", str(len(active_paths)))
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
    review_closeout = build_review_closeout(
        combined, primary_summary, secondary_summary
    )
    require(
        review_closeout["independent_component_review_closeout"][
            "unresolved_disagreement_count"
        ]
        == 0,
        "E_REVIEW_DISAGREEMENT",
    )
    import_manifest = _build_import_manifest(root, primary_summary, secondary_summary)
    generator_contract = build_generator_contract()
    generator_registry = build_generator_registry(root, active_components, active_edges)
    result = _result_document(
        active_components,
        active_edges,
        active_rules,
        active_paths,
        combined,
        evidence,
        route_comparisons,
        provider_audit,
    )
    owner = _owner_document(
        len(active_components), len(active_edges), len(active_rules)
    )
    return {
        IMPORT_MANIFEST_PATH: yaml_bytes(import_manifest),
        COMBINED_REVIEW_PATH: jsonl_bytes(combined),
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
        FINAL_RESULT_PATH: yaml_bytes(result),
        CURRENT_OWNER_PATH: yaml_bytes(owner),
    }


def validate_final_documents(documents: dict[Path, bytes]) -> None:
    result = yaml.safe_load(documents[FINAL_RESULT_PATH])["p2_final_result"]
    owner = yaml.safe_load(documents[CURRENT_OWNER_PATH])["current_gate1_owner"]
    supply = yaml.safe_load(documents[APPROVED_SUPPLY_PATH])[
        "approved_component_supply_matrix"
    ]
    components = [
        json.loads(line)
        for line in documents[ACTIVE_COMPONENTS_PATH].decode("utf-8").splitlines()
    ]
    edges = [
        json.loads(line)
        for line in documents[ACTIVE_EDGES_PATH].decode("utf-8").splitlines()
    ]
    require(result["result_state"] == "PASS_TO_P3_OPEN_PROBE", "E_RESULT_STATE")
    require(result["p2_complete"] is True and result["p3_allowed"] is True, "E_P3")
    require(supply["approved_complete_profile_count"] == 20, "E_SUPPLY")
    require(len(components) == result["active_component_count"], "E_COMPONENT_COUNT")
    require(len(edges) == result["active_edge_count"], "E_EDGE_COUNT")
    require(
        all(
            row["component_digest"] == object_digest(row, "component_digest")
            for row in components
        ),
        "E_COMPONENT_DIGEST",
    )
    require(
        all(row["edge_digest"] == object_digest(row, "edge_digest") for row in edges),
        "E_EDGE_DIGEST",
    )
    require(owner["owner_id"] == "GATE1_V11_P2_FINAL_OWNER", "E_OWNER")
    require(owner["p3_allowed"] is True, "E_OWNER_P3")
    for state in (result["readiness"], owner["readiness"]):
        require(not any(state.values()), "E_READINESS_TRUE")
    require(result["core_number_impact"]["all_unchanged"] is True, "E_CORE_NUMBER")
    serialized = b"".join(documents.values()).decode("utf-8")
    require('"audience_body":["' not in serialized, "E_AUDIENCE_BODY")
    require("CompositionPlan" not in serialized, "E_COMPOSITION_PLAN")
    require(bool(documents), "E_EMPTY_DOCUMENTS")
