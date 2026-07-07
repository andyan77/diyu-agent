#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

V4_5_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_4-CONDITIONAL-PASS-CLOSEOUT-AND-V4_5-CAPSULE-RICH-BODY-INTEGRATION-001"
V4_6_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_5-CLOSEOUT-TYPE-SPECIFIC-RICH-BODY-COMPILER-AND-V4_6-REWRITE-001"
V4_7_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_6-CONDITIONAL-REPAIR-CLOSEOUT-AND-V4_7-SEMANTIC-CLEANUP-001"
TASK_ID = "CODEX-SEMANTIC-PILOT-REGEN-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-JUDGE-GO-NOGO-001"
V3_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V3-JUDGE-GO-NOGO-001"
V4_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4-JUDGE-GO-NOGO-001"
V4_1_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_1-JUDGE-GO-NOGO-001"
V4_2_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_2-JUDGE-GO-NOGO-001"
V4_3_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_3-JUDGE-GO-NOGO-001"
V4_4_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_4-JUDGE-GO-NOGO-001"
V4_5_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_5-JUDGE-GO-NOGO-001"
V4_6_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_6-JUDGE-GO-NOGO-001"
V4_7_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_7-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_TOTAL = 20
EXPECTED_CATEGORY_COUNTS = {
    "content_method": 5,
    "apparel_claim_boundary": 5,
    "display_to_content": 5,
    "control_plane_governance": 5,
}
EXPECTED_W7_DIGEST = "dd1503011a3a3f4cba9a663e50417037e85e8f09001edfc98c214919284d6c7c"
EXPECTED_FOUNDER_DIGEST = "823ff7ab0a88aa41e235d03b09515b4303c7e4fd420af6619bcddb1cad96ea48"
FORBIDDEN_PREDICATES = {
    "generic",
    "review_adjacent",
    "review_adjacent_method_boundary",
    "placeholder",
    "related_to",
    "similar_to",
}
ALLOWED_PROVENANCE = {
    "expert_synthesis_draft",
    "founder_overlay_governance_basis",
    "source_gap_seed",
    "decision_packet_seed",
}
INDUSTRY_ELEMENTS = {
    "apparel_object",
    "retail_scene",
    "content_action",
    "display_or_styling_action",
    "evidence_or_claim_boundary",
    "downstream_output_implication",
    "failure_mode",
    "operator_decision",
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
    "negative_wrong_category_distribution.yaml",
    "negative_readiness_true.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked.yaml",
    "negative_duplicate_proposition_signature.yaml",
    "negative_duplicate_normalized_body.yaml",
    "negative_hash_only_fingerprint.yaml",
    "negative_missing_cluster_entailment.yaml",
    "negative_low_industry_density.yaml",
    "negative_generic_relation_predicate.yaml",
    "negative_missing_min_two_relations.yaml",
    "negative_source_status_conflation.yaml",
    "negative_hard_claim_expert_synthesis.yaml",
    "negative_real_instance_fact_leak.yaml",
    "negative_p0_00_general_kb_leak.yaml",
    "negative_missing_judge_queue.yaml",
    "negative_source_repo_dependency_true.yaml",
    "negative_external_drive_dependency_true.yaml",
    "negative_batch_generation_next_step.yaml",
]


class SemanticRegenError(Exception):
    pass


def fail(message: str) -> None:
    raise SemanticRegenError(message)

def assert_false(value: Any, label: str) -> None:
    if value is True or str(value).lower() == "true":
        fail(f"{label} must be false")



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


