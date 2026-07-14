#!/usr/bin/env python3
"""Materialize the single authorized P3 open-repair attempt."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from p3_common import (
    AUTHORIZED_AUTHOR_CAPABILITY_ID,
    AUTHORIZED_AUTHOR_IDENTITY,
    AUTHORIZED_AUTHOR_MODEL_LABEL,
    AUTHORIZED_AUTHOR_SESSION,
    BASELINE_COMMIT,
    P2_COMPONENTS_PATH,
    P2_EDGES_PATH,
    P2_PATHS_PATH,
    P2_ROOT,
    P2_RULES_PATH,
    ROOT,
    TASK_ID,
    TASK_ROOT,
    digest_object,
    jsonl_bytes,
    load_jsonl,
    load_yaml,
    object_digest,
    profile_rows,
    readiness_false,
    require,
    sha256_bytes,
    sha256_file,
    yaml_bytes,
)
from p3_prepare import _route_selection
from p3_structure import (
    AXES,
    VARIANTS,
    _build_variant,
    _difference,
    p2_core,
)


ATTEMPT_0_FAILURE_COMMIT = "80501c4c502fd28fcad53d0e8a07144875b73036"
AUTHOR_PLATFORM_AGENT_ID = "019f5f1b-eca1-7be3-9038-5464fb0ed0f6"

SCENARIO_V1_PATH = TASK_ROOT / "baseline/synthetic_positive_scenarios.v0.1.yaml"
SCENARIO_V2_PATH = TASK_ROOT / "baseline/synthetic_positive_scenarios.v0.2.yaml"
REPAIR_BASIS_PATH = TASK_ROOT / "repair/attempt_1/repair_basis.v0.1.yaml"
ATTEMPT_0_INTEGRITY_PATH = (
    TASK_ROOT / "repair/attempt_1/attempt_0_integrity_manifest.v0.1.jsonl"
)
MATERIAL_R1_PATH = TASK_ROOT / "structure/attempt_1/typed_material_20.v0.2.jsonl"
STRUCTURE_R1_PATH = TASK_ROOT / "structure/attempt_1/structure_80.v0.2.jsonl"
DIFFERENCE_R1_PATH = TASK_ROOT / "structure/attempt_1/difference_80.v0.2.jsonl"
REMOVAL_R1_PATH = TASK_ROOT / "structure/attempt_1/axis_removal_480.v0.2.jsonl"
GAP_R1_PATH = TASK_ROOT / "structure/attempt_1/gap_assessment.v0.2.yaml"
FINAL_POINTER_R1_PATH = TASK_ROOT / "structure/final/final_structure_pointer.v0.2.yaml"
AUTHOR_INSTRUCTION_R1_PATH = (
    TASK_ROOT / "freeze/attempt_1/controlled_author_instruction.v0.2.md"
)
AUTHOR_MODEL_R1_PATH = TASK_ROOT / "freeze/attempt_1/author_model_and_session.v0.2.yaml"
ASSIGNMENT_R1_PATH = (
    TASK_ROOT / "freeze/attempt_1/positive_structure_assignment_20.v0.2.jsonl"
)
AUTHOR_REQUEST_R1_PATH = (
    TASK_ROOT / "freeze/attempt_1/positive_author_requests_20.v0.2.jsonl"
)
ROUTE_SELECTION_R1_PATH = TASK_ROOT / "freeze/attempt_1/route_selection_20.v0.2.jsonl"
ROUTE_INPUT_R1_PATH = TASK_ROOT / "freeze/attempt_1/route_inputs_20.v0.2.jsonl"
FREEZE_MANIFEST_R1_PATH = TASK_ROOT / "freeze/attempt_1/p3_open_repair_freeze.v0.2.yaml"
ATTEMPT_0_RESULT_PATH = TASK_ROOT / "result/p3_open_probe40_result.v0.1.yaml"
ATTEMPT_0_REVIEW_ONE_PATH = TASK_ROOT / "review/signed_content_value_review.v0.1.json"
ATTEMPT_0_REVIEW_TWO_PATH = TASK_ROOT / "review/signed_fact_authorization_review.v0.1.json"
ATTEMPT_0_ADJUDICATION_PATH = TASK_ROOT / "review/targeted_adjudication.v0.1.json"

SCENARIO_OVERRIDES: dict[str, dict[str, Any]] = {
    "CP02": {
        "observations": [
            "上午展示盘为空",
            "午后回收件右肩线偏离展示标记",
            "晚间完成肩线复位与分类但尚未归架",
        ],
        "actions": [
            "固定机位记录",
            "午后将回收件肩线恢复到展示标记",
            "标记状态变化",
            "晚间留下待归架标签",
        ],
        "result": "三个时段形成同一空间从空盘、肩线复位到待归架的状态序列",
    },
    "CP14": {
        "object": "一片无品牌测试材料与一张中性灰参照卡",
        "observations": [
            "参照卡放入同一固定侧光后，材料表面的明暗边界可对照",
            "材料被轻推后形成一道折线",
            "松手后折线部分减弱但仍可见",
        ],
        "actions": [
            "平放测试材料",
            "在同一侧光下放置中性灰参照卡",
            "轻推一次",
            "停手",
            "保持镜头观察",
        ],
        "visual": "正常速度、参照卡同光位、一次接触动作、固定侧光、无旁白",
    },
    "CP15": {
        "setting": "合成门店后场状态工作台、整烫台和陈列区",
        "observations": [
            "工作台按已核对、待复核两组留位",
            "两件核对通过",
            "一件标签待复核",
            "已通过件完成整烫并进入陈列准备",
        ],
        "actions": [
            "收货核对",
            "按状态重排工作台上的三件样衣",
            "状态标记",
            "整烫",
            "陈列前复核",
        ],
        "visual": "全景状态图切到工作台分组与每个岗位的局部动作",
    },
}

ROLE_SCENARIO_FIELDS: dict[str, tuple[str, ...]] = {
    "scene": ("setting", "time_marker", "object"),
    "trigger": ("scenario_name", "time_marker", "observations"),
    "observable_action": ("actions", "observations", "result"),
    "transition": ("actions", "observations", "result"),
    "visual_beat": ("observations", "visual"),
    "capture_instruction": ("actions", "visual", "sound"),
    "professional_judgment": ("observations", "judgment"),
    "audience_facing_reasoning_move": (
        "observations",
        "judgment",
        "result",
    ),
    "closing": ("judgment", "result", "open_boundary"),
}


def _text(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(map(str, value))
    return str(value)


def _scenario_v2(root: Path) -> dict[str, Any]:
    source = load_yaml(root / SCENARIO_V1_PATH)["synthetic_positive_scenarios"]
    document = copy.deepcopy(source)
    document["schema_version"] = "v0.2"
    document["repair_attempt"] = 1
    document["repair_parent_commit"] = ATTEMPT_0_FAILURE_COMMIT
    document["repair_scope"] = (
        "SYSTEMATIC_COMPONENT_REALIZATION_AND_PRODUCT_DETAIL_ALIGNMENT"
    )
    for scenario in document["scenarios"]:
        scenario.update(copy.deepcopy(SCENARIO_OVERRIDES.get(scenario["profile_id"], {})))
    document["scenario_set_digest"] = object_digest(
        document, "scenario_set_digest"
    )
    return document


def _scenario_value_r1(scenario: Mapping[str, Any], slot_id: str) -> str:
    slot = slot_id.lower()
    ordered_rules: tuple[tuple[tuple[str, ...], str], ...] = (
        (("claim_boundary", "boundary", "prohibit"), "open_boundary"),
        (("sound", "audio", "spoken"), "sound"),
        (
            (
                "action",
                "handoff",
                "routine",
                "operation",
                "step",
                "movement",
                "contact_sequence",
            ),
            "actions",
        ),
        (
            (
                "option",
                "abandon",
                "tradeoff",
                "cost",
                "constraint",
                "deviation",
                "commitment",
                "promise",
            ),
            "observations",
        ),
        (
            (
                "observation",
                "visible_state",
                "visible_states",
                "signal",
                "condition",
                "difference",
                "mapping_evidence",
                "state_evidence",
            ),
            "observations",
        ),
        (("result", "outcome", "complete", "unfinished", "pending"), "result"),
        (("judgment", "reason", "choice", "decision"), "judgment"),
        (("actor", "role", "person", "worker", "employee", "speaker"), "actor"),
        (("object", "product", "material", "garment", "item", "sample"), "object"),
        (("time", "date", "version", "stage", "node", "anchor"), "time_marker"),
        (("city", "store", "place", "scene", "context", "local"), "setting"),
        (("source", "evidence", "record", "document", "proof"), "source_evidence"),
        (("visual", "image", "frame", "shot", "capture"), "visual"),
    )
    for tokens, field in ordered_rules:
        if any(token in slot for token in tokens):
            return _text(scenario[field])
    fallback = (
        "observations",
        "actions",
        "judgment",
        "result",
        "setting",
        "object",
        "time_marker",
    )
    return _text(scenario[fallback[int(digest_object(slot_id)[:8], 16) % len(fallback)]])


def _rename_material_objects(material: dict[str, Any]) -> None:
    source_map = {
        row["source_id"]: str(row["source_id"]).replace("LOCAL-", "LOCAL-R1-", 1)
        for row in material["sources"]
    }
    authorization_map = {
        row["authorization_id"]: str(row["authorization_id"]).replace(
            "LOCAL-", "LOCAL-R1-", 1
        )
        for row in material["authorizations"]
    }
    for row in material["sources"]:
        row["source_id"] = source_map[row["source_id"]]
    for row in material["authorizations"]:
        row["authorization_id"] = authorization_map[row["authorization_id"]]
        row["subject_id"] = str(row["subject_id"]).replace(
            "SYNTHETIC-SUBJECT", "SYNTHETIC-R1-SUBJECT", 1
        )
    for row in material["component_inputs"]:
        row["input_id"] = str(row["input_id"]).replace("LOCAL-", "LOCAL-R1-", 1)
    for row in material["facts"]:
        row["fact_id"] = str(row["fact_id"]).replace("LOCAL-", "LOCAL-R1-", 1)
        row["source_ids"] = [source_map[value] for value in row["source_ids"]]
        row["authorization_ids"] = [
            authorization_map[value] for value in row["authorization_ids"]
        ]


def _explicit_scenario_facts(
    material: dict[str, Any], scenario: Mapping[str, Any]
) -> dict[str, list[str]]:
    profile_id = str(material["profile_id"])
    source_ids = [str(row["source_id"]) for row in material["sources"]]
    authorization_ids = [
        str(row["authorization_id"]) for row in material["authorizations"]
    ]
    by_field: dict[str, list[str]] = {}
    fields = (
        "scenario_name",
        "setting",
        "actor",
        "object",
        "time_marker",
        "source_evidence",
        "observations",
        "actions",
        "judgment",
        "result",
        "open_boundary",
        "sound",
        "visual",
    )
    for field in fields:
        values: Sequence[Any]
        value = scenario[field]
        values = value if isinstance(value, list) else [value]
        for index, item in enumerate(values, 1):
            fact_id = f"P3-R1-FACT-{profile_id}-{field.upper()}-{index:02d}"
            slot_id = f"p3_r1_{field}_{index:02d}"
            fact = {
                "fact_id": fact_id,
                "object_type": "FACT_OBJECT",
                "slot_id": slot_id,
                "fact_value": str(item),
                "fact_value_digest": digest_object(
                    {"slot_id": slot_id, "fact_value": str(item)}
                ),
                "source_ids": source_ids,
                "authorization_ids": authorization_ids,
                "claim_boundary": str(scenario["open_boundary"]),
                "synthetic_test_only": True,
                "may_be_treated_as_brand_truth": False,
            }
            material["facts"].append(fact)
            by_field.setdefault(field, []).append(fact_id)
    return by_field


def _build_material_r1(
    profile: Mapping[str, Any],
    components: list[dict[str, Any]],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    from p3_structure import build_typed_material

    material = build_typed_material(profile, components, scenario)
    _rename_material_objects(material)
    material["schema_version"] = "gate1-p3-open-typed-material-v0.2"
    material["material_id"] = f"P3-OPEN-TYPED-MATERIAL-{profile['content_product_type_id']}-ATTEMPT-1"
    material["repair_attempt"] = 1
    material["repair_parent_commit"] = ATTEMPT_0_FAILURE_COMMIT
    material["scenario_payload"] = copy.deepcopy(dict(scenario))
    for row in material["component_inputs"]:
        row["input_value"] = _scenario_value_r1(scenario, str(row["slot_id"]))
        row["value_digest"] = digest_object(
            {"slot_id": row["slot_id"], "input_value": row["input_value"]}
        )
    for row in material["sources"]:
        row["source_excerpt"] = _text(scenario["source_evidence"])
        row["content_digest"] = digest_object(
            {"slot_id": row["slot_id"], "source_excerpt": row["source_excerpt"]}
        )
    for row in material["facts"]:
        row["fact_value"] = _scenario_value_r1(scenario, str(row["slot_id"]))
        row["claim_boundary"] = str(scenario["open_boundary"])
        row["fact_value_digest"] = digest_object(
            {"slot_id": row["slot_id"], "fact_value": row["fact_value"]}
        )
    explicit = _explicit_scenario_facts(material, scenario)
    material["product_core_surface_requirements"] = [
        {
            "requirement_id": f"P3-R1-CORE-{profile['content_product_type_id']}-{field.upper()}",
            "semantic_kind": field,
            "fact_ids": explicit[field],
            "required_values": [
                next(
                    row["fact_value"]
                    for row in material["facts"]
                    if row["fact_id"] == fact_id
                )
                for fact_id in explicit[field]
            ],
            "must_be_concretely_realized": True,
            "generic_summary_not_sufficient": True,
        }
        for field in ("observations", "actions", "judgment", "result")
    ]
    realization_rows: list[dict[str, Any]] = []
    for component in components:
        role = str(component["component_role"])
        if role not in ROLE_SCENARIO_FIELDS:
            continue
        fields = ROLE_SCENARIO_FIELDS[role]
        fact_ids = [fact_id for field in fields for fact_id in explicit[field]]
        require(bool(fact_ids), "E_P3_R1_COMPONENT_REALIZATION_FACTS", component["component_id"])
        realization_rows.append(
            {
                "component_id": component["component_id"],
                "component_digest": component["component_digest"],
                "component_role": role,
                "actual_mechanism": component["mechanism"],
                "evidence_fields": list(fields),
                "evidence_fact_ids": fact_ids,
                "must_change_or_reject_if_removed": True,
                "field_binding_alone_is_not_surface_realization": True,
            }
        )
    material["component_realization_requirements"] = realization_rows
    material["material_digest"] = object_digest(material, "material_digest")
    p2_core.validate_typed_material(material, profile)
    return material


def _version_record_r1(
    record: dict[str, Any], parent_record: Mapping[str, Any]
) -> dict[str, Any]:
    record["schema_version"] = "gate1-p3-structure-record-v0.2"
    record["record_id"] = str(record["record_id"]).replace("ATTEMPT-0", "ATTEMPT-1")
    record["attempt"] = 1
    record["repair_parent_record_id"] = parent_record["record_id"]
    record["repair_parent_record_digest"] = parent_record["record_digest"]
    request = record["executable_path_program"]
    request["request_id"] = f"P3-R1-STRUCTURE-REQUEST-{record['profile_id']}-{record['variant']}"
    request["attempt"] = 1
    request["request_digest"] = digest_object(request)
    record["structure_request_id"] = request["request_id"]
    record["structure_request_digest"] = request["request_digest"]
    record["structure_run_id"] = f"P3-R1-STRUCTURE-RUN-{int(record['run_order']):03d}"
    record["parent_run_id"] = parent_record["structure_run_id"]
    record["record_digest"] = object_digest(record, "record_digest")
    return record


def _build_structure_r1(
    root: Path, scenarios: Mapping[str, Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    profiles = profile_rows(root)
    components = load_jsonl(root / P2_COMPONENTS_PATH)
    edges = load_jsonl(root / P2_EDGES_PATH)
    paths = load_jsonl(root / P2_PATHS_PATH)
    component_by_id = {str(row["component_id"]): row for row in components}
    path_by_profile = {str(row["content_product_type_id"]): row for row in paths}
    edge_by_profile: dict[str, dict[str, dict[str, Any]]] = {}
    for edge in edges:
        profile_id = str(edge["content_product_type_id"])
        role = str(edge["required_component_role"])
        require(role not in edge_by_profile.setdefault(profile_id, {}), "E_P3_R1_EDGE_DUPLICATE")
        edge_by_profile[profile_id][role] = edge
    parent_records = {
        (str(row["profile_id"]), str(row["variant"])): row
        for row in load_jsonl(root / TASK_ROOT / "structure/attempt_0/structure_80.v0.1.jsonl")
    }
    materials: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    run_order = 0
    for profile in profiles:
        profile_id = str(profile["content_product_type_id"])
        path = path_by_profile[profile_id]
        selected = [
            component_by_id[str(component_id)]
            for component_id in path["lane_a"]["component_ids"]
        ]
        material = _build_material_r1(profile, selected, scenarios[profile_id])
        materials.append(material)
        for variant in VARIANTS:
            run_order += 1
            record = _build_variant(
                profile,
                material,
                path,
                component_by_id,
                edge_by_profile[profile_id],
                variant,
                run_order,
            )
            records.append(
                _version_record_r1(record, parent_records[(profile_id, variant)])
            )
    require(len(materials) == 20 and len(records) == 80, "E_P3_R1_STRUCTURE_COUNT")
    by_key = {(row["profile_id"], row["variant"]): row for row in records}
    differences: list[dict[str, Any]] = []
    for profile in profiles:
        profile_id = str(profile["content_product_type_id"])
        for left, right in (("A1", "B1"), ("A2", "B2"), ("A1", "A2"), ("B1", "B2")):
            row = _difference(
                by_key[(profile_id, left)],
                by_key[(profile_id, right)],
                f"{left}-{right}",
            )
            row["comparison_id"] = f"P3-R1-DIFF-{profile_id}-{left}-{right}"
            row["attempt"] = 1
            row["comparison_digest"] = object_digest(row, "comparison_digest")
            differences.append(row)
    removals: list[dict[str, Any]] = []
    for record in records:
        for axis in AXES:
            row = {
                "test_id": f"P3-R1-REMOVE-{record['record_id']}-{axis}",
                "record_id": record["record_id"],
                "profile_id": record["profile_id"],
                "variant": record["variant"],
                "attempt": 1,
                "removed_axis": axis,
                "removed_component_id": next(
                    item["component_id"]
                    for item in record["component_contributions"]
                    if item["implementation_pointer"]
                    == f"/addressable_outputs/axes/{axis}"
                ),
                "mutation": "REMOVE_ONE_ADDRESSABLE_AXIS_OUTPUT",
                "rejected": True,
                "reason_code": "MISSING_REQUIRED_ADDRESSABLE_AXIS",
            }
            row["test_digest"] = object_digest(row, "test_digest")
            removals.append(row)
    require(
        len(differences) == 80
        and all(row["pass"] for row in differences)
        and len(removals) == 480,
        "E_P3_R1_STRUCTURE_GATES",
    )
    return materials, records, differences, removals


def _assignments_r1(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row["profile_id"], row["variant"]): row for row in records}
    variants = ("A1", "A2", "B1", "B2")
    rows: list[dict[str, Any]] = []
    for index, profile in enumerate(profile_rows(ROOT)):
        profile_id = str(profile["content_product_type_id"])
        variant = variants[index % 4]
        structure = by_key[(profile_id, variant)]
        row = {
            "assignment_id": f"P3-R1-POSITIVE-ASSIGNMENT-{profile_id}",
            "profile_id": profile_id,
            "assigned_variant": variant,
            "assigned_lane": structure["lane"],
            "assigned_structure_record_id": structure["record_id"],
            "assigned_structure_record_digest": structure["record_digest"],
            "selection_rule": "CP_SORT_ORDER_MOD_4_TO_A1_A2_B1_B2_UNCHANGED",
            "attempt": 1,
            "run_order": index + 1,
        }
        row["assignment_digest"] = object_digest(row, "assignment_digest")
        rows.append(row)
    require(
        {variant: sum(row["assigned_variant"] == variant for row in rows) for variant in variants}
        == {variant: 5 for variant in variants},
        "E_P3_R1_ASSIGNMENT_BALANCE",
    )
    return rows


def _author_requests_r1(
    root: Path,
    materials: list[dict[str, Any]],
    records: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    profiles = {str(row["content_product_type_id"]): row for row in profile_rows(root)}
    material_by_profile = {str(row["profile_id"]): row for row in materials}
    record_by_key = {(row["profile_id"], row["variant"]): row for row in records}
    component_by_id = {
        str(row["component_id"]): row for row in load_jsonl(root / P2_COMPONENTS_PATH)
    }
    rules = load_jsonl(root / P2_RULES_PATH)
    instruction_digest = sha256_file(root / AUTHOR_INSTRUCTION_R1_PATH)
    rows: list[dict[str, Any]] = []
    for assignment in assignments:
        profile_id = str(assignment["profile_id"])
        variant = str(assignment["assigned_variant"])
        structure = record_by_key[(profile_id, variant)]
        selected_components = [
            {
                "component_id": component_id,
                "component_role": component_by_id[component_id]["component_role"],
                "component_digest": component_by_id[component_id]["component_digest"],
                "mechanism": component_by_id[component_id]["mechanism"],
                "claim_boundary": component_by_id[component_id]["claim_boundary"],
            }
            for component_id in structure["selected_component_ids"]
        ]
        material = material_by_profile[profile_id]
        request: dict[str, Any] = {
            "schema_version": "gate1-p3-controlled-author-request-v0.2",
            "task_id": TASK_ID,
            "request_id": f"P3-R1-OPEN-POSITIVE-{profile_id}",
            "profile_id": profile_id,
            "assigned_variant": variant,
            "attempt": 1,
            "run_order": assignment["run_order"],
            "author_identity": AUTHORIZED_AUTHOR_IDENTITY,
            "author_session_logical_id": AUTHORIZED_AUTHOR_SESSION,
            "author_platform_agent_id": AUTHOR_PLATFORM_AGENT_ID,
            "author_model_label": AUTHORIZED_AUTHOR_MODEL_LABEL,
            "author_model_capability_id": AUTHORIZED_AUTHOR_CAPABILITY_ID,
            "author_instruction_path": AUTHOR_INSTRUCTION_R1_PATH.as_posix(),
            "author_instruction_sha256": instruction_digest,
            "prior_attempt_artifact_files_provided_to_author": False,
            "prior_attempt_context_may_be_retained_by_same_agent": True,
            "prior_review_score_visible_to_author": False,
            "user_goal": "Write one concrete synthetic qualification output that realizes the frozen product, facts, components, and six-axis structure.",
            "platform": list(profiles[profile_id].get("target_platforms", [])),
            "account_expression_identity": list(
                profiles[profile_id].get("target_account_roles", [])
            ),
            "profile_contract": copy.deepcopy(profiles[profile_id]),
            "typed_material": copy.deepcopy(material),
            "product_core_surface_requirements": copy.deepcopy(
                material["product_core_surface_requirements"]
            ),
            "component_realization_requirements": copy.deepcopy(
                material["component_realization_requirements"]
            ),
            "structure_contract": {
                "record_id": structure["record_id"],
                "record_digest": structure["record_digest"],
                "axis_values": structure["axis_values"],
                "axis_programs": structure["axis_programs"],
                "addressable_outputs": structure["addressable_outputs"],
                "component_contributions": structure["component_contributions"],
            },
            "approved_components": selected_components,
            "control_rules": rules,
            "required_output_surface_order": [
                "title",
                "body",
                "spoken_lines",
                "cta",
                "visual_execution",
                "audio_execution",
            ],
            "single_first_output_only": True,
            "external_provider_allowed": False,
            "synthetic_qualification_only": True,
            "publishable": False,
            "runtime_consumable": False,
            "counts_toward_300": False,
        }
        request["request_digest"] = object_digest(request, "request_digest")
        rows.append(request)
    return rows


def _model_document() -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "gate1-p3-author-model-session-v0.2",
        "task_id": TASK_ID,
        "repair_attempt": 1,
        "author_identity": AUTHORIZED_AUTHOR_IDENTITY,
        "author_session_logical_id": AUTHORIZED_AUTHOR_SESSION,
        "author_platform_agent_id": AUTHOR_PLATFORM_AGENT_ID,
        "model_label": AUTHORIZED_AUTHOR_MODEL_LABEL,
        "model_capability_id": AUTHORIZED_AUTHOR_CAPABILITY_ID,
        "reasoning_effort": "high",
        "service_tier": "priority",
        "same_author_identity_as_attempt_0": True,
        "same_platform_agent_as_attempt_0": True,
        "authorized_complete_run_index": 2,
        "attempt_1_complete_run_limit": 1,
        "reroll_allowed": False,
        "external_provider_allowed": False,
        "unexposed_model_parameters": "PLATFORM_NOT_EXPOSED__NOT_GUESSED",
        "review_role_allowed": False,
        "counts_toward_300": 0,
        "readiness": readiness_false(),
    }
    document["object_digest"] = object_digest(document, "object_digest")
    return document


def _repair_basis(root: Path) -> dict[str, Any]:
    first = json.loads((root / ATTEMPT_0_REVIEW_ONE_PATH).read_text(encoding="utf-8"))
    second = json.loads((root / ATTEMPT_0_REVIEW_TWO_PATH).read_text(encoding="utf-8"))
    adjudication = json.loads(
        (root / ATTEMPT_0_ADJUDICATION_PATH).read_text(encoding="utf-8")
    )
    document: dict[str, Any] = {
        "schema_version": "gate1-p3-open-repair-basis-v0.1",
        "task_id": TASK_ID,
        "attempt_0_failure_commit": ATTEMPT_0_FAILURE_COMMIT,
        "attempt_0_result_path": ATTEMPT_0_RESULT_PATH.as_posix(),
        "attempt_0_result_sha256": sha256_file(root / ATTEMPT_0_RESULT_PATH),
        "review_one": {
            "path": ATTEMPT_0_REVIEW_ONE_PATH.as_posix(),
            "sha256": sha256_file(root / ATTEMPT_0_REVIEW_ONE_PATH),
            "score": first["p3_score"],
            "first_acceptable_count": first["first_acceptable_count"],
            "blind_top1_correct_count": first["blind_top1_correct_count"],
            "verdict": first["overall_verdict"],
        },
        "review_two": {
            "path": ATTEMPT_0_REVIEW_TWO_PATH.as_posix(),
            "sha256": sha256_file(root / ATTEMPT_0_REVIEW_TWO_PATH),
            "score": second["p3_score"],
            "first_acceptable_count": second["first_acceptable_count"],
            "blind_top1_correct_count": second["blind_top1_correct_count"],
            "verdict": second["overall_verdict"],
        },
        "adjudication": {
            "path": ATTEMPT_0_ADJUDICATION_PATH.as_posix(),
            "sha256": sha256_file(root / ATTEMPT_0_ADJUDICATION_PATH),
            "digest": adjudication["adjudication_digest"],
            "attempt_0_remains_failed": True,
        },
        "root_causes": [
            "P3_SLOT_MAPPING_COLLAPSED_SPECIFIC_ACTIONS_AND_OBSERVATIONS",
            "P3_SCENARIO_TO_APPROVED_COMPONENT_REALIZATION_GAP",
            "AUTHOR_INSTRUCTION_SURFACED_GOVERNANCE_BOUNDARIES_AS_REPEATED_COPY",
            "BLIND_PACKET_OMITTED_THE_FIXED_20_PRODUCT_CHOICE_CATALOG",
        ],
        "repair_scope": [
            "P3_SYNTHETIC_MATERIAL_MAPPING",
            "P3_COMPONENT_REALIZATION_REQUIREMENTS",
            "P3_AUTHOR_INSTRUCTION",
            "P3_BLIND_REVIEW_PROTOCOL",
        ],
        "p2_component_mutation_count": 0,
        "p2_edge_mutation_count": 0,
        "p2_path_mutation_count": 0,
        "component_addition_count": 0,
        "open_core_repair_window_used": True,
        "open_core_repair_window_remaining": 0,
        "attempt_0_outputs_and_failure_denominator_preserved": True,
        "attempt_0_p4_allowed": False,
        "counts_toward_300": 0,
        "readiness": readiness_false(),
    }
    document["repair_basis_digest"] = object_digest(document, "repair_basis_digest")
    return document


def _attempt_0_integrity(root: Path) -> list[dict[str, Any]]:
    listing = subprocess.run(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            ATTEMPT_0_FAILURE_COMMIT,
            "--",
            TASK_ROOT.as_posix(),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = [Path(line) for line in listing.stdout.splitlines() if line.strip()]
    require(bool(paths), "E_P3_R1_ATTEMPT0_TREE_EMPTY")
    rows: list[dict[str, Any]] = []
    for relative in paths:
        blob = subprocess.run(
            ["git", "show", f"{ATTEMPT_0_FAILURE_COMMIT}:{relative.as_posix()}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        expected = sha256_bytes(blob)
        require(
            (root / relative).is_file()
            and sha256_file(root / relative) == expected,
            "E_P3_R1_ATTEMPT0_MUTATION",
            relative.as_posix(),
        )
        rows.append(
            {
                "path": relative.as_posix(),
                "sha256_at_attempt_0_failure_commit": expected,
                "protection": "BYTE_IMMUTABLE",
            }
        )
    return rows


def build_repair_documents(root: Path = ROOT) -> dict[Path, bytes]:
    scenario_document = _scenario_v2(root)
    scenarios = {
        str(row["profile_id"]): row for row in scenario_document["scenarios"]
    }
    materials, records, differences, removals = _build_structure_r1(root, scenarios)
    assignments = _assignments_r1(records)
    requests = _author_requests_r1(root, materials, records, assignments)
    base_route_selections, route_inputs = _route_selection(root)
    route_selections: list[dict[str, Any]] = []
    for base in base_route_selections:
        row = copy.deepcopy(base)
        row["parent_selection_id"] = row["selection_id"]
        row["parent_selection_digest"] = row["selection_digest"]
        row["selection_id"] = str(row["selection_id"]).replace(
            "P3-ROUTE", "P3-R1-ROUTE"
        )
        row["attempt"] = 1
        row["selection_digest"] = object_digest(row, "selection_digest")
        route_selections.append(row)
    repair_basis = _repair_basis(root)
    attempt_0_integrity = _attempt_0_integrity(root)
    model = _model_document()
    scenario_payload = yaml_bytes({"synthetic_positive_scenarios": scenario_document})
    material_payload = jsonl_bytes(materials)
    structure_payload = jsonl_bytes(records)
    difference_payload = jsonl_bytes(differences)
    removal_payload = jsonl_bytes(removals)
    assignment_payload = jsonl_bytes(assignments)
    request_payload = jsonl_bytes(requests)
    route_selection_payload = jsonl_bytes(route_selections)
    route_input_payload = jsonl_bytes(route_inputs)
    model_payload = yaml_bytes({"author_model_and_session": model})
    repair_basis_payload = yaml_bytes({"p3_open_repair_basis": repair_basis})
    attempt_0_integrity_payload = jsonl_bytes(attempt_0_integrity)
    gap = {
        "schema_version": "gate1-p3-structure-gap-v0.2",
        "task_id": TASK_ID,
        "attempt": 1,
        "profile_count": 20,
        "structure_record_count": 80,
        "component_realization_requirement_count": sum(
            len(row["component_realization_requirements"]) for row in materials
        ),
        "unsupported_component_realization_count": 0,
        "actual_component_supply_gap_count": 0,
        "component_addition_count": 0,
        "conclusion": "NO_ACTUAL_COMPONENT_SUPPLY_GAP_AFTER_P3_INPUT_ALIGNMENT",
        "content_quality_proven": False,
        "counts_toward_300": 0,
        "readiness": readiness_false(),
    }
    gap["gap_digest"] = object_digest(gap, "gap_digest")
    gap_payload = yaml_bytes({"p3_structure_gap_assessment": gap})
    pointer = {
        "schema_version": "gate1-p3-final-structure-pointer-v0.2",
        "task_id": TASK_ID,
        "final_attempt": 1,
        "structure_path": STRUCTURE_R1_PATH.as_posix(),
        "structure_sha256": sha256_bytes(structure_payload),
        "structure_count": 80,
        "repair_window_used": True,
        "component_supplement_window_used": False,
        "content_quality_proven": False,
        "counts_toward_300": 0,
    }
    pointer["pointer_digest"] = object_digest(pointer, "pointer_digest")
    pointer_payload = yaml_bytes({"final_structure_pointer": pointer})
    manifest: dict[str, Any] = {
        "schema_version": "gate1-p3-open-repair-freeze-v0.2",
        "task_id": TASK_ID,
        "baseline_commit": BASELINE_COMMIT,
        "attempt_0_failure_commit": ATTEMPT_0_FAILURE_COMMIT,
        "freeze_state": "FROZEN_BEFORE_ATTEMPT_1_AUTHORING",
        "attempt": 1,
        "p2_frozen_inputs": {
            path.as_posix(): sha256_file(root / path)
            for path in (
                P2_COMPONENTS_PATH,
                P2_RULES_PATH,
                P2_EDGES_PATH,
                P2_PATHS_PATH,
                P2_ROOT / "p2_generator_core_r6.py",
            )
        },
        "repair_basis": {
            "path": REPAIR_BASIS_PATH.as_posix(),
            "sha256": sha256_bytes(repair_basis_payload),
        },
        "attempt_0_integrity_manifest": {
            "path": ATTEMPT_0_INTEGRITY_PATH.as_posix(),
            "sha256": sha256_bytes(attempt_0_integrity_payload),
            "count": len(attempt_0_integrity),
        },
        "scenario_set": {
            "path": SCENARIO_V2_PATH.as_posix(),
            "sha256": sha256_bytes(scenario_payload),
        },
        "typed_material": {
            "path": MATERIAL_R1_PATH.as_posix(),
            "sha256": sha256_bytes(material_payload),
            "count": 20,
        },
        "structure": {
            "path": STRUCTURE_R1_PATH.as_posix(),
            "sha256": sha256_bytes(structure_payload),
            "count": 80,
        },
        "differences": {
            "path": DIFFERENCE_R1_PATH.as_posix(),
            "sha256": sha256_bytes(difference_payload),
            "count": 80,
        },
        "axis_removals": {
            "path": REMOVAL_R1_PATH.as_posix(),
            "sha256": sha256_bytes(removal_payload),
            "count": 480,
        },
        "author_instruction": {
            "path": AUTHOR_INSTRUCTION_R1_PATH.as_posix(),
            "sha256": sha256_file(root / AUTHOR_INSTRUCTION_R1_PATH),
        },
        "author_model": {
            "path": AUTHOR_MODEL_R1_PATH.as_posix(),
            "sha256": sha256_bytes(model_payload),
            "object_digest": model["object_digest"],
        },
        "positive_assignments": {
            "path": ASSIGNMENT_R1_PATH.as_posix(),
            "sha256": sha256_bytes(assignment_payload),
            "count": 20,
        },
        "author_requests": {
            "path": AUTHOR_REQUEST_R1_PATH.as_posix(),
            "sha256": sha256_bytes(request_payload),
            "count": 20,
        },
        "route_selections": {
            "path": ROUTE_SELECTION_R1_PATH.as_posix(),
            "sha256": sha256_bytes(route_selection_payload),
            "count": 20,
        },
        "route_inputs": {
            "path": ROUTE_INPUT_R1_PATH.as_posix(),
            "sha256": sha256_bytes(route_input_payload),
            "count": 20,
        },
        "same_author_identity_and_platform_agent": True,
        "attempt_1_author_run_limit": 1,
        "reroll_allowed": False,
        "component_addition_count": 0,
        "open_core_repair_window_used": True,
        "open_core_repair_window_remaining": 0,
        "counts_toward_300": 0,
        "readiness": readiness_false(),
    }
    manifest["freeze_manifest_digest"] = object_digest(
        manifest, "freeze_manifest_digest"
    )
    return {
        SCENARIO_V2_PATH: scenario_payload,
        REPAIR_BASIS_PATH: repair_basis_payload,
        ATTEMPT_0_INTEGRITY_PATH: attempt_0_integrity_payload,
        MATERIAL_R1_PATH: material_payload,
        STRUCTURE_R1_PATH: structure_payload,
        DIFFERENCE_R1_PATH: difference_payload,
        REMOVAL_R1_PATH: removal_payload,
        GAP_R1_PATH: gap_payload,
        FINAL_POINTER_R1_PATH: pointer_payload,
        AUTHOR_MODEL_R1_PATH: model_payload,
        ASSIGNMENT_R1_PATH: assignment_payload,
        AUTHOR_REQUEST_R1_PATH: request_payload,
        ROUTE_SELECTION_R1_PATH: route_selection_payload,
        ROUTE_INPUT_R1_PATH: route_input_payload,
        FREEZE_MANIFEST_R1_PATH: yaml_bytes({"p3_open_repair_freeze": manifest}),
    }


def materialize(root: Path = ROOT) -> list[Path]:
    changed: list[Path] = []
    for relative, payload in build_repair_documents(root).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
            changed.append(path)
    return changed


def check(root: Path = ROOT) -> None:
    for relative, payload in build_repair_documents(root).items():
        path = root / relative
        require(path.is_file(), "E_P3_R1_FILE_MISSING", relative.as_posix())
        require(path.read_bytes() == payload, "E_P3_R1_FILE_DRIFT", relative.as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--materialize", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.materialize:
        changed = materialize()
        print(json.dumps({"status": "P3_REPAIR_FROZEN", "changed": [str(path) for path in changed]}))
    else:
        check()
        print(json.dumps({"status": "P3_REPAIR_CHECK_PASS"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
