#!/usr/bin/env python3
"""Typed, provider-free Gate 1 generator control core for P2 validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, NoReturn


TASK_ID = "GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001"
GENERATOR_VERSION = "gate1-v1.1-p2-successor-v0.1"
REQUEST_SCHEMA_VERSION = "gate1-typed-author-request-v0.1"
ROUTE_ENGINE_VERSION = "gate1-v1.1-route-successor-v0.1"

AUTHORIZATION_BLOCKING_RISKS = frozenset(
    {
        "PRIVACY_AUTHORIZATION_FAILURE",
        "ROLE_AUTHORITY_EXPANSION",
        "UNAUTHORIZED_BRAND_CLAIM",
    }
)
FACT_BLOCKING_RISKS = frozenset(
    {
        "FABRICATED_EVENT",
        "FABRICATED_PERSON_EXPERIENCE",
        "UNSUPPORTED_NUMERIC_OR_PERFORMANCE_CLAIM",
    }
)


class Gate1ValidationError(ValueError):
    """Raised when an explicitly typed Gate 1 object violates its contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    return digest_object(
        {key: child for key, child in value.items() if key != digest_key}
    )


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise Gate1ValidationError(f"{code}:{detail}" if detail else code)


def _typed_rows(value: Any, object_type: str, id_key: str) -> list[dict[str, Any]]:
    require(isinstance(value, list), "E_TYPED_LIST", object_type)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        require(isinstance(item, dict), "E_TYPED_OBJECT", object_type)
        require(item.get("object_type") == object_type, "E_OBJECT_TYPE", object_type)
        object_id = item.get(id_key)
        require(isinstance(object_id, str) and object_id, "E_OBJECT_ID", id_key)
        require(object_id not in seen, "E_OBJECT_DUPLICATE", object_id)
        seen.add(object_id)
        rows.append(item)
    return rows


def profile_required_slots(profile: Mapping[str, Any]) -> dict[str, list[str]]:
    requirements = profile.get("input_requirements")
    require(isinstance(requirements, Mapping), "E_PROFILE_INPUT_REQUIREMENTS")
    return {
        "source": list(map(str, requirements.get("required_source_slots", []))),
        "fact": list(map(str, requirements.get("required_fact_slots", []))),
        "authorization": list(
            map(str, requirements.get("required_authorization_slots", []))
        ),
    }


