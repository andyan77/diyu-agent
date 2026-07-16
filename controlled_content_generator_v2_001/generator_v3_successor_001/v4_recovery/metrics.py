"""Sealed-batch qualification metrics with a true whole-batch veto gate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from . import contract, deterministic_gates


def _review_index(
    rows: Sequence[Mapping[str, Any]],
    *,
    track: str,
) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    required = ({"request_id", "output_digest", "grade", "approved",
                 "formulaic_or_near_duplicate", "hard_veto_codes"}
                if track == "content" else
                {"request_id", "output_digest", "fact_approved", "hard_veto_codes"})
    for row in rows:
        contract.exact_fields(row, required, f"E_V4_{track.upper()}_REVIEW_FIELDS")
        request_id = contract.as_text(row["request_id"], f"E_V4_{track.upper()}_REVIEW_ID")
        contract.require(request_id not in index, f"E_V4_{track.upper()}_REVIEW_DUP",
                         request_id)
        contract.as_text(row["output_digest"], f"E_V4_{track.upper()}_REVIEW_DIGEST")
        contract.unique_text_list(row["hard_veto_codes"],
                                  f"E_V4_{track.upper()}_REVIEW_VETOES",
                                  allow_empty=True)
        if track == "content":
            contract.require(row["grade"] in contract.VERDICT_GRADES,
                             "E_V4_CONTENT_GRADE")
            contract.require(isinstance(row["approved"], bool) and
                             isinstance(row["formulaic_or_near_duplicate"], bool),
                             "E_V4_CONTENT_REVIEW_BOOL")
            contract.require(row["approved"] == (row["grade"] in {"A", "B"}),
                             "E_V4_CONTENT_APPROVAL_GRADE")
            contract.require(not row["formulaic_or_near_duplicate"] or
                             row["grade"] in {"C", "D"},
                             "E_V4_FORMULAIC_GRADE_CAP")
        else:
            contract.require(isinstance(row["fact_approved"], bool),
                             "E_V4_FACT_REVIEW_BOOL")
        index[request_id] = row
    return index


def compute_batch_metrics(
    outputs: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, Any]],
    gate_report: Mapping[str, Any],
    content_reviews: Sequence[Mapping[str, Any]],
    fact_reviews: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    deterministic_gates.validate_gate_report(gate_report, outputs, requests)
    output_by_id = contract.unique_by(outputs, "request_id", "E_V4_METRICS_OUTPUT_DUP")
    content = _review_index(content_reviews, track="content")
    facts = _review_index(fact_reviews, track="fact")
    contract.require(set(output_by_id) == set(content) == set(facts),
                     "E_V4_METRICS_REVIEW_COVERAGE")
    gate_by_id = contract.unique_by(gate_report["per_output"], "request_id",
                                    "E_V4_METRICS_GATE_DUP")
    acceptable_ids: list[str] = []
    formulaic_ids: list[str] = []
    whole_batch_veto_by_id: dict[str, list[str]] = {}
    per_profile: dict[str, dict[str, int]] = {}
    for request_id in sorted(output_by_id):
        output = output_by_id[request_id]
        contract.require(content[request_id]["output_digest"] == output["output_digest"] and
                         facts[request_id]["output_digest"] == output["output_digest"],
                         "E_V4_METRICS_REVIEW_OUTPUT_DIGEST", request_id)
        vetoes = sorted(set(gate_by_id[request_id]["hard_veto_codes"])
                        | set(content[request_id]["hard_veto_codes"])
                        | set(facts[request_id]["hard_veto_codes"]))
        if vetoes:
            whole_batch_veto_by_id[request_id] = vetoes
        if content[request_id]["formulaic_or_near_duplicate"]:
            formulaic_ids.append(request_id)
        acceptable = (
            not gate_by_id[request_id]["machine_first_fail"]
            and content[request_id]["approved"]
            and not content[request_id]["formulaic_or_near_duplicate"]
            and facts[request_id]["fact_approved"]
            and not vetoes
        )
        if acceptable:
            acceptable_ids.append(request_id)
        profile_id = str(output["profile_id"])
        profile = per_profile.setdefault(profile_id,
                                         {"total": 0, "first_acceptable": 0,
                                          "formulaic": 0, "hard_veto": 0})
        profile["total"] += 1
        profile["first_acceptable"] += int(acceptable)
        profile["formulaic"] += int(request_id in formulaic_ids)
        profile["hard_veto"] += int(bool(vetoes))

    total = len(output_by_id)
    contract.require(total > 0, "E_V4_METRICS_EMPTY")
    first_rate = len(acceptable_ids) / total
    formulaic_rate = len(formulaic_ids) / total
    whole_batch_veto_ids = sorted(whole_batch_veto_by_id)
    gate_first = first_rate >= 0.90
    gate_formulaic = formulaic_rate <= 0.10
    gate_veto = not whole_batch_veto_ids
    acceptable_veto_ids = sorted(set(acceptable_ids) & set(whole_batch_veto_ids))
    metrics: dict[str, Any] = {
        "schema_version": contract.METRICS_SCHEMA,
        "task_id": contract.TASK_ID,
        "generator_version": contract.GENERATOR_VERSION,
        "rule_version": contract.RULE_VERSION,
        "output_count": total,
        "first_acceptable_count": len(acceptable_ids),
        "first_acceptable_ids": acceptable_ids,
        "first_acceptance_rate": round(first_rate, 6),
        "gate_first_acceptance": gate_first,
        "formulaic_count": len(formulaic_ids),
        "formulaic_ids": sorted(formulaic_ids),
        "formulaic_rate": round(formulaic_rate, 6),
        "gate_formulaic": gate_formulaic,
        "whole_batch_hard_veto_count": len(whole_batch_veto_ids),
        "whole_batch_hard_veto_ids": whole_batch_veto_ids,
        "whole_batch_hard_veto_codes_by_id": {
            key: whole_batch_veto_by_id[key] for key in whole_batch_veto_ids},
        "gate_whole_batch_hard_veto_zero": gate_veto,
        "hard_veto_count_in_acceptable_set": len(acceptable_veto_ids),
        "hard_veto_ids_in_acceptable_set": acceptable_veto_ids,
        "gate_hard_veto_zero_in_acceptable_set": not acceptable_veto_ids,
        "gate_qualified": gate_first and gate_formulaic and gate_veto,
        "per_profile": {key: per_profile[key] for key in sorted(per_profile)},
        "failed_ids_retained_in_denominator": sorted(set(output_by_id) - set(acceptable_ids)),
        "gate_report_digest": gate_report["report_digest"],
        "metrics_digest": "",
    }
    contract.close_digest(metrics, "metrics_digest")
    return metrics


__all__ = ["compute_batch_metrics"]
