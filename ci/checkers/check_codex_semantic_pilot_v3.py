#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

TASK_ID = "CODEX-SEMANTIC-PILOT-V3-REWRITE-AND-W7-ALIGNMENT-001"
V4_TASK_ID = "CODEX-V3-NOGO-W7-AUTHORITY-AND-V4-PILOT-001"
V4_1_TASK_ID = "CODEX-SEMANTIC-PILOT-V4-NOGO-CLOSEOUT-AND-V4_1-REVISION-001"
V4_2_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_1-NOGO-CLOSEOUT-AND-V4_2-TYPE-SPECIFIC-REWRITE-001"
V4_3_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_2-NOGO-CLOSEOUT-PREDICATE-REGISTRY-AND-V4_3-TARGETED-REPAIR-001"
V4_4_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_3-NOGO-CLOSEOUT-CREATIVE-KNOWLEDGE-CAPSULE-AND-V4_4-REWRITE-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V3-JUDGE-GO-NOGO-001"
V4_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4-JUDGE-GO-NOGO-001"
V4_1_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_1-JUDGE-GO-NOGO-001"
V4_2_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_2-JUDGE-GO-NOGO-001"
V4_3_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_3-JUDGE-GO-NOGO-001"
V4_4_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_4-JUDGE-GO-NOGO-001"
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
ALLOWED_PRIMARY_OWNERS = {
    "GeneralKnowledgeBase",
    "L2_PlayCardCandidate",
    "L3_ExecutionAssetCandidate",
    "EvidencePolicyCandidate",
    "ControlPlaneContractSource",
    "DecisionPacketLedger",
    "SourceGapLedger",
}
OWNER_MAPPING = {
    "GeneralKnowledgeBase": ("general_knowledge_candidate", "GeneralKnowledgeBase", "TBox_candidate"),
    "L2_PlayCardCandidate": ("general_knowledge_candidate", "GeneralKnowledgeBase", "L2_PlayCard_candidate"),
    "L3_ExecutionAssetCandidate": ("execution_asset_outbox_candidate", "ExecutionAssetOutbox", "L3_ExecutionAsset_candidate"),
    "EvidencePolicyCandidate": ("general_knowledge_candidate", "GeneralKnowledgeBase", "EvidencePolicy_candidate"),
    "ControlPlaneContractSource": ("control_plane_candidate", "ControlPlaneContractSource", "GovernanceContract_candidate"),
    "DecisionPacketLedger": ("decision_packet", "DecisionPacketLedger", "DecisionPacketLedger"),
    "SourceGapLedger": ("source_gap", "SourceGapLedger", "SourceGapLedger"),
}
FORBIDDEN_BODY_TERMS = {
    "pilot",
    "metadata",
    "hash",
    "fingerprint",
    "cluster changed",
    "this candidate",
    "this draft",
    "review queue",
    "judge",
    "not a template",
    "not through metadata",
    "intended as dense knowledge text",
    "readiness",
    "schema",
    "source_repo",
}
FORBIDDEN_PREDICATES = {
    "generic",
    "review_adjacent",
    "review_adjacent_method_boundary",
    "placeholder",
    "related_to",
    "similar_to",
    "traces_to_cluster",
    "references_cluster",
}
INDUSTRY_ELEMENTS = {
    "apparel_object",
    "material_or_fabric_property",
    "fit_or_silhouette_observation",
    "retail_scene",
    "display_or_styling_action",
    "content_action",
    "claim_or_evidence_boundary",
    "operator_decision",
    "downstream_output_implication",
    "failure_mode",
}
NEGATIVE_FIXTURES = [
    "negative_wrong_count.yaml",
    "negative_english_primary_body.yaml",
    "negative_missing_chinese_body.yaml",
    "negative_forbidden_audit_phrase_in_body.yaml",
    "negative_W7_topic_mismatch.yaml",
    "negative_duplicate_proposition_signature.yaml",
    "negative_duplicate_normalized_body.yaml",
    "negative_hash_only_fingerprint.yaml",
    "negative_low_industry_density.yaml",
    "negative_generic_relation_predicate.yaml",
    "negative_candidate_to_cluster_relation.yaml",
    "negative_missing_min_two_relations.yaml",
    "negative_multiple_primary_target_owners.yaml",
    "negative_control_plane_targets_GKB.yaml",
    "negative_source_status_conflation.yaml",
    "negative_hard_claim_expert_synthesis.yaml",
    "negative_real_instance_fact_leak.yaml",
    "negative_batch_generation_unlocked.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_source_repo_dependency_true.yaml",
    "negative_google_drive_dependency_true.yaml",
    "negative_readiness_true.yaml",
    "negative_missing_judge_queue.yaml",
]
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ENGLISH_RE = re.compile(r"[A-Za-z]")
HARD_CLAIM_RE = re.compile(r"(guarantee|clinically proven|tested to|cure|显瘦|瘦身|保证|实测|检测证明)", re.IGNORECASE)
REAL_INSTANCE_RE = re.compile(r"(SKU-[A-Z0-9-]+|真实顾客说|某品牌的|某门店的|某设计师|某达人)")


