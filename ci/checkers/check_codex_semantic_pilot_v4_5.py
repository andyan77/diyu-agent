#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

TASK_ID = "CODEX-SEMANTIC-PILOT-V4_4-CONDITIONAL-PASS-CLOSEOUT-AND-V4_5-CAPSULE-RICH-BODY-INTEGRATION-001"
PREVIOUS_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_3-NOGO-CLOSEOUT-CREATIVE-KNOWLEDGE-CAPSULE-AND-V4_4-REWRITE-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_5-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_TOTAL = 8
EXPECTED_DISTRIBUTION = {
    "content_method": 2,
    "apparel_claim_boundary": 2,
    "display_to_content": 2,
    "control_plane_governance": 2,
}
EXPECTED_V4_4_IDS = {
    "SEM-V4_4-CONTENT-METHOD-001",
    "SEM-V4_4-CONTENT-METHOD-002",
    "SEM-V4_4-APPAREL-CLAIM-BOUNDARY-001",
    "SEM-V4_4-APPAREL-CLAIM-BOUNDARY-002",
    "SEM-V4_4-DISPLAY-TO-CONTENT-001",
    "SEM-V4_4-DISPLAY-TO-CONTENT-002",
    "SEM-V4_4-CONTROL-PLANE-GOVERNANCE-001",
    "SEM-V4_4-CONTROL-PLANE-GOVERNANCE-002",
}
REQUIRED_RICH_BODY_SECTIONS = [
    "mechanism_chain",
    "observable_material",
    "transfer_logic",
    "boundary_logic",
    "contrast_or_micro_scenario",
    "anti_pattern",
    "downstream_use",
]
RELATION_FIELDS = [
    "relation_id",
    "source_draft_id",
    "artifact_kind",
    "subject_ref",
    "subject_type",
    "predicate_id",
    "predicate_family",
    "object_ref",
    "object_type",
    "condition",
    "evidence_requirement",
    "owner_scope",
    "body_proposition_ref",
    "w7_required_relation_ref",
    "relation_status",
]
REAL_INSTANCE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"SKU-[A-Z0-9-]+",
        r"品牌A",
        r"门店A",
        r"张三",
        r"李四",
        r"王女士",
        r"顾客说[:：]",
        r"某顾客反馈",
        r"actual brand",
        r"actual store",
        r"real SKU",
    ]
]
DIRECT_PUBLISH_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [r"直接发布脚本", r"发布文案如下", r"最终发布稿", r"ready to publish"]
]
SIDECAR_BODY_TERMS = ["readiness", "checker", "W7 authority", "batch eligibility", "CandidatePack"]
NEGATIVE_FIXTURES = [
    "negative_capsule_without_rich_body.yaml",
    "negative_rich_body_without_capsule.yaml",
    "negative_capsule_index_shell_only.yaml",
    "negative_rich_body_missing_required_section.yaml",
    "negative_rich_body_below_min_chars.yaml",
    "negative_repeated_capsule_paraphrase_only.yaml",
    "negative_sidecar_information_inside_rich_body.yaml",
    "negative_rich_body_contradicts_capsule.yaml",
    "negative_claim_boundary_missing_safe_alternatives.yaml",
    "negative_claim_boundary_treats_touch_as_direct_observation.yaml",
    "negative_safe_alternative_performance_claim.yaml",
    "negative_creative_hypothesis_marked_as_audience_fact.yaml",
    "negative_display_card_only_observation_checklist.yaml",
    "negative_control_plane_missing_excluded_route.yaml",
    "negative_control_plane_missing_multi_asset_conflict.yaml",
    "negative_invalid_relation_predicate.yaml",
    "negative_invalid_relation_status.yaml",
    "negative_formal_graph_claim.yaml",
    "negative_real_instance_fact_leak.yaml",
    "negative_direct_publish_script_leak.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_readiness_true.yaml",
]


class V45CheckError(Exception):
    pass


def fail(message: str) -> None:
    raise V45CheckError(message)


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


