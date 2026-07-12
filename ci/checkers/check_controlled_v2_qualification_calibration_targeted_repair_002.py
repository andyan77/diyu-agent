#!/usr/bin/env python3
"""Fail-closed checker for qualification calibration targeted repair 002."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    print("check_controlled_v2_qualification_calibration_targeted_repair_002 refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "CONTROLLED_V2_QUALIFICATION_CALIBRATION_TARGETED_REPAIR_002"
PHASE0_MERGE_COMMIT_SHA = "829ab218bd371b4e8cd4197fbc4c6ce295771f40"
PHASE0_MERGE_TREE_SHA = "84deb62b22eb2b4571c145dbf5ef71cfafa6196f"
REVIEWED_BASE_SHA = "531fe864b0b338a8708449ae29e739e2dce8e119"
REVIEWED_HEAD_SHA = "89db1d72b5db3372f280e2d851ddfaf20635bde6"
REVIEWED_HEAD_TREE_SHA = "84deb62b22eb2b4571c145dbf5ef71cfafa6196f"
REVIEWED_FULL_DIFF_DIGEST = "6dd7d686083d8c2dda2cde871d05c6e5278c439359170ad3b9b9892520375223"
FAILED_REVIEW_REPORT_DIGEST = "5ba33d30c6424bdaa8d1af8b6592adc04ebeda6d42109f7701dfee90d4356702"

TASK_DIR = Path("controlled_content_generator_v2_001/qualification_calibration_targeted_repair_002")
ACTIVE_MODULE_PATH = TASK_DIR / "active_authoring/controlled_v2_authoring_successor.py"
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CI_PATH = Path(".github/workflows/ci.yml")
CHECKER_PATH = Path("ci/checkers/check_controlled_v2_qualification_calibration_targeted_repair_002.py")
MATERIALIZER_PATH = TASK_DIR / "run_qualification_calibration_repair_002_materializer.py"
OLD_TASK_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_targeted_repair_001")

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

CALIBRATION_PATHS = {
    ACTIVE_MODULE_PATH,
    MATERIALIZER_PATH,
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
}
HIDDEN_PATHS = {
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
    LEDGER_PATH,
}
EXPECTED_CPS = [f"CP{index:02d}" for index in range(1, 21)]
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
READINESS_KEYS = {
    "generator_qualified",
    "runtime_provider_adapter_qualified",
    "runtime_ingest_ready",
    "generation_eligible",
    "generation_allowed",
    "generation_600_allowed",
    "expand_600_allowed",
    "expand_3600_allowed",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "Serving_ready",
    "production_ready",
    "release_ready",
}


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


def add_error(errors: list[dict[str, str]], code: str, section: str, detail: str) -> None:
    errors.append({"code": code, "section": section, "detail": detail})


def changed_paths(root: Path) -> set[Path]:
    names = git(root, ["diff", "--name-only", f"{PHASE0_MERGE_COMMIT_SHA}..HEAD"])
    names += git(root, ["diff", "--name-only", "HEAD"])
    names += git(root, ["ls-files", "--others", "--exclude-standard"])
    return {Path(line) for line in names.splitlines() if line}


def validate_phase0(root: Path, errors: list[dict[str, str]]) -> None:
    parents = git(root, ["show", "-s", "--format=%P", PHASE0_MERGE_COMMIT_SHA]).split()
    tree = git(root, ["show", "-s", "--format=%T", PHASE0_MERGE_COMMIT_SHA]).strip()
    if REVIEWED_BASE_SHA not in parents or REVIEWED_HEAD_SHA not in parents:
        add_error(errors, "E_PHASE0_PARENTS", "phase0", str(parents))
    if tree != PHASE0_MERGE_TREE_SHA or tree != REVIEWED_HEAD_TREE_SHA:
        add_error(errors, "E_PHASE0_TREE", "phase0", tree)
    diff = git(root, ["diff", f"{REVIEWED_BASE_SHA}..{REVIEWED_HEAD_SHA}"])
    if sha256_text(diff) != REVIEWED_FULL_DIFF_DIGEST:
        add_error(errors, "E_PHASE0_DIFF_DIGEST", "phase0", sha256_text(diff))


def validate_write_surface(root: Path, errors: list[dict[str, str]]) -> None:
    allowed = set(CALIBRATION_PATHS | HIDDEN_PATHS | {CHECKER_PATH, CI_PATH})
    allowed.update(
        {
            Path("ci/checkers/check_controlled_v2_qualification_probe_40_targeted_repair.py"),
            Path("ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py"),
            Path("ci/checkers/check_controlled_content_generator_v2_build.py"),
            Path("ci/checkers/check_orch_v2_20cp_validation_dryrun.py"),
            Path("ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py"),
            Path("ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py"),
            Path("controlled_content_generator_v2_001/qualification_probe_40_targeted_repair_001/run_targeted_repair_materializer.py"),
            Path("controlled_content_generator_v2_001/qualification_probe_40_001/run_qualification_probe_40_generator_acceptance.py"),
            Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001/run_generator_v2_acceptance_harness.py"),
            Path(
                "08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001/"
                "run_orch_20cp_validation_dryrun_freezer.py"
            ),
            Path(
                "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
                "controlled_composition_v2_001/fact_authorization_fixture_closeout_001/"
                "run_fact_authorization_fixture_freezer.py"
            ),
            Path(
                "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
                "controlled_composition_v2_001/component_supply_closeout_20cp_001/"
                "run_component_supply_closeout_freezer.py"
            ),
        }
    )
    unexpected = sorted(path.as_posix() for path in changed_paths(root) if not path.is_relative_to(TASK_DIR) and path not in allowed)
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", "git", str(unexpected))


def validate_old_task_unchanged(root: Path, errors: list[dict[str, str]]) -> None:
    diff = git(root, ["diff", "--name-only", f"{PHASE0_MERGE_COMMIT_SHA}..HEAD", "--", OLD_TASK_DIR.as_posix()])
    allowed_tool_compat = {OLD_TASK_DIR / "run_targeted_repair_materializer.py"}
    changed = {Path(line) for line in diff.splitlines() if line.strip()}
    unexpected = sorted(path.as_posix() for path in changed - allowed_tool_compat)
    if unexpected:
        add_error(errors, "E_OLD_PROBE_REWRITTEN", OLD_TASK_DIR.as_posix(), str(unexpected))


def assert_digest(errors: list[dict[str, str]], section: str, value: dict[str, Any], field: str) -> None:
    if value.get(field) != object_digest(value, {field}):
        add_error(errors, "E_DIGEST", section, field)


def surface_text(candidate: dict[str, Any]) -> str:
    audience = candidate["audience_form_candidate"]
    execution = candidate["execution_payload"]
    return "\n".join(
        [
            audience["title"],
            audience["body"],
            *audience.get("spoken_lines", []),
            audience.get("CTA", ""),
            *execution.get("visual_beats", []),
            *execution.get("capture_instructions", []),
            execution.get("audio_grammar", ""),
            execution.get("editing_grammar", ""),
        ]
    )


def expected_surface_paths(candidate: dict[str, Any]) -> set[str]:
    audience = candidate["audience_form_candidate"]
    execution = candidate["execution_payload"]
    paths = {"audience_form_candidate.title"}
    paths.update(f"audience_form_candidate.body[{index}]" for index, _ in enumerate(audience["body"].split("\n")))
    paths.update(f"audience_form_candidate.spoken_lines[{index}]" for index, _ in enumerate(audience["spoken_lines"]))
    if audience.get("CTA"):
        paths.add("audience_form_candidate.CTA")
    paths.update(f"execution_payload.visual_beats[{index}]" for index, _ in enumerate(execution["visual_beats"]))
    paths.update(f"execution_payload.capture_instructions[{index}]" for index, _ in enumerate(execution["capture_instructions"]))
    paths.update({"execution_payload.audio_grammar", "execution_payload.editing_grammar"})
    return paths


def validate_candidate(candidate: dict[str, Any], errors: list[dict[str, str]], section: str) -> None:
    text = surface_text(candidate)
    hits = [snippet for snippet in FORBIDDEN_SURFACE_SNIPPETS if snippet in text]
    if hits:
        add_error(errors, "E_FORBIDDEN_SURFACE_SNIPPET", candidate["candidate_id"], str(hits))
    if "INTERNAL_REVIEW_CANARY_" in text:
        add_error(errors, "E_REVIEW_CANARY_LEAK", candidate["candidate_id"], "canary reached surface")
    actual_paths = {unit["field_path"] for unit in candidate["surface_units"]}
    expected_paths = expected_surface_paths(candidate)
    if actual_paths != expected_paths:
        add_error(errors, "E_EXACT_JOIN", candidate["candidate_id"], str(sorted(actual_paths ^ expected_paths)))
    if any(not unit.get("source_refs") or not unit.get("authorization_refs") for unit in candidate["surface_units"]):
        add_error(errors, "E_SURFACE_SOURCE_AUTH", candidate["candidate_id"], "missing source/auth")
    wrapper = candidate.get("qualification_wrapper", {})
    if wrapper.get("qualification_only") is not True or wrapper.get("runtime_consumable") is not False:
        add_error(errors, "E_CANDIDATE_WRAPPER", candidate["candidate_id"], str(wrapper))
    if candidate.get("acceptance_state") != "PENDING_GUARDIAN_FULL_SURFACE_REVIEW":
        add_error(errors, "E_CANDIDATE_STATE", candidate["candidate_id"], str(candidate.get("acceptance_state")))
    assert_digest(errors, section, candidate, "candidate_digest")


def validate_calibration(root: Path, errors: list[dict[str, str]]) -> None:
    for path in CALIBRATION_PATHS:
        if not (root / path).exists():
            add_error(errors, "E_CALIBRATION_FILE_MISSING", path.as_posix(), "missing")
    if errors:
        return
    binding = load_yaml(root / REPORT_BINDING_PATH)["hidden_qualification_review_report_v2_0_binding"]
    if binding.get("external_report_digest") != FAILED_REVIEW_REPORT_DIGEST:
        add_error(errors, "E_REPORT_BINDING", "report", str(binding))
    assert_digest(errors, "report_binding", binding, "binding_digest")
    trace = load_yaml(root / FAILURE_TRACE_PATH)["creative_authoring_failure_trace"]
    if trace.get("root_cause_classification") != "active_authoring_realization_template_failure":
        add_error(errors, "E_FAILURE_TRACE", "failure_trace", str(trace))
    assert_digest(errors, "failure_trace", trace, "trace_digest")
    registry = load_yaml(root / ACTIVE_REGISTRY_PATH)["active_authoring_registry"]
    active_entries = [entry for entry in registry["entries"] if entry.get("status") == "active"]
    if registry.get("active_entry_count") != 1 or len(active_entries) != 1:
        add_error(errors, "E_ACTIVE_ENTRY_COUNT", "active_registry", str(registry))
    if active_entries and active_entries[0].get("path") != ACTIVE_MODULE_PATH.as_posix():
        add_error(errors, "E_ACTIVE_ENTRY_PATH", "active_registry", str(active_entries[0]))
    assert_digest(errors, "active_registry", registry, "registry_digest")
    contract = load_yaml(root / ENVELOPE_CONTRACT_PATH)["authoring_envelope_contract"]
    if contract.get("canary_policy", {}).get("review_envelope_canary_must_not_reach_authoring_surface") is not True:
        add_error(errors, "E_CANARY_POLICY", "envelope_contract", str(contract))
    assert_digest(errors, "envelope_contract", contract, "contract_digest")
    matrix = load_yaml(root / MATERIAL_MATRIX_PATH)["material_slot_evidence_matrix"]
    if matrix.get("profile_count") != 20 or len(matrix.get("rows", [])) != 20:
        add_error(errors, "E_MATERIAL_MATRIX_COUNT", "material_matrix", str(matrix.get("profile_count")))
    if any(row.get("single_fact_atom_sufficient") is not False or row.get("material_sufficiency_pass") is not True for row in matrix["rows"]):
        add_error(errors, "E_MATERIAL_MATRIX", "material_matrix", "bad row")
    assert_digest(errors, "material_matrix", matrix, "matrix_digest")
    style = load_yaml(root / STYLE_PATH)["style_compatibility_and_realization"]
    rows = style.get("allocation_rows", [])
    if len(rows) != 20 or any(row.get("declared_axis_difference_count", 0) < 4 for row in rows):
        add_error(errors, "E_STYLE_AXIS", "style", str(rows[:2]))
    if any(row.get("style_difference_pass") is not True for row in rows):
        add_error(errors, "E_STYLE_PASS", "style", "style pass false")
    assert_digest(errors, "style", style, "style_digest")
    positives = [row["positive_allow_regression_case"] for row in load_jsonl(root / POSITIVE_CASES_PATH)]
    routes = [row["abnormal_route_case"] for row in load_jsonl(root / ROUTE_CASES_PATH)]
    route_results = [row["abnormal_route_result"] for row in load_jsonl(root / ROUTE_RESULTS_PATH)]
    if len(positives) != 20 or len(routes) != 60 or len(route_results) != 60:
        add_error(errors, "E_ROUTE_COUNTS", "routes", f"{len(positives)}/{len(routes)}/{len(route_results)}")
    route_counter = Counter(route["expected_primary_action"] for route in routes)
    if route_counter != {"REQUEST_INPUT": 20, "BLOCK": 20, "DEGRADE": 20}:
        add_error(errors, "E_ROUTE_DISTRIBUTION", "routes", str(route_counter))
    if any(route.get("audience_content_created") is not False or route.get("runtime_consumable") is not False for route in routes):
        add_error(errors, "E_ROUTE_BOUNDARY", "routes", "route created content/runtime")
    if any(result.get("actual_primary_action") != next(route["expected_primary_action"] for route in routes if route["route_case_id"] == result["route_case_id"]) for result in route_results):
        add_error(errors, "E_ROUTE_RESULT_MISMATCH", "routes", "actual != expected")
    dev_packs = [row["devreg_material_pack"] for row in load_jsonl(root / DEV_PACKS_PATH)]
    dev_assignments = [row["dev_assignment"] for row in load_jsonl(root / DEV_ASSIGNMENTS_PATH)]
    dev_plans = [row["dev_qualification_plan"] for row in load_jsonl(root / DEV_PLANS_PATH)]
    dev_projections = [row["dev_authoring_projection"] for row in load_jsonl(root / DEV_PROJECTIONS_PATH)]
    dev_envelopes = [row["dev_review_envelope"] for row in load_jsonl(root / DEV_ENVELOPES_PATH)]
    dev_candidates = [row["devreg_candidate"] for row in load_jsonl(root / DEV_CANDIDATES_PATH)]
    if [len(dev_packs), len(dev_assignments), len(dev_plans), len(dev_projections), len(dev_envelopes), len(dev_candidates)] != [20, 40, 40, 40, 40, 40]:
        add_error(errors, "E_DEV_COUNTS", "dev", str([len(dev_packs), len(dev_assignments), len(dev_plans), len(dev_projections), len(dev_envelopes), len(dev_candidates)]))
    if Counter(pack["content_product_type_id"] for pack in dev_packs) != {cp: 1 for cp in EXPECTED_CPS}:
        add_error(errors, "E_DEV_PACK_CP", "dev_packs", "bad CP distribution")
    if any(pack.get("runtime_consumable") is not False or pack.get("publishable") is not False for pack in dev_packs):
        add_error(errors, "E_DEV_PACK_BOUNDARY", "dev_packs", "bad boundary")
    if any(plan.get("owner") != "ORCH" or plan.get("writer") != "ORCH" for plan in dev_plans):
        add_error(errors, "E_DEV_PLAN_OWNER", "dev_plans", "non ORCH")
    for candidate in dev_candidates:
        validate_candidate(candidate, errors, "dev_candidate")
    review = load_yaml(root / DEV_REVIEW_PATH)["devreg_semantic_review"]
    if review.get("machine_final_quality_claim") is not False or review.get("guardian_review_still_required") is not True:
        add_error(errors, "E_DEV_REVIEW_BOUNDARY", "dev_review", str(review))
    if review.get("candidate_count") != 40 or review.get("first_acceptance_count", 0) < 36 or review.get("devreg_semantic_gate_pass") is not True:
        add_error(errors, "E_DEV_REVIEW_GATE", "dev_review", str(review))
    assert_digest(errors, "dev_review", review, "review_digest")
    manifest = load_yaml(root / FREEZE_MANIFEST_PATH)["calibration_freeze_manifest"]
    if manifest.get("calibration_freeze_ready") is not True or manifest.get("devreg_hidden_phase_allowed") is not True:
        add_error(errors, "E_FREEZE_NOT_READY", "freeze", str(manifest))
    for entry in manifest.get("path_digests", []):
        path = root / entry["path"]
        if not path.exists() or sha256_file(path) != entry["sha256"]:
            add_error(errors, "E_FREEZE_PATH_DIGEST", entry["path"], entry["sha256"])
    assert_digest(errors, "freeze", manifest, "manifest_digest")


def validate_hidden(root: Path, errors: list[dict[str, str]]) -> None:
    if not (root / RESULT_PATH).exists():
        return
    for path in HIDDEN_PATHS:
        if not (root / path).exists():
            add_error(errors, "E_HIDDEN_FILE_MISSING", path.as_posix(), "missing")
    if errors:
        return
    result = load_yaml(root / RESULT_PATH)["qualification_repair_002_result"]
    calibration_sha = result["calibration"]["calibration_freeze_commit_sha"]
    manifest = load_yaml(root / FREEZE_MANIFEST_PATH)["calibration_freeze_manifest"]
    frozen_paths = manifest["frozen_core_paths"]
    frozen_diff = git(root, ["diff", "--name-only", f"{calibration_sha}..HEAD", "--", *frozen_paths]).splitlines()
    if frozen_diff:
        add_error(errors, "E_FROZEN_CORE_CHANGED_AFTER_CALIBRATION", "freeze", str(frozen_diff))
    hidden_packs = [row["hidden_r002_material_pack"] for row in load_jsonl(root / HIDDEN_PACKS_PATH)]
    hidden_assignments = [row["hidden_r002_assignment"] for row in load_jsonl(root / HIDDEN_ASSIGNMENTS_PATH)]
    hidden_plans = [row["hidden_r002_qualification_plan"] for row in load_jsonl(root / HIDDEN_PLANS_PATH)]
    hidden_projections = [row["hidden_r002_authoring_projection"] for row in load_jsonl(root / HIDDEN_PROJECTIONS_PATH)]
    hidden_envelopes = [row["hidden_r002_review_envelope"] for row in load_jsonl(root / HIDDEN_ENVELOPES_PATH)]
    hidden_candidates = [row["hidden_r002_candidate"] for row in load_jsonl(root / HIDDEN_CANDIDATES_PATH)]
    machine = [row["hidden_r002_machine_result"] for row in load_jsonl(root / HIDDEN_MACHINE_PATH)]
    checkpoints = [row["hidden_r002_checkpoint_record"] for row in load_jsonl(root / HIDDEN_CHECKPOINT_PATH)]
    if [len(hidden_packs), len(hidden_assignments), len(hidden_plans), len(hidden_projections), len(hidden_envelopes), len(hidden_candidates), len(machine)] != [20, 40, 40, 40, 40, 40, 40]:
        add_error(errors, "E_HIDDEN_COUNTS", "hidden", str([len(hidden_packs), len(hidden_assignments), len(hidden_plans), len(hidden_projections), len(hidden_envelopes), len(hidden_candidates), len(machine)]))
    if any(pack.get("runtime_consumable") is not False or pack.get("publishable") is not False for pack in hidden_packs):
        add_error(errors, "E_HIDDEN_PACK_BOUNDARY", "hidden_packs", "bad boundary")
    if any(assignment.get("old_candidate_id_reuse") is not False or assignment.get("new_candidate_id") is not True for assignment in hidden_assignments):
        add_error(errors, "E_HIDDEN_ID_REUSE", "hidden_assignments", "old id reuse")
    if any(plan.get("owner") != "ORCH" or plan.get("writer") != "ORCH" for plan in hidden_plans):
        add_error(errors, "E_HIDDEN_PLAN_OWNER", "hidden_plans", "non ORCH")
    for candidate in hidden_candidates:
        validate_candidate(candidate, errors, "hidden_candidate")
    if any(row.get("machine_acceptance_state") != "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN" for row in machine):
        add_error(errors, "E_HIDDEN_MACHINE_STATE", "machine", "bad state")
    if any(row.get("accepted_content_count") != 0 or row.get("published_content_count") != 0 for row in machine):
        add_error(errors, "E_HIDDEN_MACHINE_ACCEPTED", "machine", "machine accepted content")
    if len(checkpoints) != 4 or any(row.get("rewrite_or_reroll_count") != 0 for row in checkpoints):
        add_error(errors, "E_HIDDEN_CHECKPOINT", "checkpoints", str(checkpoints))
    binding = load_yaml(root / HIDDEN_BINDING_PATH)["hidden_r002_freeze_binding"]
    if binding.get("calibration_core_changed_after_freeze") is not False:
        add_error(errors, "E_HIDDEN_BINDING", "hidden_binding", str(binding))
    assert_digest(errors, "hidden_binding", binding, "binding_digest")
    if result.get("verdict") != "EXECUTED_PENDING_GUARDIAN":
        add_error(errors, "E_RESULT_VERDICT", "result", str(result.get("verdict")))
    if result["hidden_r002"].get("generated_count") != 40 or result["counting"].get("baseline_increment_count") != 0:
        add_error(errors, "E_RESULT_COUNTS", "result", str(result))
    if result["qualification"].get("generator_qualified") is not False:
        add_error(errors, "E_GENERATOR_QUALIFIED", "result", "generator qualified true")
    readiness = result.get("readiness", {})
    if any(readiness.get(key) is not False for key in READINESS_KEYS):
        add_error(errors, "E_READINESS_FLIP", "result", str(readiness))
    assert_digest(errors, "result", result, "result_digest")
    packet = load_yaml(root / PACKET_PATH)["qualification_guardian_review_packet"]
    if packet.get("guardian_must_not_trust_machine_quality") is not True or packet.get("generator_qualified") is not False:
        add_error(errors, "E_PACKET_BOUNDARY", "packet", str(packet))
    assert_digest(errors, "packet", packet, "packet_digest")
    route = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"].get("route_migration_29")
    if not route:
        add_error(errors, "E_ROUTE29_MISSING", "ledger", "missing")
    else:
        if route.get("migration_digest") != object_digest(route, {"migration_digest"}):
            add_error(errors, "E_ROUTE29_DIGEST", "ledger", "bad digest")
        if route.get("qualification_calibration_repair_002", {}).get("result_digest") != result["result_digest"]:
            add_error(errors, "E_ROUTE29_RESULT_DIGEST", "ledger", "result digest mismatch")
        disclosure = route.get("historical_digest_disclosure", {})
        if disclosure.get("route_migration_28_runner_change_disclosed") is not True:
            add_error(errors, "E_ROUTE29_DISCLOSURE", "ledger", str(disclosure))


def validate_ci(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / CI_PATH).read_text(encoding="utf-8")
    required = [
        "python3 ci/checkers/check_controlled_v2_qualification_calibration_targeted_repair_002.py",
        "python3 ci/checkers/check_controlled_v2_qualification_calibration_targeted_repair_002.py --selftest",
        "run_qualification_calibration_repair_002_materializer.py --phase calibration --check",
        "run_qualification_calibration_repair_002_materializer.py --phase hidden --check",
    ]
    for snippet in required:
        if snippet not in text:
            add_error(errors, "E_CI_REGISTRATION", "ci", snippet)
    optimized_block = text.split("Verify fail-closed optimized mode", 1)[-1]
    if "check_controlled_v2_qualification_calibration_targeted_repair_002.py --selftest" not in optimized_block:
        add_error(errors, "E_CI_OPTIMIZED", "ci", "new checker not in -O loop")


def run_all(root: Path, enforce_git: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if enforce_git:
        validate_phase0(root, errors)
        validate_write_surface(root, errors)
        validate_old_task_unchanged(root, errors)
    validate_calibration(root, errors)
    validate_hidden(root, errors)
    validate_ci(root, errors)
    return errors


def selftest() -> int:
    root = Path.cwd()
    errors = run_all(root, enforce_git=False)
    if errors:
        print(json.dumps({"status": "SELFTEST_BASE_INVALID", "errors": errors[:8]}, ensure_ascii=False), file=sys.stderr)
        return 1
    candidates_path = root / (HIDDEN_CANDIDATES_PATH if (root / HIDDEN_CANDIDATES_PATH).exists() else DEV_CANDIDATES_PATH)
    key = "hidden_r002_candidate" if candidates_path == root / HIDDEN_CANDIDATES_PATH else "devreg_candidate"
    candidate = load_jsonl(candidates_path)[0][key]
    mutated_errors: list[dict[str, str]] = []
    bad = copy.deepcopy(candidate)
    bad["audience_form_candidate"]["title"] += " 内部审查"
    validate_candidate(bad, mutated_errors, "selftest")
    if "E_FORBIDDEN_SURFACE_SNIPPET" not in {error["code"] for error in mutated_errors}:
        print("SELFTEST_FAIL forbidden surface not detected", file=sys.stderr)
        return 1
    mutated_errors = []
    bad = copy.deepcopy(candidate)
    bad["qualification_wrapper"]["runtime_consumable"] = True
    validate_candidate(bad, mutated_errors, "selftest")
    if "E_CANDIDATE_WRAPPER" not in {error["code"] for error in mutated_errors}:
        print("SELFTEST_FAIL runtime wrapper not detected", file=sys.stderr)
        return 1
    mutated_errors = []
    bad = copy.deepcopy(candidate)
    bad["surface_units"] = bad["surface_units"][:-1]
    validate_candidate(bad, mutated_errors, "selftest")
    if "E_EXACT_JOIN" not in {error["code"] for error in mutated_errors}:
        print("SELFTEST_FAIL exact join not detected", file=sys.stderr)
        return 1
    print("check_controlled_v2_qualification_calibration_targeted_repair_002 SELFTEST_PASS 3 cases")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errors = run_all(Path.cwd(), enforce_git="--no-git" not in argv)
    if errors:
        for error in errors:
            print(json.dumps(error, ensure_ascii=False, sort_keys=True))
        return 1
    print("check_controlled_v2_qualification_calibration_targeted_repair_002 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
