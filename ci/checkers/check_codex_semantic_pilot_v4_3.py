#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

TASK_ID = "CODEX-SEMANTIC-PILOT-V4_2-NOGO-CLOSEOUT-PREDICATE-REGISTRY-AND-V4_3-TARGETED-REPAIR-001"
PREVIOUS_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_1-NOGO-CLOSEOUT-AND-V4_2-TYPE-SPECIFIC-REWRITE-001"
V4_4_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_3-NOGO-CLOSEOUT-CREATIVE-KNOWLEDGE-CAPSULE-AND-V4_4-REWRITE-001"
V4_5_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_4-CONDITIONAL-PASS-CLOSEOUT-AND-V4_5-CAPSULE-RICH-BODY-INTEGRATION-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_3-JUDGE-GO-NOGO-001"
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
EXPECTED_V4_2_IDS = {
    "SEM-V4_2-CONTENT-METHOD-001",
    "SEM-V4_2-CONTENT-METHOD-002",
    "SEM-V4_2-APPAREL-CLAIM-BOUNDARY-001",
    "SEM-V4_2-APPAREL-CLAIM-BOUNDARY-002",
    "SEM-V4_2-DISPLAY-TO-CONTENT-001",
    "SEM-V4_2-DISPLAY-TO-CONTENT-002",
    "SEM-V4_2-CONTROL-PLANE-GOVERNANCE-001",
    "SEM-V4_2-CONTROL-PLANE-GOVERNANCE-002",
}
STRICT_ARTIFACT_KINDS = {
    "general_knowledge_candidate",
    "control_plane_candidate",
    "cso_outbox_candidate",
    "execution_asset_outbox_candidate",
    "governance_outbox_candidate",
    "source_gap",
    "decision_packet",
}
FORBIDDEN_STRICT_VALUES = {"claim_boundary", "asset_binding_policy_candidate"}
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
REQUIRED_BLOCKS_BY_PROFILE = {
    "general_knowledge_candidate": {
        "definition",
        "decision_matrix_for_story_arc_or_anchor_choice",
        "input_signal_to_method_selection",
        "failure_downgrade_path",
        "difference_from_neighbor_cluster",
    },
    "claim_boundary": {
        "claim_type_ladder",
        "allowed_expression_examples",
        "restricted_expression_examples",
        "prohibited_expression_examples",
        "evidence_threshold_by_claim_strength",
        "source_workorder_hint",
    },
    "execution_asset_outbox_candidate": {
        "input_condition",
        "observation_target",
        "ordered_steps",
        "camera_or_explanation_slot",
        "completion_condition",
        "stop_condition",
        "authorization_or_privacy_boundary",
    },
    "control_plane_candidate": {"trigger", "route_target", "ledger_write", "reentry", "prohibited_transition"},
    "asset_binding_policy_candidate": {
        "asset_stub_shape",
        "bindability_condition",
        "forbidden_binding",
        "review_only_label",
        "non_production_seal",
        "reslice_target",
        "governance_outbox_route",
    },
}
NEGATIVE_FIXTURES = [
    "negative_claim_boundary_uses_maps_zone_to_shot_task.yaml",
    "negative_display_execution_uses_blocks_production_binding.yaml",
    "negative_control_plane_uses_camera_predicate.yaml",
    "negative_human_review_used_as_route_target_without_founder_review_mapping.yaml",
    "negative_decision_packet_without_decision_id.yaml",
    "negative_asset_binding_policy_mislabeled_as_decision_packet.yaml",
    "negative_claim_boundary_missing_source_workorder_hint.yaml",
    "negative_display_execution_missing_completion_condition.yaml",
    "negative_predicate_registry_missing_artifact_kind.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_readiness_true.yaml",
    "negative_claim_boundary_written_to_strict_artifact_kind.yaml",
    "negative_asset_binding_policy_written_to_strict_artifact_kind.yaml",
]


class V43CheckError(Exception):
    pass


