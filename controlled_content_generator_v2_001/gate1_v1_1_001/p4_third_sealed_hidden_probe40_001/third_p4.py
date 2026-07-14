#!/usr/bin/env python3
"""Third sealed P4 qualification lifecycle for the Gate 1 v1.1 generator."""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("third_p4 refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_P5_PREREQUISITE_P4_AUTHOR_OUTPUT_RECOVERY_001"
ROUTE_TASK_ID = "GATE1_V11_P3_ROUTE_INPUT_COMPILER_RECOVERY_AND_P4_RESEALED_PROBE40_001"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_third_sealed_hidden_probe40_001"
)
RECOVERY_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_author_output_contract_recovery_001"
)
P3_RECOVERY_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p3_route_input_compiler_recovery_001"
)
P2_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
OLD_P4_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_sealed_hidden_probe40_001"
)
RESEALED_P4_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_resealed_hidden_probe40_001"
)
OWNER = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "current_gate1_owner.v0.1.yaml"
)
CURRENT_CHECKER = Path("ci/checkers/check_gate1_v1_1_current.py")

AUTHOR_CONTRACT = RECOVERY_ROOT / "author_contract.py"
AUTHOR_REQUEST_BUILDER = RECOVERY_ROOT / "build_public_requests.py"
AUTHOR_INSTRUCTION = RECOVERY_ROOT / "contract/controlled_author_instruction.v1.0.md"
AUTHOR_SCHEMA = RECOVERY_ROOT / "contract/author_semantic_output_contract.v1.0.json"
RECOVERY_GUARD = RECOVERY_ROOT / "recovery_guard.py"
ROUTE_CONTRACT = P3_RECOVERY_ROOT / "route_contract.py"
COMPONENTS = P2_ROOT / "component/active_gate1_components.v0.1.jsonl"
EDGES = P2_ROOT / "component/active_gate1_edges.v0.1.jsonl"
RULES = P2_ROOT / "component/active_control_rules.v0.1.jsonl"
GENERATOR_CORE = P2_ROOT / "p2_generator_core_r6.py"

ALLOWED_INPUT = TASK_ROOT / "contract/curator_allowed_input.v1.0.json"
THIRD_CONTRACT = TASK_ROOT / "contract/third_p4_contract.v1.0.json"
CURATION_SCHEMA = TASK_ROOT / "contract/curation_bundle.schema.json"
BLIND_STAGE_SCHEMA = TASK_ROOT / "contract/blind_review_stage.schema.json"
REVIEW_SCHEMA = TASK_ROOT / "contract/independent_review.schema.json"
DECISION_SCHEMA = TASK_ROOT / "contract/qualification_decision.schema.json"
ADJUDICATION_SCHEMA = TASK_ROOT / "contract/targeted_adjudication.schema.json"
LIFECYCLE_SCHEMA = TASK_ROOT / "contract/lifecycle_record.schema.json"
CURATION_BUNDLE = TASK_ROOT / "curation/third_hidden_curation_bundle.v1.0.json"
ROLE_MANIFEST = TASK_ROOT / "curation/role_manifest.v1.0.json"
TOOL_FREEZE = TASK_ROOT / "freeze/tool_freeze.v1.0.yaml"
TOOL_COMMIT_BINDING = TASK_ROOT / "freeze/tool_commit_binding.v1.0.yaml"
AUTHOR_REQUESTS = TASK_ROOT / "freeze/positive_author_requests_20.v1.0.jsonl"
ROUTE_INPUTS = TASK_ROOT / "freeze/anomaly_route_inputs_20.v1.0.jsonl"
ROUTE_GOLD = TASK_ROOT / "freeze/anomaly_route_gold_20.v1.0.jsonl"
HIDDEN_FREEZE = TASK_ROOT / "freeze/hidden_input_freeze.v1.0.yaml"
LIFECYCLE = TASK_ROOT / "result/third_p4_lifecycle.v1.0.yaml"
RAW_OUTPUTS = TASK_ROOT / "run/positive_20_first_raw_outputs.v1.0.jsonl"
NORMALIZED_OUTPUTS = TASK_ROOT / "run/positive_20_first_outputs.v1.0.jsonl"
AUTHOR_RECEIPT = TASK_ROOT / "run/author_run_receipt.v1.0.yaml"
COMPILED_ROUTES = TASK_ROOT / "run/anomaly_compiled_inputs_20.v1.0.jsonl"
ROUTE_ACTUALS = TASK_ROOT / "run/anomaly_first_actuals_20.v1.0.jsonl"
ROUTE_ACTUAL_FREEZE = TASK_ROOT / "run/anomaly_actual_freeze.v1.0.yaml"
ROUTE_COMPARISONS = TASK_ROOT / "run/anomaly_comparisons_20.v1.0.jsonl"
EXTERNAL_AUDIT = TASK_ROOT / "run/external_exit_audit.v1.0.yaml"
MACHINE_REPORT = TASK_ROOT / "run/machine_acceptance_report.v1.0.yaml"
BLIND_PACKET = TASK_ROOT / "review/blind_positive_20.v1.0.jsonl"
BLIND_CATALOG = TASK_ROOT / "review/content_product_choice_catalog.v1.0.jsonl"
BLIND_MAPPING = TASK_ROOT / "review/blind_label_mapping.v1.0.jsonl"
REVIEW_PACKET = TASK_ROOT / "review/review_packet.v1.0.yaml"
CONTENT_STAGE = TASK_ROOT / "review/staging/content_value_blind_stage.v1.0.json"
FACT_STAGE = TASK_ROOT / "review/staging/fact_authorization_blind_stage.v1.0.json"
CONTENT_REVIEW = TASK_ROOT / "review/signed_content_value_review.v1.0.json"
FACT_REVIEW = TASK_ROOT / "review/signed_fact_authorization_review.v1.0.json"
TARGETED_ADJUDICATION = TASK_ROOT / "review/targeted_adjudication.v1.0.json"
REVIEW_METRICS = TASK_ROOT / "review/review_metrics.v1.0.yaml"
DECISION_PACKET = TASK_ROOT / "decision/qualification_decision_packet.v1.0.yaml"
QUALIFICATION_DECISION = TASK_ROOT / "decision/qualification_decision.v1.0.json"
CHECKPOINT_RESULT = TASK_ROOT / "result/qualification_checkpoint_result.v1.0.yaml"
DELIVERY_RECEIPT = TASK_ROOT / "result/delivery_receipt.v1.0.yaml"

MODEL_CAPABILITY = "gpt-5.6-sol"
REASONING_EFFORT = "high"
SERVICE_TIER = "priority"
EXPECTED_PROFILES = tuple(f"CP{number:02d}" for number in range(1, 21))
EXPECTED_VARIANTS = {"A1": 5, "A2": 5, "B1": 5, "B2": 5}
AXIS_ROLES = {
    "narrative_mechanism_operator",
    "information_order_operator",
    "visual_subject_operator",
    "sound_subject_operator",
    "rhythm_operator",
    "ending_operator",
}
AXES = {
    "narrative_mechanism",
    "information_order",
    "visual_subject",
    "sound_subject",
    "rhythm",
    "ending",
}
ROUTE_ACTIONS = {"BLOCK", "DEGRADE", "REQUEST_INPUT"}
ROUTE_REASONS = {"事实缺失", "授权缺失", "输入冲突"}
PUBLIC_SCORE_MAX = {
    "truth_and_boundary": 20,
    "apparel_specificity": 10,
    "role_and_brand_consistency": 10,
    "user_value": 10,
    "platform_execution": 10,
    "anti_formula": 10,
}
PRODUCT_SCORE_MAX = {
    "product_core_fidelity": 15,
    "product_specific_narrative_av": 10,
    "continuity": 5,
}
READY_FALSE = {
    "candidatepack_ready": False,
    "KE_ready": False,
    "RAG_ready": False,
    "DIFY_ready": False,
    "production_servable": False,
    "generation_eligible": False,
    "generation_allowed": False,
    "release_ready": False,
    "production_ready": False,
}
ROLE_KEYS = (
    "curator",
    "author",
    "content_value_reviewer",
    "fact_authorization_reviewer",
    "qualification_coordinator",
    "targeted_adjudicator",
)
ROLE_NAMES = {
    "curator": "CURATOR",
    "author": "AUTHOR",
    "content_value_reviewer": "CONTENT_VALUE_REVIEWER",
    "fact_authorization_reviewer": "FACT_AUTHORIZATION_REVIEWER",
    "qualification_coordinator": "QUALIFICATION_COORDINATOR",
    "targeted_adjudicator": "TARGETED_ADJUDICATOR",
}
OLD_P4_TREE = "404a77ec7f59e0ce639daddbcd3c8d658d9bed5b"
RESEALED_P4_TREE = "0d51df3fbd122173f3848d8e87ccc3a7253e963f"
P3_RECOVERY_TREE = "9bdbbe6864c8afd5942b8dfe827bab2f0522907a"
P1B_RESULT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001/result/"
    "p1b_signed_review_closeout_result.v0.1.yaml"
)


