#!/usr/bin/env python3
"""Shared deterministic utilities for the Gate 1 v1.1 P3 open probe."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    sys.stderr.write("P3 modules refuse python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_OPEN_PROBE40_001"
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/p3_open_probe40_001"
)
P2_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p2_component_supply_and_generator_core_repair_001"
)
P1A_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1a_standard_baseline_review_packet_and_governance_preflight_001"
)
P1B_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p1b_signed_review_closeout_and_baseline_freeze_001"
)
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
ROUTE_INPUT_PATH = Path(
    "controlled_content_generator_v2_001/"
    "creative_authoring_route_oracle_convergence_001/route/route_inputs.v0.1.jsonl"
)
ROUTE_GOLD_PATH = P1B_ROOT / "route/route_60_gold_answers.v0.1.jsonl"
P2_COMPONENTS_PATH = P2_ROOT / "component/active_gate1_components.v0.1.jsonl"
P2_RULES_PATH = P2_ROOT / "component/active_control_rules.v0.1.jsonl"
P2_EDGES_PATH = P2_ROOT / "component/active_gate1_edges.v0.1.jsonl"
P2_PATHS_PATH = P2_ROOT / "ab/active_ab_structural_paths.v0.1.jsonl"
P2_RESULT_PATH = P2_ROOT / "result/p2_final_result.v0.1.yaml"
CURRENT_OWNER_PATH = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/current_gate1_owner.v0.1.yaml"
)
CURRENT_CHECKER_PATH = Path("ci/checkers/check_gate1_v1_1_current.py")

BASELINE_COMMIT = "b707f97f16f1d8cdfe6cdee87ee7edba76170c8c"
AUTHORIZED_AUTHOR_MODEL_LABEL = "GPT 5.6 SOL"
AUTHORIZED_AUTHOR_CAPABILITY_ID = "gpt-5.6-sol"
AUTHORIZED_AUTHOR_IDENTITY = "P3-CONTROLLED-AUTHOR-GPT56SOL-001"
AUTHORIZED_AUTHOR_SESSION = "P3-AUTHOR-SESSION-GPT56SOL-001"


class P3ValidationError(ValueError):
    """Fail-closed validation error with a stable reason code."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise P3ValidationError(f"{code}{suffix}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def digest_object(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def object_digest(value: dict[str, Any], field: str) -> str:
    return digest_object({key: child for key, child in value.items() if key != field})


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), "E_JSONL_OBJECT", f"{path}:{line_number}")
        rows.append(value)
    return rows


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "E_YAML_OBJECT", path.as_posix())
    return value


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def yaml_bytes(value: dict[str, Any]) -> bytes:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=False,
        width=100,
    ).encode("utf-8")


def profile_rows(root: Path = ROOT) -> list[dict[str, Any]]:
    registry = load_yaml(root / PROFILE_PATH).get("content_product_profile_registry")
    require(isinstance(registry, dict), "E_PROFILE_REGISTRY")
    profiles = registry.get("profiles")
    require(isinstance(profiles, list) and len(profiles) == 20, "E_PROFILE_COUNT")
    typed = [dict(profile) for profile in profiles if isinstance(profile, dict)]
    require(len(typed) == 20, "E_PROFILE_OBJECTS")
    return typed


def p2_rows(root: Path = ROOT) -> dict[str, list[dict[str, Any]]]:
    return {
        "components": load_jsonl(root / P2_COMPONENTS_PATH),
        "rules": load_jsonl(root / P2_RULES_PATH),
        "edges": load_jsonl(root / P2_EDGES_PATH),
        "paths": load_jsonl(root / P2_PATHS_PATH),
    }


def readiness_false() -> dict[str, bool]:
    return {
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
    }
