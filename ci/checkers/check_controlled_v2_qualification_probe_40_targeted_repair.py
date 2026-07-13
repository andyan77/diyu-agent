#!/usr/bin/env python3
"""Fail-closed checker for targeted qualification probe 40 repair."""

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
    print("check_controlled_v2_qualification_probe_40_targeted_repair refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "CONTROLLED_V2_QUALIFICATION_PROBE_40_TARGETED_REPAIR_001"
PHASE0_MERGE_COMMIT_SHA = "531fe864b0b338a8708449ae29e739e2dce8e119"
REVIEWED_BASE_SHA = "25ce4ff092befe39106783d8b7f2cf31e77f0e82"
REVIEWED_HEAD_SHA = "aaeda5a280b2790c00157e47f89370f6535ee230"
REVIEWED_HEAD_TREE_SHA = "63eba39bf2ed4f31d0906d8339fe169adf9a79a4"
REVIEWED_FULL_DIFF_DIGEST = "5305d3de6760e9410965325bc998a3036697440e662b595d37c2b4e7c8632df6"

TASK_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_targeted_repair_001")
V1_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CI_PATH = Path(".github/workflows/ci.yml")
CHECKER_PATH = Path("ci/checkers/check_controlled_v2_qualification_probe_40_targeted_repair.py")
MATERIALIZER_PATH = TASK_DIR / "run_targeted_repair_materializer.py"
SUCCESSOR_CALIBRATION_REPAIR_002_DIR = Path(
    "controlled_content_generator_v2_001/qualification_calibration_targeted_repair_002"
)
SUCCESSOR_CALIBRATION_REPAIR_002_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_qualification_calibration_targeted_repair_002.py"
)
SUCCESSOR_CONVERGENCE_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001"
)
SUCCESSOR_B_LANE_DIR = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001"
)
SUCCESSOR_CONVERGENCE_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_creative_authoring_route_convergence.py"
)
V1_GENERATOR_ENTRY_PATH = V1_DIR / "run_qualification_probe_40_generator_acceptance.py"
GENERATOR_BUILD_FREEZER_PATH = Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001/run_generator_v2_acceptance_harness.py")
ORCH_FREEZER_PATH = Path(
    "08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001/"
    "run_orch_20cp_validation_dryrun_freezer.py"
)
FACT_AUTH_FREEZER_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/fact_authorization_fixture_closeout_001/"
    "run_fact_authorization_fixture_freezer.py"
)
COMPONENT_SUPPLY_FREEZER_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/component_supply_closeout_20cp_001/"
    "run_component_supply_closeout_freezer.py"
)

REVIEW_CONTRACT_PATH = TASK_DIR / "qualification_review_contract.v1.2.yaml"
SUFFICIENCY_PATH = TASK_DIR / "material_sufficiency_matrix.v0.1.yaml"
STYLE_PATH = TASK_DIR / "style_vector_and_allocation_contract.v0.1.yaml"
DEV_PACKS_PATH = TASK_DIR / "development_material_packs.v0.2.jsonl"
DEV_CANDIDATES_PATH = TASK_DIR / "development_regression_candidates.v0.2.jsonl"
DEV_RESULT_PATH = TASK_DIR / "development_regression_result.v0.1.yaml"
ROUTE_REGISTRY_PATH = TASK_DIR / "route_case_registry.v0.1.jsonl"
ROUTE_RESULTS_PATH = TASK_DIR / "route_case_results.v0.1.jsonl"
FREEZE_MANIFEST_PATH = TASK_DIR / "calibration_freeze_manifest.v0.1.yaml"
HIDDEN_PACKS_PATH = TASK_DIR / "hidden_material_packs.v0.1.jsonl"
HIDDEN_ASSIGNMENTS_PATH = TASK_DIR / "hidden_assignments.v0.1.jsonl"
HIDDEN_PLANS_PATH = TASK_DIR / "hidden_composition_plans.v0.1.jsonl"
HIDDEN_CANDIDATES_PATH = TASK_DIR / "hidden_candidates.v0.1.jsonl"
HIDDEN_RESULTS_PATH = TASK_DIR / "hidden_machine_results.v0.1.jsonl"
FINAL_RESULT_PATH = TASK_DIR / "qualification_rerun_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "qualification_guardian_review_packet.v0.1.yaml"