def validate_candidate_entry(entry: dict[str, Any], schema: dict[str, Any], relations_by_candidate: dict[str, list[dict[str, str]]]) -> list[str]:
    errors: list[str] = []
    category = entry.get("pilot_category")
    candidate = entry.get("candidate", {})
    schema_errors = validate_schema_shape(candidate, schema)
    if schema_errors:
        return schema_errors
    cid = candidate["identity"]["candidate_id"]
    if candidate["identity"]["generation_status"] != "gpt_generated_structured_draft":
        errors.append(f"{cid}: wrong generation status")
    if candidate["w7_trace"]["w7_map_digest"] != EXPECTED_W7_DIGEST:
        errors.append(f"{cid}: W7 digest mismatch")
    if candidate["w7_trace"]["founder_overlay_digest"] != EXPECTED_FOUNDER_DIGEST:
        errors.append(f"{cid}: founder overlay digest mismatch")
    if any(value is not False for value in candidate["readiness_flags"].values()):
        errors.append(f"{cid}: readiness flag true")

    source_status = entry.get("source_status", {})
    provenance = source_status.get("provenance_class")
    human_status = source_status.get("human_review_status")
    human_method = source_status.get("human_reviewed_method")
    if provenance not in ALLOWED_PROVENANCE:
        errors.append(f"{cid}: invalid provenance class")
    if human_status not in {"pending", "reviewed", "rejected"}:
        errors.append(f"{cid}: invalid human review status")
    if human_status == "pending" and human_method is not False:
        errors.append(f"{cid}: pending human status must have human_reviewed_method false")
    if provenance == "human_reviewed_expert_synthesis" and human_status == "pending":
        errors.append(f"{cid}: source status conflation")

    distinct = entry.get("semantic_distinctness", {})
    for key in ["normalized_proposition_signature", "normalized_body_signature", "normalized_body_mechanism_signature", "semantic_fingerprint"]:
        if not distinct.get(key):
            errors.append(f"{cid}: missing {key}")
    relation_set = distinct.get("relation_predicate_set", [])
    if not relation_set:
        errors.append(f"{cid}: missing relation predicate set")

    entailment = entry.get("cluster_entailment", {})
    required_cluster_fields = [
        "cluster_specific_mechanism",
        "cluster_specific_object_or_action",
        "cluster_specific_risk_boundary",
        "cluster_specific_evidence_requirement",
        "cluster_specific_output_effect",
    ]
    present = [field for field in required_cluster_fields if entailment.get(field)]
    if len(present) < 5:
        errors.append(f"{cid}: missing cluster entailment required fields")
    if int(entailment.get("cluster_specific_elements_count", 0)) < 4:
        errors.append(f"{cid}: cluster specific element count below 4")

    rich = candidate["rich_body"]
    body_text = rich["body_text"]
    if len(body_text) < 900:
        errors.append(f"{cid}: rich body below 900 chars")
    density = entry.get("industry_density", {})
    element_types = set(density.get("element_types_present", []))
    if len(element_types & INDUSTRY_ELEMENTS) < 6:
        errors.append(f"{cid}: industry element coverage below 6")
    if density.get("review_instruction_body") is True:
        errors.append(f"{cid}: body is review instruction")
    if float(density.get("boilerplate_ratio", 1.0)) > 0.12:
        errors.append(f"{cid}: boilerplate ratio too high")

    relations = relations_by_candidate.get(cid, [])
    if len(relations) < 2:
        errors.append(f"{cid}: fewer than two relation candidates")
    for relation in relations:
        predicate = relation.get("relation_predicate", "")
        if predicate in FORBIDDEN_PREDICATES:
            errors.append(f"{cid}: forbidden relation predicate {predicate}")
        if relation.get("contains_real_instance_fact", "").lower() != "false":
            errors.append(f"{cid}: relation real instance fact leak")

    all_text = candidate_text(candidate)
    if text_contains(HARD_CLAIM_PATTERNS, all_text) and candidate["source_policy"]["expert_synthesis_allowed"] is True:
        errors.append(f"{cid}: hard claim expert synthesis leak")
    if text_contains(REAL_INSTANCE_PATTERNS, all_text):
        errors.append(f"{cid}: real instance fact leak")
    if category == "control_plane_governance" and candidate["ownership"]["proposed_target_owner"] == "GeneralKnowledgeBase":
        errors.append(f"{cid}: P0-00/control-plane routed to GeneralKnowledgeBase")
    return errors


