#!/usr/bin/env python3
"""G3 后继生成器 · 作者输出合同（fail-closed）。

出处：受控分叉自冻结的
`gate1_v1_1_001/p4_author_output_contract_recovery_001/author_contract.py`
（sha256 见 g3_registry），保留其全部已验证语义：
表面精确拼接（exact join）、主张逐字在面、组件指针序数、五项作者宣誓、
合成披露必含"合成+测试/非真实"。

v3 差异（协议缺陷修复，源指令 §7 执行包1 授权）：
- task_id / schema 换为本任务 v3 值；
- 作者模型锁定 gpt-5.6-sol 作废（源指令 §0/§4），改为 claude-fable-5；
- validate_raw 不再隐式吞并批级 run_id 唯一性（由 g3_gates 批级检查）；
- 新增请求字段 expression_plan / fingerprint_contract 的形状校验。

本模块不读取、不修改任何 P4/P5 历史文件。
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any


if not __debug__:
    sys.stderr.write("g3_author_contract refuses python -O\n")
    raise SystemExit(2)


TASK_ID = "GATE1_V11_SUCCESSOR_LONGRUN_001"
REQUEST_SCHEMA = "gate1-g3-author-request-v3.0"
RAW_SCHEMA = "gate1-g3-author-semantic-output-v3.0"
OUTPUT_SCHEMA = "gate1-g3-author-output-v3.0"
MODEL_CAPABILITY = "claude-fable-5"
REASONING_EFFORT = "high"
SERVICE_TIER = "standard"

RAW_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "run_id",
        "title",
        "body",
        "spoken_lines",
        "cta",
        "visual_execution",
        "audio_execution",
        "synthetic_disclosure",
        "semantic_surfaces",
        "semantic_claims",
        "semantic_component_usage",
        "author_attestation",
    }
)
RAW_SURFACE_FIELDS = frozenset(
    {"surface_kind", "text", "fact_ids", "source_ids", "authorization_ids"}
)
RAW_CLAIM_FIELDS = frozenset(
    {"claim_text", "fact_ids", "source_ids", "authorization_ids", "claim_boundary"}
)
RAW_COMPONENT_FIELDS = frozenset(
    {"component_id", "implementation_note", "surface_ordinals"}
)
EXPECTED_ATTESTATION = {
    "unbound_fact_added": False,
    "input_backfilled_after_authoring": False,
    "external_service_called": False,
    "second_candidate_generated": False,
    "review_performed_by_author": False,
}
ROLE_ALLOWED_SURFACE_KINDS = {
    "scene": ["body", "title", "visual_execution"],
    "trigger": ["body", "spoken_line", "title", "visual_execution"],
    "observable_action": ["body", "spoken_line", "visual_execution"],
    "transition": ["body", "visual_execution"],
    "visual_beat": ["body", "visual_execution"],
    "capture_instruction": ["audio_execution", "visual_execution"],
    "professional_judgment": ["body", "spoken_line"],
    "audience_facing_reasoning_move": ["body", "spoken_line", "visual_execution"],
    "closing": ["body", "cta", "spoken_line", "visual_execution"],
    "narrative_mechanism_operator": ["body", "spoken_line", "visual_execution"],
    "information_order_operator": ["body", "spoken_line", "title", "visual_execution"],
    "visual_subject_operator": ["body", "visual_execution"],
    "sound_subject_operator": ["audio_execution", "spoken_line"],
    "rhythm_operator": ["audio_execution", "body", "spoken_line", "visual_execution"],
    "ending_operator": ["body", "cta", "spoken_line", "visual_execution"],
}
RAW_TYPE_CONTRACT = {
    "schema_version": "nonempty_string",
    "request_id": "nonempty_string",
    "run_id": "nonempty_string_unique_across_batch",
    "title": "nonempty_string",
    "body": "nonempty_string_array_min_1",
    "spoken_lines": "nonempty_string_array_allow_empty",
    "cta": "string_allow_empty",
    "visual_execution": "nonempty_string_array_min_1",
    "audio_execution": "nonempty_string_array_allow_empty",
    "synthetic_disclosure": "nonempty_string",
    "semantic_surfaces": "semantic_surface_array_exact_join",
    "semantic_claims": "semantic_claim_array_min_1",
    "semantic_component_usage": "semantic_component_usage_array",
    "author_attestation": "exact_false_boolean_object",
}
NESTED_TYPE_CONTRACT = {
    "semantic_surface": {
        "surface_kind": "enum_nonempty_string",
        "text": "nonempty_string",
        "fact_ids": "unique_nonempty_string_array_disclosure_may_be_empty",
        "source_ids": "unique_nonempty_string_array_disclosure_may_be_empty",
        "authorization_ids": "unique_nonempty_string_array_disclosure_may_be_empty",
    },
    "semantic_claim": {
        "claim_text": "nonempty_string_verbatim_on_surface",
        "fact_ids": "unique_nonempty_string_array_min_1",
        "source_ids": "unique_nonempty_string_array_min_1",
        "authorization_ids": "unique_nonempty_string_array_min_1",
        "claim_boundary": "nonempty_string_exact_material_boundary",
    },
    "semantic_component_usage": {
        "component_id": "nonempty_string_unique",
        "implementation_note": "nonempty_string",
        "surface_ordinals": "unique_positive_integer_array_min_1",
    },
}
SURFACE_KIND_ENUM = [
    "audio_execution",
    "body",
    "cta",
    "spoken_line",
    "synthetic_disclosure",
    "title",
    "visual_execution",
]

EXPRESSION_PLAN_FIELDS = frozenset(
    {
        "plan_id",
        "opening_archetype",
        "ending_archetype",
        "title_archetype",
        "narrative_arc",
        "body_architecture",
        "spoken_format",
        "audio_signature",
        "boundary_position",
        "boundary_style",
        "boundary_realization",
        "forbidden_patterns",
    }
)
FINGERPRINT_CONTRACT_FIELDS = frozenset(
    {
        "profile_id",
        "entry_signal_duty",
        "neighbor_contrast_duties",
        "machine_predicates",
    }
)


class AuthorContractError(ValueError):
    """Stable fail-closed contract error."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise AuthorContractError(f"{code}:{detail}" if detail else code)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    reduced = {k: v for k, v in value.items() if k != digest_key}
    return sha256_bytes(canonical_json(reduced).encode("utf-8"))


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    require(isinstance(value, Mapping), code)
    return value


