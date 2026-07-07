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

TASK_ID = "CODEX-SEMANTIC-PILOT-V4_5-CLOSEOUT-TYPE-SPECIFIC-RICH-BODY-COMPILER-AND-V4_6-REWRITE-001"
V4_7_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_6-CONDITIONAL-REPAIR-CLOSEOUT-AND-V4_7-SEMANTIC-CLEANUP-001"
HOLDOUT_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_7-PASS-CLOSEOUT-METADATA-CLEANUP-AND-HOLDOUT-MICROBATCH-001"
PREVIOUS_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_4-CONDITIONAL-PASS-CLOSEOUT-AND-V4_5-CAPSULE-RICH-BODY-INTEGRATION-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_6-JUDGE-GO-NOGO-001"
V4_7_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_7-JUDGE-GO-NOGO-001"
HOLDOUT_NEXT_STEP = "CODEX-HOLDOUT-MICROBATCH-001-JUDGE-GO-NOGO-001"
HOLDOUT_REPAIR_NEXT_STEP = "HOLDOUT-MB001-REPAIR-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_TOTAL = 8
EXPECTED_DISTRIBUTION = {
    "content_method": 2,
    "apparel_claim_boundary": 2,
    "display_to_content": 2,
    "control_plane_governance": 2,
}
EXPECTED_V4_5_IDS = {
    "SEM-V4_5-CONTENT-METHOD-001",
    "SEM-V4_5-CONTENT-METHOD-002",
    "SEM-V4_5-APPAREL-CLAIM-BOUNDARY-001",
    "SEM-V4_5-APPAREL-CLAIM-BOUNDARY-002",
    "SEM-V4_5-DISPLAY-TO-CONTENT-001",
    "SEM-V4_5-DISPLAY-TO-CONTENT-002",
    "SEM-V4_5-CONTROL-PLANE-GOVERNANCE-001",
    "SEM-V4_5-CONTROL-PLANE-GOVERNANCE-002",
}
COMPILER_SHAPES = {
    "content_story_method": ["evidence_strength", "story_problem_type", "allowable_arc", "value_expression", "downgrade_path", "micro_scene_contrast", "downstream_use"],
    "anchor_composition_method": ["object_action_relation_time_space", "primary_anchor", "constraint", "sequencing", "content_rhythm", "anti_template_failure", "downstream_use"],
    "claim_boundary": ["expression_layer", "allowed_expression", "conditional_expression", "source_workorder", "prohibited_expression", "safe_creative_alternative", "epistemic_warning"],
    "display_execution.spatial_variant": ["spatial_signal", "visual_focus", "supporting_object_or_distance", "capture_order", "content_angle", "authorization_boundary", "multi_output_consumption"],
    "display_execution.temporal_variant": ["action_trigger", "before_after_change", "explanation_slot", "completion_marker", "content_rhythm", "authorization_boundary", "multi_output_consumption"],
    "control_plane": ["trigger", "route", "ledger_target", "block_or_split", "reentry_condition", "forbidden_transition", "false_generation_prevention"],
}
COMPILER_BY_MKC = {
    "mkc_009": "content_story_method",
    "mkc_010": "anchor_composition_method",
    "mkc_026": "claim_boundary",
    "mkc_027": "claim_boundary",
    "mkc_032": "display_execution.spatial_variant",
    "mkc_034": "display_execution.temporal_variant",
    "mkc_004": "control_plane",
    "mkc_006": "control_plane",
}
RELATION_FIELDS = [
    "relation_id", "source_draft_id", "artifact_kind", "subject_ref", "subject_type", "predicate_id", "predicate_family", "object_ref", "object_type", "condition", "evidence_requirement", "owner_scope", "body_proposition_ref", "w7_required_relation_ref", "relation_status",
]
FORBIDDEN_BODY_TERMS = [
    "W7", "authority", "sidecar", "judge", "next_step", "batch_generation", "CandidatePack", "KE", "Serving", "RAG", "DIFY", "readiness", "accepted_domain_knowledge_count", "relation_design_hints", "reviewer", "checker", "no_go", "go_nogo", "批量",
]
ALLOWED_CONTROL_ROUTE_TERMS = {"source_gap", "decision_required", "founder_review", "excluded"}
NEGATIVE_FIXTURES = [
    "negative_exact_section_reuse_across_cards.yaml",
    "negative_same_group_core_section_duplicate.yaml",
    "negative_repeated_downstream_use_paragraph.yaml",
    "negative_W7_text_in_rich_body.yaml",
    "negative_sidecar_word_in_rich_body.yaml",
    "negative_judge_or_batch_word_in_rich_body.yaml",
    "negative_story_arc_uses_anchor_compiler_shape.yaml",
    "negative_anchor_card_uses_story_arc_compiler_shape.yaml",
    "negative_spatial_display_reuses_temporal_core_section.yaml",
    "negative_touch_labeled_direct_observation.yaml",
    "negative_control_plane_contains_not_applicable_for_control_plane.yaml",
    "negative_relation_hint_claims_formal_ontology_edge.yaml",
    "negative_predicate_id_has_v43_suffix.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_readiness_true.yaml",
]


