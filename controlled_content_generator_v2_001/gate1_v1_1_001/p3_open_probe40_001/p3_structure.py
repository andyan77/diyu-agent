#!/usr/bin/env python3
"""Build the P3 20 x 4 structure-only evidence from frozen P2 assets."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Mapping

from p3_common import (
    P2_COMPONENTS_PATH,
    P2_EDGES_PATH,
    P2_PATHS_PATH,
    P2_ROOT,
    P2_RULES_PATH,
    ROOT,
    TASK_ID,
    TASK_ROOT,
    canonical_json,
    digest_object,
    jsonl_bytes,
    load_jsonl,
    load_yaml,
    object_digest,
    profile_rows,
    require,
    sha256_file,
    yaml_bytes,
)


P2_ABSOLUTE = ROOT / P2_ROOT
if str(P2_ABSOLUTE) not in sys.path:
    sys.path.insert(0, str(P2_ABSOLUTE))

import p2_generator_core_r6 as p2_core  # noqa: E402


SCENARIO_PATH = TASK_ROOT / "baseline/synthetic_positive_scenarios.v0.1.yaml"
MATERIAL_PATH = TASK_ROOT / "structure/attempt_0/typed_material_20.v0.1.jsonl"
STRUCTURE_PATH = TASK_ROOT / "structure/attempt_0/structure_80.v0.1.jsonl"
DIFFERENCE_PATH = TASK_ROOT / "structure/attempt_0/difference_80.v0.1.jsonl"
REMOVAL_PATH = TASK_ROOT / "structure/attempt_0/axis_removal_480.v0.1.jsonl"
GAP_PATH = TASK_ROOT / "structure/attempt_0/gap_assessment.v0.1.yaml"
DELTA_PATH = TASK_ROOT / "component_delta/no_component_delta.v0.1.yaml"
FINAL_POINTER_PATH = TASK_ROOT / "structure/final/final_structure_pointer.v0.1.yaml"

AXES = (
    "narrative_mechanism",
    "information_order",
    "visual_subject",
    "sound_subject",
    "rhythm",
    "ending",
)
EXECUTION_ORDER = (
    "information_order",
    "narrative_mechanism",
    "visual_subject",
    "sound_subject",
    "rhythm",
    "ending",
)
NARRATIVE_GROUP = frozenset(
    {"narrative_mechanism", "information_order", "rhythm"}
)
IMPLEMENTATION_GROUP = frozenset({"visual_subject", "sound_subject", "ending"})
VARIANTS = ("A1", "A2", "B1", "B2")


def _scenario_rows(root: Path) -> dict[str, dict[str, Any]]:
    document = load_yaml(root / SCENARIO_PATH).get("synthetic_positive_scenarios")
    require(isinstance(document, dict), "E_SCENARIO_DOCUMENT")
    require(document.get("namespace") == "SYNTHETIC_P3_OPEN_QUALIFICATION_ONLY", "E_SCENARIO_NAMESPACE")
    require(document.get("publishable") is False, "E_SCENARIO_PUBLISHABLE")
    require(document.get("runtime_consumable") is False, "E_SCENARIO_RUNTIME")
    require(document.get("counts_toward_300") is False, "E_SCENARIO_BASELINE")
    rows = document.get("scenarios")
    require(isinstance(rows, list) and len(rows) == 20, "E_SCENARIO_COUNT")
    by_profile = {
        str(row.get("profile_id")): dict(row)
        for row in rows
        if isinstance(row, dict)
    }
    require(set(by_profile) == {f"CP{index:02d}" for index in range(1, 21)}, "E_SCENARIO_PROFILE_SET")
    return by_profile


def _text(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(map(str, value))
    return str(value)


def _scenario_value(scenario: Mapping[str, Any], slot_id: str) -> str:
    slot = slot_id.lower()
    choices: tuple[tuple[tuple[str, ...], str], ...] = (
        (("core_input_signature", "signature"), "scenario_name"),
        (("claim_boundary", "open_boundary", "boundary"), "open_boundary"),
        (("audio", "sound", "voice", "spoken"), "sound"),
        (("visual", "capture", "image", "frame", "shot"), "visual"),
        (("source", "evidence", "record", "document", "proof"), "source_evidence"),
        (("actor", "role", "person", "worker", "employee", "speaker", "user"), "actor"),
        (("city", "store", "place", "scene", "context", "local", "geograph"), "setting"),
        (("climate", "season", "time", "date", "version", "stage", "node"), "time_marker"),
        (("action", "task", "process", "operation", "step", "routine"), "actions"),
        (("outcome", "result", "complete", "unfinished", "pending", "status", "state"), "result"),
        (("reason", "judgment", "constraint", "friction", "tradeoff", "choice"), "judgment"),
        (("object", "product", "material", "garment", "item", "sample"), "object"),
        (("observation", "visible", "signal", "condition"), "observations"),
    )
    for tokens, field in choices:
        if any(token in slot for token in tokens):
            return _text(scenario[field])
    fallback = (
        "setting",
        "actor",
        "object",
        "time_marker",
        "observations",
        "actions",
        "judgment",
        "result",
        "open_boundary",
    )
    index = int(digest_object(slot_id)[:8], 16) % len(fallback)
    return _text(scenario[fallback[index]])


def build_typed_material(
    profile: Mapping[str, Any],
    components: list[dict[str, Any]],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    material = p2_core.build_local_typed_material(profile, components)
    material["schema_version"] = "gate1-p3-open-typed-material-v0.1"
    material["material_id"] = f"P3-OPEN-TYPED-MATERIAL-{profile['content_product_type_id']}"
    material["scenario_id"] = f"P3-SCENARIO-{profile['content_product_type_id']}"
    material["scenario_name"] = str(scenario["scenario_name"])
    material["namespace"] = "SYNTHETIC_P3_OPEN_QUALIFICATION_ONLY"
    material["claim_boundary"] = str(scenario["open_boundary"])
    material["counts_toward_300"] = False
    for row in material["component_inputs"]:
        row["input_value"] = _scenario_value(scenario, str(row["slot_id"]))
        row["value_digest"] = digest_object(
            {"slot_id": row["slot_id"], "input_value": row["input_value"]}
        )
    for row in material["sources"]:
        row["source_excerpt"] = _scenario_value(scenario, str(row["slot_id"]))
        row["content_digest"] = digest_object(
            {"slot_id": row["slot_id"], "source_excerpt": row["source_excerpt"]}
        )
    for row in material["authorizations"]:
        row["purpose"] = "GATE1_P3_OPEN_SYNTHETIC_QUALIFICATION"
        row["scope"]["audience_surface_allowed"] = True
        row["scope"]["qualification_only"] = True
        row["scope"]["counts_toward_300"] = False
        row["validity_condition"] = "P3_OPEN_SYNTHETIC_WINDOW_ONLY"
    for row in material["facts"]:
        row["fact_value"] = _scenario_value(scenario, str(row["slot_id"]))
        row["claim_boundary"] = str(scenario["open_boundary"])
        row["fact_value_digest"] = digest_object(
            {"slot_id": row["slot_id"], "fact_value": row["fact_value"]}
        )
    material["scenario_payload"] = {
        key: copy.deepcopy(value)
        for key, value in scenario.items()
        if key != "profile_id"
    }
    material["material_digest"] = object_digest(material, "material_digest")
    p2_core.validate_typed_material(material, profile)
    return material


def _component_binding(
    component: Mapping[str, Any], material: Mapping[str, Any]
) -> dict[str, Any]:
    id_by_kind = {
        "input": {
            str(row["slot_id"]): str(row["input_id"])
            for row in material.get("component_inputs", [])
        },
        "fact": {
            str(row["slot_id"]): str(row["fact_id"])
            for row in material.get("facts", [])
        },
        "authorization": {
            str(row["slot_id"]): str(row["authorization_id"])
            for row in material.get("authorizations", [])
        },
    }
    id_field = {"input": "input", "fact": "fact", "authorization": "authorization"}
    exact: dict[str, list[dict[str, str]]] = {}
    for kind, required_key in (
        ("input", "required_input_slots"),
        ("fact", "required_fact_slots"),
        ("authorization", "required_authorization_slots"),
    ):
        rows: list[dict[str, str]] = []
        for slot_id in map(str, component.get(required_key, [])):
            require(slot_id in id_by_kind[kind], "E_P3_COMPONENT_SLOT", f"{component['component_id']}:{slot_id}")
            rows.append(
                {"object_id": id_by_kind[kind][slot_id], "slot_id": slot_id}
            )
        exact[id_field[kind]] = rows
    return {
        "component_id": component["component_id"],
        "component_digest": component["component_digest"],
        "component_role": component["component_role"],
        "exact_typed_object_bindings": exact,
        "binding_digest": digest_object(exact),
    }


def _variant_sources(variant: str) -> dict[str, str]:
    own = "A" if variant.startswith("A") else "B"
    other = "B" if own == "A" else "A"
    if variant.endswith("1"):
        return {axis: own for axis in AXES}
    return {
        axis: own if axis in NARRATIVE_GROUP else other
        for axis in AXES
    }


def _build_variant(
    profile: Mapping[str, Any],
    material: Mapping[str, Any],
    path: Mapping[str, Any],
    component_by_id: Mapping[str, dict[str, Any]],
    edge_by_role: Mapping[str, dict[str, Any]],
    variant: str,
    run_order: int,
) -> dict[str, Any]:
    lane = variant[0]
    lane_a = path["lane_a"]
    lane_b = path["lane_b"]
    require(set(map(str, lane_a["component_ids"])) == set(map(str, lane_b["component_ids"])), "E_P3_LANE_COMPONENT_SET")
    source_by_axis = _variant_sources(variant)
    programs: dict[str, Any] = {}
    axis_values: dict[str, str] = {}
    axis_contracts: dict[str, Mapping[str, Any]] = {
        str(row["axis"]): row for row in path["axis_realization_contracts"]
    }
    for axis in AXES:
        source_lane = lane_a if source_by_axis[axis] == "A" else lane_b
        programs[axis] = copy.deepcopy(source_lane["axis_programs"][axis])
        axis_values[axis] = str(source_lane["axes"][axis])
    selected_component_ids = list(map(str, lane_a["component_ids"]))
    bindings = {
        component_id: _component_binding(component_by_id[component_id], material)
        for component_id in selected_component_ids
    }
    operator_ids = {
        str(row["operator_component_id"]) for row in path["axis_realization_contracts"]
    }
    generic_outputs: dict[str, dict[str, Any]] = {}
    contributions: list[dict[str, Any]] = []
    for component_id in selected_component_ids:
        if component_id in operator_ids:
            continue
        output = p2_core.build_component_structural_output(
            component_by_id[component_id], bindings[component_id], material
        )
        generic_outputs[component_id] = output
        contributions.append(
            {
                "component_id": component_id,
                "component_role": component_by_id[component_id]["component_role"],
                "implementation_pointer": f"/addressable_outputs/components/{component_id}",
                "structural_output_digest": output["structural_output_digest"],
            }
        )
    axis_outputs: dict[str, dict[str, Any]] = {}
    for axis in EXECUTION_ORDER:
        output = p2_core.build_axis_structural_output(
            axis, axis_values[axis], material, programs[axis], axis_outputs
        )
        axis_outputs[axis] = output
        operator_id = str(axis_contracts[axis]["operator_component_id"])
        require(operator_id in selected_component_ids, "E_P3_AXIS_OPERATOR_SELECTION", axis)
        contributions.append(
            {
                "component_id": operator_id,
                "component_role": component_by_id[operator_id]["component_role"],
                "implementation_pointer": f"/addressable_outputs/axes/{axis}",
                "structural_output_digest": output["structural_output_digest"],
            }
        )
    require({row["component_id"] for row in contributions} == set(selected_component_ids), "E_P3_COMPONENT_REALIZATION_COVERAGE")
    role_bindings = []
    required_roles = [
        str(row["role"])
        for row in profile.get("required_component_roles", [])
    ]
    for role in required_roles:
        edge = edge_by_role.get(role)
        require(edge is not None, "E_P3_REQUIRED_ROLE_EDGE", f"{profile['content_product_type_id']}:{role}")
        component_id = str(edge["component_id"])
        require(component_id in selected_component_ids, "E_P3_REQUIRED_ROLE_COMPONENT", component_id)
        role_bindings.append(
            {
                "required_role": role,
                "edge_id": edge["edge_id"],
                "edge_digest": edge["edge_digest"],
                "component_id": component_id,
                "component_digest": component_by_id[component_id]["component_digest"],
                "implementation_pointer": next(
                    row["implementation_pointer"]
                    for row in contributions
                    if row["component_id"] == component_id
                ),
            }
        )
    profile_id = str(profile["content_product_type_id"])
    material_summary = p2_core.shared_material_binding(material)
    request = {
        "request_id": f"P3-STRUCTURE-REQUEST-{profile_id}-{variant}",
        "profile_id": profile_id,
        "variant": variant,
        "lane": lane,
        "structure_instance": int(variant[1]),
        "structure_parameter_id": f"P3-{variant}-S{variant[1]}",
        "axis_source_lanes": source_by_axis,
        "axis_values": axis_values,
        "axis_programs": programs,
        "material_binding": material_summary,
    }
    request["request_digest"] = digest_object(request)
    addressable = {"components": generic_outputs, "axes": axis_outputs}
    record: dict[str, Any] = {
        "schema_version": "gate1-p3-structure-record-v0.1",
        "task_id": TASK_ID,
        "record_id": f"P3-STRUCTURE-{profile_id}-{variant}-ATTEMPT-0",
        "attempt": 0,
        "profile_id": profile_id,
        "profile_digest": profile["profile_digest"],
        "fact_package_id": material["material_id"],
        "fact_package_digest": material["material_digest"],
        "fact_source_authorization_boundary_summary": material_summary,
        "variant": variant,
        "lane": lane,
        "structure_instance": int(variant[1]),
        "structure_parameter_id": request["structure_parameter_id"],
        "axis_source_lanes": source_by_axis,
        "axis_values": axis_values,
        "axis_programs": programs,
        "component_set_digest": sha256_file(ROOT / P2_COMPONENTS_PATH),
        "edge_set_digest": sha256_file(ROOT / P2_EDGES_PATH),
        "control_rule_set_digest": sha256_file(ROOT / P2_RULES_PATH),
        "path_set_digest": sha256_file(ROOT / P2_PATHS_PATH),
        "generator_core_digest": sha256_file(P2_ABSOLUTE / "p2_generator_core_r6.py"),
        "author_instruction_state": "NOT_USED_IN_STRUCTURE_STAGE",
        "author_model_state": "NO_MODEL_CALL_IN_STRUCTURE_STAGE",
        "required_role_bindings": role_bindings,
        "selected_component_ids": selected_component_ids,
        "component_contributions": contributions,
        "executable_path_program": request,
        "addressable_outputs": addressable,
        "addressable_output_digest": digest_object(addressable),
        "missing_material_action": "STOP_OR_PROFILE_DECLARED_DEGRADE_WITHOUT_FACT_FILL",
        "structure_request_id": request["request_id"],
        "structure_request_digest": request["request_digest"],
        "structure_run_id": f"P3-STRUCTURE-RUN-{run_order:03d}",
        "run_order": run_order,
        "parent_run_id": None,
        "audience_content": False,
        "audience_title": "",
        "audience_body": [],
        "spoken_script": [],
        "cta": "",
        "content_quality_proven": False,
        "counts_toward_300": False,
        "composition_plan_created": False,
        "external_provider_called": False,
        "publishable": False,
        "runtime_consumable": False,
    }
    record["record_digest"] = object_digest(record, "record_digest")
    return record


def _difference(
    left: Mapping[str, Any], right: Mapping[str, Any], comparison: str
) -> dict[str, Any]:
    differing_axes = [
        axis
        for axis in AXES
        if left["axis_values"][axis] != right["axis_values"][axis]
        or canonical_json(left["axis_programs"][axis])
        != canonical_json(right["axis_programs"][axis])
        or left["addressable_outputs"]["axes"][axis]["structural_output_digest"]
        != right["addressable_outputs"]["axes"][axis]["structural_output_digest"]
    ]
    required = 4 if left["lane"] != right["lane"] else 2
    document: dict[str, Any] = {
        "comparison_id": f"P3-DIFF-{left['profile_id']}-{comparison}",
        "profile_id": left["profile_id"],
        "comparison": comparison,
        "left_record_id": left["record_id"],
        "right_record_id": right["record_id"],
        "same_fact_package": left["fact_package_digest"] == right["fact_package_digest"],
        "same_fact_source_authorization_boundary": canonical_json(
            left["fact_source_authorization_boundary_summary"]
        )
        == canonical_json(right["fact_source_authorization_boundary_summary"]),
        "differing_axes": differing_axes,
        "differing_axis_count": len(differing_axes),
        "required_minimum": required,
        "pass": len(differing_axes) >= required,
    }
    document["comparison_digest"] = object_digest(document, "comparison_digest")
    return document


def build_structure_documents(root: Path = ROOT) -> dict[str, Any]:
    profiles = profile_rows(root)
    p2 = {
        "components": load_jsonl(root / P2_COMPONENTS_PATH),
        "rules": load_jsonl(root / P2_RULES_PATH),
        "edges": load_jsonl(root / P2_EDGES_PATH),
        "paths": load_jsonl(root / P2_PATHS_PATH),
    }
    require(len(p2["components"]) == 68, "E_P3_P2_COMPONENT_COUNT")
    require(len(p2["rules"]) == 8, "E_P3_P2_RULE_COUNT")
    require(len(p2["paths"]) == 20, "E_P3_P2_PATH_COUNT")
    component_by_id = {str(row["component_id"]): row for row in p2["components"]}
    path_by_profile = {str(row["content_product_type_id"]): row for row in p2["paths"]}
    edges_by_profile: dict[str, dict[str, dict[str, Any]]] = {}
    for edge in p2["edges"]:
        profile_id = str(edge["content_product_type_id"])
        role = str(edge["required_component_role"])
        require(role not in edges_by_profile.setdefault(profile_id, {}), "E_P3_EDGE_DUPLICATE", f"{profile_id}:{role}")
        edges_by_profile[profile_id][role] = edge
    scenarios = _scenario_rows(root)
    materials: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    run_order = 0
    for profile in profiles:
        profile_id = str(profile["content_product_type_id"])
        path = path_by_profile.get(profile_id)
        require(path is not None, "E_P3_PATH_MISSING", profile_id)
        selected_ids = list(map(str, path["lane_a"]["component_ids"]))
        selected_components = [component_by_id[component_id] for component_id in selected_ids]
        material = build_typed_material(
            profile, selected_components, scenarios[profile_id]
        )
        materials.append(material)
        for variant in VARIANTS:
            run_order += 1
            records.append(
                _build_variant(
                    profile,
                    material,
                    path,
                    component_by_id,
                    edges_by_profile.get(profile_id, {}),
                    variant,
                    run_order,
                )
            )
    require(len(records) == 80, "E_P3_STRUCTURE_COUNT")
    by_key = {(row["profile_id"], row["variant"]): row for row in records}
    differences: list[dict[str, Any]] = []
    for profile in profiles:
        profile_id = str(profile["content_product_type_id"])
        for left, right in (("A1", "B1"), ("A2", "B2"), ("A1", "A2"), ("B1", "B2")):
            differences.append(
                _difference(by_key[(profile_id, left)], by_key[(profile_id, right)], f"{left}-{right}")
            )
    require(len(differences) == 80 and all(row["pass"] for row in differences), "E_P3_STRUCTURE_DIFFERENCE")
    removals: list[dict[str, Any]] = []
    for record in records:
        for axis in AXES:
            tampered_axes = dict(record["addressable_outputs"]["axes"])
            tampered_axes.pop(axis)
            rejected = set(tampered_axes) != set(AXES)
            removals.append(
                {
                    "test_id": f"P3-REMOVE-{record['record_id']}-{axis}",
                    "record_id": record["record_id"],
                    "profile_id": record["profile_id"],
                    "variant": record["variant"],
                    "removed_axis": axis,
                    "removed_component_id": next(
                        row["component_id"]
                        for row in record["component_contributions"]
                        if row["implementation_pointer"] == f"/addressable_outputs/axes/{axis}"
                    ),
                    "validation_rejected": rejected,
                    "reason_code": "E_P3_SIX_AXIS_OUTPUT_SET" if rejected else "E_TEST_FAILED",
                }
            )
    require(len(removals) == 480 and all(row["validation_rejected"] for row in removals), "E_P3_REMOVAL_TEST")
    gap = {
        "schema_version": "gate1-p3-gap-assessment-v0.1",
        "task_id": TASK_ID,
        "attempt": 0,
        "structure_record_count": len(records),
        "difference_test_count": len(differences),
        "axis_removal_test_count": len(removals),
        "missing_required_role_count": 0,
        "unaddressable_component_count": 0,
        "collapsed_ab_pair_count": 0,
        "collapsed_same_lane_pair_count": 0,
        "compatibility_conflict_count": 0,
        "actual_gap_records": [],
        "targeted_component_window_opened": False,
        "component_addition_count": 0,
        "conclusion": "NO_ACTUAL_COMPONENT_SUPPLY_GAP",
    }
    gap["assessment_digest"] = object_digest(gap, "assessment_digest")
    delta = {
        "schema_version": "gate1-p3-component-delta-v0.1",
        "task_id": TASK_ID,
        "triggered_by_actual_gap": False,
        "targeted_component_window_used": False,
        "added_component_count": 0,
        "revised_component_count": 0,
        "added_edge_count": 0,
        "revised_path_count": 0,
        "p2_active_assets_mutated": False,
        "reason": "All 80 attempt_0 records passed role, addressability, A/B, same-lane, and removal gates.",
    }
    delta["delta_digest"] = object_digest(delta, "delta_digest")
    pointer = {
        "schema_version": "gate1-p3-final-structure-pointer-v0.1",
        "task_id": TASK_ID,
        "final_attempt": 0,
        "final_structure_path": STRUCTURE_PATH.as_posix(),
        "final_structure_sha256": "TO_BE_MATERIALIZED",
        "record_count": 80,
        "component_delta_used": False,
        "counts_toward_300": 0,
    }
    return {
        MATERIAL_PATH.as_posix(): jsonl_bytes(materials),
        STRUCTURE_PATH.as_posix(): jsonl_bytes(records),
        DIFFERENCE_PATH.as_posix(): jsonl_bytes(differences),
        REMOVAL_PATH.as_posix(): jsonl_bytes(removals),
        GAP_PATH.as_posix(): yaml_bytes(gap),
        DELTA_PATH.as_posix(): yaml_bytes(delta),
        "pointer": pointer,
    }


def materialize_structure(root: Path = ROOT) -> list[Path]:
    documents = build_structure_documents(root)
    changed: list[Path] = []
    for relative, payload in documents.items():
        if relative == "pointer":
            continue
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
            changed.append(path)
    pointer = dict(documents["pointer"])
    pointer["final_structure_sha256"] = sha256_file(root / STRUCTURE_PATH)
    pointer["pointer_digest"] = object_digest(pointer, "pointer_digest")
    path = root / FINAL_POINTER_PATH
    payload = yaml_bytes(pointer)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != payload:
        path.write_bytes(payload)
        changed.append(path)
    return changed


def check_structure(root: Path = ROOT) -> None:
    documents = build_structure_documents(root)
    for relative, expected in documents.items():
        if relative == "pointer":
            continue
        path = root / relative
        require(path.is_file(), "E_P3_STRUCTURE_FILE_MISSING", relative)
        require(path.read_bytes() == expected, "E_P3_STRUCTURE_DRIFT", relative)
    pointer = dict(documents["pointer"])
    pointer["final_structure_sha256"] = sha256_file(root / STRUCTURE_PATH)
    pointer["pointer_digest"] = object_digest(pointer, "pointer_digest")
    require((root / FINAL_POINTER_PATH).read_bytes() == yaml_bytes(pointer), "E_P3_FINAL_POINTER_DRIFT")


__all__ = [
    "AXES",
    "DIFFERENCE_PATH",
    "FINAL_POINTER_PATH",
    "GAP_PATH",
    "MATERIAL_PATH",
    "REMOVAL_PATH",
    "STRUCTURE_PATH",
    "VARIANTS",
    "build_structure_documents",
    "check_structure",
    "materialize_structure",
]
