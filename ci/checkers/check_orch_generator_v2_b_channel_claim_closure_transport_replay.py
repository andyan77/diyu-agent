#!/usr/bin/env python3
"""Independently verify the authorized transport replay and honest DEV stop."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    print("authorized transport replay checker refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_CLAIM_CLOSURE_DEV_GATE_AUTHORIZED_TRANSPORT_REPLAY_001"
TASK_DIR = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_claim_closure_dev_gate_authorized_transport_replay_001"
)
PRIOR_TASK = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001"
)
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
HORIZON_PATH = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001/"
    "phase_0/current_ledger_horizon.v0.1.yaml"
)
DEV_CHECKER_PATH = Path(
    "ci/checkers/check_orch_generator_v2_b_channel_component_consumption_dev_gate.py"
)
B_CHANNEL_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_b_channel_24_component_review.py")
DISPATCH_PATH = TASK_DIR / "replay/replay_dispatch_manifest.v0.1.jsonl"
ENVELOPE_PATH = TASK_DIR / "replay/persisted_batch/raw_author_response_envelopes.v0.1.jsonl"
CANDIDATE_PATH = TASK_DIR / "generator/development_candidates.v0.1.jsonl"
VALIDATION_PATH = TASK_DIR / "claim_closure/candidate_validation_results.v0.1.jsonl"
SURFACE_MANIFEST_PATH = TASK_DIR / "claim_closure/surface_manifests.v0.1.jsonl"
PAIR_PATH = TASK_DIR / "machine/pair_surface_independence_audits.v0.1.jsonl"
MACHINE_PATH = TASK_DIR / "machine/development_machine_result.v0.1.json"
PERSISTENCE_PATH = TASK_DIR / "replay/persisted_batch/atomic_persistence_receipt.v0.1.json"
REVIEW_FAILURE_PATH = TASK_DIR / "review/review_execution_failure.v0.1.json"
RESULT_PATH = TASK_DIR / "result/development_gate_result.v0.1.json"
GUARDIAN_PATH = TASK_DIR / "guardian/guardian_review_packet.v0.1.json"
FREEZE_PATH = TASK_DIR / "freeze/transport_freeze_manifest.v0.1.json"
COMPAT_PATH = TASK_DIR / "compatibility/live_checker_reference_safe_repairs.v0.1.json"
ROUTE_LINE_PREFIX = "  route_migration_"
HISTORICAL_ROUTE_DIGESTS_19_33 = {
    19: "a10f1a8477b7b36435ce16f806d21eec505b7d0eee39084666edbc7b9e67f76a",
    20: "ca76d27c8a84ee4a5888c17a0d88249b651de05314fc81a553d031981db4a5a3",
    21: "ba3f824ba4699c821a34416641a55f480451afdc371131916bcf30bb031b8195",
    22: "5ade29110d186c98c05fe17ed07b62a11bd590aafb38a5cec5fa10973e89fc1b",
    23: "0b7568944bdf073c5b6842263a954e59dc016709518fa57ece86b0ba2b365045",
    24: "5a64c5130872905521bfa536e2d64e17f66a2c589dbd80b3c45183a78fcfb862",
    25: "1fef7a924fe2abb7e28c5ba5a06e86a8e2421084043d02d35502ce8b1aa7da38",
    26: "6383578d17aba2642b1e1299f6227954c5846ea7a83203949303d43e233c8e3d",
    27: "58c4768bcc91ce69ffda835a85f257a1ac99116fd4276c5d1aaf7b0367a6eb1a",
    28: "35491c51661a0f39d44410d4aa08753c10e6edb9e958304802a294a00f54c880",
    29: "bc7c526085bba2e4c0b7f0cd439f9218bce81bd2e393e2f15aec6d3cce7ce456",
    30: "143ee83792fefa5f48e577350d3aa0d4ae84d79dd9f4d2866fe363620c3d6f51",
    31: "b2d7ea6f24df0db18acfb40ea6e2d50249d41320302473068dff0b688b952e48",
    32: "098b9070582e52e8d03f4bd884d317b97b650ffae7ec6c3035f1ec9993dc0e33",
    33: "c24cf07ba96cb58083a33e95dd3972527e9d93d0b1e34f631dc354b8e382bff7",
}
READY_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "Serving_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "release_ready",
        "production_ready",
        "generator_qualified",
        "runtime_provider_adapter_qualified",
        "runtime_ingest_ready",
        "generation_600_allowed",
        "expand_3600_allowed",
    }
)


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML mapping keys."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


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
        raise TypeError(f"expected object rows in {path}")
    return rows


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"expected mapping in {path}")
    return value


def add_error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def recursive_pairs(value: Any) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            pairs.append((str(key), child))
            pairs.extend(recursive_pairs(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            pairs.extend(recursive_pairs(child))
    return pairs


def route_blocks(text: str) -> tuple[dict[int, str], list[int], list[str]]:
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    order: list[int] = []
    shadows: list[str] = []
    for index, line in enumerate(lines):
        if not line.startswith(ROUTE_LINE_PREFIX) or not line.endswith(":"):
            continue
        suffix = line[len(ROUTE_LINE_PREFIX) : -1]
        if not suffix.isdigit():
            shadows.append(suffix)
            continue
        route_id = int(suffix)
        starts.append((route_id, index))
        order.append(route_id)
    blocks: dict[int, str] = {}
    for route_id, start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if lines[index].startswith("  ") and not lines[index].startswith("    ") and lines[index].endswith(":"):
                end = index
                break
        blocks[route_id] = "\n".join(lines[start:end]) + "\n"
    return blocks, order, shadows


def required_paths(root: Path) -> list[Path]:
    paths = [
        TASK_DIR / "phase_0/pr12_merge_receipt.v0.1.json",
        TASK_DIR / "transport/transport_identity_contract.v0.1.json",
        TASK_DIR / "transport/transport_root_cause_analysis.v0.1.yaml",
        TASK_DIR / "t0/transport_t0_cases.v0.1.jsonl",
        TASK_DIR / "t0/transport_t0_results.v0.1.jsonl",
        TASK_DIR / "t0/transport_t0_result.v0.1.json",
        DISPATCH_PATH,
        ENVELOPE_PATH,
        PERSISTENCE_PATH,
        CANDIDATE_PATH,
        VALIDATION_PATH,
        SURFACE_MANIFEST_PATH,
        PAIR_PATH,
        MACHINE_PATH,
        REVIEW_FAILURE_PATH,
        RESULT_PATH,
        GUARDIAN_PATH,
        FREEZE_PATH,
        COMPAT_PATH,
        LEDGER_PATH,
        HORIZON_PATH,
        DEV_CHECKER_PATH,
        B_CHANNEL_CHECKER_PATH,
        PRIOR_TASK / "author/author_session_failure_receipt.v0.1.json",
        PRIOR_TASK / "result/development_gate_result.v0.1.json",
        PRIOR_TASK / "guardian/guardian_review_packet.v0.1.json",
    ]
    freeze_path = root / FREEZE_PATH
    if freeze_path.exists():
        freeze = load_json(freeze_path)
        for group in ("prior_frozen_file_digests", "transport_core_file_digests"):
            paths.extend(Path(relative) for relative in freeze.get(group, {}))
        paths.extend(TASK_DIR / relative for relative in freeze.get("generated_file_digests", {}))
    return sorted(set(paths))


def _check_phase0_and_freeze(root: Path, errors: list[dict[str, str]]) -> None:
    receipt = load_json(root / TASK_DIR / "phase_0/pr12_merge_receipt.v0.1.json")
    expected = {
        "reviewed_head_sha": "e0f004e403a1947691178d42c0a33e32f0ecd767",
        "merge_commit_sha": "f5e458730aca52e63748f597e007352b72d7bb63",
        "merge_tree": "138f49b10220a0010bc15f75234b2d542b185922",
        "merge_method": "merge_commit",
        "admin_bypass_used": False,
        "master_ci_run_id": 29228408541,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            add_error(errors, "E_PHASE0_BINDING", f"{key}={receipt.get(key)}")
    if receipt.get("receipt_digest") != object_digest(receipt, "receipt_digest"):
        add_error(errors, "E_PHASE0_DIGEST", "receipt")

    freeze = load_json(root / FREEZE_PATH)
    if freeze.get("freeze_manifest_digest") != object_digest(freeze, "freeze_manifest_digest"):
        add_error(errors, "E_FREEZE_DIGEST", "transport freeze")
    for group in ("prior_frozen_file_digests", "transport_core_file_digests"):
        for relative, expected_digest in freeze.get(group, {}).items():
            path = root / relative
            if not path.exists() or sha256_file(path) != expected_digest:
                add_error(errors, "E_FROZEN_FILE", relative)
    for relative, expected_digest in freeze.get("generated_file_digests", {}).items():
        path = root / TASK_DIR / relative
        if not path.exists() or sha256_file(path) != expected_digest:
            add_error(errors, "E_FROZEN_CHECKPOINT", relative)
    if freeze.get("frozen_before_real_author_replay") is not True:
        add_error(errors, "E_FREEZE_ORDER", "transport was not frozen before author replay")


def _check_t0(root: Path, errors: list[dict[str, str]]) -> None:
    cases = load_jsonl(root / TASK_DIR / "t0/transport_t0_cases.v0.1.jsonl")
    rows = load_jsonl(root / TASK_DIR / "t0/transport_t0_results.v0.1.jsonl")
    result = load_json(root / TASK_DIR / "t0/transport_t0_result.v0.1.json")
    if len(cases) != 34 or len(rows) != 34:
        add_error(errors, "E_T0_CASE_COUNT", f"{len(cases)}/{len(rows)}")
    if {row.get("case_id") for row in cases} != {row.get("case_id") for row in rows}:
        add_error(errors, "E_T0_CASE_IDENTITY", "case/result identities differ")
    if any(row.get("expected") != row.get("observed") for row in rows):
        add_error(errors, "E_T0_RESULT", "expected/observed mismatch")
    expected_flags = {
        "status": "PASS",
        "positive_case_count": 8,
        "negative_case_count": 26,
        "valid_binding_count": 40,
        "request_response_binding_mismatch_count": 0,
        "duplicate_request_id_count": 0,
        "duplicate_response_id_count": 0,
        "completion_order_invariance": True,
        "request_order_invariance": True,
        "repeated_run_byte_identity": True,
        "real_author_replay_count": 0,
    }
    for key, value in expected_flags.items():
        if result.get(key) != value:
            add_error(errors, "E_T0_RESULT", f"{key}={result.get(key)}")
    if result.get("t0_result_digest") != object_digest(result, "t0_result_digest"):
        add_error(errors, "E_T0_DIGEST", "result")


def _check_transport(root: Path, errors: list[dict[str, str]]) -> None:
    dispatches = load_jsonl(root / DISPATCH_PATH)
    envelopes = load_jsonl(root / ENVELOPE_PATH)
    if len(dispatches) != 40 or len(envelopes) != 40:
        add_error(errors, "E_ATOMIC_BATCH_COUNT", f"{len(dispatches)}/{len(envelopes)}")
        return
    by_request: dict[str, dict[str, Any]] = {}
    response_ids: set[str] = set()
    for row in dispatches:
        identity = row.get("dispatch_identity", {})
        request = row.get("replay_request", {})
        request_id = identity.get("request_id")
        if not isinstance(request_id, str) or request_id in by_request:
            add_error(errors, "E_REQUEST_IDENTITY", str(request_id))
            continue
        by_request[request_id] = row
        if row.get("dispatch_record_digest") != object_digest(row, "dispatch_record_digest"):
            add_error(errors, "E_DISPATCH_DIGEST", request_id)
        if identity.get("dispatch_manifest_digest") != object_digest(identity, "dispatch_manifest_digest"):
            add_error(errors, "E_DISPATCH_IDENTITY_DIGEST", request_id)
        if request.get("request_digest") != object_digest(request, "request_digest"):
            add_error(errors, "E_REQUEST_DIGEST", request_id)
        checks = {
            "assignment_id": request.get("assignment_id"),
            "lane_id": request.get("lane_id"),
            "plan_id": request.get("plan_id"),
            "plan_digest": request.get("plan_digest"),
            "request_id": request.get("request_id"),
        }
        if any(identity.get(key) != value for key, value in checks.items()):
            add_error(errors, "E_DISPATCH_CROSS_BINDING", request_id)
        if row.get("physical_invocation_ordinal") != 2 or row.get("content_evaluable_attempt_ordinal") != 1:
            add_error(errors, "E_REPLAY_ORDINAL", request_id)
        if row.get("no_content_feedback_carried_forward") is not True:
            add_error(errors, "E_FEEDBACK_POLLUTION", request_id)

    for envelope in envelopes:
        response = envelope.get("response_identity", {})
        request_id = response.get("parent_request_id")
        response_id = response.get("response_id")
        dispatch = by_request.get(str(request_id))
        if dispatch is None:
            add_error(errors, "E_STALE_OR_UNKNOWN_RESPONSE", str(request_id))
            continue
        if not isinstance(response_id, str) or response_id in response_ids:
            add_error(errors, "E_RESPONSE_IDENTITY", str(response_id))
        response_ids.add(str(response_id))
        identity = dispatch["dispatch_identity"]
        expected = {
            "parent_run_id": identity["run_id"],
            "parent_assignment_id": identity["assignment_id"],
            "parent_lane_id": identity["lane_id"],
            "parent_request_id": identity["request_id"],
            "parent_session_id": identity["session_id"],
            "response_id": dispatch["expected_response_id"],
            "binding_method": "PARENT_REQUEST_ID",
        }
        if any(response.get(key) != value for key, value in expected.items()):
            add_error(errors, "E_RESPONSE_CROSS_BINDING", str(request_id))
        payload = envelope.get("author_payload")
        if not isinstance(payload, dict) or response.get("payload_digest") != hashlib.sha256(
            canonical_json(payload).encode("utf-8")
        ).hexdigest():
            add_error(errors, "E_PAYLOAD_DIGEST", str(request_id))
        forbidden_identity = {
            "request_id",
            "request_digest",
            "response_id",
            "assignment_id",
            "session_id",
            "lane_id",
        }
        if forbidden_identity.intersection(payload):
            add_error(errors, "E_AUTHOR_IDENTITY_WRITE", str(request_id))
        if envelope.get("author_identity_write_count") != 0:
            add_error(errors, "E_AUTHOR_IDENTITY_WRITE", str(request_id))
        if envelope.get("transport_authority") != "DISPATCHER_OWNED_IDENTITY":
            add_error(errors, "E_TRANSPORT_AUTHORITY", str(request_id))
        if envelope.get("response_envelope_digest") != object_digest(envelope, "response_envelope_digest"):
            add_error(errors, "E_RESPONSE_ENVELOPE_DIGEST", str(request_id))

    receipt = load_json(root / PERSISTENCE_PATH)
    derived = {
        "physical_author_invocation_total": 40 + len(dispatches),
        "content_evaluable_attempt_count": len(envelopes),
        "persisted_raw_response_count": len(envelopes),
        "staged_response_count": len(envelopes),
        "transport_valid_response_count": len(envelopes),
        "content_reroll_count": sum(int(row.get("content_reroll_count", 0)) for row in dispatches),
        "replacement_count": 0,
        "selective_retry_count": 0,
        "third_attempt_allowed": False,
        "atomic_batch_persistence": True,
    }
    for key, value in derived.items():
        if receipt.get(key) != value:
            add_error(errors, "E_REPLAY_COUNTING", f"{key}={receipt.get(key)} derived={value}")
    if receipt.get("persistence_receipt_digest") != object_digest(receipt, "persistence_receipt_digest"):
        add_error(errors, "E_PERSISTENCE_DIGEST", "receipt")


def _check_candidates_and_machine(root: Path, errors: list[dict[str, str]]) -> None:
    candidates = load_jsonl(root / CANDIDATE_PATH)
    validations = load_jsonl(root / VALIDATION_PATH)
    surface_manifests = load_jsonl(root / SURFACE_MANIFEST_PATH)
    pairs = load_jsonl(root / PAIR_PATH)
    machine = load_json(root / MACHINE_PATH)
    if len(candidates) != 40 or len(validations) != 40 or len(surface_manifests) != 40 or len(pairs) != 20:
        add_error(
            errors,
            "E_DEVELOPMENT_EVIDENCE_COUNT",
            f"{len(candidates)}/{len(validations)}/{len(surface_manifests)}/{len(pairs)}",
        )
        return
    candidate_ids = {str(row.get("candidate_id")) for row in candidates}
    if len(candidate_ids) != 40 or {str(row.get("candidate_id")) for row in validations} != candidate_ids:
        add_error(errors, "E_CANDIDATE_IDENTITY", "candidate/validation identities")
    for row in candidates:
        if row.get("candidate_digest") != object_digest(row, "candidate_digest"):
            add_error(errors, "E_CANDIDATE_DIGEST", str(row.get("candidate_id")))
        if row.get("content_reroll_count") != 0 or row.get("first_acceptance_transport_exception_applied") is not True:
            add_error(errors, "E_CANDIDATE_REPLAY_PROVENANCE", str(row.get("candidate_id")))
        for key in ("publishable", "production_consumable", "runtime_consumable", "may_enter_baseline"):
            if row.get(key) is not False:
                add_error(errors, "E_CANDIDATE_BOUNDARY", f"{row.get('candidate_id')}:{key}")
    surfaces_by_candidate = {
        str(row.get("candidate_id")): row for row in surface_manifests
    }
    for row in validations:
        manifest = surfaces_by_candidate.get(str(row.get("candidate_id")), {})
        surface_units = manifest.get("surface_units")
        if manifest.get("manifest_digest") != hashlib.sha256(
            canonical_json(surface_units).encode("utf-8")
        ).hexdigest():
            add_error(errors, "E_SURFACE_MANIFEST_DIGEST", str(row.get("candidate_id")))
        full_validation = dict(row)
        full_validation["surface_units"] = surface_units
        if row.get("validation_digest") != object_digest(full_validation, "validation_digest"):
            add_error(errors, "E_VALIDATION_DIGEST", str(row.get("candidate_id")))
    for row in pairs:
        if row.get("pair_audit_digest") != object_digest(row, "pair_audit_digest"):
            add_error(errors, "E_PAIR_DIGEST", str(row.get("profile_id")))

    aggregate_fields = (
        "reviewed_surface_unit_count",
        "undeclared_assertion_count",
        "unsupported_fact_count",
        "invented_number_count",
        "invented_action_count",
        "invented_causality_count",
        "invented_result_count",
        "invented_entity_count",
        "invalid_source_span_count",
        "post_author_source_change_count",
        "component_as_fact_source_count",
        "meta_scaffold_leak_count",
    )
    for field in aggregate_fields:
        derived = sum(int(row.get(field, 0)) for row in validations)
        if machine.get(field) != derived:
            add_error(errors, "E_MACHINE_AGGREGATE", f"{field}={machine.get(field)} derived={derived}")
    pair_derived = {
        "identical_fact_set_pair_count": sum(row.get("identical_fact_set") is True for row in pairs),
        "pair_with_at_least_four_real_axes_count": sum(
            row.get("pair_with_at_least_four_real_axes") is True for row in pairs
        ),
        "authorial_exact_line_overlap_pair_count": sum(
            int(row.get("authorial_exact_line_overlap_count", 0)) > 0 for row in pairs
        ),
        "cross_lane_fact_leak_count": sum(int(row.get("cross_lane_fact_leak_count", 0)) for row in pairs),
    }
    for key, value in pair_derived.items():
        if machine.get(key) != value:
            add_error(errors, "E_MACHINE_PAIR_AGGREGATE", f"{key}={machine.get(key)} derived={value}")
    if machine.get("machine_result_digest") != object_digest(machine, "machine_result_digest"):
        add_error(errors, "E_MACHINE_DIGEST", "result")
    if machine.get("invented_number_count", 0) <= 0 or machine.get("invented_action_count", 0) <= 0:
        add_error(errors, "E_CONTENT_FAILURE_ERASED", "machine hard findings")


def _check_review_and_result(root: Path, errors: list[dict[str, str]]) -> None:
    failure = load_json(root / REVIEW_FAILURE_PATH)
    if failure.get("failure_digest") != object_digest(failure, "failure_digest"):
        add_error(errors, "E_REVIEW_FAILURE_DIGEST", "review")
    if failure.get("status") != "INDEPENDENT_REVIEW_EXECUTION_FAILED":
        add_error(errors, "E_REVIEW_FAILURE_STATE", str(failure.get("status")))
    if (root / TASK_DIR / "review/persisted_reviews").exists():
        add_error(errors, "E_PARTIAL_REVIEW_PERSISTED", "review/persisted_reviews")
    result = load_json(root / RESULT_PATH)
    if result.get("result_digest") != object_digest(result, "result_digest"):
        add_error(errors, "E_RESULT_DIGEST", "result")
    expected = {
        "verdict": "STOPPED_BEFORE_HIDDEN",
        "task_status": "STOPPED_BEFORE_HIDDEN_CONTENT_GATE_FAILED",
        "dev_gate_pass": False,
        "dev_gate_pass_candidate": False,
    }
    for key, value in expected.items():
        if result.get(key) != value:
            add_error(errors, "E_FAILURE_NOT_RECORDED", f"{key}={result.get(key)}")
    blocking = set(result.get("blocking_items", []))
    required_blocking = {
        "INDEPENDENT_REVIEW_EXECUTION_FAILED",
        "INVENTED_ACTION",
        "INVENTED_CAUSALITY",
        "INVENTED_NUMBER",
        "AUTHORIAL_EXACT_LINE_OVERLAP",
    }
    if blocking != required_blocking:
        add_error(errors, "E_BLOCKING_ITEMS", str(sorted(blocking)))
    review = result.get("independent_review", {})
    if review.get("quality_evaluation_completed") is not False or any(
        review.get(key) != 0
        for key in (
            "completed_primary_candidate_review_count",
            "completed_fact_candidate_review_count",
            "completed_pair_review_count",
        )
    ):
        add_error(errors, "E_FALSE_REVIEW_COMPLETION", str(review))
    gate = result.get("development_gate", {})
    if gate.get("dev_gate_pass") is not False or gate.get("structural_failure_count") != 1:
        add_error(errors, "E_DEVELOPMENT_GATE", str(gate))
    if any(gate.get(key) is not None for key in (
        "first_acceptance_total",
        "first_acceptance_A",
        "first_acceptance_B",
        "fully_accepted_pair_count",
        "semantically_independent_pair_count",
    )):
        add_error(errors, "E_UNPROVEN_CONTENT_SCORE", "incomplete review produced scores")
    boundaries = result.get("boundaries", {})
    expected_boundaries = {
        "accepted_baseline_count": 120,
        "baseline_increment_count": 0,
        "hidden_count": 0,
        "generator_qualified": False,
        "runtime_provider_adapter_qualified": False,
        "runtime_generation_eligible_profile_count": 0,
        "runtime_ingest_ready": False,
        "published_content_count": 0,
        "production_candidate_count": 0,
        "generation_600_allowed": False,
        "expand_3600_allowed": False,
        "readiness_all_false": True,
        "external_provider_API_call_count": 0,
        "KE_truth_change_count": 0,
        "RAG_change_count": 0,
        "DIFY_change_count": 0,
        "Serving_change_count": 0,
    }
    if boundaries != expected_boundaries:
        add_error(errors, "E_BOUNDARIES", str(boundaries))
    packet = load_json(root / GUARDIAN_PATH)
    if packet.get("packet_digest") != object_digest(packet, "packet_digest"):
        add_error(errors, "E_GUARDIAN_PACKET_DIGEST", "packet")
    if packet.get("eligible_to_open_sealed_hidden") is not False:
        add_error(errors, "E_HIDDEN_ELIGIBILITY", "guardian packet")
    for document in (result, packet):
        for key, value in recursive_pairs(document):
            if key in READY_KEYS and value is True:
                add_error(errors, "E_READINESS_TRUE", key)


def _check_ledger_and_compatibility(root: Path, errors: list[dict[str, str]]) -> None:
    ledger = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    horizon = load_yaml(root / HORIZON_PATH)["ledger_horizon"]
    if horizon.get("horizon_digest") != object_digest(horizon, "horizon_digest"):
        add_error(errors, "E_HORIZON_DIGEST", "horizon")
    expected_horizon = {
        "previous_terminal_route_id": 33,
        "authorized_new_route_ids": [34],
        "authorized_terminal_route_id": 34,
        "authorization_task_id": TASK_ID,
        "unknown_future_successor_allowed": False,
        "derivation_source": "FOUNDER_AUTHORIZED_HORIZON_FILE",
    }
    for key, value in expected_horizon.items():
        if horizon.get(key) != value:
            add_error(errors, "E_HORIZON_POLICY", f"{key}={horizon.get(key)}")
    text = (root / LEDGER_PATH).read_text(encoding="utf-8")
    blocks, order, shadows = route_blocks(text)
    if shadows or [route for route in order if 19 <= route <= 34] != list(range(19, 35)):
        add_error(errors, "E_LEDGER_SEQUENCE", str(order))
    for route_id, expected_digest in HISTORICAL_ROUTE_DIGESTS_19_33.items():
        if hashlib.sha256(blocks.get(route_id, "").encode("utf-8")).hexdigest() != expected_digest:
            add_error(errors, "E_HISTORICAL_ROUTE_DIGEST", str(route_id))
    frozen = horizon.get("frozen_route_sha256", {})
    if set(frozen) != {str(route) for route in range(19, 35)}:
        add_error(errors, "E_HORIZON_FROZEN_KEYS", str(sorted(frozen)))
    if frozen.get("34") != hashlib.sha256(blocks.get(34, "").encode("utf-8")).hexdigest():
        add_error(errors, "E_ROUTE34_BLOCK_DIGEST", "route34")
    route34 = ledger.get("route_migration_34")
    if not isinstance(route34, dict) or route34.get("applied_by_task") != TASK_ID:
        add_error(errors, "E_ROUTE34", "task binding")
    elif route34.get("migration_digest") != object_digest(route34, "migration_digest"):
        add_error(errors, "E_ROUTE34_DIGEST", "object digest")
    if "route_migration_35" in ledger:
        add_error(errors, "E_ROUTE35", "unauthorized successor")

    compatibility = load_json(root / COMPAT_PATH)
    if compatibility.get("repair_digest") != object_digest(compatibility, "repair_digest"):
        add_error(errors, "E_COMPAT_DIGEST", "receipt")
    if compatibility.get("current_live_checker_modified_count") != 2:
        add_error(errors, "E_COMPAT_SCOPE", "live checker count")
    if compatibility.get("sealed_checker_modified_count") != 0:
        add_error(errors, "E_COMPAT_SCOPE", "sealed checker modified")
    for repair in compatibility.get("repairs", []):
        path = root / str(repair.get("path"))
        if not path.exists() or repair.get("after_sha256") != sha256_file(path):
            add_error(errors, "E_COMPAT_AFTER", str(path))


def validate(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    paths = required_paths(root)
    missing = [path.as_posix() for path in paths if not (root / path).exists()]
    if missing:
        add_error(errors, "E_REQUIRED_FILE", str(missing))
        return errors
    try:
        _check_phase0_and_freeze(root, errors)
        _check_t0(root, errors)
        _check_transport(root, errors)
        _check_candidates_and_machine(root, errors)
        _check_review_and_result(root, errors)
        _check_ledger_and_compatibility(root, errors)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        add_error(errors, "E_PARSE_OR_SCHEMA", str(exc))
    return errors


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def mutate_json(path: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    value = load_json(path)
    mutator(value)
    _write_json(path, value)


def mutate_jsonl(path: Path, mutator: Callable[[list[dict[str, Any]]], None]) -> None:
    rows = load_jsonl(path)
    mutator(rows)
    _write_jsonl(path, rows)


def mutate_yaml(path: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    value = load_yaml(path)
    mutator(value)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")


def copy_fixture(root: Path, destination: Path) -> None:
    shutil.copytree(root / TASK_DIR, destination / TASK_DIR)
    for path in required_paths(root):
        if path.is_relative_to(TASK_DIR):
            continue
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, target)


def selftest(root: Path) -> int:
    baseline = validate(root)
    if baseline:
        print(json.dumps({"status": "SELFTEST_BASE_INVALID", "errors": baseline}, ensure_ascii=False))
        return 1
    tests: list[tuple[str, str, Callable[[Path], None]]] = []

    def add(name: str, code: str, mutation: Callable[[Path], None]) -> None:
        tests.append((name, code, mutation))

    add("prior_failure_cleared", "E_FROZEN_FILE", lambda temp: mutate_json(
        temp / PRIOR_TASK / "result/development_gate_result.v0.1.json", lambda row: row.update({"dev_gate_pass": True})
    ))
    add("transport_core_mutated", "E_FROZEN_FILE", lambda temp: (temp / TASK_DIR / "transport/dispatcher_owned_identity_adapter.py").write_text("mutation\n", encoding="utf-8"))
    add("T0_not_passed", "E_T0_RESULT", lambda temp: mutate_json(temp / TASK_DIR / "t0/transport_t0_result.v0.1.json", lambda row: row.update({"status": "FAIL"})))
    add("T0_case_removed", "E_T0_CASE_COUNT", lambda temp: mutate_jsonl(temp / TASK_DIR / "t0/transport_t0_cases.v0.1.jsonl", lambda rows: rows.pop()))
    add("selective_replay", "E_REPLAY_COUNTING", lambda temp: mutate_json(temp / PERSISTENCE_PATH, lambda row: row.update({"selective_retry_count": 1})))
    add("replacement", "E_REPLAY_COUNTING", lambda temp: mutate_json(temp / PERSISTENCE_PATH, lambda row: row.update({"replacement_count": 1})))
    add("third_attempt", "E_REPLAY_COUNTING", lambda temp: mutate_json(temp / PERSISTENCE_PATH, lambda row: row.update({"third_attempt_allowed": True})))
    add("physical_count_hidden", "E_REPLAY_COUNTING", lambda temp: mutate_json(temp / PERSISTENCE_PATH, lambda row: row.update({"physical_author_invocation_total": 40})))
    add("denominator_80", "E_REPLAY_COUNTING", lambda temp: mutate_json(temp / PERSISTENCE_PATH, lambda row: row.update({"content_evaluable_attempt_count": 80})))
    add("second_call_as_first", "E_REPLAY_ORDINAL", lambda temp: mutate_jsonl(temp / DISPATCH_PATH, lambda rows: rows[0].update({"physical_invocation_ordinal": 1})))
    add("request_id_missing", "E_REQUEST_IDENTITY", lambda temp: mutate_jsonl(temp / DISPATCH_PATH, lambda rows: rows[0]["dispatch_identity"].pop("request_id")))
    add("request_id_mismatch", "E_DISPATCH_CROSS_BINDING", lambda temp: mutate_jsonl(temp / DISPATCH_PATH, lambda rows: rows[0]["replay_request"].update({"request_id": "WRONG"})))
    add("duplicate_request", "E_REQUEST_IDENTITY", lambda temp: mutate_jsonl(temp / DISPATCH_PATH, lambda rows: rows[1]["dispatch_identity"].update({"request_id": rows[0]["dispatch_identity"]["request_id"]})))
    add("duplicate_response", "E_RESPONSE_IDENTITY", lambda temp: mutate_jsonl(temp / ENVELOPE_PATH, lambda rows: rows[1]["response_identity"].update({"response_id": rows[0]["response_identity"]["response_id"]})))
    add("lane_swap", "E_RESPONSE_CROSS_BINDING", lambda temp: mutate_jsonl(temp / ENVELOPE_PATH, lambda rows: rows[0]["response_identity"].update({"parent_lane_id": "B"})))
    add("assignment_swap", "E_RESPONSE_CROSS_BINDING", lambda temp: mutate_jsonl(temp / ENVELOPE_PATH, lambda rows: rows[0]["response_identity"].update({"parent_assignment_id": "CCV2-DEV-CP20-B-001"})))
    add("session_swap", "E_RESPONSE_CROSS_BINDING", lambda temp: mutate_jsonl(temp / ENVELOPE_PATH, lambda rows: rows[0]["response_identity"].update({"parent_session_id": "STALE"})))
    add("stale_response", "E_STALE_OR_UNKNOWN_RESPONSE", lambda temp: mutate_jsonl(temp / ENVELOPE_PATH, lambda rows: rows[0]["response_identity"].update({"parent_request_id": "OLD"})))
    add("author_identity_write", "E_AUTHOR_IDENTITY_WRITE", lambda temp: mutate_jsonl(temp / ENVELOPE_PATH, lambda rows: rows[0]["author_payload"].update({"request_id": "FORGED"})))
    add("traversal_binding", "E_RESPONSE_CROSS_BINDING", lambda temp: mutate_jsonl(temp / ENVELOPE_PATH, lambda rows: rows[0]["response_identity"].update({"binding_method": "TRAVERSAL_ORDER"})))
    add("partial_response", "E_ATOMIC_BATCH_COUNT", lambda temp: mutate_jsonl(temp / ENVELOPE_PATH, lambda rows: rows.pop()))
    add("partial_persistence_claim", "E_REPLAY_COUNTING", lambda temp: mutate_json(temp / PERSISTENCE_PATH, lambda row: row.update({"atomic_batch_persistence": False})))
    add("feedback_pollution", "E_FEEDBACK_POLLUTION", lambda temp: mutate_jsonl(temp / DISPATCH_PATH, lambda rows: rows[0].update({"no_content_feedback_carried_forward": False})))
    add("candidate_deleted_for_quality", "E_DEVELOPMENT_EVIDENCE_COUNT", lambda temp: mutate_jsonl(temp / CANDIDATE_PATH, lambda rows: rows.pop()))
    add("machine_finding_erased", "E_MACHINE_AGGREGATE", lambda temp: mutate_json(temp / MACHINE_PATH, lambda row: row.update({"invented_number_count": 0})))
    add("review_failure_erased", "E_REVIEW_FAILURE_STATE", lambda temp: mutate_json(temp / REVIEW_FAILURE_PATH, lambda row: row.update({"status": "PASS"})))
    add("false_review_complete", "E_FALSE_REVIEW_COMPLETION", lambda temp: mutate_json(temp / RESULT_PATH, lambda row: row["independent_review"].update({"quality_evaluation_completed": True})))
    add("unproven_score", "E_UNPROVEN_CONTENT_SCORE", lambda temp: mutate_json(temp / RESULT_PATH, lambda row: row["development_gate"].update({"first_acceptance_total": 40})))
    add("force_dev_pass", "E_FAILURE_NOT_RECORDED", lambda temp: mutate_json(temp / RESULT_PATH, lambda row: row.update({"dev_gate_pass": True})))
    add("blocking_cleared", "E_BLOCKING_ITEMS", lambda temp: mutate_json(temp / RESULT_PATH, lambda row: row.update({"blocking_items": []})))
    add("baseline_increase", "E_BOUNDARIES", lambda temp: mutate_json(temp / RESULT_PATH, lambda row: row["boundaries"].update({"accepted_baseline_count": 121})))
    add("hidden_created", "E_BOUNDARIES", lambda temp: mutate_json(temp / RESULT_PATH, lambda row: row["boundaries"].update({"hidden_count": 1})))
    add("qualified_flip", "E_BOUNDARIES", lambda temp: mutate_json(temp / RESULT_PATH, lambda row: row["boundaries"].update({"generator_qualified": True})))
    add("readiness_flip", "E_BOUNDARIES", lambda temp: mutate_json(temp / RESULT_PATH, lambda row: row["boundaries"].update({"runtime_ingest_ready": True})))
    add("guardian_hidden", "E_HIDDEN_ELIGIBILITY", lambda temp: mutate_json(temp / GUARDIAN_PATH, lambda row: row.update({"eligible_to_open_sealed_hidden": True})))
    add("horizon_from_max", "E_HORIZON_POLICY", lambda temp: mutate_yaml(temp / HORIZON_PATH, lambda row: row["ledger_horizon"].update({"derivation_source": "MAX_LEDGER_ROUTE"})))
    add("route35", "E_ROUTE35", lambda temp: (temp / LEDGER_PATH).write_text((temp / LEDGER_PATH).read_text(encoding="utf-8") + "  route_migration_35:\n    applied_by_task: UNAUTHORIZED\n", encoding="utf-8"))
    add("route33_tamper", "E_HISTORICAL_ROUTE_DIGEST", lambda temp: (temp / LEDGER_PATH).write_text((temp / LEDGER_PATH).read_text(encoding="utf-8").replace("      blocking_error_code: AUTHOR_RESPONSE_REQUEST_ID_MISMATCH", "      blocking_error_code: ERASED", 1), encoding="utf-8"))
    add("compat_third_checker", "E_COMPAT_SCOPE", lambda temp: mutate_json(temp / COMPAT_PATH, lambda row: row.update({"current_live_checker_modified_count": 3})))

    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="transport-replay34-checker-") as temporary:
        base = Path(temporary)
        for name, expected_code, mutation in tests:
            case_root = base / name
            copy_fixture(root, case_root)
            mutation(case_root)
            codes = {error["code"] for error in validate(case_root)}
            if expected_code not in codes:
                failures.append({"case": name, "expected": expected_code, "actual": sorted(codes)})
    if failures:
        print(json.dumps({"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "SELFTEST_PASS",
                "negative_case_count": len(tests),
                "request_order_invariance": True,
                "completion_order_invariance": True,
                "content_failure_retention_guard": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest(ROOT)
    errors = validate(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "governance_meaning": "HONEST_TRANSPORT_SUCCESS_AND_CONTENT_GATE_FAILURE",
                "physical_author_invocation_total": 80,
                "content_evaluable_response_count": 40,
                "candidate_count": 40,
                "dev_gate_pass": False,
                "hidden_count": 0,
                "accepted_baseline_count": 120,
                "generator_qualified": False,
                "authorized_terminal_route_id": 34,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