def read_relations(path: Path) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
    if not path.exists():
        fail(f"missing relation csv: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    required = {"relation_id", "candidate_id", "target_ref", "relation_predicate", "relation_note", "contains_real_instance_fact"}
    if not rows:
        fail("relation csv is empty")
    if set(rows[0]) != required:
        fail(f"relation csv fields mismatch: {sorted(rows[0])}")
    for row in rows:
        by_candidate[row["candidate_id"]].append(row)
    return rows, by_candidate


def validate_status(status: dict[str, Any]) -> None:
    phase = status.get("phase", {})
    if phase.get("current_next_step") == BATCH_NEXT_STEP:
        fail("batch generation must not be next step")
    current_next_step = phase.get("current_next_step")
    if current_next_step not in {NEXT_STEP, V3_NEXT_STEP, V4_NEXT_STEP, V4_1_NEXT_STEP, V4_2_NEXT_STEP, V4_3_NEXT_STEP, V4_4_NEXT_STEP, V4_5_NEXT_STEP, V4_6_NEXT_STEP, V4_7_NEXT_STEP}:
        fail("workspace next step must be semantic pilot judge go/no-go, semantic pilot v3 judge go/no-go, semantic pilot v4 judge go/no-go, semantic pilot v4.1 judge go/no-go, semantic pilot v4.2 judge go/no-go, or semantic pilot v4.3 judge go/no-go or semantic pilot v4.4 judge go/no-go")
    regen = status.get("semantic_pilot_regen", {})
    if regen.get("task_id") != TASK_ID or regen.get("status") != "completed":
        fail("semantic_pilot_regen status block missing")
    if regen.get("semantic_pilot_structured_draft_count") != EXPECTED_TOTAL:
        fail("semantic pilot regen count must be 20")
    if regen.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must be 0")
    if regen.get("batch_generation_unlocked") is True:
        fail("batch_generation_unlocked must be false")
    if regen.get("ready_for_first_batch_generation") is True:
        fail("ready_for_first_batch_generation must be false")
    if current_next_step == V3_NEXT_STEP:
        v3 = status.get("semantic_pilot_v3", {})
        if v3.get("status") != "completed":
            fail("semantic v3 judge route requires completed semantic_pilot_v3 block")
        if v3.get("semantic_pilot_v3_structured_draft_count") != 20:
            fail("semantic v3 judge route requires 20 v3 semantic pilot drafts")
        if v3.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v3 judge route requires accepted_domain_knowledge_count 0")
        if v3.get("batch_generation_unlocked") is True:
            fail("semantic v3 judge route must keep batch_generation_unlocked false")
        if v3.get("ready_for_first_batch_generation") is True:
            fail("semantic v3 judge route must keep ready_for_first_batch_generation false")
    if current_next_step == V4_NEXT_STEP:
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
    if current_next_step == V4_1_NEXT_STEP:
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
    if current_next_step == V4_2_NEXT_STEP:
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
    if current_next_step == V4_3_NEXT_STEP:
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
    if current_next_step == V4_4_NEXT_STEP:
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
    if current_next_step == V4_5_NEXT_STEP:
        validate_v45_status_block(status)
    if current_next_step == V4_6_NEXT_STEP:
        validate_v46_status_block(status)
    if current_next_step == V4_7_NEXT_STEP:
        validate_v47_status_block(status)
    readiness = status.get("readiness", {})
    bad = {key: value for key, value in readiness.items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")


def validate_v45_status_block(status: dict[str, Any]) -> None:
    phase = status.get("phase", {})
    if phase.get("previous_step") != V4_5_TASK_ID:
        fail("semantic v4.5 judge route requires V4.5 integration task as previous_step")
    v45 = status.get("semantic_pilot_v4_5", {})
    if v45.get("task_id") != V4_5_TASK_ID or v45.get("status") != "completed":
        fail("semantic v4.5 judge route requires completed semantic_pilot_v4_5 block")
    if v45.get("semantic_pilot_v4_5_count") != 8:
        fail("semantic v4.5 judge route requires 8 v4.5 semantic revision drafts")
    if v45.get("one_to_one_revision_of_v4_4") is not True:
        fail("semantic v4.5 judge route requires one-to-one revision of V4.4")
    if v45.get("capsule_rich_body_alignment_valid_count") != 8:
        fail("semantic v4.5 judge route requires 8 capsule/rich-body alignments")
    if v45.get("accepted_domain_knowledge_count") != 0:
        fail("semantic v4.5 judge route requires accepted_domain_knowledge_count 0")
    assert_false(v45.get("batch_generation_unlocked"), "semantic v4.5 judge route batch_generation_unlocked")
    assert_false(v45.get("ready_for_first_batch_generation"), "semantic v4.5 judge route ready_for_first_batch_generation")
    if v45.get("ready_for_semantic_pilot_v4_5_judge_review") is not True:
        fail("semantic v4.5 judge route requires ready_for_semantic_pilot_v4_5_judge_review true")


def validate_v46_status_block(status: dict[str, Any]) -> None:
    phase = status.get("phase", {})
    if phase.get("previous_step") != V4_6_TASK_ID:
        fail("semantic v4.6 judge route requires V4.6 compiler rewrite task as previous_step")
    v46 = status.get("semantic_pilot_v4_6", {})
    if v46.get("task_id") != V4_6_TASK_ID or v46.get("status") != "completed":
        fail("semantic v4.6 judge route requires completed semantic_pilot_v4_6 block")
    if v46.get("semantic_pilot_v4_6_count") != 8:
        fail("semantic v4.6 judge route requires 8 v4.6 semantic revision drafts")
    if v46.get("one_to_one_revision_of_v4_5") is not True:
        fail("semantic v4.6 judge route requires one-to-one revision of V4.5")
    if v46.get("compiler_shape_valid_count") != 8:
        fail("semantic v4.6 judge route requires 8 valid compiler shapes")
    if v46.get("accepted_domain_knowledge_count") != 0:
        fail("semantic v4.6 judge route requires accepted_domain_knowledge_count 0")
    assert_false(v46.get("batch_generation_unlocked"), "semantic v4.6 judge route batch_generation_unlocked")
    assert_false(v46.get("ready_for_first_batch_generation"), "semantic v4.6 judge route ready_for_first_batch_generation")
    if v46.get("ready_for_semantic_pilot_v4_6_judge_review") is not True:
        fail("semantic v4.6 judge route requires ready_for_semantic_pilot_v4_6_judge_review true")



def validate_v47_status_block(status: dict[str, Any]) -> None:
    phase = status.get("phase", {})
    if phase.get("previous_step") != V4_7_TASK_ID:
        fail("semantic v4.7 judge route requires V4.7 semantic cleanup task as previous_step")
    v47 = status.get("semantic_pilot_v4_7", {})
    if v47.get("task_id") != V4_7_TASK_ID or v47.get("status") != "completed":
        fail("semantic v4.7 judge route requires completed semantic_pilot_v4_7 block")
    if v47.get("semantic_pilot_v4_7_count") != 8:
        fail("semantic v4.7 judge route requires 8 v4.7 semantic cleanup drafts")
    if v47.get("one_to_one_revision_of_v4_6") is not True:
        fail("semantic v4.7 judge route requires one-to-one revision of V4.6")
    if v47.get("capsule_forbidden_term_count") != 0:
        fail("semantic v4.7 judge route requires zero capsule forbidden terms")
    if v47.get("complete_rich_body_valid_count") != 8:
        fail("semantic v4.7 judge route requires 8 complete rich bodies")
    if v47.get("accepted_domain_knowledge_count") != 0:
        fail("semantic v4.7 judge route requires accepted_domain_knowledge_count 0")
    assert_false(v47.get("batch_generation_unlocked"), "semantic v4.7 judge route batch_generation_unlocked")
    assert_false(v47.get("ready_for_first_batch_generation"), "semantic v4.7 judge route ready_for_first_batch_generation")
    if v47.get("ready_for_semantic_pilot_v4_7_judge_review") is not True:
        fail("semantic v4.7 judge route requires ready_for_semantic_pilot_v4_7_judge_review true")

def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_regen_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("source_repo_live_dependency") is not False:
        errors.append("source repo dependency must be false")
    if data.get("source_repo_live_accessed") is not False:
        errors.append("source repo live accessed must be false")
    if data.get("external_drive_dependency") is not False:
        errors.append("external drive dependency must be false")
    if data.get("external_drive_accessed") is not False:
        errors.append("external drive accessed must be false")
    if data.get("semantic_pilot_structured_draft_count") != EXPECTED_TOTAL:
        errors.append("semantic pilot count must be 20")
    if data.get("category_counts") != EXPECTED_CATEGORY_COUNTS:
        errors.append("category counts must be 5 each")
    if data.get("accepted_domain_knowledge_count") != 0:
        errors.append("accepted domain knowledge count must be 0")
    if data.get("batch_generation_unlocked") is not False:
        errors.append("batch generation must remain locked")
    if data.get("ready_for_first_batch_generation") is not False:
        errors.append("first batch generation must remain false")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") not in {NEXT_STEP, V3_NEXT_STEP, V4_NEXT_STEP, V4_1_NEXT_STEP, V4_2_NEXT_STEP, V4_3_NEXT_STEP, V4_4_NEXT_STEP, V4_5_NEXT_STEP, V4_6_NEXT_STEP, V4_7_NEXT_STEP}:
        errors.append("next step must be semantic pilot judge go/no-go, semantic pilot v3 judge go/no-go, semantic pilot v4 judge go/no-go, semantic pilot v4.1 judge go/no-go, semantic pilot v4.2 judge go/no-go, or semantic pilot v4.3 judge go/no-go or semantic pilot v4.4 judge go/no-go")
    for key in [
        "normalized_proposition_duplicate_count",
        "normalized_body_duplicate_count",
        "semantic_fingerprint_duplicate_count",
        "hard_claim_leak_count",
        "real_instance_fact_leak_count",
        "P0_00_general_kb_leak_count",
        "forbidden_relation_predicate_count",
    ]:
        if data.get(key) != 0:
            errors.append(f"{key} must be 0")
    if data.get("candidates_with_min_two_relations") != EXPECTED_TOTAL:
        errors.append("all candidates must have min two relations")
    if data.get("cluster_entailment_pass_count") != EXPECTED_TOTAL:
        errors.append("all candidates must pass cluster entailment")
    if data.get("industry_density_pass_count") != EXPECTED_TOTAL:
        errors.append("all candidates must pass industry density")
    if data.get("source_status_disambiguation_pass_count") != EXPECTED_TOTAL:
        errors.append("all candidates must pass source status disambiguation")
    if data.get("judge_review_queue_present") is not True:
        errors.append("judge review queue required")
    if data.get("readiness_all_false") is not True:
        errors.append("readiness must remain all false")
    return errors


def validate_live(
    workspace: Path,
    semantic_root: Path,
    contracts_root: Path,
    fixtures_root: Path,
    report_out: Path | None,
) -> dict[str, Any]:
    schema = load_json(contracts_root / "codex_generation_output_contract.v0.1.schema.json")
    manifest = load_yaml(semantic_root / "semantic_pilot_regen_manifest.yaml")["semantic_pilot_regen_manifest"]
    cards = load_yaml(semantic_root / "semantic_pilot_candidate_cards.yaml")["semantic_pilot_candidate_cards"]
    body_blocks = load_yaml(semantic_root / "semantic_pilot_rich_body_blocks.yaml")["semantic_pilot_rich_body_blocks"]
    queue = load_yaml(semantic_root / "semantic_pilot_judge_review_queue.yaml")["semantic_pilot_judge_review_queue"]
    semantic_report = load_json(semantic_root / "semantic_pilot_semantic_alignment_report.json")
    body_report = load_json(semantic_root / "semantic_pilot_body_entailment_report.json")
    density_report = load_json(semantic_root / "semantic_pilot_industry_density_report.json")
    relation_report = load_json(semantic_root / "semantic_pilot_relation_quality_report.json")
    dedupe_report = load_json(semantic_root / "semantic_pilot_dedupe_report.json")
    receipt = load_json(semantic_root / "semantic_pilot_generation_receipt.json")
    relations, by_candidate = read_relations(semantic_root / "semantic_pilot_relation_candidates.csv")

    if manifest.get("task_id") != TASK_ID:
        fail("manifest task id mismatch")
    if manifest.get("human_decision", {}).get("authorized_by") != "founder_current_request":
        fail("founder authorization missing")
    if manifest.get("semantic_pilot_structured_draft_count") != EXPECTED_TOTAL:
        fail("manifest count must be 20")
    if manifest.get("category_counts") != EXPECTED_CATEGORY_COUNTS:
        fail("manifest category distribution mismatch")
    for key in ["source_repo_live_dependency", "source_repo_live_accessed", "external_drive_dependency", "external_drive_accessed"]:
        if manifest.get(key) is not False:
            fail(f"manifest {key} must be false")
    if manifest.get("accepted_domain_knowledge_count") != 0:
        fail("accepted domain knowledge count must be 0")
    if manifest.get("batch_generation_unlocked") is True or manifest.get("ready_for_first_batch_generation") is True:
        fail("batch generation must remain locked")

    entries = cards.get("candidates", [])
    if len(entries) != EXPECTED_TOTAL:
        fail("candidate count must be 20")
    category_counts = Counter(entry.get("pilot_category") for entry in entries)
    if dict(category_counts) != EXPECTED_CATEGORY_COUNTS:
        fail(f"category counts mismatch: {dict(category_counts)}")

    candidate_ids: set[str] = set()
    prop_signatures: list[str] = []
    body_signatures: list[str] = []
    semantic_fingerprints: list[str] = []
    cluster_errors: dict[str, list[str]] = {}
    source_status_pass = 0
    body_block_by_id = {block["candidate_id"]: block for block in body_blocks.get("blocks", [])}
    for entry in entries:
        candidate = entry["candidate"]
        cid = candidate["identity"]["candidate_id"]
        if cid in candidate_ids:
            fail(f"duplicate candidate id: {cid}")
        candidate_ids.add(cid)
        errors = validate_candidate_entry(entry, schema, by_candidate)
        if errors:
            cluster_errors[cid] = errors
        distinct = entry["semantic_distinctness"]
        prop_signatures.append(distinct["normalized_proposition_signature"])
        body_signatures.append(distinct["normalized_body_signature"])
        semantic_fingerprints.append(distinct["semantic_fingerprint"])
        source_status = entry["source_status"]
        if source_status["human_review_status"] == "pending" and source_status["human_reviewed_method"] is False:
            source_status_pass += 1
        if body_block_by_id.get(cid, {}).get("body_text") != candidate["rich_body"]["body_text"]:
            fail(f"rich body block mismatch: {cid}")
    if cluster_errors:
        fail(f"candidate validation failed: {cluster_errors}")
    if len(set(prop_signatures)) != EXPECTED_TOTAL:
        fail("normalized proposition duplicate found")
    if len(set(body_signatures)) != EXPECTED_TOTAL:
        fail("normalized body duplicate found")
    if len(set(semantic_fingerprints)) != EXPECTED_TOTAL:
        fail("semantic fingerprint duplicate found")
    if set(by_candidate) != candidate_ids:
        fail("relation candidate id set mismatch")

    queue_items = queue.get("items", [])
    if len(queue_items) != EXPECTED_TOTAL:
        fail("judge queue must include 20 items")
    if {item["candidate_id"] for item in queue_items} != candidate_ids:
        fail("judge queue candidate ids mismatch")
    if any(item.get("review_status") != "pending" for item in queue_items):
        fail("judge queue items must remain pending")
    if not (semantic_root / "semantic_pilot_judge_protocol.md").exists():
        fail("judge protocol missing")

    validate_status(load_yaml(workspace / "project-infra/current_workspace_status.yaml"))

    checks = {
        "semantic_alignment": semantic_report.get("candidate_count") == EXPECTED_TOTAL
        and semantic_report.get("cluster_entailment_fail_count") == 0
        and semantic_report.get("semantic_uniqueness_fail_count") == 0,
        "body_entailment": body_report.get("structural_checker_passed") is True
        and body_report.get("hard_claim_leak_count") == 0
        and body_report.get("unsupported_body_claim_count") == 0
        and body_report.get("requires_judge_review") is True,
        "industry_density": density_report.get("min_body_chars_pass_count") == EXPECTED_TOTAL
        and density_report.get("review_instruction_body_count") == 0,
        "relation_quality": relation_report.get("total_relations", 0) >= 40
        and relation_report.get("forbidden_predicate_count") == 0
        and relation_report.get("candidates_with_min_two_relations") == EXPECTED_TOTAL,
        "dedupe": dedupe_report.get("blocking_duplicate_count") == 0
        and dedupe_report.get("normalized_proposition_duplicate_count") == 0
        and dedupe_report.get("normalized_body_duplicate_count") == 0
        and dedupe_report.get("semantic_fingerprint_duplicate_count") == 0,
        "receipt": receipt.get("semantic_pilot_structured_draft_count") == EXPECTED_TOTAL
        and receipt.get("candidatepack_created") is False,
    }
    failing = [key for key, ok in checks.items() if not ok]
    if failing:
        fail(f"report checks failed: {failing}")

    positive = load_yaml(fixtures_root / "positive_valid_semantic_regen_minimal.yaml")
    positive_errors = validate_fixture_model(positive)
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name))
        negative_results[name] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")

    report = {
        "status": "PASS",
        "task_id": TASK_ID,
        "source_repo_live_accessed": False,
        "external_drive_accessed": False,
        "semantic_pilot_structured_draft_count": EXPECTED_TOTAL,
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
        "ready_for_first_batch_generation": False,
        "category_counts": dict(category_counts),
        "normalized_proposition_duplicate_count": 0,
        "normalized_body_duplicate_count": 0,
        "semantic_fingerprint_duplicate_count": 0,
        "cluster_entailment_pass_count": EXPECTED_TOTAL,
        "cluster_entailment_fail_count": 0,
        "industry_density_pass_count": EXPECTED_TOTAL,
        "relation_quality_result": "PASS",
        "source_status_disambiguation_pass_count": source_status_pass,
        "hard_claim_leak_count": 0,
        "real_instance_fact_leak_count": 0,
        "P0_00_general_kb_leak_count": 0,
        "judge_review_queue_created": True,
        "judge_protocol_created": True,
        "relation_count": len(relations),
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "positive_fixture_count": 1,
        "negative_fixtures_fail_closed": True,
        "positive_fixture_passed": True,
        "readiness_flags_result": "all_false",
        "candidatepack_created": False,
        "KE_touched": False,
        "serving_touched": False,
        "RAG_touched": False,
        "DIFY_touched": False,
        "recommended_next_step": NEXT_STEP,
        "negative_results": negative_results,
    }
    if report_out:
        write_json(report_out, report)
    return report


