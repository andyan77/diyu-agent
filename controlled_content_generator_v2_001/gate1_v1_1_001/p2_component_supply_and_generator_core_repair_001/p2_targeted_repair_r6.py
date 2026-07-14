#!/usr/bin/env python3
"""Build the R6 executable-contract repair review packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from p2_component_model import (
    COMPONENT_CANDIDATES_PATH,
    TASK_ID,
    TASK_ROOT,
    jsonl_bytes,
    load_jsonl,
    object_digest,
    require,
    sha256_bytes,
    sha256_file,
    source_state,
    yaml_bytes,
)
from p2_final_documents_r6 import build_generator_evidence_r6
from p2_targeted_repair_r2 import (
    ADDITION_CANDIDATES_R2_PATH,
    REVISED_COMPONENTS_R2_PATH,
)
from p2_targeted_repair_r3 import (
    ADDITION_CANDIDATES_R3_PATH,
    REVISED_COMPONENTS_R3_PATH,
)
from p2_targeted_repair_r4 import (
    ADDITION_CANDIDATES_R4_PATH,
    REVISED_COMPONENTS_R4_PATH,
)
from p2_targeted_repair_r5 import (
    ADDITION_CANDIDATES_R5_PATH,
    REVISED_AB_R5_PATH,
    REVISED_COMPONENTS_R5_PATH,
    REVISED_RULES_R5_PATH,
    TARGETED_REVIEW_PACKET_R5_PATH,
)


if not __debug__:
    sys.stderr.write("P2 targeted repair r6 refuses python -O\n")
    raise SystemExit(2)


GENERATOR_CORE_R6_PATH = TASK_ROOT / "p2_generator_core_r6.py"
GENERATOR_EVIDENCE_R6_PATH = TASK_ROOT / "p2_final_documents_r6.py"
REQUIRED_SLOT_TAMPERS_R6_PATH = (
    TASK_ROOT / "generator/required_slot_trust_root_tamper_results.r6.jsonl"
)
PROGRAM_SCHEMA_TAMPERS_R6_PATH = (
    TASK_ROOT / "generator/path_program_schema_tamper_results.r6.jsonl"
)
MECHANISM_IDENTITY_TAMPERS_R6_PATH = (
    TASK_ROOT / "generator/mechanism_identity_tamper_results.r6.jsonl"
)
BOUND_FACT_EFFECTS_R6_PATH = (
    TASK_ROOT / "generator/bound_fact_structural_effect_results.r6.jsonl"
)
TARGETED_REVIEW_PACKET_R6_PATH = (
    TASK_ROOT / "review/targeted_repair_review_packet.r6.jsonl"
)
TARGETED_REVIEW_JOB_R6_PATH = (
    TASK_ROOT / "review/targeted_repair_review_job.r6.yaml"
)
TARGETED_RESULT_R6_PATH = (
    TASK_ROOT / "result/p2_targeted_repair_checkpoint_result.r6.yaml"
)
R5_PRIMARY_RECORDS_PATH = TASK_ROOT / "imports/targeted_r5/primary/records.jsonl"
R5_SECONDARY_RECORDS_PATH = TASK_ROOT / "imports/targeted_r5/secondary/records.jsonl"


def _component_pool(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in (
        COMPONENT_CANDIDATES_PATH,
        REVISED_COMPONENTS_R2_PATH,
        ADDITION_CANDIDATES_R2_PATH,
        REVISED_COMPONENTS_R3_PATH,
        ADDITION_CANDIDATES_R3_PATH,
        REVISED_COMPONENTS_R4_PATH,
        ADDITION_CANDIDATES_R4_PATH,
        REVISED_COMPONENTS_R5_PATH,
        ADDITION_CANDIDATES_R5_PATH,
    ):
        rows.update(
            {
                str(row["component_id"]): row
                for row in load_jsonl(root / path)
            }
        )
    return rows


def _r5_core_records(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    primary = next(
        row
        for row in load_jsonl(root / R5_PRIMARY_RECORDS_PATH)
        if row["packet_item_id"] == "P2R5-GENERATOR-CORE"
    )
    secondary = next(
        row
        for row in load_jsonl(root / R5_SECONDARY_RECORDS_PATH)
        if row["packet_item_id"] == "P2R5-GENERATOR-CORE"
    )
    require(primary["decision"] == "REPAIR", "E_R6_R5_PRIMARY_FAILURE")
    require(secondary["decision"] == "APPROVE", "E_R6_R5_SECONDARY_EVIDENCE")
    require(
        primary["record_digest"] == object_digest(primary, "record_digest")
        and secondary["record_digest"] == object_digest(secondary, "record_digest"),
        "E_R6_R5_REVIEW_DIGEST",
    )
    return primary, secondary


def build_targeted_repair_r6_documents(root: Path) -> dict[Path, bytes]:
    state = source_state(root)
    paths = load_jsonl(root / REVISED_AB_R5_PATH)
    rules = load_jsonl(root / REVISED_RULES_R5_PATH)
    pool = _component_pool(root)
    selected_ids = {
        str(component_id)
        for path in paths
        for component_id in path["lane_a"]["component_ids"]
    }
    components = [pool[component_id] for component_id in sorted(selected_ids)]
    evidence = build_generator_evidence_r6(
        state["profiles"], components, rules, paths
    )
    primary, secondary = _r5_core_records(root)
    evidence_documents = {
        REQUIRED_SLOT_TAMPERS_R6_PATH: jsonl_bytes(
            evidence["required_slot_tampers"]
        ),
        PROGRAM_SCHEMA_TAMPERS_R6_PATH: jsonl_bytes(
            evidence["path_program_schema_tampers"]
        ),
        MECHANISM_IDENTITY_TAMPERS_R6_PATH: jsonl_bytes(
            evidence["observable_effect_tampers"]
        ),
        BOUND_FACT_EFFECTS_R6_PATH: jsonl_bytes(
            evidence["bound_fact_effect_cases"]
        ),
    }
    evidence_index = [
        {
            "path": path.as_posix(),
            "sha256": sha256_bytes(payload),
            "case_count": len(payload.decode("utf-8").splitlines()),
        }
        for path, payload in evidence_documents.items()
    ]
    packet = [
        {
            "packet_item_id": "P2R6-GENERATOR-CORE",
            "object_type": "EXECUTABLE_SLOT_AND_PATH_SCHEMA_GENERATOR_CORE_REPAIR",
            "review_subject": {
                "path": GENERATOR_CORE_R6_PATH.as_posix(),
                "sha256": sha256_file(root / GENERATOR_CORE_R6_PATH),
                "evidence_harness": {
                    "path": GENERATOR_EVIDENCE_R6_PATH.as_posix(),
                    "sha256": sha256_file(root / GENERATOR_EVIDENCE_R6_PATH),
                },
                "evidence_documents": evidence_index,
                "r5_failure_evidence": {
                    "review_packet_sha256": sha256_file(
                        root / TARGETED_REVIEW_PACKET_R5_PATH
                    ),
                    "primary_record_digest": primary["record_digest"],
                    "primary_decision": primary["decision"],
                    "secondary_record_digest": secondary["record_digest"],
                    "secondary_decision": secondary["decision"],
                },
                "required_repairs": {
                    "component_required_slot_exact_equality_enforced": True,
                    "operator_program_required_and_unknown_fields_enforced": True,
                    "mechanism_metadata_tamper_classified_as_identity_rejection": True,
                    "ordinary_component_nonmetadata_bound_fact_effect_proven": True,
                },
                "approved_r5_components_and_paths_modified": False,
                "audience_content_allowed": False,
                "external_provider_allowed": False,
                "readiness_transition_allowed": False,
            },
            "required_review_roles": [
                "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
            ],
            "prefilled_score": None,
            "prefilled_decision": None,
        }
    ]
    packet_bytes = jsonl_bytes(packet)
    packet_sha = sha256_bytes(packet_bytes)
    job: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "prompt_revision": "r6",
        "checkpoint_state": "PENDING_TARGETED_R6_TWO_REVIEW",
        "review_packet_path": TARGETED_REVIEW_PACKET_R6_PATH.as_posix(),
        "review_packet_sha256": packet_sha,
        "packet_item_count": 1,
        "reviewer_policy": {
            "reuse_identity_isolated_primary_and_secondary_reviewers": True,
            "review_actual_runtime_and_evidence": True,
            "r5_failure_record_remains_visible_and_immutable": True,
            "self_approval_allowed": False,
        },
        "activation_before_matching_approvals_allowed": False,
    }
    job["review_job_digest"] = object_digest(job, "review_job_digest")
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_TARGETED_R6_TWO_REVIEW",
        "p2_complete": False,
        "p3_allowed": False,
        "review_packet_sha256": packet_sha,
        "review_item_count": 1,
        "r5_failure_evidence_preserved": True,
        "active_component_count": 0,
        "active_edge_count": 0,
        "self_approval_count": 0,
        "core_numbers": {
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
    result["result_digest"] = object_digest(result, "result_digest")
    documents = dict(evidence_documents)
    documents.update(
        {
            TARGETED_REVIEW_PACKET_R6_PATH: packet_bytes,
            TARGETED_REVIEW_JOB_R6_PATH: yaml_bytes(
                {"targeted_repair_review_job": job}
            ),
            TARGETED_RESULT_R6_PATH: yaml_bytes(
                {"p2_targeted_repair_checkpoint_result": result}
            ),
        }
    )
    return documents


def validate_targeted_repair_r6_documents(documents: dict[Path, bytes]) -> None:
    def rows(path: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in documents[path].decode("utf-8").splitlines()
            if line
        ]

    slot_cases = rows(REQUIRED_SLOT_TAMPERS_R6_PATH)
    schema_cases = rows(PROGRAM_SCHEMA_TAMPERS_R6_PATH)
    identity_cases = rows(MECHANISM_IDENTITY_TAMPERS_R6_PATH)
    effect_cases = rows(BOUND_FACT_EFFECTS_R6_PATH)
    packet = rows(TARGETED_REVIEW_PACKET_R6_PATH)
    result = yaml.safe_load(documents[TARGETED_RESULT_R6_PATH])[
        "p2_targeted_repair_checkpoint_result"
    ]
    require(
        len(slot_cases) == 20
        and all(
            row["tamper_rejected"]
            and row["error_code"] == "E_COMPONENT_REQUIRED_SLOT_MISMATCH"
            for row in slot_cases
        ),
        "E_R6_REQUIRED_SLOT_GATE",
    )
    require(
        len(schema_cases) == 240
        and all(
            row["tamper_rejected"]
            and row["error_code"] == "E_AXIS_PROGRAM_FIELD_SET"
            for row in schema_cases
        ),
        "E_R6_PROGRAM_SCHEMA_GATE",
    )
    require(
        len(identity_cases) == 62
        and all(
            row["registry_identity_rejected"]
            and row["nonmetadata_structure_change_claimed"] is False
            for row in identity_cases
        ),
        "E_R6_MECHANISM_IDENTITY_CLASSIFICATION",
    )
    require(
        len(effect_cases) == 62
        and all(
            row["same_required_slot_preserved"]
            and row["nonmetadata_structure_changed"]
            for row in effect_cases
        ),
        "E_R6_BOUND_FACT_EFFECT",
    )
    require(len(packet) == 1, "E_R6_PACKET_COUNT")
    require(
        result["p2_complete"] is False
        and result["p3_allowed"] is False
        and not any(result["readiness"].values()),
        "E_R6_EARLY_ACTIVATION",
    )


__all__ = [
    "BOUND_FACT_EFFECTS_R6_PATH",
    "MECHANISM_IDENTITY_TAMPERS_R6_PATH",
    "PROGRAM_SCHEMA_TAMPERS_R6_PATH",
    "REQUIRED_SLOT_TAMPERS_R6_PATH",
    "TARGETED_REVIEW_PACKET_R6_PATH",
    "TARGETED_RESULT_R6_PATH",
    "build_targeted_repair_r6_documents",
    "validate_targeted_repair_r6_documents",
]
