#!/usr/bin/env python3
"""Canonical typed route-input contract shared by P3 recovery and resealed P4."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("route_contract refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_P3_ROUTE_INPUT_COMPILER_RECOVERY_AND_P4_RESEALED_PROBE40_001"
CONTRACT_VERSION = "gate1-canonical-route-input-v1.0"
COMPILER_VERSION = "gate1-route-input-compiler-v1.0"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p3_route_input_compiler_recovery_001"
)
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
P2_CORE_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001/p2_generator_core.py"
)

SLOT_CLASSES = ("source", "fact", "authorization")
PRESENT_FIELD_BY_CLASS = {
    "source": "present_source_slots",
    "fact": "present_fact_slots",
    "authorization": "present_authorization_slots",
}
REQUIRED_FIELD_BY_CLASS = {
    "source": "required_source_slots",
    "fact": "required_fact_slots",
    "authorization": "required_authorization_slots",
}
ALLOWED_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "task_id",
        "case_id",
        "profile_id",
        "provided",
        "missing",
        "risk_codes",
        "hard_guard_hits",
        "degrade_request",
        "provenance",
        "input_digest",
    }
)
FORBIDDEN_ANSWER_KEYS = frozenset(
    {
        "anomaly_class",
        "gold_primary_action",
        "gold_primary_reason_category",
        "expected_action",
        "expected_reason",
        "review_verdict",
    }
)
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class RouteContractError(ValueError):
    """Fail-closed contract or compilation error with a stable reason code."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise RouteContractError(f"{code}{suffix}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def digest_object(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    return digest_object({key: child for key, child in value.items() if key != digest_key})


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), "E_JSONL_OBJECT", f"{path}:{line_number}")
        rows.append(value)
    return rows


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "E_YAML_OBJECT", path.as_posix())
    return value


def profile_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    registry = load_yaml(root / PROFILE_PATH).get("content_product_profile_registry")
    require(isinstance(registry, dict), "E_PROFILE_REGISTRY")
    profiles = registry.get("profiles")
    require(isinstance(profiles, list) and len(profiles) == 20, "E_PROFILE_COUNT")
    rows = [dict(profile) for profile in profiles if isinstance(profile, dict)]
    require(len(rows) == 20, "E_PROFILE_OBJECTS")
    return rows


def profile_by_id(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    return {str(row["content_product_type_id"]): row for row in profile_rows(root)}


def required_slots(profile: Mapping[str, Any]) -> dict[str, list[str]]:
    requirements = profile.get("input_requirements")
    require(isinstance(requirements, Mapping), "E_PROFILE_INPUT_REQUIREMENTS")
    result: dict[str, list[str]] = {}
    for slot_class in SLOT_CLASSES:
        value = requirements.get(REQUIRED_FIELD_BY_CLASS[slot_class])
        require(isinstance(value, list) and value, "E_PROFILE_REQUIRED_SLOTS", slot_class)
        typed = [str(item) for item in value]
        require(all(typed) and len(typed) == len(set(typed)), "E_PROFILE_SLOT_IDS", slot_class)
        result[slot_class] = typed
    return result


def allowed_degrade_outputs(profile: Mapping[str, Any], slot_class: str) -> set[str]:
    route_id = f"required_{slot_class}_missing"
    routes = profile.get("input_sufficiency_routes")
    require(isinstance(routes, list), "E_PROFILE_ROUTE_LIST")
    for route in routes:
        if isinstance(route, Mapping) and route.get("route_id") == route_id:
            require(route.get("audience_facing_body_allowed") is False, "E_PROFILE_DEGRADE_AUDIENCE")
            outputs = route.get("allowed_outputs")
            require(isinstance(outputs, list) and outputs, "E_PROFILE_DEGRADE_OUTPUTS")
            return {str(item) for item in outputs}
    raise RouteContractError(f"E_PROFILE_ROUTE_MISSING:{route_id}")


def _load_p2_core(root: Path = ROOT) -> ModuleType:
    module_name = "gate1_frozen_p2_route_core"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    path = root / P2_CORE_PATH
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, "E_ROUTE_ENGINE_IMPORT_SPEC")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def allowed_risk_codes(root: Path = ROOT) -> set[str]:
    core = _load_p2_core(root)
    return set(core.AUTHORIZATION_BLOCKING_RISKS).union(core.FACT_BLOCKING_RISKS)


def _assert_exact_keys(value: Mapping[str, Any], expected: set[str], code: str) -> None:
    actual = set(map(str, value.keys()))
    require(actual == expected, code, canonical_json(sorted(actual.symmetric_difference(expected))))


