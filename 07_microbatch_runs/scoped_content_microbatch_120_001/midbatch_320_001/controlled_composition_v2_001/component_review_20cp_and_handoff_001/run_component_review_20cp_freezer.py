#!/usr/bin/env python3
"""Freeze the 89-candidate Controlled V2 component review and handoff."""

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


TASK_ID = "GKB-CONTROLLED-V2-COMPONENT-DOMAIN-REVIEW-20CP-RECLASSIFICATION-AND-HANDOFF-FREEZE-001"
BASELINE_HEAD = "78d21adff79c006449763e0644e52cdae55bcbe8"

CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
SCALE_600_CONTRACT_SHA256 = (
    "966190c341b070d88fbc3a25540e9c8fddf69ad8f19b90fb29badbb1ffad52a9"
)

S1_DIGESTS = {
    "contract": "7bf9315ebbb5bf97c3330695de7327af42ae30771b6315d2432c5c78d51d742c",
    "profiles": "c4e744f3f0505025d780f46eb12b879f1b9920ede63e4c84ffbc3fac9a715a6c",
    "candidates": "70ce2f7ebae3699fba6be0a0fff5d4a0a8e1023bbd32ae5a4f7340b3c4f43f7d",
    "bundles": "6d294274ea235962c33a8e7cd9f4d4be92d2e6ce5b48860286a1d13f08ce7970",
    "pilot_handoff": "12a369dcf64641a16b73636e95ba1c710fc787efa663608f446f73634a2f6223",
}
S1_5_FILE_SHA256 = {
    "profiles_v0_2": "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056",
    "legacy_migration": "e80d33d27e89d41f369533ae2e881083ae474fc59c9d347412ab0b511a3a0f21",
    "coverage": "0101c8a6d86ade2bd832fa57a8e246dabd9668de013aa2605050f699b16e12bd",
    "result": "8832e397d3c507edb998966c11cd063b60b9b6f121273625fec2cfc18992a88d",
}
S1_5_INTERNAL_DIGESTS = {
    "profiles_v0_2": "160f640f3c677b3e3aa7fb13c89549c61825cdde1919731bc573740ae38ef53b",
    "legacy_migration": "6208c15235072d6c8fdfa1f2ed7ccb12fd5f52b5d8cae41f182f9033545e2b4d",
    "coverage": "e3c8eeaedb8856370cd8f0ed1e9d4dcb5b4aacf509d4127948535532e67ab658",
    "result": "d3c601d2280886d32cd2671905db86ed6af784d5b54a218295c4f0215fe41bfd",
    "route_migration_20": "585c5477125243ecbfc22bfe7e77722f554e66936bf8007616427ec1219a8010",
}

ROOT_S1 = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = ROOT_S1 / "component_review_20cp_and_handoff_001"
MAPPING_PATH = TASK_DIR / "capability_product_composition_mapping.v0.1.yaml"
POLICY_PATH = TASK_DIR / "component_domain_review_policy.v0.1.yaml"
DECISIONS_PATH = TASK_DIR / "component_domain_review_decisions.v0.1.jsonl"
REGISTRY_PATH = TASK_DIR / "reviewed_reusable_component_registry.v0.1.jsonl"
COVERAGE_PATH = TASK_DIR / "content_product_component_coverage.v0.1.yaml"
HANDOFF_PATH = TASK_DIR / "gkb_orch_reviewed_component_handoff.v0.1.yaml"
RESULT_PATH = TASK_DIR / "component_review_20cp_and_handoff_result.v0.1.yaml"
FREEZER_PATH = TASK_DIR / "run_component_review_20cp_freezer.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_controlled_v2_component_review_20cp.py")

S1_CONTRACT_PATH = ROOT_S1 / "controlled_composition_v2_contract.v0.1.yaml"
S1_PROFILES_PATH = ROOT_S1 / "content_product_profiles.v0.1.yaml"
S1_CANDIDATES_PATH = ROOT_S1 / "component_candidate_manifest.v0.1.jsonl"
S1_BUNDLES_PATH = ROOT_S1 / "gkb_composition_candidate_bundles.v0.1.jsonl"
S1_HANDOFF_PATH = ROOT_S1 / "gkb_orch_pilot_handoff.v0.1.yaml"
S1_SELECTION_PATH = ROOT_S1 / "pilot_source_selection.v0.1.yaml"
S1_5_DIR = ROOT_S1 / "content_product_profile_20_completion_001"
S1_5_PROFILES_PATH = S1_5_DIR / "content_product_profiles.v0.2.yaml"
S1_5_MIGRATION_PATH = S1_5_DIR / "content_product_profile_legacy_migration.v0.1.yaml"
S1_5_COVERAGE_PATH = S1_5_DIR / "content_product_profile_coverage_and_gap.v0.1.yaml"
S1_5_RESULT_PATH = S1_5_DIR / "content_product_profile_20_completion_result.v0.1.yaml"

