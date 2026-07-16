#!/usr/bin/env python3
"""Fail-closed checker for the Diyu public product foundation."""

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
from collections import Counter
from datetime import datetime
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
LEGACY_GATE1_CHECKER_PATH = Path("ci/checkers/check_gate1_v1_1_current.py")
CHECKER_PATH = Path("ci/checkers/check_product_foundation.py")
WORKFLOW_PATH = Path(".github/workflows/ci.yml")
FROZEN_REVIEWED_COMMIT = "3f610726943dee5545d4d310f107239f2eeb9234"
AUTHORIZED_CURRENT_LIVE_PATHS = frozenset(
    {LEGACY_GATE1_CHECKER_PATH, CHECKER_PATH, WORKFLOW_PATH}
)
SUCCESSOR_PACKAGES = (
    (
        "PACKAGE_2_LIGHT_EXPRESSION_SERVICE",
        Path("12_expression_service/expression_runtime_adapter_001"),
        Path(
            "12_expression_service/expression_runtime_adapter_001/check_light_expression_service.py"
        ),
        "PACKAGE_2_ONLY",
    ),
    (
        "PACKAGE_3_BRAND_DATA",
        Path("13_brand_data/brand_data_import_001"),
        Path("13_brand_data/brand_data_import_001/check_brand_data_import.py"),
        "PACKAGE_3_ONLY",
    ),
    (
        "PACKAGE_4_DIFY_SHELL",
        Path("14_dify_shell/dify_content_shell_001"),
        Path("14_dify_shell/dify_content_shell_001/check_dify_content_shell.py"),
        "PACKAGE_4_ONLY",
    ),
)
SERIAL_SUCCESSOR_PACKAGES = (
    (
        "PACKAGE_5_BRAND_FACT_RETRIEVAL",
        Path("15_brand_retrieval/brand_fact_retrieval_001"),
        Path(
            "15_brand_retrieval/brand_fact_retrieval_001/check_brand_fact_retrieval.py"
        ),
        "PACKAGE_5_ONLY",
    ),
    (
        "PACKAGE_6_FACT_AWARE_PLAN_ADAPTER",
        Path("16_composition_runtime/fact_aware_plan_adapter_001"),
        Path(
            "16_composition_runtime/fact_aware_plan_adapter_001/"
            "check_fact_aware_plan_adapter.py"
        ),
        "PACKAGE_6_ONLY",
    ),
    (
        "PACKAGE_7_DIFY_END_TO_END",
        Path("17_dify_runtime/dify_end_to_end_001"),
        Path("17_dify_runtime/dify_end_to_end_001/check_dify_end_to_end.py"),
        "PACKAGE_7_ONLY",
    ),
    (
        "PACKAGE_8_HOSTED_OPERATIONS",
        Path("18_deployment/hosted_operations_001"),
        Path("18_deployment/hosted_operations_001/check_hosted_operations.py"),
        "PACKAGE_8_ONLY",
    ),
)
CHECKED_DOWNSTREAM_PACKAGES = SUCCESSOR_PACKAGES + SERIAL_SUCCESSOR_PACKAGES
MANDATORY_SUCCESSOR_ROOTS = frozenset(
    {
        Path("16_composition_runtime/fact_aware_plan_adapter_001"),
        Path("17_dify_runtime/dify_end_to_end_001"),
        Path("18_deployment/hosted_operations_001"),
    }
)
REFERENCE_SAFE_SUCCESSOR_COMMITS = {
    Path(
        "15_brand_retrieval/brand_fact_retrieval_001/check_brand_fact_retrieval.py"
    ): "24cd9888f38f2f22b22aa6c5a23f388b39fa1469",
    Path(
        "17_dify_runtime/dify_end_to_end_001/check_dify_end_to_end.py"
    ): "f046ec6e3d1a34345c97292e9ab1f5a13a2bd031",
}
REFERENCE_SAFE_SUCCESSOR_MUTABLE_PATHS = {
    Path("17_dify_runtime/dify_end_to_end_001/check_dify_end_to_end.py"): {
        Path("17_dify_runtime/dify_end_to_end_001/persistence.py"),
        Path("17_dify_runtime/dify_end_to_end_001/runtime_models.py"),
        Path("17_dify_runtime/dify_end_to_end_001/runtime_retrieval.py"),
        Path("17_dify_runtime/dify_end_to_end_001/runtime_service.py"),
    },
}
SUCCESSOR_NORMAL_STEP_NAME = "Run reserved downstream package checks"
SUCCESSOR_OPTIMIZED_STEP_NAME = (
    "Verify reserved downstream package fail-closed optimized mode"
)
SUCCESSOR_NORMAL_RUN_LINES = (
    "set -euo pipefail",
    "run_downstream_package_checker() {",
    '  package_root="$1"',
    '  checker="$2"',
    '  required="${3:-false}"',
    '  reference_commit="${4:-}"',
    '  test "$required" = "true" || test "$required" = "false"',
    '  if [ ! -e "$package_root" ]; then',
    '    test "$required" = "false"',
    "    return 0",
    "  fi",
    '  test -d "$package_root"',
    '  test -f "$checker"',
    '  run_root="."',
    '  temporary_parent=""',
    '  if [ -n "$reference_commit" ]; then',
    '    temporary_parent="$(mktemp -d)"',
    '    run_root="$temporary_parent/snapshot"',
    '    git worktree add --detach "$run_root" "$reference_commit" >/dev/null',
    "  fi",
    "  set +e",
    '  (cd "$run_root" && python3 "$checker" && python3 "$checker" --selftest)',
    "  code=$?",
    "  set -e",
    '  if [ -n "$temporary_parent" ]; then',
    '    git worktree remove --force "$run_root" >/dev/null',
    '    rmdir "$temporary_parent"',
    "  fi",
    '  test "$code" -eq 0',
    "}",
    *(
        f'run_downstream_package_checker "{package_root.as_posix()}" "{checker.as_posix()}"'
        f' "{"true" if package_root in MANDATORY_SUCCESSOR_ROOTS else "false"}"'
        + (
            f' "{REFERENCE_SAFE_SUCCESSOR_COMMITS[checker]}"'
            if checker in REFERENCE_SAFE_SUCCESSOR_COMMITS
            else ""
        )
        for _, package_root, checker, _ in CHECKED_DOWNSTREAM_PACKAGES
    ),
)
SUCCESSOR_OPTIMIZED_RUN_LINES = (
    "set -euo pipefail",
    "run_downstream_package_checker_optimized() {",
    '  package_root="$1"',
    '  checker="$2"',
    '  required="${3:-false}"',
    '  reference_commit="${4:-}"',
    '  test "$required" = "true" || test "$required" = "false"',
    '  if [ ! -e "$package_root" ]; then',
    '    test "$required" = "false"',
    "    return 0",
    "  fi",
    '  test -d "$package_root"',
    '  test -f "$checker"',
    '  run_root="."',
    '  temporary_parent=""',
    '  if [ -n "$reference_commit" ]; then',
    '    temporary_parent="$(mktemp -d)"',
    '    run_root="$temporary_parent/snapshot"',
    '    git worktree add --detach "$run_root" "$reference_commit" >/dev/null',
    "  fi",
    "  set +e",
    '  (cd "$run_root" && python3 -O "$checker")',
    "  code=$?",
    "  set -e",
    '  test "$code" -eq 2',
    "  set +e",
    '  (cd "$run_root" && python3 -O "$checker" --selftest)',
    "  code=$?",
    "  set -e",
    '  test "$code" -eq 2',
    '  if [ -n "$temporary_parent" ]; then',
    '    git worktree remove --force "$run_root" >/dev/null',
    '    rmdir "$temporary_parent"',
    "  fi",
    "}",
    *(
        f'run_downstream_package_checker_optimized "{package_root.as_posix()}" "{checker.as_posix()}"'
        f' "{"true" if package_root in MANDATORY_SUCCESSOR_ROOTS else "false"}"'
        + (
            f' "{REFERENCE_SAFE_SUCCESSOR_COMMITS[checker]}"'
            if checker in REFERENCE_SAFE_SUCCESSOR_COMMITS
            else ""
        )
        for _, package_root, checker, _ in CHECKED_DOWNSTREAM_PACKAGES
    ),
)

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
    LEGACY_GATE1_CHECKER_PATH,
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
    r"(?:(?<![A-Z0-9])CP\d{2}(?!\d)|(?<![A-Z0-9])(?:BNO|BRV|VGA|BCL|FC)-\d{2}(?!\d)|"
    r"(?<![A-Z0-9])G1V11-[A-Z0-9-]+|(?<![A-Z0-9])RCV2-[A-Z0-9-]+|"
    r"(?<![A-Z0-9])E_[A-Z0-9_]+|(?<![A-Z0-9])(?:all_required_inputs_present|"
    r"required_source_missing|required_fact_missing|required_authorization_missing)(?![A-Z0-9_]))",
    re.IGNORECASE,
)
INTERNAL_ROUTE_IDS = frozenset(
    {
        "all_required_inputs_present",
        "required_source_missing",
        "required_fact_missing",
        "required_authorization_missing",
    }
)
TRUSTED_SCOPE_DIMENSIONS = (
    "tenant_id",
    "brand_id",
    "organization_id",
    "store_ids",
    "login_principal_id",
    "allowed_content_account_ids",
)
REQUEST_SCOPE_FIELDS = (
    "tenant_id",
    "brand_id",
    "organization_id",
    "store_id",
    "login_principal_id",
    "content_account_id",
)
NARRATIVE_FRAGMENT_METADATA = (
    "fragment_id",
    "tenant_id",
    "brand_id",
    "source_organization_id",
    "source_store_id",
    "source_ref",
    "applicable_organization_ids",
    "applicable_store_ids",
    "applicable_content_account_ids",
    "observed_at",
    "valid_until",
    "authorization_ref",
    "authorization_state",
    "disclosure_scope",
    "status",
)
PRECISE_FACT_METADATA = (
    "fact_id",
    "tenant_id",
    "brand_id",
    "organization_id",
    "store_id",
    "applicable_content_account_ids",
    "fact_kind",
    "value",
    "source_ref",
    "effective_at",
    "valid_until",
    "authorization_ref",
    "disclosure_scope",
    "status",
)
ALLOWED_FACT_KINDS = frozenset(
    {
        "SKU",
        "SPECIFICATION",
        "PRICE",
        "STOCK",
        "TIME_POINT",
        "AUTHORIZATION",
        "REVOCATION",
    }
)
FIXTURE_SERVER_EVALUATION_TIME = "2026-07-14T00:00:00Z"
NEUTRAL_EXPRESSION_PROFILE_REF = "expression-profile://neutral-default/v1"
HIGH_LEVEL_MODE_REFS = frozenset(
    {
        "expression-mode://documentary-observation/v1",
        "expression-mode://professional-explanation/v1",
        "expression-mode://life-scene/v1",
        "expression-mode://styling-demonstration/v1",
        "expression-mode://store-micro-documentary/v1",
        "expression-mode://product-role-narrative/v1",
    }
)
HARD_CHECK_CATEGORIES = frozenset(
    {
        "fact_support",
        "source_provenance",
        "authorization",
        "privacy",
        "trusted_scope",
        "effective_time_and_revocation",
        "enterprise_commitment",
        "explicit_brand_prohibition",
        "internal_identifier_leak",
    }
)
SOFT_EVALUATION_TASKS = frozenset(
    {
        "task_fit",
        "brand_fit",
        "naturalness",
        "platform_fit",
        "candidate_difference",
    }
)
EXPRESSION_GUIDANCE_INPUT_KINDS = frozenset(
    {
        "EXPRESSION_COMPONENT",
        "BRAND_EXPRESSION_PROFILE",
        "HIGH_LEVEL_MODE",
        "APPROVED_EXAMPLE",
        "CLIENT_SOFT_PREFERENCE",
    }
)
AUTHORITY_CLAIM_KINDS = frozenset({"BRAND_FACT", "AUTHORIZATION", "TRUSTED_SCOPE"})
CLIENT_SOFT_PREFERENCE_FIELDS = frozenset(
    {
        "rhythm",
        "emotional_intensity",
        "narrative_entry",
        "visual_focus",
        "ending_tendency",
    }
)
URI_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s]+$")
USER_VISIBLE_SURFACE_FIELDS = frozenset(
    {"title", "body", "spoken_lines", "CTA", "execution_payload", "surface_units"}
)
PREPARE_CASE_INPUT_FIELDS = frozenset(
    {
        "principal_id",
        "content_account_id",
        "acting_maker_role_id",
        "confirmed_by_role_id",
        "confirmed_by_role_ids",
        "confirmation_scope",
        "subject_confirmation_ref",
        "trusted_scope_match",
        "trusted_scope",
        "requirement_status",
        "active_plan_count_for_key",
        "material_state",
        "authorization_state",
        "missing_required",
        "evaluation_time",
        "verified_precise_facts",
        "server_expression_profile_mode",
        "client_soft_preferences",
        "experimental_diagnostics",
        "required_candidate_count",
    }
)
VALIDATE_CASE_INPUT_FIELDS = frozenset(
    {
        "trusted_scope_match",
        "trusted_scope",
        "evaluation_time",
        "verified_precise_facts",
        "scoped_retrieval_fragments",
        "plan_consistent",
        "plan_allowed_fact_refs",
        "plan_allowed_material_refs",
        "actually_used_fact_refs",
        "actually_used_material_refs",
        "semantic_fact_review_status",
        "soft_evaluation_scores",
        "authorization_state",
        "internal_identifier_leak",
        "candidate_user_visible_surfaces",
    }
)
WORKFLOW_REQUIRED_ACTIVE_LINES = (
    "python3 ci/checkers/check_product_foundation.py",
    "python3 ci/checkers/check_product_foundation.py --selftest",
    '"ci/checkers/check_product_foundation.py" \\',
    '"ci/checkers/check_product_foundation.py --selftest" \\',
)
WORKFLOW_CHECKER_PIN_PATTERN = re.compile(
    r'^test "\$\(sha256sum ci/checkers/check_product_foundation\.py '
    r"\| cut -d ' ' -f 1\)\" = \"([0-9a-f]{64})\"$"
)
EXPECTED_CASE_IDS = frozenset(
    {
        *(f"PF-POS-{number:03d}" for number in range(1, 13)),
        *(f"PF-NEG-{number:03d}" for number in range(1, 26)),
    }
)


class CheckFailure(RuntimeError):
    """A stable fail-closed validation error."""


SELFTEST_FAILURE_CASES_RUN = 0


def require(condition: bool, code: str) -> None:
    if not condition:
        raise CheckFailure(code)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_digest(value: dict[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


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


def git_blob(root: Path, commit: str, relative_path: Path) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative_path.as_posix()}"],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(
        completed.returncode == 0,
        f"E_FROZEN_SNAPSHOT_BLOB:{relative_path}",
    )
    return completed.stdout


def snapshot_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for relative_path in SNAPSHOT_PATHS:
        if relative_path in AUTHORIZED_CURRENT_LIVE_PATHS:
            payload = git_blob(root, FROZEN_REVIEWED_COMMIT, relative_path)
        else:
            path = root / relative_path
            require(path.is_file(), f"E_SNAPSHOT_MISSING:{relative_path}")
            payload = path.read_bytes()
        digest.update(relative_path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


def validate_all_false(mapping: Any, code: str) -> None:
    require(isinstance(mapping, dict), f"{code}:NOT_OBJECT")
    require(READINESS_KEYS.issubset(mapping), f"{code}:MISSING_KEYS")
    for key in READINESS_KEYS:
        require(mapping[key] is False, f"{code}:{key}")


def workflow_active_run_lines(root: Path) -> tuple[str, ...]:
    workflow = root / WORKFLOW_PATH
    require(workflow.is_file(), "E_WORKFLOW_MISSING")
    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    require(isinstance(document, dict), "E_WORKFLOW_DOCUMENT")
    jobs = document.get("jobs")
    require(isinstance(jobs, dict), "E_WORKFLOW_JOBS")
    job = jobs.get("checker-compatibility")
    require(isinstance(job, dict), "E_WORKFLOW_CHECKER_JOB")
    steps = job.get("steps")
    require(isinstance(steps, list), "E_WORKFLOW_STEPS")
    return tuple(
        stripped
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("run"), str)
        for line in step["run"].splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#")
    )