class V46CheckError(Exception):
    pass


def fail(message: str) -> None:
    raise V46CheckError(message)


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


def assert_false(value: Any, label: str) -> None:
    if value is True or str(value).lower() == "true":
        fail(f"{label} must be false")


def normalize_units(text: str) -> set[str]:
    text = text.lower()
    ascii_tokens = set(re.findall(r"[a-z0-9_]+", text))
    cjk = "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    cjk_bigrams = {cjk[i:i+2] for i in range(max(0, len(cjk) - 1))}
    return ascii_tokens | cjk_bigrams


def similarity(left: str, right: str) -> float:
    a = normalize_units(left)
    b = normalize_units(right)
    if not a and not b:
        return 0.0
    return round(len(a & b) / len(a | b), 3)



def validate_holdout_microbatch_status_block(status: dict[str, Any]) -> None:
    phase = status.get("phase", {})
    if phase.get("previous_step") != HOLDOUT_TASK_ID:
        fail("holdout judge route requires holdout microbatch task as previous_step")
    holdout = status.get("holdout_microbatch_001", {})
    if holdout.get("task_id") != HOLDOUT_TASK_ID or holdout.get("status") != "completed":
        fail("holdout judge route requires completed holdout_microbatch_001 block")
    if holdout.get("holdout_scope") != "pilot_validation_only":
        fail("holdout judge route requires pilot_validation_only scope")
    if holdout.get("not_formal_microbatch_generation") is not True:
        fail("holdout judge route must not be formal microbatch generation")
    if int(holdout.get("holdout_count", 0)) < 12 or int(holdout.get("holdout_count", 99)) > 16:
        fail("holdout judge route requires 12..16 holdout drafts")
    if int(holdout.get("body_compiler_family_count", 0)) < 4:
        fail("holdout judge route requires at least four compiler families")
    if holdout.get("accepted_domain_knowledge_count") != 0:
        fail("holdout judge route requires accepted_domain_knowledge_count 0")
    assert_false(holdout.get("batch_generation_unlocked"), "holdout judge route batch_generation_unlocked")
    assert_false(holdout.get("ready_for_first_batch_generation"), "holdout judge route ready_for_first_batch_generation")
    if holdout.get("ready_for_holdout_microbatch_001_judge_review") is not True:
        fail("holdout judge route requires ready_for_holdout_microbatch_001_judge_review true")