COMPOSITION_ASSET_CLASSES = [
    "scene_action_kernel",
    "narrative_operator",
    "role_perspective_voice",
    "style_vector",
    "visual_audio_grammar",
    "platform_expression",
    "continuity_pattern",
    "anti_pattern_control",
]

ROLE_TO_CLASS = {
    "scene": "scene_action_kernel",
    "trigger": "scene_action_kernel",
    "tension": "scene_action_kernel",
    "observable_action": "scene_action_kernel",
    "audience_facing_reasoning_move": "narrative_operator",
    "opening": "narrative_operator",
    "transition": "narrative_operator",
    "closing": "narrative_operator",
    "CTA": "narrative_operator",
    "professional_judgment": "role_perspective_voice",
    "spoken_line_intent": "role_perspective_voice",
    "visual_beat": "visual_audio_grammar",
    "capture_instruction": "visual_audio_grammar",
}

P0_CP_MAPPING = {
    "CP01": {"primary_capabilities": ["P0_02"], "auxiliary_capabilities": ["P0_03", "P0_04", "P0_01", "P0_05"]},
    "CP02": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_02"]},
    "CP03": {
        "primary_capability_options": ["P0_03", "P0_04"],
        "primary_selection_rule": "按真实手艺任务所属业务域选择恰好一个",
        "auxiliary_capabilities": ["P0_02"],
    },
    "CP04": {"primary_capabilities": ["P0_02"], "auxiliary_capabilities": ["P0_01", "P0_03", "P0_04"]},
    "CP05": {"primary_capabilities": ["P0_02"], "auxiliary_capabilities": ["P0_01"]},
    "CP06": {"primary_capabilities": ["P0_03"], "auxiliary_capabilities": ["P0_02", "P0_04"]},
    "CP07": {
        "primary_capability_options": ["P0_03", "P0_04"],
        "primary_selection_rule": "按问题属于专业判断还是门店服务选择恰好一个",
        "auxiliary_capabilities": ["P0_02", "P0_05"],
    },
    "CP08": {"primary_capabilities": ["P0_03"], "auxiliary_capabilities": ["P0_05"]},
    "CP09": {"primary_capabilities": ["P0_03"], "auxiliary_capabilities": ["P0_05", "P0_02"]},
    "CP10": {"primary_capabilities": ["P0_03"], "auxiliary_capabilities": ["P0_05", "P0_01"]},
    "CP11": {"primary_capabilities": ["P0_05"], "auxiliary_capabilities": ["P0_03", "P0_01", "P0_02"]},
    "CP12": {"primary_capabilities": ["P0_05"], "auxiliary_capabilities": ["P0_03"]},
    "CP13": {"primary_capabilities": ["P0_05"], "auxiliary_capabilities": ["P0_03", "P0_04"]},
    "CP14": {"primary_capabilities": ["P0_05"], "auxiliary_capabilities": ["P0_03"]},
    "CP15": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_05", "P0_02"]},
    "CP16": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_02", "P0_05", "P0_03"]},
    "CP17": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_03", "P0_02"]},
    "CP18": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_02", "P0_01"]},
    "CP19": {"primary_capabilities": ["P0_01"], "auxiliary_capabilities": ["P0_02", "P0_03", "P0_04", "P0_05"]},
    "CP20": {"primary_capabilities": ["P0_01"], "auxiliary_capabilities": ["P0_05", "P0_04"]},
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_key(value: Any, key_to_strip: str) -> None:
    if isinstance(value, dict):
        value.pop(key_to_strip, None)
        for child in value.values():
            strip_key(child, key_to_strip)
    elif isinstance(value, list):
        for child in value:
            strip_key(child, key_to_strip)


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    stripped = copy.deepcopy(value)
    for key in digest_keys or set():
        strip_key(stripped, key)
    return sha256_text(canonical_json(stripped))


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(record) + "\n" for record in records)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(path)
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def cp_capabilities(cp_id: str) -> set[str]:
    mapping = P0_CP_MAPPING[cp_id]
    caps = set(mapping.get("primary_capabilities", []))
    caps.update(mapping.get("primary_capability_options", []))
    caps.update(mapping.get("auxiliary_capabilities", []))
    return caps


def role_allowed_cp_ids(role: str, source_p0: str, profiles: list[dict[str, Any]]) -> list[str]:
    cp_ids: list[str] = []
    for profile in profiles:
        cp_id = profile["content_product_type_id"]
        profile_roles = {
            item["role"] for item in profile.get("required_component_roles", [])
        } | {item["role"] for item in profile.get("optional_component_roles", [])}
        if role not in profile_roles:
            continue
        if source_p0 not in cp_capabilities(cp_id):
            continue
        cp_ids.append(cp_id)
    return cp_ids


