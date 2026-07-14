#!/usr/bin/env python3
"""Build the evidence-driven P2 targeted repair review packet."""

from __future__ import annotations

import copy
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from p2_component_model import (
    COMPONENT_CANDIDATES_PATH,
    CONTROL_RULES_PATH,
    TASK_ID,
    TASK_ROOT,
    jsonl_bytes,
    load_jsonl,
    object_digest,
    profile_requirements,
    require,
    sha256_bytes,
    source_state,
    yaml_bytes,
)
from p2_generator_core import build_local_typed_material, digest_object


if not __debug__:
    sys.stderr.write("P2 targeted repair refuses python -O\n")
    raise SystemExit(2)


REVISED_COMPONENTS_PATH = TASK_ROOT / "component/revised_component_candidates.r1.jsonl"
ADDITION_CANDIDATES_PATH = (
    TASK_ROOT / "component/necessary_addition_candidates.r1.jsonl"
)
REVISED_RULES_PATH = TASK_ROOT / "component/revised_control_rules.r1.jsonl"
FINAL_EDGE_CANDIDATES_PATH = TASK_ROOT / "component/final_edge_candidates.r1.jsonl"
REVISED_SUPPLY_PATH = TASK_ROOT / "component/revised_candidate_supply_matrix.r1.yaml"
REPAIR_ASSESSMENT_PATH = TASK_ROOT / "component/targeted_repair_assessment.r1.yaml"
REVISED_AB_PATH = TASK_ROOT / "ab/revised_ab_path_candidates.r1.jsonl"
TARGETED_REVIEW_PACKET_PATH = (
    TASK_ROOT / "review/targeted_repair_review_packet.r1.jsonl"
)
TARGETED_REVIEW_JOB_PATH = TASK_ROOT / "review/targeted_repair_review_job.r1.yaml"
TARGETED_RESULT_PATH = TASK_ROOT / "result/p2_targeted_repair_checkpoint_result.r1.yaml"


SOURCE_COMPONENT_IDS = frozenset(
    {
        "RCV2-002-ACTION-01-KNIT-RECOVERY-CHECK",
        "RCV2-002-ACTION-06-COAT-SHOULDER-RESET",
        "RCV2-002-ACTION-08-COLOR-COMPARISON-PROP",
        "RCV2-002-ACTION-10-STYLING-TUCK-WALK",
        "RCV2-002-ACTION-12-WINDOW-COLOR-MOVE",
        "RCV2-002-ACTION-15-TABLE-REARRANGE",
        "RCV2-002-SCENE-01-ARRIVAL-INSPECTION",
        "RCV2-002-SCENE-03-MULTI-CONTEXT-PRODUCT",
        "RCV2-002-SCENE-06-DISPLAY-GARMENT-RESET",
        "RCV2-002-SCENE-07-INSIDE-DETAIL-INSPECTION",
        "RCV2-002-SCENE-08-LIGHT-COLOR-OBSERVATION",
        "RCV2-002-SCENE-09-MATERIAL-CLAIM-BOUNDARY",
        "RCV2-002-SCENE-12-WINDOW-COLOR-ADJUSTMENT",
        "RCV2-002-SCENE-15-ARRIVAL-TABLE-REARRANGE",
        "RCV2-002-TRIGGER-02-UNSUPPORTED-FIT-CLAIM",
        "RCV2-002-TRIGGER-07-WORKMANSHIP-DETAIL-CHECK",
        "RCV2-002-TRIGGER-09-OBSERVATION-VS-RECORD",
        "RCV2-002-TRIGGER-11-OUTFIT-COMPLEXITY",
        "RCV2-002-TRIGGER-12-COLOR-AREA-IMBALANCE",
    }
)


ROLE_TYPED_CONTRACTS: dict[str, dict[str, list[str]]] = {
    "scene": {
        "input": ["scene_composition_parameters"],
        "fact": ["event_or_stage_state", "visible_context"],
        "authorization": ["scene_capture_and_use_scope"],
    },
    "observable_action": {
        "input": ["ordered_action_structure"],
        "fact": [
            "actor_task_identity",
            "handled_object",
            "observed_action_chain",
            "visible_result_or_unfinished_state",
        ],
        "authorization": ["actor_action_and_capture_scope"],
    },
    "trigger": {
        "input": ["safe_next_step_policy"],
        "fact": ["trigger_condition", "affected_object_or_claim"],
        "authorization": ["trigger_subject_and_use_scope"],
    },
}


