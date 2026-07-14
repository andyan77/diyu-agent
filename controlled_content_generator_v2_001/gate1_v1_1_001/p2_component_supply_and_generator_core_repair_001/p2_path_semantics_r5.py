#!/usr/bin/env python3
"""Build profile/lane bindings for the small reusable P2 r5 operators."""

from __future__ import annotations

from typing import Any

from p2_axis_semantics_r4 import SEMANTIC_LANE_PLANS


AXIS_NAMES = (
    "narrative_mechanism",
    "information_order",
    "visual_subject",
    "sound_subject",
    "rhythm",
    "ending",
)


def _beat_groups(node_count: int, lane_id: str) -> list[list[int]]:
    """Return lane-specific partitions over information-node positions."""

    if lane_id == "A":
        return [[index] for index in range(node_count)]
    groups: list[list[int]] = []
    index = 0
    while index < node_count:
        width = 2 if index + 1 < node_count else 1
        groups.append(list(range(index, index + width)))
        index += width
    return groups


def _ending_actions(
    lane_id: str,
    boundary_slots: list[str],
    closure_mode: str,
    next_step_policy: str,
) -> list[dict[str, Any]]:
    """Represent closure as executable action topology, not policy labels alone."""

    if lane_id == "A":
        return [
            {
                "action_type": "BOUND_CURRENT_EVIDENCE",
                "fact_slots": boundary_slots,
                "closure_mode": closure_mode,
            },
            {
                "action_type": "PROHIBIT_UNSUPPORTED_EXTENSION",
                "policy": next_step_policy,
            },
        ]
    return [
        {
            "action_type": "MARK_UNRESOLVED_BOUNDARY",
            "fact_slots": boundary_slots,
            "closure_mode": closure_mode,
        },
        {
            "action_type": "REQUEST_EXACT_NEXT_EVIDENCE",
            "policy": next_step_policy,
        },
        {"action_type": "STOP_PENDING_BOUND_INPUT"},
    ]


def lane_axis_programs(profile_id: str, lane_id: str) -> dict[str, dict[str, Any]]:
    """Translate one reviewed R4 lane design into path-owned R5 programs."""

    plan = SEMANTIC_LANE_PLANS[profile_id][lane_id]
    sequence = list(map(str, plan["sequence"]))
    ending_slots = list(map(str, plan["ending_slots"]))
    return {
        "information_order": {
            "operator_primitive": "ORDER_EXACT_FACT_NODES",
            "ordered_fact_slots": sequence,
        },
        "narrative_mechanism": {
            "operator_primitive": "LINK_INFORMATION_NODES",
            "information_order_dependency": "information_order",
            "relation_mode": str(plan["relation"]),
        },
        "visual_subject": {
            "operator_primitive": "FOCUS_EXACT_FACT_ROLES",
            "lead_fact_slot": str(plan["visual_lead"]),
            "supporting_fact_slots": list(map(str, plan["visual_support"])),
            "focus_mode": str(plan["visual_mode"]),
        },
        "sound_subject": {
            "operator_primitive": "MAP_AUTHORIZED_FACT_CUES",
            "cue_fact_slots": list(map(str, plan["sound_slots"])),
            "cue_source_class": str(plan["sound_mode"]),
            "missing_source_behavior": "SILENCE_OR_STOP",
        },
        "rhythm": {
            "operator_primitive": "GROUP_INFORMATION_NODE_POSITIONS",
            "information_order_dependency": "information_order",
            "beat_node_position_groups": _beat_groups(len(sequence), lane_id),
            "cadence_mode": str(plan["cadence"]),
        },
        "ending": {
            "operator_primitive": "EMIT_BOUNDARY_ACTION_NODES",
            "boundary_fact_slots": ending_slots,
            "action_nodes": _ending_actions(
                lane_id,
                ending_slots,
                str(plan["closure_mode"]),
                str(plan["next_step_policy"]),
            ),
            "claims_resolved": False,
            "may_add_commitment": False,
        },
    }


__all__ = ["AXIS_NAMES", "lane_axis_programs"]
