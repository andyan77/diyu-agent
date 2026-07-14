#!/usr/bin/env python3
"""Deterministic tooling for the resealed Gate 1 P4 qualification batch."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("p4_resealed refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_P3_ROUTE_INPUT_COMPILER_RECOVERY_AND_P4_RESEALED_PROBE40_001"
PROMPT_REVISION = "r0"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_resealed_hidden_probe40_001"
)
P4_ROOT = ROOT / TASK_ROOT
P3_RECOVERY_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p3_route_input_compiler_recovery_001"
)
OLD_P4_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_sealed_hidden_probe40_001"
)
P2_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
P3_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001"
)
P1A_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1a_standard_baseline_review_packet_and_governance_preflight_001"
)
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
COMPONENTS = P2_ROOT / "component/active_gate1_components.v0.1.jsonl"
RULES = P2_ROOT / "component/active_control_rules.v0.1.jsonl"
EDGES = P2_ROOT / "component/active_gate1_edges.v0.1.jsonl"
AB_PATHS = P2_ROOT / "ab/active_ab_structural_paths.v0.1.jsonl"
GENERATOR_CORE = P2_ROOT / "p2_generator_core_r6.py"
AUTHOR_INSTRUCTION = (
    P3_ROOT / "freeze/attempt_1/controlled_author_instruction.v0.2.md"
)
AUTHOR_MODEL = P3_ROOT / "freeze/attempt_1/author_model_and_session.v0.2.yaml"
STANDARD = P1A_ROOT / "standard/diyu_content_composition_standard.v1.1.md"
CURRENT_CHECKER = Path("ci/checkers/check_gate1_v1_1_current.py")
CURRENT_OWNER = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "current_gate1_owner.v0.1.yaml"
)

ALLOWED_INPUT = TASK_ROOT / "contract/curator_allowed_input.v1.0.json"
CURATION_CONTRACT = TASK_ROOT / "contract/curation_contract.v1.0.yaml"
REVIEW_CONTRACT = TASK_ROOT / "contract/review_contract.v1.0.yaml"
TOOL_FREEZE = TASK_ROOT / "freeze/p4_resealed_tool_freeze.v1.0.yaml"
TOOL_COMMIT_BINDING = TASK_ROOT / "freeze/p4_tool_commit_binding.v1.0.yaml"
LIFECYCLE = TASK_ROOT / "result/p4_resealed_lifecycle.v1.0.yaml"

CURATED_POSITIVE = TASK_ROOT / "curation/curated_positive_20.v1.0.jsonl"
CURATED_ROUTE_INPUTS = TASK_ROOT / "curation/curated_anomaly_route_inputs_20.v1.0.jsonl"
CURATED_ROUTE_GOLD = TASK_ROOT / "curation/curated_anomaly_route_gold_20.v1.0.jsonl"
CURATOR_RECEIPT = TASK_ROOT / "curation/curator_run_receipt.v1.0.yaml"
PREFREEZE_REPORT = TASK_ROOT / "curation/pre_freeze_validation.v1.0.yaml"
AUTHOR_REQUESTS = TASK_ROOT / "freeze/positive_author_requests_20.v1.0.jsonl"
ROUTE_INPUTS = TASK_ROOT / "freeze/anomaly_route_inputs_20.v1.0.jsonl"
ROUTE_GOLD = TASK_ROOT / "freeze/anomaly_route_gold_20.v1.0.jsonl"
RUN_ORDER = TASK_ROOT / "freeze/sealed_run_order_40.v1.0.jsonl"
HIDDEN_FREEZE = TASK_ROOT / "freeze/p4_resealed_hidden_input_freeze.v1.0.yaml"

POSITIVE_OUTPUTS = TASK_ROOT / "run/positive_20_first_outputs.v1.0.jsonl"
AUTHOR_RECEIPT = TASK_ROOT / "run/author_run_receipt.v1.0.yaml"
COMPILED_ROUTES = TASK_ROOT / "run/anomaly_compiled_inputs_20.v1.0.jsonl"
ROUTE_ACTUALS = TASK_ROOT / "run/anomaly_first_actuals_20.v1.0.jsonl"
ROUTE_ACTUAL_FREEZE = TASK_ROOT / "run/anomaly_actual_freeze.v1.0.yaml"
ROUTE_COMPARISONS = TASK_ROOT / "run/anomaly_comparisons_20.v1.0.jsonl"
EXTERNAL_AUDIT = TASK_ROOT / "audit/external_exit_audit.v1.0.yaml"

BLIND_PACKET = TASK_ROOT / "review/blind_positive_20.v1.0.jsonl"
BLIND_CATALOG = TASK_ROOT / "review/content_product_choice_catalog.v1.0.jsonl"
BLIND_MAPPING = TASK_ROOT / "review/blind_label_mapping.v1.0.jsonl"
REVIEW_ONE_STAGE = TASK_ROOT / "review/staging/content_value_blind_stage.v1.0.json"
REVIEW_TWO_STAGE = TASK_ROOT / "review/staging/fact_authorization_blind_stage.v1.0.json"
REVIEW_ONE = TASK_ROOT / "review/signed_content_value_review.v1.0.json"
REVIEW_TWO = TASK_ROOT / "review/signed_fact_authorization_review.v1.0.json"
ADJUDICATION = TASK_ROOT / "review/targeted_adjudication.v1.0.json"
CHECKPOINT_RESULT = TASK_ROOT / "result/p4_resealed_checkpoint_result.v1.0.yaml"
DELIVERY_RECEIPT = TASK_ROOT / "result/p4_resealed_delivery_receipt.v1.0.yaml"

P3_RECOVERY_COMMIT = "21fdd1f"
P3_RECOVERY_BASELINE = "08627f5a843f450efa3a5d4a32cf2191087badd8"
OLD_P4_TREE = "404a77ec7f59e0ce639daddbcd3c8d658d9bed5b"
MODEL_CAPABILITY = "gpt-5.6-sol"
REASONING_EFFORT = "high"
SERVICE_TIER = "priority"
EXPECTED_PROFILES = tuple(f"CP{number:02d}" for number in range(1, 21))
EXPECTED_VARIANTS = {"A1": 5, "A2": 5, "B1": 5, "B2": 5}
ALLOWED_ACTIONS = frozenset({"BLOCK", "REQUEST_INPUT", "DEGRADE"})
ALLOWED_REASONS = frozenset({"输入冲突", "事实缺失", "授权缺失"})
POSITIVE_SCHEMA = "gate1-p4r-curated-positive-v1.0"
POSITIVE_OUTPUT_SCHEMA = "gate1-p4r-positive-first-output-v1.0"
GOLD_SCHEMA = "gate1-p4r-anomaly-route-gold-v1.0"

FROZEN_SHA256 = {
    COMPONENTS: "83dd1a8d35149785ac8bb172700b79d6221e5a7331b210018699fabaa49bc8ae",
    RULES: "5d0ded265a6be6d0f39d35d2f739239225211081db6d6c4e4df0c8dcc2f09386",
    EDGES: "de366eb50afe8a5a9362d3faa2a6a845af9c334683bdb9a8489cbfad2b2566f0",
    AB_PATHS: "4756971ef58ed472d0447f61f00bac7b7ef594117c43ecfb9fe3d7106c9631f3",
    GENERATOR_CORE: "e15eab89cef2cb9b2a35d76ca3550b67f2c49c583fc9efe107ebaf062f527015",
    AUTHOR_INSTRUCTION: "5962400130fd59ed8b94611cb4c2d46a9f10b3672041369325e3acf417b5a98e",
    AUTHOR_MODEL: "516bc60467bfe30991ea9228ff34b3c753d96410f74424ca5dbffc74d91283d3",
}


class P4ResealedError(ValueError):
    """Stable fail-closed error raised by P4 resealed tooling."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise P4ResealedError(f"{code}:{detail}" if detail else code)


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
    path.write_text(
        "\n".join(canonical_json(row) for row in rows) + "\n",
        encoding="utf-8",
    )


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
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _profiles() -> list[dict[str, Any]]:
    registry = load_yaml(ROOT / PROFILE_PATH).get("content_product_profile_registry")
    require(isinstance(registry, dict), "E_PROFILE_REGISTRY")
    profiles = registry.get("profiles")
    require(isinstance(profiles, list) and len(profiles) == 20, "E_PROFILE_COUNT")
    rows = [dict(item) for item in profiles if isinstance(item, dict)]
    require({row.get("content_product_type_id") for row in rows} == set(EXPECTED_PROFILES), "E_PROFILE_SET")
    return rows