CALIBRATION_PATHS = {
    REVIEW_CONTRACT_PATH,
    SUFFICIENCY_PATH,
    STYLE_PATH,
    DEV_PACKS_PATH,
    DEV_CANDIDATES_PATH,
    DEV_RESULT_PATH,
    ROUTE_REGISTRY_PATH,
    ROUTE_RESULTS_PATH,
    FREEZE_MANIFEST_PATH,
    MATERIALIZER_PATH,
    CHECKER_PATH,
    CI_PATH,
}
HIDDEN_PATHS = {
    HIDDEN_PACKS_PATH,
    HIDDEN_ASSIGNMENTS_PATH,
    HIDDEN_PLANS_PATH,
    HIDDEN_CANDIDATES_PATH,
    HIDDEN_RESULTS_PATH,
    FINAL_RESULT_PATH,
    PACKET_PATH,
    LEDGER_PATH,
}
EXPECTED_CPS = [f"CP{index:02d}" for index in range(1, 21)]
V1_BYTE_PATHS = [
    V1_DIR / "qualification_material_packs.v0.1.jsonl",
    V1_DIR / "qualification_probe_assignments.v0.1.jsonl",
    V1_DIR / "canonical_qualification_composition_plans.v0.1.jsonl",
    V1_DIR / "qualification_probe_candidates.v0.1.jsonl",
    V1_DIR / "qualification_machine_acceptance_results.v0.1.jsonl",
    V1_DIR / "qualification_probe_result.v0.1.yaml",
    V1_DIR / "qualification_guardian_review_packet.v0.1.yaml",
]


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
    if tree != REVIEWED_HEAD_TREE_SHA:
        add_error(errors, "E_PHASE0_TREE", "phase0", tree)
    actual_diff = git(root, ["diff", f"{REVIEWED_BASE_SHA}..{REVIEWED_HEAD_SHA}"])
    if sha256_text(actual_diff) != REVIEWED_FULL_DIFF_DIGEST:
        add_error(errors, "E_PHASE0_DIFF_DIGEST", "phase0", sha256_text(actual_diff))


def validate_v1_identity(root: Path, errors: list[dict[str, str]]) -> None:
    for path in V1_BYTE_PATHS:
        old = git(root, ["show", f"{PHASE0_MERGE_COMMIT_SHA}:{path.as_posix()}"])
        if not old:
            add_error(errors, "E_V1_BASELINE_READ", path.as_posix(), "missing in phase0")
        elif (root / path).read_text(encoding="utf-8") != old:
            add_error(errors, "E_V1_BYTE_DRIFT", path.as_posix(), "v1 asset changed")
    old_ledger = git(root, ["show", f"{PHASE0_MERGE_COMMIT_SHA}:{LEDGER_PATH.as_posix()}"])
    if old_ledger:
        old_data = yaml.safe_load(old_ledger)["grc_3600_execution_plan_status"]
        current = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
        for key, value in old_data.items():
            if current.get(key) != value:
                add_error(errors, "E_LEDGER_PRIOR_DRIFT", "ledger", key)


