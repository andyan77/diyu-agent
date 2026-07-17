#!/usr/bin/env python3
"""Deterministic, fail-closed verifier for the Package 9 ECS cutover."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, cast

import yaml  # type: ignore[import-untyped]


if not __debug__:
    sys.stderr.write("check_ecs_cutover refuses python -O\n")
    raise SystemExit(2)


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_RELATIVE_ROOT = Path("19_cloud_cutover/ecs_migration_001")
TASK_ID = "DIYU_ECS_CUTOVER_001"
PACKAGE8_MERGE_COMMIT = "e4ca0b44d5f5b64a8c7840986b716abb3be4f88d"
PACKAGE8_REVIEWED_HEAD = "e048790034c9ab20c0e570627f4e4a20d1a48cc6"
REMOTE_CODE_COMMIT = "068eac4c9758f8c3e8029eedbe35f4c32d944dc5"
RESULT_PATH = Path("result/ecs_cutover_result.v1.json")
DELIVERY_PATH = Path("delivery/execution_review_request.v1.yaml")
INVENTORY_PATH = Path("object_inventory.v1.json")
BACKUP_PATH = Path("evidence/backup_restore_evidence.v1.json")
CUTOVER_PATH = Path("evidence/remote_cutover_evidence.v1.json")
JOURNEY_PATH = Path("evidence/remote_journey_evidence.v1.json")
REVIEW_PATHS = (
    Path("review/deployment_cutover_recovery_review.v1.yaml"),
    Path("review/trust_isolation_user_journey_review.v1.yaml"),
)
SNAPSHOT_PATHS = (INVENTORY_PATH, BACKUP_PATH, CUTOVER_PATH, JOURNEY_PATH)
BASE_FILES = {
    Path("RUNBOOK.md"),
    Path("check_ecs_cutover.py"),
    Path("database_security.py"),
    Path("ecs_cutover.py"),
    Path("nginx_apps.conf.template"),
    Path("test_ecs_cutover.py"),
    INVENTORY_PATH,
    BACKUP_PATH,
    CUTOVER_PATH,
    JOURNEY_PATH,
    RESULT_PATH,
    DELIVERY_PATH,
}
AUTHORIZED_P7_CHANGES = {
    Path("17_dify_runtime/dify_end_to_end_001/bridge_app.py"),
    Path("17_dify_runtime/dify_end_to_end_001/persistence.py"),
    Path("17_dify_runtime/dify_end_to_end_001/portal.html"),
    Path("17_dify_runtime/dify_end_to_end_001/portal.js"),
    Path("17_dify_runtime/dify_end_to_end_001/provision_dify.py"),
    Path("17_dify_runtime/dify_end_to_end_001/test_dify_end_to_end.py"),
}
AUTHORIZED_CENTRAL_CHANGES = {
    Path(".github/workflows/ci.yml"),
    Path("ci/checkers/check_gate1_v1_1_current.py"),
    Path("ci/checkers/check_product_foundation.py"),
}
FROZEN_P7_EVIDENCE_PREFIXES = (
    "17_dify_runtime/dify_end_to_end_001/evidence/",
    "17_dify_runtime/dify_end_to_end_001/result/",
    "17_dify_runtime/dify_end_to_end_001/review/",
    "17_dify_runtime/dify_end_to_end_001/delivery/",
)
REQUIRED_FALSE_FLAGS = {
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "runtime_ready",
    "release_ready",
    "production_ready",
}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"Bearer [A-Za-z0-9._-]{20,}"),
    re.compile(r"postgresql(?:\+\w+)?://[^\s'\"]+:[^@\s'\"]+@"),
    re.compile(r"(?i)(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
)


class CheckFailure(RuntimeError):
    """One deterministic Package 9 validation failure."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CheckFailure(code)


def read_json(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"E_JSON_OBJECT:{path}")
    return cast(JsonObject, value)


