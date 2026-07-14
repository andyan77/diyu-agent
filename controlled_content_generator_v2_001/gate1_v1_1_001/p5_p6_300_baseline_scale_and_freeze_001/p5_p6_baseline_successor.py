#!/usr/bin/env python3
"""Versioned recovery for the Gate 1 v1.1 240+60 baseline pipeline.

The frozen v1 runner aborts the whole batch when a single first output fails
the machine gate and also requires a zero-failure batch before top-up.  The
execution contract requires the opposite lifecycle: retain every failed first
candidate in the denominator, append new cases, and never replace a failure.
This successor keeps the v1 basis and author semantics immutable while making
that lifecycle explicit and independently checkable.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any


if not __debug__:
    sys.stderr.write("p5_p6_baseline_successor refuses python -O\n")
    raise SystemExit(2)


SCRIPT_PATH = Path(__file__).resolve()


def _load_base() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gate1_p5_p6_frozen_v1", SCRIPT_PATH.with_name("p5_p6_baseline.py")
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("E_SUCCESSOR_BASE_IMPORT")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load_base()
ROOT: Path = BASE.ROOT
TASK_ID: str = BASE.TASK_ID
TASK_ROOT: Path = BASE.TASK_ROOT
PROFILE_IDS: tuple[str, ...] = BASE.PROFILE_IDS

V1_FAILURE = TASK_ROOT / "result/v1_serializer_failure.v1.0.yaml"
SUCCESSOR_MANIFEST = TASK_ROOT / "freeze/p5_p6_successor_as_built.v1.0.yaml"
MACHINE_GATES = TASK_ROOT / "production/first_output_machine_gates.v1.0.jsonl"
TOPUP_REQUIREMENTS = TASK_ROOT / "production/topup_requirements.v1.0.jsonl"
TOPUP_ROOT = TASK_ROOT / "production/topup"
TOPUP_REQUEST_GLOB = "production/topup/round_*/author_requests.v1.0.jsonl"
TOPUP_RAW_GLOB = "production/topup/round_*/author_raw/raw.*.jsonl"

MACHINE_GATE_SCHEMA = "gate1-v1.1-first-output-machine-gate-v1.0"
SUCCESSOR_SCHEMA = "gate1-v1.1-p5-p6-successor-as-built-v1.0"


def _error_code(error: Exception) -> str:
    text = str(error).strip()
    return text.split(":", 1)[0] if text else type(error).__name__


def _all_request_paths() -> list[Path]:
    return [
        ROOT / BASE.AUTHOR_REQUESTS,
        *sorted((ROOT / TASK_ROOT).glob(TOPUP_REQUEST_GLOB)),
    ]


def _all_raw_paths() -> list[Path]:
    return [
        *sorted((ROOT / TASK_ROOT).glob(BASE.RAW_OUTPUT_GLOB)),
        *sorted((ROOT / TASK_ROOT).glob(TOPUP_RAW_GLOB)),
    ]


def _all_requests() -> list[dict[str, Any]]:
    rows = [row for path in _all_request_paths() for row in BASE.read_jsonl(path)]
    request_ids = [str(row.get("request_id")) for row in rows]
    BASE.require(
        len(request_ids) == len(set(request_ids)), "E_SUCCESSOR_REQUEST_DUPLICATE"
    )
    return rows


def _all_raws() -> tuple[list[dict[str, Any]], list[Path]]:
    paths = _all_raw_paths()
    rows = [row for path in paths for row in BASE.read_jsonl(path)]
    request_ids = [str(row.get("request_id")) for row in rows]
    run_ids = [str(row.get("run_id")) for row in rows]
    BASE.require(
        len(request_ids) == len(set(request_ids)), "E_SUCCESSOR_RAW_REQUEST_DUPLICATE"
    )
    BASE.require(len(run_ids) == len(set(run_ids)), "E_SUCCESSOR_RUN_ID_DUPLICATE")
    return rows, paths


def _audience_gate_errors(output: Mapping[str, Any]) -> list[str]:
    request_id = str(output["request_id"])
    errors: list[str] = []
    audience_texts = [
        str(output["title"]),
        *map(str, output["body"]),
        *map(str, output["spoken_lines"]),
        str(output["cta"]),
        *map(str, output["visual_execution"]),
        *map(str, output["audio_execution"]),
    ]
    for text in audience_texts:
        if BASE.AUDIENCE_INTERNAL_ID_RE.search(text) is not None:
            errors.append("E_AUDIENCE_INTERNAL_ID")
        if any(phrase in text for phrase in BASE.AUDIENCE_GOVERNANCE_PHRASES):
            errors.append("E_AUDIENCE_GOVERNANCE_PROSE")
    return sorted(set(f"{code}:{request_id}" for code in errors))


def _materialize_in_memory() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    requests = _all_requests()
    raws, _ = _all_raws()
    request_by_id = {str(row["request_id"]): row for row in requests}
    BASE.require(len(raws) == len(requests), "E_SUCCESSOR_RAW_OUTPUT_COUNT")
    BASE.require(
        {str(row["request_id"]) for row in raws} == set(request_by_id),
        "E_SUCCESSOR_RAW_OUTPUT_COVERAGE",
    )
    author_contract = BASE.load_module(
        BASE.AUTHOR_MODULE_PATH, "gate1_p5_author_successor_serializer"
    )
    author_contract.TASK_ID = TASK_ID
    strict = author_contract.frozen_strict_module()
    strict.TASK_ID = TASK_ID
    outputs: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    for raw in raws:
        request_id = str(raw["request_id"])
        request = request_by_id[request_id]
        output = author_contract.serialize(raw, request)
        errors = _audience_gate_errors(output)
        try:
            strict.validate_positive_output(output, request)
        except ValueError as error:
            errors.append(str(error))
        errors = sorted(set(errors))
        row = {
            "schema_version": MACHINE_GATE_SCHEMA,
            "task_id": TASK_ID,
            "request_id": request_id,
            "profile_id": output["profile_id"],
            "run_id": output["run_id"],
            "output_digest": output["output_digest"],
            "machine_gate_pass": not errors,
            "failure_codes": [_error_code(ValueError(item)) for item in errors],
            "failure_details": errors,
            "retained_in_first_acceptance_denominator": True,
            "replacement_allowed": False,
            "gate_digest": "",
        }
        row["gate_digest"] = BASE.object_digest(row, "gate_digest")
        outputs.append(output)
        gates.append(row)
    outputs.sort(key=lambda row: int(row["run_order"]))
    gates.sort(key=lambda row: int(request_by_id[str(row["request_id"])]["run_order"]))
    return outputs, gates


def _write_successor_manifest() -> None:
    manifest = {
        "schema_version": SUCCESSOR_SCHEMA,
        "task_id": TASK_ID,
        "successor_scope": "RECORD_AND_LIFECYCLE_ONLY",
        "frozen_v1_runner_sha256": BASE.sha256_file(
            SCRIPT_PATH.with_name("p5_p6_baseline.py")
        ),
        "successor_runner_sha256": BASE.sha256_file(SCRIPT_PATH),
        "production_basis_manifest_sha256": BASE.sha256_file(
            ROOT / BASE.PRODUCTION_FREEZE
        ),
        "author_request_semantics_changed": False,
        "author_output_semantics_changed": False,
        "component_or_generator_changed": False,
        "failed_first_candidates_retained": True,
        "append_only_topup_enabled": True,
        "manifest_digest": "",
    }
    manifest["manifest_digest"] = BASE.object_digest(manifest, "manifest_digest")
    BASE.write_yaml(ROOT / SUCCESSOR_MANIFEST, manifest)


def serialize_outputs() -> None:
    outputs, gates = _materialize_in_memory()
    initial_count = len(BASE.read_jsonl(ROOT / BASE.AUTHOR_REQUESTS))
    initial_gates = gates[:initial_count]
    initial_failures = [row for row in initial_gates if not row["machine_gate_pass"]]
    v1_failure = {
        "schema_version": "gate1-v1.1-v1-serializer-failure-v1.0",
        "task_id": TASK_ID,
        "frozen_v1_runner_sha256": BASE.sha256_file(
            SCRIPT_PATH.with_name("p5_p6_baseline.py")
        ),
        "observed_v1_command": "serialize-author",
        "observed_v1_exit_code": 1,
        "observed_v1_error_code": "E_P4_COMPONENT_USAGE_COVERAGE",
        "initial_first_output_count": initial_count,
        "machine_failure_count": len(initial_failures),
        "machine_failure_request_ids": [row["request_id"] for row in initial_failures],
        "failure_retained_and_not_replaced": True,
        "author_semantics_mutated_by_recovery": False,
        "result_digest": "",
    }
    BASE.require(
        v1_failure["machine_failure_request_ids"]
        == ["G1V11-P5-POS-CP19-002", "G1V11-P5-POS-CP20-004"],
        "E_V1_FAILURE_SET_DRIFT",
    )
    v1_failure["result_digest"] = BASE.object_digest(v1_failure, "result_digest")
    BASE.write_yaml(ROOT / V1_FAILURE, v1_failure)
    BASE.write_jsonl(ROOT / BASE.FIRST_OUTPUTS, outputs)
    BASE.write_jsonl(ROOT / MACHINE_GATES, gates)
    _, raw_paths = _all_raws()
    external_events = [
        str(row["request_id"])
        for row in [row for path in raw_paths for row in BASE.read_jsonl(path)]
        if row.get("author_attestation", {}).get("external_service_called") is not False
    ]
    BASE.require(not external_events, "E_EXTERNAL_PROVIDER_CALL")
    raw_set_digest = BASE.digest_object(
        {
            path.relative_to(ROOT).as_posix(): BASE.sha256_file(path)
            for path in raw_paths
        }
    )
    audit = {
        "schema_version": "gate1-v1.1-external-exit-audit-v1.1",
        "task_id": TASK_ID,
        "audited_author_output_count": len(outputs),
        "external_content_provider_event_request_ids": external_events,
        "external_content_provider_call_count": len(external_events),
        "execution_agent_is_local_controlled_author": True,
        "git_transport_excluded_from_content_provider_count": True,
        "audit_source": "AUTHOR_ATTESTATIONS_RECOMPUTED_FROM_ALL_RAW_OUTPUTS",
        "raw_output_set_digest": raw_set_digest,
        "audit_digest": "",
    }
    audit["audit_digest"] = BASE.object_digest(audit, "audit_digest")
    BASE.write_yaml(ROOT / BASE.EXTERNAL_EXIT_AUDIT, audit)
    freeze = {
        "schema_version": "gate1-v1.1-positive-first-output-freeze-v1.1",
        "task_id": TASK_ID,
        "request_count": len(_all_requests()),
        "first_semantic_output_count": len(outputs),
        "machine_gate_pass_count": sum(row["machine_gate_pass"] for row in gates),
        "machine_gate_failure_count": sum(
            not row["machine_gate_pass"] for row in gates
        ),
        "second_candidate_count": 0,
        "replacement_count": 0,
        "author_request_set_digest": BASE.digest_object(
            {
                path.relative_to(ROOT).as_posix(): BASE.sha256_file(path)
                for path in _all_request_paths()
            }
        ),
        "raw_output_set_digest": raw_set_digest,
        "first_outputs_sha256": BASE.sha256_file(ROOT / BASE.FIRST_OUTPUTS),
        "machine_gates_sha256": BASE.sha256_file(ROOT / MACHINE_GATES),
        "production_basis_freeze_sha256": BASE.sha256_file(
            ROOT / BASE.PRODUCTION_FREEZE
        ),
        "external_exit_audit_sha256": BASE.sha256_file(ROOT / BASE.EXTERNAL_EXIT_AUDIT),
        "counts_toward_300_before_review": 0,
        "publishable_count": 0,
        "runtime_consumable_count": 0,
        "freeze_digest": "",
    }
    freeze["freeze_digest"] = BASE.object_digest(freeze, "freeze_digest")
    BASE.write_yaml(ROOT / BASE.OUTPUT_FREEZE, freeze)
    _write_successor_manifest()


def _review_rows(pattern: str) -> list[dict[str, Any]]:
    paths = sorted((ROOT / TASK_ROOT).glob(pattern))
    BASE.require(paths, "E_SUCCESSOR_REVIEW_FILES", pattern)
    return [row for path in paths for row in BASE.read_jsonl(path)]


def _validate_review_identities(
    content_rows: Sequence[Mapping[str, Any]],
    fact_rows: Sequence[Mapping[str, Any]],
) -> None:
    author_values = {
        str(request[key])
        for request in _all_requests()
        for key in (
            "author_identity",
            "author_session_logical_id",
            "author_platform_agent_id",
        )
    }
    content_values = {
        str(row[key])
        for row in content_rows
        for key in (
            "reviewer_identity",
            "reviewer_session_logical_id",
            "reviewer_platform_agent_id",
        )
    }
    fact_values = {
        str(row[key])
        for row in fact_rows
        for key in (
            "reviewer_identity",
            "reviewer_session_logical_id",
            "reviewer_platform_agent_id",
        )
    }
    BASE.require(
        not author_values.intersection(content_values | fact_values),
        "E_AUTHOR_REVIEW_COLLISION",
    )
    BASE.require(
        not content_values.intersection(fact_values), "E_REVIEW_TRACK_COLLISION"
    )


def _approval_state(
    request_id: str,
    gate_by_request: Mapping[str, Mapping[str, Any]],
    content_by_request: Mapping[str, Mapping[str, Any]],
    fact_by_request: Mapping[str, Mapping[str, Any]],
) -> bool:
    return bool(
        gate_by_request[request_id]["machine_gate_pass"]
        and content_by_request[request_id]["approved_as_is"]
        and (
            request_id not in fact_by_request
            or fact_by_request[request_id]["approved_as_is"]
        )
    )


def close_production_review() -> None:
    freeze = BASE.read_yaml(ROOT / BASE.OUTPUT_FREEZE)
    BASE.require(
        freeze.get("first_outputs_sha256")
        == BASE.sha256_file(ROOT / BASE.FIRST_OUTPUTS),
        "E_OUTPUT_DRIFT",
    )
    outputs = BASE.read_jsonl(ROOT / BASE.FIRST_OUTPUTS)
    gates = BASE.read_jsonl(ROOT / MACHINE_GATES)
    output_by_request = {str(row["request_id"]): row for row in outputs}
    gate_by_request = {str(row["request_id"]): row for row in gates}
    BASE.require(
        len(output_by_request) == len(outputs) == len(gate_by_request),
        "E_SUCCESSOR_OUTPUT_GATE_COVERAGE",
    )
    content_rows = _review_rows(BASE.PRODUCTION_CONTENT_REVIEW_GLOB)
    fact_rows = _review_rows(BASE.PRODUCTION_FACT_REVIEW_GLOB)
    for row in content_rows:
        BASE._validate_production_review_row(row, "CONTENT_VALUE", output_by_request)
    for row in fact_rows:
        BASE._validate_production_review_row(
            row, "FACT_AUTHORIZATION", output_by_request
        )
    content_by_request = {str(row["request_id"]): row for row in content_rows}
    fact_by_request = {str(row["request_id"]): row for row in fact_rows}
    BASE.require(
        len(content_by_request) == len(content_rows) == len(outputs)
        and set(content_by_request) == set(output_by_request),
        "E_CONTENT_REVIEW_COVERAGE",
    )
    BASE.require(len(fact_by_request) == len(fact_rows) >= 48, "E_FACT_REVIEW_COVERAGE")
    fact_profile_counts = Counter(str(row["profile_id"]) for row in fact_rows)
    BASE.require(
        all(fact_profile_counts[profile_id] >= 2 for profile_id in PROFILE_IDS),
        "E_FACT_REVIEW_PROFILE_COVERAGE",
    )
    _validate_review_identities(content_rows, fact_rows)
    high_risk = {
        request_id
        for request_id, row in content_by_request.items()
        if row["hard_error_codes"]
        or not row["approved_as_is"]
        or not gate_by_request[request_id]["machine_gate_pass"]
    }
    BASE.require(high_risk.issubset(fact_by_request), "E_HIGH_RISK_SECOND_REVIEW")
    approved_ids = sorted(
        request_id
        for request_id in output_by_request
        if _approval_state(
            request_id, gate_by_request, content_by_request, fact_by_request
        )
    )
    failures = []
    for request_id in sorted(output_by_request):
        if request_id in approved_ids:
            continue
        failures.append(
            {
                "request_id": request_id,
                "profile_id": output_by_request[request_id]["profile_id"],
                "output_digest": output_by_request[request_id]["output_digest"],
                "machine_gate_digest": gate_by_request[request_id]["gate_digest"],
                "machine_failure_codes": gate_by_request[request_id]["failure_codes"],
                "content_review_digest": content_by_request[request_id][
                    "review_digest"
                ],
                "fact_review_digest": fact_by_request.get(request_id, {}).get(
                    "review_digest"
                ),
                "retained_in_first_acceptance_denominator": True,
                "replacement_allowed": False,
            }
        )
    BASE.write_jsonl(ROOT / BASE.PRODUCTION_FAILURES, failures)
    first_acceptable_ids = {
        request_id
        for request_id, row in content_by_request.items()
        if row["first_acceptable"]
        and gate_by_request[request_id]["machine_gate_pass"]
        and (
            request_id not in fact_by_request
            or fact_by_request[request_id]["approved_as_is"]
        )
    }
    formulaic_ids = {
        request_id
        for request_id, row in content_by_request.items()
        if row["formulaic_or_near_duplicate"]
    }
    references = BASE.approved_reference_rows()
    p4_rows = BASE.approved_p4_rows()
    approved_new_rows = []
    for request_id in approved_ids:
        output = output_by_request[request_id]
        approved_new_rows.append(
            {
                "baseline_item_id": f"G1V11-P5-{request_id}",
                "request_id": request_id,
                "profile_id": output["profile_id"],
                "title": output["title"],
                "body": output["body"],
                "spoken_lines": output["spoken_lines"],
                "cta": output["cta"],
                "visual_execution": output["visual_execution"],
                "audio_execution": output["audio_execution"],
                "output_digest": output["output_digest"],
                "approval_source": "P5_INDEPENDENT_PRODUCTION_REVIEWS",
                "content_review_digest": content_by_request[request_id][
                    "review_digest"
                ],
                "fact_review_digest": fact_by_request.get(request_id, {}).get(
                    "review_digest"
                ),
                "first_acceptable": request_id in first_acceptable_ids,
                "original_first_output_unchanged": True,
                "publishable": False,
                "runtime_consumable": False,
            }
        )
    combined = [*references, *p4_rows, *approved_new_rows]
    profile_counts = Counter(str(row["profile_id"]) for row in combined)
    first_by_profile = Counter(
        str(row["profile_id"])
        for row in combined
        if row.get("first_acceptable") is True
    )
    first_acceptance_rate = round(len(first_acceptable_ids) / len(outputs), 6)
    formulaic_rate = round(len(formulaic_ids) / len(outputs), 6)
    blind_correct_count = sum(
        row["blind_profile_choice"] == row["profile_id"] for row in content_rows
    )
    lane_counts = Counter(
        str(output_by_request[request_id]["assigned_variant"])[0]
        for request_id in approved_ids
    )
    approved_hard_veto_count = sum(
        bool(content_by_request[request_id]["hard_error_codes"])
        or bool(fact_by_request.get(request_id, {}).get("hard_error_codes"))
        for request_id in approved_ids
    )
    pass_gate = (
        len(combined) == 240
        and all(profile_counts[profile_id] == 12 for profile_id in PROFILE_IDS)
        and first_acceptance_rate >= 0.90
        and all(first_by_profile[profile_id] >= 11 for profile_id in PROFILE_IDS)
        and formulaic_rate <= 0.10
        and blind_correct_count / len(outputs) >= 0.85
        and approved_hard_veto_count == 0
        and lane_counts["A"] > 0
        and lane_counts["B"] > 0
    )
    result = {
        "schema_version": "gate1-v1.1-production-review-result-v1.1",
        "task_id": TASK_ID,
        "result_state": (
            "PASS_TO_CANDIDATE_FREEZE"
            if pass_gate
            else "STOPPED_PRODUCTION_TOPUP_OR_REVIEW_REQUIRED"
        ),
        "first_output_count": len(outputs),
        "first_acceptable_count": len(first_acceptable_ids),
        "first_acceptance_rate": first_acceptance_rate,
        "approved_new_count": len(approved_new_rows),
        "failed_new_count": len(failures),
        "formulaic_or_near_duplicate_count": len(formulaic_ids),
        "formulaic_or_near_duplicate_rate": formulaic_rate,
        "blind_profile_correct_count": blind_correct_count,
        "blind_profile_total": len(outputs),
        "approved_reference_count": len(references),
        "approved_p4_count": len(p4_rows),
        "combined_positive_count": len(combined),
        "profile_counts": dict(sorted(profile_counts.items())),
        "first_acceptable_profile_counts": dict(sorted(first_by_profile.items())),
        "lane_counts": dict(sorted(lane_counts.items())),
        "attempt_hard_veto_count": sum(
            bool(row["hard_error_codes"]) for row in content_rows
        ),
        "approved_hard_veto_count": approved_hard_veto_count,
        "historical_failures_retained": True,
        "pass": pass_gate,
        "review_digest": "",
    }
    result["review_digest"] = BASE.object_digest(result, "review_digest")
    BASE.write_yaml(ROOT / BASE.PRODUCTION_REVIEW_RESULT, result)
    topup_rows = []
    for profile_id in PROFILE_IDS:
        missing = max(0, 12 - profile_counts[profile_id])
        if missing:
            row = {
                "schema_version": "gate1-v1.1-topup-requirement-v1.0",
                "task_id": TASK_ID,
                "profile_id": profile_id,
                "approved_positive_count": profile_counts[profile_id],
                "required_approved_positive_count": 12,
                "minimum_additional_candidate_count": missing,
                "failed_candidates_retained": True,
                "replacement_allowed": False,
                "requirement_digest": "",
            }
            row["requirement_digest"] = BASE.object_digest(row, "requirement_digest")
            topup_rows.append(row)
    BASE.write_jsonl(ROOT / TOPUP_REQUIREMENTS, topup_rows)
    if not pass_gate:
        return
    BASE.write_jsonl(ROOT / BASE.APPROVED_POSITIVES, combined)
    manifest = {
        "schema_version": "gate1-v1.1-candidate-300-manifest-v1.1",
        "task_id": TASK_ID,
        "candidate_state": "FROZEN_PENDING_INDEPENDENT_FINAL_REVIEW",
        "positive_count": len(combined),
        "route_count": len(BASE.read_jsonl(ROOT / BASE.ROUTE_COMPARISONS)),
        "total_count": len(combined)
        + len(BASE.read_jsonl(ROOT / BASE.ROUTE_COMPARISONS)),
        "profile_positive_counts": dict(sorted(profile_counts.items())),
        "basis_freeze_sha256": BASE.sha256_file(ROOT / BASE.PRODUCTION_FREEZE),
        "successor_manifest_sha256": BASE.sha256_file(ROOT / SUCCESSOR_MANIFEST),
        "output_freeze_sha256": BASE.sha256_file(ROOT / BASE.OUTPUT_FREEZE),
        "approved_positives_sha256": BASE.sha256_file(ROOT / BASE.APPROVED_POSITIVES),
        "route_comparisons_sha256": BASE.sha256_file(ROOT / BASE.ROUTE_COMPARISONS),
        "route_result_sha256": BASE.sha256_file(ROOT / BASE.ROUTE_RESULT),
        "production_review_result_sha256": BASE.sha256_file(
            ROOT / BASE.PRODUCTION_REVIEW_RESULT
        ),
        "production_failures_sha256": BASE.sha256_file(ROOT / BASE.PRODUCTION_FAILURES),
        "content_review_set_digest": BASE.digest_object(
            {row["request_id"]: row["review_digest"] for row in content_rows}
        ),
        "fact_review_set_digest": BASE.digest_object(
            {row["request_id"]: row["review_digest"] for row in fact_rows}
        ),
        "production_role_may_modify_after_freeze": False,
        "readiness_changed": False,
        "manifest_digest": "",
    }
    BASE.require(
        manifest["positive_count"] == 240
        and manifest["route_count"] == 60
        and manifest["total_count"] == 300,
        "E_CANDIDATE_COUNTS",
    )
    manifest["manifest_digest"] = BASE.object_digest(manifest, "manifest_digest")
    BASE.write_yaml(ROOT / BASE.CANDIDATE_MANIFEST, manifest)


def prepare_topup(round_id: str) -> None:
    BASE.require(round_id.startswith("round_"), "E_TOPUP_ROUND_ID")
    round_root = TOPUP_ROOT / round_id
    scenario_path = round_root / "curated_scenarios.v1.0.jsonl"
    role_path = round_root / "author_role_manifest.v1.0.json"
    request_path = round_root / "author_requests.v1.0.jsonl"
    batch_path = round_root / "batch_ledger.v1.0.jsonl"
    freeze_path = round_root / "round_basis_freeze.v1.0.yaml"
    BASE.require(not (ROOT / request_path).exists(), "E_TOPUP_ROUND_ALREADY_PREPARED")
    requirements = BASE.read_jsonl(ROOT / TOPUP_REQUIREMENTS)
    needed = {
        str(row["profile_id"]): int(row["minimum_additional_candidate_count"])
        for row in requirements
    }
    BASE.require(needed, "E_TOPUP_NOT_REQUIRED")
    scenarios = BASE.read_jsonl(ROOT / scenario_path)
    for scenario in scenarios:
        BASE._validate_scenario(scenario)
    BASE.require(
        Counter(str(row["profile_id"]) for row in scenarios) == Counter(needed),
        "E_TOPUP_SCENARIO_COUNTS",
    )
    existing_scenario_ids = {
        str(row["scenario_id"])
        for path in sorted((ROOT / TASK_ROOT).glob(BASE.CURATION_GLOB))
        for row in BASE.read_jsonl(path)
    }
    existing_scenario_ids.update(
        str(row["scenario_id"])
        for path in sorted(
            (ROOT / TOPUP_ROOT).glob("round_*/curated_scenarios.v1.0.jsonl")
        )
        if path != ROOT / scenario_path
        for row in BASE.read_jsonl(path)
    )
    BASE.require(
        not existing_scenario_ids.intersection(
            str(row["scenario_id"]) for row in scenarios
        ),
        "E_TOPUP_SCENARIO_REUSE",
    )
    role_manifest = BASE.read_json(ROOT / role_path)
    authors = role_manifest.get("authors")
    BASE.require(isinstance(authors, list) and authors, "E_TOPUP_AUTHOR_ROLES")
    author_by_profile: dict[str, dict[str, Any]] = {}
    for author in authors:
        BASE.require(
            author.get("model_capability_id") == BASE.MODEL_CAPABILITY
            and author.get("reasoning_effort") == BASE.REASONING_EFFORT
            and author.get("service_tier") == BASE.SERVICE_TIER,
            "E_TOPUP_AUTHOR_MODEL",
        )
        BASE.require(
            author.get("may_review_or_freeze") is False
            and author.get("external_content_provider_allowed") is False,
            "E_TOPUP_AUTHOR_BOUNDARY",
        )
        for profile_id in author.get("assigned_profile_ids", []):
            BASE.require(
                str(profile_id) not in author_by_profile,
                "E_TOPUP_AUTHOR_PROFILE_DUPLICATE",
            )
            author_by_profile[str(profile_id)] = dict(author)
    BASE.require(set(author_by_profile) == set(needed), "E_TOPUP_AUTHOR_COVERAGE")
    templates = {
        str(row["profile_id"]): row for row in BASE.read_jsonl(ROOT / BASE.P4_REQUESTS)
    }
    start_order = max(int(row["run_order"]) for row in _all_requests()) + 1
    requests = [
        BASE._request_from_scenario(
            scenario,
            templates[str(scenario["profile_id"])],
            author_by_profile[str(scenario["profile_id"])],
            start_order + index,
        )
        for index, scenario in enumerate(
            sorted(scenarios, key=lambda row: str(row["scenario_id"]))
        )
    ]
    existing_request_ids = {str(row["request_id"]) for row in _all_requests()}
    BASE.require(
        not existing_request_ids.intersection(
            str(row["request_id"]) for row in requests
        ),
        "E_TOPUP_REQUEST_REUSE",
    )
    author_contract = BASE.load_module(
        BASE.AUTHOR_MODULE_PATH, f"gate1_topup_{round_id}_author_contract"
    )
    author_contract.TASK_ID = TASK_ID
    for request in requests:
        author_contract.validate_request(request)
    BASE.write_jsonl(ROOT / request_path, requests)
    batch_rows = []
    requests_by_author: dict[str, list[dict[str, Any]]] = {}
    for request in requests:
        requests_by_author.setdefault(
            str(request["author_platform_agent_id"]), []
        ).append(request)
    for index, (agent_id, rows) in enumerate(sorted(requests_by_author.items()), 1):
        BASE.require(len(rows) <= 40, "E_TOPUP_AUTHOR_BATCH_SIZE")
        batch = {
            "schema_version": "gate1-v1.1-production-topup-batch-ledger-v1.0",
            "task_id": TASK_ID,
            "round_id": round_id,
            "batch_id": f"{round_id.upper()}-BATCH-{index:03d}",
            "author_platform_agent_id": agent_id,
            "request_ids": sorted(str(row["request_id"]) for row in rows),
            "request_count": len(rows),
            "maximum_candidate_count": 40,
            "first_candidate_only": True,
            "append_only": True,
            "batch_digest": "",
        }
        batch["batch_digest"] = BASE.object_digest(batch, "batch_digest")
        batch_rows.append(batch)
    BASE.write_jsonl(ROOT / batch_path, batch_rows)
    freeze = {
        "schema_version": "gate1-v1.1-topup-round-basis-freeze-v1.0",
        "task_id": TASK_ID,
        "round_id": round_id,
        "same_production_basis_required": True,
        "production_basis_manifest_sha256": BASE.sha256_file(
            ROOT / BASE.PRODUCTION_FREEZE
        ),
        "successor_manifest_sha256": BASE.sha256_file(ROOT / SUCCESSOR_MANIFEST),
        "curated_scenarios_sha256": BASE.sha256_file(ROOT / scenario_path),
        "author_role_manifest_sha256": BASE.sha256_file(ROOT / role_path),
        "author_requests_sha256": BASE.sha256_file(ROOT / request_path),
        "batch_ledger_sha256": BASE.sha256_file(ROOT / batch_path),
        "candidate_count": len(requests),
        "replacement_count": 0,
        "failed_candidates_retained": True,
        "model_capability_id": BASE.MODEL_CAPABILITY,
        "reasoning_effort": BASE.REASONING_EFFORT,
        "service_tier": BASE.SERVICE_TIER,
        "freeze_digest": "",
    }
    freeze["freeze_digest"] = BASE.object_digest(freeze, "freeze_digest")
    BASE.write_yaml(ROOT / freeze_path, freeze)


def check() -> None:
    manifest = BASE.read_yaml(ROOT / SUCCESSOR_MANIFEST)
    BASE.require(
        manifest.get("schema_version") == SUCCESSOR_SCHEMA, "E_SUCCESSOR_SCHEMA"
    )
    BASE.require(
        manifest.get("successor_runner_sha256") == BASE.sha256_file(SCRIPT_PATH),
        "E_SUCCESSOR_RUNNER_DRIFT",
    )
    outputs, gates = _materialize_in_memory()
    BASE.require(
        BASE.canonical_json(outputs)
        == BASE.canonical_json(BASE.read_jsonl(ROOT / BASE.FIRST_OUTPUTS)),
        "E_SUCCESSOR_OUTPUT_NONDETERMINISTIC",
    )
    BASE.require(
        BASE.canonical_json(gates)
        == BASE.canonical_json(BASE.read_jsonl(ROOT / MACHINE_GATES)),
        "E_SUCCESSOR_GATE_NONDETERMINISTIC",
    )
    freeze = BASE.read_yaml(ROOT / BASE.OUTPUT_FREEZE)
    BASE.require(
        freeze.get("first_outputs_sha256")
        == BASE.sha256_file(ROOT / BASE.FIRST_OUTPUTS)
        and freeze.get("machine_gates_sha256")
        == BASE.sha256_file(ROOT / MACHINE_GATES),
        "E_SUCCESSOR_OUTPUT_FREEZE",
    )
    BASE.require(
        BASE.read_yaml(ROOT / BASE.EXTERNAL_EXIT_AUDIT).get(
            "external_content_provider_call_count"
        )
        == 0,
        "E_EXTERNAL_PROVIDER_CALL",
    )


def selftest() -> None:
    BASE.selftest()
    outputs, gates = _materialize_in_memory()
    gate_by_request = {str(row["request_id"]): row for row in gates}
    BASE.require(
        gate_by_request["G1V11-P5-POS-CP19-002"]["machine_gate_pass"] is False,
        "E_SELFTEST_EXPECTED_MACHINE_FAILURE",
    )
    failed_request_id = "G1V11-P5-POS-CP19-002"
    fake_content = {failed_request_id: {"approved_as_is": True}}
    fake_fact = {failed_request_id: {"approved_as_is": True}}
    BASE.require(
        not _approval_state(
            failed_request_id, gate_by_request, fake_content, fake_fact
        ),
        "E_SELFTEST_MACHINE_FAILURE_FALSE_APPROVAL",
    )
    BASE.require(len(outputs) == len(gates), "E_SELFTEST_OUTPUT_GATE_COUNT")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "serialize-outputs",
            "close-production-review",
            "prepare-topup",
            "prepare-final-decision",
            "apply-final-decision",
            "check",
            "selftest",
        ),
    )
    parser.add_argument("--round-id")
    args = parser.parse_args()
    if args.command == "serialize-outputs":
        serialize_outputs()
    elif args.command == "close-production-review":
        close_production_review()
    elif args.command == "prepare-topup":
        BASE.require(isinstance(args.round_id, str), "E_TOPUP_ROUND_REQUIRED")
        prepare_topup(args.round_id)
    elif args.command == "prepare-final-decision":
        BASE.prepare_final_decision_packet()
    elif args.command == "apply-final-decision":
        BASE.apply_final_decision()
    elif args.command == "check":
        check()
    else:
        selftest()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BASE.BaselineError as error:
        sys.stderr.write(f"{error}\n")
        raise SystemExit(1) from error
