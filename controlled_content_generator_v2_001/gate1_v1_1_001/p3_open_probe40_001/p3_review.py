#!/usr/bin/env python3
"""Build and validate the isolated P3 review packet and signed reports."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from p3_common import (
    BASELINE_COMMIT,
    ROOT,
    TASK_ID,
    TASK_ROOT,
    digest_object,
    jsonl_bytes,
    load_jsonl,
    load_yaml,
    object_digest,
    require,
    sha256_bytes,
    sha256_file,
    yaml_bytes,
)
from p3_open_core import (
    MACHINE_REPORT_PATH,
    POSITIVE_OUTPUT_PATH,
    ROUTE_ACTUAL_PATH,
    ROUTE_COMPARISON_PATH,
    validate_positive_file,
)
from p3_prepare import FREEZE_MANIFEST_PATH
from p3_structure import DIFFERENCE_PATH, REMOVAL_PATH, STRUCTURE_PATH


BLIND_PACKET_PATH = TASK_ROOT / "review/blind_positive_20.v0.1.jsonl"
BLIND_LABEL_PATH = TASK_ROOT / "review/blind_label_mapping.v0.1.jsonl"
REVIEW_CONTRACT_PATH = TASK_ROOT / "review/independent_review_contract.v0.1.yaml"
REVIEW_PACKET_PATH = TASK_ROOT / "review/p3_review_packet.v0.1.yaml"
REVIEW_ONE_PATH = TASK_ROOT / "review/signed_content_value_review.v0.1.json"
REVIEW_TWO_PATH = TASK_ROOT / "review/signed_fact_authorization_review.v0.1.json"
ADJUDICATION_PATH = TASK_ROOT / "review/targeted_adjudication.v0.1.json"

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
VALID_PROFILES = {f"CP{index:02d}" for index in range(1, 21)}
FREEZE_MANIFEST_V2_PATH = TASK_ROOT / "freeze/p3_open_baseline_manifest.v0.2.yaml"
FREEZE_CORRECTION_PATH = TASK_ROOT / "freeze/freeze_digest_correction_receipt.v0.1.yaml"
FREEZE_COMMIT = "bb598b098bf2fc673ede61a0f947d5e485ac7058"
FREEZE_DIGEST_CORRECTIONS = {
    "positive_assignments": {
        "sha256": "1f06c942cee782e8b46b8aea2980b5ff8203a294c91e84f73f1961e978aef53d",
        "legacy_object_digest": "53f3c5b0cea67183ab389c38580052637c9e2e255f23d83b4cb21b2f4f3d3692",
        "git_blob_oid": "5a3b4b37d83223fecb1197a1a3feb90f946ec84e",
    },
    "author_requests": {
        "sha256": "6e649ca0bb255b4cbbdd4bd97f1441cb654bb73f4715da35250f8de561ceb279",
        "legacy_object_digest": "722b50c465d99f8fb98fba1ce4c9cc40ed9231cef5fd02dbd7b52172df7de6d3",
        "git_blob_oid": "353f67fcab0b013b0ea78561578b1599c09aac40",
    },
    "route_selections": {
        "sha256": "7f01fa79931db680835e96569e774da6f315b4a889f8ee5b0b4289a6b339c9af",
        "legacy_object_digest": "2552a4da96f751049ff4836a7e09a729521e5569569c3c06864c49200dbf154b",
        "git_blob_oid": "9b9e893de42f525c0ef98b3b4de8e5f6bca39a28",
    },
    "route_inputs": {
        "sha256": "118de86e842ae80c8d7bd40c36c5b1f7d1ee1f296c4bad8f5013a33887c8c9b3",
        "legacy_object_digest": "342caccac01bf24d73b3885a880f29f0c3cbf947fc18aba1cbe23513a4416814",
        "git_blob_oid": "ef26ddc26d242a7d8b44f2222eda74923b620a72",
    },
}


def _freeze_correction_documents(root: Path) -> dict[Path, bytes]:
    original = load_yaml(root / FREEZE_MANIFEST_PATH)
    manifest = copy.deepcopy(original["p3_open_baseline_manifest"])
    correction_rows: list[dict[str, Any]] = []
    for key, expected in FREEZE_DIGEST_CORRECTIONS.items():
        item = manifest[key]
        require(
            item["sha256"] == expected["legacy_object_digest"],
            "E_P3_FREEZE_LEGACY_DIGEST_DRIFT",
            key,
        )
        actual_sha256 = sha256_file(root / item["path"])
        require(
            actual_sha256 == expected["sha256"],
            "E_P3_FREEZE_CORRECTED_FILE_DRIFT",
            key,
        )
        item["legacy_v0_1_object_digest"] = item["sha256"]
        item["sha256"] = actual_sha256
        correction_rows.append(
            {
                "manifest_key": key,
                "path": item["path"],
                "legacy_v0_1_object_digest": expected["legacy_object_digest"],
                "corrected_file_sha256": actual_sha256,
                "git_blob_oid_at_freeze_commit": expected["git_blob_oid"],
                "byte_mutation_count": 0,
            }
        )
    manifest["schema_version"] = "gate1-p3-open-freeze-manifest-v0.2"
    manifest["freeze_commit"] = FREEZE_COMMIT
    manifest["supersedes_metadata_path"] = FREEZE_MANIFEST_PATH.as_posix()
    manifest["superseded_manifest_sha256"] = sha256_file(root / FREEZE_MANIFEST_PATH)
    manifest["correction_scope"] = "FOUR_FIELDS_OBJECT_DIGEST_MISLABELED_AS_FILE_SHA256"
    manifest["frozen_input_byte_mutation_count"] = 0
    manifest["author_or_route_rerun_count_due_to_correction"] = 0
    manifest["open_core_repair_window_used"] = False
    manifest["freeze_manifest_digest"] = object_digest(manifest, "freeze_manifest_digest")
    manifest_payload = yaml_bytes({"p3_open_baseline_manifest": manifest})

    receipt: dict[str, Any] = {
        "schema_version": "gate1-p3-freeze-digest-correction-v0.1",
        "task_id": TASK_ID,
        "baseline_commit": manifest["baseline_commit"],
        "freeze_commit": FREEZE_COMMIT,
        "current_review_head_policy": "MUST_DESCEND_FROM_FREEZE_COMMIT",
        "original_manifest_path": FREEZE_MANIFEST_PATH.as_posix(),
        "original_manifest_sha256": sha256_file(root / FREEZE_MANIFEST_PATH),
        "corrected_manifest_path": FREEZE_MANIFEST_V2_PATH.as_posix(),
        "corrected_manifest_sha256": sha256_bytes(manifest_payload),
        "root_cause": "digest_object(list) was stored under four sha256 field names",
        "corrections": correction_rows,
        "frozen_files_present_in_commit_before_author_run": True,
        "frozen_input_byte_mutation_count": 0,
        "author_output_mutation_count": 0,
        "route_actual_mutation_count": 0,
        "author_rerun_count": 0,
        "metadata_only_correction": True,
        "open_core_repair_window_used": False,
    }
    receipt["receipt_digest"] = object_digest(receipt, "receipt_digest")
    return {
        FREEZE_MANIFEST_V2_PATH: manifest_payload,
        FREEZE_CORRECTION_PATH: yaml_bytes({"freeze_digest_correction_receipt": receipt}),
    }


def _blind_documents(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    outputs = validate_positive_file(root)
    ordered = sorted(outputs, key=lambda row: digest_object(str(row["output_digest"])))
    packet: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    for index, output in enumerate(ordered, 1):
        blind_id = f"P3-BLIND-{index:02d}"
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
                "product_id_and_name_hidden": True,
            }
        )
        label = {
            "blind_id": blind_id,
            "profile_id": output["profile_id"],
            "request_id": output["request_id"],
            "output_digest": output["output_digest"],
        }
        label["label_digest"] = object_digest(label, "label_digest")
        labels.append(label)
    return packet, labels


def build_review_documents(root: Path = ROOT) -> dict[str, bytes]:
    blind, labels = _blind_documents(root)
    correction_documents = _freeze_correction_documents(root)
    contract: dict[str, Any] = {
        "schema_version": "gate1-p3-independent-review-contract-v0.1",
        "task_id": TASK_ID,
        "reviewer_identity_policy": {
            "reviewer_must_not_be_author": True,
            "reviewer_must_not_be_executor_builder_or_finalizer": True,
            "two_reviewers_must_be_distinct_instances_and_sessions": True,
            "blind_prediction_must_be_recorded_before_label_reveal": True,
        },
        "execution_lineage": {
            "task_baseline_commit": BASELINE_COMMIT,
            "freeze_commit": FREEZE_COMMIT,
            "review_head_policy": "MUST_DESCEND_FROM_FREEZE_COMMIT",
            "frozen_input_policy": "VERIFY_FILE_BYTES_AGAINST_CORRECTED_V0_2_MANIFEST",
            "legacy_manifest_policy": "PRESERVE_V0_1_AS_METADATA_ERROR_EVIDENCE",
        },
        "review_roles": {
            "review_1": "CONTENT_PRODUCT_USER_VALUE_STRUCTURE_PLATFORM_ANTI_FORMULA",
            "review_2": "FACT_SOURCE_AUTHORIZATION_CLAIM_COMPONENT_ROUTE_SAFETY",
        },
        "public_quality_dimensions": PUBLIC_DIMENSIONS,
        "product_quality_dimensions": PRODUCT_DIMENSIONS,
        "grade_bands": {"A": [90, 100], "B": [80, 89], "C": [70, 79], "D": [0, 69]},
        "critical_minimums": {
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
        },
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
            "first_acceptance_rate_minimum": 0.90,
            "blind_top1_accuracy_minimum": 0.85,
            "human_confirmed_formula_or_near_duplicate_rate_maximum": 0.10,
            "route_action_and_reason_accuracy": 1.0,
            "hard_error_count": 0,
            "structure_hard_gate_pass_required": True,
        },
        "score_definition": "Arithmetic mean of the 20 positive 70+30 scores; structure and route are separate non-compensable hard gates.",
    }
    contract["contract_digest"] = object_digest(contract, "contract_digest")
    blind_payload = jsonl_bytes(blind)
    label_payload = jsonl_bytes(labels)
    contract_payload = yaml_bytes({"independent_review_contract": contract})
    artifacts = {
        "blind_positive": BLIND_PACKET_PATH,
        "blind_labels_reveal_after_stage_1": BLIND_LABEL_PATH,
        "structure_80": STRUCTURE_PATH,
        "structure_difference_80": DIFFERENCE_PATH,
        "axis_removal_480": REMOVAL_PATH,
        "positive_20": POSITIVE_OUTPUT_PATH,
        "route_actual_20": ROUTE_ACTUAL_PATH,
        "route_comparison_20": ROUTE_COMPARISON_PATH,
        "machine_report": MACHINE_REPORT_PATH,
        "freeze_manifest_legacy_v0_1": FREEZE_MANIFEST_PATH,
        "freeze_manifest_authoritative_v0_2": FREEZE_MANIFEST_V2_PATH,
        "freeze_digest_correction_receipt": FREEZE_CORRECTION_PATH,
    }
    packet: dict[str, Any] = {
        "schema_version": "gate1-p3-review-packet-v0.1",
        "task_id": TASK_ID,
        "review_contract_path": REVIEW_CONTRACT_PATH.as_posix(),
        "review_contract_digest": contract["contract_digest"],
        "stage_order": [
            "READ_BLIND_PACKET_AND_RECORD_20_TOP1_PREDICTIONS",
            "SIGN_BLIND_STAGE_DIGEST",
            "REVEAL_LABEL_MAPPING",
            "READ_ALL_80_STRUCTURES_20_POSITIVES_20_ROUTES_AND_MACHINE_EVIDENCE",
            "SCORE_ALL_20_POSITIVES_AND_SIGN_FINAL_REPORT",
        ],
        "artifacts": {},
        "positive_count": 20,
        "structure_count": 80,
        "route_count": 20,
        "counts_toward_300": 0,
    }
    pending_payloads = {
        BLIND_PACKET_PATH: blind_payload,
        BLIND_LABEL_PATH: label_payload,
        REVIEW_CONTRACT_PATH: contract_payload,
        **correction_documents,
    }
    packet["artifacts"] = {
        name: {
            "path": path.as_posix(),
            "sha256": (
                sha256_bytes(pending_payloads[path])
                if path in pending_payloads
                else sha256_file(root / path)
            ),
        }
        for name, path in artifacts.items()
    }
    packet["packet_digest"] = object_digest(packet, "packet_digest")
    return {
        **{path.as_posix(): payload for path, payload in correction_documents.items()},
        BLIND_PACKET_PATH.as_posix(): blind_payload,
        BLIND_LABEL_PATH.as_posix(): label_payload,
        REVIEW_CONTRACT_PATH.as_posix(): contract_payload,
        REVIEW_PACKET_PATH.as_posix(): yaml_bytes({"p3_review_packet": packet}),
    }


def materialize_review_packet(root: Path = ROOT) -> list[Path]:
    documents = build_review_documents(root)
    changed: list[Path] = []
    for relative, payload in documents.items():
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
    if grade not in {"A", "B"}:
        return False
    thresholds = load_yaml(ROOT / REVIEW_CONTRACT_PATH)["independent_review_contract"]["critical_minimums"][grade]
    merged = {**score["public_quality"], **score["product_quality"]}
    return all(int(merged[key]) >= int(value) for key, value in thresholds.items())


def validate_review_report(
    report: Mapping[str, Any], expected_role: str, root: Path = ROOT
) -> None:
    required = {
        "schema_version",
        "task_id",
        "review_id",
        "reviewer_identity",
        "reviewer_platform_agent_id",
        "reviewer_session_id",
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
    require(set(report) == required, "E_P3_REVIEW_FIELD_SET")
    require(report.get("schema_version") == "gate1-p3-independent-review-v0.1", "E_P3_REVIEW_SCHEMA")
    require(report.get("task_id") == TASK_ID, "E_P3_REVIEW_TASK")
    require(report.get("reviewer_role") == expected_role, "E_P3_REVIEW_ROLE")
    require(report.get("author_identity_excluded") is True, "E_P3_REVIEW_AUTHOR_COLLISION")
    require(report.get("executor_builder_finalizer_identity_excluded") is True, "E_P3_REVIEW_EXECUTOR_COLLISION")
    blind = report.get("blind_stage")
    require(isinstance(blind, Mapping), "E_P3_REVIEW_BLIND")
    blind_rows = load_jsonl(root / BLIND_PACKET_PATH)
    label_rows = load_jsonl(root / BLIND_LABEL_PATH)
    label_by_blind = {str(row["blind_id"]): row for row in label_rows}
    predictions = blind.get("predictions")
    require(isinstance(predictions, list) and len(predictions) == 20, "E_P3_REVIEW_PREDICTION_COUNT")
    require(blind.get("recorded_before_label_reveal") is True, "E_P3_REVIEW_BLIND_ORDER")
    require(blind.get("blind_packet_sha256") == sha256_file(root / BLIND_PACKET_PATH), "E_P3_REVIEW_BLIND_SHA")
    require({row["blind_id"] for row in predictions} == {row["blind_id"] for row in blind_rows}, "E_P3_REVIEW_BLIND_COVERAGE")
    for prediction in predictions:
        require(prediction["predicted_profile_id"] in VALID_PROFILES, "E_P3_REVIEW_BLIND_PROFILE")
        require(isinstance(prediction.get("reason"), str) and bool(prediction["reason"]), "E_P3_REVIEW_BLIND_REASON")
    expected_correct = sum(
        prediction["predicted_profile_id"] == label_by_blind[prediction["blind_id"]]["profile_id"]
        for prediction in predictions
    )
    require(blind.get("blind_stage_digest") == object_digest(dict(blind), "blind_stage_digest"), "E_P3_REVIEW_BLIND_DIGEST")
    coverage = report.get("coverage")
    require(
        coverage == {
            "structure_records_read": 80,
            "positive_outputs_read": 20,
            "route_results_read": 20,
            "machine_report_read": True,
            "failure_records_read": True,
        },
        "E_P3_REVIEW_COVERAGE",
    )
    scores = report.get("positive_scores")
    require(isinstance(scores, list) and len(scores) == 20, "E_P3_REVIEW_SCORE_COUNT")
    require({row["profile_id"] for row in scores} == VALID_PROFILES, "E_P3_REVIEW_SCORE_PROFILE_SET")
    score_by_profile = {str(row["profile_id"]): row for row in scores}
    outputs = {str(row["profile_id"]): row for row in load_jsonl(root / POSITIVE_OUTPUT_PATH)}
    accepted_count = 0
    for profile_id, score in score_by_profile.items():
        require(score.get("request_id") == outputs[profile_id]["request_id"], "E_P3_REVIEW_SCORE_REQUEST")
        require(set(score["public_quality"]) == set(PUBLIC_DIMENSIONS), "E_P3_REVIEW_PUBLIC_DIMENSIONS")
        require(set(score["product_quality"]) == set(PRODUCT_DIMENSIONS), "E_P3_REVIEW_PRODUCT_DIMENSIONS")
        for key, maximum in PUBLIC_DIMENSIONS.items():
            require(isinstance(score["public_quality"][key], int) and 0 <= score["public_quality"][key] <= maximum, "E_P3_REVIEW_PUBLIC_SCORE", key)
        for key, maximum in PRODUCT_DIMENSIONS.items():
            require(isinstance(score["product_quality"][key], int) and 0 <= score["product_quality"][key] <= maximum, "E_P3_REVIEW_PRODUCT_SCORE", key)
        total = sum(score["public_quality"].values()) + sum(score["product_quality"].values())
        grade = _grade(total)
        require(score.get("total_score") == total and score.get("grade") == grade, "E_P3_REVIEW_SCORE_TOTAL")
        minimum_pass = _critical_minimum_pass(score, grade)
        require(score.get("critical_minimum_pass") is minimum_pass, "E_P3_REVIEW_CRITICAL_MINIMUM")
        hard_vetoes = score.get("hard_vetoes")
        require(isinstance(hard_vetoes, list), "E_P3_REVIEW_HARD_VETOES")
        expected_acceptable = grade in {"A", "B"} and minimum_pass and not hard_vetoes
        require(score.get("first_acceptable") is expected_acceptable, "E_P3_REVIEW_FIRST_ACCEPTABLE")
        require(isinstance(score.get("evidence"), list) and bool(score["evidence"]), "E_P3_REVIEW_SCORE_EVIDENCE")
        require(isinstance(score.get("defects"), list), "E_P3_REVIEW_SCORE_DEFECTS")
        accepted_count += int(expected_acceptable)
    expected_average = round(sum(row["total_score"] for row in scores) / 20, 2)
    require(report.get("p3_score") == expected_average, "E_P3_REVIEW_AVERAGE")
    require(report.get("first_acceptable_count") == accepted_count, "E_P3_REVIEW_ACCEPTED_COUNT")
    require(report.get("first_acceptance_rate") == round(accepted_count / 20, 4), "E_P3_REVIEW_ACCEPTED_RATE")
    require(report.get("blind_top1_correct_count") == expected_correct, "E_P3_REVIEW_BLIND_CORRECT")
    require(report.get("blind_top1_accuracy") == round(expected_correct / 20, 4), "E_P3_REVIEW_BLIND_RATE")
    formula_ids = report.get("human_confirmed_formula_or_near_duplicate_profile_ids")
    require(isinstance(formula_ids, list) and set(formula_ids).issubset(VALID_PROFILES), "E_P3_REVIEW_FORMULA_IDS")
    require(report.get("human_confirmed_formula_or_near_duplicate_rate") == round(len(set(formula_ids)) / 20, 4), "E_P3_REVIEW_FORMULA_RATE")
    hard_ids = report.get("hard_error_profile_ids")
    require(isinstance(hard_ids, list) and set(hard_ids).issubset(VALID_PROFILES), "E_P3_REVIEW_HARD_IDS")
    pass_conditions = (
        accepted_count >= 18
        and expected_correct >= 17
        and len(set(formula_ids)) <= 2
        and not hard_ids
        and report.get("structure_hard_gate_pass") is True
        and report.get("route_hard_gate_pass") is True
    )
    require(report.get("overall_verdict") == ("PASS" if pass_conditions else "FAIL"), "E_P3_REVIEW_VERDICT")
    require(report.get("signed_record_digest") == object_digest(dict(report), "signed_record_digest"), "E_P3_REVIEW_DIGEST")


def load_and_validate_reports(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    import json

    review_one = json.loads((root / REVIEW_ONE_PATH).read_text(encoding="utf-8"))
    review_two = json.loads((root / REVIEW_TWO_PATH).read_text(encoding="utf-8"))
    validate_review_report(review_one, "CONTENT_PRODUCT_USER_VALUE_STRUCTURE_PLATFORM_ANTI_FORMULA", root)
    validate_review_report(review_two, "FACT_SOURCE_AUTHORIZATION_CLAIM_COMPONENT_ROUTE_SAFETY", root)
    identities = {
        review_one["reviewer_identity"],
        review_two["reviewer_identity"],
        review_one["reviewer_platform_agent_id"],
        review_two["reviewer_platform_agent_id"],
        review_one["reviewer_session_id"],
        review_two["reviewer_session_id"],
    }
    require(len(identities) == 6, "E_P3_REVIEW_IDENTITY_COLLISION")
    return review_one, review_two


def substantive_disagreements(
    review_one: Mapping[str, Any], review_two: Mapping[str, Any]
) -> list[dict[str, Any]]:
    first = {row["profile_id"]: row for row in review_one["positive_scores"]}
    second = {row["profile_id"]: row for row in review_two["positive_scores"]}
    rows: list[dict[str, Any]] = []
    for profile_id in sorted(VALID_PROFILES):
        reasons = []
        if first[profile_id]["first_acceptable"] != second[profile_id]["first_acceptable"]:
            reasons.append("FIRST_ACCEPTANCE_DISAGREEMENT")
        if set(first[profile_id]["hard_vetoes"]) != set(second[profile_id]["hard_vetoes"]):
            reasons.append("HARD_VETO_DISAGREEMENT")
        if reasons:
            rows.append({"profile_id": profile_id, "reasons": reasons})
    if review_one["structure_hard_gate_pass"] != review_two["structure_hard_gate_pass"]:
        rows.append({"profile_id": "STRUCTURE_GATE", "reasons": ["STRUCTURE_GATE_DISAGREEMENT"]})
    if review_one["route_hard_gate_pass"] != review_two["route_hard_gate_pass"]:
        rows.append({"profile_id": "ROUTE_GATE", "reasons": ["ROUTE_GATE_DISAGREEMENT"]})
    return rows


__all__ = [
    "ADJUDICATION_PATH",
    "BLIND_LABEL_PATH",
    "BLIND_PACKET_PATH",
    "REVIEW_CONTRACT_PATH",
    "REVIEW_ONE_PATH",
    "REVIEW_PACKET_PATH",
    "REVIEW_TWO_PATH",
    "build_review_documents",
    "load_and_validate_reports",
    "materialize_review_packet",
    "substantive_disagreements",
    "validate_review_report",
]