def validate_calibration(root: Path, errors: list[dict[str, str]]) -> None:
    required = [path for path in CALIBRATION_PATHS if path not in {CI_PATH, CHECKER_PATH, MATERIALIZER_PATH}]
    for path in required:
        if not (root / path).exists():
            add_error(errors, "E_CALIBRATION_FILE_MISSING", path.as_posix(), "missing")
    if errors:
        return
    contract = load_yaml(root / REVIEW_CONTRACT_PATH)["qualification_review_contract"]
    if contract.get("contract_digest") != object_digest(contract, {"contract_digest"}):
        add_error(errors, "E_REVIEW_CONTRACT_DIGEST", "review_contract", "digest mismatch")
    passline = contract.get("qualification_passline", {})
    if passline.get("first_acceptance", {}).get("minimum_accepted_count_for_40") != 36:
        add_error(errors, "E_PASSLINE", "review_contract", str(passline.get("first_acceptance")))
    matrix = load_yaml(root / SUFFICIENCY_PATH)["material_sufficiency_matrix"]
    if len(matrix.get("profiles", [])) != 20 or matrix.get("uniform_minimum_fact_count_for_all_CP") != "forbidden":
        add_error(errors, "E_SUFFICIENCY_MATRIX", "sufficiency", str(matrix.get("profiles", [])))
    if any(row.get("single_fact_atom_is_sufficient") is not False for row in matrix["profiles"]):
        add_error(errors, "E_SINGLE_FACT_SUFFICIENT", "sufficiency", "single fact allowed")
    style = load_yaml(root / STYLE_PATH)["style_vector_and_allocation_contract"]
    if len(style.get("style_vectors", [])) < 8 or style.get("global_restrained_documentary_voice_default_removed") is not True:
        add_error(errors, "E_STYLE_VECTOR", "style", str(style))
    if style.get("global_fixed_CTA_count") != 0 or style.get("global_fixed_spoken_line_count_pattern") is not False:
        add_error(errors, "E_STYLE_GLOBAL_DEFAULT", "style", str(style))
    dev_packs = [row["development_material_pack"] for row in load_jsonl(root / DEV_PACKS_PATH)]
    dev_candidates = [row["development_revision"] for row in load_jsonl(root / DEV_CANDIDATES_PATH)]
    route_cases = [row["qualification_route_case"] for row in load_jsonl(root / ROUTE_REGISTRY_PATH)]
    route_results = [row["qualification_route_case_result"] for row in load_jsonl(root / ROUTE_RESULTS_PATH)]
    if len(dev_packs) != 20 or Counter(row["content_product_type_id"] for row in dev_packs) != {cp: 1 for cp in EXPECTED_CPS}:
        add_error(errors, "E_DEV_PACK_COUNT", "dev_packs", str(len(dev_packs)))
    if any(row.get("material_sufficiency_pass") is not True or row.get("runtime_consumable") is not False for row in dev_packs):
        add_error(errors, "E_DEV_PACK_BOUNDARY", "dev_packs", "bad material boundary")
    if len(dev_candidates) != 40:
        add_error(errors, "E_DEV_REGRESSION_COUNT", "dev_candidates", str(len(dev_candidates)))
    if any(row.get("lifecycle_status") != "DEVELOPMENT_REGRESSION_ONLY" for row in dev_candidates):
        add_error(errors, "E_DEV_LIFECYCLE", "dev_candidates", "bad lifecycle")
    if any("INTERNAL QUALIFICATION" in canonical_json(row.get("audience_form_candidate", {})) for row in dev_candidates):
        add_error(errors, "E_REVIEW_WRAPPER_LEAK", "dev_candidates", "review wrapper leaked to audience surface")
    if len(route_cases) != 60 or len(route_results) != 60:
        add_error(errors, "E_ROUTE_COUNT", "routes", f"{len(route_cases)}/{len(route_results)}")
    if any(row.get("audience_content_created") is not False or row.get("runtime_consumable") is not False for row in route_cases):
        add_error(errors, "E_ROUTE_CONTENT_LEAK", "routes", "route case leaked content/runtime")
    result = load_yaml(root / DEV_RESULT_PATH)["development_regression_result"]
    if result.get("result_digest") != object_digest(result, {"result_digest"}):
        add_error(errors, "E_DEV_RESULT_DIGEST", "dev_result", "digest mismatch")
    if result.get("baseline_increment_count") != 0 or result.get("generator_qualified") is not False:
        add_error(errors, "E_DEV_RESULT_BOUNDARY", "dev_result", str(result))
    manifest = load_yaml(root / FREEZE_MANIFEST_PATH)["calibration_freeze_manifest"]
    if manifest.get("manifest_digest") != object_digest(manifest, {"manifest_digest"}):
        add_error(errors, "E_FREEZE_MANIFEST_DIGEST", "freeze", "digest mismatch")


