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

TASK_ID = "CODEX-SEMANTIC-PILOT-V4-NOGO-CLOSEOUT-AND-V4_1-REVISION-001"
V4_2_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_1-NOGO-CLOSEOUT-AND-V4_2-TYPE-SPECIFIC-REWRITE-001"
V4_3_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_2-NOGO-CLOSEOUT-PREDICATE-REGISTRY-AND-V4_3-TARGETED-REPAIR-001"
V4_4_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_3-NOGO-CLOSEOUT-CREATIVE-KNOWLEDGE-CAPSULE-AND-V4_4-REWRITE-001"
V4_5_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_4-CONDITIONAL-PASS-CLOSEOUT-AND-V4_5-CAPSULE-RICH-BODY-INTEGRATION-001"
V4_6_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_5-CLOSEOUT-TYPE-SPECIFIC-RICH-BODY-COMPILER-AND-V4_6-REWRITE-001"
PREVIOUS_TASK_ID = "CODEX-V3-NOGO-W7-AUTHORITY-AND-V4-PILOT-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_1-JUDGE-GO-NOGO-001"
V4_2_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_2-JUDGE-GO-NOGO-001"
V4_3_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_3-JUDGE-GO-NOGO-001"
V4_4_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_4-JUDGE-GO-NOGO-001"
V4_5_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_5-JUDGE-GO-NOGO-001"
V4_6_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_6-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_TOTAL = 8
EXPECTED_DISTRIBUTION = {
    "content_method": 2,
    "apparel_claim_boundary": 2,
    "display_to_content": 2,
    "control_plane_governance": 2,
}
EXPECTED_V4_IDS = {
    "SEM-V4-CONTENT-METHOD-001",
    "SEM-V4-CONTENT-METHOD-002",
    "SEM-V4-APPAREL-CLAIM-BOUNDARY-001",
    "SEM-V4-APPAREL-CLAIM-BOUNDARY-002",
    "SEM-V4-DISPLAY-TO-CONTENT-001",
    "SEM-V4-DISPLAY-TO-CONTENT-002",
    "SEM-V4-CONTROL-PLANE-GOVERNANCE-001",
    "SEM-V4-CONTROL-PLANE-GOVERNANCE-002",
}
FORBIDDEN_BODY_TOKENS = {
    "权威项",
    "权威关系项",
    "专属段",
    "本条低质风险",
    "逐句检查",
    "进入下一步审查",
    "关系依据来自权威关系项",
    "证据依据来自权威项",
    "本文只应用已登记主题",
    "checker",
    "schema",
    "W7",
    "authority",
    "批量",
    "批次",
    "审查",
    "复核",
    "样本",
}
PLACEHOLDER_RE = re.compile(r"(TBD|todo|placeholder|待填|某权威项|某字段|未解析|占位)", re.IGNORECASE)
AUDIT_TERMS = {
    "审查",
    "复核",
    "checker",
    "schema",
    "W7",
    "authority",
    "batch",
    "readiness",
    "CandidatePack",
    "是否可以进入",
}
ALLOWED_SEMANTIC_OWNERS = {
    "creative_content_operating",
    "apparel_claim_boundary",
    "display_to_content",
    "governance_control_plane",
}
ALLOWED_STORAGE_TARGETS = {
    "GeneralKnowledgeBase",
    "ControlPlaneContractSource",
    "ExecutionAssetOutbox",
    "GovernanceOutbox",
    "SourceGapLedger",
    "DecisionPacketLedger",
}
ALLOWED_ARTIFACT_KINDS = {
    "general_knowledge_candidate",
    "control_plane_candidate",
    "execution_asset_outbox_candidate",
    "governance_outbox_candidate",
    "source_gap",
    "decision_packet",
}
ALLOWED_CONSUMER_LAYERS = {
    "L2_PlayCardCandidate",
    "L3_ExecutionAssetCandidate",
    "GenerationContract",
    "CandidatePackETL",
    "HumanReview",
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
    "negative_body_contains_authority_item.yaml",
    "negative_body_contains_authority_relation.yaml",
    "negative_body_contains_low_quality_risk.yaml",
    "negative_body_placeholder_unresolved.yaml",
    "negative_missing_w7_topic_coverage_sidecar.yaml",
    "negative_owner_model_missing_storage_target.yaml",
    "negative_control_plane_storage_target_GKB.yaml",
    "negative_relation_uses_node_mkc_subject.yaml",
    "negative_relation_uses_candidate_to_cluster_trace.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_readiness_true.yaml",
]
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


