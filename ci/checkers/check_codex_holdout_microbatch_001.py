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

TASK_ID = "CODEX-SEMANTIC-PILOT-V4_7-PASS-CLOSEOUT-METADATA-CLEANUP-AND-HOLDOUT-MICROBATCH-001"
PREVIOUS_TASK_ID = "CODEX-SEMANTIC-PILOT-V4_6-CONDITIONAL-REPAIR-CLOSEOUT-AND-V4_7-SEMANTIC-CLEANUP-001"
NEXT_STEP = "CODEX-HOLDOUT-MICROBATCH-001-JUDGE-GO-NOGO-001"
REPAIR_NEXT_STEP = "HOLDOUT-MB001-REPAIR-JUDGE-GO-NOGO-001"
BATCH_NEXT_STEP = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_MIN = 12
EXPECTED_MAX = 16
SAMPLED_MKC_IDS = {"mkc_004", "mkc_006", "mkc_009", "mkc_010", "mkc_026", "mkc_027", "mkc_032", "mkc_034"}
FORBIDDEN_LABEL_TERMS = ["胶囊语义清理版", "语义清理", "V4", "V4.7", "修订", "pilot", "judge"]
GOVERNANCE_DUMP_TERMS = ["readiness", "W7", "checker", "batch eligibility", "CandidatePack", "RAG", "DIFY", "KE", "Serving"]
REAL_INSTANCE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"SKU[-_ ]?[A-Z0-9]+",
        r"品牌A",
        r"门店A",
        r"张三",
        r"李四",
        r"王女士",
        r"价格[:： ]?\d+",
        r"库存[:： ]?\d+",
        r"actual brand",
        r"actual store",
        r"real SKU",
    ]
]
DIRECT_PUBLISH_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in [r"直接发布脚本", r"发布文案如下", r"最终发布稿", r"ready to publish"]]
PERFORMANCE_TERMS = ["透气", "抗皱", "耐穿", "持久舒适", "回弹性能", "保证显瘦", "保证舒适", "长期不变形"]
RELATION_FIELDS = [
    "relation_id", "source_draft_id", "artifact_kind", "subject_ref", "subject_type", "predicate_id", "predicate_family", "object_ref", "object_type", "condition", "evidence_requirement", "owner_scope", "body_proposition_ref", "w7_required_relation_ref", "relation_status",
]
NEGATIVE_FIXTURES = [
    "negative_canonical_label_contains_semantic_cleanup_version.yaml",
    "negative_human_motive_without_creative_hypothesis_label.yaml",
    "negative_control_plane_has_material_observation_check_terms.yaml",
    "negative_holdout_count_less_than_12.yaml",
    "negative_holdout_uses_v4_sampled_mkc_id.yaml",
    "negative_holdout_only_has_capsule_no_rich_body.yaml",
    "negative_holdout_capsule_is_tag_index_only.yaml",
    "negative_rich_body_is_padding_or_governance_dump.yaml",
    "negative_relation_hint_claims_formal_ontology_edge.yaml",
    "negative_real_instance_fact_leak.yaml",
    "negative_direct_publish_script_leak.yaml",
    "negative_safe_alternative_performance_claim.yaml",
    "negative_accepted_domain_knowledge_count_positive.yaml",
    "negative_batch_generation_unlocked_true.yaml",
    "negative_ready_for_first_batch_generation_true.yaml",
    "negative_readiness_true.yaml",
]


class HoldoutCheckError(Exception):
    pass


def fail(message: str) -> None:
    raise HoldoutCheckError(message)


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


