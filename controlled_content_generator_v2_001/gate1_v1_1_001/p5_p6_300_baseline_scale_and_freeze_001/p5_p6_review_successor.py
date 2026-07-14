#!/usr/bin/env python3
"""Materialize adjudicated production-review triage without changing frozen outputs."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any


if not __debug__:
    sys.stderr.write("p5_p6_review_successor refuses python -O\n")
    raise SystemExit(2)


SCRIPT_PATH = Path(__file__).resolve()


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"E_MODULE_IMPORT:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load_module(SCRIPT_PATH.with_name("p5_p6_baseline.py"), "gate1_p5_review_base")
SERIALIZER = _load_module(
    SCRIPT_PATH.with_name("p5_p6_baseline_successor.py"),
    "gate1_p5_review_serializer",
)
ROOT: Path = BASE.ROOT
TASK_ID: str = BASE.TASK_ID
TASK_ROOT: Path = BASE.TASK_ROOT
PROFILE_IDS: tuple[str, ...] = BASE.PROFILE_IDS

ADJUDICATION = TASK_ROOT / "review/production/fact_dispute_adjudication.v1.0.jsonl"
TRIAGE = TASK_ROOT / "review/production/adjudicated_triage.v1.0.jsonl"
TRIAGE_RESULT = TASK_ROOT / "review/production/adjudicated_triage_result.v1.0.yaml"
REVIEW_SUCCESSOR_MANIFEST = TASK_ROOT / "freeze/review_successor_as_built.v1.0.yaml"
STOP_RESULT = TASK_ROOT / "result/production_quality_gate_stop.v1.0.yaml"
ADJUDICATION_SCHEMA = "gate1-v1.1-fact-dispute-adjudication-v1.0"
TRIAGE_SCHEMA = "gate1-v1.1-adjudicated-production-triage-v1.0"


def _review_rows(pattern: str) -> list[dict[str, Any]]:
    paths = sorted((ROOT / TASK_ROOT).glob(pattern))
    BASE.require(paths, "E_REVIEW_FILES", pattern)
    return [row for path in paths for row in BASE.read_jsonl(path)]


def _prior_state() -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    outputs = BASE.read_jsonl(ROOT / BASE.FIRST_OUTPUTS)
    output_by_request = {str(row["request_id"]): row for row in outputs}
    gates = BASE.read_jsonl(ROOT / SERIALIZER.MACHINE_GATES)
    gate_by_request = {str(row["request_id"]): row for row in gates}
    content_rows = _review_rows(BASE.PRODUCTION_CONTENT_REVIEW_GLOB)
    fact_rows = _review_rows(BASE.PRODUCTION_FACT_REVIEW_GLOB)
    for row in content_rows:
        BASE._validate_production_review_row(row, "CONTENT_VALUE", output_by_request)
    for row in fact_rows:
        BASE._validate_production_review_row(row, "FACT_AUTHORIZATION", output_by_request)
    content_by_request = {str(row["request_id"]): row for row in content_rows}
    fact_by_request = {str(row["request_id"]): row for row in fact_rows}
    BASE.require(
        len(outputs) == len(output_by_request) == len(gates) == len(gate_by_request),
        "E_PRIOR_OUTPUT_GATE_COVERAGE",
    )
    BASE.require(
        len(content_rows) == len(content_by_request) == len(outputs)
        and set(content_by_request) == set(output_by_request),
        "E_PRIOR_CONTENT_COVERAGE",
    )
    BASE.require(len(fact_rows) == len(fact_by_request) >= 48, "E_PRIOR_FACT_COVERAGE")
    return outputs, gate_by_request, content_by_request, fact_by_request


def _expected_disputes(
    gate_by_request: Mapping[str, Mapping[str, Any]],
    fact_by_request: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    return {
        request_id
        for request_id, review in fact_by_request.items()
        if review["hard_error_codes"]
        and gate_by_request[request_id]["machine_gate_pass"] is True
    }


def _validate_adjudications(
    rows: Sequence[Mapping[str, Any]],
    output_by_request: Mapping[str, Mapping[str, Any]],
    gate_by_request: Mapping[str, Mapping[str, Any]],
    fact_by_request: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    expected = _expected_disputes(gate_by_request, fact_by_request)
    adjudication_by_request = {str(row.get("request_id")): dict(row) for row in rows}
    BASE.require(
        len(rows) == len(adjudication_by_request) and set(adjudication_by_request) == expected,
        "E_ADJUDICATION_COVERAGE",
    )
    author_manifest = BASE.read_json(ROOT / BASE.AUTHOR_ROLE_MANIFEST)
    author_values = {
        str(author[key])
        for author in author_manifest["authors"]
        for key in ("author_identity", "author_session_logical_id", "author_platform_agent_id")
    }
    prior_reviewer_values = {
        str(review[key])
        for review in fact_by_request.values()
        for key in (
            "reviewer_identity",
            "reviewer_session_logical_id",
            "reviewer_platform_agent_id",
        )
    }
    adjudicator_values: set[str] = set()
    for request_id, row in adjudication_by_request.items():
        output = output_by_request[request_id]
        prior = fact_by_request[request_id]
        approved = row.get("independent_fact_approved")
        hard_codes = row.get("independent_hard_error_codes")
        expected_resolution = (
            "OVERRIDE_FACT_REJECTION" if approved is True else "UPHOLD_FACT_REJECTION"
        )
        BASE.require(
            row.get("schema_version") == ADJUDICATION_SCHEMA
            and row.get("task_id") == TASK_ID
            and row.get("profile_id") == output["profile_id"]
            and row.get("output_digest") == output["output_digest"]
            and row.get("prior_fact_review_digest") == prior["review_digest"],
            "E_ADJUDICATION_BINDING",
            request_id,
        )
        BASE.require(
            row.get("model_capability_id") == BASE.MODEL_CAPABILITY
            and row.get("reasoning_effort") == BASE.REASONING_EFFORT
            and row.get("blank_context") is True
            and row.get("prior_review_read_after_independent_assessment") is True,
            "E_ADJUDICATION_ISOLATION",
            request_id,
        )
        BASE.require(
            isinstance(approved, bool)
            and isinstance(hard_codes, list)
            and ((approved and not hard_codes) or (not approved and bool(hard_codes)))
            and row.get("resolution") == expected_resolution,
            "E_ADJUDICATION_DECISION",
            request_id,
        )
        BASE.require(
            isinstance(row.get("rationale"), str)
            and bool(str(row["rationale"]).strip())
            and isinstance(row.get("evidence"), list)
            and bool(row["evidence"]),
            "E_ADJUDICATION_EVIDENCE",
            request_id,
        )
        for key in (
            "adjudicator_identity",
            "adjudicator_session_logical_id",
            "adjudicator_platform_agent_id",
        ):
            value = row.get(key)
            BASE.require(isinstance(value, str) and bool(value.strip()), "E_ADJUDICATOR_ID", key)
            adjudicator_values.add(value)
        BASE.require(
            row.get("review_digest") == BASE.object_digest(row, "review_digest"),
            "E_ADJUDICATION_DIGEST",
            request_id,
        )
    BASE.require(
        not adjudicator_values.intersection(author_values | prior_reviewer_values),
        "E_ADJUDICATOR_ROLE_COLLISION",
    )
    return adjudication_by_request


def _effective_fact_approved(
    request_id: str,
    fact_by_request: Mapping[str, Mapping[str, Any]],
    adjudication_by_request: Mapping[str, Mapping[str, Any]],
) -> bool:
    fact_review = fact_by_request.get(request_id)
    if fact_review is None or fact_review["approved_as_is"] is True:
        return True
    adjudication = adjudication_by_request.get(request_id)
    return bool(adjudication and adjudication["independent_fact_approved"] is True)


def _materialized_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    outputs, gate_by_request, content_by_request, fact_by_request = _prior_state()
    output_by_request = {str(row["request_id"]): row for row in outputs}
    adjudications = BASE.read_jsonl(ROOT / ADJUDICATION)
    adjudication_by_request = _validate_adjudications(
        adjudications,
        output_by_request,
        gate_by_request,
        fact_by_request,
    )
    triage_rows: list[dict[str, Any]] = []
    for output in outputs:
        request_id = str(output["request_id"])
        content = content_by_request[request_id]
        machine_pass = gate_by_request[request_id]["machine_gate_pass"] is True
        fact_approved = _effective_fact_approved(
            request_id, fact_by_request, adjudication_by_request
        )
        content_hard = bool(content["hard_error_codes"])
        if machine_pass and fact_approved and content["approved_as_is"] is True:
            disposition = "APPROVED_INITIAL_A"
        elif (
            machine_pass
            and fact_approved
            and not content_hard
            and content["grade"] == "B"
            and content["first_acceptable"] is True
        ):
            disposition = "LIGHT_REVISION_REQUIRED"
        else:
            disposition = "FRESH_TOPUP_REQUIRED"
        first_acceptable = bool(
            machine_pass
            and fact_approved
            and not content_hard
            and content["first_acceptable"] is True
        )
        fact_review = fact_by_request.get(request_id)
        adjudication = adjudication_by_request.get(request_id)
        row = {
            "schema_version": TRIAGE_SCHEMA,
            "task_id": TASK_ID,
            "request_id": request_id,
            "profile_id": output["profile_id"],
            "output_digest": output["output_digest"],
            "machine_gate_digest": gate_by_request[request_id]["gate_digest"],
            "content_review_digest": content["review_digest"],
            "fact_review_digest": fact_review.get("review_digest") if fact_review else None,
            "fact_adjudication_digest": (
                adjudication.get("review_digest") if adjudication else None
            ),
            "effective_fact_approved": fact_approved,
            "first_acceptable": first_acceptable,
            "formulaic_or_near_duplicate": content["formulaic_or_near_duplicate"],
            "disposition": disposition,
            "counts_toward_final_before_revision": disposition == "APPROVED_INITIAL_A",
            "failed_first_candidate_retained": disposition != "APPROVED_INITIAL_A",
            "replacement_allowed": False,
            "triage_digest": "",
        }
        row["triage_digest"] = BASE.object_digest(row, "triage_digest")
        triage_rows.append(row)
    disposition_counts = Counter(str(row["disposition"]) for row in triage_rows)
    first_by_profile = Counter(
        str(row["profile_id"]) for row in triage_rows if row["first_acceptable"]
    )
    reference_rows = BASE.approved_reference_rows()
    reference_by_profile = Counter(str(row["profile_id"]) for row in reference_rows)
    projected_approved_by_profile = Counter(reference_by_profile)
    for row in triage_rows:
        if row["disposition"] in {"APPROVED_INITIAL_A", "LIGHT_REVISION_REQUIRED"}:
            projected_approved_by_profile[str(row["profile_id"])] += 1
    result = {
        "schema_version": "gate1-v1.1-adjudicated-production-triage-result-v1.0",
        "task_id": TASK_ID,
        "first_output_count": len(triage_rows),
        "first_acceptable_count": sum(bool(row["first_acceptable"]) for row in triage_rows),
        "first_acceptance_rate": round(
            sum(bool(row["first_acceptable"]) for row in triage_rows) / len(triage_rows),
            6,
        ),
        "fact_dispute_count": len(adjudications),
        "fact_rejection_upheld_count": sum(
            row["resolution"] == "UPHOLD_FACT_REJECTION" for row in adjudications
        ),
        "fact_rejection_overridden_count": sum(
            row["resolution"] == "OVERRIDE_FACT_REJECTION" for row in adjudications
        ),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "reference_approved_count": len(reference_rows),
        "projected_approved_count_if_all_light_revisions_pass": sum(
            projected_approved_by_profile.values()
        ),
        "projected_profile_counts_if_all_light_revisions_pass": {
            profile_id: projected_approved_by_profile[profile_id]
            for profile_id in PROFILE_IDS
        },
        "first_acceptable_profile_counts_before_topup": {
            profile_id: first_by_profile[profile_id] + reference_by_profile[profile_id]
            for profile_id in PROFILE_IDS
        },
        "production_gate_passed": False,
        "candidate_300_frozen": False,
        "readiness_changed": False,
        "result_digest": "",
    }
    result["result_digest"] = BASE.object_digest(result, "result_digest")
    return triage_rows, result


def materialize() -> None:
    triage_rows, result = _materialized_rows()
    BASE.write_jsonl(ROOT / TRIAGE, triage_rows)
    BASE.write_yaml(ROOT / TRIAGE_RESULT, result)
    manifest = {
        "schema_version": "gate1-v1.1-review-successor-as-built-v1.0",
        "task_id": TASK_ID,
        "review_successor_sha256": BASE.sha256_file(SCRIPT_PATH),
        "serializer_successor_sha256": BASE.sha256_file(
            SCRIPT_PATH.with_name("p5_p6_baseline_successor.py")
        ),
        "first_output_freeze_sha256": BASE.sha256_file(ROOT / BASE.OUTPUT_FREEZE),
        "adjudication_sha256": BASE.sha256_file(ROOT / ADJUDICATION),
        "triage_sha256": BASE.sha256_file(ROOT / TRIAGE),
        "triage_result_sha256": BASE.sha256_file(ROOT / TRIAGE_RESULT),
        "frozen_output_mutation_count": 0,
        "component_or_generator_change_count": 0,
        "manifest_digest": "",
    }
    manifest["manifest_digest"] = BASE.object_digest(manifest, "manifest_digest")
    BASE.write_yaml(ROOT / REVIEW_SUCCESSOR_MANIFEST, manifest)


def _stop_result() -> dict[str, Any]:
    triage_rows = BASE.read_jsonl(ROOT / TRIAGE)
    triage_result = BASE.read_yaml(ROOT / TRIAGE_RESULT)
    BASE.require(
        BASE.canonical_json(triage_rows)
        == BASE.canonical_json(_materialized_rows()[0])
        and triage_result["result_digest"]
        == BASE.object_digest(triage_result, "result_digest"),
        "E_STOP_TRIAGE_DRIFT",
    )
    disposition_counts = Counter(str(row["disposition"]) for row in triage_rows)
    reference_count = int(triage_result["reference_approved_count"])
    projected_approved = int(
        triage_result["projected_approved_count_if_all_light_revisions_pass"]
    )
    minimum_topup = 240 - projected_approved
    first_acceptable = int(triage_result["first_acceptable_count"])
    maximum_first_acceptable = first_acceptable + minimum_topup
    minimum_final_denominator = len(triage_rows) + minimum_topup
    maximum_rate = round(maximum_first_acceptable / minimum_final_denominator, 6)
    extra_successes = 0
    while round(
        (maximum_first_acceptable + extra_successes)
        / (minimum_final_denominator + extra_successes),
        12,
    ) < 0.90:
        extra_successes += 1
    BASE.require(
        disposition_counts["APPROVED_INITIAL_A"]
        + disposition_counts["LIGHT_REVISION_REQUIRED"]
        + reference_count
        == projected_approved
        and minimum_topup > 0
        and maximum_rate < 0.90
        and extra_successes > 0,
        "E_STOP_MATH",
    )
    result = {
        "schema_version": "gate1-v1.1-production-quality-gate-stop-v1.0",
        "task_id": TASK_ID,
        "result_state": "STOPPED_PRODUCTION_FIRST_ACCEPTANCE_GATE_FAILED_NONBLOCKING",
        "blocking_quality_gate": "SEALED_BATCH_FIRST_ACCEPTANCE_RATE_GTE_0_90",
        "first_output_count": len(triage_rows),
        "first_acceptable_count_after_fact_adjudication": first_acceptable,
        "observed_first_acceptance_rate": triage_result["first_acceptance_rate"],
        "approved_reference_count": reference_count,
        "approved_initial_a_count": disposition_counts["APPROVED_INITIAL_A"],
        "light_revision_eligible_count": disposition_counts["LIGHT_REVISION_REQUIRED"],
        "fresh_topup_required_count": disposition_counts["FRESH_TOPUP_REQUIRED"],
        "minimum_topup_candidate_count_if_all_light_revisions_pass": minimum_topup,
        "maximum_first_acceptable_count_without_rate_gaming": maximum_first_acceptable,
        "minimum_final_sealed_candidate_denominator": minimum_final_denominator,
        "maximum_possible_first_acceptance_rate_without_rate_gaming": maximum_rate,
        "required_first_acceptance_rate": 0.90,
        "minimum_superfluous_success_only_candidates_needed_to_reach_threshold": extra_successes,
        "superfluous_candidate_generation_allowed": False,
        "failed_first_candidates_retained": True,
        "light_revisions_executed_count": 0,
        "topup_candidates_generated_count": 0,
        "candidate_300_manifest_created": False,
        "independent_final_review_started": False,
        "generator_qualified": False,
        "legacy_p5_allowed": False,
        "baseline_300_frozen": False,
        "quality_line_blocks_other_system_work": False,
        "external_content_provider_call_count": 0,
        "core_numbers": {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "readiness_changed": False,
        "triage_sha256": BASE.sha256_file(ROOT / TRIAGE),
        "triage_result_sha256": BASE.sha256_file(ROOT / TRIAGE_RESULT),
        "review_successor_manifest_sha256": BASE.sha256_file(
            ROOT / REVIEW_SUCCESSOR_MANIFEST
        ),
        "result_digest": "",
    }
    result["result_digest"] = BASE.object_digest(result, "result_digest")
    return result


def finalize_stop() -> None:
    BASE.require(not (ROOT / BASE.CANDIDATE_MANIFEST).exists(), "E_CANDIDATE_ALREADY_FROZEN")
    BASE.require(not (ROOT / BASE.APPROVED_POSITIVES).exists(), "E_APPROVED_SET_ALREADY_FROZEN")
    BASE.write_yaml(ROOT / STOP_RESULT, _stop_result())


def check() -> None:
    manifest = BASE.read_yaml(ROOT / REVIEW_SUCCESSOR_MANIFEST)
    BASE.require(
        manifest.get("review_successor_sha256") == BASE.sha256_file(SCRIPT_PATH)
        and manifest.get("serializer_successor_sha256")
        == BASE.sha256_file(SCRIPT_PATH.with_name("p5_p6_baseline_successor.py"))
        and manifest.get("first_output_freeze_sha256")
        == BASE.sha256_file(ROOT / BASE.OUTPUT_FREEZE)
        and manifest.get("adjudication_sha256") == BASE.sha256_file(ROOT / ADJUDICATION)
        and manifest.get("triage_sha256") == BASE.sha256_file(ROOT / TRIAGE)
        and manifest.get("triage_result_sha256") == BASE.sha256_file(ROOT / TRIAGE_RESULT),
        "E_REVIEW_SUCCESSOR_FREEZE",
    )
    triage_rows, result = _materialized_rows()
    BASE.require(
        BASE.canonical_json(triage_rows) == BASE.canonical_json(BASE.read_jsonl(ROOT / TRIAGE))
        and BASE.canonical_json(result) == BASE.canonical_json(BASE.read_yaml(ROOT / TRIAGE_RESULT)),
        "E_REVIEW_SUCCESSOR_NONDETERMINISTIC",
    )
    if (ROOT / STOP_RESULT).exists():
        BASE.require(
            BASE.canonical_json(_stop_result())
            == BASE.canonical_json(BASE.read_yaml(ROOT / STOP_RESULT)),
            "E_STOP_RESULT_NONDETERMINISTIC",
        )


def selftest() -> None:
    outputs, gate_by_request, _, fact_by_request = _prior_state()
    output_by_request = {str(row["request_id"]): row for row in outputs}
    rows = BASE.read_jsonl(ROOT / ADJUDICATION)
    _validate_adjudications(rows, output_by_request, gate_by_request, fact_by_request)
    tests: list[tuple[str, list[dict[str, Any]]]] = []
    missing = copy.deepcopy(rows)
    missing.pop()
    tests.append(("missing_dispute", missing))
    wrong_resolution = copy.deepcopy(rows)
    wrong_resolution[0]["resolution"] = (
        "UPHOLD_FACT_REJECTION"
        if wrong_resolution[0]["resolution"] == "OVERRIDE_FACT_REJECTION"
        else "OVERRIDE_FACT_REJECTION"
    )
    wrong_resolution[0]["review_digest"] = BASE.object_digest(
        wrong_resolution[0], "review_digest"
    )
    tests.append(("decision_mismatch", wrong_resolution))
    forged_parent = copy.deepcopy(rows)
    forged_parent[0]["prior_fact_review_digest"] = "0" * 64
    forged_parent[0]["review_digest"] = BASE.object_digest(
        forged_parent[0], "review_digest"
    )
    tests.append(("forged_prior", forged_parent))
    for name, mutated in tests:
        try:
            _validate_adjudications(
                mutated, output_by_request, gate_by_request, fact_by_request
            )
        except BASE.BaselineError:
            continue
        raise BASE.BaselineError(f"E_SELFTEST_FALSE_NEGATIVE:{name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("materialize", "finalize-stop", "check", "selftest")
    )
    args = parser.parse_args()
    if args.command == "materialize":
        materialize()
    elif args.command == "finalize-stop":
        finalize_stop()
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
