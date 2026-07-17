"""证据索引与人工裁决参考断言的确定性检查。"""

from __future__ import annotations

import re
from typing import Any, Iterable

from .canonical import digest_json, digest_text, stable_id
from .contracts import ContractError, require_fields


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REFERENCE_REVIEW_FIELDS = {
    "schema_version", "review_id", "assertion_id", "assertion_object_digest",
    "evidence_unit_ids", "evidence_set_digest", "reviewer_identity",
    "reviewer_kind", "model_revision", "prompt_digest", "reviewer_role",
    "decision", "evidence_digest", "review_digest",
}


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None


def _reference_review_evidence_set_digest(row: dict[str, Any]) -> str:
    raw_evidence_ids = row.get("evidence_unit_ids")
    evidence_ids = raw_evidence_ids if isinstance(raw_evidence_ids, list) else []
    return digest_json({
        "assertion_id": row.get("assertion_id"),
        "assertion_object_digest": row.get("object_digest"),
        "evidence_unit_ids": sorted(set(map(str, evidence_ids))),
    })


def _evidence_record_manifest_digest(
        assertion: dict[str, Any],
        evidence_units_by_id: dict[str, dict[str, Any]] | None) -> str:
    evidence_ids = assertion.get("evidence_unit_ids")
    if not isinstance(evidence_ids, list):
        evidence_ids = []
    records = evidence_units_by_id or {}
    return digest_json([
        {"evidence_unit_id": evidence_id,
         "object_digest": (records.get(str(evidence_id)) or {}).get(
             "object_digest")}
        for evidence_id in sorted(set(map(str, evidence_ids)))
    ])


def _validate_reference_review_record(
        review_id: str, review: Any, assertion: dict[str, Any],
        evidence_units_by_id: dict[str, dict[str, Any]] | None) -> list[str]:
    """验证审查记录自身以及它对断言和证据集合的闭包。"""
    assertion_id = str(assertion.get("assertion_id", ""))
    label = f"{assertion_id}:{review_id}"
    if not isinstance(review, dict):
        return [f"review_record_not_object:{label}"]
    errors: list[str] = []
    if set(review) != REFERENCE_REVIEW_FIELDS:
        errors.append(f"review_record_field_set_mismatch:{label}")
    if review.get("schema_version") != "eval-spine-reference-assertion-review-v1":
        errors.append(f"review_record_schema_version:{label}")
    if not review_id or review.get("review_id") != review_id:
        errors.append(f"review_record_key_mismatch:{label}")
    if review.get("assertion_id") != assertion_id:
        errors.append(f"review_assertion_binding_mismatch:{label}")
    if (not _is_digest(review.get("assertion_object_digest"))
            or review.get("assertion_object_digest") != assertion.get("object_digest")):
        errors.append(f"review_assertion_digest_mismatch:{label}")

    evidence_ids = review.get("evidence_unit_ids")
    assertion_evidence_ids = assertion.get("evidence_unit_ids")
    if (not isinstance(evidence_ids, list)
            or any(not isinstance(value, str) or not value for value in evidence_ids)
            or len(evidence_ids) != len(set(evidence_ids))):
        errors.append(f"review_evidence_ids_invalid:{label}")
    elif (not isinstance(assertion_evidence_ids, list)
          or set(evidence_ids) != set(map(str, assertion_evidence_ids))):
        errors.append(f"review_evidence_binding_mismatch:{label}")
    if (not _is_digest(review.get("evidence_set_digest"))
            or review.get("evidence_set_digest")
            != _reference_review_evidence_set_digest(assertion)):
        errors.append(f"review_evidence_set_digest_mismatch:{label}")

    identity = review.get("reviewer_identity")
    kind = review.get("reviewer_kind")
    if (not isinstance(identity, str) or not identity.strip()
            or identity != identity.strip()):
        errors.append(f"reviewer_identity_invalid:{label}")
    if kind not in {"HUMAN", "AI"}:
        errors.append(f"reviewer_kind_invalid:{label}")
    elif kind == "AI":
        if (not isinstance(review.get("model_revision"), str)
                or not review["model_revision"].strip()
                or not _is_digest(review.get("prompt_digest"))):
            errors.append(f"ai_reviewer_provenance_invalid:{label}")
    elif review.get("model_revision") is not None or review.get("prompt_digest") is not None:
        errors.append(f"human_reviewer_provenance_invalid:{label}")
    if review.get("reviewer_role") not in {"REVIEWER", "ADJUDICATOR"}:
        errors.append(f"reviewer_role_invalid:{label}")
    if review.get("decision") not in {"CONFIRM", "REJECT"}:
        errors.append(f"review_decision_invalid:{label}")
    if (not _is_digest(review.get("evidence_digest"))
            or review.get("evidence_digest") != _evidence_record_manifest_digest(
                assertion, evidence_units_by_id)):
        errors.append(f"review_evidence_digest_mismatch:{label}")
    unsigned = dict(review)
    supplied = unsigned.pop("review_digest", None)
    if not _is_digest(supplied) or supplied != digest_json(unsigned):
        errors.append(f"review_digest_mismatch:{label}")
    return errors


