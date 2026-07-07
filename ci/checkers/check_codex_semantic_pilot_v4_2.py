#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

TASK_ID = "CODEX-SEMANTIC-PILOT-V4_1-NOGO-CLOSEOUT-AND-V4_2-TYPE-SPECIFIC-REWRITE-001"
PREVIOUS_TASK_ID = "CODEX-SEMANTIC-PILOT-V4-NOGO-CLOSEOUT-AND-V4_1-REVISION-001"
V4_3_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_2-NOGO-CLOSEOUT-PREDICATE-REGISTRY-AND-V4_3-TARGETED-REPAIR-001"
V4_4_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_3-NOGO-CLOSEOUT-CREATIVE-KNOWLEDGE-CAPSULE-AND-V4_4-REWRITE-001"
V4_5_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_4-CONDITIONAL-PASS-CLOSEOUT-AND-V4_5-CAPSULE-RICH-BODY-INTEGRATION-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_2-JUDGE-GO-NOGO-001"
V4_3_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_3-JUDGE-GO-NOGO-001"
V4_4_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_4-JUDGE-GO-NOGO-001"
V4_5_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_5-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_TOTAL = 8
EXPECTED_DISTRIBUTION = {
    "content_method": 2,
    "apparel_claim_boundary": 2,
    "display_to_content": 2,
    "control_plane_governance": 2,
}
EXPECTED_V4_1_IDS = {
    "SEM-V4_1-CONTENT-METHOD-001",
    "SEM-V4_1-CONTENT-METHOD-002",
    "SEM-V4_1-APPAREL-CLAIM-BOUNDARY-001",
    "SEM-V4_1-APPAREL-CLAIM-BOUNDARY-002",
    "SEM-V4_1-DISPLAY-TO-CONTENT-001",
    "SEM-V4_1-DISPLAY-TO-CONTENT-002",
    "SEM-V4_1-CONTROL-PLANE-GOVERNANCE-001",
    "SEM-V4_1-CONTROL-PLANE-GOVERNANCE-002",
}
REQUIRED_BLOCKS = {
    "general_knowledge": {
        "definition",
        "differentiation_mechanism",
        "applicable_conditions",
        "not_applicable_conditions",
        "positive_example_minimum",
        "negative_example_minimum",
        "observable_apparel_or_retail_anchor",
        "downstream_consumption_effect",
    },
    "claim_boundary": {
        "claim_type_ladder",
        "allowed_expression_examples",
        "restricted_expression_examples",
        "prohibited_expression_examples",
        "minimum_contrast_examples",
        "evidence_threshold_by_claim_strength",
        "source_gap_route",
        "downgrade_expression_rule",
    },
    "execution_asset": {
        "input_signal",
        "spatial_or_temporal_logic",
        "ordered_steps",
        "observable_completion_condition",
        "failure_or_stop_condition",
        "shot_or_action_slot_mapping",
        "downstream_output_asset_shape",
    },
    "control_plane": {
        "trigger_condition",
        "state_transition",
        "route_target",
        "ledger_write",
        "reentry_condition",
        "prohibited_transition",
        "fail_closed_default",
    },
    "decision_packet": {
        "decision_question",
        "options",
        "decision_owner",
        "impacted_contract_or_layer",
        "default_safe_action",
        "unresolved_inputs",
        "next_review_condition",
    },
}
FORBIDDEN_REVIEW_PROSE = {
    "可保留的句子",
    "需要修改的句子",
    "必须阻断的句子",
    "帮助人审人员判断",
    "在质量判断上",
    "人审如何保留",
    "本条质量判断",
    "本文是否可进入下一步",
}
RELATION_FIELDS = [
    "relation_id",
    "source_draft_id",
    "subject_ref",
    "subject_type",
    "predicate_id",
    "object_ref",
    "object_type",
    "condition",
    "evidence_requirement",
    "owner_scope",
    "body_proposition_ref",
    "w7_required_relation_ref",
    "relation_status",
]
FORBIDDEN_RELATION_PREDICATES = {
    "review_adjacent_method_boundary",
    "candidate_to_cluster_trace",
    "related_to",
    "adjacent_to",
}
NEGATIVE_FIXTURES = [
    "negative_same_category_similarity_over_0_55.yaml",
    "negative_cross_category_similarity_over_0_45.yaml",
    "negative_exact_paragraph_duplicate.yaml",
    "negative_body_contains_review_prose.yaml",
    "negative_general_knowledge_missing_differentiation_mechanism.yaml",
    "negative_claim_boundary_missing_expression_ladder.yaml",
    "negative_execution_asset_missing_ordered_steps.yaml",
    "negative_control_plane_missing_route_target.yaml",
    "negative_decision_packet_missing_default_safe_action.yaml",
    "negative_relation_predicate_reuse_too_high.yaml",
    "negative_fixed_three_relations_per_card_even_if_total_24.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_readiness_true.yaml",
]
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