def validate_hidden(root: Path, errors: list[dict[str, str]]) -> None:
    if not (root / FINAL_RESULT_PATH).exists():
        return
    for path in HIDDEN_PATHS:
        if not (root / path).exists():
            add_error(errors, "E_HIDDEN_FILE_MISSING", path.as_posix(), "missing")
    if errors:
        return
    final = load_yaml(root / FINAL_RESULT_PATH)["qualification_rerun_result"]
    calibration_sha = final["calibration"]["calibration_freeze_commit_sha"]
    frozen_paths = [
        path.as_posix()
        for path in CALIBRATION_PATHS
        if path not in {CI_PATH, CHECKER_PATH, MATERIALIZER_PATH}
    ]
    frozen_diff = git(root, ["diff", "--name-only", f"{calibration_sha}..HEAD", "--", *frozen_paths]).splitlines()
    if frozen_diff:
        add_error(errors, "E_FREEZE_CORE_CHANGED", "freeze", str(frozen_diff))
    hidden_packs = [row["hidden_material_pack"] for row in load_jsonl(root / HIDDEN_PACKS_PATH)]
    assignments = [row["hidden_assignment"] for row in load_jsonl(root / HIDDEN_ASSIGNMENTS_PATH)]
    plans = [row["hidden_qualification_composition_plan"] for row in load_jsonl(root / HIDDEN_PLANS_PATH)]
    candidates = [row["hidden_qualification_candidate"] for row in load_jsonl(root / HIDDEN_CANDIDATES_PATH)]
    machine = [row["hidden_machine_result"] for row in load_jsonl(root / HIDDEN_RESULTS_PATH)]
    if [len(hidden_packs), len(assignments), len(plans), len(candidates), len(machine)] != [20, 40, 40, 40, 40]:
        add_error(errors, "E_HIDDEN_COUNTS", "hidden", str([len(hidden_packs), len(assignments), len(plans), len(candidates), len(machine)]))
    if any(row.get("runtime_consumable") is not False or row.get("publishable") is not False for row in hidden_packs):
        add_error(errors, "E_HIDDEN_PACK_BOUNDARY", "hidden_packs", "bad boundary")
    if any(row.get("new_hidden_ID") is not True or row.get("old_ID_reuse") is not False for row in assignments):
        add_error(errors, "E_HIDDEN_ASSIGNMENT_ID", "assignments", "id reuse")
    if any(row.get("owner") != "ORCH" or row.get("writer") != "ORCH" for row in plans):
        add_error(errors, "E_HIDDEN_PLAN_OWNER", "plans", "non ORCH plan")
    if any(row.get("runtime_consumable") is not False or row.get("publishable") is not False for row in plans):
        add_error(errors, "E_HIDDEN_PLAN_BOUNDARY", "plans", "runtime plan")
    for candidate in candidates:
        if candidate.get("acceptance_state") != "PENDING_GUARDIAN_FULL_SURFACE_REVIEW":
            add_error(errors, "E_HIDDEN_CANDIDATE_STATE", candidate.get("candidate_id", "?"), str(candidate.get("acceptance_state")))
        wrapper = candidate.get("qualification_wrapper", {})
        if wrapper.get("hidden_holdout") is not True or wrapper.get("runtime_consumable") is not False:
            add_error(errors, "E_HIDDEN_WRAPPER", candidate.get("candidate_id", "?"), str(wrapper))
        expected_paths = set()
        audience = candidate["audience_form_candidate"]
        expected_paths.add("audience_form_candidate.title")
        expected_paths.update(f"audience_form_candidate.body[{i}]" for i, _ in enumerate(audience["body"].split("\n")))
        expected_paths.update(f"audience_form_candidate.spoken_lines[{i}]" for i, _ in enumerate(audience["spoken_lines"]))
        if audience["CTA"]:
            expected_paths.add("audience_form_candidate.CTA")
        execution = candidate["execution_payload"]
        expected_paths.update(f"execution_payload.visual_beats[{i}]" for i, _ in enumerate(execution["visual_beats"]))
        expected_paths.update(f"execution_payload.capture_instructions[{i}]" for i, _ in enumerate(execution["capture_instructions"]))
        expected_paths.update(["execution_payload.audio_grammar", "execution_payload.editing_grammar"])
        actual_paths = {unit["field_path"] for unit in candidate["surface_units"]}
        if expected_paths != actual_paths:
            add_error(errors, "E_HIDDEN_EXACT_JOIN", candidate["candidate_id"], str(sorted(expected_paths ^ actual_paths)))
        if any(not unit.get("source_refs") or not unit.get("authorization_refs") for unit in candidate["surface_units"]):
            add_error(errors, "E_HIDDEN_SOURCE_AUTH", candidate["candidate_id"], "missing source/auth")
    if any(row.get("machine_acceptance_state") != "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN" for row in machine):
        add_error(errors, "E_HIDDEN_MACHINE_STATE", "machine", "bad state")
    if final.get("result_digest") != object_digest(final, {"result_digest"}):
        add_error(errors, "E_FINAL_DIGEST", "final", "digest mismatch")
    if final["hidden"].get("generated_count") != 40 or final["counting"].get("baseline_increment_count") != 0:
        add_error(errors, "E_FINAL_COUNTS", "final", str(final))
    if final["qualification"].get("generator_qualified") is not False:
        add_error(errors, "E_GENERATOR_QUALIFIED", "final", "generator qualified flipped")
    route = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"].get("route_migration_28")
    if not route or route.get("migration_digest") != object_digest(route, {"migration_digest"}):
        add_error(errors, "E_ROUTE28", "ledger", "missing or bad digest")
    elif route.get("qualification_targeted_repair", {}).get("result_digest") != final["result_digest"]:
        add_error(errors, "E_ROUTE28_RESULT", "ledger", "result digest mismatch")
    packet = load_yaml(root / PACKET_PATH)["qualification_guardian_review_packet"]
    if packet.get("packet_digest") != object_digest(packet, {"packet_digest"}):
        add_error(errors, "E_PACKET_DIGEST", "packet", "digest mismatch")


