#!/usr/bin/env python3
"""Validate the identity-isolated third adjudication of initial P2 disputes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from p2_review_closeout import (
    PACKET_SHA256,
    REVIEWED_COMMIT,
    canonical_json,
    object_digest,
    read_jsonl,
    require,
    sha256_file,
)


ADJUDICATION_ROLE = "TARGETED_THIRD_ADJUDICATION"


def validate_adjudication(
    adjudication_dir: Path,
    disagreements: list[dict[str, Any]],
    primary_by_id: dict[str, dict[str, Any]],
    secondary_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records_path = adjudication_dir / "records.jsonl"
    report_path = adjudication_dir / "report.md"
    manifest_path = adjudication_dir / "run_manifest.yaml"
    for path in (records_path, report_path, manifest_path):
        require(path.is_file(), "E_ADJUDICATION_FILE_MISSING", str(path))
    records = read_jsonl(records_path)
    require(len(records) == len(disagreements) == 92, "E_ADJUDICATION_COUNT")
    identities: set[str] = set()
    sessions: set[str] = set()
    runs: set[str] = set()
    for record, dispute in zip(records, disagreements, strict=True):
        item_id = str(dispute["packet_item_id"])
        primary = primary_by_id[item_id]
        secondary = secondary_by_id[item_id]
        require(
            record.get("schema_version") == "v0.1", "E_ADJUDICATION_SCHEMA", item_id
        )
        require(
            record.get("task_id")
            == "GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001",
            "E_ADJUDICATION_TASK",
            item_id,
        )
        require(
            record.get("prompt_revision") == "r0", "E_ADJUDICATION_REVISION", item_id
        )
        require(
            record.get("review_role") == ADJUDICATION_ROLE,
            "E_ADJUDICATION_ROLE",
            item_id,
        )
        require(
            record.get("reviewed_commit") == REVIEWED_COMMIT,
            "E_ADJUDICATION_COMMIT",
            item_id,
        )
        require(
            record.get("review_packet_sha256") == PACKET_SHA256,
            "E_ADJUDICATION_PACKET",
            item_id,
        )
        require(
            record.get("packet_item_id") == item_id, "E_ADJUDICATION_ORDER", item_id
        )
        require(
            record.get("object_type") == dispute["object_type"],
            "E_ADJUDICATION_TYPE",
            item_id,
        )
        require(
            record.get("primary_record_digest") == primary["record_digest"]
            and record.get("secondary_record_digest") == secondary["record_digest"],
            "E_ADJUDICATION_REVIEW_BINDING",
            item_id,
        )
        require(
            record.get("primary_decision") == primary["decision"]
            and record.get("secondary_decision") == secondary["decision"],
            "E_ADJUDICATION_DECISION_BINDING",
            item_id,
        )
        require(
            record.get("adjudicated_decision") in {"APPROVE", "REPAIR", "REJECT"},
            "E_ADJUDICATION_DECISION",
            item_id,
        )
        require(
            isinstance(record.get("findings"), list), "E_ADJUDICATION_FINDINGS", item_id
        )
        require(
            isinstance(record.get("rationale"), str) and record["rationale"],
            "E_ADJUDICATION_RATIONALE",
            item_id,
        )
        require(
            record.get("record_digest") == object_digest(record, "record_digest"),
            "E_ADJUDICATION_DIGEST",
            item_id,
        )
        identities.add(str(record.get("reviewer_identity_id")))
        sessions.add(str(record.get("reviewer_instance_or_session_id")))
        runs.add(str(record.get("review_run_id")))
    require(
        len(identities) == len(sessions) == len(runs) == 1, "E_ADJUDICATION_IDENTITY"
    )
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    require(isinstance(manifest, dict), "E_ADJUDICATION_MANIFEST")
    manifest_text = canonical_json(manifest)
    for expected in (
        next(iter(identities)),
        next(iter(sessions)),
        next(iter(runs)),
        REVIEWED_COMMIT,
        PACKET_SHA256,
    ):
        require(expected in manifest_text, "E_ADJUDICATION_MANIFEST_BINDING", expected)
    require(report_path.read_text(encoding="utf-8").strip(), "E_ADJUDICATION_REPORT")
    summary = {
        "review_role": ADJUDICATION_ROLE,
        "reviewer_identity_id": next(iter(identities)),
        "reviewer_instance_or_session_id": next(iter(sessions)),
        "review_run_id": next(iter(runs)),
        "record_count": len(records),
        "records_sha256": sha256_file(records_path),
        "report_sha256": sha256_file(report_path),
        "run_manifest_sha256": sha256_file(manifest_path),
    }
    return records, summary
