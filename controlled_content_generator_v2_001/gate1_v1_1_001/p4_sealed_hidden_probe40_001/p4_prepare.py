#!/usr/bin/env python3
"""Prepare and freeze the P4 sealed input without authoring any content."""

from __future__ import annotations

import difflib
import re
import subprocess
from collections import Counter, defaultdict
from typing import Any, Mapping

from p4_common import (
    AB_PATHS,
    ALLOWED_ACTIONS,
    ALLOWED_INPUT,
    ALLOWED_REASONS,
    AUTHOR_REQUESTS,
    BASELINE_MANIFEST,
    COMPONENTS,
    CURATED_ANOMALY,
    CURATED_POSITIVE,
    CURATION_CONTRACT,
    CURATION_VALIDATION,
    CURATOR_RECEIPT,
    CURRENT_CHECKER,
    EDGES,
    EXPECTED_PROFILES,
    EXPECTED_VARIANTS,
    FROZEN_HASHES,
    HIDDEN_FREEZE,
    LIFECYCLE,
    MODEL_CAPABILITY,
    P3_REQUESTS,
    P4,
    PROFILES,
    PROMPT_REVISION,
    REASONING_EFFORT,
    REVIEW_CONTRACT,
    ROOT,
    ROUTE_GOLD,
    ROUTE_INPUTS,
    RUN_ORDER,
    SERVICE_TIER,
    TASK_ID,
    TASK_ROOT,
    TOOL_FREEZE,
    bind_digest,
    load_json,
    load_yaml,
    object_digest,
    read_jsonl,
    sha256_bytes,
    sha256_file,
    write_json,
    write_jsonl,
    write_yaml,
)


POSITIVE_SCHEMA = "gate1-p4-curated-positive-v0.1"
ANOMALY_SCHEMA = "gate1-p4-curated-anomaly-v0.1"
REQUEST_SCHEMA = "gate1-p4-sealed-author-request-v0.1"
ROUTE_INPUT_SCHEMA = "gate1-p4-sealed-route-input-v0.1"


def _profiles() -> list[dict[str, Any]]:
    registry = load_yaml(ROOT / PROFILES).get("content_product_profile_registry")
    if not isinstance(registry, dict) or not isinstance(registry.get("profiles"), list):
        raise ValueError("E_PROFILE_REGISTRY")
    rows = registry["profiles"]
    if {row.get("content_product_type_id") for row in rows} != set(EXPECTED_PROFILES):
        raise ValueError("E_PROFILE_SET")
    return rows