class V42CheckError(Exception):
    pass


def fail(message: str) -> None:
    raise V42CheckError(message)

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


def tokenize(text: str) -> set[str]:
    clean = re.sub(r"\s+", "", text)
    return {clean[idx : idx + 2] for idx in range(max(0, len(clean) - 1)) if CJK_RE.search(clean[idx : idx + 2])}


def similarity(a: str, b: str) -> float:
    left, right = tokenize(a), tokenize(b)
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 3)


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


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_v4_2_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("v4_2_draft_count") != EXPECTED_TOTAL:
        errors.append("v4_2_draft_count must be 8")
    if data.get("v4_2_distribution") != EXPECTED_DISTRIBUTION:
        errors.append("distribution must be 2/2/2/2")
    if data.get("one_to_one_revision_count") != EXPECTED_TOTAL:
        errors.append("one_to_one_revision_count must be 8")
    if data.get("artifact_kind_specific_body_shape_valid_count") != EXPECTED_TOTAL:
        errors.append("artifact-kind-specific body shape count must be 8")
    for key in [
        "forbidden_review_prose_count",
        "exact_paragraph_duplicate_count",
        "required_block_missing_count",
        "relation_schema_invalid_count",
    ]:
        if data.get(key) != 0:
            errors.append(f"{key} must be 0")
    if float(data.get("same_category_body_similarity_max", 1.0)) > 0.55:
        errors.append("same_category_body_similarity_max must be <= 0.55")
    if float(data.get("cross_category_body_similarity_max", 1.0)) > 0.45:
        errors.append("cross_category_body_similarity_max must be <= 0.45")
    relation_count = data.get("relation_design_hints_count", 0)
    if relation_count < 20 or relation_count > 32:
        errors.append("relation_design_hints_count must be 20..32")
    if data.get("distinct_predicate_id_count", 0) < 12:
        errors.append("distinct_predicate_id_count must be at least 12")
    if float(data.get("max_same_predicate_usage_ratio", 1.0)) > 0.25:
        errors.append("max_same_predicate_usage_ratio must be <= 0.25")
    if data.get("fixed_three_relations_per_card") is True:
        errors.append("relation hints must not be fixed three per card")
    if data.get("owner_model_valid_count") != EXPECTED_TOTAL:
        errors.append("owner_model_valid_count must be 8")
    if data.get("accepted_domain_knowledge_count") != 0:
        errors.append("accepted_domain_knowledge_count must be 0")
    if data.get("batch_generation_unlocked") is not False:
        errors.append("batch_generation_unlocked must be false")
    if data.get("ready_for_first_batch_generation") is not False:
        errors.append("ready_for_first_batch_generation must be false")
    if data.get("readiness_all_false") is not True:
        errors.append("readiness_all_false must be true")
    for key in ["candidatepack_created", "KE_touched", "serving_touched", "RAG_touched", "DIFY_touched"]:
        if data.get(key) is not False:
            errors.append(f"{key} must be false")
    return errors


