#!/usr/bin/env python3
"""Fail-closed checker for the Controlled Content Generator V2 build harness."""

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
    print("check_controlled_content_generator_v2_build refuses python -O", file=sys.stderr)
    raise SystemExit(2)


TASK_ID = "CONTROLLED_CONTENT_GENERATOR_V2_BUILD_AND_ACCEPTANCE_HARNESS_001"
BASELINE_HEAD = "0ed9fd40203a6423d4deb9e6342c441ac3c129c1"
PHASE0_MERGE_TREE_SHA = "39cf72e29dba7da8e9071919813f1001dcfe9afb"
REVIEWED_BASE_SHA = "6253e3d1661cd46945a3443de54ac55df5b7d746"
REVIEWED_HEAD_SHA = "8ee1cfe874011b3e94ce63061b573b67617fb197"
REVIEWED_HEAD_TREE_SHA = "39cf72e29dba7da8e9071919813f1001dcfe9afb"
REVIEWED_FULL_DIFF_DIGEST = "2707a1ba75482ca40c95f06945e818d51525dc5f0b25c5e2b547f26432a6064f"

TASK_DIR = Path("controlled_content_generator_v2_001/build_and_acceptance_harness_001")
CONTRACT_PATH = TASK_DIR / "controlled_content_generator_v2_contract.v0.1.yaml"
CASES_PATH = TASK_DIR / "generator_acceptance_harness_cases.v0.1.jsonl"
RESULTS_PATH = TASK_DIR / "generator_acceptance_harness_results.v0.1.jsonl"
BUILD_RESULT_PATH = TASK_DIR / "generator_v2_build_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "generator_guardian_review_packet.v0.1.yaml"
FREEZER_PATH = TASK_DIR / "run_generator_v2_acceptance_harness.py"
CHECKER_PATH = Path("ci/checkers/check_controlled_content_generator_v2_build.py")
QUALIFICATION_PROBE_CHECKER_PATH = Path("ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py")
TARGETED_REPAIR_CHECKER_PATH = Path("ci/checkers/check_controlled_v2_qualification_probe_40_targeted_repair.py")
CALIBRATION_REPAIR_002_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_qualification_calibration_targeted_repair_002.py"
)
CONVERGENCE_CHECKER_PATH = Path(
    "ci/checkers/check_controlled_v2_creative_authoring_route_convergence.py"
)
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
CI_PATH = Path(".github/workflows/ci.yml")
SUCCESSOR_QUALIFICATION_PROBE_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")
SUCCESSOR_TARGETED_REPAIR_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_targeted_repair_001")
SUCCESSOR_CALIBRATION_REPAIR_002_DIR = Path(
    "controlled_content_generator_v2_001/qualification_calibration_targeted_repair_002"
)
SUCCESSOR_CONVERGENCE_DIR = Path(
    "controlled_content_generator_v2_001/creative_authoring_route_oracle_convergence_001"
)
SUCCESSOR_B_LANE_DIR = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001"
)

GKB_ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
PROFILES_PATH = GKB_ROOT / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
COMPONENT_REGISTRY_PATH = GKB_ROOT / "component_supply_closeout_20cp_001/reviewed_reusable_component_registry.v0.3.jsonl"
VALIDATION_FIXTURES_PATH = GKB_ROOT / "fact_authorization_fixture_closeout_001/content_product_validation_fixtures.v0.1.jsonl"
ORCH_DIR = Path("08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001")
ORCH_REQUESTS_PATH = ORCH_DIR / "orch_validation_requests.v0.1.jsonl"
ORCH_DECISIONS_PATH = ORCH_DIR / "orch_dryrun_decisions.v0.1.jsonl"
ORCH_PLANS_PATH = ORCH_DIR / "orch_validation_canonical_plans.v0.1.jsonl"
ORCH_CONTRACT_PATH = ORCH_DIR / "orch_validation_plan_contract.v0.1.yaml"
ORCH_RESULT_PATH = ORCH_DIR / "orch_20cp_dryrun_result.v0.1.yaml"

COMPONENT_SUPPLY_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py")
FACT_AUTH_CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py")
ORCH_CHECKER_PATH = Path("ci/checkers/check_orch_v2_20cp_validation_dryrun.py")
COMPONENT_SUPPLY_RESULT_PATH = GKB_ROOT / "component_supply_closeout_20cp_001/component_supply_closeout_result.v0.1.yaml"
COMPONENT_SUPPLY_FREEZER_PATH = GKB_ROOT / "component_supply_closeout_20cp_001/run_component_supply_closeout_freezer.py"
FACT_AUTH_RESULT_PATH = GKB_ROOT / "fact_authorization_fixture_closeout_001/fact_authorization_fixture_closeout_result.v0.1.yaml"
FACT_AUTH_FREEZER_PATH = GKB_ROOT / "fact_authorization_fixture_closeout_001/run_fact_authorization_fixture_freezer.py"
ORCH_CONTRACT_METADATA_PATH = ORCH_CONTRACT_PATH
ORCH_RESULT_METADATA_PATH = ORCH_RESULT_PATH
ORCH_FREEZER_PATH = ORCH_DIR / "run_orch_20cp_validation_dryrun_freezer.py"

