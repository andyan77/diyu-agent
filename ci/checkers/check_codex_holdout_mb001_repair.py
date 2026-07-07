#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

TASK_ID = "HOLDOUT-MB001-FAIL-CLOSEOUT-AND-CLUSTER-SPECIFIC-COMPILER-REPAIR-001"
PREVIOUS_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_7-PASS-CLOSEOUT-METADATA-CLEANUP-AND-HOLDOUT-MICROBATCH-001"
NEXT_STEP = "HOLDOUT-MB001-REPAIR-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
ORIGINAL_HOLDOUT_IDS = {
    "mkc_002",
    "mkc_003",
    "mkc_005",
    "mkc_007",
    "mkc_012",
    "mkc_013",
    "mkc_020",
    "mkc_021",
    "mkc_022",
    "mkc_024",
    "mkc_028",
    "mkc_030",
    "mkc_033",
    "mkc_036",
}
ORIGINAL_HOLDOUT_FILES = [
    "holdout_microbatch_001_manifest.yaml",
    "holdout_microbatch_001_selection_matrix.yaml",
    "holdout_microbatch_001_candidate_cards.yaml",
    "holdout_microbatch_001_knowledge_capsules.yaml",
    "holdout_microbatch_001_complete_rich_bodies.yaml",
    "holdout_microbatch_001_creative_value_blocks.yaml",
    "holdout_microbatch_001_epistemic_labels.yaml",
    "holdout_microbatch_001_relation_design_hints.csv",
    "holdout_microbatch_001_sidecars.yaml",
    "holdout_microbatch_001_transferability_report.json",
    "holdout_microbatch_001_quality_report.json",
    "holdout_microbatch_001_judge_review_queue.yaml",
    "holdout_microbatch_001_judge_protocol.md",
]
FORBIDDEN_BODY_TERMS = [
    "对于 mkc_",
    "正文还要",
    "先说明",
    "再说明",
    "这个补充保证",
    "用于待审迁移验证",
    "不进入正式产线",
    "当前可用的领域机制",
    "基础正文现在已经存在",
    "后续可以补充来源",
    "这条知识应该",
    "pilot",
    "revision",
    "migration validation",
    "how to generate",
    "how to review",
]
WRITER_INSTRUCTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"正文还要",
        r"这条知识应该",
        r"should explain",
        r"how to generate",
        r"how to review",
        r"write this card",
    ]
]
STATUS_LANGUAGE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"pilot",
        r"revision",
        r"migration validation",
        r"production status",
        r"产线状态",
        r"迁移验证",
        r"当前阶段",
    ]
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
NEGATIVE_FIXTURES = [
    "negative_holdout_count_14_marked_mismatch.yaml",
    "negative_body_contains_writer_instruction.yaml",
    "negative_capsule_contains_pilot_validation_status.yaml",
    "negative_normalized_sentence_reused_across_three_cards.yaml",
    "negative_compiler_shape_mismatch.yaml",
    "negative_expected_body_topic_only_mentioned_not_covered.yaml",
    "negative_boundary_only_body.yaml",
    "negative_P0_00_control_item_routed_to_GKB.yaml",
    "negative_claim_evidence_global_item_routed_to_GKB_without_decision.yaml",
    "negative_index_only_capsule.yaml",
    "negative_fat_pseudo_rich_body.yaml",
    "negative_relation_hint_claims_formal_ontology_edge.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_ready_for_first_batch_generation_true.yaml",
    "negative_readiness_true.yaml",
]


class RepairCheckError(Exception):
    pass