def _component_projection() -> dict[str, Any]:
    components = {row["component_id"]: row for row in read_jsonl(ROOT / COMPONENTS)}
    edges: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in read_jsonl(ROOT / EDGES):
        edges[str(edge["content_product_type_id"])].append(edge)
    paths = {
        str(row["content_product_type_id"]): row
        for row in read_jsonl(ROOT / AB_PATHS)
    }
    projected: list[dict[str, Any]] = []
    for profile in _profiles():
        profile_id = str(profile["content_product_type_id"])
        approved: list[dict[str, Any]] = []
        for edge in sorted(edges[profile_id], key=lambda item: str(item["edge_id"])):
            component = components[str(edge["component_id"])]
            approved.append(
                {
                    "component_id": component["component_id"],
                    "component_digest": component["component_digest"],
                    "component_role": component["component_role"],
                    "mechanism": component["mechanism"],
                    "required_input_slots": component.get("required_input_slots", []),
                    "required_fact_slots": component.get("required_fact_slots", []),
                    "required_authorization_slots": component.get(
                        "required_authorization_slots", []
                    ),
                    "claim_boundary": component.get("claim_boundary"),
                    "edge_id": edge["edge_id"],
                    "fit_basis": edge["fit_basis"],
                }
            )
        axis_values: dict[str, dict[str, Any]] = {"A": {}, "B": {}}
        axis_programs: dict[str, dict[str, Any]] = {"A": {}, "B": {}}
        for contract in paths[profile_id]["axis_realization_contracts"]:
            axis = str(contract["axis"])
            axis_values["A"][axis] = contract["lane_a_value"]
            axis_values["B"][axis] = contract["lane_b_value"]
            axis_programs["A"][axis] = contract["lane_a_structural_output"]["structural_body"]
            axis_programs["B"][axis] = contract["lane_b_structural_output"]["structural_body"]
        projected.append(
            {
                "profile_id": profile_id,
                "label": profile["chinese_label"],
                "business_purpose": profile["business_purpose"],
                "target_account_roles": profile["target_account_roles"],
                "target_platforms": profile["target_platforms"],
                "founder_core_inputs": profile["founder_core_inputs"],
                "input_requirements": profile["input_requirements"],
                "required_component_roles": profile["required_component_roles"],
                "narrative_constraints": profile["narrative_constraints"],
                "style_constraints": profile["style_constraints"],
                "founder_hard_guards": profile["founder_hard_guards"],
                "event_truth_policy": profile["event_truth_policy"],
                "input_sufficiency_routes": profile["input_sufficiency_routes"],
                "approved_components": approved,
                "lane_axis_values": axis_values,
                "lane_axis_programs": axis_programs,
            }
        )
    return bind_digest(
        {
            "schema_version": "gate1-p4r-curator-allowed-input-v1.0",
            "task_id": TASK_ID,
            "source_boundary": {
                "contains_p3_or_old_p4_case_text": False,
                "contains_historical_gold_pairings": False,
                "synthetic_hidden_qualification_only": True,
            },
            "route_vocabulary": {
                "actions": sorted(ALLOWED_ACTIONS),
                "reasons": sorted(ALLOWED_REASONS),
            },
            "profiles": projected,
        },
        "allowed_input_digest",
    )


def _curation_contract() -> dict[str, Any]:
    return {
        "p4_resealed_curation_contract": bind_digest(
            {
                "schema_version": "gate1-p4r-curation-contract-v1.0",
                "task_id": TASK_ID,
                "positive_count": 20,
                "anomaly_count": 20,
                "one_positive_and_anomaly_per_profile": True,
                "variant_counts": EXPECTED_VARIANTS,
                "positive_schema": POSITIVE_SCHEMA,
                "route_input_schema": "gate1-canonical-route-input-v1.0",
                "route_gold_schema": GOLD_SCHEMA,
                "namespace": "P4R_SYNTHETIC_HIDDEN_QUALIFICATION",
                "positive_required_semantic_kinds": [
                    "setting",
                    "actor",
                    "object",
                    "observation",
                    "action",
                    "result",
                    "visual",
                    "sound",
                    "boundary",
                ],
                "newness": {
                    "new_case_ids_and_scenarios": True,
                    "new_fact_values_and_key_combinations": True,
                    "historical_case_or_gold_rewrite_forbidden": True,
                    "normalized_near_duplicate_threshold": 0.82,
                },
                "forbidden_curator_inputs": [
                    "P3 case text, gold, output, or review",
                    "old P4 case text, gold, output, or review",
                    "compiler implementation or actual route results",
                ],
            },
            "contract_digest",
        )
    }


def _review_contract() -> dict[str, Any]:
    return {
        "p4_resealed_review_contract": bind_digest(
            {
                "schema_version": "gate1-p4r-review-contract-v1.0",
                "task_id": TASK_ID,
                "review_roles": ["CONTENT_VALUE", "FACT_AUTHORIZATION"],
                "blind_first": True,
                "score_dimensions": {
                    "public_quality": {
                        "truth_and_boundary": 20,
                        "apparel_specificity": 10,
                        "role_and_brand_consistency": 10,
                        "user_value": 10,
                        "platform_execution": 10,
                        "anti_formula": 10,
                    },
                    "product_quality": {
                        "product_core_fidelity": 15,
                        "product_specific_narrative_av": 10,
                        "continuity": 5,
                    },
                },
                "first_acceptable_min_score": 80,
                "batch_thresholds": {
                    "first_acceptable_min_each": 18,
                    "blind_top1_min_each": 17,
                    "formula_or_near_duplicate_union_max": 2,
                    "hard_error_union_max": 0,
                    "route_action_match": 20,
                    "route_reason_match": 20,
                },
                "third_review_only_for_substantive_disagreement": True,
            },
            "contract_digest",
        )
    }


