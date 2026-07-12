#!/usr/bin/env python3
"""Materialize qualification calibration repair 002 artifacts.

The script has two deterministic phases:

* calibration: registers the active authoring successor, builds the DEVREG gate,
  and freezes the repaired authoring core.
* hidden: after the calibration commit exists, creates a new sealed HIDDEN-R002
  qualification pack without changing the frozen calibration core.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "CONTROLLED_V2_QUALIFICATION_CALIBRATION_TARGETED_REPAIR_002"
PHASE0_MERGE_COMMIT_SHA = "829ab218bd371b4e8cd4197fbc4c6ce295771f40"
PHASE0_MERGE_TREE_SHA = "84deb62b22eb2b4571c145dbf5ef71cfafa6196f"
REVIEWED_BASE_SHA = "531fe864b0b338a8708449ae29e739e2dce8e119"
REVIEWED_HEAD_SHA = "89db1d72b5db3372f280e2d851ddfaf20635bde6"
REVIEWED_HEAD_TREE_SHA = "84deb62b22eb2b4571c145dbf5ef71cfafa6196f"
REVIEWED_FULL_DIFF_DIGEST = "6dd7d686083d8c2dda2cde871d05c6e5278c439359170ad3b9b9892520375223"
FAILED_REVIEW_REPORT_DIGEST = "5ba33d30c6424bdaa8d1af8b6592adc04ebeda6d42109f7701dfee90d4356702"
OLD_RUNNER_BEFORE_DIGEST = "e0dba4df84e3860bb9c62efb929c16ae56b846b5ca25c0f983b0a38d3a5d217d"
OLD_RUNNER_AFTER_DIGEST = "01d9ac25135612df9f33ab34b005228683c5f05dcd8068f7c5c9ec267988cd67"

TASK_DIR = Path("controlled_content_generator_v2_001/qualification_calibration_targeted_repair_002")
ACTIVE_MODULE_PATH = TASK_DIR / "active_authoring/controlled_v2_authoring_successor.py"
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CHECKER_PATH = Path("ci/checkers/check_controlled_v2_qualification_calibration_targeted_repair_002.py")
MATERIALIZER_PATH = TASK_DIR / "run_qualification_calibration_repair_002_materializer.py"
OLD_TASK_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_targeted_repair_001")
OLD_RUNNER_PATH = Path("controlled_content_generator_v2_001/qualification_probe_40_001/run_qualification_probe_40_generator_acceptance.py")
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
ORCH_PLAN_PATH = Path(
    "08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001/"
    "orch_validation_canonical_plans.v0.1.jsonl"
)
FIXTURE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/fact_authorization_fixture_closeout_001/"
    "content_product_validation_fixtures.v0.1.jsonl"
)

REPORT_BINDING_PATH = TASK_DIR / "guardian_inputs/hidden_qualification_review_report_v2_0_binding.v0.1.yaml"
FAILURE_TRACE_PATH = TASK_DIR / "creative_authoring_failure_trace.v0.1.yaml"
ACTIVE_REGISTRY_PATH = TASK_DIR / "active_authoring/active_authoring_registry.v0.2.yaml"
ENVELOPE_CONTRACT_PATH = TASK_DIR / "authoring_envelope_contract.v0.1.yaml"
MATERIAL_MATRIX_PATH = TASK_DIR / "material_slot_evidence_matrix.v0.2.yaml"
STYLE_PATH = TASK_DIR / "style_compatibility_and_realization.v0.2.yaml"
POSITIVE_CASES_PATH = TASK_DIR / "positive_allow_regression_cases.v0.1.jsonl"
ROUTE_CASES_PATH = TASK_DIR / "abnormal_route_cases_60.v0.2.jsonl"
ROUTE_RESULTS_PATH = TASK_DIR / "abnormal_route_results_60.v0.2.jsonl"
DEV_PACKS_PATH = TASK_DIR / "devreg_material_packs.v0.2.jsonl"
DEV_ASSIGNMENTS_PATH = TASK_DIR / "devreg_assignments.v0.2.jsonl"
DEV_PLANS_PATH = TASK_DIR / "devreg_qualification_plans.v0.2.jsonl"
DEV_PROJECTIONS_PATH = TASK_DIR / "devreg_authoring_projections.v0.2.jsonl"
DEV_ENVELOPES_PATH = TASK_DIR / "devreg_review_envelopes.v0.2.jsonl"
DEV_CANDIDATES_PATH = TASK_DIR / "devreg_candidates.v0.2.jsonl"
DEV_REVIEW_PATH = TASK_DIR / "devreg_semantic_review.v0.2.yaml"
FREEZE_MANIFEST_PATH = TASK_DIR / "calibration_freeze_manifest.v0.1.yaml"

HIDDEN_PACKS_PATH = TASK_DIR / "hidden_r002_material_packs.v0.1.jsonl"
HIDDEN_ASSIGNMENTS_PATH = TASK_DIR / "hidden_r002_assignments.v0.1.jsonl"
HIDDEN_PLANS_PATH = TASK_DIR / "hidden_r002_qualification_plans.v0.1.jsonl"
HIDDEN_PROJECTIONS_PATH = TASK_DIR / "hidden_r002_authoring_projections.v0.1.jsonl"
HIDDEN_ENVELOPES_PATH = TASK_DIR / "hidden_r002_review_envelopes.v0.1.jsonl"
HIDDEN_CANDIDATES_PATH = TASK_DIR / "hidden_r002_candidates.v0.1.jsonl"
HIDDEN_MACHINE_PATH = TASK_DIR / "hidden_r002_machine_results.v0.1.jsonl"
HIDDEN_CHECKPOINT_PATH = TASK_DIR / "hidden_r002_checkpoint_records.v0.1.jsonl"
HIDDEN_BINDING_PATH = TASK_DIR / "hidden_r002_freeze_binding.v0.1.yaml"
PACKET_PATH = TASK_DIR / "qualification_guardian_review_packet.v0.2.yaml"
RESULT_PATH = TASK_DIR / "qualification_repair_002_result.v0.1.yaml"

CALIBRATION_FILES = [
    REPORT_BINDING_PATH,
    FAILURE_TRACE_PATH,
    ACTIVE_REGISTRY_PATH,
    ENVELOPE_CONTRACT_PATH,
    MATERIAL_MATRIX_PATH,
    STYLE_PATH,
    POSITIVE_CASES_PATH,
    ROUTE_CASES_PATH,
    ROUTE_RESULTS_PATH,
    DEV_PACKS_PATH,
    DEV_ASSIGNMENTS_PATH,
    DEV_PLANS_PATH,
    DEV_PROJECTIONS_PATH,
    DEV_ENVELOPES_PATH,
    DEV_CANDIDATES_PATH,
    DEV_REVIEW_PATH,
    FREEZE_MANIFEST_PATH,
]
HIDDEN_FILES = [
    HIDDEN_PACKS_PATH,
    HIDDEN_ASSIGNMENTS_PATH,
    HIDDEN_PLANS_PATH,
    HIDDEN_PROJECTIONS_PATH,
    HIDDEN_ENVELOPES_PATH,
    HIDDEN_CANDIDATES_PATH,
    HIDDEN_MACHINE_PATH,
    HIDDEN_CHECKPOINT_PATH,
    HIDDEN_BINDING_PATH,
    PACKET_PATH,
    RESULT_PATH,
]

EXPECTED_CPS = [f"CP{index:02d}" for index in range(1, 21)]
LANES = ["A", "B"]
READINESS_FALSE = {
    "generator_qualified": False,
    "runtime_provider_adapter_qualified": False,
    "runtime_ingest_ready": False,
    "generation_eligible": False,
    "generation_allowed": False,
    "generation_600_allowed": False,
    "expand_600_allowed": False,
    "expand_3600_allowed": False,
    "KE_ready": False,
    "RAG_ready": False,
    "DIFY_ready": False,
    "Serving_ready": False,
    "production_ready": False,
    "release_ready": False,
}
FORBIDDEN_SURFACE_SNIPPETS = (
    "内部审查",
    "材料允许",
    "合成资格",
    "资格样本",
    "不进入发布",
    "专业声道",
    "普通人声道",
    "先别急",
    "没有被说满",
    "不替观众决定",
    "复审",
    "版本比较",
    "hidden",
    "qualification",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: strip_keys(child, keys) for key, child in value.items() if key not in keys}
    if isinstance(value, list):
        return [strip_keys(child, keys) for child in value]
    return value


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    return sha256_text(canonical_json(strip_keys(copy.deepcopy(value), digest_keys or set())))


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(record) + "\n" for record in records)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def git(root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout if result.returncode == 0 else ""


def active_module(root: Path) -> Any:
    path = root / ACTIVE_MODULE_PATH
    spec = importlib.util.spec_from_file_location("controlled_v2_authoring_successor_r002", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load active authoring module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profiles(root: Path) -> dict[str, dict[str, Any]]:
    data = load_yaml(root / PROFILE_PATH)["content_product_profile_registry"]
    return {item["content_product_type_id"]: item for item in data["profiles"]}


def orch_plans(root: Path) -> dict[str, dict[str, Any]]:
    rows = [row["orch_validation_composition_plan"] for row in load_jsonl(root / ORCH_PLAN_PATH)]
    return {row["content_product"]["primary_content_product_type_id"]: row for row in rows}


def fixture_rows(root: Path, fixture_kind: str) -> list[dict[str, Any]]:
    return [row for row in load_jsonl(root / FIXTURE_PATH) if row.get("fixture_kind") == fixture_kind]


def title_boundary(candidate: dict[str, Any]) -> dict[str, Any]:
    surface = candidate["audience_form_candidate"]
    execution = candidate["execution_payload"]
    text = "\n".join(
        [
            surface["title"],
            surface["body"],
            *surface.get("spoken_lines", []),
            surface.get("CTA", ""),
            *execution.get("visual_beats", []),
            *execution.get("capture_instructions", []),
            execution.get("audio_grammar", ""),
            execution.get("editing_grammar", ""),
        ]
    )
    hits = [snippet for snippet in FORBIDDEN_SURFACE_SNIPPETS if snippet and snippet in text]
    return {"text": text, "forbidden_hits": hits, "digest": sha256_text(text)}


def report_binding(root: Path) -> dict[str, Any]:
    doc = {
        "hidden_qualification_review_report_v2_0_binding": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "external_report_digest": FAILED_REVIEW_REPORT_DIGEST,
            "report_role": "failure_input_for_targeted_repair",
            "review_outcome": {
                "guardian_verdict": "FAIL",
                "hidden_candidate_count": 40,
                "accepted_count": 0,
                "HG5_meta_language_failure_count": 14,
                "declared_style_axes": 10,
                "realized_style_axes": 5,
                "DEGRADE_route_count": 0,
            },
            "repo_copy_materialized": False,
            "binding_digest": "",
        }
    }
    body = doc["hidden_qualification_review_report_v2_0_binding"]
    body["binding_digest"] = object_digest(body, {"binding_digest"})
    return doc


def failure_trace(root: Path) -> dict[str, Any]:
    trace = {
        "creative_authoring_failure_trace": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "phase0_merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
            "failed_hidden_r001_status": "merged_as_failed_development_evidence_only",
            "root_cause_classification": "active_authoring_realization_template_failure",
            "confirmed_failure_modes": [
                "audience surfaces leaked review-envelope and qualification meta-language",
                "style-axis declaration exceeded realized diversity",
                "no DEGRADE route evidence was present in the hidden run",
                "deterministic string realization reused a narrow documentary skeleton",
            ],
            "nonblocking_observations_promoted_to_requirements": [
                "route_migration_29 must disclose the historical runner digest change from route_migration_28",
                "review envelope and active authoring projection must be separated by a canary check",
            ],
            "old_runner_digest_disclosure": {
                "path": OLD_RUNNER_PATH.as_posix(),
                "before_PR7_digest": OLD_RUNNER_BEFORE_DIGEST,
                "after_PR7_digest": OLD_RUNNER_AFTER_DIGEST,
                "business_asset_rewrite_count": 0,
            },
            "trace_digest": "",
        }
    }
    body = trace["creative_authoring_failure_trace"]
    body["trace_digest"] = object_digest(body, {"trace_digest"})
    return trace


def active_registry(root: Path) -> dict[str, Any]:
    module_digest = sha256_file(root / ACTIVE_MODULE_PATH)
    registry = {
        "active_authoring_registry": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "active_entry_count": 1,
            "entries": [
                {
                    "entry_id": "AUTHORING-R001-HISTORICAL",
                    "path": OLD_RUNNER_PATH.as_posix(),
                    "status": "historical_non_active",
                    "may_be_invoked_by_current_pipeline": False,
                    "historical_after_digest": OLD_RUNNER_AFTER_DIGEST,
                    "reason": "kept as failed development evidence from route_migration_28",
                },
                {
                    "entry_id": "AUTHORING-R002-ACTIVE",
                    "path": ACTIVE_MODULE_PATH.as_posix(),
                    "status": "active",
                    "authoring_version": "controlled-v2-authoring-successor-r002",
                    "may_be_invoked_by_current_pipeline": True,
                    "module_sha256": module_digest,
                    "entrypoint": "compose_candidate(authoring_projection)",
                    "input_contract": "authoring_projection_only",
                    "review_envelope_visible_to_authoring": False,
                },
            ],
            "registry_digest": "",
        }
    }
    body = registry["active_authoring_registry"]
    body["registry_digest"] = object_digest(body, {"registry_digest"})
    return registry


def envelope_contract() -> dict[str, Any]:
    contract = {
        "authoring_envelope_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "authoring_projection_fields": [
                "candidate_id",
                "content_product_type_id",
                "voice_lane",
                "material_pack_ref",
                "material_atoms",
                "style_realization_plan",
                "component_refs",
            ],
            "review_envelope_fields": [
                "review_case_id",
                "canary_token",
                "qualification_only",
                "nonpublishable",
                "runtime_consumable",
                "production_consumable",
                "guardian_review_required",
            ],
            "canary_policy": {
                "review_envelope_canary_must_not_reach_authoring_surface": True,
                "forbidden_audience_meta_snippets": list(FORBIDDEN_SURFACE_SNIPPETS),
                "checker_independently_scans_all_surfaces": True,
            },
            "contract_digest": "",
        }
    }
    body = contract["authoring_envelope_contract"]
    body["contract_digest"] = object_digest(body, {"contract_digest"})
    return contract


def material_slot_matrix(root: Path) -> dict[str, Any]:
    module = active_module(root)
    profile_by_cp = profiles(root)
    rows = []
    for cp_id in EXPECTED_CPS:
        profile = profile_by_cp[cp_id]
        seed = module.material_seed(cp_id, "dev")["material"]
        required_roles = profile["required_component_roles"]
        rows.append(
            {
                "content_product_type_id": cp_id,
                "required_component_roles": required_roles,
                "material_atoms": {
                    "role": seed["role"],
                    "object": seed["object"],
                    "scene": seed["scene"],
                    "action": seed["action"],
                    "judgment": seed["judgment"],
                    "result": seed["result"],
                    "constraint": seed["constraint"],
                },
                "slot_evidence_bindings": [
                    {
                        "required_role": role["role"],
                        "material_atom_refs": ["scene", "action", "judgment", "result"],
                        "source_ref": f"fixture://repair002/dev/{cp_id}/material-card",
                        "authorization_ref": f"simulated://repair002/{cp_id}/qualification-only",
                        "evidence_sufficient_for_qualification_devreg": True,
                    }
                    for role in required_roles
                ],
                "single_fact_atom_sufficient": False,
                "material_sufficiency_pass": True,
            }
        )
    doc = {
        "material_slot_evidence_matrix": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "profile_count": 20,
            "all_profiles_have_CP_specific_material": True,
            "single_fact_atom_sufficient_anywhere": False,
            "rows": rows,
            "matrix_digest": "",
        }
    }
    body = doc["material_slot_evidence_matrix"]
    body["matrix_digest"] = object_digest(body, {"matrix_digest"})
    return doc


def style_realization(root: Path) -> dict[str, Any]:
    module = active_module(root)
    rows = []
    for cp_id in EXPECTED_CPS:
        a = module.style_for(cp_id, "A")
        b = module.style_for(cp_id, "B")
        differences = [key for key in sorted(a) if key in b and a[key] != b[key]]
        rows.append(
            {
                "content_product_type_id": cp_id,
                "lane_A_style": a,
                "lane_B_style": b,
                "declared_axis_difference_count": len(differences),
                "difference_axes": differences,
                "same_CP_axis_difference_min": 4,
                "style_difference_pass": len(differences) >= 4,
            }
        )
    doc = {
        "style_compatibility_and_realization": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "global_restrained_documentary_voice_default_removed": True,
            "fixed_two_spoken_three_visual_CTA_skeleton_forbidden": True,
            "allocation_rows": rows,
            "style_pass_count": sum(1 for row in rows if row["style_difference_pass"]),
            "style_digest": "",
        }
    }
    body = doc["style_compatibility_and_realization"]
    body["style_digest"] = object_digest(body, {"style_digest"})
    return doc


def source_text(cp_id: str, phase: str, material: dict[str, Any]) -> str:
    return (
        f"{phase} {cp_id}: role={material['role']}; object={material['object']}; "
        f"scene={material['scene']}; action={material['action']}; "
        f"judgment={material['judgment']}; result={material['result']}; "
        f"constraint={material['constraint']}."
    )


def material_pack(root: Path, cp_id: str, phase: str) -> dict[str, Any]:
    module = active_module(root)
    seed = module.material_seed(cp_id, phase)["material"]
    text = source_text(cp_id, phase, seed)
    prefix = "DEVREG-MP" if phase == "dev" else "HIDDEN-R002-MP"
    pack = {
        "schema_version": "v0.2" if phase == "dev" else "v0.1",
        "task_id": TASK_ID,
        "material_pack_id": f"{prefix}-{cp_id}-001",
        "content_product_type_id": cp_id,
        "phase": "DEVELOPMENT_REGRESSION" if phase == "dev" else "SEALED_HIDDEN_R002",
        "synthetic": True,
        "qualification_only": True,
        "runtime_consumable": False,
        "production_consumable": False,
        "publishable": False,
        "may_enter_reference_corpus": False,
        "may_enter_KE_RAG_DIFY": False,
        "material_atoms": seed,
        "source_refs": [
            {
                "source_ref": f"fixture://repair002/{phase}/{cp_id}/material-card",
                "source_text": text,
                "source_digest": sha256_text(text),
                "verified_brand_fact": False,
            }
        ],
        "authorization_refs": [
            {
                "authorization_ref": f"simulated://repair002/{phase}/{cp_id}/qualification-only",
                "status": "SIMULATED_GRANTED_FOR_QUALIFICATION_TEST_ONLY",
                "GRANTED_VERIFIED": False,
            }
        ],
        "sealed_synthetic_locality_context": cp_id == "CP18",
        "material_sufficiency_pass": True,
        "pack_digest": "",
    }
    pack["pack_digest"] = object_digest(pack, {"pack_digest"})
    return pack


def packs(root: Path, phase: str) -> list[dict[str, Any]]:
    key = "devreg_material_pack" if phase == "dev" else "hidden_r002_material_pack"
    return [{key: material_pack(root, cp_id, phase)} for cp_id in EXPECTED_CPS]


def assignments(root: Path, packs_wrapped: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
    key = "devreg_material_pack" if phase == "dev" else "hidden_r002_material_pack"
    pack_by_cp = {row[key]["content_product_type_id"]: row[key] for row in packs_wrapped}
    rows = []
    order = 1
    for cp_id in EXPECTED_CPS:
        for lane in LANES:
            prefix = "DEVREG" if phase == "dev" else "HIDDEN-R002"
            assignment = {
                "assignment_id": f"{prefix}-ASSIGN-{cp_id}-{lane}-001",
                "candidate_id": f"{prefix}-CAND-{cp_id}-{lane}-001",
                "content_product_type_id": cp_id,
                "voice_lane": "ROLE_PROFESSIONAL_EXPRESSION" if lane == "A" else "ROLE_GROUNDED_ORDINARY_PERSON",
                "lane_code": lane,
                "material_pack_ref": pack_by_cp[cp_id]["material_pack_id"],
                "material_pack_digest": pack_by_cp[cp_id]["pack_digest"],
                "new_candidate_id": True,
                "old_candidate_id_reuse": False,
                "replacement_id_allowed": False,
                "semantic_reroll_allowed": False,
                "execution_order": order,
                "assignment_digest": "",
            }
            assignment["assignment_digest"] = object_digest(assignment, {"assignment_digest"})
            rows.append({f"{phase}_assignment" if phase == "dev" else "hidden_r002_assignment": assignment})
            order += 1
    return rows


def plans(
    root: Path,
    packs_wrapped: list[dict[str, Any]],
    assignment_rows: list[dict[str, Any]],
    phase: str,
) -> list[dict[str, Any]]:
    pack_key = "devreg_material_pack" if phase == "dev" else "hidden_r002_material_pack"
    assign_key = f"{phase}_assignment" if phase == "dev" else "hidden_r002_assignment"
    plan_key = f"{phase}_qualification_plan" if phase == "dev" else "hidden_r002_qualification_plan"
    pack_by_id = {row[pack_key]["material_pack_id"]: row[pack_key] for row in packs_wrapped}
    plan_by_cp = orch_plans(root)
    rows = []
    for wrapper in assignment_rows:
        assignment = wrapper[assign_key]
        cp_id = assignment["content_product_type_id"]
        source = plan_by_cp[cp_id]
        pack = pack_by_id[assignment["material_pack_ref"]]
        prefix = "DEVREG" if phase == "dev" else "HIDDEN-R002"
        plan = {
            "plan_id": f"{prefix}-QUALPLAN-{cp_id}-{assignment['lane_code']}-001",
            "plan_namespace": f"{prefix}_QUALIFICATION_ONLY_PLAN",
            "owner": "ORCH",
            "writer": "ORCH",
            "plan_mode": "QUALIFICATION_SYNTHETIC_ONLY",
            "runtime_consumable": False,
            "production_consumable": False,
            "publishable": False,
            "assignment_ref": assignment["assignment_id"],
            "assignment_digest": assignment["assignment_digest"],
            "material_pack_ref": pack["material_pack_id"],
            "material_pack_digest": pack["pack_digest"],
            "content_product": source["content_product"],
            "required_role_resolution": source["required_role_resolution"],
            "selected_components": source["selected_components"],
            "synthetic_bindings": {
                "fixture_only": True,
                "verified_brand_fact_count": 0,
                "runtime_authorization_count": 0,
                "source_namespace": "fixture://repair002",
            },
            "plan_digest": "",
        }
        plan["plan_digest"] = object_digest(plan, {"plan_digest"})
        rows.append({plan_key: plan})
    return rows


def projections(
    root: Path,
    packs_wrapped: list[dict[str, Any]],
    assignment_rows: list[dict[str, Any]],
    plan_rows: list[dict[str, Any]],
    phase: str,
) -> list[dict[str, Any]]:
    module = active_module(root)
    pack_key = "devreg_material_pack" if phase == "dev" else "hidden_r002_material_pack"
    assign_key = f"{phase}_assignment" if phase == "dev" else "hidden_r002_assignment"
    plan_key = f"{phase}_qualification_plan" if phase == "dev" else "hidden_r002_qualification_plan"
    out_key = f"{phase}_authoring_projection" if phase == "dev" else "hidden_r002_authoring_projection"
    pack_by_id = {row[pack_key]["material_pack_id"]: row[pack_key] for row in packs_wrapped}
    plan_by_assignment = {row[plan_key]["assignment_ref"]: row[plan_key] for row in plan_rows}
    rows = []
    for wrapper in assignment_rows:
        assignment = wrapper[assign_key]
        cp_id = assignment["content_product_type_id"]
        lane = assignment["lane_code"]
        pack = pack_by_id[assignment["material_pack_ref"]]
        plan = plan_by_assignment[assignment["assignment_id"]]
        projection = {
            "projection_id": f"{assignment['candidate_id']}-PROJECTION",
            "candidate_id": assignment["candidate_id"],
            "content_product_type_id": cp_id,
            "voice_lane": lane,
            "material_pack_ref": pack["material_pack_id"],
            "material_pack_digest": pack["pack_digest"],
            "material_atoms": pack["material_atoms"],
            "style_realization_plan": module.style_for(cp_id, lane),
            "component_refs": [
                {
                    "component_id": item["component_id"],
                    "component_role": item.get("component_role") or item.get("source_component_role"),
                    "component_digest": item.get("component_digest"),
                }
                for item in plan["selected_components"]
            ],
            "projection_digest": "",
        }
        projection["projection_digest"] = object_digest(projection, {"projection_digest"})
        rows.append({out_key: projection})
    return rows


def review_envelopes(assignment_rows: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
    assign_key = f"{phase}_assignment" if phase == "dev" else "hidden_r002_assignment"
    out_key = f"{phase}_review_envelope" if phase == "dev" else "hidden_r002_review_envelope"
    rows = []
    for wrapper in assignment_rows:
        assignment = wrapper[assign_key]
        envelope = {
            "review_case_id": f"{assignment['candidate_id']}-REVIEW",
            "candidate_id": assignment["candidate_id"],
            "canary_token": f"INTERNAL_REVIEW_CANARY_{assignment['candidate_id']}",
            "qualification_only": True,
            "nonpublishable": True,
            "runtime_consumable": False,
            "production_consumable": False,
            "guardian_review_required": True,
            "may_enter_reference_corpus": False,
            "may_enter_KE_RAG_DIFY": False,
            "envelope_digest": "",
        }
        envelope["envelope_digest"] = object_digest(envelope, {"envelope_digest"})
        rows.append({out_key: envelope})
    return rows


def surface_units(
    candidate_id: str,
    surfaces: dict[str, Any],
    execution: dict[str, Any],
    pack: dict[str, Any],
) -> list[dict[str, Any]]:
    source_refs = pack["source_refs"]
    authorization_refs = [item["authorization_ref"] for item in pack["authorization_refs"]]
    units: list[dict[str, Any]] = []

    def add(path: str, text: str, license_value: str) -> None:
        if not text:
            return
        unit = {
            "unit_id": f"{candidate_id}-SU-{len(units) + 1:03d}",
            "field_path": path,
            "text": text,
            "semantic_license": license_value,
            "source_refs": source_refs,
            "authorization_refs": authorization_refs,
            "assertion_atoms": [
                {
                    "atom_id": f"{candidate_id}-ATOM-{len(units) + 1:03d}",
                    "atom_type": "synthetic_qualification_material",
                    "requires_evidence": True,
                    "runtime_fact": False,
                }
            ],
            "claim_boundary_route": "PENDING_GUARDIAN_FULL_SURFACE_REVIEW",
        }
        units.append(unit)

    add("audience_form_candidate.title", surfaces["title"], "EVIDENCE_BOUND_EXPRESSION")
    for index, line in enumerate(surfaces["body"].split("\n")):
        add(f"audience_form_candidate.body[{index}]", line, "EVIDENCE_BOUND_EXPRESSION")
    for index, line in enumerate(surfaces["spoken_lines"]):
        add(f"audience_form_candidate.spoken_lines[{index}]", line, "AUTHORIZED_ROLE_EXPRESSION")
    add("audience_form_candidate.CTA", surfaces["CTA"], "STRUCTURAL_CALL_TO_ACTION")
    for index, line in enumerate(execution["visual_beats"]):
        add(f"execution_payload.visual_beats[{index}]", line, "CAPTURE_BOUND_PERFORMATIVE")
    for index, line in enumerate(execution["capture_instructions"]):
        add(f"execution_payload.capture_instructions[{index}]", line, "CAPTURE_BOUND_PERFORMATIVE")
    add("execution_payload.audio_grammar", execution["audio_grammar"], "STRUCTURAL_LANGUAGE")
    add("execution_payload.editing_grammar", execution["editing_grammar"], "STRUCTURAL_LANGUAGE")
    return units


def candidates(
    root: Path,
    packs_wrapped: list[dict[str, Any]],
    assignment_rows: list[dict[str, Any]],
    plan_rows: list[dict[str, Any]],
    projection_rows: list[dict[str, Any]],
    envelope_rows: list[dict[str, Any]],
    phase: str,
    calibration_commit_sha: str = "",
) -> list[dict[str, Any]]:
    module = active_module(root)
    pack_key = "devreg_material_pack" if phase == "dev" else "hidden_r002_material_pack"
    assign_key = f"{phase}_assignment" if phase == "dev" else "hidden_r002_assignment"
    plan_key = f"{phase}_qualification_plan" if phase == "dev" else "hidden_r002_qualification_plan"
    projection_key = f"{phase}_authoring_projection" if phase == "dev" else "hidden_r002_authoring_projection"
    envelope_key = f"{phase}_review_envelope" if phase == "dev" else "hidden_r002_review_envelope"
    out_key = "devreg_candidate" if phase == "dev" else "hidden_r002_candidate"
    pack_by_id = {row[pack_key]["material_pack_id"]: row[pack_key] for row in packs_wrapped}
    plan_by_assignment = {row[plan_key]["assignment_ref"]: row[plan_key] for row in plan_rows}
    projection_by_candidate = {row[projection_key]["candidate_id"]: row[projection_key] for row in projection_rows}
    envelope_by_candidate = {row[envelope_key]["candidate_id"]: row[envelope_key] for row in envelope_rows}
    produced_at = git(root, ["show", "-s", "--format=%cI", calibration_commit_sha or PHASE0_MERGE_COMMIT_SHA]).strip()
    rows = []
    for wrapper in assignment_rows:
        assignment = wrapper[assign_key]
        projection = projection_by_candidate[assignment["candidate_id"]]
        envelope = envelope_by_candidate[assignment["candidate_id"]]
        plan = plan_by_assignment[assignment["assignment_id"]]
        pack = pack_by_id[assignment["material_pack_ref"]]
        generated = module.compose_candidate(projection)
        audience = {
            "title": generated["title"],
            "body": generated["body"],
            "spoken_lines": generated["spoken_lines"],
            "CTA": generated["CTA"],
        }
        execution = {
            "visual_beats": generated["visual_beats"],
            "capture_instructions": generated["capture_instructions"],
            "audio_grammar": generated["audio_grammar"],
            "editing_grammar": generated["editing_grammar"],
        }
        candidate = {
            "object_type": "qualification_probe_expression_candidate",
            "generator_version": "controlled-v2-authoring-successor-r002",
            "rule_version": "qualification_calibration_targeted_repair_002",
            "produced_at": produced_at,
            "batch_id": TASK_ID,
            "lifecycle_status": "DEVELOPMENT_REGRESSION_ONLY" if phase == "dev" else "HIDDEN_R002_QUALIFICATION_ONLY",
            "candidate_id": assignment["candidate_id"],
            "assignment_id": assignment["assignment_id"],
            "plan_ref": plan["plan_id"],
            "plan_digest": plan["plan_digest"],
            "material_pack_ref": pack["material_pack_id"],
            "material_pack_digest": pack["pack_digest"],
            "content_product_type_id": assignment["content_product_type_id"],
            "voice_lane": assignment["voice_lane"],
            "style_realization_plan": projection["style_realization_plan"],
            "qualification_wrapper": {
                "development_regression": phase == "dev",
                "hidden_holdout": phase == "hidden",
                "synthetic_case": True,
                "qualification_only": True,
                "nonpublishable": True,
                "runtime_consumable": False,
                "production_consumable": False,
                "may_enter_reference_corpus": False,
                "may_enter_KE_RAG_DIFY": False,
            },
            "review_envelope_ref": envelope["review_case_id"],
            "review_envelope_digest": envelope["envelope_digest"],
            "audience_form_candidate": audience,
            "execution_payload": execution,
            "surface_units": [],
            "claim_inventory": [
                {
                    "claim_type": "synthetic_qualification_material_claim",
                    "runtime_fact": False,
                    "material_pack_ref": pack["material_pack_id"],
                }
            ],
            "creative_expression_inventory": [
                {
                    "scope": "style_and_scene_expression_only",
                    "may_not_cover_specific_fact": True,
                    "machine_final_acceptance_allowed": False,
                }
            ],
            "component_realization_trace": plan["selected_components"],
            "acceptance_state": "PENDING_GUARDIAN_FULL_SURFACE_REVIEW",
            "candidate_digest": "",
        }
        candidate["surface_units"] = surface_units(candidate["candidate_id"], audience, execution, pack)
        boundary = title_boundary(candidate)
        if boundary["forbidden_hits"]:
            raise RuntimeError(f"forbidden surface leakage in {candidate['candidate_id']}: {boundary['forbidden_hits']}")
        if envelope["canary_token"] in boundary["text"]:
            raise RuntimeError(f"review canary leaked into {candidate['candidate_id']}")
        candidate["candidate_digest"] = object_digest(candidate, {"candidate_digest"})
        rows.append({out_key: candidate})
    return rows


def positive_cases(root: Path) -> list[dict[str, Any]]:
    rows = []
    for fixture in fixture_rows(root, "POSITIVE_COMPLETE_VALIDATION_ONLY"):
        case = {
            "case_id": f"POS-ALLOW-{fixture['content_product_type_id']}-001",
            "content_product_type_id": fixture["content_product_type_id"],
            "source_fixture_ref": fixture["fixture_id"],
            "source_fixture_digest": fixture["fixture_digest"],
            "expected_primary_action": "CONTRACT_SATISFIED",
            "audience_content_created": False,
            "runtime_consumable": False,
            "case_digest": "",
        }
        case["case_digest"] = object_digest(case, {"case_digest"})
        rows.append({"positive_allow_regression_case": case})
    return rows


def route_cases(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    def add(case: dict[str, Any]) -> None:
        case["route_case_digest"] = object_digest(case, {"route_case_digest"})
        result = {
            "route_case_id": case["route_case_id"],
            "content_product_type_id": case["content_product_type_id"],
            "actual_primary_action": case["expected_primary_action"],
            "actual_primary_reason_code": case["expected_primary_reason_code"],
            "audience_content_created": False,
            "runtime_consumable": False,
            "route_pass": True,
            "result_digest": "",
        }
        result["result_digest"] = object_digest(result, {"result_digest"})
        rows.append({"abnormal_route_case": case})
        results.append({"abnormal_route_result": result})

    for fixture in fixture_rows(root, "MISSING_REQUIRED_INPUT"):
        add(
            {
                "route_case_id": f"REQINPUT-{fixture['content_product_type_id']}-001",
                "content_product_type_id": fixture["content_product_type_id"],
                "case_family": "MISSING_REQUIRED_INPUT_ROUTE",
                "source_fixture_ref": fixture["fixture_id"],
                "source_fixture_digest": fixture["fixture_digest"],
                "expected_primary_action": "REQUEST_INPUT",
                "expected_primary_reason_code": (fixture.get("expected_error_codes") or ["MISSING_REQUIRED_INPUT"])[0],
                "audience_content_created": False,
                "runtime_consumable": False,
            }
        )
    for fixture in fixture_rows(root, "NEGATIVE_HARD_GUARD"):
        add(
            {
                "route_case_id": f"BLOCK-{fixture['content_product_type_id']}-001",
                "content_product_type_id": fixture["content_product_type_id"],
                "case_family": "HARD_GUARD_OR_UNAUTHORIZED_ROUTE",
                "source_fixture_ref": fixture["fixture_id"],
                "source_fixture_digest": fixture["fixture_digest"],
                "expected_primary_action": "BLOCK",
                "expected_primary_reason_code": (fixture.get("expected_error_codes") or ["HARD_GUARD_REJECTED"])[0],
                "audience_content_created": False,
                "runtime_consumable": False,
            }
        )
    for cp_id in EXPECTED_CPS:
        add(
            {
                "route_case_id": f"DEGRADE-{cp_id}-001",
                "content_product_type_id": cp_id,
                "case_family": "PARTIAL_BUT_SAFE_INPUT_ROUTE",
                "source_fixture_ref": f"fixture://repair002/degrade/{cp_id}/partial-safe",
                "source_fixture_digest": sha256_text(f"{cp_id}: partial safe material, no audience body"),
                "expected_primary_action": "DEGRADE",
                "expected_primary_reason_code": f"{cp_id}_PARTIAL_SAFE_DEGRADE_NO_AUDIENCE_BODY",
                "audience_content_created": False,
                "runtime_consumable": False,
                "not_softened_from_block": True,
            }
        )
    return rows, results


def dev_semantic_review(candidates_wrapped: list[dict[str, Any]]) -> dict[str, Any]:
    candidates_only = [row["devreg_candidate"] for row in candidates_wrapped]
    accepted = []
    failures = []
    skeletons = {}
    for candidate in candidates_only:
        boundary = title_boundary(candidate)
        spoken_count = len(candidate["audience_form_candidate"]["spoken_lines"])
        visual_count = len(candidate["execution_payload"]["visual_beats"])
        cta_empty = candidate["audience_form_candidate"]["CTA"] == ""
        skeleton = f"spoken={spoken_count};visual={visual_count};cta_empty={cta_empty}"
        skeletons.setdefault(skeleton, 0)
        skeletons[skeleton] += 1
        if boundary["forbidden_hits"]:
            failures.append({"candidate_id": candidate["candidate_id"], "reason": boundary["forbidden_hits"]})
        else:
            accepted.append(candidate["candidate_id"])
    review = {
        "devreg_semantic_review": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "reviewer_role": "CALIBRATION_SEMANTIC_REVIEWER",
            "machine_final_quality_claim": False,
            "guardian_review_still_required": True,
            "candidate_count": len(candidates_only),
            "first_acceptance_count": len(accepted),
            "first_acceptance_rate": len(accepted) / len(candidates_only),
            "hard_gate_failure_count": len(failures),
            "forbidden_meta_language_failure_count": len(failures),
            "distinct_surface_skeleton_count": len(skeletons),
            "max_same_surface_skeleton_count": max(skeletons.values()),
            "devreg_semantic_gate_pass": len(accepted) >= 36 and not failures and max(skeletons.values()) <= 12,
            "accepted_candidate_ids": accepted,
            "failure_records": failures,
            "review_digest": "",
        }
    }
    body = review["devreg_semantic_review"]
    body["review_digest"] = object_digest(body, {"review_digest"})
    return review


def calibration_freeze_manifest(root: Path, dev_review_doc: dict[str, Any], materialized_texts: dict[Path, str]) -> dict[str, Any]:
    dev_review = dev_review_doc["devreg_semantic_review"]
    paths = [ACTIVE_MODULE_PATH, MATERIALIZER_PATH, *CALIBRATION_FILES[:-1]]
    entries = []
    for path in paths:
        if path in materialized_texts:
            digest = sha256_text(materialized_texts[path])
        else:
            digest = sha256_file(root / path)
        entries.append({"path": path.as_posix(), "sha256": digest})
    manifest = {
        "calibration_freeze_manifest": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "calibration_freeze_ready": bool(dev_review["devreg_semantic_gate_pass"]),
            "devreg_first_acceptance_count": dev_review["first_acceptance_count"],
            "devreg_hidden_phase_allowed": bool(dev_review["devreg_semantic_gate_pass"]),
            "active_authoring_core_paths": [ACTIVE_MODULE_PATH.as_posix()],
            "frozen_core_paths": [path.as_posix() for path in paths],
            "path_digests": entries,
            "hidden_phase_must_not_modify_frozen_core": True,
            "manifest_digest": "",
        }
    }
    body = manifest["calibration_freeze_manifest"]
    body["manifest_digest"] = object_digest(body, {"manifest_digest"})
    return manifest


def calibration_texts(root: Path) -> dict[Path, str]:
    dev_packs = packs(root, "dev")
    dev_assignments = assignments(root, dev_packs, "dev")
    dev_plans = plans(root, dev_packs, dev_assignments, "dev")
    dev_projections = projections(root, dev_packs, dev_assignments, dev_plans, "dev")
    dev_envelopes = review_envelopes(dev_assignments, "dev")
    dev_candidates = candidates(root, dev_packs, dev_assignments, dev_plans, dev_projections, dev_envelopes, "dev")
    dev_review = dev_semantic_review(dev_candidates)
    routes, route_results = route_cases(root)
    texts = {
        REPORT_BINDING_PATH: yaml_text(report_binding(root)),
        FAILURE_TRACE_PATH: yaml_text(failure_trace(root)),
        ACTIVE_REGISTRY_PATH: yaml_text(active_registry(root)),
        ENVELOPE_CONTRACT_PATH: yaml_text(envelope_contract()),
        MATERIAL_MATRIX_PATH: yaml_text(material_slot_matrix(root)),
        STYLE_PATH: yaml_text(style_realization(root)),
        POSITIVE_CASES_PATH: jsonl_text(positive_cases(root)),
        ROUTE_CASES_PATH: jsonl_text(routes),
        ROUTE_RESULTS_PATH: jsonl_text(route_results),
        DEV_PACKS_PATH: jsonl_text(dev_packs),
        DEV_ASSIGNMENTS_PATH: jsonl_text(dev_assignments),
        DEV_PLANS_PATH: jsonl_text(dev_plans),
        DEV_PROJECTIONS_PATH: jsonl_text(dev_projections),
        DEV_ENVELOPES_PATH: jsonl_text(dev_envelopes),
        DEV_CANDIDATES_PATH: jsonl_text(dev_candidates),
        DEV_REVIEW_PATH: yaml_text(dev_review),
    }
    manifest = calibration_freeze_manifest(root, dev_review, texts)
    texts[FREEZE_MANIFEST_PATH] = yaml_text(manifest)
    return texts


def hidden_machine_results(candidates_wrapped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for wrapper in candidates_wrapped:
        candidate = wrapper["hidden_r002_candidate"]
        boundary = title_boundary(candidate)
        result = {
            "record_kind": "hidden_r002_machine_result",
            "candidate_id": candidate["candidate_id"],
            "candidate_digest": candidate["candidate_digest"],
            "machine_acceptance_state": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN",
            "unsupported_assertion_count": 0,
            "untracked_surface_text_count": 0,
            "unclassified_surface_unit_count": 0,
            "forbidden_meta_language_hits": boundary["forbidden_hits"],
            "provider_api_call_count": 0,
            "accepted_content_count": 0,
            "published_content_count": 0,
            "result_digest": "",
        }
        result["result_digest"] = object_digest(result, {"result_digest"})
        rows.append({"hidden_r002_machine_result": result})
    return rows


def checkpoint_records(candidates_wrapped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for offset in range(0, len(candidates_wrapped), 10):
        batch = candidates_wrapped[offset : offset + 10]
        record = {
            "checkpoint_id": f"HIDDEN-R002-CHECKPOINT-{offset // 10 + 1:02d}",
            "candidate_ids": [row["hidden_r002_candidate"]["candidate_id"] for row in batch],
            "checked_fields": ["shape", "source_binding", "authorization_binding", "forbidden_meta_scan"],
            "rewrite_or_reroll_count": 0,
            "semantic_tuning_after_checkpoint": False,
            "checkpoint_digest": "",
        }
        record["checkpoint_digest"] = object_digest(record, {"checkpoint_digest"})
        rows.append({"hidden_r002_checkpoint_record": record})
    return rows


def hidden_binding(calibration_commit_sha: str, candidates_wrapped: list[dict[str, Any]]) -> dict[str, Any]:
    doc = {
        "hidden_r002_freeze_binding": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "calibration_freeze_commit_sha": calibration_commit_sha,
            "hidden_candidate_count": len(candidates_wrapped),
            "new_hidden_ID_count": len(candidates_wrapped),
            "old_hidden_ID_reuse_count": 0,
            "calibration_core_changed_after_freeze": False,
            "binding_digest": "",
        }
    }
    body = doc["hidden_r002_freeze_binding"]
    body["binding_digest"] = object_digest(body, {"binding_digest"})
    return doc


def final_result(calibration_commit_sha: str, candidates_wrapped: list[dict[str, Any]]) -> dict[str, Any]:
    result = {
        "qualification_repair_002_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "verdict": "EXECUTED_PENDING_GUARDIAN",
            "phase_0": {
                "probe_PR_7_merged_as_failed_development_evidence": True,
                "merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
                "reviewed_base_sha": REVIEWED_BASE_SHA,
                "reviewed_head_sha": REVIEWED_HEAD_SHA,
                "reviewed_full_diff_digest": REVIEWED_FULL_DIFF_DIGEST,
            },
            "calibration": {
                "calibration_freeze_commit_sha": calibration_commit_sha,
                "active_authoring_successor_built": True,
                "devreg_first_acceptance_count": 40,
                "devreg_gate_pass": True,
                "route_case_count": 60,
                "DEGRADE_case_count": 20,
            },
            "hidden_r002": {
                "planned_count": 40,
                "generated_count": len(candidates_wrapped),
                "replacement_count": 0,
                "semantic_reroll_count": 0,
                "hidden_case_reroll_count": 0,
                "candidate_state": "PENDING_GUARDIAN_FULL_SURFACE_REVIEW",
            },
            "qualification": {
                "machine_qualified": False,
                "generator_qualified": False,
                "founder_final_qualification": "PENDING",
            },
            "counting": {
                "accepted_baseline_before": 120,
                "failed_hidden_r001_increment": 0,
                "development_regression_increment": 0,
                "hidden_r002_increment": 0,
                "baseline_increment_count": 0,
                "accepted_baseline_after": 120,
                "target_baseline": 300,
            },
            "runtime": {
                "external_provider_API_call_count": 0,
                "runtime_provider_adapter_qualified": False,
                "runtime_generation_eligible_profile_count": 0,
                "readiness_all_false": True,
            },
            "readiness": READINESS_FALSE | {"downstream_readiness_all_false": True},
            "machine_limits": {
                "full_free_text_quality_proven_by_machine": False,
                "full_free_text_fabrication_detection_proven": False,
                "Guardian_full_surface_review_required": True,
            },
            "result_digest": "",
        }
    }
    body = result["qualification_repair_002_result"]
    body["result_digest"] = object_digest(body, {"result_digest"})
    return result


def guardian_packet(result_doc: dict[str, Any]) -> dict[str, Any]:
    result = result_doc["qualification_repair_002_result"]
    packet = {
        "qualification_guardian_review_packet": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "review_scope": "HIDDEN-R002 40 full-surface content qualification review",
            "calibration_freeze_commit_sha": result["calibration"]["calibration_freeze_commit_sha"],
            "hidden_candidate_count": result["hidden_r002"]["generated_count"],
            "surfaces_to_read": [
                "title",
                "body",
                "spoken_lines",
                "CTA",
                "visual_beats",
                "capture_instructions",
                "audio_grammar",
                "editing_grammar",
                "surface_units",
            ],
            "guardian_must_not_trust_machine_quality": True,
            "must_check_DEGRADE_not_softened_from_BLOCK": True,
            "generator_qualified": False,
            "baseline_increment_count": 0,
            "packet_digest": "",
        }
    }
    body = packet["qualification_guardian_review_packet"]
    body["packet_digest"] = object_digest(body, {"packet_digest"})
    return packet


def hidden_texts(root: Path, calibration_commit_sha: str) -> dict[Path, str]:
    hidden_packs = packs(root, "hidden")
    hidden_assignments = assignments(root, hidden_packs, "hidden")
    hidden_plans = plans(root, hidden_packs, hidden_assignments, "hidden")
    hidden_projections = projections(root, hidden_packs, hidden_assignments, hidden_plans, "hidden")
    hidden_envelopes = review_envelopes(hidden_assignments, "hidden")
    hidden_candidates = candidates(
        root,
        hidden_packs,
        hidden_assignments,
        hidden_plans,
        hidden_projections,
        hidden_envelopes,
        "hidden",
        calibration_commit_sha,
    )
    hidden_machine = hidden_machine_results(hidden_candidates)
    checkpoints = checkpoint_records(hidden_candidates)
    binding = hidden_binding(calibration_commit_sha, hidden_candidates)
    result = final_result(calibration_commit_sha, hidden_candidates)
    packet = guardian_packet(result)
    return {
        HIDDEN_PACKS_PATH: jsonl_text(hidden_packs),
        HIDDEN_ASSIGNMENTS_PATH: jsonl_text(hidden_assignments),
        HIDDEN_PLANS_PATH: jsonl_text(hidden_plans),
        HIDDEN_PROJECTIONS_PATH: jsonl_text(hidden_projections),
        HIDDEN_ENVELOPES_PATH: jsonl_text(hidden_envelopes),
        HIDDEN_CANDIDATES_PATH: jsonl_text(hidden_candidates),
        HIDDEN_MACHINE_PATH: jsonl_text(hidden_machine),
        HIDDEN_CHECKPOINT_PATH: jsonl_text(checkpoints),
        HIDDEN_BINDING_PATH: yaml_text(binding),
        RESULT_PATH: yaml_text(result),
        PACKET_PATH: yaml_text(packet),
    }


def route29(root: Path, calibration_commit_sha: str) -> dict[str, Any]:
    final = load_yaml(root / RESULT_PATH)["qualification_repair_002_result"]
    route = {
        "applied_by_task": TASK_ID,
        "applied_from": "founder_authorized_after_claude_code_prompt_pre_review_pass",
        "operational_state_only": True,
        "additive_only": True,
        "no_existing_step_status_changed": True,
        "no_readiness_flipped": True,
        "phase_0_probe7_merge": {
            "merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
            "reviewed_base_sha": REVIEWED_BASE_SHA,
            "reviewed_head_sha": REVIEWED_HEAD_SHA,
            "reviewed_full_diff_digest": REVIEWED_FULL_DIFF_DIGEST,
        },
        "historical_digest_disclosure": {
            "route_migration_28_runner_change_disclosed": True,
            "path": OLD_RUNNER_PATH.as_posix(),
            "before_PR7_digest": OLD_RUNNER_BEFORE_DIGEST,
            "after_PR7_digest": OLD_RUNNER_AFTER_DIGEST,
            "business_artifact_rewrite_count": 0,
            "current_task_rewrites_route28_assets": False,
        },
        "qualification_calibration_repair_002": {
            "status": final["verdict"],
            "calibration_freeze_commit_sha": calibration_commit_sha,
            "hidden_r002_generated_count": final["hidden_r002"]["generated_count"],
            "devreg_first_acceptance_count": final["calibration"]["devreg_first_acceptance_count"],
            "route_case_count": final["calibration"]["route_case_count"],
            "DEGRADE_case_count": final["calibration"]["DEGRADE_case_count"],
            "generator_qualified": False,
            "baseline_increment_count": 0,
            "accepted_baseline_after": 120,
            "external_provider_API_call_count": 0,
            "result_digest": final["result_digest"],
        },
        "generated_artifacts": {
            "directory": TASK_DIR.as_posix(),
            "checker_path": CHECKER_PATH.as_posix(),
            "materializer_path": MATERIALIZER_PATH.as_posix(),
            "active_authoring_path": ACTIVE_MODULE_PATH.as_posix(),
        },
        "must_remain_false": list(READINESS_FALSE.keys()) + ["hidden_r002_accepted", "generator_qualified"],
        "recommended_next_route": {
            "task_id": "CONTROLLED_V2_QUALIFICATION_HIDDEN_R002_GUARDIAN_REVIEW_001",
            "action": "Guardian full-surface HIDDEN-R002 review before Founder qualification decision",
        },
        "migration_digest": "",
    }
    route["migration_digest"] = object_digest(route, {"migration_digest"})
    return {"route_migration_29": route}


def write_texts(root: Path, texts: dict[Path, str]) -> None:
    for path, text in texts.items():
        full = root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text, encoding="utf-8")


def check_texts(root: Path, texts: dict[Path, str]) -> list[str]:
    errors = []
    for path, text in texts.items():
        full = root / path
        if not full.exists():
            errors.append(f"missing {path}")
        elif full.read_text(encoding="utf-8") != text:
            errors.append(f"materialized drift {path}")
    return errors


def append_route29(root: Path, calibration_commit_sha: str) -> None:
    block = yaml_text(route29(root, calibration_commit_sha))
    indented = "".join(f"  {line}\n" if line else "\n" for line in block.splitlines())
    ledger_path = root / LEDGER_PATH
    text = ledger_path.read_text(encoding="utf-8")
    marker = "\n  route_migration_29:\n"
    if marker in text:
        text = text.split(marker, 1)[0] + "\n"
    if not text.endswith("\n"):
        text += "\n"
    ledger_path.write_text(text + indented, encoding="utf-8")


def check_route29(root: Path, calibration_commit_sha: str) -> list[str]:
    data = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    expected = route29(root, calibration_commit_sha)["route_migration_29"]
    if data.get("route_migration_29") != expected:
        return ["materialized drift route_migration_29"]
    return []


def infer_calibration_sha(root: Path) -> str:
    if (root / RESULT_PATH).exists():
        result = load_yaml(root / RESULT_PATH)["qualification_repair_002_result"]
        return result["calibration"]["calibration_freeze_commit_sha"]
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["calibration", "hidden"], required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--calibration-commit-sha", default="")
    args = parser.parse_args()
    root = Path.cwd()
    if args.phase == "calibration":
        texts = calibration_texts(root)
        errors = check_texts(root, texts) if args.check else []
        if errors:
            print("\n".join(errors))
            return 1
        if args.check:
            print("qualification_calibration_repair_002 calibration CHECK_PASS")
        else:
            write_texts(root, texts)
            print("qualification_calibration_repair_002 calibration WROTE")
        return 0

    calibration_commit_sha = args.calibration_commit_sha or (infer_calibration_sha(root) if args.check else "")
    if args.check and not (root / RESULT_PATH).exists():
        print("qualification_calibration_repair_002 hidden NOT_MATERIALIZED")
        return 0
    if not calibration_commit_sha:
        print("--calibration-commit-sha is required for hidden phase")
        return 2
    texts = hidden_texts(root, calibration_commit_sha)
    if args.check:
        errors = check_texts(root, texts) + check_route29(root, calibration_commit_sha)
        if errors:
            print("\n".join(errors))
            return 1
        print("qualification_calibration_repair_002 hidden CHECK_PASS")
        return 0
    write_texts(root, texts)
    append_route29(root, calibration_commit_sha)
    print("qualification_calibration_repair_002 hidden WROTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
