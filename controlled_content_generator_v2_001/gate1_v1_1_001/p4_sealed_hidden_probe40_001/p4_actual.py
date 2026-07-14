#!/usr/bin/env python3
"""Pure validation and actual-result builders for Gate 1 P4 stage five."""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from typing import Any

from p4_common import (
    EXPECTED_PROFILES,
    EXPECTED_VARIANTS,
    FROZEN_HASHES,
    GENERATOR_CORE,
    MODEL_CAPABILITY,
    P2_ROOT,
    REASONING_EFFORT,
    ROOT,
    ROUTE_ACTUAL_FREEZE,
    ROUTE_ACTUALS,
    ROUTE_INPUTS,
    SERVICE_TIER,
    TASK_ID,
    bind_digest,
    digest_rows,
    object_digest,
)


P2_ABSOLUTE = ROOT / P2_ROOT
if str(P2_ABSOLUTE) not in sys.path:
    sys.path.insert(0, str(P2_ABSOLUTE))

import p2_generator_core_r6 as p2_core  # noqa: E402


POSITIVE_OUTPUT_SCHEMA = "gate1-p4-positive-first-output-v0.1"
ROUTE_FREEZE_SCHEMA = "gate1-p4-route-actual-freeze-v0.1"
EXIT_EVENT_SCHEMA = "gate1-p4-execution-exit-event-v0.1"
EXPECTED_OUTPUT_FIELDS = frozenset(
    {
        "schema_version",
        "task_id",
        "request_id",
        "request_digest",
        "profile_id",
        "assigned_variant",
        "run_order",
        "run_id",
        "author_identity",
        "author_session_logical_id",
        "author_platform_agent_id",
        "model_capability_id",
        "reasoning_effort",
        "service_tier",
        "title",
        "body",
        "spoken_lines",
        "cta",
        "visual_execution",
        "audio_execution",
        "synthetic_disclosure",
        "surface_units",
        "claims",
        "component_usage",
        "author_attestation",
        "synthetic_qualification_only",
        "publishable",
        "runtime_consumable",
        "counts_toward_300",
        "output_digest",
    }
)
EXPECTED_ATTESTATION = {
    "unbound_fact_added": False,
    "input_backfilled_after_authoring": False,
    "external_service_called": False,
    "second_candidate_generated": False,
    "review_performed_by_author": False,
}
SURFACE_KINDS = frozenset(
    {
        "synthetic_disclosure",
        "title",
        "body",
        "spoken_line",
        "cta",
        "visual_execution",
        "audio_execution",
    }
)
ROLE_ALLOWED_SURFACES = {
    "scene": frozenset({"title", "body", "visual_execution"}),
    "trigger": frozenset({"title", "body", "spoken_line", "visual_execution"}),
    "observable_action": frozenset({"body", "spoken_line", "visual_execution"}),
    "transition": frozenset({"body", "visual_execution"}),
    "visual_beat": frozenset({"body", "visual_execution"}),
    "capture_instruction": frozenset({"visual_execution", "audio_execution"}),
    "professional_judgment": frozenset({"body", "spoken_line"}),
    "audience_facing_reasoning_move": frozenset(
        {"body", "spoken_line", "visual_execution"}
    ),
    "closing": frozenset({"body", "spoken_line", "cta", "visual_execution"}),
    "narrative_mechanism_operator": frozenset(
        {"body", "spoken_line", "visual_execution"}
    ),
    "information_order_operator": frozenset(
        {"title", "body", "spoken_line", "visual_execution"}
    ),
    "visual_subject_operator": frozenset({"body", "visual_execution"}),
    "sound_subject_operator": frozenset({"spoken_line", "audio_execution"}),
    "rhythm_operator": frozenset(
        {"body", "spoken_line", "visual_execution", "audio_execution"}
    ),
    "ending_operator": frozenset({"body", "spoken_line", "cta", "visual_execution"}),
}
EXIT_OBSERVATION_FIELDS = frozenset(
    {
        "event_id",
        "exit_class",
        "platform_agent_id",
        "model_capability_id",
        "request_count",
        "response_count",
        "external_provider_request_count",
        "external_provider_response_count",
        "external_api_call_count",
        "credential_read_count",
        "network_dispatch_count",
    }
)


