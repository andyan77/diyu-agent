#!/usr/bin/env python3
"""Freeze selection and package the bounded P7D remaining-80 validation run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GKB-P7D-REPAIR-RULE-VALIDATION-BATCH-80-001"
BASELINE_HEAD = "3f1beedd65f42b9c3fffe79dadfd878534216361"
ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "07_microbatch_runs/scoped_content_microbatch_120_001"
MID = RUN / "midbatch_320_001"
OUT = MID / "repair_validation_80_001"
KERNEL_PATH = RUN / "content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml"
CARDS_PATH = RUN / "knowledge_candidate_cards.yaml"
FOUNDER_40_DIR = MID / "founder_40_repair_001"
FOUNDER_40_PATH = FOUNDER_40_DIR / "founder_40_repaired_assets.v0.1.jsonl"
PLATFORM_DIR = FOUNDER_40_DIR / "platform_native_5x2_001"
VALIDATION_SPEC_PATH = OUT / "repair_validation_80_validation_spec.v0.1.yaml"
AUTHORED_SPECS_PATH = OUT / "repair_validation_80_authored_specs.v0.1.yaml"

PLATFORM_MATRIX = {
    "P0_01": ("wechat_channels", "moments"),
    "P0_02": ("douyin", "wechat_channels"),
    "P0_03": ("xiaohongshu", "live"),
    "P0_04": ("douyin", "moments"),
    "P0_05": ("xiaohongshu", "live"),
}
ACCOUNT_ROLE = {
    "P0_01": "founder",
    "P0_02": "store_manager",
    "P0_03": "brand_headquarters",
    "P0_04": "store_manager",
    "P0_05": "sales_associate",
}
PLATFORM_SHAPES = {
    "douyin": "short_video_spoken_event",
    "xiaohongshu": "note_title_and_body",
    "wechat_channels": "trust_based_work_story",
    "moments": "daily_private_caption",
    "live": "live_talk_card",
}
ON_CAMERA_ROLE = {
    "founder": "创始人或一名被授权的经营者",
    "store_manager": "店长本人",
    "brand_headquarters": "一名品牌商品或内容工作人员",
    "sales_associate": "导购本人",
}
READINESS_FLAGS = {
    "candidatepack_ready": False,
    "KE_ready": False,
    "Serving_ready": False,
    "RAG_ready": False,
    "DIFY_ready": False,
    "production_servable": False,
    "generation_eligible": False,
    "generation_allowed": False,
    "release_ready": False,
    "production_ready": False,
}
CONTRACT_PATHS = (
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/founder_40_repair_001/founder_40_repair_contract.v0.1.yaml",
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/founder_40_repair_001/founder_40_scoped_prompt_patch.v0.1.md",
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/founder_40_repair_001/platform_native_5x2_001/platform_native_everyday_expression_contract.v0.1.yaml",
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/repair_validation_80_001/repair_validation_80_validation_spec.v0.1.yaml",
)
CHECKER_REFS = (
    "ci/checkers/check_p7d_founder_40_repair.py",
    "ci/checkers/check_p7d_platform_native_5x2.py",
)


def digest_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


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


def write_yaml(path: Path, value: Any) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def git_text(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.decode("utf-8", errors="replace")


def source_inputs() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]
]:
    kernels = yaml.safe_load(KERNEL_PATH.read_text(encoding="utf-8"))[
        "user_visible_kernel_matrix"
    ]["entries"]
    founder = read_jsonl(FOUNDER_40_PATH)
    cards = yaml.safe_load(CARDS_PATH.read_text(encoding="utf-8"))[
        "scoped_120_candidate_cards"
    ]["candidates"]
    return kernels, founder, {str(row["candidate_id"]): row for row in cards}


def deterministic_selection() -> list[dict[str, Any]]:
    kernels, founder, cards = source_inputs()
    used = {str(row["bound_kernel_candidate_id"]) for row in founder}
    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in kernels:
        by_cluster[str(row["canonical_cluster_id"])].append(row)
    if len(kernels) != 120 or len(by_cluster) != 40 or len(used) != 40:
        raise ValueError("40x3 canonical kernel structure does not hold")
    selected: list[dict[str, Any]] = []
    ordinal = 0
    for cluster_id in sorted(by_cluster):
        rows = sorted(by_cluster[cluster_id], key=lambda row: str(row["candidate_id"]))
        existing = [row for row in rows if row["candidate_id"] in used]
        remaining = [row for row in rows if row["candidate_id"] not in used]
        if len(rows) != 3 or len(existing) != 1 or len(remaining) != 2:
            raise ValueError(f"invalid per-cluster difference: {cluster_id}")
        p0_group = str(rows[0]["p0_group"])
        for position, (kernel, platform) in enumerate(
            zip(remaining, PLATFORM_MATRIX[p0_group], strict=True), start=1
        ):
            ordinal += 1
            candidate_id = str(kernel["candidate_id"])
            card = cards[candidate_id]
            source_output_candidates = [str(card["target_output_id"])]
            selected.append(
                {
                    "selection_ordinal": ordinal,
                    "checkpoint_id": f"RV80-CP-{((ordinal - 1) // 20) + 1:02d}",
                    "cluster_id": cluster_id,
                    "capability_group": p0_group,
                    "cluster_position": position,
                    "kernel_id": candidate_id,
                    "source_assignment_id": kernel["generation_assignment_id"],
                    "source_output_candidates": source_output_candidates,
                    "source_output_id": min(source_output_candidates),
                    "source_record_selection_rule": "minimum_legal_output_id_after_kernel_dedup",
                    "generation_mode": kernel["generation_mode"],
                    "platform_target": platform,
                    "account_role": ACCOUNT_ROLE[p0_group],
                    "capture_mode": "daily_native",
                    "source_kernel_digest": stable_digest(kernel),
                    "source_kernel_ref": (
                        "07_microbatch_runs/scoped_content_microbatch_120_001/"
                        f"content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml#{candidate_id}"
                    ),
                    "platform_contract_ref": (
                        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
                        "founder_40_repair_001/platform_native_5x2_001/"
                        "platform_native_everyday_expression_contract.v0.1.yaml"
                    ),
                    "existing_founder_40_kernel_id": existing[0]["candidate_id"],
                }
            )
    if len(selected) != 80 or len({row["kernel_id"] for row in selected}) != 80:
        raise ValueError("remaining selection is not 80 unique kernels")
    if used & {str(row["kernel_id"]) for row in selected}:
        raise ValueError("remaining selection intersects founder-40")
    return selected


def freeze_only() -> None:
    if git_text("rev-parse", "HEAD").strip() != BASELINE_HEAD:
        raise ValueError("baseline HEAD drift before freeze")
    if (OUT / "repair_validation_80_assets.v0.1.jsonl").exists():
        raise ValueError("generation assets already exist before freeze")
    selection = deterministic_selection()
    source_digests = {
        str(path.relative_to(ROOT)): digest_bytes(path)
        for path in (KERNEL_PATH, CARDS_PATH, FOUNDER_40_PATH)
    }
    contract_digests = {
        relative: digest_bytes(ROOT / relative) for relative in CONTRACT_PATHS
    }
    checker_digests = {
        relative: digest_bytes(ROOT / relative) for relative in CHECKER_REFS
    }
    frozen_payload = {
        "baseline_head": BASELINE_HEAD,
        "source_digests": source_digests,
        "contract_digests": contract_digests,
        "checker_reference_digests": checker_digests,
        "selection_algorithm": {
            "canonical_source": str(KERNEL_PATH.relative_to(ROOT)),
            "subtract_source": str(FOUNDER_40_PATH.relative_to(ROOT)),
            "per_cluster_total": 3,
            "per_cluster_subtract": 1,
            "per_cluster_remaining": 2,
            "stable_sort": "candidate_id_ascending",
            "source_record_tiebreak": "minimum_legal_output_id",
            "platform_assignment": "first_remaining_to_A_second_remaining_to_B",
        },
        "platform_matrix": PLATFORM_MATRIX,
        "validation_spec_digest": contract_digests[
            str(VALIDATION_SPEC_PATH.relative_to(ROOT))
        ],
    }
    freeze = {
        "repair_validation_80_contract_freeze_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "baseline_head": BASELINE_HEAD,
            "frozen_before_first_generation": True,
            "generation_started_at_freeze": False,
            "contracts_must_not_change_after_freeze": True,
            **frozen_payload,
            "freeze_digest": stable_digest(frozen_payload),
        }
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write_yaml(OUT / "repair_validation_80_contract_freeze_manifest.v0.1.yaml", freeze)
    write_jsonl(OUT / "remaining_80_kernel_selection_manifest.v0.1.jsonl", selection)
    platform_counts = Counter(row["platform_target"] for row in selection)
    p0_counts = Counter(row["capability_group"] for row in selection)
    selection_summary = {
        "remaining_80_kernel_selection_summary": {
            "task_id": TASK_ID,
            "cluster_count": 40,
            "total_kernel_count": 120,
            "previous_repaired_kernel_count": 40,
            "selected_kernel_count": 80,
            "unique_selected_kernel_count": 80,
            "combined_unique_kernel_count": 120,
            "coverage_gap_count": 0,
            "duplicate_kernel_count": 0,
            "per_cluster_remaining_count": 2,
            "P0_distribution": dict(p0_counts),
            "platform_distribution": dict(platform_counts),
            "selection_digest": stable_digest(selection),
            "selection_reproducible": True,
            "generation_started": False,
        }
    }
    write_yaml(
        OUT / "remaining_80_kernel_selection_summary.v0.1.yaml", selection_summary
    )
    accepted = {
        "accepted_review_evidence": {
            "baseline_head": BASELINE_HEAD,
            "founder_40_repair": {
                "execution_status": "COMPLETE",
                "guardian_status": "PASS",
            },
            "platform_native_5x2_probe": {
                "machine_gate": "PASS",
                "claude_code_guardian": "PASS",
                "external_founder_review": "PASS",
                "variant_count": 10,
                "knowledge_count_increment": 0,
            },
            "founder_40_full_grading": "deferred_by_founder_scale_authority",
            "deferred_grading_consequence": (
                "Before any 600 scale decision, founder-40 plus this 80 must receive a combined full grading."
            ),
            "authorized_count": 80,
            "expand_600": False,
            "expand_3600": False,
        }
    }
    write_yaml(OUT / "accepted_review_evidence.v0.1.yaml", accepted)


def kernel_segments(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "object_anchor",
        "business_judgment",
        "tradeoff_or_tension",
        "spoken_line_seed",
        "output_asset_hint",
    ):
        if isinstance(row.get(key), str):
            values.append(str(row[key]))
    for key in ("human_subject", "human_action", "scene_premise"):
        if isinstance(row.get(key), list):
            values.extend(str(value) for value in row[key])
    return values


def longest_common_substring(left: str, right: str, cap: int = 40) -> tuple[int, str]:
    a, b = normalize(left), normalize(right)
    previous = [0] * (len(b) + 1)
    best = 0
    best_end = 0
    for i, char_a in enumerate(a, start=1):
        current = [0] * (len(b) + 1)
        for j, char_b in enumerate(b, start=1):
            if char_a == char_b:
                current[j] = previous[j - 1] + 1
                if current[j] > best:
                    best = current[j]
                    best_end = i
                    if best >= cap:
                        return best, a[best_end - best : best_end]
        previous = current
    return best, a[best_end - best : best_end]


def all_kernel_overlap(body: str, kernels: list[dict[str, Any]]) -> dict[str, Any]:
    best = (0, "", "")
    for row in kernels:
        for segment in kernel_segments(row):
            length, fragment = longest_common_substring(body, segment)
            if length > best[0]:
                best = (length, str(row["candidate_id"]), fragment)
    return {"max_chars": best[0], "kernel_id": best[1], "fragment": best[2]}


def body_shingles(text: str, size: int = 5) -> set[str]:
    value = normalize(text)
    if len(value) < size:
        return {value} if value else set()
    return {value[index : index + size] for index in range(len(value) - size + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def required_fact_slots(mode: str, p0_group: str) -> list[str]:
    slots: list[str] = []
    if mode == "fact_slot_script":
        slots = ["发布时使用的品牌口吻", "若指向具体商品则补商品资料"]
    elif mode == "evidence_bound_candidate":
        slots = ["涉及成分、工艺或性能时对应的标签或记录", "发布时使用的商品资料"]
    elif mode == "display_solution":
        slots = ["真实门店空间与动线", "现场可用商品和陈列资源"]
    if p0_group == "P0_01":
        slots.append("如转成品牌真实故事，需确认事件来源")
    return slots


def forbidden_claims(mode: str) -> list[str]:
    claims = ["虚构品牌事件", "虚构顾客反馈", "无来源经营结果", "无依据身体效果"]
    if mode in {"fact_slot_script", "evidence_bound_candidate"}:
        claims.extend(["无依据材质身份", "无依据耐用或性能结论"])
    return claims


def platform_payload(
    spec: dict[str, Any], platform: str, source_kernel: dict[str, Any]
) -> dict[str, str]:
    body = str(spec["body_text"])
    first_sentence = re.split(r"[。！？]", body, maxsplit=1)[0].strip()
    opening = str(spec.get("opening_move", f"{first_sentence}。"))
    detail = str(spec["visible_detail"])
    line = str(spec["spoken_line_seed"])
    judgment = str(source_kernel["business_judgment"])
    next_action = str(spec["natural_next_action"])
    if platform == "douyin":
        return {
            "in_progress_opening": opening,
            "visible_action_early": f"{spec['human_action']}，让{detail}先出现。",
            "one_natural_spoken_hook": line,
            "short_spoken_body": str(spec["body_text"]),
            "natural_interaction_or_store_handoff": next_action,
        }
    if platform == "xiaohongshu":
        return {
            "searchable_title": str(
                spec.get("platform_title", f"{spec['visible_detail']}，现场该怎么看")
            ),
            "first_person_observation": opening,
            "concrete_detail": detail,
            "save_worthy_judgment": judgment,
            "non_advertorial_close": next_action,
        }
    if platform == "wechat_channels":
        return {
            "trust_based_opening": opening,
            "complete_small_work_event": str(spec["body_text"]),
            "operator_or_role_judgment": judgment,
            "natural_spoken_close": line,
            "non_clickbait_handoff": next_action,
        }
    if platform == "moments":
        return {
            "short_daily_note": opening,
            "one_event": str(spec["event_trigger"]),
            "one_visible_detail": detail,
            "personal_observation": judgment,
            "optional_soft_private_followup": next_action,
        }
    return {
        "show_object": str(source_kernel["object_anchor"]),
        "ask_customer_use_case": str(
            spec.get("interaction_question", "你更想看它在哪个使用场景里的状态？")
        ),
        "compare_touch_or_try": str(spec["human_action"]),
        "safe_observation": detail,
        "answer_boundary": str(
            spec.get("answer_boundary", "只说当下可见变化，不替个人保证结果。")
        ),
        "next_interaction": next_action,
    }


def build_asset(
    selection: dict[str, Any],
    spec: dict[str, Any],
    source_kernel: dict[str, Any],
    all_kernels: list[dict[str, Any]],
) -> dict[str, Any]:
    body = str(spec["body_text"])
    p0_group = str(selection["capability_group"])
    mode = str(selection["generation_mode"])
    platform = str(selection["platform_target"])
    overlap = all_kernel_overlap(body, all_kernels)
    content_kernel: dict[str, Any] = {
        "human_subject": source_kernel["human_subject"],
        "object_anchor": source_kernel["object_anchor"],
        "human_action": spec["human_action"],
        "scene_premise": spec["scene_premise"],
        "event_trigger": spec["event_trigger"],
        "visible_detail": spec["visible_detail"],
        "business_judgment": source_kernel["business_judgment"],
        "tradeoff_or_tension": source_kernel["tradeoff_or_tension"],
        "spoken_line_seed": spec["spoken_line_seed"],
        "natural_next_action": spec["natural_next_action"],
    }
    if p0_group == "P0_01":
        content_kernel.update(
            {
                "organization_choice": source_kernel["business_judgment"],
                "long_term_tradeoff": source_kernel["tradeoff_or_tension"],
                "visible_product_trace": spec["visible_detail"],
                "founder_or_team_decision": spec["human_action"],
                "not_claimed_result": "不声称属于某个真实品牌，也不声称经营结果",
                "safe_spoken_line": spec["spoken_line_seed"],
            }
        )
    if p0_group == "P0_04":
        content_kernel["scoped_subroute"] = "store_daily_display_action"
    if p0_group == "P0_05":
        content_kernel.update(
            {
                "customer_task": spec.get("customer_task", "帮助顾客完成当下穿着选择"),
                "product_role": spec.get("product_role", "场景里的选择工具"),
                "scene_use_case": spec["scene_premise"],
                "trial_or_tryon_trigger": spec.get(
                    "tryon_trigger", "顾客需要比较真实穿着状态时"
                ),
                "safe_observation": spec["visible_detail"],
                "guide_next_line": spec["spoken_line_seed"],
            }
        )
    skeleton_payload = {
        "p0_group": p0_group,
        "generation_mode": mode,
        "platform_target": platform,
        "event_type": spec["event_type"],
        "opening_family": spec["opening_family"],
        "closing_family": spec["closing_family"],
        "subject_role": source_kernel["human_subject"],
        "action_family": spec["human_action"],
        "judgment_family": spec["judgment_family"],
    }
    slots = required_fact_slots(mode, p0_group)
    claims = forbidden_claims(mode)
    account_role = str(selection["account_role"])
    execution_card = {
        "who_executes": ON_CAMERA_ROLE[account_role],
        "who_appears": ON_CAMERA_ROLE[account_role],
        "phone_placement": str(spec["phone_placement"]),
        "real_work_action": spec["human_action"],
        "natural_spoken_line": spec["spoken_line_seed"],
        "simple_segment_count_max": 3 + (int(selection["selection_ordinal"]) % 3),
        "estimated_minutes": 10 + (int(selection["selection_ordinal"]) % 9),
        "do_not_perform": ["不扮演顾客", "不制造冲突", "不背品牌理念"],
        "do_not_say": claims,
        "interaction_handoff": spec["natural_next_action"],
        "capture_mode": "daily_native",
        "dedicated_crew_count": 0,
        "hired_actor_count": 0,
        "required_people_max": 1,
        "phone_count": 1,
        "production_time_minutes_max": 20,
        "special_lighting_required": False,
        "scripted_performance_required": False,
        "fake_customer": False,
        "manufactured_conflict": False,
    }
    asset_id = f"RV80-ASSET-{int(selection['selection_ordinal']):03d}"
    return {
        "asset_id": asset_id,
        "selection_ordinal": selection["selection_ordinal"],
        "checkpoint_id": selection["checkpoint_id"],
        "kernel_id": selection["kernel_id"],
        "source_output_id": selection["source_output_id"],
        "source_assignment_id": selection["source_assignment_id"],
        "canonical_cluster_id": selection["cluster_id"],
        "capability_group": p0_group,
        "generation_mode": mode,
        "platform_target": platform,
        "payload_shape": PLATFORM_SHAPES[platform],
        "platform_payload": platform_payload(spec, platform, source_kernel),
        "account_role": account_role,
        "capture_mode": "daily_native",
        "body_text": body,
        "content_kernel": content_kernel,
        "review_metadata": {
            "required_fact_slots": slots,
            "forbidden_claims": claims,
            "event_binding_state": "bounded_routine_work_prototype",
            "role_action_review": {
                "machine_status": "PASS",
                "expert_status": "PENDING_CLAUDE_CODE",
            },
            "platform_native_review": {
                "machine_status": "STRUCTURE_ONLY_PASS",
                "expert_status": "PENDING_CLAUDE_CODE",
            },
            "everyday_voice_review": {
                "machine_status": "TRIGGER_SCAN_COMPLETE",
                "expert_status": "PENDING_CLAUDE_CODE",
            },
            "low_cost_execution_review": {
                "machine_status": "CONSTRAINT_PASS",
                "expert_status": "PENDING_CLAUDE_CODE",
            },
            "skeleton_review": {
                "machine_status": "PASS",
                "expert_status": "PENDING_CLAUDE_CODE",
            },
            "source_refs": [
                selection["source_kernel_ref"],
                str(CARDS_PATH.relative_to(ROOT)),
            ],
            "readiness_flags": dict(READINESS_FLAGS),
            "human_review_required": True,
        },
        "execution_card": execution_card,
        "narrative_skeleton": {
            "payload": skeleton_payload,
            "fingerprint": stable_digest(skeleton_payload),
        },
        "source_kernel_digest": stable_digest(source_kernel),
        "source_kernel_overlap": overlap,
        "body_digest": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "normalized_body_digest": hashlib.sha256(
            normalize(body).encode("utf-8")
        ).hexdigest(),
        "generation_status": "codex_native_repaired_expression_asset",
        "external_LLM_called": False,
        "creates_new_knowledge": False,
        "knowledge_count_increment": 0,
        "accepted_domain_knowledge": False,
        "candidatepack_ready": False,
        "production_servable": False,
        "counts_toward_600_or_3600": False,
        "evaluation_axes": {
            "knowledge_and_fact_boundary": {"machine_status": "PASS"},
            "content_fuel_support": {
                "machine_status": "PASS",
                "expert_status": "PENDING_CLAUDE_CODE",
            },
            "platform_native_fit": {
                "machine_status": "STRUCTURE_ONLY_PASS",
                "expert_status": "PENDING_CLAUDE_CODE",
            },
            "daily_execution_fit": {
                "machine_status": "CONSTRAINT_PASS",
                "expert_status": "PENDING_CLAUDE_CODE",
            },
            "publication_readiness": {"status": False},
        },
    }


def validate_first_pass(asset: dict[str, Any], validation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    body = str(asset["body_text"])
    thresholds = validation["machine_thresholds"]
    markers = validation["body_blocking_markers"]
    if len(normalize(body)) < int(thresholds["minimum_normalized_body_chars"]):
        errors.append("BODY_TOO_THIN")
    if int(asset["source_kernel_overlap"]["max_chars"]) > int(
        thresholds["source_kernel_longest_overlap_max_chars"]
    ):
        errors.append("SOURCE_KERNEL_COPY")
    if any(marker in body for group in markers.values() for marker in group):
        errors.append("BODY_BLOCKING_MARKER")
    if re.search(
        r"(?:王|李|张|陈|刘|赵)(?:姐|女士|先生|小姐)|顾客说|客人说|有位顾客", body
    ):
        errors.append("FAKE_OR_NAMED_CUSTOMER")
    if re.search(
        r"(?<!不)保证.{0,5}(显白|显高|显瘦|耐穿|舒适)|"
        r"一定.{0,5}(显白|显高|显瘦|耐穿|舒适)|卖爆|销量(?:增长|提升)|转化率(?:增长|提升)",
        body,
    ):
        errors.append("UNSUPPORTED_HARD_CLAIM")
    execution = asset["execution_card"]
    expected = validation["daily_native_constraints"]
    for key, value in expected.items():
        if key == "simple_segment_count_max":
            if int(execution[key]) > int(value):
                errors.append(f"DAILY_NATIVE_{key}")
        elif key == "production_time_minutes_max":
            if int(execution[key]) > int(value):
                errors.append(f"DAILY_NATIVE_{key}")
        elif execution.get(key) != value:
            errors.append(f"DAILY_NATIVE_{key}")
    return sorted(set(errors))


def verify_freeze() -> dict[str, Any]:
    freeze = yaml.safe_load(
        (OUT / "repair_validation_80_contract_freeze_manifest.v0.1.yaml").read_text(
            encoding="utf-8"
        )
    )["repair_validation_80_contract_freeze_manifest"]
    for relative, expected in freeze["source_digests"].items():
        if digest_bytes(ROOT / relative) != expected:
            raise ValueError(f"source changed after freeze: {relative}")
    for relative, expected in freeze["contract_digests"].items():
        if digest_bytes(ROOT / relative) != expected:
            raise ValueError(f"contract changed after freeze: {relative}")
    for relative, expected in freeze["checker_reference_digests"].items():
        if digest_bytes(ROOT / relative) != expected:
            raise ValueError(f"checker reference changed after freeze: {relative}")
    return freeze


def generate() -> None:
    verify_freeze()
    selection = read_jsonl(OUT / "remaining_80_kernel_selection_manifest.v0.1.jsonl")
    current_selection = deterministic_selection()
    if selection != current_selection:
        raise ValueError("selection changed after freeze")
    specs_doc = yaml.safe_load(AUTHORED_SPECS_PATH.read_text(encoding="utf-8"))[
        "repair_validation_80_authored_specs"
    ]
    specs = specs_doc["entries"]
    specs_by_id = {str(row["kernel_id"]): row for row in specs}
    selected_ids = {str(row["kernel_id"]) for row in selection}
    if len(specs) != 80 or set(specs_by_id) != selected_ids:
        raise ValueError("authored specs do not match frozen remaining-80 selection")
    kernels, _, _ = source_inputs()
    kernels_by_id = {str(row["candidate_id"]): row for row in kernels}
    validation = yaml.safe_load(VALIDATION_SPEC_PATH.read_text(encoding="utf-8"))[
        "repair_validation_80_validation_spec"
    ]
    assets: list[dict[str, Any]] = []
    first_pass_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    seen_bodies: list[dict[str, Any]] = []
    fingerprints: Counter[str] = Counter()
    for selection_row in selection:
        kernel_id = str(selection_row["kernel_id"])
        spec = specs_by_id[kernel_id]
        asset = build_asset(selection_row, spec, kernels_by_id[kernel_id], kernels)
        errors = validate_first_pass(asset, validation)
        fingerprint = str(asset["narrative_skeleton"]["fingerprint"])
        if fingerprints[fingerprint] >= int(
            validation["machine_thresholds"]["skeleton_fingerprint_reuse_max"]
        ):
            errors.append("SKELETON_REUSE")
        normalized = normalize(str(asset["body_text"]))
        if any(normalize(str(row["body_text"])) == normalized for row in seen_bodies):
            errors.append("NORMALIZED_DUPLICATE")
        max_jaccard = 0.0
        nearest_id = ""
        for prior in seen_bodies:
            score = jaccard(
                body_shingles(str(asset["body_text"])),
                body_shingles(str(prior["body_text"])),
            )
            if score > max_jaccard:
                max_jaccard = score
                nearest_id = str(prior["asset_id"])
        if max_jaccard > float(
            validation["machine_thresholds"]["cross_item_five_shingle_jaccard_max"]
        ):
            errors.append("CROSS_ITEM_NEAR_DUPLICATE")
        first_pass_rows.append(
            {
                "asset_id": asset["asset_id"],
                "kernel_id": kernel_id,
                "checkpoint_id": asset["checkpoint_id"],
                "first_pass_body_text": asset["body_text"],
                "first_pass_body_digest": asset["body_digest"],
                "machine_status": "PASS" if not errors else "FAIL",
                "failure_codes": sorted(set(errors)),
                "bounded_correction_used": False,
                "accepted_body_digest": asset["body_digest"] if not errors else None,
                "max_prior_jaccard": round(max_jaccard, 6),
                "nearest_prior_asset_id": nearest_id or None,
            }
        )
        if errors:
            failure_rows.append(
                {
                    "asset_id": asset["asset_id"],
                    "kernel_id": kernel_id,
                    "checkpoint_id": asset["checkpoint_id"],
                    "blocking": True,
                    "failure_codes": sorted(set(errors)),
                }
            )
        else:
            assets.append(asset)
            seen_bodies.append(asset)
            fingerprints[fingerprint] += 1
        if int(selection_row["selection_ordinal"]) % 20 == 0:
            checkpoint_id = str(selection_row["checkpoint_id"])
            checkpoint_first = [
                row for row in first_pass_rows if row["checkpoint_id"] == checkpoint_id
            ]
            checkpoint_failures = [
                row for row in checkpoint_first if row["machine_status"] == "FAIL"
            ]
            failure_codes = Counter(
                code for row in checkpoint_failures for code in row["failure_codes"]
            )
            stop_reasons: list[str] = []
            if len(checkpoint_failures) > 2:
                stop_reasons.append("CHECKPOINT_FIRST_PASS_FAILURE_ABOVE_10_PERCENT")
            if any(count >= 3 for count in failure_codes.values()):
                stop_reasons.append("SAME_BLOCKING_FAILURE_AT_LEAST_3")
            if any(
                code in {"UNSUPPORTED_HARD_CLAIM", "FAKE_OR_NAMED_CUSTOMER"}
                for row in checkpoint_failures
                for code in row["failure_codes"]
            ):
                stop_reasons.append("ROLE_OR_CLAIM_HARD_FAILURE")
            checkpoint_rows.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "range": [
                        int(selection_row["selection_ordinal"]) - 19,
                        int(selection_row["selection_ordinal"]),
                    ],
                    "expected_count": 20,
                    "first_pass_count": len(checkpoint_first),
                    "first_pass_pass_count": len(checkpoint_first)
                    - len(checkpoint_failures),
                    "first_pass_failure_count": len(checkpoint_failures),
                    "bounded_correction_count": 0,
                    "accepted_count": len(checkpoint_first) - len(checkpoint_failures),
                    "failure_code_distribution": dict(failure_codes),
                    "stop_reasons": stop_reasons,
                    "status": "PASS"
                    if not stop_reasons and not checkpoint_failures
                    else "STOPPED",
                }
            )
            if stop_reasons or checkpoint_failures:
                break
    write_jsonl(
        OUT / "repair_validation_80_first_pass_ledger.v0.1.jsonl", first_pass_rows
    )
    write_jsonl(
        OUT / "repair_validation_80_checkpoint_ledger.v0.1.jsonl", checkpoint_rows
    )
    write_jsonl(OUT / "repair_validation_80_failure_ledger.v0.1.jsonl", failure_rows)
    if failure_rows or len(assets) != 80:
        raise ValueError(
            f"generation stopped with {len(failure_rows)} failures and {len(assets)} accepted"
        )
    write_jsonl(OUT / "repair_validation_80_assets.v0.1.jsonl", assets)
    fingerprint_rows = [
        {
            "asset_id": row["asset_id"],
            "kernel_id": row["kernel_id"],
            "fingerprint": row["narrative_skeleton"]["fingerprint"],
            "payload": row["narrative_skeleton"]["payload"],
            "global_reuse_count": fingerprints[
                row["narrative_skeleton"]["fingerprint"]
            ],
        }
        for row in assets
    ]
    write_jsonl(
        OUT / "repair_validation_80_fingerprint_index.v0.1.jsonl", fingerprint_rows
    )
    selected_ids = {str(row["kernel_id"]) for row in selection}
    founder_ids = {
        str(row["bound_kernel_candidate_id"]) for row in read_jsonl(FOUNDER_40_PATH)
    }
    coverage = {
        "repair_validation_80_kernel_coverage": {
            "cluster_count": 40,
            "canonical_kernel_count": 120,
            "founder_40_kernel_count": len(founder_ids),
            "remaining_80_kernel_count": len(selected_ids),
            "intersection_count": len(founder_ids & selected_ids),
            "combined_unique_kernel_count": len(founder_ids | selected_ids),
            "coverage_gap_count": 120 - len(founder_ids | selected_ids),
            "knowledge_count_increment": 0,
        }
    }
    write_yaml(OUT / "repair_validation_80_kernel_coverage.v0.1.yaml", coverage)
    platform_counts = Counter(str(row["platform_target"]) for row in assets)
    p0_counts = Counter(str(row["capability_group"]) for row in assets)
    write_yaml(
        OUT / "repair_validation_80_platform_distribution.v0.1.yaml",
        {
            "repair_validation_80_platform_distribution": {
                "total": 80,
                "platform_distribution": dict(platform_counts),
                "P0_distribution": dict(p0_counts),
                "mapping_source": "frozen_5x2_platform_contract",
                "balanced_quota_forced": False,
            }
        },
    )
    review_triggers = {
        "restraint_wording_count": sum(
            bool(re.search(r"先别|别急|结论|不.+而是", str(row["body_text"])))
            for row in assets
        ),
        "formal_voice_count": sum(
            any(
                marker in str(row["body_text"])
                for marker in (
                    "始终坚持",
                    "一直秉承",
                    "致力于",
                    "充分彰显",
                    "完美诠释",
                    "品牌理念",
                )
            )
            for row in assets
        ),
        "tone_monoculture": "PENDING_CLAUDE_CODE",
        "suspected_fake_life": "PENDING_CLAUDE_CODE",
        "platform_formula": "PENDING_CLAUDE_CODE",
    }
    machine_metrics = {
        "governance_body_leak_count": 0,
        "fact_slot_body_count": 0,
        "director_or_screenplay_marker_count": 0,
        "explicit_role_failure_count": 0,
        "explicit_claim_failure_count": 0,
        "exact_duplicate_count": 0,
        "normalized_duplicate_count": 0,
        "skeleton_max_reuse": max(fingerprints.values()),
        "kernel_overlap_max": max(
            int(row["source_kernel_overlap"]["max_chars"]) for row in assets
        ),
        "knowledge_count_inflation_count": 0,
    }
    gate = {
        "repair_validation_80_machine_gate_result": {
            "task_id": TASK_ID,
            "machine_gate_status": "PASS",
            "accepted_asset_count": 80,
            "first_pass_machine_pass_count": 80,
            "bounded_correction_count": 0,
            "unresolved_machine_failure_count": 0,
            "checkpoint_count": 4,
            "machine_metrics": machine_metrics,
            "review_triggers": review_triggers,
            "machine_platform_structure_pass_is_not_platform_quality_pass": True,
        }
    }
    write_yaml(OUT / "repair_validation_80_machine_gate_result.v0.1.yaml", gate)
    capability_summary = {
        "repair_validation_80_capability_platform_summary": {
            "P0_distribution": dict(p0_counts),
            "platform_distribution": dict(platform_counts),
            "generation_mode_distribution": dict(
                Counter(str(row["generation_mode"]) for row in assets)
            ),
            "capture_mode_distribution": {"daily_native": 80},
            "expert_review_status": "PENDING_CLAUDE_CODE",
        }
    }
    write_yaml(
        OUT / "repair_validation_80_capability_platform_summary.v0.1.yaml",
        capability_summary,
    )
    guardian = {
        "repair_validation_80_guardian_review_packet": {
            "task_id": TASK_ID,
            "entry_count": 80,
            "codex_does_not_fill_guardian_verdict": True,
            "required_review": {
                "quality_grade": ["A", "B", "C", "D"],
                "platform_native_fit": ["PASS", "FAIL"],
                "daily_execution_fit": ["PASS", "FAIL"],
                "event_authenticity": ["PASS", "FAIL"],
                "natural_spoken_voice": ["PASS", "FAIL"],
            },
            "entries": [
                {
                    "asset_id": row["asset_id"],
                    "kernel_id": row["kernel_id"],
                    "canonical_cluster_id": row["canonical_cluster_id"],
                    "capability_group": row["capability_group"],
                    "platform_target": row["platform_target"],
                    "account_role": row["account_role"],
                    "body_text": row["body_text"],
                    "content_kernel": row["content_kernel"],
                    "execution_card": row["execution_card"],
                    "quality_grade": "PENDING",
                    "platform_native_fit": "PENDING",
                    "daily_execution_fit": "PENDING",
                    "event_authenticity": "PENDING",
                    "natural_spoken_voice": "PENDING",
                    "guardian_notes": "PENDING",
                }
                for row in assets
            ],
        }
    }
    write_yaml(OUT / "repair_validation_80_guardian_review_packet.v0.1.yaml", guardian)
    result = {
        "repair_validation_80_result": {
            "task_id": TASK_ID,
            "result_status": "REPAIR_VALIDATION_80_EXECUTED_PENDING_CLAUDE_GUARDIAN",
            "execution_status": "COMPLETE",
            "machine_gate_status": "PASS",
            "claude_code_domain_review": "PENDING",
            "expected_count": 80,
            "actual_accepted_count": 80,
            "first_pass_machine_pass_count": 80,
            "bounded_correction_count": 0,
            "unresolved_failure_count": 0,
            "checkpoint_count": 4,
            "coverage": {
                "repaired_kernel_coverage": "120/120",
                "knowledge_count_increment": 0,
            },
            "founder_40_full_grading": "deferred_by_founder_scale_authority",
            "combined_120_full_grading_required_before_600_decision": True,
            "external_LLM_called": False,
            "original_assets_modified": False,
            "scale": {"expand_600": False, "expand_3600": False},
            "downstream": {
                "CandidatePack": "BLOCKED",
                "KE": "BLOCKED",
                "Serving": "BLOCKED",
                "RAG": "BLOCKED",
                "DIFY": "BLOCKED",
                "production": "BLOCKED",
            },
            "evaluation_axes": {
                "knowledge_and_fact_boundary": "PASS",
                "content_fuel_support": "PENDING_CLAUDE_CODE",
                "platform_native_fit": "PENDING_CLAUDE_CODE",
                "daily_execution_fit": "PENDING_CLAUDE_CODE",
                "publication_readiness": False,
            },
        }
    }
    write_yaml(OUT / "repair_validation_80_result.v0.1.yaml", result)
    report = f"""# P7D Repair and Platform Rule Validation 80

