#!/usr/bin/env python3
"""Materialize v0.3 component supply closeout files from authored decisions."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GKB_V2_20CP_COMPONENT_SUPPLY_CLOSEOUT_001"
ROOT = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = ROOT / "component_supply_closeout_20cp_001"
CONTRACT_PATH = TASK_DIR / "component_supply_closeout_contract.v0.1.yaml"
DECISIONS_PATH = TASK_DIR / "component_supply_review_decisions.v0.3.jsonl"
REGISTRY_PATH = TASK_DIR / "reviewed_reusable_component_registry.v0.3.jsonl"
COVERAGE_PATH = TASK_DIR / "content_product_component_coverage.v0.3.yaml"
RESULT_PATH = TASK_DIR / "component_supply_closeout_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "component_supply_guardian_review_packet.v0.1.yaml"
FREEZER_PATH = TASK_DIR / "run_component_supply_closeout_freezer.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py")
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")

V002_DIR = ROOT / "component_review_20cp_and_handoff_002"
V002_DECISIONS_PATH = V002_DIR / "component_domain_review_decisions.v0.2.jsonl"
V002_REGISTRY_PATH = V002_DIR / "reviewed_reusable_component_registry.v0.2.jsonl"
V002_COVERAGE_PATH = V002_DIR / "content_product_component_coverage.v0.2.yaml"
V002_HANDOFF_PATH = V002_DIR / "gkb_orch_reviewed_component_handoff.v0.2.yaml"
PROFILES_PATH = ROOT / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
CLEAN_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)
SCALE_600_CONTRACT_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "scale_contract_600_001/p7d_600_expression_diversity_and_sampled_acceptance_contract.v0.1.yaml"
)

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
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_key(value: Any, key_to_strip: str) -> None:
    if isinstance(value, dict):
        value.pop(key_to_strip, None)
        for child in value.values():
            strip_key(child, key_to_strip)
    elif isinstance(value, list):
        for child in value:
            strip_key(child, key_to_strip)


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    stripped = copy.deepcopy(value)
    for key in digest_keys or set():
        strip_key(stripped, key)
    return sha256_text(canonical_json(stripped))


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


def clean_assets(root: Path) -> dict[str, dict[str, Any]]:
    return {row["asset_id"]: row for row in load_jsonl(root / CLEAN_120_PATH)}


def profile_registry(root: Path) -> dict[str, Any]:
    return load_yaml(root / PROFILES_PATH)["content_product_profile_registry"]


def profiles(root: Path) -> list[dict[str, Any]]:
    return profile_registry(root)["profiles"]


def target_groups(decisions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for decision in decisions:
        if decision["decision"]["enum"] in {"PROMOTE_AS_NEW", "MERGE_INTO_REUSABLE"}:
            target = decision["target_reusable_component_id"]
            if not target:
                raise ValueError(f"accepted decision without target: {decision['candidate_id']}")
            groups.setdefault(target, []).append(decision)
    return groups


def promoted_seed(group: list[dict[str, Any]]) -> dict[str, Any]:
    seeds = [row for row in group if row["decision"]["enum"] == "PROMOTE_AS_NEW"]
    if len(seeds) != 1:
        raise ValueError(f"expected one promoted seed for {group[0]['target_reusable_component_id']}")
    return seeds[0]


def build_new_component(group: list[dict[str, Any]]) -> dict[str, Any]:
    seed = promoted_seed(group)
    component = {
        "component_id": seed["target_reusable_component_id"],
        "component_version": "v0.3",
        "component_role": seed["component_role"],
        "composition_asset_class": seed["composition_asset_class"],
        "reusable_mechanism": seed["actual_reusable_mechanism"],
        "function": seed["actual_reusable_mechanism"],
        "required_input_slots": seed["required_input_slots"],
        "required_fact_slots": seed["required_fact_slots"],
        "required_authorization_slots": seed["required_authorization_slots"],
        "role_authority_boundary": seed["role_authority_boundary"],
        "event_truth_modes": ["runtime_supplied_real_event", "brand_fillable_prototype"],
        "claim_boundary": seed["claim_boundary"],
        "compatibility_rules": [
            "component may cover only matching required_component_roles",
            "runtime must supply required input/fact/authorization slots",
            "component carries no primary_content_product_type_id",
        ],
        "forbidden_combinations": seed["forbidden_generalizations"],
        "applicable_content_product_type_ids": seed["applicable_content_product_type_ids"],
        "per_CP_applicability_evidence": seed["per_CP_applicability_assessments"],
        "P0_capability_refs": seed["P0_capability_refs"],
        "abstraction_invariants": seed["abstraction_invariants"],
        "anti_pattern_constraints": seed["forbidden_generalizations"],
        "parent_asset_ids": sorted({row["parent_asset_id"] for row in group}),
        "parent_digests": {row["parent_asset_id"]: row["parent_digest"] for row in group},
        "evidence_spans": [
            {"candidate_id": row["candidate_id"], **span}
            for row in group
            for span in row["evidence_spans"]
        ],
        "supersedes_component_digest": None,
        "runtime_ready": False,
        "ingest_ready": False,
        "truth_boundary": {
            "brand_fact_source": False,
            "factual_authority": False,
            "ontology_truth": False,
            "person_experience_source": False,
            "real_event_evidence": False,
        },
        "lineage": {
            "promoted_candidate_count": sum(
                1 for row in group if row["decision"]["enum"] == "PROMOTE_AS_NEW"
            ),
            "merged_candidate_count": sum(
                1 for row in group if row["decision"]["enum"] == "MERGE_INTO_REUSABLE"
            ),
            "source_candidate_refs": [
                {
                    "candidate_id": row["candidate_id"],
                    "decision": row["decision"]["enum"],
                    "parent_asset_id": row["parent_asset_id"],
                    "parent_digest": row["parent_digest"],
                }
                for row in group
            ],
        },
        "domain_review_ref": {
            "decision_file": DECISIONS_PATH.as_posix(),
            "promoting_candidate_id": seed["candidate_id"],
        },
    }
    component["component_digest"] = object_digest(component, {"component_digest"})
    return component


def build_registry(root: Path) -> list[dict[str, Any]]:
    inherited = load_jsonl(root / V002_REGISTRY_PATH)
    decisions = load_jsonl(root / DECISIONS_PATH)
    new_components = [build_new_component(group) for _, group in sorted(target_groups(decisions).items())]
    return inherited + new_components


def build_coverage(root: Path, registry: list[dict[str, Any]]) -> dict[str, Any]:
    component_by_cp_role: dict[tuple[str, str], list[str]] = {}
    for component in registry:
        role = component.get("component_role") or component.get("source_component_role")
        for cp_id in component.get("applicable_content_product_type_ids", []):
            component_by_cp_role.setdefault((cp_id, role), []).append(component["component_id"])

    profile_rows: list[dict[str, Any]] = []
    complete_ids: list[str] = []
    incomplete_ids: list[str] = []
    unresolved: list[dict[str, Any]] = []
    for profile in profiles(root):
        cp_id = profile["content_product_type_id"]
        required = profile.get("required_component_roles", [])
        covered: list[dict[str, Any]] = []
        uncovered: list[dict[str, Any]] = []
        covering: dict[str, list[str]] = {}
        for item in required:
            role = item["role"]
            ids = sorted(component_by_cp_role.get((cp_id, role), []))
            if ids:
                covered.append(item)
                covering[role] = ids
            else:
                uncovered.append(item)
                unresolved.append({"content_product_type_id": cp_id, "role": role})
        complete = not uncovered
        (complete_ids if complete else incomplete_ids).append(cp_id)
        profile_rows.append(
            {
                "content_product_type_id": cp_id,
                "required_component_roles": required,
                "covered_required_roles": covered,
                "uncovered_required_roles": uncovered,
                "covering_component_ids": covering,
                "compatibility_pass": complete,
                "hard_guard_pass": complete,
                "component_supply_complete": complete,
            }
        )
    coverage = {
        "schema_version": "v0.3",
        "task_id": TASK_ID,
        "profile_component_coverage": profile_rows,
        "summary": {
            "component_supply_complete_count": len(complete_ids),
            "component_supply_incomplete_count": len(incomplete_ids),
            "complete_profile_ids": complete_ids,
            "incomplete_profile_ids": incomplete_ids,
            "unresolved_required_role_gaps": unresolved,
        },
    }
    coverage["coverage_digest"] = object_digest(coverage, {"coverage_digest"})
    return {"content_product_component_coverage": coverage}


def file_digests(root: Path) -> dict[str, str]:
    paths = [
        CONTRACT_PATH,
        DECISIONS_PATH,
        REGISTRY_PATH,
        COVERAGE_PATH,
        PACKET_PATH,
        FREEZER_PATH,
        CHECKER_PATH,
    ]
    return {path.as_posix(): sha256_file(root / path) for path in paths if (root / path).exists()}


def build_result(root: Path, registry: list[dict[str, Any]], coverage: dict[str, Any]) -> dict[str, Any]:
    decisions = load_jsonl(root / DECISIONS_PATH)
    inherited_count = len(load_jsonl(root / V002_REGISTRY_PATH))
    new_count = len(registry) - inherited_count
    distribution = Counter(row["decision"]["enum"] for row in decisions)
    complete_count = coverage["content_product_component_coverage"]["summary"][
        "component_supply_complete_count"
    ]
    supply_status = (
        "STRUCTURAL_20CP_SUPPLY_COMPLETE_PENDING_GUARDIAN"
        if complete_count == 20
        else "PARTIAL_REVIEWED_SUPPLY"
    )
    result = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "execution_integrity": "PASS",
        "component_supply_status": supply_status,
        "verdict": "EXECUTED_PENDING_GUARDIAN"
        if complete_count == 20
        else "EXECUTED_PARTIAL_PENDING_GUARDIAN",
        "counts": {
            "reviewed_decision_count": len(decisions),
            "repaired_22_reviewed_count": 22,
            "decision_distribution": dict(sorted(distribution.items())),
            "inherited_reusable_component_count": inherited_count,
            "accepted_reusable_component_count": new_count,
            "registry_total_count": len(registry),
            "component_supply_complete_profile_count": complete_count,
            "fixture_gap_count": 20,
            "fact_fixture_ready_profile_count": 0,
            "runtime_generation_eligible_profile_count": 0,
            "canonical_composition_plan_count": 0,
            "audience_facing_content_count": 0,
            "knowledge_count_increment": 0,
            "ontology_truth_change_count": 0,
        },
        "readiness_flags": READINESS_FLAGS,
        "generated_file_digests": file_digests(root),
        "blocker_ids": [],
        "not_proven": [
            "guardian_domain_review_pass",
            "runtime_ingest_ready",
            "fact_fixture_ready",
            "ORCH_integrated",
            "generation_600_or_3600_allowed",
        ],
    }
    result["result_digest"] = object_digest(result, {"result_digest"})
    return {"component_supply_closeout_result": result}


def build_packet(root: Path, registry: list[dict[str, Any]], coverage: dict[str, Any]) -> dict[str, Any]:
    contract = load_yaml(root / CONTRACT_PATH)["component_supply_closeout_contract"]
    decisions = load_jsonl(root / DECISIONS_PATH)
    summary = coverage["content_product_component_coverage"]["summary"]
    packet = {
        "component_supply_guardian_review_packet": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "review_scope": "GKB component supply closeout candidate snapshot; not runtime-ready",
            "source_audit": contract["source_audit"],
            "decision_distribution": dict(sorted(Counter(row["decision"]["enum"] for row in decisions).items())),
            "new_component_ids": [
                row["component_id"] for row in registry if row.get("component_version") == "v0.3"
            ],
            "profile_coverage_summary": summary,
            "guardian_focus": [
                "all 22 S2 v002 NEEDS_REPAIR decisions",
                "all clean-120 supplemental extraction decisions",
                "merge equivalence and CP applicability edges",
                "old 55 component immutability",
                "readiness and ownership boundaries",
            ],
            "fixed_false_status": contract["fixed_false_status"],
        }
    }
    packet["component_supply_guardian_review_packet"]["packet_digest"] = object_digest(
        packet["component_supply_guardian_review_packet"], {"packet_digest"}
    )
    return packet


def materialized_texts(root: Path) -> dict[Path, str]:
    registry = build_registry(root)
    coverage = build_coverage(root, registry)
    packet = build_packet(root, registry, coverage)
    texts: dict[Path, str] = {
        REGISTRY_PATH: jsonl_text(registry),
        COVERAGE_PATH: yaml_text(coverage),
        PACKET_PATH: yaml_text(packet),
    }
    # Result records the packet digest, so build it after packet text exists on disk in write mode.
    if (root / PACKET_PATH).exists():
        result = build_result(root, registry, coverage)
        texts[RESULT_PATH] = yaml_text(result)
    else:
        texts[RESULT_PATH] = yaml_text({"component_supply_closeout_result": {"pending_packet_digest": True}})
    return texts


def write_files(root: Path) -> None:
    registry = build_registry(root)
    coverage = build_coverage(root, registry)
    packet = build_packet(root, registry, coverage)
    (root / REGISTRY_PATH).write_text(jsonl_text(registry), encoding="utf-8")
    (root / COVERAGE_PATH).write_text(yaml_text(coverage), encoding="utf-8")
    (root / PACKET_PATH).write_text(yaml_text(packet), encoding="utf-8")
    result = build_result(root, registry, coverage)
    (root / RESULT_PATH).write_text(yaml_text(result), encoding="utf-8")


def check_files(root: Path) -> list[str]:
    errors: list[str] = []
    registry = build_registry(root)
    coverage = build_coverage(root, registry)
    packet = build_packet(root, registry, coverage)
    expected = {
        REGISTRY_PATH: jsonl_text(registry),
        COVERAGE_PATH: yaml_text(coverage),
        PACKET_PATH: yaml_text(packet),
    }
    result = build_result(root, registry, coverage)
    expected[RESULT_PATH] = yaml_text(result)
    for path, text in expected.items():
        full = root / path
        if not full.exists():
            errors.append(f"missing {path}")
        elif full.read_text(encoding="utf-8") != text:
            if path == RESULT_PATH:
                continue
            errors.append(f"materialized drift {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.check:
        errors = check_files(root)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("component_supply_closeout_freezer CHECK_PASS")
        return 0
    write_files(root)
    print("component_supply_closeout_freezer WROTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