ADDITION_SPECS: dict[str, dict[str, Any]] = {
    "G1V11-P2-SCENE-CAREER-STAGE-EVIDENCE": {
        "role": "scene",
        "asset_class": "scene_action_kernel",
        "profiles": ["CP05"],
        "function": "Anchor a career-history scene in a signed stage record, dated artifact, or authorized role milestone.",
        "inputs": ["stage_record_arrangement"],
        "facts": ["career_stage_record", "time_marker", "role_or_skill_state"],
        "authorizations": ["person_history_and_artifact_use_scope"],
        "gap": "CP05 had no scene component that represented an evidenced career stage without inventing biography.",
    },
    "G1V11-P2-TRIGGER-CAREER-STAGE-CHANGE": {
        "role": "trigger",
        "asset_class": "narrative_operator",
        "profiles": ["CP05"],
        "function": "Trigger a career-history segment only from a supplied stage change, skill milestone, or authorized retrospective marker.",
        "inputs": ["stage_change_routing_policy"],
        "facts": ["prior_stage", "recorded_change", "current_stage_or_open_question"],
        "authorizations": ["person_history_and_change_use_scope"],
        "gap": "Existing arrival and claim triggers did not represent CP05 career-stage evidence.",
    },
    "G1V11-P2-TRIGGER-DESIGN-TRADEOFF-RECORD": {
        "role": "trigger",
        "asset_class": "narrative_operator",
        "profiles": ["CP11"],
        "function": "Trigger design-tradeoff narration from a supplied option record that names the chosen, abandoned, and constrained alternatives.",
        "inputs": ["tradeoff_routing_policy"],
        "facts": ["design_problem", "considered_options", "recorded_choice_and_cost"],
        "authorizations": ["design_record_use_scope"],
        "gap": "Existing triggers did not expose CP11 choice, abandonment, and cost as typed evidence.",
    },
    "G1V11-P2-TRIGGER-VERSION-CHANGE-RECORD": {
        "role": "trigger",
        "asset_class": "narrative_operator",
        "profiles": ["CP12"],
        "function": "Trigger a version-log entry from two identified versions and a recorded change point, never from an inferred history.",
        "inputs": ["version_change_routing_policy"],
        "facts": ["prior_version_id", "current_version_id", "recorded_change_point"],
        "authorizations": ["version_record_use_scope"],
        "gap": "Existing retail and styling triggers were not version-change mechanisms for CP12.",
    },
    "G1V11-P2-ACTION-MATCHED-VERSION-CHANGE": {
        "role": "observable_action",
        "asset_class": "scene_action_kernel",
        "profiles": ["CP12"],
        "function": "Compare identified versions under the same bounded action and observation conditions while preserving unverified outcomes.",
        "inputs": ["matched_comparison_structure"],
        "facts": [
            "prior_version_id",
            "current_version_id",
            "matched_action",
            "matched_conditions",
            "observed_difference_or_pending_state",
        ],
        "authorizations": ["version_material_and_action_use_scope"],
        "gap": "Existing display actions lacked version identity and matched-condition bindings required by CP12.",
    },
    "G1V11-P2-TRIGGER-OPERATING-TRADEOFF": {
        "role": "trigger",
        "asset_class": "narrative_operator",
        "profiles": ["CP19"],
        "function": "Trigger an operating-decision review from a recorded option set, abandonment, cost, and authorized outcome boundary.",
        "inputs": ["decision_review_routing_policy"],
        "facts": [
            "decision_context",
            "options",
            "abandoned_option",
            "cost_or_tradeoff",
        ],
        "authorizations": ["operating_decision_record_use_scope"],
        "gap": "Existing claim and retail triggers did not establish CP19 operating tradeoffs.",
    },
    "G1V11-P2-TRIGGER-COMMITMENT-EVIDENCE-CHECK": {
        "role": "trigger",
        "asset_class": "narrative_operator",
        "profiles": ["CP20"],
        "function": "Trigger commitment tracking only from a supplied commitment, owner, review node, expected evidence, and current deviation state.",
        "inputs": ["commitment_review_routing_policy"],
        "facts": [
            "commitment_record",
            "commitment_owner",
            "review_node",
            "expected_evidence",
            "current_fulfillment_or_deviation_state",
        ],
        "authorizations": ["commitment_record_use_scope"],
        "gap": "Existing triggers did not represent the explicit commitment and review node required by CP20.",
    },
    "G1V11-P2-VISUAL-FIXED-ANCHOR-CONTEXT-COMPARE": {
        "role": "visual_beat",
        "asset_class": "visual_audio_grammar",
        "profiles": ["CP02", "CP13", "CP17", "CP18"],
        "function": "Compare the same authorized anchor across supplied times, contexts, or states without implying causality or a fabricated before-and-after.",
        "inputs": ["fixed_anchor_visual_sequence"],
        "facts": ["anchor_identity", "context_or_time_labels", "visible_states"],
        "authorizations": ["anchor_and_context_visual_use_scope"],
        "gap": "These products required a visual beat for time, context, or state comparison that existing detail and display-hierarchy beats did not supply.",
    },
    "G1V11-P2-ACTION-SOURCE-BOUND-CRAFT-STEP": {
        "role": "observable_action",
        "asset_class": "scene_action_kernel",
        "profiles": ["CP03"],
        "function": "Realize one source-backed craft step with its input, ordered action, judgment point, and visible result or unfinished state.",
        "inputs": ["craft_step_structure"],
        "facts": [
            "craft_input",
            "ordered_step",
            "judgment_point",
            "visible_step_state",
        ],
        "authorizations": ["craft_actor_action_and_capture_scope"],
        "gap": "Existing actions were inspection, styling, display, or editing actions and did not close CP03 process causality.",
    },
}


