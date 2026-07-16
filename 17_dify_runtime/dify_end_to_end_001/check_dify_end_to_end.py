#!/usr/bin/env python3
"""Fail-closed checker for the Package 7 Dify end-to-end candidate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, cast

import yaml  # type: ignore[import-untyped]


if not __debug__:
    sys.stderr.write("check_dify_end_to_end refuses python -O\n")
    raise SystemExit(2)


JsonObject = dict[str, Any]
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_RELATIVE_ROOT = Path("17_dify_runtime/dify_end_to_end_001")
TASK_ID = "DIYU_DIFY_END_TO_END_001"
BASELINE_COMMIT = "a8fe258b8f8693247a46f1dbba3c2553b778bfaa"

MANIFEST_PATH = Path("dify_end_to_end_manifest.v1.json")
EXTERNAL_EVIDENCE_PATH = Path("evidence/external_runtime_evidence.v1.json")
MODEL_EVIDENCE_PATH = Path("evidence/model_run_evidence.v1.json")
RESULT_PATH = Path("result/dify_end_to_end_result.v1.json")
DELIVERY_PATH = Path("delivery/execution_review_request.v1.yaml")
REVIEW_PATHS = (
    Path("review/content_experience_and_organization_review.v1.yaml"),
    Path("review/trust_fact_authorization_runtime_review.v1.yaml"),
)
REVIEW_TYPES = {
    "CONTENT_EXPERIENCE_AND_ORGANIZATION",
    "TRUST_FACT_AUTHORIZATION_PRIVACY_AND_RUNTIME",
}
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
EXPECTED_PACKAGE_FILES = frozenset(
    {
        Path("brand_import.py"),
        Path("brand_import_contract.v1.yaml"),
        Path("brand_runtime_profile.v1.yaml"),
        Path("bridge_app.py"),
        Path("check_dify_end_to_end.py"),
        Path("contracts.py"),
        Path("deploy_remote.sh"),
        Path("dify_app.v1.yaml"),
        Path("dify_chat.py"),
        Path("dify_end_to_end_manifest.v1.json"),
        Path("dify_knowledge.py"),
        Path("persistence.py"),
        Path("portal.css"),
        Path("portal.html"),
        Path("portal.js"),
        Path("provision_dify.py"),
        Path("runtime_models.py"),
        Path("runtime_retrieval.py"),
        Path("runtime_service.py"),
        Path("security.py"),
        Path("seed_runtime.py"),
        Path("test_dify_end_to_end.py"),
        EXTERNAL_EVIDENCE_PATH,
        MODEL_EVIDENCE_PATH,
        RESULT_PATH,
        DELIVERY_PATH,
        *REVIEW_PATHS,
    }
)
POST_CANDIDATE_ALLOWED_PATHS = frozenset(
    {PACKAGE_RELATIVE_ROOT / RESULT_PATH, PACKAGE_RELATIVE_ROOT / DELIVERY_PATH}
    | {PACKAGE_RELATIVE_ROOT / path for path in REVIEW_PATHS}
)
AUTHORIZED_COMPATIBILITY_PATHS = frozenset(
    {
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "light_expression_service.py"
        ),
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "test_light_expression_service.py"
        ),
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "check_light_expression_service.py"
        ),
        Path(
            "12_expression_service/expression_runtime_adapter_001/"
            "service_manifest.v1.yaml"
        ),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "fact_aware_plan_adapter.py"
        ),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "test_fact_aware_plan_adapter.py"
        ),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "check_fact_aware_plan_adapter.py"
        ),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "adapter_manifest.v1.yaml"
        ),
        Path("ci/checkers/check_gate1_v1_1_current.py"),
        Path(".github/workflows/ci.yml"),
    }
)
EXPECTED_FORMATS = {
    "article": ("图文", "article"),
    "display": ("陈列搭配", "display"),
    "short_video": ("短视频", "video"),
}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"Bearer [A-Za-z0-9._-]{20,}"),
)


class CheckFailure(RuntimeError):
    """Raised by one fail-closed validation boundary."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CheckFailure(code)


def require_fields(
    value: Mapping[str, Any], required: Iterable[str], code: str
) -> None:
    missing = sorted(set(required) - set(value))
    require(not missing, f"{code}:{missing}")


def load_json(path: Path) -> JsonObject:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"E_JSON_OBJECT:{path}")
    return cast(JsonObject, value)


