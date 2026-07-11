#!/usr/bin/env python3
"""Fail-closed checker for the Controlled Composition V2 pilot proof."""

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
    print("check_gkb_controlled_composition_v2 refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "GKB-CONTROLLED-COMPOSITION-V2-PROFILE-SCHEMA-AND-PILOT-HANDOFF-001"
BASELINE_HEAD = "30a972a32749f4bb1048546ceedd39c652c7162a"
TASK_COMMIT = "538b464042656dec7df0e05acff554a8a4b4528f"
CLEAN_120_SHA256 = "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91"
SCALE_600_CONTRACT_SHA256 = (
    "966190c341b070d88fbc3a25540e9c8fddf69ad8f19b90fb29badbb1ffad52a9"
)
IMPLEMENTATION_KIND = "codex_native_controlled_composition_pilot_harness"

TASK_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
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
V1_RUNNER_PATH = Path("ci/runners/run_p7d_midbatch_320.py")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CHECKER_PATH = Path("ci/checkers/check_gkb_controlled_composition_v2.py")
HARNESS_PATH = TASK_DIR / "run_controlled_composition_v2_pilot.py"

CONTRACT_PATH = TASK_DIR / "controlled_composition_v2_contract.v0.1.yaml"
PROFILES_PATH = TASK_DIR / "content_product_profiles.v0.1.yaml"
SELECTION_PATH = TASK_DIR / "pilot_source_selection.v0.1.yaml"
COMPONENTS_PATH = TASK_DIR / "component_candidate_manifest.v0.1.jsonl"
BUNDLES_PATH = TASK_DIR / "gkb_composition_candidate_bundles.v0.1.jsonl"
HANDOFF_PATH = TASK_DIR / "gkb_orch_pilot_handoff.v0.1.yaml"
RESULT_PATH = TASK_DIR / "controlled_composition_v2_result.v0.1.yaml"

EXPECTED_NEW_FILES = {
    CONTRACT_PATH,
    PROFILES_PATH,
    SELECTION_PATH,
    COMPONENTS_PATH,
    BUNDLES_PATH,
    HANDOFF_PATH,
    RESULT_PATH,
    HARNESS_PATH,
    CHECKER_PATH,
    LEDGER_PATH,
}
EXPECTED_PROFILE_IDS = {
    "CP_ROLE_WORK_VLOG",
    "CP_STORE_MICRO_DOCUMENTARY",
    "CP_PRODUCT_ITERATION_ARCHIVE",
}
EXPECTED_EVENT_MODES = {
    "brand_supplied_real_event",
    "brand_fillable_prototype",
    "generic_creative_prototype",
    "collection_task_only",
}
EXPECTED_ROUTE_IDS = {
    "all_required_inputs_present",
    "optional_inputs_missing_only",
    "real_event_missing",
    "person_authorization_missing",
    "product_fact_or_claim_support_missing",
}
FORBIDDEN_TRUE_KEYS = {
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "Serving_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
    "generation_600_allowed",
    "generation_3600_allowed",
    "expand_600_allowed",
    "expand_3600_allowed",
    "runtime_ingest_ready",
    "runtime_ingest_allowed",
    "DIFY_direct_GKB_consumption_allowed",
}
AUDIENCE_BODY_KEYS = {
    "audience_facing_body",
    "title",
    "spoken_draft",
    "spoken_line_draft",
    "brand_story",
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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise TypeError(f"JSONL row is not an object: {path}:{line_number}")
        rows.append(row)
    return rows


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def get_path(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def load_harness(root: Path) -> Any:
    harness_path = root / HARNESS_PATH
    spec = importlib.util.spec_from_file_location("controlled_composition_v2_harness", harness_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load harness: {harness_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root: Path, args: list[str]) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def changed_paths(root: Path) -> set[Path]:
    diff_names = git(root, ["diff", "--name-only", BASELINE_HEAD, TASK_COMMIT]) or ""
    return {Path(line.strip()) for line in diff_names.splitlines() if line.strip()}


def load_commit_yaml(root: Path, commit: str, path: Path) -> dict[str, Any] | None:
    text = git(root, ["show", f"{commit}:{path.as_posix()}"])
    if text is None:
        return None
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return None
    return data


def load_commit_text(root: Path, commit: str, path: Path) -> str | None:
    return git(root, ["show", f"{commit}:{path.as_posix()}"])


def load_baseline_yaml(root: Path, path: Path) -> dict[str, Any] | None:
    text = git(root, ["show", f"{BASELINE_HEAD}:{path.as_posix()}"])
    if text is None:
        return None
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return None
    return data


def load_baseline_bytes(root: Path, path: Path) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{BASELINE_HEAD}:{path.as_posix()}"],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def record_digest(record: dict[str, Any]) -> str:
    return sha256_text(canonical_json(record))


def occurrence_count(container: str, exact_text: str) -> int:
    if not exact_text:
        return 0
    count = 0
    start = 0
    while True:
        index = container.find(exact_text, start)
        if index < 0:
            return count
        count += 1
        start = index + len(exact_text)


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


def recursive_audience_material(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in AUDIENCE_BODY_KEYS and child:
                hits.append(child_path)
            hits.extend(recursive_audience_material(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_audience_material(child, f"{path}[{index}]"))
    return hits


def probe_materialized_paths(root: Path) -> list[str]:
    hits: list[str] = []
    needles = ("probe_15", "single_cluster", "dual_voice")
    artifact_terms = ("assignment", "draft", "sample", "generation_record")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().lower()
        if any(needle in relative for needle in needles) and any(
            term in relative for term in artifact_terms
        ):
            hits.append(relative)
    return sorted(hits)


def top_level_route_ids(text: str) -> list[int]:
    ids: list[int] = []
    for line in text.splitlines():
        if line.startswith("  route_migration_") and line.endswith(":"):
            suffix = line.strip().removeprefix("route_migration_").removesuffix(":")
            if suffix.isdigit():
                ids.append(int(suffix))
    return ids


def extract_top_level_block(text: str, key: str) -> str | None:
    lines = text.splitlines(keepends=True)
    start: int | None = None
    for index, line in enumerate(lines):
        if line == f"  {key}:\n" or line == f"  {key}:":
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.startswith("  ") and not line.startswith("    ") and ":" in line:
            end = index
            break
    return "".join(lines[start:end])


def validate_route_envelope(
    root: Path,
    current_text: str,
    task_text: str,
    protected_route_id: int,
    errors: list[dict[str, str]],
) -> None:
    route_key = f"route_migration_{protected_route_id}"
    current_block = extract_top_level_block(current_text, route_key)
    task_block = extract_top_level_block(task_text, route_key)
    if current_block is None or task_block is None:
        add_error(errors, "E_LEDGER_FROZEN_PREFIX", "ledger", f"{route_key} block missing")
    elif current_block != task_block:
        add_error(errors, "E_LEDGER_FROZEN_PREFIX", "ledger", f"{route_key} block is not byte-identical")

    ids = top_level_route_ids(current_text)
    task_ids = top_level_route_ids(task_text)
    duplicates = sorted({route_id for route_id in ids if ids.count(route_id) > 1})
    if duplicates:
        add_error(errors, "E_LEDGER_DUPLICATE_ROUTE", "ledger", f"duplicate route ids: {duplicates}")
    inserted_historical = sorted(
        route_id
        for route_id in set(ids)
        if route_id <= protected_route_id and route_id not in set(task_ids)
    )
    if inserted_historical:
        add_error(
            errors,
            "E_LEDGER_HISTORICAL_ROUTE_INSERT",
            "ledger",
            f"inserted historical route ids: {inserted_historical}",
        )
    if protected_route_id not in ids:
        add_error(errors, "E_LEDGER_FROZEN_PREFIX", "ledger", f"{route_key} id missing")
    future_ids = sorted(route_id for route_id in ids if route_id > protected_route_id)
    if future_ids:
        expected = list(range(protected_route_id + 1, max(future_ids) + 1))
        if future_ids != expected:
            add_error(errors, "E_LEDGER_ROUTE_SEQUENCE", "ledger", f"future route ids {future_ids} != {expected}")


def validate_write_surface(root: Path, errors: list[dict[str, str]]) -> None:
    changed = changed_paths(root)
    unexpected = sorted(path.as_posix() for path in changed - EXPECTED_NEW_FILES)
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", "git", f"unexpected changed paths: {unexpected}")


def validate_preflight(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    if enforce_git:
        head = (git(root, ["rev-parse", "HEAD"]) or "").strip()
        if not head:
            add_error(errors, "E_HEAD", "git", "cannot resolve HEAD")
        if git(root, ["merge-base", "--is-ancestor", BASELINE_HEAD, TASK_COMMIT]) is None:
            add_error(errors, "E_BASELINE_HEAD", "git", "baseline is not the task commit parent line")
        if git(root, ["merge-base", "--is-ancestor", TASK_COMMIT, "HEAD"]) is None:
            add_error(errors, "E_TASK_COMMIT", "git", "task commit is not an ancestor of HEAD")
        validate_write_surface(root, errors)

    if sha256_file(root / CLEAN_120_PATH) != CLEAN_120_SHA256:
        add_error(errors, "E_CLEAN_DIGEST", "inputs", "Clean-120 digest mismatch")
    if sha256_file(root / SCALE_600_CONTRACT_PATH) != SCALE_600_CONTRACT_SHA256:
        add_error(errors, "E_SCALE_CONTRACT_DIGEST", "inputs", "600 contract digest mismatch")
    if not (root / V1_RUNNER_PATH).exists():
        add_error(errors, "E_V1_MISSING", "inputs", "V1 runner missing")
    if enforce_git:
        baseline_v1 = load_baseline_bytes(root, V1_RUNNER_PATH)
        if baseline_v1 is None or hashlib.sha256(baseline_v1).hexdigest() != sha256_file(root / V1_RUNNER_PATH):
            add_error(errors, "E_V1_MODIFIED", "inputs", "V1 runner differs from baseline")
    probe_hits = probe_materialized_paths(root)
    if probe_hits:
        add_error(errors, "E_PROBE_MATERIALIZED", "inputs", f"probe artifacts: {probe_hits}")


def validate_profiles(profiles_doc: dict[str, Any], root: Path, errors: list[dict[str, str]]) -> None:
    container = profiles_doc.get("content_product_profiles", {})
    profiles = container.get("profiles", [])
    if len(profiles) != 3:
        add_error(errors, "E_PROFILE_COUNT", "profiles", f"profile count {len(profiles)} != 3")
    profile_ids = {profile.get("content_product_type_id") for profile in profiles}
    if profile_ids != EXPECTED_PROFILE_IDS:
        add_error(errors, "E_PROFILE_IDS", "profiles", f"profile ids {sorted(profile_ids)}")
    for profile in profiles:
        profile_id = str(profile.get("content_product_type_id"))
        if "forbidden_event_truth_modes" in profile:
            add_error(errors, "E_PROFILE_SECOND_MODE_TRUTH", profile_id, "forbidden_event_truth_modes present")
        if "missing_input_routes" in profile or "allowed_degraded_outputs" in profile:
            add_error(errors, "E_PROFILE_DUPLICATE_ROUTE_TRUTH", profile_id, "duplicate missing route truth present")
        if profile.get("owner") != "GKB" or profile.get("runtime_plan_owner") != "ORCH":
            add_error(errors, "E_PROFILE_OWNER", profile_id, "owner/runtime owner mismatch")
        roles = profile.get("required_component_roles", [])
        role_names = [item.get("role") for item in roles if isinstance(item, dict)]
        if not roles or any(not isinstance(item, dict) for item in roles):
            add_error(errors, "E_PROFILE_REQUIRED_ROLE", profile_id, "required roles not parseable")
        for required in roles:
            if not {"role", "min_count", "max_count"} <= set(required):
                add_error(errors, "E_PROFILE_REQUIRED_ROLE", profile_id, "required role missing min/max")
        expected_min_roles = {
            "CP_ROLE_WORK_VLOG": {
                "scene",
                "observable_action",
                "professional_judgment",
                "capture_instruction",
            },
            "CP_STORE_MICRO_DOCUMENTARY": {
                "scene",
                "observable_action",
                "visual_beat",
                "capture_instruction",
            },
            "CP_PRODUCT_ITERATION_ARCHIVE": {
                "scene",
                "trigger",
                "professional_judgment",
                "capture_instruction",
            },
        }
        if profile_id in expected_min_roles and set(role_names) != expected_min_roles[profile_id]:
            add_error(errors, "E_PROFILE_REQUIRED_ROLE", profile_id, f"roles are {role_names}")
        reqs = profile.get("input_requirements", {})
        if not all(
            isinstance(reqs.get(key), list) and reqs.get(key)
            for key in [
                "required_source_slots",
                "required_fact_slots",
                "required_authorization_slots",
            ]
        ):
            add_error(errors, "E_PROFILE_INPUT_SLOTS", profile_id, "source/fact/authorization slots incomplete")
        policy = profile.get("event_truth_policy", {})
        if set(policy.get("allowed_event_truth_modes", [])) != EXPECTED_EVENT_MODES or policy.get("default_deny_unlisted") is not True:
            add_error(errors, "E_PROFILE_EVENT_POLICY", profile_id, "event truth policy mismatch")
        routes = profile.get("input_sufficiency_routes", [])
        route_ids = [route.get("route_id") for route in routes if isinstance(route, dict)]
        if set(route_ids) != EXPECTED_ROUTE_IDS or len(route_ids) != len(set(route_ids)):
            add_error(errors, "E_PROFILE_ROUTE_TRUTH", profile_id, f"route ids {route_ids}")
        fixture_refs = profile.get("fixture_refs", {})
        if fixture_refs.get("may_enter_generation_prompt") is not False or fixture_refs.get("may_supply_facts") is not False:
            add_error(errors, "E_FIXTURE_REF", profile_id, "fixture refs may enter generation or supply facts")
        for fixture_key in ["positive", "negative"]:
            for fixture in fixture_refs.get(fixture_key, []) or []:
                if not (root / str(fixture)).exists():
                    add_error(errors, "E_FIXTURE_REF", profile_id, f"fixture missing: {fixture}")
        if profile.get("profile_digest") != object_digest(profile, {"profile_digest"}):
            add_error(errors, "E_PROFILE_DIGEST", profile_id, "profile digest mismatch")


def validate_selection(
    selection_doc: dict[str, Any],
    clean_records: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    selection = selection_doc.get("pilot_source_selection", {})
    selected = selection.get("selected_sources", [])
    if len(selected) != 15 or len({item.get("asset_id") for item in selected}) != 15:
        add_error(errors, "E_SELECTION_COUNT", "selection", "selected source count/uniqueness mismatch")
    counts = Counter(item.get("p0_group") for item in selected)
    if dict(sorted(counts.items())) != {f"P0_0{i}": 3 for i in range(1, 6)}:
        add_error(errors, "E_SELECTION_P0_COUNTS", "selection", f"group counts {dict(counts)}")
    by_id = {record["asset_id"]: record for record in clean_records}
    groups: dict[str, list[str]] = {}
    for record in clean_records:
        groups.setdefault(str(record["p0_group"]), []).append(str(record["asset_id"]))
    expected_ids: list[str] = []
    for p0_group in [f"P0_0{i}" for i in range(1, 6)]:
        expected_ids.extend(
            sorted(
                groups[p0_group],
                key=lambda asset_id: sha256_text(f"{CLEAN_120_SHA256}:{asset_id}"),
            )[:3]
        )
    actual_ids = [item.get("asset_id") for item in selected]
    if actual_ids != expected_ids:
        add_error(errors, "E_SELECTION_ALGORITHM", "selection", f"ids {actual_ids} != {expected_ids}")
    for item in selected:
        asset_id = str(item.get("asset_id"))
        if asset_id not in by_id:
            add_error(errors, "E_SELECTION_SOURCE", "selection", f"missing source {asset_id}")
            continue
        expected_hash = sha256_text(f"{CLEAN_120_SHA256}:{asset_id}")
        if item.get("selection_hash") != expected_hash:
            add_error(errors, "E_SELECTION_ALGORITHM", asset_id, "selection hash mismatch")
        if item.get("source_record_digest") != record_digest(by_id[asset_id]):
            add_error(errors, "E_SELECTION_SOURCE_DIGEST", asset_id, "source record digest mismatch")
    if selection.get("selection_digest") != object_digest(selection, {"selection_digest"}):
        add_error(errors, "E_SELECTION_DIGEST", "selection", "selection digest mismatch")


def validate_components(
    components: list[dict[str, Any]],
    selected_doc: dict[str, Any],
    clean_records: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    selected_ids = {
        item.get("asset_id")
        for item in selected_doc.get("pilot_source_selection", {}).get("selected_sources", [])
    }
    by_id = {record["asset_id"]: record for record in clean_records}
    if len(components) > 90:
        add_error(errors, "E_COMPONENT_COUNT", "components", f"count {len(components)} > 90")
    component_ids = [component.get("component_id") for component in components]
    if len(component_ids) != len(set(component_ids)):
        add_error(errors, "E_COMPONENT_ID", "components", "duplicate component id")
    per_parent = Counter(component["parent_refs"][0]["parent_asset_id"] for component in components if component.get("parent_refs"))
    if any(count > 6 for count in per_parent.values()):
        add_error(errors, "E_COMPONENT_COUNT", "components", f"parent counts {dict(per_parent)}")

    for component in components:
        component_id = str(component.get("component_id"))
        role = component.get("component_role")
        if not isinstance(role, str):
            add_error(errors, "E_COMPONENT_ROLE_SHAPE", component_id, "component role is not a single string")
        if component.get("lifecycle") != "extracted_candidate":
            add_error(errors, "E_COMPONENT_LIFECYCLE", component_id, "component not extracted_candidate")
        if "primary_content_product_type_id" in component:
            add_error(errors, "E_COMPONENT_PRIMARY_CP", component_id, "primary content product field present")
        applicable = component.get("applicable_content_product_type_ids")
        if not isinstance(applicable, list) or not applicable:
            add_error(errors, "E_COMPONENT_APPLICABLE_CP", component_id, "applicable CP list empty")
        if component.get("component_digest") != object_digest(component, {"component_digest"}):
            add_error(errors, "E_COMPONENT_DIGEST", component_id, "component digest mismatch")
        if any(value is True for value in (component.get("truth_boundary") or {}).values()):
            add_error(errors, "E_TRUTH_BOUNDARY", component_id, "truth boundary contains true")
        if component.get("surface_reuse_policy") == "reviewed_reusable":
            add_error(errors, "E_COMPONENT_LIFECYCLE", component_id, "candidate promoted to reviewed reusable")
        if role == "professional_judgment":
            binding = component.get("professional_judgment_binding", {})
            if not all(binding.get(key) for key in ["applicable_role_authority", "required_fact_slots", "claim_boundary"]):
                add_error(errors, "E_PROFESSIONAL_JUDGMENT_BINDING", component_id, "judgment binding incomplete")
        if isinstance(role, str) and role in {"opening", "closing", "CTA", "spoken_line_intent"}:
            content = component.get("payload", {}).get("content")
            if isinstance(content, str) and len(content) >= 15:
                add_error(errors, "E_TEMPLATE_COMPONENT", component_id, "template-like direct sentence stored")

        parent_refs = component.get("parent_refs", [])
        if len(parent_refs) != 1:
            add_error(errors, "E_COMPONENT_PARENT", component_id, "expected one parent ref")
            continue
        parent = parent_refs[0]
        parent_id = str(parent.get("parent_asset_id"))
        if parent_id not in selected_ids or parent_id not in by_id:
            add_error(errors, "E_COMPONENT_PARENT", component_id, f"invalid parent {parent_id}")
            continue
        if parent.get("parent_digest") != record_digest(by_id[parent_id]):
            add_error(errors, "E_COMPONENT_PARENT_DIGEST", component_id, "parent digest mismatch")
        field_value = get_path(by_id[parent_id], str(parent.get("parent_field_path")))
        if field_value is None:
            add_error(errors, "E_DERIVATION_SPAN", component_id, "parent field path missing")
            continue
        field_text = str(field_value)
        for span in parent.get("derivation_spans", []):
            exact_text = str(span.get("exact_text", ""))
            if exact_text not in field_text:
                add_error(errors, "E_DERIVATION_SPAN", component_id, "exact text not found in parent field")
            elif occurrence_count(field_text, exact_text) <= int(span.get("occurrence_index", -1)):
                add_error(errors, "E_DERIVATION_SPAN", component_id, "occurrence index not found")
            if span.get("span_digest") != sha256_text(exact_text):
                add_error(errors, "E_DERIVATION_SPAN", component_id, "span digest mismatch")


def validate_bundles(
    bundles: list[dict[str, Any]],
    profiles_doc: dict[str, Any],
    components: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    profiles = {
        profile["content_product_type_id"]: profile
        for profile in profiles_doc.get("content_product_profiles", {}).get("profiles", [])
    }
    components_by_id = {component["component_id"]: component for component in components}
    if len(bundles) != 9:
        add_error(errors, "E_BUNDLE_COUNT", "bundles", f"bundle count {len(bundles)} != 9")
    counts = Counter(bundle.get("primary_content_product_type_id") for bundle in bundles)
    if any(counts.get(profile_id, 0) != 3 for profile_id in EXPECTED_PROFILE_IDS):
        add_error(errors, "E_BUNDLE_COUNT", "bundles", f"per CP counts {dict(counts)}")

    for bundle in bundles:
        bundle_id = str(bundle.get("bundle_id"))
        primary = bundle.get("primary_content_product_type_id")
        if not isinstance(primary, str) or "primary_content_product_type_ids" in bundle:
            add_error(errors, "E_BUNDLE_PRIMARY_SHAPE", bundle_id, "bundle primary CP is not singular")
        if primary not in profiles:
            add_error(errors, "E_BUNDLE_PRIMARY_SHAPE", bundle_id, f"unknown primary {primary}")
            continue
        profile = profiles[primary]
        ref = bundle.get("content_product_profile_ref", {})
        if ref.get("id") != primary or ref.get("digest") != profile.get("profile_digest"):
            add_error(errors, "E_BUNDLE_PROFILE_REF", bundle_id, "profile ref mismatch")
        selected_refs = bundle.get("selected_candidate_refs", [])
        selected_roles: set[str] = set()
        for ref_item in selected_refs:
            component_id = ref_item.get("component_id")
            component = components_by_id.get(component_id)
            if component is None:
                add_error(errors, "E_BUNDLE_COMPONENT_REF", bundle_id, f"missing component {component_id}")
                continue
            selected_roles.add(str(component.get("component_role")))
            if primary not in component.get("applicable_content_product_type_ids", []):
                add_error(errors, "E_BUNDLE_COMPONENT_PRODUCT_MISMATCH", bundle_id, f"{component_id} not applicable")
        required_roles = {item["role"] for item in profile.get("required_component_roles", [])}
        if not required_roles <= selected_roles:
            add_error(errors, "E_BUNDLE_REQUIRED_ROLE", bundle_id, f"missing roles {sorted(required_roles - selected_roles)}")
        expected_digests = [
            components_by_id[ref_item["component_id"]]["component_digest"]
            for ref_item in selected_refs
            if ref_item.get("component_id") in components_by_id
        ]
        if bundle.get("selected_candidate_digests") != expected_digests:
            add_error(errors, "E_BUNDLE_COMPONENT_DIGEST", bundle_id, "component digest list mismatch")
        if bundle.get("event_truth_mode") != "collection_task_only":
            add_error(errors, "E_EVENT_TRUTH_MODE", bundle_id, "bundle not collection_task_only")
        if bundle.get("brand_supplied_source_slots") or bundle.get("authorization_refs"):
            add_error(errors, "E_MISSING_INPUT_ROUTE", bundle_id, "source/auth slots unexpectedly supplied")
        brand_fact_slots = bundle.get("brand_supplied_fact_slots") or []
        if brand_fact_slots:
            add_error(errors, "E_BRAND_FACT_FROM_CONTENT_REFERENCE", bundle_id, "brand facts supplied in no-input task")
        if any("content_reference" in str(slot) for slot in brand_fact_slots):
            add_error(errors, "E_BRAND_FACT_FROM_CONTENT_REFERENCE", bundle_id, "content reference used as fact")
        if not bundle.get("missing_required_slots"):
            add_error(errors, "E_MISSING_INPUT_ROUTE", bundle_id, "missing required slots empty")
        route = bundle.get("sufficiency_route_result", {})
        if route.get("route_id") != "real_event_missing":
            add_error(errors, "E_MISSING_INPUT_ROUTE", bundle_id, "wrong sufficiency route")
        if route.get("audience_facing_body_allowed") is not False:
            add_error(errors, "E_AUDIENCE_BODY_MATERIALIZED", bundle_id, "audience body allowed")
        if route.get("first_person_experience_allowed") is not False:
            add_error(errors, "E_FIRST_PERSON_ALLOWED", bundle_id, "first-person experience allowed")
        if route.get("product_claim_allowed") is not False:
            add_error(errors, "E_CLAIM_SUPPORT", bundle_id, "product claim allowed")
        if bundle.get("audience_facing_body_allowed") is not False or bundle.get("audience_facing_body_materialized") is not False:
            add_error(errors, "E_AUDIENCE_BODY_MATERIALIZED", bundle_id, "audience body materialized")
        if recursive_audience_material(bundle):
            add_error(errors, "E_AUDIENCE_BODY_MATERIALIZED", bundle_id, "audience/title/spoken material present")
        if bundle.get("canonical_composition_plan") is not False:
            add_error(errors, "E_BUNDLE_CANONICAL_PLAN", bundle_id, "bundle marked canonical CompositionPlan")
        if bundle.get("runtime_owner") != "ORCH":
            add_error(errors, "E_RUNTIME_OWNER", bundle_id, "runtime owner is not ORCH")
        if bundle.get("runtime_ingest_allowed") is not False:
            add_error(errors, "E_RUNTIME_OWNER", bundle_id, "runtime ingest allowed")
        if bundle.get("forbidden_combination_hits"):
            add_error(errors, "E_FORBIDDEN_COMBINATION", bundle_id, "forbidden combination hit")
        if bundle.get("bundle_digest") != object_digest(bundle, {"bundle_digest"}):
            add_error(errors, "E_BUNDLE_DIGEST", bundle_id, "bundle digest mismatch")


def validate_handoff(handoff_doc: dict[str, Any], root: Path, errors: list[dict[str, str]]) -> None:
    handoff = handoff_doc.get("gkb_orch_pilot_handoff", {})
    if handoff.get("reviewed_reusable_component_count") != 0:
        add_error(errors, "E_HANDOFF_REVIEWED_COUNT", "handoff", "reviewed reusable count nonzero")
    if handoff.get("runtime_ingest_ready") is not False:
        add_error(errors, "E_HANDOFF_RUNTIME_INGEST", "handoff", "runtime ingest ready true")
    if handoff.get("canonical_composition_plan_count") != 0:
        add_error(errors, "E_BUNDLE_CANONICAL_PLAN", "handoff", "canonical plan count nonzero")
    if handoff.get("DIFY_direct_GKB_consumption_allowed") is not False:
        add_error(errors, "E_DIFY_DIRECT", "handoff", "DIFY direct GKB consumption allowed")
    orch = handoff.get("ORCH_behavior", {})
    if orch.get("may_mutate_GKB_assets") is not False or orch.get("owns_canonical_composition_plan") is not True:
        add_error(errors, "E_HANDOFF_OWNER", "handoff", "ORCH behavior mismatch")
    gkb = handoff.get("GKB_behavior", {})
    if gkb.get("may_create_runtime_composition_plan") is not False:
        add_error(errors, "E_BUNDLE_CANONICAL_PLAN", "handoff", "GKB may create runtime plan")
    snapshots = set(handoff.get("snapshot_digests", []))
    for path in [CONTRACT_PATH, PROFILES_PATH, COMPONENTS_PATH, BUNDLES_PATH]:
        actual = sha256_file(root / path)
        if actual not in snapshots:
            add_error(errors, "E_HANDOFF_DIGEST", "handoff", f"snapshot missing {path}")
    if handoff.get("handoff_digest") != object_digest(handoff, {"handoff_digest"}):
        add_error(errors, "E_HANDOFF_DIGEST", "handoff", "handoff digest mismatch")


def validate_result(result_doc: dict[str, Any], root: Path, errors: list[dict[str, str]]) -> None:
    result = result_doc.get("controlled_composition_v2_result", {})
    if result.get("verdict") != "CONTROLLED_COMPOSITION_V2_MINIMUM_COMPOSABILITY_PROOF_PASS":
        add_error(errors, "E_RESULT_VERDICT", "result", "verdict mismatch")
    if result.get("implementation_kind") != IMPLEMENTATION_KIND:
        add_error(errors, "E_IMPLEMENTATION_KIND", "result", "implementation kind mismatch")
    counts = result.get("counts", {})
    expected_counts = {
        "profile_count": 3,
        "selected_source_count": 15,
        "candidate_bundle_count": 9,
        "reviewed_reusable_component_count": 0,
        "canonical_composition_plan_count": 0,
        "audience_facing_body_count": 0,
        "title_count": 0,
        "spoken_draft_count": 0,
    }
    for key, expected in expected_counts.items():
        if counts.get(key) != expected:
            add_error(errors, "E_RESULT_COUNT", "result", f"{key}={counts.get(key)} != {expected}")
    auth = result.get("generation_authorization", {})
    if auth.get("generation_600_allowed") is not False or auth.get("generation_3600_allowed") is not False:
        add_error(errors, "E_GENERATION_SCALE_ALLOWED", "result", "scale generation allowed")
    for flag_path in recursive_true_flags(result):
        if flag_path.endswith("runtime_ingest_allowed"):
            continue
        add_error(errors, "E_READINESS_TRUE", "result", f"forbidden true flag {flag_path}")
    for rel_path, expected_digest in (result.get("generated_file_digests") or {}).items():
        path = root / rel_path
        if Path(rel_path) == CHECKER_PATH:
            historical_checker = git(root, ["show", f"{TASK_COMMIT}:{CHECKER_PATH.as_posix()}"])
            if historical_checker is None or sha256_text(historical_checker) != expected_digest:
                add_error(errors, "E_RECORDED_DIGEST_MISMATCH", "result", f"historical checker digest mismatch {rel_path}")
        elif not path.exists():
            add_error(errors, "E_RECORDED_DIGEST_MISMATCH", "result", f"missing digest file {rel_path}")
        elif sha256_file(path) != expected_digest:
            add_error(errors, "E_RECORDED_DIGEST_MISMATCH", "result", f"digest mismatch {rel_path}")
    if result.get("result_digest") != object_digest(result, {"result_digest"}):
        add_error(errors, "E_RESULT_DIGEST", "result", "result digest mismatch")


def validate_ledger(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    ledger = load_yaml(root / LEDGER_PATH)
    root_node = ledger.get("grc_3600_execution_plan_status", {})
    migration = root_node.get("route_migration_19")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_MIGRATION_19", "ledger", "route_migration_19 missing")
        return
    if migration.get("no_existing_step_status_changed") is not True or migration.get("additive_only") is not True:
        add_error(errors, "E_LEDGER_NON_ADDITIVE_DECLARATION", "ledger", "route migration not declared additive")
    progress = migration.get("controlled_v2_progress", {})
    expected = {
        "status": "EXECUTED_PENDING_GUARDIAN",
        "profile_count": 3,
        "selected_source_count": 15,
        "candidate_bundle_count": 9,
        "reviewed_reusable_component_count": 0,
        "canonical_composition_plan_count": 0,
        "audience_facing_body_count": 0,
    }
    for key, value in expected.items():
        if progress.get(key) != value:
            add_error(errors, "E_LEDGER_COUNT", "ledger", f"{key}={progress.get(key)} != {value}")
    scale = migration.get("scale_600_contract", {})
    if scale.get("generation_600_allowed") is not False:
        add_error(errors, "E_GENERATION_SCALE_ALLOWED", "ledger", "generation_600_allowed true")
    if migration.get("downstream_and_readiness", {}).get("all_false") is not True:
        add_error(errors, "E_READINESS_TRUE", "ledger", "downstream/readiness not all false")

    if enforce_git:
        task_ledger = load_commit_yaml(root, TASK_COMMIT, LEDGER_PATH)
        task_text = load_commit_text(root, TASK_COMMIT, LEDGER_PATH)
        current_text = (root / LEDGER_PATH).read_text(encoding="utf-8")
        if task_ledger is None or task_text is None:
            add_error(errors, "E_LEDGER_BASELINE", "ledger", "cannot load task ledger")
        else:
            task_migration = (
                task_ledger.get("grc_3600_execution_plan_status", {}).get("route_migration_19")
            )
            if migration != task_migration:
                add_error(errors, "E_LEDGER_FROZEN_PREFIX", "ledger", "route_migration_19 content drift")
            validate_route_envelope(root, current_text, task_text, 19, errors)


def validate_idempotence(root: Path, errors: list[dict[str, str]]) -> None:
    harness = load_harness(root)
    expected_artifacts = harness.build_artifacts(root)
    for rel_path, expected_text in expected_artifacts.items():
        if rel_path == RESULT_PATH:
            continue
        path = root / rel_path
        if not path.exists():
            add_error(errors, "E_IDEMPOTENCE_MISMATCH", "harness", f"missing {rel_path}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected_text:
            add_error(errors, "E_IDEMPOTENCE_MISMATCH", "harness", f"content mismatch {rel_path}")


def collect_errors(
    root: Path,
    *,
    enforce_git: bool = True,
    compare_expected: bool = True,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    validate_preflight(root, errors, enforce_git)

    for path in [
        CONTRACT_PATH,
        PROFILES_PATH,
        SELECTION_PATH,
        COMPONENTS_PATH,
        BUNDLES_PATH,
        HANDOFF_PATH,
        RESULT_PATH,
        HARNESS_PATH,
        CHECKER_PATH,
    ]:
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE_MISSING", "files", f"missing {path}")
    if any(error["code"] == "E_REQUIRED_FILE_MISSING" for error in errors):
        return errors

    clean_records = load_jsonl(root / CLEAN_120_PATH)
    profiles_doc = load_yaml(root / PROFILES_PATH)
    selection_doc = load_yaml(root / SELECTION_PATH)
    components = load_jsonl(root / COMPONENTS_PATH)
    bundles = load_jsonl(root / BUNDLES_PATH)
    handoff_doc = load_yaml(root / HANDOFF_PATH)
    result_doc = load_yaml(root / RESULT_PATH)
    contract_doc = load_yaml(root / CONTRACT_PATH)

    if contract_doc.get("controlled_composition_v2_contract", {}).get("implementation_kind") != IMPLEMENTATION_KIND:
        add_error(errors, "E_IMPLEMENTATION_KIND", "contract", "implementation kind mismatch")
    if recursive_true_flags(contract_doc):
        add_error(errors, "E_READINESS_TRUE", "contract", f"forbidden true flags {recursive_true_flags(contract_doc)}")

    validate_profiles(profiles_doc, root, errors)
    validate_selection(selection_doc, clean_records, errors)
    validate_components(components, selection_doc, clean_records, errors)
    validate_bundles(bundles, profiles_doc, components, errors)
    validate_handoff(handoff_doc, root, errors)
    validate_result(result_doc, root, errors)
    validate_ledger(root, errors, enforce_git)
    if compare_expected:
        validate_idempotence(root, errors)
    return errors


def copy_for_selftest(source_root: Path, tmp_root: Path) -> None:
    paths = [
        CLEAN_120_PATH,
        SCALE_600_CONTRACT_PATH,
        V1_RUNNER_PATH,
        LEDGER_PATH,
        CHECKER_PATH,
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


def run_selftest_case(
    source_root: Path,
    name: str,
    expected_code: str,
    mutator: Callable[[Path], None],
) -> tuple[str, bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="ccv2-selftest-") as tmp:
        tmp_root = Path(tmp)
        copy_for_selftest(source_root, tmp_root)
        mutator(tmp_root)
        codes = [error["code"] for error in collect_errors(tmp_root, enforce_git=False, compare_expected=False)]
        return name, expected_code in codes, codes


def selftest(root: Path) -> int:
    cases: list[tuple[str, str, Callable[[Path], None]]] = [
        (
            "profile_missing_required_role",
            "E_PROFILE_REQUIRED_ROLE",
            lambda tmp: mutate_yaml_file(
                tmp,
                PROFILES_PATH,
                lambda data: data["content_product_profiles"]["profiles"][0]["required_component_roles"].pop(),
            ),
        ),
        (
            "profile_forbidden_second_truth",
            "E_PROFILE_SECOND_MODE_TRUTH",
            lambda tmp: mutate_yaml_file(
                tmp,
                PROFILES_PATH,
                lambda data: data["content_product_profiles"]["profiles"][0].__setitem__(
                    "forbidden_event_truth_modes", ["made_up"]
                ),
            ),
        ),
        (
            "profile_duplicate_missing_route_truth",
            "E_PROFILE_DUPLICATE_ROUTE_TRUTH",
            lambda tmp: mutate_yaml_file(
                tmp,
                PROFILES_PATH,
                lambda data: data["content_product_profiles"]["profiles"][0].__setitem__(
                    "missing_input_routes", []
                ),
            ),
        ),
        (
            "fixture_missing_or_generation",
            "E_FIXTURE_REF",
            lambda tmp: mutate_yaml_file(
                tmp,
                PROFILES_PATH,
                lambda data: data["content_product_profiles"]["profiles"][0]["fixture_refs"].update(
                    {
                        "positive": ["ci/fixtures/does_not_exist.yaml"],
                        "may_enter_generation_prompt": True,
                    }
                ),
            ),
        ),
        (
            "component_empty_applicable_cp",
            "E_COMPONENT_APPLICABLE_CP",
            lambda tmp: mutate_jsonl_file(
                tmp,
                COMPONENTS_PATH,
                lambda rows: rows[0].__setitem__("applicable_content_product_type_ids", []),
            ),
        ),
        (
            "component_primary_cp",
            "E_COMPONENT_PRIMARY_CP",
            lambda tmp: mutate_jsonl_file(
                tmp,
                COMPONENTS_PATH,
                lambda rows: rows[0].__setitem__("primary_content_product_type_id", "CP_ROLE_WORK_VLOG"),
            ),
        ),
        (
            "component_multiple_roles",
            "E_COMPONENT_ROLE_SHAPE",
            lambda tmp: mutate_jsonl_file(
                tmp,
                COMPONENTS_PATH,
                lambda rows: rows[0].__setitem__("component_role", ["scene", "trigger"]),
            ),
        ),
        (
            "parent_digest_forged",
            "E_COMPONENT_PARENT_DIGEST",
            lambda tmp: mutate_jsonl_file(
                tmp,
                COMPONENTS_PATH,
                lambda rows: rows[0]["parent_refs"][0].__setitem__("parent_digest", "0" * 64),
            ),
        ),
        (
            "derivation_span_not_hit",
            "E_DERIVATION_SPAN",
            lambda tmp: mutate_jsonl_file(
                tmp,
                COMPONENTS_PATH,
                lambda rows: rows[0]["parent_refs"][0]["derivation_spans"][0].__setitem__(
                    "exact_text", "not present in parent field"
                ),
            ),
        ),
        (
            "derivation_span_as_fact",
            "E_TRUTH_BOUNDARY",
            lambda tmp: mutate_jsonl_file(
                tmp,
                COMPONENTS_PATH,
                lambda rows: rows[0]["truth_boundary"].__setitem__("real_event_evidence", True),
            ),
        ),
        (
            "candidate_promoted",
            "E_COMPONENT_LIFECYCLE",
            lambda tmp: mutate_jsonl_file(
                tmp,
                COMPONENTS_PATH,
                lambda rows: rows[0].__setitem__("lifecycle", "reviewed_reusable"),
            ),
        ),
        (
            "bundle_multiple_primary",
            "E_BUNDLE_PRIMARY_SHAPE",
            lambda tmp: mutate_jsonl_file(
                tmp,
                BUNDLES_PATH,
                lambda rows: rows[0].__setitem__(
                    "primary_content_product_type_ids",
                    ["CP_ROLE_WORK_VLOG", "CP_STORE_MICRO_DOCUMENTARY"],
                ),
            ),
        ),
        (
            "component_not_applicable_to_bundle",
            "E_BUNDLE_COMPONENT_PRODUCT_MISMATCH",
            lambda tmp: mutate_jsonl_file(
                tmp,
                COMPONENTS_PATH,
                lambda rows: rows[0].__setitem__("applicable_content_product_type_ids", ["CP_PRODUCT_ITERATION_ARCHIVE"]),
            ),
        ),
        (
            "required_component_missing_but_pass",
            "E_BUNDLE_REQUIRED_ROLE",
            lambda tmp: mutate_jsonl_file(
                tmp,
                BUNDLES_PATH,
                lambda rows: rows[0].__setitem__("selected_candidate_refs", rows[0]["selected_candidate_refs"][:1]),
            ),
        ),
        (
            "missing_event_generates_body",
            "E_AUDIENCE_BODY_MATERIALIZED",
            lambda tmp: mutate_jsonl_file(
                tmp,
                BUNDLES_PATH,
                lambda rows: rows[0].update(
                    {
                        "audience_facing_body_allowed": True,
                        "audience_facing_body": "audience body should not exist",
                    }
                ),
            ),
        ),
        (
            "missing_auth_allows_first_person",
            "E_FIRST_PERSON_ALLOWED",
            lambda tmp: mutate_jsonl_file(
                tmp,
                BUNDLES_PATH,
                lambda rows: rows[0]["sufficiency_route_result"].__setitem__(
                    "first_person_experience_allowed", True
                ),
            ),
        ),
        (
            "prototype_as_real_event",
            "E_EVENT_TRUTH_MODE",
            lambda tmp: mutate_jsonl_file(
                tmp,
                BUNDLES_PATH,
                lambda rows: rows[0].__setitem__("event_truth_mode", "brand_supplied_real_event"),
            ),
        ),
        (
            "content_reference_as_fact",
            "E_BRAND_FACT_FROM_CONTENT_REFERENCE",
            lambda tmp: mutate_jsonl_file(
                tmp,
                BUNDLES_PATH,
                lambda rows: rows[0].__setitem__("brand_supplied_fact_slots", ["content_reference:body_text"]),
            ),
        ),
        (
            "bundle_canonical_plan",
            "E_BUNDLE_CANONICAL_PLAN",
            lambda tmp: mutate_jsonl_file(
                tmp,
                BUNDLES_PATH,
                lambda rows: rows[0].__setitem__("canonical_composition_plan", True),
            ),
        ),
        (
            "gkb_runtime_owner",
            "E_RUNTIME_OWNER",
            lambda tmp: mutate_jsonl_file(
                tmp,
                BUNDLES_PATH,
                lambda rows: rows[0].__setitem__("runtime_owner", "GKB"),
            ),
        ),
        (
            "handoff_runtime_ingest_ready",
            "E_HANDOFF_RUNTIME_INGEST",
            lambda tmp: mutate_yaml_file(
                tmp,
                HANDOFF_PATH,
                lambda data: data["gkb_orch_pilot_handoff"].__setitem__("runtime_ingest_ready", True),
            ),
        ),
        (
            "dify_direct_gkb",
            "E_DIFY_DIRECT",
            lambda tmp: mutate_yaml_file(
                tmp,
                HANDOFF_PATH,
                lambda data: data["gkb_orch_pilot_handoff"].__setitem__(
                    "DIFY_direct_GKB_consumption_allowed", True
                ),
            ),
        ),
        (
            "silent_fallback_to_v1",
            "E_IMPLEMENTATION_KIND",
            lambda tmp: mutate_yaml_file(
                tmp,
                RESULT_PATH,
                lambda data: data["controlled_composition_v2_result"].__setitem__(
                    "implementation_kind", "legacy_v1_fallback"
                ),
            ),
        ),
        (
            "probe_materialized",
            "E_PROBE_MATERIALIZED",
            lambda tmp: (
                (tmp / "07_microbatch_runs/probe_15_assignment.json").parent.mkdir(
                    parents=True, exist_ok=True
                ),
                (tmp / "07_microbatch_runs/probe_15_assignment.json").write_text("{}", encoding="utf-8"),
            ),
        ),
        (
            "generation_600_allowed",
            "E_GENERATION_SCALE_ALLOWED",
            lambda tmp: mutate_yaml_file(
                tmp,
                RESULT_PATH,
                lambda data: data["controlled_composition_v2_result"]["generation_authorization"].__setitem__(
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
                lambda data: data["controlled_composition_v2_result"]["readiness_flags"].__setitem__(
                    "production_ready", True
                ),
            ),
        ),
        (
            "route_migration_non_additive",
            "E_LEDGER_NON_ADDITIVE_DECLARATION",
            lambda tmp: mutate_yaml_file(
                tmp,
                LEDGER_PATH,
                lambda data: data["grc_3600_execution_plan_status"]["route_migration_19"].__setitem__(
                    "additive_only", False
                ),
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
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--selftest", action="store_true", help="run fail-closed mutation tests")
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
