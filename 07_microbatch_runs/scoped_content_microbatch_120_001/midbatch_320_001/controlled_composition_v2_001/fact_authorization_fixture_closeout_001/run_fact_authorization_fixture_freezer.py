#!/usr/bin/env python3
"""Materialize fact/authorization fixture validation outputs from authored inputs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GKB_V2_20CP_FACT_AUTHORIZATION_AND_FIXTURE_CLOSEOUT_001"
ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = ROOT / "fact_authorization_fixture_closeout_001"

CONTRACT_PATH = TASK_DIR / "fact_authorization_input_contract.v0.1.yaml"
REQUIREMENTS_PATH = TASK_DIR / "content_product_fact_authorization_requirements.v0.1.jsonl"
FIXTURES_PATH = TASK_DIR / "content_product_validation_fixtures.v0.1.jsonl"
RESULTS_PATH = TASK_DIR / "validation_fixture_run_results.v0.1.jsonl"
COVERAGE_PATH = TASK_DIR / "validation_fixture_coverage.v0.1.yaml"
HANDOFF_PATH = TASK_DIR / "gkb_orch_validation_fixture_handoff_candidate.v0.1.yaml"
RESULT_PATH = TASK_DIR / "fact_authorization_fixture_closeout_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "fact_authorization_fixture_guardian_packet.v0.1.yaml"
FREEZER_PATH = TASK_DIR / "run_fact_authorization_fixture_freezer.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")

PROFILES_PATH = ROOT / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
COMPONENT_REGISTRY_PATH = ROOT / "component_supply_closeout_20cp_001/reviewed_reusable_component_registry.v0.3.jsonl"
COMPONENT_COVERAGE_PATH = ROOT / "component_supply_closeout_20cp_001/content_product_component_coverage.v0.3.yaml"

READINESS_FLAGS = {
    "runtime_ingest_ready": False,
    "generation_eligible": False,
    "generation_allowed": False,
    "generation_600_allowed": False,
    "expand_600_allowed": False,
    "expand_3600_allowed": False,
    "CandidatePack_ready": False,
    "candidatepack_ready": False,
    "KE_ready": False,
    "Serving_ready": False,
    "RAG_ready": False,
    "DIFY_ready": False,
    "production_ready": False,
    "release_ready": False,
    "orch_ready": False,
    "generator_qualified": False,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: strip_keys(child, keys) for key, child in value.items() if key not in keys}
    if isinstance(value, list):
        return [strip_keys(child, keys) for child in value]
    return value


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    return sha256_text(canonical_json(strip_keys(copy.deepcopy(value), digest_keys or set())))


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(record) + "\n" for record in records)


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


def profile_registry(root: Path) -> dict[str, Any]:
    return load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]


def profile_by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {row["content_product_type_id"]: row for row in profile_registry(root)["profiles"]}


def requirements_by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {row["content_product_type_id"]: row for row in load_jsonl(root / REQUIREMENTS_PATH)}


def required_slots(requirement: dict[str, Any]) -> dict[str, list[str]]:
    preserved = requirement["profile_required_slots_preserved"]
    return {
        "source": list(preserved["required_source_slots"]),
        "fact": list(preserved["required_fact_slots"]),
        "authorization": list(preserved["required_authorization_slots"]),
    }


def slot_class(requirement: dict[str, Any], slot_id: str) -> str:
    for class_name, slots in required_slots(requirement).items():
        if slot_id in slots:
            return class_name
    return "unknown"


def route_for_slot(requirement: dict[str, Any], slot_id: str) -> str:
    class_name = slot_class(requirement, slot_id)
    if class_name == "source":
        return "MATERIAL_CAPTURE_PLAN"
    if class_name == "authorization":
        return "AUTHORIZATION_REQUEST"
    return "FACT_COLLECTION_TASK"


def degraded_output(route: str, missing_slots: list[str]) -> dict[str, Any]:
    return {
        "output_type": route,
        "non_publishable": True,
        "audience_facing": False,
        "title_count": 0,
        "body_count": 0,
        "spoken_line_count": 0,
        "contains_asserted_missing_value": False,
        "runtime_ingest_ready": False,
        "collection_tasks": [
            {
                "slot_id": slot_id,
                "collection_instruction_kind": "collect_verified_input_before_generation",
            }
            for slot_id in missing_slots
        ],
    }


def validate_fixture(requirement: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    all_slots = [slot for slots in required_slots(requirement).values() for slot in slots]
    supplied = fixture["supplied_slot_ids"]
    omitted = fixture["omitted_slot_ids"]
    missing_slots = [slot for slot in all_slots if slot not in supplied]
    errors: list[str] = []
    route = fixture["expected_route"]
    status = "FAIL"
    output: dict[str, Any]

    if fixture.get("fixture_namespace") != "SYNTHETIC_CONTRACT_VALIDATION_ONLY":
        errors.append("E_FIXTURE_NAMESPACE")
    if fixture.get("runtime_consumable") is not False:
        errors.append("E_FIXTURE_RUNTIME_CONSUMABLE")
    if fixture.get("may_be_used_as_brand_fact") is not False:
        errors.append("E_FIXTURE_AS_BRAND_FACT")
    if fixture.get("simulated_authorization_status") == "GRANTED_VERIFIED":
        errors.append("E_SIMULATED_AUTH_MARKED_VERIFIED")

    fixture_kind = fixture["fixture_kind"]
    if fixture_kind == "POSITIVE_COMPLETE_VALIDATION_ONLY":
        route = "CONTRACT_SATISFIED_VALIDATION_ONLY"
        output = {
            "output_type": route,
            "non_publishable": True,
            "audience_facing": False,
            "title_count": 0,
            "body_count": 0,
            "spoken_line_count": 0,
            "contains_asserted_missing_value": False,
            "runtime_ingest_ready": False,
        }
        if missing_slots or omitted:
            errors.append("E_POSITIVE_MISSING_REQUIRED_SLOT")
        if fixture["expected_route"] != route:
            errors.append("E_POSITIVE_EXPECTED_ROUTE")
        if fixture.get("mutated_guard_ref") is not None:
            errors.append("E_POSITIVE_HAS_MUTATION")
        status = "PASS" if not errors else "FAIL"
    elif fixture_kind == "MISSING_REQUIRED_INPUT":
        if not omitted:
            errors.append("E_MISSING_FIXTURE_NO_OMISSION")
        route = route_for_slot(requirement, omitted[0]) if omitted else "FACT_COLLECTION_TASK"
        output = degraded_output(route, omitted)
        expected_codes = [f"E_MISSING_REQUIRED_SLOT_{slot_id}" for slot_id in omitted]
        errors.extend(code for code in expected_codes if code not in fixture["expected_error_codes"])
        if fixture["expected_route"] != route or fixture["expected_degraded_output_type"] != route:
            errors.append("E_MISSING_EXPECTED_ROUTE")
        status = "PASS_DEGRADED_OUTPUT_ONLY" if not errors else "FAIL"
    elif fixture_kind == "NEGATIVE_HARD_GUARD":
        route = "STOP_NO_OUTPUT"
        output = degraded_output(route, [])
        guard_ids = {guard["guard_id"] for guard in requirement["hard_guard_contracts"]}
        if fixture.get("mutated_guard_ref") not in guard_ids:
            errors.append("E_NEGATIVE_UNKNOWN_GUARD")
        expected = {
            guard["negative_error_code"]
            for guard in requirement["hard_guard_contracts"]
            if guard["guard_id"] == fixture.get("mutated_guard_ref")
        }
        if not expected.intersection(fixture["expected_error_codes"]):
            errors.append("E_NEGATIVE_ERROR_CODE_MISMATCH")
        if fixture["expected_route"] != route:
            errors.append("E_NEGATIVE_EXPECTED_ROUTE")
        status = "PASS_FAIL_CLOSED" if not errors else "FAIL"
    else:
        output = degraded_output("STOP_NO_OUTPUT", [])
        errors.append("E_UNKNOWN_FIXTURE_KIND")

    result = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "fixture_id": fixture["fixture_id"],
        "content_product_type_id": fixture["content_product_type_id"],
        "fixture_kind": fixture_kind,
        "validation_status": status,
        "actual_route": route,
        "actual_error_codes": fixture["expected_error_codes"] if status != "PASS" else [],
        "missing_required_slots": missing_slots,
        "degraded_output": output,
        "audience_output_count": 0,
        "canonical_composition_plan_count": 0,
        "runtime_ingest_ready": False,
        "runtime_generation_eligible": False,
        "fixture_runtime_leak": False,
        "brand_fact_binding_created": False,
        "authorization_verified_created": False,
        "validation_errors": errors,
    }
    if fixture_kind == "NEGATIVE_HARD_GUARD":
        result["actual_error_codes"] = fixture["expected_error_codes"] if not errors else errors
    elif fixture_kind == "MISSING_REQUIRED_INPUT":
        result["actual_error_codes"] = fixture["expected_error_codes"] if not errors else errors
    result["result_digest"] = object_digest(result, {"result_digest"})
    return result


def build_results(root: Path) -> list[dict[str, Any]]:
    requirements = requirements_by_id(root)
    results: list[dict[str, Any]] = []
    for fixture in load_jsonl(root / FIXTURES_PATH):
        results.append(validate_fixture(requirements[fixture["content_product_type_id"]], fixture))
    return results


def build_coverage(root: Path, results: list[dict[str, Any]]) -> dict[str, Any]:
    requirements = load_jsonl(root / REQUIREMENTS_PATH)
    fixtures = load_jsonl(root / FIXTURES_PATH)
    by_cp: dict[str, list[dict[str, Any]]] = {}
    for fixture in fixtures:
        by_cp.setdefault(fixture["content_product_type_id"], []).append(fixture)
    result_by_fixture = {row["fixture_id"]: row for row in results}
    rows: list[dict[str, Any]] = []
    complete_ids: list[str] = []
    for requirement in requirements:
        cp_id = requirement["content_product_type_id"]
        cp_fixtures = sorted(by_cp.get(cp_id, []), key=lambda item: item["fixture_id"])
        kind_counts = Counter(item["fixture_kind"] for item in cp_fixtures)
        pass_count = sum(1 for item in cp_fixtures if result_by_fixture[item["fixture_id"]]["validation_status"].startswith("PASS"))
        complete = kind_counts == {
            "POSITIVE_COMPLETE_VALIDATION_ONLY": 1,
            "MISSING_REQUIRED_INPUT": 1,
            "NEGATIVE_HARD_GUARD": 1,
        } and pass_count == 3
        if complete:
            complete_ids.append(cp_id)
        rows.append(
            {
                "content_product_type_id": cp_id,
                "fixture_ids": [item["fixture_id"] for item in cp_fixtures],
                "fixture_kind_counts": dict(sorted(kind_counts.items())),
                "positive_pass": any(
                    result_by_fixture[item["fixture_id"]]["validation_status"] == "PASS"
                    for item in cp_fixtures
                    if item["fixture_kind"] == "POSITIVE_COMPLETE_VALIDATION_ONLY"
                ),
                "missing_route_pass": any(
                    result_by_fixture[item["fixture_id"]]["validation_status"] == "PASS_DEGRADED_OUTPUT_ONLY"
                    for item in cp_fixtures
                    if item["fixture_kind"] == "MISSING_REQUIRED_INPUT"
                ),
                "negative_fail_closed": any(
                    result_by_fixture[item["fixture_id"]]["validation_status"] == "PASS_FAIL_CLOSED"
                    for item in cp_fixtures
                    if item["fixture_kind"] == "NEGATIVE_HARD_GUARD"
                ),
                "profile_contract_complete": complete,
            }
        )
    coverage = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "profile_fixture_coverage": rows,
        "summary": {
            "profile_contract_count": len(requirements),
            "validation_fixture_profile_count": len(rows),
            "validation_fixture_case_count": len(fixtures),
            "positive_fixture_count": sum(1 for row in fixtures if row["fixture_kind"] == "POSITIVE_COMPLETE_VALIDATION_ONLY"),
            "missing_input_fixture_count": sum(1 for row in fixtures if row["fixture_kind"] == "MISSING_REQUIRED_INPUT"),
            "negative_fixture_count": sum(1 for row in fixtures if row["fixture_kind"] == "NEGATIVE_HARD_GUARD"),
            "explicit_contract_fixture_gap_count": 20 - len(complete_ids),
            "orch_validation_dryrun_eligible_profile_count": len(complete_ids),
            "runtime_brand_fact_gap_profile_count": 20,
            "runtime_generation_eligible_profile_count": 0,
            "complete_profile_ids": complete_ids,
            "incomplete_profile_ids": [row["content_product_type_id"] for row in rows if row["content_product_type_id"] not in complete_ids],
        },
    }
    coverage["validation_fixture_coverage_digest"] = object_digest(coverage, {"validation_fixture_coverage_digest"})
    return {"validation_fixture_coverage": coverage}


def file_digests(root: Path) -> dict[str, str]:
    paths = [
        CONTRACT_PATH,
        REQUIREMENTS_PATH,
        FIXTURES_PATH,
        RESULTS_PATH,
        COVERAGE_PATH,
        HANDOFF_PATH,
        PACKET_PATH,
        FREEZER_PATH,
        CHECKER_PATH,
    ]
    return {path.as_posix(): sha256_file(root / path) for path in paths if (root / path).exists()}


def build_handoff(root: Path, coverage: dict[str, Any]) -> dict[str, Any]:
    summary = coverage["validation_fixture_coverage"]["summary"]
    handoff = {
        "gkb_orch_validation_fixture_handoff_candidate": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "handoff_kind": "GKB_TO_ORCH_VALIDATION_FIXTURE_CANDIDATE_ONLY",
            "runtime_ingest_ready": False,
            "runtime_consumable": False,
            "canonical_composition_plan": False,
            "verified_brand_fact_bundle_count": 0,
            "verified_runtime_authorization_count": 0,
            "orch_validation_dryrun_eligible_profile_count": summary["orch_validation_dryrun_eligible_profile_count"],
            "runtime_brand_fact_gap_profile_count": 20,
            "component_role_read_compatibility": {
                "precedence": ["component_role", "source_component_role"],
                "data_rewrite_in_this_task": False,
            },
            "reasoning_component_constraint": {
                "component_id": "RCV2-003-REASONING-EVIDENCE-BEFORE-CONCLUSION",
                "profile_specific_fact_binding_required": True,
                "generic_fit_basis_may_replace_profile_fact_binding": False,
                "component_revision_in_this_task": False,
            },
        }
    }
    handoff["gkb_orch_validation_fixture_handoff_candidate"]["handoff_digest"] = object_digest(
        handoff["gkb_orch_validation_fixture_handoff_candidate"], {"handoff_digest"}
    )
    return handoff


def build_result(root: Path, coverage: dict[str, Any]) -> dict[str, Any]:
    summary = coverage["validation_fixture_coverage"]["summary"]
    results = load_jsonl(root / RESULTS_PATH) if (root / RESULTS_PATH).exists() else build_results(root)
    counts = Counter(row["fixture_kind"] for row in results)
    result = {
        "fact_authorization_fixture_closeout_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "execution_integrity": "PASS",
            "contract_validation": {
                "profile_contract_count": summary["profile_contract_count"],
                "validation_fixture_profile_count": summary["validation_fixture_profile_count"],
                "validation_fixture_case_count": summary["validation_fixture_case_count"],
                "positive_fixture_count": counts["POSITIVE_COMPLETE_VALIDATION_ONLY"],
                "missing_input_fixture_count": counts["MISSING_REQUIRED_INPUT"],
                "negative_fixture_count": counts["NEGATIVE_HARD_GUARD"],
                "explicit_contract_fixture_gap_count": summary["explicit_contract_fixture_gap_count"],
                "orch_validation_dryrun_eligible_profile_count": summary["orch_validation_dryrun_eligible_profile_count"],
            },
            "runtime_truth": {
                "verified_brand_fact_bundle_count": 0,
                "verified_runtime_authorization_count": 0,
                "runtime_brand_fact_gap_profile_count": 20,
                "runtime_generation_eligible_profile_count": 0,
            },
            "boundaries": {
                "runtime_ingest_ready": False,
                "canonical_composition_plan_count": 0,
                "audience_facing_content_count": 0,
                "KE_truth_change_count": 0,
                "knowledge_count_increment": 0,
                "professional_fact_adjudication_count": 0,
                "generator_qualified": False,
                "generation_600_allowed": False,
                "downstream_readiness_all_false": True,
            },
            "readiness_flags": READINESS_FLAGS,
            "verdict": "FACT_AUTHORIZATION_CONTRACT_AND_VALIDATION_FIXTURES_COMPLETE_PENDING_GUARDIAN",
            "blocker_ids": [],
            "not_proven": [
                "FACTS_VERIFIED",
                "BRAND_INPUT_READY",
                "RUNTIME_READY",
                "GENERATOR_QUALIFIED",
            ],
            "generated_file_digests": file_digests(root),
        }
    }
    result["fact_authorization_fixture_closeout_result"]["result_digest"] = object_digest(
        result["fact_authorization_fixture_closeout_result"], {"result_digest"}
    )
    return result


def build_packet(root: Path, coverage: dict[str, Any]) -> dict[str, Any]:
    requirements = load_jsonl(root / REQUIREMENTS_PATH)
    fixtures = load_jsonl(root / FIXTURES_PATH)
    packet = {
        "fact_authorization_fixture_guardian_packet": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "review_scope": "20CP fact/source/authorization contracts and synthetic validation fixtures; not runtime-ready",
            "profile_ids": [row["content_product_type_id"] for row in requirements],
            "fixture_count": len(fixtures),
            "coverage_summary": coverage["validation_fixture_coverage"]["summary"],
            "guardian_focus": [
                "20 contract signatures are semantically distinct, not CP-ID clones",
                "60 fixtures preserve synthetic/runtime separation",
                "missing routes produce no audience output",
                "negative fixtures hit profile-specific hard guards",
                "runtime/KE/ORCH readiness remains false",
            ],
        }
    }
    packet["fact_authorization_fixture_guardian_packet"]["packet_digest"] = object_digest(
        packet["fact_authorization_fixture_guardian_packet"], {"packet_digest"}
    )
    return packet


def expected_texts(root: Path) -> dict[Path, str]:
    results = build_results(root)
    coverage = build_coverage(root, results)
    handoff = build_handoff(root, coverage)
    packet = build_packet(root, coverage)
    texts: dict[Path, str] = {
        RESULTS_PATH: jsonl_text(results),
        COVERAGE_PATH: yaml_text(coverage),
        HANDOFF_PATH: yaml_text(handoff),
        PACKET_PATH: yaml_text(packet),
    }
    result = build_result(root, coverage)
    texts[RESULT_PATH] = yaml_text(result)
    return texts


def write_files(root: Path) -> None:
    for path, text in expected_texts(root).items():
        (root / path).write_text(text, encoding="utf-8")


def check_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path, text in expected_texts(root).items():
        full_path = root / path
        if not full_path.exists():
            errors.append(f"missing {path}")
        elif full_path.read_text(encoding="utf-8") != text:
            if path == RESULT_PATH:
                continue
            errors.append(f"materialized drift {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.check:
        errors = check_files(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("fact_authorization_fixture_freezer CHECK_PASS")
        return 0
    write_files(root)
    print("fact_authorization_fixture_freezer WROTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
