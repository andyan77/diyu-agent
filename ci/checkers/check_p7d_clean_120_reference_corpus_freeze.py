#!/usr/bin/env python3
"""Fail-closed checker for the Founder-reviewed Clean-120 corpus freeze."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import yaml


TASK_ID = "GKB-P7D-CLEAN-120-FOUR-ANCHOR-NORMALIZATION-AND-REFERENCE-CORPUS-FREEZE-001"
BASELINE_HEAD = "acfeeaa615a34a974174dd1b7973da96ddebd71e"
PARENT_SHA256 = "a783363fd37ea55a5e887549e40118a9de880ec4196dc46c298ef9ded2b425ca"
SUCCESS_STATUS = (
    "FOUNDER_APPROVED_CLEAN_120_REFERENCE_CORPUS_FREEZE_EXECUTED_"
    "PENDING_CLAUDE_DELIVERY_CONFIRMATION"
)
CORPUS_ID = "FOUNDER-REVIEWED-CLEAN-120-REFERENCE-CORPUS-001"

PARENT_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_semantic_metadata_patch_001/"
    "clean_120_semantic_asset_manifest.v0.2.jsonl"
)
OUTPUT_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001"
)
CORPUS_PATH = OUTPUT_DIR / "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
DELTA_PATH = OUTPUT_DIR / "four_anchor_normalization_delta.v0.1.yaml"
FREEZE_PATH = OUTPUT_DIR / "reference_corpus_freeze_manifest.v0.1.yaml"
RESULT_PATH = OUTPUT_DIR / "reference_corpus_freeze_result.v0.1.yaml"
REPORT_PATH = Path("ci/reports/p7d_clean_120_reference_corpus_freeze_report.v0.1.json")

CHANGED_IDS = {
    "P7D40-REPAIR-234",
    "RV80-ASSET-015",
    "RV80-ASSET-049",
    "RV80-ASSET-059",
}
EXPECTED_OUTPUT_FILES = {
    CORPUS_PATH.name,
    DELTA_PATH.name,
    FREEZE_PATH.name,
    RESULT_PATH.name,
}

ALLOWED_REFERENCE_USES = [
    "offline evaluation",
    "gold/reference calibration",
    "generation contract design",
    "prompt and judge calibration",
    "future scale-batch comparison",
    "bounded generation exemplar reference",
]
FORBIDDEN_INTERPRETATIONS = [
    "ontology truth",
    "CandidatePack acceptance",
    "KE admission",
    "Serving Projection",
    "RAG context",
    "DIFY input",
    "runtime-ready content kernel",
    "production-ready content",
    "600 or 3600 generation authorization",
    "mechanical replication as a scale template",
]

EXPECTED_ANCHORS: dict[str, list[dict[str, Any]]] = {
    "RV80-ASSET-015": [
        {
            "anchor_id": "ANCH-P-001",
            "anchor_type": "apparel_item",
            "anchor_role": "primary_focus",
            "canonical_label": "大衣",
            "surface_forms": ["大衣"],
            "derivation_mode": "extractive",
            "evidence_texts": ["大衣"],
        },
        {
            "anchor_id": "ANCH-C-001",
            "anchor_type": "space_or_display",
            "anchor_role": "scene_context",
            "canonical_label": "橱窗",
            "surface_forms": ["橱窗"],
            "derivation_mode": "extractive",
            "evidence_texts": ["橱窗"],
        },
    ],
    "RV80-ASSET-049": [
        {
            "anchor_id": "ANCH-P-001",
            "anchor_type": "space_or_display",
            "anchor_role": "primary_focus",
            "canonical_label": "橱窗色彩面积与视觉层级",
            "surface_forms": [
                "橱窗",
                "最大面积",
                "辅色",
                "最亮的小配件",
                "第一眼",
                "主色",
            ],
            "derivation_mode": "faithful_composite",
            "evidence_texts": [
                "橱窗",
                "驼色毛衣裙留在中间占最大面积，辅色只在两侧接住高度，最亮的小配件收在上方一点。",
                "看第一眼是否仍回到主色上",
            ],
            "components": {
                "display_context": ["橱窗"],
                "color_area_relationship": [
                    "驼色毛衣裙留在中间占最大面积，辅色只在两侧接住高度，最亮的小配件收在上方一点。"
                ],
                "visual_hierarchy": ["看第一眼是否仍回到主色上"],
            },
        },
        {
            "anchor_id": "ANCH-S-001",
            "anchor_type": "apparel_item",
            "anchor_role": "secondary_focus",
            "canonical_label": "驼色毛衣裙",
            "surface_forms": ["驼色毛衣裙"],
            "derivation_mode": "extractive",
            "evidence_texts": ["驼色毛衣裙"],
        },
    ],
    "RV80-ASSET-059": [
        {
            "anchor_id": "ANCH-P-001",
            "anchor_type": "styling_or_selection_task",
            "anchor_role": "primary_focus",
            "canonical_label": "橱窗人台陈列实施与复核流程",
            "surface_forms": [
                "清单核对",
                "橱窗人台",
                "套上",
                "退到玻璃外",
                "复核",
                "完成标志",
            ],
            "derivation_mode": "faithful_composite",
            "evidence_texts": [
                "店长先拿清单核对可用服装与尺码",
                "再给橱窗人台套上廓形西装和阔腿裤",
                "她退到玻璃外，复核人台肩部与裤长是否落在同一条视线上",
                "每一步都有清楚的完成标志",
            ],
            "components": {
                "checklist_verification": ["店长先拿清单核对可用服装与尺码"],
                "mannequin_dressing": ["再给橱窗人台套上廓形西装和阔腿裤"],
                "outside_glass_review": [
                    "她退到玻璃外，复核人台肩部与裤长是否落在同一条视线上"
                ],
                "completion_marker": ["每一步都有清楚的完成标志"],
            },
        },
        {
            "anchor_id": "ANCH-S-001",
            "anchor_type": "apparel_item",
            "anchor_role": "secondary_focus",
            "canonical_label": "廓形西装",
            "surface_forms": ["廓形西装"],
            "derivation_mode": "extractive",
            "evidence_texts": ["廓形西装"],
        },
        {
            "anchor_id": "ANCH-S-002",
            "anchor_type": "apparel_item",
            "anchor_role": "secondary_focus",
            "canonical_label": "阔腿裤",
            "surface_forms": ["阔腿裤"],
            "derivation_mode": "extractive",
            "evidence_texts": ["阔腿裤"],
        },
        {
            "anchor_id": "ANCH-C-001",
            "anchor_type": "space_or_display",
            "anchor_role": "scene_context",
            "canonical_label": "橱窗",
            "surface_forms": ["橱窗"],
            "derivation_mode": "extractive",
            "evidence_texts": ["橱窗"],
        },
    ],
    "P7D40-REPAIR-234": [
        {
            "anchor_id": "ANCH-P-001",
            "anchor_type": "space_or_display",
            "anchor_role": "primary_focus",
            "canonical_label": "橱窗穿搭可见性复核",
            "surface_forms": ["橱窗", "穿搭", "复核", "第一眼"],
            "derivation_mode": "faithful_composite",
            "evidence_texts": [
                "橱窗",
                "给橱窗人台完成穿搭后",
                "退到玻璃外复核",
                "主角能不能第一眼被看见",
            ],
            "components": {
                "display_context": ["橱窗"],
                "completed_styling": ["给橱窗人台完成穿搭后"],
                "visibility_review": ["退到玻璃外复核"],
                "first_view_visibility": ["主角能不能第一眼被看见"],
            },
        },
        {
            "anchor_id": "ANCH-S-001",
            "anchor_type": "apparel_item",
            "anchor_role": "secondary_focus",
            "canonical_label": "藏青西装外套",
            "surface_forms": ["藏青西装外套"],
            "derivation_mode": "extractive",
            "evidence_texts": ["藏青西装外套"],
        },
        {
            "anchor_id": "ANCH-S-002",
            "anchor_type": "apparel_item",
            "anchor_role": "secondary_focus",
            "canonical_label": "白色上衣",
            "surface_forms": ["白色上衣"],
            "derivation_mode": "extractive",
            "evidence_texts": ["白色上衣"],
        },
        {
            "anchor_id": "ANCH-S-003",
            "anchor_type": "apparel_item",
            "anchor_role": "secondary_focus",
            "canonical_label": "直筒牛仔裤",
            "surface_forms": ["直筒牛仔裤"],
            "derivation_mode": "extractive",
            "evidence_texts": ["直筒牛仔裤"],
        },
        {
            "anchor_id": "ANCH-E-001",
            "anchor_type": "prop",
            "anchor_role": "execution_prop",
            "canonical_label": "橱窗人台",
            "surface_forms": ["橱窗人台"],
            "derivation_mode": "extractive",
            "evidence_texts": ["橱窗人台"],
        },
    ],
}

EXPECTED_PROJECTIONS: dict[str, Any] = {
    "RV80-ASSET-015": "大衣",
    "RV80-ASSET-049": "橱窗色彩面积与视觉层级",
    "RV80-ASSET-059": "橱窗人台陈列实施与复核流程",
    "P7D40-REPAIR-234": "橱窗穿搭可见性复核",
}


def add_error(
    errors: list[dict[str, str]], code: str, asset_id: str, detail: str
) -> None:
    errors.append({"code": code, "asset_id": asset_id, "detail": detail})


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_jsonl_with_lines(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"JSONL row is not an object: {path}:{line_number}")
        records.append(value)
    return records, lines


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return value


def exact_span(body: str, evidence: Any) -> bool:
    if not isinstance(evidence, dict):
        return False
    start = evidence.get("start")
    end = evidence.get("end")
    text = evidence.get("text")
    if (
        not isinstance(start, int)
        or not isinstance(end, int)
        or not isinstance(text, str)
        or start < 0
        or end <= start
        or end > len(body)
    ):
        return False
    return body[start:end] == text


def record_map(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record["asset_id"]: record for record in records}


def immutable_view(record: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(record)
    expression = value.get("expression_content_kernel_candidate")
    if isinstance(expression, dict):
        expression.pop("typed_anchors", None)
        expression.pop("object_anchor", None)
    return value


def anchor_evidence_texts(anchor: dict[str, Any]) -> list[str]:
    spans = anchor.get("evidence_spans")
    if not isinstance(spans, list):
        return []
    return [str(span.get("text", "")) for span in spans if isinstance(span, dict)]


def component_map(anchor: dict[str, Any]) -> dict[str, list[str]]:
    components = anchor.get("semantic_components")
    if not isinstance(components, list):
        return {}
    result: dict[str, list[str]] = {}
    for item in components:
        if not isinstance(item, dict) or not isinstance(item.get("component"), str):
            return {}
        spans = item.get("evidence_spans")
        if not isinstance(spans, list):
            return {}
        result[item["component"]] = [
            str(span.get("text", "")) for span in spans if isinstance(span, dict)
        ]
    return result


def validate_exact_anchors(
    current: dict[str, dict[str, Any]], errors: list[dict[str, str]]
) -> None:
    for asset_id, expected_anchors in EXPECTED_ANCHORS.items():
        record = current[asset_id]
        body = record["body_text"]
        expression = record["expression_content_kernel_candidate"]
        anchors = expression.get("typed_anchors")
        if not isinstance(anchors, list) or len(anchors) != len(expected_anchors):
            add_error(
                errors,
                "E_FOUNDER_ANCHOR_COUNT",
                asset_id,
                f"expected {len(expected_anchors)}",
            )
            continue
        for index, (actual, expected) in enumerate(
            zip(anchors, expected_anchors, strict=True)
        ):
            if not isinstance(actual, dict):
                add_error(errors, "E_ANCHOR_SHAPE", asset_id, str(index))
                continue
            for key in (
                "anchor_id",
                "anchor_type",
                "anchor_role",
                "canonical_label",
                "surface_forms",
                "derivation_mode",
            ):
                if actual.get(key) != expected[key]:
                    add_error(
                        errors,
                        "E_FOUNDER_ANCHOR_MAPPING",
                        asset_id,
                        f"{index}:{key}",
                    )
            if anchor_evidence_texts(actual) != expected["evidence_texts"]:
                add_error(
                    errors,
                    "E_ANCHOR_EVIDENCE_TEXT",
                    asset_id,
                    str(index),
                )
            if any(
                not exact_span(body, span) for span in actual.get("evidence_spans", [])
            ):
                add_error(errors, "E_ANCHOR_EVIDENCE_SPAN", asset_id, str(index))
            if any(surface not in body for surface in actual.get("surface_forms", [])):
                add_error(errors, "E_ANCHOR_SURFACE", asset_id, str(index))

            expected_components = expected.get("components")
            if expected_components is None:
                if "semantic_components" in actual:
                    add_error(errors, "E_UNEXPECTED_COMPONENTS", asset_id, str(index))
            else:
                if component_map(actual) != expected_components:
                    add_error(
                        errors,
                        "E_FAITHFUL_COMPOSITE_COMPONENT",
                        asset_id,
                        str(index),
                    )
                for item in actual.get("semantic_components", []):
                    if any(
                        not exact_span(body, span)
                        for span in item.get("evidence_spans", [])
                    ):
                        add_error(
                            errors,
                            "E_FAITHFUL_COMPOSITE_EVIDENCE",
                            asset_id,
                            str(index),
                        )

        primary = [
            anchor
            for anchor in anchors
            if isinstance(anchor, dict) and anchor.get("anchor_role") == "primary_focus"
        ]
        primary.sort(key=lambda item: item["evidence_spans"][0]["start"])
        if len(primary) == 1:
            expected_projection: Any = primary[0]["canonical_label"]
        else:
            expected_projection = [item["canonical_label"] for item in primary]
        projection = expression.get("object_anchor")
        if (
            not isinstance(projection, dict)
            or projection.get("status") != "DERIVED_COMPATIBILITY_PROJECTION"
            or projection.get("value") != expected_projection
            or projection.get("value") != EXPECTED_PROJECTIONS[asset_id]
            or projection.get("derived_from_anchor_ids")
            != [item["anchor_id"] for item in primary]
        ):
            add_error(
                errors,
                "E_OBJECT_ANCHOR_PROJECTION",
                asset_id,
                repr(expected_projection),
            )


def validate_records(
    records: list[dict[str, Any]],
    parent_records: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    errors: list[dict[str, str]] = []
    current = record_map(records)
    parent = record_map(parent_records)
    if len(records) != 120 or len(current) != 120:
        add_error(errors, "E_ASSET_COUNT", "GLOBAL", str(len(records)))
    if len(parent_records) != 120 or set(current) != set(parent):
        add_error(errors, "E_ASSET_DENOMINATOR", "GLOBAL", "parent mismatch")
        return errors, {}
    if len({record.get("kernel_id") for record in records}) != 120:
        add_error(errors, "E_KERNEL_COUNT", "GLOBAL", "kernel IDs")

    changed_ids: set[str] = set()
    body_matches = 0
    source_matches = 0
    role_action_headcount_matches = 0
    asset_type_matches = 0
    other_expression_matches = 0
    for asset_id, record in current.items():
        old = parent[asset_id]
        if record != old:
            changed_ids.add(asset_id)
        if record.get("body_text") == old.get("body_text"):
            body_matches += 1
        else:
            add_error(errors, "E_BODY_CHANGED", asset_id, "/body_text")
        if record.get("source_knowledge_kernel_ref") == old.get(
            "source_knowledge_kernel_ref"
        ):
            source_matches += 1
        else:
            add_error(errors, "E_SOURCE_KERNEL_CHANGED", asset_id, "source ref")
        role_keys = (
            "role_entities",
            "role_mentions",
            "action_bindings",
            "execution_card",
            "rhetorical_object_references",
        )
        if all(record.get(key) == old.get(key) for key in role_keys):
            role_action_headcount_matches += 1
        else:
            add_error(errors, "E_ROLE_ACTION_HEADCOUNT_CHANGED", asset_id, "role")
        expression = record["expression_content_kernel_candidate"]
        old_expression = old["expression_content_kernel_candidate"]
        if expression.get("expression_asset_type") == old_expression.get(
            "expression_asset_type"
        ):
            asset_type_matches += 1
        else:
            add_error(errors, "E_ASSET_TYPE_CHANGED", asset_id, "asset type")
        if immutable_view(record) == immutable_view(old):
            other_expression_matches += 1
        else:
            add_error(errors, "E_UNAUTHORIZED_DIFF", asset_id, "outside anchors")
        if record.get("knowledge_count_increment") != 0:
            add_error(errors, "E_KNOWLEDGE_INCREMENT", asset_id, "nonzero")

    if changed_ids != CHANGED_IDS:
        add_error(
            errors,
            "E_CHANGED_ASSET_SET",
            "GLOBAL",
            repr(sorted(changed_ids)),
        )
    validate_exact_anchors(current, errors)
    metrics = {
        "asset_count": len(records),
        "unique_kernel_count": len({record.get("kernel_id") for record in records}),
        "changed_asset_count": len(changed_ids),
        "changed_asset_ids": sorted(changed_ids),
        "unchanged_record_count": len(records) - len(changed_ids),
        "body_digest_match_count": body_matches,
        "source_kernel_digest_match_count": source_matches,
        "role_action_headcount_digest_match_count": role_action_headcount_matches,
        "expression_asset_type_digest_match_count": asset_type_matches,
        "other_expression_field_digest_match_count": other_expression_matches,
        "knowledge_count_increment": sum(
            int(record.get("knowledge_count_increment", 0)) for record in records
        ),
    }
    return errors, metrics


def validate_line_identity(
    records: list[dict[str, Any]],
    lines: list[str],
    parent_records: list[dict[str, Any]],
    parent_lines: list[str],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if len(lines) != 120 or len(parent_lines) != 120:
        add_error(errors, "E_LINE_COUNT", "GLOBAL", "not 120")
        return errors
    if [record.get("asset_id") for record in records] != [
        record.get("asset_id") for record in parent_records
    ]:
        add_error(errors, "E_RECORD_ORDER", "GLOBAL", "asset order drift")
        return errors
    unchanged = 0
    for record, line, parent_line in zip(records, lines, parent_lines, strict=True):
        asset_id = record["asset_id"]
        if asset_id not in CHANGED_IDS:
            if line != parent_line:
                add_error(errors, "E_116_BYTE_IDENTITY", asset_id, "line drift")
            else:
                unchanged += 1
    if unchanged != 116:
        add_error(errors, "E_116_IDENTITY_COUNT", "GLOBAL", str(unchanged))
    return errors


def validate_freeze_manifest(
    freeze: dict[str, Any],
    corpus_sha256: str,
    parent_sha256: str,
    canonical_corpus_count: int,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    root = freeze.get("reference_corpus_freeze_manifest", {})
    corpus = root.get("reference_corpus", {})
    if canonical_corpus_count != 1:
        add_error(
            errors,
            "E_MULTIPLE_CANONICAL_CORPUS",
            "GLOBAL",
            str(canonical_corpus_count),
        )
    expected_corpus = {
        "corpus_id": CORPUS_ID,
        "freeze_name": "Founder-reviewed_Clean_120_reference_corpus",
        "version": "1.0.0",
        "path": CORPUS_PATH.as_posix(),
        "asset_count": 120,
        "unique_kernel_count": 120,
        "corpus_sha256": corpus_sha256,
        "content_copy_count_in_freeze_manifest": 0,
    }
    if corpus != expected_corpus:
        add_error(errors, "E_FREEZE_CORPUS", "GLOBAL", "corpus metadata")
    expected_parent = {
        "manifest_version": "v0.2",
        "path": PARENT_PATH.as_posix(),
        "commit": BASELINE_HEAD,
        "manifest_sha256": parent_sha256,
    }
    if root.get("parent") != expected_parent:
        add_error(errors, "E_FREEZE_PARENT", "GLOBAL", "parent metadata")
    acceptance = root.get("acceptance", {})
    expected_acceptance = {
        "decision_authority": "Founder",
        "decision_recorded_by": "Codex",
        "founder_verdict": "FINAL_PASS_AFTER_APPROVED_METADATA_PATCH",
        "approved_patch_count": 4,
        "applied_patch_count": 4,
        "conditions_satisfied": True,
        "founder_final_acceptance": "PASS",
        "reference_corpus_frozen": True,
        "guardian_delivery_review": "PENDING",
    }
    if acceptance != expected_acceptance:
        add_error(errors, "E_FOUNDER_ACCEPTANCE", "GLOBAL", "decision drift")
    if root.get("inherited_record_review_status") != {
        "status": "PRE_FREEZE_HISTORICAL_METADATA",
        "authoritative_for_reference_freeze": False,
        "mutation_allowed_in_this_task": False,
        "freeze_authority": "reference_corpus_freeze_manifest.acceptance",
        "reason": "per_record_freeze_field_drift_is_forbidden",
    }:
        add_error(errors, "E_RECORD_STATUS_AUTHORITY", "GLOBAL", "freeze authority")
    if root.get("allowed_reference_uses") != ALLOWED_REFERENCE_USES:
        add_error(errors, "E_ALLOWED_USES", "GLOBAL", "use whitelist")
    if root.get("forbidden_interpretations") != FORBIDDEN_INTERPRETATIONS:
        add_error(errors, "E_FORBIDDEN_INTERPRETATIONS", "GLOBAL", "boundary")
    if root.get("expression_diversity") != {
        "status": "OPEN_SCALE_RISK",
        "reference_corpus_freeze_blocked_by_this_risk": False,
        "generation_600_blocked_by_this_risk": True,
    }:
        add_error(errors, "E_DIVERSITY_RISK", "GLOBAL", "risk closed")
    if root.get("scale") != {
        "scale_contract_design_allowed": True,
        "generation_600_allowed": False,
        "expand_600_allowed": False,
        "expand_3600_allowed": False,
    }:
        add_error(errors, "E_SCALE_BOUNDARY", "GLOBAL", "scale drift")
    readiness = root.get("downstream_and_readiness", {})
    expected_readiness = {
        "CandidatePack_ready": False,
        "KE_ready": False,
        "Serving_ready": False,
        "RAG_ready": False,
        "DIFY_ready": False,
        "production_ready": False,
        "runtime_content_kernel_ready": False,
    }
    if readiness != expected_readiness:
        add_error(errors, "E_READINESS_BOUNDARY", "GLOBAL", "readiness drift")
    return errors


def validate_supporting_artifacts(
    delta: dict[str, Any],
    result: dict[str, Any],
    corpus_sha256: str,
    metrics: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    delta_root = delta.get("four_anchor_normalization_delta", {})
    if (
        delta_root.get("changed_asset_count") != 4
        or set(delta_root.get("changed_asset_ids", [])) != CHANGED_IDS
        or {item.get("asset_id") for item in delta_root.get("items", [])} != CHANGED_IDS
    ):
        add_error(errors, "E_DELTA_SET", "GLOBAL", "four-anchor delta")
    if delta_root.get("parent", {}).get("sha256") != PARENT_SHA256:
        add_error(errors, "E_DELTA_PARENT_DIGEST", "GLOBAL", "parent SHA")
    if delta_root.get("frozen_corpus", {}).get("sha256") != corpus_sha256:
        add_error(errors, "E_DELTA_CORPUS_DIGEST", "GLOBAL", "corpus SHA")
    expected_immutability = {
        "unchanged_record_count": 116,
        "body_change_count": 0,
        "source_kernel_change_count": 0,
        "role_semantic_change_count": 0,
        "action_binding_change_count": 0,
        "headcount_change_count": 0,
        "expression_asset_type_change_count": 0,
        "other_expression_kernel_change_count": 0,
        "knowledge_count_increment": 0,
    }
    if delta_root.get("immutability") != expected_immutability:
        add_error(errors, "E_DELTA_IMMUTABILITY", "GLOBAL", "immutability")

    result_root = result.get("reference_corpus_freeze_result", {})
    if result_root.get("result_status") != SUCCESS_STATUS:
        add_error(errors, "E_RESULT_STATUS", "GLOBAL", "result status")
    expected_machine = {
        "asset_count": 120,
        "unique_kernel_count": 120,
        "changed_asset_count": 4,
        "changed_asset_ids": sorted(CHANGED_IDS),
        "changed_asset_ids_exact_match": True,
        "remaining_116_record_identity": "116/116",
        "four_founder_mappings_exact_match": True,
        "anchor_evidence_missing_count": 0,
        "faithful_composite_unsupported_count": 0,
        "object_anchor_projection_mismatch_count": 0,
        "unauthorized_json_pointer_diff_count": 0,
        "body_digest_match_count": 120,
        "source_kernel_digest_match_count": 120,
        "role_action_headcount_digest_match_count": 120,
        "expression_asset_type_digest_match_count": 120,
        "other_expression_field_digest_match_count": 120,
        "frozen_corpus_digest_present": True,
        "freeze_manifest_digest_match": True,
        "founder_decision_authority_correct": True,
        "founder_condition_satisfied": True,
    }
    if result_root.get("machine_acceptance") != expected_machine:
        add_error(errors, "E_RESULT_MACHINE", "GLOBAL", "machine metrics")
    freeze = result_root.get("freeze", {})
    if freeze != {
        "corpus_id": CORPUS_ID,
        "corpus_version": "1.0.0",
        "corpus_sha256": corpus_sha256,
        "founder_final_acceptance": "PASS",
        "reference_corpus_frozen": True,
        "guardian_delivery_review": "PENDING",
    }:
        add_error(errors, "E_RESULT_FREEZE", "GLOBAL", "freeze result")
    if result_root.get("scale") != {
        "scale_contract_design_allowed": True,
        "generation_600_allowed": False,
        "expand_600_allowed": False,
        "expand_3600_allowed": False,
    }:
        add_error(errors, "E_RESULT_SCALE", "GLOBAL", "scale result")
    if result_root.get("downstream_and_readiness", {}).get("all_false") is not True:
        add_error(errors, "E_RESULT_READINESS", "GLOBAL", "readiness result")
    if metrics.get("changed_asset_count") != 4:
        add_error(errors, "E_RESULT_DERIVATION", "GLOBAL", "computed delta")
    return errors


def git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def validate_ledger(root: Path, corpus_sha256: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    yaml_path = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
    current = load_yaml_mapping(root / yaml_path)
    baseline = yaml.safe_load(
        git_output(root, "show", f"{BASELINE_HEAD}:{yaml_path.as_posix()}")
    )
    current_root = current.get("grc_3600_execution_plan_status", {})
    baseline_root = baseline.get("grc_3600_execution_plan_status", {})
    migration = current_root.get("route_migration_17")
    if not isinstance(migration, dict):
        add_error(errors, "E_ROUTE_MIGRATION_17", "GLOBAL", "absent")
        return errors
    without_migration = copy.deepcopy(current_root)
    without_migration.pop("route_migration_17", None)
    if without_migration != baseline_root:
        add_error(errors, "E_LEDGER_NON_ADDITIVE", "GLOBAL", "outside migration17")
    current_task = migration.get("current_task", {})
    if current_task != {
        "task_id": TASK_ID,
        "patch_scope": "exact_4_metadata_only",
        "body_change_count": 0,
        "source_kernel_change_count": 0,
        "knowledge_count_increment": 0,
    }:
        add_error(errors, "E_ROUTE_TASK", "GLOBAL", "current task")
    completion = migration.get("completion", {})
    if completion != {
        "founder_final_acceptance": "PASS",
        "reference_corpus_status": "FROZEN_FOUNDER_REVIEWED",
        "corpus_sha256": corpus_sha256,
        "guardian_delivery_review": "PENDING",
    }:
        add_error(errors, "E_ROUTE_COMPLETION", "GLOBAL", "completion")
    if (
        migration.get("next_after_guardian_delivery_pass")
        != "GKB-P7D-600-EXPRESSION-DIVERSITY-AND-SAMPLED-ACCEPTANCE-CONTRACT-001"
    ):
        add_error(errors, "E_ROUTE_NEXT", "GLOBAL", "next task")
    if migration.get("scale") != {
        "scale_contract_design_allowed": True,
        "generation_600_allowed": False,
        "expand_600_allowed": False,
        "expand_3600_allowed": False,
    }:
        add_error(errors, "E_ROUTE_SCALE", "GLOBAL", "scale")
    if migration.get("downstream_and_readiness") != {"all_false": True}:
        add_error(errors, "E_ROUTE_READINESS", "GLOBAL", "readiness")

    md_path = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.md")
    current_md = (root / md_path).read_text(encoding="utf-8")
    baseline_md = git_output(root, "show", f"{BASELINE_HEAD}:{md_path.as_posix()}")
    if not current_md.startswith(baseline_md):
        add_error(errors, "E_LEDGER_MD_NON_ADDITIVE", "GLOBAL", "not append-only")
    if (
        "## P7D Founder-reviewed Clean-120 Reference Corpus Freeze"
        not in current_md[len(baseline_md) :]
    ):
        add_error(errors, "E_LEDGER_MD_SECTION", "GLOBAL", "summary absent")
    return errors


def validate_git_surface(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    allowed_prefixes = (
        OUTPUT_DIR.as_posix() + "/",
        "ci/fixtures/p7d_clean_120_reference_corpus_freeze/",
    )
    allowed_exact = {
        "ci/checkers/check_p7d_clean_120_reference_corpus_freeze.py",
        REPORT_PATH.as_posix(),
        "docs/reports/p7d_clean_120_reference_corpus_freeze_report.md",
        "docs/reports/p7d_clean_120_reference_corpus_freeze_receipt.json",
        "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
        "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    }
    changed = set(git_output(root, "diff", "--name-only", BASELINE_HEAD).splitlines())
    changed.update(
        git_output(root, "ls-files", "--others", "--exclude-standard").splitlines()
    )
    for line in git_output(root, "status", "--porcelain=v1").splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.add(path)
    for path in sorted(changed):
        if path in allowed_exact or path.startswith(allowed_prefixes):
            continue
        add_error(errors, "E_WRITE_SURFACE", "GLOBAL", path)
    new_jsonl = [path for path in changed if path.endswith(".jsonl")]
    if new_jsonl != [CORPUS_PATH.as_posix()]:
        add_error(errors, "E_CANONICAL_CORPUS_COUNT", "GLOBAL", repr(new_jsonl))
    if PARENT_PATH.as_posix() in changed:
        add_error(errors, "E_PARENT_MODIFIED", "GLOBAL", PARENT_PATH.as_posix())
    actual_output_files = {
        path.name for path in (root / OUTPUT_DIR).iterdir() if path.is_file()
    }
    if actual_output_files != EXPECTED_OUTPUT_FILES:
        add_error(
            errors,
            "E_OUTPUT_FILE_SET",
            "GLOBAL",
            repr(sorted(actual_output_files)),
        )
    return errors


def load_bundle(
    root: Path,
) -> tuple[
    list[dict[str, Any]],
    list[str],
    list[dict[str, Any]],
    list[str],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    records, lines = load_jsonl_with_lines(root / CORPUS_PATH)
    parent, parent_lines = load_jsonl_with_lines(root / PARENT_PATH)
    delta = load_yaml_mapping(root / DELTA_PATH)
    freeze = load_yaml_mapping(root / FREEZE_PATH)
    result = load_yaml_mapping(root / RESULT_PATH)
    return records, lines, parent, parent_lines, delta, freeze, result


def run_live(
    root: Path, write_report: bool
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    records, lines, parent, parent_lines, delta, freeze, result = load_bundle(root)
    parent_sha256 = sha256_bytes((root / PARENT_PATH).read_bytes())
    corpus_sha256 = sha256_bytes((root / CORPUS_PATH).read_bytes())
    errors, metrics = validate_records(records, parent)
    errors.extend(validate_line_identity(records, lines, parent, parent_lines))
    if parent_sha256 != PARENT_SHA256:
        add_error(errors, "E_PARENT_DIGEST", "GLOBAL", parent_sha256)
    errors.extend(validate_freeze_manifest(freeze, corpus_sha256, parent_sha256, 1))
    errors.extend(validate_supporting_artifacts(delta, result, corpus_sha256, metrics))
    errors.extend(validate_ledger(root, corpus_sha256))
    errors.extend(validate_git_surface(root))
    metrics["parent_manifest_sha256"] = parent_sha256
    metrics["frozen_corpus_sha256"] = corpus_sha256
    metrics["founder_final_acceptance"] = "PASS"
    metrics["reference_corpus_frozen"] = True
    metrics["guardian_delivery_review"] = "PENDING"
    report = {
        "task_id": TASK_ID,
        "checker_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "metrics": metrics,
        "result_status": SUCCESS_STATUS
        if not errors
        else "FOUR_ANCHOR_NORMALIZATION_OR_FREEZE_BLOCKED",
    }
    if write_report:
        path = root / REPORT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return errors, report


Mutator = Callable[[list[dict[str, Any]], dict[str, Any], dict[str, int]], None]


def run_selftest(root: Path) -> dict[str, Any]:
    records, _, parent, _, _, freeze, _ = load_bundle(root)
    positive_errors, _ = validate_records(records, parent)
    corpus_sha = sha256_bytes((root / CORPUS_PATH).read_bytes())
    positive_errors.extend(
        validate_freeze_manifest(freeze, corpus_sha, PARENT_SHA256, 1)
    )
    cases: list[tuple[str, Mutator]] = []

    def add_case(name: str, mutator: Mutator) -> None:
        cases.append((name, mutator))

    def row(rows: list[dict[str, Any]], asset_id: str) -> dict[str, Any]:
        return next(item for item in rows if item["asset_id"] == asset_id)

    def anchors(rows: list[dict[str, Any]], asset_id: str) -> list[dict[str, Any]]:
        return row(rows, asset_id)["expression_content_kernel_candidate"][
            "typed_anchors"
        ]

    def anchor_015_window(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        target = row(rows, "RV80-ASSET-015")["expression_content_kernel_candidate"]
        target["typed_anchors"] = [target["typed_anchors"][1]]
        target["typed_anchors"][0]["anchor_role"] = "primary_focus"
        target["object_anchor"]["value"] = "橱窗"
        target["object_anchor"]["derived_from_anchor_ids"] = ["ANCH-C-001"]

    add_case("anchor_015_window_still_primary", anchor_015_window)

    def anchor_049_no_garment(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        anchors(rows, "RV80-ASSET-049").pop()

    add_case("anchor_049_missing_garment", anchor_049_no_garment)

    def anchor_059_only_window(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        target = row(rows, "RV80-ASSET-059")["expression_content_kernel_candidate"]
        target["typed_anchors"] = [target["typed_anchors"][-1]]
        target["typed_anchors"][0]["anchor_role"] = "primary_focus"
        target["object_anchor"]["value"] = "橱窗"

    add_case("anchor_059_only_window", anchor_059_only_window)

    def anchor_234_missing_prop(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        anchors(rows, "P7D40-REPAIR-234").pop()

    add_case("anchor_234_missing_prop", anchor_234_missing_prop)

    def projection_mismatch(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        row(rows, "RV80-ASSET-049")["expression_content_kernel_candidate"][
            "object_anchor"
        ]["value"] = "橱窗"

    add_case("primary_projection_mismatch", projection_mismatch)

    def bad_evidence(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        anchors(rows, "RV80-ASSET-049")[0]["evidence_spans"][0]["text"] = "不存在"

    add_case("anchor_evidence_not_in_body", bad_evidence)

    def unsupported_composite(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        anchors(rows, "RV80-ASSET-059")[0]["semantic_components"].append(
            {
                "component": "invented_display_theory",
                "evidence_spans": [{"start": 0, "end": 2, "text": "陈列"}],
            }
        )

    add_case("faithful_composite_adds_theory", unsupported_composite)

    def fifth_asset(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        target = row(rows, "RV80-ASSET-001")["expression_content_kernel_candidate"]
        target["typed_anchors"][0]["canonical_label"] = "外套"
        target["object_anchor"]["value"] = "外套"

    add_case("fifth_asset_changed", fifth_asset)

    def body_changed(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        row(rows, "RV80-ASSET-015")["body_text"] += "改动"

    add_case("body_changed", body_changed)

    def source_changed(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        row(rows, "RV80-ASSET-015")["source_knowledge_kernel_ref"]["source_sha256"] = (
            "0" * 64
        )

    add_case("source_kernel_changed", source_changed)

    def role_changed(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        row(rows, "RV80-ASSET-059")["execution_card"]["event_required_people_min"] += 1

    add_case("role_headcount_changed", role_changed)

    def asset_type_changed(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        row(rows, "RV80-ASSET-049")["expression_content_kernel_candidate"][
            "expression_asset_type"
        ]["primary_type"] = "unauthorized_changed_type"

    add_case("expression_asset_type_changed", asset_type_changed)

    def wrong_digest(
        _rows: list[dict[str, Any]], mutable: dict[str, Any], _state: dict[str, int]
    ) -> None:
        mutable["reference_corpus_freeze_manifest"]["reference_corpus"][
            "corpus_sha256"
        ] = "0" * 64

    add_case("freeze_manifest_wrong_digest", wrong_digest)

    def only_three(
        rows: list[dict[str, Any]], _freeze: dict[str, Any], _state: dict[str, int]
    ) -> None:
        parent_row = row(parent, "RV80-ASSET-015")
        target = row(rows, "RV80-ASSET-015")
        target.clear()
        target.update(copy.deepcopy(parent_row))

    add_case("only_three_of_four_frozen", only_three)

    def second_corpus(
        _rows: list[dict[str, Any]], _freeze: dict[str, Any], state: dict[str, int]
    ) -> None:
        state["canonical_corpus_count"] = 2

    add_case("second_canonical_corpus", second_corpus)

    def generation_or_readiness(
        _rows: list[dict[str, Any]], mutable: dict[str, Any], _state: dict[str, int]
    ) -> None:
        root_value = mutable["reference_corpus_freeze_manifest"]
        root_value["scale"]["generation_600_allowed"] = True
        root_value["downstream_and_readiness"]["KE_ready"] = True

    add_case("generation_or_downstream_unlocked", generation_or_readiness)

    results: list[dict[str, Any]] = []
    for name, mutator in cases:
        mutable_records = copy.deepcopy(records)
        mutable_freeze = copy.deepcopy(freeze)
        state = {"canonical_corpus_count": 1}
        mutator(mutable_records, mutable_freeze, state)
        case_errors, _ = validate_records(mutable_records, parent)
        case_errors.extend(
            validate_freeze_manifest(
                mutable_freeze,
                corpus_sha,
                PARENT_SHA256,
                state["canonical_corpus_count"],
            )
        )
        results.append(
            {
                "name": name,
                "fail_closed": bool(case_errors),
                "error_codes": sorted({item["code"] for item in case_errors}),
            }
        )
    passed = not positive_errors and all(item["fail_closed"] for item in results)
    return {
        "task_id": TASK_ID,
        "selftest_status": "PASS" if passed else "FAIL",
        "positive_fixture_pass": not positive_errors,
        "positive_fixture_errors": positive_errors,
        "negative_fixture_count": len(results),
        "negative_fixtures": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> int:
    if not __debug__:
        sys.stdout.write(
            json.dumps({"status": "FAIL_CLOSED", "reason": "python_optimized_mode"})
            + "\n"
        )
        return 2
    args = parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        if args.selftest:
            result = run_selftest(root)
            sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            return 0 if result["selftest_status"] == "PASS" else 1
        errors, report = run_live(root, write_report=True)
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0 if not errors else 1
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        yaml.YAMLError,
        subprocess.CalledProcessError,
    ) as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "checker_status": "FAIL_CLOSED",
                    "reason": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
