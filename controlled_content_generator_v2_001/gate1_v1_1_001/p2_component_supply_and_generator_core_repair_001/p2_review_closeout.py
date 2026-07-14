#!/usr/bin/env python3
"""Validate and combine the two identity-isolated P2 component reviews."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001"
REVIEWED_COMMIT = "c37a894930025aac99db18a055d5a79294fa89dc"
PACKET_SHA256 = "67751ab60e6ee8e227c4aaff3dccd4c7f3c5d027ceda2f910f4ea1a600231095"
PRIMARY_ROLE = "PRIMARY_CONTENT_VALUE_COMPOSABILITY"
SECONDARY_ROLE = "SECONDARY_PROVENANCE_FACT_AUTHORIZATION"
SCORE_KEYS = (
    "source_parent_evidence_15",
    "semantic_atomicity_15",
    "parameterization_composability_20",
    "applicability_compatibility_missing_boundary_15",
    "cross_product_reuse_5",
    "nonduplicate_information_gain_10",
)
SCORE_MAXIMA = {
    "source_parent_evidence_15": 15,
    "semantic_atomicity_15": 15,
    "parameterization_composability_20": 20,
    "applicability_compatibility_missing_boundary_15": 15,
    "cross_product_reuse_5": 5,
    "nonduplicate_information_gain_10": 10,
    "type_specific_quality_20": 20,
}


class IndependentReviewError(ValueError):
    """Raised when an external review cannot be consumed without reinterpretation."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: dict[str, Any], digest_key: str) -> str:
    return sha256_bytes(
        canonical_json(
            {key: child for key, child in value.items() if key != digest_key}
        ).encode("utf-8")
    )


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise IndependentReviewError(f"{code}:{detail}" if detail else code)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line:
            continue
        value = json.loads(raw_line)
        require(isinstance(value, dict), "E_REVIEW_RECORD", f"{path}:{line_number}")
        rows.append(value)
    return rows


