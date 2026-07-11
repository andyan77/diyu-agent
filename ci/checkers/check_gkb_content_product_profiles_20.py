#!/usr/bin/env python3
"""Fail-closed checker for the Controlled V2 20 content-product profiles."""

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
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml


if not __debug__:
    print("check_gkb_content_product_profiles_20 refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "GKB-CONTROLLED-V2-CONTENT-PRODUCT-PROFILE-20-COMPLETION-AND-ID-REBASELINE-001"
BASELINE_HEAD = "538b464042656dec7df0e05acff554a8a4b4528f"
CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
SCALE_600_CONTRACT_SHA256 = (
    "966190c341b070d88fbc3a25540e9c8fddf69ad8f19b90fb29badbb1ffad52a9"
)

S1_RESULT_FILE_SHA256 = "61a97a8abe3e0b3187b1d547a83832eb645624684b637f8417920dba9f63d265"
S1_RESULT_INTERNAL_DIGEST = "baf2616624ea0bb71ef87eb5f5467fd03a2738a7afeec621a3cde77a9681f711"
S1_CONTRACT_SHA256 = "7bf9315ebbb5bf97c3330695de7327af42ae30771b6315d2432c5c78d51d742c"
S1_PROFILES_V0_1_SHA256 = "c4e744f3f0505025d780f46eb12b879f1b9920ede63e4c84ffbc3fac9a715a6c"
S1_SOURCE_SELECTION_SHA256 = "36708420abc159f5a557f48c421ebf0b46a345384afdea9821c6ff0f0089f38c"
S1_CANDIDATES_SHA256 = "70ce2f7ebae3699fba6be0a0fff5d4a0a8e1023bbd32ae5a4f7340b3c4f43f7d"
S1_BUNDLES_SHA256 = "6d294274ea235962c33a8e7cd9f4d4be92d2e6ce5b48860286a1d13f08ce7970"
S1_HANDOFF_SHA256 = "12a369dcf64641a16b73636e95ba1c710fc787efa663608f446f73634a2f6223"

S1_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = S1_DIR / "content_product_profile_20_completion_001"
CONTRACT_PATH = TASK_DIR / "content_product_profile_contract.v0.2.yaml"
PROFILES_PATH = TASK_DIR / "content_product_profiles.v0.2.yaml"
MIGRATION_PATH = TASK_DIR / "content_product_profile_legacy_migration.v0.1.yaml"
COVERAGE_PATH = TASK_DIR / "content_product_profile_coverage_and_gap.v0.1.yaml"
RESULT_PATH = TASK_DIR / "content_product_profile_20_completion_result.v0.1.yaml"
VALIDATOR_PATH = TASK_DIR / "run_content_product_profile_20_validator.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_content_product_profiles_20.py")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CLEAN_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
SCALE_600_CONTRACT_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "scale_contract_600_001/"
    "p7d_600_expression_diversity_and_sampled_acceptance_contract.v0.1.yaml"
)
S1_PATHS = {
    "result": S1_DIR / "controlled_composition_v2_result.v0.1.yaml",
    "contract": S1_DIR / "controlled_composition_v2_contract.v0.1.yaml",
    "profiles_v0_1": S1_DIR / "content_product_profiles.v0.1.yaml",
    "source_selection": S1_DIR / "pilot_source_selection.v0.1.yaml",
    "candidates": S1_DIR / "component_candidate_manifest.v0.1.jsonl",
    "bundles": S1_DIR / "gkb_composition_candidate_bundles.v0.1.jsonl",
    "pilot_handoff": S1_DIR / "gkb_orch_pilot_handoff.v0.1.yaml",
}
EXPECTED_S1_DIGESTS = {
    "result": S1_RESULT_FILE_SHA256,
    "contract": S1_CONTRACT_SHA256,
    "profiles_v0_1": S1_PROFILES_V0_1_SHA256,
    "source_selection": S1_SOURCE_SELECTION_SHA256,
    "candidates": S1_CANDIDATES_SHA256,
    "bundles": S1_BUNDLES_SHA256,
    "pilot_handoff": S1_HANDOFF_SHA256,
}