def build_fixture_model() -> dict[str, Any]:
    return {
        "semantic_regen_fixture": {
            "task_id": TASK_ID,
            "source_repo_live_dependency": False,
            "source_repo_live_accessed": False,
            "external_drive_dependency": False,
            "external_drive_accessed": False,
            "semantic_pilot_structured_draft_count": EXPECTED_TOTAL,
            "category_counts": EXPECTED_CATEGORY_COUNTS,
            "accepted_domain_knowledge_count": 0,
            "batch_generation_unlocked": False,
            "ready_for_first_batch_generation": False,
            "current_next_step": NEXT_STEP,
            "normalized_proposition_duplicate_count": 0,
            "normalized_body_duplicate_count": 0,
            "semantic_fingerprint_duplicate_count": 0,
            "hard_claim_leak_count": 0,
            "real_instance_fact_leak_count": 0,
            "P0_00_general_kb_leak_count": 0,
            "forbidden_relation_predicate_count": 0,
            "candidates_with_min_two_relations": EXPECTED_TOTAL,
            "cluster_entailment_pass_count": EXPECTED_TOTAL,
            "industry_density_pass_count": EXPECTED_TOTAL,
            "source_status_disambiguation_pass_count": EXPECTED_TOTAL,
            "judge_review_queue_present": True,
            "readiness_all_false": True,
        }
    }


