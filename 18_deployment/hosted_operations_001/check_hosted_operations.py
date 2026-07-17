#!/usr/bin/env python3
"""Fail-closed Package 8 checker without database, cloud, or model access."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, cast

import yaml  # type: ignore[import-untyped]


if not __debug__:
    sys.stderr.write("check_hosted_operations refuses python -O\n")
    raise SystemExit(2)


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_RELATIVE_ROOT = Path("18_deployment/hosted_operations_001")
BASELINE_COMMIT = "f046ec6e3d1a34345c97292e9ab1f5a13a2bd031"
TASK_ID = "DIYU_HOSTED_OPERATIONS_001"
EXPECTED_ACCEPTANCE_RUN_DIGEST = (
    "91fd614e2c78257bbb1c5398d410dcc4bebc3cd7de3f2ae2b1c270dc606cc435"
)
EXPECTED_BACKUP_DUMP_SHA256 = (
    "59c565abdc5c0cfefa1ff385cb27f89e67e31e2c83b6d4be6d4e45d8d2b90391"
)
EXPECTED_RELEASE_OBJECT_COUNT = 38
RESULT_PATH = Path("result/hosted_operations_result.v1.json")
DELIVERY_PATH = Path("delivery/execution_review_request.v1.yaml")
REVIEW_PATHS = (
    Path("review/deployment_recovery_operations_review.v1.yaml"),
    Path("review/brand_import_isolation_security_review.v1.yaml"),
)
EXPECTED_REVIEW_TYPES = {
    "DEPLOYMENT_RECOVERY_OPERATIONS",
    "BRAND_IMPORT_ISOLATION_SECURITY",
}
EXPECTED_FILES = {
    Path("RUNBOOK.md"),
    Path("brand_bundle.py"),
    Path("brand_input_template.v1.yaml"),
    Path("check_hosted_operations.py"),
    Path("dify_materialization_manifest.v1.json"),
    Path("evidence/postgresql_acceptance_evidence.v1.json"),
    Path("fixtures/authorized_real_brand_contract_fixture.v1.yaml"),
    Path("fixtures/second_brand_fixture.v1.yaml"),
    Path("hosted_models.py"),
    Path("hosted_operations.py"),
    Path("hosted_operations_manifest.v1.json"),
    Path("operations.py"),
    Path("test_hosted_operations.py"),
    RESULT_PATH,
    DELIVERY_PATH,
    *REVIEW_PATHS,
}
AUTHORIZED_P7_CHANGES = {
    Path("17_dify_runtime/dify_end_to_end_001/brand_import.py"),
    Path("17_dify_runtime/dify_end_to_end_001/brand_import_contract.v1.yaml"),
    Path("17_dify_runtime/dify_end_to_end_001/deploy_remote.sh"),
    Path("17_dify_runtime/dify_end_to_end_001/persistence.py"),
    Path("17_dify_runtime/dify_end_to_end_001/provision_dify.py"),
    Path("17_dify_runtime/dify_end_to_end_001/runtime_models.py"),
    Path("17_dify_runtime/dify_end_to_end_001/runtime_retrieval.py"),
    Path("17_dify_runtime/dify_end_to_end_001/runtime_service.py"),
}
AUTHORIZED_CENTRAL_CHANGES = {
    Path(".github/workflows/ci.yml"),
    Path("ci/checkers/check_gate1_v1_1_current.py"),
    Path("ci/checkers/check_product_foundation.py"),
}
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
)


class CheckFailure(RuntimeError):
    """One deterministic Package 8 validation failure."""


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
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def command(args: list[str], *, expected: int = 0) -> str:
    completed = subprocess.run(
        args,
        cwd=REPOSITORY_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    require(
        completed.returncode == expected,
        f"E_COMMAND:{args}:{completed.returncode}:{completed.stdout[-500:]}",
    )
    return completed.stdout


def validate_readiness(readiness: Mapping[str, Any]) -> None:
    require(
        REQUIRED_FALSE_FLAGS <= set(readiness),
        "E_READINESS_FIELDS",
    )
    require(
        all(readiness[name] is False for name in REQUIRED_FALSE_FLAGS),
        "E_READINESS_UNLOCKED",
    )


def validate_manifest_hash(root: Path, item: Mapping[str, Any], code: str) -> None:
    path = item.get("path")
    digest = item.get("sha256")
    require(isinstance(path, str) and isinstance(digest, str), f"{code}:FIELDS")
    target = root / cast(str, path)
    require(target.is_file(), f"{code}:MISSING")
    require(sha256_file(target) == digest, f"{code}:DIGEST")


def validate_manifests(root: Path) -> None:
    hosted = read_json(PACKAGE_ROOT / "hosted_operations_manifest.v1.json")
    require(hosted.get("task_id") == TASK_ID, "E_MANIFEST_TASK")
    require(hosted.get("package7_merge_commit") == BASELINE_COMMIT, "E_MANIFEST_BASE")
    require(hosted.get("external_model_calls_allowed") is False, "E_MANIFEST_MODEL")
    require(hosted.get("real_cloud_mutations_allowed") is False, "E_MANIFEST_CLOUD")
    require(
        hosted.get("hosted_operations_entrypoint")
        == "18_deployment/hosted_operations_001/hosted_operations.py",
        "E_MANIFEST_ENTRYPOINT",
    )
    require(
        hosted.get("core_numbers")
        == {
            "120": "UNCHANGED_HISTORICAL_SCOPE",
            "300": "UNCHANGED_NOT_FROZEN",
            "86": "UNCHANGED_HISTORICAL_SCOPE",
        },
        "E_MANIFEST_CORE_NUMBERS",
    )
    require(hosted.get("application_version") == "package8-v1.1", "E_APP_VERSION")
    modes = hosted.get("brand_import_modes", {})
    require(
        modes.get("simulation") is True
        and modes.get("authorized_real") is True
        and modes.get(
            "authorized_real_requires_source_authorization_time_revocation_and_operator_confirmation"
        )
        is True
        and modes.get("authorized_real_success_does_not_grant_publication") is True,
        "E_BRAND_MODES",
    )
    require(
        hosted.get("database_isolation")
        == {
            "database_rls_enabled": False,
            "enforcement": "APPLICATION_SCOPE_AND_CURRENT_STATE_POSTCHECK",
            "package9_production_hardening_required": True,
            "production_ready": False,
        },
        "E_MANIFEST_DATABASE_ISOLATION",
    )
    require(
        hosted.get("database_backup_security")
        == {
            "contains_credential_verifiers": True,
            "contains_plaintext_secrets": False,
            "repository_commit_allowed": False,
            "restricted_storage_required": True,
        },
        "E_MANIFEST_BACKUP_SECURITY",
    )
    validate_readiness(hosted.get("readiness", {}))
    validate_manifest_hash(root, hosted.get("second_brand_fixture", {}), "E_FIXTURE")
    validate_manifest_hash(
        root,
        hosted.get("authorized_real_contract_fixture", {}),
        "E_REAL_FIXTURE",
    )
    validate_manifest_hash(root, hosted.get("template", {}), "E_TEMPLATE")
    require(
        hosted.get("release_recovery")
        == {
            "database_backup_plus_offline_release_bundle": True,
            "isolated_restore_rematerialization_verified": True,
            "release_object_digest_and_version_required": True,
        },
        "E_RELEASE_RECOVERY",
    )
    require(
        hosted.get("runtime_dify_materialization")
        == {
            "deterministic": True,
            "dify_consumes_database_projection": True,
            "second_retrieval_truth_created": False,
            "withdrawn_expired_inactive_or_unauthorized_excluded": True,
        },
        "E_RUNTIME_MATERIALIZATION",
    )
    materialization = read_json(PACKAGE_ROOT / "dify_materialization_manifest.v1.json")
    require(materialization.get("task_id") == TASK_ID, "E_DIFY_TASK")
    require(materialization.get("real_dify_import_performed") is False, "E_DIFY_REMOTE")
    require(materialization.get("secrets_included") is False, "E_DIFY_SECRET")
    validate_manifest_hash(
        root, materialization["application_definition"], "E_DIFY_APP"
    )
    validate_manifest_hash(root, materialization["bridge"], "E_DIFY_BRIDGE")
    validate_manifest_hash(root, materialization["package7_manifest"], "E_DIFY_P7")
    validate_manifest_hash(
        root,
        materialization["brand_import_contract"],
        "E_DIFY_BRAND_CONTRACT",
    )
    validate_manifest_hash(
        root,
        {
            "path": materialization["runtime_materialization"]["materializer_path"],
            "sha256": materialization["runtime_materialization"]["materializer_sha256"],
        },
        "E_DIFY_MATERIALIZER",
    )
    for label, path_key, digest_key, code in (
        (
            "dify_import_consumer",
            "provisioner_path",
            "provisioner_sha256",
            "E_DIFY_PROVISIONER",
        ),
        (
            "dify_import_consumer",
            "deployment_entrypoint_path",
            "deployment_entrypoint_sha256",
            "E_DIFY_DEPLOYMENT_ENTRYPOINT",
        ),
        (
            "release_recovery",
            "backup_entrypoint_path",
            "backup_entrypoint_sha256",
            "E_DIFY_BACKUP_ENTRYPOINT",
        ),
    ):
        validate_manifest_hash(
            root,
            {
                "path": materialization[label][path_key],
                "sha256": materialization[label][digest_key],
            },
            code,
        )
    require(
        materialization["application_definition"].get("singleton") is True,
        "E_DIFY_APP_SINGLETON",
    )
    require(
        materialization["bridge"].get("singleton") is True,
        "E_DIFY_BRIDGE_SINGLETON",
    )
    require(
        materialization["runtime_materialization"].get("truth_count") == 1
        and materialization["runtime_materialization"].get(
            "second_retrieval_truth_created"
        )
        is False
        and materialization["dify_import_consumer"].get(
            "static_package5_fragment_path_allowed"
        )
        is False,
        "E_DIFY_RETRIEVAL_SINGLETON",
    )
    require(
        materialization["release_recovery"].get("minimum_runtime_file_closure_included")
        is True
        and materialization["release_recovery"].get("offline_release_object_count")
        == EXPECTED_RELEASE_OBJECT_COUNT,
        "E_DIFY_RELEASE_INVENTORY",
    )


def validate_brand_fixture() -> None:
    sys.path.insert(0, str(PACKAGE_ROOT))
    try:
        from brand_bundle import compile_brand_bundle, load_brand_input
        from brand_import import preflight_brand_bundle

        fixture = load_brand_input(
            PACKAGE_ROOT / "fixtures/second_brand_fixture.v1.yaml"
        )
        bundle = compile_brand_bundle(fixture)
        preflight = preflight_brand_bundle(bundle)
        real_fixture = load_brand_input(
            PACKAGE_ROOT / "fixtures/authorized_real_brand_contract_fixture.v1.yaml"
        )
        real_bundle = compile_brand_bundle(real_fixture)
        real_preflight = preflight_brand_bundle(real_bundle)
    finally:
        sys.path.pop(0)
    require(preflight.get("state") == "CAN_IMPORT", "E_BRAND_PREFLIGHT")
    require(preflight.get("account_count") == 2, "E_BRAND_ACCOUNT_COUNT")
    tenant = bundle.identity.get("tenant", {})
    require(tenant.get("tenant_id") == "TENANT-QINGHE-LAB", "E_BRAND_TENANT")
    require(
        tenant.get("brand_id") == "BRAND-QINGHE-LAB--QINGHE-HOME",
        "E_BRAND_ID",
    )
    require(tenant.get("simulation_only") is True, "E_BRAND_SIMULATION")
    require(tenant.get("publish_allowed") is False, "E_BRAND_PUBLISH")
    require(
        real_preflight.get("state") == "CAN_IMPORT"
        and real_preflight.get("data_mode") == "AUTHORIZED_REAL"
        and real_preflight.get("simulation_only") is False
        and real_preflight.get("test_fixture_only") is True,
        "E_REAL_BRAND_PREFLIGHT",
    )
    require(
        real_bundle.identity.get("tenant", {}).get("publish_allowed") is False,
        "E_REAL_BRAND_PUBLISH",
    )
    accounts = bundle.identity.get("content_accounts", [])
    require(
        any(row.get("display_name") == "笛语童装" for row in accounts),
        "E_SAME_LABEL_CASE",
    )
    require(
        len(bundle.narrative_fragments) == 2 and len(bundle.precise_facts) == 4,
        "E_BRAND_CONTENT_COUNTS",
    )
    fixture_text = (PACKAGE_ROOT / "fixtures/second_brand_fixture.v1.yaml").read_text(
        encoding="utf-8"
    )
    require("（虚构）" in fixture_text, "E_BRAND_FICTION_DISCLOSURE")
    require("route_migration" not in fixture_text, "E_BRAND_INTERNAL_ROUTE")
    require("component_id" not in fixture_text, "E_BRAND_INTERNAL_COMPONENT")
    real_fixture_text = (
        PACKAGE_ROOT / "fixtures/authorized_real_brand_contract_fixture.v1.yaml"
    ).read_text(encoding="utf-8")
    require("safe_fixture_data: true" in real_fixture_text, "E_REAL_FIXTURE_DISCLOSURE")
    require("sk-" not in real_fixture_text, "E_REAL_FIXTURE_SECRET")


def validate_source_and_files() -> None:
    actual = {
        path.relative_to(PACKAGE_ROOT)
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    require(
        actual == EXPECTED_FILES,
        f"E_FILE_SET:{sorted(map(str, actual ^ EXPECTED_FILES))}",
    )
    operational_source = (PACKAGE_ROOT / "hosted_operations.py").read_text(
        encoding="utf-8"
    )
    for command_name in (
        "preflight",
        "install",
        "initialize",
        "import",
        "update",
        "revoke",
        "materialize-dify",
        "backup",
        "restore",
        "rollback",
        "health",
        "upgrade",
    ):
        require(
            f'"{command_name}"' in operational_source,
            f"E_COMMAND_MISSING:{command_name}",
        )
    require("sqlite" not in operational_source.casefold(), "E_SQLITE_OPERATIONAL")
    operations_source = (PACKAGE_ROOT / "operations.py").read_text(encoding="utf-8")
    require(
        "pg_dump" in operations_source and "pg_restore" in operations_source,
        "E_PG_BACKUP",
    )
    require("pg_advisory_xact_lock" in operations_source, "E_PG_CONCURRENCY")
    require(
        "--single-transaction" in operations_source
        and "--exit-on-error" in operations_source,
        "E_PG_RESTORE_ATOMIC",
    )
    require(
        "ix_hosted_brand_revision_tenant_digest" in operations_source,
        "E_PG_SCHEMA_MIGRATION",
    )
    require("sqlite" not in operations_source.casefold(), "E_SQLITE_ACCEPTANCE")
    provision_source = (
        REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001/provision_dify.py"
    ).read_text(encoding="utf-8")
    deployment_source = (
        REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001/deploy_remote.sh"
    ).read_text(encoding="utf-8")
    require(
        "PACKAGE8_DIFY_MATERIALIZATION_MANIFEST_PATH" in provision_source
        and "resolve_materialized_fragments" in provision_source
        and "PACKAGE7_FRAGMENTS_PATH" not in provision_source,
        "E_DIFY_RUNTIME_MATERIALIZATION_CONSUMER",
    )
    require(
        "PACKAGE8_DIFY_MATERIALIZATION_MANIFEST_PATH" in deployment_source
        and "PACKAGE7_FRAGMENTS_PATH" not in deployment_source
        and "15_brand_retrieval/brand_fact_retrieval_001/data/retrieval_fragments"
        not in deployment_source,
        "E_DIFY_STATIC_FRAGMENT_DEPENDENCY",
    )
    require(
        "active_runtime_brand"
        not in (
            REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001/runtime_retrieval.py"
        ).read_text(encoding="utf-8"),
        "E_ACTIVE_BRAND_RETRIEVAL",
    )
    require(
        "active_runtime_brand"
        not in (
            REPOSITORY_ROOT / "17_dify_runtime/dify_end_to_end_001/runtime_service.py"
        ).read_text(encoding="utf-8"),
        "E_ACTIVE_BRAND_SERVICE",
    )
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file() and path.suffix in {".py", ".json", ".yaml", ".md"}
    )
    for pattern in SECRET_PATTERNS:
        require(
            pattern.search(source_text) is None, f"E_SECRET_PATTERN:{pattern.pattern}"
        )


def validate_acceptance_evidence(evidence: Mapping[str, Any]) -> None:
    required_true = {
        "install_idempotent",
        "brand_import_idempotent",
        "concurrent_import_serialized",
        "failed_import_rolled_back",
        "same_display_name_scope_safe",
        "bidirectional_brand_isolation",
        "revocation_immediate",
        "stale_candidate_rejected",
        "bundle_rollback_restored",
        "bundle_omission_removed",
        "failed_upgrade_rolled_back",
        "schema_upgrade_changed_structure",
        "successful_upgrade_and_rollback",
        "fresh_namespace_restore_equal",
        "full_database_snapshot_equal",
        "snapshot_mismatch_rejected",
        "corrupt_backup_rejected",
        "incompatible_backup_rejected",
        "failed_restore_left_target_empty",
        "unknown_restore_objects_cleaned",
        "selected_candidate_rechecked_after_revocation",
        "authorized_real_brand_contract_imported",
        "missing_real_brand_authorization_rejected",
        "runtime_database_materialization_deterministic",
        "second_simulated_brand_materialized",
        "revoked_expired_inactive_unauthorized_excluded",
        "dify_import_consumes_runtime_materialization",
        "release_bundle_inventory_complete",
        "release_bundle_missing_object_rejected",
        "release_bundle_damaged_object_rejected",
        "release_bundle_version_mismatch_rejected",
        "restored_materialization_digest_equal",
    }
    require(evidence.get("task_id") == TASK_ID, "E_EVIDENCE_TASK")
    require(evidence.get("database_kind") == "POSTGRESQL_14", "E_EVIDENCE_DB")
    require(all(evidence.get(key) is True for key in required_true), "E_EVIDENCE_FLAGS")
    require(evidence.get("external_model_calls") == 0, "E_EVIDENCE_MODEL_CALLS")
    require(evidence.get("real_cloud_mutations") == 0, "E_EVIDENCE_CLOUD")
    require(
        evidence.get("local_task_database_count_after_cleanup") == 0,
        "E_EVIDENCE_CLEANUP",
    )
    database_names = evidence.get("database_names")
    require(
        isinstance(database_names, list)
        and len(database_names) == 3
        and len(set(database_names)) == 3
        and all(
            isinstance(name, str) and name.startswith("diyu-pkg8-")
            for name in database_names
        ),
        "E_EVIDENCE_DATABASE_NAMES",
    )
    command_contract = evidence.get("acceptance_command_contract", {})
    require(
        command_contract.get("test_path")
        == "18_deployment/hosted_operations_001/test_hosted_operations.py"
        and command_contract.get("database_url_env") == "DIYU_PKG8_ADMIN_DATABASE_URL"
        and command_contract.get("report_env") == "DIYU_PKG8_ACCEPTANCE_REPORT"
        and command_contract.get("local_only") is True
        and command_contract.get("remote_ci_database_replay_allowed") is False
        and command_contract.get("exit_code") == 0,
        "E_EVIDENCE_COMMAND_CONTRACT",
    )
    require(
        command_contract.get("test_file_sha256")
        == sha256_file(PACKAGE_ROOT / "test_hosted_operations.py"),
        "E_EVIDENCE_TEST_DIGEST",
    )
    require(
        evidence.get("postgresql_server_version_num", 0) >= 140000,
        "E_EVIDENCE_PG_VERSION",
    )
    require(
        str(evidence.get("pg_dump_version", "")).startswith("pg_dump (PostgreSQL) 14")
        and str(evidence.get("pg_restore_version", "")).startswith(
            "pg_restore (PostgreSQL) 14"
        ),
        "E_EVIDENCE_PG_TOOLS",
    )
    require(
        evidence.get("backup_security")
        == {
            "contains_credential_verifiers": True,
            "contains_plaintext_secrets": False,
            "repository_commit_allowed": False,
            "restricted_storage_required": True,
        },
        "E_EVIDENCE_BACKUP_SECURITY",
    )
    require(
        evidence.get("backup_dump_sha256") == EXPECTED_BACKUP_DUMP_SHA256,
        "E_EVIDENCE_BACKUP_DIGEST",
    )
    require(
        evidence.get("database_isolation")
        == {
            "database_rls_enabled": False,
            "enforcement": "APPLICATION_SCOPE_AND_CURRENT_STATE_POSTCHECK",
            "production_ready": False,
        },
        "E_EVIDENCE_DATABASE_ISOLATION",
    )
    runtime = evidence.get("runtime", {})
    require(runtime.get("prepared_and_validated_brand_count") == 2, "E_RUNTIME_BRANDS")
    require(runtime.get("feedback_brand_count") == 2, "E_RUNTIME_FEEDBACK")
    require(runtime.get("cross_tenant_attacks_rejected") == 2, "E_RUNTIME_ATTACKS")
    counts = evidence.get("source_object_counts", {})
    require(
        counts.get("brands") == 3 and counts.get("tenants") == 3,
        "E_EVIDENCE_COUNTS",
    )
    require(
        counts.get("candidates", 0) >= 4 and counts.get("feedback", 0) >= 2,
        "E_EVIDENCE_RUNTIME_COUNTS",
    )
    require(
        isinstance(evidence.get("release_bundle_digest"), str)
        and len(evidence["release_bundle_digest"]) == 64
        and evidence.get("release_object_count") == EXPECTED_RELEASE_OBJECT_COUNT
        and isinstance(evidence.get("materialization_digest"), str)
        and len(evidence["materialization_digest"]) == 64
        and isinstance(evidence.get("materialization_document_sha256"), str)
        and len(evidence["materialization_document_sha256"]) == 64
        and evidence.get("materialization_document_count", 0) >= 3,
        "E_EVIDENCE_RELEASE_MATERIALIZATION",
    )
    source_health = evidence.get("source_health", {})
    require(
        source_health.get("object_counts") == counts
        and source_health.get("database_table_count") == 23
        and isinstance(source_health.get("database_snapshot_digest"), str)
        and len(source_health["database_snapshot_digest"]) == 64,
        "E_EVIDENCE_DATABASE_SNAPSHOT",
    )
    recorded_run_digest = evidence.get("acceptance_run_digest")
    require(
        isinstance(recorded_run_digest, str)
        and recorded_run_digest == EXPECTED_ACCEPTANCE_RUN_DIGEST,
        "E_EVIDENCE_RUN_DIGEST_PIN",
    )
    digest_payload = copy.deepcopy(dict(evidence))
    digest_payload.pop("acceptance_run_digest", None)
    require(
        digest_json(digest_payload) == recorded_run_digest,
        "E_EVIDENCE_RUN_DIGEST_REPLAY",
    )


def git_changed_paths() -> set[Path]:
    output = command(["git", "diff", "--name-only", f"{BASELINE_COMMIT}...HEAD"])
    return {Path(line) for line in output.splitlines() if line.strip()}


def validate_diff_scope() -> None:
    changed = git_changed_paths()
    allowed = AUTHORIZED_P7_CHANGES | AUTHORIZED_CENTRAL_CHANGES
    unauthorized = sorted(
        path
        for path in changed
        if path not in allowed and not path.is_relative_to(PACKAGE_RELATIVE_ROOT)
    )
    require(not unauthorized, f"E_DIFF_SCOPE:{unauthorized}")
    require(AUTHORIZED_P7_CHANGES <= changed, "E_P7_MINIMUM_CHANGE_SET")
    forbidden_p7 = [
        path
        for path in changed
        if path.is_relative_to(Path("17_dify_runtime/dify_end_to_end_001"))
        and any(
            part in {"review", "evidence", "result", "delivery"} for part in path.parts
        )
    ]
    require(not forbidden_p7, f"E_P7_FROZEN_OUTPUT_CHANGED:{forbidden_p7}")


def implementation_tree_digest(commit: str) -> str:
    completed = subprocess.run(
        [
            "git",
            "ls-tree",
            "-r",
            commit,
            "17_dify_runtime/dify_end_to_end_001",
            PACKAGE_RELATIVE_ROOT.as_posix(),
            ".github/workflows/ci.yml",
            "ci/checkers/check_product_foundation.py",
            "ci/checkers/check_gate1_v1_1_current.py",
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require(completed.returncode == 0, "E_CANDIDATE_TREE_COMMAND")
    lines = [
        line
        for line in completed.stdout.splitlines()
        if not any(
            marker in line
            for marker in (
                f"\t{PACKAGE_RELATIVE_ROOT}/review/",
                f"\t{PACKAGE_RELATIVE_ROOT}/result/",
                f"\t{PACKAGE_RELATIVE_ROOT}/delivery/",
            )
        )
    ]
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def validate_reviews_and_result() -> None:
    result = read_json(PACKAGE_ROOT / RESULT_PATH)
    require(result.get("task_id") == TASK_ID, "E_RESULT_TASK")
    require(
        result.get("state") == "PASS_HOSTED_OPERATIONS_PENDING_PACKAGE_9",
        "E_RESULT_STATE",
    )
    require(result.get("external_model_calls") == 0, "E_RESULT_MODEL_CALLS")
    require(result.get("real_cloud_mutations") == 0, "E_RESULT_CLOUD")
    require(result.get("core_numbers_changed") is False, "E_RESULT_CORE_NUMBERS")
    validate_readiness(result.get("readiness", {}))
    candidate = result.get("implementation_candidate_commit")
    digest = result.get("implementation_tree_digest")
    require(isinstance(candidate, str) and len(candidate) == 40, "E_RESULT_CANDIDATE")
    require(isinstance(digest, str) and len(digest) == 64, "E_RESULT_TREE_DIGEST")
    candidate_commit = cast(str, candidate)
    tree_digest = cast(str, digest)
    require(
        implementation_tree_digest(candidate_commit) == tree_digest,
        "E_RESULT_TREE_BINDING",
    )
    command(["git", "merge-base", "--is-ancestor", candidate_commit, "HEAD"])
    reviews = [read_yaml(PACKAGE_ROOT / path) for path in REVIEW_PATHS]
    require(
        {review.get("review_type") for review in reviews} == EXPECTED_REVIEW_TYPES,
        "E_REVIEW_TYPES",
    )
    for review in reviews:
        require(review.get("task_id") == TASK_ID, "E_REVIEW_TASK")
        require(review.get("candidate_commit") == candidate, "E_REVIEW_CANDIDATE")
        require(review.get("implementation_tree_digest") == digest, "E_REVIEW_TREE")
        require(review.get("score", 0) >= 90, "E_REVIEW_SCORE")
        require(review.get("verdict") == "PASS", "E_REVIEW_VERDICT")
        require(review.get("blocking_items") == [], "E_REVIEW_BLOCKING")
        require(review.get("independent_read_only") is True, "E_REVIEW_INDEPENDENCE")
    identities = {
        (
            review.get("reviewer_identity"),
            review.get("reviewer_agent_id"),
            review.get("review_run_id"),
        )
        for review in reviews
    }
    require(len(identities) == 2, "E_REVIEW_IDENTITY_COLLISION")
    delivery = read_yaml(PACKAGE_ROOT / DELIVERY_PATH)
    require(delivery.get("task_id") == TASK_ID, "E_DELIVERY_TASK")
    require(
        delivery.get("requested_decision") == "APPROVE_PACKAGE_8_MERGE",
        "E_DELIVERY_DECISION",
    )
    require(
        delivery.get("implementation_candidate_commit") == candidate,
        "E_DELIVERY_CANDIDATE",
    )


def run_regressions() -> None:
    command(
        [
            sys.executable,
            "18_deployment/hosted_operations_001/test_hosted_operations.py",
        ]
    )
    command(
        [
            sys.executable,
            "12_expression_service/expression_runtime_adapter_001/test_light_expression_service.py",
        ]
    )
    command(
        [
            sys.executable,
            "16_composition_runtime/fact_aware_plan_adapter_001/test_fact_aware_plan_adapter.py",
        ]
    )
    command(
        [sys.executable, "17_dify_runtime/dify_end_to_end_001/test_dify_end_to_end.py"]
    )


def run_live() -> None:
    validate_source_and_files()
    validate_manifests(REPOSITORY_ROOT)
    validate_brand_fixture()
    validate_acceptance_evidence(
        read_json(PACKAGE_ROOT / "evidence/postgresql_acceptance_evidence.v1.json")
    )
    validate_diff_scope()
    validate_reviews_and_result()
    run_regressions()


def expect_failure(code: str, action: Callable[[], None]) -> None:
    try:
        action()
    except CheckFailure as exc:
        require(code in str(exc), f"E_SELFTEST_WRONG_FAILURE:{code}:{exc}")
        return
    raise CheckFailure(f"E_SELFTEST_FALSE_NEGATIVE:{code}")


def run_selftest() -> None:
    readiness = {name: False for name in REQUIRED_FALSE_FLAGS}
    readiness["production_ready"] = True
    expect_failure("E_READINESS_UNLOCKED", lambda: validate_readiness(readiness))
    evidence = read_json(
        PACKAGE_ROOT / "evidence/postgresql_acceptance_evidence.v1.json"
    )
    changed = copy.deepcopy(evidence)
    changed["fresh_namespace_restore_equal"] = False
    expect_failure("E_EVIDENCE_FLAGS", lambda: validate_acceptance_evidence(changed))
    changed = copy.deepcopy(evidence)
    changed["external_model_calls"] = 1
    expect_failure(
        "E_EVIDENCE_MODEL_CALLS", lambda: validate_acceptance_evidence(changed)
    )
    changed = copy.deepcopy(evidence)
    changed["runtime"]["cross_tenant_attacks_rejected"] = 0
    expect_failure("E_RUNTIME_ATTACKS", lambda: validate_acceptance_evidence(changed))
    changed = copy.deepcopy(evidence)
    changed["acceptance_command_contract"]["test_file_sha256"] = "0" * 64
    expect_failure(
        "E_EVIDENCE_TEST_DIGEST",
        lambda: validate_acceptance_evidence(changed),
    )
    changed = copy.deepcopy(evidence)
    changed["backup_security"]["contains_credential_verifiers"] = False
    expect_failure(
        "E_EVIDENCE_BACKUP_SECURITY",
        lambda: validate_acceptance_evidence(changed),
    )
    changed = copy.deepcopy(evidence)
    changed["backup_dump_sha256"] = "0" * 64
    expect_failure(
        "E_EVIDENCE_BACKUP_DIGEST",
        lambda: validate_acceptance_evidence(changed),
    )
    changed = copy.deepcopy(evidence)
    changed["release_bundle_version_mismatch_rejected"] = False
    expect_failure("E_EVIDENCE_FLAGS", lambda: validate_acceptance_evidence(changed))
    changed = copy.deepcopy(evidence)
    changed["release_object_count"] = EXPECTED_RELEASE_OBJECT_COUNT - 1
    expect_failure(
        "E_EVIDENCE_RELEASE_MATERIALIZATION",
        lambda: validate_acceptance_evidence(changed),
    )
    changed = copy.deepcopy(evidence)
    changed["source_health"]["database_snapshot_digest"] = "0" * 63
    expect_failure(
        "E_EVIDENCE_DATABASE_SNAPSHOT",
        lambda: validate_acceptance_evidence(changed),
    )
    changed = copy.deepcopy(evidence)
    changed.pop("acceptance_run_digest")
    expect_failure(
        "E_EVIDENCE_RUN_DIGEST_PIN",
        lambda: validate_acceptance_evidence(changed),
    )
    changed = copy.deepcopy(evidence)
    changed["acceptance_run_digest"] = "0" * 64
    expect_failure(
        "E_EVIDENCE_RUN_DIGEST_PIN",
        lambda: validate_acceptance_evidence(changed),
    )
    changed = copy.deepcopy(evidence)
    changed["first_initialization_state"] = "FORGED"
    changed["acceptance_run_digest"] = EXPECTED_ACCEPTANCE_RUN_DIGEST
    expect_failure(
        "E_EVIDENCE_RUN_DIGEST_REPLAY",
        lambda: validate_acceptance_evidence(changed),
    )
    invalid_item = {
        "path": "18_deployment/hosted_operations_001/brand_input_template.v1.yaml",
        "sha256": "0" * 64,
    }
    expect_failure(
        "E_SELFTEST_DIGEST",
        lambda: validate_manifest_hash(
            REPOSITORY_ROOT, invalid_item, "E_SELFTEST_DIGEST"
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        run_selftest() if args.selftest else run_live()
    except (CheckFailure, KeyError, OSError, ValueError) as exc:
        print(f"FAIL {exc}")
        return 1
    print("PASS DIYU_HOSTED_OPERATIONS_001" + (" selftest" if args.selftest else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