class P4ActualValidationError(ValueError):
    """Fail-closed validation error with a stable stage-five reason code."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise P4ActualValidationError(f"{code}{suffix}")


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    require(isinstance(value, Mapping), code)
    return value


def _text(value: Any, code: str, *, allow_empty: bool = False) -> str:
    require(isinstance(value, str), code)
    require(allow_empty or bool(value.strip()), code)
    return value


def _text_list(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), code)
    rows = [_text(item, code) for item in value]
    require(allow_empty or bool(rows), code)
    return rows


def _unique_text_ids(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), code)
    rows = [_text(item, code) for item in value]
    require(allow_empty or bool(rows), code)
    require(len(rows) == len(set(rows)), code)
    return rows


def _validate_identity_config(value: Mapping[str, Any]) -> dict[str, str]:
    required = {
        "author_identity",
        "author_session_logical_id",
        "author_platform_agent_id",
        "model_capability_id",
        "reasoning_effort",
        "service_tier",
    }
    require(set(value) == required, "E_P4_IDENTITY_CONFIG_FIELDS")
    config = {key: _text(value[key], "E_P4_IDENTITY_CONFIG_VALUE") for key in required}
    require(config["model_capability_id"] == MODEL_CAPABILITY, "E_P4_MODEL_CAPABILITY")
    require(config["reasoning_effort"] == REASONING_EFFORT, "E_P4_REASONING_EFFORT")
    require(config["service_tier"] == SERVICE_TIER, "E_P4_SERVICE_TIER")
    return config


def build_author_identity_config(
    requests: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    """Derive the single frozen author identity/configuration from requests."""

    require(len(requests) == 20, "E_P4_IDENTITY_REQUEST_COUNT")
    fields = (
        "author_identity",
        "author_session_logical_id",
        "author_platform_agent_id",
        "model_capability_id",
        "reasoning_effort",
        "service_tier",
    )
    first = {field: requests[0].get(field) for field in fields}
    for request in requests:
        require(
            {field: request.get(field) for field in fields} == first,
            "E_P4_IDENTITY_REQUEST_DRIFT",
        )
        contract = _mapping(
            request.get("author_output_contract"), "E_P4_AUTHOR_OUTPUT_CONTRACT"
        )
        require(
            contract.get("one_first_semantic_output_only") is True,
            "E_P4_SINGLE_OUTPUT_CONTRACT",
        )
        require(
            contract.get("author_may_not_review_or_approve") is True,
            "E_P4_AUTHOR_REVIEW_BOUNDARY",
        )
    return _validate_identity_config(first)


def _surface_sequence(output: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows = [
        ("synthetic_disclosure", str(output["synthetic_disclosure"])),
        ("title", str(output["title"])),
    ]
    rows.extend(("body", text) for text in output["body"])
    rows.extend(("spoken_line", text) for text in output["spoken_lines"])
    if output["cta"]:
        rows.append(("cta", str(output["cta"])))
    rows.extend(("visual_execution", text) for text in output["visual_execution"])
    rows.extend(("audio_execution", text) for text in output["audio_execution"])
    return rows


def _validate_output_identity(
    output: Mapping[str, Any],
    request: Mapping[str, Any],
    identity_config: Mapping[str, Any],
) -> None:
    for field, expected in identity_config.items():
        require(output.get(field) == expected, "E_P4_OUTPUT_IDENTITY", field)
        require(request.get(field) == expected, "E_P4_REQUEST_IDENTITY", field)


def _validate_surface_units(
    output: Mapping[str, Any], request: Mapping[str, Any]
) -> tuple[dict[str, Mapping[str, Any]], set[str]]:
    expected_sequence = _surface_sequence(output)
    units = output.get("surface_units")
    require(isinstance(units, list), "E_P4_SURFACE_UNITS")
    require(len(units) == len(expected_sequence), "E_P4_SURFACE_COUNT")

    material = _mapping(request.get("typed_material"), "E_P4_TYPED_MATERIAL")
    facts = material.get("facts")
    sources = material.get("sources")
    authorizations = material.get("authorizations")
    require(isinstance(facts, list), "E_P4_FACTS")
    require(isinstance(sources, list), "E_P4_SOURCES")
    require(isinstance(authorizations, list), "E_P4_AUTHORIZATIONS")
    fact_by_id = {
        str(_mapping(row, "E_P4_FACT_OBJECT").get("fact_id")): row for row in facts
    }
    source_ids = {
        str(_mapping(row, "E_P4_SOURCE_OBJECT").get("source_id")) for row in sources
    }
    authorization_ids = {
        str(_mapping(row, "E_P4_AUTH_OBJECT").get("authorization_id"))
        for row in authorizations
    }
    require(len(fact_by_id) == len(facts), "E_P4_FACT_ID_UNIQUE")
    require(len(source_ids) == len(sources), "E_P4_SOURCE_ID_UNIQUE")
    require(len(authorization_ids) == len(authorizations), "E_P4_AUTH_ID_UNIQUE")

    surface_by_id: dict[str, Mapping[str, Any]] = {}
    referenced_fact_ids: set[str] = set()
    for index, (raw_unit, expected) in enumerate(
        zip(units, expected_sequence, strict=True), 1
    ):
        unit = _mapping(raw_unit, "E_P4_SURFACE_OBJECT")
        require(
            set(unit)
            == {
                "surface_unit_id",
                "surface_kind",
                "text",
                "fact_ids",
                "source_ids",
                "authorization_ids",
            },
            "E_P4_SURFACE_FIELDS",
        )
        unit_id = _text(unit["surface_unit_id"], "E_P4_SURFACE_ID")
        require(
            unit_id == f"{output['request_id']}-SURFACE-{index:02d}",
            "E_P4_SURFACE_ID",
        )
        require(unit_id not in surface_by_id, "E_P4_SURFACE_ID_UNIQUE")
        kind = unit.get("surface_kind")
        require(kind in SURFACE_KINDS, "E_P4_SURFACE_KIND")
        require((kind, unit.get("text")) == expected, "E_P4_SURFACE_EXACT_JOIN")
        fact_ids = _unique_text_ids(
            unit.get("fact_ids"),
            "E_P4_SURFACE_FACT_IDS",
            allow_empty=kind == "synthetic_disclosure",
        )
        bound_source_ids = _unique_text_ids(
            unit.get("source_ids"),
            "E_P4_SURFACE_SOURCE_IDS",
            allow_empty=kind == "synthetic_disclosure",
        )
        bound_authorization_ids = _unique_text_ids(
            unit.get("authorization_ids"),
            "E_P4_SURFACE_AUTH_IDS",
            allow_empty=kind == "synthetic_disclosure",
        )
        require(set(fact_ids).issubset(fact_by_id), "E_P4_SURFACE_FACT_REF", unit_id)
        require(
            set(bound_source_ids).issubset(source_ids),
            "E_P4_SURFACE_SOURCE_REF",
            unit_id,
        )
        require(
            set(bound_authorization_ids).issubset(authorization_ids),
            "E_P4_SURFACE_AUTH_REF",
            unit_id,
        )
        expected_source_ids: set[str] = set()
        expected_authorization_ids: set[str] = set()
        for fact_id in fact_ids:
            fact = _mapping(fact_by_id[fact_id], "E_P4_FACT_OBJECT")
            fact_sources = set(
                _unique_text_ids(fact.get("source_ids"), "E_P4_FACT_SOURCE_IDS")
            )
            fact_authorizations = set(
                _unique_text_ids(fact.get("authorization_ids"), "E_P4_FACT_AUTH_IDS")
            )
            expected_source_ids.update(fact_sources)
            expected_authorization_ids.update(fact_authorizations)
        require(
            set(bound_source_ids) == expected_source_ids,
            "E_P4_FACT_SOURCE_CLOSURE",
            unit_id,
        )
        require(
            set(bound_authorization_ids) == expected_authorization_ids,
            "E_P4_FACT_AUTH_CLOSURE",
            unit_id,
        )
        referenced_fact_ids.update(fact_ids)
        surface_by_id[unit_id] = unit

    requirements = request.get("product_core_requirements")
    require(
        isinstance(requirements, list) and bool(requirements), "E_P4_CORE_REQUIREMENTS"
    )
    for raw_requirement in requirements:
        requirement = _mapping(raw_requirement, "E_P4_CORE_REQUIREMENT_OBJECT")
        required_fact_ids = set(
            _unique_text_ids(
                requirement.get("fact_ids"), "E_P4_CORE_REQUIREMENT_FACT_IDS"
            )
        )
        require(
            required_fact_ids.issubset(referenced_fact_ids),
            "E_P4_PRODUCT_CORE_FACT_COVERAGE",
            str(requirement.get("requirement_id")),
        )
    return surface_by_id, referenced_fact_ids


def _validate_claims(output: Mapping[str, Any], request: Mapping[str, Any]) -> None:
    material = _mapping(request["typed_material"], "E_P4_TYPED_MATERIAL")
    fact_by_id = {str(row["fact_id"]): row for row in material["facts"]}
    source_ids = {str(row["source_id"]) for row in material["sources"]}
    authorization_ids = {
        str(row["authorization_id"]) for row in material["authorizations"]
    }
    surface_text = "\n".join(text for _, text in _surface_sequence(output))
    claims = output.get("claims")
    require(isinstance(claims, list) and bool(claims), "E_P4_CLAIMS")
    claim_ids: set[str] = set()
    for raw_claim in claims:
        claim = _mapping(raw_claim, "E_P4_CLAIM_OBJECT")
        require(
            set(claim)
            == {
                "claim_id",
                "claim_text",
                "fact_ids",
                "source_ids",
                "authorization_ids",
                "claim_boundary",
            },
            "E_P4_CLAIM_FIELDS",
        )
        claim_id = _text(claim["claim_id"], "E_P4_CLAIM_ID")
        require(claim_id not in claim_ids, "E_P4_CLAIM_ID_UNIQUE")
        claim_ids.add(claim_id)
        claim_text = _text(claim["claim_text"], "E_P4_CLAIM_TEXT")
        require(claim_text in surface_text, "E_P4_CLAIM_NOT_ON_SURFACE", claim_id)
        bound_fact_ids = _unique_text_ids(claim["fact_ids"], "E_P4_CLAIM_FACT_IDS")
        bound_source_ids = _unique_text_ids(
            claim["source_ids"], "E_P4_CLAIM_SOURCE_IDS"
        )
        bound_authorization_ids = _unique_text_ids(
            claim["authorization_ids"], "E_P4_CLAIM_AUTH_IDS"
        )
        require(set(bound_fact_ids).issubset(fact_by_id), "E_P4_CLAIM_FACT_REF")
        require(set(bound_source_ids).issubset(source_ids), "E_P4_CLAIM_SOURCE_REF")
        require(
            set(bound_authorization_ids).issubset(authorization_ids),
            "E_P4_CLAIM_AUTH_REF",
        )
        expected_source_ids: set[str] = set()
        expected_authorization_ids: set[str] = set()
        for fact_id in bound_fact_ids:
            fact = _mapping(fact_by_id[fact_id], "E_P4_FACT_OBJECT")
            expected_source_ids.update(map(str, fact["source_ids"]))
            expected_authorization_ids.update(map(str, fact["authorization_ids"]))
        require(
            set(bound_source_ids) == expected_source_ids,
            "E_P4_CLAIM_FACT_SOURCE_CLOSURE",
            claim_id,
        )
        require(
            set(bound_authorization_ids) == expected_authorization_ids,
            "E_P4_CLAIM_FACT_AUTH_CLOSURE",
            claim_id,
        )
        require(
            claim["claim_boundary"] == material.get("claim_boundary"),
            "E_P4_CLAIM_BOUNDARY",
            claim_id,
        )


def _validate_component_usage(
    output: Mapping[str, Any],
    request: Mapping[str, Any],
    surface_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    structure = _mapping(request.get("structure_contract"), "E_P4_STRUCTURE_CONTRACT")
    require(isinstance(structure.get("axis_values"), Mapping), "E_P4_AXIS_VALUES")
    require(isinstance(structure.get("axis_programs"), Mapping), "E_P4_AXIS_PROGRAMS")
    approved = request.get("approved_components")
    require(isinstance(approved, list) and bool(approved), "E_P4_APPROVED_COMPONENTS")
    approved_by_id = {
        str(_mapping(row, "E_P4_APPROVED_COMPONENT_OBJECT").get("component_id")): row
        for row in approved
    }
    require(len(approved_by_id) == len(approved), "E_P4_APPROVED_COMPONENT_UNIQUE")
    usage = output.get("component_usage")
    require(isinstance(usage, list), "E_P4_COMPONENT_USAGE")
    usage_by_id: dict[str, Mapping[str, Any]] = {}
    for raw_usage in usage:
        row = _mapping(raw_usage, "E_P4_COMPONENT_USAGE_OBJECT")
        require(
            set(row)
            == {
                "component_id",
                "implementation_surface_unit_ids",
                "implementation_note",
            },
            "E_P4_COMPONENT_USAGE_FIELDS",
        )
        component_id = _text(row["component_id"], "E_P4_COMPONENT_ID")
        require(component_id not in usage_by_id, "E_P4_COMPONENT_USAGE_UNIQUE")
        pointers = _unique_text_ids(
            row["implementation_surface_unit_ids"], "E_P4_COMPONENT_POINTERS"
        )
        require(set(pointers).issubset(surface_by_id), "E_P4_COMPONENT_POINTER_REF")
        _text(row["implementation_note"], "E_P4_COMPONENT_NOTE")
        usage_by_id[component_id] = row
    require(set(usage_by_id) == set(approved_by_id), "E_P4_COMPONENT_USAGE_COVERAGE")
    distinct_pointers = {
        str(pointer)
        for row in usage_by_id.values()
        for pointer in row["implementation_surface_unit_ids"]
    }
    require(
        len(distinct_pointers) >= max(2, len(usage_by_id) // 3),
        "E_P4_COMPONENT_EVIDENCE_COLLAPSE",
    )

    core_fact_ids = {
        str(fact_id)
        for requirement in request["product_core_requirements"]
        for fact_id in requirement["fact_ids"]
    }
    material = _mapping(request.get("typed_material"), "E_P4_TYPED_MATERIAL")
    fact_ids_by_slot: dict[str, set[str]] = {}
    for raw_fact in material["facts"]:
        fact = _mapping(raw_fact, "E_P4_FACT_OBJECT")
        fact_ids_by_slot.setdefault(str(fact.get("slot_id")), set()).add(
            str(fact.get("fact_id"))
        )
    for component_id, raw_component in approved_by_id.items():
        component = _mapping(raw_component, "E_P4_APPROVED_COMPONENT_OBJECT")
        pointers = usage_by_id[component_id]["implementation_surface_unit_ids"]
        units = [surface_by_id[str(pointer)] for pointer in pointers]
        realized_fact_ids = {
            str(fact_id) for unit in units for fact_id in unit["fact_ids"]
        }
        required_slots = set(map(str, component.get("required_fact_slots", [])))
        component_fact_ids = {
            fact_id
            for slot in required_slots
            for fact_id in fact_ids_by_slot.get(slot, set())
        }
        allowed_fact_ids = component_fact_ids | core_fact_ids
        require(
            bool(realized_fact_ids.intersection(allowed_fact_ids)),
            "E_P4_COMPONENT_EVIDENCE_FACT",
            component_id,
        )
        role = str(component.get("component_role"))
        require(role in ROLE_ALLOWED_SURFACES, "E_P4_COMPONENT_ROLE", role)
        require(
            any(
                str(unit["surface_kind"]) in ROLE_ALLOWED_SURFACES[role]
                for unit in units
            ),
            "E_P4_COMPONENT_SURFACE_ROLE",
            component_id,
        )


def validate_positive_output(
    output: Mapping[str, Any],
    request: Mapping[str, Any],
    identity_config: Mapping[str, Any] | None = None,
) -> None:
    """Validate one immutable first candidate against its frozen request."""

    if identity_config is None:
        identity = _validate_identity_config(
            {
                field: request.get(field)
                for field in (
                    "author_identity",
                    "author_session_logical_id",
                    "author_platform_agent_id",
                    "model_capability_id",
                    "reasoning_effort",
                    "service_tier",
                )
            }
        )
    else:
        identity = _validate_identity_config(identity_config)
    require(set(output) == EXPECTED_OUTPUT_FIELDS, "E_P4_OUTPUT_FIELD_SET")
    require(
        output.get("schema_version") == POSITIVE_OUTPUT_SCHEMA, "E_P4_OUTPUT_SCHEMA"
    )
    require(output.get("task_id") == TASK_ID, "E_P4_OUTPUT_TASK")
    require(request.get("task_id") == TASK_ID, "E_P4_REQUEST_TASK")
    for field in (
        "request_id",
        "request_digest",
        "profile_id",
        "assigned_variant",
        "run_order",
    ):
        require(output.get(field) == request.get(field), "E_P4_REQUEST_BINDING", field)
    contract = _mapping(
        request.get("author_output_contract"), "E_P4_AUTHOR_OUTPUT_CONTRACT"
    )
    require(
        contract.get("one_first_semantic_output_only") is True,
        "E_P4_SINGLE_OUTPUT_CONTRACT",
    )
    require(
        contract.get("author_may_not_review_or_approve") is True,
        "E_P4_AUTHOR_REVIEW_BOUNDARY",
    )
    _text(output.get("run_id"), "E_P4_RUN_ID")
    _validate_output_identity(output, request, identity)
    require(output.get("synthetic_qualification_only") is True, "E_P4_NAMESPACE")
    for field in ("publishable", "runtime_consumable", "counts_toward_300"):
        require(output.get(field) is False, "E_P4_READINESS_BOUNDARY", field)
    for field in ("publishable", "runtime_consumable", "may_enter_300"):
        require(contract.get(field) is False, "E_P4_REQUEST_BOUNDARY", field)
    _text(output.get("title"), "E_P4_TITLE")
    _text_list(output.get("body"), "E_P4_BODY")
    _text_list(output.get("spoken_lines"), "E_P4_SPOKEN", allow_empty=True)
    _text(output.get("cta"), "E_P4_CTA", allow_empty=True)
    _text_list(output.get("visual_execution"), "E_P4_VISUAL")
    _text_list(output.get("audio_execution"), "E_P4_AUDIO", allow_empty=True)
    disclosure = _text(output.get("synthetic_disclosure"), "E_P4_DISCLOSURE")
    require(
        "合成" in disclosure and ("测试" in disclosure or "非真实" in disclosure),
        "E_P4_DISCLOSURE_MEANING",
    )
    surface_by_id, _ = _validate_surface_units(output, request)
    _validate_claims(output, request)
    _validate_component_usage(output, request, surface_by_id)
    require(
        output.get("author_attestation") == EXPECTED_ATTESTATION, "E_P4_ATTESTATION"
    )
    require(
        output.get("output_digest") == object_digest(dict(output), "output_digest"),
        "E_P4_OUTPUT_DIGEST",
    )


def validate_positive_outputs(
    outputs: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, Any]],
    identity_config: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate all 20 first outputs and return detached row copies."""

    require(len(outputs) == len(requests) == 20, "E_P4_POSITIVE_COUNT")
    identity = (
        build_author_identity_config(requests)
        if identity_config is None
        else _validate_identity_config(identity_config)
    )
    request_by_id = {str(row.get("request_id")): row for row in requests}
    require(len(request_by_id) == 20, "E_P4_REQUEST_ID_UNIQUE")
    seen_ids: set[str] = set()
    seen_run_ids: set[str] = set()
    run_orders: list[int] = []
    validated: list[dict[str, Any]] = []
    for output in outputs:
        request_id = str(output.get("request_id"))
        require(request_id not in seen_ids, "E_P4_OUTPUT_ID_UNIQUE")
        require(request_id in request_by_id, "E_P4_OUTPUT_REQUEST")
        validate_positive_output(output, request_by_id[request_id], identity)
        run_id = str(output["run_id"])
        require(run_id not in seen_run_ids, "E_P4_RUN_ID_UNIQUE")
        run_order = output["run_order"]
        require(
            isinstance(run_order, int) and not isinstance(run_order, bool),
            "E_P4_RUN_ORDER",
        )
        require(1 <= run_order <= 20, "E_P4_RUN_ORDER_RANGE")
        seen_ids.add(request_id)
        seen_run_ids.add(run_id)
        run_orders.append(run_order)
        validated.append(dict(output))
    require(seen_ids == set(request_by_id), "E_P4_OUTPUT_COVERAGE")
    require(run_orders == list(range(1, 21)), "E_P4_RUN_ORDER_SEQUENCE")
    require(
        {str(row["profile_id"]) for row in outputs} == set(EXPECTED_PROFILES),
        "E_P4_PROFILE_COVERAGE",
    )
    variant_counts = {
        variant: sum(row.get("assigned_variant") == variant for row in outputs)
        for variant in EXPECTED_VARIANTS
    }
    require(variant_counts == EXPECTED_VARIANTS, "E_P4_VARIANT_BALANCE")
    return validated


