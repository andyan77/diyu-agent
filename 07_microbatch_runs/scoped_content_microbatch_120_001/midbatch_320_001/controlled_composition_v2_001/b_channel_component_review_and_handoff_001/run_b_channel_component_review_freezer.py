#!/usr/bin/env python3
"""Materialize reviewed B-channel component artifacts from human-authored decisions."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    print("run_b_channel_component_review_freezer refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[5]
TASK_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001"
)
SOURCE_PATH = TASK_DIR / "component_review_source.v0.1.yaml"
CANDIDATES_PATH = TASK_DIR / "founder_component_candidates.v0.1.jsonl"
DECISIONS_PATH = TASK_DIR / "component_domain_review_decisions.v0.1.jsonl"
EDGES_PATH = TASK_DIR / "component_CP_edge_review.v0.1.jsonl"
MERGES_PATH = TASK_DIR / "component_merge_relations.v0.1.jsonl"
REGISTRY_PATH = TASK_DIR / "reviewed_reusable_component_registry.v0.4.jsonl"
SUMMARY_PATH = TASK_DIR / "component_supply_delta_summary.v0.1.yaml"
BASE_REGISTRY_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/component_supply_closeout_20cp_001/"
    "reviewed_reusable_component_registry.v0.3.jsonl"
)
EXPECTED_PROPOSALS = tuple(
    [f"BNO-{index:02d}" for index in range(1, 9)]
    + [f"BRV-{index:02d}" for index in range(1, 5)]
    + [f"VGA-{index:02d}" for index in range(1, 11)]
    + [f"BCL-{index:02d}" for index in range(1, 3)]
)
ALLOWED_DECISIONS = {
    "PROMOTE_AS_NEW",
    "MERGE_INTO_REUSABLE",
    "NEEDS_REPAIR",
    "REJECT",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_digest(value: dict[str, Any], excluded: set[str]) -> str:
    payload = {key: child for key, child in value.items() if key not in excluded}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_source(root: Path) -> dict[str, Any]:
    value = yaml.safe_load((root / SOURCE_PATH).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("component_review_source"), dict):
        raise TypeError("component review source root missing")
    return value["component_review_source"]


def validate_source(source: dict[str, Any]) -> None:
    candidates = source.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != len(EXPECTED_PROPOSALS):
        raise ValueError("source must contain exactly 24 candidates")
    proposal_ids = [candidate.get("proposal_id") for candidate in candidates]
    if sorted(proposal_ids) != sorted(EXPECTED_PROPOSALS) or len(set(proposal_ids)) != len(proposal_ids):
        raise ValueError("proposal IDs are missing or duplicated")
    for candidate in candidates:
        review = candidate.get("review")
        if not isinstance(review, dict) or review.get("decision") not in ALLOWED_DECISIONS:
            raise ValueError(f"invalid review for {candidate.get('proposal_id')}")
        accepted = candidate.get("accepted_cp_edges")
        rejected = candidate.get("rejected_cp_edges")
        if not isinstance(accepted, dict) or not isinstance(rejected, dict):
            raise ValueError(f"edge mappings missing for {candidate.get('proposal_id')}")
        if set(accepted) & set(rejected):
            raise ValueError(f"edge is both accepted and rejected for {candidate.get('proposal_id')}")
        if review["decision"] == "PROMOTE_AS_NEW" and not candidate.get("canonical_component_id"):
            raise ValueError(f"canonical ID missing for {candidate.get('proposal_id')}")
        if review["decision"] == "MERGE_INTO_REUSABLE" and not review.get("merge_target_component_id"):
            raise ValueError(f"merge target missing for {candidate.get('proposal_id')}")


def candidate_record(source: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    record = {
        "schema_version": "v0.1",
        "task_id": source["task_id"],
        "proposal_id": candidate["proposal_id"],
        "proposal_alias_id": candidate["proposal_id"],
        "label": candidate["label"],
        "candidate_family": candidate["candidate_family"],
        "proposed_composition_asset_class": candidate["composition_asset_class"],
        "proposed_component_role": candidate.get("component_role"),
        "sub_function": candidate.get("sub_function"),
        "mechanism_definition": candidate["mechanism_definition"],
        "input_slot_contract": candidate["input_slots"],
        "output_function": candidate["output_function"],
        "required_observable_evidence": candidate["required_observable_evidence"],
        "required_authorization_slots": candidate["required_authorization_slots"],
        "role_authority_boundary": candidate["role_authority_boundary"],
        "truth_boundary": candidate["truth_boundary"],
        "proposed_cp_upper_bound": candidate.get("proposed_cp_upper_bound"),
        "reviewed_minimal_cp_set": candidate.get("reviewed_minimal_cp_set"),
        "compatibility_requirements": candidate["compatibility_requirements"],
        "anti_pattern_rules": candidate["anti_pattern_rules"],
        "forbidden_inference": candidate["forbidden_inference"],
        "provenance": source["provenance"],
        "knowledge_increment": 0,
        "fact_eligibility": False,
        "runtime_eligibility": False,
        "review_status": "DOMAIN_REVIEWED_PENDING_GUARDIAN",
    }
    record["candidate_digest"] = object_digest(record, {"candidate_digest"})
    return record


def decision_record(source: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    review = candidate["review"]
    record = {
        "schema_version": "v0.1",
        "task_id": source["task_id"],
        "proposal_id": candidate["proposal_id"],
        "candidate_specific_semantic_readback": review["semantic_readback"],
        "asset_class_schema_fit": review["asset_class_schema_fit"],
        "atomicity_assessment": review["atomicity_assessment"],
        "truth_boundary_assessment": review["truth_boundary_assessment"],
        "duplicate_equivalence_assessment": review["duplicate_equivalence_assessment"],
        "proposed_cp_edges": sorted(
            set(candidate.get("proposed_cp_upper_bound") or candidate.get("reviewed_minimal_cp_set") or [])
        ),
        "accepted_cp_edges": sorted(candidate["accepted_cp_edges"]),
        "rejected_cp_edges": sorted(candidate["rejected_cp_edges"]),
        "hard_guard_assessment": review["hard_guard_assessment"],
        "decision": review["decision"],
        "decision_rationale": review["decision_rationale"],
        "reason_codes": review["reason_codes"],
        "merge_target_component_id": review.get("merge_target_component_id"),
        "merge_equivalence_proof": review.get("merge_equivalence_proof"),
        "reviewer_identity": source["reviewer_identity"],
        "review_timestamp": source["review_timestamp"],
    }
    record["decision_digest"] = object_digest(record, {"decision_digest"})
    return record


def edge_records(source: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for status, mapping in (
        ("ACCEPTED", candidate["accepted_cp_edges"]),
        ("REJECTED", candidate["rejected_cp_edges"]),
    ):
        for cp_id, edge in mapping.items():
            row = {
                "schema_version": "v0.1",
                "task_id": source["task_id"],
                "proposal_id": candidate["proposal_id"],
                "content_product_type_id": cp_id,
                "edge_status": status,
                "component_role": candidate.get("component_role"),
                "composition_asset_class": candidate["composition_asset_class"],
                "fit_basis": edge["fit_basis"],
                "profile_role_basis": edge["profile_role_basis"],
                "hard_guard_refs": edge["hard_guard_refs"],
                "truth_mode_compatible": edge["truth_mode_compatible"],
                "founder_upper_bound_respected": edge["founder_upper_bound_respected"],
            }
            row["edge_digest"] = object_digest(row, {"edge_digest"})
            rows.append(row)
    return rows


def component_record(
    source: dict[str, Any],
    candidate: dict[str, Any],
    accepted_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    cp_ids = sorted(edge["content_product_type_id"] for edge in accepted_edges)
    component = {
        "schema_version": "v0.4",
        "component_version": "v0.4",
        "component_id": candidate["canonical_component_id"],
        "proposal_alias_id": candidate["proposal_id"],
        "component_role": candidate["component_role"],
        "composition_asset_class": candidate["composition_asset_class"],
        "sub_function": candidate.get("sub_function"),
        "function": candidate["output_function"],
        "reusable_mechanism": candidate["mechanism_definition"],
        "claim_boundary": candidate["claim_boundary"],
        "required_input_slots": candidate["input_slots"],
        "required_fact_slots": candidate["required_observable_evidence"],
        "required_authorization_slots": candidate["required_authorization_slots"],
        "role_authority_boundary": candidate["role_authority_boundary"],
        "abstraction_invariants": candidate["compatibility_requirements"],
        "anti_pattern_constraints": candidate["anti_pattern_rules"],
        "forbidden_combinations": candidate["forbidden_inference"],
        "compatibility_rules": [
            "component may cover only accepted CP edges",
            "all required input, evidence and authorization slots are runtime supplied",
            "component carries no fact, event, surface text or CompositionPlan authority",
        ],
        "applicable_content_product_type_ids": cp_ids,
        "per_CP_applicability_evidence": [
            {
                "content_product_type_id": edge["content_product_type_id"],
                "required_component_role": candidate["component_role"],
                "fit_basis": edge["fit_basis"],
                "hard_guard_refs": edge["hard_guard_refs"],
            }
            for edge in sorted(accepted_edges, key=lambda item: item["content_product_type_id"])
        ],
        "event_truth_modes": [
            "runtime_supplied_real_event",
            "brand_fillable_prototype",
            "generic_creative_prototype",
        ],
        "provenance": source["provenance"],
        "domain_review_ref": {
            "decision_file": DECISIONS_PATH.as_posix(),
            "proposal_id": candidate["proposal_id"],
        },
        "lineage": {
            "provenance_type": "FOUNDER_AUTHORIZED_DESIGN_COMPONENT_CANDIDATE",
            "parent_asset_ids": [],
            "source_text_spans": [],
        },
        "truth_boundary": candidate["truth_boundary"],
        "knowledge_increment": 0,
        "fact_eligibility": False,
        "runtime_eligibility": False,
        "runtime_ready": False,
        "ingest_ready": False,
        "lifecycle": "reviewed_reusable_pending_guardian",
    }
    component["component_digest"] = object_digest(component, {"component_digest"})
    return component


def build_outputs(root: Path, source: dict[str, Any]) -> dict[Path, bytes]:
    validate_source(source)
    candidates = sorted(source["candidates"], key=lambda item: item["proposal_id"])
    candidate_rows = [candidate_record(source, candidate) for candidate in candidates]
    decision_rows = [decision_record(source, candidate) for candidate in candidates]
    edge_rows = sorted(
        [row for candidate in candidates for row in edge_records(source, candidate)],
        key=lambda item: (item["proposal_id"], item["content_product_type_id"]),
    )
    edges_by_proposal: dict[str, list[dict[str, Any]]] = {}
    for edge in edge_rows:
        if edge["edge_status"] == "ACCEPTED":
            edges_by_proposal.setdefault(edge["proposal_id"], []).append(edge)

    promoted = [candidate for candidate in candidates if candidate["review"]["decision"] == "PROMOTE_AS_NEW"]
    components = [
        component_record(source, candidate, edges_by_proposal.get(candidate["proposal_id"], []))
        for candidate in promoted
    ]
    components.sort(key=lambda item: item["component_id"])

    base_registry = (root / BASE_REGISTRY_PATH).read_bytes()
    if not base_registry.endswith(b"\n"):
        raise ValueError("base registry must end with newline")
    registry_bytes = base_registry + b"".join(
        (canonical_json(component) + "\n").encode("utf-8") for component in components
    )

    merge_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        review = candidate["review"]
        if review["decision"] != "MERGE_INTO_REUSABLE":
            continue
        row = {
            "schema_version": "v0.1",
            "task_id": source["task_id"],
            "proposal_id": candidate["proposal_id"],
            "merge_target_component_id": review["merge_target_component_id"],
            "equivalence_proof": review["merge_equivalence_proof"],
            "accepted_cp_edges": sorted(candidate["accepted_cp_edges"]),
            "target_modified": False,
        }
        row["merge_relation_digest"] = object_digest(row, {"merge_relation_digest"})
        merge_rows.append(row)

    jsonl_outputs = {
        CANDIDATES_PATH: candidate_rows,
        DECISIONS_PATH: decision_rows,
        EDGES_PATH: edge_rows,
        MERGES_PATH: merge_rows,
    }
    outputs: dict[Path, bytes] = {
        path: "".join(canonical_json(row) + "\n" for row in rows).encode("utf-8")
        for path, rows in jsonl_outputs.items()
    }
    outputs[REGISTRY_PATH] = registry_bytes

    decision_counts: dict[str, int] = {decision: 0 for decision in sorted(ALLOWED_DECISIONS)}
    for row in decision_rows:
        decision_counts[row["decision"]] += 1
    accepted_edge_count = sum(row["edge_status"] == "ACCEPTED" for row in edge_rows)
    rejected_edge_count = sum(row["edge_status"] == "REJECTED" for row in edge_rows)
    narrowed_candidates = sum(
        bool(candidate["rejected_cp_edges"])
        for candidate in candidates
        if candidate.get("proposed_cp_upper_bound") is not None
    )
    summary = {
        "component_supply_delta_summary": {
            "schema_version": "v0.1",
            "task_id": source["task_id"],
            "source_review_digest": sha256_bytes((root / SOURCE_PATH).read_bytes()),
            "existing_registry_digest": sha256_bytes(base_registry),
            "reviewed_candidate_count": len(candidate_rows),
            "decision_counts": decision_counts,
            "promoted_new_component_count": len(components),
            "merged_candidate_count": len(merge_rows),
            "registry_total_count": 64 + len(components),
            "accepted_edge_count": accepted_edge_count,
            "rejected_edge_count": rejected_edge_count,
            "narrowed_candidate_count": narrowed_candidates,
            "existing_component_count": 64,
            "existing_component_changed_count": 0,
            "existing_component_reordered_count": 0,
            "registry_digest": sha256_bytes(registry_bytes),
            "candidate_review_digest": sha256_bytes(outputs[DECISIONS_PATH]),
            "CP_edge_review_digest": sha256_bytes(outputs[EDGES_PATH]),
            "merge_relations_digest": sha256_bytes(outputs[MERGES_PATH]),
            "authoritative_freeze": False,
            "runtime_ingest_ready": False,
            "summary_digest": "PENDING",
        }
    }
    summary_value = summary["component_supply_delta_summary"]
    summary_value["summary_digest"] = object_digest(summary_value, {"summary_digest"})
    outputs[SUMMARY_PATH] = yaml.safe_dump(
        summary,
        allow_unicode=True,
        sort_keys=False,
    ).encode("utf-8")
    return outputs


def write_outputs(root: Path, outputs: dict[Path, bytes]) -> None:
    for path, content in outputs.items():
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def check_outputs(root: Path, outputs: dict[Path, bytes]) -> list[str]:
    errors: list[str] = []
    for path, expected in outputs.items():
        destination = root / path
        if not destination.exists():
            errors.append(f"missing:{path.as_posix()}")
        elif destination.read_bytes() != expected:
            errors.append(f"drift:{path.as_posix()}")
    return errors


def check_permutations(root: Path, source: dict[str, Any]) -> list[str]:
    baseline = build_outputs(root, source)
    candidates = source["candidates"]
    errors: list[str] = []
    permutations = [list(reversed(candidates))]
    for seed in (7, 19, 31):
        shuffled = list(candidates)
        random.Random(seed).shuffle(shuffled)
        permutations.append(shuffled)
    for index, permutation in enumerate(permutations):
        mutated = copy.deepcopy(source)
        mutated["candidates"] = permutation
        if build_outputs(root, mutated) != baseline:
            errors.append(f"permutation_{index}_changed_output")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-permutations", action="store_true")
    args = parser.parse_args()
    if not (args.write or args.check or args.check_permutations):
        parser.error("one mode is required")
    source = load_source(ROOT)
    outputs = build_outputs(ROOT, source)
    if args.write:
        write_outputs(ROOT, outputs)
    errors: list[str] = []
    if args.check:
        errors.extend(check_outputs(ROOT, outputs))
    if args.check_permutations:
        errors.extend(check_permutations(ROOT, source))
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", "output_count": len(outputs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
