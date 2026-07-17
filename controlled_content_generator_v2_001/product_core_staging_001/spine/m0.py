"""M0 固定键合取门、密封清单和报告证据闭包。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable

from .canonical import digest_json

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_MODULES = (
    "reference_assertion_extraction", "claim_atomization", "risk_classification",
    "entailment", "fact_chain_end_to_end", "formulaic_construct",
    "disclosure_and_omission", "review_calibration", "cost",
)

REQUIRED_REPORT_REFS = (
    "reference_assertion_extraction_report", "claim_atomization_report",
    "risk_classification_report", "entailment_report",
    "fact_chain_end_to_end_report", "formulaic_construct_report",
    "disclosure_and_omission_report", "reviewer_agreement_report", "cost_report",
    "immutable_qualification_manifest", "independent_adjudication_report",
    "audit_integrity_report",
)

MODULE_REPORT_REF = {
    "reference_assertion_extraction": "reference_assertion_extraction_report",
    "claim_atomization": "claim_atomization_report",
    "risk_classification": "risk_classification_report",
    "entailment": "entailment_report",
    "fact_chain_end_to_end": "fact_chain_end_to_end_report",
    "formulaic_construct": "formulaic_construct_report",
    "disclosure_and_omission": "disclosure_and_omission_report",
    "review_calibration": "reviewer_agreement_report",
    "cost": "cost_report",
}

MODULE_RECORD_ROLE_MINIMUMS = {
    "reference_assertion_extraction": {"qualification_case": 300},
    "claim_atomization": {"qualification_case": 300},
    "risk_classification": {"qualification_case": 600},
    "entailment": {"qualification_case": 700, "known_risk_regression": 5},
    "fact_chain_end_to_end": {"qualification_case": 600},
    "formulaic_construct": {
        "judgment": 600, "adjudication": 300, "candidate_audit": 200,
        "candidate_audit_manifest": 1, "rubric_registry": 1,
        "necessary_grammar_exception_registry": 1,
    },
    "disclosure_and_omission": {"disclosure_case": 100, "omission_case": 200},
    "review_calibration": {"judgment": 80},
    "cost": {"cost_event": 12, "expected_event_manifest": 1,
             "source_event_manifest": 1, "rate_card": 1},
}
MIN_RECORD_COUNTS = {
    module_id: sum(role_minimums.values())
    for module_id, role_minimums in MODULE_RECORD_ROLE_MINIMUMS.items()
}

MODULE_GATE_KEYS = {
    "reference_assertion_extraction": {
        "detection_qualification_evidence_bound", "detection_record_shape_valid",
        "detection_sample_count", "detection_positive_sample_count",
        "detection_negative_control_count", "detection_family_coverage",
        "detection_recall", "detection_precision",
        "detection_critical_omissions_zero", "attribute_annotations_complete",
        "polarity_correct_accuracy", "modality_correct_accuracy",
        "time_scope_correct_accuracy", "preconditions_correct_accuracy",
    },
    "claim_atomization": {
        "detection_qualification_evidence_bound", "detection_record_shape_valid",
        "detection_sample_count", "detection_positive_sample_count",
        "detection_negative_control_count", "detection_family_coverage",
        "detection_recall", "detection_precision",
        "detection_critical_omissions_zero", "merge_annotations_complete",
        "cross_surface_duplicate_annotations_complete", "incorrect_merge_rate",
    },
    "risk_classification": {
        "qualification_evidence_bound", "record_shape_valid", "family_coverage",
        "high_risk_sample",
        "legal_control_sample", "high_risk_downclassification_zero",
        "high_risk_downclassification_upper_below_one_percent", "overall_accuracy",
        "legal_false_high_upper_at_most_five_percent",
    },
    "entailment": {
        "qualification_evidence_bound", "record_shape_valid", "family_coverage",
        "contradicted_recall",
        "contradicted_precision", "supported_recall", "supported_precision",
        "unknown_recall", "unknown_precision", "abstention_annotations_complete",
        "high_risk_contradicted_sample",
        "high_risk_unknown_sample", "high_risk_auto_pass_fn_zero",
        "high_risk_upper_below_one_percent", "natural_legal_sample",
        "natural_false_hard_upper_at_most_five_percent", "unknown_never_auto_allow",
        "known_risk_regression_sample", "known_risk_regression_shape_valid",
        "known_risk_regression_unique", "known_risk_regression_manifest_bound",
        "known_risk_regression_recall_one",
        "joint_risk_downclass_and_unsafe_allow_zero",
    },
    "fact_chain_end_to_end": {
        "qualification_evidence_bound", "record_shape_valid", "family_coverage",
        "high_risk_unsafe_sample", "high_risk_unsafe_clear_zero",
        "high_risk_unsafe_upper_below_one_percent", "natural_legal_sample",
        "natural_false_hard_upper_at_most_five_percent",
        "chain_digest_closure_complete", "joint_risk_downclass_and_unsafe_allow_zero",
    },
    "formulaic_construct": {
        "rubric_frozen_before_qualification", "judgment_qualification_evidence_bound",
        "adjudication_qualification_evidence_bound",
        "candidate_audit_qualification_evidence_bound", "candidate_audit_shape_valid",
        "candidate_audit_manifest_valid", "candidate_audit_pairs_bound",
        "candidate_gold_matches_adjudication", "family_coverage",
        "review_coverage_valid", "reviewer_independence_valid",
        "registry_cross_binding", "fresh_pair_count", "adjudication_records_valid",
        "adjudication_covers_reviewed_pairs", "class_counts_valid",
        "class_counts_close_reviewed_denominator",
        "necessary_grammar_is_negative_subset", "positive_pair_count",
        "negative_pair_count", "necessary_grammar_pair_count",
        "candidate_miner_confirmed_sample", "candidate_miner_recall", "interpretable",
        "raw_agreement", "kappa", "positive_agreement", "negative_agreement",
        "adjudication_rate",
    },
    "disclosure_and_omission": {
        "disclosure_qualification_evidence_bound",
        "omission_qualification_evidence_bound", "disclosure_record_shape_valid",
        "omission_record_shape_valid", "family_coverage", "deterministic_disclosure_sample",
        "all_deterministic_obligation_types_present",
        "deterministic_disclosure_recall_one",
        "deterministic_disclosure_false_hard_zero", "omission_positive_sample",
        "omission_control_sample", "omission_recall", "omission_precision",
        "high_risk_omission_false_negative_zero",
        "high_risk_omission_fn_upper_at_most_three_percent",
        "joint_risk_downclass_and_omission_fn_zero",
    },
    "review_calibration": {
        "qualification_evidence_bound", "double_reviewed_item_count",
        "coverage_complete", "reviewer_provenance_complete", "role_collision_absent",
        "family_coverage", "distinct_reviewers_present", "two_decision_classes_present",
        "approval_decision_agreement", "approval_positive_specific_agreement",
        "approval_negative_specific_agreement", "hard_veto_cases_present",
        "hard_veto_agreement_one",
    },
    "cost": {
        "minimum_event_count", "event_contracts_valid", "critical_fields_available",
        "event_ids_unique", "provider_call_ids_unique",
        "expected_event_manifest_matches", "source_event_manifest_matches",
        "rate_card_valid",
        "costs_recompute_from_rate_card", "human_costs_recompute_from_rate_card",
        "all_events_complete",
    },
}

QUALIFICATION_CLASS_MINIMUMS = {
    "reference_extraction_positive": 100,
    "reference_extraction_negative": 100,
    "claim_atomization_positive": 100,
    "claim_atomization_negative": 100,
    "risk_high": 300,
    "risk_legal_control": 300,
    "entailment_high_risk_contradicted": 300,
    "entailment_high_risk_unknown": 100,
    "entailment_natural_supported": 300,
    "fact_chain_high_risk_unsafe": 300,
    "fact_chain_natural_legal": 300,
    "formulaic_total_pairs": 300,
    "formulaic_positive_pairs": 100,
    "formulaic_negative_pairs": 100,
    "formulaic_necessary_grammar_pairs": 20,
    "deterministic_disclosure_cases": 100,
    "omission_high_risk_misleading": 100,
    "omission_nonmisleading_controls": 100,
    "review_double_reviewed_items": 40,
    "cost_events": 12,
}

FROZEN_METHOD_PARAMETERS = {
    "reference_assertion_extraction": {
        "sample": 300, "positive": 100, "negative": 100,
        "recall": .95, "precision": .90, "attribute_accuracy": .95},
    "claim_atomization": {
        "sample": 300, "positive": 100, "negative": 100,
        "recall": .95, "precision": .90, "incorrect_merge_rate": .05},
    "risk_classification": {
        "high": 300, "legal": 300, "downclassification": 0,
        "downclassification_upper": .01, "accuracy": .95,
        "false_high_upper": .05},
    "entailment": {
        "high_contradicted": 300, "high_unknown": 100,
        "natural_supported": 300, "known_regression": 5,
        "contradicted_recall": .95, "contradicted_precision": .85,
        "unsafe_upper": .01, "false_hard_upper": .05},
    "fact_chain_end_to_end": {
        "high_unsafe": 300, "natural_legal": 300,
        "unsafe_upper": .01, "false_hard_upper": .05},
    "formulaic_construct": {
        "pairs": 300, "positive": 100, "negative": 100,
        "necessary_grammar": 20, "candidate_recall": .95,
        "raw_agreement": .90, "kappa": .60,
        "class_specific_agreement": .80, "adjudication_rate": .20},
    "disclosure_and_omission": {
        "deterministic_cases": 100, "omission_positive": 100,
        "omission_control": 100, "deterministic_recall": 1.0,
        "omission_recall": .95, "omission_precision": .85,
        "high_risk_fn_upper": .03},
    "review_calibration": {
        "double_reviewed_items": 40, "approval_agreement": .90,
        "class_specific_agreement": .80, "hard_veto_agreement": 1.0},
    "cost": {"complete_events": 12, "price_snapshot_max_age_days": 30},
}
METHOD_CONFIG_DIGESTS = {
    module_id: digest_json({
        "method_version": 1,
        "module_id": module_id,
        "gate_keys": sorted(MODULE_GATE_KEYS[module_id]),
        "parameters": FROZEN_METHOD_PARAMETERS[module_id],
    })
    for module_id in REQUIRED_MODULES
}


def _digest(value: Any) -> bool:
    return isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None


def build_record_manifest(*, module_id: str, records: Iterable[dict[str, Any]],
                          dataset_manifest_digest: str) -> dict[str, Any]:
    if module_id not in REQUIRED_MODULES or not _digest(dataset_manifest_digest):
        raise ValueError("invalid record manifest scope")
    entries = []
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError(f"invalid record object at {index}")
        raw_id = row.get("case_id") or row.get("event_id") or row.get("record_id")
        record_id = raw_id if isinstance(raw_id, str) else ""
        record_digest = row.get("case_digest") or row.get("event_digest")
        record_role = row.get("record_role")
        if (not record_id or not _digest(record_digest)
                or record_role not in MODULE_RECORD_ROLE_MINIMUMS[module_id]):
            raise ValueError(f"invalid record identity at {index}")
        entries.append({"record_id": record_id, "record_digest": record_digest,
                        "record_role": record_role})
    entries.sort(key=lambda row: (row["record_role"], row["record_id"]))
    role_counts = {role: sum(row["record_role"] == role for row in entries)
                   for role in MODULE_RECORD_ROLE_MINIMUMS[module_id]}
    if (len(entries) < MIN_RECORD_COUNTS[module_id]
            or len({row["record_id"] for row in entries}) != len(entries)
            or len({row["record_digest"] for row in entries}) != len(entries)
            or any(role_counts[role] < minimum for role, minimum
                   in MODULE_RECORD_ROLE_MINIMUMS[module_id].items())):
        raise ValueError("record manifest count or uniqueness failed")
    manifest: dict[str, Any] = {
        "schema_version": "eval-spine-m0-record-manifest-v1",
        "module_id": module_id, "visibility_partition": "HIDDEN",
        "dataset_manifest_digest": dataset_manifest_digest,
        "record_count": len(entries), "record_role_counts": role_counts,
        "entries": entries,
        "record_manifest_digest": "",
    }
    unsigned = dict(manifest)
    unsigned.pop("record_manifest_digest")
    manifest["record_manifest_digest"] = digest_json(unsigned)
    return manifest


def verify_record_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    module_id = manifest.get("module_id")
    entries = manifest.get("entries")
    required = {"schema_version", "module_id", "visibility_partition",
                "dataset_manifest_digest", "record_count", "record_role_counts", "entries",
                "record_manifest_digest"}
    if set(manifest) != required:
        errors.append("record_manifest_field_set")
    if manifest.get("schema_version") != "eval-spine-m0-record-manifest-v1":
        errors.append("record_manifest_schema")
    if module_id not in REQUIRED_MODULES:
        errors.append("record_manifest_module")
    if manifest.get("visibility_partition") != "HIDDEN":
        errors.append("record_manifest_partition")
    if not _digest(manifest.get("dataset_manifest_digest")):
        errors.append("record_manifest_dataset_digest")
    if not isinstance(entries, list):
        entries = []
        errors.append("record_manifest_entries")
    valid_entries = [row for row in entries if isinstance(row, dict)
                     and set(row) == {"record_id", "record_digest", "record_role"}]
    ids = [row.get("record_id") for row in valid_entries]
    digests = [row.get("record_digest") for row in valid_entries]
    roles = [row.get("record_role") for row in valid_entries]
    if (len(valid_entries) != len(entries)
            or not all(isinstance(value, str) and value for value in ids)
            or not all(_digest(v) for v in digests)
            or len(set(ids)) != len(ids) or len(set(digests)) != len(digests)):
        errors.append("record_manifest_entry_integrity")
    expected_roles = MODULE_RECORD_ROLE_MINIMUMS.get(module_id, {})
    computed_role_counts = {role: roles.count(role) for role in expected_roles}
    if (set(roles) - set(expected_roles)
            or manifest.get("record_role_counts") != computed_role_counts
            or any(computed_role_counts.get(role, 0) < minimum
                   for role, minimum in expected_roles.items())):
        errors.append("record_manifest_role_coverage")
    if (not isinstance(manifest.get("record_count"), int)
            or manifest.get("record_count") != len(entries)
            or module_id in MIN_RECORD_COUNTS
            and len(entries) < MIN_RECORD_COUNTS[module_id]):
        errors.append("record_manifest_count")
    unsigned = dict(manifest)
    supplied = unsigned.pop("record_manifest_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("record_manifest_digest")
    return sorted(set(errors))


def _verify_module_result(module_id: str, result: Any) -> list[str]:
    if not isinstance(result, dict) or not {"qualified", "gates"}.issubset(result):
        return ["module_result_shape"]
    gates = result.get("gates")
    errors: list[str] = []
    if not isinstance(gates, dict) or set(gates) != MODULE_GATE_KEYS[module_id]:
        errors.append("module_gate_key_set")
    elif any(value is not True and value is not False for value in gates.values()):
        errors.append("module_gate_value_type")
    elif result.get("qualified") is not all(gates.values()):
        errors.append("module_qualified_not_derived")
    return errors


def close_module_report(*, module_id: str, result: dict[str, Any],
                        dataset_manifest_digest: str,
                        record_manifest: dict[str, Any], method_version: int,
                        evaluator_revision_digest: str,
                        execution_receipt_digest: str) -> dict[str, Any]:
    result_errors = _verify_module_result(module_id, result) if module_id in REQUIRED_MODULES else ["module"]
    record_errors = verify_record_manifest(record_manifest)
    if (result_errors or record_errors
            or record_manifest.get("module_id") != module_id
            or record_manifest.get("dataset_manifest_digest") != dataset_manifest_digest
            or method_version != 1
            or not _digest(evaluator_revision_digest)
            or not _digest(execution_receipt_digest)):
        raise ValueError("invalid M0 module report inputs")
    report: dict[str, Any] = {
        "schema_version": "eval-spine-m0-module-report-v1",
        "module_id": module_id, "method_version": method_version,
        "visibility_partition": "HIDDEN",
        "dataset_manifest_digest": dataset_manifest_digest,
        "record_manifest_digest": record_manifest["record_manifest_digest"],
        "method_config_digest": METHOD_CONFIG_DIGESTS[module_id],
        "evaluator_revision_digest": evaluator_revision_digest,
        "execution_receipt_digest": execution_receipt_digest,
        "qualified": result["qualified"], "result": result,
        "result_digest": digest_json(result), "report_digest": "",
    }
    unsigned = dict(report)
    unsigned.pop("report_digest")
    report["report_digest"] = digest_json(unsigned)
    return report


def verify_module_report(report: dict[str, Any]) -> list[str]:
    required = {"schema_version", "module_id", "method_version", "visibility_partition",
                "dataset_manifest_digest", "record_manifest_digest", "method_config_digest",
                "evaluator_revision_digest", "execution_receipt_digest", "qualified", "result",
                "result_digest",
                "report_digest"}
    errors: list[str] = []
    module_id = report.get("module_id")
    if set(report) != required:
        errors.append("module_report_field_set")
    if report.get("schema_version") != "eval-spine-m0-module-report-v1":
        errors.append("module_report_schema")
    if module_id not in REQUIRED_MODULES:
        errors.append("module_report_unknown_module")
    else:
        errors.extend(_verify_module_result(module_id, report.get("result")))
    if report.get("method_version") != 1:
        errors.append("module_report_method_version")
    if report.get("visibility_partition") != "HIDDEN":
        errors.append("module_report_partition")
    for field in ("dataset_manifest_digest", "record_manifest_digest",
                  "method_config_digest", "evaluator_revision_digest",
                  "execution_receipt_digest", "result_digest", "report_digest"):
        if not _digest(report.get(field)):
            errors.append(f"module_report_digest:{field}")
    if isinstance(report.get("result"), dict):
        if report.get("qualified") is not report["result"].get("qualified"):
            errors.append("module_report_qualified_mismatch")
        if report.get("result_digest") != digest_json(report["result"]):
            errors.append("module_report_result_digest_mismatch")
    if module_id in METHOD_CONFIG_DIGESTS and report.get(
            "method_config_digest") != METHOD_CONFIG_DIGESTS[module_id]:
        errors.append("module_report_method_config_mismatch")
    unsigned = dict(report)
    supplied = unsigned.pop("report_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("module_report_digest_mismatch")
    return sorted(set(errors))


def verify_qualification_manifest(manifest: dict[str, Any] | None) -> list[str]:
    if not isinstance(manifest, dict):
        return ["qualification_manifest_missing"]
    required = {"schema_version", "manifest_id", "data_grid", "content_status", "sealed",
                "case_count", "class_counts", "dataset_manifest_digest",
                "source_manifest_digest",
                "gold_manifest_digest", "allowed_consumers", "prohibited_consumers",
                "record_manifest_digests", "qualification_record_index_digest",
                "leakage_status", "notes", "manifest_digest"}
    errors: list[str] = []
    if set(manifest) != required:
        errors.append("qualification_manifest_field_set")
    if (manifest.get("schema_version") != "eval-spine-calibration-manifest-v1"
            or manifest.get("data_grid") != "G3_MEASUREMENT_QUALIFICATION"
            or manifest.get("content_status") != "ADJUDICATED"
            or manifest.get("sealed") is not True
            or manifest.get("leakage_status") != "PASS"):
        errors.append("qualification_manifest_state")
    if not isinstance(manifest.get("case_count"), int) or manifest.get("case_count", 0) < 700:
        errors.append("qualification_manifest_case_count")
    counts = manifest.get("class_counts")
    if not isinstance(counts, dict) or any(
            not isinstance(counts.get(key), int) or counts[key] < minimum
            for key, minimum in QUALIFICATION_CLASS_MINIMUMS.items()):
        errors.append("qualification_manifest_class_minimums")
    record_digests = manifest.get("record_manifest_digests")
    if (not isinstance(record_digests, dict)
            or set(record_digests) != set(REQUIRED_MODULES)
            or not all(_digest(value) for value in record_digests.values())):
        errors.append("qualification_manifest_record_manifests")
    allowed = manifest.get("allowed_consumers")
    prohibited = manifest.get("prohibited_consumers")
    required_allowed = {"INDEPENDENT_AUDITOR", "QUALIFICATION_ADJUDICATOR",
                        "QUALIFICATION_REVIEWER_A", "QUALIFICATION_REVIEWER_B",
                        "QUALIFICATION_RUNNER", "SEALED_DATA_CUSTODIAN"}
    required_prohibited = {"EVALUATOR_DEVELOPER", "GENERATOR_AUTHOR",
                           "GENERATOR_DEVELOPER", "RUBRIC_DEVELOPER"}
    if (not isinstance(allowed, list) or not isinstance(prohibited, list)
            or not all(isinstance(value, str) for value in allowed + prohibited)
            or not required_allowed.issubset(allowed)
            or not required_prohibited.issubset(prohibited)
            or set(allowed) & set(prohibited)):
        errors.append("qualification_manifest_access_policy")
    for field in ("dataset_manifest_digest", "source_manifest_digest",
                  "gold_manifest_digest", "manifest_digest"):
        if not _digest(manifest.get(field)):
            errors.append(f"qualification_manifest_digest:{field}")
    if not _digest(manifest.get("qualification_record_index_digest")):
        errors.append("qualification_manifest_record_index_digest")
    unsigned = dict(manifest)
    supplied = unsigned.pop("manifest_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("qualification_manifest_digest_mismatch")
    return sorted(set(errors))


INDEPENDENT_ADJUDICATION_GATES = {
    "sealed_gold_integrity", "record_manifest_integrity",
    "module_report_integrity", "module_metrics_recomputed",
    "dataset_binding_integrity", "leakage_check_pass",
}
AUDIT_INTEGRITY_GATES = {
    "public_manifest_schema_valid", "source_group_isolation_pass",
    "hidden_payload_leakage_absent", "artifact_digest_closure_pass",
}


def verify_audit_integrity_report(report: dict[str, Any] | None, *,
                                  dataset_manifest_digest: str | None) -> list[str]:
    if not isinstance(report, dict):
        return ["audit_integrity_report_missing"]
    required = {"schema_version", "report_id", "dataset_manifest_digest",
                "visibility_partition", "gate_verdicts", "evidence_manifest_digest",
                "executed_by", "executed_at", "report_digest"}
    errors: list[str] = []
    gates = report.get("gate_verdicts")
    if set(report) != required:
        errors.append("audit_integrity_field_set")
    if (report.get("schema_version") != "eval-spine-audit-integrity-report-v1"
            or report.get("visibility_partition") != "HIDDEN"
            or not str(report.get("report_id", "")).strip()
            or not str(report.get("executed_by", "")).strip()
            or not isinstance(gates, dict) or set(gates) != AUDIT_INTEGRITY_GATES
            or not all(value is True for value in gates.values())
            or not _digest(report.get("evidence_manifest_digest"))):
        errors.append("audit_integrity_state")
    if report.get("dataset_manifest_digest") != dataset_manifest_digest:
        errors.append("audit_integrity_dataset_mismatch")
    try:
        parsed = datetime.fromisoformat(
            str(report.get("executed_at", "")).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
    except ValueError:
        errors.append("audit_integrity_timestamp")
    unsigned = dict(report)
    supplied = unsigned.pop("report_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("audit_integrity_digest")
    return sorted(set(errors))


def verify_independent_adjudication_report(report: dict[str, Any] | None,
                                           *, qualification_manifest_digest: str | None,
                                           module_report_digests: dict[str, str],
                                           record_manifest_digests: dict[str, str],
                                           module_result_digests: dict[str, str],
                                           audit_integrity_report_digest: str | None) -> list[str]:
    if not isinstance(report, dict):
        return ["independent_adjudication_missing"]
    required = {"schema_version", "report_id", "reviewer_identity", "reviewer_provenance",
                "independence_attestation", "qualification_manifest_digest",
                "module_report_digests", "record_manifest_digests", "gate_verdicts",
                "recomputed_module_result_digests", "gate_evidence_digests",
                "review_assignment_digest", "reviewer_separation_digest",
                "audit_integrity_report_digest", "open_finding_count", "status",
                "reviewed_at", "report_digest"}
    errors: list[str] = []
    if set(report) != required:
        errors.append("independent_adjudication_field_set")
    attestation = report.get("independence_attestation")
    expected_attestation = {"did_not_build_gold", "did_not_develop_evaluator",
                            "did_not_develop_generator", "did_not_author_module_reports"}
    provenance = report.get("reviewer_provenance")
    provenance_valid = (isinstance(provenance, dict)
                        and set(provenance) == {"reviewer_kind", "model_revision",
                                               "prompt_digest"}
                        and provenance.get("reviewer_kind") in {"HUMAN", "AI"})
    if provenance_valid and provenance.get("reviewer_kind") == "AI":
        provenance_valid = (bool(str(provenance.get("model_revision") or "").strip())
                            and _digest(provenance.get("prompt_digest")))
    elif provenance_valid:
        provenance_valid = (provenance.get("model_revision") is None
                            and provenance.get("prompt_digest") is None)
    gates = report.get("gate_verdicts")
    gate_evidence = report.get("gate_evidence_digests")
    if (report.get("schema_version") != "eval-spine-m0-independent-adjudication-v1"
            or report.get("status") != "PASS"
            or not str(report.get("reviewer_identity", "")).strip()
            or not provenance_valid
            or not isinstance(attestation, dict) or set(attestation) != expected_attestation
            or not all(value is True for value in attestation.values())
            or not isinstance(gates, dict) or set(gates) != INDEPENDENT_ADJUDICATION_GATES
            or not all(value is True for value in gates.values())
            or not isinstance(gate_evidence, dict)
            or set(gate_evidence) != INDEPENDENT_ADJUDICATION_GATES
            or not all(_digest(value) for value in gate_evidence.values())
            or not _digest(report.get("review_assignment_digest"))
            or not _digest(report.get("reviewer_separation_digest"))
            or report.get("open_finding_count") != 0):
        errors.append("independent_adjudication_state")
    try:
        reviewed_at = datetime.fromisoformat(
            str(report.get("reviewed_at", "")).replace("Z", "+00:00"))
        if reviewed_at.tzinfo is None:
            raise ValueError
    except ValueError:
        errors.append("independent_adjudication_timestamp")
    if report.get("qualification_manifest_digest") != qualification_manifest_digest:
        errors.append("independent_adjudication_manifest_mismatch")
    if report.get("module_report_digests") != dict(sorted(module_report_digests.items())):
        errors.append("independent_adjudication_module_mismatch")
    if report.get("record_manifest_digests") != dict(sorted(record_manifest_digests.items())):
        errors.append("independent_adjudication_record_mismatch")
    if report.get("recomputed_module_result_digests") != dict(
            sorted(module_result_digests.items())):
        errors.append("independent_adjudication_recompute_mismatch")
    if report.get("audit_integrity_report_digest") != audit_integrity_report_digest:
        errors.append("independent_adjudication_audit_mismatch")
    unsigned = dict(report)
    supplied = unsigned.pop("report_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("independent_adjudication_digest")
    return sorted(set(errors))


def build_m0_decision(
        module_reports: Iterable[dict[str, Any]], *,
        record_manifests: Iterable[dict[str, Any]],
        required_report_refs: dict[str, str] | None,
        qualification_manifest: dict[str, Any] | None,
        independent_adjudication_report: dict[str, Any] | None,
        audit_integrity_report: dict[str, Any] | None) -> dict[str, Any]:
    """固定键合取；缺模块、混清单、自报布尔或未裁决清单永不 PASS。"""
    reports = list(module_reports)
    manifests = list(record_manifests)
    by_module: dict[str, dict[str, Any]] = {}
    record_by_module: dict[str, dict[str, Any]] = {}
    duplicate_modules: list[str] = []
    unknown_modules: list[str] = []
    invalid_reports: dict[str, list[str]] = {}
    invalid_record_manifests: dict[str, list[str]] = {}
    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            invalid_reports[f"row-{index}"] = ["module_report_not_object"]
            continue
        module_id = str(report.get("module_id", ""))
        if module_id not in REQUIRED_MODULES:
            unknown_modules.append(module_id or f"row-{index}")
        elif module_id in by_module:
            duplicate_modules.append(module_id)
        else:
            by_module[module_id] = report
            errors = verify_module_report(report)
            if errors:
                invalid_reports[module_id] = errors
    for index, manifest in enumerate(manifests):
        if not isinstance(manifest, dict):
            invalid_record_manifests[f"row-{index}"] = ["record_manifest_not_object"]
            continue
        module_id = str(manifest.get("module_id", ""))
        if module_id not in REQUIRED_MODULES or module_id in record_by_module:
            invalid_record_manifests[module_id or f"row-{index}"] = [
                "unknown_or_duplicate_record_manifest"]
        else:
            record_by_module[module_id] = manifest
            errors = verify_record_manifest(manifest)
            if errors:
                invalid_record_manifests[module_id] = errors
    missing_modules = sorted(set(REQUIRED_MODULES) - set(by_module))
    missing_record_manifests = sorted(set(REQUIRED_MODULES) - set(record_by_module))
    manifest_errors = verify_qualification_manifest(qualification_manifest)
    safe_qualification = qualification_manifest if isinstance(
        qualification_manifest, dict) else {}
    qualification_digest = safe_qualification.get("manifest_digest")
    qualification_dataset_digest = safe_qualification.get(
        "dataset_manifest_digest")
    module_digests = {module_id: str(report.get("report_digest", ""))
                      for module_id, report in sorted(by_module.items())}
    module_result_digests = {module_id: str(report.get("result_digest", ""))
                             for module_id, report in sorted(by_module.items())}
    record_manifest_digests = {
        module_id: str(manifest.get("record_manifest_digest", ""))
        for module_id, manifest in sorted(record_by_module.items())}
    audit_integrity_errors = verify_audit_integrity_report(
        audit_integrity_report,
        dataset_manifest_digest=qualification_dataset_digest)
    audit_integrity_digest = ((audit_integrity_report or {}).get("report_digest")
                              if isinstance(audit_integrity_report, dict) else None)
    adjudication_errors = verify_independent_adjudication_report(
        independent_adjudication_report,
        qualification_manifest_digest=qualification_digest,
        module_report_digests=module_digests,
        record_manifest_digests=record_manifest_digests,
        module_result_digests=module_result_digests,
        audit_integrity_report_digest=audit_integrity_digest)
    refs = required_report_refs if isinstance(required_report_refs, dict) else {}
    missing_refs = sorted(name for name in REQUIRED_REPORT_REFS if not _digest(refs.get(name)))
    unknown_refs = sorted(set(refs) - set(REQUIRED_REPORT_REFS))
    unbound_module_refs = sorted(module_id for module_id, report in by_module.items()
                                 if refs.get(MODULE_REPORT_REF[module_id])
                                 != report.get("report_digest"))
    record_binding_errors = sorted(module_id for module_id in set(by_module) & set(record_by_module)
                                   if by_module[module_id].get("record_manifest_digest")
                                   != record_by_module[module_id].get("record_manifest_digest"))
    qualification_record_binding_errors = sorted(
        module_id for module_id, digest in record_manifest_digests.items()
        if not isinstance(qualification_manifest, dict)
        or qualification_manifest.get("record_manifest_digests", {}).get(module_id) != digest)
    dataset_binding_errors = sorted(
        module_id for module_id in set(by_module) | set(record_by_module)
        if module_id not in by_module or module_id not in record_by_module
        or by_module[module_id].get("dataset_manifest_digest")
        != qualification_dataset_digest
        or record_by_module[module_id].get("dataset_manifest_digest")
        != qualification_dataset_digest
        or by_module[module_id].get("dataset_manifest_digest")
        != record_by_module[module_id].get("dataset_manifest_digest"))
    method_versions = {report.get("method_version") for report in by_module.values()}
    method_version_consistent = method_versions == {1}
    manifest_ref_matches = refs.get("immutable_qualification_manifest") == qualification_digest
    adjudication_ref_matches = (isinstance(independent_adjudication_report, dict)
                                and refs.get("independent_adjudication_report")
                                == independent_adjudication_report.get("report_digest"))
    audit_integrity_ref_matches = (isinstance(audit_integrity_report, dict)
                                   and refs.get("audit_integrity_report")
                                   == audit_integrity_digest)
    module_failures = sorted(module_id for module_id, report in by_module.items()
                             if report.get("qualified") is False)
    gates = {
        "fixed_module_set_complete": not missing_modules and not unknown_modules
                                     and not duplicate_modules,
        "module_reports_valid": not invalid_reports,
        "record_manifests_complete_and_valid": not missing_record_manifests
                                               and not invalid_record_manifests,
        "record_manifests_bound": not record_binding_errors,
        "qualification_manifest_binds_record_manifests":
            not qualification_record_binding_errors and not missing_record_manifests,
        "single_hidden_dataset_bound": not dataset_binding_errors and not manifest_errors,
        "single_method_version": method_version_consistent,
        "all_modules_qualified": len(by_module) == len(REQUIRED_MODULES)
                                 and not module_failures,
        "required_report_refs_complete": not missing_refs and not unknown_refs,
        "module_report_refs_bound": not unbound_module_refs,
        "qualification_manifest_ref_matches": manifest_ref_matches,
        "independent_adjudication_valid": not adjudication_errors,
        "independent_adjudication_ref_matches": adjudication_ref_matches,
        "audit_integrity_valid": not audit_integrity_errors,
        "audit_integrity_ref_matches": audit_integrity_ref_matches,
    }
    explicit_failure = any((invalid_reports, invalid_record_manifests,
                            manifest_errors if qualification_manifest is not None else [],
                            adjudication_errors
                            if independent_adjudication_report is not None else [],
                            audit_integrity_errors
                            if audit_integrity_report is not None else [],
                            record_binding_errors,
                            qualification_record_binding_errors,
                            dataset_binding_errors, module_failures, unknown_refs,
                            unbound_module_refs))
    status = "PASS" if all(gates.values()) else "FAIL" if explicit_failure else "BLOCKED"
    reasons = [key.upper() for key, passed in gates.items() if not passed]
    decision: dict[str, Any] = {
        "schema_version": "eval-spine-m0-decision-v1", "status": status,
        "gates": gates, "reason_codes": sorted(reasons),
        "module_report_digests": module_digests,
        "record_manifest_digests": record_manifest_digests,
        "required_report_refs": {key: refs[key] for key in sorted(refs)},
        "qualification_manifest_digest": qualification_digest,
        "independent_adjudication_report_digest": (
            independent_adjudication_report.get("report_digest")
            if isinstance(independent_adjudication_report, dict) else None),
        "audit_integrity_report_digest": audit_integrity_digest,
        "method_version": next(iter(method_versions)) if method_version_consistent else None,
        "missing_module_ids": missing_modules,
        "unknown_module_ids": sorted(unknown_modules),
        "duplicate_module_ids": sorted(duplicate_modules),
        "invalid_module_reports": invalid_reports,
        "invalid_record_manifests": invalid_record_manifests,
        "independent_adjudication_errors": adjudication_errors,
        "audit_integrity_errors": audit_integrity_errors,
        "unbound_record_manifest_ids": qualification_record_binding_errors,
        "failed_module_ids": module_failures,
        "missing_required_report_refs": missing_refs,
        "unknown_report_refs": unknown_refs,
        "unbound_module_report_ids": unbound_module_refs,
        "claims_allowed": (["M0_MEASUREMENT_QUALIFIED"] if status == "PASS"
                           else ["M0_MEASUREMENT_NOT_QUALIFIED"]),
        "claims_forbidden": ([] if status == "PASS" else [
            "TRUSTED_EVALUATION", "READY_FOR_GENERATOR_SCALE", "READY_FOR_300"]),
        "decision_digest": "",
    }
    unsigned = dict(decision)
    unsigned.pop("decision_digest")
    decision["decision_digest"] = digest_json(unsigned)
    return decision


def verify_m0_decision(
        decision: dict[str, Any], *, module_reports: Iterable[dict[str, Any]],
        record_manifests: Iterable[dict[str, Any]],
        required_report_refs: dict[str, str] | None,
        qualification_manifest: dict[str, Any] | None,
        independent_adjudication_report: dict[str, Any] | None,
        audit_integrity_report: dict[str, Any] | None) -> list[str]:
    """M0 决定不是可自报状态；必须与同一组输入重算结果逐字节等价。"""
    if not isinstance(decision, dict):
        return ["m0_decision_not_object"]
    expected = build_m0_decision(
        module_reports, record_manifests=record_manifests,
        required_report_refs=required_report_refs,
        qualification_manifest=qualification_manifest,
        independent_adjudication_report=independent_adjudication_report,
        audit_integrity_report=audit_integrity_report)
    errors: list[str] = []
    if decision != expected:
        errors.append("m0_decision_not_recomputed")
    unsigned = dict(decision)
    supplied = unsigned.pop("decision_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("m0_decision_digest")
    return errors