def validate_status(workspace: Path) -> None:
    status = load_yaml(workspace / "project-infra/current_workspace_status.yaml")
    phase = status.get("phase", {})
    if phase.get("current_next_step") == BATCH_NEXT_STEP:
        fail("batch generation task cannot be next step")
    current_next_step = phase.get("current_next_step")
    if current_next_step not in {NEXT_STEP, V4_3_NEXT_STEP, V4_4_NEXT_STEP, V4_5_NEXT_STEP}:
        fail("workspace next step must be semantic pilot V4.2 judge go/no-go or semantic pilot V4.3 judge go/no-go or semantic pilot V4.4 judge go/no-go")
    if current_next_step == NEXT_STEP and phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be V4.2 rewrite task")
    if current_next_step == V4_3_NEXT_STEP and phase.get("previous_step") != V4_3_TASK_ID:
        fail("workspace previous step must be V4.3 targeted repair task")
    if current_next_step == V4_4_NEXT_STEP and phase.get("previous_step") != V4_4_TASK_ID:
        fail("workspace previous step must be V4.4 creative capsule task")
    v42 = status.get("semantic_pilot_v4_2", {})
    if v42.get("task_id") != TASK_ID or v42.get("status") != "completed":
        fail("semantic_pilot_v4_2 status block missing")
    if v42.get("semantic_pilot_v4_2_count") != EXPECTED_TOTAL:
        fail("semantic_pilot_v4_2 count must be 8")
    if v42.get("one_to_one_revision_of_v4_1") is not True:
        fail("semantic_pilot_v4_2 must be one-to-one revision of V4.1")
    if v42.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    if v42.get("batch_generation_unlocked") is True or v42.get("ready_for_first_batch_generation") is True:
        fail("batch generation must remain locked")
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
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")


