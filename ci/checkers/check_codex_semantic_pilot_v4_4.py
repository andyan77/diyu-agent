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

TASK_ID = "CODEX-SEMANTIC-PILOT-V4_3-NOGO-CLOSEOUT-CREATIVE-KNOWLEDGE-CAPSULE-AND-V4_4-REWRITE-001"
PREVIOUS_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_2-NOGO-CLOSEOUT-PREDICATE-REGISTRY-AND-V4_3-TARGETED-REPAIR-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_4-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_TOTAL = 8
EXPECTED_DISTRIBUTION = {
    "content_method": 2,
    "apparel_claim_boundary": 2,
    "display_to_content": 2,
    "control_plane_governance": 2,
}
EXPECTED_V4_3_IDS = {
    "SEM-V4_3-CONTENT-METHOD-001",
    "SEM-V4_3-CONTENT-METHOD-002",
    "SEM-V4_3-APPAREL-CLAIM-BOUNDARY-001",
    "SEM-V4_3-APPAREL-CLAIM-BOUNDARY-002",
    "SEM-V4_3-DISPLAY-TO-CONTENT-001",
    "SEM-V4_3-DISPLAY-TO-CONTENT-002",
    "SEM-V4_3-CONTROL-PLANE-GOVERNANCE-001",
    "SEM-V4_3-CONTROL-PLANE-GOVERNANCE-002",
}
CAPSULE_SECTIONS = {
    "capsule_question",
    "core_mechanism",
    "observable_material",
    "creative_transfer",
    "boundary_guardrail",
    "generative_options",
    "failure_signal",
    "downstream_effect",
}
CREATIVE_REQUIRED_DIMS = {
    "sensory_or_visual_anchor",
    "aesthetic_tension",
    "emotional_or_human_motive",
    "cross_domain_transfer",
    "generative_option_space",
    "audience_cognition_shift",
}
SAFE_ALTERNATIVE_FIELDS = {
    "direct_observation_sentence",
    "conditional_experience_sentence",
    "styling_context_sentence",
    "scene_or_role_expression",
    "aesthetic_direction",
}
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
DIRECT_PUBLISH_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in [r"直接发布脚本", r"发布文案如下", r"最终发布稿", r"ready to publish"]]
GENERIC_SHIFT = {"提升认知", "增强理解", "更有感觉"}
ADJECTIVE_STACK_TERMS = {"高级", "松弛", "氛围", "精致", "优雅", "温柔", "高级感"}
NEGATIVE_FIXTURES = [
    "negative_creative_card_missing_aesthetic_tension.yaml",
    "negative_creative_card_missing_generative_option_space.yaml",
    "negative_content_method_treats_emotion_as_evidence.yaml",
    "negative_display_card_only_observation_checklist.yaml",
    "negative_display_card_missing_content_angle_transfer.yaml",
    "negative_claim_boundary_only_says_forbidden_without_safe_alternatives.yaml",
    "negative_claim_boundary_allows_unconditioned_body_effect_claim.yaml",
    "negative_claim_boundary_treats_experience_as_direct_observation.yaml",
    "negative_control_plane_forced_into_creative_value_weight.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_readiness_true.yaml",
    "negative_real_instance_fact_leak.yaml",
    "negative_direct_publish_script_leak.yaml",
    "negative_generative_options_synonym_only.yaml",
    "negative_pure_aesthetic_adjective_stack.yaml",
    "negative_audience_cognition_shift_generic.yaml",
]


class V44CheckError(Exception):
    pass


def fail(message: str) -> None:
    raise V44CheckError(message)


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


