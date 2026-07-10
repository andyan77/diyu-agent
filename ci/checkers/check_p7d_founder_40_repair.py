#!/usr/bin/env python3
"""Fail-closed checker for the scoped P7D founder-40 creative repair."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


TASK_ID = "GKB-P7D-FOUNDER-40-CREATIVE-REPAIR-AND-SCOPED-GATE-PATCH-001"
BASELINE_HEAD = "4d5ce09cda5909bdc3ba6b1b8c8f8921099e8250"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
MID_REL = f"{RUN_REL}/midbatch_320_001"
OUT_REL = f"{MID_REL}/founder_40_repair_001"
PACKET_REL = f"{MID_REL}/midbatch_320_founder_review_packet.v0.1.yaml"
KERNEL_REL = f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml"
REVIEW_KERNEL_REL = f"{RUN_REL}/content_kernel_extraction/review_packet_kernel_matrix.v0.1.yaml"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
LEDGER_MD_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"
REPORT_REL = "ci/reports/p7d_founder_40_repair_report.v0.1.json"
FIXTURE_REL = "ci/fixtures/p7d_founder_40_repair/fixture_manifest.v0.1.yaml"

REQUIRED_ARTIFACTS = (
    "accepted_review_evidence.v0.1.yaml",
    "founder_40_repair_contract.v0.1.yaml",
    "founder_40_scoped_prompt_patch.v0.1.md",
    "founder_40_original_to_repair_map.v0.1.yaml",
    "founder_40_repaired_assets.v0.1.jsonl",
    "founder_40_before_after_review_packet.v0.1.yaml",
    "founder_40_content_layer_audit.v0.1.yaml",
    "founder_40_capture_mode_quota.v0.1.yaml",
    "founder_40_platform_account_matrix.v0.1.yaml",
    "founder_40_role_action_gate_result.v0.1.yaml",
    "founder_40_skeleton_fingerprint_index.v0.1.jsonl",
    "founder_40_skeleton_gate_result.v0.1.yaml",
    "founder_40_kernel_overlap_report.v0.1.yaml",
    "founder_40_repair_result.v0.1.yaml",
    "p7d_320_generation_label_correction_overlay.v0.1.yaml",
)

CLASS_IDS = {
    "A": {
        "P7D320-OUT-021", "P7D320-OUT-040", "P7D320-OUT-082",
        "P7D320-OUT-089", "P7D320-OUT-097", "P7D320-OUT-115",
        "P7D320-OUT-129", "P7D320-OUT-154", "P7D320-OUT-202",
        "P7D320-OUT-224", "P7D320-OUT-298", "P7D320-OUT-312",
    },
    "B": {
        "P7D320-OUT-006", "P7D320-OUT-054", "P7D320-OUT-063",
        "P7D320-OUT-071", "P7D320-OUT-077", "P7D320-OUT-105",
        "P7D320-OUT-127", "P7D320-OUT-151", "P7D320-OUT-162",
        "P7D320-OUT-177", "P7D320-OUT-214", "P7D320-OUT-234",
        "P7D320-OUT-263", "P7D320-OUT-276", "P7D320-OUT-287",
        "P7D320-OUT-289",
    },
    "C": {
        "P7D320-OUT-030", "P7D320-OUT-048", "P7D320-OUT-138",
        "P7D320-OUT-170", "P7D320-OUT-191", "P7D320-OUT-254",
        "P7D320-OUT-316",
    },
    "D": {
        "P7D320-OUT-012", "P7D320-OUT-195", "P7D320-OUT-226",
        "P7D320-OUT-243", "P7D320-OUT-267",
    },
}

PLATFORMS = {"douyin", "xiaohongshu", "wechat_channels", "moments", "live"}
ACCOUNT_ROLES = {"brand_headquarters", "founder", "store", "store_manager", "sales_associate"}
CAPTURE_MODES = {"daily_native", "lightly_guided", "campaign_directed"}
P0_GROUPS = {"P0_01", "P0_02", "P0_03", "P0_04", "P0_05"}
READINESS_KEYS = {
    "candidatepack_ready", "KE_ready", "Serving_ready", "RAG_ready",
    "DIFY_ready", "production_servable", "generation_eligible",
    "generation_allowed", "release_ready", "production_ready",
}
BODY_GOVERNANCE_MARKERS = (
    "这是一段可拍原型", "不把原型伪装", "发布前补齐", "待绑定事实",
    "角色称呼待替换", "现场仍需核对", "资料接入", "source gap",
    "readiness", "CandidatePack", "KE_ready", "RAG", "DIFY",
    "production_servable", "【", "】",
)
BODY_DIRECTOR_MARKERS = (
    "镜头", "机位", "提词卡", "环境声", "片尾", "配乐", "第一镜",
    "第二镜", "第三镜", "开拍", "收尾", "画面",
)
FORBIDDEN_ROLE_PATTERNS = (
    r"顾客.{0,5}(调整橱窗|整理货架|陈列执行|工艺复核|证明工艺|负责陈列|处理橱窗)",
    r"模特.{0,5}(调整橱窗|负责陈列|复核工艺|处理橱窗)",
    r"老板.{0,5}(顺过橱窗|处理橱窗纹理)",
    r"版师.{0,5}(催顾客购买|代替导购成交)",
)
ALLOWED_PREFIXES = (
    f"{OUT_REL}/",
    "ci/checkers/check_p7d_founder_40_repair.py",
    "ci/fixtures/p7d_founder_40_repair/",
    REPORT_REL,
    LEDGER_REL,
    LEDGER_MD_REL,
    "docs/reports/p7d_founder_40_repair_report.md",
    "docs/reports/p7d_founder_40_repair_receipt.json",
)
FORBIDDEN_DIFF_PREFIXES = (
    "00_source_inputs/", "01_generation_contracts/", "02_generation_brief_pack/",
    "03_grc_goldset_corpus/", "03_pilot/", "04_judge_calibration/",
    "06_canary_runs/", "07_microbatch_briefing/", "08_batch_unlock_reconciliation/",
    "CandidatePack/", "KE/", "serving_projection/", "rag/", "RAG/",
    "dify/", "DIFY/", "candidatepack_etl/", "08_consolidated_outputs/",
    "09_candidatepack_eligibility/", "project-infra/",
)


def read_yaml(path: Path) -> Any:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if value is None:
        raise ValueError(f"empty YAML: {path}")
    return value


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL row {path}:{line_no}")
        rows.append(value)
    return rows


def normalize(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check
    )


def git_text(root: Path, *args: str) -> str:
    return run_git(root, *args).stdout.decode("utf-8", errors="replace")


def changed_paths(root: Path) -> set[str]:
    paths = {
        line.strip()
        for line in git_text(root, "diff", "--name-only", BASELINE_HEAD, "--").splitlines()
        if line.strip()
    }
    paths.update(
        line.strip()
        for line in git_text(root, "ls-files", "--others", "--exclude-standard").splitlines()
        if line.strip()
    )
    return paths


def expected_class(output_id: str) -> str:
    for class_name, ids in CLASS_IDS.items():
        if output_id in ids:
            return class_name
    raise KeyError(output_id)


def entry_type(body: str) -> str:
    first = re.split(r"[。！？]", body, maxsplit=1)[0]
    if "？" in body[:60] or first.startswith(("先别", "别急", "为什么")):
        return "question_or_challenge"
    if any(token in first for token in ("不是", "不必", "不能", "最怕")):
        return "contrast_claim"
    if any(token in first for token in ("时", "前", "后", "里", "会上", "间")):
        return "scene_action"
    if any(token in first for token in ("同一", "两件", "三个", "这一组", "一套")):
        return "comparison_or_set"
    return "object_assertion"


def object_category(text: str) -> str:
    if any(token in text for token in ("裤", "半裙")):
        return "bottom"
    if any(token in text for token in ("衬衫", "针织", "上装", "开衫")) and "外套" not in text:
        return "top"
    if any(token in text for token in ("陈列", "橱窗", "入口", "搭配", "组合", "Look", "货架")):
        return "display_or_look"
    return "outerwear"


def action_category(text: str) -> str:
    for category, tokens in (
        ("compare", ("比较", "并排", "对照")),
        ("inspect", ("检查", "复核", "观察", "查看", "翻看")),
        ("adjust", ("调整", "整理", "翻折", "收紧", "搭配")),
        ("explain", ("讲解", "说明", "回应", "引导")),
        ("handoff", ("交接", "接力", "分配")),
        ("try", ("试穿", "走动", "坐下")),
    ):
        if any(token in text for token in tokens):
            return category
    return "handle_object"


def conflict_category(text: str) -> str:
    for category, tokens in (
        ("claim_boundary", ("承诺", "结论", "认证", "效果", "证据", "性能")),
        ("role_boundary", ("岗位", "职责", "角色", "权限", "履历")),
        ("choice_tradeoff", ("取舍", "选择", "交期", "改动", "平衡")),
        ("scene_fit", ("场景", "任务", "空间", "动线", "生活")),
        ("expression_quality", ("口号", "形容词", "语气", "表达", "复述")),
    ):
        if any(token in text for token in tokens):
            return category
    return "content_focus"


def closing_type(body: str) -> str:
    last = re.split(r"[。！？]", body.rstrip("。！？"))[-1]
    if "？" in body[-60:]:
        return "open_question"
    if any(token in last for token in ("选择", "决定", "自己")):
        return "return_choice"
    if any(token in last for token in ("看", "细节", "结构", "实物")):
        return "return_observation"
    if any(token in last for token in ("结束", "完成", "收束", "位置", "任务")):
        return "complete_action"
    return "judgment_echo"


def recompute_skeleton(record: dict[str, Any]) -> dict[str, Any]:
    kernel = record["content_kernel"]
    metadata = record["review_metadata"]
    body = record["body_text"]
    return {
        "p0_group": record["p0_group"],
        "generation_mode": record["generation_mode"],
        "opening_type": entry_type(body),
        "opening_scene": record["narrative_skeleton"]["opening_scene"],
        "subject_role": kernel["human_subject"],
        "object_category": object_category(kernel["object_anchor"]),
        "first_action_category": action_category(kernel["human_action"]),
        "conflict_category": conflict_category(kernel["tradeoff_or_tension"]),
        "judgment_axis": record["narrative_skeleton"]["business_judgment"],
        "fact_boundary_move": metadata["fact_boundary_mode"],
        "closing_type": closing_type(body),
    }


def kernel_segments(row: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key in ("object_anchor", "business_judgment", "tradeoff_or_tension", "spoken_line_seed", "output_asset_hint"):
        value = row.get(key)
        if isinstance(value, str) and value:
            result.append(value)
    for key in ("human_subject", "human_action", "scene_premise"):
        value = row.get(key)
        if isinstance(value, list):
            result.extend(str(item) for item in value if item)
    return result


def build_overlap_index(segments: list[tuple[str, str]], max_size: int = 18) -> dict[int, dict[str, set[str]]]:
    index: dict[int, dict[str, set[str]]] = {
        size: defaultdict(set) for size in range(1, max_size + 1)
    }
    for source_id, segment in segments:
        value = normalize(segment)
        for size in range(1, min(max_size, len(value)) + 1):
            for offset in range(len(value) - size + 1):
                index[size][value[offset : offset + size]].add(source_id)
    return index


def max_overlap(body: str, index: dict[int, dict[str, set[str]]]) -> tuple[int, list[str], str]:
    value = normalize(body)
    for size in range(max(index), 0, -1):
        for offset in range(max(0, len(value) - size + 1)):
            fragment = value[offset : offset + size]
            matches = index[size].get(fragment)
            if matches:
                return size, sorted(matches), fragment
    return 0, [], ""


def review_kernel_segments(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    for row in rows:
        source_id = str(row["candidate_id"])
        for key in ("forbidden_claims", "evidence_boundary", "downgrade_path"):
            value = row.get(key)
            if isinstance(value, str):
                segments.append((source_id, value))
        for slot in row.get("required_fact_slots", []):
            if isinstance(slot, dict):
                for key in ("name", "family", "placeholder"):
                    value = slot.get(key)
                    if isinstance(value, str):
                        segments.append((source_id, value))
    return segments


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for nested in value.values():
            result.extend(flatten_strings(nested))
        return result
    if isinstance(value, list):
        result = []
        for nested in value:
            result.extend(flatten_strings(nested))
        return result
    return []


def validate_records(
    records: list[dict[str, Any]],
    source_kernels: list[dict[str, Any]],
    review_kernels: list[dict[str, Any]],
    expected_ids: set[str],
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    if len(records) != 40:
        errors.append(f"repair count must be 40, got {len(records)}")
    original_ids = [str(row.get("original_output_id", "")) for row in records]
    repair_ids = [str(row.get("repair_id", "")) for row in records]
    if set(original_ids) != expected_ids:
        errors.append("repair original IDs do not exactly match fixed founder sample")
    if len(original_ids) != len(set(original_ids)):
        errors.append("an original has more than one repaired variant")
    if len(repair_ids) != len(set(repair_ids)) or any(not item for item in repair_ids):
        errors.append("repair IDs must be present and unique")
    actual_classes = Counter(str(row.get("original_review_class", "")) for row in records)
    if actual_classes != Counter({"A": 12, "B": 16, "C": 7, "D": 5}):
        errors.append(f"review class counts differ: {dict(actual_classes)}")

    source_segments = [
        (str(row["candidate_id"]), segment)
        for row in source_kernels
        for segment in kernel_segments(row)
    ]
    source_index = build_overlap_index(source_segments)
    review_index = build_overlap_index(review_kernel_segments(review_kernels))
    source_overlap_observed = 0
    review_overlap_observed = 0
    fingerprints: list[str] = []
    bodies: list[str] = []
    norm_bodies: list[str] = []
    capture_counts: Counter[str] = Counter()
    platform_counts: Counter[str] = Counter()
    account_counts: Counter[str] = Counter()
    governance_hits = 0
    director_hits = 0
    role_failures = 0
    platform_review_queue = 0
    semantic_review_queue = 0

    required_kernel = {
        "human_subject", "object_anchor", "human_action", "scene_premise",
        "business_judgment", "tradeoff_or_tension", "spoken_line_seed",
    }
    p0_01_required = {
        "organization_choice", "long_term_tradeoff", "visible_product_trace",
        "founder_or_team_decision", "not_claimed_result", "safe_spoken_line",
    }
    p0_05_required = {
        "customer_task", "product_role", "scene_use_case", "trial_or_tryon_trigger",
        "safe_observation", "guide_next_line",
    }
    required_metadata = {
        "required_fact_slots", "forbidden_claims", "source_gap_notes",
        "authorization_boundary", "role_action_review", "platform_fit_review",
        "skeleton_review", "readiness_flags", "original_review_class",
        "recommended_route_after_repair", "human_review_required", "fact_boundary_mode",
    }
    required_card = {
        "who_shoots", "what_to_capture", "who_appears", "spoken_line", "do_not_say",
        "estimated_minutes", "crew_count", "equipment", "engagement_handoff",
        "facts_brand_must_confirm", "shot_count_max", "lighting",
        "forced_performance", "fictional_customer", "manufactured_conflict",
    }
    required_platform = {
        "platform_opening_move", "platform_rhythm", "engagement_or_conversion_move",
        "account_voice", "next_customer_action",
    }
    required_skeleton = {
        "opening_scene", "camera_entry", "human_subject", "object_anchor", "first_action",
        "conflict_or_question", "detail_focus", "business_judgment",
        "fact_boundary_move", "closing_move", "canonical_payload", "canonical_fingerprint",
    }

    for row in records:
        repair_id = str(row.get("repair_id", "<missing>"))
        if row.get("original_output_id") in expected_ids:
            expected = expected_class(str(row["original_output_id"]))
            if row.get("original_review_class") != expected:
                errors.append(f"{repair_id}: wrong founder review class")
            if expected == "A" and row.get("review_metadata", {}).get("original_review_class_meaning") != "优先修复的高价值 Content Kernel 候选":
                errors.append(f"{repair_id}: A class is overstated or mislabeled")
            if expected == "D":
                if row.get("repair_kind") != "full_rewrite":
                    errors.append(f"{repair_id}: D item was not fully rewritten")
                if row.get("review_metadata", {}).get("original_as_anti_gold") is not True:
                    errors.append(f"{repair_id}: D original not retained as anti-gold")
        for layer in ("body_text", "content_kernel", "review_metadata", "execution_card"):
            if layer not in row:
                errors.append(f"{repair_id}: missing layer {layer}")
        if any(layer not in row for layer in ("body_text", "content_kernel", "review_metadata", "execution_card")):
            continue
        body = row["body_text"]
        kernel = row["content_kernel"]
        metadata = row["review_metadata"]
        card = row["execution_card"]
        if not isinstance(body, str) or len(normalize(body)) < 80:
            errors.append(f"{repair_id}: body_text is not a complete readable body")
            body = str(body)
        bodies.append(body)
        norm_bodies.append(normalize(body))
        body_governance = [marker for marker in BODY_GOVERNANCE_MARKERS if marker in body]
        body_director = [marker for marker in BODY_DIRECTOR_MARKERS if marker in body]
        if body_governance:
            governance_hits += 1
            errors.append(f"{repair_id}: governance/fact-slot language in body: {body_governance}")
        if body_director:
            director_hits += 1
            errors.append(f"{repair_id}: director instructions in body: {body_director}")
        if not isinstance(kernel, dict) or not required_kernel.issubset(kernel):
            errors.append(f"{repair_id}: incomplete content_kernel")
            continue
        if not isinstance(metadata, dict) or not required_metadata.issubset(metadata):
            errors.append(f"{repair_id}: incomplete review_metadata")
            continue
        if not isinstance(card, dict) or not required_card.issubset(card):
            errors.append(f"{repair_id}: incomplete execution_card")
        if row.get("p0_group") not in P0_GROUPS:
            errors.append(f"{repair_id}: unknown P0 group")
        if row.get("p0_group") == "P0_01" and not p0_01_required.issubset(kernel):
            errors.append(f"{repair_id}: P0-01 enterprise kernel fields incomplete")
        if row.get("p0_group") == "P0_05" and not p0_05_required.issubset(kernel):
            errors.append(f"{repair_id}: P0-05 product-role kernel fields incomplete")
        if row.get("p0_group") == "P0_04" and kernel.get("scoped_subroute") not in {"display_method_fuel", "store_capture_fuel"}:
            errors.append(f"{repair_id}: invalid or missing P0-04 scoped subroute")
        for key in required_platform:
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(f"{repair_id}: platform expression field {key} missing")
        platform = str(row.get("platform_target", ""))
        account = str(row.get("account_role", ""))
        capture = str(row.get("capture_mode", ""))
        platform_counts[platform] += 1
        account_counts[account] += 1
        capture_counts[capture] += 1
        if platform not in PLATFORMS:
            errors.append(f"{repair_id}: unknown platform {platform}")
        if account not in ACCOUNT_ROLES:
            errors.append(f"{repair_id}: unknown account role {account}")
        if capture not in CAPTURE_MODES:
            errors.append(f"{repair_id}: unknown capture mode {capture}")
        if row.get("capture_mode_scope") != "scoped_repair_orchestration_only_not_ontology_or_formal_CSO_axis":
            errors.append(f"{repair_id}: capture mode was not scoped away from ontology/formal CSO")
        if capture == "campaign_directed" and row.get("p0_group") in {"P0_01", "P0_02"}:
            errors.append(f"{repair_id}: campaign-directed forbidden for P0-01/P0-02")
        if capture == "daily_native" and isinstance(card, dict):
            if card.get("crew_count") != 1 or int(card.get("estimated_minutes", 999)) > 20 or int(card.get("shot_count_max", 999)) > 5:
                errors.append(f"{repair_id}: daily-native low-cost limits violated")
            if card.get("forced_performance") is not False or card.get("fictional_customer") is not False or card.get("manufactured_conflict") is not False:
                errors.append(f"{repair_id}: daily-native authenticity flags violated")
            if "手机" not in flatten_strings(card.get("equipment", [])):
                errors.append(f"{repair_id}: daily-native card lacks phone equipment")
        for pattern in FORBIDDEN_ROLE_PATTERNS:
            if re.search(pattern, body):
                role_failures += 1
                errors.append(f"{repair_id}: explicit implausible role-action pattern {pattern}")
        role_review = metadata.get("role_action_review", {})
        if role_review.get("deterministic_status") != "PASS" or role_review.get("forbidden_role_action_pairs") != []:
            errors.append(f"{repair_id}: role-action review is not clean")
        if role_review.get("human_plausibility_review") != "PENDING_CLAUDE_AND_FOUNDER":
            errors.append(f"{repair_id}: role human review must remain pending")
        if metadata.get("platform_fit_review", {}).get("human_naturalness_review") != "PENDING_CLAUDE_AND_FOUNDER":
            errors.append(f"{repair_id}: platform human review must remain pending")
        else:
            platform_review_queue += 1
        if metadata.get("skeleton_review", {}).get("semantic_near_skeleton_review") != "PENDING_CLAUDE_AND_FOUNDER":
            errors.append(f"{repair_id}: semantic skeleton human review must remain pending")
        else:
            semantic_review_queue += 1
        if metadata.get("human_review_required") is not True:
            errors.append(f"{repair_id}: human review requirement was bypassed")
        flags = metadata.get("readiness_flags", {})
        if set(flags) != READINESS_KEYS or any(value is not False for value in flags.values()):
            errors.append(f"{repair_id}: readiness flags missing or true")
        if row.get("accepted_domain_knowledge") is not False or row.get("candidatepack_ready") is not False or row.get("production_servable") is not False:
            errors.append(f"{repair_id}: asset/downstream readiness must be false")
        if row.get("generation_status") != "codex_native_creative_repair_draft":
            errors.append(f"{repair_id}: wrong generation_status")
        if row.get("external_LLM_called") is not False:
            errors.append(f"{repair_id}: external LLM claim must be false")
        if row.get("founder_second_review") != "PENDING" or row.get("claude_code_guardian_review") != "PENDING":
            errors.append(f"{repair_id}: human reviews must remain pending")
        if row.get("counts_toward_80_or_3600") is not False:
            errors.append(f"{repair_id}: repair incorrectly counts toward scale")
        skeleton = row.get("narrative_skeleton")
        if not isinstance(skeleton, dict) or not required_skeleton.issubset(skeleton):
            errors.append(f"{repair_id}: incomplete narrative skeleton")
        else:
            payload = recompute_skeleton(row)
            fingerprint = stable_digest(payload)
            if skeleton.get("canonical_payload") != payload or skeleton.get("canonical_fingerprint") != fingerprint:
                errors.append(f"{repair_id}: skeleton fingerprint is not independently reproducible")
            fingerprints.append(fingerprint)
        source_overlap, _, _ = max_overlap(body, source_index)
        review_overlap, _, _ = max_overlap(body, review_index)
        source_overlap_observed = max(source_overlap_observed, source_overlap)
        review_overlap_observed = max(review_overlap_observed, review_overlap)
        if source_overlap > 17:
            errors.append(f"{repair_id}: copied more than 17 chars from one of 120 user-visible kernels")
        if review_overlap > 17:
            errors.append(f"{repair_id}: review-packet kernel leaked into body")
        own_kernel_segments = [value for value in flatten_strings(kernel) if len(normalize(value)) >= 18]
        own_index = build_overlap_index([(repair_id, value) for value in own_kernel_segments])
        own_overlap, _, _ = max_overlap(body, own_index)
        if own_overlap > 17:
            errors.append(f"{repair_id}: content_kernel was copied into body instead of transformed")

    if Counter(capture_counts) != Counter({"daily_native": 32, "lightly_guided": 6, "campaign_directed": 2}):
        errors.append(f"capture-mode quota must be 32/6/2, got {dict(capture_counts)}")
    if set(platform_counts) != PLATFORMS:
        errors.append(f"all five platforms must be covered, got {dict(platform_counts)}")
    if set(account_counts) != ACCOUNT_ROLES:
        errors.append(f"all five account roles must be covered, got {dict(account_counts)}")
    fingerprint_counts = Counter(fingerprints)
    fingerprint_max = max(fingerprint_counts.values(), default=0)
    if fingerprint_max > 2:
        errors.append(f"skeleton fingerprint reused {fingerprint_max} times")
    exact_duplicate_count = len(bodies) - len(set(bodies))
    normalized_duplicate_count = len(norm_bodies) - len(set(norm_bodies))
    if exact_duplicate_count:
        errors.append(f"exact duplicate body count {exact_duplicate_count}")
    if normalized_duplicate_count:
        errors.append(f"normalized duplicate body count {normalized_duplicate_count}")
    metrics.update({
        "repair_count": len(records),
        "class_counts": dict(actual_classes),
        "capture_modes": dict(capture_counts),
        "platform_counts": dict(platform_counts),
        "account_role_counts": dict(account_counts),
        "governance_language_in_body_count": governance_hits,
        "director_marker_in_body_count": director_hits,
        "role_action_failure_count": role_failures,
        "skeleton_fingerprint_max_reuse": fingerprint_max,
        "unique_skeleton_fingerprint_count": len(fingerprint_counts),
        "exact_duplicate_count": exact_duplicate_count,
        "normalized_duplicate_count": normalized_duplicate_count,
        "kernel_overlap_max": source_overlap_observed,
        "review_packet_kernel_overlap_max": review_overlap_observed,
        "platform_fit_review_queue_count": platform_review_queue,
        "semantic_skeleton_review_queue_count": semantic_review_queue,
    })
    return errors, metrics


def baseline_file_bytes(root: Path, rel: str) -> bytes:
    result = run_git(root, "show", f"{BASELINE_HEAD}:{rel}", check=False)
    if result.returncode != 0:
        raise ValueError(f"baseline file missing: {rel}")
    return result.stdout


def validate_original_midbatch_immutable(root: Path) -> list[str]:
    errors: list[str] = []
    listed = git_text(root, "ls-tree", "-r", "--name-only", BASELINE_HEAD, "--", MID_REL)
    for rel in (line.strip() for line in listed.splitlines() if line.strip()):
        path = root / rel
        if not path.is_file():
            errors.append(f"baseline midbatch artifact deleted: {rel}")
            continue
        if path.read_bytes() != baseline_file_bytes(root, rel):
            errors.append(f"baseline midbatch artifact modified: {rel}")
    return errors


def validate_ledger_additive(root: Path) -> list[str]:
    errors: list[str] = []
    current = read_yaml(root / LEDGER_REL)
    baseline = yaml.safe_load(baseline_file_bytes(root, LEDGER_REL).decode("utf-8"))
    current_root = current.get("grc_3600_execution_plan_status", {})
    baseline_root = baseline.get("grc_3600_execution_plan_status", {})
    migration = current_root.get("route_migration_10")
    if not isinstance(migration, dict):
        errors.append("route_migration_10 missing")
        return errors
    reduced = copy.deepcopy(current_root)
    reduced.pop("route_migration_10", None)
    if reduced != baseline_root:
        errors.append("ledger changed outside additive route_migration_10")
    required = {
        "applied_by_task": TASK_ID,
        "operational_state_only": True,
        "no_existing_step_status_changed": True,
        "no_old_checker_edited": True,
        "no_readiness_flipped": True,
        "repair_count": 40,
        "guardian_review": "PENDING",
        "founder_second_review": "PENDING",
        "expand_80": False,
        "expand_600": False,
        "expand_3600": False,
    }
    for key, expected in required.items():
        if migration.get(key) != expected:
            errors.append(f"route_migration_10.{key} must equal {expected!r}")
    md = (root / LEDGER_MD_REL).read_text(encoding="utf-8")
    if TASK_ID not in md or "REPAIR_40_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW" not in md:
        errors.append("human-readable ledger lacks additive repair migration")
    return errors


def validate_summaries(root: Path, records: list[dict[str, Any]], metrics: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    out = root / OUT_REL
    mapping = read_yaml(out / "founder_40_original_to_repair_map.v0.1.yaml")["founder_40_original_to_repair_map"]
    packet = read_yaml(out / "founder_40_before_after_review_packet.v0.1.yaml")["founder_40_before_after_review_packet"]
    audit = read_yaml(out / "founder_40_content_layer_audit.v0.1.yaml")["founder_40_content_layer_audit"]
    quota = read_yaml(out / "founder_40_capture_mode_quota.v0.1.yaml")["founder_40_capture_mode_quota"]
    platform = read_yaml(out / "founder_40_platform_account_matrix.v0.1.yaml")["founder_40_platform_account_matrix"]
    role = read_yaml(out / "founder_40_role_action_gate_result.v0.1.yaml")["founder_40_role_action_gate_result"]
    skeleton = read_yaml(out / "founder_40_skeleton_gate_result.v0.1.yaml")["founder_40_skeleton_gate_result"]
    overlap = read_yaml(out / "founder_40_kernel_overlap_report.v0.1.yaml")["founder_40_kernel_overlap_report"]
    result = read_yaml(out / "founder_40_repair_result.v0.1.yaml")["founder_40_repair_result"]
    overlay = read_yaml(out / "p7d_320_generation_label_correction_overlay.v0.1.yaml")["p7d_320_generation_label_correction_overlay"]
    evidence = read_yaml(out / "accepted_review_evidence.v0.1.yaml")["accepted_review_evidence"]
    contract = read_yaml(out / "founder_40_repair_contract.v0.1.yaml")["founder_40_repair_contract"]
    fingerprint_rows = read_jsonl(out / "founder_40_skeleton_fingerprint_index.v0.1.jsonl")
    if mapping.get("count") != 40 or len(mapping.get("entries", [])) != 40:
        errors.append("original-to-repair map count mismatch")
    if packet.get("count") != 40 or len(packet.get("entries", [])) != 40 or packet.get("codex_does_not_fill_human_verdict") is not True:
        errors.append("before/after review packet is incomplete or self-adjudicated")
    if any(entry.get("claude_code_guardian_review") != "PENDING" or entry.get("founder_second_review") != "PENDING" for entry in packet.get("entries", [])):
        errors.append("before/after packet human verdict was prefilled")
    for key in ("body_text_complete_count", "content_kernel_complete_count", "review_metadata_complete_count", "execution_card_complete_count"):
        if audit.get(key) != 40:
            errors.append(f"content-layer audit {key} mismatch")
    if audit.get("governance_language_in_body_count") != metrics["governance_language_in_body_count"] or audit.get("director_marker_in_body_count") != metrics["director_marker_in_body_count"]:
        errors.append("content-layer audit disagrees with recomputation")
    if quota.get("counts") != metrics["capture_modes"] or quota.get("scope_only_not_formal_schema") is not True:
        errors.append("capture quota summary disagrees or is not scoped")
    if platform.get("platform_counts") != metrics["platform_counts"] or platform.get("account_role_counts") != metrics["account_role_counts"]:
        errors.append("platform/account summary disagrees with records")
    if role.get("explicit_failure_count") != metrics["role_action_failure_count"] or role.get("human_review_required_count") != 40:
        errors.append("role-action report disagrees or omits human queue")
    if skeleton.get("max_fingerprint_reuse") != metrics["skeleton_fingerprint_max_reuse"] or skeleton.get("exact_duplicate_count") != 0 or skeleton.get("normalized_duplicate_count") != 0 or skeleton.get("semantic_human_review_queue_count") != 40:
        errors.append("skeleton report disagrees with recomputation")
    if overlap.get("kernel_count_compared") != 120 or overlap.get("observed_max_chars") != metrics["kernel_overlap_max"] or overlap.get("max_allowed_chars") != 17:
        errors.append("kernel-overlap report disagrees with recomputation")
    expected_fp = {row["repair_id"]: row["narrative_skeleton"]["canonical_fingerprint"] for row in records}
    actual_fp = {str(row.get("repair_id")): str(row.get("canonical_fingerprint")) for row in fingerprint_rows}
    if actual_fp != expected_fp:
        errors.append("fingerprint index disagrees with repaired records")
    if result.get("result") != "REPAIR_40_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW" or result.get("machine_gate_status") != "PASS":
        errors.append("repair result has wrong status semantics")
    if result.get("claude_code_guardian_review") != "PENDING" or result.get("founder_second_review") != "PENDING":
        errors.append("repair result prefilled a human verdict")
    if result.get("scale") != {"expand_80": False, "expand_600": False, "expand_3600": False}:
        errors.append("repair result improperly unlocks scale")
    if overlay != {
        "original_status_literal": "gpt_generated_structured_draft",
        "correct_operational_interpretation": "deterministic_template_assembled_draft",
        "original_records_modified": False,
        "applies_to": "P7D_midbatch_320_001_only",
        "repair_status_literal": "codex_native_creative_repair_draft",
        "evidence_types_must_not_be_conflated": True,
    }:
        errors.append("label correction overlay is not exact and additive")
    if evidence.get("fixed_sample_count") != 40 or evidence.get("prompt_guardian_safe_to_execute") is not True or evidence.get("founder_review_verdict") != "CONDITIONAL_PASS_FOR_REVIEW_ONLY":
        errors.append("accepted review evidence is incomplete")
    if contract.get("scope") != "fixed_founder_40_only" or contract.get("external_LLM_called") is not False or contract.get("original_assets_immutable") is not True:
        errors.append("repair contract scope or provenance is wrong")
    return errors


def validate_live(root: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    metrics: dict[str, Any] = {}
    branch = git_text(root, "branch", "--show-current").strip()
    head = git_text(root, "rev-parse", "HEAD").strip()
    if branch != "master":
        errors.append(f"branch must be master, got {branch}")
    ancestor = run_git(root, "merge-base", "--is-ancestor", BASELINE_HEAD, head, check=False)
    if ancestor.returncode != 0:
        errors.append(f"baseline {BASELINE_HEAD} is not an ancestor of HEAD {head}")
    paths = changed_paths(root)
    disallowed = sorted(path for path in paths if not any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES))
    if disallowed:
        errors.append(f"changed paths outside allowed surface: {disallowed}")
    forbidden = sorted(path for path in paths if path.startswith(FORBIDDEN_DIFF_PREFIXES) or re.search(r"(^|/)(\.env|.*secret.*|.*credential.*)$", path, re.I))
    if forbidden:
        errors.append(f"forbidden scope touched: {forbidden}")
    errors.extend(validate_original_midbatch_immutable(root))
    out = root / OUT_REL
    for name in REQUIRED_ARTIFACTS:
        if not (out / name).is_file():
            errors.append(f"required repair artifact missing: {name}")
    for rel in (FIXTURE_REL, LEDGER_REL, LEDGER_MD_REL, "docs/reports/p7d_founder_40_repair_report.md", "docs/reports/p7d_founder_40_repair_receipt.json"):
        if not (root / rel).is_file():
            errors.append(f"required task file missing: {rel}")
    if errors:
        return errors, metrics
    packet = read_yaml(root / PACKET_REL)["midbatch_320_founder_review_packet"]
    packet_ids = {str(row["output_id"]) for row in packet["samples"]}
    expected_ids = set().union(*CLASS_IDS.values())
    if packet.get("sample_count") != 40 or packet_ids != expected_ids:
        errors.append("source founder packet does not match fixed 40 IDs")
    kernels = read_yaml(root / KERNEL_REL)["user_visible_kernel_matrix"]["entries"]
    review_kernels = read_yaml(root / REVIEW_KERNEL_REL)["review_packet_kernel_matrix"]["entries"]
    if len(kernels) != 120 or len(review_kernels) != 120:
        errors.append("source kernel matrices must each contain 120 entries")
    records = read_jsonl(out / "founder_40_repaired_assets.v0.1.jsonl")
    record_errors, metrics = validate_records(records, kernels, review_kernels, expected_ids)
    errors.extend(record_errors)
    if not record_errors:
        errors.extend(validate_summaries(root, records, metrics))
    errors.extend(validate_ledger_additive(root))
    receipt = read_json(root / "docs/reports/p7d_founder_40_repair_receipt.json")
    if receipt.get("task_id") != TASK_ID or receipt.get("machine_gate_status") != "PASS" or receipt.get("external_LLM_called") is not False:
        errors.append("task receipt is missing or dishonest")
    all_task_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in out.rglob("*") if path.is_file())
    true_patterns = (
        r"candidatepack_ready\s*[:=]\s*true", r"KE_ready\s*[:=]\s*true",
        r"RAG_ready\s*[:=]\s*true", r"DIFY_ready\s*[:=]\s*true",
        r"production_servable\s*[:=]\s*true", r"generation_allowed\s*[:=]\s*true",
        r"production_ready\s*[:=]\s*true", r"expand_80\s*[:=]\s*true",
        r"expand_600\s*[:=]\s*true", r"expand_3600\s*[:=]\s*true",
    )
    for pattern in true_patterns:
        if re.search(pattern, all_task_text, re.I):
            errors.append(f"forbidden readiness/scale truth found: {pattern}")
    metrics.update({
        "branch": branch,
        "baseline_head": BASELINE_HEAD,
        "validated_head_relation": "baseline_or_descendant",
        "changed_path_count": len(paths),
        "original_assets_unchanged": not validate_original_midbatch_immutable(root),
        "readiness_false": not any(
            "readiness" in error or "improperly unlocks" in error
            for error in errors
        ),
    })
    return errors, metrics


def run_selftest(root: Path) -> tuple[bool, dict[str, Any]]:
    out = root / OUT_REL
    records = read_jsonl(out / "founder_40_repaired_assets.v0.1.jsonl")
    kernels = read_yaml(root / KERNEL_REL)["user_visible_kernel_matrix"]["entries"]
    review_kernels = read_yaml(root / REVIEW_KERNEL_REL)["review_packet_kernel_matrix"]["entries"]
    expected_ids = set().union(*CLASS_IDS.values())
    positive_errors, _ = validate_records(copy.deepcopy(records), kernels, review_kernels, expected_ids)
    if positive_errors:
        return False, {"positive_fixture_errors": positive_errors}
    manifest = read_yaml(root / FIXTURE_REL)["p7d_founder_40_repair_fixtures"]
    expected_cases = [str(item) for item in manifest["negative_cases"]]
    parse_cases = {"malformed_yaml", "malformed_json"}

    def mutate(case: str, rows: list[dict[str, Any]]) -> None:
        if case == "missing_record":
            rows.pop()
        elif case == "duplicate_original":
            rows[1]["original_output_id"] = rows[0]["original_output_id"]
        elif case == "governance_body_leak":
            rows[0]["body_text"] += "发布前补齐事实。"
        elif case == "director_body_leak":
            rows[0]["body_text"] += "镜头切到机位。"
        elif case == "fact_slot_body_leak":
            rows[0]["body_text"] += "【品牌事实】"
        elif case == "missing_layer":
            rows[0].pop("execution_card")
        elif case == "p0_01_missing_field":
            rows[0]["content_kernel"].pop("organization_choice")
        elif case == "p0_05_missing_field":
            row = next(item for item in rows if item["p0_group"] == "P0_05")
            row["content_kernel"].pop("customer_task")
        elif case == "bad_p0_04_subroute":
            row = next(item for item in rows if item["p0_group"] == "P0_04")
            row["content_kernel"]["scoped_subroute"] = "ontology_object"
        elif case == "capture_quota_mismatch":
            row = next(item for item in rows if item["capture_mode"] == "daily_native")
            row["capture_mode"] = "lightly_guided"
        elif case == "campaign_in_p0_01":
            rows[0]["capture_mode"] = "campaign_directed"
        elif case == "unknown_platform":
            rows[0]["platform_target"] = "generic_video"
        elif case == "implausible_role_action":
            rows[0]["body_text"] += "顾客调整橱窗。"
        elif case == "forged_fingerprint":
            rows[0]["narrative_skeleton"]["canonical_fingerprint"] = "0" * 64
        elif case == "duplicate_body":
            rows[1]["body_text"] = rows[0]["body_text"]
        elif case == "kernel_copy":
            rows[0]["body_text"] = kernels[0]["business_judgment"]
        elif case == "readiness_true":
            rows[0]["review_metadata"]["readiness_flags"]["generation_allowed"] = True
        elif case == "founder_verdict_prefilled":
            rows[0]["founder_second_review"] = "PASS"
        elif case == "external_llm_true":
            rows[0]["external_LLM_called"] = True
        elif case == "wrong_generation_status":
            rows[0]["generation_status"] = "gpt_generated_structured_draft"
        elif case == "human_review_bypassed":
            rows[0]["review_metadata"]["human_review_required"] = False
        else:
            raise ValueError(f"unknown fixture case: {case}")

    failures: list[str] = []
    for case in expected_cases:
        if case in parse_cases:
            try:
                if case == "malformed_yaml":
                    yaml.safe_load("root: [unterminated")
                else:
                    json.loads('{"unterminated":')
            except (yaml.YAMLError, json.JSONDecodeError):
                continue
            failures.append(case)
            continue
        mutated = copy.deepcopy(records)
        mutate(case, mutated)
        case_errors, _ = validate_records(mutated, kernels, review_kernels, expected_ids)
        if not case_errors:
            failures.append(case)
    return not failures, {"negative_case_count": len(expected_cases), "negative_cases_not_caught": failures}


def main() -> int:
    if not __debug__:
        print(json.dumps({"checker": Path(__file__).name, "status": "FAIL_CLOSED", "reason": "python_optimized_mode_forbidden"}))
        return 2
    if yaml is None:
        print(json.dumps({"checker": Path(__file__).name, "status": "FAIL_CLOSED", "reason": "yaml_unavailable"}))
        return 2
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--live", action="store_true")
    group.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        if args.selftest:
            passed, details = run_selftest(root)
            payload = {"checker": Path(__file__).name, "mode": "selftest", "status": "PASS" if passed else "FAIL", **details}
            print(json.dumps(payload, ensure_ascii=False))
            return 0 if passed else 1
        errors, metrics = validate_live(root)
    except Exception as exc:
        errors = [f"fail-closed exception: {type(exc).__name__}: {exc}"]
        metrics = {}
    payload = {
        "checker": Path(__file__).name,
        "task_id": TASK_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        **metrics,
    }
    report_path = root / REPORT_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