class SemanticV3Error(Exception):
    pass


def fail(message: str) -> None:
    raise SemanticV3Error(message)


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


def zh_count(text: str) -> int:
    return len(CJK_RE.findall(text))


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


def candidate_text(candidate: dict[str, Any]) -> str:
    rich = candidate.get("rich_body", {})
    semantic = candidate.get("semantic_structure", {})
    chunks = [str(value) for value in semantic.values()]
    chunks.append(str(rich.get("body_text", "")))
    for section in rich.get("body_sections", []):
        chunks.append(str(section.get("heading", "")))
        chunks.append(str(section.get("text", "")))
    return "\n".join(chunks)


def read_relations(path: Path) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "relation_id",
        "candidate_id",
        "subject_ref",
        "relation_predicate",
        "object_ref",
        "relation_note",
        "contains_real_instance_fact",
    }
    if not rows:
        fail("relation csv is empty")
    if set(rows[0]) != required:
        fail(f"relation csv fields mismatch: {sorted(rows[0])}")
    by_candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_candidate[row["candidate_id"]].append(row)
    return rows, by_candidate


def validate_status(status: dict[str, Any]) -> None:
    phase = status.get("phase", {})
    if phase.get("current_next_step") == BATCH_NEXT_STEP:
        fail("batch generation task cannot be next step")
    current_next_step = phase.get("current_next_step")
    if current_next_step not in {NEXT_STEP, V4_NEXT_STEP, V4_1_NEXT_STEP, V4_2_NEXT_STEP, V4_3_NEXT_STEP, V4_4_NEXT_STEP}:
        fail("workspace next step must be semantic pilot v3 judge go/no-go, semantic pilot v4 judge go/no-go, semantic pilot v4.1 judge go/no-go, semantic pilot v4.2 judge go/no-go, or semantic pilot v4.3 judge go/no-go or semantic pilot v4.4 judge go/no-go")
    previous_step = phase.get("previous_step")
    if current_next_step == NEXT_STEP and previous_step != TASK_ID:
        fail("workspace previous step must be semantic pilot v3 task")
    if current_next_step == V4_NEXT_STEP and previous_step != V4_TASK_ID:
        fail("workspace previous step must be semantic pilot v4 task")
    if current_next_step == V4_1_NEXT_STEP and previous_step != V4_1_TASK_ID:
        fail("workspace previous step must be semantic pilot v4.1 revision task")
    if current_next_step == V4_2_NEXT_STEP and previous_step != V4_2_TASK_ID:
        fail("workspace previous step must be semantic pilot v4.2 rewrite task")
    if current_next_step == V4_3_NEXT_STEP and previous_step != V4_3_TASK_ID:
        fail("workspace previous step must be semantic pilot v4.3 targeted repair task")
    if current_next_step == V4_4_NEXT_STEP and previous_step != V4_4_TASK_ID:
        fail("workspace previous step must be semantic pilot v4.4 creative capsule task")
    v3 = status.get("semantic_pilot_v3", {})
    if v3.get("task_id") != TASK_ID or v3.get("status") != "completed":
        fail("semantic_pilot_v3 status block missing")
    if v3.get("semantic_pilot_v3_structured_draft_count") != EXPECTED_TOTAL:
        fail("semantic pilot v3 count must be 20")
    if v3.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    if v3.get("batch_generation_unlocked") is True:
        fail("batch_generation_unlocked must remain false")
    if v3.get("ready_for_first_batch_generation") is True:
        fail("ready_for_first_batch_generation must remain false")
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
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")


