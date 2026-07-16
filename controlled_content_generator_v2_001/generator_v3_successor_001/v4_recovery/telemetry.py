"""Provider-neutral telemetry and V1.1 run-manifest contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from . import contract

STAGES = frozenset({"AUTHOR_GENERATION", "MACHINE_GATE", "HUMAN_REVIEW", "METRICS"})
STATUSES = frozenset({"SUCCESS", "FAILED", "ABORTED"})
OPERATION_STAGES = {
    "AUTHOR_GENERATION": "AUTHOR_GENERATION",
    "DETERMINISTIC_GATE": "MACHINE_GATE",
    "CONTENT_REVIEW": "HUMAN_REVIEW",
    "FACT_REVIEW": "HUMAN_REVIEW",
    "METRICS_AGGREGATION": "METRICS",
}
MODEL_FIELDS = ("provider", "model_family", "model_revision", "reasoning_effort",
                "temperature", "top_p", "seed")
USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens",
                "reasoning_tokens", "total_tokens")


def unavailable(reason: str) -> dict[str, str]:
    return {"availability": "unavailable",
            "reason": contract.as_text(reason, "E_V4_TELEMETRY_UNAVAILABLE_REASON")}


def _is_unavailable(value: Any) -> bool:
    return (isinstance(value, Mapping) and value.get("availability") == "unavailable"
            and isinstance(value.get("reason"), str) and bool(value["reason"].strip()))


def _available_or_unavailable(value: Any, code: str, kinds: tuple[type, ...]) -> None:
    if _is_unavailable(value):
        return
    contract.require(isinstance(value, kinds) and not isinstance(value, bool), code)
    if str in kinds and isinstance(value, str):
        contract.as_text(value, code)


def _digest_or_unavailable(value: Any, code: str) -> None:
    if _is_unavailable(value):
        return
    digest = contract.as_text(value, code)
    contract.require(len(digest) == 64 and all(character in "0123456789abcdef"
                                               for character in digest), code)


def _timestamp(value: Any, code: str) -> datetime:
    text = contract.as_text(value, code)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise contract.ContractError(code) from error
    contract.require(parsed.tzinfo is not None, code, "timezone_required")
    return parsed


def make_event(
    *,
    event_id: str,
    run_id: str,
    batch_id: str,
    stage: str,
    operation_kind: str,
    request_id: str,
    attempt_index: int,
    status: str,
    started_at: str,
    completed_at: str,
    input_digest: str,
    output_digest: Any,
    provider_call_id: Any,
    reviewer_minutes: Any,
    model_config: Mapping[str, Any],
    usage: Mapping[str, Any],
    cost: Mapping[str, Any],
    retry_count: int = 0,
    retry_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    start = _timestamp(started_at, "E_V4_TELEMETRY_START")
    end = _timestamp(completed_at, "E_V4_TELEMETRY_END")
    duration_ms = int(round((end - start).total_seconds() * 1000))
    event: dict[str, Any] = {
        "schema_version": contract.TELEMETRY_EVENT_SCHEMA,
        "event_id": event_id,
        "run_id": run_id,
        "batch_id": batch_id,
        "stage": stage,
        "operation_kind": operation_kind,
        "request_id": request_id,
        "attempt_index": attempt_index,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "input_digest": input_digest,
        "output_digest": output_digest,
        "provider_call_id": provider_call_id,
        "reviewer_minutes": reviewer_minutes,
        "model_config": dict(model_config),
        "usage": dict(usage),
        "cost": dict(cost),
        "retry_count": retry_count,
        "retry_reasons": list(retry_reasons),
        "secret_material_recorded": False,
        "event_digest": "",
    }
    contract.close_digest(event, "event_digest")
    validate_event(event)
    return event


def validate_event(event: Mapping[str, Any]) -> None:
    expected = {
        "schema_version", "event_id", "run_id", "batch_id", "stage", "operation_kind",
        "request_id",
        "attempt_index", "status", "started_at", "completed_at", "duration_ms",
        "input_digest", "output_digest", "provider_call_id", "reviewer_minutes",
        "model_config", "usage", "cost",
        "retry_count", "retry_reasons", "secret_material_recorded", "event_digest",
    }
    contract.exact_fields(event, expected, "E_V4_TELEMETRY_FIELDS")
    contract.require(event["schema_version"] == contract.TELEMETRY_EVENT_SCHEMA,
                     "E_V4_TELEMETRY_SCHEMA")
    for field in ("event_id", "run_id", "batch_id", "request_id"):
        contract.as_text(event[field], f"E_V4_TELEMETRY_TEXT:{field}")
    _digest_or_unavailable(event["input_digest"], "E_V4_TELEMETRY_INPUT_DIGEST")
    contract.require(event["stage"] in STAGES, "E_V4_TELEMETRY_STAGE")
    contract.require(event["operation_kind"] in OPERATION_STAGES and
                     OPERATION_STAGES[event["operation_kind"]] == event["stage"],
                     "E_V4_TELEMETRY_OPERATION_STAGE")
    contract.require(event["status"] in STATUSES, "E_V4_TELEMETRY_STATUS")
    contract.as_int(event["attempt_index"], "E_V4_TELEMETRY_ATTEMPT", minimum=0)
    start = _timestamp(event["started_at"], "E_V4_TELEMETRY_START")
    end = _timestamp(event["completed_at"], "E_V4_TELEMETRY_END")
    expected_duration = int(round((end - start).total_seconds() * 1000))
    contract.require(expected_duration >= 0 and event["duration_ms"] == expected_duration,
                     "E_V4_TELEMETRY_DURATION")
    _digest_or_unavailable(event["output_digest"], "E_V4_TELEMETRY_OUTPUT_DIGEST")
    _available_or_unavailable(event["provider_call_id"],
                              "E_V4_TELEMETRY_PROVIDER_CALL_ID", (str,))
    _available_or_unavailable(event["reviewer_minutes"],
                              "E_V4_TELEMETRY_REVIEWER_MINUTES", (int, float))
    if not _is_unavailable(event["reviewer_minutes"]):
        contract.require(float(event["reviewer_minutes"]) >= 0,
                         "E_V4_TELEMETRY_REVIEWER_MINUTES")
    model = contract.as_mapping(event["model_config"], "E_V4_TELEMETRY_MODEL")
    contract.exact_fields(model, MODEL_FIELDS, "E_V4_TELEMETRY_MODEL_FIELDS")
    for field in ("provider", "model_family", "model_revision", "reasoning_effort"):
        _available_or_unavailable(model[field], f"E_V4_TELEMETRY_MODEL:{field}", (str,))
    for field in ("temperature", "top_p", "seed"):
        _available_or_unavailable(model[field], f"E_V4_TELEMETRY_MODEL:{field}",
                                  (int, float))
    usage = contract.as_mapping(event["usage"], "E_V4_TELEMETRY_USAGE")
    contract.exact_fields(usage, USAGE_FIELDS, "E_V4_TELEMETRY_USAGE_FIELDS")
    for field in USAGE_FIELDS:
        if _is_unavailable(usage[field]):
            continue
        contract.as_int(usage[field], f"E_V4_TELEMETRY_USAGE:{field}", minimum=0)
    if all(not _is_unavailable(usage[field]) for field in USAGE_FIELDS):
        contract.require(usage["cached_input_tokens"] <= usage["input_tokens"],
                         "E_V4_TELEMETRY_CACHED_INPUT_SUBSET")
        contract.require(usage["reasoning_tokens"] <= usage["output_tokens"],
                         "E_V4_TELEMETRY_REASONING_OUTPUT_SUBSET")
        expected_total = usage["input_tokens"] + usage["output_tokens"]
        contract.require(usage["total_tokens"] == expected_total,
                         "E_V4_TELEMETRY_TOKEN_TOTAL")
    cost = contract.as_mapping(event["cost"], "E_V4_TELEMETRY_COST")
    contract.exact_fields(cost, {"amount", "currency", "rate_card_ref"},
                          "E_V4_TELEMETRY_COST_FIELDS")
    if _is_unavailable(cost["amount"]):
        contract.require(_is_unavailable(cost["currency"]) and
                         _is_unavailable(cost["rate_card_ref"]),
                         "E_V4_TELEMETRY_COST_CLOSURE")
    else:
        contract.as_number(cost["amount"], "E_V4_TELEMETRY_COST_AMOUNT", minimum=0)
        contract.as_text(cost["currency"], "E_V4_TELEMETRY_COST_CURRENCY")
        contract.as_text(cost["rate_card_ref"], "E_V4_TELEMETRY_RATE_CARD")
    retry_count = contract.as_int(event["retry_count"], "E_V4_TELEMETRY_RETRY", minimum=0)
    retry_reasons = contract.text_list(event["retry_reasons"],
                                       "E_V4_TELEMETRY_RETRY_REASONS",
                                       allow_empty=True)
    contract.require(len(retry_reasons) == retry_count, "E_V4_TELEMETRY_RETRY_CLOSURE")
    if event["operation_kind"] == "AUTHOR_GENERATION":
        contract.require(event["attempt_index"] == 1 and retry_count == 0,
                         "E_V4_TELEMETRY_QUALIFICATION_RETRY_FORBIDDEN")
    else:
        contract.require(event["attempt_index"] == 0,
                         "E_V4_TELEMETRY_NON_AUTHOR_ATTEMPT")
    contract.require(event["secret_material_recorded"] is False,
                     "E_V4_TELEMETRY_SECRET_MATERIAL")
    contract.validate_digest(event, "event_digest", "E_V4_TELEMETRY_DIGEST")


def summarize_events(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    event_by_id = contract.unique_by(events, "event_id", "E_V4_TELEMETRY_EVENT_DUP")
    unavailable_paths: list[str] = []
    token_totals = {field: 0 for field in USAGE_FIELDS}
    currencies: dict[str, float] = {}
    duration_ms = 0
    reviewer_minutes_total = 0.0
    for event in event_by_id.values():
        validate_event(event)
        duration_ms += int(event["duration_ms"])
        for field in MODEL_FIELDS:
            if _is_unavailable(event["model_config"][field]):
                unavailable_paths.append(f"{event['event_id']}:model_config.{field}")
        if _is_unavailable(event["input_digest"]):
            unavailable_paths.append(f"{event['event_id']}:input_digest")
        if _is_unavailable(event["output_digest"]):
            unavailable_paths.append(f"{event['event_id']}:output_digest")
        if _is_unavailable(event["provider_call_id"]):
            unavailable_paths.append(f"{event['event_id']}:provider_call_id")
        if _is_unavailable(event["reviewer_minutes"]):
            unavailable_paths.append(f"{event['event_id']}:reviewer_minutes")
        else:
            reviewer_minutes_total += float(event["reviewer_minutes"])
        for field in USAGE_FIELDS:
            value = event["usage"][field]
            if _is_unavailable(value):
                unavailable_paths.append(f"{event['event_id']}:usage.{field}")
            else:
                token_totals[field] += int(value)
        if _is_unavailable(event["cost"]["amount"]):
            unavailable_paths.append(f"{event['event_id']}:cost")
        else:
            currency = str(event["cost"]["currency"])
            currencies[currency] = currencies.get(currency, 0.0) + float(
                event["cost"]["amount"])
    summary: dict[str, Any] = {
        "schema_version": "gate1-v4-telemetry-summary-v1",
        "event_count": len(event_by_id),
        "event_manifest_digest": contract.sha256_text(contract.canonical_json([
            {"event_id": event_id, "event_digest": event_by_id[event_id]["event_digest"]}
            for event_id in sorted(event_by_id)
        ])),
        "total_duration_ms": duration_ms,
        "reviewer_minutes_total_for_available_events": round(reviewer_minutes_total, 6),
        "token_totals_for_available_events": token_totals,
        "cost_totals_for_available_events": {
            key: round(currencies[key], 8) for key in sorted(currencies)},
        "unavailable_paths": sorted(unavailable_paths),
        "telemetry_complete": not unavailable_paths,
        "summary_digest": "",
    }
    contract.close_digest(summary, "summary_digest")
    return summary


def validate_generation_coverage(
    events: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
    *,
    run_id: str,
    batch_id: str,
) -> None:
    request_by_id = contract.unique_by(requests, "request_id",
                                       "E_V4_TELEMETRY_REQUEST_DUP")
    output_by_id = contract.unique_by(outputs, "request_id",
                                      "E_V4_TELEMETRY_OUTPUT_DUP")
    contract.require(set(request_by_id) == set(output_by_id),
                     "E_V4_TELEMETRY_OUTPUT_COVERAGE")
    generation = []
    for event in events:
        validate_event(event)
        contract.require(event["run_id"] == run_id and event["batch_id"] == batch_id,
                         "E_V4_TELEMETRY_RUN_JOIN")
        if event["operation_kind"] == "AUTHOR_GENERATION":
            generation.append(event)
    index = contract.unique_by(generation, "request_id", "E_V4_TELEMETRY_GENERATION_DUP")
    contract.require(set(index) == set(request_by_id),
                     "E_V4_TELEMETRY_GENERATION_COVERAGE")
    for request_id, event in index.items():
        contract.require(event["status"] == "SUCCESS",
                         "E_V4_TELEMETRY_GENERATION_STATUS", request_id)
        contract.require(event["input_digest"] ==
                         request_by_id[request_id]["request_digest"],
                         "E_V4_TELEMETRY_GENERATION_INPUT_JOIN", request_id)
        contract.require(event["output_digest"] ==
                         output_by_id[request_id]["output_digest"],
                         "E_V4_TELEMETRY_GENERATION_OUTPUT_JOIN", request_id)
        contract.require(not _is_unavailable(event["provider_call_id"]),
                         "E_V4_TELEMETRY_PROVIDER_CALL_REQUIRED", request_id)


def object_manifest_digest(
    rows: Sequence[Mapping[str, Any]],
    *,
    id_field: str,
    digest_field: str,
) -> str:
    index = contract.unique_by(rows, id_field, "E_V4_TELEMETRY_MANIFEST_DUP")
    manifest_rows = []
    for object_id in sorted(index):
        digest = contract.as_text(index[object_id].get(digest_field),
                                  "E_V4_TELEMETRY_MANIFEST_DIGEST")
        contract.require(len(digest) == 64, "E_V4_TELEMETRY_MANIFEST_DIGEST")
        manifest_rows.append({id_field: object_id, digest_field: digest})
    return contract.sha256_text(contract.canonical_json(manifest_rows))


def review_record_digest(review: Mapping[str, Any]) -> str:
    return contract.sha256_text(contract.canonical_json(dict(review)))


def review_manifest_digest(reviews: Sequence[Mapping[str, Any]]) -> str:
    rows = [
        {"request_id": contract.as_text(review.get("request_id"),
                                        "E_V4_TELEMETRY_REVIEW_ID"),
         "review_digest": review_record_digest(review)}
        for review in reviews
    ]
    return object_manifest_digest(rows, id_field="request_id",
                                  digest_field="review_digest")


def model_config_binding_ref(requests: Sequence[Mapping[str, Any]]) -> str:
    rows = sorted(
        ({"request_id": contract.as_text(request.get("request_id"),
                                         "E_V4_TELEMETRY_MODEL_BINDING_ID"),
          "author_identity": contract.as_text(request.get("author_identity"),
                                              "E_V4_TELEMETRY_MODEL_BINDING_AUTHOR"),
          "model_config_ref": contract.as_text(request.get("model_config_ref"),
                                               "E_V4_TELEMETRY_MODEL_BINDING_REF")}
         for request in requests),
        key=lambda row: row["request_id"],
    )
    return f"sha256:{contract.sha256_text(contract.canonical_json(rows))}"


def evaluation_input_digest(
    gate_report: Mapping[str, Any],
    content_reviews: Sequence[Mapping[str, Any]],
    fact_reviews: Sequence[Mapping[str, Any]],
) -> str:
    value = {
        "gate_report_digest": gate_report["report_digest"],
        "content_review_manifest_digest": review_manifest_digest(content_reviews),
        "fact_review_manifest_digest": review_manifest_digest(fact_reviews),
    }
    return contract.sha256_text(contract.canonical_json(value))


def validate_qualification_coverage(
    events: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
    gate_report: Mapping[str, Any],
    content_reviews: Sequence[Mapping[str, Any]],
    fact_reviews: Sequence[Mapping[str, Any]],
    batch_metrics: Mapping[str, Any],
    *,
    run_id: str,
    batch_id: str,
) -> None:
    """Require exact author, gate, two-review, and metric event coverage."""
    request_by_id = contract.unique_by(requests, "request_id",
                                       "E_V4_TELEMETRY_REQUEST_DUP")
    output_by_id = contract.unique_by(outputs, "request_id",
                                      "E_V4_TELEMETRY_OUTPUT_DUP")
    content_by_id = contract.unique_by(content_reviews, "request_id",
                                       "E_V4_TELEMETRY_CONTENT_REVIEW_DUP")
    fact_by_id = contract.unique_by(fact_reviews, "request_id",
                                    "E_V4_TELEMETRY_FACT_REVIEW_DUP")
    expected_ids = set(request_by_id)
    contract.require(expected_ids == set(output_by_id) == set(content_by_id) ==
                     set(fact_by_id), "E_V4_TELEMETRY_OBJECT_COVERAGE")
    contract.unique_by(events, "event_id", "E_V4_TELEMETRY_EVENT_DUP")
    grouped = {operation: [] for operation in OPERATION_STAGES}
    for event in events:
        validate_event(event)
        contract.require(event["run_id"] == run_id and event["batch_id"] == batch_id,
                         "E_V4_TELEMETRY_RUN_JOIN")
        contract.require(event["status"] == "SUCCESS",
                         "E_V4_TELEMETRY_QUALIFICATION_STATUS",
                         str(event["event_id"]))
        contract.require(not _is_unavailable(event["provider_call_id"]),
                         "E_V4_TELEMETRY_PROVIDER_CALL_REQUIRED",
                         str(event["event_id"]))
        grouped[str(event["operation_kind"])].append(event)

    for operation in ("AUTHOR_GENERATION", "DETERMINISTIC_GATE",
                      "CONTENT_REVIEW", "FACT_REVIEW"):
        index = contract.unique_by(grouped[operation], "request_id",
                                   f"E_V4_TELEMETRY_{operation}_DUP")
        contract.require(set(index) == expected_ids,
                         f"E_V4_TELEMETRY_{operation}_COVERAGE")
    metrics_events = grouped["METRICS_AGGREGATION"]
    contract.require(len(metrics_events) == 1 and
                     metrics_events[0]["request_id"] == f"BATCH::{batch_id}",
                     "E_V4_TELEMETRY_METRICS_COVERAGE")

    for request_id in sorted(expected_ids):
        author = next(event for event in grouped["AUTHOR_GENERATION"]
                      if event["request_id"] == request_id)
        machine = next(event for event in grouped["DETERMINISTIC_GATE"]
                       if event["request_id"] == request_id)
        content = next(event for event in grouped["CONTENT_REVIEW"]
                       if event["request_id"] == request_id)
        fact = next(event for event in grouped["FACT_REVIEW"]
                    if event["request_id"] == request_id)
        contract.require(author["input_digest"] ==
                         request_by_id[request_id]["request_digest"] and
                         author["output_digest"] ==
                         output_by_id[request_id]["output_digest"],
                         "E_V4_TELEMETRY_AUTHOR_JOIN", request_id)
        contract.require(machine["input_digest"] ==
                         output_by_id[request_id]["output_digest"] and
                         machine["output_digest"] == gate_report["report_digest"],
                         "E_V4_TELEMETRY_MACHINE_JOIN", request_id)
        contract.require(content["input_digest"] ==
                         output_by_id[request_id]["output_digest"] and
                         content["output_digest"] ==
                         review_record_digest(content_by_id[request_id]),
                         "E_V4_TELEMETRY_CONTENT_REVIEW_JOIN", request_id)
        contract.require(fact["input_digest"] ==
                         output_by_id[request_id]["output_digest"] and
                         fact["output_digest"] == review_record_digest(fact_by_id[request_id]),
                         "E_V4_TELEMETRY_FACT_REVIEW_JOIN", request_id)
    metrics_event = metrics_events[0]
    contract.require(metrics_event["input_digest"] == evaluation_input_digest(
        gate_report, content_reviews, fact_reviews) and
        metrics_event["output_digest"] == batch_metrics["metrics_digest"],
        "E_V4_TELEMETRY_METRICS_JOIN")


def build_run_manifest(**values: Any) -> dict[str, Any]:
    manifest = {
        "schema_version": contract.RUN_MANIFEST_SCHEMA,
        "run_id": values["run_id"],
        "stage_gate": values["stage_gate"],
        "batch_id": values["batch_id"],
        "generator_version": contract.GENERATOR_VERSION,
        "rule_version": contract.RULE_VERSION,
        "schema_version_ref": values["schema_version_ref"],
        "content_product_profile_version": values["content_product_profile_version"],
        "evaluation_case_set_version": values["evaluation_case_set_version"],
        "checker_versions": dict(values["checker_versions"]),
        "model_or_engine_config_ref": values["model_or_engine_config_ref"],
        "randomization_config": dict(values["randomization_config"]),
        "input_manifest_ref": values["input_manifest_ref"],
        "input_manifest_digest": values["input_manifest_digest"],
        "output_manifest_ref": values["output_manifest_ref"],
        "output_manifest_digest": values["output_manifest_digest"],
        "retry_count": values.get("retry_count", 0),
        "retry_reasons": list(values.get("retry_reasons", [])),
        "started_at": values["started_at"],
        "completed_at": values["completed_at"],
        "human_review_batch_ref": values["human_review_batch_ref"],
        "telemetry_summary_digest": values["telemetry_summary_digest"],
        "secret_material_recorded": False,
        "manifest_digest": "",
    }
    contract.close_digest(manifest, "manifest_digest")
    validate_run_manifest(manifest)
    return manifest


def validate_run_manifest(manifest: Mapping[str, Any]) -> None:
    expected = {
        "schema_version", "run_id", "stage_gate", "batch_id", "generator_version",
        "rule_version", "schema_version_ref", "content_product_profile_version",
        "evaluation_case_set_version", "checker_versions", "model_or_engine_config_ref",
        "randomization_config", "input_manifest_ref", "input_manifest_digest",
        "output_manifest_ref", "output_manifest_digest", "retry_count", "retry_reasons",
        "started_at", "completed_at", "human_review_batch_ref",
        "telemetry_summary_digest", "secret_material_recorded", "manifest_digest",
    }
    contract.exact_fields(manifest, expected, "E_V4_RUN_MANIFEST_FIELDS")
    contract.require(manifest["schema_version"] == contract.RUN_MANIFEST_SCHEMA,
                     "E_V4_RUN_MANIFEST_SCHEMA")
    for field in ("run_id", "stage_gate", "batch_id", "schema_version_ref",
                  "content_product_profile_version", "evaluation_case_set_version",
                  "model_or_engine_config_ref", "input_manifest_ref",
                  "input_manifest_digest", "output_manifest_ref", "output_manifest_digest",
                  "human_review_batch_ref", "telemetry_summary_digest"):
        contract.as_text(manifest[field], f"E_V4_RUN_MANIFEST_TEXT:{field}")
    contract.require(manifest["generator_version"] == contract.GENERATOR_VERSION and
                     manifest["rule_version"] == contract.RULE_VERSION,
                     "E_V4_RUN_MANIFEST_VERSION")
    contract.require(isinstance(manifest["checker_versions"], Mapping) and
                     bool(manifest["checker_versions"]), "E_V4_RUN_MANIFEST_CHECKERS")
    contract.require(isinstance(manifest["randomization_config"], Mapping),
                     "E_V4_RUN_MANIFEST_RANDOMIZATION")
    contract.require(manifest["randomization_config"].get(
        "batch_id_affects_assignment") is False,
        "E_V4_RUN_MANIFEST_BATCH_ALLOCATION_FORBIDDEN")
    retries = contract.as_int(manifest["retry_count"], "E_V4_RUN_MANIFEST_RETRY",
                              minimum=0)
    reasons = contract.text_list(manifest["retry_reasons"],
                                 "E_V4_RUN_MANIFEST_REASONS", allow_empty=True)
    contract.require(retries == len(reasons), "E_V4_RUN_MANIFEST_RETRY_CLOSURE")
    contract.require(retries == 0, "E_V4_RUN_MANIFEST_QUALIFICATION_RETRY_FORBIDDEN")
    contract.require(_timestamp(manifest["completed_at"], "E_V4_RUN_MANIFEST_END") >=
                     _timestamp(manifest["started_at"], "E_V4_RUN_MANIFEST_START"),
                     "E_V4_RUN_MANIFEST_TIME_ORDER")
    contract.require(manifest["secret_material_recorded"] is False,
                     "E_V4_RUN_MANIFEST_SECRET")
    contract.validate_digest(manifest, "manifest_digest", "E_V4_RUN_MANIFEST_DIGEST")


def to_eval_spine_cost_event(event: Mapping[str, Any], *,
                              budget_category: str) -> dict[str, Any]:
    """Adapt one v4 detail event to the audit spine's flat cost-event contract."""
    validate_event(event)
    unavailable_reasons: dict[str, str] = {}

    def available(field: str, value: Any) -> Any:
        if _is_unavailable(value):
            unavailable_reasons[field] = str(value["reason"])
            return None
        return value

    if event["operation_kind"] == "AUTHOR_GENERATION":
        attempt_id: str | None = f"{event['request_id']}:attempt:{event['attempt_index']}"
    else:
        attempt_id = None
        unavailable_reasons["attempt_id"] = "not applicable to non-author operation"
    provider = available("provider", event["model_config"]["provider"])
    model_revision = available("model_revision",
                               event["model_config"]["model_revision"])
    provider_call_id = available("provider_call_id", event["provider_call_id"])
    input_tokens = available("input_tokens", event["usage"]["input_tokens"])
    cached_input_tokens = available(
        "cached_input_tokens", event["usage"]["cached_input_tokens"])
    output_tokens = available("output_tokens", event["usage"]["output_tokens"])
    price_snapshot_id = available("price_snapshot_id", event["cost"]["rate_card_ref"])
    reviewer_minutes = available("reviewer_minutes", event["reviewer_minutes"])
    has_human_resource = isinstance(reviewer_minutes, (int, float)) and reviewer_minutes > 0
    if has_human_resource:
        reviewer_identity = None
        labor_rate_snapshot_id = None
        human_cost_usd = None
        unavailable_reasons["reviewer_identity"] = (
            "v4 telemetry does not record reviewer identity")
        unavailable_reasons["labor_rate_snapshot_id"] = (
            "v4 telemetry does not record an approved labor rate snapshot")
        unavailable_reasons["human_cost_usd"] = (
            "human cost cannot be computed without reviewer and labor rate")
    else:
        reviewer_identity = None
        labor_rate_snapshot_id = None
        human_cost_usd = 0
    if _is_unavailable(event["cost"]["amount"]):
        model_cost_usd = available("model_cost_usd", event["cost"]["amount"])
    elif event["cost"]["currency"] != "USD":
        model_cost_usd = None
        unavailable_reasons["model_cost_usd"] = (
            f"cost currency is {event['cost']['currency']}, not USD")
    else:
        model_cost_usd = event["cost"]["amount"]
    adapted: dict[str, Any] = {
        "schema_version": "eval-spine-cost-event-v1",
        "event_id": event["event_id"],
        "stage_id": event["stage"],
        "task_kind": event["operation_kind"],
        "resource_kind": "HYBRID" if has_human_resource else "MODEL_CALL",
        "budget_category": budget_category,
        "outcome_status": {"SUCCESS": "SUCCEEDED", "FAILED": "FAILED",
                           "ABORTED": "ABORTED"}[event["status"]],
        "source_telemetry_event_digest": event["event_digest"],
        "object_id": event["request_id"],
        "attempt_id": attempt_id,
        "provider": provider,
        "model_revision": model_revision,
        "provider_call_id": provider_call_id,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "output_tokens": output_tokens,
        "price_snapshot_id": price_snapshot_id,
        "model_cost_usd": model_cost_usd,
        "reviewer_minutes": reviewer_minutes,
        "reviewer_identity": reviewer_identity,
        "labor_rate_snapshot_id": labor_rate_snapshot_id,
        "human_cost_usd": human_cost_usd,
        "wall_clock_seconds": event["duration_ms"] / 1000.0,
        "unavailable_reasons": unavailable_reasons,
        "event_digest": "",
    }
    contract.close_digest(adapted, "event_digest")
    return adapted


__all__ = [
    "OPERATION_STAGES", "USAGE_FIELDS", "build_run_manifest",
    "evaluation_input_digest", "make_event", "model_config_binding_ref",
    "object_manifest_digest", "review_manifest_digest", "review_record_digest",
    "summarize_events", "to_eval_spine_cost_event", "unavailable", "validate_event",
    "validate_generation_coverage", "validate_qualification_coverage",
    "validate_run_manifest",
]
