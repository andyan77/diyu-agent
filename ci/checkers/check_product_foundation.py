#!/usr/bin/env python3
"""Fail-closed checker for the Diyu public product foundation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml


if not __debug__:
    print("check_product_foundation refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "DIYU_ENGINEERING_ENTRY_AND_PUBLIC_FOUNDATION_FREEZE_001"
FOUNDATION_ROOT = Path("11_product_foundation/public_foundation_001")
CONTRACT_PATH = FOUNDATION_ROOT / "contract/public_foundation_contract.v1.yaml"
IDENTITY_PATH = FOUNDATION_ROOT / "identity/simulation_tenant.v1.yaml"
TOPIC_PATH = FOUNDATION_ROOT / "taxonomy/topic_product_mapping.v1.yaml"
CASES_PATH = FOUNDATION_ROOT / "fixtures/contract_cases.v1.jsonl"
RESULT_PATH = FOUNDATION_ROOT / "result/public_foundation_result.v1.yaml"
ARCH_REVIEW_PATH = FOUNDATION_ROOT / "review/architecture_consumability_review.v1.yaml"
TRUST_REVIEW_PATH = FOUNDATION_ROOT / "review/trust_fact_safety_review.v1.yaml"
COORDINATOR_PATH = FOUNDATION_ROOT / "review/coordinator_decision.v1.yaml"
STATUS_PATH = Path("project-infra/current_product_status.v1.yaml")
MANIFEST_PATH = Path("project-infra/product_workspace_manifest.v1.yaml")
CHECKER_PATH = Path("ci/checkers/check_product_foundation.py")
WORKFLOW_PATH = Path(".github/workflows/ci.yml")

BASE_FOUNDATION_FILES = frozenset(
    {
        CONTRACT_PATH.relative_to(FOUNDATION_ROOT),
        IDENTITY_PATH.relative_to(FOUNDATION_ROOT),
        TOPIC_PATH.relative_to(FOUNDATION_ROOT),
        CASES_PATH.relative_to(FOUNDATION_ROOT),
        RESULT_PATH.relative_to(FOUNDATION_ROOT),
    }
)
REVIEW_FILES = frozenset(
    {
        ARCH_REVIEW_PATH.relative_to(FOUNDATION_ROOT),
        TRUST_REVIEW_PATH.relative_to(FOUNDATION_ROOT),
        COORDINATOR_PATH.relative_to(FOUNDATION_ROOT),
    }
)
SNAPSHOT_PATHS = (
    Path("AGENTS.md"),
    Path("README.md"),
    CONTRACT_PATH,
    IDENTITY_PATH,
    TOPIC_PATH,
    CASES_PATH,
    STATUS_PATH,
    MANIFEST_PATH,
    CHECKER_PATH,
    WORKFLOW_PATH,
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
        "generator_qualified",
        "retrieval_ready",
        "runtime_ready",
        "release_ready",
        "production_ready",
    }
)
EXPECTED_TOPIC_NAMES = {
    "TOPIC-01": "真实工作与人物",
    "TOPIC-02": "手艺、工艺与专业知识",
    "TOPIC-03": "用户问题与理性选择",
    "TOPIC-04": "产品研发与验证",
    "TOPIC-05": "穿搭与衣橱关系",
    "TOPIC-06": "商品质感与视觉审美",
    "TOPIC-07": "门店运营与空间经营",
    "TOPIC-08": "城市门店与本地生活",
}
EXPECTED_ACCOUNT_NAMES = {
    "ACCOUNT-DIYU-HQ-OFFICIAL": "笛语童装",
    "ACCOUNT-DIYU-FOUNDER": "林知远｜笛语",
    "ACCOUNT-DIYU-PRODUCT-LEAD": "许闻川的产品记录",
    "ACCOUNT-DIYU-RETAIL-DISPLAY": "周静宜｜门店与陈列",
    "ACCOUNT-DIYU-CONTENT-LEAD": "唐予安｜内容现场",
    "ACCOUNT-DIYU-HZ-BINJIANG": "笛语杭州滨江店",
    "ACCOUNT-DIYU-JS-OFFICIAL": "笛语江苏",
    "ACCOUNT-DIYU-JS-PRINCIPAL": "顾知夏｜江苏笛语",
    "ACCOUNT-DIYU-JS-STYLING-SERVICE": "许知宁｜搭配与门店服务",
    "ACCOUNT-DIYU-SZ-PARK": "笛语苏州园区店",
    "ACCOUNT-DIYU-WX-BINHU": "笛语无锡滨湖店",
}
EXPECTED_EXPRESSION_ASSETS = {
    "ACTIVE_COMPONENTS": (
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/component/"
        "active_gate1_components.v0.1.jsonl",
        "83dd1a8d35149785ac8bb172700b79d6221e5a7331b210018699fabaa49bc8ae",
        68,
    ),
    "ACTIVE_CONTROL_RULES": (
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/component/"
        "active_control_rules.v0.1.jsonl",
        "5d0ded265a6be6d0f39d35d2f739239225211081db6d6c4e4df0c8dcc2f09386",
        8,
    ),
    "ACTIVE_EDGES": (
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/component/"
        "active_gate1_edges.v0.1.jsonl",
        "de366eb50afe8a5a9362d3faa2a6a845af9c334683bdb9a8489cbfad2b2566f0",
        85,
    ),
    "ACTIVE_AB_STRUCTURAL_PATHS": (
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/ab/"
        "active_ab_structural_paths.v0.1.jsonl",
        "4756971ef58ed472d0447f61f00bac7b7ef594117c43ecfb9fe3d7106c9631f3",
        20,
    ),
    "GENERATOR_CONTRACT": (
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/generator/"
        "gate1_generator_contract.v0.1.yaml",
        "67be34b2db8be54e5a81ef46c71367d196c12e29886dbcae62daf55a8d7518fa",
        None,
    ),
    "GENERATOR_REGISTRY": (
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/generator/"
        "active_gate1_generator_registry.v0.1.yaml",
        "46b83a926efaceb43010278bc33156a587dc7d38361dd8a149a5e1b96ecbff7a",
        None,
    ),
    "P2_FINAL_RESULT": (
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p2_component_supply_and_generator_core_repair_001/result/"
        "p2_final_result.v0.1.yaml",
        "076bd9eb6c8ab67c0023bb454f6a82f16acecb284e896dc9029ef97582db5c3b",
        None,
    ),
    "P3_OPEN_PROBE_RESULT": (
        "controlled_content_generator_v2_001/gate1_v1_1_001/"
        "p3_open_probe40_001/result/p3_open_probe40_result.v0.2.yaml",
        "c06955256ef9190f5b89221c69417353791fbc7a4b0eb4f8dab0be2826b6fcb0",
        None,
    ),
}
PROHIBITED_USER_PATTERN = re.compile(
    r"(?:\bCP\d{2}\b|\b(?:BNO|BRV|VGA|BCL|FC)-\d{2}\b|\bE_[A-Z0-9_]+\b)"
)


class CheckFailure(RuntimeError):
    """A stable fail-closed validation error."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CheckFailure(code)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_yaml(root: Path, relative_path: Path, top_key: str) -> dict[str, Any]:
    path = root / relative_path
    require(path.is_file(), f"E_MISSING_FILE:{relative_path}")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"E_YAML_ROOT:{relative_path}")
    require(set(value) == {top_key}, f"E_YAML_TOP_KEY:{relative_path}")
    payload = value[top_key]
    require(isinstance(payload, dict), f"E_YAML_PAYLOAD:{relative_path}")
    return payload