def validate_candidate_entry(
    entry: dict[str, Any],
    schema: dict[str, Any],
    alignment_by_id: dict[str, dict[str, Any]],
    relations_by_candidate: dict[str, list[dict[str, str]]],
) -> list[str]:
    errors: list[str] = []
    candidate = entry.get("candidate", {})
    errors.extend(validate_schema_shape(candidate, schema))
    if errors:
        return errors
    cid = candidate["identity"]["candidate_id"]
    label = entry.get("canonical_label_zh")
    body = entry.get("canonical_body_zh")
    if not label or zh_count(str(label)) < 2:
        errors.append(f"{cid}: canonical_label_zh missing")
    if candidate["identity"]["candidate_name"] != label:
        errors.append(f"{cid}: candidate_name must mirror canonical_label_zh")
    if not body or candidate["rich_body"]["body_text"] != body:
        errors.append(f"{cid}: canonical_body_zh must mirror rich_body.body_text")
    if zh_count(str(body)) < 900:
        errors.append(f"{cid}: canonical_body_zh below 900 Chinese chars")
    if len(ENGLISH_RE.findall(str(body))) > 20:
        errors.append(f"{cid}: English appears to be primary body language")
    lowered_body = str(body).lower()
    hits = sorted(term for term in FORBIDDEN_BODY_TERMS if term in lowered_body)
    if hits:
        errors.append(f"{cid}: forbidden audit phrase in body: {hits}")

    if candidate["identity"]["generation_status"] != "gpt_generated_structured_draft":
        errors.append(f"{cid}: wrong generation status")
    if candidate["w7_trace"]["w7_map_digest"] != EXPECTED_W7_DIGEST:
        errors.append(f"{cid}: W7 digest mismatch")
    if candidate["w7_trace"]["founder_overlay_digest"] != EXPECTED_FOUNDER_DIGEST:
        errors.append(f"{cid}: founder overlay digest mismatch")
    if any(value is not False for value in candidate["readiness_flags"].values()):
        errors.append(f"{cid}: readiness flag true")

    alignment = alignment_by_id.get(cid)
    if not alignment:
        errors.append(f"{cid}: missing W7 alignment item")
    elif alignment.get("alignment_verdict") == "mismatched":
        errors.append(f"{cid}: W7 alignment mismatched")

    owner_decision = entry.get("target_owner_decision", {})
    primary_owner = owner_decision.get("primary_target_owner")
    if primary_owner not in ALLOWED_PRIMARY_OWNERS:
        errors.append(f"{cid}: invalid primary target owner")
    rejected = owner_decision.get("rejected_target_owners", [])
    if not isinstance(rejected, list) or primary_owner in rejected:
        errors.append(f"{cid}: target owner decision is not single-primary")
    expected = OWNER_MAPPING.get(primary_owner)
    mapping = entry.get("target_owner_schema_mapping", {})
    if expected:
        expected_kind, expected_owner, expected_layer = expected
        if candidate["ownership"]["candidate_kind"] != expected_kind:
            errors.append(f"{cid}: strict candidate_kind mapping mismatch")
        if candidate["ownership"]["proposed_target_owner"] != expected_owner:
            errors.append(f"{cid}: strict proposed_target_owner mapping mismatch")
        if candidate["layer_annotation"]["target_layer_candidate"] != expected_layer:
            errors.append(f"{cid}: strict layer mapping mismatch")
        if mapping.get("strict_schema_proposed_target_owner") != expected_owner:
            errors.append(f"{cid}: sidecar owner mapping mismatch")
    if entry.get("pilot_category") == "control_plane_governance" and primary_owner == "GeneralKnowledgeBase":
        errors.append(f"{cid}: control-plane candidate targets GeneralKnowledgeBase")

    source_status = entry.get("source_status", {})
    if source_status.get("provenance_class") == "expert_synthesis_draft":
        if source_status.get("human_review_status") != "pending":
            errors.append(f"{cid}: expert synthesis draft must be pending")
        if source_status.get("human_reviewed_method") is not False:
            errors.append(f"{cid}: expert synthesis draft must not be human reviewed")
        if source_status.get("expert_synthesis_policy") != "allowed_after_human_review":
            errors.append(f"{cid}: expert synthesis policy mismatch")
        if source_status.get("is_source_anchor") is not False:
            errors.append(f"{cid}: expert synthesis draft cannot be source anchor")
    if source_status.get("provenance_class") == "human_reviewed_expert_synthesis":
        errors.append(f"{cid}: source status conflation")

    density = entry.get("industry_density", {})
    if len(set(density.get("element_types_present", [])) & INDUSTRY_ELEMENTS) < 7:
        errors.append(f"{cid}: industry element coverage below 7")
    if float(density.get("boilerplate_ratio", 1.0)) > 0.08:
        errors.append(f"{cid}: boilerplate ratio too high")

    relations = relations_by_candidate.get(cid, [])
    if len(relations) < 2:
        errors.append(f"{cid}: fewer than two real relation candidates")
    for relation in relations:
        predicate = relation.get("relation_predicate", "")
        subject = relation.get("subject_ref", "")
        obj = relation.get("object_ref", "")
        if predicate in FORBIDDEN_PREDICATES:
            errors.append(f"{cid}: forbidden relation predicate {predicate}")
        if subject == cid or obj == cid or subject.startswith("mkc_") or obj.startswith("mkc_") or "source_cluster" in obj:
            errors.append(f"{cid}: candidate-to-cluster trace relation")
        if relation.get("contains_real_instance_fact", "").lower() != "false":
            errors.append(f"{cid}: relation real instance fact leak")

    text = candidate_text(candidate)
    if HARD_CLAIM_RE.search(text) and candidate["source_policy"]["expert_synthesis_allowed"] is True:
        errors.append(f"{cid}: hard claim expert synthesis leak")
    if REAL_INSTANCE_RE.search(text):
        errors.append(f"{cid}: real instance fact leak")
    return errors


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_v3_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("source_repo_live_dependency") is not False or data.get("source_repo_live_accessed") is not False:
        errors.append("source repo dependency/access must be false")
    if data.get("external_drive_dependency") is not False or data.get("external_drive_accessed") is not False:
        errors.append("external drive dependency/access must be false")
    if data.get("semantic_pilot_v3_structured_draft_count") != EXPECTED_TOTAL:
        errors.append("semantic pilot v3 count must be 20")
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
    if data.get("current_next_step") not in {NEXT_STEP, V4_NEXT_STEP, V4_1_NEXT_STEP, V4_2_NEXT_STEP, V4_3_NEXT_STEP, V4_4_NEXT_STEP}:
        errors.append("next step must be semantic pilot v3 judge go/no-go, semantic pilot v4 judge go/no-go, semantic pilot v4.1 judge go/no-go, semantic pilot v4.2 judge go/no-go, or semantic pilot v4.3 judge go/no-go or semantic pilot v4.4 judge go/no-go")
    expected_zero = [
        "english_primary_body_count",
        "forbidden_audit_phrase_count",
        "W7_mismatched_count",
        "normalized_proposition_duplicate_count",
        "normalized_body_duplicate_count",
        "semantic_fingerprint_duplicate_count",
        "forbidden_relation_predicate_count",
        "candidate_to_cluster_trace_edge_count",
        "control_plane_GKB_target_count",
        "hard_claim_leak_count",
        "real_instance_fact_leak_count",
    ]
    for key in expected_zero:
        if data.get(key) != 0:
            errors.append(f"{key} must be 0")
    expected_twenty = [
        "canonical_label_zh_present_count",
        "canonical_body_zh_present_count",
        "industry_density_pass_count",
        "candidates_with_min_two_relations",
        "single_primary_target_owner_count",
        "source_status_disambiguation_pass_count",
    ]
    for key in expected_twenty:
        if data.get(key) != EXPECTED_TOTAL:
            errors.append(f"{key} must be 20")
    if data.get("relation_total", 0) < 40:
        errors.append("relation total must be at least 40")
    if data.get("judge_review_queue_present") is not True:
        errors.append("judge review queue required")
    if data.get("judge_protocol_present") is not True:
        errors.append("judge protocol required")
    if data.get("readiness_all_false") is not True:
        errors.append("readiness must remain all false")
    for key in ["candidatepack_created", "KE_touched", "serving_touched", "RAG_touched", "DIFY_touched"]:
        if data.get(key) is not False:
            errors.append(f"{key} must be false")
    return errors


