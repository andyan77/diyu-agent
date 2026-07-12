#!/usr/bin/env python3
"""Validate semantic and visible divergence before authoring begins."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


SEMANTIC_FIELDS = (
    "primary_audience_question",
    "observation_mission",
    "center_of_gravity",
    "causal_path",
)
STYLE_AXES = (
    "information_order",
    "narrative_distance",
    "language_register",
    "sentence_rhythm",
    "visual_subject",
    "shot_continuity",
    "sound_subject",
    "ending_mode",
    "CTA_policy",
)


def _strings(value: Any) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return set()
    return {str(item) for item in value if str(item)}


def _selected_style(plan: Mapping[str, Any], axis: str) -> str:
    styles = plan.get("style_realization_plan")
    if not isinstance(styles, Mapping):
        return ""
    item = styles.get(axis)
    if not isinstance(item, Mapping):
        return ""
    return str(item.get("selected_value", "")).strip()


def pair_plan_divergence_gate(
    lane_a_plan: Mapping[str, Any],
    lane_b_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed when two plans differ only by labels or style declarations."""

    errors: list[str] = []
    contract_a = lane_a_plan.get("semantic_divergence_contract")
    contract_b = lane_b_plan.get("semantic_divergence_contract")
    if not isinstance(contract_a, Mapping) or not isinstance(contract_b, Mapping):
        return {
            "pass": False,
            "error_codes": ["MISSING_SEMANTIC_DIVERGENCE_CONTRACT"],
            "semantic_difference_axis_count": 0,
            "visible_difference_axis_count": 0,
        }

    semantic_differences = 0
    for field in SEMANTIC_FIELDS:
        left = str(contract_a.get(field, "")).strip()
        right = str(contract_b.get(field, "")).strip()
        different = bool(left and right and left != right)
        semantic_differences += int(different)
        if not different:
            errors.append(f"SEMANTIC_AXIS_NOT_DIFFERENT:{field}")

    evidence_a = _strings(lane_a_plan.get("selected_evidence_atom_refs"))
    evidence_b = _strings(lane_b_plan.get("selected_evidence_atom_refs"))
    if evidence_a != evidence_b:
        semantic_differences += 1
    else:
        errors.append("SELECTED_EVIDENCE_SUBSET_IDENTICAL")

    obligations_a = _strings(lane_a_plan.get("lane_story_obligation_ids"))
    obligations_b = _strings(lane_b_plan.get("lane_story_obligation_ids"))
    if len(obligations_a) < 2 or len(obligations_b) < 2:
        errors.append("LANE_EXCLUSIVE_OBLIGATIONS_INSUFFICIENT")
    if obligations_a == obligations_b:
        errors.append("LANE_STORY_OBLIGATIONS_IDENTICAL")
    else:
        semantic_differences += 1

    visible_differences = sum(
        _selected_style(lane_a_plan, axis) != _selected_style(lane_b_plan, axis)
        and bool(_selected_style(lane_a_plan, axis))
        and bool(_selected_style(lane_b_plan, axis))
        for axis in STYLE_AXES
    )
    if visible_differences < 4:
        errors.append("VISIBLE_DIFFERENCE_AXIS_COUNT_BELOW_4")
    if semantic_differences < 2:
        errors.append("SEMANTIC_DIFFERENCE_AXIS_COUNT_BELOW_2")

    if lane_a_plan.get("profile_id") != lane_b_plan.get("profile_id"):
        errors.append("PROFILE_MISMATCH")
    if lane_a_plan.get("voice_lane") != "A" or lane_b_plan.get("voice_lane") != "B":
        errors.append("LANE_IDENTITY_MISMATCH")

    return {
        "pass": not errors,
        "error_codes": sorted(set(errors)),
        "different_primary_audience_question": (
            contract_a.get("primary_audience_question")
            != contract_b.get("primary_audience_question")
        ),
        "different_observation_mission": (
            contract_a.get("observation_mission")
            != contract_b.get("observation_mission")
        ),
        "different_center_of_gravity": (
            contract_a.get("center_of_gravity") != contract_b.get("center_of_gravity")
        ),
        "different_causal_path": contract_a.get("causal_path")
        != contract_b.get("causal_path"),
        "lane_exclusive_obligation_count_each": {
            "A": len(obligations_a),
            "B": len(obligations_b),
        },
        "visible_difference_axis_count": visible_differences,
        "semantic_difference_axis_count": semantic_differences,
        "creative_author_invocation_allowed": not errors,
    }


if __name__ == "__main__":
    raise SystemExit(2)