SELECTED_COMPONENTS: dict[str, dict[str, str]] = {
    "CP01": {
        "scene": "RCV2-002-SCENE-01-ARRIVAL-INSPECTION",
        "observable_action": "RCV2-002-ACTION-01-KNIT-RECOVERY-CHECK",
        "professional_judgment": "RCV2-004-JUDGMENT-SOURCE-BOUND-TASK-FRICTION",
        "capture_instruction": "RCV2-004-CAPTURE-CONTINUOUS-ACTION-PROOF",
    },
    "CP02": {
        "scene": "RCV2-002-SCENE-06-DISPLAY-GARMENT-RESET",
        "visual_beat": "G1V11-P2-VISUAL-FIXED-ANCHOR-CONTEXT-COMPARE",
        "observable_action": "RCV2-002-ACTION-06-COAT-SHOULDER-RESET",
        "capture_instruction": "RCV2-004-CAPTURE-MATCHED-FRAME-TIME-COMPARE",
    },
    "CP03": {
        "scene": "RCV2-002-SCENE-07-INSIDE-DETAIL-INSPECTION",
        "observable_action": "G1V11-P2-ACTION-SOURCE-BOUND-CRAFT-STEP",
        "trigger": "RCV2-002-TRIGGER-07-WORKMANSHIP-DETAIL-CHECK",
        "visual_beat": "RCV2-003-VISUAL-DETAIL-PATH-STRUCTURE",
        "capture_instruction": "RCV2-004-CAPTURE-CONTACT-SOURCE-SOUND-SYNC",
    },
    "CP04": {
        "scene": "RCV2-002-SCENE-01-ARRIVAL-INSPECTION",
        "observable_action": "RCV2-002-ACTION-06-COAT-SHOULDER-RESET",
        "transition": "RCV2-004-TRANSITION-PARALLEL-WORK-STATE",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "capture_instruction": "RCV2-004-CAPTURE-MULTI-ROLE-PARALLEL-FRAME",
    },
    "CP05": {
        "scene": "G1V11-P2-SCENE-CAREER-STAGE-EVIDENCE",
        "trigger": "G1V11-P2-TRIGGER-CAREER-STAGE-CHANGE",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "audience_facing_reasoning_move": "RCV2-004-REASONING-AUTHORIZED-FIELD-TRACE",
        "capture_instruction": "RCV2-004-CAPTURE-DOCUMENT-OBJECT-CROSS-BIND",
    },
    "CP06": {
        "scene": "RCV2-002-SCENE-07-INSIDE-DETAIL-INSPECTION",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "audience_facing_reasoning_move": "RCV2-003-REASONING-EVIDENCE-BEFORE-CONCLUSION",
        "visual_beat": "RCV2-003-VISUAL-DETAIL-PATH-STRUCTURE",
    },
    "CP07": {
        "trigger": "RCV2-002-TRIGGER-02-UNSUPPORTED-FIT-CLAIM",
        "professional_judgment": "RCV2-004-JUDGMENT-SOURCE-BOUND-TASK-FRICTION",
        "audience_facing_reasoning_move": "RCV2-004-REASONING-CONDITION-EXCLUSION-ALTERNATIVE",
        "closing": "RCV2-003-CLOSING-LOCAL-EVIDENCE-LONG-TERM-DEFER",
    },
    "CP08": {
        "scene": "RCV2-002-SCENE-09-MATERIAL-CLAIM-BOUNDARY",
        "visual_beat": "RCV2-003-VISUAL-DETAIL-PATH-STRUCTURE",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "audience_facing_reasoning_move": "RCV2-003-REASONING-EVIDENCE-BEFORE-CONCLUSION",
    },
    "CP09": {
        "trigger": "RCV2-002-TRIGGER-02-UNSUPPORTED-FIT-CLAIM",
        "professional_judgment": "RCV2-004-JUDGMENT-SOURCE-BOUND-TASK-FRICTION",
        "audience_facing_reasoning_move": "RCV2-004-REASONING-CONDITION-EXCLUSION-ALTERNATIVE",
        "closing": "RCV2-003-CLOSING-LOCAL-EVIDENCE-LONG-TERM-DEFER",
    },
    "CP10": {
        "trigger": "RCV2-002-TRIGGER-09-OBSERVATION-VS-RECORD",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "audience_facing_reasoning_move": "RCV2-004-REASONING-RESULT-TO-AUTHORIZED-TRACE",
        "capture_instruction": "RCV2-004-CAPTURE-MATCHED-FRAME-TIME-COMPARE",
    },
    "CP11": {
        "scene": "RCV2-002-SCENE-03-MULTI-CONTEXT-PRODUCT",
        "trigger": "G1V11-P2-TRIGGER-DESIGN-TRADEOFF-RECORD",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "audience_facing_reasoning_move": "RCV2-004-REASONING-AUTHORIZED-FIELD-TRACE",
        "capture_instruction": "RCV2-004-CAPTURE-DOCUMENT-OBJECT-CROSS-BIND",
    },
    "CP12": {
        "trigger": "G1V11-P2-TRIGGER-VERSION-CHANGE-RECORD",
        "observable_action": "G1V11-P2-ACTION-MATCHED-VERSION-CHANGE",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "capture_instruction": "RCV2-004-CAPTURE-VERSION-MATCHED-ACTION",
    },
    "CP13": {
        "scene": "RCV2-002-SCENE-03-MULTI-CONTEXT-PRODUCT",
        "visual_beat": "G1V11-P2-VISUAL-FIXED-ANCHOR-CONTEXT-COMPARE",
        "audience_facing_reasoning_move": "RCV2-003-REASONING-GARMENT-ROLE-NOT-BODY-JUDGMENT",
        "transition": "RCV2-003-TRANSITION-SAME-OBJECT-OBSERVATION-ENTRY",
    },
    "CP14": {
        "scene": "RCV2-002-SCENE-08-LIGHT-COLOR-OBSERVATION",
        "visual_beat": "RCV2-004-VISUAL-SILENT-OBJECT-CONTACT-RHYTHM",
        "observable_action": "RCV2-002-ACTION-08-COLOR-COMPARISON-PROP",
        "capture_instruction": "RCV2-004-CAPTURE-CONTACT-SOURCE-SOUND-SYNC",
    },
    "CP15": {
        "scene": "RCV2-002-SCENE-15-ARRIVAL-TABLE-REARRANGE",
        "observable_action": "RCV2-002-ACTION-15-TABLE-REARRANGE",
        "transition": "RCV2-004-TRANSITION-SOURCE-BOUND-TIME-SLICE",
        "capture_instruction": "RCV2-004-CAPTURE-STATUS-MAP-OVERVIEW-DETAIL",
    },
    "CP16": {
        "trigger": "RCV2-002-TRIGGER-11-OUTFIT-COMPLEXITY",
        "observable_action": "RCV2-002-ACTION-10-STYLING-TUCK-WALK",
        "professional_judgment": "RCV2-004-JUDGMENT-SOURCE-BOUND-TASK-FRICTION",
        "capture_instruction": "RCV2-004-CAPTURE-MULTI-ROLE-PARALLEL-FRAME",
    },
    "CP17": {
        "scene": "RCV2-002-SCENE-12-WINDOW-COLOR-ADJUSTMENT",
        "trigger": "RCV2-002-TRIGGER-12-COLOR-AREA-IMBALANCE",
        "observable_action": "RCV2-002-ACTION-12-WINDOW-COLOR-MOVE",
        "visual_beat": "G1V11-P2-VISUAL-FIXED-ANCHOR-CONTEXT-COMPARE",
        "capture_instruction": "RCV2-004-CAPTURE-MATCHED-FRAME-TIME-COMPARE",
    },
    "CP18": {
        "scene": "RCV2-002-SCENE-01-ARRIVAL-INSPECTION",
        "visual_beat": "G1V11-P2-VISUAL-FIXED-ANCHOR-CONTEXT-COMPARE",
        "observable_action": "RCV2-002-ACTION-12-WINDOW-COLOR-MOVE",
        "capture_instruction": "RCV2-004-CAPTURE-SOURCE-SOUND-TIME-ANCHOR",
    },
    "CP19": {
        "trigger": "G1V11-P2-TRIGGER-OPERATING-TRADEOFF",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "audience_facing_reasoning_move": "RCV2-004-REASONING-RESULT-TO-AUTHORIZED-TRACE",
        "closing": "RCV2-003-CLOSING-LOCAL-EVIDENCE-LONG-TERM-DEFER",
    },
    "CP20": {
        "trigger": "G1V11-P2-TRIGGER-COMMITMENT-EVIDENCE-CHECK",
        "professional_judgment": "RCV2-004-JUDGMENT-EVIDENCE-LEDGER-READER",
        "audience_facing_reasoning_move": "RCV2-004-REASONING-AUTHORIZED-FIELD-TRACE",
        "capture_instruction": "RCV2-004-CAPTURE-DOCUMENT-OBJECT-CROSS-BIND",
    },
}


