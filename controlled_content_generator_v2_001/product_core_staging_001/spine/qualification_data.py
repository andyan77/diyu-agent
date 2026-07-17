"""密封资格记录的公共证据闭包。"""

from __future__ import annotations

import re
from typing import Any, Iterable

from .canonical import digest_json

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _digest(value: Any) -> bool:
    return isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None


def _review_digest(review: dict[str, Any]) -> str:
    unsigned = dict(review)
    unsigned.pop("review_digest", None)
    return digest_json(unsigned)


def build_qualification_record_index(
        records: Iterable[dict[str, Any]], *,
        dataset_manifest_digest: str) -> dict[str, Any]:
    """由密封数据保管角色生成；索引只暴露身份/摘要，不暴露题面或答案。"""
    if not _digest(dataset_manifest_digest):
        raise ValueError("invalid qualification dataset digest")
    entries: list[dict[str, Any]] = []
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError(f"qualification row {index} is not an object")
        reviews = row.get("gold_review_provenance")
        if not isinstance(reviews, list) or len(reviews) < 2:
            raise ValueError(f"qualification row {index} lacks sealed reviews")
        review_digests = [review.get("review_digest") for review in reviews
                          if isinstance(review, dict)]
        required = ("case_id", "case_digest", "case_payload_digest",
                    "source_group_id", "source_evidence_digest", "gold_label_digest")
        if (any(not str(row.get(field, "")).strip() for field in required[:1])
                or any(not _digest(row.get(field)) for field in required[1:3] + required[4:])
                or not str(row.get("source_group_id", "")).strip()
                or len(review_digests) != len(reviews)
                or not all(_digest(value) for value in review_digests)):
            raise ValueError(f"qualification row {index} identity invalid")
        entries.append({
            "case_id": row["case_id"], "case_digest": row["case_digest"],
            "case_payload_digest": row["case_payload_digest"],
            "source_group_id": row["source_group_id"],
            "source_evidence_digest": row["source_evidence_digest"],
            "gold_label_digest": row["gold_label_digest"],
            "gold_review_digests": sorted(review_digests),
        })
    entries.sort(key=lambda row: row["case_id"])
    if (len({row["case_id"] for row in entries}) != len(entries)
            or len({row["case_digest"] for row in entries}) != len(entries)):
        raise ValueError("qualification index contains duplicates")
    result: dict[str, Any] = {
        "schema_version": "eval-spine-qualification-record-index-v1",
        "data_grid": "G3_MEASUREMENT_QUALIFICATION",
        "content_status": "ADJUDICATED", "sealed": True,
        "visibility_partition": "HIDDEN",
        "dataset_manifest_digest": dataset_manifest_digest,
        "record_count": len(entries), "entries": entries, "index_digest": "",
    }
    unsigned = dict(result)
    unsigned.pop("index_digest")
    result["index_digest"] = digest_json(unsigned)
    return result


