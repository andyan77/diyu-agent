#!/usr/bin/env python3
"""Fail-closed checker for the source-recovered Clean-120 review package."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

try:
    import yaml
except Exception:  # pragma: no cover - explicit fail-closed branch
    yaml = None


TASK_ID = "GKB-P7D-CLEAN-120-SURGICAL-RECOVERY-AND-FINAL-REVIEW-HANDOFF-001"
BASELINE_HEAD = "045065bc364dca508b8783503f3601089c9ecbf8"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
MID_REL = f"{RUN_REL}/midbatch_320_001"
FOUNDER_REL = f"{MID_REL}/founder_40_repair_001/founder_40_repaired_assets.v0.1.jsonl"
REPAIR_80_REL = (
    f"{MID_REL}/repair_validation_80_001/repair_validation_80_assets.v0.1.jsonl"
)
REJECTED_REL = f"{MID_REL}/final_120_semantic_repair_001"
OUT_REL = f"{MID_REL}/clean_120_surgical_recovery_001"
CONTRACT_REL = f"{OUT_REL}/clean_120_semantic_integrity_contract.v0.1.yaml"
REGISTRY_REL = f"{OUT_REL}/clean_120_repair_registry.v0.1.jsonl"
CANDIDATE_REL = f"{OUT_REL}/clean_120_candidate_manifest.v0.1.jsonl"
PACKET_REL = f"{OUT_REL}/clean_120_guardian_review_packet.v0.1.yaml"
RESULT_REL = f"{OUT_REL}/clean_120_result.v0.1.yaml"
KERNEL_REL = f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml"
LEDGER_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml"
LEDGER_MD_REL = "10_execution_progress/grc_3600_execution_plan_status.v0.1.md"
REPORT_REL = "ci/reports/p7d_clean_120_surgical_recovery_report.v0.1.json"
FIXTURE_REL = "ci/fixtures/p7d_clean_120_surgical_recovery/fixture_manifest.v0.1.yaml"
DOC_REPORT_REL = "docs/reports/p7d_clean_120_surgical_recovery_report.md"
RECEIPT_REL = "docs/reports/p7d_clean_120_surgical_recovery_receipt.json"

EXPECTED_STATUS = (
    "CLEAN_120_SURGICAL_RECOVERY_EXECUTED_"
    "PENDING_CLAUDE_GUARDIAN_AND_FOUNDER_FINAL_REVIEW"
)
EXPECTED_BODY_CHANGES = {
    "P7D40-REPAIR-234",
    "P7D40-REPAIR-243",
    "RV80-ASSET-017",
    "RV80-ASSET-018",
    "RV80-ASSET-059",
    "RV80-ASSET-060",
}
KNOWN_C = {
    "RV80-ASSET-017",
    "RV80-ASSET-018",
    "RV80-ASSET-059",
    "RV80-ASSET-060",
}
PRIOR_OVERLAP = {
    "RV80-ASSET-043": 5,
    "RV80-ASSET-052": 5,
    "RV80-ASSET-056": 7,
    "RV80-ASSET-063": 5,
    "RV80-ASSET-070": 9,
    "RV80-ASSET-075": 5,
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
ALLOWED_DISPOSITIONS = {
    "CLOSED_BY_SOURCE_RECOVERY",
    "REPAIR_REQUIRED_ON_SOURCE",
    "FALSE_POSITIVE_UNDER_CANONICAL_METRIC",
    "SUPERSEDED_BY_VERIFIED_SURGICAL_FIX",
    "STILL_BLOCKING",
}
ROLE_LABELS = (
    ("陈列负责人", "visual_merchandiser"),
    ("内容同事", "content_operator"),
    ("品牌内容", "brand_content_operator"),
    ("创始人", "founder"),
    ("经营者", "founder_or_authorized_operator"),
    ("负责人", "founder_or_authorized_operator"),
    ("店长", "store_manager"),
    ("导购", "sales_associate"),
    ("版师", "pattern_maker"),
    ("买手", "buyer"),
    ("陈列师", "visual_merchandiser"),
    ("搭配师", "stylist"),
    ("店员", "store_associate"),
    ("同事", "team_member"),
    ("团队", "team_member"),
    ("实习生", "store_intern"),
    ("顾客", "customer"),
)
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
    "不抢答",
    "不下结论",
    "不用抢着",
    "先等",
    "不由",
    "不靠",
    "不能凭",
    "等人真正",
    "不直接推成",
    "不包办",
    "不说满",
    "不写",
)
HARD_ACTUAL = re.compile(
    r"今天我们店(?:发生|来了)|刚来了一位顾客|刚有一位顾客|"
    r"昨晚团队决定|顾客刚刚说|今早[^。]{0,20}我们又"
)
KNOWN_REGRESSIONS = (
    "先先",
    "导购让导购",
    "可以从替",
    "先减，先再加",
    "分次把所有信息塞满",
)
GOVERNANCE_LEAKS = (
    "candidatepack_ready",
    "generation_allowed",
    "production_servable",
    "Governance Gate",
    "Creative Gate",
    "[品牌事实]",
)
ALLOWED_PREFIXES = (
    f"{OUT_REL}/",
    "ci/checkers/check_p7d_clean_120_surgical_recovery.py",
    "ci/fixtures/p7d_clean_120_surgical_recovery/",
    REPORT_REL,
    LEDGER_REL,
    LEDGER_MD_REL,
    DOC_REPORT_REL,
    RECEIPT_REL,
)


def stable_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(
        candidate for candidate in path.rglob("*") if candidate.is_file()
    ):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(file.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: expected object")
        rows.append(value)
    return rows


def read_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML unavailable")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected mapping")
    return value


def git_text(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def baseline_bytes(root: Path, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{BASELINE_HEAD}:{relative}"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def changed_paths(root: Path) -> set[str]:
    tracked = {
        line.strip()
        for line in git_text(root, "diff", "--name-only", BASELINE_HEAD).splitlines()
        if line.strip()
    }
    untracked = {
        line.strip()
        for line in git_text(
            root, "ls-files", "--others", "--exclude-standard"
        ).splitlines()
        if line.strip()
    }
    return tracked | untracked


def normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", text)
        if not character.isspace()
        and not unicodedata.category(character).startswith("P")
    )


def sentences(text: str) -> list[str]:
    parts = [
        part.strip() for part in re.split(r"(?<=[。！？!?；;])", text) if part.strip()
    ]
    return parts or [text]


def string_leaves(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from string_leaves(item)


def longest_common_substring(left: str, right: str) -> tuple[int, str]:
    a, b = normalize(left), normalize(right)
    previous = [0] * (len(b) + 1)
    best = 0
    end = 0
    for left_index, left_character in enumerate(a, 1):
        current = [0] * (len(b) + 1)
        for right_index, right_character in enumerate(b, 1):
            if left_character == right_character:
                current[right_index] = previous[right_index - 1] + 1
                if current[right_index] > best:
                    best = current[right_index]
                    end = left_index
        previous = current
    return best, a[end - best : end]


def unsupported_positive_claim(body: str) -> bool:
    if re.search(r"卖爆|销量(?:增长|提升)|转化率(?:增长|提升)", body):
        return True
    for sentence in sentences(body):
        has_risk = any(
            term in sentence
            for term in ("显瘦", "显白", "保暖", "耐穿", "耐用", "舒适")
        )
        has_assertion = any(term in sentence for term in ("保证", "一定", "绝对"))
        has_negation = any(
            term in sentence for term in ("不", "不能", "别", "划掉", "收回")
        )
        if has_risk and has_assertion and not has_negation:
            return True
    return False


def claim_control(body: str, platform: str) -> dict[str, Any]:
    risk_sentence = next(
        (
            sentence
            for sentence in sentences(body)
            if any(term in sentence for term in HIGH_RISK_TERMS + MEDIUM_RISK_TERMS)
        ),
        "",
    )
    high = sorted(term for term in HIGH_RISK_TERMS if term in risk_sentence)
    medium = sorted(term for term in MEDIUM_RISK_TERMS if term in risk_sentence)
    bounded = any(term in risk_sentence for term in BOUNDARY_TERMS)
    if high and bounded and platform == "live":
        required, risk = "L2", "high"
    elif (high or medium) and bounded:
        required, risk = "L1", "medium"
    else:
        required, risk = "L0", "low"
    return {
        "immutable_claim_risk": risk,
        "required_route": required,
        "actual_route": required,
        "risk_terms": high or medium,
        "claim_body_span": risk_sentence if high or medium else "",
        "boundary_body_span": risk_sentence if required != "L0" else "",
        "unsupported_positive_claim": unsupported_positive_claim(body),
    }


def detected_roles(body: str) -> set[str]:
    return {role for label, role in ROLE_LABELS if label in body}


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


def language_surface_errors(asset_id: str, body: str) -> list[str]:
    errors: list[str] = []
    if body.count("“") != body.count("”"):
        errors.append(f"unbalanced quote: {asset_id}")
    if body.count("（") != body.count("）"):
        errors.append(f"unbalanced bracket: {asset_id}")
    for signature in KNOWN_REGRESSIONS:
        if signature in body:
            errors.append(f"known regression {signature}: {asset_id}")
    for signature in GOVERNANCE_LEAKS:
        if signature in body:
            errors.append(f"governance/slot leak {signature}: {asset_id}")
    return errors


def shingles(value: str, width: int = 3) -> set[str]:
    normalized = normalize(value)
    if len(normalized) < width:
        return {normalized} if normalized else set()
    return {
        normalized[index : index + width]
        for index in range(len(normalized) - width + 1)
    }


def jaccard(left: str, right: str) -> float:
    a, b = shingles(left), shingles(right)
    return len(a & b) / len(a | b) if a or b else 1.0


def max_near_boundary_cluster(boundaries: list[str], threshold: float) -> int:
    parent = list(range(len(boundaries)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left in range(len(boundaries)):
        for right in range(left + 1, len(boundaries)):
            if jaccard(boundaries[left], boundaries[right]) >= threshold:
                union(left, right)
    counts = Counter(find(index) for index in range(len(boundaries)))
    return max(counts.values(), default=0)


def source_rows(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for source_kind, relative in (
        ("founder_40", FOUNDER_REL),
        ("repair_80", REPAIR_80_REL),
    ):
        for raw in read_jsonl(root / relative):
            asset_id = str(raw.get("repair_id") or raw["asset_id"])
            rows[asset_id] = {
                "source_kind": source_kind,
                "relative": relative,
                "raw": raw,
                "kernel_id": str(
                    raw.get("bound_kernel_candidate_id") or raw["kernel_id"]
                ),
            }
    return rows


def load_bundle(root: Path) -> dict[str, Any]:
    return {
        "registry": read_jsonl(root / REGISTRY_REL),
        "candidates": read_jsonl(root / CANDIDATE_REL),
        "contract": read_yaml(root / CONTRACT_REL)[
            "clean_120_semantic_integrity_contract"
        ],
        "packet": read_yaml(root / PACKET_REL)["clean_120_guardian_review_packet"],
        "result": read_yaml(root / RESULT_REL)["clean_120_result"],
    }


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_core(
    bundle: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    kernel_entries: list[dict[str, Any]],
    *,
    check_overlap: bool,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    registry = bundle["registry"]
    candidates = bundle["candidates"]
    contract = bundle["contract"]
    packet = bundle["packet"]
    result = bundle["result"]

    require(errors, len(sources) == 120, "source count must be 120")
    require(errors, len(registry) == 120, "registry count must be 120")
    require(errors, len(candidates) == 120, "candidate count must be 120")
    records = contract.get("records", [])
    require(errors, len(records) == 120, "contract record count must be 120")

    registry_by_id = {str(row.get("asset_id")): row for row in registry}
    candidates_by_id = {str(row.get("asset_id")): row for row in candidates}
    records_by_id = {str(row.get("asset_id")): row for row in records}
    require(errors, len(registry_by_id) == 120, "duplicate registry asset ID")
    require(errors, len(candidates_by_id) == 120, "duplicate candidate asset ID")
    require(errors, len(records_by_id) == 120, "duplicate contract asset ID")
    require(
        errors,
        set(sources)
        == set(registry_by_id)
        == set(candidates_by_id)
        == set(records_by_id),
        "source/registry/candidate/contract ID drift",
    )

    approved = {
        asset_id
        for asset_id, row in registry_by_id.items()
        if row.get("repair", {}).get("approved_body_change") is True
    }
    require(errors, approved == EXPECTED_BODY_CHANGES, "approved body-change set drift")
    require(errors, len(approved) <= 40, "body-change cap exceeded")
    changed = {
        asset_id
        for asset_id, row in candidates_by_id.items()
        if row.get("body_changed") is True
    }
    require(errors, changed == approved, "changed-body IDs differ from registry")

    disposition_counts: Counter[str] = Counter()
    disposition_total = 0
    for asset_id, row in registry_by_id.items():
        require(
            errors,
            row.get("frozen_before_body_authoring") is True,
            f"registry was not frozen first: {asset_id}",
        )
        for key in (
            "facts_changed",
            "kernel_changed",
            "claim_risk_changed",
            "claim_safety_reduced",
            "mechanical_transform_used",
        ):
            require(errors, row.get(key) is False, f"registry {key}: {asset_id}")
        for disposition in row.get("prior_blocker_dispositions", []):
            family = str(disposition.get("blocker_family"))
            disposition_counts[family] += 1
            disposition_total += 1
            require(
                errors,
                disposition.get("disposition") in ALLOWED_DISPOSITIONS,
                f"invalid blocker disposition: {asset_id}",
            )
            require(
                errors,
                disposition.get("disposition") != "STILL_BLOCKING",
                f"still-blocking disposition in PASS result: {asset_id}",
            )
    expected_dispositions = {
        "failed_candidate_formula": 69,
        "kernel_overlap": 6,
        "failed_candidate_event_depiction": 3,
        "failed_candidate_claim_route": 4,
        "failed_candidate_unsupported_claim": 1,
        "known_c": 4,
        "failed_candidate_language_regression": 8,
        "source_model_participation_ambiguity": 2,
    }
    for family, expected in expected_dispositions.items():
        require(
            errors,
            disposition_counts[family] == expected,
            f"prior blocker disposition coverage drift: {family}",
        )

    thresholds = contract.get("fixed_thresholds", {})
    require(
        errors,
        thresholds.get("kernel_overlap_max_chars") == 17,
        "overlap threshold changed",
    )
    require(
        errors,
        thresholds.get("normalization")
        == "Unicode_NFKC_remove_whitespace_and_punctuation_preserve_semantic_characters",
        "normalization changed",
    )
    require(
        errors, thresholds.get("l2_asset_share_max") == 0.15, "L2 threshold changed"
    )
    registry_meta = contract.get("repair_registry", {})
    require(
        errors, registry_meta.get("body_change_cap") == 40, "body-change cap changed"
    )

    all_bodies: list[str] = []
    all_normalized_bodies: list[str] = []
    openings: list[str] = []
    closings: list[str] = []
    boundaries: list[str] = []
    l2_count = 0
    language_failure_count = 0
    semantic_failure_count = 0
    role_failure_count = 0
    event_failure_count = 0
    claim_failure_count = 0
    unsupported_count = 0
    kernel_ids: set[str] = set()

    for asset_id, candidate in candidates_by_id.items():
        source = sources.get(asset_id, {})
        raw = source.get("raw", {})
        registry_row = registry_by_id.get(asset_id, {})
        record = records_by_id.get(asset_id, {})
        source_body = str(raw.get("body_text", ""))
        body = str(candidate.get("body_text", ""))
        kernel_id = str(
            raw.get("bound_kernel_candidate_id") or raw.get("kernel_id", "")
        )
        kernel_ids.add(str(candidate.get("kernel_id")))
        require(
            errors,
            candidate.get("kernel_id") == kernel_id,
            f"kernel ID drift: {asset_id}",
        )
        require(
            errors,
            candidate.get("source_body_sha256") == text_digest(source_body),
            f"source body digest drift: {asset_id}",
        )
        require(
            errors,
            candidate.get("body_sha256") == text_digest(body),
            f"body digest drift: {asset_id}",
        )
        require(
            errors,
            candidate.get("content_kernel") == raw.get("content_kernel", {}),
            f"content kernel changed: {asset_id}",
        )
        require(
            errors,
            candidate.get("content_kernel_sha256")
            == stable_digest(raw.get("content_kernel", {})),
            f"content kernel digest drift: {asset_id}",
        )
        approved_change = (
            registry_row.get("repair", {}).get("approved_body_change") is True
        )
        if approved_change:
            require(
                errors,
                body != source_body,
                f"approved body repair did not change: {asset_id}",
            )
        else:
            require(
                errors, body == source_body, f"registry outside body change: {asset_id}"
            )
        require(
            errors,
            candidate.get("body_origin")
            == ("surgical_repair" if approved_change else "source_byte_identical"),
            f"body origin drift: {asset_id}",
        )
        require(
            errors,
            REJECTED_REL not in str(candidate.get("source_asset_path")),
            f"rejected resolved used as body parent: {asset_id}",
        )
        require(
            errors,
            candidate.get("creates_new_knowledge") is False,
            f"knowledge inflation: {asset_id}",
        )
        require(
            errors,
            candidate.get("knowledge_count_increment") == 0,
            f"knowledge count drift: {asset_id}",
        )
        require(
            errors,
            candidate.get("counts_toward_600_or_3600") is False,
            f"scale count drift: {asset_id}",
        )
        require(
            errors,
            candidate.get("external_LLM_called") is False,
            f"external LLM claim: {asset_id}",
        )
        readiness_failures = false_readiness_paths(candidate)
        errors.extend(
            f"readiness true: {asset_id}:{path}" for path in readiness_failures
        )

        require(
            errors,
            record.get("kernel_id") == kernel_id,
            f"contract kernel drift: {asset_id}",
        )
        lineage = record.get("lineage", {})
        require(
            errors,
            lineage.get("body_origin") == candidate.get("body_origin"),
            f"contract lineage drift: {asset_id}",
        )
        require(
            errors,
            lineage.get("rejected_resolved_used_as_body_source") is False,
            f"rejected body source admitted: {asset_id}",
        )
        for key in (
            "facts_changed",
            "kernel_changed",
            "claim_risk_changed",
            "claim_safety_reduced",
            "mechanical_transform_used",
        ):
            require(errors, record.get(key) is False, f"contract {key}: {asset_id}")

        binding = record.get("semantic_binding", {})
        declared_roles = {
            str(row.get("role")) for row in binding.get("mentioned_roles", [])
        }
        body_roles = detected_roles(body)
        if not body_roles.issubset(declared_roles):
            role_failure_count += 1
            errors.append(f"undeclared body role: {asset_id}")
        executors = binding.get("action_executors", [])
        executor_roles = {str(row.get("role")) for row in executors}
        natural_roles = {
            str(role) for role in binding.get("natural_participant_roles", [])
        }
        if executor_roles != natural_roles:
            role_failure_count += 1
            errors.append(f"executor/participant role drift: {asset_id}")
        if binding.get("required_unique_people_min") != len(natural_roles):
            role_failure_count += 1
            errors.append(f"participant undercount: {asset_id}")
        if binding.get("max_simultaneous_visible_people") != len(natural_roles):
            role_failure_count += 1
            errors.append(f"visible people count drift: {asset_id}")
        for executor in executors:
            evidence = str(executor.get("body_evidence", ""))
            if evidence not in body:
                role_failure_count += 1
                errors.append(f"action body evidence missing: {asset_id}")
        authority = binding.get("narration_authority", {})
        require(
            errors,
            authority.get("mode")
            in {
                "self_performed",
                "decision_owner",
                "authorized_observer",
                "editorial_host",
            },
            f"narration authority missing: {asset_id}",
        )
        require(
            errors,
            str(authority.get("body_evidence", "")) in body,
            f"narration authority evidence missing: {asset_id}",
        )
        expected_model = "mannequin_prop" if "人台" in body else "none"
        model = binding.get("model_participation", {})
        if model.get("kind") != expected_model or "模特" in body:
            role_failure_count += 1
            errors.append(f"model kind mismatch: {asset_id}")
        require(
            errors,
            binding.get("hired_performer_count") == 0,
            f"hired performer: {asset_id}",
        )
        require(
            errors,
            binding.get("platform_target") == candidate.get("platform_target"),
            f"platform binding drift: {asset_id}",
        )

        event = record.get("event_binding", {})
        event_evidence = str(event.get("body_evidence", ""))
        if (
            event.get("event_surface_mode") != "brand_fillable_prototype"
            or event.get("source_anchor") is not None
            or event_evidence not in body
            or HARD_ACTUAL.search(body)
        ):
            event_failure_count += 1
            errors.append(f"prototype/event mismatch: {asset_id}")

        expected_claim = claim_control(body, str(candidate.get("platform_target")))
        actual_claim = record.get("claim_control", {})
        if actual_claim != expected_claim:
            claim_failure_count += 1
            errors.append(f"claim route mismatch: {asset_id}")
        if expected_claim["unsupported_positive_claim"]:
            unsupported_count += 1
            errors.append(f"unsupported claim: {asset_id}")
        if actual_claim.get("actual_route") == "L2":
            l2_count += 1
        boundary = str(actual_claim.get("boundary_body_span", ""))
        if boundary:
            require(errors, boundary in body, f"boundary span missing: {asset_id}")
            boundaries.append(boundary)

        invariants = record.get("meaning_invariants", [])
        if approved_change:
            require(
                errors, len(invariants) >= 3, f"meaning invariants missing: {asset_id}"
            )
            for invariant in invariants:
                source_evidence = str(invariant.get("source_evidence", ""))
                target_evidence = str(invariant.get("target_evidence", ""))
                if source_evidence not in source_body:
                    semantic_failure_count += 1
                    errors.append(f"source evidence missing: {asset_id}")
                if target_evidence not in body:
                    semantic_failure_count += 1
                    errors.append(f"target evidence missing: {asset_id}")
                require(
                    errors,
                    invariant.get("change_allowed") is False,
                    f"meaning change allowed: {asset_id}",
                )
        else:
            expected_identity = text_digest(source_body)
            require(
                errors,
                len(invariants) == 1,
                f"source identity invariant drift: {asset_id}",
            )
            invariant = invariants[0] if invariants else {}
            require(
                errors,
                invariant.get("kind") == "source_identity"
                and invariant.get("source_evidence") == expected_identity
                and invariant.get("target_evidence") == expected_identity,
                f"source identity invariant failure: {asset_id}",
            )

        surface_errors = language_surface_errors(asset_id, body)
        language_failure_count += len(surface_errors)
        errors.extend(surface_errors)
        all_bodies.append(body)
        all_normalized_bodies.append(normalize(body))
        openings.append(normalize(sentences(body)[0]))
        closings.append(normalize(sentences(body)[-1]))

    require(errors, len(kernel_ids) == 120, "unique kernel count must be 120")
    exact_duplicates = sum(
        count - 1 for count in Counter(all_bodies).values() if count > 1
    )
    normalized_duplicates = sum(
        count - 1 for count in Counter(all_normalized_bodies).values() if count > 1
    )
    opening_reuse = max(Counter(openings).values(), default=0)
    closing_reuse = max(Counter(closings).values(), default=0)
    boundary_reuse = max(
        Counter(normalize(value) for value in boundaries).values(), default=0
    )
    near_boundary_cluster = max_near_boundary_cluster(boundaries, 0.92)
    require(errors, exact_duplicates == 0, "exact body duplicate")
    require(errors, normalized_duplicates == 0, "normalized body duplicate")
    require(errors, opening_reuse <= 2, "exact opening sentence reuse")
    require(errors, closing_reuse <= 2, "exact closing sentence reuse")
    require(errors, boundary_reuse <= 2, "exact claim boundary sentence reuse")
    require(errors, near_boundary_cluster <= 3, "near claim-boundary cluster")
    require(errors, l2_count <= 18, "L2 asset share exceeds 15 percent")

    overlap_max = 0
    overlap_by_id: dict[str, int] = {}
    overlap_details: list[dict[str, Any]] = []
    if check_overlap:
        kernel_fields = (
            "object_anchor",
            "human_subject",
            "human_action",
            "scene_premise",
            "business_judgment",
            "tradeoff_or_tension",
            "spoken_line_seed",
            "output_asset_hint",
        )
        kernel_strings: list[tuple[str, str, str]] = []
        for entry in kernel_entries:
            for field in kernel_fields:
                for value in string_leaves(entry.get(field)):
                    kernel_strings.append(
                        (str(entry.get("candidate_id")), field, value)
                    )
        for asset_id, candidate in candidates_by_id.items():
            best_length = 0
            best_kernel = ""
            best_field = ""
            best_fragment = ""
            for kernel_id, field, value in kernel_strings:
                length, fragment = longest_common_substring(
                    str(candidate.get("body_text", "")), value
                )
                if length > best_length:
                    best_length = length
                    best_kernel = kernel_id
                    best_field = field
                    best_fragment = fragment
            overlap_max = max(overlap_max, best_length)
            overlap_by_id[asset_id] = best_length
            overlap_details.append(
                {
                    "asset_id": asset_id,
                    "matched_kernel_id": best_kernel,
                    "matched_kernel_field": best_field,
                    "matched_substring": best_fragment,
                    "overlap_length": best_length,
                }
            )
        require(errors, overlap_max <= 17, "canonical kernel overlap exceeds 17")
        for asset_id, expected in PRIOR_OVERLAP.items():
            require(
                errors,
                overlap_by_id.get(asset_id) == expected,
                f"prior overlap false-positive recompute drift: {asset_id}",
            )

    require(errors, packet.get("candidate_count") == 120, "packet count drift")
    require(
        errors, packet.get("changed_asset_count") == 6, "packet changed count drift"
    )
    packet_changed = {
        str(row.get("asset_id"))
        for row in packet.get("changed_assets_before_after", [])
    }
    require(errors, packet_changed == approved, "packet changed set drift")
    for row in packet.get("changed_assets_before_after", []):
        asset_id = str(row.get("asset_id"))
        require(
            errors,
            row.get("source_body") == sources[asset_id]["raw"].get("body_text"),
            f"packet before-body drift: {asset_id}",
        )
        require(
            errors,
            row.get("clean_body") == candidates_by_id[asset_id].get("body_text"),
            f"packet after-body drift: {asset_id}",
        )

    result_gate = result.get("machine_gate", {})
    require(
        errors,
        result.get("result_status") == EXPECTED_STATUS,
        "result overclaim or status drift",
    )
    require(errors, result_gate.get("status") == "PASS", "machine status drift")
    require(
        errors,
        result_gate.get("cross_layer_failure_count") == role_failure_count,
        "cross-layer metric lie",
    )
    require(
        errors,
        result_gate.get("event_mismatch_count") == event_failure_count,
        "event metric lie",
    )
    require(
        errors,
        result_gate.get("claim_route_mismatch_count") == claim_failure_count,
        "claim metric lie",
    )
    require(
        errors,
        result_gate.get("unsupported_claim_count") == unsupported_count,
        "unsupported metric lie",
    )
    require(
        errors,
        result_gate.get("semantic_invariant_failure_count") == semantic_failure_count,
        "semantic metric lie",
    )
    require(
        errors,
        result_gate.get("language_surface_failure_count") == language_failure_count,
        "language metric lie",
    )
    require(
        errors,
        result_gate.get("exact_duplicate_count") == exact_duplicates,
        "duplicate metric lie",
    )
    require(
        errors,
        result_gate.get("normalized_duplicate_count") == normalized_duplicates,
        "normalized duplicate metric lie",
    )
    require(
        errors,
        result_gate.get("exact_opening_sentence_reuse_max") == opening_reuse,
        "opening metric lie",
    )
    require(
        errors,
        result_gate.get("exact_closing_sentence_reuse_max") == closing_reuse,
        "closing metric lie",
    )
    require(
        errors,
        result_gate.get("exact_claim_boundary_sentence_reuse_max") == boundary_reuse,
        "boundary metric lie",
    )
    require(errors, result_gate.get("l2_asset_count") == l2_count, "L2 metric lie")
    if check_overlap:
        require(
            errors,
            result_gate.get("kernel_overlap_max") == overlap_max,
            "overlap metric lie",
        )
    require(
        errors,
        result.get("claude_code_guardian_review") == "PENDING",
        "guardian review overclaim",
    )
    require(
        errors,
        result.get("founder_final_acceptance") == "PENDING",
        "founder acceptance overclaim",
    )
    require(
        errors,
        result.get("scale") == {"expand_600": False, "expand_3600": False},
        "scale lock drift",
    )
    require(
        errors,
        all(value == "BLOCKED" for value in result.get("downstream", {}).values()),
        "downstream unlocked",
    )
    require(
        errors, result.get("readiness_all_false") is True, "readiness summary drift"
    )
    errors.extend(f"readiness true: {path}" for path in false_readiness_paths(bundle))

    metrics = {
        "asset_count": len(candidates),
        "unique_kernel_count": len(kernel_ids),
        "body_repair_count": len(changed),
        "metadata_only_repair_count": sum(
            row.get("repair", {}).get("authorized_route") == "metadata_alignment"
            for row in registry
        ),
        "prior_blocker_disposition_count": disposition_total,
        "false_positive_or_closed_by_recovery_count": sum(
            disposition.get("disposition")
            in {"CLOSED_BY_SOURCE_RECOVERY", "FALSE_POSITIVE_UNDER_CANONICAL_METRIC"}
            for row in registry
            for disposition in row.get("prior_blocker_dispositions", [])
        ),
        "cross_layer_failure_count": role_failure_count,
        "event_mismatch_count": event_failure_count,
        "claim_route_mismatch_count": claim_failure_count,
        "unsupported_claim_count": unsupported_count,
        "semantic_invariant_failure_count": semantic_failure_count,
        "language_surface_failure_count": language_failure_count,
        "formula_blocker_count": int(
            any(
                (
                    exact_duplicates,
                    normalized_duplicates,
                    opening_reuse > 2,
                    closing_reuse > 2,
                    boundary_reuse > 2,
                    near_boundary_cluster > 3,
                )
            )
        ),
        "kernel_overlap_max": overlap_max,
        "l2_asset_count": l2_count,
        "overlap_details": overlap_details,
    }
    return errors, metrics


def validate_repository(root: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    require(
        errors,
        git_text(root, "branch", "--show-current").strip() == "master",
        "branch drift",
    )
    require(
        errors,
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", BASELINE_HEAD, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0,
        "baseline is not an ancestor",
    )
    for relative in (FOUNDER_REL, REPAIR_80_REL):
        require(
            errors,
            (root / relative).read_bytes() == baseline_bytes(root, relative),
            f"source asset mutated: {relative}",
        )
    rejected_files = [
        line
        for line in git_text(
            root, "ls-tree", "-r", "--name-only", BASELINE_HEAD, REJECTED_REL
        ).splitlines()
        if line
    ]
    for relative in rejected_files:
        require(
            errors,
            (root / relative).read_bytes() == baseline_bytes(root, relative),
            f"rejected negative evidence mutated: {relative}",
        )
    paths = changed_paths(root)
    for path in sorted(paths):
        require(
            errors,
            any(
                path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES
            ),
            f"changed outside allowed surface: {path}",
        )

    try:
        bundle = load_bundle(root)
        sources = source_rows(root)
        kernel_entries = read_yaml(root / KERNEL_REL)["user_visible_kernel_matrix"][
            "entries"
        ]
    except Exception as error:
        return [*errors, f"parse failure: {error}"], {}
    contract = bundle["contract"]
    require(
        errors,
        contract.get("source_lineage", {}).get("founder_40_sha256")
        == file_digest(root / FOUNDER_REL),
        "Founder-40 source digest drift",
    )
    require(
        errors,
        contract.get("source_lineage", {}).get("repair_80_sha256")
        == file_digest(root / REPAIR_80_REL),
        "Repair-80 source digest drift",
    )
    require(
        errors,
        contract.get("source_lineage", {}).get("rejected_final_120_tree_sha256")
        == tree_digest(root / REJECTED_REL),
        "rejected tree digest drift",
    )
    require(
        errors,
        contract.get("repair_registry", {}).get("sha256")
        == file_digest(root / REGISTRY_REL),
        "frozen registry digest drift",
    )

    core_errors, metrics = validate_core(
        bundle,
        sources,
        kernel_entries,
        check_overlap=True,
    )
    errors.extend(core_errors)

    try:
        current_ledger = read_yaml(root / LEDGER_REL)["grc_3600_execution_plan_status"]
        baseline_ledger = yaml.safe_load(baseline_bytes(root, LEDGER_REL).decode())[
            "grc_3600_execution_plan_status"
        ]
        migration = current_ledger.get("route_migration_14", {})
        current_without_migration = copy.deepcopy(current_ledger)
        current_without_migration.pop("route_migration_14", None)
        require(
            errors,
            current_without_migration == baseline_ledger,
            "ledger changed outside route_migration_14",
        )
        require(
            errors,
            migration.get("applied_by_task") == TASK_ID,
            "route_migration_14 task drift",
        )
        require(
            errors,
            migration.get("prior_task", {}).get("status")
            == "NEGATIVE_RESULT_REJECTED_AS_CANONICAL_CORPUS",
            "prior negative result status drift",
        )
        require(
            errors,
            migration.get("source_lineage") == "founder_40_plus_repair_80",
            "route source lineage drift",
        )
        require(
            errors,
            migration.get("next_if_machine_pass")
            == "CLAUDE_CODE_CLEAN_120_GUARDIAN_REVIEW",
            "next action drift",
        )
        require(
            errors,
            migration.get("scale") == {"expand_600": False, "expand_3600": False},
            "ledger scale drift",
        )
        require(
            errors,
            migration.get("downstream_and_readiness", {}).get("all_false") is True,
            "ledger readiness drift",
        )
    except Exception as error:
        errors.append(f"ledger validation failure: {error}")
    require(errors, (root / DOC_REPORT_REL).is_file(), "documentation report missing")
    require(errors, (root / RECEIPT_REL).is_file(), "receipt missing")
    require(errors, (root / FIXTURE_REL).is_file(), "fixture manifest missing")
    return errors, metrics


def mutate_case(bundle: dict[str, Any], name: str) -> str:
    candidates = bundle["candidates"]
    records = bundle["contract"]["records"]
    registry = bundle["registry"]
    result = bundle["result"]
    candidate_by_id = {row["asset_id"]: row for row in candidates}
    record_by_id = {row["asset_id"]: row for row in records}
    if name == "rejected_body_parent":
        candidate_by_id["RV80-ASSET-001"]["source_asset_path"] = f"{REJECTED_REL}/bad"
        return "rejected resolved used as body parent"
    if name == "registry_outside_body_change":
        candidate_by_id["RV80-ASSET-001"]["body_text"] += "坏"
        return "registry outside body change"
    if name in {
        "polarity_inversion",
        "deferral_lost",
        "action_order_changed",
        "claim_stance_changed",
    }:
        target = record_by_id["RV80-ASSET-060"]["meaning_invariants"][0]
        target["target_evidence"] = "不存在的反向证据"
        return "target evidence missing"
    if name == "orphan_quote":
        candidate_by_id["RV80-ASSET-001"]["body_text"] += "“"
        return "unbalanced quote"
    if name == "role_undeclared":
        record_by_id["RV80-ASSET-017"]["semantic_binding"]["mentioned_roles"] = []
        return "undeclared body role"
    if name == "participant_undercount":
        record_by_id["RV80-ASSET-017"]["semantic_binding"][
            "required_unique_people_min"
        ] = 1
        return "participant undercount"
    if name == "human_mannequin_confusion":
        record_by_id["RV80-ASSET-059"]["semantic_binding"]["model_participation"][
            "kind"
        ] = "hired_human"
        return "model kind mismatch"
    if name == "prototype_as_actual":
        record_by_id["RV80-ASSET-001"]["event_binding"]["event_surface_mode"] = (
            "verified_real_event"
        )
        return "prototype/event mismatch"
    if name == "high_risk_to_l0":
        row = next(
            row for row in records if row["claim_control"]["actual_route"] == "L2"
        )
        row["claim_control"]["actual_route"] = "L0"
        return "claim route mismatch"
    if name == "generic_l2_reuse":
        rows = [row for row in records if row["claim_control"]["actual_route"] == "L2"][
            :4
        ]
        for row in rows:
            row["claim_control"]["boundary_body_span"] = "统一免责"
        return "claim route mismatch"
    if name == "threshold_tamper":
        bundle["contract"]["fixed_thresholds"]["kernel_overlap_max_chars"] = 18
        return "overlap threshold changed"
    if name == "normalization_tamper":
        bundle["contract"]["fixed_thresholds"]["normalization"] = "remove_negation"
        return "normalization changed"
    if name == "readiness_true":
        candidate_by_id["RV80-ASSET-001"]["readiness_flags"]["generation_allowed"] = (
            True
        )
        return "readiness true"
    if name == "scale_true":
        result["scale"]["expand_600"] = True
        return "scale lock drift"
    if name == "kernel_changed":
        candidate_by_id["RV80-ASSET-001"]["content_kernel"]["business_judgment"] = (
            "changed"
        )
        return "content kernel changed"
    if name == "mechanical_transform":
        registry[0]["mechanical_transform_used"] = True
        return "registry mechanical_transform_used"
    if name == "knowledge_inflation":
        candidate_by_id["RV80-ASSET-001"]["knowledge_count_increment"] = 1
        return "knowledge count drift"
    raise ValueError(name)


def run_selftest(root: Path) -> tuple[bool, dict[str, Any]]:
    try:
        base = load_bundle(root)
        sources = source_rows(root)
        kernel_entries = read_yaml(root / KERNEL_REL)["user_visible_kernel_matrix"][
            "entries"
        ]
        fixture = read_yaml(root / FIXTURE_REL)[
            "p7d_clean_120_surgical_recovery_selftest"
        ]
    except Exception as error:
        return False, {"status": "FAIL", "error": str(error)}
    positive_errors, _ = validate_core(
        copy.deepcopy(base), sources, kernel_entries, check_overlap=False
    )
    failures: list[str] = []
    if positive_errors:
        failures.append(f"positive fixture failed: {positive_errors[:3]}")
    expected_cases = list(fixture.get("negative_cases", []))
    observed: list[str] = []
    for name in expected_cases:
        mutated = copy.deepcopy(base)
        expected_error = mutate_case(mutated, name)
        case_errors, _ = validate_core(
            mutated,
            sources,
            kernel_entries,
            check_overlap=False,
        )
        if not any(expected_error in error for error in case_errors):
            failures.append(f"{name}: expected guard not hit ({expected_error})")
        else:
            observed.append(name)
    overlap_length, _ = longest_common_substring("甲" * 18, "甲" * 18)
    if overlap_length <= 17:
        failures.append("kernel_overlap_18: overlap guard primitive failed")
    else:
        observed.append("kernel_overlap_18")
    if sorted(observed) != sorted(expected_cases + ["kernel_overlap_18"]):
        failures.append("fixture case coverage drift")
    return not failures, {
        "status": "PASS" if not failures else "FAIL",
        "positive_fixture": "PASS" if not positive_errors else "FAIL",
        "negative_case_count": len(observed),
        "negative_cases": observed,
        "failures": failures,
    }


def write_report(root: Path, errors: list[str], metrics: dict[str, Any]) -> None:
    payload = {
        "task_id": TASK_ID,
        "checker_status": "PASS" if not errors else "FAIL",
        "execution_result_status": EXPECTED_STATUS
        if not errors
        else "SURGICAL_RECOVERY_BLOCKED",
        "error_count": len(errors),
        "errors": errors,
        "metrics": metrics,
    }
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if not __debug__:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "python_optimized"}))
        return 2
    if yaml is None:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "yaml_unavailable"}))
        return 2
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if arguments.selftest:
        passed, payload = run_selftest(root)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if passed else 1
    try:
        errors, metrics = validate_repository(root)
    except Exception as error:  # pragma: no cover - fail-closed outer boundary
        errors, metrics = [f"checker exception: {error}"], {}
    write_report(root, errors, metrics)
    payload = {
        "task_id": TASK_ID,
        "checker_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "metrics": metrics,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
