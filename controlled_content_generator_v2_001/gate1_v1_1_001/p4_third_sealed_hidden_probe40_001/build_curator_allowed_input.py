#!/usr/bin/env python3
"""Build the history-free curator input projection for the third P4 probe."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("build_curator_allowed_input refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_P5_PREREQUISITE_P4_AUTHOR_OUTPUT_RECOVERY_001"
SCHEMA_VERSION = "gate1-third-p4-curator-allowed-input-v1.0"
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
P2_COMPONENT_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001/component"
)
COMPONENT_PATH = P2_COMPONENT_ROOT / "active_gate1_components.v0.1.jsonl"
EDGE_PATH = P2_COMPONENT_ROOT / "active_gate1_edges.v0.1.jsonl"
RULE_PATH = P2_COMPONENT_ROOT / "active_control_rules.v0.1.jsonl"

PROFILE_FIELDS = (
    "content_product_type_id",
    "canonical_slug",
    "chinese_label",
    "family_id",
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
)
COMPONENT_FIELDS = (
    "component_id",
    "component_version",
    "component_digest",
    "component_role",
    "composition_asset_class",
    "mechanism",
    "claim_boundary",
    "truth_boundary",
    "role_authority_boundary",
    "required_input_slots",
    "required_fact_slots",
    "required_authorization_slots",
    "missing_input_behavior",
    "compatibility_rules",
    "forbidden_combinations",
)
EDGE_FIELDS = (
    "edge_id",
    "edge_digest",
    "component_id",
    "component_digest",
    "content_product_type_id",
    "required_component_role",
    "selection_purpose",
    "component_exact_binding",
    "profile_exact_binding",
    "shared_material_contract",
    "missing_input_behavior",
    "forbidden_combinations",
)
RULE_FIELDS = (
    "control_rule_id",
    "control_rule_digest",
    "source_mechanism",
    "trigger_condition",
    "blocking_or_repair_action",
    "applicability_boundary",
    "false_positive_handling",
    "may_write_audience_surface",
    "contributes_component_supply",
)
EXPECTED_COUNTS = {
    "content_product_profile": 20,
    "active_component": 68,
    "active_edge": 85,
    "active_control_rule": 8,
}
FORBIDDEN_HISTORICAL_KEYS = frozenset(
    {
        "case_id",
        "scenario_id",
        "scenario_name",
        "scenario_payload",
        "source_excerpt",
        "fact_value",
        "output_text",
        "review_judgment",
        "gold_primary_action",
        "gold_primary_reason_category",
    }
)


class AllowedInputError(ValueError):
    """Stable fail-closed error for the curator projection."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise AllowedInputError(f"{code}{suffix}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), "E_JSONL_OBJECT", f"{path}:{line_number}")
        rows.append(value)
    return rows


def _read_profiles(path: Path) -> list[dict[str, Any]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(document, Mapping), "E_PROFILE_DOCUMENT")
    registry = document.get("content_product_profile_registry")
    require(isinstance(registry, Mapping), "E_PROFILE_REGISTRY")
    profiles = registry.get("profiles")
    require(isinstance(profiles, list), "E_PROFILE_LIST")
    rows = [dict(row) for row in profiles if isinstance(row, Mapping)]
    require(len(rows) == len(profiles), "E_PROFILE_OBJECT")
    return rows


def _project(row: Mapping[str, Any], fields: Sequence[str], code: str) -> dict[str, Any]:
    missing = [field for field in fields if field not in row]
    require(not missing, code, ",".join(missing))
    return {field: copy.deepcopy(row[field]) for field in fields}