def build_local_typed_material(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Build a nonpublishable typed fixture without supplying real brand facts."""

    profile_id = str(profile["content_product_type_id"])
    slots = profile_required_slots(profile)
    sources = [
        {
            "object_type": "SOURCE_OBJECT",
            "source_id": f"LOCAL-SOURCE-{profile_id}-{index:02d}",
            "slot_id": slot_id,
            "source_kind": "SYNTHETIC_STRUCTURAL_FIXTURE",
            "content_digest": digest_object(
                {"profile_id": profile_id, "slot_id": slot_id, "kind": "source"}
            ),
            "synthetic_test_only": True,
            "may_supply_real_brand_fact": False,
        }
        for index, slot_id in enumerate(slots["source"], 1)
    ]
    authorizations = [
        {
            "object_type": "AUTHORIZATION_OBJECT",
            "authorization_id": f"LOCAL-AUTH-{profile_id}-{index:02d}",
            "slot_id": slot_id,
            "subject_id": f"SYNTHETIC-SUBJECT-{profile_id}",
            "purpose": "GATE1_LOCAL_STRUCTURAL_TEST",
            "scope": {
                "profile_id": profile_id,
                "audience_surface_allowed": False,
                "publication_allowed": False,
            },
            "validity_condition": "SYNTHETIC_TEST_WINDOW_ONLY",
            "synthetic_test_only": True,
        }
        for index, slot_id in enumerate(slots["authorization"], 1)
    ]
    source_ids = [row["source_id"] for row in sources]
    authorization_ids = [row["authorization_id"] for row in authorizations]
    facts = [
        {
            "object_type": "FACT_OBJECT",
            "fact_id": f"LOCAL-FACT-{profile_id}-{index:02d}",
            "slot_id": slot_id,
            "source_ids": source_ids,
            "authorization_ids": authorization_ids,
            "claim_boundary": "SYNTHETIC_STRUCTURE_ONLY_NO_AUDIENCE_CLAIM",
            "fact_value_digest": digest_object(
                {"profile_id": profile_id, "slot_id": slot_id, "kind": "fact"}
            ),
            "synthetic_test_only": True,
            "may_be_treated_as_brand_truth": False,
        }
        for index, slot_id in enumerate(slots["fact"], 1)
    ]
    material: dict[str, Any] = {
        "schema_version": "v0.1",
        "material_id": f"LOCAL-TYPED-MATERIAL-{profile_id}",
        "profile_id": profile_id,
        "sources": sources,
        "facts": facts,
        "authorizations": authorizations,
        "claim_boundary": "SYNTHETIC_STRUCTURE_ONLY_NO_AUDIENCE_CLAIM",
        "synthetic_test_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "may_enter_300": False,
    }
    material["material_digest"] = object_digest(material, "material_digest")
    return material


def validate_typed_material(
    material: Mapping[str, Any], profile: Mapping[str, Any]
) -> None:
    profile_id = str(profile["content_product_type_id"])
    require(material.get("profile_id") == profile_id, "E_MATERIAL_PROFILE")
    require(
        material.get("material_digest") == object_digest(material, "material_digest"),
        "E_MATERIAL_DIGEST",
    )
    require(material.get("synthetic_test_only") is True, "E_MATERIAL_NAMESPACE")
    require(material.get("publishable") is False, "E_MATERIAL_PUBLISHABLE")
    require(material.get("runtime_consumable") is False, "E_MATERIAL_RUNTIME")
    require(material.get("may_enter_300") is False, "E_MATERIAL_BASELINE")
    sources = _typed_rows(material.get("sources"), "SOURCE_OBJECT", "source_id")
    facts = _typed_rows(material.get("facts"), "FACT_OBJECT", "fact_id")
    authorizations = _typed_rows(
        material.get("authorizations"),
        "AUTHORIZATION_OBJECT",
        "authorization_id",
    )
    expected = profile_required_slots(profile)
    actual = {
        "source": sorted(str(row.get("slot_id")) for row in sources),
        "fact": sorted(str(row.get("slot_id")) for row in facts),
        "authorization": sorted(str(row.get("slot_id")) for row in authorizations),
    }
    for slot_class, slots in expected.items():
        require(actual[slot_class] == sorted(slots), "E_SLOT_BINDING", slot_class)
    source_ids = {str(row["source_id"]) for row in sources}
    authorization_ids = {str(row["authorization_id"]) for row in authorizations}
    for source in sources:
        require(source.get("synthetic_test_only") is True, "E_SOURCE_NAMESPACE")
        require(source.get("may_supply_real_brand_fact") is False, "E_SOURCE_TRUTH")
    for authorization in authorizations:
        scope = authorization.get("scope")
        require(isinstance(scope, Mapping), "E_AUTHORIZATION_SCOPE")
        require(scope.get("profile_id") == profile_id, "E_AUTHORIZATION_PROFILE")
        require(
            scope.get("publication_allowed") is False, "E_AUTHORIZATION_PUBLICATION"
        )
    for fact in facts:
        require(fact.get("synthetic_test_only") is True, "E_FACT_NAMESPACE")
        require(
            fact.get("may_be_treated_as_brand_truth") is False,
            "E_FACT_TRUTH_BOUNDARY",
        )
        require(
            set(map(str, fact.get("source_ids", []))).issubset(source_ids),
            "E_FACT_SOURCE_BINDING",
        )
        require(
            set(map(str, fact.get("authorization_ids", []))).issubset(
                authorization_ids
            ),
            "E_FACT_AUTHORIZATION_BINDING",
        )


def _profile_projection(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_product_type_id": profile.get("content_product_type_id"),
        "business_purpose": profile.get("business_purpose"),
        "target_account_roles": profile.get("target_account_roles", []),
        "target_platforms": profile.get("target_platforms", []),
        "founder_core_inputs": profile.get("founder_core_inputs", []),
        "required_component_roles": profile.get("required_component_roles", []),
        "input_requirements": profile.get("input_requirements"),
        "event_truth_policy": profile.get("event_truth_policy"),
        "narrative_constraints": profile.get("narrative_constraints"),
        "style_constraints": profile.get("style_constraints"),
        "continuity_policy": profile.get("continuity_policy"),
        "visual_audio_requirement_refs": profile.get(
            "visual_audio_requirement_refs", []
        ),
        "platform_expression_requirement_refs": profile.get(
            "platform_expression_requirement_refs", []
        ),
        "anti_pattern_rule_refs": profile.get("anti_pattern_rule_refs", []),
        "founder_hard_guards": profile.get("founder_hard_guards", []),
        "input_sufficiency_routes": profile.get("input_sufficiency_routes", []),
        "profile_digest": profile.get("profile_digest"),
    }


def build_author_request(
    profile: Mapping[str, Any],
    material: Mapping[str, Any],
    lane_id: str,
    lane_path: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
    control_rule_ids: list[str],
) -> dict[str, Any]:
    """Build a complete author request from typed objects and approved references."""

    validate_typed_material(material, profile)
    require(lane_id in {"A", "B"}, "E_LANE_ID")
    profile_id = str(profile["content_product_type_id"])
    component_bindings: list[dict[str, Any]] = []
    for component_id in lane_path.get("component_ids", []):
        component = component_by_id.get(str(component_id))
        require(component is not None, "E_COMPONENT_NOT_APPROVED", str(component_id))
        component_bindings.append(
            {
                "object_type": "COMPONENT_BINDING",
                "component_id": component_id,
                "component_digest": component.get("component_digest"),
                "component_role": component.get("component_role"),
                "required_input_slots": component.get("required_input_slots", []),
                "required_fact_slots": component.get("required_fact_slots", []),
                "required_authorization_slots": component.get(
                    "required_authorization_slots", []
                ),
                "claim_boundary": component.get("claim_boundary"),
            }
        )
    require(component_bindings, "E_COMPONENT_BINDING_EMPTY", profile_id)
    request: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "task_id": TASK_ID,
        "generator_version": GENERATOR_VERSION,
        "request_id": f"P2-LOCAL-{profile_id}-LANE-{lane_id}",
        "user_goal": "Validate controlled structural authoring without audience content",
        "content_product_type_id": profile_id,
        "audience": "SYNTHETIC_LOCAL_TEST_AUDIENCE",
        "platform": list(profile.get("target_platforms", [])),
        "duration_constraint": "LOCAL_STRUCTURAL_TEST_NOT_DURATION_BOUND",
        "account_expression_identity": list(profile.get("target_account_roles", [])),
        "capture_conditions": list(profile.get("visual_audio_requirement_refs", [])),
        "profile_contract": _profile_projection(profile),
        "typed_material": dict(material),
        "lane": {
            "lane_id": lane_id,
            "session_id": f"P2-INDEPENDENT-AUTHOR-SESSION-{profile_id}-{lane_id}",
            "other_lane_visible": False,
            "narrative_mechanism": lane_path.get("narrative_mechanism"),
            "information_order": lane_path.get("information_order"),
            "visual_subject": lane_path.get("visual_subject"),
            "sound_subject": lane_path.get("sound_subject"),
            "rhythm": lane_path.get("rhythm"),
            "ending": lane_path.get("ending"),
        },
        "component_bindings": component_bindings,
        "control_rule_bindings": [
            {"object_type": "CONTROL_RULE_BINDING", "control_rule_id": rule_id}
            for rule_id in control_rule_ids
        ],
        "hard_prohibitions": {
            "profile_hard_guards": profile.get("founder_hard_guards", []),
            "no_unbound_fact": True,
            "no_unbound_authorization": True,
            "no_component_as_fact_or_authorization": True,
            "no_external_provider": True,
            "no_audience_content_in_p2": True,
        },
        "expected_output_structure": {
            "kind": "STRUCTURAL_REALIZATION_EVIDENCE_ONLY",
            "audience_title_allowed": False,
            "audience_body_allowed": False,
            "spoken_script_allowed": False,
        },
        "external_provider_allowed": False,
        "development_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "may_enter_300": False,
    }
    request["request_digest"] = object_digest(request, "request_digest")
    return request


def validate_author_request(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    require(
        request.get("request_digest") == object_digest(request, "request_digest"),
        "E_REQUEST_DIGEST",
    )
    require(request.get("schema_version") == REQUEST_SCHEMA_VERSION, "E_REQUEST_SCHEMA")
    require(
        request.get("generator_version") == GENERATOR_VERSION, "E_GENERATOR_VERSION"
    )
    require(request.get("external_provider_allowed") is False, "E_PROVIDER_ALLOWED")
    require(request.get("publishable") is False, "E_REQUEST_PUBLISHABLE")
    require(request.get("runtime_consumable") is False, "E_REQUEST_RUNTIME")
    require(request.get("may_enter_300") is False, "E_REQUEST_BASELINE")
    profile_contract = request.get("profile_contract")
    material = request.get("typed_material")
    require(isinstance(profile_contract, Mapping), "E_REQUEST_PROFILE")
    require(isinstance(material, Mapping), "E_REQUEST_MATERIAL")
    require(
        profile_contract.get("content_product_type_id")
        == request.get("content_product_type_id")
        == material.get("profile_id"),
        "E_REQUEST_PROFILE_BINDING",
    )
    bindings = _typed_rows(
        request.get("component_bindings"), "COMPONENT_BINDING", "component_id"
    )
    for binding in bindings:
        component = component_by_id.get(str(binding["component_id"]))
        require(component is not None, "E_COMPONENT_NOT_APPROVED")
        require(
            binding.get("component_digest") == component.get("component_digest"),
            "E_COMPONENT_DIGEST",
        )
        require(
            binding.get("component_role") == component.get("component_role"),
            "E_COMPONENT_ROLE",
        )


def realize_request(
    request: Mapping[str, Any],
    component_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Produce non-audience structural evidence with one unique range per component."""

    validate_author_request(request, component_by_id)
    lane = request["lane"]
    contributions: list[dict[str, Any]] = []
    for index, binding in enumerate(request["component_bindings"], 1):
        component = component_by_id[str(binding["component_id"])]
        mechanism = component.get("mechanism", {})
        contributions.append(
            {
                "component_id": binding["component_id"],
                "component_digest": binding["component_digest"],
                "implementation_pointer": (
                    f"/structural_realization/lane_{lane['lane_id']}/"
                    f"{binding['component_role']}/{index - 1}"
                ),
                "observable_structural_effect": {
                    "component_role": binding["component_role"],
                    "mechanism_digest": digest_object(mechanism),
                    "lane_operator": lane.get("narrative_mechanism"),
                    "information_order": lane.get("information_order"),
                },
            }
        )
    pointers = [row["implementation_pointer"] for row in contributions]
    require(len(pointers) == len(set(pointers)), "E_IMPLEMENTATION_POINTER_REUSE")
    realization: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "generator_version": GENERATOR_VERSION,
        "request_id": request["request_id"],
        "request_digest": request["request_digest"],
        "profile_id": request["content_product_type_id"],
        "lane_id": lane["lane_id"],
        "component_contributions": contributions,
        "selected_component_count": len(request["component_bindings"]),
        "realized_component_count": len(contributions),
        "unrealized_component_count": len(request["component_bindings"])
        - len(contributions),
        "audience_title": "",
        "audience_body": [],
        "spoken_script": [],
        "development_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "may_enter_300": False,
    }
    realization["realization_digest"] = object_digest(realization, "realization_digest")
    return realization


