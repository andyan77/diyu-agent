"""跨模块合同验证。

合同刻意把语义关系、风险和运行动作分开。UNKNOWN 不是失败的同义词，
更不是可自动放行的 SUPPORTED。
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Iterable

from .canonical import digest_json

RELATION_LABELS = {"SUPPORTED", "CONTRADICTED", "UNKNOWN"}
RUNTIME_ACTIONS = {"ALLOW", "HUMAN_REVIEW", "HARD_VETO"}
RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VISIBILITY_PARTITIONS = {"DEVELOPMENT", "VALIDATION", "HIDDEN"}
CASE_ORIGINS = {"NATURAL", "CHALLENGE"}


class ContractError(ValueError):
    pass


def require_fields(record: dict[str, Any], fields: Iterable[str], kind: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise ContractError(f"{kind} missing fields: {missing}")


def validate_gate1_test_assignment(value: dict[str, Any]) -> None:
    required = {
        "schema_version", "object_type", "assignment_id", "assignment_set_id",
        "case_id", "scenario_id", "scenario_digest", "profile_id",
        "family_id", "material_packet_digest", "allocation_version",
        "strategy_version", "strategy_digest",
        "argument_spine", "evidence_surface_policy", "perspective_anchor",
        "limitation_carrier", "closing_function", "paired_assignment_id",
        "forbidden_inferences",
        "stage_scope", "not_formal_content_composition_plan", "runtime_consumable",
        "publishable", "binds_enterprise_runtime_input", "counts_toward_300",
        "test_dna", "assignment_digest",
    }
    require_fields(value, required, "gate1_test_assignment")
    fixed = {
        "object_type": "gate1_test_assignment",
        "stage_scope": "GATE1_QUALIFICATION_ONLY",
        "not_formal_content_composition_plan": True,
        "runtime_consumable": False,
        "publishable": False,
        "binds_enterprise_runtime_input": False,
        "counts_toward_300": False,
    }
    for key, expected in fixed.items():
        if value.get(key) != expected:
            raise ContractError(f"{key} must equal {expected!r}")
    if value.get("case_id") != value.get("scenario_id"):
        raise ContractError("case_id and scenario_id must be identical")
    dna = value.get("test_dna")
    if not isinstance(dna, dict):
        raise ContractError("test_dna must be an object")
    require_fields(dna, ("entry_lens", "evidence_route", "boundary_carrier",
                         "closing_function", "strategy_id", "strategy_source",
                         "strategy_frozen"), "test_dna")
    if value.get("profile_id") in {"CP01", "CP02", "CP03"}:
        if dna.get("strategy_source") != "PROFILE_OVERRIDE" or dna.get("strategy_frozen") is not True:
            raise ContractError("CP01/02/03 must retain frozen profile strategies")
    forbidden_names = {"content_composition_plan", "expression_plan", "runtime_plan"}
    if forbidden_names & set(value):
        raise ContractError("first-gate assignment may not masquerade as a formal plan")
    unsigned = dict(value)
    supplied = unsigned.pop("assignment_digest")
    expected = digest_json(unsigned)
    if supplied != expected:
        raise ContractError("assignment_digest mismatch")


def validate_dataset_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """校验来源组不跨 visibility 分区；自然/挑战是独立维度。"""
    rows = list(rows)
    case_ids: set[str] = set()
    case_digests: set[str] = set()
    group_partition: dict[str, str] = {}
    digest_group: dict[str, str] = {}
    errors: list[str] = []
    cells: Counter[str] = Counter()
    allowed_fields = {"case_id", "case_origin", "visibility_partition",
                      "source_group_id", "case_digest"}
    for row in rows:
        try:
            require_fields(row, ("case_id", "case_origin", "visibility_partition",
                                 "source_group_id", "case_digest"), "dataset row")
        except ContractError as exc:
            errors.append(str(exc))
            continue
        case_id = str(row["case_id"])
        if set(row) != allowed_fields:
            errors.append(f"public manifest field set mismatch: {case_id}")
        origin = str(row["case_origin"])
        partition = str(row["visibility_partition"])
        if origin not in CASE_ORIGINS or partition not in VISIBILITY_PARTITIONS:
            errors.append(f"invalid split labels for {row['case_id']}")
        if not case_id or case_id in case_ids:
            errors.append(f"duplicate case_id {case_id}")
        case_ids.add(case_id)
        group = str(row["source_group_id"])
        if not group:
            errors.append(f"empty source_group_id {case_id}")
        previous = group_partition.setdefault(group, partition)
        if previous != partition:
            errors.append(f"source_group leakage {group}: {previous}/{partition}")
        cells[f"{origin}:{partition}"] += 1
        case_digest = row.get("case_digest")
        if (not isinstance(case_digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", case_digest) is None):
            errors.append(f"invalid case_digest {case_id}")
        else:
            if case_digest in case_digests:
                errors.append(f"duplicate case_digest {case_id}")
            case_digests.add(case_digest)
            previous_group = digest_group.setdefault(case_digest, group)
            if previous_group != group:
                errors.append(
                    f"case_digest reused across source_group {case_id}: "
                    f"{previous_group}/{group}")
        if partition == "HIDDEN" and any(key in row for key in
                                         ("prompt", "source_text", "gold_label")):
            errors.append(f"hidden payload leaked in public manifest: {case_id}")
    return {"passed": not errors, "errors": sorted(errors),
            "cell_counts": dict(sorted(cells.items())), "case_count": len(rows)}


def validate_cost_event(event: dict[str, Any]) -> list[str]:
    fields = ("schema_version", "event_id", "stage_id", "task_kind", "object_id",
              "resource_kind", "budget_category", "outcome_status",
              "source_telemetry_event_digest",
              "attempt_id", "provider", "model_revision", "provider_call_id",
              "input_tokens", "cached_input_tokens", "output_tokens",
              "price_snapshot_id", "model_cost_usd", "reviewer_minutes",
              "reviewer_identity", "labor_rate_snapshot_id", "human_cost_usd",
              "wall_clock_seconds", "unavailable_reasons", "event_digest")
    errors: list[str] = []
    for field in fields:
        if field not in event:
            errors.append(f"missing:{field}")
    unavailable = event.get("unavailable_reasons", {})
    if not isinstance(unavailable, dict):
        errors.append("unavailable_reasons_must_be_object")
        unavailable = {}
    resource_kind = event.get("resource_kind")
    nullable = ("attempt_id", "provider", "model_revision", "provider_call_id",
                "input_tokens", "cached_input_tokens", "output_tokens",
                "price_snapshot_id", "model_cost_usd", "reviewer_minutes",
                "reviewer_identity", "labor_rate_snapshot_id", "human_cost_usd")
    for field in nullable:
        value = event.get(field)
        model_applicable = field in {
            "provider", "model_revision", "provider_call_id", "input_tokens",
            "cached_input_tokens", "output_tokens", "price_snapshot_id", "model_cost_usd"}
        human_applicable = field in {
            "reviewer_identity", "labor_rate_snapshot_id", "reviewer_minutes",
            "human_cost_usd"}
        required_when_null = (field == "attempt_id"
                              or model_applicable
                              and resource_kind in {"MODEL_CALL", "HYBRID"}
                              or human_applicable
                              and resource_kind in {"HUMAN_REVIEW", "HYBRID"})
        if value is None and required_when_null and not str(unavailable.get(field, "")).strip():
            errors.append(f"null_without_unavailable_reason:{field}")
        if value is not None and field in unavailable:
            errors.append(f"available_field_marked_unavailable:{field}")
    if event.get("schema_version") != "eval-spine-cost-event-v1":
        errors.append("invalid_schema_version")
    if resource_kind not in {"MODEL_CALL", "HUMAN_REVIEW", "HYBRID"}:
        errors.append("invalid_resource_kind")
    if event.get("budget_category") not in {
            "one_time_gold_and_measurement_usd", "causal_pilot_60_usd",
            "open_120_usd", "hidden_40_usd", "baseline_240_plus_60_usd"}:
        errors.append("invalid_budget_category")
    if event.get("outcome_status") not in {"SUCCEEDED", "FAILED", "ABORTED"}:
        errors.append("invalid_outcome_status")
    source_digest = event.get("source_telemetry_event_digest")
    if (not isinstance(source_digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", source_digest) is None):
        errors.append("invalid_source_telemetry_event_digest")
    for field in ("event_id", "stage_id", "task_kind", "object_id"):
        if not isinstance(event.get(field), str) or not event[field].strip():
            errors.append(f"invalid_nonempty_string:{field}")
    for field in ("input_tokens", "cached_input_tokens", "output_tokens"):
        value = event.get(field)
        if value is not None and (not isinstance(value, int)
                                  or isinstance(value, bool) or value < 0):
            errors.append(f"invalid_nonnegative_integer:{field}")
    for field in ("model_cost_usd", "reviewer_minutes", "human_cost_usd"):
        value = event.get(field)
        if value is not None and (not isinstance(value, (int, float))
                                  or isinstance(value, bool) or value < 0):
            errors.append(f"invalid_nonnegative_number:{field}")
    wall = event.get("wall_clock_seconds")
    if (not isinstance(wall, (int, float)) or isinstance(wall, bool) or wall < 0):
        errors.append("invalid_nonnegative_number:wall_clock_seconds")
    if (isinstance(event.get("cached_input_tokens"), int)
            and isinstance(event.get("input_tokens"), int)
            and event["cached_input_tokens"] > event["input_tokens"]):
        errors.append("cached_input_tokens_exceed_input_tokens")
    model_fields = ("provider", "model_revision", "provider_call_id", "input_tokens",
                    "cached_input_tokens", "output_tokens", "price_snapshot_id",
                    "model_cost_usd")
    human_fields = ("reviewer_identity", "labor_rate_snapshot_id",
                    "reviewer_minutes", "human_cost_usd")
    if resource_kind in {"MODEL_CALL", "HYBRID"} and any(
            event.get(field) is None for field in model_fields):
        errors.append("model_resource_fields_incomplete")
    if resource_kind == "HUMAN_REVIEW" and any(
            event.get(field) is not None for field in model_fields):
        errors.append("human_event_contains_model_resource")
    if resource_kind in {"HUMAN_REVIEW", "HYBRID"}:
        if (any(event.get(field) is None for field in human_fields)
                or _numeric_positive(event.get("reviewer_minutes")) is False):
            errors.append("human_resource_fields_incomplete")
    if resource_kind == "MODEL_CALL" and (
            event.get("reviewer_minutes") != 0
            or event.get("human_cost_usd") != 0
            or event.get("reviewer_identity") is not None
            or event.get("labor_rate_snapshot_id") is not None):
        errors.append("model_event_contains_human_resource")
    unsigned = dict(event)
    supplied = unsigned.pop("event_digest", None)
    if (not isinstance(supplied, str) or re.fullmatch(r"[0-9a-f]{64}", supplied) is None
            or supplied != digest_json(unsigned)):
        errors.append("event_digest_mismatch")
    return errors


def _numeric_positive(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value > 0)


def qualification_decision(artifact_integrity: bool,
                           required_gates: dict[str, bool | None]) -> dict[str, str]:
    if not artifact_integrity:
        return {"artifact_integrity_status": "FAIL",
                "m0_qualification_status": "NOT_RUN"}
    if not required_gates:
        status = "BLOCKED"
    elif any(value is False for value in required_gates.values()):
        status = "FAIL"
    elif any(value is None for value in required_gates.values()):
        status = "BLOCKED"
    else:
        status = "PASS"
    return {"artifact_integrity_status": "PASS", "m0_qualification_status": status}