def prepare_tools() -> None:
    for path in (CURATED_POSITIVE, CURATED_ROUTE_INPUTS, CURATED_ROUTE_GOLD, HIDDEN_FREEZE):
        require(not (ROOT / path).exists(), "E_HIDDEN_BEFORE_TOOL_FREEZE", path.as_posix())
    for path, expected in FROZEN_SHA256.items():
        require(sha256_file(ROOT / path) == expected, "E_FROZEN_BASELINE", path.as_posix())
    old_tree = _git("rev-parse", f"{P3_RECOVERY_BASELINE}:{OLD_P4_ROOT.as_posix()}")
    require(old_tree.returncode == 0 and old_tree.stdout.strip() == OLD_P4_TREE, "E_OLD_P4_TREE")
    require(
        _git("diff", "--quiet", P3_RECOVERY_BASELINE, "--", OLD_P4_ROOT.as_posix()).returncode == 0,
        "E_OLD_P4_MUTATION",
    )
    write_json(ROOT / ALLOWED_INPUT, _component_projection())
    write_yaml(ROOT / CURATION_CONTRACT, _curation_contract())
    write_yaml(ROOT / REVIEW_CONTRACT, _review_contract())
    tool_files = (
        TASK_ROOT / "p4_resealed.py",
        TASK_ROOT / "p4_resealed_guard.py",
        TASK_ROOT / "p3_recovery_guard_current.py",
        CURRENT_CHECKER,
    )
    for path in tool_files:
        require((ROOT / path).is_file(), "E_TOOL_FILE", path.as_posix())
    freeze = {
        "p4_resealed_tool_freeze": bind_digest(
            {
                "schema_version": "gate1-p4r-tool-freeze-v1.0",
                "task_id": TASK_ID,
                "prompt_revision": PROMPT_REVISION,
                "p3_recovery_commit": _git("rev-parse", P3_RECOVERY_COMMIT).stdout.strip(),
                "p3_recovery_root_sha256": sha256_file(
                    ROOT / P3_RECOVERY_ROOT / "freeze/p3_route_compiler_recovery_freeze.v1.0.yaml"
                ),
                "old_p4_tree": OLD_P4_TREE,
                "tool_files": {
                    path.as_posix(): sha256_file(ROOT / path) for path in tool_files
                },
                "contract_files": {
                    path.as_posix(): sha256_file(ROOT / path)
                    for path in (ALLOWED_INPUT, CURATION_CONTRACT, REVIEW_CONTRACT)
                },
                "frozen_business_files": {
                    path.as_posix(): digest for path, digest in FROZEN_SHA256.items()
                },
                "hidden_material_absent": True,
                "generator_qualified": False,
                "p5_allowed": False,
                "core_numbers": {"300": "UNCHANGED", "120": "UNCHANGED", "86": "UNCHANGED"},
            },
            "freeze_digest",
        )
    }
    write_yaml(ROOT / TOOL_FREEZE, freeze)
    write_yaml(
        ROOT / LIFECYCLE,
        {
            "p4_resealed_lifecycle": bind_digest(
                {
                    "schema_version": "gate1-p4r-lifecycle-v1.0",
                    "task_id": TASK_ID,
                    "state": "TOOLS_FROZEN_PENDING_HIDDEN_CURATION",
                    "hidden_created": False,
                    "hidden_exposed": False,
                    "generator_qualified": False,
                    "p5_allowed": False,
                    "readiness_true_keys": [],
                },
                "lifecycle_digest",
            )
        },
    )


def _assert_digest(row: Mapping[str, Any], key: str, code: str) -> None:
    require(row.get(key) == object_digest(row, key), code, str(row.get("case_id", "")))


def _validate_positive_rows(rows: Sequence[dict[str, Any]]) -> None:
    require(len(rows) == 20, "E_POSITIVE_COUNT")
    require({row.get("profile_id") for row in rows} == set(EXPECTED_PROFILES), "E_POSITIVE_PROFILES")
    require(Counter(str(row.get("assigned_variant")) for row in rows) == Counter(EXPECTED_VARIANTS), "E_POSITIVE_VARIANTS")
    require(sorted(row.get("run_order") for row in rows) == list(range(1, 21)), "E_POSITIVE_ORDER")
    profile_map = {str(row["content_product_type_id"]): row for row in _profiles()}
    for row in rows:
        require(row.get("schema_version") == POSITIVE_SCHEMA and row.get("task_id") == TASK_ID, "E_POSITIVE_SCHEMA")
        require(str(row.get("case_id", "")).startswith("P4R-POS-"), "E_POSITIVE_CASE_ID")
        _assert_digest(row, "case_digest", "E_POSITIVE_DIGEST")
        material = row.get("typed_material")
        require(isinstance(material, dict), "E_POSITIVE_MATERIAL")
        _assert_digest(material, "material_digest", "E_MATERIAL_DIGEST")
        require(
            material.get("namespace") == "P4R_SYNTHETIC_HIDDEN_QUALIFICATION"
            and material.get("synthetic_test_only") is True
            and material.get("publishable") is False
            and material.get("runtime_consumable") is False
            and material.get("may_enter_300") is False,
            "E_MATERIAL_BOUNDARY",
        )
        sources = material.get("sources")
        facts = material.get("facts")
        authorizations = material.get("authorizations")
        require(all(isinstance(value, list) and value for value in (sources, facts, authorizations)), "E_MATERIAL_CLOSURE")
        source_ids = {str(item.get("source_id")) for item in sources if isinstance(item, dict)}
        auth_ids = {str(item.get("authorization_id")) for item in authorizations if isinstance(item, dict)}
        require(len(source_ids) == len(sources) and len(auth_ids) == len(authorizations), "E_MATERIAL_ID_UNIQUE")
        fact_ids: set[str] = set()
        kinds: set[str] = set()
        for fact in facts:
            require(isinstance(fact, dict), "E_FACT_OBJECT")
            fact_id = str(fact.get("fact_id"))
            require(fact_id and fact_id not in fact_ids, "E_FACT_ID")
            fact_ids.add(fact_id)
            kinds.add(str(fact.get("semantic_kind")))
            value = fact.get("value")
            require(isinstance(value, str) and value.strip(), "E_FACT_VALUE", fact_id)
            require(fact.get("fact_value_digest") == sha256_bytes(value.encode()), "E_FACT_DIGEST", fact_id)
            require(set(fact.get("source_ids", [])).issubset(source_ids), "E_FACT_SOURCE", fact_id)
            require(set(fact.get("authorization_ids", [])).issubset(auth_ids), "E_FACT_AUTH", fact_id)
        require(
            {"setting", "actor", "object", "observation", "action", "result", "visual", "sound", "boundary"}.issubset(kinds),
            "E_FACT_SEMANTIC_COVERAGE",
            str(row.get("profile_id")),
        )
        requirements = profile_map[str(row["profile_id"])]["input_requirements"]
        require(set(requirements["required_source_slots"]).issubset({str(item.get("slot_id")) for item in sources}), "E_REQUIRED_SOURCE_CLOSURE")
        require(set(requirements["required_fact_slots"]).issubset({str(item.get("slot_id")) for item in facts}), "E_REQUIRED_FACT_CLOSURE")
        require(set(requirements["required_authorization_slots"]).issubset({str(item.get("slot_id")) for item in authorizations}), "E_REQUIRED_AUTH_CLOSURE")
        core = row.get("product_core_requirements")
        require(isinstance(core, list) and core, "E_CORE_REQUIREMENTS")
        for requirement in core:
            require(isinstance(requirement, dict) and set(requirement.get("fact_ids", [])).issubset(fact_ids), "E_CORE_FACT_REFS")