class V41CheckError(Exception):
    pass


def fail(message: str) -> None:
    raise V41CheckError(message)

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


def zh_count(text: str) -> int:
    return len(CJK_RE.findall(text))


def audit_ratio(text: str) -> float:
    segments = [part for part in re.split(r"[。！？\n]+", text) if part.strip()]
    if not segments:
        return 1.0
    hits = sum(1 for segment in segments if any(term in segment for term in AUDIT_TERMS))
    return round(hits / len(segments), 3)


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


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_v4_1_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("v4_1_draft_count") != EXPECTED_TOTAL:
        errors.append("v4_1_draft_count must be 8")
    if data.get("distribution") != EXPECTED_DISTRIBUTION:
        errors.append("distribution must be 2/2/2/2")
    if data.get("one_to_one_revision_count") != EXPECTED_TOTAL:
        errors.append("one_to_one_revision_count must be 8")
    for key in [
        "forbidden_body_token_count",
        "body_placeholder_count",
        "missing_w7_topic_coverage_sidecar_count",
        "owner_model_missing_storage_target_count",
        "control_plane_GKB_storage_target_count",
        "relation_uses_node_mkc_subject_count",
        "forbidden_relation_predicate_count",
    ]:
        if data.get(key) != 0:
            errors.append(f"{key} must be 0")
    if float(data.get("audit_scaffolding_ratio_max", 1.0)) > 0.10:
        errors.append("audit_scaffolding_ratio_max must be <= 0.10")
    if data.get("relation_design_hints_count", 0) < 24:
        errors.append("relation_design_hints_count must be >= 24")
    if data.get("relation_schema_valid_count") != data.get("relation_design_hints_count"):
        errors.append("all relation design hints must match schema")
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
    if current_next_step not in {NEXT_STEP, V4_2_NEXT_STEP, V4_3_NEXT_STEP, V4_4_NEXT_STEP, V4_5_NEXT_STEP, V4_6_NEXT_STEP}:
        fail("workspace next step must be semantic pilot V4.1 judge go/no-go, semantic pilot V4.2 judge go/no-go, or semantic pilot V4.3 judge go/no-go or semantic pilot V4.4 judge go/no-go")
    if current_next_step == NEXT_STEP and phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be V4.1 revision task")
    if current_next_step == V4_2_NEXT_STEP and phase.get("previous_step") != V4_2_TASK_ID:
        fail("workspace previous step must be V4.2 rewrite task")
    if current_next_step == V4_3_NEXT_STEP and phase.get("previous_step") != V4_3_TASK_ID:
        fail("workspace previous step must be V4.3 targeted repair task")
    if current_next_step == V4_4_NEXT_STEP and phase.get("previous_step") != V4_4_TASK_ID:
        fail("workspace previous step must be V4.4 creative capsule task")
    v41 = status.get("semantic_pilot_v4_1", {})
    if v41.get("task_id") != TASK_ID or v41.get("status") != "completed":
        fail("semantic_pilot_v4_1 status block missing")
    if v41.get("semantic_pilot_v4_1_count") != EXPECTED_TOTAL:
        fail("semantic_pilot_v4_1 count must be 8")
    if v41.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    if v41.get("batch_generation_unlocked") is True or v41.get("ready_for_first_batch_generation") is True:
        fail("batch generation must remain locked")
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
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")


