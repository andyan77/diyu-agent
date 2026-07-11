#!/usr/bin/env python3
"""Build the Controlled V2 20-profile completion artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GKB-CONTROLLED-V2-CONTENT-PRODUCT-PROFILE-20-COMPLETION-AND-ID-REBASELINE-001"
BASELINE_HEAD = "538b464042656dec7df0e05acff554a8a4b4528f"

CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
SCALE_600_CONTRACT_SHA256 = (
    "966190c341b070d88fbc3a25540e9c8fddf69ad8f19b90fb29badbb1ffad52a9"
)
S1_RESULT_FILE_SHA256 = "61a97a8abe3e0b3187b1d547a83832eb645624684b637f8417920dba9f63d265"
S1_RESULT_INTERNAL_DIGEST = "baf2616624ea0bb71ef87eb5f5467fd03a2738a7afeec621a3cde77a9681f711"
S1_CONTRACT_SHA256 = "7bf9315ebbb5bf97c3330695de7327af42ae30771b6315d2432c5c78d51d742c"
S1_PROFILES_V0_1_SHA256 = "c4e744f3f0505025d780f46eb12b879f1b9920ede63e4c84ffbc3fac9a715a6c"
S1_SOURCE_SELECTION_SHA256 = "36708420abc159f5a557f48c421ebf0b46a345384afdea9821c6ff0f0089f38c"
S1_CANDIDATES_SHA256 = "70ce2f7ebae3699fba6be0a0fff5d4a0a8e1023bbd32ae5a4f7340b3c4f43f7d"
S1_BUNDLES_SHA256 = "6d294274ea235962c33a8e7cd9f4d4be92d2e6ce5b48860286a1d13f08ce7970"
S1_HANDOFF_SHA256 = "12a369dcf64641a16b73636e95ba1c710fc787efa663608f446f73634a2f6223"

S1_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = S1_DIR / "content_product_profile_20_completion_001"
CONTRACT_PATH = TASK_DIR / "content_product_profile_contract.v0.2.yaml"
PROFILES_PATH = TASK_DIR / "content_product_profiles.v0.2.yaml"
MIGRATION_PATH = TASK_DIR / "content_product_profile_legacy_migration.v0.1.yaml"
COVERAGE_PATH = TASK_DIR / "content_product_profile_coverage_and_gap.v0.1.yaml"
RESULT_PATH = TASK_DIR / "content_product_profile_20_completion_result.v0.1.yaml"
VALIDATOR_PATH = TASK_DIR / "run_content_product_profile_20_validator.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_content_product_profiles_20.py")

S1_PATHS = {
    "result": S1_DIR / "controlled_composition_v2_result.v0.1.yaml",
    "contract": S1_DIR / "controlled_composition_v2_contract.v0.1.yaml",
    "profiles_v0_1": S1_DIR / "content_product_profiles.v0.1.yaml",
    "source_selection": S1_DIR / "pilot_source_selection.v0.1.yaml",
    "candidates": S1_DIR / "component_candidate_manifest.v0.1.jsonl",
    "bundles": S1_DIR / "gkb_composition_candidate_bundles.v0.1.jsonl",
    "pilot_handoff": S1_DIR / "gkb_orch_pilot_handoff.v0.1.yaml",
}

EVENT_TRUTH_MODES = [
    "brand_supplied_real_event",
    "brand_fillable_prototype",
    "generic_creative_prototype",
    "collection_task_only",
]

FAMILIES = {
    "F1_PEOPLE_AND_REAL_SCENE": {
        "products": ["CP01", "CP02", "CP03", "CP04", "CP05"],
        "planning_share_percent": 30,
        "purpose": "活人感、在场感、账号人格",
    },
    "F2_PROFESSIONAL_AND_SEARCH": {
        "products": ["CP06", "CP07", "CP08", "CP09", "CP10"],
        "planning_share_percent": 25,
        "purpose": "搜索资产、收藏、专业信任",
    },
    "F3_PRODUCT_RELATION_AND_AESTHETIC": {
        "products": ["CP11", "CP12", "CP13", "CP14"],
        "planning_share_percent": 20,
        "purpose": "产品记忆、审美区别、商业连接",
    },
    "F4_STORE_LOCAL_AND_RETAIL": {
        "products": ["CP15", "CP16", "CP17", "CP18"],
        "planning_share_percent": 15,
        "purpose": "同城、到店、加盟门店差异",
    },
    "F5_ENTERPRISE_LONG_TERM_TRUST": {
        "products": ["CP19", "CP20"],
        "planning_share_percent": 10,
        "purpose": "品牌信用、组织人格、长期背书",
    },
}

PRODUCTS = [
    {
        "id": "CP01",
        "slug": "role_task_vlog",
        "label": "岗位任务VLOG",
        "core_inputs": ["具体人员", "真实岗位", "当天或明确周期任务", "工作对象", "动作链", "判断点", "结果或未完成状态"],
        "narrative": ["时间顺序", "问题—判断—动作", "未完成连续记录"],
        "style": ["岗位口语", "观察纪实", "环境原声", "保留停顿"],
        "accounts": ["professional_role_account"],
        "platforms": ["douyin", "kuaishou", "wechat_channels"],
        "hard_guards": ["必须围绕真实任务", "禁止忙碌镜头拼贴", "禁止企业宣传语塞进员工嘴里"],
        "required_roles": ["scene", "observable_action", "professional_judgment", "capture_instruction"],
        "continuity_model": "single_task_or_explicit_period",
        "runtime_thread_required": False,
    },
    {
        "id": "CP02",
        "slug": "store_time_slice_micro_documentary",
        "label": "门店时段微纪录",
        "core_inputs": ["真实门店或授权别名", "明确时段", "实际门店任务或状态", "空间对象", "可用现场素材"],
        "narrative": ["时间切片", "固定机位", "空间观察"],
        "style": ["生活流白描", "低旁白", "环境声", "自然节奏"],
        "accounts": ["store_account"],
        "platforms": ["douyin", "kuaishou", "wechat_channels"],
        "hard_guards": ["禁止伪造门店事件", "允许普通重复和没有高潮"],
        "required_roles": ["scene", "visual_beat", "observable_action", "capture_instruction"],
        "continuity_model": "bounded_time_slice",
        "runtime_thread_required": False,
    },
    {
        "id": "CP03",
        "slug": "single_craft_process",
        "label": "单项手艺全过程",
        "core_inputs": ["真实任务", "责任岗位", "工作对象", "输入状态", "完整步骤", "判断节点", "结果或未完成状态"],
        "narrative": ["输入—步骤—判断—结果", "局部动作放大"],
        "style": ["手部中心", "操作原声", "低语言密度", "过程美感"],
        "accounts": ["professional_role_account", "store_account"],
        "platforms": ["douyin", "xiaohongshu"],
        "hard_guards": ["禁止省略关键因果动作", "禁止库存B-roll冒充过程"],
        "required_roles": ["scene", "observable_action", "trigger", "visual_beat", "capture_instruction"],
        "continuity_model": "single_process_trace",
        "runtime_thread_required": False,
    },
    {
        "id": "CP04",
        "slug": "multi_role_collaboration_documentary",
        "label": "多岗位协作纪实",
        "core_inputs": ["真实协作事件", "参与岗位", "共同业务对象", "各岗位动作和权限", "交接或协商结果", "参与者授权"],
        "narrative": ["多声部", "岗位接力", "同一对象多视角"],
        "style": ["克制对话", "保留差异", "不制造对立"],
        "accounts": ["brand_account", "professional_role_account"],
        "platforms": ["wechat_channels", "douyin"],
        "hard_guards": ["禁止编造争吵", "禁止角色权限混用", "required_people必须覆盖真实参与者"],
        "required_roles": ["scene", "observable_action", "transition", "professional_judgment", "capture_instruction"],
        "continuity_model": "multi_role_event_thread",
        "runtime_thread_required": True,
        "extra_fact_slots": ["participating_roles", "role_authority_boundaries"],
        "extra_authorization_slots": ["participant_authorizations"],
    },
    {
        "id": "CP05",
        "slug": "career_growth_and_professional_history",
        "label": "人物成长与职业史",
        "core_inputs": ["真实人物或授权别名", "真实职业经历", "时间节点", "技能形成证据", "失败或变化事实", "人物授权"],
        "narrative": ["时间线", "口述史", "阶段回访", "师徒双视角"],
        "style": ["温和纪实", "档案材料", "低煽情", "长期跟踪"],
        "accounts": ["professional_role_account", "brand_account"],
        "platforms": ["wechat_channels", "xiaohongshu", "official_account"],
        "hard_guards": ["禁止卖惨竞赛", "禁止编造经历", "禁止把加班等同成长"],
        "required_roles": ["scene", "trigger", "professional_judgment", "audience_facing_reasoning_move", "capture_instruction"],
        "continuity_model": "person_history_timeline",
        "runtime_thread_required": True,
    },
    {
        "id": "CP06",
        "slug": "professional_judgment_slice",
        "label": "专业判断切片",
        "core_inputs": ["真实岗位权威", "具体业务对象", "可观察信号", "判断条件", "适用限制"],
        "narrative": ["观察—判断—依据—限制", "局部细节—整体影响"],
        "style": ["岗位口语", "精确", "低说教", "专业词附人话解释"],
        "accounts": ["professional_role_account"],
        "platforms": ["xiaohongshu", "douyin"],
        "hard_guards": ["判断不得超过岗位权限", "禁止万能结论"],
        "required_roles": ["scene", "professional_judgment", "audience_facing_reasoning_move", "visual_beat"],
        "continuity_model": "single_judgment_slice",
        "runtime_thread_required": False,
    },
    {
        "id": "CP07",
        "slug": "user_question_diagnostic_room",
        "label": "用户问题诊断室",
        "core_inputs": ["真实搜索词或用户问题", "问题来源", "条件信息", "可用判断依据", "适用边界"],
        "narrative": ["问题分类", "条件判断", "决策树", "排除法"],
        "style": ["耐心", "直接", "非推销", "面向具体任务"],
        "accounts": ["professional_role_account", "store_account"],
        "platforms": ["xiaohongshu"],
        "hard_guards": ["禁止虚构用户提问", "禁止固定三招模板"],
        "required_roles": ["trigger", "professional_judgment", "audience_facing_reasoning_move", "closing"],
        "continuity_model": "question_case_with_conditions",
        "runtime_thread_required": False,
    },
    {
        "id": "CP08",
        "slug": "craft_material_fit_deconstruction",
        "label": "工艺／面料／版型解构",
        "core_inputs": ["真实对象", "部件或结构", "材料或工序", "可观察依据", "允许公开范围"],
        "narrative": ["拆解", "微观—结构—使用结果", "标准对照"],
        "style": ["冷静实证", "微距", "结构图", "操作同步"],
        "accounts": ["professional_account", "brand_account"],
        "platforms": ["xiaohongshu", "wechat_channels"],
        "hard_guards": ["禁止触感推导全部性能", "禁止局部工艺为整件产品背书"],
        "required_roles": ["scene", "visual_beat", "professional_judgment", "audience_facing_reasoning_move"],
        "continuity_model": "object_structure_case",
        "runtime_thread_required": False,
    },
    {
        "id": "CP09",
        "slug": "suitability_boundary_and_anti_selection",
        "label": "适用边界与反选指南",
        "core_inputs": ["真实产品或设计条件", "适用任务", "不适用条件", "替代选择", "Claim边界"],
        "narrative": ["条件—适用—不适用—替代", "反向决策"],
        "style": ["坦白", "克制", "不制造焦虑", "不羞辱身体"],
        "accounts": ["product_account", "sales_associate_account", "professional_account"],
        "platforms": ["xiaohongshu"],
        "hard_guards": ["禁止身体羞辱", "禁止绝对适配结论"],
        "required_roles": ["trigger", "professional_judgment", "audience_facing_reasoning_move", "closing"],
        "continuity_model": "bounded_selection_case",
        "runtime_thread_required": False,
    },
    {
        "id": "CP10",
        "slug": "evidence_and_long_term_validation_archive",
        "label": "证据与长期验证档案",
        "core_inputs": ["测试或使用记录", "条件", "时间节点", "结果", "局限", "允许公开证据"],
        "narrative": ["假设—条件—记录—结果—局限", "定期回访"],
        "style": ["工程日志", "谨慎结论", "时间标记", "低营销浓度"],
        "accounts": ["brand_account", "professional_account"],
        "platforms": ["xiaohongshu", "official_account", "wechat_channels"],
        "hard_guards": ["单次体验不得替代普遍规律", "无记录不得生成长期结论"],
        "required_roles": ["trigger", "professional_judgment", "audience_facing_reasoning_move", "capture_instruction"],
        "continuity_model": "evidence_time_series",
        "runtime_thread_required": True,
    },
    {
        "id": "CP11",
        "slug": "product_birth_and_design_tradeoff_archive",
        "label": "产品诞生与设计取舍档案",
        "core_inputs": ["真实需求或企划", "设计选项", "最终选择", "放弃方案", "材料或成本约束", "公开授权"],
        "narrative": ["问题—选项—选择—放弃—代价", "档案展开"],
        "style": ["克制档案", "设计随笔", "过程材料", "避免灵感神话"],
        "accounts": ["brand_account", "designer_account"],
        "platforms": ["wechat_channels", "xiaohongshu"],
        "hard_guards": ["禁止编造灵感故事", "禁止隐藏关键取舍条件"],
        "required_roles": ["scene", "trigger", "professional_judgment", "audience_facing_reasoning_move", "capture_instruction"],
        "continuity_model": "design_origin_archive",
        "runtime_thread_required": True,
    },
    {
        "id": "CP12",
        "slug": "product_iteration_and_version_log",
        "label": "产品迭代与版本日志",
        "core_inputs": ["产品或项目引用", "真实版本号或阶段", "变更点", "触发原因", "结果或待验证事项"],
        "narrative": ["版本—变更—原因—待验证"],
        "style": ["工程日志", "时间连续", "理性透明"],
        "accounts": ["product_account", "brand_account"],
        "platforms": ["xiaohongshu", "official_account"],
        "hard_guards": ["禁止不存在的版本历史", "禁止把待验证写成已证明"],
        "required_roles": ["trigger", "observable_action", "professional_judgment", "capture_instruction"],
        "continuity_model": "product_version_timeline",
        "runtime_thread_required": True,
    },
    {
        "id": "CP13",
        "slug": "product_life_and_wardrobe_role",
        "label": "产品的生活与衣橱角色",
        "core_inputs": ["真实产品或类型", "生活任务", "搭配关系", "季节位置", "使用条件"],
        "narrative": ["一件产品多场景", "衣橱关系", "身体—空间—时间关系"],
        "style": ["生活观察", "轻叙事", "低销售压力", "克制情感"],
        "accounts": ["product_account", "user_style_account"],
        "platforms": ["douyin", "xiaohongshu", "wechat_channels"],
        "hard_guards": ["禁止虚构具体生活经历", "场景演绎不得冒充已发生事实"],
        "required_roles": ["scene", "visual_beat", "audience_facing_reasoning_move", "transition"],
        "continuity_model": "product_life_role_case",
        "runtime_thread_required": False,
    },
    {
        "id": "CP14",
        "slug": "materiality_visual_and_sensory_short",
        "label": "物性影像与感官短片",
        "core_inputs": ["真实材料或产品", "真实光线", "真实动作", "真实声音", "可用拍摄素材"],
        "narrative": ["非语言叙事", "细节组合", "单一物性母题"],
        "style": ["微距", "环境声", "静默", "慢节奏", "少旁白"],
        "accounts": ["brand_account", "product_account"],
        "platforms": ["douyin", "xiaohongshu", "wechat_channels"],
        "hard_guards": ["禁止高级感空镜", "禁止过度调色", "禁止假慢镜", "禁止通用治愈音乐", "spoken_line和CTA不得设为必需组件"],
        "required_roles": ["scene", "visual_beat", "observable_action", "capture_instruction"],
        "continuity_model": "single_materiality_motif",
        "runtime_thread_required": False,
    },
    {
        "id": "CP15",
        "slug": "product_arrival_lifecycle",
        "label": "商品到店生命周期",
        "core_inputs": ["真实商品或批次", "到货时间", "真实岗位接力", "验收、整烫、上架、补货或退场状态", "允许公开范围"],
        "narrative": ["商品旅程", "时间轴", "多岗位接力"],
        "style": ["运营纪实", "信息清晰", "低促销浓度"],
        "accounts": ["store_account", "product_account"],
        "platforms": ["douyin", "wechat_channels"],
        "hard_guards": ["禁止虚构库存、售罄或调拨事实"],
        "required_roles": ["scene", "observable_action", "transition", "capture_instruction"],
        "continuity_model": "store_product_lifecycle",
        "runtime_thread_required": True,
    },
    {
        "id": "CP16",
        "slug": "real_service_review",
        "label": "真实服务复盘",
        "core_inputs": ["真实用户任务", "需求识别", "方案调整", "结果或未完成状态", "匿名化与授权"],
        "narrative": ["需求—判断—方案—反馈", "服务者复盘"],
        "style": ["平等", "尊重", "匿名化", "避免导购英雄化"],
        "accounts": ["store_account", "sales_associate_account"],
        "platforms": ["xiaohongshu", "wechat_channels"],
        "hard_guards": ["禁止假顾客", "禁止暴露隐私", "禁止导购英雄化"],
        "required_roles": ["trigger", "observable_action", "professional_judgment", "capture_instruction"],
        "continuity_model": "anonymized_service_case",
        "runtime_thread_required": True,
        "extra_fact_slots": ["customer_task_truth", "service_feedback_or_unfinished_state"],
        "extra_authorization_slots": ["customer_privacy_consent", "anonymization_approval"],
    },
    {
        "id": "CP17",
        "slug": "display_change_and_space_experiment",
        "label": "陈列换陈与空间实验",
        "core_inputs": ["真实陈列区域", "陈列目标", "原状态", "调整动作", "视觉复核", "用户行为观察边界"],
        "narrative": ["假设—调整—前后—复核", "空间导览"],
        "style": ["整洁秩序", "固定视点", "动作实录", "谨慎解释"],
        "accounts": ["store_account", "visual_merchandiser_account"],
        "platforms": ["douyin", "xiaohongshu"],
        "hard_guards": ["禁止假前后对照", "禁止把观察相关性写成因果"],
        "required_roles": ["scene", "trigger", "observable_action", "visual_beat", "capture_instruction"],
        "continuity_model": "display_before_after_review",
        "runtime_thread_required": True,
    },
    {
        "id": "CP18",
        "slug": "city_store_life_chronicle",
        "label": "城市门店生活志",
        "core_inputs": ["真实城市与门店", "地方气候或节令", "街区与职业人群", "门店生活事件", "地域语言或声景素材"],
        "narrative": ["地方观察", "季节编年", "门店与社区关系"],
        "style": ["地域口语", "生活纪录", "街区声景", "低营销"],
        "accounts": ["local_store_account"],
        "platforms": ["douyin", "kuaishou", "wechat_channels"],
        "hard_guards": ["禁止总部脚本加地理标签冒充本地生活", "禁止编造地方习惯和常客关系"],
        "required_roles": ["scene", "visual_beat", "observable_action", "capture_instruction"],
        "continuity_model": "local_store_chronicle",
        "runtime_thread_required": True,
        "extra_source_slots": ["local_language_or_soundscape_materials"],
        "extra_fact_slots": ["real_city_and_store", "local_climate_or_season", "neighborhood_or_professional_crowd"],
    },
    {
        "id": "CP19",
        "slug": "business_tradeoff_and_decision_review",
        "label": "经营取舍与决策复盘",
        "core_inputs": ["真实经营背景", "实际选项", "最终选择", "放弃事项", "成本或代价", "结果或未完成事项", "企业发言授权"],
        "narrative": ["背景—选项—选择—放弃—代价—结果"],
        "style": ["创始人随笔", "组织复盘", "坦白但不自我感动"],
        "accounts": ["brand_account", "founder_account"],
        "platforms": ["wechat_channels", "official_account"],
        "cadence": "low_frequency",
        "hard_guards": ["无真实放弃和代价不得成立", "禁止自我表彰和空喊长期主义"],
        "required_roles": ["trigger", "professional_judgment", "audience_facing_reasoning_move", "closing"],
        "continuity_model": "business_decision_review_thread",
        "runtime_thread_required": True,
    },
    {
        "id": "CP20",
        "slug": "commitment_and_fulfillment_tracking",
        "label": "承诺—兑现追踪",
        "core_inputs": ["真实公开承诺", "承诺主体", "时间节点", "执行证据", "结果或偏差", "修正动作", "下一复核时间", "企业公开授权"],
        "narrative": ["承诺—节点—证据—结果—下一步"],
        "style": ["庄重", "简洁", "证据优先", "禁止情绪包装"],
        "accounts": ["brand_primary_account"],
        "platforms": ["wechat_channels", "official_account", "xiaohongshu"],
        "cadence": "low_frequency",
        "hard_guards": ["无承诺或证据不得成立", "未做到必须允许如实记录", "禁止情绪替代证据"],
        "required_roles": ["trigger", "professional_judgment", "audience_facing_reasoning_move", "capture_instruction"],
        "continuity_model": "commitment_evidence_review_schedule",
        "runtime_thread_required": True,
        "extra_fact_slots": ["public_commitment", "commitment_actor", "execution_evidence", "result_or_deviation", "next_review_time"],
        "extra_authorization_slots": ["enterprise_public_authorization"],
    },
]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_key(value: Any, key_to_strip: str) -> None:
    if isinstance(value, dict):
        value.pop(key_to_strip, None)
        for child in value.values():
            strip_key(child, key_to_strip)
    elif isinstance(value, list):
        for child in value:
            strip_key(child, key_to_strip)


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    stripped = copy.deepcopy(value)
    for key in digest_keys or set():
        strip_key(stripped, key)
    return sha256_text(canonical_json(stripped))


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)


def family_for_product(product_id: str) -> str:
    for family_id, family in FAMILIES.items():
        if product_id in family["products"]:
            return family_id
    raise KeyError(product_id)


def input_routes() -> list[dict[str, Any]]:
    return [
        {
            "route_id": "all_required_inputs_present",
            "missing_slot_classes": [],
            "allowed_outputs": ["content_candidate", "shooting_plan"],
            "audience_facing_body_allowed": True,
            "first_person_experience_allowed": True,
            "product_claim_allowed": True,
        },
        {
            "route_id": "required_source_missing",
            "missing_slot_classes": ["source"],
            "allowed_outputs": ["material_capture_plan", "slot_based_outline"],
            "audience_facing_body_allowed": False,
            "first_person_experience_allowed": False,
            "product_claim_allowed": False,
        },
        {
            "route_id": "required_fact_missing",
            "missing_slot_classes": ["fact"],
            "allowed_outputs": ["fact_collection_task", "interview_outline"],
            "audience_facing_body_allowed": False,
            "first_person_experience_allowed": False,
            "product_claim_allowed": False,
        },
        {
            "route_id": "required_authorization_missing",
            "missing_slot_classes": ["authorization"],
            "allowed_outputs": ["authorization_collection_task", "anonymous_capture_plan"],
            "audience_facing_body_allowed": False,
            "first_person_experience_allowed": False,
            "product_claim_allowed": False,
        },
    ]


def product_input_slots(product: dict[str, Any]) -> dict[str, list[str]]:
    source_slots = ["usable_source_materials", "product_or_scene_reference"]
    fact_slots = [
        f"{product['id'].lower()}_core_input_signature",
        "real_event_or_object_truth",
        "claim_boundary",
    ]
    authorization_slots = ["publication_scope_authorization"]

    for source_slot in product.get("extra_source_slots", []):
        if source_slot not in source_slots:
            source_slots.append(source_slot)
    for fact_slot in product.get("extra_fact_slots", []):
        if fact_slot not in fact_slots:
            fact_slots.append(fact_slot)
    for auth_slot in product.get("extra_authorization_slots", []):
        if auth_slot not in authorization_slots:
            authorization_slots.append(auth_slot)
    if product["id"] in {"CP01", "CP03", "CP04", "CP05", "CP06"}:
        fact_slots.append("real_role_or_person_truth")
    if product["id"] in {"CP05", "CP10", "CP12", "CP20"}:
        fact_slots.append("time_state_or_version_marker")
    return {
        "required_source_slots": source_slots,
        "required_fact_slots": fact_slots,
        "required_authorization_slots": authorization_slots,
    }


def build_profile(product: dict[str, Any]) -> dict[str, Any]:
    input_slots = product_input_slots(product)
    hard_guard_ids = [f"AGR_{product['id']}_{index:02d}" for index, _ in enumerate(product["hard_guards"], start=1)]
    profile = {
        "schema_version": "v0.2",
        "profile_version": "v0.2",
        "content_product_type_id": product["id"],
        "canonical_slug": product["slug"],
        "chinese_label": product["label"],
        "family_id": family_for_product(product["id"]),
        "lifecycle": "PROFILE_DEFINED_PENDING_COMPONENT_SUPPLY",
        "owner": "GKB",
        "runtime_plan_owner": "ORCH",
        "business_purpose": FAMILIES[family_for_product(product["id"])]["purpose"],
        "cadence_policy": product.get("cadence", "standard_frequency"),
        "target_account_roles": product["accounts"],
        "target_platforms": product["platforms"],
        "founder_core_inputs": product["core_inputs"],
        "required_component_roles": [
            {"role": role, "min_count": 1, "max_count": 3} for role in product["required_roles"]
        ],
        "optional_component_roles": [
            {"role": "opening", "min_count": 0, "max_count": 1},
            {"role": "closing", "min_count": 0, "max_count": 1},
        ],
        "input_requirements": input_slots,
        "event_truth_policy": {
            "allowed_event_truth_modes": EVENT_TRUTH_MODES,
            "default_deny_unlisted": True,
        },
        "narrative_constraints": {
            "allowed_narrative_operator_families": product["narrative"],
            "required_tension_source_types": [
                "real_task_condition",
                "observable_constraint",
                "authorized_time_state",
            ],
            "fabricated_conflict_allowed": False,
        },
        "style_constraints": {
            "preferred_style_vector_ranges": {
                "marketing_density": "low_to_medium",
                "fact_specificity": "high",
                "emotional_intensity": "low_to_moderate",
            },
            "founder_style_terms": product["style"],
            "forbidden_style_patterns": [
                "one_size_fits_all_template",
                "先看—再看—免责声明—CTA",
                "empty_brand_slogan",
            ],
        },
        "continuity_policy": {
            "model": product["continuity_model"],
            "runtime_thread_required": product["runtime_thread_required"],
            "continuity_state_owner": "ORCH",
        },
        "visual_audio_requirement_refs": [
            "REAL_MATERIAL_OR_SCENE_SOURCE_REQUIRED",
            "NO_STOCK_BROLL_AS_EVENT_PROOF",
        ],
        "platform_expression_requirement_refs": [
            f"PLATFORM_SET::{','.join(product['platforms'])}",
        ],
        "anti_pattern_rule_refs": hard_guard_ids,
        "founder_hard_guards": [
            {"rule_id": rule_id, "text": text} for rule_id, text in zip(hard_guard_ids, product["hard_guards"])
        ],
        "input_sufficiency_routes": input_routes(),
        "quality_rubric_refs": [
            "QR_INPUT_SUFFICIENCY_V0_2",
            "QR_FOUNDER_PRODUCT_DEFINITION_FIDELITY_V0_2",
            "QR_NO_AUDIENCE_BODY_WITHOUT_REAL_INPUT_V0_2",
        ],
        "fixture_refs": {
            "positive": [],
            "negative": [],
            "fixture_coverage": "missing_explicit",
            "usage": "evaluation_and_guardian_calibration_only",
            "may_enter_generation_prompt": False,
            "may_supply_facts": False,
        },
        "component_supply_state": {
            "reviewed_reusable_component_count": 0,
            "required_role_coverage": "NOT_EVALUATED",
            "ORCH_profile_eligible": False,
        },
    }
    profile["profile_digest"] = object_digest(profile, {"profile_digest"})
    return profile


def build_contract() -> dict[str, Any]:
    return {
        "content_product_profile_contract_v0_2": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "baseline_head": BASELINE_HEAD,
            "purpose": "canonical 20 content product profile registry contract",
            "s1_immutability": {
                "result_file_sha256": S1_RESULT_FILE_SHA256,
                "result_internal_digest": S1_RESULT_INTERNAL_DIGEST,
                "contract_sha256": S1_CONTRACT_SHA256,
                "profiles_v0_1_sha256": S1_PROFILES_V0_1_SHA256,
                "source_selection_sha256": S1_SOURCE_SELECTION_SHA256,
                "candidates_sha256": S1_CANDIDATES_SHA256,
                "bundles_sha256": S1_BUNDLES_SHA256,
                "pilot_handoff_sha256": S1_HANDOFF_SHA256,
            },
            "allocation_policy": {
                "status": "PLANNING_POLICY_NOT_EXECUTION_QUOTA",
                "family_planning_shares": {
                    family_id: family["planning_share_percent"] for family_id, family in FAMILIES.items()
                },
                "sum_percent": 100,
                "generation_authority": False,
                "may_not_auto_allocate_600": True,
            },
            "profile_hard_rules": [
                "Profile is input sufficiency and output eligibility contract, not content body.",
                "No forbidden_event_truth_modes second source of truth.",
                "Unlisted event truth modes default-deny.",
                "Missing input behavior only lives in input_sufficiency_routes.",
                "Fixtures are evaluation-only and cannot enter generation prompts.",
                "Fixture gaps must be explicit and cannot be filled with fake fixtures.",
                "Planning share is not generation authorization.",
                "Profile cannot prove fact truth, content quality, or runtime readiness.",
                "No profile inheritance system, rule DSL, or graph database.",
            ],
            "component_supply_default": {
                "reviewed_reusable_component_count": 0,
                "required_role_coverage": "NOT_EVALUATED",
                "ORCH_profile_eligible": False,
            },
            "forbidden_outputs_this_task": {
                "audience_body": False,
                "title": False,
                "spoken_script": False,
                "new_component": False,
                "new_bundle": False,
                "canonical_composition_plan": False,
            },
        }
    }


def build_profiles() -> dict[str, Any]:
    profiles = [build_profile(product) for product in PRODUCTS]
    registry = {
        "content_product_profile_registry": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "families": {
                family_id: {
                    "family_id": family_id,
                    "products": family["products"],
                    "planning_share_percent": family["planning_share_percent"],
                    "purpose": family["purpose"],
                }
                for family_id, family in FAMILIES.items()
            },
            "allocation_policy": {
                "status": "PLANNING_POLICY_NOT_EXECUTION_QUOTA",
                "sum_percent": 100,
                "generation_authority": False,
                "may_not_auto_allocate_600": True,
            },
            "profile_count": len(profiles),
            "profiles": profiles,
        }
    }
    registry["content_product_profile_registry"]["registry_digest"] = object_digest(
        registry["content_product_profile_registry"], {"registry_digest"}
    )
    return registry


def build_migration() -> dict[str, Any]:
    migration = {
        "legacy_profile_migration": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "source_profiles_version": "v0.1",
            "target_profiles_version": "v0.2",
            "mappings": {
                "CP_ROLE_WORK_VLOG": {
                    "canonical_target": "CP01",
                    "mapping": "DIRECT",
                },
                "CP_STORE_MICRO_DOCUMENTARY": {
                    "canonical_target": "CP02",
                    "mapping": "DIRECT",
                },
                "CP_PRODUCT_ITERATION_ARCHIVE": {
                    "canonical_targets": ["CP11", "CP12"],
                    "mapping": "SPLIT_REQUIRED",
                    "automatic_target_selection": "forbidden",
                    "routing_rule": {
                        "design_origin_and_tradeoff": "CP11",
                        "version_change_and_iteration": "CP12",
                    },
                    "forbidden_shortcut": "legacy_third_profile_must_not_map_to_new_CP03",
                },
            },
            "old_pilot_bundles": {
                "remain_unchanged": True,
                "historical_contract_proof_only": True,
                "in_place_migration_allowed": False,
                "counts_as_20_profile_fixture_coverage": False,
                "becomes_ORCH_plan": False,
                "future_use_requires_CP11_or_CP12_reclassification": True,
            },
            "old_89_candidates": {
                "remain_unchanged": True,
                "next_stage_reclassifies_applicable_content_product_type_ids": True,
                "mechanical_inheritance_from_3_profile_applicability_allowed": False,
            },
        }
    }
    migration["legacy_profile_migration"]["migration_digest"] = object_digest(
        migration["legacy_profile_migration"], {"migration_digest"}
    )
    return migration


def build_coverage(profiles_doc: dict[str, Any]) -> dict[str, Any]:
    profiles = profiles_doc["content_product_profile_registry"]["profiles"]
    records = []
    for profile in profiles:
        records.append(
            {
                "content_product_type_id": profile["content_product_type_id"],
                "fixture_coverage": "missing_explicit",
                "positive_refs": [],
                "negative_refs": [],
                "blocks_content_quality_validation": True,
                "gap_reason": "No product-specific positive/negative fixture pair was authorized or mapped in this task.",
            }
        )
    coverage = {
        "content_product_profile_coverage_and_gap": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "fixture_policy": {
                "copy_body_text_allowed": False,
                "may_enter_generation_prompt": False,
                "may_supply_facts": False,
                "fake_fixture_allowed": False,
            },
            "existing_reference_pools_considered": [
                {
                    "ref_id": "CLEAN_120_REFERENCE_CORPUS",
                    "path": str(
                        Path(
                            "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
                            "clean_120_reference_corpus_freeze_001/"
                            "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
                        )
                    ),
                    "sha256": CLEAN_120_SHA256,
                    "assigned_as_product_specific_fixture": False,
                    "reason": "Clean-120 is a frozen reference pool, not a complete per-product fixture suite.",
                },
                {
                    "ref_id": "S1_HISTORICAL_9_BUNDLES",
                    "path": str(S1_PATHS["bundles"]),
                    "sha256": S1_BUNDLES_SHA256,
                    "assigned_as_product_specific_fixture": False,
                    "reason": "Brief forbids using old pilot bundles as 20 Profile coverage evidence.",
                },
            ],
            "coverage_records": records,
            "summary": {
                "profile_count": len(records),
                "complete_count": 0,
                "partial_count": 0,
                "missing_explicit_count": len(records),
                "blocks_content_quality_validation_count": len(records),
            },
        }
    }
    coverage["content_product_profile_coverage_and_gap"]["coverage_digest"] = object_digest(
        coverage["content_product_profile_coverage_and_gap"], {"coverage_digest"}
    )
    return coverage


def build_result(file_digests: dict[str, str], profiles_digest: str, migration_digest: str, gap_count: int) -> dict[str, Any]:
    result = {
        "content_product_profile_20_completion_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "verdict": "CONTENT_PRODUCT_PROFILE_20_COMPLETION_EXECUTED_PENDING_CLAUDE_GUARDIAN",
            "baseline_head_before": BASELINE_HEAD,
            "counts": {
                "content_product_family_count": 5,
                "content_product_profile_count": 20,
                "planning_share_sum": 100,
                "component_supply_evaluated": False,
                "ORCH_eligible_profile_count": 0,
                "reviewed_reusable_component_count": 0,
                "canonical_composition_plan_count": 0,
                "audience_facing_content_count": 0,
                "title_count": 0,
                "spoken_script_count": 0,
                "fixture_gap_count": gap_count,
            },
            "s1_immutability": {
                "result_file_sha256": S1_RESULT_FILE_SHA256,
                "result_internal_digest": S1_RESULT_INTERNAL_DIGEST,
                "contract_sha256": S1_CONTRACT_SHA256,
                "profiles_v0_1_sha256": S1_PROFILES_V0_1_SHA256,
                "source_selection_sha256": S1_SOURCE_SELECTION_SHA256,
                "candidates_sha256": S1_CANDIDATES_SHA256,
                "bundles_sha256": S1_BUNDLES_SHA256,
                "pilot_handoff_sha256": S1_HANDOFF_SHA256,
            },
            "proof_scope": {
                "profiles_20_machine_source_created": True,
                "families_and_planning_share_encoded": True,
                "legacy_3_profile_migration_defined": True,
                "next_stage_can_review_89_candidates_against_20_profiles": True,
            },
            "not_proven": [
                "20_products_have_component_supply",
                "20_products_are_runtime_eligible",
                "20_products_content_quality_passed",
                "ORCH_integrated",
                "generation_600_allowed",
            ],
            "readiness_flags": readiness_flags(),
            "generated_file_digests": file_digests,
            "profile_registry_digest": profiles_digest,
            "migration_digest": migration_digest,
            "blocking_items": [],
        }
    }
    result["content_product_profile_20_completion_result"]["result_digest"] = object_digest(
        result["content_product_profile_20_completion_result"], {"result_digest"}
    )
    return result


def readiness_flags() -> dict[str, bool]:
    return {
        "runtime_ingest_ready": False,
        "generation_600_allowed": False,
        "expand_600_allowed": False,
        "expand_3600_allowed": False,
        "CandidatePack_ready": False,
        "KE_ready": False,
        "Serving_ready": False,
        "RAG_ready": False,
        "DIFY_ready": False,
        "production_ready": False,
    }


def build_artifacts(root: Path) -> dict[Path, str]:
    contract = build_contract()
    profiles = build_profiles()
    migration = build_migration()
    coverage = build_coverage(profiles)

    artifacts = {
        CONTRACT_PATH: yaml_text(contract),
        PROFILES_PATH: yaml_text(profiles),
        MIGRATION_PATH: yaml_text(migration),
        COVERAGE_PATH: yaml_text(coverage),
    }
    file_digests = {str(path): sha256_text(text) for path, text in artifacts.items()}
    validator_abs = root / VALIDATOR_PATH
    checker_abs = root / CHECKER_PATH
    file_digests[str(VALIDATOR_PATH)] = sha256_file(validator_abs)
    file_digests[str(CHECKER_PATH)] = sha256_file(checker_abs) if checker_abs.exists() else "CHECKER_NOT_PRESENT"

    result = build_result(
        file_digests,
        profiles["content_product_profile_registry"]["registry_digest"],
        migration["legacy_profile_migration"]["migration_digest"],
        coverage["content_product_profile_coverage_and_gap"]["summary"]["missing_explicit_count"],
    )
    artifacts[RESULT_PATH] = yaml_text(result)
    return artifacts


def write_artifacts(root: Path, artifacts: dict[Path, str]) -> None:
    for relative_path, text in artifacts.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def check_artifacts(root: Path, artifacts: dict[Path, str]) -> list[str]:
    mismatches = []
    for relative_path, expected in artifacts.items():
        path = root / relative_path
        if not path.exists():
            mismatches.append(f"missing: {relative_path}")
        elif path.read_text(encoding="utf-8") != expected:
            mismatches.append(f"content mismatch: {relative_path}")
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    if not args.write and not args.check:
        parser.error("choose --write or --check")

    root = Path(args.root).resolve()
    artifacts = build_artifacts(root)
    if args.write:
        write_artifacts(root, artifacts)
    if args.check:
        mismatches = check_artifacts(root, artifacts)
        if mismatches:
            for mismatch in mismatches:
                print(mismatch, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