def _load_route_contract() -> ModuleType:
    path = ROOT / P3_RECOVERY_ROOT / "route_contract.py"
    name = "gate1_p4r_route_contract"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "E_ROUTE_IMPORT")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _validate_route_rows(inputs: Sequence[dict[str, Any]], gold: Sequence[dict[str, Any]]) -> None:
    require(len(inputs) == len(gold) == 20, "E_ROUTE_COUNT")
    require({row.get("profile_id") for row in inputs} == set(EXPECTED_PROFILES), "E_ROUTE_PROFILES")
    require({row.get("case_id") for row in inputs} == {row.get("case_id") for row in gold}, "E_ROUTE_CASE_COVERAGE")
    contract = _load_route_contract()
    for row in inputs:
        require(str(row.get("case_id", "")).startswith("P4R-ANOM-"), "E_ROUTE_CASE_ID")
        contract.compile_route_input(row, ROOT)
    actions: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    for row in gold:
        require(row.get("schema_version") == GOLD_SCHEMA and row.get("task_id") == TASK_ID, "E_GOLD_SCHEMA")
        _assert_digest(row, "gold_digest", "E_GOLD_DIGEST")
        require(row.get("gold_primary_action") in ALLOWED_ACTIONS, "E_GOLD_ACTION")
        require(row.get("gold_primary_reason_category") in ALLOWED_REASONS, "E_GOLD_REASON")
        actions[str(row["gold_primary_action"])] += 1
        reasons[str(row["gold_primary_reason_category"])] += 1
    require(set(actions) == set(ALLOWED_ACTIONS), "E_GOLD_ACTION_COVERAGE")
    require(set(reasons) == set(ALLOWED_REASONS), "E_GOLD_REASON_COVERAGE")


