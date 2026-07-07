#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

EXPECTED_TASK_ID = "CODEX-GENERATION-CROSS-TYPE-PILOT-001"
EXPECTED_HEAD_BEFORE = "8db429a2a3650a4f31d9e8b6fa72e88f6647e4c1"
EXPECTED_TOTAL = 44
EXPECTED_CATEGORY_COUNTS = {
    "content_method": 11,
    "apparel_claim_boundary": 11,
    "display_to_content": 11,
    "control_plane_governance": 11,
}
EXPECTED_W7_DIGEST = "dd1503011a3a3f4cba9a663e50417037e85e8f09001edfc98c214919284d6c7c"
EXPECTED_FOUNDER_DIGEST = "823ff7ab0a88aa41e235d03b09515b4303c7e4fd420af6619bcddb1cad96ea48"
EXPECTED_ASSIGNMENTS = {f"GA-{idx:03d}" for idx in range(1, 15)}
PILOT_JUDGE_NEXT_STEP = "CODEX-PILOT-JUDGE-REVIEW-AND-GO-NOGO-001"
SEMANTIC_REGEN_NEXT_STEP = "CODEX-SEMANTIC-PILOT-REGEN-001"
SEMANTIC_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-JUDGE-GO-NOGO-001"
SEMANTIC_V3_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V3-JUDGE-GO-NOGO-001"
SEMANTIC_V4_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4-JUDGE-GO-NOGO-001"
SEMANTIC_V4_1_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_1-JUDGE-GO-NOGO-001"
SEMANTIC_V4_2_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_2-JUDGE-GO-NOGO-001"
SEMANTIC_V4_3_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_3-JUDGE-GO-NOGO-001"
SEMANTIC_V4_4_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_4-JUDGE-GO-NOGO-001"
SEMANTIC_V4_5_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_5-JUDGE-GO-NOGO-001"
BATCH_GENERATION_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
SMOKE_FIXTURE_CLASSIFICATION = "schema_route_provenance_smoke_fixture"
SELF_CHECK_TERMS = {
    "candidate_kind",
    "target_owner",
    "layer_annotation",
    "semantic_alignment",
    "body_entailment",
    "dedupe_fingerprint",
    "readiness_flags",
    "state_machine_route",
}
REAL_INSTANCE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\breal brand\b",
        r"\breal sku\b",
        r"\breal store\b",
        r"\breal person\b",
        r"\breal customer\b",
        r"\bcustomer feedback\b",
        r"\bSKU-[A-Z0-9-]+\b",
        r"\bactual brand\b",
        r"\bactual store\b",
    ]
]
HARD_CLAIM_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bguarantees?\b",
        r"\bclinically proven\b",
        r"\btested to\b",
        r"\bcures?\b",
        r"\breduces body size\b",
        r"\bwill make\b",
    ]
]
NEGATIVE_FIXTURES = [
    "negative_wrong_count.yaml",
    "negative_missing_category.yaml",
    "negative_readiness_true.yaml",
    "negative_schema_invalid_candidate.yaml",
    "negative_empty_rich_body.yaml",
    "negative_body_without_proposition_refs.yaml",
    "negative_missing_judge_queue.yaml",
    "negative_hard_claim_expert_synthesis.yaml",
    "negative_real_instance_fact_leak.yaml",
    "negative_p0_00_general_kb_leak.yaml",
    "negative_candidatepack_created.yaml",
    "negative_source_repo_dependency_true.yaml",
    "negative_relation_unknown_candidate.yaml",
    "negative_batch_generation_next_step.yaml",
]


class PilotCheckError(Exception):
    pass


def fail(message: str) -> None:
    raise PilotCheckError(message)


