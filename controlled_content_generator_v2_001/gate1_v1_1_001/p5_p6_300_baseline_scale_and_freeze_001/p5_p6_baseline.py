#!/usr/bin/env python3
"""Recoverable Gate 1 v1.1 240+60 quality-baseline materializer."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("p5_p6_baseline refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_300_BASELINE_SCALE_AND_INDEPENDENT_FREEZE_001"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p5_p6_300_baseline_scale_and_freeze_001"
)
P4_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_third_sealed_hidden_probe40_001"
)
P4_SUCCESSOR = P4_ROOT / "review_successor"
P1B_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001"
)
P2_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
P3_ROUTE_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p3_route_input_compiler_recovery_001"
)
AUTHOR_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_author_output_contract_recovery_001"
)
LEGACY_ROUTE_ROOT = Path(
    "controlled_content_generator_v2_001/"
    "creative_authoring_route_oracle_convergence_001"
)
REFERENCE_CORPUS = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)

CONTRACT = TASK_ROOT / "contract/baseline_contract.v1.0.yaml"
P4_DECISION = P4_SUCCESSOR / "qualification_decision.v1.0.json"
P4_MAPPING = P4_SUCCESSOR / "neutral_blind_mapping.v1.0.jsonl"
P4_OUTPUTS = P4_ROOT / "run/positive_20_first_outputs.v1.0.jsonl"
P4_REQUESTS = P4_ROOT / "freeze/positive_author_requests_20.v1.0.jsonl"
DISPOSITIONS = P1B_ROOT / "content/reference_120_final_dispositions.v0.1.jsonl"
ROUTE_GOLD = P1B_ROOT / "route/route_60_gold_answers.v0.1.jsonl"
LEGACY_ROUTE_INPUTS = LEGACY_ROUTE_ROOT / "route/route_inputs.v0.1.jsonl"
ROUTE_MODULE_PATH = P3_ROUTE_ROOT / "route_contract.py"
AUTHOR_MODULE_PATH = AUTHOR_ROOT / "author_contract.py"

ACTIVE_COMPONENTS = P2_ROOT / "component/active_gate1_components.v0.1.jsonl"
ACTIVE_RULES = P2_ROOT / "component/active_control_rules.v0.1.jsonl"
ACTIVE_EDGES = P2_ROOT / "component/active_gate1_edges.v0.1.jsonl"
ACTIVE_AB_PATHS = P2_ROOT / "ab/active_ab_structural_paths.v0.1.jsonl"
GENERATOR_CORE = P2_ROOT / "p2_generator_core_r6.py"
GENERATOR_REGISTRY = P2_ROOT / "generator/active_gate1_generator_registry.v0.1.yaml"
AUTHOR_INSTRUCTION = AUTHOR_ROOT / "contract/controlled_author_instruction.v1.0.md"
AUTHOR_CONTRACT = AUTHOR_ROOT / "contract/author_semantic_output_contract.v1.0.json"

REFERENCE_APPROVED = TASK_ROOT / "production/reference_approved.v1.0.jsonl"
P4_APPROVED = TASK_ROOT / "production/p4_approved.v1.0.jsonl"
ALLOCATION = TASK_ROOT / "production/allocation.v1.0.jsonl"
CURATION_GLOB = "production/curation/scenarios.*.jsonl"
AUTHOR_ROLE_MANIFEST = TASK_ROOT / "production/author_role_manifest.v1.0.json"
AUTHOR_REQUESTS = TASK_ROOT / "production/author_requests.v1.0.jsonl"
PRODUCTION_FREEZE = TASK_ROOT / "freeze/production_basis_manifest.v1.0.yaml"
RAW_OUTPUT_GLOB = "production/author_raw/raw.*.jsonl"
FIRST_OUTPUTS = TASK_ROOT / "production/positive_first_outputs.v1.0.jsonl"
OUTPUT_FREEZE = TASK_ROOT / "freeze/positive_first_output_freeze.v1.0.yaml"

ROUTE_INPUTS = TASK_ROOT / "route/route_inputs.v1.0.jsonl"
ROUTE_COMPILED = TASK_ROOT / "route/route_compiled.v1.0.jsonl"
ROUTE_ACTUALS = TASK_ROOT / "route/route_actuals.v1.0.jsonl"
ROUTE_ACTUAL_FREEZE = TASK_ROOT / "freeze/route_actual_freeze.v1.0.yaml"
ROUTE_COMPARISONS = TASK_ROOT / "route/route_comparisons.v1.0.jsonl"
ROUTE_RESULT = TASK_ROOT / "route/route_result.v1.0.yaml"

PROFILE_RE = re.compile(r"^CP(?:0[1-9]|1\d|20)$")
SCENARIO_ID_RE = re.compile(r"^P5-CUR-CP(?:0[1-9]|1\d|20)-\d{3}$")
PROFILE_IDS = tuple(f"CP{number:02d}" for number in range(1, 21))
MODEL_CAPABILITY = "gpt-5.6-sol"
REASONING_EFFORT = "high"
SERVICE_TIER = "priority"


class BaselineError(ValueError):
    """Stable fail-closed pipeline error."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise BaselineError(f"{code}{suffix}")


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
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), "E_JSONL_OBJECT", f"{path}:{number}")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(canonical_json(row) for row in rows) + "\n"
    path.write_text(payload, encoding="utf-8")


