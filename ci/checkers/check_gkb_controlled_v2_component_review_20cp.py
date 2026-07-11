#!/usr/bin/env python3
"""Fail-closed checker for the Controlled V2 89-component review handoff."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import yaml


if not __debug__:
    print("check_gkb_controlled_v2_component_review_20cp refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "GKB-CONTROLLED-V2-COMPONENT-DOMAIN-REVIEW-20CP-RECLASSIFICATION-AND-HANDOFF-FREEZE-001"
BASELINE_HEAD = "78d21adff79c006449763e0644e52cdae55bcbe8"
ROOT_S1 = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = ROOT_S1 / "component_review_20cp_and_handoff_001"
MAPPING_PATH = TASK_DIR / "capability_product_composition_mapping.v0.1.yaml"
POLICY_PATH = TASK_DIR / "component_domain_review_policy.v0.1.yaml"
DECISIONS_PATH = TASK_DIR / "component_domain_review_decisions.v0.1.jsonl"
REGISTRY_PATH = TASK_DIR / "reviewed_reusable_component_registry.v0.1.jsonl"
COVERAGE_PATH = TASK_DIR / "content_product_component_coverage.v0.1.yaml"
HANDOFF_PATH = TASK_DIR / "gkb_orch_reviewed_component_handoff.v0.1.yaml"
RESULT_PATH = TASK_DIR / "component_review_20cp_and_handoff_result.v0.1.yaml"
FREEZER_PATH = TASK_DIR / "run_component_review_20cp_freezer.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_controlled_v2_component_review_20cp.py")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CLEAN_120_CORPUS_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)

ALLOWED_CHANGED_PATHS = {
    MAPPING_PATH,
    POLICY_PATH,
    DECISIONS_PATH,
    REGISTRY_PATH,
    COVERAGE_PATH,
    HANDOFF_PATH,
    RESULT_PATH,
    FREEZER_PATH,
    CHECKER_PATH,
    LEDGER_PATH,
}
DECISION_ENUM = {
    "PROMOTE_AS_NEW",
    "MERGE_INTO_REUSABLE",
    "SOURCE_SPECIFIC_REFERENCE_ONLY",
    "NEEDS_REPAIR",
    "REJECT",
}
APPLICABILITY_ENUM = {
    "PRESERVE",
    "NARROW",
    "EVIDENCE_BACKED_EXPAND",
    "CLEAR_ALL_AND_RETAIN_REFERENCE_ONLY",
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
}
READY_TRUE_KEYS = {
    "runtime_ingest_ready",
    "generation_allowed",
    "generation_600_allowed",
    "generation_3600_allowed",
    "expand_600_allowed",
    "expand_3600_allowed",
    "CandidatePack_ready",
    "candidatepack_ready",
    "KE_ready",
    "Serving_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_ready",
}


def add_error(errors: list[dict[str, str]], code: str, section: str, detail: str) -> None:
    errors.append({"code": code, "section": section, "detail": detail})


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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


def dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"JSONL row is not object: {path}:{line_number}")
        rows.append(value)
    return rows


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def load_freezer(root: Path) -> Any:
    spec = importlib.util.spec_from_file_location("component_review_freezer", root / FREEZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load freezer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root: Path, args: list[str]) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def changed_paths(root: Path) -> set[Path]:
    paths: set[Path] = set()
    head = (git(root, ["rev-parse", "HEAD"]) or "").strip()
    if head:
        if head == BASELINE_HEAD:
            names = git(root, ["diff", "--name-only", "HEAD"]) or ""
        else:
            names = git(root, ["diff", "--name-only", f"{BASELINE_HEAD}..HEAD"]) or ""
            names += git(root, ["diff", "--name-only", "HEAD"]) or ""
        paths.update(Path(line) for line in names.splitlines() if line)
    untracked = git(root, ["ls-files", "--others", "--exclude-standard"]) or ""
    paths.update(Path(line) for line in untracked.splitlines() if line)
    return paths


def load_baseline_yaml(root: Path, path: Path) -> dict[str, Any] | None:
    text = git(root, ["show", f"{BASELINE_HEAD}:{path.as_posix()}"])
    if text is None:
        return None
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else None


def check_keys(
    value: dict[str, Any],
    allowed: set[str],
    errors: list[dict[str, str]],
    code: str,
    section: str,
) -> None:
    extra = sorted(set(value) - allowed)
    missing = sorted(allowed - set(value))
    if extra or missing:
        add_error(errors, code, section, f"extra={extra} missing={missing}")


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


def string_leaf_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, str):
        values.append(value)
    elif isinstance(value, dict):
        for child in value.values():
            values.extend(string_leaf_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(string_leaf_values(child))
    return values


@lru_cache(maxsize=8192)
def substring_set(value: str, length: int) -> frozenset[str]:
    return frozenset(value[index : index + length] for index in range(len(value) - length + 1))


def max_common_substring_len(a: str, b: str, cap: int = 18) -> int:
    if not a or not b:
        return 0
    if len(a) > len(b):
        a, b = b, a
    max_len = min(len(a), len(b), cap)
    for length in range(max_len, 0, -1):
        needles = substring_set(b, length)
        for index in range(len(a) - length + 1):
            if a[index : index + length] in needles:
                return length
    return 0


def validate_preflight(root: Path, freezer: Any, errors: list[dict[str, str]], enforce_git: bool) -> None:
    if enforce_git:
        branch = (git(root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "").strip()
        if branch != "master":
            add_error(errors, "E_BRANCH", "git", f"branch={branch}")
        head = (git(root, ["rev-parse", "HEAD"]) or "").strip()
        if head != BASELINE_HEAD and git(root, ["merge-base", "--is-ancestor", BASELINE_HEAD, "HEAD"]) is None:
            add_error(errors, "E_BASELINE", "git", "baseline not current or ancestor")
        unexpected = sorted(path.as_posix() for path in changed_paths(root) - ALLOWED_CHANGED_PATHS)
        if unexpected:
            add_error(errors, "E_WRITE_SURFACE", "git", f"unexpected changed paths: {unexpected}")

    if sha256_file(root / freezer.S1_CONTRACT_PATH) != freezer.S1_DIGESTS["contract"]:
        add_error(errors, "E_S1_DIGEST", "S1", "contract changed")
    if sha256_file(root / freezer.S1_PROFILES_PATH) != freezer.S1_DIGESTS["profiles"]:
        add_error(errors, "E_S1_DIGEST", "S1", "profiles changed")
    if sha256_file(root / freezer.S1_CANDIDATES_PATH) != freezer.S1_DIGESTS["candidates"]:
        add_error(errors, "E_S1_DIGEST", "S1", "candidates changed")
    if sha256_file(root / freezer.S1_BUNDLES_PATH) != freezer.S1_DIGESTS["bundles"]:
        add_error(errors, "E_S1_DIGEST", "S1", "bundles changed")
    if sha256_file(root / freezer.S1_HANDOFF_PATH) != freezer.S1_DIGESTS["pilot_handoff"]:
        add_error(errors, "E_S1_DIGEST", "S1", "handoff changed")
    s1_5_files = {
        "profiles_v0_2": freezer.S1_5_PROFILES_PATH,
        "legacy_migration": freezer.S1_5_MIGRATION_PATH,
        "coverage": freezer.S1_5_COVERAGE_PATH,
        "result": freezer.S1_5_RESULT_PATH,
    }
    for key, path in s1_5_files.items():
        if sha256_file(root / path) != freezer.S1_5_FILE_SHA256[key]:
            add_error(errors, "E_S1_5_FILE_DIGEST", key, "file sha256 changed")
    profile_registry = load_yaml(root / freezer.S1_5_PROFILES_PATH)["content_product_profile_registry"]
    if profile_registry.get("registry_digest") != freezer.S1_5_INTERNAL_DIGESTS["profiles_v0_2"]:
        add_error(errors, "E_S1_5_INTERNAL_DIGEST", "profiles", "internal digest changed")
    migration = load_yaml(root / freezer.S1_5_MIGRATION_PATH)["legacy_profile_migration"]
    if migration.get("migration_digest") != freezer.S1_5_INTERNAL_DIGESTS["legacy_migration"]:
        add_error(errors, "E_S1_5_INTERNAL_DIGEST", "migration", "internal digest changed")
    coverage = load_yaml(root / freezer.S1_5_COVERAGE_PATH)["content_product_profile_coverage_and_gap"]
    if coverage.get("coverage_digest") != freezer.S1_5_INTERNAL_DIGESTS["coverage"]:
        add_error(errors, "E_S1_5_INTERNAL_DIGEST", "coverage", "internal digest changed")
    result = load_yaml(root / freezer.S1_5_RESULT_PATH)["content_product_profile_20_completion_result"]
    if result.get("result_digest") != freezer.S1_5_INTERNAL_DIGESTS["result"]:
        add_error(errors, "E_S1_5_INTERNAL_DIGEST", "result", "internal digest changed")


def validate_mapping(mapping_doc: dict[str, Any], freezer: Any, errors: list[dict[str, str]]) -> None:
    root = mapping_doc.get("capability_product_composition_mapping", {})
    check_keys(
        root,
        {
            "schema_version",
            "task_id",
            "layer_1_capability_groups",
            "layer_2_content_products",
            "layer_3_composition_assets",
            "ownership_correction",
            "P0_CP_mapping",
            "role_to_default_composition_asset_class",
            "asset_supply_gaps_expected_without_evidence",
            "P0_CP_mapping_digest",
            "composition_asset_class_contract_digest",
            "mapping_digest",
        },
        errors,
        "E_CLOSED_SCHEMA",
        "mapping",
    )
    if root.get("P0_CP_mapping") != freezer.P0_CP_MAPPING:
        add_error(errors, "E_P0_CP_MAPPING", "mapping", "P0×CP mapping mismatch")
    p0_02 = root.get("layer_1_capability_groups", {}).get("values", {}).get("P0_02", {})
    if p0_02.get("cross_cutting_perspective_overlay") is not True or p0_02.get("independent_people_content_capability") is not True:
        add_error(errors, "E_P0_02_SEMANTICS", "mapping", "P0_02 cross-cutting semantics missing")
    classes = root.get("layer_3_composition_assets", {}).get("values", [])
    if classes != freezer.COMPOSITION_ASSET_CLASSES or len(classes) != 8:
        add_error(errors, "E_ASSET_CLASS_CONTRACT", "mapping", "asset class list mismatch")
    if root.get("ownership_correction", {}).get("GKB_may_create_runtime_thread") is not False:
        add_error(errors, "E_CONTINUITY_THREAD", "mapping", "GKB may create runtime thread")
    if root.get("mapping_digest") != object_digest(root, {"mapping_digest"}):
        add_error(errors, "E_MAPPING_DIGEST", "mapping", "mapping digest mismatch")


def validate_policy(policy_doc: dict[str, Any], errors: list[dict[str, str]]) -> None:
    policy = policy_doc.get("component_domain_review_policy", {})
    if policy.get("promotion_policy", {}).get("promotion_rate_target_allowed") is not False:
        add_error(errors, "E_PROMOTION_KPI", "policy", "promotion KPI allowed")
    if policy.get("component_supply_gap_policy", {}).get("do_not_auto_create_from_profile_description") is not True:
        add_error(errors, "E_FORCE_FILL_ASSET_CLASSES", "policy", "auto-create gap class allowed")
    if policy.get("handoff_policy", {}).get("handoff_is_composition_plan") is not False:
        add_error(errors, "E_HANDOFF_PLAN_OWNER", "policy", "handoff can be plan")


def validate_decisions(
    decisions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    valid_cp_ids: set[str],
    freezer: Any,
    errors: list[dict[str, str]],
) -> None:
    allowed_keys = {
        "candidate_id",
        "candidate_digest",
        "source_asset_id",
        "source_P0_group",
        "component_role",
        "proposed_composition_asset_class",
        "original_applicable_product_ids",
        "reviewed_applicable_product_ids",
        "applicability_change",
        "review_dimensions",
        "decision",
        "target_reusable_component_id",
        "decision_reason_codes",
        "domain_rationale",
        "reviewer",
        "review_method",
        "external_LLM_called",
    }
    candidate_by_id = {item["component_id"]: item for item in candidates}
    decision_ids = [item.get("candidate_id") for item in decisions]
    if len(decisions) != 89 or len(decision_ids) != len(set(decision_ids)):
        add_error(errors, "E_CANDIDATE_REVIEW_COUNT", "decisions", f"count={len(decisions)} unique={len(set(decision_ids))}")
    if set(decision_ids) != set(candidate_by_id):
        add_error(errors, "E_CANDIDATE_REVIEW_SET", "decisions", "candidate review set mismatch")
    registry_ids = {item["component_id"] for item in registry}
    contribution_count: Counter[str] = Counter()
    for record in decisions:
        cid = str(record.get("candidate_id"))
        check_keys(record, allowed_keys, errors, "E_CLOSED_SCHEMA", f"decision:{cid}")
        if cid not in candidate_by_id:
            add_error(errors, "E_UNKNOWN_CANDIDATE", cid, "unknown candidate id")
            continue
        candidate = candidate_by_id[cid]
        if record.get("candidate_digest") != candidate.get("component_digest"):
            add_error(errors, "E_CANDIDATE_DIGEST", cid, "candidate digest mismatch")
        if record.get("component_role") != candidate.get("component_role"):
            add_error(errors, "E_CANDIDATE_ROLE", cid, "role mismatch")
        expected_class = freezer.ROLE_TO_CLASS[candidate["component_role"]]
        if record.get("proposed_composition_asset_class") != expected_class:
            add_error(errors, "E_ASSET_CLASS_MAPPING", cid, "asset class mismatch")
        if record.get("decision", {}).get("enum") not in DECISION_ENUM:
            add_error(errors, "E_DECISION_ENUM", cid, "bad decision enum")
        if record.get("applicability_change", {}).get("enum") not in APPLICABILITY_ENUM:
            add_error(errors, "E_APPLICABILITY_ENUM", cid, "bad applicability enum")
        if record.get("applicability_change", {}).get("enum") == "EVIDENCE_BACKED_EXPAND" and not record.get("applicability_change", {}).get("rationale"):
            add_error(errors, "E_EXPAND_WITHOUT_RATIONALE", cid, "missing expansion rationale")
        reviewed = record.get("reviewed_applicable_product_ids", [])
        if any(cp not in valid_cp_ids for cp in reviewed):
            add_error(errors, "E_UNKNOWN_CP", cid, f"unknown reviewed CP {reviewed}")
        if "primary_content_product_type_id" in record:
            add_error(errors, "E_PRIMARY_CP", cid, "candidate owns primary CP")
        target = record.get("target_reusable_component_id")
        if record.get("decision", {}).get("enum") in {"PROMOTE_AS_NEW", "MERGE_INTO_REUSABLE"}:
            contribution_count[cid] += 1
            if target not in registry_ids:
                add_error(errors, "E_MERGE_TARGET", cid, f"missing target {target}")
        if record.get("external_LLM_called") is not False:
            add_error(errors, "E_EXTERNAL_LLM", cid, "external LLM called")
    if any(count > 1 for count in contribution_count.values()):
        add_error(errors, "E_MULTI_REUSABLE_CONTRIBUTION", "decisions", "candidate contributes to more than one reusable")


def validate_registry(
    registry: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    valid_cp_ids: set[str],
    freezer: Any,
    errors: list[dict[str, str]],
) -> int:
    reusable_keys = {
        "component_id",
        "component_version",
        "lifecycle",
        "composition_asset_class",
        "source_component_role",
        "applicable_content_product_type_ids",
        "capability_bindings",
        "abstract_payload",
        "input_slot_contract",
        "compatibility_tag_refs",
        "incompatible_condition_refs",
        "forbidden_combination_rule_refs",
        "role_authority_requirement",
        "claim_boundary",
        "surface_realization_policy",
        "truth_boundary",
        "lineage",
        "component_digest",
    }
    ids = [item.get("component_id") for item in registry]
    if len(ids) != len(set(ids)):
        add_error(errors, "E_REGISTRY_ID", "registry", "duplicate component id")
    candidate_by_id = {item["component_id"]: item for item in candidates}
    decision_by_candidate = {item["candidate_id"]: item for item in decisions}
    signatures: set[str] = set()
    max_overlap = 0
    parent_records = freezer.source_record_index()
    all_parent_bodies = [str(record.get("body_text", "")) for record in parent_records.values()]
    for component in registry:
        cid = str(component.get("component_id"))
        check_keys(component, reusable_keys, errors, "E_CLOSED_SCHEMA", f"registry:{cid}")
        if component.get("lifecycle") != "reviewed_reusable":
            add_error(errors, "E_REGISTRY_LIFECYCLE", cid, "not reviewed reusable")
        if component.get("composition_asset_class") not in freezer.COMPOSITION_ASSET_CLASSES:
            add_error(errors, "E_ASSET_CLASS_CONTRACT", cid, "unknown class")
        if component.get("source_component_role") not in freezer.ROLE_TO_CLASS:
            add_error(errors, "E_SOURCE_ROLE", cid, "unknown role")
        if freezer.ROLE_TO_CLASS.get(component.get("source_component_role")) != component.get("composition_asset_class"):
            add_error(errors, "E_ASSET_CLASS_MAPPING", cid, "role/class mismatch")
        if "primary_content_product_type_id" in component:
            add_error(errors, "E_PRIMARY_CP", cid, "component owns primary CP")
        cps = component.get("applicable_content_product_type_ids", [])
        if not cps or any(cp not in valid_cp_ids for cp in cps):
            add_error(errors, "E_COMPONENT_APPLICABLE_CP", cid, f"bad CPs {cps}")
        if any(component.get("truth_boundary", {}).values()):
            add_error(errors, "E_TRUTH_BOUNDARY", cid, "truth boundary true")
        if component.get("surface_realization_policy", {}).get("parent_surface_verbatim_allowed") is not False:
            add_error(errors, "E_SURFACE_COPY", cid, "parent surface allowed")
        if component.get("surface_realization_policy", {}).get("source_sentence_template_allowed") is not False:
            add_error(errors, "E_SURFACE_COPY", cid, "source template allowed")
        if recursive_forbidden_fields(component):
            add_error(errors, "E_FORBIDDEN_SURFACE_FIELD", cid, f"forbidden fields {recursive_forbidden_fields(component)}")
        if recursive_ready_true(component):
            add_error(errors, "E_READY_TRUE", cid, f"ready true {recursive_ready_true(component)}")
        lineage = component.get("lineage", {})
        source_refs = lineage.get("source_candidate_refs", [])
        if not source_refs:
            add_error(errors, "E_LINEAGE", cid, "empty candidate lineage")
        for ref in source_refs:
            candidate_id = ref.get("candidate_id")
            if candidate_id not in candidate_by_id:
                add_error(errors, "E_LINEAGE", cid, f"unknown lineage candidate {candidate_id}")
                continue
            if decision_by_candidate.get(candidate_id, {}).get("target_reusable_component_id") != cid:
                add_error(errors, "E_LINEAGE", cid, f"decision target mismatch for {candidate_id}")
        role = component.get("source_component_role")
        abstract = component.get("abstract_payload", {})
        role_fields = abstract.get("role_specific_fields", {})
        if role == "professional_judgment":
            for key in ["authority_role_types", "required_fact_slots", "claim_route"]:
                if not role_fields.get(key):
                    add_error(errors, "E_PROFESSIONAL_JUDGMENT", cid, f"missing {key}")
        if role == "trigger" and role_fields.get("fabricated_conflict_allowed") is True:
            add_error(errors, "E_TENSION_FAKE_CONFLICT", cid, "fabricated conflict allowed")
        if role == "visual_beat" and (
            not role_fields.get("action_continuity_constraint") or not role_fields.get("available_material_requirement")
        ):
            add_error(errors, "E_VISUAL_BEAT", cid, "visual material/action binding missing")
        if role == "capture_instruction" and role_fields.get("execution_layer_only") is not True:
            add_error(errors, "E_CAPTURE_LAYER", cid, "capture not execution-layer-only")
        signature = canonical_json(
            {
                "class": component.get("composition_asset_class"),
                "role": role,
                "payload_kind": abstract.get("kind"),
                "mechanism": abstract.get("mechanism"),
                "p0": component.get("capability_bindings", {}).get("supported_primary_P0_groups")
                or component.get("capability_bindings", {}).get("supported_auxiliary_P0_groups"),
            }
        )
        if signature in signatures:
            add_error(errors, "E_REGISTRY_DUPLICATE_SIGNATURE", cid, "duplicate semantic signature")
        signatures.add(signature)
        abstract_values = string_leaf_values(abstract)
        compare_values = []
        for ref in source_refs:
            candidate = candidate_by_id.get(ref.get("candidate_id"))
            if not candidate:
                continue
            compare_values.extend(string_leaf_values(candidate.get("payload", {})))
            parent_id = candidate["parent_refs"][0]["parent_asset_id"]
            compare_values.append(str(parent_records[parent_id].get("body_text", "")))
        compare_values.extend(all_parent_bodies)
        for left in abstract_values:
            for right in compare_values:
                if max_overlap < 18:
                    max_overlap = max(max_overlap, max_common_substring_len(left, right))
        if component.get("component_digest") != object_digest(component, {"component_digest"}):
            add_error(errors, "E_COMPONENT_DIGEST", cid, "component digest mismatch")
    if max_overlap > 17:
        add_error(errors, "E_OVERLAP", "registry", f"max overlap {max_overlap}")
    return max_overlap


def recompute_coverage(registry: list[dict[str, Any]], freezer: Any) -> dict[str, Any]:
    return freezer.build_coverage(registry)


def validate_coverage(coverage_doc: dict[str, Any], registry: list[dict[str, Any]], freezer: Any, errors: list[dict[str, str]]) -> None:
    expected = recompute_coverage(registry, freezer)
    if coverage_doc != expected:
        add_error(errors, "E_COVERAGE_RECOMPUTE", "coverage", "coverage does not match registry/profile recompute")
    coverage = coverage_doc.get("content_product_component_coverage", {})
    summary = coverage.get("summary", {})
    if summary.get("fixture_gap_count") != 20:
        add_error(errors, "E_FIXTURE_GAP", "coverage", "fixture gap not 20")
    for record in coverage.get("coverage_records", []):
        status = record.get("component_contract_coverage", {}).get("status")
        eligible = record.get("ORCH_contract_design_eligibility", {}).get("true_only_when_required_component_roles_complete")
        if status == "COMPLETE" and eligible is not True:
            add_error(errors, "E_COVERAGE_ELIGIBILITY", record.get("content_product_type_id", ""), "complete not eligible")
        if status != "COMPLETE" and eligible is True:
            add_error(errors, "E_COVERAGE_ELIGIBILITY", record.get("content_product_type_id", ""), "incomplete listed eligible")
        if record.get("runtime_content_generation_eligibility") is not False:
            add_error(errors, "E_RUNTIME_GENERATION_ELIGIBLE", record.get("content_product_type_id", ""), "runtime eligible true")


def validate_handoff(
    handoff_doc: dict[str, Any],
    mapping_doc: dict[str, Any],
    decisions_text: str,
    registry_text: str,
    coverage_doc: dict[str, Any],
    freezer: Any,
    errors: list[dict[str, str]],
    root: Path,
) -> None:
    handoff = handoff_doc.get("gkb_orch_reviewed_component_handoff", {})
    check_keys(
        handoff,
        {
            "handoff_kind",
            "handoff_version",
            "freeze_status",
            "producer",
            "intended_consumer",
            "pinned_inputs",
            "component_contract_eligible_profile_ids",
            "component_contract_ineligible_profile_ids",
            "fixture_calibration_ready_profile_ids",
            "runtime_generation_eligible_profile_ids",
            "runtime_excluded",
            "ownership",
            "state",
            "reviewed_reusable_component_count",
            "handoff_digest",
        },
        errors,
        "E_CLOSED_SCHEMA",
        "handoff",
    )
    pinned = handoff.get("pinned_inputs", {})
    expected = {
        "clean_120_digest": freezer.CLEAN_120_SHA256,
        "controlled_v2_contract_digest": freezer.S1_DIGESTS["contract"],
        "profiles_v0_2_digest": freezer.S1_5_INTERNAL_DIGESTS["profiles_v0_2"],
        "P0_CP_mapping_digest": mapping_doc["capability_product_composition_mapping"]["P0_CP_mapping_digest"],
        "composition_asset_class_contract_digest": mapping_doc["capability_product_composition_mapping"]["composition_asset_class_contract_digest"],
        "source_candidates_digest": freezer.S1_DIGESTS["candidates"],
        "review_decisions_digest": sha256_text(decisions_text),
        "reviewed_registry_digest": sha256_text(registry_text),
        "profile_coverage_digest": coverage_doc["content_product_component_coverage"]["coverage_digest"],
    }
    check_keys(pinned, set(expected), errors, "E_CLOSED_SCHEMA", "handoff.pinned_inputs")
    if pinned != expected:
        add_error(errors, "E_HANDOFF_DIGEST", "handoff", "pinned digest mismatch")
    coverage_summary = coverage_doc["content_product_component_coverage"]["summary"]
    if handoff.get("component_contract_eligible_profile_ids") != coverage_summary.get("eligible_profile_ids"):
        add_error(errors, "E_HANDOFF_ELIGIBLE", "handoff", "eligible list mismatch")
    if handoff.get("component_contract_ineligible_profile_ids") != coverage_summary.get("ineligible_profile_ids"):
        add_error(errors, "E_HANDOFF_ELIGIBLE", "handoff", "ineligible list mismatch")
    if handoff.get("runtime_generation_eligible_profile_ids") != []:
        add_error(errors, "E_RUNTIME_GENERATION_ELIGIBLE", "handoff", "runtime generation ids nonempty")
    ownership = handoff.get("ownership", {})
    check_keys(
        ownership,
        {
            "GKB_owns_profiles_and_component_versions",
            "GKB_may_create_canonical_CompositionPlan",
            "ORCH_owns_canonical_CompositionPlan",
            "ORCH_selects_runtime_components",
            "ORCH_binds_brand_facts_and_authorizations",
            "ORCH_owns_runtime_continuity_thread",
            "ORCH_may_mutate_GKB_assets",
            "DIFY_direct_GKB_consumption_allowed",
        },
        errors,
        "E_CLOSED_SCHEMA",
        "handoff.ownership",
    )
    if ownership.get("GKB_may_create_canonical_CompositionPlan") is not False:
        add_error(errors, "E_HANDOFF_PLAN_OWNER", "handoff", "GKB may create plan")
    if ownership.get("DIFY_direct_GKB_consumption_allowed") is not False:
        add_error(errors, "E_DIFY_DIRECT", "handoff", "DIFY direct true")
    state = handoff.get("state", {})
    check_keys(
        state,
        {
            "runtime_ingest_ready",
            "handoff_integrity_frozen",
            "ORCH_integration_complete",
            "canonical_composition_plan_count",
            "audience_facing_content_count",
            "generation_invocation_count",
        },
        errors,
        "E_CLOSED_SCHEMA",
        "handoff.state",
    )
    if state.get("runtime_ingest_ready") is not False:
        add_error(errors, "E_RUNTIME_INGEST", "handoff", "runtime ingest true")
    if state.get("canonical_composition_plan_count") != 0:
        add_error(errors, "E_COMPOSITION_PLAN", "handoff", "plan count nonzero")
    if state.get("audience_facing_content_count") != 0:
        add_error(errors, "E_AUDIENCE_CONTENT", "handoff", "audience content nonzero")
    handoff_values = [value for value in string_leaf_values(handoff) if len(value) > 17]
    parent_values = [
        str(record.get("body_text", ""))
        for record in load_jsonl(root / CLEAN_120_CORPUS_PATH)
        if len(str(record.get("body_text", ""))) > 17
    ]
    source_values = list(parent_values)
    for candidate in load_jsonl(root / freezer.S1_CANDIDATES_PATH):
        source_values.extend(value for value in string_leaf_values(candidate.get("payload", {})) if len(value) > 17)
    if any(max_common_substring_len(left, right) >= 18 for left in handoff_values for right in source_values):
        add_error(errors, "E_HANDOFF_EXACT_PAYLOAD", "handoff", "candidate exact payload leaked")
    if handoff.get("handoff_digest") != object_digest(handoff, {"handoff_digest"}):
        add_error(errors, "E_HANDOFF_DIGEST", "handoff", "handoff digest mismatch")


def validate_result(result_doc: dict[str, Any], decisions: list[dict[str, Any]], registry: list[dict[str, Any]], coverage_doc: dict[str, Any], max_overlap: int, errors: list[dict[str, str]], root: Path) -> None:
    result = result_doc.get("component_review_20cp_and_handoff_result", {})
    if result.get("verdict") != "CONTROLLED_V2_89_COMPONENT_REVIEWED_AND_20CP_HANDOFF_FROZEN_PENDING_CLAUDE_GUARDIAN":
        add_error(errors, "E_RESULT_VERDICT", "result", "verdict mismatch")
    decision_counts = Counter(item["decision"]["enum"] for item in decisions)
    coverage_summary = coverage_doc["content_product_component_coverage"]["summary"]
    expected_counts = {
        "reviewed_candidate_count": len(decisions),
        "reviewed_reusable_component_count": len(registry),
        "merged_candidate_count": decision_counts["MERGE_INTO_REUSABLE"],
        "source_specific_reference_only_count": decision_counts["SOURCE_SPECIFIC_REFERENCE_ONLY"],
        "needs_repair_count": decision_counts["NEEDS_REPAIR"],
        "rejected_count": decision_counts["REJECT"],
        "component_contract_complete_profile_count": coverage_summary["complete_count"],
        "component_contract_partial_profile_count": coverage_summary["partial_count"],
        "component_contract_none_profile_count": coverage_summary["none_count"],
        "fixture_gap_count": 20,
        "runtime_generation_eligible_profile_count": 0,
        "canonical_composition_plan_count": 0,
        "audience_facing_content_count": 0,
    }
    if result.get("counts") != expected_counts:
        add_error(errors, "E_RESULT_COUNTS", "result", "counts mismatch")
    if result.get("max_verbatim_overlap_chars") != max_overlap:
        add_error(errors, "E_OVERLAP", "result", "max overlap mismatch")
    if recursive_ready_true(result):
        add_error(errors, "E_READY_TRUE", "result", f"ready true {recursive_ready_true(result)}")
    for rel_path, expected_digest in result.get("generated_file_digests", {}).items():
        path = root / rel_path
        if not path.exists() or sha256_file(path) != expected_digest:
            add_error(errors, "E_RECORDED_DIGEST", "result", f"digest mismatch {rel_path}")
    if result.get("result_digest") != object_digest(result, {"result_digest"}):
        add_error(errors, "E_RESULT_DIGEST", "result", "result digest mismatch")


def validate_diff_scan(root: Path, errors: list[dict[str, str]]) -> None:
    forbidden_file_terms = ["compositionplan", "assignment", "draft", "generation_record"]
    changed = changed_paths(root)
    task_dir = root / TASK_DIR
    if task_dir.exists():
        changed.update(path.relative_to(root) for path in task_dir.rglob("*") if path.is_file())
    for path in changed:
        lower = path.as_posix().lower()
        if any(term in lower for term in forbidden_file_terms):
            add_error(errors, "E_FORBIDDEN_FILE", "git-diff", f"forbidden file path {path}")
    for path in [MAPPING_PATH, POLICY_PATH, DECISIONS_PATH, REGISTRY_PATH, COVERAGE_PATH, HANDOFF_PATH, RESULT_PATH]:
        if not (root / path).exists():
            continue
        text = (root / path).read_text(encoding="utf-8")
        if "publishable copy:" in text.lower() or "audience_facing_body:" in text:
            add_error(errors, "E_AUDIENCE_CONTENT", path.as_posix(), "audience content marker")


def validate_ledger(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    ledger = load_yaml(root / LEDGER_PATH)
    root_node = ledger.get("grc_3600_execution_plan_status", {})
    migration = root_node.get("route_migration_21")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_ROUTE21", "ledger", "route_migration_21 missing")
        return
    if migration.get("additive_only") is not True or migration.get("no_existing_step_status_changed") is not True:
        add_error(errors, "E_LEDGER_NON_ADDITIVE_DECLARATION", "ledger", "not additive")
    s2 = migration.get("S2", {})
    if s2.get("status") != "EXECUTED_PENDING_CLAUDE_GUARDIAN":
        add_error(errors, "E_LEDGER_S2", "ledger", "S2 status mismatch")
    for flag in recursive_ready_true(migration):
        add_error(errors, "E_READY_TRUE", "ledger", f"ready true {flag}")
    if migration.get("migration_digest") != object_digest(migration, {"migration_digest"}):
        add_error(errors, "E_LEDGER_DIGEST", "ledger", "migration digest mismatch")
    if enforce_git:
        baseline = load_baseline_yaml(root, LEDGER_PATH)
        if baseline is None:
            add_error(errors, "E_LEDGER_BASELINE", "ledger", "cannot load baseline")
        else:
            current_without = copy.deepcopy(ledger)
            baseline_without = copy.deepcopy(baseline)
            current_without["grc_3600_execution_plan_status"].pop("route_migration_21", None)
            if current_without != baseline_without:
                add_error(errors, "E_LEDGER_NON_ADDITIVE", "ledger", "changes beyond route_migration_21")


def validate_idempotence(root: Path, freezer: Any, errors: list[dict[str, str]]) -> None:
    expected = freezer.build_artifacts(root)
    for rel_path, expected_text in expected.items():
        path = root / rel_path
        if not path.exists():
            add_error(errors, "E_IDEMPOTENCE", "freezer", f"missing {rel_path}")
        elif path.read_text(encoding="utf-8") != expected_text:
            add_error(errors, "E_IDEMPOTENCE", "freezer", f"content mismatch {rel_path}")


def collect_errors(root: Path, *, enforce_git: bool = True, compare_expected: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    freezer = load_freezer(root)
    validate_preflight(root, freezer, errors, enforce_git)
    for path in [MAPPING_PATH, POLICY_PATH, DECISIONS_PATH, REGISTRY_PATH, COVERAGE_PATH, HANDOFF_PATH, RESULT_PATH, FREEZER_PATH, CHECKER_PATH]:
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE_MISSING", "files", f"missing {path}")
    if any(error["code"] == "E_REQUIRED_FILE_MISSING" for error in errors):
        return errors

    mapping_doc = load_yaml(root / MAPPING_PATH)
    policy_doc = load_yaml(root / POLICY_PATH)
    decisions = load_jsonl(root / DECISIONS_PATH)
    registry = load_jsonl(root / REGISTRY_PATH)
    coverage_doc = load_yaml(root / COVERAGE_PATH)
    handoff_doc = load_yaml(root / HANDOFF_PATH)
    result_doc = load_yaml(root / RESULT_PATH)
    candidates = load_jsonl(root / freezer.S1_CANDIDATES_PATH)
    profiles = load_yaml(root / freezer.S1_5_PROFILES_PATH)["content_product_profile_registry"]["profiles"]
    valid_cp_ids = {profile["content_product_type_id"] for profile in profiles}

    for doc_name, doc in [
        ("mapping", mapping_doc),
        ("policy", policy_doc),
        ("coverage", coverage_doc),
        ("handoff", handoff_doc),
        ("result", result_doc),
    ]:
        if recursive_forbidden_fields(doc):
            add_error(errors, "E_FORBIDDEN_SURFACE_FIELD", doc_name, str(recursive_forbidden_fields(doc)))
        if recursive_ready_true(doc):
            add_error(errors, "E_READY_TRUE", doc_name, str(recursive_ready_true(doc)))

    validate_mapping(mapping_doc, freezer, errors)
    validate_policy(policy_doc, errors)
    validate_decisions(decisions, candidates, registry, valid_cp_ids, freezer, errors)
    max_overlap = validate_registry(registry, decisions, candidates, valid_cp_ids, freezer, errors)
    validate_coverage(coverage_doc, registry, freezer, errors)
    decisions_text = (root / DECISIONS_PATH).read_text(encoding="utf-8")
    registry_text = (root / REGISTRY_PATH).read_text(encoding="utf-8")
    validate_handoff(handoff_doc, mapping_doc, decisions_text, registry_text, coverage_doc, freezer, errors, root)
    validate_result(result_doc, decisions, registry, coverage_doc, max_overlap, errors, root)
    validate_diff_scan(root, errors)
    validate_ledger(root, errors, enforce_git)
    if compare_expected:
        validate_idempotence(root, freezer, errors)
    return errors


def copy_for_selftest(source_root: Path, tmp_root: Path) -> None:
    freezer = load_freezer(source_root)
    paths = [
        CHECKER_PATH,
        LEDGER_PATH,
        freezer.S1_CONTRACT_PATH,
        freezer.S1_PROFILES_PATH,
        freezer.S1_CANDIDATES_PATH,
        freezer.S1_BUNDLES_PATH,
        freezer.S1_HANDOFF_PATH,
        freezer.S1_SELECTION_PATH,
        CLEAN_120_CORPUS_PATH,
        freezer.S1_5_PROFILES_PATH,
        freezer.S1_5_MIGRATION_PATH,
        freezer.S1_5_COVERAGE_PATH,
        freezer.S1_5_RESULT_PATH,
    ]
    for path in paths:
        target = tmp_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / path, target)
    shutil.copytree(source_root / TASK_DIR, tmp_root / TASK_DIR)


def mutate_yaml_file(root: Path, path: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    data = load_yaml(root / path)
    mutator(data)
    dump_yaml(root / path, data)


def mutate_jsonl_file(root: Path, path: Path, mutator: Callable[[list[dict[str, Any]]], None]) -> None:
    rows = load_jsonl(root / path)
    mutator(rows)
    dump_jsonl(root / path, rows)


def run_selftest_case(source_root: Path, name: str, expected_code: str, mutator: Callable[[Path], None]) -> tuple[str, bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="review20-selftest-") as tmp:
        tmp_root = Path(tmp)
        copy_for_selftest(source_root, tmp_root)
        mutator(tmp_root)
        codes = [error["code"] for error in collect_errors(tmp_root, enforce_git=False, compare_expected=False)]
        return name, expected_code in codes, codes


def duplicate_registry_signature(rows: list[dict[str, Any]]) -> None:
    rows[1]["composition_asset_class"] = copy.deepcopy(rows[0]["composition_asset_class"])
    rows[1]["source_component_role"] = copy.deepcopy(rows[0]["source_component_role"])
    rows[1]["capability_bindings"] = copy.deepcopy(rows[0]["capability_bindings"])
    rows[1]["abstract_payload"] = copy.deepcopy(rows[0]["abstract_payload"])


def selftest(root: Path) -> int:
    cases: list[tuple[str, str, Callable[[Path], None]]] = [
        ("candidate_missing", "E_CANDIDATE_REVIEW_COUNT", lambda tmp: mutate_jsonl_file(tmp, DECISIONS_PATH, lambda rows: rows.pop())),
        ("candidate_duplicate", "E_CANDIDATE_REVIEW_COUNT", lambda tmp: mutate_jsonl_file(tmp, DECISIONS_PATH, lambda rows: rows.append(copy.deepcopy(rows[0])))),
        ("candidate_unknown", "E_UNKNOWN_CANDIDATE", lambda tmp: mutate_jsonl_file(tmp, DECISIONS_PATH, lambda rows: rows[0].__setitem__("candidate_id", "NOPE"))),
        ("promotion_kpi", "E_PROMOTION_KPI", lambda tmp: mutate_yaml_file(tmp, POLICY_PATH, lambda data: data["component_domain_review_policy"]["promotion_policy"].__setitem__("promotion_rate_target_allowed", True))),
        ("unreviewed_promotion", "E_LINEAGE", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: rows[0]["lineage"]["source_candidate_refs"][0].__setitem__("candidate_id", "NO_REVIEW"))),
        ("unknown_cp", "E_UNKNOWN_CP", lambda tmp: mutate_jsonl_file(tmp, DECISIONS_PATH, lambda rows: rows[0].__setitem__("reviewed_applicable_product_ids", ["CP99"]))),
        ("mechanical_old_profile", "E_UNKNOWN_CP", lambda tmp: mutate_jsonl_file(tmp, DECISIONS_PATH, lambda rows: rows[0].__setitem__("reviewed_applicable_product_ids", ["CP_ROLE_WORK_VLOG"]))),
        ("expand_without_rationale", "E_EXPAND_WITHOUT_RATIONALE", lambda tmp: mutate_jsonl_file(tmp, DECISIONS_PATH, lambda rows: rows[0]["applicability_change"].__setitem__("rationale", ""))),
        ("candidate_primary_cp", "E_CLOSED_SCHEMA", lambda tmp: mutate_jsonl_file(tmp, DECISIONS_PATH, lambda rows: rows[0].__setitem__("primary_content_product_type_id", "CP01"))),
        ("p0_mapping_wrong", "E_P0_CP_MAPPING", lambda tmp: mutate_yaml_file(tmp, MAPPING_PATH, lambda data: data["capability_product_composition_mapping"]["P0_CP_mapping"]["CP01"].__setitem__("primary_capabilities", ["P0_01"]))),
        ("p0_02_not_cross", "E_P0_02_SEMANTICS", lambda tmp: mutate_yaml_file(tmp, MAPPING_PATH, lambda data: data["capability_product_composition_mapping"]["layer_1_capability_groups"]["values"]["P0_02"].__setitem__("cross_cutting_perspective_overlay", False))),
        ("asset_class_missing", "E_ASSET_CLASS_CONTRACT", lambda tmp: mutate_yaml_file(tmp, MAPPING_PATH, lambda data: data["capability_product_composition_mapping"]["layer_3_composition_assets"].__setitem__("values", ["scene_action_kernel"]))),
        ("continuity_thread", "E_CONTINUITY_THREAD", lambda tmp: mutate_yaml_file(tmp, MAPPING_PATH, lambda data: data["capability_product_composition_mapping"]["ownership_correction"].__setitem__("GKB_may_create_runtime_thread", True))),
        ("force_fill_assets", "E_FORCE_FILL_ASSET_CLASSES", lambda tmp: mutate_yaml_file(tmp, POLICY_PATH, lambda data: data["component_domain_review_policy"]["component_supply_gap_policy"].__setitem__("do_not_auto_create_from_profile_description", False))),
        ("copy_parent_sentence", "E_OVERLAP", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: rows[0]["abstract_payload"].__setitem__("function", "负责人轻轻拉开领边，再松手看它怎么回位"))),
        ("overlap_too_high", "E_OVERLAP", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: rows[0]["abstract_payload"].__setitem__("function", "structured_capture_instruction"))),
        ("forbidden_body_field", "E_FORBIDDEN_SURFACE_FIELD", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: rows[0].__setitem__("body_text", "x"))),
        ("hidden_extra_field", "E_CLOSED_SCHEMA", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: rows[0].__setitem__("hidden", True))),
        ("nested_ready_true", "E_READY_TRUE", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: rows[0]["abstract_payload"].__setitem__("runtime_ingest_ready", True))),
        ("truth_true", "E_TRUTH_BOUNDARY", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: rows[0]["truth_boundary"].__setitem__("brand_fact_source", True))),
        ("judgment_missing_authority", "E_PROFESSIONAL_JUDGMENT", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: next(r for r in rows if r["source_component_role"] == "professional_judgment")["abstract_payload"]["role_specific_fields"].__setitem__("authority_role_types", []))),
        ("spoken_complete_line", "E_FORBIDDEN_SURFACE_FIELD", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: rows[0].__setitem__("spoken_script", "完整口播"))),
        ("capture_not_execution", "E_CAPTURE_LAYER", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, lambda rows: next(r for r in rows if r["source_component_role"] == "capture_instruction")["abstract_payload"]["role_specific_fields"].__setitem__("execution_layer_only", False))),
        ("merge_target_missing", "E_MERGE_TARGET", lambda tmp: mutate_jsonl_file(tmp, DECISIONS_PATH, lambda rows: next(r for r in rows if r["decision"]["enum"] == "MERGE_INTO_REUSABLE").__setitem__("target_reusable_component_id", "MISSING"))),
        ("duplicate_signature", "E_REGISTRY_DUPLICATE_SIGNATURE", lambda tmp: mutate_jsonl_file(tmp, REGISTRY_PATH, duplicate_registry_signature)),
        ("coverage_recompute_bad", "E_COVERAGE_RECOMPUTE", lambda tmp: mutate_yaml_file(tmp, COVERAGE_PATH, lambda data: data["content_product_component_coverage"]["coverage_records"][0]["covered_required_roles"].append("fake"))),
        ("incomplete_eligible", "E_COVERAGE_RECOMPUTE", lambda tmp: mutate_yaml_file(tmp, COVERAGE_PATH, lambda data: data["content_product_component_coverage"]["summary"]["eligible_profile_ids"].append("CP05"))),
        ("fixture_gap_closed", "E_COVERAGE_RECOMPUTE", lambda tmp: mutate_yaml_file(tmp, COVERAGE_PATH, lambda data: data["content_product_component_coverage"]["summary"].__setitem__("fixture_gap_count", 0))),
        ("handoff_digest_forged", "E_HANDOFF_DIGEST", lambda tmp: mutate_yaml_file(tmp, HANDOFF_PATH, lambda data: data["gkb_orch_reviewed_component_handoff"]["pinned_inputs"].__setitem__("reviewed_registry_digest", "0" * 64))),
        ("handoff_exact_payload", "E_HANDOFF_EXACT_PAYLOAD", lambda tmp: mutate_yaml_file(tmp, HANDOFF_PATH, lambda data: data["gkb_orch_reviewed_component_handoff"].__setitem__("leak", "负责人轻轻拉开领边，再松手看它怎么回位"))),
        ("gkb_plan_owner", "E_HANDOFF_PLAN_OWNER", lambda tmp: mutate_yaml_file(tmp, HANDOFF_PATH, lambda data: data["gkb_orch_reviewed_component_handoff"]["ownership"].__setitem__("GKB_may_create_canonical_CompositionPlan", True))),
        ("compositionplan_file", "E_FORBIDDEN_FILE", lambda tmp: (tmp / TASK_DIR / "fake_CompositionPlan.yaml").write_text("{}", encoding="utf-8")),
        ("constant_plan_count", "E_CLOSED_SCHEMA", lambda tmp: mutate_yaml_file(tmp, HANDOFF_PATH, lambda data: data["gkb_orch_reviewed_component_handoff"]["state"].__setitem__("plan_count_source", "constant_0"))),
        ("runtime_ingest_true", "E_RUNTIME_INGEST", lambda tmp: mutate_yaml_file(tmp, HANDOFF_PATH, lambda data: data["gkb_orch_reviewed_component_handoff"]["state"].__setitem__("runtime_ingest_ready", True))),
        ("dify_direct", "E_DIFY_DIRECT", lambda tmp: mutate_yaml_file(tmp, HANDOFF_PATH, lambda data: data["gkb_orch_reviewed_component_handoff"]["ownership"].__setitem__("DIFY_direct_GKB_consumption_allowed", True))),
        ("audience_content", "E_AUDIENCE_CONTENT", lambda tmp: mutate_yaml_file(tmp, HANDOFF_PATH, lambda data: data["gkb_orch_reviewed_component_handoff"]["state"].__setitem__("audience_facing_content_count", 1))),
        ("generation_600", "E_READY_TRUE", lambda tmp: mutate_yaml_file(tmp, RESULT_PATH, lambda data: data["component_review_20cp_and_handoff_result"]["readiness_flags"].__setitem__("generation_600_allowed", True))),
        ("readiness_true", "E_READY_TRUE", lambda tmp: mutate_yaml_file(tmp, RESULT_PATH, lambda data: data["component_review_20cp_and_handoff_result"]["readiness_flags"].__setitem__("production_ready", True))),
        ("route_non_additive", "E_LEDGER_NON_ADDITIVE_DECLARATION", lambda tmp: mutate_yaml_file(tmp, LEDGER_PATH, lambda data: data["grc_3600_execution_plan_status"]["route_migration_21"].__setitem__("additive_only", False))),
    ]
    failures: list[str] = []
    for name, expected_code, mutator in cases:
        case_name, passed, codes = run_selftest_case(root, name, expected_code, mutator)
        if not passed:
            failures.append(f"{case_name}: expected {expected_code}, saw {sorted(set(codes))}")
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print(f"selftest PASS: {len(cases)} cases")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.selftest:
        return selftest(root)
    errors = collect_errors(root, enforce_git=True, compare_expected=True)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task_id": TASK_ID}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