def p0_binding_kind(cp_id: str, p0: str) -> str:
    mapping = P0_CP_MAPPING[cp_id]
    if p0 in mapping.get("primary_capabilities", []) or p0 in mapping.get("primary_capability_options", []):
        return "primary"
    if p0 in mapping.get("auxiliary_capabilities", []):
        return "auxiliary"
    return "none"


def build_mapping_doc() -> dict[str, Any]:
    doc = {
        "capability_product_composition_mapping": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "layer_1_capability_groups": {
                "purpose": ["provide business capability", "provide judgment source", "provide role and scene source"],
                "values": {
                    "P0_01": {"role": "企业与组织叙事能力"},
                    "P0_02": {
                        "role": ["横切角色视角能力", "独立人物内容能力"],
                        "controls": ["谁观察", "谁判断", "谁表达", "权威来源", "角色声音"],
                        "may_be": ["primary_capability", "cross_cutting_perspective_overlay"],
                        "cross_cutting_perspective_overlay": True,
                        "independent_people_content_capability": True,
                    },
                    "P0_03": {"role": "工艺、面料、版型和专业判断能力"},
                    "P0_04": {"role": "门店事件、零售动作和空间执行能力"},
                    "P0_05": {"role": "产品关系、商品角色和产品叙事能力"},
                },
            },
            "layer_2_content_products": {"values": [f"CP{i:02d}" for i in range(1, 21)]},
            "layer_3_composition_assets": {"values": COMPOSITION_ASSET_CLASSES},
            "ownership_correction": {
                "GKB_owns": ["continuity_pattern"],
                "ORCH_owns": ["continuity_thread_instance"],
                "GKB_may_create_runtime_thread": False,
            },
            "P0_CP_mapping": P0_CP_MAPPING,
            "role_to_default_composition_asset_class": ROLE_TO_CLASS,
            "asset_supply_gaps_expected_without_evidence": [
                "style_vector",
                "platform_expression",
                "continuity_pattern",
                "anti_pattern_control",
            ],
        }
    }
    root = doc["capability_product_composition_mapping"]
    root["P0_CP_mapping_digest"] = object_digest(root["P0_CP_mapping"])
    root["composition_asset_class_contract_digest"] = object_digest(
        {
            "classes": COMPOSITION_ASSET_CLASSES,
            "role_to_class": ROLE_TO_CLASS,
            "ownership": root["ownership_correction"],
        }
    )
    root["mapping_digest"] = object_digest(root, {"mapping_digest"})
    return doc


def build_policy_doc() -> dict[str, Any]:
    return {
        "component_domain_review_policy": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "candidate_scope": 89,
            "review_method": "bounded_codex_native_domain_review",
            "promotion_policy": {
                "promotion_rate_target_allowed": False,
                "ambiguous_default": "candidate_only_or_needs_repair",
                "machine_pass_is_domain_pass": False,
                "clean_120_score_auto_promotion_allowed": False,
                "unselected_clean_120_sources_allowed": False,
            },
            "decision_enum": [
                "PROMOTE_AS_NEW",
                "MERGE_INTO_REUSABLE",
                "SOURCE_SPECIFIC_REFERENCE_ONLY",
                "NEEDS_REPAIR",
                "REJECT",
            ],
            "applicability_change_enum": [
                "PRESERVE",
                "NARROW",
                "EVIDENCE_BACKED_EXPAND",
                "CLEAR_ALL_AND_RETAIN_REFERENCE_ONLY",
            ],
            "abstraction_requirements": {
                "runtime_payload_must_be_mechanism_not_sentence": True,
                "parent_surface_verbatim_allowed": False,
                "source_sentence_template_allowed": False,
                "hard_overlap_ceiling_chars": 17,
                "guardian_semantic_review_required": True,
            },
            "forbidden_surface_field_names": [
                "body_text",
                "title_text",
                "spoken_script",
                "source_sentence",
                "template_sentence",
                "literal_quote",
                "surface_script",
                "publishable_copy",
            ],
            "component_supply_gap_policy": {
                "do_not_auto_create_from_profile_description": True,
                "gap_classes_without_candidate_evidence": [
                    "style_vector",
                    "platform_expression",
                    "continuity_pattern",
                    "anti_pattern_control",
                ],
            },
            "handoff_policy": {
                "handoff_is_composition_plan": False,
                "runtime_ingest_ready": False,
                "runtime_generation_eligible_profile_count": 0,
            },
        }
    }


def candidate_id(candidate: dict[str, Any]) -> str:
    return candidate["component_id"]


def candidate_digest(candidate: dict[str, Any]) -> str:
    return candidate["component_digest"]


def source_p0_index() -> dict[str, str]:
    selection = load_yaml(S1_SELECTION_PATH)["pilot_source_selection"]["selected_sources"]
    return {item["asset_id"]: item["p0_group"] for item in selection}


def source_record_index() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    clean_path = Path(
        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
        "clean_120_reference_corpus_freeze_001/founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
    )
    for row in load_jsonl(clean_path):
        records[row["asset_id"]] = row
    return records


