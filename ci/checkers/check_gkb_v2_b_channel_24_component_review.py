#!/usr/bin/env python3
"""Independently validate the B-channel component review and bounded handoff."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml


if not __debug__:
    print("check_gkb_v2_b_channel_24_component_review refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "GKB_V2_B_CHANNEL_24_COMPONENT_REVIEW_AND_HANDOFF_001"
TASK_DIR = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/b_channel_component_review_and_handoff_001"
)
SOURCE_PATH = TASK_DIR / "component_review_source.v0.1.yaml"
HANDOFF_SOURCE_PATH = TASK_DIR / "component_handoff_source.v0.1.yaml"
CANDIDATES_PATH = TASK_DIR / "founder_component_candidates.v0.1.jsonl"
DECISIONS_PATH = TASK_DIR / "component_domain_review_decisions.v0.1.jsonl"
EDGES_PATH = TASK_DIR / "component_CP_edge_review.v0.1.jsonl"
MERGES_PATH = TASK_DIR / "component_merge_relations.v0.1.jsonl"
REGISTRY_PATH = TASK_DIR / "reviewed_reusable_component_registry.v0.4.jsonl"
SUMMARY_PATH = TASK_DIR / "component_supply_delta_summary.v0.1.yaml"
FC_HANDOFF_PATH = TASK_DIR / "generator_validator_FC_handoff.v0.1.yaml"
ORCH_HANDOFF_PATH = TASK_DIR / "orch_AB_constraint_handoff.v0.1.yaml"
HANDOFF_PATH = TASK_DIR / "b_channel_component_handoff_candidate.v0.1.yaml"
RESULT_PATH = TASK_DIR / "b_channel_component_review_result.v0.1.yaml"
MATERIALIZER_PATH = TASK_DIR / "run_b_channel_component_review_freezer.py"
BASE_REGISTRY_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/component_supply_closeout_20cp_001/"
    "reviewed_reusable_component_registry.v0.3.jsonl"
)
PROFILE_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "controlled_composition_v2_001/content_product_profile_20_completion_001/"
    "content_product_profiles.v0.2.yaml"
)
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
HORIZON_PATH = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001/"
    "phase_0/current_ledger_horizon.v0.1.yaml"
)
HISTORICAL_ROUTE_DIGESTS_19_32 = {
    19: "a10f1a8477b7b36435ce16f806d21eec505b7d0eee39084666edbc7b9e67f76a",
    20: "ca76d27c8a84ee4a5888c17a0d88249b651de05314fc81a553d031981db4a5a3",
    21: "ba3f824ba4699c821a34416641a55f480451afdc371131916bcf30bb031b8195",
    22: "5ade29110d186c98c05fe17ed07b62a11bd590aafb38a5cec5fa10973e89fc1b",
    23: "0b7568944bdf073c5b6842263a954e59dc016709518fa57ece86b0ba2b365045",
    24: "5a64c5130872905521bfa536e2d64e17f66a2c589dbd80b3c45183a78fcfb862",
    25: "1fef7a924fe2abb7e28c5ba5a06e86a8e2421084043d02d35502ce8b1aa7da38",
    26: "6383578d17aba2642b1e1299f6227954c5846ea7a83203949303d43e233c8e3d",
    27: "58c4768bcc91ce69ffda835a85f257a1ac99116fd4276c5d1aaf7b0367a6eb1a",
    28: "35491c51661a0f39d44410d4aa08753c10e6edb9e958304802a294a00f54c880",
    29: "bc7c526085bba2e4c0b7f0cd439f9218bce81bd2e393e2f15aec6d3cce7ce456",
    30: "143ee83792fefa5f48e577350d3aa0d4ae84d79dd9f4d2866fe363620c3d6f51",
    31: "b2d7ea6f24df0db18acfb40ea6e2d50249d41320302473068dff0b688b952e48",
    32: "098b9070582e52e8d03f4bd884d317b97b650ffae7ec6c3035f1ec9993dc0e33",
}
EXPECTED_BASE_REGISTRY_SHA256 = "e5a3f31a9017a39e51ad409531e26b1e910e8e2effb34a4a24dab5fd11105bb1"
EXPECTED_PROFILE_SHA256 = "d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056"
EXPECTED_IDS = frozenset(
    [f"BNO-{index:02d}" for index in range(1, 9)]
    + [f"BRV-{index:02d}" for index in range(1, 5)]
    + [f"VGA-{index:02d}" for index in range(1, 11)]
    + [f"BCL-{index:02d}" for index in range(1, 3)]
)
ALLOWED_DECISIONS = frozenset(
    {"PROMOTE_AS_NEW", "MERGE_INTO_REUSABLE", "NEEDS_REPAIR", "REJECT"}
)
READY_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "Serving_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "release_ready",
        "production_ready",
        "runtime_ready",
        "ingest_ready",
        "runtime_eligibility",
        "fact_eligibility",
        "generator_qualified",
        "runtime_provider_adapter_qualified",
        "runtime_ingest_ready",
        "generation_600_allowed",
        "expand_3600_allowed",
        "runtime_consumable",
        "may_enter_GKB_runtime_registry",
        "may_create_CompositionPlan",
    }
)
FORBIDDEN_SURFACE_KEYS = frozenset(
    {
        "title",
        "body",
        "spoken_line",
        "spoken_lines",
        "CTA",
        "cta",
        "caption",
        "audience_content",
        "CompositionPlan",
        "composition_plan",
        "brand_fact",
        "real_event",
        "customer_name",
        "SKU",
        "price",
    }
)
ROUTE_LINE = re.compile(r"^  route_migration_([^:]+):$")
TOP_LEVEL_LINE = re.compile(r"^  [A-Za-z0-9_]+:$")


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate keys."""


def construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_digest(value: dict[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"expected mapping in {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"expected object in {path}:{index}")
        rows.append(value)
    return rows


def add_error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def recursive_pairs(value: Any) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            pairs.append((str(key), child))
            pairs.extend(recursive_pairs(child))
    elif isinstance(value, list):
        for child in value:
            pairs.extend(recursive_pairs(child))
    return pairs


def route_blocks(text: str) -> tuple[dict[int, str], list[int], list[str]]:
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    order: list[int] = []
    shadows: list[str] = []
    for index, line in enumerate(lines):
        match = ROUTE_LINE.fullmatch(line)
        if match is None:
            continue
        suffix = match.group(1)
        if not suffix.isdigit():
            shadows.append(suffix)
            continue
        route_id = int(suffix)
        starts.append((route_id, index))
        order.append(route_id)
    blocks: dict[int, str] = {}
    for route_id, start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if TOP_LEVEL_LINE.fullmatch(lines[index]):
                end = index
                break
        blocks[route_id] = "\n".join(lines[start:end]) + "\n"
    return blocks, order, shadows


def profile_maps(profile_doc: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    registry = profile_doc["content_product_profile_registry"]
    roles: dict[str, set[str]] = {}
    guards: dict[str, set[str]] = {}
    for profile in registry["profiles"]:
        cp_id = profile["content_product_type_id"]
        role_rows = profile["required_component_roles"] + profile["optional_component_roles"]
        roles[cp_id] = {row["role"] for row in role_rows}
        guards[cp_id] = {row["rule_id"] for row in profile["founder_hard_guards"]}
    return roles, guards


def check_digest(
    errors: list[dict[str, str]],
    row: dict[str, Any],
    digest_key: str,
    detail: str,
) -> None:
    if row.get(digest_key) != object_digest(row, digest_key):
        add_error(errors, "E_OBJECT_DIGEST", detail)


def validate(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = (
        SOURCE_PATH,
        HANDOFF_SOURCE_PATH,
        CANDIDATES_PATH,
        DECISIONS_PATH,
        EDGES_PATH,
        MERGES_PATH,
        REGISTRY_PATH,
        SUMMARY_PATH,
        FC_HANDOFF_PATH,
        ORCH_HANDOFF_PATH,
        HANDOFF_PATH,
        RESULT_PATH,
        MATERIALIZER_PATH,
        BASE_REGISTRY_PATH,
        PROFILE_PATH,
        LEDGER_PATH,
        HORIZON_PATH,
    )
    for path in required:
        if not (root / path).exists():
            add_error(errors, "E_REQUIRED_FILE", path.as_posix())
    if errors:
        return errors
    try:
        source = load_yaml(root / SOURCE_PATH)["component_review_source"]
        handoff_source = load_yaml(root / HANDOFF_SOURCE_PATH)["component_handoff_source"]
        candidate_rows = load_jsonl(root / CANDIDATES_PATH)
        decision_rows = load_jsonl(root / DECISIONS_PATH)
        edge_rows = load_jsonl(root / EDGES_PATH)
        merge_rows = load_jsonl(root / MERGES_PATH)
        registry_rows = load_jsonl(root / REGISTRY_PATH)
        base_rows = load_jsonl(root / BASE_REGISTRY_PATH)
        summary = load_yaml(root / SUMMARY_PATH)["component_supply_delta_summary"]
        fc_handoff = load_yaml(root / FC_HANDOFF_PATH)["generator_validator_FC_handoff"]
        orch_handoff = load_yaml(root / ORCH_HANDOFF_PATH)["orch_AB_constraint_handoff"]
        handoff = load_yaml(root / HANDOFF_PATH)["b_channel_component_handoff_candidate"]
        result = load_yaml(root / RESULT_PATH)["b_channel_component_review_result"]
        profile_doc = load_yaml(root / PROFILE_PATH)
        ledger_doc = load_yaml(root / LEDGER_PATH)["grc_3600_execution_plan_status"]
        horizon = load_yaml(root / HORIZON_PATH)["ledger_horizon"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        add_error(errors, "E_PARSE_OR_SCHEMA", str(exc))
        return errors

    base_bytes = (root / BASE_REGISTRY_PATH).read_bytes()
    registry_bytes = (root / REGISTRY_PATH).read_bytes()
    if sha256_bytes(base_bytes) != EXPECTED_BASE_REGISTRY_SHA256:
        add_error(errors, "E_BASE_REGISTRY_DRIFT", "v0.3 sha256")
    if sha256_bytes((root / PROFILE_PATH).read_bytes()) != EXPECTED_PROFILE_SHA256:
        add_error(errors, "E_PROFILE_DRIFT", "v0.2 sha256")
    if len(base_rows) != 64 or not registry_bytes.startswith(base_bytes):
        add_error(errors, "E_INHERITED_REGISTRY_BYTES", "first 64 raw lines changed or reordered")

    source_candidates = source.get("candidates")
    if not isinstance(source_candidates, list):
        add_error(errors, "E_SOURCE_CANDIDATES", "list missing")
        return errors
    source_by_id = {row.get("proposal_id"): row for row in source_candidates}
    candidates_by_id = {row.get("proposal_id"): row for row in candidate_rows}
    decisions_by_id = {row.get("proposal_id"): row for row in decision_rows}
    if any(len(mapping) != 24 for mapping in (source_by_id, candidates_by_id, decisions_by_id)):
        add_error(errors, "E_CANDIDATE_COUNT", "source/candidate/decision count must each be 24")
    if any(set(mapping) != EXPECTED_IDS for mapping in (source_by_id, candidates_by_id, decisions_by_id)):
        add_error(errors, "E_PROPOSAL_IDS", "BNO/BRV/VGA/BCL proposal set mismatch")

    materializer_text = (root / MATERIALIZER_PATH).read_text(encoding="utf-8")
    for token in ("first_for_group", "decision_distribution", "forced_zero_reject"):
        if token in materializer_text:
            add_error(errors, "E_MATERIALIZER_DECISION_ENGINE", token)

    provenance = source.get("provenance")
    expected_provenance = {
        "provenance_type": "FOUNDER_AUTHORIZED_DESIGN_COMPONENT_CANDIDATE",
        "extracted_from_clean_120": False,
        "source_text_span_required": False,
        "parent_asset_ids": [],
        "source_text_spans": [],
        "not_domain_fact": True,
        "not_real_event": True,
        "not_brand_fact": True,
        "not_person_experience": True,
        "not_product_claim": True,
        "not_runtime_authorization": True,
    }
    if not isinstance(provenance, dict) or any(
        provenance.get(key) != expected for key, expected in expected_provenance.items()
    ):
        add_error(errors, "E_PROVENANCE", "Founder design provenance was washed or misclassified")

    review_signatures: set[str] = set()
    decision_counts: Counter[str] = Counter()
    for proposal_id in sorted(EXPECTED_IDS):
        source_row = source_by_id.get(proposal_id, {})
        candidate = candidates_by_id.get(proposal_id, {})
        decision = decisions_by_id.get(proposal_id, {})
        review = source_row.get("review")
        if not isinstance(review, dict) or review.get("decision") not in ALLOWED_DECISIONS:
            add_error(errors, "E_DECISION", proposal_id)
            continue
        decision_counts[review["decision"]] += 1
        expected_candidate_fields = {
            "mechanism_definition": source_row.get("mechanism_definition"),
            "output_function": source_row.get("output_function"),
            "input_slot_contract": source_row.get("input_slots"),
            "provenance": provenance,
            "knowledge_increment": 0,
            "fact_eligibility": False,
            "runtime_eligibility": False,
        }
        for key, expected in expected_candidate_fields.items():
            if candidate.get(key) != expected:
                add_error(errors, "E_CANDIDATE_BINDING", f"{proposal_id}:{key}")
        check_digest(errors, candidate, "candidate_digest", proposal_id)
        expected_decision_fields = {
            "candidate_specific_semantic_readback": review.get("semantic_readback"),
            "asset_class_schema_fit": review.get("asset_class_schema_fit"),
            "atomicity_assessment": review.get("atomicity_assessment"),
            "truth_boundary_assessment": review.get("truth_boundary_assessment"),
            "duplicate_equivalence_assessment": review.get("duplicate_equivalence_assessment"),
            "hard_guard_assessment": review.get("hard_guard_assessment"),
            "decision": review.get("decision"),
            "decision_rationale": review.get("decision_rationale"),
            "reason_codes": review.get("reason_codes"),
        }
        for key, expected in expected_decision_fields.items():
            if decision.get(key) != expected:
                add_error(errors, "E_DECISION_BINDING", f"{proposal_id}:{key}")
        check_digest(errors, decision, "decision_digest", proposal_id)
        signature_values = [str(review.get(key, "")) for key in (
            "semantic_readback",
            "asset_class_schema_fit",
            "atomicity_assessment",
            "truth_boundary_assessment",
            "duplicate_equivalence_assessment",
            "decision_rationale",
        )]
        review_signatures.add("\n".join(signature_values))
        for key in ("mechanism_definition", "output_function", "claim_boundary"):
            value = source_row.get(key)
            if not isinstance(value, str) or not value.strip():
                add_error(errors, "E_ABSTRACTION_FIELD", f"{proposal_id}:{key}")
            elif re.search(r"\d", value):
                add_error(errors, "E_LITERAL_NUMBER_IN_COMPONENT", f"{proposal_id}:{key}")
        for key, value in recursive_pairs(source_row):
            if key in FORBIDDEN_SURFACE_KEYS:
                add_error(errors, "E_FORBIDDEN_COMPONENT_SURFACE", f"{proposal_id}:{key}")
            if key in READY_KEYS and value is True:
                add_error(errors, "E_READINESS_TRUE", f"{proposal_id}:{key}")
    if len(review_signatures) != 24:
        add_error(errors, "E_RUBBER_STAMP_REVIEW", f"unique_review_count={len(review_signatures)}")

    profile_roles, profile_guards = profile_maps(profile_doc)
    edges_by_proposal: dict[str, list[dict[str, Any]]] = {}
    edge_keys: set[tuple[str, str]] = set()
    for edge in edge_rows:
        proposal_id = edge.get("proposal_id")
        cp_id = edge.get("content_product_type_id")
        key = (str(proposal_id), str(cp_id))
        if key in edge_keys:
            add_error(errors, "E_DUPLICATE_CP_EDGE", str(key))
        edge_keys.add(key)
        edges_by_proposal.setdefault(str(proposal_id), []).append(edge)
        source_row = source_by_id.get(proposal_id, {})
        status = edge.get("edge_status")
        expected_map = source_row.get("accepted_cp_edges" if status == "ACCEPTED" else "rejected_cp_edges")
        if status not in {"ACCEPTED", "REJECTED"} or not isinstance(expected_map, dict):
            add_error(errors, "E_CP_EDGE_STATUS", str(key))
            continue
        source_edge = expected_map.get(cp_id)
        if not isinstance(source_edge, dict):
            add_error(errors, "E_CP_EDGE_BINDING", str(key))
            continue
        for field in (
            "fit_basis",
            "profile_role_basis",
            "hard_guard_refs",
            "truth_mode_compatible",
            "founder_upper_bound_respected",
        ):
            if edge.get(field) != source_edge.get(field):
                add_error(errors, "E_CP_EDGE_BINDING", f"{key}:{field}")
        if source_edge.get("founder_upper_bound_respected") is not True:
            add_error(errors, "E_FOUNDER_BOUND", str(key))
        guard_refs = set(edge.get("hard_guard_refs") or [])
        if cp_id not in profile_guards or not guard_refs or not guard_refs <= profile_guards[cp_id]:
            add_error(errors, "E_CP_HARD_GUARD", str(key))
        if status == "ACCEPTED":
            role = source_row.get("component_role")
            if role not in profile_roles.get(cp_id, set()):
                add_error(errors, "E_CP_ROLE", f"{proposal_id}:{cp_id}:{role}")
        check_digest(errors, edge, "edge_digest", str(key))

    for proposal_id, source_row in source_by_id.items():
        accepted = set(source_row.get("accepted_cp_edges") or {})
        rejected = set(source_row.get("rejected_cp_edges") or {})
        materialized = {row["content_product_type_id"] for row in edges_by_proposal.get(proposal_id, [])}
        proposed = source_row.get("proposed_cp_upper_bound")
        minimal = source_row.get("reviewed_minimal_cp_set")
        if materialized != accepted | rejected:
            add_error(errors, "E_CP_EDGE_COMPLETENESS", proposal_id)
        if isinstance(proposed, list):
            if accepted | rejected != set(proposed) or not accepted <= set(proposed):
                add_error(errors, "E_FOUNDER_BOUND", proposal_id)
        elif isinstance(minimal, list):
            if accepted != set(minimal) or rejected:
                add_error(errors, "E_MINIMAL_CP_SET", proposal_id)
        else:
            add_error(errors, "E_CP_SCOPE_MISSING", proposal_id)
        if proposal_id.startswith("BRV-") and len(accepted) == 20:
            add_error(errors, "E_BRV_DEFAULT_ALL_CP", proposal_id)

    promoted_count = decision_counts["PROMOTE_AS_NEW"]
    expected_total = len(base_rows) + promoted_count
    if len(registry_rows) != expected_total:
        add_error(errors, "E_REGISTRY_TOTAL", f"actual={len(registry_rows)} expected={expected_total}")
    base_ids = {row["component_id"] for row in base_rows}
    promoted_by_alias: dict[str, dict[str, Any]] = {}
    for component in registry_rows[len(base_rows):]:
        alias = component.get("proposal_alias_id")
        source_row = source_by_id.get(alias, {})
        if source_row.get("review", {}).get("decision") != "PROMOTE_AS_NEW":
            add_error(errors, "E_FALSE_PROMOTION", str(alias))
            continue
        promoted_by_alias[str(alias)] = component
        accepted = set(source_row.get("accepted_cp_edges") or {})
        if set(component.get("applicable_content_product_type_ids") or []) != accepted:
            add_error(errors, "E_COMPONENT_CP_BINDING", str(alias))
        expected_fields = {
            "component_id": source_row.get("canonical_component_id"),
            "component_role": source_row.get("component_role"),
            "composition_asset_class": source_row.get("composition_asset_class"),
            "reusable_mechanism": source_row.get("mechanism_definition"),
            "function": source_row.get("output_function"),
            "claim_boundary": source_row.get("claim_boundary"),
            "required_input_slots": source_row.get("input_slots"),
            "truth_boundary": source_row.get("truth_boundary"),
            "knowledge_increment": 0,
            "fact_eligibility": False,
            "runtime_eligibility": False,
            "runtime_ready": False,
            "ingest_ready": False,
        }
        for key, expected in expected_fields.items():
            if component.get(key) != expected:
                add_error(errors, "E_COMPONENT_BINDING", f"{alias}:{key}")
        if str(component.get("component_id", "")).startswith("FC-"):
            add_error(errors, "E_FC_AS_COMPONENT", str(component.get("component_id")))
        if component.get("component_id") in base_ids:
            add_error(errors, "E_COMPONENT_ID_COLLISION", str(component.get("component_id")))
        for key, value in recursive_pairs(component):
            if key in FORBIDDEN_SURFACE_KEYS:
                add_error(errors, "E_FORBIDDEN_COMPONENT_SURFACE", f"{alias}:{key}")
            if key in READY_KEYS and value is True:
                add_error(errors, "E_READINESS_TRUE", f"{alias}:{key}")
        check_digest(errors, component, "component_digest", str(alias))
    if set(promoted_by_alias) != {
        proposal_id
        for proposal_id, source_row in source_by_id.items()
        if source_row.get("review", {}).get("decision") == "PROMOTE_AS_NEW"
    }:
        add_error(errors, "E_PROMOTION_COMPLETENESS", "registry aliases")

    merge_decisions = {
        proposal_id
        for proposal_id, row in source_by_id.items()
        if row.get("review", {}).get("decision") == "MERGE_INTO_REUSABLE"
    }
    if {row.get("proposal_id") for row in merge_rows} != merge_decisions:
        add_error(errors, "E_MERGE_COMPLETENESS", "merge rows")
    for merge in merge_rows:
        proposal_id = merge.get("proposal_id")
        source_row = source_by_id.get(proposal_id, {})
        review = source_row.get("review", {})
        target_id = merge.get("merge_target_component_id")
        target = next((row for row in base_rows if row.get("component_id") == target_id), None)
        if target is None or merge.get("target_modified") is not False:
            add_error(errors, "E_MERGE_TARGET", str(proposal_id))
            continue
        if target_id != review.get("merge_target_component_id"):
            add_error(errors, "E_MERGE_TARGET", str(proposal_id))
        proof = merge.get("equivalence_proof")
        required_proof = {
            "same_mechanism",
            "same_output_function",
            "same_input_slots",
            "same_authorization_boundary",
            "same_claim_boundary",
            "same_asset_class",
            "same_component_role",
            "order_independent_equivalence",
        }
        if not isinstance(proof, dict) or set(proof) != required_proof:
            add_error(errors, "E_MERGE_EQUIVALENCE", str(proposal_id))
        else:
            if proof != review.get("merge_equivalence_proof"):
                add_error(errors, "E_MERGE_EQUIVALENCE", f"{proposal_id}:source")
            if proof.get("same_input_slots") != target.get("required_input_slots"):
                add_error(errors, "E_MERGE_EQUIVALENCE", f"{proposal_id}:slots")
            if proof.get("same_asset_class") != target.get("composition_asset_class"):
                add_error(errors, "E_MERGE_EQUIVALENCE", f"{proposal_id}:class")
            if proof.get("same_component_role") != target.get("component_role"):
                add_error(errors, "E_MERGE_EQUIVALENCE", f"{proposal_id}:role")
        check_digest(errors, merge, "merge_relation_digest", str(proposal_id))

    expected_summary = {
        "reviewed_candidate_count": 24,
        "decision_counts": {decision: decision_counts[decision] for decision in sorted(ALLOWED_DECISIONS)},
        "promoted_new_component_count": promoted_count,
        "merged_candidate_count": len(merge_rows),
        "registry_total_count": expected_total,
        "accepted_edge_count": sum(row.get("edge_status") == "ACCEPTED" for row in edge_rows),
        "rejected_edge_count": sum(row.get("edge_status") == "REJECTED" for row in edge_rows),
        "existing_component_count": 64,
        "existing_component_changed_count": 0,
        "existing_component_reordered_count": 0,
        "registry_digest": sha256_bytes(registry_bytes),
        "authoritative_freeze": False,
        "runtime_ingest_ready": False,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            add_error(errors, "E_SUMMARY", f"{key}={summary.get(key)}")
    check_digest(errors, summary, "summary_digest", "summary")

    fc_rules = fc_handoff.get("rules")
    if (
        fc_handoff.get("owner") != "GENERATOR_VALIDATOR"
        or fc_handoff.get("status") != "HANDOFF_ONLY_NOT_IMPLEMENTED"
        or fc_handoff.get("implemented_rule_count") != 0
        or fc_handoff.get("requirement_count") != 10
        or not isinstance(fc_rules, list)
        or [row.get("rule_id") for row in fc_rules] != [f"FC-{index:02d}" for index in range(1, 11)]
    ):
        add_error(errors, "E_FC_HANDOFF", "FC-01..10 ownership or state")
    check_digest(errors, fc_handoff, "handoff_digest", "FC")
    expected_axes = [
        "primary_question",
        "narrative_operator",
        "information_order",
        "visual_subject",
        "sound_subject",
        "rhythm",
        "ending",
    ]
    if (
        orch_handoff.get("owner") != "ORCH"
        or orch_handoff.get("status") != "HANDOFF_ONLY_NOT_IMPLEMENTED"
        or orch_handoff.get("implemented_constraint_count") != 0
        or orch_handoff.get("constraint_count") != 1
        or orch_handoff.get("fact_set_rule") != "A_AND_B_FACT_SET_MUST_BE_IDENTICAL"
        or orch_handoff.get("minimum_real_difference_axis_count") != 4
        or orch_handoff.get("difference_axes") != expected_axes
    ):
        add_error(errors, "E_ORCH_HANDOFF", "ORCH A/B constraint")
    check_digest(errors, orch_handoff, "handoff_digest", "ORCH")
    if (
        handoff.get("status") != "IMMUTABLE_CANDIDATE_SNAPSHOT_PENDING_GUARDIAN"
        or handoff.get("authoritative_freeze") is not False
        or handoff.get("runtime_consumable") is not False
        or handoff.get("may_create_CompositionPlan") is not False
        or handoff.get("registry_total_count") != expected_total
        or handoff.get("registry_digest") != sha256_bytes(registry_bytes)
    ):
        add_error(errors, "E_HANDOFF_CANDIDATE", "candidate handoff state")
    check_digest(errors, handoff, "handoff_digest", "handoff")

    boundaries = handoff_source.get("boundaries")
    expected_boundaries = {
        "accepted_baseline_count": 120,
        "baseline_increment_count": 0,
        "hidden_qualification_case_count": 0,
        "generated_candidate_count": 0,
        "audience_facing_content_count": 0,
        "verified_brand_fact_bundle_count": 0,
        "verified_runtime_authorization_count": 0,
        "canonical_composition_plan_count": 0,
        "runtime_composition_plan_count": 0,
        "production_composition_plan_count": 0,
        "generator_qualified": False,
        "runtime_provider_adapter_qualified": False,
        "runtime_generation_eligible_profile_count": 0,
        "runtime_ingest_ready": False,
        "generation_600_allowed": False,
        "expand_3600_allowed": False,
        "downstream_readiness_all_false": True,
        "KE_truth_change_count": 0,
        "RAG_change_count": 0,
        "DIFY_change_count": 0,
        "Serving_change_count": 0,
        "external_provider_API_call_count": 0,
    }
    if boundaries != expected_boundaries:
        add_error(errors, "E_BOUNDARIES", "handoff source boundaries")
    for document_name, document in (
        ("source", source),
        ("handoff_source", handoff_source),
        ("FC", fc_handoff),
        ("ORCH", orch_handoff),
        ("handoff", handoff),
        ("result", result),
    ):
        for key, value in recursive_pairs(document):
            if key in READY_KEYS and value is True:
                add_error(errors, "E_READINESS_TRUE", f"{document_name}:{key}")
            if key in {"CompositionPlan", "composition_plan"}:
                add_error(errors, "E_COMPOSITION_PLAN", f"{document_name}:{key}")
    if result.get("verdict") != "EXECUTED_PENDING_GUARDIAN":
        add_error(errors, "E_RESULT_STATE", str(result.get("verdict")))
    if result.get("boundaries") != expected_boundaries:
        add_error(errors, "E_RESULT_BOUNDARIES", "result")
    if result.get("ledger") != {
        "previous_horizon": 31,
        "new_horizon": 32,
        "route_migration_32_appended": True,
        "route_migration_33_allowed": False,
    }:
        add_error(errors, "E_RESULT_LEDGER", "result")
    check_digest(errors, result, "result_digest", "result")

    if not isinstance(horizon, dict) or horizon.get("horizon_digest") != object_digest(
        horizon, "horizon_digest"
    ):
        add_error(errors, "E_HORIZON_DIGEST", "current horizon")
    expected_horizon_fields = {
        "owner": "CURRENT_LEDGER_OWNER",
        "authorization_mode": "EXPLICIT_BOUNDED",
        "derivation_source": "FOUNDER_AUTHORIZED_HORIZON_FILE",
        "unknown_future_successor_allowed": False,
    }
    for key, expected in expected_horizon_fields.items():
        if horizon.get(key) != expected:
            add_error(errors, "E_HORIZON_POLICY", f"{key}={horizon.get(key)}")
    ledger_text = (root / LEDGER_PATH).read_text(encoding="utf-8")
    blocks, route_order, shadows = route_blocks(ledger_text)
    historical_order = [route for route in route_order if 19 <= route <= 32]
    if shadows or historical_order != list(range(19, 33)):
        add_error(errors, "E_LEDGER_SEQUENCE", f"order={route_order} shadows={shadows}")
    for route_id, expected_digest in HISTORICAL_ROUTE_DIGESTS_19_32.items():
        block = blocks.get(route_id, "").encode("utf-8")
        if expected_digest != sha256_bytes(block):
            add_error(errors, "E_FROZEN_ROUTE_DIGEST", f"route_migration_{route_id}")
    route32 = ledger_doc.get("route_migration_32")
    if not isinstance(route32, dict):
        add_error(errors, "E_ROUTE32", "missing")
    else:
        if route32.get("applied_by_task") != TASK_ID:
            add_error(errors, "E_ROUTE32", "task binding")
        if route32.get("migration_digest") != object_digest(route32, "migration_digest"):
            add_error(errors, "E_ROUTE32_DIGEST", "migration digest")
        fixed = route32.get("fixed_boundaries")
        if not isinstance(fixed, dict) or fixed.get("accepted_baseline_count") != 120:
            add_error(errors, "E_ROUTE32_BOUNDARY", "baseline")
        if not isinstance(fixed, dict) or fixed.get("hidden_created_count") != 0:
            add_error(errors, "E_ROUTE32_BOUNDARY", "hidden")
    return errors


def predecessor_check(root: Path, predecessor: str) -> int:
    checker_paths = {
        "component-supply": "ci/checkers/check_gkb_v2_20cp_component_supply_closeout.py",
        "fact-authorization": "ci/checkers/check_gkb_v2_20cp_fact_authorization_fixture_closeout.py",
        "orch-validation": "ci/checkers/check_orch_v2_20cp_validation_dryrun.py",
        "generator-build": "ci/checkers/check_controlled_content_generator_v2_build.py",
        "b-lane-dev-gate": (
            "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001/"
            "check_controlled_v2_b_lane_independent_composition_dev_gate.py"
        ),
    }
    checker_path = root / checker_paths[predecessor]
    spec = importlib.util.spec_from_file_location(
        "gkb_v2_component_supply_predecessor",
        checker_path,
    )
    if spec is None or spec.loader is None:
        print("cannot load predecessor supply checker", file=sys.stderr)
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if predecessor == "b-lane-dev-gate":
        errors = [
            error
            for error in module.run_live()
            if error != "E_LEDGER_NON_ADDITIVE_BEFORE_ROUTE31"
        ]
    else:
        errors = module.collect_errors(root, enforce_git=False)
    if errors:
        print(
            json.dumps(
                {"status": "FAIL", "predecessor": predecessor, "errors": errors},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "predecessor": predecessor,
                "historical_scope_delegated_to_current_checker": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


def copy_fixture(root: Path, destination: Path) -> None:
    paths = (
        SOURCE_PATH,
        HANDOFF_SOURCE_PATH,
        CANDIDATES_PATH,
        DECISIONS_PATH,
        EDGES_PATH,
        MERGES_PATH,
        REGISTRY_PATH,
        SUMMARY_PATH,
        FC_HANDOFF_PATH,
        ORCH_HANDOFF_PATH,
        HANDOFF_PATH,
        RESULT_PATH,
        MATERIALIZER_PATH,
        BASE_REGISTRY_PATH,
        PROFILE_PATH,
        LEDGER_PATH,
        HORIZON_PATH,
    )
    for path in paths:
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, target)


def mutate_yaml(path: Path, mutator: Callable[[dict[str, Any]], None]) -> None:
    document = load_yaml(path)
    mutator(document)
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")


def mutate_jsonl(path: Path, mutator: Callable[[list[dict[str, Any]]], None]) -> None:
    rows = load_jsonl(path)
    mutator(rows)
    path.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def mutate_route_block(path: Path, route_id: int, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    blocks, _, _ = route_blocks(text)
    block = blocks[route_id]
    if old not in block:
        raise ValueError(f"mutation token absent from route_migration_{route_id}")
    path.write_text(text.replace(block, block.replace(old, new, 1), 1), encoding="utf-8")


def selftest(root: Path) -> int:
    baseline_errors = validate(root)
    if baseline_errors:
        print(json.dumps({"status": "SELFTEST_BASE_INVALID", "errors": baseline_errors}, ensure_ascii=False))
        return 1

    tests: list[tuple[str, str, Callable[[Path], None]]] = []

    def add(name: str, code: str, mutation: Callable[[Path], None]) -> None:
        tests.append((name, code, mutation))

    add(
        "mutate_old_component_byte",
        "E_INHERITED_REGISTRY_BYTES",
        lambda temp: (temp / REGISTRY_PATH).write_bytes(
            (temp / REGISTRY_PATH).read_bytes().replace(b"RCV2-002", b"RCV2-X02", 1)
        ),
    )
    add(
        "reorder_old_components",
        "E_INHERITED_REGISTRY_BYTES",
        lambda temp: (temp / REGISTRY_PATH).write_text(
            "\n".join(
                [
                    (temp / REGISTRY_PATH).read_text(encoding="utf-8").splitlines()[1],
                    (temp / REGISTRY_PATH).read_text(encoding="utf-8").splitlines()[0],
                    *(temp / REGISTRY_PATH).read_text(encoding="utf-8").splitlines()[2:],
                ]
            )
            + "\n",
            encoding="utf-8",
        ),
    )
    add(
        "hardcode_registry_total_88",
        "E_SUMMARY",
        lambda temp: mutate_yaml(
            temp / SUMMARY_PATH,
            lambda doc: doc["component_supply_delta_summary"].update({"registry_total_count": 88}),
        ),
    )
    add(
        "first_promote_rest_merge",
        "E_DECISION_BINDING",
        lambda temp: mutate_jsonl(
            temp / DECISIONS_PATH,
            lambda rows: [row.update({"decision": "MERGE_INTO_REUSABLE"}) for row in rows[1:]],
        ),
    )
    add(
        "merge_different_semantics",
        "E_MERGE_EQUIVALENCE",
        lambda temp: mutate_jsonl(
            temp / MERGES_PATH,
            lambda rows: rows[0]["equivalence_proof"].update({"same_asset_class": "scene_action_kernel"}),
        ),
    )
    add(
        "wrong_asset_class",
        "E_COMPONENT_BINDING",
        lambda temp: mutate_jsonl(
            temp / REGISTRY_PATH,
            lambda rows: rows[64].update({"composition_asset_class": "scene_action_kernel"}),
        ),
    )
    add(
        "fake_clean120_provenance",
        "E_PROVENANCE",
        lambda temp: mutate_yaml(
            temp / SOURCE_PATH,
            lambda doc: doc["component_review_source"]["provenance"].update(
                {"extracted_from_clean_120": True}
            ),
        ),
    )
    add(
        "inject_numeric_fact",
        "E_LITERAL_NUMBER_IN_COMPONENT",
        lambda temp: mutate_yaml(
            temp / SOURCE_PATH,
            lambda doc: doc["component_review_source"]["candidates"][0].update(
                {"mechanism_definition": "声称在2026年完成了三次真实任务。"}
            ),
        ),
    )
    add(
        "broaden_founder_upper_bound",
        "E_FOUNDER_BOUND",
        lambda temp: mutate_yaml(
            temp / SOURCE_PATH,
            lambda doc: doc["component_review_source"]["candidates"][0][
                "accepted_cp_edges"
            ].update({"CP01": copy.deepcopy(doc["component_review_source"]["candidates"][0]["accepted_cp_edges"]["CP10"])}),
        ),
    )
    add(
        "accepted_role_mismatch",
        "E_CP_ROLE",
        lambda temp: mutate_yaml(
            temp / SOURCE_PATH,
            lambda doc: doc["component_review_source"]["candidates"][0].update(
                {"component_role": "scene"}
            ),
        ),
    )
    add(
        "hard_guard_mismatch",
        "E_CP_HARD_GUARD",
        lambda temp: mutate_jsonl(
            temp / EDGES_PATH,
            lambda rows: rows[0].update({"hard_guard_refs": ["AGR_FAKE"]}),
        ),
    )
    add(
        "CP14_CTA_injection",
        "E_FORBIDDEN_COMPONENT_SURFACE",
        lambda temp: mutate_yaml(
            temp / SOURCE_PATH,
            lambda doc: doc["component_review_source"]["candidates"][1].update(
                {"CTA": "fixture text"}
            ),
        ),
    )
    add(
        "BRV_default_all_CP",
        "E_MINIMAL_CP_SET",
        lambda temp: mutate_yaml(
            temp / SOURCE_PATH,
            lambda doc: next(
                row for row in doc["component_review_source"]["candidates"] if row["proposal_id"] == "BRV-01"
            ).update({"reviewed_minimal_cp_set": [f"CP{index:02d}" for index in range(1, 21)]}),
        ),
    )
    add(
        "FC_as_component",
        "E_REGISTRY_TOTAL",
        lambda temp: (temp / REGISTRY_PATH).write_text(
            (temp / REGISTRY_PATH).read_text(encoding="utf-8")
            + canonical_json({"component_id": "FC-01"})
            + "\n",
            encoding="utf-8",
        ),
    )
    add(
        "ORCH_marked_implemented",
        "E_ORCH_HANDOFF",
        lambda temp: mutate_yaml(
            temp / ORCH_HANDOFF_PATH,
            lambda doc: doc["orch_AB_constraint_handoff"].update(
                {"implemented_constraint_count": 1}
            ),
        ),
    )
    add(
        "CompositionPlan_created",
        "E_COMPOSITION_PLAN",
        lambda temp: mutate_yaml(
            temp / HANDOFF_SOURCE_PATH,
            lambda doc: doc["component_handoff_source"].update({"CompositionPlan": {"id": "forbidden"}}),
        ),
    )
    add(
        "generator_qualified_true",
        "E_BOUNDARIES",
        lambda temp: mutate_yaml(
            temp / HANDOFF_SOURCE_PATH,
            lambda doc: doc["component_handoff_source"]["boundaries"].update(
                {"generator_qualified": True}
            ),
        ),
    )
    add(
        "baseline_increment",
        "E_BOUNDARIES",
        lambda temp: mutate_yaml(
            temp / HANDOFF_SOURCE_PATH,
            lambda doc: doc["component_handoff_source"]["boundaries"].update(
                {"accepted_baseline_count": 121}
            ),
        ),
    )
    add(
        "hidden_created",
        "E_BOUNDARIES",
        lambda temp: mutate_yaml(
            temp / HANDOFF_SOURCE_PATH,
            lambda doc: doc["component_handoff_source"]["boundaries"].update(
                {"hidden_qualification_case_count": 1}
            ),
        ),
    )
    add(
        "historical_route_32_mutation",
        "E_FROZEN_ROUTE_DIGEST",
        lambda temp: mutate_route_block(
            temp / LEDGER_PATH,
            32,
            "registry_total_count: 86",
            "registry_total_count: 87",
        ),
    )
    add(
        "unknown_future_successor_allowed",
        "E_HORIZON_POLICY",
        lambda temp: mutate_yaml(
            temp / HORIZON_PATH,
            lambda doc: doc["ledger_horizon"].update({"unknown_future_successor_allowed": True}),
        ),
    )
    add(
        "historical_route_19_mutation",
        "E_FROZEN_ROUTE_DIGEST",
        lambda temp: mutate_route_block(
            temp / LEDGER_PATH,
            19,
            "no_readiness_flipped: true",
            "no_readiness_flipped: false",
        ),
    )
    add(
        "horizon_derived_from_ledger_max",
        "E_HORIZON_POLICY",
        lambda temp: mutate_yaml(
            temp / HORIZON_PATH,
            lambda doc: doc["ledger_horizon"].update({"derivation_source": "MAX_LEDGER_ROUTE"}),
        ),
    )

    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="gkb-b24-checker-") as temporary:
        base_temp = Path(temporary)
        for name, expected_code, mutation in tests:
            case_root = base_temp / name
            copy_fixture(root, case_root)
            mutation(case_root)
            codes = {error["code"] for error in validate(case_root)}
            if expected_code not in codes:
                failures.append({"name": name, "expected": expected_code, "actual": sorted(codes)})
        permutation_root = base_temp / "candidate_order_permutation"
        copy_fixture(root, permutation_root)
        mutate_yaml(
            permutation_root / SOURCE_PATH,
            lambda doc: doc["component_review_source"].update(
                {"candidates": list(reversed(doc["component_review_source"]["candidates"]))}
            ),
        )
        permutation_errors = validate(permutation_root)
        if permutation_errors:
            failures.append(
                {
                    "name": "candidate_order_permutation",
                    "expected": "PASS",
                    "actual": permutation_errors,
                }
            )
    if failures:
        print(json.dumps({"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "SELFTEST_PASS",
                "negative_case_count": len(tests),
                "candidate_order_permutation_invariance": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument(
        "--predecessor-check",
        choices=(
            "component-supply",
            "fact-authorization",
            "orch-validation",
            "generator-build",
            "b-lane-dev-gate",
        ),
    )
    args = parser.parse_args()
    if args.predecessor_check:
        return predecessor_check(ROOT, args.predecessor_check)
    if args.selftest:
        return selftest(ROOT)
    errors = validate(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 1
    result = load_yaml(ROOT / RESULT_PATH)["b_channel_component_review_result"]
    print(
        json.dumps(
            {
                "status": "PASS",
                "reviewed_candidate_count": result["candidate_review"]["reviewed_candidate_count"],
                "registry_total_count": result["registry"]["registry_total_count"],
                "historical_snapshot_terminal_route_id": 32,
                "current_horizon_delegated_to_owner": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
