#!/usr/bin/env python3
"""Project shared evidence into two independent, structure-only ORCH plans."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from controlled_content_generator_v2_001.b_lane_independent_composition_dev_gate_001.core.dual_narrative_affordance_gate import (
    PAIR_READY,
    dual_narrative_affordance_gate,
)


TASK_ID = "CONTROLLED_V2_B_LANE_INDEPENDENT_COMPOSITION_DEV_GATE_001"
LANES = ("A", "B")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(item) for item in value if str(item)]


def _lane_spec(material_pack: Mapping[str, Any], lane_id: str) -> Mapping[str, Any]:
    lane_specs = material_pack.get("lane_specs")
    if not isinstance(lane_specs, Mapping):
        raise ValueError("material pack is missing lane_specs")
    lane = lane_specs.get(lane_id)
    if not isinstance(lane, Mapping):
        raise ValueError(f"material pack is missing lane {lane_id}")
    return lane


def _project_pack(material_pack: Mapping[str, Any], lane_id: str) -> dict[str, Any]:
    lane = _lane_spec(material_pack, lane_id)
    allowed_refs = set(_string_list(material_pack.get("shared_truth_anchor_refs")))
    allowed_refs.update(_string_list(lane.get("evidence_atom_refs")))
    source_atoms = [
        dict(atom)
        for atom in material_pack.get("source_atoms", [])
        if isinstance(atom, Mapping) and str(atom.get("atom_id")) in allowed_refs
    ]
    if {str(atom["atom_id"]) for atom in source_atoms} != allowed_refs:
        raise ValueError(f"lane {lane_id} evidence projection contains unknown refs")
    projected: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "namespace": material_pack["namespace"],
        "material_pack_id": f"{material_pack['material_pack_id']}-LANE-{lane_id}-PROJECTION",
        "profile_id": material_pack["profile_id"],
        "qualification_only": True,
        "source_material_pack_ref": material_pack["material_pack_id"],
        "source_atoms": source_atoms,
        "shared_truth_anchor_refs": _string_list(
            material_pack.get("shared_truth_anchor_refs")
        ),
        "lane_exclusive_atom_refs": _string_list(lane.get("exclusive_atom_refs")),
        "authorization_boundary": dict(material_pack["authorization_boundary"]),
        "role_boundary": dict(material_pack["role_boundary"]),
        "creative_license": list(material_pack["creative_license"]),
        "other_lane_evidence_visible": False,
        "other_lane_plan_visible": False,
        "runtime_consumable": False,
        "publishable": False,
    }
    projected["material_pack_digest"] = digest_object(projected)
    return projected


def _obligations(
    material_pack: Mapping[str, Any], lane: Mapping[str, Any]
) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    for item in material_pack.get("product_invariants", []):
        if isinstance(item, Mapping):
            obligations.append(dict(item))
    for item in lane.get("lane_story_obligations", []):
        if isinstance(item, Mapping):
            obligations.append(dict(item))
    return obligations


def _build_plan(
    material_pack: Mapping[str, Any],
    projected_pack: Mapping[str, Any],
    lane_id: str,
) -> dict[str, Any]:
    lane = _lane_spec(material_pack, lane_id)
    namespace = str(material_pack["namespace"])
    profile_id = str(material_pack["profile_id"])
    stem = f"{namespace}-{profile_id}-{lane_id}-001"
    plan: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "namespace": namespace,
        "plan_id": f"ORCH-{stem}-PLAN",
        "assignment_id": f"{stem}-ASSIGN",
        "canonicality_scope": "QUALIFICATION_DEV_CASE_LOCAL",
        "plan_mode": "PAIR_INDEPENDENT_SYNTHETIC_QUALIFICATION",
        "writer": "ORCH",
        "profile_id": profile_id,
        "voice_lane": lane_id,
        "material_pack_ref": projected_pack["material_pack_id"],
        "material_pack_digest": projected_pack["material_pack_digest"],
        "product_invariants": [
            dict(item) for item in material_pack["product_invariants"]
        ],
        "lane_story_obligations": [
            dict(item) for item in lane["lane_story_obligations"]
        ],
        "lane_story_obligation_ids": [
            str(item["obligation_id"]) for item in lane["lane_story_obligations"]
        ],
        "required_obligations": _obligations(material_pack, lane),
        "selected_evidence_atom_refs": _string_list(lane["evidence_atom_refs"]),
        "lane_exclusive_atom_refs": _string_list(lane["exclusive_atom_refs"]),
        "semantic_divergence_contract": {
            "primary_audience_question": lane["primary_audience_question"],
            "observation_mission": lane["observation_mission"],
            "center_of_gravity": lane["center_of_gravity"],
            "causal_path": lane["causal_path"],
        },
        "narrative_operator": dict(lane["narrative_operator"]),
        "output_contract": dict(lane["output_contract"]),
        "style_realization_plan": {
            str(axis): dict(item)
            for axis, item in lane["style_realization_plan"].items()
        },
        "other_lane_plan_visible": False,
        "other_lane_evidence_visible": False,
        "publishable": False,
        "runtime_consumable": False,
        "production_consumable": False,
        "generator_qualified": False,
        "synthetic_bindings": {
            "fixture_only": True,
            "verified_brand_fact_count": 0,
            "runtime_authorization_count": 0,
        },
    }
    plan["plan_digest"] = digest_object(plan)
    return plan


def build_pair_plans(
    material_pack: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Create two plans only when material affordance is independently proven."""

    affordance = dual_narrative_affordance_gate(material_pack, profile)
    if affordance["decision"] != PAIR_READY:
        return {
            "affordance": affordance,
            "projected_material_packs": [],
            "plans": [],
            "audience_text_created": False,
        }
    projected = {lane_id: _project_pack(material_pack, lane_id) for lane_id in LANES}
    plans = [
        _build_plan(material_pack, projected[lane_id], lane_id) for lane_id in LANES
    ]
    return {
        "affordance": affordance,
        "projected_material_packs": [projected[lane_id] for lane_id in LANES],
        "plans": plans,
        "audience_text_created": False,
    }


if __name__ == "__main__":
    raise SystemExit(2)
