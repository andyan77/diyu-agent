"""阶段合取门、首轮提前判死与止损。"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


STAGE_GATE_KEYS = {
    "S0": {"single_assignment", "assignment_material_match",
           "whole_batch_hard_veto_metric", "first_response_retained",
           "cost_provenance", "no_plan_impersonation"},
    "M0": {"measurement_qualification", "m0_status",
           "independent_adjudication"},
    "S2": {"profile_capacity", "supported_assignments", "budget",
           "cost_latency_forecast"},
    "S3": {"causal_interpretability", "minimum_useful_effect",
           "hard_veto_zero"},
    "S4": {"first_acceptance", "formulaic", "whole_batch_hard_veto_zero",
           "blind", "route", "audit"},
    "S5": {"hidden_contract", "sample_swap_zero", "whole_batch_hard_veto_zero"},
    "S6": {"positive_240", "route_60", "per_profile_first_acceptance",
           "global_first_acceptance", "formulaic", "whole_batch_hard_veto_zero",
           "route_accuracy", "review_coverage"},
    "S7": {"v11_final_admission", "metrics_recompute", "founder_decision"},
}


def whole_batch_metrics(outputs: Iterable[dict[str, Any]], *, target_count: int,
                        max_failures_per_profile: int | None = None,
                        expected_output_ids: set[str] | None = None,
                        expected_profile_counts: dict[str, int] | None = None) -> dict[str, Any]:
    rows = list(outputs)
    output_ids = [str(row.get("output_id", "")) for row in rows]
    row_shape_valid = all(
        isinstance(row.get("output_id"), str) and bool(row["output_id"])
        and isinstance(row.get("profile_id"), str) and bool(row["profile_id"])
        and isinstance(row.get("first_acceptable"), bool)
        and isinstance(row.get("formulaic"), bool)
        and isinstance(row.get("hard_veto"), bool)
        for row in rows)
    unique_ids = len(output_ids) == len(set(output_ids)) and all(output_ids)
    expected_ids_match = (expected_output_ids is None
                          or set(output_ids) == set(expected_output_ids))
    profile_counts = Counter(str(row.get("profile_id", "")) for row in rows)
    profile_counts_match = (expected_profile_counts is None
                            or dict(profile_counts) == expected_profile_counts)
    hard_ids = sorted(str(row["output_id"]) for row in rows if row.get("hard_veto"))
    acceptable = [row for row in rows if row.get("first_acceptable")]
    formulaic_ids = sorted(str(row["output_id"]) for row in rows if row.get("formulaic"))
    failures_by_profile = Counter(str(row["profile_id"]) for row in rows
                                  if not row.get("first_acceptable"))
    first_threshold = target_count * .90
    formulaic_threshold = target_count * .10
    gates = {
        "complete_denominator": len(rows) == target_count and target_count > 0,
        "row_shape_valid": row_shape_valid,
        "unique_output_ids": bool(unique_ids),
        "expected_output_ids_match": expected_ids_match,
        "profile_coverage_match": profile_counts_match,
        "first_acceptance": len(acceptable) >= first_threshold,
        "formulaic": len(formulaic_ids) <= formulaic_threshold,
        "whole_batch_hard_veto_zero": len(hard_ids) == 0,
    }
    profile_impossible = (max_failures_per_profile is not None
                          and any(count > max_failures_per_profile
                                  for count in failures_by_profile.values()))
    gates["per_profile_failure_limit"] = not profile_impossible
    impossible = (bool(hard_ids)
                  or profile_impossible
                  or target_count - len(acceptable) > int(target_count * .10)
                  or len(formulaic_ids) > int(target_count * .10))
    return {"scope": "POSITIVE_CONTENT_QUALITY_TRIAD_ONLY_NOT_FULL_V11_ADMISSION",
            "output_count": len(rows), "first_acceptable_count": len(acceptable),
            "formulaic_item_count": len(formulaic_ids), "whole_batch_veto_ids": hard_ids,
            "duplicate_output_ids": sorted(output_id for output_id, count
                                           in Counter(output_ids).items() if count > 1),
            "profile_counts": dict(sorted(profile_counts.items())),
            "whole_batch_veto_count": len(hard_ids), "gates": gates,
            "gate_batch_qualified": all(gates.values()),
            "early_stop_impossible": impossible,
            "acceptable_set_hard_veto_count_diagnostic":
                sum(1 for row in acceptable if row.get("hard_veto"))}


def stage_decision(*, stage: str, gates: dict[str, bool | None], revision_count: int,
                   max_revisions: int = 1) -> dict[str, Any]:
    required = STAGE_GATE_KEYS.get(stage)
    missing = sorted(required - set(gates)) if required is not None else []
    unknown = sorted(set(gates) - required) if required is not None else []
    invalid_values = sorted(key for key, value in gates.items()
                            if value is not True and value is not False and value is not None)
    if required is None:
        status = "FAIL"
    elif not gates or missing:
        status = "BLOCKED"
    elif unknown or invalid_values:
        status = "FAIL"
    elif any(value is False for value in gates.values()):
        status = ("STOP_M0_MEASUREMENT_UNQUALIFIED"
                  if stage == "M0" and revision_count >= max_revisions else "FAIL")
    elif any(value is None for value in gates.values()):
        status = "BLOCKED"
    else:
        status = "PASS"
    return {"stage": stage, "status": status, "gates": gates,
            "required_gate_keys": sorted(required) if required is not None else None,
            "missing_gate_keys": missing, "unknown_gate_keys": unknown,
            "invalid_gate_value_keys": invalid_values,
            "revision_count": revision_count, "max_revisions": max_revisions}
