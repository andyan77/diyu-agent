"""逐事件遥测完整性和300规模成本投影。"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable

from .canonical import digest_json
from .contracts import validate_cost_event

# 投影/遥测度量维度键集。依裁决 #4（拨付制+只记账），这些键只承载诊断计量，
# 不再作为任何 hard-ceiling 阻断键集（原名 REQUIRED_CEILING_KEYS，M1-C2 迁移改名）。
PROJECTION_METRIC_KEYS = {
    "one_time_gold_and_measurement_usd", "causal_pilot_60_usd",
    "open_120_usd", "hidden_40_usd", "baseline_240_plus_60_usd",
    "total_program_usd", "total_model_input_tokens",
    "total_model_cached_input_tokens", "total_model_output_tokens",
    "total_reviewer_minutes", "p95_single_item_wall_clock_seconds",
    "total_wall_clock_minutes",
}

# budget_category 是 24 字段成本事件的保留字段名（分类记账维度，非阻断门）。
BUDGET_CATEGORY_KEYS = {
    "one_time_gold_and_measurement_usd", "causal_pilot_60_usd",
    "open_120_usd", "hidden_40_usd", "baseline_240_plus_60_usd",
}

FORECAST_AGGREGATE_KEYS = PROJECTION_METRIC_KEYS - BUDGET_CATEGORY_KEYS
MAX_PRICE_SNAPSHOT_AGE_DAYS = 30


def _numeric(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _nonnegative(value: Any) -> float | None:
    number = _numeric(value)
    return number if number is not None and number >= 0 else None


def _utc_datetime(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def validate_rate_card(rate_card: dict[str, Any] | None) -> list[str]:
    if not isinstance(rate_card, dict):
        return ["rate_card_missing"]
    required = {"schema_version", "snapshot_id", "captured_at", "currency",
                "rates", "labor_rates", "rate_card_digest"}
    errors: list[str] = []
    if set(rate_card) != required:
        errors.append("rate_card_field_set_mismatch")
    if rate_card.get("schema_version") != "eval-spine-rate-card-v1":
        errors.append("rate_card_schema_version")
    if not str(rate_card.get("snapshot_id", "")).strip():
        errors.append("rate_card_snapshot_id")
    if rate_card.get("currency") != "USD":
        errors.append("rate_card_currency")
    if _utc_datetime(rate_card.get("captured_at")) is None:
        errors.append("rate_card_captured_at")
    rates = rate_card.get("rates")
    if not isinstance(rates, dict) or not rates:
        errors.append("rate_card_rates_missing")
    else:
        for key, row in rates.items():
            if not str(key).strip() or not isinstance(row, dict) or set(row) != {
                    "input_per_million", "cached_input_per_million",
                    "output_per_million"}:
                errors.append(f"rate_card_rate_shape:{key}")
                continue
            if any(_nonnegative(value) is None for value in row.values()):
                errors.append(f"rate_card_negative_or_invalid:{key}")
    labor_rates = rate_card.get("labor_rates")
    if not isinstance(labor_rates, dict):
        errors.append("rate_card_labor_rates_missing")
    else:
        for identity, hourly_rate in labor_rates.items():
            if not str(identity).strip() or _nonnegative(hourly_rate) is None:
                errors.append(f"rate_card_labor_rate_invalid:{identity}")
    unsigned = dict(rate_card)
    supplied = unsigned.pop("rate_card_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("rate_card_digest_mismatch")
    return sorted(errors)


def _event_expected_cost(event: dict[str, Any], rate_card: dict[str, Any]) -> float | None:
    key = f"{event.get('provider')}::{event.get('model_revision')}"
    rate = rate_card.get("rates", {}).get(key)
    fields = (event.get("input_tokens"), event.get("cached_input_tokens"),
              event.get("output_tokens"))
    if not isinstance(rate, dict) or any(value is None for value in fields):
        return None
    input_tokens, cached_tokens, output_tokens = map(int, fields)
    uncached = input_tokens - cached_tokens
    return ((uncached * float(rate["input_per_million"])
             + cached_tokens * float(rate["cached_input_per_million"])
             + output_tokens * float(rate["output_per_million"])) / 1_000_000)


def _verify_expected_event_manifest(manifest: dict[str, Any] | None) -> list[str]:
    if not isinstance(manifest, dict):
        return ["expected_event_manifest_missing"]
    required = {"schema_version", "stage_scope", "registered_before_run",
                "custodian_identity", "approved_by", "approved_at",
                "source_run_manifest_digest", "expected_events", "manifest_digest"}
    errors: list[str] = []
    if set(manifest) != required:
        errors.append("expected_event_manifest_field_set")
    if (manifest.get("schema_version") != "eval-spine-expected-cost-events-v1"
            or manifest.get("registered_before_run") is not True
            or not str(manifest.get("stage_scope", "")).strip()
            or not str(manifest.get("custodian_identity", "")).strip()
            or not str(manifest.get("approved_by", "")).strip()
            or _utc_datetime(manifest.get("approved_at")) is None
            or not isinstance(manifest.get("source_run_manifest_digest"), str)
            or len(manifest.get("source_run_manifest_digest", "")) != 64):
        errors.append("expected_event_manifest_state")
    events = manifest.get("expected_events")
    if not isinstance(events, list) or not events:
        errors.append("expected_event_manifest_entries")
        events = []
    identities: list[tuple[str, str, str, str, str, str]] = []
    for row in events:
        if (not isinstance(row, dict)
                or set(row) != {"event_id", "stage_id", "task_kind",
                                    "resource_kind", "budget_category", "object_id"}
                or not all(str(row.get(key, "")).strip()
                           for key in ("event_id", "stage_id", "task_kind",
                                       "resource_kind", "budget_category", "object_id"))
                or row.get("resource_kind") not in {
                    "MODEL_CALL", "HUMAN_REVIEW", "HYBRID"}
                or row.get("budget_category") not in BUDGET_CATEGORY_KEYS):
            errors.append("expected_event_manifest_entry_shape")
            continue
        identities.append((row["event_id"], row["stage_id"], row["task_kind"],
                           row["resource_kind"], row["budget_category"],
                           row["object_id"]))
    if len(identities) != len(set(identities)):
        errors.append("expected_event_manifest_duplicate_entry")
    unsigned = dict(manifest)
    supplied = unsigned.pop("manifest_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("expected_event_manifest_digest")
    return sorted(set(errors))


def _verify_source_event_manifest(manifest: dict[str, Any] | None) -> list[str]:
    if not isinstance(manifest, dict):
        return ["source_event_manifest_missing"]
    required = {"schema_version", "run_id", "source_run_manifest_digest",
                "generated_from_append_only_log", "includes_failed_attempts",
                "source_events", "manifest_digest"}
    errors: list[str] = []
    if set(manifest) != required:
        errors.append("source_event_manifest_field_set")
    if (manifest.get("schema_version") != "eval-spine-source-cost-events-v1"
            or not str(manifest.get("run_id", "")).strip()
            or manifest.get("generated_from_append_only_log") is not True
            or manifest.get("includes_failed_attempts") is not True
            or not isinstance(manifest.get("source_run_manifest_digest"), str)
            or len(manifest.get("source_run_manifest_digest", "")) != 64):
        errors.append("source_event_manifest_state")
    rows = manifest.get("source_events")
    if not isinstance(rows, list) or not rows:
        errors.append("source_event_manifest_entries")
        rows = []
    event_ids: list[str] = []
    source_digests: list[str] = []
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {
                "event_id", "resource_kind", "outcome_status",
                "source_telemetry_event_digest", "provider_call_id",
                "wall_clock_seconds"}):
            errors.append("source_event_manifest_entry_shape")
            continue
        event_id = row.get("event_id")
        digest = row.get("source_telemetry_event_digest")
        if (not isinstance(event_id, str) or not event_id.strip()
                or row.get("resource_kind") not in {
                    "MODEL_CALL", "HUMAN_REVIEW", "HYBRID"}
                or row.get("outcome_status") not in {
                    "SUCCEEDED", "FAILED", "ABORTED"}
                or not isinstance(digest, str) or len(digest) != 64
                or _nonnegative(row.get("wall_clock_seconds")) is None):
            errors.append("source_event_manifest_entry_value")
            continue
        if (row["resource_kind"] in {"MODEL_CALL", "HYBRID"}
                and (not isinstance(row.get("provider_call_id"), str)
                     or not row["provider_call_id"].strip())):
            errors.append("source_event_manifest_provider_call")
        if (row["resource_kind"] == "HUMAN_REVIEW"
                and row.get("provider_call_id") is not None):
            errors.append("source_event_manifest_human_provider_call")
        event_ids.append(event_id)
        source_digests.append(digest)
    if len(event_ids) != len(set(event_ids)):
        errors.append("source_event_manifest_duplicate_event")
    if len(source_digests) != len(set(source_digests)):
        errors.append("source_event_manifest_duplicate_source_digest")
    unsigned = dict(manifest)
    supplied = unsigned.pop("manifest_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("source_event_manifest_digest")
    return sorted(set(errors))


def metering_report(events: Iterable[dict[str, Any]], *,
                    rate_card: dict[str, Any] | None = None,
                    expected_event_manifest: dict[str, Any] | None = None,
                    source_event_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = list(events)
    errors = {
        str(row.get("event_id", f"row-{index}")) if isinstance(row, dict)
        else f"row-{index}": (validate_cost_event(row) if isinstance(row, dict)
                              else ["cost_event_not_object"])
        for index, row in enumerate(rows)}
    errors = {key: value for key, value in errors.items() if value}
    unavailable = {
        str(row.get("event_id", f"row-{index}")): sorted(
            field for field in (
                (("input_tokens", "cached_input_tokens", "output_tokens",
                  "model_cost_usd") if row.get("resource_kind")
                 in {"MODEL_CALL", "HYBRID"} else ())
                + (("reviewer_identity", "labor_rate_snapshot_id",
                    "reviewer_minutes", "human_cost_usd")
                   if row.get("resource_kind") in {"HUMAN_REVIEW", "HYBRID"} else ()))
            if row.get(field) is None)
        for index, row in enumerate(rows) if isinstance(row, dict)
    }
    unavailable = {key: value for key, value in unavailable.items() if value}
    event_ids = [str(row.get("event_id", "")) if isinstance(row, dict) else ""
                 for row in rows]
    provider_call_ids = [str(row.get("provider_call_id")) for row in rows
                         if isinstance(row, dict)
                         and row.get("resource_kind") in {"MODEL_CALL", "HYBRID"}
                         and row.get("provider_call_id") is not None]
    duplicate_event_ids = sorted(key for key, count in __import__("collections").Counter(
        event_ids).items() if count > 1)
    duplicate_provider_calls = sorted(key for key, count in __import__("collections").Counter(
        provider_call_ids).items() if count > 1)
    rate_errors = validate_rate_card(rate_card)
    cost_recompute_errors: list[str] = []
    human_cost_recompute_errors: list[str] = []
    if not rate_errors and rate_card is not None:
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("price_snapshot_id") != rate_card.get("snapshot_id"):
                if row.get("resource_kind") in {"MODEL_CALL", "HYBRID"}:
                    cost_recompute_errors.append(
                        f"price_snapshot_mismatch:{row.get('event_id')}")
            elif row.get("resource_kind") in {"MODEL_CALL", "HYBRID"}:
                expected_cost = _event_expected_cost(row, rate_card)
                actual_cost = _numeric(row.get("model_cost_usd"))
                if (expected_cost is None or actual_cost is None
                        or not math.isclose(expected_cost, actual_cost,
                                            rel_tol=1e-9, abs_tol=1e-12)):
                    cost_recompute_errors.append(
                        f"cost_recompute_mismatch:{row.get('event_id')}")
            if row.get("resource_kind") in {"HUMAN_REVIEW", "HYBRID"}:
                hourly = _numeric(rate_card.get("labor_rates", {}).get(
                    row.get("reviewer_identity")))
                minutes = _numeric(row.get("reviewer_minutes"))
                actual_human = _numeric(row.get("human_cost_usd"))
                expected_human = (hourly * minutes / 60
                                  if hourly is not None and minutes is not None else None)
                if (row.get("labor_rate_snapshot_id") != rate_card.get("snapshot_id")
                        or expected_human is None or actual_human is None
                        or not math.isclose(expected_human, actual_human,
                                            rel_tol=1e-9, abs_tol=1e-12)):
                    human_cost_recompute_errors.append(
                        f"human_cost_recompute_mismatch:{row.get('event_id')}")
    event_manifest_errors = _verify_expected_event_manifest(expected_event_manifest)
    expected_rows = ((expected_event_manifest or {}).get("expected_events", [])
                     if not event_manifest_errors else [])
    actual_identities = {(str(row.get("event_id", "")),
                          str(row.get("stage_id", "")),
                          str(row.get("task_kind", "")),
                          str(row.get("resource_kind", "")),
                          str(row.get("budget_category", "")),
                          str(row.get("object_id", ""))) for row in rows
                         if isinstance(row, dict)}
    expected_identities = {(str(row.get("event_id", "")),
                            str(row.get("stage_id", "")),
                            str(row.get("task_kind", "")),
                            str(row.get("resource_kind", "")),
                            str(row.get("budget_category", "")),
                            str(row.get("object_id", "")))
                           for row in expected_rows if isinstance(row, dict)}
    expected_ids_match = (not event_manifest_errors
                          and actual_identities == expected_identities
                          and len(rows) == len(expected_rows))
    source_manifest_errors = _verify_source_event_manifest(source_event_manifest)
    source_rows = ((source_event_manifest or {}).get("source_events", [])
                   if not source_manifest_errors else [])
    actual_source_identities = {(str(row.get("event_id", "")),
                                 str(row.get("resource_kind", "")),
                                 str(row.get("outcome_status", "")),
                                 str(row.get("source_telemetry_event_digest", "")),
                                 row.get("provider_call_id"),
                                 _numeric(row.get("wall_clock_seconds")))
                                for row in rows if isinstance(row, dict)}
    source_identities = {(str(row.get("event_id", "")),
                          str(row.get("resource_kind", "")),
                          str(row.get("outcome_status", "")),
                          str(row.get("source_telemetry_event_digest", "")),
                          row.get("provider_call_id"),
                          _numeric(row.get("wall_clock_seconds")))
                         for row in source_rows if isinstance(row, dict)}
    source_events_match = (not source_manifest_errors
                           and actual_source_identities == source_identities
                           and len(rows) == len(source_rows)
                           and (source_event_manifest or {}).get(
                               "source_run_manifest_digest")
                           == (expected_event_manifest or {}).get(
                               "source_run_manifest_digest"))
    complete = sum(
        isinstance(row, dict)
        and str(row.get("event_id", f"row-{index}")) not in errors
        and str(row.get("event_id", f"row-{index}")) not in unavailable
        for index, row in enumerate(rows)
    )
    latencies = [value for row in rows if isinstance(row, dict)
                 if (value := _numeric(row.get("wall_clock_seconds"))) is not None]
    item_latency_totals: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        object_id = row.get("object_id")
        latency = _numeric(row.get("wall_clock_seconds"))
        if not isinstance(object_id, str) or not object_id.strip() or latency is None:
            continue
        item_latency_totals[object_id] = item_latency_totals.get(object_id, 0.0) + latency
    item_latencies = list(item_latency_totals.values())

    def total_applicable(field: str, applicable: set[str]) -> float | None:
        values: list[float] = []
        if len([row for row in rows if isinstance(row, dict)]) != len(rows):
            return None
        for row in rows:
            if row.get("resource_kind") not in applicable:
                values.append(0.0)
                continue
            value = _numeric(row.get(field))
            if value is None:
                return None
            values.append(value)
        return sum(values) if values else None

    model_kinds = {"MODEL_CALL", "HYBRID"}
    human_kinds = {"HUMAN_REVIEW", "HYBRID"}
    model_cost_total = total_applicable("model_cost_usd", model_kinds)
    human_cost_total = total_applicable("human_cost_usd", human_kinds)
    category_costs: dict[str, float | None] = {}
    for category in sorted(BUDGET_CATEGORY_KEYS):
        category_rows = [row for row in rows if isinstance(row, dict)
                         and row.get("budget_category") == category]
        if not category_rows:
            category_costs[category] = 0.0
            continue
        values: list[float] = []
        for row in category_rows:
            model_value = (0.0 if row.get("resource_kind") == "HUMAN_REVIEW"
                           else _numeric(row.get("model_cost_usd")))
            human_value = (0.0 if row.get("resource_kind") == "MODEL_CALL"
                           else _numeric(row.get("human_cost_usd")))
            if model_value is None or human_value is None:
                values = []
                break
            values.append(model_value + human_value)
        category_costs[category] = sum(values) if values else None

    gates = {
        "minimum_event_count": len(rows) >= 12,
        "event_contracts_valid": not errors,
        "critical_fields_available": not unavailable,
        "event_ids_unique": not duplicate_event_ids,
        "provider_call_ids_unique": not duplicate_provider_calls,
        "expected_event_manifest_matches": expected_ids_match,
        "source_event_manifest_matches": source_events_match,
        "rate_card_valid": not rate_errors,
        "costs_recompute_from_rate_card": not cost_recompute_errors,
        "human_costs_recompute_from_rate_card": not human_cost_recompute_errors,
        "all_events_complete": complete == len(rows),
    }
    report = {
        "schema_version": "eval-spine-metering-report-v1",
        "qualified": all(gates.values()), "gates": gates,
        "event_count": len(rows), "complete_event_count": complete,
        "errors": errors, "unavailable_critical_fields": unavailable,
        "duplicate_event_ids": duplicate_event_ids,
        "duplicate_provider_call_ids": duplicate_provider_calls,
        "rate_card_errors": rate_errors,
        "rate_card_digest": ((rate_card or {}).get("rate_card_digest")),
        "rate_card_captured_at": ((rate_card or {}).get("captured_at")),
        "expected_event_manifest_errors": event_manifest_errors,
        "expected_event_manifest_digest": (
            (expected_event_manifest or {}).get("manifest_digest")),
        "source_event_manifest_errors": source_manifest_errors,
        "source_event_manifest_digest": (
            (source_event_manifest or {}).get("manifest_digest")),
        "cost_recompute_errors": sorted(cost_recompute_errors),
        "human_cost_recompute_errors": sorted(human_cost_recompute_errors),
        "event_record_manifest_digest": digest_json([
            {"event_id": row.get("event_id"),
             "event_digest": row.get("event_digest"),
             "budget_category": row.get("budget_category")}
            for row in sorted((row for row in rows if isinstance(row, dict)),
                              key=lambda item: str(item.get("event_id", "")))
        ]),
        "actual_cost_by_budget_category_usd": category_costs,
        "total_model_cost_usd": model_cost_total,
        "total_input_tokens": total_applicable("input_tokens", model_kinds),
        "total_cached_input_tokens": total_applicable(
            "cached_input_tokens", model_kinds),
        "total_output_tokens": total_applicable("output_tokens", model_kinds),
        "total_reviewer_minutes": total_applicable(
            "reviewer_minutes", human_kinds),
        "total_human_cost_usd": human_cost_total,
        "total_wall_clock_seconds": sum(latencies) if len(latencies) == len(rows) else None,
        "p50_single_event_wall_clock_seconds": _percentile(latencies, .50),
        "p95_single_event_wall_clock_seconds": _percentile(latencies, .95),
        "p50_single_item_wall_clock_seconds": _percentile(item_latencies, .50),
        "p95_single_item_wall_clock_seconds": _percentile(item_latencies, .95),
    }
    report["total_program_cost_to_date_usd"] = (
        report["total_model_cost_usd"] + report["total_human_cost_usd"]
        if report["total_model_cost_usd"] is not None
        and report["total_human_cost_usd"] is not None else None)
    report["report_digest"] = digest_json(report)
    return report


def project_scale(*, fixed_cost: float, positive_items: int, route_items: int,
                  average_claims: float, per_claim_cost: float, per_pair_screen_cost: float,
                  human_item_cost: float, human_pair_cost: float,
                  candidate_pair_rate: float, contingency: float = .20) -> dict[str, Any]:
    """仅供早期诊断的旧公式；输出只作诊断遥测，不进入任何门。"""
    profiles = 20
    per_profile = positive_items // profiles
    all_within_profile_pairs = profiles * (per_profile * (per_profile - 1) / 2)
    variable = (positive_items * average_claims * per_claim_cost
                + all_within_profile_pairs * per_pair_screen_cost
                + positive_items * human_item_cost
                + all_within_profile_pairs * candidate_pair_rate * human_pair_cost
                + route_items * human_item_cost)
    baseline = fixed_cost + variable
    p95 = baseline * (1 + contingency)
    return {"schema_version": "eval-spine-diagnostic-cost-estimate-v1",
            "diagnostic_only": True,
            "projection_scope": "BASELINE_240_PLUS_60_DOLLAR_PARTIAL",
            "within_profile_pair_count": all_within_profile_pairs,
            "low": baseline * .85, "baseline": baseline, "high": p95}


def _closed_metering_report(events: Iterable[dict[str, Any]], *,
                            rate_card: dict[str, Any] | None,
                            expected_event_manifest: dict[str, Any] | None,
                            source_event_manifest: dict[str, Any] | None
                            ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = list(events)
    report = metering_report(
        rows, rate_card=rate_card,
        expected_event_manifest=expected_event_manifest,
        source_event_manifest=source_event_manifest)
    unsigned = dict(report)
    supplied = unsigned.pop("report_digest", None)
    if report.get("qualified") is not True or supplied != digest_json(unsigned):
        raise ValueError("metering_report_not_qualified")
    return rows, report


def _validate_scale_assumption_manifest(
        manifest: dict[str, Any] | None, *, report: dict[str, Any],
        rate_card: dict[str, Any]) -> list[str]:
    if not isinstance(manifest, dict):
        return ["scale_assumption_manifest_missing"]
    required = {
        "schema_version", "scope", "registered_before_scale",
        "custodian_identity", "approved_by", "approved_at",
        "price_snapshot_id", "basis_metering_report_digest",
        "basis_event_record_manifest_digest", "single_item_wall_clock_seconds",
        "stage_workloads", "manifest_digest",
    }
    errors: list[str] = []
    if set(manifest) != required:
        errors.append("scale_assumption_manifest_field_set")
    if (manifest.get("schema_version") != "eval-spine-scale-assumption-manifest-v1"
            or manifest.get("scope") != "FULL_PROGRAM_THROUGH_240_PLUS_60"
            or manifest.get("registered_before_scale") is not True):
        errors.append("scale_assumption_manifest_state")
    for field in ("custodian_identity", "approved_by"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"scale_assumption_manifest_{field}")
    if _utc_datetime(manifest.get("approved_at")) is None:
        errors.append("scale_assumption_manifest_approved_at")
    if manifest.get("price_snapshot_id") != rate_card.get("snapshot_id"):
        errors.append("scale_assumption_price_snapshot_mismatch")
    if manifest.get("basis_metering_report_digest") != report.get("report_digest"):
        errors.append("scale_assumption_metering_report_mismatch")
    if (manifest.get("basis_event_record_manifest_digest")
            != report.get("event_record_manifest_digest")):
        errors.append("scale_assumption_event_records_mismatch")
    single_item = manifest.get("single_item_wall_clock_seconds")
    if (not isinstance(single_item, dict) or set(single_item) != {"p50", "p95"}
            or _nonnegative(single_item.get("p50")) is None
            or _nonnegative(single_item.get("p95")) is None
            or float(single_item.get("p50", 0)) > float(single_item.get("p95", 0))):
        errors.append("scale_assumption_single_item_wall_clock")
    workloads = manifest.get("stage_workloads")
    if not isinstance(workloads, dict) or set(workloads) != BUDGET_CATEGORY_KEYS:
        errors.append("scale_assumption_stage_set")
        workloads = {}
    model_fields = {
        "workload_id", "resource_kind", "provider", "model_revision",
        "p50_event_count", "p95_event_count",
        "p50_input_tokens_per_event", "p95_input_tokens_per_event",
        "p50_cached_input_tokens_per_event", "p95_cached_input_tokens_per_event",
        "p50_output_tokens_per_event", "p95_output_tokens_per_event",
        "p50_wall_clock_seconds_per_event", "p95_wall_clock_seconds_per_event",
    }
    human_fields = {
        "workload_id", "resource_kind", "reviewer_identity",
        "p50_event_count", "p95_event_count",
        "p50_reviewer_minutes_per_event", "p95_reviewer_minutes_per_event",
        "p50_wall_clock_seconds_per_event", "p95_wall_clock_seconds_per_event",
    }
    workload_ids: list[str] = []
    for category in sorted(BUDGET_CATEGORY_KEYS):
        rows = workloads.get(category)
        if not isinstance(rows, list) or not rows:
            errors.append(f"scale_assumption_stage_empty:{category}")
            continue
        for index, row in enumerate(rows):
            prefix = f"{category}:{index}"
            if not isinstance(row, dict):
                errors.append(f"scale_assumption_workload_not_object:{prefix}")
                continue
            kind = row.get("resource_kind")
            expected_fields = model_fields if kind == "MODEL_CALL" else human_fields
            if kind not in {"MODEL_CALL", "HUMAN_REVIEW"}:
                errors.append(f"scale_assumption_resource_kind:{prefix}")
                continue
            if set(row) != expected_fields:
                errors.append(f"scale_assumption_workload_field_set:{prefix}")
                continue
            workload_id = row.get("workload_id")
            if not isinstance(workload_id, str) or not workload_id.strip():
                errors.append(f"scale_assumption_workload_id:{prefix}")
            else:
                workload_ids.append(workload_id)
            for quantile in ("p50", "p95"):
                count = row.get(f"{quantile}_event_count")
                if (not isinstance(count, int) or isinstance(count, bool) or count <= 0):
                    errors.append(f"scale_assumption_event_count:{prefix}:{quantile}")
                wall = row.get(f"{quantile}_wall_clock_seconds_per_event")
                if _nonnegative(wall) is None:
                    errors.append(f"scale_assumption_wall_clock:{prefix}:{quantile}")
            if kind == "MODEL_CALL":
                provider = row.get("provider")
                revision = row.get("model_revision")
                if (not isinstance(provider, str) or not provider.strip()
                        or not isinstance(revision, str) or not revision.strip()
                        or f"{provider}::{revision}" not in rate_card.get("rates", {})):
                    errors.append(f"scale_assumption_model_rate:{prefix}")
                for quantile in ("p50", "p95"):
                    values = [row.get(f"{quantile}_{name}_tokens_per_event")
                              for name in ("input", "cached_input", "output")]
                    if any(not isinstance(value, int) or isinstance(value, bool)
                           or value < 0 for value in values):
                        errors.append(f"scale_assumption_tokens:{prefix}:{quantile}")
                    elif values[1] > values[0]:
                        errors.append(f"scale_assumption_cached_tokens:{prefix}:{quantile}")
            else:
                identity = row.get("reviewer_identity")
                if (not isinstance(identity, str) or not identity.strip()
                        or identity not in rate_card.get("labor_rates", {})):
                    errors.append(f"scale_assumption_labor_rate:{prefix}")
                for quantile in ("p50", "p95"):
                    if _numeric(row.get(
                            f"{quantile}_reviewer_minutes_per_event")) is None or float(
                                row[f"{quantile}_reviewer_minutes_per_event"]) <= 0:
                        errors.append(
                            f"scale_assumption_reviewer_minutes:{prefix}:{quantile}")
            for suffix in [key[4:] for key in row if key.startswith("p50_")]:
                p50 = _numeric(row.get(f"p50_{suffix}"))
                p95 = _numeric(row.get(f"p95_{suffix}"))
                if p50 is None or p95 is None or p50 > p95:
                    errors.append(f"scale_assumption_quantile_order:{prefix}:{suffix}")
    if len(workload_ids) != len(set(workload_ids)):
        errors.append("scale_assumption_duplicate_workload_id")
    unsigned = dict(manifest)
    supplied = unsigned.pop("manifest_digest", None)
    if supplied != digest_json(unsigned):
        errors.append("scale_assumption_manifest_digest")
    return sorted(set(errors))


def _forecast_values(manifest: dict[str, Any], rate_card: dict[str, Any],
                     quantile: str) -> tuple[dict[str, float | int], dict[str, Any]]:
    values: dict[str, float | int] = {key: 0 for key in PROJECTION_METRIC_KEYS}
    trace_rows: list[dict[str, Any]] = []
    for category in sorted(BUDGET_CATEGORY_KEYS):
        category_cost = 0.0
        for row in manifest["stage_workloads"][category]:
            count = int(row[f"{quantile}_event_count"])
            wall = float(row[f"{quantile}_wall_clock_seconds_per_event"])
            row_trace: dict[str, Any] = {
                "budget_category": category, "workload_id": row["workload_id"],
                "resource_kind": row["resource_kind"], "event_count": count,
                "wall_clock_seconds_per_event": wall,
            }
            values["total_wall_clock_minutes"] += count * wall / 60
            if row["resource_kind"] == "MODEL_CALL":
                input_tokens = int(row[f"{quantile}_input_tokens_per_event"])
                cached_tokens = int(row[
                    f"{quantile}_cached_input_tokens_per_event"])
                output_tokens = int(row[f"{quantile}_output_tokens_per_event"])
                rate = rate_card["rates"][
                    f"{row['provider']}::{row['model_revision']}"]
                row_cost = count * (
                    (input_tokens - cached_tokens) * float(rate["input_per_million"])
                    + cached_tokens * float(rate["cached_input_per_million"])
                    + output_tokens * float(rate["output_per_million"])) / 1_000_000
                values["total_model_input_tokens"] += count * input_tokens
                values["total_model_cached_input_tokens"] += count * cached_tokens
                values["total_model_output_tokens"] += count * output_tokens
                row_trace.update({"input_tokens_per_event": input_tokens,
                                  "cached_input_tokens_per_event": cached_tokens,
                                  "output_tokens_per_event": output_tokens,
                                  "rate_key": f"{row['provider']}::{row['model_revision']}",
                                  "row_cost_usd": round(row_cost, 12)})
            else:
                minutes = float(row[f"{quantile}_reviewer_minutes_per_event"])
                hourly = float(rate_card["labor_rates"][row["reviewer_identity"]])
                row_cost = count * minutes * hourly / 60
                values["total_reviewer_minutes"] += count * minutes
                row_trace.update({"reviewer_minutes_per_event": minutes,
                                  "reviewer_identity": row["reviewer_identity"],
                                  "hourly_rate_usd": hourly,
                                  "row_cost_usd": round(row_cost, 12)})
            category_cost += row_cost
            trace_rows.append(row_trace)
        values[category] = round(category_cost, 12)
    values["total_program_usd"] = round(sum(
        float(values[key]) for key in BUDGET_CATEGORY_KEYS), 12)
    single_item = manifest["single_item_wall_clock_seconds"]
    values["p95_single_item_wall_clock_seconds"] = float(single_item[quantile])
    values["total_reviewer_minutes"] = round(
        float(values["total_reviewer_minutes"]), 6)
    values["total_wall_clock_minutes"] = round(
        float(values["total_wall_clock_minutes"]), 6)
    return values, {"quantile": quantile, "workloads": trace_rows,
                    "result": values}


def build_scale_projection(*, assumption_manifest: dict[str, Any] | None,
                           cost_events: Iterable[dict[str, Any]],
                           expected_event_manifest: dict[str, Any] | None,
                           source_event_manifest: dict[str, Any] | None,
                           rate_card: dict[str, Any] | None,
                           generated_at: str) -> dict[str, Any]:
    """从实际计量、费率卡和预登记工作量假设唯一生成正式预测。"""
    if validate_rate_card(rate_card):
        raise ValueError("rate_card_invalid")
    assert rate_card is not None
    rows, report = _closed_metering_report(
        cost_events, rate_card=rate_card,
        expected_event_manifest=expected_event_manifest,
        source_event_manifest=source_event_manifest)
    errors = _validate_scale_assumption_manifest(
        assumption_manifest, report=report, rate_card=rate_card)
    generated_dt = _utc_datetime(generated_at)
    approved_dt = _utc_datetime(
        (assumption_manifest or {}).get("approved_at"))
    if generated_dt is None or approved_dt is None or approved_dt > generated_dt:
        errors.append("scale_projection_generation_time")
    if errors:
        raise ValueError(";".join(sorted(set(errors))))
    assert assumption_manifest is not None
    p50, p50_trace = _forecast_values(assumption_manifest, rate_card, "p50")
    p95, p95_trace = _forecast_values(assumption_manifest, rate_card, "p95")
    if any(float(p50[key]) > float(p95[key]) for key in PROJECTION_METRIC_KEYS):
        raise ValueError("scale_projection_quantile_order")
    trace = {
        "formula_version": "eval-spine-scale-formula-v1",
        "rate_card_digest": rate_card["rate_card_digest"],
        "assumption_manifest_digest": assumption_manifest["manifest_digest"],
        "basis_event_digests": [row["event_digest"] for row in sorted(
            rows, key=lambda item: item["event_id"])],
        "p50": p50_trace, "p95": p95_trace,
    }
    projection = {
        "schema_version": "eval-spine-scale-projection-v1",
        "price_snapshot_id": rate_card["snapshot_id"],
        "generated_at": generated_at,
        "basis_metering_report_digest": report["report_digest"],
        "basis_event_record_manifest_digest": report[
            "event_record_manifest_digest"],
        "basis_event_count": report["event_count"],
        "assumption_manifest_digest": assumption_manifest["manifest_digest"],
        "rate_card_digest": rate_card["rate_card_digest"],
        "calculation_trace_digest": digest_json(trace),
        "p50": p50, "p95": p95, "projection_digest": "",
    }
    unsigned = dict(projection)
    unsigned.pop("projection_digest")
    projection["projection_digest"] = digest_json(unsigned)
    return projection


def accounting_integrity_gate(cost_events: Iterable[dict[str, Any]] = (), *,
                              rate_card: dict[str, Any] | None = None,
                              expected_event_manifest: dict[str, Any] | None = None,
                              source_event_manifest: dict[str, Any] | None = None,
                              as_of: str | None = None) -> dict[str, Any]:
    """记账完整性硬门（拨付制下唯一 STOP 语义：记账缺失=停）。

    依裁决 #4 取代 budget_gate（M1-C2 迁移）：不检查任何总体预算批准或
    hard ceiling；金额、令牌与吞吐总量仅作诊断遥测随决策附带输出。
    DeepSeek 30 元/日窄门由 external_llm.py 独立承载，保留不动，不经本门。
    拦截面：事件合同无效、关键字段缺失、事件/回执重复、与预登记清单或
    append-only 源清单不符、费率卡不可复算——任一命中即 STOP。
    """
    rows = list(cost_events)
    report = metering_report(rows, rate_card=rate_card,
                             expected_event_manifest=expected_event_manifest,
                             source_event_manifest=source_event_manifest)
    failed_gates = sorted(key for key, ok in report["gates"].items() if not ok)
    passed = report["qualified"] is True
    value = {
        "schema_version": "eval-spine-accounting-decision-v1",
        "passed": passed,
        "status": "PASS" if passed else "STOP_COST_ACCOUNTING_MISSING",
        "checked_at": as_of,
        "metering_report_digest": report.get("report_digest"),
        "rate_card_digest": ((rate_card or {}).get("rate_card_digest")
                             if isinstance(rate_card, dict) else None),
        "expected_event_manifest_digest": (
            (expected_event_manifest or {}).get("manifest_digest")
            if isinstance(expected_event_manifest, dict) else None),
        "source_event_manifest_digest": (
            (source_event_manifest or {}).get("manifest_digest")
            if isinstance(source_event_manifest, dict) else None),
        "failed_gates": failed_gates,
        "diagnostic_telemetry": {
            "event_count": report["event_count"],
            "total_program_cost_to_date_usd": report[
                "total_program_cost_to_date_usd"],
            "total_model_cost_usd": report["total_model_cost_usd"],
            "total_human_cost_usd": report["total_human_cost_usd"],
            "total_input_tokens": report["total_input_tokens"],
            "total_cached_input_tokens": report["total_cached_input_tokens"],
            "total_output_tokens": report["total_output_tokens"],
            "total_reviewer_minutes": report["total_reviewer_minutes"],
            "total_wall_clock_seconds": report["total_wall_clock_seconds"],
            "p95_single_item_wall_clock_seconds": report[
                "p95_single_item_wall_clock_seconds"],
        },
        "budget_blocking": False,
        "decision_digest": "",
    }
    unsigned = dict(value)
    unsigned.pop("decision_digest")
    value["decision_digest"] = digest_json(unsigned)
    return value