def load_yaml(path: Path) -> Any:
    if not path.exists():
        fail(f"missing yaml: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    if not path.exists():
        fail(f"missing json: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_schema_shape(candidate: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def check(node: Any, spec: dict[str, Any], path: str) -> None:
        expected_type = spec.get("type")
        if expected_type == "object":
            if not isinstance(node, dict):
                errors.append(f"{path}: expected object")
                return
            allowed = set(spec.get("properties", {}))
            for key in spec.get("required", []):
                if key not in node:
                    errors.append(f"{path}.{key}: missing required")
            if spec.get("additionalProperties") is False:
                for key in node:
                    if key not in allowed:
                        errors.append(f"{path}.{key}: additional property")
            for key, child_spec in spec.get("properties", {}).items():
                if key in node:
                    check(node[key], child_spec, f"{path}.{key}")
        elif expected_type == "array":
            if not isinstance(node, list):
                errors.append(f"{path}: expected array")
                return
            if len(node) < spec.get("minItems", 0):
                errors.append(f"{path}: too few items")
            item_spec = spec.get("items")
            if item_spec:
                for index, item in enumerate(node):
                    check(item, item_spec, f"{path}[{index}]")
        elif expected_type == "string":
            if not isinstance(node, str):
                errors.append(f"{path}: expected string")
                return
            if len(node) < spec.get("minLength", 0):
                errors.append(f"{path}: string too short")
        elif expected_type == "boolean":
            if not isinstance(node, bool):
                errors.append(f"{path}: expected boolean")
        elif expected_type == "number":
            if not isinstance(node, (int, float)) or isinstance(node, bool):
                errors.append(f"{path}: expected number")
                return
            if "minimum" in spec and node < spec["minimum"]:
                errors.append(f"{path}: below minimum")
            if "maximum" in spec and node > spec["maximum"]:
                errors.append(f"{path}: above maximum")
        if "const" in spec and node != spec["const"]:
            errors.append(f"{path}: expected const {spec['const']!r}")
        if "enum" in spec and node not in spec["enum"]:
            errors.append(f"{path}: invalid enum {node!r}")

    check(candidate, schema, "$")
    return errors


def text_contains(patterns: list[re.Pattern[str]], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def candidate_text(candidate: dict[str, Any]) -> str:
    semantic = candidate.get("semantic_structure", {})
    rich = candidate.get("rich_body", {})
    chunks = [str(value) for value in semantic.values()]
    chunks.append(str(rich.get("body_text", "")))
    for section in rich.get("body_sections", []):
        chunks.append(str(section.get("heading", "")))
        chunks.append(str(section.get("text", "")))
    return "\n".join(chunks)


def validate_candidate(
    candidate: dict[str, Any],
    schema: dict[str, Any],
    pilot_category: str,
) -> list[str]:
    errors = validate_schema_shape(candidate, schema)
    if errors:
        return errors
    identity = candidate["identity"]
    trace = candidate["w7_trace"]
    ownership = candidate["ownership"]
    source_policy = candidate["source_policy"]
    rich_body = candidate["rich_body"]
    layer = candidate["layer_annotation"]
    readiness = candidate["readiness_flags"]
    state_machine = candidate["state_machine"]
    review = candidate["review"]
    all_text = candidate_text(candidate)

    if trace["w7_map_digest"] != EXPECTED_W7_DIGEST:
        errors.append(f"{identity['candidate_id']}: W7 digest mismatch")
    if trace["founder_overlay_digest"] != EXPECTED_FOUNDER_DIGEST:
        errors.append(f"{identity['candidate_id']}: founder overlay digest mismatch")
    if trace["generation_assignment_id"] not in EXPECTED_ASSIGNMENTS:
        errors.append(f"{identity['candidate_id']}: unknown generation assignment")
    if source_policy["source_type_boundary_status"] != "source_type_is_intake_classification_only":
        errors.append(f"{identity['candidate_id']}: source type boundary not locked")
    if any(value is not False for value in readiness.values()):
        errors.append(f"{identity['candidate_id']}: readiness flag true")
    if state_machine["current_state"] != "gpt_generated_structured_draft":
        errors.append(f"{identity['candidate_id']}: wrong state")
    if review["human_review_required"] is not True or review["reviewer_status"] != "pending_human_review":
        errors.append(f"{identity['candidate_id']}: review queue state invalid")
    if len(rich_body["body_text"]) < 350:
        errors.append(f"{identity['candidate_id']}: rich body too short")
    if any(term in rich_body["body_text"] for term in SELF_CHECK_TERMS):
        errors.append(f"{identity['candidate_id']}: self-check field leaked into body")
    if not rich_body["body_proposition_refs"]:
        errors.append(f"{identity['candidate_id']}: missing body proposition refs")
    for section in rich_body["body_sections"]:
        if not section.get("proposition_refs"):
            errors.append(f"{identity['candidate_id']}: body section without proposition refs")
    if text_contains(HARD_CLAIM_PATTERNS, all_text) and source_policy["expert_synthesis_allowed"] is True:
        errors.append(f"{identity['candidate_id']}: hard claim expert synthesis leak")
    if text_contains(REAL_INSTANCE_PATTERNS, all_text):
        errors.append(f"{identity['candidate_id']}: real instance fact leak")
    if pilot_category == "control_plane_governance":
        if ownership["proposed_target_owner"] == "GeneralKnowledgeBase":
            errors.append(f"{identity['candidate_id']}: P0-00/control-plane routed to GeneralKnowledgeBase")
        if layer["target_layer_candidate"] in {"TBox_candidate", "L2_PlayCard_candidate"}:
            errors.append(f"{identity['candidate_id']}: control-plane sample landed in knowledge layer")
    if pilot_category != "control_plane_governance":
        if ownership["candidate_kind"] != "general_knowledge_candidate":
            errors.append(f"{identity['candidate_id']}: non-control pilot should remain general draft")
    return errors


def validate_relation_candidates(path: Path, candidate_ids: set[str]) -> dict[str, Any]:
    if not path.exists():
        fail(f"missing relation csv: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "relation_id",
        "source_candidate_id",
        "target_candidate_id",
        "relation_type",
        "relation_note",
        "contains_real_instance_fact",
    }
    if not rows:
        fail("relation candidate csv is empty")
    if set(rows[0]) != required:
        fail(f"relation csv fields mismatch: {sorted(rows[0])}")
    unknown_refs: list[str] = []
    real_fact_rows: list[str] = []
    for row in rows:
        if row["source_candidate_id"] not in candidate_ids:
            unknown_refs.append(f"{row['relation_id']}:source")
        if row["target_candidate_id"] not in candidate_ids:
            unknown_refs.append(f"{row['relation_id']}:target")
        relation_text = f"{row['relation_type']} {row['relation_note']}"
        if row["contains_real_instance_fact"].lower() != "false" or text_contains(REAL_INSTANCE_PATTERNS, relation_text):
            real_fact_rows.append(row["relation_id"])
    if unknown_refs:
        fail(f"relation unknown candidate refs: {unknown_refs}")
    if real_fact_rows:
        fail(f"relation real instance leak: {real_fact_rows}")
    return {"relation_count": len(rows), "unknown_refs": 0, "real_instance_fact_leak_count": 0}


def validate_fixture_model(model: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("pilot_fixture", {})
    if data.get("task_id") != EXPECTED_TASK_ID:
        errors.append("task_id mismatch")
    if data.get("source_repo_live_accessed") is not False:
        errors.append("source repo live access must be false")
    if data.get("source_repo_live_dependency") is not False:
        errors.append("source repo live dependency must be false")
    if data.get("pilot_structured_draft_count") != EXPECTED_TOTAL:
        errors.append("pilot count must be 44")
    if data.get("production_knowledge_count") != 0:
        errors.append("production knowledge count must be 0")
    if data.get("candidatepack_created") is not False:
        errors.append("candidatepack_created must be false")
    if data.get("ready_for_first_batch_generation") is not False:
        errors.append("first batch generation must remain false")
    if data.get("batch_generation_unlocked") is True:
        errors.append("batch generation must remain locked")
    current_next_step = data.get("current_next_step", PILOT_JUDGE_NEXT_STEP)
    if current_next_step == BATCH_GENERATION_NEXT_STEP:
        errors.append("batch generation task cannot be current next step")
    allowed_next_steps = {
        PILOT_JUDGE_NEXT_STEP,
        SEMANTIC_REGEN_NEXT_STEP,
        SEMANTIC_JUDGE_NEXT_STEP,
        SEMANTIC_V3_JUDGE_NEXT_STEP,
        SEMANTIC_V4_JUDGE_NEXT_STEP,
        SEMANTIC_V4_1_JUDGE_NEXT_STEP,
        SEMANTIC_V4_2_JUDGE_NEXT_STEP,
        SEMANTIC_V4_3_JUDGE_NEXT_STEP,
        SEMANTIC_V4_4_JUDGE_NEXT_STEP,
        SEMANTIC_V4_5_JUDGE_NEXT_STEP,
    }
    if current_next_step not in allowed_next_steps:
        errors.append("current next step must be pilot judge review, semantic pilot regen, semantic judge go/no-go, semantic v3 judge go/no-go, semantic v4 judge go/no-go, semantic v4.1 judge go/no-go, semantic v4.2 judge go/no-go, or semantic v4.3 judge go/no-go or semantic v4.4 judge go/no-go")
    if data.get("ready_for_pilot_review") is not True:
        errors.append("pilot review should be true")
    if data.get("category_counts") != EXPECTED_CATEGORY_COUNTS:
        errors.append("category counts must be 11 each")
    if data.get("review_queue_present") is not True:
        errors.append("review queue required")
    if data.get("independent_judge_protocol_present") is not True:
        errors.append("independent judge protocol required")
    if data.get("relation_candidates_valid") is not True:
        errors.append("relation candidates must be valid")
    if data.get("hard_claim_leak_count") != 0:
        errors.append("hard claim leak count must be 0")
    if data.get("real_instance_fact_leak_count") != 0:
        errors.append("real instance fact leak count must be 0")
    if data.get("P0_00_general_kb_leak_count") != 0:
        errors.append("P0-00 GeneralKnowledgeBase leak count must be 0")
    candidates = data.get("sample_candidates", [])
    for candidate_entry in candidates:
        category = candidate_entry.get("pilot_category", "content_method")
        candidate = candidate_entry.get("candidate", {})
        errors.extend(validate_candidate(candidate, schema, category))
    return errors


def validate_workspace_route(status: dict[str, Any]) -> dict[str, Any]:
    phase = status.get("phase", {})
    current_next_step = phase.get("current_next_step")
    if current_next_step == BATCH_GENERATION_NEXT_STEP:
        fail("workspace next step must not be batch generation")
    pilot_status = status.get("pilot", {})
    if pilot_status.get("ready_for_first_batch_generation") is not False:
        fail("workspace status must not unlock first batch generation")
    if current_next_step == PILOT_JUDGE_NEXT_STEP:
        if pilot_status.get("ready_for_pilot_review") is not True:
            fail("workspace status should route to pilot review")
        return {
            "route_validation_mode": "pre_semantic_closeout_pilot_review",
            "current_workspace_next_step": current_next_step,
        }
    if current_next_step == SEMANTIC_REGEN_NEXT_STEP:
        closeout = status.get("pilot_semantic_closeout", {})
        if closeout.get("status") != "completed":
            fail("semantic closeout route requires completed closeout block")
        if closeout.get("semantic_pilot_status") != "failed":
            fail("semantic closeout route requires semantic_pilot_status failed")
        if closeout.get("current_44_reclassified_as") != SMOKE_FIXTURE_CLASSIFICATION:
            fail("semantic closeout route requires current 44 smoke fixture reclassification")
        if closeout.get("accepted_domain_knowledge_count") != 0:
            fail("semantic closeout route requires accepted_domain_knowledge_count 0")
        if closeout.get("batch_generation_unlocked") is True:
            fail("semantic closeout route must keep batch_generation_unlocked false")
        if closeout.get("ready_for_first_batch_generation") is True:
            fail("semantic closeout route must keep ready_for_first_batch_generation false")
        return {
            "route_validation_mode": "post_semantic_closeout_regen",
            "current_workspace_next_step": current_next_step,
            "current_44_reclassified_as": closeout.get("current_44_reclassified_as"),
            "accepted_domain_knowledge_count": closeout.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": closeout.get("batch_generation_unlocked"),
        }
    if current_next_step == SEMANTIC_JUDGE_NEXT_STEP:
        regen = status.get("semantic_pilot_regen", {})
        if regen.get("status") != "completed":
            fail("semantic judge route requires completed semantic_pilot_regen block")
        if regen.get("semantic_pilot_structured_draft_count") != 20:
            fail("semantic judge route requires 20 regenerated pilot drafts")
        if regen.get("accepted_domain_knowledge_count") != 0:
            fail("semantic judge route requires accepted_domain_knowledge_count 0")
        if regen.get("batch_generation_unlocked") is True:
            fail("semantic judge route must keep batch_generation_unlocked false")
        if regen.get("ready_for_first_batch_generation") is True:
            fail("semantic judge route must keep ready_for_first_batch_generation false")
        if regen.get("ready_for_semantic_pilot_judge_review") is not True:
            fail("semantic judge route requires ready_for_semantic_pilot_judge_review true")
        return {
            "route_validation_mode": "post_semantic_regen_judge_go_nogo",
            "current_workspace_next_step": current_next_step,
            "semantic_pilot_structured_draft_count": regen.get("semantic_pilot_structured_draft_count"),
            "accepted_domain_knowledge_count": regen.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": regen.get("batch_generation_unlocked"),
        }
    if current_next_step == SEMANTIC_V3_JUDGE_NEXT_STEP:
        v3 = status.get("semantic_pilot_v3", {})
        if v3.get("status") != "completed":
            fail("semantic v3 judge route requires completed semantic_pilot_v3 block")
        if v3.get("semantic_pilot_v3_structured_draft_count") != 20:
            fail("semantic v3 judge route requires 20 regenerated v3 pilot drafts")
        if v3.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v3 judge route requires accepted_domain_knowledge_count 0")
        if v3.get("batch_generation_unlocked") is True:
            fail("semantic v3 judge route must keep batch_generation_unlocked false")
        if v3.get("ready_for_first_batch_generation") is True:
            fail("semantic v3 judge route must keep ready_for_first_batch_generation false")
        if v3.get("ready_for_semantic_pilot_v3_judge_review") is not True:
            fail("semantic v3 judge route requires ready_for_semantic_pilot_v3_judge_review true")
        return {
            "route_validation_mode": "post_semantic_v3_judge_go_nogo",
            "current_workspace_next_step": current_next_step,
            "semantic_pilot_v3_structured_draft_count": v3.get("semantic_pilot_v3_structured_draft_count"),
            "accepted_domain_knowledge_count": v3.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": v3.get("batch_generation_unlocked"),
        }
    if current_next_step == SEMANTIC_V4_JUDGE_NEXT_STEP:
        v4 = status.get("semantic_pilot_v4", {})
        if v4.get("status") != "completed":
            fail("semantic v4 judge route requires completed semantic_pilot_v4 block")
        if v4.get("W7_authority_records_count") != 46:
            fail("semantic v4 judge route requires 46 W7 authority records")
        if v4.get("semantic_pilot_v4_count") != 8:
            fail("semantic v4 judge route requires 8 v4 semantic pilot drafts")
        if v4.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v4 judge route requires accepted_domain_knowledge_count 0")
        if v4.get("batch_generation_unlocked") is True:
            fail("semantic v4 judge route must keep batch_generation_unlocked false")
        if v4.get("ready_for_first_batch_generation") is True:
            fail("semantic v4 judge route must keep ready_for_first_batch_generation false")
        if v4.get("ready_for_v4_judge_review") is not True:
            fail("semantic v4 judge route requires ready_for_v4_judge_review true")
        return {
            "route_validation_mode": "post_semantic_v4_judge_go_nogo",
            "current_workspace_next_step": current_next_step,
            "W7_authority_records_count": v4.get("W7_authority_records_count"),
            "semantic_pilot_v4_count": v4.get("semantic_pilot_v4_count"),
            "accepted_domain_knowledge_count": v4.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": v4.get("batch_generation_unlocked"),
        }
    if current_next_step == SEMANTIC_V4_1_JUDGE_NEXT_STEP:
        v41 = status.get("semantic_pilot_v4_1", {})
        if v41.get("status") != "completed":
            fail("semantic v4.1 judge route requires completed semantic_pilot_v4_1 block")
        if v41.get("semantic_pilot_v4_1_count") != 8:
            fail("semantic v4.1 judge route requires 8 v4.1 semantic revision drafts")
        if v41.get("one_to_one_revision_of_v4") is not True:
            fail("semantic v4.1 judge route requires one-to-one revision of V4")
        if v41.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v4.1 judge route requires accepted_domain_knowledge_count 0")
        if v41.get("batch_generation_unlocked") is True:
            fail("semantic v4.1 judge route must keep batch_generation_unlocked false")
        if v41.get("ready_for_first_batch_generation") is True:
            fail("semantic v4.1 judge route must keep ready_for_first_batch_generation false")
        if v41.get("ready_for_semantic_pilot_v4_1_judge_review") is not True:
            fail("semantic v4.1 judge route requires ready_for_semantic_pilot_v4_1_judge_review true")
        return {
            "route_validation_mode": "post_semantic_v4_1_judge_go_nogo",
            "current_workspace_next_step": current_next_step,
            "semantic_pilot_v4_1_count": v41.get("semantic_pilot_v4_1_count"),
            "accepted_domain_knowledge_count": v41.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": v41.get("batch_generation_unlocked"),
        }
    if current_next_step == SEMANTIC_V4_2_JUDGE_NEXT_STEP:
        v42 = status.get("semantic_pilot_v4_2", {})
        if v42.get("status") != "completed":
            fail("semantic v4.2 judge route requires completed semantic_pilot_v4_2 block")
        if v42.get("semantic_pilot_v4_2_count") != 8:
            fail("semantic v4.2 judge route requires 8 v4.2 semantic revision drafts")
        if v42.get("one_to_one_revision_of_v4_1") is not True:
            fail("semantic v4.2 judge route requires one-to-one revision of V4.1")
        if v42.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v4.2 judge route requires accepted_domain_knowledge_count 0")
        if v42.get("batch_generation_unlocked") is True:
            fail("semantic v4.2 judge route must keep batch_generation_unlocked false")
        if v42.get("ready_for_first_batch_generation") is True:
            fail("semantic v4.2 judge route must keep ready_for_first_batch_generation false")
        if v42.get("ready_for_semantic_pilot_v4_2_judge_review") is not True:
            fail("semantic v4.2 judge route requires ready_for_semantic_pilot_v4_2_judge_review true")
        return {
            "route_validation_mode": "post_semantic_v4_2_judge_go_nogo",
            "current_workspace_next_step": current_next_step,
            "semantic_pilot_v4_2_count": v42.get("semantic_pilot_v4_2_count"),
            "accepted_domain_knowledge_count": v42.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": v42.get("batch_generation_unlocked"),
        }
    if current_next_step == SEMANTIC_V4_3_JUDGE_NEXT_STEP:
        v43 = status.get("semantic_pilot_v4_3", {})
        if v43.get("status") != "completed":
            fail("semantic v4.3 judge route requires completed semantic_pilot_v4_3 block")
        if v43.get("semantic_pilot_v4_3_count") != 8:
            fail("semantic v4.3 judge route requires 8 v4.3 semantic revision drafts")
        if v43.get("one_to_one_revision_of_v4_2") is not True:
            fail("semantic v4.3 judge route requires one-to-one revision of V4.2")
        if v43.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v4.3 judge route requires accepted_domain_knowledge_count 0")
        if v43.get("batch_generation_unlocked") is True:
            fail("semantic v4.3 judge route must keep batch_generation_unlocked false")
        if v43.get("ready_for_first_batch_generation") is True:
            fail("semantic v4.3 judge route must keep ready_for_first_batch_generation false")
        if v43.get("ready_for_semantic_pilot_v4_3_judge_review") is not True:
            fail("semantic v4.3 judge route requires ready_for_semantic_pilot_v4_3_judge_review true")
        return {
            "route_validation_mode": "post_semantic_v4_3_judge_go_nogo",
            "current_workspace_next_step": current_next_step,
            "semantic_pilot_v4_3_count": v43.get("semantic_pilot_v4_3_count"),
            "accepted_domain_knowledge_count": v43.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": v43.get("batch_generation_unlocked"),
        }
    if current_next_step == SEMANTIC_V4_4_JUDGE_NEXT_STEP:
        v44 = status.get("semantic_pilot_v4_4", {})
        if v44.get("status") != "completed":
            fail("semantic v4.4 judge route requires completed semantic_pilot_v4_4 block")
        if v44.get("semantic_pilot_v4_4_count") != 8:
            fail("semantic v4.4 judge route requires 8 v4.4 semantic revision drafts")
        if v44.get("one_to_one_revision_of_v4_3") is not True:
            fail("semantic v4.4 judge route requires one-to-one revision of V4.3")
        if v44.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v4.4 judge route requires accepted_domain_knowledge_count 0")
        if v44.get("batch_generation_unlocked") is True:
            fail("semantic v4.4 judge route must keep batch_generation_unlocked false")
        if v44.get("ready_for_first_batch_generation") is True:
            fail("semantic v4.4 judge route must keep ready_for_first_batch_generation false")
        if v44.get("ready_for_semantic_pilot_v4_4_judge_review") is not True:
            fail("semantic v4.4 judge route requires ready_for_semantic_pilot_v4_4_judge_review true")
        return {
            "route_validation_mode": "post_semantic_v4_4_judge_go_nogo",
            "current_workspace_next_step": current_next_step,
            "semantic_pilot_v4_4_count": v44.get("semantic_pilot_v4_4_count"),
            "accepted_domain_knowledge_count": v44.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": v44.get("batch_generation_unlocked"),
        }

    if current_next_step == SEMANTIC_V4_5_JUDGE_NEXT_STEP:
        v45 = status.get("semantic_pilot_v4_5", {})
        if v45.get("task_id") != "CODEX-SEMANTIC-PILOT-V4_4-CONDITIONAL-PASS-CLOSEOUT-AND-V4_5-CAPSULE-RICH-BODY-INTEGRATION-001" or v45.get("status") != "completed":
            fail("semantic v4.5 judge route requires completed semantic_pilot_v4_5 block")
        if v45.get("semantic_pilot_v4_5_count") != 8:
            fail("semantic v4.5 judge route requires 8 v4.5 semantic revision drafts")
        if v45.get("one_to_one_revision_of_v4_4") is not True:
            fail("semantic v4.5 judge route requires one-to-one revision of V4.4")
        if v45.get("capsule_rich_body_alignment_valid_count") != 8:
            fail("semantic v4.5 judge route requires 8 capsule/rich-body alignments")
        if v45.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v4.5 judge route requires accepted_domain_knowledge_count 0")
        if v45.get("batch_generation_unlocked") is True:
            fail("semantic v4.5 judge route must keep batch_generation_unlocked false")
        if v45.get("ready_for_first_batch_generation") is True:
            fail("semantic v4.5 judge route must keep ready_for_first_batch_generation false")
        if v45.get("ready_for_semantic_pilot_v4_5_judge_review") is not True:
            fail("semantic v4.5 judge route requires ready_for_semantic_pilot_v4_5_judge_review true")
        return {
            "route_validation_mode": "post_semantic_v4_5_judge_go_nogo",
            "current_workspace_next_step": current_next_step,
            "semantic_pilot_v4_5_count": v45.get("semantic_pilot_v4_5_count"),
            "accepted_domain_knowledge_count": v45.get("accepted_domain_knowledge_count"),
            "batch_generation_unlocked": v45.get("batch_generation_unlocked"),
        }
    fail("workspace next step must be a known pilot/semantic judge handoff and must not be batch generation")


def validate_live(
    workspace: Path,
    pilot_root: Path,
    contracts_root: Path,
    brief_pack_root: Path,
    fixtures_root: Path,
    report_out: Path | None,
) -> dict[str, Any]:
    schema = load_json(contracts_root / "codex_generation_output_contract.v0.1.schema.json")
    manifest = load_yaml(pilot_root / "pilot_manifest.yaml")["pilot_manifest"]
    cards = load_yaml(pilot_root / "pilot_knowledge_candidate_cards.yaml")["pilot_knowledge_candidate_cards"]
    body_blocks = load_yaml(pilot_root / "pilot_rich_body_blocks.yaml")["pilot_rich_body_blocks"]
    review_queue = load_yaml(pilot_root / "pilot_review_queue.yaml")["pilot_review_queue"]
    semantic_report = load_json(pilot_root / "pilot_semantic_alignment_report.json")
    entailment_report = load_json(pilot_root / "pilot_body_entailment_report.json")
    dedupe_report = load_json(pilot_root / "pilot_dedupe_report.json")
    receipt = load_json(pilot_root / "pilot_generation_receipt.json")

    required_inputs = [
        contracts_root / "codex_body_entailment_policy.v0.1.yaml",
        contracts_root / "codex_expert_synthesis_source_policy.v0.1.yaml",
        brief_pack_root / "00_brief_pack_manifest.yaml",
        brief_pack_root / "00_pilot_sampling_plan.yaml",
        brief_pack_root / "00_microbatch_plan.csv",
        brief_pack_root / "00_batch_allocation_matrix.yaml",
    ]
    for path in required_inputs:
        if not path.exists():
            fail(f"missing required input: {path}")

    if manifest.get("task_id") != EXPECTED_TASK_ID:
        fail("pilot manifest task id mismatch")
    if manifest.get("source_repo_live_dependency") is not False:
        fail("pilot manifest source repo dependency must be false")
    if manifest.get("source_repo_live_accessed") is not False:
        fail("pilot manifest source repo access must be false")
    if manifest.get("pilot_structured_draft_count") != EXPECTED_TOTAL:
        fail("pilot manifest count must be 44")
    if manifest.get("production_knowledge_count") != 0:
        fail("production knowledge count must be 0")
    if manifest.get("ready_for_pilot_review") is not True:
        fail("ready_for_pilot_review must be true")
    if manifest.get("ready_for_first_batch_generation") is not False:
        fail("ready_for_first_batch_generation must be false")
    if manifest.get("recommended_next_step") != "CODEX-PILOT-JUDGE-REVIEW-AND-GO-NOGO-001":
        fail("recommended next step must be pilot judge review")

    entries = cards.get("candidates", [])
    if len(entries) != EXPECTED_TOTAL:
        fail("pilot candidate count must be 44")
    category_counts = Counter(entry.get("pilot_category") for entry in entries)
    if dict(category_counts) != EXPECTED_CATEGORY_COUNTS:
        fail(f"pilot category counts mismatch: {dict(category_counts)}")

    candidate_ids: set[str] = set()
    assignment_refs: set[str] = set()
    cluster_refs: set[str] = set()
    schema_errors: dict[str, list[str]] = {}
    rich_body_by_id = {block["candidate_id"]: block for block in body_blocks.get("blocks", [])}
    for entry in entries:
        category = entry["pilot_category"]
        candidate = entry["candidate"]
        candidate_id = candidate["identity"]["candidate_id"]
        if candidate_id in candidate_ids:
            fail(f"duplicate candidate id: {candidate_id}")
        candidate_ids.add(candidate_id)
        assignment_refs.add(candidate["w7_trace"]["generation_assignment_id"])
        cluster_refs.add(candidate["w7_trace"]["canonical_cluster_id"])
        errors = validate_candidate(candidate, schema, category)
        if errors:
            schema_errors[candidate_id] = errors
        if candidate_id not in rich_body_by_id:
            fail(f"missing rich body block: {candidate_id}")
        if rich_body_by_id[candidate_id]["body_text"] != candidate["rich_body"]["body_text"]:
            fail(f"rich body block mismatch: {candidate_id}")
    if schema_errors:
        fail(f"candidate validation failed: {schema_errors}")
    if len(assignment_refs) < 14 or not EXPECTED_ASSIGNMENTS.issubset(assignment_refs):
        fail(f"assignment coverage invalid: {sorted(assignment_refs)}")
    if len(cluster_refs) < 16:
        fail(f"canonical cluster coverage too small: {len(cluster_refs)}")

    relation_result = validate_relation_candidates(
        pilot_root / "pilot_relation_candidates.csv",
        candidate_ids,
    )
    queue_entries = review_queue.get("items", [])
    if len(queue_entries) != EXPECTED_TOTAL:
        fail("review queue must include all 44 candidates")
    if {item["candidate_id"] for item in queue_entries} != candidate_ids:
        fail("review queue candidate id set mismatch")
    if not (pilot_root / "pilot_independent_judge_protocol.md").exists():
        fail("missing independent judge protocol")

    if semantic_report.get("status") != "PASS" or semantic_report.get("candidate_count") != EXPECTED_TOTAL:
        fail("semantic alignment report invalid")
    if entailment_report.get("structural_status") != "PASS":
        fail("body entailment structural status must pass")
    if entailment_report.get("requires_independent_judge_or_human_review") is not True:
        fail("body entailment must carry forward judge/human review")
    if dedupe_report.get("duplicate_blocking_count") != 0:
        fail("dedupe blocking count must be 0")
    if receipt.get("generated_knowledge_count") != 0:
        fail("receipt generated knowledge count must be 0")
    if receipt.get("candidatepack_created") is not False:
        fail("receipt candidatepack_created must be false")

    status = load_yaml(workspace / "project-infra/current_workspace_status.yaml")
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"workspace readiness true flags: {bad}")
    route_result = validate_workspace_route(status)

    positive = load_yaml(fixtures_root / "positive_valid_pilot_minimal.yaml")
    positive_errors = validate_fixture_model(positive, schema)
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name), schema)
        negative_results[name] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")

    report = {
        "status": "PASS",
        "task_id": EXPECTED_TASK_ID,
        "expected_HEAD_before": EXPECTED_HEAD_BEFORE,
        "pilot_structured_draft_count": EXPECTED_TOTAL,
        "production_knowledge_count": 0,
        "pilot_category_counts": dict(category_counts),
        "generation_assignment_coverage_count": len(assignment_refs),
        "canonical_cluster_coverage_count": len(cluster_refs),
        "schema_validation_result": "PASS",
        "rich_body_quality_result": "PASS",
        "body_entailment_structural_result": "PASS",
        "body_entailment_review_queue": "present",
        "independent_judge_protocol": "present",
        "dedupe_result": "PASS",
        "relation_candidates_result": relation_result,
        "hard_claim_leak_count": 0,
        "real_instance_fact_leak_count": 0,
        "P0_00_general_kb_leak_count": 0,
        "source_repo_live_accessed": False,
        "candidatepack_created": False,
        "KE_touched": False,
        "serving_touched": False,
        "RAG_touched": False,
        "DIFY_touched": False,
        "ready_for_pilot_review": True,
        "ready_for_first_batch_generation": False,
        "historical_pilot_recommended_next_step": PILOT_JUDGE_NEXT_STEP,
        "recommended_next_step": route_result["current_workspace_next_step"],
        **route_result,
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "positive_fixture_passed": True,
        "negative_fixtures_fail_closed": True,
        "negative_results": negative_results,
    }
    if report_out:
        write_json(report_out, report)
    return report


def run_selftest() -> dict[str, Any]:
    workspace = Path(tempfile.mkdtemp(prefix="codex-pilot-selftest-"))
    contracts = workspace / "contracts"
    fixtures = workspace / "fixtures"
    contracts.mkdir(parents=True)
    fixtures.mkdir(parents=True)
    schema_path = Path("01_generation_contracts/codex_generation_output_contract.v0.1.schema.json")
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    else:
        schema = {"type": "object", "additionalProperties": False, "required": []}
    (contracts / "codex_generation_output_contract.v0.1.schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    positive = build_fixture_model()
    (fixtures / "positive_valid_pilot_minimal.yaml").write_text(
        yaml.safe_dump(positive, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    for name in NEGATIVE_FIXTURES:
        model = build_fixture_model()
        mutate_fixture_for_negative(model, name)
        (fixtures / name).write_text(
            yaml.safe_dump(model, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    positive_errors = validate_fixture_model(positive, schema)
    if positive_errors:
        fail(f"selftest positive failed: {positive_errors}")
    failed_closed = 0
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures / name), schema)
        if not errors:
            fail(f"selftest negative passed unexpectedly: {name}")
        failed_closed += 1
    return {
        "status": "PASS",
        "positive_fixture_count": 1,
        "negative_fixture_count": failed_closed,
        "negative_fixtures_fail_closed": True,
    }


def build_candidate() -> dict[str, Any]:
    section_refs = ["definition", "applicable_when", "output_effect"]
    body = (
        "This pilot draft describes a repeatable content method for planning a theme before any publishable claim is made. "
        "The method starts from a neutral styling observation, identifies the shopper question it can answer, and turns that question into a short narrative path. "
        "It is applicable when the team needs a structured draft for review, not when a verified product fact, measured effect, named example, or final landing decision is required. "
        "The expected effect is a reviewable note with clear boundaries, visible evidence needs, and no downstream readiness signal. "
        "The risk boundary is that reviewers must reject unsupported performance language and keep unresolved facts in the review queue."
    )
    return {
        "identity": {
            "candidate_id": "PILOT-CONTENT-METHOD-001",
            "candidate_name": "Pilot content method sample",
            "schema_version": "v0.1",
            "generation_status": "gpt_generated_structured_draft",
        },
        "w7_trace": {
            "w7_map_digest": EXPECTED_W7_DIGEST,
            "founder_overlay_digest": EXPECTED_FOUNDER_DIGEST,
            "canonical_cluster_id": "mkc_001",
            "generation_assignment_id": "GA-001",
            "input_digest": "0" * 64,
        },
        "ownership": {
            "candidate_kind": "general_knowledge_candidate",
            "proposed_target_owner": "GeneralKnowledgeBase",
            "target_owner_reason": "General method draft for later review.",
        },
        "source_policy": {
            "source_type": "human_reviewed_expert_synthesis",
            "source_type_boundary_status": "source_type_is_intake_classification_only",
            "source_refs": ["02_generation_brief_pack/00_pilot_sampling_plan.yaml"],
            "expert_synthesis_allowed": True,
            "expert_synthesis_policy_ref": "01_generation_contracts/codex_expert_synthesis_source_policy.v0.1.yaml",
        },
        "layer_annotation": {
            "declared_layer": "method draft pending review",
            "target_layer_candidate": "L2_PlayCard_candidate",
            "allowed_landing_layers": ["L2_PlayCard_candidate", "DraftBacklog"],
            "forbidden_landing_layers": ["GovernanceContract_candidate", "SourceGapLedger"],
            "layer_confidence": 0.74,
            "layer_boundary_note": "Landing remains provisional until review.",
            "if_layer_uncertain_route": "decision_required",
        },
        "semantic_structure": {
            "definition": "A repeatable planning method for shaping a reviewable content draft.",
            "applicable_when": "Use when a team needs a safe draft structure before fact review.",
            "not_applicable_when": "Do not use for verified product facts or measured effects.",
            "output_effect": "Creates a structured draft for judge and human review.",
            "risk_boundary": "Unsupported claims must be held for review or source work.",
            "evidence_requirement": "Requires review evidence before any downstream use.",
        },
        "rich_body": {
            "body_text": body,
            "body_sections": [
                {"heading": "Use", "text": "Use the draft as a planning note for review.", "proposition_refs": section_refs},
                {"heading": "Boundary", "text": "Keep unresolved facts outside publishable language.", "proposition_refs": ["risk_boundary", "evidence_requirement"]},
            ],
            "body_proposition_refs": section_refs,
        },
        "dedupe": {
            "duplicate_check_key": "pilot-content-method-001",
            "semantic_fingerprint": "content-method-neutral-planning",
            "proposition_fingerprint": "definition-applicable-output",
            "runtime_effect_fingerprint": "reviewable-draft-no-readiness",
        },
        "readiness_flags": {
            "candidatepack_ready": False,
            "KE_ready": False,
            "serving_ready": False,
            "RAG_ready": False,
            "DIFY_ready": False,
            "generation_eligible": False,
            "production_servable": False,
            "production_ready": False,
        },
        "state_machine": {
            "current_state": "gpt_generated_structured_draft",
            "route_after_review": "draft_backlog",
            "route_reason": "Pilot output requires judge and human review before any next-stage use.",
        },
        "review": {"human_review_required": True, "reviewer_status": "pending_human_review"},
    }


def build_fixture_model() -> dict[str, Any]:
    return {
        "pilot_fixture": {
            "task_id": EXPECTED_TASK_ID,
            "source_repo_live_dependency": False,
            "source_repo_live_accessed": False,
            "pilot_structured_draft_count": EXPECTED_TOTAL,
            "production_knowledge_count": 0,
            "candidatepack_created": False,
            "ready_for_pilot_review": True,
            "ready_for_first_batch_generation": False,
            "batch_generation_unlocked": False,
            "current_next_step": PILOT_JUDGE_NEXT_STEP,
            "category_counts": EXPECTED_CATEGORY_COUNTS,
            "review_queue_present": True,
            "independent_judge_protocol_present": True,
            "relation_candidates_valid": True,
            "hard_claim_leak_count": 0,
            "real_instance_fact_leak_count": 0,
            "P0_00_general_kb_leak_count": 0,
            "sample_candidates": [
                {"pilot_category": "content_method", "candidate": build_candidate()},
            ],
        }
    }


def mutate_fixture_for_negative(model: dict[str, Any], name: str) -> None:
    data = model["pilot_fixture"]
    candidate = data["sample_candidates"][0]["candidate"]
    if name == "negative_wrong_count.yaml":
        data["pilot_structured_draft_count"] = 43
    elif name == "negative_missing_category.yaml":
        data["category_counts"] = {"content_method": 44}
    elif name == "negative_readiness_true.yaml":
        candidate["readiness_flags"]["generation_eligible"] = True
    elif name == "negative_schema_invalid_candidate.yaml":
        candidate["ownership"].pop("candidate_kind", None)
    elif name == "negative_empty_rich_body.yaml":
        candidate["rich_body"]["body_text"] = ""
    elif name == "negative_body_without_proposition_refs.yaml":
        candidate["rich_body"]["body_sections"][0]["proposition_refs"] = []
    elif name == "negative_missing_judge_queue.yaml":
        data["review_queue_present"] = False
    elif name == "negative_hard_claim_expert_synthesis.yaml":
        candidate["rich_body"]["body_text"] += " This wording guarantees a body effect."
    elif name == "negative_real_instance_fact_leak.yaml":
        candidate["rich_body"]["body_text"] += " It cites a real brand as proof."
    elif name == "negative_p0_00_general_kb_leak.yaml":
        data["sample_candidates"][0]["pilot_category"] = "control_plane_governance"
        candidate["ownership"]["proposed_target_owner"] = "GeneralKnowledgeBase"
    elif name == "negative_candidatepack_created.yaml":
        data["candidatepack_created"] = True
    elif name == "negative_source_repo_dependency_true.yaml":
        data["source_repo_live_dependency"] = True
    elif name == "negative_relation_unknown_candidate.yaml":
        data["relation_candidates_valid"] = False
    elif name == "negative_batch_generation_next_step.yaml":
        data["current_next_step"] = BATCH_GENERATION_NEXT_STEP


def main() -> int:
    if not __debug__:
        print("FAIL-CLOSED: optimized Python mode is not allowed for this checker", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--pilot-root", default="03_pilot")
    parser.add_argument("--contracts-root", default="01_generation_contracts")
    parser.add_argument("--brief-pack-root", default="02_generation_brief_pack")
    parser.add_argument("--fixtures-root", default="ci/fixtures/codex_generation_cross_type_pilot")
    parser.add_argument("--report-out")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            result = run_selftest()
        else:
            workspace = Path(args.workspace_root)
            result = validate_live(
                workspace=workspace,
                pilot_root=workspace / args.pilot_root,
                contracts_root=workspace / args.contracts_root,
                brief_pack_root=workspace / args.brief_pack_root,
                fixtures_root=workspace / args.fixtures_root,
                report_out=workspace / args.report_out if args.report_out else None,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except PilotCheckError as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
