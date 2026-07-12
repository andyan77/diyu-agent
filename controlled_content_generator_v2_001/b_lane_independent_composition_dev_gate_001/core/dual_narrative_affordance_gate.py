#!/usr/bin/env python3
"""Decide whether one evidence pack can support two independent narratives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


PAIR_READY = "PAIR_READY"
SINGLE_LANE_ONLY = "SINGLE_LANE_ONLY"
REQUEST_MORE_MATERIAL = "REQUEST_MORE_MATERIAL"
LANES = ("A", "B")
SEMANTIC_FIELDS = (
    "primary_audience_question",
    "observation_mission",
    "center_of_gravity",
    "causal_path",
)


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return set()
    return {str(item) for item in value if str(item)}


def _lane(pack: Mapping[str, Any], lane_id: str) -> Mapping[str, Any]:
    lane_specs = pack.get("lane_specs")
    if not isinstance(lane_specs, Mapping):
        return {}
    lane = lane_specs.get(lane_id)
    return lane if isinstance(lane, Mapping) else {}


def dual_narrative_affordance_gate(
    material_pack: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a deterministic routing decision without creating audience text."""

    reasons: list[str] = []
    atom_ids = {
        str(atom.get("atom_id"))
        for atom in material_pack.get("source_atoms", [])
        if isinstance(atom, Mapping) and atom.get("atom_id")
    }
    shared = _string_set(material_pack.get("shared_truth_anchor_refs"))
    invariants = material_pack.get("product_invariants")
    if not atom_ids:
        reasons.append("MISSING_SOURCE_ATOMS")
    if not shared or not shared.issubset(atom_ids):
        reasons.append("INVALID_SHARED_TRUTH_ANCHORS")
    if not isinstance(invariants, list) or not invariants:
        reasons.append("MISSING_PRODUCT_INVARIANTS")
    if str(material_pack.get("profile_id")) != str(
        profile.get("content_product_type_id")
    ):
        reasons.append("PROFILE_MISMATCH")

    lane_evidence: dict[str, set[str]] = {}
    lane_exclusive: dict[str, set[str]] = {}
    for lane_id in LANES:
        lane = _lane(material_pack, lane_id)
        for field in SEMANTIC_FIELDS:
            if not str(lane.get(field, "")).strip():
                reasons.append(f"{lane_id}_MISSING_{field.upper()}")
        evidence = _string_set(lane.get("evidence_atom_refs"))
        exclusive = _string_set(lane.get("exclusive_atom_refs"))
        obligations = lane.get("lane_story_obligations")
        if not evidence or not evidence.issubset(atom_ids):
            reasons.append(f"{lane_id}_INVALID_EVIDENCE_REFS")
        if len(exclusive) < 2 or not exclusive.issubset(evidence):
            reasons.append(f"{lane_id}_INSUFFICIENT_EXCLUSIVE_ATOMS")
        if not isinstance(obligations, list) or len(obligations) < 2:
            reasons.append(f"{lane_id}_INSUFFICIENT_EXCLUSIVE_OBLIGATIONS")
        if lane.get("independently_delivers_profile_core") is not True:
            reasons.append(f"{lane_id}_DOES_NOT_DELIVER_PROFILE_CORE")
        lane_evidence[lane_id] = evidence
        lane_exclusive[lane_id] = exclusive

    for field in SEMANTIC_FIELDS:
        left = str(_lane(material_pack, "A").get(field, "")).strip()
        right = str(_lane(material_pack, "B").get(field, "")).strip()
        if left and left == right:
            reasons.append(f"SEMANTIC_FIELD_NOT_DIVERGENT:{field}")
    if lane_exclusive.get("A", set()).intersection(lane_exclusive.get("B", set())):
        reasons.append("LANE_EXCLUSIVE_ATOMS_OVERLAP")

    non_anchor_a = lane_evidence.get("A", set()).difference(shared)
    non_anchor_b = lane_evidence.get("B", set()).difference(shared)
    union = non_anchor_a.union(non_anchor_b)
    jaccard = len(non_anchor_a.intersection(non_anchor_b)) / max(1, len(union))
    if jaccard > 0.50:
        reasons.append("NON_ANCHOR_ATOM_JACCARD_ABOVE_WARNING_LIMIT")

    declared_route = str(material_pack.get("declared_affordance", PAIR_READY))
    if reasons:
        decision = (
            SINGLE_LANE_ONLY
            if declared_route == SINGLE_LANE_ONLY
            else REQUEST_MORE_MATERIAL
        )
    else:
        decision = PAIR_READY
    return {
        "decision": decision,
        "reason_codes": sorted(set(reasons)),
        "shared_truth_anchor_count": len(shared),
        "lane_A_exclusive_atom_count": len(lane_exclusive.get("A", set())),
        "lane_B_exclusive_atom_count": len(lane_exclusive.get("B", set())),
        "non_anchor_atom_jaccard_ratio": round(jaccard, 6),
        "audience_text_created": False,
        "runtime_authorization_changed": False,
    }


if __name__ == "__main__":
    raise SystemExit(2)