def read_yaml(path: Path) -> JsonObject:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"E_YAML_OBJECT:{path}")
    return cast(JsonObject, value)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_json(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def snapshot_digest(root: Path) -> str:
    return digest_json(
        {path.as_posix(): sha256_file(root / path) for path in SNAPSHOT_PATHS}
    )


def run_git(args: list[str], expected: int = 0) -> str:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=environment,
    )
    require(
        completed.returncode == expected,
        f"E_GIT:{args}:{completed.returncode}:{completed.stdout[-500:]}",
    )
    return completed.stdout


def validate_readiness(readiness: Mapping[str, Any]) -> None:
    require(REQUIRED_FALSE_FLAGS <= set(readiness), "E_READINESS_FIELDS")
    require(
        all(readiness[name] is False for name in REQUIRED_FALSE_FLAGS),
        "E_READINESS_UNLOCKED",
    )


def validate_file_set(root: Path, final: bool) -> None:
    actual = {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    expected = set(BASE_FILES)
    if final:
        expected.update(REVIEW_PATHS)
    require(actual == expected, f"E_FILE_SET:{sorted(map(str, actual ^ expected))}")


def validate_inventory(root: Path) -> None:
    data = read_json(root / INVENTORY_PATH)
    require(data.get("task_id") == TASK_ID, "E_INVENTORY_TASK")
    source = data.get("source_candidate", {})
    require(source.get("commit") == REMOTE_CODE_COMMIT, "E_INVENTORY_COMMIT")
    require(source.get("release_source_file_count") == 124, "E_RELEASE_FILES")
    capacity = data.get("host_capacity", {})
    require(capacity.get("cpu_count") == 2, "E_CAPACITY_CPU")
    require(capacity.get("root_disk_free_bytes_after_cutover", 0) >= 10 * 1024**3, "E_CAPACITY_DISK")
    require(capacity.get("memory_available_bytes_after_cutover", 0) >= 1024**3, "E_CAPACITY_MEMORY")
    adopted = data.get("adopted_current_system", [])
    require(isinstance(adopted, list) and len(adopted) == 5, "E_ADOPTED_OBJECTS")
    classes = [item.get("object_class") for item in adopted]
    require(
        classes
        == [
            "DIFY_APPLICATION",
            "DIFY_DATASET",
            "RUNTIME_DATABASE",
            "THIN_BRIDGE",
            "USER_ENTRY",
        ],
        "E_SINGLE_SYSTEM_CLASSES",
    )
    require(all(item.get("count") == 1 for item in adopted[:4]), "E_SINGLE_SYSTEM_COUNTS")
    deleted = data.get("confirmed_legacy_deleted", [])
    require(isinstance(deleted, list) and len(deleted) == 7, "E_DELETE_INVENTORY")
    require(all(item.get("backup_verified_before_delete") is True for item in deleted), "E_DELETE_WITHOUT_BACKUP")
    preserved = data.get("ownership_unknown_or_shared_preserved", [])
    require(isinstance(preserved, list) and len(preserved) == 3, "E_PRESERVED_UNKNOWN")
    require(data.get("forbidden_object_mutation_count") == 0, "E_FORBIDDEN_MUTATION")
    require(data.get("unknown_object_deleted_count") == 0, "E_UNKNOWN_DELETED")
    require(data.get("parallel_diyu_system_created_count") == 0, "E_PARALLEL_SYSTEM")
    require(data.get("secrets_included") is False, "E_INVENTORY_SECRET")


def validate_backup(root: Path) -> None:
    data = read_json(root / BACKUP_PATH)
    require(data.get("task_id") == TASK_ID, "E_BACKUP_TASK")
    before = data.get("pre_cutover", {})
    after = data.get("post_cutover", {})
    require(before.get("artifact_count") == 13, "E_PRE_BACKUP_COUNT")
    require(after.get("artifact_count") == 4, "E_POST_BACKUP_COUNT")
    for label, item in (("PRE", before), ("POST", after)):
        require(item.get("location_class") == "SERVER_EXTERNAL_RESTRICTED_LOCAL_STORAGE", f"E_{label}_LOCATION")
        require(item.get("key_location_class") == "SEPARATE_SERVER_EXTERNAL_RESTRICTED_KEY_STORE", f"E_{label}_KEY_LOCATION")
        require(item.get("encryption") == "GPG_SYMMETRIC_AES256", f"E_{label}_ENCRYPTION")
        require(item.get("all_artifact_digests_verified") is True, f"E_{label}_DIGEST")
        require(item.get("all_decryptions_verified") is True, f"E_{label}_DECRYPT")
        require(item.get("plaintext_artifacts_persisted") is False, f"E_{label}_PLAINTEXT")
        require(item.get("isolated_restore", {}).get("network") == "NONE", f"E_{label}_RESTORE_NETWORK")
        require(item.get("isolated_restore", {}).get("pass") is True, f"E_{label}_RESTORE")
    require(before.get("manifest_sha256") == "2281cee2add4c103428e37be57cf98293d478319bcbbb4633a27acff1a633f85", "E_PRE_MANIFEST")
    require(after.get("manifest_sha256") == "69e464cc92e2ccaf9fb03e543a6c65c7e1ab8b563123aa1813bdd46099d170e0", "E_POST_MANIFEST")
    runtime_counts = after.get("isolated_restore", {}).get("runtime_counts", {})
    require(runtime_counts == {"tenants": 2, "accounts": 13, "fragments": 31, "candidates": 24}, "E_RESTORE_RUNTIME_COUNTS")
    require(data.get("corrupt_missing_or_version_mismatch_rejected") is True, "E_RESTORE_FAIL_CLOSED")
    require(data.get("backup_keys_in_repository") is False, "E_BACKUP_KEY")
    require(data.get("credentials_in_evidence") is False, "E_BACKUP_CREDENTIAL")


def validate_cutover(root: Path) -> None:
    data = read_json(root / CUTOVER_PATH)
    require(data.get("task_id") == TASK_ID, "E_CUTOVER_TASK")
    merge = data.get("package8_merge", {})
    require(merge.get("reviewed_head") == PACKAGE8_REVIEWED_HEAD, "E_P8_HEAD")
    require(merge.get("merge_commit") == PACKAGE8_MERGE_COMMIT, "E_P8_MERGE")
    require(merge.get("merge_method") == "MERGE_COMMIT_WITHOUT_BYPASS", "E_P8_METHOD")
    require(merge.get("checker_compatibility") == "SUCCESS" and merge.get("secret_scan") == "SUCCESS", "E_P8_CI")
    candidate = data.get("remote_candidate", {})
    require(candidate.get("code_commit") == REMOTE_CODE_COMMIT, "E_REMOTE_COMMIT")
    require(candidate.get("release_count") == 1, "E_RELEASE_COUNT")
    require(candidate.get("dify_version") == "1.15.0", "E_DIFY_VERSION")
    require(candidate.get("single_current_system") is True, "E_SINGLE_SYSTEM")
    database = data.get("database_security", {})
    require(database.get("table_count") == 23, "E_DATABASE_TABLES")
    require(database.get("forced_rls_table_count") == 19, "E_RLS_COUNT")
    require(database.get("runtime_role_login") is True, "E_RUNTIME_LOGIN")
    require(database.get("runtime_role_bypass_rls") is False, "E_RUNTIME_BYPASS")
    require(database.get("legacy_role_login") is False, "E_LEGACY_LOGIN")
    require(database.get("trusted_scope_set_server_side") is True, "E_TRUSTED_SCOPE")
    require(database.get("no_scope_visible_account_count") == 0, "E_NO_SCOPE_READ")
    require(database.get("primary_scope_account_counts") == [11, 0], "E_PRIMARY_SCOPE")
    require(database.get("second_scope_account_counts") == [2, 0, 1], "E_SECOND_SCOPE")
    for field in ("cross_tenant_write_rejected", "migration_only_read_rejected", "row_security_off_rejected"):
        require(database.get(field) is True, f"E_DATABASE_NEGATIVE:{field}")
    runtime = data.get("runtime_data", {})
    require(runtime.get("tenant_count") == 2, "E_TENANTS")
    require(runtime.get("account_count") == 13 and runtime.get("primary_account_count") == 11, "E_ACCOUNTS")
    require(runtime.get("fragment_count") == 31 and runtime.get("dify_bound_fragment_count") == 30, "E_FRAGMENTS")
    materialization = data.get("dify_materialization", {})
    require(materialization.get("source_kind") == "RUNTIME_POSTGRESQL_PROJECTION", "E_MATERIALIZATION_SOURCE")
    require(materialization.get("document_count") == 30, "E_DOCUMENT_COUNT")
    require(materialization.get("excluded_revoked_expired_or_inactive_count") == 1, "E_EXCLUDED_FRAGMENT")
    require(materialization.get("second_retrieval_truth_created") is False, "E_SECOND_TRUTH")
    entry = data.get("user_entry", {})
    require(entry.get("root_https_status") == 200 and entry.get("apps_https_status") == 200, "E_HTTPS")
    require(entry.get("login_status") == 200 and entry.get("login_account_count") == 11, "E_LOGIN")
    require(entry.get("technical_token_required_by_user") is False, "E_TECH_TOKEN")
    require(entry.get("dify_admin_exposed") is False, "E_DIFY_ADMIN")
    require(entry.get("conversation_id_persisted_per_user_scope") is True, "E_CONVERSATION")
    health = data.get("post_restart_health", {})
    require(health.get("pass") is True, "E_HEALTH")
    require(health.get("disk_free_bytes", 0) >= 10 * 1024**3, "E_HEALTH_DISK")
    require(health.get("memory_available_bytes", 0) >= 1024**3, "E_HEALTH_MEMORY")
    cleanup = data.get("exact_cleanup", {})
    require(cleanup.get("removed_ports") == [5433, 8006, 8021, 18008], "E_CLEANUP_PORTS")
    require(cleanup.get("preserved_shared_port") == 18007, "E_SHARED_PORT")
    require(cleanup.get("unknown_object_deleted_count") == 0, "E_CLEANUP_UNKNOWN")
    rollback = data.get("rollback", {})
    require(rollback.get("actual_rollback_executed") is True, "E_ROLLBACK_EXECUTED")
    require(rollback.get("rollback_and_forward_pass") is True, "E_ROLLBACK_FORWARD")
    require(rollback.get("forward_rls_table_count") == 19, "E_FORWARD_RLS")
    require(rollback.get("final_state") == "PACKAGE9_CANDIDATE", "E_FINAL_REMOTE_STATE")
    require(data.get("real_customer_data_imported") is False, "E_REAL_CUSTOMER_DATA")
    require(data.get("public_content_published") is False, "E_PUBLICATION")
    require(data.get("secrets_included") is False, "E_CUTOVER_SECRET")


def validate_journeys(root: Path) -> None:
    data = read_json(root / JOURNEY_PATH)
    require(data.get("task_id") == TASK_ID, "E_JOURNEY_TASK")
    require(data.get("journey_group_count") == 6, "E_JOURNEY_GROUPS")
    require(data.get("journey_action_count") == 15, "E_JOURNEY_ACTIONS")
    require(data.get("all_http_actions_succeeded") is True, "E_JOURNEY_HTTP")
    journeys = data.get("journey_groups", [])
    require(isinstance(journeys, list) and len(journeys) == 6, "E_JOURNEY_LIST")
    require(all(item.get("status") == "PASS" for item in journeys), "E_JOURNEY_STATUS")
    require(sum(cast(int, item.get("action_count", 0)) for item in journeys) == 15, "E_JOURNEY_ACTION_SUM")
    distribution = data.get("persisted_candidate_distribution", {})
    require(distribution == {"total": 24, "short_video": 12, "article": 9, "display": 3}, "E_FORMAT_DISTRIBUTION")
    usage = data.get("model_usage", {})
    require(usage.get("package9_invocation_increment") == 13, "E_MODEL_CALLS")
    require(usage.get("founder_authorized_call_limit") == 40, "E_MODEL_OVERRIDE")
    require(usage.get("package9_invocation_increment", 1000) <= usage.get("founder_authorized_call_limit", -1), "E_MODEL_BUDGET")
    require(usage.get("observed_cost_cny", 1000) <= usage.get("cost_limit_cny", -1), "E_MODEL_COST")
    require(usage.get("new_model_calls_frozen") is True, "E_MODEL_NOT_FROZEN")
    integrity = data.get("failure_integrity", {})
    require(integrity.get("failed_formal_attempts_preserved") is True, "E_FAILURE_NOT_PRESERVED")
    for field in ("failed_samples_deleted", "replacement_sample_used", "reroll_to_green_used", "cloud_prompt_tuning_used"):
        require(integrity.get(field) is False, f"E_JOURNEY_GAMING:{field}")
    safety = data.get("surface_safety", {})
    require(safety.get("internal_identifier_leak_count") == 0, "E_IDENTIFIER_LEAK")
    require(safety.get("technical_token_exposed_count") == 0, "E_TOKEN_LEAK")
    require(safety.get("automatic_publication_count") == 0, "E_AUTO_PUBLICATION")
    require(safety.get("publish_allowed") is False, "E_PUBLISH_ALLOWED")
    require(safety.get("ordinary_creative_surface_requires_per_sentence_evidence") is False, "E_CREATIVE_OVERBOUND")
    raw = data.get("raw_private_evidence", {})
    require(raw.get("committed_to_repository") is False, "E_RAW_PRIVATE_COMMITTED")
    require(raw.get("storage_class") == "REMOTE_ROOT_ONLY_RESTRICTED_STATE", "E_RAW_PRIVATE_STORAGE")


def validate_review(path: Path, candidate: str, tree: str, snapshot: str) -> JsonObject:
    review = read_yaml(path)
    require(review.get("task_id") == TASK_ID, f"E_REVIEW_TASK:{path}")
    require(review.get("candidate_commit") == candidate, f"E_REVIEW_COMMIT:{path}")
    require(review.get("candidate_tree") == tree, f"E_REVIEW_TREE:{path}")
    require(review.get("remote_environment_snapshot_digest") == snapshot, f"E_REVIEW_SNAPSHOT:{path}")
    require(review.get("verdict") == "PASS", f"E_REVIEW_VERDICT:{path}")
    require(isinstance(review.get("score"), int) and review["score"] >= 90, f"E_REVIEW_SCORE:{path}")
    require(review.get("blocking_items") == [], f"E_REVIEW_BLOCKERS:{path}")
    independence = review.get("independence", {})
    require(independence.get("not_author_or_migration_executor") is True, f"E_REVIEW_AUTHOR:{path}")
    require(independence.get("separate_session") is True, f"E_REVIEW_SESSION:{path}")
    require(independence.get("independent_from_other_reviewer") is True, f"E_REVIEW_OTHER:{path}")
    reviewer = review.get("reviewer", {})
    require(isinstance(reviewer.get("identity"), str) and reviewer.get("identity"), f"E_REVIEW_IDENTITY:{path}")
    require(isinstance(reviewer.get("session_id"), str) and reviewer.get("session_id"), f"E_REVIEW_SESSION_ID:{path}")
    return review


def validate_result_and_delivery(root: Path) -> bool:
    result = read_json(root / RESULT_PATH)
    delivery = read_yaml(root / DELIVERY_PATH)
    require(result.get("task_id") == TASK_ID, "E_RESULT_TASK")
    require(delivery.get("task_id") == TASK_ID, "E_DELIVERY_TASK")
    state = result.get("state")
    final = state == "PASS_REMOTE_CANDIDATE_PENDING_PACKAGE_10"
    require(state in {"PENDING_INDEPENDENT_REVIEW", "PASS_REMOTE_CANDIDATE_PENDING_PACKAGE_10"}, "E_RESULT_STATE")
    validate_file_set(root, final)
    require(result.get("remote_deployed_code_commit") == REMOTE_CODE_COMMIT, "E_RESULT_REMOTE_COMMIT")
    require(result.get("core_numbers_changed") is False, "E_CORE_NUMBERS_CHANGED")
    require(
        result.get("core_numbers")
        == {
            "300": "UNCHANGED_NOT_FROZEN",
            "120": "UNCHANGED_HISTORICAL_SCOPE",
            "86": "UNCHANGED_HISTORICAL_SCOPE",
        },
        "E_CORE_NUMBERS",
    )
    require(result.get("real_customer_data_imported") is False, "E_RESULT_CUSTOMER_DATA")
    require(result.get("automatic_publication_count") == 0, "E_RESULT_PUBLICATION")
    require(result.get("merge_allowed") is False, "E_RESULT_MERGE")
    validate_readiness(result.get("readiness", {}))
    validate_readiness(delivery.get("readiness", {}))
    assertions = delivery.get("assertions", {})
    require(assertions.get("real_customer_data_imported") is False, "E_DELIVERY_CUSTOMER_DATA")
    require(assertions.get("automatic_publication_count") == 0, "E_DELIVERY_PUBLICATION")
    require(assertions.get("production_ready_claimed") is False, "E_DELIVERY_PRODUCTION")
    require(assertions.get("package9_merge_performed") is False, "E_DELIVERY_MERGE")
    require(assertions.get("package10_started") is False, "E_DELIVERY_PACKAGE10")
    if not final:
        require(result.get("implementation_candidate_commit") == "PENDING_CANDIDATE_FREEZE", "E_PENDING_COMMIT")
        require(result.get("blocking_items") == ["INDEPENDENT_REVIEWS_PENDING"], "E_PENDING_BLOCKERS")
        require(result.get("independent_reviews") == [], "E_PENDING_REVIEWS")
        require(result.get("package10_allowed") is False, "E_PENDING_PACKAGE10")
        require(delivery.get("request_state") == "PENDING_INDEPENDENT_REVIEW", "E_PENDING_DELIVERY")
        return False
    candidate = result.get("implementation_candidate_commit")
    tree = result.get("implementation_candidate_tree")
    snapshot = result.get("remote_environment_snapshot_digest")
    require(isinstance(candidate, str) and re.fullmatch(r"[0-9a-f]{40}", candidate) is not None, "E_FINAL_COMMIT")
    require(isinstance(tree, str) and re.fullmatch(r"[0-9a-f]{40}", tree) is not None, "E_FINAL_TREE")
    require(snapshot == snapshot_digest(root), "E_FINAL_SNAPSHOT")
    require(result.get("blocking_items") == [], "E_FINAL_BLOCKERS")
    require(result.get("package10_allowed") is True, "E_FINAL_PACKAGE10")
    require(delivery.get("request_state") == "REQUEST_APPROVE_PACKAGE_9_MERGE", "E_FINAL_DELIVERY")
    require(delivery.get("requested_decision") == "APPROVE_PACKAGE_9_MERGE", "E_FINAL_REQUEST")
    for field, expected in (
        ("implementation_candidate_commit", candidate),
        ("implementation_candidate_tree", tree),
        ("remote_environment_snapshot_digest", snapshot),
    ):
        require(delivery.get(field) == expected, f"E_DELIVERY_BINDING:{field}")
    reviews = [validate_review(root / path, candidate, tree, snapshot) for path in REVIEW_PATHS]
    identities = [review["reviewer"]["identity"] for review in reviews]
    sessions = [review["reviewer"]["session_id"] for review in reviews]
    require(len(set(identities)) == 2, "E_REVIEW_IDENTITY_COLLISION")
    require(len(set(sessions)) == 2, "E_REVIEW_SESSION_COLLISION")
    require({review.get("review_type") for review in reviews} == {"DEPLOYMENT_CUTOVER_RECOVERY", "TRUST_ISOLATION_USER_JOURNEY"}, "E_REVIEW_TYPES")
    result_reviews = result.get("independent_reviews", [])
    delivery_reviews = delivery.get("reviews", [])
    require(isinstance(result_reviews, list) and len(result_reviews) == 2, "E_RESULT_REVIEW_COUNT")
    require(isinstance(delivery_reviews, list) and len(delivery_reviews) == 2, "E_DELIVERY_REVIEW_COUNT")
    require(all(item.get("score", 0) >= 90 and item.get("verdict") == "PASS" for item in result_reviews), "E_RESULT_REVIEW_SUMMARY")
    local = result.get("local_verification", {})
    require(local.get("package7_test_count") == 55 and local.get("package9_test_count") == 8, "E_TEST_COUNTS")
    for field in ("ruff_pass", "package9_checker_pass", "package9_selftest_pass", "optimized_mode_exit_2", "central_compatibility_pass", "secret_scan_pass"):
        require(local.get(field) is True, f"E_LOCAL_VERIFICATION:{field}")
    return True


def validate_secret_surface(root: Path) -> None:
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            require(pattern.search(text) is None, f"E_SECRET_PATTERN:{path}:{pattern.pattern}")


def validate_git_scope(final: bool, result: Mapping[str, Any]) -> None:
    run_git(["merge-base", "--is-ancestor", PACKAGE8_MERGE_COMMIT, "HEAD"])
    changed = {
        Path(line)
        for line in run_git(["diff", "--name-only", f"{PACKAGE8_MERGE_COMMIT}...HEAD"]).splitlines()
        if line.strip()
    }
    authorized = AUTHORIZED_P7_CHANGES | AUTHORIZED_CENTRAL_CHANGES
    unauthorized = sorted(
        path
        for path in changed
        if path not in authorized
        and not path.as_posix().startswith(f"{PACKAGE_RELATIVE_ROOT.as_posix()}/")
    )
    require(not unauthorized, f"E_GIT_SCOPE:{unauthorized}")
    require(not any(path.as_posix().startswith("18_deployment/hosted_operations_001/") for path in changed), "E_PACKAGE8_MUTATED")
    require(not any(any(path.as_posix().startswith(prefix) for prefix in FROZEN_P7_EVIDENCE_PREFIXES) for path in changed), "E_PACKAGE7_EVIDENCE_MUTATED")
    if final:
        candidate = cast(str, result["implementation_candidate_commit"])
        run_git(["merge-base", "--is-ancestor", candidate, "HEAD"])
        actual_tree = run_git(["show", "-s", "--format=%T", candidate]).strip()
        require(actual_tree == result.get("implementation_candidate_tree"), "E_CANDIDATE_TREE")
        post_candidate = {
            Path(line)
            for line in run_git(["diff", "--name-only", f"{candidate}...HEAD"]).splitlines()
            if line.strip()
        }
        allowed = {
            PACKAGE_RELATIVE_ROOT / RESULT_PATH,
            PACKAGE_RELATIVE_ROOT / DELIVERY_PATH,
            *(PACKAGE_RELATIVE_ROOT / path for path in REVIEW_PATHS),
        }
        require(post_candidate <= allowed, f"E_POST_CANDIDATE_SCOPE:{sorted(post_candidate - allowed)}")


def validate_package(root: Path, live_git: bool) -> str:
    result = read_json(root / RESULT_PATH)
    final = result.get("state") == "PASS_REMOTE_CANDIDATE_PENDING_PACKAGE_10"
    validate_file_set(root, final)
    validate_inventory(root)
    validate_backup(root)
    validate_cutover(root)
    validate_journeys(root)
    validated_final = validate_result_and_delivery(root)
    require(validated_final == final, "E_FINAL_STATE_MISMATCH")
    validate_secret_surface(root)
    if live_git:
        validate_git_scope(final, result)
    return digest_json(
        {
            "final": final,
            "snapshot": snapshot_digest(root),
            "package_file_count": len(BASE_FILES) + (len(REVIEW_PATHS) if final else 0),
        }
    )


def expect_failure(action: Callable[[], None], code_prefix: str) -> None:
    try:
        action()
    except CheckFailure as exc:
        require(str(exc).startswith(code_prefix), f"E_SELFTEST_WRONG_FAILURE:{code_prefix}:{exc}")
        return
    raise CheckFailure(f"E_SELFTEST_FALSE_NEGATIVE:{code_prefix}")


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="package9-selftest-") as temporary:
        root = Path(temporary) / "package"
        shutil.copytree(PACKAGE_ROOT, root, ignore=shutil.ignore_patterns("__pycache__"))
        baseline = validate_package(root, live_git=False)
        require(baseline == validate_package(root, live_git=False), "E_SELFTEST_NONDETERMINISTIC")

        def mutate_json(path: Path, mutation: Callable[[JsonObject], None]) -> Callable[[], None]:
            original = read_json(root / path)

            def run() -> None:
                mutated = copy.deepcopy(original)
                mutation(mutated)
                write_json(root / path, mutated)
                try:
                    validate_package(root, live_git=False)
                finally:
                    write_json(root / path, original)

            return run

        expect_failure(
            mutate_json(BACKUP_PATH, lambda value: value["pre_cutover"].update({"artifact_count": 12})),
            "E_PRE_BACKUP_COUNT",
        )
        expect_failure(
            mutate_json(CUTOVER_PATH, lambda value: value["database_security"].update({"cross_tenant_write_rejected": False})),
            "E_DATABASE_NEGATIVE",
        )
        expect_failure(
            mutate_json(INVENTORY_PATH, lambda value: value.update({"unknown_object_deleted_count": 1})),
            "E_UNKNOWN_DELETED",
        )
        expect_failure(
            mutate_json(JOURNEY_PATH, lambda value: value["model_usage"].update({"package9_invocation_increment": 41})),
            "E_MODEL_CALLS",
        )
        expect_failure(
            mutate_json(JOURNEY_PATH, lambda value: value["surface_safety"].update({"internal_identifier_leak_count": 1})),
            "E_IDENTIFIER_LEAK",
        )
        expect_failure(
            mutate_json(RESULT_PATH, lambda value: value["readiness"].update({"production_ready": True})),
            "E_READINESS_UNLOCKED",
        )
        expect_failure(
            mutate_json(RESULT_PATH, lambda value: value.update({"package10_allowed": True})),
            "E_PENDING_PACKAGE10",
        )

        extra = root / "undeclared_state.json"
        extra.write_text("{}\n", encoding="utf-8")
        try:
            expect_failure(lambda: validate_package(root, live_git=False), "E_FILE_SET")
        finally:
            extra.unlink()

        runbook = root / "RUNBOOK.md"
        original_runbook = runbook.read_text(encoding="utf-8")
        synthetic_bearer = "Bearer " + ("A" * 32)
        runbook.write_text(
            original_runbook + f"\n{synthetic_bearer}\n",
            encoding="utf-8",
        )
        try:
            expect_failure(lambda: validate_package(root, live_git=False), "E_SECRET_PATTERN")
        finally:
            runbook.write_text(original_runbook, encoding="utf-8")

    print(json.dumps({"status": "PASS", "selftests": 9}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            run_selftest()
        else:
            digest = validate_package(PACKAGE_ROOT, live_git=True)
            print(json.dumps({"status": "PASS", "validation_digest": digest}, sort_keys=True))
    except (CheckFailure, json.JSONDecodeError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        sys.stderr.write(f"FAIL:{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
