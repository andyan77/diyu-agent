#!/usr/bin/env python3
"""Fail-closed checker for the Controlled V2 20CP qualification probe 40."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    print("check_controlled_v2_20cp_qualification_probe_40 refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "CONTROLLED_V2_20CP_QUALIFICATION_PROBE_40_001"
PHASE0_MERGE_COMMIT_SHA = "25ce4ff092befe39106783d8b7f2cf31e77f0e82"
PHASE0_MERGE_TREE_SHA = "d961d44c977cbeecd762827218b75008108f8414"
REVIEWED_BASE_SHA = "0ed9fd40203a6423d4deb9e6342c441ac3c129c1"
REVIEWED_HEAD_SHA = "7b7f87db532ad89271d471bb0020d749324af917"
REVIEWED_HEAD_TREE_SHA = "d961d44c977cbeecd762827218b75008108f8414"
REVIEWED_FULL_DIFF_DIGEST = "e40bb98a0af50d7a8351c3038b53edde6d46d0157f9ca4780cd74a8539c5be3e"
QUALIFICATION_PROBE_AS_BUILT_HEAD_SHA = "aaeda5a280b2790c00157e47f89370f6535ee230"

TASK_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")
PACKS_PATH = TASK_DIR / "qualification_material_packs.v0.1.jsonl"
ASSIGNMENTS_PATH = TASK_DIR / "qualification_probe_assignments.v0.1.jsonl"
PLANS_PATH = TASK_DIR / "canonical_qualification_composition_plans.v0.1.jsonl"
INSTRUCTIONS_PATH = TASK_DIR / "qualification_generation_instructions.v0.1.jsonl"
CANDIDATES_PATH = TASK_DIR / "qualification_probe_candidates.v0.1.jsonl"
ACCEPTANCE_RESULTS_PATH = TASK_DIR / "qualification_machine_acceptance_results.v0.1.jsonl"
RESULT_PATH = TASK_DIR / "qualification_probe_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "qualification_guardian_review_packet.v0.1.yaml"
ORCH_MATERIALIZER_PATH = TASK_DIR / "run_qualification_probe_40_orch_materializer.py"
GENERATOR_ENTRY_PATH = TASK_DIR / "run_qualification_probe_40_generator_acceptance.py"

CHECKER_PATH = Path("ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py")
TARGETED_REPAIR_CHECKER_PATH = Path("ci/checkers/check_controlled_v2_qualification_probe_40_targeted_repair.py")
CALIBRATION_REPAIR_002_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_qualification_calibration_targeted_repair_002.py"
)
CONVERGENCE_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_creative_authoring_route_convergence.py"
)
GENERATOR_BUILD_CHECKER_PATH = Path("ci/checkers/check_controlled_content_generator_v2_build.py")
COMPONENT_SUPPLY_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py")
FACT_AUTH_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py")
ORCH_CHECKER_PATH = Path("ci/checkers/check_orch_v2_20cp_validation_dryrun.py")
CI_PATH = Path(".github/workflows/ci.yml")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
SUCCESSOR_TARGETED_REPAIR_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_targeted_repair_001")
SUCCESSOR_CALIBRATION_REPAIR_002_DIR = Path(
    "controlled_content_generator_v2_001/qualification_calibration_targeted_repair_002"
)
SUCCESSOR_CONVERGENCE_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001"
)
SUCCESSOR_B_LANE_DIR = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001"
)

GKB_ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
PROFILES_PATH = GKB_ROOT / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
COMPONENT_REGISTRY_PATH = GKB_ROOT / "component_supply_closeout_20cp_001/reviewed_reusable_component_registry.v0.3.jsonl"
VALIDATION_FIXTURES_PATH = GKB_ROOT / "fact_authorization_fixture_closeout_001/content_product_validation_fixtures.v0.1.jsonl"
ORCH_VALIDATION_PLANS_PATH = Path(
    "08_orchestration_runs/controlled_composition_v2_001/"
    "orch_20cp_validation_dryrun_001/orch_validation_canonical_plans.v0.1.jsonl"
)
GENERATOR_HARNESS_CASES_PATH = Path(
    "controlled_content_generator_v2_001/build_and_acceptance_harness_001/"
    "generator_acceptance_harness_cases.v0.1.jsonl"
)
GENERATOR_HARNESS_RESULTS_PATH = Path(
    "controlled_content_generator_v2_001/build_and_acceptance_harness_001/"
    "generator_acceptance_harness_results.v0.1.jsonl"
)
GENERATOR_BUILD_RESULT_PATH = Path(
    "controlled_content_generator_v2_001/build_and_acceptance_harness_001/"
    "generator_v2_build_result.v0.1.yaml"
)
GENERATOR_BUILD_FREEZER_PATH = Path(
    "controlled_content_generator_v2_001/build_and_acceptance_harness_001/"
    "run_generator_v2_acceptance_harness.py"
)
COMPONENT_SUPPLY_FREEZER_PATH = (
    GKB_ROOT / "component_supply_closeout_20cp_001/run_component_supply_closeout_freezer.py"
)
FACT_AUTH_FREEZER_PATH = (
    GKB_ROOT / "fact_authorization_fixture_closeout_001/run_fact_authorization_fixture_freezer.py"
)
ORCH_FREEZER_PATH = Path(
    "08_orchestration_runs/controlled_composition_v2_001/"
    "orch_20cp_validation_dryrun_001/run_orch_20cp_validation_dryrun_freezer.py"
)

QUALIFICATION_NAMESPACE = "qualification://controlled-v2/probe-40/"
VISIBLE_DISCLOSURE_TEXT = "INTERNAL QUALIFICATION PROBE / SYNTHETIC CASE / NOT PUBLISHABLE"
EXPECTED_CPS = [f"CP{index:02d}" for index in range(1, 21)]
EXPECTED_GENERATED_DIGEST_PATHS = {
    PACKS_PATH,
    ASSIGNMENTS_PATH,
    PLANS_PATH,
    INSTRUCTIONS_PATH,
    CANDIDATES_PATH,
    ACCEPTANCE_RESULTS_PATH,
    PACKET_PATH,
    ORCH_MATERIALIZER_PATH,
    GENERATOR_ENTRY_PATH,
    CHECKER_PATH,
}
ALLOWED_CHANGED_PATHS = {
    CHECKER_PATH,
    TARGETED_REPAIR_CHECKER_PATH,
    CALIBRATION_REPAIR_002_CHECKER_PATH,
    CONVERGENCE_CHECKER_PATH,
    GENERATOR_BUILD_CHECKER_PATH,
    COMPONENT_SUPPLY_CHECKER_PATH,
    FACT_AUTH_CHECKER_PATH,
    ORCH_CHECKER_PATH,
    COMPONENT_SUPPLY_FREEZER_PATH,
    FACT_AUTH_FREEZER_PATH,
    ORCH_FREEZER_PATH,
    GENERATOR_BUILD_FREEZER_PATH,
    CI_PATH,
    LEDGER_PATH,
}
FALSE_KEYS = {
    "generator_qualified",
    "runtime_provider_adapter_qualified",
    "runtime_ingest_ready",
    "generation_eligible",
    "generation_allowed",
    "generation_600_allowed",
    "expand_600_allowed",
    "expand_3600_allowed",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "Serving_ready",
    "production_ready",
    "release_ready",
    "runtime_consumable",
    "production_consumable",
    "publishable",
    "may_be_published",
    "may_enter_KE_RAG_DIFY",
    "runtime_authoritative",
    "production_executable",
    "runtime_executable",
}
ZERO_KEYS = {
    "verified_brand_fact_bundle_count",
    "verified_runtime_authorization_count",
    "external_provider_request_count",
    "external_provider_API_call_count",
    "credential_read_count",
    "provider_request_count",
    "provider_api_call_count",
    "published_content_count",
    "accepted_content_count",
    "baseline_increment_count",
    "guardian_accepted_count",
    "founder_accepted_count",
    "canonical_runtime_composition_plan_count",
    "canonical_production_composition_plan_count",
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


def unwrap(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"missing wrapper {key}")
    return value


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
    names = git(root, ["diff", "--name-only", f"{PHASE0_MERGE_COMMIT_SHA}..HEAD"])
    names += git(root, ["diff", "--name-only", "HEAD"])
    names += git(root, ["ls-files", "--others", "--exclude-standard"])
    return {Path(line) for line in names.splitlines() if line}


def recursive_true_flags(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FALSE_KEYS and child is True:
                hits.append(child_path)
            hits.extend(recursive_true_flags(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_true_flags(child, f"{path}[{index}]"))
    return hits


def recursive_nonzero_counts(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in ZERO_KEYS and child not in (0, False):
                hits.append(f"{child_path}={child}")
            hits.extend(recursive_nonzero_counts(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_nonzero_counts(child, f"{path}[{index}]"))
    return hits


def load_snapshot(root: Path) -> dict[str, Any]:
    return {
        "packs": [unwrap(row, "qualification_material_pack") for row in load_jsonl(root / PACKS_PATH)],
        "assignments": [unwrap(row, "qualification_probe_assignment") for row in load_jsonl(root / ASSIGNMENTS_PATH)],
        "plans": [unwrap(row, "canonical_qualification_composition_plan") for row in load_jsonl(root / PLANS_PATH)],
        "instructions": [unwrap(row, "qualification_generation_instruction") for row in load_jsonl(root / INSTRUCTIONS_PATH)],
        "candidates": [unwrap(row, "qualification_probe_candidate") for row in load_jsonl(root / CANDIDATES_PATH)],
        "acceptance": [
            unwrap(row, "qualification_machine_acceptance_result") for row in load_jsonl(root / ACCEPTANCE_RESULTS_PATH)
        ],
        "result": load_yaml(root / RESULT_PATH)["qualification_probe_result"],
        "packet": load_yaml(root / PACKET_PATH)["qualification_guardian_review_packet"],
        "profiles": load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]["profiles"],
        "components": [next(iter(row.values())) for row in load_jsonl(root / COMPONENT_REGISTRY_PATH)],
        "fixtures": load_jsonl(root / VALIDATION_FIXTURES_PATH),
        "validation_plans": [
            unwrap(row, "orch_validation_composition_plan") for row in load_jsonl(root / ORCH_VALIDATION_PLANS_PATH)
        ],
        "harness_cases": [
            unwrap(row, "generator_acceptance_harness_case") for row in load_jsonl(root / GENERATOR_HARNESS_CASES_PATH)
        ],
        "harness_results": [
            unwrap(row, "generator_acceptance_harness_result")
            for row in load_jsonl(root / GENERATOR_HARNESS_RESULTS_PATH)
        ],
        "build_result": load_yaml(root / GENERATOR_BUILD_RESULT_PATH)["generator_v2_build_result"],
    }


def validate_preflight(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    if not enforce_git:
        return
    head = git(root, ["rev-parse", "HEAD"]).strip()
    if not head:
        add_error(errors, "E_HEAD", "git", "cannot resolve HEAD")
    elif head != PHASE0_MERGE_COMMIT_SHA and not git_ok(
        root, ["merge-base", "--is-ancestor", PHASE0_MERGE_COMMIT_SHA, head]
    ):
        add_error(errors, "E_BASELINE", "git", f"{PHASE0_MERGE_COMMIT_SHA} is not ancestor of {head}")
    unexpected = sorted(
        path.as_posix()
        for path in changed_paths(root) - ALLOWED_CHANGED_PATHS
        if not path.is_relative_to(TASK_DIR)
        and not path.is_relative_to(SUCCESSOR_TARGETED_REPAIR_DIR)
        and not path.is_relative_to(SUCCESSOR_CALIBRATION_REPAIR_002_DIR)
        and not path.is_relative_to(SUCCESSOR_CONVERGENCE_DIR)
        and not path.is_relative_to(SUCCESSOR_B_LANE_DIR)
    )
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", "git", str(unexpected))
    parents = git(root, ["show", "-s", "--format=%P", PHASE0_MERGE_COMMIT_SHA]).split()
    tree = git(root, ["show", "-s", "--format=%T", PHASE0_MERGE_COMMIT_SHA]).strip()
    if REVIEWED_BASE_SHA not in parents or REVIEWED_HEAD_SHA not in parents:
        add_error(errors, "E_PHASE0_PARENTS", "git", str(parents))
    if tree != PHASE0_MERGE_TREE_SHA or tree != REVIEWED_HEAD_TREE_SHA:
        add_error(errors, "E_PHASE0_TREE", "git", tree)


def validate_input_baseline(snapshot: dict[str, Any], errors: list[dict[str, str]]) -> None:
    if len(snapshot["profiles"]) != 20:
        add_error(errors, "E_PROFILE_COUNT", "baseline", str(len(snapshot["profiles"])))
    if len(snapshot["components"]) != 64:
        add_error(errors, "E_COMPONENT_COUNT", "baseline", str(len(snapshot["components"])))
    if len(snapshot["fixtures"]) != 60:
        add_error(errors, "E_FIXTURE_COUNT", "baseline", str(len(snapshot["fixtures"])))
    if len(snapshot["validation_plans"]) != 20:
        add_error(errors, "E_VALIDATION_PLAN_COUNT", "baseline", str(len(snapshot["validation_plans"])))
    if len(snapshot["harness_cases"]) != 16:
        add_error(errors, "E_HARNESS_CASE_COUNT", "baseline", str(len(snapshot["harness_cases"])))
    harness_kind_counts = Counter(row.get("record_kind") for row in snapshot["harness_results"])
    if harness_kind_counts.get("validation_plan_input_gate") != 20:
        add_error(errors, "E_HARNESS_GATE_COUNT", "baseline", str(harness_kind_counts))
    accepted_validation = [
        row
        for row in snapshot["harness_results"]
        if row.get("record_kind") == "validation_plan_input_gate"
        and row.get("decision") != "BLOCKED_NON_RUNTIME_VALIDATION_PLAN"
    ]
    if accepted_validation:
        add_error(errors, "E_VALIDATION_PLAN_INPUT_GATE", "baseline", str(accepted_validation[:1]))
    if snapshot["build_result"]["input_gate"].get("validation_plan_rejected_count") != 20:
        add_error(errors, "E_GENERATOR_INPUT_GATE", "baseline", str(snapshot["build_result"].get("input_gate")))


def validate_pack(pack: dict[str, Any], fixture_by_id: dict[str, dict[str, Any]], errors: list[dict[str, str]]) -> None:
    pack_id = pack.get("pack_id", "?")
    if pack.get("task_id") != TASK_ID or pack.get("schema_version") != "v0.1":
        add_error(errors, "E_PACK_SCHEMA", pack_id, str(pack))
    if pack.get("pack_digest") != object_digest(pack, {"pack_digest"}):
        add_error(errors, "E_PACK_DIGEST", pack_id, "digest mismatch")
    cp_id = pack.get("content_product_type_id")
    expected_id = f"QMP-{cp_id}-001"
    if pack_id != expected_id or cp_id not in EXPECTED_CPS:
        add_error(errors, "E_PACK_ID", pack_id, str(cp_id))
    flags = {
        "synthetic": True,
        "qualification_only": True,
        "runtime_consumable": False,
        "production_consumable": False,
        "publishable": False,
    }
    for key, value in flags.items():
        if pack.get(key) is not value:
            add_error(errors, "E_PACK_BOUNDARY", pack_id, f"{key}={pack.get(key)}")
    boundary = pack.get("hard_boundary", {})
    for key in [
        "may_be_published",
        "may_enter_DIFY",
        "may_enter_KE_truth",
        "may_enter_RAG",
        "verified_brand_fact",
        "verified_runtime_authorization",
    ]:
        if boundary.get(key) is not False:
            add_error(errors, "E_PACK_BOUNDARY", pack_id, f"{key}={boundary.get(key)}")
    fixture = fixture_by_id.get(pack.get("derived_from_validation_fixture_ref"))
    if not fixture or fixture.get("fixture_kind") != "POSITIVE_COMPLETE_VALIDATION_ONLY":
        add_error(errors, "E_PACK_FIXTURE", pack_id, str(pack.get("derived_from_validation_fixture_ref")))
    elif pack.get("parent_fixture_digest") != fixture.get("fixture_digest"):
        add_error(errors, "E_PACK_FIXTURE_DIGEST", pack_id, str(pack.get("parent_fixture_digest")))
    if pack.get("visible_disclosure", {}).get("text") != VISIBLE_DISCLOSURE_TEXT:
        add_error(errors, "E_PACK_DISCLOSURE", pack_id, str(pack.get("visible_disclosure")))


def validate_assignments(assignments: list[dict[str, Any]], packs_by_cp: dict[str, dict[str, Any]], errors: list[dict[str, str]]) -> None:
    if len(assignments) != 40:
        add_error(errors, "E_ASSIGNMENT_COUNT", "assignments", str(len(assignments)))
    counts = Counter(row.get("content_product_type_id") for row in assignments)
    if counts != {cp_id: 2 for cp_id in EXPECTED_CPS}:
        add_error(errors, "E_ASSIGNMENT_CP_COUNTS", "assignments", str(counts))
    lanes = Counter(row.get("voice_lane") for row in assignments)
    if lanes != {
        "ROLE_PROFESSIONAL_EXPRESSION": 20,
        "ROLE_GROUNDED_ORDINARY_PERSON": 19,
        "SENSORY_NONVERBAL_EXPRESSION": 1,
    }:
        add_error(errors, "E_ASSIGNMENT_LANES", "assignments", str(lanes))
    by_cp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in assignments:
        cp_id = row.get("content_product_type_id", "?")
        by_cp[cp_id].append(row)
        if row.get("assignment_digest") != object_digest(row, {"assignment_digest"}):
            add_error(errors, "E_ASSIGNMENT_DIGEST", row.get("assignment_id", "?"), "digest mismatch")
        if row.get("task_id") != TASK_ID or row.get("difference_axis_count_min") < 4:
            add_error(errors, "E_ASSIGNMENT_SCHEMA", row.get("assignment_id", "?"), str(row))
        pack = packs_by_cp.get(cp_id)
        if not pack or row.get("material_pack_ref") != pack["pack_id"] or row.get("material_pack_digest") != pack["pack_digest"]:
            add_error(errors, "E_ASSIGNMENT_PACK", row.get("assignment_id", "?"), str(row))
        if row.get("semantic_reroll_allowed") is not False or row.get("replacement_asset_id_allowed") is not False:
            add_error(errors, "E_ASSIGNMENT_REROLL", row.get("assignment_id", "?"), str(row))
        if row.get("frozen_before_authoring") is not True:
            add_error(errors, "E_ASSIGNMENT_FREEZE", row.get("assignment_id", "?"), str(row))
    for cp_id, rows in by_cp.items():
        if len(rows) != 2:
            continue
        rows = sorted(rows, key=lambda item: item["lane_code"])
        diff_fields = {
            "voice_lane",
            "platform_target",
            "narrative_device",
            "opening_family",
            "information_order",
            "reasoning_shape",
            "language_register",
            "visual_audio_grammar",
            "closing_family",
            "spoken_line_allowed",
            "CTA_allowed",
        }
        diff_count = sum(rows[0].get(field) != rows[1].get(field) for field in diff_fields)
        if diff_count < 4:
            add_error(errors, "E_ASSIGNMENT_AXIS_COUNT", cp_id, str(diff_count))
    cp14_b = [row for row in assignments if row.get("content_product_type_id") == "CP14" and row.get("lane_code") == "B"]
    if len(cp14_b) != 1 or cp14_b[0].get("spoken_line_allowed") is not False or cp14_b[0].get("CTA_allowed") is not False:
        add_error(errors, "E_CP14_ASSIGNMENT", "assignments", str(cp14_b))


def validate_plans(
    plans: list[dict[str, Any]],
    assignments_by_id: dict[str, dict[str, Any]],
    packs_by_id: dict[str, dict[str, Any]],
    validation_by_cp: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    if len(plans) != 40:
        add_error(errors, "E_PLAN_COUNT", "plans", str(len(plans)))
    for plan in plans:
        plan_id = plan.get("plan_id", "?")
        assignment = assignments_by_id.get(plan.get("assignment_ref"))
        pack = packs_by_id.get(plan.get("material_pack_ref"))
        cp_id = assignment.get("content_product_type_id") if assignment else "?"
        source = validation_by_cp.get(cp_id)
        if plan.get("plan_digest") != object_digest(plan, {"plan_digest"}):
            add_error(errors, "E_PLAN_DIGEST", plan_id, "digest mismatch")
        expected = {
            "task_id": TASK_ID,
            "plan_type": "ORCHQualificationCompositionPlan",
            "plan_mode": "QUALIFICATION_SYNTHETIC",
            "namespace": QUALIFICATION_NAMESPACE,
            "qualification_plan_namespace": "CANONICAL_QUALIFICATION_COMPOSITION_PLAN",
            "writer": "ORCH",
            "canonicality_scope": "QUALIFICATION_ONLY",
        }
        for key, value in expected.items():
            if plan.get(key) != value:
                add_error(errors, "E_PLAN_MODE", plan_id, f"{key}={plan.get(key)}")
        if not assignment or plan.get("assignment_digest") != assignment.get("assignment_digest"):
            add_error(errors, "E_PLAN_ASSIGNMENT", plan_id, str(plan.get("assignment_ref")))
        if not pack or plan.get("material_pack_digest") != pack.get("pack_digest"):
            add_error(errors, "E_PLAN_PACK", plan_id, str(plan.get("material_pack_ref")))
        if not source or plan.get("derived_validation_plan_ref") != source.get("plan_id"):
            add_error(errors, "E_PLAN_SOURCE", plan_id, str(plan.get("derived_validation_plan_ref")))
        elif plan.get("selected_components") != source.get("selected_components"):
            add_error(errors, "E_PLAN_COMPONENTS", plan_id, "selected components drift")
        lifecycle = plan.get("lifecycle", {})
        for key in [
            "canonical_within_qualification_namespace",
            "qualification_consumable",
        ]:
            if lifecycle.get(key) is not True:
                add_error(errors, "E_PLAN_LIFECYCLE", plan_id, f"{key}={lifecycle.get(key)}")
        for key in [
            "runtime_consumable",
            "production_consumable",
            "publishable",
            "runtime_authoritative",
            "production_executable",
            "runtime_ingest_ready",
            "dify_consumable",
        ]:
            if lifecycle.get(key) is not False:
                add_error(errors, "E_PLAN_LIFECYCLE", plan_id, f"{key}={lifecycle.get(key)}")
        bindings = plan.get("synthetic_bindings", {})
        if bindings.get("all_fixture_only") is not True or bindings.get("synthetic_qualification_only") is not True:
            add_error(errors, "E_PLAN_SYNTHETIC_BINDING", plan_id, str(bindings))
        for key in ["verified_brand_fact_count", "verified_authorization_count", "GRANTED_VERIFIED_authorization_count", "real_event_binding_count"]:
            if bindings.get(key) != 0:
                add_error(errors, "E_PLAN_SYNTHETIC_BINDING", plan_id, f"{key}={bindings.get(key)}")
        contract = plan.get("output_contract", {})
        if contract.get("audience_facing_output_allowed") is not False or contract.get("surface_unit_exact_join_required") is not True:
            add_error(errors, "E_PLAN_OUTPUT_CONTRACT", plan_id, str(contract))
        if cp_id == "CP14" and assignment and assignment.get("lane_code") == "B":
            if contract.get("spoken_line_payload_allowed") is not False or contract.get("CTA_payload_allowed") is not False:
                add_error(errors, "E_CP14_PLAN_CONTRACT", plan_id, str(contract))


def validate_instructions(
    instructions: list[dict[str, Any]],
    assignments_by_id: dict[str, dict[str, Any]],
    plans_by_id: dict[str, dict[str, Any]],
    packs_by_id: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    if len(instructions) != 40:
        add_error(errors, "E_INSTRUCTION_COUNT", "instructions", str(len(instructions)))
    for instruction in instructions:
        instruction_id = instruction.get("instruction_id", "?")
        assignment = assignments_by_id.get(instruction.get("assignment_id"))
        plan = plans_by_id.get(instruction.get("qualification_plan_ref"))
        pack = packs_by_id.get(instruction.get("material_pack_ref"))
        if instruction.get("instruction_digest") != object_digest(instruction, {"instruction_digest"}):
            add_error(errors, "E_INSTRUCTION_DIGEST", instruction_id, "digest mismatch")
        if instruction.get("authoring_mode") != "CONTROLLED_EXECUTION_AGENT_QUALIFICATION":
            add_error(errors, "E_INSTRUCTION_MODE", instruction_id, str(instruction.get("authoring_mode")))
        if instruction.get("external_provider_adapter_enabled") is not False:
            add_error(errors, "E_INSTRUCTION_PROVIDER", instruction_id, "adapter enabled")
        if instruction.get("external_provider_request_count") != 0 or instruction.get("credential_read_count") != 0:
            add_error(errors, "E_INSTRUCTION_PROVIDER", instruction_id, str(instruction))
        if not assignment or instruction.get("assignment_digest") != assignment.get("assignment_digest"):
            add_error(errors, "E_INSTRUCTION_ASSIGNMENT", instruction_id, str(instruction.get("assignment_id")))
        if not plan or instruction.get("qualification_plan_digest") != plan.get("plan_digest"):
            add_error(errors, "E_INSTRUCTION_PLAN", instruction_id, str(instruction.get("qualification_plan_ref")))
        if not pack or instruction.get("material_pack_digest") != pack.get("pack_digest"):
            add_error(errors, "E_INSTRUCTION_PACK", instruction_id, str(instruction.get("material_pack_ref")))
        body = instruction.get("instruction", {})
        expected = {
            "read_one_plan_only": True,
            "do_not_modify_plan": True,
            "do_not_add_input_fact": True,
            "visible_wrapper_required": VISIBLE_DISCLOSURE_TEXT,
            "surface_unit_exact_join_required_for_all_surfaces": True,
            "machine_max_acceptance_state": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN",
            "guardian_full_text_semantic_review_required": True,
        }
        for key, value in expected.items():
            if body.get(key) != value:
                add_error(errors, "E_INSTRUCTION_CONTRACT", instruction_id, f"{key}={body.get(key)}")


def surface_expectations(candidate: dict[str, Any]) -> dict[str, str]:
    audience = candidate.get("audience_form_candidate", {})
    execution = candidate.get("execution_payload", {})
    expected: dict[str, str] = {"audience_form_candidate.title": audience.get("title", "")}
    for index, line in enumerate(audience.get("body", "").split("\n")):
        expected[f"audience_form_candidate.body[{index}]"] = line
    for index, line in enumerate(audience.get("spoken_lines", [])):
        expected[f"audience_form_candidate.spoken_lines[{index}]"] = line
    if audience.get("CTA"):
        expected["audience_form_candidate.CTA"] = audience["CTA"]
    for key in ["visual_beats", "capture_instructions"]:
        for index, line in enumerate(execution.get(key, [])):
            expected[f"execution_payload.{key}[{index}]"] = line
    for key in ["audio_grammar", "editing_grammar"]:
        expected[f"execution_payload.{key}"] = execution.get(key, "")
    return expected


def validate_surface_units(candidate: dict[str, Any], errors: list[dict[str, str]]) -> None:
    asset_id = candidate.get("asset_id", "?")
    expected = surface_expectations(candidate)
    units = candidate.get("surface_units", [])
    by_path: dict[str, str] = {}
    for unit in units:
        field_path = unit.get("field_path")
        text = unit.get("text")
        if not isinstance(field_path, str) or not isinstance(text, str):
            add_error(errors, "E_SURFACE_UNIT_SHAPE", asset_id, str(unit))
            continue
        if field_path in by_path:
            add_error(errors, "E_SURFACE_DUPLICATE", asset_id, field_path)
        by_path[field_path] = text
        if unit.get("claim_boundary_route") != "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN":
            add_error(errors, "E_SURFACE_ROUTE", asset_id, str(unit))
        refs = unit.get("source_refs", [])
        if not refs:
            add_error(errors, "E_SOURCE_REFS", asset_id, field_path)
        for ref in refs:
            if not str(ref.get("source_ref", "")).startswith("fixture://qualification/"):
                add_error(errors, "E_SOURCE_NAMESPACE", asset_id, str(ref))
            if sha256_text(ref.get("source_text", "")) != ref.get("source_digest"):
                add_error(errors, "E_SOURCE_DIGEST", asset_id, str(ref))
        if unit.get("semantic_license") != "NONFACTUAL_CREATIVE_EXPRESSION":
            if not unit.get("authorization_refs") or not unit.get("fact_slot_refs"):
                add_error(errors, "E_SURFACE_BINDING", asset_id, field_path)
        for atom in unit.get("assertion_atoms", []):
            if atom.get("requires_evidence") is not True:
                add_error(errors, "E_ASSERTION_ATOM", asset_id, str(atom))
    if by_path != expected:
        missing = sorted(set(expected) - set(by_path))
        extra = sorted(set(by_path) - set(expected))
        mismatched = sorted(path for path in set(expected) & set(by_path) if expected[path] != by_path[path])
        add_error(errors, "E_SURFACE_JOIN", asset_id, f"missing={missing} extra={extra} mismatch={mismatched}")


def validate_candidates(
    candidates: list[dict[str, Any]],
    assignments_by_id: dict[str, dict[str, Any]],
    plans_by_id: dict[str, dict[str, Any]],
    instructions_by_id: dict[str, dict[str, Any]],
    packs_by_id: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    if len(candidates) != 40:
        add_error(errors, "E_CANDIDATE_COUNT", "candidates", str(len(candidates)))
    ids = [row.get("asset_id") for row in candidates]
    if len(set(ids)) != len(ids):
        add_error(errors, "E_CANDIDATE_DUPLICATE", "candidates", str([item for item, count in Counter(ids).items() if count > 1]))
    cp_counts = Counter(row.get("content_product_type_id") for row in candidates)
    if cp_counts != {cp_id: 2 for cp_id in EXPECTED_CPS}:
        add_error(errors, "E_CANDIDATE_CP_COUNTS", "candidates", str(cp_counts))
    for candidate in candidates:
        asset_id = candidate.get("asset_id", "?")
        assignment = assignments_by_id.get(candidate.get("assignment_id"))
        plan = plans_by_id.get(candidate.get("qualification_plan_ref"))
        instruction = instructions_by_id.get(candidate.get("instruction_ref"))
        pack = packs_by_id.get(candidate.get("material_pack_ref"))
        if candidate.get("candidate_digest") != object_digest(candidate, {"candidate_digest"}):
            add_error(errors, "E_CANDIDATE_DIGEST", asset_id, "digest mismatch")
        if candidate.get("task_id") != TASK_ID or candidate.get("schema_version") != "v0.1":
            add_error(errors, "E_CANDIDATE_SCHEMA", asset_id, str(candidate))
        if candidate.get("acceptance_state") != "STRUCTURAL_REVIEW_PENDING":
            add_error(errors, "E_CANDIDATE_STATE", asset_id, str(candidate.get("acceptance_state")))
        if not assignment or candidate.get("assignment_digest") != assignment.get("assignment_digest"):
            add_error(errors, "E_CANDIDATE_ASSIGNMENT", asset_id, str(candidate.get("assignment_id")))
        elif candidate.get("asset_id") != assignment.get("asset_id") or candidate.get("voice_lane") != assignment.get("voice_lane"):
            add_error(errors, "E_CANDIDATE_ASSIGNMENT", asset_id, str(assignment))
        if not plan or candidate.get("qualification_plan_digest") != plan.get("plan_digest"):
            add_error(errors, "E_CANDIDATE_PLAN", asset_id, str(candidate.get("qualification_plan_ref")))
        if not instruction or candidate.get("instruction_digest") != instruction.get("instruction_digest"):
            add_error(errors, "E_CANDIDATE_INSTRUCTION", asset_id, str(candidate.get("instruction_ref")))
        if not pack or candidate.get("material_pack_digest") != pack.get("pack_digest"):
            add_error(errors, "E_CANDIDATE_PACK", asset_id, str(candidate.get("material_pack_ref")))
        wrapper = candidate.get("qualification_wrapper")
        if not isinstance(wrapper, dict):
            add_error(errors, "E_CANDIDATE_WRAPPER", asset_id, "missing")
        else:
            expected_wrapper = {
                "synthetic_case": True,
                "qualification_only": True,
                "nonpublishable": True,
                "runtime_consumable": False,
                "production_consumable": False,
                "may_enter_KE_RAG_DIFY": False,
                "may_be_published": False,
                "visible_text": VISIBLE_DISCLOSURE_TEXT,
            }
            for key, value in expected_wrapper.items():
                if wrapper.get(key) != value:
                    add_error(errors, "E_CANDIDATE_WRAPPER", asset_id, f"{key}={wrapper.get(key)}")
        if candidate.get("surface_unit_exact_join_pass") is not True:
            add_error(errors, "E_CANDIDATE_SURFACE_FLAG", asset_id, "exact join not true")
        if candidate.get("untracked_surface_text_count") != 0 or candidate.get("unclassified_surface_unit_count") != 0:
            add_error(errors, "E_CANDIDATE_SURFACE_COUNTS", asset_id, str(candidate))
        validate_surface_units(candidate, errors)
        cp_id = candidate.get("content_product_type_id")
        if cp_id == "CP14" and assignment and assignment.get("lane_code") == "B":
            audience = candidate.get("audience_form_candidate", {})
            if audience.get("spoken_lines") != [] or audience.get("CTA") != "":
                add_error(errors, "E_CP14_SURFACE", asset_id, str(audience))
        if recursive_true_flags(candidate):
            add_error(errors, "E_CANDIDATE_READY_TRUE", asset_id, str(recursive_true_flags(candidate)))
        if recursive_nonzero_counts(candidate):
            add_error(errors, "E_CANDIDATE_NONZERO", asset_id, str(recursive_nonzero_counts(candidate)))


def validate_acceptance_and_result(root: Path, snapshot: dict[str, Any], errors: list[dict[str, str]]) -> None:
    candidates = snapshot["candidates"]
    acceptance = snapshot["acceptance"]
    result = snapshot["result"]
    packet = snapshot["packet"]
    if len(acceptance) != 44:
        add_error(errors, "E_ACCEPTANCE_ROW_COUNT", "acceptance", str(len(acceptance)))
    kind_counts = Counter(row.get("record_kind") for row in acceptance)
    if kind_counts != {"candidate_machine_acceptance": 40, "checkpoint_summary": 4}:
        add_error(errors, "E_ACCEPTANCE_KIND_COUNTS", "acceptance", str(kind_counts))
    candidate_by_id = {row["asset_id"]: row for row in candidates}
    for row in acceptance:
        if row.get("result_digest") != object_digest(row, {"result_digest"}):
            add_error(errors, "E_ACCEPTANCE_DIGEST", row.get("asset_id", row.get("checkpoint_id", "?")), "digest mismatch")
        if row.get("task_id") != TASK_ID:
            add_error(errors, "E_ACCEPTANCE_TASK", row.get("record_kind", "?"), str(row.get("task_id")))
        if row.get("record_kind") == "candidate_machine_acceptance":
            candidate = candidate_by_id.get(row.get("asset_id"))
            if not candidate or row.get("candidate_digest") != candidate.get("candidate_digest"):
                add_error(errors, "E_ACCEPTANCE_CANDIDATE", row.get("asset_id", "?"), str(row))
            if row.get("machine_acceptance_state") != "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN":
                add_error(errors, "E_ACCEPTANCE_STATE", row.get("asset_id", "?"), str(row))
            if row.get("Guardian_full_text_semantic_review_required") is not True:
                add_error(errors, "E_ACCEPTANCE_GUARDIAN", row.get("asset_id", "?"), str(row))
            if row.get("full_free_text_fabrication_detection_proven") is not False:
                add_error(errors, "E_ACCEPTANCE_FABRICATION_CLAIM", row.get("asset_id", "?"), str(row))
            for key in [
                "unsupported_assertion_count",
                "untracked_surface_text_count",
                "unclassified_surface_unit_count",
                "synthetic_runtime_leak_count",
                "invalid_fact_or_authorization_count",
                "provider_request_count",
                "provider_api_call_count",
                "accepted_content_count",
                "published_content_count",
            ]:
                if row.get(key) != 0:
                    add_error(errors, "E_ACCEPTANCE_ZERO", row.get("asset_id", "?"), f"{key}={row.get(key)}")
        if row.get("record_kind") == "checkpoint_summary":
            if row.get("candidate_count") != 10 or row.get("machine_structural_pass_count") != 10:
                add_error(errors, "E_CHECKPOINT_SUMMARY", row.get("checkpoint_id", "?"), str(row))
            if row.get("machine_hold_or_reject_count") != 0 or row.get("replacement_asset_id_count") != 0:
                add_error(errors, "E_CHECKPOINT_SUMMARY", row.get("checkpoint_id", "?"), str(row))
    if result.get("result_digest") != object_digest(result, {"result_digest"}):
        add_error(errors, "E_RESULT_DIGEST", "result", "digest mismatch")
    phase0 = result.get("phase_0", {})
    expected_phase0 = {
        "generator_PR_5_merged": True,
        "merge_method": "merge_commit",
        "merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
        "merge_tree_sha": PHASE0_MERGE_TREE_SHA,
        "reviewed_base_parent_present": True,
        "reviewed_head_parent_present": True,
        "merge_tree_equals_reviewed_head_tree": True,
        "master_required_checks_green": True,
        "local_remote_master_match": True,
    }
    for key, value in expected_phase0.items():
        if phase0.get(key) != value:
            add_error(errors, "E_RESULT_PHASE0", "result", f"{key}={phase0.get(key)}")
    if phase0.get("review_binding") != {
        "reviewed_base_sha": REVIEWED_BASE_SHA,
        "reviewed_head_sha": REVIEWED_HEAD_SHA,
        "reviewed_head_tree_sha": REVIEWED_HEAD_TREE_SHA,
        "reviewed_full_diff_digest": REVIEWED_FULL_DIFF_DIGEST,
        "guardian_verdict": "PASS",
    }:
        add_error(errors, "E_RESULT_REVIEW_BINDING", "result", str(phase0.get("review_binding")))
    expected_counts = {
        ("probe", "planned_count"): 40,
        ("probe", "generated_candidate_count"): 40,
        ("probe", "machine_structural_pass_count"): 40,
        ("probe", "machine_hold_or_reject_count"): 0,
        ("truth", "synthetic_qualification_pack_count"): 20,
        ("generation", "execution_AI_authored_count"): 40,
        ("integrity", "qualification_material_pack_count"): 20,
        ("integrity", "qualification_assignment_count"): 40,
        ("integrity", "canonical_qualification_composition_plan_count"): 40,
        ("integrity", "canonical_validation_composition_plan_count"): 20,
        ("integrity", "assignment_replacement_count"): 0,
        ("integrity", "alternative_candidate_generation_count"): 0,
        ("integrity", "semantic_reroll_count"): 0,
        ("integrity", "candidate_overflow_count"): 0,
    }
    for (section, key), value in expected_counts.items():
        if result.get(section, {}).get(key) != value:
            add_error(errors, "E_RESULT_COUNTS", "result", f"{section}.{key}={result.get(section, {}).get(key)}")
    if result.get("integrity", {}).get("full_free_text_fabrication_detection_proven") is not False:
        add_error(errors, "E_RESULT_FABRICATION_CLAIM", "result", str(result.get("integrity")))
    if result.get("integrity", {}).get("Guardian_full_text_semantic_review_required") is not True:
        add_error(errors, "E_RESULT_GUARDIAN_REQUIRED", "result", str(result.get("integrity")))
    if recursive_true_flags(result) or recursive_nonzero_counts(result):
        add_error(errors, "E_RESULT_BOUNDARY", "result", str(recursive_true_flags(result) + recursive_nonzero_counts(result)))
    digests = result.get("generated_file_digests", {})
    expected_digest_paths = {path.as_posix() for path in EXPECTED_GENERATED_DIGEST_PATHS}
    if set(digests) != expected_digest_paths:
        add_error(errors, "E_RESULT_DIGEST_PATHS", "result", str(sorted(set(digests) ^ expected_digest_paths)))
    for path_text, digest in digests.items():
        path = Path(path_text)
        if path in {CHECKER_PATH, GENERATOR_ENTRY_PATH}:
            historical_text = git(root, ["show", f"{QUALIFICATION_PROBE_AS_BUILT_HEAD_SHA}:{path.as_posix()}"])
            if not historical_text or sha256_text(historical_text) != digest:
                add_error(errors, "E_RESULT_FILE_DIGEST", "result", f"historical {path_text}")
            continue
        if path.exists() and sha256_file(path) != digest:
            add_error(errors, "E_RESULT_FILE_DIGEST", "result", path_text)
    if packet.get("packet_digest") != object_digest(packet, {"packet_digest"}):
        add_error(errors, "E_PACKET_DIGEST", "packet", "digest mismatch")
    if packet.get("guardian_must_read_full_surface_40_of_40") is not True:
        add_error(errors, "E_PACKET_GUARDIAN_SCOPE", "packet", str(packet))
    surfaces = set(packet.get("surfaces_to_read", []))
    required_surfaces = {"title", "body", "spoken_lines", "CTA", "visual_beats", "capture_instructions", "audio_grammar", "editing_grammar", "surface_units"}
    if not required_surfaces <= surfaces:
        add_error(errors, "E_PACKET_SURFACES", "packet", str(sorted(required_surfaces - surfaces)))


def validate_artifacts(snapshot: dict[str, Any], errors: list[dict[str, str]]) -> None:
    validate_input_baseline(snapshot, errors)
    fixtures_by_id = {row["fixture_id"]: row for row in snapshot["fixtures"]}
    packs = snapshot["packs"]
    assignments = snapshot["assignments"]
    plans = snapshot["plans"]
    instructions = snapshot["instructions"]
    candidates = snapshot["candidates"]
    if len(packs) != 20:
        add_error(errors, "E_PACK_COUNT", "packs", str(len(packs)))
    if len({row.get("topic_signature") for row in packs}) != 20:
        add_error(errors, "E_PACK_TOPIC_SIGNATURE", "packs", "not unique")
    for pack in packs:
        validate_pack(pack, fixtures_by_id, errors)
    packs_by_cp = {row["content_product_type_id"]: row for row in packs}
    packs_by_id = {row["pack_id"]: row for row in packs}
    validate_assignments(assignments, packs_by_cp, errors)
    assignments_by_id = {row["assignment_id"]: row for row in assignments}
    validation_by_cp = {row["content_product"]["primary_content_product_type_id"]: row for row in snapshot["validation_plans"]}
    validate_plans(plans, assignments_by_id, packs_by_id, validation_by_cp, errors)
    plans_by_id = {row["plan_id"]: row for row in plans}
    validate_instructions(instructions, assignments_by_id, plans_by_id, packs_by_id, errors)
    instructions_by_id = {row["instruction_id"]: row for row in instructions}
    validate_candidates(candidates, assignments_by_id, plans_by_id, instructions_by_id, packs_by_id, errors)
    validate_acceptance_and_result(Path.cwd(), snapshot, errors)


def validate_ci(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / CI_PATH).read_text(encoding="utf-8")
    required = [
        "python3 ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py",
        "python3 ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py --selftest",
        "python3 controlled_content_generator_v2_001/qualification_probe_40_001/run_qualification_probe_40_orch_materializer.py --check",
        "python3 controlled_content_generator_v2_001/qualification_probe_40_001/run_qualification_probe_40_generator_acceptance.py --check",
    ]
    for snippet in required:
        if snippet not in text:
            add_error(errors, "E_CI_REGISTRATION", "ci", snippet)
    loop = text.split("Verify fail-closed optimized mode", 1)[-1]
    if "check_controlled_v2_20cp_qualification_probe_40.py --selftest" not in loop:
        add_error(errors, "E_CI_OPTIMIZED_MODE", "ci", "new checker selftest absent from -O loop")


def validate_checker_independence(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / CHECKER_PATH).read_text(encoding="utf-8")
    forbidden = [
        "import " + "run_qualification_probe_40",
        "from " + "controlled_content_generator_v2_001.qualification_probe_40_001",
        "run_qualification_probe_40_generator_acceptance" + " import",
        "run_qualification_probe_40_orch_materializer" + " import",
    ]
    for token in forbidden:
        if token in text:
            add_error(errors, "E_CHECKER_ORACLE_IMPORT", "checker", token)


def validate_ledger(root: Path, result: dict[str, Any], errors: list[dict[str, str]], enforce_git: bool) -> None:
    data = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    migration = data.get("route_migration_27")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_ROUTE27", "ledger", "missing")
        return
    if migration.get("applied_by_task") != TASK_ID:
        add_error(errors, "E_LEDGER_TASK", "ledger", str(migration.get("applied_by_task")))
    if migration.get("additive_only") is not True or migration.get("no_readiness_flipped") is not True:
        add_error(errors, "E_LEDGER_DECLARATION", "ledger", str(migration))
    probe = migration.get("qualification_probe_40", {})
    expected = {
        "generated_candidate_count": 40,
        "machine_structural_pass_count": 40,
        "machine_hold_or_reject_count": 0,
        "synthetic_qualification_pack_count": 20,
        "canonical_qualification_composition_plan_count": 40,
        "external_provider_request_count": 0,
        "external_provider_API_call_count": 0,
        "credential_read_count": 0,
        "generator_qualified": False,
        "runtime_provider_adapter_qualified": False,
        "baseline_increment_count": 0,
        "accepted_baseline_after": 120,
        "target_baseline": 300,
    }
    for key, value in expected.items():
        if probe.get(key) != value:
            add_error(errors, "E_LEDGER_PROBE", "ledger", f"{key}={probe.get(key)}")
    if probe.get("result_digest") != result.get("result_digest"):
        add_error(errors, "E_LEDGER_RESULT_DIGEST", "ledger", str(probe.get("result_digest")))
    if migration.get("migration_digest") != object_digest(migration, {"migration_digest"}):
        add_error(errors, "E_LEDGER_DIGEST", "ledger", "digest mismatch")
    if enforce_git:
        old_text = git(root, ["show", f"{PHASE0_MERGE_COMMIT_SHA}:{LEDGER_PATH.as_posix()}"])
        if old_text:
            old_data = yaml.safe_load(old_text)["grc_3600_execution_plan_status"]
            for key, old_value in old_data.items():
                if data.get(key) != old_value:
                    add_error(errors, "E_LEDGER_PRIOR_MUTATION", "ledger", key)


def run_all(root: Path, enforce_git: bool) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    validate_preflight(root, errors, enforce_git)
    snapshot = load_snapshot(root)
    validate_artifacts(snapshot, errors)
    validate_ci(root, errors)
    validate_checker_independence(root, errors)
    validate_ledger(root, snapshot["result"], errors, enforce_git)
    return errors


def selftest() -> int:
    root = Path.cwd()
    snapshot = load_snapshot(root)
    errors: list[dict[str, str]] = []
    validate_artifacts(snapshot, errors)
    if errors:
        print("SELFTEST_BASE_INVALID", json.dumps(errors[:5], ensure_ascii=False), file=sys.stderr)
        return 1

    tests: list[tuple[str, str, Any]] = [
        (
            "reject_validation_plan_mode",
            "E_PLAN_MODE",
            lambda snap: snap["plans"][0].__setitem__("plan_mode", "VALIDATION_SYNTHETIC"),
        ),
        (
            "reject_generator_plan_writer",
            "E_PLAN_MODE",
            lambda snap: snap["plans"][0].__setitem__("writer", "GENERATOR"),
        ),
        (
            "reject_runtime_plan",
            "E_PLAN_LIFECYCLE",
            lambda snap: snap["plans"][0]["lifecycle"].__setitem__("runtime_consumable", True),
        ),
        (
            "reject_verified_synthetic_fact",
            "E_PLAN_SYNTHETIC_BINDING",
            lambda snap: snap["plans"][0]["synthetic_bindings"].__setitem__("verified_brand_fact_count", 1),
        ),
        (
            "reject_missing_candidate_wrapper",
            "E_CANDIDATE_WRAPPER",
            lambda snap: snap["candidates"][0].pop("qualification_wrapper", None),
        ),
        (
            "reject_unbound_surface_unit",
            "E_SOURCE_REFS",
            lambda snap: snap["candidates"][0]["surface_units"][0].__setitem__("source_refs", []),
        ),
        (
            "reject_untracked_body_text",
            "E_SURFACE_JOIN",
            lambda snap: snap["candidates"][0]["audience_form_candidate"].__setitem__(
                "body", snap["candidates"][0]["audience_form_candidate"]["body"] + "\n未声明新增句。"
            ),
        ),
        (
            "reject_cp14_b_spoken",
            "E_CP14_SURFACE",
            lambda snap: next(
                row for row in snap["candidates"] if row["asset_id"] == "QPROBE-CP14-B-001"
            )["audience_form_candidate"].__setitem__("spoken_lines", ["不该出现的口播"]),
        ),
        (
            "reject_candidate_overflow",
            "E_CANDIDATE_COUNT",
            lambda snap: snap["candidates"].append(copy.deepcopy(snap["candidates"][0])),
        ),
        (
            "reject_generator_qualified",
            "E_RESULT_BOUNDARY",
            lambda snap: snap["result"]["qualification"].__setitem__("generator_qualified", True),
        ),
        (
            "reject_baseline_increment",
            "E_RESULT_BOUNDARY",
            lambda snap: snap["result"]["counting"].__setitem__("baseline_increment_count", 1),
        ),
        (
            "reject_checkpoint_reroll",
            "E_CHECKPOINT_SUMMARY",
            lambda snap: next(
                row for row in snap["acceptance"] if row["record_kind"] == "checkpoint_summary"
            ).__setitem__("replacement_asset_id_count", 1),
        ),
    ]
    for name, expected_code, mutator in tests:
        mutated = copy.deepcopy(snapshot)
        mutator(mutated)
        test_errors: list[dict[str, str]] = []
        validate_artifacts(mutated, test_errors)
        codes = {error["code"] for error in test_errors}
        if expected_code not in codes:
            print(f"SELFTEST_FAIL {name}: expected {expected_code}, got {sorted(codes)}", file=sys.stderr)
            return 1
    print(f"{Path(__file__).name} SELFTEST_PASS {len(tests)} cases")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    root = Path.cwd()
    errors = run_all(root, enforce_git="--no-git" not in argv)
    if errors:
        for error in errors:
            print(json.dumps(error, ensure_ascii=False, sort_keys=True))
        return 1
    print("check_controlled_v2_20cp_qualification_probe_40 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
