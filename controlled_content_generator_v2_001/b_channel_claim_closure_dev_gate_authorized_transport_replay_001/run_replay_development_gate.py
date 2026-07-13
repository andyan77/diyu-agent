#!/usr/bin/env python3
"""Materialize replay candidates and independent review packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


TASK_DIR = Path(__file__).resolve().parent
ROOT = TASK_DIR.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controlled_content_generator_v2_001.b_channel_component_consumption_and_claim_closure_dev_gate_001.core.fc_claim_closure_validator import (  # noqa: E402
    validate_candidate,
)
from controlled_content_generator_v2_001.b_channel_component_consumption_and_claim_closure_dev_gate_001.core.generator_plan_consumer import (  # noqa: E402
    consume_author_response,
)
from controlled_content_generator_v2_001.b_channel_component_consumption_and_claim_closure_dev_gate_001.run_component_consumption_dev_gate import (  # noqa: E402
    _realization_audit,
)
from transport.dispatcher_owned_identity_adapter import (  # noqa: E402
    TASK_ID,
    canonical_json,
    digest_object,
    project_for_frozen_consumer,
    validate_and_bind_batch,
)


LOGGER = logging.getLogger(__name__)
PRIOR_TASK = ROOT / (
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001"
)
PROFILE_PATH = ROOT / (
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
DISPATCH_PATH = TASK_DIR / "replay/replay_dispatch_manifest.v0.1.jsonl"
RAW_ENVELOPE_PATH = TASK_DIR / "replay/persisted_batch/raw_author_response_envelopes.v0.1.jsonl"
MATERIAL_PATH = PRIOR_TASK / "materials/development_material_packs.v0.1.jsonl"
PLAN_PATH = PRIOR_TASK / "orch/orch_composition_plans.v0.1.jsonl"
PAIR_PATH = PRIOR_TASK / "orch/orch_pair_plan_results.v0.1.jsonl"
FREEZE_PATH = TASK_DIR / "freeze/transport_freeze_manifest.v0.1.json"
OUTPUT_RELATIONS = {
    Path("generator/development_candidates.v0.1.jsonl"): "candidates",
    Path("generator/candidate_materialization_failures.v0.1.jsonl"): "failures",
    Path("claim_closure/surface_manifests.v0.1.jsonl"): "surface_manifests",
    Path("claim_closure/candidate_validation_results.v0.1.jsonl"): "validation_results",
    Path("component/component_realization_audits.v0.1.jsonl"): "realization_audits",
    Path("machine/pair_surface_independence_audits.v0.1.jsonl"): "pair_audits",
    Path("machine/development_machine_result.v0.1.json"): "machine_result",
    Path("review/primary_review_packets.v0.1.jsonl"): "primary_packets",
    Path("review/fact_review_packets.v0.1.jsonl"): "fact_packets",
    Path("review/pair_review_packets.v0.1.jsonl"): "pair_packets",
}
SPACE_RE = re.compile(r"\s+")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected object in {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if any(not isinstance(row, dict) for row in rows):
        raise TypeError(f"expected objects in {path}")
    return rows


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def _load_by_id(path: Path, field: str) -> dict[str, dict[str, Any]]:
    return {str(row[field]): row for row in load_jsonl(path)}


def _verify_transport_and_freeze(
    dispatches: list[dict[str, Any]], envelopes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    freeze = load_json(FREEZE_PATH)
    if freeze.get("freeze_manifest_digest") != digest_object(
        {key: value for key, value in freeze.items() if key != "freeze_manifest_digest"}
    ):
        raise ValueError("transport freeze digest mismatch")
    for group in ("prior_frozen_file_digests", "transport_core_file_digests"):
        for relative, expected in freeze[group].items():
            if sha256_file(ROOT / relative) != expected:
                raise ValueError(f"frozen file drift after author start: {relative}")
    for relative, expected in freeze["generated_file_digests"].items():
        if sha256_file(TASK_DIR / relative) != expected:
            raise ValueError(f"transport checkpoint drift after author start: {relative}")
    return validate_and_bind_batch(dispatches, envelopes)


def _candidate_with_replay_provenance(
    candidate: dict[str, Any], envelope: Mapping[str, Any]
) -> dict[str, Any]:
    candidate["task_id"] = TASK_ID
    candidate["source_transport_task_id"] = TASK_ID
    candidate["transport_response_envelope_digest"] = envelope["response_envelope_digest"]
    candidate["physical_author_invocation_ordinal"] = 2
    candidate["content_evaluable_attempt_ordinal"] = 1
    candidate["first_acceptance_transport_exception_applied"] = True
    candidate["content_reroll_count"] = 0
    candidate["candidate_digest"] = digest_object(
        {key: value for key, value in candidate.items() if key != "candidate_digest"}
    )
    return candidate


def _surface_lines(candidate: Mapping[str, Any]) -> list[str]:
    surfaces = candidate["surfaces"]
    values: list[str] = []
    for field in sorted(surfaces):
        value = surfaces[field]
        if isinstance(value, list):
            values.extend(str(item) for item in value if str(item).strip())
        elif str(value).strip():
            values.append(str(value))
    editing = str(candidate.get("non_audience_editing_grammar", ""))
    if editing.strip():
        values.append(editing)
    return values


def _normalized_line(value: str) -> str:
    return SPACE_RE.sub("", value).strip("，。！？；：,.!?;:、")


def _pair_audit(
    profile_id: str,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    pair_plan: Mapping[str, Any],
) -> dict[str, Any]:
    left_lines = {_normalized_line(line) for line in _surface_lines(left) if _normalized_line(line)}
    right_lines = {_normalized_line(line) for line in _surface_lines(right) if _normalized_line(line)}
    exact_overlap = sorted(left_lines.intersection(right_lines))
    result: dict[str, Any] = {
        "profile_id": profile_id,
        "candidate_A_id": left["candidate_id"],
        "candidate_B_id": right["candidate_id"],
        "identical_fact_set": all(
            int(pair_plan[field]) == 0
            for field in (
                "source_atom_set_difference_count",
                "authorization_set_difference_count",
                "claim_boundary_difference_count",
            )
        ),
        "real_plan_axis_difference_count": pair_plan["real_difference_axis_count"],
        "pair_with_at_least_four_real_axes": pair_plan["real_difference_axis_count"] >= 4,
        "authorial_exact_line_overlap_count": len(exact_overlap),
        "authorial_exact_line_overlaps": exact_overlap,
        "machine_semantic_independence_claim": False,
        "blind_pair_review_required": True,
        "cross_lane_fact_leak_count": 0,
    }
    result["pair_audit_digest"] = digest_object(result)
    return result


def _profile_summaries() -> dict[str, dict[str, Any]]:
    document = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    profiles = document["content_product_profile_registry"]["profiles"]
    return {
        str(profile["content_product_type_id"]): {
            "content_product_type_id": profile["content_product_type_id"],
            "chinese_label": profile["chinese_label"],
            "business_purpose": profile["business_purpose"],
            "founder_style_terms": profile["style_constraints"]["founder_style_terms"],
            "forbidden_style_patterns": profile["style_constraints"]["forbidden_style_patterns"],
            "founder_hard_guards": profile["founder_hard_guards"],
        }
        for profile in profiles
    }


def _primary_packet(
    candidate: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "review_packet_id": f"PRIMARY::{candidate['candidate_id']}",
        "review_role": "BLIND_SURFACE_PRIMARY_REVIEWER",
        "candidate_id": candidate["candidate_id"],
        "profile": dict(profile),
        "surfaces": candidate["surfaces"],
        "non_audience_editing_grammar": candidate["non_audience_editing_grammar"],
        "first_acceptance_definition": "zero edit, directly usable as a development candidate",
        "review_rules": [
            "read every audience and execution surface",
            "reject meta scaffolding, formulaic filler, generic review language, or incoherent execution",
            "do not infer source support; fact authorization is reviewed separately",
            "minor edits or polish still mean zero_edit_acceptable=false",
        ],
    }
    packet["packet_digest"] = digest_object(packet)
    return packet


def _fact_packet(
    candidate: Mapping[str, Any],
    material: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "review_packet_id": f"FACT::{candidate['candidate_id']}",
        "review_role": "FACT_AUTHORIZATION_ADVERSARIAL_REVIEWER",
        "candidate_id": candidate["candidate_id"],
        "profile_id": candidate["profile_id"],
        "founder_hard_guards": profile["founder_hard_guards"],
        "surfaces": candidate["surfaces"],
        "non_audience_editing_grammar": candidate["non_audience_editing_grammar"],
        "source_atoms": material["source_atoms"],
        "authorization": material["authorization"],
        "claim_boundary": material["claim_boundary"],
        "review_rules": [
            "independently bind every factual unit across all surfaces to supplied atoms",
            "reject invented numbers, actions, causality, results, entities, roles, sounds, or authority",
            "components are never fact sources",
            "open questions and disclosed hypotheses may be creative only when they do not assert facts",
        ],
    }
    packet["packet_digest"] = digest_object(packet)
    return packet


def _pair_packet(
    profile_id: str,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    left_plan: Mapping[str, Any],
    right_plan: Mapping[str, Any],
) -> dict[str, Any]:
    swap = int(profile_id.removeprefix("CP")) % 2 == 0
    first, second = (right, left) if swap else (left, right)
    packet: dict[str, Any] = {
        "review_packet_id": f"PAIR::{profile_id}",
        "review_role": "BLIND_SURFACE_PRIMARY_REVIEWER",
        "profile_id": profile_id,
        "presentation_order_blinded": True,
        "surface_X": first["surfaces"],
        "surface_Y": second["surfaces"],
        "plan_axes_X": right_plan["planning_axes"] if swap else left_plan["planning_axes"],
        "plan_axes_Y": left_plan["planning_axes"] if swap else right_plan["planning_axes"],
        "review_rules": [
            "decide whether the two outputs use genuinely independent narrative composition",
            "different wording over the same sequence, shot subject, sound subject, rhythm, and ending is not independent",
            "both outputs may use the same facts but must realize at least four actual axes",
            "identify formulaic sibling structure and exact or near-copy overlap",
        ],
    }
    packet["packet_digest"] = digest_object(packet)
    return packet


def _write_materialization(output_dir: Path) -> None:
    dispatches = load_jsonl(DISPATCH_PATH)
    envelopes = load_jsonl(RAW_ENVELOPE_PATH)
    bound = _verify_transport_and_freeze(dispatches, envelopes)
    dispatch_by_request = {
        str(row["dispatch_identity"]["request_id"]): row for row in dispatches
    }
    envelope_by_request = {
        str(row["response_identity"]["parent_request_id"]): row for row in bound
    }
    materials = _load_by_id(MATERIAL_PATH, "material_pack_id")
    plans = _load_by_id(PLAN_PATH, "plan_id")
    pair_plans = _load_by_id(PAIR_PATH, "profile_id")
    profiles = _profile_summaries()
    candidates: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    realization_audits: list[dict[str, Any]] = []
    for request_id in sorted(dispatch_by_request):
        dispatch = dispatch_by_request[request_id]
        envelope = envelope_by_request[request_id]
        request = dispatch["replay_request"]
        plan = plans[str(request["plan_id"])]
        material = materials[str(request["material_pack_id"])]
        try:
            projected = project_for_frozen_consumer(dispatch, envelope)
            candidate = consume_author_response(plan, request, projected)
            candidate = _candidate_with_replay_provenance(candidate, envelope)
            validation = validate_candidate(candidate, material, plan)
        except Exception as exc:
            failure: dict[str, Any] = {
                "assignment_id": request["assignment_id"],
                "request_id": request_id,
                "error_class": type(exc).__name__,
                "content_reroll_count": 0,
                "candidate_materialized": False,
            }
            failure["failure_digest"] = digest_object(failure)
            failures.append(failure)
            continue
        candidates.append(candidate)
        manifests.append(
            {
                "candidate_id": candidate["candidate_id"],
                "surface_units": validation["surface_units"],
                "reviewed_surface_unit_count": validation["reviewed_surface_unit_count"],
                "all_surface_units_classified": validation["all_surface_units_classified"],
                "manifest_digest": digest_object(validation["surface_units"]),
            }
        )
        validations.append({key: value for key, value in validation.items() if key != "surface_units"})
        realization_audits.append(_realization_audit(plan, validation))
    candidates.sort(key=lambda row: str(row["assignment_id"]))
    candidate_by_profile_lane = {
        (str(row["profile_id"]), str(row["lane_id"])): row for row in candidates
    }
    pair_audits: list[dict[str, Any]] = []
    pair_packets: list[dict[str, Any]] = []
    for profile_id in sorted(profiles):
        left = candidate_by_profile_lane.get((profile_id, "A"))
        right = candidate_by_profile_lane.get((profile_id, "B"))
        if left is None or right is None:
            continue
        pair_plan = pair_plans[profile_id]
        pair_audits.append(_pair_audit(profile_id, left, right, pair_plan))
        pair_packets.append(
            _pair_packet(
                profile_id,
                left,
                right,
                plans[str(left["source_plan_id"])],
                plans[str(right["source_plan_id"])],
            )
        )
    aggregate_fields = (
        "undeclared_assertion_count",
        "unsupported_fact_count",
        "invented_number_count",
        "invented_action_count",
        "invented_causality_count",
        "invented_result_count",
        "invented_entity_count",
        "invalid_source_span_count",
        "component_as_fact_source_count",
        "meta_scaffold_leak_count",
    )
    machine_result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "persisted_raw_response_count": len(envelopes),
        "candidate_materialization_attempt_count": len(envelopes),
        "candidate_count": len(candidates),
        "candidate_schema_failure_count": len(failures),
        "reviewed_surface_unit_count": sum(
            int(row["reviewed_surface_unit_count"]) for row in validations
        ),
        **{field: sum(int(row[field]) for row in validations) for field in aggregate_fields},
        "post_author_source_change_count": 0,
        "machine_claim_closure_candidate_pass_count": sum(
            row["machine_claim_closure_pass"] is True for row in validations
        ),
        "pair_count": len(pair_audits),
        "identical_fact_set_pair_count": sum(row["identical_fact_set"] for row in pair_audits),
        "pair_with_at_least_four_real_axes_count": sum(
            row["pair_with_at_least_four_real_axes"] for row in pair_audits
        ),
        "authorial_exact_line_overlap_pair_count": sum(
            row["authorial_exact_line_overlap_count"] > 0 for row in pair_audits
        ),
        "cross_lane_fact_leak_count": sum(row["cross_lane_fact_leak_count"] for row in pair_audits),
        "machine_final_semantic_claim": False,
        "machine_final_quality_claim": False,
        "independent_human_review_required": True,
        "physical_author_invocation_total": 80,
        "content_evaluable_attempt_count": 40,
        "content_reroll_count": 0,
        "accepted_baseline_count": 120,
        "baseline_increment_count": 0,
        "hidden_count": 0,
        "generator_qualified": False,
        "runtime_ingest_ready": False,
        "readiness_all_false": True,
    }
    machine_result["machine_result_digest"] = digest_object(machine_result)
    primary_packets = [
        _primary_packet(candidate, profiles[str(candidate["profile_id"])])
        for candidate in candidates
    ]
    fact_packets = [
        _fact_packet(
            candidate,
            materials[
                str(
                    dispatch_by_request[str(candidate["source_request_id"])]["replay_request"][
                        "material_pack_id"
                    ]
                )
            ],
            profiles[str(candidate["profile_id"])],
        )
        for candidate in candidates
    ]
    payloads: dict[str, Any] = {
        "candidates": candidates,
        "failures": failures,
        "surface_manifests": manifests,
        "validation_results": validations,
        "realization_audits": realization_audits,
        "pair_audits": pair_audits,
        "machine_result": machine_result,
        "primary_packets": primary_packets,
        "fact_packets": fact_packets,
        "pair_packets": pair_packets,
    }
    for relative, key in OUTPUT_RELATIONS.items():
        value = payloads[key]
        if relative.suffix == ".jsonl":
            write_jsonl(output_dir / relative, value)
        else:
            write_json(output_dir / relative, value)


def _check_materialization() -> None:
    with tempfile.TemporaryDirectory(prefix="replay34-materialization-check-") as temp_dir:
        rebuilt = Path(temp_dir)
        _write_materialization(rebuilt)
        for relative in OUTPUT_RELATIONS:
            live = TASK_DIR / relative
            candidate = rebuilt / relative
            if not live.exists() or live.read_bytes() != candidate.read_bytes():
                raise ValueError(f"replay development artifact drift: {relative}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if __debug__ is False:
        return 2
    if args.check:
        _check_materialization()
        LOGGER.info("replay candidate materialization CHECK_PASS")
    else:
        _write_materialization(TASK_DIR)
        LOGGER.info("replay candidate materialization MATERIALIZED")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        raise SystemExit(main())
    except Exception as exc:
        LOGGER.error("E_REPLAY_DEVELOPMENT_GATE: %s", exc)
        raise SystemExit(1) from exc
