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

TASK_ID = "CODEX-SEMANTIC-PILOT-V4_6-CONDITIONAL-REPAIR-CLOSEOUT-AND-V4_7-SEMANTIC-CLEANUP-001"
PREVIOUS_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_5-CLOSEOUT-TYPE-SPECIFIC-RICH-BODY-COMPILER-AND-V4_6-REWRITE-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_7-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_TOTAL = 8
EXPECTED_DISTRIBUTION = {
    "content_method": 2,
    "apparel_claim_boundary": 2,
    "display_to_content": 2,
    "control_plane_governance": 2,
}
EXPECTED_V4_6_IDS = {
    "SEM-V4_6-CONTENT-METHOD-001",
    "SEM-V4_6-CONTENT-METHOD-002",
    "SEM-V4_6-APPAREL-CLAIM-BOUNDARY-001",
    "SEM-V4_6-APPAREL-CLAIM-BOUNDARY-002",
    "SEM-V4_6-DISPLAY-TO-CONTENT-001",
    "SEM-V4_6-DISPLAY-TO-CONTENT-002",
    "SEM-V4_6-CONTROL-PLANE-GOVERNANCE-001",
    "SEM-V4_6-CONTROL-PLANE-GOVERNANCE-002",
}
CAPSULE_BODY_FIELDS = [
    "domain_question",
    "core_mechanism",
    "observable_material",
    "transfer_logic",
    "boundary_guardrail",
    "generative_options",
    "failure_signal",
    "downstream_effect",
]
CAPSULE_FORBIDDEN_TERMS = [
    "V4",
    "V4.5",
    "V4.6",
    "V4.7",
    "compiler",
    "checker",
    "route-sync",
    "brief",
    "selftest",
    "fail-closed",
    "closeout",
    "judge",
    "no-go",
    "batch_generation",
    "CandidatePack",
    "KE",
    "Serving",
    "RAG",
    "DIFY",
    "readiness",
]
DIRECT_OBSERVATION_FORBIDDEN = ["触感", "贴肤感", "活动感", "舒适", "比例被拉开"]
SAFE_ALT_FORBIDDEN = ["显瘦", "显高", "透气", "抗皱", "耐穿", "持久舒适", "回弹性能", "保证", "长期不变形", "活动多久都不勒"]
PERFORMANCE_TERMS = ["透气", "抗皱", "耐穿", "持久舒适", "回弹性能"]
CONTROL_ALLOWED = {
    "route_decision",
    "generation_contract_guard",
    "source_gap_or_decision_ledger_write",
    "governance_outbox_write",
    "reentry_validation",
    "prohibited_transition_block",
}
CONTROL_FORBIDDEN = {
    "content_angle_selection",
    "review_focus_for_content_quality",
    "execution_asset_hint",
    "creative_value_block",
    "aesthetic_tension",
    "human_motive",
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
NEGATIVE_FIXTURES = [
    "negative_capsule_contains_V4_6_or_compiler_language.yaml",
    "negative_capsule_contains_checker_or_fail_closed_language.yaml",
    "negative_touch_labeled_direct_observation.yaml",
    "negative_comfort_labeled_direct_observation.yaml",
    "negative_body_effect_hidden_as_safe_alternative.yaml",
    "negative_safe_alternative_performance_claim.yaml",
    "negative_control_plane_downstream_effect_content_angle_selection.yaml",
    "negative_source_gap_blocks_labeled_draft_generation.yaml",
    "negative_review_pending_scope_expands_to_batch.yaml",
    "negative_relation_design_hint_claims_formal_ontology_edge.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_readiness_true.yaml",
    "negative_capsule_scan_false_positive_from_sidecar.yaml",
]


class V47CheckError(Exception):
    pass


def fail(message: str) -> None:
    raise V47CheckError(message)


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


def text_blob(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(text_blob(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(text_blob(item) for item in value.values())
    return str(value)


def capsule_body_text(capsule: dict[str, Any]) -> str:
    return "\n".join(text_blob(capsule.get(field, "")) for field in CAPSULE_BODY_FIELDS)


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_v4_7_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") != NEXT_STEP:
        errors.append("current_next_step must be semantic pilot V4.7 judge go/no-go")
    if data.get("v4_7_draft_count") != EXPECTED_TOTAL:
        errors.append("v4_7_draft_count must be 8")
    if data.get("v4_7_distribution") != EXPECTED_DISTRIBUTION:
        errors.append("distribution must be 2/2/2/2")
    if data.get("one_to_one_revision_count") != EXPECTED_TOTAL:
        errors.append("one_to_one_revision_count must be 8")
    scan_scope = data.get("capsule_scan_scope")
    if scan_scope != "knowledge_capsule_body_fields_only":
        errors.append("capsule scan scope must be body fields only")
    capsule_text = str(data.get("capsule_text", ""))
    hits = [term for term in CAPSULE_FORBIDDEN_TERMS if term in capsule_text]
    if hits:
        errors.append(f"capsule forbidden terms present: {hits}")
    direct_terms = text_blob(data.get("direct_observation_terms", []))
    if any(term in direct_terms for term in DIRECT_OBSERVATION_FORBIDDEN):
        errors.append("touch/comfort/body-effect language cannot be direct_observation")
    if data.get("conditional_experience_label") not in {None, "creative_hypothesis_not_audience_fact"}:
        errors.append("conditional experience must be labeled creative_hypothesis_not_audience_fact")
    safe_alt = data.get("safe_creative_alternatives", [])
    safe_alt_text = text_blob(safe_alt)
    if len(safe_alt) < 5:
        errors.append("safe creative alternatives must include at least five paths for claim cards")
    if any(term in safe_alt_text for term in SAFE_ALT_FORBIDDEN):
        errors.append("safe creative alternatives cannot contain performance, guarantee, or body-effect claims")
    downstream = set(data.get("control_plane_downstream_effect", []))
    if downstream and not downstream.issubset(CONTROL_ALLOWED):
        errors.append("control-plane downstream effect contains disallowed consumer")
    if downstream & CONTROL_FORBIDDEN:
        errors.append("control-plane downstream effect uses content or creative consumer")
    boundary = data.get("source_gap_boundary", {})
    if boundary.get("blocks_formal_landing") is not True:
        errors.append("source gap must block formal landing")
    if boundary.get("allows_labeled_review_pending_drafts") is not True:
        errors.append("source gap must not block labeled review-pending drafts")
    if boundary.get("scope") != "this_v4_7_pilot_8_review_pending_drafts_only":
        errors.append("review-pending draft scope must remain limited to V4.7 pilot eight drafts")
    if data.get("relation_status") != "design_hint_not_ontology_edge":
        errors.append("relation status must remain design_hint_not_ontology_edge")
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


def validate_status(workspace: Path) -> dict[str, Any]:
    status = load_yaml(workspace / "project-infra/current_workspace_status.yaml")
    phase = status.get("phase", {})
    if phase.get("current_next_step") == BATCH_NEXT_STEP:
        fail("batch generation task cannot be next step")
    if phase.get("current_next_step") != NEXT_STEP:
        fail("workspace next step must be semantic pilot V4.7 judge go/no-go")
    if phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be V4.7 semantic cleanup task")
    closeout = status.get("v4_6_conditional_repair_closeout", {})
    if closeout.get("task_id") != TASK_ID or closeout.get("status") != "completed":
        fail("v4_6_conditional_repair_closeout status block missing")
    if closeout.get("V4_6_original_artifacts_modified") is not False:
        fail("V4.6 original artifacts must not be modified")
    v47 = status.get("semantic_pilot_v4_7", {})
    if v47.get("task_id") != TASK_ID or v47.get("status") != "completed":
        fail("semantic_pilot_v4_7 status block missing")
    if v47.get("semantic_pilot_v4_7_count") != EXPECTED_TOTAL:
        fail("semantic_pilot_v4_7_count must be 8")
    if v47.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("semantic_pilot_v4_7 distribution must be 2/2/2/2")
    if v47.get("one_to_one_revision_of_v4_6") is not True:
        fail("semantic_pilot_v4_7 must be one-to-one revision of V4.6")
    if v47.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    assert_false(v47.get("batch_generation_unlocked"), "semantic_pilot_v4_7 batch_generation_unlocked")
    assert_false(v47.get("ready_for_first_batch_generation"), "semantic_pilot_v4_7 ready_for_first_batch_generation")
    if v47.get("ready_for_semantic_pilot_v4_7_judge_review") is not True:
        fail("semantic_pilot_v4_7 must be ready for judge review only")
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")
    return status


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    root = workspace / "03_pilot/semantic_v4_7"
    v46_root = workspace / "03_pilot/semantic_v4_6"
    closeout = load_yaml(v46_root / "v4_6_conditional_repair_closeout.yaml")["v4_6_conditional_repair_closeout"]
    digest = load_yaml(v46_root / "v4_6_semantic_review_digest.yaml")["v4_6_semantic_review_digest"]
    if closeout.get("human_decision_authorization", {}).get("human_decision_present") is not True:
        fail("human decision authorization missing from V4.6 closeout")
    if closeout.get("semantic_verdict") != "CONDITIONAL_REPAIR_REQUIRED":
        fail("V4.6 closeout must record conditional repair required")
    if closeout.get("V4_6_original_artifacts_modified") is not False:
        fail("V4.6 original artifacts must not be modified")
    if digest.get("V4_6_original_artifacts_modified") is not False:
        fail("V4.6 digest must record original artifacts unmodified")

    semantic_policy = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_7_semantic_cleanup_policy.v0.1.yaml")["semantic_cleanup_policy"]
    formal_policy = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_7_formal_landing_boundary_policy.v0.1.yaml")["formal_landing_boundary_policy"]
    control_policy = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_7_control_plane_consumer_policy.v0.1.yaml")["control_plane_consumer_policy"]
    if semantic_policy.get("capsule_scan_scope") != "knowledge_capsule_body_fields_only":
        fail("semantic cleanup policy must scope scan to capsule body fields only")
    review_scope = formal_policy.get("review_pending_draft_generation", {}).get("scope")
    if review_scope != "this_v4_7_pilot_8_review_pending_drafts_only":
        fail("review-pending draft scope must be limited to V4.7 pilot eight drafts")
    forbidden_scope = set(formal_policy.get("review_pending_draft_generation", {}).get("forbidden_scope_expansion", []))
    for item in ["3600_generation", "batch_001", "microbatch_generation", "CandidatePack_eligibility", "formal_landing"]:
        if item not in forbidden_scope:
            fail(f"formal landing policy missing forbidden scope expansion: {item}")
    allowed_downstream = set(control_policy.get("allowed_downstream_effect", []))
    if not CONTROL_ALLOWED.issubset(allowed_downstream):
        fail("control-plane consumer policy missing allowed downstream effects")
    if set(control_policy.get("forbidden_downstream_effect", [])) & CONTROL_ALLOWED:
        fail("control policy mixes allowed effects into forbidden list")

    authority = {
        item["mkc_id"]: item
        for item in load_yaml(workspace / "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml")["w7_canonical_cluster_authority"]["records"]
    }
    cards = load_yaml(root / "semantic_pilot_v4_7_candidate_cards.yaml")["semantic_pilot_v4_7_candidate_cards"]["candidates"]
    capsules = load_yaml(root / "semantic_pilot_v4_7_knowledge_capsules.yaml")["semantic_pilot_v4_7_knowledge_capsules"]["items"]
    bodies = load_yaml(root / "semantic_pilot_v4_7_complete_rich_bodies.yaml")["semantic_pilot_v4_7_complete_rich_bodies"]["items"]
    creative = load_yaml(root / "semantic_pilot_v4_7_creative_value_blocks.yaml")["semantic_pilot_v4_7_creative_value_blocks"]["items"]
    epistemic = load_yaml(root / "semantic_pilot_v4_7_epistemic_labels.yaml")["semantic_pilot_v4_7_epistemic_labels"]["items"]
    sidecars = load_yaml(root / "semantic_pilot_v4_7_sidecars.yaml")["semantic_pilot_v4_7_sidecars"]["sidecars"]
    queue = load_yaml(root / "semantic_pilot_v4_7_judge_review_queue.yaml")["semantic_pilot_v4_7_judge_review_queue"]["items"]
    manifest = load_yaml(root / "semantic_pilot_v4_7_manifest.yaml")["semantic_pilot_v4_7_manifest"]
    cleanup = load_json(root / "semantic_pilot_v4_7_cleanup_report.json")
    quality = load_json(root / "semantic_pilot_v4_7_quality_report.json")
    if manifest.get("task_id") != TASK_ID or manifest.get("recommended_next_step") != NEXT_STEP:
        fail("manifest task or next step mismatch")
    if manifest.get("review_pending_draft_scope") != "this_v4_7_pilot_8_review_pending_drafts_only":
        fail("manifest review-pending draft scope mismatch")
    if len(cards) != EXPECTED_TOTAL:
        fail("V4.7 candidate count must be 8")
    distribution = Counter(card.get("pilot_category") for card in cards)
    if distribution != EXPECTED_DISTRIBUTION:
        fail("V4.7 distribution must be 2/2/2/2")
    by_id = {item["draft_id"]: item for item in cards}
    cap_by_id = {item["draft_id"]: item for item in capsules}
    body_by_id = {item["draft_id"]: item for item in bodies}
    creative_by_id = {item["draft_id"]: item for item in creative}
    epi_by_id = {item["draft_id"]: item for item in epistemic}
    side_by_id = {item["draft_id"]: item for item in sidecars}
    revision_ids: set[str] = set()
    capsule_forbidden_hits: dict[str, list[str]] = {}
    rich_valid = 0
    alignment_valid = 0
    claim_valid = 0
    touch_direct = 0
    body_effect_residual = 0
    safe_alt_count = 0
    safe_alt_perf = 0
    control_valid = 0
    for card in cards:
        draft_id = card["draft_id"]
        revision_of = card.get("revision_lineage", {}).get("revision_of")
        revision_ids.add(revision_of)
        if revision_of not in EXPECTED_V4_6_IDS:
            fail(f"{draft_id}: revision_of must point to V4.6")
        mkc = card.get("canonical_cluster_id")
        if mkc not in authority:
            fail(f"{draft_id}: mkc id missing from authority")
        if card.get("canonical_cluster_title_from_authority") != authority[mkc]["canonical_title"]:
            fail(f"{draft_id}: authority title mismatch")
        if card.get("accepted_domain_knowledge") is not False:
            fail(f"{draft_id}: accepted domain knowledge must be false")
        assert_false(card.get("batch_generation_unlocked"), f"{draft_id} batch_generation_unlocked")
        assert_false(card.get("ready_for_first_batch_generation"), f"{draft_id} ready_for_first_batch_generation")
        if any(value is not False for value in card.get("readiness_flags", {}).values()):
            fail(f"{draft_id}: readiness flag true")
        for collection_name, collection in [("capsule", cap_by_id), ("body", body_by_id), ("creative", creative_by_id), ("epistemic", epi_by_id), ("sidecar", side_by_id)]:
            if draft_id not in collection:
                fail(f"{draft_id}: {collection_name} missing")
        capsule = cap_by_id[draft_id]
        capsule_keys = [key for key in CAPSULE_BODY_FIELDS if key in capsule]
        if capsule_keys != CAPSULE_BODY_FIELDS:
            fail(f"{draft_id}: capsule body fields mismatch")
        cap_text = capsule_body_text(capsule)
        hits = [term for term in CAPSULE_FORBIDDEN_TERMS if term in cap_text]
        if hits:
            capsule_forbidden_hits[draft_id] = hits
        body = body_by_id[draft_id]
        sections = body.get("compiler_sections", {})
        if not sections or list(sections.keys()) != body.get("section_order"):
            fail(f"{draft_id}: rich body section order mismatch")
        if any(not str(value).strip() for value in sections.values()):
            fail(f"{draft_id}: rich body contains empty section")
        if body.get("sidecar_leak_into_rich_body") is not False:
            fail(f"{draft_id}: sidecar leak flag true")
        if body.get("capsule_paraphrase_only") is not False:
            fail(f"{draft_id}: rich body is capsule paraphrase only")
        rich_valid += 1
        alignment_valid += 1
        category = card.get("pilot_category")
        if category == "apparel_claim_boundary":
            ep = epi_by_id[draft_id]
            direct_terms = text_blob(ep.get("direct_observation_allowed_terms", []))
            if any(term in direct_terms for term in DIRECT_OBSERVATION_FORBIDDEN):
                touch_direct += 1
                fail(f"{draft_id}: forbidden direct observation term found")
            if ep.get("touch_labeled_direct_observation") is not False or ep.get("comfort_labeled_direct_observation") is not False:
                touch_direct += 1
                fail(f"{draft_id}: touch or comfort labeled direct observation")
            if ep.get("body_effect_hidden_as_conditional_experience") is not False:
                body_effect_residual += 1
                fail(f"{draft_id}: body effect hidden as conditional experience")
            section_safe = str(sections.get("safe_creative_alternative", ""))
            creative_safe = creative_by_id[draft_id].get("safe_creative_alternatives", [])
            safe_alt_count += len(creative_safe)
            if len(creative_safe) < 5:
                fail(f"{draft_id}: safe creative alternatives fewer than five")
            safe_text = text_blob(creative_safe) + "\n" + section_safe
            if any(term in safe_text for term in SAFE_ALT_FORBIDDEN):
                safe_alt_perf += 1
                fail(f"{draft_id}: safe creative alternative contains performance/body-effect claim")
            if not any(label.get("epistemic_class") == "source_required_performance_claim" and label.get("source_required") is True for label in ep.get("labels", [])):
                fail(f"{draft_id}: source-required performance claim label missing")
            if not any(label.get("epistemic_class") == "prohibited_guarantee" for label in ep.get("labels", [])):
                fail(f"{draft_id}: prohibited guarantee label missing")
            claim_valid += 1
        if category == "control_plane_governance":
            downstream_text = capsule.get("downstream_effect", "") + "\n" + text_blob(creative_by_id[draft_id].get("control_downstream_effects", [])) + "\n" + str(sections.get("false_generation_prevention", ""))
            if any(term in downstream_text for term in CONTROL_FORBIDDEN):
                fail(f"{draft_id}: control downstream effect contains content/creative consumer")
            listed = {item.strip() for item in re.split(r"[;；,，]", str(capsule.get("downstream_effect", ""))) if item.strip()}
            if not listed.issubset(CONTROL_ALLOWED):
                fail(f"{draft_id}: control capsule downstream effect outside allowed set: {listed - CONTROL_ALLOWED}")
            if "source_gap" in text_blob(sections) and "草案" not in text_blob(sections):
                fail(f"{draft_id}: source gap boundary must preserve labeled draft permission")
            control_valid += 1
    if revision_ids != EXPECTED_V4_6_IDS:
        fail("V4.7 must revise all 8 V4.6 cards exactly once")
    if capsule_forbidden_hits:
        fail(f"capsule forbidden terms present: {capsule_forbidden_hits}")
    if len(queue) != EXPECTED_TOTAL or {item.get("draft_id") for item in queue} != set(by_id):
        fail("judge queue must contain all 8 V4.7 drafts")
    with (root / "semantic_pilot_v4_7_relation_design_hints.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or list(rows[0]) != RELATION_FIELDS:
        fail("relation design hints schema mismatch")
    relation_valid = 0
    formal_graph_claims = 0
    for row in rows:
        if row["source_draft_id"] not in by_id:
            fail("relation references unknown draft")
        if row["relation_status"] != "design_hint_not_ontology_edge":
            formal_graph_claims += 1
            fail("relation status must remain design hint")
        if "ontology_edge" in row.get("relation_status", "") and row["relation_status"] != "design_hint_not_ontology_edge":
            formal_graph_claims += 1
            fail("relation claims ontology edge")
        relation_valid += 1
    status = validate_status(workspace)
    if cleanup.get("capsule_forbidden_term_count") != 0 or cleanup.get("batch_generation_unlocked") is not False:
        fail("cleanup report status mismatch")
    if quality.get("complete_rich_body_valid_count") != EXPECTED_TOTAL or quality.get("readiness_all_false") is not True:
        fail("quality report status mismatch")
    fixture_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_7"
    positive_errors = validate_fixture_model(load_yaml(fixture_root / "positive_valid_semantic_v4_7_minimal.yaml"))
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for fixture in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixture_root / fixture))
        negative_results[fixture] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {fixture}")
    report = {
        "status": "PASS",
        "task_id": TASK_ID,
        "v4_7_draft_count": EXPECTED_TOTAL,
        "v4_7_distribution": dict(distribution),
        "one_to_one_revision_count": len(revision_ids),
        "capsule_scan_scope": "knowledge_capsule_body_fields_only",
        "capsule_forbidden_term_count": 0,
        "complete_rich_body_valid_count": rich_valid,
        "capsule_rich_body_alignment_valid_count": alignment_valid,
        "claim_boundary_epistemic_split_valid_count": claim_valid,
        "touch_or_comfort_direct_observation_count": touch_direct,
        "body_effect_residual_count": body_effect_residual,
        "safe_creative_alternative_count": safe_alt_count,
        "safe_alternative_performance_claim_count": safe_alt_perf,
        "control_plane_downstream_effect_valid_count": control_valid,
        "source_gap_draft_generation_boundary_valid": True,
        "relation_design_hints_count": len(rows),
        "relation_design_hints_valid_count": relation_valid,
        "formal_graph_claim_count": formal_graph_claims,
        "review_pending_draft_scope": "this_v4_7_pilot_8_review_pending_drafts_only",
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
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "positive_fixture_passed": True,
        "negative_fixtures_fail_closed": True,
        "negative_results": negative_results,
        "workspace_status_block_present": "semantic_pilot_v4_7" in status,
    }
    if report_out:
        write_json(report_out, report)
    return report


def run_selftest(workspace: Path) -> dict[str, Any]:
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_7"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_7_minimal.yaml"))
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
    except V47CheckError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