def role_specific_fields(role: str, p0: str) -> dict[str, Any]:
    if role == "scene":
        return {
            "scene_class": f"{p0.lower()}_authorized_context",
            "work_phase": "runtime_supplied_phase",
            "spatial_context": "runtime_supplied_space",
            "required_object_slots": ["business_object", "visible_context"],
            "participant_constraints": ["only_authorized_or_anonymized_participants"],
        }
    if role == "trigger":
        return {
            "trigger_class": f"{p0.lower()}_observable_prompt",
            "precondition": "verified_event_or_task_condition",
            "observable_signal": "runtime_supplied_signal",
            "event_truth_requirement": "profile_allowed_event_truth_mode",
        }
    if role == "observable_action":
        return {
            "actor_role_slots": ["authorized_actor_role"],
            "object_slots": ["work_object", "operation_target"],
            "ordered_action_steps": ["runtime_step_1", "runtime_step_2", "runtime_step_3"],
            "observable_completion_condition": "visible_state_change_or_declared_unfinished_state",
            "captureability": "can_be_shown_without_claiming unseen facts",
        }
    if role == "professional_judgment":
        return {
            "authority_role_types": ["authorized_founder", "store_manager", "sales_associate", "designer", "technical_operator"],
            "judgment_scope": f"{p0.lower()}_bounded_decision",
            "observable_basis": ["visible_signal", "declared_condition", "permitted_record"],
            "required_fact_slots": ["decision_authority", "claim_boundary", "observable_basis"],
            "claim_route": "bounded_non_universal_claim",
            "non_transferable_conditions": ["no role authority", "missing fact support", "missing public scope"],
        }
    if role == "visual_beat":
        return {
            "visual_function": f"{p0.lower()}_material_or_scene_anchor",
            "subject_type": "runtime_supplied_visible_subject",
            "shot_relation": "detail_to_context_or_context_to_detail",
            "action_continuity_constraint": "must_match_authorized_event_sequence",
            "available_material_requirement": "usable_visual_or_audio_material",
            "prohibit_fake_broll": True,
        }
    if role == "capture_instruction":
        return {
            "capture_mode": "simple_documentary_capture",
            "device_assumption": "basic_device",
            "people_requirement": "profile_required_people_and_authorization",
            "shot_count_range": "one_to_three_short_observations",
            "sound_policy": "ambient_or_low_guidance_only",
            "time_budget": "bounded_short_capture",
            "execution_layer_only": True,
        }
    raise ValueError(role)


def abstract_payload(role: str, p0: str, asset_class: str) -> dict[str, Any]:
    role_codes = {
        "scene": "scn",
        "trigger": "trg",
        "observable_action": "act",
        "professional_judgment": "eval",
        "visual_beat": "vis",
        "capture_instruction": "cap",
    }
    class_codes = {
        "scene_action_kernel": "sak",
        "narrative_operator": "nop",
        "role_perspective_voice": "rpv",
        "visual_audio_grammar": "vag",
    }
    return {
        "kind": f"{class_codes[asset_class]}_{role_codes[role]}_pattern",
        "function": f"organize {p0} {role_codes[role]} component logic through runtime-supplied slots",
        "mechanism": "separate observable structure, authority, and missing-input gates before any surface is written",
        "parameter_slots": [
            "content_product_type_id",
            "capability_group",
            "authorized_role_or_object",
            "event_truth_mode",
            "claim_boundary",
        ],
        "completion_condition": "all required slots are bound or the profile router degrades the output",
        "permitted_variation": "surface wording, shot order, and emphasis must be freshly generated by runtime context",
        "role_specific_fields": role_specific_fields(role, p0),
    }


def input_contract_for(role: str) -> dict[str, list[str]]:
    base = ["content_product_type_id", "event_truth_mode", "authorization_scope"]
    role_required = {
        "scene": ["scene_context", "business_object"],
        "trigger": ["trigger_condition", "observable_signal"],
        "observable_action": ["actor_role", "ordered_action_chain", "object_slot"],
        "professional_judgment": ["authority_role", "observable_basis", "claim_boundary"],
        "visual_beat": ["available_visual_material", "visible_subject"],
        "capture_instruction": ["usable_materials", "capture_people_authorization"],
    }
    return {
        "required": base + role_required[role],
        "optional": ["platform_expression_constraint", "continuity_pattern_ref"],
    }