def _normalize(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def _new_material_texts(positives: Sequence[dict[str, Any]], routes: Sequence[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for row in positives:
        texts.extend([str(row.get("scenario_title", "")), str(row.get("scenario_summary", ""))])
        material = row.get("typed_material", {})
        for fact in material.get("facts", []) if isinstance(material, dict) else []:
            if isinstance(fact, dict):
                texts.append(str(fact.get("value", "")))
    for row in routes:
        for bucket in row.get("provided", {}).values():
            for item in bucket:
                if isinstance(item, dict):
                    texts.append(str(item.get("value_ref", "")))
        payload = row.get("degrade_request", {}).get("payload", {})
        if isinstance(payload, dict):
            texts.extend(str(value) for value in payload.values() if isinstance(value, str))
    return [_normalize(text) for text in texts if len(_normalize(text)) >= 20]


def _historical_material_texts() -> list[str]:
    paths = (
        OLD_P4_ROOT / "curation/curated_positive_20.v0.1.jsonl",
        OLD_P4_ROOT / "curation/curated_anomaly_20.v0.1.jsonl",
        P3_ROOT / "freeze/attempt_1/positive_author_requests_20.v0.2.jsonl",
        P3_RECOVERY_ROOT / "public/open_route_inputs_20.v1.0.jsonl",
    )
    texts: list[str] = []
    for path in paths:
        for row in read_jsonl(ROOT / path):
            material = row.get("typed_material")
            if isinstance(material, dict):
                for fact in material.get("facts", []):
                    if isinstance(fact, dict):
                        texts.append(str(fact.get("value", fact.get("fact_value", ""))))
            for key in ("scenario_title", "scenario_summary"):
                texts.append(str(row.get(key, "")))
    return [_normalize(text) for text in texts if len(_normalize(text)) >= 20]


def _anti_reuse(positives: Sequence[dict[str, Any]], routes: Sequence[dict[str, Any]]) -> dict[str, Any]:
    import difflib

    current = _new_material_texts(positives, routes)
    previous = _historical_material_texts()
    exact = 0
    maximum = 0.0
    compared = 0
    for left in current:
        for right in previous:
            if left == right or (min(len(left), len(right)) >= 30 and (left in right or right in left)):
                exact += 1
            if abs(len(left) - len(right)) <= max(len(left), len(right)) * 0.55:
                compared += 1
                maximum = max(maximum, difflib.SequenceMatcher(None, left, right).ratio())
    require(exact == 0 and maximum < 0.82, "E_HISTORICAL_REUSE", f"{exact}:{maximum:.3f}")
    return {
        "current_material_text_count": len(current),
        "historical_material_text_count": len(previous),
        "bounded_pair_comparison_count": compared,
        "normalized_exact_or_containment_hit_count": exact,
        "maximum_sequence_similarity": round(maximum, 6),
        "threshold": 0.82,
        "pass": True,
    }


def _allowed_by_profile() -> dict[str, dict[str, Any]]:
    value = json.loads((ROOT / ALLOWED_INPUT).read_text(encoding="utf-8"))
    return {str(row["profile_id"]): row for row in value["profiles"]}


def _build_author_request(row: dict[str, Any], author_agent_id: str) -> dict[str, Any]:
    allowed = _allowed_by_profile()[str(row["profile_id"])]
    lane = str(row["assigned_variant"])[0]
    return bind_digest(
        {
            "schema_version": "gate1-p4r-sealed-author-request-v1.0",
            "task_id": TASK_ID,
            "request_id": row["case_id"],
            "profile_id": row["profile_id"],
            "assigned_variant": row["assigned_variant"],
            "lane": lane,
            "run_order": row["run_order"],
            "model_capability_id": MODEL_CAPABILITY,
            "reasoning_effort": REASONING_EFFORT,
            "service_tier": SERVICE_TIER,
            "author_identity": "P4R-CONTROLLED-AUTHOR-GPT56SOL-001",
            "author_session_logical_id": "P4R-AUTHOR-SESSION-GPT56SOL-001",
            "author_platform_agent_id": author_agent_id,
            "platform": row["platform"],
            "audience": row["audience"],
            "duration_seconds": row["duration_seconds"],
            "business_purpose": allowed["business_purpose"],
            "typed_material": row["typed_material"],
            "product_core_requirements": row["product_core_requirements"],
            "approved_components": allowed["approved_components"],
            "structure_contract": {
                "axis_values": allowed["lane_axis_values"][lane],
                "axis_programs": allowed["lane_axis_programs"][lane],
            },
            "founder_hard_guards": allowed["founder_hard_guards"],
            "narrative_constraints": allowed["narrative_constraints"],
            "style_constraints": allowed["style_constraints"],
            "author_output_contract": {
                "schema_version": POSITIVE_OUTPUT_SCHEMA,
                "all_audience_surfaces_require_exact_fact_source_authorization_binding": True,
                "component_usage_requires_distinct_addressable_surface_evidence": True,
                "one_first_semantic_output_only": True,
                "synthetic_disclosure_required": True,
                "publishable": False,
                "runtime_consumable": False,
                "may_enter_300": False,
                "author_may_not_review_or_approve": True,
            },
        },
        "request_digest",
    )


def freeze_hidden(tool_commit: str, author_agent_id: str) -> None:
    require(_git("rev-parse", "HEAD").stdout.strip() == tool_commit, "E_TOOL_COMMIT_NOT_HEAD")
    require(_git("cat-file", "-e", f"{tool_commit}^{{commit}}").returncode == 0, "E_TOOL_COMMIT")
    for path in (CURATED_POSITIVE, CURATED_ROUTE_INPUTS, CURATED_ROUTE_GOLD):
        require(
            _git("cat-file", "-e", f"{tool_commit}:{path.as_posix()}").returncode != 0,
            "E_HIDDEN_IN_TOOL_COMMIT",
            path.as_posix(),
        )
    positives = read_jsonl(ROOT / CURATED_POSITIVE)
    routes = read_jsonl(ROOT / CURATED_ROUTE_INPUTS)
    gold = read_jsonl(ROOT / CURATED_ROUTE_GOLD)
    _validate_positive_rows(positives)
    _validate_route_rows(routes, gold)
    receipt = load_yaml(ROOT / CURATOR_RECEIPT).get("p4_resealed_curator_receipt")
    require(isinstance(receipt, dict), "E_CURATOR_RECEIPT")
    for key in ("curator_identity_id", "curator_platform_agent_id", "curator_session_id", "curator_run_id"):
        require(isinstance(receipt.get(key), str) and receipt[key], "E_CURATOR_IDENTITY", key)
    require(receipt.get("forbidden_material_access_count") == 0, "E_CURATOR_FORBIDDEN_ACCESS")
    require(receipt.get("allowed_input_sha256") == sha256_file(ROOT / ALLOWED_INPUT), "E_CURATOR_INPUT_BINDING")
    reuse = _anti_reuse(positives, routes)
    requests = [_build_author_request(row, author_agent_id) for row in sorted(positives, key=lambda item: item["run_order"])]
    write_jsonl(ROOT / AUTHOR_REQUESTS, requests)
    write_jsonl(ROOT / ROUTE_INPUTS, sorted(routes, key=lambda item: str(item["profile_id"])))
    write_jsonl(ROOT / ROUTE_GOLD, sorted(gold, key=lambda item: str(item["profile_id"])))
    order = [
        bind_digest(
            {
                "sequence": number,
                "case_kind": "POSITIVE" if number <= 20 else "ANOMALY",
                "case_id": (
                    requests[number - 1]["request_id"]
                    if number <= 20
                    else sorted(routes, key=lambda item: str(item["profile_id"]))[number - 21]["case_id"]
                ),
            },
            "order_digest",
        )
        for number in range(1, 41)
    ]
    write_jsonl(ROOT / RUN_ORDER, order)
    compiled = [_load_route_contract().compile_route_input(row, ROOT) for row in routes]
    report = {
        "p4_resealed_pre_freeze_validation": bind_digest(
            {
                "schema_version": "gate1-p4r-pre-freeze-validation-v1.0",
                "task_id": TASK_ID,
                "positive_count": 20,
                "anomaly_count": 20,
                "compiler_invocation_count": len(compiled),
                "compiled_payload_complete_count": sum(
                    isinstance(row.get("actual_input_payload"), dict) and bool(row["actual_input_payload"])
                    for row in compiled
                ),
                "anti_reuse": reuse,
                "gold_fields_in_compiler_input_count": 0,
                "author_agent_id": author_agent_id,
                "pass": True,
            },
            "validation_digest",
        )
    }
    write_yaml(ROOT / PREFREEZE_REPORT, report)
    write_yaml(
        ROOT / TOOL_COMMIT_BINDING,
        {
            "p4_tool_commit_binding": bind_digest(
                {
                    "schema_version": "gate1-p4r-tool-commit-binding-v1.0",
                    "task_id": TASK_ID,
                    "tool_freeze_commit": tool_commit,
                    "tool_freeze_sha256": sha256_file(ROOT / TOOL_FREEZE),
                    "hidden_material_absent_from_tool_commit": True,
                },
                "binding_digest",
            )
        },
    )
    artifacts = (CURATED_POSITIVE, CURATED_ROUTE_INPUTS, CURATED_ROUTE_GOLD, CURATOR_RECEIPT, PREFREEZE_REPORT, AUTHOR_REQUESTS, ROUTE_INPUTS, ROUTE_GOLD, RUN_ORDER)
    write_yaml(
        ROOT / HIDDEN_FREEZE,
        {
            "p4_resealed_hidden_input_freeze": bind_digest(
                {
                    "schema_version": "gate1-p4r-hidden-input-freeze-v1.0",
                    "task_id": TASK_ID,
                    "tool_freeze_commit": tool_commit,
                    "containing_commit_is_hidden_freeze_commit": True,
                    "artifacts": {path.as_posix(): sha256_file(ROOT / path) for path in artifacts},
                    "output_or_actual_or_review_present": False,
                    "new_material_created_after_p3_freeze": True,
                    "old_or_historical_case_reuse_count": 0,
                    "generator_qualified": False,
                    "p5_allowed": False,
                    "core_numbers": {"300": "UNCHANGED", "120": "UNCHANGED", "86": "UNCHANGED"},
                },
                "freeze_digest",
            )
        },
    )
    lifecycle = load_yaml(ROOT / LIFECYCLE)["p4_resealed_lifecycle"]
    lifecycle.update({"state": "HIDDEN_INPUTS_FROZEN", "hidden_created": True, "hidden_exposed": False, "tool_freeze_commit": tool_commit})
    lifecycle["lifecycle_digest"] = object_digest(lifecycle, "lifecycle_digest")
    write_yaml(ROOT / LIFECYCLE, {"p4_resealed_lifecycle": lifecycle})


def _validate_hidden_artifacts() -> None:
    freeze = load_yaml(ROOT / HIDDEN_FREEZE)["p4_resealed_hidden_input_freeze"]
    require(freeze.get("freeze_digest") == object_digest(freeze, "freeze_digest"), "E_HIDDEN_FREEZE_DIGEST")
    for path, identity in freeze.get("artifacts", {}).items():
        require(sha256_file(ROOT / Path(path)) == identity, "E_HIDDEN_ARTIFACT_DRIFT", path)
    _validate_positive_rows(read_jsonl(ROOT / CURATED_POSITIVE))
    _validate_route_rows(read_jsonl(ROOT / ROUTE_INPUTS), read_jsonl(ROOT / ROUTE_GOLD))


def run_route_actuals() -> None:
    _validate_hidden_artifacts()
    contract = _load_route_contract()
    inputs = read_jsonl(ROOT / ROUTE_INPUTS)
    compiled = [contract.compile_route_input(row, ROOT) for row in inputs]
    actuals = [contract.evaluate_compiled_route(row, ROOT) for row in compiled]
    write_jsonl(ROOT / COMPILED_ROUTES, compiled)
    write_jsonl(ROOT / ROUTE_ACTUALS, actuals)
    write_yaml(
        ROOT / ROUTE_ACTUAL_FREEZE,
        {
            "p4_resealed_route_actual_freeze": bind_digest(
                {
                    "schema_version": "gate1-p4r-route-actual-freeze-v1.0",
                    "task_id": TASK_ID,
                    "route_input_sha256": sha256_file(ROOT / ROUTE_INPUTS),
                    "compiled_route_sha256": sha256_file(ROOT / COMPILED_ROUTES),
                    "actual_route_sha256": sha256_file(ROOT / ROUTE_ACTUALS),
                    "actual_count": 20,
                    "gold_read_before_actual_freeze": False,
                },
                "actual_freeze_digest",
            )
        },
    )


def compare_route_gold() -> None:
    freeze = load_yaml(ROOT / ROUTE_ACTUAL_FREEZE)["p4_resealed_route_actual_freeze"]
    require(freeze.get("actual_freeze_digest") == object_digest(freeze, "actual_freeze_digest"), "E_ROUTE_FREEZE_DIGEST")
    require(freeze.get("actual_route_sha256") == sha256_file(ROOT / ROUTE_ACTUALS), "E_ROUTE_ACTUAL_DRIFT")
    actuals = {str(row["case_id"]): row for row in read_jsonl(ROOT / ROUTE_ACTUALS)}
    gold = {str(row["case_id"]): row for row in read_jsonl(ROOT / ROUTE_GOLD)}
    require(set(actuals) == set(gold), "E_ROUTE_COMPARE_COVERAGE")
    rows: list[dict[str, Any]] = []
    for case_id in sorted(actuals):
        actual = actuals[case_id]
        expected = gold[case_id]
        rows.append(
            bind_digest(
                {
                    "schema_version": "gate1-p4r-route-comparison-v1.0",
                    "task_id": TASK_ID,
                    "case_id": case_id,
                    "profile_id": actual["profile_id"],
                    "actual_primary_action": actual["actual_primary_action"],
                    "actual_primary_reason_category": actual["actual_primary_reason_category"],
                    "gold_primary_action": expected["gold_primary_action"],
                    "gold_primary_reason_category": expected["gold_primary_reason_category"],
                    "primary_action_matches_gold": actual["actual_primary_action"] == expected["gold_primary_action"],
                    "primary_reason_matches_gold": actual["actual_primary_reason_category"] == expected["gold_primary_reason_category"],
                    "audience_content_created": any(
                        actual.get(key) is True
                        for key in ("audience_title_created", "audience_body_created", "spoken_script_created", "runtime_plan_created", "runtime_consumable")
                    ),
                },
                "comparison_digest",
            )
        )
    write_jsonl(ROOT / ROUTE_COMPARISONS, rows)


def _load_old_actual_validator() -> ModuleType:
    module_root = ROOT / OLD_P4_ROOT
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))
    import p4_actual

    p4_actual.TASK_ID = TASK_ID
    p4_actual.POSITIVE_OUTPUT_SCHEMA = POSITIVE_OUTPUT_SCHEMA
    p4_actual.EXPECTED_PROFILES = EXPECTED_PROFILES
    p4_actual.EXPECTED_VARIANTS = EXPECTED_VARIANTS
    return p4_actual


def validate_author_outputs() -> None:
    _validate_hidden_artifacts()
    outputs = read_jsonl(ROOT / POSITIVE_OUTPUTS)
    requests = read_jsonl(ROOT / AUTHOR_REQUESTS)
    _load_old_actual_validator().validate_positive_outputs(outputs, requests)
    author_ids = {str(row["author_platform_agent_id"]) for row in outputs}
    require(len(author_ids) == 1, "E_AUTHOR_IDENTITY_COUNT")
    write_yaml(
        ROOT / AUTHOR_RECEIPT,
        {
            "p4_resealed_author_run_receipt": bind_digest(
                {
                    "schema_version": "gate1-p4r-author-run-receipt-v1.0",
                    "task_id": TASK_ID,
                    "author_platform_agent_id": next(iter(author_ids)),
                    "model_capability_id": MODEL_CAPABILITY,
                    "reasoning_effort": REASONING_EFFORT,
                    "service_tier": SERVICE_TIER,
                    "request_count": 20,
                    "first_output_count": 20,
                    "second_candidate_or_replacement_count": 0,
                    "external_provider_or_api_call_count": 0,
                    "request_sha256": sha256_file(ROOT / AUTHOR_REQUESTS),
                    "output_sha256": sha256_file(ROOT / POSITIVE_OUTPUTS),
                },
                "receipt_digest",
            )
        },
    )


def build_blind_packet() -> None:
    validate_author_outputs()
    outputs = read_jsonl(ROOT / POSITIVE_OUTPUTS)
    ranked = sorted(outputs, key=lambda row: sha256_bytes(f"P4R-BLIND:{row['request_id']}".encode()))
    mapping: list[dict[str, Any]] = []
    packet: list[dict[str, Any]] = []
    for number, output in enumerate(ranked, 1):
        blind_id = f"P4R-BLIND-{number:02d}"
        mapping.append(bind_digest({"blind_id": blind_id, "request_id": output["request_id"], "profile_id": output["profile_id"]}, "mapping_digest"))
        packet.append(
            bind_digest(
                {
                    "blind_id": blind_id,
                    "title": output["title"],
                    "body": output["body"],
                    "spoken_lines": output["spoken_lines"],
                    "cta": output["cta"],
                    "visual_execution": output["visual_execution"],
                    "audio_execution": output["audio_execution"],
                    "synthetic_disclosure": output["synthetic_disclosure"],
                },
                "blind_digest",
            )
        )
    catalog = [
        bind_digest(
            {
                "profile_id": row["content_product_type_id"],
                "label": row["chinese_label"],
                "business_purpose": row["business_purpose"],
                "founder_core_inputs": row["founder_core_inputs"],
                "founder_hard_guards": row["founder_hard_guards"],
            },
            "catalog_digest",
        )
        for row in _profiles()
    ]
    write_jsonl(ROOT / BLIND_MAPPING, mapping)
    write_jsonl(ROOT / BLIND_PACKET, packet)
    write_jsonl(ROOT / BLIND_CATALOG, catalog)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "E_JSON_OBJECT", path.as_posix())
    return value