def validate_live(
    workspace: Path,
    semantic_root: Path,
    contracts_root: Path,
    fixtures_root: Path,
    report_out: Path | None,
) -> dict[str, Any]:
    schema = load_json(contracts_root / "codex_generation_output_contract.v0.1.schema.json")
    manifest = load_yaml(semantic_root / "semantic_pilot_v3_manifest.yaml")["semantic_pilot_v3_manifest"]
    alignment = load_yaml(semantic_root / "W7_cluster_topic_alignment_matrix.yaml")["W7_cluster_topic_alignment_matrix"]
    cards = load_yaml(semantic_root / "semantic_pilot_v3_candidate_cards.yaml")["semantic_pilot_v3_candidate_cards"]
    blocks = load_yaml(semantic_root / "semantic_pilot_v3_rich_body_blocks.yaml")["semantic_pilot_v3_rich_body_blocks"]
    queue = load_yaml(semantic_root / "semantic_pilot_v3_judge_review_queue.yaml")["semantic_pilot_v3_judge_review_queue"]
    semantic_report = load_json(semantic_root / "semantic_pilot_v3_semantic_alignment_report.json")
    body_report = load_json(semantic_root / "semantic_pilot_v3_body_entailment_report.json")
    chinese_report = load_json(semantic_root / "semantic_pilot_v3_chinese_body_quality_report.json")
    density_report = load_json(semantic_root / "semantic_pilot_v3_industry_density_report.json")
    relation_report = load_json(semantic_root / "semantic_pilot_v3_relation_graph_quality_report.json")
    source_report = load_json(semantic_root / "semantic_pilot_v3_source_status_repair_report.json")
    dedupe_report = load_json(semantic_root / "semantic_pilot_v3_dedupe_report.json")
    receipt = load_json(semantic_root / "semantic_pilot_v3_generation_receipt.json")
    relations, relations_by_candidate = read_relations(semantic_root / "semantic_pilot_v3_relation_candidates.csv")

    if manifest.get("task_id") != TASK_ID:
        fail("manifest task id mismatch")
    if manifest.get("human_decision", {}).get("authorized_by") != "founder_current_request":
        fail("founder authorization missing")
    mapping = manifest.get("schema_compatibility_mapping", {})
    if mapping.get("v3_only_fields_stay_in_wrapper_or_sidecar") is not True:
        fail("schema compatibility mapping missing")
    for key in ["source_repo_live_dependency", "source_repo_live_accessed", "external_drive_dependency", "external_drive_accessed"]:
        if manifest.get(key) is not False:
            fail(f"manifest {key} must be false")
    if manifest.get("semantic_pilot_v3_structured_draft_count") != EXPECTED_TOTAL:
        fail("manifest count must be 20")
    if manifest.get("category_counts") != EXPECTED_CATEGORY_COUNTS:
        fail("manifest category counts mismatch")
    if manifest.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must be 0")
    if manifest.get("batch_generation_unlocked") is True or manifest.get("ready_for_first_batch_generation") is True:
        fail("batch generation must remain locked")

    entries = cards.get("candidates", [])
    if len(entries) != EXPECTED_TOTAL:
        fail("candidate count must be 20")
    category_counts = Counter(entry.get("pilot_category") for entry in entries)
    if dict(category_counts) != EXPECTED_CATEGORY_COUNTS:
        fail(f"category distribution mismatch: {dict(category_counts)}")
    alignment_by_id = {item["candidate_id"]: item for item in alignment.get("items", [])}
    body_by_id = {block["candidate_id"]: block for block in blocks.get("blocks", [])}
    candidate_ids: set[str] = set()
    prop_signatures: list[str] = []
    body_signatures: list[str] = []
    semantic_fps: list[str] = []
    validation_errors: dict[str, list[str]] = {}
    source_status_pass = 0
    single_owner_count = 0
    for entry in entries:
        candidate = entry["candidate"]
        cid = candidate["identity"]["candidate_id"]
        if cid in candidate_ids:
            fail(f"duplicate candidate id: {cid}")
        candidate_ids.add(cid)
        errors = validate_candidate_entry(entry, schema, alignment_by_id, relations_by_candidate)
        if errors:
            validation_errors[cid] = errors
        if body_by_id.get(cid, {}).get("canonical_body_zh") != entry.get("canonical_body_zh"):
            fail(f"rich body block mismatch: {cid}")
        distinct = entry.get("semantic_distinctness", {})
        prop_signatures.append(distinct.get("normalized_proposition_signature", ""))
        body_signatures.append(distinct.get("normalized_body_signature", ""))
        semantic_fps.append(distinct.get("semantic_fingerprint", ""))
        if entry.get("source_status", {}).get("human_review_status") == "pending":
            source_status_pass += 1
        if entry.get("target_owner_decision", {}).get("primary_target_owner") in ALLOWED_PRIMARY_OWNERS:
            single_owner_count += 1
    if validation_errors:
        fail(f"candidate validation failed: {validation_errors}")
    if len(set(prop_signatures)) != EXPECTED_TOTAL:
        fail("normalized proposition duplicate found")
    if len(set(body_signatures)) != EXPECTED_TOTAL:
        fail("normalized body duplicate found")
    if len(set(semantic_fps)) != EXPECTED_TOTAL:
        fail("semantic fingerprint duplicate found")
    if set(relations_by_candidate) != candidate_ids:
        fail("relation candidate id set mismatch")

    queue_items = queue.get("items", [])
    if len(queue_items) != EXPECTED_TOTAL:
        fail("judge queue must include 20 items")
    if {item["candidate_id"] for item in queue_items} != candidate_ids:
        fail("judge queue candidate ids mismatch")
    if any(item.get("review_status") != "pending" for item in queue_items):
        fail("judge queue items must remain pending")
    if not (semantic_root / "semantic_pilot_v3_judge_protocol.md").exists():
        fail("judge protocol missing")

    validate_status(load_yaml(workspace / "project-infra/current_workspace_status.yaml"))

    report_checks = {
        "semantic_alignment": semantic_report.get("candidate_count") == EXPECTED_TOTAL
        and semantic_report.get("mismatched_count") == 0,
        "body_entailment": body_report.get("body_entailment_pass_count") == EXPECTED_TOTAL
        and body_report.get("hard_claim_leak_count") == 0,
        "chinese_body": chinese_report.get("canonical_body_zh_count") == EXPECTED_TOTAL
        and chinese_report.get("english_primary_body_count") == 0
        and chinese_report.get("forbidden_audit_phrase_count") == 0,
        "industry_density": density_report.get("industry_density_pass_count") == EXPECTED_TOTAL,
        "relation_graph": relation_report.get("total_relations", 0) >= 40
        and relation_report.get("forbidden_predicate_count") == 0
        and relation_report.get("candidate_to_cluster_trace_edge_count") == 0,
        "source_status": source_report.get("source_status_conflation_count") == 0
        and source_report.get("hard_claim_expert_synthesis_violation_count") == 0,
        "dedupe": dedupe_report.get("blocking_duplicate_count") == 0
        and dedupe_report.get("normalized_proposition_duplicate_count") == 0
        and dedupe_report.get("normalized_body_duplicate_count") == 0
        and dedupe_report.get("semantic_fingerprint_duplicate_count") == 0,
        "receipt": receipt.get("semantic_pilot_v3_structured_draft_count") == EXPECTED_TOTAL
        and receipt.get("candidatepack_created") is False,
    }
    failed_reports = [key for key, ok in report_checks.items() if not ok]
    if failed_reports:
        fail(f"report checks failed: {failed_reports}")

    positive = load_yaml(fixtures_root / "positive_valid_semantic_v3_minimal.yaml")
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
        "semantic_pilot_v3_structured_draft_count": EXPECTED_TOTAL,
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
        "ready_for_first_batch_generation": False,
        "category_counts": dict(category_counts),
        "chinese_canonical_body_result": "PASS",
        "W7_alignment_result": "PASS",
        "forbidden_audit_phrase_count": 0,
        "normalized_proposition_duplicate_count": 0,
        "normalized_body_duplicate_count": 0,
        "semantic_fingerprint_duplicate_count": 0,
        "industry_density_result": "PASS",
        "relation_graph_quality_result": "PASS",
        "source_status_disambiguation_result": "PASS",
        "source_status_disambiguation_pass_count": source_status_pass,
        "target_owner_single_assignment_result": "PASS",
        "target_owner_single_assignment_count": single_owner_count,
        "hard_claim_leak_count": 0,
        "real_instance_fact_leak_count": 0,
        "judge_review_queue_created": True,
        "judge_protocol_created": True,
        "relation_count": len(relations),
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "positive_fixture_passed": True,
        "negative_fixtures_fail_closed": True,
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
        "semantic_v3_fixture": {
            "task_id": TASK_ID,
            "source_repo_live_dependency": False,
            "source_repo_live_accessed": False,
            "external_drive_dependency": False,
            "external_drive_accessed": False,
            "semantic_pilot_v3_structured_draft_count": EXPECTED_TOTAL,
            "category_counts": EXPECTED_CATEGORY_COUNTS,
            "accepted_domain_knowledge_count": 0,
            "batch_generation_unlocked": False,
            "ready_for_first_batch_generation": False,
            "current_next_step": NEXT_STEP,
            "canonical_label_zh_present_count": EXPECTED_TOTAL,
            "canonical_body_zh_present_count": EXPECTED_TOTAL,
            "english_primary_body_count": 0,
            "forbidden_audit_phrase_count": 0,
            "W7_mismatched_count": 0,
            "normalized_proposition_duplicate_count": 0,
            "normalized_body_duplicate_count": 0,
            "semantic_fingerprint_duplicate_count": 0,
            "industry_density_pass_count": EXPECTED_TOTAL,
            "relation_total": 40,
            "forbidden_relation_predicate_count": 0,
            "candidate_to_cluster_trace_edge_count": 0,
            "candidates_with_min_two_relations": EXPECTED_TOTAL,
            "single_primary_target_owner_count": EXPECTED_TOTAL,
            "control_plane_GKB_target_count": 0,
            "source_status_disambiguation_pass_count": EXPECTED_TOTAL,
            "hard_claim_leak_count": 0,
            "real_instance_fact_leak_count": 0,
            "judge_review_queue_present": True,
            "judge_protocol_present": True,
            "readiness_all_false": True,
            "candidatepack_created": False,
            "KE_touched": False,
            "serving_touched": False,
            "RAG_touched": False,
            "DIFY_touched": False,
        }
    }