def _missing_slots(
    input_payload: Mapping[str, Any], profile: Mapping[str, Any]
) -> dict[str, list[str]]:
    required = profile_required_slots(profile)
    present = {
        "source": set(map(str, input_payload.get("present_source_slots", []))),
        "fact": set(map(str, input_payload.get("present_fact_slots", []))),
        "authorization": set(
            map(str, input_payload.get("present_authorization_slots", []))
        ),
    }
    return {
        key: sorted(set(values).difference(present[key]))
        for key, values in required.items()
    }


def _missing_route(profile: Mapping[str, Any], slot_class: str) -> Mapping[str, Any]:
    route_id = f"required_{slot_class}_missing"
    for route in profile.get("input_sufficiency_routes", []):
        if isinstance(route, Mapping) and route.get("route_id") == route_id:
            return route
    raise Gate1ValidationError(f"E_ROUTE_CONTRACT:{route_id}")


def evaluate_route(
    input_record: Mapping[str, Any], profile: Mapping[str, Any]
) -> dict[str, Any]:
    """Route from typed input state without reading the frozen expected answer."""

    payload = input_record.get("actual_input_payload")
    require(isinstance(payload, Mapping), "E_ROUTE_INPUT_PAYLOAD")
    profile_id = str(profile["content_product_type_id"])
    require(input_record.get("profile_id") == profile_id, "E_ROUTE_PROFILE")
    missing = _missing_slots(payload, profile)
    hard_guard_hits = set(map(str, payload.get("hard_guard_hits", [])))
    risk_points = set(map(str, payload.get("risk_points", [])))
    guard_risks = {
        risk
        for risk in risk_points
        if risk.startswith("AGR_") or risk.startswith("hard_guard:AGR_")
    }
    action: str
    category: str
    detailed_reason: str
    degraded_artifact: dict[str, Any] | None = None
    if hard_guard_hits or guard_risks:
        action = "BLOCK"
        category = "输入冲突"
        detailed_reason = "HARD_GUARD_OR_INPUT_CONFLICT"
    elif AUTHORIZATION_BLOCKING_RISKS.intersection(risk_points):
        action = "BLOCK"
        category = "授权缺失"
        detailed_reason = "UNAUTHORIZED_OR_INVALID_AUTHORIZATION_SCOPE"
    elif FACT_BLOCKING_RISKS.intersection(risk_points):
        action = "BLOCK"
        category = "事实缺失"
        detailed_reason = "UNSUPPORTED_OR_FABRICATED_FACT"
    else:
        missing_classes = [
            slot_class
            for slot_class in ("authorization", "fact", "source")
            if missing[slot_class]
        ]
        require(
            missing_classes,
            "E_ROUTE_UNEXPECTED_ALLOW",
            str(input_record.get("case_id")),
        )
        slot_class = missing_classes[0]
        category = "授权缺失" if slot_class == "authorization" else "事实缺失"
        route = _missing_route(profile, slot_class)
        requested = str(payload.get("requested_degraded_output", ""))
        partial_payload = payload.get("partial_artifact_payload")
        partial_allowed = (
            payload.get("partial_safe") is True
            and route.get("audience_facing_body_allowed") is False
            and requested in set(map(str, route.get("allowed_outputs", [])))
            and isinstance(partial_payload, Mapping)
            and bool(partial_payload)
        )
        if partial_allowed:
            action = "DEGRADE"
            detailed_reason = f"PROFILE_ALLOWED_PARTIAL_SAFE_{slot_class.upper()}"
            degraded_artifact = {
                "artifact_type": requested,
                "profile_id": profile_id,
                "missing_slot_class": slot_class,
                "missing_slots": missing[slot_class],
                "internal_payload": dict(partial_payload),
                "audience_facing": False,
                "runtime_consumable": False,
            }
            degraded_artifact["artifact_digest"] = digest_object(degraded_artifact)
        else:
            action = "REQUEST_INPUT"
            detailed_reason = f"REQUIRED_{slot_class.upper()}_MISSING"
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "route_engine_version": ROUTE_ENGINE_VERSION,
        "case_id": input_record.get("case_id"),
        "profile_id": profile_id,
        "actual_primary_action": action,
        "actual_primary_reason_category": category,
        "actual_detailed_reason_code": detailed_reason,
        "missing_slots": missing,
        "hard_guard_hits": sorted(hard_guard_hits.union(guard_risks)),
        "risk_points": sorted(risk_points),
        "degraded_artifact": degraded_artifact,
        "audience_title_created": False,
        "audience_body_created": False,
        "spoken_script_created": False,
        "runtime_plan_created": False,
        "runtime_consumable": False,
    }
    result["route_result_digest"] = object_digest(result, "route_result_digest")
    return result