def grade_for(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def validate_record_score(record: dict[str, Any]) -> None:
    item_id = str(record.get("packet_item_id"))
    breakdown = record.get("score_breakdown")
    require(isinstance(breakdown, dict), "E_SCORE_BREAKDOWN", item_id)
    for key, maximum in SCORE_MAXIMA.items():
        score = breakdown.get(key)
        require(
            isinstance(score, int) and 0 <= score <= maximum,
            "E_SCORE_RANGE",
            f"{item_id}:{key}",
        )
    common = sum(int(breakdown[key]) for key in SCORE_KEYS)
    type_score = int(breakdown["type_specific_quality_20"])
    total = common + type_score
    require(record.get("common_score_80") == common, "E_COMMON_SCORE", item_id)
    require(record.get("type_score_20") == type_score, "E_TYPE_SCORE", item_id)
    require(record.get("total_score_100") == total, "E_TOTAL_SCORE", item_id)
    require(record.get("grade") == grade_for(total), "E_GRADE", item_id)
    decision = record.get("decision")
    severity = record.get("defect_severity")
    vetoes = record.get("hard_veto_ids")
    require(decision in {"APPROVE", "REPAIR", "REJECT"}, "E_DECISION", item_id)
    require(
        severity in {"NONE", "OBSERVATION", "MINOR", "MAJOR", "FATAL"},
        "E_DEFECT_SEVERITY",
        item_id,
    )
    require(isinstance(vetoes, list), "E_HARD_VETO", item_id)
    if vetoes:
        require(decision == "REJECT", "E_VETO_DECISION", item_id)
    if severity in {"MAJOR", "FATAL"}:
        require(decision != "APPROVE", "E_MAJOR_APPROVAL", item_id)
    if decision == "APPROVE":
        require(total >= 90, "E_APPROVAL_GRADE", item_id)
        require(severity in {"NONE", "OBSERVATION"}, "E_APPROVAL_DEFECT", item_id)
        require(not vetoes, "E_APPROVAL_VETO", item_id)
        if record.get("object_type") == "PROPOSED_ACTIVE_COMPONENT":
            require(
                breakdown["semantic_atomicity_15"] >= 13,
                "E_COMPONENT_ATOMICITY",
                item_id,
            )
            require(
                breakdown["parameterization_composability_20"] >= 17,
                "E_COMPONENT_COMPOSABILITY",
                item_id,
            )
            require(
                breakdown["applicability_compatibility_missing_boundary_15"] >= 13,
                "E_COMPONENT_BOUNDARY",
                item_id,
            )
            require(type_score >= 17, "E_COMPONENT_TYPE_SCORE", item_id)
    if record.get("grade") == "B":
        require(decision == "REPAIR", "E_GRADE_B_REQUIRES_REPAIR", item_id)


def validate_review_records(
    records: list[dict[str, Any]],
    packet: list[dict[str, Any]],
    role: str,
) -> dict[str, Any]:
    require(len(records) == len(packet) == 244, "E_REVIEW_COUNT", role)
    identity_values: set[str] = set()
    session_values: set[str] = set()
    run_values: set[str] = set()
    decision_counts: dict[str, int] = {"APPROVE": 0, "REPAIR": 0, "REJECT": 0}
    for record, packet_item in zip(records, packet, strict=True):
        item_id = str(packet_item.get("packet_item_id"))
        require(record.get("schema_version") == "v0.1", "E_REVIEW_SCHEMA", item_id)
        require(record.get("task_id") == TASK_ID, "E_REVIEW_TASK", item_id)
        require(record.get("prompt_revision") == "r0", "E_REVIEW_REVISION", item_id)
        require(record.get("review_role") == role, "E_REVIEW_ROLE", item_id)
        require(
            record.get("reviewed_commit") == REVIEWED_COMMIT, "E_REVIEW_COMMIT", item_id
        )
        require(
            record.get("review_packet_sha256") == PACKET_SHA256,
            "E_REVIEW_PACKET_HASH",
            item_id,
        )
        require(record.get("packet_item_id") == item_id, "E_REVIEW_ORDER", item_id)
        require(
            record.get("object_type") == packet_item.get("object_type"),
            "E_REVIEW_OBJECT_TYPE",
            item_id,
        )
        require(
            record.get("record_digest") == object_digest(record, "record_digest"),
            "E_REVIEW_RECORD_DIGEST",
            item_id,
        )
        require(isinstance(record.get("findings"), list), "E_REVIEW_FINDINGS", item_id)
        require(isinstance(record.get("rationale"), str), "E_REVIEW_RATIONALE", item_id)
        validate_record_score(record)
        identity_values.add(str(record.get("reviewer_identity_id")))
        session_values.add(str(record.get("reviewer_instance_or_session_id")))
        run_values.add(str(record.get("review_run_id")))
        decision_counts[str(record["decision"])] += 1
    require(len(identity_values) == 1, "E_REVIEW_IDENTITY", role)
    require(len(session_values) == 1, "E_REVIEW_SESSION", role)
    require(len(run_values) == 1, "E_REVIEW_RUN", role)
    return {
        "review_role": role,
        "reviewer_identity_id": next(iter(identity_values)),
        "reviewer_instance_or_session_id": next(iter(session_values)),
        "review_run_id": next(iter(run_values)),
        "record_count": len(records),
        "decision_counts": decision_counts,
    }


def load_review_directory(
    review_dir: Path,
    packet: list[dict[str, Any]],
    role: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records_path = review_dir / "records.jsonl"
    report_path = review_dir / "report.md"
    manifest_path = review_dir / "run_manifest.yaml"
    for path in (records_path, report_path, manifest_path):
        require(path.is_file(), "E_REVIEW_FILE_MISSING", str(path))
    records = read_jsonl(records_path)
    summary = validate_review_records(records, packet, role)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    require(isinstance(manifest, dict), "E_REVIEW_MANIFEST", role)
    manifest_text = canonical_json(manifest)
    for expected in (
        summary["reviewer_identity_id"],
        summary["reviewer_instance_or_session_id"],
        summary["review_run_id"],
        REVIEWED_COMMIT,
        PACKET_SHA256,
    ):
        require(expected in manifest_text, "E_REVIEW_MANIFEST_BINDING", str(expected))
    report_text = report_path.read_text(encoding="utf-8")
    require(report_text.strip(), "E_REVIEW_REPORT_EMPTY", role)
    summary.update(
        {
            "records_sha256": sha256_file(records_path),
            "report_sha256": sha256_file(report_path),
            "run_manifest_sha256": sha256_file(manifest_path),
        }
    )
    return records, summary


def combine_reviews(
    packet: list[dict[str, Any]],
    primary_records: list[dict[str, Any]],
    secondary_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    combined: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    for packet_item, primary, secondary in zip(
        packet, primary_records, secondary_records, strict=True
    ):
        item_id = str(packet_item["packet_item_id"])
        require(
            primary["packet_item_id"] == secondary["packet_item_id"] == item_id,
            "E_PAIR_ORDER",
        )
        same_decision = primary["decision"] == secondary["decision"]
        disposition = (
            primary["decision"]
            if same_decision
            else "DISAGREEMENT_REQUIRES_ADJUDICATION"
        )
        row: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "packet_item_id": item_id,
            "object_type": packet_item["object_type"],
            "primary_record_digest": primary["record_digest"],
            "secondary_record_digest": secondary["record_digest"],
            "primary_decision": primary["decision"],
            "secondary_decision": secondary["decision"],
            "combined_disposition": disposition,
            "requires_targeted_adjudication": not same_decision,
        }
        row["combined_digest"] = object_digest(row, "combined_digest")
        combined.append(row)
        if not same_decision:
            disagreements.append(row)
    return combined, disagreements
