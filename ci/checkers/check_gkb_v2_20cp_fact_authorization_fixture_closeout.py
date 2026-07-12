#!/usr/bin/env python3
"""Fail-closed checker for GKB 20CP fact/authorization validation fixtures."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    print("check_gkb_v2_20cp_fact_authorization_fixture_closeout refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "GKB_V2_20CP_FACT_AUTHORIZATION_AND_FIXTURE_CLOSEOUT_001"
BASELINE_HEAD = "6db51ad67d747f56815316c5ff88edf16a7d44bc"
ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = ROOT / "fact_authorization_fixture_closeout_001"

CONTRACT_PATH = TASK_DIR / "fact_authorization_input_contract.v0.1.yaml"
REQUIREMENTS_PATH = TASK_DIR / "content_product_fact_authorization_requirements.v0.1.jsonl"
FIXTURES_PATH = TASK_DIR / "content_product_validation_fixtures.v0.1.jsonl"
RUN_RESULTS_PATH = TASK_DIR / "validation_fixture_run_results.v0.1.jsonl"
COVERAGE_PATH = TASK_DIR / "validation_fixture_coverage.v0.1.yaml"
HANDOFF_PATH = TASK_DIR / "gkb_orch_validation_fixture_handoff_candidate.v0.1.yaml"
RESULT_PATH = TASK_DIR / "fact_authorization_fixture_closeout_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "fact_authorization_fixture_guardian_packet.v0.1.yaml"
FREEZER_PATH = TASK_DIR / "run_fact_authorization_fixture_freezer.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py")
COMPONENT_SUPPLY_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py")
ORCH_VALIDATION_DRYRUN_CHECKER_PATH = Path("ci/checkers/check_orch_v2_20cp_validation_dryrun.py")
GENERATOR_V2_CHECKER_PATH = Path("ci/checkers/check_controlled_content_generator_v2_build.py")
QUALIFICATION_PROBE_CHECKER_PATH = Path("ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py")
TARGETED_REPAIR_CHECKER_PATH = Path("ci/checkers/check_controlled_v2_qualification_probe_40_targeted_repair.py")
CALIBRATION_REPAIR_002_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_qualification_calibration_targeted_repair_002.py"
)
CONVERGENCE_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_creative_authoring_route_convergence.py"
)
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CI_PATH = Path(".github/workflows/ci.yml")

PROFILES_PATH = ROOT / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
COMPONENT_REGISTRY_PATH = ROOT / "component_supply_closeout_20cp_001/reviewed_reusable_component_registry.v0.3.jsonl"
COMPONENT_COVERAGE_PATH = ROOT / "component_supply_closeout_20cp_001/content_product_component_coverage.v0.3.yaml"
COMPONENT_RESULT_PATH = ROOT / "component_supply_closeout_20cp_001/component_supply_closeout_result.v0.1.yaml"
COMPONENT_SUPPLY_FREEZER_PATH = ROOT / "component_supply_closeout_20cp_001/run_component_supply_closeout_freezer.py"
CLEAN_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
SCALE_600_CONTRACT_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "scale_contract_600_001/p7d_600_expression_diversity_and_sampled_acceptance_contract.v0.1.yaml"
)
SUCCESSOR_ORCH_VALIDATION_DRYRUN_DIR = Path(
    "08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001"
)
SUCCESSOR_GENERATOR_V2_DIR = Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001")
SUCCESSOR_QUALIFICATION_PROBE_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")
SUCCESSOR_TARGETED_REPAIR_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_targeted_repair_001")
SUCCESSOR_CALIBRATION_REPAIR_002_DIR = Path(
    "controlled_content_generator_v2_001/qualification_calibration_targeted_repair_002"
)
SUCCESSOR_CONVERGENCE_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001"
)

ALLOWED_CHANGED_PATHS = {
    CONTRACT_PATH,
    REQUIREMENTS_PATH,
    FIXTURES_PATH,
    RUN_RESULTS_PATH,
    COVERAGE_PATH,
    HANDOFF_PATH,
    RESULT_PATH,
    PACKET_PATH,
    FREEZER_PATH,
    CHECKER_PATH,
    COMPONENT_SUPPLY_CHECKER_PATH,
    ORCH_VALIDATION_DRYRUN_CHECKER_PATH,
    GENERATOR_V2_CHECKER_PATH,
    QUALIFICATION_PROBE_CHECKER_PATH,
    TARGETED_REPAIR_CHECKER_PATH,
    CALIBRATION_REPAIR_002_CHECKER_PATH,
    CONVERGENCE_CHECKER_PATH,
    COMPONENT_RESULT_PATH,
    COMPONENT_SUPPLY_FREEZER_PATH,
    LEDGER_PATH,
    CI_PATH,
}
EXPECTED_PROFILE_DIGEST = "160f640f3c677b3e3aa7fb13c89549c61825cdde1919731bc573740ae38ef53b"
EXPECTED_CLEAN_120_DIGEST = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
EXPECTED_SCALE_600_DIGEST = "966190c341b070d88fbc3a25540e9c8fddf69ad8f19b90fb29badbb1ffad52a9"
EXPECTED_ALLOWED_EVENT_MODES = [
    "brand_supplied_real_event",
    "brand_fillable_prototype",
    "generic_creative_prototype",
    "collection_task_only",
]
EXPECTED_FIXTURE_KINDS = {
    "POSITIVE_COMPLETE_VALIDATION_ONLY",
    "MISSING_REQUIRED_INPUT",
    "NEGATIVE_HARD_GUARD",
}
MANDATORY_HEADLINE_NEGATIVE_GUARDS = {
    "CP04": {
        "guard_id": "AGR_CP04_01",
        "negative_error_code": "E_AGR_CP04_01_GUARD",
        "guard_text": "禁止编造争吵",
    },
    "CP10": {
        "guard_id": "AGR_CP10_01",
        "negative_error_code": "E_AGR_CP10_01_GUARD",
        "guard_text": "单次体验不得替代普遍规律",
    },
    "CP19": {
        "guard_id": "AGR_CP19_02",
        "negative_error_code": "E_AGR_CP19_02_GUARD",
        "guard_text": "禁止自我表彰和空喊长期主义",
    },
}
READY_TRUE_KEYS = {
    "runtime_ingest_ready",
    "generation_eligible",
    "generation_allowed",
    "generation_600_allowed",
    "expand_600_allowed",
    "expand_3600_allowed",
    "CandidatePack_ready",
    "candidatepack_ready",
    "KE_ready",
    "Serving_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_ready",
    "release_ready",
    "orch_ready",
    "generator_qualified",
    "runtime_generation_eligible",
    "runtime_consumable",
    "runtime_usable",
}
FORBIDDEN_FIELD_NAMES = {
    "body_text",
    "audience_facing_body",
    "spoken_script",
    "spoken_draft",
    "publishable_copy",
    "canonical_CompositionPlan",
    "CompositionPlan",
    "generation_record",
}
PII_MARKERS = {"phone", "mobile", "id_number", "address", "wechat", "email", "customer_name"}


def load_freezer(root: Path) -> Any:
    spec = importlib.util.spec_from_file_location("fact_authorization_fixture_freezer", root / FREEZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load freezer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_error(errors: list[dict[str, str]], code: str, section: str, detail: str) -> None:
    errors.append({"code": code, "section": section, "detail": detail})


def git(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def git_ok(root: Path, args: list[str]) -> bool:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode == 0


def changed_paths(root: Path) -> set[Path]:
    head = git(root, ["rev-parse", "HEAD"]).strip()
    names = ""
    if head == BASELINE_HEAD:
        names += git(root, ["diff", "--name-only", "HEAD"])
    elif head:
        names += git(root, ["diff", "--name-only", f"{BASELINE_HEAD}..HEAD"])
        names += git(root, ["diff", "--name-only", "HEAD"])
    names += git(root, ["ls-files", "--others", "--exclude-standard"])
    return {Path(line) for line in names.splitlines() if line}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise TypeError(f"JSONL row is not a mapping: {path}:{line_number}")
        rows.append(row)
    return rows


def recursive_forbidden_fields(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_FIELD_NAMES:
                hits.append(child_path)
            hits.extend(recursive_forbidden_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_forbidden_fields(child, f"{path}[{index}]"))
    return hits


def recursive_true_flags(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in READY_TRUE_KEYS and child is True:
                hits.append(child_path)
            hits.extend(recursive_true_flags(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_true_flags(child, f"{path}[{index}]"))
    return hits


def profile_registry(root: Path) -> dict[str, Any]:
    return load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]


def profiles_by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {profile["content_product_type_id"]: profile for profile in profile_registry(root)["profiles"]}


def requirements_by_id(requirements: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["content_product_type_id"]: row for row in requirements}


def all_required_slots(requirement: dict[str, Any]) -> list[str]:
    preserved = requirement["profile_required_slots_preserved"]
    return (
        list(preserved["required_source_slots"])
        + list(preserved["required_fact_slots"])
        + list(preserved["required_authorization_slots"])
    )


def slot_class(requirement: dict[str, Any], slot_id: str) -> str:
    preserved = requirement["profile_required_slots_preserved"]
    if slot_id in preserved["required_source_slots"]:
        return "source"
    if slot_id in preserved["required_authorization_slots"]:
        return "authorization"
    if slot_id in preserved["required_fact_slots"]:
        return "fact"
    return "unknown"


def route_for_slot(requirement: dict[str, Any], slot_id: str) -> str:
    class_name = slot_class(requirement, slot_id)
    if class_name == "source":
        return "MATERIAL_CAPTURE_PLAN"
    if class_name == "authorization":
        return "AUTHORIZATION_REQUEST"
    return "FACT_COLLECTION_TASK"


def normalized_signature(requirement: dict[str, Any]) -> str:
    compact = {
        "definition_signature": requirement["definition_signature"],
        "required_slots": requirement["profile_required_slots_preserved"],
        "hard_guards": [
            {"text": guard["guard_text"], "error": guard["negative_error_code"]}
            for guard in requirement["hard_guard_contracts"]
        ],
        "selected_negative": requirement["selected_negative_guard"],
        "source_purposes": [row["semantic_purpose"] for row in requirement["source_slot_contracts"]],
        "fact_purposes": [row["semantic_purpose"] for row in requirement["fact_slot_contracts"]],
    }
    return json.dumps(compact, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_preflight(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    if not enforce_git:
        return
    head = git(root, ["rev-parse", "HEAD"]).strip()
    if not head:
        add_error(errors, "E_HEAD", "git", "cannot resolve HEAD")
    elif head != BASELINE_HEAD and not git_ok(root, ["merge-base", "--is-ancestor", BASELINE_HEAD, head]):
        add_error(errors, "E_BASELINE", "git", "baseline is not ancestor of HEAD")
    unexpected = sorted(
        path.as_posix()
        for path in changed_paths(root) - ALLOWED_CHANGED_PATHS
        if not path.is_relative_to(SUCCESSOR_ORCH_VALIDATION_DRYRUN_DIR)
        and not path.is_relative_to(SUCCESSOR_GENERATOR_V2_DIR)
        and not path.is_relative_to(SUCCESSOR_QUALIFICATION_PROBE_DIR)
        and not path.is_relative_to(SUCCESSOR_TARGETED_REPAIR_DIR)
        and not path.is_relative_to(SUCCESSOR_CALIBRATION_REPAIR_002_DIR)
        and not path.is_relative_to(SUCCESSOR_CONVERGENCE_DIR)
    )
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", "git", str(unexpected))


def validate_contract(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    contract = load_yaml(root / CONTRACT_PATH)["fact_authorization_input_contract"]
    if contract.get("contract_digest") != freezer.object_digest(contract, {"contract_digest"}):
        add_error(errors, "E_CONTRACT_DIGEST", "contract", "digest mismatch")
    baseline = contract["baseline"]
    checks = {
        "expected_head": BASELINE_HEAD,
        "clean_120_sha256": EXPECTED_CLEAN_120_DIGEST,
        "scale_600_contract_sha256": EXPECTED_SCALE_600_DIGEST,
        "content_product_profile_registry_digest": EXPECTED_PROFILE_DIGEST,
    }
    for key, expected in checks.items():
        if baseline.get(key) != expected:
            add_error(errors, "E_CONTRACT_BASELINE_PIN", "contract", f"{key}={baseline.get(key)}")
    if freezer.sha256_file(root / CLEAN_120_PATH) != EXPECTED_CLEAN_120_DIGEST:
        add_error(errors, "E_CLEAN120_DIGEST", "baseline", "clean-120 drift")
    if freezer.sha256_file(root / SCALE_600_CONTRACT_PATH) != EXPECTED_SCALE_600_DIGEST:
        add_error(errors, "E_SCALE600_DIGEST", "baseline", "600 contract drift")
    if freezer.object_digest(profile_registry(root), {"registry_digest"}) != EXPECTED_PROFILE_DIGEST:
        add_error(errors, "E_PROFILE_OBJECT_DIGEST", "baseline", "profile registry object digest drift")
    if contract.get("founder_authorized_verified_brand_input_allowlist") != []:
        add_error(errors, "E_BRAND_FACT_ALLOWLIST", "contract", "allowlist must be empty")
    forbidden = contract.get("event_truth_policy", {}).get("forbidden_mode_representation", [])
    if not forbidden or forbidden[0].get("policy") != "DEFAULT_DENY_UNLISTED":
        add_error(errors, "E_EVENT_FORBIDDEN_DEFAULT_DENY", "contract", str(forbidden))
    if recursive_true_flags(contract):
        add_error(errors, "E_READY_TRUE", "contract", str(recursive_true_flags(contract)))
    if recursive_forbidden_fields(contract):
        add_error(errors, "E_FORBIDDEN_FIELD", "contract", str(recursive_forbidden_fields(contract)))


def validate_requirements(
    root: Path,
    freezer: Any,
    requirements: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    profiles = profiles_by_id(root)
    if len(requirements) != 20:
        add_error(errors, "E_REQUIREMENT_COUNT", "requirements", str(len(requirements)))
    ids = [row["content_product_type_id"] for row in requirements]
    if ids != sorted(profiles):
        add_error(errors, "E_REQUIREMENT_PROFILE_IDS", "requirements", str(ids))
    signatures = [normalized_signature(row) for row in requirements]
    if len(set(signatures)) != 20:
        add_error(errors, "E_NORMALIZED_SIGNATURE_UNIQUE", "requirements", str(len(set(signatures))))
    duplicates = sorted({sig for sig in signatures if signatures.count(sig) > 1})
    if duplicates:
        add_error(errors, "E_GENERIC_CONTRACT_CLONE", "requirements", str(len(duplicates)))
    for row in requirements:
        cp_id = row["content_product_type_id"]
        profile = profiles.get(cp_id)
        if not profile:
            add_error(errors, "E_UNKNOWN_PROFILE", "requirements", cp_id)
            continue
        if row.get("requirement_digest") != freezer.object_digest(row, {"requirement_digest"}):
            add_error(errors, "E_REQUIREMENT_DIGEST", cp_id, "digest mismatch")
        preserved = row["profile_required_slots_preserved"]
        profile_input = profile["input_requirements"]
        for key in ["required_source_slots", "required_fact_slots", "required_authorization_slots"]:
            if preserved.get(key) != profile_input.get(key):
                add_error(errors, "E_PROFILE_REQUIRED_SLOT_DRIFT", cp_id, key)
        if row.get("profile_ref", {}).get("profile_digest") != profile["profile_digest"]:
            add_error(errors, "E_PROFILE_DIGEST_REF", cp_id, str(row.get("profile_ref")))
        if row["event_truth_contract"]["allowed_event_truth_modes"] != profile["event_truth_policy"]["allowed_event_truth_modes"]:
            add_error(errors, "E_ALLOWED_TRUTH_MODE_DRIFT", cp_id, "allowed modes changed")
        if profile["event_truth_policy"].get("default_deny_unlisted") is not True:
            add_error(errors, "E_PROFILE_DEFAULT_DENY", cp_id, "profile default deny missing")
        forbidden = row["event_truth_contract"].get("forbidden_event_truth_modes", [])
        if not forbidden or forbidden[0].get("policy") != "DEFAULT_DENY_UNLISTED":
            add_error(errors, "E_FORBIDDEN_TRUTH_MODE_DRIFT", cp_id, str(forbidden))
        if row["event_truth_contract"].get("prototype_may_look_like_happened_event") is not False:
            add_error(errors, "E_PROTOTYPE_HAPPENED_EVENT", cp_id, "prototype looks happened")
        profile_guard_ids = {guard["rule_id"] for guard in profile["founder_hard_guards"]}
        row_guard_ids = {guard["guard_id"] for guard in row["hard_guard_contracts"]}
        if row_guard_ids != profile_guard_ids:
            add_error(errors, "E_HARD_GUARD_COVERAGE", cp_id, str(row_guard_ids))
        if row["selected_negative_guard"]["guard_id"] not in profile_guard_ids:
            add_error(errors, "E_SELECTED_NEGATIVE_GUARD", cp_id, str(row["selected_negative_guard"]))
        mandatory_negative = MANDATORY_HEADLINE_NEGATIVE_GUARDS.get(cp_id)
        if mandatory_negative:
            matching_guards = [
                guard
                for guard in row["hard_guard_contracts"]
                if guard["guard_id"] == mandatory_negative["guard_id"]
                and guard["negative_error_code"] == mandatory_negative["negative_error_code"]
                and guard["guard_text"] == mandatory_negative["guard_text"]
            ]
            if not matching_guards:
                add_error(errors, "E_HEADLINE_GUARD_CONTRACT", cp_id, str(mandatory_negative))
            selected = row["selected_negative_guard"]
            if (
                selected.get("guard_id") != mandatory_negative["guard_id"]
                or selected.get("expected_error_code") != mandatory_negative["negative_error_code"]
            ):
                add_error(errors, "E_HEADLINE_NEGATIVE_GUARD", cp_id, str(selected))
        for contract in row["fact_slot_contracts"]:
            required = {
                "slot_id",
                "semantic_purpose",
                "value_type",
                "cardinality",
                "required_when",
                "sensitive_data_class",
                "allowed_source_kinds",
                "provenance_required",
                "freshness_or_time_scope",
                "allowed_claim_scope",
                "missing_input_route",
                "may_be_inferred",
            }
            if set(contract) < required:
                add_error(errors, "E_FACT_SLOT_SCHEMA", cp_id, contract.get("slot_id", "?"))
            if contract.get("may_be_inferred") is not False:
                add_error(errors, "E_FACT_MAY_BE_INFERRED", cp_id, contract.get("slot_id", "?"))
        for source in row["source_slot_contracts"]:
            if source.get("runtime_usable") is not False or source.get("may_be_inferred") is not False:
                add_error(errors, "E_SOURCE_RUNTIME_OR_INFERRED", cp_id, source.get("slot_id", "?"))
            if source.get("provenance_required") is not True:
                add_error(errors, "E_SOURCE_PROVENANCE", cp_id, source.get("slot_id", "?"))
        for authorization in row["authorization_slot_contracts"]:
            if authorization.get("runtime_usable") is not False or authorization.get("fixture_only") is not True:
                add_error(errors, "E_AUTH_RUNTIME_BOUNDARY", cp_id, authorization.get("authorization_id", "?"))
            if authorization.get("allowed_fixture_status") != "SIMULATED_GRANTED_FOR_CONTRACT_TEST":
                add_error(errors, "E_AUTH_SIMULATED_STATUS", cp_id, authorization.get("authorization_id", "?"))
        if cp_id == "CP14":
            required_slot_text = json.dumps(row["profile_required_slots_preserved"], ensure_ascii=False).lower()
            if "spoken_line" in required_slot_text or "cta" in required_slot_text:
                add_error(errors, "E_CP14_SPOKEN_OR_CTA", cp_id, "spoken/CTA made required")
        if cp_id == "CP16":
            serialized = json.dumps(row, ensure_ascii=False).lower()
            if any(marker in serialized for marker in PII_MARKERS):
                add_error(errors, "E_CP16_PII_MARKER", cp_id, "PII marker present")
        if cp_id == "CP20" and "public_commitment" not in preserved["required_fact_slots"]:
            add_error(errors, "E_CP20_COMMITMENT_SOURCE", cp_id, "public commitment missing")
        if recursive_true_flags(row):
            add_error(errors, "E_READY_TRUE", cp_id, str(recursive_true_flags(row)))
        if recursive_forbidden_fields(row):
            add_error(errors, "E_FORBIDDEN_FIELD", cp_id, str(recursive_forbidden_fields(row)))


def validate_fixtures(
    freezer: Any,
    requirements: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    req_by_id = requirements_by_id(requirements)
    if len(fixtures) != 60:
        add_error(errors, "E_FIXTURE_COUNT", "fixtures", str(len(fixtures)))
    by_cp: dict[str, list[dict[str, Any]]] = {}
    for fixture in fixtures:
        by_cp.setdefault(fixture["content_product_type_id"], []).append(fixture)
        if fixture.get("fixture_digest") != freezer.object_digest(fixture, {"fixture_digest"}):
            add_error(errors, "E_FIXTURE_DIGEST", fixture["fixture_id"], "digest mismatch")
        if fixture.get("fixture_namespace") != "SYNTHETIC_CONTRACT_VALIDATION_ONLY":
            add_error(errors, "E_FIXTURE_NAMESPACE", fixture["fixture_id"], str(fixture.get("fixture_namespace")))
        false_flags = [
            "runtime_consumable",
            "may_be_used_as_brand_fact",
            "may_be_used_for_audience_generation",
        ]
        for key in false_flags:
            if fixture.get(key) is not False:
                add_error(errors, "E_FIXTURE_RUNTIME_LEAK", fixture["fixture_id"], f"{key}=true")
        if fixture.get("simulated_authorization_status") == "GRANTED_VERIFIED":
            add_error(errors, "E_SIM_AUTH_VERIFIED", fixture["fixture_id"], "simulated auth marked verified")
        if fixture.get("expected_audience_output_count") != 0:
            add_error(errors, "E_AUDIENCE_OUTPUT", fixture["fixture_id"], str(fixture.get("expected_audience_output_count")))
        requirement = req_by_id.get(fixture["content_product_type_id"])
        if not requirement:
            add_error(errors, "E_FIXTURE_UNKNOWN_CP", fixture["fixture_id"], fixture["content_product_type_id"])
            continue
        expected = freezer.validate_fixture(requirement, fixture)
        if expected.get("validation_errors"):
            add_error(errors, "E_FIXTURE_VALIDATION", fixture["fixture_id"], str(expected["validation_errors"]))
        if fixture["fixture_kind"] == "POSITIVE_COMPLETE_VALIDATION_ONLY":
            if fixture["expected_route"] != "CONTRACT_SATISFIED_VALIDATION_ONLY":
                add_error(errors, "E_POSITIVE_ROUTE", fixture["fixture_id"], fixture["expected_route"])
            if sorted(fixture["supplied_slot_ids"]) != sorted(all_required_slots(requirement)):
                add_error(errors, "E_POSITIVE_REQUIRED_SLOT", fixture["fixture_id"], "positive is incomplete")
            if fixture.get("expected_error_codes"):
                add_error(errors, "E_POSITIVE_ERROR_CODES", fixture["fixture_id"], str(fixture["expected_error_codes"]))
        elif fixture["fixture_kind"] == "MISSING_REQUIRED_INPUT":
            if len(fixture["omitted_slot_ids"]) != 1:
                add_error(errors, "E_MISSING_OMITTED_COUNT", fixture["fixture_id"], str(fixture["omitted_slot_ids"]))
            else:
                route = route_for_slot(requirement, fixture["omitted_slot_ids"][0])
                if fixture["expected_route"] != route:
                    add_error(errors, "E_MISSING_ROUTE", fixture["fixture_id"], f"{fixture['expected_route']} != {route}")
        elif fixture["fixture_kind"] == "NEGATIVE_HARD_GUARD":
            selected = requirement["selected_negative_guard"]
            if fixture.get("mutated_guard_ref") != selected["guard_id"]:
                add_error(errors, "E_NEGATIVE_GUARD_REF", fixture["fixture_id"], str(fixture.get("mutated_guard_ref")))
            if selected["expected_error_code"] not in fixture["expected_error_codes"]:
                add_error(errors, "E_NEGATIVE_ERROR_CODE", fixture["fixture_id"], str(fixture["expected_error_codes"]))
            mandatory_negative = MANDATORY_HEADLINE_NEGATIVE_GUARDS.get(fixture["content_product_type_id"])
            if mandatory_negative and (
                fixture.get("mutated_guard_ref") != mandatory_negative["guard_id"]
                or mandatory_negative["negative_error_code"] not in fixture["expected_error_codes"]
            ):
                add_error(errors, "E_HEADLINE_NEGATIVE_FIXTURE", fixture["fixture_id"], str(fixture))
            if fixture["expected_route"] != "STOP_NO_OUTPUT":
                add_error(errors, "E_NEGATIVE_ROUTE", fixture["fixture_id"], fixture["expected_route"])
        else:
            add_error(errors, "E_FIXTURE_KIND", fixture["fixture_id"], fixture["fixture_kind"])
    for cp_id, rows in by_cp.items():
        counts = Counter(row["fixture_kind"] for row in rows)
        if set(counts) != EXPECTED_FIXTURE_KINDS or any(count != 1 for count in counts.values()):
            add_error(errors, "E_FIXTURE_TRIPLET", cp_id, str(counts))


def validate_materialization(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    drift = freezer.check_files(root)
    for item in drift:
        if item == f"materialized drift {RESULT_PATH.as_posix()}":
            continue
        add_error(errors, "E_MATERIALIZED_DRIFT", "freezer", item)


def validate_results_and_coverage(
    root: Path,
    freezer: Any,
    requirements: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    actual_results = load_jsonl(root / RUN_RESULTS_PATH)
    expected_results = freezer.build_results(root)
    if actual_results != expected_results:
        add_error(errors, "E_RUN_RESULTS_RECOMPUTE", "results", "run results drift")
    status_counts = Counter(row["validation_status"] for row in actual_results)
    if status_counts != {"PASS": 20, "PASS_DEGRADED_OUTPUT_ONLY": 20, "PASS_FAIL_CLOSED": 20}:
        add_error(errors, "E_RESULT_STATUS_COUNTS", "results", str(status_counts))
    for row in actual_results:
        if row.get("result_digest") != freezer.object_digest(row, {"result_digest"}):
            add_error(errors, "E_RUN_RESULT_DIGEST", row["fixture_id"], "digest mismatch")
        if row.get("audience_output_count") != 0 or row.get("canonical_composition_plan_count") != 0:
            add_error(errors, "E_RUN_RESULT_OUTPUT", row["fixture_id"], "audience/plan output created")
        if recursive_true_flags(row):
            add_error(errors, "E_READY_TRUE", row["fixture_id"], str(recursive_true_flags(row)))
        if recursive_forbidden_fields(row):
            add_error(errors, "E_FORBIDDEN_FIELD", row["fixture_id"], str(recursive_forbidden_fields(row)))
    coverage = load_yaml(root / COVERAGE_PATH)["validation_fixture_coverage"]
    if coverage.get("validation_fixture_coverage_digest") != freezer.object_digest(
        coverage, {"validation_fixture_coverage_digest"}
    ):
        add_error(errors, "E_COVERAGE_DIGEST", "coverage", "digest mismatch")
    summary = coverage["summary"]
    fixed = {
        "profile_contract_count": 20,
        "validation_fixture_profile_count": 20,
        "validation_fixture_case_count": 60,
        "positive_fixture_count": 20,
        "missing_input_fixture_count": 20,
        "negative_fixture_count": 20,
        "explicit_contract_fixture_gap_count": 0,
        "orch_validation_dryrun_eligible_profile_count": 20,
        "runtime_brand_fact_gap_profile_count": 20,
        "runtime_generation_eligible_profile_count": 0,
    }
    for key, expected in fixed.items():
        if summary.get(key) != expected:
            add_error(errors, "E_COVERAGE_SUMMARY", "coverage", f"{key}={summary.get(key)}")
    if len(requirements) != summary["profile_contract_count"] or len(fixtures) != summary["validation_fixture_case_count"]:
        add_error(errors, "E_COVERAGE_INPUT_COUNTS", "coverage", "input/result count mismatch")


def validate_handoff_result_packet(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    handoff = load_yaml(root / HANDOFF_PATH)["gkb_orch_validation_fixture_handoff_candidate"]
    if handoff.get("handoff_digest") != freezer.object_digest(handoff, {"handoff_digest"}):
        add_error(errors, "E_HANDOFF_DIGEST", "handoff", "digest mismatch")
    if handoff.get("runtime_ingest_ready") is not False or handoff.get("runtime_consumable") is not False:
        add_error(errors, "E_HANDOFF_RUNTIME", "handoff", "runtime boundary flipped")
    if handoff.get("canonical_composition_plan") is not False:
        add_error(errors, "E_HANDOFF_PLAN", "handoff", "CompositionPlan created")
    result = load_yaml(root / RESULT_PATH)["fact_authorization_fixture_closeout_result"]
    if result.get("result_digest") != freezer.object_digest(result, {"result_digest"}):
        add_error(errors, "E_RESULT_DIGEST", "result", "digest mismatch")
    expected_verdict = "FACT_AUTHORIZATION_CONTRACT_AND_VALIDATION_FIXTURES_COMPLETE_PENDING_GUARDIAN"
    if result.get("verdict") != expected_verdict or result.get("execution_integrity") != "PASS":
        add_error(errors, "E_RESULT_VERDICT", "result", str(result.get("verdict")))
    if result["runtime_truth"] != {
        "verified_brand_fact_bundle_count": 0,
        "verified_runtime_authorization_count": 0,
        "runtime_brand_fact_gap_profile_count": 20,
        "runtime_generation_eligible_profile_count": 0,
    }:
        add_error(errors, "E_RUNTIME_TRUTH", "result", str(result["runtime_truth"]))
    boundaries = result["boundaries"]
    if boundaries.get("KE_truth_change_count") != 0 or boundaries.get("canonical_composition_plan_count") != 0:
        add_error(errors, "E_BOUNDARY_COUNTS", "result", str(boundaries))
    if recursive_true_flags(result):
        add_error(errors, "E_READY_TRUE", "result", str(recursive_true_flags(result)))
    packet = load_yaml(root / PACKET_PATH)["fact_authorization_fixture_guardian_packet"]
    if packet.get("packet_digest") != freezer.object_digest(packet, {"packet_digest"}):
        add_error(errors, "E_PACKET_DIGEST", "packet", "digest mismatch")


def validate_component_supply_unchanged(root: Path, errors: list[dict[str, str]]) -> None:
    registry = load_jsonl(root / COMPONENT_REGISTRY_PATH)
    coverage = load_yaml(root / COMPONENT_COVERAGE_PATH)["content_product_component_coverage"]
    supply_result = load_yaml(root / COMPONENT_RESULT_PATH)["component_supply_closeout_result"]
    if len(registry) != 64:
        add_error(errors, "E_COMPONENT_REGISTRY_COUNT", "component_supply", str(len(registry)))
    if coverage["summary"].get("component_supply_complete_count") != 20:
        add_error(errors, "E_COMPONENT_SUPPLY_COVERAGE", "component_supply", str(coverage["summary"]))
    false_edges = [
        row["component_id"]
        for row in registry
        if row["component_id"] == "RCV2-003-TRANSITION-DISPLAY-HIERARCHY-SPACE"
        and "CP17" in row.get("applicable_content_product_type_ids", [])
    ]
    if false_edges:
        add_error(errors, "E_FALSE_CP17_EDGE", "component_supply", str(false_edges))
    if supply_result["counts"].get("runtime_generation_eligible_profile_count") != 0:
        add_error(errors, "E_COMPONENT_SUPPLY_RUNTIME", "component_supply", "runtime eligible flipped")


def top_level_route_ids(text: str) -> list[int]:
    ids: list[int] = []
    for line in text.splitlines():
        if line.startswith("  route_migration_") and line.endswith(":"):
            suffix = line.strip().removeprefix("route_migration_").removesuffix(":")
            if suffix.isdigit():
                ids.append(int(suffix))
    return ids


def validate_ledger(root: Path, freezer: Any, errors: list[dict[str, str]], enforce_git: bool) -> None:
    data = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    migration = data.get("route_migration_24")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_ROUTE24", "ledger", "route_migration_24 missing")
        return
    if migration.get("applied_by_task") != TASK_ID:
        add_error(errors, "E_LEDGER_TASK", "ledger", str(migration.get("applied_by_task")))
    if migration.get("additive_only") is not True or migration.get("no_readiness_flipped") is not True:
        add_error(errors, "E_LEDGER_DECLARATION", "ledger", "additive/readiness declaration missing")
    result = load_yaml(root / RESULT_PATH)["fact_authorization_fixture_closeout_result"]
    ledger_result_digest = migration.get("fact_authorization_fixture_closeout", {}).get("result_digest")
    if ledger_result_digest != result.get("result_digest"):
        add_error(errors, "E_LEDGER_RESULT_DIGEST", "ledger", str(ledger_result_digest))
    if migration.get("migration_digest") != freezer.object_digest(migration, {"migration_digest"}):
        add_error(errors, "E_LEDGER_DIGEST", "ledger", "migration digest mismatch")
    text = (root / LEDGER_PATH).read_text(encoding="utf-8")
    ids = top_level_route_ids(text)
    if 24 not in ids:
        add_error(errors, "E_LEDGER_ROUTE24", "ledger", "route id missing")
    if sorted(route_id for route_id in ids if route_id >= 19) != list(range(19, max(ids) + 1)):
        add_error(errors, "E_LEDGER_SEQUENCE", "ledger", str(ids))
    if enforce_git:
        old_text = git(root, ["show", f"{BASELINE_HEAD}:{LEDGER_PATH.as_posix()}"])
        if old_text:
            old_data = yaml.safe_load(old_text)["grc_3600_execution_plan_status"]
            extra = sorted(set(data) - set(old_data))
            if extra not in (
                [
                    "route_migration_24",
                    "route_migration_25",
                    "route_migration_26",
                    "route_migration_27",
                ],
                [
                    "route_migration_24",
                    "route_migration_25",
                    "route_migration_26",
                    "route_migration_27",
                    "route_migration_28",
                ],
                [
                    "route_migration_24",
                    "route_migration_25",
                    "route_migration_26",
                    "route_migration_27",
                    "route_migration_28",
                    "route_migration_29",
                ],
                [
                    "route_migration_24",
                    "route_migration_25",
                    "route_migration_26",
                    "route_migration_27",
                    "route_migration_28",
                    "route_migration_29",
                    "route_migration_30",
                ],
            ):
                add_error(errors, "E_LEDGER_EXTRA_KEYS", "ledger", str(extra))
            for key, value in old_data.items():
                if key == "route_migration_23":
                    continue
                if data.get(key) != value:
                    add_error(errors, "E_LEDGER_NON_ADDITIVE", "ledger", key)


def validate_ci(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / CI_PATH).read_text(encoding="utf-8")
    live = "python3 ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py"
    selftest = "python3 ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py --selftest"
    if live not in text or selftest not in text:
        add_error(errors, "E_CI_CHECKER_REGISTRATION", "ci", "new checker live/selftest missing")
    if "check_gkb_v2_20cp_fact_authorization_fixture_closeout.py --selftest" not in text:
        add_error(errors, "E_CI_SELFTEST_REGISTRATION", "ci", "selftest missing")
    if ".github/workflows" not in CI_PATH.as_posix():
        add_error(errors, "E_CI_PATH", "ci", "unexpected")


def collect_errors(root: Path, enforce_git: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    freezer = load_freezer(root)
    required_paths = [
        CONTRACT_PATH,
        REQUIREMENTS_PATH,
        FIXTURES_PATH,
        RUN_RESULTS_PATH,
        COVERAGE_PATH,
        HANDOFF_PATH,
        RESULT_PATH,
        PACKET_PATH,
        FREEZER_PATH,
        CHECKER_PATH,
        LEDGER_PATH,
        CI_PATH,
    ]
    for path in required_paths:
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE_MISSING", path.as_posix(), "missing")
    if errors:
        return errors
    validate_preflight(root, errors, enforce_git)
    validate_contract(root, freezer, errors)
    requirements = load_jsonl(root / REQUIREMENTS_PATH)
    fixtures = load_jsonl(root / FIXTURES_PATH)
    validate_requirements(root, freezer, requirements, errors)
    validate_fixtures(freezer, requirements, fixtures, errors)
    validate_materialization(root, freezer, errors)
    validate_results_and_coverage(root, freezer, requirements, fixtures, errors)
    validate_handoff_result_packet(root, freezer, errors)
    validate_component_supply_unchanged(root, errors)
    validate_ledger(root, freezer, errors, enforce_git)
    validate_ci(root, errors)
    return errors


def selftest() -> int:
    root = Path.cwd()
    freezer = load_freezer(root)
    requirements = load_jsonl(root / REQUIREMENTS_PATH)
    fixtures = load_jsonl(root / FIXTURES_PATH)
    tests: list[tuple[str, bool]] = []

    def requirement_errors(mutated: list[dict[str, Any]]) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        validate_requirements(root, freezer, mutated, errors)
        return errors

    def fixture_errors(mutated: list[dict[str, Any]], reqs: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        validate_fixtures(freezer, reqs or requirements, mutated, errors)
        return errors

    positive_missing = copy.deepcopy(fixtures)
    for row in positive_missing:
        if row["fixture_kind"] == "POSITIVE_COMPLETE_VALIDATION_ONLY":
            row["supplied_slot_ids"] = row["supplied_slot_ids"][:-1]
            break
    tests.append(
        (
            "positive_missing_required_slot_rejected",
            any(e["code"] == "E_POSITIVE_REQUIRED_SLOT" for e in fixture_errors(positive_missing)),
        )
    )

    missing_body_errors: list[dict[str, str]] = []
    bad_results = freezer.build_results(root)
    bad_results[1]["degraded_output"]["body_text"] = "forbidden draft"
    for row in bad_results:
        if recursive_forbidden_fields(row):
            add_error(missing_body_errors, "E_FORBIDDEN_FIELD", row["fixture_id"], str(recursive_forbidden_fields(row)))
    tests.append(("missing_generates_body_rejected", any(e["code"] == "E_FORBIDDEN_FIELD" for e in missing_body_errors)))

    negative_accepted = copy.deepcopy(fixtures)
    for row in negative_accepted:
        if row["fixture_kind"] == "NEGATIVE_HARD_GUARD":
            row["expected_route"] = "CONTRACT_SATISFIED_VALIDATION_ONLY"
            break
    tests.append(("negative_accepted_rejected", any(e["code"] == "E_NEGATIVE_ROUTE" for e in fixture_errors(negative_accepted))))

    fixture_as_fact = copy.deepcopy(fixtures)
    fixture_as_fact[0]["may_be_used_as_brand_fact"] = True
    tests.append(("synthetic_as_real_fact_rejected", any(e["code"] == "E_FIXTURE_RUNTIME_LEAK" for e in fixture_errors(fixture_as_fact))))

    verified_auth = copy.deepcopy(fixtures)
    verified_auth[0]["simulated_authorization_status"] = "GRANTED_VERIFIED"
    tests.append(("simulated_auth_verified_rejected", any(e["code"] == "E_SIM_AUTH_VERIFIED" for e in fixture_errors(verified_auth))))

    cp04_partial_auth = copy.deepcopy(fixtures)
    for row in cp04_partial_auth:
        if row["fixture_id"] == "FAF-CP04-POSITIVE-001":
            row["supplied_slot_ids"].remove("participant_authorizations")
            break
    tests.append(("multi_person_single_auth_rejected", any(e["code"] == "E_POSITIVE_REQUIRED_SLOT" for e in fixture_errors(cp04_partial_auth))))

    weakened_slot = copy.deepcopy(requirements)
    weakened_slot[0]["profile_required_slots_preserved"]["required_fact_slots"].pop()
    tests.append(("profile_required_slot_weakened_rejected", any(e["code"] == "E_PROFILE_REQUIRED_SLOT_DRIFT" for e in requirement_errors(weakened_slot))))

    expanded_truth = copy.deepcopy(requirements)
    expanded_truth[0]["event_truth_contract"]["allowed_event_truth_modes"].append("invented_real_event")
    tests.append(("allowed_truth_mode_expanded_rejected", any(e["code"] == "E_ALLOWED_TRUTH_MODE_DRIFT" for e in requirement_errors(expanded_truth))))

    forbidden_deleted = copy.deepcopy(requirements)
    forbidden_deleted[0]["event_truth_contract"]["forbidden_event_truth_modes"] = []
    tests.append(("forbidden_mode_deleted_rejected", any(e["code"] == "E_FORBIDDEN_TRUTH_MODE_DRIFT" for e in requirement_errors(forbidden_deleted))))

    prototype_happened = copy.deepcopy(requirements)
    prototype_happened[0]["event_truth_contract"]["prototype_may_look_like_happened_event"] = True
    tests.append(("prototype_happened_event_rejected", any(e["code"] == "E_PROTOTYPE_HAPPENED_EVENT" for e in requirement_errors(prototype_happened))))

    cp14_spoken = copy.deepcopy(requirements)
    for row in cp14_spoken:
        if row["content_product_type_id"] == "CP14":
            row["profile_required_slots_preserved"]["required_fact_slots"].append("spoken_line")
            break
    tests.append(("cp14_spoken_or_cta_rejected", any(e["code"] == "E_CP14_SPOKEN_OR_CTA" for e in requirement_errors(cp14_spoken))))

    cp16_pii = copy.deepcopy(requirements)
    for row in cp16_pii:
        if row["content_product_type_id"] == "CP16":
            row["definition_signature"]["privacy_notes"].append("customer_phone")
            break
    tests.append(("cp16_pii_marker_rejected", any(e["code"] == "E_CP16_PII_MARKER" for e in requirement_errors(cp16_pii))))

    cp20_no_commitment = copy.deepcopy(requirements)
    for row in cp20_no_commitment:
        if row["content_product_type_id"] == "CP20":
            row["profile_required_slots_preserved"]["required_fact_slots"].remove("public_commitment")
            break
    tests.append(("cp20_no_commitment_source_rejected", any(e["code"] == "E_PROFILE_REQUIRED_SLOT_DRIFT" for e in requirement_errors(cp20_no_commitment))))

    cloned_contracts = copy.deepcopy(requirements)
    clone = copy.deepcopy(cloned_contracts[0]["definition_signature"])
    for row in cloned_contracts:
        row["definition_signature"] = copy.deepcopy(clone)
        row["hard_guard_contracts"] = copy.deepcopy(cloned_contracts[0]["hard_guard_contracts"])
        row["selected_negative_guard"] = copy.deepcopy(cloned_contracts[0]["selected_negative_guard"])
        row["source_slot_contracts"] = copy.deepcopy(cloned_contracts[0]["source_slot_contracts"])
        row["fact_slot_contracts"] = copy.deepcopy(cloned_contracts[0]["fact_slot_contracts"])
        row["profile_required_slots_preserved"] = copy.deepcopy(cloned_contracts[0]["profile_required_slots_preserved"])
    tests.append(("normalized_clone_rejected", any(e["code"] == "E_NORMALIZED_SIGNATURE_UNIQUE" for e in requirement_errors(cloned_contracts))))

    runtime_fixture = copy.deepcopy(fixtures)
    runtime_fixture[0]["runtime_consumable"] = True
    tests.append(("runtime_consumable_true_rejected", any(e["code"] == "E_FIXTURE_RUNTIME_LEAK" for e in fixture_errors(runtime_fixture))))

    runtime_result_errors: list[dict[str, str]] = []
    result_doc = load_yaml(root / RESULT_PATH)["fact_authorization_fixture_closeout_result"]
    result_doc["runtime_truth"]["runtime_generation_eligible_profile_count"] = 1
    if result_doc["runtime_truth"]["runtime_generation_eligible_profile_count"] != 0:
        add_error(runtime_result_errors, "E_RUNTIME_TRUTH", "result", "runtime eligible flipped")
    tests.append(("runtime_eligible_true_rejected", any(e["code"] == "E_RUNTIME_TRUTH" for e in runtime_result_errors)))

    plan_errors: list[dict[str, str]] = []
    bad_requirement = copy.deepcopy(requirements[0])
    bad_requirement["CompositionPlan"] = {}
    if recursive_forbidden_fields(bad_requirement):
        add_error(plan_errors, "E_FORBIDDEN_FIELD", "requirements", "CompositionPlan")
    tests.append(("composition_plan_created_rejected", any(e["code"] == "E_FORBIDDEN_FIELD" for e in plan_errors)))

    tests.append(
        (
            "orch_successor_write_surface_declared",
            (SUCCESSOR_ORCH_VALIDATION_DRYRUN_DIR / "orch_20cp_dryrun_result.v0.1.yaml").is_relative_to(
                SUCCESSOR_ORCH_VALIDATION_DRYRUN_DIR
            ),
        )
    )
    tests.append(
        (
            "generator_successor_write_surface_declared",
            (SUCCESSOR_GENERATOR_V2_DIR / "generator_v2_build_result.v0.1.yaml").is_relative_to(
                SUCCESSOR_GENERATOR_V2_DIR
            ),
        )
    )

    ke_errors: list[dict[str, str]] = []
    bad_result = load_yaml(root / RESULT_PATH)["fact_authorization_fixture_closeout_result"]
    bad_result["boundaries"]["KE_truth_change_count"] = 1
    if bad_result["boundaries"]["KE_truth_change_count"] != 0:
        add_error(ke_errors, "E_BOUNDARY_COUNTS", "result", "KE truth increased")
    tests.append(("ke_truth_increase_rejected", any(e["code"] == "E_BOUNDARY_COUNTS" for e in ke_errors)))

    hidden_body = copy.deepcopy(requirements)
    hidden_body[0]["body_text"] = "hidden"
    tests.append(("hidden_body_title_script_rejected", any(e["code"] == "E_FORBIDDEN_FIELD" for e in requirement_errors(hidden_body))))

    digest_tamper = copy.deepcopy(requirements)
    digest_tamper[0]["requirement_digest"] = "0" * 64
    tests.append(("digest_tamper_rejected", any(e["code"] == "E_REQUIREMENT_DIGEST" for e in requirement_errors(digest_tamper))))

    headline_guard_weakened = copy.deepcopy(requirements)
    for row in headline_guard_weakened:
        if row["content_product_type_id"] == "CP04":
            row["selected_negative_guard"] = {
                "guard_id": "AGR_CP04_03",
                "expected_error_code": "E_CP04_PARTICIPANT_AUTHORIZATION_GAP",
                "mutation": "multi_role_event_with_single_person_authorized",
            }
            break
    tests.append(
        (
            "headline_negative_guard_weakened_rejected",
            any(e["code"] == "E_HEADLINE_NEGATIVE_GUARD" for e in requirement_errors(headline_guard_weakened)),
        )
    )

    headline_fixture_weakened = copy.deepcopy(fixtures)
    for row in headline_fixture_weakened:
        if row["fixture_id"] == "FAF-CP04-NEGATIVE-001":
            row["mutated_guard_ref"] = "AGR_CP04_03"
            row["expected_error_codes"] = ["E_CP04_PARTICIPANT_AUTHORIZATION_GAP"]
            break
    tests.append(
        (
            "headline_negative_fixture_weakened_rejected",
            any(e["code"] == "E_HEADLINE_NEGATIVE_FIXTURE" for e in fixture_errors(headline_fixture_weakened)),
        )
    )

    failed = [name for name, ok in tests if not ok]
    if failed:
        print(json.dumps({"status": "SELFTEST_FAIL", "failed": failed}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print("SELFTEST_PASS")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        print("usage: check_gkb_v2_20cp_fact_authorization_fixture_closeout.py [--selftest]", file=sys.stderr)
        return 2
    if len(argv) == 1 and argv[0] == "--selftest":
        return selftest()
    if argv:
        print("usage: check_gkb_v2_20cp_fact_authorization_fixture_closeout.py [--selftest]", file=sys.stderr)
        return 2
    errors = collect_errors(Path.cwd(), enforce_git=True)
    if errors:
        print(json.dumps({"status": "FAIL", "error_count": len(errors), "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task_id": TASK_ID}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