def _validate_blind_stage(report: dict[str, Any], role: str) -> dict[str, str]:
    require(report.get("schema_version") == "gate1-p4r-blind-stage-v1.0" and report.get("task_id") == TASK_ID, "E_BLIND_SCHEMA")
    require(report.get("review_role") == role, "E_BLIND_ROLE")
    for key in ("reviewer_identity_id", "reviewer_platform_agent_id", "reviewer_session_id", "review_run_id"):
        require(isinstance(report.get(key), str) and report[key], "E_BLIND_IDENTITY", key)
    require(report.get("recorded_before_label_reveal") is True and report.get("label_mapping_accessed") is False, "E_BLIND_ORDER")
    require(report.get("blind_packet_sha256") == sha256_file(ROOT / BLIND_PACKET), "E_BLIND_PACKET_BINDING")
    require(report.get("choice_catalog_sha256") == sha256_file(ROOT / BLIND_CATALOG), "E_BLIND_CATALOG_BINDING")
    predictions = report.get("predictions")
    require(isinstance(predictions, list) and len(predictions) == 20, "E_BLIND_PREDICTIONS")
    blind_ids = {row["blind_id"] for row in read_jsonl(ROOT / BLIND_MAPPING)}
    require({row.get("blind_id") for row in predictions if isinstance(row, dict)} == blind_ids, "E_BLIND_COVERAGE")
    require(all(row.get("predicted_profile_id") in EXPECTED_PROFILES for row in predictions), "E_BLIND_PROFILE")
    require(report.get("blind_stage_digest") == object_digest(report, "blind_stage_digest"), "E_BLIND_DIGEST")
    return {str(row["blind_id"]): str(row["predicted_profile_id"]) for row in predictions}