def fail(message: str) -> None:
    raise V43CheckError(message)


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
    data = model.get("semantic_v4_3_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") not in {NEXT_STEP, V4_4_NEXT_STEP, V4_5_NEXT_STEP}:
        errors.append("current_next_step must be semantic pilot V4.3/V4.4/V4.5 judge go/no-go")
    if data.get("v4_3_draft_count") != EXPECTED_TOTAL:
        errors.append("v4_3_draft_count must be 8")
    if data.get("v4_3_distribution") != EXPECTED_DISTRIBUTION:
        errors.append("distribution must be 2/2/2/2")
    if data.get("one_to_one_revision_count") != EXPECTED_TOTAL:
        errors.append("one_to_one_revision_count must be 8")
    if data.get("predicate_profile_count") != 5 or data.get("relation_profile_count") != 5:
        errors.append("five predicate/relation profiles required")
    if data.get("strict_artifact_kind_illegal_value_count") != 0:
        errors.append("strict artifact kind illegal value count must be 0")
    relation_count = data.get("relation_design_hints_count", 0)
    if relation_count < 20 or relation_count > 32:
        errors.append("relation_design_hints_count must be 20..32")
    if data.get("predicate_registry_valid_relation_count") != relation_count:
        errors.append("all relation hints must validate against predicate registry")
    if data.get("fixed_three_relations_per_card") is True:
        errors.append("fixed three relations per card is forbidden")
    if data.get("prohibited_cross_type_predicate_count") != 0:
        errors.append("prohibited cross-type predicate count must be 0")
    if data.get("claim_boundary_source_workorder_hint_count") != 2:
        errors.append("two claim-boundary source workorder hints required")
    if data.get("display_execution_major_fix_valid_count") != 2:
        errors.append("two display execution major fixes required")
    if data.get("control_plane_001_founder_review_policy_valid") is not True:
        errors.append("control_plane_001 must route risk-sensitive review to founder_review")
    if data.get("control_plane_002_resliced_to") != "asset_binding_policy_candidate":
        errors.append("control_plane_002 must be resliced to asset_binding_policy_candidate profile")
    if data.get("control_plane_002_strict_artifact_kind") != "governance_outbox_candidate":
        errors.append("control_plane_002 strict artifact kind must be governance_outbox_candidate")
    if data.get("decision_packet_without_decision_instance_count") != 0:
        errors.append("decision packet without decision instance count must be 0")
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
    if current_next_step not in {NEXT_STEP, V4_4_NEXT_STEP, V4_5_NEXT_STEP}:
        fail("workspace next step must be semantic pilot V4.3 judge go/no-go or semantic pilot V4.4 judge go/no-go")
    if current_next_step == NEXT_STEP and phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be V4.3 targeted repair task")
    if current_next_step == V4_4_NEXT_STEP and phase.get("previous_step") != V4_4_TASK_ID:
        fail("workspace previous step must be V4.4 creative capsule task")
    closeout = status.get("v4_2_no_go_closeout", {})
    if closeout.get("task_id") != TASK_ID or closeout.get("status") != "completed":
        fail("v4_2_no_go_closeout status block missing")
    if closeout.get("semantic_verdict") != "NO_GO_FOR_BATCH":
        fail("V4.2 semantic verdict must be NO_GO_FOR_BATCH")
    v43 = status.get("semantic_pilot_v4_3", {})
    if v43.get("task_id") != TASK_ID or v43.get("status") != "completed":
        fail("semantic_pilot_v4_3 status block missing")
    if v43.get("semantic_pilot_v4_3_count") != EXPECTED_TOTAL:
        fail("semantic_pilot_v4_3_count must be 8")
    if v43.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("semantic_pilot_v4_3 distribution must be 2/2/2/2")
    if v43.get("one_to_one_revision_of_v4_2") is not True:
        fail("semantic_pilot_v4_3 must be one-to-one revision of V4.2")
    if v43.get("accepted_domain_knowledge_count") != 0:
        fail("semantic_pilot_v4_3 accepted_domain_knowledge_count must be 0")
    assert_false(v43.get("batch_generation_unlocked"), "semantic_pilot_v4_3 batch_generation_unlocked")
    assert_false(v43.get("ready_for_first_batch_generation"), "semantic_pilot_v4_3 ready_for_first_batch_generation")
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


