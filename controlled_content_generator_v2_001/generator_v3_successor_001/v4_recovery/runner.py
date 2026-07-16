"""Qualification runner for the isolated v4 recovery package."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import (author_contract, contract, deterministic_gates, material_policy,
               metrics, request_builder, telemetry, test_allocator)


def build_qualification_requests(
    scenarios: Sequence[Mapping[str, Any]],
    raw_materials: Sequence[Mapping[str, Any]],
    *,
    assignment_set_id: str,
    batch_id: str,
    run_id: str,
    authors_by_profile: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Build assignments, normalized materials, and requests as one closed bundle."""
    materials = [material_policy.normalize_material(raw) for raw in raw_materials]
    material_by_id = contract.unique_by(materials, "scenario_id", "E_V4_MATERIAL_DUP")
    allocation_cases: list[dict[str, Any]] = []
    for scenario in scenarios:
        scenario_id = str(scenario["scenario_id"])
        contract.require(scenario_id in material_by_id, "E_V4_RUNNER_MATERIAL_JOIN",
                         scenario_id)
        material = material_by_id[scenario_id]
        stable_scenario = dict(scenario)
        stable_scenario["scenario_digest"] = test_allocator.scenario_digest_for_case(scenario)
        stable_scenario["material_packet_digest"] = material["material_digest"]
        stable_scenario["evidence_surface_policy"] = [
            {"reference_assertion_id": fact["fact_id"],
             "policy": fact["surface_policy"],
             "reason_code": f"EXPLICIT_{fact['surface_policy']}"}
            for fact in material["facts"]
        ]
        stable_scenario["forbidden_inferences"] = list(
            scenario.get("forbidden_inferences", ["NO_UNBOUND_FACT_OR_ACTION"]))
        stable_scenario["paired_assignment_id"] = scenario.get("paired_assignment_id")
        allocation_cases.append(stable_scenario)
    assignments = test_allocator.allocate_test_assignments(
        allocation_cases, assignment_set_id)
    requests = request_builder.build_batch(
        scenarios, materials, assignments, batch_id=batch_id, run_id=run_id,
        authors_by_profile=authors_by_profile,
    )
    bundle: dict[str, Any] = {
        "schema_version": "gate1-v4-qualification-request-bundle-v1",
        "task_id": contract.TASK_ID,
        "generator_version": contract.GENERATOR_VERSION,
        "rule_version": contract.RULE_VERSION,
        "assignment_set_id": assignment_set_id,
        "batch_id": batch_id,
        "run_id": run_id,
        "assignments": assignments,
        "materials": materials,
        "requests": requests,
        "bundle_digest": "",
    }
    contract.close_digest(bundle, "bundle_digest")
    return bundle


def evaluate_qualification_batch(
    requests: Sequence[Mapping[str, Any]],
    raw_outputs: Sequence[Mapping[str, Any]],
    content_reviews: Sequence[Mapping[str, Any]],
    fact_reviews: Sequence[Mapping[str, Any]],
    telemetry_events: Sequence[Mapping[str, Any]],
    run_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate exactly one first attempt for every sealed request."""
    request_by_id = contract.unique_by(requests, "request_id", "E_V4_RUNNER_REQUEST_DUP")
    raw_by_id = contract.unique_by(raw_outputs, "request_id", "E_V4_RUNNER_RAW_DUP")
    contract.require(set(raw_by_id) == set(request_by_id), "E_V4_RUNNER_RAW_COVERAGE")
    run_ids = {str(request["run_id"]) for request in requests}
    batch_ids = {str(request["batch_id"]) for request in requests}
    contract.require(len(run_ids) == 1 and len(batch_ids) == 1, "E_V4_RUNNER_BATCH_JOIN")
    run_id = next(iter(run_ids))
    batch_id = next(iter(batch_ids))
    outputs = [author_contract.serialize(raw_by_id[request_id], request_by_id[request_id])
               for request_id in sorted(request_by_id)]
    gate_report = deterministic_gates.gate_batch(outputs, requests)
    batch_metrics = metrics.compute_batch_metrics(
        outputs, requests, gate_report, content_reviews, fact_reviews)
    telemetry.validate_qualification_coverage(
        telemetry_events, list(request_by_id.values()), outputs, gate_report,
        content_reviews, fact_reviews, batch_metrics,
        run_id=run_id, batch_id=batch_id)
    telemetry_summary = telemetry.summarize_events(telemetry_events)
    telemetry.validate_run_manifest(run_manifest)
    contract.require(run_manifest["run_id"] == run_id and
                     run_manifest["batch_id"] == batch_id,
                     "E_V4_RUNNER_MANIFEST_JOIN")
    contract.require(run_manifest["stage_gate"] == "GATE1_QUALIFICATION",
                     "E_V4_RUNNER_MANIFEST_STAGE")
    contract.require(run_manifest["input_manifest_digest"] ==
                     telemetry.object_manifest_digest(
                         list(request_by_id.values()), id_field="request_id",
                         digest_field="request_digest"),
                     "E_V4_RUNNER_INPUT_MANIFEST_DIGEST")
    contract.require(run_manifest["output_manifest_digest"] ==
                     telemetry.object_manifest_digest(
                         outputs, id_field="request_id", digest_field="output_digest"),
                     "E_V4_RUNNER_OUTPUT_MANIFEST_DIGEST")
    contract.require(run_manifest["model_or_engine_config_ref"] ==
                     telemetry.model_config_binding_ref(
                         list(request_by_id.values())),
                     "E_V4_RUNNER_MODEL_CONFIG_BINDING")
    contract.require(run_manifest["telemetry_summary_digest"] ==
                     telemetry_summary["summary_digest"],
                     "E_V4_RUNNER_MANIFEST_TELEMETRY")
    result: dict[str, Any] = {
        "schema_version": "gate1-v4-qualification-evaluation-v1",
        "task_id": contract.TASK_ID,
        "generator_version": contract.GENERATOR_VERSION,
        "rule_version": contract.RULE_VERSION,
        "run_id": run_id,
        "batch_id": batch_id,
        "request_count": len(request_by_id),
        "outputs": outputs,
        "gate_report": gate_report,
        "metrics": batch_metrics,
        "telemetry_summary": telemetry_summary,
        "run_manifest_digest": run_manifest["manifest_digest"],
        "gate_telemetry_complete": telemetry_summary["telemetry_complete"],
        "qualification_pass": (batch_metrics["gate_qualified"]
                               and telemetry_summary["telemetry_complete"]),
        "result_digest": "",
    }
    contract.close_digest(result, "result_digest")
    return result


def historical_r5_paths(repo_root: Path | None = None) -> tuple[Path, Path]:
    root = repo_root or Path(__file__).resolve().parents[3]
    r5 = (root / "controlled_content_generator_v2_001/gate1_v1_1_001"
          / "p7_successor_longrun_001/pkg1_open_regression/round5/inputs")
    return r5 / "scenarios.g3.v2.jsonl", r5 / "requests.g3.v1.jsonl"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    diagnose = sub.add_parser("diagnose-r5",
                              help="read-only historical R5 plan mismatch diagnostic")
    diagnose.add_argument("--repo-root", type=Path)
    args = parser.parse_args(argv)
    if args.command == "diagnose-r5":
        scenarios, requests = historical_r5_paths(args.repo_root)
        report = test_allocator.diagnose_legacy_r5_plan_mismatch(scenarios, requests)
        print(contract.canonical_json(report))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_qualification_requests", "evaluate_qualification_batch",
           "historical_r5_paths", "main"]
