#!/usr/bin/env python3
"""Consume frozen ORCH plans without selecting components or writing content."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_COMPONENT_CONSUMPTION_AND_CLAIM_CLOSURE_DEV_GATE_001"
EXPECTED_PLAN_WRITER = "ORCH_COMPONENT_PLANNER_SUCCESSOR_V0_1"
KNOWN_AUTHOR_SURFACES = frozenset(
    {
        "title",
        "body_blocks",
        "spoken_lines",
        "CTA",
        "visual_beats",
        "capture_instructions",
        "audio_grammar",
        "editing_grammar",
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def build_author_request(plan: Mapping[str, Any], material_pack: Mapping[str, Any]) -> dict[str, Any]:
    """Create a one-lane request while preserving the frozen ORCH plan."""

    plan_without_digest = {key: value for key, value in plan.items() if key != "plan_digest"}
    if digest_object(plan_without_digest) != plan.get("plan_digest"):
        raise ValueError("ORCH plan digest mismatch")
    if plan.get("writer") != EXPECTED_PLAN_WRITER or plan.get("owner") != "ORCH":
        raise ValueError("Generator accepts only the active ORCH successor")
    if plan.get("material_pack_id") != material_pack.get("material_pack_id"):
        raise ValueError("plan/material mismatch")
    if plan.get("source_atom_id_set") != sorted(
        str(atom["atom_id"])
        for atom in material_pack.get("source_atoms", [])
        if isinstance(atom, Mapping) and atom.get("atom_id")
    ):
        raise ValueError("plan source set differs from frozen material")

    request: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "request_id": f"AUTHOR-{plan['assignment_id']}-REQUEST",
        "assignment_id": plan["assignment_id"],
        "profile_id": plan["profile_id"],
        "lane_id": plan["lane_id"],
        "plan_id": plan["plan_id"],
        "plan_digest": plan["plan_digest"],
        "material_pack_id": material_pack["material_pack_id"],
        "material_pack_version": material_pack["material_pack_version"],
        "source_atoms": material_pack["source_atoms"],
        "authorization": material_pack["authorization"],
        "claim_boundary": material_pack["claim_boundary"],
        "planning_axes": plan["planning_axes"],
        "component_bindings": plan["component_bindings"],
        "component_constraints": plan["component_constraints"],
        "authoring_instruction": (
            "Write a concise audience-facing development candidate from only these source atoms. "
            "Use component constraints only as form operators. Do not mention CP IDs, qualification, "
            "synthetic data, internal review, versions, tests, or the authoring process. Do not add "
            "entities, actions, numbers, causes, results, sounds, or experiences. Return one response "
            "matching the supplied response schema and bind every factual surface to the smallest "
            "supporting source atom IDs."
        ),
        "other_lane_candidate_visible": False,
        "other_lane_plan_visible": False,
        "expected_score_visible": False,
        "expected_verdict_visible": False,
        "review_answer_visible": False,
        "route_expected_visible": False,
        "baseline_target_visible": False,
        "one_request_one_response": True,
        "reroll_allowed": False,
        "external_provider_allowed": False,
        "development_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "production_consumable": False,
    }
    request["request_digest"] = digest_object(request)
    return request


def _map_author_pointer(pointer: str) -> str:
    replacements = {
        "/surfaces/body_blocks": "/surfaces/body",
        "/surfaces/spoken_lines": "/surfaces/spoken_script",
        "/surfaces/visual_beats": "/surfaces/visual_direction",
        "/surfaces/capture_instructions": "/surfaces/shot_instruction",
        "/surfaces/audio_grammar": "/surfaces/audio_direction",
    }
    for source, target in replacements.items():
        if pointer == source or pointer.startswith(source + "/"):
            return target + pointer[len(source) :]
    if pointer.startswith("/surfaces/editing_grammar"):
        return "/non_audience_editing_grammar" + pointer[len("/surfaces/editing_grammar") :]
    return pointer


def consume_author_response(
    plan: Mapping[str, Any], request: Mapping[str, Any], response: Mapping[str, Any]
) -> dict[str, Any]:
    """Map the frozen author response into the complete claim-closure envelope."""

    if response.get("request_id") != request.get("request_id"):
        raise ValueError("author response request ID mismatch")
    if response.get("request_digest") != request.get("request_digest"):
        raise ValueError("author response request digest mismatch")
    author_surfaces = response.get("surfaces")
    if not isinstance(author_surfaces, Mapping):
        raise ValueError("author response lacks surfaces")
    unknown = set(map(str, author_surfaces)).difference(KNOWN_AUTHOR_SURFACES)
    if unknown:
        raise ValueError(f"unknown author surface fields: {sorted(unknown)}")

    canonical_surfaces: dict[str, Any] = {
        "title": str(author_surfaces.get("title", "")),
        "body": list(author_surfaces.get("body_blocks", [])),
        "spoken_script": list(author_surfaces.get("spoken_lines", [])),
        "CTA": str(author_surfaces.get("CTA", "")),
        "caption": "",
        "on_screen_text": [],
        "visual_direction": list(author_surfaces.get("visual_beats", [])),
        "shot_instruction": list(author_surfaces.get("capture_instructions", [])),
        "audio_direction": str(author_surfaces.get("audio_grammar", "")),
        "sound_instruction": [],
    }
    claimed_bindings = []
    for item in response.get("surface_bindings", []):
        if not isinstance(item, Mapping):
            continue
        claimed_bindings.append(
            {
                **dict(item),
                "surface_path": _map_author_pointer(str(item.get("surface_path", ""))),
            }
        )

    candidate: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "candidate_id": f"CANDIDATE-{plan['assignment_id']}",
        "assignment_id": plan["assignment_id"],
        "profile_id": plan["profile_id"],
        "lane_id": plan["lane_id"],
        "source_plan_id": plan["plan_id"],
        "source_plan_digest": plan["plan_digest"],
        "source_request_id": request["request_id"],
        "source_request_digest": request["request_digest"],
        "author_response_id": response["response_id"],
        "author_backend_class": response["backend_class"],
        "surfaces": canonical_surfaces,
        "non_audience_editing_grammar": str(author_surfaces.get("editing_grammar", "")),
        "author_claimed_surface_bindings": claimed_bindings,
        "style_realization_evidence": response.get("style_realization_evidence", []),
        "required_obligation_evidence": response.get("required_obligation_evidence", []),
        "component_bindings": plan["component_bindings"],
        "generator_component_selection_count": 0,
        "generator_plan_write_count": 0,
        "generator_plan_mutation_count": 0,
        "development_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "production_consumable": False,
        "may_enter_baseline": False,
        "generator_qualified": False,
    }
    candidate["candidate_digest"] = digest_object(candidate)
    return candidate


if __name__ == "__main__":
    raise SystemExit(2)
