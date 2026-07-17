"""具体执行器到横向评测脊柱的窄适配器。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .canonical import digest_json
from .contracts import ContractError, validate_cost_event


def _unwrap(value: Any, field: str, reasons: dict[str, str]) -> Any:
    if (isinstance(value, Mapping) and value.get("availability") == "unavailable"
            and isinstance(value.get("reason"), str) and value["reason"].strip()):
        reasons[field] = value["reason"].strip()
        return None
    return value


def adapt_v4_cost_event(event: Mapping[str, Any], *, budget_category: str,
                        outcome_status: str,
                        reviewer_minutes: float = 0.0,
                        reviewer_identity: str | None = None,
                        labor_rate_snapshot_id: str | None = None,
                        human_cost_usd: float | None = None) -> dict[str, Any]:
    """把 v4 的嵌套遥测转换为脊柱扁平成本事件，缺数原因原样保留。"""
    reasons: dict[str, str] = {}
    model = event.get("model_config", {})
    usage = event.get("usage", {})
    cost = event.get("cost", {})
    if not all(isinstance(value, Mapping) for value in (model, usage, cost)):
        raise ContractError("v4 telemetry model/usage/cost must be objects")
    currency = cost.get("currency")
    if not (isinstance(currency, Mapping) and currency.get("availability") == "unavailable"):
        if currency != "USD":
            raise ContractError("model_cost_usd requires a USD v4 cost event")
    attempt_index = event.get("attempt_index")
    attempt_id: str | None
    if isinstance(attempt_index, int) and attempt_index > 0:
        attempt_id = f"{event.get('request_id')}:attempt:{attempt_index}"
    else:
        attempt_id = None
        reasons["attempt_id"] = "v4 event has no positive attempt index"
    adapted: dict[str, Any] = {
        "schema_version": "eval-spine-cost-event-v1",
        "event_id": str(event.get("event_id", "")),
        "stage_id": str(event.get("stage", "")),
        "task_kind": str(event.get("stage", "")),
        "resource_kind": "HYBRID" if reviewer_minutes > 0 else "MODEL_CALL",
        "budget_category": budget_category,
        "outcome_status": outcome_status,
        "source_telemetry_event_digest": digest_json(dict(event)),
        "object_id": str(event.get("request_id", "")),
        "attempt_id": attempt_id,
        "provider": _unwrap(model.get("provider"), "provider", reasons),
        "model_revision": _unwrap(model.get("model_revision"), "model_revision", reasons),
        "provider_call_id": _unwrap(event.get("provider_call_id"),
                                    "provider_call_id", reasons),
        "input_tokens": _unwrap(usage.get("input_tokens"), "input_tokens", reasons),
        "cached_input_tokens": _unwrap(usage.get("cached_input_tokens"),
                                       "cached_input_tokens", reasons),
        "output_tokens": _unwrap(usage.get("output_tokens"), "output_tokens", reasons),
        "price_snapshot_id": _unwrap(cost.get("rate_card_ref"),
                                     "price_snapshot_id", reasons),
        "model_cost_usd": _unwrap(cost.get("amount"), "model_cost_usd", reasons),
        "reviewer_minutes": reviewer_minutes,
        "reviewer_identity": reviewer_identity,
        "labor_rate_snapshot_id": labor_rate_snapshot_id,
        "human_cost_usd": human_cost_usd if reviewer_minutes > 0 else 0,
        "wall_clock_seconds": float(event.get("duration_ms", 0)) / 1000,
        "unavailable_reasons": dict(sorted(reasons.items())),
        "event_digest": "",
    }
    unsigned = dict(adapted)
    unsigned.pop("event_digest")
    adapted["event_digest"] = digest_json(unsigned)
    errors = validate_cost_event(adapted)
    if errors:
        raise ContractError("invalid adapted cost event: " + ",".join(errors))
    return adapted
