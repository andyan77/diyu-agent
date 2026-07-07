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

V4_5_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_4-CONDITIONAL-PASS-CLOSEOUT-AND-V4_5-CAPSULE-RICH-BODY-INTEGRATION-001"
TASK_ID = "CODEX-V3-NOGO-W7-AUTHORITY-AND-V4-PILOT-001"
NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4-JUDGE-GO-NOGO-001"
V4_1_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_1-JUDGE-GO-NOGO-001"
V4_2_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_2-JUDGE-GO-NOGO-001"
V4_3_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_3-JUDGE-GO-NOGO-001"
V4_4_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_4-JUDGE-GO-NOGO-001"
V4_5_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4_5-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_TOTAL = 8
EXPECTED_AUTHORITY_COUNT = 46
EXPECTED_CATEGORY_COUNTS = {
    "content_method": 2,
    "apparel_claim_boundary": 2,
    "display_to_content": 2,
    "control_plane_governance": 2,
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
    "readiness",
    "schema",
    "source_repo",
}
FORBIDDEN_RELATION_PREDICATES = {
    "generic",
    "related_to",
    "similar_to",
    "review_adjacent",
    "placeholder",
}
CONTROL_PLANE_PREDICATES = {
    "routes_to_source_gap",
    "requires_decision_packet",
    "prohibits_target_owner",
    "gates_batch_generation",
    "blocks_candidatepack_eligibility",
    "records_failure_code",
}
ALLOWED_OWNERS = {
    "GeneralKnowledgeBase",
    "L2_PlayCardCandidate",
    "L3_ExecutionAssetCandidate",
    "EvidencePolicyCandidate",
    "ControlPlaneContractSource",
    "DecisionPacketLedger",
    "SourceGapLedger",
}
NEGATIVE_FIXTURES = [
    "negative_unknown_mkc_id.yaml",
    "negative_redefined_mkc_title.yaml",
    "negative_topic_mismatch.yaml",
    "negative_missing_authority_record.yaml",
    "negative_english_primary_body.yaml",
    "negative_forbidden_audit_phrase.yaml",
    "negative_shared_sentence_ratio_high.yaml",
    "negative_candidate_to_cluster_relation.yaml",
    "negative_generic_relation_predicate.yaml",
    "negative_control_plane_targets_GKB.yaml",
    "negative_multiple_primary_target_owners.yaml",
    "negative_source_status_conflation.yaml",
    "negative_batch_generation_unlocked.yaml",
    "negative_readiness_true.yaml",
    "negative_source_repo_dependency_true.yaml",
    "negative_google_drive_dependency_true.yaml",
]
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
EN_RE = re.compile(r"[A-Za-z]")


class SemanticV4Error(Exception):
    pass


def fail(message: str) -> None:
    raise SemanticV4Error(message)

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


def shared_sentence_ratio(bodies: list[str]) -> float:
    sentences: list[str] = []
    for body in bodies:
        sentences.extend(sentence.strip() for sentence in re.split(r"[。！？]", body) if sentence.strip())
    if not bodies or not sentences:
        return 1.0
    counts = Counter(sentences)
    return round(max(counts.values()) / len(bodies), 3)


def registry_record_to_authority(cluster: dict[str, Any]) -> dict[str, Any]:
    return {
        "mkc_id": cluster["canonical_cluster_id"],
        "canonical_title": cluster["canonical_cluster_name"],
        "owner_capability_group": cluster["owner_capability_group"],
        "secondary_capability_groups": cluster.get("secondary_capability_groups", []),
        "knowledge_types": cluster.get("knowledge_types", []),
        "expected_body_topics": cluster.get("expected_body_topics", []),
        "required_relations": cluster.get("required_relations", []),
        "evidence_classes": cluster.get("evidence_classes", []),
        "candidate_output_effect": cluster.get("candidate_output_effect", []),
        "source_gap_likelihood": cluster.get("source_gap_likelihood"),
    }


def load_registry_authority(workspace: Path) -> dict[str, dict[str, Any]]:
    registry = load_yaml(workspace / "00_source_inputs/W7_master_map/shared_knowledge_cluster_registry.yaml")
    clusters = registry.get("clusters", [])
    if len(clusters) != EXPECTED_AUTHORITY_COUNT:
        fail(f"W7 registry authority record count must be 46, got {len(clusters)}")
    return {cluster["canonical_cluster_id"]: registry_record_to_authority(cluster) for cluster in clusters}