def workflow_checker_steps(root: Path) -> list[dict[str, Any]]:
    workflow = root / WORKFLOW_PATH
    require(workflow.is_file(), "E_WORKFLOW_MISSING")
    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    require(isinstance(document, dict), "E_WORKFLOW_DOCUMENT")
    jobs = document.get("jobs")
    require(isinstance(jobs, dict), "E_WORKFLOW_JOBS")
    job = jobs.get("checker-compatibility")
    require(isinstance(job, dict), "E_WORKFLOW_CHECKER_JOB")
    steps = job.get("steps")
    require(isinstance(steps, list), "E_WORKFLOW_STEPS")
    require(all(isinstance(step, dict) for step in steps), "E_WORKFLOW_STEP_OBJECT")
    return steps


def normalized_run_lines(run: str) -> tuple[str, ...]:
    return tuple(line.rstrip() for line in run.splitlines() if line.strip())


def require_exact_workflow_step(
    steps: list[dict[str, Any]], name: str, expected_lines: tuple[str, ...], code: str
) -> None:
    matches = [step for step in steps if step.get("name") == name]
    require(len(matches) == 1, f"{code}:COUNT")
    step = matches[0]
    require(
        step.get("env") == {"PYTHONDONTWRITEBYTECODE": "1"},
        f"{code}:ENV",
    )
    run = step.get("run")
    require(isinstance(run, str), f"{code}:RUN")
    require(normalized_run_lines(run) == expected_lines, f"{code}:BODY")


def validate_workflow_registration(root: Path) -> None:
    active_lines = workflow_active_run_lines(root)
    for required_line in WORKFLOW_REQUIRED_ACTIVE_LINES:
        require(active_lines.count(required_line) == 1, "E_WORKFLOW_REGISTRATION")
    pin_digests = [
        match.group(1)
        for line in active_lines
        if (match := WORKFLOW_CHECKER_PIN_PATTERN.fullmatch(line))
    ]
    require(
        pin_digests == [sha256_file(root / CHECKER_PATH)],
        "E_WORKFLOW_CHECKER_DIGEST_PIN",
    )
    steps = workflow_checker_steps(root)
    require_exact_workflow_step(
        steps,
        SUCCESSOR_NORMAL_STEP_NAME,
        SUCCESSOR_NORMAL_RUN_LINES,
        "E_WORKFLOW_SUCCESSOR_NORMAL",
    )
    require_exact_workflow_step(
        steps,
        SUCCESSOR_OPTIMIZED_STEP_NAME,
        SUCCESSOR_OPTIMIZED_RUN_LINES,
        "E_WORKFLOW_SUCCESSOR_OPTIMIZED",
    )


def path_is_in_successor_root(path: str) -> bool:
    return any(
        path.startswith(f"{package_root.as_posix()}/")
        for _, package_root, _, _ in CHECKED_DOWNSTREAM_PACKAGES
    )


def validate_post_candidate_paths(paths: set[str]) -> None:
    fixed_paths = {
        RESULT_PATH.as_posix(),
        ARCH_REVIEW_PATH.as_posix(),
        TRUST_REVIEW_PATH.as_posix(),
        COORDINATOR_PATH.as_posix(),
        *(path.as_posix() for path in AUTHORIZED_CURRENT_LIVE_PATHS),
    }
    unauthorized = sorted(
        path
        for path in paths
        if path not in fixed_paths and not path_is_in_successor_root(path)
    )
    require(not unauthorized, f"E_REVIEW_POST_CANDIDATE_SCOPE:{unauthorized}")