ALLOWED_CHANGED_PATHS = {
    CONTRACT_PATH,
    PROFILES_PATH,
    MIGRATION_PATH,
    COVERAGE_PATH,
    RESULT_PATH,
    VALIDATOR_PATH,
    CHECKER_PATH,
    LEDGER_PATH,
}
EXPECTED_FAMILIES = {
    "F1_PEOPLE_AND_REAL_SCENE": (["CP01", "CP02", "CP03", "CP04", "CP05"], 30),
    "F2_PROFESSIONAL_AND_SEARCH": (["CP06", "CP07", "CP08", "CP09", "CP10"], 25),
    "F3_PRODUCT_RELATION_AND_AESTHETIC": (["CP11", "CP12", "CP13", "CP14"], 20),
    "F4_STORE_LOCAL_AND_RETAIL": (["CP15", "CP16", "CP17", "CP18"], 15),
    "F5_ENTERPRISE_LONG_TERM_TRUST": (["CP19", "CP20"], 10),
}
EXPECTED_CP_IDS = [f"CP{i:02d}" for i in range(1, 21)]
EXPECTED_EVENT_MODES = {
    "brand_supplied_real_event",
    "brand_fillable_prototype",
    "generic_creative_prototype",
    "collection_task_only",
}
REQUIRED_PROFILE_KEYS = {
    "schema_version",
    "profile_version",
    "content_product_type_id",
    "canonical_slug",
    "chinese_label",
    "family_id",
    "lifecycle",
    "owner",
    "runtime_plan_owner",
    "business_purpose",
    "cadence_policy",
    "target_account_roles",
    "target_platforms",
    "founder_core_inputs",
    "required_component_roles",
    "optional_component_roles",
    "input_requirements",
    "event_truth_policy",
    "narrative_constraints",
    "style_constraints",
    "continuity_policy",
    "visual_audio_requirement_refs",
    "platform_expression_requirement_refs",
    "anti_pattern_rule_refs",
    "founder_hard_guards",
    "input_sufficiency_routes",
    "quality_rubric_refs",
    "fixture_refs",
    "component_supply_state",
    "profile_digest",
}
FORBIDDEN_TRUE_KEYS = {
    "runtime_ingest_ready",
    "generation_600_allowed",
    "expand_600_allowed",
    "expand_3600_allowed",
    "CandidatePack_ready",
    "candidatepack_ready",
    "KE_ready",
    "Serving_ready",
    "ServingProjection_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_ready",
    "ORCH_profile_eligible",
    "generation_authority",
}
AUDIENCE_CONTENT_KEYS = {
    "audience_facing_body",
    "body_text",
    "title",
    "spoken_script",
    "spoken_draft",
    "script",
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
        raise TypeError(f"YAML root is not a mapping: {path}")
    return data


def dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def load_validator(root: Path) -> Any:
    spec = importlib.util.spec_from_file_location("profile20_validator", root / VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator: {root / VALIDATOR_PATH}")
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
            diff_names = git(root, ["diff", "--name-only", "HEAD"]) or ""
        else:
            diff_names = git(root, ["diff", "--name-only", f"{BASELINE_HEAD}..HEAD"]) or ""
            diff_names += git(root, ["diff", "--name-only", "HEAD"]) or ""
        paths.update(Path(line.strip()) for line in diff_names.splitlines() if line.strip())
    untracked = git(root, ["ls-files", "--others", "--exclude-standard"]) or ""
    paths.update(Path(line.strip()) for line in untracked.splitlines() if line.strip())
    return paths


def load_baseline_yaml(root: Path, path: Path) -> dict[str, Any] | None:
    text = git(root, ["show", f"{BASELINE_HEAD}:{path.as_posix()}"])
    if text is None:
        return None
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else None


def recursive_true_flags(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_TRUE_KEYS and child is True:
                hits.append(child_path)
            hits.extend(recursive_true_flags(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_true_flags(child, f"{path}[{index}]"))
    return hits


def recursive_audience_content(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in AUDIENCE_CONTENT_KEYS and child:
                hits.append(child_path)
            hits.extend(recursive_audience_content(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_audience_content(child, f"{path}[{index}]"))
    return hits


def validate_preflight(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    if enforce_git:
        branch = (git(root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "").strip()
        if branch != "master":
            add_error(errors, "E_BRANCH", "git", f"branch={branch!r}")
        head = (git(root, ["rev-parse", "HEAD"]) or "").strip()
        if head != BASELINE_HEAD and git(root, ["merge-base", "--is-ancestor", BASELINE_HEAD, "HEAD"]) is None:
            add_error(errors, "E_BASELINE_HEAD", "git", "baseline is not current head or ancestor")
        unexpected = sorted(path.as_posix() for path in changed_paths(root) - ALLOWED_CHANGED_PATHS)
        if unexpected:
            add_error(errors, "E_WRITE_SURFACE", "git", f"unexpected changed paths: {unexpected}")

    if sha256_file(root / CLEAN_120_PATH) != CLEAN_120_SHA256:
        add_error(errors, "E_CLEAN_DIGEST", "inputs", "Clean-120 digest mismatch")
    if sha256_file(root / SCALE_600_CONTRACT_PATH) != SCALE_600_CONTRACT_SHA256:
        add_error(errors, "E_SCALE_CONTRACT_DIGEST", "inputs", "600 contract digest mismatch")
    for key, path in S1_PATHS.items():
        actual = sha256_file(root / path)
        expected = EXPECTED_S1_DIGESTS[key]
        if actual != expected:
            add_error(errors, "E_S1_DIGEST_CHANGED", key, f"{actual} != {expected}")
    s1_result = load_yaml(root / S1_PATHS["result"]).get("controlled_composition_v2_result", {})
    if s1_result.get("result_digest") != S1_RESULT_INTERNAL_DIGEST:
        add_error(errors, "E_S1_RESULT_INTERNAL_DIGEST", "S1", "internal result_digest mismatch")


def validate_contract(contract_doc: dict[str, Any], errors: list[dict[str, str]]) -> None:
    contract = contract_doc.get("content_product_profile_contract_v0_2", {})
    allocation = contract.get("allocation_policy", {})
    if allocation.get("status") != "PLANNING_POLICY_NOT_EXECUTION_QUOTA":
        add_error(errors, "E_ALLOCATION_POLICY", "contract", "allocation status mismatch")
    if allocation.get("sum_percent") != 100:
        add_error(errors, "E_SHARE_SUM", "contract", "sum_percent != 100")
    if allocation.get("generation_authority") is not False or allocation.get("may_not_auto_allocate_600") is not True:
        add_error(errors, "E_ALLOCATION_AS_GENERATION", "contract", "planning share can act as generation")
    if contract.get("s1_immutability", {}).get("result_file_sha256") != S1_RESULT_FILE_SHA256:
        add_error(errors, "E_S1_DIGEST_CHANGED", "contract", "wrong S1 result file hash")
    if contract.get("s1_immutability", {}).get("result_internal_digest") != S1_RESULT_INTERNAL_DIGEST:
        add_error(errors, "E_S1_RESULT_INTERNAL_DIGEST", "contract", "wrong S1 internal digest")


def validate_profiles(registry_doc: dict[str, Any], errors: list[dict[str, str]]) -> None:
    registry = registry_doc.get("content_product_profile_registry", {})
    families = registry.get("families", {})
    profiles = registry.get("profiles", [])
    if len(families) != 5:
        add_error(errors, "E_FAMILY_COUNT", "profiles", f"family count {len(families)}")
    shares = []
    for family_id, (expected_products, expected_share) in EXPECTED_FAMILIES.items():
        family = families.get(family_id, {})
        if family.get("products") != expected_products:
            add_error(errors, "E_FAMILY_MEMBERS", family_id, f"products={family.get('products')}")
        if family.get("planning_share_percent") != expected_share:
            add_error(errors, "E_SHARE_VALUE", family_id, f"share={family.get('planning_share_percent')}")
        shares.append(family.get("planning_share_percent", 0))
    if sum(shares) != 100 or registry.get("allocation_policy", {}).get("sum_percent") != 100:
        add_error(errors, "E_SHARE_SUM", "profiles", "planning share sum mismatch")
    allocation = registry.get("allocation_policy", {})
    if allocation.get("generation_authority") is not False or allocation.get("may_not_auto_allocate_600") is not True:
        add_error(errors, "E_ALLOCATION_AS_GENERATION", "profiles", "allocation can generate")
    if len(profiles) != 20:
        add_error(errors, "E_PROFILE_COUNT", "profiles", f"profile count {len(profiles)}")
    ids = [profile.get("content_product_type_id") for profile in profiles]
    if ids != EXPECTED_CP_IDS:
        add_error(errors, "E_CP_SEQUENCE", "profiles", f"ids={ids}")
    if len(ids) != len(set(ids)):
        add_error(errors, "E_DUPLICATE_CP_ID", "profiles", "duplicate CP id")

    signatures = set()
    role_sets = set()
    unique_guard_texts: Counter[str] = Counter()
    for profile in profiles:
        cp_id = str(profile.get("content_product_type_id"))
        missing = sorted(REQUIRED_PROFILE_KEYS - set(profile))
        if missing:
            add_error(errors, "E_PROFILE_FIELDS", cp_id, f"missing {missing}")
        if profile.get("schema_version") != "v0.2" or profile.get("lifecycle") != "PROFILE_DEFINED_PENDING_COMPONENT_SUPPLY":
            add_error(errors, "E_PROFILE_FIELDS", cp_id, "schema/lifecycle mismatch")
        if profile.get("owner") != "GKB" or profile.get("runtime_plan_owner") != "ORCH":
            add_error(errors, "E_PROFILE_OWNER", cp_id, "owner/runtime owner mismatch")
        input_req = profile.get("input_requirements", {})
        for slot_key in ["required_source_slots", "required_fact_slots", "required_authorization_slots"]:
            if not isinstance(input_req.get(slot_key), list) or not input_req.get(slot_key):
                add_error(errors, "E_PROFILE_INPUT_SLOT", cp_id, f"{slot_key} missing")
        if "forbidden_event_truth_modes" in profile:
            add_error(errors, "E_EVENT_MODE_SECOND_TRUTH", cp_id, "forbidden_event_truth_modes present")
        event_policy = profile.get("event_truth_policy", {})
        if set(event_policy.get("allowed_event_truth_modes", [])) != EXPECTED_EVENT_MODES or event_policy.get("default_deny_unlisted") is not True:
            add_error(errors, "E_EVENT_POLICY", cp_id, "event mode/default-deny mismatch")
        if "missing_input_routes" in profile or "allowed_degraded_outputs" in profile:
            add_error(errors, "E_MISSING_ROUTE_SECOND_TRUTH", cp_id, "duplicate missing route truth")
        routes = profile.get("input_sufficiency_routes", [])
        route_ids = [route.get("route_id") for route in routes if isinstance(route, dict)]
        if len(route_ids) != len(set(route_ids)) or not route_ids:
            add_error(errors, "E_MISSING_ROUTE_SECOND_TRUTH", cp_id, "route ids duplicate or empty")
        fixtures = profile.get("fixture_refs", {})
        if fixtures.get("may_enter_generation_prompt") is not False:
            add_error(errors, "E_FIXTURE_PROMPT", cp_id, "fixture may enter generation prompt")
        if fixtures.get("may_supply_facts") is not False:
            add_error(errors, "E_FIXTURE_FACT", cp_id, "fixture may supply facts")
        if fixtures.get("fixture_coverage") not in {"complete", "partial", "missing_explicit"}:
            add_error(errors, "E_FIXTURE_COVERAGE", cp_id, "fixture coverage invalid")
        supply = profile.get("component_supply_state", {})
        if supply.get("reviewed_reusable_component_count") != 0:
            add_error(errors, "E_COMPONENT_SUPPLY_CLAIM", cp_id, "reviewed reusable count nonzero")
        if supply.get("required_role_coverage") != "NOT_EVALUATED":
            add_error(errors, "E_COMPONENT_SUPPLY_CLAIM", cp_id, "role coverage evaluated")
        if supply.get("ORCH_profile_eligible") is not False:
            add_error(errors, "E_ORCH_ELIGIBLE", cp_id, "ORCH eligible true")
        if profile.get("profile_digest") != object_digest(profile, {"profile_digest"}):
            add_error(errors, "E_PROFILE_DIGEST", cp_id, "profile digest mismatch")
        signatures.add("|".join(profile.get("founder_core_inputs", [])))
        role_sets.add("|".join(item.get("role", "") for item in profile.get("required_component_roles", [])))
        for guard in profile.get("founder_hard_guards", []):
            unique_guard_texts[str(guard.get("text"))] += 1
        narrative_families = profile.get("narrative_constraints", {}).get(
            "allowed_narrative_operator_families", []
        )
        if narrative_families == ["先看—再看—免责声明—CTA"]:
            add_error(errors, "E_TEMPLATE_COPY", cp_id, "profile collapsed to forbidden template pattern")

    if len(signatures) != 20:
        add_error(errors, "E_PROFILE_SIGNATURE_DUPLICATE", "profiles", "core input signatures not unique")
    if len(role_sets) <= 1:
        add_error(errors, "E_PROFILE_ROLE_TEMPLATE", "profiles", "required role sets all identical")
    for profile in profiles:
        cp_id = str(profile.get("content_product_type_id"))
        guard_texts = [str(item.get("text")) for item in profile.get("founder_hard_guards", [])]
        if not any(unique_guard_texts[text] == 1 for text in guard_texts):
            add_error(errors, "E_PROFILE_HARD_GUARD_UNIQUE", cp_id, "no unique hard guard")

    by_id = {profile["content_product_type_id"]: profile for profile in profiles if "content_product_type_id" in profile}
    cp14_roles = {item["role"] for item in by_id.get("CP14", {}).get("required_component_roles", [])}
    if cp14_roles & {"spoken_line_intent", "CTA"}:
        add_error(errors, "E_CP14_SPOKEN_CTA", "CP14", "spoken_line or CTA required")
    cp04 = by_id.get("CP04", {})
    cp04_json = canonical_json(cp04)
    if "participating_roles" not in cp04_json or "participant_authorizations" not in cp04_json:
        add_error(errors, "E_CP04_MULTI_AUTH", "CP04", "multi-role authorization missing")
    for cp_id in ["CP05", "CP10", "CP12", "CP20"]:
        continuity = by_id.get(cp_id, {}).get("continuity_policy", {})
        if continuity.get("runtime_thread_required") is not True or not continuity.get("model"):
            add_error(errors, "E_CONTINUITY", cp_id, "time-state continuity missing")
    cp16_json = canonical_json(by_id.get("CP16", {}))
    if "privacy" not in cp16_json and "隐私" not in cp16_json:
        add_error(errors, "E_CP16_PRIVACY", "CP16", "privacy/consent missing")
    cp18 = by_id.get("CP18", {})
    cp18_json = canonical_json(
        {
            "founder_core_inputs": cp18.get("founder_core_inputs", []),
            "input_requirements": cp18.get("input_requirements", {}),
            "style_constraints": cp18.get("style_constraints", {}),
            "founder_hard_guards": cp18.get("founder_hard_guards", []),
            "target_account_roles": cp18.get("target_account_roles", []),
        }
    )
    if "local" not in cp18_json and "地方" not in cp18_json and "真实城市" not in cp18_json:
        add_error(errors, "E_CP18_LOCATION", "CP18", "location/local materials missing")
    for cp_id in ["CP19", "CP20"]:
        if by_id.get(cp_id, {}).get("cadence_policy") != "low_frequency":
            add_error(errors, "E_LOW_FREQUENCY", cp_id, "not low_frequency")
    cp20_json = canonical_json(by_id.get("CP20", {}))
    for token in ["public_commitment", "execution_evidence", "result_or_deviation", "next_review_time"]:
        if token not in cp20_json:
            add_error(errors, "E_CP20_EVIDENCE_REVIEW", "CP20", f"{token} missing")
    if registry.get("registry_digest") != object_digest(registry, {"registry_digest"}):
        add_error(errors, "E_REGISTRY_DIGEST", "profiles", "registry digest mismatch")


def validate_migration(migration_doc: dict[str, Any], errors: list[dict[str, str]]) -> None:
    migration = migration_doc.get("legacy_profile_migration", {})
    mappings = migration.get("mappings", {})
    if mappings.get("CP_ROLE_WORK_VLOG", {}).get("canonical_target") != "CP01":
        add_error(errors, "E_MIGRATION_DIRECT", "migration", "work vlog direct mapping wrong")
    if mappings.get("CP_STORE_MICRO_DOCUMENTARY", {}).get("canonical_target") != "CP02":
        add_error(errors, "E_MIGRATION_DIRECT", "migration", "store documentary direct mapping wrong")
    split = mappings.get("CP_PRODUCT_ITERATION_ARCHIVE", {})
    if split.get("canonical_targets") != ["CP11", "CP12"] or split.get("mapping") != "SPLIT_REQUIRED":
        add_error(errors, "E_MIGRATION_SPLIT", "migration", "product archive split wrong")
    if split.get("automatic_target_selection") != "forbidden":
        add_error(errors, "E_MIGRATION_SPLIT", "migration", "automatic target selection not forbidden")
    target_values = []
    for key in ["canonical_target", "canonical_targets"]:
        value = split.get(key)
        if isinstance(value, list):
            target_values.extend(value)
        elif isinstance(value, str):
            target_values.append(value)
    routing_targets = [
        value for value in split.get("routing_rule", {}).values() if isinstance(value, str)
    ]
    if "CP03" in target_values or "CP03" in routing_targets:
        add_error(errors, "E_LEGACY_CP03_WRONG", "migration", "legacy profile incorrectly maps to new CP03")
    old_bundles = migration.get("old_pilot_bundles", {})
    if old_bundles.get("in_place_migration_allowed") is not False or old_bundles.get("counts_as_20_profile_fixture_coverage") is not False:
        add_error(errors, "E_OLD_BUNDLE_MIGRATED", "migration", "old bundles migrated or used as coverage")
    old_candidates = migration.get("old_89_candidates", {})
    if old_candidates.get("mechanical_inheritance_from_3_profile_applicability_allowed") is not False:
        add_error(errors, "E_COMPONENT_SUPPLY_CLAIM", "migration", "old candidate applicability mechanically inherited")
    if migration.get("migration_digest") != object_digest(migration, {"migration_digest"}):
        add_error(errors, "E_MIGRATION_DIGEST", "migration", "migration digest mismatch")


def validate_coverage(coverage_doc: dict[str, Any], registry_doc: dict[str, Any], errors: list[dict[str, str]]) -> None:
    coverage = coverage_doc.get("content_product_profile_coverage_and_gap", {})
    policy = coverage.get("fixture_policy", {})
    if policy.get("may_enter_generation_prompt") is not False:
        add_error(errors, "E_FIXTURE_PROMPT", "coverage", "fixtures can enter prompt")
    if policy.get("may_supply_facts") is not False:
        add_error(errors, "E_FIXTURE_FACT", "coverage", "fixtures can supply facts")
    if policy.get("fake_fixture_allowed") is not False:
        add_error(errors, "E_FAKE_FIXTURE", "coverage", "fake fixture allowed")
    records = coverage.get("coverage_records", [])
    profile_ids = [p["content_product_type_id"] for p in registry_doc.get("content_product_profile_registry", {}).get("profiles", [])]
    record_ids = [record.get("content_product_type_id") for record in records]
    if record_ids != profile_ids:
        add_error(errors, "E_FIXTURE_COVERAGE", "coverage", "coverage ids mismatch")
    missing_count = 0
    for record in records:
        cp_id = str(record.get("content_product_type_id"))
        if record.get("fixture_coverage") == "missing_explicit":
            missing_count += 1
            if record.get("blocks_content_quality_validation") is not True:
                add_error(errors, "E_FIXTURE_GAP_DISHONEST", cp_id, "missing fixture does not block quality validation")
        elif record.get("fixture_coverage") == "complete" and not record.get("positive_refs"):
            add_error(errors, "E_FIXTURE_GAP_DISHONEST", cp_id, "complete coverage without positive refs")
        if record.get("fake_fixture_created") is True:
            add_error(errors, "E_FAKE_FIXTURE", cp_id, "fake fixture marked")
    summary = coverage.get("summary", {})
    if summary.get("missing_explicit_count") != missing_count:
        add_error(errors, "E_FIXTURE_COVERAGE", "coverage", "missing count summary mismatch")
    if coverage.get("coverage_digest") != object_digest(coverage, {"coverage_digest"}):
        add_error(errors, "E_COVERAGE_DIGEST", "coverage", "coverage digest mismatch")


def validate_result(result_doc: dict[str, Any], errors: list[dict[str, str]], root: Path) -> None:
    result = result_doc.get("content_product_profile_20_completion_result", {})
    if result.get("verdict") != "CONTENT_PRODUCT_PROFILE_20_COMPLETION_EXECUTED_PENDING_CLAUDE_GUARDIAN":
        add_error(errors, "E_RESULT_VERDICT", "result", "verdict mismatch")
    counts = result.get("counts", {})
    expected_counts = {
        "content_product_family_count": 5,
        "content_product_profile_count": 20,
        "planning_share_sum": 100,
        "component_supply_evaluated": False,
        "ORCH_eligible_profile_count": 0,
        "reviewed_reusable_component_count": 0,
        "canonical_composition_plan_count": 0,
        "audience_facing_content_count": 0,
        "title_count": 0,
        "spoken_script_count": 0,
    }
    for key, expected in expected_counts.items():
        if counts.get(key) != expected:
            add_error(errors, "E_RESULT_COUNT", "result", f"{key}={counts.get(key)} != {expected}")
    for flag_path in recursive_true_flags(result):
        add_error(errors, "E_READINESS_TRUE", "result", f"forbidden true flag {flag_path}")
    for content_path in recursive_audience_content(result):
        add_error(errors, "E_AUDIENCE_CONTENT", "result", f"audience content key materialized: {content_path}")
    digests = result.get("generated_file_digests", {})
    for rel_path, expected_digest in digests.items():
        path = root / rel_path
        if not path.exists() or sha256_file(path) != expected_digest:
            add_error(errors, "E_RECORDED_DIGEST", "result", f"digest mismatch: {rel_path}")
    if result.get("result_digest") != object_digest(result, {"result_digest"}):
        add_error(errors, "E_RESULT_DIGEST", "result", "result digest mismatch")


def validate_ledger(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    ledger = load_yaml(root / LEDGER_PATH)
    root_node = ledger.get("grc_3600_execution_plan_status", {})
    migration = root_node.get("route_migration_20")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_ROUTE20", "ledger", "route_migration_20 missing")
        return
    s1 = migration.get("S1", {})
    if s1.get("head") != BASELINE_HEAD or s1.get("status") != "DONE_GUARDIAN_PASS":
        add_error(errors, "E_LEDGER_S1", "ledger", "S1 ledger values wrong")
    s1_5 = migration.get("S1_5", {})
    expected = {
        "status": "EXECUTED_PENDING_CLAUDE_GUARDIAN",
        "content_product_family_count": 5,
        "content_product_profile_count": 20,
        "planning_share_sum": 100,
        "component_supply_evaluated": False,
        "ORCH_eligible_profile_count": 0,
        "audience_facing_content_count": 0,
    }
    for key, value in expected.items():
        if s1_5.get(key) != value:
            add_error(errors, "E_LEDGER_S1_5", "ledger", f"{key}={s1_5.get(key)}")
    if migration.get("S2", {}).get("status") != "BLOCKED_BY_S1_5_GUARDIAN":
        add_error(errors, "E_LEDGER_S2", "ledger", "S2 not blocked by S1.5 guardian")
    if migration.get("additive_only") is not True or migration.get("no_existing_step_status_changed") is not True:
        add_error(errors, "E_LEDGER_NON_ADDITIVE_DECLARATION", "ledger", "not declared additive")
    for key in migration.get("must_remain_false", []):
        if not isinstance(key, str):
            add_error(errors, "E_READINESS_TRUE", "ledger", "must_remain_false contains non-string")
    if any(flag for flag in recursive_true_flags(migration)):
        add_error(errors, "E_READINESS_TRUE", "ledger", f"forbidden true flags: {recursive_true_flags(migration)}")
    if migration.get("migration_digest") != object_digest(migration, {"migration_digest"}):
        add_error(errors, "E_LEDGER_DIGEST", "ledger", "migration digest mismatch")
    if enforce_git:
        baseline = load_baseline_yaml(root, LEDGER_PATH)
        if baseline is None:
            add_error(errors, "E_LEDGER_BASELINE", "ledger", "cannot load baseline ledger")
        else:
            current_without = copy.deepcopy(ledger)
            baseline_without = copy.deepcopy(baseline)
            current_without["grc_3600_execution_plan_status"].pop("route_migration_20", None)
            if current_without != baseline_without:
                add_error(errors, "E_LEDGER_NON_ADDITIVE", "ledger", "changes beyond route_migration_20")


def validate_no_forbidden_artifacts(root: Path, errors: list[dict[str, str]]) -> None:
    forbidden_names = []
    for path in (root / TASK_DIR).rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if "component_candidate_manifest" in name or "gkb_composition_candidate_bundles" in name:
            forbidden_names.append(path.relative_to(root).as_posix())
        if "fixture" in name and name != "content_product_profile_coverage_and_gap.v0.1.yaml":
            forbidden_names.append(path.relative_to(root).as_posix())
    if forbidden_names:
        add_error(errors, "E_NEW_COMPONENT_OR_BUNDLE", "files", f"forbidden artifacts: {forbidden_names}")


def validate_idempotence(root: Path, errors: list[dict[str, str]]) -> None:
    validator = load_validator(root)
    expected_artifacts = validator.build_artifacts(root)
    for rel_path, expected_text in expected_artifacts.items():
        path = root / rel_path
        if not path.exists():
            add_error(errors, "E_IDEMPOTENCE", "validator", f"missing {rel_path}")
        elif path.read_text(encoding="utf-8") != expected_text:
            add_error(errors, "E_IDEMPOTENCE", "validator", f"content mismatch {rel_path}")


def collect_errors(root: Path, *, enforce_git: bool = True, compare_expected: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    validate_preflight(root, errors, enforce_git)
    for path in [CONTRACT_PATH, PROFILES_PATH, MIGRATION_PATH, COVERAGE_PATH, RESULT_PATH, VALIDATOR_PATH, CHECKER_PATH]:
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE_MISSING", "files", f"missing {path}")
    if any(error["code"] == "E_REQUIRED_FILE_MISSING" for error in errors):
        return errors

    contract_doc = load_yaml(root / CONTRACT_PATH)
    profiles_doc = load_yaml(root / PROFILES_PATH)
    migration_doc = load_yaml(root / MIGRATION_PATH)
    coverage_doc = load_yaml(root / COVERAGE_PATH)
    result_doc = load_yaml(root / RESULT_PATH)

    validate_contract(contract_doc, errors)
    validate_profiles(profiles_doc, errors)
    validate_migration(migration_doc, errors)
    validate_coverage(coverage_doc, profiles_doc, errors)
    validate_result(result_doc, errors, root)
    validate_ledger(root, errors, enforce_git)
    validate_no_forbidden_artifacts(root, errors)
    if compare_expected:
        validate_idempotence(root, errors)
    return errors


def copy_for_selftest(source_root: Path, tmp_root: Path) -> None:
    paths = [
        CLEAN_120_PATH,
        SCALE_600_CONTRACT_PATH,
        LEDGER_PATH,
        CHECKER_PATH,
        *S1_PATHS.values(),
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


def profiles_mutator(mutator: Callable[[list[dict[str, Any]]], None]) -> Callable[[Path], None]:
    def apply(root: Path) -> None:
        mutate_yaml_file(
            root,
            PROFILES_PATH,
            lambda data: mutator(data["content_product_profile_registry"]["profiles"]),
        )

    return apply


def run_selftest_case(
    source_root: Path,
    name: str,
    expected_code: str,
    mutator: Callable[[Path], None],
) -> tuple[str, bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="profile20-selftest-") as tmp:
        tmp_root = Path(tmp)
        copy_for_selftest(source_root, tmp_root)
        mutator(tmp_root)
        codes = [error["code"] for error in collect_errors(tmp_root, enforce_git=False, compare_expected=False)]
        return name, expected_code in codes, codes


def selftest(root: Path) -> int:
    cases: list[tuple[str, str, Callable[[Path], None]]] = [
        ("missing_profile", "E_PROFILE_COUNT", profiles_mutator(lambda rows: rows.pop())),
        ("duplicate_cp_id", "E_DUPLICATE_CP_ID", profiles_mutator(lambda rows: rows[1].__setitem__("content_product_type_id", "CP01"))),
        (
            "family_members_wrong",
            "E_FAMILY_MEMBERS",
            lambda tmp: mutate_yaml_file(
                tmp,
                PROFILES_PATH,
                lambda data: data["content_product_profile_registry"]["families"]["F1_PEOPLE_AND_REAL_SCENE"]["products"].append("CP06"),
            ),
        ),
        (
            "share_sum_wrong",
            "E_SHARE_SUM",
            lambda tmp: mutate_yaml_file(
                tmp,
                PROFILES_PATH,
                lambda data: data["content_product_profile_registry"]["allocation_policy"].__setitem__("sum_percent", 99),
            ),
        ),
        (
            "planning_as_generation",
            "E_ALLOCATION_AS_GENERATION",
            lambda tmp: mutate_yaml_file(
                tmp,
                PROFILES_PATH,
                lambda data: data["content_product_profile_registry"]["allocation_policy"].__setitem__("generation_authority", True),
            ),
        ),
        (
            "missing_fact_slot",
            "E_PROFILE_INPUT_SLOT",
            profiles_mutator(lambda rows: rows[0]["input_requirements"].__setitem__("required_fact_slots", [])),
        ),
        (
            "missing_auth_slot",
            "E_PROFILE_INPUT_SLOT",
            profiles_mutator(lambda rows: rows[0]["input_requirements"].__setitem__("required_authorization_slots", [])),
        ),
        (
            "event_second_truth",
            "E_EVENT_MODE_SECOND_TRUTH",
            profiles_mutator(lambda rows: rows[0].__setitem__("forbidden_event_truth_modes", ["fake"])),
        ),
        (
            "missing_route_second_truth",
            "E_MISSING_ROUTE_SECOND_TRUTH",
            profiles_mutator(lambda rows: rows[0].__setitem__("missing_input_routes", [])),
        ),
        (
            "fixture_prompt",
            "E_FIXTURE_PROMPT",
            profiles_mutator(lambda rows: rows[0]["fixture_refs"].__setitem__("may_enter_generation_prompt", True)),
        ),
        (
            "fixture_as_fact",
            "E_FIXTURE_FACT",
            profiles_mutator(lambda rows: rows[0]["fixture_refs"].__setitem__("may_supply_facts", True)),
        ),
        (
            "fake_fixture",
            "E_FAKE_FIXTURE",
            lambda tmp: mutate_yaml_file(
                tmp,
                COVERAGE_PATH,
                lambda data: data["content_product_profile_coverage_and_gap"]["fixture_policy"].__setitem__("fake_fixture_allowed", True),
            ),
        ),
        (
            "cp14_spoken_required",
            "E_CP14_SPOKEN_CTA",
            profiles_mutator(lambda rows: rows[13]["required_component_roles"].append({"role": "spoken_line_intent", "min_count": 1, "max_count": 1})),
        ),
        (
            "cp04_no_multi_auth",
            "E_CP04_MULTI_AUTH",
            profiles_mutator(lambda rows: rows[3]["input_requirements"].__setitem__("required_authorization_slots", ["publication_scope_authorization"])),
        ),
        (
            "cp16_no_privacy",
            "E_CP16_PRIVACY",
            profiles_mutator(
                lambda rows: (
                    rows[15]["input_requirements"].__setitem__(
                        "required_authorization_slots", ["publication_scope_authorization"]
                    ),
                    rows[15].__setitem__("founder_hard_guards", [{"rule_id": "X", "text": "generic"}]),
                    rows[15]["style_constraints"].__setitem__("founder_style_terms", ["平等", "尊重"]),
                )
            ),
        ),
        (
            "cp18_no_location",
            "E_CP18_LOCATION",
            profiles_mutator(
                lambda rows: (
                    rows[17].__setitem__("founder_core_inputs", ["素材"]),
                    rows[17]["input_requirements"].__setitem__("required_fact_slots", ["generic_fact"]),
                    rows[17]["input_requirements"].__setitem__("required_source_slots", ["usable_source_materials"]),
                    rows[17]["style_constraints"].__setitem__("founder_style_terms", ["生活纪录"]),
                    rows[17]["continuity_policy"].__setitem__("model", "generic_chronicle"),
                    rows[17].__setitem__("target_account_roles", ["store_account"]),
                    rows[17].__setitem__("founder_hard_guards", [{"rule_id": "X", "text": "generic"}]),
                )
            ),
        ),
        (
            "cp19_non_low_frequency",
            "E_LOW_FREQUENCY",
            profiles_mutator(lambda rows: rows[18].__setitem__("cadence_policy", "standard_frequency")),
        ),
        (
            "cp20_no_evidence_review",
            "E_CP20_EVIDENCE_REVIEW",
            profiles_mutator(lambda rows: rows[19]["input_requirements"].__setitem__("required_fact_slots", ["public_commitment"])),
        ),
        (
            "legacy_maps_to_cp03",
            "E_LEGACY_CP03_WRONG",
            lambda tmp: mutate_yaml_file(
                tmp,
                MIGRATION_PATH,
                lambda data: data["legacy_profile_migration"]["mappings"]["CP_PRODUCT_ITERATION_ARCHIVE"].__setitem__("canonical_targets", ["CP03"]),
            ),
        ),
        (
            "coverage_gap_claimed_complete",
            "E_FIXTURE_GAP_DISHONEST",
            lambda tmp: mutate_yaml_file(
                tmp,
                COVERAGE_PATH,
                lambda data: data["content_product_profile_coverage_and_gap"]["coverage_records"][0].update(
                    {"fixture_coverage": "complete", "positive_refs": []}
                ),
            ),
        ),
        (
            "orch_eligible_true",
            "E_ORCH_ELIGIBLE",
            profiles_mutator(lambda rows: rows[0]["component_supply_state"].__setitem__("ORCH_profile_eligible", True)),
        ),
        (
            "new_component_or_bundle",
            "E_NEW_COMPONENT_OR_BUNDLE",
            lambda tmp: (tmp / TASK_DIR / "component_candidate_manifest.v0.2.jsonl").write_text("{}", encoding="utf-8"),
        ),
        (
            "s1_asset_modified",
            "E_S1_DIGEST_CHANGED",
            lambda tmp: (tmp / S1_PATHS["profiles_v0_1"]).write_text(
                (tmp / S1_PATHS["profiles_v0_1"]).read_text(encoding="utf-8") + "\n# mutation\n",
                encoding="utf-8",
            ),
        ),
        (
            "generated_body",
            "E_AUDIENCE_CONTENT",
            lambda tmp: mutate_yaml_file(
                tmp,
                RESULT_PATH,
                lambda data: data["content_product_profile_20_completion_result"].__setitem__("title", "generated title"),
            ),
        ),
        (
            "generation_600_allowed",
            "E_READINESS_TRUE",
            lambda tmp: mutate_yaml_file(
                tmp,
                RESULT_PATH,
                lambda data: data["content_product_profile_20_completion_result"]["readiness_flags"].__setitem__(
                    "generation_600_allowed", True
                ),
            ),
        ),
        (
            "readiness_true",
            "E_READINESS_TRUE",
            lambda tmp: mutate_yaml_file(
                tmp,
                RESULT_PATH,
                lambda data: data["content_product_profile_20_completion_result"]["readiness_flags"].__setitem__("production_ready", True),
            ),
        ),
        (
            "route_non_additive",
            "E_LEDGER_NON_ADDITIVE_DECLARATION",
            lambda tmp: mutate_yaml_file(
                tmp,
                LEDGER_PATH,
                lambda data: data["grc_3600_execution_plan_status"]["route_migration_20"].__setitem__("additive_only", False),
            ),
        ),
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