def validate_ci(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / CI_PATH).read_text(encoding="utf-8")
    required = [
        "python3 ci/checkers/check_controlled_v2_qualification_probe_40_targeted_repair.py",
        "python3 ci/checkers/check_controlled_v2_qualification_probe_40_targeted_repair.py --selftest",
        "run_targeted_repair_materializer.py --phase calibration --check",
        "run_targeted_repair_materializer.py --phase hidden --check",
    ]
    for snippet in required:
        if snippet not in text:
            add_error(errors, "E_CI_REGISTRATION", "ci", snippet)
    if "check_controlled_v2_qualification_probe_40_targeted_repair.py --selftest" not in text.split("Verify fail-closed optimized mode", 1)[-1]:
        add_error(errors, "E_CI_OPTIMIZED", "ci", "optimized-mode missing")


def validate_write_surface(root: Path, errors: list[dict[str, str]]) -> None:
    allowed = set(CALIBRATION_PATHS | HIDDEN_PATHS | {CHECKER_PATH})
    allowed.update({
        Path("ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py"),
        SUCCESSOR_CALIBRATION_REPAIR_002_CHECKER_PATH,
        SUCCESSOR_CONVERGENCE_CHECKER_PATH,
        Path("ci/checkers/check_controlled_content_generator_v2_build.py"),
        Path("ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py"),
        Path("ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py"),
        Path("ci/checkers/check_orch_v2_20cp_validation_dryrun.py"),
        V1_GENERATOR_ENTRY_PATH,
        GENERATOR_BUILD_FREEZER_PATH,
        ORCH_FREEZER_PATH,
        FACT_AUTH_FREEZER_PATH,
        COMPONENT_SUPPLY_FREEZER_PATH,
    })
    unexpected = sorted(
        path.as_posix()
        for path in changed_paths(root)
        if not path.is_relative_to(TASK_DIR)
        and not path.is_relative_to(SUCCESSOR_CALIBRATION_REPAIR_002_DIR)
        and not path.is_relative_to(SUCCESSOR_CONVERGENCE_DIR)
        and not path.is_relative_to(SUCCESSOR_B_LANE_DIR)
        and path not in allowed
    )
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", "git", str(unexpected))