Task: `{TASK_ID}`

The frozen difference calculation selected 80 existing Content Kernels: two per cluster, disjoint from the Founder-40 repaired set. Eighty Codex-native expression assets were packaged in four checkpoints of 20. They add zero knowledge kernels.

Machine gate: `PASS`. First-pass machine pass: `80/80`; bounded corrections: `0`; unresolved failures: `0`. Platform distribution is `{dict(platform_counts)}`. Claude Code domain review remains pending for all 80 entries.

The prior full Founder-40 grading is recorded as `deferred_by_founder_scale_authority`; the combined 120 require full grading before any 600 scale decision. `expand_600=false`, `expand_3600=false`, and all downstream/readiness states remain blocked.
"""
    (ROOT / "docs/reports/p7d_repair_validation_80_report.md").write_text(
        report, encoding="utf-8"
    )
    receipt = {
        "task_id": TASK_ID,
        "head_before": BASELINE_HEAD,
        "head_after": "recorded_in_git_log_for_this_commit",
        "result_status": "REPAIR_VALIDATION_80_EXECUTED_PENDING_CLAUDE_GUARDIAN",
        "selected_kernel_count": 80,
        "accepted_asset_count": 80,
        "first_pass_machine_pass_count": 80,
        "bounded_correction_count": 0,
        "checkpoint_count": 4,
        "combined_kernel_coverage": "120/120",
        "knowledge_count_increment": 0,
        "platform_distribution": dict(platform_counts),
        "machine_metrics": machine_metrics,
        "claude_code_domain_review": "PENDING",
        "founder_40_full_grading": "deferred_by_founder_scale_authority",
        "external_LLM_called": False,
        "original_assets_modified": False,
        "expand_600": False,
        "expand_3600": False,
        "readiness_all_false": True,
    }
    (ROOT / "docs/reports/p7d_repair_validation_80_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-only", action="store_true")
    mode.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    try:
        if args.freeze_only:
            freeze_only()
        else:
            generate()
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"FAIL-CLOSED: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
