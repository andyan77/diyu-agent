#!/usr/bin/env python3
"""Lifecycle-aware governance gate for the failed PR #9 development evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "CONTROLLED_V2_B_LANE_INDEPENDENT_COMPOSITION_DEV_GATE_001"
ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001"
)
OPEN_DIR = TASK_DIR / "dev_open_gate_001"
ORIGINAL_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_creative_authoring_route_convergence.py"
)
LIVE_CHECKER_PATH = TASK_DIR / (
    "checkpoint_0/check_controlled_v2_creative_authoring_route_convergence_lifecycle.py"
)
REQUESTS_PATH = OPEN_DIR / "authoring_requests.v0.1.jsonl"
RAW_PATH = OPEN_DIR / "raw_authoring_responses.v0.1.jsonl"
CANDIDATES_PATH = OPEN_DIR / "candidates.v0.1.jsonl"
MACHINE_PATH = OPEN_DIR / "machine_structural_results.v0.1.jsonl"
PAIR_PATH = OPEN_DIR / "pair_independence_machine_results.v0.1.jsonl"
RESULT_PATH = OPEN_DIR / "checkpoint_A_result.v0.1.yaml"
SUMMARY_PATH = OPEN_DIR / "reviewer_inputs/development_review_summary.v0.1.yaml"
GUARDIAN_VERDICT_PATH = TASK_DIR / "guardian_inputs/guardian_checkpoint_A_verdict.v0.1.yaml"
FOUNDER_DECISION_PATH = TASK_DIR / "guardian_inputs/founder_architecture_decision.v0.1.yaml"
REVIEW_BINDING_PATH = TASK_DIR / "guardian_inputs/external_review_binding.v0.1.yaml"
ISOLATION_PATH = TASK_DIR / "checkpoint_0/structural_isolation_registry.v0.1.yaml"
RECEIPT_PATH = TASK_DIR / "checkpoint_0/checker_closeout_receipt.v0.1.yaml"
PACKET_PATH = TASK_DIR / "checkpoint_0/guardian_checkpoint_0_packet.v0.1.yaml"

SENSITIVE_CONCEPTS = (
    "expected_score",
    "review_envelope",
    "sibling_candidate",
    "paired_output",
    "expected_verdict",
)
ALLOWED_NEGATIVE_VISIBILITY_KEYS = frozenset(
    {
        "expected_score_visibility",
        "expected_score_visible",
        "review_envelope_visibility",
        "review_envelope_visible",
        "sibling_candidate_visibility",
        "sibling_candidate_visible",
        "paired_output_visibility",
        "paired_output_visible",
        "expected_verdict_visibility",
        "expected_verdict_visible",
    }
)
FIELD_SELECTOR_KEYS = frozenset(
    {"field", "field_name", "kind", "label", "name", "payload_type", "type"}
)
REQUIRED_BLOCKERS = frozenset(
    {
        "B_DEVELOPMENT_GATE_THRESHOLD_NOT_MET",
        "B_PAIR_INDEPENDENCE_FAILED",
        "B_CP14_B_INVALID_OBLIGATION_REF",
    }
)
READINESS_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "release_ready",
        "production_ready",
        "generator_qualified",
        "runtime_provider_adapter_qualified",
        "runtime_ingest_ready",
        "eligible_to_open_sealed_hidden",
        "generation_600_allowed",
        "expand_3600_allowed",
        "formal_300_generation_started",
    }
)
ZERO_KEYS = frozenset(
    {
        "accepted_baseline_increment_count",
        "baseline_increment_count",
        "external_provider_API_call_count",
        "hidden_created_count",
        "published_content_count",
        "runtime_generation_eligible_profile_count",
        "sealed_hidden_attempt_count",
    }
)
FALSE_KEYS = frozenset(
    {
        "development_gate_pass",
        "development_semantic_gate_pass",
        "hidden_created",
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def import_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def original_checker() -> Any:
    return import_module(ROOT / ORIGINAL_CHECKER_PATH, "frozen_convergence_checker")


def response_validator() -> Any:
    return import_module(
        ROOT / TASK_DIR / "core/response_validator.py",
        "lifecycle_response_validator",
    )


def normalize_identifier(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return re.sub(r"_+", "_", normalized)


def sensitive_payload_errors(value: Any, label: str) -> list[str]:
    """Reject value-bearing leak fields while allowing explicit negative visibility flags."""

    errors: list[str] = []

    def walk(child: Any, path: tuple[str, ...]) -> None:
        if isinstance(child, Mapping):
            for raw_key, nested in child.items():
                key = str(raw_key)
                normalized = normalize_identifier(key)
                child_path = (*path, key)
                rendered_path = ".".join(child_path)
                matched = [
                    concept for concept in SENSITIVE_CONCEPTS if concept in normalized
                ]
                if normalized in ALLOWED_NEGATIVE_VISIBILITY_KEYS:
                    if nested is not False:
                        errors.append(
                            f"E_SENSITIVE_VISIBILITY_NOT_FALSE:{label}:{rendered_path}"
                        )
                elif matched:
                    for concept in matched:
                        errors.append(
                            f"E_AUTHOR_REQUEST_LEAK:{label}:{rendered_path}:{concept}"
                        )
                if normalized in FIELD_SELECTOR_KEYS and isinstance(nested, str):
                    selected = normalize_identifier(nested)
                    for concept in SENSITIVE_CONCEPTS:
                        if concept in selected:
                            errors.append(
                                f"E_AUTHOR_REQUEST_LEAK_SELECTOR:{label}:"
                                f"{rendered_path}:{concept}"
                            )
                walk(nested, child_path)
        elif isinstance(child, Sequence) and not isinstance(
            child, (str, bytes, bytearray)
        ):
            for index, nested in enumerate(child):
                walk(nested, (*path, f"[{index}]"))

    walk(value, ())
    return sorted(set(errors))


def boundary_errors(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            child_path = f"{path}.{key}" if path else key
            if key in READINESS_KEYS and child is not False:
                errors.append(f"E_READINESS_TRUE:{child_path}")
            if key in ZERO_KEYS and child != 0:
                errors.append(f"E_FIXED_ZERO_DRIFT:{child_path}")
            if key in FALSE_KEYS and child is not False:
                errors.append(f"E_FAILURE_LIFECYCLE_DRIFT:{child_path}")
            if key in {"accepted_baseline_count", "accepted_baseline_after"} and child != 120:
                errors.append(f"E_BASELINE_INCREASE:{child_path}")
            errors.extend(boundary_errors(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            errors.extend(boundary_errors(child, f"{path}[{index}]"))
    return errors


def failure_lifecycle_errors(
    *,
    pair_overlap_present: bool,
    structural_failure_present: bool,
    verdict: Mapping[str, Any],
    hidden_present: bool,
) -> list[str]:
    errors: list[str] = []
    blockers = set(map(str, verdict.get("blocking_items", [])))
    if verdict.get("artifact_integrity_pass") is not True:
        errors.append("E_ARTIFACT_INTEGRITY_NOT_RECORDED")
    if verdict.get("development_gate_pass") is not False:
        errors.append("E_DEVELOPMENT_FAILURE_NOT_RECORDED")
    if verdict.get("development_semantic_gate_pass") is not False:
        errors.append("E_SEMANTIC_FAILURE_NOT_RECORDED")
    if pair_overlap_present and verdict.get("pair_overlap_present") is not True:
        errors.append("E_PAIR_OVERLAP_NOT_RECORDED")
    if structural_failure_present and verdict.get("structural_failure_present") is not True:
        errors.append("E_STRUCTURAL_FAILURE_NOT_RECORDED")
    if (pair_overlap_present or structural_failure_present) and not REQUIRED_BLOCKERS.issubset(
        blockers
    ):
        errors.append("E_FAILURE_BLOCKING_ITEMS_INCOMPLETE")
    if hidden_present or verdict.get("hidden_created") is not False:
        errors.append("E_HIDDEN_AFTER_DEVELOPMENT_FAILURE")
    if verdict.get("generator_qualified") is not False:
        errors.append("E_GENERATOR_QUALIFIED_AFTER_FAILURE")
    if verdict.get("accepted_baseline_count") != 120:
        errors.append("E_BASELINE_INCREASE_AFTER_FAILURE")
    return errors


def reference_integrity_errors(
    requests: list[dict[str, Any]],
    raw: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    machine: list[dict[str, Any]],
    isolation_records: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    request_map = {row["request_id"]: row for row in requests}
    candidate_map = {row["request_id"]: row for row in candidates}
    machine_map = {row["candidate_id"]: row for row in machine}
    isolation_map = {row["candidate_id"]: row for row in isolation_records}
    validator = response_validator()
    invalid_candidate_ids: set[str] = set()

    for response in raw:
        request_id = str(response.get("request_id", ""))
        request = request_map.get(request_id)
        candidate = candidate_map.get(request_id)
        if request is None or candidate is None:
            errors.append(f"E_REFERENCE_JOIN_MISSING:{request_id}")
            continue
        candidate_id = str(candidate["candidate_id"])
        validation_errors = validator.validate_response(request, response)
        machine_row = machine_map.get(candidate_id)
        if candidate.get("machine_validation_errors") != validation_errors:
            errors.append(f"E_CANDIDATE_VALIDATION_DRIFT:{candidate_id}")
        if machine_row is None or machine_row.get("validation_errors") != validation_errors:
            errors.append(f"E_MACHINE_VALIDATION_DRIFT:{candidate_id}")
            continue
        if validation_errors:
            invalid_candidate_ids.add(candidate_id)
            if candidate.get("machine_structural_eligible") is not False or machine_row.get(
                "machine_structural_eligible"
            ) is not False:
                errors.append(f"E_STRUCTURAL_INELIGIBLE_CLAIMED_ELIGIBLE:{candidate_id}")
            record = isolation_map.get(candidate_id)
            if record is None:
                errors.append(f"E_STRUCTURAL_QUARANTINE_MISSING:{candidate_id}")
                continue
            if record.get("candidate_digest") != candidate.get("candidate_digest"):
                errors.append(f"E_STRUCTURAL_QUARANTINE_DIGEST:{candidate_id}")
            if record.get("validation_errors") != validation_errors:
                errors.append(f"E_STRUCTURAL_QUARANTINE_ERRORS:{candidate_id}")
            expected_markers = {
                "machine_structural_eligible": False,
                "lifecycle": "QUARANTINED_DEVELOPMENT_EVIDENCE",
                "development_gate_pass": False,
                "hidden_created": False,
            }
            for key, expected in expected_markers.items():
                if record.get(key) != expected:
                    errors.append(f"E_STRUCTURAL_QUARANTINE_MARKER:{candidate_id}:{key}")
        elif candidate.get("machine_structural_eligible") is not True or machine_row.get(
            "machine_structural_eligible"
        ) is not True:
            errors.append(f"E_VALID_REFERENCE_MARKED_INELIGIBLE:{candidate_id}")

    for candidate_id in isolation_map:
        if candidate_id not in invalid_candidate_ids:
            errors.append(f"E_SPURIOUS_STRUCTURAL_QUARANTINE:{candidate_id}")
    if invalid_candidate_ids != {"DEV-OPEN-CAND-CP14-B-001"}:
        errors.append("E_INVALID_REFERENCE_SET_DRIFT")
    return errors


def hidden_paths() -> list[Path]:
    return [
        path
        for path in (ROOT / TASK_DIR).rglob("*")
        if "sealed_hidden" in path.name.lower()
    ]


def check_artifact_pins(verdict: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    pins = verdict.get("frozen_artifacts")
    if not isinstance(pins, list):
        return ["E_FROZEN_ARTIFACT_PINS_MISSING"]
    for item in pins:
        if not isinstance(item, Mapping):
            errors.append("E_FROZEN_ARTIFACT_PIN_SHAPE")
            continue
        relative = Path(str(item.get("path", "")))
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            errors.append(f"E_FROZEN_ARTIFACT_DRIFT:{relative}")
    return errors


def check_receipt() -> list[str]:
    errors: list[str] = []
    required = (
        GUARDIAN_VERDICT_PATH,
        FOUNDER_DECISION_PATH,
        REVIEW_BINDING_PATH,
        ISOLATION_PATH,
        RECEIPT_PATH,
        PACKET_PATH,
    )
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        return [f"E_CHECKPOINT0_ARTIFACT_MISSING:{path}" for path in missing]
    receipt = load_yaml(ROOT / RECEIPT_PATH)["checker_closeout_receipt"]
    if receipt.get("original_checker_path") != ORIGINAL_CHECKER_PATH.as_posix():
        errors.append("E_RECEIPT_ORIGINAL_CHECKER_PATH")
    if receipt.get("original_checker_sha256") != sha256_file(ROOT / ORIGINAL_CHECKER_PATH):
        errors.append("E_RECEIPT_ORIGINAL_CHECKER_DIGEST")
    if receipt.get("live_checker_path") != LIVE_CHECKER_PATH.as_posix():
        errors.append("E_RECEIPT_LIVE_CHECKER_PATH")
    if receipt.get("live_checker_sha256") != sha256_file(ROOT / LIVE_CHECKER_PATH):
        errors.append("E_RECEIPT_LIVE_CHECKER_DIGEST")
    if receipt.get("frozen_original_checker_unchanged") is not True:
        errors.append("E_RECEIPT_ORIGINAL_CHECKER_UNFROZEN")
    if receipt.get("candidate_mutation_count") != 0:
        errors.append("E_RECEIPT_CANDIDATE_MUTATION")
    if receipt.get("hidden_created_count") != 0:
        errors.append("E_RECEIPT_HIDDEN_CREATED")
    return errors


def check_open_gate_lifecycle() -> list[str]:
    errors: list[str] = []
    required = (
        REQUESTS_PATH,
        RAW_PATH,
        CANDIDATES_PATH,
        MACHINE_PATH,
        PAIR_PATH,
        RESULT_PATH,
        SUMMARY_PATH,
        GUARDIAN_VERDICT_PATH,
        FOUNDER_DECISION_PATH,
        ISOLATION_PATH,
    )
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        return [f"E_OPEN_GATE_LIFECYCLE_MISSING:{path}" for path in missing]

    requests = load_jsonl(ROOT / REQUESTS_PATH)
    raw = load_jsonl(ROOT / RAW_PATH)
    candidates = load_jsonl(ROOT / CANDIDATES_PATH)
    machine = load_jsonl(ROOT / MACHINE_PATH)
    pairs = load_jsonl(ROOT / PAIR_PATH)
    if [len(rows) for rows in (requests, raw, candidates, machine, pairs)] != [
        40,
        40,
        40,
        40,
        20,
    ]:
        errors.append("E_OPEN_GATE_LIFECYCLE_COUNTS")

    for request in requests:
        errors.extend(sensitive_payload_errors(request, str(request.get("request_id"))))
    for response in raw:
        errors.extend(sensitive_payload_errors(response, str(response.get("response_id"))))

    isolation = load_yaml(ROOT / ISOLATION_PATH)["structural_isolation_registry"]
    isolation_records = isolation.get("records", [])
    errors.extend(
        reference_integrity_errors(requests, raw, candidates, machine, isolation_records)
    )

    pair_overlap_present = any(
        row.get("non_evidence_exact_line_overlap_count", 0) != 0
        or row.get("normalized_8gram_overlap_ratio", 0.0) > 0.15
        for row in pairs
    )
    structural_failure_present = any(row.get("validation_errors") for row in machine)
    verdict = load_yaml(ROOT / GUARDIAN_VERDICT_PATH)["guardian_checkpoint_A_verdict"]
    errors.extend(
        failure_lifecycle_errors(
            pair_overlap_present=pair_overlap_present,
            structural_failure_present=structural_failure_present,
            verdict=verdict,
            hidden_present=bool(hidden_paths()),
        )
    )
    errors.extend(check_artifact_pins(verdict))

    decision = load_yaml(ROOT / FOUNDER_DECISION_PATH)["founder_architecture_decision"]
    if decision.get("authoring_architecture") != "ACCEPT_AND_FREEZE":
        errors.append("E_FOUNDER_ARCHITECTURE_DECISION")
    if decision.get("route_gate") != "ACCEPT_AND_FREEZE":
        errors.append("E_FOUNDER_ROUTE_GATE_DECISION")
    if decision.get("development_gate_001") != "FAIL":
        errors.append("E_FOUNDER_DEVELOPMENT_GATE_DECISION")
    if decision.get("hidden_qualification") != "LOCKED":
        errors.append("E_FOUNDER_HIDDEN_DECISION")
    if decision.get("external_provider_authorized") is not False:
        errors.append("E_FOUNDER_PROVIDER_DECISION")

    result = load_yaml(ROOT / RESULT_PATH)["checkpoint_A_result"]
    if result.get("status") != "PENDING_EXTERNAL_GUARDIAN":
        errors.append("E_CHECKPOINT_A_RESULT_REWRITTEN")
    summary = load_yaml(ROOT / SUMMARY_PATH)["development_review_summary"]
    if summary.get("internal_thresholds_met") is not False:
        errors.append("E_DEVELOPMENT_THRESHOLD_FALSE_NOT_RECORDED")
    if summary.get("eligible_to_open_sealed_hidden") is not False:
        errors.append("E_DEVELOPMENT_SUMMARY_UNLOCKED_HIDDEN")
    return errors


def check_fixed_boundaries() -> list[str]:
    errors: list[str] = []
    task_root = ROOT / TASK_DIR
    for path in task_root.rglob("*.yaml"):
        errors.extend(boundary_errors(load_yaml(path), path.relative_to(ROOT).as_posix()))
    for path in task_root.rglob("*.jsonl"):
        for index, row in enumerate(load_jsonl(path)):
            errors.extend(
                boundary_errors(row, f"{path.relative_to(ROOT).as_posix()}:{index + 1}")
            )
    return errors


def run_live() -> list[str]:
    frozen = original_checker()
    errors: list[str] = []
    errors.extend(frozen.check_registry())
    errors.extend(frozen.check_control_source())
    errors.extend(frozen.check_route_inputs())
    errors.extend(frozen.check_review_protocol())
    errors.extend(frozen.check_core_freeze())
    errors.extend(check_open_gate_lifecycle())
    errors.extend(check_fixed_boundaries())
    errors.extend(check_receipt())
    errors.extend(frozen.check_predecessor_boundaries())
    return sorted(set(errors))


def selftest() -> list[str]:
    errors: list[str] = []
    frozen = original_checker()
    errors.extend(f"FROZEN_{error}" for error in frozen.selftest())

    legal = {
        "expected_score_visibility": False,
        "review_envelope_visibility": False,
        "sibling_candidate_visibility": False,
        "paired_output_visible": False,
        "expected_verdict_visibility": False,
    }
    if sensitive_payload_errors(legal, "legal"):
        errors.append("SELFTEST_LEGAL_VISIBILITY_FALSE_POSITIVE")
    illegal_payloads = (
        {"expected_score": 92},
        {"nested": {"expected_score_payload": {"value": 92}}},
        {"nested": {"leaked_expected_score": 92}},
        {"review_envelope": {"grade": "A"}},
        {"sibling_candidate": {"body": "leak"}},
        {"paired_output": {"body": "leak"}},
        {"expected_verdict": "PASS"},
        {"metadata": {"field": "expected_score", "value": 92}},
        {"expected_score_visibility": True},
    )
    for index, payload in enumerate(illegal_payloads):
        if not sensitive_payload_errors(payload, f"illegal-{index}"):
            errors.append(f"SELFTEST_TRUE_LEAK_NOT_CAUGHT:{index}")

    honest_verdict = {
        "artifact_integrity_pass": True,
        "development_gate_pass": False,
        "development_semantic_gate_pass": False,
        "pair_overlap_present": True,
        "structural_failure_present": True,
        "blocking_items": sorted(REQUIRED_BLOCKERS),
        "hidden_created": False,
        "generator_qualified": False,
        "accepted_baseline_count": 120,
    }
    if failure_lifecycle_errors(
        pair_overlap_present=True,
        structural_failure_present=True,
        verdict=honest_verdict,
        hidden_present=False,
    ):
        errors.append("SELFTEST_HONEST_FAILURE_NOT_ACCEPTED")
    lifecycle_mutations = (
        ("dev-pass", {**honest_verdict, "development_gate_pass": True}, False),
        ("missing-blockers", {**honest_verdict, "blocking_items": []}, False),
        ("qualified", {**honest_verdict, "generator_qualified": True}, False),
        ("baseline", {**honest_verdict, "accepted_baseline_count": 121}, False),
        ("hidden-field", {**honest_verdict, "hidden_created": True}, False),
        ("hidden-path", honest_verdict, True),
    )
    for label, verdict, hidden_present in lifecycle_mutations:
        if not failure_lifecycle_errors(
            pair_overlap_present=True,
            structural_failure_present=True,
            verdict=verdict,
            hidden_present=hidden_present,
        ):
            errors.append(f"SELFTEST_FAILURE_LIFECYCLE_TAMPER_NOT_CAUGHT:{label}")
    if not boundary_errors({"runtime_ingest_ready": True}, "tamper"):
        errors.append("SELFTEST_READINESS_FLIP_NOT_CAUGHT")
    if not boundary_errors({"accepted_baseline_count": 121}, "tamper"):
        errors.append("SELFTEST_BASELINE_INCREASE_NOT_CAUGHT")

    requests = load_jsonl(ROOT / REQUESTS_PATH)
    raw = load_jsonl(ROOT / RAW_PATH)
    candidates = load_jsonl(ROOT / CANDIDATES_PATH)
    machine = load_jsonl(ROOT / MACHINE_PATH)
    isolation = load_yaml(ROOT / ISOLATION_PATH)["structural_isolation_registry"]["records"]
    if reference_integrity_errors(requests, raw, candidates, machine, isolation):
        errors.append("SELFTEST_HONEST_QUARANTINE_NOT_ACCEPTED")
    mutated_machine = copy.deepcopy(machine)
    cp14_machine = next(
        row for row in mutated_machine if row["candidate_id"] == "DEV-OPEN-CAND-CP14-B-001"
    )
    cp14_machine["machine_structural_eligible"] = True
    if not any(
        error.startswith("E_STRUCTURAL_INELIGIBLE_CLAIMED_ELIGIBLE")
        for error in reference_integrity_errors(
            requests, raw, candidates, mutated_machine, isolation
        )
    ):
        errors.append("SELFTEST_INVALID_REF_CLAIMED_ELIGIBLE_NOT_CAUGHT")
    if not any(
        error.startswith("E_STRUCTURAL_QUARANTINE_MISSING")
        for error in reference_integrity_errors(requests, raw, candidates, machine, [])
    ):
        errors.append("SELFTEST_INVALID_REF_UNQUARANTINED_NOT_CAUGHT")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if not __debug__:
        return 2
    errors = selftest() if args.selftest else run_live()
    if errors:
        for error in errors:
            sys.stderr.write(error + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
