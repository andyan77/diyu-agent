#!/usr/bin/env python3
"""Single route gate for qualification-only controlled authoring."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


ROUTE_GATE_VERSION = "controlled-v2-route-gate-v0.1"
RISK_BLOCKERS = frozenset(
    {
        "FABRICATED_EVENT",
        "FABRICATED_PERSON_EXPERIENCE",
        "PRIVACY_AUTHORIZATION_FAILURE",
        "ROLE_AUTHORITY_EXPANSION",
        "UNAUTHORIZED_BRAND_CLAIM",
        "UNSUPPORTED_NUMERIC_OR_PERFORMANCE_CLAIM",
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _slot_sets(profile: Mapping[str, Any]) -> dict[str, set[str]]:
    requirements = profile.get("input_requirements", {})
    if not isinstance(requirements, Mapping):
        raise ValueError("profile input_requirements must be an object")
    return {
        "source": set(map(str, requirements.get("required_source_slots", []))),
        "fact": set(map(str, requirements.get("required_fact_slots", []))),
        "authorization": set(map(str, requirements.get("required_authorization_slots", []))),
    }


def _missing_slots(
    input_projection: Mapping[str, Any], profile: Mapping[str, Any]
) -> dict[str, list[str]]:
    required = _slot_sets(profile)
    present = {
        "source": set(map(str, input_projection.get("present_source_slots", []))),
        "fact": set(map(str, input_projection.get("present_fact_slots", []))),
        "authorization": set(map(str, input_projection.get("present_authorization_slots", []))),
    }
    return {
        slot_class: sorted(required_slots.difference(present[slot_class]))
        for slot_class, required_slots in required.items()
    }


def _route_contract(profile: Mapping[str, Any], slot_class: str) -> Mapping[str, Any]:
    route_id = f"required_{slot_class}_missing"
    routes = profile.get("input_sufficiency_routes", [])
    for route in routes:
        if isinstance(route, Mapping) and route.get("route_id") == route_id:
            return route
    raise ValueError(f"profile lacks route contract {route_id}")


def _decision(
    action: str,
    reason_code: str,
    evaluated_rules: list[dict[str, Any]],
    missing: Mapping[str, list[str]],
    degraded_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "route_gate_version": ROUTE_GATE_VERSION,
        "actual_primary_action": action,
        "actual_primary_reason_code": reason_code,
        "missing_slots": {key: list(value) for key, value in missing.items()},
        "rule_evaluation_trace": evaluated_rules,
        "audience_title_created": False,
        "audience_body_created": False,
        "spoken_script_created": False,
        "runtime_plan_created": False,
        "runtime_consumable": False,
        "degraded_artifact": dict(degraded_artifact) if degraded_artifact else None,
    }
    decision["actual_decision_digest"] = digest_object(decision)
    return decision


def controlled_v2_route_gate(
    input_projection: Mapping[str, Any], profile_contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Evaluate real input state without access to sealed expectations."""

    if input_projection.get("profile_id") != profile_contract.get("content_product_type_id"):
        raise ValueError("input projection and profile mismatch")

    missing = _missing_slots(input_projection, profile_contract)
    hard_guard_hits = sorted(set(map(str, input_projection.get("hard_guard_hits", []))))
    risk_points = sorted(set(map(str, input_projection.get("risk_points", []))))
    evaluated: list[dict[str, Any]] = [
        {
            "rule_ref": "ROUTE-GATE-01-HARD-GUARD",
            "outcome": "FAIL" if hard_guard_hits else "PASS",
            "evidence": hard_guard_hits,
        },
        {
            "rule_ref": "ROUTE-GATE-02-RISK-BLOCK",
            "outcome": "FAIL" if RISK_BLOCKERS.intersection(risk_points) else "PASS",
            "evidence": sorted(RISK_BLOCKERS.intersection(risk_points)),
        },
    ]
    if hard_guard_hits:
        return _decision(
            "BLOCK",
            "HARD_GUARD_TRIGGERED",
            evaluated,
            missing,
        )
    blocking_risks = sorted(RISK_BLOCKERS.intersection(risk_points))
    if blocking_risks:
        return _decision(
            "BLOCK",
            "UNAUTHORIZED_OR_UNSAFE_INPUT",
            evaluated,
            missing,
        )

    missing_classes = [slot_class for slot_class in ("authorization", "fact", "source") if missing[slot_class]]
    if not missing_classes:
        evaluated.append(
            {
                "rule_ref": "ROUTE-GATE-03-INPUT-SUFFICIENCY",
                "outcome": "PASS",
                "evidence": [],
            }
        )
        return _decision("ALLOW", "ALL_REQUIRED_INPUTS_PRESENT", evaluated, missing)

    slot_class = missing_classes[0]
    contract = _route_contract(profile_contract, slot_class)
    allowed_outputs = list(map(str, contract.get("allowed_outputs", [])))
    requested_output = str(input_projection.get("requested_degraded_output", ""))
    partial_payload = input_projection.get("partial_artifact_payload")
    partial_safe = input_projection.get("partial_safe") is True
    audience_forbidden = contract.get("audience_facing_body_allowed") is False
    degraded_allowed = requested_output in allowed_outputs
    artifact_nonempty = isinstance(partial_payload, Mapping) and bool(partial_payload)
    evaluated.extend(
        [
            {
                "rule_ref": f"PROFILE::{profile_contract['content_product_type_id']}::{contract['route_id']}",
                "outcome": "MATCH",
                "evidence": missing[slot_class],
            },
            {
                "rule_ref": "ROUTE-GATE-04-PARTIAL-SAFE-DEGRADE",
                "outcome": (
                    "PASS"
                    if partial_safe and audience_forbidden and degraded_allowed and artifact_nonempty
                    else "NOT_APPLICABLE"
                ),
                "evidence": {
                    "partial_safe": partial_safe,
                    "audience_forbidden": audience_forbidden,
                    "requested_output": requested_output,
                    "allowed_outputs": allowed_outputs,
                    "artifact_nonempty": artifact_nonempty,
                },
            },
        ]
    )
    if partial_safe and audience_forbidden and degraded_allowed and artifact_nonempty:
        degraded_artifact = {
            "artifact_type": requested_output,
            "profile_id": profile_contract["content_product_type_id"],
            "missing_slot_class": slot_class,
            "missing_slots": missing[slot_class],
            "internal_payload": dict(partial_payload),
            "audience_facing": False,
            "runtime_consumable": False,
        }
        degraded_artifact["artifact_digest"] = digest_object(degraded_artifact)
        return _decision(
            "DEGRADE",
            f"PROFILE_ALLOWED_PARTIAL_SAFE_{slot_class.upper()}",
            evaluated,
            missing,
            degraded_artifact,
        )

    return _decision(
        "REQUEST_INPUT",
        f"REQUIRED_{slot_class.upper()}_MISSING",
        evaluated,
        missing,
    )


if __name__ == "__main__":
    raise SystemExit(2)
