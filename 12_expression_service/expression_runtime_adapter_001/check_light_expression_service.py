#!/usr/bin/env python3
"""Fail-closed package gate for the Phase B light-expression service."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import yaml


if not __debug__:
    print("check_light_expression_service refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "DIYU_LIGHT_EXPRESSION_SERVICE_001"
BASELINE_MASTER = "95b8b1700b7e96b1d2383465713bef8c36e7f6cb"
PACKAGE_ROOT = Path("12_expression_service/expression_runtime_adapter_001")
MANIFEST_PATH = PACKAGE_ROOT / "service_manifest.v1.yaml"
RESULT_PATH = PACKAGE_ROOT / "result/light_expression_service_result.v1.yaml"
ARCH_REVIEW_PATH = PACKAGE_ROOT / "review/light_expression_architecture_review.v1.yaml"
TRUST_REVIEW_PATH = PACKAGE_ROOT / "review/trust_fact_safety_review.v1.yaml"
CONTRACT_PATH = Path(
    "11_product_foundation/public_foundation_001/contract/public_foundation_contract.v1.yaml"
)
IDENTITY_PATH = Path(
    "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml"
)
TOPIC_PATH = Path(
    "11_product_foundation/public_foundation_001/taxonomy/topic_product_mapping.v1.yaml"
)
STATUS_PATH = Path("project-infra/current_product_status.v1.yaml")
WORKSPACE_MANIFEST_PATH = Path("project-infra/product_workspace_manifest.v1.yaml")
WORKFLOW_PATH = Path(".github/workflows/ci.yml")
TEST_PATH = PACKAGE_ROOT / "test_light_expression_service.py"
SOURCE_PATHS = (
    PACKAGE_ROOT / "light_expression_service.py",
    PACKAGE_ROOT / "http_entrypoint.py",
)
REQUIRED_PACKAGE_PATHS = frozenset(
    {
        PACKAGE_ROOT / "README.md",
        PACKAGE_ROOT / "light_expression_service.py",
        PACKAGE_ROOT / "http_entrypoint.py",
        PACKAGE_ROOT / "neutral_expression_profile.v1.yaml",
        PACKAGE_ROOT / "service_manifest.v1.yaml",
        PACKAGE_ROOT / "test_light_expression_service.py",
        PACKAGE_ROOT / "check_light_expression_service.py",
        RESULT_PATH,
    }
)
OPTIONAL_REVIEW_PATHS = frozenset({ARCH_REVIEW_PATH, TRUST_REVIEW_PATH})
PACKAGE7_SUCCESSOR_EXTENSION_PATHS = frozenset(
    {
        PACKAGE_ROOT / "light_expression_service.py",
        PACKAGE_ROOT / "test_light_expression_service.py",
        PACKAGE_ROOT / "check_light_expression_service.py",
        MANIFEST_PATH,
    }
)
EXPECTED_ENDPOINTS = (
    ("POST", "/v1/content/prepare"),
    ("POST", "/v1/content/validate"),
    ("GET", "/healthz"),
    ("GET", "/readyz"),
)
PUBLIC_PINS = {
    CONTRACT_PATH: "a3aec92fdcc22635bb07bc5d2595ebaa5cfa1f1c9d5fad42cc39481808bbc1af",
    IDENTITY_PATH: "65b8242b9b760e64f8e441c4334c68fa76f6dc3a11e2fe2f8f62ad6a887c3cbc",
    TOPIC_PATH: "e51f46635b6c3312e0626bc5aca448c91d20b0d71cae6a8de793ba5b603e2b95",
}
HISTORICAL_ASSET_PINS = {
    Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/component/"
        "active_gate1_components.v0.1.jsonl"
    ): (68, "83dd1a8d35149785ac8bb172700b79d6221e5a7331b210018699fabaa49bc8ae"),
    Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/component/"
        "active_control_rules.v0.1.jsonl"
    ): (8, "5d0ded265a6be6d0f39d35d2f739239225211081db6d6c4e4df0c8dcc2f09386"),
    Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/component/"
        "active_gate1_edges.v0.1.jsonl"
    ): (85, "de366eb50afe8a5a9362d3faa2a6a845af9c334683bdb9a8489cbfad2b2566f0"),
    Path(
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/ab/"
        "active_ab_structural_paths.v0.1.jsonl"
    ): (20, "4756971ef58ed472d0447f61f00bac7b7ef594117c43ecfb9fe3d7106c9631f3"),
    Path(
        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
        "clean_120_reference_corpus_freeze_001/"
        "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
    ): (120, "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"),
    Path(
        "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
        "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
        "reviewed_reusable_component_registry.v0.4.jsonl"
    ): (86, "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601"),
}
READINESS_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "generator_qualified",
        "retrieval_ready",
        "runtime_ready",
        "release_ready",
        "production_ready",
    }
)
FORBIDDEN_IMPLEMENTATION_IMPORTS = frozenset(
    {
        "openai",
        "requests",
        "httpx",
        "urllib.request",
        "boto3",
        "sqlalchemy",
        "psycopg",
        "dify",
    }
)
REQUIRED_TEST_METHODS = frozenset(
    {
        "test_valid_request_without_atom_references_uses_neutral_profile",
        "test_narrative_only_input_is_allowed_without_precise_claim_requirement",
        "test_missing_required_precise_fact_returns_collection_card",
        "test_explicit_product_and_audience_are_carried_without_inference",
        "test_missing_or_out_of_topic_product_never_selects_a_default",
        "test_missing_audience_returns_requirement_collection_card",
        "test_unregistered_requirement_change_cannot_reuse_confirmation",
        "test_body_cannot_create_trust_without_server_context",
        "test_client_cannot_override_hard_prohibitions",
        "test_unknown_creative_hints_are_ignored_with_diagnostics",
        "test_evaluation_rules_are_server_resolved_when_omitted",
        "test_fact_only_input_degrades_safely",
        "test_empty_material_and_facts_returns_collection_card",
        "test_missing_fact_authorization_requests_authorization",
        "test_cross_tenant_store_and_account_fail_closed",
        "test_unregistered_request_body_fact_cannot_self_upgrade",
        "test_authorization_kind_and_disclosure_scope_are_bound",
        "test_requirement_confirmation_grant_is_purpose_and_scope_bound",
        "test_future_or_empty_evidence_is_not_usable",
        "test_subject_confirmation_cannot_be_replayed_across_scope_or_account",
        "test_used_references_must_be_plan_subsets",
        "test_all_user_visible_surfaces_are_scanned_for_internal_leaks",
        "test_nested_scope_and_authorization_fields_are_internal_leaks",
        "test_internal_identifier_values_are_blocked_on_every_surface",
        "test_obvious_contact_information_is_a_privacy_hard_issue",
        "test_all_plan_required_surfaces_must_be_present",
        "test_structured_pass_keeps_semantic_review_pending_and_scores_empty",
        "test_candidate_count_and_difference_policy_are_explicit",
        "test_request_id_does_not_change_deterministic_plan",
        "test_concurrent_replay_keeps_one_deterministic_plan",
        "test_four_http_endpoints_run_locally",
        "test_http_body_cannot_register_a_fabricated_fact",
        "test_simulation_context_cannot_bind_non_loopback_host",
        "test_injected_plan_store_preserves_package2_ownership_and_default_behavior",
        "test_server_injected_brand_profile_cannot_grant_scope",
    }
)


class GateFailure(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise GateFailure(code)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"E_YAML_OBJECT:{path}")
    return value


def validate_all_readiness_false(value: Any, location: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in READINESS_KEYS:
                require(child is False, f"E_READINESS_TRUE:{location}:{key}")
            validate_all_readiness_false(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_all_readiness_false(child, f"{location}[{index}]")


def validate_manifest(manifest: dict[str, Any]) -> None:
    require(manifest.get("schema_version") == "v1.0", "E_MANIFEST_SCHEMA")
    require(manifest.get("task_id") == TASK_ID, "E_MANIFEST_TASK")
    require(manifest.get("baseline_master_commit") == BASELINE_MASTER, "E_MANIFEST_BASELINE")
    require(manifest.get("main_write_root") == PACKAGE_ROOT.as_posix(), "E_MANIFEST_ROOT")
    endpoints = tuple((row.get("method"), row.get("path")) for row in manifest.get("endpoints", []))
    require(endpoints == EXPECTED_ENDPOINTS, "E_MANIFEST_ENDPOINTS")
    trust = manifest.get("trust_boundary", {})
    require(trust.get("trusted_context_injected_outside_request_body") is True, "E_TRUST_INJECTION")
    require(trust.get("client_trust_labels_authoritative") is False, "E_CLIENT_TRUST")
    require(trust.get("request_body_may_register_fact_or_fragment") is False, "E_CLIENT_EVIDENCE_REGISTRATION")
    require(
        trust.get("exact_evidence_digest_must_be_registered_by_trusted_context") is True,
        "E_TRUSTED_EVIDENCE_REGISTRATION",
    )
    require(trust.get("normal_runtime_requires_atom_refs") is False, "E_ATOM_RUNTIME")
    requirement = manifest.get("confirmed_requirement_extension", {})
    require(
        requirement.get("required_fields")
        == [
            "selected_internal_content_product_id",
            "primary_audience",
            "required_precise_fact_kinds",
        ],
        "E_REQUIREMENT_EXTENSION_FIELDS",
    )
    require(requirement.get("keyword_or_digest_inference_allowed") is False, "E_REQUIREMENT_INFERENCE")
    require(requirement.get("product_must_be_explicit_and_allowed_by_selected_topic") is True, "E_PRODUCT_ROUTE")
    require(requirement.get("audience_must_be_explicit") is True, "E_AUDIENCE_ROUTE")
    runtime = manifest.get("runtime_boundaries", {})
    for key in (
        "external_provider_adapter_count",
        "external_model_call_count",
        "Dify_call_count",
        "database_call_count",
        "audience_body_generation_count",
    ):
        require(runtime.get(key) == 0, f"E_RUNTIME_BOUNDARY:{key}")
    successor = manifest.get("authorized_package7_successor_extension", {})
    require(successor.get("task_id") == "DIYU_DIFY_END_TO_END_001", "E_SUCCESSOR_TASK")
    for key in (
        "historical_review_remains_as_built",
        "current_extension_review_owned_by_package7",
        "injectable_plan_store_preserves_package2_plan_ownership",
        "injectable_expression_profile_is_server_resolved",
        "default_in_memory_and_neutral_behavior_preserved",
    ):
        require(successor.get(key) is True, f"E_SUCCESSOR_CONTRACT:{key}")
    require(
        successor.get("injected_profile_may_grant_fact_or_scope") is False,
        "E_SUCCESSOR_SCOPE_GRANT",
    )
    numbers = manifest.get("core_numbers", {})
    require(numbers.get("target_case_baseline") == 300, "E_CORE_300")
    require(numbers.get("frozen_reference_inventory") == 120, "E_CORE_120")
    require(numbers.get("historical_component_inventory") == 86, "E_CORE_86")
    require(numbers.get("changed_or_harmed") is False, "E_CORE_HARM")
    validate_all_readiness_false(manifest.get("readiness", {}), "manifest.readiness")


def validate_result(result: dict[str, Any]) -> None:
    require(result.get("schema_version") == "v1.0", "E_RESULT_SCHEMA")
    require(result.get("task_id") == TASK_ID, "E_RESULT_TASK")
    require(result.get("baseline_master_commit") == BASELINE_MASTER, "E_RESULT_BASELINE")
    require(
        result.get("state")
        in {"CANDIDATE_READY_PENDING_INDEPENDENT_REVIEWS", "PENDING_ROOT_APPROVAL"},
        "E_RESULT_STATE",
    )
    implementation = result.get("implementation", {})
    require(implementation.get("endpoint_count") == 4, "E_RESULT_ENDPOINTS")
    require(implementation.get("prepare_generates_audience_body") is False, "E_RESULT_BODY")
    require(implementation.get("external_provider_adapter_count") == 0, "E_RESULT_PROVIDER")
    require(implementation.get("external_model_call_count") == 0, "E_RESULT_MODEL")
    require(implementation.get("Dify_call_count") == 0, "E_RESULT_DIFY")
    require(implementation.get("database_call_count") == 0, "E_RESULT_DATABASE")
    numbers = result.get("core_numbers", {})
    require(numbers == {
        "target_case_baseline": 300,
        "frozen_reference_inventory": 120,
        "historical_component_inventory": 86,
        "changed_or_harmed": False,
    }, "E_RESULT_CORE_NUMBERS")
    historical = result.get("historical_expression_assets", {})
    require(historical.get("active_component_count") == 68, "E_RESULT_COMPONENTS")
    require(historical.get("active_edge_count") == 85, "E_RESULT_EDGES")
    require(historical.get("ab_structural_path_group_count") == 20, "E_RESULT_AB")
    require(historical.get("changed_or_harmed") is False, "E_RESULT_HISTORICAL_HARM")
    require(result.get("pull_request", {}).get("merged") is False, "E_RESULT_MERGED")
    validate_all_readiness_false(result.get("readiness", {}), "result.readiness")


def validate_implementation_source(source: str, path: Path) -> None:
    tree = ast.parse(source, filename=path.as_posix())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    blocked = sorted(
        imported
        for imported in imports
        if any(imported == forbidden or imported.startswith(forbidden + ".") for forbidden in FORBIDDEN_IMPLEMENTATION_IMPORTS)
    )
    require(not blocked, f"E_FORBIDDEN_IMPLEMENTATION_IMPORT:{path}:{blocked}")
    require("eval(" not in source and "exec(" not in source, f"E_DYNAMIC_EXECUTION:{path}")


def validate_source_shape(root: Path) -> None:
    core = (root / SOURCE_PATHS[0]).read_text(encoding="utf-8")
    http = (root / SOURCE_PATHS[1]).read_text(encoding="utf-8")
    tests = (root / TEST_PATH).read_text(encoding="utf-8")
    validate_implementation_source(core, SOURCE_PATHS[0])
    validate_implementation_source(http, SOURCE_PATHS[1])
    for token in (
        "class LightExpressionService",
        "class PlanStore(Protocol)",
        "def action_card(",
        "expression_profile_resolver",
        "def prepare(",
        "def validate(",
        "PENDING_EXTERNAL_REVIEW",
    ):
        require(token in core, f"E_CORE_SHAPE:{token}")
    require("int(digest_object(key)" not in core, "E_DIGEST_PRODUCT_INFERENCE")
    require("与该题材相关的普通用户" not in core, "E_HARDCODED_AUDIENCE")
    require('requirement["selected_internal_content_product_id"]' in core, "E_EXPLICIT_PRODUCT_ROUTE")
    require('requirement["primary_audience"]' in core, "E_EXPLICIT_AUDIENCE_ROUTE")
    for method, path in EXPECTED_ENDPOINTS:
        del method
        require(path in http, f"E_HTTP_ENDPOINT:{path}")
    require("ThreadingHTTPServer" in http, "E_HTTP_SERVER")
    require("TrustedUpstreamContext" in http, "E_HTTP_TRUST_CONTEXT")
    for method in REQUIRED_TEST_METHODS:
        require(f"def {method}(" in tests, f"E_REQUIRED_TEST:{method}")


def git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    require(completed.returncode == 0, f"E_GIT:{' '.join(args)}:{completed.stderr.strip()}")
    return completed.stdout.strip()


def git_file_digest(root: Path, commit: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, f"E_REVIEWED_ARTIFACT_MISSING:{path}")
    return hashlib.sha256(completed.stdout).hexdigest()


def validate_review(review: dict[str, Any], expected_id: str) -> None:
    require(review.get("schema_version") == "v1.0", f"E_REVIEW_SCHEMA:{expected_id}")
    require(review.get("task_id") == TASK_ID, f"E_REVIEW_TASK:{expected_id}")
    require(review.get("review_id") == expected_id, f"E_REVIEW_ID:{expected_id}")
    require(review.get("verdict") == "PASS", f"E_REVIEW_VERDICT:{expected_id}")
    require(review.get("hard_veto") is False, f"E_REVIEW_VETO:{expected_id}")
    score = review.get("score")
    require(isinstance(score, int) and score >= 90, f"E_REVIEW_SCORE:{expected_id}")
    for key in ("reviewer_identity", "reviewer_session_id", "reviewer_run_id", "reviewed_candidate_commit"):
        require(isinstance(review.get(key), str) and review[key], f"E_REVIEW_BINDING:{expected_id}:{key}")
    artifacts = review.get("reviewed_artifacts")
    require(isinstance(artifacts, list) and artifacts, f"E_REVIEW_ARTIFACTS:{expected_id}")


def validate_reviews(root: Path, result: dict[str, Any]) -> None:
    if result.get("state") == "CANDIDATE_READY_PENDING_INDEPENDENT_REVIEWS":
        require(not (root / ARCH_REVIEW_PATH).exists(), "E_EARLY_ARCH_REVIEW")
        require(not (root / TRUST_REVIEW_PATH).exists(), "E_EARLY_TRUST_REVIEW")
        return
    review_result = result.get("review", {})
    candidate = review_result.get("candidate_commit")
    candidate_tree = review_result.get("candidate_tree")
    require(isinstance(candidate, str) and len(candidate) == 40, "E_CANDIDATE_COMMIT")
    require(git_output(root, "rev-parse", f"{candidate}^{{tree}}") == candidate_tree, "E_CANDIDATE_TREE")
    require(
        subprocess.run(["git", "merge-base", "--is-ancestor", candidate, "HEAD"], cwd=root).returncode == 0,
        "E_CANDIDATE_NOT_ANCESTOR",
    )
    reviews = []
    for path, expected_id, ref_key in (
        (ARCH_REVIEW_PATH, "LIGHT_EXPRESSION_ARCHITECTURE_REVIEW", "architecture_review_ref"),
        (TRUST_REVIEW_PATH, "TRUST_FACT_SAFETY_REVIEW", "trust_fact_safety_review_ref"),
    ):
        require((root / path).is_file(), f"E_REVIEW_MISSING:{path}")
        review = load_yaml(root / path)["independent_review"]
        validate_review(review, expected_id)
        require(review["reviewed_candidate_commit"] == candidate, f"E_REVIEW_CANDIDATE:{expected_id}")
        declared_ref = review_result.get(ref_key, {})
        require(declared_ref.get("path") == path.as_posix(), f"E_RESULT_REVIEW_PATH:{expected_id}")
        require(declared_ref.get("sha256") == sha256_file(root / path), f"E_RESULT_REVIEW_SHA:{expected_id}")
        for artifact in review["reviewed_artifacts"]:
            artifact_path = str(artifact.get("path", ""))
            declared_sha = artifact.get("sha256")
            require(artifact_path.startswith(PACKAGE_ROOT.as_posix() + "/"), f"E_REVIEW_ARTIFACT_SCOPE:{artifact_path}")
            require(git_file_digest(root, candidate, artifact_path) == declared_sha, f"E_REVIEW_ARTIFACT_SHA:{artifact_path}")
            if Path(artifact_path) not in PACKAGE7_SUCCESSOR_EXTENSION_PATHS:
                require(
                    sha256_file(root / artifact_path) == declared_sha,
                    f"E_REVIEWED_ARTIFACT_DRIFT:{artifact_path}",
                )
        reviews.append(review)
    identities = {review["reviewer_identity"] for review in reviews}
    sessions = {review["reviewer_session_id"] for review in reviews}
    runs = {review["reviewer_run_id"] for review in reviews}
    require(len(identities) == len(sessions) == len(runs) == 2, "E_REVIEWER_NOT_INDEPENDENT")
    require("codex-execution-primary" not in identities, "E_AUTHOR_AS_REVIEWER")
    require(review_result.get("both_scores_at_least_90") is True, "E_RESULT_REVIEW_PASS")
    require(review_result.get("Root_approval") == "PENDING", "E_ROOT_PREAPPROVED")


def validate_repository(root: Path, run_tests: bool = True) -> dict[str, Any]:
    for path in REQUIRED_PACKAGE_PATHS:
        require((root / path).is_file(), f"E_REQUIRED_FILE:{path}")
    actual_files = {
        path.relative_to(root)
        for path in (root / PACKAGE_ROOT).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    allowed_files = REQUIRED_PACKAGE_PATHS | OPTIONAL_REVIEW_PATHS
    require(actual_files.issubset(allowed_files), f"E_UNDECLARED_PACKAGE_FILE:{sorted(actual_files - allowed_files)}")
    for path, expected in PUBLIC_PINS.items():
        require(sha256_file(root / path) == expected, f"E_PUBLIC_CONTRACT_DRIFT:{path}")
    for path, (expected_count, expected_sha) in HISTORICAL_ASSET_PINS.items():
        require(sha256_file(root / path) == expected_sha, f"E_HISTORICAL_ASSET_DRIFT:{path}")
        with (root / path).open("r", encoding="utf-8") as handle:
            require(sum(1 for line in handle if line.strip()) == expected_count, f"E_HISTORICAL_COUNT:{path}")
    manifest = load_yaml(root / MANIFEST_PATH)["light_expression_service_manifest"]
    result = load_yaml(root / RESULT_PATH)["light_expression_service_result"]
    validate_manifest(manifest)
    validate_result(result)
    validate_source_shape(root)
    validate_all_readiness_false(load_yaml(root / STATUS_PATH), "current_product_status")
    validate_all_readiness_false(load_yaml(root / WORKSPACE_MANIFEST_PATH), "product_workspace_manifest")
    workflow = (root / WORKFLOW_PATH).read_text(encoding="utf-8")
    checker_rel = (PACKAGE_ROOT / "check_light_expression_service.py").as_posix()
    require(workflow.count(checker_rel) == 2, "E_WORKFLOW_REGISTRATION")
    require("Run reserved downstream package checks" in workflow, "E_WORKFLOW_NORMAL")
    require("Verify reserved downstream package fail-closed optimized mode" in workflow, "E_WORKFLOW_OPTIMIZED")
    package_readme = (root / PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
    require("Light Expression Service" in package_readme, "E_README_TITLE")
    require("check_light_expression_service.py" in package_readme, "E_README_CHECK_ENTRY")
    validate_reviews(root, result)
    if run_tests:
        completed = subprocess.run(
            [sys.executable, str(TEST_PATH)],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        )
        require(completed.returncode == 0, f"E_FOCUSED_TESTS:\n{completed.stdout}")
    return {
        "task_id": TASK_ID,
        "verdict": "PASS",
        "state": result["state"],
        "endpoint_count": 4,
        "core_numbers": [300, 120, 86],
        "global_readiness_all_false": True,
        "package_digest": canonical_digest(manifest),
    }


def expect_failure(call: Callable[[], None], expected_prefix: str) -> None:
    try:
        call()
    except GateFailure as exc:
        require(str(exc).startswith(expected_prefix), f"E_SELFTEST_WRONG_FAILURE:{exc}")
        return
    raise GateFailure(f"E_SELFTEST_FALSE_NEGATIVE:{expected_prefix}")


def run_selftest(root: Path) -> dict[str, Any]:
    manifest = load_yaml(root / MANIFEST_PATH)["light_expression_service_manifest"]
    result = load_yaml(root / RESULT_PATH)["light_expression_service_result"]

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["readiness"]["production_ready"] = True
    expect_failure(lambda: validate_manifest(mutated_manifest), "E_READINESS_TRUE")

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["runtime_boundaries"]["external_model_call_count"] = 1
    expect_failure(lambda: validate_manifest(mutated_manifest), "E_RUNTIME_BOUNDARY")

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["trust_boundary"]["request_body_may_register_fact_or_fragment"] = True
    expect_failure(lambda: validate_manifest(mutated_manifest), "E_CLIENT_EVIDENCE_REGISTRATION")

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["authorized_package7_successor_extension"][
        "injected_profile_may_grant_fact_or_scope"
    ] = True
    expect_failure(lambda: validate_manifest(mutated_manifest), "E_SUCCESSOR_SCOPE_GRANT")

    mutated_result = copy.deepcopy(result)
    mutated_result["core_numbers"]["target_case_baseline"] = 301
    expect_failure(lambda: validate_result(mutated_result), "E_RESULT_CORE_NUMBERS")

    expect_failure(
        lambda: validate_implementation_source("import openai\n", Path("mutated_service.py")),
        "E_FORBIDDEN_IMPLEMENTATION_IMPORT",
    )
    expect_failure(
        lambda: validate_implementation_source("eval('1 + 1')\n", Path("mutated_service.py")),
        "E_DYNAMIC_EXECUTION",
    )

    review = {
        "schema_version": "v1.0",
        "task_id": TASK_ID,
        "review_id": "LIGHT_EXPRESSION_ARCHITECTURE_REVIEW",
        "verdict": "PASS",
        "hard_veto": False,
        "score": 89,
        "reviewer_identity": "reviewer-a",
        "reviewer_session_id": "session-a",
        "reviewer_run_id": "run-a",
        "reviewed_candidate_commit": "0" * 40,
        "reviewed_artifacts": [{"path": "x", "sha256": "y"}],
    }
    expect_failure(
        lambda: validate_review(review, "LIGHT_EXPRESSION_ARCHITECTURE_REVIEW"),
        "E_REVIEW_SCORE",
    )
    return {"task_id": TASK_ID, "selftest": "PASS", "negative_case_count": 8}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_selftest(ROOT) if args.selftest else validate_repository(ROOT)
    except (GateFailure, KeyError, TypeError, ValueError, OSError, yaml.YAMLError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
