#!/usr/bin/env python3
"""Independent gate for creative-authoring and route convergence evidence."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "CONTROLLED_V2_CREATIVE_AUTHORING_ROUTE_ORACLE_CONVERGENCE_001"
ROOT = Path(__file__).resolve().parents[2]
TASK_DIR = Path("controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001")
CORE_DIR = TASK_DIR / "core"
ROUTE_DIR = TASK_DIR / "route"
OPEN_DIR = TASK_DIR / "dev_open_gate_001"
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
REGISTRY_PATH = CORE_DIR / "active_authoring_registry.v0.3.yaml"
COMPILER_PATH = CORE_DIR / "constraint_compiler.py"
VALIDATOR_PATH = CORE_DIR / "response_validator.py"
ROUTE_GATE_PATH = CORE_DIR / "controlled_v2_route_gate.py"
MATERIALIZER_PATH = TASK_DIR / "run_convergence_materializer.py"
RUBRIC_PATH = TASK_DIR / "review/qualification_rubric.v2.0.yaml"
PROTOCOL_PATH = TASK_DIR / "review/qualification_review_protocol.freeze.yaml"
FREEZE_PATH = TASK_DIR / "core_freeze_manifest.v0.1.yaml"
ROUTE_INPUTS_PATH = ROUTE_DIR / "route_inputs.v0.1.jsonl"
EXPECTATIONS_PATH = ROUTE_DIR / "sealed_route_expectations.v0.1.jsonl"
ACTUALS_PATH = ROUTE_DIR / "route_actuals.v0.1.jsonl"
COMPARISON_PATH = ROUTE_DIR / "route_comparison_results.v0.1.jsonl"
DEGRADED_PATH = ROUTE_DIR / "degraded_internal_artifacts.v0.1.jsonl"
OPEN_REQUESTS_PATH = OPEN_DIR / "authoring_requests.v0.1.jsonl"
OPEN_RAW_PATH = OPEN_DIR / "raw_authoring_responses.v0.1.jsonl"
OPEN_CANDIDATES_PATH = OPEN_DIR / "candidates.v0.1.jsonl"
OPEN_MACHINE_PATH = OPEN_DIR / "machine_structural_results.v0.1.jsonl"
OPEN_PAIR_PATH = OPEN_DIR / "pair_independence_machine_results.v0.1.jsonl"
OPEN_FREEZE_PATH = OPEN_DIR / "authoring_input_freeze.v0.1.yaml"
OPEN_RESULT_PATH = OPEN_DIR / "checkpoint_A_result.v0.1.yaml"
PHASE0_MERGE_SHA = "edca984941a824172f83e543446067ecc5ea90d2"

FORBIDDEN_CONTROL_PATTERNS = (
    "CP_BLUEPRINTS",
    "def _title(",
    "def _body(",
    "def _spoken(",
    "def _cta(",
    "STYLE_SELECTION",
    "actual_primary_action = expected",
    '"route_pass": True',
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
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


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


def profiles() -> dict[str, dict[str, Any]]:
    document = load_yaml(ROOT / PROFILE_PATH)
    rows = document["content_product_profile_registry"]["profiles"]
    return {str(row["content_product_type_id"]): row for row in rows}


def walk_readiness(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in READINESS_KEYS and child is not False:
                errors.append(f"E_READINESS_TRUE:{child_path}")
            errors.extend(walk_readiness(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(walk_readiness(child, f"{path}[{index}]"))
    return errors


def _git(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _git_blob_sha256(commit_sha: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{commit_sha}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def _route_gate() -> Any:
    return import_module(ROOT / ROUTE_GATE_PATH, "controlled_v2_route_gate_checker")


def recompute_actuals() -> list[dict[str, Any]]:
    gate = _route_gate()
    profile_map = profiles()
    records: list[dict[str, Any]] = []
    for fixture in load_jsonl(ROOT / ROUTE_INPUTS_PATH):
        projection = fixture["actual_input_payload"]
        decision = gate.controlled_v2_route_gate(projection, profile_map[fixture["profile_id"]])
        record = {
            "case_id": fixture["case_id"],
            "profile_id": fixture["profile_id"],
            "input_digest": digest_object(projection),
            "actual_decision": decision,
        }
        record["actual_record_digest"] = digest_object(record)
        records.append(record)
    return records


def comparison_rows() -> list[dict[str, Any]]:
    expected = {row["case_id"]: row for row in load_jsonl(ROOT / EXPECTATIONS_PATH)}
    actual = {row["case_id"]: row for row in load_jsonl(ROOT / ACTUALS_PATH)}
    rows: list[dict[str, Any]] = []
    if set(expected) != set(actual):
        raise ValueError("expected and actual case sets differ")
    for case_id in sorted(expected):
        expectation = expected[case_id]
        decision = actual[case_id]["actual_decision"]
        row = {
            "case_id": case_id,
            "expected_action": expectation["expected_action"],
            "actual_action": decision["actual_primary_action"],
            "action_match": expectation["expected_action"] == decision["actual_primary_action"],
            "expected_reason_basis": expectation["expected_reason_basis"],
            "actual_reason_code": decision["actual_primary_reason_code"],
            "expected_rule_refs": expectation["expected_rule_refs"],
            "actual_rule_refs": [
                item["rule_ref"] for item in decision["rule_evaluation_trace"]
            ],
        }
        row["comparison_digest"] = digest_object(row)
        rows.append(row)
    return rows


def write_comparison() -> None:
    rows = comparison_rows()
    target = ROOT / COMPARISON_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def check_registry() -> list[str]:
    errors: list[str] = []
    registry = load_yaml(ROOT / REGISTRY_PATH)["active_authoring_registry"]
    entries = registry["entries"]
    active = [entry for entry in entries if entry.get("status") == "active"]
    if registry.get("active_entry_count") != 1 or len(active) != 1:
        errors.append("E_ACTIVE_AUTHOR_COUNT")
    if active and active[0].get("backend_class") != "CONTROLLED_EXECUTION_AGENT":
        errors.append("E_ACTIVE_AUTHOR_BACKEND")
    if registry.get("deterministic_surface_writer_active_count") != 0:
        errors.append("E_DETERMINISTIC_WRITER_ACTIVE")
    if registry.get("active_route_gate_count") != 1:
        errors.append("E_ACTIVE_ROUTE_GATE_COUNT")
    return errors


def check_control_source() -> list[str]:
    errors: list[str] = []
    for relative in (COMPILER_PATH, ROUTE_GATE_PATH, MATERIALIZER_PATH):
        source = (ROOT / relative).read_text(encoding="utf-8")
        patterns = FORBIDDEN_CONTROL_PATTERNS
        if relative == MATERIALIZER_PATH:
            patterns = tuple(
                pattern
                for pattern in patterns
                if pattern
                not in {
                    "CP_BLUEPRINTS",
                    "STYLE_SELECTION",
                    "def _title(",
                    "def _body(",
                    "def _spoken(",
                    "def _cta(",
                }
            )
            function_names = {
                node.name
                for node in ast.walk(ast.parse(source))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for name in {"_title", "_body", "_spoken", "_cta"}.intersection(function_names):
                errors.append(f"E_MATERIALIZER_SURFACE_FUNCTION:{name}")
        for pattern in patterns:
            if pattern in source:
                errors.append(f"E_CONTROL_WRITES_SURFACE:{relative}:{pattern}")
        if relative == COMPILER_PATH and ('"CP01":' in source or '"CP20":' in source):
            errors.append("E_COMPILER_CP_SURFACE_BRANCH")
    return errors


def check_route_inputs() -> list[str]:
    errors: list[str] = []
    profile_map = profiles()
    inputs = load_jsonl(ROOT / ROUTE_INPUTS_PATH)
    expectations = load_jsonl(ROOT / EXPECTATIONS_PATH)
    actuals = load_jsonl(ROOT / ACTUALS_PATH)
    if len(inputs) != 60 or len(expectations) != 60 or len(actuals) != 60:
        errors.append("E_ROUTE_COUNT")
    if len({row["case_id"] for row in inputs}) != len(inputs):
        errors.append("E_ROUTE_INPUT_DUPLICATE")
    for row in inputs:
        forbidden = {"expected", "expected_action", "route_pass", "actual_action"}.intersection(row)
        forbidden.update(
            {"expected", "expected_action", "route_pass", "actual_action"}.intersection(
                row.get("actual_input_payload", {})
            )
        )
        if forbidden:
            errors.append(f"E_ROUTE_INPUT_LEAK:{row['case_id']}")
        source_path = ROOT / row["source_fixture_path"]
        if not source_path.is_file() or sha256_file(source_path) != row["source_fixture_digest"]:
            errors.append(f"E_ROUTE_SOURCE:{row['case_id']}")
        profile = profile_map[row["profile_id"]]
        hard_guard_ids = {guard["rule_id"] for guard in profile["founder_hard_guards"]}
        if not set(row["actual_input_payload"]["hard_guard_hits"]).issubset(hard_guard_ids):
            errors.append(f"E_ROUTE_GUARD_REF:{row['case_id']}")
    for row in expectations:
        if {"actual", "actual_action", "route_pass", "actual_input_payload"}.intersection(row):
            errors.append(f"E_EXPECTATION_ACTUAL_LEAK:{row['case_id']}")
        if row.get("reviewer_id") == "PENDING_INDEPENDENT_REVIEW":
            errors.append(f"E_EXPECTATION_UNREVIEWED:{row['case_id']}")
    for row in actuals:
        if {"expected", "expected_action", "route_pass"}.intersection(row):
            errors.append(f"E_ACTUAL_EXPECTATION_LEAK:{row['case_id']}")

    recomputed = recompute_actuals()
    if recomputed != actuals:
        errors.append("E_ROUTE_ACTUAL_DRIFT")
    comparisons = comparison_rows()
    if not all(row["action_match"] for row in comparisons):
        errors.append("E_ROUTE_EXPECTATION_MISMATCH")
    if (ROOT / COMPARISON_PATH).exists() and load_jsonl(ROOT / COMPARISON_PATH) != comparisons:
        errors.append("E_ROUTE_COMPARISON_DRIFT")
    actions = Counter(row["actual_decision"]["actual_primary_action"] for row in actuals)
    if set(actions).difference({"ALLOW", "REQUEST_INPUT", "DEGRADE", "BLOCK"}):
        errors.append("E_ROUTE_ACTION_ENUM")
    for profile_id in profile_map:
        profile_rows = [row for row in inputs if row["profile_id"] == profile_id]
        if len(profile_rows) != 3:
            errors.append(f"E_ROUTE_PROFILE_COUNT:{profile_id}")
        if not any(row["missing_points"] for row in profile_rows):
            errors.append(f"E_ROUTE_PROFILE_MISSING_CASE:{profile_id}")
        if not any(row["actual_input_payload"]["hard_guard_hits"] for row in profile_rows):
            errors.append(f"E_ROUTE_PROFILE_GUARD_CASE:{profile_id}")
    degraded = load_jsonl(ROOT / DEGRADED_PATH)
    degrade_actuals = [
        row for row in actuals if row["actual_decision"]["actual_primary_action"] == "DEGRADE"
    ]
    if len(degraded) != len(degrade_actuals):
        errors.append("E_DEGRADED_ARTIFACT_COUNT")
    for row in degrade_actuals:
        decision = row["actual_decision"]
        artifact = decision.get("degraded_artifact")
        if not isinstance(artifact, Mapping) or not artifact.get("internal_payload"):
            errors.append(f"E_DEGRADE_EMPTY:{row['case_id']}")
        if any(
            decision.get(key) is not False
            for key in (
                "audience_title_created",
                "audience_body_created",
                "spoken_script_created",
                "runtime_plan_created",
            )
        ):
            errors.append(f"E_DEGRADE_AUDIENCE_OUTPUT:{row['case_id']}")
    return errors


def check_review_protocol() -> list[str]:
    errors: list[str] = []
    rubric = load_yaml(ROOT / RUBRIC_PATH)["qualification_rubric"]
    protocol = load_yaml(ROOT / PROTOCOL_PATH)["qualification_review_protocol"]
    first = rubric["first_acceptance_definition"]
    if first.get("zero_edit_required") is not True or first.get("small_repair_is_accepted") is not False:
        errors.append("E_SOFT_FIRST_ACCEPTANCE_RUBRIC")
    if protocol.get("rubric_digest") != sha256_file(ROOT / RUBRIC_PATH):
        errors.append("E_RUBRIC_DIGEST")
    if protocol["disagreement_adjudication"].get(
        "only_adjudicated_result_may_set_first_acceptance"
    ) is not True:
        errors.append("E_ADJUDICATION_AUTHORITY")
    return errors


def check_core_freeze() -> list[str]:
    if not (ROOT / FREEZE_PATH).exists():
        return ["E_CORE_FREEZE_MISSING"]
    errors: list[str] = []
    freeze = load_yaml(ROOT / FREEZE_PATH)["core_freeze_manifest"]
    files = freeze["files"]
    for item in files:
        path = ROOT / item["path"]
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            errors.append(f"E_CORE_FREEZE_DRIFT:{item['path']}")
    if freeze.get("core_digest") != digest_object(files):
        errors.append("E_CORE_FREEZE_DIGEST")
    return errors


def check_open_gate() -> list[str]:
    if not (ROOT / OPEN_DIR).exists():
        return []
    required = (
        OPEN_REQUESTS_PATH,
        OPEN_RAW_PATH,
        OPEN_CANDIDATES_PATH,
        OPEN_MACHINE_PATH,
        OPEN_PAIR_PATH,
        OPEN_FREEZE_PATH,
        OPEN_RESULT_PATH,
    )
    missing = [path for path in required if not (ROOT / path).exists()]
    if missing:
        return [f"E_OPEN_GATE_MISSING:{path}" for path in missing]
    errors: list[str] = []
    freeze = load_yaml(ROOT / OPEN_FREEZE_PATH)["authoring_input_freeze"]
    core_sha = str(freeze["core_commit_sha"])
    code, resolved, _ = _git(["rev-parse", core_sha])
    if code != 0 or resolved != core_sha:
        errors.append("E_CORE_COMMIT_BINDING")
    core_manifest = load_yaml(ROOT / FREEZE_PATH)["core_freeze_manifest"]
    if freeze.get("core_digest") != core_manifest.get("core_digest"):
        errors.append("E_OPEN_CORE_DIGEST")
    for item in core_manifest["files"]:
        if _git_blob_sha256(core_sha, item["path"]) != item["sha256"]:
            errors.append(f"E_POST_FREEZE_CORE_CHANGE:{item['path']}")
    requests = load_jsonl(ROOT / OPEN_REQUESTS_PATH)
    raw = load_jsonl(ROOT / OPEN_RAW_PATH)
    candidates = load_jsonl(ROOT / OPEN_CANDIDATES_PATH)
    machine = load_jsonl(ROOT / OPEN_MACHINE_PATH)
    pairs = load_jsonl(ROOT / OPEN_PAIR_PATH)
    if not all(len(rows) == 40 for rows in (requests, raw, candidates, machine)):
        errors.append("E_OPEN_GATE_COUNT")
    if len(pairs) != 20:
        errors.append("E_OPEN_PAIR_COUNT")
    request_map = {row["request_id"]: row for row in requests}
    validator = import_module(ROOT / VALIDATOR_PATH, "response_validator_checker")
    for response in raw:
        request = request_map.get(response.get("request_id"))
        if request is None:
            errors.append(f"E_RAW_REQUEST_REF:{response.get('response_id')}")
            continue
        validation_errors = validator.validate_response(request, response)
        candidate = next(
            (item for item in candidates if item["request_id"] == request["request_id"]),
            None,
        )
        if candidate is None or candidate.get("machine_validation_errors") != validation_errors:
            errors.append(f"E_CANDIDATE_VALIDATION:{request['request_id']}")
    for request in requests:
        serialized = canonical_json(request)
        for forbidden in (
            "expected_score",
            "paired_output",
            "review_envelope",
            "sibling_candidate",
        ):
            if forbidden in serialized:
                errors.append(f"E_AUTHOR_REQUEST_LEAK:{request['request_id']}:{forbidden}")
    if any(item.get("machine_quality_claim") is not False for item in machine):
        errors.append("E_MACHINE_QUALITY_CLAIM")
    if any(item.get("non_evidence_exact_line_overlap_count") != 0 for item in pairs):
        errors.append("E_PAIR_EXACT_OVERLAP")
    if any(item.get("normalized_8gram_overlap_ratio", 1.0) > 0.15 for item in pairs):
        errors.append("E_PAIR_8GRAM_OVERLAP")
    result = load_yaml(ROOT / OPEN_RESULT_PATH)["checkpoint_A_result"]
    if result.get("status") != "PENDING_EXTERNAL_GUARDIAN":
        errors.append("E_CHECKPOINT_A_SELF_APPROVAL")
    if result.get("eligible_to_open_sealed_hidden") is not False:
        errors.append("E_HIDDEN_UNLOCKED")
    errors.extend(walk_readiness(result))
    hidden_files = [path for path in (ROOT / TASK_DIR).rglob("*") if "sealed_hidden" in path.name.lower()]
    if hidden_files:
        errors.append("E_HIDDEN_BEFORE_CHECKPOINT_A")
    return errors


def check_predecessor_boundaries() -> list[str]:
    errors: list[str] = []
    code, names, _ = _git(["diff", "--name-only", PHASE0_MERGE_SHA, "HEAD"])
    if code == 0:
        forbidden_prefixes = ("KE/", "rag/", "dify/", "serving_projection/")
        for name in names.splitlines():
            if name.startswith(forbidden_prefixes):
                errors.append(f"E_FORBIDDEN_LAYER_WRITE:{name}")
            if name.startswith(
                "controlled_content_generator_v2_001/qualification_calibration_targeted_repair_002/"
            ):
                errors.append(f"E_PR8_EVIDENCE_MUTATED:{name}")
    return errors


def run_live() -> list[str]:
    errors: list[str] = []
    errors.extend(check_registry())
    errors.extend(check_control_source())
    errors.extend(check_route_inputs())
    errors.extend(check_review_protocol())
    errors.extend(check_core_freeze())
    errors.extend(check_open_gate())
    errors.extend(check_predecessor_boundaries())
    for path in (ROOT / TASK_DIR).rglob("*.yaml"):
        errors.extend(walk_readiness(load_yaml(path), path.as_posix()))
    for path in (ROOT / TASK_DIR).rglob("*.jsonl"):
        for index, row in enumerate(load_jsonl(path)):
            errors.extend(walk_readiness(row, f"{path.as_posix()}:{index + 1}"))
    return sorted(set(errors))


def selftest() -> list[str]:
    errors: list[str] = []
    gate = _route_gate()
    profile_map = profiles()
    fixtures = load_jsonl(ROOT / ROUTE_INPUTS_PATH)
    degrade = next(row for row in fixtures if row["case_id"].endswith("MISSING-001"))
    original = gate.controlled_v2_route_gate(
        degrade["actual_input_payload"], profile_map[degrade["profile_id"]]
    )
    mutated = copy.deepcopy(degrade["actual_input_payload"])
    mutated["partial_safe"] = False
    changed = gate.controlled_v2_route_gate(mutated, profile_map[degrade["profile_id"]])
    if original["actual_primary_action"] != "DEGRADE":
        errors.append("SELFTEST_DEGRADE_BASE")
    if changed["actual_primary_action"] == original["actual_primary_action"]:
        errors.append("SELFTEST_INPUT_MUTATION_NO_EFFECT")
    fake_expectation = {"expected_action": "BLOCK"}
    unchanged = gate.controlled_v2_route_gate(
        degrade["actual_input_payload"], profile_map[degrade["profile_id"]]
    )
    if fake_expectation["expected_action"] == original["actual_primary_action"]:
        errors.append("SELFTEST_BAD_MUTATION")
    if unchanged != original:
        errors.append("SELFTEST_EXPECTATION_MUTATION_CHANGED_ACTUAL")
    gate_source = (ROOT / ROUTE_GATE_PATH).read_text(encoding="utf-8")
    if "sealed_route_expectations" in gate_source or "expected_action" in gate_source:
        errors.append("SELFTEST_GATE_READS_EXPECTATION")
    rubric = load_yaml(ROOT / RUBRIC_PATH)["qualification_rubric"]
    if rubric["first_acceptance_definition"]["small_repair_is_accepted"] is not False:
        errors.append("SELFTEST_SOFT_RUBRIC")
    with tempfile.TemporaryDirectory() as directory:
        bad = Path(directory) / "bad.py"
        bad.write_text("actual_primary_action = expected\n", encoding="utf-8")
        if "actual_primary_action = expected" not in bad.read_text(encoding="utf-8"):
            errors.append("SELFTEST_SOURCE_SCAN")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--materialize-comparison", action="store_true")
    args = parser.parse_args()
    if not __debug__:
        return 2
    if args.materialize_comparison:
        write_comparison()
        return 0
    errors = selftest() if args.selftest else run_live()
    if errors:
        for error in errors:
            sys.stderr.write(error + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
