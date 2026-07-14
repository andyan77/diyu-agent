#!/usr/bin/env python3
"""Build the second, semantics-closed P2 targeted-repair review packet."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from p2_component_model import (
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
from p2_targeted_repair import (
    AXIS_NAMES,
    CP_PATH_DESIGNS,
    SELECTED_COMPONENTS as R1_SELECTED_COMPONENTS,
    build_additions as build_r1_additions,
    build_revised_components as build_r1_revised_components,
    build_revised_rules as build_r1_revised_rules,
)


if not __debug__:
    sys.stderr.write("P2 targeted repair r2 refuses python -O\n")
    raise SystemExit(2)


REVISED_COMPONENTS_R2_PATH = TASK_ROOT / "component/revised_component_candidates.r2.jsonl"
ADDITION_CANDIDATES_R2_PATH = TASK_ROOT / "component/necessary_addition_candidates.r2.jsonl"
REVISED_RULES_R2_PATH = TASK_ROOT / "component/revised_control_rules.r2.jsonl"
FINAL_EDGE_CANDIDATES_R2_PATH = TASK_ROOT / "component/final_edge_candidates.r2.jsonl"
REVISED_SUPPLY_R2_PATH = TASK_ROOT / "component/revised_candidate_supply_matrix.r2.yaml"
REPAIR_ASSESSMENT_R2_PATH = TASK_ROOT / "component/targeted_repair_assessment.r2.yaml"
REVISED_AB_R2_PATH = TASK_ROOT / "ab/revised_ab_path_candidates.r2.jsonl"
TARGETED_REVIEW_PACKET_R2_PATH = TASK_ROOT / "review/targeted_repair_review_packet.r2.jsonl"
TARGETED_REVIEW_JOB_R2_PATH = TASK_ROOT / "review/targeted_repair_review_job.r2.yaml"
TARGETED_RESULT_R2_PATH = TASK_ROOT / "result/p2_targeted_repair_checkpoint_result.r2.yaml"


ALL_CP_IDS = tuple(f"CP{index:02d}" for index in range(1, 21))

SOURCE_EVIDENCE_REPAIRS: dict[str, dict[str, str]] = {
    "RCV2-002-TRIGGER-07-WORKMANSHIP-DETAIL-CHECK": {
        "field": "expression_content_kernel_candidate.business_judgment",
        "text": "做工可以给你看，寿命不能靠这一眼说满。",
        "repair_basis": "The cited judgment is the exact workmanship-versus-lifespan boundary that creates the bounded detail-check trigger.",
    },
    "RCV2-002-TRIGGER-09-OBSERVATION-VS-RECORD": {
        "field": "expression_content_kernel_candidate.business_judgment",
        "text": "把话分清并不会削弱内容，反而让顾客知道哪些可以当场看，哪些要等成分、工艺或测试记录来说。",
        "repair_basis": "The cited judgment explicitly separates present observation from claims that require records.",
    },
    "RCV2-002-TRIGGER-12-COLOR-AREA-IMBALANCE": {
        "field": "expression_content_kernel_candidate.business_judgment",
        "text": "暖不是把所有暖色都堆满，面积和位置也要有分寸。",
        "repair_basis": "The cited judgment explicitly names color area and position as the bounded display trigger.",
    },
}


def _spec(
    role: str,
    asset_class: str,
    profiles: list[str],
    function: str,
    inputs: list[str],
    facts: list[str],
    authorizations: list[str],
    gap: str,
    nearest_difference: str,
    *,
    parameter_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "role": role,
        "asset_class": asset_class,
        "profiles": profiles,
        "function": function,
        "inputs": inputs,
        "facts": facts,
        "authorizations": authorizations,
        "gap": gap,
        "nearest_difference": nearest_difference,
        "parameter_schema": parameter_schema,
    }


R2_ADDITION_SPECS: dict[str, dict[str, Any]] = {
    "G1V11-P2-SCENE-ORDERED-CRAFT-PROCESS": _spec(
        "scene", "scene_action_kernel", ["CP03"],
        "Bound a craft-process scene to one authorized work object, its complete step range, and the current process state.",
        ["process_scene_structure"],
        ["work_object", "process_start_state", "ordered_step_inventory", "process_end_or_unfinished_state"],
        ["craft_process_and_capture_scope"],
        "CP03 required a process scene rather than a generic inside-detail inspection.",
        "Unlike the inside-detail scene, this component requires a complete ordered process boundary and cannot be satisfied by an inspection-only view.",
    ),
    "G1V11-P2-VISUAL-CRAFT-STEP-STATE-SEQUENCE": _spec(
        "visual_beat", "visual_audio_grammar", ["CP03"],
        "Map each authorized craft step to its own visible before, action, and resulting-or-unfinished state without skipping causal steps.",
        ["step_state_visual_map"],
        ["ordered_step_inventory", "per_step_visible_input", "per_step_visible_action", "per_step_visible_state"],
        ["craft_step_visual_use_scope"],
        "CP03 needed visual proof of every causally necessary step.",
        "Unlike a detail-path visual, this mechanism is indexed by the complete process step inventory and fails when any causal step has no visual state.",
    ),
    "G1V11-P2-CAPTURE-CAUSAL-STEP-COVERAGE": _spec(
        "capture_instruction", "visual_audio_grammar", ["CP03"],
        "Require continuous capture coverage for every causally necessary craft step and reject inventory B-roll as process evidence.",
        ["causal_step_capture_plan"],
        ["ordered_step_inventory", "step_to_capture_segment_map", "continuity_breaks", "unfinished_step_state"],
        ["craft_actor_action_and_capture_scope"],
        "CP03 required a capture contract that closes omitted-action risk.",
        "Contact-sound synchronization can style one action; this mechanism proves complete step coverage and explicitly rejects unrelated stock footage.",
    ),
    "G1V11-P2-SCENE-SHARED-OBJECT-ROLE-HANDOFF": _spec(
        "scene", "scene_action_kernel", ["CP04"],
        "Anchor a collaboration scene in one real shared work object and an evidenced sequence of authorized role handoffs.",
        ["shared_object_handoff_scene"],
        ["shared_work_object", "participating_roles", "ordered_role_handoffs", "current_shared_state"],
        ["participant_authorizations", "shared_object_capture_scope"],
        "CP04 required a real multi-role collaboration scene rather than a single-role arrival scene.",
        "This mechanism requires multiple authorized roles acting on the same object; a generic arrival or inspection scene cannot satisfy it.",
    ),
    "G1V11-P2-ACTION-AUTHORIZED-ROLE-HANDOFF": _spec(
        "observable_action", "scene_action_kernel", ["CP04"],
        "Realize an ordered role-to-role handoff in which each visible action stays inside that role's supplied authority.",
        ["role_handoff_action_structure"],
        ["shared_work_object", "participating_roles", "role_action_assignments", "handoff_state_changes"],
        ["participant_authorizations", "role_action_and_capture_scopes"],
        "CP04 required actual collaboration actions with authority separation.",
        "A single garment-reset action has no role-to-action assignment or handoff state; this component makes both mandatory.",
    ),
    "G1V11-P2-JUDGMENT-ROLE-AUTHORITY-HANDOFF": _spec(
        "professional_judgment", "role_perspective_voice", ["CP04"],
        "Attribute each collaboration judgment to the exact role that owns it and expose the evidence and handoff boundary between roles.",
        ["role_authority_judgment_map"],
        ["participating_roles", "role_authority_boundaries", "role_specific_evidence", "handoff_decision_state"],
        ["participant_authorizations", "role_judgment_scopes"],
        "CP04 required multi-role authority and handoff judgment.",
        "A ledger reader can inspect fields but cannot assign judgment ownership across collaborating roles; this mechanism can.",
    ),
    "G1V11-P2-JUDGMENT-OBSERVATION-BASIS-LIMIT": _spec(
        "professional_judgment", "role_perspective_voice", ["CP06"],
        "Turn one supplied observable signal into an authority-bounded judgment with an explicit basis, limit, and unresolved condition.",
        ["observation_judgment_boundary"],
        ["observable_signal", "professional_basis", "judgment_scope", "unresolved_condition"],
        ["professional_role_judgment_scope"],
        "CP06 required observation-to-judgment-to-basis-and-limit semantics.",
        "Unlike generic ledger reading, this mechanism requires a real professional authority and a direct observation-to-basis relation.",
    ),
    "G1V11-P2-JUDGMENT-MATERIAL-STRUCTURE-USE": _spec(
        "professional_judgment", "role_perspective_voice", ["CP08"],
        "Relate an authorized material or construction observation to a bounded use implication while preserving what remains unproven.",
        ["material_structure_use_judgment"],
        ["material_or_structure_record", "visible_structure_observation", "bounded_use_implication", "unsupported_performance_boundary"],
        ["material_record_and_professional_judgment_scope"],
        "CP08 required material/structure-to-use judgment without whole-product endorsement.",
        "Unlike a generic evidence ledger, this mechanism encodes the micro-structure-to-use relation and its explicit non-generalization boundary.",
    ),
    "G1V11-P2-JUDGMENT-CONDITION-FIT-ALTERNATIVE": _spec(
        "professional_judgment", "role_perspective_voice", ["CP07", "CP09"],
        "Classify supplied conditions into fit, non-fit, missing-condition, and evidence-supported alternative paths without judging a person's body.",
        ["condition_fit_decision_map"],
        ["question_or_decision_context", "fit_conditions", "nonfit_conditions", "missing_conditions", "supported_alternatives"],
        ["diagnostic_or_advisory_judgment_scope"],
        "CP07 and CP09 required conditional diagnosis and boundary judgment.",
        "Task-friction judgment lacks fit/non-fit conditions and alternatives; this component makes those four branches explicit.",
    ),
    "G1V11-P2-CLOSING-CONDITION-OR-ALTERNATIVE": _spec(
        "closing", "narrative_operator", ["CP07", "CP09"],
        "Close with either a supported alternative or a precise missing-condition request, never a generic CTA or durability deferral.",
        ["condition_or_alternative_closure"],
        ["decision_state", "supported_alternative", "missing_condition_request", "claim_boundary"],
        ["advisory_closing_scope"],
        "CP07 and CP09 required condition-aware closure.",
        "The prior long-term-evidence closing only defers proof; this component closes a conditional decision with an alternative or exact information request.",
    ),
    "G1V11-P2-SCENE-RECORDED-TRADEOFF": _spec(
        "scene", "scene_action_kernel", ["CP11"],
        "Arrange an authorized decision record so the problem, options, selected and abandoned choices, constraint, and cost are all visible as fields.",
        ["tradeoff_record_scene"],
        ["decision_domain", "decision_problem", "options_considered", "selected_option", "abandoned_option", "constraint_or_cost"],
        ["domain_decision_record_use_scope"],
        "CP11 required a design-tradeoff scene rather than a generic multi-context product scene.",
        "This component is a field-complete decision-record scene, not a product use-context scene and not a trigger.",
    ),
    "G1V11-P2-TRIGGER-RECORDED-TRADEOFF": _spec(
        "trigger", "narrative_operator", ["CP11", "CP19"],
        "Trigger a tradeoff review only from a domain-scoped record containing options, selection, abandonment, constraint or cost, and current evidence boundary.",
        ["tradeoff_trigger_policy"],
        ["decision_domain", "decision_context", "options_considered", "selected_option", "abandoned_option", "constraint_or_cost", "current_evidence_boundary"],
        ["domain_decision_record_use_scope"],
        "CP11 and CP19 shared one parameterizable recorded-tradeoff trigger gap.",
        "This consolidates the rejected design/operating near-duplicate pair; decision_domain controls authorization without duplicating the mechanism.",
        parameter_schema={"decision_domain": ["PRODUCT_DESIGN", "BUSINESS_OPERATION"]},
    ),
    "G1V11-P2-CAPTURE-PRIVACY-SAFE-SERVICE-FEEDBACK": _spec(
        "capture_instruction", "visual_audio_grammar", ["CP16"],
        "Capture service need, action, feedback or unfinished state with customer identity exclusion and explicit consent/anonymization checks.",
        ["privacy_safe_service_capture_plan"],
        ["customer_task_truth", "service_action", "service_feedback_or_unfinished_state", "identity_exclusion_map"],
        ["customer_privacy_consent", "anonymization_approval", "service_capture_scope"],
        "CP16 required service feedback capture with privacy separation.",
        "A multi-role frame does not distinguish customer task, feedback, consent, or identity exclusion; this component does.",
    ),
    "G1V11-P2-SCENE-AUTHORIZED-LOCAL-CONTEXT": _spec(
        "scene", "scene_action_kernel", ["CP18"],
        "Anchor the scene in supplied real city, store, season or climate, and neighborhood or professional-crowd facts without adding local lore.",
        ["local_context_scene_structure"],
        ["real_city_and_store", "local_climate_or_season", "neighborhood_or_professional_crowd", "visible_store_context"],
        ["local_context_and_publication_scope"],
        "CP18 required actual local context rather than a generic arrival scene.",
        "This mechanism cannot run without explicit city/store and local-context facts, preventing a headquarters script from acquiring a place label.",
    ),
    "G1V11-P2-ACTION-AUTHORIZED-LOCAL-ROUTINE": _spec(
        "observable_action", "scene_action_kernel", ["CP18"],
        "Realize one supplied local store routine whose actor, object, place, time or season, and visible state are all authorized.",
        ["local_routine_action_structure"],
        ["real_city_and_store", "local_routine_actor", "local_routine_object", "local_climate_or_season", "observed_local_action_state"],
        ["local_actor_action_and_capture_scope"],
        "CP18 required a local routine action rather than an unrelated display move.",
        "A window-color move is not inherently local; this mechanism requires the local place/time/object bindings before realization.",
    ),
    "G1V11-P2-CLOSING-TRADEOFF-COST-BOUNDARY": _spec(
        "closing", "narrative_operator", ["CP19"],
        "Close a decision review by naming the recorded cost, current result boundary, and unresolved consequence without self-congratulation.",
        ["tradeoff_cost_closure"],
        ["abandoned_option", "constraint_or_cost", "current_result_or_open_state", "unresolved_consequence"],
        ["business_decision_closing_scope"],
        "CP19 required a tradeoff-specific closing.",
        "The prior long-term-proof deferral does not expose abandoned choice and cost; this component requires both.",
    ),
}


AXIS_OPERATOR_IDS = {
    "narrative_mechanism": "G1V11-P2-AXIS-NARRATIVE-MECHANISM",
    "information_order": "G1V11-P2-AXIS-INFORMATION-ORDER",
    "visual_subject": "G1V11-P2-AXIS-VISUAL-SUBJECT",
    "sound_subject": "G1V11-P2-AXIS-SOUND-SUBJECT",
    "rhythm": "G1V11-P2-AXIS-RHYTHM",
    "ending": "G1V11-P2-AXIS-ENDING-BOUNDARY",
}

AXIS_OPERATOR_FUNCTIONS = {
    "narrative_mechanism": "Select one approved narrative operator and bind its start state, transformation relation, and stop condition to the shared facts.",
    "information_order": "Declare a complete ordering of the same bound fact objects without deleting, adding, or changing their claim scope.",
    "visual_subject": "Select which already-authorized object or state leads each visual segment while preserving the shared fact set.",
    "sound_subject": "Select an authorized source sound, role voice, silence, or record cue as the sound lead without inventing an event.",
    "rhythm": "Assign structural segment cadence to the same bound events and observations without changing their chronology or truth status.",
    "ending": "Select a bounded ending action that preserves unresolved facts, authorization limits, and the profile's hard guards.",
}

for _axis, _component_id in AXIS_OPERATOR_IDS.items():
    R2_ADDITION_SPECS[_component_id] = _spec(
        f"{_axis}_operator",
        "ab_structural_operator",
        list(ALL_CP_IDS),
        AXIS_OPERATOR_FUNCTIONS[_axis],
        [f"{_axis}_parameter"],
        ["shared_fact_set_digest", "shared_claim_boundary_digest"],
        ["structural_authoring_scope"],
        f"All 20 products required a machine-consumed A/B {_axis} mechanism; r1 only attached labels to unrelated content components.",
        f"This operator changes only {_axis}; it cannot supply facts, authorization, or another structural axis.",
        parameter_schema={"axis": _axis, "value_type": "PROFILE_REVIEWED_SYMBOLIC_ENUM"},
    )


SELECTED_COMPONENTS = copy.deepcopy(R1_SELECTED_COMPONENTS)
SELECTED_COMPONENTS["CP03"].update(
    {
        "scene": "G1V11-P2-SCENE-ORDERED-CRAFT-PROCESS",
        "visual_beat": "G1V11-P2-VISUAL-CRAFT-STEP-STATE-SEQUENCE",
        "capture_instruction": "G1V11-P2-CAPTURE-CAUSAL-STEP-COVERAGE",
    }
)
SELECTED_COMPONENTS["CP04"].update(
    {
        "scene": "G1V11-P2-SCENE-SHARED-OBJECT-ROLE-HANDOFF",
        "observable_action": "G1V11-P2-ACTION-AUTHORIZED-ROLE-HANDOFF",
        "professional_judgment": "G1V11-P2-JUDGMENT-ROLE-AUTHORITY-HANDOFF",
    }
)
SELECTED_COMPONENTS["CP06"]["professional_judgment"] = (
    "G1V11-P2-JUDGMENT-OBSERVATION-BASIS-LIMIT"
)
for _cp_id in ("CP07", "CP09"):
    SELECTED_COMPONENTS[_cp_id]["professional_judgment"] = (
        "G1V11-P2-JUDGMENT-CONDITION-FIT-ALTERNATIVE"
    )
    SELECTED_COMPONENTS[_cp_id]["closing"] = (
        "G1V11-P2-CLOSING-CONDITION-OR-ALTERNATIVE"
    )
SELECTED_COMPONENTS["CP08"]["professional_judgment"] = (
    "G1V11-P2-JUDGMENT-MATERIAL-STRUCTURE-USE"
)
SELECTED_COMPONENTS["CP11"].update(
    {
        "scene": "G1V11-P2-SCENE-RECORDED-TRADEOFF",
        "trigger": "G1V11-P2-TRIGGER-RECORDED-TRADEOFF",
    }
)
SELECTED_COMPONENTS["CP16"]["capture_instruction"] = (
    "G1V11-P2-CAPTURE-PRIVACY-SAFE-SERVICE-FEEDBACK"
)
SELECTED_COMPONENTS["CP18"].update(
    {
        "scene": "G1V11-P2-SCENE-AUTHORIZED-LOCAL-CONTEXT",
        "observable_action": "G1V11-P2-ACTION-AUTHORIZED-LOCAL-ROUTINE",
    }
)
SELECTED_COMPONENTS["CP19"].update(
    {
        "trigger": "G1V11-P2-TRIGGER-RECORDED-TRADEOFF",
        "closing": "G1V11-P2-CLOSING-TRADEOFF-COST-BOUNDARY",
    }
)


CONTROL_RULE_REPAIR_IDS = frozenset(
    {
        "G1V11-CR-05-ONLY-SITE-DOABLE-ACTIONS",
        "G1V11-CR-06-ANONYMIZE-CLOTHING-STORY",
        "G1V11-CR-07-WORKMANSHIP-VS-LIFESPAN",
        "G1V11-CR-08-LIGHT-BEFORE-COLOR-CLAIM",
    }
)

CONTROL_SAFE_NONTRIGGERS = {
    "G1V11-CR-05-ONLY-SITE-DOABLE-ACTIONS": "An action explicitly assigned to the supplied actor and feasible under the supplied site conditions is allowed.",
    "G1V11-CR-06-ANONYMIZE-CLOTHING-STORY": "A non-personal product demonstration with no customer or person story does not trigger anonymization.",
    "G1V11-CR-07-WORKMANSHIP-VS-LIFESPAN": "A visible workmanship observation that makes no durability or lifespan inference is allowed.",
    "G1V11-CR-08-LIGHT-BEFORE-COLOR-CLAIM": "A color observation that carries its supplied lighting condition and makes no universal color claim is allowed.",
}


def _typed_compatibility() -> list[dict[str, str]]:
    return [
        {"rule": "exact_fact_object_binding_required", "fail_action": "STOP_OR_PROFILE_DEGRADE"},
        {"rule": "exact_authorization_object_binding_required", "fail_action": "STOP"},
        {"rule": "component_never_supplies_fact_or_authorization", "fail_action": "REJECT_BINDING"},
        {"rule": "claim_remains_inside_bound_fact_and_authorization_scope", "fail_action": "HOLD_OR_STOP"},
    ]


def build_revised_components_r2(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = build_r1_revised_components(root)
    changed: list[dict[str, Any]] = []
    for row in rows:
        component_id = str(row["component_id"])
        if component_id not in SOURCE_EVIDENCE_REPAIRS:
            continue
        repair = SOURCE_EVIDENCE_REPAIRS[component_id]
        old_digest = str(row["component_digest"])
        parent = row["provenance"]["parent_assets"][0]
        exact_text = repair["text"]
        parent["parent_field_path"] = repair["field"]
        parent["derivation_spans"] = [
            {
                "exact_text": exact_text,
                "occurrence_index": 0,
                "span_digest": hashlib.sha256(exact_text.encode("utf-8")).hexdigest(),
            }
        ]
        row["component_version"] = "v1.1-p2-r2"
        row["supersedes_targeted_repair_component_digest"] = old_digest
        row["revision_basis"] = list(row["revision_basis"]) + [
            "R1_INDEPENDENT_REVIEW_EXACT_SOURCE_SPAN_REPAIR",
            repair["repair_basis"],
        ]
        row["activation_proposal"] = "REVISED_R2_FOR_TARGETED_TWO_REVIEW"
        row["independent_review_state"] = "PENDING_TARGETED_R2_TWO_REVIEWS"
        row["component_digest"] = object_digest(row, "component_digest")
        changed.append(row)
    return rows, changed


def _design_component(
    component_id: str,
    spec: dict[str, Any],
    profile_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    profile_refs = [
        {
            "content_product_type_id": cp_id,
            "profile_digest": profile_by_id[cp_id]["profile_digest"],
            "required_role": (
                spec["role"]
                if not spec["role"].endswith("_operator")
                else "A_B_STRUCTURAL_AXIS"
            ),
            "hard_guards": profile_by_id[cp_id]["founder_hard_guards"],
        }
        for cp_id in spec["profiles"]
    ]
    row: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "component_id": component_id,
        "component_version": "v1.1-p2-r2-new",
        "component_role": spec["role"],
        "composition_asset_class": spec["asset_class"],
        "mechanism": {
            "kind": f"{spec['asset_class']}:{spec['role']}:domain_design_mechanism",
            "function": spec["function"],
            "actual_mechanism": spec["function"],
            "parameter_schema": spec["parameter_schema"],
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
        "role_authority_boundary": "runtime role and authority must be supplied as exact typed objects",
        "compatibility_rules": _typed_compatibility(),
        "forbidden_combinations": [
            "no_fake_fact",
            "no_source_surface_copy",
            "no_runtime_plan_authority",
            "no_cross_axis_substitution",
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
            "nearest_component_difference": spec["nearest_difference"],
            "source_text_span_required": False,
            "evidence_boundary": "PRODUCT_CONTRACT_DESIGN_ONLY_NO_FACT_AUTHORITY",
        },
        "historical_applicability_only": [],
        "proposed_applicability": spec["profiles"],
        "activation_proposal": "NECESSARY_R2_ADDITION_PENDING_TWO_REVIEWS",
        "new_generator_consumable": False,
        "independent_review_state": "PENDING_TARGETED_R2_TWO_REVIEWS",
        "readiness": {
            "generation_eligible": False,
            "runtime_ingest_ready": False,
            "production_ready": False,
        },
    }
    row["component_digest"] = object_digest(row, "component_digest")
    return row


def build_additions_r2(state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    retired = {
        "G1V11-P2-TRIGGER-DESIGN-TRADEOFF-RECORD",
        "G1V11-P2-TRIGGER-OPERATING-TRADEOFF",
    }
    prior = [
        row for row in build_r1_additions(state) if row["component_id"] not in retired
    ]
    profile_by_id = state["profile_by_id"]
    changed = [
        _design_component(component_id, spec, profile_by_id)
        for component_id, spec in sorted(R2_ADDITION_SPECS.items())
    ]
    return prior + changed, changed


def build_rules_r2(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = build_r1_revised_rules(root)
    changed: list[dict[str, Any]] = []
    for row in rows:
        rule_id = str(row["control_rule_id"])
        if rule_id not in CONTROL_RULE_REPAIR_IDS:
            continue
        old_digest = str(row["control_rule_digest"])
        row["control_rule_version"] = "v1.1-p2-r2"
        row["supersedes_targeted_repair_control_rule_digest"] = old_digest
        row["applicability_boundary"] = {
            "mode": "RISK_TRIGGER_DRIVEN_ALL_PROFILES",
            "applicable_profile_ids": list(ALL_CP_IDS),
            "requires_trigger_condition_match": True,
            "non_trigger_behavior": "ALLOW_WITHOUT_THIS_RULE_WHILE_OTHER_RULES_STILL_APPLY",
            "safe_non_trigger_example": CONTROL_SAFE_NONTRIGGERS[rule_id],
            "product_label_must_not_control_applicability": True,
        }
        row["false_positive_handling"] = CONTROL_SAFE_NONTRIGGERS[rule_id]
        row["independent_review_state"] = "PENDING_TARGETED_R2_TWO_REVIEWS"
        row["control_rule_digest"] = object_digest(row, "control_rule_digest")
        changed.append(row)
    return rows, changed


def _component_pool(
    root: Path,
    revised: list[dict[str, Any]],
    additions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    from p2_component_model import COMPONENT_CANDIDATES_PATH

    rows = {
        str(row["component_id"]): row
        for row in load_jsonl(root / COMPONENT_CANDIDATES_PATH)
    }
    rows.update({str(row["component_id"]): row for row in revised})
    rows.update({str(row["component_id"]): row for row in additions})
    return rows


def _catalog(material: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    return {
        "source": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["source_id"])}
            for row in material["sources"]
        ],
        "input": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["input_id"])}
            for row in material["component_inputs"]
        ],
        "fact": [
            {"slot_id": str(row["slot_id"]), "object_id": str(row["fact_id"])}
            for row in material["facts"]
        ],
        "authorization": [
            {
                "slot_id": str(row["slot_id"]),
                "object_id": str(row["authorization_id"]),
            }
            for row in material["authorizations"]
        ],
    }


def _binding_for(component: dict[str, Any], catalog: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    by_slot = {
        kind: {row["slot_id"]: row["object_id"] for row in entries}
        for kind, entries in catalog.items()
    }
    bindings: dict[str, list[dict[str, str]]] = {}
    for kind, field in (
        ("input", "required_input_slots"),
        ("fact", "required_fact_slots"),
        ("authorization", "required_authorization_slots"),
    ):
        slots = list(map(str, component.get(field, [])))
        require(set(slots).issubset(by_slot[kind]), "E_R2_BINDING_SLOT", str(component["component_id"]))
        bindings[kind] = [
            {"slot_id": slot_id, "object_id": by_slot[kind][slot_id]}
            for slot_id in slots
        ]
    return {
        "component_id": component["component_id"],
        "component_digest": component["component_digest"],
        "component_role": component["component_role"],
        "exact_typed_object_bindings": bindings,
        "binding_digest": digest_object(bindings),
    }


def _profile_binding(profile: dict[str, Any], catalog: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    requirements = profile_requirements(profile)
    by_slot = {
        kind: {row["slot_id"]: row["object_id"] for row in entries}
        for kind, entries in catalog.items()
    }
    bindings: dict[str, list[dict[str, str]]] = {}
    for kind in ("source", "fact", "authorization"):
        slots = list(map(str, requirements[kind]))
        require(set(slots).issubset(by_slot[kind]), "E_R2_PROFILE_BINDING", f"{profile['content_product_type_id']}:{kind}")
        bindings[kind] = [
            {"slot_id": slot_id, "object_id": by_slot[kind][slot_id]}
            for slot_id in slots
        ]
    return {"exact_profile_bindings": bindings, "binding_digest": digest_object(bindings)}


def _material_for_cp(
    profile: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]], list[str]]:
    cp_id = str(profile["content_product_type_id"])
    component_ids = list(SELECTED_COMPONENTS[cp_id].values()) + list(AXIS_OPERATOR_IDS.values())
    require(len(component_ids) == len(set(component_ids)), "E_R2_COMPONENT_DUPLICATE", cp_id)
    material = build_local_typed_material(
        profile, [component_by_id[component_id] for component_id in component_ids]
    )
    return material, _catalog(material), component_ids


def _role_intent(profile: dict[str, Any], role: str) -> str:
    operators = ", ".join(profile["narrative_constraints"]["allowed_narrative_operator_families"])
    guards = "; ".join(str(row["text"]) for row in profile["founder_hard_guards"])
    return (
        f"For {profile['content_product_type_id']} {profile['chinese_label']}, the {role} must realize "
        f"the product purpose through [{operators}] and remain inside [{guards}]. Role equality alone is not evidence."
    )


def build_edges_r2(
    state: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in state["profiles"]:
        cp_id = str(profile["content_product_type_id"])
        selected = SELECTED_COMPONENTS[cp_id]
        requirements = {str(row["role"]): row for row in profile["required_component_roles"]}
        require(set(selected) == set(requirements), "E_R2_SELECTED_ROLE_COVERAGE", cp_id)
        material, catalog, _ = _material_for_cp(profile, component_by_id)
        profile_binding = _profile_binding(profile, catalog)
        for role in requirements:
            component = component_by_id[selected[role]]
            require(component["component_role"] == role, "E_R2_SELECTED_ROLE", f"{cp_id}:{role}")
            binding = _binding_for(component, catalog)
            row: dict[str, Any] = {
                "schema_version": "v0.1",
                "task_id": TASK_ID,
                "edge_id": f"P2R2-EDGE-{cp_id}-{role}-01",
                "content_product_type_id": cp_id,
                "component_id": component["component_id"],
                "component_digest": component["component_digest"],
                "required_component_role": role,
                "selection_purpose": "MINIMUM_SEMANTIC_AND_TYPED_OBJECT_CLOSED_SUPPLY",
                "fit_basis": {
                    "product_label": profile["chinese_label"],
                    "business_purpose": profile["business_purpose"],
                    "exact_required_role": role,
                    "required_role_intent": _role_intent(profile, role),
                    "component_function": component["mechanism"].get("function"),
                    "component_nearest_difference": component.get("provenance", {}).get("nearest_component_difference"),
                    "profile_narrative_operators": profile["narrative_constraints"]["allowed_narrative_operator_families"],
                    "profile_hard_guards": profile["founder_hard_guards"],
                    "product_label_or_historical_applicability_is_not_evidence": True,
                },
                "shared_material_contract": {
                    "material_id": material["material_id"],
                    "material_digest": material["material_digest"],
                    "typed_object_catalog_digest": digest_object(catalog),
                },
                "component_exact_binding": binding,
                "profile_exact_binding": profile_binding,
                "forbidden_combinations": component["forbidden_combinations"],
                "missing_input_behavior": component["missing_input_behavior"],
                "historical_edge_reactivated": False,
                "proposed_new_edge": True,
                "active": False,
                "independent_review_state": "PENDING_TARGETED_R2_TWO_REVIEWS",
            }
            row["edge_digest"] = object_digest(row, "edge_digest")
            rows.append(row)
    return rows


def build_ab_paths_r2(
    state: dict[str, Any], component_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in state["profiles"]:
        cp_id = str(profile["content_product_type_id"])
        material, catalog, component_ids = _material_for_cp(profile, component_by_id)
        design = CP_PATH_DESIGNS[cp_id]
        lanes: dict[str, dict[str, Any]] = {}
        for lane_id, key in (("A", "a"), ("B", "b")):
            axis_values = dict(zip(AXIS_NAMES, design[key], strict=True))
            lane: dict[str, Any] = dict(axis_values)
            lane.update(
                {
                    "lane_id": lane_id,
                    "session_policy": f"INDEPENDENT_SESSION_{lane_id}",
                    "other_lane_visible": False,
                    "component_ids": component_ids,
                    "axis_operator_parameters": {
                        axis: {
                            "operator_component_id": AXIS_OPERATOR_IDS[axis],
                            "parameter_value": axis_values[axis],
                        }
                        for axis in AXIS_NAMES
                    },
                }
            )
            lanes[lane_id] = lane
        component_bindings = [
            _binding_for(component_by_id[component_id], catalog)
            for component_id in component_ids
        ]
        binding_by_id = {str(row["component_id"]): row for row in component_bindings}
        contracts = []
        for axis in AXIS_NAMES:
            operator_id = AXIS_OPERATOR_IDS[axis]
            contracts.append(
                {
                    "axis": axis,
                    "lane_a_value": lanes["A"][axis],
                    "lane_b_value": lanes["B"][axis],
                    "operator_component_id": operator_id,
                    "supporting_component_ids": [operator_id],
                    "operator_component_binding": binding_by_id[operator_id],
                    "operator_mechanism_digest": digest_object(component_by_id[operator_id]["mechanism"]),
                    "realization_target": f"/lane/{{lane_id}}/axes/{axis}",
                    "values_must_differ": True,
                    "same_fact_set_must_be_preserved": True,
                }
            )
        row: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "content_product_type_id": cp_id,
            "profile_digest": profile["profile_digest"],
            "shared_typed_material_contract": {
                "material_id": material["material_id"],
                "material_digest": material["material_digest"],
                "typed_object_catalog": catalog,
                "typed_object_catalog_digest": digest_object(catalog),
                "profile_exact_binding": _profile_binding(profile, catalog),
                "component_exact_bindings": component_bindings,
                "claim_boundary_digest": digest_object(material["claim_boundary"]),
                "same_exact_object_required_for_both_lanes": True,
            },
            "lane_a": lanes["A"],
            "lane_b": lanes["B"],
            "axis_realization_contracts": contracts,
            "observable_difference_axes": list(AXIS_NAMES),
            "observable_difference_axis_count": len(AXIS_NAMES),
            "structural_candidate_only": True,
            "content_quality_proven": False,
            "active": False,
            "independent_review_state": "PENDING_TARGETED_R2_TWO_REVIEWS",
        }
        row["path_digest"] = object_digest(row, "path_digest")
        rows.append(row)
    return rows


def build_supply_r2(state: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for profile in state["profiles"]:
        cp_id = str(profile["content_product_type_id"])
        role_entries = []
        for requirement in profile["required_component_roles"]:
            role = str(requirement["role"])
            matches = [
                row for row in edges
                if row["content_product_type_id"] == cp_id
                and row["required_component_role"] == role
            ]
            role_entries.append(
                {
                    "role": role,
                    "minimum": requirement["min_count"],
                    "candidate_count": len(matches),
                    "candidate_component_ids": [row["component_id"] for row in matches],
                    "complete_pending_targeted_review": len(matches) >= requirement["min_count"],
                }
            )
        entries.append(
            {
                "content_product_type_id": cp_id,
                "candidate_supply_complete": all(row["complete_pending_targeted_review"] for row in role_entries),
                "approved_supply_complete": False,
                "required_roles": role_entries,
            }
        )
    document: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "candidate_complete_profile_count": sum(row["candidate_supply_complete"] for row in entries),
        "approved_complete_profile_count": 0,
        "entries": entries,
    }
    document["matrix_digest"] = object_digest(document, "matrix_digest")
    return {"revised_candidate_supply_matrix": document}


def _packet_item(prefix: str, object_type: str, subject: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_item_id": prefix,
        "object_type": object_type,
        "review_subject": subject,
        "required_review_roles": [
            "PRIMARY_CONTENT_VALUE_COMPOSABILITY",
            "SECONDARY_PROVENANCE_FACT_AUTHORIZATION",
        ],
        "prefilled_score": None,
        "prefilled_decision": None,
    }


def build_review_packet_r2(
    changed_sources: list[dict[str, Any]],
    changed_additions: list[dict[str, Any]],
    changed_rules: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    paths: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [
        _packet_item(
            f"P2R2-COMPONENT-{row['component_id']}",
            "REVISED_OR_NECESSARY_COMPONENT",
            row,
        )
        for row in changed_sources + changed_additions
    ]
    rows.extend(
        _packet_item(
            f"P2R2-CONTROL-{row['control_rule_id']}",
            "REVISED_CONTROL_RULE_SEPARATION",
            row,
        )
        for row in changed_rules
    )
    rows.extend(
        _packet_item(f"P2R2-{row['edge_id']}", "REVISED_COMPONENT_CP_EDGE", row)
        for row in edges
    )
    rows.extend(
        _packet_item(
            f"P2R2-AB-{row['content_product_type_id']}",
            "REVISED_AB_STRUCTURAL_PATH_CAPABILITY",
            row,
        )
        for row in paths
    )
    return rows


def build_targeted_repair_r2_documents(root: Path) -> dict[Path, bytes]:
    state = source_state(root)
    revised, changed_sources = build_revised_components_r2(root)
    additions, changed_additions = build_additions_r2(state)
    rules, changed_rules = build_rules_r2(root)
    component_by_id = _component_pool(root, revised, additions)
    edges = build_edges_r2(state, component_by_id)
    paths = build_ab_paths_r2(state, component_by_id)
    supply = build_supply_r2(state, edges)
    packet = build_review_packet_r2(changed_sources, changed_additions, changed_rules, edges, paths)
    packet_bytes = jsonl_bytes(packet)
    packet_sha = sha256_bytes(packet_bytes)
    assessment: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "historical_inventory": 86,
        "historical_inventory_target_used": False,
        "r1_failure_evidence_preserved": True,
        "r1_reviewer_blockers_closed": [
            "EXACT_COMPONENT_SLOT_TO_TYPED_OBJECT_BINDING",
            "MECHANISM_BACKED_A_B_AXIS_REALIZATION",
            "THREE_EXACT_SOURCE_SPAN_REPAIRS",
            "TRADEOFF_TRIGGER_NEAR_DUPLICATE_CONSOLIDATION",
            "RISK_TRIGGERED_CONTROL_SCOPE",
            "PRODUCT_SEMANTIC_EDGE_REPLACEMENTS",
        ],
        "full_revised_source_component_count": len(revised),
        "r2_changed_source_component_count": len(changed_sources),
        "full_necessary_addition_count": len(additions),
        "r2_new_addition_count": len(changed_additions),
        "r2_axis_operator_count": len(AXIS_OPERATOR_IDS),
        "replacement_minimum_edge_count": len(edges),
        "revised_ab_path_count": len(paths),
        "number_target_used": False,
    }
    assessment["assessment_digest"] = object_digest(assessment, "assessment_digest")
    job: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "prompt_revision": "r2",
        "checkpoint_state": "PENDING_TARGETED_R2_TWO_REVIEW",
        "review_packet_path": TARGETED_REVIEW_PACKET_R2_PATH.as_posix(),
        "review_packet_sha256": packet_sha,
        "packet_item_count": len(packet),
        "packet_item_counts": dict(Counter(row["object_type"] for row in packet)),
        "reviewer_policy": {
            "reuse_original_identity_isolated_primary_and_secondary_reviewers": True,
            "review_actual_payload_and_exact_bindings": True,
            "r1_failure_records_remain_visible_and_immutable": True,
            "self_approval_allowed": False,
        },
        "activation_before_matching_approvals_allowed": False,
    }
    job["review_job_digest"] = object_digest(job, "review_job_digest")
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "checkpoint_state": "PENDING_TARGETED_R2_TWO_REVIEW",
        "p2_complete": False,
        "p3_allowed": False,
        "review_packet_sha256": packet_sha,
        "review_item_count": len(packet),
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
        REVISED_COMPONENTS_R2_PATH: jsonl_bytes(revised),
        ADDITION_CANDIDATES_R2_PATH: jsonl_bytes(additions),
        REVISED_RULES_R2_PATH: jsonl_bytes(rules),
        FINAL_EDGE_CANDIDATES_R2_PATH: jsonl_bytes(edges),
        REVISED_SUPPLY_R2_PATH: yaml_bytes(supply),
        REPAIR_ASSESSMENT_R2_PATH: yaml_bytes({"targeted_repair_assessment": assessment}),
        REVISED_AB_R2_PATH: jsonl_bytes(paths),
        TARGETED_REVIEW_PACKET_R2_PATH: packet_bytes,
        TARGETED_REVIEW_JOB_R2_PATH: yaml_bytes({"targeted_repair_review_job": job}),
        TARGETED_RESULT_R2_PATH: yaml_bytes({"p2_targeted_repair_checkpoint_result": result}),
    }


def validate_targeted_repair_r2_documents(documents: dict[Path, bytes]) -> None:
    def rows(path: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in documents[path].decode("utf-8").splitlines()
            if line
        ]

    revised = rows(REVISED_COMPONENTS_R2_PATH)
    additions = rows(ADDITION_CANDIDATES_R2_PATH)
    rules = rows(REVISED_RULES_R2_PATH)
    edges = rows(FINAL_EDGE_CANDIDATES_R2_PATH)
    paths = rows(REVISED_AB_R2_PATH)
    packet = rows(TARGETED_REVIEW_PACKET_R2_PATH)
    result = yaml.safe_load(documents[TARGETED_RESULT_R2_PATH])[
        "p2_targeted_repair_checkpoint_result"
    ]
    require(len(revised) == 19, "E_R2_REVISED_COUNT")
    require(len(additions) == 7 + len(R2_ADDITION_SPECS), "E_R2_ADDITION_COUNT")
    require(len(rules) == 8, "E_R2_RULE_COUNT")
    require(len(edges) == 85, "E_R2_EDGE_COUNT")
    require(len(paths) == 20, "E_R2_PATH_COUNT")
    require(len(packet) == 3 + len(R2_ADDITION_SPECS) + 4 + 85 + 20, "E_R2_PACKET_COUNT")
    require(result["p2_complete"] is False and result["p3_allowed"] is False, "E_R2_EARLY_ACTIVATION")
    require(
        result["core_numbers"]
        == {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "E_R2_CORE_NUMBERS",
    )
    require(not any(result["readiness"].values()), "E_R2_READINESS")
    require(
        all(row["component_digest"] == object_digest(row, "component_digest") for row in revised + additions),
        "E_R2_COMPONENT_DIGEST",
    )
    require(
        all(row["control_rule_digest"] == object_digest(row, "control_rule_digest") for row in rules),
        "E_R2_RULE_DIGEST",
    )
    require(
        all(row["edge_digest"] == object_digest(row, "edge_digest") for row in edges),
        "E_R2_EDGE_DIGEST",
    )
    require(
        all(row["path_digest"] == object_digest(row, "path_digest") for row in paths),
        "E_R2_PATH_DIGEST",
    )
    require(
        all(row["component_exact_binding"]["exact_typed_object_bindings"]["fact"] for row in edges),
        "E_R2_EDGE_FACT_BINDING",
    )
    require(
        all(row["component_exact_binding"]["exact_typed_object_bindings"]["authorization"] for row in edges),
        "E_R2_EDGE_AUTH_BINDING",
    )
    require(
        all(
            len(row["axis_realization_contracts"]) == len(AXIS_NAMES)
            and all(
                contract["supporting_component_ids"] == [contract["operator_component_id"]]
                for contract in row["axis_realization_contracts"]
            )
            for row in paths
        ),
        "E_R2_AXIS_OPERATOR_CLOSURE",
    )
    require(
        all(
            set(row["lane_a"]["component_ids"]) == set(row["lane_b"]["component_ids"])
            and row["lane_a"]["session_policy"] != row["lane_b"]["session_policy"]
            for row in paths
        ),
        "E_R2_LANE_ISOLATION",
    )
    path_by_cp = {str(row["content_product_type_id"]): row for row in paths}
    for edge in edges:
        cp_id = str(edge["content_product_type_id"])
        path = path_by_cp[cp_id]
        contract = path["shared_typed_material_contract"]
        require(
            edge["shared_material_contract"]["material_digest"]
            == contract["material_digest"],
            "E_R2_EDGE_MATERIAL_DIGEST",
            str(edge["edge_id"]),
        )
        require(
            edge["shared_material_contract"]["typed_object_catalog_digest"]
            == contract["typed_object_catalog_digest"]
            == digest_object(contract["typed_object_catalog"]),
            "E_R2_EDGE_CATALOG_DIGEST",
            str(edge["edge_id"]),
        )
        binding = next(
            row
            for row in contract["component_exact_bindings"]
            if row["component_id"] == edge["component_id"]
        )
        require(
            edge["component_exact_binding"] == binding,
            "E_R2_EDGE_COMPONENT_BINDING",
            str(edge["edge_id"]),
        )
        require(
            edge["profile_exact_binding"] == contract["profile_exact_binding"],
            "E_R2_EDGE_PROFILE_BINDING",
            str(edge["edge_id"]),
        )
    corrected_by_id = {str(row["component_id"]): row for row in revised}
    for component_id, repair in SOURCE_EVIDENCE_REPAIRS.items():
        parent = corrected_by_id[component_id]["provenance"]["parent_assets"][0]
        span = parent["derivation_spans"][0]
        require(parent["parent_field_path"] == repair["field"], "E_R2_SOURCE_FIELD", component_id)
        require(span["exact_text"] == repair["text"], "E_R2_SOURCE_TEXT", component_id)
        require(
            span["span_digest"] == hashlib.sha256(repair["text"].encode("utf-8")).hexdigest(),
            "E_R2_SOURCE_SPAN_DIGEST",
            component_id,
        )
    addition_ids = {str(row["component_id"]) for row in additions}
    require(
        "G1V11-P2-TRIGGER-DESIGN-TRADEOFF-RECORD" not in addition_ids
        and "G1V11-P2-TRIGGER-OPERATING-TRADEOFF" not in addition_ids
        and "G1V11-P2-TRIGGER-RECORDED-TRADEOFF" in addition_ids,
        "E_R2_TRADEOFF_CONSOLIDATION",
    )
    require(
        all(
            row["applicability_boundary"]["applicable_profile_ids"] == list(ALL_CP_IDS)
            and row["applicability_boundary"]["requires_trigger_condition_match"] is True
            for row in rules
            if row["control_rule_id"] in CONTROL_RULE_REPAIR_IDS
        ),
        "E_R2_CONTROL_SCOPE",
    )
    supply = yaml.safe_load(documents[REVISED_SUPPLY_R2_PATH])[
        "revised_candidate_supply_matrix"
    ]
    require(supply["candidate_complete_profile_count"] == 20, "E_R2_SUPPLY")


__all__ = [
    "ADDITION_CANDIDATES_R2_PATH",
    "FINAL_EDGE_CANDIDATES_R2_PATH",
    "REVISED_AB_R2_PATH",
    "REVISED_COMPONENTS_R2_PATH",
    "REVISED_RULES_R2_PATH",
    "TARGETED_REVIEW_PACKET_R2_PATH",
    "TARGETED_RESULT_R2_PATH",
    "build_targeted_repair_r2_documents",
    "validate_targeted_repair_r2_documents",
]
