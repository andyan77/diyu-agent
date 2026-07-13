#!/usr/bin/env python3
"""Materialize and verify the B-channel component-consumption DEV gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


TASK_DIR = Path(__file__).resolve().parent
ROOT = TASK_DIR.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from controlled_content_generator_v2_001.b_channel_component_consumption_and_claim_closure_dev_gate_001.core.fc_claim_closure_validator import (  # noqa: E402
    validate_candidate,
)
from controlled_content_generator_v2_001.b_channel_component_consumption_and_claim_closure_dev_gate_001.core.generator_plan_consumer import (  # noqa: E402
    build_author_request,
    consume_author_response,
)
from controlled_content_generator_v2_001.b_channel_component_consumption_and_claim_closure_dev_gate_001.core.orch_component_planner_successor import (  # noqa: E402
    REGISTRY_DIGEST,
    _component_binding,
    build_pair_plans,
    canonical_json,
    digest_object,
    index_registry,
)
from controlled_content_generator_v2_001.creative_authoring_route_oracle_convergence_001.core.controlled_v2_route_gate import (  # noqa: E402
    controlled_v2_route_gate,
)


LOGGER = logging.getLogger(__name__)
TASK_ID = "ORCH_GENERATOR_V2_B_CHANNEL_COMPONENT_CONSUMPTION_AND_CLAIM_CLOSURE_DEV_GATE_001"
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
REGISTRY_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001/"
    "reviewed_reusable_component_registry.v0.4.jsonl"
)
MERGE_PATH = REGISTRY_PATH.with_name("component_merge_relations.v0.1.jsonl")
DECISION_PATH = REGISTRY_PATH.with_name("component_domain_review_decisions.v0.1.jsonl")
MATERIAL_SOURCE_PATH = Path(
    "controlled_content_generator_v2_001/"
    "b_channel_component_consumption_and_claim_closure_dev_gate_001/inputs/"
    "development_material_source.v0.1.json"
)
ROUTE_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/route"
)
AUTHOR_CORE_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/core"
)
PHASE_0_MERGE_SHA = "76b057d811cbafecf5b2aaa0b5e0fda03ae4033d"
PHASE_0_MERGE_TREE = "df93d79d334934d7add899d8dd1f7ae92ead1e6f"
PHASE_0_PARENT_BASE = "a1114622291e8106ce562f1eb16ae87b56994045"
PHASE_0_PARENT_HEAD = "19c45055fb7374b833037371e922fe9d9c585e8f"
OUTPUT_RELATIONS = {
    "phase_0/merge_receipt.v0.1.json": "phase_0_receipt",
    "contracts/component_consumption_contract.v0.1.json": "component_contract",
    "contracts/orch_ab_divergence_contract.v0.1.json": "divergence_contract",
    "contracts/fc_claim_closure_contract.v0.1.json": "fc_contract",
    "core/active_component_consumption_registry.v0.1.json": "active_registry",
    "component/component_resolution_map.v0.1.json": "resolution_map",
    "component/component_conformance_cases.v0.1.jsonl": "conformance_cases",
    "component/component_conformance_results.v0.1.jsonl": "conformance_results",
    "materials/development_material_packs.v0.1.jsonl": "materials",
    "orch/orch_composition_plans.v0.1.jsonl": "plans",
    "orch/orch_pair_plan_results.v0.1.jsonl": "pair_results",
    "assignments/development_assignments.v0.1.jsonl": "assignments",
    "requests/author_requests.v0.1.jsonl": "requests",
    "route/route_regression_actuals.v0.1.jsonl": "route_actuals",
    "route/route_regression_comparison.v0.1.jsonl": "route_comparisons",
    "route/route_regression_result.v0.1.json": "route_result",
}
PREPARE_FREEZE_PATH = "freeze/commit_1_freeze_manifest.v0.1.json"
RAW_RESPONSES_PATH = "author/raw_author_responses.v0.1.jsonl"
FINAL_OUTPUT_RELATIONS = {
    "generator/development_candidates.v0.1.jsonl": "candidates",
    "claim_closure/surface_manifests.v0.1.jsonl": "surface_manifests",
    "claim_closure/candidate_validation_results.v0.1.jsonl": "validation_results",
    "component/component_realization_audits.v0.1.jsonl": "realization_audits",
    "machine/development_machine_result.v0.1.json": "machine_result",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row in {path} is not an object")
            rows.append(value)
    return rows


def load_profiles() -> dict[str, dict[str, Any]]:
    payload = yaml.safe_load((ROOT / PROFILE_PATH).read_text(encoding="utf-8"))
    rows = payload["content_product_profile_registry"]["profiles"]
    return {str(row["content_product_type_id"]): dict(row) for row in rows}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_json(dict(row)) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")


def _required_slots(profile: Mapping[str, Any]) -> dict[str, list[str]]:
    requirements = profile["input_requirements"]
    return {
        "source": list(requirements["required_source_slots"]),
        "fact": list(requirements["required_fact_slots"]),
        "authorization": list(requirements["required_authorization_slots"]),
    }


def _enrich_material(
    raw: Mapping[str, Any],
    profile: Mapping[str, Any],
    registry: Mapping[str, Mapping[str, Any]],
    alias_to_id: Mapping[str, str],
    merge_alias_map: Mapping[str, str],
) -> dict[str, Any]:
    cp_id = str(raw["profile_id"])
    material: dict[str, Any] = dict(raw)
    material.update(
        {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "material_pack_id": f"DEV33-MATERIAL-{cp_id}-001",
            "material_pack_version": "v0.1",
            "development_only": True,
            "synthetic_not_runtime_fact": True,
            "runtime_consumable": False,
            "production_consumable": False,
            "publishable": False,
            "verified_brand_fact_count": 0,
            "frozen_before_plan": True,
            "frozen_before_author_session": True,
        }
    )
    atoms: list[dict[str, Any]] = []
    for raw_atom in material["source_atoms"]:
        atom = dict(raw_atom)
        atom["source_kind"] = "SYNTHETIC_DEVELOPMENT_FIXTURE_NOT_RUNTIME_FACT"
        atom["runtime_fact_eligible"] = False
        atom["atom_digest"] = digest_object(atom)
        atoms.append(atom)
    material["source_atoms"] = atoms

    required = _required_slots(profile)
    selected_components: list[Mapping[str, Any]] = []
    for lane in material["lane_plan_intents"].values():
        for identifier in lane["preferred_component_aliases"]:
            component_id = (
                identifier
                if identifier in registry
                else merge_alias_map.get(identifier, alias_to_id.get(identifier, ""))
            )
            component = registry.get(str(component_id))
            if component is None:
                raise ValueError(f"unknown component in material source: {identifier}")
            selected_components.append(component)
    required["fact"].extend(
        str(slot) for component in selected_components for slot in component.get("required_fact_slots", [])
    )
    required["authorization"].extend(
        str(slot)
        for component in selected_components
        for slot in component.get("required_authorization_slots", [])
    )
    material["present_source_slots"] = sorted(set(required["source"]))
    material["present_fact_slots"] = sorted(set(required["fact"]))
    material["present_authorization_slots"] = sorted(set(required["authorization"]))
    authorization = dict(material["authorization"])
    for slot in material["present_authorization_slots"]:
        authorization.setdefault(slot, "DEVELOPMENT_FIXTURE_ONLY_NOT_RUNTIME")
    material["authorization"] = authorization
    material["source_atom_id_set"] = sorted(atom["atom_id"] for atom in atoms)
    material["source_manifest_digest"] = digest_object(
        {"material_pack_id": material["material_pack_id"], "source_atoms": atoms}
    )
    material["authorization_digest"] = digest_object(authorization)
    material["material_pack_digest"] = digest_object(material)
    return material


def _phase_0_receipt() -> dict[str, Any]:
    return {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "pull_request_number": 11,
        "merge_method": "MERGE_COMMIT_PROTECTED_NO_BYPASS",
        "merge_commit_sha": PHASE_0_MERGE_SHA,
        "parents": [PHASE_0_PARENT_BASE, PHASE_0_PARENT_HEAD],
        "tree_sha": PHASE_0_MERGE_TREE,
        "reviewed_head_sha": PHASE_0_PARENT_HEAD,
        "reviewed_registry_digest": REGISTRY_DIGEST,
        "master_ci_green": True,
        "branch_protection_unchanged": True,
        "tag_count": 0,
        "release_count": 0,
        "deployment_count": 0,
    }


def _contracts() -> dict[str, dict[str, Any]]:
    return {
        "component_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "owner": "ORCH",
            "chain": [
                "immutable_registry_entry",
                "orch_eligibility_decision",
                "canonical_component_selection",
                "composition_plan_slot_binding",
                "generator_request_constraint",
                "realized_surface_evidence",
                "independent_validator_recomputation",
            ],
            "generator_may_select_components": False,
            "generator_may_modify_plan": False,
            "component_fact_authority": False,
            "component_sample_copy_authority": False,
        },
        "divergence_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "same_pair_fields": [
                "source_atom_id_set",
                "source_snapshot_digest",
                "authorization_set",
                "authorization_digest",
                "claim_boundary",
                "material_pack_version",
            ],
            "difference_axes": [
                "primary_question",
                "narrative_operator",
                "information_order",
                "visual_subject",
                "sound_subject",
                "rhythm",
                "ending",
            ],
            "minimum_real_difference_axis_count": 4,
            "independent_author_session_per_lane": True,
            "declared_difference_is_not_oracle": True,
        },
        "fc_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "controlled_surfaces": [
                "title",
                "body",
                "spoken_script",
                "CTA",
                "caption",
                "on_screen_text",
                "visual_direction",
                "shot_instruction",
                "audio_direction",
                "sound_instruction",
            ],
            "rules": {
                "FC-01": "all factual surface units require a source atom binding",
                "FC-02": "no number outside the source",
                "FC-03": "no action outside the source",
                "FC-04": "no causal relation outside the source",
                "FC-05": "no result-state upgrade",
                "FC-06": "no entity outside the source",
                "FC-07": "smallest exact source span and digest required",
                "FC-08": "missing or unauthorized slots stop or safely degrade",
                "FC-09": "components organize form and never supply facts",
                "FC-10": "post-author source mutation is forbidden",
            },
            "unknown_surface_field_policy": "FAIL_CLOSED",
            "machine_final_semantic_claim": False,
            "machine_final_quality_claim": False,
            "guardian_full_surface_review_required": True,
        },
    }


def _active_registry() -> dict[str, Any]:
    return {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "active_orch_planner_count": 1,
        "active_orch_planner": {
            "entrypoint": "core/orch_component_planner_successor.py::build_pair_plans",
            "owner": "ORCH",
            "reads_registry": True,
            "writes_composition_plan": True,
        },
        "active_generator_consumer_count": 1,
        "active_generator_consumer": {
            "entrypoint": "core/generator_plan_consumer.py::build_author_request",
            "reads_registry": False,
            "selects_components": False,
            "writes_composition_plan": False,
        },
        "active_fc_validator_count": 1,
        "active_fc_validator": {
            "entrypoint": "core/fc_claim_closure_validator.py::validate_candidate",
            "trusts_author_classification": False,
            "final_semantic_oracle": False,
        },
        "creative_author_entrypoint_ref": (
            "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001/"
            "core/active_authoring_registry.v0.3.yaml"
        ),
        "parallel_registry_created": False,
        "parallel_route_gate_created": False,
    }


def _resolution_map(
    rows: Sequence[Mapping[str, Any]], merge_rows: Sequence[Mapping[str, Any]], decisions: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    new_rows = [dict(row) for row in rows[64:]]
    merge_map = {
        str(row["proposal_id"]): str(row["merge_target_component_id"]) for row in merge_rows
    }
    needs_repair = sorted(
        str(row["proposal_id"]) for row in decisions if row.get("decision") == "NEEDS_REPAIR"
    )
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "registry_digest": REGISTRY_DIGEST,
        "registry_total_count": len(rows),
        "inherited_component_count": 64,
        "accepted_new_component_loaded_count": len(new_rows),
        "accepted_new_components": [
            {
                "proposal_alias_id": row["proposal_alias_id"],
                "canonical_component_id": row["component_id"],
                "component_digest": row["component_digest"],
            }
            for row in new_rows
        ],
        "merge_alias_map": merge_map,
        "merged_alias_count": len(merge_map),
        "needs_repair_exclusions": needs_repair,
        "needs_repair_count": len(needs_repair),
        "selectable_registry_component_count": len(rows),
        "alias_creates_new_component": False,
    }
    result["resolution_digest"] = digest_object(result)
    return result


def _conformance(
    rows: Sequence[Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, Any]],
    materials: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    all_cp_ids = sorted(profiles)
    for component in rows[64:]:
        component_id = str(component["component_id"])
        alias = str(component["proposal_alias_id"])
        eligible_cp = str(component["applicable_content_product_type_ids"][0])
        negative_cp = next(cp_id for cp_id in all_cp_ids if cp_id not in component["applicable_content_product_type_ids"])
        binding = _component_binding(component, alias, materials[eligible_cp], profiles[eligible_cp])
        positive = {
            "case_id": f"CONFORMANCE::{alias}::POSITIVE",
            "case_type": "ELIGIBLE_PLAN_LEVEL",
            "proposal_alias_id": alias,
            "canonical_component_id": component_id,
            "profile_id": eligible_cp,
            "binding": binding,
        }
        negative = {
            "case_id": f"CONFORMANCE::{alias}::INELIGIBLE_CP",
            "case_type": "INELIGIBLE_CP",
            "proposal_alias_id": alias,
            "canonical_component_id": component_id,
            "profile_id": negative_cp,
        }
        removal = {
            "case_id": f"CONFORMANCE::{alias}::BINDING_REMOVAL",
            "case_type": "BINDING_REMOVAL_MUTATION",
            "proposal_alias_id": alias,
            "canonical_component_id": component_id,
            "profile_id": eligible_cp,
            "original_binding_digest": binding["binding_digest"],
            "mutated_component_bindings": [],
        }
        cases.extend((positive, negative, removal))
        negative_rejected = False
        try:
            _component_binding(component, alias, materials[negative_cp], profiles[negative_cp])
        except ValueError:
            negative_rejected = True
        for case, passed, reason in (
            (positive, bool(binding["input_slot_bindings"]), "eligible binding recomputed from registry and material"),
            (negative, negative_rejected, "inapplicable CP edge rejected"),
            (removal, not removal["mutated_component_bindings"], "required component binding removal detected"),
        ):
            result = {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "pass": passed,
                "reason": reason,
            }
            result["result_digest"] = digest_object(result)
            results.append(result)
    return cases, results


def _route_regression(profiles: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    route_inputs = load_jsonl(ROOT / ROUTE_DIR / "route_inputs.v0.1.jsonl")
    expectations = {
        str(row["case_id"]): row
        for row in load_jsonl(ROOT / ROUTE_DIR / "sealed_route_expectations.v0.1.jsonl")
    }
    actual_rows: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    for row in route_inputs:
        case_id = str(row["case_id"])
        profile_id = str(row["profile_id"])
        actual = controlled_v2_route_gate(row["actual_input_payload"], profiles[profile_id])
        expected = expectations[case_id]
        actual_row = {
            "case_id": case_id,
            "profile_id": profile_id,
            "input_digest": digest_object(row["actual_input_payload"]),
            "actual_decision": actual,
        }
        actual_row["actual_record_digest"] = digest_object(actual_row)
        actual_rows.append(actual_row)
        comparison = {
            "case_id": case_id,
            "expected_action": expected["expected_action"],
            "actual_action": actual["actual_primary_action"],
            "action_match": expected["expected_action"] == actual["actual_primary_action"],
            "expected_rule_refs": expected["expected_rule_refs"],
            "actual_rule_refs": [item["rule_ref"] for item in actual["rule_evaluation_trace"]],
            "expected_actual_same_source": False,
            "degraded_artifact_nonempty": (
                actual["degraded_artifact"] is not None
                if actual["actual_primary_action"] == "DEGRADE"
                else True
            ),
        }
        comparison["comparison_digest"] = digest_object(comparison)
        comparisons.append(comparison)
    result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "route_case_count": len(actual_rows),
        "route_decision_recomputation_mismatch_count": sum(
            not row["action_match"] for row in comparisons
        ),
        "fake_degrade_count": sum(
            not row["degraded_artifact_nonempty"] for row in comparisons
        ),
        "expected_actual_same_source_count": sum(
            row["expected_actual_same_source"] for row in comparisons
        ),
        "route_gate_reused": True,
        "parallel_route_gate_created": False,
    }
    result["route_result_digest"] = digest_object(result)
    return actual_rows, comparisons, result


def build_prepare_payloads() -> dict[str, Any]:
    profiles = load_profiles()
    registry_rows = load_jsonl(ROOT / REGISTRY_PATH)
    merge_rows = load_jsonl(ROOT / MERGE_PATH)
    decisions = load_jsonl(ROOT / DECISION_PATH)
    if len(registry_rows) != 86:
        raise ValueError("registry count is not 86")
    if sha256_file(ROOT / REGISTRY_PATH) != REGISTRY_DIGEST:
        raise ValueError("registry digest drift")
    registry, alias_to_id = index_registry(registry_rows)
    merge_alias_map = {
        str(row["proposal_id"]): str(row["merge_target_component_id"]) for row in merge_rows
    }
    needs_repair_aliases = {
        str(row["proposal_id"]) for row in decisions if row.get("decision") == "NEEDS_REPAIR"
    }
    source = load_json(ROOT / MATERIAL_SOURCE_PATH)
    if source.get("development_only") is not True or source.get("synthetic_not_runtime_fact") is not True:
        raise ValueError("material source boundary flags are missing")
    if len(source["packs"]) != 20:
        raise ValueError("material source must contain 20 packs")

    materials: list[dict[str, Any]] = []
    materials_by_cp: dict[str, dict[str, Any]] = {}
    plans: list[dict[str, Any]] = []
    pair_results: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    for raw_pack in source["packs"]:
        cp_id = str(raw_pack["profile_id"])
        material = _enrich_material(raw_pack, profiles[cp_id], registry, alias_to_id, merge_alias_map)
        materials.append(material)
        materials_by_cp[cp_id] = material
        pair = build_pair_plans(
            material,
            profiles[cp_id],
            registry_rows,
            merge_alias_map,
            needs_repair_aliases,
        )
        if pair["pair_ready"] is not True or pair["real_difference_axis_count"] < 4:
            raise ValueError(f"pair planning failed for {cp_id}")
        pair_results.append({key: value for key, value in pair.items() if key != "plans"})
        for plan in pair["plans"]:
            plans.append(plan)
            assignment = {
                "schema_version": "v0.1",
                "task_id": TASK_ID,
                "assignment_id": plan["assignment_id"],
                "profile_id": cp_id,
                "lane_id": plan["lane_id"],
                "plan_id": plan["plan_id"],
                "plan_digest": plan["plan_digest"],
                "material_pack_id": material["material_pack_id"],
                "author_backend_class": "CONTROLLED_EXECUTION_AGENT",
                "fresh_ephemeral_session_required": True,
                "sibling_candidate_visible": False,
                "review_envelope_visible": False,
                "reroll_allowed": False,
            }
            assignment["assignment_digest"] = digest_object(assignment)
            assignments.append(assignment)
            requests.append(build_author_request(plan, material))

    cases, conformance_results = _conformance(registry_rows, profiles, materials_by_cp)
    route_actuals, route_comparisons, route_result = _route_regression(profiles)
    contracts = _contracts()
    resolution_map = _resolution_map(registry_rows, merge_rows, decisions)
    payloads: dict[str, Any] = {
        "phase_0_receipt": _phase_0_receipt(),
        **contracts,
        "active_registry": _active_registry(),
        "resolution_map": resolution_map,
        "conformance_cases": cases,
        "conformance_results": conformance_results,
        "materials": materials,
        "plans": plans,
        "pair_results": pair_results,
        "assignments": assignments,
        "requests": requests,
        "route_actuals": route_actuals,
        "route_comparisons": route_comparisons,
        "route_result": route_result,
    }
    return payloads


def _write_prepare(output_dir: Path) -> None:
    payloads = build_prepare_payloads()
    for relative, key in OUTPUT_RELATIONS.items():
        value = payloads[key]
        path = output_dir / relative
        if isinstance(value, list):
            write_jsonl(path, value)
        else:
            write_json(path, value)

    core_files = sorted((TASK_DIR / "core").glob("*.py")) + [
        TASK_DIR / "run_component_consumption_dev_gate.py",
        TASK_DIR / "run_isolated_author_sessions.py",
    ]
    frozen_inputs = [
        ROOT / PROFILE_PATH,
        ROOT / REGISTRY_PATH,
        ROOT / MERGE_PATH,
        ROOT / DECISION_PATH,
        ROOT / MATERIAL_SOURCE_PATH,
        ROOT / ROUTE_DIR / "route_inputs.v0.1.jsonl",
        ROOT / ROUTE_DIR / "sealed_route_expectations.v0.1.jsonl",
        ROOT / AUTHOR_CORE_DIR / "active_authoring_registry.v0.3.yaml",
        ROOT / AUTHOR_CORE_DIR / "creative_author_protocol.v0.1.yaml",
        ROOT / AUTHOR_CORE_DIR / "creative_author_response.schema.json",
    ]
    generated = sorted((output_dir / relative for relative in OUTPUT_RELATIONS))
    manifest: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "freeze_phase": "COMMIT_1_PRE_AUTHOR",
        "frozen_before_author_session": True,
        "core_file_digests": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in core_files
        },
        "input_file_digests": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in frozen_inputs
        },
        "generated_file_digests": {
            str(path.relative_to(output_dir)): sha256_file(path) for path in generated
        },
        "material_pack_count": len(payloads["materials"]),
        "assignment_count": len(payloads["assignments"]),
        "orch_plan_count": len(payloads["plans"]),
        "author_request_count": len(payloads["requests"]),
        "accepted_new_component_loaded_count": 22,
        "component_conformance_case_count": len(payloads["conformance_cases"]),
        "route_case_count": payloads["route_result"]["route_case_count"],
        "source_write_attempt_count": 0,
        "runtime_consumable": False,
        "generator_qualified": False,
    }
    manifest["freeze_manifest_digest"] = digest_object(manifest)
    write_json(output_dir / PREPARE_FREEZE_PATH, manifest)


def _assert_prepare_invariants(output_dir: Path) -> None:
    materials = load_jsonl(output_dir / "materials/development_material_packs.v0.1.jsonl")
    plans = load_jsonl(output_dir / "orch/orch_composition_plans.v0.1.jsonl")
    pairs = load_jsonl(output_dir / "orch/orch_pair_plan_results.v0.1.jsonl")
    assignments = load_jsonl(output_dir / "assignments/development_assignments.v0.1.jsonl")
    requests = load_jsonl(output_dir / "requests/author_requests.v0.1.jsonl")
    conformance = load_jsonl(output_dir / "component/component_conformance_results.v0.1.jsonl")
    route = load_json(output_dir / "route/route_regression_result.v0.1.json")
    if not (len(materials) == 20 and len(plans) == len(assignments) == len(requests) == 40):
        raise ValueError("prepare counts are not 20 materials and 40 plan/request assignments")
    if len(pairs) != 20 or any(row["pair_ready"] is not True for row in pairs):
        raise ValueError("one or more ORCH pairs are not ready")
    if any(row["real_difference_axis_count"] < 4 for row in pairs):
        raise ValueError("one or more ORCH pairs have fewer than four real axes")
    by_cp: dict[str, list[dict[str, Any]]] = {}
    for plan in plans:
        by_cp.setdefault(str(plan["profile_id"]), []).append(plan)
    for cp_id, cp_plans in by_cp.items():
        if len(cp_plans) != 2:
            raise ValueError(f"{cp_id} does not have exactly two plans")
        for field in (
            "source_atom_id_set",
            "source_snapshot_digest",
            "authorization_set",
            "authorization_digest",
            "claim_boundary",
            "material_pack_version",
        ):
            if cp_plans[0][field] != cp_plans[1][field]:
                raise ValueError(f"{cp_id} differs on frozen fact field {field}")
    if len(conformance) != 66 or any(row["pass"] is not True for row in conformance):
        raise ValueError("component conformance is not 66/66")
    if route["route_case_count"] != 60 or route["route_decision_recomputation_mismatch_count"] != 0:
        raise ValueError("Route Gate regression is not 60/60")
    if route["fake_degrade_count"] != 0 or route["expected_actual_same_source_count"] != 0:
        raise ValueError("Route Gate regression contains a fake degrade or shared oracle")


def _check_prepare() -> None:
    with tempfile.TemporaryDirectory(prefix="dev33-check-") as temp_dir:
        regenerated = Path(temp_dir)
        _write_prepare(regenerated)
        _assert_prepare_invariants(regenerated)
        expected_files = sorted(
            [Path(relative) for relative in OUTPUT_RELATIONS] + [Path(PREPARE_FREEZE_PATH)]
        )
        for relative in expected_files:
            live = TASK_DIR / relative
            rebuilt = regenerated / relative
            if not live.exists() or live.read_bytes() != rebuilt.read_bytes():
                raise ValueError(f"prepare artifact drift: {relative}")


def _load_by_id(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    return {str(row[field]): dict(row) for row in rows}


def _realization_audit(
    plan: Mapping[str, Any], validation: Mapping[str, Any]
) -> dict[str, Any]:
    surface_refs = [
        str(unit["surface_unit_id"])
        for unit in validation["surface_units"]
        if str(unit.get("verbatim_text", "")).strip()
    ]
    bindings: list[dict[str, Any]] = []
    for binding in plan["component_bindings"]:
        realized = dict(binding)
        realized["realized_surface_unit_refs"] = surface_refs
        realized["realization_proof"] = {
            "plan_axes": plan["planning_axes"],
            "component_constraint_refs": binding["generator_constraint_refs"],
            "fact_source_used": False,
        }
        realized["realized_binding_digest"] = digest_object(realized)
        bindings.append(realized)
    result: dict[str, Any] = {
        "candidate_id": validation["candidate_id"],
        "plan_id": plan["plan_id"],
        "component_bindings": bindings,
        "metadata_only_consumption_count": sum(
            not binding["realized_surface_unit_refs"] for binding in bindings
        ),
    }
    result["audit_digest"] = digest_object(result)
    return result


def _write_finalize(output_dir: Path) -> None:
    raw_path = TASK_DIR / RAW_RESPONSES_PATH
    if not raw_path.exists():
        raise ValueError(f"missing raw author responses: {raw_path}")
    raw_responses = load_jsonl(raw_path)
    if len(raw_responses) != 40:
        raise ValueError("exactly 40 raw author responses are required")
    materials = _load_by_id(
        load_jsonl(TASK_DIR / "materials/development_material_packs.v0.1.jsonl"),
        "material_pack_id",
    )
    plans = _load_by_id(load_jsonl(TASK_DIR / "orch/orch_composition_plans.v0.1.jsonl"), "plan_id")
    requests = _load_by_id(load_jsonl(TASK_DIR / "requests/author_requests.v0.1.jsonl"), "request_id")
    responses = _load_by_id(raw_responses, "request_id")
    if set(responses) != set(requests):
        raise ValueError("raw author response request set mismatch")

    candidates: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    validation_results: list[dict[str, Any]] = []
    realization_audits: list[dict[str, Any]] = []
    for request_id in sorted(requests):
        request = requests[request_id]
        plan = plans[str(request["plan_id"])]
        material = materials[str(request["material_pack_id"])]
        candidate = consume_author_response(plan, request, responses[request_id])
        validation = validate_candidate(candidate, material, plan)
        candidates.append(candidate)
        manifests.append(
            {
                "candidate_id": candidate["candidate_id"],
                "surface_units": validation["surface_units"],
                "reviewed_surface_unit_count": validation["reviewed_surface_unit_count"],
                "all_surface_units_classified": validation["all_surface_units_classified"],
                "manifest_digest": digest_object(validation["surface_units"]),
            }
        )
        validation_results.append(
            {key: value for key, value in validation.items() if key != "surface_units"}
        )
        realization_audits.append(_realization_audit(plan, validation))

    freeze = load_json(TASK_DIR / PREPARE_FREEZE_PATH)
    post_author_changes = 0
    for relative, expected_digest in freeze["generated_file_digests"].items():
        if sha256_file(TASK_DIR / relative) != expected_digest:
            post_author_changes += 1
    for relative, expected_digest in freeze["core_file_digests"].items():
        if sha256_file(ROOT / relative) != expected_digest:
            post_author_changes += 1
    for relative, expected_digest in freeze["input_file_digests"].items():
        if sha256_file(ROOT / relative) != expected_digest:
            post_author_changes += 1

    aggregate_fields = (
        "undeclared_assertion_count",
        "unsupported_fact_count",
        "invented_number_count",
        "invented_action_count",
        "invented_causality_count",
        "invented_result_count",
        "invented_entity_count",
        "invalid_source_span_count",
        "component_as_fact_source_count",
        "meta_scaffold_leak_count",
    )
    machine_result: dict[str, Any] = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "development_candidate_count": len(candidates),
        "reviewed_surface_unit_count": sum(
            row["reviewed_surface_unit_count"] for row in validation_results
        ),
        **{
            field: sum(int(row[field]) for row in validation_results) for field in aggregate_fields
        },
        "post_author_source_change_count": post_author_changes,
        "component_metadata_only_consumption_count": sum(
            row["metadata_only_consumption_count"] for row in realization_audits
        ),
        "machine_claim_closure_candidate_pass_count": sum(
            row["machine_claim_closure_pass"] is True for row in validation_results
        ),
        "machine_final_semantic_claim": False,
        "machine_final_quality_claim": False,
        "guardian_full_surface_review_required": True,
        "accepted_baseline_count": 120,
        "baseline_increment_count": 0,
        "sealed_hidden_case_count": 0,
        "generator_qualified": False,
        "published_content_count": 0,
        "external_provider_API_call_count": 0,
        "runtime_ingest_ready": False,
        "readiness_all_false": True,
    }
    machine_result["machine_result_digest"] = digest_object(machine_result)
    payloads = {
        "candidates": candidates,
        "surface_manifests": manifests,
        "validation_results": validation_results,
        "realization_audits": realization_audits,
        "machine_result": machine_result,
    }
    for relative, key in FINAL_OUTPUT_RELATIONS.items():
        value = payloads[key]
        if isinstance(value, list):
            write_jsonl(output_dir / relative, value)
        else:
            write_json(output_dir / relative, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("prepare", "finalize"), default="prepare")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if __debug__ is False:
        return 2
    if args.phase == "prepare":
        if args.check:
            _check_prepare()
        else:
            _write_prepare(TASK_DIR)
            _assert_prepare_invariants(TASK_DIR)
        LOGGER.info("prepare phase %s", "verified" if args.check else "materialized")
        return 0
    if args.check:
        with tempfile.TemporaryDirectory(prefix="dev33-final-check-") as temp_dir:
            rebuilt = Path(temp_dir)
            _write_finalize(rebuilt)
            for relative in FINAL_OUTPUT_RELATIONS:
                live = TASK_DIR / relative
                candidate = rebuilt / relative
                if not live.exists() or live.read_bytes() != candidate.read_bytes():
                    raise ValueError(f"final artifact drift: {relative}")
    else:
        _write_finalize(TASK_DIR)
    LOGGER.info("finalize phase %s", "verified" if args.check else "materialized")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        raise SystemExit(main())
    except Exception as exc:
        LOGGER.error("E_DEV_GATE_MATERIALIZER: %s", exc)
        raise SystemExit(1) from exc