def read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "E_YAML_OBJECT", path.as_posix())
    return value


def write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    require(spec is not None and spec.loader is not None, "E_IMPORT_SPEC", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def approved_reference_rows() -> list[dict[str, Any]]:
    dispositions = read_jsonl(ROOT / DISPOSITIONS)
    source_by_id = {
        str(row["asset_id"]): row for row in read_jsonl(ROOT / REFERENCE_CORPUS)
    }
    selected = [
        row
        for row in dispositions
        if row.get("final_disposition") == "COUNT_TOWARD_FINAL_300_POSITIVE"
    ]
    require(len(dispositions) == 120, "E_REFERENCE_DISPOSITION_COUNT")
    require(len(selected) == 29, "E_REFERENCE_APPROVED_RECOMPUTE")
    result: list[dict[str, Any]] = []
    for row in selected:
        asset_id = str(row["asset_id"])
        source = source_by_id.get(asset_id)
        require(source is not None, "E_REFERENCE_SOURCE", asset_id)
        require(
            row.get("source_record_sha256") == digest_object(source),
            "E_REFERENCE_SOURCE_DIGEST",
            asset_id,
        )
        result.append(
            {
                "baseline_item_id": f"G1V11-REF-{asset_id}",
                "source_asset_id": asset_id,
                "profile_id": row["final_content_product_id"],
                "body_text": source["body_text"],
                "historical_generation_version": source.get("generation_mode"),
                "historical_source_record_sha256": row["source_record_sha256"],
                "approval_source": "P1B_SIGNED_MECHANICAL_DISPOSITION",
                "first_acceptable": True,
                "reclassified_as_current_generation": False,
                "publishable": False,
                "runtime_consumable": False,
            }
        )
    return sorted(result, key=lambda item: str(item["baseline_item_id"]))


def approved_p4_rows() -> list[dict[str, Any]]:
    require((ROOT / P4_DECISION).is_file(), "E_P4_DECISION_MISSING")
    decision = json.loads((ROOT / P4_DECISION).read_text(encoding="utf-8"))
    require(isinstance(decision, dict), "E_P4_DECISION_OBJECT")
    require(decision.get("qualification_verdict") in {"APPROVE", "REJECT"}, "E_P4_DECISION")
    if decision["qualification_verdict"] == "REJECT":
        require(decision.get("approved_first_output_request_ids") == [], "E_P4_REJECT_APPROVED")
        return []
    require(decision.get("hard_veto") is False, "E_P4_HARD_VETO")
    approved = set(map(str, decision.get("approved_first_output_request_ids", [])))
    outputs = {str(row["request_id"]): row for row in read_jsonl(ROOT / P4_OUTPUTS)}
    mapping = {str(row["request_id"]): row for row in read_jsonl(ROOT / P4_MAPPING)}
    require(approved.issubset(outputs) and approved.issubset(mapping), "E_P4_APPROVED_REF")
    result = []
    for request_id in sorted(approved):
        output = outputs[request_id]
        result.append(
            {
                "baseline_item_id": f"G1V11-H-{request_id}",
                "request_id": request_id,
                "profile_id": output["profile_id"],
                "title": output["title"],
                "body": output["body"],
                "output_digest": output["output_digest"],
                "approval_source": "P4_INDEPENDENT_QUALIFICATION_DECISION",
                "first_acceptable": True,
                "original_first_output_unchanged": True,
                "publishable": False,
                "runtime_consumable": False,
            }
        )
    return result


def build_allocation(
    references: Sequence[Mapping[str, Any]],
    p4_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    existing = Counter(str(row["profile_id"]) for row in [*references, *p4_rows])
    require(set(existing).issubset(PROFILE_IDS), "E_ALLOCATION_PROFILE")
    rows = []
    for profile_id in PROFILE_IDS:
        count = existing[profile_id]
        require(0 <= count <= 12, "E_ALLOCATION_EXISTING", profile_id)
        rows.append(
            {
                "profile_id": profile_id,
                "approved_reference_count": sum(
                    row["profile_id"] == profile_id for row in references
                ),
                "approved_p4_count": sum(
                    row["profile_id"] == profile_id for row in p4_rows
                ),
                "initial_new_candidate_count": 12 - count,
                "approved_positive_target": 12,
            }
        )
    require(sum(row["initial_new_candidate_count"] for row in rows) == 240 - len(references) - len(p4_rows), "E_ALLOCATION_TOTAL")
    return rows


def _normalized_route_record(
    old: Mapping[str, Any], route: ModuleType
) -> dict[str, Any]:
    profile = route.profile_by_id(ROOT)[str(old["profile_id"])]
    required = route.required_slots(profile)
    payload = old.get("actual_input_payload")
    require(isinstance(payload, Mapping), "E_LEGACY_ROUTE_PAYLOAD")
    present = {
        slot_class: sorted(map(str, payload[f"present_{slot_class}_slots"]))
        for slot_class in ("source", "fact", "authorization")
    }
    missing = {
        slot_class: sorted(set(required[slot_class]) - set(present[slot_class]))
        for slot_class in present
    }
    allowed_risks = route.allowed_risk_codes(ROOT)
    risks: set[str] = set()
    guards = set(map(str, payload.get("hard_guard_hits", [])))
    for raw_risk in map(str, payload.get("risk_points", [])):
        if raw_risk in allowed_risks:
            risks.add(raw_risk)
        elif raw_risk.startswith("hard_guard:AGR_"):
            guards.add(raw_risk.split(":", 1)[1])
        elif raw_risk.startswith("AGR_"):
            guards.add(raw_risk)
        else:
            raise BaselineError(f"E_LEGACY_RISK_UNKNOWN:{raw_risk}")
    case_id = str(old["case_id"])
    provided: dict[str, list[dict[str, str]]] = {}
    for slot_class, slot_ids in present.items():
        provided[slot_class] = []
        for slot_id in slot_ids:
            value_ref = f"{case_id}#{slot_class}:{slot_id}"
            provided[slot_class].append(
                {
                    "slot_id": slot_id,
                    "value_ref": value_ref,
                    "value_digest": sha256_bytes(value_ref.encode("utf-8")),
                }
            )
    partial_safe = payload.get("partial_safe") is True
    record: dict[str, Any] = {
        "schema_version": route.CONTRACT_VERSION,
        "task_id": route.TASK_ID,
        "case_id": case_id,
        "profile_id": old["profile_id"],
        "provided": provided,
        "missing": missing,
        "risk_codes": sorted(risks),
        "hard_guard_hits": sorted(guards),
        "degrade_request": {
            "enabled": partial_safe,
            "artifact_type": str(payload.get("requested_degraded_output", "")) if partial_safe else "",
            "payload": dict(payload.get("partial_artifact_payload", {})) if partial_safe else {},
        },
        "provenance": {
            "source_kind": "SYNTHETIC_OPEN_DEVELOPMENT",
            "record_refs": [
                f"{LEGACY_ROUTE_INPUTS.as_posix()}#{case_id}",
            ],
        },
    }
    record["input_digest"] = route.object_digest(record, "input_digest")
    return record


def prepare_routes() -> None:
    require(not (ROOT / ROUTE_ACTUALS).exists(), "E_ROUTE_ACTUAL_ALREADY_FROZEN")
    route = load_module(ROUTE_MODULE_PATH, "gate1_p5_route_contract")
    legacy = read_jsonl(ROOT / LEGACY_ROUTE_INPUTS)
    require(len(legacy) == 60, "E_ROUTE_INPUT_COUNT")
    inputs = [_normalized_route_record(row, route) for row in legacy]
    compiled = [route.compile_route_input(row, ROOT) for row in inputs]
    actuals = [route.evaluate_compiled_route(row, ROOT) for row in compiled]
    require(len(actuals) == 60, "E_ROUTE_ACTUAL_COUNT")
    write_jsonl(ROOT / ROUTE_INPUTS, inputs)
    write_jsonl(ROOT / ROUTE_COMPILED, compiled)
    write_jsonl(ROOT / ROUTE_ACTUALS, actuals)
    freeze = {
        "schema_version": "gate1-v1.1-route-60-actual-freeze-v1.0",
        "task_id": TASK_ID,
        "input_count": 60,
        "compiled_count": 60,
        "actual_count": 60,
        "route_contract_path": ROUTE_MODULE_PATH.as_posix(),
        "route_contract_sha256": sha256_file(ROOT / ROUTE_MODULE_PATH),
        "route_inputs_sha256": sha256_file(ROOT / ROUTE_INPUTS),
        "route_compiled_sha256": sha256_file(ROOT / ROUTE_COMPILED),
        "route_actuals_sha256": sha256_file(ROOT / ROUTE_ACTUALS),
        "gold_answer_loaded_by_actual_runner": False,
        "actuals_frozen_before_gold_comparison": True,
        "audience_content_created_count": sum(
            any(
                row.get(field)
                for field in (
                    "audience_title_created",
                    "audience_body_created",
                    "spoken_script_created",
                )
            )
            for row in actuals
        ),
    }
    freeze["freeze_digest"] = object_digest(freeze, "freeze_digest")
    write_yaml(ROOT / ROUTE_ACTUAL_FREEZE, freeze)


def compare_routes() -> None:
    freeze = read_yaml(ROOT / ROUTE_ACTUAL_FREEZE)
    require(freeze.get("route_actuals_sha256") == sha256_file(ROOT / ROUTE_ACTUALS), "E_ROUTE_ACTUAL_DRIFT")
    actuals = {str(row["case_id"]): row for row in read_jsonl(ROOT / ROUTE_ACTUALS)}
    gold = {str(row["case_id"]): row for row in read_jsonl(ROOT / ROUTE_GOLD)}
    require(len(actuals) == len(gold) == 60 and set(actuals) == set(gold), "E_ROUTE_GOLD_COVERAGE")
    comparisons = []
    for case_id in sorted(actuals):
        actual = actuals[case_id]
        expected = gold[case_id]
        comparisons.append(
            {
                "case_id": case_id,
                "profile_id": actual["profile_id"],
                "actual_primary_action": actual["actual_primary_action"],
                "actual_primary_reason_category": actual["actual_primary_reason_category"],
                "gold_primary_action": expected["gold_primary_action"],
                "gold_primary_reason_category": expected["gold_reason_code"],
                "primary_action_matches_gold": actual["actual_primary_action"] == expected["gold_primary_action"],
                "primary_reason_matches_gold": actual["actual_primary_reason_category"] == expected["gold_reason_code"],
                "audience_content_created": any(
                    actual.get(field)
                    for field in (
                        "audience_title_created",
                        "audience_body_created",
                        "spoken_script_created",
                    )
                ),
            }
        )
    write_jsonl(ROOT / ROUTE_COMPARISONS, comparisons)
    result = {
        "schema_version": "gate1-v1.1-route-60-result-v1.0",
        "task_id": TASK_ID,
        "action_match_count": sum(row["primary_action_matches_gold"] for row in comparisons),
        "reason_match_count": sum(row["primary_reason_matches_gold"] for row in comparisons),
        "audience_content_created_count": sum(row["audience_content_created"] for row in comparisons),
        "actuals_sha256": sha256_file(ROOT / ROUTE_ACTUALS),
        "gold_sha256": sha256_file(ROOT / ROUTE_GOLD),
        "comparison_sha256": sha256_file(ROOT / ROUTE_COMPARISONS),
    }
    result["pass"] = (
        result["action_match_count"] == 60
        and result["reason_match_count"] == 60
        and result["audience_content_created_count"] == 0
    )
    require(result["pass"], "E_ROUTE_60_GATE")
    result["result_digest"] = object_digest(result, "result_digest")
    write_yaml(ROOT / ROUTE_RESULT, result)


def _validate_scenario(row: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "scenario_id",
        "profile_id",
        "scenario_label",
        "core_fact",
        "object_truth",
        "claim_boundary",
        "role_truth",
        "user_goal",
        "assigned_variant",
        "lane_id",
        "source_summary_a",
        "source_summary_b",
        "authorization_scope",
        "curator_identity",
        "curator_session_logical_id",
        "curator_platform_agent_id",
        "synthetic_test_only",
        "scenario_digest",
    }
    require(set(row) == required, "E_SCENARIO_FIELDS")
    require(row.get("schema_version") == "gate1-v1.1-curated-scenario-v1.0", "E_SCENARIO_SCHEMA")
    require(isinstance(row.get("scenario_id"), str) and SCENARIO_ID_RE.fullmatch(str(row["scenario_id"])) is not None, "E_SCENARIO_ID")
    require(isinstance(row.get("profile_id"), str) and PROFILE_RE.fullmatch(str(row["profile_id"])) is not None, "E_SCENARIO_PROFILE")
    require(str(row["scenario_id"])[7:11] == row["profile_id"], "E_SCENARIO_ID_PROFILE")
    for key in (
        "scenario_label",
        "core_fact",
        "object_truth",
        "claim_boundary",
        "user_goal",
        "source_summary_a",
        "source_summary_b",
        "authorization_scope",
        "curator_identity",
        "curator_session_logical_id",
        "curator_platform_agent_id",
    ):
        require(isinstance(row.get(key), str) and bool(str(row[key]).strip()), "E_SCENARIO_TEXT", key)
    require(isinstance(row.get("role_truth"), str), "E_SCENARIO_ROLE_TRUTH")
    require(row.get("assigned_variant") in {"A1", "A2", "B1", "B2"}, "E_SCENARIO_VARIANT")
    require(row.get("lane_id") in {"A", "B"}, "E_SCENARIO_LANE")
    require(str(row["assigned_variant"]).startswith(str(row["lane_id"])), "E_SCENARIO_LANE_VARIANT")
    require(row.get("synthetic_test_only") is True, "E_SCENARIO_NAMESPACE")
    require(row.get("scenario_digest") == object_digest(row, "scenario_digest"), "E_SCENARIO_DIGEST")


def _request_from_scenario(
    scenario: Mapping[str, Any],
    template: Mapping[str, Any],
    author: Mapping[str, Any],
    run_order: int,
) -> dict[str, Any]:
    profile_id = str(scenario["profile_id"])
    suffix = str(scenario["scenario_id"]).rsplit("-", 1)[1]
    prefix = f"G1V11-P5-{profile_id}-{suffix}"
    source_ids = [f"{prefix}-SRC-01", f"{prefix}-SRC-02"]
    authorization_id = f"{prefix}-AUTH-01"
    template_facts = template["typed_material"]["facts"]
    value_by_slot = {
        f"{profile_id.lower()}_core_input_signature": scenario["core_fact"],
        "real_event_or_object_truth": scenario["object_truth"],
        "claim_boundary": scenario["claim_boundary"],
        "real_role_or_person_truth": scenario["role_truth"],
    }
    facts = []
    for index, old_fact in enumerate(template_facts, 1):
        slot_id = str(old_fact["slot_id"])
        require(slot_id in value_by_slot, "E_SCENARIO_SLOT_UNSUPPORTED", f"{profile_id}:{slot_id}")
        value = str(value_by_slot[slot_id])
        require(bool(value.strip()), "E_SCENARIO_SLOT_VALUE", f"{profile_id}:{slot_id}")
        facts.append(
            {
                "authorization_ids": [authorization_id],
                "claim_boundary": scenario["claim_boundary"],
                "fact_id": f"{prefix}-FACT-{index:02d}",
                "fact_value": value,
                "fact_value_digest": sha256_bytes(value.encode("utf-8")),
                "slot_id": slot_id,
                "source_ids": source_ids,
                "synthetic_test_only": True,
            }
        )
    request = copy.deepcopy(dict(template))
    request.update(
        {
            "schema_version": "gate1-v1.1-p5-author-request-v1.0",
            "task_id": TASK_ID,
            "request_id": f"G1V11-P5-POS-{profile_id}-{suffix}",
            "profile_id": profile_id,
            "assigned_variant": scenario["assigned_variant"],
            "run_order": run_order,
            "author_identity": author["author_identity"],
            "author_session_logical_id": author["author_session_logical_id"],
            "author_platform_agent_id": author["author_platform_agent_id"],
            "model_capability_id": MODEL_CAPABILITY,
            "reasoning_effort": REASONING_EFFORT,
            "service_tier": SERVICE_TIER,
            "typed_material": {
                "sources": [
                    {
                        "slot_id": "usable_source_materials",
                        "source_id": source_ids[0],
                        "source_summary": scenario["source_summary_a"],
                        "synthetic_test_only": True,
                    },
                    {
                        "slot_id": "product_or_scene_reference",
                        "source_id": source_ids[1],
                        "source_summary": scenario["source_summary_b"],
                        "synthetic_test_only": True,
                    },
                ],
                "facts": facts,
                "authorizations": [
                    {
                        "authorization_id": authorization_id,
                        "scope_summary": scenario["authorization_scope"],
                        "slot_id": "publication_scope_authorization",
                        "synthetic_test_only": True,
                    }
                ],
                "claim_boundary": scenario["claim_boundary"],
            },
            "product_core_requirements": [
                {
                    "requirement_id": f"{prefix}-CORE-{index:02d}",
                    "fact_ids": [fact["fact_id"]],
                }
                for index, fact in enumerate(facts, 1)
            ],
            "user_goal": scenario["user_goal"],
            "synthetic_qualification_only": True,
            "publishable": False,
            "runtime_consumable": False,
            "counts_toward_300": False,
            "counts_toward_H": False,
        }
    )
    request["request_digest"] = object_digest(request, "request_digest")
    return request


def prepare_production() -> None:
    require(not (ROOT / FIRST_OUTPUTS).exists(), "E_PRODUCTION_OUTPUT_ALREADY_EXISTS")
    references = approved_reference_rows()
    p4_rows = approved_p4_rows()
    allocation = build_allocation(references, p4_rows)
    scenario_paths = sorted((ROOT / TASK_ROOT).glob(CURATION_GLOB.split("production/", 1)[1]))
    scenarios = [row for path in scenario_paths for row in read_jsonl(path)]
    for scenario in scenarios:
        _validate_scenario(scenario)
    expected = sum(row["initial_new_candidate_count"] for row in allocation)
    require(len(scenarios) == expected, "E_SCENARIO_COUNT", f"{len(scenarios)}!={expected}")
    scenario_ids = [str(row["scenario_id"]) for row in scenarios]
    require(len(scenario_ids) == len(set(scenario_ids)), "E_SCENARIO_ID_DUPLICATE")
    expected_by_profile = {
        str(row["profile_id"]): int(row["initial_new_candidate_count"])
        for row in allocation
    }
    require(Counter(str(row["profile_id"]) for row in scenarios) == Counter(expected_by_profile), "E_SCENARIO_PROFILE_COUNTS")
    role_manifest = json.loads((ROOT / AUTHOR_ROLE_MANIFEST).read_text(encoding="utf-8"))
    require(isinstance(role_manifest, dict), "E_AUTHOR_ROLE_MANIFEST")
    authors = role_manifest.get("authors")
    require(isinstance(authors, list) and authors, "E_AUTHOR_ROLES")
    author_by_profile: dict[str, dict[str, Any]] = {}
    for author in authors:
        require(isinstance(author, dict), "E_AUTHOR_ROLE_OBJECT")
        require(author.get("model_capability_id") == MODEL_CAPABILITY, "E_AUTHOR_MODEL")
        require(author.get("reasoning_effort") == REASONING_EFFORT, "E_AUTHOR_REASONING")
        require(author.get("service_tier") == SERVICE_TIER, "E_AUTHOR_SERVICE")
        require(author.get("may_review_or_freeze") is False, "E_AUTHOR_REVIEW_BOUNDARY")
        for profile_id in author.get("assigned_profile_ids", []):
            require(profile_id not in author_by_profile, "E_AUTHOR_PROFILE_DUPLICATE", str(profile_id))
            author_by_profile[str(profile_id)] = dict(author)
    require(set(author_by_profile) == set(PROFILE_IDS), "E_AUTHOR_PROFILE_COVERAGE")
    templates = {str(row["profile_id"]): row for row in read_jsonl(ROOT / P4_REQUESTS)}
    require(set(templates) == set(PROFILE_IDS), "E_TEMPLATE_PROFILE_COVERAGE")
    scenarios = sorted(scenarios, key=lambda item: (str(item["profile_id"]), str(item["scenario_id"])))
    requests = [
        _request_from_scenario(
            scenario,
            templates[str(scenario["profile_id"])],
            author_by_profile[str(scenario["profile_id"])],
            index,
        )
        for index, scenario in enumerate(scenarios, 1)
    ]
    author_contract = load_module(AUTHOR_MODULE_PATH, "gate1_p5_author_contract")
    author_contract.TASK_ID = TASK_ID
    for request in requests:
        author_contract.validate_request(request)
    write_jsonl(ROOT / REFERENCE_APPROVED, references)
    write_jsonl(ROOT / P4_APPROVED, p4_rows)
    write_jsonl(ROOT / ALLOCATION, allocation)
    write_jsonl(ROOT / AUTHOR_REQUESTS, requests)
    basis_paths = {
        "active_components": ACTIVE_COMPONENTS,
        "active_control_rules": ACTIVE_RULES,
        "active_component_profile_edges": ACTIVE_EDGES,
        "active_ab_structural_paths": ACTIVE_AB_PATHS,
        "generator_core": GENERATOR_CORE,
        "generator_registry": GENERATOR_REGISTRY,
        "author_instruction": AUTHOR_INSTRUCTION,
        "author_output_contract": AUTHOR_CONTRACT,
        "route_input_compiler": ROUTE_MODULE_PATH,
        "baseline_contract": CONTRACT,
        "author_role_manifest": AUTHOR_ROLE_MANIFEST,
        "curated_scenarios": scenario_paths[0] if len(scenario_paths) == 1 else None,
    }
    hashes = {
        name: sha256_file(ROOT / path)
        for name, path in basis_paths.items()
        if path is not None
    }
    if len(scenario_paths) > 1:
        hashes["curated_scenarios"] = digest_object(
            {path.as_posix(): sha256_file(path) for path in scenario_paths}
        )
    freeze = {
        "schema_version": "gate1-v1.1-production-basis-freeze-v1.0",
        "task_id": TASK_ID,
        "model_capability_id": MODEL_CAPABILITY,
        "reasoning_effort": REASONING_EFFORT,
        "service_tier": SERVICE_TIER,
        "external_provider_allowed": False,
        "approved_reference_count": len(references),
        "approved_p4_count": len(p4_rows),
        "initial_new_candidate_count": len(requests),
        "component_count": len(read_jsonl(ROOT / ACTIVE_COMPONENTS)),
        "control_rule_count": len(read_jsonl(ROOT / ACTIVE_RULES)),
        "component_profile_edge_count": len(read_jsonl(ROOT / ACTIVE_EDGES)),
        "basis_sha256": hashes,
        "reference_approved_sha256": sha256_file(ROOT / REFERENCE_APPROVED),
        "p4_approved_sha256": sha256_file(ROOT / P4_APPROVED),
        "allocation_sha256": sha256_file(ROOT / ALLOCATION),
        "author_requests_sha256": sha256_file(ROOT / AUTHOR_REQUESTS),
        "semantic_candidate_created": False,
        "readiness_changed": False,
    }
    require(freeze["component_count"] == 68, "E_COMPONENT_COUNT")
    require(freeze["control_rule_count"] == 8, "E_CONTROL_RULE_COUNT")
    require(freeze["component_profile_edge_count"] == 85, "E_EDGE_COUNT")
    freeze["freeze_digest"] = object_digest(freeze, "freeze_digest")
    write_yaml(ROOT / PRODUCTION_FREEZE, freeze)


def serialize_author_outputs() -> None:
    freeze = read_yaml(ROOT / PRODUCTION_FREEZE)
    require(freeze.get("author_requests_sha256") == sha256_file(ROOT / AUTHOR_REQUESTS), "E_AUTHOR_REQUEST_DRIFT")
    requests = read_jsonl(ROOT / AUTHOR_REQUESTS)
    raw_paths = sorted((ROOT / TASK_ROOT).glob(RAW_OUTPUT_GLOB.split("production/", 1)[1]))
    raws = [row for path in raw_paths for row in read_jsonl(path)]
    require(len(raws) == len(requests), "E_RAW_OUTPUT_COUNT")
    request_by_id = {str(row["request_id"]): row for row in requests}
    require(len(request_by_id) == len(requests), "E_REQUEST_ID_DUPLICATE")
    author_contract = load_module(AUTHOR_MODULE_PATH, "gate1_p5_author_serializer")
    author_contract.TASK_ID = TASK_ID
    strict = author_contract.frozen_strict_module()
    strict.TASK_ID = TASK_ID
    outputs = []
    seen_request_ids: set[str] = set()
    seen_run_ids: set[str] = set()
    for raw in raws:
        request_id = str(raw.get("request_id"))
        require(request_id in request_by_id, "E_RAW_REQUEST_UNKNOWN", request_id)
        require(request_id not in seen_request_ids, "E_RAW_REQUEST_DUPLICATE", request_id)
        run_id = str(raw.get("run_id"))
        require(run_id not in seen_run_ids, "E_RAW_RUN_ID_DUPLICATE", run_id)
        output = author_contract.serialize(raw, request_by_id[request_id])
        strict.validate_positive_output(output, request_by_id[request_id])
        outputs.append(output)
        seen_request_ids.add(request_id)
        seen_run_ids.add(run_id)
    require(seen_request_ids == set(request_by_id), "E_RAW_REQUEST_COVERAGE")
    outputs.sort(key=lambda row: int(row["run_order"]))
    write_jsonl(ROOT / FIRST_OUTPUTS, outputs)
    output_freeze = {
        "schema_version": "gate1-v1.1-positive-first-output-freeze-v1.0",
        "task_id": TASK_ID,
        "request_count": len(requests),
        "first_semantic_output_count": len(outputs),
        "second_candidate_count": 0,
        "replacement_count": 0,
        "author_requests_sha256": sha256_file(ROOT / AUTHOR_REQUESTS),
        "raw_output_set_digest": digest_object(
            {path.as_posix(): sha256_file(path) for path in raw_paths}
        ),
        "first_outputs_sha256": sha256_file(ROOT / FIRST_OUTPUTS),
        "production_basis_freeze_sha256": sha256_file(ROOT / PRODUCTION_FREEZE),
        "counts_toward_300_before_review": 0,
        "publishable_count": 0,
        "runtime_consumable_count": 0,
    }
    output_freeze["freeze_digest"] = object_digest(output_freeze, "freeze_digest")
    write_yaml(ROOT / OUTPUT_FREEZE, output_freeze)


def check() -> None:
    contract = read_yaml(ROOT / CONTRACT)
    require(contract.get("task_id") == TASK_ID, "E_CONTRACT_TASK")
    require(len(read_jsonl(ROOT / ACTIVE_COMPONENTS)) == 68, "E_COMPONENT_COUNT")
    require(len(read_jsonl(ROOT / ACTIVE_RULES)) == 8, "E_CONTROL_RULE_COUNT")
    require(len(read_jsonl(ROOT / ACTIVE_EDGES)) == 85, "E_EDGE_COUNT")
    if (ROOT / ROUTE_ACTUAL_FREEZE).exists():
        freeze = read_yaml(ROOT / ROUTE_ACTUAL_FREEZE)
        require(freeze.get("route_actuals_sha256") == sha256_file(ROOT / ROUTE_ACTUALS), "E_ROUTE_ACTUAL_DRIFT")
        require(freeze.get("gold_answer_loaded_by_actual_runner") is False, "E_ROUTE_GOLD_LEAK")
    if (ROOT / ROUTE_RESULT).exists():
        result = read_yaml(ROOT / ROUTE_RESULT)
        require(result.get("pass") is True, "E_ROUTE_RESULT")
        require(result.get("action_match_count") == 60, "E_ROUTE_ACTION_COUNT")
        require(result.get("reason_match_count") == 60, "E_ROUTE_REASON_COUNT")
    if (ROOT / PRODUCTION_FREEZE).exists():
        freeze = read_yaml(ROOT / PRODUCTION_FREEZE)
        require(freeze.get("component_count") == 68, "E_COMPONENT_COUNT")
        require(freeze.get("control_rule_count") == 8, "E_CONTROL_RULE_COUNT")
        require(freeze.get("component_profile_edge_count") == 85, "E_EDGE_COUNT")
        require(freeze.get("author_requests_sha256") == sha256_file(ROOT / AUTHOR_REQUESTS), "E_AUTHOR_REQUEST_DRIFT")
        require(len(approved_reference_rows()) == 29, "E_REFERENCE_APPROVED_RECOMPUTE")
    if (ROOT / OUTPUT_FREEZE).exists():
        freeze = read_yaml(ROOT / OUTPUT_FREEZE)
        require(freeze.get("first_outputs_sha256") == sha256_file(ROOT / FIRST_OUTPUTS), "E_OUTPUT_DRIFT")
        require(freeze.get("second_candidate_count") == 0, "E_SECOND_CANDIDATE")
        require(freeze.get("replacement_count") == 0, "E_REPLACEMENT")
    print("GATE1_V11_300_BASELINE_CHECK: PASS")


def selftest() -> None:
    example = {
        "schema_version": "gate1-v1.1-curated-scenario-v1.0",
        "scenario_id": "P5-CUR-CP01-001",
        "profile_id": "CP01",
        "scenario_label": "example",
        "core_fact": "example core fact",
        "object_truth": "example object truth",
        "claim_boundary": "example boundary",
        "role_truth": "example role",
        "user_goal": "example goal",
        "assigned_variant": "A1",
        "lane_id": "A",
        "source_summary_a": "example source a",
        "source_summary_b": "example source b",
        "authorization_scope": "example authorization",
        "curator_identity": "CURATOR-TEST",
        "curator_session_logical_id": "CURATOR-TEST-SESSION",
        "curator_platform_agent_id": "CURATOR-TEST-AGENT",
        "synthetic_test_only": True,
    }
    example["scenario_digest"] = object_digest(example, "scenario_digest")
    _validate_scenario(example)
    changed = copy.deepcopy(example)
    changed["profile_id"] = "CP02"
    try:
        _validate_scenario(changed)
    except BaselineError as error:
        require(str(error).startswith("E_SCENARIO_ID_PROFILE"), "E_SELFTEST_WRONG_FAILURE")
    else:
        raise BaselineError("E_SELFTEST_TAMPER_ACCEPTED")
    require(240 + 60 == 300, "E_SELFTEST_CORE_TOTAL")
    print("GATE1_V11_300_BASELINE_SELFTEST: PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "prepare-routes",
            "compare-routes",
            "prepare-production",
            "serialize-author",
            "check",
            "selftest",
        ),
    )
    args = parser.parse_args()
    if args.command == "prepare-routes":
        prepare_routes()
    elif args.command == "compare-routes":
        compare_routes()
    elif args.command == "prepare-production":
        prepare_production()
    elif args.command == "serialize-author":
        serialize_author_outputs()
    elif args.command == "check":
        check()
    else:
        selftest()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BaselineError, OSError, ValueError, KeyError, TypeError) as error:
        sys.stderr.write(f"{error}\n")
        raise SystemExit(1)