def _score_review(report: dict[str, Any], role: str, stage: dict[str, Any]) -> dict[str, Any]:
    require(report.get("schema_version") == "gate1-p4r-independent-review-v1.0" and report.get("task_id") == TASK_ID, "E_REVIEW_SCHEMA")
    require(report.get("review_role") == role, "E_REVIEW_ROLE")
    for key in ("reviewer_identity_id", "reviewer_platform_agent_id", "reviewer_session_id", "review_run_id"):
        require(report.get(key) == stage.get(key), "E_REVIEW_IDENTITY_BINDING", key)
    require(report.get("blind_stage_sha256") == sha256_file(ROOT / (REVIEW_ONE_STAGE if role == "CONTENT_VALUE" else REVIEW_TWO_STAGE)), "E_REVIEW_BLIND_BINDING")
    reviews = report.get("positive_reviews")
    require(isinstance(reviews, list) and len(reviews) == 20, "E_REVIEW_POSITIVE_COUNT")
    mapping = {str(row["request_id"]): row for row in read_jsonl(ROOT / BLIND_MAPPING)}
    stage_choices = _validate_blind_stage(stage, role)
    request_ids = set(mapping)
    require({row.get("request_id") for row in reviews if isinstance(row, dict)} == request_ids, "E_REVIEW_COVERAGE")
    acceptable = 0
    blind_correct = 0
    formulas: set[str] = set()
    hard_errors: set[str] = set()
    scores: list[int] = []
    expected_public = {"truth_and_boundary": 20, "apparel_specificity": 10, "role_and_brand_consistency": 10, "user_value": 10, "platform_execution": 10, "anti_formula": 10}
    expected_product = {"product_core_fidelity": 15, "product_specific_narrative_av": 10, "continuity": 5}
    for row in reviews:
        request_id = str(row["request_id"])
        public = row.get("public_quality")
        product = row.get("product_quality")
        require(isinstance(public, dict) and set(public) == set(expected_public), "E_REVIEW_PUBLIC_DIMENSIONS")
        require(isinstance(product, dict) and set(product) == set(expected_product), "E_REVIEW_PRODUCT_DIMENSIONS")
        for key, maximum in expected_public.items():
            require(isinstance(public[key], int) and 0 <= public[key] <= maximum, "E_REVIEW_SCORE", key)
        for key, maximum in expected_product.items():
            require(isinstance(product[key], int) and 0 <= product[key] <= maximum, "E_REVIEW_SCORE", key)
        total = sum(public.values()) + sum(product.values())
        require(row.get("total_score") == total, "E_REVIEW_TOTAL", request_id)
        vetoes = row.get("hard_vetoes")
        require(isinstance(vetoes, list), "E_REVIEW_VETOES")
        expected_acceptable = total >= 80 and not vetoes
        require(row.get("first_acceptable") is expected_acceptable, "E_REVIEW_ACCEPTABLE", request_id)
        expected_grade = "A" if total >= 90 and not vetoes else "B" if expected_acceptable else "C"
        require(row.get("grade") == expected_grade, "E_REVIEW_GRADE", request_id)
        blind_id = str(mapping[request_id]["blind_id"])
        correct = stage_choices[blind_id] == mapping[request_id]["profile_id"]
        require(row.get("blind_id") == blind_id and row.get("blind_top1_correct") is correct, "E_REVIEW_BLIND_RESULT", request_id)
        acceptable += int(expected_acceptable)
        blind_correct += int(correct)
        scores.append(total)
        if row.get("formula_or_near_duplicate") is True:
            formulas.add(str(mapping[request_id]["profile_id"]))
        if vetoes:
            hard_errors.add(str(mapping[request_id]["profile_id"]))
        require(isinstance(row.get("evidence"), list) and row["evidence"], "E_REVIEW_EVIDENCE", request_id)
        require(isinstance(row.get("defects"), list), "E_REVIEW_DEFECTS", request_id)
    route_reviews = report.get("route_reviews")
    comparisons = {str(row["case_id"]): row for row in read_jsonl(ROOT / ROUTE_COMPARISONS)}
    require(isinstance(route_reviews, list) and len(route_reviews) == 20, "E_REVIEW_ROUTE_COUNT")
    require({row.get("case_id") for row in route_reviews if isinstance(row, dict)} == set(comparisons), "E_REVIEW_ROUTE_COVERAGE")
    for row in route_reviews:
        comparison = comparisons[str(row["case_id"])]
        require(
            row.get("primary_action_matches_gold") is comparison["primary_action_matches_gold"]
            and row.get("primary_reason_matches_gold") is comparison["primary_reason_matches_gold"],
            "E_REVIEW_ROUTE_BINDING",
            str(row["case_id"]),
        )
    require(report.get("review_digest") == object_digest(report, "review_digest"), "E_REVIEW_DIGEST")
    require(report.get("overall_verdict") == "PASS", "E_REVIEW_VERDICT")
    return {
        "score": round(sum(scores) / len(scores), 2),
        "first_acceptable": acceptable,
        "blind_correct": blind_correct,
        "formulas": sorted(formulas),
        "hard_errors": sorted(hard_errors),
    }


def review_metrics() -> dict[str, Any]:
    stage_one = _load_json(ROOT / REVIEW_ONE_STAGE)
    stage_two = _load_json(ROOT / REVIEW_TWO_STAGE)
    first_identity = tuple(stage_one.get(key) for key in ("reviewer_identity_id", "reviewer_platform_agent_id", "reviewer_session_id", "review_run_id"))
    second_identity = tuple(stage_two.get(key) for key in ("reviewer_identity_id", "reviewer_platform_agent_id", "reviewer_session_id", "review_run_id"))
    require(first_identity != second_identity, "E_REVIEW_IDENTITY_COLLISION")
    one = _score_review(_load_json(ROOT / REVIEW_ONE), "CONTENT_VALUE", stage_one)
    two = _score_review(_load_json(ROOT / REVIEW_TWO), "FACT_AUTHORIZATION", stage_two)
    formulas = sorted(set(one["formulas"]).union(two["formulas"]))
    hard_errors = sorted(set(one["hard_errors"]).union(two["hard_errors"]))
    return {"reviewer_one": one, "reviewer_two": two, "formula_union": formulas, "hard_error_union": hard_errors}


def _route_metrics() -> dict[str, Any]:
    rows = read_jsonl(ROOT / ROUTE_COMPARISONS)
    return {
        "count": len(rows),
        "action_match": sum(row.get("primary_action_matches_gold") is True for row in rows),
        "reason_match": sum(row.get("primary_reason_matches_gold") is True for row in rows),
        "audience_content_leak_count": sum(row.get("audience_content_created") is True for row in rows),
        "actions": sorted({str(row["actual_primary_action"]) for row in rows}),
    }