def load_jsonl(root: Path, relative_path: Path) -> list[dict[str, Any]]:
    path = root / relative_path
    require(path.is_file(), f"E_MISSING_FILE:{relative_path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        require(bool(line.strip()), f"E_JSONL_BLANK:{relative_path}:{line_number}")
        value = json.loads(line)
        require(
            isinstance(value, dict), f"E_JSONL_OBJECT:{relative_path}:{line_number}"
        )
        records.append(value)
    return records


def count_jsonl(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def snapshot_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for relative_path in SNAPSHOT_PATHS:
        path = root / relative_path
        require(path.is_file(), f"E_SNAPSHOT_MISSING:{relative_path}")
        digest.update(relative_path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_all_false(mapping: Any, code: str) -> None:
    require(isinstance(mapping, dict), f"{code}:NOT_OBJECT")
    require(READINESS_KEYS.issubset(mapping), f"{code}:MISSING_KEYS")
    for key in READINESS_KEYS:
        require(mapping[key] is False, f"{code}:{key}")


def validate_foundation_files(root: Path, review_state: str) -> None:
    actual = {
        path.relative_to(root / FOUNDATION_ROOT)
        for path in (root / FOUNDATION_ROOT).rglob("*")
        if path.is_file()
    }
    expected = set(BASE_FOUNDATION_FILES)
    if review_state == "PASS_TO_MERGE":
        expected.update(REVIEW_FILES)
    require(
        actual == expected,
        f"E_FOUNDATION_FILE_SET:{sorted(map(str, actual ^ expected))}",
    )


def validate_expression_baseline(root: Path, contract: dict[str, Any]) -> None:
    baseline = contract.get("expression_v1_baseline")
    require(isinstance(baseline, dict), "E_EXPRESSION_BASELINE")
    require(
        baseline.get("consumption_mode") == "REFERENCE_ONLY",
        "E_EXPRESSION_REFERENCE_MODE",
    )
    require(
        baseline.get("assets_may_not_be_copied_to_brand_facts") is True,
        "E_COMPONENT_COPY_BOUNDARY",
    )
    assets = baseline.get("assets")
    require(isinstance(assets, list), "E_EXPRESSION_ASSETS")
    by_id = {
        asset.get("asset_id"): asset for asset in assets if isinstance(asset, dict)
    }
    require(set(by_id) == set(EXPECTED_EXPRESSION_ASSETS), "E_EXPRESSION_ASSET_IDS")
    for asset_id, (
        relative_path,
        expected_hash,
        expected_count,
    ) in EXPECTED_EXPRESSION_ASSETS.items():
        record = by_id[asset_id]
        require(record.get("path") == relative_path, f"E_ASSET_PATH:{asset_id}")
        require(
            record.get("sha256") == expected_hash, f"E_ASSET_DECLARED_DIGEST:{asset_id}"
        )
        path = root / relative_path
        require(path.is_file(), f"E_ASSET_MISSING:{asset_id}")
        require(sha256_file(path) == expected_hash, f"E_ASSET_LIVE_DIGEST:{asset_id}")
        if expected_count is not None:
            require(
                record.get("count") == expected_count,
                f"E_ASSET_DECLARED_COUNT:{asset_id}",
            )
            require(
                count_jsonl(path) == expected_count, f"E_ASSET_LIVE_COUNT:{asset_id}"
            )
    status = baseline.get("status")
    require(
        status
        == {
            "generator_qualified": False,
            "runtime_ready": False,
            "production_ready": False,
        },
        "E_EXPRESSION_STATUS",
    )


def validate_core_numbers(root: Path, contract: dict[str, Any]) -> None:
    guard = contract.get("core_number_guard")
    require(isinstance(guard, dict), "E_CORE_NUMBER_GUARD")
    target = guard.get("target_case_baseline")
    require(isinstance(target, dict), "E_TARGET_300")
    require(target.get("count") == 300, "E_TARGET_300_COUNT")
    require(target.get("frozen") is False, "E_TARGET_300_FALSE_FREEZE")
    require(target.get("changed_or_harmed") is False, "E_TARGET_300_HARM")
    require(target.get("second_inventory_created") is False, "E_SECOND_300_INVENTORY")
    expected = {
        "frozen_reference_inventory": (
            120,
            "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91",
        ),
        "historical_component_inventory": (
            86,
            "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601",
        ),
    }
    for key, (count, expected_hash) in expected.items():
        record = guard.get(key)
        require(isinstance(record, dict), f"E_CORE_RECORD:{key}")
        require(record.get("count") == count, f"E_CORE_COUNT:{key}")
        require(record.get("sha256") == expected_hash, f"E_CORE_DIGEST_DECLARED:{key}")
        require(record.get("changed_or_harmed") is False, f"E_CORE_HARM:{key}")
        path = root / str(record.get("path"))
        require(path.is_file(), f"E_CORE_PATH:{key}")
        require(count_jsonl(path) == count, f"E_CORE_LIVE_COUNT:{key}")
        require(sha256_file(path) == expected_hash, f"E_CORE_LIVE_DIGEST:{key}")
    failure = guard.get("failed_quality_candidate")
    require(isinstance(failure, dict), "E_PR15_RECORD")
    require(failure.get("pull_request") == 15, "E_PR15_NUMBER")
    require(
        failure.get("head_commit") == "b4c40beb509d81db30b497abf38af1da6dc797da",
        "E_PR15_HEAD",
    )
    require(
        failure.get("classification")
        == "OPEN_DRAFT_FAILURE_EVIDENCE_NOT_APPROVED_BASELINE",
        "E_PR15_CLASSIFICATION",
    )


def validate_contract_data(root: Path, contract: dict[str, Any]) -> None:
    require(contract.get("schema_version") == "v1.0", "E_CONTRACT_VERSION")
    require(contract.get("task_id") == TASK_ID, "E_CONTRACT_TASK")
    boundary = contract.get("implementation_boundary")
    require(isinstance(boundary, dict), "E_IMPLEMENTATION_BOUNDARY")
    require(boundary.get("contract_only") is True, "E_NOT_CONTRACT_ONLY")
    for key, value in boundary.items():
        if key != "contract_only":
            require(value is False, f"E_PREMATURE_IMPLEMENTATION:{key}")

    trusted = contract.get("trusted_scope_contract")
    require(isinstance(trusted, dict), "E_TRUSTED_SCOPE")
    require(trusted.get("authority") == "SERVER_CONFIRMED_SCOPE", "E_SCOPE_AUTHORITY")
    require(
        trusted.get("user_input_may_override_server_scope") is False,
        "E_SCOPE_OVERRIDE_POLICY",
    )
    require(
        trusted.get("Dify_user_id_is_trusted_login_identity") is False,
        "E_DIFY_IDENTITY_POLICY",
    )
    require(trusted.get("cross_tenant_access") == "FORBIDDEN", "E_CROSS_TENANT_POLICY")
    real_policy = trusted.get("real_identity_policy")
    require(isinstance(real_policy, dict), "E_REAL_IDENTITY_POLICY")
    require(
        real_policy.get("one_login_principal_per_real_person") is True,
        "E_REAL_PRINCIPAL_POLICY",
    )
    require(
        real_policy.get("shared_credentials_allowed") is False,
        "E_SHARED_CREDENTIAL_POLICY",
    )
    require(
        real_policy.get("content_account_is_login_identity") is False,
        "E_ACCOUNT_IDENTITY_COLLAPSE",
    )

    intent_contract = contract.get("intent_and_requirement_contract")
    require(isinstance(intent_contract, dict), "E_INTENT_CONTRACT")
    intents = intent_contract.get("intents")
    require(isinstance(intents, list), "E_INTENTS")
    by_intent = {
        item.get("intent_id"): item for item in intents if isinstance(item, dict)
    }
    require(
        set(by_intent)
        == {
            "NORMAL_CHAT",
            "FIND_INSPIRATION",
            "NEED_MORE_INFORMATION",
            "AWAITING_CONFIRMATION",
            "START_CREATION",
            "REVISE_OUTPUT",
        },
        "E_INTENT_SET",
    )
    normal = by_intent["NORMAL_CHAT"]
    require(normal.get("creates_composition_plan") is False, "E_CHAT_PLAN")
    require(normal.get("writes_brand_fact") is False, "E_CHAT_FACT_WRITE")
    start = by_intent["START_CREATION"]
    require(
        start.get("required_requirement_status") == "CONFIRMED", "E_START_CONFIRMATION"
    )
    revise = by_intent["REVISE_OUTPUT"]
    require(
        revise.get("creates_competing_composition_plan") is False,
        "E_REVISE_PARALLEL_PLAN",
    )
    requirement = intent_contract.get("requirement_version")
    require(isinstance(requirement, dict), "E_REQUIREMENT_VERSION")
    require(
        requirement.get("prepare_requires_status") == "CONFIRMED", "E_PREPARE_STATUS"
    )
    require(
        requirement.get("unconfirmed_requirement_may_enter_prepare") is False,
        "E_UNCONFIRMED_PREPARE",
    )

    fact_contract = contract.get("brand_fact_contract")
    require(isinstance(fact_contract, dict), "E_FACT_CONTRACT")
    channels = fact_contract.get("channels")
    require(isinstance(channels, list), "E_FACT_CHANNELS")
    by_channel = {
        item.get("channel_id"): item for item in channels if isinstance(item, dict)
    }
    require(
        set(by_channel) == {"SCOPED_NARRATIVE_RETRIEVAL", "VERIFIED_PRECISE_FACT"},
        "E_FACT_CHANNEL_SET",
    )
    narrative = by_channel["SCOPED_NARRATIVE_RETRIEVAL"]
    require(narrative.get("may_grant_authorization") is False, "E_RETRIEVAL_AUTHORITY")
    require(
        narrative.get("may_override_precise_fact") is False,
        "E_RETRIEVAL_PRECISE_OVERRIDE",
    )
    require(
        narrative.get("may_override_revocation") is False,
        "E_RETRIEVAL_REVOCATION_OVERRIDE",
    )
    precise = by_channel["VERIFIED_PRECISE_FACT"]
    require(
        precise.get("precedence_over_narrative_retrieval") is True,
        "E_PRECISE_PRECEDENCE",
    )
    require(
        fact_contract.get("expression_asset_may_be_fact_or_authorization") is False,
        "E_EXPRESSION_AS_FACT_POLICY",
    )

    plan = contract.get("canonical_composition_plan_contract")
    require(isinstance(plan, dict), "E_PLAN_CONTRACT")
    require(plan.get("authority") == "EXPRESSION_SERVICE_PREPARE", "E_PLAN_AUTHORITY")
    require(plan.get("is_independent_microservice") is False, "E_PLAN_MICROSERVICE")
    require(
        plan.get("maximum_active_canonical_plans_per_key") == 1, "E_PLAN_UNIQUENESS"
    )
    require(
        set(plan.get("competing_plan_writers_forbidden", []))
        == {"DIFY", "RETRIEVAL_LAYER", "GENERATOR"},
        "E_COMPETING_PLAN_WRITERS",
    )
    require(plan.get("audience_body_allowed_in_plan") is False, "E_PLAN_BODY")

    workflow = contract.get("composition_workflow")
    require(isinstance(workflow, dict), "E_WORKFLOW")
    stages = workflow.get("ordered_stages")
    require(isinstance(stages, list), "E_WORKFLOW_STAGES")
    require(
        [item.get("stage") for item in stages]
        == [
            "REQUIREMENT_SUMMARY",
            "USER_CONFIRMATION",
            "PREPARE",
            "CANDIDATE_AUTHORING",
            "VALIDATE",
        ],
        "E_WORKFLOW_ORDER",
    )
    require(
        workflow.get("prepare_must_precede_candidate_authoring") is True,
        "E_PREPARE_ORDER",
    )
    require(
        workflow.get("candidate_authoring_must_precede_validate") is True,
        "E_VALIDATE_ORDER",
    )
    candidate = next(
        item for item in stages if item.get("stage") == "CANDIDATE_AUTHORING"
    )
    require(candidate.get("may_add_facts") is False, "E_CANDIDATE_FACT_ADD")
    require(
        candidate.get("may_create_canonical_plan") is False, "E_CANDIDATE_PLAN_WRITE"
    )

    delivery = contract.get("delivery_contract")
    require(isinstance(delivery, dict), "E_DELIVERY_CONTRACT")
    require(
        delivery.get("action_card_may_contain_publishable_candidate") is False,
        "E_ACTION_CARD_PUBLISHABLE",
    )
    require(
        delivery.get("missing_input_may_be_filled_by_model") is False,
        "E_MODEL_FILL_MISSING",
    )

    endpoints = contract.get("api_contracts")
    require(isinstance(endpoints, list), "E_API_CONTRACTS")
    endpoint_keys = {
        (item.get("method"), item.get("path"))
        for item in endpoints
        if isinstance(item, dict)
    }
    require(
        endpoint_keys
        == {
            ("POST", "/v1/content/prepare"),
            ("POST", "/v1/content/validate"),
            ("GET", "/healthz"),
            ("GET", "/readyz"),
        },
        "E_API_ENDPOINT_SET",
    )
    require(
        all(item.get("implemented_in_this_package") is False for item in endpoints),
        "E_API_IMPLEMENTED_EARLY",
    )
    ready = next(item for item in endpoints if item.get("path") == "/readyz")
    require(ready.get("current_response_ready") is False, "E_READYZ_TRUE")

    evidence = contract.get("case_evidence_contract")
    require(isinstance(evidence, dict), "E_CASE_EVIDENCE")
    require(
        evidence.get("creates_second_case_inventory") is False,
        "E_SECOND_CASE_INVENTORY",
    )
    require(evidence.get("append_only") is True, "E_CASE_NOT_APPEND_ONLY")
    require(evidence.get("prior_event_mutation_allowed") is False, "E_CASE_MUTATION")
    require(evidence.get("failed_case_deletion_allowed") is False, "E_FAILURE_DELETE")
    require(
        evidence.get("pull_request_15_may_be_approved_asset") is False,
        "E_PR15_APPROVED",
    )

    ownership = contract.get("module_ownership")
    require(isinstance(ownership, dict), "E_MODULE_OWNERSHIP")
    require(
        set(ownership)
        == {
            "DIFY",
            "EXPRESSION_SERVICE",
            "BRAND_FACT_MODULE",
            "POSTGRESQL",
            "DIFY_KNOWLEDGE_BASE",
        },
        "E_MODULE_OWNER_SET",
    )
    require(
        "canonical_composition_plan" in ownership["DIFY"].get("does_not_own", []),
        "E_DIFY_PLAN_OWNER",
    )
    require(
        "canonical_composition_plan" in ownership["EXPRESSION_SERVICE"].get("owns", []),
        "E_EXPRESSION_PLAN_OWNER",
    )

    downstream = contract.get("downstream_package_boundaries")
    require(
        isinstance(downstream, list) and len(downstream) == 3, "E_DOWNSTREAM_PACKAGES"
    )
    roots = [item.get("exclusive_root") for item in downstream]
    require(len(set(roots)) == 3, "E_DOWNSTREAM_ROOT_COLLISION")
    require(
        all(
            item.get("state_before_foundation_master_green") == "LOCKED"
            for item in downstream
        ),
        "E_DOWNSTREAM_EARLY_UNLOCK",
    )
    require(
        contract.get("downstream_may_create_parallel_public_model") is False,
        "E_PARALLEL_PUBLIC_MODEL",
    )
    validate_all_false(contract.get("readiness"), "E_CONTRACT_READINESS")

    protocol = contract.get("review_protocol")
    require(isinstance(protocol, dict), "E_REVIEW_PROTOCOL")
    require(
        protocol.get("reviewer_must_not_be_author_or_final_merger") is True,
        "E_REVIEW_AUTHOR_SEPARATION",
    )
    require(
        protocol.get("reviewer_instances_must_be_distinct") is True,
        "E_REVIEW_INSTANCE_SEPARATION",
    )
    require(
        protocol.get("material_disagreement_requires_third_review") is True,
        "E_REVIEW_DISAGREEMENT_POLICY",
    )


def validate_identity_data(identity: dict[str, Any]) -> None:
    require(identity.get("schema_version") == "v1.0", "E_IDENTITY_VERSION")
    require(identity.get("task_id") == TASK_ID, "E_IDENTITY_TASK")
    source = identity.get("source")
    require(isinstance(source, dict), "E_IDENTITY_SOURCE")
    require(
        source.get("sha256")
        == "3b4577c411ea34ce46db5e8fe13b0af3ce751dcc443a4db95f59a32a1ca923f9",
        "E_IDENTITY_SOURCE_DIGEST",
    )
    require(
        source.get("continuous_fact_body_copied") is False, "E_CONTINUOUS_FACT_COPY"
    )
    tenant = identity.get("tenant")
    require(isinstance(tenant, dict), "E_TENANT")
    require(tenant.get("tenant_id") == "TENANT-DIYU-SIM-001", "E_TENANT_ID")
    require(tenant.get("simulation_only") is True, "E_TENANT_SIMULATION")
    require(tenant.get("publish_allowed") is False, "E_TENANT_PUBLISH")
    require(tenant.get("production_fact_eligible") is False, "E_TENANT_PRODUCTION_FACT")

    policy = identity.get("login_policy")
    require(isinstance(policy, dict), "E_LOGIN_POLICY")
    real = policy.get("real_enterprise")
    simulation = policy.get("simulation_exception")
    require(
        isinstance(real, dict) and isinstance(simulation, dict), "E_LOGIN_POLICY_PARTS"
    )
    require(real.get("one_principal_per_real_person") is True, "E_REAL_LOGIN_PRINCIPAL")
    require(real.get("shared_credentials_allowed") is False, "E_REAL_LOGIN_SHARED")
    require(real.get("Dify_user_id_is_authoritative") is False, "E_REAL_DIFY_ID")
    require(simulation.get("login_principal_count") == 1, "E_SIM_LOGIN_COUNT")
    require(
        simulation.get("content_account_count") == 11, "E_SIM_ACCOUNT_DECLARED_COUNT"
    )
    require(
        simulation.get("credential_material_in_repository") is False,
        "E_SIM_CREDENTIAL_STORAGE",
    )
    require(
        simulation.get("changes_real_enterprise_policy") is False, "E_SIM_POLICY_LEAK"
    )

    principals = identity.get("login_principals")
    organizations = identity.get("organizations")
    stores = identity.get("stores")
    roles = identity.get("work_roles")
    accounts = identity.get("content_accounts")
    require(isinstance(principals, list) and len(principals) == 1, "E_PRINCIPAL_COUNT")
    require(
        isinstance(organizations, list) and len(organizations) == 5,
        "E_ORGANIZATION_COUNT",
    )
    require(isinstance(stores, list) and len(stores) == 3, "E_STORE_COUNT")
    require(isinstance(roles, list) and roles, "E_WORK_ROLES")
    require(isinstance(accounts, list) and len(accounts) == 11, "E_ACCOUNT_COUNT")
    require(
        identity.get("work_roles_are_login_principals") is False,
        "E_ROLE_LOGIN_COLLAPSE",
    )

    organization_ids = {
        item.get("organization_id") for item in organizations if isinstance(item, dict)
    }
    store_ids = {item.get("store_id") for item in stores if isinstance(item, dict)}
    role_ids = {item.get("role_id") for item in roles if isinstance(item, dict)}
    require(
        len(organization_ids) == 5 and None not in organization_ids,
        "E_ORGANIZATION_IDS",
    )
    require(len(store_ids) == 3 and None not in store_ids, "E_STORE_IDS")
    require(len(role_ids) == len(roles) and None not in role_ids, "E_ROLE_IDS")
    for organization in organizations:
        require(organization.get("simulation_only") is True, "E_ORG_SIMULATION")
        require(organization.get("publish_allowed") is False, "E_ORG_PUBLISH")
    for store in stores:
        require(store.get("organization_id") in organization_ids, "E_STORE_ORG_REF")
        require(store.get("simulation_only") is True, "E_STORE_SIMULATION")
        require(store.get("publish_allowed") is False, "E_STORE_PUBLISH")
    for role in roles:
        require(role.get("organization_id") in organization_ids, "E_ROLE_ORG_REF")

    by_account = {
        item.get("account_id"): item for item in accounts if isinstance(item, dict)
    }
    require(
        {key: value.get("display_name") for key, value in by_account.items()}
        == EXPECTED_ACCOUNT_NAMES,
        "E_ACCOUNT_IDENTITIES",
    )
    for account_id, account in by_account.items():
        require(
            account.get("organization_id") in organization_ids,
            f"E_ACCOUNT_ORG:{account_id}",
        )
        store_id = account.get("store_id")
        require(
            store_id is None or store_id in store_ids, f"E_ACCOUNT_STORE:{account_id}"
        )
        makers = account.get("maker_role_ids")
        routes = account.get("confirmation_routes")
        require(isinstance(makers, list) and makers, f"E_ACCOUNT_MAKERS:{account_id}")
        require(set(makers).issubset(role_ids), f"E_ACCOUNT_MAKER_REF:{account_id}")
        require(
            isinstance(routes, list) and routes, f"E_ACCOUNT_CONFIRMERS:{account_id}"
        )
        for route in routes:
            confirmer_ids = route.get("confirmer_role_ids")
            require(
                isinstance(confirmer_ids, list) and confirmer_ids,
                f"E_CONFIRMERS:{account_id}",
            )
            require(
                set(confirmer_ids).issubset(role_ids), f"E_CONFIRMER_REF:{account_id}"
            )
        allowed_orgs = account.get("allowed_source_organization_ids")
        require(
            isinstance(allowed_orgs, list) and allowed_orgs,
            f"E_ACCOUNT_MATERIAL_SCOPE:{account_id}",
        )
        require(
            set(allowed_orgs).issubset(organization_ids),
            f"E_ACCOUNT_MATERIAL_REF:{account_id}",
        )
        require(
            account.get("cross_organization_source_requires_explicit_grant") is True,
            f"E_ACCOUNT_CROSS_SCOPE:{account_id}",
        )
        require(
            account.get("simulation_only") is True, f"E_ACCOUNT_SIMULATION:{account_id}"
        )
        require(
            account.get("publish_allowed") is False, f"E_ACCOUNT_PUBLISH:{account_id}"
        )
        require(
            bool(account.get("forbidden_claim_scopes")),
            f"E_ACCOUNT_FORBIDDEN_SCOPE:{account_id}",
        )

    principal = principals[0]
    require(
        principal.get("principal_id") == "SIM-LOGIN-DIYU-ACCEPTANCE-001",
        "E_SIM_PRINCIPAL_ID",
    )
    require(
        principal.get("trusted_identity_source") == "SERVER_MANAGED_ONLY",
        "E_SIM_IDENTITY_SOURCE",
    )
    require(principal.get("Dify_user_id_is_authoritative") is False, "E_SIM_DIFY_ID")
    require(principal.get("simulation_only") is True, "E_SIM_PRINCIPAL_FLAG")
    require(principal.get("publish_allowed") is False, "E_SIM_PRINCIPAL_PUBLISH")
    require(
        set(principal.get("allowed_content_account_ids", [])) == set(by_account),
        "E_SIM_ACCOUNT_ALLOWLIST",
    )

    serialized = json.dumps(identity, ensure_ascii=False).lower()
    for forbidden in (
        "secret_value",
        "credential_value",
        "-----begin private key-----",
        "ghp_",
        "sk-proj-",
    ):
        require(forbidden not in serialized, f"E_SECRET_MATERIAL:{forbidden}")
    invariants = identity.get("invariants")
    require(isinstance(invariants, dict), "E_IDENTITY_INVARIANTS")
    require(invariants.get("login_principal_count") == 1, "E_IDENTITY_LOGIN_INVARIANT")
    require(
        invariants.get("content_account_count") == 11, "E_IDENTITY_ACCOUNT_INVARIANT"
    )
    require(
        invariants.get("every_record_simulation_only") is True,
        "E_IDENTITY_SIM_INVARIANT",
    )
    require(
        invariants.get("every_record_publish_allowed") is False,
        "E_IDENTITY_PUBLISH_INVARIANT",
    )
    require(
        invariants.get("continuous_30_day_fact_body_included") is False,
        "E_IDENTITY_FACT_BODY",
    )
    require(
        invariants.get("credential_material_included") is False,
        "E_IDENTITY_CREDENTIAL_INVARIANT",
    )


def validate_topics_data(root: Path, topics: dict[str, Any]) -> None:
    require(topics.get("schema_version") == "v1.0", "E_TOPIC_VERSION")
    require(
        topics.get("mapping_kind")
        == "MANY_TO_MANY_USER_TOPIC_TO_INTERNAL_CONTENT_PRODUCT",
        "E_TOPIC_KIND",
    )
    require(
        topics.get("user_selects_topic_not_internal_product_id") is True,
        "E_TOPIC_USER_SELECTION",
    )
    require(topics.get("topic_is_not_permission_model") is True, "E_TOPIC_PERMISSION")
    source = topics.get("internal_profile_source")
    require(isinstance(source, dict), "E_TOPIC_SOURCE")
    source_path = root / str(source.get("path"))
    require(source_path.is_file(), "E_TOPIC_SOURCE_PATH")
    require(
        source.get("file_sha256")
        == "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056",
        "E_TOPIC_SOURCE_DECLARED_DIGEST",
    )
    require(
        sha256_file(source_path) == source.get("file_sha256"),
        "E_TOPIC_SOURCE_LIVE_DIGEST",
    )
    registry = yaml.safe_load(source_path.read_text(encoding="utf-8"))[
        "content_product_profile_registry"
    ]
    live_products = {
        item["content_product_type_id"]: item["chinese_label"]
        for item in registry["profiles"]
    }
    require(len(live_products) == 20, "E_TOPIC_LIVE_PRODUCT_COUNT")

    categories = topics.get("categories")
    products = topics.get("internal_products")
    require(
        isinstance(categories, list) and len(categories) == 8, "E_TOPIC_CATEGORY_COUNT"
    )
    require(isinstance(products, list) and len(products) == 20, "E_TOPIC_PRODUCT_COUNT")
    by_category = {
        item.get("topic_category_id"): item
        for item in categories
        if isinstance(item, dict)
    }
    require(
        {key: value.get("display_name") for key, value in by_category.items()}
        == EXPECTED_TOPIC_NAMES,
        "E_TOPIC_NAMES",
    )
    product_counter: Counter[str] = Counter()
    for category_id, category in by_category.items():
        product_ids = category.get("internal_product_ids")
        require(
            isinstance(product_ids, list) and len(product_ids) >= 2,
            f"E_TOPIC_NOT_MANY:{category_id}",
        )
        require(
            set(product_ids).issubset(live_products),
            f"E_TOPIC_UNKNOWN_PRODUCT:{category_id}",
        )
        product_counter.update(product_ids)
        visible_values = [
            category.get("display_name"),
            *category.get("plain_examples", []),
        ]
        require(
            all(
                isinstance(value, str) and not PROHIBITED_USER_PATTERN.search(value)
                for value in visible_values
            ),
            f"E_TOPIC_INTERNAL_LEAK:{category_id}",
        )
    require(set(product_counter) == set(live_products), "E_TOPIC_PRODUCT_COVERAGE")
    require(
        all(count >= 2 for count in product_counter.values()),
        "E_TOPIC_NOT_MANY_TO_MANY",
    )
    declared_products = {
        item.get("content_product_id"): item
        for item in products
        if isinstance(item, dict)
    }
    require(set(declared_products) == set(live_products), "E_TOPIC_DECLARED_PRODUCTS")
    for product_id, product in declared_products.items():
        require(
            product.get("internal_label") == live_products[product_id],
            f"E_TOPIC_PRODUCT_LABEL:{product_id}",
        )
        require(
            product.get("user_visible_id") is False,
            f"E_TOPIC_PRODUCT_VISIBILITY:{product_id}",
        )
    policy = topics.get("user_output_policy")
    require(isinstance(policy, dict), "E_TOPIC_OUTPUT_POLICY")
    require(
        policy.get("may_show_internal_content_product_id") is False,
        "E_TOPIC_CP_VISIBILITY",
    )
    require(
        policy.get("may_show_component_id") is False, "E_TOPIC_COMPONENT_VISIBILITY"
    )
    require(policy.get("may_show_route_code") is False, "E_TOPIC_ROUTE_VISIBILITY")
    require(policy.get("may_show_raw_error_code") is False, "E_TOPIC_ERROR_VISIBILITY")


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    operation = case.get("operation")
    data = case.get("input")
    require(isinstance(data, dict), f"E_CASE_INPUT:{case.get('case_id')}")
    if operation == "chat":
        effects = data.get("requested_effects", {})
        if effects.get("create_plan") or effects.get("write_brand_fact"):
            return {
                "decision": "REJECT_CHAT_SIDE_EFFECT",
                "plan_created": False,
                "brand_fact_written": False,
            }
        if data.get("intent") == "NORMAL_CHAT":
            return {
                "decision": "CHAT_ONLY",
                "plan_created": False,
                "brand_fact_written": False,
            }
        return {
            "decision": "INSPIRATION_ONLY",
            "plan_created": False,
            "brand_fact_written": False,
        }
    if operation == "scope":
        dimensions = ("tenant", "store", "account")
        if any(
            data.get(f"trusted_{name}_id") != data.get(f"requested_{name}_id")
            for name in dimensions
        ):
            return {"decision": "REJECT_SCOPE_OVERRIDE"}
    if operation == "identity":
        if data.get("identity_source") != "SERVER_CONFIRMED" or not data.get(
            "server_confirmed_principal"
        ):
            return {"decision": "REJECT_UNTRUSTED_IDENTITY"}
    if operation == "consume_material":
        if not data.get("tenant_match"):
            return {"decision": "REJECT_CROSS_TENANT_MATERIAL"}
        if not data.get("store_match"):
            return {"decision": "REJECT_CROSS_STORE_MATERIAL"}
        if not data.get("account_match"):
            return {"decision": "REJECT_CROSS_ACCOUNT_MATERIAL"}
        if data.get("material_state") == "EXPIRED":
            return {"decision": "REJECT_EXPIRED_MATERIAL"}
        if data.get("material_state") == "REVOKED":
            return {"decision": "REJECT_REVOKED_MATERIAL"}
        if data.get("authorization_state") != "GRANTED":
            return {"decision": "REJECT_UNAUTHORIZED_MATERIAL"}
        return {"decision": "ALLOW_SCOPED_MATERIAL"}
    if operation == "fact_precedence":
        if data.get("attempt_narrative_override"):
            return {"decision": "REJECT_FACT_PRECEDENCE_OVERRIDE"}
        return {"decision": "USE_PRECISE_FACT"}
    if operation == "prepare":
        if data.get("expression_baseline_matches") is not True:
            return {
                "decision": "REJECT_BASELINE_TAMPER",
                "canonical_plan_created": False,
            }
        if data.get("trusted_scope_match") is not True:
            return {
                "decision": "REJECT_SCOPE_OVERRIDE",
                "canonical_plan_created": False,
            }
        if data.get("requirement_status") != "CONFIRMED":
            return {
                "decision": "REJECT_UNCONFIRMED_REQUIREMENT",
                "canonical_plan_created": False,
            }
        if data.get("active_plan_count_for_key") != 0:
            return {
                "decision": "REJECT_DUPLICATE_CANONICAL_PLAN",
                "canonical_plan_created": False,
            }
        if (
            data.get("material_state") != "ACTIVE"
            or data.get("authorization_state") != "GRANTED"
        ):
            return {
                "decision": "ACTION_CARD_REQUEST_AUTHORIZATION",
                "canonical_plan_created": False,
            }
        if data.get("missing_required"):
            return {
                "decision": "ACTION_CARD_COLLECT_FACT",
                "canonical_plan_created": False,
            }
        return {"decision": "PREPARE_PLAN", "canonical_plan_created": True}
    if operation == "validate":
        if data.get("internal_identifier_leak"):
            return {"decision": "REJECT_INTERNAL_IDENTIFIER_LEAK"}
        if not data.get("trusted_scope_match"):
            return {"decision": "REJECT_SCOPE_OVERRIDE"}
        if not data.get("plan_consistent") or not data.get("all_claims_supported"):
            return {"decision": "VALIDATE_REVISE"}
        if data.get("authorization_state") != "GRANTED":
            return {"decision": "VALIDATE_BLOCK"}
        return {"decision": "VALIDATE_PASS"}
    if operation == "fact_input":
        if (
            data.get("input_kind") == "EXPRESSION_COMPONENT"
            and data.get("claimed_as") == "BRAND_FACT"
        ):
            return {"decision": "REJECT_COMPONENT_AS_FACT"}
    if operation == "simulation_record":
        if (
            data.get("simulation_only") is not True
            or data.get("publish_allowed") is not False
        ):
            return {"decision": "REJECT_SIMULATION_PUBLISH"}
    if operation == "baseline":
        expected = (68, 8, 85, 20, True)
        actual = (
            data.get("active_component_count"),
            data.get("active_control_rule_count"),
            data.get("active_edge_count"),
            data.get("ab_path_count"),
            data.get("readiness_all_false"),
        )
        if actual != expected:
            return {"decision": "REJECT_BASELINE_TAMPER"}
    if operation == "write_surface":
        requested = str(data.get("requested_path", ""))
        allowed = [str(item).rstrip("/") for item in data.get("allowed_roots", [])]
        if not any(
            requested == root or requested.startswith(f"{root}/") for root in allowed
        ):
            return {"decision": "REJECT_UNAUTHORIZED_PATH"}
    if operation == "switch_account":
        if data.get("account_is_allowlisted") and data.get(
            "preserve_target_account_scope"
        ):
            return {"decision": "SWITCH_ACCOUNT"}
        return {"decision": "REJECT_ACCOUNT_SWITCH"}
    if operation == "revise":
        if (
            data.get("existing_plan_ref")
            and not data.get("create_competing_plan")
            and not data.get("change_confirmed_fact")
        ):
            return {"decision": "REVISE_EXISTING_CANDIDATE"}
        return {"decision": "REJECT_REVISION_SCOPE"}
    raise CheckFailure(f"E_CASE_UNHANDLED:{case.get('case_id')}")


def validate_cases(cases: list[dict[str, Any]]) -> None:
    require(len(cases) >= 20, "E_CASE_COUNT")
    ids = [case.get("case_id") for case in cases]
    require(len(ids) == len(set(ids)) and None not in ids, "E_CASE_IDS")
    classes = Counter(case.get("case_class") for case in cases)
    require(
        classes["POSITIVE"] >= 6 and classes["NEGATIVE"] >= 13, "E_CASE_DISTRIBUTION"
    )
    decisions: set[str] = set()
    for case in cases:
        expected = case.get("expected")
        require(isinstance(expected, dict), f"E_CASE_EXPECTED:{case.get('case_id')}")
        actual = evaluate_case(case)
        require(
            actual.get("decision") == expected.get("decision"),
            f"E_CASE_DECISION:{case.get('case_id')}",
        )
        for key in ("plan_created", "brand_fact_written", "canonical_plan_created"):
            if key in expected:
                require(
                    actual.get(key) == expected.get(key),
                    f"E_CASE_OUTPUT:{case.get('case_id')}:{key}",
                )
        message = expected.get("user_message")
        require(
            isinstance(message, str) and message.strip(),
            f"E_CASE_USER_MESSAGE:{case.get('case_id')}",
        )
        require(
            PROHIBITED_USER_PATTERN.search(message) is None,
            f"E_CASE_MESSAGE_LEAK:{case.get('case_id')}",
        )
        decisions.add(str(expected.get("decision")))
    required_decisions = {
        "REJECT_SCOPE_OVERRIDE",
        "REJECT_UNTRUSTED_IDENTITY",
        "REJECT_CROSS_TENANT_MATERIAL",
        "REJECT_CROSS_STORE_MATERIAL",
        "REJECT_CROSS_ACCOUNT_MATERIAL",
        "REJECT_EXPIRED_MATERIAL",
        "REJECT_REVOKED_MATERIAL",
        "REJECT_UNAUTHORIZED_MATERIAL",
        "REJECT_FACT_PRECEDENCE_OVERRIDE",
        "REJECT_CHAT_SIDE_EFFECT",
        "REJECT_UNCONFIRMED_REQUIREMENT",
        "REJECT_COMPONENT_AS_FACT",
        "REJECT_DUPLICATE_CANONICAL_PLAN",
        "REJECT_SIMULATION_PUBLISH",
        "REJECT_INTERNAL_IDENTIFIER_LEAK",
        "REJECT_BASELINE_TAMPER",
        "REJECT_UNAUTHORIZED_PATH",
    }
    require(required_decisions.issubset(decisions), "E_CASE_NEGATIVE_COVERAGE")


def validate_status_and_manifest(
    root: Path, status: dict[str, Any], manifest: dict[str, Any]
) -> None:
    require(status.get("task_id") == TASK_ID, "E_STATUS_TASK")
    require(
        status.get("repository_role") == "SINGLE_BUSINESS_REPOSITORY",
        "E_STATUS_REPOSITORY_ROLE",
    )
    require(status.get("current_owner") == "PUBLIC_FOUNDATION_001", "E_STATUS_OWNER")
    state = status.get("state_resolution")
    require(isinstance(state, dict), "E_STATUS_STATE_MODEL")
    require(
        state.get("candidate_state") == "REVIEW_PENDING_PUBLIC_FOUNDATION",
        "E_STATUS_CANDIDATE",
    )
    require(
        state.get("master_green_state") == "PUBLIC_FOUNDATION_FROZEN", "E_STATUS_FROZEN"
    )
    require(
        state.get("may_not_self_activate_from_branch") is True, "E_STATUS_SELF_ACTIVATE"
    )
    expression = status.get("expression_v1")
    require(
        expression
        == {
            "active_component_count": 68,
            "active_control_rule_count": 8,
            "active_edge_count": 85,
            "ab_structural_path_group_count": 20,
            "internal_content_product_count": 20,
            "generator_qualified": False,
            "runtime_ready": False,
        },
        "E_STATUS_EXPRESSION",
    )
    quality = status.get("quality_baseline")
    require(isinstance(quality, dict), "E_STATUS_QUALITY")
    require(quality.get("target_case_count") == 300, "E_STATUS_300")
    require(quality.get("target_baseline_frozen") is False, "E_STATUS_300_FROZEN")
    require(quality.get("frozen_reference_inventory_count") == 120, "E_STATUS_120")
    require(quality.get("historical_component_inventory_count") == 86, "E_STATUS_86")
    require(
        quality.get("changed_or_harmed_by_this_task") is False, "E_STATUS_CORE_HARM"
    )
    validate_all_false(status.get("readiness"), "E_STATUS_READINESS")
    history = status.get("historical_product_route_files")
    require(isinstance(history, list) and len(history) == 3, "E_STATUS_HISTORY")
    for record in history:
        path = root / str(record.get("path"))
        require(record.get("authority") == "HISTORICAL_ONLY", "E_HISTORY_AUTHORITY")
        require(path.is_file(), "E_HISTORY_PATH")
        require(
            sha256_file(path) == record.get("sha256"),
            f"E_HISTORY_DIGEST:{record.get('path')}",
        )

    require(manifest.get("task_id") == TASK_ID, "E_MANIFEST_TASK")
    require(
        manifest.get("repository") == "andyan77/diyu-agent", "E_MANIFEST_REPOSITORY"
    )
    owner = manifest.get("single_current_owner")
    require(isinstance(owner, dict), "E_MANIFEST_OWNER")
    require(owner.get("owner_id") == "PUBLIC_FOUNDATION_001", "E_MANIFEST_OWNER_ID")
    require(owner.get("root") == FOUNDATION_ROOT.as_posix(), "E_MANIFEST_OWNER_ROOT")
    downstream = manifest.get("downstream_reserved_write_roots")
    require(
        isinstance(downstream, list) and len(downstream) == 3, "E_MANIFEST_DOWNSTREAM"
    )
    roots = [str(item.get("root")) for item in downstream]
    require(len(set(roots)) == 3, "E_MANIFEST_ROOT_COLLISION")
    for left in roots:
        for right in roots:
            if left != right:
                require(not left.startswith(f"{right}/"), "E_MANIFEST_ROOT_OVERLAP")
    require(
        manifest.get("readiness_transition_authorized") is False, "E_MANIFEST_READINESS"
    )


def validate_reviews(root: Path, result: dict[str, Any]) -> None:
    review_state = result.get("review_state")
    require(
        review_state in {"PENDING_INDEPENDENT_REVIEWS", "PASS_TO_MERGE"},
        "E_REVIEW_STATE",
    )
    validate_foundation_files(
        root, "PASS_TO_MERGE" if review_state == "PASS_TO_MERGE" else "PENDING"
    )
    if review_state == "PENDING_INDEPENDENT_REVIEWS":
        require(result.get("independent_reviews") == [], "E_PENDING_REVIEW_REFS")
        require(result.get("coordinator_decision") is None, "E_PENDING_COORDINATOR")
        return

    arch = load_yaml(root, ARCH_REVIEW_PATH, "independent_review")
    trust = load_yaml(root, TRUST_REVIEW_PATH, "independent_review")
    coordinator = load_yaml(root, COORDINATOR_PATH, "coordinator_decision")
    reports = [arch, trust]
    expected_ids = {"ARCHITECTURE_CONSUMABILITY_REVIEW", "TRUST_FACT_SAFETY_REVIEW"}
    require(
        {report.get("review_id") for report in reports} == expected_ids, "E_REVIEW_IDS"
    )
    reviewed_commit = result.get("reviewed_candidate_commit")
    digest = result.get("candidate_snapshot_digest")
    reviewer_ids: list[str] = []
    for report in reports:
        reviewer = report.get("reviewer")
        require(isinstance(reviewer, dict), "E_REVIEWER")
        reviewer_id = reviewer.get("agent_id")
        require(isinstance(reviewer_id, str) and reviewer_id, "E_REVIEWER_ID")
        reviewer_ids.append(reviewer_id)
        require(reviewer_id != "codex-execution-primary", "E_REVIEWER_IS_AUTHOR")
        require(report.get("reviewed_commit") == reviewed_commit, "E_REVIEWED_COMMIT")
        require(report.get("reviewed_snapshot_digest") == digest, "E_REVIEWED_DIGEST")
        require(report.get("verdict") == "PASS", "E_REVIEW_VERDICT")
        require(
            isinstance(report.get("score"), int) and report["score"] >= 90,
            "E_REVIEW_SCORE",
        )
        require(report.get("blocking_findings") == [], "E_REVIEW_BLOCKERS")
        require(report.get("repo_changed") is False, "E_REVIEW_REPO_WRITE")
    require(len(set(reviewer_ids)) == 2, "E_REVIEWER_IDENTITY_COLLISION")
    coordinator_identity = coordinator.get("coordinator")
    require(isinstance(coordinator_identity, dict), "E_COORDINATOR_IDENTITY")
    coordinator_id = coordinator_identity.get("agent_id")
    require(isinstance(coordinator_id, str) and coordinator_id, "E_COORDINATOR_ID")
    require(
        coordinator_id not in {*reviewer_ids, "codex-execution-primary"},
        "E_COORDINATOR_COLLISION",
    )
    require(
        coordinator.get("reviewed_candidate_commit") == reviewed_commit,
        "E_COORDINATOR_COMMIT",
    )
    require(
        coordinator.get("reviewed_snapshot_digest") == digest, "E_COORDINATOR_DIGEST"
    )
    require(coordinator.get("decision") == "PASS_TO_MERGE", "E_COORDINATOR_DECISION")
    require(
        isinstance(coordinator.get("score"), int) and coordinator["score"] >= 90,
        "E_COORDINATOR_SCORE",
    )
    require(coordinator.get("material_disagreements") == [], "E_MATERIAL_DISAGREEMENT")
    require(coordinator.get("blocking_findings") == [], "E_COORDINATOR_BLOCKERS")
    review_refs = result.get("independent_reviews")
    require(
        isinstance(review_refs, list)
        and {item.get("path") for item in review_refs}
        == {ARCH_REVIEW_PATH.as_posix(), TRUST_REVIEW_PATH.as_posix()},
        "E_RESULT_REVIEW_REFS",
    )
    for record in review_refs:
        path = root / str(record.get("path"))
        require(sha256_file(path) == record.get("sha256"), "E_RESULT_REVIEW_DIGEST")
    coordinator_ref = result.get("coordinator_decision")
    require(isinstance(coordinator_ref, dict), "E_RESULT_COORDINATOR_REF")
    require(
        coordinator_ref.get("path") == COORDINATOR_PATH.as_posix(),
        "E_RESULT_COORDINATOR_PATH",
    )
    require(
        sha256_file(root / COORDINATOR_PATH) == coordinator_ref.get("sha256"),
        "E_RESULT_COORDINATOR_DIGEST",
    )


def validate_result(root: Path, result: dict[str, Any]) -> None:
    require(result.get("schema_version") == "v1.0", "E_RESULT_VERSION")
    require(result.get("task_id") == TASK_ID, "E_RESULT_TASK")
    require(
        result.get("baseline_master_commit")
        == "847e0db45ae0a3a116222e5f66b99cba225fd9f2",
        "E_RESULT_BASELINE",
    )
    require(
        result.get("candidate_snapshot_digest") == snapshot_digest(root),
        "E_RESULT_SNAPSHOT_DIGEST",
    )
    require(
        result.get("expression_baseline_digest_match") is True, "E_RESULT_EXPRESSION"
    )
    require(
        result.get("core_numbers_300_120_86_unchanged") is True, "E_RESULT_CORE_NUMBERS"
    )
    require(result.get("http_service_implemented") is False, "E_RESULT_HTTP")
    require(result.get("external_provider_call_count") == 0, "E_RESULT_PROVIDER_CALL")
    require(result.get("continuous_deployment_implemented") is False, "E_RESULT_CD")
    validate_all_false(result.get("readiness"), "E_RESULT_READINESS")
    validate_reviews(root, result)


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    contract = load_yaml(root, CONTRACT_PATH, "public_foundation_contract")
    identity = load_yaml(root, IDENTITY_PATH, "simulation_tenant")
    topics = load_yaml(root, TOPIC_PATH, "topic_product_mapping")
    cases = load_jsonl(root, CASES_PATH)
    status = load_yaml(root, STATUS_PATH, "current_product_status")
    manifest = load_yaml(root, MANIFEST_PATH, "product_workspace_manifest")
    result = load_yaml(root, RESULT_PATH, "public_foundation_result")
    validate_contract_data(root, contract)
    validate_expression_baseline(root, contract)
    validate_core_numbers(root, contract)
    validate_identity_data(identity)
    validate_topics_data(root, topics)
    validate_cases(cases)
    validate_status_and_manifest(root, status, manifest)
    validate_result(root, result)
    return {
        "task_id": TASK_ID,
        "contract_cases": len(cases),
        "content_accounts": len(identity["content_accounts"]),
        "topic_categories": len(topics["categories"]),
        "internal_products": len(topics["internal_products"]),
        "review_state": result["review_state"],
        "result": "PASS",
    }


def expect_failure(callback: Callable[[], None], expected_prefix: str) -> None:
    try:
        callback()
    except CheckFailure as error:
        require(
            str(error).startswith(expected_prefix), f"E_SELFTEST_WRONG_ERROR:{error}"
        )
        return
    raise CheckFailure(f"E_SELFTEST_FALSE_NEGATIVE:{expected_prefix}")


def run_selftest() -> dict[str, Any]:
    validate_repository(ROOT)
    contract = load_yaml(ROOT, CONTRACT_PATH, "public_foundation_contract")
    identity = load_yaml(ROOT, IDENTITY_PATH, "simulation_tenant")
    topics = load_yaml(ROOT, TOPIC_PATH, "topic_product_mapping")
    cases = load_jsonl(ROOT, CASES_PATH)
    status = load_yaml(ROOT, STATUS_PATH, "current_product_status")
    manifest = load_yaml(ROOT, MANIFEST_PATH, "product_workspace_manifest")

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["trusted_scope_contract"][
        "user_input_may_override_server_scope"
    ] = True
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract),
        "E_SCOPE_OVERRIDE_POLICY",
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["content_accounts"][0]["publish_allowed"] = True
    expect_failure(
        lambda: validate_identity_data(mutated_identity), "E_ACCOUNT_PUBLISH"
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["login_principals"][0]["allowed_content_account_ids"].pop()
    expect_failure(
        lambda: validate_identity_data(mutated_identity), "E_SIM_ACCOUNT_ALLOWLIST"
    )

    mutated_topics = copy.deepcopy(topics)
    for category in mutated_topics["categories"]:
        category["internal_product_ids"] = [
            item for item in category["internal_product_ids"] if item != "CP20"
        ]
    expect_failure(
        lambda: validate_topics_data(ROOT, mutated_topics), "E_TOPIC_PRODUCT_COVERAGE"
    )

    mutated_cases = copy.deepcopy(cases)
    mutated_cases[0]["expected"]["decision"] = "PREPARE_PLAN"
    expect_failure(lambda: validate_cases(mutated_cases), "E_CASE_DECISION")

    mutated_status = copy.deepcopy(status)
    mutated_status["readiness"]["production_ready"] = True
    expect_failure(
        lambda: validate_status_and_manifest(ROOT, mutated_status, manifest),
        "E_STATUS_READINESS:production_ready",
    )

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["downstream_reserved_write_roots"][1]["root"] = mutated_manifest[
        "downstream_reserved_write_roots"
    ][0]["root"]
    expect_failure(
        lambda: validate_status_and_manifest(ROOT, status, mutated_manifest),
        "E_MANIFEST_ROOT_COLLISION",
    )

    with tempfile.TemporaryDirectory(
        prefix="product-foundation-selftest-"
    ) as temporary:
        temp_root = Path(temporary)
        shutil.copytree(ROOT / FOUNDATION_ROOT, temp_root / FOUNDATION_ROOT)
        extra = temp_root / FOUNDATION_ROOT / "unexpected.yaml"
        extra.write_text("unexpected: true\n", encoding="utf-8")
        result = load_yaml(ROOT, RESULT_PATH, "public_foundation_result")
        review_state = (
            "PASS_TO_MERGE"
            if result.get("review_state") == "PASS_TO_MERGE"
            else "PENDING"
        )
        expect_failure(
            lambda: validate_foundation_files(temp_root, review_state),
            "E_FOUNDATION_FILE_SET",
        )

    return {"selftest_cases": 8, "result": "PASS"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = run_selftest() if args.selftest else validate_repository(ROOT)
    except (
        CheckFailure,
        KeyError,
        TypeError,
        ValueError,
        yaml.YAMLError,
        json.JSONDecodeError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