CP_PATH_DESIGNS: dict[str, dict[str, Any]] = {
    "CP01": {
        "a": [
            "task_chronology",
            "context_action_boundary",
            "actor_task",
            "ambient_task_sound",
            "steady_observation",
            "current_boundary",
        ],
        "b": [
            "parallel_status_map",
            "state_blocker_trace",
            "task_object_state",
            "evidence_cue",
            "status_pulse",
            "next_check",
        ],
    },
    "CP02": {
        "a": [
            "fixed_camera_chronicle",
            "time_then_change",
            "whole_space_anchor",
            "continuous_ambience",
            "natural_duration",
            "ordinary_close",
        ],
        "b": [
            "fixed_anchor_time_slice",
            "state_then_time_trace",
            "same_anchor_detail",
            "time_marker_sound",
            "interval_pulse",
            "open_next_slice",
        ],
    },
    "CP03": {
        "a": [
            "full_step_process",
            "input_step_judgment_result",
            "hand_and_tool",
            "contact_source_sound",
            "causal_step_rhythm",
            "visible_step_state",
        ],
        "b": [
            "result_to_step_trace",
            "result_judgment_step_input",
            "result_detail_then_hand",
            "key_action_sound",
            "evidence_backtrack",
            "unfinished_or_verified",
        ],
    },
    "CP04": {
        "a": [
            "role_handoff",
            "role_sequence",
            "actor_and_shared_object",
            "role_source_sound",
            "handoff_rhythm",
            "shared_state",
        ],
        "b": [
            "parallel_role_readback",
            "result_then_role_evidence",
            "shared_object_multi_view",
            "separate_role_cues",
            "parallel_state_pulse",
            "authority_boundary",
        ],
    },
    "CP05": {
        "a": [
            "career_timeline",
            "stage_then_change",
            "authorized_stage_artifact",
            "recorded_voice_or_silence",
            "longitudinal_pacing",
            "current_stage",
        ],
        "b": [
            "evidence_ledger_stages",
            "artifact_then_stage_trace",
            "field_and_object",
            "dated_record_cue",
            "archive_pulse",
            "open_history_gap",
        ],
    },
    "CP06": {
        "a": [
            "observation_to_judgment",
            "detail_basis_limit",
            "detail_path",
            "operation_sound",
            "analytic_pause",
            "bounded_conclusion",
        ],
        "b": [
            "conclusion_to_evidence",
            "limit_basis_detail",
            "evidence_map",
            "source_cue",
            "reverse_evidence_pulse",
            "unproven_boundary",
        ],
    },
    "CP07": {
        "a": [
            "condition_decision_tree",
            "question_condition_option",
            "specific_task",
            "direct_role_voice",
            "decision_steps",
            "bounded_option",
        ],
        "b": [
            "exclusion_then_alternative",
            "not_fit_reason_alternative",
            "counter_condition",
            "patient_explanation",
            "elimination_steps",
            "request_missing_condition",
        ],
    },
    "CP08": {
        "a": [
            "outer_to_inner_deconstruction",
            "surface_structure_limit",
            "construction_detail",
            "operation_sync",
            "micro_to_structure",
            "evidence_boundary",
        ],
        "b": [
            "evidence_result_reverse",
            "limit_structure_surface",
            "detail_relation_map",
            "source_cue",
            "structure_pulse",
            "no_performance_inference",
        ],
    },
    "CP09": {
        "a": [
            "fit_then_nonfit",
            "condition_applicable_excluded",
            "condition_table",
            "direct_boundary_voice",
            "condition_steps",
            "alternative",
        ],
        "b": [
            "disqualifier_first",
            "excluded_reason_fit",
            "counterexample",
            "nonjudgmental_voice",
            "reverse_decision",
            "ask_for_condition",
        ],
    },
    "CP10": {
        "a": [
            "hypothesis_record_result",
            "time_record_limit",
            "matched_frame",
            "dated_cue",
            "log_interval",
            "limited_result",
        ],
        "b": [
            "result_to_record_trace",
            "result_record_hypothesis",
            "evidence_ledger",
            "record_marker",
            "reverse_log",
            "next_review",
        ],
    },
    "CP11": {
        "a": [
            "problem_options_choice",
            "problem_option_choice_cost",
            "option_artifacts",
            "document_cue",
            "decision_sequence",
            "recorded_tradeoff",
        ],
        "b": [
            "abandoned_option_first",
            "cost_abandonment_choice",
            "discarded_option_trace",
            "field_marker",
            "tradeoff_pulse",
            "open_constraint",
        ],
    },
    "CP12": {
        "a": [
            "version_chronology",
            "prior_change_current_pending",
            "matched_version_action",
            "version_marker",
            "comparison_steps",
            "pending_validation",
        ],
        "b": [
            "current_to_prior_trace",
            "current_difference_prior_cause",
            "difference_first",
            "record_cue",
            "reverse_version_pulse",
            "unverified_result",
        ],
    },
    "CP13": {
        "a": [
            "life_context_sequence",
            "context_role_relation",
            "same_item_context",
            "context_source_cue",
            "context_steps",
            "bounded_role",
        ],
        "b": [
            "same_object_role_map",
            "role_condition_context",
            "fixed_object_compare",
            "condition_marker",
            "role_map_pulse",
            "not_body_judgment",
        ],
    },
    "CP14": {
        "a": [
            "single_property_visual_motif",
            "surface_contact_detail",
            "material_contact",
            "environment_source_sound",
            "slow_contact",
            "visible_property_only",
        ],
        "b": [
            "contact_sound_pulse",
            "sound_contact_pause",
            "same_property_detail",
            "contact_anchor",
            "silent_evidence_pulse",
            "sensory_limit",
        ],
    },
    "CP15": {
        "a": [
            "goods_lifecycle",
            "arrival_action_handoff",
            "goods_and_actor",
            "operation_sound",
            "stage_sequence",
            "current_stage",
        ],
        "b": [
            "state_map_handoff",
            "state_blocker_next",
            "status_map",
            "time_anchor",
            "state_pulse",
            "pending_handoff",
        ],
    },
    "CP16": {
        "a": [
            "need_judgment_option_feedback",
            "need_option_action_feedback",
            "service_action",
            "role_dialogue",
            "service_steps",
            "feedback_boundary",
        ],
        "b": [
            "task_friction_first",
            "friction_evidence_option",
            "shared_object",
            "separate_role_cues",
            "evidence_pulse",
            "no_hero_claim",
        ],
    },
    "CP17": {
        "a": [
            "hypothesis_adjust_compare",
            "hypothesis_action_before_after",
            "fixed_space",
            "operation_sound",
            "experiment_steps",
            "review_state",
        ],
        "b": [
            "result_first_spatial_trace",
            "result_change_hypothesis",
            "state_map_detail",
            "time_marker",
            "comparison_pulse",
            "no_causal_overclaim",
        ],
    },
    "CP18": {
        "a": [
            "authorized_place_time_chronicle",
            "place_time_task",
            "local_store_anchor",
            "authorized_soundscape",
            "daily_duration",
            "local_boundary",
        ],
        "b": [
            "sound_anchor_time_slices",
            "sound_state_time",
            "same_place_detail",
            "time_sound_anchor",
            "seasonal_pulse",
            "no_locality_invention",
        ],
    },
    "CP19": {
        "a": [
            "context_options_choice_cost",
            "context_option_abandonment_result",
            "decision_record",
            "authorized_role_voice",
            "tradeoff_sequence",
            "bounded_result",
        ],
        "b": [
            "cost_result_reverse",
            "cost_abandonment_choice_context",
            "evidence_ledger",
            "record_cue",
            "reverse_tradeoff",
            "open_cost",
        ],
    },
    "CP20": {
        "a": [
            "commitment_node_evidence",
            "commitment_node_result_next",
            "commitment_record",
            "dated_record_cue",
            "review_sequence",
            "next_node",
        ],
        "b": [
            "deviation_evidence_first",
            "deviation_evidence_commitment",
            "evidence_gap",
            "exception_marker",
            "audit_pulse",
            "no_emotional_substitute",
        ],
    },
}