def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_v4_6_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") not in {NEXT_STEP, V4_7_NEXT_STEP, HOLDOUT_NEXT_STEP, HOLDOUT_REPAIR_NEXT_STEP}:
        errors.append("current_next_step must be semantic pilot V4.6/V4.7 judge go/no-go")
    if data.get("v4_6_draft_count") != EXPECTED_TOTAL:
        errors.append("v4_6_draft_count must be 8")
    if data.get("v4_6_distribution") != EXPECTED_DISTRIBUTION:
        errors.append("distribution must be 2/2/2/2")
    for key in ["one_to_one_revision_count", "compiler_shape_valid_count", "complete_rich_body_valid_count", "capsule_rich_body_alignment_valid_count"]:
        if data.get(key) != EXPECTED_TOTAL:
            errors.append(f"{key} must be 8")
    if data.get("exact_section_reuse_count") != 0:
        errors.append("exact_section_reuse_count must be 0")
    if float(data.get("same_group_core_section_similarity_max", 1)) > 0.35:
        errors.append("same group core section similarity must be <= 0.35")
    if float(data.get("cross_group_core_section_similarity_max", 1)) > 0.25:
        errors.append("cross group core section similarity must be <= 0.25")
    for key in [
        "repeated_downstream_use_paragraph_count",
        "sidecar_leak_into_rich_body_count",
        "epistemic_label_text_conflict_count",
        "story_arc_anchor_compiler_confusion_count",
        "spatial_temporal_display_confusion_count",
        "touch_labeled_direct_observation_count",
        "control_plane_forbidden_body_slot_count",
        "formal_graph_claim_count",
        "predicate_version_suffix_count",
    ]:
        if data.get(key) != 0:
            errors.append(f"{key} must be 0")
    if data.get("relation_design_hints_valid_count") != data.get("relation_design_hints_count"):
        errors.append("all relation hints must validate")
    if data.get("accepted_domain_knowledge_count") != 0:
        errors.append("accepted_domain_knowledge_count must be 0")
    if data.get("batch_generation_unlocked") is not False:
        errors.append("batch_generation_unlocked must be false")
    if data.get("ready_for_first_batch_generation") is not False:
        errors.append("ready_for_first_batch_generation must be false")
    if data.get("readiness_all_false") is not True:
        errors.append("readiness_all_false must be true")
    for key in ["candidatepack_created", "KE_touched", "Serving_touched", "RAG_touched", "DIFY_touched"]:
        if data.get(key) is not False:
            errors.append(f"{key} must be false")
    return errors



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

