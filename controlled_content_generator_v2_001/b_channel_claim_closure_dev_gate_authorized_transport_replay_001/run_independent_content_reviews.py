#!/usr/bin/env python3
"""Run isolated primary and fact reviewers over all replay candidates."""

from __future__ import annotations

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
TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_CLAIM_CLOSURE_DEV_GATE_AUTHORIZED_TRANSPORT_REPLAY_001"
CODEX_PATH = shutil.which("codex") or "/home/faye/.nvm/versions/node/v20.20.1/bin/codex"
CANDIDATE_PATH = TASK_DIR / "generator/development_candidates.v0.1.jsonl"
PRIMARY_PACKET_PATH = TASK_DIR / "review/primary_review_packets.v0.1.jsonl"
FACT_PACKET_PATH = TASK_DIR / "review/fact_review_packets.v0.1.jsonl"
PAIR_PACKET_PATH = TASK_DIR / "review/pair_review_packets.v0.1.jsonl"
PRIMARY_SCHEMA_PATH = TASK_DIR / "review/primary_review_response.schema.json"
FACT_SCHEMA_PATH = TASK_DIR / "review/fact_review_response.schema.json"
FINAL_REVIEW_DIR = TASK_DIR / "review/persisted_reviews"
FAILURE_PATH = TASK_DIR / "review/review_execution_failure.v0.1.json"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


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


def _primary_prompt() -> str:
    return """You are the independent Blind Surface Primary Reviewer, not the producer.

Read every record in primary_review_packets.jsonl and pair_review_packets.jsonl. Review all title, body, spoken, CTA, visual, shot, audio, sound, caption, on-screen, and editing surfaces. Return exactly one JSON object matching review_response.schema.json.

For each of the 40 candidates, zero_edit_acceptable is true only when the candidate can be used directly with no wording, structural, coherence, execution, or polish change. Any minor edit means false. Reject formulaic review language, meta scaffolding, empty generic filler, incoherent production direction, and a surface that does not realize its content-product purpose. Do not assess source truth; that belongs to the separate fact reviewer.

For each of the 20 blinded pairs, read both complete surfaces and their planning axes. semantically_independent is true only when the actual information order, narrative mechanism, visual subject, sound subject, rhythm, and ending produce genuinely different compositions. Synonym replacement or the same sequence with cosmetic wording is false. Count only axes visibly realized in the final surfaces.

Do not expose chain of thought. Give concise evidence-based rationales and output only JSON."""


def _fact_prompt() -> str:
    return """You are the independent Fact/Authorization Adversarial Reviewer, not the producer.

Read every one of the 40 records in fact_review_packets.jsonl. For every candidate, inspect every audience and execution surface against the supplied source atoms, authorization, claim boundary, role limits, and founder hard guards. Return exactly one JSON object matching review_response.schema.json.

fact_authorization_pass is true only when every factual unit is fully supported and authorized. Count unsupported facts and all invented numbers, actions, causality, results, entities, sounds, roles, or authority across title, body, spoken, CTA, visual, shot, audio, sound, caption, on-screen, and editing surfaces. Components and stylistic plausibility are never evidence. Open questions and disclosed hypotheticals are allowed only when they do not assert an unsupported fact. Record findings only where a real issue exists.

Do not trust machine labels, do not repair text, do not expose chain of thought, and output only JSON."""


def _run_role(
    role: str,
    session_root: Path,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    session_dir = session_root / role.lower()
    session_dir.mkdir(parents=True, exist_ok=False)
    if role == "PRIMARY":
        shutil.copyfile(PRIMARY_PACKET_PATH, session_dir / "primary_review_packets.jsonl")
        shutil.copyfile(PAIR_PACKET_PATH, session_dir / "pair_review_packets.jsonl")
        schema = PRIMARY_SCHEMA_PATH
        prompt = _primary_prompt()
    else:
        shutil.copyfile(FACT_PACKET_PATH, session_dir / "fact_review_packets.jsonl")
        schema = FACT_SCHEMA_PATH
        prompt = _fact_prompt()
    shutil.copyfile(schema, session_dir / "review_response.schema.json")
    response_path = session_dir / "review_response.json"
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
        str(session_dir / "review_response.schema.json"),
        "-o",
        str(response_path),
        prompt,
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
        timeout=1800,
    )
    if completed.returncode != 0 or not response_path.exists():
        raise RuntimeError(f"{role} reviewer failed")
    response = json.loads(response_path.read_text(encoding="utf-8"))
    if not isinstance(response, dict):
        raise TypeError(f"{role} reviewer returned non-object")
    audit: dict[str, Any] = {
        "review_role": role,
        "backend_class": "CONTROLLED_EXECUTION_AGENT",
        "fresh_ephemeral_session": True,
        "producer_role": False,
        "candidate_edit_allowed": False,
        "expected_gate_score_visible": False,
        "external_provider_API_call_count": 0,
        "response_digest": digest_object(response),
    }
    audit["audit_digest"] = digest_object(audit)
    return role, response, audit