def _text(value: Any, code: str, *, allow_empty: bool = False) -> str:
    require(isinstance(value, str), code)
    if not allow_empty:
        require(bool(value.strip()), code)
    return value


def _text_list(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), code)
    if not allow_empty:
        require(bool(value), code)
    for item in value:
        require(isinstance(item, str) and bool(item.strip()), code)
    return list(value)


def _unique_text_list(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    rows = _text_list(value, code, allow_empty=allow_empty)
    require(len(rows) == len(set(rows)), code)
    return rows


def surface_sequence(raw: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows = [
        ("synthetic_disclosure", str(raw["synthetic_disclosure"])),
        ("title", str(raw["title"])),
    ]
    rows.extend(("body", text) for text in raw["body"])
    rows.extend(("spoken_line", text) for text in raw["spoken_lines"])
    if raw["cta"]:
        rows.append(("cta", str(raw["cta"])))
    rows.extend(("visual_execution", text) for text in raw["visual_execution"])
    rows.extend(("audio_execution", text) for text in raw["audio_execution"])
    return rows


def audience_texts(raw: Mapping[str, Any]) -> list[tuple[str, str]]:
    """受众表面 =（标题/正文/口播/CTA/画面/声音），不含专用披露表面。"""
    return [(kind, text) for kind, text in surface_sequence(raw)
            if kind != "synthetic_disclosure"]


def validate_request(request: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "task_id",
        "request_id",
        "request_digest",
        "profile_id",
        "assigned_variant",
        "run_order",
        "author_identity",
        "author_session_logical_id",
        "author_platform_agent_id",
        "model_capability_id",
        "reasoning_effort",
        "service_tier",
        "typed_material",
        "product_core_requirements",
        "approved_components",
        "structure_contract",
        "author_output_contract",
        "exact_author_contract",
        "expression_plan",
        "fingerprint_contract",
    }
    require(required.issubset(request), "E_REQUEST_FIELDS",
            ",".join(sorted(required - set(request))))
    require(request.get("schema_version") == REQUEST_SCHEMA, "E_REQUEST_SCHEMA")
    require(request.get("task_id") == TASK_ID, "E_REQUEST_TASK")
    require(request.get("model_capability_id") == MODEL_CAPABILITY, "E_MODEL")
    require(request.get("reasoning_effort") == REASONING_EFFORT, "E_REASONING")
    require(request.get("service_tier") == SERVICE_TIER, "E_SERVICE_TIER")
    require(
        request.get("request_digest") == object_digest(request, "request_digest"),
        "E_REQUEST_DIGEST",
    )
    contract = _mapping(request.get("exact_author_contract"), "E_EXACT_CONTRACT")
    require(contract.get("raw_schema_version") == RAW_SCHEMA, "E_RAW_SCHEMA_CONTRACT")
    require(contract.get("raw_top_level_fields") == sorted(RAW_FIELDS), "E_RAW_CONTRACT")
    require(contract.get("semantic_surface_fields") == sorted(RAW_SURFACE_FIELDS),
            "E_SURFACE_CONTRACT")
    require(contract.get("semantic_claim_fields") == sorted(RAW_CLAIM_FIELDS),
            "E_CLAIM_CONTRACT")
    require(contract.get("semantic_component_usage_fields") == sorted(RAW_COMPONENT_FIELDS),
            "E_COMPONENT_CONTRACT")
    require(contract.get("author_attestation_fields_and_values") == EXPECTED_ATTESTATION,
            "E_ATTESTATION_CONTRACT")
    require(contract.get("surface_kind_enum") == SURFACE_KIND_ENUM,
            "E_SURFACE_KIND_CONTRACT")
    for key in (
        "component_pointer_must_bind_core_or_required_slot_fact",
        "component_pointer_must_use_role_compatible_surface",
        "core_fact_coverage_required",
        "claim_text_verbatim_on_surface_required",
        "run_id_unique_across_batch",
    ):
        require(contract.get(key) is True, "E_CONTRACT_FLAG", key)
    require(contract.get("role_allowed_surface_kinds") == ROLE_ALLOWED_SURFACE_KINDS,
            "E_ROLE_SURFACE_CONTRACT")
    require(contract.get("raw_type_contract") == RAW_TYPE_CONTRACT, "E_RAW_TYPE_CONTRACT")
    require(contract.get("nested_type_contract") == NESTED_TYPE_CONTRACT,
            "E_NESTED_TYPE_CONTRACT")
    output_contract = _mapping(request.get("author_output_contract"), "E_OUTPUT_CONTRACT")
    for key in ("one_first_semantic_output_only", "author_may_not_review_or_approve"):
        require(output_contract.get(key) is True, "E_OUTPUT_CONTRACT", key)
    for key in ("publishable", "runtime_consumable", "may_enter_300"):
        require(output_contract.get(key) is False, "E_OUTPUT_BOUNDARY", key)
    requirements = request.get("product_core_requirements")
    require(isinstance(requirements, list) and bool(requirements), "E_CORE_REQUIREMENTS")
    for raw_requirement in requirements:
        requirement = _mapping(raw_requirement, "E_CORE_REQUIREMENT")
        _text(requirement.get("requirement_id"), "E_CORE_REQUIREMENT_ID")
        _unique_text_list(requirement.get("fact_ids"), "E_CORE_FACT_IDS")
    plan = _mapping(request.get("expression_plan"), "E_EXPRESSION_PLAN")
    require(set(plan) == EXPRESSION_PLAN_FIELDS, "E_EXPRESSION_PLAN_FIELDS",
            ",".join(sorted(set(plan) ^ EXPRESSION_PLAN_FIELDS)))
    for key in ("plan_id", "opening_archetype", "ending_archetype",
                "title_archetype", "narrative_arc", "body_architecture",
                "spoken_format", "audio_signature", "boundary_position",
                "boundary_realization"):
        _text(plan.get(key), f"E_EXPRESSION_PLAN_VALUE:{key}")
    _text_list(plan.get("forbidden_patterns"), "E_EXPRESSION_PLAN_FORBIDDEN",
               allow_empty=True)
    fingerprint = _mapping(request.get("fingerprint_contract"), "E_FINGERPRINT_CONTRACT")
    require(set(fingerprint) == FINGERPRINT_CONTRACT_FIELDS,
            "E_FINGERPRINT_CONTRACT_FIELDS")
    require(fingerprint.get("profile_id") == request.get("profile_id"),
            "E_FINGERPRINT_PROFILE")
    _text(fingerprint.get("entry_signal_duty"), "E_FINGERPRINT_ENTRY")
    _text_list(fingerprint.get("neighbor_contrast_duties"), "E_FINGERPRINT_NEIGHBORS")
    require(isinstance(fingerprint.get("machine_predicates"), list),
            "E_FINGERPRINT_PREDICATES")


def validate_raw(raw: Mapping[str, Any], request: Mapping[str, Any]) -> None:
    validate_request(request)
    require(set(raw) == RAW_FIELDS, "E_RAW_FIELD_SET",
            ",".join(sorted(set(raw) ^ RAW_FIELDS)))
    require(raw.get("schema_version") == RAW_SCHEMA, "E_RAW_SCHEMA")
    require(raw.get("request_id") == request.get("request_id"), "E_RAW_REQUEST")
    _text(raw.get("run_id"), "E_RAW_RUN_ID")
    _text(raw.get("title"), "E_RAW_TITLE")
    _text_list(raw.get("body"), "E_RAW_BODY")
    _text_list(raw.get("spoken_lines"), "E_RAW_SPOKEN", allow_empty=True)
    _text(raw.get("cta"), "E_RAW_CTA", allow_empty=True)
    _text_list(raw.get("visual_execution"), "E_RAW_VISUAL")
    _text_list(raw.get("audio_execution"), "E_RAW_AUDIO", allow_empty=True)
    disclosure = _text(raw.get("synthetic_disclosure"), "E_RAW_DISCLOSURE")
    require("合成" in disclosure and ("测试" in disclosure or "非真实" in disclosure),
            "E_RAW_DISCLOSURE")
    require(raw.get("author_attestation") == EXPECTED_ATTESTATION, "E_RAW_ATTESTATION")

    expected_surfaces = surface_sequence(raw)
    surfaces = raw.get("semantic_surfaces")
    require(isinstance(surfaces, list), "E_RAW_SURFACES")
    require(len(surfaces) == len(expected_surfaces), "E_RAW_SURFACE_COUNT",
            f"{len(surfaces)}!={len(expected_surfaces)}")
    material = _mapping(request.get("typed_material"), "E_REQUEST_MATERIAL")
    known_fact_ids = {str(f["fact_id"]) for f in material.get("facts", [])}
    known_source_ids = {str(s["source_id"]) for s in material.get("sources", [])}
    known_auth_ids = {str(a["authorization_id"])
                      for a in material.get("authorizations", [])}
    fact_by_id = {str(f["fact_id"]): f for f in material.get("facts", [])}
    for raw_surface, expected in zip(surfaces, expected_surfaces, strict=True):
        surface = _mapping(raw_surface, "E_RAW_SURFACE_OBJECT")
        require(set(surface) == RAW_SURFACE_FIELDS, "E_RAW_SURFACE_FIELDS")
        require((surface.get("surface_kind"), surface.get("text")) == expected,
                "E_RAW_SURFACE_EXACT_JOIN")
        kind = str(surface["surface_kind"])
        fact_ids = _unique_text_list(surface.get("fact_ids"), "E_RAW_SURFACE_FACT_IDS",
                                     allow_empty=kind == "synthetic_disclosure")
        source_ids = _unique_text_list(surface.get("source_ids"),
                                       "E_RAW_SURFACE_SOURCE_IDS",
                                       allow_empty=kind == "synthetic_disclosure")
        auth_ids = _unique_text_list(surface.get("authorization_ids"),
                                     "E_RAW_SURFACE_AUTH_IDS",
                                     allow_empty=kind == "synthetic_disclosure")
        # 事实/来源/授权闭包：表面只能引用材料内对象，
        # 且来源与授权必须等于所绑事实的来源/授权闭包（P4 语义）。
        require(set(fact_ids).issubset(known_fact_ids), "E_SURFACE_FACT_UNKNOWN")
        require(set(source_ids).issubset(known_source_ids), "E_SURFACE_SOURCE_UNKNOWN")
        require(set(auth_ids).issubset(known_auth_ids), "E_SURFACE_AUTH_UNKNOWN")
        if fact_ids:
            closure_sources: set[str] = set()
            closure_auths: set[str] = set()
            for fid in fact_ids:
                fact = fact_by_id[fid]
                closure_sources.update(map(str, fact.get("source_ids", [])))
                closure_auths.update(map(str, fact.get("authorization_ids", [])))
            require(set(source_ids) == closure_sources, "E_SURFACE_SOURCE_CLOSURE")
            require(set(auth_ids) == closure_auths, "E_SURFACE_AUTH_CLOSURE")

    claims = raw.get("semantic_claims")
    require(isinstance(claims, list) and bool(claims), "E_RAW_CLAIMS")
    surface_text = "\n".join(text for _, text in expected_surfaces)
    material_boundary = str(material.get("claim_boundary", ""))
    for raw_claim in claims:
        claim = _mapping(raw_claim, "E_RAW_CLAIM_OBJECT")
        require(set(claim) == RAW_CLAIM_FIELDS, "E_RAW_CLAIM_FIELDS")
        claim_text = _text(claim.get("claim_text"), "E_RAW_CLAIM_TEXT")
        require(claim_text in surface_text, "E_RAW_CLAIM_NOT_ON_SURFACE")
        fact_ids = _unique_text_list(claim.get("fact_ids"), "E_RAW_CLAIM_FACT_IDS")
        require(set(fact_ids).issubset(known_fact_ids), "E_CLAIM_FACT_UNKNOWN")
        _unique_text_list(claim.get("source_ids"), "E_RAW_CLAIM_SOURCE_IDS")
        _unique_text_list(claim.get("authorization_ids"), "E_RAW_CLAIM_AUTH_IDS")
        boundary = _text(claim.get("claim_boundary"), "E_RAW_CLAIM_BOUNDARY")
        require(boundary == material_boundary, "E_RAW_CLAIM_BOUNDARY_EXACT")

    usage = raw.get("semantic_component_usage")
    require(isinstance(usage, list), "E_RAW_COMPONENT_USAGE")
    component_ids: set[str] = set()
    for raw_usage in usage:
        row = _mapping(raw_usage, "E_RAW_COMPONENT_OBJECT")
        require(set(row) == RAW_COMPONENT_FIELDS, "E_RAW_COMPONENT_FIELDS")
        component_id = _text(row.get("component_id"), "E_RAW_COMPONENT_ID")
        require(component_id not in component_ids, "E_RAW_COMPONENT_DUPLICATE")
        component_ids.add(component_id)
        _text(row.get("implementation_note"), "E_RAW_COMPONENT_NOTE")
        ordinals = row.get("surface_ordinals")
        require(isinstance(ordinals, list) and bool(ordinals), "E_RAW_SURFACE_ORDINALS")
        require(all(isinstance(item, int) and not isinstance(item, bool)
                    for item in ordinals), "E_RAW_SURFACE_ORDINALS")
        require(len(ordinals) == len(set(ordinals)), "E_RAW_SURFACE_ORDINALS")
        require(all(1 <= item <= len(expected_surfaces) for item in ordinals),
                "E_RAW_SURFACE_ORDINAL_RANGE")


def serialize(raw: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    """机器信封序列化：只机械生成容器字段，不改作者语义。"""
    validate_raw(raw, request)
    request_id = str(request["request_id"])
    surfaces = []
    for index, raw_surface in enumerate(raw["semantic_surfaces"], 1):
        surface = dict(raw_surface)
        surfaces.append(
            {
                "surface_unit_id": f"{request_id}-SURFACE-{index:02d}",
                "surface_kind": surface["surface_kind"],
                "text": surface["text"],
                "fact_ids": list(surface["fact_ids"]),
                "source_ids": list(surface["source_ids"]),
                "authorization_ids": list(surface["authorization_ids"]),
            }
        )
    claims = []
    for index, raw_claim in enumerate(raw["semantic_claims"], 1):
        claim = dict(raw_claim)
        claims.append(
            {
                "claim_id": f"{request_id}-CLAIM-{index:02d}",
                "claim_text": claim["claim_text"],
                "fact_ids": list(claim["fact_ids"]),
                "source_ids": list(claim["source_ids"]),
                "authorization_ids": list(claim["authorization_ids"]),
                "claim_boundary": claim["claim_boundary"],
            }
        )
    usage = []
    for raw_usage in raw["semantic_component_usage"]:
        row = dict(raw_usage)
        usage.append(
            {
                "component_id": row["component_id"],
                "implementation_surface_unit_ids": [
                    surfaces[index - 1]["surface_unit_id"]
                    for index in row["surface_ordinals"]
                ],
                "implementation_note": row["implementation_note"],
            }
        )
    output: dict[str, Any] = {
        "schema_version": OUTPUT_SCHEMA,
        "task_id": TASK_ID,
        "request_id": request_id,
        "request_digest": request["request_digest"],
        "profile_id": request["profile_id"],
        "assigned_variant": request["assigned_variant"],
        "run_order": request["run_order"],
        "run_id": raw["run_id"],
        "author_identity": request["author_identity"],
        "author_session_logical_id": request["author_session_logical_id"],
        "author_platform_agent_id": request["author_platform_agent_id"],
        "model_capability_id": request["model_capability_id"],
        "reasoning_effort": request["reasoning_effort"],
        "service_tier": request["service_tier"],
        "expression_plan_id": request["expression_plan"]["plan_id"],
        "title": raw["title"],
        "body": copy.deepcopy(raw["body"]),
        "spoken_lines": copy.deepcopy(raw["spoken_lines"]),
        "cta": raw["cta"],
        "visual_execution": copy.deepcopy(raw["visual_execution"]),
        "audio_execution": copy.deepcopy(raw["audio_execution"]),
        "synthetic_disclosure": raw["synthetic_disclosure"],
        "surface_units": surfaces,
        "claims": claims,
        "component_usage": usage,
        "author_attestation": copy.deepcopy(raw["author_attestation"]),
        "synthetic_qualification_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "counts_toward_300": False,
        "output_digest": "",
    }
    output["output_digest"] = object_digest(output, "output_digest")
    return output


__all__ = [
    "AuthorContractError",
    "EXPECTED_ATTESTATION",
    "MODEL_CAPABILITY",
    "NESTED_TYPE_CONTRACT",
    "OUTPUT_SCHEMA",
    "RAW_CLAIM_FIELDS",
    "RAW_COMPONENT_FIELDS",
    "RAW_FIELDS",
    "RAW_SCHEMA",
    "RAW_SURFACE_FIELDS",
    "RAW_TYPE_CONTRACT",
    "REASONING_EFFORT",
    "REQUEST_SCHEMA",
    "ROLE_ALLOWED_SURFACE_KINDS",
    "SERVICE_TIER",
    "SURFACE_KIND_ENUM",
    "TASK_ID",
    "audience_texts",
    "canonical_json",
    "object_digest",
    "require",
    "serialize",
    "sha256_bytes",
    "surface_sequence",
    "validate_raw",
    "validate_request",
]
