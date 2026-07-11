#!/usr/bin/env python3
"""Materialize the v0.2 component review snapshot from authored decisions."""

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


TASK_ID = "GKB-CONTROLLED-V2-COMPONENT-DOMAIN-REVIEW-20CP-RECLASSIFICATION-AND-HANDOFF-FREEZE-002"
BASELINE_HEAD = "84faff476c248d9277d8882f2c9e4aa402a96b22"

ROOT_S1 = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/"
    "midbatch_320_001/controlled_composition_v2_001"
)
TASK_DIR = ROOT_S1 / "component_review_20cp_and_handoff_002"
POLICY_PATH = TASK_DIR / "component_domain_review_policy.v0.2.yaml"
DECISIONS_PATH = TASK_DIR / "component_domain_review_decisions.v0.2.jsonl"
REGISTRY_PATH = TASK_DIR / "reviewed_reusable_component_registry.v0.2.jsonl"
COVERAGE_PATH = TASK_DIR / "content_product_component_coverage.v0.2.yaml"
HANDOFF_PATH = TASK_DIR / "gkb_orch_reviewed_component_handoff.v0.2.yaml"
RESULT_PATH = TASK_DIR / "component_review_20cp_and_handoff_result.v0.2.yaml"
FREEZER_PATH = TASK_DIR / "run_component_review_20cp_v002_freezer.py"
CHECKER_PATH = Path("ci/checkers/check_gkb_controlled_v2_component_review_20cp_v002.py")

S1_CANDIDATES_PATH = ROOT_S1 / "component_candidate_manifest.v0.1.jsonl"
S1_SELECTION_PATH = ROOT_S1 / "pilot_source_selection.v0.1.yaml"
S1_5_PROFILES_PATH = ROOT_S1 / "content_product_profile_20_completion_001/content_product_profiles.v0.2.yaml"
CLEAN_120_PATH = Path(
    "07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/"
    "clean_120_reference_corpus_freeze_001/founder_reviewed_clean_120_reference_corpus.v1.0.jsonl"
)

ROLE_TO_CLASS = {
    "scene": "scene_action_kernel",
    "trigger": "scene_action_kernel",
    "tension": "scene_action_kernel",
    "observable_action": "scene_action_kernel",
    "audience_facing_reasoning_move": "narrative_operator",
    "opening": "narrative_operator",
    "transition": "narrative_operator",
    "closing": "narrative_operator",
    "CTA": "narrative_operator",
    "professional_judgment": "role_perspective_voice",
    "spoken_line_intent": "role_perspective_voice",
    "visual_beat": "visual_audio_grammar",
    "capture_instruction": "visual_audio_grammar",
}

P0_CP_MAPPING = {
    "CP01": {"primary_capabilities": ["P0_02"], "auxiliary_capabilities": ["P0_03", "P0_04", "P0_01", "P0_05"]},
    "CP02": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_02"]},
    "CP03": {"primary_capability_options": ["P0_03", "P0_04"], "auxiliary_capabilities": ["P0_02"]},
    "CP04": {"primary_capabilities": ["P0_02"], "auxiliary_capabilities": ["P0_01", "P0_03", "P0_04"]},
    "CP05": {"primary_capabilities": ["P0_02"], "auxiliary_capabilities": ["P0_01"]},
    "CP06": {"primary_capabilities": ["P0_03"], "auxiliary_capabilities": ["P0_02", "P0_04"]},
    "CP07": {"primary_capability_options": ["P0_03", "P0_04"], "auxiliary_capabilities": ["P0_02", "P0_05"]},
    "CP08": {"primary_capabilities": ["P0_03"], "auxiliary_capabilities": ["P0_05"]},
    "CP09": {"primary_capabilities": ["P0_03"], "auxiliary_capabilities": ["P0_05", "P0_02"]},
    "CP10": {"primary_capabilities": ["P0_03"], "auxiliary_capabilities": ["P0_05", "P0_01"]},
    "CP11": {"primary_capabilities": ["P0_05"], "auxiliary_capabilities": ["P0_03", "P0_01", "P0_02"]},
    "CP12": {"primary_capabilities": ["P0_05"], "auxiliary_capabilities": ["P0_03"]},
    "CP13": {"primary_capabilities": ["P0_05"], "auxiliary_capabilities": ["P0_03", "P0_04"]},
    "CP14": {"primary_capabilities": ["P0_05"], "auxiliary_capabilities": ["P0_03"]},
    "CP15": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_05", "P0_02"]},
    "CP16": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_02", "P0_05", "P0_03"]},
    "CP17": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_03", "P0_02"]},
    "CP18": {"primary_capabilities": ["P0_04"], "auxiliary_capabilities": ["P0_02", "P0_01"]},
    "CP19": {"primary_capabilities": ["P0_01"], "auxiliary_capabilities": ["P0_02", "P0_03", "P0_04", "P0_05"]},
    "CP20": {"primary_capabilities": ["P0_01"], "auxiliary_capabilities": ["P0_05", "P0_04"]},
}

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


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)