def _project_allowed_input() -> dict[str, Any]:
    profiles = _profiles()
    components = {row["component_id"]: row for row in read_jsonl(ROOT / COMPONENTS)}
    edges = read_jsonl(ROOT / EDGES)
    paths = {row["content_product_type_id"]: row for row in read_jsonl(ROOT / AB_PATHS)}
    edges_by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        edges_by_profile[str(edge["content_product_type_id"])].append(edge)
    projected: list[dict[str, Any]] = []
    for profile in profiles:
        profile_id = str(profile["content_product_type_id"])
        path = paths[profile_id]
        component_rows: list[dict[str, Any]] = []
        for edge in sorted(
            edges_by_profile[profile_id], key=lambda row: str(row["edge_id"])
        ):
            component = components[str(edge["component_id"])]
            component_rows.append(
                {
                    "component_id": component["component_id"],
                    "component_digest": component["component_digest"],
                    "component_role": component["component_role"],
                    "mechanism": component["mechanism"],
                    "required_input_slots": component.get("required_input_slots", []),
                    "required_fact_slots": component.get("required_fact_slots", []),
                    "required_authorization_slots": component.get(
                        "required_authorization_slots", []
                    ),
                    "claim_boundary": component.get("claim_boundary"),
                }
            )
        axis_programs: dict[str, Any] = {"A": {}, "B": {}}
        axis_values: dict[str, Any] = {"A": {}, "B": {}}
        for contract in path["axis_realization_contracts"]:
            axis = str(contract["axis"])
            axis_values["A"][axis] = contract["lane_a_value"]
            axis_values["B"][axis] = contract["lane_b_value"]
            axis_programs["A"][axis] = contract["lane_a_structural_output"][
                "structural_body"
            ]
            axis_programs["B"][axis] = contract["lane_b_structural_output"][
                "structural_body"
            ]
        projected.append(
            {
                "profile_id": profile_id,
                "label": profile["chinese_label"],
                "business_purpose": profile["business_purpose"],
                "target_account_roles": profile["target_account_roles"],
                "target_platforms": profile["target_platforms"],
                "founder_core_inputs": profile["founder_core_inputs"],
                "input_requirements": profile["input_requirements"],
                "required_component_roles": profile["required_component_roles"],
                "optional_component_roles": profile["optional_component_roles"],
                "narrative_constraints": profile["narrative_constraints"],
                "style_constraints": profile["style_constraints"],
                "founder_hard_guards": profile["founder_hard_guards"],
                "input_sufficiency_routes": profile["input_sufficiency_routes"],
                "event_truth_policy": profile["event_truth_policy"],
                "approved_components": component_rows,
                "lane_axis_values": axis_values,
                "lane_axis_programs": axis_programs,
            }
        )
    value = {
        "schema_version": "gate1-p4-curator-allowed-input-v0.1",
        "task_id": TASK_ID,
        "source_boundary": {
            "contains_p3_cases_or_outputs": False,
            "contains_historical_hidden_cases": False,
            "contains_route_answer_pairings": False,
            "synthetic_hidden_qualification_only": True,
        },
        "route_vocabulary": {
            "allowed_primary_actions": sorted(ALLOWED_ACTIONS),
            "allowed_primary_reason_categories": sorted(ALLOWED_REASONS),
            "gold_pairing_not_included": True,
        },
        "profiles": projected,
    }
    return bind_digest(value, "allowed_input_digest")


def _curation_contract() -> dict[str, Any]:
    value = {
        "schema_version": "gate1-p4-curation-contract-v0.1",
        "task_id": TASK_ID,
        "curator_role": "ISOLATED_HIDDEN_MATERIAL_CURATOR",
        "allowed_inputs": [
            str(ALLOWED_INPUT),
            str(TASK_ROOT / "curation/curation_contract.v0.1.yaml"),
            str(TASK_ROOT / "review/p4_independent_review_contract.v0.1.yaml"),
            str(
                TASK_ROOT.parent
                / "p1a_standard_baseline_review_packet_and_governance_preflight_001/"
                "standard/diyu_content_composition_standard.v1.1.md"
            ),
        ],
        "forbidden_inputs": [
            "P3 open inputs, outputs, reviews, repair basis, or feedback",
            "P1B cases and route gold",
            "historical hidden, sealed, or qualification probe materials",
            "author context, generated candidates, or reviewer conclusions",
        ],
        "positive_schema": {
            "schema_version": POSITIVE_SCHEMA,
            "required_top_level_fields": [
                "schema_version",
                "task_id",
                "case_id",
                "profile_id",
                "assigned_variant",
                "run_order",
                "scenario_title",
                "scenario_summary",
                "platform",
                "audience",
                "duration_seconds",
                "typed_material",
                "product_core_requirements",
                "curation_rationale",
                "case_digest",
            ],
            "typed_material_required": [
                "material_id",
                "namespace",
                "profile_id",
                "sources",
                "authorizations",
                "facts",
                "claim_boundary",
                "synthetic_test_only",
                "publishable",
                "runtime_consumable",
                "may_enter_300",
                "material_digest",
            ],
            "fact_required": [
                "fact_id",
                "slot_id",
                "semantic_kind",
                "value",
                "source_ids",
                "authorization_ids",
                "fact_value_digest",
            ],
        },
        "anomaly_classes": {
            "INPUT_CONFLICT": ["BLOCK", "输入冲突"],
            "AUTHORIZATION_HIGH_RISK": ["BLOCK", "授权缺失"],
            "FACT_HIGH_RISK": ["BLOCK", "事实缺失"],
            "FACT_MISSING_REQUEST": ["REQUEST_INPUT", "事实缺失"],
            "AUTHORIZATION_MISSING_REQUEST": ["REQUEST_INPUT", "授权缺失"],
            "FACT_MISSING_DEGRADE": ["DEGRADE", "事实缺失"],
            "AUTHORIZATION_MISSING_DEGRADE": ["DEGRADE", "授权缺失"],
        },
        "anomaly_schema": {
            "schema_version": ANOMALY_SCHEMA,
            "required_top_level_fields": [
                "schema_version",
                "task_id",
                "case_id",
                "profile_id",
                "run_order",
                "anomaly_class",
                "actual_input_payload",
                "gold_primary_action",
                "gold_primary_reason_category",
                "gold_rationale",
                "case_digest",
            ],
        },
        "distribution": {
            "profile_positive_and_anomaly_each": 1,
            "lane_A": 10,
            "lane_B": 10,
            "variant_counts": EXPECTED_VARIANTS,
            "case_replacement_after_freeze": False,
        },
    }
    return {"p4_curation_contract": bind_digest(value, "contract_digest")}


