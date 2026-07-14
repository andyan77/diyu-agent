#!/usr/bin/env python3
"""Build and validate the isolated review evidence for P3 repair attempt 1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from p3_common import (
    ROOT,
    TASK_ID,
    TASK_ROOT,
    canonical_json,
    digest_object,
    jsonl_bytes,
    load_jsonl,
    object_digest,
    profile_rows,
    require,
    sha256_bytes,
    sha256_file,
    yaml_bytes,
)
from p3_open_r1 import (
    MACHINE_REPORT_R1_PATH,
    POSITIVE_OUTPUT_R1_PATH,
    ROUTE_ACTUAL_R1_PATH,
    ROUTE_COMPARISON_R1_PATH,
    validate_positive_file_r1,
)
from p3_repair import (
    ATTEMPT_0_ADJUDICATION_PATH,
    ATTEMPT_0_REVIEW_ONE_PATH,
    ATTEMPT_0_REVIEW_TWO_PATH,
    DIFFERENCE_R1_PATH,
    FREEZE_MANIFEST_R1_PATH,
    REMOVAL_R1_PATH,
    REPAIR_BASIS_PATH,
    STRUCTURE_R1_PATH,
)


REVIEW_ROOT = TASK_ROOT / "review/attempt_1"
BLIND_PACKET_R1_PATH = REVIEW_ROOT / "blind_positive_20.v0.2.jsonl"
BLIND_LABEL_R1_PATH = REVIEW_ROOT / "blind_label_mapping.v0.2.jsonl"
CHOICE_CATALOG_R1_PATH = REVIEW_ROOT / "content_product_choice_catalog.v0.2.jsonl"
REVIEW_CONTRACT_R1_PATH = REVIEW_ROOT / "independent_review_contract.v0.2.yaml"
REVIEW_PACKET_R1_PATH = REVIEW_ROOT / "p3_review_packet.v0.2.yaml"
REVIEW_ONE_R1_PATH = REVIEW_ROOT / "signed_content_value_review.v0.2.json"
REVIEW_TWO_R1_PATH = REVIEW_ROOT / "signed_fact_authorization_review.v0.2.json"
ADJUDICATION_R1_PATH = REVIEW_ROOT / "targeted_adjudication.v0.2.json"
STAGING_ONE_R1_PATH = REVIEW_ROOT / "staging/content_value_blind_stage.v0.2.json"
STAGING_TWO_R1_PATH = REVIEW_ROOT / "staging/fact_authorization_blind_stage.v0.2.json"

PUBLIC_DIMENSIONS = {
    "truth_evidence_traceability": 20,
    "apparel_business_specificity": 10,
    "role_brand_viewpoint_consistency": 10,
    "user_value_information_gain": 10,
    "platform_native_executability": 10,
    "anti_formula_ethics_restraint": 10,
}
PRODUCT_DIMENSIONS = {
    "core_product_value": 15,
    "product_specific_narrative_av": 10,
    "continuity_composability_accumulation": 5,
}
CRITICAL_MINIMUMS = {
    "A": {
        "truth_evidence_traceability": 18,
        "core_product_value": 13,
        "role_brand_viewpoint_consistency": 8,
        "platform_native_executability": 8,
        "anti_formula_ethics_restraint": 8,
    },
    "B": {
        "truth_evidence_traceability": 17,
        "core_product_value": 12,
        "role_brand_viewpoint_consistency": 7,
        "platform_native_executability": 7,
        "anti_formula_ethics_restraint": 7,
    },
}
VALID_PROFILES = {f"CP{index:02d}" for index in range(1, 21)}
REVIEW_ROLES = {
    "CONTENT_PRODUCT_USER_VALUE_STRUCTURE_PLATFORM_ANTI_FORMULA",
    "FACT_SOURCE_AUTHORIZATION_CLAIM_COMPONENT_ROUTE_SAFETY",
}
FORBIDDEN_REVIEW_IDENTITIES = {
    "P3-CONTROLLED-AUTHOR-GPT56SOL-001",
    "P3-EXECUTOR-BUILDER-FINALIZER-001",
}


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (canonical_json(dict(value)) + "\n").encode("utf-8")


def _blind_documents(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    outputs = validate_positive_file_r1(root)
    ordered = sorted(outputs, key=lambda row: digest_object(str(row["output_digest"])))
    packet: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    for index, output in enumerate(ordered, 1):
        blind_id = f"P3-R1-BLIND-{index:02d}"
        packet.append(
            {
                "blind_id": blind_id,
                "synthetic_disclosure": output["synthetic_disclosure"],
                "title": output["title"],
                "body": output["body"],
                "spoken_lines": output["spoken_lines"],
                "cta": output["cta"],
                "visual_execution": output["visual_execution"],
                "audio_execution": output["audio_execution"],
                "output_digest": output["output_digest"],
                "item_profile_id_and_name_hidden": True,
            }
        )
        label: dict[str, Any] = {
            "blind_id": blind_id,
            "profile_id": output["profile_id"],
            "request_id": output["request_id"],
            "output_digest": output["output_digest"],
        }
        label["label_digest"] = object_digest(label, "label_digest")
        labels.append(label)
    return packet, labels


def _choice_catalog(root: Path) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for profile in sorted(profile_rows(root), key=lambda row: row["content_product_type_id"]):
        row: dict[str, Any] = {
            "profile_id": profile["content_product_type_id"],
            "chinese_label": profile["chinese_label"],
            "business_purpose": profile["business_purpose"],
            "founder_core_inputs": profile["founder_core_inputs"],
            "target_account_roles": profile["target_account_roles"],
            "target_platforms": profile["target_platforms"],
            "catalog_is_fixed_before_blind_review": True,
        }
        row["catalog_row_digest"] = object_digest(row, "catalog_row_digest")
        catalog.append(row)
    require({row["profile_id"] for row in catalog} == VALID_PROFILES, "E_P3_R1_CATALOG")
    return catalog


def build_review_documents(root: Path = ROOT) -> dict[Path, bytes]:
    blind, labels = _blind_documents(root)
    catalog = _choice_catalog(root)
    contract: dict[str, Any] = {
        "schema_version": "gate1-p3-independent-review-contract-v0.2",
        "task_id": TASK_ID,
        "attempt": 1,
        "reviewer_identity_policy": {
            "reviewer_must_not_be_author_executor_builder_or_finalizer": True,
            "two_reviewers_must_be_distinct_instances_sessions_and_runs": True,
            "blind_packet_and_fixed_choice_catalog_only_before_stage_1_signature": True,
            "label_mapping_reveal_only_after_stage_1_signature": True,
        },
        "review_roles": sorted(REVIEW_ROLES),
        "public_quality_dimensions": PUBLIC_DIMENSIONS,
        "product_quality_dimensions": PRODUCT_DIMENSIONS,
        "grade_bands": {"A": [90, 100], "B": [80, 89], "C": [70, 79], "D": [0, 69]},
        "critical_minimums": CRITICAL_MINIMUMS,
        "hard_vetoes": [
            "FABRICATED_OR_REALITY_WASHED_FACT",
            "UNBOUND_OR_OUT_OF_SCOPE_CLAIM",
            "AUTHORIZATION_OR_PRIVACY_VIOLATION",
            "CROSS_SUBJECT_OR_TENANT_MISUSE",
            "PRODUCT_MANDATORY_INPUT_OR_GUARD_VIOLATION",
            "UNSAFE_OR_DISCRIMINATORY_PROMISE",
            "SUBSTANTIAL_SOURCE_OR_LEGACY_COPY",
            "SELF_APPROVAL_OR_READINESS_ESCALATION",
        ],
        "p3_pass_lines": {
            "first_acceptable_count_minimum": 18,
            "blind_top1_correct_count_minimum": 17,
            "formula_or_near_duplicate_profile_count_maximum": 2,
            "route_action_and_reason_accuracy": 1.0,
            "hard_error_count": 0,
            "structure_hard_gate_pass_required": True,
        },
        "score_definition": "The arithmetic mean of all twenty v1.1 70+30 scores; structure and route remain non-compensable hard gates.",
    }
    contract["contract_digest"] = object_digest(contract, "contract_digest")
    payloads = {
        BLIND_PACKET_R1_PATH: jsonl_bytes(blind),
        BLIND_LABEL_R1_PATH: jsonl_bytes(labels),
        CHOICE_CATALOG_R1_PATH: jsonl_bytes(catalog),
        REVIEW_CONTRACT_R1_PATH: yaml_bytes({"independent_review_contract": contract}),
    }
    artifact_paths = {
        "blind_positive": BLIND_PACKET_R1_PATH,
        "blind_labels_reveal_after_stage_1": BLIND_LABEL_R1_PATH,
        "fixed_choice_catalog_visible_at_stage_1": CHOICE_CATALOG_R1_PATH,
        "structure_80": STRUCTURE_R1_PATH,
        "structure_difference_80": DIFFERENCE_R1_PATH,
        "axis_removal_480": REMOVAL_R1_PATH,
        "positive_20": POSITIVE_OUTPUT_R1_PATH,
        "route_actual_20": ROUTE_ACTUAL_R1_PATH,
        "route_comparison_20": ROUTE_COMPARISON_R1_PATH,
        "machine_report": MACHINE_REPORT_R1_PATH,
        "repair_freeze": FREEZE_MANIFEST_R1_PATH,
        "repair_basis": REPAIR_BASIS_PATH,
        "attempt_0_content_review": ATTEMPT_0_REVIEW_ONE_PATH,
        "attempt_0_fact_review": ATTEMPT_0_REVIEW_TWO_PATH,
        "attempt_0_adjudication": ATTEMPT_0_ADJUDICATION_PATH,
    }
    packet: dict[str, Any] = {
        "schema_version": "gate1-p3-review-packet-v0.2",
        "task_id": TASK_ID,
        "attempt": 1,
        "review_contract_path": REVIEW_CONTRACT_R1_PATH.as_posix(),
        "review_contract_digest": contract["contract_digest"],
        "stage_order": [
            "READ_FIXED_CHOICE_CATALOG_AND_BLIND_PACKET_ONLY",
            "RECORD_AND_SIGN_TWENTY_TOP1_PREDICTIONS",
            "REVEAL_LABEL_MAPPING_AFTER_SIGNED_STAGE_FILE_EXISTS",
            "READ_ALL_EIGHTY_STRUCTURES_TWENTY_POSITIVES_TWENTY_ROUTES_AND_FAILURE_EVIDENCE",
            "SCORE_ALL_TWENTY_POSITIVES_AND_SIGN_FINAL_REPORT",
        ],
        "artifacts": {
            name: {
                "path": path.as_posix(),
                "sha256": sha256_bytes(payloads[path]) if path in payloads else sha256_file(root / path),
            }
            for name, path in artifact_paths.items()
        },
        "positive_count": 20,
        "structure_count": 80,
        "route_count": 20,
        "counts_toward_300": 0,
    }
    packet["packet_digest"] = object_digest(packet, "packet_digest")
    payloads[REVIEW_PACKET_R1_PATH] = yaml_bytes({"p3_review_packet": packet})
    return payloads


def materialize_review_packet(root: Path = ROOT) -> list[Path]:
    changed: list[Path] = []
    for relative, payload in build_review_documents(root).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
            changed.append(path)
    return changed


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def _critical_minimum_pass(score: Mapping[str, Any], grade: str) -> bool:
    if grade not in CRITICAL_MINIMUMS:
        return False
    merged = {**score["public_quality"], **score["product_quality"]}
    return all(int(merged[key]) >= value for key, value in CRITICAL_MINIMUMS[grade].items())


def validate_blind_stage(stage: Mapping[str, Any], expected_role: str, root: Path = ROOT) -> None:
    required = {
        "schema_version",
        "task_id",
        "review_id",
        "reviewer_identity",
        "reviewer_platform_agent_id",
        "reviewer_session_id",
        "review_run_id",
        "reviewer_role",
        "reviewer_model_capability_id",
        "reviewer_reasoning_effort",
        "recorded_before_label_reveal",
        "label_mapping_accessed",
        "blind_packet_sha256",
        "choice_catalog_sha256",
        "predictions",
        "blind_stage_digest",
    }
    require(set(stage) == required, "E_P3_R1_BLIND_FIELD_SET")
    require(stage["schema_version"] == "gate1-p3-blind-stage-v0.2", "E_P3_R1_BLIND_SCHEMA")
    require(stage["task_id"] == TASK_ID and stage["reviewer_role"] == expected_role, "E_P3_R1_BLIND_ROLE")
    require(stage["reviewer_identity"] not in FORBIDDEN_REVIEW_IDENTITIES, "E_P3_R1_BLIND_IDENTITY")
    require(stage["recorded_before_label_reveal"] is True, "E_P3_R1_BLIND_ORDER")
    require(stage["label_mapping_accessed"] is False, "E_P3_R1_BLIND_LABEL_ACCESS")
    require(stage["blind_packet_sha256"] == sha256_file(root / BLIND_PACKET_R1_PATH), "E_P3_R1_BLIND_SHA")
    require(stage["choice_catalog_sha256"] == sha256_file(root / CHOICE_CATALOG_R1_PATH), "E_P3_R1_CATALOG_SHA")
    predictions = stage["predictions"]
    blind_ids = {row["blind_id"] for row in load_jsonl(root / BLIND_PACKET_R1_PATH)}
    require(isinstance(predictions, list) and len(predictions) == 20, "E_P3_R1_BLIND_COUNT")
    require({row.get("blind_id") for row in predictions} == blind_ids, "E_P3_R1_BLIND_COVERAGE")
    for prediction in predictions:
        require(set(prediction) == {"blind_id", "predicted_profile_id", "reason"}, "E_P3_R1_BLIND_PREDICTION_FIELDS")
        require(prediction["predicted_profile_id"] in VALID_PROFILES, "E_P3_R1_BLIND_PROFILE")
        require(isinstance(prediction["reason"], str) and bool(prediction["reason"].strip()), "E_P3_R1_BLIND_REASON")
    require(stage["blind_stage_digest"] == object_digest(dict(stage), "blind_stage_digest"), "E_P3_R1_BLIND_DIGEST")


def validate_review_report(report: Mapping[str, Any], expected_role: str, root: Path = ROOT) -> None:
    required = {
        "schema_version",
        "task_id",
        "review_id",
        "reviewer_identity",
        "reviewer_platform_agent_id",
        "reviewer_session_id",
        "review_run_id",
        "reviewer_model_capability_id",
        "reviewer_reasoning_effort",
        "reviewer_role",
        "author_identity_excluded",
        "executor_builder_finalizer_identity_excluded",
        "blind_stage",
        "coverage",
        "positive_scores",
        "p3_score",
        "first_acceptable_count",
        "first_acceptance_rate",
        "blind_top1_correct_count",
        "blind_top1_accuracy",
        "human_confirmed_formula_or_near_duplicate_profile_ids",
        "human_confirmed_formula_or_near_duplicate_rate",
        "hard_error_profile_ids",
        "structure_hard_gate_pass",
        "route_hard_gate_pass",
        "findings",
        "overall_verdict",
        "signed_record_digest",
    }
    require(set(report) == required, "E_P3_R1_REVIEW_FIELD_SET")
    require(report["schema_version"] == "gate1-p3-independent-review-v0.2", "E_P3_R1_REVIEW_SCHEMA")
    require(report["task_id"] == TASK_ID and report["reviewer_role"] == expected_role, "E_P3_R1_REVIEW_ROLE")
    require(report["reviewer_identity"] not in FORBIDDEN_REVIEW_IDENTITIES, "E_P3_R1_REVIEW_IDENTITY")
    require(report["author_identity_excluded"] is True, "E_P3_R1_REVIEW_AUTHOR_COLLISION")
    require(report["executor_builder_finalizer_identity_excluded"] is True, "E_P3_R1_REVIEW_EXECUTOR_COLLISION")
    validate_blind_stage(report["blind_stage"], expected_role, root)
    labels = {row["blind_id"]: row for row in load_jsonl(root / BLIND_LABEL_R1_PATH)}
    predictions = report["blind_stage"]["predictions"]
    expected_correct = sum(row["predicted_profile_id"] == labels[row["blind_id"]]["profile_id"] for row in predictions)
    require(
        report["coverage"]
        == {
            "structure_records_read": 80,
            "positive_outputs_read": 20,
            "route_results_read": 20,
            "machine_report_read": True,
            "attempt_0_failure_records_read": True,
            "attempt_1_repair_basis_read": True,
        },
        "E_P3_R1_REVIEW_COVERAGE",
    )
    scores = report["positive_scores"]
    require(isinstance(scores, list) and len(scores) == 20, "E_P3_R1_REVIEW_SCORE_COUNT")
    require({row.get("profile_id") for row in scores} == VALID_PROFILES, "E_P3_R1_REVIEW_SCORE_PROFILES")
    outputs = {row["profile_id"]: row for row in load_jsonl(root / POSITIVE_OUTPUT_R1_PATH)}
    accepted_count = 0
    for score in scores:
        profile_id = score["profile_id"]
        require(score["request_id"] == outputs[profile_id]["request_id"], "E_P3_R1_REVIEW_REQUEST")
        require(set(score["public_quality"]) == set(PUBLIC_DIMENSIONS), "E_P3_R1_REVIEW_PUBLIC_FIELDS")
        require(set(score["product_quality"]) == set(PRODUCT_DIMENSIONS), "E_P3_R1_REVIEW_PRODUCT_FIELDS")
        for key, maximum in PUBLIC_DIMENSIONS.items():
            require(isinstance(score["public_quality"][key], int) and 0 <= score["public_quality"][key] <= maximum, "E_P3_R1_REVIEW_PUBLIC_SCORE", key)
        for key, maximum in PRODUCT_DIMENSIONS.items():
            require(isinstance(score["product_quality"][key], int) and 0 <= score["product_quality"][key] <= maximum, "E_P3_R1_REVIEW_PRODUCT_SCORE", key)
        total = sum(score["public_quality"].values()) + sum(score["product_quality"].values())
        grade = _grade(total)
        minimum_pass = _critical_minimum_pass(score, grade)
        require(score["total_score"] == total and score["grade"] == grade, "E_P3_R1_REVIEW_TOTAL")
        require(score["critical_minimum_pass"] is minimum_pass, "E_P3_R1_REVIEW_MINIMUM")
        require(isinstance(score["hard_vetoes"], list), "E_P3_R1_REVIEW_VETOES")
        expected_acceptable = grade in {"A", "B"} and minimum_pass and not score["hard_vetoes"]
        require(score["first_acceptable"] is expected_acceptable, "E_P3_R1_REVIEW_ACCEPTABLE")
        require(isinstance(score["evidence"], list) and score["evidence"], "E_P3_R1_REVIEW_EVIDENCE")
        require(isinstance(score["defects"], list), "E_P3_R1_REVIEW_DEFECTS")
        accepted_count += int(expected_acceptable)
    average = round(sum(row["total_score"] for row in scores) / 20, 2)
    require(report["p3_score"] == average, "E_P3_R1_REVIEW_AVERAGE")
    require(report["first_acceptable_count"] == accepted_count, "E_P3_R1_REVIEW_ACCEPTED_COUNT")
    require(report["first_acceptance_rate"] == round(accepted_count / 20, 4), "E_P3_R1_REVIEW_ACCEPTED_RATE")
    require(report["blind_top1_correct_count"] == expected_correct, "E_P3_R1_REVIEW_BLIND_CORRECT")
    require(report["blind_top1_accuracy"] == round(expected_correct / 20, 4), "E_P3_R1_REVIEW_BLIND_RATE")
    formula_ids = set(report["human_confirmed_formula_or_near_duplicate_profile_ids"])
    hard_ids = set(report["hard_error_profile_ids"])
    require(formula_ids.issubset(VALID_PROFILES), "E_P3_R1_REVIEW_FORMULA_IDS")
    require(hard_ids.issubset(VALID_PROFILES), "E_P3_R1_REVIEW_HARD_IDS")
    require(report["human_confirmed_formula_or_near_duplicate_rate"] == round(len(formula_ids) / 20, 4), "E_P3_R1_REVIEW_FORMULA_RATE")
    pass_conditions = (
        accepted_count >= 18
        and expected_correct >= 17
        and len(formula_ids) <= 2
        and not hard_ids
        and report["structure_hard_gate_pass"] is True
        and report["route_hard_gate_pass"] is True
    )
    require(report["overall_verdict"] == ("PASS" if pass_conditions else "FAIL"), "E_P3_R1_REVIEW_VERDICT")
    require(report["signed_record_digest"] == object_digest(dict(report), "signed_record_digest"), "E_P3_R1_REVIEW_DIGEST")


def load_and_validate_reports(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    one = json.loads((root / REVIEW_ONE_R1_PATH).read_text(encoding="utf-8"))
    two = json.loads((root / REVIEW_TWO_R1_PATH).read_text(encoding="utf-8"))
    roles = sorted(REVIEW_ROLES)
    validate_review_report(one, roles[0], root)
    validate_review_report(two, roles[1], root)
    distinct = {
        one["reviewer_identity"],
        two["reviewer_identity"],
        one["reviewer_platform_agent_id"],
        two["reviewer_platform_agent_id"],
        one["reviewer_session_id"],
        two["reviewer_session_id"],
        one["review_run_id"],
        two["review_run_id"],
    }
    require(len(distinct) == 8, "E_P3_R1_REVIEW_IDENTITY_COLLISION")
    return one, two


def substantive_disagreements(one: Mapping[str, Any], two: Mapping[str, Any]) -> list[dict[str, Any]]:
    first = {row["profile_id"]: row for row in one["positive_scores"]}
    second = {row["profile_id"]: row for row in two["positive_scores"]}
    rows: list[dict[str, Any]] = []
    for profile_id in sorted(VALID_PROFILES):
        reasons: list[str] = []
        if first[profile_id]["first_acceptable"] != second[profile_id]["first_acceptable"]:
            reasons.append("FIRST_ACCEPTANCE_DISAGREEMENT")
        if set(first[profile_id]["hard_vetoes"]) != set(second[profile_id]["hard_vetoes"]):
            reasons.append("HARD_VETO_DISAGREEMENT")
        if reasons:
            rows.append({"profile_id": profile_id, "reasons": reasons})
    if one["structure_hard_gate_pass"] != two["structure_hard_gate_pass"]:
        rows.append({"profile_id": "STRUCTURE_GATE", "reasons": ["STRUCTURE_GATE_DISAGREEMENT"]})
    if one["route_hard_gate_pass"] != two["route_hard_gate_pass"]:
        rows.append({"profile_id": "ROUTE_GATE", "reasons": ["ROUTE_GATE_DISAGREEMENT"]})
    return rows


def check_materialized(root: Path = ROOT) -> None:
    for path, expected in build_review_documents(root).items():
        require((root / path).read_bytes() == expected, "E_P3_R1_REVIEW_PACKET_DRIFT", path.as_posix())
    if (root / REVIEW_ONE_R1_PATH).exists() or (root / REVIEW_TWO_R1_PATH).exists():
        load_and_validate_reports(root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--validate-reports", action="store_true")
    args = parser.parse_args()
    if args.materialize:
        changed = materialize_review_packet()
        print(canonical_json({"status": "P3_R1_REVIEW_PACKET_READY", "changed": [path.as_posix() for path in changed]}))
    elif args.validate_reports:
        one, two = load_and_validate_reports()
        print(canonical_json({"status": "P3_R1_REVIEWS_VALID", "scores": [one["p3_score"], two["p3_score"]]}))
    elif args.check:
        check_materialized()
        print(canonical_json({"status": "P3_R1_REVIEW_CHECK_PASS"}))
    else:
        parser.error("choose --materialize, --check, or --validate-reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
