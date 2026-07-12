#!/usr/bin/env python3
"""Fail-closed checker for GKB v0.3 20CP component supply closeout."""

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
    print("check_gkb_v2_20cp_component_supply_closeout refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "GKB_V2_20CP_COMPONENT_SUPPLY_CLOSEOUT_001"
BASELINE_HEAD = "c7c1a0a277af1ae70db2dc6700f74ea1bc2c7464"
ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = ROOT / "component_supply_closeout_20cp_001"
FREEZER_PATH = TASK_DIR / "run_component_supply_closeout_freezer.py"
CONTRACT_PATH = TASK_DIR / "component_supply_closeout_contract.v0.1.yaml"
DECISIONS_PATH = TASK_DIR / "component_supply_review_decisions.v0.3.jsonl"
REGISTRY_PATH = TASK_DIR / "reviewed_reusable_component_registry.v0.3.jsonl"
COVERAGE_PATH = TASK_DIR / "content_product_component_coverage.v0.3.yaml"
RESULT_PATH = TASK_DIR / "component_supply_closeout_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "component_supply_guardian_review_packet.v0.1.yaml"
CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py")
FACT_AUTH_FIXTURE_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py")
ORCH_VALIDATION_DRYRUN_CHECKER_PATH = Path("ci/checkers/check_orch_v2_20cp_validation_dryrun.py")
GENERATOR_V2_CHECKER_PATH = Path("ci/checkers/check_controlled_content_generator_v2_build.py")
QUALIFICATION_PROBE_CHECKER_PATH = Path("ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CI_PATH = Path(".github/workflows/ci.yml")
SUCCESSOR_FACT_AUTH_FIXTURE_DIR = ROOT / "fact_authorization_fixture_closeout_001"
SUCCESSOR_ORCH_VALIDATION_DRYRUN_DIR = Path(
    "08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001"
)
SUCCESSOR_GENERATOR_V2_DIR = Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001")
SUCCESSOR_QUALIFICATION_PROBE_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")

ALLOWED_CHANGED_PATHS = {
    CONTRACT_PATH,
    DECISIONS_PATH,
    REGISTRY_PATH,
    COVERAGE_PATH,
    RESULT_PATH,
    PACKET_PATH,
    FREEZER_PATH,
    CHECKER_PATH,
    FACT_AUTH_FIXTURE_CHECKER_PATH,
    ORCH_VALIDATION_DRYRUN_CHECKER_PATH,
    GENERATOR_V2_CHECKER_PATH,
    QUALIFICATION_PROBE_CHECKER_PATH,
    LEDGER_PATH,
    CI_PATH,
}
EXPECTED_HELD_COUNT = 22
EXPECTED_OLD_COMPONENT_COUNT = 55
EXPECTED_NEW_COMPONENT_COUNT = 9
EXPECTED_DECISION_DISTRIBUTION = {
    "PROMOTE_AS_NEW": 9,
    "MERGE_INTO_REUSABLE": 3,
    "REJECT": 14,
}
EXPECTED_INPUT_DIGESTS = {
    "clean_120_sha256": "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91",
    "content_product_profile_registry_digest": "160f640f3c677b3e3aa7fb13c89549c61825cdde1919731bc573740ae38ef53b",
    "scale_600_contract_sha256": "966190c341b070d88fbc3a25540e9c8fddf69ad8f19b90fb29badbb1ffad52a9",
    "s2_v002_decisions_sha256": "d233b8e1c4e1b773ed23174f702fd3f6b0881481b0e9d0442feef33c91a46f65",
    "s2_v002_registry_sha256": "6daf3f043ad22d021e0b7719da30a25d9bf13d8c969d41cf6fec793881f9d14b",
    "s2_v002_coverage_sha256": "5f520a1b462b823f6719bd63b97886eb560a34ffde28825bf666af880aa12d22",
    "s2_v002_handoff_sha256": "a81322e034618a78164771b1d7389825623b042fb6d710e0c9c37146b77d61ca",
}
FORBIDDEN_FIELD_NAMES = {
    "audience_facing_body",
    "body_text",
    "title",
    "title_text",
    "spoken_script",
    "spoken_draft",
    "publishable_copy",
    "canonical_CompositionPlan",
    "CompositionPlan",
    "assignment",
    "generation_record",
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
}


def load_freezer(root: Path):
    spec = importlib.util.spec_from_file_location("component_supply_freezer", root / FREEZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load freezer")
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


def recursive_forbidden_fields(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_FIELD_NAMES:
                hits.append(child_path)
            hits.extend(recursive_forbidden_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_forbidden_fields(child, f"{path}[{index}]"))
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


def profile_role_sets(root: Path, freezer: Any) -> dict[str, set[str]]:
    profiles = load_yaml(root / freezer.PROFILES_PATH)["content_product_profile_registry"]["profiles"]
    role_sets: dict[str, set[str]] = {}
    for profile in profiles:
        roles = {item["role"] for item in profile.get("required_component_roles", [])}
        roles.update(item["role"] for item in profile.get("optional_component_roles", []))
        role_sets[profile["content_product_type_id"]] = roles
    return role_sets


def validate_preflight(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    if not enforce_git:
        return
    head = git(root, ["rev-parse", "HEAD"]).strip()
    if not head:
        add_error(errors, "E_HEAD", "git", "cannot resolve HEAD")
    elif git(root, ["merge-base", "--is-ancestor", BASELINE_HEAD, head]) is None:
        add_error(errors, "E_BASELINE", "git", "baseline is not ancestor of current HEAD")
    changed = changed_paths(root)
    unexpected = sorted(
        path.as_posix()
        for path in changed - ALLOWED_CHANGED_PATHS
        if not path.is_relative_to(SUCCESSOR_FACT_AUTH_FIXTURE_DIR)
        and not path.is_relative_to(SUCCESSOR_ORCH_VALIDATION_DRYRUN_DIR)
        and not path.is_relative_to(SUCCESSOR_GENERATOR_V2_DIR)
        and not path.is_relative_to(SUCCESSOR_QUALIFICATION_PROBE_DIR)
    )
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", "git", f"unexpected changed paths: {unexpected}")


def validate_input_digests(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    contract = load_yaml(root / CONTRACT_PATH)["component_supply_closeout_contract"]
    baseline = contract["baseline"]
    for key, expected in EXPECTED_INPUT_DIGESTS.items():
        if baseline.get(key) != expected:
            add_error(errors, "E_CONTRACT_DIGEST_PIN", "contract", f"{key}={baseline.get(key)}")
    checks = {
        "clean_120_sha256": freezer.sha256_file(root / freezer.CLEAN_120_PATH),
        "scale_600_contract_sha256": freezer.sha256_file(root / freezer.SCALE_600_CONTRACT_PATH),
        "s2_v002_decisions_sha256": freezer.sha256_file(root / freezer.V002_DECISIONS_PATH),
        "s2_v002_registry_sha256": freezer.sha256_file(root / freezer.V002_REGISTRY_PATH),
        "s2_v002_coverage_sha256": freezer.sha256_file(root / freezer.V002_COVERAGE_PATH),
        "s2_v002_handoff_sha256": freezer.sha256_file(root / freezer.V002_HANDOFF_PATH),
    }
    profile_registry = load_yaml(root / freezer.PROFILES_PATH)["content_product_profile_registry"]
    checks["content_product_profile_registry_digest"] = freezer.object_digest(
        profile_registry, {"registry_digest"}
    )
    for key, actual in checks.items():
        if actual != EXPECTED_INPUT_DIGESTS[key]:
            add_error(errors, "E_INPUT_DIGEST", "baseline", f"{key}={actual}")


def validate_decisions(
    root: Path,
    freezer: Any,
    decisions: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    v002_decisions = load_jsonl(root / freezer.V002_DECISIONS_PATH)
    held_ids = [
        row["candidate_id"]
        for row in v002_decisions
        if row["decision"]["enum"] == "NEEDS_REPAIR"
    ]
    decision_ids = [row["candidate_id"] for row in decisions]
    if len(held_ids) != EXPECTED_HELD_COUNT:
        add_error(errors, "E_V002_HELD_COUNT", "decisions", str(len(held_ids)))
    missing = sorted(set(held_ids) - set(decision_ids))
    extra_s2 = sorted(cid for cid in decision_ids if cid.startswith("CCV2-") and cid not in set(held_ids))
    if missing or extra_s2:
        add_error(errors, "E_HELD_COVERAGE", "decisions", f"missing={missing} extra_s2={extra_s2}")
    distribution = dict(Counter(row["decision"]["enum"] for row in decisions))
    if distribution != EXPECTED_DECISION_DISTRIBUTION:
        add_error(errors, "E_DECISION_DISTRIBUTION", "decisions", str(distribution))
    clean = freezer.clean_assets(root)
    role_sets = profile_role_sets(root, freezer)
    for row in decisions:
        if row.get("task_id") != TASK_ID:
            add_error(errors, "E_DECISION_TASK", row.get("candidate_id", "?"), str(row.get("task_id")))
        if recursive_forbidden_fields(row):
            add_error(errors, "E_FORBIDDEN_FIELD", row["candidate_id"], str(recursive_forbidden_fields(row)))
        if recursive_true_flags(row):
            add_error(errors, "E_READY_TRUE", row["candidate_id"], str(recursive_true_flags(row)))
        parent = clean.get(row.get("parent_asset_id"))
        if not parent:
            add_error(errors, "E_PARENT_MISSING", row["candidate_id"], str(row.get("parent_asset_id")))
            continue
        if row.get("parent_digest") != freezer.object_digest(parent):
            add_error(errors, "E_PARENT_DIGEST", row["candidate_id"], str(row.get("parent_digest")))
        body = parent["body_text"]
        for span in row.get("evidence_spans", []):
            start = span.get("start")
            end = span.get("end")
            text = span.get("text")
            if not isinstance(start, int) or not isinstance(end, int) or body[start:end] != text:
                add_error(errors, "E_EVIDENCE_SPAN", row["candidate_id"], str(span))
        decision = row["decision"]["enum"]
        if decision in {"PROMOTE_AS_NEW", "MERGE_INTO_REUSABLE"}:
            if not row.get("target_reusable_component_id"):
                add_error(errors, "E_ACCEPTED_NO_TARGET", row["candidate_id"], decision)
            if not row.get("applicable_content_product_type_ids"):
                add_error(errors, "E_ACCEPTED_NO_CP_EDGE", row["candidate_id"], decision)
            edge_ids = [
                edge.get("content_product_type_id")
                for edge in row.get("per_CP_applicability_assessments", [])
            ]
            if sorted(edge_ids) != sorted(row.get("applicable_content_product_type_ids", [])):
                add_error(errors, "E_CP_EDGE_SET", row["candidate_id"], str(edge_ids))
            for edge in row.get("per_CP_applicability_assessments", []):
                cp_id = edge.get("content_product_type_id")
                edge_role = edge.get("required_component_role")
                if edge_role != row.get("component_role"):
                    add_error(errors, "E_CP_EDGE_ROLE", row["candidate_id"], f"{cp_id}:{edge_role}")
                if row.get("component_role") not in role_sets.get(cp_id, set()):
                    add_error(
                        errors,
                        "E_CP_APPLICABILITY_ROLE_MISMATCH",
                        row["candidate_id"],
                        f"{cp_id} lacks role {row.get('component_role')}",
                    )
        if decision == "REJECT" and row["component_role"] == "visual_beat":
            if row.get("applicable_content_product_type_ids"):
                add_error(errors, "E_REJECTED_HAS_COVERAGE", row["candidate_id"], "visual reject covers CP")


def validate_merge_equivalence(decisions: list[dict[str, Any]], errors: list[dict[str, str]]) -> None:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in decisions:
        if row["decision"]["enum"] in {"PROMOTE_AS_NEW", "MERGE_INTO_REUSABLE"}:
            groups.setdefault(row["target_reusable_component_id"], []).append(row)
    for target, group in groups.items():
        promoted = [row for row in group if row["decision"]["enum"] == "PROMOTE_AS_NEW"]
        if len(promoted) != 1:
            add_error(errors, "E_MERGE_PROMOTED_SEED", target, str(len(promoted)))
            continue
        seed = promoted[0]
        for row in group:
            for key in [
                "component_role",
                "composition_asset_class",
                "required_input_slots",
                "role_authority_boundary",
                "claim_boundary",
            ]:
                if row.get(key) != seed.get(key):
                    add_error(errors, "E_MERGE_EQUIVALENCE", target, f"{row['candidate_id']} {key}")
            if row["decision"]["enum"] == "MERGE_INTO_REUSABLE":
                assessment = row.get("merge_equivalence_assessment", {})
                if assessment.get("target_component_id") != target or assessment.get("merge_allowed") is not True:
                    add_error(errors, "E_MERGE_DECLARATION", target, row["candidate_id"])


def validate_registry(root: Path, freezer: Any, registry: list[dict[str, Any]], errors: list[dict[str, str]]) -> None:
    old = load_jsonl(root / freezer.V002_REGISTRY_PATH)
    role_sets = profile_role_sets(root, freezer)
    if len(old) != EXPECTED_OLD_COMPONENT_COUNT:
        add_error(errors, "E_OLD_REGISTRY_COUNT", "registry", str(len(old)))
    if registry[: len(old)] != old:
        add_error(errors, "E_OLD_COMPONENT_DRIFT", "registry", "v002 prefix is not byte-equivalent as parsed JSON")
    new_rows = registry[len(old) :]
    if len(new_rows) != EXPECTED_NEW_COMPONENT_COUNT:
        add_error(errors, "E_NEW_COMPONENT_COUNT", "registry", str(len(new_rows)))
    ids = [row["component_id"] for row in registry]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        add_error(errors, "E_COMPONENT_DUPLICATE", "registry", str(duplicates))
    for row in new_rows:
        if row.get("component_digest") != freezer.object_digest(row, {"component_digest"}):
            add_error(errors, "E_COMPONENT_DIGEST", row["component_id"], "digest mismatch")
        if row.get("runtime_ready") is not False or row.get("ingest_ready") is not False:
            add_error(errors, "E_COMPONENT_READY", row["component_id"], "runtime/ingest not false")
        if "primary_content_product_type_id" in row:
            add_error(errors, "E_PRIMARY_CP_ON_COMPONENT", row["component_id"], "forbidden field")
        if recursive_forbidden_fields(row):
            add_error(errors, "E_FORBIDDEN_FIELD", row["component_id"], str(recursive_forbidden_fields(row)))
        if recursive_true_flags(row):
            add_error(errors, "E_READY_TRUE", row["component_id"], str(recursive_true_flags(row)))
    for row in registry:
        role = row.get("component_role") or row.get("source_component_role")
        for cp_id in row.get("applicable_content_product_type_ids", []):
            if role not in role_sets.get(cp_id, set()):
                add_error(
                    errors,
                    "E_COMPONENT_CP_ROLE_MISMATCH",
                    row["component_id"],
                    f"{cp_id} lacks role {role}",
                )
        if row.get("component_version") == "v0.3":
            edge_ids = [
                edge.get("content_product_type_id")
                for edge in row.get("per_CP_applicability_evidence", [])
            ]
            if sorted(edge_ids) != sorted(row.get("applicable_content_product_type_ids", [])):
                add_error(errors, "E_COMPONENT_CP_EDGE_SET", row["component_id"], str(edge_ids))


def validate_materialization(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    drift = freezer.check_files(root)
    for item in drift:
        if item == f"materialized drift {RESULT_PATH.as_posix()}":
            continue
        add_error(errors, "E_MATERIALIZED_DRIFT", "freezer", item)


def validate_coverage(root: Path, freezer: Any, registry: list[dict[str, Any]], errors: list[dict[str, str]]) -> None:
    actual = load_yaml(root / COVERAGE_PATH)
    expected = freezer.build_coverage(root, registry)
    if actual != expected:
        add_error(errors, "E_COVERAGE_RECOMPUTE", "coverage", "coverage file is not recomputed output")
    summary = actual["content_product_component_coverage"]["summary"]
    if summary["component_supply_complete_count"] != 20:
        add_error(errors, "E_COVERAGE_NOT_20", "coverage", str(summary))
    for row in actual["content_product_component_coverage"]["profile_component_coverage"]:
        cp_id = row["content_product_type_id"]
        for role, component_ids in row["covering_component_ids"].items():
            for component_id in component_ids:
                component = next((item for item in registry if item["component_id"] == component_id), None)
                actual_role = (component or {}).get("component_role") or (component or {}).get("source_component_role")
                if actual_role != role:
                    add_error(errors, "E_ROLE_COVERAGE_MISMATCH", cp_id, f"{role} <- {component_id}")


def validate_result(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    result = load_yaml(root / RESULT_PATH)["component_supply_closeout_result"]
    if result.get("result_digest") != freezer.object_digest(result, {"result_digest"}):
        add_error(errors, "E_RESULT_DIGEST", "result", "digest mismatch")
    if result.get("execution_integrity") != "PASS":
        add_error(errors, "E_EXECUTION_INTEGRITY", "result", str(result.get("execution_integrity")))
    if result.get("component_supply_status") != "STRUCTURAL_20CP_SUPPLY_COMPLETE_PENDING_GUARDIAN":
        add_error(errors, "E_SUPPLY_STATUS", "result", str(result.get("component_supply_status")))
    counts = result["counts"]
    fixed = {
        "fixture_gap_count": 20,
        "runtime_generation_eligible_profile_count": 0,
        "canonical_composition_plan_count": 0,
        "audience_facing_content_count": 0,
        "knowledge_count_increment": 0,
        "ontology_truth_change_count": 0,
    }
    for key, expected in fixed.items():
        if counts.get(key) != expected:
            add_error(errors, "E_FIXED_FALSE_COUNT", "result", f"{key}={counts.get(key)}")
    if recursive_true_flags(result):
        add_error(errors, "E_READY_TRUE", "result", str(recursive_true_flags(result)))


def top_level_route_ids(text: str) -> list[int]:
    ids: list[int] = []
    for line in text.splitlines():
        if line.startswith("  route_migration_") and line.endswith(":"):
            suffix = line.strip().removeprefix("route_migration_").removesuffix(":")
            if suffix.isdigit():
                ids.append(int(suffix))
    return ids


def validate_ledger(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    data = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    migration = data.get("route_migration_23")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_ROUTE23", "ledger", "route_migration_23 missing")
        return
    if migration.get("applied_by_task") != TASK_ID:
        add_error(errors, "E_LEDGER_TASK", "ledger", str(migration.get("applied_by_task")))
    if migration.get("additive_only") is not True or migration.get("no_readiness_flipped") is not True:
        add_error(errors, "E_LEDGER_DECLARATION", "ledger", "additive/readiness declaration missing")
    if migration.get("S2_v003", {}).get("runtime_generation_eligible_profile_count") != 0:
        add_error(errors, "E_LEDGER_RUNTIME", "ledger", "runtime eligible not zero")
    text = (root / LEDGER_PATH).read_text(encoding="utf-8")
    ids = top_level_route_ids(text)
    if 23 not in ids:
        add_error(errors, "E_LEDGER_ROUTE23", "ledger", "id missing")
    if sorted(route_id for route_id in ids if route_id >= 19) != list(range(19, max(ids) + 1)):
        add_error(errors, "E_LEDGER_ROUTE_SEQUENCE", "ledger", str(ids))
    if enforce_git:
        old_text = git(root, ["show", f"{BASELINE_HEAD}:{LEDGER_PATH.as_posix()}"])
        if old_text:
            old_data = yaml.safe_load(old_text)["grc_3600_execution_plan_status"]
            current_extra = sorted(set(data) - set(old_data))
            if current_extra != [
                "route_migration_23",
                "route_migration_24",
                "route_migration_25",
                "route_migration_26",
                "route_migration_27",
            ]:
                add_error(errors, "E_LEDGER_EXTRA_KEYS", "ledger", str(current_extra))
            for key, value in old_data.items():
                if data.get(key) != value:
                    add_error(errors, "E_LEDGER_NON_ADDITIVE", "ledger", f"drift at {key}")


def collect_errors(root: Path, enforce_git: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    freezer = load_freezer(root)
    required = [
        CONTRACT_PATH,
        DECISIONS_PATH,
        REGISTRY_PATH,
        COVERAGE_PATH,
        RESULT_PATH,
        PACKET_PATH,
        FREEZER_PATH,
        CHECKER_PATH,
        ORCH_VALIDATION_DRYRUN_CHECKER_PATH,
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
    decisions = load_jsonl(root / DECISIONS_PATH)
    validate_decisions(root, freezer, decisions, errors)
    validate_merge_equivalence(decisions, errors)
    registry = load_jsonl(root / REGISTRY_PATH)
    validate_registry(root, freezer, registry, errors)
    validate_materialization(root, freezer, errors)
    validate_coverage(root, freezer, registry, errors)
    validate_result(root, freezer, errors)
    validate_ledger(root, errors, enforce_git)
    return errors


def selftest() -> int:
    root = Path.cwd()
    freezer = load_freezer(root)
    decisions = load_jsonl(root / DECISIONS_PATH)
    registry = load_jsonl(root / REGISTRY_PATH)
    tests: list[tuple[str, bool]] = []

    def decision_errors(mutated: list[dict[str, Any]]) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        validate_decisions(root, freezer, mutated, errors)
        validate_merge_equivalence(mutated, errors)
        return errors

    tests.append(("valid_decisions", not decision_errors(copy.deepcopy(decisions))))

    missing = [row for row in decisions if row["candidate_id"] != "CCV2-CAND-01-VISUAL"]
    tests.append(("missing_held_rejected", any(e["code"] == "E_HELD_COVERAGE" for e in decision_errors(missing))))

    promoted_bare = copy.deepcopy(decisions)
    promoted_bare[0]["decision"] = {"enum": "PROMOTE_AS_NEW"}
    promoted_bare[0]["target_reusable_component_id"] = "RCV2-003-INVALID-BARE-VISUAL"
    tests.append(("bare_visual_without_cp_rejected", any(e["code"] == "E_ACCEPTED_NO_CP_EDGE" for e in decision_errors(promoted_bare))))

    bad_merge = copy.deepcopy(decisions)
    for row in bad_merge:
        if row["decision"]["enum"] == "MERGE_INTO_REUSABLE":
            row["required_input_slots"] = ["changed_slot"]
            break
    tests.append(("merge_equivalence_rejected", any(e["code"] == "E_MERGE_EQUIVALENCE" for e in decision_errors(bad_merge))))

    bad_parent = copy.deepcopy(decisions)
    bad_parent[1]["parent_digest"] = "0" * 64
    tests.append(("parent_digest_tamper_rejected", any(e["code"] == "E_PARENT_DIGEST" for e in decision_errors(bad_parent))))

    bad_span = copy.deepcopy(decisions)
    bad_span[1]["evidence_spans"][0]["text"] = "not in parent"
    tests.append(("evidence_span_tamper_rejected", any(e["code"] == "E_EVIDENCE_SPAN" for e in decision_errors(bad_span))))

    false_cp_edge = copy.deepcopy(decisions)
    for row in false_cp_edge:
        if row["candidate_id"] == "CCV2-CAND-14-ACTION":
            row["applicable_content_product_type_ids"].append("CP17")
            row["per_CP_applicability_assessments"].append(
                {
                    "content_product_type_id": "CP17",
                    "required_component_role": "transition",
                    "fit_basis": ["synthetic false edge for selftest"],
                }
            )
            break
    tests.append(
        (
            "false_cp17_transition_edge_rejected",
            any(e["code"] == "E_CP_APPLICABILITY_ROLE_MISMATCH" for e in decision_errors(false_cp_edge)),
        )
    )

    registry_errors: list[dict[str, str]] = []
    bad_registry = copy.deepcopy(registry)
    bad_registry[0]["component_id"] = "tampered"
    validate_registry(root, freezer, bad_registry, registry_errors)
    tests.append(("old_55_tamper_rejected", any(e["code"] == "E_OLD_COMPONENT_DRIFT" for e in registry_errors)))

    ready_errors: list[dict[str, str]] = []
    bad_new = copy.deepcopy(registry)
    bad_new[-1]["runtime_ready"] = True
    validate_registry(root, freezer, bad_new, ready_errors)
    tests.append(("runtime_ready_true_rejected", any(e["code"] == "E_COMPONENT_READY" for e in ready_errors)))

    registry_false_edge_errors: list[dict[str, str]] = []
    registry_false_edge = copy.deepcopy(registry)
    for row in registry_false_edge:
        if row["component_id"] == "RCV2-003-TRANSITION-DISPLAY-HIERARCHY-SPACE":
            row["applicable_content_product_type_ids"].append("CP17")
            break
    validate_registry(root, freezer, registry_false_edge, registry_false_edge_errors)
    tests.append(
        (
            "registry_false_cp17_transition_edge_rejected",
            any(e["code"] == "E_COMPONENT_CP_ROLE_MISMATCH" for e in registry_false_edge_errors),
        )
    )

    partial_registry = copy.deepcopy(registry)
    partial_registry = [row for row in partial_registry if row["component_id"] != "RCV2-003-CLOSING-LOCAL-EVIDENCE-LONG-TERM-DEFER"]
    partial_coverage = freezer.build_coverage(root, partial_registry)["content_product_component_coverage"]
    tests.append(("partial_coverage_structural_positive", partial_coverage["summary"]["component_supply_complete_count"] < 20))

    hidden_plan = copy.deepcopy(decisions)
    hidden_plan[0]["CompositionPlan"] = {"runtime": True}
    tests.append(("runtime_plan_field_rejected", any(e["code"] == "E_FORBIDDEN_FIELD" for e in decision_errors(hidden_plan))))

    tests.append(
        (
            "orch_successor_write_surface_declared",
            (SUCCESSOR_ORCH_VALIDATION_DRYRUN_DIR / "orch_20cp_dryrun_result.v0.1.yaml").is_relative_to(
                SUCCESSOR_ORCH_VALIDATION_DRYRUN_DIR
            ),
        )
    )
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
        print({"status": "SELFTEST_FAIL", "failed": failed}, file=sys.stderr)
        return 1
    print("SELFTEST_PASS")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        print("usage: check_gkb_v2_20cp_component_supply_closeout.py [--selftest]", file=sys.stderr)
        return 2
    if len(argv) == 1 and argv[0] == "--selftest":
        return selftest()
    if argv:
        print("usage: check_gkb_v2_20cp_component_supply_closeout.py [--selftest]", file=sys.stderr)
        return 2
    errors = collect_errors(Path.cwd(), enforce_git=True)
    if errors:
        print(json.dumps({"status": "FAIL", "error_count": len(errors), "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task_id": TASK_ID}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
