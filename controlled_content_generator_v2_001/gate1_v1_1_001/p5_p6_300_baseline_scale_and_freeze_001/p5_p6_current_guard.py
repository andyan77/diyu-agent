#!/usr/bin/env python3
"""Current-owner guard for the nonblocking Gate 1 v1.1 300 quality line."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("p5_p6_current_guard refuses python -O\n")
    raise SystemExit(2)


TASK_ID = "GATE1_V11_300_BASELINE_SCALE_AND_INDEPENDENT_FREEZE_001"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p5_p6_300_baseline_scale_and_freeze_001"
)
OWNER = Path("controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml")
CURRENT_CHECKER = Path("ci/checkers/check_gate1_v1_1_current.py")
SUCCESSOR = TASK_ROOT / "p5_p6_review_successor.py"
SUCCESSOR_MANIFEST = TASK_ROOT / "freeze/review_successor_as_built.v1.0.yaml"
STOP_RESULT = TASK_ROOT / "result/production_quality_gate_stop.v1.0.yaml"
TRIAGE = TASK_ROOT / "review/production/adjudicated_triage.v1.0.jsonl"
TRIAGE_RESULT = TASK_ROOT / "review/production/adjudicated_triage_result.v1.0.yaml"
ADJUDICATION = TASK_ROOT / "review/production/fact_dispute_adjudication.v1.0.jsonl"
FIRST_OUTPUTS = TASK_ROOT / "production/positive_first_outputs.v1.0.jsonl"
FIRST_OUTPUT_FREEZE = TASK_ROOT / "freeze/positive_first_output_freeze.v1.0.yaml"
MACHINE_GATES = TASK_ROOT / "production/first_output_machine_gates.v1.0.jsonl"
EXTERNAL_AUDIT = TASK_ROOT / "production/external_exit_audit.v1.0.yaml"
COMPAT_RECEIPT = TASK_ROOT / "compatibility/current_gate1_checker_p5_receipt.v1.0.yaml"
REFERENCES = TASK_ROOT / "production/reference_approved.v1.0.jsonl"
ROUTE_COMPARISONS = TASK_ROOT / "route/route_comparisons.v1.0.jsonl"
ROUTE_RESULT = TASK_ROOT / "route/route_result.v1.0.yaml"
CANDIDATE_MANIFEST = TASK_ROOT / "freeze/candidate_300_manifest.v1.0.yaml"
FINAL_MANIFEST = TASK_ROOT / "freeze/final_300_baseline_manifest.v1.0.yaml"
APPROVED_POSITIVES = TASK_ROOT / "candidate/approved_positive_240.v1.0.jsonl"
READY_KEYS = {
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
    "runtime_ingest_ready",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_digest(value: dict[str, Any], digest_key: str) -> str:
    payload = dict(value)
    payload.pop(digest_key, None)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return value


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def _has_true_ready(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            (key in READY_KEYS and item is True) or _has_true_ready(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_has_true_ready(item) for item in value)
    return False


def _validate_stop_math(root: Path, errors: list[dict[str, str]]) -> None:
    stop = read_yaml(root / STOP_RESULT)
    triage = read_jsonl(root / TRIAGE)
    triage_result = read_yaml(root / TRIAGE_RESULT)
    dispositions = Counter(str(row.get("disposition")) for row in triage)
    first_acceptable = sum(row.get("first_acceptable") is True for row in triage)
    projected = (
        dispositions["APPROVED_INITIAL_A"]
        + dispositions["LIGHT_REVISION_REQUIRED"]
        + len(read_jsonl(root / REFERENCES))
    )
    minimum_topup = 240 - projected
    maximum_numerator = first_acceptable + minimum_topup
    minimum_denominator = len(triage) + minimum_topup
    maximum_rate = round(maximum_numerator / minimum_denominator, 6)
    extra = 0
    while (maximum_numerator + extra) / (minimum_denominator + extra) < 0.90:
        extra += 1
    expected = {
        "first_output_count": len(triage),
        "first_acceptable_count_after_fact_adjudication": first_acceptable,
        "approved_reference_count": len(read_jsonl(root / REFERENCES)),
        "approved_initial_a_count": dispositions["APPROVED_INITIAL_A"],
        "light_revision_eligible_count": dispositions["LIGHT_REVISION_REQUIRED"],
        "fresh_topup_required_count": dispositions["FRESH_TOPUP_REQUIRED"],
        "minimum_topup_candidate_count_if_all_light_revisions_pass": minimum_topup,
        "maximum_first_acceptable_count_without_rate_gaming": maximum_numerator,
        "minimum_final_sealed_candidate_denominator": minimum_denominator,
        "maximum_possible_first_acceptance_rate_without_rate_gaming": maximum_rate,
        "minimum_superfluous_success_only_candidates_needed_to_reach_threshold": extra,
    }
    if stop.get("result_digest") != object_digest(stop, "result_digest"):
        _error(errors, "E_P5_STOP_DIGEST", "mismatch")
    for key, value in expected.items():
        if stop.get(key) != value:
            _error(errors, "E_P5_STOP_MATH", f"{key}:{stop.get(key)} != {value}")
    if (
        stop.get("schema_version") != "gate1-v1.1-production-quality-gate-stop-v1.0"
        or stop.get("task_id") != TASK_ID
        or stop.get("result_state")
        != "STOPPED_PRODUCTION_FIRST_ACCEPTANCE_GATE_FAILED_NONBLOCKING"
        or stop.get("required_first_acceptance_rate") != 0.90
        or maximum_rate >= 0.90
        or stop.get("superfluous_candidate_generation_allowed") is not False
        or stop.get("light_revisions_executed_count") != 0
        or stop.get("topup_candidates_generated_count") != 0
        or stop.get("candidate_300_manifest_created") is not False
        or stop.get("independent_final_review_started") is not False
        or stop.get("generator_qualified") is not False
        or stop.get("legacy_p5_allowed") is not False
        or stop.get("baseline_300_frozen") is not False
        or stop.get("quality_line_blocks_other_system_work") is not False
        or stop.get("readiness_changed") is not False
    ):
        _error(errors, "E_P5_STOP_STATE", "invalid stop boundary")
    if triage_result.get("result_digest") != object_digest(
        triage_result, "result_digest"
    ):
        _error(errors, "E_P5_TRIAGE_RESULT_DIGEST", "mismatch")


def _validate_rows(root: Path, errors: list[dict[str, str]]) -> None:
    triage = read_jsonl(root / TRIAGE)
    adjudication = read_jsonl(root / ADJUDICATION)
    outputs = read_jsonl(root / FIRST_OUTPUTS)
    gates = read_jsonl(root / MACHINE_GATES)
    if not (
        len(triage) == len(outputs) == len(gates) == 211
        and len({row.get("request_id") for row in triage}) == 211
        and all(row.get("triage_digest") == object_digest(row, "triage_digest") for row in triage)
    ):
        _error(errors, "E_P5_TRIAGE_ROWS", "coverage or digest")
    if not (
        len(adjudication) == 23
        and len({row.get("request_id") for row in adjudication}) == 23
        and sum(row.get("resolution") == "OVERRIDE_FACT_REJECTION" for row in adjudication) == 1
        and sum(row.get("resolution") == "UPHOLD_FACT_REJECTION" for row in adjudication) == 22
        and all(row.get("review_digest") == object_digest(row, "review_digest") for row in adjudication)
    ):
        _error(errors, "E_P5_ADJUDICATION_ROWS", "coverage, distribution, or digest")


def _validate_freezes(root: Path, errors: list[dict[str, str]]) -> None:
    freeze = read_yaml(root / FIRST_OUTPUT_FREEZE)
    if (
        freeze.get("first_outputs_sha256") != sha256_file(root / FIRST_OUTPUTS)
        or freeze.get("machine_gates_sha256") != sha256_file(root / MACHINE_GATES)
    ):
        _error(errors, "E_P5_FIRST_OUTPUT_FREEZE", "output or machine gate drift")
    manifest = read_yaml(root / SUCCESSOR_MANIFEST)
    for field, path in (
        ("review_successor_sha256", SUCCESSOR),
        ("adjudication_sha256", ADJUDICATION),
        ("triage_sha256", TRIAGE),
        ("triage_result_sha256", TRIAGE_RESULT),
    ):
        if manifest.get(field) != sha256_file(root / path):
            _error(errors, "E_P5_REVIEW_SUCCESSOR_FREEZE", field)
    route_result = read_yaml(root / ROUTE_RESULT)
    comparisons = read_jsonl(root / ROUTE_COMPARISONS)
    if (
        len(comparisons) != 60
        or route_result.get("action_match_count") != 60
        or route_result.get("reason_match_count") != 60
        or route_result.get("audience_content_created_count") != 0
        or route_result.get("pass") is not True
    ):
        _error(errors, "E_P5_ROUTE60", "route baseline not 60/60")
    audit = read_yaml(root / EXTERNAL_AUDIT)
    if audit.get("external_content_provider_call_count") != 0:
        _error(errors, "E_P5_EXTERNAL_CALL", str(audit.get("external_content_provider_call_count")))


def _validate_owner(root: Path, errors: list[dict[str, str]]) -> None:
    owner = read_yaml(root / OWNER).get("current_gate1_owner")
    if not isinstance(owner, dict):
        _error(errors, "E_P5_OWNER", "missing")
        return
    if (
        owner.get("owner_id") != "GATE1_V11_300_BASELINE_NONBLOCKING_FAILURE_OWNER"
        or owner.get("task_id") != TASK_ID
        or owner.get("current_task_root") != TASK_ROOT.as_posix()
        or owner.get("current_checker") != CURRENT_CHECKER.as_posix()
        or owner.get("result_state")
        != "STOPPED_PRODUCTION_FIRST_ACCEPTANCE_GATE_FAILED_NONBLOCKING"
        or owner.get("generator_qualified") is not False
        or owner.get("p5_allowed") is not False
        or owner.get("p5_executed") is not True
        or owner.get("baseline_300_frozen") is not False
        or owner.get("nonblocking_quality_line") is not True
        or owner.get("quality_line_blocks_other_system_work") is not False
        or owner.get("owner_digest") != object_digest(owner, "owner_digest")
    ):
        _error(errors, "E_P5_OWNER", "binding or digest")
    if owner.get("core_numbers") != {
        "target_total": 300,
        "positive_target": 240,
        "route_target": 60,
        "reference_inventory": 120,
        "counted_positive_parent_count": 29,
        "historical_component_inventory": 86,
        "active_component_count": 68,
        "active_control_rule_count": 8,
        "active_edge_count": 85,
        "all_unchanged": True,
    }:
        _error(errors, "E_P5_CORE_NUMBERS", str(owner.get("core_numbers")))
    if _has_true_ready(owner.get("readiness")):
        _error(errors, "E_P5_READINESS", "readiness true")


def _validate_compatibility_receipt(root: Path, errors: list[dict[str, str]]) -> None:
    receipt = read_yaml(root / COMPAT_RECEIPT)
    if (
        receipt.get("schema_version")
        != "gate1-v1.1-current-checker-p5-compatibility-receipt-v1.0"
        or receipt.get("task_id") != TASK_ID
        or receipt.get("repair_class") != "REFERENCE_SAFE_SUCCESSOR_DELEGATION"
        or receipt.get("current_checker_sha256_before")
        != "1fae78276fe8d3e69da4a1cda369b792cd091bbca96094c8a76880c9859a75a8"
        or receipt.get("current_checker_sha256_after")
        != sha256_file(root / CURRENT_CHECKER)
        or receipt.get("owner_sha256_before")
        != "9f8865b03c80140683860c33a833f3da24facc8870b69597995c086cac5b8291"
        or receipt.get("owner_sha256_after") != sha256_file(root / OWNER)
        or receipt.get("historical_p1_to_p4_business_asset_checks_preserved") is not True
        or receipt.get("historical_current_checker_and_owner_point_in_time_reinterpreted_only")
        is not True
        or receipt.get("p5_directory_and_report_append_write_surface_allowed_only")
        is not True
        or receipt.get("unknown_future_successor_allowed") is not False
        or receipt.get("normal_mode_pass") is not True
        or receipt.get("selftest_pass") is not True
        or receipt.get("optimized_mode_fail_closed_exit_2") is not True
        or receipt.get("readiness_changed") is not False
        or receipt.get("receipt_digest") != object_digest(receipt, "receipt_digest")
    ):
        _error(errors, "E_P5_COMPAT_RECEIPT", "binding, scope, or digest")


def validate_p5(root: Path, *, run_successor: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = (
        OWNER,
        SUCCESSOR,
        SUCCESSOR_MANIFEST,
        STOP_RESULT,
        TRIAGE,
        TRIAGE_RESULT,
        ADJUDICATION,
        FIRST_OUTPUTS,
        FIRST_OUTPUT_FREEZE,
        MACHINE_GATES,
        EXTERNAL_AUDIT,
        COMPAT_RECEIPT,
        REFERENCES,
        ROUTE_COMPARISONS,
        ROUTE_RESULT,
    )
    for path in required:
        if not (root / path).exists():
            _error(errors, "E_P5_REQUIRED_FILE", path.as_posix())
    if errors:
        return errors
    try:
        _validate_rows(root, errors)
        _validate_stop_math(root, errors)
        _validate_freezes(root, errors)
        _validate_owner(root, errors)
        _validate_compatibility_receipt(root, errors)
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        _error(errors, "E_P5_GUARD_EXCEPTION", str(error))
    for forbidden in (CANDIDATE_MANIFEST, FINAL_MANIFEST, APPROVED_POSITIVES):
        if (root / forbidden).exists():
            _error(errors, "E_P5_FALSE_FREEZE", forbidden.as_posix())
    for forbidden_dir in (TASK_ROOT / "production/topup", TASK_ROOT / "production/revision"):
        if (root / forbidden_dir).exists():
            _error(errors, "E_P5_POST_STOP_GENERATION", forbidden_dir.as_posix())
    if run_successor and not errors:
        completed = subprocess.run(
            [sys.executable, str(root / SUCCESSOR), "check"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            _error(errors, "E_P5_SUCCESSOR_CHECK", completed.stderr or completed.stdout)
    return errors


def selftest(root: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="gate1-p5-guard-") as temporary:
        fixture = Path(temporary)
        shutil.copytree(root / TASK_ROOT, fixture / TASK_ROOT)
        (fixture / OWNER).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / OWNER, fixture / OWNER)
        (fixture / CURRENT_CHECKER).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / CURRENT_CHECKER, fixture / CURRENT_CHECKER)
        if validate_p5(fixture, run_successor=False):
            return 1
        tests: list[tuple[str, Any]] = []

        def tamper_stop(target: Path) -> None:
            value = read_yaml(target / STOP_RESULT)
            value["maximum_possible_first_acceptance_rate_without_rate_gaming"] = 0.90
            value["result_digest"] = object_digest(value, "result_digest")
            write_yaml(target / STOP_RESULT, value)

        def tamper_owner(target: Path) -> None:
            value = read_yaml(target / OWNER)
            owner = value["current_gate1_owner"]
            owner["readiness"]["production_ready"] = True
            owner["owner_digest"] = object_digest(owner, "owner_digest")
            write_yaml(target / OWNER, value)

        def add_false_freeze(target: Path) -> None:
            path = target / CANDIDATE_MANIFEST
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("false freeze\n", encoding="utf-8")

        tests.extend(
            [
                ("stop_math", tamper_stop),
                ("readiness", tamper_owner),
                ("false_freeze", add_false_freeze),
            ]
        )
        for name, mutate in tests:
            case = fixture.with_name(f"{fixture.name}-{name}")
            shutil.copytree(fixture, case)
            mutate(case)
            if not validate_p5(case, run_successor=False):
                return 1
    return 0
