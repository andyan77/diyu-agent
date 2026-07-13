#!/usr/bin/env python3
"""Bind author payloads to dispatcher-owned replay identities."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn


TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_CLAIM_CLOSURE_DEV_GATE_AUTHORIZED_TRANSPORT_REPLAY_001"
REPLAY_RUN_ID = "AUTHORIZED-TRANSPORT-REPLAY-34-RUN-001"
AUTHORITY_FIELDS = frozenset(
    {
        "request_id",
        "request_digest",
        "response_id",
        "session_id",
        "assignment_id",
        "plan_id",
        "run_id",
        "dispatch_manifest_digest",
        "transport_binding_digest",
    }
)
SEMANTIC_EXCLUDED_FIELDS = frozenset({"task_id", "request_id", "request_digest"})
SURFACE_FIELDS = frozenset(
    {
        "title",
        "body_blocks",
        "spoken_lines",
        "CTA",
        "visual_beats",
        "capture_instructions",
        "audio_grammar",
        "editing_grammar",
    }
)
PAYLOAD_FIELDS = frozenset(
    {
        "backend_class",
        "one_request_one_response",
        "paired_output_visible",
        "review_envelope_visible",
        "expected_score_visible",
        "chain_of_thought_stored",
        "surfaces",
        "surface_bindings",
        "style_realization_evidence",
        "required_obligation_evidence",
    }
)


class TransportIdentityError(ValueError):
    """Fail-closed transport identity error with a stable code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _fail(code: str, detail: str) -> NoReturn:
    raise TransportIdentityError(code, detail)