def jsonl_text(records: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(record) + "\n" for record in records)


def source_p0_index(root: Path) -> dict[str, str]:
    selected = load_yaml(root / S1_SELECTION_PATH)["pilot_source_selection"]["selected_sources"]
    return {item["asset_id"]: item["p0_group"] for item in selected}


def cp_capabilities(cp_id: str) -> set[str]:
    mapping = P0_CP_MAPPING[cp_id]
    caps = set(mapping.get("primary_capabilities", []))
    caps.update(mapping.get("primary_capability_options", []))
    caps.update(mapping.get("auxiliary_capabilities", []))
    return caps


def profile_required_roles(profile: dict[str, Any]) -> list[str]:
    return [item["role"] for item in profile.get("required_component_roles", [])]


def profile_all_roles(profile: dict[str, Any]) -> set[str]:
    roles = set(profile_required_roles(profile))
    roles.update(item["role"] for item in profile.get("optional_component_roles", []))
    return roles


def role_allowed_cp_ids(role: str, p0_group: str, profiles: list[dict[str, Any]]) -> list[str]:
    allowed: list[str] = []
    for profile in profiles:
        cp_id = profile["content_product_type_id"]
        if role in profile_all_roles(profile) and p0_group in cp_capabilities(cp_id):
            allowed.append(cp_id)
    return allowed


