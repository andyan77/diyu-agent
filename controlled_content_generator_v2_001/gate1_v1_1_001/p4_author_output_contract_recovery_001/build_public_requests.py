#!/usr/bin/env python3
"""Build 20 public author-interface recovery requests from frozen P3 inputs."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from author_contract import (
    EXPECTED_ATTESTATION,
    MODEL_CAPABILITY,
    NESTED_TYPE_CONTRACT,
    RAW_CLAIM_FIELDS,
    RAW_COMPONENT_FIELDS,
    RAW_FIELDS,
    RAW_SCHEMA,
    RAW_SURFACE_FIELDS,
    RAW_TYPE_CONTRACT,
    REASONING_EFFORT,
    ROLE_ALLOWED_SURFACE_KINDS,
    ROOT,
    SERVICE_TIER,
    TASK_ID,
    canonical_json,
    object_digest,
    sha256_file,
    write_jsonl,
)


if not __debug__:
    sys.stderr.write("build_public_requests refuses python -O\n")
    raise SystemExit(2)


TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_author_output_contract_recovery_001"
)
P3_REQUESTS = ROOT / (
    "controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001/"
    "freeze/attempt_1/positive_author_requests_20.v0.2.jsonl"
)
CONTRACT = ROOT / TASK_ROOT / "contract/author_semantic_output_contract.v1.0.json"
INSTRUCTION = ROOT / TASK_ROOT / "contract/controlled_author_instruction.v1.0.md"
OUTPUT = ROOT / TASK_ROOT / "public/public_author_requests_20.v1.0.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def exact_contract() -> dict[str, Any]:
    return {
        "raw_top_level_fields": sorted(RAW_FIELDS),
        "semantic_surface_fields": sorted(RAW_SURFACE_FIELDS),
        "semantic_claim_fields": sorted(RAW_CLAIM_FIELDS),
        "semantic_component_usage_fields": sorted(RAW_COMPONENT_FIELDS),
        "author_attestation_fields_and_values": EXPECTED_ATTESTATION,
        "surface_kind_enum": [
            "audio_execution",
            "body",
            "cta",
            "spoken_line",
            "synthetic_disclosure",
            "title",
            "visual_execution",
        ],
        "raw_schema_version": RAW_SCHEMA,
        "unknown_or_alias_fields_forbidden": True,
        "core_fact_coverage_required": True,
        "claim_text_verbatim_on_surface_required": True,
        "component_pointer_must_bind_core_or_required_slot_fact": True,
        "component_pointer_must_use_role_compatible_surface": True,
        "role_allowed_surface_kinds": ROLE_ALLOWED_SURFACE_KINDS,
        "serializer_semantic_mutation_allowed": False,
        "run_id_unique_across_batch": True,
        "raw_type_contract": RAW_TYPE_CONTRACT,
        "nested_type_contract": NESTED_TYPE_CONTRACT,
    }


def build(platform_agent_id: str) -> list[dict[str, Any]]:
    contract_sha = sha256_file(CONTRACT)
    instruction_sha = sha256_file(INSTRUCTION)
    rows = []
    for source in read_jsonl(P3_REQUESTS):
        row = copy.deepcopy(source)
        profile_id = str(row["profile_id"])
        row.pop("attempt", None)
        row.pop("product_core_surface_requirements", None)
        for key in (
            "prior_attempt_artifact_files_provided_to_author",
            "prior_attempt_context_may_be_retained_by_same_agent",
            "prior_review_score_visible_to_author",
            "author_model_capability_id",
            "author_model_label",
            "single_first_output_only",
        ):
            row.pop(key, None)
        row.update(
            {
                "schema_version": "gate1-p4-public-author-request-v1.0",
                "task_id": TASK_ID,
                "request_id": f"P4AOR-PUBLIC-{profile_id}",
                "request_digest": "",
                "author_identity": "P4AOR-PUBLIC-CONTROLLED-AUTHOR-GPT56SOL-001",
                "author_session_logical_id": "P4AOR-PUBLIC-AUTHOR-SESSION-001",
                "author_platform_agent_id": platform_agent_id,
                "model_capability_id": MODEL_CAPABILITY,
                "reasoning_effort": REASONING_EFFORT,
                "service_tier": SERVICE_TIER,
                "author_instruction_path": (TASK_ROOT / "contract/controlled_author_instruction.v1.0.md").as_posix(),
                "author_instruction_sha256": instruction_sha,
                "author_contract_path": (TASK_ROOT / "contract/author_semantic_output_contract.v1.0.json").as_posix(),
                "author_contract_sha256": contract_sha,
                "product_core_requirements": copy.deepcopy(
                    source["product_core_surface_requirements"]
                ),
                "author_output_contract": {
                    "one_first_semantic_output_only": True,
                    "author_may_not_review_or_approve": True,
                    "publishable": False,
                    "runtime_consumable": False,
                    "may_enter_300": False,
                },
                "exact_author_contract": exact_contract(),
                "public_nonhidden_probe": True,
                "counts_toward_H": False,
            }
        )
        row["request_digest"] = object_digest(row, "request_digest")
        rows.append(row)
    if len(rows) != 20 or {row["profile_id"] for row in rows} != {
        f"CP{number:02d}" for number in range(1, 21)
    }:
        raise ValueError("E_PUBLIC_REQUEST_COVERAGE")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--author-platform-agent-id", required=True)
    args = parser.parse_args()
    rows = build(args.author_platform_agent_id)
    write_jsonl(OUTPUT, rows)
    print(canonical_json({"status": "PASS", "request_count": len(rows), "output": OUTPUT.relative_to(ROOT).as_posix()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