def authority_by_id(workspace: Path) -> dict[str, dict[str, Any]]:
    data = load_yaml(workspace / "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml")["w7_canonical_cluster_authority"]
    records = data.get("records", [])
    if len(records) != 46:
        fail("W7 authority table must contain 46 records")
    return {record["mkc_id"]: record for record in records}


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    semantic_root = workspace / "03_pilot/semantic_v4_1"
    registry = authority_by_id(workspace)
    load_yaml(workspace / "01_generation_contracts/codex_semantic_pilot_v4_1_revision_policy.v0.1.yaml")

    closeout = load_yaml(workspace / "03_pilot/semantic_v4/v4_no_go_closeout.yaml")["v4_no_go_closeout"]
    if closeout.get("human_decision", {}).get("authorized_by") != "founder_current_request":
        fail("founder authorization missing from V4 no-go closeout")
    if closeout.get("semantic_verdict") != "NO_GO":
        fail("V4 closeout must be NO_GO")
    if closeout.get("accepted_domain_knowledge_count") != 0 or closeout.get("batch_generation_unlocked") is not False:
        fail("V4 closeout must keep accepted count 0 and batch locked")
    disposition = closeout.get("disposition", {})
    if set(disposition) != EXPECTED_V4_IDS or any(value != "revise_required" for value in disposition.values()):
        fail("V4 closeout must mark all 8 V4 drafts revise_required")

    manifest = load_yaml(semantic_root / "semantic_pilot_v4_1_manifest.yaml")["semantic_pilot_v4_1_manifest"]
    cards = load_yaml(semantic_root / "semantic_pilot_v4_1_candidate_cards.yaml")["semantic_pilot_v4_1_candidate_cards"]["candidates"]
    blocks = load_yaml(semantic_root / "semantic_pilot_v4_1_rich_body_blocks.yaml")["semantic_pilot_v4_1_rich_body_blocks"]["blocks"]
    sidecars = load_yaml(semantic_root / "semantic_pilot_v4_1_sidecars.yaml")["semantic_pilot_v4_1_sidecars"]["sidecars"]
    queue = load_yaml(semantic_root / "semantic_pilot_v4_1_judge_review_queue.yaml")["semantic_pilot_v4_1_judge_review_queue"]["items"]
    quality = load_json(semantic_root / "semantic_pilot_v4_1_quality_report.json")
    receipt = load_json(workspace / "docs/reports/codex_semantic_pilot_v4_1_receipt.json")

    if manifest.get("task_id") != TASK_ID:
        fail("manifest task id mismatch")
    if manifest.get("human_decision", {}).get("authorized_by") != "founder_current_request":
        fail("manifest founder authorization missing")
    if manifest.get("semantic_pilot_v4_1_count") != EXPECTED_TOTAL:
        fail("manifest V4.1 count must be 8")
    if manifest.get("distribution") != EXPECTED_DISTRIBUTION:
        fail("manifest distribution must be 2/2/2/2")
    if manifest.get("one_to_one_revision_of_v4") is not True:
        fail("manifest must declare one-to-one revision")
    if manifest.get("accepted_domain_knowledge_count") != 0 or manifest.get("batch_generation_unlocked") is not False:
        fail("manifest must keep accepted count 0 and batch locked")

    if len(cards) != EXPECTED_TOTAL:
        fail("V4.1 candidate count must be 8")
    if Counter(card.get("pilot_category") for card in cards) != EXPECTED_DISTRIBUTION:
        fail("V4.1 distribution must be 2/2/2/2")
    blocks_by_id = {block["draft_id"]: block for block in blocks}
    sidecars_by_id = {sidecar["draft_id"]: sidecar for sidecar in sidecars}
    draft_ids: set[str] = set()
    revised_ids: set[str] = set()
    forbidden_body_token_count = 0
    body_placeholder_count = 0
    audit_ratio_max = 0.0
    owner_model_valid_count = 0
    for card in cards:
        draft_id = card["draft_id"]
        if draft_id in draft_ids:
            fail(f"duplicate draft id: {draft_id}")
        draft_ids.add(draft_id)
        lineage = card.get("revision_lineage", {})
        old_id = lineage.get("revision_of")
        revised_ids.add(old_id)
        if old_id not in EXPECTED_V4_IDS:
            fail(f"{draft_id}: revision_of does not point to a V4 draft")
        mkc_id = lineage.get("referenced_mkc_id") or card.get("canonical_cluster_id")
        if mkc_id not in registry:
            fail(f"{draft_id}: mkc id missing from authority")
        authority = registry[mkc_id]
        if card.get("canonical_cluster_title_from_authority") != authority["canonical_title"]:
            fail(f"{draft_id}: canonical title mismatch")
        body = card.get("canonical_body_zh", "")
        if not body or zh_count(body) < 1000:
            fail(f"{draft_id}: canonical_body_zh below 1000 Chinese chars")
        if blocks_by_id.get(draft_id, {}).get("canonical_body_zh") != body:
            fail(f"{draft_id}: rich body block does not mirror canonical_body_zh")
        hits = [token for token in FORBIDDEN_BODY_TOKENS if token in body]
        if hits:
            forbidden_body_token_count += len(hits)
            fail(f"{draft_id}: forbidden body tokens {hits}")
        if PLACEHOLDER_RE.search(body):
            body_placeholder_count += 1
            fail(f"{draft_id}: placeholder or unresolved rendering in body")
        ratio = audit_ratio(body)
        audit_ratio_max = max(audit_ratio_max, ratio)
        if ratio > 0.10:
            fail(f"{draft_id}: audit scaffolding ratio too high: {ratio}")
        owner = card.get("owner_model", {})
        if owner.get("semantic_owner") not in ALLOWED_SEMANTIC_OWNERS:
            fail(f"{draft_id}: invalid semantic_owner")
        if owner.get("storage_target") not in ALLOWED_STORAGE_TARGETS:
            fail(f"{draft_id}: invalid storage_target")
        if owner.get("artifact_kind") not in ALLOWED_ARTIFACT_KINDS:
            fail(f"{draft_id}: invalid artifact_kind")
        if owner.get("consumer_layer") not in ALLOWED_CONSUMER_LAYERS:
            fail(f"{draft_id}: invalid consumer_layer")
        if card.get("pilot_category") == "control_plane_governance" and owner.get("storage_target") == "GeneralKnowledgeBase":
            fail(f"{draft_id}: control-plane draft targets GeneralKnowledgeBase")
        if card.get("legacy_aliases", {}).get("alias_of") != "owner_model":
            fail(f"{draft_id}: legacy aliases must be derived from owner_model")
        owner_model_valid_count += 1
        source_status = card.get("source_status", {})
        if source_status.get("is_source_anchor") is not False or source_status.get("human_review_status") != "pending":
            fail(f"{draft_id}: source status boundary invalid")
        if any(value is not False for value in card.get("readiness_flags", {}).values()):
            fail(f"{draft_id}: readiness flag true")
        sidecar = sidecars_by_id.get(draft_id)
        if not sidecar:
            fail(f"{draft_id}: missing sidecar")
        coverage = sidecar.get("w7_expected_topic_coverage", {})
        if coverage.get("referenced_mkc_id") != mkc_id:
            fail(f"{draft_id}: sidecar mkc id mismatch")
        if coverage.get("canonical_title_from_authority") != authority["canonical_title"]:
            fail(f"{draft_id}: sidecar title mismatch")
        topics = coverage.get("expected_body_topics", [])
        if [topic.get("topic") for topic in topics] != authority.get("expected_body_topics", []):
            fail(f"{draft_id}: sidecar expected topics redefined")
        paragraph_ids = set(card.get("body_paragraph_ids", []))
        for topic in topics:
            status = topic.get("coverage_status")
            if status not in {"covered", "not_covered_with_reason"}:
                fail(f"{draft_id}: invalid topic coverage status")
            if status == "covered" and not set(topic.get("body_paragraph_refs", [])).issubset(paragraph_ids):
                fail(f"{draft_id}: topic coverage references unknown paragraph")
            if status == "not_covered_with_reason" and not topic.get("mechanism_summary"):
                fail(f"{draft_id}: uncovered topic requires reason")
    if revised_ids != EXPECTED_V4_IDS:
        fail("V4.1 must be a one-to-one revision of all 8 V4 drafts")

    with (semantic_root / "semantic_pilot_v4_1_relation_design_hints.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        fail("relation design hints csv is empty")
    if list(rows[0]) != RELATION_FIELDS:
        fail("relation design hints schema mismatch")
    if len(rows) < 24:
        fail("relation design hints total must be at least 24")
    by_draft: dict[str, list[dict[str, str]]] = defaultdict(list)
    relation_schema_valid_count = 0
    for row in rows:
        draft_id = row["source_draft_id"]
        if draft_id not in draft_ids:
            fail(f"relation references unknown draft: {draft_id}")
        by_draft[draft_id].append(row)
        relation_schema_valid_count += 1
        if row["relation_status"] != "design_hint_not_ontology_edge":
            fail("relation_status must be design_hint_not_ontology_edge")
        if row["predicate_id"] in FORBIDDEN_RELATION_PREDICATES:
            fail(f"forbidden relation predicate: {row['predicate_id']}")
        for key in ["subject_ref", "object_ref"]:
            value = row[key]
            if value.startswith("node_mkc_") or re.search(r"[。！？]", value) or len(value) > 90:
                fail(f"relation uses forbidden node reference: {value}")
    for draft_id in draft_ids:
        if len(by_draft[draft_id]) < 3:
            fail(f"{draft_id}: fewer than three relation design hints")

    if len(queue) != EXPECTED_TOTAL or {item["draft_id"] for item in queue} != draft_ids:
        fail("judge review queue must contain all 8 V4.1 drafts")
    if any(item.get("review_status") != "pending" for item in queue):
        fail("judge queue must remain pending")
    if not (semantic_root / "semantic_pilot_v4_1_judge_protocol.md").exists():
        fail("judge protocol missing")
    validate_status(workspace)

    report_checks = {
        "quality_status": quality.get("status") == "PASS",
        "forbidden_body_token_count": quality.get("forbidden_body_token_count") == 0,
        "body_placeholder_count": quality.get("body_placeholder_count") == 0,
        "relation_design_hints_count": quality.get("relation_design_hints_count") == len(rows),
        "owner_model_valid_count": quality.get("owner_model_valid_count") == EXPECTED_TOTAL,
        "accepted_domain_knowledge_count": quality.get("accepted_domain_knowledge_count") == 0,
        "receipt_next_step": receipt.get("recommended_next_step") == NEXT_STEP,
    }
    failing = [name for name, passed in report_checks.items() if not passed]
    if failing:
        fail(f"report checks failed: {failing}")

    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_1"
    positive = load_yaml(fixtures_root / "positive_valid_semantic_v4_1_minimal.yaml")
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
        "v4_no_go_closeout_recorded": True,
        "v4_1_draft_count": EXPECTED_TOTAL,
        "v4_1_distribution": EXPECTED_DISTRIBUTION,
        "one_to_one_revision_count": EXPECTED_TOTAL,
        "forbidden_body_token_count": forbidden_body_token_count,
        "body_placeholder_count": body_placeholder_count,
        "audit_scaffolding_ratio_max": audit_ratio_max,
        "relation_design_hints_count": len(rows),
        "relation_schema_valid_count": relation_schema_valid_count,
        "owner_model_valid_count": owner_model_valid_count,
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
        "ready_for_first_batch_generation": False,
        "readiness_flags_result": "all_false",
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "positive_fixture_passed": True,
        "negative_fixtures_fail_closed": True,
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


def run_selftest(workspace: Path) -> dict[str, Any]:
    fixtures_root = workspace / "ci/fixtures/codex_semantic_pilot_v4_1"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_semantic_v4_1_minimal.yaml"))
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
    except V41CheckError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
