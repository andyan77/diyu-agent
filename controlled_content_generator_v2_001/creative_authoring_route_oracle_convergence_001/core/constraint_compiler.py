#!/usr/bin/env python3
"""Compile ORCH qualification objects into isolated authoring requests.

The compiler projects constraints and evidence. It deliberately has no surface
realization vocabulary and cannot create audience-facing text.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


TASK_ID = "CONTROLLED_V2_CREATIVE_AUTHORING_ROUTE_ORACLE_CONVERGENCE_001"
COMPILER_VERSION = "controlled-v2-constraint-compiler-v0.1"

FORBIDDEN_REQUEST_KEYS = frozenset(
    {
        "candidate",
        "candidate_id",
        "expected",
        "expected_score",
        "first_acceptance",
        "paired_output",
        "review_envelope",
        "review_result",
        "route_pass",
        "sibling_candidate",
    }
)

REQUIRED_STYLE_AXES = (
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


def canonical_json(value: Any) -> str:
    """Return the repository canonical JSON representation."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    """Hash a structured object without mutating it."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


def _require_fields(value: Mapping[str, Any], fields: Sequence[str], label: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        raise ValueError(f"{label} missing fields: {','.join(missing)}")


def _validate_style_plan(style_plan: Mapping[str, Any]) -> None:
    _require_fields(style_plan, REQUIRED_STYLE_AXES, "style_realization_plan")
    for axis in REQUIRED_STYLE_AXES:
        item = style_plan[axis]
        if not isinstance(item, Mapping):
            raise ValueError(f"style axis {axis} must be an object")
        _require_fields(
            item,
            (
                "selected_value",
                "compatibility_basis",
                "required_observable_effect",
                "forbidden_effect",
            ),
            f"style axis {axis}",
        )


def _validate_material_pack(material_pack: Mapping[str, Any]) -> None:
    _require_fields(
        material_pack,
        (
            "material_pack_id",
            "material_pack_digest",
            "profile_id",
            "source_atoms",
            "authorization_boundary",
            "role_boundary",
            "creative_license",
        ),
        "material_pack",
    )
    atoms = material_pack["source_atoms"]
    if not isinstance(atoms, list) or not atoms:
        raise ValueError("material_pack source_atoms must be a non-empty list")
    atom_ids: set[str] = set()
    for atom in atoms:
        if not isinstance(atom, Mapping):
            raise ValueError("source atom must be an object")
        _require_fields(
            atom,
            ("atom_id", "atom_type", "text", "source_ref", "authorization_ref"),
            "source atom",
        )
        atom_id = str(atom["atom_id"])
        if atom_id in atom_ids:
            raise ValueError(f"duplicate source atom: {atom_id}")
        atom_ids.add(atom_id)


def compile_authoring_request(
    plan: Mapping[str, Any],
    material_pack: Mapping[str, Any],
    style_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile one plan into one author-visible request.

    The caller owns isolation. This function refuses review, expected-answer,
    sibling-output, and candidate payloads before returning the request.
    """

    _require_fields(
        plan,
        (
            "plan_id",
            "plan_digest",
            "assignment_id",
            "profile_id",
            "voice_lane",
            "required_obligations",
            "narrative_operator",
            "output_contract",
        ),
        "qualification plan",
    )
    _validate_material_pack(material_pack)
    _validate_style_plan(style_plan)

    if plan["profile_id"] != material_pack["profile_id"]:
        raise ValueError("plan and material profile mismatch")
    if plan.get("material_pack_ref") != material_pack["material_pack_id"]:
        raise ValueError("plan material reference mismatch")
    if plan.get("material_pack_digest") != material_pack["material_pack_digest"]:
        raise ValueError("plan material digest mismatch")

    forbidden_hits = sorted(FORBIDDEN_REQUEST_KEYS.intersection(_walk_keys(plan)))
    if forbidden_hits:
        raise ValueError(f"plan exposes forbidden author keys: {','.join(forbidden_hits)}")

    request: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "request_id": f"{plan['assignment_id']}-AUTHORING-REQUEST",
        "assignment_id": plan["assignment_id"],
        "plan_ref": plan["plan_id"],
        "plan_digest": plan["plan_digest"],
        "material_pack_ref": material_pack["material_pack_id"],
        "material_pack_digest": material_pack["material_pack_digest"],
        "content_product_contract": {
            "profile_id": plan["profile_id"],
            "required_obligations": list(plan["required_obligations"]),
            "narrative_operator": dict(plan["narrative_operator"]),
            "output_contract": dict(plan["output_contract"]),
        },
        "voice_contract": {
            "voice_lane": plan["voice_lane"],
            "role_identity": material_pack["role_boundary"]["role_identity"],
            "allowed_observation_scope": list(
                material_pack["role_boundary"]["allowed_observation_scope"]
            ),
            "forbidden_inference": list(material_pack["role_boundary"]["forbidden_inference"]),
        },
        "immutable_evidence_atoms": [dict(atom) for atom in material_pack["source_atoms"]],
        "authorization_boundary": dict(material_pack["authorization_boundary"]),
        "creative_license": list(material_pack["creative_license"]),
        "style_realization_plan": {axis: dict(style_plan[axis]) for axis in REQUIRED_STYLE_AXES},
        "isolation_contract": {
            "one_request_one_response": True,
            "reroll_allowed": False,
            "sibling_candidate_visibility": False,
            "review_envelope_visibility": False,
            "expected_score_visibility": False,
            "chain_of_thought_storage": "FORBIDDEN",
            "qualification_only": True,
            "external_provider_API_call_count": 0,
        },
        "response_contract_ref": (
            "controlled_content_generator_v2_001/"
            "creative_authoring_route_oracle_convergence_001/core/"
            "creative_author_response.schema.json"
        ),
    }
    request["request_digest"] = digest_object(request)

    leaked_keys = sorted(FORBIDDEN_REQUEST_KEYS.intersection(_walk_keys(request)))
    if leaked_keys:
        raise ValueError(f"compiled request leaks forbidden keys: {','.join(leaked_keys)}")
    return request


if __name__ == "__main__":
    raise SystemExit(2)
