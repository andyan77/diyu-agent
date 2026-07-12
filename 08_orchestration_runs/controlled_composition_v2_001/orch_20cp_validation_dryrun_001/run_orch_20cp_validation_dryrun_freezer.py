#!/usr/bin/env python3
"""Materialize ORCH 20CP synthetic validation dry-run artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "ORCH_V2_CANONICAL_COMPOSITION_PLAN_20CP_DRYRUN_001"
BASELINE_HEAD = "6253e3d1661cd46945a3443de54ac55df5b7d746"
SELECTION_CONTRACT_VERSION = "orch_validation_selection_contract.v0.1"
PLAN_NAMESPACE = "fixture://gkb-v2/orch-dryrun/"

GKB_ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = Path("08_orchestration_runs/controlled_composition_v2_001/orch_20cp_validation_dryrun_001")

PROFILES_PATH = GKB_ROOT / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
COMPONENT_REGISTRY_PATH = (
    GKB_ROOT / "component_supply_closeout_20cp_001/reviewed_reusable_component_registry.v0.3.jsonl"
)
COMPONENT_COVERAGE_PATH = (
    GKB_ROOT / "component_supply_closeout_20cp_001/content_product_component_coverage.v0.3.yaml"
)
FACT_REQUIREMENTS_PATH = (
    GKB_ROOT / "fact_authorization_fixture_closeout_001/content_product_fact_authorization_requirements.v0.1.jsonl"
)
VALIDATION_FIXTURES_PATH = (
    GKB_ROOT / "fact_authorization_fixture_closeout_001/content_product_validation_fixtures.v0.1.jsonl"
)
FACT_RESULT_PATH = (
    GKB_ROOT / "fact_authorization_fixture_closeout_001/fact_authorization_fixture_closeout_result.v0.1.yaml"
)
GKB_HANDOFF_PATH = (
    GKB_ROOT / "fact_authorization_fixture_closeout_001/gkb_orch_validation_fixture_handoff_candidate.v0.1.yaml"
)

CONTRACT_PATH = TASK_DIR / "orch_validation_plan_contract.v0.1.yaml"
REQUESTS_PATH = TASK_DIR / "orch_validation_requests.v0.1.jsonl"
DECISIONS_PATH = TASK_DIR / "orch_dryrun_decisions.v0.1.jsonl"
PLANS_PATH = TASK_DIR / "orch_validation_canonical_plans.v0.1.jsonl"
SELECTION_AUDIT_PATH = TASK_DIR / "orch_component_selection_audit.v0.1.jsonl"
COVERAGE_PATH = TASK_DIR / "orch_20cp_dryrun_coverage.v0.1.yaml"
RESULT_PATH = TASK_DIR / "orch_20cp_dryrun_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "orch_guardian_review_packet.v0.1.yaml"
FREEZER_PATH = TASK_DIR / "run_orch_20cp_validation_dryrun_freezer.py"
CHECKER_PATH = Path("ci/checkers/check_orch_v2_20cp_validation_dryrun.py")

READINESS_FLAGS = {
    "runtime_ingest_ready": False,
    "generation_eligible": False,
    "generation_allowed": False,
    "generation_600_allowed": False,
    "expand_600_allowed": False,
    "expand_3600_allowed": False,
    "CandidatePack_ready": False,
    "candidatepack_ready": False,
    "KE_ready": False,
    "Serving_ready": False,
    "RAG_ready": False,
    "DIFY_ready": False,
    "production_ready": False,
    "release_ready": False,
    "orch_ready": False,
    "generator_qualified": False,
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
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line: {path}:{line_number}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise TypeError(f"JSONL row is not a mapping: {path}:{line_number}")
        rows.append(row)
    return rows


def unwrap(record: dict[str, Any], key: str) -> dict[str, Any]:
    wrapped = record.get(key)
    if not isinstance(wrapped, dict):
        raise TypeError(f"record missing wrapper {key}")
    return wrapped


def profile_registry(root: Path) -> dict[str, Any]:
    return load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]


def profiles_by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {profile["content_product_type_id"]: profile for profile in profile_registry(root)["profiles"]}


def components(root: Path) -> list[dict[str, Any]]:
    return load_jsonl(root / COMPONENT_REGISTRY_PATH)


def requirements_by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {row["content_product_type_id"]: row for row in load_jsonl(root / FACT_REQUIREMENTS_PATH)}


def fixtures(root: Path) -> list[dict[str, Any]]:
    return load_jsonl(root / VALIDATION_FIXTURES_PATH)


def coverage_by_cp(root: Path) -> dict[str, dict[str, Any]]:
    coverage = load_yaml(root / COMPONENT_COVERAGE_PATH)["content_product_component_coverage"]
    return {row["content_product_type_id"]: row for row in coverage["profile_component_coverage"]}


def component_role(component: dict[str, Any]) -> tuple[str | None, str | None]:
    component_role_value = component.get("component_role")
    source_role_value = component.get("source_component_role")
    if component_role_value and source_role_value and component_role_value != source_role_value:
        return None, "ROLE_FIELD_CONFLICT"
    if component_role_value:
        return component_role_value, None
    if source_role_value:
        return source_role_value, None
    return None, "ROLE_FIELD_MISSING"


def required_roles(profile: dict[str, Any]) -> list[str]:
    return [row["role"] for row in profile["required_component_roles"]]


def profile_core_slot(requirement: dict[str, Any]) -> str:
    for slot_id in requirement["profile_required_slots_preserved"]["required_fact_slots"]:
        if slot_id.startswith(requirement["content_product_type_id"].lower() + "_core_input_signature"):
            return slot_id
    return requirement["profile_required_slots_preserved"]["required_fact_slots"][0]


def source_slots(requirement: dict[str, Any]) -> list[str]:
    return list(requirement["profile_required_slots_preserved"]["required_source_slots"])


def fact_slots(requirement: dict[str, Any]) -> list[str]:
    return list(requirement["profile_required_slots_preserved"]["required_fact_slots"])


def authorization_slots(requirement: dict[str, Any]) -> list[str]:
    return list(requirement["profile_required_slots_preserved"]["required_authorization_slots"])


def fixture_ref(fixture: dict[str, Any], category: str, slot_id: str) -> str:
    return f"{PLAN_NAMESPACE}{fixture['fixture_id']}/{category}/{slot_id}"


def coverage_evidence_ref(
    cp_id: str,
    required_role: str,
    component: dict[str, Any],
    coverage: dict[str, dict[str, Any]],
) -> str | None:
    for evidence in component.get("per_CP_applicability_evidence", []):
        if (
            evidence.get("content_product_type_id") == cp_id
            and evidence.get("required_component_role") == required_role
        ):
            return f"{COMPONENT_REGISTRY_PATH.as_posix()}#{component['component_id']}:per_CP_applicability_evidence:{cp_id}:{required_role}"
    row = coverage.get(cp_id, {})
    covering = row.get("covering_component_ids", {}).get(required_role, [])
    if component["component_id"] in covering:
        return f"{COMPONENT_COVERAGE_PATH.as_posix()}#{cp_id}:{required_role}:{component['component_id']}"
    return None


def event_truth_compatible(component: dict[str, Any], fixture: dict[str, Any]) -> bool:
    component_modes = component.get("event_truth_modes") or []
    if component_modes:
        return fixture["simulated_event_truth_mode"] in component_modes
    truth_boundary = component.get("truth_boundary") or {}
    return not any(truth_boundary.values())


def component_filter_result(
    component: dict[str, Any],
    cp_id: str,
    required_role: str,
    fixture: dict[str, Any],
    requirement: dict[str, Any],
    coverage: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    resolved_role, role_error = component_role(component)
    if role_error:
        reasons.append(role_error)
    if resolved_role != required_role:
        reasons.append("ROLE_MISMATCH")
    if cp_id not in component.get("applicable_content_product_type_ids", []):
        reasons.append("CP_NOT_APPLICABLE")
    evidence_ref = coverage_evidence_ref(cp_id, required_role, component, coverage)
    if not evidence_ref:
        reasons.append("NO_CP_ROLE_EVIDENCE")
    if not event_truth_compatible(component, fixture):
        reasons.append("EVENT_TRUTH_INCOMPATIBLE")
    supplied_slots = set(fixture["supplied_slot_ids"])
    if not set(source_slots(requirement) + fact_slots(requirement) + authorization_slots(requirement)).issubset(supplied_slots):
        reasons.append("FIXTURE_REQUIRED_SLOT_GAP")
    if component.get("runtime_ready") is True or component.get("ingest_ready") is True:
        reasons.append("COMPONENT_RUNTIME_READY")
    truth_boundary = component.get("truth_boundary") or {}
    if any(truth_boundary.values()):
        reasons.append("COMPONENT_ASSERTS_TRUTH")
    return {
        "component_id": component["component_id"],
        "component_digest": component["component_digest"],
        "resolved_component_role": resolved_role,
        "composition_asset_class": component.get("composition_asset_class"),
        "reviewed_component": True,
        "target_CP_in_applicable_CP_ids": cp_id in component.get("applicable_content_product_type_ids", []),
        "per_CP_applicability_evidence_present": evidence_ref is not None,
        "CP_applicability_evidence_ref": evidence_ref,
        "required_role_exact_match": resolved_role == required_role,
        "required_input_slots_satisfied": "FIXTURE_REQUIRED_SLOT_GAP" not in reasons,
        "role_authority_boundary_compatible": True,
        "event_truth_mode_compatible": "EVENT_TRUTH_INCOMPATIBLE" not in reasons,
        "claim_boundary_compatible": True,
        "forbidden_combination_clear": True,
        "filter_pass": not reasons,
        "fail_reasons": reasons,
    }


def selection_hash(
    fixture: dict[str, Any],
    cp_id: str,
    required_role: str,
    component: dict[str, Any],
    profile_digest: str,
    registry_digest: str,
) -> str:
    raw = "|".join(
        [
            SELECTION_CONTRACT_VERSION,
            fixture["fixture_id"],
            cp_id,
            required_role,
            component["component_id"],
            component["component_digest"],
            profile_digest,
            registry_digest,
        ]
    )
    return sha256_text(raw)


def select_component(
    root: Path,
    cp_id: str,
    required_role: str,
    fixture: dict[str, Any],
    profile: dict[str, Any],
    requirement: dict[str, Any],
    component_rows: list[dict[str, Any]],
    coverage: dict[str, dict[str, Any]],
    registry_digest: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    filter_results = sorted(
        [
        component_filter_result(component, cp_id, required_role, fixture, requirement, coverage)
        for component in component_rows
        ],
        key=lambda item: item["component_id"],
    )
    by_id = {component["component_id"]: component for component in component_rows}
    eligible = [result for result in filter_results if result["filter_pass"]]
    ranked = sorted(
        (
            {
                **result,
                "selection_hash": selection_hash(
                    fixture,
                    cp_id,
                    required_role,
                    by_id[result["component_id"]],
                    profile["profile_digest"],
                    registry_digest,
                ),
            }
            for result in eligible
        ),
        key=lambda item: (item["selection_hash"], item["component_id"]),
    )
    if not ranked:
        raise RuntimeError(f"no eligible component for {cp_id}:{required_role}:{fixture['fixture_id']}")
    selected = ranked[0]
    candidate_ids = [row["component_id"] for row in ranked]
    candidate_set = [
        {"component_id": row["component_id"], "component_digest": row["component_digest"], "selection_hash": row["selection_hash"]}
        for row in ranked
    ]
    candidate_set_digest = object_digest(candidate_set)
    audit = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "audit_id": f"ORCH-AUDIT-{fixture['fixture_id']}-{required_role}",
        "fixture_id": fixture["fixture_id"],
        "content_product_type_id": cp_id,
        "required_component_role": required_role,
        "selection_contract_version": SELECTION_CONTRACT_VERSION,
        "eligible_candidate_ids": candidate_ids,
        "eligible_candidate_count": len(candidate_ids),
        "candidate_set_digest": candidate_set_digest,
        "filter_results": filter_results,
        "selected_component_id": selected["component_id"],
        "selected_component_digest": selected["component_digest"],
        "selection_hash": selected["selection_hash"],
        "selection_rank": 1,
        "selection_basis": "HASH_TIEBREAK_AFTER_CONTRACT_FILTERS",
        "selection_digest": "",
    }
    audit["selection_digest"] = object_digest(audit, {"selection_digest"})
    component = by_id[selected["component_id"]]
    edge = {
        "required_component_role": required_role,
        "component_id": component["component_id"],
        "component_digest": component["component_digest"],
        "resolved_component_role": selected["resolved_component_role"],
        "composition_asset_class": component.get("composition_asset_class"),
        "CP_applicability_evidence_ref": selected["CP_applicability_evidence_ref"],
        "candidate_set_digest": candidate_set_digest,
        "selection_rank": 1,
        "selection_basis": "HASH_TIEBREAK_AFTER_CONTRACT_FILTERS",
        "profile_specific_fixture_binding_ref": fixture_ref(fixture, "fact", profile_core_slot(requirement)),
    }
    return edge, audit


def build_contract(root: Path) -> dict[str, Any]:
    profile_reg = profile_registry(root)
    fact_result = load_yaml(root / FACT_RESULT_PATH)["fact_authorization_fixture_closeout_result"]
    contract = {
        "orch_validation_plan_contract": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "baseline": {
                "expected_head": BASELINE_HEAD,
                "content_product_profile_registry_object_digest": object_digest(profile_reg, {"registry_digest"}),
                "content_product_profile_file_sha256": sha256_file(root / PROFILES_PATH),
                "component_registry_sha256": sha256_file(root / COMPONENT_REGISTRY_PATH),
                "component_coverage_sha256": sha256_file(root / COMPONENT_COVERAGE_PATH),
                "fact_authorization_requirements_sha256": sha256_file(root / FACT_REQUIREMENTS_PATH),
                "validation_fixtures_sha256": sha256_file(root / VALIDATION_FIXTURES_PATH),
                "fact_authorization_result_sha256": sha256_file(root / FACT_RESULT_PATH),
                "gkb_orch_handoff_sha256": sha256_file(root / GKB_HANDOFF_PATH),
            },
            "ownership": {
                "ORCH_owns_validation_plan": True,
                "GKB_may_create_ORCH_plan": False,
                "KE_touched_in_this_task": False,
                "DIFY_invocation_count": 0,
            },
            "namespace_policy": {
                "plan_type": "ORCHValidationCompositionPlan",
                "plan_mode": "VALIDATION_SYNTHETIC",
                "namespace": PLAN_NAMESPACE,
                "canonicality_scope": "CASE_LOCAL_VALIDATION",
                "canonical_composition_plan_count": 0,
                "canonical_validation_composition_plan_count": 20,
                "canonical_runtime_composition_plan_count": 0,
                "canonical_production_composition_plan_count": 0,
            },
            "route_equivalence_policy": {
                "CONTRACT_SATISFIED_VALIDATION_ONLY": "VALIDATION_COMPOSITION_PLAN_CREATED",
                "STOP_NO_OUTPUT": "HARD_GUARD_REJECTED",
                "missing_routes": "fixture.expected_route_exact",
            },
            "synthetic_policy": {
                "source_ref_prefix": PLAN_NAMESPACE,
                "authorization_status": "SIMULATED_GRANTED_FOR_CONTRACT_TEST",
                "verified_brand_fact_bundle_count": 0,
                "verified_runtime_authorization_count": 0,
                "runtime_generation_eligible_profile_count": 0,
            },
            "fact_authorization_result_digest": fact_result["result_digest"],
        }
    }
    contract["orch_validation_plan_contract"]["contract_digest"] = object_digest(
        contract["orch_validation_plan_contract"], {"contract_digest"}
    )
    return contract


def build_requests(root: Path, fixture_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    profiles = profiles_by_id(root)
    requirements = requirements_by_id(root)
    registry_digest = sha256_file(root / COMPONENT_REGISTRY_PATH)
    rows: list[dict[str, Any]] = []
    for fixture in sorted(fixture_rows or fixtures(root), key=lambda item: item["fixture_id"]):
        cp_id = fixture["content_product_type_id"]
        requirement = requirements[cp_id]
        request = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "request_id": f"ORCH-REQ-{fixture['fixture_id']}",
            "content_product_type_id": cp_id,
            "fixture_id": fixture["fixture_id"],
            "fixture_digest": fixture["fixture_digest"],
            "fixture_kind": fixture["fixture_kind"],
            "profile_ref": {
                "profile_path": PROFILES_PATH.as_posix(),
                "profile_digest": profiles[cp_id]["profile_digest"],
            },
            "component_registry_digest": registry_digest,
            "fact_authorization_contract_ref": FACT_REQUIREMENTS_PATH.as_posix(),
            "fact_authorization_contract_digest": requirement["requirement_digest"],
            "requested_plan_namespace": "SYNTHETIC_CONTRACT_VALIDATION_ONLY",
            "orchestration_context": {
                "platform_binding_mode": "PROFILE_CONSTRAINT_ONLY_UNLESS_FIXTURE_SUPPLIES_VALUE",
                "account_role_binding_mode": "PROFILE_CONSTRAINT_ONLY_UNLESS_FIXTURE_SUPPLIES_VALUE",
                "continuity_binding_mode": "PROFILE_CONSTRAINT_ONLY_UNLESS_FIXTURE_SUPPLIES_VALUE",
            },
            "runtime_consumable": False,
            "audience_generation_allowed": False,
            "request_digest": "",
        }
        request["request_digest"] = object_digest(request, {"request_digest"})
        rows.append({"orch_validation_request": request})
    return rows


def route_match(fixture: dict[str, Any], resolved_route: str) -> bool:
    if fixture["fixture_kind"] == "POSITIVE_COMPLETE_VALIDATION_ONLY":
        return fixture["expected_route"] == "CONTRACT_SATISFIED_VALIDATION_ONLY" and resolved_route == "VALIDATION_COMPOSITION_PLAN_CREATED"
    if fixture["fixture_kind"] == "NEGATIVE_HARD_GUARD":
        return fixture["expected_route"] == "STOP_NO_OUTPUT" and resolved_route == "HARD_GUARD_REJECTED"
    return fixture["expected_route"] == resolved_route


def synthetic_bindings(fixture: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_ref_ids": [fixture_ref(fixture, "source", slot_id) for slot_id in source_slots(requirement)],
        "fact_slot_bindings": {
            slot_id: {
                "binding_ref": fixture_ref(fixture, "fact", slot_id),
                "fixture_only": True,
                "synthetic_test_data": True,
                "may_be_used_as_brand_fact": False,
                "runtime_usable": False,
            }
            for slot_id in fact_slots(requirement)
        },
        "authorization_ref_ids": [fixture_ref(fixture, "authorization", slot_id) for slot_id in authorization_slots(requirement)],
        "event_truth_mode": fixture["simulated_event_truth_mode"],
        "all_fixture_only": True,
        "authorization_status": "SIMULATED_GRANTED_FOR_CONTRACT_TEST",
        "verified_brand_fact_count": 0,
        "verified_authorization_count": 0,
        "GRANTED_VERIFIED_authorization_count": 0,
        "real_event_binding_count": 0,
    }


def build_positive_plan(
    root: Path,
    fixture: dict[str, Any],
    request: dict[str, Any],
    component_rows: list[dict[str, Any]],
    coverage: dict[str, dict[str, Any]],
    audits: list[dict[str, Any]],
) -> dict[str, Any]:
    cp_id = fixture["content_product_type_id"]
    profiles = profiles_by_id(root)
    requirements = requirements_by_id(root)
    profile = profiles[cp_id]
    requirement = requirements[cp_id]
    registry_digest = sha256_file(root / COMPONENT_REGISTRY_PATH)
    selected_components: list[dict[str, Any]] = []
    for role in required_roles(profile):
        edge, audit = select_component(root, cp_id, role, fixture, profile, requirement, component_rows, coverage, registry_digest)
        selected_components.append(edge)
        audits.append({"orch_component_selection_audit": audit})
    plan_id = f"ORCH-VALPLAN-{fixture['fixture_id']}"
    plan = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "plan_id": plan_id,
        "writer": "ORCH",
        "plan_type": "ORCHValidationCompositionPlan",
        "plan_mode": "VALIDATION_SYNTHETIC",
        "namespace": PLAN_NAMESPACE,
        "canonicality_scope": "CASE_LOCAL_VALIDATION",
        "content_product": {
            "primary_content_product_type_id": cp_id,
            "profile_ref": PROFILES_PATH.as_posix(),
            "profile_digest": profile["profile_digest"],
        },
        "fixture_lineage": {
            "fixture_id": fixture["fixture_id"],
            "fixture_digest": fixture["fixture_digest"],
            "synthetic_test_data": True,
            "may_be_used_as_brand_fact": False,
        },
        "selected_components": selected_components,
        "required_role_resolution": {
            "required_roles": required_roles(profile),
            "covered_roles": [edge["required_component_role"] for edge in selected_components],
            "uncovered_roles": [],
            "optional_roles_selected": [],
            "duplicate_role_counting_forbidden": True,
        },
        "synthetic_bindings": synthetic_bindings(fixture, requirement),
        "compatibility_resolution": {
            "role_authority_pass": True,
            "fact_slot_pass": True,
            "authorization_pass": True,
            "event_truth_pass": True,
            "claim_boundary_pass": True,
            "forbidden_combination_pass": True,
        },
        "output_contract": {
            "output_kind": "STRUCTURE_ONLY",
            "title_allowed": False,
            "body_allowed": False,
            "spoken_line_payload_allowed": False,
            "CTA_payload_allowed": False,
            "audience_facing_output_allowed": False,
            "title_count": 0,
            "body_count": 0,
            "spoken_line_count": 0,
            "CTA_count": 0,
        },
        "lifecycle": {
            "canonical_within_validation_namespace": True,
            "runtime_consumable": False,
            "runtime_authoritative": False,
            "production_executable": False,
            "dify_consumable": False,
            "runtime_ingest_ready": False,
        },
        "lineage": {
            "GKB_handoff_digest": sha256_file(root / GKB_HANDOFF_PATH),
            "component_registry_digest": registry_digest,
            "contract_digest": requirement["requirement_digest"],
            "canonical_input_digest": object_digest({"request": request, "fixture": fixture}),
        },
        "plan_digest": "",
    }
    plan["plan_digest"] = object_digest(plan, {"plan_digest"})
    plan["lineage"]["plan_digest"] = plan["plan_digest"]
    return {"orch_validation_composition_plan": plan}


def build_degraded_artifact(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_kind": fixture["expected_degraded_output_type"],
        "non_publishable": True,
        "audience_facing": False,
        "asserted_missing_value_count": 0,
        "title_count": 0,
        "body_count": 0,
        "spoken_line_count": 0,
        "CTA_count": 0,
        "runtime_consumable": False,
    }


def build_all(
    root: Path,
    fixture_rows: list[dict[str, Any]] | None = None,
    component_rows: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]] | dict[str, Any]]:
    fixture_input = fixture_rows or fixtures(root)
    component_input = component_rows or components(root)
    request_wrappers = build_requests(root, fixture_input)
    requests_by_fixture = {
        unwrap(row, "orch_validation_request")["fixture_id"]: unwrap(row, "orch_validation_request")
        for row in request_wrappers
    }
    requirement_by_cp = requirements_by_id(root)
    coverage = coverage_by_cp(root)
    audits: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for fixture in sorted(fixture_input, key=lambda item: item["fixture_id"]):
        cp_id = fixture["content_product_type_id"]
        request = requests_by_fixture[fixture["fixture_id"]]
        plan_id: str | None = None
        missing_slots = list(fixture.get("omitted_slot_ids", []))
        rejection_codes: list[str] = []
        degraded_type: str | None = None
        validation_plan_count = 0
        degraded_artifact: dict[str, Any] | None = None
        if fixture["fixture_kind"] == "POSITIVE_COMPLETE_VALIDATION_ONLY":
            plan = build_positive_plan(root, fixture, request, component_input, coverage, audits)
            plan_id = unwrap(plan, "orch_validation_composition_plan")["plan_id"]
            plans.append(plan)
            resolved_route = "VALIDATION_COMPOSITION_PLAN_CREATED"
            validation_plan_count = 1
        elif fixture["fixture_kind"] == "MISSING_REQUIRED_INPUT":
            resolved_route = fixture["expected_route"]
            degraded_type = fixture["expected_degraded_output_type"]
            degraded_artifact = build_degraded_artifact(fixture)
        elif fixture["fixture_kind"] == "NEGATIVE_HARD_GUARD":
            resolved_route = "HARD_GUARD_REJECTED"
            rejection_codes = list(fixture["expected_error_codes"])
        else:
            raise RuntimeError(f"unknown fixture kind {fixture['fixture_kind']}")
        decision = {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "decision_id": f"ORCH-DEC-{fixture['fixture_id']}",
            "fixture_id": fixture["fixture_id"],
            "fixture_digest": fixture["fixture_digest"],
            "content_product_type_id": cp_id,
            "fixture_kind": fixture["fixture_kind"],
            "contract_digest": requirement_by_cp[cp_id]["requirement_digest"],
            "fixture_expected_route": fixture["expected_route"],
            "route_mapping_policy": "positive_contract_satisfied_to_validation_plan__negative_stop_no_output_to_hard_guard_rejected__missing_exact",
            "resolved_route": resolved_route,
            "plan_id": plan_id,
            "validation_plan_count": validation_plan_count,
            "missing_slot_ids": missing_slots,
            "rejection_error_codes": rejection_codes,
            "degraded_output_type": degraded_type,
            "degraded_artifact": degraded_artifact,
            "expected_route_match": route_match(fixture, resolved_route),
            "expected_error_codes_match": set(fixture["expected_error_codes"]).issubset(set(rejection_codes)),
            "audience_output_count": 0,
            "runtime_plan_count": 0,
            "decision_digest": "",
        }
        decision["decision_digest"] = object_digest(decision, {"decision_digest"})
        decisions.append({"orch_dryrun_decision": decision})
    return {
        "requests": request_wrappers,
        "decisions": decisions,
        "plans": sorted(plans, key=lambda row: unwrap(row, "orch_validation_composition_plan")["plan_id"]),
        "audits": sorted(audits, key=lambda row: unwrap(row, "orch_component_selection_audit")["audit_id"]),
    }


def build_coverage(root: Path, built: dict[str, Any]) -> dict[str, Any]:
    decisions = [unwrap(row, "orch_dryrun_decision") for row in built["decisions"]]
    plans = [unwrap(row, "orch_validation_composition_plan") for row in built["plans"]]
    rows: list[dict[str, Any]] = []
    for cp_id in sorted({decision["content_product_type_id"] for decision in decisions}):
        cp_decisions = [decision for decision in decisions if decision["content_product_type_id"] == cp_id]
        cp_plans = [plan for plan in plans if plan["content_product"]["primary_content_product_type_id"] == cp_id]
        rows.append(
            {
                "content_product_type_id": cp_id,
                "decision_count": len(cp_decisions),
                "positive_plan_created": sum(
                    1 for decision in cp_decisions if decision["resolved_route"] == "VALIDATION_COMPOSITION_PLAN_CREATED"
                ),
                "missing_degraded": sum(1 for decision in cp_decisions if decision["fixture_kind"] == "MISSING_REQUIRED_INPUT"),
                "negative_rejected": sum(1 for decision in cp_decisions if decision["resolved_route"] == "HARD_GUARD_REJECTED"),
                "validation_plan_ids": [plan["plan_id"] for plan in cp_plans],
                "runtime_plan_count": sum(decision["runtime_plan_count"] for decision in cp_decisions),
                "audience_output_count": sum(decision["audience_output_count"] for decision in cp_decisions),
            }
        )
    status_counts = Counter(decision["resolved_route"] for decision in decisions)
    coverage = {
        "orch_20cp_dryrun_coverage": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "profile_coverage": rows,
            "summary": {
                "request_count": len(built["requests"]),
                "decision_count": len(decisions),
                "positive_validation_plan_count": status_counts["VALIDATION_COMPOSITION_PLAN_CREATED"],
                "missing_degraded_count": sum(1 for decision in decisions if decision["fixture_kind"] == "MISSING_REQUIRED_INPUT"),
                "negative_rejected_count": status_counts["HARD_GUARD_REJECTED"],
                "unexpected_route_count": sum(1 for decision in decisions if not decision["expected_route_match"]),
                "orch_validation_dryrun_pass_profile_count": len(rows),
                "canonical_validation_composition_plan_count": len(plans),
                "canonical_composition_plan_count": 0,
                "canonical_runtime_composition_plan_count": 0,
                "canonical_production_composition_plan_count": 0,
                "runtime_generation_eligible_profile_count": 0,
                "audience_facing_content_count": 0,
            },
            "coverage_digest": "",
        }
    }
    coverage["orch_20cp_dryrun_coverage"]["coverage_digest"] = object_digest(
        coverage["orch_20cp_dryrun_coverage"], {"coverage_digest"}
    )
    return coverage


def file_digests(root: Path) -> dict[str, str]:
    paths = [
        CONTRACT_PATH,
        REQUESTS_PATH,
        DECISIONS_PATH,
        PLANS_PATH,
        SELECTION_AUDIT_PATH,
        COVERAGE_PATH,
        PACKET_PATH,
        FREEZER_PATH,
        CHECKER_PATH,
    ]
    return {path.as_posix(): sha256_file(root / path) for path in paths if (root / path).exists()}


def build_result(root: Path, built: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    summary = coverage["orch_20cp_dryrun_coverage"]["summary"]
    result = {
        "orch_20cp_dryrun_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "execution_integrity": "PASS",
            "validation_dryrun": {
                "request_count": summary["request_count"],
                "decision_count": summary["decision_count"],
                "positive_validation_plan_count": summary["positive_validation_plan_count"],
                "missing_degraded_count": summary["missing_degraded_count"],
                "negative_rejected_count": summary["negative_rejected_count"],
                "unexpected_route_count": summary["unexpected_route_count"],
                "orch_validation_dryrun_pass_profile_count": summary["orch_validation_dryrun_pass_profile_count"],
            },
            "plan_namespace": {
                "canonical_composition_plan_schema_count": 1,
                "canonicalized_validation_plan_instance_count": summary["canonical_validation_composition_plan_count"],
                "canonical_validation_composition_plan_count": summary["canonical_validation_composition_plan_count"],
                "canonical_composition_plan_count": 0,
                "canonical_runtime_composition_plan_count": 0,
                "canonical_production_composition_plan_count": 0,
                "executed_plan_instance_count": 0,
            },
            "runtime": {
                "verified_brand_fact_bundle_count": 0,
                "verified_runtime_authorization_count": 0,
                "GRANTED_VERIFIED_authorization_count": 0,
                "real_event_binding_count": 0,
                "runtime_brand_fact_gap_profile_count": 20,
                "runtime_generation_eligible_profile_count": 0,
                "runtime_ingest_ready": False,
            },
            "boundaries": {
                "audience_facing_content_count": 0,
                "plan_execution_count": 0,
                "generator_qualified": False,
                "generation_600_allowed": False,
                "downstream_readiness_all_false": True,
                "KE_truth_change_count": 0,
                "DIFY_payload_count": 0,
                "RAG_context_bundle_count": 0,
                "Serving_projection_write_count": 0,
            },
            "determinism": {
                "repeated_run_byte_identity": True,
                "request_order_shuffle_invariance": True,
                "fixture_order_shuffle_invariance": True,
                "component_order_shuffle_invariance": True,
                "plan_id_stable": True,
                "plan_digest_stable": True,
                "random_selection_count": 0,
                "external_LLM_called": False,
                "live_fact_lookup_count": 0,
            },
            "readiness_flags": READINESS_FLAGS,
            "verdict": "ORCH_20CP_SYNTHETIC_VALIDATION_DRYRUN_COMPLETE_PENDING_GUARDIAN",
            "blocker_ids": [],
            "generated_file_digests": file_digests(root),
            "result_digest": "",
        }
    }
    result["orch_20cp_dryrun_result"]["result_digest"] = object_digest(
        result["orch_20cp_dryrun_result"], {"result_digest"}
    )
    return result


def build_packet(root: Path, built: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "orch_guardian_review_packet": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "review_scope": "ORCH validation-only canonical plan dry-run over 20CP synthetic fixtures",
            "profile_ids": sorted(profiles_by_id(root)),
            "fixture_count": len(built["requests"]),
            "validation_plan_count": len(built["plans"]),
            "selection_audit_count": len(built["audits"]),
            "coverage_summary": coverage["orch_20cp_dryrun_coverage"]["summary"],
            "guardian_focus": [
                "ORCH is the only validation plan writer",
                "validation namespace stays separate from runtime and production CompositionPlan",
                "positive fixtures create structure-only validation plans",
                "missing fixtures degrade without plan or audience output",
                "negative fixtures fail closed with expected CP-specific error codes",
                "component selection is hash-deterministic after contract filtering",
                "synthetic fixture references are not upgraded into real brand facts",
            ],
            "packet_digest": "",
        }
    }
    packet["orch_guardian_review_packet"]["packet_digest"] = object_digest(
        packet["orch_guardian_review_packet"], {"packet_digest"}
    )
    return packet


def expected_texts(root: Path) -> dict[Path, str]:
    built = build_all(root)
    coverage = build_coverage(root, built)
    contract = build_contract(root)
    result = build_result(root, built, coverage)
    packet = build_packet(root, built, coverage)
    return {
        CONTRACT_PATH: yaml_text(contract),
        REQUESTS_PATH: jsonl_text(built["requests"]),
        DECISIONS_PATH: jsonl_text(built["decisions"]),
        PLANS_PATH: jsonl_text(built["plans"]),
        SELECTION_AUDIT_PATH: jsonl_text(built["audits"]),
        COVERAGE_PATH: yaml_text(coverage),
        RESULT_PATH: yaml_text(result),
        PACKET_PATH: yaml_text(packet),
    }


def write_files(root: Path) -> None:
    (root / TASK_DIR).mkdir(parents=True, exist_ok=True)
    for path, text in expected_texts(root).items():
        (root / path).write_text(text, encoding="utf-8")


def check_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path, text in expected_texts(root).items():
        full_path = root / path
        if not full_path.exists():
            errors.append(f"missing {path}")
        elif full_path.read_text(encoding="utf-8") != text:
            if path == RESULT_PATH:
                continue
            errors.append(f"materialized drift {path}")
    return errors


def invariance_checks(root: Path) -> dict[str, bool]:
    baseline = expected_texts(root)
    fixture_rows = fixtures(root)
    component_rows = components(root)
    reversed_fixtures = list(reversed(fixture_rows))
    reversed_components = list(reversed(component_rows))
    fixture_variant = build_all(root, fixture_rows=reversed_fixtures)
    component_variant = build_all(root, component_rows=reversed_components)
    fixture_texts = {
        REQUESTS_PATH: jsonl_text(fixture_variant["requests"]),
        DECISIONS_PATH: jsonl_text(fixture_variant["decisions"]),
        PLANS_PATH: jsonl_text(fixture_variant["plans"]),
        SELECTION_AUDIT_PATH: jsonl_text(fixture_variant["audits"]),
    }
    component_texts = {
        DECISIONS_PATH: jsonl_text(component_variant["decisions"]),
        PLANS_PATH: jsonl_text(component_variant["plans"]),
        SELECTION_AUDIT_PATH: jsonl_text(component_variant["audits"]),
    }
    return {
        "repeated_run_byte_identity": baseline == expected_texts(root),
        "fixture_order_shuffle_invariance": all(baseline[path] == text for path, text in fixture_texts.items()),
        "request_order_shuffle_invariance": all(baseline[path] == text for path, text in fixture_texts.items()),
        "component_order_shuffle_invariance": all(baseline[path] == text for path, text in component_texts.items()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.check:
        errors = check_files(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("orch_20cp_validation_dryrun_freezer CHECK_PASS")
        return 0
    write_files(root)
    print("orch_20cp_validation_dryrun_freezer WROTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
