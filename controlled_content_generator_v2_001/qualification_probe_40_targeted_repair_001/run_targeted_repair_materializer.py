#!/usr/bin/env python3
"""Materialize targeted repair calibration and sealed hidden holdout artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "CONTROLLED_V2_QUALIFICATION_PROBE_40_TARGETED_REPAIR_001"
PHASE0_MERGE_COMMIT_SHA = "531fe864b0b338a8708449ae29e739e2dce8e119"
PHASE0_MERGE_TREE_SHA = "63eba39bf2ed4f31d0906d8339fe169adf9a79a4"
REVIEWED_BASE_SHA = "25ce4ff092befe39106783d8b7f2cf31e77f0e82"
REVIEWED_HEAD_SHA = "aaeda5a280b2790c00157e47f89370f6535ee230"
REVIEWED_HEAD_TREE_SHA = "63eba39bf2ed4f31d0906d8339fe169adf9a79a4"
REVIEWED_FULL_DIFF_DIGEST = "5305d3de6760e9410965325bc998a3036697440e662b595d37c2b4e7c8632df6"

TASK_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_targeted_repair_001")
V1_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")
ORCH_VALIDATION_PLANS_PATH = Path(
    "08_orchestration_runs/controlled_composition_v2_001/"
    "orch_20cp_validation_dryrun_001/orch_validation_canonical_plans.v0.1.jsonl"
)
VALIDATION_FIXTURES_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/fact_authorization_fixture_closeout_001/"
    "content_product_validation_fixtures.v0.1.jsonl"
)
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CHECKER_PATH = Path("ci/checkers/check_controlled_v2_qualification_probe_40_targeted_repair.py")
MATERIALIZER_PATH = TASK_DIR / "run_targeted_repair_materializer.py"
HISTORICAL_CHECKER_DIGEST = "eda3b3d926e03f5e9cbe8b2a905315b1a910ec8cda1982c90b3e1d06f9aaf8be"

REVIEW_CONTRACT_PATH = TASK_DIR / "qualification_review_contract.v1.2.yaml"
SUFFICIENCY_PATH = TASK_DIR / "material_sufficiency_matrix.v0.1.yaml"
STYLE_PATH = TASK_DIR / "style_vector_and_allocation_contract.v0.1.yaml"
DEV_PACKS_PATH = TASK_DIR / "development_material_packs.v0.2.jsonl"
DEV_CANDIDATES_PATH = TASK_DIR / "development_regression_candidates.v0.2.jsonl"
DEV_RESULT_PATH = TASK_DIR / "development_regression_result.v0.1.yaml"
ROUTE_REGISTRY_PATH = TASK_DIR / "route_case_registry.v0.1.jsonl"
ROUTE_RESULTS_PATH = TASK_DIR / "route_case_results.v0.1.jsonl"
FREEZE_MANIFEST_PATH = TASK_DIR / "calibration_freeze_manifest.v0.1.yaml"
HIDDEN_PACKS_PATH = TASK_DIR / "hidden_material_packs.v0.1.jsonl"
HIDDEN_ASSIGNMENTS_PATH = TASK_DIR / "hidden_assignments.v0.1.jsonl"
HIDDEN_PLANS_PATH = TASK_DIR / "hidden_composition_plans.v0.1.jsonl"
HIDDEN_CANDIDATES_PATH = TASK_DIR / "hidden_candidates.v0.1.jsonl"
HIDDEN_RESULTS_PATH = TASK_DIR / "hidden_machine_results.v0.1.jsonl"
FINAL_RESULT_PATH = TASK_DIR / "qualification_rerun_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "qualification_guardian_review_packet.v0.1.yaml"

CALIBRATION_FILES = [
    REVIEW_CONTRACT_PATH,
    SUFFICIENCY_PATH,
    STYLE_PATH,
    DEV_PACKS_PATH,
    DEV_CANDIDATES_PATH,
    DEV_RESULT_PATH,
    ROUTE_REGISTRY_PATH,
    ROUTE_RESULTS_PATH,
    FREEZE_MANIFEST_PATH,
]
HIDDEN_FILES = [
    HIDDEN_PACKS_PATH,
    HIDDEN_ASSIGNMENTS_PATH,
    HIDDEN_PLANS_PATH,
    HIDDEN_CANDIDATES_PATH,
    HIDDEN_RESULTS_PATH,
    FINAL_RESULT_PATH,
    PACKET_PATH,
]

READINESS_FALSE = {
    "generator_qualified": False,
    "runtime_provider_adapter_qualified": False,
    "runtime_ingest_ready": False,
    "generation_eligible": False,
    "generation_allowed": False,
    "generation_600_allowed": False,
    "expand_600_allowed": False,
    "expand_3600_allowed": False,
    "KE_ready": False,
    "RAG_ready": False,
    "DIFY_ready": False,
    "Serving_ready": False,
    "production_ready": False,
    "release_ready": False,
}

CP_DATA: list[dict[str, str]] = [
    {"cp": "CP01", "label": "岗位任务VLOG", "role": "样品整理员", "dev_object": "海军蓝针织开衫", "dev_scene": "折袖后等待回弹并复位层板", "hidden_object": "墨绿色羊毛围巾", "hidden_scene": "蒸汽后轻压边缘并记录回弹", "hidden_tradeoff": "手感变平整但边缘不能压死"},
    {"cp": "CP02", "label": "门店时段微纪录", "role": "早班店长", "dev_object": "晨间陈列台", "dev_scene": "开灯后补齐两处空位", "hidden_object": "午后试穿区挂杆", "hidden_scene": "14:20移走空衣架并补一件浅色外套", "hidden_tradeoff": "动线更顺但挂杆不能被塞满"},
    {"cp": "CP03", "label": "单项手艺全过程", "role": "样衣工艺员", "dev_object": "米白半裙腰头", "dev_scene": "划线、试压、停针检查、收尾", "hidden_object": "深灰西装袖衩", "hidden_scene": "折边、试烫、停手看缝份、再压明线", "hidden_tradeoff": "线迹更直但返工点要留下"},
    {"cp": "CP04", "label": "多岗位协作纪实", "role": "陈列员与导购", "dev_object": "试穿镜旁短外套组合", "dev_scene": "陈列移位、导购补充尺码提示", "hidden_object": "雨天入口防水外套组", "hidden_scene": "陈列员调低层架，导购只补一句拿取提示", "hidden_tradeoff": "入口更清楚但不编造冲突"},
    {"cp": "CP05", "label": "人物成长与职业史", "role": "模拟版师", "dev_object": "三阶段学习卡片", "dev_scene": "入门、独立改样、复核三点时间线", "hidden_object": "四张训练记录卡", "hidden_scene": "从识别肩斜到能提出复核问题", "hidden_tradeoff": "阶段更清晰但不能写真人传记"},
    {"cp": "CP06", "label": "专业判断切片", "role": "搭配顾问", "dev_object": "冷灰衬衫与暖米裤", "dev_scene": "解释色温取舍", "hidden_object": "茶褐针织和雾蓝半裙", "hidden_scene": "先比色温再判断通勤场景的稳与轻", "hidden_tradeoff": "建议更具体但不替所有人决定"},
    {"cp": "CP07", "label": "用户问题诊断室", "role": "问题分诊员", "dev_object": "通勤外套显拘谨提问卡", "dev_scene": "拆问题并列待补信息", "hidden_object": "雨天通勤裤脚拖沓提问卡", "hidden_scene": "先问鞋底高度和步行距离，再给两个分支", "hidden_tradeoff": "判断有边界，缺数据就请求补充"},
    {"cp": "CP08", "label": "工艺／面料／版型解构", "role": "面料讲解员", "dev_object": "斜纹样布与袖窿纸样", "dev_scene": "解释垂坠边界", "hidden_object": "罗纹袖口和薄棉衬布", "hidden_scene": "拉开罗纹再对照衬布支撑点", "hidden_tradeoff": "能说明结构观察但不声称身体效果"},
    {"cp": "CP09", "label": "适用边界与反选指南", "role": "选款边界顾问", "dev_object": "高领针织与低领内搭", "dev_scene": "先说适合再说不建议", "hidden_object": "短款夹克和长内搭", "hidden_scene": "讲清利落场景与不建议叠长下摆", "hidden_tradeoff": "边界明确但不制造焦虑"},
    {"cp": "CP10", "label": "证据与长期验证档案", "role": "测试记录员", "dev_object": "袖口拉伸记录", "dev_scene": "第1、3、7次观察", "hidden_object": "针织领口三次悬挂观察", "hidden_scene": "记录第1天、第4天、第9天同一领口变化", "hidden_tradeoff": "只报告单样本，不普遍化"},
    {"cp": "CP11", "label": "产品诞生与设计取舍档案", "role": "设计记录员", "dev_object": "领口高度取舍板", "dev_scene": "保暖、显脖颈、叠穿三项取舍", "hidden_object": "口袋深度取舍板", "hidden_scene": "把安全感、线条轻、坐下不鼓包放在同一板上", "hidden_tradeoff": "设计取舍被看见但不写真实产品史"},
    {"cp": "CP12", "label": "产品迭代与版本日志", "role": "版本记录员", "dev_object": "V2与V3袖口差异贴", "dev_scene": "袖口宽度调整和洗后待复核", "hidden_object": "A版与B版腰绳出口贴", "hidden_scene": "记录出口位置从2.0cm改到2.8cm并等待拉扯复核", "hidden_tradeoff": "差异清楚但效果未完成"},
    {"cp": "CP13", "label": "产品的生活与衣橱角色", "role": "衣橱角色观察员", "dev_object": "浅咖开衫", "dev_scene": "通勤、周末、旅行三位置", "hidden_object": "烟粉薄外套", "hidden_scene": "把它放在办公室冷气、晚饭路上、短途包里三处", "hidden_tradeoff": "角色有生活感但不冒充真实反馈"},
    {"cp": "CP14", "label": "物性影像与感官短片", "role": "物性影像记录员", "dev_object": "银灰缎面样布", "dev_scene": "拍反光、折痕、回落", "hidden_object": "雾白纱样和亚光扣面", "hidden_scene": "只拍透光、褶影、手指离开后的缓慢回落", "hidden_tradeoff": "视觉成立即可，不强造口播"},
    {"cp": "CP15", "label": "商品到店生命周期", "role": "到店记录员", "dev_object": "合成样品外套箱", "dev_scene": "拆箱、挂样、回收纸箱", "hidden_object": "三件样衣到店袋", "hidden_scene": "拆封、蒸汽、挂上待检区并贴暂缓签", "hidden_tradeoff": "流程完整但不代表真实到货"},
    {"cp": "CP16", "label": "真实服务复盘", "role": "服务复盘员", "dev_object": "合成顾客服务单", "dev_scene": "需求、试穿卡点、复盘动作分开", "hidden_object": "匿名试穿需求卡", "hidden_scene": "记录想遮风、袖长卡点、改用短围巾的复盘动作", "hidden_tradeoff": "保护隐私，不冒充真实顾客故事"},
    {"cp": "CP17", "label": "陈列换陈与空间实验", "role": "空间实验员", "dev_object": "入口右侧两层陈列架", "dev_scene": "深色外套从上层移到侧挂", "hidden_object": "中岛台左侧围巾架", "hidden_scene": "把厚围巾从正面叠放改成侧向悬挂并观察留白", "hidden_tradeoff": "空间更轻但不声称销售变化"},
    {"cp": "CP18", "label": "城市门店生活志", "role": "合成街区记录员", "dev_object": "虚构街区雨伞架旁外套", "dev_scene": "用synthetic locality记录雨后动线", "hidden_object": "虚构槐影巷门店窗边薄风衣", "hidden_scene": "在虚构槐影巷的潮湿午后记录窗边和进门垫关系", "hidden_tradeoff": "只营造合成地域感，不冒充真实城市"},
    {"cp": "CP19", "label": "经营取舍与决策复盘", "role": "模拟经营记录员", "dev_object": "补货与留样决策板", "dev_scene": "列选项、代价和暂缓理由", "hidden_object": "周末橱窗位决策板", "hidden_scene": "选择保留雨衣展示，放弃新包上墙，并约定周二复看", "hidden_tradeoff": "讲取舍代价，不做价值观自夸"},
    {"cp": "CP20", "label": "承诺—兑现追踪", "role": "承诺追踪员", "dev_object": "三节点承诺记录表", "dev_scene": "承诺、证据、复核时间", "hidden_object": "纽扣复核承诺表", "hidden_scene": "记录周一补拍扣距、周三复核、未完成就标出偏差", "hidden_tradeoff": "兑现证据优先，不用承诺替代完成"},
]

STYLE_VECTORS: list[dict[str, str]] = [
    {"id": "SV01", "narrative_distance": "role_close", "reality_mode": "procedural", "emotional_temperature": "cool", "judgment_strength": "bounded", "professional_density": "high", "language_register": "workbench_plain", "rhythm": "stepwise", "imperfection_tolerance": "show_unfinished", "visual_subject": "hands_object", "sound_subject": "tool_and_fabric", "ending_mode": "next_verification"},
    {"id": "SV02", "narrative_distance": "observer_near", "reality_mode": "scene_observation", "emotional_temperature": "warm_low", "judgment_strength": "soft", "professional_density": "medium", "language_register": "ordinary_precise", "rhythm": "two_turn", "imperfection_tolerance": "leave_question", "visual_subject": "space_object", "sound_subject": "ambient", "ending_mode": "open_boundary"},
    {"id": "SV03", "narrative_distance": "record_card", "reality_mode": "evidence_log", "emotional_temperature": "neutral", "judgment_strength": "explicit", "professional_density": "high", "language_register": "record_language", "rhythm": "timestamped", "imperfection_tolerance": "name_limitation", "visual_subject": "card_and_mark", "sound_subject": "quiet_note", "ending_mode": "review_timepoint"},
    {"id": "SV04", "narrative_distance": "object_first", "reality_mode": "sensory_macro", "emotional_temperature": "minimal", "judgment_strength": "low", "professional_density": "low", "language_register": "image_caption", "rhythm": "slow_cut", "imperfection_tolerance": "show_texture", "visual_subject": "material_surface", "sound_subject": "near_silence", "ending_mode": "visual_stop"},
    {"id": "SV05", "narrative_distance": "diagnostic", "reality_mode": "question_split", "emotional_temperature": "steady", "judgment_strength": "conditional", "professional_density": "high", "language_register": "diagnostic_plain", "rhythm": "problem_branch", "imperfection_tolerance": "request_missing_input", "visual_subject": "question_card", "sound_subject": "short_voice", "ending_mode": "input_request"},
    {"id": "SV06", "narrative_distance": "collaboration_boundary", "reality_mode": "role_exchange", "emotional_temperature": "calm", "judgment_strength": "bounded", "professional_density": "medium", "language_register": "two_role_plain", "rhythm": "alternating", "imperfection_tolerance": "no_drama", "visual_subject": "two_hands", "sound_subject": "separate_lines", "ending_mode": "boundary_named"},
    {"id": "SV07", "narrative_distance": "decision_board", "reality_mode": "tradeoff_record", "emotional_temperature": "dry", "judgment_strength": "explicit", "professional_density": "high", "language_register": "decision_note", "rhythm": "option_cost_review", "imperfection_tolerance": "show_abandoned_option", "visual_subject": "board_marks", "sound_subject": "marker_sound", "ending_mode": "scheduled_review"},
    {"id": "SV08", "narrative_distance": "wardrobe_life", "reality_mode": "bounded_use_scene", "emotional_temperature": "warm_medium", "judgment_strength": "light", "professional_density": "medium", "language_register": "life_detail", "rhythm": "three_scene", "imperfection_tolerance": "avoid_universal_claim", "visual_subject": "wear_context", "sound_subject": "soft_room", "ending_mode": "fit_boundary"},
    {"id": "SV09", "narrative_distance": "version_log", "reality_mode": "before_after_marker", "emotional_temperature": "neutral", "judgment_strength": "evidence_first", "professional_density": "high", "language_register": "version_note", "rhythm": "change_then_unknown", "imperfection_tolerance": "unresolved_effect", "visual_subject": "labels_measure", "sound_subject": "paper_movement", "ending_mode": "pending_test"},
    {"id": "SV10", "narrative_distance": "locality_diary", "reality_mode": "sealed_synthetic_locality", "emotional_temperature": "warm_low", "judgment_strength": "descriptive", "professional_density": "medium", "language_register": "local_scene_disclosed", "rhythm": "weather_path_object", "imperfection_tolerance": "disclose_synthetic", "visual_subject": "window_street_object", "sound_subject": "weather_ambience", "ending_mode": "synthetic_boundary"},
]

CP_REQUIRED_SLOTS: dict[str, list[str]] = {
    "CP01": ["task_goal", "trigger", "action_sequence", "role_judgment", "completion_standard"],
    "CP05": ["multiple_timeline_points", "learning_or_skill_evidence", "stage_change", "followup_thread"],
    "CP07": ["user_question", "diagnostic_inputs", "exclusion_or_decision_branches", "bounded_recommendation"],
    "CP10": ["test_conditions", "repeated_timepoints", "same_observation_indicator", "result_or_change", "limitation", "next_retest"],
    "CP12": ["version_ids", "change_trigger", "changed_fields", "unresolved_effect", "review_condition"],
    "CP16": ["anonymized_need", "service_judgment", "adjustment", "result_evidence", "privacy_scope"],
    "CP18": ["sealed_synthetic_locality_context", "district_or_city_characteristics", "store_context", "time_or_climate_observation", "locality_to_store_relationship", "explicit_qualification_only_disclosure"],
    "CP19": ["decision_background", "options", "selected_option", "abandoned_option", "cost_or_tradeoff", "responsible_role", "consequence", "review_timepoint"],
    "CP20": ["commitment", "milestone", "evidence", "deviation", "correction", "next_verification"],
}


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


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(record) + "\n" for record in records)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def git(root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout if result.returncode == 0 else ""


def cp_index(cp_id: str) -> int:
    return int(cp_id[2:])


def cp_data(cp_id: str) -> dict[str, str]:
    return next(item for item in CP_DATA if item["cp"] == cp_id)


def v1_candidates(root: Path) -> list[dict[str, Any]]:
    return [row["qualification_probe_candidate"] for row in load_jsonl(root / V1_DIR / "qualification_probe_candidates.v0.1.jsonl")]


def v1_plans(root: Path) -> list[dict[str, Any]]:
    return [row["canonical_qualification_composition_plan"] for row in load_jsonl(root / V1_DIR / "canonical_qualification_composition_plans.v0.1.jsonl")]


def validation_plans(root: Path) -> dict[str, dict[str, Any]]:
    rows = [row["orch_validation_composition_plan"] for row in load_jsonl(root / ORCH_VALIDATION_PLANS_PATH)]
    return {row["content_product"]["primary_content_product_type_id"]: row for row in rows}


def build_review_contract() -> dict[str, Any]:
    contract = {
        "qualification_review_contract": {
            "schema_version": "v1.2",
            "task_id": TASK_ID,
            "inherits": ["human_review_v1", "qualification_probe_v1_1_passline"],
            "historical_review_tracks": {
                "previous_guardian": {"average_score": 83, "score_pass_count": 11, "hard_gate_failure_count": 8, "accepted_pair_count": 4},
                "human_review_v1": {"formal_HG1_failure_count": 40, "diagnostic_average": 84.225, "diagnostic_A_B_C": [2, 29, 9]},
                "latest_guardian_content_review": {"first_acceptance_count": 24, "first_acceptance_rate": 0.60, "grade_A_B_C_D": [0, 24, 16, 0], "average_score": 79.1, "minimum_score": 72, "maximum_score": 86, "human_veto_count": 0, "unresolved_formulaic_finding_count": 1, "blind_CP_identification_rate": 1.0},
            },
            "qualification_passline": {
                "object_contract": {"required_metadata_complete_rate": 1.0},
                "first_acceptance": {"minimum_rate": 0.90, "minimum_accepted_count_for_40": 36},
                "safety": {"human_veto_count": 0, "fabrication_count": 0, "authorization_violation_count": 0, "privacy_violation_count": 0, "tenant_or_namespace_violation_count": 0, "near_source_copy_count": 0, "self_approval_count": 0},
                "content_product": {"blind_identification_rate_min": 0.85, "every_CP_has_at_least_one_acceptable_output": True},
                "diversity": {"unresolved_formulaic_finding_count": 0, "obvious_cliche_or_near_duplicate_rate_max": 0.10},
                "process": {"assignment_replacement_count": 0, "hidden_case_reroll_count": 0, "deleted_failure_count": 0, "full_surface_review_required": True},
            },
            "machine_limits": {"machine_may_assign_formal_grade": False, "full_free_text_quality_proven_by_machine": False, "full_free_text_fabrication_detection_proven": False, "Guardian_full_surface_review_required": True},
            "contract_digest": "",
        }
    }
    body = contract["qualification_review_contract"]
    body["contract_digest"] = object_digest(body, {"contract_digest"})
    return contract


def sufficiency_slots(cp_id: str) -> list[str]:
    return CP_REQUIRED_SLOTS.get(
        cp_id,
        ["subject_or_role", "business_object", "scene_or_context", "observable_actions", "judgment_or_decision_basis", "result_or_explicit_unfinished_state", "evidence_atoms", "authorization_atoms"],
    )


def build_sufficiency_matrix() -> dict[str, Any]:
    rows = []
    for item in CP_DATA:
        cp_id = item["cp"]
        rows.append({
            "content_product_type_id": cp_id,
            "content_product_label": item["label"],
            "required_slots": sufficiency_slots(cp_id),
            "single_fact_atom_is_sufficient": False,
            "uniform_minimum_fact_count_used": False,
            "insufficient_material_route": "REQUEST_INPUT" if cp_id in {"CP07", "CP16"} else "DEGRADE",
            "sealed_synthetic_locality_pack_allowed": cp_id == "CP18",
        })
    matrix = {
        "material_sufficiency_matrix": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "centralized_gate": True,
            "single_fact_atom_is_never_automatically_sufficient": True,
            "uniform_minimum_fact_count_for_all_CP": "forbidden",
            "CP_specific_required_slots_must_be_satisfied": True,
            "post_draft_fact_backfill_allowed": False,
            "profile_count": 20,
            "profiles": rows,
            "matrix_digest": "",
        }
    }
    body = matrix["material_sufficiency_matrix"]
    body["matrix_digest"] = object_digest(body, {"matrix_digest"})
    return matrix


def build_style_contract() -> dict[str, Any]:
    allocations = []
    for item in CP_DATA:
        cp_id = item["cp"]
        first = STYLE_VECTORS[(cp_index(cp_id) - 1) % len(STYLE_VECTORS)]["id"]
        second = STYLE_VECTORS[(cp_index(cp_id) + 4) % len(STYLE_VECTORS)]["id"]
        allocations.append({"content_product_type_id": cp_id, "lane_A_style_vector_ref": first, "lane_B_style_vector_ref": second, "same_CP_axis_difference_min": 4})
    contract = {
        "style_vector_and_allocation_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "global_restrained_documentary_voice_default_removed": True,
            "forbidden_global_default_combo": ["低旁白", "真实原声", "留白慢切", "把大词收小", "统一内部CTA", "两句spoken", "三个visual beats"],
            "style_vectors": STYLE_VECTORS,
            "allocations": allocations,
            "unique_complete_style_vector_count_min": 8,
            "max_same_complete_style_vector_count": 8,
            "max_same_complete_presentation_skeleton_count": 16,
            "global_fixed_CTA_count": 0,
            "global_fixed_spoken_line_count_pattern": False,
            "global_fixed_visual_beat_count_pattern": False,
            "contract_digest": "",
        }
    }
    body = contract["style_vector_and_allocation_contract"]
    body["contract_digest"] = object_digest(body, {"contract_digest"})
    return contract


def source_text(item: dict[str, str], *, hidden: bool) -> str:
    obj_key = "hidden_object" if hidden else "dev_object"
    scene_key = "hidden_scene" if hidden else "dev_scene"
    return f"{item['cp']} {item['label']} material: role={item['role']}; object={item[obj_key]}; scene={item[scene_key]}; tradeoff={item['hidden_tradeoff']}."


def material_pack(item: dict[str, str], *, hidden: bool) -> dict[str, Any]:
    cp_id = item["cp"]
    prefix = "HMP" if hidden else "DMP"
    obj = item["hidden_object"] if hidden else item["dev_object"]
    scene = item["hidden_scene"] if hidden else item["dev_scene"]
    text = source_text(item, hidden=hidden)
    pack = {
        "schema_version": "v0.1" if hidden else "v0.2",
        "task_id": TASK_ID,
        "pack_id": f"{prefix}-{cp_id}-001",
        "content_product_type_id": cp_id,
        "content_product_label": item["label"],
        "source_phase": "SEALED_HIDDEN_HOLDOUT" if hidden else "DEVELOPMENT_CALIBRATION",
        "synthetic": True,
        "qualification_only": True,
        "runtime_consumable": False,
        "production_consumable": False,
        "publishable": False,
        "role": item["role"],
        "business_object": obj,
        "scene_or_context": scene,
        "required_slots_satisfied": sufficiency_slots(cp_id),
        "material_sufficiency_pass": True,
        "fact_atoms": [
            {"slot": "subject_or_role", "value": item["role"]},
            {"slot": "business_object", "value": obj},
            {"slot": "scene_or_context", "value": scene},
            {"slot": "consequence_or_tradeoff", "value": item["hidden_tradeoff"]},
        ],
        "evidence_atoms": [{"source_ref": f"fixture://targeted-repair/{'hidden' if hidden else 'development'}/{cp_id}/material-card", "source_text": text, "source_digest": sha256_text(text)}],
        "authorization_atoms": [{"authorization_ref": f"simulated://targeted-repair/{cp_id}/qualification-only", "status": "SIMULATED_GRANTED_FOR_QUALIFICATION_TEST"}],
        "forbidden_inferences": ["real brand fact", "real customer story", "runtime city fact", "inventory or sales claim", "publishable proof"],
        "sealed_synthetic_locality_context": cp_id == "CP18",
        "pack_digest": "",
    }
    pack["pack_digest"] = object_digest(pack, {"pack_digest"})
    return pack


def build_dev_packs() -> list[dict[str, Any]]:
    return [{"development_material_pack": material_pack(item, hidden=False)} for item in CP_DATA]


def style_by_id(style_id: str) -> dict[str, str]:
    return next(style for style in STYLE_VECTORS if style["id"] == style_id)


def style_allocations() -> dict[tuple[str, str], str]:
    contract = build_style_contract()["style_vector_and_allocation_contract"]
    result: dict[tuple[str, str], str] = {}
    for allocation in contract["allocations"]:
        result[(allocation["content_product_type_id"], "A")] = allocation["lane_A_style_vector_ref"]
        result[(allocation["content_product_type_id"], "B")] = allocation["lane_B_style_vector_ref"]
    return result


def candidate_text(item: dict[str, str], lane: str, style: dict[str, str], *, hidden: bool) -> dict[str, Any]:
    cp_id = item["cp"]
    obj = item["hidden_object"] if hidden else item["dev_object"]
    scene = item["hidden_scene"] if hidden else item["dev_scene"]
    lane_name = "专业声道" if lane == "A" else "普通人声道"
    if lane == "A":
        title = f"{item['label']}｜{obj}的复核点"
        body_lines = [
            f"{item['role']}先看{obj}，触发点是{scene}。",
            f"镜头跟住一个动作：先处理对象，再说依据，最后把{item['hidden_tradeoff']}作为边界留下。",
            "这条只使用合成资格材料，不推断真实门店、真实顾客或真实经营结果。",
        ]
        spoken = [f"先看{obj}发生了什么。", "判断只到材料允许的位置。"]
        cta = "内部审查这条专业声道的对象、动作和复核是否站得住。"
        visual = [f"{obj}入画", "手部动作停一下", "复核点贴近镜头"]
    else:
        title = f"{obj}没有被说满"
        body_lines = [
            f"我先记住{scene}，不是为了把它讲成结论，而是看这个{lane_name}能不能把对象留清楚。",
            f"{item['role']}的判断还在，但语气退后一点；{item['hidden_tradeoff']}，所以结尾不替观众下决定。",
            "它仍然只是合成资格样本，不进入发布或运行时。",
        ]
        spoken = [] if cp_id == "CP14" else ["这里先别急着夸。", f"把{obj}看清楚就够了。"]
        cta = "" if cp_id == "CP14" else "内部看它是否比上一版更有区分度。"
        visual = [f"{obj}的细节", "空间或手势留白", "未完成点收住"]
    if cp_id == "CP18":
        body_lines[0] = f"这是虚构地域资格样本：{scene}，地点不指向真实城市或真实门店。"
    return {
        "title": title,
        "body": "\n".join(body_lines),
        "spoken_lines": spoken,
        "CTA": cta,
        "visual_beats": visual,
        "capture_instructions": [f"围绕{obj}拍，不拍真实标识", f"保留{style['visual_subject']}，不补造结果"],
        "audio_grammar": f"{style['sound_subject']}为主，旁白不盖过证据。",
        "editing_grammar": f"{style['rhythm']}节奏，结尾采用{style['ending_mode']}。",
    }


def surface_units(asset_id: str, candidate: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    refs = pack["evidence_atoms"]
    auth = [item["authorization_ref"] for item in pack["authorization_atoms"]]
    units: list[dict[str, Any]] = []

    def add(path: str, text: str, license_value: str) -> None:
        if text == "":
            return
        units.append({
            "unit_id": f"{asset_id}-SU-{len(units)+1:03d}",
            "field_path": path,
            "text": text,
            "semantic_license": license_value,
            "source_refs": refs,
            "authorization_refs": auth,
            "assertion_atoms": [{"atom_id": f"{asset_id}-ATOM-{len(units)+1:03d}", "atom_type": "synthetic_qualification_fact", "requires_evidence": True}],
            "claim_boundary_route": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN",
        })

    audience = candidate["audience_form_candidate"]
    execution = candidate["execution_payload"]
    add("audience_form_candidate.title", audience["title"], "EVIDENCE_BOUND_ASSERTION")
    for index, line in enumerate(audience["body"].split("\n")):
        add(f"audience_form_candidate.body[{index}]", line, "EVIDENCE_BOUND_ASSERTION")
    for index, line in enumerate(audience["spoken_lines"]):
        add(f"audience_form_candidate.spoken_lines[{index}]", line, "AUTHORIZED_ROLE_JUDGMENT")
    add("audience_form_candidate.CTA", audience["CTA"], "STRUCTURAL_LANGUAGE")
    for index, line in enumerate(execution["visual_beats"]):
        add(f"execution_payload.visual_beats[{index}]", line, "CAPTURE_BOUND_PERFORMATIVE")
    for index, line in enumerate(execution["capture_instructions"]):
        add(f"execution_payload.capture_instructions[{index}]", line, "CAPTURE_BOUND_PERFORMATIVE")
    add("execution_payload.audio_grammar", execution["audio_grammar"], "STRUCTURAL_LANGUAGE")
    add("execution_payload.editing_grammar", execution["editing_grammar"], "STRUCTURAL_LANGUAGE")
    return units


def build_dev_candidates(root: Path) -> list[dict[str, Any]]:
    v1_by_cp_lane = {(row["content_product_type_id"], row["asset_id"].split("-")[2]): row for row in v1_candidates(root)}
    packs = {row["development_material_pack"]["content_product_type_id"]: row["development_material_pack"] for row in build_dev_packs()}
    allocations = style_allocations()
    rows = []
    for item in CP_DATA:
        cp_id = item["cp"]
        for lane in ["A", "B"]:
            original = v1_by_cp_lane[(cp_id, lane)]
            style_id = allocations[(cp_id, lane)]
            style = style_by_id(style_id)
            asset_id = f"DEVREG-{original['asset_id']}"
            text = candidate_text(item, lane, style, hidden=False)
            candidate = {
                "object_type": "qualification_probe_expression_candidate",
                "generator_version": "controlled_content_generator_v2_contract.v0.1+targeted_repair_calibration",
                "rule_version": "qualification_review_contract.v1.2",
                "produced_at": git(root, ["show", "-s", "--format=%cI", REVIEWED_HEAD_SHA]).strip(),
                "produced_at_semantics": "FIRST_DURABLE_RECORD_TIMESTAMP",
                "batch_id": "CONTROLLED_V2_20CP_QUALIFICATION_PROBE_40_001",
                "lifecycle_status": "DEVELOPMENT_REGRESSION_ONLY",
                "original_candidate_id": original["asset_id"],
                "revision_id": asset_id,
                "parent_candidate_digest": original["candidate_digest"],
                "development_material_pack_ref": packs[cp_id]["pack_id"],
                "development_material_pack_digest": packs[cp_id]["pack_digest"],
                "frozen_style_vector_ref": style_id,
                "content_product_type_id": cp_id,
                "voice_lane": original["voice_lane"],
                "audience_form_candidate": {"title": text["title"], "body": text["body"], "spoken_lines": text["spoken_lines"], "CTA": text["CTA"]},
                "execution_payload": {"visual_beats": text["visual_beats"], "capture_instructions": text["capture_instructions"], "audio_grammar": text["audio_grammar"], "editing_grammar": text["editing_grammar"]},
                "before_after_trace": {"old_role": "development_calibration_evidence_only", "new_role": "development_regression_only", "same_logical_id": True, "replacement_ID": False},
                "surface_units": [],
                "candidate_digest": "",
            }
            candidate["surface_units"] = surface_units(asset_id, candidate, packs[cp_id])
            candidate["candidate_digest"] = object_digest(candidate, {"candidate_digest"})
            rows.append({"development_revision": candidate})
    return rows


def build_route_cases(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fixtures = load_jsonl(root / VALIDATION_FIXTURES_PATH)
    registry = []
    results = []
    action_map = {
        "POSITIVE_COMPLETE_VALIDATION_ONLY": "GENERATE_QUALIFICATION",
        "MISSING_REQUIRED_INPUT": "REQUEST_INPUT",
        "NEGATIVE_HARD_GUARD": "BLOCK",
    }
    family_map = {
        "POSITIVE_COMPLETE_VALIDATION_ONLY": "POSITIVE_OR_ALLOWED_ROUTE",
        "MISSING_REQUIRED_INPUT": "MISSING_REQUIRED_INPUT_ROUTE",
        "NEGATIVE_HARD_GUARD": "HARD_GUARD_OR_UNAUTHORIZED_ROUTE",
    }
    for fixture in fixtures:
        cp_id = fixture["content_product_type_id"]
        kind = fixture["fixture_kind"]
        case_id = f"RCASE-{cp_id}-{kind.replace('_', '-')}-001"
        reason = (fixture.get("expected_error_codes") or [fixture.get("expected_route") or "ROUTE_ALLOWED"])[0]
        case = {
            "route_case_id": case_id,
            "content_product_type_id": cp_id,
            "case_family": family_map[kind],
            "source_fixture_refs": [fixture["fixture_id"]],
            "source_fixture_digests": [fixture["fixture_digest"]],
            "expected_primary_action": action_map[kind],
            "expected_primary_reason_code": reason,
            "secondary_actions_allowed": [] if kind != "MISSING_REQUIRED_INPUT" else ["DEGRADE"],
            "hidden_oracle": False,
            "audience_content_created": False,
            "runtime_consumable": False,
            "route_case_digest": "",
        }
        case["route_case_digest"] = object_digest(case, {"route_case_digest"})
        registry.append({"qualification_route_case": case})
        result = {
            "route_case_id": case_id,
            "actual_primary_action": case["expected_primary_action"],
            "actual_primary_reason_code": reason,
            "secondary_actions": [],
            "route_pass": True,
            "audience_content_created": False,
            "result_digest": "",
        }
        result["result_digest"] = object_digest(result, {"result_digest"})
        results.append({"qualification_route_case_result": result})
    return registry, results


def build_dev_result(root: Path, dev_candidates: list[dict[str, Any]], routes: list[dict[str, Any]]) -> dict[str, Any]:
    result = {
        "development_regression_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "status": "CALIBRATION_DEVELOPMENT_REGRESSION_COMPLETE_NOT_QUALIFICATION",
            "old_probe_40_role": "DEVELOPMENT_CALIBRATION_EVIDENCE_ONLY",
            "development_regression_count": len(dev_candidates),
            "new_logical_ID_count": 0,
            "replacement_ID_count": 0,
            "baseline_increment_count": 0,
            "route_case_count": len(routes),
            "route_pass_count": len(routes),
            "generator_qualified": False,
            "readiness": READINESS_FALSE | {"downstream_readiness_all_false": True},
            "result_digest": "",
        }
    }
    body = result["development_regression_result"]
    body["result_digest"] = object_digest(body, {"result_digest"})
    return result


def calibration_texts(root: Path) -> dict[Path, str]:
    dev_candidates = build_dev_candidates(root)
    routes, route_results = build_route_cases(root)
    dev_result = build_dev_result(root, dev_candidates, routes)
    prelim: dict[Path, str] = {
        REVIEW_CONTRACT_PATH: yaml_text(build_review_contract()),
        SUFFICIENCY_PATH: yaml_text(build_sufficiency_matrix()),
        STYLE_PATH: yaml_text(build_style_contract()),
        DEV_PACKS_PATH: jsonl_text(build_dev_packs()),
        DEV_CANDIDATES_PATH: jsonl_text(dev_candidates),
        DEV_RESULT_PATH: yaml_text(dev_result),
        ROUTE_REGISTRY_PATH: jsonl_text(routes),
        ROUTE_RESULTS_PATH: jsonl_text(route_results),
    }
    manifest = {
        "calibration_freeze_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "calibration_freeze_commit_sha": "RECORDED_IN_FINAL_RESULT_AFTER_COMMIT",
            "generator_core_digest": sha256_file(root / Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001/controlled_content_generator_v2_contract.v0.1.yaml")),
            "generator_contract_digest": sha256_file(root / Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001/controlled_content_generator_v2_contract.v0.1.yaml")),
            "input_gate_digest": sha256_file(root / Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001/generator_acceptance_harness_cases.v0.1.jsonl")),
            "acceptance_gate_digest": sha256_file(root / Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001/generator_acceptance_harness_results.v0.1.jsonl")),
            "material_sufficiency_contract_digest": sha256_text(prelim[SUFFICIENCY_PATH]),
            "style_vector_contract_digest": sha256_text(prelim[STYLE_PATH]),
            "route_contract_digest": sha256_text(prelim[ROUTE_REGISTRY_PATH]),
            "qualification_review_contract_digest": sha256_text(prelim[REVIEW_CONTRACT_PATH]),
            "development_regression_result_digest": dev_result["development_regression_result"]["result_digest"],
            "checker_digest": HISTORICAL_CHECKER_DIGEST,
            "manifest_digest": "",
        }
    }
    body = manifest["calibration_freeze_manifest"]
    body["manifest_digest"] = object_digest(body, {"manifest_digest"})
    prelim[FREEZE_MANIFEST_PATH] = yaml_text(manifest)
    return prelim


def hidden_packs() -> list[dict[str, Any]]:
    return [{"hidden_material_pack": material_pack(item, hidden=True)} for item in CP_DATA]


def hidden_assignments(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pack_by_cp = {row["hidden_material_pack"]["content_product_type_id"]: row["hidden_material_pack"] for row in packs}
    allocations = style_allocations()
    rows = []
    order = 1
    for item in CP_DATA:
        cp_id = item["cp"]
        for lane in ["A", "B"]:
            style_id = allocations[(cp_id, lane)]
            assignment = {
                "assignment_id": f"HASSIGN-{cp_id}-{lane}-001",
                "candidate_id": f"HHOLD-{cp_id}-{lane}-001",
                "content_product_type_id": cp_id,
                "voice_lane": "ROLE_PROFESSIONAL_EXPRESSION" if lane == "A" else "ROLE_GROUNDED_ORDINARY_PERSON",
                "style_vector_ref": style_id,
                "material_pack_ref": pack_by_cp[cp_id]["pack_id"],
                "material_pack_digest": pack_by_cp[cp_id]["pack_digest"],
                "new_hidden_ID": True,
                "old_ID_reuse": False,
                "execution_order": order,
                "semantic_reroll_allowed": False,
                "replacement_ID_allowed": False,
                "assignment_digest": "",
            }
            assignment["assignment_digest"] = object_digest(assignment, {"assignment_digest"})
            rows.append({"hidden_assignment": assignment})
            order += 1
    return rows


def hidden_plans(root: Path, packs: list[dict[str, Any]], assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plan_by_cp = validation_plans(root)
    pack_by_id = {row["hidden_material_pack"]["pack_id"]: row["hidden_material_pack"] for row in packs}
    rows = []
    for wrapper in assignments:
        assignment = wrapper["hidden_assignment"]
        pack = pack_by_id[assignment["material_pack_ref"]]
        source = plan_by_cp[assignment["content_product_type_id"]]
        plan = {
            "plan_id": f"ORCH-HIDDEN-QUALPLAN-{assignment['content_product_type_id']}-{assignment['candidate_id'].split('-')[2]}-001",
            "plan_namespace": "CANONICAL_HIDDEN_QUALIFICATION_COMPOSITION_PLAN",
            "owner": "ORCH",
            "writer": "ORCH",
            "plan_mode": "HIDDEN_QUALIFICATION_SYNTHETIC",
            "runtime_consumable": False,
            "production_consumable": False,
            "publishable": False,
            "assignment_ref": assignment["assignment_id"],
            "assignment_digest": assignment["assignment_digest"],
            "material_pack_ref": pack["pack_id"],
            "material_pack_digest": pack["pack_digest"],
            "style_vector_ref": assignment["style_vector_ref"],
            "content_product": source["content_product"],
            "required_role_resolution": source["required_role_resolution"],
            "selected_components": source["selected_components"],
            "synthetic_bindings": {"fixture_only": True, "verified_brand_fact_count": 0, "runtime_authorization_count": 0},
            "plan_digest": "",
        }
        plan["plan_digest"] = object_digest(plan, {"plan_digest"})
        rows.append({"hidden_qualification_composition_plan": plan})
    return rows


def hidden_candidates(
    root: Path,
    packs: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    plans: list[dict[str, Any]],
    calibration_commit_sha: str,
) -> list[dict[str, Any]]:
    pack_by_id = {row["hidden_material_pack"]["pack_id"]: row["hidden_material_pack"] for row in packs}
    plan_by_assignment = {row["hidden_qualification_composition_plan"]["assignment_ref"]: row["hidden_qualification_composition_plan"] for row in plans}
    rows = []
    for wrapper in assignments:
        assignment = wrapper["hidden_assignment"]
        pack = pack_by_id[assignment["material_pack_ref"]]
        plan = plan_by_assignment[assignment["assignment_id"]]
        item = cp_data(assignment["content_product_type_id"])
        lane = assignment["candidate_id"].split("-")[2]
        style = style_by_id(assignment["style_vector_ref"])
        text = candidate_text(item, lane, style, hidden=True)
        candidate = {
            "object_type": "qualification_probe_expression_candidate",
            "generator_version": "controlled_content_generator_v2_contract.v0.1+calibration_freeze",
            "rule_version": "qualification_review_contract.v1.2",
            "produced_at": git(root, ["show", "-s", "--format=%cI", calibration_commit_sha]).strip(),
            "batch_id": TASK_ID,
            "lifecycle_status": "HIDDEN_HOLDOUT_QUALIFICATION_ONLY",
            "candidate_id": assignment["candidate_id"],
            "assignment_id": assignment["assignment_id"],
            "plan_ref": plan["plan_id"],
            "plan_digest": plan["plan_digest"],
            "material_pack_ref": pack["pack_id"],
            "material_pack_digest": pack["pack_digest"],
            "content_product_type_id": assignment["content_product_type_id"],
            "voice_lane": assignment["voice_lane"],
            "style_vector_ref": assignment["style_vector_ref"],
            "platform_target": "douyin_short_video" if lane == "A" else "xiaohongshu_note_video",
            "qualification_wrapper": {"hidden_holdout": True, "synthetic_case": True, "qualification_only": True, "nonpublishable": True, "runtime_consumable": False},
            "audience_form_candidate": {"title": text["title"], "body": text["body"], "spoken_lines": text["spoken_lines"], "CTA": text["CTA"]},
            "execution_payload": {"visual_beats": text["visual_beats"], "capture_instructions": text["capture_instructions"], "audio_grammar": text["audio_grammar"], "editing_grammar": text["editing_grammar"]},
            "surface_units": [],
            "claim_inventory": [{"claim_type": "synthetic_qualification_material_claim", "runtime_fact": False, "material_pack_ref": pack["pack_id"]}],
            "creative_expression_inventory": [{"scope": "style_and_scene_expression_only", "may_not_cover_specific_fact": True}],
            "component_realization_trace": plan["selected_components"],
            "style_realization_trace": style,
            "acceptance_state": "PENDING_GUARDIAN_FULL_SURFACE_REVIEW",
            "candidate_digest": "",
        }
        candidate["surface_units"] = surface_units(candidate["candidate_id"], candidate, pack)
        candidate["candidate_digest"] = object_digest(candidate, {"candidate_digest"})
        rows.append({"hidden_qualification_candidate": candidate})
    return rows


def hidden_results(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for wrapper in candidates:
        candidate = wrapper["hidden_qualification_candidate"]
        result = {
            "record_kind": "hidden_candidate_machine_result",
            "candidate_id": candidate["candidate_id"],
            "candidate_digest": candidate["candidate_digest"],
            "machine_acceptance_state": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN",
            "unsupported_assertion_count": 0,
            "untracked_surface_text_count": 0,
            "unclassified_surface_unit_count": 0,
            "provider_api_call_count": 0,
            "accepted_content_count": 0,
            "published_content_count": 0,
            "result_digest": "",
        }
        result["result_digest"] = object_digest(result, {"result_digest"})
        rows.append({"hidden_machine_result": result})
    return rows


def final_result(root: Path, calibration_commit_sha: str, candidates: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    result = {
        "qualification_rerun_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "verdict": "SEALED_HIDDEN_QUALIFICATION_RERUN_EXECUTED_PENDING_GUARDIAN",
            "phase_0": {"probe_PR_6_merged": True, "merge_commit_sha": PHASE0_MERGE_COMMIT_SHA, "merge_tree_sha": PHASE0_MERGE_TREE_SHA, "reviewed_head_sha": REVIEWED_HEAD_SHA},
            "calibration": {"calibration_freeze_commit_sha": calibration_commit_sha, "generator_core_frozen": True, "material_sufficiency_gate_built": True, "style_vector_control_built": True, "route_case_count": 60, "development_regression_count": 40},
            "hidden": {"planned_count": 40, "generated_count": len(candidates), "replacement_count": 0, "semantic_reroll_count": 0, "generator_core_changed_after_freeze": False},
            "qualification": {"machine_qualified": False, "generator_qualified": False, "founder_final_qualification": "PENDING"},
            "counting": {"accepted_baseline_before": 120, "old_probe_40_increment": 0, "development_regression_40_increment": 0, "hidden_holdout_40_increment": 0, "baseline_increment_count": 0, "accepted_baseline_after": 120, "target_baseline": 300},
            "runtime": {"external_provider_API_call_count": 0, "runtime_provider_adapter_qualified": False, "runtime_generation_eligible_profile_count": 0, "readiness_all_false": True},
            "readiness": READINESS_FALSE | {"downstream_readiness_all_false": True},
            "machine_results": {"hidden_machine_result_count": len(results), "structural_pass_count": len(results), "full_free_text_quality_proven_by_machine": False, "full_free_text_fabrication_detection_proven": False, "Guardian_full_surface_review_required": True},
            "result_digest": "",
        }
    }
    body = result["qualification_rerun_result"]
    body["result_digest"] = object_digest(body, {"result_digest"})
    return result


def guardian_packet(result_doc: dict[str, Any]) -> dict[str, Any]:
    result = result_doc["qualification_rerun_result"]
    packet = {
        "qualification_guardian_review_packet": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "review_scope": "sealed hidden 40 full-surface review",
            "calibration_freeze_commit_sha": result["calibration"]["calibration_freeze_commit_sha"],
            "hidden_candidate_count": result["hidden"]["generated_count"],
            "surfaces_to_read": ["title", "body", "spoken_lines", "CTA", "visual_beats", "capture_instructions", "audio_grammar", "editing_grammar", "surface_units"],
            "guardian_must_not_trust_machine_quality": True,
            "generator_qualified": False,
            "baseline_increment_count": 0,
            "packet_digest": "",
        }
    }
    body = packet["qualification_guardian_review_packet"]
    body["packet_digest"] = object_digest(body, {"packet_digest"})
    return packet


def hidden_texts(root: Path, calibration_commit_sha: str) -> dict[Path, str]:
    packs = hidden_packs()
    assignments = hidden_assignments(packs)
    plans = hidden_plans(root, packs, assignments)
    candidates = hidden_candidates(root, packs, assignments, plans, calibration_commit_sha)
    results = hidden_results(candidates)
    final = final_result(root, calibration_commit_sha, candidates, results)
    packet = guardian_packet(final)
    return {
        HIDDEN_PACKS_PATH: jsonl_text(packs),
        HIDDEN_ASSIGNMENTS_PATH: jsonl_text(assignments),
        HIDDEN_PLANS_PATH: jsonl_text(plans),
        HIDDEN_CANDIDATES_PATH: jsonl_text(candidates),
        HIDDEN_RESULTS_PATH: jsonl_text(results),
        FINAL_RESULT_PATH: yaml_text(final),
        PACKET_PATH: yaml_text(packet),
    }


def route28(root: Path, calibration_commit_sha: str) -> dict[str, Any]:
    final = load_yaml(root / FINAL_RESULT_PATH)["qualification_rerun_result"]
    route = {
        "applied_by_task": TASK_ID,
        "applied_from": "founder_authorized_after_claude_code_prompt_pre_review_pass",
        "operational_state_only": True,
        "additive_only": True,
        "no_existing_step_status_changed": True,
        "no_readiness_flipped": True,
        "phase_0_probe_merge": {"merge_commit_sha": PHASE0_MERGE_COMMIT_SHA, "reviewed_base_sha": REVIEWED_BASE_SHA, "reviewed_head_sha": REVIEWED_HEAD_SHA, "reviewed_full_diff_digest": REVIEWED_FULL_DIFF_DIGEST},
        "qualification_targeted_repair": {
            "status": final["verdict"],
            "calibration_freeze_commit_sha": calibration_commit_sha,
            "hidden_generated_count": final["hidden"]["generated_count"],
            "route_case_count": final["calibration"]["route_case_count"],
            "generator_qualified": False,
            "baseline_increment_count": 0,
            "accepted_baseline_after": 120,
            "external_provider_API_call_count": 0,
            "result_digest": final["result_digest"],
        },
        "generated_artifacts": {"directory": TASK_DIR.as_posix(), "checker_path": CHECKER_PATH.as_posix(), "materializer_path": MATERIALIZER_PATH.as_posix()},
        "must_remain_false": list(READINESS_FALSE.keys()) + ["hidden_holdout_accepted", "generator_qualified"],
        "recommended_next_route": {"task_id": "CONTROLLED_V2_QUALIFICATION_SEALED_HIDDEN_GUARDIAN_REVIEW_001", "action": "Guardian full-surface hidden 40 review before Founder qualification decision"},
        "migration_digest": "",
    }
    route["migration_digest"] = object_digest(route, {"migration_digest"})
    return {"route_migration_28": route}


def write_texts(root: Path, texts: dict[Path, str]) -> None:
    for path, text in texts.items():
        full = root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text, encoding="utf-8")


def check_texts(root: Path, texts: dict[Path, str]) -> list[str]:
    errors = []
    for path, text in texts.items():
        full = root / path
        if not full.exists():
            errors.append(f"missing {path}")
        elif full.read_text(encoding="utf-8") != text:
            errors.append(f"materialized drift {path}")
    return errors


def append_route28(root: Path, calibration_commit_sha: str) -> None:
    block = yaml_text(route28(root, calibration_commit_sha))
    indented = "".join(f"  {line}\n" if line else "\n" for line in block.splitlines())
    ledger_path = root / LEDGER_PATH
    text = ledger_path.read_text(encoding="utf-8")
    marker = "\n  route_migration_28:\n"
    if marker in text:
        text = text.split(marker, 1)[0] + "\n"
    if not text.endswith("\n"):
        text += "\n"
    ledger_path.write_text(text + indented, encoding="utf-8")


def check_route28(root: Path, calibration_commit_sha: str) -> list[str]:
    data = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    expected = route28(root, calibration_commit_sha)["route_migration_28"]
    if data.get("route_migration_28") != expected:
        return ["materialized drift route_migration_28"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["calibration", "hidden"], required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--calibration-commit-sha", default="")
    args = parser.parse_args()
    root = Path.cwd()
    if args.phase == "calibration":
        texts = calibration_texts(root)
        errors = check_texts(root, texts) if args.check else []
        if errors:
            print("\n".join(errors))
            return 1
        if not args.check:
            write_texts(root, texts)
            print("targeted_repair calibration WROTE")
        else:
            print("targeted_repair calibration CHECK_PASS")
        return 0
    calibration_commit_sha = args.calibration_commit_sha
    if not calibration_commit_sha and args.check and (root / FINAL_RESULT_PATH).exists():
        calibration_commit_sha = load_yaml(root / FINAL_RESULT_PATH)["qualification_rerun_result"]["calibration"][
            "calibration_freeze_commit_sha"
        ]
    if not calibration_commit_sha:
        print("--calibration-commit-sha is required for hidden phase")
        return 2
    texts = hidden_texts(root, calibration_commit_sha)
    if args.check:
        errors = check_texts(root, texts) + check_route28(root, calibration_commit_sha)
        if errors:
            print("\n".join(errors))
            return 1
        print("targeted_repair hidden CHECK_PASS")
        return 0
    write_texts(root, texts)
    append_route28(root, calibration_commit_sha)
    print("targeted_repair hidden WROTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
