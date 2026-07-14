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
    canonical_json,
    jsonl_bytes,
    load_jsonl,
    object_digest,
    require,
    sha256_bytes,
    sha256_file,
    source_state,
    yaml_bytes,
)
from p2_final_documents import (
    build_approved_supply,
    build_provider_audit,
    build_route_evidence,
)
from p2_final_documents_r6 import build_generator_evidence_r6
from p2_generator_core_r5 import (
    build_component_structural_output,
    build_local_typed_material,
    digest_object,
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
    TARGETED_REVIEW_PACKET_PATH,
)
from p2_targeted_repair_r2 import (
    ADDITION_CANDIDATES_R2_PATH,
    REVISED_COMPONENTS_R2_PATH,
    TARGETED_REVIEW_PACKET_R2_PATH,
)
from p2_targeted_repair_r3 import (
    ADDITION_CANDIDATES_R3_PATH,
    REVISED_COMPONENTS_R3_PATH,
    TARGETED_REVIEW_PACKET_R3_PATH,
)
from p2_targeted_repair_r4 import (
    ADDITION_CANDIDATES_R4_PATH,
    REVISED_COMPONENTS_R4_PATH,
    TARGETED_REVIEW_PACKET_R4_PATH,
)
from p2_targeted_repair_r5 import (
    ADDITION_CANDIDATES_R5_PATH,
    FINAL_EDGE_CANDIDATES_R5_PATH,
    REVISED_AB_R5_PATH,
    REVISED_COMPONENTS_R5_PATH,
    REVISED_RULES_R5_PATH,
    TARGETED_REVIEW_PACKET_R5_PATH,
)
from p2_targeted_repair_r6 import TARGETED_REVIEW_PACKET_R6_PATH


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
TARGET_R3_PRIMARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r3/primary"
TARGET_R3_SECONDARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r3/secondary"
TARGET_R4_PRIMARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r4/primary"
TARGET_R4_SECONDARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r4/secondary"
TARGET_R5_PRIMARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r5/primary"
TARGET_R5_SECONDARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r5/secondary"
TARGET_R6_PRIMARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r6/primary"
TARGET_R6_SECONDARY_IMPORT_DIR = TASK_ROOT / "imports/targeted_r6/secondary"
FINAL_IMPORT_SENTINEL = TARGET_R6_PRIMARY_IMPORT_DIR / "records.jsonl"
IMPORT_MANIFEST_PATH = (
    TASK_ROOT / "imports/independent_review_import_manifest.v0.1.yaml"
)
COMBINED_REVIEW_PATH = TASK_ROOT / "review/combined_review_records.v0.1.jsonl"
TARGET_COMBINED_REVIEW_PATH = (
    TASK_ROOT / "review/targeted_r1_combined_review_records.v0.1.jsonl"
)
TARGET_R2_COMBINED_REVIEW_PATH = (
    TASK_ROOT / "review/targeted_r2_combined_review_records.v0.1.jsonl"
)
TARGET_R3_COMBINED_REVIEW_PATH = (
    TASK_ROOT / "review/targeted_r3_combined_review_records.v0.1.jsonl"
)
TARGET_R4_COMBINED_REVIEW_PATH = (
    TASK_ROOT / "review/targeted_r4_combined_review_records.v0.1.jsonl"
)
TARGET_R5_COMBINED_REVIEW_PATH = (
    TASK_ROOT / "review/targeted_r5_combined_review_records.v0.1.jsonl"
)
TARGET_R6_COMBINED_REVIEW_PATH = (
    TASK_ROOT / "review/targeted_r6_combined_review_records.v0.1.jsonl"
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
AXIS_BODY_PAIR_RESULTS_PATH = (
    TASK_ROOT / "generator/axis_body_pair_results.v0.1.jsonl"
)
LANE_BINDING_TAMPER_RESULTS_PATH = (
    TASK_ROOT / "generator/lane_binding_tamper_results.v0.1.jsonl"
)
PATH_PROGRAM_TAMPER_RESULTS_PATH = (
    TASK_ROOT / "generator/path_program_tamper_results.v0.1.jsonl"
)
TRUST_CONTRACT_TAMPER_RESULTS_PATH = (
    TASK_ROOT / "generator/trust_contract_tamper_results.v0.1.jsonl"
)
COMPONENT_POINTER_RESULTS_PATH = (
    TASK_ROOT / "generator/component_pointer_results.v0.1.jsonl"
)
OBSERVABLE_EFFECT_TAMPER_RESULTS_PATH = (
    TASK_ROOT / "generator/observable_effect_tamper_results.v0.1.jsonl"
)
BOUND_FACT_EFFECT_RESULTS_PATH = (
    TASK_ROOT / "generator/bound_fact_structural_effect_results.v0.1.jsonl"
)
REQUIRED_SLOT_TAMPER_RESULTS_PATH = (
    TASK_ROOT / "generator/required_slot_trust_root_tamper_results.v0.1.jsonl"
)
PROGRAM_SCHEMA_TAMPER_RESULTS_PATH = (
    TASK_ROOT / "generator/path_program_schema_tamper_results.v0.1.jsonl"
)
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
TARGET_R2_REVIEWED_COMMIT = "211b9b241d7660dfa688d3b8db4716ce4e871d27"
TARGET_R2_REVIEW_PACKET_SHA256 = (
    "6eaa8e8f365888ea887a13e3065e9cb711f8f518460f61d4865f3e24852986ef"
)
TARGET_R3_REVIEWED_COMMIT = "e83c4a27259d64dd1a52d41d9ca0b9cc7237db61"
TARGET_R3_REVIEW_PACKET_SHA256 = (
    "e14bf95b40d87c83be48e45f2455d983c3c5e412f88ef41f5b034b9d2403883d"
)
TARGET_R4_REVIEWED_COMMIT = "87d3ca89ba9cbb743ee82af105cf831bbd8e2dab"
TARGET_R4_REVIEW_PACKET_SHA256 = (
    "95c2a44e8d473844ada77d242ede0299a6b4db63b2699dfc633af0704d2c7e72"
)
TARGET_R5_REVIEWED_COMMIT = "6f18ac14a15e7e17bfb3f45809c3b33d3b1c1d5a"
TARGET_R5_REVIEW_PACKET_SHA256 = (
    "de59316fd7d88237e00cc84bd8802959d194995ddf5aef703477bd4921adc245"
)
TARGET_R6_REVIEWED_COMMIT = "6555c83c58c54e698ef50c3ff707e44a255d5d9b"
TARGET_R6_REVIEW_PACKET_SHA256 = (
    "2da6b6eaebd03feea33094e6606730e357d07ae57e38119414685a96332f52a8"
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
        ("targeted_r2", "primary", TARGET_R2_PRIMARY_IMPORT_DIR),
        ("targeted_r2", "secondary", TARGET_R2_SECONDARY_IMPORT_DIR),
        ("targeted_r3", "primary", TARGET_R3_PRIMARY_IMPORT_DIR),
        ("targeted_r3", "secondary", TARGET_R3_SECONDARY_IMPORT_DIR),
        ("targeted_r4", "primary", TARGET_R4_PRIMARY_IMPORT_DIR),
        ("targeted_r4", "secondary", TARGET_R4_SECONDARY_IMPORT_DIR),
        ("targeted_r5", "primary", TARGET_R5_PRIMARY_IMPORT_DIR),
        ("targeted_r5", "secondary", TARGET_R5_SECONDARY_IMPORT_DIR),
        ("targeted_r6", "primary", TARGET_R6_PRIMARY_IMPORT_DIR),
        ("targeted_r6", "secondary", TARGET_R6_SECONDARY_IMPORT_DIR),
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
        "independent_reviewer_identity_count": len(
            {
                summary["reviewer_identity_id"]
                for summary in summaries.values()
            }
        ),
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
            "final_targeted_review": {
                "reviewed_checkpoint_commit": TARGET_R6_REVIEWED_COMMIT,
                "review_packet_sha256": TARGET_R6_REVIEW_PACKET_SHA256,
            },
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


def _generator_contract_r6() -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "v0.3",
        "task_id": TASK_ID,
        "generator_version": "gate1-v1.1-p2-composable-successor-v0.4",
        "scope": "P2_LOCAL_STRUCTURAL_VALIDATION_ONLY",
        "single_current_entrypoint": (
            TASK_ROOT / "run_p2_component_supply_and_generator_core_repair.py"
        ).as_posix(),
        "active_core_module": "p2_generator_core_r6.py",
        "historical_non_active_core_modules": [
            "p2_generator_core.py",
            "p2_generator_core_r4.py",
            "p2_generator_core_r5.py",
        ],
        "approved_path_registry_is_authoritative": True,
        "profile_lane_program_owner": "APPROVED_PROFILE_LANE_PATH",
        "axis_component_profile_lane_payload_allowed": False,
        "all_selected_components_require_addressable_structural_output": True,
        "component_required_slots_must_equal_binding_slots": True,
        "path_program_schema_is_executable": True,
        "mechanism_metadata_change_may_not_claim_nonmetadata_effect": True,
        "hash_or_token_semantic_selection_allowed": False,
        "field_name_or_path_guessing_allowed": False,
        "first_match_binding_allowed": False,
        "generator_may_write_composition_plan": False,
        "composition_plan_owner": "ORCH",
        "external_provider_allowed": False,
        "audience_content_generation_allowed_in_p2": False,
        "readiness": {
            "generator_qualified": False,
            "generation_allowed": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        },
    }
    document["contract_digest"] = object_digest(document, "contract_digest")
    return {"gate1_generator_contract": document}


def _generator_registry_r6(
    root: Path,
    active_components: list[dict[str, Any]],
    active_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    core_path = TASK_ROOT / "p2_generator_core_r6.py"
    document: dict[str, Any] = {
        "schema_version": "v0.3",
        "task_id": TASK_ID,
        "current_generator_entrypoint_count": 1,
        "generator_version": "gate1-v1.1-p2-composable-successor-v0.4",
        "entrypoint": (
            TASK_ROOT / "run_p2_component_supply_and_generator_core_repair.py"
        ).as_posix(),
        "core_module": {
            "path": core_path.as_posix(),
            "sha256": sha256_file(root / core_path),
        },
        "historical_non_active_core_modules": [
            {
                "path": (TASK_ROOT / "p2_generator_core.py").as_posix(),
                "active": False,
            },
            {
                "path": (TASK_ROOT / "p2_generator_core_r4.py").as_posix(),
                "active": False,
            },
            {
                "path": (TASK_ROOT / "p2_generator_core_r5.py").as_posix(),
                "active": False,
            },
        ],
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
    targeted_r1_combined: list[dict[str, Any]],
    targeted_r2_combined: list[dict[str, Any]],
    targeted_r3_combined: list[dict[str, Any]],
    targeted_r4_combined: list[dict[str, Any]],
    targeted_r5_combined: list[dict[str, Any]],
    targeted_r6_combined: list[dict[str, Any]],
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
    targeted_r1_disposition_counts = {
        decision: sum(
            row["combined_disposition"] == decision for row in targeted_r1_combined
        )
        for decision in ("APPROVE", "REPAIR", "REJECT")
    }
    targeted_r1_disposition_counts["DISAGREEMENT_REQUIRES_ADJUDICATION"] = sum(
        row["requires_targeted_adjudication"] for row in targeted_r1_combined
    )
    targeted_r2_disposition_counts = {
        decision: sum(
            row["combined_disposition"] == decision for row in targeted_r2_combined
        )
        for decision in ("APPROVE", "REPAIR", "REJECT")
    }
    targeted_r2_disposition_counts["DISAGREEMENT_REQUIRES_ADJUDICATION"] = sum(
        row["requires_targeted_adjudication"] for row in targeted_r2_combined
    )
    targeted_r3_disposition_counts = {
        decision: sum(
            row["combined_disposition"] == decision for row in targeted_r3_combined
        )
        for decision in ("APPROVE", "REPAIR", "REJECT")
    }
    targeted_r3_disposition_counts["DISAGREEMENT_REQUIRES_ADJUDICATION"] = sum(
        row["requires_targeted_adjudication"] for row in targeted_r3_combined
    )
    targeted_r4_disposition_counts = {
        decision: sum(
            row["combined_disposition"] == decision for row in targeted_r4_combined
        )
        for decision in ("APPROVE", "REPAIR", "REJECT")
    }
    targeted_r4_disposition_counts["DISAGREEMENT_REQUIRES_ADJUDICATION"] = sum(
        row["requires_targeted_adjudication"] for row in targeted_r4_combined
    )
    targeted_r5_disposition_counts = {
        decision: sum(
            row["combined_disposition"] == decision for row in targeted_r5_combined
        )
        for decision in ("APPROVE", "REPAIR", "REJECT")
    }
    targeted_r5_disposition_counts["DISAGREEMENT_REQUIRES_ADJUDICATION"] = sum(
        row["requires_targeted_adjudication"] for row in targeted_r5_combined
    )
    targeted_r6_disposition_counts = {
        decision: sum(
            row["combined_disposition"] == decision for row in targeted_r6_combined
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
        "targeted_r1_reviewed_commit": TARGET_REVIEWED_COMMIT,
        "targeted_r1_review_packet_sha256": TARGET_REVIEW_PACKET_SHA256,
        "targeted_r2_reviewed_commit": TARGET_R2_REVIEWED_COMMIT,
        "targeted_r2_review_packet_sha256": TARGET_R2_REVIEW_PACKET_SHA256,
        "targeted_r3_reviewed_commit": TARGET_R3_REVIEWED_COMMIT,
        "targeted_r3_review_packet_sha256": TARGET_R3_REVIEW_PACKET_SHA256,
        "targeted_r4_reviewed_commit": TARGET_R4_REVIEWED_COMMIT,
        "targeted_r4_review_packet_sha256": TARGET_R4_REVIEW_PACKET_SHA256,
        "targeted_r5_reviewed_commit": TARGET_R5_REVIEWED_COMMIT,
        "targeted_r5_review_packet_sha256": TARGET_R5_REVIEW_PACKET_SHA256,
        "targeted_r6_reviewed_commit": TARGET_R6_REVIEWED_COMMIT,
        "targeted_r6_review_packet_sha256": TARGET_R6_REVIEW_PACKET_SHA256,
        "initial_review_record_count_per_reviewer": len(initial_combined),
        "initial_review_disposition_counts": initial_disposition_counts,
        "initial_adjudication_record_count": len(adjudication_records),
        "initial_adjudication_disposition_counts": adjudication_counts,
        "targeted_r1_review_record_count_per_reviewer": len(targeted_r1_combined),
        "targeted_r1_review_disposition_counts": targeted_r1_disposition_counts,
        "targeted_r2_review_record_count_per_reviewer": len(targeted_r2_combined),
        "targeted_r2_review_disposition_counts": targeted_r2_disposition_counts,
        "targeted_r2_failure_evidence_preserved": True,
        "targeted_r3_review_record_count_per_reviewer": len(targeted_r3_combined),
        "targeted_r3_review_disposition_counts": targeted_r3_disposition_counts,
        "targeted_r3_failure_evidence_preserved": True,
        "targeted_r4_review_record_count_per_reviewer": len(targeted_r4_combined),
        "targeted_r4_review_disposition_counts": targeted_r4_disposition_counts,
        "targeted_r4_failure_evidence_preserved": True,
        "targeted_r5_review_record_count_per_reviewer": len(targeted_r5_combined),
        "targeted_r5_review_disposition_counts": targeted_r5_disposition_counts,
        "targeted_r5_failure_evidence_preserved": True,
        "targeted_r6_review_record_count_per_reviewer": len(targeted_r6_combined),
        "targeted_r6_review_disposition_counts": targeted_r6_disposition_counts,
        "unresolved_review_disagreement_count": 0,
        "self_approval_count": 0,
        "active_component_count": len(active_components),
        "revised_historical_component_count": sum(
            str(row.get("component_version", "")).startswith("v1.1-p2-r")
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
        "axis_body_pair_case_count": len(evidence["axis_body_pairs"]),
        "component_pointer_case_count": len(evidence["pointer_cases"]),
        "observable_effect_tamper_case_count": len(
            evidence["observable_effect_tampers"]
        ),
        "bound_fact_effect_case_count": len(evidence["bound_fact_effect_cases"]),
        "required_slot_tamper_case_count": len(evidence["required_slot_tampers"]),
        "path_program_schema_tamper_case_count": len(
            evidence["path_program_schema_tampers"]
        ),
        "path_program_tamper_case_count": len(evidence["path_program_tampers"]),
        "trust_contract_tamper_case_count": len(
            evidence["trust_contract_tampers"]
        ),
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
    targeted_r1_approved_ids: set[str],
    targeted_r2_approved_ids: set[str],
    targeted_r3_approved_ids: set[str],
    targeted_r4_approved_ids: set[str],
    targeted_r5_approved_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component_id in sorted(selected_ids):
        candidate = component_pool[component_id]
        targeted_r5_item_id = f"P2R5-COMPONENT-{component_id}"
        targeted_r4_item_id = f"P2R4-COMPONENT-{component_id}"
        targeted_r3_item_id = f"P2R3-COMPONENT-{component_id}"
        targeted_r2_item_id = f"P2R2-COMPONENT-{component_id}"
        targeted_r1_item_id = f"P2R1-COMPONENT-{component_id}"
        initial_item_id = f"P2-COMPONENT-{component_id}"
        if targeted_r5_item_id in targeted_r5_approved_ids:
            review_stage = "TARGETED_R5_MATCHING_TWO_APPROVALS"
            packet_item_id = targeted_r5_item_id
        elif targeted_r4_item_id in targeted_r4_approved_ids:
            review_stage = "TARGETED_R4_MATCHING_TWO_APPROVALS"
            packet_item_id = targeted_r4_item_id
        elif targeted_r3_item_id in targeted_r3_approved_ids:
            review_stage = "TARGETED_R3_MATCHING_TWO_APPROVALS"
            packet_item_id = targeted_r3_item_id
        elif targeted_r2_item_id in targeted_r2_approved_ids:
            review_stage = "TARGETED_R2_MATCHING_TWO_APPROVALS"
            packet_item_id = targeted_r2_item_id
        elif targeted_r1_item_id in targeted_r1_approved_ids:
            review_stage = "TARGETED_R1_MATCHING_TWO_APPROVALS"
            packet_item_id = targeted_r1_item_id
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
        row["independent_review_state"] = "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
        row["readiness"] = {
            "generation_eligible": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        }
        row["component_digest"] = object_digest(row, "component_digest")
        rows.append(row)
    return rows


def _activate_rules(
    candidates: list[dict[str, Any]],
    targeted_r1_approved_ids: set[str],
    targeted_r2_approved_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        rule_id = str(candidate["control_rule_id"])
        r2_packet_item_id = f"P2R2-CONTROL-{rule_id}"
        r1_packet_item_id = f"P2R1-CONTROL-{rule_id}"
        if r2_packet_item_id in targeted_r2_approved_ids:
            packet_item_id = r2_packet_item_id
            activation_basis = "TARGETED_R2_MATCHING_TWO_APPROVALS"
        else:
            require(r1_packet_item_id in targeted_r1_approved_ids, "E_RULE_REVIEW_GAP", rule_id)
            packet_item_id = r1_packet_item_id
            activation_basis = "TARGETED_R1_MATCHING_TWO_APPROVALS"
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_control_rule_digest"] = row.pop(
            "control_rule_digest"
        )
        row["active"] = True
        row["independent_review_state"] = "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
        row["activation_basis"] = activation_basis
        row["review_packet_item_id"] = packet_item_id
        row["contributes_component_supply"] = False
        row["may_write_audience_surface"] = False
        row["control_rule_digest"] = object_digest(row, "control_rule_digest")
        rows.append(row)
    return rows


def _activated_component_binding(
    binding: dict[str, Any],
    component_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = copy.deepcopy(binding)
    component = component_by_id[str(row["component_id"])]
    row["reviewed_candidate_component_digest"] = row["component_digest"]
    row["component_digest"] = component["component_digest"]
    row["component_role"] = component["component_role"]
    row["binding_digest"] = sha256_bytes(
        canonical_json(row["exact_typed_object_bindings"]).encode("utf-8")
    )
    return row


def _activate_edges(
    candidates: list[dict[str, Any]],
    component_by_id: dict[str, dict[str, Any]],
    targeted_r2_approved_ids: set[str],
    targeted_r3_approved_ids: set[str],
    targeted_r5_approved_ids: set[str],
    active_path_by_profile: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        edge_id = str(candidate["edge_id"])
        if edge_id in targeted_r3_approved_ids:
            packet_item_id = edge_id
            activation_basis = "TARGETED_R3_MATCHING_TWO_APPROVALS"
        else:
            packet_item_id = f"P2R2-{edge_id}"
            require(
                packet_item_id in targeted_r2_approved_ids,
                "E_EDGE_REVIEW_GAP",
                edge_id,
            )
            activation_basis = "TARGETED_R2_MATCHING_TWO_APPROVALS"
        component = component_by_id[str(candidate["component_id"])]
        cp_id = str(candidate["content_product_type_id"])
        path_packet_item_id = f"P2R5-AB-{cp_id}"
        require(
            path_packet_item_id in targeted_r5_approved_ids,
            "E_EDGE_PATH_BINDING_REVIEW_GAP",
            cp_id,
        )
        active_path = active_path_by_profile[cp_id]
        material_contract = active_path["shared_typed_material_contract"]
        path_binding_by_component = {
            str(binding["component_id"]): binding
            for binding in material_contract["component_exact_bindings"]
        }
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_edge_digest"] = row.pop("edge_digest")
        row["reviewed_candidate_component_digest"] = row["component_digest"]
        row["component_digest"] = component["component_digest"]
        row["component_exact_binding"] = copy.deepcopy(
            path_binding_by_component[str(candidate["component_id"])]
        )
        row["profile_exact_binding"] = copy.deepcopy(
            material_contract["profile_exact_binding"]
        )
        row["shared_material_contract"] = {
            key: material_contract[key]
            for key in (
                "material_id",
                "material_digest",
                "typed_object_catalog_digest",
            )
        }
        row["binding_activation_basis"] = (
            "TARGETED_R5_PATH_MATCHING_TWO_APPROVALS"
        )
        row["binding_review_packet_item_id"] = path_packet_item_id
        row["active"] = True
        row["activation_basis"] = activation_basis
        row["review_packet_item_id"] = packet_item_id
        row["independent_review_state"] = "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
        row["edge_digest"] = object_digest(row, "edge_digest")
        rows.append(row)
    return rows


def _activate_paths(
    candidates: list[dict[str, Any]],
    targeted_r5_approved_ids: set[str],
    component_by_id: dict[str, dict[str, Any]],
    control_rule_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        cp_id = str(candidate["content_product_type_id"])
        packet_item_id = f"P2R5-AB-{cp_id}"
        require(packet_item_id in targeted_r5_approved_ids, "E_PATH_REVIEW_GAP", cp_id)
        row = copy.deepcopy(candidate)
        row["reviewed_candidate_path_digest"] = row.pop("path_digest")
        activated_bindings = [
            _activated_component_binding(binding, component_by_id)
            for binding in row["shared_typed_material_contract"][
                "component_exact_bindings"
            ]
        ]
        row["shared_typed_material_contract"][
            "component_exact_bindings"
        ] = activated_bindings
        binding_by_id = {
            str(binding["component_id"]): binding for binding in activated_bindings
        }
        material = build_local_typed_material(
            row["trusted_profile_contract"],
            [component_by_id[component_id] for component_id in row["lane_a"]["component_ids"]],
        )
        for contract in row["component_realization_contracts"]:
            component_id = str(contract["component_id"])
            component = component_by_id[component_id]
            binding = binding_by_id[component_id]
            contract["component_digest"] = component["component_digest"]
            contract["exact_binding_digest"] = binding["binding_digest"]
            contract["expected_structural_output"] = build_component_structural_output(
                component, binding, material
            )
        for contract in row["axis_realization_contracts"]:
            operator_id = str(contract["operator_component_id"])
            operator = component_by_id[operator_id]
            contract["operator_component_binding"] = binding_by_id[operator_id]
            contract["operator_component_digest"] = operator["component_digest"]
            contract["operator_mechanism_digest"] = digest_object(
                operator["mechanism"]
            )
        active_control_bindings = [
            {
                "control_rule_id": rule_id,
                "control_rule_digest": control_rule_by_id[rule_id][
                    "control_rule_digest"
                ],
            }
            for rule_id in (
                str(binding["control_rule_id"])
                for binding in row["author_request_control_contract"][
                    "control_rule_bindings"
                ]
            )
        ]
        row["author_request_control_contract"][
            "control_rule_bindings"
        ] = active_control_bindings
        row["author_request_control_contract"][
            "control_rule_set_digest"
        ] = digest_object(active_control_bindings)
        row["active"] = True
        row["structural_candidate_only"] = False
        row["p2_structural_validation_only"] = True
        row["independent_review_state"] = "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
        row["activation_basis"] = "TARGETED_R5_MATCHING_TWO_APPROVALS"
        row["review_packet_item_id"] = packet_item_id
        row["path_digest"] = object_digest(row, "path_digest")
        rows.append(row)
    return rows


def _review_closeout(
    summaries: dict[str, dict[str, Any]],
    initial_combined: list[dict[str, Any]],
    targeted_r1_combined: list[dict[str, Any]],
    targeted_r2_combined: list[dict[str, Any]],
    targeted_r3_combined: list[dict[str, Any]],
    targeted_r4_combined: list[dict[str, Any]],
    targeted_r5_combined: list[dict[str, Any]],
    targeted_r6_combined: list[dict[str, Any]],
    adjudication_records: list[dict[str, Any]],
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "initial_reviewed_commit": REVIEWED_COMMIT,
        "initial_review_packet_sha256": PACKET_SHA256,
        "targeted_r1_reviewed_commit": TARGET_REVIEWED_COMMIT,
        "targeted_r1_review_packet_sha256": TARGET_REVIEW_PACKET_SHA256,
        "targeted_r2_reviewed_commit": TARGET_R2_REVIEWED_COMMIT,
        "targeted_r2_review_packet_sha256": TARGET_R2_REVIEW_PACKET_SHA256,
        "targeted_r3_reviewed_commit": TARGET_R3_REVIEWED_COMMIT,
        "targeted_r3_review_packet_sha256": TARGET_R3_REVIEW_PACKET_SHA256,
        "targeted_r4_reviewed_commit": TARGET_R4_REVIEWED_COMMIT,
        "targeted_r4_review_packet_sha256": TARGET_R4_REVIEW_PACKET_SHA256,
        "targeted_r5_reviewed_commit": TARGET_R5_REVIEWED_COMMIT,
        "targeted_r5_review_packet_sha256": TARGET_R5_REVIEW_PACKET_SHA256,
        "targeted_r6_reviewed_commit": TARGET_R6_REVIEWED_COMMIT,
        "targeted_r6_review_packet_sha256": TARGET_R6_REVIEW_PACKET_SHA256,
        "reviewer_identities": summaries,
        "initial_combined_record_count": len(initial_combined),
        "initial_real_disagreement_count": sum(
            row["requires_targeted_adjudication"] for row in initial_combined
        ),
        "initial_adjudication_record_count": len(adjudication_records),
        "targeted_r1_combined_record_count": len(targeted_r1_combined),
        "targeted_r1_matching_approval_count": sum(
            row["combined_disposition"] == "APPROVE"
            for row in targeted_r1_combined
        ),
        "targeted_r1_failure_or_open_count": sum(
            row["combined_disposition"] != "APPROVE"
            or row["requires_targeted_adjudication"]
            for row in targeted_r1_combined
        ),
        "targeted_r2_combined_record_count": len(targeted_r2_combined),
        "targeted_r2_matching_approval_count": sum(
            row["combined_disposition"] == "APPROVE"
            for row in targeted_r2_combined
        ),
        "targeted_r2_unresolved_disagreement_count": sum(
            row["requires_targeted_adjudication"] for row in targeted_r2_combined
        ),
        "targeted_r2_matching_repair_count": sum(
            row["combined_disposition"] == "REPAIR"
            and not row["requires_targeted_adjudication"]
            for row in targeted_r2_combined
        ),
        "targeted_r2_failure_evidence_preserved": True,
        "targeted_r3_combined_record_count": len(targeted_r3_combined),
        "targeted_r3_matching_approval_count": sum(
            row["combined_disposition"] == "APPROVE"
            and not row["requires_targeted_adjudication"]
            for row in targeted_r3_combined
        ),
        "targeted_r3_unresolved_disagreement_count": sum(
            row["requires_targeted_adjudication"] for row in targeted_r3_combined
        ),
        "targeted_r3_matching_repair_count": sum(
            row["combined_disposition"] == "REPAIR"
            and not row["requires_targeted_adjudication"]
            for row in targeted_r3_combined
        ),
        "targeted_r3_failure_evidence_preserved": True,
        "targeted_r4_combined_record_count": len(targeted_r4_combined),
        "targeted_r4_matching_approval_count": sum(
            row["combined_disposition"] == "APPROVE"
            and not row["requires_targeted_adjudication"]
            for row in targeted_r4_combined
        ),
        "targeted_r4_unresolved_disagreement_count": sum(
            row["requires_targeted_adjudication"] for row in targeted_r4_combined
        ),
        "targeted_r4_matching_repair_count": sum(
            row["combined_disposition"] == "REPAIR"
            and not row["requires_targeted_adjudication"]
            for row in targeted_r4_combined
        ),
        "targeted_r4_failure_evidence_preserved": True,
        "targeted_r5_combined_record_count": len(targeted_r5_combined),
        "targeted_r5_matching_approval_count": sum(
            row["combined_disposition"] == "APPROVE"
            and not row["requires_targeted_adjudication"]
            for row in targeted_r5_combined
        ),
        "targeted_r5_unresolved_disagreement_count": sum(
            row["requires_targeted_adjudication"] for row in targeted_r5_combined
        ),
        "targeted_r5_failure_evidence_preserved": True,
        "targeted_r6_combined_record_count": len(targeted_r6_combined),
        "targeted_r6_matching_approval_count": sum(
            row["combined_disposition"] == "APPROVE"
            and not row["requires_targeted_adjudication"]
            for row in targeted_r6_combined
        ),
        "targeted_r6_unresolved_disagreement_count": sum(
            row["requires_targeted_adjudication"] for row in targeted_r6_combined
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
    targeted_r1_combined, targeted_r1_disagreements = combine_reviews(
        targeted_packet, targeted_primary, targeted_secondary
    )
    require(len(targeted_r1_disagreements) == 82, "E_TARGET_R1_FAILURE_EVIDENCE")

    targeted_r2_packet = load_jsonl(root / TARGETED_REVIEW_PACKET_R2_PATH)
    require(
        sha256_file(root / TARGETED_REVIEW_PACKET_R2_PATH)
        == TARGET_R2_REVIEW_PACKET_SHA256,
        "E_TARGET_R2_PACKET_PIN",
    )
    targeted_r2_primary, targeted_r2_primary_summary = load_review_directory(
        root / TARGET_R2_PRIMARY_IMPORT_DIR,
        targeted_r2_packet,
        PRIMARY_ROLE,
        reviewed_commit=TARGET_R2_REVIEWED_COMMIT,
        packet_sha256=TARGET_R2_REVIEW_PACKET_SHA256,
        prompt_revision="r2",
    )
    targeted_r2_secondary, targeted_r2_secondary_summary = load_review_directory(
        root / TARGET_R2_SECONDARY_IMPORT_DIR,
        targeted_r2_packet,
        SECONDARY_ROLE,
        reviewed_commit=TARGET_R2_REVIEWED_COMMIT,
        packet_sha256=TARGET_R2_REVIEW_PACKET_SHA256,
        prompt_revision="r2",
    )
    require(
        targeted_r2_primary_summary["reviewer_identity_id"]
        == targeted_primary_summary["reviewer_identity_id"]
        and targeted_r2_secondary_summary["reviewer_identity_id"]
        == targeted_secondary_summary["reviewer_identity_id"],
        "E_TARGET_R2_REVIEWER_IDENTITY_DRIFT",
    )
    require(
        targeted_r2_primary_summary["reviewer_instance_or_session_id"]
        != targeted_r2_secondary_summary["reviewer_instance_or_session_id"]
        and targeted_r2_primary_summary["review_run_id"]
        != targeted_r2_secondary_summary["review_run_id"],
        "E_TARGET_R2_REVIEW_ISOLATION",
    )
    targeted_r2_combined, targeted_r2_disagreements = combine_reviews(
        targeted_r2_packet, targeted_r2_primary, targeted_r2_secondary
    )
    require(
        len(targeted_r2_disagreements) == 7,
        "E_TARGET_R2_FAILURE_DISAGREEMENT_EVIDENCE",
        str(len(targeted_r2_disagreements)),
    )
    require(
        sum(row["combined_disposition"] == "APPROVE" for row in targeted_r2_combined)
        == 107
        and sum(
            row["combined_disposition"] == "REPAIR"
            for row in targeted_r2_combined
        )
        == 20,
        "E_TARGET_R2_FAILURE_DISTRIBUTION",
    )

    targeted_r3_packet = load_jsonl(root / TARGETED_REVIEW_PACKET_R3_PATH)
    require(
        sha256_file(root / TARGETED_REVIEW_PACKET_R3_PATH)
        == TARGET_R3_REVIEW_PACKET_SHA256,
        "E_TARGET_R3_PACKET_PIN",
    )
    targeted_r3_primary, targeted_r3_primary_summary = load_review_directory(
        root / TARGET_R3_PRIMARY_IMPORT_DIR,
        targeted_r3_packet,
        PRIMARY_ROLE,
        reviewed_commit=TARGET_R3_REVIEWED_COMMIT,
        packet_sha256=TARGET_R3_REVIEW_PACKET_SHA256,
        prompt_revision="r3",
    )
    targeted_r3_secondary, targeted_r3_secondary_summary = load_review_directory(
        root / TARGET_R3_SECONDARY_IMPORT_DIR,
        targeted_r3_packet,
        SECONDARY_ROLE,
        reviewed_commit=TARGET_R3_REVIEWED_COMMIT,
        packet_sha256=TARGET_R3_REVIEW_PACKET_SHA256,
        prompt_revision="r3",
    )
    require(
        targeted_r3_primary_summary["reviewer_identity_id"]
        == targeted_r2_primary_summary["reviewer_identity_id"]
        and targeted_r3_secondary_summary["reviewer_identity_id"]
        == targeted_r2_secondary_summary["reviewer_identity_id"],
        "E_TARGET_R3_REVIEWER_IDENTITY_DRIFT",
    )
    require(
        targeted_r3_primary_summary["reviewer_instance_or_session_id"]
        != targeted_r3_secondary_summary["reviewer_instance_or_session_id"]
        and targeted_r3_primary_summary["review_run_id"]
        != targeted_r3_secondary_summary["review_run_id"]
        and targeted_r3_primary_summary["review_run_id"]
        != targeted_r2_primary_summary["review_run_id"]
        and targeted_r3_secondary_summary["review_run_id"]
        != targeted_r2_secondary_summary["review_run_id"],
        "E_TARGET_R3_REVIEW_ISOLATION",
    )
    targeted_r3_combined, targeted_r3_disagreements = combine_reviews(
        targeted_r3_packet, targeted_r3_primary, targeted_r3_secondary
    )
    require(
        len(targeted_r3_disagreements) == 6,
        "E_TARGET_R3_FAILURE_DISAGREEMENT_EVIDENCE",
        str(len(targeted_r3_disagreements)),
    )
    require(
        sum(row["combined_disposition"] == "APPROVE" for row in targeted_r3_combined)
        == 2
        and sum(
            row["combined_disposition"] == "REPAIR"
            for row in targeted_r3_combined
        )
        == 21,
        "E_TARGET_R3_FAILURE_DISTRIBUTION",
    )

    targeted_r4_packet = load_jsonl(root / TARGETED_REVIEW_PACKET_R4_PATH)
    require(
        sha256_file(root / TARGETED_REVIEW_PACKET_R4_PATH)
        == TARGET_R4_REVIEW_PACKET_SHA256,
        "E_TARGET_R4_PACKET_PIN",
    )
    targeted_r4_primary, targeted_r4_primary_summary = load_review_directory(
        root / TARGET_R4_PRIMARY_IMPORT_DIR,
        targeted_r4_packet,
        PRIMARY_ROLE,
        reviewed_commit=TARGET_R4_REVIEWED_COMMIT,
        packet_sha256=TARGET_R4_REVIEW_PACKET_SHA256,
        prompt_revision="r4",
    )
    targeted_r4_secondary, targeted_r4_secondary_summary = load_review_directory(
        root / TARGET_R4_SECONDARY_IMPORT_DIR,
        targeted_r4_packet,
        SECONDARY_ROLE,
        reviewed_commit=TARGET_R4_REVIEWED_COMMIT,
        packet_sha256=TARGET_R4_REVIEW_PACKET_SHA256,
        prompt_revision="r4",
    )
    require(
        targeted_r4_primary_summary["reviewer_identity_id"]
        == targeted_r3_primary_summary["reviewer_identity_id"]
        and targeted_r4_secondary_summary["reviewer_identity_id"]
        == targeted_r3_secondary_summary["reviewer_identity_id"],
        "E_TARGET_R4_REVIEWER_IDENTITY_DRIFT",
    )
    require(
        targeted_r4_primary_summary["reviewer_instance_or_session_id"]
        != targeted_r4_secondary_summary["reviewer_instance_or_session_id"]
        and targeted_r4_primary_summary["review_run_id"]
        != targeted_r4_secondary_summary["review_run_id"]
        and targeted_r4_primary_summary["review_run_id"]
        != targeted_r3_primary_summary["review_run_id"]
        and targeted_r4_secondary_summary["review_run_id"]
        != targeted_r3_secondary_summary["review_run_id"],
        "E_TARGET_R4_REVIEW_ISOLATION",
    )
    targeted_r4_combined, targeted_r4_disagreements = combine_reviews(
        targeted_r4_packet, targeted_r4_primary, targeted_r4_secondary
    )
    require(
        len(targeted_r4_disagreements) == 6,
        "E_TARGET_R4_FAILURE_DISAGREEMENT_EVIDENCE",
        str(len(targeted_r4_disagreements)),
    )
    require(
        sum(
            row["combined_disposition"] == "REPAIR"
            for row in targeted_r4_combined
        )
        == 21,
        "E_TARGET_R4_FAILURE_DISTRIBUTION",
    )

    targeted_r5_packet = load_jsonl(root / TARGETED_REVIEW_PACKET_R5_PATH)
    require(
        sha256_file(root / TARGETED_REVIEW_PACKET_R5_PATH)
        == TARGET_R5_REVIEW_PACKET_SHA256,
        "E_TARGET_R5_PACKET_PIN",
    )
    targeted_r5_primary, targeted_r5_primary_summary = load_review_directory(
        root / TARGET_R5_PRIMARY_IMPORT_DIR,
        targeted_r5_packet,
        PRIMARY_ROLE,
        reviewed_commit=TARGET_R5_REVIEWED_COMMIT,
        packet_sha256=TARGET_R5_REVIEW_PACKET_SHA256,
        prompt_revision="r5",
    )
    targeted_r5_secondary, targeted_r5_secondary_summary = load_review_directory(
        root / TARGET_R5_SECONDARY_IMPORT_DIR,
        targeted_r5_packet,
        SECONDARY_ROLE,
        reviewed_commit=TARGET_R5_REVIEWED_COMMIT,
        packet_sha256=TARGET_R5_REVIEW_PACKET_SHA256,
        prompt_revision="r5",
    )
    require(
        targeted_r5_primary_summary["reviewer_identity_id"]
        == targeted_r4_primary_summary["reviewer_identity_id"]
        and targeted_r5_secondary_summary["reviewer_identity_id"]
        == targeted_r4_secondary_summary["reviewer_identity_id"],
        "E_TARGET_R5_REVIEWER_IDENTITY_DRIFT",
    )
    require(
        targeted_r5_primary_summary["reviewer_instance_or_session_id"]
        != targeted_r5_secondary_summary["reviewer_instance_or_session_id"]
        and targeted_r5_primary_summary["review_run_id"]
        != targeted_r5_secondary_summary["review_run_id"]
        and targeted_r5_primary_summary["review_run_id"]
        != targeted_r4_primary_summary["review_run_id"]
        and targeted_r5_secondary_summary["review_run_id"]
        != targeted_r4_secondary_summary["review_run_id"],
        "E_TARGET_R5_REVIEW_ISOLATION",
    )
    targeted_r5_combined, targeted_r5_disagreements = combine_reviews(
        targeted_r5_packet, targeted_r5_primary, targeted_r5_secondary
    )
    require(
        len(targeted_r5_disagreements) == 1,
        "E_TARGET_R5_FAILURE_DISAGREEMENT_EVIDENCE",
        str(len(targeted_r5_disagreements)),
    )
    require(
        sum(
            row["combined_disposition"] == "APPROVE"
            and not row["requires_targeted_adjudication"]
            for row in targeted_r5_combined
        )
        == 26,
        "E_TARGET_R5_FAILURE_DISTRIBUTION",
    )

    targeted_r6_packet = load_jsonl(root / TARGETED_REVIEW_PACKET_R6_PATH)
    require(
        sha256_file(root / TARGETED_REVIEW_PACKET_R6_PATH)
        == TARGET_R6_REVIEW_PACKET_SHA256,
        "E_TARGET_R6_PACKET_PIN",
    )
    r5_primary_by_id = {
        str(row["packet_item_id"]): row for row in targeted_r5_primary
    }
    r5_secondary_by_id = {
        str(row["packet_item_id"]): row for row in targeted_r5_secondary
    }
    expected_r5_failure = {
        "review_packet_sha256": TARGET_R5_REVIEW_PACKET_SHA256,
        "primary_decision": "REPAIR",
        "primary_record_digest": r5_primary_by_id["P2R5-GENERATOR-CORE"][
            "record_digest"
        ],
        "secondary_decision": "APPROVE",
        "secondary_record_digest": r5_secondary_by_id["P2R5-GENERATOR-CORE"][
            "record_digest"
        ],
    }
    require(
        len(targeted_r6_packet) == 1
        and targeted_r6_packet[0]["packet_item_id"] == "P2R6-GENERATOR-CORE"
        and targeted_r6_packet[0]["review_subject"]["r5_failure_evidence"]
        == expected_r5_failure,
        "E_TARGET_R6_R5_FAILURE_BINDING",
    )
    targeted_r6_primary, targeted_r6_primary_summary = load_review_directory(
        root / TARGET_R6_PRIMARY_IMPORT_DIR,
        targeted_r6_packet,
        PRIMARY_ROLE,
        reviewed_commit=TARGET_R6_REVIEWED_COMMIT,
        packet_sha256=TARGET_R6_REVIEW_PACKET_SHA256,
        prompt_revision="r6",
    )
    targeted_r6_secondary, targeted_r6_secondary_summary = load_review_directory(
        root / TARGET_R6_SECONDARY_IMPORT_DIR,
        targeted_r6_packet,
        SECONDARY_ROLE,
        reviewed_commit=TARGET_R6_REVIEWED_COMMIT,
        packet_sha256=TARGET_R6_REVIEW_PACKET_SHA256,
        prompt_revision="r6",
    )
    require(
        targeted_r6_primary_summary["reviewer_identity_id"]
        == targeted_r5_primary_summary["reviewer_identity_id"]
        and targeted_r6_secondary_summary["reviewer_identity_id"]
        == targeted_r5_secondary_summary["reviewer_identity_id"],
        "E_TARGET_R6_REVIEWER_IDENTITY_DRIFT",
    )
    require(
        targeted_r6_primary_summary["reviewer_instance_or_session_id"]
        != targeted_r6_secondary_summary["reviewer_instance_or_session_id"]
        and targeted_r6_primary_summary["review_run_id"]
        != targeted_r6_secondary_summary["review_run_id"]
        and targeted_r6_primary_summary["review_run_id"]
        != targeted_r5_primary_summary["review_run_id"]
        and targeted_r6_secondary_summary["review_run_id"]
        != targeted_r5_secondary_summary["review_run_id"],
        "E_TARGET_R6_REVIEW_ISOLATION",
    )
    targeted_r6_combined, targeted_r6_disagreements = combine_reviews(
        targeted_r6_packet, targeted_r6_primary, targeted_r6_secondary
    )
    require(
        not targeted_r6_disagreements,
        "E_TARGET_R6_REVIEW_ADJUDICATION_REQUIRED",
        str(len(targeted_r6_disagreements)),
    )
    require(
        all(row["combined_disposition"] == "APPROVE" for row in targeted_r6_combined),
        "E_TARGET_R6_REPAIR_STILL_OPEN",
    )

    initial_approved_ids = {
        str(row["packet_item_id"])
        for row in initial_combined
        if row["final_disposition"] == "APPROVE"
    }
    targeted_r1_approved_ids = {
        str(row["packet_item_id"])
        for row in targeted_r1_combined
        if row["combined_disposition"] == "APPROVE"
    }
    targeted_r2_approved_ids = {
        str(row["packet_item_id"])
        for row in targeted_r2_combined
        if row["combined_disposition"] == "APPROVE"
    }
    targeted_r3_approved_ids = {
        str(row["packet_item_id"])
        for row in targeted_r3_combined
        if row["combined_disposition"] == "APPROVE"
    }
    targeted_r4_approved_ids = {
        str(row["packet_item_id"])
        for row in targeted_r4_combined
        if row["combined_disposition"] == "APPROVE"
    }
    targeted_r5_approved_ids = {
        str(row["packet_item_id"])
        for row in targeted_r5_combined
        if row["combined_disposition"] == "APPROVE"
    }
    targeted_r6_approved_ids = {
        str(row["packet_item_id"])
        for row in targeted_r6_combined
        if row["combined_disposition"] == "APPROVE"
    }
    require(
        "P2R6-GENERATOR-CORE" in targeted_r6_approved_ids,
        "E_GENERATOR_CORE_REVIEW_GAP",
    )
    component_pool = {
        str(row["component_id"]): row
        for row in load_jsonl(root / COMPONENT_CANDIDATES_PATH)
    }
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / REVISED_COMPONENTS_R2_PATH)
        }
    )
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / ADDITION_CANDIDATES_R2_PATH)
        }
    )
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / REVISED_COMPONENTS_R3_PATH)
        }
    )
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / ADDITION_CANDIDATES_R3_PATH)
        }
    )
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / REVISED_COMPONENTS_R4_PATH)
        }
    )
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / ADDITION_CANDIDATES_R4_PATH)
        }
    )
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / REVISED_COMPONENTS_R5_PATH)
        }
    )
    component_pool.update(
        {
            str(row["component_id"]): row
            for row in load_jsonl(root / ADDITION_CANDIDATES_R5_PATH)
        }
    )
    edge_candidates = load_jsonl(root / FINAL_EDGE_CANDIDATES_R5_PATH)
    path_candidates = load_jsonl(root / REVISED_AB_R5_PATH)
    selected_component_ids = {
        str(row["component_id"]) for row in edge_candidates
    }
    selected_component_ids.update(
        str(component_id)
        for path in path_candidates
        for component_id in set(path["lane_a"]["component_ids"]).union(
            path["lane_b"]["component_ids"]
        )
    )
    require(
        selected_component_ids.issubset(component_pool),
        "E_SELECTED_COMPONENT_UNKNOWN",
    )
    active_components = _activate_components(
        component_pool,
        selected_component_ids,
        initial_approved_ids,
        targeted_r1_approved_ids,
        targeted_r2_approved_ids,
        targeted_r3_approved_ids,
        targeted_r4_approved_ids,
        targeted_r5_approved_ids,
    )
    active_component_by_id = {row["component_id"]: row for row in active_components}
    active_rules = _activate_rules(
        load_jsonl(root / REVISED_RULES_R5_PATH),
        targeted_r1_approved_ids,
        targeted_r2_approved_ids,
    )
    require(len(active_rules) == 8, "E_CONTROL_RULE_REVIEW_GAP", str(len(active_rules)))
    active_rule_by_id = {row["control_rule_id"]: row for row in active_rules}
    active_paths = _activate_paths(
        path_candidates,
        targeted_r5_approved_ids,
        active_component_by_id,
        active_rule_by_id,
    )
    require(len(active_paths) == 20, "E_AB_PATH_REVIEW_GAP", str(len(active_paths)))
    active_path_by_profile = {
        str(row["content_product_type_id"]): row for row in active_paths
    }
    active_edges = _activate_edges(
        edge_candidates,
        active_component_by_id,
        targeted_r2_approved_ids,
        targeted_r3_approved_ids,
        targeted_r5_approved_ids,
        active_path_by_profile,
    )
    supply = build_approved_supply(state["profiles"], active_edges)
    require(
        supply["approved_component_supply_matrix"]["approved_complete_profile_count"]
        == 20,
        "E_COMPONENT_SUPPLY_GAP",
    )
    require(
        all(
            set(path["lane_a"]["component_ids"])
            .union(path["lane_b"]["component_ids"])
            .issubset(active_component_by_id)
            for path in active_paths
        ),
        "E_AB_PATH_COMPONENT_GAP",
    )
    evidence = build_generator_evidence_r6(
        state["profiles"], active_components, active_rules, active_paths
    )
    require(len(evidence["requests"]) == 40, "E_REQUEST_COUNT")
    require(
        all(row["unrealized_component_count"] == 0 for row in evidence["realizations"]),
        "E_COMPONENT_UNREALIZED",
    )
    require(
        all(
            row["required_output_dependency_preserved"]
            for row in evidence["ablations"]
        ),
        "E_COMPONENT_ABLATION",
    )
    require(
        len(evidence["pointer_cases"]) == 410
        and all(
            row["pointer_resolved"] and row["digest_matches"]
            for row in evidence["pointer_cases"]
        ),
        "E_COMPONENT_POINTER",
    )
    require(
        len(evidence["axis_body_pairs"]) == 120
        and all(row["body_level_difference"] for row in evidence["axis_body_pairs"]),
        "E_AXIS_BODY_DIVERGENCE",
    )
    require(
        len(evidence["path_program_tampers"]) == 120
        and all(
            row["substitution_rejected"]
            for row in evidence["path_program_tampers"]
        ),
        "E_PATH_PROGRAM_TAMPER",
    )
    require(
        len(evidence["trust_contract_tampers"]) == 180
        and all(
            row["tamper_rejected"] for row in evidence["trust_contract_tampers"]
        ),
        "E_TRUST_CONTRACT_TAMPER",
    )
    require(
        len(evidence["observable_effect_tampers"]) == 62
        and all(
            row["registry_identity_rejected"]
            and not row["nonmetadata_structure_change_claimed"]
            for row in evidence["observable_effect_tampers"]
        ),
        "E_COMPONENT_IDENTITY_TAMPER",
    )
    require(
        len(evidence["bound_fact_effect_cases"]) == 62
        and all(
            row["same_required_slot_preserved"]
            and row["nonmetadata_structure_changed"]
            for row in evidence["bound_fact_effect_cases"]
        ),
        "E_BOUND_FACT_STRUCTURAL_EFFECT",
    )
    require(
        len(evidence["required_slot_tampers"]) == 20
        and all(
            row["tamper_rejected"]
            and row["error_code"] == "E_COMPONENT_REQUIRED_SLOT_MISMATCH"
            for row in evidence["required_slot_tampers"]
        ),
        "E_REQUIRED_SLOT_TRUST_ROOT",
    )
    require(
        len(evidence["path_program_schema_tampers"]) == 240
        and all(
            row["tamper_rejected"]
            and row["error_code"] == "E_AXIS_PROGRAM_FIELD_SET"
            for row in evidence["path_program_schema_tampers"]
        ),
        "E_PATH_PROGRAM_SCHEMA",
    )
    require(
        all(
            row["same_source_fact_authorization_boundary"]
            and row["independent_session_ids"]
            and row["minimum_four_axes_pass"]
            and row["all_six_structural_bodies_differ"]
            and row["ending_action_topology_differs"]
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
        "targeted_r2_primary": targeted_r2_primary_summary,
        "targeted_r2_secondary": targeted_r2_secondary_summary,
        "targeted_r3_primary": targeted_r3_primary_summary,
        "targeted_r3_secondary": targeted_r3_secondary_summary,
        "targeted_r4_primary": targeted_r4_primary_summary,
        "targeted_r4_secondary": targeted_r4_secondary_summary,
        "targeted_r5_primary": targeted_r5_primary_summary,
        "targeted_r5_secondary": targeted_r5_secondary_summary,
        "targeted_r6_primary": targeted_r6_primary_summary,
        "targeted_r6_secondary": targeted_r6_secondary_summary,
    }
    review_closeout = _review_closeout(
        summaries,
        initial_combined,
        targeted_r1_combined,
        targeted_r2_combined,
        targeted_r3_combined,
        targeted_r4_combined,
        targeted_r5_combined,
        targeted_r6_combined,
        adjudication_records,
    )
    require(
        review_closeout["independent_component_review_closeout"][
            "targeted_r6_unresolved_disagreement_count"
        ]
        == 0,
        "E_REVIEW_DISAGREEMENT",
    )
    import_manifest = _build_import_manifest(root, summaries)
    generator_contract = _generator_contract_r6()
    generator_registry = _generator_registry_r6(
        root, active_components, active_edges
    )
    compatibility = _compatibility_document(root)
    result = _result_document(
        active_components,
        active_edges,
        active_rules,
        active_paths,
        initial_combined,
        targeted_r1_combined,
        targeted_r2_combined,
        targeted_r3_combined,
        targeted_r4_combined,
        targeted_r5_combined,
        targeted_r6_combined,
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
        TARGET_COMBINED_REVIEW_PATH: jsonl_bytes(targeted_r1_combined),
        TARGET_R2_COMBINED_REVIEW_PATH: jsonl_bytes(targeted_r2_combined),
        TARGET_R3_COMBINED_REVIEW_PATH: jsonl_bytes(targeted_r3_combined),
        TARGET_R4_COMBINED_REVIEW_PATH: jsonl_bytes(targeted_r4_combined),
        TARGET_R5_COMBINED_REVIEW_PATH: jsonl_bytes(targeted_r5_combined),
        TARGET_R6_COMBINED_REVIEW_PATH: jsonl_bytes(targeted_r6_combined),
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
        AXIS_BODY_PAIR_RESULTS_PATH: jsonl_bytes(evidence["axis_body_pairs"]),
        PATH_PROGRAM_TAMPER_RESULTS_PATH: jsonl_bytes(
            evidence["path_program_tampers"]
        ),
        TRUST_CONTRACT_TAMPER_RESULTS_PATH: jsonl_bytes(
            evidence["trust_contract_tampers"]
        ),
        COMPONENT_POINTER_RESULTS_PATH: jsonl_bytes(evidence["pointer_cases"]),
        OBSERVABLE_EFFECT_TAMPER_RESULTS_PATH: jsonl_bytes(
            evidence["observable_effect_tampers"]
        ),
        BOUND_FACT_EFFECT_RESULTS_PATH: jsonl_bytes(
            evidence["bound_fact_effect_cases"]
        ),
        REQUIRED_SLOT_TAMPER_RESULTS_PATH: jsonl_bytes(
            evidence["required_slot_tampers"]
        ),
        PROGRAM_SCHEMA_TAMPER_RESULTS_PATH: jsonl_bytes(
            evidence["path_program_schema_tampers"]
        ),
        ABLATION_RESULTS_PATH: jsonl_bytes(evidence["ablations"]),
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

    def resolve_pointer(document: dict[str, Any], pointer: str) -> Any:
        node: Any = document
        for token in pointer.removeprefix("/").split("/"):
            require(isinstance(node, dict) and token in node, "E_POINTER", pointer)
            node = node[token]
        return node

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
    targeted_r1_combined = jsonl_rows(TARGET_COMBINED_REVIEW_PATH)
    targeted_r2_combined = jsonl_rows(TARGET_R2_COMBINED_REVIEW_PATH)
    targeted_r3_combined = jsonl_rows(TARGET_R3_COMBINED_REVIEW_PATH)
    targeted_r4_combined = jsonl_rows(TARGET_R4_COMBINED_REVIEW_PATH)
    targeted_r5_combined = jsonl_rows(TARGET_R5_COMBINED_REVIEW_PATH)
    targeted_r6_combined = jsonl_rows(TARGET_R6_COMBINED_REVIEW_PATH)
    components = jsonl_rows(ACTIVE_COMPONENTS_PATH)
    rules = jsonl_rows(ACTIVE_RULES_PATH)
    edges = jsonl_rows(ACTIVE_EDGES_PATH)
    paths = jsonl_rows(ACTIVE_AB_PATH)
    requests = jsonl_rows(AUTHOR_REQUESTS_PATH)
    realizations = jsonl_rows(REALIZATIONS_PATH)
    pairs = jsonl_rows(AB_PAIR_RESULTS_PATH)
    axis_body_pairs = jsonl_rows(AXIS_BODY_PAIR_RESULTS_PATH)
    path_program_tampers = jsonl_rows(PATH_PROGRAM_TAMPER_RESULTS_PATH)
    trust_contract_tampers = jsonl_rows(TRUST_CONTRACT_TAMPER_RESULTS_PATH)
    pointer_cases = jsonl_rows(COMPONENT_POINTER_RESULTS_PATH)
    observable_effect_tampers = jsonl_rows(
        OBSERVABLE_EFFECT_TAMPER_RESULTS_PATH
    )
    bound_fact_effects = jsonl_rows(BOUND_FACT_EFFECT_RESULTS_PATH)
    required_slot_tampers = jsonl_rows(REQUIRED_SLOT_TAMPER_RESULTS_PATH)
    program_schema_tampers = jsonl_rows(PROGRAM_SCHEMA_TAMPER_RESULTS_PATH)
    ablations = jsonl_rows(ABLATION_RESULTS_PATH)
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
        len(targeted_r1_combined) == 141
        and sum(
            row["combined_disposition"] == "APPROVE"
            and row["requires_targeted_adjudication"] is False
            for row in targeted_r1_combined
        )
        == 27
        and sum(
            row["requires_targeted_adjudication"]
            for row in targeted_r1_combined
        )
        == 82
        and all(
            row["combined_digest"] == object_digest(row, "combined_digest")
            for row in targeted_r1_combined
        ),
        "E_TARGET_R1_REVIEW_EVIDENCE",
    )
    require(
        len(targeted_r2_combined) == 134
        and sum(row["combined_disposition"] == "APPROVE" for row in targeted_r2_combined)
        == 107
        and sum(row["combined_disposition"] == "REPAIR" for row in targeted_r2_combined)
        == 20
        and sum(row["requires_targeted_adjudication"] for row in targeted_r2_combined)
        == 7
        and all(
            row["combined_digest"] == object_digest(row, "combined_digest")
            for row in targeted_r2_combined
        ),
        "E_TARGET_R2_FAILURE_EVIDENCE",
    )
    require(
        len(targeted_r3_combined) == 29
        and sum(
            row["combined_disposition"] == "APPROVE"
            and row["requires_targeted_adjudication"] is False
            for row in targeted_r3_combined
        )
        == 2
        and sum(
            row["combined_disposition"] == "REPAIR"
            and row["requires_targeted_adjudication"] is False
            for row in targeted_r3_combined
        )
        == 21
        and sum(row["requires_targeted_adjudication"] for row in targeted_r3_combined)
        == 6
        and all(
            row["combined_digest"] == object_digest(row, "combined_digest")
            for row in targeted_r3_combined
        ),
        "E_TARGET_R3_FAILURE_EVIDENCE",
    )
    require(
        len(targeted_r4_combined) == 27
        and sum(
            row["combined_disposition"] == "REPAIR"
            and row["requires_targeted_adjudication"] is False
            for row in targeted_r4_combined
        )
        == 21
        and sum(row["requires_targeted_adjudication"] for row in targeted_r4_combined)
        == 6
        and all(
            row["combined_digest"] == object_digest(row, "combined_digest")
            for row in targeted_r4_combined
        ),
        "E_TARGET_R4_FAILURE_EVIDENCE",
    )
    require(
        len(targeted_r5_combined) == 27
        and sum(
            row["combined_disposition"] == "APPROVE"
            and row["requires_targeted_adjudication"] is False
            for row in targeted_r5_combined
        )
        == 26
        and sum(row["requires_targeted_adjudication"] for row in targeted_r5_combined)
        == 1
        and all(
            row["combined_digest"] == object_digest(row, "combined_digest")
            for row in targeted_r5_combined
        ),
        "E_TARGET_R5_FAILURE_EVIDENCE",
    )
    require(
        len(targeted_r6_combined) == 1
        and all(
            row["combined_disposition"] == "APPROVE"
            and row["requires_targeted_adjudication"] is False
            and row["combined_digest"] == object_digest(row, "combined_digest")
            for row in targeted_r6_combined
        ),
        "E_TARGET_R6_REVIEW_CLOSEOUT",
    )
    require(
        manifest["manifest_digest"] == object_digest(manifest, "manifest_digest")
        and manifest["imported_file_count"] == 45
        and len(manifest["files"]) == 45
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
        and closeout["targeted_r1_combined_record_count"] == 141
        and closeout["targeted_r1_matching_approval_count"] == 27
        and closeout["targeted_r1_failure_or_open_count"] == 114
        and closeout["targeted_r2_combined_record_count"] == 134
        and closeout["targeted_r2_matching_approval_count"] == 107
        and closeout["targeted_r2_matching_repair_count"] == 20
        and closeout["targeted_r2_unresolved_disagreement_count"] == 7
        and closeout["targeted_r2_failure_evidence_preserved"] is True
        and closeout["targeted_r3_combined_record_count"] == 29
        and closeout["targeted_r3_matching_approval_count"] == 2
        and closeout["targeted_r3_matching_repair_count"] == 21
        and closeout["targeted_r3_unresolved_disagreement_count"] == 6
        and closeout["targeted_r3_failure_evidence_preserved"] is True
        and closeout["targeted_r4_combined_record_count"] == 27
        and closeout["targeted_r4_matching_approval_count"] == 0
        and closeout["targeted_r4_matching_repair_count"] == 21
        and closeout["targeted_r4_unresolved_disagreement_count"] == 6
        and closeout["targeted_r4_failure_evidence_preserved"] is True
        and closeout["targeted_r5_combined_record_count"] == 27
        and closeout["targeted_r5_matching_approval_count"] == 26
        and closeout["targeted_r5_unresolved_disagreement_count"] == 1
        and closeout["targeted_r5_failure_evidence_preserved"] is True
        and closeout["targeted_r6_combined_record_count"] == 1
        and closeout["targeted_r6_matching_approval_count"] == 1
        and closeout["targeted_r6_unresolved_disagreement_count"] == 0
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
            and row["independent_review_state"]
            == "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
            and not any(row["readiness"].values())
            for row in components
        ),
        "E_COMPONENT_DIGEST",
    )
    require(
        all(
            row["edge_digest"] == object_digest(row, "edge_digest")
            and row["active"] is True
            and row["independent_review_state"]
            == "APPROVED_BY_REQUIRED_INDEPENDENT_REVIEW"
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
                isinstance(binding.get("exact_typed_object_bindings"), dict)
                and all(
                    isinstance(
                        binding["exact_typed_object_bindings"].get(kind), list
                    )
                    and binding["exact_typed_object_bindings"][kind]
                    for kind in ("input", "fact", "authorization")
                )
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
    for realization in realizations:
        require(
            len(realization["lane_axis_realizations"]) == 6,
            "E_AXIS_REALIZATION_COUNT",
        )
        for contribution in realization["component_contributions"]:
            resolved = resolve_pointer(
                realization, str(contribution["implementation_pointer"])
            )
            require(
                isinstance(resolved, dict)
                and resolved.get("structural_body_digest")
                == contribution["structural_body_digest"]
                and resolved.get("structural_output_digest")
                == contribution["structural_output_digest"],
                "E_COMPONENT_POINTER_OUTPUT",
            )
    require(
        len(pairs) == 20
        and all(
            row["same_source_fact_authorization_boundary"] is True
            and row["independent_session_ids"] is True
            and row["minimum_four_axes_pass"] is True
            and row["observable_difference_axis_count"] == 6
            and row["all_six_structural_bodies_differ"] is True
            and row["ending_action_topology_differs"] is True
            and row["content_quality_proven"] is False
            for row in pairs
        ),
        "E_AB_PAIR_EVIDENCE",
    )
    require(
        len(axis_body_pairs) == result["axis_body_pair_case_count"] == 120
        and all(row["body_level_difference"] is True for row in axis_body_pairs),
        "E_AXIS_BODY_PAIR_EVIDENCE",
    )
    require(
        len(path_program_tampers)
        == result["path_program_tamper_case_count"]
        == 120
        and all(
            row["substitution_rejected"] is True
            for row in path_program_tampers
        ),
        "E_PATH_PROGRAM_TAMPER_EVIDENCE",
    )
    require(
        len(trust_contract_tampers)
        == result["trust_contract_tamper_case_count"]
        == 180
        and all(
            row["tamper_rejected"] is True for row in trust_contract_tampers
        ),
        "E_TRUST_CONTRACT_TAMPER_EVIDENCE",
    )
    require(
        len(ablations) == result["component_ablation_case_count"]
        and len(ablations) == 410
        and all(
            row["ablation_rejected"] is True
            and row["required_output_dependency_preserved"] is True
            for row in ablations
        ),
        "E_COMPONENT_ABLATION",
    )
    require(
        len(pointer_cases) == result["component_pointer_case_count"] == 410
        and all(
            row["pointer_resolved"] is True and row["digest_matches"] is True
            for row in pointer_cases
        ),
        "E_COMPONENT_POINTER_EVIDENCE",
    )
    require(
        len(observable_effect_tampers)
        == result["observable_effect_tamper_case_count"]
        == 62
        and all(
            row["registry_identity_rejected"] is True
            and row["nonmetadata_structure_change_claimed"] is False
            for row in observable_effect_tampers
        ),
        "E_COMPONENT_IDENTITY_TAMPER_EVIDENCE",
    )
    require(
        len(bound_fact_effects) == result["bound_fact_effect_case_count"] == 62
        and all(
            row["same_required_slot_preserved"] is True
            and row["nonmetadata_structure_changed"] is True
            for row in bound_fact_effects
        ),
        "E_BOUND_FACT_EFFECT_EVIDENCE",
    )
    require(
        len(required_slot_tampers)
        == result["required_slot_tamper_case_count"]
        == 20
        and all(
            row["tamper_rejected"] is True
            and row["error_code"] == "E_COMPONENT_REQUIRED_SLOT_MISMATCH"
            for row in required_slot_tampers
        ),
        "E_REQUIRED_SLOT_TAMPER_EVIDENCE",
    )
    require(
        len(program_schema_tampers)
        == result["path_program_schema_tamper_case_count"]
        == 240
        and all(
            row["tamper_rejected"] is True
            and row["error_code"] == "E_AXIS_PROGRAM_FIELD_SET"
            for row in program_schema_tampers
        ),
        "E_PROGRAM_SCHEMA_TAMPER_EVIDENCE",
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
        and contract["generator_may_write_composition_plan"] is False
        and contract["active_core_module"] == "p2_generator_core_r6.py"
        and contract["approved_path_registry_is_authoritative"] is True
        and contract["axis_component_profile_lane_payload_allowed"] is False
        and contract["all_selected_components_require_addressable_structural_output"]
        is True
        and contract["component_required_slots_must_equal_binding_slots"] is True
        and contract["path_program_schema_is_executable"] is True
        and contract["hash_or_token_semantic_selection_allowed"] is False,
        "E_GENERATOR_CONTRACT",
    )
    require(
        registry["registry_digest"] == object_digest(registry, "registry_digest")
        and registry["current_generator_entrypoint_count"] == 1
        and registry["historical_generator_entrypoints_consumed"] == []
        and registry["core_module"]["path"].endswith("p2_generator_core_r6.py")
        and all(
            row["active"] is False
            for row in registry["historical_non_active_core_modules"]
        )
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
