#!/usr/bin/env python3
"""Fail-closed integrity checker for the scoped Final-120 repair package."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


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
CONTRACT_REL = (
    f"{OUT_REL}/asset_semantic_integrity_and_expression_diversity_contract.v0.1.yaml"
)
FREEZE_REL = f"{OUT_REL}/repair_set_freeze.v0.1.yaml"
RUNNER_REL = "ci/runners/run_p7d_final_120_semantic_repair.py"
REPORT_REL = "ci/reports/p7d_final_120_semantic_repair_report.v0.1.json"
FIXTURE_REL = "ci/fixtures/p7d_final_120_semantic_repair/fixture_manifest.v0.1.yaml"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
LEDGER_MD_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"
RECEIPT_REL = "docs/reports/p7d_final_120_semantic_repair_receipt.json"
DOC_REPORT_REL = "docs/reports/p7d_final_120_semantic_repair_report.md"
KNOWN_C = {
    "RV80-ASSET-017",
    "RV80-ASSET-018",
    "RV80-ASSET-059",
    "RV80-ASSET-060",
}
READINESS_KEYS = {
    "candidatepack_ready",
    "KE_ready",
    "Serving_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
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
ACTUAL_PROTOTYPE_PATTERN = re.compile(
    r"(^|[，。；：])(?:我|我们)|今天|今早|刚刚|明早|明天|我们店|老板决定"
)
UNSUPPORTED_CLAIM_PATTERN = re.compile(
    r"保证.{0,6}(显瘦|显白|保暖|耐穿|舒适)|"
    r"一定.{0,6}(显瘦|显白|保暖|耐穿|舒适)|"
    r"卖爆|销量(?:增长|提升)|转化率(?:增长|提升)"
)
NORMALIZE_PATTERN = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])")
ALLOWED_PREFIXES = (
    f"{OUT_REL}/",
    RUNNER_REL,
    "ci/checkers/check_p7d_final_120_semantic_repair.py",
    "ci/fixtures/p7d_final_120_semantic_repair/",
    REPORT_REL,
    LEDGER_REL,
    LEDGER_MD_REL,
    RECEIPT_REL,
    DOC_REPORT_REL,
)


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
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL row: {path}:{line_number}")
        rows.append(value)
    return rows


def read_yaml(path: Path) -> Any:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if value is None:
        raise ValueError(f"empty YAML: {path}")
    return value


def run_git(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_text(root: Path, *args: str) -> str:
    return run_git(root, *args).stdout.decode("utf-8", errors="replace")


def changed_paths(root: Path) -> set[str]:
    paths = {
        line.strip()
        for line in git_text(
            root, "diff", "--name-only", BASELINE_HEAD, "--"
        ).splitlines()
        if line.strip()
    }
    paths.update(
        line.strip()
        for line in git_text(
            root, "ls-files", "--others", "--exclude-standard"
        ).splitlines()
        if line.strip()
    )
    return paths


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


def claim_route(body: str) -> dict[str, Any]:
    high = sorted(term for term in HIGH_RISK_TERMS if term in body)
    medium = sorted(term for term in MEDIUM_RISK_TERMS if term in body)
    visible = any(term in body for term in VISIBLE_BOUNDARY_TERMS)
    if high:
        required, risk = "L2_explicit_disclaimer", "high"
    elif medium:
        required, risk = "L1_natural_limitation", "medium"
    else:
        required, risk = "L0_silent_control", "low"
    if visible and high:
        actual = "L2_explicit_disclaimer"
    elif visible:
        actual = "L1_natural_limitation"
    else:
        actual = "L0_silent_control"
    last = sentence_text(sentences(body)[-1])
    placement = (
        "final_move"
        if any(term in last for term in VISIBLE_BOUNDARY_TERMS)
        else "claim_local_or_mid_body"
        if visible
        else "metadata_only"
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
            if visible and high
            else "generic_or_low_risk"
            if visible
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
        r"开门前|打烊|闭店|收工|早班|晚班|清晨|午后|上新前|开播前|收播后",
        first,
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
    text: str, p0_group: str, cluster_id: str, platform: str, route: dict[str, Any]
) -> dict[str, Any]:
    parts = sentences(text)
    limitation_count = sum(
        any(
            token in part
            for token in ("不", "不能", "不该", "别", "没有", "未", "无法")
        )
        for part in parts
    )
    payload = {
        "event_family": f"{p0_group}:{cluster_id}",
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
        "platform_payload_family": platform,
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


def group_rows(
    rows: list[dict[str, Any]], keys: tuple[str, ...]
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups["|".join(str(row[key]) for key in keys)].append(row)
    return groups


def allowance(total: int, share: float, minimum: int = 0) -> int:
    return max(minimum, math.floor(total * share))


def add_excess(
    members: list[dict[str, Any]],
    keep: int,
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
    for row in ordered[keep:]:
        reasons[row["source_asset_id"]].add(reason)


def formula_excess(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    reasons: dict[str, set[str]] = defaultdict(set)
    for key, keep, reason in (
        ("full_fingerprint", 2, "FORMULA_FULL_FINGERPRINT_REUSE"),
        ("normalized_opening_stem", 2, "FORMULA_OPENING_STEM_REUSE"),
        ("normalized_closing_stem", 2, "FORMULA_CLOSING_STEM_REUSE"),
    ):
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row["rhetorical"][key])].append(row)
        for members in groups.values():
            if len(members) > keep:
                add_excess(members, keep, reason, reasons)
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
            keep = allowance(
                len(platform_rows), share, 2 if dimension != "move_sequence" else 0
            )
            for members in groups.values():
                if len(members) > keep:
                    add_excess(members, keep, reason, reasons)
    for cell, cell_rows in group_rows(rows, ("p0_group", "platform_target")).items():
        for dimension, reason in (
            ("opening_family", "FORMULA_OPENING_FAMILY_CELL"),
            ("closing_family", "FORMULA_CLOSING_FAMILY_CELL"),
        ):
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in cell_rows:
                groups[str(row["rhetorical"]["payload"][dimension])].append(row)
            keep = allowance(len(cell_rows), 0.30, 2)
            for members in groups.values():
                if len(members) > keep:
                    add_excess(members, keep, f"{reason}:{cell}", reasons)
        keep = allowance(len(cell_rows), 0.25)
        sequential = [
            row
            for row in cell_rows
            if row["rhetorical"]["payload"]["sequential_first_then"]
        ]
        negation = [
            row
            for row in cell_rows
            if row["rhetorical"]["payload"]["negation_dominant_body"]
        ]
        if len(sequential) > keep:
            add_excess(sequential, keep, f"FORMULA_SEQUENTIAL_CELL:{cell}", reasons)
        if len(negation) > keep:
            add_excess(negation, keep, f"FORMULA_NEGATION_CELL:{cell}", reasons)
    for key, share, reason in (
        ("sequential_first_then", 0.20, "FORMULA_SEQUENTIAL_OVERALL"),
        ("negation_dominant_body", 0.20, "FORMULA_NEGATION_OVERALL"),
    ):
        members = [row for row in rows if row["rhetorical"]["payload"][key]]
        keep = allowance(len(rows), share)
        if len(members) > keep:
            add_excess(members, keep, reason, reasons)
    final_boundary = [
        row for row in rows if row["claim_route"]["boundary_placement"] == "final_move"
    ]
    if len(final_boundary) > allowance(len(rows), 0.20):
        add_excess(
            final_boundary,
            allowance(len(rows), 0.20),
            "FORMULA_BOUNDARY_FINAL_OVERALL",
            reasons,
        )
    generic = [
        row
        for row in rows
        if row["claim_route"]["visible_boundary_family"] == "generic_or_low_risk"
    ]
    if len(generic) > allowance(len(rows), 0.10):
        add_excess(
            generic,
            allowance(len(rows), 0.10),
            "FORMULA_GENERIC_BOUNDARY_OVERALL",
            reasons,
        )
    douyin = [row for row in rows if row["platform_target"] == "douyin"]
    progressive = [
        row
        for row in douyin
        if row["rhetorical"]["payload"]["first_person_progressive"]
    ]
    if len(progressive) > allowance(len(douyin), 0.25):
        add_excess(
            progressive,
            allowance(len(douyin), 0.25),
            "FORMULA_DOUYIN_FIRST_PERSON_PROGRESSIVE",
            reasons,
        )
    moments = [row for row in rows if row["platform_target"] == "moments"]
    temporal = [
        row
        for row in moments
        if row["rhetorical"]["payload"]["opening_family"] == "temporal_work_scene"
    ]
    if len(temporal) > allowance(len(moments), 0.25):
        add_excess(
            temporal,
            allowance(len(moments), 0.25),
            "FORMULA_MOMENTS_TEMPORAL_OPENING",
            reasons,
        )
    return {asset_id: sorted(values) for asset_id, values in sorted(reasons.items())}


def false_readiness_paths(value: Any, prefix: str = "$") -> list[str]:
    failures: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            path = f"{prefix}.{key}"
            if key in READINESS_KEYS and nested is not False:
                failures.append(path)
            failures.extend(false_readiness_paths(nested, path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            failures.extend(false_readiness_paths(nested, f"{prefix}[{index}]"))
    return failures


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def load_bundle(root: Path) -> dict[str, Any]:
    out = root / OUT_REL
    return {
        "founder": read_jsonl(root / FOUNDER_REL),
        "repair80": read_jsonl(root / REPAIR_80_REL),
        "r80_bindings": read_jsonl(root / R80_BINDING_REL),
        "probe": read_jsonl(root / PROBE_REL),
        "contract": read_yaml(root / CONTRACT_REL)[
            "asset_semantic_integrity_and_expression_diversity_contract"
        ],
        "accepted": read_yaml(out / "accepted_guardian_and_founder_evidence.v0.1.yaml")[
            "accepted_guardian_and_founder_evidence"
        ],
        "source_manifest": read_yaml(out / "source_120_resolution_manifest.v0.1.yaml")[
            "source_120_resolution_manifest"
        ],
        "cross_before": read_jsonl(out / "cross_layer_audit_before.v0.1.jsonl"),
        "rhetoric_before": read_jsonl(out / "rhetorical_audit_before.v0.1.jsonl"),
        "claim_before": read_jsonl(out / "claim_boundary_route_index.v0.1.jsonl"),
        "freeze": read_yaml(root / FREEZE_REL)["repair_set_freeze"],
        "workorder": read_yaml(out / "repair_workorder.v0.1.yaml")["repair_workorder"],
        "variants": read_jsonl(out / "repair_variants.v0.1.jsonl"),
        "actor_index": read_jsonl(out / "actor_event_consistency_index.v0.1.jsonl"),
        "rhetoric_index": read_jsonl(out / "rhetorical_fingerprint_index.v0.1.jsonl"),
        "distribution": read_yaml(
            out / "claim_boundary_surface_distribution.v0.1.yaml"
        )["claim_boundary_surface_distribution"],
        "resolved": read_jsonl(out / "resolved_120_manifest.v0.1.jsonl"),
        "gate": read_yaml(out / "final_120_machine_gate_result.v0.1.yaml")[
            "final_120_machine_gate_result"
        ],
        "guardian": read_yaml(out / "final_120_guardian_review_packet.v0.1.yaml")[
            "final_120_guardian_review_packet"
        ],
        "result": read_yaml(out / "final_120_result.v0.1.yaml")["final_120_result"],
        "receipt": json.loads((root / RECEIPT_REL).read_text(encoding="utf-8")),
    }


def source_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = {str(row["asset_id"]): row for row in bundle["r80_bindings"]}
    rows: list[dict[str, Any]] = []
    for source_kind, records, relative in (
        ("founder_40", bundle["founder"], FOUNDER_REL),
        ("repair_80", bundle["repair80"], REPAIR_80_REL),
    ):
        for raw in records:
            source_id = str(raw.get("repair_id") or raw.get("asset_id"))
            kernel_id = str(
                raw.get("bound_kernel_candidate_id") or raw.get("kernel_id")
            )
            p0_group = str(raw.get("p0_group") or raw.get("capability_group"))
            binding = bindings.get(source_id)
            fact_digest = (
                str(binding["fact_boundary_digest"])
                if binding
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
                    "event_binding_state": "bounded_routine_work_prototype",
                    "fact_boundary_digest": fact_digest,
                    "content_kernel": raw.get("content_kernel", {}),
                    "body_text": str(raw.get("body_text", "")),
                }
            )
    rows.sort(key=lambda row: (row["cluster_id"], row["kernel_id"]))
    return rows


def validate_freeze(bundle: dict[str, Any], root: Path, errors: list[str]) -> None:
    freeze = bundle["freeze"]
    require(
        errors, freeze.get("baseline_head") == BASELINE_HEAD, "freeze baseline drift"
    )
    require(
        errors,
        freeze.get("frozen_before_first_repair") is True,
        "repair set not frozen first",
    )
    require(
        errors,
        freeze.get("first_repair_started") is False,
        "freeze mutated after repair",
    )
    require(
        errors,
        freeze.get("contract_digest") == file_digest(root / CONTRACT_REL),
        "contract changed after freeze",
    )
    require(
        errors,
        freeze.get("runner_digest") == file_digest(root / RUNNER_REL),
        "runner changed after freeze",
    )
    require(
        errors, freeze.get("known_C_set") == sorted(KNOWN_C), "known C freeze drift"
    )
    require(
        errors, freeze.get("repair_asset_count") == 114, "frozen repair count drift"
    )
    require(
        errors, freeze.get("source_asset_count") == 120, "frozen source count drift"
    )
    recomputed_failure_digest = stable_digest(
        {
            "hard": freeze.get("cross_layer_hard_failure_set"),
            "ambiguity": freeze.get("semantic_ambiguity_set"),
            "claim": freeze.get("claim_boundary_mode_mismatch_set"),
            "formula": freeze.get("formula_excess_set"),
            "known_C": freeze.get("known_C_set"),
        }
    )
    require(
        errors,
        freeze.get("failure_set_digest") == recomputed_failure_digest,
        "failure-set digest drift",
    )
    workorder = bundle["workorder"]
    require(
        errors,
        workorder.get("frozen_failure_set_digest") == freeze.get("failure_set_digest"),
        "workorder does not consume freeze",
    )
    entries = workorder.get("entries", [])
    require(
        errors,
        workorder.get("workorder_count") == 114 and len(entries) == 114,
        "workorder count drift",
    )
    require(
        errors,
        {row.get("source_asset_id") for row in entries}
        == set(freeze.get("repair_asset_ids", [])),
        "workorder/frozen IDs drift",
    )


def longest_common_substring(left: str, right: str, cap: int = 40) -> int:
    a, b = normalize(left), normalize(right)
    for width in range(min(cap, len(a), len(b)), 0, -1):
        if any(b[index : index + width] in a for index in range(len(b) - width + 1)):
            return width
    return 0


def kernel_segments(kernel: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "object_anchor",
        "business_judgment",
        "tradeoff_or_tension",
        "spoken_line_seed",
        "output_asset_hint",
    ):
        if isinstance(kernel.get(key), str):
            values.append(str(kernel[key]))
    for key in ("human_subject", "human_action", "scene_premise"):
        value = kernel.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif isinstance(value, str):
            values.append(value)
    return values


def validate_bundle(bundle: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    accepted = bundle["accepted"]
    require(
        errors,
        accepted.get("claude_code_guardian", {}).get("verdict") == "PASS_WITH_CAVEAT",
        "accepted Guardian verdict drift",
    )
    require(
        errors,
        accepted.get("latest_founder_review", {}).get("reviewed_asset_scope")
        == "repair_validation_80_not_combined_120",
        "Founder 80-grade scope misrepresented as 120",
    )
    require(
        errors,
        {
            key: accepted.get("latest_founder_review", {}).get(key)
            for key in ("A", "B", "C", "D")
        }
        == {"A": 54, "B": 22, "C": 4, "D": 0},
        "accepted Founder distribution drift",
    )
    sources = source_rows(bundle)
    require(errors, len(sources) == 120, "source count is not 120")
    require(
        errors,
        len({row["kernel_id"] for row in sources}) == 120,
        "source kernels not unique",
    )
    require(
        errors,
        Counter(row["source_kind"] for row in sources)
        == {"founder_40": 40, "repair_80": 80},
        "source 40+80 split drift",
    )
    source_by_id = {row["source_asset_id"]: row for row in sources}
    manifest = bundle["source_manifest"]
    expected_manifest = [
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
        for row in sources
    ]
    require(
        errors,
        manifest.get("entries") == expected_manifest,
        "source manifest differs from recompute",
    )
    require(
        errors,
        manifest.get("manifest_digest") == stable_digest(expected_manifest),
        "source manifest digest drift",
    )

    variants = bundle["variants"]
    resolved = bundle["resolved"]
    require(errors, len(variants) == 114, "repair variant count drift")
    require(errors, len(resolved) == 120, "resolved count drift")
    require(
        errors,
        len({row.get("kernel_id") for row in resolved}) == 120,
        "resolved kernels not unique",
    )
    require(
        errors,
        {row.get("source_asset_id") for row in variants}
        == set(bundle["freeze"].get("repair_asset_ids", [])),
        "variants differ from frozen repair set",
    )
    require(
        errors,
        KNOWN_C <= {row.get("source_asset_id") for row in variants},
        "known 4C not repaired",
    )
    variant_by_id = {str(row["source_asset_id"]): row for row in variants}
    actor_by_id = {str(row["source_asset_id"]): row for row in bundle["actor_index"]}
    rhetoric_by_id = {
        str(row["source_asset_id"]): row for row in bundle["rhetoric_index"]
    }
    bodies: list[str] = []
    normalized_bodies: list[str] = []
    final_rows: list[dict[str, Any]] = []
    hard_event_ids: list[str] = []
    route_mismatch_ids: list[str] = []
    unsupported_ids: list[str] = []
    max_kernel_overlap = 0
    kernel_overlap_blocker_ids: list[str] = []
    for record in resolved:
        source_id = str(record.get("source_asset_id"))
        source = source_by_id.get(source_id, {})
        effective = record.get("effective_asset", {})
        body = str(effective.get("body_text", ""))
        require(
            errors,
            record.get("source_asset_digest") == source.get("source_asset_digest"),
            f"source digest drift: {source_id}",
        )
        require(
            errors,
            effective.get("kernel_id") == source.get("kernel_id"),
            f"kernel binding drift: {source_id}",
        )
        require(
            errors,
            effective.get("authoritative_kernel_digest")
            == stable_digest(source.get("content_kernel", {})),
            f"kernel truth changed: {source_id}",
        )
        require(
            errors,
            effective.get("content_kernel") == source.get("content_kernel"),
            f"content kernel changed: {source_id}",
        )
        require(
            errors,
            effective.get("fact_boundary_digest") == source.get("fact_boundary_digest"),
            f"fact binding changed: {source_id}",
        )
        require(
            errors,
            effective.get("body_digest")
            == hashlib.sha256(body.encode("utf-8")).hexdigest(),
            f"body digest drift: {source_id}",
        )
        require(
            errors,
            effective.get("knowledge_count_increment") == 0
            and effective.get("creates_new_knowledge") is False,
            f"knowledge inflation: {source_id}",
        )
        require(
            errors,
            effective.get("candidatepack_ready") is False
            and effective.get("production_servable") is False,
            f"readiness true: {source_id}",
        )
        require(
            errors,
            effective.get("all_readiness_false") is True,
            f"readiness summary drift: {source_id}",
        )
        if source_id in variant_by_id:
            require(
                errors,
                effective == variant_by_id[source_id],
                f"resolved variant mismatch: {source_id}",
            )
        else:
            require(
                errors,
                record.get("resolution_status") == "unchanged",
                f"untracked repair: {source_id}",
            )
            require(
                errors,
                body == source.get("body_text"),
                f"unchanged body drift: {source_id}",
            )
        binding = effective.get("cross_layer_semantic_binding", {})
        require(
            errors,
            actor_by_id.get(source_id, {}).get("cross_layer_semantic_binding")
            == binding,
            f"actor index drift: {source_id}",
        )
        event = binding.get("event_binding", {})
        trigger_span = str(event.get("event_trigger_body_span", ""))
        require(
            errors,
            trigger_span and trigger_span in body,
            f"event span missing: {source_id}",
        )
        for action in event.get("event_action_bindings", []):
            require(
                errors,
                str(action.get("body_evidence_span", "")) in body,
                f"action span missing: {source_id}",
            )
        participant = binding.get("participant_and_execution", {})
        slots = participant.get("participant_slots", [])
        require(
            errors,
            participant.get("natural_work_participant_count") == len(slots),
            f"participant count drift: {source_id}",
        )
        require(
            errors,
            participant.get("content_only_participant_count") == 0
            and participant.get("hired_performer_count") == 0
            and participant.get("dedicated_production_crew_count") == 0,
            f"daily-native staging: {source_id}",
        )
        require(
            errors,
            participant.get("minimum_people_present") == len(slots),
            f"minimum people drift: {source_id}",
        )
        require(
            errors,
            participant.get("model_participation", {}).get("status")
            != "hired_professional_model",
            f"hired model in daily-native: {source_id}",
        )
        execution = effective.get("execution_card_overlay", {})
        require(
            errors,
            stable_digest(execution)
            == binding.get("asset_ref", {}).get("execution_card_digest"),
            f"execution digest drift: {source_id}",
        )
        payload = effective.get("platform_payload", {})
        require(
            errors,
            stable_digest(payload)
            == binding.get("asset_ref", {}).get("platform_payload_digest"),
            f"platform payload digest drift: {source_id}",
        )
        if ACTUAL_PROTOTYPE_PATTERN.search(body):
            hard_event_ids.append(source_id)
        route = claim_route(body)
        require(
            errors,
            effective.get("claim_boundary_expression") == route,
            f"claim route report drift: {source_id}",
        )
        if not route["route_match"]:
            route_mismatch_ids.append(source_id)
        if UNSUPPORTED_CLAIM_PATTERN.search(body):
            unsupported_ids.append(source_id)
        rhetoric = rhetorical_fingerprint(
            body,
            str(effective.get("p0_group")),
            str(effective.get("cluster_id")),
            str(effective.get("platform_target")),
            route,
        )
        require(
            errors,
            effective.get("rhetorical_fingerprint") == rhetoric,
            f"rhetorical fingerprint drift: {source_id}",
        )
        require(
            errors,
            rhetoric_by_id.get(source_id, {}).get("full_fingerprint")
            == rhetoric["full_fingerprint"],
            f"rhetorical index drift: {source_id}",
        )
        overlap = max(
            (
                longest_common_substring(body, segment)
                for segment in kernel_segments(source.get("content_kernel", {}))
            ),
            default=0,
        )
        max_kernel_overlap = max(max_kernel_overlap, overlap)
        if overlap > 17:
            kernel_overlap_blocker_ids.append(source_id)
        bodies.append(body)
        normalized_bodies.append(normalize(body))
        final_rows.append(
            {
                "source_asset_id": source_id,
                "p0_group": effective.get("p0_group"),
                "platform_target": effective.get("platform_target"),
                "claim_route": route,
                "rhetorical": rhetoric,
            }
        )
    final_formula = formula_excess(final_rows)
    gate = bundle["gate"]
    metrics = gate.get("metrics", {})
    require(
        errors,
        sorted(hard_event_ids)
        == sorted(["P7D40-REPAIR-151", "RV80-ASSET-008", "RV80-ASSET-070"]),
        "remaining event mismatch set drift",
    )
    require(
        errors,
        sorted(route_mismatch_ids)
        == sorted(
            ["P7D40-REPAIR-097", "RV80-ASSET-018", "RV80-ASSET-068", "RV80-ASSET-078"]
        ),
        "remaining claim mismatch set drift",
    )
    require(
        errors, unsupported_ids == ["P7D40-REPAIR-040"], "unsupported claim set drift"
    )
    require(
        errors,
        gate.get("final_formula_blockers") == final_formula
        and len(final_formula) == 69,
        "final formula blockers differ from recompute",
    )
    require(
        errors,
        metrics.get("cross_layer_hard_failure_count") == len(hard_event_ids),
        "cross-layer metric lie",
    )
    require(
        errors,
        metrics.get("claim_boundary_route_mismatch_count") == len(route_mismatch_ids),
        "claim metric lie",
    )
    require(
        errors,
        metrics.get("unsupported_claim_count") == len(unsupported_ids),
        "unsupported metric lie",
    )
    require(
        errors,
        metrics.get("corpus_concentration_blocker_count") == len(final_formula),
        "formula metric lie",
    )
    require(
        errors,
        metrics.get("exact_duplicate_count") == len(bodies) - len(set(bodies)),
        "exact duplicate metric lie",
    )
    require(
        errors,
        metrics.get("normalized_duplicate_count")
        == len(normalized_bodies) - len(set(normalized_bodies)),
        "normalized duplicate metric lie",
    )
    expected_overlap_blockers = [
        "RV80-ASSET-043",
        "RV80-ASSET-052",
        "RV80-ASSET-056",
        "RV80-ASSET-063",
        "RV80-ASSET-070",
        "RV80-ASSET-075",
    ]
    require(
        errors,
        kernel_overlap_blocker_ids == expected_overlap_blockers
        and max_kernel_overlap == 19,
        "kernel-overlap blocker set drift",
    )
    require(
        errors,
        gate.get("machine_composite_gate") == "FAIL",
        "partial machine gate rewritten PASS",
    )
    result = bundle["result"]
    require(
        errors,
        result.get("result_status") == "PARTIAL_REPAIR_BLOCKED",
        "partial result overclaim",
    )
    require(
        errors,
        result.get("machine_composite_gate") == "FAIL",
        "result machine gate overclaim",
    )
    require(
        errors,
        result.get("claude_code_domain_review") == "PENDING",
        "guardian review prefilled",
    )
    require(
        errors,
        result.get("fact_safety_reduced_for_diversity") is False,
        "fact safety reduced",
    )
    require(
        errors,
        result.get("independent_checker_additional_blockers")
        == {
            "kernel_overlap": {
                "threshold": 17,
                "blocker_count": 6,
                "max_overlap": 19,
                "source_asset_ids": expected_overlap_blockers,
            }
        },
        "independent kernel-overlap blocker hidden",
    )
    require(
        errors,
        result.get("expand_600") is False and result.get("expand_3600") is False,
        "scale unlocked",
    )
    require(
        errors,
        all(value == "BLOCKED" for value in result.get("downstream", {}).values()),
        "downstream unblocked",
    )
    receipt = bundle["receipt"]
    require(
        errors,
        receipt.get("result_status") == "PARTIAL_REPAIR_BLOCKED",
        "receipt result overclaim",
    )
    require(
        errors,
        receipt.get("machine_composite_gate") == "FAIL",
        "receipt machine gate overclaim",
    )
    require(
        errors,
        receipt.get("remaining_blockers")
        == {
            "event_depiction_mismatch_count": 3,
            "claim_route_mismatch_count": 4,
            "unsupported_claim_count": 1,
            "formula_blocker_asset_count": 69,
            "kernel_overlap_blocker_count": 6,
            "kernel_overlap_max": 19,
            "kernel_overlap_blocker_ids": expected_overlap_blockers,
        },
        "receipt blocker summary drift",
    )
    require(
        errors, receipt.get("readiness_all_false") is True, "receipt readiness drift"
    )
    require(
        errors,
        receipt.get("expand_600") is False and receipt.get("expand_3600") is False,
        "receipt scale unlocked",
    )
    guardian = bundle["guardian"]
    require(
        errors,
        guardian.get("entry_count") == 120 and len(guardian.get("entries", [])) == 120,
        "guardian packet count drift",
    )
    require(
        errors,
        guardian.get("claude_code_domain_review") == "PENDING",
        "guardian packet prefilled",
    )
    require(
        errors,
        all(
            entry.get("guardian_grade") is None for entry in guardian.get("entries", [])
        ),
        "guardian grade prefilled",
    )
    errors.extend(f"readiness true: {path}" for path in false_readiness_paths(bundle))
    return sorted(set(errors)), {
        "source_asset_count": len(sources),
        "repair_variant_count": len(variants),
        "resolved_asset_count": len(resolved),
        "remaining_event_depiction_mismatch_count": len(hard_event_ids),
        "remaining_claim_route_mismatch_count": len(route_mismatch_ids),
        "remaining_unsupported_claim_count": len(unsupported_ids),
        "remaining_formula_blocker_count": len(final_formula),
        "remaining_kernel_overlap_blocker_count": len(kernel_overlap_blocker_ids),
        "kernel_overlap_blocker_ids": kernel_overlap_blocker_ids,
        "kernel_overlap_max": max_kernel_overlap,
        "exact_duplicate_count": len(bodies) - len(set(bodies)),
        "normalized_duplicate_count": len(normalized_bodies)
        - len(set(normalized_bodies)),
    }


def validate_parent_assets(root: Path, errors: list[str]) -> None:
    for relative in (FOUNDER_REL, REPAIR_80_REL, R80_BINDING_REL, PROBE_REL):
        current = root / relative
        require(errors, current.is_file(), f"parent missing: {relative}")
        if not current.is_file():
            continue
        baseline_blob = git_text(
            root, "rev-parse", f"{BASELINE_HEAD}:{relative}"
        ).strip()
        current_blob = git_text(
            root, "hash-object", f"--path={relative}", relative
        ).strip()
        require(errors, current_blob == baseline_blob, f"parent modified: {relative}")


def validate_ledger(root: Path, errors: list[str]) -> None:
    current = read_yaml(root / LEDGER_REL)["grc_3600_execution_plan_status"]
    baseline = yaml.safe_load(git_text(root, "show", f"{BASELINE_HEAD}:{LEDGER_REL}"))[
        "grc_3600_execution_plan_status"
    ]
    require(errors, "route_migration_13" in current, "route_migration_13 missing")
    stripped = copy.deepcopy(current)
    migration = stripped.pop("route_migration_13", None)
    require(errors, stripped == baseline, "ledger changed outside route_migration_13")
    expected = {
        "applied_by_task": TASK_ID,
        "applied_from": "founder_authorized_after_claude_code_prompt_pre_review_conditional_pass",
        "operational_state_only": True,
        "no_existing_step_status_changed": True,
        "no_old_checker_edited": True,
        "no_readiness_flipped": True,
        "result": "PARTIAL_REPAIR_BLOCKED",
        "result_path": f"{OUT_REL}/final_120_result.v0.1.yaml",
        "source_asset_count": 120,
        "repair_variant_count": 114,
        "resolved_asset_count": 120,
        "known_4C_repaired_count": 4,
        "remaining_event_depiction_mismatch_count": 3,
        "remaining_claim_route_mismatch_count": 4,
        "remaining_unsupported_claim_count": 1,
        "remaining_formula_blocker_count": 69,
        "remaining_kernel_overlap_blocker_count": 6,
        "kernel_overlap_max": 19,
        "knowledge_count_increment": 0,
        "fact_safety_reduced_for_diversity": False,
        "claude_code_domain_review": "PENDING",
        "expand_600": False,
        "expand_3600": False,
        "next_action": "CLAUDE_CODE_GUARDIAN_REVIEW_PARTIAL_120_AND_BLOCKER_CONFIRMATION",
        "preserved_status_literals": {
            "P7C-AB": "NEXT",
            "P7C_SCALE": "BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY",
            "P7C_SCALE_PREP": "DONE",
            "P7D": "BLOCKED_BY_P7C_SCALE_DECISION",
            "P8": "BLOCKED_BY_P7D",
        },
    }
    require(errors, migration == expected, "route_migration_13 content drift")
    errors.extend(
        f"ledger readiness true: {path}" for path in false_readiness_paths(current)
    )
    baseline_md = git_text(root, "show", f"{BASELINE_HEAD}:{LEDGER_MD_REL}")
    current_md = (root / LEDGER_MD_REL).read_text(encoding="utf-8")
    require(
        errors,
        current_md.startswith(baseline_md),
        "ledger markdown changed before appendix",
    )
    require(
        errors,
        "## P7D Final-120 Semantic Repair" in current_md[len(baseline_md) :],
        "ledger markdown appendix missing",
    )


def validate_repository(root: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    require(
        errors,
        git_text(root, "branch", "--show-current").strip() == "master",
        "branch must be master",
    )
    ancestor = run_git(
        root, "merge-base", "--is-ancestor", BASELINE_HEAD, "HEAD", check=False
    )
    require(errors, ancestor.returncode == 0, "baseline is not ancestor of HEAD")
    try:
        bundle = load_bundle(root)
        validate_freeze(bundle, root, errors)
        bundle_errors, metrics = validate_bundle(bundle)
        errors.extend(bundle_errors)
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        errors.append(f"structured validation failed: {exc}")
        metrics = {}
    validate_parent_assets(root, errors)
    try:
        validate_ledger(root, errors)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append(f"ledger validation failed: {exc}")
    require(errors, (root / FIXTURE_REL).is_file(), "fixture manifest missing")
    require(errors, (root / DOC_REPORT_REL).is_file(), "human report missing")
    for path in changed_paths(root):
        require(
            errors,
            any(
                path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES
            ),
            f"changed path outside allowlist: {path}",
        )
    return sorted(set(errors)), metrics


Mutation = Callable[[dict[str, Any]], None]


def selftest_cases() -> list[tuple[str, Mutation]]:
    def remove_source(bundle: dict[str, Any]) -> None:
        bundle["source_manifest"]["entries"].pop()

    def duplicate_kernel(bundle: dict[str, Any]) -> None:
        bundle["resolved"][1]["kernel_id"] = bundle["resolved"][0]["kernel_id"]

    def remove_known_c(bundle: dict[str, Any]) -> None:
        bundle["freeze"]["known_C_set"].pop()

    def contract_digest(bundle: dict[str, Any]) -> None:
        bundle["freeze"]["contract_digest"] = "0" * 64

    def failure_digest(bundle: dict[str, Any]) -> None:
        bundle["freeze"]["failure_set_digest"] = "0" * 64

    def workorder_count(bundle: dict[str, Any]) -> None:
        bundle["workorder"]["workorder_count"] = 113

    def remove_variant(bundle: dict[str, Any]) -> None:
        bundle["variants"].pop()

    def remove_resolved(bundle: dict[str, Any]) -> None:
        bundle["resolved"].pop()

    def kernel_drift(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["content_kernel"]["object_anchor"] = (
            "invented"
        )

    def fact_digest_drift(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["fact_boundary_digest"] = "0" * 64

    def event_span_missing(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["cross_layer_semantic_binding"][
            "event_binding"
        ]["event_trigger_body_span"] = "missing"

    def participant_count(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["cross_layer_semantic_binding"][
            "participant_and_execution"
        ]["minimum_people_present"] = 0

    def hired_model(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["cross_layer_semantic_binding"][
            "participant_and_execution"
        ]["model_participation"]["status"] = "hired_professional_model"

    def readiness_true(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["candidatepack_ready"] = True

    def knowledge_inflation(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["knowledge_count_increment"] = 1

    def guardian_prefill(bundle: dict[str, Any]) -> None:
        bundle["guardian"]["entries"][0]["guardian_grade"] = "A"

    def result_pass(bundle: dict[str, Any]) -> None:
        bundle["result"]["result_status"] = "FINAL_120_CONTENT_CONFIRMED"

    def machine_pass(bundle: dict[str, Any]) -> None:
        bundle["gate"]["machine_composite_gate"] = "PASS"

    def hide_event_failure(bundle: dict[str, Any]) -> None:
        bundle["gate"]["metrics"]["cross_layer_hard_failure_count"] = 0

    def hide_claim_failure(bundle: dict[str, Any]) -> None:
        bundle["gate"]["metrics"]["claim_boundary_route_mismatch_count"] = 0

    def hide_unsupported(bundle: dict[str, Any]) -> None:
        bundle["gate"]["metrics"]["unsupported_claim_count"] = 0

    def hide_formula(bundle: dict[str, Any]) -> None:
        bundle["gate"]["final_formula_blockers"] = {}

    def scale_true(bundle: dict[str, Any]) -> None:
        bundle["result"]["expand_600"] = True

    def downstream_true(bundle: dict[str, Any]) -> None:
        bundle["result"]["downstream"]["CandidatePack"] = "READY"

    def body_digest_drift(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["body_text"] += " changed"

    def rhetoric_drift(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["rhetorical_fingerprint"][
            "full_fingerprint"
        ] = "0" * 64

    def execution_digest_drift(bundle: dict[str, Any]) -> None:
        bundle["resolved"][0]["effective_asset"]["cross_layer_semantic_binding"][
            "asset_ref"
        ]["execution_card_digest"] = "0" * 64

    def kernel_overlap_blocker_hidden(bundle: dict[str, Any]) -> None:
        bundle["result"]["independent_checker_additional_blockers"] = {}

    def accepted_scope_drift(bundle: dict[str, Any]) -> None:
        bundle["accepted"]["latest_founder_review"]["reviewed_asset_scope"] = (
            "combined_120"
        )

    def receipt_overclaim(bundle: dict[str, Any]) -> None:
        bundle["receipt"]["machine_composite_gate"] = "PASS"

    return [
        ("source_count_mismatch", remove_source),
        ("duplicate_kernel", duplicate_kernel),
        ("known_C_missing", remove_known_c),
        ("contract_digest_drift", contract_digest),
        ("failure_set_digest_drift", failure_digest),
        ("workorder_count_drift", workorder_count),
        ("variant_count_mismatch", remove_variant),
        ("resolved_count_mismatch", remove_resolved),
        ("kernel_truth_drift", kernel_drift),
        ("fact_binding_drift", fact_digest_drift),
        ("event_span_missing", event_span_missing),
        ("participant_count_conflict", participant_count),
        ("hired_model_daily_native", hired_model),
        ("readiness_true", readiness_true),
        ("knowledge_inflation", knowledge_inflation),
        ("guardian_prefilled", guardian_prefill),
        ("result_overclaim", result_pass),
        ("machine_gate_false_green", machine_pass),
        ("event_failure_hidden", hide_event_failure),
        ("claim_failure_hidden", hide_claim_failure),
        ("unsupported_claim_hidden", hide_unsupported),
        ("formula_blockers_hidden", hide_formula),
        ("scale_unlocked", scale_true),
        ("downstream_unblocked", downstream_true),
        ("body_digest_drift", body_digest_drift),
        ("rhetorical_fingerprint_drift", rhetoric_drift),
        ("execution_digest_drift", execution_digest_drift),
        ("kernel_overlap_blocker_hidden", kernel_overlap_blocker_hidden),
        ("accepted_review_scope_drift", accepted_scope_drift),
        ("receipt_overclaim", receipt_overclaim),
    ]


def run_selftest(root: Path) -> tuple[bool, dict[str, Any]]:
    try:
        bundle = load_bundle(root)
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        return False, {
            "status": "FAIL",
            "reason": f"cannot load positive bundle: {exc}",
        }
    positive_candidate = copy.deepcopy(bundle)
    positive_errors: list[str] = []
    validate_freeze(positive_candidate, root, positive_errors)
    bundle_errors, _ = validate_bundle(positive_candidate)
    positive_errors.extend(bundle_errors)
    failures: list[str] = []
    observed: list[str] = []
    if positive_errors:
        failures.append(f"positive fixture failed: {positive_errors}")
    for name, mutate in selftest_cases():
        candidate = copy.deepcopy(bundle)
        mutate(candidate)
        case_errors: list[str] = []
        validate_freeze(candidate, root, case_errors)
        candidate_errors, _ = validate_bundle(candidate)
        case_errors.extend(candidate_errors)
        if case_errors:
            observed.append(name)
        else:
            failures.append(f"negative fixture escaped: {name}")
    try:
        json.loads("{malformed")
        failures.append("malformed JSON escaped")
    except json.JSONDecodeError:
        observed.append("malformed_json")
    fixture = read_yaml(root / FIXTURE_REL)["p7d_final_120_semantic_repair_selftest"]
    if set(fixture.get("negative_cases", [])) != set(observed):
        failures.append("fixture manifest/selftest case drift")
    return not failures, {
        "status": "PASS" if not failures else "FAIL",
        "positive_fixture": "PASS" if not positive_errors else "FAIL",
        "negative_case_count": len(observed),
        "negative_cases": observed,
        "failures": failures,
    }


def write_report(root: Path, errors: list[str], metrics: dict[str, Any]) -> None:
    report = {
        "task_id": TASK_ID,
        "baseline_head": BASELINE_HEAD,
        "checker_status": "PASS" if not errors else "FAIL",
        "execution_result_status": "PARTIAL_REPAIR_BLOCKED",
        "error_count": len(errors),
        "errors": errors,
        "independently_recomputed_metrics": metrics,
        "result_scope": "partial_integrity_confirmed_not_content_or_scale_pass",
    }
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not __debug__:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "python_optimized_mode"}))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "yaml_unavailable"}))
        return 2
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.selftest:
        passed, payload = run_selftest(root)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if passed else 1
    errors, metrics = validate_repository(root)
    write_report(root, errors, metrics)
    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "checker_status": "PASS" if not errors else "FAIL",
                "execution_result_status": "PARTIAL_REPAIR_BLOCKED",
                "error_count": len(errors),
                "errors": errors,
                "metrics": metrics,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
