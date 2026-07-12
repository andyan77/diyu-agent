#!/usr/bin/env python3
"""Fail-closed checker for ORCH 20CP synthetic validation dry-run."""

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
    print("check_orch_v2_20cp_validation_dryrun refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "ORCH_V2_CANONICAL_COMPOSITION_PLAN_20CP_DRYRUN_001"
BASELINE_HEAD = "6253e3d1661cd46945a3443de54ac55df5b7d746"
GKB_ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = Path("08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001")
FREEZER_PATH = TASK_DIR / "run_orch_20cp_validation_dryrun_freezer.py"
CONTRACT_PATH = TASK_DIR / "orch_validation_plan_contract.v0.1.yaml"
REQUESTS_PATH = TASK_DIR / "orch_validation_requests.v0.1.jsonl"
DECISIONS_PATH = TASK_DIR / "orch_dryrun_decisions.v0.1.jsonl"
PLANS_PATH = TASK_DIR / "orch_validation_canonical_plans.v0.1.jsonl"
SELECTION_AUDIT_PATH = TASK_DIR / "orch_component_selection_audit.v0.1.jsonl"
COVERAGE_PATH = TASK_DIR / "orch_20cp_dryrun_coverage.v0.1.yaml"
RESULT_PATH = TASK_DIR / "orch_20cp_dryrun_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "orch_guardian_review_packet.v0.1.yaml"
CHECKER_PATH = Path("ci/checkers/check_orch_v2_20cp_validation_dryrun.py")
CI_PATH = Path(".github/workflows/ci.yml")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")

COMPONENT_SUPPLY_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py")
FACT_AUTH_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py")
GENERATOR_V2_CHECKER_PATH = Path("ci/checkers/check_controlled_content_generator_v2_build.py")
QUALIFICATION_PROBE_CHECKER_PATH = Path("ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py")
COMPONENT_SUPPLY_RESULT_PATH = (
    GKB_ROOT / "component_supply_closeout_20cp_001/component_supply_closeout_result.v0.1.yaml"
)
COMPONENT_SUPPLY_FREEZER_PATH = (
    GKB_ROOT / "component_supply_closeout_20cp_001/run_component_supply_closeout_freezer.py"
)
FACT_AUTH_RESULT_PATH = (
    GKB_ROOT / "fact_authorization_fixture_closeout_001/fact_authorization_fixture_closeout_result.v0.1.yaml"
)
FACT_AUTH_FREEZER_PATH = (
    GKB_ROOT / "fact_authorization_fixture_closeout_001/run_fact_authorization_fixture_freezer.py"
)
SUCCESSOR_GENERATOR_V2_DIR = Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001")
SUCCESSOR_QUALIFICATION_PROBE_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")

PLAN_NAMESPACE = "fixture://gkb-v2/orch-dryrun/"
EXPECTED_PROFILE_OBJECT_DIGEST = "160f640f3c677b3e3aa7fb13c89549c61825cdde1919731bc573740ae38ef53b"
EXPECTED_PROFILE_FILE_SHA256 = "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056"
EXPECTED_COMPONENT_REGISTRY_SHA256 = "e5a3f31a9017a39e51ad409531e26b1e910e8e2effb34a4a24dab5fd11105bb1"
EXPECTED_COMPONENT_COVERAGE_SHA256 = "374cb796018d8d5e316e234db747218a0bb61a3574d1b71dcd5151e53bbe6b81"
EXPECTED_FACT_REQUIREMENTS_SHA256 = "e59f7e187d78477b6ec587dfe1df176aeb8b08ef94972ae0ef09273c5c7e6f84"
EXPECTED_VALIDATION_FIXTURES_SHA256 = "bff74e6fac3fe85733fc6d094a81d14af3c303aa0a003e7dc7776cc034043697"
EXPECTED_FACT_RESULT_SHA256 = "15c352136cb71545254cd2d593f50ddb8d54524de4e8d61a855370181281e5c3"

ALLOWED_CHANGED_PATHS = {
    FREEZER_PATH,
    CONTRACT_PATH,
    REQUESTS_PATH,
    DECISIONS_PATH,
    PLANS_PATH,
    SELECTION_AUDIT_PATH,
    COVERAGE_PATH,
    RESULT_PATH,
    PACKET_PATH,
    CHECKER_PATH,
    COMPONENT_SUPPLY_CHECKER_PATH,
    FACT_AUTH_CHECKER_PATH,
    GENERATOR_V2_CHECKER_PATH,
    QUALIFICATION_PROBE_CHECKER_PATH,
    COMPONENT_SUPPLY_RESULT_PATH,
    COMPONENT_SUPPLY_FREEZER_PATH,
    FACT_AUTH_RESULT_PATH,
    FACT_AUTH_FREEZER_PATH,
    LEDGER_PATH,
    CI_PATH,
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
    "runtime_authoritative",
    "production_executable",
    "dify_consumable",
    "audience_generation_allowed",
    "audience_facing_output_allowed",
}
FORBIDDEN_CONTENT_FIELD_NAMES = {
    "audience_facing_body",
    "body",
    "body_text",
    "copy_text",
    "draft_text",
    "generated_text",
    "publishable_copy",
    "spoken_draft",
    "spoken_line",
    "spoken_line_payload",
    "spoken_script",
    "title",
    "title_text",
    "CTA_payload",
    "cta_payload",
    "canonical_CompositionPlan",
    "runtime_CompositionPlan",
    "production_CompositionPlan",
    "CompositionPlan",
}
COMPONENT_PAYLOAD_FIELD_NAMES = {
    "abstract_payload",
    "candidate_payload",
    "evidence_spans",
    "payload",
    "reusable_mechanism",
}


def load_freezer(root: Path) -> Any:
    spec = importlib.util.spec_from_file_location("orch_validation_freezer", root / FREEZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load ORCH freezer")
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


def unwrap(record: dict[str, Any], key: str) -> dict[str, Any]:
    wrapped = record.get(key)
    if not isinstance(wrapped, dict):
        raise TypeError(f"record missing wrapper {key}")
    return wrapped


def recursive_hits(value: Any, names: set[str], path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in names:
                hits.append(child_path)
            hits.extend(recursive_hits(child, names, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_hits(child, names, f"{path}[{index}]"))
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
        if not path.is_relative_to(SUCCESSOR_GENERATOR_V2_DIR)
        and not path.is_relative_to(SUCCESSOR_QUALIFICATION_PROBE_DIR)
    )
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", "git", str(unexpected))


def validate_input_digests(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    contract = load_yaml(root / CONTRACT_PATH)["orch_validation_plan_contract"]
    baseline = contract["baseline"]
    expected = {
        "expected_head": BASELINE_HEAD,
        "content_product_profile_registry_object_digest": EXPECTED_PROFILE_OBJECT_DIGEST,
        "content_product_profile_file_sha256": EXPECTED_PROFILE_FILE_SHA256,
        "component_registry_sha256": EXPECTED_COMPONENT_REGISTRY_SHA256,
        "component_coverage_sha256": EXPECTED_COMPONENT_COVERAGE_SHA256,
        "fact_authorization_requirements_sha256": EXPECTED_FACT_REQUIREMENTS_SHA256,
        "validation_fixtures_sha256": EXPECTED_VALIDATION_FIXTURES_SHA256,
        "fact_authorization_result_sha256": EXPECTED_FACT_RESULT_SHA256,
    }
    for key, value in expected.items():
        if baseline.get(key) != value:
            add_error(errors, "E_BASELINE_PIN", "contract", f"{key}={baseline.get(key)}")
    profile_registry = freezer.profile_registry(root)
    actual = {
        "content_product_profile_registry_object_digest": freezer.object_digest(
            profile_registry, {"registry_digest"}
        ),
        "content_product_profile_file_sha256": freezer.sha256_file(root / freezer.PROFILES_PATH),
        "component_registry_sha256": freezer.sha256_file(root / freezer.COMPONENT_REGISTRY_PATH),
        "component_coverage_sha256": freezer.sha256_file(root / freezer.COMPONENT_COVERAGE_PATH),
        "fact_authorization_requirements_sha256": freezer.sha256_file(root / freezer.FACT_REQUIREMENTS_PATH),
        "validation_fixtures_sha256": freezer.sha256_file(root / freezer.VALIDATION_FIXTURES_PATH),
    }
    # The fact result file may receive digest-metadata compatibility updates in this task. Its
    # pinned byte hash remains the contract boundary in the ORCH contract itself.
    for key, value in actual.items():
        if value != expected[key]:
            add_error(errors, "E_INPUT_DIGEST", "baseline", f"{key}={value}")
    if contract.get("contract_digest") != freezer.object_digest(contract, {"contract_digest"}):
        add_error(errors, "E_CONTRACT_DIGEST", "contract", "digest mismatch")
    ownership = contract["ownership"]
    if ownership.get("ORCH_owns_validation_plan") is not True or ownership.get("GKB_may_create_ORCH_plan") is not False:
        add_error(errors, "E_OWNERSHIP", "contract", str(ownership))
    namespace = contract["namespace_policy"]
    if namespace.get("canonical_validation_composition_plan_count") != 20:
        add_error(errors, "E_VALIDATION_PLAN_COUNT", "contract", str(namespace))
    for key in [
        "canonical_composition_plan_count",
        "canonical_runtime_composition_plan_count",
        "canonical_production_composition_plan_count",
    ]:
        if namespace.get(key) != 0:
            add_error(errors, "E_RUNTIME_PLAN_NAMESPACE", "contract", f"{key}={namespace.get(key)}")
    synthetic = contract["synthetic_policy"]
    if synthetic.get("source_ref_prefix") != PLAN_NAMESPACE:
        add_error(errors, "E_SYNTHETIC_PREFIX", "contract", str(synthetic))
    if synthetic.get("authorization_status") != "SIMULATED_GRANTED_FOR_CONTRACT_TEST":
        add_error(errors, "E_SYNTHETIC_AUTH", "contract", str(synthetic))


def fixture_maps(root: Path, freezer: Any) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    requirements = {row["content_product_type_id"]: row for row in freezer.load_jsonl(root / freezer.FACT_REQUIREMENTS_PATH)}
    fixtures = {row["fixture_id"]: row for row in freezer.load_jsonl(root / freezer.VALIDATION_FIXTURES_PATH)}
    return requirements, fixtures


def profiles_by_id(root: Path, freezer: Any) -> dict[str, dict[str, Any]]:
    return freezer.profiles_by_id(root)


def component_by_id(root: Path, freezer: Any) -> dict[str, dict[str, Any]]:
    return {row["component_id"]: row for row in freezer.components(root)}


def validate_requests(
    root: Path,
    freezer: Any,
    requests: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    requirements, fixtures = fixture_maps(root, freezer)
    profiles = profiles_by_id(root, freezer)
    rows = [unwrap(row, "orch_validation_request") for row in requests]
    if len(rows) != 60:
        add_error(errors, "E_REQUEST_COUNT", "requests", str(len(rows)))
    counts = Counter(row["fixture_kind"] for row in rows)
    if counts != {
        "POSITIVE_COMPLETE_VALIDATION_ONLY": 20,
        "MISSING_REQUIRED_INPUT": 20,
        "NEGATIVE_HARD_GUARD": 20,
    }:
        add_error(errors, "E_REQUEST_KIND_COUNTS", "requests", str(counts))
    for row in rows:
        fixture = fixtures.get(row["fixture_id"])
        requirement = requirements.get(row["content_product_type_id"])
        profile = profiles.get(row["content_product_type_id"])
        if not fixture or not requirement or not profile:
            add_error(errors, "E_REQUEST_LINEAGE", row.get("request_id", "?"), "missing fixture/profile/requirement")
            continue
        if row.get("request_digest") != freezer.object_digest(row, {"request_digest"}):
            add_error(errors, "E_REQUEST_DIGEST", row["request_id"], "digest mismatch")
        if row.get("fixture_digest") != fixture["fixture_digest"]:
            add_error(errors, "E_REQUEST_FIXTURE_DIGEST", row["request_id"], str(row.get("fixture_digest")))
        if row.get("fact_authorization_contract_digest") != requirement["requirement_digest"]:
            add_error(errors, "E_REQUEST_CONTRACT_DIGEST", row["request_id"], str(row.get("fact_authorization_contract_digest")))
        if row.get("profile_ref", {}).get("profile_digest") != profile["profile_digest"]:
            add_error(errors, "E_REQUEST_PROFILE_DIGEST", row["request_id"], str(row.get("profile_ref")))
        if row.get("requested_plan_namespace") != "SYNTHETIC_CONTRACT_VALIDATION_ONLY":
            add_error(errors, "E_REQUEST_NAMESPACE", row["request_id"], str(row.get("requested_plan_namespace")))
        if recursive_true_flags(row):
            add_error(errors, "E_READY_TRUE", row["request_id"], str(recursive_true_flags(row)))


def validate_decisions(
    root: Path,
    freezer: Any,
    decisions: list[dict[str, Any]],
    plan_ids: set[str],
    errors: list[dict[str, str]],
) -> None:
    _, fixtures = fixture_maps(root, freezer)
    rows = [unwrap(row, "orch_dryrun_decision") for row in decisions]
    if len(rows) != 60:
        add_error(errors, "E_DECISION_COUNT", "decisions", str(len(rows)))
    routes = Counter(row["resolved_route"] for row in rows)
    if routes["VALIDATION_COMPOSITION_PLAN_CREATED"] != 20 or routes["HARD_GUARD_REJECTED"] != 20:
        add_error(errors, "E_DECISION_ROUTE_COUNTS", "decisions", str(routes))
    for row in rows:
        fixture = fixtures.get(row["fixture_id"])
        if not fixture:
            add_error(errors, "E_DECISION_FIXTURE", row.get("decision_id", "?"), str(row.get("fixture_id")))
            continue
        if row.get("decision_digest") != freezer.object_digest(row, {"decision_digest"}):
            add_error(errors, "E_DECISION_DIGEST", row["decision_id"], "digest mismatch")
        if row.get("fixture_digest") != fixture["fixture_digest"]:
            add_error(errors, "E_DECISION_FIXTURE_DIGEST", row["decision_id"], str(row.get("fixture_digest")))
        if row.get("expected_route_match") is not True:
            add_error(errors, "E_ROUTE_MISMATCH", row["decision_id"], str(row.get("resolved_route")))
        if row.get("audience_output_count") != 0 or row.get("runtime_plan_count") != 0:
            add_error(errors, "E_DECISION_OUTPUT", row["decision_id"], "audience/runtime output created")
        if recursive_hits(row, FORBIDDEN_CONTENT_FIELD_NAMES):
            add_error(errors, "E_FORBIDDEN_CONTENT_FIELD", row["decision_id"], str(recursive_hits(row, FORBIDDEN_CONTENT_FIELD_NAMES)))
        if recursive_true_flags(row):
            add_error(errors, "E_READY_TRUE", row["decision_id"], str(recursive_true_flags(row)))
        kind = fixture["fixture_kind"]
        if kind == "POSITIVE_COMPLETE_VALIDATION_ONLY":
            if row.get("resolved_route") != "VALIDATION_COMPOSITION_PLAN_CREATED":
                add_error(errors, "E_POSITIVE_ROUTE", row["decision_id"], str(row.get("resolved_route")))
            if row.get("validation_plan_count") != 1 or row.get("plan_id") not in plan_ids:
                add_error(errors, "E_POSITIVE_PLAN", row["decision_id"], str(row.get("plan_id")))
        elif kind == "MISSING_REQUIRED_INPUT":
            if row.get("resolved_route") != fixture["expected_route"]:
                add_error(errors, "E_MISSING_ROUTE", row["decision_id"], str(row.get("resolved_route")))
            if row.get("plan_id") is not None or row.get("validation_plan_count") != 0:
                add_error(errors, "E_MISSING_CREATED_PLAN", row["decision_id"], str(row.get("plan_id")))
            degraded = row.get("degraded_artifact")
            if not isinstance(degraded, dict) or degraded.get("artifact_kind") != fixture["expected_degraded_output_type"]:
                add_error(errors, "E_DEGRADED_ARTIFACT", row["decision_id"], str(degraded))
            else:
                fixed_zero = ["title_count", "body_count", "spoken_line_count", "CTA_count", "asserted_missing_value_count"]
                if any(degraded.get(key) != 0 for key in fixed_zero):
                    add_error(errors, "E_DEGRADED_OUTPUT_COUNT", row["decision_id"], str(degraded))
                if degraded.get("audience_facing") is not False or degraded.get("runtime_consumable") is not False:
                    add_error(errors, "E_DEGRADED_RUNTIME", row["decision_id"], str(degraded))
        elif kind == "NEGATIVE_HARD_GUARD":
            if row.get("resolved_route") != "HARD_GUARD_REJECTED":
                add_error(errors, "E_NEGATIVE_ROUTE", row["decision_id"], str(row.get("resolved_route")))
            if row.get("plan_id") is not None or row.get("validation_plan_count") != 0:
                add_error(errors, "E_NEGATIVE_CREATED_PLAN", row["decision_id"], str(row.get("plan_id")))
            if row.get("expected_error_codes_match") is not True:
                add_error(errors, "E_NEGATIVE_ERROR_CODES", row["decision_id"], str(row.get("rejection_error_codes")))


def validate_plan_edges(
    root: Path,
    freezer: Any,
    plan: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    components: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    cp_id = plan["content_product"]["primary_content_product_type_id"]
    profile = profiles[cp_id]
    required_roles = freezer.required_roles(profile)
    selected = plan["selected_components"]
    selected_roles = [edge["required_component_role"] for edge in selected]
    if selected_roles != required_roles:
        add_error(errors, "E_PLAN_ROLE_SET", plan["plan_id"], str(selected_roles))
    if len(selected_roles) != len(set(selected_roles)):
        add_error(errors, "E_PLAN_DUPLICATE_ROLE", plan["plan_id"], str(selected_roles))
    resolution = plan["required_role_resolution"]
    if resolution.get("required_roles") != required_roles or resolution.get("covered_roles") != required_roles:
        add_error(errors, "E_ROLE_RESOLUTION", plan["plan_id"], str(resolution))
    if resolution.get("uncovered_roles") != [] or resolution.get("optional_roles_selected") != []:
        add_error(errors, "E_OPTIONAL_OR_UNCOVERED_ROLE", plan["plan_id"], str(resolution))
    for edge in selected:
        component = components.get(edge["component_id"])
        if not component:
            add_error(errors, "E_SELECTED_COMPONENT_MISSING", plan["plan_id"], edge["component_id"])
            continue
        resolved_role, role_error = freezer.component_role(component)
        if role_error or resolved_role != edge["required_component_role"] or edge["resolved_component_role"] != resolved_role:
            add_error(errors, "E_SELECTED_COMPONENT_ROLE", plan["plan_id"], str(edge))
        if cp_id not in component.get("applicable_content_product_type_ids", []):
            add_error(errors, "E_SELECTED_COMPONENT_CP", plan["plan_id"], edge["component_id"])
        if component.get("runtime_ready") is True or component.get("ingest_ready") is True:
            add_error(errors, "E_SELECTED_COMPONENT_RUNTIME_READY", plan["plan_id"], edge["component_id"])
        if any((component.get("truth_boundary") or {}).values()):
            add_error(errors, "E_SELECTED_COMPONENT_TRUTH_BOUNDARY", plan["plan_id"], edge["component_id"])
        if not edge.get("CP_applicability_evidence_ref") or edge.get("selection_basis") != "HASH_TIEBREAK_AFTER_CONTRACT_FILTERS":
            add_error(errors, "E_SELECTED_EDGE_EVIDENCE", plan["plan_id"], str(edge))
        binding_ref = edge.get("profile_specific_fixture_binding_ref")
        if not isinstance(binding_ref, str) or not binding_ref.startswith(PLAN_NAMESPACE):
            add_error(errors, "E_SELECTED_EDGE_FIXTURE_BINDING", plan["plan_id"], str(binding_ref))


def validate_plans(
    root: Path,
    freezer: Any,
    plans: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    _, fixtures = fixture_maps(root, freezer)
    profiles = profiles_by_id(root, freezer)
    components = component_by_id(root, freezer)
    rows = [unwrap(row, "orch_validation_composition_plan") for row in plans]
    if len(rows) != 20:
        add_error(errors, "E_PLAN_COUNT", "plans", str(len(rows)))
    for plan in rows:
        fixture_id = plan["fixture_lineage"]["fixture_id"]
        fixture = fixtures.get(fixture_id)
        if not fixture or fixture["fixture_kind"] != "POSITIVE_COMPLETE_VALIDATION_ONLY":
            add_error(errors, "E_PLAN_FIXTURE", plan.get("plan_id", "?"), fixture_id)
            continue
        if plan.get("plan_digest") != freezer.object_digest(plan, {"plan_digest"}):
            add_error(errors, "E_PLAN_DIGEST", plan["plan_id"], "digest mismatch")
        if plan.get("writer") != "ORCH":
            add_error(errors, "E_PLAN_WRITER", plan["plan_id"], str(plan.get("writer")))
        fixed = {
            "plan_type": "ORCHValidationCompositionPlan",
            "plan_mode": "VALIDATION_SYNTHETIC",
            "namespace": PLAN_NAMESPACE,
            "canonicality_scope": "CASE_LOCAL_VALIDATION",
        }
        for key, expected in fixed.items():
            if plan.get(key) != expected:
                add_error(errors, "E_PLAN_NAMESPACE", plan["plan_id"], f"{key}={plan.get(key)}")
        if plan["fixture_lineage"].get("synthetic_test_data") is not True:
            add_error(errors, "E_PLAN_SYNTHETIC", plan["plan_id"], str(plan["fixture_lineage"]))
        if plan["fixture_lineage"].get("may_be_used_as_brand_fact") is not False:
            add_error(errors, "E_PLAN_BRAND_FACT", plan["plan_id"], str(plan["fixture_lineage"]))
        lifecycle = plan["lifecycle"]
        if lifecycle.get("canonical_within_validation_namespace") is not True:
            add_error(errors, "E_PLAN_VALIDATION_CANONICALITY", plan["plan_id"], str(lifecycle))
        for key in ["runtime_consumable", "runtime_authoritative", "production_executable", "dify_consumable", "runtime_ingest_ready"]:
            if lifecycle.get(key) is not False:
                add_error(errors, "E_PLAN_RUNTIME_LIFECYCLE", plan["plan_id"], f"{key}={lifecycle.get(key)}")
        output = plan["output_contract"]
        for key in ["title_allowed", "body_allowed", "spoken_line_payload_allowed", "CTA_payload_allowed", "audience_facing_output_allowed"]:
            if output.get(key) is not False:
                add_error(errors, "E_PLAN_OUTPUT_ALLOWED", plan["plan_id"], f"{key}={output.get(key)}")
        for key in ["title_count", "body_count", "spoken_line_count", "CTA_count"]:
            if output.get(key) != 0:
                add_error(errors, "E_PLAN_OUTPUT_COUNT", plan["plan_id"], f"{key}={output.get(key)}")
        bindings = plan["synthetic_bindings"]
        if bindings.get("authorization_status") != "SIMULATED_GRANTED_FOR_CONTRACT_TEST":
            add_error(errors, "E_PLAN_AUTH_STATUS", plan["plan_id"], str(bindings.get("authorization_status")))
        zero_counts = ["verified_brand_fact_count", "verified_authorization_count", "GRANTED_VERIFIED_authorization_count", "real_event_binding_count"]
        if any(bindings.get(key) != 0 for key in zero_counts):
            add_error(errors, "E_PLAN_VERIFIED_BINDING", plan["plan_id"], str(bindings))
        if bindings.get("all_fixture_only") is not True:
            add_error(errors, "E_PLAN_FIXTURE_ONLY", plan["plan_id"], str(bindings))
        refs = list(bindings.get("source_ref_ids", [])) + list(bindings.get("authorization_ref_ids", []))
        refs.extend(binding.get("binding_ref") for binding in bindings.get("fact_slot_bindings", {}).values())
        bad_refs = [ref for ref in refs if not isinstance(ref, str) or not ref.startswith(f"{PLAN_NAMESPACE}{fixture_id}/")]
        if bad_refs:
            add_error(errors, "E_PLAN_REF_NAMESPACE", plan["plan_id"], str(bad_refs))
        for slot_id, binding in bindings.get("fact_slot_bindings", {}).items():
            if binding.get("fixture_only") is not True or binding.get("synthetic_test_data") is not True:
                add_error(errors, "E_PLAN_FACT_FIXTURE_FLAG", plan["plan_id"], slot_id)
            if binding.get("may_be_used_as_brand_fact") is not False or binding.get("runtime_usable") is not False:
                add_error(errors, "E_PLAN_FACT_RUNTIME_FLAG", plan["plan_id"], slot_id)
        if recursive_hits(plan, FORBIDDEN_CONTENT_FIELD_NAMES):
            add_error(errors, "E_FORBIDDEN_CONTENT_FIELD", plan["plan_id"], str(recursive_hits(plan, FORBIDDEN_CONTENT_FIELD_NAMES)))
        if recursive_hits(plan, COMPONENT_PAYLOAD_FIELD_NAMES):
            add_error(errors, "E_COMPONENT_PAYLOAD_LEAK", plan["plan_id"], str(recursive_hits(plan, COMPONENT_PAYLOAD_FIELD_NAMES)))
        if recursive_true_flags(plan):
            add_error(errors, "E_READY_TRUE", plan["plan_id"], str(recursive_true_flags(plan)))
        validate_plan_edges(root, freezer, plan, profiles, components, errors)


def validate_selection_audits(
    root: Path,
    freezer: Any,
    plans: list[dict[str, Any]],
    audits: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    plan_rows = [unwrap(row, "orch_validation_composition_plan") for row in plans]
    audit_rows = [unwrap(row, "orch_component_selection_audit") for row in audits]
    requirements, fixtures = fixture_maps(root, freezer)
    profiles = profiles_by_id(root, freezer)
    components = component_by_id(root, freezer)
    registry_digest = freezer.sha256_file(root / freezer.COMPONENT_REGISTRY_PATH)
    expected_count = sum(len(plan["selected_components"]) for plan in plan_rows)
    if len(audit_rows) != expected_count:
        add_error(errors, "E_AUDIT_COUNT", "audits", str(len(audit_rows)))
    by_key = {
        (audit["fixture_id"], audit["required_component_role"]): audit
        for audit in audit_rows
    }
    for audit in audit_rows:
        if audit.get("selection_digest") != freezer.object_digest(audit, {"selection_digest"}):
            add_error(errors, "E_AUDIT_DIGEST", audit["audit_id"], "digest mismatch")
        fixture = fixtures.get(audit["fixture_id"])
        profile = profiles.get(audit["content_product_type_id"])
        if not fixture or not profile:
            add_error(errors, "E_AUDIT_LINEAGE", audit["audit_id"], "fixture/profile missing")
            continue
        passing = [row for row in audit.get("filter_results", []) if row.get("filter_pass") is True]
        ranked = sorted(
            (
                {
                    **row,
                    "selection_hash": freezer.selection_hash(
                        fixture,
                        audit["content_product_type_id"],
                        audit["required_component_role"],
                        components[row["component_id"]],
                        profile["profile_digest"],
                        registry_digest,
                    ),
                }
                for row in passing
            ),
            key=lambda item: (item["selection_hash"], item["component_id"]),
        )
        ranked_ids = [row["component_id"] for row in ranked]
        if ranked_ids != audit.get("eligible_candidate_ids"):
            add_error(errors, "E_AUDIT_ELIGIBLE_IDS", audit["audit_id"], str(ranked_ids))
        if audit.get("eligible_candidate_count") != len(ranked_ids) or not ranked_ids:
            add_error(errors, "E_AUDIT_ELIGIBLE_COUNT", audit["audit_id"], str(audit.get("eligible_candidate_count")))
        if audit.get("selected_component_id") not in ranked_ids:
            add_error(errors, "E_AUDIT_SELECTED_NOT_ELIGIBLE", audit["audit_id"], str(audit.get("selected_component_id")))
        for row in passing:
            if row.get("fail_reasons") != []:
                add_error(errors, "E_AUDIT_PASS_HAS_FAILURE", audit["audit_id"], row["component_id"])
            must_true = [
                "reviewed_component",
                "target_CP_in_applicable_CP_ids",
                "per_CP_applicability_evidence_present",
                "required_role_exact_match",
                "required_input_slots_satisfied",
                "role_authority_boundary_compatible",
                "event_truth_mode_compatible",
                "claim_boundary_compatible",
                "forbidden_combination_clear",
            ]
            if any(row.get(key) is not True for key in must_true):
                add_error(errors, "E_AUDIT_PASS_FLAG", audit["audit_id"], row["component_id"])
        selected_hash = audit.get("selection_hash")
        selected_hashes = [
            row.get("selection_hash")
            for row in ranked
            if row["component_id"] == audit.get("selected_component_id")
        ]
        if selected_hash not in selected_hashes:
            add_error(errors, "E_AUDIT_SELECTED_HASH", audit["audit_id"], str(selected_hash))
        ordered_hashes = [(row.get("selection_hash"), row.get("component_id")) for row in ranked]
        if ordered_hashes and (selected_hash, audit.get("selected_component_id")) != ordered_hashes[0]:
            add_error(errors, "E_AUDIT_NOT_HASH_MIN", audit["audit_id"], str(ordered_hashes[:2]))
    for plan in plan_rows:
        fixture_id = plan["fixture_lineage"]["fixture_id"]
        for edge in plan["selected_components"]:
            audit = by_key.get((fixture_id, edge["required_component_role"]))
            if not audit:
                add_error(errors, "E_PLAN_AUDIT_MISSING", plan["plan_id"], edge["required_component_role"])
                continue
            if audit["selected_component_id"] != edge["component_id"]:
                add_error(errors, "E_PLAN_AUDIT_COMPONENT", plan["plan_id"], edge["required_component_role"])
            if audit["candidate_set_digest"] != edge["candidate_set_digest"]:
                add_error(errors, "E_PLAN_AUDIT_CANDIDATE_SET", plan["plan_id"], edge["required_component_role"])


def validate_coverage_result_packet(
    root: Path,
    freezer: Any,
    coverage_doc: dict[str, Any],
    result_doc: dict[str, Any],
    packet_doc: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    coverage = coverage_doc["orch_20cp_dryrun_coverage"]
    if coverage.get("coverage_digest") != freezer.object_digest(coverage, {"coverage_digest"}):
        add_error(errors, "E_COVERAGE_DIGEST", "coverage", "digest mismatch")
    summary = coverage["summary"]
    expected_summary = {
        "request_count": 60,
        "decision_count": 60,
        "positive_validation_plan_count": 20,
        "missing_degraded_count": 20,
        "negative_rejected_count": 20,
        "unexpected_route_count": 0,
        "orch_validation_dryrun_pass_profile_count": 20,
        "canonical_validation_composition_plan_count": 20,
        "canonical_composition_plan_count": 0,
        "canonical_runtime_composition_plan_count": 0,
        "canonical_production_composition_plan_count": 0,
        "runtime_generation_eligible_profile_count": 0,
        "audience_facing_content_count": 0,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            add_error(errors, "E_COVERAGE_SUMMARY", "coverage", f"{key}={summary.get(key)}")
    result = result_doc["orch_20cp_dryrun_result"]
    if result.get("result_digest") != freezer.object_digest(result, {"result_digest"}):
        add_error(errors, "E_RESULT_DIGEST", "result", "digest mismatch")
    if result.get("execution_integrity") != "PASS":
        add_error(errors, "E_EXECUTION_INTEGRITY", "result", str(result.get("execution_integrity")))
    if result["validation_dryrun"].get("unexpected_route_count") != 0:
        add_error(errors, "E_RESULT_UNEXPECTED_ROUTE", "result", str(result["validation_dryrun"]))
    namespace = result["plan_namespace"]
    if namespace.get("canonical_validation_composition_plan_count") != 20:
        add_error(errors, "E_RESULT_VALIDATION_PLAN_COUNT", "result", str(namespace))
    for key in [
        "canonical_composition_plan_count",
        "canonical_runtime_composition_plan_count",
        "canonical_production_composition_plan_count",
        "executed_plan_instance_count",
    ]:
        if namespace.get(key) != 0:
            add_error(errors, "E_RESULT_RUNTIME_PLAN_COUNT", "result", f"{key}={namespace.get(key)}")
    runtime = result["runtime"]
    runtime_zero = [
        "verified_brand_fact_bundle_count",
        "verified_runtime_authorization_count",
        "GRANTED_VERIFIED_authorization_count",
        "real_event_binding_count",
        "runtime_generation_eligible_profile_count",
    ]
    if any(runtime.get(key) != 0 for key in runtime_zero) or runtime.get("runtime_ingest_ready") is not False:
        add_error(errors, "E_RESULT_RUNTIME", "result", str(runtime))
    boundaries = result["boundaries"]
    boundary_zero = [
        "audience_facing_content_count",
        "plan_execution_count",
        "KE_truth_change_count",
        "DIFY_payload_count",
        "RAG_context_bundle_count",
        "Serving_projection_write_count",
    ]
    if any(boundaries.get(key) != 0 for key in boundary_zero):
        add_error(errors, "E_RESULT_BOUNDARY", "result", str(boundaries))
    if boundaries.get("generator_qualified") is not False or boundaries.get("generation_600_allowed") is not False:
        add_error(errors, "E_RESULT_GENERATION_BOUNDARY", "result", str(boundaries))
    if recursive_true_flags(result):
        add_error(errors, "E_READY_TRUE", "result", str(recursive_true_flags(result)))
    digests = result.get("generated_file_digests", {})
    if CHECKER_PATH.as_posix() not in digests:
        add_error(errors, "E_RESULT_CHECKER_DIGEST", "result", "checker digest missing from generated_file_digests")
    invariance = freezer.invariance_checks(root)
    if any(value is not True for value in invariance.values()):
        add_error(errors, "E_INVARIANCE", "result", str(invariance))
    packet = packet_doc["orch_guardian_review_packet"]
    if packet.get("packet_digest") != freezer.object_digest(packet, {"packet_digest"}):
        add_error(errors, "E_PACKET_DIGEST", "packet", "digest mismatch")
    if packet.get("validation_plan_count") != 20 or packet.get("selection_audit_count") != 85:
        add_error(errors, "E_PACKET_COUNTS", "packet", str(packet))


def validate_materialization(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    for item in freezer.check_files(root):
        if item == f"materialized drift {RESULT_PATH.as_posix()}":
            continue
        add_error(errors, "E_MATERIALIZED_DRIFT", "freezer", item)


def top_level_route_ids(text: str) -> list[int]:
    ids: list[int] = []
    for line in text.splitlines():
        if line.startswith("  route_migration_") and line.endswith(":"):
            suffix = line.strip().removeprefix("route_migration_").removesuffix(":")
            if suffix.isdigit():
                ids.append(int(suffix))
    return ids


def validate_ledger(root: Path, freezer: Any, result_doc: dict[str, Any], errors: list[dict[str, str]], enforce_git: bool) -> None:
    data = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    migration = data.get("route_migration_25")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_ROUTE25", "ledger", "route_migration_25 missing")
        return
    if migration.get("applied_by_task") != TASK_ID:
        add_error(errors, "E_LEDGER_TASK", "ledger", str(migration.get("applied_by_task")))
    if migration.get("additive_only") is not True or migration.get("no_readiness_flipped") is not True:
        add_error(errors, "E_LEDGER_DECLARATION", "ledger", str(migration))
    if migration.get("ORCH_validation_dryrun", {}).get("result_digest") != result_doc["orch_20cp_dryrun_result"]["result_digest"]:
        add_error(errors, "E_LEDGER_RESULT_DIGEST", "ledger", str(migration.get("ORCH_validation_dryrun")))
    if migration.get("ORCH_validation_dryrun", {}).get("canonical_validation_composition_plan_count") != 20:
        add_error(errors, "E_LEDGER_VALIDATION_COUNT", "ledger", str(migration.get("ORCH_validation_dryrun")))
    if migration.get("ORCH_validation_dryrun", {}).get("canonical_composition_plan_count") != 0:
        add_error(errors, "E_LEDGER_RUNTIME_PLAN_COUNT", "ledger", str(migration.get("ORCH_validation_dryrun")))
    if migration.get("ORCH_validation_dryrun", {}).get("runtime_generation_eligible_profile_count") != 0:
        add_error(
            errors,
            "E_LEDGER_RUNTIME_ELIGIBLE",
            "ledger",
            str(migration.get("ORCH_validation_dryrun", {}).get("runtime_generation_eligible_profile_count")),
        )
    if migration.get("migration_digest") != freezer.object_digest(migration, {"migration_digest"}):
        add_error(errors, "E_LEDGER_DIGEST", "ledger", "migration digest mismatch")
    ids = top_level_route_ids((root / LEDGER_PATH).read_text(encoding="utf-8"))
    if 25 not in ids:
        add_error(errors, "E_LEDGER_ROUTE25", "ledger", "route id missing")
    if sorted(route_id for route_id in ids if route_id >= 19) != list(range(19, max(ids) + 1)):
        add_error(errors, "E_LEDGER_SEQUENCE", "ledger", str(ids))
    if enforce_git:
        old_text = git(root, ["show", f"{BASELINE_HEAD}:{LEDGER_PATH.as_posix()}"])
        if old_text:
            old_data = yaml.safe_load(old_text)["grc_3600_execution_plan_status"]
            extra = sorted(set(data) - set(old_data))
            if extra != ["route_migration_25", "route_migration_26", "route_migration_27"]:
                add_error(errors, "E_LEDGER_EXTRA_KEYS", "ledger", str(extra))
            for key, value in old_data.items():
                if key in {"route_migration_23", "route_migration_24"}:
                    continue
                if data.get(key) != value:
                    add_error(errors, "E_LEDGER_NON_ADDITIVE", "ledger", key)


def validate_ci(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / CI_PATH).read_text(encoding="utf-8")
    required = [
        "python3 ci/checkers/check_orch_v2_20cp_validation_dryrun.py",
        "python3 ci/checkers/check_orch_v2_20cp_validation_dryrun.py --selftest",
        "python3 08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001/run_orch_20cp_validation_dryrun_freezer.py --check",
        '"ci/checkers/check_orch_v2_20cp_validation_dryrun.py"',
        '"ci/checkers/check_orch_v2_20cp_validation_dryrun.py --selftest"',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        add_error(errors, "E_CI_REGISTRATION", "ci", str(missing))


def collect_errors(root: Path, enforce_git: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    freezer = load_freezer(root)
    required = [
        FREEZER_PATH,
        CONTRACT_PATH,
        REQUESTS_PATH,
        DECISIONS_PATH,
        PLANS_PATH,
        SELECTION_AUDIT_PATH,
        COVERAGE_PATH,
        RESULT_PATH,
        PACKET_PATH,
        CHECKER_PATH,
        LEDGER_PATH,
        CI_PATH,
    ]
    for path in required:
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE_MISSING", path.as_posix(), "missing")
    if errors:
        return errors
    validate_preflight(root, errors, enforce_git)
    validate_input_digests(root, freezer, errors)
    requests = load_jsonl(root / REQUESTS_PATH)
    decisions = load_jsonl(root / DECISIONS_PATH)
    plans = load_jsonl(root / PLANS_PATH)
    audits = load_jsonl(root / SELECTION_AUDIT_PATH)
    plan_ids = {unwrap(row, "orch_validation_composition_plan")["plan_id"] for row in plans}
    validate_requests(root, freezer, requests, errors)
    validate_decisions(root, freezer, decisions, plan_ids, errors)
    validate_plans(root, freezer, plans, errors)
    validate_selection_audits(root, freezer, plans, audits, errors)
    validate_materialization(root, freezer, errors)
    coverage = load_yaml(root / COVERAGE_PATH)
    result = load_yaml(root / RESULT_PATH)
    packet = load_yaml(root / PACKET_PATH)
    validate_coverage_result_packet(root, freezer, coverage, result, packet, errors)
    validate_ledger(root, freezer, result, errors, enforce_git)
    validate_ci(root, errors)
    return errors


def selftest() -> int:
    root = Path.cwd()
    freezer = load_freezer(root)
    requests = load_jsonl(root / REQUESTS_PATH)
    decisions = load_jsonl(root / DECISIONS_PATH)
    plans = load_jsonl(root / PLANS_PATH)
    audits = load_jsonl(root / SELECTION_AUDIT_PATH)
    coverage = load_yaml(root / COVERAGE_PATH)
    result = load_yaml(root / RESULT_PATH)
    packet = load_yaml(root / PACKET_PATH)
    plan_ids = {unwrap(row, "orch_validation_composition_plan")["plan_id"] for row in plans}
    tests: list[tuple[str, bool]] = []

    tests.append(("valid_outputs", not collect_errors(root, enforce_git=False)))

    bad_result = copy.deepcopy(result)
    bad_result["orch_20cp_dryrun_result"]["plan_namespace"]["canonical_composition_plan_count"] = 20
    result_errors: list[dict[str, str]] = []
    validate_coverage_result_packet(root, freezer, coverage, bad_result, packet, result_errors)
    tests.append(("runtime_canonical_count_rejected", any(e["code"] == "E_RESULT_RUNTIME_PLAN_COUNT" for e in result_errors)))

    bad_plan_docs = copy.deepcopy(plans)
    bad_plan = unwrap(bad_plan_docs[0], "orch_validation_composition_plan")
    bad_plan["output_contract"]["CTA_payload"] = "call now"
    plan_errors: list[dict[str, str]] = []
    validate_plans(root, freezer, bad_plan_docs, plan_errors)
    tests.append(("cta_payload_rejected", any(e["code"] == "E_FORBIDDEN_CONTENT_FIELD" for e in plan_errors)))

    verified_plan_docs = copy.deepcopy(plans)
    verified = unwrap(verified_plan_docs[0], "orch_validation_composition_plan")
    verified["synthetic_bindings"]["authorization_status"] = "GRANTED_VERIFIED"
    verified["synthetic_bindings"]["GRANTED_VERIFIED_authorization_count"] = 1
    verified_errors: list[dict[str, str]] = []
    validate_plans(root, freezer, verified_plan_docs, verified_errors)
    tests.append(("verified_auth_rejected", any(e["code"] in {"E_PLAN_AUTH_STATUS", "E_PLAN_VERIFIED_BINDING"} for e in verified_errors)))

    missing_plan_docs = copy.deepcopy(decisions)
    for row in missing_plan_docs:
        decision = unwrap(row, "orch_dryrun_decision")
        if decision["fixture_kind"] == "MISSING_REQUIRED_INPUT":
            decision["plan_id"] = "ORCH-VALPLAN-ILLEGAL"
            decision["validation_plan_count"] = 1
            break
    missing_errors: list[dict[str, str]] = []
    validate_decisions(root, freezer, missing_plan_docs, plan_ids, missing_errors)
    tests.append(("missing_input_plan_rejected", any(e["code"] == "E_MISSING_CREATED_PLAN" for e in missing_errors)))

    negative_plan_docs = copy.deepcopy(decisions)
    for row in negative_plan_docs:
        decision = unwrap(row, "orch_dryrun_decision")
        if decision["fixture_kind"] == "NEGATIVE_HARD_GUARD":
            decision["resolved_route"] = "VALIDATION_COMPOSITION_PLAN_CREATED"
            decision["plan_id"] = "ORCH-VALPLAN-ILLEGAL"
            decision["validation_plan_count"] = 1
            break
    negative_errors: list[dict[str, str]] = []
    validate_decisions(root, freezer, negative_plan_docs, plan_ids, negative_errors)
    tests.append(("negative_plan_rejected", any(e["code"] in {"E_NEGATIVE_ROUTE", "E_NEGATIVE_CREATED_PLAN"} for e in negative_errors)))

    audit_docs = copy.deepcopy(audits)
    audit = unwrap(audit_docs[0], "orch_component_selection_audit")
    audit["selected_component_id"] = "NOT-ELIGIBLE"
    audit_errors: list[dict[str, str]] = []
    validate_selection_audits(root, freezer, plans, audit_docs, audit_errors)
    tests.append(("selection_audit_tamper_rejected", any(e["code"] == "E_AUDIT_SELECTED_NOT_ELIGIBLE" for e in audit_errors)))

    bad_edge_docs = copy.deepcopy(plans)
    bad_edge = unwrap(bad_edge_docs[0], "orch_validation_composition_plan")
    bad_edge["selected_components"][0]["profile_specific_fixture_binding_ref"] = "verified://brand/fact/001"
    edge_errors: list[dict[str, str]] = []
    validate_plans(root, freezer, bad_edge_docs, edge_errors)
    tests.append(("non_fixture_ref_rejected", any(e["code"] == "E_SELECTED_EDGE_FIXTURE_BINDING" for e in edge_errors)))

    payload_docs = copy.deepcopy(plans)
    unwrap(payload_docs[0], "orch_validation_composition_plan")["selected_components"][0]["payload"] = "copied mechanism"
    payload_errors: list[dict[str, str]] = []
    validate_plans(root, freezer, payload_docs, payload_errors)
    tests.append(("component_payload_leak_rejected", any(e["code"] == "E_COMPONENT_PAYLOAD_LEAK" for e in payload_errors)))

    req_docs = copy.deepcopy(requests)
    unwrap(req_docs[0], "orch_validation_request")["runtime_consumable"] = True
    request_errors: list[dict[str, str]] = []
    validate_requests(root, freezer, req_docs, request_errors)
    tests.append(("runtime_request_rejected", any(e["code"] == "E_READY_TRUE" for e in request_errors)))

    invariance = freezer.invariance_checks(root)
    tests.append(("fixture_and_component_order_invariance", all(value is True for value in invariance.values())))
    tests.append(
        (
            "generator_successor_write_surface_declared",
            (SUCCESSOR_GENERATOR_V2_DIR / "generator_v2_build_result.v0.1.yaml").is_relative_to(
                SUCCESSOR_GENERATOR_V2_DIR
            ),
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
        print("usage: check_orch_v2_20cp_validation_dryrun.py [--selftest]", file=sys.stderr)
        return 2
    if len(argv) == 1 and argv[0] == "--selftest":
        return selftest()
    if argv:
        print("usage: check_orch_v2_20cp_validation_dryrun.py [--selftest]", file=sys.stderr)
        return 2
    errors = collect_errors(Path.cwd(), enforce_git=True)
    if errors:
        print(json.dumps({"status": "FAIL", "error_count": len(errors), "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task_id": TASK_ID}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
