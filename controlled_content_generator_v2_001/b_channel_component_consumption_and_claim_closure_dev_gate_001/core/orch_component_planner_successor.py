#!/usr/bin/env python3
"""ORCH-only component eligibility, selection, and plan materialization."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_COMPONENT_CONSUMPTION_AND_CLAIM_CLOSURE_DEV_GATE_001"
REGISTRY_DIGEST = "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601"
PLAN_WRITER = "ORCH_COMPONENT_PLANNER_SUCCESSOR_V0_1"
LANES = ("A", "B")
DIFFERENCE_AXES = (
    "primary_question",
    "narrative_operator",
    "information_order",
    "visual_subject",
    "sound_subject",
    "rhythm",
    "ending",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _as_strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(item) for item in value]


def _profile_roles(profile: Mapping[str, Any]) -> set[str]:
    roles: set[str] = set()
    for field in ("required_component_roles", "optional_component_roles"):
        for item in profile.get(field, []):
            if isinstance(item, Mapping) and item.get("role"):
                roles.add(str(item["role"]))
    return roles


def _component_role(component: Mapping[str, Any]) -> str:
    return str(component.get("component_role") or component.get("source_component_role") or "")


def _required_input_slots(component: Mapping[str, Any]) -> list[str]:
    direct = _as_strings(component.get("required_input_slots"))
    if direct:
        return direct
    contract = component.get("input_slot_contract")
    if isinstance(contract, Mapping):
        return _as_strings(contract.get("required"))
    payload = component.get("abstract_payload")
    if isinstance(payload, Mapping):
        return _as_strings(payload.get("required_runtime_slots"))
    return []


def _payload_value(component: Mapping[str, Any], direct_key: str, payload_key: str) -> Any:
    if component.get(direct_key) is not None:
        return component[direct_key]
    payload = component.get("abstract_payload")
    if isinstance(payload, Mapping):
        return payload.get(payload_key)
    return None


def _atom_classes(material_pack: Mapping[str, Any]) -> dict[str, set[str]]:
    classes: dict[str, set[str]] = {}
    for atom in material_pack.get("source_atoms", []):
        if not isinstance(atom, Mapping) or not atom.get("atom_id"):
            continue
        classes[str(atom["atom_id"])] = set(_as_strings(atom.get("evidence_classes")))
    return classes


def _slot_class(slot_name: str) -> str:
    lowered = slot_name.lower()
    rules = (
        (("sound", "audio"), "sound"),
        (("time", "anchor", "version"), "time"),
        (("role", "owner", "authority", "participant"), "role"),
        (("document", "field", "record", "ledger"), "record"),
        (("action", "contact", "task", "friction"), "action"),
        (("condition", "variable", "alternative", "conflict", "comparison"), "condition"),
        (("claim", "boundary", "scope"), "boundary"),
        (("state", "result", "complete", "pending", "unresolved", "unfinished", "gap"), "state"),
        (("scene", "subject", "object", "frame", "shot", "overview", "local", "map"), "scene"),
        (("authorization", "capture"), "authorization"),
    )
    for needles, class_name in rules:
        if any(needle in lowered for needle in needles):
            return class_name
    return "core"


def _bind_component_slots(
    component: Mapping[str, Any], material_pack: Mapping[str, Any]
) -> dict[str, str]:
    atom_classes = _atom_classes(material_pack)
    bindings: dict[str, str] = {}
    for slot in _required_input_slots(component):
        required_class = _slot_class(slot)
        matches = sorted(
            atom_id for atom_id, classes in atom_classes.items() if required_class in classes
        )
        if not matches:
            raise ValueError(f"no material atom supplies {slot} ({required_class})")
        bindings[slot] = matches[0]
    return bindings


def index_registry(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    by_id: dict[str, dict[str, Any]] = {}
    alias_to_id: dict[str, str] = {}
    for row in rows:
        component_id = str(row.get("component_id", ""))
        if not component_id or component_id in by_id:
            raise ValueError("registry component IDs must be nonempty and unique")
        component = dict(row)
        by_id[component_id] = component
        alias = str(component.get("proposal_alias_id", ""))
        if alias:
            if alias in alias_to_id:
                raise ValueError(f"duplicate proposal alias: {alias}")
            alias_to_id[alias] = component_id
    return by_id, alias_to_id


def _component_binding(
    component: Mapping[str, Any],
    alias: str,
    material_pack: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    cp_id = str(profile["content_product_type_id"])
    component_id = str(component["component_id"])
    role = _component_role(component)
    if cp_id not in _as_strings(component.get("applicable_content_product_type_ids")):
        raise ValueError(f"{component_id} is not applicable to {cp_id}")
    if role not in _profile_roles(profile):
        raise ValueError(f"{component_id} role {role} is absent from {cp_id}")
    slot_bindings = _bind_component_slots(component, material_pack)
    hard_guards = [
        str(item["rule_id"])
        for item in profile.get("founder_hard_guards", [])
        if isinstance(item, Mapping) and item.get("rule_id")
    ]
    binding: dict[str, Any] = {
        "canonical_component_id": component_id,
        "proposal_alias_id": alias,
        "registry_digest": REGISTRY_DIGEST,
        "applicable_cp_id": cp_id,
        "component_role": role,
        "input_slot_bindings": slot_bindings,
        "plan_field_bindings": {
            "function": "component_constraints.component_function",
            "reusable_mechanism": "component_constraints.form_operator",
            "anti_pattern_constraints": "component_constraints.forbidden_forms",
            "claim_boundary": "component_constraints.claim_boundary",
        },
        "hard_guard_checks": hard_guards,
        "eligibility_reason": (
            "Registry edge, Profile role, material slots, and authorization boundary all match."
        ),
        "generator_constraint_refs": [
            f"COMPONENT::{component_id}::FORM_ONLY",
            f"COMPONENT::{component_id}::NO_FACT_AUTHORITY",
        ],
        "realized_surface_unit_refs": [],
        "component_digest": component["component_digest"],
        "fact_eligibility": component.get("fact_eligibility") is True,
    }
    binding["binding_digest"] = digest_object(binding)
    return binding


def _validate_material_sufficiency(
    material_pack: Mapping[str, Any], profile: Mapping[str, Any], components: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    requirements = profile.get("input_requirements", {})
    if not isinstance(requirements, Mapping):
        raise ValueError("profile input_requirements must be an object")
    present = {
        "source": set(_as_strings(material_pack.get("present_source_slots"))),
        "fact": set(_as_strings(material_pack.get("present_fact_slots"))),
        "authorization": set(_as_strings(material_pack.get("present_authorization_slots"))),
    }
    required = {
        "source": set(_as_strings(requirements.get("required_source_slots"))),
        "fact": set(_as_strings(requirements.get("required_fact_slots"))),
        "authorization": set(_as_strings(requirements.get("required_authorization_slots"))),
    }
    for component in components:
        required["fact"].update(_as_strings(component.get("required_fact_slots")))
        required["authorization"].update(
            _as_strings(component.get("required_authorization_slots"))
        )
    missing = {kind: sorted(values - present[kind]) for kind, values in required.items()}
    return {
        "pass": not any(missing.values()),
        "missing_slots": missing,
        "required_slots": {kind: sorted(values) for kind, values in required.items()},
        "present_slots": {kind: sorted(values) for kind, values in present.items()},
    }


def build_pair_plans(
    material_pack: Mapping[str, Any],
    profile: Mapping[str, Any],
    registry_rows: Sequence[Mapping[str, Any]],
    merge_alias_map: Mapping[str, str],
    needs_repair_aliases: set[str],
) -> dict[str, Any]:
    """Build two plans from one immutable fact set; Generator never calls this."""

    cp_id = str(profile["content_product_type_id"])
    if cp_id != str(material_pack.get("profile_id")):
        raise ValueError("material pack and Profile mismatch")
    if material_pack.get("development_only") is not True:
        raise ValueError("material pack is not development-only")
    if material_pack.get("synthetic_not_runtime_fact") is not True:
        raise ValueError("material pack must remain synthetic and non-runtime")

    registry, alias_to_id = index_registry(registry_rows)
    source_atom_ids = sorted(
        str(atom["atom_id"])
        for atom in material_pack.get("source_atoms", [])
        if isinstance(atom, Mapping) and atom.get("atom_id")
    )
    source_snapshot = {
        "material_pack_id": material_pack["material_pack_id"],
        "material_pack_version": material_pack["material_pack_version"],
        "source_atoms": material_pack["source_atoms"],
    }
    source_snapshot_digest = digest_object(source_snapshot)
    authorization_digest = digest_object(material_pack["authorization"])
    claim_boundary_digest = digest_object(material_pack["claim_boundary"])
    plans: list[dict[str, Any]] = []

    lane_specs = material_pack.get("lane_plan_intents")
    if not isinstance(lane_specs, Mapping):
        raise ValueError("material pack lacks lane_plan_intents")
    for lane_id in LANES:
        lane = lane_specs.get(lane_id)
        if not isinstance(lane, Mapping):
            raise ValueError(f"material pack lacks lane intent {lane_id}")
        aliases = _as_strings(lane.get("preferred_component_aliases"))
        if not aliases:
            raise ValueError(f"lane {lane_id} lacks component selection intents")
        selected: list[dict[str, Any]] = []
        bindings: list[dict[str, Any]] = []
        for alias in aliases:
            if alias in needs_repair_aliases:
                raise ValueError(f"NEEDS_REPAIR alias is not selectable: {alias}")
            if alias in registry:
                component_id = alias
            elif alias in merge_alias_map:
                component_id = str(merge_alias_map[alias])
            else:
                component_id = alias_to_id.get(alias, "")
            component = registry.get(component_id)
            if component is None:
                raise ValueError(f"unknown component selection intent: {alias}")
            selected.append(component)
            bindings.append(_component_binding(component, alias, material_pack, profile))

        selected_roles = {_component_role(component) for component in selected}
        required_roles = {
            str(item["role"])
            for item in profile.get("required_component_roles", [])
            if isinstance(item, Mapping) and item.get("role")
        }
        missing_roles = sorted(required_roles - selected_roles)
        if missing_roles:
            raise ValueError(f"plan lacks required Profile roles: {missing_roles}")
        if "BNO-08" in aliases:
            information_order = lane.get("information_order")
            if not isinstance(information_order, Sequence) or isinstance(
                information_order, (str, bytes, bytearray)
            ):
                raise ValueError("BNO-08 requires a structured information_order")
            if not information_order or str(information_order[0]) != "observed_result_state":
                raise ValueError("BNO-08 requires observed_result_state first")

        sufficiency = _validate_material_sufficiency(material_pack, profile, selected)
        if sufficiency["pass"] is not True:
            raise ValueError(f"material insufficient for {cp_id}/{lane_id}: {sufficiency['missing_slots']}")
        plan: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "plan_id": f"ORCH-CCV2-DEV-{cp_id}-{lane_id}-001",
            "assignment_id": f"CCV2-DEV-{cp_id}-{lane_id}-001",
            "writer": PLAN_WRITER,
            "owner": "ORCH",
            "canonicality_scope": "DEVELOPMENT_CASE_LOCAL_NOT_RUNTIME",
            "profile_id": cp_id,
            "lane_id": lane_id,
            "material_pack_id": material_pack["material_pack_id"],
            "material_pack_version": material_pack["material_pack_version"],
            "source_atom_id_set": source_atom_ids,
            "source_snapshot_digest": source_snapshot_digest,
            "authorization_set": sorted(material_pack["authorization"]),
            "authorization_digest": authorization_digest,
            "claim_boundary": material_pack["claim_boundary"],
            "claim_boundary_digest": claim_boundary_digest,
            "planning_axes": {axis: lane[axis] for axis in DIFFERENCE_AXES},
            "component_bindings": bindings,
            "component_constraints": [
                {
                    "canonical_component_id": component["component_id"],
                    "component_function": _payload_value(component, "function", "function"),
                    "form_operator": _payload_value(
                        component, "reusable_mechanism", "actual_mechanism"
                    ),
                    "forbidden_forms": component.get(
                        "anti_pattern_constraints",
                        component.get("forbidden_combination_rule_refs", []),
                    ),
                    "claim_boundary": _payload_value(
                        component, "claim_boundary", "claim_boundary"
                    ),
                    "fact_source_allowed": False,
                    "sample_copy_source_allowed": False,
                }
                for component in selected
            ],
            "material_sufficiency": sufficiency,
            "generator_may_select_components": False,
            "generator_may_modify_plan": False,
            "other_lane_candidate_visible": False,
            "other_lane_review_visible": False,
            "development_only": True,
            "publishable": False,
            "runtime_consumable": False,
            "production_consumable": False,
            "generator_qualified": False,
        }
        plan["plan_digest"] = digest_object(plan)
        plans.append(plan)

    differences = {
        axis: plans[0]["planning_axes"][axis] != plans[1]["planning_axes"][axis]
        for axis in DIFFERENCE_AXES
    }
    same_fact_set = all(
        plans[0][field] == plans[1][field]
        for field in (
            "source_atom_id_set",
            "source_snapshot_digest",
            "authorization_set",
            "authorization_digest",
            "claim_boundary",
            "claim_boundary_digest",
            "material_pack_version",
        )
    )
    return {
        "profile_id": cp_id,
        "plans": plans,
        "source_atom_set_difference_count": 0 if same_fact_set else 1,
        "authorization_set_difference_count": 0 if same_fact_set else 1,
        "claim_boundary_difference_count": 0 if same_fact_set else 1,
        "independently_recomputed_difference_axes": differences,
        "real_difference_axis_count": sum(differences.values()),
        "pair_ready": same_fact_set and sum(differences.values()) >= 4,
    }


if __name__ == "__main__":
    raise SystemExit(2)
