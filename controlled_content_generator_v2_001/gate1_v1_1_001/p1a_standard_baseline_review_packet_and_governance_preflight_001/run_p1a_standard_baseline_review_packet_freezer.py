#!/usr/bin/env python3
"""Materialize the read-only Gate 1 v1.1 P1A review packet.

P1A builds a common, traceable review input only. It deliberately does not
map legacy content to a content product, decide component dispositions, or
freeze any Gate 1 count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_STANDARD_BASELINE_REVIEW_PACKET_AND_GOVERNANCE_PREFLIGHT_001"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1a_standard_baseline_review_packet_and_governance_preflight_001"
)
STANDARD_EXTERNAL_PATH = Path(
    "/mnt/c/Users/Administrator/Documents/笛语agent/planning/"
    "笛语内容编排生成器与人审评价标准体系_v1.1.md"
)
STANDARD_SNAPSHOT_PATH = (
    TASK_ROOT / "standard/diyu_content_composition_standard.v1.1.md"
)
STANDARD_CONTRACT_PATH = TASK_ROOT / "standard/v1_1_standard_contract.v0.1.yaml"
BASELINE_MANIFEST_PATH = TASK_ROOT / "baseline/gate1_input_baseline_manifest.v0.1.yaml"
REVIEW_PACKET_PATH = TASK_ROOT / "review/unified_gate1_review_packet.v0.1.jsonl"
REVIEW_CONTRACT_PATH = TASK_ROOT / "review/independent_review_contract.v0.1.yaml"
REVIEW_RECORD_TEMPLATE_PATH = (
    TASK_ROOT / "review/unified_independent_review_record_template.v0.1.yaml"
)
LEGACY_EDGE_MANIFEST_PATH = (
    TASK_ROOT
    / "component/legacy_component_applicability_historical_manifest.v0.1.jsonl"
)
COMPAT_RECEIPT_PATH = (
    TASK_ROOT / "compatibility/governance_compatibility_repair_receipt.v0.1.yaml"
)
RESULT_PATH = TASK_ROOT / "result/p1a_standard_baseline_preflight_result.v0.1.yaml"

REPORT_PATH = Path(
    "docs/reports/gate1_v1_1_generator_gkb_retrospective_and_recovery_plan_20260713.md"
)
CLEAN_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
ROUTE_INPUT_PATH = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/"
    "route/route_inputs.v0.1.jsonl"
)
ROUTE_ACTUAL_PATH = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001/"
    "route/route_regression_actuals.v0.1.jsonl"
)
COMPONENT_SOURCE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
    "reviewed_reusable_component_registry.v0.4.jsonl"
)
B24_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_b_channel_24_component_review.py")
SUCCESSOR_CHECKER_PATH = Path(
    "ci/checkers/check_orch_generator_v2_b_channel_component_consumption_dev_gate.py"
)
CURRENT_GATE1_CHECKER_PATH = Path("ci/checkers/check_gate1_v1_1_current.py")

BASELINE_COMMIT = "473a8664bdab37246db1b75785f765e62c80ed86"
ANCHOR_REPORT_PRE_P1A_SHA256 = (
    "8b5088b895245b11fc0270159f98a373be73aa13e236377819cd3d107975eb01"
)
STANDARD_SHA256 = "022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542"
CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
ROUTE_INPUT_SHA256 = "68bc65bff904652f1e565097117c7e8dfccdcc6ef00d2e3a0e93a082a4d72f12"
ROUTE_ACTUAL_SHA256 = "bb7d68686761b7be092f191a0f46cb7493a3947f98959703c3ccaa69a86de3ad"
COMPONENT_SOURCE_SHA256 = (
    "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601"
)
PR13_FAILURE_COMMIT = "d2a9225d4fafea6651a53d8f02a489629a81ef84"
PR13_FAILURE_RESULT_PATH = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_claim_closure_dev_gate_authorized_transport_replay_001/"
    "result/development_gate_result.v0.1.json"
)
PR13_FAILURE_RESULT_SHA256 = (
    "83d03d14c53aecc82d461782f4d560ae0e0a6c4eea02dc662cfc49c0fef344f2"
)
B24_CHECKER_BEFORE_SHA256 = (
    "ff4060e02f387e92b9ec1613df31b5b855cbd04a1155d92f5ca03dacf3191394"
)
SUCCESSOR_CHECKER_BEFORE_SHA256 = (
    "95fcf3e6716e86f01a210c64dbe4685705962583ff9b2c560182389ba66df71c"
)
CURRENT_GATE1_CHECKER_V1_BEFORE_SHA256 = (
    "679343b9187ad12c3af077ab4041a3c706bcef56b915c6ef0234af54319ee716"
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: dict[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def yaml_bytes(value: dict[str, Any]) -> bytes:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    ).encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def read_jsonl(path: Path) -> list[tuple[dict[str, Any], str]]:
    rows: list[tuple[dict[str, Any], str]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line:
            continue
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            raise TypeError(f"{path}:{line_number} is not a JSON object")
        rows.append((value, raw_line))
    return rows


def unique_ids(rows: list[tuple[dict[str, Any], str]], key: str, path: Path) -> None:
    ids = [row.get(key) for row, _ in rows]
    if any(not isinstance(value, str) or not value for value in ids):
        raise ValueError(f"{path} has missing {key}")
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path} has duplicate {key}")


def ensure_hash(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"sha256 mismatch for {path}: {actual}")


def read_sources(root: Path) -> dict[str, Any]:
    paths = {
        "clean_120": root / CLEAN_120_PATH,
        "route_input": root / ROUTE_INPUT_PATH,
        "route_actual": root / ROUTE_ACTUAL_PATH,
        "components": root / COMPONENT_SOURCE_PATH,
        "report": root / REPORT_PATH,
        "b24_checker": root / B24_CHECKER_PATH,
        "successor_checker": root / SUCCESSOR_CHECKER_PATH,
        "current_gate1_checker": root / CURRENT_GATE1_CHECKER_PATH,
    }
    for path in paths.values():
        if not path.exists():
            raise FileNotFoundError(path)
    ensure_hash(paths["clean_120"], CLEAN_120_SHA256)
    ensure_hash(paths["route_input"], ROUTE_INPUT_SHA256)
    ensure_hash(paths["route_actual"], ROUTE_ACTUAL_SHA256)
    ensure_hash(paths["components"], COMPONENT_SOURCE_SHA256)

    clean_rows = read_jsonl(paths["clean_120"])
    route_input_rows = read_jsonl(paths["route_input"])
    route_actual_rows = read_jsonl(paths["route_actual"])
    component_rows = read_jsonl(paths["components"])
    unique_ids(clean_rows, "asset_id", paths["clean_120"])
    unique_ids(route_input_rows, "case_id", paths["route_input"])
    unique_ids(route_actual_rows, "case_id", paths["route_actual"])
    unique_ids(component_rows, "component_id", paths["components"])
    if (
        len(clean_rows) != 120
        or len(route_input_rows) != 60
        or len(route_actual_rows) != 60
    ):
        raise ValueError("unexpected 120/60 source cardinality")
    if len(component_rows) != 86:
        raise ValueError("unexpected component candidate cardinality")
    route_input_ids = {row["case_id"] for row, _ in route_input_rows}
    route_actual_ids = {row["case_id"] for row, _ in route_actual_rows}
    if route_input_ids != route_actual_ids:
        raise ValueError("route input and actual case ids differ")
    edge_count = sum(
        len(row.get("applicable_content_product_type_ids", []))
        for row, _ in component_rows
    )
    if edge_count != 543:
        raise ValueError(f"unexpected legacy applicability edge count: {edge_count}")
    return {
        "paths": paths,
        "clean_rows": clean_rows,
        "route_input_rows": route_input_rows,
        "route_actual_rows": route_actual_rows,
        "component_rows": component_rows,
        "edge_count": edge_count,
    }


def standard_contract() -> dict[str, Any]:
    contract: dict[str, Any] = {
        "gate1_v1_1_standard_contract": {
            "schema_version": "v0.1",
            "standard_version": "v1.1",
            "source_path": STANDARD_EXTERNAL_PATH.as_posix(),
            "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
            "source_sha256": STANDARD_SHA256,
            "first_gate_targets": {
                "positive_parent_content_target": 240,
                "route_case_target": 60,
                "total_case_target": 300,
                "content_product_count": 20,
            },
            "review_coverage": {
                "machine_check_coverage": "ALL_MATERIAL",
                "primary_content_review": "APPLICABLE_POSITIVE_FIRST_OUTPUTS_100_PERCENT",
                "second_expert_minimum_review_count": 48,
                "second_expert_minimum_per_content_product": 2,
                "disagreement_resolution": "INDEPENDENT_ADJUDICATION_REQUIRED",
            },
            "p1a_boundary": {
                "standard_snapshot_only": True,
                "review_decisions_created": False,
                "counted_positive_parent_count_frozen": False,
                "generator_qualification_created": False,
            },
        }
    }
    contract["gate1_v1_1_standard_contract"]["contract_digest"] = object_digest(
        contract["gate1_v1_1_standard_contract"],
        "contract_digest",
    )
    return contract


def baseline_manifest(source: dict[str, Any]) -> dict[str, Any]:
    paths = source["paths"]
    manifest: dict[str, Any] = {
        "gate1_input_baseline_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "baseline_commit": BASELINE_COMMIT,
            "anchor_report": {
                "path": REPORT_PATH.as_posix(),
                "pre_p1a_sha256": ANCHOR_REPORT_PRE_P1A_SHA256,
                "after_p1a_policy_correction_sha256": sha256_file(paths["report"]),
            },
            "standard": {
                "external_source_path": STANDARD_EXTERNAL_PATH.as_posix(),
                "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
                "sha256": STANDARD_SHA256,
            },
            "review_inputs": {
                "legacy_reference_content": {
                    "path": CLEAN_120_PATH.as_posix(),
                    "sha256": CLEAN_120_SHA256,
                    "count": 120,
                    "read_only": True,
                },
                "route_input_cases": {
                    "path": ROUTE_INPUT_PATH.as_posix(),
                    "sha256": ROUTE_INPUT_SHA256,
                    "count": 60,
                    "read_only": True,
                },
                "route_actual_records": {
                    "path": ROUTE_ACTUAL_PATH.as_posix(),
                    "sha256": ROUTE_ACTUAL_SHA256,
                    "count": 60,
                    "observed_implementation_only": True,
                    "may_not_define_gold_answer": True,
                    "excluded_from_blind_review_packet": True,
                    "comparison_allowed_only_after_signed_independent_determination": True,
                },
                "component_candidates": {
                    "path": COMPONENT_SOURCE_PATH.as_posix(),
                    "sha256": COMPONENT_SOURCE_SHA256,
                    "count": 86,
                    "read_only": True,
                },
            },
            "historical_failure_evidence": {
                "pull_request_number": 13,
                "commit": PR13_FAILURE_COMMIT,
                "result_path": PR13_FAILURE_RESULT_PATH.as_posix(),
                "result_sha256_at_historical_commit": PR13_FAILURE_RESULT_SHA256,
                "classification": "HISTORICAL_FAILURE_EVIDENCE_NOT_ACCEPTANCE",
            },
            "p1a_boundary": {
                "review_decisions_created": False,
                "counted_positive_parent_count": "NOT_FROZEN",
                "component_dispositions_created": False,
                "route_gold_answers_created": False,
            },
        }
    }
    manifest["gate1_input_baseline_manifest"]["manifest_digest"] = object_digest(
        manifest["gate1_input_baseline_manifest"],
        "manifest_digest",
    )
    return manifest


def review_packet(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row, raw_line in source["clean_rows"]:
        asset_id = row["asset_id"]
        rows.append(
            {
                "packet_item_id": f"P1A-LEGACY-CONTENT-{asset_id}",
                "object_type": "LEGACY_REFERENCE_CONTENT",
                "object_id": asset_id,
                "source": {
                    "path": CLEAN_120_PATH.as_posix(),
                    "locator": f"{CLEAN_120_PATH}#{asset_id}",
                    "record_sha256": sha256_bytes(raw_line.encode("utf-8")),
                    "read_only": True,
                },
                "review_questions": [
                    "MAP_PRIMARY_CONTENT_PRODUCT",
                    "ASSESS_CONTENT_AND_USER_VALUE",
                    "ASSESS_FACT_SOURCE_AND_AUTHORIZATION_BOUNDARY",
                    "ASSESS_FIRST_GATE_ELIGIBILITY",
                ],
                "review_state": "PENDING_INDEPENDENT_REVIEW",
                "may_count_toward_positive_240_before_p1b": False,
            }
        )
    for row, raw_line in source["route_input_rows"]:
        case_id = row["case_id"]
        rows.append(
            {
                "packet_item_id": f"P1A-ROUTE-{case_id}",
                "object_type": "ROUTE_CASE",
                "object_id": case_id,
                "profile_id": row["profile_id"],
                "input_source": {
                    "path": ROUTE_INPUT_PATH.as_posix(),
                    "locator": f"{ROUTE_INPUT_PATH}#{case_id}",
                    "record_sha256": sha256_bytes(raw_line.encode("utf-8")),
                    "read_only": True,
                },
                "review_questions": [
                    "DETERMINE_GOLD_PRIMARY_ACTION",
                    "DETERMINE_GOLD_REASON_CODE",
                    "ASSESS_HARD_GUARD_AND_SAFE_DEGRADE_BOUNDARY",
                ],
                "review_state": "PENDING_INDEPENDENT_REVIEW",
            }
        )
    for row, raw_line in source["component_rows"]:
        component_id = row["component_id"]
        role = row.get(
            "component_role", row.get("source_component_role", "UNSPECIFIED")
        )
        rows.append(
            {
                "packet_item_id": f"P1A-COMPONENT-{component_id}",
                "object_type": "COMPONENT_CANDIDATE",
                "object_id": component_id,
                "source": {
                    "path": COMPONENT_SOURCE_PATH.as_posix(),
                    "locator": f"{COMPONENT_SOURCE_PATH}#{component_id}",
                    "record_sha256": sha256_bytes(raw_line.encode("utf-8")),
                    "read_only": True,
                },
                "historical_descriptor": {
                    "component_role": role,
                    "composition_asset_class": row.get(
                        "composition_asset_class", "UNSPECIFIED"
                    ),
                },
                "review_questions": [
                    "DETERMINE_DISPOSITION",
                    "ASSESS_ABSTRACTION_AND_PROVENANCE",
                    "ASSESS_CONTENT_PRODUCT_APPLICABILITY_EDGES",
                    "ASSESS_RECLASSIFY_AS_CONTROL_RULE_IF_NEEDED",
                ],
                "review_state": "PENDING_INDEPENDENT_REVIEW",
                "may_be_consumed_by_new_generator": False,
            }
        )
    if len(rows) != 266 or len({row["packet_item_id"] for row in rows}) != 266:
        raise ValueError("review packet must contain 266 unique objects")
    return rows


def review_contract() -> dict[str, Any]:
    contract: dict[str, Any] = {
        "independent_review_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "packet_builder_identity_id": "P1A_DETERMINISTIC_PACKET_MATERIALIZER",
            "p1b_freezer_identity_id": "P1B_UNASSIGNED_FREEZER_IDENTITY",
            "repository_standard_binding": {
                "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
                "snapshot_sha256": STANDARD_SHA256,
                "positive_content_scoring": "70_PLUS_30_EQUALS_100",
                "component_scoring": "80_PLUS_20_EQUALS_100",
                "route_scoring": "HARD_PRIMARY_ACTION_AND_REASON_CODE_NO_PER_RECORD_PERCENTAGE",
            },
            "reviewer_identity_policy": {
                "reviewer_may_be_ai_or_human": True,
                "distinct_reviewer_identity_id_required": True,
                "isolated_instance_or_session_required": True,
                "independent_run_and_signature_record_required": True,
                "blind_to_other_review_before_own_conclusion": True,
                "primary_and_secondary_pairwise_distinct_required": True,
                "adjudicator_pairwise_distinct_from_primary_and_secondary_when_triggered": True,
                "pairwise_distinct_record_fields": [
                    "reviewer_identity_id",
                    "reviewer_instance_or_session_id",
                    "review_run_id",
                    "append_only_signature_or_attestation",
                ],
                "may_not_equal_content_author": True,
                "may_not_equal_p1a_packet_builder": True,
                "may_not_equal_p1b_freezer": True,
                "required_record_fields": [
                    "reviewer_identity_id",
                    "reviewer_instance_or_session_id",
                    "review_run_id",
                    "input_digest",
                    "instruction_digest",
                    "model_or_instance_configuration_digest",
                    "append_only_signature_or_attestation",
                ],
            },
            "route_blind_review_sequence": {
                "blind_packet_may_not_contain_current_implementation_locator_or_digest": True,
                "first_submission_required_before_actual_comparison": True,
                "required_signed_determination_fields": [
                    "primary_action",
                    "reason_code",
                    "evidence_refs",
                    "append_only_record_digest",
                ],
                "current_actual_source": {
                    "path": ROUTE_ACTUAL_PATH.as_posix(),
                    "sha256": ROUTE_ACTUAL_SHA256,
                    "p1b_only_after_signed_determination": True,
                },
            },
            "scoring_and_decision_contract": {
                "positive_content": {
                    "formula": "70_PLUS_30_EQUALS_100",
                    "must_use_repository_standard": True,
                },
                "component_candidate": {
                    "formula": "80_PLUS_20_EQUALS_100",
                    "must_use_repository_standard": True,
                },
                "route_case": {
                    "formula": "HARD_PRIMARY_ACTION_AND_REASON_CODE",
                    "per_record_percentage_forbidden": True,
                },
                "review_delivery_summary": {
                    "independent_coordinator_score_out_of": 100,
                    "is_not_a_substitute_for_object_level_decision": True,
                },
                "separation_required": [
                    "total_score",
                    "hard_gate",
                    "veto",
                    "grade",
                    "disposition",
                    "lifecycle_status",
                ],
                "high_score_may_not_override_hard_veto": True,
            },
            "disagreement_policy": {
                "original_conclusions_and_evidence_append_only": True,
                "independent_adjudication_required_on_conflict": True,
                "silent_intersection_forbidden": True,
                "average_forbidden": True,
                "overwrite_forbidden": True,
            },
            "creative_channel_boundary": {
                "review_roles": [
                    "PRIMARY_CONTENT_VALUE",
                    "SECONDARY_FACT_AUTHORIZATION",
                    "INDEPENDENT_ADJUDICATION",
                ],
                "review_role_may_not_be_mapped_to_generation_lane": True,
                "historical_b_channel_is_not_generation_lane_evidence": True,
                "source_generation_lane_or_pair_ref_only_if_source_carries_it": True,
                "source_generation_lane_or_pair_ref_fabrication_forbidden": True,
                "optional_lane_applicability_nonblocking": True,
                "optional_lane_applicability_not_approval_evidence": True,
                "default_lane_applicability_without_source_evidence": "NOT_APPLICABLE",
                "p1a_may_not_assert_dual_channel_qualified": True,
                "p2_to_p6_must_preserve_dual_channel_requirement": True,
            },
            "roles": {
                "PRIMARY_CONTENT_VALUE": {
                    "scope": ["content_quality", "user_value", "content_product_match"],
                    "coverage": "APPLICABLE_POSITIVE_FIRST_OUTPUTS_100_PERCENT",
                },
                "SECONDARY_FACT_AUTHORIZATION": {
                    "scope": [
                        "fact_support",
                        "authorization",
                        "boundary",
                        "route_safety",
                    ],
                    "minimum_review_count": 48,
                    "minimum_per_content_product": 2,
                    "must_cover": ["high_risk", "disagreement"],
                },
                "INDEPENDENT_ADJUDICATION": {
                    "required_when": "PRIMARY_AND_SECONDARY_CONCLUSIONS_CONFLICT",
                    "may_not_be_p1a_builder_or_p1b_freezer": True,
                },
            },
            "p1a_prohibitions": {
                "review_records_created": False,
                "review_decisions_created": False,
                "count_n_frozen": False,
                "component_dispositions_frozen": False,
                "route_gold_answers_frozen": False,
            },
        }
    }
    contract["independent_review_contract"]["contract_digest"] = object_digest(
        contract["independent_review_contract"],
        "contract_digest",
    )
    return contract


def review_record_template() -> dict[str, Any]:
    """Return the sole blank record shape for all independent P1B reviews."""

    template: dict[str, Any] = {
        "unified_independent_review_record_template": {
            "schema_version": "v0.1",
            "template_status": "BLANK_TEMPLATE_NO_REVIEW_DECISION",
            "task_id": TASK_ID,
            "contract_path": REVIEW_CONTRACT_PATH.as_posix(),
            "standard_binding": {
                "snapshot_path": STANDARD_SNAPSHOT_PATH.as_posix(),
                "snapshot_sha256": STANDARD_SHA256,
                "content_formula": "70_PLUS_30_EQUALS_100",
                "component_formula": "80_PLUS_20_EQUALS_100",
                "route_formula": "HARD_PRIMARY_ACTION_AND_REASON_CODE_NO_PER_RECORD_PERCENTAGE",
            },
            "object": {
                "packet_item_id": None,
                "object_type": None,
                "object_id": None,
                "input_digest": None,
                "source_generation_lane_or_pair_ref": None,
                "optional_lane_applicability": None,
            },
            "reviewer": {
                "review_role": None,
                "reviewer_identity_id": None,
                "reviewer_instance_or_session_id": None,
                "review_run_id": None,
                "instruction_digest": None,
                "model_or_instance_configuration_digest": None,
                "review_timestamp": None,
            },
            "evidence_and_evaluation": {
                "evidence_refs": [],
                "content_70_plus_30": {
                    "common_quality_score_out_of_70": None,
                    "content_product_specific_score_out_of_30": None,
                    "total_score_out_of_100": None,
                },
                "component_80_plus_20": {
                    "common_component_score_out_of_80": None,
                    "type_specific_score_out_of_20": None,
                    "total_score_out_of_100": None,
                },
                "route_hard_determination": {
                    "primary_action": None,
                    "reason_code": None,
                },
                "hard_gate": None,
                "veto": None,
                "grade": None,
                "disposition": None,
                "lifecycle_status": None,
                "defects": [],
                "conclusion": None,
            },
            "review_delivery_summary": {
                "coordinator_identity_id": None,
                "overall_score_out_of_100": None,
                "summary_is_not_object_level_approval": True,
            },
            "disagreement": {
                "primary_conclusion_ref": None,
                "secondary_conclusion_ref": None,
                "disagreement_points": [],
                "primary_evidence_refs": [],
                "secondary_evidence_refs": [],
                "adjudicator_identity_id": None,
                "adjudication_conclusion": None,
                "final_disposition": None,
            },
            "append_only_signature": {
                "signature_or_attestation": None,
                "append_only_record_digest": None,
            },
        }
    }
    template["unified_independent_review_record_template"]["template_digest"] = (
        object_digest(
            template["unified_independent_review_record_template"],
            "template_digest",
        )
    )
    return template


def legacy_edge_manifest(source: dict[str, Any]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    sequence = 1
    for row, raw_line in source["component_rows"]:
        component_id = row["component_id"]
        component_digest = row.get("component_digest")
        for content_product_type_id in row["applicable_content_product_type_ids"]:
            edges.append(
                {
                    "legacy_edge_id": f"P1A-LEGACY-EDGE-{sequence:03d}",
                    "component_id": component_id,
                    "content_product_type_id": content_product_type_id,
                    "source": {
                        "path": COMPONENT_SOURCE_PATH.as_posix(),
                        "locator": f"{COMPONENT_SOURCE_PATH}#{component_id}",
                        "record_sha256": sha256_bytes(raw_line.encode("utf-8")),
                        "component_digest": component_digest,
                    },
                    "relationship_lifecycle": "HISTORICAL_UNREVIEWED_NON_ACTIVE",
                    "review_state": "PENDING_INDEPENDENT_REVIEW",
                    "new_generator_consumable": False,
                    "active_edge_claimed": False,
                }
            )
            sequence += 1
    if len(edges) != 543:
        raise ValueError("legacy edge manifest must contain 543 records")
    return edges


def compatibility_receipt(source: dict[str, Any]) -> dict[str, Any]:
    paths = source["paths"]
    receipt: dict[str, Any] = {
        "governance_compatibility_repair_receipt": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "modified_live_checker_count": 2,
            "modified_live_checkers": [
                {
                    "path": B24_CHECKER_PATH.as_posix(),
                    "sha256_before": B24_CHECKER_BEFORE_SHA256,
                    "sha256_after": sha256_file(paths["b24_checker"]),
                    "reason": "Historical B24 protection no longer owns the current branch write surface.",
                    "negative_injection_proof": {
                        "command": "python3 ci/checkers/check_gkb_v2_b_channel_24_component_review.py --selftest",
                        "must_reject": "historical B24 asset mutation",
                    },
                },
                {
                    "path": SUCCESSOR_CHECKER_PATH.as_posix(),
                    "sha256_before": SUCCESSOR_CHECKER_BEFORE_SHA256,
                    "sha256_after": sha256_file(paths["successor_checker"]),
                    "reason": "Historical 19-33 protection remains local; current ledger authority delegates to the existing owner.",
                    "negative_injection_proof": {
                        "command": "python3 ci/checkers/check_orch_generator_v2_b_channel_component_consumption_dev_gate.py --selftest",
                        "must_reject": [
                            "historical route 33 mutation",
                            "unauthorized route 34",
                        ],
                    },
                },
            ],
            "new_current_checker": {
                "path": CURRENT_GATE1_CHECKER_PATH.as_posix(),
                "sha256": sha256_file(paths["current_gate1_checker"]),
                "negative_injection_proof": {
                    "command": "python3 ci/checkers/check_gate1_v1_1_current.py --selftest",
                    "must_reject": [
                        "readiness flip",
                        "unauthorized path",
                        "active legacy edge",
                        "route actual leakage into blind packet",
                        "same reviewer identity",
                        "missing scoring contract",
                    ],
                },
            },
            "v1_current_checker_repair": {
                "path": CURRENT_GATE1_CHECKER_PATH.as_posix(),
                "sha256_before": CURRENT_GATE1_CHECKER_V1_BEFORE_SHA256,
                "sha256_after": sha256_file(paths["current_gate1_checker"]),
                "negative_injection_proof": {
                    "command": "python3 ci/checkers/check_gate1_v1_1_current.py --selftest",
                    "must_reject": [
                        "route actual leakage into blind packet",
                        "same reviewer identity or session/run/signature",
                        "missing scoring contract",
                        "review role mapped to generation lane",
                    ],
                },
            },
            "shared_ledger_or_horizon_modified": False,
            "historical_allowlist_expanded": False,
        }
    }
    receipt["governance_compatibility_repair_receipt"]["receipt_digest"] = (
        object_digest(
            receipt["governance_compatibility_repair_receipt"],
            "receipt_digest",
        )
    )
    return receipt


def p1a_result() -> dict[str, Any]:
    result: dict[str, Any] = {
        "p1a_standard_baseline_preflight_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "execution_status": "PASS_PENDING_INDEPENDENT_REVIEWS",
            "first_gate_verdict": "NOT_CREATED",
            "core_number_impact": {
                "target_total": 300,
                "legacy_reference_content": 120,
                "component_candidates": 86,
                "all_unchanged": True,
            },
            "review_decision_boundary": {
                "review_decisions_created": False,
                "counted_positive_parent_count": "NOT_FROZEN",
                "component_approved_count": "NOT_FROZEN",
                "route_gold_answer_count": 0,
                "route_blind_review_packet_created": True,
                "unified_blank_review_record_template_created": True,
            },
            "readiness": {
                "readiness_changed": False,
                "generation_allowed": False,
                "generator_qualified": False,
                "runtime_ingest_ready": False,
                "production_ready": False,
            },
            "next_action": "IDENTITY_ISOLATED_INDEPENDENT_REVIEWS_ONLY",
        }
    }
    result["p1a_standard_baseline_preflight_result"]["result_digest"] = object_digest(
        result["p1a_standard_baseline_preflight_result"],
        "result_digest",
    )
    return result


def output_bytes(root: Path, use_external_standard: bool) -> dict[Path, bytes]:
    source = read_sources(root)
    if use_external_standard:
        if not STANDARD_EXTERNAL_PATH.exists():
            raise FileNotFoundError(STANDARD_EXTERNAL_PATH)
        standard_bytes = STANDARD_EXTERNAL_PATH.read_bytes()
        if sha256_bytes(standard_bytes) != STANDARD_SHA256:
            raise ValueError("external v1.1 standard sha256 mismatch")
    else:
        snapshot_path = root / STANDARD_SNAPSHOT_PATH
        if not snapshot_path.exists():
            raise FileNotFoundError(snapshot_path)
        standard_bytes = snapshot_path.read_bytes()
        if sha256_bytes(standard_bytes) != STANDARD_SHA256:
            raise ValueError("repository v1.1 standard snapshot sha256 mismatch")

    return {
        STANDARD_SNAPSHOT_PATH: standard_bytes,
        STANDARD_CONTRACT_PATH: yaml_bytes(standard_contract()),
        BASELINE_MANIFEST_PATH: yaml_bytes(baseline_manifest(source)),
        REVIEW_PACKET_PATH: jsonl_bytes(review_packet(source)),
        REVIEW_CONTRACT_PATH: yaml_bytes(review_contract()),
        REVIEW_RECORD_TEMPLATE_PATH: yaml_bytes(review_record_template()),
        LEGACY_EDGE_MANIFEST_PATH: jsonl_bytes(legacy_edge_manifest(source)),
        COMPAT_RECEIPT_PATH: yaml_bytes(compatibility_receipt(source)),
        RESULT_PATH: yaml_bytes(p1a_result()),
    }


def write_outputs(root: Path) -> list[str]:
    written: list[str] = []
    for relative_path, content in output_bytes(
        root, use_external_standard=True
    ).items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != content:
            path.write_bytes(content)
            written.append(relative_path.as_posix())
    return written


def check_outputs(root: Path) -> list[str]:
    mismatches: list[str] = []
    expected = output_bytes(root, use_external_standard=False)
    for relative_path, content in expected.items():
        path = root / relative_path
        if not path.exists() or path.read_bytes() != content:
            mismatches.append(relative_path.as_posix())
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify materialized outputs without writing",
    )
    args = parser.parse_args()
    try:
        if args.check:
            mismatches = check_outputs(ROOT)
            if mismatches:
                print(
                    json.dumps(
                        {"status": "CHECK_FAIL", "mismatches": mismatches},
                        ensure_ascii=False,
                    )
                )
                return 1
            print(
                json.dumps(
                    {"status": "CHECK_PASS", "task_id": TASK_ID}, ensure_ascii=False
                )
            )
            return 0
        written = write_outputs(ROOT)
        print(
            json.dumps(
                {"status": "MATERIALIZED", "written": written}, ensure_ascii=False
            )
        )
        return 0
    except (
        FileNotFoundError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        print(
            json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
