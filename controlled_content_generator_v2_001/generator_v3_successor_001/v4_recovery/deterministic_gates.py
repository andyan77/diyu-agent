"""Deterministic qualification gates for v4 recovery.

These gates enforce contracts and explicit deterministic prohibitions. They do
not pretend to solve semantic factuality or formulaic judgment.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import author_contract, contract, deterministic_claims, request_builder

_SELF_APPROVAL_RE = re.compile(r"(已经|已)?(批准|获准)(上线|发布)?|正式资产|生产可用|可直接发布")
_DISCLOSURE_RE = re.compile(r"(本条|本文|这个内容).{0,8}(合成|非真实)|合成(测试)?内容")
_NORMALIZE_RE = re.compile(r"[\s，。；：、！？「」『』“”‘’（）()《》…—\-·,.;:!?\"']+")


def _normalized_audience(output: Mapping[str, Any]) -> str:
    return _NORMALIZE_RE.sub("", author_contract.audience_text(output))


def _surface_fact_ids(output: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for surface in output["surface_units"]:
        if surface["surface_kind"] != "synthetic_disclosure":
            result.update(map(str, surface["fact_ids"]))
    return result


def gate_batch(
    outputs: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, Any]],
    *,
    _validate: bool = True,
) -> dict[str, Any]:
    claim_registry = deterministic_claims.load_registry()
    request_by_id = contract.unique_by(requests, "request_id", "E_V4_GATE_REQUEST_DUP")
    output_by_id = contract.unique_by(outputs, "request_id", "E_V4_GATE_OUTPUT_DUP")
    contract.require(set(output_by_id) == set(request_by_id), "E_V4_GATE_BATCH_JOIN")
    per_output: list[dict[str, Any]] = []
    attempt_ids: set[str] = set()
    normalized_groups: dict[str, list[str]] = {}
    for request_id in sorted(request_by_id):
        request = request_by_id[request_id]
        output = output_by_id[request_id]
        request_builder.validate_request(request)
        author_contract.validate_output(output, request)
        hard_failures: list[str] = []
        hard_vetoes: list[str] = []
        flags: list[str] = []
        attempt_id = str(output["attempt_id"])
        if attempt_id in attempt_ids:
            hard_failures.append("HF_DUPLICATE_ATTEMPT_ID")
        attempt_ids.add(attempt_id)
        bound = _surface_fact_ids(output)
        policy = request["surface_policy"]
        for fact_id in policy["must_surface_fact_ids"]:
            if fact_id not in bound:
                hard_failures.append(f"HF_MUST_SURFACE_MISSING:{fact_id}")
        for fact_id in policy["control_only_fact_ids"]:
            if fact_id in bound:
                hard_vetoes.append(f"HV_CONTROL_ONLY_SURFACED:{fact_id}")
        audience = author_contract.audience_text(output)
        facts = {fact["fact_id"]: fact for fact in request["typed_material"]["facts"]}
        for fact_id in policy["control_only_fact_ids"]:
            for term in facts[fact_id]["prohibited_surface_terms"]:
                if term in audience:
                    hard_vetoes.append(f"HV_PROHIBITED_CONTROL_TERM:{fact_id}:{term}")
        if _SELF_APPROVAL_RE.search(audience):
            hard_vetoes.append("HV_SELF_APPROVAL_OR_PUBLISH_STATE")
        if _DISCLOSURE_RE.search(audience):
            hard_failures.append("HF_DISCLOSURE_ON_AUDIENCE_SURFACE")
        hard_vetoes.extend(deterministic_claims.unsupported_claim_codes(
            output, request, claim_registry))
        normalized_groups.setdefault(_normalized_audience(output), []).append(request_id)
        per_output.append({
            "request_id": request_id,
            "profile_id": output["profile_id"],
            "output_digest": output["output_digest"],
            "hard_failure_codes": sorted(set(hard_failures)),
            "hard_veto_codes": sorted(set(hard_vetoes)),
            "review_flag_codes": sorted(set(flags)),
            "machine_first_fail": bool(hard_failures or hard_vetoes),
        })

    exact_duplicate_groups = [sorted(ids) for text, ids in normalized_groups.items()
                              if text and len(ids) > 1]
    row_by_id = {row["request_id"]: row for row in per_output}
    for group in exact_duplicate_groups:
        for request_id in group:
            row = row_by_id[request_id]
            row["hard_failure_codes"] = sorted(
                set(row["hard_failure_codes"]) | {"HF_EXACT_AUDIENCE_DUPLICATE"})
            row["machine_first_fail"] = True
    veto_ids = sorted(row["request_id"] for row in per_output if row["hard_veto_codes"])
    fail_ids = sorted(row["request_id"] for row in per_output if row["machine_first_fail"])
    report: dict[str, Any] = {
        "schema_version": contract.GATE_REPORT_SCHEMA,
        "task_id": contract.TASK_ID,
        "generator_version": contract.GENERATOR_VERSION,
        "rule_version": contract.RULE_VERSION,
        "deterministic_claim_registry_digest": claim_registry["registry_digest"],
        "output_count": len(per_output),
        "machine_hard_fail_count": len(fail_ids),
        "machine_hard_veto_count": len(veto_ids),
        "whole_batch_machine_hard_veto_zero": not veto_ids,
        "machine_hard_fail_ids": fail_ids,
        "machine_hard_veto_ids": veto_ids,
        "exact_duplicate_groups": sorted(exact_duplicate_groups),
        "per_output": per_output,
        "report_digest": "",
    }
    contract.close_digest(report, "report_digest")
    if _validate:
        validate_gate_report(report, outputs, requests)
    return report


def validate_gate_report(
    report: Mapping[str, Any],
    outputs: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, Any]],
) -> None:
    expected_fields = {
        "schema_version", "task_id", "generator_version", "rule_version",
        "deterministic_claim_registry_digest",
        "output_count", "machine_hard_fail_count", "machine_hard_veto_count",
        "whole_batch_machine_hard_veto_zero", "machine_hard_fail_ids",
        "machine_hard_veto_ids", "exact_duplicate_groups", "per_output",
        "report_digest",
    }
    contract.exact_fields(report, expected_fields, "E_V4_GATE_REPORT_FIELDS")
    contract.require(report.get("schema_version") == contract.GATE_REPORT_SCHEMA,
                     "E_V4_GATE_REPORT_SCHEMA")
    contract.require(report.get("task_id") == contract.TASK_ID and
                     report.get("generator_version") == contract.GENERATOR_VERSION and
                     report.get("rule_version") == contract.RULE_VERSION,
                     "E_V4_GATE_REPORT_VERSION")
    contract.require(report.get("deterministic_claim_registry_digest") ==
                     deterministic_claims.load_registry()["registry_digest"],
                     "E_V4_GATE_REPORT_CLAIM_REGISTRY")
    contract.require(report.get("output_count") == len(outputs), "E_V4_GATE_REPORT_COUNT")
    rows = report.get("per_output")
    contract.require(isinstance(rows, list), "E_V4_GATE_REPORT_ROWS")
    row_by_id = contract.unique_by(rows, "request_id", "E_V4_GATE_REPORT_DUP")
    output_by_id = contract.unique_by(outputs, "request_id", "E_V4_GATE_OUTPUT_DUP")
    contract.require(set(row_by_id) == set(output_by_id),
                     "E_V4_GATE_REPORT_OUTPUT_COVERAGE")
    for request_id, row in row_by_id.items():
        contract.exact_fields(
            row,
            {"request_id", "profile_id", "output_digest", "hard_failure_codes",
             "hard_veto_codes", "review_flag_codes", "machine_first_fail"},
            "E_V4_GATE_REPORT_ROW_FIELDS",
        )
        contract.require(row["profile_id"] == output_by_id[request_id]["profile_id"] and
                         row["output_digest"] == output_by_id[request_id]["output_digest"],
                         "E_V4_GATE_REPORT_OUTPUT_JOIN", request_id)
        failures = contract.unique_text_list(
            row["hard_failure_codes"], "E_V4_GATE_REPORT_FAILURE_CODES",
            allow_empty=True)
        vetoes = contract.unique_text_list(
            row["hard_veto_codes"], "E_V4_GATE_REPORT_VETO_CODES",
            allow_empty=True)
        contract.unique_text_list(row["review_flag_codes"],
                                  "E_V4_GATE_REPORT_FLAG_CODES", allow_empty=True)
        contract.require(isinstance(row["machine_first_fail"], bool) and
                         row["machine_first_fail"] == bool(failures or vetoes),
                         "E_V4_GATE_REPORT_ROW_FAIL_RECOMPUTE", request_id)
    expected_duplicate_groups = sorted(
        sorted(ids) for text, ids in _duplicate_groups(outputs).items()
        if text and len(ids) > 1
    )
    contract.require(report["exact_duplicate_groups"] == expected_duplicate_groups,
                     "E_V4_GATE_REPORT_DUPLICATE_RECOMPUTE")
    veto_ids = sorted(row["request_id"] for row in rows if row["hard_veto_codes"])
    fail_ids = sorted(row["request_id"] for row in rows if row["machine_first_fail"])
    contract.require(report.get("machine_hard_veto_ids") == veto_ids and
                     report.get("machine_hard_veto_count") == len(veto_ids) and
                     report.get("whole_batch_machine_hard_veto_zero") == (not veto_ids),
                     "E_V4_GATE_REPORT_VETO_RECOMPUTE")
    contract.require(report.get("machine_hard_fail_ids") == fail_ids and
                     report.get("machine_hard_fail_count") == len(fail_ids),
                     "E_V4_GATE_REPORT_FAIL_RECOMPUTE")
    contract.validate_digest(report, "report_digest", "E_V4_GATE_REPORT_DIGEST")
    expected = gate_batch(outputs, requests, _validate=False)
    contract.require(report == expected, "E_V4_GATE_REPORT_FULL_RECOMPUTE")


def _duplicate_groups(outputs: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for output in outputs:
        groups.setdefault(_normalized_audience(output), []).append(str(output["request_id"]))
    return groups


__all__ = ["gate_batch", "validate_gate_report"]
