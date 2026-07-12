#!/usr/bin/env python3
"""Materialize frozen control evidence without authoring audience text."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "CONTROLLED_V2_CREATIVE_AUTHORING_ROUTE_ORACLE_CONVERGENCE_001"
ROOT = Path(__file__).resolve().parents[2]
TASK_DIR = Path("controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001")
CORE_DIR = TASK_DIR / "core"
ROUTE_DIR = TASK_DIR / "route"
DIAGNOSTIC_DIR = TASK_DIR / "diagnostic"
REVIEW_DIR = TASK_DIR / "review"
OPEN_DIR = TASK_DIR / "dev_open_gate_001"

PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
OLD_TASK_DIR = Path(
    "controlled_content_generator_v2_001/qualification_calibration_targeted_repair_002"
)
OLD_ACTIVE_PATH = OLD_TASK_DIR / "active_authoring/controlled_v2_authoring_successor.py"
OLD_CANDIDATES_PATH = OLD_TASK_DIR / "hidden_r002_candidates.v0.1.jsonl"
OLD_RESULT_PATH = OLD_TASK_DIR / "qualification_repair_002_result.v0.1.yaml"

CONSTRAINT_COMPILER_PATH = CORE_DIR / "constraint_compiler.py"
RESPONSE_VALIDATOR_PATH = CORE_DIR / "response_validator.py"
ROUTE_GATE_PATH = CORE_DIR / "controlled_v2_route_gate.py"
AUTHOR_INSTRUCTION_PATH = CORE_DIR / "creative_author_instruction.v0.1.yaml"
AUTHOR_PROTOCOL_PATH = CORE_DIR / "creative_author_protocol.v0.1.yaml"
AUTHOR_SCHEMA_PATH = CORE_DIR / "creative_author_response.schema.json"
ACTIVE_REGISTRY_PATH = CORE_DIR / "active_authoring_registry.v0.3.yaml"
BACKEND_MANIFEST_PATH = CORE_DIR / "authoring_backend_manifest.v0.1.yaml"
ROUTE_CONTRACT_PATH = CORE_DIR / "route_gate_contract.v0.1.yaml"
RUBRIC_PATH = REVIEW_DIR / "qualification_rubric.v2.0.yaml"
REVIEW_PROTOCOL_PATH = REVIEW_DIR / "qualification_review_protocol.freeze.yaml"
ROUTE_INPUTS_PATH = ROUTE_DIR / "route_inputs.v0.1.jsonl"
ROUTE_EXPECTATIONS_PATH = ROUTE_DIR / "sealed_route_expectations.v0.1.jsonl"
ROUTE_ACTUALS_PATH = ROUTE_DIR / "route_actuals.v0.1.jsonl"
DEGRADED_ARTIFACTS_PATH = ROUTE_DIR / "degraded_internal_artifacts.v0.1.jsonl"
ROUTE_EXECUTION_PATH = ROUTE_DIR / "route_execution_manifest.v0.1.yaml"
ROUTE_COMPARISON_PATH = ROUTE_DIR / "route_comparison_results.v0.1.jsonl"
DIAGNOSTIC_PATH = DIAGNOSTIC_DIR / "development_diagnostic.v0.1.yaml"
PHASE0_BINDING_PATH = DIAGNOSTIC_DIR / "phase_0_pr8_merge_binding.v0.1.yaml"
REVIEW_DISCREPANCY_PATH = REVIEW_DIR / "historical_review_discrepancy_binding.v0.1.yaml"
FREEZE_MANIFEST_PATH = TASK_DIR / "core_freeze_manifest.v0.1.yaml"
CHECKER_PATH = Path("ci/checkers/check_controlled_v2_creative_authoring_route_convergence.py")
MATERIALIZER_PATH = TASK_DIR / "run_convergence_materializer.py"

OPEN_PACKS_PATH = OPEN_DIR / "material_packs.v0.1.jsonl"
OPEN_PLANS_PATH = OPEN_DIR / "composition_plans.v0.1.jsonl"
OPEN_REQUESTS_PATH = OPEN_DIR / "authoring_requests.v0.1.jsonl"
OPEN_INPUT_FREEZE_PATH = OPEN_DIR / "authoring_input_freeze.v0.1.yaml"
OPEN_RAW_PATH = OPEN_DIR / "raw_authoring_responses.v0.1.jsonl"
OPEN_INVOCATIONS_PATH = OPEN_DIR / "authoring_invocations.v0.1.jsonl"
OPEN_CANDIDATES_PATH = OPEN_DIR / "candidates.v0.1.jsonl"
OPEN_BLIND1_PATH = OPEN_DIR / "blind_view_1.v0.1.jsonl"
OPEN_BLIND2_PATH = OPEN_DIR / "blind_view_2.v0.1.jsonl"
OPEN_BLIND_BINDING_PATH = OPEN_DIR / "blind_view_binding.v0.1.jsonl"
OPEN_MACHINE_PATH = OPEN_DIR / "machine_structural_results.v0.1.jsonl"
OPEN_PAIR_PATH = OPEN_DIR / "pair_independence_machine_results.v0.1.jsonl"
OPEN_REVIEW_INPUT_PATH = OPEN_DIR / "development_reviewer_input_manifest.v0.1.yaml"
OPEN_PACKET_PATH = OPEN_DIR / "guardian_checkpoint_A_packet.v0.1.yaml"
OPEN_RESULT_PATH = OPEN_DIR / "checkpoint_A_result.v0.1.yaml"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def jsonl_text(rows: Iterable[Mapping[str, Any]]) -> str:
    return "".join(canonical_json(dict(row)) + "\n" for row in rows)


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected mapping in {path}")
    return value


def yaml_text(value: Mapping[str, Any]) -> str:
    return yaml.safe_dump(
        dict(value),
        allow_unicode=True,
        sort_keys=False,
        width=140,
    )


def write_text(path: Path, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def import_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile_map() -> dict[str, dict[str, Any]]:
    document = load_yaml(ROOT / PROFILE_PATH)
    profiles = document["content_product_profile_registry"]["profiles"]
    return {str(item["content_product_type_id"]): item for item in profiles}


def _update_core_metadata() -> None:
    backend = load_yaml(ROOT / BACKEND_MANIFEST_PATH)
    body = backend["authoring_backend_manifest"]
    body["instruction_digest"] = sha256_file(ROOT / AUTHOR_INSTRUCTION_PATH)
    body["constraint_compiler_digest"] = sha256_file(ROOT / CONSTRAINT_COMPILER_PATH)
    write_text(BACKEND_MANIFEST_PATH, yaml_text(backend))

    protocol = load_yaml(ROOT / REVIEW_PROTOCOL_PATH)
    protocol["qualification_review_protocol"]["rubric_digest"] = sha256_file(ROOT / RUBRIC_PATH)
    write_text(REVIEW_PROTOCOL_PATH, yaml_text(protocol))


def development_diagnostic() -> dict[str, Any]:
    source = (ROOT / OLD_ACTIVE_PATH).read_text(encoding="utf-8")
    candidates = load_jsonl(ROOT / OLD_CANDIDATES_PATH)
    old_result = load_yaml(ROOT / OLD_RESULT_PATH)
    surfaces: list[dict[str, Any]] = []
    for row in candidates:
        candidate = row.get("hidden_r002_candidate", row)
        audience = candidate.get("audience_form_candidate", {})
        execution = candidate.get("execution_payload", {})
        surfaces.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "lane": candidate.get("voice_lane"),
                "title": audience.get("title", ""),
                "body": audience.get("body", ""),
                "spoken": audience.get("spoken_lines", []),
                "CTA": audience.get("CTA", ""),
                "visual": execution.get("visual_beats", []),
                "capture": execution.get("capture_instructions", []),
                "audio": execution.get("audio_grammar", ""),
                "editing": execution.get("editing_grammar", ""),
            }
        )
    capture_counts = Counter(
        line
        for item in surfaces
        for line in item["capture"]
        if isinstance(line, str)
    )
    cta_counts = Counter(str(item["CTA"]) for item in surfaces if item["CTA"])
    report = {
        "development_diagnostic": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "source_lifecycle": "DEV-EXPOSED-FAILURE-EVIDENCE",
            "source_candidate_count": len(candidates),
            "source_result_digest": sha256_file(ROOT / OLD_RESULT_PATH),
            "old_active_module_digest": sha256_file(ROOT / OLD_ACTIVE_PATH),
            "machine_source_findings": {
                "CP_BLUEPRINTS_present": "CP_BLUEPRINTS" in source,
                "python_title_writer_present": "def _title(" in source,
                "python_body_writer_present": "def _body(" in source,
                "python_spoken_writer_present": "def _spoken(" in source,
                "python_CTA_writer_present": "def _cta(" in source,
                "CP_specific_surface_branch_present": '"CP01":' in source and '"CP20":' in source,
                "lane_B_rewrite_logic_present": 'if lane == "B"' in source,
                "index_or_modulo_surface_selection_present": "% 4" in source or "% 5" in source,
                "hidden_material_baked_into_active_core": '"hidden": {' in source,
                "most_repeated_capture_sentence_count": max(capture_counts.values(), default=0),
                "most_repeated_CTA_count": max(cta_counts.values(), default=0),
            },
            "historical_review_counts": {
                "guardian_strict_first_acceptance": 0,
                "content_expert_first_acceptance": 19,
                "review_v3_first_acceptance": 26,
                "current_qualification_state": "FAIL",
                "numbers_averaged_or_selected": False,
            },
            "diagnostic_verdict": "GLOBAL_ARCHITECTURE_REPAIR_REQUIRED",
            "per_candidate_patch_performed": False,
            "candidate_deleted_or_replaced": False,
            "generator_qualified": False,
            "accepted_baseline_count": 120,
            "source_result_reported_state": old_result,
        }
    }
    report["development_diagnostic"]["diagnostic_digest"] = digest_object(
        report["development_diagnostic"]
    )
    return report


def execute_routes() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    gate_module = import_module(ROUTE_GATE_PATH, "controlled_v2_route_gate_materializer")
    profiles = profile_map()
    inputs = load_jsonl(ROOT / ROUTE_INPUTS_PATH)
    actuals: list[dict[str, Any]] = []
    degraded: list[dict[str, Any]] = []
    actions: Counter[str] = Counter()
    for fixture in inputs:
        projection = fixture["actual_input_payload"]
        profile_id = str(fixture["profile_id"])
        decision = gate_module.controlled_v2_route_gate(projection, profiles[profile_id])
        actions[str(decision["actual_primary_action"])] += 1
        record = {
            "case_id": fixture["case_id"],
            "profile_id": profile_id,
            "input_digest": digest_object(projection),
            "actual_decision": decision,
        }
        record["actual_record_digest"] = digest_object(record)
        actuals.append(record)
        artifact = decision.get("degraded_artifact")
        if isinstance(artifact, Mapping):
            degraded.append(
                {
                    "case_id": fixture["case_id"],
                    "profile_id": profile_id,
                    "artifact": dict(artifact),
                }
            )
    manifest = {
        "route_execution_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "route_gate_path": ROUTE_GATE_PATH.as_posix(),
            "route_gate_digest": sha256_file(ROOT / ROUTE_GATE_PATH),
            "route_input_count": len(inputs),
            "actual_count": len(actuals),
            "action_distribution_recomputed": dict(sorted(actions.items())),
            "distribution_quota_used": False,
            "expectation_file_visible_to_gate": False,
            "case_id_visible_to_gate": False,
            "degraded_artifact_count": len(degraded),
            "audience_content_created_count": 0,
            "runtime_plan_created_count": 0,
        }
    }
    manifest["route_execution_manifest"]["manifest_digest"] = digest_object(
        manifest["route_execution_manifest"]
    )
    return actuals, degraded, manifest


def core_paths() -> list[Path]:
    return [
        CONSTRAINT_COMPILER_PATH,
        RESPONSE_VALIDATOR_PATH,
        ROUTE_GATE_PATH,
        AUTHOR_INSTRUCTION_PATH,
        AUTHOR_PROTOCOL_PATH,
        AUTHOR_SCHEMA_PATH,
        ACTIVE_REGISTRY_PATH,
        BACKEND_MANIFEST_PATH,
        ROUTE_CONTRACT_PATH,
        CORE_DIR / "route_fixture_batch.schema.json",
        CORE_DIR / "route_expectation_batch.schema.json",
        RUBRIC_PATH,
        REVIEW_PROTOCOL_PATH,
        ROUTE_INPUTS_PATH,
        ROUTE_EXPECTATIONS_PATH,
        ROUTE_ACTUALS_PATH,
        DEGRADED_ARTIFACTS_PATH,
        ROUTE_EXECUTION_PATH,
        ROUTE_COMPARISON_PATH,
        DIAGNOSTIC_PATH,
        PHASE0_BINDING_PATH,
        REVIEW_DISCREPANCY_PATH,
        CHECKER_PATH,
        MATERIALIZER_PATH,
    ]


def write_core() -> None:
    _update_core_metadata()
    write_text(DIAGNOSTIC_PATH, yaml_text(development_diagnostic()))
    actuals, degraded, route_manifest = execute_routes()
    write_text(ROUTE_ACTUALS_PATH, jsonl_text(actuals))
    write_text(DEGRADED_ARTIFACTS_PATH, jsonl_text(degraded))
    write_text(ROUTE_EXECUTION_PATH, yaml_text(route_manifest))
    if not (ROOT / ROUTE_COMPARISON_PATH).exists():
        return
    manifest = {
        "core_freeze_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "freeze_semantics": "FILES_HASHED_IN_COMMIT_1_TREE",
            "freeze_commit_sha_binding": "BOUND_BY_COMMIT_2_OPEN_GATE_MANIFEST",
            "core_file_count": len(core_paths()),
            "files": [
                {"path": path.as_posix(), "sha256": sha256_file(ROOT / path)}
                for path in core_paths()
            ],
            "post_commit_core_mutation_allowed": False,
            "route_gate_mutation_allowed": False,
            "qualification_review_protocol_mutation_allowed": False,
        }
    }
    manifest["core_freeze_manifest"]["core_digest"] = digest_object(
        manifest["core_freeze_manifest"]["files"]
    )
    write_text(FREEZE_MANIFEST_PATH, yaml_text(manifest))


def check_core() -> list[str]:
    errors: list[str] = []
    diagnostic = yaml_text(development_diagnostic())
    if not (ROOT / DIAGNOSTIC_PATH).exists() or (ROOT / DIAGNOSTIC_PATH).read_text() != diagnostic:
        errors.append("E_DIAGNOSTIC_DRIFT")
    actuals, degraded, route_manifest = execute_routes()
    expected_texts = {
        ROUTE_ACTUALS_PATH: jsonl_text(actuals),
        DEGRADED_ARTIFACTS_PATH: jsonl_text(degraded),
        ROUTE_EXECUTION_PATH: yaml_text(route_manifest),
    }
    for path, text in expected_texts.items():
        if not (ROOT / path).exists() or (ROOT / path).read_text(encoding="utf-8") != text:
            errors.append(f"E_MATERIALIZED_DRIFT:{path}")
    if not (ROOT / FREEZE_MANIFEST_PATH).exists():
        errors.append("E_FREEZE_MANIFEST_MISSING")
        return errors
    manifest = load_yaml(ROOT / FREEZE_MANIFEST_PATH)["core_freeze_manifest"]
    listed = {item["path"]: item["sha256"] for item in manifest["files"]}
    for path in core_paths():
        if listed.get(path.as_posix()) != sha256_file(ROOT / path):
            errors.append(f"E_CORE_DIGEST:{path}")
    if manifest.get("core_digest") != digest_object(manifest["files"]):
        errors.append("E_CORE_MANIFEST_DIGEST")
    return errors


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def prepare_open_gate(core_commit_sha: str) -> None:
    if not core_commit_sha or _git(["rev-parse", core_commit_sha]) != core_commit_sha:
        raise ValueError("full core commit SHA required")
    packs = load_jsonl(ROOT / OPEN_PACKS_PATH)
    plans = load_jsonl(ROOT / OPEN_PLANS_PATH)
    if len(packs) != 20 or len(plans) != 40:
        raise ValueError("open gate requires 20 material packs and 40 plans")
    pack_map = {row["material_pack_id"]: row for row in packs}
    compiler = import_module(CONSTRAINT_COMPILER_PATH, "constraint_compiler_open_gate")
    requests: list[dict[str, Any]] = []
    for plan in plans:
        pack = pack_map[str(plan["material_pack_ref"])]
        request = compiler.compile_authoring_request(plan, pack, plan["style_realization_plan"])
        requests.append(request)
    write_text(OPEN_REQUESTS_PATH, jsonl_text(requests))
    core_manifest = load_yaml(ROOT / FREEZE_MANIFEST_PATH)["core_freeze_manifest"]
    freeze = {
        "authoring_input_freeze": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "namespace": "DEV-OPEN-GATE-001",
            "core_commit_sha": core_commit_sha,
            "core_digest": core_manifest["core_digest"],
            "material_pack_count": len(packs),
            "plan_count": len(plans),
            "authoring_request_count": len(requests),
            "material_file_digest": sha256_file(ROOT / OPEN_PACKS_PATH),
            "plan_file_digest": sha256_file(ROOT / OPEN_PLANS_PATH),
            "request_file_digest": sha256_file(ROOT / OPEN_REQUESTS_PATH),
            "frozen_before_authoring": True,
            "candidate_reroll_allowed": 0,
            "candidate_replacement_allowed": 0,
            "per_candidate_patch_allowed": 0,
        }
    }
    freeze["authoring_input_freeze"]["freeze_digest"] = digest_object(
        freeze["authoring_input_freeze"]
    )
    write_text(OPEN_INPUT_FREEZE_PATH, yaml_text(freeze))


def _ngrams(text: str, size: int = 8) -> set[str]:
    normalized = "".join(character.lower() for character in text if character.isalnum())
    if len(normalized) < size:
        return set()
    return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}


def _surface_text(response: Mapping[str, Any]) -> str:
    surfaces = response["surfaces"]
    parts = [surfaces["title"], *surfaces["body_blocks"], *surfaces["spoken_lines"]]
    parts.extend([surfaces["CTA"], *surfaces["visual_beats"], *surfaces["capture_instructions"]])
    parts.extend([surfaces["audio_grammar"], surfaces["editing_grammar"]])
    return "\n".join(str(part) for part in parts if part)


def materialize_open_gate(core_commit_sha: str) -> None:
    freeze = load_yaml(ROOT / OPEN_INPUT_FREEZE_PATH)["authoring_input_freeze"]
    if freeze["core_commit_sha"] != core_commit_sha:
        raise ValueError("core commit binding mismatch")
    requests = load_jsonl(ROOT / OPEN_REQUESTS_PATH)
    raw = load_jsonl(ROOT / OPEN_RAW_PATH)
    if len(requests) != 40 or len(raw) != 40:
        raise ValueError("open gate requires exactly 40 requests and 40 raw responses")
    request_map = {row["request_id"]: row for row in requests}
    validator = import_module(RESPONSE_VALIDATOR_PATH, "response_validator_open_gate")
    candidates: list[dict[str, Any]] = []
    machine: list[dict[str, Any]] = []
    invocations: list[dict[str, Any]] = []
    for response in raw:
        request_id = str(response["request_id"])
        request = request_map[request_id]
        errors = validator.validate_response(request, response)
        candidate = {
            "candidate_id": response["response_id"],
            "request_id": request_id,
            "request_digest": request["request_digest"],
            "assignment_id": request["assignment_id"],
            "profile_id": request["content_product_contract"]["profile_id"],
            "voice_lane": request["voice_contract"]["voice_lane"],
            "material_pack_ref": request["material_pack_ref"],
            "plan_ref": request["plan_ref"],
            "surfaces": response["surfaces"],
            "surface_bindings": response["surface_bindings"],
            "style_realization_evidence": response["style_realization_evidence"],
            "required_obligation_evidence": response["required_obligation_evidence"],
            "machine_validation_errors": errors,
            "machine_structural_eligible": not errors,
            "machine_safety_eligible": not errors,
            "machine_quality_claim": False,
            "qualification_wrapper": {
                "synthetic_case": True,
                "qualification_only": True,
                "nonpublishable": True,
                "runtime_consumable": False,
                "production_consumable": False,
                "may_enter_reference_corpus": False,
                "may_enter_KE_RAG_DIFY": False,
            },
        }
        candidate["candidate_digest"] = digest_object(candidate)
        candidates.append(candidate)
        machine.append(
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_digest": candidate["candidate_digest"],
                "machine_structural_eligible": not errors,
                "machine_safety_eligible": not errors,
                "machine_quality_claim": False,
                "validation_errors": errors,
            }
        )
        invocations.append(
            {
                "request_id": request_id,
                "request_digest": request["request_digest"],
                "response_id": response["response_id"],
                "response_digest": digest_object(response),
                "backend_class": "CONTROLLED_EXECUTION_AGENT",
                "fresh_ephemeral_session": True,
                "one_request_one_response": True,
                "paired_output_visible": False,
                "reroll_count": 0,
                "replacement_count": 0,
                "external_provider_API_call_count": 0,
            }
        )
    write_text(OPEN_INVOCATIONS_PATH, jsonl_text(invocations))
    write_text(OPEN_CANDIDATES_PATH, jsonl_text(candidates))
    write_text(OPEN_MACHINE_PATH, jsonl_text(machine))

    blind1: list[dict[str, Any]] = []
    blind2: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for candidate in candidates:
        token = hashlib.sha256(candidate["candidate_digest"].encode("ascii")).hexdigest()[:16]
        surfaces = candidate["surfaces"]
        blind1.append(
            {
                "blind_token": token,
                "body": surfaces["body_blocks"],
                "spoken": surfaces["spoken_lines"],
                "visual": surfaces["visual_beats"],
                "audio": surfaces["audio_grammar"],
                "editing": surfaces["editing_grammar"],
            }
        )
        blind2.append(
            {
                "blind_token": token,
                "title": surfaces["title"],
                "CTA": surfaces["CTA"],
                "full_surface": surfaces,
            }
        )
        bindings.append(
            {
                "blind_token": token,
                "candidate_id": candidate["candidate_id"],
                "candidate_digest": candidate["candidate_digest"],
                "profile_id": candidate["profile_id"],
                "voice_lane": candidate["voice_lane"],
            }
        )
    write_text(OPEN_BLIND1_PATH, jsonl_text(blind1))
    write_text(OPEN_BLIND2_PATH, jsonl_text(blind2))
    write_text(OPEN_BLIND_BINDING_PATH, jsonl_text(bindings))

    pair_rows: list[dict[str, Any]] = []
    by_profile: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_profile.setdefault(candidate["profile_id"], []).append(candidate)
    for profile_id, pair in sorted(by_profile.items()):
        if len(pair) != 2:
            raise ValueError(f"profile {profile_id} does not have a pair")
        pair.sort(key=lambda item: item["voice_lane"])
        left, right = pair
        left_text = _surface_text(left)
        right_text = _surface_text(right)
        left_ngrams = _ngrams(left_text)
        right_ngrams = _ngrams(right_text)
        denominator = max(1, min(len(left_ngrams), len(right_ngrams)))
        overlap = len(left_ngrams.intersection(right_ngrams)) / denominator
        left_lines = {line.strip() for line in left_text.splitlines() if line.strip()}
        right_lines = {line.strip() for line in right_text.splitlines() if line.strip()}
        pair_rows.append(
            {
                "profile_id": profile_id,
                "lane_A_candidate_id": left["candidate_id"],
                "lane_B_candidate_id": right["candidate_id"],
                "non_evidence_exact_line_overlap_count": len(left_lines.intersection(right_lines)),
                "normalized_8gram_overlap_ratio": overlap,
                "mere_paraphrase_machine_claim": False,
                "human_pair_review_required": True,
            }
        )
    write_text(OPEN_PAIR_PATH, jsonl_text(pair_rows))

    review_input = {
        "development_reviewer_input_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "namespace": "DEV-OPEN-GATE-001",
            "candidate_count": 40,
            "candidate_file": OPEN_CANDIDATES_PATH.as_posix(),
            "candidate_file_digest": sha256_file(ROOT / OPEN_CANDIDATES_PATH),
            "blind_view_1_file": OPEN_BLIND1_PATH.as_posix(),
            "blind_view_1_digest": sha256_file(ROOT / OPEN_BLIND1_PATH),
            "blind_view_2_file": OPEN_BLIND2_PATH.as_posix(),
            "blind_view_2_digest": sha256_file(ROOT / OPEN_BLIND2_PATH),
            "rubric_file": RUBRIC_PATH.as_posix(),
            "rubric_digest": sha256_file(ROOT / RUBRIC_PATH),
            "review_protocol_file": REVIEW_PROTOCOL_PATH.as_posix(),
            "review_protocol_digest": sha256_file(ROOT / REVIEW_PROTOCOL_PATH),
            "machine_quality_claim": False,
            "external_guardian_required": True,
        }
    }
    review_input["development_reviewer_input_manifest"]["manifest_digest"] = digest_object(
        review_input["development_reviewer_input_manifest"]
    )
    write_text(OPEN_REVIEW_INPUT_PATH, yaml_text(review_input))

    packet = {
        "guardian_checkpoint_A_packet": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "core_commit_sha": core_commit_sha,
            "core_digest": freeze["core_digest"],
            "candidate_count": 40,
            "route_case_count": 60,
            "candidate_file": OPEN_CANDIDATES_PATH.as_posix(),
            "route_inputs_file": ROUTE_INPUTS_PATH.as_posix(),
            "sealed_expectations_file": ROUTE_EXPECTATIONS_PATH.as_posix(),
            "route_actuals_file": ROUTE_ACTUALS_PATH.as_posix(),
            "route_comparison_file": ROUTE_COMPARISON_PATH.as_posix(),
            "degraded_artifacts_file": DEGRADED_ARTIFACTS_PATH.as_posix(),
            "review_protocol_file": REVIEW_PROTOCOL_PATH.as_posix(),
            "guardian_must_read_all_40_nine_surfaces": True,
            "guardian_must_rerun_all_60_routes": True,
            "machine_quality_claim": False,
            "development_gate_status": "PENDING_EXTERNAL_GUARDIAN",
            "eligible_to_open_sealed_hidden": False,
        }
    }
    packet["guardian_checkpoint_A_packet"]["packet_digest"] = digest_object(
        packet["guardian_checkpoint_A_packet"]
    )
    write_text(OPEN_PACKET_PATH, yaml_text(packet))

    result = {
        "checkpoint_A_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "status": "PENDING_EXTERNAL_GUARDIAN",
            "development_gate_status": "PENDING_EXTERNAL_GUARDIAN",
            "candidate_count": 40,
            "authoring_invocation_count": 40,
            "structural_failure_count": sum(bool(item["validation_errors"]) for item in machine),
            "machine_content_quality_pass_claimed": False,
            "first_acceptance_count": None,
            "lane_A_first_acceptance_count": None,
            "lane_B_first_acceptance_count": None,
            "eligible_to_open_sealed_hidden": False,
            "generator_qualified": False,
            "founder_final_qualification": "PENDING",
            "accepted_baseline_increment_count": 0,
            "accepted_baseline_count": 120,
            "external_provider_API_call_count": 0,
            "runtime_provider_adapter_qualified": False,
            "runtime_ingest_ready": False,
            "published_content_count": 0,
        }
    }
    result["checkpoint_A_result"]["result_digest"] = digest_object(result["checkpoint_A_result"])
    write_text(OPEN_RESULT_PATH, yaml_text(result))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize-core", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--prepare-open-gate", action="store_true")
    parser.add_argument("--materialize-open-gate", action="store_true")
    parser.add_argument("--core-commit-sha", default="")
    args = parser.parse_args()
    selected = sum(
        int(value)
        for value in (
            args.materialize_core,
            args.check,
            args.prepare_open_gate,
            args.materialize_open_gate,
        )
    )
    if selected != 1:
        return 2
    if args.materialize_core:
        write_core()
        return 0
    if args.check:
        errors = check_core()
        if errors:
            for error in errors:
                sys.stderr.write(error + "\n")
            return 1
        return 0
    if args.prepare_open_gate:
        prepare_open_gate(args.core_commit_sha)
        return 0
    materialize_open_gate(args.core_commit_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
