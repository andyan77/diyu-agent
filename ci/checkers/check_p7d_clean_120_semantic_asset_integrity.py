#!/usr/bin/env python3
"""Fail-closed checker for the Clean-120 semantic asset closeout."""

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
from typing import Any

import yaml


TASK_ID = "GKB-P7D-CLEAN-120-SEMANTIC-ASSET-INTEGRITY-CLOSEOUT-001"
BASELINE_HEAD = "54e248032a815fa1fe7877cf913326cce5e6ff9e"
SUCCESS_STATUS = (
    "CLEAN_120_SEMANTIC_ASSET_REPAIR_EXECUTED_"
    "PENDING_CLAUDE_GUARDIAN_AND_FOUNDER_FINAL_ACCEPTANCE"
)
AUTHORIZED_BODY_IDS = {
    "RV80-ASSET-017",
    "RV80-ASSET-018",
    "RV80-ASSET-059",
    "RV80-ASSET-060",
    "P7D40-REPAIR-234",
    "P7D40-REPAIR-243",
}
REQUIRED_EXPRESSION_FIELDS = (
    "human_subject",
    "object_anchor",
    "observable_action",
    "scene",
    "business_judgment",
    "tension_or_question",
    "spoken_seed",
    "claim_surface",
    "event_surface",
)
READINESS_FLAGS = {
    "candidatepack_ready",
    "KE_ready",
    "Serving_ready",
    "RAG_ready",
    "DIFY_ready",
    "generation_allowed",
    "generation_eligible",
    "production_ready",
    "production_servable",
    "release_ready",
}
SEMANTIC_FUNCTIONS = {
    "narrator",
    "event_owner",
    "action_executor",
    "visible_participant",
    "audience_addressee",
    "hypothetical_role",
    "absent_or_prohibited_role",
    "quoted_or_referenced_role",
}
NON_ACTUAL_FUNCTIONS = {
    "audience_addressee",
    "hypothetical_role",
    "absent_or_prohibited_role",
    "quoted_or_referenced_role",
}
ROLE_TERMS = sorted(
    {
        "陈列负责人",
        "内容同事",
        "陈列同事",
        "品牌内容",
        "创始人",
        "经营者",
        "负责人",
        "店长",
        "导购",
        "买手",
        "陈列师",
        "搭配师",
        "版师",
        "店员",
        "同事",
        "团队",
        "实习生",
        "员工",
        "顾客",
        "观众",
        "真人模特",
        "模特",
        "人台",
        "人物",
        "熟客",
        "客户",
        "本人",
        "对方",
        "别人",
        "下一位同事",
        "下一位",
        "下个岗位",
        "每个岗位",
        "岗位",
        "三个人",
        "每个人",
        "任何人",
        "第一次看藏青羊毛西装外套的人",
        "熟悉这类外套的人",
        "懂版型的人",
        "试穿的人",
        "路过的人",
        "穿的人",
        "有人",
        "没人",
        "谁",
        "你",
    },
    key=len,
    reverse=True,
)
ROLE_SCAN_RE = re.compile(
    "|".join(re.escape(term) for term in ROLE_TERMS)
    + r"|我们|他们|我|她|(?<!其)他(?!们)"
)
BODY_METADATA_PATTERNS = (
    "手机固定",
    "现场只有",
    "不另找演员",
    "不需要谁扮演谁",
    "不计真人",
    "不计作真人",
    "一人完成",
    "三名当班员工",
    "四名当班同事",
    "谁负责拍摄",
    "hired performer",
    "required people",
)
BODY_REVIEW_LANGUAGE_PATTERNS = (
    "action_executor",
    "event_required_people_min",
    "capture_required_people_min",
    "counts_as_event_human",
    "mannequin_prop",
    "审计说明",
    "执行卡字段",
)
GENERIC_SUBJECTS = {"人", "她", "他", "待人工复核主体"}


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json_sha(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return sha_text(payload)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: JSONL row is not an object")
        records.append(value)
    return records


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: YAML root is not a mapping")
    return value


def exact_span(body: str, evidence: Any) -> bool:
    if not isinstance(evidence, dict):
        return False
    text = evidence.get("text")
    start = evidence.get("start")
    end = evidence.get("end")
    return (
        isinstance(text, str)
        and bool(text)
        and isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start <= end <= len(body)
        and body[start:end] == text
        and end - start == len(text)
    )


def add_error(
    errors: list[dict[str, str]], code: str, asset_id: str, detail: str
) -> None:
    errors.append({"code": code, "asset_id": asset_id, "detail": detail})


def scan_role_mentions(body: str) -> Counter[tuple[str, int, int]]:
    return Counter(
        (match.group(0), match.start(), match.end())
        for match in ROLE_SCAN_RE.finditer(body)
    )


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


def validate_records(
    records: list[dict[str, Any]],
    parent_records: list[dict[str, Any]],
    old_contract_records: dict[str, dict[str, Any]],
    body_packet_records: dict[str, dict[str, Any]],
    contract: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    errors: list[dict[str, str]] = []
    parent_by_id = {record["asset_id"]: record for record in parent_records}
    current_by_id = {record.get("asset_id"): record for record in records}
    if len(records) != 120:
        add_error(
            errors, "E_ASSET_COUNT", "GLOBAL", f"expected 120, got {len(records)}"
        )
    if len(current_by_id) != len(records) or None in current_by_id:
        add_error(
            errors, "E_ASSET_ID_UNIQUE", "GLOBAL", "asset_id is missing or duplicated"
        )
    if set(current_by_id) != set(parent_by_id):
        add_error(
            errors,
            "E_ASSET_DENOMINATOR",
            "GLOBAL",
            "asset IDs differ from parent Clean-120",
        )
    kernel_ids = [record.get("kernel_id") for record in records]
    if len(set(kernel_ids)) != len(kernel_ids) or len(set(kernel_ids)) != 120:
        add_error(
            errors,
            "E_KERNEL_ID_UNIQUE",
            "GLOBAL",
            "kernel denominator is not 120 unique IDs",
        )

    changed_ids: set[str] = set()
    mention_total = 0
    binding_total = 0
    nonempty_expression_fields = 0
    expression_evidence_total = 0

    for asset_id, record in current_by_id.items():
        if not isinstance(asset_id, str) or asset_id not in parent_by_id:
            continue
        parent = parent_by_id[asset_id]
        body = record.get("body_text")
        if not isinstance(body, str) or not body:
            add_error(
                errors, "E_BODY_MISSING", asset_id, "body_text is empty or not text"
            )
            continue
        lineage = record.get("body_lineage", {})
        changed = body != parent.get("body_text")
        if changed:
            changed_ids.add(asset_id)
        if lineage.get("body_changed_in_this_task") is not changed:
            add_error(
                errors,
                "E_BODY_CHANGE_FLAG",
                asset_id,
                "lineage change flag disagrees with body bytes",
            )
        if lineage.get("parent_body_sha256") != sha_text(parent["body_text"]):
            add_error(
                errors, "E_PARENT_BODY_DIGEST", asset_id, "parent body digest mismatch"
            )
        if lineage.get("final_body_sha256") != sha_text(body):
            add_error(
                errors, "E_FINAL_BODY_DIGEST", asset_id, "final body digest mismatch"
            )
        for pattern in BODY_METADATA_PATTERNS:
            if pattern in body:
                add_error(
                    errors,
                    "E_BODY_EXECUTION_METADATA",
                    asset_id,
                    f"body contains {pattern!r}",
                )
        for pattern in BODY_REVIEW_LANGUAGE_PATTERNS:
            if pattern in body:
                add_error(
                    errors,
                    "E_BODY_REVIEW_LANGUAGE",
                    asset_id,
                    f"body contains {pattern!r}",
                )

        if asset_id in body_packet_records:
            packet_record = body_packet_records[asset_id]
            if body != packet_record.get("after_body_text"):
                add_error(
                    errors,
                    "E_FROZEN_AFTER_BODY",
                    asset_id,
                    "final body differs from frozen after body",
                )
            if parent.get("body_text") != packet_record.get("before_body_text"):
                add_error(
                    errors,
                    "E_FROZEN_BEFORE_BODY",
                    asset_id,
                    "parent body differs from frozen before body",
                )
            preserved = packet_record.get("preserved_business_judgment", {})
            after_evidence = preserved.get("after_evidence")
            if not isinstance(after_evidence, str) or after_evidence not in body:
                add_error(
                    errors,
                    "E_BUSINESS_JUDGMENT_PRESERVATION",
                    asset_id,
                    "after evidence is absent",
                )

        source_ref = record.get("source_knowledge_kernel_ref", {})
        source_kernel = parent.get("content_kernel")
        expected_source_sha = canonical_json_sha(source_kernel)
        if source_ref.get("source_kernel_id") != parent.get("kernel_id"):
            add_error(
                errors, "E_SOURCE_KERNEL_ID", asset_id, "source kernel ID mismatch"
            )
        if source_ref.get("source_sha256") != parent.get("content_kernel_sha256"):
            add_error(
                errors,
                "E_SOURCE_KERNEL_RECORDED_DIGEST",
                asset_id,
                "recorded source digest drift",
            )
        if source_ref.get("recomputed_source_sha256") != expected_source_sha:
            add_error(
                errors,
                "E_SOURCE_KERNEL_RECOMPUTED_DIGEST",
                asset_id,
                "recomputed source digest drift",
            )
        if source_ref.get("source_sha256") != expected_source_sha:
            add_error(
                errors,
                "E_SOURCE_KERNEL_MUTATION",
                asset_id,
                "source kernel does not match immutable parent",
            )
        if "content_kernel" in record:
            add_error(
                errors,
                "E_SOURCE_KERNEL_EMBEDDED",
                asset_id,
                "raw source kernel is embedded in new asset",
            )
        boundaries = source_ref.get("boundaries", {})
        if not boundaries or any(value is not True for value in boundaries.values()):
            add_error(
                errors,
                "E_SOURCE_BOUNDARIES",
                asset_id,
                "source boundary flags are incomplete",
            )

        entities_value = record.get("role_entities")
        mentions_value = record.get("role_mentions")
        bindings_value = record.get("action_bindings")
        if (
            not isinstance(entities_value, list)
            or not isinstance(mentions_value, list)
            or not isinstance(bindings_value, list)
        ):
            add_error(
                errors,
                "E_ROLE_STRUCTURE",
                asset_id,
                "role entities, mentions, or bindings are not lists",
            )
            continue
        entities = {
            entity.get("entity_id"): entity
            for entity in entities_value
            if isinstance(entity, dict)
        }
        if len(entities) != len(entities_value) or None in entities:
            add_error(
                errors,
                "E_ROLE_ENTITY_ID",
                asset_id,
                "role entity IDs are missing or duplicated",
            )
        for entity in entities_value:
            canonical_role = str(entity.get("canonical_role", ""))
            if not canonical_role or any(
                token in canonical_role.lower() for token in ("unresolved", "ambiguous")
            ):
                add_error(errors, "E_UNRESOLVED_ROLE_ENTITY", asset_id, canonical_role)
        mention_total += len(mentions_value)
        binding_total += len(bindings_value)

        scanned = scan_role_mentions(body)
        classified = Counter()
        for mention in mentions_value:
            if not isinstance(mention, dict):
                add_error(
                    errors,
                    "E_ROLE_MENTION_SHAPE",
                    asset_id,
                    "role mention is not an object",
                )
                continue
            mention_span = mention.get("body_span")
            if not exact_span(body, mention_span):
                add_error(
                    errors,
                    "E_ROLE_MENTION_SPAN",
                    asset_id,
                    str(mention.get("mention_id")),
                )
                continue
            if mention.get("mention_text") != mention_span.get("text"):
                add_error(
                    errors,
                    "E_ROLE_MENTION_TEXT",
                    asset_id,
                    str(mention.get("mention_id")),
                )
            if mention.get("referent_id") not in entities:
                add_error(
                    errors, "E_ROLE_REFERENT", asset_id, str(mention.get("mention_id"))
                )
            functions = mention.get("semantic_functions")
            if (
                not isinstance(functions, list)
                or not functions
                or not set(functions) <= SEMANTIC_FUNCTIONS
            ):
                add_error(
                    errors, "E_ROLE_FUNCTION", asset_id, str(mention.get("mention_id"))
                )
                functions = []
            if "action_executor" in functions and set(functions) & NON_ACTUAL_FUNCTIONS:
                add_error(
                    errors,
                    "E_NONACTUAL_EXECUTOR",
                    asset_id,
                    str(mention.get("mention_id")),
                )
            if mention.get("classification_basis") == "publisher_or_narrator_default":
                add_error(
                    errors,
                    "E_PUBLISHER_DEFAULT_EXECUTOR",
                    asset_id,
                    str(mention.get("mention_id")),
                )
            token = (mention_span["text"], mention_span["start"], mention_span["end"])
            if token in scanned:
                classified[token] += 1
        for token, count in scanned.items():
            if classified[token] < count:
                add_error(errors, "E_UNCLASSIFIED_ROLE_MENTION", asset_id, repr(token))

        actual_binding_actor_spans: set[tuple[str, int]] = set()
        for binding in bindings_value:
            if not isinstance(binding, dict):
                add_error(
                    errors,
                    "E_ACTION_BINDING_SHAPE",
                    asset_id,
                    "action binding is not an object",
                )
                continue
            actor_ref = binding.get("actor_ref")
            if actor_ref not in entities:
                add_error(
                    errors,
                    "E_ACTION_ACTOR_REF",
                    asset_id,
                    str(binding.get("action_id")),
                )
                continue
            actor_span = binding.get("actor_evidence_span")
            action_span = binding.get("action_evidence_span")
            object_span = binding.get("object_evidence_span")
            if (
                not exact_span(body, actor_span)
                or not exact_span(body, action_span)
                or not exact_span(body, object_span)
            ):
                add_error(
                    errors, "E_ACTION_EVIDENCE", asset_id, str(binding.get("action_id"))
                )
                continue
            polarity = binding.get("action_polarity")
            if polarity not in {
                "actual",
                "hypothetical",
                "negated",
                "quoted_or_referenced",
            }:
                add_error(
                    errors, "E_ACTION_POLARITY", asset_id, str(binding.get("action_id"))
                )
            actual = polarity == "actual"
            if binding.get("portrayed_as_actual_action") is not actual:
                add_error(
                    errors,
                    "E_ACTION_ACTUAL_FLAG",
                    asset_id,
                    str(binding.get("action_id")),
                )
            entity = entities[actor_ref]
            if actual and entity.get("entity_kind") in {"audience", "mannequin_prop"}:
                add_error(
                    errors,
                    "E_INVALID_ACTUAL_ACTOR_KIND",
                    asset_id,
                    str(binding.get("action_id")),
                )
            if actual and entity.get("entity_kind") in {"human", "abstract_group"}:
                counted = entity.get("counts_as_event_human") is True
                alias_refs = entity.get("resolved_alias_of_entity_refs", [])
                valid_alias = (
                    entity.get("entity_kind") == "abstract_group"
                    and isinstance(alias_refs, list)
                    and bool(alias_refs)
                    and all(
                        ref in entities
                        and entities[ref].get("counts_as_event_human") is True
                        for ref in alias_refs
                    )
                )
                if not counted and not valid_alias:
                    add_error(
                        errors,
                        "E_ACTUAL_ACTOR_NOT_COUNTED_OR_RESOLVED",
                        asset_id,
                        str(binding.get("action_id")),
                    )
            matching_mentions = [
                mention
                for mention in mentions_value
                if mention.get("referent_id") == actor_ref
                and mention.get("body_span", {}).get("start") == actor_span["start"]
            ]
            if not matching_mentions:
                add_error(
                    errors,
                    "E_ACTION_WITHOUT_ROLE_MENTION",
                    asset_id,
                    str(binding.get("action_id")),
                )
            if actual and not any(
                "action_executor" in mention.get("semantic_functions", [])
                for mention in matching_mentions
            ):
                add_error(
                    errors,
                    "E_ACTION_WITHOUT_EXECUTOR_CLASS",
                    asset_id,
                    str(binding.get("action_id")),
                )
            if actual:
                actual_binding_actor_spans.add(
                    (str(actor_ref), int(actor_span["start"]))
                )
        for mention in mentions_value:
            if "action_executor" in mention.get("semantic_functions", []):
                key = (
                    str(mention.get("referent_id")),
                    int(mention.get("body_span", {}).get("start", -1)),
                )
                if key not in actual_binding_actor_spans:
                    add_error(
                        errors,
                        "E_EXECUTOR_WITHOUT_ACTION",
                        asset_id,
                        str(mention.get("mention_id")),
                    )

        event_refs = set(
            record.get("execution_card", {}).get("event_human_entity_refs", [])
        )
        capture_refs = set(
            record.get("execution_card", {}).get("capture_human_entity_refs", [])
        )
        expected_event_refs = {
            entity_id
            for entity_id, entity in entities.items()
            if entity.get("counts_as_event_human") is True
        }
        expected_capture_refs = {
            entity_id
            for entity_id, entity in entities.items()
            if entity.get("counts_as_capture_human") is True
        }
        if event_refs != expected_event_refs:
            add_error(
                errors,
                "E_EVENT_ROLE_REFS",
                asset_id,
                "execution card event refs mismatch entities",
            )
        if capture_refs != expected_capture_refs:
            add_error(
                errors,
                "E_CAPTURE_ROLE_REFS",
                asset_id,
                "execution card capture refs mismatch entities",
            )
        for entity_id, entity in entities.items():
            kind = entity.get("entity_kind")
            if kind == "mannequin_prop" and (
                entity.get("counts_as_event_human") is not False
                or entity.get("counts_as_capture_human") is not False
                or entity_id in event_refs
                or entity_id in capture_refs
            ):
                add_error(errors, "E_MANNEQUIN_COUNTED_AS_HUMAN", asset_id, entity_id)
            if kind == "audience" and (
                entity_id in event_refs or entity_id in capture_refs
            ):
                add_error(
                    errors, "E_AUDIENCE_COUNTED_AS_PARTICIPANT", asset_id, entity_id
                )
        card = record.get("execution_card", {})
        if card.get("event_required_people_min") != expected_headcount(
            entities_value, "counts_as_event_human"
        ):
            add_error(
                errors,
                "E_EVENT_HEADCOUNT",
                asset_id,
                "event headcount does not recompute",
            )
        if card.get("capture_required_people_min") != expected_headcount(
            entities_value, "counts_as_capture_human"
        ):
            add_error(
                errors,
                "E_CAPTURE_HEADCOUNT",
                asset_id,
                "capture headcount does not recompute",
            )
        if (
            card.get("independent_capture_human_required") is not False
            or card.get("hired_performer_count") != 0
        ):
            add_error(
                errors,
                "E_CAPTURE_EXECUTION_CARD",
                asset_id,
                "unexpected capture person or hired performer",
            )

        expression = record.get("expression_content_kernel_candidate", {})
        if not isinstance(expression, dict) or any(
            field not in expression for field in REQUIRED_EXPRESSION_FIELDS
        ):
            add_error(
                errors,
                "E_EXPRESSION_FIELDS",
                asset_id,
                "expression kernel fields are incomplete",
            )
            continue
        if expression.get("derived_from_final_body_only") is not True:
            add_error(
                errors,
                "E_EXPRESSION_DERIVATION_SOURCE",
                asset_id,
                "not final-body-only",
            )
        if expression.get("derived_body_sha256") != sha_text(body):
            add_error(
                errors,
                "E_EXPRESSION_BODY_DIGEST",
                asset_id,
                "derived body digest mismatch",
            )
        if (
            expression.get("creates_new_knowledge") is not False
            or expression.get("runtime_ready") is not False
        ):
            add_error(
                errors,
                "E_EXPRESSION_READINESS",
                asset_id,
                "expression kernel crossed its review boundary",
            )
        evidence_value = expression.get("field_evidence_spans")
        if not isinstance(evidence_value, list):
            add_error(
                errors,
                "E_EXPRESSION_EVIDENCE_SHAPE",
                asset_id,
                "field evidence is not a list",
            )
            continue
        evidence_by_field: dict[str, list[dict[str, Any]]] = {}
        for evidence in evidence_value:
            if not isinstance(evidence, dict):
                add_error(
                    errors,
                    "E_EXPRESSION_EVIDENCE_ITEM",
                    asset_id,
                    "evidence item is not an object",
                )
                continue
            field = evidence.get("field")
            if field not in REQUIRED_EXPRESSION_FIELDS:
                add_error(errors, "E_EXPRESSION_EVIDENCE_FIELD", asset_id, str(field))
                continue
            if not exact_span(body, evidence.get("body_span")):
                add_error(errors, "E_EXPRESSION_EVIDENCE_SPAN", asset_id, str(field))
            if evidence.get("derivation_mode") not in {
                "extractive",
                "minimally_normalized",
                "faithful_paraphrase",
            }:
                add_error(errors, "E_EXPRESSION_DERIVATION_MODE", asset_id, str(field))
            evidence_by_field.setdefault(str(field), []).append(evidence)
        expression_evidence_total += len(evidence_value)
        for field in REQUIRED_EXPRESSION_FIELDS:
            value = expression.get(field)
            units = (
                value
                if field == "human_subject" and isinstance(value, list)
                else ([value] if value else [])
            )
            nonempty_expression_fields += len(units)
            field_evidence = evidence_by_field.get(field, [])
            if len(field_evidence) != len(units):
                add_error(errors, "E_EXPRESSION_EVIDENCE_COVERAGE", asset_id, field)
                continue
            for index, unit in enumerate(units):
                evidence = field_evidence[index]
                mode = evidence.get("derivation_mode")
                source_text = evidence.get("body_span", {}).get("text")
                if (
                    field != "human_subject"
                    and mode == "extractive"
                    and unit != source_text
                ):
                    add_error(errors, "E_EXPRESSION_UNSUPPORTED_VALUE", asset_id, field)
                if field == "human_subject" and unit in GENERIC_SUBJECTS:
                    add_error(
                        errors, "E_EXPRESSION_GENERIC_SUBJECT", asset_id, str(unit)
                    )
        actual_subjects = [
            entity.get("canonical_role")
            for entity in entities_value
            if entity.get("counts_as_event_human") is True
        ]
        if expression.get("human_subject") != actual_subjects:
            add_error(
                errors,
                "E_EXPRESSION_SUBJECT_BINDING",
                asset_id,
                "human subjects differ from actual human entities",
            )
        actual_action_spans = {
            binding.get("action_evidence_span", {}).get("text")
            for binding in bindings_value
            if binding.get("action_polarity") == "actual"
            and binding.get("portrayed_as_actual_action") is True
        }
        observable = expression.get("observable_action")
        if observable and observable not in actual_action_spans:
            add_error(
                errors,
                "E_EXPRESSION_ACTION_BINDING",
                asset_id,
                "observable action lacks actual action binding",
            )
        if not actual_action_spans and observable:
            add_error(
                errors,
                "E_EXPRESSION_ACTION_WITHOUT_ACTOR",
                asset_id,
                "observable action exists without actual actor",
            )
        expression_text = json.dumps(expression, ensure_ascii=False)
        for pattern in BODY_REVIEW_LANGUAGE_PATTERNS:
            if pattern in expression_text:
                add_error(errors, "E_EXPRESSION_REVIEW_METADATA", asset_id, pattern)

        relation = record.get("source_to_expression_relation", {})
        if relation.get("conflicting_elements") != []:
            add_error(
                errors,
                "E_SOURCE_EXPRESSION_CONFLICT",
                asset_id,
                "conflicting source elements are present",
            )
        relation_items = []
        for key in (
            "expressed_source_elements",
            "partially_expressed_source_elements",
            "unexpressed_source_elements",
        ):
            value = relation.get(key)
            if not isinstance(value, list):
                add_error(errors, "E_SOURCE_RELATION_SHAPE", asset_id, key)
                value = []
            relation_items.extend(value)
        relation_fields = [
            item.get("field") for item in relation_items if isinstance(item, dict)
        ]
        if Counter(relation_fields) != Counter(parent.get("content_kernel", {}).keys()):
            add_error(
                errors,
                "E_SOURCE_RELATION_COVERAGE",
                asset_id,
                "source fields are missing or duplicated",
            )

        old = old_contract_records.get(asset_id, {})
        old_claim = old.get("claim_control", {})
        old_event = old.get("event_binding", {})
        boundary = record.get("claim_event_boundary", {})
        if boundary.get("immutable_claim_risk") != old_claim.get(
            "immutable_claim_risk"
        ):
            add_error(errors, "E_CLAIM_RISK_DRIFT", asset_id, "claim risk changed")
        if boundary.get("required_claim_route") != old_claim.get("required_route"):
            add_error(
                errors, "E_CLAIM_ROUTE_DRIFT", asset_id, "required claim route changed"
            )
        if boundary.get("actual_claim_route") != old_claim.get("actual_route"):
            add_error(
                errors, "E_CLAIM_ROUTE_DRIFT", asset_id, "actual claim route changed"
            )
        if boundary.get("event_surface_mode") != old_event.get("event_surface_mode"):
            add_error(errors, "E_EVENT_MODE_DRIFT", asset_id, "event mode changed")
        if boundary.get("event_authorization") != old_event.get("authorization"):
            add_error(
                errors,
                "E_EVENT_AUTHORIZATION_DRIFT",
                asset_id,
                "event authorization changed",
            )
        if not exact_span(body, boundary.get("event_evidence_span")):
            add_error(
                errors, "E_EVENT_EVIDENCE", asset_id, "event evidence span is invalid"
            )
        if boundary.get("unsupported_positive_claim") is not False:
            add_error(
                errors,
                "E_UNSUPPORTED_POSITIVE_CLAIM",
                asset_id,
                "unsupported claim flag is true",
            )

        if (
            record.get("knowledge_count_increment") != 0
            or record.get("counts_toward_600_or_3600") is not False
        ):
            add_error(
                errors,
                "E_KNOWLEDGE_OR_SCALE_COUNT",
                asset_id,
                "asset was counted as knowledge or scale output",
            )
        for flag in READINESS_FLAGS:
            if record.get("readiness_flags", {}).get(flag) is not False:
                add_error(errors, "E_READINESS_TRUE", asset_id, flag)
        if record.get("accepted_domain_knowledge") is not False:
            add_error(
                errors,
                "E_ACCEPTED_DOMAIN_KNOWLEDGE",
                asset_id,
                "asset was accepted as domain knowledge",
            )
        if (
            record.get("candidatepack_ready") is not False
            or record.get("production_servable") is not False
        ):
            add_error(
                errors,
                "E_DOWNSTREAM_READY",
                asset_id,
                "downstream readiness became true",
            )

    if changed_ids != AUTHORIZED_BODY_IDS:
        add_error(errors, "E_CHANGED_BODY_SET", "GLOBAL", f"got {sorted(changed_ids)}")

    explicit_cases = {
        "P7D40-REPAIR-006": "quoted_or_referenced_role",
        "RV80-ASSET-006": "absent_or_prohibited_role",
        "RV80-ASSET-015": "absent_or_prohibited_role",
    }
    for asset_id, expected_function in explicit_cases.items():
        record = current_by_id.get(asset_id, {})
        customer_mentions = [
            mention
            for mention in record.get("role_mentions", [])
            if mention.get("mention_text") == "顾客"
        ]
        if not customer_mentions or any(
            expected_function not in m.get("semantic_functions", [])
            for m in customer_mentions
        ):
            add_error(errors, "E_EXPLICIT_CUSTOMER_CASE", asset_id, expected_function)
        customer_refs = {mention.get("referent_id") for mention in customer_mentions}
        if any(
            "action_executor" in mention.get("semantic_functions", [])
            for mention in customer_mentions
        ):
            add_error(
                errors,
                "E_EXPLICIT_CUSTOMER_EXECUTOR",
                asset_id,
                "customer became executor",
            )
        if customer_refs & set(
            record.get("execution_card", {}).get("event_human_entity_refs", [])
        ):
            add_error(
                errors,
                "E_EXPLICIT_CUSTOMER_PARTICIPANT",
                asset_id,
                "customer entered event headcount",
            )

    contract_scale = contract.get("scale_and_downstream", {})
    if (
        contract_scale.get("expand_600") is not False
        or contract_scale.get("expand_3600") is not False
    ):
        add_error(errors, "E_SCALE_UNLOCKED", "GLOBAL", "scale flag became true")
    if contract_scale.get("readiness_all_false") is not True:
        add_error(
            errors,
            "E_CONTRACT_READINESS",
            "GLOBAL",
            "contract readiness boundary changed",
        )
    for key in ("CandidatePack", "KE", "Serving", "RAG", "DIFY", "production"):
        if contract_scale.get(key) != "BLOCKED":
            add_error(errors, "E_DOWNSTREAM_UNBLOCKED", "GLOBAL", key)
    if contract.get("machine_semantics_scope") != "STRUCTURAL_EVIDENCE_ONLY":
        add_error(
            errors, "E_MACHINE_SEMANTICS_SCOPE", "GLOBAL", "machine scope is overstated"
        )
    if (
        contract.get("forbidden_machine_claim")
        != "FULL_NATURAL_LANGUAGE_ROLE_SEMANTICS_PROVEN"
    ):
        add_error(
            errors,
            "E_MACHINE_SEMANTICS_GUARD",
            "GLOBAL",
            "forbidden claim guard is absent",
        )
    acceptance = contract.get("acceptance", {})
    if acceptance.get("success_status") != SUCCESS_STATUS:
        add_error(
            errors,
            "E_CONTRACT_SUCCESS_STATUS",
            "GLOBAL",
            "contract success status drift",
        )
    for key in (
        "clean_120_final_acceptance",
        "runtime_content_kernel_ready",
        "semantic_asset_integrity_final_pass",
    ):
        if acceptance.get(key) is not False:
            add_error(errors, "E_CONTRACT_FINALITY_OVERCLAIM", "GLOBAL", key)

    metrics = {
        "asset_count": len(records),
        "unique_kernel_count": len(set(kernel_ids)),
        "body_changed_count": len(changed_ids),
        "unchanged_body_byte_identical_count": len(records) - len(changed_ids),
        "classified_role_mention_count": mention_total,
        "action_binding_count": binding_total,
        "expression_nonempty_field_count": nonempty_expression_fields,
        "expression_evidence_span_count": expression_evidence_total,
        "machine_semantics_scope": "STRUCTURAL_EVIDENCE_ONLY",
    }
    return errors, metrics


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
        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
        "clean_120_semantic_asset_closeout_001/",
        "ci/fixtures/p7d_clean_120_semantic_asset_integrity/",
    )
    allowed_exact = {
        "ci/checkers/check_p7d_clean_120_semantic_asset_integrity.py",
        "ci/reports/p7d_clean_120_semantic_asset_integrity_report.v0.1.json",
        "docs/reports/p7d_clean_120_semantic_asset_integrity_report.md",
        "docs/reports/p7d_clean_120_semantic_asset_integrity_receipt.json",
        "10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml",
        "10_execution_progress/grc_3600_execution_plan_status.v0.1.md",
    }
    changed = set(git_output(root, "diff", "--name-only", BASELINE_HEAD).splitlines())
    status_lines = git_output(root, "status", "--porcelain=v1").splitlines()
    for line in status_lines:
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.add(path)
    for path in sorted(changed):
        if path in allowed_exact or path.startswith(allowed_prefixes):
            continue
        add_error(errors, "E_WRITE_SURFACE", "GLOBAL", path)
    return errors


def validate_ledger(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    yaml_path = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
    current = load_yaml_mapping(root / yaml_path)
    baseline_text = git_output(root, "show", f"{BASELINE_HEAD}:{yaml_path.as_posix()}")
    baseline = yaml.safe_load(baseline_text)
    current_root = current.get("grc_3600_execution_plan_status", {})
    baseline_root = baseline.get("grc_3600_execution_plan_status", {})
    migration = current_root.get("route_migration_15")
    if not isinstance(migration, dict):
        add_error(
            errors, "E_ROUTE_MIGRATION_15", "GLOBAL", "route_migration_15 is absent"
        )
        return errors
    without_migration = copy.deepcopy(current_root)
    without_migration.pop("route_migration_15", None)
    if without_migration != baseline_root:
        add_error(
            errors,
            "E_LEDGER_NON_ADDITIVE",
            "GLOBAL",
            "ledger changed outside route_migration_15",
        )
    expected = {
        "body_repairs": 6,
        "role_semantic_bindings": 120,
        "source_expression_kernel_splits": 120,
        "knowledge_count_increment": 0,
    }
    if migration.get("scope") != expected:
        add_error(
            errors,
            "E_ROUTE_MIGRATION_SCOPE",
            "GLOBAL",
            "route_migration_15 scope mismatch",
        )
    if (
        migration.get("next_if_guardian_pass")
        != "FOUNDER_P7D_CLEAN_120_FINAL_ACCEPTANCE"
    ):
        add_error(
            errors,
            "E_ROUTE_NEXT",
            "GLOBAL",
            "next route is not founder final acceptance",
        )
    if migration.get("scale") != {"expand_600": False, "expand_3600": False}:
        add_error(errors, "E_ROUTE_SCALE", "GLOBAL", "scale lock drift")
    if migration.get("downstream_and_readiness") != {"all_false": True}:
        add_error(errors, "E_ROUTE_READINESS", "GLOBAL", "readiness boundary drift")

    md_path = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.md")
    current_md = (root / md_path).read_text(encoding="utf-8")
    baseline_md = git_output(root, "show", f"{BASELINE_HEAD}:{md_path.as_posix()}")
    if not current_md.startswith(baseline_md):
        add_error(
            errors,
            "E_LEDGER_MD_NON_ADDITIVE",
            "GLOBAL",
            "human ledger was not append-only",
        )
    if (
        "## P7D Clean-120 Semantic Asset Integrity Closeout"
        not in current_md[len(baseline_md) :]
    ):
        add_error(
            errors,
            "E_LEDGER_MD_SECTION",
            "GLOBAL",
            "route_migration_15 summary is absent",
        )
    return errors


def load_bundle(
    root: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    base = root / (
        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
        "clean_120_surgical_recovery_001"
    )
    out = root / (
        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
        "clean_120_semantic_asset_closeout_001"
    )
    records = load_jsonl(out / "clean_120_semantic_asset_manifest.v0.1.jsonl")
    parent = load_jsonl(base / "clean_120_candidate_manifest.v0.1.jsonl")
    old_contract_raw = load_yaml_mapping(
        base / "clean_120_semantic_integrity_contract.v0.1.yaml"
    )
    old_records = {
        record["asset_id"]: record
        for record in old_contract_raw["clean_120_semantic_integrity_contract"][
            "records"
        ]
    }
    packet_raw = load_yaml_mapping(out / "six_body_before_after_packet.v0.1.yaml")
    packet_records = {
        record["asset_id"]: record
        for record in packet_raw["six_body_before_after_packet"]["records"]
    }
    contract_raw = load_yaml_mapping(
        out / "semantic_asset_integrity_contract.v0.1.yaml"
    )
    contract = contract_raw["semantic_asset_integrity_contract"]
    guardian = load_yaml_mapping(
        out / "semantic_asset_guardian_review_packet.v0.1.yaml"
    )
    result = load_yaml_mapping(out / "semantic_asset_closeout_result.v0.1.yaml")
    return records, parent, old_records, packet_records, contract, guardian, result


def validate_supporting_artifacts(
    records: list[dict[str, Any]], guardian: dict[str, Any], result: dict[str, Any]
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    guardian_root = guardian.get("semantic_asset_guardian_review_packet", {})
    items = guardian_root.get("items")
    if not isinstance(items, list) or len(items) != 120:
        add_error(
            errors,
            "E_GUARDIAN_PACKET_COUNT",
            "GLOBAL",
            "guardian item count is not 120",
        )
    elif {item.get("asset_id") for item in items} != {
        record.get("asset_id") for record in records
    }:
        add_error(
            errors,
            "E_GUARDIAN_PACKET_COVERAGE",
            "GLOBAL",
            "guardian packet coverage mismatch",
        )
    else:
        records_by_id = {record["asset_id"]: record for record in records}
        for item in items:
            asset_id = item["asset_id"]
            record = records_by_id[asset_id]
            expression = record["expression_content_kernel_candidate"]
            expected_item = {
                "role_mention_count": len(record["role_mentions"]),
                "actual_action_binding_count": sum(
                    binding.get("action_polarity") == "actual"
                    for binding in record["action_bindings"]
                ),
                "event_required_people_min": record["execution_card"][
                    "event_required_people_min"
                ],
                "capture_required_people_min": record["execution_card"][
                    "capture_required_people_min"
                ],
                "expression_nonempty_field_count": sum(
                    bool(expression[field]) for field in REQUIRED_EXPRESSION_FIELDS
                ),
                "expression_evidence_span_count": len(
                    expression["field_evidence_spans"]
                ),
            }
            for key, expected_value in expected_item.items():
                if item.get(key) != expected_value:
                    add_error(errors, "E_GUARDIAN_PACKET_METRIC", asset_id, key)
    if (
        guardian_root.get("machine_limit", {}).get("status")
        != "STRUCTURAL_ROLE_EVIDENCE_ONLY"
    ):
        add_error(
            errors,
            "E_GUARDIAN_MACHINE_LIMIT",
            "GLOBAL",
            "guardian packet overstates machine semantics",
        )
    if (
        guardian_root.get("next_if_guardian_pass")
        != "FOUNDER_P7D_CLEAN_120_FINAL_ACCEPTANCE"
    ):
        add_error(errors, "E_GUARDIAN_NEXT", "GLOBAL", "guardian next action mismatch")

    result_root = result.get("semantic_asset_closeout_result", {})
    if result_root.get("result_status") != SUCCESS_STATUS:
        add_error(
            errors,
            "E_RESULT_STATUS",
            "GLOBAL",
            "result status is not pending guardian and founder",
        )
    if result_root.get("machine_semantics_scope") != "STRUCTURAL_EVIDENCE_ONLY":
        add_error(
            errors,
            "E_RESULT_MACHINE_SCOPE",
            "GLOBAL",
            "result overstates machine semantics",
        )
    if result_root.get("structural_role_evidence") != "STRUCTURAL_ROLE_EVIDENCE_PASS":
        add_error(
            errors,
            "E_RESULT_STRUCTURAL_EVIDENCE",
            "GLOBAL",
            "structural evidence result mismatch",
        )
    if result_root.get("full_natural_language_role_semantics_proven") is not False:
        add_error(
            errors,
            "E_RESULT_NL_SEMANTICS",
            "GLOBAL",
            "full natural-language semantics was claimed",
        )
    if (
        result_root.get("guardian_and_founder", {}).get("founder_final_acceptance")
        is not False
    ):
        add_error(
            errors,
            "E_RESULT_FINAL_ACCEPTANCE",
            "GLOBAL",
            "founder final acceptance was claimed",
        )
    if result_root.get("scale") != {"expand_600": False, "expand_3600": False}:
        add_error(errors, "E_RESULT_SCALE", "GLOBAL", "result scale lock drift")
    if result_root.get("downstream_and_readiness", {}).get("all_false") is not True:
        add_error(
            errors, "E_RESULT_READINESS", "GLOBAL", "result readiness boundary drift"
        )
    result_metrics = result_root.get("machine_acceptance", {})
    expected_result_metrics = {
        "asset_count": len(records),
        "unique_kernel_count": len({record["kernel_id"] for record in records}),
        "body_changed_count": sum(
            record["body_lineage"]["body_changed_in_this_task"] for record in records
        ),
        "classified_role_mention_count": sum(
            len(record["role_mentions"]) for record in records
        ),
        "action_binding_count": sum(
            len(record["action_bindings"]) for record in records
        ),
        "expression_kernel_nonempty_field_count": sum(
            len(record["expression_content_kernel_candidate"][field])
            if field == "human_subject"
            else 1
            for record in records
            for field in REQUIRED_EXPRESSION_FIELDS
            if record["expression_content_kernel_candidate"][field]
        ),
        "expression_kernel_evidence_span_count": sum(
            len(record["expression_content_kernel_candidate"]["field_evidence_spans"])
            for record in records
        ),
    }
    for key, expected_value in expected_result_metrics.items():
        if result_metrics.get(key) != expected_value:
            add_error(errors, "E_RESULT_METRIC", "GLOBAL", key)
    return errors


def run_live(
    root: Path, write_report: bool
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    records, parent, old_records, packet, contract, guardian, result = load_bundle(root)
    errors, metrics = validate_records(records, parent, old_records, packet, contract)
    errors.extend(validate_supporting_artifacts(records, guardian, result))
    errors.extend(validate_ledger(root))
    errors.extend(validate_git_surface(root))
    report = {
        "task_id": TASK_ID,
        "checker_status": "PASS" if not errors else "FAIL",
        "machine_semantics_scope": "STRUCTURAL_EVIDENCE_ONLY",
        "error_count": len(errors),
        "errors": errors,
        "metrics": metrics,
        "result_status": SUCCESS_STATUS
        if not errors
        else "SEMANTIC_ASSET_CLOSEOUT_BLOCKED",
    }
    if write_report:
        report_path = (
            root / "ci/reports/p7d_clean_120_semantic_asset_integrity_report.v0.1.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return errors, report


def run_selftest(root: Path) -> dict[str, Any]:
    records, parent, old_records, packet, contract, _, _ = load_bundle(root)
    positive_errors, _ = validate_records(
        records, parent, old_records, packet, contract
    )
    cases: list[tuple[str, Any]] = []

    def add_case(name: str, mutate: Any) -> None:
        cases.append((name, mutate))

    def role_mutator(asset_id: str, mention_text: str, function: str) -> Any:
        def mutate(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
            record = next(row for row in rows if row["asset_id"] == asset_id)
            mention = next(
                item
                for item in record["role_mentions"]
                if item["mention_text"] == mention_text
            )
            mention["semantic_functions"] = [function, "action_executor"]

        return mutate

    add_case(
        "customer_reference_as_executor",
        role_mutator("P7D40-REPAIR-006", "顾客", "quoted_or_referenced_role"),
    )

    def count_role(asset_id: str, mention_text: str) -> Any:
        def mutate(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
            record = next(row for row in rows if row["asset_id"] == asset_id)
            mention = next(
                item
                for item in record["role_mentions"]
                if item["mention_text"] == mention_text
            )
            entity = next(
                item
                for item in record["role_entities"]
                if item["entity_id"] == mention["referent_id"]
            )
            entity["counts_as_event_human"] = True
            entity["counts_as_capture_human"] = True
            entity["minimum_human_count"] = 1
            record["execution_card"]["event_human_entity_refs"].append(
                entity["entity_id"]
            )
            record["execution_card"]["capture_human_entity_refs"].append(
                entity["entity_id"]
            )

        return mutate

    add_case("absent_customer_counted", count_role("RV80-ASSET-006", "顾客"))
    add_case("removed_customer_story_counted", count_role("RV80-ASSET-015", "顾客"))
    add_case("you_counted_as_capture_participant", count_role("RV80-ASSET-028", "你"))
    add_case(
        "quoted_person_as_event_actor",
        role_mutator("RV80-ASSET-026", "版师", "quoted_or_referenced_role"),
    )

    def mannequin_as_human(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        record = next(row for row in rows if row["asset_id"] == "RV80-ASSET-059")
        entity = next(
            item
            for item in record["role_entities"]
            if item["entity_kind"] == "mannequin_prop"
        )
        entity["counts_as_event_human"] = True
        entity["minimum_human_count"] = 1

    add_case("mannequin_as_human", mannequin_as_human)

    def publisher_default(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        mention = next(
            mention
            for row in rows
            for mention in row["role_mentions"]
            if mention["classification_basis"].startswith("implicit_subject")
        )
        mention["classification_basis"] = "publisher_or_narrator_default"

    add_case("publisher_default_executor", publisher_default)

    def missing_action_span(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        rows[0]["action_bindings"][0]["action_evidence_span"] = {
            "text": "",
            "start": 0,
            "end": 0,
        }

    add_case("action_without_action_span", missing_action_span)

    def set_unsupported_expression(
        rows: list[dict[str, Any]], text: str, field: str = "object_anchor"
    ) -> None:
        expression = rows[0]["expression_content_kernel_candidate"]
        expression[field] = text

    add_case(
        "old_kernel_soak_test_in_expression",
        lambda rows, _contract: set_unsupported_expression(rows, "泡水甩干抽检"),
    )
    add_case(
        "business_judgment_strengthened",
        lambda rows, _contract: set_unsupported_expression(
            rows, "该服装保证永久耐穿", "business_judgment"
        ),
    )

    def unsupported_person(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        rows[0]["expression_content_kernel_candidate"]["human_subject"].append(
            "invented_founder"
        )

    add_case("unsupported_expression_person", unsupported_person)

    def body_metadata_leak(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        record = next(row for row in rows if row["asset_id"] == "RV80-ASSET-017")
        record["body_text"] += "手机固定在中岛旁。"

    add_case("six_body_metadata_leak", body_metadata_leak)

    def seventh_body_change(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        record = next(row for row in rows if row["asset_id"] == "RV80-ASSET-001")
        record["body_text"] += "额外改动。"

    add_case("seventh_body_changed", seventh_body_change)

    def unchanged_digest_drift(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        record = next(row for row in rows if row["asset_id"] == "RV80-ASSET-002")
        record["body_lineage"]["final_body_sha256"] = "0" * 64

    add_case("unchanged_body_digest_drift", unchanged_digest_drift)

    def source_kernel_mutation(
        rows: list[dict[str, Any]], _contract: dict[str, Any]
    ) -> None:
        rows[0]["source_knowledge_kernel_ref"]["recomputed_source_sha256"] = "f" * 64

    add_case("source_kernel_mutated", source_kernel_mutation)

    def readiness_true(rows: list[dict[str, Any]], _contract: dict[str, Any]) -> None:
        rows[0]["readiness_flags"]["generation_allowed"] = True

    add_case("readiness_true", readiness_true)

    def scale_or_downstream_true(
        _rows: list[dict[str, Any]], mutable_contract: dict[str, Any]
    ) -> None:
        mutable_contract["scale_and_downstream"]["expand_600"] = True
        mutable_contract["scale_and_downstream"]["Serving"] = "READY"

    add_case("scale_or_downstream_unlocked", scale_or_downstream_true)

    results: list[dict[str, Any]] = []
    for name, mutate in cases:
        mutated_rows = copy.deepcopy(records)
        mutated_contract = copy.deepcopy(contract)
        mutate(mutated_rows, mutated_contract)
        errors, _ = validate_records(
            mutated_rows, parent, old_records, packet, mutated_contract
        )
        results.append(
            {
                "name": name,
                "fail_closed": bool(errors),
                "error_codes": sorted({e["code"] for e in errors}),
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