def mutate_fixture_for_negative(model: dict[str, Any], name: str) -> None:
    data = model["semantic_regen_fixture"]
    if name == "negative_wrong_count.yaml":
        data["semantic_pilot_structured_draft_count"] = 19
    elif name == "negative_wrong_category_distribution.yaml":
        data["category_counts"] = {"content_method": 20}
    elif name == "negative_readiness_true.yaml":
        data["readiness_all_false"] = False
    elif name == "negative_accepted_domain_knowledge_count_positive.yaml":
        data["accepted_domain_knowledge_count"] = 1
    elif name == "negative_batch_generation_unlocked.yaml":
        data["batch_generation_unlocked"] = True
    elif name == "negative_duplicate_proposition_signature.yaml":
        data["normalized_proposition_duplicate_count"] = 1
    elif name == "negative_duplicate_normalized_body.yaml":
        data["normalized_body_duplicate_count"] = 1
    elif name == "negative_hash_only_fingerprint.yaml":
        data["semantic_fingerprint_duplicate_count"] = 1
    elif name == "negative_missing_cluster_entailment.yaml":
        data["cluster_entailment_pass_count"] = 19
    elif name == "negative_low_industry_density.yaml":
        data["industry_density_pass_count"] = 19
    elif name == "negative_generic_relation_predicate.yaml":
        data["forbidden_relation_predicate_count"] = 1
    elif name == "negative_missing_min_two_relations.yaml":
        data["candidates_with_min_two_relations"] = 19
    elif name == "negative_source_status_conflation.yaml":
        data["source_status_disambiguation_pass_count"] = 19
    elif name == "negative_hard_claim_expert_synthesis.yaml":
        data["hard_claim_leak_count"] = 1
    elif name == "negative_real_instance_fact_leak.yaml":
        data["real_instance_fact_leak_count"] = 1
    elif name == "negative_p0_00_general_kb_leak.yaml":
        data["P0_00_general_kb_leak_count"] = 1
    elif name == "negative_missing_judge_queue.yaml":
        data["judge_review_queue_present"] = False
    elif name == "negative_source_repo_dependency_true.yaml":
        data["source_repo_live_dependency"] = True
    elif name == "negative_external_drive_dependency_true.yaml":
        data["external_drive_dependency"] = True
    elif name == "negative_batch_generation_next_step.yaml":
        data["current_next_step"] = BATCH_NEXT_STEP