def semantic_request_payload(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return the author-visible semantic payload without transport identity metadata."""

    return {
        str(key): value
        for key, value in request.items()
        if str(key) not in SEMANTIC_EXCLUDED_FIELDS
    }


def semantic_request_digest(request: Mapping[str, Any]) -> str:
    return digest_object(semantic_request_payload(request))


def build_dispatch_record(
    prior_request: Mapping[str, Any],
    *,
    sequence: int,
    run_id: str = REPLAY_RUN_ID,
) -> dict[str, Any]:
    """Create one replay request and its dispatcher-owned identity."""

    assignment_id = str(prior_request.get("assignment_id", ""))
    lane_id = str(prior_request.get("lane_id", ""))
    plan_id = str(prior_request.get("plan_id", ""))
    plan_digest = str(prior_request.get("plan_digest", ""))
    prior_request_id = str(prior_request.get("request_id", ""))
    prior_request_digest = str(prior_request.get("request_digest", ""))
    if not all((assignment_id, lane_id, plan_id, plan_digest, prior_request_id)):
        _fail("E_DISPATCH_SOURCE_INCOMPLETE", assignment_id or "missing assignment")
    request_id = f"AUTHOR-REPLAY34-{assignment_id}-REQUEST"
    session_id = f"AUTHOR-REPLAY34-{assignment_id}-SESSION"
    response_id = f"AUTHOR-REPLAY34-{assignment_id}-RESPONSE"
    replay_request = dict(prior_request)
    replay_request["task_id"] = TASK_ID
    replay_request["request_id"] = request_id
    replay_request.pop("request_digest", None)
    replay_request["request_digest"] = digest_object(replay_request)
    prior_semantic_digest = semantic_request_digest(prior_request)
    replay_semantic_digest = semantic_request_digest(replay_request)
    if prior_semantic_digest != replay_semantic_digest:
        _fail("E_SEMANTIC_PAYLOAD_DRIFT", assignment_id)
    dispatch_identity: dict[str, Any] = {
        "run_id": run_id,
        "assignment_id": assignment_id,
        "lane_id": lane_id,
        "plan_id": plan_id,
        "plan_digest": plan_digest,
        "request_id": request_id,
        "session_id": session_id,
        "dispatch_sequence": sequence,
        "binding_method": "PARENT_REQUEST_ID",
    }
    dispatch_identity["dispatch_manifest_digest"] = digest_object(dispatch_identity)
    record: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "dispatch_identity": dispatch_identity,
        "expected_response_id": response_id,
        "prior_failed_request_id": prior_request_id,
        "prior_failed_request_digest": prior_request_digest,
        "replay_request": replay_request,
        "semantic_payload_digest": replay_semantic_digest,
        "no_content_feedback_carried_forward": True,
        "content_evaluable_attempt_ordinal": 1,
        "physical_invocation_ordinal": 2,
    }
    record["dispatch_record_digest"] = digest_object(record)
    return record


def validate_author_payload(payload: Mapping[str, Any]) -> None:
    """Validate content shape while rejecting any author-owned identity authority."""

    forbidden = sorted(AUTHORITY_FIELDS.intersection(map(str, payload)))
    if forbidden:
        _fail("E_AUTHOR_PAYLOAD_IDENTITY_FORBIDDEN", ",".join(forbidden))
    fields = set(map(str, payload))
    if fields != PAYLOAD_FIELDS:
        _fail("E_AUTHOR_PAYLOAD_FIELDS", f"fields={sorted(fields)}")
    fixed_values = {
        "backend_class": "CONTROLLED_EXECUTION_AGENT",
        "one_request_one_response": True,
        "paired_output_visible": False,
        "review_envelope_visible": False,
        "expected_score_visible": False,
        "chain_of_thought_stored": False,
    }
    for field, expected in fixed_values.items():
        if payload.get(field) != expected:
            _fail("E_AUTHOR_PAYLOAD_BOUNDARY", field)
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, Mapping) or set(map(str, surfaces)) != SURFACE_FIELDS:
        _fail("E_AUTHOR_PAYLOAD_SURFACES", "closed surface schema required")
    list_surfaces = (
        "body_blocks",
        "spoken_lines",
        "visual_beats",
        "capture_instructions",
    )
    string_surfaces = ("title", "CTA", "audio_grammar", "editing_grammar")
    if any(
        not isinstance(surfaces.get(field), list)
        or any(not isinstance(item, str) for item in surfaces.get(field, []))
        for field in list_surfaces
    ):
        _fail("E_AUTHOR_PAYLOAD_SURFACE_TYPE", "array surface")
    if any(not isinstance(surfaces.get(field), str) for field in string_surfaces):
        _fail("E_AUTHOR_PAYLOAD_SURFACE_TYPE", "string surface")
    for field in (
        "surface_bindings",
        "style_realization_evidence",
        "required_obligation_evidence",
    ):
        if not isinstance(payload.get(field), list):
            _fail("E_AUTHOR_PAYLOAD_COLLECTION_TYPE", field)


def build_response_envelope(
    dispatch: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    received_at_sequence: int,
) -> dict[str, Any]:
    """Wrap one author payload in a transport-owned response envelope."""

    validate_author_payload(payload)
    identity = dispatch.get("dispatch_identity")
    if not isinstance(identity, Mapping):
        _fail("E_DISPATCH_IDENTITY_MISSING", "dispatch_identity")
    response_identity: dict[str, Any] = {
        "response_id": str(dispatch.get("expected_response_id", "")),
        "parent_run_id": str(identity.get("run_id", "")),
        "parent_assignment_id": str(identity.get("assignment_id", "")),
        "parent_lane_id": str(identity.get("lane_id", "")),
        "parent_request_id": str(identity.get("request_id", "")),
        "parent_session_id": str(identity.get("session_id", "")),
        "payload_digest": digest_object(payload),
        "received_at_sequence": received_at_sequence,
        "binding_method": "PARENT_REQUEST_ID",
    }
    response_identity["transport_binding_digest"] = digest_object(
        {
            **response_identity,
            "dispatch_manifest_digest": identity.get("dispatch_manifest_digest"),
        }
    )
    envelope: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "response_identity": response_identity,
        "author_payload": dict(payload),
        "transport_authority": "DISPATCHER_OWNED_IDENTITY",
        "author_identity_write_count": 0,
    }
    envelope["response_envelope_digest"] = digest_object(envelope)
    return envelope


def _validate_dispatches(dispatches: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    if len(dispatches) != 40:
        _fail("E_SELECTIVE_REPLAY", f"dispatch_count={len(dispatches)}")
    by_request: dict[str, dict[str, Any]] = {}
    request_ids: set[str] = set()
    session_ids: set[str] = set()
    assignment_ids: set[str] = set()
    expected_response_ids: set[str] = set()
    for dispatch in dispatches:
        if dispatch.get("dispatch_record_digest") != digest_object(
            {
                str(key): value
                for key, value in dispatch.items()
                if str(key) != "dispatch_record_digest"
            }
        ):
            _fail("E_DISPATCH_RECORD_DIGEST", "dispatch record")
        identity = dispatch.get("dispatch_identity")
        if not isinstance(identity, Mapping):
            _fail("E_DISPATCH_IDENTITY_MISSING", "dispatch_identity")
        stored_digest = identity.get("dispatch_manifest_digest")
        digest_payload = {
            str(key): value
            for key, value in identity.items()
            if str(key) != "dispatch_manifest_digest"
        }
        if stored_digest != digest_object(digest_payload):
            _fail("E_DISPATCH_DIGEST", str(identity.get("request_id", "")))
        request_id = str(identity.get("request_id", ""))
        session_id = str(identity.get("session_id", ""))
        assignment_id = str(identity.get("assignment_id", ""))
        response_id = str(dispatch.get("expected_response_id", ""))
        replay_request = dispatch.get("replay_request")
        if not isinstance(replay_request, Mapping):
            _fail("E_REPLAY_REQUEST_MISSING", assignment_id)
        if replay_request.get("request_id") != request_id:
            _fail("E_REPLAY_REQUEST_ID_MISMATCH", assignment_id)
        if replay_request.get("assignment_id") != assignment_id:
            _fail("E_REPLAY_ASSIGNMENT_MISMATCH", assignment_id)
        if replay_request.get("lane_id") != identity.get("lane_id"):
            _fail("E_REPLAY_LANE_MISMATCH", assignment_id)
        if replay_request.get("plan_id") != identity.get("plan_id"):
            _fail("E_REPLAY_PLAN_MISMATCH", assignment_id)
        replay_without_digest = {
            str(key): value
            for key, value in replay_request.items()
            if str(key) != "request_digest"
        }
        if replay_request.get("request_digest") != digest_object(replay_without_digest):
            _fail("E_REPLAY_REQUEST_DIGEST", assignment_id)
        if dispatch.get("semantic_payload_digest") != semantic_request_digest(replay_request):
            _fail("E_SEMANTIC_PAYLOAD_DRIFT", assignment_id)
        if dispatch.get("no_content_feedback_carried_forward") is not True:
            _fail("E_CONTENT_FEEDBACK_CARRIED_FORWARD", assignment_id)
        if not request_id:
            _fail("E_REQUEST_ID_MISSING", assignment_id)
        if request_id in request_ids:
            _fail("E_DUPLICATE_REQUEST_ID", request_id)
        if session_id in session_ids:
            _fail("E_DUPLICATE_SESSION_ID", session_id)
        if assignment_id in assignment_ids:
            _fail("E_REPLACEMENT_ASSIGNMENT", assignment_id)
        if response_id in expected_response_ids:
            _fail("E_DUPLICATE_EXPECTED_RESPONSE_ID", response_id)
        request_ids.add(request_id)
        session_ids.add(session_id)
        assignment_ids.add(assignment_id)
        expected_response_ids.add(response_id)
        by_request[request_id] = dict(dispatch)
    return by_request


def validate_and_bind_batch(
    dispatches: Sequence[Mapping[str, Any]],
    envelopes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Bind by parent request identity; completion and file order are irrelevant."""

    by_request = _validate_dispatches(dispatches)
    if len(envelopes) != 40:
        _fail("E_ATOMIC_RESPONSE_COUNT", f"response_count={len(envelopes)}")
    response_ids: set[str] = set()
    bound_requests: set[str] = set()
    bound: list[dict[str, Any]] = []
    for envelope in envelopes:
        if envelope.get("response_envelope_digest") != digest_object(
            {
                str(key): value
                for key, value in envelope.items()
                if str(key) != "response_envelope_digest"
            }
        ):
            _fail("E_RESPONSE_ENVELOPE_DIGEST", "response envelope")
        identity = envelope.get("response_identity")
        if not isinstance(identity, Mapping):
            _fail("E_RESPONSE_IDENTITY_MISSING", "response_identity")
        if isinstance(identity.get("parent_request_id"), list):
            _fail("E_RESPONSE_BINDS_MULTIPLE_REQUESTS", "parent_request_id")
        request_id = str(identity.get("parent_request_id", ""))
        if not request_id:
            _fail("E_RESPONSE_REQUEST_ID_MISSING", "parent_request_id")
        if request_id not in by_request:
            _fail("E_RESPONSE_REQUEST_ID_MISMATCH", request_id)
        if request_id in bound_requests:
            _fail("E_REQUEST_ACCEPTS_MULTIPLE_RESPONSES", request_id)
        dispatch = by_request[request_id]
        expected = dispatch["dispatch_identity"]
        if identity.get("binding_method") == "TRAVERSAL_ORDER":
            _fail("E_TRAVERSAL_ORDER_BINDING_FORBIDDEN", request_id)
        if identity.get("binding_method") == "FILENAME_ORDER":
            _fail("E_FILENAME_ORDER_BINDING_FORBIDDEN", request_id)
        if identity.get("old_response_replay") is True:
            _fail("E_OLD_RESPONSE_REPLAY", request_id)
        if identity.get("parent_run_id") != expected.get("run_id"):
            _fail("E_STALE_RUN_RESPONSE", request_id)
        if identity.get("parent_assignment_id") != expected.get("assignment_id"):
            _fail("E_RESPONSE_ASSIGNMENT_MISMATCH", request_id)
        if identity.get("parent_lane_id") != expected.get("lane_id"):
            _fail("E_CROSS_LANE_BINDING", request_id)
        if identity.get("parent_session_id") != expected.get("session_id"):
            _fail("E_RESPONSE_SESSION_MISMATCH", request_id)
        response_id = str(identity.get("response_id", ""))
        if not response_id:
            _fail("E_RESPONSE_ID_MISSING", request_id)
        if response_id in response_ids:
            _fail("E_DUPLICATE_RESPONSE_ID", response_id)
        if response_id != dispatch.get("expected_response_id"):
            _fail("E_RESPONSE_ID_MISMATCH", request_id)
        payload = envelope.get("author_payload")
        if not isinstance(payload, Mapping):
            _fail("E_PARTIAL_OR_TRUNCATED_RESPONSE", request_id)
        validate_author_payload(payload)
        if identity.get("payload_digest") != digest_object(payload):
            _fail("E_RESPONSE_PAYLOAD_DIGEST", request_id)
        actual_binding_payload = {
            str(key): value
            for key, value in identity.items()
            if str(key) != "transport_binding_digest"
        }
        actual_binding_payload["dispatch_manifest_digest"] = expected.get(
            "dispatch_manifest_digest"
        )
        if identity.get("transport_binding_digest") != digest_object(actual_binding_payload):
            _fail("E_TRANSPORT_BINDING_DIGEST", request_id)
        response_ids.add(response_id)
        bound_requests.add(request_id)
        bound.append(dict(envelope))
    if bound_requests != set(by_request):
        _fail("E_SELECTIVE_REPLAY", "not all requests received one response")
    return sorted(
        bound,
        key=lambda row: str(row["response_identity"]["parent_assignment_id"]),
    )


def project_for_frozen_consumer(
    dispatch: Mapping[str, Any], envelope: Mapping[str, Any]
) -> dict[str, Any]:
    """Project transport metadata into the frozen consumer's legacy response shape."""

    replay_request = dispatch.get("replay_request")
    response_identity = envelope.get("response_identity")
    author_payload = envelope.get("author_payload")
    if not isinstance(replay_request, Mapping):
        _fail("E_REPLAY_REQUEST_MISSING", "replay_request")
    if not isinstance(response_identity, Mapping) or not isinstance(author_payload, Mapping):
        _fail("E_RESPONSE_PROJECTION_INPUT", "response envelope")
    projected = dict(author_payload)
    projected["request_id"] = replay_request["request_id"]
    projected["request_digest"] = replay_request["request_digest"]
    projected["response_id"] = response_identity["response_id"]
    return projected


def valid_stub_payload() -> dict[str, Any]:
    """Return a no-content payload for transport-only T0 tests."""

    return {
        "backend_class": "CONTROLLED_EXECUTION_AGENT",
        "one_request_one_response": True,
        "paired_output_visible": False,
        "review_envelope_visible": False,
        "expected_score_visible": False,
        "chain_of_thought_stored": False,
        "surfaces": {
            "title": "",
            "body_blocks": [],
            "spoken_lines": [],
            "CTA": "",
            "visual_beats": [],
            "capture_instructions": [],
            "audio_grammar": "",
            "editing_grammar": "",
        },
        "surface_bindings": [],
        "style_realization_evidence": [],
        "required_obligation_evidence": [],
    }


if __name__ == "__main__":
    raise SystemExit(2)
