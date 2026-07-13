#!/usr/bin/env python3
"""Execute the one authorized 40-request transport replay."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_IMPORT_TASK_DIR = Path(__file__).resolve().parent
_IMPORT_ROOT = _IMPORT_TASK_DIR.parents[1]
if str(_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPORT_ROOT))

from controlled_content_generator_v2_001.b_channel_component_consumption_and_claim_closure_dev_gate_001.run_isolated_author_sessions import (  # noqa: E402
    AUTHOR_PROTOCOL_PATH,
    CODEX_PATH,
    _author_prompt,
)
from transport.dispatcher_owned_identity_adapter import (  # noqa: E402
    TASK_ID,
    TransportIdentityError,
    build_response_envelope,
    canonical_json,
    digest_object,
    validate_and_bind_batch,
)


LOGGER = logging.getLogger(__name__)
TASK_DIR = Path(__file__).resolve().parent
ROOT = TASK_DIR.parents[1]
DISPATCH_PATH = TASK_DIR / "replay/replay_dispatch_manifest.v0.1.jsonl"
PAYLOAD_SCHEMA_PATH = TASK_DIR / "transport/author_payload.schema.json"
FREEZE_PATH = TASK_DIR / "freeze/transport_freeze_manifest.v0.1.json"
FINAL_BATCH_DIR = TASK_DIR / "replay/persisted_batch"
FAILURE_RECEIPT_PATH = TASK_DIR / "replay/transport_replay_failure_receipt.v0.1.json"
INITIAL_FAILURE_PATH = ROOT / (
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001/"
    "author/author_session_failure_receipt.v0.1.json"
)
INITIAL_RESULT_PATH = INITIAL_FAILURE_PATH.parents[1] / "result/development_gate_result.v0.1.json"


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def _verify_freeze() -> dict[str, Any]:
    freeze = load_json(FREEZE_PATH)
    if freeze.get("freeze_manifest_digest") != digest_object(
        {key: value for key, value in freeze.items() if key != "freeze_manifest_digest"}
    ):
        raise ValueError("transport freeze manifest digest mismatch")
    for group in (
        "prior_frozen_file_digests",
        "transport_core_file_digests",
    ):
        for relative, expected in freeze[group].items():
            if sha256_file(ROOT / relative) != expected:
                raise ValueError(f"frozen file drift before replay: {relative}")
    for relative, expected in freeze["generated_file_digests"].items():
        if sha256_file(TASK_DIR / relative) != expected:
            raise ValueError(f"transport checkpoint artifact drift: {relative}")
    prompt_digest = hashlib.sha256(_author_prompt().encode("utf-8")).hexdigest()
    if prompt_digest != freeze.get("author_runtime_prompt_sha256"):
        raise ValueError("semantic author runtime prompt drift")
    return freeze


def _verify_authorization() -> None:
    initial = load_json(INITIAL_FAILURE_PATH)
    result = load_json(INITIAL_RESULT_PATH)
    if initial.get("persisted_raw_response_count") != 0:
        raise ValueError("initial raw responses exist; authorized replay is forbidden")
    if initial.get("persisted_candidate_count") != 0:
        raise ValueError("initial candidates exist; authorized replay is forbidden")
    if result.get("development_gate", {}).get("quality_evaluation_completed") is not False:
        raise ValueError("initial quality review exists; authorized replay is forbidden")
    if result.get("authoring", {}).get("reroll_count") != 0:
        raise ValueError("initial reroll count is not zero")
    if FINAL_BATCH_DIR.exists() or FAILURE_RECEIPT_PATH.exists():
        raise ValueError("authorized transport replay was already consumed")
    replay_dir = TASK_DIR / "replay"
    residuals = list(replay_dir.glob(".transport-replay-stage-*"))
    if residuals:
        raise ValueError("temporary replay response residual exists")


def _run_one(
    dispatch: Mapping[str, Any],
    sessions_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = dispatch["dispatch_identity"]
    request_id = str(identity["request_id"])
    session_id = str(identity["session_id"])
    session_dir = sessions_root / session_id
    session_dir.mkdir(parents=True, exist_ok=False)
    request = dispatch["replay_request"]
    (session_dir / "author_request.json").write_text(
        json.dumps(request, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(AUTHOR_PROTOCOL_PATH, session_dir / "creative_author_protocol.yaml")
    shutil.copyfile(PAYLOAD_SCHEMA_PATH, session_dir / "creative_author_response.schema.json")
    payload_path = session_dir / "author_payload.json"
    command = [
        CODEX_PATH,
        "exec",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "-C",
        str(session_dir),
        "--output-schema",
        str(session_dir / "creative_author_response.schema.json"),
        "-o",
        str(payload_path),
        _author_prompt(),
    ]
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"CODEX_THREAD_ID", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE"}
    }
    completed = subprocess.run(
        command,
        cwd=session_dir,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=900,
    )
    if completed.returncode != 0:
        raise TransportIdentityError("E_AUTHOR_PROCESS_FAILED", request_id)
    if not payload_path.exists():
        raise TransportIdentityError("E_PARTIAL_OR_TRUNCATED_RESPONSE", request_id)
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TransportIdentityError("E_PARTIAL_OR_TRUNCATED_RESPONSE", request_id) from exc
    if not isinstance(payload, Mapping):
        raise TransportIdentityError("E_PARTIAL_OR_TRUNCATED_RESPONSE", request_id)
    envelope = build_response_envelope(
        dispatch,
        payload,
        received_at_sequence=int(identity["dispatch_sequence"]),
    )
    audit: dict[str, Any] = {
        "request_id": request_id,
        "assignment_id": identity["assignment_id"],
        "lane_id": identity["lane_id"],
        "session_id": session_id,
        "response_id": dispatch["expected_response_id"],
        "backend_class": "CONTROLLED_EXECUTION_AGENT",
        "execution_surface": "codex_exec_ephemeral_isolated_session",
        "fresh_process": True,
        "working_directory_contains_only_request_protocol_schema": True,
        "sibling_request_visible": False,
        "sibling_candidate_visible": False,
        "prior_failed_response_visible": False,
        "quality_feedback_visible": False,
        "review_envelope_visible": False,
        "expected_score_visible": False,
        "external_provider_API_call_count": 0,
        "content_reroll_count": 0,
        "replacement_count": 0,
        "payload_digest": digest_object(payload),
        "response_envelope_digest": envelope["response_envelope_digest"],
    }
    audit["session_audit_digest"] = digest_object(audit)
    return envelope, audit


def _write_failure_receipt(errors: list[dict[str, str]], staged_count: int) -> None:
    receipt: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "status": "STOPPED_TRANSPORT_REPLAY_FAILED",
        "authorized_replay_consumed": True,
        "physical_author_invocation_total": 80,
        "authorized_transport_request_replay_count": 40,
        "staged_response_count": staged_count,
        "persisted_raw_response_count": 0,
        "candidate_count": 0,
        "transport_errors": errors,
        "content_reroll_count": 0,
        "replacement_count": 0,
        "selective_retry_count": 0,
        "third_attempt_allowed": False,
        "hidden_count": 0,
        "accepted_baseline_count": 120,
        "generator_qualified": False,
    }
    receipt["failure_receipt_digest"] = digest_object(receipt)
    write_json(FAILURE_RECEIPT_PATH, receipt)


def _persist_success(
    bound: list[dict[str, Any]],
    audits: list[dict[str, Any]],
    dispatches: list[dict[str, Any]],
) -> None:
    replay_dir = TASK_DIR / "replay"
    stage_dir = Path(tempfile.mkdtemp(prefix=".transport-replay-stage-", dir=replay_dir))
    try:
        write_jsonl(stage_dir / "raw_author_response_envelopes.v0.1.jsonl", bound)
        manifest: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "new_replay_run_id": dispatches[0]["dispatch_identity"]["run_id"],
            "author_session_count": 40,
            "fresh_ephemeral_session_count": 40,
            "transport_valid_response_count": 40,
            "one_request_one_response_count": 40,
            "author_identity_write_count": 0,
            "initial_author_invocation_count": 40,
            "replay_author_invocation_count": 40,
            "physical_author_invocation_total": 80,
            "content_evaluable_attempt_count": 40,
            "content_reroll_count": 0,
            "replacement_count": 0,
            "selective_retry_count": 0,
            "external_provider_API_call_count": 0,
            "hidden_count": 0,
            "session_audits": sorted(audits, key=lambda row: str(row["assignment_id"])),
        }
        manifest["manifest_digest"] = digest_object(manifest)
        write_json(stage_dir / "replay_session_manifest.v0.1.json", manifest)
        receipt: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "status": "AUTHORIZED_TRANSPORT_REPLAY_PERSISTED",
            "authorized_replay_consumed": True,
            "staged_response_count": 40,
            "transport_valid_response_count": 40,
            "persisted_raw_response_count": 40,
            "atomic_batch_persistence": True,
            "physical_author_invocation_total": 80,
            "content_evaluable_attempt_count": 40,
            "content_reroll_count": 0,
            "replacement_count": 0,
            "selective_retry_count": 0,
            "third_attempt_allowed": False,
            "content_validation_started_before_persistence": False,
            "hidden_count": 0,
            "accepted_baseline_count": 120,
            "generator_qualified": False,
        }
        receipt["persistence_receipt_digest"] = digest_object(receipt)
        write_json(stage_dir / "atomic_persistence_receipt.v0.1.json", receipt)
        os.replace(stage_dir, FINAL_BATCH_DIR)
    finally:
        if stage_dir.exists():
            shutil.rmtree(stage_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if __debug__ is False:
        return 2
    if args.workers < 1 or args.workers > 4:
        raise ValueError("workers must be between one and four")
    _verify_freeze()
    _verify_authorization()
    dispatches = sorted(
        load_jsonl(DISPATCH_PATH),
        key=lambda row: str(row["dispatch_identity"]["assignment_id"]),
    )
    if len(dispatches) != 40:
        raise ValueError("authorized replay requires exactly 40 dispatches")
    responses: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="replay34-isolated-authors-") as temp_dir:
        sessions_root = Path(temp_dir)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(_run_one, dispatch, sessions_root): dispatch
                for dispatch in dispatches
            }
            for future in concurrent.futures.as_completed(futures):
                dispatch = futures[future]
                request_id = str(dispatch["dispatch_identity"]["request_id"])
                try:
                    envelope, audit = future.result()
                    responses.append(envelope)
                    audits.append(audit)
                except TransportIdentityError as exc:
                    errors.append({"request_id": request_id, "code": exc.code})
                except Exception:
                    errors.append({"request_id": request_id, "code": "E_AUTHOR_SESSION_UNEXPECTED"})
    if errors:
        _write_failure_receipt(sorted(errors, key=lambda row: row["request_id"]), len(responses))
        LOGGER.error("authorized replay failed transport validation; third attempt forbidden")
        return 1
    try:
        bound = validate_and_bind_batch(dispatches, responses)
    except TransportIdentityError as exc:
        _write_failure_receipt([{"request_id": "BATCH", "code": exc.code}], len(responses))
        LOGGER.error("authorized replay batch binding failed; third attempt forbidden")
        return 1
    _persist_success(bound, audits, dispatches)
    LOGGER.info("authorized transport replay persisted 40/40 responses atomically")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        raise SystemExit(main())
    except Exception as exc:
        LOGGER.error("E_AUTHORIZED_TRANSPORT_REPLAY: %s", exc)
        raise SystemExit(1) from exc