def run_selftest() -> dict[str, Any]:
    temp_root = Path(tempfile.mkdtemp(prefix="semantic-regen-selftest-"))
    fixtures = temp_root / "fixtures"
    fixtures.mkdir(parents=True)
    positive = build_fixture_model()
    (fixtures / "positive_valid_semantic_regen_minimal.yaml").write_text(
        yaml.safe_dump(positive, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    for name in NEGATIVE_FIXTURES:
        fixture = build_fixture_model()
        mutate_fixture_for_negative(fixture, name)
        (fixtures / name).write_text(
            yaml.safe_dump(fixture, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    if errors := validate_fixture_model(positive):
        fail(f"selftest positive failed: {errors}")
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures / name))
        if not errors:
            fail(f"selftest negative passed unexpectedly: {name}")
    return {
        "status": "PASS",
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "negative_fixtures_fail_closed": True,
    }


def main() -> int:
    if not __debug__:
        print("FAIL-CLOSED: optimized Python mode is not allowed for this checker", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--semantic-pilot-root", default="03_pilot/semantic_regen")
    parser.add_argument("--contracts-root", default="01_generation_contracts")
    parser.add_argument("--brief-pack-root", default="02_generation_brief_pack")
    parser.add_argument("--fixtures-root", default="ci/fixtures/codex_semantic_pilot_regen")
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
                semantic_root=workspace / args.semantic_pilot_root,
                contracts_root=workspace / args.contracts_root,
                fixtures_root=workspace / args.fixtures_root,
                report_out=workspace / args.report_out if args.report_out else None,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except SemanticRegenError as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