def _validate_reference_review_outcome(
        assertion: dict[str, Any], reviews: list[dict[str, Any]]) -> list[str]:
    """把 DUAL_ADJUDICATED 操作化为双同意或分歧后的独立裁决。"""
    assertion_id = str(assertion.get("assertion_id", ""))
    status = assertion.get("verification_status")
    primary = [row for row in reviews if row.get("reviewer_role") == "REVIEWER"]
    adjudicators = [row for row in reviews if row.get("reviewer_role") == "ADJUDICATOR"]
    identities = [str(row.get("reviewer_identity", "")).strip().casefold()
                  for row in reviews]
    errors: list[str] = []
    if len(identities) != len(set(identities)):
        errors.append(f"independent_reviewer_identity_unproven:{assertion_id}")

    if status == "PROPOSED":
        if reviews:
            errors.append(f"proposed_assertion_must_not_claim_reviews:{assertion_id}")
        return errors
    if status == "SINGLE_REVIEWED":
        if (len(primary) != 1 or adjudicators
                or primary[0].get("decision") != "CONFIRM"):
            errors.append(f"single_review_outcome_invalid:{assertion_id}")
        return errors
    if status == "DUAL_ADJUDICATED":
        if len(primary) != 2:
            errors.append(f"dual_primary_review_count_invalid:{assertion_id}")
            return errors
        decisions = [row.get("decision") for row in primary]
        if decisions == ["CONFIRM", "CONFIRM"]:
            if adjudicators:
                errors.append(f"unnecessary_adjudicator:{assertion_id}")
        elif set(decisions) == {"CONFIRM", "REJECT"}:
            if (len(adjudicators) != 1
                    or adjudicators[0].get("decision") != "CONFIRM"):
                errors.append(f"disagreement_requires_confirming_adjudicator:{assertion_id}")
        else:
            errors.append(f"dual_adjudicated_not_confirmed:{assertion_id}")
        return errors
    if status == "REJECTED":
        decisions = [row.get("decision") for row in primary]
        if len(primary) == 1 and decisions == ["REJECT"] and not adjudicators:
            return errors
        if len(primary) == 2 and decisions == ["REJECT", "REJECT"] and not adjudicators:
            return errors
        if (len(primary) == 2 and set(decisions) == {"CONFIRM", "REJECT"}
                and len(adjudicators) == 1
                and adjudicators[0].get("decision") == "REJECT"):
            return errors
        errors.append(f"rejected_outcome_invalid:{assertion_id}")
    return errors


