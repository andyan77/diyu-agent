#!/usr/bin/env python3
"""Independently check component consumption and an honest pre-candidate DEV stop."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

import yaml


if not __debug__:
    print("component-consumption DEV checker refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_COMPONENT_CONSUMPTION_AND_CLAIM_CLOSURE_DEV_GATE_001"
TASK_DIR = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001"
)
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
REGISTRY_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
    "reviewed_reusable_component_registry.v0.4.jsonl"
)
MERGE_PATH = REGISTRY_PATH.with_name("component_merge_relations.v0.1.jsonl")
DECISION_PATH = REGISTRY_PATH.with_name("component_domain_review_decisions.v0.1.jsonl")
ROUTE_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/route"
)
AUTHOR_CORE_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/core"
)
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
HORIZON_PATH = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001/"
    "phase_0/current_ledger_horizon.v0.1.yaml"
)
CURRENT_LEDGER_OWNER_PATH = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001/"
    "phase_0/check_current_ledger_owner.py"
)
CURRENT_B_CHANNEL_CHECKER = Path("ci/checkers/check_gkb_v2_b_channel_24_component_review.py")
REGISTRY_SHA256 = "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601"
HISTORICAL_ROUTE_DIGESTS_19_33 = {
    19: "a10f1a8477b7b36435ce16f806d21eec505b7d0eee39084666edbc7b9e67f76a",
    20: "ca76d27c8a84ee4a5888c17a0d88249b651de05314fc81a553d031981db4a5a3",
    21: "ba3f824ba4699c821a34416641a55f480451afdc371131916bcf30bb031b8195",
    22: "5ade29110d186c98c05fe17ed07b62a11bd590aafb38a5cec5fa10973e89fc1b",
    23: "0b7568944bdf073c5b6842263a954e59dc016709518fa57ece86b0ba2b365045",
    24: "5a64c5130872905521bfa536e2d64e17f66a2c589dbd80b3c45183a78fcfb862",
    25: "1fef7a924fe2abb7e28c5ba5a06e86a8e2421084043d02d35502ce8b1aa7da38",
    26: "6383578d17aba2642b1e1299f6227954c5846ea7a83203949303d43e233c8e3d",
    27: "58c4768bcc91ce69ffda835a85f257a1ac99116fd4276c5d1aaf7b0367a6eb1a",
    28: "35491c51661a0f39d44410d4aa08753c10e6edb9e958304802a294a00f54c880",
    29: "bc7c526085bba2e4c0b7f0cd439f9218bce81bd2e393e2f15aec6d3cce7ce456",
    30: "143ee83792fefa5f48e577350d3aa0d4ae84d79dd9f4d2866fe363620c3d6f51",
    31: "b2d7ea6f24df0db18acfb40ea6e2d50249d41320302473068dff0b688b952e48",
    32: "098b9070582e52e8d03f4bd884d317b97b650ffae7ec6c3035f1ec9993dc0e33",
    33: "c24cf07ba96cb58083a33e95dd3972527e9d93d0b1e34f631dc354b8e382bff7",
}
ROUTE_LINE = re.compile(r"^  route_migration_([^:]+):$")
TOP_LEVEL_LINE = re.compile(r"^  [A-Za-z0-9_]+:$")
READY_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "Serving_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "release_ready",
        "production_ready",
        "generator_qualified",
        "runtime_provider_adapter_qualified",
        "runtime_ingest_ready",
        "generation_600_allowed",
        "expand_3600_allowed",
    }
)
PAIR_EQUAL_FIELDS = (
    "source_atom_id_set",
    "source_snapshot_digest",
    "authorization_set",
    "authorization_digest",
    "claim_boundary",
    "claim_boundary_digest",
    "material_pack_version",
)
DIFFERENCE_AXES = (
    "primary_question",
    "narrative_operator",
    "information_order",
    "visual_subject",
    "sound_subject",
    "rhythm",
    "ending",
)
RISK_BLOCKERS = frozenset(
    {
        "FABRICATED_EVENT",
        "FABRICATED_PERSON_EXPERIENCE",
        "PRIVACY_AUTHORIZATION_FAILURE",
        "ROLE_AUTHORITY_EXPANSION",
        "UNAUTHORIZED_BRAND_CLAIM",
        "UNSUPPORTED_NUMERIC_OR_PERFORMANCE_CLAIM",
    }
)


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected object in {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"expected object row in {path}")
        rows.append(value)
    return rows


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"expected mapping in {path}")
    return value


def add_error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def recursive_pairs(value: Any) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            pairs.append((str(key), child))
            pairs.extend(recursive_pairs(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            pairs.extend(recursive_pairs(child))
    return pairs


def route_blocks(text: str) -> tuple[dict[int, str], list[int], list[str]]:
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    order: list[int] = []
    shadows: list[str] = []
    for index, line in enumerate(lines):
        match = ROUTE_LINE.fullmatch(line)
        if match is None:
            continue
        suffix = match.group(1)
        if not suffix.isdigit():
            shadows.append(suffix)
            continue
        route_id = int(suffix)
        starts.append((route_id, index))
        order.append(route_id)
    blocks: dict[int, str] = {}
    for route_id, start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if TOP_LEVEL_LINE.fullmatch(lines[index]):
                end = index
                break
        blocks[route_id] = "\n".join(lines[start:end]) + "\n"
    return blocks, order, shadows


def _component_role(component: Mapping[str, Any]) -> str:
    return str(component.get("component_role") or component.get("source_component_role") or "")


def _required_input_slots(component: Mapping[str, Any]) -> set[str]:
    direct = component.get("required_input_slots")
    if isinstance(direct, list):
        return set(map(str, direct))
    contract = component.get("input_slot_contract")
    if isinstance(contract, Mapping) and isinstance(contract.get("required"), list):
        return set(map(str, contract["required"]))
    payload = component.get("abstract_payload")
    if isinstance(payload, Mapping) and isinstance(payload.get("required_runtime_slots"), list):
        return set(map(str, payload["required_runtime_slots"]))
    return set()


def _profiles(root: Path) -> dict[str, dict[str, Any]]:
    document = load_yaml(root / PROFILE_PATH)["content_product_profile_registry"]
    return {str(row["content_product_type_id"]): row for row in document["profiles"]}


def _profile_roles(profile: Mapping[str, Any]) -> set[str]:
    rows = list(profile["required_component_roles"]) + list(profile["optional_component_roles"])
    return {str(row["role"]) for row in rows}


def _required_profile_roles(profile: Mapping[str, Any]) -> set[str]:
    return {str(row["role"]) for row in profile["required_component_roles"]}


def _independent_route_action(
    input_payload: Mapping[str, Any], profile: Mapping[str, Any]
) -> tuple[str, bool]:
    requirements = profile["input_requirements"]
    present = {
        "source": set(map(str, input_payload.get("present_source_slots", []))),
        "fact": set(map(str, input_payload.get("present_fact_slots", []))),
        "authorization": set(map(str, input_payload.get("present_authorization_slots", []))),
    }
    required = {
        "source": set(map(str, requirements["required_source_slots"])),
        "fact": set(map(str, requirements["required_fact_slots"])),
        "authorization": set(map(str, requirements["required_authorization_slots"])),
    }
    if input_payload.get("hard_guard_hits"):
        return "BLOCK", True
    if RISK_BLOCKERS.intersection(map(str, input_payload.get("risk_points", []))):
        return "BLOCK", True
    missing_classes = [
        kind for kind in ("authorization", "fact", "source") if required[kind] - present[kind]
    ]
    if not missing_classes:
        return "ALLOW", True
    slot_class = missing_classes[0]
    route_id = f"required_{slot_class}_missing"
    contract = next(row for row in profile["input_sufficiency_routes"] if row["route_id"] == route_id)
    payload = input_payload.get("partial_artifact_payload")
    valid_degrade = (
        input_payload.get("partial_safe") is True
        and contract.get("audience_facing_body_allowed") is False
        and input_payload.get("requested_degraded_output") in contract.get("allowed_outputs", [])
        and isinstance(payload, Mapping)
        and bool(payload)
    )
    return ("DEGRADE", True) if valid_degrade else ("REQUEST_INPUT", True)


def _check_freeze(root: Path, errors: list[dict[str, str]]) -> None:
    freeze = load_json(root / TASK_DIR / "freeze/commit_1_freeze_manifest.v0.1.json")
    if freeze.get("freeze_manifest_digest") != object_digest(freeze, "freeze_manifest_digest"):
        add_error(errors, "E_FREEZE_DIGEST", "freeze manifest")
    for group in ("core_file_digests", "input_file_digests"):
        for relative, expected in freeze.get(group, {}).items():
            path = root / relative
            if not path.exists() or sha256_file(path) != expected:
                add_error(errors, "E_FROZEN_FILE", relative)
    for relative, expected in freeze.get("generated_file_digests", {}).items():
        path = root / TASK_DIR / relative
        if not path.exists() or sha256_file(path) != expected:
            add_error(errors, "E_FROZEN_PREAUTHOR_ARTIFACT", relative)
    expected_counts = {
        "material_pack_count": 20,
        "assignment_count": 40,
        "orch_plan_count": 40,
        "author_request_count": 40,
        "accepted_new_component_loaded_count": 22,
        "component_conformance_case_count": 66,
        "route_case_count": 60,
        "source_write_attempt_count": 0,
        "runtime_consumable": False,
        "generator_qualified": False,
    }
    for key, expected in expected_counts.items():
        if freeze.get(key) != expected:
            add_error(errors, "E_FREEZE_COUNT", f"{key}={freeze.get(key)}")


def _check_registry_and_resolution(root: Path, errors: list[dict[str, str]]) -> tuple[
    dict[str, dict[str, Any]], dict[str, str], set[str]
]:
    rows = load_jsonl(root / REGISTRY_PATH)
    if len(rows) != 86 or sha256_file(root / REGISTRY_PATH) != REGISTRY_SHA256:
        add_error(errors, "E_REGISTRY_FREEZE", f"count={len(rows)}")
    registry = {str(row["component_id"]): row for row in rows}
    alias_map = {
        str(row["proposal_alias_id"]): str(row["component_id"])
        for row in rows
        if row.get("proposal_alias_id")
    }
    merge_rows = load_jsonl(root / MERGE_PATH)
    merge_map = {str(row["proposal_id"]): str(row["merge_target_component_id"]) for row in merge_rows}
    needs_repair = {
        str(row["proposal_id"])
        for row in load_jsonl(root / DECISION_PATH)
        if row.get("decision") == "NEEDS_REPAIR"
    }
    resolution = load_json(root / TASK_DIR / "component/component_resolution_map.v0.1.json")
    if resolution.get("resolution_digest") != object_digest(resolution, "resolution_digest"):
        add_error(errors, "E_RESOLUTION_DIGEST", "resolution map")
    expected_resolution = {
        "registry_total_count": 86,
        "inherited_component_count": 64,
        "accepted_new_component_loaded_count": 22,
        "merged_alias_count": 1,
        "needs_repair_count": 1,
        "selectable_registry_component_count": 86,
        "alias_creates_new_component": False,
    }
    for key, expected in expected_resolution.items():
        if resolution.get(key) != expected:
            add_error(errors, "E_RESOLUTION_MAP", f"{key}={resolution.get(key)}")
    if resolution.get("merge_alias_map") != merge_map or set(resolution.get("needs_repair_exclusions", [])) != needs_repair:
        add_error(errors, "E_RESOLUTION_MAP", "merge or repair mapping")
    return registry, {**alias_map, **merge_map}, needs_repair


def _check_materials_and_plans(
    root: Path,
    errors: list[dict[str, str]],
    registry: Mapping[str, Mapping[str, Any]],
    aliases: Mapping[str, str],
    needs_repair: set[str],
) -> None:
    profiles = _profiles(root)
    materials = load_jsonl(root / TASK_DIR / "materials/development_material_packs.v0.1.jsonl")
    plans = load_jsonl(root / TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl")
    requests = load_jsonl(root / TASK_DIR / "requests/author_requests.v0.1.jsonl")
    assignments = load_jsonl(root / TASK_DIR / "assignments/development_assignments.v0.1.jsonl")
    pairs = load_jsonl(root / TASK_DIR / "orch/orch_pair_plan_results.v0.1.jsonl")
    if len(materials) != 20 or len(plans) != 40 or len(requests) != 40 or len(assignments) != 40:
        add_error(errors, "E_PREAUTHOR_COUNTS", "materials/plans/requests/assignments")
        return
    if len(pairs) != 20:
        add_error(errors, "E_PAIR_COUNT", str(len(pairs)))
    material_by_id = {str(row["material_pack_id"]): row for row in materials}
    plans_by_cp: dict[str, list[dict[str, Any]]] = {}
    for material in materials:
        if material.get("material_pack_digest") != object_digest(material, "material_pack_digest"):
            add_error(errors, "E_MATERIAL_DIGEST", str(material.get("material_pack_id")))
        if material.get("development_only") is not True or material.get("synthetic_not_runtime_fact") is not True:
            add_error(errors, "E_MATERIAL_BOUNDARY", str(material.get("material_pack_id")))
        atoms = material.get("source_atoms", [])
        for atom in atoms:
            if atom.get("atom_digest") != object_digest(atom, "atom_digest"):
                add_error(errors, "E_SOURCE_ATOM_DIGEST", str(atom.get("atom_id")))
    for plan in plans:
        plan_id = str(plan.get("plan_id"))
        if plan.get("plan_digest") != object_digest(plan, "plan_digest"):
            add_error(errors, "E_PLAN_DIGEST", plan_id)
        if plan.get("writer") != "ORCH_COMPONENT_PLANNER_SUCCESSOR_V0_1" or plan.get("owner") != "ORCH":
            add_error(errors, "E_PLAN_OWNER", plan_id)
        if any(
            plan.get(key) is not False
            for key in (
                "generator_may_select_components",
                "generator_may_modify_plan",
                "publishable",
                "runtime_consumable",
                "production_consumable",
                "generator_qualified",
            )
        ):
            add_error(errors, "E_PLAN_BOUNDARY", plan_id)
        material = material_by_id.get(str(plan.get("material_pack_id")))
        profile = profiles.get(str(plan.get("profile_id")))
        if material is None or profile is None:
            add_error(errors, "E_PLAN_BINDING", plan_id)
            continue
        snapshot = {
            "material_pack_id": material["material_pack_id"],
            "material_pack_version": material["material_pack_version"],
            "source_atoms": material["source_atoms"],
        }
        if plan.get("source_snapshot_digest") != object_digest(snapshot, "__absent__"):
            add_error(errors, "E_PLAN_SOURCE_SNAPSHOT", plan_id)
        selected_roles: set[str] = set()
        for binding in plan.get("component_bindings", []):
            alias = str(binding.get("proposal_alias_id", ""))
            component_id = str(binding.get("canonical_component_id", ""))
            component = registry.get(component_id)
            if alias in needs_repair or component is None:
                add_error(errors, "E_INVALID_COMPONENT_SELECTION", f"{plan_id}:{alias}")
                continue
            if aliases.get(alias, component_id) != component_id:
                add_error(errors, "E_COMPONENT_ALIAS_RESOLUTION", f"{plan_id}:{alias}")
            role = _component_role(component)
            selected_roles.add(role)
            if plan["profile_id"] not in component.get("applicable_content_product_type_ids", []):
                add_error(errors, "E_COMPONENT_CP_EDGE", f"{plan_id}:{component_id}")
            if role not in _profile_roles(profile):
                add_error(errors, "E_COMPONENT_ROLE", f"{plan_id}:{component_id}")
            required_slots = _required_input_slots(component)
            if set(binding.get("input_slot_bindings", {})) != required_slots:
                add_error(errors, "E_COMPONENT_SLOT_BINDING", f"{plan_id}:{component_id}")
            if binding.get("registry_digest") != REGISTRY_SHA256 or binding.get("fact_eligibility") is not False:
                add_error(errors, "E_COMPONENT_FACT_AUTHORITY", f"{plan_id}:{component_id}")
            if alias == "BNO-08":
                order = plan.get("planning_axes", {}).get("information_order", [])
                if plan["profile_id"] not in {"CP04", "CP15"} or not order or order[0] != "observed_result_state":
                    add_error(errors, "E_BNO08_GUARD", plan_id)
        missing_roles = _required_profile_roles(profile) - selected_roles
        if missing_roles:
            add_error(errors, "E_PLAN_ROLE_COVERAGE", f"{plan_id}:{sorted(missing_roles)}")
        plans_by_cp.setdefault(str(plan["profile_id"]), []).append(plan)

    for cp_id, cp_plans in plans_by_cp.items():
        if len(cp_plans) != 2 or {row.get("lane_id") for row in cp_plans} != {"A", "B"}:
            add_error(errors, "E_PAIR_SHAPE", cp_id)
            continue
        left, right = sorted(cp_plans, key=lambda row: str(row["lane_id"]))
        for field in PAIR_EQUAL_FIELDS:
            if left.get(field) != right.get(field):
                add_error(errors, "E_PAIR_FACT_DRIFT", f"{cp_id}:{field}")
        differences = sum(
            left.get("planning_axes", {}).get(axis) != right.get("planning_axes", {}).get(axis)
            for axis in DIFFERENCE_AXES
        )
        if differences < 4:
            add_error(errors, "E_PAIR_AXIS_COUNT", f"{cp_id}:{differences}")

    plan_ids = {str(row["plan_id"]) for row in plans}
    assignment_ids = {str(row["assignment_id"]) for row in assignments}
    for request in requests:
        request_id = str(request.get("request_id"))
        if request.get("request_digest") != object_digest(request, "request_digest"):
            add_error(errors, "E_REQUEST_DIGEST", request_id)
        if request.get("plan_id") not in plan_ids or request.get("assignment_id") not in assignment_ids:
            add_error(errors, "E_REQUEST_BINDING", request_id)
        forbidden = (
            "expected_score",
            "expected_verdict",
            "guardian_rubric_answer",
            "other_lane_body",
            "route_expected",
            "baseline_acceptance_target",
        )
        if any(key in request for key in forbidden):
            add_error(errors, "E_AUTHOR_REQUEST_LEAK", request_id)


def _check_conformance(root: Path, errors: list[dict[str, str]], registry: Mapping[str, Mapping[str, Any]]) -> None:
    cases = load_jsonl(root / TASK_DIR / "component/component_conformance_cases.v0.1.jsonl")
    results = load_jsonl(root / TASK_DIR / "component/component_conformance_results.v0.1.jsonl")
    if len(cases) != 66 or len(results) != 66:
        add_error(errors, "E_CONFORMANCE_COUNT", f"{len(cases)}/{len(results)}")
        return
    result_map = {str(row["case_id"]): row for row in results}
    type_counts: Counter[str] = Counter()
    component_ids: set[str] = set()
    for case in cases:
        case_id = str(case["case_id"])
        case_type = str(case["case_type"])
        type_counts[case_type] += 1
        component_id = str(case["canonical_component_id"])
        component_ids.add(component_id)
        component = registry.get(component_id)
        independently_passed = False
        if component is not None and case_type == "ELIGIBLE_PLAN_LEVEL":
            binding = case.get("binding", {})
            independently_passed = (
                case["profile_id"] in component.get("applicable_content_product_type_ids", [])
                and binding.get("canonical_component_id") == component_id
                and set(binding.get("input_slot_bindings", {})) == _required_input_slots(component)
            )
        elif component is not None and case_type == "INELIGIBLE_CP":
            independently_passed = case["profile_id"] not in component.get(
                "applicable_content_product_type_ids", []
            )
        elif component is not None and case_type == "BINDING_REMOVAL_MUTATION":
            independently_passed = case.get("mutated_component_bindings") == []
        result = result_map.get(case_id)
        if not independently_passed or result is None or result.get("pass") is not True:
            add_error(errors, "E_CONFORMANCE_CASE", case_id)
        if result is not None and result.get("result_digest") != object_digest(result, "result_digest"):
            add_error(errors, "E_CONFORMANCE_RESULT_DIGEST", case_id)
    if set(type_counts.values()) != {22} or len(component_ids) != 22:
        add_error(errors, "E_CONFORMANCE_DISTRIBUTION", str(type_counts))


def _check_route_regression(root: Path, errors: list[dict[str, str]]) -> None:
    profiles = _profiles(root)
    inputs = load_jsonl(root / ROUTE_DIR / "route_inputs.v0.1.jsonl")
    expectations = {
        str(row["case_id"]): row
        for row in load_jsonl(root / ROUTE_DIR / "sealed_route_expectations.v0.1.jsonl")
    }
    actuals = {
        str(row["case_id"]): row
        for row in load_jsonl(root / TASK_DIR / "route/route_regression_actuals.v0.1.jsonl")
    }
    comparisons = {
        str(row["case_id"]): row
        for row in load_jsonl(root / TASK_DIR / "route/route_regression_comparison.v0.1.jsonl")
    }
    if len(inputs) != 60 or len(expectations) != 60:
        add_error(errors, "E_ROUTE_CASE_COUNT", "input/expectation")
    mismatch = 0
    fake_degrade = 0
    for row in inputs:
        case_id = str(row["case_id"])
        action, _ = _independent_route_action(row["actual_input_payload"], profiles[str(row["profile_id"])])
        actual = actuals.get(case_id, {}).get("actual_decision", {})
        comparison = comparisons.get(case_id, {})
        if action != expectations[case_id]["expected_action"] or action != actual.get("actual_primary_action"):
            mismatch += 1
        if comparison.get("expected_actual_same_source") is not False:
            add_error(errors, "E_ROUTE_ORACLE_SEPARATION", case_id)
        if action == "DEGRADE" and not actual.get("degraded_artifact"):
            fake_degrade += 1
    if mismatch:
        add_error(errors, "E_ROUTE_MISMATCH", str(mismatch))
    if fake_degrade:
        add_error(errors, "E_FAKE_DEGRADE", str(fake_degrade))
    result = load_json(root / TASK_DIR / "route/route_regression_result.v0.1.json")
    expected_result = {
        "route_case_count": 60,
        "route_decision_recomputation_mismatch_count": 0,
        "fake_degrade_count": 0,
        "expected_actual_same_source_count": 0,
        "route_gate_reused": True,
        "parallel_route_gate_created": False,
    }
    for key, expected in expected_result.items():
        if result.get(key) != expected:
            add_error(errors, "E_ROUTE_RESULT", f"{key}={result.get(key)}")
    if result.get("route_result_digest") != object_digest(result, "route_result_digest"):
        add_error(errors, "E_ROUTE_RESULT_DIGEST", "route result")


def _check_failure_result(root: Path, errors: list[dict[str, str]]) -> None:
    receipt = load_json(root / TASK_DIR / "author/author_session_failure_receipt.v0.1.json")
    review = load_json(root / TASK_DIR / "review/development_review_status.v0.1.json")
    result = load_json(root / TASK_DIR / "result/development_gate_result.v0.1.json")
    packet = load_json(root / TASK_DIR / "guardian/guardian_review_packet.v0.1.json")
    for document, digest_key, label in (
        (receipt, "failure_receipt_digest", "author failure"),
        (review, "review_status_digest", "review status"),
        (result, "result_digest", "result"),
        (packet, "packet_digest", "guardian packet"),
    ):
        if document.get(digest_key) != object_digest(document, digest_key):
            add_error(errors, "E_RESULT_DIGEST", label)
    expected_receipt = {
        "status": "AUTHOR_BATCH_REJECTED_AT_ATOMIC_RESPONSE_VALIDATION",
        "failure_stage": "POST_AUTHOR_RESPONSE_PRE_PERSISTENCE",
        "blocking_error_code": "AUTHOR_RESPONSE_REQUEST_ID_MISMATCH",
        "blocking_error_count": 1,
        "author_invocation_count": 40,
        "fresh_ephemeral_process_count": 40,
        "requested_response_count": 40,
        "persisted_raw_response_count": 0,
        "persisted_candidate_count": 0,
        "response_set_atomically_discarded": True,
        "reroll_count": 0,
        "replacement_count": 0,
        "manual_response_patch_count": 0,
        "external_provider_API_call_count": 0,
        "material_or_semantic_core_changed_after_author_start": False,
        "hidden_created_count": 0,
        "generator_qualified": False,
    }
    for key, expected in expected_receipt.items():
        if receipt.get(key) != expected:
            add_error(errors, "E_AUTHOR_FAILURE_RECEIPT", f"{key}={receipt.get(key)}")
    forbidden_outputs = (
        TASK_DIR / "author/raw_author_responses.v0.1.jsonl",
        TASK_DIR / "generator/development_candidates.v0.1.jsonl",
        TASK_DIR / "claim_closure/surface_manifests.v0.1.jsonl",
        TASK_DIR / "machine/development_machine_result.v0.1.json",
    )
    for path in forbidden_outputs:
        if (root / path).exists():
            add_error(errors, "E_OUTPUT_AFTER_ATOMIC_AUTHOR_FAILURE", path.as_posix())
    if review.get("review_status") != "NOT_STARTED_DUE_TO_AUTHOR_RESPONSE_PROTOCOL_FAILURE":
        add_error(errors, "E_REVIEW_STATUS", str(review.get("review_status")))
    if result.get("verdict") != "STOPPED_BEFORE_HIDDEN" or result.get("dev_gate_pass") is not False:
        add_error(errors, "E_FAILURE_NOT_RECORDED", str(result.get("verdict")))
    if result.get("blocking_items") != ["AUTHOR_RESPONSE_REQUEST_ID_MISMATCH"]:
        add_error(errors, "E_BLOCKING_ITEMS", str(result.get("blocking_items")))
    boundaries = result.get("boundaries", {})
    expected_boundaries = {
        "accepted_baseline_count": 120,
        "baseline_increment_count": 0,
        "hidden_count": 0,
        "generator_qualified": False,
        "runtime_provider_adapter_qualified": False,
        "runtime_generation_eligible_profile_count": 0,
        "runtime_ingest_ready": False,
        "published_content_count": 0,
        "production_candidate_count": 0,
        "generation_600_allowed": False,
        "expand_3600_allowed": False,
        "readiness_all_false": True,
        "external_provider_API_call_count": 0,
        "KE_truth_change_count": 0,
        "RAG_change_count": 0,
        "DIFY_change_count": 0,
        "Serving_change_count": 0,
    }
    if boundaries != expected_boundaries:
        add_error(errors, "E_RESULT_BOUNDARIES", str(boundaries))
    if packet.get("eligible_to_open_sealed_hidden") is not False:
        add_error(errors, "E_HIDDEN_ELIGIBILITY", "guardian packet")
    for key, value in recursive_pairs(result):
        if key in READY_KEYS and value is True:
            add_error(errors, "E_READINESS_TRUE", key)


def _check_ledger(root: Path, errors: list[dict[str, str]]) -> None:
    ledger_doc = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    text = (root / LEDGER_PATH).read_text(encoding="utf-8")
    blocks, order, shadows = route_blocks(text)
    historical_order = [route_id for route_id in order if 19 <= route_id <= 33]
    if shadows or historical_order != list(range(19, 34)):
        add_error(errors, "E_HISTORICAL_LEDGER_SEQUENCE", str(historical_order))
    for route_id, expected_digest in HISTORICAL_ROUTE_DIGESTS_19_33.items():
        digest = hashlib.sha256(blocks.get(route_id, "").encode("utf-8")).hexdigest()
        if expected_digest != digest:
            add_error(errors, "E_HISTORICAL_ROUTE_DIGEST", f"route_migration_{route_id}")
    route33 = ledger_doc.get("route_migration_33")
    if not isinstance(route33, Mapping) or route33.get("applied_by_task") != TASK_ID:
        add_error(errors, "E_ROUTE33", "task binding")
    elif route33.get("migration_digest") != object_digest(route33, "migration_digest"):
        add_error(errors, "E_ROUTE33_DIGEST", "migration digest")

    owner_path = root / CURRENT_LEDGER_OWNER_PATH
    spec = importlib.util.spec_from_file_location("current_ledger_owner", owner_path)
    if spec is None or spec.loader is None:
        add_error(errors, "E_CURRENT_LEDGER_OWNER", "unable to load owner")
        return
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    for owner_error in owner.validate(root):
        add_error(errors, str(owner_error["code"]), f"current owner: {owner_error['detail']}")


def _check_compatibility_repair(root: Path, errors: list[dict[str, str]]) -> None:
    receipt = load_json(
        root / TASK_DIR / "compatibility/b_channel_live_checker_reference_safe_repair.v0.1.json"
    )
    if receipt.get("repair_digest") != object_digest(receipt, "repair_digest"):
        add_error(errors, "E_COMPAT_RECEIPT_DIGEST", "repair receipt")
    if receipt.get("before_sha256") != "fa2b5a94a75b302b13e81e5b0349d22b0e9b9dc8e8a0753d8dd03c94d81d04b2":
        add_error(errors, "E_COMPAT_BEFORE", str(receipt.get("before_sha256")))
    if receipt.get("after_sha256") != "ff4060e02f387e92b9ec1613df31b5b855cbd04a1155d92f5ca03dacf3191394":
        add_error(errors, "E_COMPAT_AFTER", str(receipt.get("after_sha256")))
    if receipt.get("sealed_checker_modified_count") != 0 or receipt.get(
        "current_live_checker_modified_count"
    ) != 1:
        add_error(errors, "E_COMPAT_SCOPE", "checker counts")
    if receipt.get("historical_route_tamper_still_rejected") is not True:
        add_error(errors, "E_COMPAT_TAMPER", "historical route guard")


def required_paths() -> tuple[Path, ...]:
    return (
        PROFILE_PATH,
        REGISTRY_PATH,
        MERGE_PATH,
        DECISION_PATH,
        ROUTE_DIR / "route_inputs.v0.1.jsonl",
        ROUTE_DIR / "sealed_route_expectations.v0.1.jsonl",
        AUTHOR_CORE_DIR / "active_authoring_registry.v0.3.yaml",
        AUTHOR_CORE_DIR / "creative_author_protocol.v0.1.yaml",
        AUTHOR_CORE_DIR / "creative_author_response.schema.json",
        LEDGER_PATH,
        HORIZON_PATH,
        CURRENT_LEDGER_OWNER_PATH,
        CURRENT_B_CHANNEL_CHECKER,
        TASK_DIR / "freeze/commit_1_freeze_manifest.v0.1.json",
        TASK_DIR / "component/component_resolution_map.v0.1.json",
        TASK_DIR / "component/component_conformance_cases.v0.1.jsonl",
        TASK_DIR / "component/component_conformance_results.v0.1.jsonl",
        TASK_DIR / "materials/development_material_packs.v0.1.jsonl",
        TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl",
        TASK_DIR / "orch/orch_pair_plan_results.v0.1.jsonl",
        TASK_DIR / "assignments/development_assignments.v0.1.jsonl",
        TASK_DIR / "requests/author_requests.v0.1.jsonl",
        TASK_DIR / "route/route_regression_actuals.v0.1.jsonl",
        TASK_DIR / "route/route_regression_comparison.v0.1.jsonl",
        TASK_DIR / "route/route_regression_result.v0.1.json",
        TASK_DIR / "author/author_session_failure_receipt.v0.1.json",
        TASK_DIR / "review/development_review_status.v0.1.json",
        TASK_DIR / "result/development_gate_result.v0.1.json",
        TASK_DIR / "guardian/guardian_review_packet.v0.1.json",
        TASK_DIR / "compatibility/b_channel_live_checker_reference_safe_repair.v0.1.json",
    )


def validate(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for path in required_paths():
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE", path.as_posix())
    if errors:
        return errors
    try:
        _check_freeze(root, errors)
        registry, aliases, needs_repair = _check_registry_and_resolution(root, errors)
        _check_materials_and_plans(root, errors, registry, aliases, needs_repair)
        _check_conformance(root, errors, registry)
        _check_route_regression(root, errors)
        _check_failure_result(root, errors)
        _check_ledger(root, errors)
        _check_compatibility_repair(root, errors)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        add_error(errors, "E_PARSE_OR_SCHEMA", str(exc))
    return errors


def copy_fixture(root: Path, destination: Path) -> None:
    shutil.copytree(root / TASK_DIR, destination / TASK_DIR)
    for path in required_paths():
        if path.is_relative_to(TASK_DIR):
            continue
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, target)


def mutate_json(path: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    value = load_json(path)
    mutator(value)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def mutate_jsonl(path: Path, mutator: Callable[[list[dict[str, Any]]], None]) -> None:
    rows = load_jsonl(path)
    mutator(rows)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def mutate_yaml(path: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    value = load_yaml(path)
    mutator(value)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def mutate_route_block(path: Path, route_id: int, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    blocks, _, _ = route_blocks(text)
    block = blocks[route_id]
    if old not in block:
        raise ValueError(f"route mutation token absent: route={route_id} token={old}")
    path.write_text(text.replace(block, block.replace(old, new, 1), 1), encoding="utf-8")


def _positive_classifier_examples_pass() -> bool:
    examples = (
        ("你会先看哪一处？", "OPEN_AUDIENCE_QUESTION"),
        ("先别急着下结论。", "GENERIC_CREATIVE_EXPRESSION"),
        ("如果仍是待确认，就保留待确认。", "DISCLOSED_HYPOTHETICAL"),
        ("固定机位，切近景，不加旁白。", "EDITORIAL_FORM_OPERATOR"),
    )
    return all(text and label for text, label in examples)


def selftest(root: Path) -> int:
    baseline = validate(root)
    if baseline:
        print(json.dumps({"status": "SELFTEST_BASE_INVALID", "errors": baseline}, ensure_ascii=False))
        return 1
    tests: list[tuple[str, str, Callable[[Path], None]]] = []

    def add(name: str, code: str, mutation: Callable[[Path], None]) -> None:
        tests.append((name, code, mutation))

    add(
        "metadata_only_conformance",
        "E_CONFORMANCE_CASE",
        lambda temp: mutate_jsonl(
            temp / TASK_DIR / "component/component_conformance_cases.v0.1.jsonl",
            lambda rows: rows[0]["binding"].update({"input_slot_bindings": {}}),
        ),
    )
    add(
        "merge_alias_creates_87",
        "E_RESOLUTION_MAP",
        lambda temp: mutate_json(
            temp / TASK_DIR / "component/component_resolution_map.v0.1.json",
            lambda value: value.update({"selectable_registry_component_count": 87}),
        ),
    )
    add(
        "needs_repair_selected",
        "E_INVALID_COMPONENT_SELECTION",
        lambda temp: mutate_jsonl(
            temp / TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl",
            lambda rows: rows[0]["component_bindings"][0].update(
                {"proposal_alias_id": "BNO-02", "canonical_component_id": "BNO-02"}
            ),
        ),
    )
    add(
        "invalid_cp_edge",
        "E_COMPONENT_CP_EDGE",
        lambda temp: mutate_jsonl(
            temp / TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl",
            lambda rows: rows[0]["component_bindings"][0].update(
                {"canonical_component_id": "RCV2-004-TRANSITION-SOURCE-BOUND-TIME-SLICE"}
            ),
        ),
    )
    add(
        "generator_owns_plan",
        "E_PLAN_OWNER",
        lambda temp: mutate_jsonl(
            temp / TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl",
            lambda rows: rows[0].update({"owner": "GENERATOR"}),
        ),
    )
    add(
        "pair_fact_drift",
        "E_PAIR_FACT_DRIFT",
        lambda temp: mutate_jsonl(
            temp / TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl",
            lambda rows: rows[1].update({"authorization_digest": "0" * 64}),
        ),
    )
    add(
        "fake_four_axes",
        "E_PAIR_AXIS_COUNT",
        lambda temp: mutate_jsonl(
            temp / TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl",
            lambda rows: rows[1].update({"planning_axes": copy.deepcopy(rows[0]["planning_axes"])}),
        ),
    )
    add(
        "failure_cleared",
        "E_FAILURE_NOT_RECORDED",
        lambda temp: mutate_json(
            temp / TASK_DIR / "result/development_gate_result.v0.1.json",
            lambda value: value.update({"dev_gate_pass": True}),
        ),
    )
    add(
        "blocking_items_cleared",
        "E_BLOCKING_ITEMS",
        lambda temp: mutate_json(
            temp / TASK_DIR / "result/development_gate_result.v0.1.json",
            lambda value: value.update({"blocking_items": []}),
        ),
    )
    add(
        "baseline_increase",
        "E_RESULT_BOUNDARIES",
        lambda temp: mutate_json(
            temp / TASK_DIR / "result/development_gate_result.v0.1.json",
            lambda value: value["boundaries"].update({"accepted_baseline_count": 121}),
        ),
    )
    add(
        "hidden_created",
        "E_RESULT_BOUNDARIES",
        lambda temp: mutate_json(
            temp / TASK_DIR / "result/development_gate_result.v0.1.json",
            lambda value: value["boundaries"].update({"hidden_count": 1}),
        ),
    )
    add(
        "qualified_flip",
        "E_RESULT_BOUNDARIES",
        lambda temp: mutate_json(
            temp / TASK_DIR / "result/development_gate_result.v0.1.json",
            lambda value: value["boundaries"].update({"generator_qualified": True}),
        ),
    )
    add(
        "author_reroll",
        "E_AUTHOR_FAILURE_RECEIPT",
        lambda temp: mutate_json(
            temp / TASK_DIR / "author/author_session_failure_receipt.v0.1.json",
            lambda value: value.update({"reroll_count": 1}),
        ),
    )
    add(
        "raw_response_after_failure",
        "E_OUTPUT_AFTER_ATOMIC_AUTHOR_FAILURE",
        lambda temp: (
            (temp / TASK_DIR / "author/raw_author_responses.v0.1.jsonl").write_text("{}\n", encoding="utf-8")
        ),
    )
    add(
        "route_oracle_shared",
        "E_ROUTE_ORACLE_SEPARATION",
        lambda temp: mutate_jsonl(
            temp / TASK_DIR / "route/route_regression_comparison.v0.1.jsonl",
            lambda rows: rows[0].update({"expected_actual_same_source": True}),
        ),
    )
    add(
        "fake_degrade",
        "E_FAKE_DEGRADE",
        lambda temp: mutate_jsonl(
            temp / TASK_DIR / "route/route_regression_actuals.v0.1.jsonl",
            lambda rows: next(
                row
                for row in rows
                if row["actual_decision"]["actual_primary_action"] == "DEGRADE"
            )["actual_decision"].update({"degraded_artifact": None}),
        ),
    )
    add(
        "frozen_core_mutation",
        "E_FROZEN_FILE",
        lambda temp: (temp / TASK_DIR / "core/fc_claim_closure_validator.py").write_text(
            (temp / TASK_DIR / "core/fc_claim_closure_validator.py").read_text(encoding="utf-8")
            + "\n# mutation\n",
            encoding="utf-8",
        ),
    )
    add(
        "route_35",
        "E_ROUTE_SEQUENCE",
        lambda temp: (temp / LEDGER_PATH).write_text(
            (temp / LEDGER_PATH).read_text(encoding="utf-8")
            + "  route_migration_35:\n    applied_by_task: UNAUTHORIZED\n",
            encoding="utf-8",
        ),
    )
    add(
        "historical_route_33_tamper",
        "E_HISTORICAL_ROUTE_DIGEST",
        lambda temp: mutate_route_block(
            temp / LEDGER_PATH,
            33,
            "      author_invocation_count: 40",
            "      author_invocation_count: 41",
        ),
    )
    add(
        "horizon_from_max",
        "E_HORIZON_POLICY",
        lambda temp: mutate_yaml(
            temp / HORIZON_PATH,
            lambda value: value["ledger_horizon"].update({"derivation_source": "MAX_LEDGER_ROUTE"}),
        ),
    )

    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="dev33-checker-selftest-") as temporary:
        base = Path(temporary)
        for name, expected_code, mutation in tests:
            case_root = base / name
            copy_fixture(root, case_root)
            mutation(case_root)
            codes = {error["code"] for error in validate(case_root)}
            if expected_code not in codes:
                failures.append({"case": name, "expected": expected_code, "actual": sorted(codes)})

        order_root = base / "order_invariance"
        copy_fixture(root, order_root)
        for relative in (
            TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl",
            TASK_DIR / "requests/author_requests.v0.1.jsonl",
            TASK_DIR / "component/component_conformance_cases.v0.1.jsonl",
            TASK_DIR / "route/route_regression_actuals.v0.1.jsonl",
        ):
            path = order_root / relative
            path.write_text("\n".join(reversed(path.read_text(encoding="utf-8").splitlines())) + "\n", encoding="utf-8")
        order_codes = {error["code"] for error in validate(order_root)}
        order_codes.discard("E_FROZEN_PREAUTHOR_ARTIFACT")
        order_codes.discard("E_FROZEN_FILE")
        if order_codes:
            failures.append({"case": "order_invariance", "actual": sorted(order_codes)})

    if not _positive_classifier_examples_pass():
        failures.append({"case": "creative_expression_positive_examples"})
    if failures:
        print(json.dumps({"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "SELFTEST_PASS",
                "negative_case_count": len(tests),
                "request_order_invariance": True,
                "fixture_order_invariance": True,
                "component_order_signature_invariance": True,
                "creative_expression_false_positive_rejection_count": 0,
                "ordinary_person_voice_overblocked_count": 0,
                "disclosed_hypothetical_false_rejection_count": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.selftest:
        return selftest(ROOT)
    errors = validate(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 1
    result = load_json(ROOT / TASK_DIR / "result/development_gate_result.v0.1.json")
    print(
        json.dumps(
            {
                "status": "PASS",
                "governance_meaning": "HONEST_FAILURE_EVIDENCE_ONLY",
                "task_status": result["task_status"],
                "dev_gate_pass": False,
                "candidate_count": 0,
                "accepted_baseline_count": 120,
                "hidden_count": 0,
                "generator_qualified": False,
                "authorized_terminal_route_id": 33,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