def verify_qualification_record_index(
        index: dict[str, Any] | None, *,
        expected_dataset_manifest_digest: str | None) -> list[str]:
    if not isinstance(index, dict):
        return ["qualification_record_index_missing"]
    required = {"schema_version", "data_grid", "content_status", "sealed",
                "visibility_partition", "dataset_manifest_digest", "record_count",
                "entries", "index_digest"}
    errors: list[str] = []
    if set(index) != required:
        errors.append("qualification_record_index_field_set")
    if (index.get("schema_version") != "eval-spine-qualification-record-index-v1"
            or index.get("data_grid") != "G3_MEASUREMENT_QUALIFICATION"
            or index.get("content_status") != "ADJUDICATED"
            or index.get("sealed") is not True
            or index.get("visibility_partition") != "HIDDEN"):
        errors.append("qualification_record_index_state")
    if index.get("dataset_manifest_digest") != expected_dataset_manifest_digest:
        errors.append("qualification_record_index_dataset_mismatch")
    entries = index.get("entries")
    if not isinstance(entries, list):
        entries = []
        errors.append("qualification_record_index_entries")
    entry_fields = {"case_id", "case_digest", "case_payload_digest", "source_group_id",
                    "source_evidence_digest", "gold_label_digest", "gold_review_digests"}
    ids: list[str] = []
    digests: list[str] = []
    for row in entries:
        if (not isinstance(row, dict) or set(row) != entry_fields
                or not isinstance(row.get("case_id"), str) or not row["case_id"]
                or not isinstance(row.get("source_group_id"), str)
                or not row["source_group_id"]
                or not all(_digest(row.get(field)) for field in (
                    "case_digest", "case_payload_digest", "source_evidence_digest",
                    "gold_label_digest"))
                or not isinstance(row.get("gold_review_digests"), list)
                or len(row["gold_review_digests"]) < 2
                or not all(_digest(value) for value in row["gold_review_digests"])):
            errors.append("qualification_record_index_entry_shape")
            continue
        ids.append(row["case_id"])
        digests.append(row["case_digest"])
    if len(ids) != len(set(ids)) or len(digests) != len(set(digests)):
        errors.append("qualification_record_index_duplicates")
    if index.get("record_count") != len(entries):
        errors.append("qualification_record_index_count")
    unsigned = dict(index)
    supplied = unsigned.pop("index_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("qualification_record_index_digest")
    return sorted(set(errors))


def validate_qualification_records(
        records: Iterable[dict[str, Any]], *,
        expected_dataset_manifest_digest: str | None,
        gold_field_names: Iterable[str],
        qualification_record_index: dict[str, Any] | None = None,
        require_gold_review_provenance: bool = True) -> dict[str, Any]:
    """拒绝克隆注水、跨分区、脱清单和未证明独立金标的记录。"""
    rows = list(records)
    errors: list[str] = []
    index_errors = verify_qualification_record_index(
        qualification_record_index,
        expected_dataset_manifest_digest=expected_dataset_manifest_digest)
    errors.extend(index_errors)
    indexed = {
        row["case_id"]: row for row in (qualification_record_index or {}).get("entries", [])
        if isinstance(row, dict) and isinstance(row.get("case_id"), str)
    } if isinstance(qualification_record_index, dict) else {}
    if not _digest(expected_dataset_manifest_digest):
        errors.append("expected_dataset_manifest_digest_missing")
    case_ids: set[str] = set()
    case_digests: set[str] = set()
    payload_digests: set[str] = set()
    expected_gold_fields = tuple(sorted(set(gold_field_names)))
    if not expected_gold_fields:
        errors.append("gold_field_names_missing")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"record_not_object:row-{index}")
            continue
        label = str(row.get("case_id", f"row-{index}"))
        required = {
            "case_id", "case_digest", "case_payload_digest", "source_group_id",
            "visibility_partition", "dataset_manifest_digest", "gold_label_digest",
            "gold_field_names", "source_evidence_digest",
        }
        missing = sorted(required - set(row))
        if missing:
            errors.append(f"missing_fields:{label}:{','.join(missing)}")
            continue
        case_id = str(row.get("case_id", ""))
        if not case_id:
            errors.append(f"empty_case_id:{label}")
        elif case_id in case_ids:
            errors.append(f"duplicate_case_id:{case_id}")
        case_ids.add(case_id)
        if not str(row.get("source_group_id", "")).strip():
            errors.append(f"empty_source_group_id:{label}")
        if row.get("visibility_partition") != "HIDDEN":
            errors.append(f"not_hidden_qualification_record:{label}")
        if row.get("dataset_manifest_digest") != expected_dataset_manifest_digest:
            errors.append(f"dataset_manifest_mismatch:{label}")
        supplied_gold_fields = row.get("gold_field_names")
        if (not isinstance(supplied_gold_fields, list)
                or supplied_gold_fields != sorted(set(supplied_gold_fields))
                or not set(expected_gold_fields).issubset(supplied_gold_fields)
                or any(field not in row for field in supplied_gold_fields)):
            errors.append(f"gold_field_binding_invalid:{label}")
        else:
            expected_gold_digest = digest_json({
                field: row[field] for field in supplied_gold_fields})
            if row.get("gold_label_digest") != expected_gold_digest:
                errors.append(f"gold_label_digest_mismatch:{label}")
        if not _digest(row.get("source_evidence_digest")):
            errors.append(f"invalid_digest:{label}:source_evidence_digest")
        for field, seen in (("case_digest", case_digests),
                            ("case_payload_digest", payload_digests)):
            value = row.get(field)
            if not _digest(value):
                errors.append(f"invalid_digest:{label}:{field}")
            elif value in seen:
                errors.append(f"duplicate_{field}:{label}")
            seen.add(str(value))
        if not _digest(row.get("gold_label_digest")):
            errors.append(f"invalid_digest:{label}:gold_label_digest")
        payload_excluded = {
            "case_id", "case_digest", "case_payload_digest", "source_group_id",
            "visibility_partition", "dataset_manifest_digest", "gold_label_digest",
            "gold_field_names", "gold_review_provenance",
        }
        expected_payload_digest = digest_json({
            key: value for key, value in row.items() if key not in payload_excluded})
        if row.get("case_payload_digest") != expected_payload_digest:
            errors.append(f"case_payload_digest_mismatch:{label}")
        unsigned = dict(row)
        supplied = unsigned.pop("case_digest", None)
        if supplied != digest_json(unsigned):
            errors.append(f"case_digest_mismatch:{label}")
        if require_gold_review_provenance:
            reviews = row.get("gold_review_provenance")
            if not isinstance(reviews, list) or len(reviews) < 2:
                errors.append(f"gold_review_provenance_missing:{label}")
                continue
            review_ids: set[str] = set()
            identities: set[str] = set()
            valid = True
            for review in reviews:
                review_fields = {
                    "review_id", "reviewer_identity", "reviewer_kind",
                    "model_revision", "prompt_digest", "case_id",
                    "case_payload_digest", "source_evidence_digest",
                    "gold_label_digest", "decision", "evidence_digest",
                    "review_digest"}
                if not isinstance(review, dict) or set(review) != review_fields:
                    valid = False
                    continue
                review_id = str(review.get("review_id", ""))
                identity = str(review.get("reviewer_identity", ""))
                kind = review.get("reviewer_kind")
                if not review_id or not identity or kind not in {"HUMAN", "AI"}:
                    valid = False
                if kind == "AI" and (not str(review.get("model_revision", "")).strip()
                                     or not _digest(review.get("prompt_digest"))):
                    valid = False
                if kind == "HUMAN" and (review.get("model_revision") is not None
                                        or review.get("prompt_digest") is not None):
                    valid = False
                if (review.get("case_id") != case_id
                        or review.get("case_payload_digest") != row.get("case_payload_digest")
                        or review.get("source_evidence_digest")
                        != row.get("source_evidence_digest")
                        or review.get("gold_label_digest") != row.get("gold_label_digest")
                        or review.get("decision") != "CONFIRM"
                        or not _digest(review.get("evidence_digest"))
                        or review.get("review_digest") != _review_digest(review)):
                    valid = False
                review_ids.add(review_id)
                identities.add(identity)
            if not valid:
                errors.append(f"gold_review_provenance_invalid:{label}")
            if len(review_ids) < 2 or len(identities) < 2:
                errors.append(f"gold_review_independence_unproven:{label}")
        index_entry = indexed.get(case_id)
        expected_index_entry = {
            "case_id": case_id, "case_digest": row.get("case_digest"),
            "case_payload_digest": row.get("case_payload_digest"),
            "source_group_id": row.get("source_group_id"),
            "source_evidence_digest": row.get("source_evidence_digest"),
            "gold_label_digest": row.get("gold_label_digest"),
            "gold_review_digests": sorted(
                review.get("review_digest") for review in row.get(
                    "gold_review_provenance", []) if isinstance(review, dict)),
        }
        if index_entry != expected_index_entry:
            errors.append(f"qualification_record_index_binding:{label}")
    return {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "record_count": len(rows),
        "unique_case_count": len(case_ids),
        "unique_payload_count": len(payload_digests),
        "dataset_manifest_digest": expected_dataset_manifest_digest,
        "qualification_record_index_digest": (
            (qualification_record_index or {}).get("index_digest")
            if isinstance(qualification_record_index, dict) else None),
    }
