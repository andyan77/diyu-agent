#!/usr/bin/env python3
"""Independent, fail-closed surface inventory and claim-closure validator."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


KNOWN_SURFACES = frozenset(
    {
        "title",
        "body",
        "spoken_script",
        "CTA",
        "caption",
        "on_screen_text",
        "visual_direction",
        "shot_instruction",
        "audio_direction",
        "sound_instruction",
    }
)
LIST_SURFACES = frozenset(
    {
        "body",
        "spoken_script",
        "on_screen_text",
        "visual_direction",
        "shot_instruction",
        "sound_instruction",
    }
)
CLASSIFICATIONS = frozenset(
    {
        "SOURCE_BOUND_FACT",
        "SOURCE_BOUND_OPINION_OR_FRAMING",
        "GENERIC_CREATIVE_EXPRESSION",
        "DISCLOSED_HYPOTHETICAL",
        "OPEN_AUDIENCE_QUESTION",
        "EDITORIAL_FORM_OPERATOR",
    }
)
META_TERMS = (
    "CP01",
    "CP02",
    "CP03",
    "CP04",
    "CP05",
    "CP06",
    "CP07",
    "CP08",
    "CP09",
    "CP10",
    "CP11",
    "CP12",
    "CP13",
    "CP14",
    "CP15",
    "CP16",
    "CP17",
    "CP18",
    "CP19",
    "CP20",
    "资格",
    "合成",
    "内部",
    "复审",
    "版本",
    "测试",
    "先看依据",
    "怎么看内容",
)
NUMBER_RE = re.compile(
    r"(?:\d+(?:\.\d+)?%?|[零一二三四五六七八九十百千万两半]+(?:次|个|件|天|小时|分钟|%|％)?)"
)
CAUSAL_MARKERS = ("因为", "所以", "导致", "从而", "因此", "为了", "解决了", "避免了")
RESULT_UPGRADE_MARKERS = ("已经解决", "彻底解决", "全部完成", "得到证明", "验证通过")
ACTION_TERMS = (
    "拉开",
    "剪",
    "缝",
    "熨",
    "投诉",
    "购买",
    "售罄",
    "调拨",
    "承诺",
    "整理",
    "调整",
    "移动",
    "记录",
    "核对",
    "检查",
    "拍摄",
)
ENTITY_TERMS = ("顾客", "店员", "设计师", "负责人", "品牌", "城市", "门店", "街区", "货号", "SKU")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _text_items(surface_type: str, value: Any) -> list[tuple[str, str]]:
    if surface_type in LIST_SURFACES:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise ValueError(f"surface {surface_type} must be an array")
        return [(f"/surfaces/{surface_type}/{index}", str(item)) for index, item in enumerate(value)]
    if not isinstance(value, str):
        raise ValueError(f"surface {surface_type} must be a string")
    return [(f"/surfaces/{surface_type}", value)]


def _claimed_refs(candidate: Mapping[str, Any], pointer: str, text: str) -> list[str]:
    refs: set[str] = set()
    for item in candidate.get("author_claimed_surface_bindings", []):
        if not isinstance(item, Mapping):
            continue
        item_pointer = str(item.get("surface_path", ""))
        item_text = str(item.get("text", ""))
        if item_pointer == pointer and (not item_text or item_text == text):
            refs.update(str(ref) for ref in item.get("source_atom_refs", []))
    return sorted(refs)


def _classification(surface_type: str, text: str, refs: Sequence[str]) -> tuple[str, str]:
    stripped = text.strip()
    if not stripped:
        return "EDITORIAL_FORM_OPERATOR", "PASS"
    if surface_type in {"visual_direction", "shot_instruction", "audio_direction", "sound_instruction"}:
        return "EDITORIAL_FORM_OPERATOR", "PASS" if refs else "HOLD_SEMANTIC"
    if stripped.endswith(("?", "？")):
        return "OPEN_AUDIENCE_QUESTION", "PASS" if not refs else "HOLD_SEMANTIC"
    if stripped.startswith(("如果", "假如", "设想", "假设")):
        return "DISCLOSED_HYPOTHETICAL", "HOLD_SEMANTIC"
    if refs:
        return "SOURCE_BOUND_FACT", "HOLD_SEMANTIC"
    if surface_type == "CTA":
        return "GENERIC_CREATIVE_EXPRESSION", "HOLD_SEMANTIC"
    return "SOURCE_BOUND_OPINION_OR_FRAMING", "HOLD_SEMANTIC"


def _source_binding(atom: Mapping[str, Any], snapshot_digest: str) -> dict[str, Any]:
    text = str(atom["text"])
    encoded = text.encode("utf-8")
    atom_id = str(atom["atom_id"])
    return {
        "source_atom_id": atom_id,
        "source_snapshot_digest": snapshot_digest,
        "source_pointer": f"/source_atoms/{atom_id}/text",
        "binding_kind": "text_span",
        "span_start_utf8_byte": 0,
        "span_end_utf8_byte": len(encoded),
        "span_sha256": hashlib.sha256(encoded).hexdigest(),
        "source_value_digest": digest_object(text),
        "authorization_scope": "DEVELOPMENT_FIXTURE_ONLY_NOT_RUNTIME",
        "support_mode": "SINGLE_ATOM_FAITHFUL_PARAPHRASE",
    }


def validate_candidate(
    candidate: Mapping[str, Any], material_pack: Mapping[str, Any], plan: Mapping[str, Any]
) -> dict[str, Any]:
    """Re-read every controlled surface; author classifications are never trusted."""

    surfaces = candidate.get("surfaces")
    if not isinstance(surfaces, Mapping):
        raise ValueError("candidate surfaces must be an object")
    unknown = sorted(set(map(str, surfaces)).difference(KNOWN_SURFACES))
    missing = sorted(KNOWN_SURFACES.difference(set(map(str, surfaces))))
    atoms = {
        str(atom["atom_id"]): dict(atom)
        for atom in material_pack.get("source_atoms", [])
        if isinstance(atom, Mapping) and atom.get("atom_id")
    }
    source_snapshot_digest = str(plan["source_snapshot_digest"])
    source_text = "\n".join(str(atom["text"]) for atom in atoms.values())
    allowed_numbers = set(NUMBER_RE.findall(source_text))
    allowed_actions = {term for term in ACTION_TERMS if term in source_text}
    allowed_entities = {term for term in ENTITY_TERMS if term in source_text}
    allowed_causal = any(marker in source_text for marker in CAUSAL_MARKERS)
    allowed_results = {marker for marker in RESULT_UPGRADE_MARKERS if marker in source_text}

    units: list[dict[str, Any]] = []
    counters = {
        "undeclared_assertion_count": 0,
        "unsupported_fact_count": 0,
        "invented_number_count": 0,
        "invented_action_count": 0,
        "invented_causality_count": 0,
        "invented_result_count": 0,
        "invented_entity_count": 0,
        "invalid_source_span_count": 0,
        "component_as_fact_source_count": 0,
        "meta_scaffold_leak_count": 0,
    }
    for surface_type in sorted(KNOWN_SURFACES):
        for pointer, text in _text_items(surface_type, surfaces.get(surface_type)):
            refs = _claimed_refs(candidate, pointer, text)
            invalid_refs = [ref for ref in refs if ref not in atoms]
            component_refs = [ref for ref in refs if ref.startswith("RCV2-")]
            counters["invalid_source_span_count"] += len(invalid_refs)
            counters["component_as_fact_source_count"] += len(component_refs)
            valid_refs = [ref for ref in refs if ref in atoms]
            classification, closure_status = _classification(surface_type, text, valid_refs)
            if classification not in CLASSIFICATIONS:
                raise ValueError("internal classification is outside the closed enum")

            invented_numbers = sorted(set(NUMBER_RE.findall(text)).difference(allowed_numbers))
            invented_actions = sorted(
                term for term in ACTION_TERMS if term in text and term not in allowed_actions
            )
            invented_entities = sorted(
                term for term in ENTITY_TERMS if term in text and term not in allowed_entities
            )
            invented_causal = sorted(
                marker for marker in CAUSAL_MARKERS if marker in text and not allowed_causal
            )
            invented_results = sorted(
                marker for marker in RESULT_UPGRADE_MARKERS if marker in text and marker not in allowed_results
            )
            meta_terms = sorted(term for term in META_TERMS if term in text)
            counters["invented_number_count"] += len(invented_numbers)
            counters["invented_action_count"] += len(invented_actions)
            counters["invented_entity_count"] += len(invented_entities)
            counters["invented_causality_count"] += len(invented_causal)
            counters["invented_result_count"] += len(invented_results)
            counters["meta_scaffold_leak_count"] += len(meta_terms)
            if any(
                (
                    invalid_refs,
                    component_refs,
                    invented_numbers,
                    invented_actions,
                    invented_entities,
                    invented_causal,
                    invented_results,
                    meta_terms,
                )
            ):
                closure_status = "FAIL"
            unit: dict[str, Any] = {
                "candidate_id": candidate["candidate_id"],
                "lane_id": candidate["lane_id"],
                "surface_unit_id": f"{candidate['candidate_id']}::{pointer}",
                "surface_type": surface_type,
                "json_pointer": pointer,
                "verbatim_text": text,
                "unit_digest": digest_object(text),
                "classification": classification,
                "claim_frames": {
                    "numbers": NUMBER_RE.findall(text),
                    "actions": [term for term in ACTION_TERMS if term in text],
                    "causal_markers": [term for term in CAUSAL_MARKERS if term in text],
                    "result_markers": [term for term in RESULT_UPGRADE_MARKERS if term in text],
                    "entities": [term for term in ENTITY_TERMS if term in text],
                },
                "source_bindings": [_source_binding(atoms[ref], source_snapshot_digest) for ref in valid_refs],
                "component_form_bindings": [
                    str(binding["canonical_component_id"])
                    for binding in plan.get("component_bindings", [])
                    if isinstance(binding, Mapping)
                ],
                "closure_status": closure_status,
                "machine_findings": {
                    "invalid_refs": invalid_refs,
                    "invented_numbers": invented_numbers,
                    "invented_actions": invented_actions,
                    "invented_entities": invented_entities,
                    "invented_causality": invented_causal,
                    "invented_results": invented_results,
                    "meta_terms": meta_terms,
                },
            }
            units.append(unit)

    failed_unit_count = sum(unit["closure_status"] == "FAIL" for unit in units)
    result: dict[str, Any] = {
        "candidate_id": candidate["candidate_id"],
        "surface_units": units,
        "reviewed_surface_unit_count": len(units),
        "all_surface_units_classified": all(unit["classification"] in CLASSIFICATIONS for unit in units),
        "unclassified_atomic_clause_count": 0,
        "unknown_surface_field_count": len(unknown),
        "missing_surface_field_count": len(missing),
        "surface_partition_gap_count": len(unknown) + len(missing),
        **counters,
        "machine_failed_surface_unit_count": failed_unit_count,
        "machine_claim_closure_pass": failed_unit_count == 0 and not unknown and not missing,
        "machine_final_semantic_claim": False,
        "machine_final_quality_claim": False,
        "producer_self_approval_allowed": False,
        "guardian_full_surface_review_required": True,
    }
    result["validation_digest"] = digest_object(result)
    return result


if __name__ == "__main__":
    raise SystemExit(2)
