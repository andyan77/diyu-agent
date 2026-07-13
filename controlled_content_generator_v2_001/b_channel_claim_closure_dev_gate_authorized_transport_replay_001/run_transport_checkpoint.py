#!/usr/bin/env python3
"""Materialize and verify the authorized replay transport checkpoint."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import logging
import random
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

_IMPORT_TASK_DIR = Path(__file__).resolve().parent
_IMPORT_ROOT = _IMPORT_TASK_DIR.parents[1]
if str(_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPORT_ROOT))

from controlled_content_generator_v2_001.b_channel_component_consumption_and_claim_closure_dev_gate_001.run_isolated_author_sessions import (  # noqa: E402
    _author_prompt,
)
from transport.dispatcher_owned_identity_adapter import (  # noqa: E402
    REPLAY_RUN_ID,
    TASK_ID,
    TransportIdentityError,
    build_dispatch_record,
    build_response_envelope,
    canonical_json,
    digest_object,
    validate_and_bind_batch,
    valid_stub_payload,
)


LOGGER = logging.getLogger(__name__)
TASK_DIR = Path(__file__).resolve().parent
ROOT = TASK_DIR.parents[1]
PRIOR_TASK = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001"
)
PRIOR_FREEZE = PRIOR_TASK / "freeze/commit_1_freeze_manifest.v0.1.json"
PRIOR_REQUESTS = PRIOR_TASK / "requests/author_requests.v0.1.jsonl"
PRIOR_FAILURE_RECEIPT = PRIOR_TASK / "author/author_session_failure_receipt.v0.1.json"
PRIOR_RESULT = PRIOR_TASK / "result/development_gate_result.v0.1.json"
PRIOR_GUARDIAN = PRIOR_TASK / "guardian/guardian_review_packet.v0.1.json"
OLD_RUNNER = PRIOR_TASK / "run_isolated_author_sessions.py"
AUTHOR_PROTOCOL = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/"
    "core/creative_author_protocol.v0.1.yaml"
)
AUTHOR_SCHEMA = AUTHOR_PROTOCOL.with_name("creative_author_response.schema.json")
AUTHOR_INSTRUCTION = AUTHOR_PROTOCOL.with_name("creative_author_instruction.v0.1.yaml")
OUTPUT_PATHS = (
    Path("phase_0/pr12_merge_receipt.v0.1.json"),
    Path("transport/transport_root_cause_analysis.v0.1.yaml"),
    Path("transport/transport_identity_contract.v0.1.json"),
    Path("transport/author_payload.schema.json"),
    Path("transport/active_transport_pointer.v0.1.json"),
    Path("t0/transport_t0_cases.v0.1.jsonl"),
    Path("t0/transport_t0_results.v0.1.jsonl"),
    Path("t0/transport_t0_result.v0.1.json"),
    Path("replay/authorized_replay_manifest.v0.1.json"),
    Path("replay/replay_dispatch_manifest.v0.1.jsonl"),
    Path("replay/replay_author_requests.v0.1.jsonl"),
)
TRANSPORT_CORE_PATHS = (
    Path(
        "controlled_content_generator_v2_001/"
        "b_channel_claim_closure_dev_gate_authorized_transport_replay_001/"
        "transport/dispatcher_owned_identity_adapter.py"
    ),
    Path(
        "controlled_content_generator_v2_001/"
        "b_channel_claim_closure_dev_gate_authorized_transport_replay_001/"
        "run_transport_checkpoint.py"
    ),
    Path(
        "controlled_content_generator_v2_001/"
        "b_channel_claim_closure_dev_gate_authorized_transport_replay_001/"
        "run_authorized_transport_replay.py"
    ),
)
EXPECTED_PRIOR_EVIDENCE_SHA256 = {
    PRIOR_FAILURE_RECEIPT: "6f2ef75aa610fd1da333d67624e19c7be978967587c4b342bb572cbdbc096393",
    PRIOR_RESULT: "ff00145cf747f50760e25d1b8fb6a6353cdd3c8255c0f1302609eafd14da9ee6",
    PRIOR_GUARDIAN: "c6c27641e59a2b11b97ec95e31a892855797ef7049b3413dda3f38d12a2f9fae",
}


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


def write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _with_digest(value: dict[str, Any], field: str) -> dict[str, Any]:
    value[field] = digest_object(value)
    return value


def _phase_0_receipt() -> dict[str, Any]:
    return _with_digest(
        {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "pull_request_number": 12,
            "reviewed_base_sha": "76b057d811cbafecf5b2aaa0b5e0fda03ae4033d",
            "reviewed_head_sha": "e0f004e403a1947691178d42c0a33e32f0ecd767",
            "reviewed_head_tree": "138f49b10220a0010bc15f75234b2d542b185922",
            "reviewed_diff_digest": "84fe6fa93efe09af5bf48ec4c9a1cd8a580125e3823e0cb2974796c8d2815e7e",
            "reviewed_diff_path_digest": "16fb3afc9ea0aff1833b46fe290de87e62b5683f3e9085d054b4cd1a93bb5c1c",
            "merge_commit_sha": "f5e458730aca52e63748f597e007352b72d7bb63",
            "merge_parent_shas": [
                "76b057d811cbafecf5b2aaa0b5e0fda03ae4033d",
                "e0f004e403a1947691178d42c0a33e32f0ecd767",
            ],
            "merge_tree": "138f49b10220a0010bc15f75234b2d542b185922",
            "merge_method": "merge_commit",
            "expected_head_oid_lock_used": True,
            "admin_bypass_used": False,
            "source_branch_deleted": False,
            "master_ci_run_id": 29228408541,
            "checker_compatibility": "SUCCESS",
            "secret_scan": "SUCCESS",
            "branch_protection_unchanged": True,
            "merge_semantics": {
                "component_consumption_structural_pass": True,
                "orch_plan_structural_pass": True,
                "route_regression_pass": True,
                "dev_content_result": "NONE_UNTESTED",
                "author_transport_result": "ATOMIC_STOP_BEFORE_PERSISTENCE",
                "generator_qualified": False,
                "hidden_count": 0,
                "accepted_baseline_count": 120,
            },
        },
        "receipt_digest",
    )


def _root_cause_report() -> dict[str, Any]:
    return {
        "transport_root_cause_analysis": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "transport_root_cause_confirmed": True,
            "root_cause_class": "AUTHOR_PAYLOAD_ECHO_USED_AS_AUTHORITATIVE_TRANSPORT_IDENTITY",
            "request_id_generation_owner_before": (
                "generator_plan_consumer.build_author_request generated request_id once"
            ),
            "dispatch_manifest_path_before": PRIOR_REQUESTS.as_posix(),
            "author_session_binding_before": (
                "ThreadPool future captured one request and wrote it into a unique temporary session directory"
            ),
            "response_return_path_before": (
                "one final_response.json inside that request-scoped temporary directory"
            ),
            "pairing_mechanism_before": (
                "request object was passed directly to _run_one; traversal, filename, and completion order did not assign identity"
            ),
            "author_payload_identity_authority_before": True,
            "schema_required_author_echo_fields_before": [
                "request_id",
                "request_digest",
                "response_id",
            ],
            "mismatch_observation": (
                "old _validate_response rejected at least one author payload whose request_id did not equal the captured request"
            ),
            "mismatch_stage": "AUTHOR_PAYLOAD_ECHO_BEFORE_PERSISTENCE",
            "adapter_projection_fault_found": False,
            "persistence_envelope_fault_found": False,
            "traversal_order_pairing_found": False,
            "filename_order_pairing_found": False,
            "completion_order_pairing_found": False,
            "duplicate_frozen_request_id_count": 0,
            "a_b_request_content_crossing_found": False,
            "stale_response_possible_in_old_temp_layout": False,
            "why_all_responses_were_unpersisted": (
                "writes occurred only after all futures succeeded; one exception unwound the temporary batch before either output file was written"
            ),
            "initial_persisted_raw_response_count": 0,
            "initial_candidate_count": 0,
            "initial_semantic_review_count": 0,
            "initial_quality_feedback_count": 0,
            "scope_confirmed_identity_only": True,
            "material_plan_component_fc_or_author_semantic_error_found": False,
            "repair_decision": (
                "author emits content payload only; dispatcher writes request/session/assignment/response identity envelope"
            ),
        }
    }


def _identity_contract() -> dict[str, Any]:
    return _with_digest(
        {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "authority": "DISPATCHER_OWNED_IDENTITY",
            "binding_key": "parent_request_id",
            "forbidden_binding_sources": [
                "author_payload_identity",
                "traversal_order",
                "filename_order",
                "completion_order",
                "array_index",
            ],
            "dispatch_identity_required_fields": [
                "run_id",
                "assignment_id",
                "lane_id",
                "plan_id",
                "plan_digest",
                "request_id",
                "session_id",
                "dispatch_manifest_digest",
            ],
            "response_identity_required_fields": [
                "response_id",
                "parent_run_id",
                "parent_assignment_id",
                "parent_lane_id",
                "parent_request_id",
                "parent_session_id",
                "payload_digest",
                "received_at_sequence",
                "transport_binding_digest",
            ],
            "one_request_one_response": True,
            "one_response_one_request": True,
            "atomic_batch_persistence": True,
            "author_identity_write_allowed": False,
            "diagnostic_echo_policy": "ABSENT_BY_CLOSED_SCHEMA",
            "third_attempt_allowed": False,
            "content_failure_is_transport_failure": False,
        },
        "contract_digest",
    )


def _payload_schema() -> dict[str, Any]:
    frozen = load_json(ROOT / AUTHOR_SCHEMA)
    properties = copy.deepcopy(frozen["properties"])
    required = list(frozen["required"])
    for field in ("request_id", "request_digest", "response_id"):
        properties.pop(field)
        required.remove(field)
    for value in properties.values():
        if isinstance(value, dict) and "const" in value and "type" not in value:
            value["type"] = "boolean" if isinstance(value["const"], bool) else "string"
    return {
        "$schema": frozen["$schema"],
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _active_pointer() -> dict[str, Any]:
    return _with_digest(
        {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "active_transport_entry_count": 1,
            "entries": [
                {
                    "entry_id": "AUTHOR-TRANSPORT-DEV33-HISTORICAL",
                    "path": OLD_RUNNER.as_posix(),
                    "status": "historical_non_active",
                    "may_be_invoked_by_current_replay": False,
                },
                {
                    "entry_id": "AUTHOR-TRANSPORT-REPLAY34-ACTIVE",
                    "path": TRANSPORT_CORE_PATHS[0].as_posix(),
                    "runner_path": TRANSPORT_CORE_PATHS[2].as_posix(),
                    "status": "active",
                    "may_be_invoked_by_current_replay": True,
                    "identity_authority": "DISPATCHER",
                    "semantic_author_instruction_changed": False,
                },
            ],
            "parallel_dispatcher_created_count": 0,
            "runtime_equivalence_claim": False,
        },
        "pointer_digest",
    )


def _refresh_dispatch(dispatch: dict[str, Any]) -> None:
    identity = dispatch["dispatch_identity"]
    identity.pop("dispatch_manifest_digest", None)
    identity["dispatch_manifest_digest"] = digest_object(identity)
    replay = dispatch["replay_request"]
    replay.pop("request_digest", None)
    replay["request_digest"] = digest_object(replay)
    dispatch["semantic_payload_digest"] = digest_object(
        {key: value for key, value in replay.items() if key not in {"task_id", "request_id", "request_digest"}}
    )
    dispatch.pop("dispatch_record_digest", None)
    dispatch["dispatch_record_digest"] = digest_object(dispatch)


def _refresh_envelope(envelope: dict[str, Any], dispatch: Mapping[str, Any]) -> None:
    identity = envelope["response_identity"]
    payload = envelope.get("author_payload")
    if isinstance(payload, Mapping):
        identity["payload_digest"] = digest_object(payload)
    identity.pop("transport_binding_digest", None)
    identity["transport_binding_digest"] = digest_object(
        {
            **identity,
            "dispatch_manifest_digest": dispatch["dispatch_identity"]["dispatch_manifest_digest"],
        }
    )
    envelope.pop("response_envelope_digest", None)
    envelope["response_envelope_digest"] = digest_object(envelope)


def _observe(
    dispatches: Sequence[Mapping[str, Any]], envelopes: Sequence[Mapping[str, Any]]
) -> str:
    try:
        validate_and_bind_batch(dispatches, envelopes)
    except TransportIdentityError as exc:
        return exc.code
    return "PASS"


def _eligibility_code(**overrides: Any) -> str:
    values = {
        "initial_raw": 0,
        "initial_candidate": 0,
        "initial_feedback": 0,
        "prior_failure_recorded": True,
        "replay_request_count": 40,
        "replacement_count": 0,
        "third_attempt": False,
        "temporary_residual_count": 0,
        "transport_valid_count": 40,
        "persisted_count": 40,
        "content_failure_count": 0,
        "semantic_asset_drift_count": 0,
    }
    values.update(overrides)
    if values["initial_raw"]:
        return "E_INITIAL_RAW_RESPONSE_PRESENT"
    if values["initial_candidate"]:
        return "E_INITIAL_CANDIDATE_PRESENT"
    if values["initial_feedback"]:
        return "E_INITIAL_QUALITY_FEEDBACK_PRESENT"
    if values["prior_failure_recorded"] is not True:
        return "E_PRIOR_FAILURE_NOT_RECORDED"
    if values["replay_request_count"] != 40:
        return "E_SELECTIVE_REPLAY"
    if values["replacement_count"]:
        return "E_REPLACEMENT_ASSIGNMENT"
    if values["third_attempt"]:
        return "E_THIRD_ATTEMPT_FORBIDDEN"
    if values["temporary_residual_count"]:
        return "E_TEMPORARY_RESPONSE_RESIDUAL"
    if values["semantic_asset_drift_count"]:
        return "E_SEMANTIC_ASSET_DRIFT"
    if values["transport_valid_count"] != 40 and values["persisted_count"]:
        return "E_PARTIAL_BATCH_PERSISTENCE"
    if values["transport_valid_count"] == 40 and values["content_failure_count"] and values["persisted_count"] != 40:
        return "E_CONTENT_FAILURE_MISCLASSIFIED_AS_TRANSPORT"
    return "PASS"


def _t0_rows(
    dispatches: list[dict[str, Any]], envelopes: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    baseline = validate_and_bind_batch(dispatches, envelopes)

    def add_positive(case_id: str, ordered: list[dict[str, Any]]) -> None:
        observed = _observe(dispatches, ordered)
        cases.append({"case_id": case_id, "class": "POSITIVE", "expected": "PASS"})
        results.append({"case_id": case_id, "expected": "PASS", "observed": observed})

    add_positive("T0-P-ORIGINAL-ORDER", list(envelopes))
    add_positive("T0-P-REVERSE-ORDER", list(reversed(envelopes)))
    for seed in (7, 19, 34):
        shuffled = list(envelopes)
        random.Random(seed).shuffle(shuffled)
        add_positive(f"T0-P-SHUFFLE-{seed}", shuffled)
    lane_interleaved = sorted(
        envelopes,
        key=lambda row: (
            str(row["response_identity"]["parent_lane_id"]),
            str(row["response_identity"]["parent_assignment_id"]),
        ),
        reverse=True,
    )
    add_positive("T0-P-A-B-INTERLEAVED", lane_interleaved)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(copy.deepcopy, row) for row in reversed(envelopes)]
        concurrent_order = [future.result() for future in concurrent.futures.as_completed(futures)]
    add_positive("T0-P-CONCURRENT-COMPLETION", concurrent_order)
    add_positive("T0-P-REPEATED-RUN-BYTE-IDENTITY", list(envelopes))

    def add_negative(case_id: str, expected: str, observed: str) -> None:
        cases.append({"case_id": case_id, "class": "NEGATIVE", "expected": expected})
        results.append({"case_id": case_id, "expected": expected, "observed": observed})

    def mutated() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return copy.deepcopy(dispatches), copy.deepcopy(envelopes)

    d, e = mutated()
    d[0]["dispatch_identity"]["request_id"] = ""
    d[0]["replay_request"]["request_id"] = ""
    _refresh_dispatch(d[0])
    add_negative("T0-N-MISSING-REQUEST-ID", "E_REQUEST_ID_MISSING", _observe(d, e))

    d, e = mutated()
    e[0]["response_identity"]["parent_request_id"] = "UNKNOWN-REQUEST"
    _refresh_envelope(e[0], d[0])
    add_negative("T0-N-WRONG-REQUEST-ID", "E_RESPONSE_REQUEST_ID_MISMATCH", _observe(d, e))

    d, e = mutated()
    duplicate_request = d[0]["dispatch_identity"]["request_id"]
    d[1]["dispatch_identity"]["request_id"] = duplicate_request
    d[1]["replay_request"]["request_id"] = duplicate_request
    _refresh_dispatch(d[1])
    add_negative("T0-N-DUPLICATE-REQUEST-ID", "E_DUPLICATE_REQUEST_ID", _observe(d, e))

    d, e = mutated()
    e[1]["response_identity"]["response_id"] = e[0]["response_identity"]["response_id"]
    _refresh_envelope(e[1], d[1])
    add_negative("T0-N-DUPLICATE-RESPONSE-ID", "E_DUPLICATE_RESPONSE_ID", _observe(d, e))

    for case_id, field, expected in (
        ("T0-N-A-B-RESPONSE-EXCHANGE", "parent_lane_id", "E_CROSS_LANE_BINDING"),
        ("T0-N-ASSIGNMENT-EXCHANGE", "parent_assignment_id", "E_RESPONSE_ASSIGNMENT_MISMATCH"),
        ("T0-N-SESSION-EXCHANGE", "parent_session_id", "E_RESPONSE_SESSION_MISMATCH"),
    ):
        d, e = mutated()
        e[0]["response_identity"][field] = e[1]["response_identity"][field]
        _refresh_envelope(e[0], d[0])
        add_negative(case_id, expected, _observe(d, e))

    d, e = mutated()
    e[0]["response_identity"]["parent_request_id"] = [
        d[0]["dispatch_identity"]["request_id"],
        d[1]["dispatch_identity"]["request_id"],
    ]
    _refresh_envelope(e[0], d[0])
    add_negative(
        "T0-N-ONE-RESPONSE-TWO-REQUESTS",
        "E_RESPONSE_BINDS_MULTIPLE_REQUESTS",
        _observe(d, e),
    )

    d, e = mutated()
    for field in (
        "parent_request_id",
        "parent_assignment_id",
        "parent_lane_id",
        "parent_session_id",
        "parent_run_id",
    ):
        source_field = field.removeprefix("parent_")
        e[1]["response_identity"][field] = d[0]["dispatch_identity"][source_field]
    _refresh_envelope(e[1], d[0])
    add_negative(
        "T0-N-ONE-REQUEST-TWO-RESPONSES",
        "E_REQUEST_ACCEPTS_MULTIPLE_RESPONSES",
        _observe(d, e),
    )

    d, e = mutated()
    e[0]["response_identity"]["parent_run_id"] = "STALE-RUN"
    _refresh_envelope(e[0], d[0])
    add_negative("T0-N-STALE-RUN", "E_STALE_RUN_RESPONSE", _observe(d, e))

    d, e = mutated()
    e[0]["response_identity"]["old_response_replay"] = True
    _refresh_envelope(e[0], d[0])
    add_negative("T0-N-OLD-RESPONSE-REPLAY", "E_OLD_RESPONSE_REPLAY", _observe(d, e))

    d, e = mutated()
    e[0]["author_payload"]["request_id"] = d[0]["dispatch_identity"]["request_id"]
    _refresh_envelope(e[0], d[0])
    add_negative(
        "T0-N-AUTHOR-PAYLOAD-FORGED-IDENTITY",
        "E_AUTHOR_PAYLOAD_IDENTITY_FORBIDDEN",
        _observe(d, e),
    )

    for case_id, method, expected in (
        ("T0-N-TRAVERSAL-ORDER-BINDING", "TRAVERSAL_ORDER", "E_TRAVERSAL_ORDER_BINDING_FORBIDDEN"),
        ("T0-N-FILENAME-ORDER-BINDING", "FILENAME_ORDER", "E_FILENAME_ORDER_BINDING_FORBIDDEN"),
    ):
        d, e = mutated()
        e[0]["response_identity"]["binding_method"] = method
        _refresh_envelope(e[0], d[0])
        add_negative(case_id, expected, _observe(d, e))

    d, e = mutated()
    e[0]["author_payload"] = {"backend_class": "CONTROLLED_EXECUTION_AGENT"}
    _refresh_envelope(e[0], d[0])
    add_negative("T0-N-PARTIAL-RESPONSE", "E_AUTHOR_PAYLOAD_FIELDS", _observe(d, e))

    policy_cases = (
        ("T0-N-TEMP-FILE-RESIDUAL", "E_TEMPORARY_RESPONSE_RESIDUAL", {"temporary_residual_count": 1}),
        ("T0-N-PRIOR-FAILURE-NOT-RECORDED", "E_PRIOR_FAILURE_NOT_RECORDED", {"prior_failure_recorded": False}),
        ("T0-N-SELECTIVE-REPLAY", "E_SELECTIVE_REPLAY", {"replay_request_count": 39}),
        ("T0-N-REPLACEMENT-ASSIGNMENT", "E_REPLACEMENT_ASSIGNMENT", {"replacement_count": 1}),
        ("T0-N-THIRD-ATTEMPT", "E_THIRD_ATTEMPT_FORBIDDEN", {"third_attempt": True}),
        ("T0-N-MATERIAL-OR-PLAN-DRIFT", "E_SEMANTIC_ASSET_DRIFT", {"semantic_asset_drift_count": 1}),
        ("T0-N-INITIAL-RAW-PRESENT", "E_INITIAL_RAW_RESPONSE_PRESENT", {"initial_raw": 1}),
        ("T0-N-INITIAL-CANDIDATE-PRESENT", "E_INITIAL_CANDIDATE_PRESENT", {"initial_candidate": 1}),
        ("T0-N-INITIAL-FEEDBACK-PRESENT", "E_INITIAL_QUALITY_FEEDBACK_PRESENT", {"initial_feedback": 1}),
        (
            "T0-N-PERSIST-39-AFTER-TRANSPORT-FAIL",
            "E_PARTIAL_BATCH_PERSISTENCE",
            {"transport_valid_count": 39, "persisted_count": 39},
        ),
        (
            "T0-N-CONTENT-FAIL-AS-TRANSPORT",
            "E_CONTENT_FAILURE_MISCLASSIFIED_AS_TRANSPORT",
            {"content_failure_count": 1, "persisted_count": 39},
        ),
    )
    for case_id, expected, kwargs in policy_cases:
        add_negative(case_id, expected, _eligibility_code(**kwargs))

    baseline_digest = hashlib.sha256(
        "".join(canonical_json(row) + "\n" for row in baseline).encode("utf-8")
    ).hexdigest()
    repeated_digest = hashlib.sha256(
        "".join(
            canonical_json(row) + "\n"
            for row in validate_and_bind_batch(dispatches, list(reversed(envelopes)))
        ).encode("utf-8")
    ).hexdigest()
    result = _with_digest(
        {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "status": "PASS" if all(row["expected"] == row["observed"] for row in results) else "FAIL",
            "stub_request_count": 40,
            "valid_binding_count": 40,
            "positive_case_count": sum(row["class"] == "POSITIVE" for row in cases),
            "negative_case_count": sum(row["class"] == "NEGATIVE" for row in cases),
            "request_response_binding_mismatch_count": 0,
            "duplicate_request_id_count": 0,
            "duplicate_response_id_count": 0,
            "cross_assignment_binding_count": 0,
            "cross_lane_binding_count": 0,
            "completion_order_invariance": True,
            "request_order_invariance": True,
            "repeated_run_byte_identity": baseline_digest == repeated_digest,
            "transport_root_cause_confirmed": True,
            "transport_fix_scope_is_identity_only": True,
            "semantic_core_unchanged": True,
            "transport_positive_tests_pass": all(
                row["observed"] == "PASS" for row in results if row["case_id"].startswith("T0-P-")
            ),
            "transport_negative_tests_pass": all(
                row["observed"] == row["expected"]
                for row in results
                if row["case_id"].startswith("T0-N-")
            ),
            "python_O_fail_closed": True,
            "real_author_replay_count": 0,
        },
        "t0_result_digest",
    )
    return cases, results, result


def _prior_frozen_digests() -> dict[str, str]:
    freeze = load_json(ROOT / PRIOR_FREEZE)
    digests: dict[str, str] = {}
    for relative, expected in freeze["generated_file_digests"].items():
        path = PRIOR_TASK / relative
        if sha256_file(ROOT / path) != expected:
            raise ValueError(f"prior generated asset drift: {path}")
        digests[path.as_posix()] = expected
    for group in ("core_file_digests", "input_file_digests"):
        for relative, expected in freeze[group].items():
            path = Path(relative)
            if sha256_file(ROOT / path) != expected:
                raise ValueError(f"prior frozen asset drift: {path}")
            digests[path.as_posix()] = expected
    for path, expected in EXPECTED_PRIOR_EVIDENCE_SHA256.items():
        if sha256_file(ROOT / path) != expected:
            raise ValueError(f"prior failure evidence drift: {path}")
        digests[path.as_posix()] = expected
    return dict(sorted(digests.items()))


def _replay_manifest(dispatches: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _with_digest(
        {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "prior_failed_run_id": "DEV33-ISOLATED-AUTHOR-BATCH-001",
            "new_replay_run_id": REPLAY_RUN_ID,
            "initial_author_invocation_count": 40,
            "initial_transport_valid_response_count": 0,
            "initial_persisted_raw_response_count": 0,
            "initial_candidate_count": 0,
            "initial_semantic_review_count": 0,
            "initial_quality_feedback_count": 0,
            "authorized_transport_batch_replay_count": 1,
            "authorized_transport_request_replay_count": 40,
            "physical_author_invocation_total_after_replay": 80,
            "content_evaluable_attempt_count_per_assignment": 1,
            "content_reroll_count": 0,
            "replacement_count": 0,
            "selective_retry_count": 0,
            "third_attempt_allowed": False,
            "first_acceptance_transport_exception_applied": True,
            "first_acceptance_means_first_physical_invocation": False,
            "first_acceptance_definition": (
                "first transport-valid persisted response per assignment is zero-edit directly usable"
            ),
            "exception_scope": "THIS_BATCH_ONLY_NON_PRECEDENT",
            "assignment_count": len(dispatches),
            "no_content_feedback_carried_forward_count": sum(
                row["no_content_feedback_carried_forward"] is True for row in dispatches
            ),
        },
        "manifest_digest",
    )


def _write_prepare(output_dir: Path) -> None:
    prior_requests = sorted(
        load_jsonl(ROOT / PRIOR_REQUESTS), key=lambda row: str(row["assignment_id"])
    )
    if len(prior_requests) != 40:
        raise ValueError("exactly 40 prior frozen requests required")
    dispatches = [
        build_dispatch_record(request, sequence=index)
        for index, request in enumerate(prior_requests, start=1)
    ]
    stub = valid_stub_payload()
    envelopes = [
        build_response_envelope(
            dispatch,
            stub,
            received_at_sequence=int(dispatch["dispatch_identity"]["dispatch_sequence"]),
        )
        for dispatch in dispatches
    ]
    cases, results, t0_result = _t0_rows(dispatches, envelopes)
    if t0_result["status"] != "PASS":
        raise ValueError("transport checkpoint T0 failed")
    outputs: dict[Path, Any] = {
        OUTPUT_PATHS[0]: _phase_0_receipt(),
        OUTPUT_PATHS[1]: _root_cause_report(),
        OUTPUT_PATHS[2]: _identity_contract(),
        OUTPUT_PATHS[3]: _payload_schema(),
        OUTPUT_PATHS[4]: _active_pointer(),
        OUTPUT_PATHS[5]: cases,
        OUTPUT_PATHS[6]: results,
        OUTPUT_PATHS[7]: t0_result,
        OUTPUT_PATHS[8]: _replay_manifest(dispatches),
        OUTPUT_PATHS[9]: dispatches,
        OUTPUT_PATHS[10]: [dict(row["replay_request"]) for row in dispatches],
    }
    for relative, value in outputs.items():
        target = output_dir / relative
        if relative.suffix == ".jsonl":
            write_jsonl(target, value)
        elif relative.suffix == ".yaml":
            write_yaml(target, value)
        else:
            write_json(target, value)
    prior_frozen = _prior_frozen_digests()
    transport_core = {
        path.as_posix(): sha256_file(ROOT / path) for path in TRANSPORT_CORE_PATHS
    }
    generated = {path.as_posix(): sha256_file(output_dir / path) for path in OUTPUT_PATHS}
    prior_requests_payload = load_jsonl(ROOT / PRIOR_REQUESTS)
    instruction_digest = digest_object(
        {
            "request_authoring_instruction_values": sorted(
                {str(row["authoring_instruction"]) for row in prior_requests_payload}
            ),
            "author_protocol_sha256": sha256_file(ROOT / AUTHOR_PROTOCOL),
            "author_instruction_sha256": sha256_file(ROOT / AUTHOR_INSTRUCTION),
        }
    )
    freeze = _with_digest(
        {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "freeze_phase": "TRANSPORT_CHECKPOINT_T0_PRE_REAL_AUTHOR_REPLAY",
            "frozen_before_real_author_replay": True,
            "prior_frozen_file_digests": prior_frozen,
            "transport_core_file_digests": transport_core,
            "generated_file_digests": generated,
            "material_digest": sha256_file(
                ROOT / PRIOR_TASK / "materials/development_material_packs.v0.1.jsonl"
            ),
            "assignment_digest": sha256_file(
                ROOT / PRIOR_TASK / "assignments/development_assignments.v0.1.jsonl"
            ),
            "plan_digest": sha256_file(
                ROOT / PRIOR_TASK / "orch/orch_composition_plans.v0.1.jsonl"
            ),
            "source_snapshot_digest": sha256_file(
                ROOT / PRIOR_TASK / "inputs/development_material_source.v0.1.json"
            ),
            "authorization_digest": digest_object(
                [row["authorization"] for row in prior_requests_payload]
            ),
            "semantic_author_instruction_digest": instruction_digest,
            "author_runtime_prompt_sha256": hashlib.sha256(
                _author_prompt().encode("utf-8")
            ).hexdigest(),
            "component_registry_digest": sha256_file(
                ROOT
                / "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
                "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
                "reviewed_reusable_component_registry.v0.4.jsonl"
            ),
            "route_gate_digest": digest_object(
                {
                    "inputs": sha256_file(
                        ROOT
                        / "controlled_content_generator_v2_001/"
                        "creative_authoring_route_oracle_convergence_001/route/route_inputs.v0.1.jsonl"
                    ),
                    "expectations": sha256_file(
                        ROOT
                        / "controlled_content_generator_v2_001/"
                        "creative_authoring_route_oracle_convergence_001/route/"
                        "sealed_route_expectations.v0.1.jsonl"
                    ),
                }
            ),
            "material_digest_unchanged": True,
            "assignment_digest_unchanged": True,
            "plan_digest_unchanged": True,
            "source_snapshot_digest_unchanged": True,
            "authorization_digest_unchanged": True,
            "semantic_author_instruction_digest_unchanged": True,
            "component_registry_digest_unchanged": True,
            "route_gate_digest_unchanged": True,
            "real_author_replay_count": 0,
            "hidden_count": 0,
            "accepted_baseline_count": 120,
            "generator_qualified": False,
        },
        "freeze_manifest_digest",
    )
    write_json(output_dir / "freeze/transport_freeze_manifest.v0.1.json", freeze)


def _check_prepare() -> None:
    with tempfile.TemporaryDirectory(prefix="transport34-t0-check-") as temp_dir:
        rebuilt = Path(temp_dir)
        _write_prepare(rebuilt)
        for relative in (*OUTPUT_PATHS, Path("freeze/transport_freeze_manifest.v0.1.json")):
            live = TASK_DIR / relative
            candidate = rebuilt / relative
            if not live.exists() or live.read_bytes() != candidate.read_bytes():
                raise ValueError(f"transport checkpoint drift: {relative}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if __debug__ is False:
        return 2
    if args.check:
        _check_prepare()
        LOGGER.info("transport checkpoint T0 CHECK_PASS")
    else:
        _write_prepare(TASK_DIR)
        LOGGER.info("transport checkpoint T0 MATERIALIZED")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        raise SystemExit(main())
    except Exception as exc:
        LOGGER.error("E_TRANSPORT_CHECKPOINT_T0: %s", exc)
        raise SystemExit(1) from exc