@dataclass
class ExternalProviderExitAudit:
    """The sole provider exit; P2 records blocked attempts but dispatches nothing."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def dispatch(self, provider: str, request_digest: str) -> NoReturn:
        event = {
            "event_type": "BLOCKED_EXTERNAL_PROVIDER_ATTEMPT",
            "provider": provider,
            "request_digest": request_digest,
            "network_dispatch_started": False,
            "provider_response_received": False,
        }
        event["event_digest"] = digest_object(event)
        self.events.append(event)
        raise Gate1ValidationError("E_EXTERNAL_PROVIDER_DISABLED")

    def summary(self) -> dict[str, Any]:
        completed_calls = sum(
            event.get("network_dispatch_started") is True
            and event.get("provider_response_received") is True
            for event in self.events
        )
        attempted_calls = sum(
            event.get("event_type") == "BLOCKED_EXTERNAL_PROVIDER_ATTEMPT"
            for event in self.events
        )
        summary: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "unique_exit": "ExternalProviderExitAudit.dispatch",
            "event_count": len(self.events),
            "blocked_attempt_count": attempted_calls,
            "external_provider_request_count": completed_calls,
            "external_provider_response_count": sum(
                event.get("provider_response_received") is True for event in self.events
            ),
            "derived_from_event_log": True,
            "events": self.events,
        }
        summary["audit_digest"] = object_digest(summary, "audit_digest")
        return summary