def load_source_context(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    candidates = {row["component_id"]: row for row in load_jsonl(root / S1_CANDIDATES_PATH)}
    profiles = load_yaml(root / S1_5_PROFILES_PATH)["content_product_profile_registry"]["profiles"]
    p0_by_parent = source_p0_index(root)
    return candidates, profiles, p0_by_parent


def build_registry(
    root: Path,
    decisions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = decisions if decisions is not None else load_jsonl(root / DECISIONS_PATH)
    candidates, profiles, p0_by_parent = load_source_context(root)
    promoted: dict[str, dict[str, Any]] = {}
    lineage_by_target: dict[str, list[dict[str, str]]] = {}

    for decision in rows:
        candidate = candidates[decision["candidate_id"]]
        target = decision.get("target_reusable_component_id")
        if target:
            lineage_by_target.setdefault(target, []).append(
                {
                    "candidate_id": candidate["component_id"],
                    "candidate_digest": candidate["component_digest"],
                    "decision": decision["decision"]["enum"],
                }
            )
        if decision["decision"]["enum"] != "PROMOTE_AS_NEW":
            continue
        parent_ref = candidate["parent_refs"][0]
        role = candidate["component_role"]
        p0_group = p0_by_parent[parent_ref["parent_asset_id"]]
        asset_class = ROLE_TO_CLASS[role]
        readback = decision["candidate_semantic_readback"]
        assessment = decision["abstraction_assessment"]
        component = {
            "component_id": target,
            "component_version": "v0.2",
            "lifecycle": "reviewed_reusable_pending_guardian",
            "source_component_role": role,
            "source_P0_group": p0_group,
            "composition_asset_class": asset_class,
            "applicable_content_product_type_ids": role_allowed_cp_ids(role, p0_group, profiles),
            "abstract_payload": {
                "kind": f"{asset_class}:{role}:semantic_mechanism",
                "function": assessment["abstract_component_function"],
                "actual_mechanism": readback["actual_mechanism"],
                "reusable_elements": readback["reusable_elements"],
                "required_runtime_slots": assessment["required_runtime_slots"],
                "claim_boundary": assessment["claim_boundary"],
                "surface_policy": {
                    "generate_new_surface": True,
                    "parent_verbatim_allowed": False,
                    "source_sentence_template_allowed": False,
                },
            },
            "input_slot_contract": {
                "required": assessment["required_runtime_slots"],
                "degrade_when_missing": True,
            },
            "compatibility_tag_refs": [
                f"role:{role}",
                f"class:{asset_class}",
                f"capability:{p0_group}",
                "truth_boundary:pattern_only",
            ],
            "incompatible_condition_refs": [
                "missing_required_runtime_slots",
                "unsupported_role_authority",
                "unapproved_event_truth_mode",
            ],
            "forbidden_combination_rule_refs": [
                "no_fake_fact",
                "no_source_surface_copy",
                "no_runtime_plan_authority",
            ],
            "truth_boundary": {
                "ontology_truth": False,
                "factual_authority": False,
                "real_event_evidence": False,
                "brand_fact_source": False,
                "person_experience_source": False,
            },
            "domain_review_ref": {
                "decision_file": str(DECISIONS_PATH),
                "promoting_candidate_id": decision["candidate_id"],
            },
        }
        promoted[target] = component

    registry: list[dict[str, Any]] = []
    for target in sorted(promoted):
        component = promoted[target]
        lineage = sorted(lineage_by_target.get(target, []), key=lambda item: item["candidate_id"])
        component["lineage"] = {
            "source_candidate_refs": lineage,
            "promoted_candidate_count": sum(1 for item in lineage if item["decision"] == "PROMOTE_AS_NEW"),
            "merged_candidate_count": sum(1 for item in lineage if item["decision"] == "MERGE_INTO_REUSABLE"),
        }
        component["component_digest"] = object_digest(component, {"component_digest"})
        registry.append(component)
    return registry


def build_coverage(root: Path, registry: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = load_yaml(root / S1_5_PROFILES_PATH)["content_product_profile_registry"]["profiles"]
    records: list[dict[str, Any]] = []
    for profile in profiles:
        cp_id = profile["content_product_type_id"]
        required_roles = profile_required_roles(profile)
        refs = [
            {
                "component_id": item["component_id"],
                "component_digest": item["component_digest"],
                "source_component_role": item["source_component_role"],
                "composition_asset_class": item["composition_asset_class"],
                "source_P0_group": item["source_P0_group"],
            }
            for item in registry
            if cp_id in item["applicable_content_product_type_ids"]
        ]
        covered_roles = sorted({item["source_component_role"] for item in refs if item["source_component_role"] in required_roles})
        missing_roles = [role for role in required_roles if role not in covered_roles]
        status = "COMPLETE" if not missing_roles else ("PARTIAL" if covered_roles else "NONE")
        records.append(
            {
                "content_product_type_id": cp_id,
                "required_component_roles": required_roles,
                "covered_required_roles": covered_roles,
                "missing_required_roles": missing_roles,
                "reviewed_reusable_component_refs": refs,
                "component_contract_coverage": {"status": status},
                "fixture_calibration_coverage": {"status": "MISSING_EXPLICIT"},
                "ORCH_contract_design_eligibility": {
                    "true_only_when_required_component_roles_complete": status == "COMPLETE",
                    "authoritative_after_guardian_pass_only": True,
                },
                "runtime_content_generation_eligibility": False,
            }
        )
    summary = {
        "complete_count": sum(1 for row in records if row["component_contract_coverage"]["status"] == "COMPLETE"),
        "partial_count": sum(1 for row in records if row["component_contract_coverage"]["status"] == "PARTIAL"),
        "none_count": sum(1 for row in records if row["component_contract_coverage"]["status"] == "NONE"),
        "eligible_profile_ids": [
            row["content_product_type_id"]
            for row in records
            if row["component_contract_coverage"]["status"] == "COMPLETE"
        ],
        "ineligible_profile_ids": [
            row["content_product_type_id"]
            for row in records
            if row["component_contract_coverage"]["status"] != "COMPLETE"
        ],
        "fixture_gap_count": 20,
        "runtime_generation_eligible_profile_count": 0,
    }
    doc = {
        "content_product_component_coverage": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "coverage_records": records,
            "component_supply_gaps": [
                {
                    "composition_asset_class": asset_class,
                    "status": "NO_SUFFICIENT_89_CANDIDATE_EVIDENCE",
                    "may_auto_create_from_profile_description": False,
                }
                for asset_class in [
                    "style_vector",
                    "platform_expression",
                    "continuity_pattern",
                    "anti_pattern_control",
                ]
            ],
            "summary": summary,
        }
    }
    doc["content_product_component_coverage"]["coverage_digest"] = object_digest(
        doc["content_product_component_coverage"], {"coverage_digest"}
    )
    return doc


def build_handoff(
    root: Path,
    decisions_text: str,
    registry_text: str,
    coverage_doc: dict[str, Any],
    registry: list[dict[str, Any]],
) -> dict[str, Any]:
    coverage = coverage_doc["content_product_component_coverage"]
    handoff = {
        "gkb_orch_reviewed_component_handoff": {
            "handoff_kind": "GKB_REVIEWED_COMPONENT_HANDOFF_SNAPSHOT",
            "handoff_version": "v0.2",
            "freeze_status": "IMMUTABLE_CANDIDATE_SNAPSHOT_PENDING_GUARDIAN",
            "authoritative_after_guardian_pass_only": True,
            "producer": "GKB",
            "intended_consumer": "ORCH",
            "supersedes_failed_v001_as_authoritative_source": False,
            "v001_handoff_parent": None,
            "pinned_inputs": {
                "baseline_head_before": BASELINE_HEAD,
                "clean_120_sha256": sha256_file(root / CLEAN_120_PATH),
                "source_candidates_sha256": sha256_file(root / S1_CANDIDATES_PATH),
                "profiles_v0_2_sha256": sha256_file(root / S1_5_PROFILES_PATH),
                "review_decisions_sha256": sha256_text(decisions_text),
                "reviewed_registry_sha256": sha256_text(registry_text),
                "coverage_digest": coverage["coverage_digest"],
            },
            "component_contract_eligible_profile_ids": coverage["summary"]["eligible_profile_ids"],
            "component_contract_ineligible_profile_ids": coverage["summary"]["ineligible_profile_ids"],
            "runtime_excluded": [
                "Clean_120_body_text",
                "candidate_exact_payload",
                "derivation_spans",
                "domain_review_notes",
                "positive_fixture_body",
                "negative_fixture_body",
                "nine_GKB_pilot_bundles",
            ],
            "ownership": {
                "GKB_owns_profiles_and_component_versions": True,
                "GKB_may_create_canonical_CompositionPlan": False,
                "ORCH_owns_runtime_component_selection": True,
                "ORCH_owns_runtime_continuity_thread": True,
                "ORCH_owns_canonical_CompositionPlan": True,
                "DIFY_direct_GKB_consumption_allowed": False,
            },
            "state": {
                "handoff_integrity_frozen": False,
                "runtime_ingest_ready": False,
                "ORCH_integration_complete": False,
                "canonical_composition_plan_count": 0,
                "generation_invocation_count": 0,
                "audience_facing_content_count": 0,
            },
            "reviewed_reusable_component_count": len(registry),
            "readiness_flags": READINESS_FLAGS,
        }
    }
    handoff["gkb_orch_reviewed_component_handoff"]["handoff_digest"] = object_digest(
        handoff["gkb_orch_reviewed_component_handoff"], {"handoff_digest"}
    )
    return handoff


def max_common_substring_len(left: str, right: str) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    best = 0
    for char_left in left:
        current = [0]
        for index, char_right in enumerate(right, start=1):
            value = previous[index - 1] + 1 if char_left == char_right else 0
            current.append(value)
            best = max(best, value)
        previous = current
    return best


def string_leaves(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        leaves: list[str] = []
        for child in value:
            leaves.extend(string_leaves(child))
        return leaves
    if isinstance(value, dict):
        leaves = []
        for child in value.values():
            leaves.extend(string_leaves(child))
        return leaves
    return []


def compute_max_overlap(root: Path, registry: list[dict[str, Any]]) -> int:
    candidates = {row["component_id"]: row for row in load_jsonl(root / S1_CANDIDATES_PATH)}
    best = 0
    for component in registry:
        abstract_texts = string_leaves(component["abstract_payload"])
        source_texts: list[str] = []
        for ref in component["lineage"]["source_candidate_refs"]:
            candidate = candidates[ref["candidate_id"]]
            payload_content = candidate.get("payload", {}).get("content")
            source_texts.extend(string_leaves(payload_content))
            for span in candidate["parent_refs"][0].get("derivation_spans", []):
                source_texts.append(span.get("exact_text", ""))
        for left in abstract_texts:
            for right in source_texts:
                best = max(best, max_common_substring_len(left, right))
    return best


def build_result(
    root: Path,
    decisions: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    coverage_doc: dict[str, Any],
    handoff_doc: dict[str, Any],
    generated_digests: dict[str, str],
) -> dict[str, Any]:
    decision_counts = Counter(row["decision"]["enum"] for row in decisions)
    class_counts = Counter(item["composition_asset_class"] for item in registry)
    summary = coverage_doc["content_product_component_coverage"]["summary"]
    result = {
        "component_review_20cp_and_handoff_result": {
            "schema_version": "v0.2",
            "task_id": TASK_ID,
            "verdict": "S2_V002_TRUE_SEMANTIC_REVIEW_EXECUTED_PENDING_CLAUDE_GUARDIAN",
            "handoff_status": "IMMUTABLE_CANDIDATE_SNAPSHOT_PENDING_GUARDIAN",
            "authoritative_handoff_frozen": False,
            "CI_REMOTE_execution_allowed": False,
            "baseline_head_before": BASELINE_HEAD,
            "counts": {
                "reviewed_candidate_count": len(decisions),
                "reviewed_reusable_component_count": len(registry),
                "promoted_as_new_count": decision_counts["PROMOTE_AS_NEW"],
                "merged_candidate_count": decision_counts["MERGE_INTO_REUSABLE"],
                "source_specific_reference_only_count": decision_counts["SOURCE_SPECIFIC_REFERENCE_ONLY"],
                "needs_repair_count": decision_counts["NEEDS_REPAIR"],
                "rejected_count": decision_counts["REJECT"],
                "component_contract_complete_profile_count": summary["complete_count"],
                "component_contract_partial_profile_count": summary["partial_count"],
                "component_contract_none_profile_count": summary["none_count"],
                "fixture_gap_count": 20,
                "runtime_generation_eligible_profile_count": 0,
                "canonical_composition_plan_count": 0,
                "audience_facing_content_count": 0,
            },
            "decision_distribution": dict(sorted(decision_counts.items())),
            "composition_asset_class_distribution": dict(sorted(class_counts.items())),
            "component_contract_eligible_profile_ids": summary["eligible_profile_ids"],
            "component_contract_ineligible_profile_ids": summary["ineligible_profile_ids"],
            "max_verbatim_overlap_chars": compute_max_overlap(root, registry),
            "readiness_flags": READINESS_FLAGS,
            "generated_file_digests": generated_digests,
            "handoff_digest": handoff_doc["gkb_orch_reviewed_component_handoff"]["handoff_digest"],
            "blocker_ids": [],
            "not_proven": [
                "guardian_domain_review_pass",
                "handoff_authoritative_freeze",
                "all_20_profiles_component_complete",
                "fixture_gap_closed",
                "ORCH_integrated",
                "generation_600_or_3600_allowed",
            ],
        }
    }
    result["component_review_20cp_and_handoff_result"]["result_digest"] = object_digest(
        result["component_review_20cp_and_handoff_result"], {"result_digest"}
    )
    return result


def build_artifacts(
    root: Path,
    decision_rows: list[dict[str, Any]] | None = None,
) -> dict[Path, str]:
    decisions = decision_rows if decision_rows is not None else load_jsonl(root / DECISIONS_PATH)
    decisions = sorted(decisions, key=lambda row: row["candidate_id"])
    registry = build_registry(root, decisions)
    coverage_doc = build_coverage(root, registry)
    decisions_text = jsonl_text(decisions)
    registry_text = jsonl_text(registry)
    coverage_text = yaml_text(coverage_doc)
    handoff_doc = build_handoff(root, decisions_text, registry_text, coverage_doc, registry)
    handoff_text = yaml_text(handoff_doc)
    generated_digests = {
        str(POLICY_PATH): sha256_file(root / POLICY_PATH),
        str(DECISIONS_PATH): sha256_text(decisions_text),
        str(REGISTRY_PATH): sha256_text(registry_text),
        str(COVERAGE_PATH): sha256_text(coverage_text),
        str(HANDOFF_PATH): sha256_text(handoff_text),
        str(FREEZER_PATH): sha256_file(root / FREEZER_PATH),
        str(CHECKER_PATH): sha256_file(root / CHECKER_PATH) if (root / CHECKER_PATH).exists() else "CHECKER_NOT_PRESENT",
    }
    result_doc = build_result(root, decisions, registry, coverage_doc, handoff_doc, generated_digests)
    return {
        DECISIONS_PATH: decisions_text,
        REGISTRY_PATH: registry_text,
        COVERAGE_PATH: coverage_text,
        HANDOFF_PATH: handoff_text,
        RESULT_PATH: yaml_text(result_doc),
    }


def write_artifacts(root: Path) -> None:
    for rel_path, text in build_artifacts(root).items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def check_artifacts(root: Path) -> list[str]:
    errors: list[str] = []
    for rel_path, expected_text in build_artifacts(root).items():
        path = root / rel_path
        if not path.exists():
            errors.append(f"missing {rel_path}")
        elif path.read_text(encoding="utf-8") != expected_text:
            errors.append(f"content mismatch {rel_path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.write:
        write_artifacts(root)
    errors = check_artifacts(root) if args.check else []
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