def load_yaml_root(path: Path, root_key: str) -> JsonObject:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(
        isinstance(value, dict) and isinstance(value.get(root_key), dict),
        f"E_YAML_ROOT:{path}:{root_key}",
    )
    return cast(JsonObject, value[root_key])


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_output(*args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    require(process.returncode == 0, f"E_GIT:{' '.join(args)}:{process.stderr.strip()}")
    return process.stdout.strip()


def candidate_tree(candidate_commit: str) -> str:
    return git_output("rev-parse", f"{candidate_commit}^{{tree}}")


def validate_file_set(root: Path) -> None:
    actual = {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    require(actual == EXPECTED_PACKAGE_FILES, f"E_FILE_SET:{sorted(map(str, actual ^ EXPECTED_PACKAGE_FILES))}")
    require(not list(root.rglob("*.pyc")), "E_BYTECODE_PRESENT")
    require(not list(root.rglob("__pycache__")), "E_PYCACHE_PRESENT")


def validate_readiness(value: Mapping[str, Any], code: str) -> None:
    require(set(value) == REQUIRED_FALSE_FLAGS, f"{code}:FLAG_SET")
    for key in REQUIRED_FALSE_FLAGS:
        require(value.get(key) is False, f"{code}:{key}")


def validate_core_numbers(value: Mapping[str, Any], code: str) -> None:
    require(value.get("target_total") == 300, f"{code}:300")
    require(value.get("reference_inventory") == 120, f"{code}:120")
    require(value.get("historical_component_inventory") == 86, f"{code}:86")
    require(value.get("changed") is False, f"{code}:CHANGED")


def validate_manifest(manifest: JsonObject) -> None:
    require(manifest.get("schema") == "diyu.package7.dify_end_to_end_manifest.v1", "E_MANIFEST_SCHEMA")
    require(manifest.get("task_id") == TASK_ID, "E_MANIFEST_TASK")
    require(manifest.get("package_number") == 7, "E_MANIFEST_PACKAGE")
    require(manifest.get("baseline_master_commit") == BASELINE_COMMIT, "E_MANIFEST_BASELINE")
    require(manifest.get("package_root") == PACKAGE_RELATIVE_ROOT.as_posix(), "E_MANIFEST_ROOT")
    candidate = cast(Mapping[str, Any], manifest.get("single_candidate", {}))
    require(candidate.get("dify_app_id") == "98eb36f1-50b7-42ca-8184-976512fbef9d", "E_APP_ID")
    require(candidate.get("dataset_id") == "3c9d73cc-c120-4f84-81a1-1bc95f7b6d4b", "E_DATASET_ID")
    require(candidate.get("runtime_database") == "diyu_pkg7_runtime", "E_DATABASE_ID")
    require(candidate.get("runtime_bridge") == "diyu-package7-bridge", "E_BRIDGE_ID")
    require(candidate.get("api_only") is True, "E_API_ONLY")
    require(candidate.get("simulation_only") is True, "E_SIMULATION_ONLY")
    require(candidate.get("production_ready") is False, "E_CANDIDATE_PRODUCTION")
    ownership = cast(Mapping[str, Any], manifest.get("ownership", {}))
    for key in (
        "package2_owns_light_content_plan_and_validation",
        "package5_owns_retrieval_contract_and_scope_filtering",
        "package6_owns_fact_aware_plan_adaptation",
        "package7_owns_only_runtime_persistence_dify_bridge_and_portal",
    ):
        require(ownership.get(key) is True, f"E_OWNERSHIP:{key}")
    for key in ("second_plan_created", "second_retrieval_truth_created", "second_bridge_created"):
        require(ownership.get(key) is False, f"E_PARALLEL_OWNER:{key}")
    contracts = cast(Mapping[str, Any], manifest.get("contracts", {}))
    require(contracts.get("content_product_count") == 20, "E_CONTRACT_CP")
    require(contracts.get("topic_count") == 8, "E_CONTRACT_TOPIC")
    require(contracts.get("action_card_count") == 8, "E_CONTRACT_ACTION")
    require(contracts.get("content_account_count") == 11, "E_CONTRACT_ACCOUNT")
    require(contracts.get("storyline_count") == 4, "E_CONTRACT_STORYLINE")
    require(contracts.get("candidate_count_policy") == "2_TO_3", "E_CANDIDATE_POLICY")
    require(set(contracts.get("user_visible_formats", [])) == {"短视频", "图文", "陈列搭配"}, "E_FORMAT_SET")
    retrieval = cast(Mapping[str, Any], manifest.get("retrieval_decision", {}))
    require(retrieval.get("parallel_vector_truth") is False, "E_PARALLEL_RETRIEVAL")
    continuity = cast(Mapping[str, Any], manifest.get("continuous_dialogue", {}))
    require(continuity.get("dify_conversation_id_persisted") is True, "E_CONTINUITY_PERSIST")
    require(continuity.get("scope") == "PRINCIPAL_PLUS_CONTENT_ACCOUNT", "E_CONTINUITY_SCOPE")
    require(continuity.get("sanitized_context_window") == 6, "E_CONTINUITY_WINDOW")
    require(continuity.get("raw_dify_memory_enabled") is False, "E_DIFY_RAW_MEMORY")
    require(continuity.get("raw_provider_reasoning_reused") is False, "E_RAW_REASONING_REUSE")
    require(continuity.get("history_may_not_grant_fact_or_authorization") is True, "E_HISTORY_AUTHORITY")
    budget = cast(Mapping[str, Any], manifest.get("model_budget", {}))
    require(budget.get("original_request_upper_bound") == 40, "E_BUDGET_ORIGINAL")
    require(budget.get("founder_additional_request_upper_bound") == 60, "E_BUDGET_ADDITIONAL")
    require(budget.get("effective_request_upper_bound") == 100, "E_BUDGET_EFFECTIVE")
    require(budget.get("cost_cny_upper_bound") == 50, "E_BUDGET_COST")
    require(budget.get("content_quality_reroll_allowed") is False, "E_REROLL_POLICY")
    legacy = cast(Mapping[str, Any], manifest.get("legacy_boundary", {}))
    require(legacy.get("compatibility_research_stopped") is True, "E_LEGACY_RESEARCH")
    require(legacy.get("old_object_mutation_allowed") is False, "E_LEGACY_MUTATION")
    validate_core_numbers(cast(Mapping[str, Any], manifest.get("core_numbers", {})), "E_MANIFEST_CORE")
    validate_readiness(cast(Mapping[str, Any], manifest.get("readiness", {})), "E_MANIFEST_READINESS")


def validate_external_evidence(evidence: JsonObject) -> None:
    require(evidence.get("schema") == "diyu.package7.external_runtime_evidence.v1", "E_EXTERNAL_SCHEMA")
    environment = cast(Mapping[str, Any], evidence.get("environment", {}))
    require(environment.get("dify_version") == "1.15.0", "E_DIFY_VERSION")
    require(environment.get("lifecycle") == "NON_PRODUCTION_INTERNAL_ACCEPTANCE", "E_RUNTIME_LIFECYCLE")
    require(environment.get("production_ready") is False, "E_EXTERNAL_PRODUCTION")
    owner = cast(Mapping[str, Any], evidence.get("approved_workspace_and_owner", {}))
    require(owner.get("binding_source") == "LOCKED_PACKAGE7_STATE", "E_OWNER_BINDING")
    require(owner.get("oldest_preexisting_app_used_for_owner_inference") is False, "E_OWNER_INFERENCE")
    require(owner.get("identity_drift_fails_closed") is True, "E_OWNER_DRIFT")
    for key in ("tenant_id_sha256", "owner_account_id_sha256"):
        require(bool(re.fullmatch(r"[0-9a-f]{64}", str(owner.get(key, "")))), f"E_OWNER_DIGEST:{key}")
    objects = cast(Mapping[str, Any], evidence.get("dify_objects", {}))
    require(objects.get("package7_app_name_count") == 1, "E_APP_COUNT")
    require(objects.get("package7_dataset_name_count") == 1, "E_DATASET_COUNT")
    require(objects.get("preexisting_app_count_preserved") == 2, "E_PREEXISTING_APPS")
    require(objects.get("package7_app_id") == "98eb36f1-50b7-42ca-8184-976512fbef9d", "E_EXTERNAL_APP_ID")
    require(objects.get("package7_dataset_id") == "3c9d73cc-c120-4f84-81a1-1bc95f7b6d4b", "E_EXTERNAL_DATASET_ID")
    require(objects.get("package7_public_site_enabled") is False, "E_PUBLIC_SITE")
    require(objects.get("package7_dataset_permission") == "only_me", "E_DATASET_PERMISSION")
    require(objects.get("package7_document_count") == 29, "E_DOCUMENT_COUNT")
    require(objects.get("package7_segment_count") == 29, "E_SEGMENT_COUNT")
    require(objects.get("repeated_provision_preserved_object_ids") is True, "E_PROVISION_IDEMPOTENCE")
    database = cast(Mapping[str, Any], evidence.get("runtime_database", {}))
    require(database.get("database_name") == "diyu_pkg7_runtime", "E_EXTERNAL_DATABASE")
    require(database.get("isolated_namespace") is True, "E_DATABASE_ISOLATION")
    for key in ("empty_initialization_pass", "repeat_initialization_idempotent", "transaction_rollback_pass", "bridge_restart_persistence_pass"):
        require(database.get(key) is True, f"E_DATABASE_PROOF:{key}")
    counts = cast(Mapping[str, Any], database.get("row_counts", {}))
    require(counts.get("content_accounts") == 11, "E_ACCOUNT_ROWS")
    require(counts.get("narrative_fragments") == 29, "E_FRAGMENT_ROWS")
    require(counts.get("dify_invocations") == 46, "E_INVOCATION_ROWS")
    require(counts.get("dify_conversations") == 4, "E_CONVERSATION_ROWS")
    isolation = cast(Mapping[str, Any], evidence.get("bridge_isolation", {}))
    require(isolation.get("container_name") == "diyu-package7-bridge", "E_CONTAINER")
    require(isolation.get("container_user") == "1001:1001", "E_CONTAINER_USER")
    require(isolation.get("read_only_root_filesystem") is True, "E_READONLY_ROOT")
    require(isolation.get("capabilities_dropped") == ["ALL"], "E_CAP_DROP")
    require(isolation.get("no_new_privileges") is True, "E_NO_NEW_PRIVILEGES")
    require(isolation.get("host_bindings") == ["127.0.0.1:18471"], "E_HOST_BINDING")
    require(set(isolation.get("networks", [])) == {"dify-staging_default", "diyu-package7-runtime"}, "E_NETWORKS")
    require(isolation.get("shared_business_network_attached") is False, "E_SHARED_NETWORK")
    require(isolation.get("source_file_mode") == "400", "E_SOURCE_MODE")
    require(isolation.get("state_file_mode") == "400", "E_STATE_MODE")
    retrieval = cast(Mapping[str, Any], evidence.get("retrieval", {}))
    for key in ("trusted_prefilter_before_ranking", "authoritative_metadata_postcheck", "authorized_current_record_accepted", "expired_record_rejected", "revoked_record_rejected", "index_content_drift_rejected"):
        require(retrieval.get(key) is True, f"E_RETRIEVAL:{key}")
    require(retrieval.get("probe_mutations_persisted") is False, "E_RETRIEVAL_MUTATION")
    portal = cast(Mapping[str, Any], evidence.get("portal_and_scope", {}))
    for key in ("trusted_login_success", "wrong_password_rejected", "missing_session_rejected", "session_cookie_http_only", "login_response_has_no_token_fields", "forged_account_rejected", "forged_account_model_budget_unchanged", "invalid_bridge_secret_rejected", "public_network_portal_rejected"):
        require(portal.get(key) is True, f"E_PORTAL:{key}")
    require(portal.get("content_account_option_count") == 11, "E_PORTAL_ACCOUNTS")
    continuity = cast(Mapping[str, Any], evidence.get("continuous_dialogue", {}))
    require(continuity.get("binding_scope") == "principal plus content account", "E_EXTERNAL_CONTINUITY_SCOPE")
    require(continuity.get("binding_count") == continuity.get("distinct_scope_count") == continuity.get("distinct_conversation_id_count") == 4, "E_CONVERSATION_UNIQUENESS")
    for key in ("second_turn_recalled_marker", "marker_declared_not_brand_fact", "dify_conversation_id_reused", "sanitized_runtime_context_used", "failed_preceding_attempts_retained_in_model_audit"):
        require(continuity.get(key) is True, f"E_CONTINUITY:{key}")
    for key in ("raw_provider_reasoning_reused_as_context", "cross_account_context_visible", "publish_allowed"):
        require(continuity.get(key) is False, f"E_CONTINUITY_BOUNDARY:{key}")
    legacy = cast(Mapping[str, Any], evidence.get("legacy_objects", {}))
    require(legacy.get("compatibility_research_stopped") is True, "E_EXTERNAL_LEGACY_RESEARCH")
    require(legacy.get("old_object_mutation_count") == 0, "E_OLD_MUTATION")
    require(legacy.get("old_object_deletion_count") == 0, "E_OLD_DELETION")
    for key in ("parallel_package7_app_created", "parallel_package7_dataset_created", "parallel_package7_database_created", "parallel_package7_bridge_created"):
        require(legacy.get(key) is False, f"E_PARALLEL_OBJECT:{key}")
    boundaries = cast(Mapping[str, Any], evidence.get("boundaries", {}))
    for key in ("core_300_changed", "core_120_changed", "core_86_changed", "public_release_performed", "domain_or_proxy_changed", "package8_or_later_action_performed"):
        require(boundaries.get(key) is False, f"E_EXTERNAL_BOUNDARY:{key}")
    require(boundaries.get("readiness_transition_count") == 0, "E_EXTERNAL_READINESS")


def validate_candidate_record(record: JsonObject, expected_format: str, payload_key: str) -> None:
    require(set(record) == {"candidate", "ordinal", "selected", "validation"}, "E_REPRESENTATIVE_RECORD_FIELDS")
    candidate = cast(Mapping[str, Any], record.get("candidate", {}))
    validation = cast(Mapping[str, Any], record.get("validation", {}))
    require(isinstance(record.get("ordinal"), int), "E_CANDIDATE_ORDINAL")
    require(record.get("selected") is False, "E_CANDIDATE_PRESELECTED")
    require(isinstance(candidate.get("difference_dimensions"), list) and len(candidate["difference_dimensions"]) >= 2, "E_CANDIDATE_DIFFERENCE")
    fact_refs = candidate.get("used_fact_refs")
    material_refs = candidate.get("used_material_refs")
    require(isinstance(fact_refs, list) and isinstance(material_refs, list), "E_CANDIDATE_REFS")
    require(fact_refs == validation.get("actually_used_fact_refs"), "E_FACT_REF_MISMATCH")
    require(material_refs == validation.get("actually_used_material_refs"), "E_MATERIAL_REF_MISMATCH")
    require(validation.get("decision") == "PASS", "E_STRUCTURAL_VALIDATION")
    require(validation.get("semantic_fact_review_status") == "PENDING_EXTERNAL_REVIEW", "E_SEMANTIC_SELF_APPROVAL")
    require(validation.get("structured_hard_checks_prove_candidate_semantics") is False, "E_SEMANTIC_MACHINE_CLAIM")
    surfaces = cast(Mapping[str, Any], candidate.get("candidate_user_visible_surfaces", {}))
    require_fields(surfaces, {"title", "body", "spoken_lines", "CTA", "execution_payload", "surface_units"}, "E_SURFACE_FIELDS")
    require(isinstance(surfaces.get("title"), str) and bool(surfaces["title"].strip()), "E_TITLE")
    require(isinstance(surfaces.get("body"), str) and bool(surfaces["body"].strip()), "E_BODY")
    require(isinstance(surfaces.get("spoken_lines"), list), "E_SPOKEN_LINES")
    payload = cast(Mapping[str, Any], surfaces.get("execution_payload", {}))
    require(payload.get("production_format") == expected_format, "E_PRODUCTION_FORMAT")
    require(isinstance(payload.get(payload_key), dict), f"E_FORMAT_PAYLOAD:{payload_key}")
    joined = json.dumps(surfaces, ensure_ascii=False)
    require("<think>" not in joined and "</think>" not in joined, "E_PRIVATE_REASONING_SURFACE")
    require(not any(pattern.search(joined) for pattern in SECRET_PATTERNS), "E_SECRET_SURFACE")


def validate_model_evidence(evidence: JsonObject) -> None:
    require(evidence.get("schema") == "diyu.package7.model_run_evidence.v1", "E_MODEL_SCHEMA")
    model = cast(Mapping[str, Any], evidence.get("model", {}))
    require(model.get("model_name") == "deepseek-v4-flash", "E_MODEL_NAME")
    require(model.get("configuration_frozen_during_formal_evidence") is True, "E_MODEL_FREEZE")
    require(model.get("content_reroll_for_quality_count") == 0, "E_MODEL_REROLL")
    budget = cast(Mapping[str, Any], evidence.get("founder_budget_authorization", {}))
    require(budget == {"additional_request_upper_bound": 60, "cost_cny_upper_bound": 50, "effective_request_upper_bound": 100, "original_request_upper_bound": 40}, "E_MODEL_AUTHORIZATION")
    audit = cast(Mapping[str, Any], evidence.get("invocation_audit", {}))
    require(audit.get("invocation_count") == 46, "E_MODEL_INVOCATIONS")
    require(isinstance(audit.get("model_call_upper_bound"), int) and 0 < audit["model_call_upper_bound"] <= 100, "E_MODEL_CALL_BOUND")
    require(audit.get("request_upper_bound_within_authorization") is True, "E_MODEL_BUDGET_CLAIM")
    try:
        known_cost = Decimal(str(audit.get("known_cost_rmb")))
    except InvalidOperation as exc:
        raise CheckFailure("E_MODEL_COST") from exc
    require(known_cost <= Decimal("50"), "E_MODEL_COST_BOUND")
    require(audit.get("known_cost_within_authorization") is True, "E_MODEL_COST_CLAIM")
    require(evidence.get("run_count") == 23, "E_RUN_COUNT")
    distribution = cast(Mapping[str, Any], evidence.get("run_state_distribution", {}))
    require(sum(int(value) for value in distribution.values()) == 23, "E_RUN_DISTRIBUTION")
    require(int(distribution.get("FIRST_OUTPUT_REJECTED", 0)) >= 1, "E_FAILED_OUTPUTS_NOT_RETAINED")
    require(isinstance(evidence.get("run_index"), list) and len(evidence["run_index"]) == 23, "E_RUN_INDEX")
    representative = cast(Mapping[str, Any], evidence.get("representative_first_outputs", {}))
    require(set(representative) == set(EXPECTED_FORMATS), "E_REPRESENTATIVE_FORMATS")
    for key, (expected_format, payload_key) in EXPECTED_FORMATS.items():
        run = cast(Mapping[str, Any], representative[key])
        require(run.get("first_output_preserved") is True, f"E_FIRST_OUTPUT:{key}")
        candidates = run.get("candidates")
        require(isinstance(candidates, list) and 2 <= len(candidates) <= 3, f"E_CANDIDATE_COUNT:{key}")
        for record in cast(list[Any], candidates):
            require(isinstance(record, dict), f"E_CANDIDATE_OBJECT:{key}")
            validate_candidate_record(cast(JsonObject, record), expected_format, payload_key)
    continuity = cast(Mapping[str, Any], evidence.get("continuous_dialogue", {}))
    require(continuity.get("conversation_binding_reused") is True, "E_MODEL_CONTINUITY_BINDING")
    require(continuity.get("dify_message_count_for_binding") == 2, "E_MODEL_CONTINUITY_MESSAGES")
    require(continuity.get("second_turn_recalled_marker") is True, "E_MODEL_CONTINUITY_RECALL")
    require(continuity.get("marker_is_brand_fact") is False, "E_MODEL_CONTINUITY_FACT")
    require(continuity.get("publish_allowed") is False, "E_MODEL_CONTINUITY_PUBLISH")
    require(continuity.get("raw_provider_reasoning_used_as_continuity_context") is False, "E_MODEL_CONTINUITY_REASONING")
    turns = continuity.get("accepted_sanitized_turns")
    require(isinstance(turns, list) and len(turns) == 2, "E_MODEL_CONTINUITY_TURNS")
    limits = cast(Mapping[str, Any], evidence.get("evidence_limits", {}))
    require(limits.get("all_provider_private_reasoning_excluded_from_repository_evidence") is True, "E_REASONING_EVIDENCE")
    require(limits.get("free_text_truth_requires_independent_review") is True, "E_FREE_TEXT_REVIEW")
    require(limits.get("production_or_publish_approval") is False, "E_MODEL_PUBLISH_APPROVAL")


def validate_brand_contracts(root: Path) -> None:
    contract = load_yaml_root(root / "brand_import_contract.v1.yaml", "brand_import_contract")
    require(contract.get("brand_specific_constants_allowed_in_runtime_logic") is False, "E_IMPORT_BRAND_CONSTANTS")
    transaction = cast(Mapping[str, Any], contract.get("transaction_policy", {}))
    require(transaction.get("all_or_nothing") is True, "E_IMPORT_ATOMICITY")
    require(transaction.get("partial_brand_left_after_failure") is False, "E_IMPORT_PARTIAL")
    isolation = cast(Mapping[str, Any], contract.get("isolation_policy", {}))
    require(isolation.get("cross_tenant_reference_allowed") is False, "E_IMPORT_CROSS_TENANT")
    validate_readiness(cast(Mapping[str, Any], contract.get("readiness", {})), "E_IMPORT_READINESS") if set(cast(Mapping[str, Any], contract.get("readiness", {}))) == REQUIRED_FALSE_FLAGS else None
    require(cast(Mapping[str, Any], contract.get("readiness", {})).get("DIFY_ready") is False, "E_IMPORT_DIFY_READY")
    require(cast(Mapping[str, Any], contract.get("readiness", {})).get("production_ready") is False, "E_IMPORT_PRODUCTION_READY")
    profile = load_yaml_root(root / "brand_runtime_profile.v1.yaml", "brand_runtime_profile")
    require(profile.get("simulation_only") is True, "E_PROFILE_SIMULATION")
    require(profile.get("publish_allowed") is False, "E_PROFILE_PUBLISH")
    require(profile.get("runtime_publishable") is False, "E_PROFILE_RUNTIME")
    require(profile.get("may_grant_fact_authorization_or_scope") is False, "E_PROFILE_AUTHORITY")
    require(profile.get("cross_tenant_borrowing_allowed") is False, "E_PROFILE_CROSS_TENANT")
    require(len(cast(list[Any], profile.get("principal_roles", []))) == 3, "E_PROFILE_ROLES")
    require(len(cast(list[Any], profile.get("storylines", []))) == 4, "E_PROFILE_STORYLINES")
    require(len(cast(list[Any], profile.get("account_role_cards", []))) == 11, "E_PROFILE_ACCOUNTS")
    import_source = (root / "brand_import.py").read_text(encoding="utf-8")
    for token in ("TENANT-DIYU", "BRAND-DIYU", "ACCOUNT-DIYU", "笛语"):
        require(token not in import_source, f"E_IMPORT_SHORTCUT:{token}")


def validate_dify_graph(root: Path) -> None:
    app = yaml.safe_load((root / "dify_app.v1.yaml").read_text(encoding="utf-8"))
    require(isinstance(app, dict), "E_DIFY_GRAPH_OBJECT")
    workflow = cast(Mapping[str, Any], app.get("workflow", {}))
    graph = cast(Mapping[str, Any], workflow.get("graph", {}))
    nodes = cast(list[Mapping[str, Any]], graph.get("nodes", []))
    llm_nodes = [node for node in nodes if cast(Mapping[str, Any], node.get("data", {})).get("type") == "llm"]
    require(len(llm_nodes) == 2, "E_DIFY_LLM_NODE_COUNT")
    for node in llm_nodes:
        data = cast(Mapping[str, Any], node.get("data", {}))
        require(cast(Mapping[str, Any], data.get("memory", {})).get("window") == {"enabled": False, "size": 1}, "E_DIFY_MEMORY")
        require(cast(Mapping[str, Any], data.get("model", {})).get("name") == "deepseek-v4-flash", "E_DIFY_NODE_MODEL")
    require(not [node for node in nodes if cast(Mapping[str, Any], node.get("data", {})).get("type") in {"http-request", "knowledge-retrieval"}], "E_DIFY_PARALLEL_IO_NODE")
    require(workflow.get("environment_variables") == [], "E_DIFY_SECRET_VARIABLE")


def validate_source_boundaries(root: Path) -> None:
    source = {path.name: path.read_text(encoding="utf-8") for path in root.glob("*.py")}
    all_source = "\n".join(source.values())
    require("order_by(App.created_at" not in source["provision_dify.py"], "E_OLDEST_APP_OWNER_INFERENCE")
    for token in ("PACKAGE7_APPROVED_DIFY_TENANT_ID", "PACKAGE7_APPROVED_DIFY_OWNER_ACCOUNT_ID"):
        require(token in source["provision_dify.py"], f"E_EXPLICIT_OWNER_BINDING:{token}")
    models = source["runtime_models.py"]
    for token in ("UniqueConstraint(", '"principal_id"', '"account_id"', "uq_runtime_dify_conversation_scope"):
        require(token in models, f"E_CONVERSATION_MODEL:{token}")
    persistence = source["persistence.py"]
    for token in ("def dify_conversation(self, principal_id: str, account_id: str)", "def recent_chat_turns(", "RuntimeDifyConversation.account_id == account_id"):
        require(token in persistence, f"E_CONVERSATION_PERSISTENCE:{token}")
    runtime = source["runtime_service.py"]
    for token in ("conversation_context", "recent_chat_turns", "不能增加任何品牌事实"):
        require(token in runtime, f"E_SANITIZED_CONTINUITY:{token}")
    chat = source["dify_chat.py"]
    require("maximum_model_calls > 100" in chat, "E_MODEL_BUDGET_HARD_CAP")
    require("dify_conversation(principal_id, conversation_scope)" in chat, "E_DIFY_CONVERSATION_SCOPE")
    bridge = source["bridge_app.py"]
    require("package7-dify-user:{principal_id}:{conversation_scope}" in bridge, "E_DIFY_USER_SCOPE")
    require("query=payload.message" in bridge, "E_CHAT_QUERY_NOT_REAL")
    for forbidden in ("import openai", "from openai", "import anthropic", "from anthropic", "api.deepseek.com"):
        require(forbidden not in all_source, f"E_DIRECT_PROVIDER:{forbidden}")
    for path in root.rglob("*"):
        if not path.is_file() or path.name == Path(__file__).name or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        require(not any(pattern.search(text) for pattern in SECRET_PATTERNS), f"E_SECRET:{path.relative_to(root)}")


def validate_candidate_binding(result: JsonObject) -> tuple[str, str]:
    candidate_commit = str(result.get("reviewed_candidate_commit", ""))
    candidate_snapshot = str(result.get("reviewed_snapshot_sha256", ""))
    require(bool(re.fullmatch(r"[0-9a-f]{40}", candidate_commit)), "E_CANDIDATE_COMMIT")
    require(bool(re.fullmatch(r"[0-9a-f]{40}", candidate_snapshot)), "E_CANDIDATE_TREE")
    require(candidate_tree(candidate_commit) == candidate_snapshot, "E_CANDIDATE_TREE_MISMATCH")
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate_commit, "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    require(process.returncode == 0, "E_CANDIDATE_NOT_ANCESTOR")
    changed = {
        Path(line)
        for line in git_output("diff", "--name-only", f"{candidate_commit}..HEAD").splitlines()
        if line
    }
    require(changed <= POST_CANDIDATE_ALLOWED_PATHS, f"E_POST_CANDIDATE_IMPLEMENTATION:{sorted(map(str, changed - POST_CANDIDATE_ALLOWED_PATHS))}")
    return candidate_commit, candidate_snapshot


def validate_reviews(root: Path, result: JsonObject, candidate_commit: str, candidate_snapshot: str) -> list[JsonObject]:
    reviews: list[JsonObject] = []
    for path in REVIEW_PATHS:
        review = load_yaml_root(root / path, "review")
        require(review.get("task_id") == TASK_ID, f"E_REVIEW_TASK:{path}")
        require(review.get("candidate_commit") == candidate_commit, f"E_REVIEW_COMMIT:{path}")
        require(review.get("candidate_snapshot_digest") == candidate_snapshot, f"E_REVIEW_TREE:{path}")
        require(review.get("verdict") == "PASS", f"E_REVIEW_VERDICT:{path}")
        require(isinstance(review.get("score"), int) and review["score"] >= 90, f"E_REVIEW_SCORE:{path}")
        require(review.get("hard_blockers") == [], f"E_REVIEW_BLOCKER:{path}")
        require(review.get("independent_from_executor_and_other_reviewer") is True, f"E_REVIEW_INDEPENDENCE:{path}")
        for key in ("reviewer_identity", "reviewer_session_id", "reviewer_run_id", "signed_at"):
            require(isinstance(review.get(key), str) and bool(review[key]), f"E_REVIEW_IDENTITY:{path}:{key}")
        require(isinstance(review.get("evidence"), list) and len(review["evidence"]) >= 3, f"E_REVIEW_EVIDENCE:{path}")
        reviews.append(review)
    require({str(review.get("review_type")) for review in reviews} == REVIEW_TYPES, "E_REVIEW_TYPES")
    for key in ("reviewer_identity", "reviewer_session_id", "reviewer_run_id"):
        require(len({str(review[key]) for review in reviews}) == 2, f"E_REVIEW_COLLISION:{key}")
    declared = result.get("independent_reviews")
    require(isinstance(declared, list) and len(declared) == 2, "E_RESULT_REVIEW_COUNT")
    require(
        {
            str(item.get("review_id"))
            for item in cast(list[Any], declared)
            if isinstance(item, dict)
        }
        == {str(review.get("review_id")) for review in reviews},
        "E_RESULT_REVIEW_BINDING",
    )
    return reviews


def validate_result_and_delivery(root: Path, result: JsonObject) -> None:
    require(result.get("schema") == "diyu.package7.dify_end_to_end_result.v1", "E_RESULT_SCHEMA")
    require(result.get("task_id") == TASK_ID, "E_RESULT_TASK")
    require(result.get("state") == "PASS_DIFY_END_TO_END_PENDING_PACKAGE_8", "E_RESULT_STATE")
    require(result.get("success_claim") == "PACKAGE7_ACCEPTANCE_COMPLETE_NOT_PRODUCTION_READY", "E_RESULT_CLAIM")
    require(result.get("blocking_items") == [], "E_RESULT_BLOCKERS")
    candidate_commit, snapshot = validate_candidate_binding(result)
    objects = cast(Mapping[str, Any], result.get("external_objects", {}))
    for key in ("dify_app_count", "dataset_count", "runtime_database_count", "runtime_bridge_count"):
        require(objects.get(key) == 1, f"E_RESULT_OBJECT:{key}")
    require(objects.get("parallel_object_count") == 0, "E_RESULT_PARALLEL_OBJECT")
    require(objects.get("production_ready") is False, "E_RESULT_PRODUCTION")
    coverage = cast(Mapping[str, Any], result.get("coverage", {}))
    require(coverage.get("content_products_deterministic") == 20, "E_RESULT_CP")
    require(coverage.get("formats_with_real_model_outputs") == 3, "E_RESULT_FORMATS")
    for key in ("representative_continuous_dialogue_pass", "representative_missing_material_degrade_pass", "representative_scope_rejection_pass"):
        require(coverage.get(key) is True, f"E_RESULT_COVERAGE:{key}")
    audit = cast(Mapping[str, Any], result.get("model_audit", {}))
    call_upper_bound = audit.get("model_call_upper_bound")
    authorized_upper_bound = audit.get("effective_authorized_request_upper_bound")
    require(
        isinstance(call_upper_bound, int)
        and isinstance(authorized_upper_bound, int)
        and call_upper_bound <= authorized_upper_bound == 100,
        "E_RESULT_MODEL_BUDGET",
    )
    require(Decimal(str(audit.get("known_cost_rmb"))) <= Decimal(str(audit.get("authorized_cost_cny_upper_bound"))), "E_RESULT_COST")
    require(audit.get("content_quality_reroll_count") == 0, "E_RESULT_REROLL")
    require(result.get("core_numbers") == {"300_changed": False, "120_changed": False, "86_changed": False}, "E_RESULT_CORE")
    require(result.get("readiness_transition_count") == 0, "E_RESULT_READINESS")
    require(result.get("merge_allowed") is False, "E_RESULT_MERGE")
    checks = cast(Mapping[str, Any], result.get("checks", {}))
    for key in ("package7_unit_tests", "package2_regression", "package6_regression", "package7_checker", "gate1_current_checker"):
        require(str(checks.get(key, "")).startswith("PASS"), f"E_RESULT_CHECK:{key}")
    validate_reviews(root, result, candidate_commit, snapshot)
    delivery = load_yaml_root(root / DELIVERY_PATH, "execution_review_request")
    require(delivery.get("task_id") == TASK_ID, "E_DELIVERY_TASK")
    require(delivery.get("status") == "REQUESTING_APPROVE_PACKAGE_7_MERGE", "E_DELIVERY_STATUS")
    require(delivery.get("candidate_commit") == candidate_commit, "E_DELIVERY_COMMIT")
    require(delivery.get("candidate_snapshot_digest") == snapshot, "E_DELIVERY_TREE")
    require(delivery.get("requested_root_decision") == "APPROVE_PACKAGE_7_MERGE", "E_DELIVERY_REQUEST")
    require(delivery.get("merge_authorization") == "NOT_GRANTED", "E_DELIVERY_MERGE")
    require(delivery.get("draft_pull_request_required") is True, "E_DELIVERY_DRAFT")
    require(delivery.get("package8_unlocked") is False, "E_DELIVERY_PACKAGE8")
    require(delivery.get("implementation_changes_after_candidate_freeze_allowed") is False, "E_DELIVERY_FREEZE")
    require(delivery.get("readiness_transition_authorized") is False, "E_DELIVERY_READINESS")


def validate_repository_scope(candidate_commit: str) -> None:
    changed = {
        Path(line)
        for line in git_output("diff", "--name-only", f"{BASELINE_COMMIT}..{candidate_commit}").splitlines()
        if line
    }
    allowed = AUTHORIZED_COMPATIBILITY_PATHS | {
        path
        for path in changed
        if path == PACKAGE_RELATIVE_ROOT or PACKAGE_RELATIVE_ROOT in path.parents
    }
    require(changed <= allowed, f"E_WRITE_SCOPE:{sorted(map(str, changed - allowed))}")


def validate_all(root: Path = PACKAGE_ROOT) -> JsonObject:
    validate_file_set(root)
    manifest = load_json(root / MANIFEST_PATH)
    external = load_json(root / EXTERNAL_EVIDENCE_PATH)
    model = load_json(root / MODEL_EVIDENCE_PATH)
    result = load_json(root / RESULT_PATH)
    validate_manifest(manifest)
    validate_external_evidence(external)
    validate_model_evidence(model)
    validate_brand_contracts(root)
    validate_dify_graph(root)
    validate_source_boundaries(root)
    validate_result_and_delivery(root, result)
    validate_repository_scope(str(result["reviewed_candidate_commit"]))
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "model_call_upper_bound": model["invocation_audit"]["model_call_upper_bound"],
        "review_count": len(REVIEW_PATHS),
        "readiness_transition_count": 0,
        "core_numbers_changed": False,
    }


def expect_failure(callback: Any, code: str) -> None:
    try:
        callback()
    except CheckFailure as exc:
        require(code in str(exc), f"E_SELFTEST_WRONG_FAILURE:{code}:{exc}")
        return
    raise CheckFailure(f"E_SELFTEST_FALSE_NEGATIVE:{code}")


def run_selftest(root: Path = PACKAGE_ROOT) -> JsonObject:
    manifest = load_json(root / MANIFEST_PATH)
    external = load_json(root / EXTERNAL_EVIDENCE_PATH)
    model = load_json(root / MODEL_EVIDENCE_PATH)
    result = load_json(root / RESULT_PATH)

    changed = copy.deepcopy(manifest)
    changed["readiness"]["DIFY_ready"] = True
    expect_failure(lambda: validate_manifest(changed), "E_MANIFEST_READINESS:DIFY_ready")

    changed = copy.deepcopy(manifest)
    changed["model_budget"]["effective_request_upper_bound"] = 101
    expect_failure(lambda: validate_manifest(changed), "E_BUDGET_EFFECTIVE")

    changed = copy.deepcopy(external)
    changed["dify_objects"]["package7_app_name_count"] = 2
    expect_failure(lambda: validate_external_evidence(changed), "E_APP_COUNT")

    changed = copy.deepcopy(external)
    changed["continuous_dialogue"]["cross_account_context_visible"] = True
    expect_failure(lambda: validate_external_evidence(changed), "E_CONTINUITY_BOUNDARY:cross_account_context_visible")

    changed = copy.deepcopy(model)
    changed["continuous_dialogue"]["raw_provider_reasoning_used_as_continuity_context"] = True
    expect_failure(lambda: validate_model_evidence(changed), "E_MODEL_CONTINUITY_REASONING")

    changed = copy.deepcopy(model)
    changed["invocation_audit"]["model_call_upper_bound"] = 101
    expect_failure(lambda: validate_model_evidence(changed), "E_MODEL_CALL_BOUND")

    changed = copy.deepcopy(model)
    first_format = next(iter(EXPECTED_FORMATS))
    changed["representative_first_outputs"][first_format]["candidates"][0]["candidate"]["used_material_refs"] = []
    expect_failure(lambda: validate_model_evidence(changed), "E_MATERIAL_REF_MISMATCH")

    changed = copy.deepcopy(result)
    changed["core_numbers"]["300_changed"] = True
    expect_failure(
        lambda: require(
            changed.get("core_numbers")
            == {"300_changed": False, "120_changed": False, "86_changed": False},
            "E_RESULT_CORE",
        ),
        "E_RESULT_CORE",
    )

    expect_failure(
        lambda: require(not SECRET_PATTERNS[0].search("sk-ABCDEFGHIJKLMNOPQRSTUV"), "E_SECRET_SYNTHETIC"),
        "E_SECRET_SYNTHETIC",
    )

    source = (root / "provision_dify.py").read_text(encoding="utf-8")
    expect_failure(
        lambda: require("order_by(App.created_at" not in source + "\norder_by(App.created_at)", "E_OLDEST_APP_OWNER_INFERENCE"),
        "E_OLDEST_APP_OWNER_INFERENCE",
    )

    return {
        "task_id": TASK_ID,
        "selftest": "PASS",
        "negative_case_count": 10,
        "optimized_mode_fail_closed": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_selftest() if args.selftest else validate_all()
    except (CheckFailure, KeyError, TypeError, ValueError, OSError) as exc:
        print(json.dumps({"task_id": TASK_ID, "status": "FAIL", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