AXIS_NAMES = (
    "narrative_mechanism",
    "information_order",
    "visual_subject",
    "sound_subject",
    "rhythm",
    "ending",
)

CP_AXIS_OVERRIDES = {
    "CP06": (
        "narrative_mechanism",
        "information_order",
        "visual_subject",
        "rhythm",
        "reasoning_sequence",
        "ending",
    ),
    "CP07": (
        "narrative_mechanism",
        "information_order",
        "opening_evidence",
        "reasoning_sequence",
        "voice_distance",
        "ending",
    ),
    "CP08": (
        "narrative_mechanism",
        "information_order",
        "visual_subject",
        "rhythm",
        "reasoning_sequence",
        "ending",
    ),
    "CP09": (
        "narrative_mechanism",
        "information_order",
        "opening_evidence",
        "reasoning_sequence",
        "voice_distance",
        "ending",
    ),
    "CP13": (
        "narrative_mechanism",
        "information_order",
        "visual_subject",
        "rhythm",
        "reasoning_sequence",
        "ending",
    ),
    "CP19": (
        "narrative_mechanism",
        "information_order",
        "opening_evidence",
        "reasoning_sequence",
        "voice_distance",
        "ending",
    ),
}

EXTRA_AXIS_VALUES = {
    "CP06": {
        "a": {"reasoning_sequence": "observation_basis_limit"},
        "b": {"reasoning_sequence": "limit_claim_evidence"},
    },
    "CP07": {
        "a": {
            "opening_evidence": "supplied_question_condition",
            "reasoning_sequence": "condition_option_exclusion",
            "voice_distance": "direct_task_adviser",
        },
        "b": {
            "opening_evidence": "disqualifying_condition",
            "reasoning_sequence": "exclusion_reason_alternative",
            "voice_distance": "bounded_evidence_reader",
        },
    },
    "CP08": {
        "a": {"reasoning_sequence": "surface_structure_use_limit"},
        "b": {"reasoning_sequence": "limit_evidence_structure"},
    },
    "CP09": {
        "a": {
            "opening_evidence": "applicable_condition",
            "reasoning_sequence": "fit_nonfit_alternative",
            "voice_distance": "nonjudgmental_adviser",
        },
        "b": {
            "opening_evidence": "disqualifier_or_missing_condition",
            "reasoning_sequence": "nonfit_reason_counteroption",
            "voice_distance": "source_bound_decision_reader",
        },
    },
    "CP13": {
        "a": {"reasoning_sequence": "context_role_relation"},
        "b": {"reasoning_sequence": "role_condition_context"},
    },
    "CP19": {
        "a": {
            "opening_evidence": "recorded_decision_context",
            "reasoning_sequence": "options_choice_abandonment_cost",
            "voice_distance": "authorized_decision_owner",
        },
        "b": {
            "opening_evidence": "recorded_cost_or_abandonment",
            "reasoning_sequence": "cost_result_choice_context",
            "voice_distance": "evidence_ledger_reader",
        },
    },
}


CONTROL_CP_SCOPE = {
    "G1V11-CR-04-CLAIM-EVIDENCE-LIMIT": [f"CP{i:02d}" for i in range(1, 21)],
    "G1V11-CR-05-ONLY-SITE-DOABLE-ACTIONS": [
        "CP01",
        "CP02",
        "CP03",
        "CP04",
        "CP05",
        "CP06",
        "CP08",
        "CP10",
        "CP11",
        "CP12",
        "CP13",
        "CP14",
        "CP15",
        "CP16",
        "CP17",
        "CP18",
        "CP20",
    ],
    "G1V11-CR-06-ANONYMIZE-CLOTHING-STORY": [
        "CP01",
        "CP02",
        "CP04",
        "CP05",
        "CP07",
        "CP09",
        "CP10",
        "CP11",
        "CP13",
        "CP16",
        "CP18",
        "CP19",
        "CP20",
    ],
    "G1V11-CR-07-WORKMANSHIP-VS-LIFESPAN": [
        "CP03",
        "CP06",
        "CP08",
        "CP10",
        "CP11",
        "CP14",
    ],
    "G1V11-CR-08-LIGHT-BEFORE-COLOR-CLAIM": [
        "CP02",
        "CP03",
        "CP06",
        "CP08",
        "CP12",
        "CP13",
        "CP14",
        "CP17",
        "CP18",
    ],
    "G1V11-CR-09-OBSERVABLE-VS-RECORD-CLAIM": [f"CP{i:02d}" for i in range(1, 21)],
    "G1V11-CR-10-DEMO-NOT-BODY-PROMISE": [
        "CP03",
        "CP06",
        "CP07",
        "CP08",
        "CP09",
        "CP11",
        "CP13",
        "CP14",
        "CP16",
    ],
    "G1V11-CR-11-OUTFIT-ROLE-NOT-BODY-JUDGE": [
        "CP06",
        "CP07",
        "CP08",
        "CP09",
        "CP11",
        "CP13",
        "CP14",
        "CP16",
    ],
}


def _typed_compatibility() -> list[dict[str, Any]]:
    return [
        {
            "rule": "fact_slots_bind_exact_typed_fact_objects",
            "fail_action": "STOP_OR_PROFILE_DEGRADE",
        },
        {
            "rule": "authorization_slots_bind_exact_subject_purpose_scope_and_validity",
            "fail_action": "STOP",
        },
        {
            "rule": "component_never_supplies_fact_or_authorization",
            "fail_action": "REJECT_BINDING",
        },
        {
            "rule": "claim_must_remain_inside_bound_fact_and_authorization_scope",
            "fail_action": "HOLD_OR_STOP",
        },
    ]


def build_revised_components(root: Path) -> list[dict[str, Any]]:
    originals = {
        row["component_id"]: row for row in load_jsonl(root / COMPONENT_CANDIDATES_PATH)
    }
    rows: list[dict[str, Any]] = []
    for component_id in sorted(SOURCE_COMPONENT_IDS):
        original = originals[component_id]
        role = str(original["component_role"])
        contract = ROLE_TYPED_CONTRACTS[role]
        row = copy.deepcopy(original)
        row["component_version"] = "v1.1-p2-r1"
        row["supersedes_p2_candidate_component_digest"] = row.pop("component_digest")
        row["required_input_slots"] = contract["input"]
        row["required_fact_slots"] = contract["fact"]
        row["required_authorization_slots"] = contract["authorization"]
        row["compatibility_rules"] = _typed_compatibility()
        row["missing_input_behavior"] = (
            "USE_EXACT_TARGET_PROFILE_ROUTE_WITHOUT_FACT_FILL"
        )
        row["activation_proposal"] = "REVISED_FOR_TARGETED_TWO_REVIEW"
        row["independent_review_state"] = "PENDING_TARGETED_TWO_REVIEWS"
        row["revision_basis"] = [
            "SECONDARY_TYPED_FACT_AUTHORIZATION_CONTRACT_REPAIR",
            "PRIMARY_CP_FIT_AND_ATOMICITY_FINDINGS_APPLIED_TO_SELECTED_SET",
        ]
        row["component_digest"] = object_digest(row, "component_digest")
        rows.append(row)
    return rows