def _assert_no_answer_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            require(key_text not in FORBIDDEN_ANSWER_KEYS, "E_ROUTE_GOLD_LEAK", f"{path}.{key_text}")
            _assert_no_answer_keys(child, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_answer_keys(child, f"{path}[{index}]")


def validate_contract(record: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    _assert_exact_keys(record, set(ALLOWED_TOP_LEVEL_KEYS), "E_ROUTE_CONTRACT_KEYS")
    _assert_no_answer_keys(record)
    require(record.get("schema_version") == CONTRACT_VERSION, "E_ROUTE_CONTRACT_VERSION")
    require(record.get("task_id") == TASK_ID, "E_ROUTE_CONTRACT_TASK")
    case_id = record.get("case_id")
    profile_id = record.get("profile_id")
    require(isinstance(case_id, str) and case_id.strip(), "E_ROUTE_CASE_ID")
    require(isinstance(profile_id, str) and profile_id.strip(), "E_ROUTE_PROFILE_ID")
    profiles = profile_by_id(root)
    require(profile_id in profiles, "E_ROUTE_PROFILE_UNKNOWN", str(profile_id))
    profile = profiles[profile_id]
    required = required_slots(profile)

    provided = record.get("provided")
    missing = record.get("missing")
    require(isinstance(provided, Mapping), "E_ROUTE_PROVIDED_OBJECT")
    require(isinstance(missing, Mapping), "E_ROUTE_MISSING_OBJECT")
    _assert_exact_keys(provided, set(SLOT_CLASSES), "E_ROUTE_PROVIDED_CLASSES")
    _assert_exact_keys(missing, set(SLOT_CLASSES), "E_ROUTE_MISSING_CLASSES")

    provided_ids: dict[str, list[str]] = {}
    missing_ids: dict[str, list[str]] = {}
    for slot_class in SLOT_CLASSES:
        provided_rows = provided.get(slot_class)
        missing_rows = missing.get(slot_class)
        require(isinstance(provided_rows, list), "E_ROUTE_PROVIDED_LIST", slot_class)
        require(isinstance(missing_rows, list), "E_ROUTE_MISSING_LIST", slot_class)
        slot_ids: list[str] = []
        for item in provided_rows:
            require(isinstance(item, Mapping), "E_ROUTE_PROVIDED_ITEM", slot_class)
            _assert_exact_keys(item, {"slot_id", "value_ref", "value_digest"}, "E_ROUTE_PROVIDED_ITEM_KEYS")
            slot_id = item.get("slot_id")
            value_ref = item.get("value_ref")
            value_digest = item.get("value_digest")
            require(isinstance(slot_id, str) and slot_id.strip(), "E_ROUTE_SLOT_ID_EMPTY")
            require(isinstance(value_ref, str) and value_ref.strip(), "E_ROUTE_VALUE_REF_EMPTY", str(slot_id))
            require(isinstance(value_digest, str) and HEX_64.fullmatch(value_digest) is not None, "E_ROUTE_VALUE_DIGEST", str(slot_id))
            require(value_digest == sha256_bytes(value_ref.encode("utf-8")), "E_ROUTE_VALUE_DIGEST_MISMATCH", str(slot_id))
            slot_ids.append(slot_id)
        typed_missing = [str(item) for item in missing_rows]
        require(all(typed_missing), "E_ROUTE_MISSING_SLOT_EMPTY", slot_class)
        require(len(slot_ids) == len(set(slot_ids)), "E_ROUTE_PROVIDED_DUPLICATE", slot_class)
        require(len(typed_missing) == len(set(typed_missing)), "E_ROUTE_MISSING_DUPLICATE", slot_class)
        require(set(slot_ids).isdisjoint(typed_missing), "E_ROUTE_SLOT_CONTRADICTION", slot_class)
        require(set(slot_ids).union(typed_missing) == set(required[slot_class]), "E_ROUTE_SLOT_PARTITION", slot_class)
        provided_ids[slot_class] = sorted(slot_ids)
        missing_ids[slot_class] = sorted(typed_missing)

    risk_codes = record.get("risk_codes")
    hard_guard_hits = record.get("hard_guard_hits")
    require(isinstance(risk_codes, list), "E_ROUTE_RISK_LIST")
    require(isinstance(hard_guard_hits, list), "E_ROUTE_GUARD_LIST")
    risks = [str(item) for item in risk_codes]
    guards = [str(item) for item in hard_guard_hits]
    require(all(risks) and len(risks) == len(set(risks)), "E_ROUTE_RISK_IDS") if risks else None
    require(all(guards) and len(guards) == len(set(guards)), "E_ROUTE_GUARD_IDS") if guards else None
    require(set(risks).issubset(allowed_risk_codes(root)), "E_ROUTE_RISK_UNKNOWN")
    profile_guards = {str(item) for item in profile.get("anti_pattern_rule_refs", [])}
    require(set(guards).issubset(profile_guards), "E_ROUTE_GUARD_UNKNOWN")

    degrade = record.get("degrade_request")
    require(isinstance(degrade, Mapping), "E_ROUTE_DEGRADE_OBJECT")
    _assert_exact_keys(degrade, {"enabled", "artifact_type", "payload"}, "E_ROUTE_DEGRADE_KEYS")
    enabled = degrade.get("enabled")
    artifact_type = degrade.get("artifact_type")
    payload = degrade.get("payload")
    require(isinstance(enabled, bool), "E_ROUTE_DEGRADE_ENABLED")
    require(isinstance(artifact_type, str), "E_ROUTE_DEGRADE_TYPE")
    require(isinstance(payload, Mapping), "E_ROUTE_DEGRADE_PAYLOAD")
    missing_classes = [slot_class for slot_class in SLOT_CLASSES if missing_ids[slot_class]]
    if enabled:
        require(len(missing_classes) == 1, "E_ROUTE_DEGRADE_MISSING_CLASS")
        require(bool(artifact_type.strip()) and bool(payload), "E_ROUTE_DEGRADE_INCOMPLETE")
        require(
            artifact_type in allowed_degrade_outputs(profile, missing_classes[0]),
            "E_ROUTE_DEGRADE_NOT_ALLOWED",
            artifact_type,
        )
    else:
        require(artifact_type == "" and not payload, "E_ROUTE_DEGRADE_DISABLED_PAYLOAD")

    provenance = record.get("provenance")
    require(isinstance(provenance, Mapping), "E_ROUTE_PROVENANCE_OBJECT")
    _assert_exact_keys(provenance, {"source_kind", "record_refs"}, "E_ROUTE_PROVENANCE_KEYS")
    require(
        provenance.get("source_kind") in {"SYNTHETIC_OPEN_DEVELOPMENT", "SYNTHETIC_SEALED_QUALIFICATION"},
        "E_ROUTE_PROVENANCE_KIND",
    )
    refs = provenance.get("record_refs")
    require(isinstance(refs, list) and refs and all(isinstance(item, str) and item for item in refs), "E_ROUTE_PROVENANCE_REFS")
    input_digest = record.get("input_digest")
    require(isinstance(input_digest, str) and input_digest == object_digest(record, "input_digest"), "E_ROUTE_INPUT_DIGEST")
    return {
        "profile": profile,
        "provided_ids": provided_ids,
        "missing_ids": missing_ids,
        "risks": sorted(risks),
        "guards": sorted(guards),
        "degrade": dict(degrade),
    }


def compile_route_input(record: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    validated = validate_contract(record, root)
    degrade = validated["degrade"]
    payload = {
        "profile_id": record["profile_id"],
        PRESENT_FIELD_BY_CLASS["source"]: validated["provided_ids"]["source"],
        PRESENT_FIELD_BY_CLASS["fact"]: validated["provided_ids"]["fact"],
        PRESENT_FIELD_BY_CLASS["authorization"]: validated["provided_ids"]["authorization"],
        "hard_guard_hits": validated["guards"],
        "risk_points": validated["risks"],
        "partial_safe": degrade["enabled"],
        "requested_degraded_output": degrade["artifact_type"],
        "partial_artifact_payload": dict(degrade["payload"]),
    }
    compiled: dict[str, Any] = {
        "schema_version": "gate1-compiled-route-input-v1.0",
        "task_id": TASK_ID,
        "compiler_version": COMPILER_VERSION,
        "case_id": record["case_id"],
        "profile_id": record["profile_id"],
        "actual_input_payload": payload,
        "source_contract_digest": record["input_digest"],
        "gold_fields_present": False,
    }
    compiled["compiled_route_payload_digest"] = object_digest(compiled, "compiled_route_payload_digest")
    return compiled


def evaluate_compiled_route(compiled: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    require(
        compiled.get("compiled_route_payload_digest")
        == object_digest(compiled, "compiled_route_payload_digest"),
        "E_COMPILED_ROUTE_DIGEST",
    )
    profiles = profile_by_id(root)
    profile_id = str(compiled.get("profile_id"))
    require(profile_id in profiles, "E_COMPILED_ROUTE_PROFILE")
    core = _load_p2_core(root)
    result = core.evaluate_route(compiled, profiles[profile_id])
    require(
        all(
            result.get(key) is False
            for key in (
                "audience_title_created",
                "audience_body_created",
                "spoken_script_created",
                "runtime_plan_created",
                "runtime_consumable",
            )
        ),
        "E_ROUTE_AUDIENCE_CONTENT",
    )
    return result

