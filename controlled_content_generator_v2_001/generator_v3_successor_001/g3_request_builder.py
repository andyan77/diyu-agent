#!/usr/bin/env python3
"""G3 · 场景→作者请求编译器（v3）。

相对 P5 的三处协议修复（源指令 §7 执行包1 授权面内）：

1. **冻结槽位真实填充**：typed_material.facts 覆盖本 lane 全部组件
   required_fact_slots 的并集（P5 只填 4 个通用槽，组件槽全部空置，
   导致"组件已使用"只存在于登记）。组件指针必须绑定自己槽位的事实。
2. **边界去治理化**：`claim_boundary` 槽的事实值改用策展的
   audience_safe_boundary（事实形态限度），治理措辞版约束保留在
   typed_material.claim_boundary 仅供 claims 元数据，禁止上表面。
3. **表达计划与指纹合同**：每请求携带确定性互异表达计划与产品指纹合同。

本模块只读冻结基座（AB 路径 / 激活组件），不修改任何历史文件。
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import g3_author_contract as contract  # noqa: E402
import g3_expression  # noqa: E402
import g3_fingerprint  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GATE1 = ROOT / "controlled_content_generator_v2_001/gate1_v1_1_001"
P2 = GATE1 / "p2_component_supply_and_generator_core_repair_001"
AB_PATHS_FILE = P2 / "ab/active_ab_structural_paths.v0.1.jsonl"
COMPONENTS_FILE = P2 / "component/active_gate1_components.v0.1.jsonl"

SCENARIO_SCHEMA = "gate1-g3-curated-scenario-v3.0"

SCENARIO_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "scenario_id",
        "profile_id",
        "scenario_label",
        "lane_id",
        "user_goal",
        "slot_facts",
        "audience_safe_boundary",
        "claim_boundary_governance",
        "authorization_scope",
        "source_summary_a",
        "source_summary_b",
        "synthetic_test_only",
        "provenance",
    }
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def load_frozen_base() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """返回 (profile_id→AB path, component_id→component)。只读冻结文件。"""
    paths = {str(p["content_product_type_id"]): p for p in read_jsonl(AB_PATHS_FILE)}
    components = {str(c["component_id"]): c for c in read_jsonl(COMPONENTS_FILE)}
    contract.require(len(paths) == 20, "E_G3_AB_PATH_COUNT", str(len(paths)))
    contract.require(len(components) == 68, "E_G3_COMPONENT_COUNT", str(len(components)))
    return paths, components


def lane_slot_union(
    lane: Mapping[str, Any], components: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """lane 全部普通组件 required_fact_slots 的确定性并集（排序）。"""
    slots: set[str] = set()
    for component_id in lane["component_ids"]:
        if str(component_id).startswith("G1V11-P2-AXIS"):
            continue
        slots.update(map(str, components[str(component_id)]["required_fact_slots"]))
    return sorted(slots)


def validate_scenario(
    scenario: Mapping[str, Any],
    lane: Mapping[str, Any],
    components: Mapping[str, Mapping[str, Any]],
) -> None:
    contract.require(set(scenario) >= SCENARIO_REQUIRED_FIELDS, "E_G3_SCENARIO_FIELDS",
                     ",".join(sorted(SCENARIO_REQUIRED_FIELDS - set(scenario))))
    contract.require(scenario.get("schema_version") == SCENARIO_SCHEMA,
                     "E_G3_SCENARIO_SCHEMA")
    contract.require(scenario.get("synthetic_test_only") is True, "E_G3_SCENARIO_SYNTH")
    contract.require(str(scenario.get("lane_id")) in {"A", "B"}, "E_G3_SCENARIO_LANE")
    slot_facts = scenario.get("slot_facts")
    contract.require(isinstance(slot_facts, Mapping), "E_G3_SCENARIO_SLOT_FACTS")
    required = lane_slot_union(lane, components)
    missing = [s for s in required if not str(slot_facts.get(s, "")).strip()]
    contract.require(not missing, "E_G3_SCENARIO_SLOT_MISSING", ",".join(missing))
    for key in ("audience_safe_boundary", "claim_boundary_governance",
                "authorization_scope", "user_goal"):
        contract.require(bool(str(scenario.get(key, "")).strip()),
                         "E_G3_SCENARIO_TEXT", key)


def build_request(
    scenario: Mapping[str, Any],
    plan: Mapping[str, Any],
    ab_path: Mapping[str, Any],
    components: Mapping[str, Mapping[str, Any]],
    author: Mapping[str, str],
    run_order: int,
    author_instruction_sha256: str,
    author_instruction_path: str,
) -> dict[str, Any]:
    profile_id = str(scenario["profile_id"])
    lane_id = str(scenario["lane_id"])
    lane = ab_path["lane_a" if lane_id == "A" else "lane_b"]
    validate_scenario(scenario, lane, components)

    suffix = str(scenario["scenario_id"]).rsplit("-", 1)[1]
    prefix = f"G3-{profile_id}-{suffix}"
    source_ids = [f"{prefix}-SRC-01", f"{prefix}-SRC-02"]
    authorization_id = f"{prefix}-AUTH-01"

    slots = lane_slot_union(lane, components)
    # claim_boundary 槽（冻结程序信息节点）用受众安全限度填充
    facts: list[dict[str, Any]] = []
    ordered_slots = [*slots, "claim_boundary"]
    for index, slot_id in enumerate(ordered_slots, 1):
        if slot_id == "claim_boundary":
            value = str(scenario["audience_safe_boundary"])
        else:
            value = str(scenario["slot_facts"][slot_id])
        facts.append(
            {
                "fact_id": f"{prefix}-FACT-{index:02d}",
                "slot_id": slot_id,
                "fact_value": value,
                "fact_value_digest": contract.sha256_bytes(value.encode("utf-8")),
                "source_ids": list(source_ids),
                "authorization_ids": [authorization_id],
                "synthetic_test_only": True,
            }
        )
    approved = [dict(components[str(cid)]) for cid in lane["component_ids"]]
    request: dict[str, Any] = {
        "schema_version": contract.REQUEST_SCHEMA,
        "task_id": contract.TASK_ID,
        "request_id": f"G3-POS-{profile_id}-{suffix}",
        "profile_id": profile_id,
        "assigned_variant": f"{lane_id}{suffix[-1]}",
        "lane_id": lane_id,
        "run_order": run_order,
        "scenario_id": str(scenario["scenario_id"]),
        "author_identity": author["author_identity"],
        "author_session_logical_id": author["author_session_logical_id"],
        "author_platform_agent_id": author["author_platform_agent_id"],
        "model_capability_id": contract.MODEL_CAPABILITY,
        "reasoning_effort": contract.REASONING_EFFORT,
        "service_tier": contract.SERVICE_TIER,
        "user_goal": str(scenario["user_goal"]),
        "typed_material": {
            "sources": [
                {"slot_id": "usable_source_materials", "source_id": source_ids[0],
                 "source_summary": str(scenario["source_summary_a"]),
                 "synthetic_test_only": True},
                {"slot_id": "product_or_scene_reference", "source_id": source_ids[1],
                 "source_summary": str(scenario["source_summary_b"]),
                 "synthetic_test_only": True},
            ],
            "facts": facts,
            "authorizations": [
                {"authorization_id": authorization_id,
                 "scope_summary": str(scenario["authorization_scope"]),
                 "slot_id": "publication_scope_authorization",
                 "synthetic_test_only": True}
            ],
            # 治理措辞版约束：仅作 claims 元数据边界，禁止出现在受众表面
            "claim_boundary": str(scenario["claim_boundary_governance"]),
        },
        # 全部槽位事实都必须真实上表面（含受众安全限度）
        "product_core_requirements": [
            {"requirement_id": f"{prefix}-CORE-{index:02d}",
             "fact_ids": [fact["fact_id"]]}
            for index, fact in enumerate(facts, 1)
        ],
        "approved_components": approved,
        "structure_contract": {
            "frozen_path_digest": str(ab_path["path_digest"]),
            "lane_id": lane_id,
            "axes": dict(lane["axes"]),
            "axis_programs": json.loads(json.dumps(lane["axis_programs"])),
            "boundary_realization_note": (
                "结尾程序的 claim_boundary 信息节点由受众安全限度事实"
                "（claim_boundary 槽）实现；治理措辞版约束不上任何受众表面。"
            ),
        },
        "expression_plan": dict(plan),
        "fingerprint_contract": g3_fingerprint.fingerprint_contract(profile_id),
        "author_output_contract": {
            "one_first_semantic_output_only": True,
            "author_may_not_review_or_approve": True,
            "publishable": False,
            "runtime_consumable": False,
            "may_enter_300": False,
        },
        "exact_author_contract": {
            "raw_schema_version": contract.RAW_SCHEMA,
            "raw_top_level_fields": sorted(contract.RAW_FIELDS),
            "semantic_surface_fields": sorted(contract.RAW_SURFACE_FIELDS),
            "semantic_claim_fields": sorted(contract.RAW_CLAIM_FIELDS),
            "semantic_component_usage_fields": sorted(contract.RAW_COMPONENT_FIELDS),
            "author_attestation_fields_and_values": dict(contract.EXPECTED_ATTESTATION),
            "surface_kind_enum": list(contract.SURFACE_KIND_ENUM),
            "component_pointer_must_bind_core_or_required_slot_fact": True,
            "component_pointer_must_use_role_compatible_surface": True,
            "core_fact_coverage_required": True,
            "claim_text_verbatim_on_surface_required": True,
            "run_id_unique_across_batch": True,
            "role_allowed_surface_kinds": dict(contract.ROLE_ALLOWED_SURFACE_KINDS),
            "raw_type_contract": dict(contract.RAW_TYPE_CONTRACT),
            "nested_type_contract": json.loads(
                json.dumps(contract.NESTED_TYPE_CONTRACT)),
        },
        "author_instruction_path": author_instruction_path,
        "author_instruction_sha256": author_instruction_sha256,
        "synthetic_qualification_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "counts_toward_300": False,
        "external_provider_allowed": False,
    }
    request["request_digest"] = contract.object_digest(request, "request_digest")
    contract.validate_request(request)
    return request


def build_batch(
    scenarios: Sequence[Mapping[str, Any]],
    batch_id: str,
    authors_by_profile: Mapping[str, Mapping[str, str]],
    author_instruction_sha256: str,
    author_instruction_path: str,
) -> list[dict[str, Any]]:
    """整批构建：按 profile 分组、场景序稳定、逐产品发牌表达计划。"""
    ab_paths, components = load_frozen_base()
    by_profile: dict[str, list[Mapping[str, Any]]] = {}
    for scenario in scenarios:
        by_profile.setdefault(str(scenario["profile_id"]), []).append(scenario)
    requests: list[dict[str, Any]] = []
    run_order = 0
    for profile_id in sorted(by_profile):
        rows = sorted(by_profile[profile_id], key=lambda s: str(s["scenario_id"]))
        plans = g3_expression.assign_plans(profile_id, batch_id, len(rows))
        for scenario, plan in zip(rows, plans, strict=True):
            run_order += 1
            requests.append(
                build_request(
                    scenario, plan, ab_paths[profile_id], components,
                    authors_by_profile[profile_id], run_order,
                    author_instruction_sha256, author_instruction_path,
                )
            )
    ids = [r["request_id"] for r in requests]
    contract.require(len(ids) == len(set(ids)), "E_G3_REQUEST_ID_DUPLICATE")
    return requests


__all__ = [
    "SCENARIO_REQUIRED_FIELDS",
    "SCENARIO_SCHEMA",
    "build_batch",
    "build_request",
    "lane_slot_union",
    "load_frozen_base",
    "read_jsonl",
    "validate_scenario",
]