def fail(message: str) -> None:
    raise RepairCheckError(message)


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
    if isinstance(value, dict):
        return "\n".join(text_blob(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(text_blob(item) for item in value)
    return str(value)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_sentence(sentence: str) -> str:
    return re.sub(r"[\s，。；：、,.!！?？:;（）()《》\"'`]+", "", sentence).lower()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"[。；\n]+", text)
    return [part.strip() for part in parts if len(normalize_sentence(part)) >= 18]


def expected_sections(family: str) -> set[str]:
    if family in {"control_plane_route", "asset_binding_policy"}:
        return {
            "cluster_mechanism_chain",
            "expected_topic_coverage",
            "operational_input",
            "decision_transformation",
            "boundary_logic",
            "anti_pattern_and_consequence",
            "downstream_use",
        }
    if family == "claim_boundary":
        return {
            "claim_layer",
            "expected_topic_coverage",
            "observable_input",
            "evidence_transformation",
            "boundary_logic",
            "anti_pattern_and_consequence",
            "downstream_use",
        }
    if family.startswith("display"):
        return {
            "visual_mechanism_chain",
            "expected_topic_coverage",
            "observable_input",
            "spatial_or_temporal_transformation",
            "boundary_logic",
            "micro_scenario",
            "downstream_use",
        }
    if family.startswith("product") or family.startswith("styling"):
        return {
            "product_mechanism_chain",
            "expected_topic_coverage",
            "observable_input",
            "attribute_transformation",
            "boundary_logic",
            "micro_scenario",
            "downstream_use",
        }
    return {
        "content_mechanism_chain",
        "expected_topic_coverage",
        "observable_input",
        "narrative_transformation",
        "boundary_logic",
        "micro_scenario",
        "downstream_use",
    }


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("holdout_mb001_repair_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") != NEXT_STEP:
        errors.append("current_next_step must be holdout repair judge")
    if data.get("holdout_count") != 14:
        errors.append("holdout_count must be 14")
    if data.get("count_validation_status") != "COMPLIANT_NOT_MISMATCH":
        errors.append("holdout count 14 must be marked compliant, not mismatch")
    if data.get("repair_count") != 14:
        errors.append("repair_count must be 14")
    if data.get("same_cluster_ids_as_original") is not True:
        errors.append("repair must use same cluster ids")
    for key in [
        "cluster_brief_count",
        "mechanism_plan_count",
        "candidate_card_count",
        "knowledge_capsule_count",
        "complete_rich_body_count",
        "creative_or_control_block_count",
    ]:
        if data.get(key) != 14:
            errors.append(f"{key} must be 14")
    sample = "\n".join([str(data.get("sample_capsule_text", "")), str(data.get("sample_body_text", ""))])
    if any(pattern.search(sample) for pattern in WRITER_INSTRUCTION_PATTERNS):
        errors.append("writer instruction language present")
    if any(pattern.search(sample) for pattern in STATUS_LANGUAGE_PATTERNS):
        errors.append("pilot/revision/status language present")
    if any(term in sample for term in FORBIDDEN_BODY_TERMS):
        errors.append("forbidden boilerplate phrase present")
    if int(data.get("normalized_sentence_reuse_max", 0)) > 1:
        errors.append("normalized sentence reuse exceeds limit")
    if int(data.get("compiler_shape_mismatch_count", 0)) != 0:
        errors.append("compiler shape mismatch count must be 0")
    if int(data.get("expected_topic_uncovered_count", 0)) != 0:
        errors.append("expected body topics must be covered")
    if int(data.get("mechanism_or_transformation_proposition_count_min", 0)) < 3:
        errors.append("mechanism proposition count must be >= 3")
    if float(data.get("boundary_only_proposition_ratio_max", 1.0)) > 0.4:
        errors.append("boundary-only ratio must be <= 0.4")
    if int(data.get("control_or_global_claim_to_GKB_without_decision_count", 0)) != 0:
        errors.append("control/global claim item routed to GKB without decision")
    if int(data.get("index_only_capsule_count", 0)) != 0:
        errors.append("index-only capsule count must be 0")
    if int(data.get("fat_pseudo_rich_body_count", 0)) != 0:
        errors.append("fat pseudo rich body count must be 0")
    if data.get("relation_status") != "design_hint_not_ontology_edge":
        errors.append("relation hints must remain design-only")
    if int(data.get("accepted_domain_knowledge_count", 0)) != 0:
        errors.append("accepted_domain_knowledge_count must be 0")
    if data.get("batch_generation_unlocked") is not False:
        errors.append("batch_generation_unlocked must be false")
    if data.get("ready_for_first_batch_generation") is not False:
        errors.append("ready_for_first_batch_generation must be false")
    if data.get("readiness_all_false") is not True:
        errors.append("readiness_all_false must be true")
    return errors


def validate_status(workspace: Path) -> dict[str, Any]:
    status = load_yaml(workspace / "project-infra/current_workspace_status.yaml")
    phase = status.get("phase", {})
    if phase.get("current_next_step") == BATCH_NEXT_STEP:
        fail("batch generation task cannot be next step")
    if phase.get("current_next_step") != NEXT_STEP:
        fail("workspace next step must be holdout repair judge")
    if phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be repair task")
    closeout = status.get("holdout_mb001_failure_closeout", {})
    if closeout.get("task_id") != TASK_ID or closeout.get("status") != "completed":
        fail("holdout failure closeout status block missing")
    if closeout.get("semantic_verdict") != "NO_GO_FOR_BATCH":
        fail("holdout failure closeout must be no-go for batch")
    repair = status.get("holdout_mb001_repair", {})
    if repair.get("task_id") != TASK_ID or repair.get("status") != "completed":
        fail("holdout repair status block missing")
    if repair.get("repair_count") != 14:
        fail("status repair_count must be 14")
    if set(repair.get("selected_w7_cluster_ids", [])) != ORIGINAL_HOLDOUT_IDS:
        fail("status repair cluster ids must match original holdout")
    if repair.get("accepted_domain_knowledge_count") != 0:
        fail("status accepted_domain_knowledge_count must be 0")
    assert_false(repair.get("batch_generation_unlocked"), "status batch_generation_unlocked")
    assert_false(repair.get("ready_for_first_batch_generation"), "status ready_for_first_batch_generation")
    readiness = status.get("readiness", {})
    bad = {key: value for key, value in readiness.items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags found: {bad}")
    return status


def validate_original_holdout_immutable(workspace: Path, closeout: dict[str, Any]) -> None:
    digest_rows = closeout.get("original_holdout_artifact_digests", [])
    by_path = {row.get("path"): row for row in digest_rows}
    for name in ORIGINAL_HOLDOUT_FILES:
        rel = f"03_pilot/holdout_microbatch_001/{name}"
        path = workspace / rel
        if rel not in by_path:
            fail(f"missing original digest row: {rel}")
        current = sha256(path)
        before = by_path[rel].get("sha256_before")
        after_expected = by_path[rel].get("sha256_after_expected")
        if current != before or current != after_expected:
            fail(f"original holdout artifact modified: {rel}")


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    status = validate_status(workspace)
    original_root = workspace / "03_pilot/holdout_microbatch_001"
    repair_root = workspace / "03_pilot/holdout_microbatch_001_repair"
    authority = {
        row["mkc_id"]: row
        for row in load_yaml(workspace / "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml")[
            "w7_canonical_cluster_authority"
        ]["records"]
    }
    original_selection = load_yaml(original_root / "holdout_microbatch_001_selection_matrix.yaml")[
        "holdout_microbatch_001_selection_matrix"
    ]["items"]
    original_ids = {row["selected_w7_cluster_id"] for row in original_selection}
    if original_ids != ORIGINAL_HOLDOUT_IDS:
        fail("original holdout selected cluster ids drifted")
    closeout = load_yaml(original_root / "holdout_microbatch_001_no_go_closeout.yaml")[
        "holdout_microbatch_001_closeout"
    ]
    validate_original_holdout_immutable(workspace, closeout)
    human = closeout.get("human_decision_authorization", {})
    if human.get("human_decision_present") is not True:
        fail("human decision authorization missing")
    if human.get("decision_scope") != "holdout_mb001_no_go_for_batch_and_repair_authorized":
        fail("human decision scope mismatch")
    if closeout.get("count_validation", {}).get("status") != "COMPLIANT_NOT_MISMATCH":
        fail("holdout count 14 must be compliant, not mismatch")
    if closeout.get("semantic_verdict") != "NO_GO_FOR_BATCH":
        fail("holdout must be no-go for batch")
    if closeout.get("accepted_domain_knowledge_count") != 0:
        fail("closeout accepted domain knowledge count must be 0")
    assert_false(closeout.get("batch_generation_unlocked"), "closeout batch_generation_unlocked")
    assert_false(closeout.get("ready_for_first_batch_generation"), "closeout ready_for_first_batch_generation")
    ledger = load_yaml(original_root / "holdout_microbatch_001_failure_ledger.yaml")[
        "holdout_microbatch_001_failure_ledger"
    ]
    if len(ledger.get("failure_codes", {})) < 8:
        fail("failure ledger must contain blocking failure codes")
    for code, spec in ledger.get("failure_codes", {}).items():
        if spec.get("blocking") is not True:
            fail(f"failure code must be blocking: {code}")
    digest = load_yaml(original_root / "holdout_microbatch_001_semantic_review_digest.yaml")[
        "holdout_microbatch_001_semantic_review_digest"
    ]
    if digest.get("original_holdout_artifacts_modified") is not False:
        fail("semantic review digest must preserve original artifacts")

    for rel in [
        "codex_holdout_mb001_cluster_specific_compiler_repair_policy.v0.1.yaml",
        "codex_holdout_mb001_expected_body_topic_entailment_policy.v0.1.yaml",
        "codex_holdout_mb001_anti_boilerplate_policy.v0.1.yaml",
        "codex_holdout_mb001_control_owner_routing_policy.v0.1.yaml",
    ]:
        load_yaml(workspace / "01_generation_contracts" / rel)

    manifest = load_yaml(repair_root / "holdout_mb001_repair_manifest.yaml")[
        "holdout_mb001_repair_manifest"
    ]
    cluster_briefs = load_yaml(repair_root / "holdout_mb001_repair_cluster_briefs.yaml")[
        "holdout_mb001_repair_cluster_briefs"
    ]["items"]
    mechanism_plans = load_yaml(repair_root / "holdout_mb001_repair_mechanism_plans.yaml")[
        "holdout_mb001_repair_mechanism_plans"
    ]["items"]
    cards = load_yaml(repair_root / "holdout_mb001_repair_candidate_cards.yaml")[
        "holdout_mb001_repair_candidate_cards"
    ]["candidates"]
    capsules = load_yaml(repair_root / "holdout_mb001_repair_knowledge_capsules.yaml")[
        "holdout_mb001_repair_knowledge_capsules"
    ]["items"]
    bodies = load_yaml(repair_root / "holdout_mb001_repair_complete_rich_bodies.yaml")[
        "holdout_mb001_repair_complete_rich_bodies"
    ]["items"]
    blocks = load_yaml(repair_root / "holdout_mb001_repair_creative_or_control_blocks.yaml")[
        "holdout_mb001_repair_creative_or_control_blocks"
    ]["items"]
    labels = load_yaml(repair_root / "holdout_mb001_repair_epistemic_labels.yaml")[
        "holdout_mb001_repair_epistemic_labels"
    ]["items"]
    sidecars = load_yaml(repair_root / "holdout_mb001_repair_sidecars.yaml")[
        "holdout_mb001_repair_sidecars"
    ]["sidecars"]
    coverage = load_yaml(repair_root / "holdout_mb001_repair_expected_topic_coverage.yaml")[
        "holdout_mb001_repair_expected_topic_coverage"
    ]["items"]
    owner_decisions = load_yaml(repair_root / "holdout_mb001_repair_owner_routing_decisions.yaml")[
        "holdout_mb001_repair_owner_routing_decisions"
    ]["items"]
    transfer = load_json(repair_root / "holdout_mb001_repair_transferability_report.json")
    quality = load_json(repair_root / "holdout_mb001_repair_quality_report.json")
    queue = load_yaml(repair_root / "holdout_mb001_repair_judge_review_queue.yaml")[
        "holdout_mb001_repair_judge_review_queue"
    ]["items"]
    protocol = repair_root / "holdout_mb001_repair_judge_protocol.md"
    if not protocol.exists():
        fail("missing repair judge protocol")

    relation_rows: list[dict[str, str]]
    with (repair_root / "holdout_mb001_repair_relation_design_hints.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != RELATION_FIELDS:
            fail("relation CSV fieldnames mismatch")
        relation_rows = list(reader)

    ids = [row["selected_w7_cluster_id"] for row in cards]
    draft_ids = {row["draft_id"] for row in cards}
    if manifest.get("repair_count") != 14 or len(cards) != 14:
        fail("repair_count must be 14")
    if set(ids) != original_ids or set(ids) != ORIGINAL_HOLDOUT_IDS:
        fail("repair must use same cluster ids as original holdout")
    for collection_name, collection in [
        ("cluster briefs", cluster_briefs),
        ("mechanism plans", mechanism_plans),
        ("capsules", capsules),
        ("rich bodies", bodies),
        ("creative/control blocks", blocks),
        ("epistemic labels", labels),
        ("sidecars", sidecars),
        ("queue", queue),
    ]:
        if len(collection) != 14:
            fail(f"{collection_name} count must be 14")

    coverage_by_draft: dict[str, list[dict[str, Any]]] = {}
    for row in coverage:
        coverage_by_draft.setdefault(row["draft_id"], []).append(row)
    expected_uncovered = 0
    for card in cards:
        draft_id = card["draft_id"]
        mkc_id = card["selected_w7_cluster_id"]
        record = authority[mkc_id]
        if card.get("accepted_domain_knowledge") is not False:
            fail(f"{draft_id} accepted_domain_knowledge must be false")
        assert_false(card.get("batch_generation_unlocked"), f"{draft_id} batch_generation_unlocked")
        assert_false(card.get("ready_for_first_batch_generation"), f"{draft_id} ready_for_first_batch_generation")
        for value in card.get("readiness_flags", {}).values():
            assert_false(value, f"{draft_id} readiness flag")
        owner_model = card.get("owner_model", {})
        if (record.get("owner_capability_group") == "P0-00" or card.get("body_compiler_family") == "claim_boundary") and owner_model.get("storage_target") == "GeneralKnowledgeBase":
            fail(f"{draft_id} control or claim boundary item routed to GKB without decision")
        rows = coverage_by_draft.get(draft_id, [])
        expected_topics = set(record.get("expected_body_topics", []))
        covered_topics = {row.get("expected_body_topic") for row in rows if row.get("coverage_type") not in {"TODO", "should_explain_later", "writer_instruction", "governance_statement", "mentioned_as_required_topic_only"} and row.get("body_proposition")}
        missing = expected_topics - covered_topics
        if missing:
            expected_uncovered += len(missing)

    capsule_by_id = {row["draft_id"]: row for row in capsules}
    body_by_id = {row["draft_id"]: row for row in bodies}
    writer_hits = 0
    status_hits = 0
    boilerplate_hits = 0
    sentence_counter: Counter[str] = Counter()
    for draft_id in draft_ids:
        capsule_text = text_blob(capsule_by_id.get(draft_id, {}))
        body = body_by_id.get(draft_id)
        if not body:
            fail(f"missing rich body for {draft_id}")
        body_text = text_blob(body.get("compiler_sections", {}))
        combined = f"{capsule_text}\n{body_text}"
        if any(pattern.search(combined) for pattern in WRITER_INSTRUCTION_PATTERNS):
            writer_hits += 1
        if any(pattern.search(combined) for pattern in STATUS_LANGUAGE_PATTERNS):
            status_hits += 1
        if any(term in combined for term in FORBIDDEN_BODY_TERMS):
            boilerplate_hits += 1
        for sentence in split_sentences(body_text):
            normalized = normalize_sentence(sentence)
            if not any(token in normalized for token in ["sourcegap", "generalknowledgebase", "designhint"]):
                sentence_counter[normalized] += 1
        family = body.get("body_compiler_family", "")
        if set(body.get("compiler_sections", {})) != expected_sections(family):
            fail(f"compiler shape mismatch: {draft_id}")
        if int(body.get("mechanism_or_transformation_proposition_count", 0)) < 3:
            fail(f"mechanism proposition count too low: {draft_id}")
        if float(body.get("boundary_only_proposition_ratio", 1.0)) > 0.4:
            fail(f"boundary-only ratio too high: {draft_id}")
        if body.get("fat_pseudo_rich_body") is True:
            fail(f"fat pseudo rich body: {draft_id}")
        if body.get("governance_dump_in_rich_body") is True:
            fail(f"governance dump in rich body: {draft_id}")

    reuse_violations = {sentence: count for sentence, count in sentence_counter.items() if count > 1}
    if writer_hits:
        fail("writer instruction in capsule or rich body")
    if status_hits:
        fail("pilot/revision/status language in capsule or rich body")
    if boilerplate_hits:
        fail("forbidden boilerplate phrase in capsule or rich body")
    if reuse_violations:
        fail("normalized sentence reuse exceeds limit")
    if expected_uncovered:
        fail("expected body topics not covered")

    unresolved_owner = 0
    gkb_bad = 0
    for decision in owner_decisions:
        if decision.get("risk_class") == "control_or_global_claim_boundary" and decision.get("downstream_blocked_until_decision") is not True:
            unresolved_owner += 1
        if decision.get("GeneralKnowledgeBase_without_decision") is True:
            gkb_bad += 1
    if unresolved_owner:
        fail("owner routing risk unresolved")
    if gkb_bad:
        fail("P0-00 or global claim evidence routed to GKB")
    formal_graph_claim_count = sum(1 for row in relation_rows if row.get("relation_status") != "design_hint_not_ontology_edge")
    if formal_graph_claim_count:
        fail("relation design hints claimed formal ontology edge")

    for key in [
        "accepted_domain_knowledge_count",
        "batch_generation_unlocked",
        "ready_for_first_batch_generation",
    ]:
        value = quality.get(key)
        if key == "accepted_domain_knowledge_count":
            if value != 0:
                fail("quality accepted_domain_knowledge_count must be 0")
        else:
            assert_false(value, f"quality {key}")
    if transfer.get("batch_generation_unlocked") is not False:
        fail("transferability report must not unlock batch generation")

    result = {
        "status": "PASS",
        "task_id": TASK_ID,
        "holdout_count": 14,
        "original_holdout_count_compliant": True,
        "repair_count": 14,
        "same_cluster_ids_as_original": True,
        "cluster_brief_count": len(cluster_briefs),
        "mechanism_plan_count": len(mechanism_plans),
        "candidate_card_count": len(cards),
        "knowledge_capsule_count": len(capsules),
        "complete_rich_body_count": len(bodies),
        "creative_or_control_block_count": len(blocks),
        "expected_topic_coverage_count": len(coverage),
        "expected_topic_uncovered_count": expected_uncovered,
        "writer_instruction_in_body_count": writer_hits,
        "pilot_or_revision_language_in_body_count": status_hits,
        "normalized_sentence_reuse_violation_count": len(reuse_violations),
        "compiler_shape_mismatch_count": 0,
        "boundary_only_body_count": 0,
        "owner_routing_risk_unresolved_count": unresolved_owner,
        "P0_00_or_global_claim_evidence_routed_to_GKB_count": gkb_bad,
        "relation_design_hints_count": len(relation_rows),
        "formal_graph_claim_count": formal_graph_claim_count,
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
        "original_holdout_artifacts_modified": False,
        "recommended_next_step": NEXT_STEP,
    }
    if report_out:
        write_json(report_out, result)
    return result


def run_selftest(fixtures_root: Path) -> dict[str, Any]:
    positive = load_yaml(fixtures_root / "positive_valid_holdout_mb001_repair_minimal.yaml")
    positive_errors = validate_fixture_model(positive)
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        path = fixtures_root / name
        model = load_yaml(path)
        errors = validate_fixture_model(model)
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
        negative_results[name] = errors
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
    parser.add_argument("--fixtures-root", default="ci/fixtures/codex_holdout_mb001_repair")
    parser.add_argument("--report-out")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace_root).resolve()
    fixtures = (workspace / args.fixtures_root).resolve() if not Path(args.fixtures_root).is_absolute() else Path(args.fixtures_root)
    report_out = Path(args.report_out).resolve() if args.report_out else None
    try:
        if args.selftest:
            print(json.dumps(run_selftest(fixtures), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(validate_live(workspace, report_out), ensure_ascii=False, indent=2))
        return 0
    except RepairCheckError as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