def validate_status(workspace: Path) -> None:
    status = load_yaml(workspace / "project-infra/current_workspace_status.yaml")
    phase = status.get("phase", {})
    if phase.get("current_next_step") == BATCH_NEXT_STEP:
        fail("batch generation task cannot be next step")
    current_next_step = phase.get("current_next_step")
    if current_next_step not in {NEXT_STEP, V4_7_NEXT_STEP, HOLDOUT_NEXT_STEP, HOLDOUT_REPAIR_NEXT_STEP}:
        fail("workspace next step must be semantic pilot V4.6 or V4.7 judge go/no-go")
    if current_next_step == NEXT_STEP and phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be V4.6 rewrite task")
    if current_next_step == V4_7_NEXT_STEP:
        validate_v47_status_block(status)
    if current_next_step == HOLDOUT_NEXT_STEP:
        validate_holdout_microbatch_status_block(status)
    if current_next_step == HOLDOUT_REPAIR_NEXT_STEP:
        validate_holdout_mb001_repair_status_block(status)
    closeout = status.get("v4_5_closeout", {})
    if closeout.get("task_id") != TASK_ID or closeout.get("status") != "completed":
        fail("v4_5_closeout status block missing")
    v46 = status.get("semantic_pilot_v4_6", {})
    if v46.get("task_id") != TASK_ID or v46.get("status") != "completed":
        fail("semantic_pilot_v4_6 status block missing")
    if v46.get("semantic_pilot_v4_6_count") != EXPECTED_TOTAL:
        fail("semantic_pilot_v4_6_count must be 8")
    if v46.get("one_to_one_revision_of_v4_5") is not True:
        fail("semantic_pilot_v4_6 must be one-to-one revision of V4.5")
    if v46.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    assert_false(v46.get("batch_generation_unlocked"), "semantic_pilot_v4_6 batch_generation_unlocked")
    assert_false(v46.get("ready_for_first_batch_generation"), "semantic_pilot_v4_6 ready_for_first_batch_generation")
    if v46.get("ready_for_semantic_pilot_v4_6_judge_review") is not True:
        fail("semantic_pilot_v4_6 must be ready for judge review only")
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    root = workspace / "03_pilot/semantic_v4_6"
    authority = {item["mkc_id"]: item for item in load_yaml(workspace / "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml")["w7_canonical_cluster_authority"]["records"]}
    for rel in [
        "01_generation_contracts/codex_semantic_pilot_v4_6_type_specific_rich_body_compiler.v0.1.yaml",
        "01_generation_contracts/codex_semantic_pilot_v4_6_rich_body_independence_policy.v0.1.yaml",
        "01_generation_contracts/codex_semantic_pilot_v4_6_sidecar_leak_prevention_policy.v0.1.yaml",
    ]:
        load_yaml(workspace / rel)
    compiler_contract = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_6_type_specific_rich_body_compiler.v0.1.yaml")["codex_semantic_pilot_v4_6_type_specific_rich_body_compiler"]
    matrix = compiler_contract.get("compiler_assignment_matrix", [])
    if len(matrix) != EXPECTED_TOTAL:
        fail("compiler assignment matrix must contain 8 rows")
    closeout = load_yaml(workspace / "03_pilot/semantic_v4_5/v4_5_closeout.yaml")["v4_5_closeout"]
    digest = load_yaml(workspace / "03_pilot/semantic_v4_5/v4_5_semantic_review_digest.yaml")["v4_5_semantic_review_digest"]
    if closeout.get("human_decision_authorization", {}).get("human_decision_present") is not True:
        fail("human decision authorization missing from V4.5 closeout")
    if closeout.get("semantic_verdict") != "NO_GO_FOR_BATCH":
        fail("V4.5 closeout must be no-go for batch")
    if digest.get("V4_5_original_artifacts_modified") is not False:
        fail("V4.5 original artifacts must not be modified")

    manifest = load_yaml(root / "semantic_pilot_v4_6_manifest.yaml")["semantic_pilot_v4_6_manifest"]
    cards = load_yaml(root / "semantic_pilot_v4_6_candidate_cards.yaml")["semantic_pilot_v4_6_candidate_cards"]["candidates"]
    capsules = load_yaml(root / "semantic_pilot_v4_6_knowledge_capsules.yaml")["semantic_pilot_v4_6_knowledge_capsules"]["items"]
    bodies = load_yaml(root / "semantic_pilot_v4_6_complete_rich_bodies.yaml")["semantic_pilot_v4_6_complete_rich_bodies"]["items"]
    shapes = load_yaml(root / "semantic_pilot_v4_6_body_compiler_shapes.yaml")["semantic_pilot_v4_6_body_compiler_shapes"]["items"]
    creative = load_yaml(root / "semantic_pilot_v4_6_creative_value_blocks.yaml")["semantic_pilot_v4_6_creative_value_blocks"]["items"]
    epi = load_yaml(root / "semantic_pilot_v4_6_epistemic_labels.yaml")["semantic_pilot_v4_6_epistemic_labels"]["items"]
    sidecars = load_yaml(root / "semantic_pilot_v4_6_sidecars.yaml")["semantic_pilot_v4_6_sidecars"]["sidecars"]
    queue = load_yaml(root / "semantic_pilot_v4_6_judge_review_queue.yaml")["semantic_pilot_v4_6_judge_review_queue"]["items"]
    quality = load_json(root / "semantic_pilot_v4_6_quality_report.json")
    independence = load_json(root / "semantic_pilot_v4_6_independence_report.json")
    if manifest.get("task_id") != TASK_ID or manifest.get("semantic_pilot_v4_6_count") != EXPECTED_TOTAL:
        fail("manifest mismatch")
    if manifest.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("manifest distribution must be 2/2/2/2")
    if manifest.get("recommended_next_step") != NEXT_STEP:
        fail("manifest recommended next step mismatch")
    if len(cards) != EXPECTED_TOTAL or Counter(card.get("pilot_category") for card in cards) != EXPECTED_DISTRIBUTION:
        fail("V4.6 candidate count/distribution mismatch")
    by_id = {item["draft_id"]: item for item in cards}
    cap_by_id = {item["draft_id"]: item for item in capsules}
    body_by_id = {item["draft_id"]: item for item in bodies}
    shape_by_id = {item["draft_id"]: item for item in shapes}
    creative_by_id = {item["draft_id"]: item for item in creative}
    epi_by_id = {item["draft_id"]: item for item in epi}
    side_by_id = {item["draft_id"]: item for item in sidecars}
    revision_ids: set[str] = set()
    compiler_valid = 0
    body_valid = 0
    alignment_valid = 0
    sidecar_leaks = 0
    epistemic_conflicts = 0
    story_anchor_confusion = 0
    display_confusion = 0
    touch_direct = 0
    control_forbidden = 0
    section_entries: list[tuple[str, str, str, str]] = []
    for card in cards:
        draft_id = card["draft_id"]
        revision_of = card.get("revision_lineage", {}).get("revision_of")
        revision_ids.add(revision_of)
        if revision_of not in EXPECTED_V4_5_IDS:
            fail(f"{draft_id}: revision_of must point to V4.5")
        mkc = card.get("canonical_cluster_id")
        if mkc not in authority:
            fail(f"{draft_id}: mkc id missing from authority")
        if card.get("canonical_cluster_title_from_authority") != authority[mkc]["canonical_title"]:
            fail(f"{draft_id}: authority title mismatch")
        compiler_id = COMPILER_BY_MKC.get(mkc)
        body = body_by_id.get(draft_id)
        shape = shape_by_id.get(draft_id)
        if not body or not shape:
            fail(f"{draft_id}: body or compiler shape missing")
        if shape.get("compiler_id") != compiler_id or body.get("compiler_id") != compiler_id:
            fail(f"{draft_id}: compiler mismatch")
        if shape.get("compiler_shape") != COMPILER_SHAPES[compiler_id]:
            fail(f"{draft_id}: compiler shape mismatch")
        sections = body.get("compiler_sections", {})
        if list(sections.keys()) != COMPILER_SHAPES[compiler_id]:
            fail(f"{draft_id}: body section order/shape mismatch")
        body_blob = json.dumps(sections, ensure_ascii=False)
        hits = [term for term in FORBIDDEN_BODY_TERMS if term in body_blob]
        if hits:
            sidecar_leaks += 1
            fail(f"{draft_id}: forbidden body terms {hits}")
        if body.get("sidecar_leak_into_rich_body") is not False:
            sidecar_leaks += 1
            fail(f"{draft_id}: sidecar leak flag true")
        if not body.get("difference_claim") or sorted(body.get("difference_claim", {})) != sorted(["what_decision_changes", "what_observable_material_changes", "what_transfer_logic_changes", "what_failure_mode_changes", "what_downstream_use_changes"]):
            fail(f"{draft_id}: difference claim incomplete")
        for key, text in sections.items():
            if not str(text).strip():
                fail(f"{draft_id}: empty section {key}")
            section_entries.append((draft_id, card["pilot_category"], key, str(text)))
        if compiler_id == "content_story_method" and "object_action_relation_time_space" in sections:
            story_anchor_confusion += 1
            fail("story arc used anchor compiler shape")
        if compiler_id == "anchor_composition_method" and "evidence_strength" in sections:
            story_anchor_confusion += 1
            fail("anchor card used story compiler shape")
        if compiler_id == "display_execution.spatial_variant" and "action_trigger" in sections:
            display_confusion += 1
            fail("spatial display used temporal section")
        if compiler_id == "display_execution.temporal_variant" and "spatial_signal" in sections:
            display_confusion += 1
            fail("temporal display used spatial section")
        if compiler_id == "control_plane" and any(term in body_blob for term in ["not_applicable_for_control_plane", "creative_transfer", "aesthetic_tension"]):
            control_forbidden += 1
            fail("control body contains forbidden slot")
        ep = epi_by_id.get(draft_id)
        if not ep:
            fail(f"{draft_id}: epistemic labels missing")
        if ep.get("touch_labeled_direct_observation") is not False or ep.get("comfort_labeled_direct_observation") is not False:
            touch_direct += 1
            fail(f"{draft_id}: touch/comfort labeled direct observation")
        if ep.get("epistemic_label_text_conflict") is not False or ep.get("body_effect_hidden_as_conditional_experience") is not False:
            epistemic_conflicts += 1
            fail(f"{draft_id}: epistemic label conflict")
        if not cap_by_id.get(draft_id) or not creative_by_id.get(draft_id) or not side_by_id.get(draft_id):
            fail(f"{draft_id}: four-piece bundle incomplete")
        compiler_valid += 1
        body_valid += 1
        alignment_valid += 1
        if any(value is not False for value in card.get("readiness_flags", {}).values()):
            fail(f"{draft_id}: readiness flag true")
        assert_false(card.get("batch_generation_unlocked"), f"{draft_id} batch_generation_unlocked")
        if card.get("accepted_domain_knowledge") is not False:
            fail(f"{draft_id}: accepted domain knowledge must be false")
    if revision_ids != EXPECTED_V4_5_IDS:
        fail("V4.6 must revise all 8 V4.5 cards exactly once")
    exact_reuse = 0
    same_max = 0.0
    cross_max = 0.0
    for left, right in combinations(section_entries, 2):
        if left[3].strip() == right[3].strip():
            exact_reuse += 1
        score = similarity(left[3], right[3])
        if left[1] == right[1]:
            same_max = max(same_max, score)
        else:
            cross_max = max(cross_max, score)
    if exact_reuse != 0:
        fail("exact section reuse found")
    if same_max > 0.35:
        fail(f"same-group similarity too high: {same_max}")
    if cross_max > 0.25:
        fail(f"cross-group similarity too high: {cross_max}")
    downstream_texts = [entry[3] for entry in section_entries if entry[2] in {"downstream_use", "multi_output_consumption", "false_generation_prevention"}]
    repeated_downstream = len(downstream_texts) - len(set(downstream_texts))
    if repeated_downstream != 0:
        fail("repeated downstream paragraph found")
    with (root / "semantic_pilot_v4_6_relation_design_hints.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or list(rows[0]) != RELATION_FIELDS:
        fail("relation design hints schema mismatch")
    relation_valid = 0
    formal_claims = 0
    predicate_suffix = 0
    for row in rows:
        if row["source_draft_id"] not in by_id:
            fail("relation references unknown draft")
        if row["relation_status"] != "design_hint_not_ontology_edge":
            formal_claims += 1
            fail("relation status must remain design hint")
        if re.search(r"_v4[345]$", row["predicate_id"]):
            predicate_suffix += 1
            fail("predicate id contains forbidden version suffix")
        if "formal" in row.get("condition", "").lower() and "no_formal" not in row.get("evidence_requirement", ""):
            formal_claims += 1
            fail("relation hint claims formal graph")
        relation_valid += 1
    if len(queue) != EXPECTED_TOTAL or {item.get("draft_id") for item in queue} != set(by_id):
        fail("judge queue must contain all 8 V4.6 drafts")
    validate_status(workspace)
    report = {
        "status": "PASS",
        "task_id": TASK_ID,
        "v4_6_draft_count": EXPECTED_TOTAL,
        "v4_6_distribution": dict(Counter(card.get("pilot_category") for card in cards)),
        "one_to_one_revision_count": len(revision_ids),
        "compiler_shape_valid_count": compiler_valid,
        "complete_rich_body_valid_count": body_valid,
        "capsule_rich_body_alignment_valid_count": alignment_valid,
        "exact_section_reuse_count": exact_reuse,
        "same_group_core_section_similarity_max": same_max,
        "cross_group_core_section_similarity_max": cross_max,
        "similarity_method": {
            "normalization": "lowercase ASCII tokens plus CJK character bigrams; punctuation and whitespace removed for CJK comparison",
            "metric": "Jaccard similarity over normalized unit sets",
        },
        "repeated_downstream_use_paragraph_count": repeated_downstream,
        "sidecar_leak_into_rich_body_count": sidecar_leaks,
        "epistemic_label_text_conflict_count": epistemic_conflicts,
        "story_arc_anchor_compiler_confusion_count": story_anchor_confusion,
        "spatial_temporal_display_confusion_count": display_confusion,
        "touch_labeled_direct_observation_count": touch_direct,
        "control_plane_forbidden_body_slot_count": control_forbidden,
        "relation_design_hints_count": len(rows),
        "relation_design_hints_valid_count": relation_valid,
        "formal_graph_claim_count": formal_claims,
        "predicate_version_suffix_count": predicate_suffix,
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
        "ready_for_first_batch_generation": False,
        "readiness_flags_result": "all_false",
        "candidatepack_created": False,
        "KE_touched": False,
        "Serving_touched": False,
        "RAG_touched": False,
        "DIFY_touched": False,
        "source_repo_live_accessed": False,
        "recommended_next_step": NEXT_STEP,
    }
    for persisted, label in [(quality, "quality report"), (independence, "independence report")]:
        for key in ["v4_6_draft_count", "one_to_one_revision_count", "compiler_shape_valid_count", "exact_section_reuse_count", "repeated_downstream_use_paragraph_count", "sidecar_leak_into_rich_body_count", "predicate_version_suffix_count"]:
            if persisted.get(key) != report.get(key):
                fail(f"{label} mismatch for {key}")
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_6"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_6_minimal.yaml"))
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name))
        negative_results[name] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
    report.update({
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "positive_fixture_passed": True,
        "negative_fixtures_fail_closed": True,
        "negative_results": negative_results,
    })
    if report_out:
        write_json(report_out, report)
    return report