def _validate_reviews(primary: Mapping[str, Any], fact: Mapping[str, Any]) -> None:
    candidate_ids = {str(row["candidate_id"]) for row in load_jsonl(CANDIDATE_PATH)}
    primary_rows = primary.get("candidate_reviews")
    pair_rows = primary.get("pair_reviews")
    fact_rows = fact.get("candidate_reviews")
    if not isinstance(primary_rows, list) or len(primary_rows) != 40:
        raise ValueError("primary reviewer did not review 40 candidates")
    if not isinstance(fact_rows, list) or len(fact_rows) != 40:
        raise ValueError("fact reviewer did not review 40 candidates")
    if not isinstance(pair_rows, list) or len(pair_rows) != 20:
        raise ValueError("primary reviewer did not review 20 pairs")
    if {str(row.get("candidate_id")) for row in primary_rows} != candidate_ids:
        raise ValueError("primary candidate review identity set mismatch")
    if {str(row.get("candidate_id")) for row in fact_rows} != candidate_ids:
        raise ValueError("fact candidate review identity set mismatch")
    if {str(row.get("profile_id")) for row in pair_rows} != {
        f"CP{index:02d}" for index in range(1, 21)
    }:
        raise ValueError("pair review profile set mismatch")
    if any(row.get("all_surfaces_read") is not True for row in primary_rows):
        raise ValueError("primary reviewer omitted a candidate surface set")
    if any(
        row.get("all_surfaces_read") is not True or row.get("source_atoms_read") is not True
        for row in fact_rows
    ):
        raise ValueError("fact reviewer omitted a candidate or source set")
    if any(row.get("both_surfaces_read") is not True for row in pair_rows):
        raise ValueError("primary reviewer omitted a pair surface set")


def _persist(
    primary: Mapping[str, Any],
    fact: Mapping[str, Any],
    audits: list[dict[str, Any]],
) -> None:
    review_dir = TASK_DIR / "review"
    stage_dir = Path(tempfile.mkdtemp(prefix=".review-stage-", dir=review_dir))
    try:
        write_json(stage_dir / "blind_surface_primary_reviews.v0.1.json", primary)
        write_json(stage_dir / "fact_authorization_adversarial_reviews.v0.1.json", fact)
        manifest: dict[str, Any] = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "reviewer_role_count": 2,
            "candidate_primary_review_count": 40,
            "candidate_fact_review_count": 40,
            "pair_review_count": 20,
            "disagreement_adjudicator_invocation_count": 0,
            "adjudicator_reason": "reviewers assessed distinct quality and fact dimensions",
            "producer_self_score_used_as_truth": False,
            "candidate_edit_count": 0,
            "content_reroll_count": 0,
            "reviewer_audits": sorted(audits, key=lambda row: row["review_role"]),
        }
        manifest["manifest_digest"] = digest_object(manifest)
        write_json(stage_dir / "independent_review_manifest.v0.1.json", manifest)
        os.replace(stage_dir, FINAL_REVIEW_DIR)
    finally:
        if stage_dir.exists():
            shutil.rmtree(stage_dir)


def _write_failure(code: str) -> None:
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "status": "INDEPENDENT_REVIEW_EXECUTION_FAILED",
        "error_code": code,
        "candidate_edit_count": 0,
        "content_reroll_count": 0,
        "hidden_count": 0,
        "accepted_baseline_count": 120,
        "generator_qualified": False,
    }
    result["failure_digest"] = digest_object(result)
    write_json(FAILURE_PATH, result)


def main() -> int:
    if __debug__ is False:
        return 2
    if FINAL_REVIEW_DIR.exists() or FAILURE_PATH.exists():
        raise ValueError("independent content review has already been executed")
    if len(load_jsonl(CANDIDATE_PATH)) != 40:
        raise ValueError("independent review requires 40 immutable candidates")
    outputs: dict[str, dict[str, Any]] = {}
    audits: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="replay34-independent-review-") as temp_dir:
            session_root = Path(temp_dir)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(_run_role, role, session_root) for role in ("PRIMARY", "FACT")]
                for future in concurrent.futures.as_completed(futures):
                    role, response, audit = future.result()
                    outputs[role] = response
                    audits.append(audit)
        _validate_reviews(outputs["PRIMARY"], outputs["FACT"])
    except Exception as exc:
        _write_failure(f"E_REVIEW_EXECUTION_{type(exc).__name__.upper()}")
        LOGGER.error("independent content review failed structurally")
        return 1
    _persist(outputs["PRIMARY"], outputs["FACT"], audits)
    LOGGER.info("independent content review persisted 40 primary, 40 fact, and 20 pair reviews")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        raise SystemExit(main())
    except Exception as exc:
        LOGGER.error("E_INDEPENDENT_CONTENT_REVIEW: %s", exc)
        raise SystemExit(1) from exc