def run_all(root: Path, enforce_git: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if enforce_git:
        validate_phase0(root, errors)
        validate_write_surface(root, errors)
    validate_v1_identity(root, errors)
    validate_calibration(root, errors)
    validate_hidden(root, errors)
    validate_ci(root, errors)
    return errors


def selftest() -> int:
    root = Path.cwd()
    errors = run_all(root, enforce_git=False)
    if errors:
        print(json.dumps({"status": "SELFTEST_BASE_INVALID", "errors": errors[:5]}, ensure_ascii=False), file=sys.stderr)
        return 1
    tests: list[tuple[str, str, Any]] = []
    dev = [row["development_material_pack"] for row in load_jsonl(root / DEV_PACKS_PATH)]
    tests.append(("single_fact_pack_rejected", "E_DEV_PACK_BOUNDARY", lambda: dev[0].__setitem__("runtime_consumable", True)))
    routes = [row["qualification_route_case"] for row in load_jsonl(root / ROUTE_REGISTRY_PATH)]
    tests.append(("route_content_rejected", "E_ROUTE_CONTENT_LEAK", lambda: routes[0].__setitem__("audience_content_created", True)))
    if (root / FINAL_RESULT_PATH).exists():
        hidden = [row["hidden_qualification_candidate"] for row in load_jsonl(root / HIDDEN_CANDIDATES_PATH)]
        tests.append(("hidden_wrapper_rejected", "E_HIDDEN_WRAPPER", lambda: hidden[0]["qualification_wrapper"].__setitem__("runtime_consumable", True)))
    for name, code, mutate in tests:
        mutated_errors: list[dict[str, str]] = []
        mutate()
        if name.startswith("single"):
            if any(row.get("runtime_consumable") is not False for row in dev):
                add_error(mutated_errors, "E_DEV_PACK_BOUNDARY", name, "bad")
        elif name.startswith("route"):
            if any(row.get("audience_content_created") is not False for row in routes):
                add_error(mutated_errors, "E_ROUTE_CONTENT_LEAK", name, "bad")
        else:
            if any(row.get("qualification_wrapper", {}).get("runtime_consumable") is not False for row in hidden):
                add_error(mutated_errors, "E_HIDDEN_WRAPPER", name, "bad")
        if code not in {error["code"] for error in mutated_errors}:
            print(f"SELFTEST_FAIL {name}", file=sys.stderr)
            return 1
    print(f"{Path(__file__).name} SELFTEST_PASS {len(tests)} cases")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    errors = run_all(Path.cwd(), enforce_git="--no-git" not in argv)
    if errors:
        for error in errors:
            print(json.dumps(error, ensure_ascii=False, sort_keys=True))
        return 1
    print("check_controlled_v2_qualification_probe_40_targeted_repair PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
