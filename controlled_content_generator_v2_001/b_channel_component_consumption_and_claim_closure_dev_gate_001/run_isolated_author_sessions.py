#!/usr/bin/env python3
"""Run one fresh controlled execution agent for each frozen author request."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)
TASK_DIR = Path(__file__).resolve().parent
ROOT = TASK_DIR.parents[1]
REQUESTS_PATH = TASK_DIR / "requests/author_requests.v0.1.jsonl"
RAW_OUTPUT_PATH = TASK_DIR / "author/raw_author_responses.v0.1.jsonl"
SESSION_MANIFEST_PATH = TASK_DIR / "author/author_session_manifest.v0.1.json"
AUTHOR_PROTOCOL_PATH = ROOT / (
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/"
    "core/creative_author_protocol.v0.1.yaml"
)
RESPONSE_SCHEMA_PATH = ROOT / (
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/"
    "core/creative_author_response.schema.json"
)
CODEX_PATH = shutil.which("codex") or "/home/faye/.nvm/versions/node/v20.20.1/bin/codex"
TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_COMPONENT_CONSUMPTION_AND_CLAIM_CLOSURE_DEV_GATE_001"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validate_response(request: Mapping[str, Any], response: Mapping[str, Any]) -> None:
    if response.get("request_id") != request.get("request_id"):
        raise ValueError("response request_id mismatch")
    if response.get("request_digest") != request.get("request_digest"):
        raise ValueError("response request_digest mismatch")
    fixed_values = {
        "backend_class": "CONTROLLED_EXECUTION_AGENT",
        "one_request_one_response": True,
        "paired_output_visible": False,
        "review_envelope_visible": False,
        "expected_score_visible": False,
        "chain_of_thought_stored": False,
    }
    for key, expected in fixed_values.items():
        if response.get(key) != expected:
            raise ValueError(f"invalid author response boundary field: {key}")
    surfaces = response.get("surfaces")
    if not isinstance(surfaces, Mapping):
        raise ValueError("author response surfaces are missing")
    expected_surfaces = {
        "title",
        "body_blocks",
        "spoken_lines",
        "CTA",
        "visual_beats",
        "capture_instructions",
        "audio_grammar",
        "editing_grammar",
    }
    if set(surfaces) != expected_surfaces:
        raise ValueError("author response surface schema mismatch")


def _author_prompt() -> str:
    return """You are the isolated Creative Author for exactly one development request.

Read only author_request.json, creative_author_protocol.yaml, and creative_author_response.schema.json in this directory. Return exactly one JSON object matching the response schema. Do not inspect any repository, sibling request, candidate, score, review, expectation, or baseline.

Write concise Chinese audience-facing content that realizes the supplied planning axes and form-only component constraints. The two lanes are independently authored; you cannot see the sibling lane. Use only source_atoms for any fact, entity, role, action, state, number, sound, result, or relation. Components are never fact sources and their prose must not be copied into the output.

Hard requirements:
- Do not mention CP identifiers or the words 资格、合成、内部、复审、版本、测试.
- Do not teach how to review content and do not write a fixed marketing CTA.
- Do not invent people, customers, stores, cities, SKUs, dialogue, experience, causes, actions, sounds, numbers, or outcomes.
- Keep pending and unresolved states open. Do not turn observation into proof.
- Treat every nonempty surface item as an atomic unit. Add one surface_bindings record with the exact path and exact text for every nonempty title, body block, spoken line, CTA, visual beat, capture instruction, audio grammar, and editing grammar item.
- Factual units must cite the smallest supporting source_atom_refs. Pure open questions or nonfactual form instructions may use an empty source_atom_refs list.
- Use JSON pointers such as /surfaces/title, /surfaces/body_blocks/0, /surfaces/spoken_lines/0, and /surfaces/CTA.
- Realize the requested differences through information order, visual subject, sound subject, rhythm, and ending, not by naming the content category.
- CP14 may keep spoken_lines empty and CTA empty. Empty fields still remain in the response object.
- Do not store or expose chain of thought. Output only the final JSON object.
"""


def _run_one(request: Mapping[str, Any], root_temp: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    request_id = str(request["request_id"])
    safe_name = request_id.replace("/", "_")
    session_dir = root_temp / safe_name
    session_dir.mkdir(parents=True, exist_ok=False)
    (session_dir / "author_request.json").write_text(
        json.dumps(request, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(AUTHOR_PROTOCOL_PATH, session_dir / "creative_author_protocol.yaml")
    shutil.copyfile(RESPONSE_SCHEMA_PATH, session_dir / "creative_author_response.schema.json")
    response_path = session_dir / "final_response.json"
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
        str(response_path),
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
        tail = completed.stdout[-2000:]
        raise RuntimeError(f"author session failed for {request_id}: {tail}")
    response = json.loads(response_path.read_text(encoding="utf-8"))
    if not isinstance(response, dict):
        raise ValueError(f"author response is not an object: {request_id}")
    _validate_response(request, response)
    audit: dict[str, Any] = {
        "request_id": request_id,
        "backend_class": "CONTROLLED_EXECUTION_AGENT",
        "execution_surface": "codex_exec_ephemeral_isolated_session",
        "fresh_process": True,
        "working_directory_contains_only_request_protocol_schema": True,
        "sibling_request_visible": False,
        "sibling_candidate_visible": False,
        "review_envelope_visible": False,
        "expected_score_visible": False,
        "external_provider_API_call_count": 0,
        "reroll_count": 0,
        "response_digest": digest_object(response),
    }
    audit["session_audit_digest"] = digest_object(audit)
    return response, audit


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
    requests = sorted(load_jsonl(REQUESTS_PATH), key=lambda row: str(row["request_id"]))
    if len(requests) != 40 or len({row["request_id"] for row in requests}) != 40:
        raise ValueError("exactly 40 unique frozen requests are required")
    if RAW_OUTPUT_PATH.exists() or SESSION_MANIFEST_PATH.exists():
        raise ValueError("author outputs already exist; reroll and replacement are forbidden")

    with tempfile.TemporaryDirectory(prefix="dev33-isolated-authors-") as temp_dir:
        root_temp = Path(temp_dir)
        responses: list[dict[str, Any]] = []
        audits: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(_run_one, request, root_temp): request for request in requests}
            for future in concurrent.futures.as_completed(futures):
                response, audit = future.result()
                responses.append(response)
                audits.append(audit)

    responses.sort(key=lambda row: str(row["request_id"]))
    audits.sort(key=lambda row: str(row["request_id"]))
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_OUTPUT_PATH.write_text(
        "".join(canonical_json(row) + "\n" for row in responses),
        encoding="utf-8",
    )
    manifest: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "author_session_count": len(audits),
        "fresh_ephemeral_session_count": sum(row["fresh_process"] for row in audits),
        "one_request_one_response_count": len(responses),
        "reroll_count": 0,
        "replacement_count": 0,
        "external_provider_API_call_count": 0,
        "sealed_hidden_case_count": 0,
        "session_audits": audits,
    }
    manifest["manifest_digest"] = digest_object(manifest)
    SESSION_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("completed %s isolated author sessions", len(responses))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        raise SystemExit(main())
    except Exception as exc:
        LOGGER.error("E_ISOLATED_AUTHOR_SESSION: %s", exc)
        raise SystemExit(1) from exc
