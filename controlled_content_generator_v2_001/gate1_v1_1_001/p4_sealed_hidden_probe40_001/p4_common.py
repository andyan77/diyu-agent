#!/usr/bin/env python3
"""Shared paths, serialization, and digest helpers for Gate 1 P4."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml


if not __debug__:
    print("P4 tooling refuses python -O")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_SEALED_HIDDEN_PROBE40_001"
PROMPT_REVISION = "r0"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/p4_sealed_hidden_probe40_001"
)
P4 = ROOT / TASK_ROOT
P1A_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1a_standard_baseline_review_packet_and_governance_preflight_001"
)
P2_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
P3_ROOT = Path("controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001")

STANDARD = P1A_ROOT / "standard/diyu_content_composition_standard.v1.1.md"
PROFILES = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
COMPONENTS = P2_ROOT / "component/active_gate1_components.v0.1.jsonl"
RULES = P2_ROOT / "component/active_control_rules.v0.1.jsonl"
EDGES = P2_ROOT / "component/active_gate1_edges.v0.1.jsonl"
AB_PATHS = P2_ROOT / "ab/active_ab_structural_paths.v0.1.jsonl"
GENERATOR_CORE = P2_ROOT / "p2_generator_core_r6.py"
P3_INSTRUCTION = P3_ROOT / "freeze/attempt_1/controlled_author_instruction.v0.2.md"
P3_MODEL = P3_ROOT / "freeze/attempt_1/author_model_and_session.v0.2.yaml"
P3_REQUESTS = P3_ROOT / "freeze/attempt_1/positive_author_requests_20.v0.2.jsonl"
P3_RESULT = P3_ROOT / "result/p3_open_probe40_result.v0.2.yaml"
P3_HANDOFF = P3_ROOT / "result/p4_sealed_probe_handoff.v0.2.yaml"
P3_FREEZE = P3_ROOT / "freeze/attempt_1/p3_open_repair_freeze.v0.2.yaml"
P3_VALIDATOR = P3_ROOT / "p3_open_r1.py"
P3_RUNNER = P3_ROOT / "run_p3_open_probe_r1.py"
CURRENT_OWNER = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml"
)
CURRENT_CHECKER = Path("ci/checkers/check_gate1_v1_1_current.py")

BASELINE_MANIFEST = TASK_ROOT / "baseline/p4_frozen_baseline.v0.1.yaml"
ALLOWED_INPUT = TASK_ROOT / "baseline/curator_allowed_input.v0.1.json"
CURATION_CONTRACT = TASK_ROOT / "curation/curation_contract.v0.1.yaml"
REVIEW_CONTRACT = TASK_ROOT / "review/p4_independent_review_contract.v0.1.yaml"
TOOL_FREEZE = TASK_ROOT / "freeze/p4_tool_freeze.v0.1.yaml"
LIFECYCLE = TASK_ROOT / "result/p4_lifecycle.v0.1.yaml"

CURATED_POSITIVE = TASK_ROOT / "curation/curated_positive_20.v0.1.jsonl"
CURATED_ANOMALY = TASK_ROOT / "curation/curated_anomaly_20.v0.1.jsonl"
CURATOR_RECEIPT = TASK_ROOT / "curation/curator_run_receipt.v0.1.yaml"
CURATION_VALIDATION = TASK_ROOT / "curation/pre_freeze_validation.v0.1.yaml"
AUTHOR_REQUESTS = TASK_ROOT / "freeze/positive_author_requests_20.v0.1.jsonl"
ROUTE_INPUTS = TASK_ROOT / "freeze/anomaly_route_inputs_20.v0.1.jsonl"
ROUTE_GOLD = TASK_ROOT / "freeze/anomaly_route_gold_20.v0.1.jsonl"
RUN_ORDER = TASK_ROOT / "freeze/sealed_run_order_40.v0.1.jsonl"
HIDDEN_FREEZE = TASK_ROOT / "freeze/p4_hidden_input_freeze.v0.1.yaml"

POSITIVE_OUTPUTS = TASK_ROOT / "run/positive_20_first_outputs.v0.1.jsonl"
AUTHOR_RECEIPT = TASK_ROOT / "run/author_run_receipt.v0.1.yaml"
ROUTE_ACTUALS = TASK_ROOT / "run/anomaly_20_first_actuals.v0.1.jsonl"
ROUTE_ACTUAL_FREEZE = TASK_ROOT / "run/anomaly_actual_freeze.v0.1.yaml"
ROUTE_COMPARISONS = TASK_ROOT / "run/anomaly_20_comparisons.v0.1.jsonl"
EXIT_EVENTS = TASK_ROOT / "run/execution_exit_events.v0.1.jsonl"
EXIT_OBSERVATIONS = TASK_ROOT / "run/execution_exit_observations.v0.1.jsonl"
MACHINE_REPORT = TASK_ROOT / "run/machine_acceptance_report.v0.1.yaml"

BLIND_PACKET = TASK_ROOT / "review/blind_positive_20.v0.1.jsonl"
BLIND_CATALOG = TASK_ROOT / "review/content_product_choice_catalog.v0.1.jsonl"
BLIND_MAPPING = TASK_ROOT / "review/blind_label_mapping.v0.1.jsonl"
REVIEW_PACKET = TASK_ROOT / "review/p4_review_packet.v0.1.yaml"
REVIEW_ONE_STAGE = TASK_ROOT / "review/staging/content_value_blind_stage.v0.1.json"
REVIEW_TWO_STAGE = TASK_ROOT / "review/staging/fact_authorization_blind_stage.v0.1.json"
REVIEW_ONE = TASK_ROOT / "review/signed_content_value_review.v0.1.json"
REVIEW_TWO = TASK_ROOT / "review/signed_fact_authorization_review.v0.1.json"
ADJUDICATION = TASK_ROOT / "review/targeted_adjudication.v0.1.json"
CHECKPOINT_RESULT = TASK_ROOT / "result/p4_checkpoint_result.v0.1.yaml"
DECISION_PACKET = TASK_ROOT / "decision/founder_qualification_decision_packet.v0.1.yaml"
DELIVERY_RECEIPT = TASK_ROOT / "result/p4_delivery_receipt.v0.1.yaml"

MODEL_CAPABILITY = "gpt-5.6-sol"
REASONING_EFFORT = "high"
SERVICE_TIER = "priority"
EXPECTED_PROFILES = tuple(f"CP{index:02d}" for index in range(1, 21))
EXPECTED_VARIANTS = {"A1": 5, "A2": 5, "B1": 5, "B2": 5}
ALLOWED_ACTIONS = frozenset({"BLOCK", "DEGRADE", "REQUEST_INPUT"})
ALLOWED_REASONS = frozenset({"事实缺失", "授权缺失", "输入冲突"})
READY_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "runtime_ingest_ready",
        "release_ready",
        "production_ready",
    }
)

FROZEN_HASHES: dict[Path, str] = {
    P3_RESULT: "c06955256ef9190f5b89221c69417353791fbc7a4b0eb4f8dab0be2826b6fcb0",
    P3_HANDOFF: "a20695c33ecd5b995d479ae1fe1eab3c53ef0622b5b243a4885055a87e44b3aa",
    P3_FREEZE: "7e1497e6e862be41fb9968f0bd9a20e82942f2907ef4599e3b7986f2599558db",
    P3_INSTRUCTION: "5962400130fd59ed8b94611cb4c2d46a9f10b3672041369325e3acf417b5a98e",
    P3_MODEL: "516bc60467bfe30991ea9228ff34b3c753d96410f74424ca5dbffc74d91283d3",
    P3_REQUESTS: "d1d2a314222130751e3a743e8f25033164a033342021f97cbcca5bf0bc4f2708",
    P3_VALIDATOR: "58ffd0a81fe8aa301b50c96275b84514fd43df1bc4f0de25dfaef08839c7ed2a",
    P3_RUNNER: "e24df3f594280449159175aadb54a1f179f6eda19524bfae03ce3ef0a3b7127a",
    COMPONENTS: "83dd1a8d35149785ac8bb172700b79d6221e5a7331b210018699fabaa49bc8ae",
    RULES: "5d0ded265a6be6d0f39d35d2f739239225211081db6d6c4e4df0c8dcc2f09386",
    EDGES: "de366eb50afe8a5a9362d3faa2a6a845af9c334683bdb9a8489cbfad2b2566f0",
    AB_PATHS: "4756971ef58ed472d0447f61f00bac7b7ef594117c43ecfb9fe3d7106c9631f3",
    GENERATOR_CORE: "e15eab89cef2cb9b2a35d76ca3550b67f2c49c583fc9efe107ebaf062f527015",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that fails on duplicate mapping keys."""


def _construct_mapping(
    loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    value: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in value:
            raise ValueError(f"duplicate YAML key: {key}")
        value[key] = loader.construct_object(value_node, deep=deep)
    return value


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return value


def write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON root is not a mapping: {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"{path}:{number} is not a mapping")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(canonical_json(row) for row in rows) + "\n", encoding="utf-8"
    )


def digest_rows(rows: list[Mapping[str, Any]]) -> str:
    return sha256_bytes(
        ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")
    )


def recursively_true(value: Any, keys: frozenset[str] = READY_KEYS) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and child is True:
                found.append(key)
            found.extend(recursively_true(child, keys))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursively_true(child, keys))
    return found


def bind_digest(value: dict[str, Any], key: str) -> dict[str, Any]:
    value[key] = object_digest(value, key)
    return value
