#!/usr/bin/env python3
"""Fail-closed checker for the P7D 600 scale-contract design."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import yaml


TASK_ID = "GKB-P7D-600-EXPRESSION-DIVERSITY-AND-SAMPLED-ACCEPTANCE-CONTRACT-001"
BASELINE_HEAD = "42d8a07948161bef1956a76da78f75890ae554a0"
FROZEN_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
SUCCESS_STATUS = (
    "P7D_600_SCALE_CONTRACT_DESIGN_COMPLETE_"
    "HOLD_FOR_FOUNDER_SINGLE_CLUSTER_PROBE_AUTHORIZATION"
)
FROZEN_CORPUS_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
OUTPUT_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "scale_contract_600_001"
)
CONTRACT_PATH = OUTPUT_DIR / (
    "p7d_600_expression_diversity_and_sampled_acceptance_contract.v0.1.yaml"
)
RESULT_PATH = OUTPUT_DIR / "p7d_600_scale_contract_design_result.v0.1.yaml"
REPORT_PATH = Path("ci/reports/p7d_600_scale_contract_report.v0.1.json")

EXPECTED_P0_CLUSTERS = {
    "P0_01": 6,
    "P0_02": 7,
    "P0_03": 10,
    "P0_04": 9,
    "P0_05": 8,
}
EXPECTED_P0_PLANNED = {
    "P0_01": 90,
    "P0_02": 105,
    "P0_03": 150,
    "P0_04": 135,
    "P0_05": 120,
}
EXPECTED_PLATFORMS = {
    "douyin": 120,
    "xiaohongshu": 120,
    "wechat_channels": 120,
    "moments": 120,
    "live": 120,
}
EXPECTED_GENERATION_MODES = {
    "creative_prototype": 240,
    "fact_slot_script": 240,
    "display_solution": 120,
    "evidence_bound_candidate": 0,
}
EXPECTED_CAPTURE = {
    "daily_native": 488,
    "lightly_guided": 90,
    "campaign_directed": 22,
}
EXPECTED_RISK_INPUTS = [
    "p0_group",
    "canonical_cluster_id",
    "generation_mode",
    "capture_mode",
    "required_claim_route",
    "platform",
    "primary_voice_lane",
    "narrative_truth_mode",
]
FORBIDDEN_RISK_INPUTS = [
    "body_text",
    "CPSS",
    "grade",
    "success_or_failure",
    "machine_verdict",
    "human_verdict",
    "human_preference",
    "generated_quality_metric",
]


def add_error(
    errors: list[dict[str, str]], code: str, section: str, detail: str
) -> None:
    errors.append({"code": code, "section": section, "detail": detail})


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"JSONL row is not an object: {path}:{line_number}")
        records.append(value)
    return records


def derive_frozen_topology(records: list[dict[str, Any]]) -> dict[str, Any]:
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        clusters[str(record.get("canonical_cluster_id"))].append(record)
    mixed_clusters = {
        cluster_id: sorted({str(item.get("p0_group")) for item in items})
        for cluster_id, items in clusters.items()
        if len({item.get("p0_group") for item in items}) != 1
    }
    p0_clusters = Counter(
        str(next(iter({item.get("p0_group") for item in items})))
        for items in clusters.values()
        if len({item.get("p0_group") for item in items}) == 1
    )
    return {
        "asset_count": len(records),
        "unique_kernel_count": len({record.get("kernel_id") for record in records}),
        "cluster_count": len(clusters),
        "per_cluster_counts": Counter(len(items) for items in clusters.values()),
        "mixed_clusters": mixed_clusters,
        "p0_cluster_counts": dict(p0_clusters),
    }


def validate_frozen_reference(
    root: dict[str, Any], topology: dict[str, Any], frozen_sha: str
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    reference = root.get("frozen_reference_corpus", {})
    expected = {
        "corpus_id": "FOUNDER-REVIEWED-CLEAN-120-REFERENCE-CORPUS-001",
        "version": "1.0.0",
        "path": FROZEN_CORPUS_PATH.as_posix(),
        "sha256": FROZEN_SHA256,
        "asset_count": 120,
        "unique_kernel_count": 120,
        "immutable": True,
        "reference_only": True,
    }
    if reference != expected or frozen_sha != FROZEN_SHA256:
        add_error(errors, "E_FROZEN_CORPUS_PIN", "frozen_reference", frozen_sha)
    if (
        topology.get("asset_count") != 120
        or topology.get("unique_kernel_count") != 120
        or topology.get("cluster_count") != 40
        or topology.get("per_cluster_counts") != Counter({3: 40})
        or topology.get("mixed_clusters")
        or topology.get("p0_cluster_counts") != EXPECTED_P0_CLUSTERS
    ):
        add_error(errors, "E_FROZEN_TOPOLOGY", "frozen_reference", repr(topology))
    return errors


def validate_current_state(root: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    state = root.get("current_task_state", {})
    expected = {
        "planning_target_count": 600,
        "actual_assignment_count": 0,
        "actual_draft_count": 0,
        "actual_generation_record_count": 0,
        "materialized_sample_id_count": 0,
        "runtime_checkpoint_event_count": 0,
        "external_llm_called": False,
        "knowledge_count_increment": 0,
        "contract_design_complete": True,
        "generation_authorization": "NOT_ISSUED",
        "single_cluster_probe_authorization": "NOT_ISSUED",
        "generation_600_go_decision": "NOT_ISSUED",
        "batch_acceptance": "NOT_EXECUTED",
    }
    if state != expected:
        add_error(errors, "E_CURRENT_STATE", "current_task_state", "state drift")
    materialization = root.get("forbidden_current_materialization", {})
    if not isinstance(materialization, dict) or any(
        not isinstance(value, int) or value != 0 for value in materialization.values()
    ):
        add_error(
            errors,
            "E_FORBIDDEN_MATERIALIZATION",
            "current_task_state",
            repr(materialization),
        )
    return errors


def validate_topology_and_quotas(
    root: dict[str, Any], topology: dict[str, Any]
) -> tuple[list[dict[str, str]], dict[str, int]]:
    errors: list[dict[str, str]] = []
    aggregate = root.get("aggregate_topology", {})
    expected_aggregate = {
        "parent_reference_asset_count": 120,
        "planned_expression_variant_count": 600,
        "variants_per_parent_reference": 5,
        "knowledge_count_after_generation": 120,
        "knowledge_count_increment": 0,
        "cluster_count": 40,
        "planned_items_per_cluster": 15,
        "cluster_total": 600,
        "P0_00_body_generation_count": 0,
        "parent_kernel_reuse_is_expression_variation_not_new_knowledge": True,
        "new_kernel_creation_allowed": False,
    }
    if aggregate != expected_aggregate:
        add_error(errors, "E_AGGREGATE_TOPOLOGY", "aggregate_topology", "mismatch")

    p0 = root.get("P0_allocation", {})
    p0_total = 0
    for p0_group, expected_cluster_count in EXPECTED_P0_CLUSTERS.items():
        item = p0.get(p0_group, {})
        expected_count = EXPECTED_P0_PLANNED[p0_group]
        if item != {
            "cluster_count": expected_cluster_count,
            "planned_count": expected_count,
        }:
            add_error(errors, "E_P0_ALLOCATION", p0_group, repr(item))
        p0_total += int(item.get("planned_count", 0))
    if (
        p0.get("total") != 600
        or p0_total != 600
        or p0.get("derivation") != "frozen_corpus_cluster_to_P0_mapping_times_15"
        or topology.get("p0_cluster_counts") != EXPECTED_P0_CLUSTERS
    ):
        add_error(errors, "E_P0_TOTAL", "P0_allocation", str(p0_total))

    platform = root.get("platform_allocation", {})
    platform_total = sum(int(platform.get(key, 0)) for key in EXPECTED_PLATFORMS)
    if any(platform.get(key) != value for key, value in EXPECTED_PLATFORMS.items()):
        add_error(errors, "E_PLATFORM_ALLOCATION", "platform_allocation", "values")
    if platform.get("total") != 600 or platform_total != 600:
        add_error(
            errors, "E_PLATFORM_TOTAL", "platform_allocation", str(platform_total)
        )
    per_cluster = platform.get("per_cluster", {})
    per_parent = platform.get("per_parent_reference", {})
    if per_cluster != {
        "planned_count": 15,
        "platform_family_coverage_min": 5,
        "any_single_platform_max": 5,
    }:
        add_error(errors, "E_PLATFORM_CLUSTER", "platform_allocation", "cluster")
    if per_parent != {
        "variant_count": 5,
        "platforms_min": 3,
        "opening_families_min": 3,
        "voice_lanes_min": 2,
        "reasoning_shapes_min": 2,
        "platform_label_only_variation_forbidden": True,
    }:
        add_error(errors, "E_PARENT_VARIATION", "platform_allocation", "parent")

    modes = root.get("generation_mode_allocation", {})
    mode_aggregate = modes.get("aggregate", {})
    generation_total = sum(
        int(mode_aggregate.get(key, 0)) for key in EXPECTED_GENERATION_MODES
    )
    if (
        any(
            mode_aggregate.get(key) != value
            for key, value in EXPECTED_GENERATION_MODES.items()
        )
        or mode_aggregate.get("total") != 600
    ):
        add_error(
            errors, "E_GENERATION_MODE", "generation_mode_allocation", "aggregate"
        )
    by_p0 = modes.get("by_P0", {})
    column_totals = Counter()
    for p0_group, expected_count in EXPECTED_P0_PLANNED.items():
        item = by_p0.get(p0_group, {})
        if item.get("total") != expected_count:
            add_error(errors, "E_GENERATION_P0_TOTAL", p0_group, repr(item))
        for key in ("creative_prototype", "fact_slot_script", "display_solution"):
            column_totals[key] += int(item.get(key, 0))
    if column_totals != Counter(
        {"creative_prototype": 240, "fact_slot_script": 240, "display_solution": 120}
    ):
        add_error(
            errors,
            "E_GENERATION_CROSS_TOTAL",
            "generation_mode_allocation",
            repr(column_totals),
        )
    evidence = modes.get("evidence_bound_enablement", {})
    if (
        evidence.get("enabled_in_current_plan") is not False
        or evidence.get("executor_quota_reallocation_allowed") is not False
        or evidence.get("future_assignment_contract_change_required") is not True
        or set(evidence.get("required_before_enablement", []))
        != {
            "versioned_evidence_qualified_input",
            "source_anchor",
            "claim_permission",
            "separate_Founder_authorization",
        }
    ):
        add_error(
            errors, "E_EVIDENCE_MODE_BOUNDARY", "generation_mode_allocation", "evidence"
        )
    fact_slot = modes.get("fact_slot_user_visible_boundary", {})
    if any(
        fact_slot.get(key) is not False
        for key in (
            "field_slot_leak_allowed",
            "governance_language_leak_allowed",
            "evidence_status_leak_allowed",
            "readiness_language_leak_allowed",
        )
    ):
        add_error(errors, "E_FACT_SLOT_LEAK", "generation_mode_allocation", "fact slot")

    capture = root.get("capture_mode_allocation", {})
    by_capture_p0 = capture.get("by_P0", {})
    capture_columns = Counter()
    for p0_group, expected_count in EXPECTED_P0_PLANNED.items():
        item = by_capture_p0.get(p0_group, {})
        row_total = sum(int(item.get(key, 0)) for key in EXPECTED_CAPTURE)
        if item.get("total") != expected_count or row_total != expected_count:
            add_error(errors, "E_CAPTURE_P0_TOTAL", p0_group, repr(item))
        for key in EXPECTED_CAPTURE:
            capture_columns[key] += int(item.get(key, 0))
    capture_aggregate = capture.get("aggregate", {})
    if (
        capture_columns != Counter(EXPECTED_CAPTURE)
        or any(
            capture_aggregate.get(key) != value
            for key, value in EXPECTED_CAPTURE.items()
        )
        or capture_aggregate.get("total") != 600
    ):
        add_error(
            errors, "E_CAPTURE_TOTAL", "capture_mode_allocation", repr(capture_columns)
        )
    daily = capture.get("daily_native_contract", {})
    if (
        daily.get("hired_actor_count") != 0
        or daily.get("fake_customer_count") != 0
        or daily.get("fabricated_conflict_count") != 0
        or daily.get("single_person_only") is not False
        or daily.get("natural_work_participants_must_declare_roles_and_count")
        is not True
    ):
        add_error(errors, "E_DAILY_NATIVE", "capture_mode_allocation", "daily boundary")

    return errors, {
        "cluster_total": int(aggregate.get("cluster_total", 0)),
        "P0_total": p0_total,
        "platform_total": platform_total,
        "generation_mode_total": generation_total,
        "capture_mode_total": sum(capture_columns.values()),
    }


def validate_voice_truth_and_claims(root: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    voice = root.get("voice_contract", {})
    principles = voice.get("principles", {})
    if (
        voice.get("layer") != "CSO_and_Generation_Orchestration_not_ontology_truth"
        or principles
        != {
            "professional_identity_is_authority_source": True,
            "professional_identity_does_not_require_lecture_voice": True,
            "ordinary_person_voice_does_not_erase_role_identity": True,
        }
        or set(voice.get("primary_voice_lanes", []))
        != {"professional_role_voice", "ordinary_person_voice"}
    ):
        add_error(errors, "E_VOICE_CONTRACT", "voice_contract", "identity/lane")
    cluster_voice = voice.get("per_cluster_15", {})
    if cluster_voice != {
        "professional_role_voice_min": 5,
        "ordinary_person_voice_min": 5,
        "remaining_flexible": 5,
        "joint_constraint_must_be_satisfied_with_platform_and_modes": True,
        "infeasible_route": "STOP_AND_REPAIR",
    }:
        add_error(errors, "E_VOICE_CLUSTER", "voice_contract", "cluster allocation")
    if voice.get("max_share") != {
        "scope": ["each_P0", "each_platform", "each_cluster"],
        "any_primary_voice_lane_max_share": 0.60,
    }:
        add_error(errors, "E_VOICE_SHARE", "voice_contract", "max share")
    ordinary = voice.get("ordinary_person_voice", {})
    if (
        ordinary.get("identity_role_must_remain") is not True
        or "fake_autobiography" not in ordinary.get("forbidden", [])
        or "fake_customer_story" not in ordinary.get("forbidden", [])
    ):
        add_error(errors, "E_ORDINARY_IDENTITY", "voice_contract", "ordinary lane")

    truth = root.get("narrative_truth_contract", {})
    modes = truth.get("modes", {})
    if (
        truth.get("hard_boundary") != "no_new_unsupported_real_world_assertion"
        or truth.get("creative_processing_is_not_automatically_fabrication") is not True
        or set(modes)
        != {
            "verified_real_event",
            "routine_work_demonstration",
            "role_embodied_generalization",
            "bounded_composite_prototype",
            "creative_fiction",
        }
        or modes.get("creative_fiction", {}).get("allowed_in_current_600") is not False
    ):
        add_error(errors, "E_NARRATIVE_TRUTH", "narrative_truth_contract", "modes")
    if set(modes.get("verified_real_event", {}).get("requires", [])) != {
        "source_anchor",
        "owner_or_person_authorization",
        "claim_scope_alignment",
    }:
        add_error(errors, "E_VERIFIED_EVENT", "narrative_truth_contract", "anchors")
    if not {
        "pretend_just_happened",
        "pretend_real_customer_participated",
    } <= set(modes.get("routine_work_demonstration", {}).get("forbidden", [])):
        add_error(errors, "E_PROTOTYPE_AS_REAL", "narrative_truth_contract", "routine")

    claims = root.get("personal_experience_claim_gate", {})
    if set(claims.get("autobiographical_credential_claim", {}).get("requires", [])) != {
        "person_source_anchor",
        "persona_owner_authorization",
    }:
        add_error(errors, "E_CREDENTIAL_GATE", "personal_claim_gate", "credential")
    if set(claims.get("episodic_memory_claim", {}).get("requires", [])) != {
        "event_source_anchor",
        "participant_authorization",
    }:
        add_error(errors, "E_EPISODIC_GATE", "personal_claim_gate", "episode")
    if set(claims.get("testimonial_or_outcome_claim", {}).get("requires", [])) != {
        "evidence",
        "claim_permission",
        "correct_generation_mode",
    }:
        add_error(errors, "E_OUTCOME_GATE", "personal_claim_gate", "outcome")
    hard_gate = claims.get("hard_gate", {})
    if not isinstance(hard_gate, dict) or set(hard_gate.values()) != {0}:
        add_error(
            errors, "E_PERSONAL_HARD_GATE", "personal_claim_gate", repr(hard_gate)
        )
    if (
        claims.get("fabricated_evidence_allowed") is not False
        or claims.get("delete_all_first_person_for_safety_allowed") is not False
    ):
        add_error(
            errors, "E_PERSONAL_FALLBACK", "personal_claim_gate", "unsafe fallback"
        )
    return errors


def validate_platform_and_formula(root: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    expression = root.get("event_and_platform_expression", {})
    platforms = expression.get("platforms", {})
    if set(platforms) != set(EXPECTED_PLATFORMS):
        add_error(errors, "E_PLATFORM_CONTRACT", "platform_contract", "coverage")
    event = expression.get("event_carried_expression", {})
    if (
        len(event.get("required_except_strategy_or_evidence", [])) != 5
        or event.get("strategy_or_evidence_exception", {}).get(
            "compliance_courseware_forbidden"
        )
        is not True
    ):
        add_error(errors, "E_EVENT_CARRIED", "platform_contract", "event")

    formula = root.get("anti_formula_contract", {})
    diagnostic = formula.get("diagnostic_only", {})
    if (
        formula.get("semantic_safety_priority") is not True
        or diagnostic.get("may_trigger_human_review") is not True
        or diagnostic.get("may_trigger_automatic_rewrite") is not False
        or diagnostic.get("may_fail_asset_by_itself") is not False
    ):
        add_error(errors, "E_DIAGNOSTIC_ONLY", "anti_formula_contract", "diagnostic")
    if not {
        "negation_word_frequency",
        "sequence_word_frequency",
    } <= set(diagnostic.get("features", [])):
        add_error(errors, "E_NEGATION_DIAGNOSTIC", "anti_formula_contract", "features")
    forbidden = set(formula.get("forbidden_repairs", []))
    if (
        not {
            "delete_negation_words",
            "move_sentences_to_lower_fingerprint",
            "synonym_skinning",
            "lower_claim_safety_for_diversity",
        }
        <= forbidden
    ):
        add_error(
            errors, "E_UNSAFE_FORMULA_REPAIR", "anti_formula_contract", repr(forbidden)
        )
    hard = formula.get("anti_copy_hard_gate", {})
    if (
        hard.get("exact_body_duplicate_count") != 0
        or hard.get("normalized_body_duplicate_count") != 0
        or hard.get("exact_opening_sentence_reuse_max") != 3
        or hard.get("exact_closing_sentence_reuse_max") != 3
    ):
        add_error(errors, "E_ANTI_COPY_GATE", "anti_formula_contract", "hard gate")
    overlap = formula.get("reference_overlap", {})
    if overlap.get("longest_contiguous_exact_overlap_max_chars") != 17:
        add_error(errors, "E_REFERENCE_OVERLAP", "anti_formula_contract", "threshold")
    floor = formula.get("cluster_diversity_floor", {})
    if floor != {
        "opening_families_min": 6,
        "reasoning_shapes_min": 5,
        "closing_families_min": 4,
        "same_complete_fingerprint_max": 2,
        "deep_same_person_voice_requires_human_review": True,
    }:
        add_error(errors, "E_DIVERSITY_FLOOR", "anti_formula_contract", "floor")
    return errors


def validate_probe_checkpoint_and_sampling(
    root: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    probe = root.get("pre_600_probe", {})
    if (
        probe.get("task_id")
        != "GKB-P7D-SINGLE-CLUSTER-DUAL-VOICE-DIVERSITY-PROBE-15-001"
        or probe.get("output_count") != 15
        or probe.get("cluster_selection", {}).get("eligible_group") != "P0_05"
        or probe.get("cluster_selection", {}).get("materialize_cluster_id_now")
        is not False
        or probe.get("cluster_selection", {}).get("assignment_created_now") is not False
        or probe.get("probe_generation_authorized_by_current_contract") is not False
        or probe.get("founder_separate_authorization_required") is not True
        or probe.get("generation_600_unlocked_by_probe") is not False
    ):
        add_error(errors, "E_PROBE_BOUNDARY", "pre_600_probe", "probe")
    allocation = probe.get("required_allocation", {})
    if (
        allocation.get("professional_role_voice_min") != 5
        or allocation.get("ordinary_person_voice_min") != 5
        or allocation.get("remaining_flexible") != 5
        or sum(
            int(allocation.get(key, 0))
            for key in (
                "professional_role_voice_min",
                "ordinary_person_voice_min",
                "remaining_flexible",
            )
        )
        != 15
        or allocation.get("constraints_must_be_jointly_satisfied") is not True
    ):
        add_error(errors, "E_PROBE_ALLOCATION", "pre_600_probe", "allocation")

    checkpoints = root.get("checkpoint_stop_resume_contract", {})
    plan = checkpoints.get("checkpoint_plan", {})
    if plan != {
        "checkpoint_count": 10,
        "work_items_per_checkpoint": 60,
        "planned_total": 600,
        "checkpoint_default_state": "STOPPED",
        "complete_clusters_per_checkpoint": 4,
        "items_per_cluster": 15,
    }:
        add_error(errors, "E_CHECKPOINT_PLAN", "checkpoint", "plan")
    forbidden = set(checkpoints.get("forbidden", []))
    if (
        not {
            "automatic_checkpoint_continue",
            "silent_continue_after_failure",
            "delete_failed_work_item",
            "resample_or_replace_failed_sample",
            "overgenerate_then_select_best",
        }
        <= forbidden
    ):
        add_error(errors, "E_CHECKPOINT_FAIL_CLOSED", "checkpoint", repr(forbidden))
    correction = checkpoints.get("bounded_correction", {})
    if (
        correction.get("correction_per_item_max") != 1
        or correction.get("total_correction_count_max") != 60
        or correction.get("silent_regeneration_allowed") is not False
        or correction.get("threshold_route") != "STOP_AND_REPAIR_CONTRACT_OR_GENERATOR"
    ):
        add_error(errors, "E_CORRECTION_BOUNDARY", "checkpoint", "correction")

    sampling = root.get("pre_generation_sampling_protocol", {})
    if sampling.get("materialize_sample_ids_now") is not False:
        add_error(errors, "E_SAMPLE_MATERIALIZED", "sampling", "sample IDs")
    expected_order = [
        "freeze_contract_digest",
        "freeze_assignment_manifest_digest",
        "compute_sample_ids_before_body_generation",
        "freeze_sample_plan_digest",
        "obtain_separate_Founder_generation_authorization",
        "generate",
    ]
    if sampling.get("order") != expected_order:
        add_error(errors, "E_SAMPLE_ORDER", "sampling", "order")
    rank = sampling.get("sample_rank", {})
    if rank != {
        "algorithm": "sha256",
        "ordered_inputs": [
            "contract_digest",
            "assignment_manifest_digest",
            "sample_scope",
            "work_item_id",
        ],
    }:
        add_error(errors, "E_SAMPLE_RANK", "sampling", "rank")
    risk = sampling.get("risk_stratum_function", {})
    if (
        risk.get("timing") != "pre_generation_only"
        or risk.get("allowed_inputs") != EXPECTED_RISK_INPUTS
        or risk.get("forbidden_inputs") != FORBIDDEN_RISK_INPUTS
        or risk.get("output_score_or_post_generation_feature_count") != 0
    ):
        add_error(errors, "E_RISK_STRATUM", "sampling", "pre-generation features")
    if set(sampling.get("selection_forbidden_inputs", [])) != {
        "body_text",
        "CPSS",
        "grade",
        "success_or_failure",
        "human_preference",
        "post_generation_selection",
    }:
        add_error(errors, "E_SAMPLE_SELECTION_INPUT", "sampling", "forbidden inputs")
    guardian = sampling.get("guardian_sample", {})
    founder = sampling.get("founder_sample", {})
    if (
        guardian.get("count") != 120
        or guardian.get("base_per_cluster") != 3
        or founder.get("count") != 60
        or founder.get("subset_of_guardian_sample") is not True
        or founder.get("base_per_cluster") != 1
        or founder.get("pre_generation_risk_stratum_extra") != 20
    ):
        add_error(errors, "E_SAMPLE_COUNTS", "sampling", "counts")
    if (
        sampling.get("adverse_case_policy", {}).get("replace_base_sample") is not False
        or sampling.get("failed_work_item_policy", {}).get("retain_original_id")
        is not True
        or sampling.get("failed_work_item_policy", {}).get("replacement_allowed")
        is not False
    ):
        add_error(errors, "E_RESAMPLE_POLICY", "sampling", "replacement")
    return errors


def validate_human_machine_and_authority(root: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    human = root.get("human_review_contract", {})
    acceptance = human.get("acceptance", {})
    expected_thresholds = {
        "overall_A_or_B_rate_min": 0.90,
        "each_P0_A_or_B_rate_min": 0.85,
        "each_platform_A_or_B_rate_min": 0.85,
        "professional_voice_A_or_B_rate_min": 0.85,
        "ordinary_person_voice_A_or_B_rate_min": 0.85,
        "D_count": 0,
        "fake_as_real_hard_failure_count": 0,
        "personal_claim_hard_failure_count": 0,
        "role_or_claim_hard_failure_count": 0,
        "daily_native_feasible_rate_min": 0.95,
        "formulaic_voice_failure_rate_max": 0.10,
        "any_stratum_formulaic_voice_failure_rate_max": 0.15,
        "hard_failure_cannot_be_averaged_away": True,
    }
    if acceptance != expected_thresholds or len(human.get("dimensions", [])) != 12:
        add_error(errors, "E_HUMAN_ACCEPTANCE", "human_review", "thresholds")
    machine = root.get("future_machine_gate_and_stop", {})
    if (
        len(machine.get("machine_hard_gates", [])) != 13
        or "any_auto_GO_or_readiness_true" not in machine.get("stop_conditions", [])
        or "any_fake_as_real" not in machine.get("stop_conditions", [])
        or "any_D_grade" not in machine.get("stop_conditions", [])
    ):
        add_error(errors, "E_MACHINE_STOP", "machine_gate", "stop chain")
    authority = root.get("authority_state_machine", {})
    if (
        authority.get("current_result_if_contract_checker_passes") != SUCCESS_STATUS
        or authority.get("contract_checker_may_issue_generation_GO") is not False
        or authority.get("guardian_may_issue_generation_GO") is not False
        or authority.get("probe_authorization")
        != "FOUNDER_SEPARATE_AUTHORIZATION_REQUIRED"
        or authority.get("generation_authorization") != "NOT_ISSUED"
        or authority.get("generation_600_allowed") is not False
        or authority.get("expand_600_allowed") is not False
        or authority.get("expand_3600_allowed") is not False
    ):
        add_error(errors, "E_AUTHORITY_STATE", "authority_state_machine", "auto GO")
    readiness_keys = (
        "CandidatePack_ready",
        "KE_ready",
        "Serving_ready",
        "RAG_ready",
        "DIFY_ready",
        "production_ready",
        "runtime_content_kernel_ready",
    )
    if any(authority.get(key) is not False for key in readiness_keys):
        add_error(
            errors, "E_AUTHORITY_READINESS", "authority_state_machine", "readiness"
        )
    return errors


def validate_contract(
    contract: dict[str, Any], records: list[dict[str, Any]], frozen_sha: str
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    errors: list[dict[str, str]] = []
    root = contract.get("p7d_600_expression_diversity_and_sampled_acceptance_contract")
    if not isinstance(root, dict):
        add_error(errors, "E_CONTRACT_ROOT", "GLOBAL", "missing")
        return errors, {}
    if (
        root.get("task_id") != TASK_ID
        or root.get("contract_kind") != "contract_design_only_not_generation_authority"
        or root.get("canonical_contract") is not True
        or root.get("writes_to_ontology_truth") is not False
    ):
        add_error(errors, "E_CONTRACT_IDENTITY", "GLOBAL", "identity")
    topology = derive_frozen_topology(records)
    errors.extend(validate_frozen_reference(root, topology, frozen_sha))
    errors.extend(validate_current_state(root))
    quota_errors, quota_metrics = validate_topology_and_quotas(root, topology)
    errors.extend(quota_errors)
    errors.extend(validate_voice_truth_and_claims(root))
    errors.extend(validate_platform_and_formula(root))
    errors.extend(validate_probe_checkpoint_and_sampling(root))
    errors.extend(validate_human_machine_and_authority(root))
    metrics = {
        "canonical_contract_count": 1,
        "frozen_corpus_sha256_match": frozen_sha == FROZEN_SHA256,
        "planning_target_count": root.get("current_task_state", {}).get(
            "planning_target_count"
        ),
        **quota_metrics,
        "assignment_count": root.get("current_task_state", {}).get(
            "actual_assignment_count"
        ),
        "draft_count": root.get("current_task_state", {}).get("actual_draft_count"),
        "sample_id_count": root.get("current_task_state", {}).get(
            "materialized_sample_id_count"
        ),
        "generation_record_count": root.get("current_task_state", {}).get(
            "actual_generation_record_count"
        ),
    }
    return errors, metrics


def validate_result(
    result: dict[str, Any], contract_sha: str, metrics: dict[str, Any]
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    root = result.get("p7d_600_scale_contract_design_result", {})
    if root.get("result_status") != SUCCESS_STATUS:
        add_error(errors, "E_RESULT_STATUS", "result", "status")
    if root.get("canonical_contract") != {
        "count": 1,
        "path": CONTRACT_PATH.as_posix(),
        "sha256": contract_sha,
        "frozen_corpus_sha256_match": True,
        "planning_target_count": 600,
    }:
        add_error(errors, "E_RESULT_CONTRACT", "result", "contract")
    expected_quota = {
        "cluster_total": 600,
        "P0_total": 600,
        "platform_total": 600,
        "generation_mode_total": 600,
        "capture_mode_total": 600,
    }
    if root.get("quota_validation") != expected_quota or any(
        metrics.get(key) != value for key, value in expected_quota.items()
    ):
        add_error(errors, "E_RESULT_QUOTA", "result", "quota")
    if root.get("materialization") != {
        "assignment_count": 0,
        "draft_count": 0,
        "sample_id_count": 0,
        "generation_record_count": 0,
        "runtime_checkpoint_event_count": 0,
        "external_llm_called": False,
        "knowledge_count_increment": 0,
    }:
        add_error(errors, "E_RESULT_MATERIALIZATION", "result", "materialization")
    decision = root.get("decision_state", {})
    if decision != {
        "contract_design_complete": True,
        "generation_authorization": "NOT_ISSUED",
        "single_cluster_probe_authorization": "NOT_ISSUED",
        "generation_600_go_decision": "NOT_ISSUED",
        "batch_acceptance": "NOT_EXECUTED",
        "generation_600_allowed": False,
        "expand_600_allowed": False,
        "expand_3600_allowed": False,
    }:
        add_error(errors, "E_RESULT_DECISION", "result", "decision")
    next_task = root.get("next_task", {})
    if next_task != {
        "task_id": "GKB-P7D-SINGLE-CLUSTER-DUAL-VOICE-DIVERSITY-PROBE-15-001",
        "separate_founder_authorization_required": True,
        "generation_authorized_by_this_task": False,
    }:
        add_error(errors, "E_RESULT_NEXT", "result", "next task")
    if root.get("downstream_and_readiness", {}).get("all_false") is not True:
        add_error(errors, "E_RESULT_READINESS", "result", "readiness")
    return errors


def git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return completed.stdout


def validate_ledger(root: Path, contract_sha: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    yaml_path = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
    current = load_yaml_mapping(root / yaml_path)
    baseline = yaml.safe_load(
        git_output(root, "show", f"{BASELINE_HEAD}:{yaml_path.as_posix()}")
    )
    current_root = current.get("grc_3600_execution_plan_status", {})
    baseline_root = baseline.get("grc_3600_execution_plan_status", {})
    migration = current_root.get("route_migration_18")
    if not isinstance(migration, dict):
        add_error(errors, "E_ROUTE_MIGRATION_18", "ledger", "absent")
        return errors
    without_migration = copy.deepcopy(current_root)
    without_migration.pop("route_migration_18", None)
    if without_migration != baseline_root:
        add_error(errors, "E_LEDGER_NON_ADDITIVE", "ledger", "outside migration18")
    if migration.get("current_task") != {
        "task_id": TASK_ID,
        "task_type": "contract_design_only",
        "canonical_contract_sha256": contract_sha,
    }:
        add_error(errors, "E_ROUTE_TASK", "ledger", "current task")
    if migration.get("completion") != {
        "contract_design_status": "COMPLETE",
        "generation_authorization": "NOT_ISSUED",
        "generation_600_allowed": False,
        "result_status": SUCCESS_STATUS,
    }:
        add_error(errors, "E_ROUTE_COMPLETION", "ledger", "completion")
    if migration.get(
        "next_if_guardian_pass"
    ) != "GKB-P7D-SINGLE-CLUSTER-DUAL-VOICE-DIVERSITY-PROBE-15-001" or migration.get(
        "next_task_authorization"
    ) != {"separate_founder_authorization_required": True}:
        add_error(errors, "E_ROUTE_NEXT", "ledger", "next")
    if migration.get("scale") != {
        "generation_600_allowed": False,
        "expand_600_allowed": False,
        "expand_3600_allowed": False,
    }:
        add_error(errors, "E_ROUTE_SCALE", "ledger", "scale")
    if migration.get("downstream_and_readiness") != {"all_false": True}:
        add_error(errors, "E_ROUTE_READINESS", "ledger", "readiness")
    md_path = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.md")
    current_md = (root / md_path).read_text(encoding="utf-8")
    baseline_md = git_output(root, "show", f"{BASELINE_HEAD}:{md_path.as_posix()}")
    if not current_md.startswith(baseline_md):
        add_error(errors, "E_LEDGER_MD_NON_ADDITIVE", "ledger", "not append-only")
    if (
        "## P7D 600 Expression Diversity Contract Design"
        not in current_md[len(baseline_md) :]
    ):
        add_error(errors, "E_LEDGER_MD_SECTION", "ledger", "summary absent")
    return errors


def validate_git_surface(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    allowed_prefixes = (
        OUTPUT_DIR.as_posix() + "/",
        "ci/fixtures/p7d_600_scale_contract/",
    )
    allowed_exact = {
        "ci/checkers/check_p7d_600_scale_contract.py",
        REPORT_PATH.as_posix(),
        "docs/reports/p7d_600_scale_contract_report.md",
        "docs/reports/p7d_600_scale_contract_receipt.json",
        "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
        "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    }
    changed = set(git_output(root, "diff", "--name-only", BASELINE_HEAD).splitlines())
    changed.update(
        git_output(root, "ls-files", "--others", "--exclude-standard").splitlines()
    )
    for line in git_output(root, "status", "--porcelain=v1").splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.add(path)
    for path in sorted(changed):
        if path in allowed_exact or path.startswith(allowed_prefixes):
            continue
        add_error(errors, "E_WRITE_SURFACE", "git", path)
    if FROZEN_CORPUS_PATH.as_posix() in changed:
        add_error(
            errors, "E_FROZEN_CORPUS_MODIFIED", "git", FROZEN_CORPUS_PATH.as_posix()
        )
    output_files = {
        path.name for path in (root / OUTPUT_DIR).iterdir() if path.is_file()
    }
    if output_files != {CONTRACT_PATH.name, RESULT_PATH.name}:
        add_error(errors, "E_OUTPUT_FILE_SET", "git", repr(sorted(output_files)))
    if any(path.endswith(".jsonl") for path in changed):
        add_error(errors, "E_GENERATION_ARTIFACT", "git", "new JSONL")
    disallowed_file_tokens = (
        "assignment_manifest",
        "generation_record",
        "sample_ids",
        "checkpoint_event",
        "runner.py",
    )
    for path in changed:
        if any(token in Path(path).name.lower() for token in disallowed_file_tokens):
            add_error(errors, "E_FORBIDDEN_FILE", "git", path)
    return errors


def load_bundle(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    contract = load_yaml_mapping(root / CONTRACT_PATH)
    result = load_yaml_mapping(root / RESULT_PATH)
    records = load_jsonl(root / FROZEN_CORPUS_PATH)
    return contract, result, records


def run_live(
    root: Path, write_report: bool
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    contract, result, records = load_bundle(root)
    frozen_sha = sha256_file(root / FROZEN_CORPUS_PATH)
    contract_sha = sha256_file(root / CONTRACT_PATH)
    errors, metrics = validate_contract(contract, records, frozen_sha)
    errors.extend(validate_result(result, contract_sha, metrics))
    errors.extend(validate_ledger(root, contract_sha))
    errors.extend(validate_git_surface(root))
    metrics["canonical_contract_sha256"] = contract_sha
    metrics["frozen_corpus_sha256"] = frozen_sha
    metrics["generation_authorization"] = "NOT_ISSUED"
    metrics["generation_600_allowed"] = False
    report = {
        "task_id": TASK_ID,
        "checker_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "metrics": metrics,
        "result_status": SUCCESS_STATUS
        if not errors
        else "SCALE_CONTRACT_DESIGN_BLOCKED",
    }
    if write_report:
        path = root / REPORT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return errors, report


Mutator = Callable[[dict[str, Any], dict[str, int]], None]


def run_selftest(root: Path) -> dict[str, Any]:
    contract, _, records = load_bundle(root)
    positive_errors, _ = validate_contract(contract, records, FROZEN_SHA256)
    cases: list[tuple[str, Mutator]] = []

    def add_case(name: str, mutator: Mutator) -> None:
        cases.append((name, mutator))

    def contract_root(value: dict[str, Any]) -> dict[str, Any]:
        return value["p7d_600_expression_diversity_and_sampled_acceptance_contract"]

    add_case(
        "frozen_digest_wrong",
        lambda value, state: contract_root(value)["frozen_reference_corpus"].update(
            {"sha256": "0" * 64}
        ),
    )
    add_case(
        "P0_total_not_600",
        lambda value, state: contract_root(value)["P0_allocation"]["P0_01"].update(
            {"planned_count": 89}
        ),
    )
    add_case(
        "platform_missing",
        lambda value, state: contract_root(value)["platform_allocation"].pop("live"),
    )
    add_case(
        "cluster_count_missing",
        lambda value, state: contract_root(value)["aggregate_topology"].update(
            {"cluster_count": 39}
        ),
    )
    add_case(
        "voice_lane_coverage_missing",
        lambda value, state: contract_root(value)["voice_contract"].update(
            {"primary_voice_lanes": ["professional_role_voice"]}
        ),
    )
    add_case(
        "assignment_materialized",
        lambda value, state: contract_root(value)["current_task_state"].update(
            {"actual_assignment_count": 1}
        ),
    )
    add_case(
        "sample_id_materialized",
        lambda value, state: contract_root(value)[
            "pre_generation_sampling_protocol"
        ].update({"materialize_sample_ids_now": True}),
    )

    def sample_uses_output(value: dict[str, Any], _state: dict[str, int]) -> None:
        risk = contract_root(value)["pre_generation_sampling_protocol"][
            "risk_stratum_function"
        ]
        risk["allowed_inputs"].append("body_text")

    add_case("sample_depends_on_body_or_score", sample_uses_output)
    add_case(
        "failed_item_replacement_allowed",
        lambda value, state: contract_root(value)["pre_generation_sampling_protocol"][
            "failed_work_item_policy"
        ].update({"replacement_allowed": True}),
    )

    def checkpoint_auto_continue(value: dict[str, Any], _state: dict[str, int]) -> None:
        forbidden = contract_root(value)["checkpoint_stop_resume_contract"]["forbidden"]
        forbidden.remove("automatic_checkpoint_continue")

    add_case("checkpoint_auto_continue", checkpoint_auto_continue)
    add_case(
        "machine_pass_auto_GO",
        lambda value, state: contract_root(value)["authority_state_machine"].update(
            {"contract_checker_may_issue_generation_GO": True}
        ),
    )
    add_case(
        "negation_frequency_becomes_hard_gate",
        lambda value, state: contract_root(value)["anti_formula_contract"][
            "diagnostic_only"
        ].update({"may_fail_asset_by_itself": True}),
    )
    add_case(
        "claim_safety_lowered_for_diversity",
        lambda value, state: contract_root(value)["anti_formula_contract"].update(
            {"semantic_safety_priority": False}
        ),
    )
    add_case(
        "ordinary_voice_erases_role",
        lambda value, state: contract_root(value)["voice_contract"][
            "ordinary_person_voice"
        ].update({"identity_role_must_remain": False}),
    )
    add_case(
        "credential_claim_without_anchor",
        lambda value, state: contract_root(value)["personal_experience_claim_gate"][
            "autobiographical_credential_claim"
        ].update({"requires": []}),
    )

    def prototype_as_real(value: dict[str, Any], _state: dict[str, int]) -> None:
        forbidden = contract_root(value)["narrative_truth_contract"]["modes"][
            "routine_work_demonstration"
        ]["forbidden"]
        forbidden.clear()

    add_case("prototype_presented_as_real", prototype_as_real)
    add_case(
        "second_canonical_truth_source",
        lambda value, state: state.update({"canonical_contract_count": 2}),
    )
    add_case(
        "generation_600_allowed_true",
        lambda value, state: contract_root(value)["authority_state_machine"].update(
            {"generation_600_allowed": True}
        ),
    )
    add_case(
        "downstream_readiness_true",
        lambda value, state: contract_root(value)["authority_state_machine"].update(
            {"KE_ready": True}
        ),
    )

    results: list[dict[str, Any]] = []
    for name, mutator in cases:
        mutable = copy.deepcopy(contract)
        state = {"canonical_contract_count": 1}
        mutator(mutable, state)
        case_errors, _ = validate_contract(mutable, records, FROZEN_SHA256)
        if state["canonical_contract_count"] != 1:
            add_error(
                case_errors,
                "E_CANONICAL_CONTRACT_COUNT",
                "GLOBAL",
                str(state["canonical_contract_count"]),
            )
        results.append(
            {
                "name": name,
                "fail_closed": bool(case_errors),
                "error_codes": sorted({item["code"] for item in case_errors}),
            }
        )
    passed = not positive_errors and all(item["fail_closed"] for item in results)
    return {
        "task_id": TASK_ID,
        "selftest_status": "PASS" if passed else "FAIL",
        "positive_fixture_pass": not positive_errors,
        "positive_fixture_errors": positive_errors,
        "negative_fixture_count": len(results),
        "negative_fixtures": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> int:
    if not __debug__:
        sys.stdout.write(
            json.dumps({"status": "FAIL_CLOSED", "reason": "python_optimized_mode"})
            + "\n"
        )
        return 2
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        if args.selftest:
            result = run_selftest(root)
            sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            return 0 if result["selftest_status"] == "PASS" else 1
        errors, report = run_live(root, write_report=True)
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0 if not errors else 1
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        yaml.YAMLError,
        subprocess.CalledProcessError,
    ) as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "checker_status": "FAIL_CLOSED",
                    "reason": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
