#!/usr/bin/env python3
"""Fail-closed checker for the scoped P7D everyday-native 5x2 probe."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


TASK_ID = "GKB-P7D-EVERYDAY-NATIVE-PLATFORM-VARIANT-CONTRACT-AND-10-PROBE-001"
BASELINE_HEAD = "bbee53ab33132c567ce6d4dd539fef5339ab9b40"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
MID_REL = f"{RUN_REL}/midbatch_320_001"
PARENT_REL = f"{MID_REL}/founder_40_repair_001"
OUT_REL = f"{PARENT_REL}/platform_native_5x2_001"
PARENT_ASSET_REL = f"{PARENT_REL}/founder_40_repaired_assets.v0.1.jsonl"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
LEDGER_MD_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"
REPORT_REL = "ci/reports/p7d_platform_native_5x2_report.v0.1.json"
FIXTURE_REL = "ci/fixtures/p7d_platform_native_5x2/fixture_manifest.v0.1.yaml"

REQUIRED_ARTIFACTS = (
    "accepted_guardian_and_founder_review_evidence.v0.1.yaml",
    "founder_everyday_native_direction.v0.1.yaml",
    "platform_native_everyday_expression_contract.v0.1.yaml",
    "parent_kernel_selection_manifest.v0.1.yaml",
    "platform_native_expression_variants.v0.1.jsonl",
    "parent_platform_pair_comparison.v0.1.yaml",
    "platform_native_everyday_gate_result.v0.1.yaml",
    "low_cost_execution_audit.v0.1.yaml",
    "platform_native_guardian_review_packet.v0.1.yaml",
    "platform_native_founder_review_packet.v0.1.yaml",
    "platform_native_5x2_result.v0.1.yaml",
)

PLATFORM_MATRIX = {
    "P0_01": {"wechat_channels", "moments"},
    "P0_02": {"douyin", "wechat_channels"},
    "P0_03": {"xiaohongshu", "live"},
    "P0_04": {"douyin", "moments"},
    "P0_05": {"xiaohongshu", "live"},
}
PLATFORM_SHAPES = {
    "douyin": (
        "short_video_spoken_event",
        {
            "in_progress_opening",
            "visible_action_early",
            "one_natural_spoken_hook",
            "short_spoken_body",
            "natural_interaction_or_store_handoff",
        },
    ),
    "xiaohongshu": (
        "note_title_and_body",
        {
            "searchable_title",
            "first_person_observation",
            "concrete_detail",
            "save_worthy_judgment",
            "non_advertorial_close",
        },
    ),
    "wechat_channels": (
        "trust_based_work_story",
        {
            "trust_based_opening",
            "complete_small_work_event",
            "operator_or_role_judgment",
            "natural_spoken_close",
            "non_clickbait_handoff",
        },
    ),
    "moments": (
        "daily_private_caption",
        {
            "short_daily_note",
            "one_event",
            "one_visible_detail",
            "personal_observation",
            "optional_soft_private_followup",
        },
    ),
    "live": (
        "live_talk_card",
        {
            "show_object",
            "ask_customer_use_case",
            "compare_touch_or_try",
            "safe_observation",
            "answer_boundary",
            "next_interaction",
        },
    ),
}
EVENT_FIELDS = {
    "event_type",
    "event_binding_state",
    "workplace_setting",
    "event_trigger",
    "real_role",
    "observable_action",
    "apparel_or_display_object",
    "visible_detail",
    "choice_or_change",
    "situational_judgment",
    "implicit_theme",
    "natural_next_action",
    "non_claimed_result",
}
KERNEL_FIELDS = {
    "object_anchor",
    "human_subject",
    "human_action",
    "scene_premise",
    "business_judgment",
    "tradeoff_or_tension",
    "spoken_line_seed",
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
BODY_META_MARKERS = (
    "CandidatePack",
    "generation_allowed",
    "production_servable",
    "readiness",
    "治理门",
    "证据策略",
    "Content Kernel",
    "Event Spine",
    "P0_",
)
BODY_SLOT_MARKERS = ("【", "】", "{{", "}}", "<slot", "[品牌", "[商品", "[门店")
BODY_DIRECTOR_MARKERS = (
    "短剧",
    "剧情反转",
    "导演",
    "演员",
    "布光",
    "分镜",
    "第一镜",
    "第二镜",
    "第三镜",
    "宣传片",
)
FAKE_PERSON_PATTERN = re.compile(
    r"(?:王|李|张|陈|刘|赵)(?:姐|女士|先生|小姐)|顾客说|客人说|有位顾客"
)
HARD_CLAIM_PATTERN = re.compile(
    r"(?<!不)保证.{0,5}(显白|显高|显瘦|耐穿|舒适)|"
    r"一定.{0,5}(显白|显高|显瘦|耐穿|舒适)|卖爆|销量(?:增长|提升)|转化率(?:增长|提升)|任何身材"
)
ROLE_FAILURE_PATTERN = re.compile(
    r"顾客.{0,6}(调整陈列|修改版型|工艺复核)|"
    r"导购.{0,6}(修改版型|改工艺|代替版师)|"
    r"版师.{0,6}(催顾客购买|代替导购成交)"
)
RESTRAINT_TRIGGER_PATTERN = re.compile(r"先别|别急|结论|不.+而是")
FORMAL_TRIGGER_PATTERN = re.compile(
    r"始终坚持|一直秉承|致力于|充分彰显|完美诠释|品牌理念|匠心打造|赋能消费者|长期主义|品质的态度"
)
SLANG_TRIGGER_PATTERN = re.compile(r"家人们|绝绝子|闭眼入|yyds|狠狠爱|天花板")
SCRIPTED_LIFE_TRIGGER_PATTERN = re.compile(
    r"短剧|剧情|反转|演员|布光|分镜|台词|男主|女主|传奇"
)
ALLOWED_PREFIXES = (
    f"{OUT_REL}/",
    "ci/checkers/check_p7d_platform_native_5x2.py",
    "ci/fixtures/p7d_platform_native_5x2/",
    REPORT_REL,
    LEDGER_REL,
    LEDGER_MD_REL,
    "docs/reports/p7d_platform_native_5x2_report.md",
    "docs/reports/p7d_platform_native_5x2_receipt.json",
)


def stable_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def read_yaml(path: Path) -> Any:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if value is None:
        raise ValueError(f"empty YAML: {path}")
    return value


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
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


def run_git(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
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


def body_shingles(text: str, size: int = 3) -> set[str]:
    value = normalize(text)
    if len(value) < size:
        return {value} if value else set()
    return {value[index : index + size] for index in range(len(value) - size + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def longest_common_substring(left: str, right: str) -> tuple[int, str]:
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
        previous = current
    return best, a[best_end - best : best_end]


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for nested in value.values() for item in flatten_strings(nested)]
    if isinstance(value, list):
        return [item for nested in value for item in flatten_strings(nested)]
    return []


def max_kernel_overlap(
    body: str, parents: list[dict[str, Any]]
) -> tuple[int, str, str]:
    best = (0, "", "")
    for parent in parents:
        for segment in flatten_strings(parent["content_kernel"]):
            if len(normalize(segment)) < 2:
                continue
            length, fragment = longest_common_substring(body, segment)
            if length > best[0]:
                best = (length, str(parent["repair_id"]), fragment)
    return best


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


def deterministic_selection(
    parents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for p0_group in sorted(PLATFORM_MATRIX):
        candidates = []
        for row in parents:
            metadata = row.get("review_metadata", {})
            role_gate = metadata.get("role_action_review", {}).get(
                "deterministic_status"
            )
            skeleton_gate = metadata.get("skeleton_review", {}).get(
                "machine_fingerprint_status"
            )
            kernel = row.get("content_kernel", {})
            if (
                row.get("p0_group") == p0_group
                and row.get("original_review_class") in {"A", "B"}
                and role_gate == "PASS"
                and skeleton_gate == "PASS"
                and KERNEL_FIELDS <= set(kernel)
            ):
                candidates.append(row)
        a_rows = sorted(
            (row for row in candidates if row["original_review_class"] == "A"),
            key=lambda row: str(row["original_output_id"]),
        )
        b_rows = sorted(
            (row for row in candidates if row["original_review_class"] == "B"),
            key=lambda row: str(row["original_output_id"]),
        )
        eligible = a_rows if a_rows else b_rows
        if not eligible:
            raise ValueError(f"{p0_group} has no eligible A/B parent")
        index = (len(eligible) - 1) // 2
        choice = eligible[index]
        selected.append(choice)
        audit.append(
            {
                "capability_group": p0_group,
                "eligible_set_rule": "A_only_when_A_exists_else_B_only",
                "eligible_review_class": "A" if a_rows else "B",
                "stable_sort_key": "original_output_id_ascending",
                "even_tiebreak": "lower_median_zero_based_index_(n_minus_1)_floor_div_2",
                "eligible_parent_ids": [row["repair_id"] for row in eligible],
                "eligible_source_output_ids": [
                    row["original_output_id"] for row in eligible
                ],
                "selection_ordinal_zero_based": index,
                "selected_parent_id": choice["repair_id"],
                "selected_source_output_id": choice["original_output_id"],
                "selected_parent_payload_digest": stable_digest(choice),
            }
        )
    return selected, audit


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_bundle(bundle: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    parents = bundle["parents"]
    selection = bundle["selection"]["parent_kernel_selection_manifest"]
    variants = bundle["variants"]
    comparison = bundle["comparison"]["parent_platform_pair_comparison"]
    contract = bundle["contract"]["platform_native_everyday_expression_contract"]
    direction = bundle["direction"]["founder_everyday_native_direction"]
    evidence = bundle["evidence"]["accepted_guardian_and_founder_review_evidence"]
    gate = bundle["gate"]["platform_native_everyday_gate_result"]
    low_cost = bundle["low_cost"]["low_cost_execution_audit"]
    guardian = bundle["guardian"]["platform_native_guardian_review_packet"]
    founder = bundle["founder"]["platform_native_founder_review_packet"]
    result = bundle["result"]["platform_native_5x2_result"]
    receipt = bundle["receipt"]

    try:
        selected, expected_audit = deterministic_selection(parents)
    except (KeyError, TypeError, ValueError) as exc:
        return [f"selection recompute failed: {exc}"], {}
    selected_by_group = {row["p0_group"]: row for row in selected}
    entries = selection.get("entries", [])
    require(
        errors,
        selection.get("parent_kernel_count") == 5,
        "selection parent count must be 5",
    )
    require(errors, len(entries) == 5, "selection manifest must have 5 entries")
    require(
        errors,
        selection.get("selection_digest") == stable_digest(expected_audit),
        "selection digest drift",
    )
    require(
        errors,
        selection.get("selection_reproducible") is True,
        "selection not reproducible",
    )
    require(
        errors,
        selection.get("source_asset_path") == PARENT_ASSET_REL,
        "selection source path drift",
    )
    require(
        errors,
        selection.get("source_asset_sha256")
        == hashlib.sha256(bundle["parent_asset_bytes"]).hexdigest(),
        "selection source asset digest drift",
    )
    require(
        errors,
        selection.get("selection_algorithm")
        == {
            "group_by": "p0_group",
            "review_class_priority": "A_only_when_A_exists_else_B_only",
            "stable_sort": "original_output_id_ascending",
            "median_rule": "lower_median_zero_based_index_(n_minus_1)_floor_div_2",
        },
        "selection algorithm/tiebreak not frozen",
    )
    manifest_by_group: dict[str, dict[str, Any]] = {}
    for expected, entry in zip(expected_audit, entries, strict=False):
        p0_group = str(expected["capability_group"])
        manifest_by_group[p0_group] = entry
        for key, expected_value in expected.items():
            require(
                errors,
                entry.get(key) == expected_value,
                f"selection entry drift: {p0_group}.{key}",
            )
        parent = selected_by_group[p0_group]
        event = entry.get("event_spine", {})
        fact = entry.get("fact_boundary", {})
        require(
            errors,
            EVENT_FIELDS <= set(event),
            f"event spine fields missing: {p0_group}",
        )
        require(
            errors,
            event.get("event_binding_state")
            in {"source_observed", "brand_confirmed", "bounded_routine_work_prototype"},
            f"invalid event binding state: {p0_group}",
        )
        require(
            errors,
            entry.get("parent_kernel_id") == parent.get("bound_kernel_candidate_id"),
            f"parent id drift: {p0_group}",
        )
        require(
            errors,
            entry.get("source_repair_id") == parent.get("repair_id"),
            f"repair id drift: {p0_group}",
        )
        require(
            errors,
            entry.get("source_assignment_ref") == parent.get("bound_assignment_id"),
            f"assignment drift: {p0_group}",
        )
        require(
            errors,
            entry.get("parent_kernel_digest")
            == stable_digest(parent.get("content_kernel")),
            f"kernel digest drift: {p0_group}",
        )
        require(
            errors,
            entry.get("core_business_judgment")
            == parent["content_kernel"]["business_judgment"],
            f"judgment drift: {p0_group}",
        )
        require(
            errors,
            entry.get("account_role") == parent.get("account_role"),
            f"account role drift: {p0_group}",
        )
        require(
            errors,
            entry.get("event_spine_digest") == stable_digest(event),
            f"event digest drift: {p0_group}",
        )
        require(
            errors,
            entry.get("fact_boundary_digest") == stable_digest(fact),
            f"fact digest drift: {p0_group}",
        )
        require(
            errors,
            fact.get("fact_boundary_mode")
            == parent["review_metadata"]["fact_boundary_mode"],
            f"fact mode drift: {p0_group}",
        )
        require(
            errors,
            fact.get("required_fact_slots")
            == parent["review_metadata"]["required_fact_slots"],
            f"fact slots drift: {p0_group}",
        )
        require(
            errors,
            fact.get("forbidden_claims")
            == parent["review_metadata"]["forbidden_claims"],
            f"forbidden claims drift: {p0_group}",
        )

    require(errors, len(variants) == 10, "variant count must be 10")
    require(
        errors,
        len({row.get("variant_id") for row in variants}) == 10,
        "variant ids must be unique",
    )
    by_group: dict[str, list[dict[str, Any]]] = {
        group: [row for row in variants if row.get("capability_group") == group]
        for group in PLATFORM_MATRIX
    }
    require(
        errors,
        set(row.get("capability_group") for row in variants) == set(PLATFORM_MATRIX),
        "P0 coverage drift",
    )
    platform_counts = Counter(str(row.get("platform_target")) for row in variants)
    require(
        errors,
        platform_counts == Counter({name: 2 for name in PLATFORM_SHAPES}),
        "platform distribution must be 2 each",
    )

    body_values: list[str] = []
    normalized_values: list[str] = []
    kernel_overlaps: list[int] = []
    opening_counts: Counter[str] = Counter()
    closing_counts: Counter[str] = Counter()
    for row in variants:
        variant_id = str(row.get("variant_id"))
        p0_group = str(row.get("capability_group"))
        platform = str(row.get("platform_target"))
        entry = manifest_by_group.get(p0_group, {})
        body = str(row.get("body_text", ""))
        payload = row.get("platform_payload", {})
        expected_shape = PLATFORM_SHAPES.get(platform)
        require(errors, len(normalize(body)) >= 35, f"body too thin: {variant_id}")
        require(
            errors,
            platform in PLATFORM_MATRIX.get(p0_group, set()),
            f"matrix drift: {variant_id}",
        )
        if expected_shape is None:
            errors.append(f"unknown platform: {variant_id}")
        else:
            require(
                errors,
                row.get("payload_shape") == expected_shape[0],
                f"payload shape drift: {variant_id}",
            )
            require(
                errors,
                isinstance(payload, dict) and set(payload) == expected_shape[1],
                f"payload keys drift: {variant_id}",
            )
            require(
                errors,
                all(
                    isinstance(value, str) and value.strip()
                    for value in payload.values()
                ),
                f"empty payload field: {variant_id}",
            )
        fixed_fields = (
            "parent_kernel_id",
            "source_repair_id",
            "source_assignment_ref",
            "parent_kernel_digest",
            "event_spine_digest",
            "fact_boundary_digest",
            "core_business_judgment",
            "prohibited_claims",
            "account_role",
            "capture_mode",
        )
        for key in fixed_fields:
            require(
                errors,
                row.get(key) == entry.get(key),
                f"parent binding drift: {variant_id}.{key}",
            )
        require(
            errors,
            row.get("event_spine") == entry.get("event_spine"),
            f"event spine drift: {variant_id}",
        )
        require(
            errors,
            row.get("apparel_or_display_object")
            == entry.get("event_spine", {}).get("apparel_or_display_object"),
            f"object drift: {variant_id}",
        )
        role_voice = row.get("role_voice", {})
        require(
            errors,
            role_voice.get("account_role") == row.get("account_role"),
            f"role voice drift: {variant_id}",
        )
        for key in (
            "role_specific_vocabulary",
            "account_voice",
            "spoken_line",
            "colloquial_register",
            "prohibited_voice_patterns",
        ):
            require(
                errors,
                bool(role_voice.get(key)),
                f"role voice field missing: {variant_id}.{key}",
            )
        require(
            errors,
            not any(marker in body for marker in BODY_META_MARKERS),
            f"governance metadata in body: {variant_id}",
        )
        require(
            errors,
            not any(marker in body for marker in BODY_SLOT_MARKERS),
            f"fact slot in body: {variant_id}",
        )
        require(
            errors,
            not any(marker in body for marker in BODY_DIRECTOR_MARKERS),
            f"director/script marker in body: {variant_id}",
        )
        require(
            errors,
            FAKE_PERSON_PATTERN.search(body) is None,
            f"fabricated person/customer marker: {variant_id}",
        )
        require(
            errors,
            HARD_CLAIM_PATTERN.search(body) is None,
            f"unsupported hard claim: {variant_id}",
        )
        require(
            errors,
            ROLE_FAILURE_PATTERN.search(body) is None,
            f"explicit role/action failure: {variant_id}",
        )
        require(
            errors,
            row.get("body_digest") == hashlib.sha256(body.encode("utf-8")).hexdigest(),
            f"body digest drift: {variant_id}",
        )
        require(
            errors,
            row.get("normalized_body_digest")
            == hashlib.sha256(normalize(body).encode("utf-8")).hexdigest(),
            f"normalized digest drift: {variant_id}",
        )
        skeleton = row.get("skeleton_payload", {})
        require(
            errors,
            skeleton
            == {
                "p0_group": p0_group,
                "platform": platform,
                "payload_shape": row.get("payload_shape"),
                "opening_family": row.get("opening_family"),
                "closing_family": row.get("closing_family"),
                "event_type": row.get("event_spine", {}).get("event_type"),
                "real_role": row.get("event_spine", {}).get("real_role"),
                "action_family": row.get("event_spine", {}).get("observable_action"),
            },
            f"skeleton payload drift: {variant_id}",
        )
        require(
            errors,
            row.get("skeleton_fingerprint") == stable_digest(skeleton),
            f"skeleton digest drift: {variant_id}",
        )
        overlap, overlap_parent, overlap_fragment = max_kernel_overlap(body, parents)
        kernel_overlaps.append(overlap)
        require(
            errors,
            overlap <= 17,
            f"content kernel overlap exceeds 17: {variant_id}={overlap}",
        )
        require(
            errors,
            row.get("content_kernel_overlap")
            == {
                "max_chars": overlap,
                "matched_parent_repair_id": overlap_parent,
                "fragment": overlap_fragment,
                "threshold": 17,
            },
            f"kernel overlap report drift: {variant_id}",
        )
        execution = row.get("execution_card", {})
        required_execution = {
            "capture_mode": "daily_native",
            "dedicated_crew_count": 0,
            "actor_count": 0,
            "phone_count": 1,
            "production_time_minutes_max": 20,
            "simple_segment_count_max": 5,
            "fake_customer": False,
            "manufactured_conflict": False,
            "special_lighting_required": False,
            "scripted_performance_required": False,
        }
        for key, expected in required_execution.items():
            require(
                errors,
                execution.get(key) == expected,
                f"daily-native constraint drift: {variant_id}.{key}",
            )
        require(
            errors,
            row.get("generation_status") == "codex_native_scoped_expression_variant",
            f"generation status drift: {variant_id}",
        )
        require(
            errors,
            row.get("external_LLM_called") is False,
            f"external LLM flag true: {variant_id}",
        )
        require(
            errors,
            row.get("creates_new_knowledge_kernel") is False,
            f"variant counted as kernel: {variant_id}",
        )
        require(
            errors,
            row.get("knowledge_count_increment") == 0,
            f"knowledge count inflation: {variant_id}",
        )
        axes = row.get("evaluation_axes", {})
        require(
            errors,
            axes.get("knowledge_and_fact_boundary", {}).get("status") == "PASS",
            f"fact boundary not PASS: {variant_id}",
        )
        require(
            errors,
            axes.get("content_fuel_support", {}).get("status")
            == "INHERITED_B_PLUS_PARENT_EVIDENCE",
            f"content fuel axis drift: {variant_id}",
        )
        require(
            errors,
            axes.get("content_fuel_support", {}).get("not_rescored_as_platform_quality")
            is True,
            f"content fuel conflated with platform quality: {variant_id}",
        )
        require(
            errors,
            axes.get("platform_native_fit", {}).get("status") == "PENDING_HUMAN_REVIEW",
            f"platform self-approved: {variant_id}",
        )
        require(
            errors,
            axes.get("low_cost_execution_fit", {}).get("status")
            == "PENDING_HUMAN_REVIEW",
            f"execution self-approved: {variant_id}",
        )
        require(
            errors,
            axes.get("publication_readiness", {}).get("status") is False,
            f"publication readiness true: {variant_id}",
        )
        require(
            errors,
            row.get("claude_code_guardian_review") == "PENDING",
            f"guardian prefilled: {variant_id}",
        )
        require(
            errors,
            row.get("founder_platform_review") == "PENDING",
            f"founder review prefilled: {variant_id}",
        )
        readiness_failures = false_readiness_paths(
            row.get("readiness_flags", {}), f"variant[{variant_id}]"
        )
        errors.extend(f"readiness true: {path}" for path in readiness_failures)
        body_values.append(body)
        normalized_values.append(normalize(body))
        opening_counts[str(row.get("opening_family"))] += 1
        closing_counts[str(row.get("closing_family"))] += 1

    require(errors, len(set(body_values)) == 10, "exact duplicate body detected")
    require(
        errors, len(set(normalized_values)) == 10, "normalized duplicate body detected"
    )
    require(
        errors,
        max(opening_counts.values(), default=0) <= 2,
        "opening family reused more than twice",
    )
    require(
        errors,
        max(closing_counts.values(), default=0) <= 2,
        "closing family reused more than twice",
    )

    recomputed_pairs: list[dict[str, Any]] = []
    comparison_rows = comparison.get("pairs", [])
    require(
        errors,
        comparison.get("pair_count") == 5 and len(comparison_rows) == 5,
        "pair comparison count drift",
    )
    for p0_group, pair in by_group.items():
        require(errors, len(pair) == 2, f"{p0_group} must have exactly two variants")
        if len(pair) != 2:
            continue
        left, right = pair
        require(
            errors,
            {left.get("platform_target"), right.get("platform_target")}
            == PLATFORM_MATRIX[p0_group],
            f"pair platform drift: {p0_group}",
        )
        for key in (
            "parent_kernel_id",
            "event_spine_digest",
            "fact_boundary_digest",
            "core_business_judgment",
            "apparel_or_display_object",
            "prohibited_claims",
            "account_role",
            "capture_mode",
        ):
            require(
                errors,
                left.get(key) == right.get(key),
                f"pair fixed field drift: {p0_group}.{key}",
            )
        pair_jaccard = round(
            jaccard(
                body_shingles(left["body_text"]), body_shingles(right["body_text"])
            ),
            6,
        )
        overlap, fragment = longest_common_substring(
            left["body_text"], right["body_text"]
        )
        same_skeleton = left.get("skeleton_fingerprint") == right.get(
            "skeleton_fingerprint"
        )
        require(errors, pair_jaccard <= 0.70, f"pair Jaccard exceeds 0.70: {p0_group}")
        require(errors, overlap <= 24, f"pair verbatim overlap exceeds 24: {p0_group}")
        require(errors, not same_skeleton, f"same skeleton pair: {p0_group}")
        require(
            errors,
            left.get("payload_shape") != right.get("payload_shape"),
            f"label-only payload pair: {p0_group}",
        )
        row = next(
            (
                item
                for item in comparison_rows
                if item.get("capability_group") == p0_group
            ),
            {},
        )
        require(
            errors,
            row.get("parent_kernel_id") == left.get("parent_kernel_id"),
            f"pair parent report drift: {p0_group}",
        )
        require(
            errors,
            set(row.get("variant_ids", []))
            == {left.get("variant_id"), right.get("variant_id")},
            f"pair variant report drift: {p0_group}",
        )
        require(
            errors,
            set(row.get("platforms", [])) == PLATFORM_MATRIX[p0_group],
            f"pair platform report drift: {p0_group}",
        )
        require(
            errors,
            row.get("pair_jaccard_3_shingle") == pair_jaccard,
            f"pair Jaccard report drift: {p0_group}",
        )
        require(
            errors,
            row.get("pair_longest_verbatim_overlap_chars") == overlap,
            f"pair overlap report drift: {p0_group}",
        )
        require(
            errors,
            row.get("pair_longest_verbatim_fragment") == fragment,
            f"pair fragment report drift: {p0_group}",
        )
        require(
            errors,
            row.get("same_skeleton_fingerprint") is same_skeleton,
            f"pair skeleton report drift: {p0_group}",
        )
        require(
            errors,
            row.get("machine_thresholds_pass") is True,
            f"pair threshold report not PASS: {p0_group}",
        )
        require(
            errors,
            row.get("human_pair_differentiation_review") == "PENDING",
            f"pair human review prefilled: {p0_group}",
        )
        recomputed_pairs.append(
            {
                "p0_group": p0_group,
                "jaccard": pair_jaccard,
                "overlap": overlap,
                "same_skeleton": same_skeleton,
            }
        )

    require(
        errors,
        contract.get("contract_scope") == "platform_native_5x2_validation_only",
        "contract scope drift",
    )
    require(
        errors,
        contract.get("canonical_status") == "scoped_validation_contract",
        "contract canonical status drift",
    )
    for key in (
        "writes_to_ontology",
        "writes_to_CSO_canonical_axis",
        "writes_to_KE",
        "creates_new_knowledge_kernel",
    ):
        require(
            errors,
            contract.get(key) is False,
            f"contract escapes scoped boundary: {key}",
        )
    require(
        errors,
        contract.get("failure_codes_registered_globally") is False,
        "failure codes registered globally",
    )
    require(
        errors,
        contract.get("machine_pass_does_not_confirm_platform_quality") is True,
        "machine/human boundary missing",
    )
    require(
        errors,
        contract.get("daily_native_constraints")
        == {
            "capture_mode": "daily_native",
            "dedicated_crew_count": 0,
            "actor_count": 0,
            "phone_count": 1,
            "production_time_minutes_max": 20,
            "simple_segment_count_max": 5,
            "fake_customer": False,
            "manufactured_conflict": False,
            "special_lighting_required": False,
            "scripted_performance_required": False,
        },
        "contract daily-native limits drift",
    )
    require(
        errors,
        contract.get("restraint_policy")
        == {
            "keep_as": ["fact_boundary", "claim_safety", "not_overclaiming"],
            "not_default_as": [
                "opening_formula",
                "repeated_catchphrase",
                "universal_brand_voice",
                "universal_closing",
            ],
            "same_opening_family_max": 2,
            "same_closing_family_max": 2,
        },
        "restraint policy drift",
    )
    require(
        errors,
        direction.get("this_probe_capture_mode") == "daily_native",
        "founder direction capture mode drift",
    )
    require(
        errors,
        direction.get("this_probe_variant_count") == 10,
        "founder direction variant count drift",
    )
    require(
        errors,
        direction.get("does_not_create_canonical_CSO_axis") is True,
        "founder direction creates CSO axis",
    )
    require(
        errors,
        direction.get("formal_expression_allowed_as_small_minority") is True,
        "formal minority policy missing",
    )
    require(
        errors,
        direction.get("enterprise_narrative_and_vlog_default")
        == "daily_work_event_and_low_cost_realism",
        "enterprise/VLOG daily-native default drift",
    )

    hygiene = evidence.get("runtime_ab_002_record_hygiene", {})
    require(
        errors, hygiene.get("machine_gate") == "PASS", "AB-002 machine record drift"
    )
    require(
        errors,
        hygiene.get("founder_acceptance_scope") == "bounded",
        "AB-002 founder scope drift",
    )
    require(
        errors,
        hygiene.get("claude_content_level_review_separately_performed") is False,
        "AB-002 falsely marked Guardian-reviewed",
    )
    require(
        errors,
        hygiene.get("consumed_by_this_task") is False,
        "AB-002 improperly consumed",
    )

    expected_low_cost = {
        row.get("variant_id"): row.get("execution_card") for row in variants
    }
    low_cost_entries = low_cost.get("entries", [])
    require(
        errors,
        low_cost.get("variant_count") == 10 and len(low_cost_entries) == 10,
        "low-cost audit count drift",
    )
    require(
        errors,
        low_cost.get("all_daily_native") is True,
        "low-cost audit not all daily-native",
    )
    require(
        errors,
        low_cost.get("human_execution_reality_review") == "PENDING",
        "low-cost human review prefilled",
    )
    for item in low_cost_entries:
        variant_id = item.get("variant_id")
        expected = expected_low_cost.get(variant_id)
        require(
            errors,
            expected is not None,
            f"unknown low-cost audit variant: {variant_id}",
        )
        if expected is not None:
            require(
                errors,
                all(item.get(key) == value for key, value in expected.items()),
                f"low-cost audit drift: {variant_id}",
            )
        require(
            errors,
            item.get("machine_status") == "PASS",
            f"low-cost machine status drift: {variant_id}",
        )

    guardian_entries = guardian.get("entries", [])
    require(
        errors,
        guardian.get("variant_count") == 10 and len(guardian_entries) == 10,
        "guardian packet count drift",
    )
    require(
        errors,
        guardian.get("codex_does_not_fill_guardian_verdict") is True,
        "Codex allowed to fill guardian verdict",
    )
    require(
        errors,
        all(item.get("guardian_verdict") == "PENDING" for item in guardian_entries),
        "guardian verdict prefilled",
    )
    founder_pairs = founder.get("pairs", [])
    require(
        errors,
        founder.get("pair_count") == 5 and len(founder_pairs) == 5,
        "founder packet pair count drift",
    )
    require(
        errors,
        founder.get("codex_does_not_fill_founder_verdict") is True,
        "Codex allowed to fill founder verdict",
    )
    require(
        errors,
        all(item.get("founder_pair_verdict") == "PENDING" for item in founder_pairs),
        "founder verdict prefilled",
    )

    metrics = {
        "governance_body_leak_count": sum(
            any(marker in body for marker in BODY_META_MARKERS) for body in body_values
        ),
        "director_or_screenplay_marker_count": sum(
            any(marker in body for marker in BODY_DIRECTOR_MARKERS)
            for body in body_values
        ),
        "fact_slot_body_count": sum(
            any(marker in body for marker in BODY_SLOT_MARKERS) for body in body_values
        ),
        "explicit_role_failure_count": sum(
            FAKE_PERSON_PATTERN.search(body) is not None
            or ROLE_FAILURE_PATTERN.search(body) is not None
            for body in body_values
        ),
        "explicit_claim_failure_count": sum(
            HARD_CLAIM_PATTERN.search(body) is not None for body in body_values
        ),
        "exact_duplicate_count": len(body_values) - len(set(body_values)),
        "normalized_duplicate_count": len(normalized_values)
        - len(set(normalized_values)),
        "max_pair_jaccard": max(
            (row["jaccard"] for row in recomputed_pairs), default=0.0
        ),
        "max_pair_verbatim_overlap": max(
            (row["overlap"] for row in recomputed_pairs), default=0
        ),
        "same_skeleton_pair_count": sum(
            row["same_skeleton"] for row in recomputed_pairs
        ),
        "kernel_overlap_max": max(kernel_overlaps, default=0),
        "knowledge_count_inflation_count": sum(
            row.get("knowledge_count_increment") != 0 for row in variants
        ),
        "low_cost_constraint_failure_count": sum(
            item.get("machine_status") != "PASS" for item in low_cost_entries
        ),
    }
    require(errors, gate.get("task_id") == TASK_ID, "gate task id drift")
    require(
        errors,
        gate.get("machine_hard_gate") == "PASS",
        "machine gate self-report not PASS",
    )
    require(errors, gate.get("parent_kernel_count") == 5, "gate parent count drift")
    require(
        errors, gate.get("expression_variant_count") == 10, "gate variant count drift"
    )
    require(
        errors,
        gate.get("knowledge_count_increment") == 0,
        "gate knowledge count inflation",
    )
    require(
        errors,
        gate.get("platform_distribution") == dict(platform_counts),
        "gate platform distribution drift",
    )
    require(
        errors,
        gate.get("machine_metrics") == metrics,
        "gate metrics do not match independent recompute",
    )
    expected_pair_integrity = {
        "event_spine_drift_count": 0,
        "fact_boundary_drift_count": 0,
        "role_drift_count": 0,
        "core_judgment_drift_count": 0,
    }
    require(
        errors,
        gate.get("pair_integrity") == expected_pair_integrity,
        "gate pair integrity drift",
    )
    axes = gate.get("evaluation_axes", {})
    require(
        errors,
        axes.get("knowledge_and_fact_boundary") == "PASS",
        "gate fact boundary axis drift",
    )
    require(
        errors,
        axes.get("content_fuel_support") == "INHERITED_B_PLUS_PARENT_EVIDENCE",
        "gate content fuel axis drift",
    )
    require(
        errors,
        axes.get("platform_native_fit") == "PENDING",
        "gate platform quality self-approved",
    )
    require(
        errors,
        axes.get("low_cost_execution_fit") == "PENDING",
        "gate execution quality self-approved",
    )
    require(
        errors,
        axes.get("publication_readiness") is False,
        "gate publication readiness true",
    )
    expected_triggers = {
        "restraint_tone_repetition": sum(
            RESTRAINT_TRIGGER_PATTERN.search(body) is not None for body in body_values
        ),
        "formal_voice_trigger_count": sum(
            FORMAL_TRIGGER_PATTERN.search(body) is not None for body in body_values
        ),
        "slang_stacking_trigger_count": sum(
            SLANG_TRIGGER_PATTERN.search(body) is not None for body in body_values
        ),
        "scripted_life_trigger_count": sum(
            SCRIPTED_LIFE_TRIGGER_PATTERN.search(body) is not None
            for body in body_values
        ),
        "platform_generic_trigger_count": 0,
        "opening_family_max_reuse": max(opening_counts.values(), default=0),
        "closing_family_max_reuse": max(closing_counts.values(), default=0),
        "tone_monoculture_human_review": "PENDING",
    }
    require(
        errors,
        gate.get("review_triggers") == expected_triggers,
        "review trigger report drift",
    )

    require(errors, result.get("task_id") == TASK_ID, "result task id drift")
    require(
        errors,
        result.get("result_status")
        == "PLATFORM_NATIVE_10_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW",
        "result status exceeds authorization",
    )
    require(
        errors, result.get("machine_hard_gate") == "PASS", "result machine gate drift"
    )
    require(
        errors,
        result.get("parent_knowledge_kernel_count") == 5,
        "result parent count drift",
    )
    require(
        errors,
        result.get("expression_variant_count") == 10,
        "result variant count drift",
    )
    require(
        errors,
        result.get("knowledge_count_increment") == 0,
        "result knowledge count inflation",
    )
    require(
        errors,
        result.get("platform_native_fit") == "PENDING",
        "result platform quality self-approved",
    )
    require(
        errors,
        result.get("low_cost_execution_fit") == "PENDING",
        "result execution quality self-approved",
    )
    require(
        errors,
        result.get("publication_readiness") is False,
        "result publication readiness true",
    )
    require(
        errors,
        result.get("claude_code_guardian_status") == "PENDING",
        "result guardian review prefilled",
    )
    require(
        errors,
        result.get("founder_platform_review_status") == "PENDING",
        "result founder review prefilled",
    )
    require(
        errors,
        result.get("founder_40_second_review_status") == "PENDING",
        "founder 40 review prefilled",
    )
    require(
        errors,
        result.get("external_LLM_called") is False,
        "result external LLM flag true",
    )
    require(
        errors,
        result.get("parent_assets_modified") is False,
        "result claims parent modification",
    )
    require(
        errors,
        result.get("scale")
        == {"expand_80": False, "expand_600": False, "expand_3600": False},
        "scale unlocked",
    )
    require(
        errors,
        result.get("downstream")
        == {
            "CandidatePack": "BLOCKED",
            "KE": "BLOCKED",
            "Serving": "BLOCKED",
            "RAG": "BLOCKED",
            "DIFY": "BLOCKED",
            "production": "BLOCKED",
        },
        "downstream unblocked",
    )
    require(errors, receipt.get("task_id") == TASK_ID, "receipt task id drift")
    require(
        errors, receipt.get("head_before") == BASELINE_HEAD, "receipt baseline drift"
    )
    require(
        errors,
        receipt.get("head_after") == "recorded_in_git_log_for_this_commit",
        "receipt commit placeholder drift",
    )
    require(
        errors,
        receipt.get("result_status")
        == "PLATFORM_NATIVE_10_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW",
        "receipt result overclaim",
    )
    require(
        errors,
        receipt.get("selected_parent_ids")
        == [entry["source_repair_id"] for entry in entries],
        "receipt parent ids drift",
    )
    require(
        errors,
        receipt.get("selection_digest") == selection.get("selection_digest"),
        "receipt selection digest drift",
    )
    require(
        errors,
        receipt.get("machine_metrics") == metrics,
        "receipt machine metrics drift",
    )
    require(
        errors,
        receipt.get("knowledge_count_increment") == 0,
        "receipt knowledge count inflation",
    )
    require(
        errors,
        receipt.get("platform_native_fit") == "PENDING",
        "receipt platform quality self-approved",
    )
    require(
        errors,
        receipt.get("low_cost_execution_fit") == "PENDING",
        "receipt execution quality self-approved",
    )
    require(
        errors,
        receipt.get("publication_readiness") is False,
        "receipt publication readiness true",
    )
    require(
        errors,
        receipt.get("external_LLM_called") is False,
        "receipt external LLM flag true",
    )
    require(
        errors,
        receipt.get("parent_assets_modified") is False,
        "receipt parent modification flag true",
    )
    require(
        errors,
        all(
            receipt.get(key) is False
            for key in ("expand_80", "expand_600", "expand_3600")
        ),
        "receipt scale unlocked",
    )
    require(
        errors,
        receipt.get("readiness_all_false") is True,
        "receipt readiness summary drift",
    )
    errors.extend(f"readiness true: {path}" for path in false_readiness_paths(bundle))
    return sorted(set(errors)), metrics


def load_bundle(root: Path) -> dict[str, Any]:
    out = root / OUT_REL
    return {
        "parents": read_jsonl(root / PARENT_ASSET_REL),
        "parent_asset_bytes": (root / PARENT_ASSET_REL).read_bytes(),
        "selection": read_yaml(out / "parent_kernel_selection_manifest.v0.1.yaml"),
        "variants": read_jsonl(out / "platform_native_expression_variants.v0.1.jsonl"),
        "comparison": read_yaml(out / "parent_platform_pair_comparison.v0.1.yaml"),
        "contract": read_yaml(
            out / "platform_native_everyday_expression_contract.v0.1.yaml"
        ),
        "direction": read_yaml(out / "founder_everyday_native_direction.v0.1.yaml"),
        "evidence": read_yaml(
            out / "accepted_guardian_and_founder_review_evidence.v0.1.yaml"
        ),
        "gate": read_yaml(out / "platform_native_everyday_gate_result.v0.1.yaml"),
        "low_cost": read_yaml(out / "low_cost_execution_audit.v0.1.yaml"),
        "guardian": read_yaml(out / "platform_native_guardian_review_packet.v0.1.yaml"),
        "founder": read_yaml(out / "platform_native_founder_review_packet.v0.1.yaml"),
        "result": read_yaml(out / "platform_native_5x2_result.v0.1.yaml"),
        "receipt": read_json(
            root / "docs/reports/p7d_platform_native_5x2_receipt.json"
        ),
    }


def validate_parent_assets_unchanged(root: Path, errors: list[str]) -> None:
    baseline_paths = [
        line.strip()
        for line in git_text(
            root, "ls-tree", "-r", "--name-only", BASELINE_HEAD, "--", PARENT_REL
        ).splitlines()
        if line.strip()
    ]
    require(errors, bool(baseline_paths), "baseline parent repair tree is empty")
    for relative in baseline_paths:
        current = root / relative
        require(errors, current.is_file(), f"baseline parent asset missing: {relative}")
        if not current.is_file():
            continue
        baseline = run_git(root, "show", f"{BASELINE_HEAD}:{relative}").stdout
        require(
            errors,
            current.read_bytes() == baseline,
            f"parent asset modified: {relative}",
        )


def validate_ledger(root: Path, errors: list[str]) -> None:
    current = read_yaml(root / LEDGER_REL)["grc_3600_execution_plan_status"]
    baseline_text = git_text(root, "show", f"{BASELINE_HEAD}:{LEDGER_REL}")
    baseline = yaml.safe_load(baseline_text)["grc_3600_execution_plan_status"]
    require(errors, "route_migration_11" in current, "route_migration_11 missing")
    stripped = copy.deepcopy(current)
    migration = stripped.pop("route_migration_11", None)
    require(
        errors,
        stripped == baseline,
        "ledger changed outside additive route_migration_11",
    )
    expected = {
        "applied_by_task": TASK_ID,
        "applied_from": "founder_authorized_after_claude_code_prompt_pre_review_conditional_pass",
        "operational_state_only": True,
        "no_existing_step_status_changed": True,
        "no_old_checker_edited": True,
        "no_readiness_flipped": True,
        "result": "PLATFORM_NATIVE_10_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW",
        "result_path": f"{OUT_REL}/platform_native_5x2_result.v0.1.yaml",
        "parent_kernel_count": 5,
        "expression_variant_count": 10,
        "knowledge_count_increment": 0,
        "capture_mode": "daily_native",
        "external_LLM_called": False,
        "parent_assets_modified": False,
        "claude_code_guardian_review": "PENDING",
        "founder_platform_review": "PENDING",
        "founder_40_second_review": "PENDING",
        "expand_80": False,
        "expand_600": False,
        "expand_3600": False,
        "next_action_if_all_human_thresholds_pass": "GKB-P7D-REPAIR-RULE-VALIDATION-BATCH-80-001_BRIEF_ONLY",
        "preserved_status_literals": {
            "P7C-AB": "NEXT",
            "P7C_SCALE": "BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY",
            "P7C_SCALE_PREP": "DONE",
            "P7D": "BLOCKED_BY_P7C_SCALE_DECISION",
            "P8": "BLOCKED_BY_P7D",
        },
    }
    require(errors, migration == expected, "route_migration_11 content drift")
    errors.extend(
        f"ledger readiness true: {path}" for path in false_readiness_paths(current)
    )
    baseline_md = git_text(root, "show", f"{BASELINE_HEAD}:{LEDGER_MD_REL}")
    current_md = (root / LEDGER_MD_REL).read_text(encoding="utf-8")
    require(
        errors,
        current_md.startswith(baseline_md),
        "ledger markdown changed before additive appendix",
    )
    require(
        errors,
        "## P7D Everyday-Native Platform Variant 5x2" in current_md[len(baseline_md) :],
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
    require(errors, ancestor.returncode == 0, "baseline is not an ancestor of HEAD")
    for artifact in REQUIRED_ARTIFACTS:
        require(
            errors,
            (root / OUT_REL / artifact).is_file(),
            f"required artifact missing: {artifact}",
        )
    require(
        errors,
        (root / "docs/reports/p7d_platform_native_5x2_report.md").is_file(),
        "human-readable delivery report missing",
    )
    require(errors, (root / FIXTURE_REL).is_file(), "fixture manifest missing")
    try:
        bundle = load_bundle(root)
        bundle_errors, metrics = validate_bundle(bundle)
        errors.extend(bundle_errors)
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        errors.append(f"structured parse/validation failed: {exc}")
        metrics = {}
    validate_parent_assets_unchanged(root, errors)
    try:
        validate_ledger(root, errors)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append(f"ledger validation failed: {exc}")
    paths = changed_paths(root)
    for path in paths:
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
    def remove_parent(bundle: dict[str, Any]) -> None:
        bundle["selection"]["parent_kernel_selection_manifest"]["entries"].pop()

    def remove_variant(bundle: dict[str, Any]) -> None:
        bundle["variants"].pop()

    def matrix_drift(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["platform_target"] = "douyin"

    def parent_drift(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["parent_kernel_id"] = "invented-parent"

    def event_drift(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["event_spine_digest"] = "0" * 64

    def fact_drift(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["fact_boundary_digest"] = "0" * 64

    def role_drift(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["account_role"] = "sales_associate"

    def core_drift(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["core_business_judgment"] = "drift"

    def knowledge_inflation(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["knowledge_count_increment"] = 1

    def missing_event(bundle: dict[str, Any]) -> None:
        del bundle["selection"]["parent_kernel_selection_manifest"]["entries"][0][
            "event_spine"
        ]["event_trigger"]

    def metadata_leak(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["body_text"] += " CandidatePack readiness"

    def slot_leak(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["body_text"] += "【品牌事实】"

    def director_leak(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["body_text"] += "做成短剧"

    def fake_customer(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["body_text"] += "王女士说很好。"

    def role_action_failure(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["body_text"] += "顾客调整陈列。"

    def hard_claim(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["body_text"] += "保证显瘦。"

    def exact_duplicate(bundle: dict[str, Any]) -> None:
        bundle["variants"][1]["body_text"] = bundle["variants"][0]["body_text"]

    def normalized_duplicate(bundle: dict[str, Any]) -> None:
        bundle["variants"][1]["body_text"] = (
            bundle["variants"][0]["body_text"] + "！！！"
        )

    def same_skeleton(bundle: dict[str, Any]) -> None:
        bundle["variants"][1]["skeleton_payload"] = copy.deepcopy(
            bundle["variants"][0]["skeleton_payload"]
        )
        bundle["variants"][1]["skeleton_fingerprint"] = bundle["variants"][0][
            "skeleton_fingerprint"
        ]

    def pair_copy(bundle: dict[str, Any]) -> None:
        bundle["variants"][1]["body_text"] = bundle["variants"][0]["body_text"]

    def kernel_copy(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["body_text"] = bundle["parents"][0]["content_kernel"][
            "business_judgment"
        ]

    def capture_drift(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["execution_card"]["capture_mode"] = "campaign_directed"

    def time_drift(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["execution_card"]["production_time_minutes_max"] = 21

    def readiness_true(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["readiness_flags"]["generation_allowed"] = True

    def payload_missing(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["platform_payload"].pop(
            next(iter(bundle["variants"][0]["platform_payload"]))
        )

    def opening_monoculture(bundle: dict[str, Any]) -> None:
        for row in bundle["variants"][:3]:
            row["opening_family"] = "same-opening"

    def gate_lie(bundle: dict[str, Any]) -> None:
        bundle["gate"]["platform_native_everyday_gate_result"]["machine_metrics"][
            "kernel_overlap_max"
        ] = 0

    def guardian_prefilled(bundle: dict[str, Any]) -> None:
        bundle["guardian"]["platform_native_guardian_review_packet"]["entries"][0][
            "guardian_verdict"
        ] = "PASS"

    def founder_prefilled(bundle: dict[str, Any]) -> None:
        bundle["founder"]["platform_native_founder_review_packet"]["pairs"][0][
            "founder_pair_verdict"
        ] = "PASS"

    def allow_scale(bundle: dict[str, Any]) -> None:
        bundle["result"]["platform_native_5x2_result"]["scale"]["expand_80"] = True

    def bad_result(bundle: dict[str, Any]) -> None:
        bundle["result"]["platform_native_5x2_result"]["result_status"] = (
            "PLATFORM_NATIVE_CONFIRMED"
        )

    def external_llm(bundle: dict[str, Any]) -> None:
        bundle["variants"][0]["external_LLM_called"] = True

    def selection_drift(bundle: dict[str, Any]) -> None:
        bundle["selection"]["parent_kernel_selection_manifest"]["entries"][0][
            "selected_parent_id"
        ] = "wrong"

    def source_digest_drift(bundle: dict[str, Any]) -> None:
        bundle["selection"]["parent_kernel_selection_manifest"][
            "source_asset_sha256"
        ] = "0" * 64

    def direction_drift(bundle: dict[str, Any]) -> None:
        bundle["direction"]["founder_everyday_native_direction"][
            "enterprise_narrative_and_vlog_default"
        ] = "campaign_directed"

    return [
        ("missing_parent", remove_parent),
        ("missing_variant", remove_variant),
        ("matrix_drift", matrix_drift),
        ("parent_mapping_drift", parent_drift),
        ("event_digest_drift", event_drift),
        ("fact_digest_drift", fact_drift),
        ("role_drift", role_drift),
        ("core_judgment_drift", core_drift),
        ("knowledge_count_inflation", knowledge_inflation),
        ("missing_event_field", missing_event),
        ("metadata_body_leak", metadata_leak),
        ("fact_slot_body_leak", slot_leak),
        ("director_marker", director_leak),
        ("fake_customer", fake_customer),
        ("role_action_failure", role_action_failure),
        ("unsupported_claim", hard_claim),
        ("exact_duplicate", exact_duplicate),
        ("normalized_duplicate", normalized_duplicate),
        ("same_skeleton", same_skeleton),
        ("pair_copy", pair_copy),
        ("kernel_copy", kernel_copy),
        ("capture_mode_drift", capture_drift),
        ("time_limit_drift", time_drift),
        ("readiness_true", readiness_true),
        ("payload_field_missing", payload_missing),
        ("opening_monoculture", opening_monoculture),
        ("gate_metric_lie", gate_lie),
        ("guardian_verdict_prefilled", guardian_prefilled),
        ("founder_verdict_prefilled", founder_prefilled),
        ("scale_unlocked", allow_scale),
        ("result_overclaim", bad_result),
        ("external_llm_true", external_llm),
        ("selection_manifest_drift", selection_drift),
        ("selection_source_digest_drift", source_digest_drift),
        ("founder_direction_drift", direction_drift),
    ]


def run_selftest(root: Path) -> tuple[bool, dict[str, Any]]:
    try:
        bundle = load_bundle(root)
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        return False, {
            "status": "FAIL",
            "reason": f"cannot load positive bundle: {exc}",
        }
    positive_errors, _ = validate_bundle(copy.deepcopy(bundle))
    failures: list[str] = []
    if positive_errors:
        failures.append(f"positive fixture failed: {positive_errors}")
    observed: list[str] = []
    for name, mutate in selftest_cases():
        candidate = copy.deepcopy(bundle)
        mutate(candidate)
        errors, _ = validate_bundle(candidate)
        if not errors:
            failures.append(f"negative fixture escaped: {name}")
        else:
            observed.append(name)
    try:
        json.loads("{malformed")
        failures.append("malformed JSON escaped")
    except json.JSONDecodeError:
        observed.append("malformed_json")
    fixture = read_yaml(root / FIXTURE_REL)["p7d_platform_native_5x2_selftest"]
    expected_cases = set(fixture.get("negative_cases", []))
    require(
        failures,
        expected_cases == set(observed),
        "fixture manifest/selftest case drift",
    )
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
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "machine_metrics": metrics,
        "result_scope": "machine_integrity_only_human_platform_and_execution_review_pending",
    }
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not __debug__:
        sys.stdout.write(
            json.dumps({"status": "FAIL_CLOSED", "reason": "python_optimized_mode"})
            + "\n"
        )
        return 2
    if yaml is None:
        sys.stdout.write(
            json.dumps({"status": "FAIL_CLOSED", "reason": "yaml_unavailable"}) + "\n"
        )
        return 2
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.selftest:
        passed, payload = run_selftest(root)
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return 0 if passed else 1
    errors, metrics = validate_repository(root)
    write_report(root, errors, metrics)
    payload = {
        "task_id": TASK_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "machine_metrics": metrics,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