def blob(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(blob(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(blob(v) for v in value)
    return str(value)


def has_real_instance(text: str) -> bool:
    return any(pattern.search(text) for pattern in REAL_INSTANCE_PATTERNS)


def has_direct_publish(text: str) -> bool:
    return any(pattern.search(text) for pattern in DIRECT_PUBLISH_PATTERNS)


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("holdout_microbatch_001_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("current_next_step") == BATCH_NEXT_STEP:
        errors.append("batch generation task cannot be next step")
    if data.get("current_next_step") not in {NEXT_STEP, REPAIR_NEXT_STEP}:
        errors.append("current_next_step must be holdout microbatch judge or repair judge")
    count = int(data.get("holdout_count", 0))
    if count < EXPECTED_MIN or count > EXPECTED_MAX:
        errors.append("holdout_count must be 12..16")
    selected = set(data.get("selected_w7_cluster_ids", []))
    if selected & SAMPLED_MKC_IDS:
        errors.append("holdout selected a previously sampled cluster")
    if int(data.get("body_compiler_family_count", 0)) < 4:
        errors.append("holdout must cover at least four body compiler families")
    label = str(data.get("canonical_label_zh", ""))
    if any(term in label for term in FORBIDDEN_LABEL_TERMS):
        errors.append("canonical label contains revision/process terms")
    field_typing = data.get("field_level_epistemic_typing", {})
    for key in ["human_motive", "audience_cognition_shift", "aesthetic_tension", "generative_option_space"]:
        if key in data.get("creative_fields_present", []) and field_typing.get(key) != "creative_hypothesis_not_audience_fact":
            errors.append(f"{key} must be typed as creative_hypothesis_not_audience_fact")
    control_fields = set(data.get("control_plane_check_fields", []))
    forbidden_control = {"visible_structure", "material_observation", "surface_texture", "silhouette"}
    if control_fields & forbidden_control:
        errors.append("control plane uses material observation check fields")
    if data.get("every_holdout_has_candidate_card") is not True:
        errors.append("every holdout must have candidate card")
    if data.get("every_holdout_has_knowledge_capsule") is not True:
        errors.append("every holdout must have knowledge capsule")
    if data.get("every_holdout_has_complete_rich_body") is not True:
        errors.append("every holdout must have complete rich body")
    if data.get("every_holdout_has_creative_value_block_or_control_body") is not True:
        errors.append("every holdout must have creative/control body")
    if data.get("every_holdout_has_epistemic_labels") is not True:
        errors.append("every holdout must have epistemic labels")
    if data.get("every_holdout_has_sidecar") is not True:
        errors.append("every holdout must have sidecar")
    if data.get("index_only_capsule_count") != 0:
        errors.append("index-only capsule count must be 0")
    if data.get("capsule_without_rich_body_count") != 0:
        errors.append("capsule without rich body count must be 0")
    if data.get("governance_dump_in_rich_body_count") != 0:
        errors.append("governance dump in rich body count must be 0")
    if data.get("relation_status") != "design_hint_not_ontology_edge":
        errors.append("relation status must remain design_hint_not_ontology_edge")
    if data.get("real_instance_fact_leak_count") != 0 or has_real_instance(str(data.get("sample_text", ""))):
        errors.append("real instance fact leak count must be 0")
    if data.get("direct_publish_script_leak_count") != 0 or has_direct_publish(str(data.get("sample_text", ""))):
        errors.append("direct publish script leak count must be 0")
    safe_alt = blob(data.get("safe_creative_alternatives", []))
    if data.get("safe_alternative_performance_claim_count") != 0 or any(term in safe_alt for term in PERFORMANCE_TERMS):
        errors.append("safe creative alternative cannot become a performance claim")
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
    current_next_step = phase.get("current_next_step")
    if current_next_step not in {NEXT_STEP, REPAIR_NEXT_STEP}:
        fail("workspace next step must be holdout microbatch judge or repair judge")
    if current_next_step == NEXT_STEP and phase.get("previous_step") != TASK_ID:
        fail("workspace previous step must be holdout task")
    if current_next_step == REPAIR_NEXT_STEP:
        repair = status.get("holdout_mb001_repair", {})
        if repair.get("task_id") != "HOLDOUT-MB001-FAIL-CLOSEOUT-AND-CLUSTER-SPECIFIC-COMPILER-REPAIR-001" or repair.get("status") != "completed":
            fail("repair judge route requires completed holdout_mb001_repair block")
        if repair.get("repair_count") != 14:
            fail("repair judge route requires 14 repair drafts")
        if repair.get("accepted_domain_knowledge_count") != 0:
            fail("repair judge route requires accepted_domain_knowledge_count 0")
        assert_false(repair.get("batch_generation_unlocked"), "repair batch_generation_unlocked")
        assert_false(repair.get("ready_for_first_batch_generation"), "repair ready_for_first_batch_generation")
    closeout = status.get("v4_7_pass_closeout", {})
    if closeout.get("task_id") != TASK_ID or closeout.get("status") != "completed":
        fail("v4_7_pass_closeout block missing")
    if closeout.get("V4_7_original_artifacts_modified") is not False:
        fail("V4.7 original artifacts must not be modified")
    holdout = status.get("holdout_microbatch_001", {})
    if holdout.get("task_id") != TASK_ID or holdout.get("status") != "completed":
        fail("holdout_microbatch_001 status block missing")
    if holdout.get("holdout_scope") != "pilot_validation_only":
        fail("holdout scope must be pilot_validation_only")
    if holdout.get("not_formal_microbatch_generation") is not True:
        fail("holdout must not be formal microbatch generation")
    if holdout.get("holdout_count", 0) < EXPECTED_MIN or holdout.get("holdout_count", 99) > EXPECTED_MAX:
        fail("holdout count must be 12..16")
    if set(holdout.get("selected_w7_cluster_ids", [])) & SAMPLED_MKC_IDS:
        fail("status selected previously sampled cluster")
    if holdout.get("body_compiler_family_count", 0) < 4:
        fail("status body compiler family count must be >= 4")
    if holdout.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must remain 0")
    assert_false(holdout.get("batch_generation_unlocked"), "holdout batch_generation_unlocked")
    assert_false(holdout.get("ready_for_first_batch_generation"), "holdout ready_for_first_batch_generation")
    if holdout.get("ready_for_holdout_microbatch_001_judge_review") is not True:
        fail("holdout must be ready for judge review only")
    bad = {key: value for key, value in status.get("readiness", {}).items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")
    return status


def validate_live(workspace: Path, report_out: Path | None) -> dict[str, Any]:
    v47_root = workspace / "03_pilot/semantic_v4_7"
    root = workspace / "03_pilot/holdout_microbatch_001"
    closeout = load_yaml(v47_root / "v4_7_pass_for_repair_direction_closeout.yaml")["v4_7_closeout"]
    patch = load_yaml(v47_root / "v4_7_metadata_cleanup_patch.yaml")["metadata_cleanup_patch"]
    digest = load_yaml(v47_root / "v4_7_semantic_review_digest.yaml")["v4_7_semantic_review_digest"]
    if closeout.get("human_decision_authorization", {}).get("human_decision_present") is not True:
        fail("human decision authorization missing")
    if closeout.get("semantic_verdict") != "PASS_FOR_REPAIR_DIRECTION":
        fail("V4.7 closeout must be pass for repair direction")
    if closeout.get("retained_as") == "high_signal_candidate_asset_template_baseline":
        fail("retained_as must not imply batch template baseline")
    if "batch_generation_template" not in closeout.get("not_yet", []):
        fail("closeout must preserve not_yet batch_generation_template")
    if closeout.get("V4_7_original_artifacts_modified") is not False or digest.get("V4_7_original_artifacts_modified") is not False:
        fail("V4.7 original artifacts must not be modified")
    for item in patch.get("canonical_label_cleanup", {}).get("patches", []):
        after = item.get("after", "")
        if any(term in after for term in FORBIDDEN_LABEL_TERMS):
            fail(f"metadata patch label still contains process term: {item}")
    for key in ["human_motive", "audience_cognition_shift", "aesthetic_tension", "generative_option_space"]:
        if key not in patch.get("creative_hypothesis_field_typing", {}).get("applies_to", []):
            fail(f"metadata patch missing creative hypothesis typing for {key}")
    policies = [
        workspace / "01_generation_contracts/codex_holdout_microbatch_001_policy.v0.1.yaml",
        workspace / "01_generation_contracts/codex_holdout_microbatch_001_full_asset_requirement.v0.1.yaml",
        workspace / "01_generation_contracts/codex_holdout_microbatch_001_selection_policy.v0.1.yaml",
    ]
    for policy in policies:
        load_yaml(policy)
    authority = {r["mkc_id"]: r for r in load_yaml(workspace / "01_generation_contracts/w7_canonical_cluster_authority.v0.1.yaml")["w7_canonical_cluster_authority"]["records"]}
    manifest = load_yaml(root / "holdout_microbatch_001_manifest.yaml")["holdout_microbatch_001_manifest"]
    matrix = load_yaml(root / "holdout_microbatch_001_selection_matrix.yaml")["holdout_microbatch_001_selection_matrix"]["items"]
    cards = load_yaml(root / "holdout_microbatch_001_candidate_cards.yaml")["holdout_microbatch_001_candidate_cards"]["candidates"]
    capsules = load_yaml(root / "holdout_microbatch_001_knowledge_capsules.yaml")["holdout_microbatch_001_knowledge_capsules"]["items"]
    bodies = load_yaml(root / "holdout_microbatch_001_complete_rich_bodies.yaml")["holdout_microbatch_001_complete_rich_bodies"]["items"]
    creative = load_yaml(root / "holdout_microbatch_001_creative_value_blocks.yaml")["holdout_microbatch_001_creative_value_blocks"]["items"]
    epistemic = load_yaml(root / "holdout_microbatch_001_epistemic_labels.yaml")["holdout_microbatch_001_epistemic_labels"]["items"]
    sidecars = load_yaml(root / "holdout_microbatch_001_sidecars.yaml")["holdout_microbatch_001_sidecars"]["sidecars"]
    queue = load_yaml(root / "holdout_microbatch_001_judge_review_queue.yaml")["holdout_microbatch_001_judge_review_queue"]["items"]
    transfer = load_json(root / "holdout_microbatch_001_transferability_report.json")
    quality = load_json(root / "holdout_microbatch_001_quality_report.json")
    if manifest.get("task_id") != TASK_ID or manifest.get("recommended_next_step") != NEXT_STEP:
        fail("manifest task or next step mismatch")
    if manifest.get("holdout_scope") != "pilot_validation_only" or manifest.get("not_formal_microbatch_generation") is not True:
        fail("manifest must declare pilot validation only")
    if manifest.get("holdout_count") < EXPECTED_MIN or manifest.get("holdout_count") > EXPECTED_MAX:
        fail("manifest holdout count must be 12..16")
    selected = set(manifest.get("selected_w7_cluster_ids", []))
    if selected & SAMPLED_MKC_IDS:
        fail("manifest selected previously sampled cluster")
    if not selected.issubset(authority):
        fail("manifest selected cluster outside W7 authority")
    if len(set(manifest.get("excluded_previous_sampled_cluster_ids", [])) & SAMPLED_MKC_IDS) != len(SAMPLED_MKC_IDS):
        fail("manifest must list excluded previous sampled cluster ids")
    if manifest.get("body_compiler_family_count", 0) < 4:
        fail("body compiler family count must be >= 4")
    if len(cards) != manifest["holdout_count"]:
        fail("candidate card count mismatch")
    by_id = {item["draft_id"]: item for item in cards}
    bundles = {
        "knowledge_capsule": {item["draft_id"]: item for item in capsules},
        "complete_rich_body": {item["draft_id"]: item for item in bodies},
        "creative_or_control": {item["draft_id"]: item for item in creative},
        "epistemic": {item["draft_id"]: item for item in epistemic},
        "sidecar": {item["draft_id"]: item for item in sidecars},
    }
    for name, collection in bundles.items():
        if set(collection) != set(by_id):
            fail(f"bundle mismatch for {name}")
    if len(queue) != len(cards) or {item.get("draft_id") for item in queue} != set(by_id):
        fail("judge queue must contain all holdout drafts")
    matrix_by_id = {item["draft_id"]: item for item in matrix}
    if set(matrix_by_id) != set(by_id):
        fail("selection matrix must cover every holdout draft")
    family_count = len({item.get("body_compiler_family") for item in matrix})
    if family_count < 4:
        fail("selection matrix must cover at least four compiler families")
    mix = Counter(item.get("selection_bucket") for item in matrix)
    if not (3 <= mix.get("content_method_or_narrative", 0) <= 4):
        fail("content/narrative mix out of range")
    if not (2 <= mix.get("claim_or_evidence_boundary", 0) <= 3):
        fail("claim/evidence mix out of range")
    if not (3 <= mix.get("display_or_execution_asset", 0) <= 4):
        fail("display/execution mix out of range")
    if not (1 <= mix.get("control_or_governance", 0) <= 2):
        fail("control/governance mix out of range")
    if not (3 <= mix.get("product_or_material_or_styling_method", 0) <= 4):
        fail("product/material/styling mix out of range")
    index_only = 0
    capsule_without_body = 0
    governance_dump = 0
    real_leaks = 0
    publish_leaks = 0
    safe_perf = 0
    for draft_id, card in by_id.items():
        mkc = card.get("selected_w7_cluster_id")
        if mkc in SAMPLED_MKC_IDS:
            fail(f"{draft_id}: sampled mkc reused")
        if mkc not in authority:
            fail(f"{draft_id}: selected mkc missing from authority")
        if card.get("canonical_cluster_title_from_authority") != authority[mkc]["canonical_title"]:
            fail(f"{draft_id}: authority title mismatch")
        if any(term in card.get("canonical_label_zh", "") for term in FORBIDDEN_LABEL_TERMS):
            fail(f"{draft_id}: canonical label contains process term")
        if card.get("accepted_domain_knowledge") is not False:
            fail(f"{draft_id}: accepted domain knowledge must be false")
        assert_false(card.get("batch_generation_unlocked"), f"{draft_id} batch_generation_unlocked")
        assert_false(card.get("ready_for_first_batch_generation"), f"{draft_id} ready_for_first_batch_generation")
        if any(value is not False for value in card.get("readiness_flags", {}).values()):
            fail(f"{draft_id}: readiness flag true")
        capsule = bundles["knowledge_capsule"][draft_id]
        cap_fields = ["domain_question", "core_mechanism", "observable_material", "transfer_logic", "boundary_guardrail", "generative_options", "failure_signal", "downstream_effect"]
        if any(not blob(capsule.get(field, "")).strip() for field in cap_fields):
            index_only += 1
            fail(f"{draft_id}: capsule missing required body field")
        if len(blob(capsule)) < 220:
            index_only += 1
            fail(f"{draft_id}: capsule is too thin")
        body = bundles["complete_rich_body"][draft_id]
        sections = body.get("compiler_sections", {})
        if not sections:
            capsule_without_body += 1
            fail(f"{draft_id}: rich body missing")
        body_text = blob(sections)
        if len(body_text) < 450:
            fail(f"{draft_id}: rich body too short")
        if any(term in body_text for term in GOVERNANCE_DUMP_TERMS):
            governance_dump += 1
            fail(f"{draft_id}: governance dump term in rich body")
        if len(set(str(value).strip() for value in sections.values())) != len(sections):
            fail(f"{draft_id}: repeated rich body section text")
        content_text = "\n".join(
            [
                str(card.get("canonical_label_zh", "")),
                str(card.get("candidate_topic", "")),
                str(card.get("canonical_body_zh", "")),
                blob(capsule),
                body_text,
                blob(bundles["creative_or_control"][draft_id].get("safe_creative_alternatives", [])),
            ]
        )
        if has_real_instance(content_text):
            real_leaks += 1
            fail(f"{draft_id}: real instance fact leak")
        if has_direct_publish(content_text):
            publish_leaks += 1
            fail(f"{draft_id}: direct publish script leak")
        creative_block = bundles["creative_or_control"][draft_id]
        if any(term in blob(creative_block.get("safe_creative_alternatives", [])) for term in PERFORMANCE_TERMS):
            safe_perf += 1
            fail(f"{draft_id}: safe creative alternative became performance claim")
        ep = bundles["epistemic"][draft_id]
        if card.get("body_compiler_family") == "control_plane_route" and any(field in ep.get("type_specific_epistemic_check_fields", []) for field in ["visible_structure", "material_observation", "surface_texture", "silhouette"]):
            fail(f"{draft_id}: control plane has material observation check fields")
        sidecar = bundles["sidecar"][draft_id]
        if sidecar.get("holdout_scope") != "pilot_validation_only":
            fail(f"{draft_id}: sidecar holdout scope mismatch")
        if sidecar.get("accepted_domain_knowledge_count") != 0:
            fail(f"{draft_id}: sidecar accepted_domain_knowledge_count must be 0")
        for key in ["batch_generation_unlocked", "ready_for_first_batch_generation", "candidatepack_created", "KE_touched", "Serving_touched", "RAG_touched", "DIFY_touched"]:
            assert_false(sidecar.get(key), f"{draft_id} sidecar {key}")
    with (root / "holdout_microbatch_001_relation_design_hints.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or list(rows[0]) != RELATION_FIELDS:
        fail("relation design hints schema mismatch")
    formal_claims = 0
    for row in rows:
        if row["source_draft_id"] not in by_id:
            fail("relation references unknown draft")
        if row["relation_status"] != "design_hint_not_ontology_edge":
            formal_claims += 1
            fail("relation status must remain design hint")
        if "formal ontology" in row.get("condition", "").lower() and "not formal" not in row.get("condition", "").lower():
            formal_claims += 1
            fail("relation hint claims formal ontology")
    status = validate_status(workspace)
    for persisted, label in [(transfer, "transferability report"), (quality, "quality report")]:
        for key in ["holdout_count", "candidate_card_count", "knowledge_capsule_count", "complete_rich_body_count", "real_instance_fact_leak_count", "accepted_domain_knowledge_count"]:
            if persisted.get(key) != (len(cards) if key.endswith("count") and key in {"holdout_count", "candidate_card_count", "knowledge_capsule_count", "complete_rich_body_count"} else 0):
                if key in {"holdout_count", "candidate_card_count", "knowledge_capsule_count", "complete_rich_body_count"}:
                    fail(f"{label} mismatch for {key}")
        if persisted.get("batch_generation_unlocked") is not False or persisted.get("readiness_all_false") is not True:
            fail(f"{label} readiness/batch mismatch")
    fixtures_root = workspace / "ci/fixtures/codex_holdout_microbatch_001"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_holdout_microbatch_001_minimal.yaml"))
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
        "holdout_count": len(cards),
        "selected_w7_cluster_count": len(selected),
        "selected_w7_cluster_ids": sorted(selected),
        "excluded_previous_sampled_cluster_ids": sorted(SAMPLED_MKC_IDS),
        "excluded_previous_sampled_cluster_count": len(SAMPLED_MKC_IDS),
        "body_compiler_family_count": family_count,
        "candidate_card_count": len(cards),
        "knowledge_capsule_count": len(capsules),
        "complete_rich_body_count": len(bodies),
        "creative_value_or_control_body_count": len(creative),
        "epistemic_label_count": len(epistemic),
        "sidecar_count": len(sidecars),
        "relation_design_hints_count": len(rows),
        "index_only_capsule_count": index_only,
        "capsule_without_rich_body_count": capsule_without_body,
        "governance_dump_in_rich_body_count": governance_dump,
        "real_instance_fact_leak_count": real_leaks,
        "direct_publish_script_leak_count": publish_leaks,
        "safe_alternative_performance_claim_count": safe_perf,
        "formal_graph_claim_count": formal_claims,
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
        "workspace_status_block_present": "holdout_microbatch_001" in status,
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
    fixtures_root = workspace / "ci/fixtures/codex_holdout_microbatch_001"
    positive_errors = validate_fixture_model(load_yaml(fixtures_root / "positive_valid_holdout_microbatch_001_minimal.yaml"))
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name))
        negative_results[name] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")
    return {"status": "PASS", "positive_fixture_count": 1, "negative_fixture_count": len(NEGATIVE_FIXTURES), "negative_fixtures_fail_closed": True, "negative_results": negative_results}


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
    except HoldoutCheckError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
