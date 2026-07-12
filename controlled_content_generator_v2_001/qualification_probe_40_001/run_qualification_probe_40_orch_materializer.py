#!/usr/bin/env python3
"""Materialize ORCH-owned qualification packs, assignments, plans, and instructions."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


TASK_ID = "CONTROLLED_V2_20CP_QUALIFICATION_PROBE_40_001"
PHASE0_MERGE_COMMIT_SHA = "25ce4ff092befe39106783d8b7f2cf31e77f0e82"
PHASE0_MERGE_TREE_SHA = "d961d44c977cbeecd762827218b75008108f8414"
REVIEWED_BASE_SHA = "0ed9fd40203a6423d4deb9e6342c441ac3c129c1"
REVIEWED_HEAD_SHA = "7b7f87db532ad89271d471bb0020d749324af917"
REVIEWED_HEAD_TREE_SHA = "d961d44c977cbeecd762827218b75008108f8414"
REVIEWED_FULL_DIFF_DIGEST = "e40bb98a0af50d7a8351c3038b53edde6d46d0157f9ca4780cd74a8539c5be3e"

TASK_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")
PACKS_PATH = TASK_DIR / "qualification_material_packs.v0.1.jsonl"
ASSIGNMENTS_PATH = TASK_DIR / "qualification_probe_assignments.v0.1.jsonl"
PLANS_PATH = TASK_DIR / "canonical_qualification_composition_plans.v0.1.jsonl"
INSTRUCTIONS_PATH = TASK_DIR / "qualification_generation_instructions.v0.1.jsonl"
ORCH_MATERIALIZER_PATH = TASK_DIR / "run_qualification_probe_40_orch_materializer.py"

GKB_ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
PROFILES_PATH = GKB_ROOT / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
COMPONENT_REGISTRY_PATH = GKB_ROOT / "component_supply_closeout_20cp_001/reviewed_reusable_component_registry.v0.3.jsonl"
VALIDATION_FIXTURES_PATH = GKB_ROOT / "fact_authorization_fixture_closeout_001/content_product_validation_fixtures.v0.1.jsonl"
ORCH_VALIDATION_PLANS_PATH = Path(
    "08_orchestration_runs/controlled_composition_v2_001/"
    "orch_20cp_validation_dryrun_001/orch_validation_canonical_plans.v0.1.jsonl"
)

QUALIFICATION_NAMESPACE = "qualification://controlled-v2/probe-40/"
VISIBLE_DISCLOSURE_TEXT = "INTERNAL QUALIFICATION PROBE / SYNTHETIC CASE / NOT PUBLISHABLE"

CP_MATERIALS: list[dict[str, str]] = [
    {
        "cp": "CP01",
        "label": "岗位任务VLOG",
        "role": "样品整理员",
        "object": "海军蓝针织开衫",
        "scenario": "折袖后等待回弹，再把衣身放回层板",
        "evidence": "三步动作记录：折袖、停三秒、复位层板",
        "claim": "只能说明合成样品中的任务顺序，不说明真实员工效率",
    },
    {
        "cp": "CP02",
        "label": "门店时段微纪录",
        "role": "早班店长",
        "object": "晨间陈列台",
        "scenario": "开灯后清掉纸样、补齐两处空位",
        "evidence": "时段记录：09:10开灯，09:16完成台面复位",
        "claim": "只能描述合成时段里的台面变化，不代表真实客流",
    },
    {
        "cp": "CP03",
        "label": "单项手艺全过程",
        "role": "样衣工艺员",
        "object": "米白半裙腰头",
        "scenario": "从划线到压线，保留一次停针检查",
        "evidence": "过程记录：划线、试压、停针检查、收尾",
        "claim": "只能说明合成工艺步骤，不承诺真实工艺标准",
    },
    {
        "cp": "CP04",
        "label": "多岗位协作纪实",
        "role": "陈列员与导购",
        "object": "试穿镜旁的短外套组合",
        "scenario": "陈列员移动衣架，导购只补充尺码提示",
        "evidence": "协作记录：两人授权发言范围不同，未记录争吵",
        "claim": "只能表现角色边界和协作顺序，禁止编造冲突",
    },
    {
        "cp": "CP05",
        "label": "人物成长与职业史",
        "role": "模拟版师",
        "object": "三阶段学习卡片",
        "scenario": "把入门、独立改样、复核三个阶段摆成时间线",
        "evidence": "职业史卡片：阶段A、阶段B、阶段C均为合成授权",
        "claim": "只能讲模拟职业时间线，不把加班包装成成长",
    },
    {
        "cp": "CP06",
        "label": "专业判断切片",
        "role": "搭配顾问",
        "object": "冷灰衬衫与暖米裤",
        "scenario": "在两块色布之间解释色温取舍",
        "evidence": "判断卡：冷灰更稳，暖米更软，未给绝对结论",
        "claim": "只能呈现选择依据，不替所有人下结论",
    },
    {
        "cp": "CP07",
        "label": "用户问题诊断室",
        "role": "问题分诊员",
        "object": "合成提问卡：通勤外套显拘谨",
        "scenario": "先拆问题，再列两个需要补充的信息",
        "evidence": "诊断卡：肩线、内搭厚度为待确认项",
        "claim": "只能给问题框架，不假装知道用户真实身体数据",
    },
    {
        "cp": "CP08",
        "label": "工艺／面料／版型解构",
        "role": "面料讲解员",
        "object": "斜纹样布与袖窿纸样",
        "scenario": "用斜纹方向和袖窿弧线解释垂坠边界",
        "evidence": "技术卡：斜纹方向、袖窿弧线、垂坠观察均为合成证据",
        "claim": "只能说明合成样布观察，不声称身体效果",
    },
    {
        "cp": "CP09",
        "label": "适用边界与反选指南",
        "role": "选款边界顾问",
        "object": "高领针织与低领内搭",
        "scenario": "先说适合的使用场景，再说不建议的搭法",
        "evidence": "边界卡：保暖优先可选高领，叠戴项链不优先",
        "claim": "只能描述选择边界，不制造焦虑",
    },
    {
        "cp": "CP10",
        "label": "证据与长期验证档案",
        "role": "测试记录员",
        "object": "样品袖口拉伸记录",
        "scenario": "展示第1次、第3次、第7次观察，不做普遍化",
        "evidence": "测试卡：三次观察均来自同一合成样品",
        "claim": "只能报告单个合成样品，不推成长期规律",
    },
    {
        "cp": "CP11",
        "label": "产品诞生与设计取舍档案",
        "role": "设计记录员",
        "object": "领口高度取舍板",
        "scenario": "把保暖、显脖颈、叠穿三个选项摆到同一板上",
        "evidence": "取舍卡：三项利益不能同时最大化",
        "claim": "只能说明模拟设计取舍，不声称真实产品历史",
    },
    {
        "cp": "CP12",
        "label": "产品迭代与版本日志",
        "role": "版本记录员",
        "object": "V2样衣与V3样衣差异贴",
        "scenario": "指出袖口宽度调整和待复核的洗后状态",
        "evidence": "版本卡：V2袖口6.5cm，V3袖口6.0cm，洗后待验证",
        "claim": "只能报告合成版本差异，不宣称真实库存或销量",
    },
    {
        "cp": "CP13",
        "label": "产品的生活与衣橱角色",
        "role": "衣橱角色观察员",
        "object": "一件浅咖开衫",
        "scenario": "把它放在通勤、周末、旅行三个衣橱位置",
        "evidence": "角色卡：三种位置均为合成搭配假设",
        "claim": "只能描述衣橱角色，不编造真实穿着反馈",
    },
    {
        "cp": "CP14",
        "label": "物性影像与感官短片",
        "role": "物性影像记录员",
        "object": "银灰缎面样布",
        "scenario": "只拍反光、折痕和手指离开后的回落",
        "evidence": "感官卡：反光、折痕、回落均为合成观察",
        "claim": "只能表现视觉物性，spoken和CTA不是必需",
    },
    {
        "cp": "CP15",
        "label": "商品到店生命周期",
        "role": "到店记录员",
        "object": "一箱合成样品外套",
        "scenario": "从拆箱、挂样到回收纸箱记录三个节点",
        "evidence": "生命周期卡：到店、上架、整理均为合成节点",
        "claim": "只能描述合成流程，不代表真实到货",
    },
    {
        "cp": "CP16",
        "label": "真实服务复盘",
        "role": "服务复盘员",
        "object": "合成顾客服务单",
        "scenario": "把需求、试穿卡点、复盘动作分开",
        "evidence": "服务卡：顾客为synthetic composite，不含身份信息",
        "claim": "只能复盘合成服务，不冒充真实顾客故事",
    },
    {
        "cp": "CP17",
        "label": "陈列换陈与空间实验",
        "role": "空间实验员",
        "object": "入口右侧两层陈列架",
        "scenario": "把深色外套从上层移到侧挂，观察动线留白",
        "evidence": "空间卡：位置A到位置B为合成换陈实验",
        "claim": "只能说明合成空间实验，不声称真实销售变化",
    },
    {
        "cp": "CP18",
        "label": "城市门店生活志",
        "role": "合成街区记录员",
        "object": "虚构街区雨伞架旁的外套",
        "scenario": "用synthetic locality记录雨后进店的动线",
        "evidence": "街区卡：地点为合成街区A，不是真实城市事件",
        "claim": "只能营造合成本地感，不冒充真实城市新闻",
    },
    {
        "cp": "CP19",
        "label": "经营取舍与决策复盘",
        "role": "模拟经营记录员",
        "object": "补货与留样二选一的决策板",
        "scenario": "列出两个选项、代价和暂缓理由",
        "evidence": "决策卡：组织授权为模拟，未记录真实经营决定",
        "claim": "只能复盘合成取舍，不做价值观自夸",
    },
    {
        "cp": "CP20",
        "label": "承诺—兑现追踪",
        "role": "承诺追踪员",
        "object": "三节点承诺记录表",
        "scenario": "记录承诺、复核时间、偏差修正",
        "evidence": "追踪卡：承诺A、复核B、修正C均为合成节点",
        "claim": "只能追踪合成承诺，不宣称真实履约",
    },
]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: strip_keys(child, keys) for key, child in value.items() if key not in keys}
    if isinstance(value, list):
        return [strip_keys(child, keys) for child in value]
    return value


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    return sha256_text(canonical_json(strip_keys(copy.deepcopy(value), digest_keys or set())))


def jsonl_text(rows: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(row) + "\n" for row in rows)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def unwrap(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"missing wrapper {key}")
    return value


def positive_fixtures(root: Path) -> dict[str, dict[str, Any]]:
    fixtures = {}
    for row in load_jsonl(root / VALIDATION_FIXTURES_PATH):
        if row["fixture_kind"] == "POSITIVE_COMPLETE_VALIDATION_ONLY":
            fixtures[row["content_product_type_id"]] = row
    return fixtures


def validation_plans(root: Path) -> dict[str, dict[str, Any]]:
    plans = {}
    for row in load_jsonl(root / ORCH_VALIDATION_PLANS_PATH):
        plan = unwrap(row, "orch_validation_composition_plan")
        cp_id = plan["content_product"]["primary_content_product_type_id"]
        plans[cp_id] = plan
    return plans


def pack_source_text(material: dict[str, str]) -> str:
    return (
        f"{material['cp']} synthetic qualification material: role={material['role']}; "
        f"object={material['object']}; scenario={material['scenario']}; "
        f"evidence={material['evidence']}; allowed_claim={material['claim']}."
    )


def build_packs(root: Path) -> list[dict[str, Any]]:
    fixtures = positive_fixtures(root)
    rows: list[dict[str, Any]] = []
    for index, material in enumerate(CP_MATERIALS, start=1):
        cp_id = material["cp"]
        fixture = fixtures[cp_id]
        source_text = pack_source_text(material)
        pack = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "pack_id": f"QMP-{cp_id}-001",
            "content_product_type_id": cp_id,
            "content_product_label": material["label"],
            "namespace": "SYNTHETIC_QUALIFICATION_MATERIAL",
            "synthetic": True,
            "qualification_only": True,
            "runtime_consumable": False,
            "production_consumable": False,
            "publishable": False,
            "derived_from_validation_fixture_ref": fixture["fixture_id"],
            "parent_fixture_digest": fixture["fixture_digest"],
            "topic_signature": f"{cp_id}:{material['role']}:{material['object']}:{material['scenario']}",
            "simulated_subjects": [
                {
                    "subject_id": f"SYN-SUBJECT-{cp_id}-001",
                    "role": material["role"],
                    "synthetic": True,
                    "authorized_scope": "qualification_case_only",
                }
            ],
            "simulated_business_objects": [
                {
                    "object_id": f"SYN-OBJECT-{cp_id}-001",
                    "name": material["object"],
                    "synthetic": True,
                    "runtime_fact": False,
                }
            ],
            "fact_atoms": [
                {
                    "fact_id": f"QFACT-{cp_id}-SCENARIO",
                    "text": material["scenario"],
                    "source_ref": f"fixture://qualification/{cp_id}/source/material-card",
                }
            ],
            "event_atoms": [
                {
                    "event_id": f"QEVENT-{cp_id}-OBSERVATION",
                    "event_truth_mode": "synthetic_qualification_observation",
                    "text": material["evidence"],
                    "may_be_used_as_real_event": False,
                }
            ],
            "evidence_objects": [
                {
                    "evidence_id": f"QEVID-{cp_id}-001",
                    "source_ref": f"fixture://qualification/{cp_id}/source/material-card",
                    "source_text": source_text,
                    "source_digest": sha256_text(source_text),
                }
            ],
            "authorization_atoms": [
                {
                    "authorization_id": f"QAUTH-{cp_id}-001",
                    "status": "SIMULATED_GRANTED_FOR_QUALIFICATION_TEST",
                    "scope": "synthetic qualification probe only",
                }
            ],
            "privacy_constraints": [
                "no real customer identity",
                "no real staff biography",
                "no real city event",
                "do not publish",
            ],
            "allowed_claims": [material["claim"]],
            "forbidden_inferences": [
                "verified brand fact",
                "real customer story",
                "real employee experience",
                "sales or body-effect claim",
                "runtime-ready authorization",
            ],
            "required_capture_obligations": [
                "keep visible qualification wrapper",
                "bind every specific fact to this pack",
                "surface-unit exact join across title/body/spoken/CTA/execution payload",
            ],
            "visible_disclosure": {
                "mode": "VISIBLE_QUALIFICATION_WRAPPER",
                "text": VISIBLE_DISCLOSURE_TEXT,
            },
            "hard_boundary": {
                "verified_brand_fact": False,
                "verified_runtime_authorization": False,
                "may_enter_KE_truth": False,
                "may_enter_RAG": False,
                "may_enter_DIFY": False,
                "may_be_published": False,
            },
            "pack_sequence": index,
            "pack_digest": "",
        }
        pack["pack_digest"] = object_digest(pack, {"pack_digest"})
        rows.append({"qualification_material_pack": pack})
    return rows


def lane_specs(cp_id: str) -> list[dict[str, Any]]:
    return [
        {
            "lane_code": "A",
            "voice_lane": "ROLE_PROFESSIONAL_EXPRESSION",
            "platform_target": "douyin_short_video",
            "narrative_device": "role_bound_process_walkthrough",
            "opening_family": "task_entry",
            "information_order": "context_action_reason_boundary",
            "reasoning_shape": "professional_constraint_then_choice",
            "language_register": "measured_role_language",
            "visual_audio_grammar": "handheld_workbench_observation",
            "closing_family": "boundary_note",
            "spoken_line_allowed": True,
            "CTA_allowed": True,
        },
        {
            "lane_code": "B",
            "voice_lane": "SENSORY_NONVERBAL_EXPRESSION" if cp_id == "CP14" else "ROLE_GROUNDED_ORDINARY_PERSON",
            "platform_target": "xiaohongshu_note_video" if cp_id != "CP14" else "douyin_silent_visual_short",
            "narrative_device": "lived_scene_observation" if cp_id != "CP14" else "nonverbal_material_sequence",
            "opening_family": "small_scene_hook" if cp_id != "CP14" else "visual_first_hook",
            "information_order": "image_feeling_fact_boundary" if cp_id != "CP14" else "texture_motion_pause",
            "reasoning_shape": "ordinary_use_case_reflection" if cp_id != "CP14" else "sensory_association_no_claim",
            "language_register": "plain_life_language" if cp_id != "CP14" else "minimal_caption_language",
            "visual_audio_grammar": "close_detail_cutaway" if cp_id != "CP14" else "silent_macro_sequence",
            "closing_family": "soft_nonpush_close" if cp_id != "CP14" else "no_cta_visual_close",
            "spoken_line_allowed": cp_id != "CP14",
            "CTA_allowed": cp_id != "CP14",
        },
    ]


def build_assignments(root: Path, packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pack_by_cp = {unwrap(row, "qualification_material_pack")["content_product_type_id"]: unwrap(row, "qualification_material_pack") for row in packs}
    rows: list[dict[str, Any]] = []
    sequence = 1
    for material in CP_MATERIALS:
        cp_id = material["cp"]
        pack = pack_by_cp[cp_id]
        for lane in lane_specs(cp_id):
            assignment = {
                "schema_version": "v0.1",
                "task_id": TASK_ID,
                "assignment_id": f"QASSIGN-{cp_id}-{lane['lane_code']}-001",
                "asset_id": f"QPROBE-{cp_id}-{lane['lane_code']}-001",
                "content_product_type_id": cp_id,
                "content_product_label": material["label"],
                "material_pack_ref": pack["pack_id"],
                "material_pack_digest": pack["pack_digest"],
                "voice_lane": lane["voice_lane"],
                "lane_code": lane["lane_code"],
                "platform_target": lane["platform_target"],
                "narrative_device": lane["narrative_device"],
                "opening_family": lane["opening_family"],
                "information_order": lane["information_order"],
                "reasoning_shape": lane["reasoning_shape"],
                "language_register": lane["language_register"],
                "visual_audio_grammar": lane["visual_audio_grammar"],
                "closing_family": lane["closing_family"],
                "spoken_line_allowed": lane["spoken_line_allowed"],
                "CTA_allowed": lane["CTA_allowed"],
                "difference_axis_count_min": 4,
                "checkpoint_id": f"CHK-{((int(cp_id[2:]) - 1) // 5) + 1}",
                "execution_order": sequence,
                "frozen_before_authoring": True,
                "semantic_reroll_allowed": False,
                "replacement_asset_id_allowed": False,
                "assignment_digest": "",
            }
            assignment["assignment_digest"] = object_digest(assignment, {"assignment_digest"})
            rows.append({"qualification_probe_assignment": assignment})
            sequence += 1
    return rows


def build_plans(root: Path, packs: list[dict[str, Any]], assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validation_plan_by_cp = validation_plans(root)
    pack_by_cp = {unwrap(row, "qualification_material_pack")["content_product_type_id"]: unwrap(row, "qualification_material_pack") for row in packs}
    rows: list[dict[str, Any]] = []
    for wrapper in assignments:
        assignment = unwrap(wrapper, "qualification_probe_assignment")
        cp_id = assignment["content_product_type_id"]
        source_plan = validation_plan_by_cp[cp_id]
        pack = pack_by_cp[cp_id]
        plan = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "plan_id": f"ORCH-QUALPLAN-{cp_id}-{assignment['lane_code']}-001",
            "plan_type": "ORCHQualificationCompositionPlan",
            "plan_mode": "QUALIFICATION_SYNTHETIC",
            "namespace": QUALIFICATION_NAMESPACE,
            "qualification_plan_namespace": "CANONICAL_QUALIFICATION_COMPOSITION_PLAN",
            "writer": "ORCH",
            "canonicality_scope": "QUALIFICATION_ONLY",
            "qualification_authorization_ref": TASK_ID,
            "content_product": source_plan["content_product"],
            "assignment_ref": assignment["assignment_id"],
            "assignment_digest": assignment["assignment_digest"],
            "material_pack_ref": pack["pack_id"],
            "material_pack_digest": pack["pack_digest"],
            "derived_validation_plan_ref": source_plan["plan_id"],
            "derived_validation_plan_digest": source_plan["plan_digest"],
            "required_role_resolution": source_plan["required_role_resolution"],
            "selected_components": source_plan["selected_components"],
            "compatibility_resolution": source_plan["compatibility_resolution"],
            "synthetic_bindings": {
                "qualification_material_pack_ref": pack["pack_id"],
                "qualification_material_pack_digest": pack["pack_digest"],
                "source_ref_ids": [item["source_ref"] for item in pack["evidence_objects"]],
                "authorization_ref_ids": [item["authorization_id"] for item in pack["authorization_atoms"]],
                "all_fixture_only": True,
                "synthetic_qualification_only": True,
                "authorization_status": "SIMULATED_GRANTED_FOR_QUALIFICATION_TEST",
                "verified_brand_fact_count": 0,
                "verified_authorization_count": 0,
                "GRANTED_VERIFIED_authorization_count": 0,
                "real_event_binding_count": 0,
            },
            "lifecycle": {
                "canonical_within_qualification_namespace": True,
                "qualification_consumable": True,
                "runtime_consumable": False,
                "production_consumable": False,
                "publishable": False,
                "runtime_authoritative": False,
                "production_executable": False,
                "runtime_ingest_ready": False,
                "dify_consumable": False,
            },
            "output_contract": {
                "title_allowed": True,
                "body_allowed": True,
                "spoken_line_payload_allowed": assignment["spoken_line_allowed"],
                "CTA_payload_allowed": assignment["CTA_allowed"],
                "execution_payload_allowed": True,
                "audience_facing_output_allowed": False,
                "surface_unit_exact_join_required": True,
            },
            "plan_digest": "",
        }
        plan["plan_digest"] = object_digest(plan, {"plan_digest"})
        rows.append({"canonical_qualification_composition_plan": plan})
    return rows


def build_instructions(
    root: Path,
    packs: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    plans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pack_by_id = {unwrap(row, "qualification_material_pack")["pack_id"]: unwrap(row, "qualification_material_pack") for row in packs}
    plan_by_assignment = {
        unwrap(row, "canonical_qualification_composition_plan")["assignment_ref"]: unwrap(
            row, "canonical_qualification_composition_plan"
        )
        for row in plans
    }
    rows: list[dict[str, Any]] = []
    for wrapper in assignments:
        assignment = unwrap(wrapper, "qualification_probe_assignment")
        plan = plan_by_assignment[assignment["assignment_id"]]
        pack = pack_by_id[assignment["material_pack_ref"]]
        instruction = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "instruction_id": f"QINSTR-{assignment['content_product_type_id']}-{assignment['lane_code']}-001",
            "assignment_id": assignment["assignment_id"],
            "assignment_digest": assignment["assignment_digest"],
            "qualification_plan_ref": plan["plan_id"],
            "qualification_plan_digest": plan["plan_digest"],
            "material_pack_ref": pack["pack_id"],
            "material_pack_digest": pack["pack_digest"],
            "authoring_mode": "CONTROLLED_EXECUTION_AGENT_QUALIFICATION",
            "external_provider_adapter_enabled": False,
            "external_provider_request_count": 0,
            "credential_read_count": 0,
            "instruction": {
                "read_one_plan_only": True,
                "do_not_modify_plan": True,
                "do_not_add_input_fact": True,
                "visible_wrapper_required": VISIBLE_DISCLOSURE_TEXT,
                "surface_unit_exact_join_required_for_all_surfaces": True,
                "machine_max_acceptance_state": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN",
                "guardian_full_text_semantic_review_required": True,
            },
            "instruction_digest": "",
        }
        instruction["instruction_digest"] = object_digest(instruction, {"instruction_digest"})
        rows.append({"qualification_generation_instruction": instruction})
    return rows


def expected_texts(root: Path) -> dict[Path, str]:
    packs = build_packs(root)
    assignments = build_assignments(root, packs)
    plans = build_plans(root, packs, assignments)
    instructions = build_instructions(root, packs, assignments, plans)
    return {
        PACKS_PATH: jsonl_text(packs),
        ASSIGNMENTS_PATH: jsonl_text(assignments),
        PLANS_PATH: jsonl_text(plans),
        INSTRUCTIONS_PATH: jsonl_text(instructions),
    }


def write_files(root: Path) -> None:
    (root / TASK_DIR).mkdir(parents=True, exist_ok=True)
    for path, text in expected_texts(root).items():
        (root / path).write_text(text, encoding="utf-8")


def check_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path, text in expected_texts(root).items():
        full = root / path
        if not full.exists():
            errors.append(f"missing {path}")
        elif full.read_text(encoding="utf-8") != text:
            errors.append(f"materialized drift {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.check:
        errors = check_files(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("qualification_probe_40_orch_materializer CHECK_PASS")
        return 0
    write_files(root)
    print("qualification_probe_40_orch_materializer WROTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