def _assert_history_free(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            require(key not in FORBIDDEN_HISTORICAL_KEYS, "E_HISTORICAL_CASE_FIELD", f"{path}.{key}")
            _assert_history_free(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_history_free(child, f"{path}[{index}]")


def _snapshot(root: Path, path: Path, row_count: int) -> dict[str, Any]:
    return {
        "repository_path": path.as_posix(),
        "sha256": sha256_file(root / path),
        "row_count": row_count,
        "read_mode": "SCHEMA_ONLY_NO_HISTORICAL_CASE_TEXT",
    }


def build_allowed_input(root: Path = ROOT) -> dict[str, Any]:
    profiles = _read_profiles(root / PROFILE_PATH)
    components = _read_jsonl(root / COMPONENT_PATH)
    edges = _read_jsonl(root / EDGE_PATH)
    rules = _read_jsonl(root / RULE_PATH)

    require(len(profiles) == EXPECTED_COUNTS["content_product_profile"], "E_PROFILE_COUNT")
    require(len(components) == EXPECTED_COUNTS["active_component"], "E_COMPONENT_COUNT")
    require(len(edges) == EXPECTED_COUNTS["active_edge"], "E_EDGE_COUNT")
    require(len(rules) == EXPECTED_COUNTS["active_control_rule"], "E_RULE_COUNT")
    require(all(row.get("active") is True for row in components), "E_COMPONENT_NOT_ACTIVE")
    require(all(row.get("active") is True for row in edges), "E_EDGE_NOT_ACTIVE")
    require(all(row.get("active") is True for row in rules), "E_RULE_NOT_ACTIVE")

    profile_schemas = [_project(row, PROFILE_FIELDS, "E_PROFILE_FIELD") for row in profiles]
    component_schemas = [
        _project(row, COMPONENT_FIELDS, "E_COMPONENT_FIELD") for row in components
    ]
    edge_schemas = [_project(row, EDGE_FIELDS, "E_EDGE_FIELD") for row in edges]
    rule_schemas = [_project(row, RULE_FIELDS, "E_RULE_FIELD") for row in rules]
    for collection in (profile_schemas, component_schemas, edge_schemas, rule_schemas):
        _assert_history_free(collection)

    profile_ids = {str(row["content_product_type_id"]) for row in profile_schemas}
    component_ids = {str(row["component_id"]) for row in component_schemas}
    require(profile_ids == {f"CP{index:02d}" for index in range(1, 21)}, "E_PROFILE_COVERAGE")
    require(len(component_ids) == 68, "E_COMPONENT_ID_UNIQUE")
    require(
        all(str(row["content_product_type_id"]) in profile_ids for row in edge_schemas),
        "E_EDGE_PROFILE_UNKNOWN",
    )
    require(
        all(str(row["component_id"]) in component_ids for row in edge_schemas),
        "E_EDGE_COMPONENT_UNKNOWN",
    )
    require(len({str(row["edge_id"]) for row in edge_schemas}) == 85, "E_EDGE_ID_UNIQUE")
    require(
        len({str(row["control_rule_id"]) for row in rule_schemas}) == 8,
        "E_RULE_ID_UNIQUE",
    )

    product_component_ids = {
        profile_id: sorted(
            str(edge["component_id"])
            for edge in edge_schemas
            if edge["content_product_type_id"] == profile_id
        )
        for profile_id in sorted(profile_ids)
    }
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "purpose": "CURATOR_SCHEMA_INPUT_ONLY",
        "source_snapshots": {
            "profiles": _snapshot(root, PROFILE_PATH, len(profiles)),
            "components": _snapshot(root, COMPONENT_PATH, len(components)),
            "edges": _snapshot(root, EDGE_PATH, len(edges)),
            "control_rules": _snapshot(root, RULE_PATH, len(rules)),
        },
        "profile_schemas": sorted(
            profile_schemas, key=lambda row: str(row["content_product_type_id"])
        ),
        "component_schemas": sorted(
            component_schemas, key=lambda row: str(row["component_id"])
        ),
        "edge_schemas": sorted(edge_schemas, key=lambda row: str(row["edge_id"])),
        "control_rule_schemas": sorted(
            rule_schemas, key=lambda row: str(row["control_rule_id"])
        ),
        "product_component_ids": product_component_ids,
        "curation_boundaries": {
            "historical_case_text_available": False,
            "historical_output_available": False,
            "historical_gold_pairing_available": False,
            "semantic_content_generation_by_builder": False,
            "synthetic_qualification_only": True,
            "publishable": False,
            "runtime_consumable": False,
            "counts_toward_300": False,
        },
        "allowed_input_digest": "",
    }
    result["allowed_input_digest"] = object_digest(result, "allowed_input_digest")
    validate_allowed_input(result, root)
    return result


def validate_allowed_input(value: Mapping[str, Any], root: Path = ROOT) -> None:
    expected = {
        "schema_version",
        "task_id",
        "purpose",
        "source_snapshots",
        "profile_schemas",
        "component_schemas",
        "edge_schemas",
        "control_rule_schemas",
        "product_component_ids",
        "curation_boundaries",
        "allowed_input_digest",
    }
    require(set(value) == expected, "E_ALLOWED_INPUT_FIELDS")
    require(value.get("schema_version") == SCHEMA_VERSION, "E_ALLOWED_INPUT_SCHEMA")
    require(value.get("task_id") == TASK_ID, "E_ALLOWED_INPUT_TASK")
    require(value.get("purpose") == "CURATOR_SCHEMA_INPUT_ONLY", "E_ALLOWED_INPUT_PURPOSE")
    collections = (
        ("profile_schemas", 20, PROFILE_FIELDS),
        ("component_schemas", 68, COMPONENT_FIELDS),
        ("edge_schemas", 85, EDGE_FIELDS),
        ("control_rule_schemas", 8, RULE_FIELDS),
    )
    for key, count, fields in collections:
        rows = value.get(key)
        require(isinstance(rows, list) and len(rows) == count, "E_ALLOWED_INPUT_COUNT", key)
        require(
            all(isinstance(row, Mapping) and set(row) == set(fields) for row in rows),
            "E_ALLOWED_INPUT_ROW_FIELDS",
            key,
        )
        _assert_history_free(rows, f"$.{key}")
    profiles = value["profile_schemas"]
    components = value["component_schemas"]
    edges = value["edge_schemas"]
    rules = value["control_rule_schemas"]
    profile_ids = {str(row["content_product_type_id"]) for row in profiles}
    component_ids = {str(row["component_id"]) for row in components}
    require(profile_ids == {f"CP{index:02d}" for index in range(1, 21)}, "E_ALLOWED_PROFILE_COVERAGE")
    require(len(component_ids) == 68, "E_ALLOWED_COMPONENT_IDS")
    require(len({str(row["edge_id"]) for row in edges}) == 85, "E_ALLOWED_EDGE_IDS")
    require(len({str(row["control_rule_id"]) for row in rules}) == 8, "E_ALLOWED_RULE_IDS")
    require(
        all(
            str(row["content_product_type_id"]) in profile_ids
            and str(row["component_id"]) in component_ids
            for row in edges
        ),
        "E_ALLOWED_EDGE_REFERENCE",
    )
    expected_bindings = {
        profile_id: sorted(
            str(edge["component_id"])
            for edge in edges
            if edge["content_product_type_id"] == profile_id
        )
        for profile_id in sorted(profile_ids)
    }
    require(value.get("product_component_ids") == expected_bindings, "E_ALLOWED_PRODUCT_BINDINGS")
    snapshots = value.get("source_snapshots")
    require(isinstance(snapshots, Mapping), "E_ALLOWED_SOURCE_SNAPSHOTS")
    expected_snapshots = {
        "profiles": _snapshot(root, PROFILE_PATH, 20),
        "components": _snapshot(root, COMPONENT_PATH, 68),
        "edges": _snapshot(root, EDGE_PATH, 85),
        "control_rules": _snapshot(root, RULE_PATH, 8),
    }
    require(snapshots == expected_snapshots, "E_ALLOWED_SOURCE_SNAPSHOT_BINDING")
    boundaries = value.get("curation_boundaries")
    require(isinstance(boundaries, Mapping), "E_ALLOWED_INPUT_BOUNDARIES")
    require(
        boundaries
        == {
            "historical_case_text_available": False,
            "historical_output_available": False,
            "historical_gold_pairing_available": False,
            "semantic_content_generation_by_builder": False,
            "synthetic_qualification_only": True,
            "publishable": False,
            "runtime_consumable": False,
            "counts_toward_300": False,
        },
        "E_ALLOWED_INPUT_BOUNDARIES",
    )
    require(
        value.get("allowed_input_digest") == object_digest(value, "allowed_input_digest"),
        "E_ALLOWED_INPUT_DIGEST",
    )


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
        handle.write("\n")


def selftest() -> None:
    first = build_allowed_input()
    second = build_allowed_input()
    require(canonical_json(first) == canonical_json(second), "E_NONDETERMINISTIC")
    changed = copy.deepcopy(first)
    changed["profile_schemas"][0]["scenario_id"] = "forbidden"
    try:
        validate_allowed_input(changed)
    except AllowedInputError:
        pass
    else:
        raise AllowedInputError("E_SELFTEST_FALSE_NEGATIVE")
    mutations: tuple[tuple[str, Any], ...] = (
        ("empty_profile", lambda value: value["profile_schemas"].__setitem__(0, {})),
        ("snapshot", lambda value: value["source_snapshots"]["profiles"].__setitem__("sha256", "0" * 64)),
        ("binding", lambda value: value["product_component_ids"].__setitem__("CP01", [])),
    )
    for name, mutate in mutations:
        changed = copy.deepcopy(first)
        mutate(changed)
        changed["allowed_input_digest"] = object_digest(changed, "allowed_input_digest")
        try:
            validate_allowed_input(changed)
        except AllowedInputError:
            continue
        raise AllowedInputError(f"E_SELFTEST_FALSE_NEGATIVE:{name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        result = build_allowed_input()
        if args.selftest:
            selftest()
        if args.output is not None:
            _write_exclusive(args.output, result)
    except (AllowedInputError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"FAIL {exc}\n")
        return 1
    print(
        "PASS profiles=20 components=68 edges=85 rules=8 "
        f"digest={result['allowed_input_digest']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