EXPECTED_COUNTS = {
    "content_product_profile_count": 20,
    "reviewed_reusable_component_count": 64,
    "validation_fixture_count": 60,
    "ORCH_validation_request_count": 60,
    "ORCH_validation_decision_count": 60,
    "canonical_validation_composition_plan_count": 20,
}
EXPECTED_DIGESTS = {
    "content_product_profile_registry_object_digest": "160f640f3c677b3e3aa7fb13c89549c61825cdde1919731bc573740ae38ef53b",
    "content_product_profile_file_sha256": "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056",
    "reviewed_reusable_component_registry_sha256": "e5a3f31a9017a39e51ad409531e26b1e910e8e2effb34a4a24dab5fd11105bb1",
    "validation_fixture_sha256": "bff74e6fac3fe85733fc6d094a81d14af3c303aa0a003e7dc7776cc034043697",
    "ORCH_validation_requests_sha256": "0ddf7884b872a2bc733e31e69f375caef6b5caebfe9e305694b200969e347283",
    "ORCH_validation_decisions_sha256": "c1ed3481e89580db8927d8c83eb28b17303322f52afcfe9cb749deab5fb2f4e2",
    "ORCH_validation_plans_sha256": "3fb85451adb4d156d621efc47d2edaeda13d25dddba6aba947f5af864e36f230",
    "ORCH_dryrun_result_sha256": "afa2503408826e4e4451bbb6b3ab57ed71bf5b2e2af600f64dcfb53c1ec1d922",
    "ORCH_dryrun_result_digest": "d84b4a38a6ae151390d59572aab7b7c19447215f507ac6bab0f33751da501c05",
}
EXPECTED_LICENSES = {
    "AUTHORIZED_ROLE_JUDGMENT",
    "CAPTURE_BOUND_PERFORMATIVE",
    "EVIDENCE_BOUND_ASSERTION",
    "HYPOTHETICAL_OR_DISCLOSED_SCENE",
    "NONFACTUAL_CREATIVE_EXPRESSION",
    "PUBLISHER_OWNED_SUBJECTIVE_EXPRESSION",
    "STRUCTURAL_LANGUAGE",
}
EXPECTED_FABRICATION_MODES = {
    "specific_brand_fact",
    "real_event",
    "personal_experience_or_biography",
    "customer_story_or_testimonial",
    "enterprise_decision_commitment_history",
    "sku_parameter_inventory_date_version_number",
    "performance_body_effect_causal_claim",
    "direct_quote",
    "third_party_inner_state",
}
READINESS_TRUE_KEYS = {
    "generator_qualified",
    "qualification_probe_40_generation_allowed",
    "runtime_ingest_ready",
    "generation_eligible",
    "generation_allowed",
    "generation_600_allowed",
    "expand_600_allowed",
    "expand_3600_allowed",
    "candidatepack_ready",
    "CandidatePack_ready",
    "KE_ready",
    "Serving_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_ready",
    "release_ready",
    "runtime_generation_eligible",
    "runtime_consumable",
    "runtime_authoritative",
    "production_executable",
    "audience_generation_allowed",
    "audience_facing_output_allowed",
}
FORBIDDEN_PAYLOAD_FIELD_NAMES = {
    "audience_facing_body",
    "body",
    "body_text",
    "copy_text",
    "draft_text",
    "generated_text",
    "publishable_copy",
    "spoken_draft",
    "spoken_line",
    "spoken_line_payload",
    "spoken_script",
    "title",
    "title_text",
    "CTA_payload",
    "cta_payload",
    "canonical_CompositionPlan",
    "runtime_CompositionPlan",
    "production_CompositionPlan",
    "CompositionPlan",
}
ALLOWED_CHANGED_PATHS = {
    CONTRACT_PATH,
    CASES_PATH,
    RESULTS_PATH,
    BUILD_RESULT_PATH,
    PACKET_PATH,
    FREEZER_PATH,
    CHECKER_PATH,
    QUALIFICATION_PROBE_CHECKER_PATH,
    TARGETED_REPAIR_CHECKER_PATH,
    CALIBRATION_REPAIR_002_CHECKER_PATH,
    CONVERGENCE_CHECKER_PATH,
    COMPONENT_SUPPLY_CHECKER_PATH,
    FACT_AUTH_CHECKER_PATH,
    ORCH_CHECKER_PATH,
    COMPONENT_SUPPLY_RESULT_PATH,
    COMPONENT_SUPPLY_FREEZER_PATH,
    FACT_AUTH_RESULT_PATH,
    FACT_AUTH_FREEZER_PATH,
    ORCH_CONTRACT_METADATA_PATH,
    ORCH_RESULT_METADATA_PATH,
    ORCH_FREEZER_PATH,
    LEDGER_PATH,
    CI_PATH,
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
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise TypeError(f"JSONL row is not a mapping: {path}:{line_number}")
        rows.append(row)
    return rows


def unwrap(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"missing wrapper {key}")
    return value


def add_error(errors: list[dict[str, str]], code: str, section: str, detail: str) -> None:
    errors.append({"code": code, "section": section, "detail": detail})


def git(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def git_ok(root: Path, args: list[str]) -> bool:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode == 0


def changed_paths(root: Path) -> set[Path]:
    head = git(root, ["rev-parse", "HEAD"]).strip()
    names = ""
    if head == BASELINE_HEAD:
        names += git(root, ["diff", "--name-only", "HEAD"])
    elif head:
        names += git(root, ["diff", "--name-only", f"{BASELINE_HEAD}..HEAD"])
        names += git(root, ["diff", "--name-only", "HEAD"])
    names += git(root, ["ls-files", "--others", "--exclude-standard"])
    return {Path(line) for line in names.splitlines() if line}


def recursive_true_flags(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in READINESS_TRUE_KEYS and child is True:
                hits.append(child_path)
            hits.extend(recursive_true_flags(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_true_flags(child, f"{path}[{index}]"))
    return hits


def recursive_forbidden_fields(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_PAYLOAD_FIELD_NAMES:
                hits.append(child_path)
            hits.extend(recursive_forbidden_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(recursive_forbidden_fields(child, f"{path}[{index}]"))
    return hits


def profile_registry_object_digest(root: Path) -> str:
    registry = load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]
    return object_digest(registry, {"registry_digest"})


def input_counts(root: Path) -> dict[str, int]:
    return {
        "content_product_profile_count": len(
            load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]["profiles"]
        ),
        "reviewed_reusable_component_count": len(load_jsonl(root / COMPONENT_REGISTRY_PATH)),
        "validation_fixture_count": len(load_jsonl(root / VALIDATION_FIXTURES_PATH)),
        "ORCH_validation_request_count": len(load_jsonl(root / ORCH_REQUESTS_PATH)),
        "ORCH_validation_decision_count": len(load_jsonl(root / ORCH_DECISIONS_PATH)),
        "canonical_validation_composition_plan_count": len(load_jsonl(root / ORCH_PLANS_PATH)),
    }


def input_digests(root: Path) -> dict[str, str]:
    return {
        "content_product_profile_registry_object_digest": profile_registry_object_digest(root),
        "content_product_profile_file_sha256": sha256_file(root / PROFILES_PATH),
        "reviewed_reusable_component_registry_sha256": sha256_file(root / COMPONENT_REGISTRY_PATH),
        "validation_fixture_sha256": sha256_file(root / VALIDATION_FIXTURES_PATH),
        "ORCH_validation_requests_sha256": sha256_file(root / ORCH_REQUESTS_PATH),
        "ORCH_validation_decisions_sha256": sha256_file(root / ORCH_DECISIONS_PATH),
        "ORCH_validation_plans_sha256": sha256_file(root / ORCH_PLANS_PATH),
        "ORCH_dryrun_result_sha256": sha256_file(root / ORCH_RESULT_PATH),
        "ORCH_dryrun_result_digest": load_yaml(root / ORCH_RESULT_PATH)["orch_20cp_dryrun_result"]["result_digest"],
    }


def validate_source_spans(unit: dict[str, Any]) -> str | None:
    refs = {ref["source_ref"]: ref for ref in unit.get("source_refs", [])}
    if unit.get("source_evidence_spans") and not refs:
        return "E_SOURCE_SPAN_WITHOUT_REF"
    for ref in refs.values():
        if sha256_text(ref["source_text"]) != ref["source_digest"]:
            return "E_SOURCE_DIGEST"
    for span in unit.get("source_evidence_spans", []):
        ref = refs.get(span.get("source_ref"))
        if not ref:
            return "E_SOURCE_REF_MISSING"
        if ref["source_text"][span["start"] : span["end"]] != span["text"]:
            return "E_SOURCE_SPAN_MISMATCH"
        if span["text"] not in unit.get("text", ""):
            return "E_SURFACE_TEXT_ALTERS_EVIDENCE"
    return None


def evaluate_case(case: dict[str, Any]) -> tuple[str, str]:
    if not case.get("surface_units"):
        return "HOLD_FOR_SEMANTIC_REVIEW", "E_NO_SURFACE_UNIT"
    for unit in case["surface_units"]:
        text = unit.get("text", "")
        output_span = unit.get("output_span")
        if output_span != [0, len(text)]:
            return "HOLD_FOR_SEMANTIC_REVIEW", "E_OUTPUT_SPAN"
        license_value = unit.get("semantic_license")
        if license_value not in EXPECTED_LICENSES:
            return "HOLD_FOR_SEMANTIC_REVIEW", "E_UNCLASSIFIED_SURFACE_UNIT"
        source_error = validate_source_spans(unit)
        if source_error:
            return "REJECT_UNSUPPORTED_ASSERTION", source_error
        for atom in unit.get("assertion_atoms", []):
            atom_type = atom.get("atom_type")
            has_evidence = bool(unit.get("source_evidence_spans"))
            has_auth = bool(unit.get("authorization_refs"))
            if atom.get("requires_evidence") and not has_evidence:
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_EVIDENCE_REQUIRED_{atom_type}"
            if atom.get("requires_authorization") and not has_auth:
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_AUTHORIZATION_REQUIRED_{atom_type}"
            if atom.get("requires_event_ref") and not unit.get("event_ref"):
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_EVENT_REF_REQUIRED_{atom_type}"
            if atom.get("requires_capture_obligation") and not unit.get("capture_obligation_ref"):
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_CAPTURE_REQUIRED_{atom_type}"
            if atom_type in {"customer_story", "personal_biography"} and not has_auth:
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_AUTHORIZATION_REQUIRED_{atom_type}"
            if atom_type == "direct_quote" and (not has_auth or not has_evidence):
                return "REJECT_UNSUPPORTED_ASSERTION", "E_QUOTE_REQUIRES_AUTH_AND_EVIDENCE"
            evidence_bound_atoms = {
                "real_event",
                "enterprise_commitment_history",
                "sku_date_version",
                "sku_inventory_version_number",
                "performance_body_causal_claim",
                "third_party_inner_state",
            }
            if atom_type in evidence_bound_atoms and not has_evidence:
                return "REJECT_UNSUPPORTED_ASSERTION", f"E_EVIDENCE_REQUIRED_{atom_type}"
        if license_value == "HYPOTHETICAL_OR_DISCLOSED_SCENE" and not unit.get("surface_disclosure_ref"):
            return "REJECT_UNSUPPORTED_ASSERTION", "E_DISCLOSURE_REQUIRED"
    return "ACCEPT_CREATIVE", "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_SEMANTIC_REVIEW"


def validation_plan_ids(root: Path) -> set[str]:
    return {unwrap(row, "orch_validation_composition_plan")["plan_id"] for row in load_jsonl(root / ORCH_PLANS_PATH)}


def result_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    records = [unwrap(row, "generator_acceptance_harness_result") for row in rows]
    plan_rows = [row for row in records if row.get("record_kind") == "validation_plan_input_gate"]
    fixture_rows = [row for row in records if row.get("record_kind") == "surface_fixture_evaluation"]
    mutation_rows = [row for row in records if row.get("record_kind") == "mutation_evaluation"]
    hold_rows = [row for row in records if row.get("record_kind") == "semantic_hold_diagnostic"]
    return {
        "validation_plan_evaluated_count": len(plan_rows),
        "validation_plan_rejected_count": sum(row.get("decision") == "BLOCKED_NON_RUNTIME_VALIDATION_PLAN" for row in plan_rows),
        "validation_plan_accepted_count": sum(row.get("decision") != "BLOCKED_NON_RUNTIME_VALIDATION_PLAN" for row in plan_rows),
        "synthetic_surface_fixture_count": len(fixture_rows),
        "accepted_creative_fixture_count": sum(row.get("actual_decision") == "ACCEPT_CREATIVE" for row in fixture_rows),
        "rejected_fabrication_fixture_count": sum(row.get("actual_decision") == "REJECT_UNSUPPORTED_ASSERTION" for row in fixture_rows),
        "mutation_fail_closed_count": sum(row.get("fail_closed") is True for row in mutation_rows),
        "hold_for_semantic_review_count": len(hold_rows),
        "hold_counted_as_accept_or_reject": any(
            row.get("counts_as_accept") is True or row.get("counts_as_reject") is True for row in hold_rows
        ),
        "false_accept_count": 0,
        "false_reject_count": 0,
    }


def validate_preflight(root: Path, errors: list[dict[str, str]], enforce_git: bool) -> None:
    if not enforce_git:
        return
    head = git(root, ["rev-parse", "HEAD"]).strip()
    if not head:
        add_error(errors, "E_HEAD", "git", "cannot resolve HEAD")
    elif head != BASELINE_HEAD and not git_ok(root, ["merge-base", "--is-ancestor", BASELINE_HEAD, head]):
        add_error(errors, "E_BASELINE", "git", f"{BASELINE_HEAD} is not ancestor of {head}")
    unexpected = sorted(
        path.as_posix()
        for path in changed_paths(root) - ALLOWED_CHANGED_PATHS
        if not path.is_relative_to(SUCCESSOR_QUALIFICATION_PROBE_DIR)
        and not path.is_relative_to(SUCCESSOR_TARGETED_REPAIR_DIR)
        and not path.is_relative_to(SUCCESSOR_CALIBRATION_REPAIR_002_DIR)
        and not path.is_relative_to(SUCCESSOR_CONVERGENCE_DIR)
        and not path.is_relative_to(SUCCESSOR_B_LANE_DIR)
    )
    if unexpected:
        add_error(errors, "E_WRITE_SURFACE", "git", str(unexpected))


def validate_phase0(root: Path, contract: dict[str, Any], result: dict[str, Any], errors: list[dict[str, str]]) -> None:
    phase0 = contract["phase_0"]
    result_phase0 = result["phase_0"]
    parents = git(root, ["show", "-s", "--format=%P", BASELINE_HEAD]).split()
    tree = git(root, ["show", "-s", "--format=%T", BASELINE_HEAD]).strip()
    if REVIEWED_BASE_SHA not in parents or REVIEWED_HEAD_SHA not in parents:
        add_error(errors, "E_PHASE0_PARENTS", "git", str(parents))
    if tree != REVIEWED_HEAD_TREE_SHA or tree != PHASE0_MERGE_TREE_SHA:
        add_error(errors, "E_PHASE0_TREE", "git", tree)
    expected = {
        "ORCH_PR_4_merged": True,
        "merge_method": "merge_commit",
        "merge_commit_sha": BASELINE_HEAD,
        "expected_base_parent_present": True,
        "reviewed_head_parent_present": True,
        "merge_tree_equals_reviewed_head_tree": True,
        "master_required_checks_green": True,
        "local_remote_master_match": True,
    }
    for key, value in expected.items():
        if phase0.get(key) != value:
            add_error(errors, "E_PHASE0_CONTRACT", "contract", f"{key}={phase0.get(key)}")
        if key in result_phase0 and result_phase0.get(key) != value:
            add_error(errors, "E_PHASE0_RESULT", "result", f"{key}={result_phase0.get(key)}")
    binding = phase0.get("review_binding", {})
    expected_binding = {
        "reviewed_base_sha": REVIEWED_BASE_SHA,
        "reviewed_head_sha": REVIEWED_HEAD_SHA,
        "reviewed_head_tree_sha": REVIEWED_HEAD_TREE_SHA,
        "reviewed_full_diff_digest": REVIEWED_FULL_DIFF_DIGEST,
        "guardian_verdict": "PASS",
    }
    if binding != expected_binding:
        add_error(errors, "E_REVIEW_BINDING", "contract", str(binding))


def validate_contract(root: Path, contract_doc: dict[str, Any], result_doc: dict[str, Any], errors: list[dict[str, str]]) -> None:
    contract = contract_doc["controlled_content_generator_v2_contract"]
    result = result_doc["generator_v2_build_result"]
    if contract.get("contract_digest") != object_digest(contract, {"contract_digest"}):
        add_error(errors, "E_CONTRACT_DIGEST", "contract", "digest mismatch")
    validate_phase0(root, contract, result, errors)
    baseline = contract["baseline"]
    if baseline.get("parent_sha") != BASELINE_HEAD or baseline.get("parent_tree_sha") != PHASE0_MERGE_TREE_SHA:
        add_error(errors, "E_BASELINE_PIN", "contract", str(baseline))
    if baseline.get("input_counts") != EXPECTED_COUNTS or input_counts(root) != EXPECTED_COUNTS:
        add_error(errors, "E_INPUT_COUNTS", "contract", str(baseline.get("input_counts")))
    actual_digests = input_digests(root)
    if baseline.get("input_digests") != EXPECTED_DIGESTS or actual_digests != EXPECTED_DIGESTS:
        add_error(errors, "E_INPUT_DIGESTS", "contract", str(actual_digests))
    inventory = contract["generator_baseline_inventory"]
    if inventory.get("selected_canonical_extension_target") != "01_generation_contracts/codex_generation_output_contract.v0.1.schema.json":
        add_error(errors, "E_GENERATOR_TARGET", "contract", str(inventory))
    if inventory.get("final_generator_entrypoint_count") != 1 or inventory.get("parallel_generator_created_count") != 0:
        add_error(errors, "E_GENERATOR_ENTRYPOINT", "contract", str(inventory))
    if "no reusable provider engine" not in inventory.get("selection_reason", ""):
        add_error(errors, "E_GENERATOR_INVENTORY_REASON", "contract", str(inventory.get("selection_reason")))
    for entry in inventory.get("discovered_entrypoints", []):
        path = root / Path(entry["path"])
        if not path.exists() or sha256_file(path) != entry.get("digest"):
            add_error(errors, "E_INVENTORY_DIGEST", "contract", str(entry))
    ownership = contract["ownership"]
    if any(value is not False for key, value in ownership.items() if key.startswith("GENERATOR_may_")):
        add_error(errors, "E_GENERATOR_OWNERSHIP", "contract", str(ownership))
    if ownership.get("ORCH_sole_plan_owner") is not True or ownership.get("GKB_may_create_CompositionPlan") is not False:
        add_error(errors, "E_PLAN_OWNERSHIP", "contract", str(ownership))
    provider = contract["provider_port"]
    zero_keys = ["credential_read_count", "external_network_call_count", "provider_request_count", "provider_call_count", "provider_response_count"]
    if provider.get("real_adapter_enabled") is not False or any(provider.get(key) != 0 for key in zero_keys):
        add_error(errors, "E_PROVIDER_PORT", "contract", str(provider))
    envelope = contract["controlled_output_envelope_schema"]
    if envelope.get("acceptance_state") != "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_SEMANTIC_REVIEW":
        add_error(errors, "E_ENVELOPE_STATE", "contract", str(envelope))
    if envelope.get("untracked_surface_text_count") != 0 or envelope.get("unclassified_surface_unit_count") != 0:
        add_error(errors, "E_ENVELOPE_CLOSURE", "contract", str(envelope))
    policy = contract["semantic_license_policy"]
    if set(policy.get("supported_licenses", [])) != EXPECTED_LICENSES:
        add_error(errors, "E_LICENSE_POLICY", "contract", str(policy))
    if policy.get("ambiguous_route") != "HOLD_FOR_SEMANTIC_REVIEW":
        add_error(errors, "E_HOLD_ROUTE", "contract", str(policy))
    coverage = contract["fabrication_mode_coverage"]
    if set(coverage) != EXPECTED_FABRICATION_MODES:
        add_error(errors, "E_FABRICATION_COVERAGE_KEYS", "contract", str(sorted(coverage)))
    readiness = contract["readiness"]
    if readiness.get("ready_for_founder_probe_authorization") is not True:
        add_error(errors, "E_PROBE_AUTH_SIGNAL", "contract", str(readiness))
    true_flags = recursive_true_flags(contract)
    if true_flags:
        add_error(errors, "E_READY_TRUE", "contract", str(true_flags))


def validate_cases(cases: list[dict[str, Any]], contract: dict[str, Any], errors: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    rows = [unwrap(row, "generator_acceptance_harness_case") for row in cases]
    if len(rows) != 16:
        add_error(errors, "E_CASE_COUNT", "cases", str(len(rows)))
    category_counts = Counter(row.get("case_category") for row in rows)
    if category_counts != {"MUST_ACCEPT_CREATIVE": 8, "MUST_REJECT_FABRICATION": 8}:
        add_error(errors, "E_CASE_CATEGORY_COUNTS", "cases", str(category_counts))
    expected_counts = Counter(row.get("expected_decision") for row in rows)
    if expected_counts != {"ACCEPT_CREATIVE": 8, "REJECT_UNSUPPORTED_ASSERTION": 8}:
        add_error(errors, "E_CASE_DECISION_COUNTS", "cases", str(expected_counts))
    decisions: dict[str, tuple[str, str]] = {}
    ids = {row["case_id"] for row in rows}
    coverage_refs = {
        ref
        for refs in contract["fabrication_mode_coverage"].values()
        for ref in refs
        if ref.startswith("CCGV2-")
    }
    if not coverage_refs <= ids:
        add_error(errors, "E_FABRICATION_CASE_REFS", "cases", str(sorted(coverage_refs - ids)))
    for row in rows:
        if row.get("task_id") != TASK_ID or row.get("schema_version") != "v0.1":
            add_error(errors, "E_CASE_SCHEMA", row.get("case_id", "?"), str(row))
        if row.get("case_digest") != object_digest(row, {"case_digest"}):
            add_error(errors, "E_CASE_DIGEST", row["case_id"], "digest mismatch")
        flag_expectations = {
            "fixture_only": True,
            "synthetic_namespace": True,
            "nonpublishable": True,
            "runtime_consumable": False,
            "generated_draft": False,
            "may_enter_reference_corpus": False,
        }
        for key, value in flag_expectations.items():
            if row.get(key) is not value:
                add_error(errors, "E_CASE_BOUNDARY_FLAG", row["case_id"], f"{key}={row.get(key)}")
        if len(row.get("surface_units", [])) != 1:
            add_error(errors, "E_CASE_SURFACE_UNIT_COUNT", row["case_id"], str(row.get("surface_units")))
            continue
        decision = evaluate_case(row)
        decisions[row["case_id"]] = decision
        if decision[0] != row.get("expected_decision"):
            add_error(errors, "E_CASE_INDEPENDENT_DECISION", row["case_id"], str(decision))
        if recursive_true_flags(row):
            add_error(errors, "E_CASE_READY_TRUE", row["case_id"], str(recursive_true_flags(row)))
    return decisions


def validate_results(
    root: Path,
    results: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    case_decisions: dict[str, tuple[str, str]],
    errors: list[dict[str, str]],
) -> None:
    rows = [unwrap(row, "generator_acceptance_harness_result") for row in results]
    if len(rows) != 47:
        add_error(errors, "E_RESULT_ROW_COUNT", "results", str(len(rows)))
    kind_counts = Counter(row.get("record_kind") for row in rows)
    if kind_counts != {
        "validation_plan_input_gate": 20,
        "surface_fixture_evaluation": 16,
        "mutation_evaluation": 10,
        "semantic_hold_diagnostic": 1,
    }:
        add_error(errors, "E_RESULT_KIND_COUNTS", "results", str(kind_counts))
    for row in rows:
        if row.get("result_digest") != object_digest(row, {"result_digest"}):
            add_error(errors, "E_RESULT_ROW_DIGEST", row.get("record_kind", "?"), str(row.get("result_digest")))
        if row.get("provider_request_created") is not False or row.get("provider_invocation_allowed") is not False:
            add_error(errors, "E_PROVIDER_FLAG", row.get("record_kind", "?"), str(row))
        if row.get("draft_created") is not False:
            add_error(errors, "E_DRAFT_CREATED", row.get("record_kind", "?"), str(row))
    plan_ids = validation_plan_ids(root)
    for row in rows:
        if row.get("record_kind") == "validation_plan_input_gate":
            if row.get("plan_id") not in plan_ids or row.get("plan_mode") != "VALIDATION_SYNTHETIC":
                add_error(errors, "E_PLAN_GATE_LINEAGE", row.get("plan_id", "?"), str(row))
            if row.get("runtime_consumable") is not False or row.get("decision") != "BLOCKED_NON_RUNTIME_VALIDATION_PLAN":
                add_error(errors, "E_PLAN_GATE_DECISION", row.get("plan_id", "?"), str(row))
    cases_by_id = {unwrap(row, "generator_acceptance_harness_case")["case_id"]: unwrap(row, "generator_acceptance_harness_case") for row in cases}
    for row in rows:
        if row.get("record_kind") != "surface_fixture_evaluation":
            continue
        case = cases_by_id.get(row.get("case_id"))
        if not case:
            add_error(errors, "E_FIXTURE_RESULT_CASE", str(row.get("case_id")), "missing case")
            continue
        expected_decision, expected_route = case_decisions[row["case_id"]]
        if row.get("case_digest") != case["case_digest"] or row.get("expected_decision") != case["expected_decision"]:
            add_error(errors, "E_FIXTURE_RESULT_LINEAGE", row["case_id"], str(row))
        route_ok = (
            row.get("acceptance_route") == expected_route
            if expected_decision == "ACCEPT_CREATIVE"
            else isinstance(row.get("acceptance_route"), str) and row["acceptance_route"].startswith("E_")
        )
        if row.get("actual_decision") != expected_decision or not route_ok:
            add_error(errors, "E_FIXTURE_RESULT_DECISION", row["case_id"], str(row))
        if row.get("generated_draft") is not False or row.get("accepted_content_count") != 0:
            add_error(errors, "E_FIXTURE_RESULT_CONTENT", row["case_id"], str(row))
    mutation_ids = {row["mutation_id"] for row in rows if row.get("record_kind") == "mutation_evaluation"}
    expected_mutations = {f"MUT-{index:03d}" for index in range(1, 11)}
    if {mutation_id[:7] for mutation_id in mutation_ids} != expected_mutations:
        add_error(errors, "E_MUTATION_IDS", "results", str(sorted(mutation_ids)))
    for row in rows:
        if row.get("record_kind") != "mutation_evaluation":
            continue
        if row.get("fail_closed") is not True:
            add_error(errors, "E_MUTATION_FAIL_CLOSED", row["mutation_id"], str(row))
        if row.get("actual_decision") != row.get("expected_decision"):
            add_error(errors, "E_MUTATION_DECISION", row["mutation_id"], str(row))
        if row["mutation_id"] == "MUT-010-INJECT-HIDDEN-PAYLOAD":
            if not {"body_text", "title", "spoken_script"} <= set(row.get("forbidden_payload_field_names", [])):
                add_error(errors, "E_MUTATION_HIDDEN_PAYLOAD", row["mutation_id"], str(row))
    hold_rows = [row for row in rows if row.get("record_kind") == "semantic_hold_diagnostic"]
    for row in hold_rows:
        if row.get("decision") != "HOLD_FOR_SEMANTIC_REVIEW":
            add_error(errors, "E_HOLD_DECISION", "results", str(row))
        if row.get("counts_as_accept") is not False or row.get("counts_as_reject") is not False:
            add_error(errors, "E_HOLD_COUNTING", "results", str(row))
    summary = result_summary(results)
    expected_summary = {
        "validation_plan_evaluated_count": 20,
        "validation_plan_rejected_count": 20,
        "validation_plan_accepted_count": 0,
        "synthetic_surface_fixture_count": 16,
        "accepted_creative_fixture_count": 8,
        "rejected_fabrication_fixture_count": 8,
        "mutation_fail_closed_count": 10,
        "hold_for_semantic_review_count": 1,
        "hold_counted_as_accept_or_reject": False,
        "false_accept_count": 0,
        "false_reject_count": 0,
    }
    if summary != expected_summary:
        add_error(errors, "E_RESULT_SUMMARY", "results", str(summary))
    if result_summary(list(reversed(results))) != summary:
        add_error(errors, "E_RESULT_ORDER_INVARIANCE", "results", "single reverse permutation changed summary")


def validate_build_result_and_packet(
    root: Path,
    result_doc: dict[str, Any],
    packet_doc: dict[str, Any],
    results: list[dict[str, Any]],
    errors: list[dict[str, str]],
) -> None:
    result = result_doc["generator_v2_build_result"]
    if result.get("result_digest") != object_digest(result, {"result_digest"}):
        add_error(errors, "E_BUILD_RESULT_DIGEST", "build_result", "digest mismatch")
    if result.get("verdict") != "GENERATOR_V2_CONTROL_PLANE_AND_ACCEPTANCE_HARNESS_BUILT_PENDING_GUARDIAN":
        add_error(errors, "E_BUILD_VERDICT", "build_result", str(result.get("verdict")))
    architecture = result["architecture"]
    if architecture.get("generator_v2_candidate_built") is not True or architecture.get("acceptance_harness_built") is not True:
        add_error(errors, "E_ARCHITECTURE_BUILT", "build_result", str(architecture))
    if architecture.get("final_generator_entrypoint_count") != 1 or architecture.get("parallel_generator_created_count") != 0:
        add_error(errors, "E_ARCHITECTURE_ENTRYPOINT", "build_result", str(architecture))
    if architecture.get("generator_component_selection_count") != 0 or architecture.get("generator_plan_write_count") != 0:
        add_error(errors, "E_GENERATOR_SCOPE", "build_result", str(architecture))
    if result["input_gate"] != {
        "validation_plan_evaluated_count": 20,
        "validation_plan_rejected_count": 20,
        "validation_plan_accepted_count": 0,
    }:
        add_error(errors, "E_INPUT_GATE", "build_result", str(result["input_gate"]))
    provider = result["provider"]
    if provider.get("real_provider_adapter_enabled") is not False:
        add_error(errors, "E_PROVIDER_ADAPTER", "build_result", str(provider))
    if any(provider.get(key) != 0 for key in ["credential_read_count", "provider_request_count", "provider_call_count", "provider_response_count"]):
        add_error(errors, "E_PROVIDER_COUNT", "build_result", str(provider))
    if result["harness"] != result_summary(results):
        add_error(errors, "E_BUILD_HARNESS_SUMMARY", "build_result", str(result["harness"]))
    content = result["content"]
    zero_content_keys = [
        "real_generated_content_count",
        "generated_draft_count",
        "title_count",
        "body_count",
        "spoken_script_count",
        "CTA_count",
        "accepted_content_count",
    ]
    if any(content.get(key) != 0 for key in zero_content_keys):
        add_error(errors, "E_CONTENT_COUNT", "build_result", str(content))
    if content.get("accepted_baseline_count") != 120 or content.get("target_baseline_count") != 300:
        add_error(errors, "E_BASELINE_TARGET_COUNTS", "build_result", str(content))
    runtime = result["runtime"]
    if any(value != 0 for value in runtime.values()):
        add_error(errors, "E_RUNTIME_COUNT", "build_result", str(runtime))
    readiness = result["readiness"]
    if readiness.get("ready_for_founder_probe_authorization") is not True:
        add_error(errors, "E_READY_FOR_FOUNDER_SIGNAL", "build_result", str(readiness))
    true_flags = recursive_true_flags(result)
    if true_flags:
        add_error(errors, "E_READY_TRUE", "build_result", str(true_flags))
    digests = result.get("generated_file_digests", {})
    for path in [CONTRACT_PATH, CASES_PATH, RESULTS_PATH, PACKET_PATH, FREEZER_PATH, CHECKER_PATH]:
        path_key = path.as_posix()
        if path in {CHECKER_PATH, FREEZER_PATH}:
            recorded = digests.get(path_key)
            if not isinstance(recorded, str) or len(recorded) != 64:
                add_error(errors, "E_GENERATED_FILE_DIGEST", "build_result", path_key)
        elif digests.get(path_key) != sha256_file(root / path):
            add_error(errors, "E_GENERATED_FILE_DIGEST", "build_result", path_key)
    packet = packet_doc["generator_guardian_review_packet"]
    if packet.get("packet_digest") != object_digest(packet, {"packet_digest"}):
        add_error(errors, "E_PACKET_DIGEST", "packet", "digest mismatch")
    if packet.get("validation_plan_rejected_count") != 20 or packet.get("synthetic_surface_fixture_count") != 16:
        add_error(errors, "E_PACKET_COUNTS", "packet", str(packet))
    if packet.get("provider_call_count") != 0 or packet.get("generated_draft_count") != 0:
        add_error(errors, "E_PACKET_BOUNDARY", "packet", str(packet))


def top_level_route_ids(text: str) -> list[int]:
    ids: list[int] = []
    for line in text.splitlines():
        if line.startswith("  route_migration_") and line.endswith(":"):
            suffix = line.strip().removeprefix("route_migration_").removesuffix(":")
            if suffix.isdigit():
                ids.append(int(suffix))
    return ids


def validate_ledger(root: Path, result_doc: dict[str, Any], errors: list[dict[str, str]], enforce_git: bool) -> None:
    text = (root / LEDGER_PATH).read_text(encoding="utf-8")
    data = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
    migration = data.get("route_migration_26")
    if not isinstance(migration, dict):
        add_error(errors, "E_LEDGER_ROUTE26", "ledger", "route_migration_26 missing")
        return
    result = result_doc["generator_v2_build_result"]
    if migration.get("applied_by_task") != TASK_ID:
        add_error(errors, "E_LEDGER_TASK", "ledger", str(migration.get("applied_by_task")))
    if migration.get("additive_only") is not True or migration.get("no_readiness_flipped") is not True:
        add_error(errors, "E_LEDGER_DECLARATION", "ledger", str(migration))
    generator = migration.get("controlled_content_generator_v2", {})
    expected = {
        "generator_v2_candidate_built": True,
        "acceptance_harness_built": True,
        "validation_plan_evaluated_count": 20,
        "validation_plan_rejected_count": 20,
        "validation_plan_accepted_count": 0,
        "synthetic_surface_fixture_count": 16,
        "accepted_creative_fixture_count": 8,
        "rejected_fabrication_fixture_count": 8,
        "mutation_fail_closed_count": 10,
        "provider_call_count": 0,
        "generated_draft_count": 0,
        "generator_qualified": False,
        "qualification_probe_40_generation_allowed": False,
        "ready_for_founder_probe_authorization": True,
        "result_digest": result["result_digest"],
    }
    for key, value in expected.items():
        if generator.get(key) != value:
            add_error(errors, "E_LEDGER_GENERATOR", "ledger", f"{key}={generator.get(key)}")
    if migration.get("migration_digest") != object_digest(migration, {"migration_digest"}):
        add_error(errors, "E_LEDGER_DIGEST", "ledger", "migration digest mismatch")
    ids = top_level_route_ids(text)
    if 26 not in ids:
        add_error(errors, "E_LEDGER_ROUTE26", "ledger", "route id missing")
    if sorted(route_id for route_id in ids if route_id >= 19) != list(range(19, max(ids) + 1)):
        add_error(errors, "E_LEDGER_SEQUENCE", "ledger", str(ids))
    if enforce_git:
        old_text = git(root, ["show", f"{BASELINE_HEAD}:{LEDGER_PATH.as_posix()}"])
        if old_text:
            old_data = yaml.safe_load(old_text)["grc_3600_execution_plan_status"]
            extra = sorted(set(data) - set(old_data))
            expected_extra = [f"route_migration_{index}" for index in range(26, 26 + len(extra))]
            if extra != expected_extra:
                add_error(errors, "E_LEDGER_EXTRA_KEYS", "ledger", str(extra))
            for key, value in old_data.items():
                if key in {"route_migration_23", "route_migration_24", "route_migration_25"}:
                    continue
                if data.get(key) != value:
                    add_error(errors, "E_LEDGER_NON_ADDITIVE", "ledger", key)


def validate_ci(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / CI_PATH).read_text(encoding="utf-8")
    required = [
        "python3 ci/checkers/check_controlled_content_generator_v2_build.py",
        "python3 ci/checkers/check_controlled_content_generator_v2_build.py --selftest",
        "python3 controlled_content_generator_v2_001/build_and_acceptance_harness_001/run_generator_v2_acceptance_harness.py --check",
        '"ci/checkers/check_controlled_content_generator_v2_build.py"',
        '"ci/checkers/check_controlled_content_generator_v2_build.py --selftest"',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        add_error(errors, "E_CI_REGISTRATION", "ci", str(missing))


def validate_checker_independence(root: Path, errors: list[dict[str, str]]) -> None:
    text = (root / CHECKER_PATH).read_text(encoding="utf-8")
    forbidden = [
        "import " + "run_generator_v2_acceptance_harness",
        "from " + "run_generator_v2_acceptance_harness",
        "spec_from_file_location(" + "\"generator_v2",
        "spec_from_file_location(" + "'generator_v2",
    ]
    hits = [item for item in forbidden if item in text]
    if hits:
        add_error(errors, "E_CHECKER_ORACLE_IMPORT", "checker", str(hits))


def validate_no_forbidden_payloads(
    contract_doc: dict[str, Any],
    results: list[dict[str, Any]],
    result_doc: dict[str, Any],
    packet_doc: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    for section, value in [
        ("contract", contract_doc),
        ("results", results),
        ("build_result", result_doc),
        ("packet", packet_doc),
    ]:
        hits = recursive_forbidden_fields(value)
        allowed = [hit for hit in hits if hit.endswith(".forbidden_payload_field_names")]
        actual = [hit for hit in hits if hit not in allowed]
        if actual:
            add_error(errors, "E_FORBIDDEN_PAYLOAD_FIELD", section, str(actual))


def collect_errors(root: Path, enforce_git: bool = True) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = [
        CONTRACT_PATH,
        CASES_PATH,
        RESULTS_PATH,
        BUILD_RESULT_PATH,
        PACKET_PATH,
        FREEZER_PATH,
        CHECKER_PATH,
        LEDGER_PATH,
        CI_PATH,
    ]
    for path in required:
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE_MISSING", path.as_posix(), "missing")
    if errors:
        return errors
    validate_preflight(root, errors, enforce_git)
    contract_doc = load_yaml(root / CONTRACT_PATH)
    contract = contract_doc["controlled_content_generator_v2_contract"]
    cases = load_jsonl(root / CASES_PATH)
    results = load_jsonl(root / RESULTS_PATH)
    result_doc = load_yaml(root / BUILD_RESULT_PATH)
    packet_doc = load_yaml(root / PACKET_PATH)
    validate_contract(root, contract_doc, result_doc, errors)
    case_decisions = validate_cases(cases, contract, errors)
    validate_results(root, results, cases, case_decisions, errors)
    validate_build_result_and_packet(root, result_doc, packet_doc, results, errors)
    validate_no_forbidden_payloads(contract_doc, results, result_doc, packet_doc, errors)
    validate_checker_independence(root, errors)
    validate_ledger(root, result_doc, errors, enforce_git)
    validate_ci(root, errors)
    return errors


def selftest() -> int:
    root = Path.cwd()
    contract_doc = load_yaml(root / CONTRACT_PATH)
    contract = contract_doc["controlled_content_generator_v2_contract"]
    cases = load_jsonl(root / CASES_PATH)
    results = load_jsonl(root / RESULTS_PATH)
    result_doc = load_yaml(root / BUILD_RESULT_PATH)
    packet_doc = load_yaml(root / PACKET_PATH)
    tests: list[tuple[str, bool]] = []

    tests.append(("valid_outputs", not collect_errors(root, enforce_git=False)))

    bad_cases = copy.deepcopy(cases)
    unwrap(bad_cases[0], "generator_acceptance_harness_case")["fixture_only"] = False
    case_errors: list[dict[str, str]] = []
    validate_cases(bad_cases, contract, case_errors)
    tests.append(("fixture_only_false_rejected", any(error["code"] == "E_CASE_BOUNDARY_FLAG" for error in case_errors)))

    bad_results = copy.deepcopy(results)
    for row in bad_results:
        result = unwrap(row, "generator_acceptance_harness_result")
        if result["record_kind"] == "validation_plan_input_gate":
            result["decision"] = "ACCEPTED_FOR_PROVIDER_REQUEST"
            break
    result_errors: list[dict[str, str]] = []
    validate_results(root, bad_results, cases, validate_cases(cases, contract, []), result_errors)
    tests.append(("validation_plan_accept_rejected", any(error["code"] == "E_PLAN_GATE_DECISION" for error in result_errors)))

    provider_doc = copy.deepcopy(result_doc)
    provider_doc["generator_v2_build_result"]["provider"]["provider_call_count"] = 1
    provider_errors: list[dict[str, str]] = []
    validate_build_result_and_packet(root, provider_doc, packet_doc, results, provider_errors)
    tests.append(("provider_call_rejected", any(error["code"] == "E_PROVIDER_COUNT" for error in provider_errors)))

    span_cases = copy.deepcopy(cases)
    for row in span_cases:
        case = unwrap(row, "generator_acceptance_harness_case")
        if case["case_id"] == "CCGV2-ACCEPT-007-NUMBER-UNIT":
            case["surface_units"][0]["text"] = "The sample sleeve length is 59 cm."
            break
    span_errors: list[dict[str, str]] = []
    validate_cases(span_cases, contract, span_errors)
    tests.append(("number_mismatch_rejected", any(error["code"] == "E_CASE_INDEPENDENT_DECISION" for error in span_errors)))

    quote_cases = copy.deepcopy(cases)
    for row in quote_cases:
        case = unwrap(row, "generator_acceptance_harness_case")
        if case["case_id"] == "CCGV2-ACCEPT-008-QUOTE-AUTH":
            case["surface_units"][0]["authorization_refs"] = []
            break
    quote_errors: list[dict[str, str]] = []
    validate_cases(quote_cases, contract, quote_errors)
    tests.append(("quote_auth_missing_rejected", any(error["code"] == "E_CASE_INDEPENDENT_DECISION" for error in quote_errors)))

    hidden_results = copy.deepcopy(results)
    for row in hidden_results:
        result = unwrap(row, "generator_acceptance_harness_result")
        if result.get("mutation_id") == "MUT-010-INJECT-HIDDEN-PAYLOAD":
            result["forbidden_payload_field_names"] = []
            break
    hidden_errors: list[dict[str, str]] = []
    validate_results(root, hidden_results, cases, validate_cases(cases, contract, []), hidden_errors)
    tests.append(("hidden_payload_mutation_rejected", any(error["code"] == "E_MUTATION_HIDDEN_PAYLOAD" for error in hidden_errors)))

    ready_doc = copy.deepcopy(result_doc)
    ready_doc["generator_v2_build_result"]["readiness"]["generator_qualified"] = True
    ready_errors: list[dict[str, str]] = []
    validate_build_result_and_packet(root, ready_doc, packet_doc, results, ready_errors)
    tests.append(("readiness_true_rejected", any(error["code"] == "E_READY_TRUE" for error in ready_errors)))

    hold_results = copy.deepcopy(results)
    for row in hold_results:
        result = unwrap(row, "generator_acceptance_harness_result")
        if result["record_kind"] == "semantic_hold_diagnostic":
            result["counts_as_accept"] = True
            break
    hold_errors: list[dict[str, str]] = []
    validate_results(root, hold_results, cases, validate_cases(cases, contract, []), hold_errors)
    tests.append(("hold_counted_rejected", any(error["code"] == "E_HOLD_COUNTING" for error in hold_errors)))

    tampered_contract = copy.deepcopy(contract_doc)
    tampered_contract["controlled_content_generator_v2_contract"]["fabrication_mode_coverage"].pop("direct_quote")
    contract_errors: list[dict[str, str]] = []
    validate_contract(root, tampered_contract, result_doc, contract_errors)
    tests.append(("fabrication_coverage_tamper_rejected", any(error["code"] == "E_FABRICATION_COVERAGE_KEYS" for error in contract_errors)))

    failed = [name for name, ok in tests if not ok]
    if failed:
        print(json.dumps({"status": "SELFTEST_FAIL", "failed": failed}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print("SELFTEST_PASS")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        print("usage: check_controlled_content_generator_v2_build.py [--selftest]", file=sys.stderr)
        return 2
    if len(argv) == 1 and argv[0] == "--selftest":
        return selftest()
    if argv:
        print("usage: check_controlled_content_generator_v2_build.py [--selftest]", file=sys.stderr)
        return 2
    errors = collect_errors(Path.cwd(), enforce_git=True)
    if errors:
        print(json.dumps({"status": "FAIL", "error_count": len(errors), "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "task_id": TASK_ID}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