def zh_chars(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def contains_pattern(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_v4_5_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") != NEXT_STEP:
        errors.append("current_next_step must be semantic pilot V4.5 judge go/no-go")
    if data.get("v4_5_draft_count") != EXPECTED_TOTAL:
        errors.append("v4_5_draft_count must be 8")
    if data.get("v4_5_distribution") != EXPECTED_DISTRIBUTION:
        errors.append("distribution must be 2/2/2/2")
    if data.get("one_to_one_revision_count") != EXPECTED_TOTAL:
        errors.append("one_to_one_revision_count must be 8")
    for key in ["capsule_valid_count", "complete_rich_body_valid_count", "capsule_rich_body_alignment_valid_count", "creative_value_block_valid_count", "epistemic_label_valid_count"]:
        if data.get(key) != EXPECTED_TOTAL:
            errors.append(f"{key} must be 8")
    if data.get("all_required_rich_body_sections_present") is not True:
        errors.append("all rich body required sections must be present")
    if data.get("rich_body_min_zh_chars_met_count") != EXPECTED_TOTAL:
        errors.append("all rich bodies must meet min zh char count")
    for key in [
        "rich_body_repeated_capsule_padding_count",
        "sidecar_leak_into_rich_body_count",
        "index_shell_capsule_count",
        "creative_hypothesis_as_audience_fact_count",
        "relation_formal_graph_claim_count",
        "real_instance_fact_leak_count",
        "direct_publish_script_leak_count",
        "safe_alternative_performance_claim_count",
    ]:
        if data.get(key) != 0:
            errors.append(f"{key} must be 0")
    if data.get("claim_boundary_safe_alternatives_count", 0) < 10:
        errors.append("claim boundary safe alternatives must include at least 10 entries")
    if data.get("claim_boundary_split_valid_count") != 2:
        errors.append("two claim-boundary split records required")
    if data.get("control_plane_four_route_coverage_count") != 2:
        errors.append("two control-plane four-route records required")
    if data.get("multi_asset_conflict_rule_present_count") != 2:
        errors.append("two multi-asset conflict rules required")
    if data.get("relation_registry_valid_count") != data.get("relation_design_hints_count"):
        errors.append("all relation hints must validate against V4.3 predicate registry")
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


def validate_status(workspace: Path) -> None:
    status = load_yaml(workspace / "project-infra/current_workspace_status.yaml")
    phase = status.get("phase", {})
    if phase.get("current_next_step") == BATCH_NEXT_STEP:
        fail("batch generation task cannot be next step")
    if phase.get("current_next_step") != NEXT_STEP:
        fail("workspace next step must be semantic pilot V4.5 judge go/no-go")
    if phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be V4.5 integration task")
    closeout = status.get("v4_4_conditional_pass_closeout", {})
    if closeout.get("task_id") != TASK_ID or closeout.get("status") != "completed":
        fail("v4_4_conditional_pass_closeout status block missing")
    v45 = status.get("semantic_pilot_v4_5", {})
    if v45.get("task_id") != TASK_ID or v45.get("status") != "completed":
        fail("semantic_pilot_v4_5 status block missing")
    if v45.get("semantic_pilot_v4_5_count") != EXPECTED_TOTAL:
        fail("semantic_pilot_v4_5_count must be 8")
    if v45.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("semantic_pilot_v4_5 distribution must be 2/2/2/2")
    if v45.get("ready_for_semantic_pilot_v4_5_judge_review") is not True:
        fail("V4.5 must be ready for judge review only")
    if v45.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    assert_false(v45.get("batch_generation_unlocked"), "semantic_pilot_v4_5 batch_generation_unlocked")
    assert_false(v45.get("ready_for_first_batch_generation"), "semantic_pilot_v4_5 ready_for_first_batch_generation")
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")


def predicate_registry(workspace: Path) -> dict[str, dict[str, Any]]:
    registry = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_3_predicate_registry.v0.1.yaml")["codex_semantic_pilot_v4_3_predicate_registry"]
    profiles: dict[str, dict[str, Any]] = {}
    for profile in registry.get("profiles", []):
        profiles[profile["predicate_profile_id"]] = profile
    return profiles


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    v45_root = workspace / "03_pilot/semantic_v4_5"
    v44_root = workspace / "03_pilot/semantic_v4_4"
    authority = {
        item["mkc_id"]: item
        for item in load_yaml(workspace / "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml")["w7_canonical_cluster_authority"]["records"]
    }
    profiles = predicate_registry(workspace)
    for rel in [
        "01_generation_contracts/codex_semantic_pilot_v4_5_capsule_rich_body_integration_policy.v0.1.yaml",
        "01_generation_contracts/codex_semantic_pilot_v4_5_full_rich_body_standard.v0.1.yaml",
        "01_generation_contracts/codex_semantic_pilot_v4_5_epistemic_class_policy.v0.1.yaml",
    ]:
        load_yaml(workspace / rel)
    standard = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_5_full_rich_body_standard.v0.1.yaml")["codex_semantic_pilot_v4_5_full_rich_body_standard"]
    min_chars = int(standard.get("min_body_zh_chars", 0))
    if min_chars <= 0:
        fail("full rich body standard must define min_body_zh_chars")
    closeout = load_yaml(v44_root / "v4_4_conditional_pass_closeout.yaml")["v4_4_conditional_pass_closeout"]
    digest = load_yaml(v44_root / "v4_4_semantic_review_digest.yaml")["v4_4_semantic_review_digest"]
    if closeout.get("semantic_verdict") != "CONDITIONAL_PASS_FOR_CAPSULE_DIRECTION":
        fail("V4.4 closeout verdict mismatch")
    if closeout.get("human_decision_authorization", {}).get("human_decision_present") is not True:
        fail("founder human decision authorization missing")
    if digest.get("V4_4_original_artifacts_modified") is not False:
        fail("V4.4 original artifacts must not be modified")

    manifest = load_yaml(v45_root / "semantic_pilot_v4_5_manifest.yaml")["semantic_pilot_v4_5_manifest"]
    cards = load_yaml(v45_root / "semantic_pilot_v4_5_candidate_cards.yaml")["semantic_pilot_v4_5_candidate_cards"]["candidates"]
    capsules = load_yaml(v45_root / "semantic_pilot_v4_5_knowledge_capsules.yaml")["semantic_pilot_v4_5_knowledge_capsules"]["items"]
    bodies = load_yaml(v45_root / "semantic_pilot_v4_5_complete_rich_bodies.yaml")["semantic_pilot_v4_5_complete_rich_bodies"]["items"]
    creative_blocks = load_yaml(v45_root / "semantic_pilot_v4_5_creative_value_blocks.yaml")["semantic_pilot_v4_5_creative_value_blocks"]["items"]
    safe_items = load_yaml(v45_root / "semantic_pilot_v4_5_safe_creative_alternatives.yaml")["semantic_pilot_v4_5_safe_creative_alternatives"]["items"]
    epi_items = load_yaml(v45_root / "semantic_pilot_v4_5_epistemic_labels.yaml")["semantic_pilot_v4_5_epistemic_labels"]["items"]
    sidecars = load_yaml(v45_root / "semantic_pilot_v4_5_sidecars.yaml")["semantic_pilot_v4_5_sidecars"]["sidecars"]
    queue = load_yaml(v45_root / "semantic_pilot_v4_5_judge_review_queue.yaml")["semantic_pilot_v4_5_judge_review_queue"]["items"]
    quality = load_json(v45_root / "semantic_pilot_v4_5_quality_report.json")
    integration = load_json(v45_root / "semantic_pilot_v4_5_integration_report.json")

    if manifest.get("task_id") != TASK_ID:
        fail("manifest task id mismatch")
    if manifest.get("semantic_pilot_v4_5_count") != EXPECTED_TOTAL:
        fail("manifest count must be 8")
    if manifest.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("manifest distribution must be 2/2/2/2")
    if manifest.get("one_to_one_revision_of_v4_4") is not True:
        fail("manifest must declare one-to-one revision of V4.4")
    if manifest.get("recommended_next_step") != NEXT_STEP:
        fail("manifest recommended next step mismatch")
    if manifest.get("accepted_domain_knowledge_count") != 0 or manifest.get("batch_generation_unlocked") is not False:
        fail("manifest must keep no accepted knowledge and no batch unlock")
    if len(cards) != EXPECTED_TOTAL:
        fail("V4.5 candidate count must be 8")
    if Counter(card.get("pilot_category") for card in cards) != EXPECTED_DISTRIBUTION:
        fail("V4.5 distribution must be 2/2/2/2")

    capsule_by_id = {item["draft_id"]: item for item in capsules}
    body_by_id = {item["draft_id"]: item for item in bodies}
    creative_by_id = {item["draft_id"]: item for item in creative_blocks}
    safe_by_id = {item["draft_id"]: item for item in safe_items}
    epi_by_id = {item["draft_id"]: item for item in epi_items}
    sidecar_by_id = {item["draft_id"]: item for item in sidecars}
    draft_ids: set[str] = set()
    revision_ids: set[str] = set()
    capsule_valid = 0
    body_valid = 0
    alignment_valid = 0
    creative_valid = 0
    epi_valid = 0
    safe_count = 0
    claim_split_valid = 0
    control_route = 0
    multi_conflict = 0
    sidecar_leaks = 0
    capsule_shells = 0
    repeated_padding = 0
    real_leaks = 0
    publish_leaks = 0
    safe_perf_claims = 0
    creative_hypothesis_as_audience_fact = 0
    for card in cards:
        draft_id = card["draft_id"]
        draft_ids.add(draft_id)
        revision_of = card.get("revision_lineage", {}).get("revision_of")
        revision_ids.add(revision_of)
        if revision_of not in EXPECTED_V4_4_IDS:
            fail(f"{draft_id}: revision_of must point to V4.4")
        mkc_id = card.get("canonical_cluster_id")
        if mkc_id not in authority:
            fail(f"{draft_id}: mkc id missing from W7 authority")
        if card.get("canonical_cluster_title_from_authority") != authority[mkc_id]["canonical_title"]:
            fail(f"{draft_id}: authority title mismatch")
        if any(value is not False for value in card.get("readiness_flags", {}).values()):
            fail(f"{draft_id}: readiness flag true")
        assert_false(card.get("batch_generation_unlocked"), f"{draft_id} batch_generation_unlocked")
        if card.get("accepted_domain_knowledge") is not False:
            fail(f"{draft_id}: accepted_domain_knowledge must be false")
        text_blob = json.dumps(card, ensure_ascii=False)
        if contains_pattern(text_blob, REAL_INSTANCE_PATTERNS):
            real_leaks += 1
            fail(f"{draft_id}: real instance fact leak")
        if contains_pattern(text_blob, DIRECT_PUBLISH_PATTERNS):
            publish_leaks += 1
            fail(f"{draft_id}: direct publish script leak")
        capsule = capsule_by_id.get(draft_id)
        body = body_by_id.get(draft_id)
        block = creative_by_id.get(draft_id)
        epi = epi_by_id.get(draft_id)
        sidecar = sidecar_by_id.get(draft_id)
        if not capsule:
            fail(f"{draft_id}: capsule missing")
        if not body:
            fail(f"{draft_id}: complete rich body missing")
        if not block:
            fail(f"{draft_id}: creative/control block missing")
        if not epi:
            fail(f"{draft_id}: epistemic labels missing")
        if not sidecar:
            fail(f"{draft_id}: sidecar missing")
        required_capsule = ["capsule_question", "core_mechanism", "observable_material", "creative_transfer", "boundary_guardrail", "generative_options", "failure_signal", "downstream_effect"]
        if any(not capsule.get(key) for key in required_capsule):
            capsule_shells += 1
            fail(f"{draft_id}: capsule shell only")
        if not isinstance(capsule.get("generative_options"), list) or len(capsule.get("generative_options", [])) < 2:
            capsule_shells += 1
            fail(f"{draft_id}: capsule generative options missing")
        capsule_valid += 1
        sections = body.get("required_sections", {})
        missing_sections = [section for section in REQUIRED_RICH_BODY_SECTIONS if not str(sections.get(section, "")).strip()]
        if missing_sections:
            fail(f"{draft_id}: rich body missing sections {missing_sections}")
        body_text = "\n".join(str(sections[section]) for section in REQUIRED_RICH_BODY_SECTIONS)
        if zh_chars(body_text) < min_chars or int(body.get("body_zh_chars", 0)) < min_chars:
            fail(f"{draft_id}: rich body below min zh chars")
        if any(term in body_text for term in SIDECAR_BODY_TERMS):
            sidecar_leaks += 1
            fail(f"{draft_id}: sidecar/status information leaked into rich body")
        if body.get("capsule_alignment", {}).get("capsule_paraphrase_only") is True:
            repeated_padding += 1
            fail(f"{draft_id}: rich body repeats capsule as padding")
        if body.get("capsule_alignment", {}).get("rich_body_contradicts_capsule") is True:
            fail(f"{draft_id}: rich body contradicts capsule")
        mapping = body.get("capsule_alignment", {}).get("capsule_core_expanded_in_sections", {})
        for capsule_key in ["capsule_question", "core_mechanism", "observable_material", "creative_transfer", "boundary_guardrail", "failure_signal", "downstream_effect"]:
            if mapping.get(capsule_key) not in REQUIRED_RICH_BODY_SECTIONS:
                fail(f"{draft_id}: capsule key {capsule_key} not expanded in body")
        if body.get("sidecar_leak_into_rich_body") is not False:
            sidecar_leaks += 1
            fail(f"{draft_id}: sidecar leak flag true")
        if contains_pattern(json.dumps(body, ensure_ascii=False), REAL_INSTANCE_PATTERNS):
            real_leaks += 1
            fail(f"{draft_id}: real instance fact leak in body")
        if contains_pattern(json.dumps(body, ensure_ascii=False), DIRECT_PUBLISH_PATTERNS):
            publish_leaks += 1
            fail(f"{draft_id}: direct publish leak in body")
        body_valid += 1
        alignment_valid += 1
        category = card.get("pilot_category")
        if category in {"content_method", "display_to_content"}:
            dims = block.get("creative_value_dimensions", {})
            if len([value for value in dims.values() if value]) < 4:
                fail(f"{draft_id}: creative dimensions below 4")
            if block.get("creative_transfer_points_to_observable_material") is not True:
                fail(f"{draft_id}: creative transfer must point to observable material")
            if block.get("audience_cognition_shift_is_specific") is not True:
                fail(f"{draft_id}: audience cognition shift not specific")
        elif category == "apparel_claim_boundary":
            safe = safe_by_id.get(draft_id)
            if not safe:
                fail(f"{draft_id}: safe alternatives missing")
            for field in ["direct_observation_sentence", "conditional_experience_sentence", "styling_context_sentence", "scene_or_role_expression", "aesthetic_direction"]:
                if not safe.get(field):
                    fail(f"{draft_id}: safe alternative field missing {field}")
            safe_count += 5
            split = safe.get("split", {})
            for key in ["direct_observation", "conditional_experience_expression", "source_required_performance_claim", "prohibited_guarantee"]:
                if not split.get(key):
                    fail(f"{draft_id}: claim split missing {key}")
            if safe.get("comfort_or_touch_as_direct_observation") is not False:
                fail(f"{draft_id}: touch/comfort treated as direct observation")
            if safe.get("safe_alternative_performance_claim") is not False:
                safe_perf_claims += 1
                fail(f"{draft_id}: safe alternative is performance claim")
            claim_split_valid += 1
        elif category == "control_plane_governance":
            routes = block.get("four_route_coverage", {})
            if set(routes) != {"source_gap", "decision_required", "founder_review", "excluded"}:
                fail(f"{draft_id}: control-plane four routes missing")
            conflict = block.get("multi_asset_conflict_rule", {})
            if conflict.get("trigger") != "one_input_maps_to_multiple_asset_surfaces_without_authorized_split":
                fail(f"{draft_id}: multi_asset_conflict trigger missing")
            if block.get("creative_weight_not_applicable") is not True:
                fail(f"{draft_id}: control-plane creative weight must be not applicable")
            if block.get("not_counted_as_creative_domain_quality_pass") is not True:
                fail(f"{draft_id}: control-plane counted as creative pass")
            control_route += 1
            multi_conflict += 1
        if epi.get("creative_hypothesis_marked_as_audience_fact") is not False:
            creative_hypothesis_as_audience_fact += 1
            fail(f"{draft_id}: creative hypothesis marked as audience fact")
        if epi.get("audience_fact_without_source_count") != 0 or epi.get("performance_claim_without_source_count") != 0:
            fail(f"{draft_id}: epistemic source-required count nonzero")
        if epi.get("comfort_or_touch_as_direct_observation") is not False:
            fail(f"{draft_id}: comfort/touch direct observation flag true")
        if epi.get("prohibited_guarantee_present") is not False:
            fail(f"{draft_id}: prohibited guarantee present")
        epi_valid += 1
        creative_valid += 1
    if revision_ids != EXPECTED_V4_4_IDS:
        fail("V4.5 must revise all 8 V4.4 cards exactly once")

    with (v45_root / "semantic_pilot_v4_5_relation_design_hints.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        fail("relation design hints csv is empty")
    if list(rows[0]) != RELATION_FIELDS:
        fail("relation design hints schema mismatch")
    card_by_id = {card["draft_id"]: card for card in cards}
    relation_valid = 0
    formal_claims = 0
    by_card = Counter()
    for row in rows:
        draft_id = row["source_draft_id"]
        if draft_id not in draft_ids:
            fail(f"relation references unknown draft: {draft_id}")
        if row["relation_status"] != "design_hint_not_ontology_edge":
            fail("relation status must remain design_hint_not_ontology_edge")
        if "formal" in row.get("relation_status", "") or "ontology_edge" == row.get("relation_status"):
            formal_claims += 1
            fail("relation hint claims formal graph edge")
        card = card_by_id[draft_id]
        profile = profiles.get(card.get("predicate_profile_id"))
        if not profile:
            fail(f"{draft_id}: profile missing in V4.3 registry")
        allowed = {item["predicate_id"]: item for item in profile.get("allowed_predicates", [])}
        predicate = row["predicate_id"]
        if predicate not in allowed:
            fail(f"{draft_id}: invalid predicate {predicate}")
        if row["predicate_family"] != allowed[predicate]["predicate_family"]:
            fail(f"{draft_id}: predicate family mismatch")
        if row["artifact_kind"] != card["artifact_kind"]:
            fail(f"{draft_id}: relation artifact kind mismatch")
        relation_valid += 1
        by_card[draft_id] += 1
    if any(count < 2 or count > 5 for count in by_card.values()):
        fail("each V4.5 card must have 2..5 relation design hints")
    if len(queue) != EXPECTED_TOTAL or {item.get("draft_id") for item in queue} != draft_ids:
        fail("judge queue must contain all 8 V4.5 drafts")
    if any(item.get("review_status") != "pending" for item in queue):
        fail("judge queue must remain pending")
    if not (v45_root / "semantic_pilot_v4_5_judge_protocol.md").exists():
        fail("judge protocol missing")
    validate_status(workspace)

    report = {
        "status": "PASS",
        "task_id": TASK_ID,
        "v4_5_draft_count": EXPECTED_TOTAL,
        "v4_5_distribution": dict(Counter(card.get("pilot_category") for card in cards)),
        "one_to_one_revision_count": len(revision_ids),
        "capsule_valid_count": capsule_valid,
        "complete_rich_body_valid_count": body_valid,
        "capsule_rich_body_alignment_valid_count": alignment_valid,
        "creative_value_block_valid_count": creative_valid,
        "safe_creative_alternatives_count": safe_count,
        "epistemic_label_valid_count": epi_valid,
        "control_plane_four_route_coverage": control_route,
        "multi_asset_conflict_rule_present": multi_conflict == 2,
        "multi_asset_conflict_rule_present_count": multi_conflict,
        "sidecar_leak_into_rich_body_count": sidecar_leaks,
        "index_shell_capsule_count": capsule_shells,
        "rich_body_repeated_capsule_padding_count": repeated_padding,
        "relation_design_hints_count": len(rows),
        "relation_registry_valid_count": relation_valid,
        "relation_design_hints_valid_against_v4_3_predicate_registry": relation_valid == len(rows),
        "relation_formal_graph_claim_count": formal_claims,
        "real_instance_fact_leak_count": real_leaks,
        "direct_publish_script_leak_count": publish_leaks,
        "safe_alternative_performance_claim_count": safe_perf_claims,
        "creative_hypothesis_as_audience_fact_count": creative_hypothesis_as_audience_fact,
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
    for persisted, label in [(quality, "quality report"), (integration, "integration report")]:
        for key in [
            "v4_5_draft_count",
            "one_to_one_revision_count",
            "capsule_rich_body_alignment_valid_count",
            "sidecar_leak_into_rich_body_count",
            "relation_design_hints_count",
            "relation_formal_graph_claim_count",
            "accepted_domain_knowledge_count",
        ]:
            if persisted.get(key) != report.get(key):
                fail(f"{label} mismatch for {key}")
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_5"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_5_minimal.yaml"))
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
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_5"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_5_minimal.yaml"))
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name))
        negative_results[name] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
    return {
        "status": "PASS",
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "negative_fixtures_fail_closed": True,
        "negative_results": negative_results,
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
    except V45CheckError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
