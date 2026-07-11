#!/usr/bin/env python3
"""Fail-closed checker for the v0.2 true semantic component review snapshot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    print("check_gkb_controlled_v2_component_review_20cp_v002 refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "GKB-CONTROLLED-V2-COMPONENT-DOMAIN-REVIEW-20CP-RECLASSIFICATION-AND-HANDOFF-FREEZE-002"
BASELINE_HEAD = "84faff476c248d9277d8882f2c9e4aa402a96b22"
ROOT_S1 = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = ROOT_S1 / "component_review_20cp_and_handoff_002"
POLICY_PATH = TASK_DIR / "component_domain_review_policy.v0.2.yaml"
DECISIONS_PATH = TASK_DIR / "component_domain_review_decisions.v0.2.jsonl"
REGISTRY_PATH = TASK_DIR / "reviewed_reusable_component_registry.v0.2.jsonl"
COVERAGE_PATH = TASK_DIR / "content_product_component_coverage.v0.2.yaml"
HANDOFF_PATH = TASK_DIR / "gkb_orch_reviewed_component_handoff.v0.2.yaml"
RESULT_PATH = TASK_DIR / "component_review_20cp_and_handoff_result.v0.2.yaml"
FREEZER_PATH = TASK_DIR / "run_component_review_20cp_v002_freezer.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_controlled_v2_component_review_20cp_v002.py")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")

S1_CANDIDATES_PATH = ROOT_S1 / "component_candidate_manifest.v0.1.jsonl"
S1_SELECTION_PATH = ROOT_S1 / "pilot_source_selection.v0.1.yaml"
S1_5_PROFILES_PATH = ROOT_S1 / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"

REQUIRED_PATHS = [
    POLICY_PATH,
    DECISIONS_PATH,
    REGISTRY_PATH,
    COVERAGE_PATH,
    HANDOFF_PATH,
    RESULT_PATH,
    FREEZER_PATH,
    CHECKER_PATH,
]
ALLOWED_CHANGED_PATHS = set(REQUIRED_PATHS) | {LEDGER_PATH}

DECISION_ENUM = {
    "PROMOTE_AS_NEW",
    "MERGE_INTO_REUSABLE",
    "SOURCE_SPECIFIC_REFERENCE_ONLY",
    "NEEDS_REPAIR",
    "REJECT",
}
ASSESSMENT_ENUM = {"ABSTRACTABLE", "NOT_ABSTRACTABLE_FOR_ROLE", "SOURCE_SPECIFIC_ONLY"}
DECISION_KEYS = {
    "schema_version",
    "task_id",
    "candidate_id",
    "source_asset_id",
    "source_P0_group",
    "component_role",
    "candidate_semantic_readback",
    "abstraction_assessment",
    "applicability_review",
    "review_dimensions",
    "decision",
    "target_reusable_component_id",
    "decision_reason_codes",
    "decision_rationale",
    "merge_equivalence_assessment",
    "reviewer",
}
READBACK_KEYS = {
    "summary",
    "actual_mechanism",
    "source_specific_elements",
    "reusable_elements",
    "factual_or_event_dependencies",
    "role_authority_dependencies",
    "semantic_risks",
}
ASSESSMENT_KEYS = {
    "enum",
    "abstract_component_function",
    "required_runtime_slots",
    "claim_boundary",
    "parent_verbatim_allowed",
}
FORBIDDEN_FIELD_NAMES = {
    "body_text",
    "title_text",
    "spoken_script",
    "publishable_copy",
    "source_sentence",
    "template_sentence",
    "literal_quote",
    "surface_script",
    "canonical_CompositionPlan",
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
}
INVALID_ACTION_PROMOTIONS = {
    "CCV2-CAND-02-ACTION",
    "CCV2-CAND-03-ACTION",
    "CCV2-CAND-07-ACTION",
    "CCV2-CAND-11-ACTION",
    "CCV2-CAND-13-ACTION",
    "CCV2-CAND-14-ACTION",
}
VISUAL_PROMOTION_ALLOWLIST = {"CCV2-CAND-12-VISUAL"}
UNDER_SPECIFIED_JUDGMENTS = {"CCV2-CAND-02-JUDGE", "CCV2-CAND-13-JUDGE"}


def add_error(errors: list[dict[str, str]], code: str, section: str, detail: str) -> None:
    errors.append({"code": code, "section": section, "detail": detail})


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_key(value: Any, key_to_strip: str) -> None:
    if isinstance(value, dict):
        value.pop(key_to_strip, None)
        for child in value.values():
            strip_key(child, key_to_strip)
    elif isinstance(value, list):
        for child in value:
            strip_key(child, key_to_strip)


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    stripped = copy.deepcopy(value)
    for key in digest_keys or set():
        strip_key(stripped, key)
    return sha256_text(canonical_json(stripped))


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"YAML root is not mapping: {path}")
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise TypeError(f"JSONL row is not object: {path}:{line_number}")
        rows.append(row)
    return rows


def load_freezer(root: Path) -> Any:
    spec = importlib.util.spec_from_file_location("component_review_v002_freezer", root / FREEZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load freezer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def recursive_ready_true(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in READY_TRUE_KEYS and child is True:
                hits.append(child_path)
            hits.extend(recursive_ready_true(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_ready_true(child, f"{path}[{index}]"))
    return hits


def source_p0_index(root: Path) -> dict[str, str]:
    selected = load_yaml(root / S1_SELECTION_PATH)["pilot_source_selection"]["selected_sources"]
    return {item["asset_id"]: item["p0_group"] for item in selected}


def validate_policy(policy_doc: dict[str, Any], errors: list[dict[str, str]]) -> None:
    policy = policy_doc.get("component_domain_review_policy", {})
    if policy.get("schema_version") != "v0.2" or policy.get("task_id") != TASK_ID:
        add_error(errors, "E_POLICY_HEADER", "policy", "wrong schema or task")
    method = policy.get("review_method", {})
    if method.get("decision_engine_allowed") is not False:
        add_error(errors, "E_DECISION_ENGINE_ALLOWED", "policy", "decision engine must be false")
    if method.get("role_p0_order_grouping_allowed") is not False:
        add_error(errors, "E_ROLE_P0_GROUPING_ALLOWED", "policy", "role/P0 grouping must be false")
    handoff = policy.get("handoff_policy", {})
    if handoff.get("authoritative_after_guardian_pass_only") is not True:
        add_error(errors, "E_HANDOFF_AUTHORITY", "policy", "guardian authority gate missing")


def validate_decisions(
    root: Path,
    decisions: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    candidates = {row["component_id"]: row for row in load_jsonl(root / S1_CANDIDATES_PATH)}
    p0_by_parent = source_p0_index(root)
    if len(decisions) != 89:
        add_error(errors, "E_DECISION_COUNT", "decisions", f"expected 89 got {len(decisions)}")
    ids = [row.get("candidate_id") for row in decisions]
    if set(ids) != set(candidates):
        add_error(errors, "E_DECISION_IDS", "decisions", "decision ids do not match candidate manifest")
    if len(ids) != len(set(ids)):
        add_error(errors, "E_DUPLICATE_DECISION", "decisions", "duplicate candidate decisions")

    summaries: list[str] = []
    mechanisms: list[str] = []
    rationale_values: list[str] = []
    promoted_targets: set[str] = set()

    for row in decisions:
        cid = str(row.get("candidate_id"))
        section = f"decisions:{cid}"
        extra = sorted(set(row) - DECISION_KEYS)
        missing = sorted(DECISION_KEYS - set(row))
        if extra or missing:
            add_error(errors, "E_DECISION_SCHEMA", section, f"extra={extra} missing={missing}")
            continue
        if row["schema_version"] != "v0.2" or row["task_id"] != TASK_ID:
            add_error(errors, "E_DECISION_HEADER", section, "wrong schema or task")
        candidate = candidates.get(cid)
        if candidate is None:
            continue
        parent = candidate["parent_refs"][0]
        if row["source_asset_id"] != parent["parent_asset_id"]:
            add_error(errors, "E_DECISION_SOURCE", section, "source asset mismatch")
        if row["source_P0_group"] != p0_by_parent[parent["parent_asset_id"]]:
            add_error(errors, "E_DECISION_P0", section, "P0 mismatch")
        if row["component_role"] != candidate["component_role"]:
            add_error(errors, "E_DECISION_ROLE", section, "role mismatch")
        readback = row["candidate_semantic_readback"]
        assessment = row["abstraction_assessment"]
        if set(readback) != READBACK_KEYS:
            add_error(errors, "E_READBACK_SCHEMA", section, f"keys={sorted(readback)}")
        if set(assessment) != ASSESSMENT_KEYS:
            add_error(errors, "E_ASSESSMENT_SCHEMA", section, f"keys={sorted(assessment)}")
        summaries.append(str(readback.get("summary", "")))
        mechanisms.append(str(readback.get("actual_mechanism", "")))
        rationale_values.append(str(row.get("decision_rationale", "")))
        enum = row["decision"].get("enum")
        if enum not in DECISION_ENUM:
            add_error(errors, "E_DECISION_ENUM", section, str(enum))
        if assessment.get("enum") not in ASSESSMENT_ENUM:
            add_error(errors, "E_ASSESSMENT_ENUM", section, str(assessment.get("enum")))
        if assessment.get("parent_verbatim_allowed") is not False:
            add_error(errors, "E_VERBATIM_ALLOWED", section, "parent verbatim must be false")
        target = row.get("target_reusable_component_id")
        if enum == "PROMOTE_AS_NEW":
            if not isinstance(target, str) or not target:
                add_error(errors, "E_PROMOTE_TARGET", section, "promote requires target")
            elif target in promoted_targets:
                add_error(errors, "E_PROMOTE_TARGET_DUP", section, target)
            else:
                promoted_targets.add(target)
        elif enum == "MERGE_INTO_REUSABLE":
            if not isinstance(target, str) or not target:
                add_error(errors, "E_MERGE_TARGET", section, "merge requires target")
            if row["merge_equivalence_assessment"].get("merge_allowed") is not True:
                add_error(errors, "E_MERGE_EQUIVALENCE", section, "merge_allowed must be true")
        else:
            if target is not None:
                add_error(errors, "E_NON_PROMOTED_TARGET", section, "non-promoted decision cannot target registry")
        if cid in INVALID_ACTION_PROMOTIONS and enum in {"PROMOTE_AS_NEW", "MERGE_INTO_REUSABLE"}:
            add_error(errors, "E_BAD_ACTION_PROMOTED", section, "meta/non-action promoted")
        if cid.endswith("-VISUAL") and cid not in VISUAL_PROMOTION_ALLOWLIST and enum in {"PROMOTE_AS_NEW", "MERGE_INTO_REUSABLE"}:
            add_error(errors, "E_BAD_VISUAL_PROMOTED", section, "bare visual noun promoted")
        if cid in UNDER_SPECIFIED_JUDGMENTS and enum in {"PROMOTE_AS_NEW", "MERGE_INTO_REUSABLE"}:
            add_error(errors, "E_BAD_JUDGMENT_PROMOTED", section, "under-specified judgment promoted")
        if recursive_forbidden_fields(row):
            add_error(errors, "E_FORBIDDEN_FIELD", section, str(recursive_forbidden_fields(row)))
        if recursive_ready_true(row):
            add_error(errors, "E_READY_TRUE", section, str(recursive_ready_true(row)))

    if len(set(summaries)) < 80:
        add_error(errors, "E_READBACK_NOT_CANDIDATE_SPECIFIC", "decisions", "summary uniqueness below 80")
    if len(set(mechanisms)) < 75:
        add_error(errors, "E_MECHANISM_NOT_CANDIDATE_SPECIFIC", "decisions", "mechanism uniqueness below 75")
    if len(set(rationale_values)) < 55:
        add_error(errors, "E_RATIONALE_TOO_REPETITIVE", "decisions", "rationale uniqueness below 55")


def validate_merges(
    root: Path,
    decisions: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    candidates = {row["component_id"]: row for row in load_jsonl(root / S1_CANDIDATES_PATH)}
    target_roles = {component["component_id"]: component["source_component_role"] for component in registry}
    promoting_candidate_by_target = {
        component["component_id"]: component["domain_review_ref"]["promoting_candidate_id"]
        for component in registry
    }
    for row in decisions:
        if row["decision"]["enum"] != "MERGE_INTO_REUSABLE":
            continue
        cid = row["candidate_id"]
        target = row["target_reusable_component_id"]
        section = f"merge:{cid}"
        if target not in target_roles:
            add_error(errors, "E_MERGE_TARGET_UNKNOWN", section, target)
            continue
        if row["component_role"] != target_roles[target]:
            add_error(errors, "E_MERGE_ROLE_MISMATCH", section, target)
        if row["component_role"] != "capture_instruction":
            add_error(errors, "E_MERGE_NON_CAPTURE", section, "v002 only accepts exact capture metadata merges")
        source_payload = candidates[cid]["payload"]["content"]
        target_candidate_id = promoting_candidate_by_target[target]
        target_payload = candidates[target_candidate_id]["payload"]["content"]
        if source_payload != target_payload:
            add_error(errors, "E_MERGE_PAYLOAD_MISMATCH", section, "capture metadata differs")


def validate_registry(
    registry: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    promoted_targets = {
        row["target_reusable_component_id"]
        for row in decisions
        if row["decision"]["enum"] == "PROMOTE_AS_NEW"
    }
    ids = [row["component_id"] for row in registry]
    if set(ids) != promoted_targets:
        add_error(errors, "E_REGISTRY_TARGETS", "registry", "registry does not equal promoted targets")
    if len(ids) != len(set(ids)):
        add_error(errors, "E_REGISTRY_DUPLICATE", "registry", "duplicate component ids")
    for component in registry:
        section = f"registry:{component.get('component_id')}"
        if component.get("lifecycle") != "reviewed_reusable_pending_guardian":
            add_error(errors, "E_REGISTRY_LIFECYCLE", section, "wrong lifecycle")
        if component.get("component_digest") != object_digest(component, {"component_digest"}):
            add_error(errors, "E_COMPONENT_DIGEST", section, "component digest mismatch")
        if recursive_ready_true(component):
            add_error(errors, "E_READY_TRUE", section, str(recursive_ready_true(component)))
        if recursive_forbidden_fields(component):
            add_error(errors, "E_FORBIDDEN_FIELD", section, str(recursive_forbidden_fields(component)))
        truth = component.get("truth_boundary", {})
        if any(value is True for value in truth.values()):
            add_error(errors, "E_TRUTH_BOUNDARY", section, "truth boundary must stay false")


def validate_coverage(coverage_doc: dict[str, Any], registry: list[dict[str, Any]], freezer: Any, root: Path, errors: list[dict[str, str]]) -> None:
    expected = freezer.build_coverage(root, registry)
    if coverage_doc != expected:
        add_error(errors, "E_COVERAGE_RECOMPUTE", "coverage", "coverage does not recompute from registry")
    coverage = coverage_doc.get("content_product_component_coverage", {})
    if coverage.get("coverage_digest") != object_digest(coverage, {"coverage_digest"}):
        add_error(errors, "E_COVERAGE_DIGEST", "coverage", "coverage digest mismatch")
    if coverage.get("summary", {}).get("runtime_generation_eligible_profile_count") != 0:
        add_error(errors, "E_RUNTIME_ELIGIBLE", "coverage", "runtime eligibility must remain 0")


def validate_handoff_and_result(
    root: Path,
    handoff_doc: dict[str, Any],
    result_doc: dict[str, Any],
    decisions: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    coverage_doc: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    handoff = handoff_doc.get("gkb_orch_reviewed_component_handoff", {})
    if handoff.get("handoff_version") != "v0.2":
        add_error(errors, "E_HANDOFF_VERSION", "handoff", "wrong version")
    if handoff.get("freeze_status") != "IMMUTABLE_CANDIDATE_SNAPSHOT_PENDING_GUARDIAN":
        add_error(errors, "E_HANDOFF_STATUS", "handoff", "wrong freeze status")
    if handoff.get("authoritative_after_guardian_pass_only") is not True:
        add_error(errors, "E_HANDOFF_AUTHORITY", "handoff", "guardian authority missing")
    if handoff.get("state", {}).get("handoff_integrity_frozen") is not False:
        add_error(errors, "E_HANDOFF_FROZEN", "handoff", "must not claim authoritative freeze")
    if handoff.get("handoff_digest") != object_digest(handoff, {"handoff_digest"}):
        add_error(errors, "E_HANDOFF_DIGEST", "handoff", "handoff digest mismatch")
    if recursive_ready_true(handoff_doc):
        add_error(errors, "E_READY_TRUE", "handoff", str(recursive_ready_true(handoff_doc)))

    result = result_doc.get("component_review_20cp_and_handoff_result", {})
    if result.get("verdict") != "S2_V002_TRUE_SEMANTIC_REVIEW_EXECUTED_PENDING_CLAUDE_GUARDIAN":
        add_error(errors, "E_RESULT_VERDICT", "result", "wrong verdict")
    if result.get("authoritative_handoff_frozen") is not False:
        add_error(errors, "E_RESULT_FROZEN", "result", "must not claim authoritative handoff")
    if result.get("CI_REMOTE_execution_allowed") is not False:
        add_error(errors, "E_CI_REMOTE_ALLOWED", "result", "CI_REMOTE must remain blocked")
    counts = Counter(row["decision"]["enum"] for row in decisions)
    summary = coverage_doc["content_product_component_coverage"]["summary"]
    expected_counts = {
        "reviewed_candidate_count": len(decisions),
        "reviewed_reusable_component_count": len(registry),
        "promoted_as_new_count": counts["PROMOTE_AS_NEW"],
        "merged_candidate_count": counts["MERGE_INTO_REUSABLE"],
        "source_specific_reference_only_count": counts["SOURCE_SPECIFIC_REFERENCE_ONLY"],
        "needs_repair_count": counts["NEEDS_REPAIR"],
        "rejected_count": counts["REJECT"],
        "component_contract_complete_profile_count": summary["complete_count"],
        "component_contract_partial_profile_count": summary["partial_count"],
        "component_contract_none_profile_count": summary["none_count"],
        "fixture_gap_count": 20,
        "runtime_generation_eligible_profile_count": 0,
        "canonical_composition_plan_count": 0,
        "audience_facing_content_count": 0,
    }
    if result.get("counts") != expected_counts:
        add_error(errors, "E_RESULT_COUNTS", "result", "counts mismatch")
    if result.get("result_digest") != object_digest(result, {"result_digest"}):
        add_error(errors, "E_RESULT_DIGEST", "result", "result digest mismatch")
    for rel_path, expected_digest in result.get("generated_file_digests", {}).items():
        path = root / rel_path
        if not path.exists() or sha256_file(path) != expected_digest:
            add_error(errors, "E_RECORDED_DIGEST", "result", f"digest mismatch {rel_path}")
    if recursive_ready_true(result_doc):
        add_error(errors, "E_READY_TRUE", "result", str(recursive_ready_true(result_doc)))


def validate_freezer_source(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / FREEZER_PATH).read_text(encoding="utf-8")
    forbidden_snippets = [
        "first_for_group",
        "forced_zero",
        "component_review_20cp_and_handoff_001/reviewed_reusable_component_registry",
        "component_review_20cp_and_handoff_001/gkb_orch_reviewed_component_handoff",
    ]
    for snippet in forbidden_snippets:
        if snippet in text:
            add_error(errors, "E_FREEZER_FORBIDDEN_SOURCE", "freezer", snippet)
    if "build_decisions" in text:
        add_error(errors, "E_FREEZER_DECISION_BUILDER", "freezer", "freezer must not build domain decisions")


def validate_git_surface(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    if not enforce_git:
        return
    changed = changed_paths(root)
    extra = sorted(path.as_posix() for path in changed - ALLOWED_CHANGED_PATHS)
    if extra:
        add_error(errors, "E_CHANGED_SURFACE", "git", f"unexpected changed paths {extra}")
    for path in changed:
        lower = path.as_posix().lower()
        if ".github/" in lower or "ci_remote" in lower:
            add_error(errors, "E_CI_REMOTE_SIDE_EFFECT", "git", path.as_posix())
        if any(token in lower for token in ["compositionplan", "assignment", "generation_record", "draft"]):
            add_error(errors, "E_FORBIDDEN_FILE_PATH", "git", path.as_posix())


def validate_ledger(root: Path, errors: list[dict[str, str]]) -> None:
    ledger = load_yaml(root / LEDGER_PATH).get("grc_3600_execution_plan_status", {})
    migration = ledger.get("route_migration_22")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_ROUTE22", "ledger", "route_migration_22 missing")
        return
    if migration.get("applied_by_task") != TASK_ID:
        add_error(errors, "E_LEDGER_TASK", "ledger", "wrong task")
    if migration.get("additive_only") is not True:
        add_error(errors, "E_LEDGER_ADDITIVE", "ledger", "additive_only must be true")
    if migration.get("CI_REMOTE", {}).get("execution_allowed") is not False:
        add_error(errors, "E_LEDGER_CI_REMOTE", "ledger", "CI_REMOTE must remain blocked")
    guardian = migration.get("route_migration_21_guardian_verdict", {})
    if guardian.get("verdict") != "FAIL" or guardian.get("handoff_freeze_status") != "NOT_FROZEN":
        add_error(errors, "E_LEDGER_V001_FAIL", "ledger", "v001 failure not recorded")
    if recursive_ready_true(migration):
        add_error(errors, "E_READY_TRUE", "ledger", str(recursive_ready_true(migration)))
    if migration.get("migration_digest") != object_digest(migration, {"migration_digest"}):
        add_error(errors, "E_LEDGER_DIGEST", "ledger", "migration digest mismatch")


def validate_materialized(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    expected = freezer.build_artifacts(root)
    for rel_path, expected_text in expected.items():
        path = root / rel_path
        if not path.exists():
            add_error(errors, "E_MATERIALIZED_MISSING", "freezer", str(rel_path))
        elif path.read_text(encoding="utf-8") != expected_text:
            add_error(errors, "E_MATERIALIZED_DRIFT", "freezer", str(rel_path))


def collect_errors(
    root: Path,
    *,
    decision_rows: list[dict[str, Any]] | None = None,
    enforce_git: bool = True,
    compare_materialized_files: bool = True,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for path in REQUIRED_PATHS:
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE", "files", f"missing {path}")
    if any(error["code"] == "E_REQUIRED_FILE" for error in errors):
        return errors

    freezer = load_freezer(root)
    policy_doc = load_yaml(root / POLICY_PATH)
    decisions = decision_rows if decision_rows is not None else load_jsonl(root / DECISIONS_PATH)
    registry = freezer.build_registry(root, decisions)
    registry_file = load_jsonl(root / REGISTRY_PATH)
    coverage_doc = freezer.build_coverage(root, registry)

    validate_policy(policy_doc, errors)
    validate_decisions(root, decisions, errors)
    if decision_rows is None and registry_file != registry:
        add_error(errors, "E_REGISTRY_RECOMPUTE", "registry", "registry does not recompute from decisions")
    validate_registry(registry, decisions, errors)
    validate_merges(root, decisions, registry, errors)
    if decision_rows is None:
        coverage_file = load_yaml(root / COVERAGE_PATH)
        handoff_file = load_yaml(root / HANDOFF_PATH)
        result_file = load_yaml(root / RESULT_PATH)
        validate_coverage(coverage_file, registry, freezer, root, errors)
        validate_handoff_and_result(root, handoff_file, result_file, decisions, registry, coverage_file, errors)
        if compare_materialized_files:
            validate_materialized(root, freezer, errors)
        validate_ledger(root, errors)
    validate_freezer_source(root, errors)
    validate_git_surface(root, errors, enforce_git)
    return errors


def run_selftest(root: Path) -> int:
    freezer = load_freezer(root)
    decisions = load_jsonl(root / DECISIONS_PATH)
    expected = freezer.build_artifacts(root)
    reversed_output = freezer.build_artifacts(root, decision_rows=list(reversed(decisions)))
    if expected != reversed_output:
        print("SELFTEST_FAIL: materializer output changes when decision JSONL order changes", file=sys.stderr)
        return 1

    visual_mutation = copy.deepcopy(decisions)
    for row in visual_mutation:
        if row["candidate_id"] == "CCV2-CAND-01-VISUAL":
            row["decision"]["enum"] = "PROMOTE_AS_NEW"
            row["target_reusable_component_id"] = "SELFTEST-BAD-VISUAL"
            break
    visual_errors = collect_errors(root, decision_rows=visual_mutation, enforce_git=False, compare_materialized_files=False)
    if not any(error["code"] == "E_BAD_VISUAL_PROMOTED" for error in visual_errors):
        print("SELFTEST_FAIL: bad visual promotion was not rejected", file=sys.stderr)
        return 1

    action_mutation = copy.deepcopy(decisions)
    for row in action_mutation:
        if row["candidate_id"] == "CCV2-CAND-02-ACTION":
            row["decision"]["enum"] = "PROMOTE_AS_NEW"
            row["target_reusable_component_id"] = "SELFTEST-BAD-ACTION"
            break
    action_errors = collect_errors(root, decision_rows=action_mutation, enforce_git=False, compare_materialized_files=False)
    if not any(error["code"] == "E_BAD_ACTION_PROMOTED" for error in action_errors):
        print("SELFTEST_FAIL: bad action promotion was not rejected", file=sys.stderr)
        return 1

    duplicate_mutation = copy.deepcopy(decisions)
    for row in duplicate_mutation:
        row["candidate_semantic_readback"]["summary"] = "same"
        row["candidate_semantic_readback"]["actual_mechanism"] = "same"
    duplicate_errors = collect_errors(root, decision_rows=duplicate_mutation, enforce_git=False, compare_materialized_files=False)
    if not any(error["code"] == "E_READBACK_NOT_CANDIDATE_SPECIFIC" for error in duplicate_errors):
        print("SELFTEST_FAIL: duplicate readbacks were not rejected", file=sys.stderr)
        return 1

    print("SELFTEST_PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--no-git", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.selftest:
        return run_selftest(root)
    errors = collect_errors(root, enforce_git=not args.no_git)
    if errors:
        print(json.dumps({"status": "FAIL", "error_count": len(errors), "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task_id": TASK_ID}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
