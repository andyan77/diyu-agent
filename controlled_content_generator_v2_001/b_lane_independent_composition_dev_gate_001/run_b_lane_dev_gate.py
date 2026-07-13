#!/usr/bin/env python3
"""Freeze pair plans and materialize authored evidence without writing prose."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from controlled_content_generator_v2_001.b_lane_independent_composition_dev_gate_001.core.pair_plan_divergence_gate import (  # noqa: E402
    pair_plan_divergence_gate,
)
from controlled_content_generator_v2_001.b_lane_independent_composition_dev_gate_001.core.pair_planner import (  # noqa: E402
    build_pair_plans,
)
from controlled_content_generator_v2_001.creative_authoring_route_oracle_convergence_001.core.constraint_compiler import (  # noqa: E402
    compile_authoring_request,
)
from controlled_content_generator_v2_001.creative_authoring_route_oracle_convergence_001.core.response_validator import (  # noqa: E402
    validate_response,
)


TASK_ID = "CONTROLLED_V2_B_LANE_INDEPENDENT_COMPOSITION_DEV_GATE_001"
ROOT = REPO_ROOT
TASK_DIR = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001"
)
CAL_DIR = TASK_DIR / "calibration"
DEV_DIR = TASK_DIR / "dev_open_gate_pair_002"
CORE_DIR = TASK_DIR / "core"
OLD_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001"
)
OLD_DEV_DIR = OLD_DIR / "dev_open_gate_001"
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
CHECKER_PATH = (
    TASK_DIR / "check_controlled_v2_b_lane_independent_composition_dev_gate.py"
)
RUNNER_PATH = TASK_DIR / "run_b_lane_dev_gate.py"
FREEZE_PATH = TASK_DIR / "core_freeze_manifest.v0.1.yaml"
PHASE0_GUARDIAN_PATH = TASK_DIR / "phase_0/guardian_checkpoint_0_verdict.v0.1.yaml"
PHASE0_MERGE_PATH = TASK_DIR / "phase_0/pr9_merge_binding.v0.1.yaml"

CAL_PACKS_PATH = CAL_DIR / "exposed_pair_calibration_material_packs.v0.1.jsonl"
CAL_PROJECTED_PATH = CAL_DIR / "projected_material_packs.v0.1.jsonl"
CAL_PLANS_PATH = CAL_DIR / "composition_plans.v0.1.jsonl"
CAL_REQUESTS_PATH = CAL_DIR / "authoring_requests.v0.1.jsonl"
CAL_REQUEST_DIR = CAL_DIR / "authoring_requests"
CAL_ASSIGNMENTS_PATH = CAL_DIR / "assignments.v0.1.jsonl"
CAL_FREEZE_PATH = CAL_DIR / "authoring_input_freeze.v0.1.yaml"
CAL_RAW_DIR = CAL_DIR / "raw_responses"
CAL_RAW_PATH = CAL_DIR / "raw_authoring_responses.v0.1.jsonl"
CAL_RETAINED_PATH = CAL_DIR / "retained_lane_A_candidates.v0.1.jsonl"
CAL_CANDIDATES_PATH = CAL_DIR / "generated_candidates.v0.1.jsonl"
CAL_MACHINE_PATH = CAL_DIR / "machine_pair_results.v0.1.jsonl"
CAL_REVIEW_PATH = CAL_DIR / "calibration_reviews.v0.1.jsonl"
CAL_PACKET_PATH = CAL_DIR / "calibration_reviewer_packet.v0.1.yaml"
CAL_RESULT_PATH = CAL_DIR / "calibration_result.v0.1.yaml"
CAL_SESSION_REGISTRY_PATH = CAL_DIR / "authoring_session_registry.v0.1.jsonl"

DEV_PACKS_PATH = DEV_DIR / "material_packs.v0.1.jsonl"
DEV_PROJECTED_PATH = DEV_DIR / "projected_material_packs.v0.1.jsonl"
DEV_PLANS_PATH = DEV_DIR / "composition_plans.v0.1.jsonl"
DEV_REQUESTS_PATH = DEV_DIR / "authoring_requests.v0.1.jsonl"
DEV_REQUEST_DIR = DEV_DIR / "authoring_requests"
DEV_ASSIGNMENTS_PATH = DEV_DIR / "assignments.v0.1.jsonl"
DEV_FREEZE_PATH = DEV_DIR / "authoring_input_freeze.v0.1.yaml"
DEV_RAW_DIR = DEV_DIR / "raw_responses"
DEV_RAW_PATH = DEV_DIR / "raw_authoring_responses.v0.1.jsonl"
DEV_CANDIDATES_PATH = DEV_DIR / "candidates.v0.1.jsonl"
DEV_MACHINE_PATH = DEV_DIR / "machine_structural_results.v0.1.jsonl"
DEV_PAIR_PATH = DEV_DIR / "pair_independence_machine_results.v0.1.jsonl"
DEV_INVOCATIONS_PATH = DEV_DIR / "authoring_session_audit.v0.1.jsonl"
DEV_BLIND1_PATH = DEV_DIR / "blind_view_1.v0.1.jsonl"
DEV_BLIND2_PATH = DEV_DIR / "blind_view_2.v0.1.jsonl"
DEV_BINDING_PATH = DEV_DIR / "blind_view_binding.v0.1.jsonl"
DEV_REVIEW_PACKET_PATH = DEV_DIR / "external_guardian_review_packet.v0.1.yaml"
DEV_RESULT_PATH = DEV_DIR / "task_result.v0.1.yaml"
DEV_SESSION_REGISTRY_PATH = DEV_DIR / "authoring_session_registry.v0.1.jsonl"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def jsonl_text(rows: Iterable[Mapping[str, Any]]) -> str:
    return "".join(canonical_json(dict(row)) + "\n" for row in rows)


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected mapping in {path}")
    return value


def yaml_text(value: Mapping[str, Any]) -> str:
    return yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False, width=140)


def write_text(path: Path, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def write_request_shards(directory: Path, requests: list[dict[str, Any]]) -> None:
    target = ROOT / directory
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError(
            f"request shard directory must be empty before freeze: {directory}"
        )
    for request in requests:
        filename = f"{request['request_id']}.json"
        write_text(directory / filename, canonical_json(request) + "\n")


def profile_map() -> dict[str, dict[str, Any]]:
    document = load_yaml(ROOT / PROFILE_PATH)
    profiles = document["content_product_profile_registry"]["profiles"]
    return {str(item["content_product_type_id"]): item for item in profiles}


def normalized_packs(path: Path, namespace: str) -> list[dict[str, Any]]:
    rows = load_jsonl(ROOT / path)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        pack = dict(row)
        pack["task_id"] = TASK_ID
        pack["namespace"] = namespace
        pack.pop("material_pack_digest", None)
        pack["material_pack_digest"] = digest_object(pack)
        normalized.append(pack)
    return sorted(normalized, key=lambda item: str(item["profile_id"]))


def build_inputs(
    packs: list[dict[str, Any]],
    *,
    calibration: bool,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    profiles = profile_map()
    projected: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    old_candidates = {
        (str(row["profile_id"]), str(row["voice_lane"])): row
        for row in load_jsonl(ROOT / OLD_DEV_DIR / "candidates.v0.1.jsonl")
    }
    for pack in packs:
        profile_id = str(pack["profile_id"])
        bundle = build_pair_plans(pack, profiles[profile_id])
        if bundle["affordance"]["decision"] != "PAIR_READY":
            raise ValueError(f"{profile_id} is not PAIR_READY: {bundle['affordance']}")
        lane_plans = {str(plan["voice_lane"]): plan for plan in bundle["plans"]}
        divergence = pair_plan_divergence_gate(lane_plans["A"], lane_plans["B"])
        if not divergence["pass"]:
            raise ValueError(f"{profile_id} pair plan divergence failed: {divergence}")
        projected.extend(bundle["projected_material_packs"])
        plans.extend(bundle["plans"])
        projected_by_id = {
            str(item["material_pack_id"]): item
            for item in bundle["projected_material_packs"]
        }
        selected_plans = (
            [lane_plans["B"]] if calibration else [lane_plans["A"], lane_plans["B"]]
        )
        for plan in selected_plans:
            projected_pack = projected_by_id[str(plan["material_pack_ref"])]
            request = compile_authoring_request(
                plan, projected_pack, plan["style_realization_plan"]
            )
            request["task_id"] = TASK_ID
            request["pair_isolation_contract"] = {
                "other_lane_plan_visibility": False,
                "other_lane_selected_atoms_visibility": False,
                "other_lane_request_visibility": False,
                "other_lane_response_visibility": False,
                "other_lane_candidate_visibility": False,
            }
            request.pop("request_digest", None)
            request["request_digest"] = digest_object(request)
            requests.append(request)
        assignment: dict[str, Any] = {
            "profile_id": profile_id,
            "affordance": bundle["affordance"],
            "pair_plan_divergence": divergence,
            "lane_A_plan_id": lane_plans["A"]["plan_id"],
            "lane_B_plan_id": lane_plans["B"]["plan_id"],
        }
        if calibration:
            assignment["retained_lane"] = "A"
            assignment["retained_candidate_id"] = old_candidates[(profile_id, "A")][
                "candidate_id"
            ]
            assignment["regenerated_lane"] = "B"
        assignments.append(assignment)
    return projected, plans, requests, assignments


def _freeze_document(
    *,
    namespace: str,
    core_commit_sha: str | None,
    packs_path: Path,
    plans_path: Path,
    requests_path: Path,
    request_count: int,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "namespace": namespace,
        "material_file_digest": sha256_file(ROOT / packs_path),
        "plan_file_digest": sha256_file(ROOT / plans_path),
        "request_file_digest": sha256_file(ROOT / requests_path),
        "authoring_request_count": request_count,
        "frozen_before_authoring": True,
        "reroll_allowed": 0,
        "replacement_allowed": 0,
        "per_candidate_patch_allowed": 0,
        "external_provider_API_call_count": 0,
    }
    if core_commit_sha is not None:
        body["core_commit_sha"] = core_commit_sha
        body["core_manifest_digest"] = sha256_file(ROOT / FREEZE_PATH)
    body["freeze_digest"] = digest_object(body)
    return {"authoring_input_freeze": body}


def prepare_calibration() -> None:
    packs = normalized_packs(CAL_PACKS_PATH, "EXPOSED_PAIR_CALIBRATION_001")
    if len(packs) != 13:
        raise ValueError("calibration requires exactly 13 material packs")
    write_text(CAL_PACKS_PATH, jsonl_text(packs))
    projected, plans, requests, assignments = build_inputs(packs, calibration=True)
    if len(projected) != 26 or len(plans) != 26 or len(requests) != 13:
        raise ValueError("calibration input cardinality mismatch")
    write_text(CAL_PROJECTED_PATH, jsonl_text(projected))
    write_text(CAL_PLANS_PATH, jsonl_text(plans))
    write_text(CAL_REQUESTS_PATH, jsonl_text(requests))
    write_request_shards(CAL_REQUEST_DIR, requests)
    write_text(CAL_ASSIGNMENTS_PATH, jsonl_text(assignments))
    freeze = _freeze_document(
        namespace="EXPOSED_PAIR_CALIBRATION_001",
        core_commit_sha=None,
        packs_path=CAL_PACKS_PATH,
        plans_path=CAL_PLANS_PATH,
        requests_path=CAL_REQUESTS_PATH,
        request_count=13,
    )
    write_text(CAL_FREEZE_PATH, yaml_text(freeze))


def _load_raw(directory: Path, expected: int) -> list[dict[str, Any]]:
    files = sorted((ROOT / directory).glob("*.json"))
    if len(files) != expected:
        raise ValueError(
            f"expected {expected} isolated raw responses, found {len(files)}"
        )
    return [json.loads(path.read_text(encoding="utf-8")) for path in files]


def _candidate(
    request: Mapping[str, Any], response: Mapping[str, Any]
) -> dict[str, Any]:
    normalized_response, normalized_reference_count = normalize_response_references(
        response
    )
    errors = validate_response(request, normalized_response)
    candidate: dict[str, Any] = {
        "candidate_id": normalized_response["response_id"],
        "request_id": request["request_id"],
        "request_digest": request["request_digest"],
        "assignment_id": request["assignment_id"],
        "profile_id": request["content_product_contract"]["profile_id"],
        "voice_lane": request["voice_contract"]["voice_lane"],
        "material_pack_ref": request["material_pack_ref"],
        "plan_ref": request["plan_ref"],
        "surfaces": normalized_response["surfaces"],
        "surface_bindings": normalized_response["surface_bindings"],
        "style_realization_evidence": normalized_response["style_realization_evidence"],
        "required_obligation_evidence": normalized_response[
            "required_obligation_evidence"
        ],
        "reference_notation_normalized_count": normalized_reference_count,
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
    return candidate


def canonical_surface_reference(value: str) -> str:
    """Normalize an RFC 6901 leaf pointer to the frozen dotted path form."""

    if not value.startswith("/surfaces/"):
        return value
    tokens = [
        token.replace("~1", "/").replace("~0", "~") for token in value.split("/")[1:]
    ]
    result = tokens[0]
    for token in tokens[1:]:
        result += f"[{token}]" if token.isdigit() else f".{token}"
    return result


def normalize_response_references(
    response: Mapping[str, Any],
) -> tuple[dict[str, Any], int]:
    normalized = copy.deepcopy(dict(response))
    changed = 0
    for binding in normalized.get("surface_bindings", []):
        old = str(binding.get("surface_path", ""))
        new = canonical_surface_reference(old)
        binding["surface_path"] = new
        changed += int(new != old)
    for collection in ("style_realization_evidence", "required_obligation_evidence"):
        for item in normalized.get(collection, []):
            refs = [str(ref) for ref in item.get("actual_surface_refs", [])]
            converted = [canonical_surface_reference(ref) for ref in refs]
            changed += sum(left != right for left, right in zip(refs, converted))
            item["actual_surface_refs"] = converted
    return normalized, changed


def _surface_text(candidate: Mapping[str, Any]) -> str:
    surfaces = candidate["surfaces"]
    values = [surfaces["title"], *surfaces["body_blocks"], *surfaces["spoken_lines"]]
    values.extend(
        [surfaces["CTA"], *surfaces["visual_beats"], *surfaces["capture_instructions"]]
    )
    values.extend([surfaces["audio_grammar"], surfaces["editing_grammar"]])
    return "\n".join(str(item) for item in values if str(item))


def _ngrams(text: str, size: int = 8) -> set[str]:
    normalized = "".join(character.lower() for character in text if character.isalnum())
    return {
        normalized[index : index + size]
        for index in range(max(0, len(normalized) - size + 1))
    }


def pair_machine_result(
    profile_id: str,
    lane_a: Mapping[str, Any],
    lane_b: Mapping[str, Any],
) -> dict[str, Any]:
    left = _surface_text(lane_a)
    right = _surface_text(lane_b)
    left_lines = {line.strip() for line in left.splitlines() if line.strip()}
    right_lines = {line.strip() for line in right.splitlines() if line.strip()}
    left_grams = _ngrams(left)
    right_grams = _ngrams(right)
    overlap = len(left_grams.intersection(right_grams)) / max(
        1, min(len(left_grams), len(right_grams))
    )
    return {
        "profile_id": profile_id,
        "lane_A_candidate_id": lane_a["candidate_id"],
        "lane_B_candidate_id": lane_b["candidate_id"],
        "all_surface_exact_line_overlap_count": len(
            left_lines.intersection(right_lines)
        ),
        "normalized_8gram_overlap_ratio": round(overlap, 6),
        "mere_paraphrase_machine_claim": False,
        "human_pair_review_required": True,
    }


def materialize_calibration() -> None:
    requests = load_jsonl(ROOT / CAL_REQUESTS_PATH)
    raw = _load_raw(CAL_RAW_DIR, 13)
    request_map = {str(item["request_id"]): item for item in requests}
    if {str(item["request_id"]) for item in raw} != set(request_map):
        raise ValueError("calibration raw response/request set mismatch")
    candidates = [
        _candidate(request_map[str(item["request_id"])], item) for item in raw
    ]
    old_candidates = {
        (str(item["profile_id"]), str(item["voice_lane"])): item
        for item in load_jsonl(ROOT / OLD_DEV_DIR / "candidates.v0.1.jsonl")
    }
    retained = [
        old_candidates[(str(candidate["profile_id"]), "A")] for candidate in candidates
    ]
    machine = [
        pair_machine_result(
            str(candidate["profile_id"]),
            old_candidates[(str(candidate["profile_id"]), "A")],
            candidate,
        )
        for candidate in candidates
    ]
    sessions = load_jsonl(ROOT / CAL_SESSION_REGISTRY_PATH)
    if len(sessions) != 13 or len({str(item["agent_id"]) for item in sessions}) != 13:
        raise ValueError("calibration requires 13 unique isolated author sessions")
    if {str(item["request_id"]) for item in sessions} != set(request_map):
        raise ValueError("calibration author session/request set mismatch")
    write_text(CAL_RAW_PATH, jsonl_text(raw))
    write_text(CAL_RETAINED_PATH, jsonl_text(retained))
    write_text(CAL_CANDIDATES_PATH, jsonl_text(candidates))
    write_text(CAL_MACHINE_PATH, jsonl_text(machine))
    packet = {
        "calibration_reviewer_packet": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "namespace": "EXPOSED_PAIR_CALIBRATION_001",
            "pair_count": 13,
            "retained_candidate_file": CAL_RETAINED_PATH.as_posix(),
            "generated_candidate_file": CAL_CANDIDATES_PATH.as_posix(),
            "machine_pair_file": CAL_MACHINE_PATH.as_posix(),
            "review_output_file": CAL_REVIEW_PATH.as_posix(),
            "rubric_id": "ZERO-EDIT-FIRST-ACCEPTANCE",
            "review_must_not_rewrite_candidates": True,
            "machine_quality_claim": False,
        }
    }
    packet["calibration_reviewer_packet"]["packet_digest"] = digest_object(
        packet["calibration_reviewer_packet"]
    )
    write_text(CAL_PACKET_PATH, yaml_text(packet))


def finalize_calibration() -> bool:
    reviews = load_jsonl(ROOT / CAL_REVIEW_PATH)
    candidates = load_jsonl(ROOT / CAL_CANDIDATES_PATH)
    machine = load_jsonl(ROOT / CAL_MACHINE_PATH)
    expected_profiles = {str(item["profile_id"]) for item in candidates}
    review_profiles = {str(item["profile_id"]) for item in reviews}
    if len(reviews) != 13 or review_profiles != expected_profiles:
        raise ValueError("calibration review coverage mismatch")
    structural_failures = sum(
        bool(item["machine_validation_errors"]) for item in candidates
    )
    raw_quality_pass = sum(
        str(item.get("raw_quality")) in {"A", "B"} for item in reviews
    )
    independent_pass = sum(item.get("pair_independence") == "PASS" for item in reviews)
    mere_paraphrase = sum(item.get("mere_paraphrase") is True for item in reviews)
    unsupported = sum(int(item.get("unsupported_fact_count", 0)) for item in reviews)
    invalid_refs = structural_failures + sum(
        int(item.get("invalid_reference_count", 0)) for item in reviews
    )
    exact_overlap = sum(
        int(item["all_surface_exact_line_overlap_count"]) for item in machine
    )
    passed = (
        raw_quality_pass == 13
        and independent_pass >= 12
        and mere_paraphrase == 0
        and unsupported == 0
        and invalid_refs == 0
        and exact_overlap == 0
    )
    body = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "status": "PAIR_CALIBRATION_PASS"
        if passed
        else "STOPPED_PAIR_CALIBRATION_FAILED",
        "pair_count": 13,
        "new_authoring_invocation_count": 13,
        "raw_quality_A_or_B_count": raw_quality_pass,
        "pair_independence_pass_count": independent_pass,
        "mere_paraphrase_count": mere_paraphrase,
        "non_evidence_exact_line_overlap_count": exact_overlap,
        "invalid_reference_count": invalid_refs,
        "unsupported_fact_count": unsupported,
        "reroll_count": 0,
        "replacement_count": 0,
        "per_candidate_manual_patch_count": 0,
        "calibration_pass": passed,
        "hidden_created_count": 0,
        "generator_qualified": False,
        "accepted_baseline_count": 120,
    }
    body["result_digest"] = digest_object(body)
    write_text(CAL_RESULT_PATH, yaml_text({"calibration_result": body}))
    return passed


def freeze_core() -> None:
    result = load_yaml(ROOT / CAL_RESULT_PATH)["calibration_result"]
    if result.get("calibration_pass") is not True:
        raise ValueError("core may be frozen only after calibration passes")
    paths = [
        CORE_DIR / "dual_narrative_affordance_gate.py",
        CORE_DIR / "pair_planner.py",
        CORE_DIR / "pair_plan_divergence_gate.py",
        RUNNER_PATH,
        CHECKER_PATH,
        PHASE0_GUARDIAN_PATH,
        PHASE0_MERGE_PATH,
        CAL_PACKS_PATH,
        CAL_PROJECTED_PATH,
        CAL_PLANS_PATH,
        CAL_REQUESTS_PATH,
        CAL_ASSIGNMENTS_PATH,
        CAL_FREEZE_PATH,
        CAL_RAW_PATH,
        CAL_RETAINED_PATH,
        CAL_CANDIDATES_PATH,
        CAL_MACHINE_PATH,
        CAL_REVIEW_PATH,
        CAL_PACKET_PATH,
        CAL_RESULT_PATH,
        CAL_SESSION_REGISTRY_PATH,
    ]
    paths.extend(
        path.relative_to(ROOT)
        for path in sorted((ROOT / CAL_REQUEST_DIR).glob("*.json"))
    )
    files = [
        {"path": path.as_posix(), "sha256": sha256_file(ROOT / path)} for path in paths
    ]
    manifest = {
        "core_freeze_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "freeze_semantics": "FILES_HASHED_IN_COMMIT_1_TREE",
            "file_count": len(files),
            "files": files,
            "core_digest": digest_object(files),
            "post_commit_core_mutation_allowed": False,
            "creative_author_architecture_mutation_allowed": False,
            "route_gate_mutation_allowed": False,
        }
    }
    write_text(FREEZE_PATH, yaml_text(manifest))


def _git_rev_parse(value: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", value],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip())
    return result.stdout.strip()


def prepare_dev_gate(core_commit_sha: str) -> None:
    if len(core_commit_sha) != 40 or _git_rev_parse(core_commit_sha) != core_commit_sha:
        raise ValueError("full core commit SHA required")
    packs = normalized_packs(DEV_PACKS_PATH, "DEV-OPEN-GATE-PAIR-002")
    if len(packs) != 20 or {str(item["profile_id"]) for item in packs} != {
        f"CP{index:02d}" for index in range(1, 21)
    }:
        raise ValueError("development gate requires one pack for each CP01-CP20")
    write_text(DEV_PACKS_PATH, jsonl_text(packs))
    projected, plans, requests, assignments = build_inputs(packs, calibration=False)
    if len(projected) != 40 or len(plans) != 40 or len(requests) != 40:
        raise ValueError("development input cardinality mismatch")
    write_text(DEV_PROJECTED_PATH, jsonl_text(projected))
    write_text(DEV_PLANS_PATH, jsonl_text(plans))
    write_text(DEV_REQUESTS_PATH, jsonl_text(requests))
    write_request_shards(DEV_REQUEST_DIR, requests)
    write_text(DEV_ASSIGNMENTS_PATH, jsonl_text(assignments))
    freeze = _freeze_document(
        namespace="DEV-OPEN-GATE-PAIR-002",
        core_commit_sha=core_commit_sha,
        packs_path=DEV_PACKS_PATH,
        plans_path=DEV_PLANS_PATH,
        requests_path=DEV_REQUESTS_PATH,
        request_count=40,
    )
    write_text(DEV_FREEZE_PATH, yaml_text(freeze))


def _blind_views(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    blind1: list[dict[str, Any]] = []
    blind2: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for candidate in candidates:
        token = hashlib.sha256(
            candidate["candidate_digest"].encode("ascii")
        ).hexdigest()[:16]
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
        blind2.append({"blind_token": token, "full_surface": surfaces})
        bindings.append(
            {
                "blind_token": token,
                "candidate_id": candidate["candidate_id"],
                "candidate_digest": candidate["candidate_digest"],
                "profile_id": candidate["profile_id"],
                "voice_lane": candidate["voice_lane"],
            }
        )
    return blind1, blind2, bindings


def materialize_dev_gate(core_commit_sha: str) -> None:
    freeze = load_yaml(ROOT / DEV_FREEZE_PATH)["authoring_input_freeze"]
    if freeze.get("core_commit_sha") != core_commit_sha:
        raise ValueError("development gate core binding mismatch")
    requests = load_jsonl(ROOT / DEV_REQUESTS_PATH)
    raw = _load_raw(DEV_RAW_DIR, 40)
    request_map = {str(item["request_id"]): item for item in requests}
    if {str(item["request_id"]) for item in raw} != set(request_map):
        raise ValueError("development raw response/request set mismatch")
    candidates = [
        _candidate(request_map[str(item["request_id"])], item) for item in raw
    ]
    candidates.sort(key=lambda item: (str(item["profile_id"]), str(item["voice_lane"])))
    by_profile: dict[str, dict[str, dict[str, Any]]] = {}
    for candidate in candidates:
        by_profile.setdefault(str(candidate["profile_id"]), {})[
            str(candidate["voice_lane"])
        ] = candidate
    pair_rows = [
        pair_machine_result(profile_id, pair["A"], pair["B"])
        for profile_id, pair in sorted(by_profile.items())
    ]
    machine = [
        {
            "candidate_id": item["candidate_id"],
            "candidate_digest": item["candidate_digest"],
            "machine_structural_eligible": item["machine_structural_eligible"],
            "machine_safety_eligible": item["machine_safety_eligible"],
            "machine_quality_claim": False,
            "validation_errors": item["machine_validation_errors"],
        }
        for item in candidates
    ]
    session_rows = load_jsonl(ROOT / DEV_SESSION_REGISTRY_PATH)
    if (
        len(session_rows) != 40
        or len({str(item["agent_id"]) for item in session_rows}) != 40
    ):
        raise ValueError("development gate requires 40 unique isolated author sessions")
    session_map = {str(item["request_id"]): item for item in session_rows}
    if set(session_map) != set(request_map):
        raise ValueError("development author session/request set mismatch")
    response_by_request = {str(item["request_id"]): item for item in raw}
    invocations = []
    for request_id, session in sorted(session_map.items()):
        response = response_by_request[request_id]
        invocations.append(
            {
                "request_id": request_id,
                "response_id": response["response_id"],
                "controlled_execution_session_id": session["agent_id"],
                "fresh_ephemeral_session": True,
                "one_request_one_response": response.get("one_request_one_response")
                is True,
                "paired_output_visible": response.get("paired_output_visible"),
                "reroll_count": 0,
                "replacement_count": 0,
                "external_provider_API_call_count": 0,
            }
        )
    blind1, blind2, bindings = _blind_views(candidates)
    write_text(DEV_RAW_PATH, jsonl_text(raw))
    write_text(DEV_CANDIDATES_PATH, jsonl_text(candidates))
    write_text(DEV_MACHINE_PATH, jsonl_text(machine))
    write_text(DEV_PAIR_PATH, jsonl_text(pair_rows))
    write_text(DEV_INVOCATIONS_PATH, jsonl_text(invocations))
    write_text(DEV_BLIND1_PATH, jsonl_text(blind1))
    write_text(DEV_BLIND2_PATH, jsonl_text(blind2))
    write_text(DEV_BINDING_PATH, jsonl_text(bindings))

    packet_body: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "namespace": "DEV-OPEN-GATE-PAIR-002",
        "core_commit_sha": core_commit_sha,
        "candidate_count": 40,
        "pair_count": 20,
        "candidate_file": DEV_CANDIDATES_PATH.as_posix(),
        "blind_view_1_file": DEV_BLIND1_PATH.as_posix(),
        "blind_view_2_file": DEV_BLIND2_PATH.as_posix(),
        "pair_machine_file": DEV_PAIR_PATH.as_posix(),
        "rubric_id": "ZERO-EDIT-FIRST-ACCEPTANCE",
        "primary_reviewer_must_read_40_nine_surfaces": True,
        "adversarial_reviewer_must_read_40_nine_surfaces": True,
        "pair_reviewer_must_read_20_pairs": True,
        "blind_reviewer_must_start_with_blind_view_1": True,
        "machine_quality_claim": False,
        "development_gate_status": "PENDING_EXTERNAL_GUARDIAN",
        "hidden_created_count": 0,
    }
    packet_body["packet_digest"] = digest_object(packet_body)
    write_text(
        DEV_REVIEW_PACKET_PATH,
        yaml_text({"external_guardian_review_packet": packet_body}),
    )

    structural_failures = sum(bool(item["validation_errors"]) for item in machine)
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "verdict": "EXECUTED_PENDING_GUARDIAN",
        "development_gate_status": "PENDING_EXTERNAL_GUARDIAN",
        "material_pack_count": 20,
        "assignment_count": 40,
        "candidate_count": 40,
        "lane_A_count": 20,
        "lane_B_count": 20,
        "reroll_count": 0,
        "replacement_count": 0,
        "posthoc_patch_count": 0,
        "machine_structural_failure_count": structural_failures,
        "first_acceptance_count": None,
        "lane_A_first_acceptance_count": None,
        "lane_B_first_acceptance_count": None,
        "independent_pair_pass_count": None,
        "machine_content_quality_pass_claimed": False,
        "hidden_created_count": 0,
        "sealed_hidden_attempt_count": 0,
        "accepted_baseline_increment_count": 0,
        "accepted_baseline_count": 120,
        "generator_qualified": False,
        "founder_final_qualification": "PENDING",
        "external_provider_API_call_count": 0,
        "runtime_provider_adapter_qualified": False,
        "runtime_generation_eligible_profile_count": 0,
        "runtime_ingest_ready": False,
        "canonical_runtime_plan_count": 0,
        "published_content_count": 0,
        "generation_600_allowed": False,
        "expand_3600_allowed": False,
        "KE_change_count": 0,
        "RAG_change_count": 0,
        "DIFY_change_count": 0,
        "Serving_change_count": 0,
    }
    result["result_digest"] = digest_object(result)
    write_text(DEV_RESULT_PATH, yaml_text({"execution_result": result}))


def check_freeze() -> list[str]:
    errors: list[str] = []
    calibration_path = ROOT / CAL_RESULT_PATH
    if calibration_path.exists():
        calibration = load_yaml(calibration_path)["calibration_result"]
        if calibration.get("calibration_pass") is False:
            if (ROOT / FREEZE_PATH).exists():
                errors.append("E_CORE_FROZEN_AFTER_CALIBRATION_FAILURE")
            dev_files = [path for path in (ROOT / DEV_DIR).rglob("*") if path.is_file()]
            if dev_files:
                errors.append("E_DEV_CREATED_AFTER_CALIBRATION_FAILURE")
            return errors
    if not (ROOT / FREEZE_PATH).exists():
        return ["E_CORE_FREEZE_MISSING"]
    manifest = load_yaml(ROOT / FREEZE_PATH)["core_freeze_manifest"]
    for item in manifest.get("files", []):
        path = ROOT / str(item["path"])
        if not path.exists() or sha256_file(path) != item["sha256"]:
            errors.append(f"E_CORE_FREEZE_DRIFT:{item['path']}")
    if manifest.get("core_digest") != digest_object(manifest.get("files", [])):
        errors.append("E_CORE_FREEZE_DIGEST")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-calibration", action="store_true")
    parser.add_argument("--materialize-calibration", action="store_true")
    parser.add_argument("--finalize-calibration", action="store_true")
    parser.add_argument("--freeze-core", action="store_true")
    parser.add_argument("--prepare-dev-gate", action="store_true")
    parser.add_argument("--materialize-dev-gate", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--core-commit-sha", default="")
    args = parser.parse_args()
    modes = [
        args.prepare_calibration,
        args.materialize_calibration,
        args.finalize_calibration,
        args.freeze_core,
        args.prepare_dev_gate,
        args.materialize_dev_gate,
        args.check,
    ]
    if sum(int(value) for value in modes) != 1:
        return 2
    if args.prepare_calibration:
        prepare_calibration()
    elif args.materialize_calibration:
        materialize_calibration()
    elif args.finalize_calibration:
        return 0 if finalize_calibration() else 1
    elif args.freeze_core:
        freeze_core()
    elif args.prepare_dev_gate:
        prepare_dev_gate(args.core_commit_sha)
    elif args.materialize_dev_gate:
        materialize_dev_gate(args.core_commit_sha)
    else:
        errors = check_freeze()
        if errors:
            sys.stderr.write("\n".join(errors) + "\n")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