def mutate_fixture_for_negative(model: dict[str, Any], name: str) -> None:
    data = model["semantic_v3_fixture"]
    mutations = {
        "negative_wrong_count.yaml": ("semantic_pilot_v3_structured_draft_count", 19),
        "negative_english_primary_body.yaml": ("english_primary_body_count", 1),
        "negative_missing_chinese_body.yaml": ("canonical_body_zh_present_count", 19),
        "negative_forbidden_audit_phrase_in_body.yaml": ("forbidden_audit_phrase_count", 1),
        "negative_W7_topic_mismatch.yaml": ("W7_mismatched_count", 1),
        "negative_duplicate_proposition_signature.yaml": ("normalized_proposition_duplicate_count", 1),
        "negative_duplicate_normalized_body.yaml": ("normalized_body_duplicate_count", 1),
        "negative_hash_only_fingerprint.yaml": ("semantic_fingerprint_duplicate_count", 1),
        "negative_low_industry_density.yaml": ("industry_density_pass_count", 19),
        "negative_generic_relation_predicate.yaml": ("forbidden_relation_predicate_count", 1),
        "negative_candidate_to_cluster_relation.yaml": ("candidate_to_cluster_trace_edge_count", 1),
        "negative_missing_min_two_relations.yaml": ("candidates_with_min_two_relations", 19),
        "negative_multiple_primary_target_owners.yaml": ("single_primary_target_owner_count", 19),
        "negative_control_plane_targets_GKB.yaml": ("control_plane_GKB_target_count", 1),
        "negative_source_status_conflation.yaml": ("source_status_disambiguation_pass_count", 19),
        "negative_hard_claim_expert_synthesis.yaml": ("hard_claim_leak_count", 1),
        "negative_real_instance_fact_leak.yaml": ("real_instance_fact_leak_count", 1),
        "negative_batch_generation_unlocked.yaml": ("batch_generation_unlocked", True),
        "negative_accepted_domain_knowledge_count_positive.yaml": ("accepted_domain_knowledge_count", 1),
        "negative_source_repo_dependency_true.yaml": ("source_repo_live_dependency", True),
        "negative_google_drive_dependency_true.yaml": ("external_drive_dependency", True),
        "negative_readiness_true.yaml": ("readiness_all_false", False),
        "negative_missing_judge_queue.yaml": ("judge_review_queue_present", False),
    }
    key, value = mutations[name]
    data[key] = value
    if name == "negative_google_drive_dependency_true.yaml":
        data["external_drive_accessed"] = True


def run_selftest() -> dict[str, Any]:
    positive = build_fixture_model()
    positive_errors = validate_fixture_model(positive)
    if positive_errors:
        fail(f"selftest positive failed: {positive_errors}")
    for name in NEGATIVE_FIXTURES:
        fixture = build_fixture_model()
        mutate_fixture_for_negative(fixture, name)
        errors = validate_fixture_model(fixture)
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
    parser.add_argument("--semantic-v3-root", default="03_pilot/semantic_v3")
    parser.add_argument("--contracts-root", default="01_generation_contracts")
    parser.add_argument("--brief-pack-root", default="02_generation_brief_pack")
    parser.add_argument("--fixtures-root", default="ci/fixtures/codex_semantic_pilot_v3")
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
                semantic_root=workspace / args.semantic_v3_root,
                contracts_root=workspace / args.contracts_root,
                fixtures_root=workspace / args.fixtures_root,
                report_out=workspace / args.report_out if args.report_out else None,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except SemanticV3Error as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
