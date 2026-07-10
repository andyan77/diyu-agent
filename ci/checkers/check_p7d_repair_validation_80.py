#!/usr/bin/env python3
"""Fail-closed checker for the frozen remaining-80 P7D validation run."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


TASK_ID = "GKB-P7D-REPAIR-RULE-VALIDATION-BATCH-80-001"
BASELINE_HEAD = "3f1beedd65f42b9c3fffe79dadfd878534216361"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
MID_REL = f"{RUN_REL}/midbatch_320_001"
OUT_REL = f"{MID_REL}/repair_validation_80_001"
KERNEL_REL = f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml"
CARDS_REL = f"{RUN_REL}/knowledge_candidate_cards.yaml"
FOUNDER_40_REL = (
    f"{MID_REL}/founder_40_repair_001/founder_40_repaired_assets.v0.1.jsonl"
)
VALIDATION_REL = f"{OUT_REL}/repair_validation_80_validation_spec.v0.1.yaml"
SPECS_REL = f"{OUT_REL}/repair_validation_80_authored_specs.v0.1.yaml"
BINDING_REL = f"{OUT_REL}/repair_validation_80_event_fact_binding_index.v0.1.jsonl"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
LEDGER_MD_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"
REPORT_REL = "ci/reports/p7d_repair_validation_80_report.v0.1.json"
FIXTURE_REL = "ci/fixtures/p7d_repair_validation_80/fixture_manifest.v0.1.yaml"

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
PLATFORM_PAYLOAD = {
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
KERNEL_FIELDS = {
    "human_subject",
    "object_anchor",
    "human_action",
    "scene_premise",
    "event_trigger",
    "visible_detail",
    "business_judgment",
    "tradeoff_or_tension",
    "spoken_line_seed",
    "natural_next_action",
}
REVIEW_FIELDS = {
    "required_fact_slots",
    "forbidden_claims",
    "event_binding_state",
    "role_action_review",
    "platform_native_review",
    "everyday_voice_review",
    "low_cost_execution_review",
    "skeleton_review",
    "source_refs",
    "readiness_flags",
    "human_review_required",
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
FAKE_PERSON_PATTERN = re.compile(
    r"(?:王|李|张|陈|刘|赵)(?:姐|女士|先生|小姐)|顾客说|客人说|有位顾客"
)
HARD_CLAIM_PATTERN = re.compile(
    r"(?<!不)保证.{0,5}(显白|显高|显瘦|耐穿|舒适)|"
    r"一定.{0,5}(显白|显高|显瘦|耐穿|舒适)|"
    r"卖爆|销量(?:增长|提升)|转化率(?:增长|提升)"
)
ROLE_FAILURE_PATTERN = re.compile(
    r"顾客.{0,6}(调整陈列|修改版型|工艺复核)|"
    r"导购.{0,6}(修改版型|改工艺|代替版师)|"
    r"版师.{0,6}(催顾客购买|代替导购成交)"
)
ALLOWED_PREFIXES = (
    f"{OUT_REL}/",
    "ci/runners/run_p7d_repair_validation_80.py",
    "ci/checkers/check_p7d_repair_validation_80.py",
    "ci/fixtures/p7d_repair_validation_80/",
    REPORT_REL,
    LEDGER_REL,
    LEDGER_MD_REL,
    "docs/reports/p7d_repair_validation_80_report.md",
    "docs/reports/p7d_repair_validation_80_receipt.json",
)


def stable_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@lru_cache(maxsize=32768)
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


@lru_cache(maxsize=8192)
def body_shingles(text: str, size: int = 5) -> frozenset[str]:
    value = normalize(text)
    if len(value) < size:
        return frozenset({value}) if value else frozenset()
    return frozenset(
        value[index : index + size] for index in range(len(value) - size + 1)
    )


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


@lru_cache(maxsize=131072)
def longest_common_substring(left: str, right: str, cap: int = 40) -> tuple[int, str]:
    a, b = normalize(left), normalize(right)
    maximum = min(cap, len(a), len(b))
    for width in range(maximum, 0, -1):
        earliest_start: int | None = None
        for index in range(len(b) - width + 1):
            start = a.find(b[index : index + width])
            if start >= 0 and (earliest_start is None or start < earliest_start):
                earliest_start = start
        if earliest_start is not None:
            return width, a[earliest_start : earliest_start + width]
    return 0, ""


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
            values.extend(str(item) for item in row[key])
    return values


def max_kernel_overlap(
    body: str, kernels: list[dict[str, Any]]
) -> tuple[int, str, str]:
    best = (0, "", "")
    for row in kernels:
        for segment in kernel_segments(row):
            length, fragment = longest_common_substring(body, segment)
            if length > best[0]:
                best = (length, str(row["candidate_id"]), fragment)
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


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def source_data(
    bundle: dict[str, Any],
) -> tuple[list[dict[str, Any]], set[str], dict[str, dict[str, Any]]]:
    kernels = bundle["kernels"]
    founder_ids = {
        str(row["bound_kernel_candidate_id"]) for row in bundle["founder_40"]
    }
    cards = {str(row["candidate_id"]): row for row in bundle["cards"]}
    return kernels, founder_ids, cards


def deterministic_selection(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    kernels, founder_ids, cards = source_data(bundle)
    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in kernels:
        by_cluster[str(row["canonical_cluster_id"])].append(row)
    if len(kernels) != 120 or len(by_cluster) != 40 or len(founder_ids) != 40:
        raise ValueError("40x3 source structure does not hold")
    selected: list[dict[str, Any]] = []
    ordinal = 0
    for cluster_id in sorted(by_cluster):
        rows = sorted(by_cluster[cluster_id], key=lambda row: str(row["candidate_id"]))
        existing = [row for row in rows if str(row["candidate_id"]) in founder_ids]
        remaining = [row for row in rows if str(row["candidate_id"]) not in founder_ids]
        if len(rows) != 3 or len(existing) != 1 or len(remaining) != 2:
            raise ValueError(f"invalid per-cluster difference: {cluster_id}")
        p0_group = str(rows[0]["p0_group"])
        for position, (kernel, platform) in enumerate(
            zip(remaining, PLATFORM_MATRIX[p0_group], strict=True), start=1
        ):
            ordinal += 1
            kernel_id = str(kernel["candidate_id"])
            source_output_candidates = [str(cards[kernel_id]["target_output_id"])]
            selected.append(
                {
                    "selection_ordinal": ordinal,
                    "checkpoint_id": f"RV80-CP-{((ordinal - 1) // 20) + 1:02d}",
                    "cluster_id": cluster_id,
                    "capability_group": p0_group,
                    "cluster_position": position,
                    "kernel_id": kernel_id,
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
                        f"{RUN_REL}/content_kernel_extraction/"
                        f"user_visible_kernel_matrix.v0.1.yaml#{kernel_id}"
                    ),
                    "platform_contract_ref": (
                        f"{MID_REL}/founder_40_repair_001/platform_native_5x2_001/"
                        "platform_native_everyday_expression_contract.v0.1.yaml"
                    ),
                    "existing_founder_40_kernel_id": existing[0]["candidate_id"],
                }
            )
    return selected


def load_bundle(root: Path) -> dict[str, Any]:
    out = root / OUT_REL
    kernel_doc = read_yaml(root / KERNEL_REL)["user_visible_kernel_matrix"]
    cards_doc = read_yaml(root / CARDS_REL)["scoped_120_candidate_cards"]
    return {
        "kernels": kernel_doc["entries"],
        "founder_40": read_jsonl(root / FOUNDER_40_REL),
        "cards": cards_doc["candidates"],
        "validation": read_yaml(root / VALIDATION_REL)[
            "repair_validation_80_validation_spec"
        ],
        "freeze": read_yaml(
            out / "repair_validation_80_contract_freeze_manifest.v0.1.yaml"
        )["repair_validation_80_contract_freeze_manifest"],
        "selection": read_jsonl(
            out / "remaining_80_kernel_selection_manifest.v0.1.jsonl"
        ),
        "selection_summary": read_yaml(
            out / "remaining_80_kernel_selection_summary.v0.1.yaml"
        )["remaining_80_kernel_selection_summary"],
        "accepted": read_yaml(out / "accepted_review_evidence.v0.1.yaml")[
            "accepted_review_evidence"
        ],
        "specs": read_yaml(root / SPECS_REL)["repair_validation_80_authored_specs"],
        "assets": read_jsonl(out / "repair_validation_80_assets.v0.1.jsonl"),
        "bindings": read_jsonl(root / BINDING_REL),
        "first_pass": read_jsonl(
            out / "repair_validation_80_first_pass_ledger.v0.1.jsonl"
        ),
        "checkpoints": read_jsonl(
            out / "repair_validation_80_checkpoint_ledger.v0.1.jsonl"
        ),
        "failures": read_jsonl(out / "repair_validation_80_failure_ledger.v0.1.jsonl"),
        "coverage": read_yaml(out / "repair_validation_80_kernel_coverage.v0.1.yaml")[
            "repair_validation_80_kernel_coverage"
        ],
        "distribution": read_yaml(
            out / "repair_validation_80_platform_distribution.v0.1.yaml"
        )["repair_validation_80_platform_distribution"],
        "fingerprints": read_jsonl(
            out / "repair_validation_80_fingerprint_index.v0.1.jsonl"
        ),
        "gate": read_yaml(out / "repair_validation_80_machine_gate_result.v0.1.yaml")[
            "repair_validation_80_machine_gate_result"
        ],
        "capability": read_yaml(
            out / "repair_validation_80_capability_platform_summary.v0.1.yaml"
        )["repair_validation_80_capability_platform_summary"],
        "guardian": read_yaml(
            out / "repair_validation_80_guardian_review_packet.v0.1.yaml"
        )["repair_validation_80_guardian_review_packet"],
        "result": read_yaml(out / "repair_validation_80_result.v0.1.yaml")[
            "repair_validation_80_result"
        ],
        "receipt": read_json(
            root / "docs/reports/p7d_repair_validation_80_receipt.json"
        ),
    }


def validate_freeze(bundle: dict[str, Any], root: Path, errors: list[str]) -> None:
    freeze = bundle["freeze"]
    require(errors, freeze.get("task_id") == TASK_ID, "freeze task id drift")
    require(
        errors, freeze.get("baseline_head") == BASELINE_HEAD, "freeze baseline drift"
    )
    require(
        errors,
        freeze.get("frozen_before_first_generation") is True,
        "contract not frozen before generation",
    )
    require(
        errors,
        freeze.get("generation_started_at_freeze") is False,
        "generation started before freeze",
    )
    require(
        errors,
        freeze.get("contracts_must_not_change_after_freeze") is True,
        "freeze mutability flag drift",
    )
    for category in ("source_digests", "contract_digests", "checker_reference_digests"):
        for relative, expected in freeze.get(category, {}).items():
            path = root / relative
            require(errors, path.is_file(), f"frozen reference missing: {relative}")
            if path.is_file():
                require(
                    errors,
                    hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                    f"frozen digest drift: {relative}",
                )
    frozen_payload = {
        "baseline_head": freeze["baseline_head"],
        "source_digests": freeze["source_digests"],
        "contract_digests": freeze["contract_digests"],
        "checker_reference_digests": freeze["checker_reference_digests"],
        "selection_algorithm": freeze["selection_algorithm"],
        "platform_matrix": freeze["platform_matrix"],
        "validation_spec_digest": freeze["validation_spec_digest"],
    }
    require(
        errors,
        freeze.get("freeze_digest") == stable_digest(frozen_payload),
        "freeze digest drift",
    )
    require(
        errors,
        freeze.get("validation_spec_digest")
        == hashlib.sha256((root / VALIDATION_REL).read_bytes()).hexdigest(),
        "validation spec digest drift",
    )


def validate_bundle(bundle: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    validation = bundle["validation"]
    kernels, founder_ids, _ = source_data(bundle)
    kernels_by_id = {str(row["candidate_id"]): row for row in kernels}
    try:
        expected_selection = deterministic_selection(bundle)
    except (KeyError, TypeError, ValueError) as exc:
        return [f"selection recompute failed: {exc}"], {}
    selection = bundle["selection"]
    require(
        errors,
        selection == expected_selection,
        "selection manifest differs from independent recompute",
    )
    selected_ids = {str(row["kernel_id"]) for row in selection}
    require(
        errors,
        len(selection) == 80 and len(selected_ids) == 80,
        "selection is not 80 unique kernels",
    )
    require(
        errors, not (selected_ids & founder_ids), "remaining-80 intersects founder-40"
    )
    require(
        errors,
        len(selected_ids | founder_ids) == 120,
        "combined kernel coverage is not 120",
    )
    by_cluster = Counter(str(row["cluster_id"]) for row in selection)
    require(
        errors,
        len(by_cluster) == 40 and set(by_cluster.values()) == {2},
        "selection is not two per cluster",
    )
    summary = bundle["selection_summary"]
    require(
        errors,
        summary.get("selection_digest") == stable_digest(selection),
        "selection summary digest drift",
    )
    require(
        errors,
        summary.get("selected_kernel_count") == 80,
        "selection summary count drift",
    )
    require(
        errors, summary.get("coverage_gap_count") == 0, "selection summary coverage gap"
    )
    require(
        errors,
        summary.get("generation_started") is False,
        "freeze-phase selection summary mutated",
    )
    require(
        errors,
        bundle["accepted"].get("founder_40_full_grading")
        == "deferred_by_founder_scale_authority",
        "founder-40 grading gap hidden",
    )
    require(
        errors,
        bundle["accepted"].get("expand_600") is False,
        "accepted evidence unlocks 600",
    )
    require(
        errors,
        bundle["accepted"].get("expand_3600") is False,
        "accepted evidence unlocks 3600",
    )

    specs = bundle["specs"].get("entries", [])
    require(errors, len(specs) == 80, "authored spec count drift")
    specs_by_id = {str(row.get("kernel_id")): row for row in specs}
    require(
        errors,
        len(specs_by_id) == 80 and set(specs_by_id) == selected_ids,
        "authored specs do not match selection",
    )
    assets = bundle["assets"]
    require(errors, len(assets) == 80, "accepted asset count must be 80")
    require(
        errors,
        len({row.get("asset_id") for row in assets}) == 80,
        "asset ids are not unique",
    )
    require(
        errors,
        {str(row.get("kernel_id")) for row in assets} == selected_ids,
        "asset kernel coverage drift",
    )
    selection_by_id = {str(row["kernel_id"]): row for row in selection}
    expected_bindings: list[dict[str, Any]] = []
    for row in assets:
        content_kernel = row.get("content_kernel", {})
        metadata = row.get("review_metadata", {})
        event_spine = {
            "event_trigger": content_kernel.get("event_trigger"),
            "human_subject": content_kernel.get("human_subject"),
            "human_action": content_kernel.get("human_action"),
            "object_anchor": content_kernel.get("object_anchor"),
            "visible_detail": content_kernel.get("visible_detail"),
            "business_judgment": content_kernel.get("business_judgment"),
            "tradeoff_or_tension": content_kernel.get("tradeoff_or_tension"),
            "natural_next_action": content_kernel.get("natural_next_action"),
        }
        fact_boundary = {
            "generation_mode": row.get("generation_mode"),
            "required_fact_slots": metadata.get("required_fact_slots"),
            "forbidden_claims": metadata.get("forbidden_claims"),
            "event_binding_state": metadata.get("event_binding_state"),
            "accepted_domain_knowledge": row.get("accepted_domain_knowledge"),
            "creates_new_knowledge": row.get("creates_new_knowledge"),
            "production_servable": row.get("production_servable"),
        }
        expected_bindings.append(
            {
                "asset_id": row.get("asset_id"),
                "kernel_id": row.get("kernel_id"),
                "source_output_id": row.get("source_output_id"),
                "cluster_id": row.get("canonical_cluster_id"),
                "capability_group": row.get("capability_group"),
                "platform_target": row.get("platform_target"),
                "account_role": row.get("account_role"),
                "capture_mode": row.get("capture_mode"),
                "event_spine": event_spine,
                "event_spine_digest": stable_digest(event_spine),
                "fact_boundary": fact_boundary,
                "fact_boundary_digest": stable_digest(fact_boundary),
                "platform_contract_ref": selection_by_id.get(
                    str(row.get("kernel_id")), {}
                ).get("platform_contract_ref"),
            }
        )
    require(
        errors,
        bundle["bindings"] == expected_bindings,
        "event/fact binding index differs from independent recompute",
    )
    bodies: list[str] = []
    normalized_bodies: list[str] = []
    fingerprint_counts: Counter[str] = Counter()
    kernel_overlaps: list[int] = []
    max_cross_jaccard = 0.0
    nearest_pair: tuple[str, str] = ("", "")
    platform_counts: Counter[str] = Counter()
    p0_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    markers = validation["body_blocking_markers"]
    daily = validation["daily_native_constraints"]
    thresholds = validation["machine_thresholds"]
    for row in assets:
        asset_id = str(row.get("asset_id"))
        kernel_id = str(row.get("kernel_id"))
        source = kernels_by_id.get(kernel_id, {})
        selected = selection_by_id.get(kernel_id, {})
        spec = specs_by_id.get(kernel_id, {})
        body = str(row.get("body_text", ""))
        require(
            errors,
            row.get("selection_ordinal") == selected.get("selection_ordinal"),
            f"ordinal drift: {asset_id}",
        )
        require(
            errors,
            row.get("checkpoint_id") == selected.get("checkpoint_id"),
            f"checkpoint drift: {asset_id}",
        )
        for key in (
            "source_output_id",
            "source_assignment_id",
            "platform_target",
            "account_role",
            "capture_mode",
        ):
            require(
                errors,
                row.get(key) == selected.get(key),
                f"selection binding drift: {asset_id}.{key}",
            )
        require(
            errors,
            row.get("canonical_cluster_id") == selected.get("cluster_id"),
            f"cluster drift: {asset_id}",
        )
        require(
            errors,
            row.get("capability_group") == selected.get("capability_group"),
            f"P0 drift: {asset_id}",
        )
        require(
            errors,
            row.get("generation_mode") == selected.get("generation_mode"),
            f"generation mode drift: {asset_id}",
        )
        platform = str(row.get("platform_target"))
        expected_payload = PLATFORM_PAYLOAD.get(platform)
        require(errors, expected_payload is not None, f"unknown platform: {asset_id}")
        if expected_payload is not None:
            require(
                errors,
                row.get("payload_shape") == expected_payload[0],
                f"payload shape drift: {asset_id}",
            )
            payload = row.get("platform_payload", {})
            require(
                errors,
                isinstance(payload, dict) and set(payload) == expected_payload[1],
                f"payload fields drift: {asset_id}",
            )
            require(
                errors,
                all(
                    isinstance(value, str) and value.strip()
                    for value in payload.values()
                ),
                f"empty payload: {asset_id}",
            )
        require(
            errors, body == spec.get("body_text"), f"asset/spec body drift: {asset_id}"
        )
        require(
            errors,
            len(normalize(body)) >= int(thresholds["minimum_normalized_body_chars"]),
            f"body too thin: {asset_id}",
        )
        require(
            errors,
            not any(marker in body for group in markers.values() for marker in group),
            f"body blocking marker: {asset_id}",
        )
        require(
            errors,
            FAKE_PERSON_PATTERN.search(body) is None,
            f"fake/named customer: {asset_id}",
        )
        require(
            errors,
            HARD_CLAIM_PATTERN.search(body) is None,
            f"unsupported hard claim: {asset_id}",
        )
        require(
            errors,
            ROLE_FAILURE_PATTERN.search(body) is None,
            f"role/action hard failure: {asset_id}",
        )
        require(
            errors,
            row.get("body_digest") == hashlib.sha256(body.encode("utf-8")).hexdigest(),
            f"body digest drift: {asset_id}",
        )
        require(
            errors,
            row.get("normalized_body_digest")
            == hashlib.sha256(normalize(body).encode("utf-8")).hexdigest(),
            f"normalized digest drift: {asset_id}",
        )
        overlap, overlap_kernel, fragment = max_kernel_overlap(body, kernels)
        kernel_overlaps.append(overlap)
        require(
            errors,
            overlap <= int(thresholds["source_kernel_longest_overlap_max_chars"]),
            f"source kernel copy: {asset_id}={overlap}",
        )
        require(
            errors,
            row.get("source_kernel_overlap")
            == {
                "max_chars": overlap,
                "kernel_id": overlap_kernel,
                "fragment": fragment,
            },
            f"source overlap report drift: {asset_id}",
        )
        content_kernel = row.get("content_kernel", {})
        require(
            errors,
            KERNEL_FIELDS <= set(content_kernel),
            f"content kernel fields missing: {asset_id}",
        )
        for key in (
            "human_subject",
            "object_anchor",
            "business_judgment",
            "tradeoff_or_tension",
        ):
            require(
                errors,
                content_kernel.get(key) == source.get(key),
                f"source kernel field drift: {asset_id}.{key}",
            )
        require(
            errors,
            content_kernel.get("event_trigger") == spec.get("event_trigger"),
            f"event trigger drift: {asset_id}",
        )
        require(
            errors,
            content_kernel.get("visible_detail") == spec.get("visible_detail"),
            f"visible detail drift: {asset_id}",
        )
        require(
            errors,
            content_kernel.get("natural_next_action")
            == spec.get("natural_next_action"),
            f"next action drift: {asset_id}",
        )
        if row.get("capability_group") == "P0_01":
            require(
                errors,
                {
                    "organization_choice",
                    "long_term_tradeoff",
                    "visible_product_trace",
                    "founder_or_team_decision",
                    "not_claimed_result",
                    "safe_spoken_line",
                }
                <= set(content_kernel),
                f"P0-01 fields missing: {asset_id}",
            )
        if row.get("capability_group") == "P0_04":
            require(
                errors,
                content_kernel.get("scoped_subroute") == "store_daily_display_action",
                f"P0-04 subroute drift: {asset_id}",
            )
        if row.get("capability_group") == "P0_05":
            require(
                errors,
                {
                    "customer_task",
                    "product_role",
                    "scene_use_case",
                    "trial_or_tryon_trigger",
                    "safe_observation",
                    "guide_next_line",
                }
                <= set(content_kernel),
                f"P0-05 fields missing: {asset_id}",
            )
        metadata = row.get("review_metadata", {})
        require(
            errors,
            REVIEW_FIELDS <= set(metadata),
            f"review metadata fields missing: {asset_id}",
        )
        require(
            errors,
            metadata.get("event_binding_state") == "bounded_routine_work_prototype",
            f"event binding state drift: {asset_id}",
        )
        require(
            errors,
            metadata.get("human_review_required") is True,
            f"human review bypassed: {asset_id}",
        )
        for key, expected in (
            ("role_action_review", "PENDING_CLAUDE_CODE"),
            ("platform_native_review", "PENDING_CLAUDE_CODE"),
            ("everyday_voice_review", "PENDING_CLAUDE_CODE"),
            ("low_cost_execution_review", "PENDING_CLAUDE_CODE"),
            ("skeleton_review", "PENDING_CLAUDE_CODE"),
        ):
            require(
                errors,
                metadata.get(key, {}).get("expert_status") == expected,
                f"expert review prefilled: {asset_id}.{key}",
            )
        errors.extend(
            f"readiness true: {path}"
            for path in false_readiness_paths(
                metadata.get("readiness_flags", {}), asset_id
            )
        )
        execution = row.get("execution_card", {})
        for key, expected in daily.items():
            actual = execution.get(key)
            if key in {"simple_segment_count_max", "production_time_minutes_max"}:
                require(
                    errors,
                    isinstance(actual, int) and actual <= int(expected),
                    f"daily-native limit drift: {asset_id}.{key}",
                )
            else:
                require(
                    errors,
                    actual == expected,
                    f"daily-native constraint drift: {asset_id}.{key}",
                )
        for key in (
            "who_executes",
            "who_appears",
            "phone_placement",
            "real_work_action",
            "natural_spoken_line",
            "do_not_perform",
            "do_not_say",
            "interaction_handoff",
        ):
            require(
                errors,
                bool(execution.get(key)),
                f"execution field missing: {asset_id}.{key}",
            )
        skeleton = row.get("narrative_skeleton", {})
        payload = skeleton.get("payload", {})
        expected_skeleton = {
            "p0_group": row.get("capability_group"),
            "generation_mode": row.get("generation_mode"),
            "platform_target": row.get("platform_target"),
            "event_type": spec.get("event_type"),
            "opening_family": spec.get("opening_family"),
            "closing_family": spec.get("closing_family"),
            "subject_role": source.get("human_subject"),
            "action_family": spec.get("human_action"),
            "judgment_family": spec.get("judgment_family"),
        }
        require(
            errors, payload == expected_skeleton, f"skeleton payload drift: {asset_id}"
        )
        require(
            errors,
            skeleton.get("fingerprint") == stable_digest(payload),
            f"skeleton digest drift: {asset_id}",
        )
        fingerprint_counts[str(skeleton.get("fingerprint"))] += 1
        require(
            errors,
            row.get("source_kernel_digest") == stable_digest(source),
            f"source kernel digest drift: {asset_id}",
        )
        require(
            errors,
            row.get("generation_status") == "codex_native_repaired_expression_asset",
            f"generation status drift: {asset_id}",
        )
        require(
            errors,
            row.get("external_LLM_called") is False,
            f"external LLM flag true: {asset_id}",
        )
        require(
            errors,
            row.get("creates_new_knowledge") is False,
            f"asset marked new knowledge: {asset_id}",
        )
        require(
            errors,
            row.get("knowledge_count_increment") == 0,
            f"knowledge inflation: {asset_id}",
        )
        require(
            errors,
            row.get("accepted_domain_knowledge") is False,
            f"accepted knowledge true: {asset_id}",
        )
        require(
            errors,
            row.get("candidatepack_ready") is False,
            f"candidatepack ready true: {asset_id}",
        )
        require(
            errors,
            row.get("production_servable") is False,
            f"production servable true: {asset_id}",
        )
        require(
            errors,
            row.get("counts_toward_600_or_3600") is False,
            f"asset counted toward scale: {asset_id}",
        )
        axes = row.get("evaluation_axes", {})
        require(
            errors,
            axes.get("knowledge_and_fact_boundary", {}).get("machine_status") == "PASS",
            f"fact boundary status drift: {asset_id}",
        )
        require(
            errors,
            axes.get("content_fuel_support", {}).get("expert_status")
            == "PENDING_CLAUDE_CODE",
            f"content quality self-approved: {asset_id}",
        )
        require(
            errors,
            axes.get("platform_native_fit", {}).get("expert_status")
            == "PENDING_CLAUDE_CODE",
            f"platform quality self-approved: {asset_id}",
        )
        require(
            errors,
            axes.get("daily_execution_fit", {}).get("expert_status")
            == "PENDING_CLAUDE_CODE",
            f"daily execution self-approved: {asset_id}",
        )
        require(
            errors,
            axes.get("publication_readiness", {}).get("status") is False,
            f"publication readiness true: {asset_id}",
        )
        for prior_id, prior_body in zip(
            (str(item.get("asset_id")) for item in assets[: len(bodies)]),
            bodies,
            strict=False,
        ):
            score = jaccard(body_shingles(body), body_shingles(prior_body))
            if score > max_cross_jaccard:
                max_cross_jaccard = score
                nearest_pair = (prior_id, asset_id)
        bodies.append(body)
        normalized_bodies.append(normalize(body))
        platform_counts[platform] += 1
        p0_counts[str(row.get("capability_group"))] += 1
        mode_counts[str(row.get("generation_mode"))] += 1

    require(errors, len(set(bodies)) == 80, "exact duplicate body detected")
    require(
        errors, len(set(normalized_bodies)) == 80, "normalized duplicate body detected"
    )
    skeleton_max = max(fingerprint_counts.values(), default=0)
    require(
        errors,
        skeleton_max <= int(thresholds["skeleton_fingerprint_reuse_max"]),
        "skeleton reuse exceeds frozen threshold",
    )
    require(
        errors,
        max_cross_jaccard <= float(thresholds["cross_item_five_shingle_jaccard_max"]),
        f"cross-item Jaccard exceeds threshold: {nearest_pair}={max_cross_jaccard}",
    )
    expected_platform = Counter(row["platform_target"] for row in selection)
    expected_p0 = Counter(row["capability_group"] for row in selection)
    require(errors, platform_counts == expected_platform, "platform distribution drift")
    require(errors, p0_counts == expected_p0, "P0 distribution drift")

    first_pass = bundle["first_pass"]
    require(errors, len(first_pass) == 80, "first-pass ledger count drift")
    first_by_id = {str(row.get("asset_id")): row for row in first_pass}
    require(errors, len(first_by_id) == 80, "first-pass asset ids not unique")
    assets_by_id = {str(row["asset_id"]): row for row in assets}
    for asset_id, asset in assets_by_id.items():
        first = first_by_id.get(asset_id, {})
        require(
            errors,
            first.get("kernel_id") == asset.get("kernel_id"),
            f"first-pass kernel drift: {asset_id}",
        )
        require(
            errors,
            first.get("first_pass_body_text") == asset.get("body_text"),
            f"first-pass body not preserved: {asset_id}",
        )
        require(
            errors,
            first.get("first_pass_body_digest") == asset.get("body_digest"),
            f"first-pass digest drift: {asset_id}",
        )
        require(
            errors,
            first.get("machine_status") == "PASS",
            f"first-pass not PASS: {asset_id}",
        )
        require(
            errors,
            first.get("failure_codes") == [],
            f"first-pass failure hidden: {asset_id}",
        )
        require(
            errors,
            first.get("bounded_correction_used") is False,
            f"unrecorded correction: {asset_id}",
        )
        require(
            errors,
            first.get("accepted_body_digest") == asset.get("body_digest"),
            f"accepted digest drift: {asset_id}",
        )
    require(
        errors,
        bundle["failures"] == [],
        "failure ledger must be empty for COMPLETE/PASS result",
    )
    checkpoints = bundle["checkpoints"]
    require(errors, len(checkpoints) == 4, "checkpoint count must be 4")
    for index, checkpoint in enumerate(checkpoints, start=1):
        require(
            errors,
            checkpoint.get("checkpoint_id") == f"RV80-CP-{index:02d}",
            f"checkpoint id drift: {index}",
        )
        require(
            errors,
            checkpoint.get("range") == [(index - 1) * 20 + 1, index * 20],
            f"checkpoint range drift: {index}",
        )
        require(
            errors,
            checkpoint.get("expected_count") == 20,
            f"checkpoint expected count drift: {index}",
        )
        require(
            errors,
            checkpoint.get("first_pass_count") == 20,
            f"checkpoint first-pass count drift: {index}",
        )
        require(
            errors,
            checkpoint.get("first_pass_pass_count") == 20,
            f"checkpoint first-pass failures: {index}",
        )
        require(
            errors,
            checkpoint.get("first_pass_failure_count") == 0,
            f"checkpoint failure hidden: {index}",
        )
        require(
            errors,
            checkpoint.get("bounded_correction_count") == 0,
            f"checkpoint correction drift: {index}",
        )
        require(
            errors,
            checkpoint.get("accepted_count") == 20,
            f"checkpoint accepted count drift: {index}",
        )
        require(
            errors,
            checkpoint.get("failure_code_distribution") == {},
            f"checkpoint failure code drift: {index}",
        )
        require(
            errors,
            checkpoint.get("stop_reasons") == [],
            f"checkpoint stop reason hidden: {index}",
        )
        require(
            errors,
            checkpoint.get("status") == "PASS",
            f"checkpoint status drift: {index}",
        )

    fingerprints = bundle["fingerprints"]
    require(errors, len(fingerprints) == 80, "fingerprint index count drift")
    for row in fingerprints:
        asset = assets_by_id.get(str(row.get("asset_id")), {})
        require(
            errors,
            row.get("kernel_id") == asset.get("kernel_id"),
            f"fingerprint kernel drift: {row.get('asset_id')}",
        )
        require(
            errors,
            row.get("fingerprint")
            == asset.get("narrative_skeleton", {}).get("fingerprint"),
            f"fingerprint value drift: {row.get('asset_id')}",
        )
        require(
            errors,
            row.get("global_reuse_count")
            == fingerprint_counts[str(row.get("fingerprint"))],
            f"fingerprint reuse report drift: {row.get('asset_id')}",
        )

    coverage = bundle["coverage"]
    expected_coverage = {
        "cluster_count": 40,
        "canonical_kernel_count": 120,
        "founder_40_kernel_count": 40,
        "remaining_80_kernel_count": 80,
        "intersection_count": 0,
        "combined_unique_kernel_count": 120,
        "coverage_gap_count": 0,
        "knowledge_count_increment": 0,
    }
    require(errors, coverage == expected_coverage, "coverage report drift")
    distribution = bundle["distribution"]
    require(errors, distribution.get("total") == 80, "distribution total drift")
    require(
        errors,
        distribution.get("platform_distribution") == dict(platform_counts),
        "platform report drift",
    )
    require(
        errors,
        distribution.get("P0_distribution") == dict(p0_counts),
        "P0 report drift",
    )
    require(
        errors,
        distribution.get("balanced_quota_forced") is False,
        "platform quota was forced",
    )

    machine_metrics = {
        "governance_body_leak_count": sum(
            any(
                marker in body
                for marker in validation["body_blocking_markers"]["governance"]
            )
            for body in bodies
        ),
        "fact_slot_body_count": sum(
            any(
                marker in body
                for marker in validation["body_blocking_markers"]["fact_slots"]
            )
            for body in bodies
        ),
        "director_or_screenplay_marker_count": sum(
            any(
                marker in body
                for marker in validation["body_blocking_markers"]["director_or_script"]
            )
            for body in bodies
        ),
        "explicit_role_failure_count": sum(
            FAKE_PERSON_PATTERN.search(body) is not None
            or ROLE_FAILURE_PATTERN.search(body) is not None
            for body in bodies
        ),
        "explicit_claim_failure_count": sum(
            HARD_CLAIM_PATTERN.search(body) is not None for body in bodies
        ),
        "exact_duplicate_count": len(bodies) - len(set(bodies)),
        "normalized_duplicate_count": len(normalized_bodies)
        - len(set(normalized_bodies)),
        "skeleton_max_reuse": skeleton_max,
        "kernel_overlap_max": max(kernel_overlaps, default=0),
        "knowledge_count_inflation_count": sum(
            row.get("knowledge_count_increment") != 0 for row in assets
        ),
    }
    gate = bundle["gate"]
    require(errors, gate.get("task_id") == TASK_ID, "gate task id drift")
    require(errors, gate.get("machine_gate_status") == "PASS", "gate status not PASS")
    require(errors, gate.get("accepted_asset_count") == 80, "gate accepted count drift")
    require(
        errors,
        gate.get("first_pass_machine_pass_count") == 80,
        "gate first-pass count drift",
    )
    require(
        errors, gate.get("bounded_correction_count") == 0, "gate correction count drift"
    )
    require(
        errors,
        gate.get("unresolved_machine_failure_count") == 0,
        "gate unresolved failure drift",
    )
    require(errors, gate.get("checkpoint_count") == 4, "gate checkpoint count drift")
    require(
        errors,
        gate.get("machine_metrics") == machine_metrics,
        "gate metrics differ from independent recompute",
    )
    require(
        errors,
        gate.get("machine_platform_structure_pass_is_not_platform_quality_pass")
        is True,
        "machine/platform quality boundary missing",
    )

    capability = bundle["capability"]
    require(
        errors,
        capability.get("P0_distribution") == dict(p0_counts),
        "capability P0 summary drift",
    )
    require(
        errors,
        capability.get("platform_distribution") == dict(platform_counts),
        "capability platform summary drift",
    )
    require(
        errors,
        capability.get("generation_mode_distribution") == dict(mode_counts),
        "generation mode summary drift",
    )
    require(
        errors,
        capability.get("capture_mode_distribution") == {"daily_native": 80},
        "capture summary drift",
    )
    require(
        errors,
        capability.get("expert_review_status") == "PENDING_CLAUDE_CODE",
        "capability expert review prefilled",
    )

    guardian = bundle["guardian"]
    guardian_entries = guardian.get("entries", [])
    require(
        errors,
        guardian.get("entry_count") == 80 and len(guardian_entries) == 80,
        "guardian packet count drift",
    )
    require(
        errors,
        guardian.get("codex_does_not_fill_guardian_verdict") is True,
        "Codex allowed to fill guardian review",
    )
    for item in guardian_entries:
        asset = assets_by_id.get(str(item.get("asset_id")), {})
        require(
            errors,
            item.get("body_text") == asset.get("body_text"),
            f"guardian body drift: {item.get('asset_id')}",
        )
        for key in (
            "quality_grade",
            "platform_native_fit",
            "daily_execution_fit",
            "event_authenticity",
            "natural_spoken_voice",
            "guardian_notes",
        ):
            require(
                errors,
                item.get(key) == "PENDING",
                f"guardian field prefilled: {item.get('asset_id')}.{key}",
            )

    result = bundle["result"]
    require(errors, result.get("task_id") == TASK_ID, "result task id drift")
    require(
        errors,
        result.get("result_status")
        == "REPAIR_VALIDATION_80_EXECUTED_PENDING_CLAUDE_GUARDIAN",
        "result overclaim",
    )
    require(
        errors,
        result.get("execution_status") == "COMPLETE",
        "result execution not complete",
    )
    require(
        errors,
        result.get("machine_gate_status") == "PASS",
        "result machine gate not PASS",
    )
    require(
        errors,
        result.get("claude_code_domain_review") == "PENDING",
        "result Guardian review prefilled",
    )
    require(
        errors, result.get("actual_accepted_count") == 80, "result accepted count drift"
    )
    require(
        errors,
        result.get("first_pass_machine_pass_count") == 80,
        "result first-pass count drift",
    )
    require(
        errors,
        result.get("bounded_correction_count") == 0,
        "result correction count drift",
    )
    require(
        errors,
        result.get("unresolved_failure_count") == 0,
        "result unresolved failure drift",
    )
    require(
        errors,
        result.get("coverage")
        == {"repaired_kernel_coverage": "120/120", "knowledge_count_increment": 0},
        "result coverage drift",
    )
    require(
        errors,
        result.get("founder_40_full_grading") == "deferred_by_founder_scale_authority",
        "result hides grading deferral",
    )
    require(
        errors,
        result.get("combined_120_full_grading_required_before_600_decision") is True,
        "combined grading requirement missing",
    )
    require(
        errors, result.get("external_LLM_called") is False, "result external LLM true"
    )
    require(
        errors,
        result.get("original_assets_modified") is False,
        "result parent modification flag true",
    )
    require(
        errors,
        result.get("scale") == {"expand_600": False, "expand_3600": False},
        "result scale unlocked",
    )
    require(
        errors,
        all(value == "BLOCKED" for value in result.get("downstream", {}).values()),
        "result downstream unblocked",
    )
    require(
        errors,
        result.get("evaluation_axes", {}).get("content_fuel_support")
        == "PENDING_CLAUDE_CODE",
        "result content quality self-approved",
    )
    require(
        errors,
        result.get("evaluation_axes", {}).get("platform_native_fit")
        == "PENDING_CLAUDE_CODE",
        "result platform quality self-approved",
    )
    require(
        errors,
        result.get("evaluation_axes", {}).get("daily_execution_fit")
        == "PENDING_CLAUDE_CODE",
        "result daily quality self-approved",
    )
    require(
        errors,
        result.get("evaluation_axes", {}).get("publication_readiness") is False,
        "result publication readiness true",
    )

    receipt = bundle["receipt"]
    require(errors, receipt.get("task_id") == TASK_ID, "receipt task id drift")
    require(
        errors, receipt.get("head_before") == BASELINE_HEAD, "receipt baseline drift"
    )
    require(
        errors,
        receipt.get("result_status") == result.get("result_status"),
        "receipt result drift",
    )
    require(
        errors,
        receipt.get("selected_kernel_count") == 80,
        "receipt selection count drift",
    )
    require(
        errors,
        receipt.get("accepted_asset_count") == 80,
        "receipt accepted count drift",
    )
    require(
        errors,
        receipt.get("machine_metrics") == machine_metrics,
        "receipt metrics drift",
    )
    require(
        errors,
        receipt.get("knowledge_count_increment") == 0,
        "receipt knowledge inflation",
    )
    require(
        errors,
        receipt.get("claude_code_domain_review") == "PENDING",
        "receipt Guardian review prefilled",
    )
    require(
        errors,
        receipt.get("founder_40_full_grading") == "deferred_by_founder_scale_authority",
        "receipt hides grading deferral",
    )
    require(
        errors, receipt.get("external_LLM_called") is False, "receipt external LLM true"
    )
    require(
        errors,
        receipt.get("original_assets_modified") is False,
        "receipt original assets modified",
    )
    require(
        errors,
        receipt.get("expand_600") is False and receipt.get("expand_3600") is False,
        "receipt scale unlocked",
    )
    require(
        errors,
        receipt.get("readiness_all_false") is True,
        "receipt readiness summary drift",
    )
    require(
        errors,
        receipt.get("event_fact_binding_count") == 80,
        "receipt event/fact binding count drift",
    )
    require(
        errors,
        receipt.get("event_fact_binding_index") == BINDING_REL,
        "receipt event/fact binding path drift",
    )
    errors.extend(f"readiness true: {path}" for path in false_readiness_paths(bundle))
    metrics = {
        **machine_metrics,
        "max_cross_item_five_shingle_jaccard": round(max_cross_jaccard, 6),
        "nearest_cross_item_pair": list(nearest_pair),
        "platform_distribution": dict(platform_counts),
        "P0_distribution": dict(p0_counts),
        "generation_mode_distribution": dict(mode_counts),
        "event_fact_binding_count": len(bundle["bindings"]),
    }
    return sorted(set(errors)), metrics


def validate_baseline_assets(root: Path, errors: list[str]) -> None:
    baseline_paths = [
        line.strip()
        for line in git_text(
            root, "ls-tree", "-r", "--name-only", BASELINE_HEAD, "--", RUN_REL
        ).splitlines()
        if line.strip()
    ]
    require(errors, bool(baseline_paths), "baseline run tree is empty")
    for relative in baseline_paths:
        current = root / relative
        require(errors, current.is_file(), f"baseline asset missing: {relative}")
        if current.is_file():
            baseline = git_text(
                root, "rev-parse", f"{BASELINE_HEAD}:{relative}"
            ).strip()
            current_blob = git_text(
                root,
                "hash-object",
                f"--path={relative}",
                relative,
            ).strip()
            require(
                errors,
                current_blob == baseline,
                f"baseline asset modified: {relative}",
            )


def validate_ledger(root: Path, errors: list[str]) -> None:
    current = read_yaml(root / LEDGER_REL)["grc_3600_execution_plan_status"]
    baseline = yaml.safe_load(git_text(root, "show", f"{BASELINE_HEAD}:{LEDGER_REL}"))[
        "grc_3600_execution_plan_status"
    ]
    require(errors, "route_migration_12" in current, "route_migration_12 missing")
    stripped = copy.deepcopy(current)
    migration = stripped.pop("route_migration_12", None)
    require(
        errors,
        stripped == baseline,
        "ledger changed outside additive route_migration_12",
    )
    expected = {
        "applied_by_task": TASK_ID,
        "applied_from": "founder_authorized_after_claude_code_prompt_pre_review_conditional_pass",
        "operational_state_only": True,
        "no_existing_step_status_changed": True,
        "no_old_checker_edited": True,
        "no_readiness_flipped": True,
        "result": "REPAIR_VALIDATION_80_EXECUTED_PENDING_CLAUDE_GUARDIAN",
        "result_path": f"{OUT_REL}/repair_validation_80_result.v0.1.yaml",
        "selected_kernel_count": 80,
        "accepted_asset_count": 80,
        "first_pass_machine_pass_count": 80,
        "bounded_correction_count": 0,
        "checkpoint_count": 4,
        "combined_kernel_coverage": "120/120",
        "knowledge_count_increment": 0,
        "founder_40_full_grading": "deferred_by_founder_scale_authority",
        "combined_120_full_grading_required_before_600_decision": True,
        "claude_code_domain_review": "PENDING",
        "external_LLM_called": False,
        "original_assets_modified": False,
        "expand_600": False,
        "expand_3600": False,
        "next_action": "CLAUDE_CODE_GUARDIAN_REVIEW_ALL_80",
        "preserved_status_literals": {
            "P7C-AB": "NEXT",
            "P7C_SCALE": "BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY",
            "P7C_SCALE_PREP": "DONE",
            "P7D": "BLOCKED_BY_P7C_SCALE_DECISION",
            "P8": "BLOCKED_BY_P7D",
        },
    }
    require(errors, migration == expected, "route_migration_12 content drift")
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
        "## P7D Repair Rule Validation 80" in current_md[len(baseline_md) :],
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
    try:
        bundle = load_bundle(root)
        validate_freeze(bundle, root, errors)
        bundle_errors, metrics = validate_bundle(bundle)
        errors.extend(bundle_errors)
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        errors.append(f"structured parse/validation failed: {exc}")
        metrics = {}
    validate_baseline_assets(root, errors)
    try:
        validate_ledger(root, errors)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append(f"ledger validation failed: {exc}")
    require(errors, (root / FIXTURE_REL).is_file(), "fixture manifest missing")
    require(
        errors,
        (root / "docs/reports/p7d_repair_validation_80_report.md").is_file(),
        "human-readable report missing",
    )
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
    def remove_selection(bundle: dict[str, Any]) -> None:
        bundle["selection"].pop()

    def duplicate_selection(bundle: dict[str, Any]) -> None:
        bundle["selection"][1]["kernel_id"] = bundle["selection"][0]["kernel_id"]

    def matrix_drift(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["platform_target"] = "douyin"

    def remove_asset(bundle: dict[str, Any]) -> None:
        bundle["assets"].pop()

    def duplicate_asset_id(bundle: dict[str, Any]) -> None:
        bundle["assets"][1]["asset_id"] = bundle["assets"][0]["asset_id"]

    def body_meta_leak(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["body_text"] += " CandidatePack readiness"

    def body_slot_leak(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["body_text"] += "【品牌事实】"

    def director_leak(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["body_text"] += "做成短剧分镜"

    def fake_customer(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["body_text"] += "王女士说很喜欢。"

    def hard_claim(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["body_text"] += "保证显瘦。"

    def role_failure(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["body_text"] += "顾客调整陈列。"

    def exact_duplicate(bundle: dict[str, Any]) -> None:
        bundle["assets"][1]["body_text"] = bundle["assets"][0]["body_text"]

    def normalized_duplicate(bundle: dict[str, Any]) -> None:
        bundle["assets"][1]["body_text"] = bundle["assets"][0]["body_text"] + "！！！"

    def kernel_copy(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["body_text"] = bundle["kernels"][0]["business_judgment"]

    def skeleton_reuse(bundle: dict[str, Any]) -> None:
        for row in bundle["assets"][1:4]:
            row["narrative_skeleton"] = copy.deepcopy(
                bundle["assets"][0]["narrative_skeleton"]
            )

    def capture_drift(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["execution_card"]["capture_mode"] = "campaign_directed"

    def time_drift(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["execution_card"]["production_time_minutes_max"] = 21

    def readiness_true(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["review_metadata"]["readiness_flags"][
            "generation_allowed"
        ] = True

    def knowledge_inflation(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["knowledge_count_increment"] = 1

    def guardian_prefill(bundle: dict[str, Any]) -> None:
        bundle["guardian"]["entries"][0]["quality_grade"] = "A"

    def platform_quality_prefill(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["evaluation_axes"]["platform_native_fit"][
            "expert_status"
        ] = "PASS"

    def first_pass_missing(bundle: dict[str, Any]) -> None:
        bundle["first_pass"].pop()

    def first_pass_failure_hidden(bundle: dict[str, Any]) -> None:
        bundle["first_pass"][0]["machine_status"] = "FAIL"

    def correction_hidden(bundle: dict[str, Any]) -> None:
        bundle["first_pass"][0]["bounded_correction_used"] = True

    def checkpoint_missing(bundle: dict[str, Any]) -> None:
        bundle["checkpoints"].pop()

    def checkpoint_failure(bundle: dict[str, Any]) -> None:
        bundle["checkpoints"][0]["first_pass_failure_count"] = 3

    def failure_ledger_nonempty(bundle: dict[str, Any]) -> None:
        bundle["failures"].append({"failure_codes": ["TEST"]})

    def coverage_gap(bundle: dict[str, Any]) -> None:
        bundle["coverage"]["coverage_gap_count"] = 1

    def gate_metric_lie(bundle: dict[str, Any]) -> None:
        bundle["gate"]["machine_metrics"]["kernel_overlap_max"] = 0

    def allow_scale(bundle: dict[str, Any]) -> None:
        bundle["result"]["scale"]["expand_600"] = True

    def result_overclaim(bundle: dict[str, Any]) -> None:
        bundle["result"]["result_status"] = "PLATFORM_NATIVE_80_CONFIRMED"

    def hide_grading_deferral(bundle: dict[str, Any]) -> None:
        bundle["result"]["founder_40_full_grading"] = "PASS"

    def external_llm(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["external_LLM_called"] = True

    def payload_missing(bundle: dict[str, Any]) -> None:
        bundle["assets"][0]["platform_payload"].pop(
            next(iter(bundle["assets"][0]["platform_payload"]))
        )

    def event_spine_drift(bundle: dict[str, Any]) -> None:
        bundle["bindings"][0]["event_spine"]["event_trigger"] = "invented event"

    def fact_boundary_digest_drift(bundle: dict[str, Any]) -> None:
        bundle["bindings"][0]["fact_boundary_digest"] = "0" * 64

    return [
        ("selection_count_mismatch", remove_selection),
        ("duplicate_selected_kernel", duplicate_selection),
        ("platform_matrix_drift", matrix_drift),
        ("asset_count_mismatch", remove_asset),
        ("duplicate_asset_id", duplicate_asset_id),
        ("governance_body_leak", body_meta_leak),
        ("fact_slot_body_leak", body_slot_leak),
        ("director_or_script_leak", director_leak),
        ("fake_customer", fake_customer),
        ("unsupported_claim", hard_claim),
        ("role_action_failure", role_failure),
        ("exact_duplicate", exact_duplicate),
        ("normalized_duplicate", normalized_duplicate),
        ("source_kernel_copy", kernel_copy),
        ("skeleton_reuse", skeleton_reuse),
        ("capture_mode_drift", capture_drift),
        ("time_limit_drift", time_drift),
        ("readiness_true", readiness_true),
        ("knowledge_count_inflation", knowledge_inflation),
        ("guardian_verdict_prefilled", guardian_prefill),
        ("platform_quality_prefilled", platform_quality_prefill),
        ("first_pass_missing", first_pass_missing),
        ("first_pass_failure_hidden", first_pass_failure_hidden),
        ("bounded_correction_hidden", correction_hidden),
        ("checkpoint_missing", checkpoint_missing),
        ("checkpoint_failure_hidden", checkpoint_failure),
        ("failure_ledger_nonempty", failure_ledger_nonempty),
        ("coverage_gap", coverage_gap),
        ("gate_metric_lie", gate_metric_lie),
        ("scale_unlocked", allow_scale),
        ("result_overclaim", result_overclaim),
        ("founder_grading_deferral_hidden", hide_grading_deferral),
        ("external_llm_true", external_llm),
        ("platform_payload_missing", payload_missing),
        ("event_spine_drift", event_spine_drift),
        ("fact_boundary_digest_drift", fact_boundary_digest_drift),
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
    observed: list[str] = []
    if positive_errors:
        failures.append(f"positive fixture failed: {positive_errors}")
    for name, mutate in selftest_cases():
        candidate = copy.deepcopy(bundle)
        mutate(candidate)
        case_errors, _ = validate_bundle(candidate)
        if not case_errors:
            failures.append(f"negative fixture escaped: {name}")
        else:
            observed.append(name)
    try:
        json.loads("{malformed")
        failures.append("malformed JSON escaped")
    except json.JSONDecodeError:
        observed.append("malformed_json")
    fixture = read_yaml(root / FIXTURE_REL)["p7d_repair_validation_80_selftest"]
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
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "machine_metrics": metrics,
        "result_scope": "machine_integrity_only_all_80_require_claude_code_domain_review",
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