def contains_pattern(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_v4_4_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") != NEXT_STEP:
        errors.append("current_next_step must be semantic pilot V4.4 judge go/no-go")
    if data.get("v4_4_draft_count") != EXPECTED_TOTAL:
        errors.append("v4_4_draft_count must be 8")
    if data.get("v4_4_distribution") != EXPECTED_DISTRIBUTION:
        errors.append("distribution must be 2/2/2/2")
    if data.get("one_to_one_revision_count") != EXPECTED_TOTAL:
        errors.append("one_to_one_revision_count must be 8")
    if data.get("knowledge_capsule_valid_count") != EXPECTED_TOTAL:
        errors.append("all 8 knowledge capsules must be valid")
    if int(data.get("creative_cards_min_dimension_count", 0)) < 4:
        errors.append("creative cards require at least 4 creative dimensions")
    for key in [
        "creative_cards_missing_aesthetic_tension_count",
        "creative_cards_missing_generative_option_space_count",
        "content_method_emotion_as_evidence_count",
        "display_observation_checklist_only_count",
        "claim_boundary_unconditioned_body_effect_claim_count",
        "claim_boundary_experience_as_direct_observation_count",
        "control_plane_creative_weight_forced_count",
        "real_instance_fact_leak_count",
        "direct_publish_script_count",
        "generative_options_synonym_only_count",
        "pure_aesthetic_adjective_stack_count",
        "audience_cognition_shift_generic_count",
    ]:
        if data.get(key) != 0:
            errors.append(f"{key} must be 0")
    if data.get("display_content_angle_transfer_valid_count") != 2:
        errors.append("two display content-angle transfers required")
    if data.get("claim_boundary_safe_alternatives_count", 0) < 10:
        errors.append("claim boundary safe alternatives must include at least 10 entries total")
    if data.get("control_plane_creative_weight_not_applicable_count") != 2:
        errors.append("two control-plane cards must mark creative weight not applicable")
    if data.get("relation_registry_valid_count") != data.get("relation_design_hints_count"):
        errors.append("all relation hints must validate against registry")
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
        fail("workspace next step must be semantic pilot V4.4 judge go/no-go")
    if phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be V4.4 creative capsule task")
    v44 = status.get("semantic_pilot_v4_4", {})
    if v44.get("task_id") != TASK_ID or v44.get("status") != "completed":
        fail("semantic_pilot_v4_4 status block missing")
    if v44.get("semantic_pilot_v4_4_count") != EXPECTED_TOTAL:
        fail("semantic_pilot_v4_4 count must be 8")
    if v44.get("one_to_one_revision_of_v4_3") is not True:
        fail("semantic_pilot_v4_4 must be one-to-one revision of V4.3")
    if v44.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    assert_false(v44.get("batch_generation_unlocked"), "semantic_pilot_v4_4 batch_generation_unlocked")
    assert_false(v44.get("ready_for_first_batch_generation"), "semantic_pilot_v4_4 ready_for_first_batch_generation")
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    v44_root = workspace / "03_pilot/semantic_v4_4"
    authority_records = load_yaml(workspace / "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml")["w7_canonical_cluster_authority"]["records"]
    authority = {record["mkc_id"]: record for record in authority_records}
    registry = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_3_predicate_registry.v0.1.yaml")["codex_semantic_pilot_v4_3_predicate_registry"]
    profiles = {profile["predicate_profile_id"]: profile for profile in registry.get("profiles", [])}
    for rel in [
        "01_generation_contracts/codex_semantic_pilot_v4_4_creative_knowledge_capsule_policy.v0.1.yaml",
        "01_generation_contracts/codex_semantic_pilot_v4_4_creative_value_dimension_contract.v0.1.yaml",
        "01_generation_contracts/codex_semantic_pilot_v4_4_safe_creative_alternatives_policy.v0.1.yaml",
    ]:
        load_yaml(workspace / rel)
    closeout = load_yaml(workspace / "03_pilot/semantic_v4_3/v4_3_no_go_closeout.yaml")["v4_3_no_go_closeout"]
    digest = load_yaml(workspace / "03_pilot/semantic_v4_3/v4_3_semantic_review_digest.yaml")["v4_3_semantic_review_digest"]
    if closeout.get("semantic_verdict") != "NO_GO_FOR_BATCH":
        fail("V4.3 closeout must record NO_GO_FOR_BATCH")
    if closeout.get("human_decision_authorization", {}).get("human_decision_present") is not True:
        fail("human decision authorization missing from closeout")
    if digest.get("human_decision_present") is not True:
        fail("semantic review digest must record human decision")

    manifest = load_yaml(v44_root / "semantic_pilot_v4_4_manifest.yaml")["semantic_pilot_v4_4_manifest"]
    cards = load_yaml(v44_root / "semantic_pilot_v4_4_candidate_cards.yaml")["semantic_pilot_v4_4_candidate_cards"]["candidates"]
    capsules = load_yaml(v44_root / "semantic_pilot_v4_4_knowledge_capsules.yaml")["semantic_pilot_v4_4_knowledge_capsules"]["items"]
    creative_blocks = load_yaml(v44_root / "semantic_pilot_v4_4_creative_value_blocks.yaml")["semantic_pilot_v4_4_creative_value_blocks"]["items"]
    safe_items = load_yaml(v44_root / "semantic_pilot_v4_4_safe_creative_alternatives.yaml")["semantic_pilot_v4_4_safe_creative_alternatives"]["items"]
    sidecars = load_yaml(v44_root / "semantic_pilot_v4_4_sidecars.yaml")["semantic_pilot_v4_4_sidecars"]["sidecars"]
    queue = load_yaml(v44_root / "semantic_pilot_v4_4_judge_review_queue.yaml")["semantic_pilot_v4_4_judge_review_queue"]["items"]
    creative_report = load_json(v44_root / "semantic_pilot_v4_4_creative_value_report.json")
    quality_report = load_json(v44_root / "semantic_pilot_v4_4_quality_report.json")

    if manifest.get("task_id") != TASK_ID:
        fail("manifest task id mismatch")
    if manifest.get("semantic_pilot_v4_4_count") != EXPECTED_TOTAL:
        fail("manifest count must be 8")
    if manifest.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("manifest distribution must be 2/2/2/2")
    if manifest.get("one_to_one_revision_of_v4_3") is not True:
        fail("manifest must declare one-to-one revision of V4.3")
    if manifest.get("recommended_next_step") != NEXT_STEP:
        fail("manifest recommended next step mismatch")
    if len(cards) != EXPECTED_TOTAL:
        fail("V4.4 candidate count must be 8")
    if Counter(card.get("pilot_category") for card in cards) != EXPECTED_DISTRIBUTION:
        fail("V4.4 distribution must be 2/2/2/2")
    capsule_by_id = {item["draft_id"]: item for item in capsules}
    creative_by_id = {item["draft_id"]: item for item in creative_blocks}
    safe_by_id = {item["draft_id"]: item for item in safe_items}
    sidecar_by_id = {item["draft_id"]: item for item in sidecars}
    draft_ids: set[str] = set()
    revision_ids: set[str] = set()
    knowledge_capsule_valid_count = 0
    creative_coverage: dict[str, int] = {}
    safe_count = 0
    display_transfer = 0
    claim_split = 0
    control_not_applicable = 0
    real_instance_fact_leak_count = 0
    direct_publish_script_count = 0
    synonym_only_count = 0
    adjective_stack_count = 0
    generic_shift_count = 0
    for card in cards:
        draft_id = card["draft_id"]
        draft_ids.add(draft_id)
        revision_of = card.get("revision_lineage", {}).get("revision_of")
        revision_ids.add(revision_of)
        if revision_of not in EXPECTED_V4_3_IDS:
            fail(f"{draft_id}: revision_of must point to V4.3")
        mkc_id = card.get("canonical_cluster_id")
        if mkc_id not in authority:
            fail(f"{draft_id}: mkc id missing from authority")
        if card.get("canonical_cluster_title_from_authority") != authority[mkc_id]["canonical_title"]:
            fail(f"{draft_id}: authority title mismatch")
        profile_id = card.get("predicate_profile_id")
        if profile_id not in profiles:
            fail(f"{draft_id}: unknown predicate profile")
        if any(value is not False for value in card.get("readiness_flags", {}).values()):
            fail(f"{draft_id}: readiness flag true")
        assert_false(card.get("batch_generation_unlocked"), f"{draft_id} batch_generation_unlocked")
        if card.get("accepted_domain_knowledge") is not False:
            fail(f"{draft_id}: accepted_domain_knowledge must be false")
        text_blob = json.dumps(card, ensure_ascii=False)
        if contains_pattern(text_blob, REAL_INSTANCE_PATTERNS):
            real_instance_fact_leak_count += 1
            fail(f"{draft_id}: real instance fact leak")
        if contains_pattern(text_blob, DIRECT_PUBLISH_PATTERNS):
            direct_publish_script_count += 1
            fail(f"{draft_id}: direct publish script leak")
        capsule = capsule_by_id.get(draft_id)
        if not capsule:
            fail(f"{draft_id}: knowledge capsule missing")
        missing = [section for section in CAPSULE_SECTIONS if not capsule.get(section)]
        if missing:
            fail(f"{draft_id}: missing capsule sections {missing}")
        options = capsule.get("generative_options", [])
        if not isinstance(options, list) or len(options) < 3:
            fail(f"{draft_id}: generative_options must contain at least three options")
        option_prefixes = {str(option).split("：", 1)[0].strip() for option in options}
        if len(option_prefixes) < 3:
            synonym_only_count += 1
            fail(f"{draft_id}: generative options appear synonym-only")
        if not capsule.get("observable_material") or not capsule.get("creative_transfer"):
            fail(f"{draft_id}: observable material and creative transfer required")
        knowledge_capsule_valid_count += 1
        block = creative_by_id.get(draft_id)
        if not block:
            fail(f"{draft_id}: creative value block missing")
        category = card.get("pilot_category")
        if category in {"content_method", "display_to_content"}:
            dims = block.get("creative_value_dimensions", {})
            coverage = len([key for key in CREATIVE_REQUIRED_DIMS if dims.get(key)])
            creative_coverage[draft_id] = coverage
            if coverage < 4:
                fail(f"{draft_id}: creative value dimension coverage below 4")
            if not dims.get("aesthetic_tension"):
                fail(f"{draft_id}: aesthetic tension missing")
            if not dims.get("generative_option_space"):
                fail(f"{draft_id}: generative option dimension missing")
            shift = dims.get("audience_cognition_shift", "")
            if any(term == shift.strip() for term in GENERIC_SHIFT):
                generic_shift_count += 1
                fail(f"{draft_id}: audience cognition shift is generic")
            if block.get("creative_transfer_observable_material_ref") != capsule.get("observable_material"):
                fail(f"{draft_id}: creative transfer must reference observable material")
            if block.get("pure_aesthetic_adjective_stack") is True:
                adjective_stack_count += 1
                fail(f"{draft_id}: pure aesthetic adjective stack")
            if category == "content_method" and "情绪只能作为表达方向" not in capsule.get("boundary_guardrail", "") and "不得虚构真实人物" not in capsule.get("boundary_guardrail", ""):
                fail(f"{draft_id}: content method must not treat emotion as evidence")
            if category == "display_to_content":
                if "内容角度" not in capsule.get("creative_transfer", "") and "内容" not in capsule.get("creative_transfer", ""):
                    fail(f"{draft_id}: display card missing content angle transfer")
                display_transfer += 1
        elif category == "apparel_claim_boundary":
            safe = safe_by_id.get(draft_id)
            if not safe:
                fail(f"{draft_id}: safe creative alternatives missing")
            present = [field for field in SAFE_ALTERNATIVE_FIELDS if safe.get(field)]
            if len(present) < len(SAFE_ALTERNATIVE_FIELDS):
                fail(f"{draft_id}: not enough safe creative alternatives")
            safe_count += len(present)
            split = safe.get("split", {})
            for key in ["direct_observation", "conditional_experience_expression", "source_required_performance_claim", "prohibited_guarantee"]:
                if not split.get(key):
                    fail(f"{draft_id}: claim boundary split missing {key}")
            if safe.get("unconditioned_body_effect_claim_allowed") is not False:
                fail(f"{draft_id}: unconditioned body effect claim allowed")
            if safe.get("experience_claim_as_direct_observation") is not False:
                fail(f"{draft_id}: experience claim treated as direct observation")
            claim_split += 1
        elif category == "control_plane_governance":
            if block.get("creative_weight_not_applicable") is not True:
                fail(f"{draft_id}: control-plane creative weight must be not applicable")
            if block.get("not_counted_as_creative_domain_quality_pass") is not True:
                fail(f"{draft_id}: control-plane card counted as creative pass")
            if not block.get("operational_insight_summary") or not block.get("why_this_prevents_false_generation"):
                fail(f"{draft_id}: control-plane operational insight missing")
            if any(term in card.get("canonical_body_zh", "") for term in ["美学张力", "情绪", "温度"]):
                fail(f"{draft_id}: control-plane body forced into creative language")
            control_not_applicable += 1
        if not sidecar_by_id.get(draft_id):
            fail(f"{draft_id}: sidecar missing")
    if revision_ids != EXPECTED_V4_3_IDS:
        fail("V4.4 must revise all 8 V4.3 cards exactly once")

    with (v44_root / "semantic_pilot_v4_4_relation_design_hints.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        fail("relation design hints csv is empty")
    if list(rows[0]) != RELATION_FIELDS:
        fail("relation design hints schema mismatch")
    by_card = Counter()
    card_by_id = {card["draft_id"]: card for card in cards}
    relation_valid = 0
    for row in rows:
        draft_id = row["source_draft_id"]
        if draft_id not in draft_ids:
            fail(f"relation references unknown draft: {draft_id}")
        card = card_by_id[draft_id]
        profile = profiles[card["predicate_profile_id"]]
        allowed = {item["predicate_id"]: item for item in profile.get("allowed_predicates", [])}
        predicate = row["predicate_id"]
        if predicate not in allowed:
            fail(f"{draft_id}: predicate not allowed for profile {card['predicate_profile_id']}: {predicate}")
        if row["predicate_family"] != allowed[predicate]["predicate_family"]:
            fail(f"{draft_id}: predicate family mismatch")
        if row["artifact_kind"] != card["artifact_kind"]:
            fail(f"{draft_id}: relation artifact kind mismatch")
        if row["relation_status"] != "design_hint_not_ontology_edge":
            fail("relation status must remain design_hint_not_ontology_edge")
        relation_valid += 1
        by_card[draft_id] += 1
    if any(count < 2 or count > 5 for count in by_card.values()):
        fail("each card must have 2..5 relation design hints")
    if len(queue) != EXPECTED_TOTAL or {item.get("draft_id") for item in queue} != draft_ids:
        fail("judge queue must contain all 8 V4.4 drafts")
    if any(item.get("review_status") != "pending" for item in queue):
        fail("judge queue must remain pending")
    if not (v44_root / "semantic_pilot_v4_4_judge_protocol.md").exists():
        fail("judge protocol missing")
    validate_status(workspace)

    recomputed = {
        "status": "PASS",
        "task_id": TASK_ID,
        "v4_4_draft_count": EXPECTED_TOTAL,
        "v4_4_distribution": dict(Counter(card.get("pilot_category") for card in cards)),
        "one_to_one_revision_count": len(revision_ids),
        "knowledge_capsule_valid_count": knowledge_capsule_valid_count,
        "creative_value_dimension_coverage_by_creative_card": creative_coverage,
        "safe_creative_alternatives_count": safe_count,
        "display_content_angle_transfer_valid_count": display_transfer,
        "claim_boundary_observation_experience_performance_split_valid_count": claim_split,
        "control_plane_creative_weight_not_applicable_count": control_not_applicable,
        "relation_design_hints_count": len(rows),
        "relation_registry_valid_count": relation_valid,
        "real_instance_fact_leak_count": real_instance_fact_leak_count,
        "direct_publish_script_count": direct_publish_script_count,
        "generative_options_synonym_only_count": synonym_only_count,
        "pure_aesthetic_adjective_stack_count": adjective_stack_count,
        "audience_cognition_shift_generic_count": generic_shift_count,
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
        "ready_for_first_batch_generation": False,
        "candidatepack_created": False,
        "KE_touched": False,
        "Serving_touched": False,
        "RAG_touched": False,
        "DIFY_touched": False,
        "readiness_flags_result": "all_false",
        "source_repo_live_accessed": False,
        "recommended_next_step": NEXT_STEP,
    }
    for report, label in [(creative_report, "creative value report"), (quality_report, "quality report")]:
        for key in [
            "knowledge_capsule_valid_count",
            "safe_creative_alternatives_count",
            "display_content_angle_transfer_valid_count",
            "claim_boundary_observation_experience_performance_split_valid_count",
            "control_plane_creative_weight_not_applicable_count",
        ]:
            if report.get(key) != recomputed.get(key):
                fail(f"{label} mismatch for {key}")
    if quality_report.get("relation_registry_valid_count") != relation_valid:
        fail("quality report relation registry count mismatch")

    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_4"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_4_minimal.yaml"))
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name))
        negative_results[name] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
    report = {
        **recomputed,
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "positive_fixture_passed": True,
        "negative_fixtures_fail_closed": True,
        "negative_results": negative_results,
    }
    if report_out:
        write_json(report_out, report)
    return report


def run_selftest(workspace: Path) -> dict[str, Any]:
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_4"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_4_minimal.yaml"))
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
    except V44CheckError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