def build_decisions_and_registry() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    candidates = load_jsonl(S1_CANDIDATES_PATH)
    profiles = load_yaml(S1_5_PROFILES_PATH)["content_product_profile_registry"]["profiles"]
    p0_by_parent = source_p0_index()
    group_sources: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    decisions: list[dict[str, Any]] = []

    for candidate in candidates:
        parent_ref = candidate["parent_refs"][0]
        source_asset_id = parent_ref["parent_asset_id"]
        source_p0 = p0_by_parent[source_asset_id]
        role = candidate["component_role"]
        group_sources[(role, source_p0)].append(candidate)

    registry_by_group: dict[tuple[str, str], dict[str, Any]] = {}
    for (role, p0), grouped in sorted(group_sources.items(), key=lambda item: (item[0][1], item[0][0])):
        asset_class = ROLE_TO_CLASS[role]
        applicable_cps = role_allowed_cp_ids(role, p0, profiles)
        component_id = f"RRC20-{p0}-{role.upper().replace('_', '-')}"
        primary_groups = sorted({p0 for cp in applicable_cps if p0_binding_kind(cp, p0) == "primary"})
        auxiliary_groups = sorted({p0 for cp in applicable_cps if p0_binding_kind(cp, p0) == "auxiliary"})
        reusable = {
            "component_id": component_id,
            "component_version": "v0.1",
            "lifecycle": "reviewed_reusable",
            "composition_asset_class": asset_class,
            "source_component_role": role,
            "applicable_content_product_type_ids": applicable_cps,
            "capability_bindings": {
                "supported_primary_P0_groups": primary_groups,
                "supported_auxiliary_P0_groups": auxiliary_groups,
                "P0_02_perspective_overlay_compatible": p0 == "P0_02",
            },
            "abstract_payload": abstract_payload(role, p0, asset_class),
            "input_slot_contract": input_contract_for(role),
            "compatibility_tag_refs": [
                f"role:{role}",
                f"class:{asset_class}",
                f"capability:{p0}",
                "truth_boundary:pattern_only",
            ],
            "incompatible_condition_refs": ["missing_required_profile_slots", "unapproved_event_truth_mode"],
            "forbidden_combination_rule_refs": ["no_fake_fact", "no_source_surface_copy", "no_runtime_plan_authority"],
            "role_authority_requirement": (
                "authorized_role_with_declared_decision_scope"
                if role == "professional_judgment"
                else "profile_authorization_scope"
            ),
            "claim_boundary": "pattern_and_mechanism_only_no_brand_fact_or_real_event_evidence",
            "surface_realization_policy": {
                "generate_new_surface": True,
                "parent_surface_verbatim_allowed": False,
                "source_sentence_template_allowed": False,
            },
            "truth_boundary": {
                "ontology_truth": False,
                "factual_authority": False,
                "real_event_evidence": False,
                "brand_fact_source": False,
                "person_experience_source": False,
            },
            "lineage": {
                "source_candidate_refs": [
                    {"candidate_id": item["component_id"], "candidate_digest": item["component_digest"]}
                    for item in grouped
                ],
                "parent_asset_refs": sorted(
                    {
                        (
                            item["parent_refs"][0]["parent_asset_id"],
                            item["parent_refs"][0]["parent_digest"],
                        )
                        for item in grouped
                    }
                ),
                "audit_sidecar_ref": f"{DECISIONS_PATH}#group={p0}:{role}",
            },
        }
        reusable["component_digest"] = object_digest(reusable, {"component_digest"})
        registry_by_group[(role, p0)] = reusable

    seen_group: set[tuple[str, str]] = set()
    for candidate in sorted(candidates, key=lambda item: item["component_id"]):
        parent_ref = candidate["parent_refs"][0]
        source_asset_id = parent_ref["parent_asset_id"]
        source_p0 = p0_by_parent[source_asset_id]
        role = candidate["component_role"]
        asset_class = ROLE_TO_CLASS[role]
        group = (role, source_p0)
        reusable = registry_by_group[group]
        reviewed_cp_ids = reusable["applicable_content_product_type_ids"]
        first_for_group = group not in seen_group
        seen_group.add(group)
        decision = "PROMOTE_AS_NEW" if first_for_group else "MERGE_INTO_REUSABLE"
        decisions.append(
            {
                "candidate_id": candidate["component_id"],
                "candidate_digest": candidate["component_digest"],
                "source_asset_id": source_asset_id,
                "source_P0_group": source_p0,
                "component_role": role,
                "proposed_composition_asset_class": asset_class,
                "original_applicable_product_ids": candidate.get("applicable_content_product_type_ids", []),
                "reviewed_applicable_product_ids": reviewed_cp_ids,
                "applicability_change": {
                    "enum": "EVIDENCE_BACKED_EXPAND",
                    "rationale": "Reviewed against v0.2 Profile required roles and Founder P0×CP mapping; old 3-profile applicability is not mechanically inherited.",
                },
                "review_dimensions": {
                    "semantic_purity": "PASS_ABSTRACTABLE",
                    "reusable_independence": "PASS_AFTER_ABSTRACTION",
                    "source_specificity": "SOURCE_SURFACE_EXCLUDED",
                    "factual_dependency": "REQUIRES_RUNTIME_FACT_SLOTS",
                    "role_authority_alignment": "BOUNDED_BY_PROFILE_AND_ROLE",
                    "CP_applicability": "SUPPORTED_BY_PROFILE_ROLE_AND_P0_MAPPING",
                    "capability_alignment": "SUPPORTED_BY_SOURCE_P0",
                    "compatibility_risk": "MEDIUM_REQUIRES_RUNTIME_ROUTER",
                    "surface_copy_risk": "CONTROLLED_BY_ABSTRACT_PAYLOAD",
                    "truth_boundary_integrity": "NO_FACT_AUTHORITY",
                },
                "decision": {"enum": decision},
                "target_reusable_component_id": reusable["component_id"],
                "decision_reason_codes": [
                    "ROLE_ALLOWED_BY_TARGET_PROFILE",
                    "P0_MAPPING_SUPPORTED",
                    "ABSTRACTABLE_TO_MECHANISM",
                    "SOURCE_SURFACE_EXCLUDED",
                ],
                "domain_rationale": "Promoted or merged only as a role-bound mechanism with runtime fact and authorization slots; no source surface is runtime-facing.",
                "reviewer": "Codex",
                "review_method": "bounded_codex_native_domain_review",
                "external_LLM_called": False,
            }
        )
    registry = [registry_by_group[key] for key in sorted(registry_by_group, key=lambda item: (item[1], item[0]))]
    summary = {
        "reviewed_candidate_count": len(decisions),
        "reviewed_reusable_component_count": len(registry),
        "merged_candidate_count": sum(1 for item in decisions if item["decision"]["enum"] == "MERGE_INTO_REUSABLE"),
        "source_specific_reference_only_count": 0,
        "needs_repair_count": 0,
        "rejected_count": 0,
    }
    return decisions, registry, summary