def _profile_map(profiles: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    rows = {str(row.get("content_product_type_id")): row for row in profiles}
    require(len(rows) == len(profiles) == 20, "E_P4_PROFILE_REGISTRY")
    require(set(rows) == set(EXPECTED_PROFILES), "E_P4_PROFILE_REGISTRY_COVERAGE")
    return rows


def build_route_actuals(
    route_inputs: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Evaluate the 20 frozen route inputs with the frozen R6 route engine."""

    require(len(route_inputs) == 20, "E_P4_ROUTE_INPUT_COUNT")
    profile_by_id = _profile_map(profiles)
    case_ids = [str(row.get("case_id")) for row in route_inputs]
    require(len(case_ids) == len(set(case_ids)), "E_P4_ROUTE_CASE_UNIQUE")
    for row in route_inputs:
        require(row.get("task_id") == TASK_ID, "E_P4_ROUTE_INPUT_TASK")
        require(row.get("gold_fields_present") is False, "E_P4_ROUTE_INPUT_BOUNDARY")
        require(
            row.get("input_digest") == object_digest(dict(row), "input_digest"),
            "E_P4_ROUTE_INPUT_DIGEST",
        )
    require(
        [row.get("run_order") for row in route_inputs] == list(range(21, 41)),
        "E_P4_ROUTE_RUN_ORDER",
    )
    require(
        {str(row.get("profile_id")) for row in route_inputs} == set(EXPECTED_PROFILES),
        "E_P4_ROUTE_PROFILE_COVERAGE",
    )
    actuals = [
        p2_core.evaluate_route(row, profile_by_id[str(row.get("profile_id"))])
        for row in route_inputs
    ]
    require(
        [str(row.get("case_id")) for row in actuals] == case_ids,
        "E_P4_ROUTE_RESULT_ORDER",
    )
    for actual in actuals:
        require(actual.get("task_id") == p2_core.TASK_ID, "E_P4_ROUTE_ENGINE_TASK")
        require(
            actual.get("route_result_digest")
            == p2_core.object_digest(dict(actual), "route_result_digest"),
            "E_P4_ROUTE_RESULT_DIGEST",
        )
        require(
            not any(
                actual.get(field)
                for field in (
                    "audience_title_created",
                    "audience_body_created",
                    "spoken_script_created",
                    "runtime_plan_created",
                    "runtime_consumable",
                )
            ),
            "E_P4_ROUTE_AUDIENCE_CONTENT",
        )
    return actuals


def build_route_actual_freeze(
    route_inputs: Sequence[Mapping[str, Any]],
    route_actuals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the freeze receipt for bytes the runner will materialize."""

    require(len(route_inputs) == len(route_actuals) == 20, "E_P4_ROUTE_FREEZE_COUNT")
    require(
        [str(row.get("case_id")) for row in route_inputs]
        == [str(row.get("case_id")) for row in route_actuals],
        "E_P4_ROUTE_FREEZE_BINDING",
    )
    freeze = {
        "schema_version": ROUTE_FREEZE_SCHEMA,
        "task_id": TASK_ID,
        "actual_engine_module": GENERATOR_CORE.as_posix(),
        "actual_engine_function": "evaluate_route",
        "actual_engine_sha256": FROZEN_HASHES[GENERATOR_CORE],
        "actual_engine_inputs": ROUTE_INPUTS.as_posix(),
        "actual_engine_input_sha256": digest_rows(list(route_inputs)),
        "actual_result_path": ROUTE_ACTUALS.as_posix(),
        "actual_result_sha256": digest_rows(list(route_actuals)),
        "actual_result_count": len(route_actuals),
        "actual_result_frozen_before_independent_comparison": True,
        "freeze_path": ROUTE_ACTUAL_FREEZE.as_posix(),
        "gold_answer_loaded_by_actual_engine": False,
        "gold_answer_compared_after_actual_freeze_only": True,
    }
    return bind_digest(freeze, "actual_freeze_digest")


def build_route_actual_artifacts(
    route_inputs: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return route rows and their freeze receipt for atomic runner writes."""

    actuals = build_route_actuals(route_inputs, profiles)
    return actuals, build_route_actual_freeze(route_inputs, actuals)


def _non_negative_int(value: Any, code: str, detail: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), code, detail)
    require(value >= 0, code, detail)
    return value


def build_execution_exit_events(
    execution_observations: Sequence[Mapping[str, Any]],
    positive_outputs: Sequence[Mapping[str, Any]],
    route_inputs: Sequence[Mapping[str, Any]],
    route_actuals: Sequence[Mapping[str, Any]],
    identity_config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Bind observed role exits and the locally executed route-engine exit."""

    identity = _validate_identity_config(identity_config)
    require(len(execution_observations) >= 3, "E_P4_EXIT_ROLE_OBSERVATION_COUNT")
    count_fields = (
        "request_count",
        "response_count",
        "external_provider_request_count",
        "external_provider_response_count",
        "external_api_call_count",
        "credential_read_count",
        "network_dispatch_count",
    )
    observed_events: list[dict[str, Any]] = []
    for raw_observation in execution_observations:
        require(
            set(raw_observation) == EXIT_OBSERVATION_FIELDS,
            "E_P4_EXIT_OBSERVATION_FIELDS",
        )
        event = dict(raw_observation)
        for field in count_fields:
            event[field] = _non_negative_int(event[field], "E_P4_EXIT_COUNT", field)
        require(
            event["external_provider_response_count"]
            <= event["external_provider_request_count"],
            "E_P4_EXIT_PROVIDER_COUNT",
        )
        require(
            event["external_api_call_count"] <= event["network_dispatch_count"],
            "E_P4_EXIT_NETWORK_COUNT",
        )
        event.update(
            {
                "schema_version": EXIT_EVENT_SCHEMA,
                "task_id": TASK_ID,
                "evidence_kind": "OBSERVED_EXECUTION_ROLE",
                "evidence_count": event["response_count"],
                "evidence_sha256": digest_rows([dict(raw_observation)]),
            }
        )
        observed_events.append(bind_digest(event, "event_digest"))

    authors = [
        event
        for event in observed_events
        if event["exit_class"] == "CONTROLLED_EXECUTION_AGENT"
    ]
    require(len(authors) == 1, "E_P4_AUTHOR_EXIT_EVENT_COUNT")
    author = authors[0]
    require(
        author["request_count"] == len(positive_outputs) == 20,
        "E_P4_AUTHOR_REQUEST_COUNT",
    )
    require(
        author["response_count"] == len(positive_outputs), "E_P4_AUTHOR_RESPONSE_COUNT"
    )
    require(
        author["platform_agent_id"] == identity["author_platform_agent_id"],
        "E_P4_EXIT_AUTHOR_AGENT",
    )
    require(
        author["model_capability_id"] == identity["model_capability_id"],
        "E_P4_EXIT_AUTHOR_MODEL",
    )
    attested_external_count = sum(
        _mapping(row.get("author_attestation"), "E_P4_ATTESTATION").get(
            "external_service_called"
        )
        is True
        for row in positive_outputs
    )
    require(
        (attested_external_count == 0)
        == (
            author["external_provider_request_count"] == 0
            and author["external_api_call_count"] == 0
            and author["network_dispatch_count"] == 0
        ),
        "E_P4_EXIT_ATTESTATION_CONSISTENCY",
    )
    require(len(route_inputs) == len(route_actuals) == 20, "E_P4_ROUTE_EXIT_COUNT")
    route_event = {
        "schema_version": EXIT_EVENT_SCHEMA,
        "event_id": "P4-EXIT-ROUTE-001",
        "task_id": TASK_ID,
        "exit_class": "LOCAL_DETERMINISTIC_ROUTE_ENGINE",
        "platform_agent_id": None,
        "model_capability_id": None,
        "request_count": len(route_inputs),
        "response_count": len(route_actuals),
        "external_provider_request_count": 0,
        "external_provider_response_count": 0,
        "external_api_call_count": 0,
        "credential_read_count": 0,
        "network_dispatch_count": 0,
        "evidence_kind": "ROUTE_ACTUALS",
        "evidence_count": len(route_actuals),
        "evidence_sha256": digest_rows(list(route_actuals)),
    }
    route_event = bind_digest(route_event, "event_digest")
    events = [*observed_events, route_event]
    require(
        len({str(row["event_id"]) for row in events}) == len(events),
        "E_P4_EXIT_EVENT_ID_UNIQUE",
    )
    return events


def derive_execution_exit_counts(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, int | bool]:
    """Derive every exit count exclusively from validated event rows."""

    require(bool(events), "E_P4_EXIT_EVENTS_EMPTY")
    count_fields = (
        "request_count",
        "response_count",
        "external_provider_request_count",
        "external_provider_response_count",
        "external_api_call_count",
        "credential_read_count",
        "network_dispatch_count",
    )
    seen: set[str] = set()
    totals = {field: 0 for field in count_fields}
    for event in events:
        event_id = _text(event.get("event_id"), "E_P4_EXIT_EVENT_ID")
        require(event_id not in seen, "E_P4_EXIT_EVENT_ID_UNIQUE")
        seen.add(event_id)
        require(
            event.get("schema_version") == EXIT_EVENT_SCHEMA, "E_P4_EXIT_EVENT_SCHEMA"
        )
        require(event.get("task_id") == TASK_ID, "E_P4_EXIT_EVENT_TASK")
        require(
            event.get("event_digest") == object_digest(dict(event), "event_digest"),
            "E_P4_EXIT_EVENT_DIGEST",
        )
        for field in count_fields:
            totals[field] += _non_negative_int(
                event.get(field), "E_P4_EXIT_COUNT", field
            )
    return {
        "event_count": len(events),
        **totals,
        "derived_from_event_log": True,
    }


__all__ = [
    "P4ActualValidationError",
    "build_author_identity_config",
    "build_execution_exit_events",
    "build_route_actual_artifacts",
    "build_route_actual_freeze",
    "build_route_actuals",
    "derive_execution_exit_counts",
    "validate_positive_output",
    "validate_positive_outputs",
]
