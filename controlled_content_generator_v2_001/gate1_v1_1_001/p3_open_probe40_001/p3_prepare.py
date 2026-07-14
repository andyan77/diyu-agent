#!/usr/bin/env python3
"""Freeze P3 author requests, route inputs, versions, and historical anchors."""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from typing import Any

from p3_common import (
    AUTHORIZED_AUTHOR_CAPABILITY_ID,
    AUTHORIZED_AUTHOR_IDENTITY,
    AUTHORIZED_AUTHOR_MODEL_LABEL,
    AUTHORIZED_AUTHOR_SESSION,
    BASELINE_COMMIT,
    CURRENT_CHECKER_PATH,
    CURRENT_OWNER_PATH,
    P1A_ROOT,
    P1B_ROOT,
    P2_COMPONENTS_PATH,
    P2_EDGES_PATH,
    P2_PATHS_PATH,
    P2_RESULT_PATH,
    P2_ROOT,
    P2_RULES_PATH,
    PROFILE_PATH,
    ROOT,
    ROUTE_GOLD_PATH,
    ROUTE_INPUT_PATH,
    TASK_ID,
    TASK_ROOT,
    digest_object,
    jsonl_bytes,
    load_jsonl,
    object_digest,
    profile_rows,
    readiness_false,
    require,
    sha256_file,
    yaml_bytes,
)
from p3_structure import (
    MATERIAL_PATH,
    STRUCTURE_PATH,
    check_structure,
)


AUTHOR_INSTRUCTION_PATH = TASK_ROOT / "freeze/controlled_author_instruction.v0.1.md"
AUTHOR_MODEL_PATH = TASK_ROOT / "freeze/author_model_and_session.v0.1.yaml"
POSITIVE_ASSIGNMENT_PATH = TASK_ROOT / "freeze/positive_structure_assignment_20.v0.1.jsonl"
AUTHOR_REQUEST_PATH = TASK_ROOT / "freeze/positive_author_requests_20.v0.1.jsonl"
ROUTE_SELECTION_PATH = TASK_ROOT / "freeze/route_selection_20.v0.1.jsonl"
ROUTE_INPUT_FREEZE_PATH = TASK_ROOT / "freeze/route_inputs_20.v0.1.jsonl"
FREEZE_MANIFEST_PATH = TASK_ROOT / "freeze/p3_open_baseline_manifest.v0.1.yaml"
HISTORICAL_MANIFEST_PATH = TASK_ROOT / "baseline/historical_integrity_manifest.v0.1.jsonl"
PREPARE_RESULT_PATH = TASK_ROOT / "result/p3_prepare_result.v0.1.yaml"

LEGACY_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/"
    "founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
HISTORICAL_86_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
    "reviewed_reusable_component_registry.v0.4.jsonl"
)
STANDARD_PATH = P1A_ROOT / "standard/diyu_content_composition_standard.v1.1.md"

PINNED_INPUTS = {
    STANDARD_PATH: "022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542",
    PROFILE_PATH: "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056",
    ROUTE_GOLD_PATH: "f87d984d1780423e7ace0d78c54ba40e97ab5b48c39950f691c7ffca6652e054",
    P2_RESULT_PATH: "076bd9eb6c8ab67c0023bb454f6a82f16acecb284e896dc9029ef97582db5c3b",
    P2_COMPONENTS_PATH: "83dd1a8d35149785ac8bb172700b79d6221e5a7331b210018699fabaa49bc8ae",
    P2_RULES_PATH: "5d0ded265a6be6d0f39d35d2f739239225211081db6d6c4e4df0c8dcc2f09386",
    P2_EDGES_PATH: "de366eb50afe8a5a9362d3faa2a6a845af9c334683bdb9a8489cbfad2b2566f0",
    P2_ROOT / "component/approved_component_supply_matrix.v0.1.yaml": "790fe8922117db5a2a00980dc714b7b1318af386ba3b3069924fec7bfe273dc0",
    P2_PATHS_PATH: "4756971ef58ed472d0447f61f00bac7b7ef594117c43ecfb9fe3d7106c9631f3",
    P2_ROOT / "generator/gate1_generator_contract.v0.1.yaml": "67be34b2db8be54e5a81ef46c71367d196c12e29886dbcae62daf55a8d7518fa",
    P2_ROOT / "generator/active_gate1_generator_registry.v0.1.yaml": "46b83a926efaceb43010278bc33156a587dc7d38361dd8a149a5e1b96ecbff7a",
    P2_ROOT / "p2_generator_core_r6.py": "e15eab89cef2cb9b2a35d76ca3550b67f2c49c583fc9efe107ebaf062f527015",
    CURRENT_OWNER_PATH: "6c79eb78d9abe358fd0e9d2bf38cb1b18b193987c627b175f8858e5a0da3c08c",
    CURRENT_CHECKER_PATH: "09fd2c0f10e2166c8bbee9994447bb67b4ee77bae788a2f0fa0b9a42c486c162",
    LEGACY_120_PATH: "b6f8fccdcc38407d4791e85631d4a6df7366861617eccca5c13de4d311bb8c91",
    HISTORICAL_86_PATH: "de7bb3f3142a2076d88d92494ab512d31d125bb7b96b0ed232ac0122b354a601",
    ROUTE_INPUT_PATH: "68bc65bff904652f1e565097117c7e8dfccdcc6ef00d2e3a0e93a082a4d72f12",
}