def _review_contract() -> dict[str, Any]:
    value = {
        "schema_version": "gate1-p4-independent-review-contract-v0.1",
        "task_id": TASK_ID,
        "review_roles": ["CONTENT_VALUE", "FACT_AUTHORIZATION"],
        "identity_policy": {
            "reviewers_pairwise_distinct": True,
            "distinct_from_curator_author_executor_and_freezer": True,
            "blind_stage_before_label_mapping": True,
            "may_not_read_other_review_before_signature": True,
        },
        "positive_scoring": {
            "public_dimensions": {
                "truth_and_boundary": 20,
                "apparel_specificity": 10,
                "role_and_brand_consistency": 10,
                "user_value": 10,
                "platform_execution": 10,
                "anti_formula": 10,
            },
            "product_dimensions": {
                "product_core_fidelity": 15,
                "product_specific_narrative_av": 10,
                "continuity": 5,
            },
            "total": 100,
            "first_acceptable_grades": ["A", "B"],
            "hard_error_overrides_score": True,
        },
        "batch_thresholds": {
            "first_acceptable_min": 18,
            "reviewer_blind_top1_min_each": 17,
            "formula_or_near_duplicate_union_max": 2,
            "hard_error_max": 0,
            "route_action_match": 20,
            "route_reason_match": 20,
        },
        "targeted_adjudication": {
            "only_real_disagreements": True,
            "never_full_third_review": True,
            "never_average_away_hard_veto": True,
        },
    }
    return {"p4_independent_review_contract": bind_digest(value, "contract_digest")}


def prepare_tools() -> None:
    if (ROOT / CURATED_POSITIVE).exists() or (ROOT / CURATED_ANOMALY).exists():
        raise ValueError("E_HIDDEN_MATERIAL_EXISTS_BEFORE_TOOL_FREEZE")
    for path, expected in FROZEN_HASHES.items():
        if sha256_file(ROOT / path) != expected:
            raise ValueError(f"E_FROZEN_BASELINE:{path}")
    write_json(ROOT / ALLOWED_INPUT, _project_allowed_input())
    write_yaml(ROOT / CURATION_CONTRACT, _curation_contract())
    write_yaml(ROOT / REVIEW_CONTRACT, _review_contract())
    baseline = {
        "p4_frozen_baseline": bind_digest(
            {
                "schema_version": "gate1-p4-frozen-baseline-v0.1",
                "task_id": TASK_ID,
                "prompt_revision": PROMPT_REVISION,
                "baseline_head": "44609ef9d87594019b444d5bbfa229493f9ef566",
                "frozen_files": {
                    path.as_posix(): digest for path, digest in FROZEN_HASHES.items()
                },
                "core_numbers": {
                    "300": "UNCHANGED",
                    "120": "UNCHANGED",
                    "86": "UNCHANGED",
                },
                "readiness_transition_authorized": False,
            },
            "manifest_digest",
        )
    }
    write_yaml(ROOT / BASELINE_MANIFEST, baseline)
    lifecycle = {
        "p4_lifecycle": bind_digest(
            {
                "schema_version": "gate1-p4-lifecycle-v0.1",
                "task_id": TASK_ID,
                "state": "TOOLS_PREPARED_PENDING_FREEZE_COMMIT",
                "generator_qualified": False,
                "p5_allowed": False,
                "hidden_created": False,
                "hidden_exposed": False,
                "core_numbers_unchanged": True,
                "all_non_generator_readiness_false": True,
            },
            "lifecycle_digest",
        )
    }
    write_yaml(ROOT / LIFECYCLE, lifecycle)