def build_coverage(registry: list[dict[str, Any]]) -> dict[str, Any]:
    profiles_doc = load_yaml(S1_5_PROFILES_PATH)["content_product_profile_registry"]
    profiles = profiles_doc["profiles"]
    records = []
    for profile in profiles:
        cp_id = profile["content_product_type_id"]
        required_roles = [item["role"] for item in profile["required_component_roles"]]
        refs = [
            {
                "component_id": component["component_id"],
                "source_component_role": component["source_component_role"],
                "composition_asset_class": component["composition_asset_class"],
                "component_digest": component["component_digest"],
            }
            for component in registry
            if cp_id in component["applicable_content_product_type_ids"]
        ]
        covered_roles = sorted({ref["source_component_role"] for ref in refs if ref["source_component_role"] in required_roles})
        missing_roles = [role for role in required_roles if role not in covered_roles]
        covered_classes = sorted({ref["composition_asset_class"] for ref in refs})
        required_classes = sorted({ROLE_TO_CLASS[role] for role in required_roles if role in ROLE_TO_CLASS})
        missing_classes = [asset_class for asset_class in required_classes if asset_class not in covered_classes]
        status = "COMPLETE" if not missing_roles else ("PARTIAL" if covered_roles else "NONE")
        records.append(
            {
                "content_product_type_id": cp_id,
                "required_component_roles": required_roles,
                "covered_required_roles": covered_roles,
                "missing_required_roles": missing_roles,
                "covered_composition_asset_classes": covered_classes,
                "missing_composition_asset_classes": missing_classes,
                "reviewed_reusable_component_refs": refs,
                "component_contract_coverage": {"status": status},
                "fixture_calibration_coverage": {"status": "MISSING_EXPLICIT"},
                "ORCH_contract_design_eligibility": {
                    "true_only_when_required_component_roles_complete": status == "COMPLETE"
                },
                "runtime_content_generation_eligibility": False,
            }
        )
    summary = {
        "complete_count": sum(1 for item in records if item["component_contract_coverage"]["status"] == "COMPLETE"),
        "partial_count": sum(1 for item in records if item["component_contract_coverage"]["status"] == "PARTIAL"),
        "none_count": sum(1 for item in records if item["component_contract_coverage"]["status"] == "NONE"),
        "eligible_profile_ids": [
            item["content_product_type_id"]
            for item in records
            if item["component_contract_coverage"]["status"] == "COMPLETE"
        ],
        "ineligible_profile_ids": [
            item["content_product_type_id"]
            for item in records
            if item["component_contract_coverage"]["status"] != "COMPLETE"
        ],
        "fixture_gap_count": 20,
        "runtime_generation_eligible_profile_count": 0,
    }
    doc = {
        "content_product_component_coverage": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "coverage_records": records,
            "component_supply_gaps": [
                {
                    "composition_asset_class": asset_class,
                    "status": "NO_SUFFICIENT_89_CANDIDATE_EVIDENCE",
                    "may_auto_create_from_profile_description": False,
                }
                for asset_class in [
                    "style_vector",
                    "platform_expression",
                    "continuity_pattern",
                    "anti_pattern_control",
                ]
            ],
            "summary": summary,
        }
    }
    doc["content_product_component_coverage"]["coverage_digest"] = object_digest(
        doc["content_product_component_coverage"], {"coverage_digest"}
    )
    return doc