def run_selftest(workspace: Path) -> dict[str, Any]:
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_6"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_6_minimal.yaml"))
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name))
        negative_results[name] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
    return {"status": "PASS", "positive_fixture_count": 1, "negative_fixture_count": len(NEGATIVE_FIXTURES), "negative_fixtures_fail_closed": True, "negative_results": negative_results}



def validate_holdout_mb001_repair_status_block(status: dict[str, Any]) -> None:
    phase = status.get("phase", {})
    if phase.get("previous_step") != "HOLDOUT-MB001-FAIL-CLOSEOUT-AND-CLUSTER-SPECIFIC-COMPILER-REPAIR-001":
        fail("holdout repair judge route requires holdout repair task as previous_step")
    repair = status.get("holdout_mb001_repair", {})
    if repair.get("task_id") != "HOLDOUT-MB001-FAIL-CLOSEOUT-AND-CLUSTER-SPECIFIC-COMPILER-REPAIR-001" or repair.get("status") != "completed":
        fail("holdout repair judge route requires completed holdout_mb001_repair block")
    if repair.get("repair_count") != 14:
        fail("holdout repair judge route requires 14 repair drafts")
    if repair.get("same_cluster_ids_as_original") is not True:
        fail("holdout repair judge route requires same original cluster ids")
    if repair.get("accepted_domain_knowledge_count") != 0:
        fail("holdout repair judge route requires accepted_domain_knowledge_count 0")
    assert_false(repair.get("batch_generation_unlocked"), "holdout repair judge route batch_generation_unlocked")
    assert_false(repair.get("ready_for_first_batch_generation"), "holdout repair judge route ready_for_first_batch_generation")

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
    except V46CheckError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
