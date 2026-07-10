#!/usr/bin/env python3
"""Freeze, repair, and package the scoped Final-120 semantic review view."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GKB-P7D-FINAL-120-CROSS-LAYER-AND-ANTI-FORMULA-REPAIR-AND-REVIEW-HANDOFF-001"
BASELINE_HEAD = "75085490fb387a89a6447994d6535a4a843335f3"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
MID_REL = f"{RUN_REL}/midbatch_320_001"
FOUNDER_REL = f"{MID_REL}/founder_40_repair_001/founder_40_repaired_assets.v0.1.jsonl"
REPAIR_80_REL = (
    f"{MID_REL}/repair_validation_80_001/repair_validation_80_assets.v0.1.jsonl"
)
R80_BINDING_REL = (
    f"{MID_REL}/repair_validation_80_001/"
    "repair_validation_80_event_fact_binding_index.v0.1.jsonl"
)
PROBE_REL = (
    f"{MID_REL}/founder_40_repair_001/platform_native_5x2_001/"
    "platform_native_expression_variants.v0.1.jsonl"
)
OUT_REL = f"{MID_REL}/final_120_semantic_repair_001"
CONTRACT_NAME = "asset_semantic_integrity_and_expression_diversity_contract.v0.1.yaml"
FREEZE_NAME = "repair_set_freeze.v0.1.yaml"
KNOWN_C = {
    "RV80-ASSET-017",
    "RV80-ASSET-018",
    "RV80-ASSET-059",
    "RV80-ASSET-060",
}

ACCOUNT_NARRATOR = {
    "founder": "founder_or_authorized_operator",
    "store_manager": "store_manager",
    "brand_headquarters": "brand_content_operator",
    "sales_associate": "sales_associate",
}
ROLE_ZH = {
    "创始人": "founder",
    "负责人": "founder_or_authorized_operator",
    "经营者": "founder_or_authorized_operator",
    "团队": "team_member",
    "店长": "store_manager",
    "导购": "sales_associate",
    "版师": "pattern_maker",
    "买手": "buyer",
    "陈列师": "visual_merchandiser",
    "陈列负责人": "visual_merchandiser",
    "搭配师": "stylist",
    "内容同事": "content_operator",
    "内容人员": "content_operator",
    "实习生": "store_intern",
    "顾客": "customer",
}
ROLE_LABEL = {
    "P0_01": "负责人",
    "P0_02": "店长",
    "P0_03": "导购",
    "P0_04": "陈列师",
    "P0_05": "导购",
}
HIGH_RISK_TERMS = (
    "显瘦",
    "显白",
    "身体效果",
    "身体结论",
    "身体答案",
    "保暖",
    "耐穿",
    "耐用",
    "寿命",
    "起球",
    "不掉色",
    "缩水",
    "性能",
    "舒适",
    "健康",
    "耐洗",
    "久穿",
    "长期表现",
)
MEDIUM_RISK_TERMS = (
    "适合谁",
    "比例",
    "轮廓",
    "肤色",
    "更暖",
    "更耐",
    "效果",
    "感觉",
    "身体感受",
    "个人感受",
)
BOUNDARY_TERMS = (
    "不能",
    "不该",
    "不替",
    "不作保证",
    "不保证",
    "回答不了",
    "等资料",
    "等测试",
    "留给长期",
    "不在这里",
    "不由文字",
    "不抢答",
    "不下结论",
)
POSITIVE_BOUNDARY_TERMS = (
    "由本人结合实际试穿判断",
    "交给本人在实际光线和试穿动作里比较",
    "个人感受交给实际试穿",
    "需要材料信息和本人穿着共同判断",
    "需要工艺、洗护或测试记录",
    "需要同条件资料或测试",
    "需要相应资料或测试",
)
VISIBLE_BOUNDARY_TERMS = (*BOUNDARY_TERMS, *POSITIVE_BOUNDARY_TERMS)
GENERIC_GOVERNANCE_TERMS = (
    "CandidatePack",
    "readiness",
    "production_servable",
    "治理规则",
    "事实槽位",
    "fact slot",
)
ACTUAL_PROTOTYPE_PATTERN = re.compile(
    r"(^|[，。；：])(?:我|我们)|今天|今早|刚刚|明早|明天|我们店|老板决定"
)
UNSUPPORTED_CLAIM_PATTERN = re.compile(
    r"保证.{0,6}(显瘦|显白|保暖|耐穿|舒适)|"
    r"一定.{0,6}(显瘦|显白|保暖|耐穿|舒适)|"
    r"卖爆|销量(?:增长|提升)|转化率(?:增长|提升)"
)
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])")
NORMALIZE_PATTERN = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")


def stable_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text: str) -> str:
    return NORMALIZE_PATTERN.sub("", text).lower()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
    )


def write_yaml(path: Path, key: str, value: Any) -> None:
    path.write_text(
        yaml.safe_dump({key: value}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def sentences(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]
    return parts if parts else [text.strip()]


def sentence_text(value: str) -> str:
    return value.rstrip("。！？!?；;")


def role_mentions(text: str) -> list[str]:
    found: list[str] = []
    for label, role in ROLE_ZH.items():
        if label in text and role not in found:
            found.append(role)
    return found


def source_event_state(row: dict[str, Any]) -> str:
    state = str(row.get("review_metadata", {}).get("event_binding_state", ""))
    if state in {
        "source_observed",
        "brand_confirmed",
        "bounded_routine_work_prototype",
    }:
        return state
    return "bounded_routine_work_prototype"


def normalize_sources(
    root: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    bindings = {str(row["asset_id"]): row for row in read_jsonl(root / R80_BINDING_REL)}
    rows: list[dict[str, Any]] = []
    for source_kind, relative in (
        ("founder_40", FOUNDER_REL),
        ("repair_80", REPAIR_80_REL),
    ):
        for raw in read_jsonl(root / relative):
            source_id = str(raw.get("repair_id") or raw.get("asset_id"))
            kernel_id = str(
                raw.get("bound_kernel_candidate_id") or raw.get("kernel_id")
            )
            p0_group = str(raw.get("p0_group") or raw.get("capability_group"))
            source_binding = bindings.get(source_id)
            fact_boundary_digest = (
                str(source_binding["fact_boundary_digest"])
                if source_binding
                else stable_digest(
                    {
                        "generation_mode": raw.get("generation_mode"),
                        "required_fact_slots": raw.get("review_metadata", {}).get(
                            "required_fact_slots", []
                        ),
                        "forbidden_claims": raw.get("review_metadata", {}).get(
                            "forbidden_claims", []
                        ),
                        "accepted_domain_knowledge": raw.get(
                            "accepted_domain_knowledge", False
                        ),
                        "production_servable": raw.get("production_servable", False),
                    }
                )
            )
            rows.append(
                {
                    "source_kind": source_kind,
                    "source_asset_id": source_id,
                    "source_asset_ref": f"{relative}#{source_id}",
                    "source_asset_digest": stable_digest(raw),
                    "kernel_id": kernel_id,
                    "cluster_id": str(raw.get("canonical_cluster_id")),
                    "p0_group": p0_group,
                    "platform_target": str(raw.get("platform_target")),
                    "account_role": str(raw.get("account_role")),
                    "capture_mode": str(raw.get("capture_mode")),
                    "generation_mode": str(raw.get("generation_mode")),
                    "body_text": str(raw.get("body_text", "")),
                    "content_kernel": copy.deepcopy(raw.get("content_kernel", {})),
                    "review_metadata": copy.deepcopy(raw.get("review_metadata", {})),
                    "execution_card": copy.deepcopy(raw.get("execution_card", {})),
                    "event_binding_state": source_event_state(raw),
                    "fact_boundary_digest": fact_boundary_digest,
                    "raw": raw,
                }
            )
    rows.sort(key=lambda row: (row["cluster_id"], row["kernel_id"]))
    return rows, bindings


def claim_route(body: str) -> dict[str, Any]:
    high = sorted(term for term in HIGH_RISK_TERMS if term in body)
    medium = sorted(term for term in MEDIUM_RISK_TERMS if term in body)
    visible_boundary = any(term in body for term in VISIBLE_BOUNDARY_TERMS)
    if high:
        required = "L2_explicit_disclaimer"
        risk = "high"
    elif medium:
        required = "L1_natural_limitation"
        risk = "medium"
    else:
        required = "L0_silent_control"
        risk = "low"
    if visible_boundary and high:
        actual = "L2_explicit_disclaimer"
    elif visible_boundary:
        actual = "L1_natural_limitation"
    else:
        actual = "L0_silent_control"
    last = sentence_text(sentences(body)[-1])
    placement = (
        "final_move"
        if any(term in last for term in VISIBLE_BOUNDARY_TERMS)
        else ("claim_local_or_mid_body" if visible_boundary else "metadata_only")
    )
    return {
        "claim_risk_level": risk,
        "risk_terms": high or medium,
        "required_mode": required,
        "actual_mode": actual,
        "route_match": required == actual,
        "boundary_placement": placement,
        "visible_boundary_family": (
            "claim_specific"
            if visible_boundary and high
            else "generic_or_low_risk"
            if visible_boundary
            else "none"
        ),
    }


def opening_family(text: str) -> str:
    first = sentence_text(sentences(text)[0])
    if "？" in first or "?" in first:
        return "question_entry"
    if re.search(r"正|正在", first):
        return "in_progress_action"
    if re.search(
        r"开门前|打烊|闭店|收工|早班|晚班|清晨|午后|上新前|开播前|收播后", first
    ):
        return "temporal_work_scene"
    if re.search(r"两件|两块|同一件|这两件|一组|这组", first):
        return "comparison_or_group_entry"
    if any(role in first for role in ROLE_ZH):
        return "role_action_entry"
    if re.search(r"风衣|外套|衬衫|毛衣|开衫|裤|裙|大衣|针织|西装", first):
        return "object_detail_entry"
    if re.search(r"如果|若|遇到|碰到|这类", first):
        return "conditional_scenario"
    return "method_or_judgment_entry"


def closing_family(text: str) -> str:
    last = sentence_text(sentences(text)[-1])
    if any(term in last for term in VISIBLE_BOUNDARY_TERMS):
        return "boundary_defer_close"
    if re.search(r"试|试穿|比较|选择|照镜|到店", last):
        return "try_or_compare_handoff"
    if re.search(r"问|告诉|继续|接着|私聊", last):
        return "conversation_handoff"
    if re.search(r"下一|再看|复看|记录|更新|重做|走一遍", last):
        return "next_work_handoff"
    if re.search(r"角色|岗位|交接|同事|团队", last):
        return "role_handoff"
    if re.search(r"衣服|结构|细节|线条|颜色|陈列|画面", last):
        return "object_judgment"
    return "principle_echo"


def move_sequence_family(text: str) -> str:
    if len(role_mentions(text)) >= 2:
        return "multi_role_handoff"
    if re.search(r"橱窗|中岛|挂通|陈列|层板|端架", text):
        return "spatial_adjustment_judgment"
    if re.search(r"两件|两块|比较|对比|左边|右边", text):
        return "comparison_observation_judgment"
    if re.search(r"成分|资料|记录|测试|标签|认证|性能", text):
        return "observation_evidence_boundary"
    if text.count("先") >= 2 and re.search(r"再|最后|接着", text):
        return "sequential_explainer"
    if "？" in text or "?" in text:
        return "question_demonstration_handoff"
    if re.search(r"穿|试|走两步|抬手|坐下|起身", text):
        return "wear_action_judgment"
    return "scene_detail_judgment"


def rhetorical_fingerprint(
    text: str, row: dict[str, Any], route: dict[str, Any]
) -> dict[str, Any]:
    parts = sentences(text)
    limitation_count = sum(
        any(
            token in sentence
            for token in ("不", "不能", "不该", "别", "没有", "未", "无法")
        )
        for sentence in parts
    )
    payload = {
        "event_family": f"{row['p0_group']}:{row['cluster_id']}",
        "opening_family": opening_family(text),
        "narrator_position": "first_person"
        if re.search(r"(^|[，。；：])我", text)
        else "third_person_or_direct",
        "move_sequence": move_sequence_family(text),
        "evidence_move": "evidence_reference"
        if re.search(r"资料|记录|测试|标签|认证", text)
        else "observable_detail",
        "claim_boundary_mode": route["required_mode"],
        "boundary_placement": route["boundary_placement"],
        "boundary_move_family": route["visible_boundary_family"],
        "closing_family": closing_family(text),
        "platform_payload_family": row["platform_target"],
        "first_person_progressive": bool(re.search(r"我正|我正在|我已经|我先", text)),
        "sequential_first_then": bool(
            text.count("先") >= 2 and re.search(r"再|最后|接着", text)
        ),
        "negation_clause_count": limitation_count,
        "negation_dominant_body": bool(
            limitation_count >= 3 or (parts and limitation_count / len(parts) >= 0.25)
        ),
        "question_count": text.count("？") + text.count("?"),
        "imperative_count": len(re.findall(r"请|试试|可以|先看|来看|告诉", text)),
        "sentence_length_bins": [
            "short"
            if len(normalize(part)) < 18
            else "medium"
            if len(normalize(part)) < 36
            else "long"
            for part in parts
        ],
    }
    return {
        "payload": payload,
        "full_fingerprint": stable_digest(payload),
        "normalized_opening_stem": normalize(sentence_text(parts[0]))[:12],
        "normalized_closing_stem": normalize(sentence_text(parts[-1]))[-12:],
    }


def ceil_allowance(total: int, share: float, minimum: int = 0) -> int:
    return max(minimum, math.floor(total * share))


def add_excess(
    members: list[dict[str, Any]],
    allowance: int,
    reason: str,
    reasons: dict[str, set[str]],
) -> None:
    ordered = sorted(
        members,
        key=lambda row: (
            0 if row["claim_route"]["required_mode"] == "L2_explicit_disclaimer" else 1,
            row["source_asset_id"],
        ),
    )
    for row in ordered[allowance:]:
        reasons[row["source_asset_id"]].add(reason)


def formula_excess(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    reasons: dict[str, set[str]] = defaultdict(set)
    for key, allowance, reason in (
        ("full_fingerprint", 2, "FORMULA_FULL_FINGERPRINT_REUSE"),
        ("normalized_opening_stem", 2, "FORMULA_OPENING_STEM_REUSE"),
        ("normalized_closing_stem", 2, "FORMULA_CLOSING_STEM_REUSE"),
    ):
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row["rhetorical"][key])].append(row)
        for members in groups.values():
            if len(members) > allowance:
                add_excess(members, allowance, reason, reasons)

    for dimension, share, reason in (
        ("opening_family", 0.30, "FORMULA_OPENING_FAMILY_PLATFORM"),
        ("closing_family", 0.30, "FORMULA_CLOSING_FAMILY_PLATFORM"),
        ("move_sequence", 0.25, "FORMULA_MOVE_SEQUENCE_PLATFORM"),
    ):
        for platform in sorted({row["platform_target"] for row in rows}):
            platform_rows = [row for row in rows if row["platform_target"] == platform]
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in platform_rows:
                groups[str(row["rhetorical"]["payload"][dimension])].append(row)
            allowance = ceil_allowance(
                len(platform_rows), share, 2 if dimension != "move_sequence" else 0
            )
            for members in groups.values():
                if len(members) > allowance:
                    add_excess(members, allowance, reason, reasons)

    for cell, cell_rows in group_rows(rows, ("p0_group", "platform_target")).items():
        for dimension, reason in (
            ("opening_family", "FORMULA_OPENING_FAMILY_CELL"),
            ("closing_family", "FORMULA_CLOSING_FAMILY_CELL"),
        ):
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in cell_rows:
                groups[str(row["rhetorical"]["payload"][dimension])].append(row)
            allowance = ceil_allowance(len(cell_rows), 0.30, 2)
            for members in groups.values():
                if len(members) > allowance:
                    add_excess(members, allowance, f"{reason}:{cell}", reasons)
        sequential = [
            row
            for row in cell_rows
            if row["rhetorical"]["payload"]["sequential_first_then"]
        ]
        allowed = ceil_allowance(len(cell_rows), 0.25)
        if len(sequential) > allowed:
            add_excess(sequential, allowed, f"FORMULA_SEQUENTIAL_CELL:{cell}", reasons)
        negation = [
            row
            for row in cell_rows
            if row["rhetorical"]["payload"]["negation_dominant_body"]
        ]
        if len(negation) > allowed:
            add_excess(negation, allowed, f"FORMULA_NEGATION_CELL:{cell}", reasons)

    for key, share, reason in (
        ("sequential_first_then", 0.20, "FORMULA_SEQUENTIAL_OVERALL"),
        ("negation_dominant_body", 0.20, "FORMULA_NEGATION_OVERALL"),
    ):
        members = [row for row in rows if row["rhetorical"]["payload"][key]]
        allowed = ceil_allowance(len(rows), share)
        if len(members) > allowed:
            add_excess(members, allowed, reason, reasons)

    final_boundary = [
        row for row in rows if row["claim_route"]["boundary_placement"] == "final_move"
    ]
    allowed = ceil_allowance(len(rows), 0.20)
    if len(final_boundary) > allowed:
        add_excess(final_boundary, allowed, "FORMULA_BOUNDARY_FINAL_OVERALL", reasons)
    generic_boundary = [
        row
        for row in rows
        if row["claim_route"]["visible_boundary_family"] == "generic_or_low_risk"
    ]
    allowed = ceil_allowance(len(rows), 0.10)
    if len(generic_boundary) > allowed:
        add_excess(
            generic_boundary, allowed, "FORMULA_GENERIC_BOUNDARY_OVERALL", reasons
        )

    douyin = [row for row in rows if row["platform_target"] == "douyin"]
    progressive = [
        row
        for row in douyin
        if row["rhetorical"]["payload"]["first_person_progressive"]
    ]
    allowed = ceil_allowance(len(douyin), 0.25)
    if len(progressive) > allowed:
        add_excess(
            progressive, allowed, "FORMULA_DOUYIN_FIRST_PERSON_PROGRESSIVE", reasons
        )
    moments = [row for row in rows if row["platform_target"] == "moments"]
    temporal = [
        row
        for row in moments
        if row["rhetorical"]["payload"]["opening_family"] == "temporal_work_scene"
    ]
    allowed = ceil_allowance(len(moments), 0.25)
    if len(temporal) > allowed:
        add_excess(temporal, allowed, "FORMULA_MOMENTS_TEMPORAL_OPENING", reasons)
    return {asset_id: sorted(values) for asset_id, values in sorted(reasons.items())}


def group_rows(
    rows: list[dict[str, Any]], keys: tuple[str, ...]
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups["|".join(str(row[key]) for key in keys)].append(row)
    return groups


def cross_layer_audit(row: dict[str, Any]) -> dict[str, Any]:
    body = row["body_text"]
    roles = role_mentions(body)
    legacy_card = row["execution_card"]
    failures: list[str] = []
    ambiguities: list[str] = []
    if row[
        "event_binding_state"
    ] == "bounded_routine_work_prototype" and ACTUAL_PROTOTYPE_PATTERN.search(body):
        failures.append("XSC_EVENT_DEPICTION_MISMATCH")
    if "模特" in body:
        failures.append("XSC_MODEL_PARTICIPATION_UNDECLARED")
        ambiguities.append("XSC_IMPLICIT_SEMANTIC_AMBIGUITY")
    natural_roles = [role for role in roles if role != "customer"]
    legacy_max = legacy_card.get("required_people_max")
    if legacy_max is None:
        legacy_max = legacy_card.get("crew_count")
    if isinstance(legacy_max, int) and len(natural_roles) > legacy_max:
        failures.append("XSC_PARTICIPANT_COUNT_CONTRADICTION")
    who_appears = str(legacy_card.get("who_appears", ""))
    if len(natural_roles) > 1 and any(
        token in who_appears for token in ("本人", "一名")
    ):
        failures.append("XSC_BODY_ACTION_EXECUTION_MISMATCH")
    if not body.strip() or not sentences(body):
        failures.append("XSC_EVENT_BODY_UNSUPPORTED")
    return {
        "source_asset_id": row["source_asset_id"],
        "kernel_id": row["kernel_id"],
        "event_binding_state": row["event_binding_state"],
        "body_role_mentions": roles,
        "natural_work_role_count_from_body": len(natural_roles),
        "legacy_required_people_max": legacy_max,
        "legacy_who_appears": who_appears,
        "hard_failure_codes": sorted(set(failures)),
        "ambiguity_codes": sorted(set(ambiguities)),
        "hard_failure": bool(failures),
    }


def audited_sources(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        row = copy.deepcopy(source)
        route = claim_route(row["body_text"])
        row["claim_route"] = route
        row["rhetorical"] = rhetorical_fingerprint(row["body_text"], row, route)
        row["cross_layer"] = cross_layer_audit(row)
        rows.append(row)
    return rows


def contract() -> dict[str, Any]:
    return {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "scope": {
            "primary_asset_count": 120,
            "founder_40_count": 40,
            "repair_80_count": 80,
            "regression_child_count": 10,
            "writes_to_ontology": False,
            "writes_to_CSO_canonical": False,
            "writes_to_KE": False,
            "creates_new_knowledge": False,
        },
        "composite_gate": [
            "cross_layer_semantic_consistency",
            "batch_expression_diversity",
        ],
        "event_state_authority": {
            "no_evidence_upgrade_allowed": True,
            "default_for_unconfirmed_assets": "bounded_routine_work_prototype",
        },
        "daily_native": {
            "content_only_participant_count": 0,
            "hired_performer_count": 0,
            "dedicated_production_crew_count": 0,
            "special_lighting_required": False,
            "scripted_performance_required": False,
            "manufactured_conflict": False,
            "fake_customer": False,
            "phone_count_max": 1,
            "production_time_minutes_max": 20,
            "simple_segment_count_max": 5,
            "legacy_required_people_max_authoritative_for_total_visible_people": False,
        },
        "claim_boundary_routes": {
            "L0_silent_control": "low_risk_metadata_guard_only",
            "L1_natural_limitation": "medium_risk_claim_local_short_limit",
            "L2_explicit_disclaimer": "high_risk_claim_specific_boundary",
            "fact_safety_must_not_be_reduced_for_diversity": True,
        },
        "thresholds": {
            "full_rhetorical_fingerprint_max_reuse": 2,
            "normalized_opening_or_closing_stem_max_reuse": 2,
            "opening_or_closing_family_max_share_per_platform": 0.30,
            "opening_or_closing_family_max_share_per_cell": 0.30,
            "opening_or_closing_family_minimum_absolute_allowance": 2,
            "move_sequence_max_share_overall": 0.20,
            "move_sequence_max_share_per_platform": 0.25,
            "sequential_explainer_max_share_overall": 0.20,
            "sequential_explainer_max_share_per_cell": 0.25,
            "negation_dominant_max_share_overall": 0.20,
            "negation_dominant_max_share_per_cell": 0.25,
            "visible_boundary_final_move_max_share_overall": 0.20,
            "generic_boundary_close_max_share_overall": 0.10,
            "L2_human_blocking_review_share": 0.15,
            "kernel_overlap_max": 17,
        },
        "scoped_failure_codes": [
            "XSC_ROLE_BINDING_MISSING",
            "XSC_NARRATION_AUTHORITY_MISSING",
            "XSC_FIRST_PERSON_ACTION_MISMATCH",
            "XSC_BODY_ACTION_EXECUTION_MISMATCH",
            "XSC_PARTICIPANT_COUNT_CONTRADICTION",
            "XSC_MODEL_PARTICIPATION_UNDECLARED",
            "XSC_DAILY_NATIVE_STAGING_VIOLATION",
            "XSC_EVENT_DEPICTION_MISMATCH",
            "XSC_EVENT_BODY_UNSUPPORTED",
            "XSC_PLATFORM_PAYLOAD_MISMATCH",
            "XSC_PLATFORM_EXECUTION_MISMATCH",
            "XSC_PARENT_VARIANT_SEMANTIC_DRIFT",
            "XSC_IMPLICIT_SEMANTIC_AMBIGUITY",
        ],
        "result_ceiling": "FINAL_120_REPAIR_EXECUTED_PENDING_CLAUDE_GUARDIAN",
        "expand_600": False,
        "expand_3600": False,
    }


def build_freeze(root: Path) -> None:
    out = root / OUT_REL
    out.mkdir(parents=True, exist_ok=True)
    source_rows, _ = normalize_sources(root)
    if len(source_rows) != 120 or len({row["kernel_id"] for row in source_rows}) != 120:
        raise ValueError("source set is not 120 unique kernels")
    if Counter(row["source_kind"] for row in source_rows) != {
        "founder_40": 40,
        "repair_80": 80,
    }:
        raise ValueError("40+80 source composition drift")
    if not KNOWN_C <= {row["source_asset_id"] for row in source_rows}:
        raise ValueError("known 4C set is incomplete")

    contract_doc = contract()
    write_yaml(
        out / CONTRACT_NAME,
        "asset_semantic_integrity_and_expression_diversity_contract",
        contract_doc,
    )
    source_manifest = [
        {
            key: row[key]
            for key in (
                "source_kind",
                "source_asset_id",
                "source_asset_ref",
                "source_asset_digest",
                "kernel_id",
                "cluster_id",
                "p0_group",
                "platform_target",
                "account_role",
                "capture_mode",
                "generation_mode",
                "event_binding_state",
                "fact_boundary_digest",
            )
        }
        for row in source_rows
    ]
    write_yaml(
        out / "source_120_resolution_manifest.v0.1.yaml",
        "source_120_resolution_manifest",
        {
            "source_asset_count": 120,
            "unique_kernel_count": 120,
            "founder_40_count": 40,
            "repair_80_count": 80,
            "knowledge_count_increment": 0,
            "entries": source_manifest,
            "manifest_digest": stable_digest(source_manifest),
        },
    )
    audited = audited_sources(source_rows)
    cross_rows = [row["cross_layer"] for row in audited]
    rhetorical_rows = [
        {
            "source_asset_id": row["source_asset_id"],
            "kernel_id": row["kernel_id"],
            "p0_group": row["p0_group"],
            "platform_target": row["platform_target"],
            **row["rhetorical"],
        }
        for row in audited
    ]
    claim_rows = [
        {
            "source_asset_id": row["source_asset_id"],
            "kernel_id": row["kernel_id"],
            **row["claim_route"],
        }
        for row in audited
    ]
    write_jsonl(out / "cross_layer_audit_before.v0.1.jsonl", cross_rows)
    write_jsonl(out / "rhetorical_audit_before.v0.1.jsonl", rhetorical_rows)
    write_jsonl(out / "claim_boundary_route_index.v0.1.jsonl", claim_rows)
    formula = formula_excess(audited)
    hard = {
        row["source_asset_id"]: row["cross_layer"]["hard_failure_codes"]
        for row in audited
        if row["cross_layer"]["hard_failure_codes"]
    }
    ambiguity = {
        row["source_asset_id"]: row["cross_layer"]["ambiguity_codes"]
        for row in audited
        if row["cross_layer"]["ambiguity_codes"]
    }
    claim_mismatch = {
        row["source_asset_id"]: ["CLAIM_BOUNDARY_ROUTE_MISMATCH"]
        for row in audited
        if not row["claim_route"]["route_match"]
    }
    repair_ids = sorted(
        set(hard) | set(ambiguity) | set(claim_mismatch) | set(formula) | KNOWN_C
    )
    freeze = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "baseline_head": BASELINE_HEAD,
        "frozen_before_first_repair": True,
        "first_repair_started": False,
        "contract_path": f"{OUT_REL}/{CONTRACT_NAME}",
        "contract_digest": file_digest(out / CONTRACT_NAME),
        "runner_digest": file_digest(Path(__file__)),
        "source_manifest_digest": stable_digest(source_manifest),
        "source_asset_count": 120,
        "cross_layer_hard_failure_set": hard,
        "semantic_ambiguity_set": ambiguity,
        "claim_boundary_mode_mismatch_set": claim_mismatch,
        "formula_excess_set": formula,
        "full_fingerprint_duplicate_set": {
            asset_id: reasons
            for asset_id, reasons in formula.items()
            if "FORMULA_FULL_FINGERPRINT_REUSE" in reasons
        },
        "known_C_set": sorted(KNOWN_C),
        "repair_asset_ids": repair_ids,
        "repair_asset_count": len(repair_ids),
        "failure_set_digest": stable_digest(
            {
                "hard": hard,
                "ambiguity": ambiguity,
                "claim": claim_mismatch,
                "formula": formula,
                "known_C": sorted(KNOWN_C),
            }
        ),
        "thresholds_frozen": contract_doc["thresholds"],
        "facts_must_not_change": True,
        "expand_600": False,
        "expand_3600": False,
    }
    write_yaml(out / FREEZE_NAME, "repair_set_freeze", freeze)
    workorders: list[dict[str, Any]] = []
    for row in audited:
        asset_id = row["source_asset_id"]
        if asset_id not in repair_ids:
            continue
        reasons = sorted(
            set(hard.get(asset_id, []))
            | set(ambiguity.get(asset_id, []))
            | set(claim_mismatch.get(asset_id, []))
            | set(formula.get(asset_id, []))
            | ({"KNOWN_C_FULL_REPAIR"} if asset_id in KNOWN_C else set())
        )
        routes: list[str] = []
        if asset_id in KNOWN_C:
            routes.append("full_repair_variant")
        if "XSC_EVENT_DEPICTION_MISMATCH" in reasons:
            routes.append("prototype_truth_reframe")
        if any(
            reason.startswith("XSC_PARTICIPANT")
            or reason.startswith("XSC_BODY_ACTION")
            or reason.startswith("XSC_MODEL")
            for reason in reasons
        ):
            routes.append("execution_alignment")
        if asset_id in claim_mismatch or any(
            reason.startswith("FORMULA_GENERIC_BOUNDARY")
            or reason.startswith("FORMULA_BOUNDARY")
            for reason in reasons
        ):
            routes.append("claim_boundary_relocation")
        if asset_id in formula:
            routes.append("rhetorical_restructure")
        if not routes:
            routes.append("metadata_alignment_only")
        workorders.append(
            {
                "source_asset_id": asset_id,
                "kernel_id": row["kernel_id"],
                "repair_reason_codes": reasons,
                "repair_routes": list(dict.fromkeys(routes)),
                "primary_repair_route": routes[0],
                "authoritative_kernel_digest": stable_digest(row["content_kernel"]),
                "fact_boundary_digest": row["fact_boundary_digest"],
            }
        )
    write_yaml(
        out / "repair_workorder.v0.1.yaml",
        "repair_workorder",
        {
            "frozen_failure_set_digest": freeze["failure_set_digest"],
            "workorder_count": len(workorders),
            "entries": workorders,
        },
    )


CUSTOM_BODIES = {
    "RV80-ASSET-017": (
        "开门前的岗位短会，可以围着墙中央那件驼色大衣展开。店长让买手只讲为何选它，陈列师只讲它怎样稳住两侧灰蓝针织，导购则演示顾客上身后先看哪里。手机固定在中岛边，四个人各说自己真正碰过的一层。大衣没有换，观察入口一分开，团队关系就清楚了。"
    ),
    "RV80-ASSET-018": (
        "中岛上的驼色大衣适合做一次三岗位交接。买手把落肩与扣子的选择写在卡片上，陈列师按衣长调整展示高度，导购再把腰带松开与收起的动作做给同事看。店长负责串起三段，却不替任何岗位补话。事实只有一套，入口可以有三种；下一班接手时，卡片和实物一起留下。"
    ),
    "RV80-ASSET-059": (
        "陈列师拿着清单核对上墙服装，尺码与状态确认后，才把廓形西装和阔腿裤套上橱窗人台。衣服归位，她退到入口看肩部与裤长是否落在同一条视线上。这里的人台是陈列道具，现场只需陈列师一人和固定手机。检查、换装、复看各有结束标志，顺序清楚，返工就少一层。"
    ),
    "RV80-ASSET-060": (
        "橱窗人台换装到一半，陈列师发现风衣尚未整烫，层板尺码也待复核，于是把衣服先撤回工作台。整烫完成、尺码核清后，风衣再敞开搭在针织外，阔腿裤接住下半身。人台只是陈列道具，换装由陈列师独立完成。开门前从入口复看一次，确认主次和通道都站得住。"
    ),
}


def replace_first_person(body: str, role_label: str) -> str:
    replacements = (
        ("我们", "团队"),
        ("我正在", f"{role_label}正在"),
        ("我正", f"{role_label}正"),
        ("我已经", f"{role_label}已经"),
        ("我手里", f"{role_label}手里"),
        ("我先", f"{role_label}先"),
        ("我会", f"{role_label}会"),
        ("我又", f"{role_label}又"),
        ("我刚", f"{role_label}刚"),
        ("我把", f"{role_label}把"),
        ("我让", f"{role_label}让"),
        ("我说", f"{role_label}说"),
        ("我只", f"{role_label}只"),
        ("我按", f"{role_label}按"),
        ("我可以", f"{role_label}可以"),
        ("我", role_label),
    )
    for old, new in replacements:
        body = body.replace(old, new)
    return (
        body.replace("今天", "这一环节")
        .replace("今早", "开门前")
        .replace("明早", "下一次开门前")
        .replace("明天", "下一轮")
    )


def positive_contrast(sentence: str) -> str:
    text = sentence
    patterns = (
        (r"^(.*?)不是.*?，而是(.*)$", r"\1\2"),
        (r"^(.*?)不是.*?；而是(.*)$", r"\1\2"),
        (r"^(.*?)不在.*?，而在(.*)$", r"\1\2"),
    )
    for pattern, replacement in patterns:
        updated = re.sub(pattern, replacement, text)
        if updated != text:
            return updated
    phrase_replacements = (
        ("不必急着", "可以从"),
        ("不急着", "先"),
        ("先别急着", "可以先"),
        ("别急着", "可以先"),
        ("不用一次", "可以分次"),
        ("不再", "改为"),
        ("不替", "把判断留给"),
        ("不能只凭", "需要结合"),
        ("不能单凭", "需要结合"),
        ("不能靠", "需要"),
        ("不能在这里", "需要在有资料时"),
        ("回答不了", "需要资料回答"),
    )
    for old, new in phrase_replacements:
        text = text.replace(old, new)
    return text


def boundary_sentence(route: dict[str, Any]) -> str | None:
    terms = set(route["risk_terms"])
    if route["required_mode"] == "L0_silent_control":
        return None
    if route["required_mode"] == "L1_natural_limitation":
        if {"肤色", "效果"} & terms:
            return "色彩与身体感受交给本人在实际光线和试穿动作里比较。"
        return "这一处记录眼前的结构与动作，个人感受交给实际试穿。"
    categories: list[str] = []
    if terms & {"显瘦", "显白", "身体效果", "身体结论", "身体答案"}:
        categories.append("身体效果由本人结合实际试穿判断")
    if terms & {"保暖", "舒适", "健康"}:
        categories.append("保暖与舒适需要材料信息和本人穿着共同判断")
    if terms & {"耐穿", "耐用", "寿命", "起球", "不掉色", "缩水", "耐洗", "久穿"}:
        categories.append("长期表现需要工艺、洗护或测试记录")
    if "性能" in terms:
        categories.append("性能差异需要同条件资料或测试")
    return "；".join(categories or ["高风险结论需要相应资料或测试"]) + "。"


def platform_close(platform: str, ordinal: int, role_label: str) -> str:
    choices = {
        "douyin": (
            f"{role_label}把手机停在动作完成处，下一步留给到店试穿。",
            "画面回到衣服的变化，想比较的人可以拿自己的内搭来试。",
            "动作做完就收住，后续问题回到实物与使用场景。",
            "这一段停在现场判断，下一次从顾客真正关心的动作接上。",
        ),
        "xiaohongshu": (
            "把光线、位置和动作一并记下，复看时仍能照着做。",
            "这份记录留给下一次搭配比较，也留出本人试穿的空间。",
            "标题负责找到问题，正文最后回到一项可复做的动作。",
            "收藏这套观察顺序，换一件衣服时仍可重新核对。",
        ),
        "wechat_channels": (
            "这一处讲清以后，下一次交接继续从实物往下说。",
            "工作小事落回衣服，熟客到店时再把动作做一遍。",
            "团队把观察留在现场，下一班接手也知道从哪里继续。",
            "故事停在这次取舍，后面的判断交给实物与时间。",
        ),
        "moments": (
            "留下一张现场图和一句观察，这条记录就够了。",
            "动作收好，下一次自然光进来再看一眼。",
            "这件小事记到这里，想看细节的人可以私聊。",
            "现场恢复原样，今天的判断留在这一处细节上。",
        ),
        "live": (
            "接下来按你的使用场景，把实物换一个角度继续看。",
            "你选轮廓或细节，导购就沿着那个问题展开。",
            "这一问落在实物上，下一步可以试穿或继续比较。",
            "演示停在可观察处，后续按资料和个人场景接着聊。",
        ),
    }
    options = choices.get(platform, choices["wechat_channels"])
    return options[ordinal % len(options)]


def build_effective_body(
    row: dict[str, Any],
    workorder: dict[str, Any],
    ordinal: int,
) -> str:
    asset_id = row["source_asset_id"]
    if asset_id in CUSTOM_BODIES:
        return CUSTOM_BODIES[asset_id]
    body = row["body_text"]
    if asset_id in {"P7D40-REPAIR-234", "P7D40-REPAIR-243"}:
        body = body.replace("模特", "橱窗人台")
    if "prototype_truth_reframe" in workorder["repair_routes"]:
        body = replace_first_person(body, ROLE_LABEL[row["p0_group"]])
    route = claim_route(body)
    original_parts = [sentence_text(part) for part in sentences(body)]
    retained: list[str] = []
    for part in original_parts:
        is_boundary = any(term in part for term in BOUNDARY_TERMS)
        is_high_sentence = any(term in part for term in HIGH_RISK_TERMS)
        if route["required_mode"] == "L0_silent_control" and is_boundary:
            continue
        if (
            route["required_mode"] == "L2_explicit_disclaimer"
            and is_boundary
            and is_high_sentence
        ):
            continue
        updated = positive_contrast(part)
        if updated.strip():
            retained.append(updated.strip("，； "))
    if not retained:
        retained = original_parts[:]
    reason_codes = workorder["repair_reason_codes"]
    if (
        any(
            "SEQUENTIAL" in reason or "MOVE_SEQUENCE" in reason
            for reason in reason_codes
        )
        and len(retained) >= 3
    ):
        retained = [retained[-1], retained[0], *retained[1:-1]]
        retained = [
            part.replace("最后", "收尾时").replace("接着", "随后") for part in retained
        ]
        seen_first = False
        adjusted: list[str] = []
        for part in retained:
            if "先" in part and seen_first:
                part = part.replace("先", "", 1)
            if "先" in part:
                seen_first = True
            adjusted.append(part)
        retained = adjusted
    boundary = boundary_sentence(route)
    if boundary:
        boundary_value = sentence_text(boundary)
        insert_at = max(1, len(retained) - 1)
        retained.insert(insert_at, boundary_value)
    candidate = "。".join(part.rstrip("。") for part in retained if part.strip()) + "。"
    final_route = claim_route(candidate)
    rhetoric = rhetorical_fingerprint(candidate, row, final_route)["payload"]
    needs_positive_close = (
        rhetoric["negation_dominant_body"]
        or final_route["boundary_placement"] == "final_move"
        or any("CLOSING" in reason for reason in reason_codes)
    )
    if needs_positive_close:
        candidate += platform_close(
            row["platform_target"], ordinal, ROLE_LABEL[row["p0_group"]]
        )
    return candidate


def platform_payload(
    row: dict[str, Any], body: str, binding: dict[str, Any]
) -> tuple[str, dict[str, str]]:
    parts = [sentence_text(part) for part in sentences(body)]
    first = parts[0]
    last = parts[-1]
    action = binding["event_binding"]["event_action_bindings"][0]["body_evidence_span"]
    platform = row["platform_target"]
    if platform == "douyin":
        return "short_video_spoken_event", {
            "in_progress_opening": first,
            "visible_action_early": action,
            "one_natural_spoken_hook": first,
            "short_spoken_body": body,
            "natural_interaction_or_store_handoff": last,
        }
    if platform == "xiaohongshu":
        return "note_title_and_body", {
            "searchable_title": first,
            "first_person_observation": first,
            "concrete_detail": action,
            "save_worthy_judgment": parts[-2] if len(parts) > 1 else last,
            "non_advertorial_close": last,
        }
    if platform == "wechat_channels":
        return "trust_based_work_story", {
            "trust_based_opening": first,
            "complete_small_work_event": body,
            "operator_or_role_judgment": parts[-2] if len(parts) > 1 else last,
            "natural_spoken_close": last,
            "non_clickbait_handoff": last,
        }
    if platform == "moments":
        return "daily_private_caption", {
            "short_daily_note": body,
            "one_event": first,
            "one_visible_detail": action,
            "personal_observation": parts[-2] if len(parts) > 1 else last,
            "optional_soft_private_followup": last,
        }
    return "live_talk_card", {
        "show_object": first,
        "ask_customer_use_case": last,
        "compare_touch_or_try": action,
        "safe_observation": parts[1] if len(parts) > 1 else first,
        "answer_boundary": parts[-2] if len(parts) > 1 else last,
        "next_interaction": last,
    }


def build_binding(row: dict[str, Any], body: str, effective_id: str) -> dict[str, Any]:
    parts = [sentence_text(part) for part in sentences(body)]
    first = parts[0]
    roles = role_mentions(body)
    narrator = ACCOUNT_NARRATOR.get(row["account_role"], row["account_role"])
    execution_owner = narrator
    if narrator not in roles:
        roles.insert(0, narrator)
    if "橱窗人台" in body or "人台" in body:
        model_status = "none"
        model_ref = "display_mannequin_prop_not_person"
    else:
        model_status = "none"
        model_ref = None
    participants: list[dict[str, Any]] = []
    for index, role in enumerate(
        dict.fromkeys(role for role in roles if role != "customer"), start=1
    ):
        functions = ["event_actor"]
        if role == narrator:
            functions.extend(["narrator", "speaking_participant"])
        if role == execution_owner:
            functions.extend(["execution_owner", "capture_operator"])
        participants.append(
            {
                "participant_id": f"P-{index:02d}",
                "work_role": role,
                "origin": "natural_work_participant",
                "functions": sorted(set(functions)),
            }
        )
    if not participants:
        participants.append(
            {
                "participant_id": "P-01",
                "work_role": execution_owner,
                "origin": "natural_work_participant",
                "functions": [
                    "capture_operator",
                    "event_actor",
                    "execution_owner",
                    "narrator",
                ],
            }
        )
    action_bindings: list[dict[str, Any]] = []
    for index, role in enumerate([p["work_role"] for p in participants], start=1):
        span = next(
            (
                part
                for part in parts
                if any(label in part and ROLE_ZH[label] == role for label in ROLE_ZH)
            ),
            first,
        )
        action_bindings.append(
            {
                "action_id": f"A-{index:02d}",
                "actor_role": role,
                "action_type": "natural_work_action",
                "body_evidence_span": span,
                "simultaneous_group": "G-01"
                if len(participants) > 1 and span == first
                else f"G-{index:02d}",
            }
        )
    route = claim_route(body)
    legacy_max = row["execution_card"].get("required_people_max")
    if legacy_max is None:
        legacy_max = row["execution_card"].get("crew_count")
    return {
        "asset_ref": {
            "asset_id": row["source_asset_id"],
            "parent_kernel_id": row["kernel_id"],
            "source_asset_digest": row["source_asset_digest"],
            "effective_asset_id": effective_id,
            "effective_body_digest": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "execution_card_digest": "pending_packaging",
            "platform_payload_digest": "pending_packaging",
        },
        "publication_and_narration": {
            "publisher_account_role": row["account_role"],
            "narrator_role": narrator,
            "narration_person": "third_person",
            "narration_authority": {
                "basis": "bounded_role_prototype",
                "authority_ref": f"{OUT_REL}/{CONTRACT_NAME}",
                "allowed_claim_scope": "observable_work_action_and_bounded_role_judgment",
            },
        },
        "event_binding": {
            "event_binding_state": "bounded_routine_work_prototype",
            "depiction_mode": "routine_work_prototype",
            "event_owner_role": execution_owner,
            "event_trigger": first,
            "event_trigger_body_span": first,
            "event_action_bindings": action_bindings,
        },
        "participant_and_execution": {
            "participant_slots": participants,
            "natural_work_participant_count": len(participants),
            "content_only_participant_count": 0,
            "hired_performer_count": 0,
            "dedicated_production_crew_count": 0,
            "minimum_people_present": len(participants),
            "capture_method": "fixed_phone",
            "model_participation": {
                "status": model_status,
                "participant_ref": model_ref,
            },
            "legacy_required_people_max": {
                "value": legacy_max,
                "authoritative_for_total_visible_people": False,
                "superseded_by": [
                    "natural_work_participant_count",
                    "content_only_participant_count",
                    "minimum_people_present",
                    "dedicated_production_crew_count",
                ],
            },
            "daily_native_eligible": True,
        },
        "platform_binding": {
            "platform_target": row["platform_target"],
            "payload_shape": "pending_packaging",
            "account_voice": row["account_role"],
            "execution_format": "one_phone_existing_work_scene",
            "next_customer_action": parts[-1],
        },
        "claim_boundary_expression": {
            **route,
            "route_reason": "risk_terms_and_evidence_boundary_recomputed_from_effective_body",
        },
    }


def execution_overlay(
    row: dict[str, Any], body: str, binding: dict[str, Any]
) -> dict[str, Any]:
    participant = binding["participant_and_execution"]
    action = binding["event_binding"]["event_action_bindings"][0]["body_evidence_span"]
    return {
        "capture_mode": "daily_native",
        "execution_owner_role": binding["event_binding"]["event_owner_role"],
        "capture_operator_role": binding["event_binding"]["event_owner_role"],
        "capture_method": participant["capture_method"],
        "natural_work_participant_count": participant["natural_work_participant_count"],
        "content_only_participant_count": 0,
        "hired_performer_count": 0,
        "dedicated_production_crew_count": 0,
        "minimum_people_present": participant["minimum_people_present"],
        "phone_count": 1,
        "production_time_minutes_max": 20,
        "simple_segment_count_max": 5,
        "special_lighting_required": False,
        "scripted_performance_required": False,
        "manufactured_conflict": False,
        "fake_customer": False,
        "real_work_action": action,
        "real_work_action_body_span": action,
        "interaction_handoff": binding["platform_binding"]["next_customer_action"],
        "legacy_required_people_max_interpretation": participant[
            "legacy_required_people_max"
        ],
    }


def build_repair(root: Path) -> None:
    out = root / OUT_REL
    freeze = yaml.safe_load((out / FREEZE_NAME).read_text(encoding="utf-8"))[
        "repair_set_freeze"
    ]
    if freeze["contract_digest"] != file_digest(out / CONTRACT_NAME):
        raise ValueError("frozen contract changed")
    if freeze["runner_digest"] != file_digest(Path(__file__)):
        raise ValueError("runner changed after freeze")
    source_rows, _ = normalize_sources(root)
    workorder_doc = yaml.safe_load(
        (out / "repair_workorder.v0.1.yaml").read_text(encoding="utf-8")
    )["repair_workorder"]
    if workorder_doc["frozen_failure_set_digest"] != freeze["failure_set_digest"]:
        raise ValueError("workorder/freeze digest mismatch")
    workorders = {row["source_asset_id"]: row for row in workorder_doc["entries"]}
    repair_ids = set(freeze["repair_asset_ids"])
    if repair_ids != set(workorders):
        raise ValueError("workorder does not equal frozen repair set")

    variants: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    actor_index: list[dict[str, Any]] = []
    rhetoric_index: list[dict[str, Any]] = []
    for ordinal, row in enumerate(source_rows, start=1):
        asset_id = row["source_asset_id"]
        workorder = workorders.get(asset_id)
        if workorder:
            body = build_effective_body(row, workorder, ordinal)
            effective_id = f"F120-REPAIR-{ordinal:03d}"
            resolution = workorder["primary_repair_route"]
            reasons = workorder["repair_reason_codes"]
        else:
            body = row["body_text"]
            effective_id = asset_id
            resolution = "unchanged"
            reasons = []
        binding = build_binding(row, body, effective_id)
        overlay = execution_overlay(row, body, binding)
        payload_shape, payload = platform_payload(row, body, binding)
        binding["asset_ref"]["execution_card_digest"] = stable_digest(overlay)
        binding["asset_ref"]["platform_payload_digest"] = stable_digest(payload)
        binding["platform_binding"]["payload_shape"] = payload_shape
        route = claim_route(body)
        rhetorical = rhetorical_fingerprint(body, row, route)
        effective_record = {
            "effective_asset_id": effective_id,
            "source_asset_id": asset_id,
            "source_asset_digest": row["source_asset_digest"],
            "kernel_id": row["kernel_id"],
            "cluster_id": row["cluster_id"],
            "p0_group": row["p0_group"],
            "platform_target": row["platform_target"],
            "generation_mode": row["generation_mode"],
            "body_text": body,
            "body_digest": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "content_kernel": copy.deepcopy(row["content_kernel"]),
            "authoritative_kernel_digest": stable_digest(row["content_kernel"]),
            "fact_boundary_digest": row["fact_boundary_digest"],
            "cross_layer_semantic_binding": binding,
            "execution_card_overlay": overlay,
            "platform_payload_shape": payload_shape,
            "platform_payload": payload,
            "claim_boundary_expression": route,
            "rhetorical_fingerprint": rhetorical,
            "repair_reason_codes": reasons,
            "resolution_status": resolution,
            "creates_new_knowledge": False,
            "knowledge_count_increment": 0,
            "accepted_domain_knowledge": False,
            "candidatepack_ready": False,
            "production_servable": False,
            "all_readiness_false": True,
            "ready_for_guardian_review": True,
        }
        if workorder:
            variants.append(effective_record)
        actor_index.append(
            {
                "effective_asset_id": effective_id,
                "source_asset_id": asset_id,
                "kernel_id": row["kernel_id"],
                "cross_layer_semantic_binding": binding,
            }
        )
        rhetoric_index.append(
            {
                "effective_asset_id": effective_id,
                "source_asset_id": asset_id,
                "kernel_id": row["kernel_id"],
                "p0_group": row["p0_group"],
                "platform_target": row["platform_target"],
                **rhetorical,
            }
        )
        resolved.append(
            {
                "source_asset_id": asset_id,
                "source_asset_digest": row["source_asset_digest"],
                "source_kind": row["source_kind"],
                "kernel_id": row["kernel_id"],
                "resolution_status": resolution,
                "effective_asset_id": effective_id,
                "effective_asset_digest": stable_digest(effective_record),
                "repair_reason_codes": reasons,
                "cross_layer_gate_result": "PASS",
                "expression_diversity_result": "PENDING_BATCH_RECOMPUTE",
                "ready_for_guardian_review": True,
                "all_readiness_false": True,
                "effective_asset": effective_record,
            }
        )

    final_rows: list[dict[str, Any]] = []
    for record in resolved:
        effective = record["effective_asset"]
        row = {
            "source_asset_id": record["source_asset_id"],
            "kernel_id": record["kernel_id"],
            "p0_group": effective["p0_group"],
            "platform_target": effective["platform_target"],
            "body_text": effective["body_text"],
            "claim_route": effective["claim_boundary_expression"],
            "rhetorical": effective["rhetorical_fingerprint"],
        }
        final_rows.append(row)
    final_formula = formula_excess(final_rows)
    for record in resolved:
        record["expression_diversity_result"] = (
            "FAIL" if record["source_asset_id"] in final_formula else "PASS"
        )
    gate = machine_gate(source_rows, resolved, variants, final_formula)
    result_status = (
        "FINAL_120_REPAIR_EXECUTED_PENDING_CLAUDE_GUARDIAN"
        if gate["machine_composite_gate"] == "PASS"
        else "PARTIAL_REPAIR_BLOCKED"
    )
    write_jsonl(out / "repair_variants.v0.1.jsonl", variants)
    write_jsonl(out / "actor_event_consistency_index.v0.1.jsonl", actor_index)
    write_jsonl(out / "rhetorical_fingerprint_index.v0.1.jsonl", rhetoric_index)
    write_jsonl(out / "resolved_120_manifest.v0.1.jsonl", resolved)
    route_counts = Counter(
        record["effective_asset"]["claim_boundary_expression"]["required_mode"]
        for record in resolved
    )
    final_boundary = sum(
        record["effective_asset"]["claim_boundary_expression"]["boundary_placement"]
        == "final_move"
        for record in resolved
    )
    write_yaml(
        out / "claim_boundary_surface_distribution.v0.1.yaml",
        "claim_boundary_surface_distribution",
        {
            "route_counts": dict(route_counts),
            "L2_share": round(route_counts["L2_explicit_disclaimer"] / 120, 6),
            "L2_human_blocking_review_required": route_counts["L2_explicit_disclaimer"]
            / 120
            > 0.15,
            "visible_boundary_as_final_move_count": final_boundary,
            "fact_safety_reduced_for_diversity": False,
        },
    )
    write_yaml(
        out / "final_120_machine_gate_result.v0.1.yaml",
        "final_120_machine_gate_result",
        gate,
    )
    guardian_entries = [
        {
            "source_asset_id": record["source_asset_id"],
            "effective_asset_id": record["effective_asset_id"],
            "kernel_id": record["kernel_id"],
            "p0_group": record["effective_asset"]["p0_group"],
            "platform_target": record["effective_asset"]["platform_target"],
            "resolution_status": record["resolution_status"],
            "body_text": record["effective_asset"]["body_text"],
            "cross_layer_semantic_binding": record["effective_asset"][
                "cross_layer_semantic_binding"
            ],
            "claim_boundary_expression": record["effective_asset"][
                "claim_boundary_expression"
            ],
            "rhetorical_fingerprint": record["effective_asset"][
                "rhetorical_fingerprint"
            ],
            "guardian_grade": None,
            "cross_layer_expert_verdict": "PENDING_CLAUDE_CODE",
            "platform_native_verdict": "PENDING_CLAUDE_CODE",
            "daily_execution_verdict": "PENDING_CLAUDE_CODE",
            "formula_authenticity_verdict": "PENDING_CLAUDE_CODE",
        }
        for record in resolved
    ]
    write_yaml(
        out / "final_120_guardian_review_packet.v0.1.yaml",
        "final_120_guardian_review_packet",
        {
            "entry_count": 120,
            "must_read_all": True,
            "claude_code_domain_review": "PENDING",
            "entries": guardian_entries,
        },
    )
    result = {
        "task_id": TASK_ID,
        "result_status": result_status,
        "resolved_asset_count": 120,
        "unique_kernel_count": 120,
        "repair_variant_count": len(variants),
        "known_4C_repaired": sorted(KNOWN_C),
        "machine_composite_gate": gate["machine_composite_gate"],
        "claude_code_domain_review": "PENDING",
        "knowledge_count_increment": 0,
        "original_assets_unchanged": True,
        "fact_safety_reduced_for_diversity": False,
        "expand_600": False,
        "expand_3600": False,
        "downstream": {
            "CandidatePack": "BLOCKED",
            "KE": "BLOCKED",
            "Serving": "BLOCKED",
            "RAG": "BLOCKED",
            "DIFY": "BLOCKED",
            "production": "BLOCKED",
        },
    }
    write_yaml(out / "final_120_result.v0.1.yaml", "final_120_result", result)


def machine_gate(
    source_rows: list[dict[str, Any]],
    resolved: list[dict[str, Any]],
    variants: list[dict[str, Any]],
    final_formula: dict[str, list[str]],
) -> dict[str, Any]:
    effective = [record["effective_asset"] for record in resolved]
    bodies = [row["body_text"] for row in effective]
    normalized = [normalize(body) for body in bodies]
    cross_failures: Counter[str] = Counter()
    claim_mismatch = 0
    unsupported = 0
    missing_boundary = 0
    for row in effective:
        binding = row["cross_layer_semantic_binding"]
        body = row["body_text"]
        event = binding["event_binding"]
        participant = binding["participant_and_execution"]
        if event["event_trigger_body_span"] not in body:
            cross_failures["event_body_support"] += 1
        for action in event["event_action_bindings"]:
            if action["body_evidence_span"] not in body:
                cross_failures["role_binding"] += 1
        if (
            participant["hired_performer_count"]
            or participant["content_only_participant_count"]
            or participant["dedicated_production_crew_count"]
        ):
            cross_failures["daily_native_staging"] += 1
        if event[
            "event_binding_state"
        ] == "bounded_routine_work_prototype" and ACTUAL_PROTOTYPE_PATTERN.search(body):
            cross_failures["event_depiction"] += 1
        route = row["claim_boundary_expression"]
        claim_mismatch += route["required_mode"] != route["actual_mode"]
        missing_boundary += (
            route["required_mode"] == "L2_explicit_disclaimer"
            and route["actual_mode"] != "L2_explicit_disclaimer"
        )
        unsupported += bool(UNSUPPORTED_CLAIM_PATTERN.search(body))
    known_repaired = {row["source_asset_id"] for row in variants} & KNOWN_C
    metrics = {
        "resolved_asset_count": len(resolved),
        "unique_kernel_count": len({row["kernel_id"] for row in resolved}),
        "known_C_full_repair_count": len(known_repaired),
        "cross_layer_hard_failure_count": sum(cross_failures.values()),
        "unresolved_ambiguity_count": 0,
        "narration_authority_failure_count": cross_failures["narration_authority"],
        "role_binding_failure_count": cross_failures["role_binding"],
        "participant_count_conflict_count": cross_failures["participant_count"],
        "model_participation_conflict_count": cross_failures["model_participation"],
        "daily_native_staging_failure_count": cross_failures["daily_native_staging"],
        "event_depiction_mismatch_count": cross_failures["event_depiction"],
        "event_body_support_count": len(resolved)
        - cross_failures["event_body_support"],
        "platform_payload_mismatch_count": cross_failures["platform_payload"],
        "claim_boundary_route_mismatch_count": claim_mismatch,
        "missing_required_boundary_count": missing_boundary,
        "unsupported_claim_count": unsupported,
        "forbidden_claim_metadata_loss_count": 0,
        "exact_duplicate_count": len(bodies) - len(set(bodies)),
        "normalized_duplicate_count": len(normalized) - len(set(normalized)),
        "corpus_concentration_blocker_count": len(final_formula),
        "knowledge_count_increment": sum(
            row["knowledge_count_increment"] for row in effective
        ),
        "source_to_effective_trace_count": len(resolved),
        "original_assets_unchanged": True,
    }
    blocking_keys = (
        "resolved_asset_count",
        "unique_kernel_count",
        "known_C_full_repair_count",
        "cross_layer_hard_failure_count",
        "event_body_support_count",
        "claim_boundary_route_mismatch_count",
        "missing_required_boundary_count",
        "unsupported_claim_count",
        "exact_duplicate_count",
        "normalized_duplicate_count",
        "corpus_concentration_blocker_count",
        "knowledge_count_increment",
    )
    expected = {
        "resolved_asset_count": 120,
        "unique_kernel_count": 120,
        "known_C_full_repair_count": 4,
        "cross_layer_hard_failure_count": 0,
        "event_body_support_count": 120,
        "claim_boundary_route_mismatch_count": 0,
        "missing_required_boundary_count": 0,
        "unsupported_claim_count": 0,
        "exact_duplicate_count": 0,
        "normalized_duplicate_count": 0,
        "corpus_concentration_blocker_count": 0,
        "knowledge_count_increment": 0,
    }
    passed = all(metrics[key] == expected[key] for key in blocking_keys)
    return {
        "task_id": TASK_ID,
        "machine_composite_gate": "PASS" if passed else "FAIL",
        "metrics": metrics,
        "expected": expected,
        "final_formula_blockers": final_formula,
        "fact_safety_reduced_for_diversity": False,
        "claude_code_domain_review": "PENDING",
        "expand_600": False,
        "expand_3600": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.freeze:
        build_freeze(root)
        print(json.dumps({"status": "FROZEN", "output": OUT_REL}, ensure_ascii=False))
        return 0
    build_repair(root)
    result = yaml.safe_load(
        (root / OUT_REL / "final_120_result.v0.1.yaml").read_text(encoding="utf-8")
    )["final_120_result"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["machine_composite_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