def seal_tool_freeze(commit: str) -> None:
    if (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, check=False
        ).returncode
        != 0
    ):
        raise ValueError("E_TOOL_FREEZE_COMMIT")
    hidden_paths = [CURATED_POSITIVE, CURATED_ANOMALY, AUTHOR_REQUESTS, ROUTE_GOLD]
    for path in hidden_paths:
        if (
            subprocess.run(
                ["git", "cat-file", "-e", f"{commit}:{path.as_posix()}"],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        ):
            raise ValueError(f"E_HIDDEN_IN_TOOL_COMMIT:{path}")
    tool_files = sorted(
        path.relative_to(ROOT) for path in P4.glob("*.py") if path.is_file()
    ) + [CURRENT_CHECKER]
    tool_hashes = {path.as_posix(): sha256_file(ROOT / path) for path in tool_files}
    value = {
        "p4_tool_freeze": bind_digest(
            {
                "schema_version": "gate1-p4-tool-freeze-v0.1",
                "task_id": TASK_ID,
                "tool_freeze_commit": commit,
                "tool_files": tool_hashes,
                "allowed_input_sha256": sha256_file(ROOT / ALLOWED_INPUT),
                "curation_contract_sha256": sha256_file(ROOT / CURATION_CONTRACT),
                "review_contract_sha256": sha256_file(ROOT / REVIEW_CONTRACT),
                "hidden_material_absent_from_tool_commit": True,
                "frozen_before_hidden_creation": True,
            },
            "freeze_digest",
        )
    }
    write_yaml(ROOT / TOOL_FREEZE, value)
    lifecycle = load_yaml(ROOT / LIFECYCLE)["p4_lifecycle"]
    lifecycle["state"] = "TOOLS_FROZEN"
    lifecycle["tool_freeze_commit"] = commit
    lifecycle["lifecycle_digest"] = object_digest(lifecycle, "lifecycle_digest")
    write_yaml(ROOT / LIFECYCLE, {"p4_lifecycle": lifecycle})


def _assert_digest(row: dict[str, Any], key: str) -> None:
    if row.get(key) != object_digest(row, key):
        raise ValueError(f"E_DIGEST:{row.get('case_id')}:{key}")


def _validate_curator_identity(receipt: Mapping[str, Any]) -> None:
    required = (
        "curator_identity_id",
        "curator_platform_agent_id",
        "curator_session_id",
        "curator_run_id",
    )
    if any(
        not isinstance(receipt.get(key), str) or not receipt.get(key)
        for key in required
    ):
        raise ValueError("E_CURATOR_IDENTITY")
    if receipt.get("allowed_input_sha256") != sha256_file(ROOT / ALLOWED_INPUT):
        raise ValueError("E_CURATOR_ALLOWED_INPUT")
    if receipt.get("forbidden_material_access_count") != 0:
        raise ValueError("E_CURATOR_FORBIDDEN_ACCESS")
    if receipt.get("external_provider_requests") != 0:
        raise ValueError("E_CURATOR_EXTERNAL_PROVIDER")


def _validate_positive(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 20:
        raise ValueError("E_POSITIVE_COUNT")
    if {row.get("profile_id") for row in rows} != set(EXPECTED_PROFILES):
        raise ValueError("E_POSITIVE_PROFILE_COVERAGE")
    if Counter(str(row.get("assigned_variant")) for row in rows) != Counter(
        EXPECTED_VARIANTS
    ):
        raise ValueError("E_VARIANT_DISTRIBUTION")
    if sorted(row.get("run_order") for row in rows) != list(range(1, 21)):
        raise ValueError("E_POSITIVE_RUN_ORDER")
    for row in rows:
        if (
            row.get("schema_version") != POSITIVE_SCHEMA
            or row.get("task_id") != TASK_ID
        ):
            raise ValueError("E_POSITIVE_SCHEMA")
        _assert_digest(row, "case_digest")
        material = row.get("typed_material")
        if not isinstance(material, dict):
            raise ValueError("E_TYPED_MATERIAL")
        _assert_digest(material, "material_digest")
        if (
            material.get("profile_id") != row.get("profile_id")
            or material.get("namespace") != "P4_SYNTHETIC_HIDDEN_QUALIFICATION"
            or material.get("synthetic_test_only") is not True
            or material.get("publishable") is not False
            or material.get("runtime_consumable") is not False
            or material.get("may_enter_300") is not False
        ):
            raise ValueError("E_MATERIAL_BOUNDARY")
        sources = material.get("sources")
        authorizations = material.get("authorizations")
        facts = material.get("facts")
        if not all(
            isinstance(value, list) and value
            for value in (sources, authorizations, facts)
        ):
            raise ValueError("E_MATERIAL_CLOSURE")
        source_ids = {item.get("source_id") for item in sources}
        auth_ids = {item.get("authorization_id") for item in authorizations}
        semantic_kinds: set[str] = set()
        for fact in facts:
            if not isinstance(fact, dict):
                raise ValueError("E_FACT_SCHEMA")
            semantic_kinds.add(str(fact.get("semantic_kind")))
            expected = sha256_bytes(str(fact.get("value", "")).encode("utf-8"))
            if fact.get("fact_value_digest") != expected:
                raise ValueError("E_FACT_VALUE_DIGEST")
            if not set(fact.get("source_ids", [])).issubset(source_ids):
                raise ValueError("E_FACT_SOURCE")
            if not set(fact.get("authorization_ids", [])).issubset(auth_ids):
                raise ValueError("E_FACT_AUTHORIZATION")
        required_kinds = {
            "setting",
            "actor",
            "object",
            "observation",
            "action",
            "result",
            "visual",
            "sound",
        }
        if not required_kinds.issubset(semantic_kinds):
            raise ValueError(f"E_MATERIAL_SEMANTIC_KINDS:{row['profile_id']}")
        if not row.get("product_core_requirements"):
            raise ValueError("E_PRODUCT_CORE_REQUIREMENTS")


def _validate_anomaly(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 20 or {row.get("profile_id") for row in rows} != set(
        EXPECTED_PROFILES
    ):
        raise ValueError("E_ANOMALY_COVERAGE")
    if sorted(row.get("run_order") for row in rows) != list(range(21, 41)):
        raise ValueError("E_ANOMALY_RUN_ORDER")
    contract = load_yaml(ROOT / CURATION_CONTRACT)["p4_curation_contract"]
    classes = contract["anomaly_classes"]
    actions: Counter[str] = Counter()
    for row in rows:
        if row.get("schema_version") != ANOMALY_SCHEMA or row.get("task_id") != TASK_ID:
            raise ValueError("E_ANOMALY_SCHEMA")
        _assert_digest(row, "case_digest")
        expected = classes.get(row.get("anomaly_class"))
        actual = [
            row.get("gold_primary_action"),
            row.get("gold_primary_reason_category"),
        ]
        if expected != actual:
            raise ValueError(f"E_ANOMALY_GOLD:{row.get('case_id')}")
        if not isinstance(row.get("actual_input_payload"), dict):
            raise ValueError("E_ANOMALY_PAYLOAD")
        actions[str(row["gold_primary_action"])] += 1
    if (
        set(actions) != set(ALLOWED_ACTIONS)
        or max(actions.values()) - min(actions.values()) > 1
    ):
        raise ValueError(f"E_ANOMALY_ACTION_BALANCE:{dict(actions)}")


def _normalized(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", value).lower()


def _text_values(value: Any) -> list[str]:
    output: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {
                "case_id",
                "profile_id",
                "fact_id",
                "source_id",
                "authorization_id",
                "digest",
            }:
                continue
            output.extend(_text_values(child))
    elif isinstance(value, list):
        for child in value:
            output.extend(_text_values(child))
    elif isinstance(value, str) and len(_normalized(value)) >= 12:
        output.append(value)
    return output


def _material_text_values(row: Mapping[str, Any]) -> list[str]:
    """Return authored case material, excluding shared schema and policy vocabulary."""
    output: list[str] = []
    for key in ("scenario_title", "scenario_summary"):
        value = row.get(key)
        if isinstance(value, str) and len(_normalized(value)) >= 12:
            output.append(value)

    typed_material = row.get("typed_material")
    if isinstance(typed_material, Mapping):
        scenario_name = typed_material.get("scenario_name")
        if isinstance(scenario_name, str) and len(_normalized(scenario_name)) >= 12:
            output.append(scenario_name)
        scenario_payload = typed_material.get("scenario_payload")
        if scenario_payload is not None:
            output.extend(_text_values(scenario_payload))
        facts = typed_material.get("facts")
        if isinstance(facts, list):
            for fact in facts:
                if not isinstance(fact, Mapping):
                    continue
                semantic_kind = fact.get("semantic_kind")
                if semantic_kind not in {
                    None,
                    "setting",
                    "actor",
                    "object",
                    "observation",
                    "action",
                    "result",
                    "visual",
                    "sound",
                }:
                    continue
                value = fact.get("value", fact.get("fact_value"))
                if isinstance(value, str) and len(_normalized(value)) >= 12:
                    output.append(value)
        requirements = typed_material.get("product_core_surface_requirements")
        if isinstance(requirements, list):
            for requirement in requirements:
                if isinstance(requirement, Mapping):
                    output.extend(_text_values(requirement.get("required_values", [])))

    actual_input = row.get("actual_input_payload")
    if isinstance(actual_input, Mapping):
        conflict = actual_input.get("hard_guard_conflict")
        if isinstance(conflict, Mapping):
            output.extend(_text_values(conflict.get("conflicting_input")))
        output.extend(_text_values(actual_input.get("supplied", {})))
    return output


def _anti_reuse(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prior = read_jsonl(ROOT / P3_REQUESTS)
    current_texts = [
        _normalized(text) for row in rows for text in _material_text_values(row)
    ]
    prior_texts = [
        _normalized(text) for row in prior for text in _material_text_values(row)
    ]
    shingle_size = 4
    prior_shingles = [
        {text[index : index + shingle_size] for index in range(len(text) - shingle_size + 1)}
        for text in prior_texts
    ]
    index: dict[str, set[int]] = defaultdict(set)
    for prior_index, shingles in enumerate(prior_shingles):
        for shingle in shingles:
            index[shingle].add(prior_index)
    max_ratio = 0.0
    exact_hits: list[str] = []
    compared_pair_count = 0
    for current in current_texts:
        current_shingles = {
            current[index : index + shingle_size]
            for index in range(len(current) - shingle_size + 1)
        }
        candidate_counts: Counter[int] = Counter()
        for shingle in current_shingles:
            candidate_counts.update(index.get(shingle, ()))
        candidates = [
            prior_index
            for prior_index, shared_count in candidate_counts.most_common(200)
            if shared_count >= 2
            and shared_count / max(1, min(len(current_shingles), len(prior_shingles[prior_index])))
            >= 0.2
        ]
        for prior_index in candidates:
            previous = prior_texts[prior_index]
            compared_pair_count += 1
            if len(current) >= 30 and (current in previous or previous in current):
                shorter = min(len(current), len(previous))
                if shorter >= 30:
                    exact_hits.append(current[:40])
            if len(current) >= 20 and len(previous) >= 20:
                max_ratio = max(
                    max_ratio, difflib.SequenceMatcher(None, current, previous).ratio()
                )
    if exact_hits or max_ratio >= 0.82:
        raise ValueError(f"E_HISTORICAL_NEAR_REUSE:{max_ratio:.3f}:{exact_hits[:2]}")
    return {
        "p3_request_comparison_count": len(prior),
        "raw_text_pair_space": len(current_texts) * len(prior_texts),
        "indexed_candidate_pair_count": compared_pair_count,
        "indexed_prefilter": "4_CHARACTER_SHINGLE_OVERLAP_AT_LEAST_0_2_TOP_200",
        "normalized_exact_30_character_hit_count": len(exact_hits),
        "maximum_sequence_similarity": round(max_ratio, 6),
        "threshold": 0.82,
        "pass": True,
    }


def _build_request(
    row: dict[str, Any],
    profile: dict[str, Any],
    allowed_profile: dict[str, Any],
    author_agent_id: str,
) -> dict[str, Any]:
    lane = str(row["assigned_variant"])[0]
    request: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA,
        "task_id": TASK_ID,
        "request_id": str(row["case_id"]),
        "profile_id": row["profile_id"],
        "assigned_variant": row["assigned_variant"],
        "lane": lane,
        "run_order": row["run_order"],
        "model_capability_id": MODEL_CAPABILITY,
        "reasoning_effort": REASONING_EFFORT,
        "service_tier": SERVICE_TIER,
        "author_identity": "P4-CONTROLLED-AUTHOR-GPT56SOL-001",
        "author_session_logical_id": "P4-AUTHOR-SESSION-GPT56SOL-001",
        "author_platform_agent_id": author_agent_id,
        "platform": row["platform"],
        "audience": row["audience"],
        "duration_seconds": row["duration_seconds"],
        "business_purpose": profile["business_purpose"],
        "typed_material": row["typed_material"],
        "product_core_requirements": row["product_core_requirements"],
        "approved_components": allowed_profile["approved_components"],
        "structure_contract": {
            "axis_values": allowed_profile["lane_axis_values"][lane],
            "axis_programs": allowed_profile["lane_axis_programs"][lane],
        },
        "founder_hard_guards": profile["founder_hard_guards"],
        "narrative_constraints": profile["narrative_constraints"],
        "style_constraints": profile["style_constraints"],
        "author_output_contract": {
            "all_audience_surfaces_require_exact_fact_source_authorization_binding": True,
            "component_usage_requires_distinct_addressable_surface_evidence": True,
            "one_first_semantic_output_only": True,
            "synthetic_disclosure_required": True,
            "publishable": False,
            "runtime_consumable": False,
            "may_enter_300": False,
            "author_may_not_review_or_approve": True,
        },
    }
    return bind_digest(request, "request_digest")


def freeze_hidden(author_agent_id: str) -> None:
    lifecycle = load_yaml(ROOT / LIFECYCLE)["p4_lifecycle"]
    if lifecycle.get("state") != "TOOLS_FROZEN":
        raise ValueError("E_TOOL_NOT_FROZEN")
    if not isinstance(author_agent_id, str) or not author_agent_id:
        raise ValueError("E_AUTHOR_AGENT_ID")
    positives = read_jsonl(ROOT / CURATED_POSITIVE)
    anomalies = read_jsonl(ROOT / CURATED_ANOMALY)
    receipt = load_yaml(ROOT / CURATOR_RECEIPT)["p4_curator_run_receipt"]
    _validate_curator_identity(receipt)
    _validate_positive(positives)
    _validate_anomaly(anomalies)
    reuse = _anti_reuse(positives + anomalies)
    allowed = load_json(ROOT / ALLOWED_INPUT)
    allowed_by_id = {row["profile_id"]: row for row in allowed["profiles"]}
    profile_by_id = {row["content_product_type_id"]: row for row in _profiles()}
    requests = [
        _build_request(
            row,
            profile_by_id[row["profile_id"]],
            allowed_by_id[row["profile_id"]],
            author_agent_id,
        )
        for row in sorted(positives, key=lambda item: int(item["run_order"]))
    ]
    route_inputs: list[dict[str, Any]] = []
    route_gold: list[dict[str, Any]] = []
    for row in sorted(anomalies, key=lambda item: int(item["run_order"])):
        route_inputs.append(
            bind_digest(
                {
                    "schema_version": ROUTE_INPUT_SCHEMA,
                    "task_id": TASK_ID,
                    "case_id": row["case_id"],
                    "profile_id": row["profile_id"],
                    "run_order": row["run_order"],
                    "actual_input_payload": row["actual_input_payload"],
                    "gold_fields_present": False,
                },
                "input_digest",
            )
        )
        route_gold.append(
            bind_digest(
                {
                    "schema_version": "gate1-p4-sealed-route-gold-v0.1",
                    "task_id": TASK_ID,
                    "case_id": row["case_id"],
                    "profile_id": row["profile_id"],
                    "gold_primary_action": row["gold_primary_action"],
                    "gold_primary_reason_category": row["gold_primary_reason_category"],
                    "gold_rationale": row["gold_rationale"],
                },
                "gold_digest",
            )
        )
    order = [
        bind_digest(
            {
                "schema_version": "gate1-p4-sealed-order-v0.1",
                "task_id": TASK_ID,
                "case_id": row["case_id"],
                "case_kind": "POSITIVE" if int(row["run_order"]) <= 20 else "ANOMALY",
                "run_order": row["run_order"],
            },
            "order_digest",
        )
        for row in sorted(
            positives + anomalies, key=lambda item: int(item["run_order"])
        )
    ]
    write_jsonl(ROOT / AUTHOR_REQUESTS, requests)
    write_jsonl(ROOT / ROUTE_INPUTS, route_inputs)
    write_jsonl(ROOT / ROUTE_GOLD, route_gold)
    write_jsonl(ROOT / RUN_ORDER, order)
    validation = {
        "p4_pre_freeze_validation": bind_digest(
            {
                "schema_version": "gate1-p4-pre-freeze-validation-v0.1",
                "task_id": TASK_ID,
                "positive_count": len(positives),
                "anomaly_count": len(anomalies),
                "profile_coverage": list(EXPECTED_PROFILES),
                "variant_counts": dict(
                    Counter(row["assigned_variant"] for row in positives)
                ),
                "anti_reuse": reuse,
                "validity_check_scope": "CONTRACT_CLOSURE_BOUNDARY_AND_DUPLICATION_ONLY",
                "expected_output_quality_was_not_considered": True,
            },
            "validation_digest",
        )
    }
    write_yaml(ROOT / CURATION_VALIDATION, validation)
    freeze = {
        "p4_hidden_input_freeze": bind_digest(
            {
                "schema_version": "gate1-p4-hidden-input-freeze-v0.1",
                "task_id": TASK_ID,
                "prompt_revision": PROMPT_REVISION,
                "tool_freeze_commit": lifecycle["tool_freeze_commit"],
                "author_platform_agent_id": author_agent_id,
                "curator_identity": {
                    key: receipt[key]
                    for key in (
                        "curator_identity_id",
                        "curator_platform_agent_id",
                        "curator_session_id",
                        "curator_run_id",
                    )
                },
                "frozen_file_hashes": {
                    path.as_posix(): sha256_file(ROOT / path)
                    for path in (
                        CURATED_POSITIVE,
                        CURATED_ANOMALY,
                        AUTHOR_REQUESTS,
                        ROUTE_INPUTS,
                        ROUTE_GOLD,
                        RUN_ORDER,
                        CURATOR_RECEIPT,
                        CURATION_VALIDATION,
                    )
                },
                "positive_count": 20,
                "anomaly_count": 20,
                "gold_physically_separate_from_route_input": True,
                "author_projection_excludes_gold_feedback_and_reviews": True,
                "case_replacement_allowed": False,
                "second_candidate_allowed": False,
                "all_cases_hidden_until_first_run": True,
            },
            "freeze_digest",
        )
    }
    write_yaml(ROOT / HIDDEN_FREEZE, freeze)
    lifecycle.update(
        {
            "state": "HIDDEN_FROZEN_PENDING_COMMIT",
            "hidden_created": True,
            "hidden_exposed": False,
            "author_platform_agent_id": author_agent_id,
        }
    )
    lifecycle["lifecycle_digest"] = object_digest(lifecycle, "lifecycle_digest")
    write_yaml(ROOT / LIFECYCLE, {"p4_lifecycle": lifecycle})