def run_successor_checker(root: Path, checker: Path) -> None:
    reference_commit = REFERENCE_SAFE_SUCCESSOR_COMMITS.get(checker)
    execution_root = root
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if reference_commit is not None and root.resolve() == ROOT.resolve():
        package_root = next(
            package
            for _, package, candidate_checker, _ in CHECKED_DOWNSTREAM_PACKAGES
            if candidate_checker == checker
        )
        validate_reference_safe_successor_bytes(root, package_root, reference_commit)
        temporary = tempfile.TemporaryDirectory(prefix="reference-safe-successor-")
        execution_root = Path(temporary.name) / "snapshot"
        completed = subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "--detach",
                execution_root.as_posix(),
                reference_commit,
            ],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        require(
            completed.returncode == 0,
            f"E_SUCCESSOR_REFERENCE_WORKTREE:{checker}:{completed.returncode}",
        )
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    invocations = (
        ([sys.executable, checker.as_posix()], 0, "NORMAL"),
        ([sys.executable, checker.as_posix(), "--selftest"], 0, "SELFTEST"),
        ([sys.executable, "-O", checker.as_posix()], 2, "OPTIMIZED"),
        (
            [sys.executable, "-O", checker.as_posix(), "--selftest"],
            2,
            "OPTIMIZED_SELFTEST",
        ),
    )
    try:
        for command, expected_code, mode in invocations:
            completed = subprocess.run(
                command,
                cwd=execution_root,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=environment,
            )
            require(
                completed.returncode == expected_code,
                f"E_SUCCESSOR_CHECKER_{mode}:{checker}:{completed.returncode}",
            )
    finally:
        if temporary is not None:
            subprocess.run(
                ["git", "worktree", "remove", "--force", execution_root.as_posix()],
                cwd=ROOT,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            temporary.cleanup()


def git_tree_paths(commit: str, package_root: Path) -> set[Path]:
    completed = subprocess.run(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            commit,
            package_root.as_posix(),
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require(completed.returncode == 0, f"E_SUCCESSOR_REFERENCE_TREE:{package_root}")
    return {Path(line) for line in completed.stdout.splitlines() if line.strip()}


def git_object_bytes(commit: str, path: Path) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, f"E_SUCCESSOR_REFERENCE_OBJECT:{path}")
    return completed.stdout


def validate_reference_safe_successor_bytes(
    root: Path, package_root: Path, reference_commit: str
) -> None:
    expected_paths = git_tree_paths(reference_commit, package_root)
    actual_paths = {
        path.relative_to(root)
        for path in (root / package_root).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    require(
        actual_paths == expected_paths,
        f"E_SUCCESSOR_REFERENCE_FILE_SET:{package_root}",
    )
    checker = next(
        candidate_checker
        for _, candidate_root, candidate_checker, _ in CHECKED_DOWNSTREAM_PACKAGES
        if candidate_root == package_root
    )
    mutable_paths = REFERENCE_SAFE_SUCCESSOR_MUTABLE_PATHS.get(checker, set())
    require(
        mutable_paths <= expected_paths, f"E_SUCCESSOR_MUTABLE_PATHS:{package_root}"
    )
    for relative in sorted(expected_paths - mutable_paths):
        require(
            (root / relative).read_bytes()
            == git_object_bytes(reference_commit, relative),
            f"E_SUCCESSOR_REFERENCE_BYTES:{relative}",
        )


def validate_successor_packages(root: Path) -> None:
    for _, package_root, checker, _ in CHECKED_DOWNSTREAM_PACKAGES:
        package_path = root / package_root
        if not package_path.exists():
            require(
                package_root not in MANDATORY_SUCCESSOR_ROOTS,
                f"E_SUCCESSOR_ROOT_MISSING:{package_root}",
            )
            continue
        require(package_path.is_dir(), f"E_SUCCESSOR_ROOT_NOT_DIRECTORY:{package_root}")
        require((root / checker).is_file(), f"E_SUCCESSOR_CHECKER_MISSING:{checker}")
        run_successor_checker(root, checker)


def validate_foundation_files(root: Path, review_state: str) -> None:
    actual = {
        path.relative_to(root / FOUNDATION_ROOT)
        for path in (root / FOUNDATION_ROOT).rglob("*")
        if path.is_file()
    }
    expected = set(BASE_FOUNDATION_FILES)
    if review_state in {"PENDING_ROOT_MERGE_APPROVAL", "PASS_TO_MERGE"}:
        expected.update(REVIEW_FILES - {COORDINATOR_PATH.relative_to(FOUNDATION_ROOT)})
    if review_state == "PASS_TO_MERGE":
        expected.add(COORDINATOR_PATH.relative_to(FOUNDATION_ROOT))
    require(
        actual == expected,
        f"E_FOUNDATION_FILE_SET:{sorted(map(str, actual ^ expected))}",
    )


def validate_expression_baseline(root: Path, contract: dict[str, Any]) -> None:
    baseline = contract.get("expression_v1_baseline")
    require(isinstance(baseline, dict), "E_EXPRESSION_BASELINE")
    require(
        baseline.get("consumption_mode") == "OPTIONAL_OFFLINE_REFERENCE",
        "E_EXPRESSION_REFERENCE_MODE",
    )
    require(
        baseline.get("normal_runtime_dependency") is False
        and baseline.get("normal_request_may_omit_all_asset_refs") is True
        and baseline.get("missing_asset_refs_block_prepare") is False,
        "E_EXPRESSION_RUNTIME_OPTIONALITY",
    )
    require(
        baseline.get("unknown_experiment_refs") == "DIAGNOSTIC_WARNING_ONLY"
        and set(baseline.get("permitted_uses", []))
        == {
            "OFFLINE_RESEARCH",
            "REGRESSION_EVALUATION",
            "DIAGNOSTIC",
            "EXPLICIT_EXPERIMENT",
        },
        "E_EXPRESSION_OFFLINE_USE_POLICY",
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


def validate_contract_data(
    root: Path, contract: dict[str, Any], identity: dict[str, Any]
) -> None:
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
    require(
        tuple(trusted.get("required_dimensions", [])) == TRUSTED_SCOPE_DIMENSIONS,
        "E_SCOPE_DIMENSIONS",
    )
    require(
        tuple(trusted.get("request_projection_fields", [])) == REQUEST_SCOPE_FIELDS,
        "E_SCOPE_REQUEST_PROJECTION",
    )
    require(trusted.get("cross_tenant_access") == "FORBIDDEN", "E_CROSS_TENANT_POLICY")
    require(
        trusted.get("cross_organization_access")
        == "FORBIDDEN_UNLESS_EXPLICITLY_GRANTED",
        "E_CROSS_ORGANIZATION_POLICY",
    )
    require(
        trusted.get("cross_store_access") == "FORBIDDEN_UNLESS_EXPLICITLY_GRANTED",
        "E_CROSS_STORE_POLICY",
    )
    require(
        trusted.get("cross_content_account_access")
        == "FORBIDDEN_UNLESS_EXPLICITLY_GRANTED",
        "E_CROSS_ACCOUNT_POLICY",
    )
    require(
        trusted.get("server_confirmed_acting_role_required") is True,
        "E_ACTING_ROLE_POLICY",
    )
    require(
        trusted.get("principal_account_role_grant_required") is True,
        "E_PRINCIPAL_ROLE_GRANT_POLICY",
    )
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
    require(
        tuple(narrative.get("required_metadata", [])) == NARRATIVE_FRAGMENT_METADATA,
        "E_NARRATIVE_FRAGMENT_METADATA",
    )
    require(
        narrative.get("source_scope_must_be_registered") is True
        and narrative.get("target_scope_must_match_authorization_grant") is True
        and narrative.get("expired_revoked_or_ungranted_fragment_is_usable") is False,
        "E_NARRATIVE_SCOPE_POLICY",
    )
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
        tuple(precise.get("required_metadata", [])) == PRECISE_FACT_METADATA,
        "E_PRECISE_FACT_METADATA",
    )
    require(
        precise.get("source_scope_must_be_registered") is True
        and precise.get("target_scope_must_match_authorization_grant") is True
        and precise.get("cross_scope_requires_explicit_authorization") is True,
        "E_PRECISE_SCOPE_POLICY",
    )
    require(
        precise.get("authorization_must_cover_fact_and_disclosure") is True,
        "E_PRECISE_AUTHORIZATION_POLICY",
    )
    require(
        precise.get("expired_or_revoked_fact_is_usable") is False,
        "E_PRECISE_EXPIRY_POLICY",
    )
    require(
        precise.get("precedence_over_narrative_retrieval") is True,
        "E_PRECISE_PRECEDENCE",
    )
    require(
        set(precise.get("fact_kinds", [])) == ALLOWED_FACT_KINDS,
        "E_PRECISE_FACT_KINDS",
    )
    require(
        fact_contract.get("expression_asset_may_be_fact_or_authorization") is False,
        "E_EXPRESSION_AS_FACT_POLICY",
    )
    require(
        {
            "expression_component",
            "control_rule",
            "structural_path",
            "brand_expression_profile",
            "high_level_mode",
            "approved_example",
            "client_soft_preference",
            "user_preference_without_confirmation",
            "model_inference",
        }
        == set(fact_contract.get("non_fact_inputs", []))
        and fact_contract.get("expression_guidance_may_be_fact_authorization_or_scope")
        is False,
        "E_EXPRESSION_GUIDANCE_AS_AUTHORITY_POLICY",
    )

    expression = contract.get("light_expression_contract")
    require(isinstance(expression, dict), "E_LIGHT_EXPRESSION_CONTRACT")
    profile = expression.get("brand_expression_profile")
    require(isinstance(profile, dict), "E_BRAND_EXPRESSION_PROFILE")
    require(
        profile.get("resolution_authority") == "SERVER_TRUSTED_UPSTREAM"
        and profile.get("client_may_supply_formal_profile") is False
        and profile.get("client_soft_preferences_may_override_hard_prohibitions")
        is False
        and set(profile.get("allowed_client_soft_preference_fields", []))
        == CLIENT_SOFT_PREFERENCE_FIELDS
        and profile.get("profile_may_grant_fact_authorization_or_scope") is False
        and profile.get("cross_tenant_profile_borrowing_allowed") is False,
        "E_EXPRESSION_PROFILE_BOUNDARY",
    )
    neutral_profile = profile.get("neutral_default_profile")
    require(isinstance(neutral_profile, dict), "E_NEUTRAL_EXPRESSION_PROFILE")
    require(
        neutral_profile.get("profile_ref") == NEUTRAL_EXPRESSION_PROFILE_REF
        and neutral_profile.get("profile_version") == 1
        and neutral_profile.get("resolution_mode") == "NEUTRAL_DEFAULT"
        and neutral_profile.get("tenant_specific") is False
        and neutral_profile.get("approved_example_refs") == [],
        "E_NEUTRAL_EXPRESSION_PROFILE_FIELDS",
    )
    modes = expression.get("high_level_modes")
    require(
        isinstance(modes, list)
        and {item.get("mode_ref") for item in modes if isinstance(item, dict)}
        == HIGH_LEVEL_MODE_REFS
        and all(is_nonempty_string(item.get("user_label")) for item in modes),
        "E_HIGH_LEVEL_MODES",
    )
    require(
        expression.get("mode_selection_required") is False
        and expression.get("mode_is_script_template") is False
        and expression.get("mode_may_grant_fact_authorization_or_scope") is False
        and expression.get("approved_example_may_grant_fact_authorization_or_scope")
        is False,
        "E_EXPRESSION_GUIDANCE_AUTHORITY",
    )
    candidate_policy = expression.get("candidate_policy")
    require(isinstance(candidate_policy, dict), "E_CANDIDATE_POLICY")
    difference_dimensions = set(candidate_policy.get("difference_dimensions", []))
    require(
        candidate_policy.get("minimum_count") == 2
        and candidate_policy.get("maximum_count") == 3
        and candidate_policy.get("near_duplicate_rewording_counts_as_distinct") is False
        and len(difference_dimensions) >= 4,
        "E_CANDIDATE_POLICY_FIELDS",
    )
    require(
        set(expression.get("hard_check_categories", [])) == HARD_CHECK_CATEGORIES
        and set(expression.get("soft_evaluation_tasks", [])) == SOFT_EVALUATION_TASKS
        and expression.get("missing_real_evaluator_status")
        == "PENDING_EXTERNAL_EVALUATION"
        and expression.get("soft_score_may_be_fabricated") is False,
        "E_HARD_SOFT_EVALUATION_BOUNDARY",
    )
    diagnostics = expression.get("experimental_diagnostics")
    require(isinstance(diagnostics, dict), "E_EXPERIMENTAL_DIAGNOSTICS")
    require(
        diagnostics.get("normal_runtime_required") is False
        and set(diagnostics.get("allowed_reference_fields", []))
        == {
            "expression_baseline_ref",
            "component_refs",
            "control_rule_refs",
            "edge_refs",
            "structural_path_ref",
        }
        and diagnostics.get("unknown_reference_behavior") == "DIAGNOSTIC_WARNING_ONLY"
        and diagnostics.get("may_change_fact_authorization_scope_or_publishability")
        is False,
        "E_EXPERIMENTAL_DIAGNOSTIC_BOUNDARY",
    )

    plan = contract.get("light_content_plan_contract")
    require(isinstance(plan, dict), "E_PLAN_CONTRACT")
    require(plan.get("object_name") == "LightContentPlan", "E_PLAN_NAME")
    require(plan.get("authority") == "EXPRESSION_SERVICE_PREPARE", "E_PLAN_AUTHORITY")
    require(plan.get("is_independent_microservice") is False, "E_PLAN_MICROSERVICE")
    plan_required_fields = {
        "object_type",
        "plan_id",
        "plan_revision",
        "composition_plan_ref",
        "tenant_id",
        "organization_id",
        "content_account_id",
        "requirement_id",
        "requirement_version",
        "task_objective",
        "primary_audience",
        "output_requirements",
        "candidate_policy",
        "expression_guidance",
        "hard_check_policy",
        "soft_evaluation_tasks",
        "references",
    }
    require(
        set(plan.get("required_fields", [])) == plan_required_fields,
        "E_PLAN_REQUIRED_FIELDS",
    )
    require(plan.get("object_type") == "LIGHT_CONTENT_PLAN", "E_PLAN_TYPE")
    require(
        set(plan.get("composition_plan_ref_is_derived_from", []))
        == {"plan_id", "plan_revision"}
        and set(plan.get("unique_key_fields", []))
        == {
            "tenant_id",
            "content_account_id",
            "requirement_id",
            "requirement_version",
        }
        and plan.get("maximum_active_plans_per_key") == 1,
        "E_PLAN_UNIQUENESS",
    )
    require(
        set(plan.get("competing_plan_writers_forbidden", []))
        == {"DIFY", "RETRIEVAL_LAYER", "GENERATOR"},
        "E_COMPETING_PLAN_WRITERS",
    )
    required_plan_references = {
        "trusted_scope_ref",
        "confirmed_requirement_ref",
        "retrieval_fragment_refs",
        "precise_fact_refs",
        "brand_expression_profile_ref",
        "selected_internal_content_product_id",
    }
    require(
        set(plan.get("required_references", [])) == required_plan_references
        and set(plan.get("optional_references", []))
        == {
            "high_level_mode_refs",
            "approved_example_refs",
            "experimental_diagnostics",
        }
        and plan.get("atom_component_edge_and_path_refs_required") is False
        and plan.get("audience_body_allowed_in_plan") is False,
        "E_PLAN_REFERENCE_POLICY",
    )

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
        workflow.get("prepare_must_precede_candidate_authoring") is True
        and workflow.get("candidate_authoring_must_precede_validate") is True,
        "E_WORKFLOW_ORDER_GUARDS",
    )
    candidate = next(
        item for item in stages if item.get("stage") == "CANDIDATE_AUTHORING"
    )
    require(
        candidate.get("input") == "LIGHT_CONTENT_PLAN_REFERENCE"
        and candidate.get("may_add_facts") is False
        and candidate.get("may_create_competing_plan") is False,
        "E_CANDIDATE_AUTHORING_BOUNDARY",
    )

    delivery = contract.get("delivery_contract")
    require(isinstance(delivery, dict), "E_DELIVERY_CONTRACT")
    require(
        delivery.get("action_card_may_contain_publishable_candidate") is False
        and delivery.get("missing_input_may_be_filled_by_model") is False,
        "E_ACTION_CARD_SAFETY",
    )
    require(
        delivery.get("action_card_discriminator_field") == "object_type"
        and delivery.get("action_card_discriminator_value") == "ACTION_CARD"
        and delivery.get("action_card_type_field") == "action_type",
        "E_ACTION_CARD_DISCRIMINATOR",
    )
    require(
        {"object_type", "action_type", "decision_id"}.issubset(
            delivery.get("action_card_required_fields", [])
        ),
        "E_ACTION_CARD_TYPE_FIELDS",
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

    prepare = next(
        item for item in endpoints if item.get("path") == "/v1/content/prepare"
    )
    prepare_request = prepare.get("request_example")
    prepare_responses = prepare.get("response_examples")
    require(isinstance(prepare_request, dict), "E_PREPARE_REQUEST_EXAMPLE")
    require(isinstance(prepare_responses, dict), "E_PREPARE_RESPONSE_EXAMPLES")
    expected_prepare_fields = {
        "api_version",
        "request_id",
        "trusted_scope_ref",
        "trusted_scope",
        "acting_role_id",
        "confirmed_requirement",
        "confirmation_evidence",
        "scoped_retrieval_fragments",
        "verified_precise_facts",
        "server_expression_profile",
        "output_requirements",
        "evaluation_rules",
    }
    require(
        prepare.get("request_source") == "SERVER_TRUSTED_UPSTREAM_ENVELOPE"
        and set(prepare.get("trusted_upstream_only_fields", []))
        == {
            "trusted_scope_ref",
            "trusted_scope",
            "acting_role_id",
            "confirmation_evidence",
            "scoped_retrieval_fragments",
            "verified_precise_facts",
            "server_expression_profile",
        }
        and set(prepare.get("client_hint_fields", []))
        == {
            "requested_high_level_mode_refs",
            "approved_example_refs",
            "client_soft_preferences",
            "output_requirements",
        }
        and prepare.get("client_trust_or_verified_labels_are_authoritative") is False,
        "E_PREPARE_TRUST_BOUNDARY",
    )
    require(
        set(prepare.get("request_required_fields", [])) == expected_prepare_fields
        and expected_prepare_fields.issubset(prepare_request),
        "E_PREPARE_REQUEST_EXAMPLE_FIELDS",
    )
    require(
        set(prepare_request.get("trusted_scope", {})) == set(REQUEST_SCOPE_FIELDS),
        "E_PREPARE_TRUSTED_SCOPE_EXAMPLE",
    )
    trusted_scope_example = prepare_request["trusted_scope"]
    expected_scope_ref = (
        "scope://"
        f"{trusted_scope_example.get('tenant_id')}/"
        f"{trusted_scope_example.get('login_principal_id')}/"
        f"{trusted_scope_example.get('content_account_id')}"
    )
    require(
        prepare_request.get("trusted_scope_ref") == expected_scope_ref,
        "E_PREPARE_TRUSTED_SCOPE_REF",
    )
    server_profile = prepare_request.get("server_expression_profile")
    require(isinstance(server_profile, dict), "E_PREPARE_SERVER_PROFILE")
    require(
        server_profile.get("resolution_authority") == "SERVER_TRUSTED_UPSTREAM"
        and server_profile.get("requested_profile_ref") is None
        and server_profile.get("resolved_profile_ref") == NEUTRAL_EXPRESSION_PROFILE_REF
        and server_profile.get("resolution_mode") == "NEUTRAL_DEFAULT"
        and server_profile.get("tenant_id") == trusted_scope_example.get("tenant_id")
        and server_profile.get("content_account_id")
        == trusted_scope_example.get("content_account_id"),
        "E_PREPARE_SERVER_PROFILE_BOUNDARY",
    )
    require(
        set(prepare_request.get("requested_high_level_mode_refs", []))
        <= HIGH_LEVEL_MODE_REFS
        and isinstance(prepare_request.get("approved_example_refs"), list)
        and isinstance(prepare_request.get("client_soft_preferences"), dict),
        "E_PREPARE_EXPRESSION_GUIDANCE",
    )
    output_requirements = prepare_request.get("output_requirements")
    require(isinstance(output_requirements, dict), "E_PREPARE_OUTPUT_REQUIREMENTS")
    requested_candidate_count = output_requirements.get("required_candidate_count")
    require(
        isinstance(requested_candidate_count, int)
        and 2 <= requested_candidate_count <= 3
        and set(output_requirements.get("audience_surface_fields", []))
        <= USER_VISIBLE_SURFACE_FIELDS,
        "E_PREPARE_CANDIDATE_COUNT",
    )
    evaluation_rules = prepare_request.get("evaluation_rules")
    require(isinstance(evaluation_rules, dict), "E_PREPARE_EVALUATION_RULES")
    require(
        set(evaluation_rules.get("hard_check_categories", [])) == HARD_CHECK_CATEGORIES
        and set(evaluation_rules.get("soft_evaluation_tasks", []))
        == SOFT_EVALUATION_TASKS,
        "E_PREPARE_HARD_SOFT_RULES",
    )
    confirmation_example = prepare_request.get("confirmation_evidence")
    require(
        isinstance(confirmation_example, dict)
        and set(confirmation_example)
        == {
            "confirmed_by_principal_id",
            "confirmed_by_role_ids",
            "confirmation_scope",
            "authorization_refs",
            "subject_confirmation_ref",
        },
        "E_PREPARE_CONFIRMATION_EXAMPLE",
    )
    confirmed_role_ids = confirmation_example.get("confirmed_by_role_ids")
    authorization_refs = confirmation_example.get("authorization_refs")
    require(
        confirmation_example.get("confirmed_by_principal_id")
        == trusted_scope_example.get("login_principal_id")
        and isinstance(confirmed_role_ids, list)
        and confirmed_role_ids
        and account_role_is_authorized(
            identity,
            str(trusted_scope_example.get("login_principal_id")),
            str(trusted_scope_example.get("content_account_id")),
            [str(item) for item in confirmed_role_ids],
            "CONFIRM",
            str(confirmation_example.get("confirmation_scope")),
            confirmation_example.get("subject_confirmation_ref"),
        ),
        "E_PREPARE_CONFIRMATION_AUTHORITY",
    )
    require(
        isinstance(authorization_refs, list)
        and authorization_refs
        and all(
            authorization_grant_covers(
                identity,
                authorization_ref,
                trusted_scope_example.get("organization_id"),
                trusted_scope_example.get("store_id"),
                trusted_scope_example,
                "REQUIREMENT_CONFIRMATION_ONLY",
                FIXTURE_SERVER_EVALUATION_TIME,
                frozenset({"REQUIREMENT_CONFIRMATION"}),
            )
            for authorization_ref in authorization_refs
        ),
        "E_PREPARE_CONFIRMATION_GRANT",
    )
    example_facts = prepare_request.get("verified_precise_facts")
    require(
        isinstance(example_facts, list)
        and len(example_facts) == 1
        and set(example_facts[0]) == set(PRECISE_FACT_METADATA),
        "E_PREPARE_FACT_EXAMPLE",
    )
    example_fragments = prepare_request.get("scoped_retrieval_fragments")
    require(
        isinstance(example_fragments, list)
        and len(example_fragments) == 1
        and set(example_fragments[0]) == set(NARRATIVE_FRAGMENT_METADATA),
        "E_PREPARE_FRAGMENT_EXAMPLE",
    )
    require(
        narrative_fragment_rejection_code(
            example_fragments[0],
            trusted_scope_example,
            identity,
            FIXTURE_SERVER_EVALUATION_TIME,
        )
        is None,
        "E_PREPARE_FRAGMENT_SAFETY",
    )
    require(
        fact_rejection_code(
            example_facts[0],
            trusted_scope_example,
            identity,
            FIXTURE_SERVER_EVALUATION_TIME,
        )
        is None,
        "E_PREPARE_FACT_SAFETY",
    )
    plan_example = prepare_responses.get("light_content_plan")
    action_example = prepare_responses.get("action_card")
    require(isinstance(plan_example, dict), "E_PREPARE_PLAN_EXAMPLE")
    require(isinstance(action_example, dict), "E_PREPARE_ACTION_EXAMPLE")
    require(plan_required_fields.issubset(plan_example), "E_PREPARE_PLAN_FIELDS")
    require(
        plan_example.get("object_type") == "LIGHT_CONTENT_PLAN"
        and plan_example.get("composition_plan_ref")
        == f"plan://{plan_example.get('plan_id')}/revisions/{plan_example.get('plan_revision')}",
        "E_PREPARE_PLAN_REF",
    )
    plan_references = plan_example.get("references")
    require(isinstance(plan_references, dict), "E_PREPARE_PLAN_REFERENCES")
    require(
        set(plan_references) == required_plan_references
        and all(value not in (None, "", []) for value in plan_references.values()),
        "E_PREPARE_PLAN_REFERENCE_FIELDS",
    )
    for field in ("retrieval_fragment_refs", "precise_fact_refs"):
        values = plan_references.get(field)
        require(
            isinstance(values, list)
            and len(values) == len(set(values))
            and all(is_nonempty_string(value) for value in values),
            "E_PREPARE_PLAN_REFERENCE_LISTS",
        )
    forbidden_runtime_refs = {
        "expression_baseline_ref",
        "selected_component_refs",
        "selected_control_rule_refs",
        "selected_edge_refs",
        "selected_structural_path_ref",
    }
    require(
        not forbidden_runtime_refs.intersection(plan_references),
        "E_PREPARE_PLAN_ATOM_RUNTIME_DEPENDENCY",
    )
    plan_candidate_policy = plan_example.get("candidate_policy")
    require(isinstance(plan_candidate_policy, dict), "E_PLAN_CANDIDATE_POLICY")
    require(
        plan_candidate_policy.get("required_candidate_count")
        == requested_candidate_count
        and 2 <= requested_candidate_count <= 3
        and len(set(plan_candidate_policy.get("difference_dimensions", []))) >= 4
        and set(plan_candidate_policy.get("difference_dimensions", []))
        <= difference_dimensions
        and plan_candidate_policy.get("near_duplicate_rewording_counts_as_distinct")
        is False,
        "E_PLAN_CANDIDATE_POLICY_FIELDS",
    )
    guidance = plan_example.get("expression_guidance")
    require(isinstance(guidance, dict), "E_PLAN_EXPRESSION_GUIDANCE")
    require(
        guidance.get("brand_expression_profile_ref") == NEUTRAL_EXPRESSION_PROFILE_REF
        and set(guidance.get("high_level_mode_refs", [])) <= HIGH_LEVEL_MODE_REFS
        and isinstance(guidance.get("approved_example_refs"), list)
        and isinstance(guidance.get("client_soft_preferences"), dict)
        and guidance.get("may_grant_fact_authorization_or_scope") is False,
        "E_PLAN_EXPRESSION_GUIDANCE_BOUNDARY",
    )
    require(
        set(plan_example.get("hard_check_policy", [])) == HARD_CHECK_CATEGORIES,
        "E_PLAN_HARD_CHECK_POLICY",
    )
    plan_soft_tasks = plan_example.get("soft_evaluation_tasks")
    require(
        isinstance(plan_soft_tasks, list)
        and {item.get("task_id") for item in plan_soft_tasks} == SOFT_EVALUATION_TASKS
        and all(
            item.get("status") == "PENDING_EXTERNAL_EVALUATION"
            and item.get("score") is None
            for item in plan_soft_tasks
        ),
        "E_PLAN_SOFT_EVALUATION_TASKS",
    )
    confirmed_requirement = prepare_request.get("confirmed_requirement")
    require(isinstance(confirmed_requirement, dict), "E_PREPARE_REQUIREMENT")
    require(
        plan_example.get("tenant_id") == trusted_scope_example.get("tenant_id")
        and plan_example.get("organization_id")
        == trusted_scope_example.get("organization_id")
        and plan_example.get("content_account_id")
        == trusted_scope_example.get("content_account_id")
        and plan_example.get("requirement_id")
        == confirmed_requirement.get("requirement_id")
        and plan_example.get("requirement_version")
        == confirmed_requirement.get("requirement_version"),
        "E_PREPARE_PLAN_SCOPE_BINDING",
    )
    expected_requirement_ref = (
        f"requirement://{confirmed_requirement.get('requirement_id')}/versions/"
        f"{confirmed_requirement.get('requirement_version')}"
    )
    expected_fragment_refs = {
        item.get("fragment_id") for item in example_fragments if isinstance(item, dict)
    }
    expected_fact_refs = {
        item.get("fact_id") for item in example_facts if isinstance(item, dict)
    }
    require(
        plan_references.get("trusted_scope_ref") == expected_scope_ref
        and plan_references.get("confirmed_requirement_ref") == expected_requirement_ref
        and set(plan_references.get("retrieval_fragment_refs", []))
        == expected_fragment_refs
        and set(plan_references.get("precise_fact_refs", [])) == expected_fact_refs
        and plan_references.get("brand_expression_profile_ref")
        == NEUTRAL_EXPRESSION_PROFILE_REF,
        "E_PREPARE_PLAN_SOURCE_REFS",
    )
    require(
        action_example.get("object_type") == "ACTION_CARD"
        and action_example.get("action_type") in delivery.get("action_card_types", [])
        and set(delivery.get("action_card_required_fields", [])).issubset(
            action_example
        ),
        "E_PREPARE_ACTION_FIELDS",
    )

    validate = next(
        item for item in endpoints if item.get("path") == "/v1/content/validate"
    )
    validate_request = validate.get("request_example")
    validate_responses = validate.get("response_examples")
    require(isinstance(validate_request, dict), "E_VALIDATE_REQUEST_EXAMPLE")
    require(isinstance(validate_responses, dict), "E_VALIDATE_RESPONSE_EXAMPLES")
    expected_validate_fields = {
        "api_version",
        "request_id",
        "trusted_scope_ref",
        "trusted_scope",
        "composition_plan_ref",
        "candidate",
        "actually_used_fact_refs",
        "actually_used_material_refs",
    }
    require(
        set(validate.get("request_required_fields", [])) == expected_validate_fields
        and expected_validate_fields.issubset(validate_request),
        "E_VALIDATE_REQUEST_EXAMPLE_FIELDS",
    )
    require(
        set(validate_request.get("trusted_scope", {})) == set(REQUEST_SCOPE_FIELDS)
        and validate_request.get("trusted_scope") == trusted_scope_example
        and validate_request.get("trusted_scope_ref") == expected_scope_ref,
        "E_VALIDATE_TRUSTED_SCOPE_EXAMPLE",
    )
    require(
        validate_request.get("composition_plan_ref")
        == plan_example.get("composition_plan_ref")
        and set(validate_request.get("actually_used_fact_refs", []))
        == expected_fact_refs
        and set(validate_request.get("actually_used_material_refs", []))
        == expected_fragment_refs,
        "E_VALIDATE_SOURCE_REFS",
    )
    require(
        {
            response.get("decision")
            for response in validate_responses.values()
            if isinstance(response, dict)
        }
        == {"PASS", "REVISE", "BLOCK"},
        "E_VALIDATE_RESPONSE_DECISIONS",
    )
    response_required_fields = {
        "object_type",
        "decision",
        "decision_id",
        "composition_plan_ref",
        "hard_issues",
        "soft_evaluation_tasks",
        "semantic_fact_review_status",
        "actually_used_fact_refs",
        "actually_used_material_refs",
        "plain_language_reason",
    }
    require(
        set(validate.get("response_required_fields", [])) == response_required_fields
        and all(
            isinstance(response, dict) and response_required_fields.issubset(response)
            for response in validate_responses.values()
        ),
        "E_VALIDATE_RESPONSE_REQUIRED_FIELDS",
    )
    for response in validate_responses.values():
        require(
            isinstance(response, dict)
            and response_required_fields.issubset(response)
            and response.get("object_type") == "VALIDATION_DECISION"
            and is_nonempty_string(response.get("decision_id"))
            and response.get("composition_plan_ref")
            == plan_example.get("composition_plan_ref")
            and isinstance(response.get("hard_issues"), list)
            and isinstance(response.get("actually_used_fact_refs"), list)
            and isinstance(response.get("actually_used_material_refs"), list),
            "E_VALIDATE_RESPONSE_FIELDS",
        )
        response_soft_tasks = response.get("soft_evaluation_tasks")
        require(
            isinstance(response_soft_tasks, list)
            and response_soft_tasks
            and all(
                isinstance(item, dict)
                and item.get("task_id") in SOFT_EVALUATION_TASKS
                and item.get("status") == "PENDING_EXTERNAL_EVALUATION"
                and item.get("score") is None
                for item in response_soft_tasks
            ),
            "E_VALIDATE_SOFT_EVALUATION_TASKS",
        )
        require(
            response.get("semantic_fact_review_status")
            in {"PENDING_EXTERNAL_REVIEW", "NOT_REACHED"},
            "E_VALIDATE_SEMANTIC_REVIEW_STATUS",
        )
        require(
            isinstance(response.get("plain_language_reason"), str)
            and bool(response["plain_language_reason"].strip())
            and not has_internal_identifier(response["plain_language_reason"]),
            "E_VALIDATE_PLAIN_LANGUAGE_REASON",
        )
    require(
        all(
            response.get("actually_used_fact_refs")
            == validate_request.get("actually_used_fact_refs")
            and response.get("actually_used_material_refs")
            == validate_request.get("actually_used_material_refs")
            for response in validate_responses.values()
        ),
        "E_VALIDATE_RESPONSE_SOURCE_REFS",
    )
    pass_response = validate_responses.get("pass")
    require(
        isinstance(pass_response, dict)
        and pass_response.get("hard_issues") == []
        and pass_response.get("semantic_fact_review_status")
        == "PENDING_EXTERNAL_REVIEW"
        and {item.get("task_id") for item in pass_response["soft_evaluation_tasks"]}
        == SOFT_EVALUATION_TASKS,
        "E_VALIDATE_PASS_IS_NOT_SEMANTIC_PROOF",
    )
    require(
        set(validate.get("checks", [])) == HARD_CHECK_CATEGORIES | {"plan_consistency"}
        and validate.get("hard_checks_do_not_prove_candidate_semantics") is True
        and validate.get("semantic_fact_review_required_before_publish") is True
        and validate.get("evaluation_time_source") == "SERVER_CLOCK"
        and validate.get("client_supplied_evaluation_time_accepted") is False,
        "E_VALIDATE_BOUNDARY",
    )

    output_contract = contract.get("user_output_contract")
    require(isinstance(output_contract, dict), "E_USER_OUTPUT_CONTRACT")
    require(
        set(output_contract.get("hidden_internal_identifiers", []))
        == {
            "content_product_id",
            "component_id",
            "route_code",
            "raw_error_code",
            "internal_route_id",
        },
        "E_USER_OUTPUT_HIDDEN_IDS",
    )
    require(
        set(output_contract.get("prohibited_patterns", []))
        == {
            "CP[0-9]{2}",
            "(BNO|BRV|VGA|BCL|FC)-[0-9]{2}",
            "(G1V11|RCV2)-[A-Z0-9-]+",
            "(all_required_inputs_present|required_source_missing|required_fact_missing|required_authorization_missing)",
            "E_[A-Z0-9_]+",
        },
        "E_USER_OUTPUT_PATTERNS",
    )
    require(
        set(output_contract.get("hidden_internal_route_values", []))
        == INTERNAL_ROUTE_IDS,
        "E_USER_OUTPUT_ROUTE_IDS",
    )
    require(
        output_contract.get("candidate_surface_container")
        == "candidate_user_visible_surfaces"
        and set(output_contract.get("allowed_candidate_surface_fields", []))
        == USER_VISIBLE_SURFACE_FIELDS
        and output_contract.get("unknown_candidate_surface_field_behavior") == "BLOCK"
        and output_contract.get("all_concurrent_candidate_surfaces_scanned_together")
        is True,
        "E_USER_OUTPUT_SURFACE_CLOSURE",
    )

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
        "light_content_plan" in ownership["DIFY"].get("does_not_own", []),
        "E_DIFY_PLAN_OWNER",
    )
    require(
        "light_content_plan" in ownership["EXPRESSION_SERVICE"].get("owns", []),
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
    require(
        contract.get("light_content_plan_contract_owner")
        == "PACKAGE_2_LIGHT_EXPRESSION_SERVICE",
        "E_LIGHT_PLAN_PACKAGE_OWNER",
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
    authorization_grants = identity.get("authorization_grants")
    subject_confirmations = identity.get("subject_confirmation_records")
    require(isinstance(principals, list) and len(principals) == 1, "E_PRINCIPAL_COUNT")
    require(
        isinstance(organizations, list) and len(organizations) == 5,
        "E_ORGANIZATION_COUNT",
    )
    require(isinstance(stores, list) and len(stores) == 3, "E_STORE_COUNT")
    require(isinstance(roles, list) and roles, "E_WORK_ROLES")
    require(isinstance(accounts, list) and len(accounts) == 11, "E_ACCOUNT_COUNT")
    require(
        isinstance(authorization_grants, list) and len(authorization_grants) == 6,
        "E_AUTHORIZATION_GRANT_COUNT",
    )
    require(
        isinstance(subject_confirmations, list) and len(subject_confirmations) == 1,
        "E_SUBJECT_CONFIRMATION_COUNT",
    )
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
    role_organization = {
        item.get("role_id"): item.get("organization_id")
        for item in roles
        if isinstance(item, dict)
    }
    for organization in organizations:
        require(
            organization.get("tenant_id") == tenant.get("tenant_id"),
            "E_ORG_TENANT_REF",
        )
        parent_id = organization.get("parent_organization_id")
        authorizer_id = organization.get("authorized_by_organization_id")
        require(
            parent_id is None or parent_id in organization_ids,
            "E_ORG_PARENT_REF",
        )
        require(
            authorizer_id is None or authorizer_id in organization_ids,
            "E_ORG_AUTHORIZER_REF",
        )
        require(organization.get("simulation_only") is True, "E_ORG_SIMULATION")
        require(organization.get("publish_allowed") is False, "E_ORG_PUBLISH")
    store_organization = {
        item.get("store_id"): item.get("organization_id")
        for item in stores
        if isinstance(item, dict)
    }
    for store in stores:
        require(store.get("organization_id") in organization_ids, "E_STORE_ORG_REF")
        require(store.get("simulation_only") is True, "E_STORE_SIMULATION")
        require(store.get("publish_allowed") is False, "E_STORE_PUBLISH")
    for role in roles:
        require(role.get("organization_id") in organization_ids, "E_ROLE_ORG_REF")
        require(role.get("simulation_only") is True, "E_ROLE_SIMULATION")
        require(role.get("publish_allowed") is False, "E_ROLE_PUBLISH")

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
        require(
            store_id is None
            or store_organization.get(store_id) == account.get("organization_id"),
            f"E_ACCOUNT_STORE_ORGANIZATION:{account_id}",
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
            expected_mode = "ALL_OF" if len(confirmer_ids) > 1 else "ANY_OF"
            require(
                route.get("approval_mode") == expected_mode,
                f"E_CONFIRMATION_MODE:{account_id}:{route.get('scope')}",
            )
            expected_subject_confirmation = (
                account_id == "ACCOUNT-DIYU-CONTENT-LEAD"
                and route.get("scope") == "quoted_person_viewpoint"
            ) or (
                account_id == "ACCOUNT-DIYU-HQ-OFFICIAL"
                and route.get("scope") == "person_and_customer_authorization"
            )
            require(
                route.get("subject_confirmation_required")
                is expected_subject_confirmation,
                f"E_SUBJECT_CONFIRMATION_POLICY:{account_id}:{route.get('scope')}",
            )
            require(
                route.get("simulation_only") is True,
                f"E_CONFIRMATION_ROUTE_SIMULATION:{account_id}:{route.get('scope')}",
            )
            require(
                route.get("publish_allowed") is False,
                f"E_CONFIRMATION_ROUTE_PUBLISH:{account_id}:{route.get('scope')}",
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
            all(
                role_organization[role_id] == account.get("organization_id")
                for role_id in makers
            ),
            f"E_ACCOUNT_MAKER_ORGANIZATION:{account_id}",
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
        principal.get("tenant_id") == tenant.get("tenant_id"),
        "E_SIM_PRINCIPAL_TENANT",
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
    grants = principal.get("account_role_grants")
    require(isinstance(grants, list), "E_SIM_ACCOUNT_ROLE_GRANTS")
    by_grant = {
        item.get("account_id"): item for item in grants if isinstance(item, dict)
    }
    require(set(by_grant) == set(by_account), "E_SIM_ACCOUNT_ROLE_GRANT_IDS")
    for account_id, account in by_account.items():
        grant = by_grant[account_id]
        expected_confirmers = {
            role_id
            for route in account["confirmation_routes"]
            for role_id in route["confirmer_role_ids"]
        }
        require(
            set(grant.get("maker_role_ids", [])) == set(account["maker_role_ids"]),
            f"E_SIM_MAKER_GRANT:{account_id}",
        )
        require(
            set(grant.get("confirmer_role_ids", [])) == expected_confirmers,
            f"E_SIM_CONFIRMER_GRANT:{account_id}",
        )
        require(
            grant.get("simulation_only") is True,
            f"E_SIM_ROLE_GRANT_SIMULATION:{account_id}",
        )
        require(
            grant.get("publish_allowed") is False,
            f"E_SIM_ROLE_GRANT_PUBLISH:{account_id}",
        )

    authorization_ids: set[str] = set()
    for grant in authorization_grants:
        require(isinstance(grant, dict), "E_AUTHORIZATION_GRANT_OBJECT")
        authorization_id = grant.get("authorization_id")
        require(
            isinstance(authorization_id, str)
            and authorization_id.startswith("AUTH-SIM-")
            and authorization_id not in authorization_ids,
            "E_AUTHORIZATION_GRANT_ID",
        )
        authorization_ids.add(authorization_id)
        require(
            grant.get("tenant_id") == tenant.get("tenant_id")
            and grant.get("brand_id") == tenant.get("brand_id"),
            f"E_AUTHORIZATION_TENANT:{authorization_id}",
        )
        source_org = grant.get("source_organization_id")
        source_store = grant.get("source_store_id")
        require(
            source_org in organization_ids,
            f"E_AUTHORIZATION_SOURCE_ORG:{authorization_id}",
        )
        require(
            source_store is None or store_organization.get(source_store) == source_org,
            f"E_AUTHORIZATION_SOURCE_STORE:{authorization_id}",
        )
        permitted_organizations = grant.get("permitted_organization_ids")
        permitted_stores = grant.get("permitted_store_ids")
        permitted_accounts = grant.get("permitted_content_account_ids")
        require(
            isinstance(permitted_organizations, list)
            and permitted_organizations
            and set(permitted_organizations).issubset(organization_ids),
            f"E_AUTHORIZATION_TARGET_ORG:{authorization_id}",
        )
        require(
            isinstance(permitted_stores, list)
            and permitted_stores
            and set(permitted_stores).issubset({None, *store_ids}),
            f"E_AUTHORIZATION_TARGET_STORE:{authorization_id}",
        )
        require(
            isinstance(permitted_accounts, list)
            and permitted_accounts
            and set(permitted_accounts).issubset(by_account),
            f"E_AUTHORIZATION_TARGET_ACCOUNT:{authorization_id}",
        )
        for permitted_account_id in permitted_accounts:
            permitted_account = by_account[permitted_account_id]
            require(
                permitted_account.get("organization_id") in permitted_organizations
                and permitted_account.get("store_id") in permitted_stores,
                f"E_AUTHORIZATION_TARGET_SCOPE:{authorization_id}:{permitted_account_id}",
            )
        valid_from = parse_iso_datetime(grant.get("valid_from"))
        valid_until = parse_iso_datetime(grant.get("valid_until"))
        require(
            grant.get("status") == "GRANTED"
            and valid_from is not None
            and valid_until is not None
            and valid_from <= valid_until,
            f"E_AUTHORIZATION_STATE:{authorization_id}",
        )
        expected_disclosure_scope = (
            "REQUIREMENT_CONFIRMATION_ONLY"
            if grant.get("authorization_kind") == "REQUIREMENT_CONFIRMATION"
            else "CONTENT_ACCOUNT_ONLY"
        )
        require(
            grant.get("authorization_kind")
            in {
                "FACT_DISCLOSURE",
                "MATERIAL_AND_FACT_DISCLOSURE",
                "REQUIREMENT_CONFIRMATION",
            }
            and grant.get("disclosure_scope") == expected_disclosure_scope,
            f"E_AUTHORIZATION_KIND_SCOPE:{authorization_id}",
        )
        require(
            grant.get("simulation_only") is True
            and grant.get("publish_allowed") is False,
            f"E_AUTHORIZATION_SIMULATION:{authorization_id}",
        )

    subject_confirmation_ids: set[str] = set()
    for record in subject_confirmations:
        require(isinstance(record, dict), "E_SUBJECT_CONFIRMATION_OBJECT")
        confirmation_id = record.get("subject_confirmation_id")
        require(
            isinstance(confirmation_id, str)
            and confirmation_id.startswith("SUBJECT-CONFIRM-SIM-")
            and confirmation_id not in subject_confirmation_ids,
            "E_SUBJECT_CONFIRMATION_ID",
        )
        subject_confirmation_ids.add(confirmation_id)
        account_id = record.get("content_account_id")
        account = by_account.get(account_id)
        require(
            isinstance(account, dict),
            f"E_SUBJECT_CONFIRMATION_ACCOUNT:{confirmation_id}",
        )
        require(
            record.get("tenant_id") == tenant.get("tenant_id")
            and record.get("brand_id") == tenant.get("brand_id")
            and record.get("organization_id") == account.get("organization_id")
            and record.get("store_id") == account.get("store_id"),
            f"E_SUBJECT_CONFIRMATION_SCOPE:{confirmation_id}",
        )
        route = next(
            (
                item
                for item in account.get("confirmation_routes", [])
                if item.get("scope") == record.get("confirmation_scope")
            ),
            None,
        )
        require(
            isinstance(route, dict)
            and route.get("subject_confirmation_required") is True,
            f"E_SUBJECT_CONFIRMATION_ROUTE:{confirmation_id}",
        )
        require(
            record.get("subject_role_id") in role_ids,
            f"E_SUBJECT_CONFIRMATION_ROLE:{confirmation_id}",
        )
        confirmed_at = parse_iso_datetime(record.get("confirmed_at"))
        valid_until = parse_iso_datetime(record.get("valid_until"))
        require(
            record.get("status") == "ACTIVE"
            and confirmed_at is not None
            and valid_until is not None
            and confirmed_at <= valid_until,
            f"E_SUBJECT_CONFIRMATION_STATE:{confirmation_id}",
        )
        require(
            record.get("simulation_only") is True
            and record.get("publish_allowed") is False,
            f"E_SUBJECT_CONFIRMATION_SIMULATION:{confirmation_id}",
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
        invariants.get("authorization_grant_count") == 6,
        "E_IDENTITY_AUTHORIZATION_INVARIANT",
    )
    require(
        invariants.get("subject_confirmation_record_count") == 1,
        "E_IDENTITY_SUBJECT_CONFIRMATION_INVARIANT",
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


def iter_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [
            text
            for key, child in value.items()
            for text in [str(key), *iter_text(child)]
        ]
    if isinstance(value, list):
        return [text for child in value for text in iter_text(child)]
    return []


def iter_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for child in value.values() for text in iter_string_values(child)]
    if isinstance(value, list):
        return [text for child in value for text in iter_string_values(child)]
    return []


def has_internal_identifier(value: Any) -> bool:
    strings = iter_string_values(value)
    combined = "".join(strings)
    compact = re.sub(r"\s+", "", combined)
    return any(
        PROHIBITED_USER_PATTERN.search(text)
        for text in [*iter_text(value), combined, compact]
    )


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_uri_reference(value: Any) -> bool:
    return (
        is_nonempty_string(value) and URI_REFERENCE_PATTERN.fullmatch(value) is not None
    )


def subject_confirmation_is_valid(
    identity: dict[str, Any],
    subject_confirmation_ref: Any,
    account_id: str,
    confirmation_scope: str | None,
    evaluation_time: str,
) -> bool:
    record = next(
        (
            item
            for item in identity.get("subject_confirmation_records", [])
            if item.get("subject_confirmation_id") == subject_confirmation_ref
        ),
        None,
    )
    tenant = identity.get("tenant")
    evaluation_at = parse_iso_datetime(evaluation_time)
    confirmed_at = (
        parse_iso_datetime(record.get("confirmed_at"))
        if isinstance(record, dict)
        else None
    )
    valid_until = (
        parse_iso_datetime(record.get("valid_until"))
        if isinstance(record, dict)
        else None
    )
    return (
        isinstance(record, dict)
        and isinstance(tenant, dict)
        and record.get("tenant_id") == tenant.get("tenant_id")
        and record.get("brand_id") == tenant.get("brand_id")
        and record.get("content_account_id") == account_id
        and record.get("confirmation_scope") == confirmation_scope
        and record.get("status") == "ACTIVE"
        and record.get("simulation_only") is True
        and record.get("publish_allowed") is False
        and evaluation_at is not None
        and confirmed_at is not None
        and valid_until is not None
        and confirmed_at <= evaluation_at <= valid_until
    )


def account_role_is_authorized(
    identity: dict[str, Any],
    principal_id: str,
    account_id: str,
    role_ids: list[str],
    action: str,
    confirmation_scope: str | None = None,
    subject_confirmation_ref: str | None = None,
) -> bool:
    principal = next(
        (
            item
            for item in identity["login_principals"]
            if item.get("principal_id") == principal_id
        ),
        None,
    )
    account = next(
        (
            item
            for item in identity["content_accounts"]
            if item.get("account_id") == account_id
        ),
        None,
    )
    if not isinstance(principal, dict) or not isinstance(account, dict):
        return False
    grant = next(
        (
            item
            for item in principal.get("account_role_grants", [])
            if item.get("account_id") == account_id
        ),
        None,
    )
    if not isinstance(grant, dict):
        return False
    submitted_roles = set(role_ids)
    if not submitted_roles:
        return False
    if action == "MAKE":
        return len(submitted_roles) == 1 and submitted_roles.issubset(
            grant.get("maker_role_ids", [])
        )
    if action == "CONFIRM":
        route = next(
            (
                item
                for item in account.get("confirmation_routes", [])
                if item.get("scope") == confirmation_scope
            ),
            None,
        )
        if not isinstance(route, dict):
            return False
        allowed_roles = set(route.get("confirmer_role_ids", []))
        if not submitted_roles.issubset(allowed_roles) or not submitted_roles.issubset(
            grant.get("confirmer_role_ids", [])
        ):
            return False
        if route.get("approval_mode") == "ALL_OF":
            approval_satisfied = submitted_roles == allowed_roles
        else:
            approval_satisfied = bool(submitted_roles & allowed_roles)
        if route.get("subject_confirmation_required") is True:
            return approval_satisfied and subject_confirmation_is_valid(
                identity,
                subject_confirmation_ref,
                account_id,
                confirmation_scope,
                FIXTURE_SERVER_EVALUATION_TIME,
            )
        return approval_satisfied
    return False


def trusted_scope_matches_identity(
    identity: dict[str, Any], trusted_scope: Any
) -> bool:
    if not isinstance(trusted_scope, dict):
        return False
    if set(trusted_scope) != set(REQUEST_SCOPE_FIELDS):
        return False
    tenant = identity.get("tenant")
    if not isinstance(tenant, dict):
        return False
    principal = next(
        (
            item
            for item in identity.get("login_principals", [])
            if item.get("principal_id") == trusted_scope.get("login_principal_id")
        ),
        None,
    )
    account = next(
        (
            item
            for item in identity.get("content_accounts", [])
            if item.get("account_id") == trusted_scope.get("content_account_id")
        ),
        None,
    )
    if not isinstance(principal, dict) or not isinstance(account, dict):
        return False
    return (
        trusted_scope.get("tenant_id") == tenant.get("tenant_id")
        and trusted_scope.get("brand_id") == tenant.get("brand_id")
        and trusted_scope.get("organization_id") == account.get("organization_id")
        and trusted_scope.get("store_id") == account.get("store_id")
        and principal.get("tenant_id") == tenant.get("tenant_id")
        and account.get("account_id")
        in principal.get("allowed_content_account_ids", [])
    )


def parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def source_scope_is_registered(
    identity: dict[str, Any], organization_id: Any, store_id: Any
) -> bool:
    organizations = {
        item.get("organization_id")
        for item in identity.get("organizations", [])
        if isinstance(item, dict)
    }
    stores = {
        item.get("store_id"): item.get("organization_id")
        for item in identity.get("stores", [])
        if isinstance(item, dict)
    }
    return organization_id in organizations and (
        store_id is None or stores.get(store_id) == organization_id
    )


def authorization_grant_covers(
    identity: dict[str, Any],
    authorization_ref: Any,
    source_organization_id: Any,
    source_store_id: Any,
    trusted_scope: dict[str, Any],
    disclosure_scope: Any,
    evaluation_time: str,
    allowed_kinds: frozenset[str],
) -> bool:
    grant = next(
        (
            item
            for item in identity.get("authorization_grants", [])
            if item.get("authorization_id") == authorization_ref
        ),
        None,
    )
    if (
        not isinstance(grant, dict)
        or grant.get("authorization_kind") not in allowed_kinds
    ):
        return False
    evaluation_at = parse_iso_datetime(evaluation_time)
    valid_from = parse_iso_datetime(grant.get("valid_from"))
    valid_until = parse_iso_datetime(grant.get("valid_until"))
    return (
        evaluation_at is not None
        and valid_from is not None
        and valid_until is not None
        and valid_from <= evaluation_at <= valid_until
        and grant.get("status") == "GRANTED"
        and grant.get("tenant_id") == trusted_scope.get("tenant_id")
        and grant.get("brand_id") == trusted_scope.get("brand_id")
        and grant.get("source_organization_id") == source_organization_id
        and grant.get("source_store_id") == source_store_id
        and trusted_scope.get("organization_id")
        in grant.get("permitted_organization_ids", [])
        and trusted_scope.get("store_id") in grant.get("permitted_store_ids", [])
        and trusted_scope.get("content_account_id")
        in grant.get("permitted_content_account_ids", [])
        and grant.get("disclosure_scope") == disclosure_scope
    )


def narrative_fragment_rejection_code(
    fragment: dict[str, Any],
    trusted_scope: dict[str, Any],
    identity: dict[str, Any],
    evaluation_time: str,
) -> str | None:
    if set(fragment) != set(NARRATIVE_FRAGMENT_METADATA):
        return "MISSING_OR_UNKNOWN_METADATA"
    if (
        not is_nonempty_string(fragment.get("fragment_id"))
        or not is_uri_reference(fragment.get("source_ref"))
        or not is_nonempty_string(fragment.get("authorization_ref"))
        or not all(
            isinstance(fragment.get(field), list) and bool(fragment.get(field))
            for field in (
                "applicable_organization_ids",
                "applicable_store_ids",
                "applicable_content_account_ids",
            )
        )
    ):
        return "MISSING_OR_UNKNOWN_METADATA"
    if fragment.get("tenant_id") != trusted_scope.get("tenant_id") or fragment.get(
        "brand_id"
    ) != trusted_scope.get("brand_id"):
        return "TENANT_MISMATCH"
    if trusted_scope.get("organization_id") not in fragment.get(
        "applicable_organization_ids", []
    ) or trusted_scope.get("store_id") not in fragment.get("applicable_store_ids", []):
        return "STORE_SCOPE_MISMATCH"
    if trusted_scope.get("content_account_id") not in fragment.get(
        "applicable_content_account_ids", []
    ):
        return "ACCOUNT_SCOPE_MISMATCH"
    if not source_scope_is_registered(
        identity,
        fragment.get("source_organization_id"),
        fragment.get("source_store_id"),
    ):
        return "SOURCE_SCOPE_UNKNOWN"
    evaluation_at = parse_iso_datetime(evaluation_time)
    observed_at = parse_iso_datetime(fragment.get("observed_at"))
    valid_until = parse_iso_datetime(fragment.get("valid_until"))
    if fragment.get("status") == "REVOKED":
        return "REVOKED"
    if (
        fragment.get("status") != "ACTIVE"
        or evaluation_at is None
        or observed_at is None
        or valid_until is None
        or observed_at > evaluation_at
        or valid_until < evaluation_at
    ):
        return "EXPIRED_OR_INVALID"
    if (
        fragment.get("authorization_state") != "GRANTED"
        or fragment.get("disclosure_scope") != "CONTENT_ACCOUNT_ONLY"
        or not authorization_grant_covers(
            identity,
            fragment.get("authorization_ref"),
            fragment.get("source_organization_id"),
            fragment.get("source_store_id"),
            trusted_scope,
            fragment.get("disclosure_scope"),
            evaluation_time,
            frozenset({"MATERIAL_AND_FACT_DISCLOSURE"}),
        )
    ):
        return "AUTHORIZATION"
    return None


def fact_rejection_code(
    fact: dict[str, Any],
    trusted_scope: dict[str, Any],
    identity: dict[str, Any],
    evaluation_time: str,
) -> str | None:
    if set(fact) != set(PRECISE_FACT_METADATA):
        return "MISSING_OR_UNKNOWN_METADATA"
    if (
        not is_nonempty_string(fact.get("fact_id"))
        or not is_uri_reference(fact.get("source_ref"))
        or not is_nonempty_string(fact.get("authorization_ref"))
        or fact.get("value") in (None, "")
        or not isinstance(fact.get("applicable_content_account_ids"), list)
        or not fact.get("applicable_content_account_ids")
    ):
        return "MISSING_OR_UNKNOWN_METADATA"
    if (
        fact.get("tenant_id") != trusted_scope.get("tenant_id")
        or fact.get("brand_id") != trusted_scope.get("brand_id")
        or trusted_scope.get("content_account_id")
        not in fact.get("applicable_content_account_ids", [])
    ):
        return "SCOPE_MISMATCH"
    if not source_scope_is_registered(
        identity, fact.get("organization_id"), fact.get("store_id")
    ):
        return "SOURCE_SCOPE_UNKNOWN"
    evaluation_at = parse_iso_datetime(evaluation_time)
    effective_at = parse_iso_datetime(fact.get("effective_at"))
    valid_until = parse_iso_datetime(fact.get("valid_until"))
    if (
        fact.get("status") != "ACTIVE"
        or fact.get("fact_kind") not in ALLOWED_FACT_KINDS
        or fact.get("disclosure_scope") != "CONTENT_ACCOUNT_ONLY"
        or evaluation_at is None
        or effective_at is None
        or valid_until is None
        or effective_at > evaluation_at
        or valid_until < evaluation_at
        or not authorization_grant_covers(
            identity,
            fact.get("authorization_ref"),
            fact.get("organization_id"),
            fact.get("store_id"),
            trusted_scope,
            fact.get("disclosure_scope"),
            evaluation_time,
            frozenset({"FACT_DISCLOSURE", "MATERIAL_AND_FACT_DISCLOSURE"}),
        )
    ):
        return "AUTHORIZATION_OR_VALIDITY"
    return None


def evaluate_case(
    case: dict[str, Any],
    identity: dict[str, Any] | None = None,
    *,
    trusted_upstream: bool = False,
) -> dict[str, Any]:
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
        dimensions = (
            "tenant",
            "brand",
            "organization",
            "store",
            "principal",
            "account",
        )
        if any(
            f"trusted_{name}_id" not in data or f"requested_{name}_id" not in data
            for name in dimensions
        ):
            return {"decision": "REJECT_SCOPE_OVERRIDE"}
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
        if not trusted_upstream:
            return {"decision": "REJECT_UNTRUSTED_UPSTREAM"}
        trusted_scope = data.get("trusted_scope")
        fragment = data.get("retrieval_fragment")
        if (
            identity is None
            or not trusted_scope_matches_identity(identity, trusted_scope)
            or not isinstance(trusted_scope, dict)
            or not isinstance(fragment, dict)
        ):
            return {"decision": "REJECT_CROSS_TENANT_MATERIAL"}
        rejection = narrative_fragment_rejection_code(
            fragment,
            trusted_scope,
            identity,
            FIXTURE_SERVER_EVALUATION_TIME,
        )
        if rejection in {"TENANT_MISMATCH", "SOURCE_SCOPE_UNKNOWN"}:
            return {"decision": "REJECT_CROSS_TENANT_MATERIAL"}
        if rejection == "STORE_SCOPE_MISMATCH":
            return {"decision": "REJECT_CROSS_STORE_MATERIAL"}
        if rejection == "ACCOUNT_SCOPE_MISMATCH":
            return {"decision": "REJECT_CROSS_ACCOUNT_MATERIAL"}
        if rejection == "EXPIRED_OR_INVALID":
            return {"decision": "REJECT_EXPIRED_MATERIAL"}
        if rejection == "REVOKED":
            return {"decision": "REJECT_REVOKED_MATERIAL"}
        if rejection is not None:
            return {"decision": "REJECT_UNAUTHORIZED_MATERIAL"}
        return {"decision": "ALLOW_SCOPED_MATERIAL"}
    if operation == "fact_precedence":
        if data.get("attempt_narrative_override"):
            return {"decision": "REJECT_FACT_PRECEDENCE_OVERRIDE"}
        return {"decision": "USE_PRECISE_FACT"}
    if operation == "prepare":
        if not trusted_upstream:
            return {
                "decision": "REJECT_UNTRUSTED_UPSTREAM",
                "light_plan_created": False,
            }
        if not set(data).issubset(PREPARE_CASE_INPUT_FIELDS):
            return {
                "decision": "REJECT_UNTRUSTED_UPSTREAM_FIELD",
                "light_plan_created": False,
            }
        client_soft_preferences = data.get("client_soft_preferences", {})
        if not isinstance(client_soft_preferences, dict) or not set(
            client_soft_preferences
        ).issubset(CLIENT_SOFT_PREFERENCE_FIELDS):
            return {
                "decision": "REJECT_HARD_PROHIBITION_OVERRIDE",
                "light_plan_created": False,
            }
        profile_mode = data.get("server_expression_profile_mode", "NEUTRAL_DEFAULT")
        if profile_mode not in {"NEUTRAL_DEFAULT", "SERVER_RESOLVED"}:
            return {
                "decision": "REJECT_UNTRUSTED_EXPRESSION_PROFILE",
                "light_plan_created": False,
            }
        candidate_count = data.get("required_candidate_count", 2)
        if not isinstance(candidate_count, int) or not 2 <= candidate_count <= 3:
            return {
                "decision": "REJECT_CANDIDATE_COUNT",
                "light_plan_created": False,
            }
        trusted_scope = data.get("trusted_scope")
        if (
            data.get("trusted_scope_match") is not True
            or identity is None
            or not trusted_scope_matches_identity(identity, trusted_scope)
            or data.get("principal_id") != trusted_scope.get("login_principal_id")
            or data.get("content_account_id") != trusted_scope.get("content_account_id")
        ):
            return {
                "decision": "REJECT_SCOPE_OVERRIDE",
                "light_plan_created": False,
            }
        if identity is None or not account_role_is_authorized(
            identity,
            str(data.get("principal_id")),
            str(data.get("content_account_id")),
            [str(data.get("acting_maker_role_id"))],
            "MAKE",
        ):
            return {
                "decision": "REJECT_UNAUTHORIZED_ACCOUNT_ROLE",
                "light_plan_created": False,
            }
        confirmed_role_ids = data.get("confirmed_by_role_ids")
        if not isinstance(confirmed_role_ids, list):
            confirmed_role_ids = [str(data.get("confirmed_by_role_id"))]
        if not account_role_is_authorized(
            identity,
            str(data.get("principal_id")),
            str(data.get("content_account_id")),
            [str(item) for item in confirmed_role_ids],
            "CONFIRM",
            str(data.get("confirmation_scope")),
            data.get("subject_confirmation_ref"),
        ):
            return {
                "decision": "REJECT_UNAUTHORIZED_CONFIRMATION_ROLE",
                "light_plan_created": False,
            }
        if data.get("requirement_status") != "CONFIRMED":
            return {
                "decision": "REJECT_UNCONFIRMED_REQUIREMENT",
                "light_plan_created": False,
            }
        if data.get("active_plan_count_for_key") != 0:
            return {
                "decision": "REJECT_DUPLICATE_LIGHT_PLAN",
                "light_plan_created": False,
            }
        if (
            data.get("material_state") != "ACTIVE"
            or data.get("authorization_state") != "GRANTED"
        ):
            return {
                "decision": "ACTION_CARD_REQUEST_AUTHORIZATION",
                "light_plan_created": False,
            }
        facts = data.get("verified_precise_facts")
        if not isinstance(trusted_scope, dict) or not isinstance(facts, list):
            return {
                "decision": "ACTION_CARD_COLLECT_FACT",
                "light_plan_created": False,
            }
        if not facts and not data.get("missing_required"):
            return {
                "decision": "ACTION_CARD_COLLECT_FACT",
                "light_plan_created": False,
            }
        if any(not isinstance(fact, dict) for fact in facts):
            return {
                "decision": "ACTION_CARD_COLLECT_FACT",
                "light_plan_created": False,
            }
        fact_rejections = [
            fact_rejection_code(
                fact,
                trusted_scope,
                identity,
                FIXTURE_SERVER_EVALUATION_TIME,
            )
            for fact in facts
        ]
        if "SCOPE_MISMATCH" in fact_rejections:
            return {
                "decision": "REJECT_SCOPE_OVERRIDE",
                "light_plan_created": False,
            }
        if any(fact_rejections):
            return {
                "decision": "ACTION_CARD_REQUEST_AUTHORIZATION",
                "light_plan_created": False,
            }
        if data.get("missing_required"):
            missing = data["missing_required"]
            if any(str(item).startswith("material:") for item in missing):
                return {
                    "decision": "ACTION_CARD_COLLECT_MATERIAL",
                    "light_plan_created": False,
                }
            return {
                "decision": "ACTION_CARD_COLLECT_FACT",
                "light_plan_created": False,
            }
        return {"decision": "PREPARE_PLAN", "light_plan_created": True}
    if operation == "validate":
        if not trusted_upstream:
            return {"decision": "REJECT_UNTRUSTED_UPSTREAM"}
        if set(data) != VALIDATE_CASE_INPUT_FIELDS:
            return {"decision": "VALIDATE_BLOCK"}
        visible_payload = data.get("candidate_user_visible_surfaces")
        if (
            not isinstance(visible_payload, dict)
            or not visible_payload
            or not set(visible_payload).issubset(USER_VISIBLE_SURFACE_FIELDS)
        ):
            return {"decision": "VALIDATE_BLOCK"}
        if data.get("internal_identifier_leak") or has_internal_identifier(
            visible_payload
        ):
            return {"decision": "REJECT_INTERNAL_IDENTIFIER_LEAK"}
        trusted_scope = data.get("trusted_scope")
        if (
            not data.get("trusted_scope_match")
            or identity is None
            or not trusted_scope_matches_identity(identity, trusted_scope)
        ):
            return {"decision": "REJECT_SCOPE_OVERRIDE"}
        facts = data.get("verified_precise_facts")
        fragments = data.get("scoped_retrieval_fragments")
        if (
            not isinstance(trusted_scope, dict)
            or not isinstance(facts, list)
            or not isinstance(fragments, list)
        ):
            return {"decision": "VALIDATE_BLOCK"}
        if any(not isinstance(fact, dict) for fact in facts) or any(
            not isinstance(fragment, dict) for fragment in fragments
        ):
            return {"decision": "VALIDATE_BLOCK"}
        evaluation_time = data.get("evaluation_time")
        if not is_nonempty_string(evaluation_time):
            return {"decision": "VALIDATE_BLOCK"}
        fact_rejections = [
            fact_rejection_code(
                fact,
                trusted_scope,
                identity,
                evaluation_time,
            )
            for fact in facts
        ]
        if "SCOPE_MISMATCH" in fact_rejections:
            return {"decision": "REJECT_SCOPE_OVERRIDE"}
        if any(fact_rejections):
            return {"decision": "VALIDATE_BLOCK"}
        fragment_rejections = [
            narrative_fragment_rejection_code(
                fragment,
                trusted_scope,
                identity,
                evaluation_time,
            )
            for fragment in fragments
        ]
        if any(
            rejection
            in {
                "TENANT_MISMATCH",
                "SOURCE_SCOPE_UNKNOWN",
                "STORE_SCOPE_MISMATCH",
                "ACCOUNT_SCOPE_MISMATCH",
            }
            for rejection in fragment_rejections
        ):
            return {"decision": "REJECT_SCOPE_OVERRIDE"}
        if any(fragment_rejections):
            return {"decision": "VALIDATE_BLOCK"}
        reference_lists = (
            data.get("plan_allowed_fact_refs"),
            data.get("plan_allowed_material_refs"),
            data.get("actually_used_fact_refs"),
            data.get("actually_used_material_refs"),
        )
        if any(
            not isinstance(values, list)
            or any(not is_nonempty_string(value) for value in values)
            or len(values) != len(set(values))
            for values in reference_lists
        ):
            return {"decision": "VALIDATE_BLOCK"}
        plan_fact_refs, plan_material_refs, used_fact_refs, used_material_refs = (
            set(values) for values in reference_lists
        )
        available_fact_refs = {fact.get("fact_id") for fact in facts}
        available_material_refs = {
            fragment.get("fragment_id") for fragment in fragments
        }
        if (
            not plan_fact_refs.issubset(available_fact_refs)
            or not plan_material_refs.issubset(available_material_refs)
            or not used_fact_refs.issubset(plan_fact_refs)
            or not used_material_refs.issubset(plan_material_refs)
            or not used_fact_refs.issubset(available_fact_refs)
            or not used_material_refs.issubset(available_material_refs)
        ):
            return {"decision": "VALIDATE_BLOCK"}
        if not data.get("plan_consistent"):
            return {"decision": "VALIDATE_REVISE"}
        if data.get("authorization_state") != "GRANTED":
            return {"decision": "VALIDATE_BLOCK"}
        if data.get("soft_evaluation_scores") != {}:
            return {"decision": "VALIDATE_BLOCK"}
        if data.get("semantic_fact_review_status") != "PENDING_EXTERNAL_REVIEW":
            return {"decision": "VALIDATE_BLOCK"}
        return {"decision": "VALIDATE_PASS_PENDING_SEMANTIC_REVIEW"}
    if operation == "fact_input":
        if (
            data.get("input_kind") in EXPRESSION_GUIDANCE_INPUT_KINDS
            and data.get("claimed_as") in AUTHORITY_CLAIM_KINDS
        ):
            return {"decision": "REJECT_EXPRESSION_GUIDANCE_AS_AUTHORITY"}
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
        principal = None
        if identity is not None:
            principal = next(
                (
                    item
                    for item in identity["login_principals"]
                    if item.get("principal_id") == data.get("principal_id")
                ),
                None,
            )
        if (
            isinstance(principal, dict)
            and data.get("target_account_id")
            in principal.get("allowed_content_account_ids", [])
            and data.get("preserve_target_account_scope")
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


def validate_cases(cases: list[dict[str, Any]], identity: dict[str, Any]) -> None:
    require(len(cases) == len(EXPECTED_CASE_IDS), "E_CASE_COUNT")
    ids = [case.get("case_id") for case in cases]
    require(
        len(ids) == len(set(ids)) and set(ids) == EXPECTED_CASE_IDS,
        "E_CASE_IDS",
    )
    classes = Counter(case.get("case_class") for case in cases)
    require(
        classes["POSITIVE"] >= 6 and classes["NEGATIVE"] >= 13, "E_CASE_DISTRIBUTION"
    )
    decisions: set[str] = set()
    for case in cases:
        expected = case.get("expected")
        require(isinstance(expected, dict), f"E_CASE_EXPECTED:{case.get('case_id')}")
        # The fixture harness supplies trust; no field inside a case can grant it.
        actual = evaluate_case(case, identity, trusted_upstream=True)
        require(
            actual.get("decision") == expected.get("decision"),
            f"E_CASE_DECISION:{case.get('case_id')}",
        )
        for key in ("plan_created", "brand_fact_written", "light_plan_created"):
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
        "REJECT_EXPRESSION_GUIDANCE_AS_AUTHORITY",
        "REJECT_DUPLICATE_LIGHT_PLAN",
        "REJECT_SIMULATION_PUBLISH",
        "REJECT_INTERNAL_IDENTIFIER_LEAK",
        "REJECT_BASELINE_TAMPER",
        "REJECT_UNAUTHORIZED_PATH",
        "REJECT_UNAUTHORIZED_ACCOUNT_ROLE",
        "REJECT_UNAUTHORIZED_CONFIRMATION_ROLE",
        "ACTION_CARD_COLLECT_MATERIAL",
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
            "asset_runtime_role": "OPTIONAL_OFFLINE_RESEARCH_REGRESSION_AND_EXPERIMENT",
            "normal_runtime_requires_asset_refs": False,
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
    expected_downstream = [
        {
            "package_id": package_id,
            "root": package_root.as_posix(),
            "owner": owner_id,
            "unlocked_when": (
                "PUBLIC_FOUNDATION_TREE_ON_MASTER_AND_REQUIRED_CHECKS_GREEN"
            ),
        }
        for package_id, package_root, _, owner_id in SUCCESSOR_PACKAGES
    ]
    require(downstream == expected_downstream, "E_MANIFEST_DOWNSTREAM_BINDING")
    require(
        manifest.get("readiness_transition_authorized") is False, "E_MANIFEST_READINESS"
    )
    require(
        manifest.get("shared_model_ownership", {}).get("light_content_plan_contract")
        == "PACKAGE_2_ONLY"
        and "second_light_content_plan"
        in manifest.get("forbidden_parallel_models", []),
        "E_MANIFEST_LIGHT_PLAN_OWNERSHIP",
    )


def validate_reviews(root: Path, result: dict[str, Any]) -> None:
    review_state = result.get("review_state")
    require(
        review_state
        in {
            "PENDING_INDEPENDENT_REVIEWS",
            "PENDING_ROOT_MERGE_APPROVAL",
            "PASS_TO_MERGE",
        },
        "E_REVIEW_STATE",
    )
    expected_candidate_state = {
        "PENDING_INDEPENDENT_REVIEWS": "COMPLETE_PENDING_INDEPENDENT_REVIEWS",
        "PENDING_ROOT_MERGE_APPROVAL": "COMPLETE_PENDING_ROOT_MERGE_APPROVAL",
        "PASS_TO_MERGE": "COMPLETE_APPROVED_FOR_MERGE",
    }
    require(
        result.get("candidate_state") == expected_candidate_state[review_state],
        "E_CANDIDATE_STATE",
    )
    validate_foundation_files(root, str(review_state))
    if review_state == "PENDING_INDEPENDENT_REVIEWS":
        require(result.get("reviewed_candidate_commit") is None, "E_PENDING_COMMIT")
        require(result.get("independent_reviews") == [], "E_PENDING_REVIEW_REFS")
        require(result.get("coordinator_decision") is None, "E_PENDING_COORDINATOR")
        return

    arch = load_yaml(root, ARCH_REVIEW_PATH, "independent_review")
    trust = load_yaml(root, TRUST_REVIEW_PATH, "independent_review")
    reports = [arch, trust]
    expected_ids = {"ARCHITECTURE_CONSUMABILITY_REVIEW", "TRUST_FACT_SAFETY_REVIEW"}
    require(
        {report.get("review_id") for report in reports} == expected_ids, "E_REVIEW_IDS"
    )
    reviewed_commit = result.get("reviewed_candidate_commit")
    digest = result.get("candidate_snapshot_digest")
    require(
        isinstance(reviewed_commit, str)
        and re.fullmatch(r"[0-9a-f]{40}", reviewed_commit) is not None,
        "E_REVIEWED_COMMIT_FORMAT",
    )
    if (root / ".git").exists():
        commit_exists = subprocess.run(
            ["git", "cat-file", "-e", f"{reviewed_commit}^{{commit}}"],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        require(commit_exists.returncode == 0, "E_REVIEWED_COMMIT_MISSING")
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", reviewed_commit, "HEAD"],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        require(ancestor.returncode == 0, "E_REVIEWED_COMMIT_NOT_ANCESTOR")
        evidence_diff = subprocess.run(
            ["git", "diff", "--name-only", f"{reviewed_commit}..HEAD"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(evidence_diff.returncode == 0, "E_REVIEW_EVIDENCE_DIFF")
        validate_post_candidate_paths(set(evidence_diff.stdout.splitlines()))
    reviewer_records: list[dict[str, Any]] = []
    for report in reports:
        reviewer = report.get("reviewer")
        require(isinstance(reviewer, dict), "E_REVIEWER")
        reviewer_id = reviewer.get("agent_id")
        require(isinstance(reviewer_id, str) and reviewer_id, "E_REVIEWER_ID")
        required_reviewer_fields = {
            "agent_id",
            "reviewer_identity_id",
            "reviewer_instance_or_session_id",
            "review_run_id",
            "append_only_signature_or_attestation",
        }
        require(set(reviewer) == required_reviewer_fields, "E_REVIEWER_FIELDS")
        require(
            reviewer.get("reviewer_identity_id") == reviewer_id
            and all(
                isinstance(reviewer.get(field), str) and reviewer[field]
                for field in required_reviewer_fields
            ),
            "E_REVIEWER_BINDING",
        )
        reviewer_records.append(reviewer)
        require(reviewer_id != "codex-execution-primary", "E_REVIEWER_IS_AUTHOR")
        require(report.get("reviewed_commit") == reviewed_commit, "E_REVIEWED_COMMIT")
        require(report.get("reviewed_snapshot_digest") == digest, "E_REVIEWED_DIGEST")
        require(
            report.get("review_scope")
            == "SUCCESSOR_DELEGATION_AND_NECESSARY_REGRESSION_ONLY"
            and report.get("full_review_restarted") is False,
            "E_REVIEW_SCOPE",
        )
        require(report.get("verdict") == "PASS", "E_REVIEW_VERDICT")
        require(
            isinstance(report.get("score"), int) and report["score"] >= 90,
            "E_REVIEW_SCORE",
        )
        require(report.get("blocking_findings") == [], "E_REVIEW_BLOCKERS")
        require(
            isinstance(report.get("necessary_regression_findings"), list),
            "E_REVIEW_REGRESSIONS",
        )
        require(report.get("repo_changed") is False, "E_REVIEW_REPO_WRITE")
        require(
            report.get("review_record_digest")
            == object_digest(report, "review_record_digest"),
            "E_REVIEW_RECORD_DIGEST",
        )
    for field in (
        "agent_id",
        "reviewer_identity_id",
        "reviewer_instance_or_session_id",
        "review_run_id",
        "append_only_signature_or_attestation",
    ):
        require(
            len({record[field] for record in reviewer_records}) == 2,
            "E_REVIEWER_IDENTITY_COLLISION",
        )
    reviewer_ids = [record["agent_id"] for record in reviewer_records]
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
    if review_state == "PENDING_ROOT_MERGE_APPROVAL":
        require(result.get("coordinator_decision") is None, "E_PENDING_COORDINATOR")
        return

    coordinator = load_yaml(root, COORDINATOR_PATH, "coordinator_decision")
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
        result.get("runtime_architecture") == "LIGHT_EXPRESSION"
        and result.get("normal_runtime_requires_atom_edge_or_path_refs") is False
        and result.get("historical_expression_assets_role")
        == "OPTIONAL_OFFLINE_RESEARCH_REGRESSION_AND_EXPERIMENT"
        and result.get("neutral_default_expression_profile_ref")
        == NEUTRAL_EXPRESSION_PROFILE_REF,
        "E_RESULT_LIGHT_EXPRESSION_ARCHITECTURE",
    )
    require(
        result.get("core_numbers_300_120_86_unchanged") is True, "E_RESULT_CORE_NUMBERS"
    )
    require(result.get("http_service_implemented") is False, "E_RESULT_HTTP")
    require(result.get("external_provider_call_count") == 0, "E_RESULT_PROVIDER_CALL")
    require(result.get("continuous_deployment_implemented") is False, "E_RESULT_CD")
    delivery_counts = result.get("delivery_counts")
    require(isinstance(delivery_counts, dict), "E_RESULT_DELIVERY_COUNTS")
    require(
        delivery_counts.get("contract_case_count") == len(EXPECTED_CASE_IDS),
        "E_RESULT_CASE_COUNT",
    )
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
    validate_contract_data(root, contract, identity)
    validate_expression_baseline(root, contract)
    validate_core_numbers(root, contract)
    validate_identity_data(identity)
    validate_topics_data(root, topics)
    validate_cases(cases, identity)
    validate_status_and_manifest(root, status, manifest)
    validate_workflow_registration(root)
    validate_result(root, result)
    validate_successor_packages(root)
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
    global SELFTEST_FAILURE_CASES_RUN
    try:
        callback()
    except CheckFailure as error:
        require(
            str(error).startswith(expected_prefix), f"E_SELFTEST_WRONG_ERROR:{error}"
        )
        SELFTEST_FAILURE_CASES_RUN += 1
        return
    raise CheckFailure(f"E_SELFTEST_FALSE_NEGATIVE:{expected_prefix}")


def run_selftest() -> dict[str, Any]:
    global SELFTEST_FAILURE_CASES_RUN
    SELFTEST_FAILURE_CASES_RUN = 0
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
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_SCOPE_OVERRIDE_POLICY",
    )

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["trusted_scope_contract"]["required_dimensions"].remove(
        "organization_id"
    )
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_SCOPE_DIMENSIONS",
    )

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["brand_fact_contract"]["channels"][1]["required_metadata"].remove(
        "authorization_ref"
    )
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_PRECISE_FACT_METADATA",
    )

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["brand_fact_contract"]["channels"][0]["required_metadata"].remove(
        "source_store_id"
    )
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_NARRATIVE_FRAGMENT_METADATA",
    )

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["brand_fact_contract"][
        "expression_guidance_may_be_fact_authorization_or_scope"
    ] = True
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_EXPRESSION_GUIDANCE_AS_AUTHORITY_POLICY",
    )

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["light_content_plan_contract"]["required_fields"].remove(
        "composition_plan_ref"
    )
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_PLAN_REQUIRED_FIELDS",
    )

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["expression_v1_baseline"]["normal_runtime_dependency"] = True
    expect_failure(
        lambda: validate_expression_baseline(ROOT, mutated_contract),
        "E_EXPRESSION_RUNTIME_OPTIONALITY",
    )

    for profile_field in (
        "client_may_supply_formal_profile",
        "client_soft_preferences_may_override_hard_prohibitions",
        "profile_may_grant_fact_authorization_or_scope",
        "cross_tenant_profile_borrowing_allowed",
    ):
        mutated_contract = copy.deepcopy(contract)
        mutated_contract["light_expression_contract"]["brand_expression_profile"][
            profile_field
        ] = True
        expect_failure(
            lambda: validate_contract_data(ROOT, mutated_contract, identity),
            "E_EXPRESSION_PROFILE_BOUNDARY",
        )

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["light_expression_contract"]["hard_check_categories"].remove(
        "authorization"
    )
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_HARD_SOFT_EVALUATION_BOUNDARY",
    )

    mutated_contract = copy.deepcopy(contract)
    prepare_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/prepare"
    )
    prepare_contract["request_example"].pop("confirmation_evidence")
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_PREPARE_REQUEST_EXAMPLE_FIELDS",
    )

    mutated_contract = copy.deepcopy(contract)
    prepare_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/prepare"
    )
    prepare_contract["client_trust_or_verified_labels_are_authoritative"] = True
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_PREPARE_TRUST_BOUNDARY",
    )

    mutated_contract = copy.deepcopy(contract)
    prepare_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/prepare"
    )
    prepare_contract["request_example"]["confirmation_evidence"][
        "authorization_refs"
    ] = ["AUTH-SIM-NOT-REGISTERED"]
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_PREPARE_CONFIRMATION_GRANT",
    )

    mutated_contract = copy.deepcopy(contract)
    prepare_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/prepare"
    )
    prepare_contract["request_example"]["output_requirements"][
        "required_candidate_count"
    ] = 4
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_PREPARE_CANDIDATE_COUNT",
    )

    mutated_contract = copy.deepcopy(contract)
    prepare_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/prepare"
    )
    prepare_contract["response_examples"]["light_content_plan"]["references"][
        "selected_component_refs"
    ] = ["COMPONENT-NOT-RUNTIME"]
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_PREPARE_PLAN_REFERENCE_FIELDS",
    )

    for reference_field, invalid_value in (
        ("trusted_scope_ref", "scope://unregistered"),
        (
            "confirmed_requirement_ref",
            "requirement://REQ-NOT-REGISTERED/versions/1",
        ),
        ("precise_fact_refs", ["FACT-NOT-REGISTERED"]),
        ("retrieval_fragment_refs", ["FRAGMENT-NOT-REGISTERED"]),
        ("brand_expression_profile_ref", "expression-profile://unregistered/v1"),
    ):
        mutated_contract = copy.deepcopy(contract)
        prepare_contract = next(
            item
            for item in mutated_contract["api_contracts"]
            if item["path"] == "/v1/content/prepare"
        )
        prepare_contract["response_examples"]["light_content_plan"]["references"][
            reference_field
        ] = invalid_value
        expect_failure(
            lambda: validate_contract_data(ROOT, mutated_contract, identity),
            "E_PREPARE_PLAN_SOURCE_REFS",
        )

    mutated_contract = copy.deepcopy(contract)
    prepare_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/prepare"
    )
    prepare_contract["response_examples"]["light_content_plan"][
        "soft_evaluation_tasks"
    ][0]["score"] = 95
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_PLAN_SOFT_EVALUATION_TASKS",
    )

    mutated_contract = copy.deepcopy(contract)
    validate_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/validate"
    )
    validate_contract["response_examples"]["pass"]["soft_evaluation_tasks"][0][
        "score"
    ] = 95
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_VALIDATE_SOFT_EVALUATION_TASKS",
    )

    mutated_contract = copy.deepcopy(contract)
    validate_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/validate"
    )
    validate_contract["response_examples"]["pass"]["semantic_fact_review_status"] = (
        "VERIFIED"
    )
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_VALIDATE_SEMANTIC_REVIEW_STATUS",
    )

    mutated_contract = copy.deepcopy(contract)
    validate_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/validate"
    )
    validate_contract["response_examples"]["pass"]["actually_used_fact_refs"] = [
        "FACT-NOT-USED"
    ]
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_VALIDATE_RESPONSE_SOURCE_REFS",
    )

    for collection_field, expected_error in (
        ("scoped_retrieval_fragments", "E_PREPARE_FRAGMENT_SAFETY"),
        ("verified_precise_facts", "E_PREPARE_FACT_SAFETY"),
    ):
        for metadata_field, invalid_value in (
            ("source_ref", "not-a-uri-reference"),
            ("authorization_ref", ""),
        ):
            mutated_contract = copy.deepcopy(contract)
            prepare_contract = next(
                item
                for item in mutated_contract["api_contracts"]
                if item["path"] == "/v1/content/prepare"
            )
            prepare_contract["request_example"][collection_field][0][metadata_field] = (
                invalid_value
            )
            expect_failure(
                lambda: validate_contract_data(ROOT, mutated_contract, identity),
                expected_error,
            )

    mutated_contract = copy.deepcopy(contract)
    validate_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/validate"
    )
    validate_contract["request_example"]["composition_plan_ref"] = (
        "plan://PLAN-NOT-REGISTERED/revisions/1"
    )
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_VALIDATE_SOURCE_REFS",
    )

    for reference_field, unregistered_ref in (
        ("actually_used_fact_refs", "FACT-NOT-REGISTERED"),
        ("actually_used_material_refs", "FRAGMENT-NOT-REGISTERED"),
    ):
        mutated_contract = copy.deepcopy(contract)
        validate_contract = next(
            item
            for item in mutated_contract["api_contracts"]
            if item["path"] == "/v1/content/validate"
        )
        validate_contract["request_example"][reference_field] = [unregistered_ref]
        expect_failure(
            lambda: validate_contract_data(ROOT, mutated_contract, identity),
            "E_VALIDATE_SOURCE_REFS",
        )

    mutated_contract = copy.deepcopy(contract)
    validate_contract = next(
        item
        for item in mutated_contract["api_contracts"]
        if item["path"] == "/v1/content/validate"
    )
    validate_contract["response_examples"]["pass"].pop("plain_language_reason")
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_VALIDATE_RESPONSE_REQUIRED_FIELDS",
    )

    mutated_contract = copy.deepcopy(contract)
    mutated_contract["user_output_contract"]["prohibited_patterns"].remove(
        "(G1V11|RCV2)-[A-Z0-9-]+"
    )
    expect_failure(
        lambda: validate_contract_data(ROOT, mutated_contract, identity),
        "E_USER_OUTPUT_PATTERNS",
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["content_accounts"][0]["publish_allowed"] = True
    expect_failure(
        lambda: validate_identity_data(mutated_identity), "E_ACCOUNT_PUBLISH"
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["work_roles"][0]["simulation_only"] = False
    expect_failure(
        lambda: validate_identity_data(mutated_identity), "E_ROLE_SIMULATION"
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["login_principals"][0]["allowed_content_account_ids"].pop()
    expect_failure(
        lambda: validate_identity_data(mutated_identity), "E_SIM_ACCOUNT_ALLOWLIST"
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["login_principals"][0]["account_role_grants"][0][
        "maker_role_ids"
    ].clear()
    expect_failure(
        lambda: validate_identity_data(mutated_identity),
        "E_SIM_MAKER_GRANT:ACCOUNT-DIYU-HQ-OFFICIAL",
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["login_principals"][0]["account_role_grants"][0][
        "simulation_only"
    ] = False
    expect_failure(
        lambda: validate_identity_data(mutated_identity),
        "E_SIM_ROLE_GRANT_SIMULATION:ACCOUNT-DIYU-HQ-OFFICIAL",
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["content_accounts"][0]["confirmation_routes"][0][
        "publish_allowed"
    ] = True
    expect_failure(
        lambda: validate_identity_data(mutated_identity),
        "E_CONFIRMATION_ROUTE_PUBLISH:ACCOUNT-DIYU-HQ-OFFICIAL:brand_formal_conclusion",
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["organizations"][0]["tenant_id"] = "TENANT-OTHER"
    expect_failure(lambda: validate_identity_data(mutated_identity), "E_ORG_TENANT_REF")

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["content_accounts"][0]["store_id"] = "STORE-DIYU-HZ-BINJIANG"
    expect_failure(
        lambda: validate_identity_data(mutated_identity),
        "E_ACCOUNT_STORE_ORGANIZATION:ACCOUNT-DIYU-HQ-OFFICIAL",
    )

    mutated_identity = copy.deepcopy(identity)
    product_account = next(
        account
        for account in mutated_identity["content_accounts"]
        if account["account_id"] == "ACCOUNT-DIYU-PRODUCT-LEAD"
    )
    product_account["confirmation_routes"][1]["approval_mode"] = "ANY_OF"
    expect_failure(
        lambda: validate_identity_data(mutated_identity),
        "E_CONFIRMATION_MODE:ACCOUNT-DIYU-PRODUCT-LEAD:safety_quality_testing_supplier_responsibility",
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["authorization_grants"][0]["permitted_content_account_ids"] = [
        "ACCOUNT-DIYU-SZ-PARK"
    ]
    expect_failure(
        lambda: validate_identity_data(mutated_identity),
        "E_AUTHORIZATION_TARGET_SCOPE:AUTH-SIM-001:ACCOUNT-DIYU-SZ-PARK",
    )

    mutated_identity = copy.deepcopy(identity)
    mutated_identity["authorization_grants"][0]["valid_from"] = "2027-01-01T00:00:00Z"
    expect_failure(
        lambda: validate_identity_data(mutated_identity),
        "E_AUTHORIZATION_STATE:AUTH-SIM-001",
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
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    base_prepare = next(case for case in cases if case["case_id"] == "PF-POS-003")
    without_optional_assets = copy.deepcopy(base_prepare)
    for field in (
        "experimental_diagnostics",
        "expression_baseline_ref",
        "component_refs",
        "control_rule_refs",
        "edge_refs",
        "structural_path_ref",
    ):
        without_optional_assets["input"].pop(field, None)
    require(
        evaluate_case(without_optional_assets, identity, trusted_upstream=True)
        == {"decision": "PREPARE_PLAN", "light_plan_created": True},
        "E_SELFTEST_ATOM_FREE_PREPARE",
    )

    with_unknown_experiment_refs = copy.deepcopy(without_optional_assets)
    with_unknown_experiment_refs["input"]["experimental_diagnostics"] = {
        "component_refs": ["UNKNOWN-COMPONENT"],
        "control_rule_refs": ["UNKNOWN-RULE"],
        "edge_refs": ["UNKNOWN-EDGE"],
        "structural_path_ref": "UNKNOWN-PATH",
    }
    require(
        evaluate_case(with_unknown_experiment_refs, identity, trusted_upstream=True)
        == evaluate_case(without_optional_assets, identity, trusted_upstream=True),
        "E_SELFTEST_EXPERIMENT_REFS_CHANGED_AUTHORITY",
    )

    for input_kind in EXPRESSION_GUIDANCE_INPUT_KINDS:
        for claimed_as in AUTHORITY_CLAIM_KINDS:
            require(
                evaluate_case(
                    {
                        "case_id": "SELFTEST-EXPRESSION-AUTHORITY",
                        "operation": "fact_input",
                        "input": {
                            "input_kind": input_kind,
                            "claimed_as": claimed_as,
                        },
                    },
                    identity,
                ).get("decision")
                == "REJECT_EXPRESSION_GUIDANCE_AS_AUTHORITY",
                "E_SELFTEST_EXPRESSION_GUIDANCE_AUTHORITY",
            )

    require(
        evaluate_case(base_prepare, identity).get("decision")
        == "REJECT_UNTRUSTED_UPSTREAM",
        "E_SELFTEST_PAYLOAD_CANNOT_DECLARE_TRUST",
    )

    for field, value in (
        ("trusted", True),
        ("verified", True),
        ("formal_brand_expression_profile", {"mode": "SERVER_RESOLVED"}),
    ):
        mutated_prepare = copy.deepcopy(base_prepare)
        mutated_prepare["input"][field] = value
        require(
            evaluate_case(mutated_prepare, identity, trusted_upstream=True).get(
                "decision"
            )
            == "REJECT_UNTRUSTED_UPSTREAM_FIELD",
            f"E_SELFTEST_PREPARE_TRUST_FIELD:{field}",
        )

    mutated_prepare = copy.deepcopy(base_prepare)
    mutated_prepare["input"]["client_soft_preferences"] = {"prohibited_phrasing": []}
    require(
        evaluate_case(mutated_prepare, identity, trusted_upstream=True).get("decision")
        == "REJECT_HARD_PROHIBITION_OVERRIDE",
        "E_SELFTEST_CLIENT_SOFT_PREFERENCE_ALLOWLIST",
    )

    mutated_prepare = copy.deepcopy(base_prepare)
    mutated_prepare["input"]["required_candidate_count"] = 4
    require(
        evaluate_case(mutated_prepare, identity, trusted_upstream=True).get("decision")
        == "REJECT_CANDIDATE_COUNT",
        "E_SELFTEST_CANDIDATE_COUNT",
    )

    base_validate = next(case for case in cases if case["case_id"] == "PF-POS-005")
    require(
        evaluate_case(base_validate, identity).get("decision")
        == "REJECT_UNTRUSTED_UPSTREAM",
        "E_SELFTEST_VALIDATE_REQUIRES_TRUSTED_CONTEXT",
    )
    for field, invalid_value in (
        ("soft_evaluation_scores", {"naturalness": 95}),
        ("semantic_fact_review_status", "VERIFIED"),
    ):
        mutated_validate = copy.deepcopy(base_validate)
        mutated_validate["input"][field] = invalid_value
        require(
            evaluate_case(mutated_validate, identity, trusted_upstream=True).get(
                "decision"
            )
            == "VALIDATE_BLOCK",
            f"E_SELFTEST_FAKE_SEMANTIC_RESULT:{field}",
        )

    for field, invalid_ref in (
        ("actually_used_fact_refs", "FACT-NOT-IN-PLAN"),
        ("actually_used_material_refs", "FRAGMENT-NOT-IN-PLAN"),
    ):
        mutated_cases = copy.deepcopy(cases)
        positive_validate = next(
            case for case in mutated_cases if case["case_id"] == "PF-POS-005"
        )
        positive_validate["input"][field] = [invalid_ref]
        expect_failure(
            lambda: validate_cases(mutated_cases, identity),
            "E_CASE_DECISION",
        )

    for field, invalid_ref in (
        ("plan_allowed_fact_refs", "FACT-NOT-AVAILABLE"),
        ("plan_allowed_material_refs", "FRAGMENT-NOT-AVAILABLE"),
    ):
        mutated_cases = copy.deepcopy(cases)
        positive_validate = next(
            case for case in mutated_cases if case["case_id"] == "PF-POS-005"
        )
        positive_validate["input"][field].append(invalid_ref)
        expect_failure(
            lambda: validate_cases(mutated_cases, identity),
            "E_CASE_DECISION",
        )

    for field, invalid_value in (
        ("status", "REVOKED"),
        ("valid_until", "2026-07-13T23:59:59Z"),
        ("authorization_ref", "AUTH-SIM-NOT-REGISTERED"),
        ("applicable_content_account_ids", ["ACCOUNT-DIYU-FOUNDER"]),
    ):
        mutated_cases = copy.deepcopy(cases)
        positive_validate = next(
            case for case in mutated_cases if case["case_id"] == "PF-POS-005"
        )
        positive_validate["input"]["scoped_retrieval_fragments"][0][field] = (
            invalid_value
        )
        expect_failure(
            lambda: validate_cases(mutated_cases, identity),
            "E_CASE_DECISION",
        )

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["candidate_user_visible_surfaces"]["title"] = (
        "泄漏 G1V11-P2-ACTION-AUTHORIZED-LOCAL-ROUTINE"
    )
    positive_validate["input"]["internal_identifier_leak"] = False
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["candidate_user_visible_surfaces"]["CP01"] = "普通文本"
    positive_validate["input"]["internal_identifier_leak"] = False
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    for surface_field in ("execution_payload", "surface_units"):
        mutated_cases = copy.deepcopy(cases)
        positive_validate = next(
            case for case in mutated_cases if case["case_id"] == "PF-POS-005"
        )
        positive_validate["input"]["candidate_user_visible_surfaces"][surface_field] = {
            "CP01": "普通文本"
        }
        expect_failure(
            lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION"
        )

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["candidate_user_visible_text"] = (
        "required_authorization_missing"
    )
    positive_validate["input"]["internal_identifier_leak"] = False
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["user_visible_footer"] = {"note": "普通说明"}
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["candidate_user_visible_surfaces"][
        "user_visible_footer"
    ] = "普通说明"
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["candidate_user_visible_surfaces"]["title"] = "CP"
    positive_validate["input"]["candidate_user_visible_surfaces"]["body"] = "01"
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    subject_confirmed = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-011"
    )
    subject_confirmed["input"]["subject_confirmation_ref"] = (
        "SUBJECT-CONFIRM-SIM-NOT-REGISTERED"
    )
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    scoped_material = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-012"
    )
    scoped_material["input"]["retrieval_fragment"]["source_organization_id"] = (
        "ORG-NOT-REGISTERED"
    )
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    scoped_material = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-012"
    )
    scoped_material["input"]["retrieval_fragment"]["source_ref"] = ""
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    expect_failure(
        lambda: validate_cases(cases[:-1], identity),
        "E_CASE_COUNT",
    )

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["candidate_user_visible_surfaces"]["title"] = (
        "required_fact_missing"
    )
    positive_validate["input"]["internal_identifier_leak"] = False
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["verified_precise_facts"][0][
        "applicable_content_account_ids"
    ] = ["ACCOUNT-DIYU-FOUNDER"]
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_prepare = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-003"
    )
    positive_prepare["input"]["trusted_scope"]["organization_id"] = "ORG-DIYU-SZ-PARK"
    positive_prepare["input"]["trusted_scope"]["store_id"] = "STORE-DIYU-SZ-PARK"
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["verified_precise_facts"][0]["valid_until"] = (
        "2026-07-13T23:59:59Z"
    )
    positive_validate["input"]["evaluation_time"] = "2020-01-01T00:00:00Z"
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["verified_precise_facts"][0]["authorization_ref"] = (
        "AUTH-SIM-NOT-REGISTERED"
    )
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["verified_precise_facts"][0]["source_ref"] = ""
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

    mutated_cases = copy.deepcopy(cases)
    positive_validate = next(
        case for case in mutated_cases if case["case_id"] == "PF-POS-005"
    )
    positive_validate["input"]["verified_precise_facts"][0]["fact_kind"] = (
        "MODEL_INFERENCE"
    )
    expect_failure(lambda: validate_cases(mutated_cases, identity), "E_CASE_DECISION")

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

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["downstream_reserved_write_roots"][0]["root"] += "_extra"
    expect_failure(
        lambda: validate_status_and_manifest(ROOT, status, mutated_manifest),
        "E_MANIFEST_DOWNSTREAM_BINDING",
    )

    validate_post_candidate_paths(
        {
            (package_root / f"selftest-{package_id.lower()}.txt").as_posix()
            for package_id, package_root, _, _ in SUCCESSOR_PACKAGES
        }
    )
    expect_failure(
        lambda: validate_post_candidate_paths(
            {"12_expression_service/unreserved_package/file.txt"}
        ),
        "E_REVIEW_POST_CANDIDATE_SCOPE",
    )
    expect_failure(
        lambda: validate_post_candidate_paths(
            {"12_expression_service/expression_runtime_adapter_001_extra/file.txt"}
        ),
        "E_REVIEW_POST_CANDIDATE_SCOPE",
    )

    with tempfile.TemporaryDirectory(
        prefix="product-foundation-selftest-"
    ) as temporary:
        temp_root = Path(temporary)
        shutil.copytree(ROOT / FOUNDATION_ROOT, temp_root / FOUNDATION_ROOT)
        extra = temp_root / FOUNDATION_ROOT / "unexpected.yaml"
        extra.write_text("unexpected: true\n", encoding="utf-8")
        result = load_yaml(ROOT, RESULT_PATH, "public_foundation_result")
        expect_failure(
            lambda: validate_foundation_files(
                temp_root, str(result.get("review_state"))
            ),
            "E_FOUNDATION_FILE_SET",
        )

    with tempfile.TemporaryDirectory(
        prefix="product-foundation-history-tamper-"
    ) as temporary:
        temp_root = Path(temporary)
        for relative_path, _, _ in EXPECTED_EXPRESSION_ASSETS.values():
            source = ROOT / relative_path
            destination = temp_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        tampered = temp_root / EXPECTED_EXPRESSION_ASSETS["ACTIVE_COMPONENTS"][0]
        tampered.write_bytes(tampered.read_bytes() + b"\n")
        expect_failure(
            lambda: validate_expression_baseline(temp_root, contract),
            "E_ASSET_LIVE_DIGEST:ACTIVE_COMPONENTS",
        )

    with tempfile.TemporaryDirectory(
        prefix="product-foundation-workflow-registration-"
    ) as temporary:
        temp_root = Path(temporary)
        destination = temp_root / WORKFLOW_PATH
        checker_destination = temp_root / CHECKER_PATH
        destination.parent.mkdir(parents=True, exist_ok=True)
        checker_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / WORKFLOW_PATH, destination)
        shutil.copy2(ROOT / CHECKER_PATH, checker_destination)
        workflow_text = destination.read_text(encoding="utf-8")
        destination.write_text(
            workflow_text.replace(
                "          python3 ci/checkers/check_product_foundation.py\n",
                "          # python3 ci/checkers/check_product_foundation.py\n",
                1,
            ),
            encoding="utf-8",
        )
        expect_failure(
            lambda: validate_workflow_registration(temp_root),
            "E_WORKFLOW_REGISTRATION",
        )

        shutil.copy2(ROOT / WORKFLOW_PATH, destination)
        workflow_text = destination.read_text(encoding="utf-8")
        pin_line = next(
            line
            for line in workflow_active_run_lines(ROOT)
            if WORKFLOW_CHECKER_PIN_PATTERN.fullmatch(line)
        )
        pin_match = WORKFLOW_CHECKER_PIN_PATTERN.fullmatch(pin_line)
        require(pin_match is not None, "E_SELFTEST_WORKFLOW_PIN")
        destination.write_text(
            workflow_text.replace(pin_match.group(1), "0" * 64, 1),
            encoding="utf-8",
        )
        expect_failure(
            lambda: validate_workflow_registration(temp_root),
            "E_WORKFLOW_CHECKER_DIGEST_PIN",
        )

        shutil.copy2(ROOT / WORKFLOW_PATH, destination)
        workflow_text = destination.read_text(encoding="utf-8")
        skipped_call = SUCCESSOR_NORMAL_RUN_LINES[-1]
        destination.write_text(
            workflow_text.replace(skipped_call, f"# {skipped_call}", 1),
            encoding="utf-8",
        )
        expect_failure(
            lambda: validate_workflow_registration(temp_root),
            "E_WORKFLOW_SUCCESSOR_NORMAL:BODY",
        )

    with tempfile.TemporaryDirectory(
        prefix="product-foundation-successor-checkers-"
    ) as temporary:
        temp_root = Path(temporary)
        passing_checker = """#!/usr/bin/env python3
import sys
if not __debug__:
    raise SystemExit(2)
raise SystemExit(0)
"""
        for _, package_root, checker, _ in CHECKED_DOWNSTREAM_PACKAGES:
            (temp_root / package_root).mkdir(parents=True, exist_ok=True)
            checker_path = temp_root / checker
            checker_path.write_text(passing_checker, encoding="utf-8")
        validate_successor_packages(temp_root)

        missing_checker = temp_root / CHECKED_DOWNSTREAM_PACKAGES[1][2]
        missing_checker.unlink()
        expect_failure(
            lambda: validate_successor_packages(temp_root),
            "E_SUCCESSOR_CHECKER_MISSING",
        )

        missing_checker.write_text(passing_checker, encoding="utf-8")
        failing_checker = temp_root / CHECKED_DOWNSTREAM_PACKAGES[0][2]
        failing_checker.write_text("raise SystemExit(1)\n", encoding="utf-8")
        expect_failure(
            lambda: validate_successor_packages(temp_root),
            "E_SUCCESSOR_CHECKER_NORMAL",
        )

        failing_checker.write_text(passing_checker, encoding="utf-8")
        mandatory_root = next(iter(MANDATORY_SUCCESSOR_ROOTS))
        shutil.rmtree(temp_root / mandatory_root)
        expect_failure(
            lambda: validate_successor_packages(temp_root),
            "E_SUCCESSOR_ROOT_MISSING",
        )

    with tempfile.TemporaryDirectory(
        prefix="product-foundation-reference-safe-successor-"
    ) as temporary:
        temp_root = Path(temporary)
        package_root = Path("15_brand_retrieval/brand_fact_retrieval_001")
        reference_commit = REFERENCE_SAFE_SUCCESSOR_COMMITS[
            package_root / "check_brand_fact_retrieval.py"
        ]
        reference_paths = git_tree_paths(reference_commit, package_root)
        for relative in reference_paths:
            destination = temp_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(git_object_bytes(reference_commit, relative))
        validate_reference_safe_successor_bytes(
            temp_root, package_root, reference_commit
        )

        mutated_path = min(reference_paths, key=lambda path: path.as_posix())
        (temp_root / mutated_path).write_bytes(
            (temp_root / mutated_path).read_bytes() + b"\n"
        )
        expect_failure(
            lambda: validate_reference_safe_successor_bytes(
                temp_root, package_root, reference_commit
            ),
            "E_SUCCESSOR_REFERENCE_BYTES",
        )

    with tempfile.TemporaryDirectory(
        prefix="product-foundation-p7-reference-safe-successor-"
    ) as temporary:
        temp_root = Path(temporary)
        package_root = Path("17_dify_runtime/dify_end_to_end_001")
        checker = package_root / "check_dify_end_to_end.py"
        reference_commit = REFERENCE_SAFE_SUCCESSOR_COMMITS[checker]
        reference_paths = git_tree_paths(reference_commit, package_root)
        for relative in reference_paths:
            destination = temp_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(git_object_bytes(reference_commit, relative))
        mutable_path = min(
            REFERENCE_SAFE_SUCCESSOR_MUTABLE_PATHS[checker],
            key=lambda path: path.as_posix(),
        )
        (temp_root / mutable_path).write_bytes(
            (temp_root / mutable_path).read_bytes() + b"\n# package-8-live-change\n"
        )
        validate_reference_safe_successor_bytes(
            temp_root, package_root, reference_commit
        )

        frozen_path = min(
            reference_paths - REFERENCE_SAFE_SUCCESSOR_MUTABLE_PATHS[checker],
            key=lambda path: path.as_posix(),
        )
        (temp_root / frozen_path).write_bytes(
            (temp_root / frozen_path).read_bytes() + b"\n"
        )
        expect_failure(
            lambda: validate_reference_safe_successor_bytes(
                temp_root, package_root, reference_commit
            ),
            "E_SUCCESSOR_REFERENCE_BYTES",
        )

    return {"selftest_cases": SELFTEST_FAILURE_CASES_RUN, "result": "PASS"}


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