def make_source_evidence_unit(source_id: str, source_text: str, byte_start: int,
                              byte_end: int, *, authorization_ids: list[str],
                              synthetic_test_only: bool = False) -> dict[str, Any]:
    source_bytes = source_text.encode("utf-8")
    if not (0 <= byte_start < byte_end <= len(source_bytes)):
        raise ContractError("invalid evidence span")
    try:
        quote = source_bytes[byte_start:byte_end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("evidence span must align to UTF-8 boundaries") from exc
    unit = {
        "schema_version": "eval-spine-source-evidence-unit-v1",
        "evidence_unit_id": stable_id("EV", source_id, byte_start, byte_end, quote),
        "source_id": source_id,
        "source_digest": digest_text(source_text),
        "byte_start": byte_start,
        "byte_end": byte_end,
        "text": quote,
        "authorization_ids": sorted(set(authorization_ids)),
        "synthetic_test_only": synthetic_test_only,
        "object_digest": "",
    }
    unsigned = dict(unit)
    unsigned.pop("object_digest")
    unit["object_digest"] = digest_json(unsigned)
    return unit


def verify_source_evidence_unit(unit: dict[str, Any], source_text: str) -> list[str]:
    errors: list[str] = []
    required = {"schema_version", "evidence_unit_id", "source_id", "source_digest",
                "byte_start", "byte_end", "text", "authorization_ids",
                "synthetic_test_only", "object_digest"}
    try:
        require_fields(unit, required, "evidence unit")
    except ContractError as exc:
        return [str(exc)]
    if set(unit) != required:
        errors.append("evidence_unit_field_set_mismatch")
    if unit.get("schema_version") != "eval-spine-source-evidence-unit-v1":
        errors.append("evidence_unit_schema_version")
    if unit["source_digest"] != digest_text(source_text):
        errors.append("source_digest_mismatch")
    start, end = unit["byte_start"], unit["byte_end"]
    source_bytes = source_text.encode("utf-8")
    if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(source_bytes)):
        errors.append("invalid_span")
    else:
        try:
            actual = source_bytes[start:end].decode("utf-8")
        except UnicodeDecodeError:
            errors.append("span_not_utf8_aligned")
        else:
            if actual != unit["text"]:
                errors.append("quote_span_mismatch")
    if (not isinstance(unit.get("authorization_ids"), list)
            or any(not isinstance(value, str) or not value for value in unit["authorization_ids"])):
        errors.append("invalid_authorization_ids")
    elif len(unit["authorization_ids"]) != len(set(unit["authorization_ids"])):
        errors.append("duplicate_authorization_id")
    if not isinstance(unit.get("synthetic_test_only"), bool):
        errors.append("synthetic_test_only_must_be_boolean")
    expected_id = stable_id("EV", unit.get("source_id"), start, end, unit.get("text"))
    if unit.get("evidence_unit_id") != expected_id:
        errors.append("evidence_unit_id_mismatch")
    unsigned = dict(unit)
    supplied = unsigned.pop("object_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("object_digest_mismatch")
    return errors


def validate_reference_assertions(
        assertions: Iterable[dict[str, Any]], *,
        valid_evidence_unit_ids: set[str] | None = None,
        evidence_units_by_id: dict[str, dict[str, Any]] | None = None,
        source_text_by_source_id: dict[str, str] | None = None,
        review_records_by_id: dict[str, dict[str, Any]] | None = None,
        reviewer_identity_by_review_id: dict[str, str] | None = None) -> dict[str, Any]:
    """这些对象是可追溯裁决参考，不被命名为 ground truth。

    ``reviewer_identity_by_review_id`` 仅保留为迁移探针；自由填写的名字不再
    构成独立审查证据，传入它会明确失败。正式调用必须传 digest-closed 的
    ``review_records_by_id``。
    """
    ids: set[str] = set()
    errors: list[str] = []
    referenced_review_ids: set[str] = set()
    referenced_evidence_ids: set[str] = set()
    required = ("schema_version", "assertion_id", "subject", "predicate",
                "object_value", "unit", "time_scope", "polarity", "modality",
                "preconditions", "evidence_unit_ids", "authorization_ids",
                "risk_class", "extraction_origin", "engine_provenance",
                "verification_status", "review_ids", "object_digest")
    for index, row in enumerate(assertions):
        if not isinstance(row, dict):
            errors.append(f"reference_assertion_not_object:row-{index}")
            continue
        try:
            require_fields(row, required, "reference assertion")
        except ContractError as exc:
            errors.append(str(exc))
            continue
        assertion_id = str(row["assertion_id"])
        if set(row) != set(required):
            errors.append(f"field_set_mismatch:{assertion_id}")
        if row.get("schema_version") != "eval-spine-reference-assertion-v1":
            errors.append(f"schema_version_mismatch:{assertion_id}")
        if assertion_id in ids:
            errors.append(f"duplicate_assertion_id:{assertion_id}")
        ids.add(assertion_id)
        if row["verification_status"] not in {
                "PROPOSED", "SINGLE_REVIEWED", "DUAL_ADJUDICATED", "REJECTED"}:
            errors.append(f"invalid_verification_status:{assertion_id}")
        review_ids = row["review_ids"] if isinstance(row.get("review_ids"), list) else []
        if (not isinstance(row.get("review_ids"), list)
                or any(not isinstance(value, str) or not value for value in review_ids)
                or len(review_ids) != len(set(review_ids))):
            errors.append(f"invalid_review_ids:{assertion_id}")
            review_ids = []
        assertion_evidence_ids = row.get("evidence_unit_ids")
        if (not isinstance(assertion_evidence_ids, list)
                or any(not isinstance(value, str) or not value
                       for value in assertion_evidence_ids)
                or len(assertion_evidence_ids) != len(set(assertion_evidence_ids))):
            errors.append(f"invalid_evidence_unit_ids:{assertion_id}")
            assertion_evidence_ids = []
        else:
            referenced_evidence_ids.update(assertion_evidence_ids)
        referenced_review_ids.update(review_ids)
        if reviewer_identity_by_review_id is not None:
            errors.append(
                f"legacy_self_reported_reviewer_identity_not_accepted:{assertion_id}")
        reviews: list[dict[str, Any]] = []
        if review_ids and not isinstance(review_records_by_id, dict):
            errors.append(f"review_records_missing:{assertion_id}")
        elif isinstance(review_records_by_id, dict):
            for review_id in review_ids:
                review = review_records_by_id.get(review_id)
                if review is None:
                    errors.append(f"review_record_missing:{assertion_id}:{review_id}")
                    continue
                review_errors = _validate_reference_review_record(
                    review_id, review, row, evidence_units_by_id)
                errors.extend(review_errors)
                if isinstance(review, dict):
                    reviews.append(review)
        errors.extend(_validate_reference_review_outcome(row, reviews))
        if valid_evidence_unit_ids is not None:
            errors.append(f"legacy_evidence_id_set_not_accepted:{assertion_id}")
        if row.get("verification_status") != "PROPOSED":
            if (not isinstance(evidence_units_by_id, dict)
                    or not isinstance(source_text_by_source_id, dict)):
                errors.append(f"evidence_records_missing:{assertion_id}")
            else:
                for evidence_id in assertion_evidence_ids:
                    unit = evidence_units_by_id.get(evidence_id)
                    if not isinstance(unit, dict):
                        errors.append(
                            f"evidence_record_missing:{assertion_id}:{evidence_id}")
                        continue
                    if unit.get("evidence_unit_id") != evidence_id:
                        errors.append(
                            f"evidence_record_key_mismatch:{assertion_id}:{evidence_id}")
                        continue
                    source_id = unit.get("source_id")
                    source_text = source_text_by_source_id.get(source_id)
                    if not isinstance(source_text, str):
                        errors.append(
                            f"evidence_source_missing:{assertion_id}:{evidence_id}")
                        continue
                    for error in verify_source_evidence_unit(unit, source_text):
                        errors.append(
                            f"evidence_record_invalid:{assertion_id}:{evidence_id}:{error}")
        if row.get("risk_class") not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            errors.append(f"invalid_risk_class:{assertion_id}")
        provenance = row.get("engine_provenance")
        if not isinstance(provenance, dict) or set(provenance) != {
                "engine_kind", "engine_id", "engine_revision",
                "prompt_or_rule_digest", "provider_call_id"}:
            errors.append(f"invalid_engine_provenance:{assertion_id}")
        unsigned = dict(row)
        supplied = unsigned.pop("object_digest")
        if supplied != digest_json(unsigned):
            errors.append(f"object_digest_mismatch:{assertion_id}")
    return {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "count": len(ids),
        "referenced_review_record_count": len(referenced_review_ids),
        "referenced_evidence_record_count": len(referenced_evidence_ids),
        "evidence_record_manifest_digest": digest_json([
            {"evidence_unit_id": evidence_id,
             "object_digest": ((evidence_units_by_id or {}).get(evidence_id) or {}).get(
                 "object_digest")}
            for evidence_id in sorted(referenced_evidence_ids)
        ]),
    }
