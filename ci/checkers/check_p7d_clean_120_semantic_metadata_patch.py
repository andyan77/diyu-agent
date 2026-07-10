#!/usr/bin/env python3
"""Fail-closed checker for the Clean-120 metadata precision patch."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml


TASK_ID = (
    "GKB-P7D-CLEAN-120-METADATA-ONLY-SEMANTIC-PRECISION-PATCH-"
    "AND-FINAL-ACCEPTANCE-HANDOFF-001"
)
BASELINE_HEAD = "c20c3a98b1ba0203033c021a9c13d5a527e3adae"
SUCCESS_STATUS = (
    "CLEAN_120_METADATA_PRECISION_PATCH_EXECUTED_"
    "PENDING_CLAUDE_DELTA_AND_FOUNDER_FINAL_ACCEPTANCE"
)
MACHINE_SCOPE = "STRUCTURAL_METADATA_AND_EVIDENCE_ONLY"

PARENT_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_semantic_asset_closeout_001/"
    "clean_120_semantic_asset_manifest.v0.1.jsonl"
)
OUTPUT_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_semantic_metadata_patch_001"
)
MANIFEST_PATH = OUTPUT_DIR / "clean_120_semantic_asset_manifest.v0.2.jsonl"
CONTRACT_PATH = OUTPUT_DIR / "semantic_metadata_patch_contract.v0.1.yaml"
PACKET_PATH = OUTPUT_DIR / "semantic_metadata_delta_review_packet.v0.1.yaml"
RESULT_PATH = OUTPUT_DIR / "semantic_metadata_patch_result.v0.1.yaml"
REPORT_PATH = Path("ci/reports/p7d_clean_120_semantic_metadata_patch_report.v0.1.json")

ROLE_PATCH_IDS = {
    "P7D40-REPAIR-012",
    "P7D40-REPAIR-071",
    "P7D40-REPAIR-226",
    "P7D40-REPAIR-312",
    "RV80-ASSET-077",
}
ANCHOR_PATCH_IDS = {
    "P7D40-REPAIR-298",
    "RV80-ASSET-024",
    "RV80-ASSET-036",
    "RV80-ASSET-042",
    "RV80-ASSET-051",
    "RV80-ASSET-063",
    "RV80-ASSET-073",
    "RV80-ASSET-074",
}
EMPTY_HUMAN_ACTION_IDS = {
    "P7D40-REPAIR-012",
    "P7D40-REPAIR-162",
    "P7D40-REPAIR-276",
    "P7D40-REPAIR-287",
    "P7D40-REPAIR-298",
    "RV80-ASSET-074",
}
FOLLOW_UP_IDS = {
    "P7D40-REPAIR-234",
    "RV80-ASSET-015",
    "RV80-ASSET-049",
    "RV80-ASSET-059",
}

ALLOWED_ANCHOR_TYPES = {
    "apparel_item",
    "apparel_detail",
    "material_or_craft",
    "space_or_display",
    "prop",
    "styling_or_selection_task",
}
ALLOWED_ANCHOR_ROLES = {
    "primary_focus",
    "secondary_focus",
    "scene_context",
    "detail_evidence",
    "execution_prop",
}
ALLOWED_DERIVATION_MODES = {
    "extractive",
    "minimally_normalized",
    "faithful_composite",
}
ALLOWED_ASSET_TYPES = {
    "action_scene_kernel",
    "strategy_rule_expression",
    "evidence_boundary_expression",
    "product_role_expression",
    "platform_execution_expression",
}
READINESS_KEYS = {
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "Serving_ready",
    "generation_allowed",
    "generation_eligible",
    "production_ready",
    "production_servable",
    "release_ready",
}

TARGET_PRIMARY_VALUES: dict[str, Any] = {
    "RV80-ASSET-024": "深蓝牛仔裤",
    "RV80-ASSET-036": "雾蓝裙",
    "RV80-ASSET-042": "牛仔裤",
    "RV80-ASSET-051": "入口—中岛—端架 / 门店陈列分区",
    "RV80-ASSET-063": "酒红半裙",
    "RV80-ASSET-073": "外搭选择",
    "RV80-ASSET-074": ["直筒西装裤", "针织背心"],
    "P7D40-REPAIR-298": "背带裤",
}
TARGET_PRIMARY_TYPES: dict[str, Any] = {
    "RV80-ASSET-024": ["apparel_item"],
    "RV80-ASSET-036": ["apparel_item"],
    "RV80-ASSET-042": ["apparel_item"],
    "RV80-ASSET-051": ["space_or_display"],
    "RV80-ASSET-063": ["apparel_item"],
    "RV80-ASSET-073": ["styling_or_selection_task"],
    "RV80-ASSET-074": ["apparel_item", "apparel_item"],
    "P7D40-REPAIR-298": ["apparel_item"],
}


def add_error(
    errors: list[dict[str, str]], code: str, asset_id: str, detail: str
) -> None:
    errors.append({"code": code, "asset_id": asset_id, "detail": detail})


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"JSONL row is not an object: {path}:{line_number}")
        records.append(value)
    return records


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


def expected_headcount(entities: list[dict[str, Any]], flag: str) -> int:
    active = [entity for entity in entities if entity.get(flag) is True]
    explicit = sum(
        int(entity.get("minimum_human_count", 0))
        for entity in active
        if entity.get("entity_kind") == "human"
    )
    collective = max(
        [
            int(entity.get("minimum_human_count", 0))
            for entity in active
            if entity.get("entity_kind") == "abstract_group"
        ]
        or [0]
    )
    return max(explicit, collective)


def role_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "role_entities": record.get("role_entities"),
        "role_mentions": record.get("role_mentions"),
        "action_bindings": record.get("action_bindings"),
        "execution_card": record.get("execution_card"),
        "rhetorical_object_references": record.get("rhetorical_object_references"),
        "human_subject": record.get("expression_content_kernel_candidate", {}).get(
            "human_subject"
        ),
    }


def immutable_record_view(record: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(record)
    for key in (
        "role_entities",
        "role_mentions",
        "action_bindings",
        "execution_card",
        "rhetorical_object_references",
    ):
        value.pop(key, None)
    expression = value.get("expression_content_kernel_candidate")
    if isinstance(expression, dict):
        expression.pop("typed_anchors", None)
        expression.pop("object_anchor", None)
        expression.pop("expression_asset_type", None)
    return value


def primary_anchors(record: dict[str, Any]) -> list[dict[str, Any]]:
    expression = record.get("expression_content_kernel_candidate", {})
    anchors = expression.get("typed_anchors", [])
    if not isinstance(anchors, list):
        return []
    return [
        anchor
        for anchor in anchors
        if isinstance(anchor, dict) and anchor.get("anchor_role") == "primary_focus"
    ]


def validate_role_structure(
    records: list[dict[str, Any]], errors: list[dict[str, str]]
) -> None:
    for record in records:
        asset_id = str(record.get("asset_id", "GLOBAL"))
        body = record.get("body_text")
        entities_value = record.get("role_entities")
        mentions = record.get("role_mentions")
        bindings = record.get("action_bindings")
        card = record.get("execution_card")
        if (
            not isinstance(body, str)
            or not isinstance(entities_value, list)
            or not isinstance(mentions, list)
            or not isinstance(bindings, list)
            or not isinstance(card, dict)
        ):
            add_error(errors, "E_ROLE_STRUCTURE", asset_id, "invalid role subtree")
            continue
        entities = {
            entity.get("entity_id"): entity
            for entity in entities_value
            if isinstance(entity, dict)
        }
        if len(entities) != len(entities_value) or None in entities:
            add_error(errors, "E_ROLE_ENTITY_ID", asset_id, "entity IDs drift")
        for mention in mentions:
            if not isinstance(mention, dict):
                add_error(errors, "E_ROLE_MENTION", asset_id, "non-object mention")
                continue
            if not exact_span(body, mention.get("body_span")):
                add_error(
                    errors,
                    "E_ROLE_MENTION_SPAN",
                    asset_id,
                    str(mention.get("mention_id")),
                )
            if mention.get("referent_id") not in entities:
                add_error(
                    errors,
                    "E_ROLE_REFERENT",
                    asset_id,
                    str(mention.get("mention_id")),
                )
        for binding in bindings:
            if not isinstance(binding, dict):
                add_error(errors, "E_ACTION_BINDING", asset_id, "non-object binding")
                continue
            if binding.get("actor_ref") not in entities:
                add_error(
                    errors,
                    "E_ACTION_ACTOR_REF",
                    asset_id,
                    str(binding.get("action_id")),
                )
            for key in (
                "actor_evidence_span",
                "action_evidence_span",
                "object_evidence_span",
            ):
                if not exact_span(body, binding.get(key)):
                    add_error(
                        errors,
                        "E_ACTION_EVIDENCE",
                        asset_id,
                        f"{binding.get('action_id')}:{key}",
                    )
        for flag, refs_key, count_key in (
            (
                "counts_as_event_human",
                "event_human_entity_refs",
                "event_required_people_min",
            ),
            (
                "counts_as_capture_human",
                "capture_human_entity_refs",
                "capture_required_people_min",
            ),
        ):
            refs = card.get(refs_key)
            if not isinstance(refs, list) or any(ref not in entities for ref in refs):
                add_error(errors, "E_HEADCOUNT_REFS", asset_id, refs_key)
                continue
            expected_refs = {
                entity_id
                for entity_id, entity in entities.items()
                if entity.get(flag) is True
            }
            if set(refs) != expected_refs:
                add_error(errors, "E_HEADCOUNT_REF_SET", asset_id, refs_key)
            if card.get(count_key) != expected_headcount(entities_value, flag):
                add_error(errors, "E_HEADCOUNT_VALUE", asset_id, count_key)


def validate_role_patch_semantics(
    current: dict[str, dict[str, Any]],
    parent: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    record = current["P7D40-REPAIR-012"]
    mention = next(
        (
            item
            for item in record["role_mentions"]
            if item.get("mention_text") == "有人"
        ),
        None,
    )
    entities = {item["entity_id"]: item for item in record["role_entities"]}
    entity = entities.get(mention.get("referent_id")) if mention else None
    if (
        not mention
        or not entity
        or entity.get("canonical_role")
        not in {"indefinite_workflow_participant", "hypothetical_staff_member"}
        or entity.get("entity_kind") != "human"
        or entity.get("counts_as_event_human") is not False
        or entity.get("counts_as_capture_human") is not False
        or "audience" in str(entity.get("canonical_role"))
        or mention.get("referent_id")
        in record["execution_card"].get("audience_entity_refs", [])
    ):
        add_error(errors, "E_ROLE_012_REFERENT", record["asset_id"], "有人")

    record = current["P7D40-REPAIR-071"]
    aliases = [
        item
        for item in record["role_mentions"]
        if item.get("mention_text") in {"谁", "每个人"}
    ]
    entities = {item["entity_id"]: item for item in record["role_entities"]}
    alias_refs = {item.get("referent_id") for item in aliases}
    alias_entity = (
        entities.get(next(iter(alias_refs))) if len(alias_refs) == 1 else None
    )
    expected_members = {
        "ROLE-01-buyer",
        "ROLE-02-sales_associate",
        "ROLE-04-visual_merchandiser",
    }
    if (
        len(aliases) != 2
        or not alias_entity
        or alias_entity.get("canonical_role") != "participant_collective_alias"
        or set(alias_entity.get("member_entity_refs", [])) != expected_members
        or alias_entity.get("creates_additional_person") is not False
        or alias_entity.get("counts_as_event_human") is not False
        or record["execution_card"].get("event_required_people_min") != 3
    ):
        add_error(errors, "E_ROLE_071_COLLECTIVE", record["asset_id"], "alias")

    record = current["P7D40-REPAIR-226"]
    aliases = sorted(
        [
            item
            for item in record["role_mentions"]
            if item.get("mention_text") == "有人"
        ],
        key=lambda item: item["body_span"]["start"],
    )
    entities = {item["entity_id"]: item for item in record["role_entities"]}
    roles = [
        entities.get(item.get("referent_id"), {}).get("canonical_role")
        for item in aliases
    ]
    alias_starts = {item["body_span"]["start"] for item in aliases}
    bound_starts = {
        item["actor_evidence_span"]["start"]
        for item in record["action_bindings"]
        if item.get("actor_evidence_span", {}).get("start") in alias_starts
        and item.get("action_polarity") == "hypothetical"
        and item.get("portrayed_as_actual_action") is False
    }
    if (
        len(aliases) != 2
        or roles != ["customer", "sales_associate"]
        or len({item.get("referent_id") for item in aliases}) != 2
        or bound_starts != alias_starts
    ):
        add_error(errors, "E_ROLE_226_DISTINCT", record["asset_id"], repr(roles))

    for asset_id in ("RV80-ASSET-077", "P7D40-REPAIR-312"):
        record = current[asset_id]
        rhetorical = record.get("rhetorical_object_references")
        body_who_count = record["body_text"].count("谁")
        anchor_ids = {
            item.get("anchor_id")
            for item in record["expression_content_kernel_candidate"].get(
                "typed_anchors", []
            )
        }
        human_who = [
            item for item in record["role_mentions"] if item.get("mention_text") == "谁"
        ]
        binding_who = [
            item
            for item in record["action_bindings"]
            if item.get("actor_evidence_span", {}).get("text") == "谁"
        ]
        if (
            not isinstance(rhetorical, list)
            or len(rhetorical) != body_who_count
            or human_who
            or binding_who
            or any(
                not exact_span(record["body_text"], item.get("body_span"))
                or item.get("referent_anchor_id") not in anchor_ids
                or item.get("semantic_function") != "rhetorical_object_reference"
                for item in rhetorical
            )
        ):
            add_error(errors, "E_RHETORICAL_OBJECT_GRAPH", asset_id, "谁")

    for asset_id in ROLE_PATCH_IDS:
        before_card = parent[asset_id]["execution_card"]
        after_card = current[asset_id]["execution_card"]
        for key in ("event_required_people_min", "capture_required_people_min"):
            if after_card.get(key) != before_card.get(key):
                add_error(errors, "E_DEPENDENT_HEADCOUNT_DRIFT", asset_id, key)


def validate_anchors(
    records: list[dict[str, Any]],
    current: dict[str, dict[str, Any]],
    parent: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> tuple[set[str], int]:
    semantic_changes: set[str] = set()
    projection_mismatch_count = 0
    for record in records:
        asset_id = record["asset_id"]
        body = record["body_text"]
        expression = record["expression_content_kernel_candidate"]
        anchors = expression.get("typed_anchors")
        projection = expression.get("object_anchor")
        if not isinstance(anchors, list) or not anchors:
            add_error(errors, "E_TYPED_ANCHOR_COVERAGE", asset_id, "missing")
            continue
        anchor_ids = [
            item.get("anchor_id") for item in anchors if isinstance(item, dict)
        ]
        if len(anchor_ids) != len(anchors) or len(set(anchor_ids)) != len(anchor_ids):
            add_error(errors, "E_ANCHOR_ID", asset_id, "missing or duplicate")
        for anchor in anchors:
            if not isinstance(anchor, dict):
                add_error(errors, "E_ANCHOR_SHAPE", asset_id, "non-object")
                continue
            if anchor.get("anchor_type") not in ALLOWED_ANCHOR_TYPES:
                add_error(
                    errors, "E_ANCHOR_TYPE", asset_id, str(anchor.get("anchor_type"))
                )
            if anchor.get("anchor_role") not in ALLOWED_ANCHOR_ROLES:
                add_error(
                    errors, "E_ANCHOR_ROLE", asset_id, str(anchor.get("anchor_role"))
                )
            if anchor.get("derivation_mode") not in ALLOWED_DERIVATION_MODES:
                add_error(
                    errors,
                    "E_ANCHOR_DERIVATION",
                    asset_id,
                    str(anchor.get("derivation_mode")),
                )
            if not isinstance(anchor.get("canonical_label"), str) or not anchor.get(
                "canonical_label"
            ):
                add_error(
                    errors, "E_ANCHOR_LABEL", asset_id, str(anchor.get("anchor_id"))
                )
            surface_forms = anchor.get("surface_forms")
            evidence_spans = anchor.get("evidence_spans")
            if (
                not isinstance(surface_forms, list)
                or not surface_forms
                or any(
                    not isinstance(item, str) or item not in body
                    for item in surface_forms
                )
                or not isinstance(evidence_spans, list)
                or not evidence_spans
                or any(not exact_span(body, span) for span in evidence_spans)
            ):
                add_error(
                    errors, "E_ANCHOR_EVIDENCE", asset_id, str(anchor.get("anchor_id"))
                )

        primaries = [
            item for item in anchors if item.get("anchor_role") == "primary_focus"
        ]
        ordered = sorted(primaries, key=lambda item: item["evidence_spans"][0]["start"])
        if not ordered:
            expected_value: Any = None
        elif len(ordered) == 1:
            expected_value = ordered[0]["canonical_label"]
        else:
            expected_value = [item["canonical_label"] for item in ordered]
        expected_ids = [item["anchor_id"] for item in ordered]
        if (
            not isinstance(projection, dict)
            or projection.get("status") != "DERIVED_COMPATIBILITY_PROJECTION"
            or projection.get("value") != expected_value
            or projection.get("derived_from_anchor_ids") != expected_ids
        ):
            projection_mismatch_count += 1
            add_error(errors, "E_LEGACY_PROJECTION", asset_id, repr(expected_value))

        old_value = parent[asset_id]["expression_content_kernel_candidate"][
            "object_anchor"
        ]
        if expected_value != old_value:
            semantic_changes.add(asset_id)
        if asset_id not in ANCHOR_PATCH_IDS and expected_value != old_value:
            add_error(
                errors, "E_UNAUTHORIZED_ANCHOR_CHANGE", asset_id, repr(expected_value)
            )

    if semantic_changes != ANCHOR_PATCH_IDS:
        add_error(
            errors,
            "E_ANCHOR_PATCH_SET",
            "GLOBAL",
            repr(sorted(semantic_changes)),
        )

    for asset_id, expected_value in TARGET_PRIMARY_VALUES.items():
        record = current[asset_id]
        expression = record["expression_content_kernel_candidate"]
        primary = sorted(
            primary_anchors(record),
            key=lambda item: item["evidence_spans"][0]["start"],
        )
        if (
            expression["object_anchor"].get("value") != expected_value
            or [item.get("anchor_type") for item in primary]
            != TARGET_PRIMARY_TYPES[asset_id]
        ):
            add_error(errors, "E_REQUIRED_ANCHOR", asset_id, repr(expected_value))
    contexts = {
        "RV80-ASSET-036": ("人台", "prop"),
        "RV80-ASSET-063": ("橱窗", "space_or_display"),
    }
    for asset_id, (label, anchor_type) in contexts.items():
        contexts_found = [
            item
            for item in current[asset_id]["expression_content_kernel_candidate"][
                "typed_anchors"
            ]
            if item.get("anchor_role") == "scene_context"
            and item.get("canonical_label") == label
            and item.get("anchor_type") == anchor_type
        ]
        if len(contexts_found) != 1:
            add_error(errors, "E_REQUIRED_CONTEXT_ANCHOR", asset_id, label)
    return semantic_changes, projection_mismatch_count


def validate_asset_types(
    records: list[dict[str, Any]], errors: list[dict[str, str]]
) -> tuple[set[str], Counter[str]]:
    empty_ids: set[str] = set()
    distribution: Counter[str] = Counter()
    for record in records:
        asset_id = record["asset_id"]
        body = record["body_text"]
        expression = record["expression_content_kernel_candidate"]
        type_value = expression.get("expression_asset_type")
        if not isinstance(type_value, dict):
            add_error(errors, "E_ASSET_TYPE", asset_id, "missing")
            continue
        primary_type = type_value.get("primary_type")
        distribution[str(primary_type)] += 1
        if primary_type not in ALLOWED_ASSET_TYPES:
            add_error(errors, "E_ASSET_TYPE", asset_id, str(primary_type))
        spans = type_value.get("evidence_spans")
        if (
            not isinstance(spans, list)
            or not spans
            or any(not exact_span(body, span) for span in spans)
        ):
            add_error(errors, "E_ASSET_TYPE_EVIDENCE", asset_id, str(primary_type))

        human = expression.get("human_subject")
        action = expression.get("observable_action")
        if not human and not action:
            empty_ids.add(asset_id)
        if primary_type == "action_scene_kernel" and (
            not isinstance(human, list) or not human or not action
        ):
            add_error(errors, "E_ACTION_SCENE_REQUIREMENT", asset_id, "human/action")
        if primary_type == "strategy_rule_expression" and not expression.get(
            "business_judgment"
        ):
            add_error(errors, "E_STRATEGY_REQUIREMENT", asset_id, "business_judgment")
        if primary_type == "evidence_boundary_expression" and not (
            expression.get("claim_surface")
            or record.get("claim_event_boundary", {}).get("claim_body_span")
        ):
            add_error(errors, "E_EVIDENCE_REQUIREMENT", asset_id, "claim boundary")
        if primary_type == "product_role_expression":
            primary = primary_anchors(record)
            allowed = {"apparel_item", "styling_or_selection_task"}
            if (
                not primary
                or any(item.get("anchor_type") not in allowed for item in primary)
                or not expression.get("business_judgment")
            ):
                add_error(
                    errors, "E_PRODUCT_ROLE_REQUIREMENT", asset_id, "anchor/judgment"
                )
        if primary_type == "platform_execution_expression" and not expression.get(
            "spoken_seed"
        ):
            add_error(errors, "E_PLATFORM_REQUIREMENT", asset_id, "spoken_seed")

    if empty_ids != EMPTY_HUMAN_ACTION_IDS:
        add_error(errors, "E_EMPTY_HUMAN_ACTION_SET", "GLOBAL", repr(sorted(empty_ids)))
    for asset_id in EMPTY_HUMAN_ACTION_IDS:
        primary_type = records_by_id(records)[asset_id][
            "expression_content_kernel_candidate"
        ]["expression_asset_type"]["primary_type"]
        if primary_type == "action_scene_kernel":
            add_error(errors, "E_EMPTY_ACTION_SCENE", asset_id, primary_type)
    if set(distribution) != ALLOWED_ASSET_TYPES:
        add_error(errors, "E_ASSET_TYPE_COVERAGE", "GLOBAL", repr(distribution))
    return empty_ids, distribution


def records_by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record["asset_id"]: record for record in records}


def validate_data(
    records: list[dict[str, Any]],
    parent_records: list[dict[str, Any]],
    contract: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    errors: list[dict[str, str]] = []
    current = records_by_id(records)
    parent = records_by_id(parent_records)
    if len(records) != 120 or len(current) != 120:
        add_error(errors, "E_ASSET_COUNT", "GLOBAL", str(len(records)))
    if len(parent_records) != 120 or set(current) != set(parent):
        add_error(errors, "E_ASSET_DENOMINATOR", "GLOBAL", "parent mismatch")
        return errors, {}
    if len({record.get("kernel_id") for record in records}) != 120:
        add_error(errors, "E_KERNEL_COUNT", "GLOBAL", "kernel IDs")

    role_changes: set[str] = set()
    headcount_changes: list[str] = []
    immutable_count = 0
    source_match_count = 0
    body_match_count = 0
    for asset_id, record in current.items():
        old = parent[asset_id]
        if record.get("body_text") == old.get("body_text"):
            body_match_count += 1
        else:
            add_error(errors, "E_BODY_CHANGED", asset_id, "/body_text")
        if record.get("source_knowledge_kernel_ref") == old.get(
            "source_knowledge_kernel_ref"
        ):
            source_match_count += 1
        else:
            add_error(
                errors,
                "E_SOURCE_KERNEL_CHANGED",
                asset_id,
                "/source_knowledge_kernel_ref",
            )
        if immutable_record_view(record) == immutable_record_view(old):
            immutable_count += 1
        else:
            add_error(errors, "E_UNEXPECTED_DIFF", asset_id, "outside allowed metadata")
        if role_view(record) != role_view(old):
            role_changes.add(asset_id)
        for key in ("event_required_people_min", "capture_required_people_min"):
            if record["execution_card"].get(key) != old["execution_card"].get(key):
                headcount_changes.append(f"{asset_id}:{key}")
        if record.get("knowledge_count_increment") != 0:
            add_error(errors, "E_KNOWLEDGE_INCREMENT", asset_id, "nonzero")
        if record.get("counts_toward_600_or_3600") is not False:
            add_error(errors, "E_SCALE_COUNTING", asset_id, "counted")
        if record.get("accepted_domain_knowledge") is not False:
            add_error(errors, "E_ACCEPTED_DOMAIN", asset_id, "true")
        if record.get("candidatepack_ready") is not False:
            add_error(errors, "E_CANDIDATEPACK_READY", asset_id, "true")
        if record.get("production_servable") is not False:
            add_error(errors, "E_PRODUCTION_SERVABLE", asset_id, "true")
        readiness = record.get("readiness_flags")
        if not isinstance(readiness, dict) or any(
            readiness.get(key) is not False for key in READINESS_KEYS
        ):
            add_error(errors, "E_READINESS", asset_id, "flag drift")

    if role_changes != ROLE_PATCH_IDS:
        add_error(errors, "E_ROLE_PATCH_SET", "GLOBAL", repr(sorted(role_changes)))
    if headcount_changes:
        add_error(errors, "E_HEADCOUNT_CHANGED", "GLOBAL", repr(headcount_changes))

    validate_role_structure(records, errors)
    validate_role_patch_semantics(current, parent, errors)
    anchor_changes, projection_mismatch_count = validate_anchors(
        records, current, parent, errors
    )
    empty_ids, distribution = validate_asset_types(records, errors)

    contract_scope = contract.get("scope")
    expected_scope = {
        "body_change_count": 0,
        "source_kernel_change_count": 0,
        "role_patch_ids": sorted(ROLE_PATCH_IDS),
        "anchor_patch_ids": sorted(ANCHOR_PATCH_IDS),
        "typed_anchor_asset_coverage": 120,
        "expression_asset_type_count": 120,
        "knowledge_count_increment": 0,
        "content_generation_count": 0,
    }
    if contract_scope != expected_scope:
        add_error(errors, "E_CONTRACT_SCOPE", "GLOBAL", "scope mismatch")
    if contract.get("machine_semantics_scope") != MACHINE_SCOPE:
        add_error(errors, "E_MACHINE_SCOPE", "GLOBAL", "overclaim")
    follow_up = contract.get("follow_up_anchor_policy", {})
    follow_up_items = follow_up.get("items", [])
    if (
        {item.get("asset_id") for item in follow_up_items} != FOLLOW_UP_IDS
        or any(
            item.get("patched_by_this_task") is not False for item in follow_up_items
        )
        or follow_up.get("founder_final_acceptance_remains_pending") is not True
    ):
        add_error(errors, "E_FOLLOW_UP_SCOPE", "GLOBAL", "founder cases")
    acceptance = contract.get("acceptance", {})
    if (
        acceptance.get("success_status") != SUCCESS_STATUS
        or acceptance.get("clean_120_final_acceptance") is not False
        or acceptance.get("reference_corpus_frozen") is not False
        or acceptance.get("runtime_content_kernel_ready") is not False
    ):
        add_error(errors, "E_ACCEPTANCE_BOUNDARY", "GLOBAL", "overclaim")
    scale = contract.get("scale_and_downstream", {})
    if (
        scale.get("expand_600") is not False
        or scale.get("expand_3600") is not False
        or scale.get("readiness_all_false") is not True
        or any(
            scale.get(key) != "BLOCKED"
            for key in ("CandidatePack", "KE", "Serving", "RAG", "DIFY", "production")
        )
    ):
        add_error(errors, "E_SCALE_DOWNSTREAM", "GLOBAL", "unlocked")

    metrics = {
        "asset_count": len(records),
        "unique_kernel_count": len({record.get("kernel_id") for record in records}),
        "body_digest_match_count": body_match_count,
        "source_kernel_digest_match_count": source_match_count,
        "other_expression_field_unchanged_count": immutable_count,
        "role_patch_count": len(role_changes),
        "role_patch_ids": sorted(role_changes),
        "dependent_headcount_change_count": len(headcount_changes),
        "anchor_semantic_patch_count": len(anchor_changes),
        "anchor_patch_ids": sorted(anchor_changes),
        "typed_anchor_asset_coverage": sum(
            bool(record["expression_content_kernel_candidate"].get("typed_anchors"))
            for record in records
        ),
        "legacy_projection_mismatch_count": projection_mismatch_count,
        "expression_asset_type_count": sum(
            isinstance(
                record["expression_content_kernel_candidate"].get(
                    "expression_asset_type"
                ),
                dict,
            )
            for record in records
        ),
        "expression_asset_type_distribution": dict(sorted(distribution.items())),
        "empty_human_action_exception_count": len(empty_ids),
        "knowledge_count_increment": sum(
            int(record.get("knowledge_count_increment", 0)) for record in records
        ),
    }
    return errors, metrics


def validate_supporting_artifacts(
    records: list[dict[str, Any]],
    packet: dict[str, Any],
    result: dict[str, Any],
    metrics: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    packet_root = packet.get("semantic_metadata_delta_review_packet", {})
    if packet_root.get("machine_limit", {}).get("status") != MACHINE_SCOPE:
        add_error(errors, "E_PACKET_MACHINE_SCOPE", "GLOBAL", "overclaim")
    if {
        item.get("asset_id") for item in packet_root.get("role_patch_items", [])
    } != ROLE_PATCH_IDS:
        add_error(errors, "E_PACKET_ROLE_SET", "GLOBAL", "role delta")
    if {
        item.get("asset_id") for item in packet_root.get("anchor_patch_items", [])
    } != ANCHOR_PATCH_IDS:
        add_error(errors, "E_PACKET_ANCHOR_SET", "GLOBAL", "anchor delta")
    identity_items = packet_root.get("identity_anchor_migration_items", [])
    if (
        len(identity_items) != 112
        or any(item.get("identity_preserved") is not True for item in identity_items)
        or {item.get("asset_id") for item in identity_items}
        != {record["asset_id"] for record in records} - ANCHOR_PATCH_IDS
    ):
        add_error(errors, "E_PACKET_IDENTITY", "GLOBAL", "112 migration")
    follow_up = packet_root.get("unresolved_founder_anchor_policy_follow_up", [])
    if {item.get("asset_id") for item in follow_up} != FOLLOW_UP_IDS or any(
        item.get("patched_by_this_task") is not False for item in follow_up
    ):
        add_error(errors, "E_PACKET_FOLLOW_UP", "GLOBAL", "follow-up drift")

    result_root = result.get("semantic_metadata_patch_result", {})
    if result_root.get("result_status") != SUCCESS_STATUS:
        add_error(errors, "E_RESULT_STATUS", "GLOBAL", "not pending review")
    if result_root.get("machine_semantics_scope") != MACHINE_SCOPE:
        add_error(errors, "E_RESULT_SCOPE", "GLOBAL", "overclaim")
    guardian = result_root.get("guardian_and_founder", {})
    if (
        guardian.get("claude_code_delta_guardian_review") != "PENDING"
        or guardian.get("founder_final_acceptance") is not False
    ):
        add_error(errors, "E_RESULT_REVIEW", "GLOBAL", "premature acceptance")
    if result_root.get("scale") != {"expand_600": False, "expand_3600": False}:
        add_error(errors, "E_RESULT_SCALE", "GLOBAL", "scale drift")
    if result_root.get("downstream_and_readiness", {}).get("all_false") is not True:
        add_error(errors, "E_RESULT_READINESS", "GLOBAL", "readiness drift")
    result_metrics = result_root.get("machine_acceptance", {})
    expected_metrics = {
        "asset_count": 120,
        "unique_kernel_count": 120,
        "knowledge_count_increment": 0,
        "body_change_count": 0,
        "body_digest_match_count": 120,
        "source_kernel_digest_match_count": 120,
        "source_kernel_mutation_count": 0,
        "role_patch_count": 5,
        "role_patch_ids": sorted(ROLE_PATCH_IDS),
        "role_subtree_change_outside_5_count": 0,
        "collapsed_distinct_referent_count": 0,
        "rhetorical_object_in_human_graph_count": 0,
        "nonactual_role_in_actual_headcount_count": 0,
        "dependent_headcount_change_count": 0,
        "expression_asset_type_count": 120,
        "expression_asset_type_distribution": metrics[
            "expression_asset_type_distribution"
        ],
        "invalid_expression_asset_type_count": 0,
        "type_evidence_missing_count": 0,
        "type_requirement_failure_count": 0,
        "empty_human_action_ids": sorted(EMPTY_HUMAN_ACTION_IDS),
        "invented_human_or_action_count": 0,
        "typed_anchor_asset_coverage": 120,
        "anchor_semantic_patch_count": 8,
        "anchor_patch_ids": sorted(ANCHOR_PATCH_IDS),
        "required_8_anchor_pass_count": 8,
        "unauthorized_anchor_semantic_change_count": 0,
        "unsupported_anchor_count": 0,
        "anchor_evidence_missing_count": 0,
        "legacy_projection_mismatch_count": 0,
        "other_expression_kernel_field_change_count": 0,
    }
    if result_metrics != expected_metrics:
        add_error(errors, "E_RESULT_METRICS", "GLOBAL", "derived metrics drift")
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


def validate_git_surface(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    allowed_prefixes = (
        OUTPUT_DIR.as_posix() + "/",
        "ci/fixtures/p7d_clean_120_semantic_metadata_patch/",
    )
    allowed_exact = {
        "ci/checkers/check_p7d_clean_120_semantic_metadata_patch.py",
        REPORT_PATH.as_posix(),
        "docs/reports/p7d_clean_120_semantic_metadata_patch_report.md",
        "docs/reports/p7d_clean_120_semantic_metadata_patch_receipt.json",
        "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
        "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    }
    changed = set(git_output(root, "diff", "--name-only", BASELINE_HEAD).splitlines())
    for line in git_output(root, "status", "--porcelain=v1").splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.add(path)
    for path in sorted(changed):
        if path in allowed_exact or path.startswith(allowed_prefixes):
            continue
        add_error(errors, "E_WRITE_SURFACE", "GLOBAL", path)
    if PARENT_PATH.as_posix() in changed:
        add_error(errors, "E_PARENT_MODIFIED", "GLOBAL", PARENT_PATH.as_posix())
    return errors


def validate_ledger(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    yaml_path = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
    current = load_yaml_mapping(root / yaml_path)
    baseline = yaml.safe_load(
        git_output(root, "show", f"{BASELINE_HEAD}:{yaml_path.as_posix()}")
    )
    current_root = current.get("grc_3600_execution_plan_status", {})
    baseline_root = baseline.get("grc_3600_execution_plan_status", {})
    migration = current_root.get("route_migration_16")
    if not isinstance(migration, dict):
        add_error(errors, "E_ROUTE_MIGRATION_16", "GLOBAL", "absent")
        return errors
    without_migration = copy.deepcopy(current_root)
    without_migration.pop("route_migration_16", None)
    if without_migration != baseline_root:
        add_error(errors, "E_LEDGER_NON_ADDITIVE", "GLOBAL", "outside migration16")
    current_task = migration.get("current_task", {})
    if current_task.get("task_id") != TASK_ID:
        add_error(errors, "E_ROUTE_TASK", "GLOBAL", "task ID")
    expected_scope = {
        "body_change_count": 0,
        "role_semantic_patch_assets": 5,
        "expression_anchor_patch_assets": 8,
        "expression_asset_type_count": 120,
        "source_kernel_change_count": 0,
        "knowledge_count_increment": 0,
    }
    if current_task.get("scope") != expected_scope:
        add_error(errors, "E_ROUTE_SCOPE", "GLOBAL", "scope")
    if (
        migration.get("next_if_guardian_delta_pass")
        != "FOUNDER_P7D_CLEAN_120_FINAL_ACCEPTANCE"
    ):
        add_error(errors, "E_ROUTE_NEXT", "GLOBAL", "next")
    if migration.get("scale") != {"expand_600": False, "expand_3600": False}:
        add_error(errors, "E_ROUTE_SCALE", "GLOBAL", "scale")
    if migration.get("downstream_and_readiness") != {"all_false": True}:
        add_error(errors, "E_ROUTE_READINESS", "GLOBAL", "readiness")

    md_path = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.md")
    current_md = (root / md_path).read_text(encoding="utf-8")
    baseline_md = git_output(root, "show", f"{BASELINE_HEAD}:{md_path.as_posix()}")
    if not current_md.startswith(baseline_md):
        add_error(errors, "E_LEDGER_MD_NON_ADDITIVE", "GLOBAL", "not append-only")
    if (
        "## P7D Clean-120 Metadata Precision Patch"
        not in current_md[len(baseline_md) :]
    ):
        add_error(errors, "E_LEDGER_MD_SECTION", "GLOBAL", "summary absent")
    return errors


def load_bundle(
    root: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    records = load_jsonl(root / MANIFEST_PATH)
    parent = load_jsonl(root / PARENT_PATH)
    contract_raw = load_yaml_mapping(root / CONTRACT_PATH)
    packet = load_yaml_mapping(root / PACKET_PATH)
    result = load_yaml_mapping(root / RESULT_PATH)
    contract = contract_raw.get("semantic_metadata_patch_contract")
    if not isinstance(contract, dict):
        raise TypeError("semantic metadata contract root is absent")
    return records, parent, contract, packet, result


def run_live(
    root: Path, write_report: bool
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    records, parent, contract, packet, result = load_bundle(root)
    errors, metrics = validate_data(records, parent, contract)
    errors.extend(validate_supporting_artifacts(records, packet, result, metrics))
    errors.extend(validate_ledger(root))
    errors.extend(validate_git_surface(root))
    report = {
        "task_id": TASK_ID,
        "checker_status": "PASS" if not errors else "FAIL",
        "machine_semantics_scope": MACHINE_SCOPE,
        "error_count": len(errors),
        "errors": errors,
        "metrics": metrics,
        "result_status": SUCCESS_STATUS
        if not errors
        else "METADATA_PRECISION_PATCH_BLOCKED",
    }
    if write_report:
        path = root / REPORT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return errors, report


Mutator = Callable[[list[dict[str, Any]], dict[str, Any]], None]


def run_selftest(root: Path) -> dict[str, Any]:
    records, parent, contract, _, _ = load_bundle(root)
    positive_errors, _ = validate_data(records, parent, contract)
    cases: list[tuple[str, Mutator]] = []

    def add_case(name: str, mutator: Mutator) -> None:
        cases.append((name, mutator))

    def row(rows: list[dict[str, Any]], asset_id: str) -> dict[str, Any]:
        return next(item for item in rows if item["asset_id"] == asset_id)

    def role_012_audience(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        target = row(rows, "P7D40-REPAIR-012")
        entity = next(
            item
            for item in target["role_entities"]
            if item["canonical_role"] == "indefinite_workflow_participant"
        )
        entity["canonical_role"] = "audience_member"
        entity["entity_kind"] = "audience"

    add_case("role_012_someone_as_audience", role_012_audience)

    def role_071_fourth(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        target = row(rows, "P7D40-REPAIR-071")
        entity = next(
            item
            for item in target["role_entities"]
            if item["canonical_role"] == "participant_collective_alias"
        )
        entity["creates_additional_person"] = True
        entity["counts_as_event_human"] = True
        entity["minimum_human_count"] = 1
        target["execution_card"]["event_human_entity_refs"].append(entity["entity_id"])
        target["execution_card"]["event_required_people_min"] = 4

    add_case("role_071_collective_creates_fourth", role_071_fourth)

    def role_226_collapsed(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        target = row(rows, "P7D40-REPAIR-226")
        aliases = [
            item for item in target["role_mentions"] if item["mention_text"] == "有人"
        ]
        aliases[1]["referent_id"] = aliases[0]["referent_id"]

    add_case("role_226_aliases_collapsed", role_226_collapsed)

    def role_226_actual(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        target = row(rows, "P7D40-REPAIR-226")
        binding = next(
            item
            for item in target["action_bindings"]
            if item["actor_evidence_span"]["start"] == 88
        )
        binding["action_polarity"] = "actual"
        binding["portrayed_as_actual_action"] = True

    add_case("role_226_hypothetical_counted_actual", role_226_actual)

    def rhetorical_to_human(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        target = row(rows, "RV80-ASSET-077")
        ref = target["rhetorical_object_references"][0]
        target["role_entities"].append(
            {
                "entity_id": "ROLE-X-audience",
                "canonical_role": "audience_member",
                "entity_kind": "audience",
                "minimum_human_count": 0,
                "present_in_portrayed_event": False,
                "visible_in_content": False,
                "counts_as_event_human": False,
                "counts_as_capture_human": False,
            }
        )
        target["role_mentions"].append(
            {
                "mention_id": "M-X",
                "mention_text": "谁",
                "body_span": copy.deepcopy(ref["body_span"]),
                "referent_id": "ROLE-X-audience",
                "classification_basis": "shape_only",
                "semantic_functions": ["hypothetical_role"],
            }
        )

    add_case("rhetorical_who_enters_human_graph", rhetorical_to_human)

    def set_primary(
        rows: list[dict[str, Any]], asset_id: str, value: Any, anchor_type: str
    ) -> None:
        target = row(rows, asset_id)
        expression = target["expression_content_kernel_candidate"]
        primary = primary_anchors(target)
        primary[0]["canonical_label"] = value if isinstance(value, str) else value[0]
        primary[0]["anchor_type"] = anchor_type
        if isinstance(value, list):
            expression["typed_anchors"] = [primary[0]]
            expression["object_anchor"]["value"] = value[:1]
            expression["object_anchor"]["derived_from_anchor_ids"] = [
                primary[0]["anchor_id"]
            ]
        else:
            expression["object_anchor"]["value"] = value

    add_case(
        "anchor_036_mannequin_primary",
        lambda rows, contract_: set_primary(rows, "RV80-ASSET-036", "人台", "prop"),
    )
    add_case(
        "anchor_051_sleeve_primary",
        lambda rows, contract_: set_primary(
            rows, "RV80-ASSET-051", "袖口", "apparel_detail"
        ),
    )
    add_case(
        "anchor_063_window_primary",
        lambda rows, contract_: set_primary(
            rows, "RV80-ASSET-063", "橱窗", "space_or_display"
        ),
    )
    add_case(
        "anchor_073_truncated_pants",
        lambda rows, contract_: set_primary(
            rows, "RV80-ASSET-073", "裤", "apparel_item"
        ),
    )
    add_case(
        "anchor_074_only_one_item",
        lambda rows, contract_: set_primary(
            rows, "RV80-ASSET-074", ["直筒西装裤"], "apparel_item"
        ),
    )

    def projection_drift(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        row(rows, "RV80-ASSET-001")["expression_content_kernel_candidate"][
            "object_anchor"
        ]["value"] = "错误投影"

    add_case("legacy_projection_mismatch", projection_drift)

    def anchor_span_drift(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        target = row(rows, "RV80-ASSET-001")
        target["expression_content_kernel_candidate"]["typed_anchors"][0][
            "evidence_spans"
        ][0]["text"] = "不存在"

    add_case("anchor_span_not_in_body", anchor_span_drift)

    def action_scene_missing(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        target = next(
            item
            for item in rows
            if item["expression_content_kernel_candidate"]["expression_asset_type"][
                "primary_type"
            ]
            == "action_scene_kernel"
        )
        target["expression_content_kernel_candidate"]["human_subject"] = []

    add_case("action_scene_missing_human", action_scene_missing)

    def seventh_empty(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        target = row(rows, "RV80-ASSET-001")
        expression = target["expression_content_kernel_candidate"]
        expression["human_subject"] = []
        expression["observable_action"] = ""
        expression["expression_asset_type"]["primary_type"] = "strategy_rule_expression"

    add_case("seventh_empty_human_action", seventh_empty)

    def invent_for_empty(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        target = row(rows, "P7D40-REPAIR-012")
        expression = target["expression_content_kernel_candidate"]
        expression["human_subject"] = ["invented_sales_associate"]
        expression["observable_action"] = "invented action"

    add_case("invent_person_action_for_empty", invent_for_empty)

    def body_change(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        row(rows, "RV80-ASSET-001")["body_text"] += "改动"

    add_case("body_changed", body_change)

    def source_change(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        row(rows, "RV80-ASSET-001")["source_knowledge_kernel_ref"]["source_sha256"] = (
            "0" * 64
        )

    add_case("source_kernel_changed", source_change)

    def readiness_true(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        row(rows, "RV80-ASSET-001")["readiness_flags"]["generation_allowed"] = True

    add_case("readiness_true", readiness_true)

    def unlock_scale(_rows: list[dict[str, Any]], mutable: dict[str, Any]) -> None:
        mutable["scale_and_downstream"]["expand_600"] = True
        mutable["scale_and_downstream"]["KE"] = "READY"

    add_case("scale_or_downstream_unlocked", unlock_scale)

    def unauthorized_anchor(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        target = row(rows, "RV80-ASSET-001")
        expression = target["expression_content_kernel_candidate"]
        expression["typed_anchors"][0]["canonical_label"] = "外套"
        expression["object_anchor"]["value"] = "外套"

    add_case("ninth_anchor_semantic_change", unauthorized_anchor)

    results: list[dict[str, Any]] = []
    for name, mutator in cases:
        mutable_records = copy.deepcopy(records)
        mutable_contract = copy.deepcopy(contract)
        mutator(mutable_records, mutable_contract)
        case_errors, _ = validate_data(mutable_records, parent, mutable_contract)
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
