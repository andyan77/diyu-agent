#!/usr/bin/env python3
"""Fail-closed checker for the Package 6 fact-aware plan adapter."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, cast

import yaml  # type: ignore[import-untyped]


if not __debug__:
    sys.stderr.write("check_fact_aware_plan_adapter refuses python -O\n")
    raise SystemExit(2)


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_RELATIVE_ROOT = Path("16_composition_runtime/fact_aware_plan_adapter_001")
TASK_ID = "DIYU_FACT_AWARE_PLAN_ADAPTER_001"
MANIFEST_PATH = Path("adapter_manifest.v1.yaml")
FIXTURE_PATH = Path("fixtures/integration_cases.v1.jsonl")
RESULT_PATH = Path("result/fact_aware_plan_adapter_result.v1.yaml")
DELIVERY_PATH = Path("delivery/execution_review_request.v1.yaml")
REVIEW_PATHS = (
    Path("review/architecture_upstream_and_package7_consumability_review.v1.yaml"),
    Path("review/fact_authorization_privacy_isolation_review.v1.yaml"),
)
BASE_PACKAGE_FILES = frozenset(
    {
        Path("fact_aware_plan_adapter.py"),
        Path("test_fact_aware_plan_adapter.py"),
        Path("check_fact_aware_plan_adapter.py"),
        MANIFEST_PATH,
        FIXTURE_PATH,
        RESULT_PATH,
        DELIVERY_PATH,
    }
)
IMMUTABLE_PACKAGE_FILES = (
    Path("fact_aware_plan_adapter.py"),
    Path("test_fact_aware_plan_adapter.py"),
    Path("check_fact_aware_plan_adapter.py"),
    MANIFEST_PATH,
    FIXTURE_PATH,
)
CENTRAL_COMPATIBILITY_PATHS = (
    Path("ci/checkers/check_product_foundation.py"),
    Path("ci/checkers/check_gate1_v1_1_current.py"),
    Path(".github/workflows/ci.yml"),
)
CANDIDATE_SNAPSHOT_PATHS = tuple(
    PACKAGE_RELATIVE_ROOT / path for path in IMMUTABLE_PACKAGE_FILES
) + CENTRAL_COMPATIBILITY_PATHS
PACKAGE7_SUCCESSOR_EXTENSION_PATHS = frozenset(
    {
        Path("fact_aware_plan_adapter.py"),
        Path("test_fact_aware_plan_adapter.py"),
        Path("check_fact_aware_plan_adapter.py"),
        MANIFEST_PATH,
    }
)
REQUIRED_FALSE_FLAGS = frozenset(
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
EXPECTED_UPSTREAM_ANCHORS = {
    "11_product_foundation/public_foundation_001/contract/public_foundation_contract.v1.yaml":
        "a3aec92fdcc22635bb07bc5d2595ebaa5cfa1f1c9d5fad42cc39481808bbc1af",
    "11_product_foundation/public_foundation_001/identity/simulation_tenant.v1.yaml":
        "65b8242b9b760e64f8e441c4334c68fa76f6dc3a11e2fe2f8f62ad6a887c3cbc",
    "11_product_foundation/public_foundation_001/taxonomy/topic_product_mapping.v1.yaml":
        "e51f46635b6c3312e0626bc5aca448c91d20b0d71cae6a8de793ba5b603e2b95",
    "12_expression_service/expression_runtime_adapter_001/light_expression_service.py":
        "5ebabef118ce2ec96483e4a5be656431ba30e868e79ed6d86228fb5d5658bf4c",
    "12_expression_service/expression_runtime_adapter_001/neutral_expression_profile.v1.yaml":
        "30d8ce76fa49ebfad79634cbaa19f69e8d8ad5bbc09c958403dcc8847d3025c6",
    "12_expression_service/expression_runtime_adapter_001/service_manifest.v1.yaml":
        "1a8f36b5e831481ce0c48fc32c31789789ce9ed9b7e8e72c308631aefd48ac15",
    "15_brand_retrieval/brand_fact_retrieval_001/brand_fact_retrieval.py":
        "33ae09df9abb63aa796913338568e63edc6096b410a1e27670e9a378ecdef6e8",
    "15_brand_retrieval/brand_fact_retrieval_001/retrieval_manifest.v1.json":
        "bc93d0c4ac4e11f6ec9c8ce18c6d830adb6334f2f8dab20a26a1f75aa3d25d3a",
    "15_brand_retrieval/brand_fact_retrieval_001/result/brand_fact_retrieval_result.v1.json":
        "5bf0866935a2ce73400fbacc5ae4072b4736ce10562b6886a23f50dfa21fcbe8",
}
EXPECTED_REVIEW_TYPES = {
    "ARCHITECTURE_UPSTREAM_REUSE_AND_PACKAGE7_CONSUMABILITY",
    "FACT_AUTHORIZATION_PRIVACY_AND_ENTERPRISE_ISOLATION",
}
FORBIDDEN_IMPORT_ROOTS = {
    "requests",
    "httpx",
    "urllib",
    "socket",
    "openai",
    "psycopg",
    "psycopg2",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def digest_entries(entries: list[JsonObject]) -> str:
    payload = (
        json.dumps(entries, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")
    return sha256_bytes(payload)


def load_yaml_object(path: Path, root_key: str) -> JsonObject:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get(root_key), dict):
        raise ValueError(f"invalid YAML root: {path}:{root_key}")
    return cast(JsonObject, document[root_key])


def load_jsonl(path: Path) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL row: {path}:{line_number}")
        rows.append(value)
    return rows


def require_fields(
    value: Mapping[str, Any],
    required: Iterable[str],
    label: str,
    errors: list[str],
) -> None:
    missing = sorted(set(required) - set(value))
    if missing:
        errors.append(f"{label}: missing fields {missing}")


def git_object_bytes(commit: str, relative_path: Path) -> bytes:
    process = subprocess.run(
        ["git", "show", f"{commit}:{relative_path.as_posix()}"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise ValueError(f"candidate object missing: {commit}:{relative_path}")
    return process.stdout


def live_candidate_snapshot_digest(repo_root: Path = REPOSITORY_ROOT) -> str:
    entries = [
        {"path": path.as_posix(), "sha256": sha256_file(repo_root / path)}
        for path in CANDIDATE_SNAPSHOT_PATHS
    ]
    return digest_entries(entries)


def committed_candidate_snapshot_digest(commit: str) -> str:
    entries = [
        {
            "path": path.as_posix(),
            "sha256": sha256_bytes(git_object_bytes(commit, path)),
        }
        for path in CANDIDATE_SNAPSHOT_PATHS
    ]
    return digest_entries(entries)


def validate_file_set(
    package_root: Path, require_reviews: bool, errors: list[str]
) -> None:
    actual = {
        path.relative_to(package_root)
        for path in package_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    expected = BASE_PACKAGE_FILES | (
        frozenset(REVIEW_PATHS) if require_reviews else frozenset()
    )
    if actual != expected:
        errors.append(
            f"package file set mismatch: missing={sorted(map(str, expected - actual))}, "
            f"extra={sorted(map(str, actual - expected))}"
        )


def validate_manifest(
    package_root: Path, repo_root: Path, errors: list[str]
) -> JsonObject:
    manifest = load_yaml_object(
        package_root / MANIFEST_PATH, "fact_aware_plan_adapter_manifest"
    )
    require_fields(
        manifest,
        {
            "schema_version",
            "task_id",
            "package_number",
            "baseline_master_commit",
            "package_root",
            "upstream_anchors",
            "entrypoints",
            "ownership",
            "material_access",
            "coverage",
            "expression_boundary",
            "external_calls",
            "generated_content",
            "core_numbers",
            "readiness",
        },
        "manifest",
        errors,
    )
    if manifest.get("task_id") != TASK_ID or manifest.get("package_number") != 6:
        errors.append("manifest task or package number mismatch")
    anchors = manifest.get("upstream_anchors")
    if anchors != EXPECTED_UPSTREAM_ANCHORS:
        errors.append("manifest upstream anchor set mismatch")
    for relative, expected in EXPECTED_UPSTREAM_ANCHORS.items():
        path = repo_root / relative
        if not path.is_file() or sha256_file(path) != expected:
            errors.append(f"upstream byte drift: {relative}")
    ownership = manifest.get("ownership")
    if not isinstance(ownership, dict) or not (
        ownership.get("package2_owns_light_content_plan") is True
        and ownership.get("package2_owns_action_card") is True
        and ownership.get("package2_owns_plan_store") is True
        and ownership.get("package5_owns_retrieval_and_scope_filtering") is True
        and ownership.get("second_plan_contract_created") is False
        and ownership.get("second_fact_or_context_bundle_created") is False
        and ownership.get("second_http_service_created") is False
    ):
        errors.append("manifest ownership boundary mismatch")
    coverage = manifest.get("coverage")
    expected_coverage = {
        "capability_case_count": 20,
        "topic_category_count": 8,
        "internal_content_product_count": 20,
        "evidence_backed_plan_case_count": 10,
        "honest_action_card_case_count": 10,
        "unit_test_count": 16,
    }
    if not isinstance(coverage, dict) or any(
        coverage.get(key) != value for key, value in expected_coverage.items()
    ):
        errors.append("manifest coverage counts mismatch")
    expression = manifest.get("expression_boundary")
    if not isinstance(expression, dict) or not (
        expression.get("formal_enterprise_profile_created") is False
        and expression.get("neutral_default_profile_used") is True
        and expression.get("approved_package5_example_count_passed_to_package2") == 0
        and expression.get("high_level_modes_are_soft_guidance_only") is True
    ):
        errors.append("expression authority boundary mismatch")
    successor = manifest.get("authorized_package7_successor_extension")
    if not isinstance(successor, dict) or not (
        successor.get("task_id") == "DIYU_DIFY_END_TO_END_001"
        and successor.get("historical_review_remains_as_built") is True
        and successor.get("current_extension_review_owned_by_package7") is True
        and successor.get("trusted_context_factory_is_server_only") is True
        and successor.get("expression_profile_resolver_is_server_only") is True
        and successor.get("package2_plan_and_action_card_ownership_preserved") is True
        and successor.get("second_plan_or_context_created") is False
    ):
        errors.append("Package 7 successor compatibility contract mismatch")
    validate_closed_boundaries(manifest, errors, "manifest")
    return manifest


def validate_closed_boundaries(
    value: Mapping[str, Any], errors: list[str], label: str
) -> None:
    external = value.get("external_calls")
    if not isinstance(external, dict) or not external or any(
        amount != 0 for amount in external.values()
    ):
        errors.append(f"{label} external calls must be measured zero")
    readiness = value.get("readiness")
    if not isinstance(readiness, dict) or any(
        readiness.get(flag) is not False for flag in REQUIRED_FALSE_FLAGS
    ):
        errors.append(f"{label} readiness must remain false")
    numbers = value.get("core_numbers")
    expected_numbers = {
        "target_300": 300,
        "frozen_reference_120": 120,
        "historical_component_inventory_86": 86,
        "changed_or_harmed": False,
    }
    if numbers != expected_numbers:
        errors.append(f"{label} core numbers mismatch")


def validate_fixtures(
    package_root: Path, repo_root: Path, errors: list[str]
) -> None:
    rows = load_jsonl(package_root / FIXTURE_PATH)
    if len(rows) != 20:
        errors.append("capability fixture count must be 20")
        return
    products = [str(row.get("content_product_id")) for row in rows]
    topics = {str(row.get("topic_category_id")) for row in rows}
    if set(products) != {f"CP{index:02d}" for index in range(1, 21)} or len(products) != len(set(products)):
        errors.append("capability fixtures must cover each product exactly once")
    if topics != {f"TOPIC-{index:02d}" for index in range(1, 9)}:
        errors.append("capability fixtures must cover all eight topics")
    mapping = load_yaml_object(
        repo_root
        / "11_product_foundation/public_foundation_001/taxonomy/topic_product_mapping.v1.yaml",
        "topic_product_mapping",
    )
    allowed = {
        str(row["topic_category_id"]): set(row["internal_product_ids"])
        for row in mapping["categories"]
    }
    plan_count = 0
    action_count = 0
    for row in rows:
        require_fields(
            row,
            {
                "case_id",
                "topic_category_id",
                "content_product_id",
                "query_text",
                "expected_result_type",
            },
            "capability fixture",
            errors,
        )
        topic = str(row.get("topic_category_id"))
        product = str(row.get("content_product_id"))
        if product not in allowed.get(topic, set()):
            errors.append(f"fixture topic/product mapping invalid: {topic}/{product}")
        outcome = row.get("expected_result_type")
        if outcome == "LIGHT_CONTENT_PLAN":
            plan_count += 1
            if not str(row.get("query_text", "")).strip():
                errors.append(f"plan fixture has no evidence query: {row.get('case_id')}")
        elif outcome == "ACTION_CARD":
            action_count += 1
        else:
            errors.append(f"unknown fixture result type: {row.get('case_id')}")
        if "approved_example_refs" in row or "audience_body" in row:
            errors.append(f"fixture carries forbidden example or audience body: {row.get('case_id')}")
    if (plan_count, action_count) != (10, 10):
        errors.append("fixture plan/action distribution must remain honest 10/10")


def validate_source(package_root: Path, errors: list[str]) -> None:
    source_path = package_root / "fact_aware_plan_adapter.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    classes: set[str] = set()
    called_attributes: set[str] = set()
    string_constants: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called_attributes.add(node.func.attr)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            string_constants[node.targets[0].id] = node.value.value
    forbidden = imported_roots & FORBIDDEN_IMPORT_ROOTS
    if forbidden:
        errors.append(f"external runtime imports forbidden: {sorted(forbidden)}")
    if "FactAwarePlanAdapter" not in classes:
        errors.append("single adapter entrypoint class missing")
    if classes & {
        "LightContentPlan",
        "ActionCard",
        "TrustedUpstreamContext",
        "ContextBundle",
        "FactBundle",
        "PlanStore",
        "HTTPServer",
    }:
        errors.append("parallel upstream contract, store, context, or service class created")
    for required_call in ("retrieve", "prepare", "validate"):
        if required_call not in called_attributes:
            errors.append(f"upstream entrypoint call missing: {required_call}")
    if string_constants.get("START_CREATION") != "START_CREATION":
        errors.append("public START_CREATION intent is not bound exactly")
    text = source_path.read_text(encoding="utf-8")
    if "approved_example_refs\": []" not in text:
        errors.append("Package 5 candidate examples are not forced empty")
    for token in (
        "trusted_context_factory",
        "expression_profile_resolver",
        "self.expression_service.action_card(",
    ):
        if token not in text:
            errors.append(f"Package 7 successor injection point missing: {token}")


def validate_result_and_delivery(
    package_root: Path,
    require_reviews: bool,
    errors: list[str],
) -> tuple[JsonObject, JsonObject]:
    result = load_yaml_object(
        package_root / RESULT_PATH, "fact_aware_plan_adapter_result"
    )
    delivery = load_yaml_object(
        package_root / DELIVERY_PATH, "execution_review_request"
    )
    validate_closed_boundaries(result, errors, "result")
    expected_counts = {
        "capability_cases": 20,
        "topic_categories": 8,
        "internal_content_products": 20,
        "evidence_backed_plan_cases": 10,
        "honest_action_card_cases": 10,
        "fixed_structural_validation_candidates": 1,
        "generated_audience_candidates": 0,
    }
    if result.get("task_id") != TASK_ID or result.get("counts") != expected_counts:
        errors.append("result task or counts mismatch")
    checks = result.get("checks")
    required_true_checks = {
        "package5_retrieve_called",
        "package2_prepare_called",
        "package2_validate_called",
        "server_scope_spoof_blocked",
        "exact_material_projection_proven",
        "deterministic_replay_proven",
        "all_20_products_have_plan_or_action",
        "all_8_topics_covered",
        "no_atom_dependency_proven",
        "semantic_and_aesthetic_review_pending",
    }
    if not isinstance(checks, dict) or any(
        checks.get(key) is not True for key in required_true_checks
    ):
        errors.append("result required checks missing")
    if not isinstance(checks, dict) or not (
        checks.get("package5_hold_records_consumed") is False
        and checks.get("second_plan_or_context_created") is False
    ):
        errors.append("result forbidden consumption or duplicate ownership claim")
    if delivery.get("task_id") != TASK_ID or delivery.get("merge_authorization") != "NOT_GRANTED":
        errors.append("delivery request authority mismatch")
    if delivery.get("package7_unlocked") is not False:
        errors.append("delivery request must not unlock Package 7")
    if require_reviews:
        if result.get("status") != "PASS_FACT_AWARE_PLAN_ADAPTER_PENDING_PACKAGE_7":
            errors.append("final result status mismatch")
        if delivery.get("status") != "REQUESTING_APPROVE_PACKAGE_6_MERGE":
            errors.append("final delivery status mismatch")
    else:
        if result.get("status") != "CANDIDATE_PENDING_INDEPENDENT_REVIEWS":
            errors.append("pre-review result status mismatch")
        if delivery.get("status") != "PENDING_INDEPENDENT_REVIEWS":
            errors.append("pre-review delivery status mismatch")
        if result.get("candidate_commit") != "PENDING" or result.get("candidate_snapshot_digest") != "PENDING":
            errors.append("pre-review candidate identity must be pending")
        if result.get("independent_reviews") != []:
            errors.append("pre-review result must not self-assert reviews")
    return result, delivery


def validate_reviews(
    package_root: Path,
    result: JsonObject,
    delivery: JsonObject,
    errors: list[str],
) -> None:
    candidate = result.get("candidate_commit")
    if not isinstance(candidate, str) or len(candidate) != 40:
        errors.append("final candidate commit invalid")
        return
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate, "HEAD"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        errors.append("reviewed candidate is not an ancestor of HEAD")
        return
    try:
        expected_snapshot = committed_candidate_snapshot_digest(candidate)
    except ValueError as exc:
        errors.append(str(exc))
        return
    if result.get("candidate_snapshot_digest") != expected_snapshot:
        errors.append("result candidate snapshot digest mismatch")
    if (
        delivery.get("candidate_commit") != candidate
        or delivery.get("candidate_snapshot_digest") != expected_snapshot
    ):
        errors.append("delivery request candidate binding mismatch")
    for relative in IMMUTABLE_PACKAGE_FILES:
        try:
            expected_bytes = git_object_bytes(candidate, PACKAGE_RELATIVE_ROOT / relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        path = package_root / relative
        if (
            relative not in PACKAGE7_SUCCESSOR_EXTENSION_PATHS
            and (not path.is_file() or path.read_bytes() != expected_bytes)
        ):
            errors.append(f"frozen Package 6 candidate changed: {relative}")

    reviews: list[JsonObject] = []
    for relative in REVIEW_PATHS:
        try:
            reviews.append(load_yaml_object(package_root / relative, "review"))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    if len(reviews) != 2:
        return
    identities: set[str] = set()
    sessions: set[str] = set()
    runs: set[str] = set()
    review_types: set[str] = set()
    summaries: list[JsonObject] = []
    for review in reviews:
        require_fields(
            review,
            {
                "schema_version",
                "review_id",
                "task_id",
                "review_type",
                "reviewer_identity",
                "reviewer_session_id",
                "reviewer_run_id",
                "candidate_commit",
                "candidate_snapshot_digest",
                "score",
                "verdict",
                "hard_blockers",
                "acceptance_ids",
                "signed_at",
            },
            "review",
            errors,
        )
        identities.add(str(review.get("reviewer_identity")))
        sessions.add(str(review.get("reviewer_session_id")))
        runs.add(str(review.get("reviewer_run_id")))
        review_types.add(str(review.get("review_type")))
        score = review.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 90 <= score <= 100:
            errors.append("review score must be integer 90..100")
        if review.get("task_id") != TASK_ID:
            errors.append("review task mismatch")
        if review.get("candidate_commit") != candidate or review.get("candidate_snapshot_digest") != expected_snapshot:
            errors.append("review candidate binding mismatch")
        if review.get("verdict") != "PASS" or review.get("hard_blockers") != []:
            errors.append("review must PASS without hard blocker")
        acceptance_ids = review.get("acceptance_ids")
        if not isinstance(acceptance_ids, list) or not acceptance_ids:
            errors.append("review acceptance ids missing")
        summaries.append(
            {
                "review_id": review.get("review_id"),
                "reviewer_identity": review.get("reviewer_identity"),
                "score": score,
                "verdict": review.get("verdict"),
            }
        )
    if len(identities) != 2 or len(sessions) != 2 or len(runs) != 2:
        errors.append("independent review identity, session, and run must differ")
    if review_types != EXPECTED_REVIEW_TYPES:
        errors.append("independent review type set mismatch")
    if result.get("independent_reviews") != summaries:
        errors.append("result independent review summary mismatch")


def run_tests(package_root: Path, errors: list[str]) -> None:
    process = subprocess.run(
        [sys.executable, "test_fact_aware_plan_adapter.py"],
        cwd=package_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        errors.append(f"Package 6 integration tests failed: {process.stderr[-2000:]}")


def validate_package(
    package_root: Path = PACKAGE_ROOT,
    *,
    repo_root: Path = REPOSITORY_ROOT,
    require_reviews: bool,
    run_test_suite: bool = True,
) -> list[str]:
    errors: list[str] = []
    try:
        validate_file_set(package_root, require_reviews, errors)
        validate_manifest(package_root, repo_root, errors)
        validate_fixtures(package_root, repo_root, errors)
        validate_source(package_root, errors)
        result, delivery = validate_result_and_delivery(
            package_root, require_reviews, errors
        )
        if require_reviews:
            validate_reviews(package_root, result, delivery, errors)
        if run_test_suite:
            run_tests(package_root, errors)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        errors.append(f"package load failure: {exc}")
    return errors


def selftest(require_reviews: bool) -> list[str]:
    failures: list[str] = []
    mutations: tuple[tuple[str, Path, Any], ...] = (
        (
            "readiness flip",
            MANIFEST_PATH,
            lambda path: path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "runtime_ready: false", "runtime_ready: true", 1
                ),
                encoding="utf-8",
            ),
        ),
        (
            "duplicate product fixture",
            FIXTURE_PATH,
            lambda path: path.write_text(
                path.read_text(encoding="utf-8").replace(
                    '"content_product_id":"CP20"',
                    '"content_product_id":"CP19"',
                    1,
                ),
                encoding="utf-8",
            ),
        ),
        (
            "external import",
            Path("fact_aware_plan_adapter.py"),
            lambda path: path.write_text(
                f"import socket\n{path.read_text(encoding='utf-8')}",
                encoding="utf-8",
            ),
        ),
        (
            "unsupported creation intent alias",
            Path("fact_aware_plan_adapter.py"),
            lambda path: path.write_text(
                path.read_text(encoding="utf-8").replace(
                    'START_CREATION = "START_CREATION"',
                    'START_CREATION = "START_CONTENT_PRODUCTION"',
                    1,
                ),
                encoding="utf-8",
            ),
        ),
        (
            "external call claim",
            RESULT_PATH,
            lambda path: path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "network: 0", "network: 1", 1
                ),
                encoding="utf-8",
            ),
        ),
    )
    for label, relative, mutate in mutations:
        with tempfile.TemporaryDirectory(prefix="pkg6-selftest-") as directory:
            temp_package = Path(directory) / "package"
            shutil.copytree(
                PACKAGE_ROOT,
                temp_package,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            mutate(temp_package / relative)
            errors = validate_package(
                temp_package,
                require_reviews=require_reviews,
                run_test_suite=False,
            )
            if not errors:
                failures.append(f"selftest mutation was not rejected: {label}")
    with tempfile.TemporaryDirectory(prefix="pkg6-selftest-extra-") as directory:
        temp_package = Path(directory) / "package"
        shutil.copytree(
            PACKAGE_ROOT,
            temp_package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (temp_package / "parallel_plan_contract.yaml").write_text("forbidden: true\n", encoding="utf-8")
        errors = validate_package(
            temp_package,
            require_reviews=require_reviews,
            run_test_suite=False,
        )
        if not errors:
            failures.append("selftest mutation was not rejected: parallel extra file")
    if require_reviews:
        with tempfile.TemporaryDirectory(prefix="pkg6-selftest-review-") as directory:
            temp_package = Path(directory) / "package"
            shutil.copytree(
                PACKAGE_ROOT,
                temp_package,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            review = temp_package / REVIEW_PATHS[0]
            review.write_text(
                review.read_text(encoding="utf-8").replace("score: 9", "score: 8", 1),
                encoding="utf-8",
            )
            errors = validate_package(
                temp_package,
                require_reviews=True,
                run_test_suite=False,
            )
            if not errors:
                failures.append("selftest mutation was not rejected: review score")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-review", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_reviews = not args.pre_review
    errors = validate_package(require_reviews=require_reviews)
    if args.selftest:
        errors.extend(selftest(require_reviews))
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    mode = "final" if require_reviews else "pre-review"
    snapshot = (
        "review-bound"
        if require_reviews
        else live_candidate_snapshot_digest(REPOSITORY_ROOT)
    )
    print(
        f"PASS: Package 6 fact-aware plan adapter ({mode}, "
        f"20 products, snapshot={snapshot})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