def validate_registry(workspace: Path) -> dict[str, dict[str, Any]]:
    registry = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_3_predicate_registry.v0.1.yaml")[
        "codex_semantic_pilot_v4_3_predicate_registry"
    ]
    if registry.get("task_id") != TASK_ID:
        fail("predicate registry task id mismatch")
    if registry.get("registry_status") != "draft_predicate_profile_registry_not_formal_ontology":
        fail("predicate registry must remain a draft profile registry")
    if registry.get("strict_enum_change_authorized") is not False:
        fail("strict enum change must not be authorized")
    profiles = {profile["predicate_profile_id"]: profile for profile in registry.get("profiles", [])}
    if set(profiles) != set(REQUIRED_BLOCKS_BY_PROFILE):
        fail(f"predicate profiles mismatch: {sorted(profiles)}")
    for forbidden in FORBIDDEN_STRICT_VALUES:
        if forbidden not in registry.get("forbidden_strict_artifact_kind_values", []):
            fail(f"forbidden strict value missing from registry: {forbidden}")
    for profile_id, profile in profiles.items():
        maps_to = profile.get("maps_to", {})
        strict = maps_to.get("strict_owner_model", {})
        artifact = strict.get("artifact_kind")
        if artifact in FORBIDDEN_STRICT_VALUES:
            fail(f"{profile_id}: forbidden profile written to strict artifact_kind")
        if artifact not in STRICT_ARTIFACT_KINDS:
            fail(f"{profile_id}: strict artifact_kind not allowed by schema: {artifact}")
        if not profile.get("relation_profile_id"):
            fail(f"{profile_id}: relation_profile_id missing")
        allowed = {item.get("predicate_id"): item for item in profile.get("allowed_predicates", [])}
        if not allowed:
            fail(f"{profile_id}: no allowed predicates")
        for item in allowed.values():
            if item.get("predicate_family") not in profile.get("allowed_predicate_families", []):
                fail(f"{profile_id}: predicate family not in allowed list")
    return profiles


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    v43_root = workspace / "03_pilot/semantic_v4_3"
    profiles = validate_registry(workspace)
    policy = load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_3_targeted_repair_policy.v0.1.yaml")[
        "codex_semantic_pilot_v4_3_targeted_repair_policy"
    ]
    if policy.get("human_decision", {}).get("semantic_verdict") != "NO_GO_FOR_BATCH":
        fail("repair policy must record NO_GO_FOR_BATCH")
    if policy.get("control_plane_002_reslice_decision", {}).get("strict_owner_model", {}).get("artifact_kind") != "governance_outbox_candidate":
        fail("control_plane_002 strict owner decision must be governance_outbox_candidate")
    closeout = load_yaml(workspace / "03_pilot/semantic_v4_2/v4_2_no_go_closeout.yaml")["v4_2_no_go_closeout"]
    digest = load_yaml(workspace / "03_pilot/semantic_v4_2/v4_2_semantic_review_digest.yaml")["v4_2_semantic_review_digest"]
    for item, label in [(closeout, "closeout"), (digest, "digest")]:
        if item.get("human_decision_present") is not True:
            fail(f"V4.2 {label} human decision missing")
        if item.get("engineering_delivery") != "PASS":
            fail(f"V4.2 {label} engineering delivery must be PASS")
        if item.get("semantic_verdict") != "NO_GO_FOR_BATCH":
            fail(f"V4.2 {label} semantic verdict must be NO_GO_FOR_BATCH")
    manifest = load_yaml(v43_root / "semantic_pilot_v4_3_manifest.yaml")["semantic_pilot_v4_3_manifest"]
    cards = load_yaml(v43_root / "semantic_pilot_v4_3_candidate_cards.yaml")["semantic_pilot_v4_3_candidate_cards"]["candidates"]
    rich_blocks = load_yaml(v43_root / "semantic_pilot_v4_3_rich_body_blocks.yaml")["semantic_pilot_v4_3_rich_body_blocks"]["blocks"]
    type_blocks = load_yaml(v43_root / "semantic_pilot_v4_3_type_specific_body_blocks.yaml")["semantic_pilot_v4_3_type_specific_body_blocks"]["items"]
    sidecars = load_yaml(v43_root / "semantic_pilot_v4_3_sidecars.yaml")["semantic_pilot_v4_3_sidecars"]["sidecars"]
    workorders = load_yaml(v43_root / "semantic_pilot_v4_3_source_workorder_hints.yaml")["semantic_pilot_v4_3_source_workorder_hints"]["items"]
    reslice = load_yaml(v43_root / "semantic_pilot_v4_3_reslice_report.yaml")["semantic_pilot_v4_3_reslice_report"]["items"]
    queue = load_yaml(v43_root / "semantic_pilot_v4_3_judge_review_queue.yaml")["semantic_pilot_v4_3_judge_review_queue"]["items"]
    usage_report = load_json(v43_root / "semantic_pilot_v4_3_predicate_usage_report.json")
    quality_report = load_json(v43_root / "semantic_pilot_v4_3_quality_report.json")

    if manifest.get("task_id") != TASK_ID:
        fail("manifest task id mismatch")
    if manifest.get("semantic_pilot_v4_3_count") != EXPECTED_TOTAL:
        fail("manifest count must be 8")
    if manifest.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("manifest distribution must be 2/2/2/2")
    if manifest.get("one_to_one_revision_of_v4_2") is not True:
        fail("manifest must declare one-to-one revision of V4.2")
    if manifest.get("recommended_next_step") != NEXT_STEP:
        fail("manifest next step must be V4.3 judge go/no-go")

    if len(cards) != EXPECTED_TOTAL:
        fail("V4.3 candidate count must be 8")
    if Counter(card.get("pilot_category") for card in cards) != EXPECTED_DISTRIBUTION:
        fail("V4.3 distribution must be 2/2/2/2")
    rich_by_id = {item["draft_id"]: item for item in rich_blocks}
    type_by_id = {item["draft_id"]: item for item in type_blocks}
    sidecar_by_id = {item["draft_id"]: item for item in sidecars}
    draft_ids: set[str] = set()
    revision_ids: set[str] = set()
    illegal_artifact_count = 0
    claim_source_needed = 0
    display_major_valid = 0
    control1_founder = False
    control2_resliced = False
    decision_packet_without_decision = 0
    for card in cards:
        draft_id = card["draft_id"]
        draft_ids.add(draft_id)
        lineage = card.get("revision_lineage", {})
        revision_ids.add(lineage.get("revision_of"))
        if lineage.get("revision_of") not in EXPECTED_V4_2_IDS:
            fail(f"{draft_id}: revision_of must point to V4.2")
        profile_id = card.get("predicate_profile_id")
        if profile_id not in profiles:
            fail(f"{draft_id}: unknown predicate profile")
        expected_strict = profiles[profile_id]["maps_to"]["strict_owner_model"]["artifact_kind"]
        artifact = card.get("owner_model", {}).get("artifact_kind")
        if artifact in FORBIDDEN_STRICT_VALUES or card.get("artifact_kind") in FORBIDDEN_STRICT_VALUES:
            illegal_artifact_count += 1
            fail(f"{draft_id}: profile name written to strict artifact_kind")
        if artifact != expected_strict or card.get("artifact_kind") != expected_strict:
            fail(f"{draft_id}: strict artifact kind must match profile maps_to")
        if artifact not in STRICT_ARTIFACT_KINDS:
            fail(f"{draft_id}: artifact kind not allowed by strict schema")
        body = card.get("canonical_body_zh", "")
        if rich_by_id.get(draft_id, {}).get("canonical_body_zh") != body:
            fail(f"{draft_id}: rich body mirror mismatch")
        block_item = type_by_id.get(draft_id)
        if not block_item:
            fail(f"{draft_id}: missing type-specific block item")
        block_ids = {block.get("block_id") for block in block_item.get("blocks", [])}
        missing = REQUIRED_BLOCKS_BY_PROFILE[profile_id] - block_ids
        if missing:
            fail(f"{draft_id}: missing required blocks {sorted(missing)}")
        sidecar = sidecar_by_id.get(draft_id)
        if not sidecar:
            fail(f"{draft_id}: missing sidecar")
        sidecar_artifact = sidecar.get("schema_compatibility", {}).get("strict_owner_model", {}).get("artifact_kind")
        if sidecar_artifact != artifact:
            fail(f"{draft_id}: sidecar strict artifact mismatch")
        if any(value is not False for value in card.get("readiness_flags", {}).values()):
            fail(f"{draft_id}: readiness flag true")
        assert_false(card.get("batch_generation_unlocked"), f"{draft_id} batch_generation_unlocked")
        if card.get("accepted_domain_knowledge") is not False:
            fail(f"{draft_id}: accepted_domain_knowledge must be false")
        if profile_id == "claim_boundary" and card.get("source_status", {}).get("source_readiness") == "source_workorder_needed":
            claim_source_needed += 1
        if profile_id == "execution_asset_outbox_candidate" and sidecar.get("repair_level") == "major_fix":
            display_major_valid += 1
        if draft_id == "SEM-V4_3-CONTROL-PLANE-GOVERNANCE-001":
            route = sidecar.get("route_target_policy", {})
            control1_founder = route.get("required_route_target") == "founder_review" and route.get("human_review_as_superclass_only") is True and "founder_review" in body
        if draft_id == "SEM-V4_3-CONTROL-PLANE-GOVERNANCE-002":
            if artifact == "decision_packet":
                decision_packet_without_decision += 1
            res = sidecar.get("reslice", {})
            control2_resliced = (
                card.get("resliced_to_profile") == "asset_binding_policy_candidate"
                and res.get("resliced_to_profile") == "asset_binding_policy_candidate"
                and artifact == "governance_outbox_candidate"
                and card.get("owner_model", {}).get("storage_target") == "GovernanceOutbox"
            )
    if revision_ids != EXPECTED_V4_2_IDS:
        fail("V4.3 must revise all 8 V4.2 cards exactly once")
    if claim_source_needed != 2:
        fail("two claim-boundary source workorder-needed cards required")
    if len(workorders) != 2 or {item.get("draft_id") for item in workorders} != {
        "SEM-V4_3-APPAREL-CLAIM-BOUNDARY-001",
        "SEM-V4_3-APPAREL-CLAIM-BOUNDARY-002",
    }:
        fail("claim-boundary source workorder hints missing")
    for item in workorders:
        if item.get("candidatepack_eligibility") is not False or item.get("batch_exemplar_eligibility") is not False:
            fail("source workorder hints must block CandidatePack and batch exemplar")
    if display_major_valid != 2:
        fail("two display execution major fixes required")
    if not control1_founder:
        fail("control_plane_001 founder_review route policy invalid")
    if not control2_resliced:
        fail("control_plane_002 must be resliced to asset_binding_policy_candidate profile")
    if len(reslice) != 1 or reslice[0].get("strict_owner_model", {}).get("artifact_kind") != "governance_outbox_candidate":
        fail("reslice report must record governance_outbox_candidate strict artifact kind")

    with (v43_root / "semantic_pilot_v4_3_relation_design_hints.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        fail("relation design hints csv is empty")
    if list(rows[0]) != RELATION_FIELDS:
        fail("relation design hints schema mismatch")
    if len(rows) < 20 or len(rows) > 32:
        fail("relation design hints total must be 20..32")
    by_card = Counter()
    predicate_counts = Counter()
    prohibited_cross_type = 0
    card_by_id = {card["draft_id"]: card for card in cards}
    for row in rows:
        draft_id = row["source_draft_id"]
        if draft_id not in draft_ids:
            fail(f"relation references unknown draft: {draft_id}")
        card = card_by_id[draft_id]
        profile = profiles[card["predicate_profile_id"]]
        allowed = {item["predicate_id"]: item for item in profile.get("allowed_predicates", [])}
        predicate = row["predicate_id"]
        if predicate not in allowed:
            prohibited_cross_type += 1
            fail(f"{draft_id}: predicate not allowed for profile {card['predicate_profile_id']}: {predicate}")
        expected_family = allowed[predicate]["predicate_family"]
        if row["predicate_family"] != expected_family:
            fail(f"{draft_id}: predicate family mismatch for {predicate}")
        if row["artifact_kind"] != card["owner_model"]["artifact_kind"]:
            fail(f"{draft_id}: relation strict artifact_kind mismatch")
        if row["relation_status"] != "design_hint_not_ontology_edge":
            fail("relation_status must be design_hint_not_ontology_edge")
        for key in ["subject_ref", "object_ref"]:
            if not row[key].startswith(draft_id + ":block:"):
                fail(f"{draft_id}: unstable relation ref {row[key]}")
        if card["predicate_profile_id"] == "claim_boundary" and row["predicate_family"] in {"display_execution", "temporal_execution"}:
            fail("claim-boundary relation uses display/camera predicate")
        if card["predicate_profile_id"] == "execution_asset_outbox_candidate" and row["predicate_family"] in {"control_plane_route", "state_guard", "asset_binding_policy"}:
            fail("display execution relation uses governance predicate")
        if card["predicate_profile_id"] in {"control_plane_candidate", "asset_binding_policy_candidate"} and row["predicate_family"] in {"display_execution", "temporal_execution", "claim_boundary"}:
            fail("control-plane relation uses display/camera/claim predicate")
        by_card[draft_id] += 1
        predicate_counts[predicate] += 1
    if any(count < 2 or count > 5 for count in by_card.values()):
        fail("each card must have 2..5 relation design hints")
    if all(count == 3 for count in by_card.values()):
        fail("fixed three relations per card is forbidden")
    if len(queue) != EXPECTED_TOTAL or {item.get("draft_id") for item in queue} != draft_ids:
        fail("judge queue must contain all 8 V4.3 drafts")
    if any(item.get("review_status") != "pending" for item in queue):
        fail("judge queue must remain pending")
    if not (v43_root / "semantic_pilot_v4_3_judge_protocol.md").exists():
        fail("V4.3 judge protocol missing")
    validate_status(workspace)

    recomputed = {
        "status": "PASS",
        "task_id": TASK_ID,
        "v4_3_draft_count": EXPECTED_TOTAL,
        "v4_3_distribution": dict(Counter(card.get("pilot_category") for card in cards)),
        "one_to_one_revision_count": len(revision_ids),
        "predicate_registry_artifact_kind_count": len(profiles),
        "relation_design_hints_count": len(rows),
        "predicate_registry_valid_relation_count": len(rows),
        "prohibited_cross_type_predicate_count": prohibited_cross_type,
        "strict_artifact_kind_illegal_value_count": illegal_artifact_count,
        "claim_boundary_source_workorder_hint_count": claim_source_needed,
        "display_execution_major_fix_valid_count": display_major_valid,
        "control_plane_001_founder_review_policy_valid": control1_founder,
        "control_plane_002_resliced_to": "asset_binding_policy_candidate" if control2_resliced else None,
        "control_plane_002_strict_artifact_kind": "governance_outbox_candidate",
        "decision_packet_without_decision_instance_count": decision_packet_without_decision,
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
        "ready_for_first_batch_generation": False,
        "candidatepack_created": False,
        "KE_touched": False,
        "serving_touched": False,
        "RAG_touched": False,
        "DIFY_touched": False,
        "readiness_flags_result": "all_false",
        "ready_for_semantic_pilot_v4_3_judge_review": True,
        "recommended_next_step": NEXT_STEP,
    }
    for key in [
        "v4_3_draft_count",
        "v4_3_distribution",
        "one_to_one_revision_count",
        "relation_design_hints_count",
        "predicate_registry_valid_relation_count",
        "prohibited_cross_type_predicate_count",
        "control_plane_002_resliced_to",
        "decision_packet_without_decision_instance_count",
        "accepted_domain_knowledge_count",
        "batch_generation_unlocked",
    ]:
        if quality_report.get(key) != recomputed.get(key):
            fail(f"quality report mismatch for {key}")
    if usage_report.get("predicate_registry_valid_relation_count") != recomputed["predicate_registry_valid_relation_count"]:
        fail("predicate usage report mismatch")

    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_3"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_3_minimal.yaml"))
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
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_3"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_3_minimal.yaml"))
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
    except V43CheckError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