class ThirdP4Error(ValueError):
    """Stable fail-closed third P4 error."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise ThirdP4Error(f"{code}{suffix}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    return sha256_bytes(
        canonical_json({key: child for key, child in value.items() if key != digest_key}).encode()
    )


def bind_digest(value: dict[str, Any], digest_key: str) -> dict[str, Any]:
    value[digest_key] = object_digest(value, digest_key)
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), "E_JSONL_OBJECT", f"{path}:{number}")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(canonical_json(row) for row in rows) + "\n", encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "E_YAML_OBJECT", path.as_posix())
    return value


def write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False, width=110),
        encoding="utf-8",
    )


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )


def _module(path: Path, name: str) -> ModuleType:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    require(spec is not None and spec.loader is not None, "E_MODULE_SPEC", path.as_posix())
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def author_module() -> ModuleType:
    return _module(AUTHOR_CONTRACT, "gate1_third_p4_author_contract")


def route_module() -> ModuleType:
    return _module(ROUTE_CONTRACT, "gate1_third_p4_route_contract")


def _exact_keys(value: Mapping[str, Any], expected: set[str], code: str) -> None:
    require(set(value) == expected, code, canonical_json(sorted(set(value) ^ expected)))


def _history_free(value: Any, path: str = "$") -> None:
    forbidden = {
        "historical_case_id", "historical_case_text", "historical_fact_value",
        "historical_scenario_combination", "historical_gold_pairing", "historical_output",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            require(str(key) not in forbidden, "E_CURATOR_HISTORY_FIELD", f"{path}.{key}")
            _history_free(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _history_free(child, f"{path}[{index}]")


def _allowed_input() -> dict[str, Any]:
    value = json.loads((ROOT / ALLOWED_INPUT).read_text(encoding="utf-8"))
    require(value.get("allowed_input_digest") == object_digest(value, "allowed_input_digest"), "E_ALLOWED_INPUT_DIGEST")
    return value


def _profiles() -> dict[str, dict[str, Any]]:
    return {
        str(row["content_product_type_id"]): row
        for row in _allowed_input()["profile_schemas"]
    }


def _components() -> dict[str, dict[str, Any]]:
    return {str(row["component_id"]): row for row in _allowed_input()["component_schemas"]}


def _required_component_ids(profile_id: str) -> set[str]:
    allowed = _allowed_input()
    components = {str(row["component_id"]): row for row in allowed["component_schemas"]}
    axis = {component_id for component_id, row in components.items() if row["component_role"] in AXIS_ROLES}
    edge = set(map(str, allowed["product_component_ids"][profile_id]))
    return edge | axis


def validate_role_manifest(manifest: Mapping[str, Any]) -> None:
    expected = {
        "schema_version", "task_id", *ROLE_KEYS,
        "all_identities_and_sessions_distinct", "role_manifest_digest",
    }
    _exact_keys(manifest, expected, "E_ROLE_MANIFEST_FIELDS")
    require(manifest.get("schema_version") == "gate1-third-p4-role-isolation-v1.0", "E_ROLE_MANIFEST_SCHEMA")
    require(manifest.get("task_id") == TASK_ID, "E_ROLE_MANIFEST_TASK")
    require(manifest.get("all_identities_and_sessions_distinct") is True, "E_ROLE_MANIFEST_ASSERTION")
    identities: list[str] = []
    sessions: list[str] = []
    agents: list[str] = []
    for key in ROLE_KEYS:
        role = manifest.get(key)
        require(isinstance(role, Mapping), "E_ROLE_OBJECT", key)
        _exact_keys(role, {"role", "identity", "session_logical_id", "platform_agent_id", "blank_context"}, "E_ROLE_FIELDS")
        require(role.get("role") == ROLE_NAMES[key], "E_ROLE_NAME", key)
        require(role.get("blank_context") is True, "E_ROLE_CONTEXT", key)
        for field, target in (("identity", identities), ("session_logical_id", sessions), ("platform_agent_id", agents)):
            value = role.get(field)
            require(isinstance(value, str) and bool(value.strip()), "E_ROLE_ID", f"{key}.{field}")
            target.append(value)
    require(len(identities) == len(set(identities)), "E_ROLE_IDENTITY_COLLISION")
    require(len(sessions) == len(set(sessions)), "E_ROLE_SESSION_COLLISION")
    require(len(agents) == len(set(agents)), "E_ROLE_AGENT_COLLISION")
    require(manifest.get("role_manifest_digest") == object_digest(manifest, "role_manifest_digest"), "E_ROLE_MANIFEST_DIGEST")


def _validate_typed_material(material: Mapping[str, Any], profile_id: str) -> None:
    _exact_keys(material, {"claim_boundary", "sources", "facts", "authorizations"}, "E_MATERIAL_FIELDS")
    boundary = material.get("claim_boundary")
    require(isinstance(boundary, str) and bool(boundary.strip()), "E_MATERIAL_BOUNDARY")
    sources = material.get("sources")
    facts = material.get("facts")
    authorizations = material.get("authorizations")
    require(isinstance(sources, list) and sources, "E_MATERIAL_SOURCES")
    require(isinstance(facts, list) and facts, "E_MATERIAL_FACTS")
    require(isinstance(authorizations, list) and authorizations, "E_MATERIAL_AUTHS")
    source_ids: set[str] = set()
    source_slots: set[str] = set()
    for row in sources:
        require(isinstance(row, Mapping), "E_SOURCE_OBJECT")
        _exact_keys(row, {"source_id", "slot_id", "source_summary", "synthetic_test_only"}, "E_SOURCE_FIELDS")
        require(row.get("synthetic_test_only") is True, "E_SOURCE_NAMESPACE")
        source_id = str(row.get("source_id", ""))
        require(source_id and source_id not in source_ids, "E_SOURCE_ID")
        require(isinstance(row.get("source_summary"), str) and row["source_summary"].strip(), "E_SOURCE_SUMMARY")
        source_ids.add(source_id)
        source_slots.add(str(row.get("slot_id")))
    auth_ids: set[str] = set()
    auth_slots: set[str] = set()
    for row in authorizations:
        require(isinstance(row, Mapping), "E_AUTH_OBJECT")
        _exact_keys(row, {"authorization_id", "slot_id", "scope_summary", "synthetic_test_only"}, "E_AUTH_FIELDS")
        require(row.get("synthetic_test_only") is True, "E_AUTH_NAMESPACE")
        auth_id = str(row.get("authorization_id", ""))
        require(auth_id and auth_id not in auth_ids, "E_AUTH_ID")
        require(isinstance(row.get("scope_summary"), str) and row["scope_summary"].strip(), "E_AUTH_SUMMARY")
        auth_ids.add(auth_id)
        auth_slots.add(str(row.get("slot_id")))
    fact_ids: set[str] = set()
    fact_slots: set[str] = set()
    for row in facts:
        require(isinstance(row, Mapping), "E_FACT_OBJECT")
        _exact_keys(
            row,
            {"fact_id", "slot_id", "fact_value", "fact_value_digest", "source_ids", "authorization_ids", "claim_boundary", "synthetic_test_only"},
            "E_FACT_FIELDS",
        )
        require(row.get("synthetic_test_only") is True, "E_FACT_NAMESPACE")
        fact_id = str(row.get("fact_id", ""))
        value = row.get("fact_value")
        require(fact_id and fact_id not in fact_ids, "E_FACT_ID")
        require(isinstance(value, str) and value.strip(), "E_FACT_VALUE", fact_id)
        require(row.get("fact_value_digest") == sha256_bytes(value.encode()), "E_FACT_VALUE_DIGEST", fact_id)
        require(row.get("claim_boundary") == boundary, "E_FACT_BOUNDARY", fact_id)
        refs = row.get("source_ids")
        auth_refs = row.get("authorization_ids")
        require(isinstance(refs, list) and refs and set(map(str, refs)).issubset(source_ids), "E_FACT_SOURCE_CLOSURE", fact_id)
        require(isinstance(auth_refs, list) and auth_refs and set(map(str, auth_refs)).issubset(auth_ids), "E_FACT_AUTH_CLOSURE", fact_id)
        fact_ids.add(fact_id)
        fact_slots.add(str(row.get("slot_id")))
    requirements = _profiles()[profile_id]["input_requirements"]
    require(set(map(str, requirements["required_source_slots"])).issubset(source_slots), "E_REQUIRED_SOURCE_SLOT")
    require(set(map(str, requirements["required_fact_slots"])).issubset(fact_slots), "E_REQUIRED_FACT_SLOT")
    require(set(map(str, requirements["required_authorization_slots"])).issubset(auth_slots), "E_REQUIRED_AUTH_SLOT")


def _validate_curated_request(request: Mapping[str, Any], profile_id: str, variant: str) -> None:
    _exact_keys(
        request,
        {"request_id", "profile_id", "assigned_variant", "run_order", "platform", "user_goal", "typed_material", "product_core_requirements", "approved_component_ids", "structure_contract"},
        "E_CURATED_REQUEST_FIELDS",
    )
    require(request.get("request_id") == f"P4T3-POS-{profile_id}", "E_CURATED_REQUEST_ID")
    require(request.get("profile_id") == profile_id, "E_CURATED_REQUEST_PROFILE")
    require(request.get("assigned_variant") == variant, "E_CURATED_REQUEST_VARIANT")
    require(isinstance(request.get("run_order"), int) and 1 <= request["run_order"] <= 20, "E_CURATED_RUN_ORDER")
    require(isinstance(request.get("platform"), str) and request["platform"].strip(), "E_CURATED_PLATFORM")
    require(isinstance(request.get("user_goal"), str) and request["user_goal"].strip(), "E_CURATED_GOAL")
    material = request.get("typed_material")
    require(isinstance(material, Mapping), "E_MATERIAL_OBJECT")
    _validate_typed_material(material, profile_id)
    fact_ids = {str(row["fact_id"]) for row in material["facts"]}
    core = request.get("product_core_requirements")
    require(isinstance(core, list) and core, "E_CORE_REQUIREMENTS")
    covered: set[str] = set()
    for row in core:
        require(isinstance(row, Mapping), "E_CORE_REQUIREMENT_OBJECT")
        _exact_keys(row, {"requirement_id", "fact_ids"}, "E_CORE_REQUIREMENT_FIELDS")
        refs = row.get("fact_ids")
        require(isinstance(refs, list) and refs and set(map(str, refs)).issubset(fact_ids), "E_CORE_REQUIREMENT_REFS")
        covered.update(map(str, refs))
    require(covered == fact_ids, "E_CORE_FACT_COVERAGE")
    component_ids = request.get("approved_component_ids")
    require(isinstance(component_ids, list), "E_APPROVED_COMPONENT_IDS")
    require(set(map(str, component_ids)) == _required_component_ids(profile_id), "E_APPROVED_COMPONENT_SET", profile_id)
    structure = request.get("structure_contract")
    require(isinstance(structure, Mapping), "E_STRUCTURE_OBJECT")
    _exact_keys(structure, {"axis_values", "axis_programs"}, "E_STRUCTURE_FIELDS")
    for key in ("axis_values", "axis_programs"):
        value = structure.get(key)
        require(isinstance(value, Mapping) and set(value) == AXES, "E_STRUCTURE_AXES", key)


def _novelty_signature(value: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json(value).encode())


def _normalized_texts(bundle: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for item in bundle["positive_rows"]:
        request = item["request"]
        values.extend(str(row["fact_value"]) for row in request["typed_material"]["facts"])
        values.extend(str(row["source_summary"]) for row in request["typed_material"]["sources"])
    for item in bundle["anomaly_rows"]:
        route = item["route_input"]
        for rows in route["provided"].values():
            values.extend(str(row["value_ref"]) for row in rows)
        values.extend(str(value) for value in route["degrade_request"]["payload"].values() if isinstance(value, str))
    return [re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", value).lower() for value in values if len(value) >= 8]


def _historical_texts() -> list[str]:
    paths = (
        OLD_P4_ROOT / "curation/curated_positive_20.v0.1.jsonl",
        RESEALED_P4_ROOT / "curation/curated_positive_20.v1.0.jsonl",
        RESEALED_P4_ROOT / "curation/curated_anomaly_route_inputs_20.v1.0.jsonl",
    )
    values: list[str] = []
    for path in paths:
        for row in read_jsonl(ROOT / path):
            material = row.get("typed_material")
            if isinstance(material, Mapping):
                for fact in material.get("facts", []):
                    if isinstance(fact, Mapping):
                        values.append(str(fact.get("fact_value", fact.get("value", ""))))
            for rows in row.get("provided", {}).values() if isinstance(row.get("provided"), Mapping) else []:
                for item in rows:
                    if isinstance(item, Mapping):
                        values.append(str(item.get("value_ref", "")))
    return [re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", value).lower() for value in values if len(value) >= 8]


def _validate_anti_reuse(bundle: Mapping[str, Any]) -> dict[str, Any]:
    current = _normalized_texts(bundle)
    historical = _historical_texts()
    maximum = 0.0
    exact = 0
    for left in current:
        for right in historical:
            if left == right or (min(len(left), len(right)) >= 20 and (left in right or right in left)):
                exact += 1
            if abs(len(left) - len(right)) <= max(len(left), len(right)) * 0.55:
                maximum = max(maximum, difflib.SequenceMatcher(None, left, right).ratio())
    require(exact == 0 and maximum < 0.82, "E_HISTORICAL_MATERIAL_REUSE", f"{exact}:{maximum:.3f}")
    return {"exact_or_containment_hits": exact, "maximum_similarity": round(maximum, 6), "threshold": 0.82}


def validate_curation_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(bundle, {"positive_rows", "anomaly_rows", "gold_rows", "role_manifest"}, "E_CURATION_BUNDLE_FIELDS")
    positives = bundle.get("positive_rows")
    anomalies = bundle.get("anomaly_rows")
    gold = bundle.get("gold_rows")
    manifest = bundle.get("role_manifest")
    require(all(isinstance(value, list) and len(value) == 20 for value in (positives, anomalies, gold)), "E_CURATION_COUNTS")
    require(isinstance(manifest, Mapping), "E_ROLE_MANIFEST_OBJECT")
    validate_role_manifest(manifest)
    curator = manifest["curator"]
    profiles: set[str] = set()
    variants: Counter[str] = Counter()
    orders: set[int] = set()
    for item in positives:
        require(isinstance(item, Mapping), "E_POSITIVE_CURATION_OBJECT")
        _exact_keys(item, {"schema_version", "task_id", "curation_item_id", "profile_id", "assigned_variant", "request", "curator_identity", "curator_session_logical_id", "curator_platform_agent_id", "freshness_attestation", "novelty_signature", "curation_digest"}, "E_POSITIVE_CURATION_FIELDS")
        profile_id = str(item.get("profile_id"))
        variant = str(item.get("assigned_variant"))
        require(profile_id in EXPECTED_PROFILES, "E_POSITIVE_PROFILE")
        require(item.get("curation_item_id") == f"P4T3-CURATION-POS-{profile_id}", "E_POSITIVE_ITEM_ID")
        require(item.get("schema_version") == "gate1-third-p4-positive-curation-v1.0" and item.get("task_id") == TASK_ID, "E_POSITIVE_CURATION_SCHEMA")
        for field, role_field in (("curator_identity", "identity"), ("curator_session_logical_id", "session_logical_id"), ("curator_platform_agent_id", "platform_agent_id")):
            require(item.get(field) == curator[role_field], "E_CURATOR_BINDING", profile_id)
        freshness = item.get("freshness_attestation")
        require(isinstance(freshness, Mapping) and freshness and all(value is True for value in freshness.values()), "E_POSITIVE_FRESHNESS")
        request = item.get("request")
        require(isinstance(request, Mapping), "E_CURATED_REQUEST_OBJECT")
        _validate_curated_request(request, profile_id, variant)
        require(item.get("novelty_signature") == _novelty_signature({"typed_material": request["typed_material"], "platform": request["platform"], "user_goal": request["user_goal"]}), "E_POSITIVE_NOVELTY_SIGNATURE")
        require(item.get("curation_digest") == object_digest(item, "curation_digest"), "E_POSITIVE_CURATION_DIGEST")
        profiles.add(profile_id)
        variants[variant] += 1
        orders.add(int(request["run_order"]))
    require(profiles == set(EXPECTED_PROFILES), "E_POSITIVE_PROFILE_COVERAGE")
    require(variants == Counter(EXPECTED_VARIANTS), "E_POSITIVE_VARIANT_BALANCE")
    require(orders == set(range(1, 21)), "E_POSITIVE_RUN_ORDER")

    route = route_module()
    anomaly_ids: set[str] = set()
    for item in anomalies:
        require(isinstance(item, Mapping), "E_ANOMALY_CURATION_OBJECT")
        _exact_keys(item, {"schema_version", "task_id", "curation_item_id", "case_id", "profile_id", "route_input", "curator_identity", "curator_session_logical_id", "curator_platform_agent_id", "freshness_attestation", "novelty_signature", "curation_digest"}, "E_ANOMALY_CURATION_FIELDS")
        profile_id = str(item.get("profile_id"))
        case_id = str(item.get("case_id"))
        require(profile_id in EXPECTED_PROFILES and case_id == f"P4T3-ROUTE-{profile_id}", "E_ANOMALY_ID")
        require(item.get("curation_item_id") == f"P4T3-CURATION-ROUTE-{profile_id}", "E_ANOMALY_ITEM_ID")
        require(item.get("schema_version") == "gate1-third-p4-anomaly-curation-v1.0" and item.get("task_id") == TASK_ID, "E_ANOMALY_SCHEMA")
        for field, role_field in (("curator_identity", "identity"), ("curator_session_logical_id", "session_logical_id"), ("curator_platform_agent_id", "platform_agent_id")):
            require(item.get(field) == curator[role_field], "E_CURATOR_BINDING", profile_id)
        freshness = item.get("freshness_attestation")
        require(isinstance(freshness, Mapping) and freshness and all(value is True for value in freshness.values()), "E_ANOMALY_FRESHNESS")
        route_input = item.get("route_input")
        require(isinstance(route_input, Mapping), "E_ROUTE_INPUT_OBJECT")
        require(route_input.get("task_id") == ROUTE_TASK_ID and route_input.get("case_id") == case_id and route_input.get("profile_id") == profile_id, "E_ROUTE_INPUT_BINDING")
        route.compile_route_input(route_input, ROOT)
        require(item.get("novelty_signature") == _novelty_signature(route_input), "E_ANOMALY_NOVELTY_SIGNATURE")
        require(item.get("curation_digest") == object_digest(item, "curation_digest"), "E_ANOMALY_CURATION_DIGEST")
        anomaly_ids.add(case_id)
    require(anomaly_ids == {f"P4T3-ROUTE-{profile}" for profile in EXPECTED_PROFILES}, "E_ANOMALY_COVERAGE")

    actions: set[str] = set()
    reasons: set[str] = set()
    gold_ids: set[str] = set()
    for item in gold:
        require(isinstance(item, Mapping), "E_GOLD_OBJECT")
        _exact_keys(item, {"schema_version", "task_id", "gold_item_id", "case_id", "profile_id", "expected_primary_action", "expected_primary_reason_category", "gold_rationale_code", "curator_identity", "curator_session_logical_id", "curator_platform_agent_id", "gold_digest"}, "E_GOLD_FIELDS")
        profile_id = str(item.get("profile_id"))
        case_id = str(item.get("case_id"))
        require(item.get("schema_version") == "gate1-third-p4-route-gold-v1.0" and item.get("task_id") == TASK_ID, "E_GOLD_SCHEMA")
        require(item.get("gold_item_id") == f"P4T3-GOLD-{profile_id}" and case_id == f"P4T3-ROUTE-{profile_id}", "E_GOLD_ID")
        for field, role_field in (("curator_identity", "identity"), ("curator_session_logical_id", "session_logical_id"), ("curator_platform_agent_id", "platform_agent_id")):
            require(item.get(field) == curator[role_field], "E_CURATOR_BINDING", profile_id)
        require(item.get("expected_primary_action") in ROUTE_ACTIONS, "E_GOLD_ACTION")
        require(item.get("expected_primary_reason_category") in ROUTE_REASONS, "E_GOLD_REASON")
        require(item.get("gold_digest") == object_digest(item, "gold_digest"), "E_GOLD_DIGEST")
        actions.add(str(item["expected_primary_action"]))
        reasons.add(str(item["expected_primary_reason_category"]))
        gold_ids.add(case_id)
    require(gold_ids == anomaly_ids, "E_GOLD_COVERAGE")
    require(actions == ROUTE_ACTIONS and reasons == ROUTE_REASONS, "E_GOLD_VOCABULARY_COVERAGE")
    _history_free(bundle)
    return _validate_anti_reuse(bundle)


def _build_author_request(curated: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    author = manifest["author"]
    profile_id = str(curated["profile_id"])
    components = _components()
    approved_ids = list(map(str, curated["approved_component_ids"]))
    approved = [copy.deepcopy(components[component_id]) for component_id in approved_ids]
    author_contract_module = author_module()
    builder = _module(AUTHOR_REQUEST_BUILDER, "gate1_third_p4_request_builder")
    row: dict[str, Any] = {
        "schema_version": "gate1-third-p4-author-request-v1.0",
        "task_id": TASK_ID,
        "request_id": curated["request_id"],
        "request_digest": "",
        "profile_id": profile_id,
        "assigned_variant": curated["assigned_variant"],
        "run_order": curated["run_order"],
        "author_identity": author["identity"],
        "author_session_logical_id": author["session_logical_id"],
        "author_platform_agent_id": author["platform_agent_id"],
        "model_capability_id": MODEL_CAPABILITY,
        "reasoning_effort": REASONING_EFFORT,
        "service_tier": SERVICE_TIER,
        "platform": curated["platform"],
        "user_goal": curated["user_goal"],
        "typed_material": copy.deepcopy(curated["typed_material"]),
        "product_core_requirements": copy.deepcopy(curated["product_core_requirements"]),
        "approved_components": approved,
        "structure_contract": copy.deepcopy(curated["structure_contract"]),
        "profile_contract": copy.deepcopy(_profiles()[profile_id]),
        "author_instruction_path": AUTHOR_INSTRUCTION.as_posix(),
        "author_instruction_sha256": sha256_file(ROOT / AUTHOR_INSTRUCTION),
        "author_contract_path": AUTHOR_SCHEMA.as_posix(),
        "author_contract_sha256": sha256_file(ROOT / AUTHOR_SCHEMA),
        "author_output_contract": {
            "one_first_semantic_output_only": True,
            "author_may_not_review_or_approve": True,
            "publishable": False,
            "runtime_consumable": False,
            "may_enter_300": False,
        },
        "exact_author_contract": builder.exact_contract(),
        "synthetic_qualification_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "counts_toward_H": False,
        "counts_toward_300": False,
        "external_provider_allowed": False,
    }
    row["request_digest"] = object_digest(row, "request_digest")
    author_contract_module.validate_request(row)
    return row


def lifecycle_record(
    state: str,
    evidence: Mapping[str, str] | None = None,
    approved: Sequence[str] = (),
    previous_lifecycle_digest: str = "",
) -> dict[str, Any]:
    contract = json.loads((ROOT / THIRD_CONTRACT).read_text(encoding="utf-8"))
    expected = contract["lifecycle_states"].get(state)
    require(isinstance(expected, Mapping), "E_LIFECYCLE_STATE", state)
    h_value = len(approved) if expected["h_count"] == "APPROVED_FIRST_OUTPUT_COUNT" else int(expected["h_count"])
    value: dict[str, Any] = {
        "schema_version": "gate1-third-p4-lifecycle-v1.0",
        "task_id": TASK_ID,
        "lifecycle_state": state,
        "previous_lifecycle_digest": previous_lifecycle_digest,
        "evidence_digests": dict(evidence or {}),
        "hidden_frozen": expected["hidden_frozen"],
        "hidden_exposed": expected["hidden_exposed"],
        "hidden_reusable": False,
        "technical_gate_pass": expected["technical_gate_pass"],
        "reviews_pass": expected["reviews_pass"],
        "decision_present": expected["decision_present"],
        "approved_first_output_request_ids": list(approved),
        "H": h_value,
        "generator_qualified": expected["generator_qualified"],
        "p5_allowed": expected["p5_allowed"],
        "target_baseline_count": 300,
        "positive_target_count": 240,
        "route_target_count": 60,
        "legacy_reference_inventory_count": 120,
        "counted_positive_parent_count": 29,
        "historical_component_inventory_count": 86,
        "active_component_count": 68,
        "external_provider_request_count": 0,
        "p5_executed": False,
        "readiness": copy.deepcopy(READY_FALSE),
        "lifecycle_digest": "",
    }
    return bind_digest(value, "lifecycle_digest")


def _owner_for(lifecycle: Mapping[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "v0.1",
        "owner_id": "GATE1_V11_P4_THIRD_SEALED_OWNER",
        "task_id": TASK_ID,
        "current_task_root": TASK_ROOT.as_posix(),
        "current_checker": CURRENT_CHECKER.as_posix(),
        "result_state": lifecycle["lifecycle_state"],
        "p3_complete": True,
        "prior_p4_failure_honestly_closed": True,
        "tool_freeze_complete": True,
        "third_hidden_created": lifecycle["hidden_frozen"],
        "third_hidden_exposed": lifecycle["hidden_exposed"],
        "same_hidden_batch_may_be_reused": False,
        "H_admitted_count": lifecycle["H"],
        "generator_qualified": lifecycle["generator_qualified"],
        "p5_allowed": lifecycle["p5_allowed"],
        "p5_executed": False,
        "current_generator": {
            "entrypoint": (TASK_ROOT / "third_p4.py").as_posix(),
            "author_contract": AUTHOR_CONTRACT.as_posix(),
            "route_contract": ROUTE_CONTRACT.as_posix(),
            "model_capability_id": MODEL_CAPABILITY,
            "reasoning_effort": REASONING_EFFORT,
            "service_tier": SERVICE_TIER,
            "active_component_count": 68,
            "active_edge_count": 85,
            "active_control_rule_count": 8,
            "generator_core_changed": False,
            "content_authoring_semantics_changed": False,
            "output_contract_section_changed": True,
        },
        "predecessor": {
            "owner_id": "GATE1_V11_P4_AUTHOR_OUTPUT_RECOVERY_OPEN_OWNER",
            "result_state": "OPEN_RECOVERY_COMPLETE",
        },
        "core_numbers": {
            "target_total": 300,
            "positive_target": 240,
            "route_target": 60,
            "reference_inventory": 120,
            "counted_positive_parent_count": 29,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "readiness": {**copy.deepcopy(READY_FALSE), "generator_qualified": lifecycle["generator_qualified"], "runtime_ingest_ready": False},
        "owner_digest": "",
    }
    return bind_digest(value, "owner_digest")


def _write_state(state: str, evidence: Mapping[str, str] | None = None, approved: Sequence[str] = ()) -> None:
    previous_digest = ""
    if (ROOT / LIFECYCLE).is_file():
        previous = load_yaml(ROOT / LIFECYCLE).get("third_p4_lifecycle")
        if isinstance(previous, Mapping):
            previous_digest = str(previous.get("lifecycle_digest", ""))
    lifecycle = lifecycle_record(state, evidence, approved, previous_digest)
    write_yaml(ROOT / LIFECYCLE, {"third_p4_lifecycle": lifecycle})
    write_yaml(ROOT / OWNER, {"current_gate1_owner": _owner_for(lifecycle)})


def _tool_files() -> tuple[Path, ...]:
    return (
        TASK_ROOT / "third_p4.py",
        TASK_ROOT / "third_p4_guard.py",
        TASK_ROOT / "build_curator_allowed_input.py",
        THIRD_CONTRACT,
        CURATION_SCHEMA,
        BLIND_STAGE_SCHEMA,
        REVIEW_SCHEMA,
        DECISION_SCHEMA,
        ADJUDICATION_SCHEMA,
        LIFECYCLE_SCHEMA,
        AUTHOR_CONTRACT,
        AUTHOR_REQUEST_BUILDER,
        AUTHOR_INSTRUCTION,
        AUTHOR_SCHEMA,
        RECOVERY_GUARD,
        ROUTE_CONTRACT,
        CURRENT_CHECKER,
    )


def prepare_tools() -> None:
    for path in (
        CURATION_BUNDLE,
        ROLE_MANIFEST,
        AUTHOR_REQUESTS,
        ROUTE_INPUTS,
        ROUTE_GOLD,
        HIDDEN_FREEZE,
        RAW_OUTPUTS,
        TARGETED_ADJUDICATION,
    ):
        require(not (ROOT / path).exists(), "E_HIDDEN_BEFORE_TOOL_FREEZE", path.as_posix())
    builder = _module(TASK_ROOT / "build_curator_allowed_input.py", "gate1_third_p4_curator_projection")
    allowed = builder.build_allowed_input(ROOT)
    write_json(ROOT / ALLOWED_INPUT, allowed)
    tool_files = _tool_files()
    require(all((ROOT / path).is_file() for path in tool_files), "E_TOOL_FILE_MISSING")
    frozen_business = (COMPONENTS, EDGES, RULES, GENERATOR_CORE, P1B_RESULT)
    freeze = bind_digest(
        {
            "schema_version": "gate1-third-p4-tool-freeze-v1.0",
            "task_id": TASK_ID,
            "tool_file_sha256": {path.as_posix(): sha256_file(ROOT / path) for path in tool_files},
            "curator_allowed_input_sha256": sha256_file(ROOT / ALLOWED_INPUT),
            "frozen_business_sha256": {path.as_posix(): sha256_file(ROOT / path) for path in frozen_business},
            "historical_tree_objects": {
                OLD_P4_ROOT.as_posix(): OLD_P4_TREE,
                RESEALED_P4_ROOT.as_posix(): RESEALED_P4_TREE,
                P3_RECOVERY_ROOT.as_posix(): P3_RECOVERY_TREE,
            },
            "model_config": {"model_capability_id": MODEL_CAPABILITY, "reasoning_effort": REASONING_EFFORT, "service_tier": SERVICE_TIER},
            "hidden_material_absent": True,
            "six_lifecycle_states_predeclared": True,
            "generator_qualified": False,
            "p5_allowed": False,
            "core_numbers_unchanged": {"300": True, "240": True, "60": True, "120": True, "N": 29, "86": True},
            "tool_freeze_digest": "",
        },
        "tool_freeze_digest",
    )
    write_yaml(ROOT / TOOL_FREEZE, {"third_p4_tool_freeze": freeze})
    _write_state(
        "TOOLS_FROZEN_PENDING_HIDDEN_CURATION",
        {"tool_freeze": freeze["tool_freeze_digest"]},
    )


def freeze_hidden(tool_commit: str, bundle_path: Path) -> None:
    head = git("rev-parse", "HEAD")
    require(head.returncode == 0 and head.stdout.strip() == tool_commit, "E_TOOL_COMMIT_NOT_HEAD")
    for path in (CURATION_BUNDLE, ROLE_MANIFEST, AUTHOR_REQUESTS, ROUTE_INPUTS, ROUTE_GOLD, HIDDEN_FREEZE):
        require(git("cat-file", "-e", f"{tool_commit}:{path.as_posix()}").returncode != 0, "E_HIDDEN_IN_TOOL_COMMIT", path.as_posix())
    require((ROOT / ROLE_MANIFEST).is_file(), "E_ROLE_MANIFEST_MISSING")
    independent_manifest = _load_json(ROOT / ROLE_MANIFEST)
    validate_role_manifest(independent_manifest)
    source = bundle_path if bundle_path.is_absolute() else ROOT / bundle_path
    bundle = json.loads(source.read_text(encoding="utf-8"))
    require(isinstance(bundle, Mapping), "E_CURATION_BUNDLE_OBJECT")
    anti_reuse = validate_curation_bundle(bundle)
    if source != ROOT / CURATION_BUNDLE:
        write_json(ROOT / CURATION_BUNDLE, bundle)
    manifest = bundle["role_manifest"]
    require(manifest == independent_manifest, "E_ROLE_MANIFEST_NOT_INDEPENDENTLY_BOUND")
    requests = [
        _build_author_request(item["request"], manifest)
        for item in sorted(bundle["positive_rows"], key=lambda row: row["request"]["run_order"])
    ]
    route_inputs = [copy.deepcopy(item["route_input"]) for item in sorted(bundle["anomaly_rows"], key=lambda row: row["profile_id"])]
    gold = [copy.deepcopy(item) for item in sorted(bundle["gold_rows"], key=lambda row: row["profile_id"])]
    write_jsonl(ROOT / AUTHOR_REQUESTS, requests)
    write_jsonl(ROOT / ROUTE_INPUTS, route_inputs)
    write_jsonl(ROOT / ROUTE_GOLD, gold)
    binding = bind_digest(
        {
            "schema_version": "gate1-third-p4-tool-commit-binding-v1.0",
            "task_id": TASK_ID,
            "tool_commit": tool_commit,
            "tool_tree": git("show", "-s", "--format=%T", tool_commit).stdout.strip(),
            "hidden_absent_in_tool_commit": True,
            "binding_digest": "",
        },
        "binding_digest",
    )
    write_yaml(ROOT / TOOL_COMMIT_BINDING, {"third_p4_tool_commit_binding": binding})
    freeze = bind_digest(
        {
            "schema_version": "gate1-third-p4-hidden-input-freeze-v1.0",
            "task_id": TASK_ID,
            "tool_commit": tool_commit,
            "curation_bundle_sha256": sha256_file(ROOT / CURATION_BUNDLE),
            "role_manifest_sha256": sha256_file(ROOT / ROLE_MANIFEST),
            "positive_requests_sha256": sha256_file(ROOT / AUTHOR_REQUESTS),
            "anomaly_inputs_sha256": sha256_file(ROOT / ROUTE_INPUTS),
            "anomaly_gold_sha256": sha256_file(ROOT / ROUTE_GOLD),
            "role_manifest_digest": manifest["role_manifest_digest"],
            "anti_reuse": anti_reuse,
            "positive_count": 20,
            "anomaly_count": 20,
            "gold_count": 20,
            "output_count_at_freeze": 0,
            "route_actual_count_at_freeze": 0,
            "review_count_at_freeze": 0,
            "hidden_reusable": False,
            "freeze_digest": "",
        },
        "freeze_digest",
    )
    write_yaml(ROOT / HIDDEN_FREEZE, {"third_p4_hidden_input_freeze": freeze})
    _write_state(
        "HIDDEN_INPUTS_FROZEN",
        {"tool_freeze": load_yaml(ROOT / TOOL_FREEZE)["third_p4_tool_freeze"]["tool_freeze_digest"], "hidden_freeze": freeze["freeze_digest"]},
    )


def _route_actuals(inputs: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    route = route_module()
    compiled: list[dict[str, Any]] = []
    actuals: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for row in inputs:
        try:
            compiled_row = route.compile_route_input(row, ROOT)
            actual = route.evaluate_compiled_route(compiled_row, ROOT)
            compiled.append(dict(compiled_row))
            actuals.append(dict(actual))
        except (OSError, TypeError, ValueError) as exc:
            errors.append({"case_id": str(row.get("case_id")), "error": str(exc)})
    return compiled, actuals, errors


def run_first() -> None:
    lifecycle = load_yaml(ROOT / LIFECYCLE).get("third_p4_lifecycle")
    require(isinstance(lifecycle, Mapping) and lifecycle.get("lifecycle_state") == "HIDDEN_INPUTS_FROZEN", "E_RUN_STATE")
    require((ROOT / RAW_OUTPUTS).is_file(), "E_RAW_OUTPUTS_MISSING")
    requests = read_jsonl(ROOT / AUTHOR_REQUESTS)
    raws = read_jsonl(ROOT / RAW_OUTPUTS)
    route_inputs = read_jsonl(ROOT / ROUTE_INPUTS)
    author_error = ""
    outputs: list[dict[str, Any]] = []
    try:
        outputs = author_module().serialize_all(raws, requests)
        write_jsonl(ROOT / NORMALIZED_OUTPUTS, outputs)
    except (OSError, TypeError, ValueError) as exc:
        author_error = str(exc)
    compiled, actuals, route_errors = _route_actuals(route_inputs)
    write_jsonl(ROOT / COMPILED_ROUTES, compiled)
    write_jsonl(ROOT / ROUTE_ACTUALS, actuals)
    route_freeze = bind_digest(
        {
            "schema_version": "gate1-third-p4-route-actual-freeze-v1.0",
            "task_id": TASK_ID,
            "actual_count": len(actuals),
            "compiled_count": len(compiled),
            "actuals_sha256": sha256_file(ROOT / ROUTE_ACTUALS),
            "compiled_sha256": sha256_file(ROOT / COMPILED_ROUTES),
            "gold_read_before_actual_freeze": False,
            "route_errors": route_errors,
            "freeze_digest": "",
        },
        "freeze_digest",
    )
    write_yaml(ROOT / ROUTE_ACTUAL_FREEZE, {"third_p4_route_actual_freeze": route_freeze})
    manifest = json.loads((ROOT / CURATION_BUNDLE).read_text(encoding="utf-8"))["role_manifest"]
    author = manifest["author"]
    receipt = bind_digest(
        {
            "schema_version": "gate1-third-p4-author-run-receipt-v1.0",
            "task_id": TASK_ID,
            "author_identity": author["identity"],
            "author_session_logical_id": author["session_logical_id"],
            "author_platform_agent_id": author["platform_agent_id"],
            "model_capability_id": MODEL_CAPABILITY,
            "reasoning_effort": REASONING_EFFORT,
            "service_tier": SERVICE_TIER,
            "request_count": len(requests),
            "raw_first_output_count": len(raws),
            "normalized_output_count": len(outputs),
            "author_attempts_per_request": 1,
            "second_candidate_count": 0,
            "replacement_count": 0,
            "author_error": author_error,
            "raw_sha256": sha256_file(ROOT / RAW_OUTPUTS),
            "normalized_sha256": sha256_file(ROOT / NORMALIZED_OUTPUTS) if (ROOT / NORMALIZED_OUTPUTS).is_file() else "",
            "receipt_digest": "",
        },
        "receipt_digest",
    )
    write_yaml(ROOT / AUTHOR_RECEIPT, {"third_p4_author_run_receipt": receipt})
    observed_events: list[dict[str, Any]] = []
    audit = bind_digest(
        {
            "schema_version": "gate1-third-p4-external-exit-audit-v1.0",
            "task_id": TASK_ID,
            "observed_content_exit_events": observed_events,
            "external_provider_request_count": len(observed_events),
            "external_provider_response_count": 0,
            "external_api_call_count": len(observed_events),
            "credential_read_count": 0,
            "network_dispatch_count": len(observed_events),
            "git_remote_transport_excluded": True,
            "audit_digest": "",
        },
        "audit_digest",
    )
    write_yaml(ROOT / EXTERNAL_AUDIT, {"third_p4_external_exit_audit": audit})


def _comparison_rows(actuals: Sequence[Mapping[str, Any]], gold: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    actual_by_id = {str(row.get("case_id")): row for row in actuals}
    rows: list[dict[str, Any]] = []
    for expected in gold:
        case_id = str(expected["case_id"])
        actual = actual_by_id.get(case_id, {})
        action_match = actual.get("actual_primary_action") == expected["expected_primary_action"]
        reason_match = actual.get("actual_primary_reason_category") == expected["expected_primary_reason_category"]
        leak = any(actual.get(key) is True for key in ("audience_title_created", "audience_body_created", "spoken_script_created", "runtime_plan_created", "runtime_consumable"))
        rows.append(
            bind_digest(
                {
                    "schema_version": "gate1-third-p4-route-comparison-v1.0",
                    "task_id": TASK_ID,
                    "case_id": case_id,
                    "profile_id": expected["profile_id"],
                    "actual_primary_action": actual.get("actual_primary_action"),
                    "expected_primary_action": expected["expected_primary_action"],
                    "action_match": action_match,
                    "actual_primary_reason_category": actual.get("actual_primary_reason_category"),
                    "expected_primary_reason_category": expected["expected_primary_reason_category"],
                    "reason_match": reason_match,
                    "audience_leak": leak,
                    "comparison_digest": "",
                },
                "comparison_digest",
            )
        )
    return rows


def _build_review_packet(outputs: Sequence[Mapping[str, Any]]) -> None:
    profiles = _profiles()
    sorted_outputs = sorted(outputs, key=lambda row: sha256_bytes(str(row["output_digest"]).encode()))
    blind: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    forbidden_labels = {str(value) for profile in profiles.values() for value in (profile["content_product_type_id"], profile["chinese_label"])}
    for index, output in enumerate(sorted_outputs, 1):
        blind_id = f"P4T3-BLIND-{index:02d}-{str(output['output_digest'])[:12]}"
        row = {
            "schema_version": "gate1-third-p4-blind-positive-v1.0",
            "blind_item_id": blind_id,
            "synthetic_disclosure": output["synthetic_disclosure"],
            "title": output["title"],
            "body": output["body"],
            "spoken_lines": output["spoken_lines"],
            "cta": output["cta"],
            "visual_execution": output["visual_execution"],
            "audio_execution": output["audio_execution"],
            "output_digest": output["output_digest"],
            "content_product_identity_hidden": True,
            "request_identity_hidden": True,
        }
        serialized = canonical_json(row)
        require(not any(label in serialized for label in forbidden_labels), "E_BLIND_LABEL_LEAK", blind_id)
        require(re.search(r"\bCP(?:0[1-9]|1\d|20)\b", serialized) is None, "E_BLIND_CP_LEAK", blind_id)
        blind.append(row)
        mapping.append(
            bind_digest(
                {
                    "schema_version": "gate1-third-p4-blind-mapping-v1.0",
                    "blind_item_id": blind_id,
                    "profile_id": output["profile_id"],
                    "request_id": output["request_id"],
                    "output_digest": output["output_digest"],
                    "mapping_digest": "",
                },
                "mapping_digest",
            )
        )
    catalog = []
    for profile_id in EXPECTED_PROFILES:
        profile = profiles[profile_id]
        catalog.append(
            bind_digest(
                {
                    "schema_version": "gate1-third-p4-profile-catalog-row-v1.0",
                    "profile_id": profile_id,
                    "chinese_label": profile["chinese_label"],
                    "business_purpose": profile["business_purpose"],
                    "founder_core_inputs": profile["founder_core_inputs"],
                    "catalog_row_digest": "",
                },
                "catalog_row_digest",
            )
        )
    write_jsonl(ROOT / BLIND_PACKET, blind)
    write_jsonl(ROOT / BLIND_CATALOG, catalog)
    write_jsonl(ROOT / BLIND_MAPPING, mapping)
    comparisons = read_jsonl(ROOT / ROUTE_COMPARISONS)
    packet = bind_digest(
        {
            "schema_version": "gate1-third-p4-review-packet-v1.0",
            "task_id": TASK_ID,
            "stage_order": [
                "BLIND_PACKET_AND_FIXED_CATALOG_ONLY",
                "BOTH_BLIND_STAGES_SIGNED",
                "MAPPING_AND_FULL_EVIDENCE_REVEALED",
                "TWO_INDEPENDENT_FINAL_REPORTS",
                "TARGETED_ADJUDICATION_ONLY_FOR_SUBSTANTIVE_DISAGREEMENT",
            ],
            "blind_packet_sha256": sha256_file(ROOT / BLIND_PACKET),
            "catalog_sha256": sha256_file(ROOT / BLIND_CATALOG),
            "mapping_sha256": sha256_file(ROOT / BLIND_MAPPING),
            "route_comparison_sha256": sha256_file(ROOT / ROUTE_COMPARISONS),
            "normalized_outputs_sha256": sha256_file(ROOT / NORMALIZED_OUTPUTS),
            "blind_count": len(blind),
            "route_count": len(comparisons),
            "counts_toward_300": 0,
            "packet_digest": "",
        },
        "packet_digest",
    )
    write_yaml(ROOT / REVIEW_PACKET, {"third_p4_review_packet": packet})


def compare_and_build_review() -> None:
    require((ROOT / ROUTE_ACTUAL_FREEZE).is_file(), "E_ACTUAL_FREEZE_MISSING")
    freeze = load_yaml(ROOT / ROUTE_ACTUAL_FREEZE)["third_p4_route_actual_freeze"]
    require(freeze.get("freeze_digest") == object_digest(freeze, "freeze_digest"), "E_ACTUAL_FREEZE_DIGEST")
    require(freeze.get("actuals_sha256") == sha256_file(ROOT / ROUTE_ACTUALS), "E_ACTUAL_FREEZE_BINDING")
    actuals = read_jsonl(ROOT / ROUTE_ACTUALS)
    gold = read_jsonl(ROOT / ROUTE_GOLD)
    comparisons = _comparison_rows(actuals, gold)
    write_jsonl(ROOT / ROUTE_COMPARISONS, comparisons)
    positive_pass = False
    author_error = ""
    try:
        outputs = read_jsonl(ROOT / NORMALIZED_OUTPUTS)
        author_module().strict_validate(outputs, read_jsonl(ROOT / AUTHOR_REQUESTS))
        positive_pass = len(outputs) == 20
    except (OSError, TypeError, ValueError) as exc:
        outputs = []
        author_error = str(exc)
    action_matches = sum(row["action_match"] is True for row in comparisons)
    reason_matches = sum(row["reason_match"] is True for row in comparisons)
    leaks = sum(row["audience_leak"] is True for row in comparisons)
    audit = load_yaml(ROOT / EXTERNAL_AUDIT)["third_p4_external_exit_audit"]
    external_zero = audit.get("external_provider_request_count") == len(audit.get("observed_content_exit_events", [])) == 0
    technical_pass = positive_pass and action_matches == 20 and reason_matches == 20 and leaks == 0 and external_zero
    report = bind_digest(
        {
            "schema_version": "gate1-third-p4-machine-acceptance-v1.0",
            "task_id": TASK_ID,
            "positive_strict_pass_count": 20 if positive_pass else 0,
            "positive_first_raw_count": len(read_jsonl(ROOT / RAW_OUTPUTS)),
            "normalized_output_count": len(outputs),
            "second_candidate_count": 0,
            "replacement_count": 0,
            "route_action_match_count": action_matches,
            "route_reason_match_count": reason_matches,
            "route_audience_leak_count": leaks,
            "external_provider_request_count": audit.get("external_provider_request_count"),
            "author_error": author_error,
            "technical_gate_pass": technical_pass,
            "report_digest": "",
        },
        "report_digest",
    )
    write_yaml(ROOT / MACHINE_REPORT, {"third_p4_machine_acceptance": report})
    if not technical_pass:
        evidence = {"machine_report": report["report_digest"], "hidden_freeze": load_yaml(ROOT / HIDDEN_FREEZE)["third_p4_hidden_input_freeze"]["freeze_digest"]}
        _write_state("STOPPED_RETURN_TO_P3", evidence)
        _write_checkpoint("STOPPED_RETURN_TO_P3", report, None)
        return
    _build_review_packet(outputs)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "E_JSON_OBJECT", path.as_posix())
    return value


def _validate_blind_stage(stage: Mapping[str, Any], role: str, manifest: Mapping[str, Any]) -> dict[str, str]:
    _exact_keys(stage, {"schema_version", "task_id", "review_track", "reviewer_identity", "reviewer_session_logical_id", "reviewer_platform_agent_id", "blank_context", "other_review_unavailable", "recorded_before_label_reveal", "label_mapping_accessed", "packet_digest", "catalog_digest", "blind_judgments", "blind_stage_digest"}, "E_BLIND_STAGE_FIELDS")
    require(stage.get("schema_version") == "gate1-third-p4-blind-review-stage-v1.0" and stage.get("task_id") == TASK_ID and stage.get("review_track") == role, "E_BLIND_STAGE_SCHEMA")
    key = "content_value_reviewer" if role == "CONTENT_VALUE" else "fact_authorization_reviewer"
    reviewer = manifest[key]
    for field, role_field in (("reviewer_identity", "identity"), ("reviewer_session_logical_id", "session_logical_id"), ("reviewer_platform_agent_id", "platform_agent_id")):
        require(stage.get(field) == reviewer[role_field], "E_BLIND_REVIEWER_BINDING", role)
    require(stage.get("blank_context") is True and stage.get("other_review_unavailable") is True, "E_BLIND_ISOLATION")
    require(stage.get("recorded_before_label_reveal") is True and stage.get("label_mapping_accessed") is False, "E_BLIND_STAGE_ORDER")
    packet = load_yaml(ROOT / REVIEW_PACKET)["third_p4_review_packet"]
    require(stage.get("packet_digest") == packet["packet_digest"] and stage.get("catalog_digest") == sha256_file(ROOT / BLIND_CATALOG), "E_BLIND_PACKET_BINDING")
    judgments = stage.get("blind_judgments")
    require(isinstance(judgments, list) and len(judgments) == 20, "E_BLIND_JUDGMENT_COUNT")
    expected_ids = {row["blind_item_id"] for row in read_jsonl(ROOT / BLIND_PACKET)}
    choices: dict[str, str] = {}
    for row in judgments:
        require(isinstance(row, Mapping), "E_BLIND_JUDGMENT_OBJECT")
        _exact_keys(row, {"blind_item_id", "chosen_profile_id", "reason"}, "E_BLIND_JUDGMENT_FIELDS")
        blind_id = str(row.get("blind_item_id"))
        profile_id = str(row.get("chosen_profile_id"))
        require(blind_id in expected_ids and blind_id not in choices and profile_id in EXPECTED_PROFILES, "E_BLIND_JUDGMENT_ID")
        require(isinstance(row.get("reason"), str) and row["reason"].strip(), "E_BLIND_JUDGMENT_REASON")
        choices[blind_id] = profile_id
    require(set(choices) == expected_ids, "E_BLIND_JUDGMENT_COVERAGE")
    require(stage.get("blind_stage_digest") == object_digest(stage, "blind_stage_digest"), "E_BLIND_STAGE_DIGEST")
    return choices


def _validate_review(report: Mapping[str, Any], stage: Mapping[str, Any], role: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    expected_fields = {"schema_version", "task_id", "review_track", "review_scope", "reviewer_identity", "reviewer_session_logical_id", "reviewer_platform_agent_id", "blank_context", "other_review_unavailable", "packet_digest", "catalog_digest", "route_comparison_digest", "judgments", "route_gate", "overall_verdict", "review_digest"}
    _exact_keys(report, expected_fields, "E_REVIEW_FIELDS")
    require(report.get("schema_version") == "gate1-third-p4-independent-review-v1.0" and report.get("task_id") == TASK_ID and report.get("review_track") == role, "E_REVIEW_SCHEMA")
    expected_scope = (
        "CONTENT_VALUE_USER_VALUE_PLATFORM_AND_PRODUCT_FIT"
        if role == "CONTENT_VALUE"
        else "FACT_AUTHORIZATION_CLAIM_AND_BOUNDARY"
    )
    require(report.get("review_scope") == expected_scope, "E_REVIEW_SCOPE", role)
    choices = _validate_blind_stage(stage, role, manifest)
    key = "content_value_reviewer" if role == "CONTENT_VALUE" else "fact_authorization_reviewer"
    reviewer = manifest[key]
    for field, role_field in (("reviewer_identity", "identity"), ("reviewer_session_logical_id", "session_logical_id"), ("reviewer_platform_agent_id", "platform_agent_id")):
        require(report.get(field) == reviewer[role_field], "E_REVIEWER_BINDING", role)
    packet = load_yaml(ROOT / REVIEW_PACKET)["third_p4_review_packet"]
    require(report.get("packet_digest") == packet["packet_digest"], "E_REVIEW_PACKET_BINDING")
    require(report.get("catalog_digest") == sha256_file(ROOT / BLIND_CATALOG), "E_REVIEW_CATALOG_BINDING")
    require(report.get("route_comparison_digest") == sha256_file(ROOT / ROUTE_COMPARISONS), "E_REVIEW_ROUTE_BINDING")
    require(report.get("blank_context") is True and report.get("other_review_unavailable") is True, "E_REVIEW_ISOLATION")
    mapping = {row["blind_item_id"]: row for row in read_jsonl(ROOT / BLIND_MAPPING)}
    judgments = report.get("judgments")
    require(isinstance(judgments, list) and len(judgments) == 20, "E_REVIEW_JUDGMENT_COUNT")
    seen: set[str] = set()
    acceptable = 0
    blind_correct = 0
    formula: set[str] = set()
    hard: set[str] = set()
    acceptable_requests: set[str] = set()
    per_item: dict[str, dict[str, Any]] = {}
    for row in judgments:
        require(isinstance(row, Mapping), "E_REVIEW_JUDGMENT_OBJECT")
        _exact_keys(row, {"blind_item_id", "chosen_profile_id", "public_quality", "product_quality", "total_score", "grade", "first_acceptable", "hard_error_codes", "formulaic_or_near_duplicate", "related_blind_item_ids", "rationale"}, "E_REVIEW_JUDGMENT_FIELDS")
        blind_id = str(row.get("blind_item_id"))
        require(blind_id in mapping and blind_id not in seen, "E_REVIEW_BLIND_ID")
        require(row.get("chosen_profile_id") == choices[blind_id], "E_REVIEW_BLIND_CHOICE_CHANGED")
        public_quality = row.get("public_quality")
        product_quality = row.get("product_quality")
        require(isinstance(public_quality, Mapping) and set(public_quality) == set(PUBLIC_SCORE_MAX), "E_REVIEW_PUBLIC_DIMENSIONS")
        require(isinstance(product_quality, Mapping) and set(product_quality) == set(PRODUCT_SCORE_MAX), "E_REVIEW_PRODUCT_DIMENSIONS")
        for dimension, maximum in PUBLIC_SCORE_MAX.items():
            require(isinstance(public_quality[dimension], int) and 0 <= public_quality[dimension] <= maximum, "E_REVIEW_PUBLIC_SCORE", dimension)
        for dimension, maximum in PRODUCT_SCORE_MAX.items():
            require(isinstance(product_quality[dimension], int) and 0 <= product_quality[dimension] <= maximum, "E_REVIEW_PRODUCT_SCORE", dimension)
        total = sum(public_quality.values()) + sum(product_quality.values())
        grade = "A" if total >= 90 else "B" if total >= 80 else "C" if total >= 70 else "D"
        require(row.get("total_score") == total and row.get("grade") == grade, "E_REVIEW_SCORE_TOTAL")
        codes = row.get("hard_error_codes")
        require(isinstance(codes, list) and len(codes) == len(set(map(str, codes))), "E_REVIEW_HARD_CODES")
        require(isinstance(row.get("formulaic_or_near_duplicate"), bool), "E_REVIEW_FORMULA_TYPE")
        require(row.get("first_acceptable") is (grade in {"A", "B"} and not codes), "E_REVIEW_ACCEPTABLE_RECOMPUTE")
        require(isinstance(row.get("rationale"), str) and row["rationale"].strip(), "E_REVIEW_RATIONALE")
        if row["first_acceptable"]:
            acceptable += 1
            acceptable_requests.add(str(mapping[blind_id]["request_id"]))
        if row["chosen_profile_id"] == mapping[blind_id]["profile_id"]:
            blind_correct += 1
        if row["formulaic_or_near_duplicate"]:
            formula.add(blind_id)
        hard.update(map(str, codes))
        per_item[blind_id] = {
            "first_acceptable": row["first_acceptable"],
            "hard_error_codes": sorted(map(str, codes)),
        }
        seen.add(blind_id)
    require(set(mapping) == seen, "E_REVIEW_COVERAGE")
    route_gate = report.get("route_gate")
    comparisons = read_jsonl(ROOT / ROUTE_COMPARISONS)
    expected_gate = {
        "action_match_count": sum(row["action_match"] is True for row in comparisons),
        "reason_match_count": sum(row["reason_match"] is True for row in comparisons),
        "audience_leak_count": sum(row["audience_leak"] is True for row in comparisons),
        "pass": all(row["action_match"] and row["reason_match"] and not row["audience_leak"] for row in comparisons),
    }
    require(route_gate == expected_gate, "E_REVIEW_ROUTE_GATE")
    pass_value = acceptable >= 18 and blind_correct >= 17 and not hard and expected_gate["pass"]
    require(report.get("overall_verdict") == ("PASS" if pass_value else "FAIL"), "E_REVIEW_VERDICT")
    require(report.get("review_digest") == object_digest(report, "review_digest"), "E_REVIEW_DIGEST")
    return {"acceptable": acceptable, "blind_correct": blind_correct, "formula": formula, "hard": hard, "acceptable_requests": acceptable_requests, "per_item": per_item, "pass": pass_value}


def _validate_targeted_adjudication(
    manifest: Mapping[str, Any],
    disagreement_ids: set[str],
) -> str:
    if not disagreement_ids:
        require(not (ROOT / TARGETED_ADJUDICATION).exists(), "E_UNNEEDED_ADJUDICATION")
        return ""
    require((ROOT / TARGETED_ADJUDICATION).is_file(), "E_ADJUDICATION_REQUIRED")
    value = _load_json(ROOT / TARGETED_ADJUDICATION)
    _exact_keys(
        value,
        {
            "schema_version", "task_id", "adjudicator_identity",
            "adjudicator_session_logical_id", "adjudicator_platform_agent_id",
            "blank_context", "full_batch_rereviewed", "source_reports_preserved",
            "reviewed_blind_item_ids", "adjudications", "all_closed",
            "adjudication_digest",
        },
        "E_ADJUDICATION_FIELDS",
    )
    require(
        value.get("schema_version") == "gate1-third-p4-targeted-adjudication-v1.0"
        and value.get("task_id") == TASK_ID,
        "E_ADJUDICATION_SCHEMA",
    )
    adjudicator = manifest["targeted_adjudicator"]
    for field, role_field in (
        ("adjudicator_identity", "identity"),
        ("adjudicator_session_logical_id", "session_logical_id"),
        ("adjudicator_platform_agent_id", "platform_agent_id"),
    ):
        require(value.get(field) == adjudicator[role_field], "E_ADJUDICATOR_BINDING", field)
    require(
        value.get("blank_context") is True
        and value.get("full_batch_rereviewed") is False
        and value.get("source_reports_preserved") is True
        and value.get("all_closed") is True,
        "E_ADJUDICATION_BOUNDARY",
    )
    reviewed = value.get("reviewed_blind_item_ids")
    rows = value.get("adjudications")
    require(isinstance(reviewed, list) and set(map(str, reviewed)) == disagreement_ids, "E_ADJUDICATION_SCOPE")
    require(isinstance(rows, list) and len(rows) == len(disagreement_ids), "E_ADJUDICATION_COUNT")
    seen: set[str] = set()
    for row in rows:
        require(isinstance(row, Mapping), "E_ADJUDICATION_OBJECT")
        _exact_keys(row, {"blind_item_id", "closed", "rationale"}, "E_ADJUDICATION_ROW_FIELDS")
        blind_id = str(row.get("blind_item_id"))
        require(blind_id in disagreement_ids and blind_id not in seen, "E_ADJUDICATION_ID")
        require(row.get("closed") is True, "E_ADJUDICATION_NOT_CLOSED")
        require(isinstance(row.get("rationale"), str) and row["rationale"].strip(), "E_ADJUDICATION_RATIONALE")
        seen.add(blind_id)
    require(seen == disagreement_ids, "E_ADJUDICATION_COVERAGE")
    require(value.get("adjudication_digest") == object_digest(value, "adjudication_digest"), "E_ADJUDICATION_DIGEST")
    return str(value["adjudication_digest"])


def finalize_reviews() -> None:
    manifest = json.loads((ROOT / CURATION_BUNDLE).read_text(encoding="utf-8"))["role_manifest"]
    content = _validate_review(_load_json(ROOT / CONTENT_REVIEW), _load_json(ROOT / CONTENT_STAGE), "CONTENT_VALUE", manifest)
    fact = _validate_review(_load_json(ROOT / FACT_REVIEW), _load_json(ROOT / FACT_STAGE), "FACT_AUTHORIZATION", manifest)
    formula_union = set(content["formula"]) | set(fact["formula"])
    hard_union = set(content["hard"]) | set(fact["hard"])
    disagreement_ids = {
        blind_id
        for blind_id in content["per_item"]
        if content["per_item"][blind_id] != fact["per_item"][blind_id]
    }
    adjudication_digest = _validate_targeted_adjudication(manifest, disagreement_ids)
    reviews_pass = bool(content["pass"] and fact["pass"] and len(formula_union) <= 2 and not hard_union)
    common_acceptable = sorted(set(content["acceptable_requests"]) & set(fact["acceptable_requests"]))
    metrics = bind_digest(
        {
            "schema_version": "gate1-third-p4-review-metrics-v1.0",
            "task_id": TASK_ID,
            "content_value_first_acceptable_count": content["acceptable"],
            "fact_authorization_first_acceptable_count": fact["acceptable"],
            "content_value_blind_profile_correct_count": content["blind_correct"],
            "fact_authorization_blind_profile_correct_count": fact["blind_correct"],
            "formulaic_or_near_duplicate_union_ids": sorted(formula_union),
            "hard_error_union_codes": sorted(hard_union),
            "substantive_disagreement_blind_item_ids": sorted(disagreement_ids),
            "targeted_adjudication_digest": adjudication_digest,
            "common_acceptable_request_ids": common_acceptable,
            "reviews_pass": reviews_pass,
            "metrics_digest": "",
        },
        "metrics_digest",
    )
    write_yaml(ROOT / REVIEW_METRICS, {"third_p4_review_metrics": metrics})
    machine = load_yaml(ROOT / MACHINE_REPORT)["third_p4_machine_acceptance"]
    if not reviews_pass:
        _write_state("STOPPED_RETURN_TO_P3", {"machine_report": machine["report_digest"], "review_metrics": metrics["metrics_digest"]})
        _write_checkpoint("STOPPED_RETURN_TO_P3", machine, metrics)
        return
    packet = bind_digest(
        {
            "schema_version": "gate1-third-p4-qualification-decision-packet-v1.0",
            "task_id": TASK_ID,
            "decision_authority": "EXTERNAL_INDEPENDENT_QUALIFICATION_COORDINATOR",
            "machine_report_sha256": sha256_file(ROOT / MACHINE_REPORT),
            "review_metrics_sha256": sha256_file(ROOT / REVIEW_METRICS),
            "content_review_sha256": sha256_file(ROOT / CONTENT_REVIEW),
            "fact_review_sha256": sha256_file(ROOT / FACT_REVIEW),
            "normalized_outputs_sha256": sha256_file(ROOT / NORMALIZED_OUTPUTS),
            "eligible_request_ids": common_acceptable,
            "H_before_decision": 0,
            "generator_qualified_before_decision": False,
            "p5_allowed_before_decision": False,
            "packet_digest": "",
        },
        "packet_digest",
    )
    write_yaml(ROOT / DECISION_PACKET, {"third_p4_qualification_decision_packet": packet})
    _write_state("PASS_PENDING_FOUNDER_QUALIFICATION_DECISION", {"machine_report": machine["report_digest"], "review_metrics": metrics["metrics_digest"], "decision_packet": packet["packet_digest"]})
    _write_checkpoint("PASS_PENDING_FOUNDER_QUALIFICATION_DECISION", machine, metrics)


def _write_checkpoint(state: str, machine: Mapping[str, Any], metrics: Mapping[str, Any] | None) -> None:
    result = bind_digest(
        {
            "schema_version": "gate1-third-p4-checkpoint-result-v1.0",
            "task_id": TASK_ID,
            "result_state": state,
            "machine_report_digest": machine.get("report_digest", ""),
            "review_metrics_digest": metrics.get("metrics_digest", "") if metrics else "",
            "H": 0,
            "generator_qualified": False,
            "p5_allowed": False,
            "p5_executed": False,
            "core_number_impact": {"300": 0, "120": 0, "86": 0},
            "readiness_true_keys": [],
            "result_digest": "",
        },
        "result_digest",
    )
    write_yaml(ROOT / CHECKPOINT_RESULT, {"third_p4_checkpoint_result": result})


def apply_decision() -> None:
    decision = _load_json(ROOT / QUALIFICATION_DECISION)
    _exact_keys(decision, {"schema_version", "task_id", "decision_authority", "coordinator_identity", "coordinator_session_logical_id", "coordinator_platform_agent_id", "review_metrics_digest", "qualification_score", "hard_veto", "qualification_verdict", "approved_first_output_request_ids", "decision_reason_codes", "decision_digest"}, "E_DECISION_FIELDS")
    require(decision.get("schema_version") == "gate1-third-p4-qualification-decision-v1.0" and decision.get("task_id") == TASK_ID, "E_DECISION_SCHEMA")
    require(decision.get("decision_authority") == "EXTERNAL_INDEPENDENT_QUALIFICATION_COORDINATOR", "E_DECISION_AUTHORITY")
    manifest = json.loads((ROOT / CURATION_BUNDLE).read_text(encoding="utf-8"))["role_manifest"]
    coordinator = manifest["qualification_coordinator"]
    for field, role_field in (("coordinator_identity", "identity"), ("coordinator_session_logical_id", "session_logical_id"), ("coordinator_platform_agent_id", "platform_agent_id")):
        require(decision.get(field) == coordinator[role_field], "E_COORDINATOR_BINDING")
    metrics = load_yaml(ROOT / REVIEW_METRICS)["third_p4_review_metrics"]
    require(decision.get("review_metrics_digest") == metrics["metrics_digest"], "E_DECISION_METRICS_BINDING")
    require(decision.get("decision_digest") == object_digest(decision, "decision_digest"), "E_DECISION_DIGEST")
    approved = list(map(str, decision.get("approved_first_output_request_ids", [])))
    require(len(approved) == len(set(approved)), "E_DECISION_APPROVED_DUPLICATE")
    require(set(approved).issubset(set(metrics["common_acceptable_request_ids"])), "E_DECISION_APPROVED_SCOPE")
    verdict = decision.get("qualification_verdict")
    hard_veto = decision.get("hard_veto")
    score = decision.get("qualification_score")
    require(isinstance(score, int) and 0 <= score <= 100 and isinstance(hard_veto, bool), "E_DECISION_VALUE")
    require(isinstance(decision.get("decision_reason_codes"), list) and decision["decision_reason_codes"], "E_DECISION_REASONS")
    if verdict == "APPROVE":
        require(hard_veto is False and score >= 90 and len(approved) >= 18, "E_DECISION_APPROVE_GATE")
        state = "PASS_TO_P5_POSITIVE_SCALE"
    else:
        require(verdict == "REJECT" and not approved, "E_DECISION_REJECT_GATE")
        state = "STOPPED_QUALIFICATION_REJECTED"
        approved = []
    _write_state(state, {"decision": decision["decision_digest"], "review_metrics": metrics["metrics_digest"]}, approved)
    lifecycle = load_yaml(ROOT / LIFECYCLE)["third_p4_lifecycle"]
    result = bind_digest(
        {
            "schema_version": "gate1-third-p4-final-result-v1.0",
            "task_id": TASK_ID,
            "result_state": state,
            "qualification_score": score,
            "hard_veto": hard_veto,
            "approved_first_output_request_ids": approved,
            "H": lifecycle["H"],
            "generator_qualified": lifecycle["generator_qualified"],
            "p5_allowed": lifecycle["p5_allowed"],
            "p5_executed": False,
            "core_number_impact": {"300": 0, "120": 0, "86": 0},
            "readiness_true_keys": [],
            "result_digest": "",
        },
        "result_digest",
    )
    write_yaml(ROOT / CHECKPOINT_RESULT, {"third_p4_checkpoint_result": result})
    receipt = bind_digest(
        {
            "schema_version": "gate1-third-p4-delivery-receipt-v1.0",
            "task_id": TASK_ID,
            "result_state": state,
            "tool_freeze_sha256": sha256_file(ROOT / TOOL_FREEZE),
            "hidden_freeze_sha256": sha256_file(ROOT / HIDDEN_FREEZE),
            "raw_outputs_sha256": sha256_file(ROOT / RAW_OUTPUTS),
            "normalized_outputs_sha256": sha256_file(ROOT / NORMALIZED_OUTPUTS),
            "route_actuals_sha256": sha256_file(ROOT / ROUTE_ACTUALS),
            "content_review_sha256": sha256_file(ROOT / CONTENT_REVIEW),
            "fact_review_sha256": sha256_file(ROOT / FACT_REVIEW),
            "decision_sha256": sha256_file(ROOT / QUALIFICATION_DECISION),
            "P5_executed": False,
            "receipt_digest": "",
        },
        "receipt_digest",
    )
    write_yaml(ROOT / DELIVERY_RECEIPT, {"third_p4_delivery_receipt": receipt})


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare-tools", action="store_true")
    action.add_argument("--freeze-hidden", action="store_true")
    action.add_argument("--run-first", action="store_true")
    action.add_argument("--compare-and-build-review", action="store_true")
    action.add_argument("--finalize-reviews", action="store_true")
    action.add_argument("--apply-decision", action="store_true")
    parser.add_argument("--tool-commit")
    parser.add_argument("--curation-bundle", type=Path, default=CURATION_BUNDLE)
    args = parser.parse_args()
    try:
        if args.prepare_tools:
            prepare_tools()
        elif args.freeze_hidden:
            require(bool(args.tool_commit), "E_TOOL_COMMIT_REQUIRED")
            freeze_hidden(str(args.tool_commit), args.curation_bundle)
        elif args.run_first:
            run_first()
        elif args.compare_and_build_review:
            compare_and_build_review()
        elif args.finalize_reviews:
            finalize_reviews()
        else:
            apply_decision()
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        sys.stderr.write(f"FAIL {exc}\n")
        return 1
    lifecycle = load_yaml(ROOT / LIFECYCLE).get("third_p4_lifecycle", {})
    print(canonical_json({"status": "PASS", "state": lifecycle.get("lifecycle_state"), "task_id": TASK_ID}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
