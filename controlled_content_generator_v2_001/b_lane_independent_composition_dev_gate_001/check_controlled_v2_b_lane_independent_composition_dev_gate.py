#!/usr/bin/env python3
"""Independent governance checker for the B-lane pair development gate."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "CONTROLLED_V2_B_LANE_INDEPENDENT_COMPOSITION_DEV_GATE_001"
ROOT = Path(__file__).resolve().parents[2]
TASK_DIR = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001"
)
CORE_DIR = TASK_DIR / "core"
CAL_DIR = TASK_DIR / "calibration"
DEV_DIR = TASK_DIR / "dev_open_gate_pair_002"
OLD_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001"
)
OLD_CORE = OLD_DIR / "core"
OLD_FREEZE = OLD_DIR / "core_freeze_manifest.v0.1.yaml"
OLD_MATERIALIZER = OLD_DIR / "run_convergence_materializer.py"
ACTIVE_REGISTRY = OLD_CORE / "active_authoring_registry.v0.3.yaml"
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
RUNNER_PATH = TASK_DIR / "run_b_lane_dev_gate.py"
FREEZE_PATH = TASK_DIR / "core_freeze_manifest.v0.1.yaml"

OLD_FREEZE_SHA256 = "fd4e91e00bc8e4730904a7687de212249ff0b3d874310ade90fea5d9ca08628c"
OLD_CORE_DIGEST = "c585e661f053bb3661a2861a326f31a2f68f8c649f04765e576d6e48d7602e7d"
OLD_MATERIALIZER_SHA256 = (
    "e8b614080e1752a3295bc948ff2decdf9af1b92fcf4833172c9fff2279d56de0"
)
ROUTE_GATE_SHA256 = "e741811540938f7eb2d35a2dd10e65074b365f86740d19284483ef2865c055e3"
CREATIVE_PROTOCOL_SHA256 = (
    "b264c1f02e4c4a8f4fdb14948dcf13dac1942af892bcdf0e9358f240e730e3a0"
)
CREATIVE_INSTRUCTION_SHA256 = (
    "a48d5a27c3309b2a19e9a749a389475abfa5c67c5ba6534d813cb85157b6df13"
)
ACTIVE_REGISTRY_SHA256 = (
    "c31c0b32c9628df8ebb760383f9c1d22bc4f27bca53aec52a5bb9357c10eed74"
)
LEDGER_WITHOUT_ROUTE31_DIGEST = (
    "8c4b76b633d362ebd8ea2ad1cd024a2ac7a27a14153fea5c7a462062af471c4d"
)
ROUTE30_DIGEST = "b16ddfaefea4a4aff286ff299563e48305ccd1fd03827609eeffc207c81e6d12"

STYLE_AXES = (
    "information_order",
    "narrative_distance",
    "language_register",
    "sentence_rhythm",
    "visual_subject",
    "shot_continuity",
    "sound_subject",
    "ending_mode",
    "CTA_policy",
)
SEMANTIC_FIELDS = (
    "primary_audience_question",
    "observation_mission",
    "center_of_gravity",
    "causal_path",
)
SURFACE_LIST_FIELDS = (
    "body_blocks",
    "spoken_lines",
    "visual_beats",
    "capture_instructions",
)
SURFACE_SCALAR_FIELDS = ("title", "CTA", "audio_grammar", "editing_grammar")
READINESS_KEYS = frozenset(
    {
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
        "generator_qualified",
        "runtime_provider_adapter_qualified",
        "runtime_ingest_ready",
        "generation_600_allowed",
        "expand_3600_allowed",
    }
)
ZERO_KEYS = frozenset(
    {
        "accepted_baseline_increment_count",
        "baseline_increment_count",
        "external_provider_API_call_count",
        "hidden_created_count",
        "sealed_hidden_attempt_count",
        "runtime_generation_eligible_profile_count",
        "canonical_runtime_plan_count",
        "published_content_count",
        "KE_change_count",
        "RAG_change_count",
        "DIFY_change_count",
        "Serving_change_count",
    }
)
LEGAL_VISIBILITY_KEYS = frozenset(
    {
        "expected_score_visibility",
        "review_envelope_visibility",
        "sibling_candidate_visibility",
        "paired_output_visibility",
        "expected_verdict_visibility",
        "other_lane_plan_visibility",
        "other_lane_selected_atoms_visibility",
        "other_lane_request_visibility",
        "other_lane_response_visibility",
        "other_lane_candidate_visibility",
        "paired_output_visible",
        "review_envelope_visible",
        "expected_score_visible",
    }
)
SENSITIVE_CONCEPTS = (
    "expected_score",
    "review_envelope",
    "sibling_candidate",
    "paired_output",
    "expected_verdict",
)
EXPECTED_PROFILES = frozenset(f"CP{index:02d}" for index in range(1, 21))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected mapping in {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected object at {path}:{number}")
        rows.append(value)
    return rows


def string_set(value: Any) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return set()
    return {str(item) for item in value if str(item)}


def normalized_key(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def digest_field_errors(row: Mapping[str, Any], field: str, label: str) -> list[str]:
    if field not in row:
        return [f"E_DIGEST_FIELD_MISSING:{label}:{field}"]
    body = dict(row)
    claimed = body.pop(field)
    return (
        [] if claimed == digest_object(body) else [f"E_DIGEST_MISMATCH:{label}:{field}"]
    )


def boundary_errors(value: Any, label: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            path = f"{label}.{key}" if label else key
            if key in READINESS_KEYS and child is not False:
                errors.append(f"E_READINESS_TRUE:{path}")
            if key in ZERO_KEYS and child != 0:
                errors.append(f"E_FIXED_ZERO_DRIFT:{path}")
            if (
                key in {"accepted_baseline_count", "accepted_baseline_after"}
                and child != 120
            ):
                errors.append(f"E_BASELINE_INCREASE:{path}")
            errors.extend(boundary_errors(child, path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            errors.extend(boundary_errors(child, f"{label}[{index}]"))
    return errors


def sensitive_payload_errors(value: Any, label: str) -> list[str]:
    errors: list[str] = []

    def walk(child: Any, path: tuple[str, ...]) -> None:
        if isinstance(child, Mapping):
            for raw_key, nested in child.items():
                key = str(raw_key)
                normalized = normalized_key(key)
                rendered = ".".join((*path, key))
                if normalized in LEGAL_VISIBILITY_KEYS:
                    if nested is not False:
                        errors.append(f"E_VISIBILITY_NOT_FALSE:{label}:{rendered}")
                elif any(concept in normalized for concept in SENSITIVE_CONCEPTS):
                    errors.append(f"E_AUTHOR_INPUT_LEAK:{label}:{rendered}")
                if normalized in {"field", "field_name", "payload_type"} and isinstance(
                    nested, str
                ):
                    selected = normalized_key(nested)
                    if any(concept in selected for concept in SENSITIVE_CONCEPTS):
                        errors.append(
                            f"E_AUTHOR_INPUT_LEAK_SELECTOR:{label}:{rendered}"
                        )
                walk(nested, (*path, key))
        elif isinstance(child, Sequence) and not isinstance(
            child, (str, bytes, bytearray)
        ):
            for index, nested in enumerate(child):
                walk(nested, (*path, f"[{index}]"))

    walk(value, ())
    return sorted(set(errors))


def hidden_paths() -> list[Path]:
    task_root = ROOT / TASK_DIR
    return [path for path in task_root.rglob("*") if "hidden" in path.name.lower()]


def check_pr9_frozen_identity(actual: Mapping[str, str] | None = None) -> list[str]:
    pins = {
        OLD_FREEZE.as_posix(): OLD_FREEZE_SHA256,
        OLD_MATERIALIZER.as_posix(): OLD_MATERIALIZER_SHA256,
        (OLD_CORE / "controlled_v2_route_gate.py").as_posix(): ROUTE_GATE_SHA256,
        (
            OLD_CORE / "creative_author_protocol.v0.1.yaml"
        ).as_posix(): CREATIVE_PROTOCOL_SHA256,
        (
            OLD_CORE / "creative_author_instruction.v0.1.yaml"
        ).as_posix(): CREATIVE_INSTRUCTION_SHA256,
        ACTIVE_REGISTRY.as_posix(): ACTIVE_REGISTRY_SHA256,
    }
    observed = actual or {
        path: sha256_file(ROOT / path) if (ROOT / path).is_file() else "MISSING"
        for path in pins
    }
    errors = [
        f"E_PR9_FROZEN_DRIFT:{path}"
        for path, digest in pins.items()
        if observed.get(path) != digest
    ]
    if errors or actual is not None:
        return errors
    manifest = load_yaml(ROOT / OLD_FREEZE).get("core_freeze_manifest", {})
    if (
        manifest.get("core_digest") != OLD_CORE_DIGEST
        or manifest.get("core_file_count") != 24
    ):
        errors.append("E_PR9_CORE_MANIFEST_IDENTITY")
    for item in manifest.get("files", []):
        if not isinstance(item, Mapping):
            errors.append("E_PR9_CORE_MANIFEST_SHAPE")
            continue
        path = ROOT / str(item.get("path", ""))
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            errors.append(f"E_PR9_CORE_FILE_DRIFT:{item.get('path')}")
    registry = load_yaml(ROOT / ACTIVE_REGISTRY).get("active_authoring_registry", {})
    active = [
        row
        for row in registry.get("entries", [])
        if isinstance(row, Mapping)
        and row.get("status") == "active"
        and row.get("may_be_invoked_by_current_pipeline") is True
    ]
    if registry.get("active_entry_count") != 1 or len(active) != 1:
        errors.append("E_ACTIVE_AUTHORING_ENTRYPOINT_COUNT")
    if active and active[0].get("backend_class") != "CONTROLLED_EXECUTION_AGENT":
        errors.append("E_ACTIVE_AUTHORING_BACKEND")
    return errors


def materializer_boundary_errors() -> list[str]:
    path = ROOT / RUNNER_PATH
    if not path.is_file():
        return ["E_B_LANE_MATERIALIZER_MISSING"]
    source = path.read_text(encoding="utf-8")
    errors: list[str] = []
    forbidden = (
        "render_body",
        "write_prose",
        "body_template",
        "generate_audience_text",
    )
    if any(token in source for token in forbidden):
        errors.append("E_MATERIALIZER_AUDIENCE_WRITER_PATH")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=False):
            if isinstance(key, ast.Constant) and key.value == "surfaces":
                valid_passthrough = isinstance(value, ast.Subscript) or isinstance(
                    value, ast.Name
                )
                if not valid_passthrough:
                    errors.append("E_MATERIALIZER_SYNTHESIZES_SURFACES")
    return errors


def check_task_core_freeze() -> list[str]:
    path = ROOT / FREEZE_PATH
    if not path.is_file():
        return ["E_TASK_CORE_FREEZE_MISSING"]
    manifest = load_yaml(path).get("core_freeze_manifest", {})
    errors: list[str] = []
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return ["E_TASK_CORE_FREEZE_FILE_LIST"]
    if manifest.get("task_id") != TASK_ID or manifest.get("file_count") != len(files):
        errors.append("E_TASK_CORE_FREEZE_HEADER")
    if manifest.get("core_digest") != digest_object(files):
        errors.append("E_TASK_CORE_FREEZE_DIGEST")
    required = {
        RUNNER_PATH.as_posix(),
        Path(__file__).resolve().relative_to(ROOT).as_posix(),
    }
    listed: set[str] = set()
    for item in files:
        if not isinstance(item, Mapping):
            errors.append("E_TASK_CORE_FREEZE_ENTRY")
            continue
        relative = str(item.get("path", ""))
        listed.add(relative)
        target = ROOT / relative
        if not target.is_file() or sha256_file(target) != item.get("sha256"):
            errors.append(f"E_TASK_CORE_FREEZE_DRIFT:{relative}")
    if not required.issubset(listed):
        errors.append("E_TASK_CORE_FREEZE_REQUIRED_PATHS")
    if manifest.get("post_commit_core_mutation_allowed") is not False:
        errors.append("E_TASK_CORE_MUTATION_ALLOWED")
    calibration = ROOT / CAL_DIR / "calibration_result.v0.1.yaml"
    if not calibration.is_file():
        errors.append("E_CALIBRATION_RESULT_MISSING")
    else:
        result = load_yaml(calibration).get("calibration_result", {})
        expected = {
            "pair_count": 13,
            "new_authoring_invocation_count": 13,
            "raw_quality_A_or_B_count": 13,
            "calibration_pass": True,
            "reroll_count": 0,
            "replacement_count": 0,
            "per_candidate_manual_patch_count": 0,
            "hidden_created_count": 0,
            "generator_qualified": False,
            "accepted_baseline_count": 120,
        }
        for key, value in expected.items():
            if result.get(key) != value:
                errors.append(f"E_CALIBRATION_RESULT:{key}")
        errors.extend(
            digest_field_errors(result, "result_digest", "calibration_result")
        )
    return errors


def check_stopped_calibration() -> list[str]:
    required_paths = {
        "packs": CAL_DIR / "exposed_pair_calibration_material_packs.v0.1.jsonl",
        "plans": CAL_DIR / "composition_plans.v0.1.jsonl",
        "requests": CAL_DIR / "authoring_requests.v0.1.jsonl",
        "raw": CAL_DIR / "raw_authoring_responses.v0.1.jsonl",
        "retained": CAL_DIR / "retained_lane_A_candidates.v0.1.jsonl",
        "candidates": CAL_DIR / "generated_candidates.v0.1.jsonl",
        "machine": CAL_DIR / "machine_pair_results.v0.1.jsonl",
        "reviews": CAL_DIR / "calibration_reviews.v0.1.jsonl",
        "sessions": CAL_DIR / "authoring_session_registry.v0.1.jsonl",
        "result": CAL_DIR / "calibration_result.v0.1.yaml",
    }
    errors = [
        f"E_STOPPED_CALIBRATION_ARTIFACT_MISSING:{path}"
        for path in required_paths.values()
        if not (ROOT / path).is_file()
    ]
    if errors:
        return errors
    rows = {
        key: load_jsonl(ROOT / path)
        for key, path in required_paths.items()
        if key != "result"
    }
    expected_counts = {
        "packs": 13,
        "plans": 26,
        "requests": 13,
        "raw": 13,
        "retained": 13,
        "candidates": 13,
        "machine": 13,
        "reviews": 13,
        "sessions": 13,
    }
    for key, expected in expected_counts.items():
        if len(rows[key]) != expected:
            errors.append(f"E_STOPPED_CALIBRATION_COUNT:{key}")
    if len({str(item.get("agent_id")) for item in rows["sessions"]}) != 13:
        errors.append("E_STOPPED_CALIBRATION_SESSION_UNIQUENESS")
    if any(item.get("machine_validation_errors") for item in rows["candidates"]):
        errors.append("E_STOPPED_CALIBRATION_STRUCTURAL_FAILURE")
    raw_quality_pass = sum(
        str(item.get("raw_quality")) in {"A", "B"} for item in rows["reviews"]
    )
    pair_pass = sum(item.get("pair_independence") == "PASS" for item in rows["reviews"])
    paraphrase = sum(item.get("mere_paraphrase") is True for item in rows["reviews"])
    unsupported = sum(
        int(item.get("unsupported_fact_count", 0)) for item in rows["reviews"]
    )
    invalid = sum(
        int(item.get("invalid_reference_count", 0)) for item in rows["reviews"]
    )
    exact = sum(
        int(item.get("all_surface_exact_line_overlap_count", 0))
        for item in rows["machine"]
    )
    result = load_yaml(ROOT / required_paths["result"]).get("calibration_result", {})
    expected_result = {
        "status": "STOPPED_PAIR_CALIBRATION_FAILED",
        "pair_count": 13,
        "new_authoring_invocation_count": 13,
        "raw_quality_A_or_B_count": raw_quality_pass,
        "pair_independence_pass_count": pair_pass,
        "mere_paraphrase_count": paraphrase,
        "non_evidence_exact_line_overlap_count": exact,
        "invalid_reference_count": invalid,
        "unsupported_fact_count": unsupported,
        "reroll_count": 0,
        "replacement_count": 0,
        "per_candidate_manual_patch_count": 0,
        "calibration_pass": False,
        "hidden_created_count": 0,
        "generator_qualified": False,
        "accepted_baseline_count": 120,
    }
    for key, expected in expected_result.items():
        if result.get(key) != expected:
            errors.append(f"E_STOPPED_CALIBRATION_RESULT:{key}")
    if raw_quality_pass >= 13 or unsupported == 0:
        errors.append("E_STOPPED_CALIBRATION_FAILURE_NOT_PROVEN")
    errors.extend(digest_field_errors(result, "result_digest", "calibration_result"))
    task_result_path = ROOT / TASK_DIR / "b_lane_dev_gate_result.v0.1.yaml"
    if not task_result_path.is_file():
        errors.append("E_STOPPED_TASK_RESULT_MISSING")
    else:
        task_result = load_yaml(task_result_path).get("execution_result", {})
        if task_result.get("verdict") != "STOPPED_PAIR_CALIBRATION_FAILED":
            errors.append("E_STOPPED_TASK_RESULT_VERDICT")
        if (
            task_result.get("pair_calibration", {}).get("raw_quality_pass_count")
            != raw_quality_pass
        ):
            errors.append("E_STOPPED_TASK_RESULT_RAW_QUALITY")
        if (
            task_result.get("pair_calibration", {}).get("unsupported_fact_count")
            != unsupported
        ):
            errors.append("E_STOPPED_TASK_RESULT_UNSUPPORTED_FACTS")
        if (
            task_result.get("new_dev_gate", {}).get("status")
            != "NOT_CREATED_DUE_TO_CALIBRATION_FAILURE"
        ):
            errors.append("E_STOPPED_TASK_RESULT_DEV_STATUS")
        errors.extend(digest_field_errors(task_result, "result_digest", "task_result"))
    if (ROOT / FREEZE_PATH).exists():
        errors.append("E_CORE_FROZEN_AFTER_CALIBRATION_FAILURE")
    dev_files = [path for path in (ROOT / DEV_DIR).rglob("*") if path.is_file()]
    if dev_files:
        errors.append("E_DEV_CREATED_AFTER_CALIBRATION_FAILURE")
    return errors


def lane_spec(pack: Mapping[str, Any], lane: str) -> Mapping[str, Any]:
    lanes = pack.get("lane_specs")
    if not isinstance(lanes, Mapping) or not isinstance(lanes.get(lane), Mapping):
        return {}
    return lanes[lane]


def obligation_ids(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        str(item.get("obligation_id"))
        for item in value
        if isinstance(item, Mapping) and item.get("obligation_id")
    }


def affordance_errors(pack: Mapping[str, Any]) -> list[str]:
    label = str(pack.get("profile_id", "UNKNOWN"))
    errors: list[str] = []
    atoms = {
        str(item.get("atom_id")): item
        for item in pack.get("source_atoms", [])
        if isinstance(item, Mapping) and item.get("atom_id")
    }
    shared = string_set(pack.get("shared_truth_anchor_refs"))
    if not atoms or not shared or not shared.issubset(atoms):
        errors.append(f"E_AFFORDANCE_SHARED_ANCHORS:{label}")
    if not obligation_ids(pack.get("product_invariants")):
        errors.append(f"E_AFFORDANCE_PRODUCT_INVARIANTS:{label}")
    evidence: dict[str, set[str]] = {}
    exclusive: dict[str, set[str]] = {}
    obligations: dict[str, set[str]] = {}
    for lane in ("A", "B"):
        spec = lane_spec(pack, lane)
        for field in SEMANTIC_FIELDS:
            if not str(spec.get(field, "")).strip():
                errors.append(f"E_AFFORDANCE_SEMANTIC_FIELD:{label}:{lane}:{field}")
        evidence[lane] = string_set(spec.get("evidence_atom_refs"))
        exclusive[lane] = string_set(spec.get("exclusive_atom_refs"))
        obligations[lane] = obligation_ids(spec.get("lane_story_obligations"))
        if not evidence[lane] or not evidence[lane].issubset(atoms):
            errors.append(f"E_AFFORDANCE_EVIDENCE_REFS:{label}:{lane}")
        if len(exclusive[lane]) < 2 or not exclusive[lane].issubset(evidence[lane]):
            errors.append(f"E_AFFORDANCE_EXCLUSIVE_ATOMS:{label}:{lane}")
        if len(obligations[lane]) < 2:
            errors.append(f"E_AFFORDANCE_EXCLUSIVE_OBLIGATIONS:{label}:{lane}")
        if spec.get("independently_delivers_profile_core") is not True:
            errors.append(f"E_AFFORDANCE_CORE_NOT_DELIVERED:{label}:{lane}")
    for field in SEMANTIC_FIELDS:
        if (
            str(lane_spec(pack, "A").get(field, "")).strip()
            == str(lane_spec(pack, "B").get(field, "")).strip()
        ):
            errors.append(f"E_AFFORDANCE_SEMANTIC_SAME:{label}:{field}")
    if evidence.get("A") == evidence.get("B"):
        errors.append(f"E_AFFORDANCE_SINGLE_STORY_EVIDENCE:{label}")
    if obligations.get("A") == obligations.get("B"):
        errors.append(f"E_AFFORDANCE_SINGLE_STORY_OBLIGATIONS:{label}")
    if exclusive.get("A", set()).intersection(exclusive.get("B", set())):
        errors.append(f"E_AFFORDANCE_EXCLUSIVE_OVERLAP:{label}")
    if canonical_json(lane_spec(pack, "A").get("narrative_operator")) == canonical_json(
        lane_spec(pack, "B").get("narrative_operator")
    ):
        errors.append(f"E_AFFORDANCE_SINGLE_STORY_OPERATOR:{label}")
    non_anchor_a = evidence.get("A", set()).difference(shared)
    non_anchor_b = evidence.get("B", set()).difference(shared)
    union = non_anchor_a.union(non_anchor_b)
    jaccard = len(non_anchor_a.intersection(non_anchor_b)) / max(1, len(union))
    if jaccard > 0.50:
        errors.append(f"E_AFFORDANCE_NON_ANCHOR_JACCARD:{label}")
    return errors


def affordance_claim_errors(pack: Mapping[str, Any], claimed: str) -> list[str]:
    computed_errors = affordance_errors(pack)
    declared = str(pack.get("declared_affordance", "PAIR_READY"))
    if not computed_errors:
        return (
            [] if claimed == "PAIR_READY" else ["E_AFFORDANCE_PAIR_READY_UNDERCLAIMED"]
        )
    if claimed == "PAIR_READY":
        return ["E_PAIR_READY_NOT_INDEPENDENTLY_PROVEN"]
    if (
        claimed not in {"SINGLE_LANE_ONLY", "REQUEST_MORE_MATERIAL"}
        or claimed != declared
    ):
        return ["E_AFFORDANCE_NON_PAIR_ROUTE_MISMATCH"]
    return []


def plan_pair_errors(plan_a: Mapping[str, Any], plan_b: Mapping[str, Any]) -> list[str]:
    label = str(plan_a.get("profile_id", "UNKNOWN"))
    errors: list[str] = []
    if plan_a.get("profile_id") != plan_b.get("profile_id"):
        errors.append(f"E_PLAN_PROFILE_MISMATCH:{label}")
    if plan_a.get("voice_lane") != "A" or plan_b.get("voice_lane") != "B":
        errors.append(f"E_PLAN_LANE_IDENTITY:{label}")
    contract_a = plan_a.get("semantic_divergence_contract", {})
    contract_b = plan_b.get("semantic_divergence_contract", {})
    if not isinstance(contract_a, Mapping) or not isinstance(contract_b, Mapping):
        return [f"E_PLAN_SEMANTIC_CONTRACT:{label}"]
    for field in SEMANTIC_FIELDS:
        left = str(contract_a.get(field, "")).strip()
        right = str(contract_b.get(field, "")).strip()
        if not left or not right or left == right:
            errors.append(f"E_PLAN_SEMANTIC_SAME:{label}:{field}")
    evidence_a = string_set(plan_a.get("selected_evidence_atom_refs"))
    evidence_b = string_set(plan_b.get("selected_evidence_atom_refs"))
    if evidence_a == evidence_b:
        errors.append(f"E_PLAN_EVIDENCE_SUBSET_IDENTICAL:{label}")
    obligations_a = string_set(plan_a.get("lane_story_obligation_ids"))
    obligations_b = string_set(plan_b.get("lane_story_obligation_ids"))
    if len(obligations_a) < 2 or len(obligations_b) < 2:
        errors.append(f"E_PLAN_EXCLUSIVE_OBLIGATIONS_INSUFFICIENT:{label}")
    if obligations_a.intersection(obligations_b):
        errors.append(f"E_PLAN_EXCLUSIVE_OBLIGATIONS_OVERLAP:{label}")
    style_a = plan_a.get("style_realization_plan", {})
    style_b = plan_b.get("style_realization_plan", {})
    visible = 0
    for axis in STYLE_AXES:
        left = style_a.get(axis, {}) if isinstance(style_a, Mapping) else {}
        right = style_b.get(axis, {}) if isinstance(style_b, Mapping) else {}
        left_value = left.get("selected_value") if isinstance(left, Mapping) else None
        right_value = (
            right.get("selected_value") if isinstance(right, Mapping) else None
        )
        visible += int(bool(left_value and right_value and left_value != right_value))
    if visible < 4:
        errors.append(f"E_PLAN_VISIBLE_DIFFERENCE_BELOW_4:{label}")
    return errors


def projection_errors(
    pack: Mapping[str, Any], projection: Mapping[str, Any], lane: str
) -> list[str]:
    label = f"{pack.get('profile_id')}:{lane}"
    spec = lane_spec(pack, lane)
    shared = string_set(pack.get("shared_truth_anchor_refs"))
    evidence = string_set(spec.get("evidence_atom_refs"))
    expected_refs = shared.union(evidence)
    atoms = {
        str(item.get("atom_id"))
        for item in projection.get("source_atoms", [])
        if isinstance(item, Mapping)
    }
    errors: list[str] = []
    if projection.get("source_material_pack_ref") != pack.get("material_pack_id"):
        errors.append(f"E_PROJECTION_PARENT_REF:{label}")
    if projection.get("profile_id") != pack.get("profile_id") or atoms != expected_refs:
        errors.append(f"E_PROJECTION_EVIDENCE_SET:{label}")
    if string_set(projection.get("lane_exclusive_atom_refs")) != string_set(
        spec.get("exclusive_atom_refs")
    ):
        errors.append(f"E_PROJECTION_EXCLUSIVE_SET:{label}")
    for key in (
        "other_lane_evidence_visible",
        "other_lane_plan_visible",
        "runtime_consumable",
        "publishable",
    ):
        if projection.get(key) is not False:
            errors.append(f"E_PROJECTION_BOUNDARY:{label}:{key}")
    errors.extend(
        digest_field_errors(projection, "material_pack_digest", f"projection:{label}")
    )
    return errors


def plan_binding_errors(
    pack: Mapping[str, Any],
    projection: Mapping[str, Any],
    plan: Mapping[str, Any],
    lane: str,
) -> list[str]:
    label = f"{pack.get('profile_id')}:{lane}"
    spec = lane_spec(pack, lane)
    errors: list[str] = []
    expected_obligations = obligation_ids(pack.get("product_invariants")).union(
        obligation_ids(spec.get("lane_story_obligations"))
    )
    if plan.get("voice_lane") != lane or plan.get("profile_id") != pack.get(
        "profile_id"
    ):
        errors.append(f"E_PLAN_BINDING_IDENTITY:{label}")
    if plan.get("material_pack_ref") != projection.get("material_pack_id") or plan.get(
        "material_pack_digest"
    ) != projection.get("material_pack_digest"):
        errors.append(f"E_PLAN_PROJECTION_BINDING:{label}")
    if string_set(plan.get("selected_evidence_atom_refs")) != string_set(
        spec.get("evidence_atom_refs")
    ):
        errors.append(f"E_PLAN_SELECTED_EVIDENCE:{label}")
    if string_set(plan.get("lane_exclusive_atom_refs")) != string_set(
        spec.get("exclusive_atom_refs")
    ):
        errors.append(f"E_PLAN_EXCLUSIVE_ATOMS:{label}")
    if string_set(plan.get("lane_story_obligation_ids")) != obligation_ids(
        spec.get("lane_story_obligations")
    ):
        errors.append(f"E_PLAN_STORY_OBLIGATIONS:{label}")
    if obligation_ids(plan.get("required_obligations")) != expected_obligations:
        errors.append(f"E_PLAN_REQUIRED_OBLIGATIONS:{label}")
    contract = plan.get("semantic_divergence_contract", {})
    if not isinstance(contract, Mapping) or any(
        contract.get(field) != spec.get(field) for field in SEMANTIC_FIELDS
    ):
        errors.append(f"E_PLAN_SEMANTIC_BINDING:{label}")
    errors.extend(digest_field_errors(plan, "plan_digest", f"plan:{label}"))
    return errors


def request_errors(
    request: Mapping[str, Any], plan: Mapping[str, Any], projection: Mapping[str, Any]
) -> list[str]:
    label = str(request.get("request_id", "UNKNOWN"))
    errors = sensitive_payload_errors(request, label)
    contract = request.get("content_product_contract", {})
    voice = request.get("voice_contract", {})
    expected = {
        "task_id": TASK_ID,
        "assignment_id": plan.get("assignment_id"),
        "plan_ref": plan.get("plan_id"),
        "plan_digest": plan.get("plan_digest"),
        "material_pack_ref": projection.get("material_pack_id"),
        "material_pack_digest": projection.get("material_pack_digest"),
    }
    for key, value in expected.items():
        if request.get(key) != value:
            errors.append(f"E_REQUEST_BINDING:{label}:{key}")
    if not isinstance(contract, Mapping) or contract.get("profile_id") != plan.get(
        "profile_id"
    ):
        errors.append(f"E_REQUEST_PROFILE:{label}")
    if isinstance(contract, Mapping) and contract.get(
        "required_obligations"
    ) != plan.get("required_obligations"):
        errors.append(f"E_REQUEST_OBLIGATIONS:{label}")
    if not isinstance(voice, Mapping) or voice.get("voice_lane") != plan.get(
        "voice_lane"
    ):
        errors.append(f"E_REQUEST_LANE:{label}")
    if request.get("immutable_evidence_atoms") != projection.get("source_atoms"):
        errors.append(f"E_REQUEST_EVIDENCE_PROJECTION:{label}")
    if request.get("style_realization_plan") != plan.get("style_realization_plan"):
        errors.append(f"E_REQUEST_STYLE_PLAN:{label}")
    isolation = request.get("pair_isolation_contract", {})
    if (
        not isinstance(isolation, Mapping)
        or not isolation
        or any(value is not False for value in isolation.values())
    ):
        errors.append(f"E_REQUEST_PAIR_ISOLATION:{label}")
    errors.extend(digest_field_errors(request, "request_digest", f"request:{label}"))
    return errors


def walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from walk_strings(child)
    elif isinstance(value, str):
        yield value


def cross_lane_leak_errors(
    request: Mapping[str, Any],
    sibling_plan: Mapping[str, Any],
    sibling_candidate: Mapping[str, Any] | None,
) -> list[str]:
    label = str(request.get("request_id", "UNKNOWN"))
    rendered = canonical_json(request)
    tokens = [
        sibling_plan.get("plan_id"),
        sibling_plan.get("plan_digest"),
        sibling_plan.get("assignment_id"),
    ]
    errors = [
        f"E_CROSS_LANE_PLAN_LEAK:{label}"
        for token in tokens
        if token and str(token) in rendered
    ]
    if sibling_candidate is not None:
        for binding in sibling_candidate.get("surface_bindings", []):
            if not isinstance(binding, Mapping) or binding.get("source_atom_refs"):
                continue
            text = str(binding.get("text", ""))
            if text and text in rendered:
                errors.append(f"E_CROSS_LANE_OUTPUT_LEAK:{label}")
                break
    return sorted(set(errors))


def rewrite_path_errors(value: Any, label: str) -> list[str]:
    errors: list[str] = []

    def walk(child: Any, path: tuple[str, ...]) -> None:
        if isinstance(child, Mapping):
            for raw_key, nested in child.items():
                key = normalized_key(str(raw_key))
                rendered = ".".join((*path, str(raw_key)))
                if "rewrite" in key or "paraphrase" in key:
                    errors.append(f"E_REWRITE_PATH:{label}:{rendered}")
                if (
                    key in {"generation_mode", "derivation_mode", "authoring_mode"}
                    and isinstance(nested, str)
                    and any(
                        token in normalized_key(nested)
                        for token in ("rewrite", "paraphrase")
                    )
                ):
                    errors.append(f"E_REWRITE_PATH:{label}:{rendered}")
                walk(nested, (*path, str(raw_key)))
        elif isinstance(child, Sequence) and not isinstance(
            child, (str, bytes, bytearray)
        ):
            for index, nested in enumerate(child):
                walk(nested, (*path, f"[{index}]"))

    walk(value, ())
    return sorted(set(errors))


def surface_map(response: Mapping[str, Any]) -> dict[str, str]:
    surfaces = response.get("surfaces")
    if not isinstance(surfaces, Mapping):
        return {}
    result: dict[str, str] = {}
    for field in SURFACE_SCALAR_FIELDS:
        value = surfaces.get(field)
        if value is None:
            value = ""
        if isinstance(value, str):
            result[f"surfaces.{field}"] = value
    for field in SURFACE_LIST_FIELDS:
        values = surfaces.get(field)
        if isinstance(values, list):
            for index, value in enumerate(values):
                if isinstance(value, str):
                    result[f"surfaces.{field}[{index}]"] = value
    return result


def canonical_surface_reference(value: str) -> str:
    if not value.startswith("/surfaces/"):
        return value
    tokens = [
        token.replace("~1", "/").replace("~0", "~") for token in value.split("/")[1:]
    ]
    result = tokens[0]
    for token in tokens[1:]:
        result += f"[{token}]" if token.isdigit() else f".{token}"
    return result


def normalize_response_references(response: Mapping[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(dict(response))
    for binding in normalized.get("surface_bindings", []):
        binding["surface_path"] = canonical_surface_reference(
            str(binding.get("surface_path", ""))
        )
    for collection in ("style_realization_evidence", "required_obligation_evidence"):
        for item in normalized.get(collection, []):
            item["actual_surface_refs"] = [
                canonical_surface_reference(str(ref))
                for ref in item.get("actual_surface_refs", [])
            ]
    return normalized


def response_reference_errors(
    request: Mapping[str, Any], response: Mapping[str, Any]
) -> list[str]:
    response = normalize_response_references(response)
    label = str(response.get("response_id", "UNKNOWN"))
    errors: list[str] = []
    if response.get("request_id") != request.get("request_id"):
        errors.append(f"E_RESPONSE_REQUEST_ID:{label}")
    if response.get("request_digest") != request.get("request_digest"):
        errors.append(f"E_RESPONSE_REQUEST_DIGEST:{label}")
    expected_flags = {
        "backend_class": "CONTROLLED_EXECUTION_AGENT",
        "one_request_one_response": True,
        "paired_output_visible": False,
        "review_envelope_visible": False,
        "expected_score_visible": False,
        "chain_of_thought_stored": False,
    }
    for key, value in expected_flags.items():
        if response.get(key) != value:
            errors.append(f"E_RESPONSE_ISOLATION:{label}:{key}")
    surfaces = surface_map(response)
    if not surfaces:
        errors.append(f"E_RESPONSE_SURFACES_EMPTY:{label}")
    atom_ids = {
        str(item.get("atom_id"))
        for item in request.get("immutable_evidence_atoms", [])
        if isinstance(item, Mapping)
    }
    licenses = string_set(request.get("creative_license"))
    bindings = response.get("surface_bindings")
    if not isinstance(bindings, list):
        return [*errors, f"E_RESPONSE_BINDINGS_TYPE:{label}"]
    paths: list[str] = []
    for binding in bindings:
        if not isinstance(binding, Mapping):
            errors.append(f"E_RESPONSE_BINDING_SHAPE:{label}")
            continue
        path = str(binding.get("surface_path", ""))
        paths.append(path)
        if path not in surfaces:
            errors.append(f"E_RESPONSE_SURFACE_REF:{label}:{path}")
            continue
        if binding.get("text") != surfaces[path]:
            errors.append(f"E_RESPONSE_EXACT_JOIN:{label}:{path}")
        refs = binding.get("source_atom_refs")
        if not isinstance(refs, list) or not string_set(refs).issubset(atom_ids):
            errors.append(f"E_RESPONSE_SOURCE_REF:{label}:{path}")
        elif not refs and binding.get("semantic_license") not in licenses:
            errors.append(f"E_RESPONSE_CREATIVE_LICENSE:{label}:{path}")
        elif refs and not binding.get("semantic_license"):
            errors.append(f"E_RESPONSE_SEMANTIC_LICENSE:{label}:{path}")
    for path, count in Counter(paths).items():
        if count != 1:
            errors.append(f"E_RESPONSE_BINDING_COUNT:{label}:{path}")
    for path in set(surfaces).difference(paths):
        errors.append(f"E_RESPONSE_UNBOUND_SURFACE:{label}:{path}")
    style = response.get("style_realization_evidence")
    style_map = (
        {str(item.get("axis")): item for item in style if isinstance(item, Mapping)}
        if isinstance(style, list)
        else {}
    )
    for axis in STYLE_AXES:
        item = style_map.get(axis)
        refs = item.get("actual_surface_refs") if isinstance(item, Mapping) else None
        if (
            not isinstance(refs, list)
            or not refs
            or not string_set(refs).issubset(surfaces)
        ):
            errors.append(f"E_RESPONSE_STYLE_REF:{label}:{axis}")
    obligations = request.get("content_product_contract", {}).get(
        "required_obligations", []
    )
    required = obligation_ids(obligations)
    evidence = response.get("required_obligation_evidence")
    evidence_map = (
        {
            str(item.get("obligation_id")): item
            for item in evidence
            if isinstance(item, Mapping)
        }
        if isinstance(evidence, list)
        else {}
    )
    if set(evidence_map) != required:
        errors.append(f"E_RESPONSE_OBLIGATION_SET:{label}")
    for obligation_id, item in evidence_map.items():
        refs = item.get("actual_surface_refs")
        if (
            not isinstance(refs, list)
            or not refs
            or not string_set(refs).issubset(surfaces)
        ):
            errors.append(f"E_RESPONSE_OBLIGATION_REF:{label}:{obligation_id}")
    return sorted(set(errors))


def candidate_errors(
    request: Mapping[str, Any],
    response: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> list[str]:
    label = str(candidate.get("candidate_id", "UNKNOWN"))
    ref_errors = response_reference_errors(request, response)
    response = normalize_response_references(response)
    errors: list[str] = []
    expected = {
        "request_id": request.get("request_id"),
        "request_digest": request.get("request_digest"),
        "assignment_id": request.get("assignment_id"),
        "profile_id": request.get("content_product_contract", {}).get("profile_id"),
        "voice_lane": request.get("voice_contract", {}).get("voice_lane"),
        "material_pack_ref": request.get("material_pack_ref"),
        "plan_ref": request.get("plan_ref"),
        "surfaces": response.get("surfaces"),
        "surface_bindings": response.get("surface_bindings"),
        "style_realization_evidence": response.get("style_realization_evidence"),
        "required_obligation_evidence": response.get("required_obligation_evidence"),
    }
    for key, value in expected.items():
        if candidate.get(key) != value:
            errors.append(f"E_CANDIDATE_BINDING:{label}:{key}")
    if ref_errors:
        if candidate.get("machine_structural_eligible") is not False:
            errors.append(f"E_STRUCTURAL_INELIGIBLE_CLAIMED_ELIGIBLE:{label}")
    elif candidate.get("machine_structural_eligible") is not True:
        errors.append(f"E_VALID_CANDIDATE_MARKED_INELIGIBLE:{label}")
    errors.extend(ref_errors)
    errors.extend(
        digest_field_errors(candidate, "candidate_digest", f"candidate:{label}")
    )
    errors.extend(rewrite_path_errors(candidate, label))
    return errors


def normalized_line(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).lower()


def numeric_literal(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    nondigits = re.sub(r"[\d.,:%/\-]", "", compact)
    return bool(re.search(r"\d", compact)) and len(nondigits) <= 2


def non_evidence_exact_overlap_errors(
    candidate_a: Mapping[str, Any], candidate_b: Mapping[str, Any]
) -> list[str]:
    def indexed(candidate: Mapping[str, Any]) -> dict[str, list[tuple[str, set[str]]]]:
        result: dict[str, list[tuple[str, set[str]]]] = {}
        for item in candidate.get("surface_bindings", []):
            if not isinstance(item, Mapping):
                continue
            text = str(item.get("text", ""))
            normalized = normalized_line(text)
            if normalized:
                result.setdefault(normalized, []).append(
                    (text, string_set(item.get("source_atom_refs")))
                )
        return result

    left = indexed(candidate_a)
    right = indexed(candidate_b)
    errors: list[str] = []
    for line in left.keys() & right.keys():
        legal = any(
            bool(refs_a.intersection(refs_b))
            or (refs_a and refs_b and numeric_literal(text_a))
            for text_a, refs_a in left[line]
            for _, refs_b in right[line]
        )
        if not legal:
            errors.append(
                f"E_NON_EVIDENCE_EXACT_LINE_OVERLAP:{candidate_a.get('profile_id')}:{line[:24]}"
            )
    return errors


def ngrams(text: str, size: int = 8) -> set[str]:
    normalized = normalized_line(text)
    return {
        normalized[index : index + size]
        for index in range(max(0, len(normalized) - size + 1))
    }


def all_surface_text(candidate: Mapping[str, Any]) -> str:
    return "\n".join(
        str(value) for value in surface_map(candidate).values() if str(value)
    )


def pair_machine_values(
    candidate_a: Mapping[str, Any], candidate_b: Mapping[str, Any]
) -> tuple[int, float]:
    left = all_surface_text(candidate_a)
    right = all_surface_text(candidate_b)
    exact = len(
        {line.strip() for line in left.splitlines() if line.strip()}
        & {line.strip() for line in right.splitlines() if line.strip()}
    )
    left_grams = ngrams(left)
    right_grams = ngrams(right)
    overlap = len(left_grams & right_grams) / max(
        1, min(len(left_grams), len(right_grams))
    )
    return exact, round(overlap, 6)


def lifecycle_errors(result: Mapping[str, Any], *, hidden_present: bool) -> list[str]:
    errors = boundary_errors(result, "execution_result")
    if result.get("verdict") != "EXECUTED_PENDING_GUARDIAN":
        errors.append("E_RESULT_VERDICT")
    if result.get("development_gate_status") != "PENDING_EXTERNAL_GUARDIAN":
        errors.append("E_DEVELOPMENT_GATE_WASHED_PASS")
    for key in (
        "first_acceptance_count",
        "lane_A_first_acceptance_count",
        "lane_B_first_acceptance_count",
        "independent_pair_pass_count",
    ):
        if result.get(key) is not None:
            errors.append(f"E_MACHINE_WRITES_HUMAN_VERDICT:{key}")
    if result.get("machine_content_quality_pass_claimed") is not False:
        errors.append("E_MACHINE_QUALITY_PASS_CLAIM")
    if hidden_present or result.get("hidden_created_count") != 0:
        errors.append("E_HIDDEN_AFTER_DEVELOPMENT_GATE")
    return errors


def required_dev_paths() -> dict[str, Path]:
    return {
        "packs": DEV_DIR / "material_packs.v0.1.jsonl",
        "projections": DEV_DIR / "projected_material_packs.v0.1.jsonl",
        "plans": DEV_DIR / "composition_plans.v0.1.jsonl",
        "requests": DEV_DIR / "authoring_requests.v0.1.jsonl",
        "assignments": DEV_DIR / "assignments.v0.1.jsonl",
        "raw": DEV_DIR / "raw_authoring_responses.v0.1.jsonl",
        "candidates": DEV_DIR / "candidates.v0.1.jsonl",
        "machine": DEV_DIR / "machine_structural_results.v0.1.jsonl",
        "pairs": DEV_DIR / "pair_independence_machine_results.v0.1.jsonl",
        "sessions": DEV_DIR / "authoring_session_registry.v0.1.jsonl",
        "invocations": DEV_DIR / "authoring_session_audit.v0.1.jsonl",
        "result": DEV_DIR / "task_result.v0.1.yaml",
        "freeze": DEV_DIR / "authoring_input_freeze.v0.1.yaml",
    }


def profile_map() -> dict[str, dict[str, Any]]:
    registry = load_yaml(ROOT / PROFILE_PATH)["content_product_profile_registry"]
    return {str(row["content_product_type_id"]): row for row in registry["profiles"]}


def check_dev_evidence() -> list[str]:
    paths = required_dev_paths()
    missing = [
        f"E_DEV_ARTIFACT_MISSING:{path}"
        for path in paths.values()
        if not (ROOT / path).is_file()
    ]
    raw_directory = ROOT / DEV_DIR / "raw_responses"
    if not raw_directory.is_dir() or len(list(raw_directory.glob("*.json"))) != 40:
        missing.append("E_DEV_ISOLATED_RAW_FILE_COUNT")
    if missing:
        return missing
    rows = {
        key: load_jsonl(ROOT / path)
        for key, path in paths.items()
        if path.suffix == ".jsonl"
    }
    expected_counts = {
        "packs": 20,
        "projections": 40,
        "plans": 40,
        "requests": 40,
        "assignments": 20,
        "raw": 40,
        "candidates": 40,
        "machine": 40,
        "pairs": 20,
        "sessions": 40,
        "invocations": 40,
    }
    errors = [
        f"E_DEV_COUNT:{key}"
        for key, count in expected_counts.items()
        if len(rows[key]) != count
    ]
    packs = {str(row.get("profile_id")): row for row in rows["packs"]}
    if set(packs) != EXPECTED_PROFILES or len(packs) != len(rows["packs"]):
        errors.append("E_DEV_PROFILE_COVERAGE")
    profiles = profile_map()
    projections = {
        (
            str(row.get("profile_id")),
            "A" if "-LANE-A-" in str(row.get("material_pack_id")) else "B",
        ): row
        for row in rows["projections"]
    }
    plans = {
        (str(row.get("profile_id")), str(row.get("voice_lane"))): row
        for row in rows["plans"]
    }
    requests = {
        (
            str(row.get("content_product_contract", {}).get("profile_id")),
            str(row.get("voice_contract", {}).get("voice_lane")),
        ): row
        for row in rows["requests"]
    }
    candidates = {
        (str(row.get("profile_id")), str(row.get("voice_lane"))): row
        for row in rows["candidates"]
    }
    raw_by_request = {str(row.get("request_id")): row for row in rows["raw"]}
    machine_by_candidate = {
        str(row.get("candidate_id")): row for row in rows["machine"]
    }
    pair_by_profile = {str(row.get("profile_id")): row for row in rows["pairs"]}
    assignments = {str(row.get("profile_id")): row for row in rows["assignments"]}
    for profile_id, pack in sorted(packs.items()):
        if profile_id not in profiles:
            errors.append(f"E_UNKNOWN_PROFILE:{profile_id}")
            continue
        errors.extend(
            digest_field_errors(pack, "material_pack_digest", f"pack:{profile_id}")
        )
        independent_affordance = affordance_errors(pack)
        errors.extend(independent_affordance)
        assignment = assignments.get(profile_id, {})
        claim_errors = affordance_claim_errors(
            pack, str(assignment.get("affordance", {}).get("decision", ""))
        )
        errors.extend(f"{error}:{profile_id}" for error in claim_errors)
        lane_plans: dict[str, Mapping[str, Any]] = {}
        for lane in ("A", "B"):
            projection = projections.get((profile_id, lane))
            plan = plans.get((profile_id, lane))
            request = requests.get((profile_id, lane))
            candidate = candidates.get((profile_id, lane))
            if not all((projection, plan, request, candidate)):
                errors.append(f"E_DEV_JOIN_MISSING:{profile_id}:{lane}")
                continue
            assert (
                projection is not None
                and plan is not None
                and request is not None
                and candidate is not None
            )
            lane_plans[lane] = plan
            errors.extend(projection_errors(pack, projection, lane))
            errors.extend(plan_binding_errors(pack, projection, plan, lane))
            errors.extend(request_errors(request, plan, projection))
            response = raw_by_request.get(str(request.get("request_id")))
            if response is None:
                errors.append(f"E_RAW_JOIN_MISSING:{profile_id}:{lane}")
                continue
            errors.extend(candidate_errors(request, response, candidate))
            errors.extend(
                rewrite_path_errors(response, str(response.get("response_id")))
            )
            machine = machine_by_candidate.get(str(candidate.get("candidate_id")))
            if machine is None or machine.get("candidate_digest") != candidate.get(
                "candidate_digest"
            ):
                errors.append(f"E_MACHINE_JOIN:{profile_id}:{lane}")
            elif machine.get("machine_structural_eligible") is not True or machine.get(
                "validation_errors"
            ):
                errors.append(f"E_MACHINE_STRUCTURAL_FAILURE:{profile_id}:{lane}")
        if set(lane_plans) == {"A", "B"}:
            errors.extend(plan_pair_errors(lane_plans["A"], lane_plans["B"]))
            errors.extend(
                cross_lane_leak_errors(
                    requests[(profile_id, "A")],
                    lane_plans["B"],
                    candidates.get((profile_id, "B")),
                )
            )
            errors.extend(
                cross_lane_leak_errors(
                    requests[(profile_id, "B")],
                    lane_plans["A"],
                    candidates.get((profile_id, "A")),
                )
            )
        pair_a = candidates.get((profile_id, "A"))
        pair_b = candidates.get((profile_id, "B"))
        pair_row = pair_by_profile.get(profile_id)
        if pair_a is not None and pair_b is not None and pair_row is not None:
            errors.extend(non_evidence_exact_overlap_errors(pair_a, pair_b))
            exact, overlap = pair_machine_values(pair_a, pair_b)
            if pair_row.get("all_surface_exact_line_overlap_count") != exact:
                errors.append(f"E_PAIR_MACHINE_EXACT_DRIFT:{profile_id}")
            if pair_row.get("normalized_8gram_overlap_ratio") != overlap:
                errors.append(f"E_PAIR_MACHINE_NGRAM_DRIFT:{profile_id}")
        else:
            errors.append(f"E_PAIR_JOIN_MISSING:{profile_id}")
    request_ids = {str(row.get("request_id")) for row in rows["requests"]}
    sessions = rows["sessions"]
    session_ids = {str(row.get("agent_id")) for row in sessions}
    if (
        len(session_ids) != 40
        or {str(row.get("request_id")) for row in sessions} != request_ids
    ):
        errors.append("E_AUTHOR_SESSION_ISOLATION")
    invocation_ids = {
        str(row.get("controlled_execution_session_id")) for row in rows["invocations"]
    }
    if (
        len(invocation_ids) != 40
        or {str(row.get("request_id")) for row in rows["invocations"]} != request_ids
    ):
        errors.append("E_AUTHOR_INVOCATION_ISOLATION")
    for row in rows["invocations"]:
        expected = {
            "fresh_ephemeral_session": True,
            "one_request_one_response": True,
            "paired_output_visible": False,
            "reroll_count": 0,
            "replacement_count": 0,
            "external_provider_API_call_count": 0,
        }
        if any(row.get(key) != value for key, value in expected.items()):
            errors.append(f"E_AUTHOR_INVOCATION_BOUNDARY:{row.get('request_id')}")
    freeze = load_yaml(ROOT / paths["freeze"]).get("authoring_input_freeze", {})
    if (
        freeze.get("authoring_request_count") != 40
        or freeze.get("frozen_before_authoring") is not True
    ):
        errors.append("E_DEV_INPUT_FREEZE")
    for key, path_key in (
        ("material_file_digest", "packs"),
        ("plan_file_digest", "plans"),
        ("request_file_digest", "requests"),
    ):
        if freeze.get(key) != sha256_file(ROOT / paths[path_key]):
            errors.append(f"E_DEV_INPUT_FREEZE_DIGEST:{key}")
    errors.extend(digest_field_errors(freeze, "freeze_digest", "dev_input_freeze"))
    result = load_yaml(ROOT / paths["result"]).get("execution_result", {})
    errors.extend(lifecycle_errors(result, hidden_present=bool(hidden_paths())))
    expected_result_counts = {
        "material_pack_count": 20,
        "assignment_count": 40,
        "candidate_count": 40,
        "lane_A_count": 20,
        "lane_B_count": 20,
        "reroll_count": 0,
        "replacement_count": 0,
        "posthoc_patch_count": 0,
    }
    for key, value in expected_result_counts.items():
        if result.get(key) != value:
            errors.append(f"E_RESULT_COUNT:{key}")
    errors.extend(digest_field_errors(result, "result_digest", "execution_result"))
    return errors


def find_values(value: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if str(raw_key) == key:
                found.append(child)
            found.extend(find_values(child, key))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            found.extend(find_values(child, key))
    return found


def check_route_migration_31() -> list[str]:
    document = load_yaml(ROOT / LEDGER_PATH).get("grc_3600_execution_plan_status", {})
    route = document.get("route_migration_31")
    if not isinstance(route, Mapping):
        return ["E_ROUTE_MIGRATION_31_MISSING"]
    errors: list[str] = []
    prior = {
        key: value for key, value in document.items() if key != "route_migration_31"
    }
    if digest_object(prior) != LEDGER_WITHOUT_ROUTE31_DIGEST:
        errors.append("E_LEDGER_NON_ADDITIVE_BEFORE_ROUTE31")
    if digest_object(document.get("route_migration_30")) != ROUTE30_DIGEST:
        errors.append("E_ROUTE_MIGRATION_30_DRIFT")
    route_body = dict(route)
    claimed = route_body.pop("migration_digest", None)
    if claimed != digest_object(route_body):
        errors.append("E_ROUTE_MIGRATION_31_DIGEST")
    if route.get("applied_by_task") != TASK_ID:
        errors.append("E_ROUTE_MIGRATION_31_TASK")
    if (
        route.get("additive_only") is not True
        or route.get("no_readiness_flipped") is not True
    ):
        errors.append("E_ROUTE_MIGRATION_31_ADDITIVE_FLAGS")
    required_boundaries = {
        "accepted_baseline_increment_count": 0,
        "accepted_baseline_count": 120,
        "hidden_created_count": 0,
        "generator_qualified": False,
        "external_provider_API_call_count": 0,
        "runtime_ingest_ready": False,
    }
    for key, expected in required_boundaries.items():
        values = find_values(route, key)
        if not values or any(value != expected for value in values):
            errors.append(f"E_ROUTE_MIGRATION_31_BOUNDARY:{key}")
    rendered_keys = " ".join(normalized_key(str(key)) for key in route for _ in (0,))
    rendered_all = normalized_key(canonical_json(route))
    markers = (
        ("pr9", "checker"),
        ("pr9", "merge"),
        ("dual", "affordance"),
        ("lane", "plan"),
        ("calibration",),
        ("development", "gate"),
    )
    for marker in markers:
        if not all(token in rendered_all or token in rendered_keys for token in marker):
            errors.append(f"E_ROUTE_MIGRATION_31_DISCLOSURE:{'+'.join(marker)}")
    errors.extend(boundary_errors(route, "route_migration_31"))
    return errors


def check_all_task_boundaries() -> list[str]:
    errors: list[str] = []
    task_root = ROOT / TASK_DIR
    for path in task_root.rglob("*.yaml"):
        errors.extend(
            boundary_errors(load_yaml(path), path.relative_to(ROOT).as_posix())
        )
    for path in task_root.rglob("*.jsonl"):
        for index, row in enumerate(load_jsonl(path), 1):
            errors.extend(boundary_errors(row, f"{path.relative_to(ROOT)}:{index}"))
    return errors


def run_live() -> list[str]:
    errors: list[str] = []
    errors.extend(check_pr9_frozen_identity())
    errors.extend(materializer_boundary_errors())
    errors.extend(check_all_task_boundaries())
    if hidden_paths():
        errors.append("E_HIDDEN_OBJECT_PRESENT")
    calibration_path = ROOT / CAL_DIR / "calibration_result.v0.1.yaml"
    calibration = (
        load_yaml(calibration_path).get("calibration_result", {})
        if calibration_path.exists()
        else {}
    )
    if calibration.get("calibration_pass") is False:
        errors.extend(check_stopped_calibration())
        errors.extend(check_route_migration_31())
        return sorted(set(errors))
    errors.extend(check_task_core_freeze())
    dev_started = (ROOT / DEV_DIR / "authoring_input_freeze.v0.1.yaml").exists()
    if dev_started:
        errors.extend(check_dev_evidence())
        errors.extend(check_route_migration_31())
    else:
        ledger = load_yaml(ROOT / LEDGER_PATH).get("grc_3600_execution_plan_status", {})
        if "route_migration_31" in ledger:
            errors.append("E_ROUTE_MIGRATION_31_BEFORE_DEV_EVIDENCE")
    return sorted(set(errors))


def fixture_pack() -> dict[str, Any]:
    atoms = [
        {
            "atom_id": atom_id,
            "atom_type": "fact",
            "text": atom_id,
            "source_ref": f"fixture://{atom_id}",
            "authorization_ref": "sim://ok",
        }
        for atom_id in ("S1", "S2", "A1", "A2", "B1", "B2")
    ]
    styles_a = {axis: {"selected_value": f"A-{axis}"} for axis in STYLE_AXES}
    styles_b = {axis: {"selected_value": f"B-{axis}"} for axis in STYLE_AXES}
    pack: dict[str, Any] = {
        "material_pack_id": "MP-CP14",
        "profile_id": "CP14",
        "source_atoms": atoms,
        "shared_truth_anchor_refs": ["S1", "S2"],
        "product_invariants": [{"obligation_id": "INV-1"}],
        "lane_specs": {
            "A": {
                "primary_audience_question": "A question",
                "observation_mission": "A mission",
                "center_of_gravity": "A center",
                "causal_path": "A cause",
                "evidence_atom_refs": ["S1", "A1", "A2"],
                "exclusive_atom_refs": ["A1", "A2"],
                "lane_story_obligations": [
                    {"obligation_id": "A-O1"},
                    {"obligation_id": "A-O2"},
                ],
                "independently_delivers_profile_core": True,
                "narrative_operator": {"mode": "professional"},
                "style_realization_plan": styles_a,
            },
            "B": {
                "primary_audience_question": "B question",
                "observation_mission": "B mission",
                "center_of_gravity": "B center",
                "causal_path": "B cause",
                "evidence_atom_refs": ["S2", "B1", "B2"],
                "exclusive_atom_refs": ["B1", "B2"],
                "lane_story_obligations": [
                    {"obligation_id": "B-O1"},
                    {"obligation_id": "B-O2"},
                ],
                "independently_delivers_profile_core": True,
                "narrative_operator": {"mode": "ordinary"},
                "style_realization_plan": styles_b,
            },
        },
        "declared_affordance": "PAIR_READY",
    }
    pack["material_pack_digest"] = digest_object(pack)
    return pack


def fixture_plan(pack: Mapping[str, Any], lane: str) -> dict[str, Any]:
    spec = lane_spec(pack, lane)
    obligations = [*pack["product_invariants"], *spec["lane_story_obligations"]]
    plan: dict[str, Any] = {
        "plan_id": f"PLAN-{lane}",
        "assignment_id": f"ASSIGN-{lane}",
        "profile_id": "CP14",
        "voice_lane": lane,
        "material_pack_ref": f"PROJECTION-{lane}",
        "material_pack_digest": f"projection-digest-{lane}",
        "required_obligations": obligations,
        "lane_story_obligation_ids": [
            row["obligation_id"] for row in spec["lane_story_obligations"]
        ],
        "selected_evidence_atom_refs": spec["evidence_atom_refs"],
        "lane_exclusive_atom_refs": spec["exclusive_atom_refs"],
        "semantic_divergence_contract": {
            field: spec[field] for field in SEMANTIC_FIELDS
        },
        "style_realization_plan": spec["style_realization_plan"],
    }
    plan["plan_digest"] = digest_object(plan)
    return plan


def fixture_request(pack: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    lane = str(plan["voice_lane"])
    atom_ids = string_set(lane_spec(pack, lane)["evidence_atom_refs"]).union(
        string_set(pack["shared_truth_anchor_refs"])
    )
    request: dict[str, Any] = {
        "task_id": TASK_ID,
        "request_id": f"REQUEST-{lane}",
        "assignment_id": plan["assignment_id"],
        "plan_ref": plan["plan_id"],
        "plan_digest": plan["plan_digest"],
        "material_pack_ref": plan["material_pack_ref"],
        "material_pack_digest": plan["material_pack_digest"],
        "content_product_contract": {
            "profile_id": "CP14",
            "required_obligations": plan["required_obligations"],
        },
        "voice_contract": {"voice_lane": lane},
        "immutable_evidence_atoms": [
            row for row in pack["source_atoms"] if row["atom_id"] in atom_ids
        ],
        "creative_license": ["STRUCTURAL_LANGUAGE", "EVIDENCE_BOUND_EXPRESSION"],
        "style_realization_plan": plan["style_realization_plan"],
        "pair_isolation_contract": {
            "other_lane_plan_visibility": False,
            "other_lane_selected_atoms_visibility": False,
            "other_lane_request_visibility": False,
            "other_lane_response_visibility": False,
            "other_lane_candidate_visibility": False,
        },
        "isolation_contract": {
            "expected_score_visibility": False,
            "review_envelope_visibility": False,
            "sibling_candidate_visibility": False,
        },
    }
    request["request_digest"] = digest_object(request)
    return request


def fixture_response(request: Mapping[str, Any], lane: str) -> dict[str, Any]:
    surfaces = {
        "title": f"{lane} title",
        "body_blocks": [f"{lane} body"],
        "spoken_lines": [],
        "CTA": "",
        "visual_beats": [f"{lane} visual"],
        "capture_instructions": [f"{lane} capture"],
        "audio_grammar": f"{lane} audio",
        "editing_grammar": f"{lane} editing",
    }
    leaves = surface_map({"surfaces": surfaces})
    atom = request["immutable_evidence_atoms"][0]["atom_id"]
    bindings = [
        {
            "surface_path": path,
            "text": text,
            "source_atom_refs": [atom],
            "semantic_license": "EVIDENCE_BOUND_EXPRESSION",
        }
        for path, text in leaves.items()
    ]
    body_ref = ["surfaces.body_blocks[0]"]
    return {
        "response_id": f"CAND-{lane}",
        "request_id": request["request_id"],
        "request_digest": request["request_digest"],
        "backend_class": "CONTROLLED_EXECUTION_AGENT",
        "one_request_one_response": True,
        "paired_output_visible": False,
        "review_envelope_visible": False,
        "expected_score_visible": False,
        "chain_of_thought_stored": False,
        "surfaces": surfaces,
        "surface_bindings": bindings,
        "style_realization_evidence": [
            {"axis": axis, "actual_surface_refs": body_ref} for axis in STYLE_AXES
        ],
        "required_obligation_evidence": [
            {"obligation_id": row["obligation_id"], "actual_surface_refs": body_ref}
            for row in request["content_product_contract"]["required_obligations"]
        ],
    }


def fixture_candidate(
    request: Mapping[str, Any], response: Mapping[str, Any], lane: str
) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "candidate_id": response["response_id"],
        "request_id": request["request_id"],
        "request_digest": request["request_digest"],
        "assignment_id": request["assignment_id"],
        "profile_id": "CP14",
        "voice_lane": lane,
        "material_pack_ref": request["material_pack_ref"],
        "plan_ref": request["plan_ref"],
        "surfaces": response["surfaces"],
        "surface_bindings": response["surface_bindings"],
        "style_realization_evidence": response["style_realization_evidence"],
        "required_obligation_evidence": response["required_obligation_evidence"],
        "machine_structural_eligible": True,
    }
    candidate["candidate_digest"] = digest_object(candidate)
    return candidate


def selftest() -> list[str]:
    failures: list[str] = []

    def expect_error(label: str, errors: Sequence[str], prefix: str) -> None:
        if not any(error.startswith(prefix) for error in errors):
            failures.append(f"SELFTEST_NOT_CAUGHT:{label}")

    def expect_clean(label: str, errors: Sequence[str]) -> None:
        if errors:
            failures.append(f"SELFTEST_FALSE_POSITIVE:{label}:{errors[0]}")

    pack = fixture_pack()
    plan_a = fixture_plan(pack, "A")
    plan_b = fixture_plan(pack, "B")
    request_a = fixture_request(pack, plan_a)
    request_b = fixture_request(pack, plan_b)
    response_a = fixture_response(request_a, "A")
    response_b = fixture_response(request_b, "B")
    candidate_a = fixture_candidate(request_a, response_a, "A")
    candidate_b = fixture_candidate(request_b, response_b, "B")

    single_story = copy.deepcopy(pack)
    single_story["lane_specs"]["B"]["evidence_atom_refs"] = single_story["lane_specs"][
        "A"
    ]["evidence_atom_refs"]
    single_story["lane_specs"]["B"]["lane_story_obligations"] = single_story[
        "lane_specs"
    ]["A"]["lane_story_obligations"]
    single_story["lane_specs"]["B"]["narrative_operator"] = single_story["lane_specs"][
        "A"
    ]["narrative_operator"]
    expect_error(
        "single-story-pair",
        affordance_errors(single_story),
        "E_AFFORDANCE_SINGLE_STORY",
    )
    same_question = copy.deepcopy(pack)
    same_question["lane_specs"]["B"]["primary_audience_question"] = same_question[
        "lane_specs"
    ]["A"]["primary_audience_question"]
    expect_error(
        "same-question", affordance_errors(same_question), "E_AFFORDANCE_SEMANTIC_SAME"
    )
    same_causal = copy.deepcopy(plan_b)
    same_causal["semantic_divergence_contract"]["causal_path"] = plan_a[
        "semantic_divergence_contract"
    ]["causal_path"]
    expect_error(
        "same-causal", plan_pair_errors(plan_a, same_causal), "E_PLAN_SEMANTIC_SAME"
    )
    style_only = copy.deepcopy(plan_b)
    style_only["semantic_divergence_contract"] = copy.deepcopy(
        plan_a["semantic_divergence_contract"]
    )
    style_only["selected_evidence_atom_refs"] = plan_a["selected_evidence_atom_refs"]
    style_only["lane_story_obligation_ids"] = plan_a["lane_story_obligation_ids"]
    expect_error(
        "style-only", plan_pair_errors(plan_a, style_only), "E_PLAN_SEMANTIC_SAME"
    )
    insufficient = copy.deepcopy(plan_b)
    insufficient["lane_story_obligation_ids"] = ["B-O1"]
    expect_error(
        "exclusive-insufficient",
        plan_pair_errors(plan_a, insufficient),
        "E_PLAN_EXCLUSIVE_OBLIGATIONS_INSUFFICIENT",
    )
    leak_plan = copy.deepcopy(request_b)
    leak_plan["context"] = plan_a["plan_id"]
    expect_error(
        "cross-lane-plan",
        cross_lane_leak_errors(leak_plan, plan_a, candidate_a),
        "E_CROSS_LANE_PLAN_LEAK",
    )
    leak_output = copy.deepcopy(request_b)
    leaked_binding = next(
        item
        for item in response_a["surface_bindings"]
        if item["surface_path"] == "surfaces.body_blocks[0]"
    )
    leaked_binding["source_atom_refs"] = []
    leak_output["context"] = leaked_binding["text"]
    candidate_a = fixture_candidate(request_a, response_a, "A")
    expect_error(
        "cross-lane-output",
        cross_lane_leak_errors(leak_output, plan_a, candidate_a),
        "E_CROSS_LANE_OUTPUT_LEAK",
    )
    expect_error(
        "rewrite",
        rewrite_path_errors({"derivation_mode": "PARAPHRASE"}, "test"),
        "E_REWRITE_PATH",
    )
    overlap_a = copy.deepcopy(candidate_a)
    overlap_b = copy.deepcopy(candidate_b)
    for candidate in (overlap_a, overlap_b):
        candidate["surface_bindings"][1]["text"] = "same unsupported line"
        candidate["surface_bindings"][1]["source_atom_refs"] = []
    expect_error(
        "exact-overlap",
        non_evidence_exact_overlap_errors(overlap_a, overlap_b),
        "E_NON_EVIDENCE_EXACT_LINE_OVERLAP",
    )
    bad_ref = copy.deepcopy(response_b)
    bad_ref["required_obligation_evidence"][0]["actual_surface_refs"] = [
        "surfaces.spoken_lines"
    ]
    expect_error(
        "invalid-obligation-ref",
        response_reference_errors(request_b, bad_ref),
        "E_RESPONSE_OBLIGATION_REF",
    )
    washed_candidate = fixture_candidate(request_b, bad_ref, "B")
    washed_candidate["candidate_digest"] = digest_object(
        {
            key: value
            for key, value in washed_candidate.items()
            if key != "candidate_digest"
        }
    )
    expect_error(
        "ineligible-washed-green",
        candidate_errors(request_b, bad_ref, washed_candidate),
        "E_STRUCTURAL_INELIGIBLE_CLAIMED_ELIGIBLE",
    )
    legal_visibility = {
        "expected_score_visibility": False,
        "review_envelope_visibility": False,
        "sibling_candidate_visibility": False,
    }
    expect_clean(
        "visibility-false", sensitive_payload_errors(legal_visibility, "legal")
    )
    honest_result = {
        "verdict": "EXECUTED_PENDING_GUARDIAN",
        "development_gate_status": "PENDING_EXTERNAL_GUARDIAN",
        "first_acceptance_count": None,
        "lane_A_first_acceptance_count": None,
        "lane_B_first_acceptance_count": None,
        "independent_pair_pass_count": None,
        "machine_content_quality_pass_claimed": False,
        "hidden_created_count": 0,
        "accepted_baseline_count": 120,
        "generator_qualified": False,
        "runtime_ingest_ready": False,
    }
    washed_result = {**honest_result, "development_gate_status": "PASS"}
    expect_error(
        "failure-washed-pass",
        lifecycle_errors(washed_result, hidden_present=False),
        "E_DEVELOPMENT_GATE_WASHED_PASS",
    )
    expect_error(
        "hidden-after-failure",
        lifecycle_errors(honest_result, hidden_present=True),
        "E_HIDDEN_AFTER_DEVELOPMENT_GATE",
    )
    pins = {
        OLD_FREEZE.as_posix(): OLD_FREEZE_SHA256,
        OLD_MATERIALIZER.as_posix(): OLD_MATERIALIZER_SHA256,
        (OLD_CORE / "controlled_v2_route_gate.py").as_posix(): "tampered",
        (
            OLD_CORE / "creative_author_protocol.v0.1.yaml"
        ).as_posix(): CREATIVE_PROTOCOL_SHA256,
        (
            OLD_CORE / "creative_author_instruction.v0.1.yaml"
        ).as_posix(): CREATIVE_INSTRUCTION_SHA256,
        ACTIVE_REGISTRY.as_posix(): ACTIVE_REGISTRY_SHA256,
    }
    expect_error("route-drift", check_pr9_frozen_identity(pins), "E_PR9_FROZEN_DRIFT")
    pins[(OLD_CORE / "controlled_v2_route_gate.py").as_posix()] = ROUTE_GATE_SHA256
    pins[(OLD_CORE / "creative_author_protocol.v0.1.yaml").as_posix()] = "tampered"
    expect_error(
        "creative-core-drift", check_pr9_frozen_identity(pins), "E_PR9_FROZEN_DRIFT"
    )
    expect_error(
        "baseline-increase",
        boundary_errors({"accepted_baseline_count": 121}, "test"),
        "E_BASELINE_INCREASE",
    )
    expect_error(
        "readiness-flip",
        boundary_errors({"runtime_ingest_ready": True}, "test"),
        "E_READINESS_TRUE",
    )

    expect_clean("shared-anchor-facts", affordance_errors(pack))
    shared_a = fixture_candidate(request_a, fixture_response(request_a, "A"), "A")
    shared_b = fixture_candidate(request_b, fixture_response(request_b, "B"), "B")
    for candidate in (shared_a, shared_b):
        candidate["surface_bindings"][1]["text"] = "24"
        candidate["surface_bindings"][1]["source_atom_refs"] = ["S1"]
    expect_clean(
        "shared-source-quote-or-number",
        non_evidence_exact_overlap_errors(shared_a, shared_b),
    )
    expect_clean("same-facts-divergent-tasks", plan_pair_errors(plan_a, plan_b))
    expect_clean(
        "cp14-no-spoken-cta",
        response_reference_errors(request_b, fixture_response(request_b, "B")),
    )
    single_lane = copy.deepcopy(pack)
    single_lane["declared_affordance"] = "SINGLE_LANE_ONLY"
    single_lane["lane_specs"]["B"]["exclusive_atom_refs"] = []
    expect_clean(
        "single-lane-honest",
        affordance_claim_errors(single_lane, "SINGLE_LANE_ONLY"),
    )
    more_material = copy.deepcopy(pack)
    more_material["declared_affordance"] = "REQUEST_MORE_MATERIAL"
    more_material["lane_specs"]["B"]["evidence_atom_refs"] = []
    expect_clean(
        "request-more-honest",
        affordance_claim_errors(more_material, "REQUEST_MORE_MATERIAL"),
    )
    expect_clean(
        "honest-high-quality-pair-reject",
        lifecycle_errors(honest_result, hidden_present=False),
    )
    expect_clean(
        "visibility-false-repeat", sensitive_payload_errors(request_a, "request-a")
    )
    return sorted(set(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if not __debug__:
        return 2
    try:
        errors = selftest() if args.selftest else run_live()
    except (
        KeyError,
        TypeError,
        ValueError,
        OSError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        sys.stderr.write(f"E_CHECKER_EXCEPTION:{type(exc).__name__}:{exc}\n")
        return 1
    if errors:
        for error in errors:
            sys.stderr.write(error + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