def verify_pins(root: Path = ROOT, include_current_pointer: bool = True) -> None:
    for relative, expected in PINNED_INPUTS.items():
        if not include_current_pointer and relative in {CURRENT_OWNER_PATH, CURRENT_CHECKER_PATH}:
            continue
        path = root / relative
        require(path.is_file(), "E_P3_PIN_MISSING", relative.as_posix())
        require(sha256_file(path) == expected, "E_P3_PIN_DRIFT", relative.as_posix())


def _tracked_files(root: Path, prefix: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", prefix.as_posix()],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _historical_manifest(root: Path) -> list[dict[str, Any]]:
    paths: list[Path] = []
    for prefix in (P1A_ROOT, P1B_ROOT, P2_ROOT):
        paths.extend(_tracked_files(root, prefix))
    paths.extend([LEGACY_120_PATH, HISTORICAL_86_PATH, PROFILE_PATH, ROUTE_GOLD_PATH])
    unique = sorted(set(paths), key=lambda item: item.as_posix())
    rows = []
    for relative in unique:
        rows.append(
            {
                "path": relative.as_posix(),
                "sha256_at_p3_baseline": sha256_file(root / relative),
                "protection": (
                    "CONDITIONALLY_MUTABLE_COMPATIBILITY_PIN_ONLY"
                    if relative == P2_ROOT / "p2_final_materializer.py"
                    else "BYTE_IMMUTABLE"
                ),
            }
        )
    return rows


def _positive_assignments(root: Path) -> list[dict[str, Any]]:
    structures = load_jsonl(root / STRUCTURE_PATH)
    by_key = {(row["profile_id"], row["variant"]): row for row in structures}
    variants = ("A1", "A2", "B1", "B2")
    rows: list[dict[str, Any]] = []
    for index, profile in enumerate(profile_rows(root)):
        profile_id = str(profile["content_product_type_id"])
        variant = variants[index % len(variants)]
        structure = by_key[(profile_id, variant)]
        row = {
            "assignment_id": f"P3-POSITIVE-ASSIGNMENT-{profile_id}",
            "profile_id": profile_id,
            "assigned_variant": variant,
            "assigned_lane": structure["lane"],
            "assigned_structure_record_id": structure["record_id"],
            "assigned_structure_record_digest": structure["record_digest"],
            "selection_rule": "CP_SORT_ORDER_MOD_4_TO_A1_A2_B1_B2",
            "run_order": index + 1,
        }
        row["assignment_digest"] = object_digest(row, "assignment_digest")
        rows.append(row)
    require(len(rows) == 20, "E_P3_ASSIGNMENT_COUNT")
    require(
        {variant: sum(row["assigned_variant"] == variant for row in rows) for variant in variants}
        == {variant: 5 for variant in variants},
        "E_P3_ASSIGNMENT_BALANCE",
    )
    return rows


def _author_requests(root: Path, assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = {str(row["content_product_type_id"]): row for row in profile_rows(root)}
    materials = {str(row["profile_id"]): row for row in load_jsonl(root / MATERIAL_PATH)}
    structures = {(row["profile_id"], row["variant"]): row for row in load_jsonl(root / STRUCTURE_PATH)}
    components = {str(row["component_id"]): row for row in load_jsonl(root / P2_COMPONENTS_PATH)}
    rules = load_jsonl(root / P2_RULES_PATH)
    instruction_digest = sha256_file(root / AUTHOR_INSTRUCTION_PATH)
    rows: list[dict[str, Any]] = []
    for assignment in assignments:
        profile_id = str(assignment["profile_id"])
        variant = str(assignment["assigned_variant"])
        structure = structures[(profile_id, variant)]
        selected_components = [
            {
                "component_id": component_id,
                "component_role": components[component_id]["component_role"],
                "component_digest": components[component_id]["component_digest"],
                "mechanism": components[component_id]["mechanism"],
                "claim_boundary": components[component_id]["claim_boundary"],
            }
            for component_id in structure["selected_component_ids"]
        ]
        request: dict[str, Any] = {
            "schema_version": "gate1-p3-controlled-author-request-v0.1",
            "task_id": TASK_ID,
            "request_id": f"P3-OPEN-POSITIVE-{profile_id}",
            "profile_id": profile_id,
            "assigned_variant": variant,
            "run_order": assignment["run_order"],
            "author_identity": AUTHORIZED_AUTHOR_IDENTITY,
            "author_session_logical_id": AUTHORIZED_AUTHOR_SESSION,
            "author_model_label": AUTHORIZED_AUTHOR_MODEL_LABEL,
            "author_model_capability_id": AUTHORIZED_AUTHOR_CAPABILITY_ID,
            "author_instruction_path": AUTHOR_INSTRUCTION_PATH.as_posix(),
            "author_instruction_sha256": instruction_digest,
            "user_goal": "Write one synthetic, qualification-only first output that faithfully realizes the frozen product and structure.",
            "platform": list(profiles[profile_id].get("target_platforms", [])),
            "account_expression_identity": list(profiles[profile_id].get("target_account_roles", [])),
            "profile_contract": copy.deepcopy(profiles[profile_id]),
            "typed_material": copy.deepcopy(materials[profile_id]),
            "structure_contract": {
                "record_id": structure["record_id"],
                "record_digest": structure["record_digest"],
                "axis_values": structure["axis_values"],
                "axis_programs": structure["axis_programs"],
                "addressable_outputs": structure["addressable_outputs"],
                "component_contributions": structure["component_contributions"],
            },
            "approved_components": selected_components,
            "control_rules": rules,
            "required_output_surface_order": [
                "title",
                "body",
                "spoken_lines",
                "cta",
                "visual_execution",
                "audio_execution",
            ],
            "single_first_output_only": True,
            "external_provider_allowed": False,
            "synthetic_qualification_only": True,
            "publishable": False,
            "runtime_consumable": False,
            "counts_toward_300": False,
        }
        request["request_digest"] = object_digest(request, "request_digest")
        rows.append(request)
    return rows


def _route_selection(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gold_rows = load_jsonl(root / ROUTE_GOLD_PATH)
    input_by_case = {str(row["case_id"]): row for row in load_jsonl(root / ROUTE_INPUT_PATH)}
    by_profile: dict[str, list[dict[str, Any]]] = {}
    for row in gold_rows:
        by_profile.setdefault(str(row["profile_id"]), []).append(row)
    block_profiles = sorted(
        profile_id
        for profile_id, rows in by_profile.items()
        if any(
            row["gold_primary_action"] == "BLOCK"
            and "RISK-OR-INPUT" in str(row["case_id"])
            for row in rows
        )
    )
    request_profiles = sorted(
        profile_id
        for profile_id, rows in by_profile.items()
        if profile_id not in block_profiles
        and any(
            row["gold_primary_action"] == "REQUEST_INPUT"
            and row["gold_reason_code"] == "授权缺失"
            for row in rows
        )
    )[:6]
    require(len(block_profiles) == 7 and len(request_profiles) == 6, "E_P3_ROUTE_BALANCE_PRECONDITION")
    selections: list[dict[str, Any]] = []
    selected_inputs: list[dict[str, Any]] = []
    for profile_id in sorted(by_profile):
        rows = by_profile[profile_id]
        if profile_id in block_profiles:
            candidates = [
                row
                for row in rows
                if row["gold_primary_action"] == "BLOCK"
                and "RISK-OR-INPUT" in str(row["case_id"])
            ]
            rationale = "PREFER_HIGH_RISK_BLOCK_CASE"
        elif profile_id in request_profiles:
            candidates = [
                row
                for row in rows
                if row["gold_primary_action"] == "REQUEST_INPUT"
                and row["gold_reason_code"] == "授权缺失"
            ]
            rationale = "PREFER_HIGH_RISK_AUTHORIZATION_REQUEST_CASE"
        else:
            candidates = [row for row in rows if row["gold_primary_action"] == "DEGRADE"]
            rationale = "BALANCE_WITH_PROFILE_ALLOWED_PARTIAL_SAFE_CASE"
        require(len(candidates) == 1, "E_P3_ROUTE_SELECTION_UNIQUE", profile_id)
        gold = candidates[0]
        case_id = str(gold["case_id"])
        input_record = input_by_case.get(case_id)
        require(input_record is not None, "E_P3_ROUTE_INPUT_MISSING", case_id)
        selection = {
            "selection_id": f"P3-ROUTE-SELECTION-{profile_id}",
            "profile_id": profile_id,
            "case_id": case_id,
            "selection_rule": "GROUP_BY_PROFILE_THEN_HIGH_RISK_AND_ACTION_BALANCE_V0_1",
            "selection_rationale": rationale,
            "frozen_gold_answer_digest_reference": gold["gold_answer_digest"],
            "gold_answer_not_exposed_to_route_engine": True,
        }
        selection["selection_digest"] = object_digest(selection, "selection_digest")
        selections.append(selection)
        selected_inputs.append(copy.deepcopy(input_record))
    action_counts = {
        action: sum(
            next(row for row in gold_rows if row["case_id"] == selection["case_id"])["gold_primary_action"] == action
            for selection in selections
        )
        for action in ("BLOCK", "REQUEST_INPUT", "DEGRADE")
    }
    require(action_counts == {"BLOCK": 7, "REQUEST_INPUT": 6, "DEGRADE": 7}, "E_P3_ROUTE_ACTION_BALANCE")
    return selections, selected_inputs


def _freeze_manifest(
    root: Path,
    model: dict[str, Any],
    assignments: list[dict[str, Any]],
    author_requests: list[dict[str, Any]],
    route_selections: list[dict[str, Any]],
    route_inputs: list[dict[str, Any]],
    historical_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "gate1-p3-open-freeze-manifest-v0.1",
        "task_id": TASK_ID,
        "baseline_commit": BASELINE_COMMIT,
        "freeze_state": "FROZEN_BEFORE_AUTHORING",
        "component_set": {"path": P2_COMPONENTS_PATH.as_posix(), "sha256": sha256_file(root / P2_COMPONENTS_PATH)},
        "control_rule_set": {"path": P2_RULES_PATH.as_posix(), "sha256": sha256_file(root / P2_RULES_PATH)},
        "edge_set": {"path": P2_EDGES_PATH.as_posix(), "sha256": sha256_file(root / P2_EDGES_PATH)},
        "path_set": {"path": P2_PATHS_PATH.as_posix(), "sha256": sha256_file(root / P2_PATHS_PATH)},
        "p2_core": {"path": (P2_ROOT / "p2_generator_core_r6.py").as_posix(), "sha256": sha256_file(root / P2_ROOT / "p2_generator_core_r6.py")},
        "p3_structure": {"path": STRUCTURE_PATH.as_posix(), "sha256": sha256_file(root / STRUCTURE_PATH), "count": 80},
        "positive_assignments": {"path": POSITIVE_ASSIGNMENT_PATH.as_posix(), "sha256": digest_object(assignments), "count": 20},
        "author_instruction": {"path": AUTHOR_INSTRUCTION_PATH.as_posix(), "sha256": sha256_file(root / AUTHOR_INSTRUCTION_PATH)},
        "author_model_config": {"path": AUTHOR_MODEL_PATH.as_posix(), "object_digest": model["model_session_digest"]},
        "author_requests": {"path": AUTHOR_REQUEST_PATH.as_posix(), "sha256": digest_object(author_requests), "count": 20},
        "route_selections": {"path": ROUTE_SELECTION_PATH.as_posix(), "sha256": digest_object(route_selections), "count": 20},
        "route_inputs": {"path": ROUTE_INPUT_FREEZE_PATH.as_posix(), "sha256": digest_object(route_inputs), "count": 20},
        "profile_contract": {"path": PROFILE_PATH.as_posix(), "sha256": sha256_file(root / PROFILE_PATH)},
        "standard": {"path": STANDARD_PATH.as_posix(), "sha256": sha256_file(root / STANDARD_PATH)},
        "historical_integrity_manifest": {"path": HISTORICAL_MANIFEST_PATH.as_posix(), "sha256": digest_object(historical_rows), "count": len(historical_rows)},
        "p3_core_sources": [
            {"path": (TASK_ROOT / name).as_posix(), "sha256": sha256_file(root / TASK_ROOT / name)}
            for name in ("p3_common.py", "p3_structure.py", "p3_prepare.py", "p3_open_core.py")
        ],
        "randomness_policy": "NO_VISIBLE_SEED__SINGLE_OUTPUT__NO_REROLL",
        "model_unexposed_parameters": "PLATFORM_NOT_EXPOSED__NOT_GUESSED",
        "component_supplement_window_used": False,
        "open_core_repair_window_used": False,
        "counts_toward_300": 0,
        "readiness": readiness_false(),
    }
    document["freeze_manifest_digest"] = object_digest(document, "freeze_manifest_digest")
    return document


def build_prepare_documents(
    root: Path = ROOT, include_current_pointer: bool = True
) -> dict[str, bytes]:
    check_structure(root)
    verify_pins(root, include_current_pointer=include_current_pointer)
    assignments = _positive_assignments(root)
    author_requests = _author_requests(root, assignments)
    route_selections, route_inputs = _route_selection(root)
    historical_rows = _historical_manifest(root)
    model = {
        "schema_version": "gate1-p3-author-model-v0.1",
        "task_id": TASK_ID,
        "author_identity": AUTHORIZED_AUTHOR_IDENTITY,
        "logical_session_id": AUTHORIZED_AUTHOR_SESSION,
        "model_display_name": AUTHORIZED_AUTHOR_MODEL_LABEL,
        "model_capability_id": AUTHORIZED_AUTHOR_CAPABILITY_ID,
        "service_tier": "priority",
        "reasoning_effort": "high",
        "temperature": "PLATFORM_NOT_EXPOSED",
        "seed": "PLATFORM_NOT_EXPOSED",
        "hidden_configuration": "PLATFORM_NOT_EXPOSED__NOT_GUESSED",
        "single_author_identity_for_all_20": True,
        "may_create_second_author": False,
        "may_reroll": False,
        "may_review_own_output": False,
        "external_provider_allowed": False,
    }
    model["model_session_digest"] = object_digest(model, "model_session_digest")
    manifest = _freeze_manifest(
        root,
        model,
        assignments,
        author_requests,
        route_selections,
        route_inputs,
        historical_rows,
    )
    prepare_result = {
        "p3_prepare_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "result_state": "FROZEN_READY_FOR_SINGLE_CONTROLLED_AUTHOR",
            "structure_80_pass": True,
            "targeted_component_window_used": False,
            "component_addition_count": 0,
            "positive_request_count": 20,
            "route_input_count": 20,
            "author_output_count": 0,
            "external_provider_request_count": 0,
            "external_api_call_count": 0,
            "credential_read_count": 0,
            "counts_toward_300": 0,
            "readiness": readiness_false(),
        }
    }
    prepare_result["p3_prepare_result"]["result_digest"] = object_digest(
        prepare_result["p3_prepare_result"], "result_digest"
    )
    return {
        AUTHOR_MODEL_PATH.as_posix(): yaml_bytes(model),
        POSITIVE_ASSIGNMENT_PATH.as_posix(): jsonl_bytes(assignments),
        AUTHOR_REQUEST_PATH.as_posix(): jsonl_bytes(author_requests),
        ROUTE_SELECTION_PATH.as_posix(): jsonl_bytes(route_selections),
        ROUTE_INPUT_FREEZE_PATH.as_posix(): jsonl_bytes(route_inputs),
        HISTORICAL_MANIFEST_PATH.as_posix(): jsonl_bytes(historical_rows),
        FREEZE_MANIFEST_PATH.as_posix(): yaml_bytes({"p3_open_baseline_manifest": manifest}),
        PREPARE_RESULT_PATH.as_posix(): yaml_bytes(prepare_result),
    }


def materialize_prepare(root: Path = ROOT) -> list[Path]:
    documents = build_prepare_documents(root)
    changed: list[Path] = []
    for relative, payload in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
            changed.append(path)
    return changed


def check_prepare(root: Path = ROOT, include_current_pointer: bool = True) -> None:
    verify_pins(root, include_current_pointer=include_current_pointer)
    documents = build_prepare_documents(
        root, include_current_pointer=include_current_pointer
    )
    for relative, expected in documents.items():
        path = root / relative
        require(path.is_file(), "E_P3_PREPARE_FILE_MISSING", relative)
        require(path.read_bytes() == expected, "E_P3_PREPARE_DRIFT", relative)


__all__ = [
    "AUTHOR_INSTRUCTION_PATH",
    "AUTHOR_MODEL_PATH",
    "AUTHOR_REQUEST_PATH",
    "FREEZE_MANIFEST_PATH",
    "HISTORICAL_MANIFEST_PATH",
    "POSITIVE_ASSIGNMENT_PATH",
    "PREPARE_RESULT_PATH",
    "ROUTE_INPUT_FREEZE_PATH",
    "ROUTE_SELECTION_PATH",
    "build_prepare_documents",
    "check_prepare",
    "materialize_prepare",
    "verify_pins",
]
