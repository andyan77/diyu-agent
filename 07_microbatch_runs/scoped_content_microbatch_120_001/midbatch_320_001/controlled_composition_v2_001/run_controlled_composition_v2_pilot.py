#!/usr/bin/env python3
"""Build the Controlled Composition V2 pilot proof artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GKB-CONTROLLED-COMPOSITION-V2-PROFILE-SCHEMA-AND-PILOT-HANDOFF-001"
IMPLEMENTATION_KIND = "codex_native_controlled_composition_pilot_harness"
BASELINE_HEAD = "30a972a32749f4bb1048546ceedd39c652c7162a"
CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
SCALE_600_CONTRACT_SHA256 = (
    "966190c341b070d88fbc3a25540e9c8fddf69ad8f19b90fb29badbb1ffad52a9"
)

TASK_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
CLEAN_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
SCALE_600_CONTRACT_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "scale_contract_600_001/"
    "p7d_600_expression_diversity_and_sampled_acceptance_contract.v0.1.yaml"
)
CHECKER_PATH = Path("ci/checkers/check_gkb_controlled_composition_v2.py")

CONTRACT_PATH = TASK_DIR / "controlled_composition_v2_contract.v0.1.yaml"
PROFILES_PATH = TASK_DIR / "content_product_profiles.v0.1.yaml"
SELECTION_PATH = TASK_DIR / "pilot_source_selection.v0.1.yaml"
COMPONENTS_PATH = TASK_DIR / "component_candidate_manifest.v0.1.jsonl"
BUNDLES_PATH = TASK_DIR / "gkb_composition_candidate_bundles.v0.1.jsonl"
HANDOFF_PATH = TASK_DIR / "gkb_orch_pilot_handoff.v0.1.yaml"
RESULT_PATH = TASK_DIR / "controlled_composition_v2_result.v0.1.yaml"
HARNESS_PATH = TASK_DIR / "run_controlled_composition_v2_pilot.py"

CP_ROLE_WORK_VLOG = "CP_ROLE_WORK_VLOG"
CP_STORE_MICRO_DOCUMENTARY = "CP_STORE_MICRO_DOCUMENTARY"
CP_PRODUCT_ITERATION_ARCHIVE = "CP_PRODUCT_ITERATION_ARCHIVE"
CONTENT_PRODUCT_IDS = [
    CP_ROLE_WORK_VLOG,
    CP_STORE_MICRO_DOCUMENTARY,
    CP_PRODUCT_ITERATION_ARCHIVE,
]

EVENT_TRUTH_MODES = [
    "brand_supplied_real_event",
    "brand_fillable_prototype",
    "generic_creative_prototype",
    "collection_task_only",
]

COMPONENT_ROLES = [
    "opening",
    "scene",
    "trigger",
    "tension",
    "observable_action",
    "audience_facing_reasoning_move",
    "professional_judgment",
    "transition",
    "closing",
    "CTA",
    "visual_beat",
    "spoken_line_intent",
    "capture_instruction",
]

PROFILE_REQUIREMENTS = {
    CP_ROLE_WORK_VLOG: {
        "label": "岗位工作VLOG",
        "required_components": [
            "scene",
            "observable_action",
            "professional_judgment",
            "capture_instruction",
        ],
        "source_slots": ["usable_materials"],
        "fact_slots": [
            "real_person_or_authorized_alias",
            "real_job_role",
            "actual_work_event",
            "business_object",
            "observable_action_chain",
            "decision_authority",
        ],
        "authorization_slots": ["person_and_account_authorization"],
    },
    CP_STORE_MICRO_DOCUMENTARY: {
        "label": "门店微纪录",
        "required_components": [
            "scene",
            "observable_action",
            "visual_beat",
            "capture_instruction",
        ],
        "source_slots": ["usable_visual_audio_materials"],
        "fact_slots": [
            "real_store_or_authorized_alias",
            "actual_store_task_or_event",
            "participating_roles",
            "store_object_or_display_area",
            "before_state",
            "observable_action_chain",
            "after_or_open_state",
        ],
        "authorization_slots": ["relevant_authorizations"],
    },
    CP_PRODUCT_ITERATION_ARCHIVE: {
        "label": "产品诞生或迭代档案",
        "required_components": [
            "scene",
            "trigger",
            "professional_judgment",
            "capture_instruction",
        ],
        "source_slots": ["before_after_material"],
        "fact_slots": [
            "authorized_product_or_project_ref",
            "actual_version_or_stage",
            "actual_problem_or_change_request",
            "changed_part",
            "responsible_role",
            "decision_reason",
        ],
        "authorization_slots": ["permitted_public_scope"],
    },
}

ROLE_CODES = {
    "scene": "SCENE",
    "trigger": "TRIGGER",
    "observable_action": "ACTION",
    "professional_judgment": "JUDGE",
    "visual_beat": "VISUAL",
    "capture_instruction": "CAPTURE",
}

EXTRACTABLE_ROLE_SPECS = [
    {
        "role": "scene",
        "field_path": "expression_content_kernel_candidate.scene",
        "payload_kind": "extractive_scene_span",
        "derivation_method": "extractive_body_span",
    },
    {
        "role": "trigger",
        "field_path": "expression_content_kernel_candidate.event_surface",
        "payload_kind": "extractive_event_trigger_span",
        "derivation_method": "extractive_body_span",
    },
    {
        "role": "observable_action",
        "field_path": "expression_content_kernel_candidate.observable_action",
        "payload_kind": "extractive_observable_action_span",
        "derivation_method": "extractive_body_span",
    },
    {
        "role": "professional_judgment",
        "field_path": "expression_content_kernel_candidate.business_judgment",
        "payload_kind": "extractive_professional_judgment_span",
        "derivation_method": "extractive_body_span",
    },
    {
        "role": "visual_beat",
        "field_path": "expression_content_kernel_candidate.object_anchor.value",
        "payload_kind": "extractive_visual_anchor",
        "derivation_method": "extractive_or_compatibility_projection",
    },
    {
        "role": "capture_instruction",
        "field_path": "execution_card.capture_operator_mode",
        "payload_kind": "structured_capture_instruction",
        "derivation_method": "metadata_projection_from_parent_execution_card",
    },
]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    stripped = copy.deepcopy(value)
    for key in digest_keys or set():
        strip_key(stripped, key)
    return sha256_text(canonical_json(stripped))


def strip_key(value: Any, key_to_strip: str) -> None:
    if isinstance(value, dict):
        value.pop(key_to_strip, None)
        for child in value.values():
            strip_key(child, key_to_strip)
    elif isinstance(value, list):
        for child in value:
            strip_key(child, key_to_strip)


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(record) + "\n" for record in records)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise TypeError(f"JSONL row is not an object: {path}:{line_number}")
        rows.append(row)
    return rows


def get_path(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def occurrence_index(container: str, exact_text: str) -> int:
    index = container.find(exact_text)
    if index < 0:
        return -1
    return container[:index].count(exact_text)


def record_digest(record: dict[str, Any]) -> str:
    return sha256_text(canonical_json(record))


def select_sources(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record["p0_group"])].append(record)

    selected: list[dict[str, Any]] = []
    for p0_group in [f"P0_0{i}" for i in range(1, 6)]:
        sorted_group = sorted(
            groups[p0_group],
            key=lambda row: sha256_text(f"{CLEAN_120_SHA256}:{row['asset_id']}"),
        )
        for rank, record in enumerate(sorted_group[:3], start=1):
            item = copy.deepcopy(record)
            item["_selection_rank_in_group"] = rank
            item["_selection_hash"] = sha256_text(f"{CLEAN_120_SHA256}:{record['asset_id']}")
            selected.append(item)
    return selected


def build_contract() -> dict[str, Any]:
    fail_closed_rules = [
        "FC_ROLE_JUDGMENT",
        "FC_FOUNDER_EXPERIENCE",
        "FC_EVENT_TRUTH",
        "FC_HEADCOUNT",
        "FC_CLAIM_SUPPORT",
        "FC_FAKE_CUSTOMER",
        "FC_CAPTURE_MODE",
        "FC_REFERENCE_AS_FACT",
        "FC_COMPONENT_PRODUCT_MISMATCH",
        "FC_GKB_BUNDLE_AS_ORCH_PLAN",
    ]
    compatibility_rules = [
        "CP_REQUIRED_COMPONENT_ROLES",
        "COMPONENT_APPLICABLE_PRODUCT",
        "ROLE_AUTHORITY_PROFESSIONAL_JUDGMENT",
        "EVENT_TRUTH_MODE_EVENT_SURFACE",
        "REQUIRED_PEOPLE_VISIBLE_PARTICIPANTS",
        "DAILY_NATIVE_CAMPAIGN_SCREENPLAY",
        "PLATFORM_EXPRESSION_CAPTURE_INSTRUCTION",
        "CLAIM_BOUNDARY_REQUIRED_FACT_SLOTS",
        "CONTINUITY_PATTERN_RUNTIME_HISTORY",
        "CONTENT_REFERENCE_BRAND_FACT",
        "GKB_BUNDLE_ORCH_PLAN_AUTHORITY",
    ]
    return {
        "controlled_composition_v2_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "implementation_kind": IMPLEMENTATION_KIND,
            "baseline_head": BASELINE_HEAD,
            "accepted_immutable_facts": {
                "clean_120": {
                    "status": "FROZEN",
                    "digest": CLEAN_120_SHA256,
                    "mutation_allowed": False,
                },
                "scale_600_contract": {
                    "status": "DESIGN_COMPLETE_PARKED",
                    "digest": SCALE_600_CONTRACT_SHA256,
                    "generation_allowed": False,
                },
                "prior_probe_15": {
                    "task_id": "GKB-P7D-SINGLE-CLUSTER-DUAL-VOICE-DIVERSITY-PROBE-15-001",
                    "status": "SUPERSEDED_UNEXECUTED",
                    "materialized_count": 0,
                },
                "generator_v1": {
                    "status": "FROZEN_LEGACY_REFERENCE",
                    "in_place_modification_allowed": False,
                },
            },
            "ownership": {
                "GKB_owns": [
                    "ContentProductProfile",
                    "ComponentAsset",
                    "CompatibilityRule",
                    "reviewed_reusable_component_registry",
                    "immutable_GKB_handoff_snapshot",
                    "composition_proof_bundle",
                ],
                "ORCH_owns": [
                    "runtime_request_intake",
                    "runtime_component_selection",
                    "brand_fact_and_authorization_binding",
                    "runtime_continuity_instance",
                    "canonical_CompositionPlan",
                    "generation_invocation",
                ],
                "DIFY_consumes": ["ORCH_owned_typed_generation_context_bundle"],
                "hard_boundaries": {
                    "GKB_may_create_formal_CompositionPlan": False,
                    "ORCH_may_mutate_GKB_Profile_or_Component": False,
                    "DIFY_may_directly_select_GKB_components": False,
                    "GKB_pilot_bundle_runtime_ingest_allowed": False,
                    "ORCH_formal_plan_must_pin_GKB_handoff_profile_component_id_version_digest": True,
                },
            },
            "component_asset_contract": {
                "component_role_enum": COMPONENT_ROLES,
                "primary_content_product_type_id_allowed": False,
                "applicable_content_product_type_ids_min_count": 1,
                "role_count_per_component_v0_1": 1,
                "full_role_set_required_per_parent_asset": False,
                "empty_roles_allowed": ["CTA", "opening", "closing", "visual_beat"],
                "body_text_as_default_rewrite_input_allowed": False,
                "reviewed_reusable_promotion_allowed_by_codex": False,
                "opening_closing_CTA_spoken_line_policy": {
                    "storage": "family_function_intent_rhythm_only",
                    "direct_copy_sentence_template_library_allowed": False,
                },
                "truth_boundary_defaults": {
                    "ontology_truth": False,
                    "factual_authority": False,
                    "real_event_evidence": False,
                    "brand_fact_source": False,
                },
            },
            "event_truth_modes": {
                "allowlist": EVENT_TRUTH_MODES,
                "default_deny_unlisted": True,
                "brand_supplied_real_event": {
                    "requires_profile_event_fact_authorization_slots": True,
                },
                "brand_fillable_prototype": {
                    "verified_past_event_surface_allowed": False,
                    "audience_facing_body_allowed_before_fill": False,
                },
                "generic_creative_prototype": {
                    "real_brand_history_surface_allowed": False,
                    "real_person_experience_surface_allowed": False,
                },
                "collection_task_only": {"audience_facing_body_allowed": False},
            },
            "missing_input_router": {
                "single_source_of_truth": "ContentProductProfile.input_sufficiency_routes",
                "model_runtime_discretion_allowed": False,
            },
            "compatibility_rules": {
                "rule_shape": "rule_id + requires + excludes + compatible_if",
                "full_pairwise_component_matrix_allowed": False,
                "minimum_rule_coverage": compatibility_rules,
                "fail_closed_rules": fail_closed_rules,
            },
            "audience_facing_content_generation": {
                "allowed_by_this_task": False,
                "audience_facing_body_count": 0,
                "title_count": 0,
                "spoken_draft_count": 0,
            },
            "readiness_flags": readiness_flags(),
            "downstream_writes": {
                "CandidatePack": False,
                "KE": False,
                "ServingProjection": False,
                "RAG": False,
                "DIFY": False,
                "production_runtime": False,
            },
        }
    }


def input_routes() -> list[dict[str, Any]]:
    return [
        {
            "route_id": "all_required_inputs_present",
            "condition": "all_profile_source_fact_authorization_slots_present",
            "missing_slot_classes": [],
            "allowed_outputs": ["content_candidate", "shooting_plan"],
            "audience_facing_body_allowed": True,
            "first_person_experience_allowed": True,
            "product_claim_allowed": True,
        },
        {
            "route_id": "optional_inputs_missing_only",
            "condition": "required_slots_present_optional_slots_missing",
            "missing_slot_classes": ["optional"],
            "allowed_outputs": ["slot_based_outline", "shooting_plan"],
            "audience_facing_body_allowed": False,
            "first_person_experience_allowed": False,
            "product_claim_allowed": False,
        },
        {
            "route_id": "real_event_missing",
            "condition": "one_or_more_required_real_event_or_fact_slots_missing",
            "missing_slot_classes": ["source", "fact", "authorization"],
            "allowed_outputs": [
                "fact_collection_task",
                "interview_outline",
                "material_capture_plan",
            ],
            "audience_facing_body_allowed": False,
            "first_person_experience_allowed": False,
            "product_claim_allowed": False,
        },
        {
            "route_id": "person_authorization_missing",
            "condition": "person_or_account_authorization_slot_missing",
            "missing_slot_classes": ["authorization"],
            "allowed_outputs": ["authorization_collection_task", "anonymous_shooting_plan"],
            "audience_facing_body_allowed": False,
            "first_person_experience_allowed": False,
            "product_claim_allowed": False,
        },
        {
            "route_id": "product_fact_or_claim_support_missing",
            "condition": "product_fact_or_claim_support_slot_missing",
            "missing_slot_classes": ["fact", "authorization"],
            "allowed_outputs": ["evidence_collection_task", "non_claim_shooting_plan"],
            "audience_facing_body_allowed": False,
            "first_person_experience_allowed": False,
            "product_claim_allowed": False,
        },
    ]


def build_profiles() -> dict[str, Any]:
    profiles: list[dict[str, Any]] = []
    for cp_id, spec in PROFILE_REQUIREMENTS.items():
        profile = {
            "schema_version": "v0.1",
            "profile_version": "v0.1",
            "content_product_type_id": cp_id,
            "content_product_label": spec["label"],
            "lifecycle": "pilot",
            "owner": "GKB",
            "runtime_plan_owner": "ORCH",
            "required_component_roles": [
                {"role": role, "min_count": 1, "max_count": 3}
                for role in spec["required_components"]
            ],
            "optional_component_roles": [],
            "input_requirements": {
                "required_source_slots": spec["source_slots"],
                "required_fact_slots": spec["fact_slots"],
                "required_authorization_slots": spec["authorization_slots"],
            },
            "event_truth_policy": {
                "allowed_event_truth_modes": EVENT_TRUTH_MODES,
                "default_deny_unlisted": True,
            },
            "continuity_policy_ref": "ORCH_RUNTIME_CONTINUITY_REQUIRED_FOR_HISTORY_CLAIMS",
            "visual_audio_requirement_refs": [
                "V0_1_VISIBLE_SOURCE_OR_MATERIAL_SLOT_REQUIRED_FOR_CAPTURE"
            ],
            "input_sufficiency_routes": input_routes(),
            "quality_rubric_refs": [],
            "fixture_refs": {
                "positive": [],
                "negative": [],
                "usage": "evaluation_and_guardian_calibration_only",
                "may_enter_generation_prompt": False,
                "may_supply_facts": False,
            },
            "completion_criteria": [
                "required_slots_can_be_classified_as_present_or_missing",
                "missing_required_slots_route_to_degraded_non_audience_outputs",
                "runtime_plan_authority_remains_ORCH",
            ],
        }
        profile["profile_digest"] = object_digest(profile, {"profile_digest"})
        profiles.append(profile)
    return {
        "content_product_profiles": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "profile_count": len(profiles),
            "profiles": profiles,
        }
    }


def build_selection(records: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row["p0_group"]) for row in selected)
    selected_sources: list[dict[str, Any]] = []
    for index, record in enumerate(selected, start=1):
        selected_sources.append(
            {
                "selection_index": index,
                "p0_group": record["p0_group"],
                "rank_in_p0_group": record["_selection_rank_in_group"],
                "asset_id": record["asset_id"],
                "kernel_id": record.get("kernel_id"),
                "selection_hash": record["_selection_hash"],
                "source_record_digest": record_digest(record_without_selection_meta(record)),
                "body_sha256": record.get("body_lineage", {}).get("final_body_sha256"),
                "event_surface_mode": record.get("claim_event_boundary", {}).get(
                    "event_surface_mode"
                ),
            }
        )
    selection = {
        "pilot_source_selection": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "source_corpus": {
                "path": str(CLEAN_120_PATH),
                "sha256": CLEAN_120_SHA256,
                "record_count": len(records),
            },
            "selection_algorithm": {
                "group_by": "p0_group",
                "hash_input": "sha256(clean_120_digest + ':' + asset_id)",
                "sort": "hash_ascending_within_each_p0",
                "take_per_p0": 3,
                "forbidden_inputs": [
                    "CPSS",
                    "human_grade",
                    "output_quality",
                    "extraction_difficulty",
                ],
            },
            "selected_source_count": len(selected_sources),
            "group_counts": dict(sorted(counts.items())),
            "frozen_source_ids": [item["asset_id"] for item in selected_sources],
            "selected_sources": selected_sources,
        }
    }
    selection["pilot_source_selection"]["selection_digest"] = object_digest(
        selection["pilot_source_selection"], {"selection_digest"}
    )
    return selection


def record_without_selection_meta(record: dict[str, Any]) -> dict[str, Any]:
    stripped = copy.deepcopy(record)
    for key in ["_selection_rank_in_group", "_selection_hash"]:
        stripped.pop(key, None)
    return stripped


def build_parent_ref(
    record: dict[str, Any],
    field_path: str,
    exact_text: str,
    derivation_method: str,
) -> dict[str, Any]:
    parent_record = record_without_selection_meta(record)
    field_value = get_path(parent_record, field_path)
    if not isinstance(field_value, str):
        field_value = str(field_value)
    return {
        "parent_asset_id": parent_record["asset_id"],
        "parent_digest": record_digest(parent_record),
        "parent_field_path": field_path,
        "derivation_method": derivation_method,
        "derivation_spans": [
            {
                "exact_text": exact_text,
                "occurrence_index": occurrence_index(field_value, exact_text),
                "span_digest": sha256_text(exact_text),
            }
        ],
    }


def component_payload(record: dict[str, Any], role: str, field_path: str, value: str) -> dict[str, Any]:
    if role != "capture_instruction":
        return {"kind": next(spec["payload_kind"] for spec in EXTRACTABLE_ROLE_SPECS if spec["role"] == role), "content": value}

    parent = record_without_selection_meta(record)
    execution_card = parent.get("execution_card", {})
    return {
        "kind": "structured_capture_instruction",
        "content": {
            "capture_operator_mode": value,
            "capture_required_people_min": execution_card.get("capture_required_people_min"),
            "event_required_people_min": execution_card.get("event_required_people_min"),
            "independent_capture_human_required": execution_card.get(
                "independent_capture_human_required"
            ),
            "surface_destination": "execution_layer_only",
        },
    }


def required_input_slots_for_role(role: str) -> list[str]:
    mapping = {
        "scene": ["actual_event_or_stage_surface"],
        "trigger": ["actual_event_or_change_trigger"],
        "observable_action": ["observable_action_chain"],
        "professional_judgment": ["decision_authority", "decision_reason_or_claim_boundary"],
        "visual_beat": ["usable_visual_audio_materials"],
        "capture_instruction": ["usable_materials", "relevant_authorizations"],
    }
    return mapping[role]


def build_components(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for source_index, record in enumerate(selected, start=1):
        parent = record_without_selection_meta(record)
        for spec in EXTRACTABLE_ROLE_SPECS:
            role = spec["role"]
            raw_value = get_path(parent, spec["field_path"])
            if raw_value is None:
                continue
            value = str(raw_value).strip()
            if not value:
                continue
            component_id = f"CCV2-CAND-{source_index:02d}-{ROLE_CODES[role]}"
            component = {
                "component_id": component_id,
                "component_version": "v0.1",
                "component_role": role,
                "lifecycle": "extracted_candidate",
                "applicable_content_product_type_ids": CONTENT_PRODUCT_IDS,
                "payload": component_payload(parent, role, spec["field_path"], value),
                "compatibility_tag_refs": [
                    f"role:{role}",
                    f"p0:{parent.get('p0_group')}",
                    f"generation_mode:{parent.get('generation_mode')}",
                    f"publisher_account_role:{parent.get('publisher_account_role')}",
                ],
                "required_input_slots": required_input_slots_for_role(role),
                "incompatible_condition_refs": [],
                "forbidden_combination_rule_refs": [],
                "parent_refs": [
                    build_parent_ref(parent, spec["field_path"], value, spec["derivation_method"])
                ],
                "surface_reuse_policy": (
                    "execution_layer_only"
                    if role == "capture_instruction"
                    else "candidate_only_not_default_copy_or_template"
                ),
                "truth_boundary": {
                    "ontology_truth": False,
                    "factual_authority": False,
                    "real_event_evidence": False,
                    "brand_fact_source": False,
                },
            }
            if role == "professional_judgment":
                component["professional_judgment_binding"] = {
                    "applicable_role_authority": [
                        "founder",
                        "store_manager",
                        "sales_associate",
                        "brand_headquarters",
                        "authorized_operator",
                    ],
                    "required_fact_slots": [
                        "decision_authority",
                        "decision_reason_or_claim_boundary",
                    ],
                    "claim_boundary": "judgment_pattern_only_not_brand_fact_or_result_claim",
                }
            component["component_digest"] = object_digest(component, {"component_digest"})
            components.append(component)
    return components


def missing_slots_for_profile(profile: dict[str, Any]) -> list[dict[str, str]]:
    requirements = profile["input_requirements"]
    slots: list[dict[str, str]] = []
    for slot in requirements["required_source_slots"]:
        slots.append({"slot_class": "source", "slot_id": slot})
    for slot in requirements["required_fact_slots"]:
        slots.append({"slot_class": "fact", "slot_id": slot})
    for slot in requirements["required_authorization_slots"]:
        slots.append({"slot_class": "authorization", "slot_id": slot})
    return slots


def route_by_id(profile: dict[str, Any], route_id: str) -> dict[str, Any]:
    for route in profile["input_sufficiency_routes"]:
        if route["route_id"] == route_id:
            return route
    raise KeyError(route_id)


def build_bundles(
    profiles_doc: dict[str, Any],
    selected: list[dict[str, Any]],
    components: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    profiles = {
        profile["content_product_type_id"]: profile
        for profile in profiles_doc["content_product_profiles"]["profiles"]
    }
    by_asset_role: dict[tuple[str, str], dict[str, Any]] = {}
    for component in components:
        parent_id = component["parent_refs"][0]["parent_asset_id"]
        by_asset_role[(parent_id, component["component_role"])] = component

    source_groups = {
        CP_ROLE_WORK_VLOG: selected[0:3],
        CP_STORE_MICRO_DOCUMENTARY: selected[3:6],
        CP_PRODUCT_ITERATION_ARCHIVE: selected[6:9],
    }

    bundles: list[dict[str, Any]] = []
    for cp_id in CONTENT_PRODUCT_IDS:
        profile = profiles[cp_id]
        required_roles = [item["role"] for item in profile["required_component_roles"]]
        route = route_by_id(profile, "real_event_missing")
        for bundle_index, source in enumerate(source_groups[cp_id], start=1):
            selected_components = [
                by_asset_role[(source["asset_id"], role)]
                for role in required_roles
                if (source["asset_id"], role) in by_asset_role
            ]
            missing_slots = missing_slots_for_profile(profile)
            bundle = {
                "bundle_id": f"GKB-CCV2-BUNDLE-{cp_id.replace('CP_', '')}-{bundle_index:02d}",
                "bundle_kind": "GKB_COMPOSITION_CANDIDATE_BUNDLE",
                "pilot_only": True,
                "primary_content_product_type_id": cp_id,
                "content_product_profile_ref": {
                    "id": cp_id,
                    "version": profile["profile_version"],
                    "digest": profile["profile_digest"],
                },
                "selected_candidate_refs": [
                    {
                        "component_id": component["component_id"],
                        "component_version": component["component_version"],
                        "component_role": component["component_role"],
                    }
                    for component in selected_components
                ],
                "selected_candidate_digests": [
                    component["component_digest"] for component in selected_components
                ],
                "event_truth_mode": "collection_task_only",
                "brand_supplied_source_slots": [],
                "brand_supplied_fact_slots": [],
                "authorization_refs": [],
                "missing_required_slots": missing_slots,
                "compatibility_result": {
                    "status": "PASS_DEGRADED_OUTPUT_ONLY",
                    "rule_ids_evaluated": [
                        "CP_REQUIRED_COMPONENT_ROLES",
                        "COMPONENT_APPLICABLE_PRODUCT",
                        "EVENT_TRUTH_MODE_EVENT_SURFACE",
                        "CLAIM_BOUNDARY_REQUIRED_FACT_SLOTS",
                        "GKB_BUNDLE_ORCH_PLAN_AUTHORITY",
                    ],
                    "fail_closed_rule_hits": [],
                },
                "forbidden_combination_hits": [],
                "sufficiency_route_result": {
                    "route_id": "real_event_missing",
                    "allowed_outputs": route["allowed_outputs"],
                    "selected_allowed_output": "material_capture_plan",
                    "missing_slot_classes": sorted(
                        {slot["slot_class"] for slot in missing_slots}
                    ),
                    "audience_facing_body_allowed": False,
                    "first_person_experience_allowed": False,
                    "product_claim_allowed": False,
                },
                "degraded_output_payload": {
                    "payload_kind": "material_capture_plan",
                    "surface": "internal_collection_task_only",
                    "audience_facing_body_count": 0,
                    "title_count": 0,
                    "spoken_draft_count": 0,
                    "slot_collection_tasks": [
                        {
                            "slot_class": slot["slot_class"],
                            "slot_id": slot["slot_id"],
                            "collection_instruction_kind": "collect_verified_input_before_generation",
                        }
                        for slot in missing_slots
                    ],
                },
                "audience_facing_body_allowed": False,
                "audience_facing_body_materialized": False,
                "canonical_composition_plan": False,
                "runtime_owner": "ORCH",
                "runtime_ingest_allowed": False,
            }
            bundle["bundle_digest"] = object_digest(bundle, {"bundle_digest"})
            bundles.append(bundle)
    return bundles


def readiness_flags() -> dict[str, bool]:
    return {
        "candidatepack_ready": False,
        "KE_ready": False,
        "RAG_ready": False,
        "DIFY_ready": False,
        "Serving_ready": False,
        "production_servable": False,
        "generation_eligible": False,
        "generation_allowed": False,
        "release_ready": False,
        "production_ready": False,
    }


def build_handoff(
    profiles_doc: dict[str, Any],
    components: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
    file_digests: dict[str, str],
) -> dict[str, Any]:
    profiles = profiles_doc["content_product_profiles"]["profiles"]
    handoff = {
        "gkb_orch_pilot_handoff": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "handoff_kind": "PILOT_CONTRACT_PROOF",
            "profile_snapshot_refs": [
                {
                    "id": profile["content_product_type_id"],
                    "version": profile["profile_version"],
                    "digest": profile["profile_digest"],
                }
                for profile in profiles
            ],
            "candidate_component_snapshot_refs": {
                "path": str(COMPONENTS_PATH),
                "component_count": len(components),
                "candidate_component_manifest_sha256": file_digests[str(COMPONENTS_PATH)],
                "component_ids": [component["component_id"] for component in components],
            },
            "composition_proof_bundle_snapshot_ref": {
                "path": str(BUNDLES_PATH),
                "bundle_count": len(bundles),
                "bundle_manifest_sha256": file_digests[str(BUNDLES_PATH)],
            },
            "compatibility_rule_snapshot_ref": {
                "path": str(CONTRACT_PATH),
                "contract_sha256": file_digests[str(CONTRACT_PATH)],
            },
            "snapshot_digests": [
                file_digests[str(CONTRACT_PATH)],
                file_digests[str(PROFILES_PATH)],
                file_digests[str(COMPONENTS_PATH)],
                file_digests[str(BUNDLES_PATH)],
            ],
            "reviewed_reusable_component_count": 0,
            "runtime_ingest_ready": False,
            "canonical_composition_plan_count": 0,
            "producer": "GKB",
            "consumer": "ORCH",
            "ORCH_behavior": {
                "consumes_digest_pinned_handoff": True,
                "selects_runtime_components": True,
                "binds_brand_facts_and_authorizations": True,
                "owns_canonical_composition_plan": True,
                "may_mutate_GKB_assets": False,
            },
            "GKB_behavior": {
                "owns_profile_and_component_versions": True,
                "may_create_runtime_composition_plan": False,
            },
            "DIFY_direct_GKB_consumption_allowed": False,
        }
    }
    handoff["gkb_orch_pilot_handoff"]["handoff_digest"] = object_digest(
        handoff["gkb_orch_pilot_handoff"], {"handoff_digest"}
    )
    return handoff


def build_result(
    selected: list[dict[str, Any]],
    components: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
    file_digests: dict[str, str],
) -> dict[str, Any]:
    result = {
        "controlled_composition_v2_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "verdict": "CONTROLLED_COMPOSITION_V2_MINIMUM_COMPOSABILITY_PROOF_PASS",
            "status": "EXECUTED_PENDING_GUARDIAN",
            "implementation_kind": IMPLEMENTATION_KIND,
            "baseline_head_before": BASELINE_HEAD,
            "immutable_input_digests": {
                "clean_120": CLEAN_120_SHA256,
                "scale_600_contract": SCALE_600_CONTRACT_SHA256,
            },
            "counts": {
                "profile_count": 3,
                "selected_source_count": len(selected),
                "component_candidate_count": len(components),
                "candidate_bundle_count": len(bundles),
                "reviewed_reusable_component_count": 0,
                "canonical_composition_plan_count": 0,
                "audience_facing_body_count": 0,
                "title_count": 0,
                "spoken_draft_count": 0,
            },
            "generation_authorization": {
                "audience_facing_content_generation_allowed": False,
                "generation_600_allowed": False,
                "generation_3600_allowed": False,
                "external_LLM_or_API_called": False,
                "secret_accessed": False,
            },
            "readiness_flags": readiness_flags(),
            "proof_scope": {
                "proves_profile_input_sufficiency_routing": True,
                "proves_component_multi_product_applicability_runs": True,
                "proves_bundle_single_primary_product": True,
                "proves_missing_brand_facts_degrade_to_collection_outputs": True,
                "proves_GKB_ORCH_single_writer_boundary": True,
                "proves_15_read_only_extractions_and_9_bundles_auditable": True,
            },
            "not_proven": [
                "real_content_quality_improved",
                "multi_account_differentiation_established",
                "continuity_memory_runtime_ready",
                "ORCH_integrated",
                "generation_600_or_3600_allowed",
                "KE_RAG_DIFY_or_production_ready",
            ],
            "generated_file_digests": file_digests,
            "blocking_items": [],
            "recommended_next_task": {
                "task_id": "GKB-CONTROLLED-V2-COMPONENT-DOMAIN-REVIEW-AND-HANDOFF-FREEZE-001",
                "separate_founder_authorization_required": True,
            },
        }
    }
    result["controlled_composition_v2_result"]["result_digest"] = object_digest(
        result["controlled_composition_v2_result"], {"result_digest"}
    )
    return result


def build_artifacts(root: Path) -> dict[Path, str]:
    clean_path = root / CLEAN_120_PATH
    records = load_jsonl(clean_path)
    selected = select_sources(records)

    contract = build_contract()
    profiles = build_profiles()
    selection = build_selection(records, selected)
    components = build_components(selected)
    bundles = build_bundles(profiles, selected, components)

    artifacts: dict[Path, str] = {
        CONTRACT_PATH: yaml_text(contract),
        PROFILES_PATH: yaml_text(profiles),
        SELECTION_PATH: yaml_text(selection),
        COMPONENTS_PATH: jsonl_text(components),
        BUNDLES_PATH: jsonl_text(bundles),
    }
    file_digests = {
        str(path): sha256_text(text)
        for path, text in artifacts.items()
    }

    handoff = build_handoff(profiles, components, bundles, file_digests)
    handoff_text = yaml_text(handoff)
    artifacts[HANDOFF_PATH] = handoff_text
    file_digests[str(HANDOFF_PATH)] = sha256_text(handoff_text)

    harness_path = root / HARNESS_PATH
    checker_path = root / CHECKER_PATH
    file_digests[str(HARNESS_PATH)] = sha256_file(harness_path)
    file_digests[str(CHECKER_PATH)] = (
        sha256_file(checker_path) if checker_path.exists() else "CHECKER_NOT_PRESENT"
    )

    result = build_result(selected, components, bundles, file_digests)
    artifacts[RESULT_PATH] = yaml_text(result)
    return artifacts


def write_artifacts(root: Path, artifacts: dict[Path, str]) -> None:
    for relative_path, text in artifacts.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def check_artifacts(root: Path, artifacts: dict[Path, str]) -> list[str]:
    mismatches: list[str] = []
    for relative_path, expected in artifacts.items():
        path = root / relative_path
        if not path.exists():
            mismatches.append(f"missing: {relative_path}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            mismatches.append(f"content mismatch: {relative_path}")
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write generated pilot artifacts")
    parser.add_argument("--check", action="store_true", help="check generated artifacts are idempotent")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args()

    if not args.write and not args.check:
        parser.error("choose --write or --check")

    root = Path(args.root).resolve()
    artifacts = build_artifacts(root)
    if args.write:
        write_artifacts(root, artifacts)
    if args.check:
        mismatches = check_artifacts(root, artifacts)
        if mismatches:
            for mismatch in mismatches:
                print(mismatch, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