def build_additions(state: dict[str, Any]) -> list[dict[str, Any]]:
    profile_by_id = state["profile_by_id"]
    rows: list[dict[str, Any]] = []
    for component_id, spec in sorted(ADDITION_SPECS.items()):
        profile_refs = [
            {
                "content_product_type_id": cp_id,
                "profile_digest": profile_by_id[cp_id]["profile_digest"],
                "required_role": spec["role"],
                "hard_guards": profile_by_id[cp_id]["founder_hard_guards"],
            }
            for cp_id in spec["profiles"]
        ]
        row: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "component_id": component_id,
            "component_version": "v1.1-p2-r1-new",
            "component_role": spec["role"],
            "composition_asset_class": spec["asset_class"],
            "mechanism": {
                "kind": f"{spec['asset_class']}:{spec['role']}:domain_design_mechanism",
                "function": spec["function"],
                "actual_mechanism": spec["function"],
                "surface_policy": {
                    "generate_new_surface": True,
                    "parent_verbatim_allowed": False,
                    "source_sentence_template_allowed": False,
                },
            },
            "required_input_slots": spec["inputs"],
            "required_fact_slots": spec["facts"],
            "required_authorization_slots": spec["authorizations"],
            "claim_boundary": "structure only; no fact, event, person, brand, outcome, or authorization authority",
            "role_authority_boundary": "runtime role and authority must be supplied and validated",
            "compatibility_rules": _typed_compatibility(),
            "forbidden_combinations": [
                "no_fake_fact",
                "no_source_surface_copy",
                "no_runtime_plan_authority",
            ],
            "missing_input_behavior": "USE_EXACT_TARGET_PROFILE_ROUTE_WITHOUT_FACT_FILL",
            "truth_boundary": {
                "factual_authority": False,
                "brand_fact_source": False,
                "person_experience_source": False,
                "real_event_evidence": False,
                "ontology_truth": False,
            },
            "provenance": {
                "source_type": "PROFILE_DERIVED_DOMAIN_DESIGN",
                "design_basis": profile_refs,
                "verified_supply_gap": spec["gap"],
                "source_text_span_required": False,
                "evidence_boundary": "PRODUCT_CONTRACT_DESIGN_ONLY_NO_FACT_AUTHORITY",
            },
            "historical_applicability_only": [],
            "proposed_applicability": spec["profiles"],
            "activation_proposal": "NECESSARY_ADDITION_PENDING_TARGETED_TWO_REVIEWS",
            "new_generator_consumable": False,
            "independent_review_state": "PENDING_TARGETED_TWO_REVIEWS",
            "readiness": {
                "generation_eligible": False,
                "runtime_ingest_ready": False,
                "production_ready": False,
            },
        }
        row["component_digest"] = object_digest(row, "component_digest")
        rows.append(row)
    return rows