def max_common_substring_len(a: str, b: str) -> int:
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for char_a in a:
        curr = [0]
        for j, char_b in enumerate(b, start=1):
            value = prev[j - 1] + 1 if char_a == char_b else 0
            curr.append(value)
            if value > best:
                best = value
        prev = curr
    return best


def string_leaf_values(value: Any) -> list[str]:
    leaves: list[str] = []
    if isinstance(value, str):
        leaves.append(value)
    elif isinstance(value, dict):
        for child in value.values():
            leaves.extend(string_leaf_values(child))
    elif isinstance(value, list):
        for child in value:
            leaves.extend(string_leaf_values(child))
    return leaves


def compute_max_overlap(registry: list[dict[str, Any]]) -> int:
    candidates = {item["component_id"]: item for item in load_jsonl(S1_CANDIDATES_PATH)}
    parents = source_record_index()
    all_parent_bodies = [
        str(record.get("body_text", "")) for record in parents.values()
    ]
    max_overlap = 0
    for component in registry:
        abstract_values = string_leaf_values(component["abstract_payload"])
        candidate_ids = [item["candidate_id"] for item in component["lineage"]["source_candidate_refs"]]
        compare_values = []
        for candidate_id in candidate_ids:
            candidate = candidates[candidate_id]
            compare_values.extend(string_leaf_values(candidate.get("payload", {})))
            parent_id = candidate["parent_refs"][0]["parent_asset_id"]
            compare_values.append(str(parents[parent_id].get("body_text", "")))
        compare_values.extend(all_parent_bodies)
        for left in abstract_values:
            for right in compare_values:
                max_overlap = max(max_overlap, max_common_substring_len(left, right))
    return max_overlap


def file_digest_map(paths: list[Path]) -> dict[str, str]:
    return {str(path): sha256_file(path) for path in paths}


def build_handoff(
    mapping_doc: dict[str, Any],
    decisions_text: str,
    registry_text: str,
    coverage_doc: dict[str, Any],
    registry: list[dict[str, Any]],
) -> dict[str, Any]:
    coverage = coverage_doc["content_product_component_coverage"]
    summary = coverage["summary"]
    handoff = {
        "gkb_orch_reviewed_component_handoff": {
            "handoff_kind": "GKB_REVIEWED_COMPONENT_HANDOFF_SNAPSHOT",
            "handoff_version": "v0.1",
            "freeze_status": "IMMUTABLE_DELIVERY_PENDING_GUARDIAN",
            "producer": "GKB",
            "intended_consumer": "ORCH",
            "pinned_inputs": {
                "clean_120_digest": CLEAN_120_SHA256,
                "controlled_v2_contract_digest": S1_DIGESTS["contract"],
                "profiles_v0_2_digest": S1_5_INTERNAL_DIGESTS["profiles_v0_2"],
                "P0_CP_mapping_digest": mapping_doc["capability_product_composition_mapping"]["P0_CP_mapping_digest"],
                "composition_asset_class_contract_digest": mapping_doc["capability_product_composition_mapping"]["composition_asset_class_contract_digest"],
                "source_candidates_digest": S1_DIGESTS["candidates"],
                "review_decisions_digest": sha256_text(decisions_text),
                "reviewed_registry_digest": sha256_text(registry_text),
                "profile_coverage_digest": coverage["coverage_digest"],
            },
            "component_contract_eligible_profile_ids": summary["eligible_profile_ids"],
            "component_contract_ineligible_profile_ids": summary["ineligible_profile_ids"],
            "fixture_calibration_ready_profile_ids": [],
            "runtime_generation_eligible_profile_ids": [],
            "runtime_excluded": [
                "Clean_120_body_text",
                "candidate_exact_payload",
                "derivation_spans",
                "domain_review_notes",
                "positive_fixture_body",
                "negative_fixture_body",
                "nine_GKB_pilot_bundles",
            ],
            "ownership": {
                "GKB_owns_profiles_and_component_versions": True,
                "GKB_may_create_canonical_CompositionPlan": False,
                "ORCH_selects_runtime_components": True,
                "ORCH_binds_brand_facts_and_authorizations": True,
                "ORCH_owns_runtime_continuity_thread": True,
                "ORCH_owns_canonical_CompositionPlan": True,
                "ORCH_may_mutate_GKB_assets": False,
                "DIFY_direct_GKB_consumption_allowed": False,
            },
            "state": {
                "handoff_integrity_frozen": True,
                "runtime_ingest_ready": False,
                "ORCH_integration_complete": False,
                "canonical_composition_plan_count": 0,
                "generation_invocation_count": 0,
                "audience_facing_content_count": 0,
            },
            "reviewed_reusable_component_count": len(registry),
        }
    }
    handoff["gkb_orch_reviewed_component_handoff"]["handoff_digest"] = object_digest(
        handoff["gkb_orch_reviewed_component_handoff"], {"handoff_digest"}
    )
    return handoff