def load_contract_authority(contracts_root: Path, registry: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    authority = load_yaml(contracts_root / "w7_canonical_cluster_authority.v0.1.yaml")["w7_canonical_cluster_authority"]
    if authority.get("record_count") != EXPECTED_AUTHORITY_COUNT:
        fail("W7 authority contract record_count must be 46")
    records = authority.get("records", [])
    if len(records) != EXPECTED_AUTHORITY_COUNT:
        fail("W7 authority contract must contain 46 records")
    by_id = {record["mkc_id"]: record for record in records}
    if set(by_id) != set(registry):
        fail("W7 authority contract ids do not match registry ids")
    for mkc_id, expected in registry.items():
        actual = by_id[mkc_id]
        comparable = {key: actual.get(key) for key in expected}
        if comparable != expected:
            fail(f"W7 authority contract diverges from registry for {mkc_id}")
    return by_id


def validate_status(status: dict[str, Any]) -> None:
    phase = status.get("phase", {})
    if phase.get("current_next_step") == BATCH_NEXT_STEP:
        fail("batch generation task cannot be next step")
    current_next_step = phase.get("current_next_step")
    if current_next_step not in {NEXT_STEP, V4_1_NEXT_STEP, V4_2_NEXT_STEP, V4_3_NEXT_STEP, V4_4_NEXT_STEP, V4_5_NEXT_STEP}:
        fail("workspace next step must be semantic pilot v4 judge go/no-go, semantic pilot v4.1 judge go/no-go, semantic pilot v4.2 judge go/no-go, or semantic pilot v4.3 judge go/no-go or semantic pilot v4.4 judge go/no-go")
    v4 = status.get("semantic_pilot_v4", {})
    if v4.get("task_id") != TASK_ID or v4.get("status") != "completed":
        fail("semantic_pilot_v4 status block missing")
    if v4.get("W7_authority_records_count") != EXPECTED_AUTHORITY_COUNT:
        fail("workspace status W7 authority count must be 46")
    if v4.get("semantic_pilot_v4_count") != EXPECTED_TOTAL:
        fail("workspace status v4 count must be 8")
    if v4.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    if v4.get("batch_generation_unlocked") is True:
        fail("batch_generation_unlocked must remain false")
    if v4.get("ready_for_first_batch_generation") is True:
        fail("ready_for_first_batch_generation must remain false")
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
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
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


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_v4_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("W7_authority_records_count") != EXPECTED_AUTHORITY_COUNT:
        errors.append("W7 authority records count must be 46")
    if data.get("source_repo_live_dependency") is not False or data.get("source_repo_live_accessed") is not False:
        errors.append("source repo dependency/access must be false")
    if data.get("external_drive_dependency") is not False or data.get("external_drive_accessed") is not False:
        errors.append("external drive dependency/access must be false")
    if data.get("semantic_pilot_v4_count") != EXPECTED_TOTAL:
        errors.append("semantic pilot v4 count must be 8")
    if data.get("category_counts") != EXPECTED_CATEGORY_COUNTS:
        errors.append("category counts must be 2 each")
    if data.get("accepted_domain_knowledge_count") != 0:
        errors.append("accepted domain knowledge count must be 0")
    if data.get("batch_generation_unlocked") is not False:
        errors.append("batch generation must remain locked")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") not in {NEXT_STEP, V4_1_NEXT_STEP, V4_2_NEXT_STEP, V4_3_NEXT_STEP, V4_4_NEXT_STEP, V4_5_NEXT_STEP}:
        errors.append("next step must be semantic pilot v4 judge go/no-go, semantic pilot v4.1 judge go/no-go, semantic pilot v4.2 judge go/no-go, or semantic pilot v4.3 judge go/no-go or semantic pilot v4.4 judge go/no-go")
    for key in [
        "unknown_mkc_id_count",
        "redefined_mkc_title_count",
        "topic_mismatch_count",
        "missing_authority_record_count",
        "english_primary_body_count",
        "forbidden_audit_phrase_count",
        "candidate_to_cluster_relation_count",
        "forbidden_relation_predicate_count",
        "control_plane_GKB_target_count",
    ]:
        if data.get(key) != 0:
            errors.append(f"{key} must be 0")
    if float(data.get("shared_sentence_ratio_max", 1.0)) > 0.18:
        errors.append("shared sentence ratio must be <= 0.18")
    if data.get("single_primary_target_owner_count") != EXPECTED_TOTAL:
        errors.append("single primary target owner count must be 8")
    if data.get("source_status_disambiguation_pass_count") != EXPECTED_TOTAL:
        errors.append("source status disambiguation pass count must be 8")
    if data.get("readiness_all_false") is not True:
        errors.append("readiness must remain all false")
    if data.get("judge_review_queue_present") is not True:
        errors.append("judge review queue required")
    for key in ["candidatepack_created", "KE_touched", "serving_touched", "RAG_touched", "DIFY_touched"]:
        if data.get(key) is not False:
            errors.append(f"{key} must be false")
    return errors


def validate_live(workspace: Path, semantic_root: Path, contracts_root: Path, fixtures_root: Path, report_out: Path | None) -> dict[str, Any]:
    registry_authority = load_registry_authority(workspace)
    contract_authority = load_contract_authority(contracts_root, registry_authority)
    load_yaml(contracts_root / "codex_w7_authority_alignment_policy.v0.1.yaml")

    closeout = load_yaml(semantic_root / "v3_no_go_closeout.yaml")["v3_no_go_closeout"]
    if closeout.get("human_decision", {}).get("authorized_by") != "founder_current_request":
        fail("founder authorization missing from V3 no-go closeout")
    if closeout.get("verdict", {}).get("as_3600_generation_exemplar") != "no_go":
        fail("V3 no-go closeout must mark 3600 exemplar as no_go")
    if closeout.get("disposition", {}).get("batch_generation_unlocked") is not False:
        fail("V3 no-go closeout must keep batch locked")

    manifest = load_yaml(semantic_root / "semantic_pilot_v4_manifest.yaml")["semantic_pilot_v4_manifest"]
    cards = load_yaml(semantic_root / "semantic_pilot_v4_candidate_cards.yaml")["semantic_pilot_v4_candidate_cards"]
    blocks = load_yaml(semantic_root / "semantic_pilot_v4_rich_body_blocks.yaml")["semantic_pilot_v4_rich_body_blocks"]
    matrix = load_yaml(semantic_root / "W7_authority_alignment_matrix.yaml")["W7_authority_alignment_matrix"]
    queue = load_yaml(semantic_root / "semantic_pilot_v4_judge_review_queue.yaml")["semantic_pilot_v4_judge_review_queue"]
    body_report = load_json(semantic_root / "semantic_pilot_v4_body_quality_report.json")
    alignment_report = load_json(semantic_root / "semantic_pilot_v4_W7_alignment_report.json")
    relation_report = load_json(semantic_root / "semantic_pilot_v4_relation_graph_report.json")
    owner_report = load_json(semantic_root / "semantic_pilot_v4_owner_layer_report.json")
    source_report = load_json(semantic_root / "semantic_pilot_v4_source_status_report.json")
    dedupe_report = load_json(semantic_root / "semantic_pilot_v4_dedupe_report.json")
    receipt = load_json(semantic_root / "semantic_pilot_v4_generation_receipt.json")

    if manifest.get("task_id") != TASK_ID:
        fail("manifest task id mismatch")
    if manifest.get("human_decision", {}).get("authorized_by") != "founder_current_request":
        fail("founder authorization missing from manifest")
    if manifest.get("W7_authority_records_count") != EXPECTED_AUTHORITY_COUNT:
        fail("manifest W7 authority count must be 46")
    if manifest.get("semantic_pilot_v4_count") != EXPECTED_TOTAL:
        fail("manifest V4 count must be 8")
    if manifest.get("category_counts") != EXPECTED_CATEGORY_COUNTS:
        fail("manifest category counts mismatch")
    for key in ["source_repo_live_dependency", "source_repo_live_accessed", "external_drive_dependency", "external_drive_accessed"]:
        if manifest.get(key) is not False:
            fail(f"manifest {key} must be false")
    if manifest.get("accepted_domain_knowledge_count") != 0:
        fail("accepted domain knowledge count must be 0")
    if manifest.get("batch_generation_unlocked") is True or manifest.get("ready_for_first_batch_generation") is True:
        fail("batch generation must remain locked")

    entries = cards.get("candidates", [])
    if len(entries) != EXPECTED_TOTAL:
        fail("V4 candidate count must be 8")
    if Counter(entry.get("pilot_category") for entry in entries) != EXPECTED_CATEGORY_COUNTS:
        fail("V4 category counts must be 2 each")
    blocks_by_id = {block["candidate_id"]: block for block in blocks.get("blocks", [])}
    matrix_by_id = {item["candidate_id"]: item for item in matrix.get("items", [])}
    bodies: list[str] = []
    candidate_ids: set[str] = set()
    source_status_pass = 0
    single_owner_count = 0
    for entry in entries:
        cid = entry["candidate_id"]
        if cid in candidate_ids:
            fail(f"duplicate candidate id: {cid}")
        candidate_ids.add(cid)
        mkc_id = entry.get("canonical_cluster_id")
        if mkc_id not in contract_authority:
            fail(f"unknown mkc id: {mkc_id}")
        authority = contract_authority[mkc_id]
        alignment = entry.get("W7_alignment", {})
        if entry.get("canonical_cluster_title_from_authority") != authority["canonical_title"]:
            fail(f"{cid}: canonical title redefined")
        if alignment.get("authority_title") != authority["canonical_title"]:
            fail(f"{cid}: authority title mismatch")
        if alignment.get("authority_expected_body_topics") != authority["expected_body_topics"]:
            fail(f"{cid}: expected_body_topics redefined")
        if alignment.get("authority_required_relations") != authority["required_relations"]:
            fail(f"{cid}: required_relations redefined")
        if alignment.get("authority_evidence_classes") != authority["evidence_classes"]:
            fail(f"{cid}: evidence_classes redefined")
        if alignment.get("authority_candidate_output_effect") != authority["candidate_output_effect"]:
            fail(f"{cid}: candidate_output_effect redefined")
        if alignment.get("alignment_verdict") != "aligned":
            fail(f"{cid}: W7 alignment must be aligned")
        topic = entry.get("candidate_topic", "")
        if not any(expected_topic in topic for expected_topic in authority["expected_body_topics"]):
            fail(f"{cid}: candidate topic does not apply an authority body topic")
        matrix_item = matrix_by_id.get(cid)
        if not matrix_item or matrix_item.get("canonical_cluster_title_from_authority") != authority["canonical_title"]:
            fail(f"{cid}: alignment matrix does not match authority")
        body = entry.get("canonical_body_zh", "")
        if blocks_by_id.get(cid, {}).get("canonical_body_zh") != body:
            fail(f"{cid}: rich body block mismatch")
        if zh_count(body) < 1000:
            fail(f"{cid}: body below 1000 Chinese chars")
        if len(EN_RE.findall(body)) > 10:
            fail(f"{cid}: English appears in primary body")
        lowered = body.lower()
        hits = [term for term in FORBIDDEN_BODY_TERMS if term in lowered]
        if hits:
            fail(f"{cid}: forbidden audit phrase in body: {hits}")
        bodies.append(body)
        owner = entry.get("primary_target_owner")
        if owner not in ALLOWED_OWNERS:
            fail(f"{cid}: invalid primary target owner")
        if owner in entry.get("rejected_target_owners", []):
            fail(f"{cid}: primary owner appears in rejected owners")
        if entry.get("pilot_category") == "control_plane_governance" and owner == "GeneralKnowledgeBase":
            fail(f"{cid}: control plane targets GeneralKnowledgeBase")
        single_owner_count += 1
        source_status = entry.get("source_status", {})
        if source_status.get("provenance_class") != "expert_synthesis_draft":
            fail(f"{cid}: provenance_class mismatch")
        if source_status.get("expert_synthesis_policy") != "allowed_after_human_review":
            fail(f"{cid}: expert synthesis policy mismatch")
        if source_status.get("human_review_status") != "pending" or source_status.get("human_reviewed_method") is not False:
            fail(f"{cid}: source status conflation")
        if source_status.get("is_source_anchor") is not False:
            fail(f"{cid}: expert synthesis draft cannot be source anchor")
        source_status_pass += 1
        if any(value is not False for value in entry.get("readiness_flags", {}).values()):
            fail(f"{cid}: readiness flag true")

    ratio = shared_sentence_ratio(bodies)
    if ratio > 0.18:
        fail(f"shared sentence ratio too high: {ratio}")

    with (semantic_root / "semantic_pilot_v4_relation_candidates.csv").open(encoding="utf-8", newline="") as handle:
        relations = list(csv.DictReader(handle))
    if len(relations) < 24:
        fail("relation total must be at least 24")
    by_candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    for relation in relations:
        cid = relation.get("source_candidate_id", "")
        by_candidate[cid].append(relation)
        predicate = relation.get("predicate_id", "")
        if predicate in FORBIDDEN_RELATION_PREDICATES:
            fail(f"forbidden relation predicate: {predicate}")
        subject_id = relation.get("subject_node_id", "")
        object_id = relation.get("object_node_id", "")
        if subject_id in candidate_ids or object_id in candidate_ids or subject_id.startswith("mkc_") or object_id.startswith("mkc_"):
            fail("candidate-to-cluster relation detected")
        if cid not in candidate_ids:
            fail(f"relation references unknown candidate: {cid}")
    for entry in entries:
        cid = entry["candidate_id"]
        if len(by_candidate.get(cid, [])) < 3:
            fail(f"{cid}: fewer than three relations")
        if entry.get("pilot_category") == "control_plane_governance":
            invalid = [rel["predicate_id"] for rel in by_candidate[cid] if rel["predicate_id"] not in CONTROL_PLANE_PREDICATES]
            if invalid:
                fail(f"{cid}: invalid control-plane predicates {invalid}")

    queue_items = queue.get("items", [])
    if len(queue_items) != EXPECTED_TOTAL:
        fail("judge queue must contain 8 items")
    if {item["candidate_id"] for item in queue_items} != candidate_ids:
        fail("judge queue candidate ids mismatch")
    if any(item.get("review_status") != "pending" for item in queue_items):
        fail("judge queue items must remain pending")
    if not (semantic_root / "semantic_pilot_v4_judge_protocol.md").exists():
        fail("judge protocol missing")
    validate_status(load_yaml(workspace / "project-infra/current_workspace_status.yaml"))

    report_checks = {
        "body": body_report.get("english_primary_body_count") == 0
        and body_report.get("forbidden_audit_phrase_count") == 0
        and body_report.get("min_body_zh_chars_pass_count") == EXPECTED_TOTAL
        and float(body_report.get("shared_sentence_ratio_max", 1.0)) <= 0.18,
        "alignment": alignment_report.get("authority_records_count") == EXPECTED_AUTHORITY_COUNT
        and alignment_report.get("mismatched_count") == 0
        and alignment_report.get("sidecar_redefinition_count") == 0,
        "relation": relation_report.get("total_relations", 0) >= 24
        and relation_report.get("candidate_to_cluster_relation_count") == 0
        and relation_report.get("forbidden_relation_predicate_count") == 0,
        "owner": owner_report.get("single_primary_target_owner_count") == EXPECTED_TOTAL
        and owner_report.get("control_plane_GKB_target_count") == 0,
        "source": source_report.get("source_status_disambiguation_pass_count") == EXPECTED_TOTAL
        and source_report.get("source_status_conflation_count") == 0,
        "dedupe": dedupe_report.get("blocking_duplicate_count") == 0,
        "receipt": receipt.get("semantic_pilot_v4_count") == EXPECTED_TOTAL
        and receipt.get("candidatepack_created") is False,
    }
    failing = [name for name, passed in report_checks.items() if not passed]
    if failing:
        fail(f"report checks failed: {failing}")

    positive = load_yaml(fixtures_root / "positive_valid_semantic_v4_minimal.yaml")
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
        "W7_authority_records_count": EXPECTED_AUTHORITY_COUNT,
        "V3_no_go_closeout_created": True,
        "semantic_pilot_v4_count": EXPECTED_TOTAL,
        "category_counts": dict(Counter(entry.get("pilot_category") for entry in entries)),
        "W7_alignment_result": "PASS",
        "chinese_body_result": "PASS",
        "shared_sentence_ratio_max": ratio,
        "relation_total": len(relations),
        "candidate_to_cluster_relation_count": 0,
        "forbidden_relation_predicate_count": 0,
        "target_owner_single_assignment_result": "PASS",
        "source_status_disambiguation_result": "PASS",
        "source_status_disambiguation_pass_count": source_status_pass,
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
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


def build_fixture_model() -> dict[str, Any]:
    return {
        "semantic_v4_fixture": {
            "task_id": TASK_ID,
            "W7_authority_records_count": EXPECTED_AUTHORITY_COUNT,
            "source_repo_live_dependency": False,
            "source_repo_live_accessed": False,
            "external_drive_dependency": False,
            "external_drive_accessed": False,
            "semantic_pilot_v4_count": EXPECTED_TOTAL,
            "category_counts": EXPECTED_CATEGORY_COUNTS,
            "accepted_domain_knowledge_count": 0,
            "batch_generation_unlocked": False,
            "current_next_step": NEXT_STEP,
            "unknown_mkc_id_count": 0,
            "redefined_mkc_title_count": 0,
            "topic_mismatch_count": 0,
            "missing_authority_record_count": 0,
            "english_primary_body_count": 0,
            "forbidden_audit_phrase_count": 0,
            "shared_sentence_ratio_max": 0.125,
            "candidate_to_cluster_relation_count": 0,
            "forbidden_relation_predicate_count": 0,
            "control_plane_GKB_target_count": 0,
            "single_primary_target_owner_count": EXPECTED_TOTAL,
            "source_status_disambiguation_pass_count": EXPECTED_TOTAL,
            "readiness_all_false": True,
            "candidatepack_created": False,
            "KE_touched": False,
            "serving_touched": False,
            "RAG_touched": False,
            "DIFY_touched": False,
            "judge_review_queue_present": True,
        }
    }


def mutate_fixture_for_negative(model: dict[str, Any], name: str) -> None:
    data = model["semantic_v4_fixture"]
    mapping = {
        "negative_unknown_mkc_id.yaml": ("unknown_mkc_id_count", 1),
        "negative_redefined_mkc_title.yaml": ("redefined_mkc_title_count", 1),
        "negative_topic_mismatch.yaml": ("topic_mismatch_count", 1),
        "negative_missing_authority_record.yaml": ("missing_authority_record_count", 1),
        "negative_english_primary_body.yaml": ("english_primary_body_count", 1),
        "negative_forbidden_audit_phrase.yaml": ("forbidden_audit_phrase_count", 1),
        "negative_shared_sentence_ratio_high.yaml": ("shared_sentence_ratio_max", 0.5),
        "negative_candidate_to_cluster_relation.yaml": ("candidate_to_cluster_relation_count", 1),
        "negative_generic_relation_predicate.yaml": ("forbidden_relation_predicate_count", 1),
        "negative_control_plane_targets_GKB.yaml": ("control_plane_GKB_target_count", 1),
        "negative_multiple_primary_target_owners.yaml": ("single_primary_target_owner_count", 7),
        "negative_source_status_conflation.yaml": ("source_status_disambiguation_pass_count", 7),
        "negative_batch_generation_unlocked.yaml": ("batch_generation_unlocked", True),
        "negative_readiness_true.yaml": ("readiness_all_false", False),
        "negative_source_repo_dependency_true.yaml": ("source_repo_live_dependency", True),
        "negative_google_drive_dependency_true.yaml": ("external_drive_dependency", True),
    }
    key, value = mapping[name]
    data[key] = value
    if name == "negative_google_drive_dependency_true.yaml":
        data["external_drive_accessed"] = True


def run_selftest() -> dict[str, Any]:
    positive = build_fixture_model()
    errors = validate_fixture_model(positive)
    if errors:
        fail(f"selftest positive failed: {errors}")
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
    parser.add_argument("--semantic-v4-root", default="03_pilot/semantic_v4")
    parser.add_argument("--contracts-root", default="01_generation_contracts")
    parser.add_argument("--fixtures-root", default="ci/fixtures/codex_semantic_pilot_v4")
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
                semantic_root=workspace / args.semantic_v4_root,
                contracts_root=workspace / args.contracts_root,
                fixtures_root=workspace / args.fixtures_root,
                report_out=workspace / args.report_out if args.report_out else None,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except SemanticV4Error as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