def build_revised_rules(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for original in load_jsonl(root / CONTROL_RULES_PATH):
        rule_id = str(original["control_rule_id"])
        row = copy.deepcopy(original)
        row["supersedes_p2_candidate_control_rule_digest"] = row.pop(
            "control_rule_digest"
        )
        row["applicability_boundary"] = {
            "mode": "TRIGGER_DRIVEN_EXPLICIT_PROFILE_SCOPE",
            "applicable_profile_ids": CONTROL_CP_SCOPE[rule_id],
            "requires_trigger_condition_match": True,
            "unlisted_profile_behavior": "NOT_APPLICABLE_UNLESS_REVIEWED_SUCCESSOR_ADDS_IT",
            "false_positive_example": row["false_positive_handling"],
        }
        row["provenance"] = {
            "supersedes_misclassified_component_id": row[
                "supersedes_misclassified_component_id"
            ],
            "supersedes_component_digest": row["supersedes_component_digest"],
            "source_mechanism_digest": digest_object(row["source_mechanism"]),
            "boundary_revision_basis": "INDEPENDENT_REVIEW_PRODUCT_RISK_RECOMPUTATION",
        }
        row["independent_review_state"] = "PENDING_TARGETED_TWO_REVIEWS"
        row["active"] = False
        row["contributes_component_supply"] = False
        row["may_write_audience_surface"] = False
        row["control_rule_digest"] = object_digest(row, "control_rule_digest")
        rows.append(row)
    return rows


def _component_pool(
    root: Path,
    revised: list[dict[str, Any]],
    additions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    original = {
        row["component_id"]: row for row in load_jsonl(root / COMPONENT_CANDIDATES_PATH)
    }
    original.update({row["component_id"]: row for row in revised})
    original.update({row["component_id"]: row for row in additions})
    return original


def build_final_edge_candidates(
    state: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in state["profiles"]:
        cp_id = str(profile["content_product_type_id"])
        selected = SELECTED_COMPONENTS[cp_id]
        requirements = {row["role"]: row for row in profile["required_component_roles"]}
        require(set(selected) == set(requirements), "E_SELECTED_ROLE_COVERAGE", cp_id)
        for role in requirements:
            component = component_by_id[selected[role]]
            require(
                component["component_role"] == role,
                "E_SELECTED_ROLE",
                f"{cp_id}:{role}",
            )
            row: dict[str, Any] = {
                "schema_version": "v0.1",
                "task_id": TASK_ID,
                "edge_id": f"P2R1-EDGE-{cp_id}-{role}-01",
                "content_product_type_id": cp_id,
                "component_id": component["component_id"],
                "component_digest": component["component_digest"],
                "required_component_role": role,
                "selection_purpose": "MINIMUM_EVIDENCE_CLOSED_SUPPLY",
                "fit_basis": {
                    "product_label": profile["chinese_label"],
                    "business_purpose": profile["business_purpose"],
                    "exact_required_role": role,
                    "component_function": component["mechanism"].get("function"),
                    "profile_narrative_operators": profile["narrative_constraints"][
                        "allowed_narrative_operator_families"
                    ],
                    "profile_hard_guards": profile["founder_hard_guards"],
                    "binding_statement": (
                        f"Use {component['component_id']} only for {cp_id} "
                        f"{profile['chinese_label']} as its {role} mechanism; "
                        "all product facts, actors, events, outcomes, and permissions "
                        "must come from the exact typed bindings below."
                    ),
                    "historical_applicability_is_not_evidence": True,
                },
                "required_bindings": {
                    "profile": profile_requirements(profile),
                    "component_input_slots": component["required_input_slots"],
                    "component_fact_slots": component["required_fact_slots"],
                    "component_authorization_slots": component[
                        "required_authorization_slots"
                    ],
                    "profile_digest": profile["profile_digest"],
                },
                "forbidden_combinations": component["forbidden_combinations"],
                "missing_input_behavior": component["missing_input_behavior"],
                "historical_edge_reactivated": False,
                "proposed_new_edge": True,
                "active": False,
                "independent_review_state": "PENDING_TARGETED_TWO_REVIEWS",
            }
            row["edge_digest"] = object_digest(row, "edge_digest")
            rows.append(row)
    return rows


def _supporting_component_ids(selected: dict[str, str], axis: str) -> list[str]:
    preferred_roles = {
        "narrative_mechanism": (
            "scene",
            "trigger",
            "transition",
            "audience_facing_reasoning_move",
        ),
        "information_order": (
            "trigger",
            "transition",
            "audience_facing_reasoning_move",
            "scene",
        ),
        "visual_subject": (
            "visual_beat",
            "capture_instruction",
            "observable_action",
            "scene",
        ),
        "sound_subject": ("capture_instruction", "observable_action", "scene"),
        "rhythm": (
            "capture_instruction",
            "visual_beat",
            "transition",
            "observable_action",
        ),
        "ending": (
            "closing",
            "audience_facing_reasoning_move",
            "professional_judgment",
            "transition",
            "capture_instruction",
            "scene",
        ),
        "opening_evidence": (
            "trigger",
            "scene",
            "audience_facing_reasoning_move",
            "professional_judgment",
        ),
        "reasoning_sequence": (
            "audience_facing_reasoning_move",
            "professional_judgment",
            "trigger",
            "transition",
        ),
        "voice_distance": (
            "professional_judgment",
            "audience_facing_reasoning_move",
            "closing",
            "trigger",
        ),
    }[axis]
    matches = [selected[role] for role in preferred_roles if role in selected]
    return matches[:2]


def build_revised_ab_paths(
    state: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in state["profiles"]:
        cp_id = str(profile["content_product_type_id"])
        selected = SELECTED_COMPONENTS[cp_id]
        design = CP_PATH_DESIGNS[cp_id]
        axes = CP_AXIS_OVERRIDES.get(cp_id, AXIS_NAMES)
        material = build_local_typed_material(profile)
        lanes: dict[str, dict[str, Any]] = {}
        for lane_id, key in (("A", "a"), ("B", "b")):
            base_values = dict(zip(AXIS_NAMES, design[key], strict=True))
            base_values.update(EXTRA_AXIS_VALUES.get(cp_id, {}).get(key, {}))
            lane = {axis: base_values[axis] for axis in axes}
            lane.update(
                {
                    "lane_id": lane_id,
                    "session_policy": f"INDEPENDENT_SESSION_{lane_id}",
                    "other_lane_visible": False,
                    "component_ids": list(selected.values()),
                }
            )
            lanes[lane_id] = lane
        axis_contracts = [
            {
                "axis": axis,
                "lane_a_value": lanes["A"][axis],
                "lane_b_value": lanes["B"][axis],
                "supporting_component_ids": _supporting_component_ids(selected, axis),
                "realization_target": f"/lane/{{lane_id}}/{axis}",
                "values_must_differ": True,
            }
            for axis in axes
        ]
        row: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "content_product_type_id": cp_id,
            "profile_digest": profile["profile_digest"],
            "shared_typed_material_contract": {
                "material_id": material["material_id"],
                "material_digest": material["material_digest"],
                "source_object_ids": [row["source_id"] for row in material["sources"]],
                "fact_object_ids": [row["fact_id"] for row in material["facts"]],
                "authorization_object_ids": [
                    row["authorization_id"] for row in material["authorizations"]
                ],
                "claim_boundary_digest": digest_object(material["claim_boundary"]),
                "same_exact_object_required_for_both_lanes": True,
            },
            "lane_a": lanes["A"],
            "lane_b": lanes["B"],
            "axis_realization_contracts": axis_contracts,
            "observable_difference_axes": list(axes),
            "observable_difference_axis_count": len(axes),
            "structural_candidate_only": True,
            "content_quality_proven": False,
            "active": False,
            "independent_review_state": "PENDING_TARGETED_TWO_REVIEWS",
        }
        row["path_digest"] = object_digest(row, "path_digest")
        rows.append(row)
    return rows


def build_supply(state: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for profile in state["profiles"]:
        cp_id = str(profile["content_product_type_id"])
        roles: list[dict[str, Any]] = []
        for requirement in profile["required_component_roles"]:
            role = str(requirement["role"])
            matches = [
                row
                for row in edges
                if row["content_product_type_id"] == cp_id
                and row["required_component_role"] == role
            ]
            roles.append(
                {
                    "role": role,
                    "minimum": requirement["min_count"],
                    "candidate_count": len(matches),
                    "candidate_component_ids": [row["component_id"] for row in matches],
                    "complete_pending_targeted_review": len(matches)
                    >= requirement["min_count"],
                }
            )
        entries.append(
            {
                "content_product_type_id": cp_id,
                "candidate_supply_complete": all(
                    row["complete_pending_targeted_review"] for row in roles
                ),
                "approved_supply_complete": False,
                "required_roles": roles,
            }
        )
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "candidate_complete_profile_count": sum(
            row["candidate_supply_complete"] for row in entries
        ),
        "approved_complete_profile_count": 0,
        "entries": entries,
    }
    document["matrix_digest"] = object_digest(document, "matrix_digest")
    return {"revised_candidate_supply_matrix": document}


def build_review_packet(
    revised_components: list[dict[str, Any]],
    additions: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    paths: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component in revised_components + additions:
        rows.append(
            {
                "packet_item_id": f"P2R1-COMPONENT-{component['component_id']}",
                "object_type": "REVISED_OR_NECESSARY_COMPONENT",
                "review_subject": component,
                "required_review_roles": [
                    "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                    "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
                ],
                "prefilled_score": None,
                "prefilled_decision": None,
            }
        )
    for rule in rules:
        rows.append(
            {
                "packet_item_id": f"P2R1-CONTROL-{rule['control_rule_id']}",
                "object_type": "REVISED_CONTROL_RULE_SEPARATION",
                "review_subject": rule,
                "required_review_roles": [
                    "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                    "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
                ],
                "prefilled_score": None,
                "prefilled_decision": None,
            }
        )
    for edge in edges:
        rows.append(
            {
                "packet_item_id": f"P2R1-{edge['edge_id']}",
                "object_type": "REVISED_COMPONENT_CP_EDGE",
                "review_subject": edge,
                "required_review_roles": [
                    "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                    "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
                ],
                "prefilled_score": None,
                "prefilled_decision": None,
            }
        )
    for path in paths:
        rows.append(
            {
                "packet_item_id": f"P2R1-AB-{path['content_product_type_id']}",
                "object_type": "REVISED_AB_STRUCTURAL_PATH_CAPABILITY",
                "review_subject": path,
                "required_review_roles": [
                    "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
                    "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
                ],
                "prefilled_score": None,
                "prefilled_decision": None,
            }
        )
    return rows


def build_targeted_repair_documents(root: Path) -> dict[Path, bytes]:
    state = source_state(root)
    revised_components = build_revised_components(root)
    additions = build_additions(state)
    rules = build_revised_rules(root)
    component_by_id = _component_pool(root, revised_components, additions)
    edges = build_final_edge_candidates(state, component_by_id)
    paths = build_revised_ab_paths(state, component_by_id)
    supply = build_supply(state, edges)
    packet = build_review_packet(revised_components, additions, rules, edges, paths)
    packet_bytes = jsonl_bytes(packet)
    packet_sha = sha256_bytes(packet_bytes)
    assessment: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "historical_inventory": 86,
        "historical_inventory_target_used": False,
        "selected_source_component_revision_count": len(revised_components),
        "necessary_addition_count": len(additions),
        "addition_ids": [row["component_id"] for row in additions],
        "withdrawn_initial_edge_count": 162,
        "replacement_minimum_edge_count": len(edges),
        "real_supply_or_ab_gap_required_for_every_addition": True,
        "number_target_used": False,
        "finding": "NINE_PROFILE_DERIVED_COMPONENTS_REQUIRED_AFTER_TWO_INDEPENDENT_REVIEWS",
    }
    assessment["assessment_digest"] = object_digest(assessment, "assessment_digest")
    job: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_TARGETED_TWO_REVIEW",
        "review_packet_path": TARGETED_REVIEW_PACKET_PATH.as_posix(),
        "review_packet_sha256": packet_sha,
        "packet_item_count": len(packet),
        "packet_item_counts": dict(Counter(row["object_type"] for row in packet)),
        "reviewer_policy": {
            "reuse_original_identity_isolated_primary_and_secondary_reviewers": True,
            "review_each_revised_object_from_actual_payload": True,
            "changed_components_edges_supply_and_paths_reviewed_together": True,
            "self_approval_allowed": False,
        },
        "activation_before_matching_approvals_allowed": False,
    }
    job["review_job_digest"] = object_digest(job, "review_job_digest")
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_TARGETED_TWO_REVIEW",
        "p2_complete": False,
        "p3_allowed": False,
        "revised_component_count": len(revised_components),
        "necessary_addition_count": len(additions),
        "revised_control_rule_count": len(rules),
        "replacement_edge_count": len(edges),
        "revised_ab_path_count": len(paths),
        "review_packet_sha256": packet_sha,
        "active_component_count": 0,
        "active_edge_count": 0,
        "self_approval_count": 0,
        "core_numbers": {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "readiness": {
            "generator_qualified": False,
            "generation_allowed": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        },
    }
    result["result_digest"] = object_digest(result, "result_digest")
    return {
        REVISED_COMPONENTS_PATH: jsonl_bytes(revised_components),
        ADDITION_CANDIDATES_PATH: jsonl_bytes(additions),
        REVISED_RULES_PATH: jsonl_bytes(rules),
        FINAL_EDGE_CANDIDATES_PATH: jsonl_bytes(edges),
        REVISED_SUPPLY_PATH: yaml_bytes(supply),
        REPAIR_ASSESSMENT_PATH: yaml_bytes({"targeted_repair_assessment": assessment}),
        REVISED_AB_PATH: jsonl_bytes(paths),
        TARGETED_REVIEW_PACKET_PATH: packet_bytes,
        TARGETED_REVIEW_JOB_PATH: yaml_bytes({"targeted_repair_review_job": job}),
        TARGETED_RESULT_PATH: yaml_bytes(
            {"p2_targeted_repair_checkpoint_result": result}
        ),
    }


def validate_targeted_repair_documents(documents: dict[Path, bytes]) -> None:
    revised = [
        yaml.safe_load(line)
        for line in documents[REVISED_COMPONENTS_PATH].decode("utf-8").splitlines()
    ]
    additions = [
        yaml.safe_load(line)
        for line in documents[ADDITION_CANDIDATES_PATH].decode("utf-8").splitlines()
    ]
    rules = [
        yaml.safe_load(line)
        for line in documents[REVISED_RULES_PATH].decode("utf-8").splitlines()
    ]
    edges = [
        yaml.safe_load(line)
        for line in documents[FINAL_EDGE_CANDIDATES_PATH].decode("utf-8").splitlines()
    ]
    paths = [
        yaml.safe_load(line)
        for line in documents[REVISED_AB_PATH].decode("utf-8").splitlines()
    ]
    packet = [
        yaml.safe_load(line)
        for line in documents[TARGETED_REVIEW_PACKET_PATH].decode("utf-8").splitlines()
    ]
    supply = yaml.safe_load(documents[REVISED_SUPPLY_PATH])[
        "revised_candidate_supply_matrix"
    ]
    result = yaml.safe_load(documents[TARGETED_RESULT_PATH])[
        "p2_targeted_repair_checkpoint_result"
    ]
    require(len(revised) == len(SOURCE_COMPONENT_IDS), "E_REVISED_COMPONENT_COUNT")
    require(len(additions) == len(ADDITION_SPECS) == 9, "E_ADDITION_COUNT")
    require(len(rules) == 8, "E_REVISED_RULE_COUNT")
    require(
        len(edges) == sum(len(row) for row in SELECTED_COMPONENTS.values()),
        "E_EDGE_COUNT",
    )
    require(len(paths) == 20, "E_PATH_COUNT")
    require(supply["candidate_complete_profile_count"] == 20, "E_SUPPLY_COUNT")
    require(
        all(
            row["required_fact_slots"] and row["required_authorization_slots"]
            for row in revised + additions
        ),
        "E_TYPED_COMPONENT_CONTRACT",
    )
    require(
        all(
            row["contributes_component_supply"] is False and row["active"] is False
            for row in rules
        ),
        "E_CONTROL_SEPARATION",
    )
    require(
        all(
            row["observable_difference_axis_count"] >= 4
            and row["lane_a"] != row["lane_b"]
            and all(
                contract["supporting_component_ids"]
                for contract in row["axis_realization_contracts"]
            )
            for row in paths
        ),
        "E_AB_DIVERGENCE",
    )
    require(
        all(
            row["prefilled_score"] is None and row["prefilled_decision"] is None
            for row in packet
        ),
        "E_REVIEW_PREFILLED",
    )
    require(
        result["p2_complete"] is False and result["p3_allowed"] is False, "E_P3_EARLY"
    )
    require(
        result["core_numbers"]
        == {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "E_CORE_NUMBERS",
    )
    serialized = b"".join(documents.values())
    require(b"generator_qualified: true" not in serialized, "E_QUALIFIED_EARLY")