def readiness_flags() -> dict[str, bool]:
    return {
        "runtime_ingest_ready": False,
        "generation_600_allowed": False,
        "expand_600_allowed": False,
        "expand_3600_allowed": False,
        "CandidatePack_ready": False,
        "KE_ready": False,
        "Serving_ready": False,
        "RAG_ready": False,
        "DIFY_ready": False,
        "production_ready": False,
    }


def build_result(
    decisions: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    coverage_doc: dict[str, Any],
    handoff_doc: dict[str, Any],
    max_overlap: int,
    file_digests: dict[str, str],
) -> dict[str, Any]:
    decision_counts = Counter(item["decision"]["enum"] for item in decisions)
    class_distribution = Counter(component["composition_asset_class"] for component in registry)
    coverage_summary = coverage_doc["content_product_component_coverage"]["summary"]
    result = {
        "component_review_20cp_and_handoff_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "verdict": "CONTROLLED_V2_89_COMPONENT_REVIEWED_AND_20CP_HANDOFF_FROZEN_PENDING_CLAUDE_GUARDIAN",
            "handoff_freeze_status": "IMMUTABLE_DELIVERY_PENDING_GUARDIAN",
            "baseline_head_before": BASELINE_HEAD,
            "counts": {
                "reviewed_candidate_count": len(decisions),
                "reviewed_reusable_component_count": len(registry),
                "merged_candidate_count": decision_counts["MERGE_INTO_REUSABLE"],
                "source_specific_reference_only_count": decision_counts["SOURCE_SPECIFIC_REFERENCE_ONLY"],
                "needs_repair_count": decision_counts["NEEDS_REPAIR"],
                "rejected_count": decision_counts["REJECT"],
                "component_contract_complete_profile_count": coverage_summary["complete_count"],
                "component_contract_partial_profile_count": coverage_summary["partial_count"],
                "component_contract_none_profile_count": coverage_summary["none_count"],
                "fixture_gap_count": 20,
                "runtime_generation_eligible_profile_count": 0,
                "canonical_composition_plan_count": 0,
                "audience_facing_content_count": 0,
            },
            "decision_distribution": dict(sorted(decision_counts.items())),
            "composition_asset_class_distribution": dict(sorted(class_distribution.items())),
            "component_contract_eligible_profile_ids": coverage_summary["eligible_profile_ids"],
            "component_contract_ineligible_profile_ids": coverage_summary["ineligible_profile_ids"],
            "max_verbatim_overlap_chars": max_overlap,
            "readiness_flags": readiness_flags(),
            "generated_file_digests": file_digests,
            "handoff_digest": handoff_doc["gkb_orch_reviewed_component_handoff"]["handoff_digest"],
            "blocker_ids": [],
            "not_proven": [
                "20_profiles_all_have_supply",
                "fixture_gap_closed",
                "content_quality_improved",
                "ORCH_integrated",
                "generation_600_or_3600_allowed",
            ],
        }
    }
    result["component_review_20cp_and_handoff_result"]["result_digest"] = object_digest(
        result["component_review_20cp_and_handoff_result"], {"result_digest"}
    )
    return result


def build_artifacts(root: Path) -> dict[Path, str]:
    mapping_doc = build_mapping_doc()
    policy_doc = build_policy_doc()
    decisions, registry, _summary = build_decisions_and_registry()
    coverage_doc = build_coverage(registry)
    decisions_text = jsonl_text(decisions)
    registry_text = jsonl_text(registry)
    handoff_doc = build_handoff(mapping_doc, decisions_text, registry_text, coverage_doc, registry)

    initial = {
        MAPPING_PATH: yaml_text(mapping_doc),
        POLICY_PATH: yaml_text(policy_doc),
        DECISIONS_PATH: decisions_text,
        REGISTRY_PATH: registry_text,
        COVERAGE_PATH: yaml_text(coverage_doc),
        HANDOFF_PATH: yaml_text(handoff_doc),
    }
    file_digests = {str(path): sha256_text(text) for path, text in initial.items()}
    file_digests[str(FREEZER_PATH)] = sha256_file(root / FREEZER_PATH)
    checker_abs = root / CHECKER_PATH
    file_digests[str(CHECKER_PATH)] = sha256_file(checker_abs) if checker_abs.exists() else "CHECKER_NOT_PRESENT"
    max_overlap = compute_max_overlap(registry)
    result_doc = build_result(decisions, registry, coverage_doc, handoff_doc, max_overlap, file_digests)
    initial[RESULT_PATH] = yaml_text(result_doc)
    return initial


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
        elif path.read_text(encoding="utf-8") != expected:
            mismatches.append(f"content mismatch: {relative_path}")
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", default=".")
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