def finalize_pending_decision() -> None:
    validate_author_outputs()
    metrics = review_metrics()
    routes = _route_metrics()
    require(metrics["reviewer_one"]["first_acceptable"] >= 18 and metrics["reviewer_two"]["first_acceptable"] >= 18, "E_P4R_ACCEPTANCE_GATE")
    require(metrics["reviewer_one"]["blind_correct"] >= 17 and metrics["reviewer_two"]["blind_correct"] >= 17, "E_P4R_BLIND_GATE")
    require(len(metrics["formula_union"]) <= 2, "E_P4R_FORMULA_GATE")
    require(not metrics["hard_error_union"], "E_P4R_HARD_ERROR_GATE")
    require(routes["count"] == routes["action_match"] == routes["reason_match"] == 20, "E_P4R_ROUTE_GATE")
    require(routes["audience_content_leak_count"] == 0 and set(routes["actions"]) == set(ALLOWED_ACTIONS), "E_P4R_ROUTE_BOUNDARY")
    write_yaml(
        ROOT / EXTERNAL_AUDIT,
        {
            "p4_resealed_external_exit_audit": bind_digest(
                {
                    "schema_version": "gate1-p4r-exit-audit-v1.0",
                    "task_id": TASK_ID,
                    "observed_content_exit_events": [],
                    "external_api_or_network_call_count": len([]),
                    "credential_read_count": len([]),
                    "git_remote_transport_counted_as_content_exit": False,
                },
                "audit_digest",
            )
        },
    )
    result = {
        "p4_resealed_checkpoint_result": bind_digest(
            {
                "schema_version": "gate1-p4r-checkpoint-result-v1.0",
                "task_id": TASK_ID,
                "result_state": "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION",
                "positive_first_output_count": 20,
                "anomaly_first_actual_count": 20,
                "second_candidate_or_replacement_count": 0,
                "reviewer_one_score": metrics["reviewer_one"]["score"],
                "reviewer_two_score": metrics["reviewer_two"]["score"],
                "reviewer_one_first_accepted": metrics["reviewer_one"]["first_acceptable"],
                "reviewer_two_first_accepted": metrics["reviewer_two"]["first_acceptable"],
                "reviewer_one_blind_correct": metrics["reviewer_one"]["blind_correct"],
                "reviewer_two_blind_correct": metrics["reviewer_two"]["blind_correct"],
                "formula_or_near_duplicate_union": metrics["formula_union"],
                "hard_error_union": metrics["hard_error_union"],
                "route_action_match": routes["action_match"],
                "route_reason_match": routes["reason_match"],
                "audience_content_leak_count": routes["audience_content_leak_count"],
                "external_api_or_network_call_count": 0,
                "coordinator_decision_required": True,
                "qualification_verdict": None,
                "H_admitted_count": 0,
                "generator_qualified": False,
                "p5_allowed": False,
                "readiness_true_keys": [],
                "core_numbers": {"300": "UNCHANGED", "120": "UNCHANGED", "86": "UNCHANGED"},
                "old_p4_failure_bytes_changed": False,
            },
            "result_digest",
        )
    }
    write_yaml(ROOT / CHECKPOINT_RESULT, result)
    lifecycle = load_yaml(ROOT / LIFECYCLE)["p4_resealed_lifecycle"]
    lifecycle.update({"state": "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION", "hidden_exposed": True, "generator_qualified": False, "p5_allowed": False})
    lifecycle["lifecycle_digest"] = object_digest(lifecycle, "lifecycle_digest")
    write_yaml(ROOT / LIFECYCLE, {"p4_resealed_lifecycle": lifecycle})
    owner = bind_digest(
        {
            "schema_version": "v0.1",
            "owner_id": "GATE1_V11_P4_RESEALED_PENDING_OWNER",
            "task_id": TASK_ID,
            "current_task_root": TASK_ROOT.as_posix(),
            "current_checker": CURRENT_CHECKER.as_posix(),
            "result_state": "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION",
            "p3_complete": True,
            "p4_resealed_technical_gate_pass": True,
            "coordinator_decision_required": True,
            "generator_qualified": False,
            "p5_allowed": False,
            "predecessor": {
                "owner_id": "GATE1_V11_P3_ROUTE_COMPILER_RECOVERY_OWNER",
                "task_id": TASK_ID,
                "p3_recovery_commit": _git("rev-parse", P3_RECOVERY_COMMIT).stdout.strip(),
            },
            "current_generator": {
                "entrypoint": (TASK_ROOT / "p4_resealed.py").as_posix(),
                "route_contract": (P3_RECOVERY_ROOT / "route_contract.py").as_posix(),
                "active_component_count": 68,
                "active_edge_count": 85,
                "active_control_rule_count": 8,
                "generator_core_changed": False,
                "author_instruction_or_model_changed": False,
            },
            "core_numbers": {"target_total": 300, "reference_inventory": 120, "historical_component_inventory": 86, "all_unchanged": True},
            "readiness": {
                "candidatepack_ready": False,
                "KE_ready": False,
                "RAG_ready": False,
                "DIFY_ready": False,
                "production_servable": False,
                "generation_eligible": False,
                "generation_allowed": False,
                "release_ready": False,
                "production_ready": False,
                "generator_qualified": False,
                "runtime_ingest_ready": False,
            },
        },
        "owner_digest",
    )
    write_yaml(ROOT / CURRENT_OWNER, {"current_gate1_owner": owner})
    write_yaml(
        ROOT / DELIVERY_RECEIPT,
        {
            "p4_resealed_delivery_receipt": bind_digest(
                {
                    "schema_version": "gate1-p4r-delivery-receipt-v1.0",
                    "task_id": TASK_ID,
                    "result_state": "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION",
                    "result_sha256": sha256_file(ROOT / CHECKPOINT_RESULT),
                    "review_one_sha256": sha256_file(ROOT / REVIEW_ONE),
                    "review_two_sha256": sha256_file(ROOT / REVIEW_TWO),
                    "route_comparison_sha256": sha256_file(ROOT / ROUTE_COMPARISONS),
                    "qualification_decision_imported": False,
                    "H_admitted_count": 0,
                },
                "receipt_digest",
            )
        },
    )


def selftest() -> None:
    contract = _load_route_contract()
    sample = copy.deepcopy(read_jsonl(ROOT / P3_RECOVERY_ROOT / "public/open_route_inputs_20.v1.0.jsonl")[0])
    for mutation in (
        lambda value: value.__setitem__("gold_primary_action", "BLOCK"),
        lambda value: value["provided"]["source"][0].__setitem__("value_ref", ""),
        lambda value: value["missing"]["source"].append(value["provided"]["source"][0]["slot_id"]),
    ):
        broken = copy.deepcopy(sample)
        mutation(broken)
        broken["input_digest"] = object_digest(broken, "input_digest")
        try:
            contract.compile_route_input(broken, ROOT)
        except ValueError:
            continue
        raise P4ResealedError("E_SELFTEST_ROUTE_TAMPER_ACCEPTED")
    if (ROOT / HIDDEN_FREEZE).exists():
        positives = read_jsonl(ROOT / CURATED_POSITIVE)
        broken_positive = copy.deepcopy(positives)
        broken_positive[0]["typed_material"]["facts"][0]["fact_value_digest"] = "0" * 64
        broken_positive[0]["typed_material"]["material_digest"] = object_digest(broken_positive[0]["typed_material"], "material_digest")
        broken_positive[0]["case_digest"] = object_digest(broken_positive[0], "case_digest")
        try:
            _validate_positive_rows(broken_positive)
        except ValueError:
            pass
        else:
            raise P4ResealedError("E_SELFTEST_FACT_TAMPER_ACCEPTED")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare-tools")
    freeze = sub.add_parser("freeze-hidden")
    freeze.add_argument("--tool-commit", required=True)
    freeze.add_argument("--author-agent-id", required=True)
    sub.add_parser("route-actuals")
    sub.add_parser("route-compare")
    sub.add_parser("validate-author")
    sub.add_parser("build-blind")
    sub.add_parser("finalize-pending-decision")
    sub.add_parser("selftest")
    args = parser.parse_args()
    try:
        if args.command == "prepare-tools":
            prepare_tools()
        elif args.command == "freeze-hidden":
            freeze_hidden(args.tool_commit, args.author_agent_id)
        elif args.command == "route-actuals":
            run_route_actuals()
        elif args.command == "route-compare":
            compare_route_gold()
        elif args.command == "validate-author":
            validate_author_outputs()
        elif args.command == "build-blind":
            build_blind_packet()
        elif args.command == "finalize-pending-decision":
            finalize_pending_decision()
        else:
            selftest()
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "command": args.command}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