def load_authority(workspace: Path) -> dict[str, dict[str, Any]]:
    data = load_yaml(workspace / "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml")["w7_canonical_cluster_authority"]
    return {record["mkc_id"]: record for record in data.get("records", [])}


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    v42_root = workspace / "03_pilot/semantic_v4_2"
    authority = load_authority(workspace)
    policy = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_2_type_specific_policy.v0.1.yaml")[
        "codex_semantic_pilot_v4_2_type_specific_policy"
    ]
    if "claim_boundary" not in policy.get("type_specific_body_shape", []):
        fail("claim_boundary must be a type_specific_body_shape")

    closeout = load_yaml(workspace / "03_pilot/semantic_v4_1/v4_1_no_go_closeout.yaml")["v4_1_no_go_closeout"]
    digest = load_yaml(workspace / "03_pilot/semantic_v4_1/v4_1_semantic_review_digest.yaml")["v4_1_semantic_review_digest"]
    if closeout.get("human_decision", {}).get("authorized_scope") != "V4.1 no-go closeout + V4.2 one-to-one rewrite only":
        fail("human decision scope missing from V4.1 closeout")
    if digest.get("human_decision_present") is not True:
        fail("V4.1 semantic review digest must record human decision")
    if closeout.get("semantic_verdict") != "NO_GO":
        fail("V4.1 closeout must be NO_GO")

    manifest = load_yaml(v42_root / "semantic_pilot_v4_2_manifest.yaml")["semantic_pilot_v4_2_manifest"]
    cards = load_yaml(v42_root / "semantic_pilot_v4_2_candidate_cards.yaml")["semantic_pilot_v4_2_candidate_cards"]["candidates"]
    rich_blocks = load_yaml(v42_root / "semantic_pilot_v4_2_rich_body_blocks.yaml")["semantic_pilot_v4_2_rich_body_blocks"]["blocks"]
    type_blocks = load_yaml(v42_root / "semantic_pilot_v4_2_type_specific_body_blocks.yaml")["semantic_pilot_v4_2_type_specific_body_blocks"]["items"]
    sidecars = load_yaml(v42_root / "semantic_pilot_v4_2_sidecars.yaml")["semantic_pilot_v4_2_sidecars"]["sidecars"]
    queue = load_yaml(v42_root / "semantic_pilot_v4_2_judge_review_queue.yaml")["semantic_pilot_v4_2_judge_review_queue"]["items"]
    similarity_report = load_json(v42_root / "semantic_pilot_v4_2_similarity_report.json")
    quality_report = load_json(v42_root / "semantic_pilot_v4_2_quality_report.json")
    receipt = load_json(workspace / "docs/reports/codex_semantic_pilot_v4_2_receipt.json")

    if manifest.get("task_id") != TASK_ID:
        fail("manifest task id mismatch")
    if manifest.get("authorized_scope") != "V4.1 no-go closeout + V4.2 one-to-one rewrite only":
        fail("manifest authorized scope mismatch")
    if manifest.get("semantic_pilot_v4_2_count") != EXPECTED_TOTAL:
        fail("manifest count must be 8")
    if manifest.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("manifest distribution must be 2/2/2/2")
    if manifest.get("one_to_one_revision_of_v4_1") is not True:
        fail("manifest must declare one-to-one revision of V4.1")

    if len(cards) != EXPECTED_TOTAL:
        fail("V4.2 candidate count must be 8")
    if Counter(card.get("pilot_category") for card in cards) != EXPECTED_DISTRIBUTION:
        fail("V4.2 distribution must be 2/2/2/2")

    rich_by_id = {item["draft_id"]: item for item in rich_blocks}
    type_by_id = {item["draft_id"]: item for item in type_blocks}
    sidecar_by_id = {item["draft_id"]: item for item in sidecars}
    draft_ids: set[str] = set()
    revision_ids: set[str] = set()
    bodies: dict[str, str] = {}
    required_block_missing_count = 0
    forbidden_review_prose_count = 0
    owner_model_valid_count = 0
    for card in cards:
        draft_id = card["draft_id"]
        if draft_id in draft_ids:
            fail(f"duplicate draft id: {draft_id}")
        draft_ids.add(draft_id)
        lineage = card.get("revision_lineage", {})
        revision_of = lineage.get("revision_of")
        revision_ids.add(revision_of)
        if revision_of not in EXPECTED_V4_1_IDS:
            fail(f"{draft_id}: revision_of must point to V4.1")
        mkc_id = card.get("canonical_cluster_id")
        if mkc_id not in authority:
            fail(f"{draft_id}: mkc id missing from authority")
        if card.get("canonical_cluster_title_from_authority") != authority[mkc_id]["canonical_title"]:
            fail(f"{draft_id}: authority title mismatch")
        shape = card.get("type_specific_body_shape")
        if shape not in REQUIRED_BLOCKS:
            fail(f"{draft_id}: invalid type_specific_body_shape")
        if shape == "claim_boundary" and card.get("artifact_kind") == "claim_boundary":
            fail(f"{draft_id}: claim_boundary must not be written to strict artifact_kind")
        body = card.get("canonical_body_zh", "")
        bodies[draft_id] = body
        if rich_by_id.get(draft_id, {}).get("canonical_body_zh") != body:
            fail(f"{draft_id}: rich body mirror mismatch")
        block_item = type_by_id.get(draft_id)
        if not block_item:
            fail(f"{draft_id}: missing type-specific blocks")
        block_ids = {block["block_id"] for block in block_item.get("blocks", [])}
        missing = REQUIRED_BLOCKS[shape] - block_ids
        if missing:
            required_block_missing_count += len(missing)
            fail(f"{draft_id}: missing required blocks {sorted(missing)}")
        if set(block_item.get("required_blocks", [])) != REQUIRED_BLOCKS[shape]:
            fail(f"{draft_id}: required_blocks list mismatch")
        for token in FORBIDDEN_REVIEW_PROSE:
            if token in body:
                forbidden_review_prose_count += 1
                fail(f"{draft_id}: forbidden review prose in body: {token}")
        diff = card.get("cluster_differentiation_claim", {})
        for key in [
            "referenced_mkc_id",
            "what_changes_in_decision_logic",
            "what_input_requirement_changes",
            "what_output_effect_changes",
            "what_failure_mode_is_unique",
            "closest_neighbor_cluster",
            "difference_from_neighbor",
        ]:
            if not diff.get(key):
                fail(f"{draft_id}: cluster differentiation missing {key}")
        owner = card.get("owner_model", {})
        if not all(owner.get(key) for key in ["semantic_owner", "storage_target", "artifact_kind", "consumer_layer"]):
            fail(f"{draft_id}: owner_model incomplete")
        owner_model_valid_count += 1
        if any(value is not False for value in card.get("readiness_flags", {}).values()):
            fail(f"{draft_id}: readiness flag true")
        sidecar = sidecar_by_id.get(draft_id)
        if not sidecar:
            fail(f"{draft_id}: sidecar missing")
        if sidecar.get("artifact_kind_schema_compatibility", {}).get("type_specific_body_shape") != shape:
            fail(f"{draft_id}: sidecar shape mismatch")
        if sidecar.get("type_shape_validation", {}).get("uniform_seven_paragraph_template_used") is not False:
            fail(f"{draft_id}: uniform seven paragraph template used")
    if revision_ids != EXPECTED_V4_1_IDS:
        fail("V4.2 must revise all 8 V4.1 cards exactly once")

    paragraphs: list[tuple[str, str]] = []
    for item in rich_blocks:
        for paragraph in item.get("paragraphs", []):
            paragraphs.append((item["draft_id"], paragraph.get("text", "").strip()))
    seen: dict[str, str] = {}
    exact_paragraph_duplicate_count = 0
    for draft_id, paragraph in paragraphs:
        if paragraph in seen:
            exact_paragraph_duplicate_count += 1
        else:
            seen[paragraph] = draft_id
    if exact_paragraph_duplicate_count:
        fail("exact paragraph duplicate across cards")

    same_category_body_similarity_max = 0.0
    cross_category_body_similarity_max = 0.0
    by_id = {card["draft_id"]: card for card in cards}
    for left, right in combinations(cards, 2):
        score = similarity(left["canonical_body_zh"], right["canonical_body_zh"])
        if left["pilot_category"] == right["pilot_category"]:
            same_category_body_similarity_max = max(same_category_body_similarity_max, score)
        else:
            cross_category_body_similarity_max = max(cross_category_body_similarity_max, score)
    if same_category_body_similarity_max > 0.55:
        fail(f"same category body similarity too high: {same_category_body_similarity_max}")
    if cross_category_body_similarity_max > 0.45:
        fail(f"cross category body similarity too high: {cross_category_body_similarity_max}")

    with (v42_root / "semantic_pilot_v4_2_relation_design_hints.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        fail("relation design hints csv is empty")
    if list(rows[0]) != RELATION_FIELDS:
        fail("relation design hints schema mismatch")
    if len(rows) < 20 or len(rows) > 32:
        fail("relation design hints total must be 20..32")
    relation_schema_invalid_count = 0
    by_card = Counter()
    predicate_counts = Counter()
    predicate_by_category: dict[str, set[str]] = {}
    for row in rows:
        draft_id = row["source_draft_id"]
        if draft_id not in draft_ids:
            fail(f"relation references unknown draft: {draft_id}")
        by_card[draft_id] += 1
        predicate = row["predicate_id"]
        predicate_counts[predicate] += 1
        predicate_by_category.setdefault(predicate, set()).add(by_id[draft_id]["pilot_category"])
        if predicate in FORBIDDEN_RELATION_PREDICATES:
            fail(f"forbidden relation predicate: {predicate}")
        if row["relation_status"] != "design_hint_not_ontology_edge":
            fail("relation_status must be design_hint_not_ontology_edge")
        for key in ["subject_ref", "object_ref"]:
            value = row[key]
            if not value.startswith(row["source_draft_id"] + ":block:"):
                relation_schema_invalid_count += 1
                fail(f"unstable relation ref: {value}")
    for draft_id in draft_ids:
        count = by_card[draft_id]
        if count < 2 or count > 5:
            fail(f"{draft_id}: relation count must be 2..5")
    if all(count == 3 for count in by_card.values()):
        fail("relation hints must not be fixed three per card")
    if len(predicate_counts) < 12:
        fail("relation predicate diversity too low")
    if max(predicate_counts.values()) / len(rows) > 0.25:
        fail("relation predicate reuse ratio too high")
    if any(len(categories) == 4 for categories in predicate_by_category.values()):
        fail("a predicate is used in all four categories")

    if len(queue) != EXPECTED_TOTAL or {item["draft_id"] for item in queue} != draft_ids:
        fail("judge queue must contain all 8 V4.2 drafts")
    if any(item.get("review_status") != "pending" for item in queue):
        fail("judge queue must remain pending")
    if not (v42_root / "semantic_pilot_v4_2_judge_protocol.md").exists():
        fail("judge protocol missing")
    validate_status(workspace)

    recomputed = {
        "v4_2_draft_count": EXPECTED_TOTAL,
        "v4_2_distribution": dict(Counter(card.get("pilot_category") for card in cards)),
        "one_to_one_revision_count": len(revision_ids),
        "artifact_kind_specific_body_shape_valid_count": EXPECTED_TOTAL,
        "forbidden_review_prose_count": forbidden_review_prose_count,
        "exact_paragraph_duplicate_count": exact_paragraph_duplicate_count,
        "same_category_body_similarity_max": same_category_body_similarity_max,
        "cross_category_body_similarity_max": cross_category_body_similarity_max,
        "relation_design_hints_count": len(rows),
        "distinct_predicate_id_count": len(predicate_counts),
        "max_same_predicate_usage_ratio": round(max(predicate_counts.values()) / len(rows), 3),
        "owner_model_valid_count": owner_model_valid_count,
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
        "ready_for_first_batch_generation": False,
        "candidatepack_created": False,
        "KE_touched": False,
        "serving_touched": False,
        "RAG_touched": False,
        "DIFY_touched": False,
    }
    if similarity_report.get("same_category_body_similarity_max") != recomputed["same_category_body_similarity_max"]:
        fail("similarity report does not match recomputed same-category max")
    if similarity_report.get("cross_category_body_similarity_max") != recomputed["cross_category_body_similarity_max"]:
        fail("similarity report does not match recomputed cross-category max")
    for key, value in recomputed.items():
        if quality_report.get(key) != value:
            fail(f"quality report mismatch for {key}")
        if key in receipt and receipt.get(key) != value:
            fail(f"receipt mismatch for {key}")

    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_2"
    positive = load_yaml(fixtures_root / "positive_valid_semantic_v4_2_minimal.yaml")
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
        **recomputed,
        "readiness_flags_result": "all_false",
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "positive_fixture_passed": True,
        "negative_fixtures_fail_closed": True,
        "recommended_next_step": NEXT_STEP,
        "negative_results": negative_results,
    }
    if report_out:
        write_json(report_out, report)
    return report


def run_selftest(workspace: Path) -> dict[str, Any]:
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_2"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_2_minimal.yaml"))
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name))
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
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
    parser.add_argument("--report-out")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace_root).resolve()
    try:
        if args.selftest:
            report = run_selftest(workspace)
        else:
            report = validate_live(workspace, Path(args.report_out) if args.report_out else None)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except V42CheckError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
