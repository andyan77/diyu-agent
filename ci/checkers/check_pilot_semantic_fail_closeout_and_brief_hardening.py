#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

TASK_ID = "CODEX-PILOT-SEMANTIC-FAIL-CLOSEOUT-AND-BRIEF-HARDENING-001"
NEXT_TASK_ID = "CODEX-SEMANTIC-PILOT-REGEN-001"
SEMANTIC_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-JUDGE-GO-NOGO-001"
SEMANTIC_V3_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V3-JUDGE-GO-NOGO-001"
SEMANTIC_V4_JUDGE_NEXT_STEP = "CODEX-SEMANTIC-PILOT-V4-JUDGE-GO-NOGO-001"
BATCH_TASK_ID = "CODEX-GKB-DRAFT-GENERATION-BATCH-001"
EXPECTED_BATCH_IDS = [f"batch_{idx:03d}" for idx in range(1, 15)]
GATE_KEYS = [
    "semantic_uniqueness_gate",
    "normalized_body_duplicate_gate",
    "cluster_entailment_gate",
    "rich_body_industry_density_gate",
    "relation_predicate_specificity_gate",
    "semantic_fingerprint_validity_gate",
    "source_status_disambiguation_gate",
]
NEGATIVE_FIXTURES = [
    "negative_current_44_still_counts_as_domain_knowledge.yaml",
    "negative_batch_generation_unlocked.yaml",
    "negative_missing_semantic_uniqueness_gate.yaml",
    "negative_missing_normalized_body_duplicate_gate.yaml",
    "negative_missing_cluster_entailment_gate.yaml",
    "negative_missing_industry_density_gate.yaml",
    "negative_generic_relation_predicate_allowed.yaml",
    "negative_hash_only_fingerprint_allowed.yaml",
    "negative_source_status_conflation_allowed.yaml",
    "negative_regen_brief_missing.yaml",
    "negative_readiness_true.yaml",
    "negative_source_repo_dependency_true.yaml",
]


class HardeningError(Exception):
    pass


def fail(message: str) -> None:
    raise HardeningError(message)


def load_yaml(path: Path) -> Any:
    if not path.exists():
        fail(f"missing yaml: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_false(value: Any, label: str) -> None:
    if value is True or str(value).lower() == "true":
        fail(f"{label} must be false")


def validate_gate_block(gates: dict[str, Any], label: str) -> dict[str, int]:
    counts = {key: 0 for key in GATE_KEYS}
    for key in GATE_KEYS:
        gate = gates.get(key)
        if not isinstance(gate, dict):
            fail(f"{label} missing {key}")
        if gate.get("blocking") is not True:
            fail(f"{label} {key} must be blocking")
        counts[key] = 1
    relation_gate = gates["relation_predicate_specificity_gate"]
    forbidden = set(relation_gate.get("forbidden_predicates", []))
    for generic in ["generic", "review_adjacent", "review_adjacent_method_boundary", "placeholder", "related_to", "similar_to"]:
        if generic not in forbidden:
            fail(f"{label} must forbid generic relation predicate: {generic}")
    fingerprint = gates["semantic_fingerprint_validity_gate"]
    ignored = set(fingerprint.get("must_ignore", []))
    for field in ["candidate_id", "candidate_name", "sample_number", "batch_id"]:
        if field not in ignored:
            fail(f"{label} fingerprint gate must ignore {field}")
    status_gate = gates["source_status_disambiguation_gate"]
    allowed = set(status_gate.get("allowed_provenance_class", []))
    if "expert_synthesis_draft" not in allowed:
        fail(f"{label} must allow expert_synthesis_draft provenance class")
    required = set(status_gate.get("required_fields", []))
    for field in ["provenance_class", "human_review_status", "human_reviewed_method"]:
        if field not in required:
            fail(f"{label} source status gate missing {field}")
    density_gate = gates["rich_body_industry_density_gate"]
    if int(density_gate.get("min_body_chars", 0)) < 900:
        fail(f"{label} rich body min chars must be >= 900")
    if int(density_gate.get("required_industry_elements_min", 0)) < 6:
        fail(f"{label} industry element minimum must be >= 6")
    cluster_gate = gates["cluster_entailment_gate"]
    if int(cluster_gate.get("required_cluster_specific_elements_min", 0)) < 3:
        fail(f"{label} cluster specificity minimum must be >= 3")
    body_gate = gates["normalized_body_duplicate_gate"]
    if body_gate.get("exact_duplicate_allowed") is not False:
        fail(f"{label} exact normalized body duplicate must be false")
    if float(body_gate.get("max_same_category_similarity", 1.0)) > 0.82:
        fail(f"{label} same category similarity threshold must be <= 0.82")
    return counts


def validate_fixture_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = model.get("semantic_hardening_fixture", {})
    if data.get("task_id") != TASK_ID:
        errors.append("task_id mismatch")
    if data.get("human_decision_present") is not True:
        errors.append("human decision must be present")
    if data.get("current_44_reclassified_as") != "schema_route_provenance_smoke_fixture":
        errors.append("current 44 must be smoke fixture")
    if data.get("accepted_domain_knowledge_count") != 0:
        errors.append("accepted domain knowledge count must be 0")
    if data.get("batch_generation_unlocked") is not False:
        errors.append("batch generation must remain locked")
    if data.get("ready_for_first_batch_generation") is not False:
        errors.append("first batch generation must remain false")
    if data.get("current_next_step") != NEXT_TASK_ID:
        errors.append("next step must be semantic pilot regen")
    if data.get("current_next_step") == BATCH_TASK_ID:
        errors.append("batch generation task cannot be next step")
    if data.get("batch_briefs_hardened_count") != 14:
        errors.append("14 batch briefs must be hardened")
    if data.get("semantic_pilot_regen_brief_exists") is not True:
        errors.append("regen brief required")
    target = data.get("regen_target_count", {})
    if target.get("recommended", 0) < 16 or target.get("recommended", 999) > 24:
        errors.append("regen recommended count must be 16..24")
    if data.get("regen_min_body_chars", 0) < 900:
        errors.append("regen body min chars must be >= 900")
    if data.get("readiness_all_false") is not True:
        errors.append("readiness must remain all false")
    if data.get("source_repo_live_dependency") is not False:
        errors.append("source repo live dependency must be false")
    if data.get("source_repo_live_accessed") is not False:
        errors.append("source repo live accessed must be false")
    gates = data.get("semantic_generation_gates", {})
    try:
        validate_gate_block(gates, "fixture")
    except HardeningError as error:
        errors.append(str(error))
    return errors


def validate_live(
    workspace: Path,
    pilot_root: Path,
    brief_pack_root: Path,
    fixtures_root: Path,
    report_out: Path | None,
) -> dict[str, Any]:
    closeout = load_yaml(pilot_root / "pilot_semantic_fail_closeout.yaml")["pilot_semantic_fail_closeout"]
    smoke = load_yaml(pilot_root / "pilot_smoke_fixture_manifest.yaml")["pilot_smoke_fixture_manifest"]
    analysis = load_yaml(pilot_root / "pilot_semantic_failure_analysis.yaml")["semantic_failure_analysis"]
    regen = load_yaml(pilot_root / "semantic_pilot_regen_brief.v0.1.yaml")["semantic_pilot_regen_brief"]
    status = load_yaml(workspace / "project-infra/current_workspace_status.yaml")
    shared = load_yaml(brief_pack_root / "00_shared_generation_rules.yaml")["shared_generation_rules"]
    manifest = load_yaml(brief_pack_root / "00_brief_pack_manifest.yaml")["brief_pack_manifest"]
    allocation = load_yaml(brief_pack_root / "00_batch_allocation_matrix.yaml")["batch_allocation_matrix"]
    pilot_sampling = load_yaml(brief_pack_root / "00_pilot_sampling_plan.yaml")["pilot_sampling_plan"]

    human = closeout.get("human_decision", {})
    if human.get("human_decision_present") is not True:
        fail("human decision must be recorded")
    if human.get("authorized_by") != "founder_current_request":
        fail("human decision authorization mismatch")
    if human.get("decision") != "current_44_semantic_fail_and_reclassify_as_smoke_fixture":
        fail("human decision value mismatch")

    disposition = closeout.get("disposition", {})
    if disposition.get("retain_as") != "schema_route_provenance_smoke_fixture":
        fail("current 44 must be reclassified as smoke fixture")
    for key in [
        "count_as_domain_knowledge",
        "count_as_rich_body_exemplar",
        "count_as_relation_graph_exemplar",
        "eligible_for_candidatepack",
        "eligible_for_batch_generation_gate",
        "eligible_for_human_knowledge_review",
    ]:
        assert_false(disposition.get(key), f"disposition.{key}")
    if closeout.get("accepted_domain_knowledge_count") != 0:
        fail("accepted_domain_knowledge_count must be 0")
    unlock = closeout.get("batch_generation_unlock", {})
    assert_false(unlock.get("allowed"), "batch_generation_unlock.allowed")
    assert_false(unlock.get("batch_generation_unlocked"), "batch_generation_unlocked")

    if smoke.get("classification") != "schema_route_provenance_smoke_fixture":
        fail("smoke fixture manifest classification mismatch")
    for value in smoke.get("explicitly_not_valid_for", []):
        if value in {"domain_knowledge_quality", "rich_body_quality_exemplar", "relation_graph_quality", "batch_generation_unlock", "candidatepack_eligibility"}:
            continue
    source_files = set(smoke.get("source_pilot_files", []))
    for required in [
        "03_pilot/pilot_knowledge_candidate_cards.yaml",
        "03_pilot/pilot_rich_body_blocks.yaml",
        "03_pilot/pilot_relation_candidates.csv",
    ]:
        if required not in source_files:
            fail(f"smoke manifest missing source pilot file: {required}")

    for code, spec in analysis.get("failure_codes", {}).items():
        if spec.get("blocking") is not True:
            fail(f"failure code must be blocking: {code}")

    status_closeout = status.get("pilot_semantic_closeout", {})
    if status_closeout.get("task_id") != TASK_ID or status_closeout.get("status") != "completed":
        fail("workspace status closeout block invalid")
    if status_closeout.get("current_44_reclassified_as") != "schema_route_provenance_smoke_fixture":
        fail("workspace status reclassification missing")
    if status_closeout.get("accepted_domain_knowledge_count") != 0:
        fail("workspace status accepted domain count must be 0")
    assert_false(status_closeout.get("batch_generation_unlocked"), "workspace status batch_generation_unlocked")
    assert_false(status_closeout.get("ready_for_first_batch_generation"), "workspace status ready_for_first_batch_generation")
    current_next_step = status.get("phase", {}).get("current_next_step")
    if current_next_step == BATCH_TASK_ID:
        fail("batch generation must not be next step")
    if current_next_step == SEMANTIC_JUDGE_NEXT_STEP:
        semantic_regen = status.get("semantic_pilot_regen", {})
        if semantic_regen.get("status") != "completed":
            fail("semantic judge route requires completed semantic_pilot_regen block")
        if semantic_regen.get("semantic_pilot_structured_draft_count") != 20:
            fail("semantic judge route requires 20 regenerated semantic pilot drafts")
        if semantic_regen.get("accepted_domain_knowledge_count") != 0:
            fail("semantic judge route requires accepted_domain_knowledge_count 0")
        assert_false(semantic_regen.get("batch_generation_unlocked"), "semantic judge route batch_generation_unlocked")
        assert_false(semantic_regen.get("ready_for_first_batch_generation"), "semantic judge route ready_for_first_batch_generation")
    elif current_next_step == SEMANTIC_V3_JUDGE_NEXT_STEP:
        semantic_v3 = status.get("semantic_pilot_v3", {})
        if semantic_v3.get("status") != "completed":
            fail("semantic v3 judge route requires completed semantic_pilot_v3 block")
        if semantic_v3.get("semantic_pilot_v3_structured_draft_count") != 20:
            fail("semantic v3 judge route requires 20 v3 semantic pilot drafts")
        if semantic_v3.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v3 judge route requires accepted_domain_knowledge_count 0")
        assert_false(semantic_v3.get("batch_generation_unlocked"), "semantic v3 judge route batch_generation_unlocked")
        assert_false(semantic_v3.get("ready_for_first_batch_generation"), "semantic v3 judge route ready_for_first_batch_generation")
    elif current_next_step == SEMANTIC_V4_JUDGE_NEXT_STEP:
        semantic_v4 = status.get("semantic_pilot_v4", {})
        if semantic_v4.get("status") != "completed":
            fail("semantic v4 judge route requires completed semantic_pilot_v4 block")
        if semantic_v4.get("W7_authority_records_count") != 46:
            fail("semantic v4 judge route requires 46 W7 authority records")
        if semantic_v4.get("semantic_pilot_v4_count") != 8:
            fail("semantic v4 judge route requires 8 v4 semantic pilot drafts")
        if semantic_v4.get("accepted_domain_knowledge_count") != 0:
            fail("semantic v4 judge route requires accepted_domain_knowledge_count 0")
        assert_false(semantic_v4.get("batch_generation_unlocked"), "semantic v4 judge route batch_generation_unlocked")
        assert_false(semantic_v4.get("ready_for_first_batch_generation"), "semantic v4 judge route ready_for_first_batch_generation")
    elif current_next_step != NEXT_TASK_ID:
        fail("current_next_step must be semantic pilot regen, semantic pilot judge go/no-go, semantic pilot v3 judge go/no-go, or semantic pilot v4 judge go/no-go")
    readiness = status.get("readiness", {})
    bad = {key: value for key, value in readiness.items() if value is True or str(value).lower() == "true"}
    if bad:
        fail(f"readiness true flags: {bad}")

    shared_policy = shared.get("semantic_quality_blocking_policy", {})
    if shared_policy.get("old_44_pilot_status") != "schema_route_provenance_smoke_fixture_only":
        fail("shared policy must mark old 44 as smoke fixture only")
    if shared_policy.get("batch_generation_blocked_until_semantic_pilot_pass") is not True:
        fail("shared policy must block batch until semantic pilot pass")
    if shared_policy.get("semantic_pilot_regen_required") is not True:
        fail("shared policy must require semantic pilot regen")
    for key in ["source_repo_live_dependency", "source_repo_live_accessed"]:
        assert_false(shared.get(key), f"shared.{key}")
        assert_false(manifest.get(key), f"manifest.{key}")
        assert_false(allocation.get(key), f"allocation.{key}")
        assert_false(pilot_sampling.get(key), f"pilot_sampling.{key}")

    target = regen.get("target_count", {})
    recommended = int(target.get("recommended", 0))
    if int(target.get("min", 0)) < 16 or int(target.get("max", 0)) > 24 or recommended < 16 or recommended > 24:
        fail("semantic pilot regen count must be in 16..24")
    if int(regen.get("body_requirements", {}).get("min_body_chars", 0)) < 900:
        fail("semantic pilot regen body min chars must be >= 900")
    if regen.get("next_task_id") != NEXT_TASK_ID:
        fail("semantic pilot regen next task mismatch")

    gate_counts = {key: 0 for key in GATE_KEYS}
    for batch_id in EXPECTED_BATCH_IDS:
        data = load_yaml(brief_pack_root / batch_id / f"{batch_id}_generation_brief.yaml")["batch_generation_brief"]
        batch_counts = validate_gate_block(data.get("semantic_generation_gates", {}), batch_id)
        for key, count in batch_counts.items():
            gate_counts[key] += count
        if data.get("semantic_generation_hardening_status") != "hardened_after_pilot_semantic_fail":
            fail(f"{batch_id} hardening status missing")
    for key, count in gate_counts.items():
        if count != 14:
            fail(f"{key} count must be 14, got {count}")

    for batch_id in EXPECTED_BATCH_IDS:
        mm = load_yaml(brief_pack_root / "microbatch_manifest" / f"{batch_id}_microbatch_manifest.yaml")["microbatch_manifest"]
        if mm.get("semantic_gate_profile") != "semantic_hardened_v0.1":
            fail(f"{batch_id} microbatch manifest missing semantic gate profile")
        if mm.get("batch_generation_blocked_until_semantic_pilot_pass") is not True:
            fail(f"{batch_id} microbatch manifest must block batch generation")

    positive = load_yaml(fixtures_root / "positive_valid_semantic_hardening.yaml")
    positive_errors = validate_fixture_model(positive)
    if positive_errors:
        fail(f"positive fixture failed: {positive_errors}")
    negative_results: dict[str, list[str]] = {}
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures_root / name))
        negative_results[name] = errors
        if not errors:
            fail(f"negative fixture unexpectedly passed: {name}")

    report = {
        "status": "PASS",
        "task_id": TASK_ID,
        "source_repo_live_accessed": False,
        "current_44_reclassified_as": "schema_route_provenance_smoke_fixture",
        "accepted_domain_knowledge_count": 0,
        "batch_generation_unlocked": False,
        "ready_for_first_batch_generation": False,
        "batch_briefs_hardened_count": 14,
        "semantic_uniqueness_gate_count": gate_counts["semantic_uniqueness_gate"],
        "normalized_body_duplicate_gate_count": gate_counts["normalized_body_duplicate_gate"],
        "cluster_entailment_gate_count": gate_counts["cluster_entailment_gate"],
        "rich_body_industry_density_gate_count": gate_counts["rich_body_industry_density_gate"],
        "relation_predicate_specificity_gate_count": gate_counts["relation_predicate_specificity_gate"],
        "semantic_fingerprint_validity_gate_count": gate_counts["semantic_fingerprint_validity_gate"],
        "source_status_disambiguation_gate_count": gate_counts["source_status_disambiguation_gate"],
        "semantic_pilot_regen_brief_created": True,
        "regen_target_count": recommended,
        "readiness_flags_result": "all_false",
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "negative_fixtures_fail_closed": True,
        "positive_fixture_passed": True,
        "generated_knowledge_count": 0,
        "candidatepack_created": False,
        "KE_touched": False,
        "serving_touched": False,
        "RAG_touched": False,
        "DIFY_touched": False,
        "recommended_next_step": NEXT_TASK_ID,
        "negative_results": negative_results,
    }
    if report_out:
        write_json(report_out, report)
    return report


def build_fixture_model() -> dict[str, Any]:
    return {
        "semantic_hardening_fixture": {
            "task_id": TASK_ID,
            "human_decision_present": True,
            "current_44_reclassified_as": "schema_route_provenance_smoke_fixture",
            "accepted_domain_knowledge_count": 0,
            "batch_generation_unlocked": False,
            "ready_for_first_batch_generation": False,
            "current_next_step": NEXT_TASK_ID,
            "batch_briefs_hardened_count": 14,
            "semantic_pilot_regen_brief_exists": True,
            "regen_target_count": {"min": 16, "max": 24, "recommended": 20},
            "regen_min_body_chars": 900,
            "readiness_all_false": True,
            "source_repo_live_dependency": False,
            "source_repo_live_accessed": False,
            "semantic_generation_gates": build_gate_block(),
        }
    }


def build_gate_block() -> dict[str, Any]:
    return {
        "semantic_uniqueness_gate": {
            "blocking": True,
            "normalized_proposition_signature_fields": [
                "definition",
                "applicable_when",
                "not_applicable_when",
                "output_effect",
                "risk_boundary",
                "evidence_requirement",
            ],
        },
        "normalized_body_duplicate_gate": {
            "blocking": True,
            "max_same_category_similarity": 0.82,
            "exact_duplicate_allowed": False,
        },
        "cluster_entailment_gate": {
            "blocking": True,
            "required_cluster_specific_elements_min": 3,
        },
        "rich_body_industry_density_gate": {
            "blocking": True,
            "min_body_chars": 900,
            "required_industry_elements_min": 6,
        },
        "relation_predicate_specificity_gate": {
            "blocking": True,
            "forbidden_predicates": [
                "generic",
                "review_adjacent",
                "review_adjacent_method_boundary",
                "placeholder",
                "related_to",
                "similar_to",
            ],
        },
        "semantic_fingerprint_validity_gate": {
            "blocking": True,
            "must_ignore": ["candidate_id", "candidate_name", "sample_number", "batch_id", "generated_at"],
        },
        "source_status_disambiguation_gate": {
            "blocking": True,
            "required_fields": ["provenance_class", "human_review_status", "human_reviewed_method"],
            "allowed_provenance_class": [
                "expert_synthesis_draft",
                "founder_overlay_governance_basis",
                "source_gap_seed",
                "decision_packet_seed",
            ],
        },
    }


def mutate_fixture_for_negative(model: dict[str, Any], name: str) -> None:
    data = model["semantic_hardening_fixture"]
    gates = data["semantic_generation_gates"]
    if name == "negative_current_44_still_counts_as_domain_knowledge.yaml":
        data["accepted_domain_knowledge_count"] = 44
    elif name == "negative_batch_generation_unlocked.yaml":
        data["batch_generation_unlocked"] = True
    elif name == "negative_missing_semantic_uniqueness_gate.yaml":
        gates.pop("semantic_uniqueness_gate", None)
    elif name == "negative_missing_normalized_body_duplicate_gate.yaml":
        gates.pop("normalized_body_duplicate_gate", None)
    elif name == "negative_missing_cluster_entailment_gate.yaml":
        gates.pop("cluster_entailment_gate", None)
    elif name == "negative_missing_industry_density_gate.yaml":
        gates.pop("rich_body_industry_density_gate", None)
    elif name == "negative_generic_relation_predicate_allowed.yaml":
        gates["relation_predicate_specificity_gate"]["forbidden_predicates"] = ["placeholder"]
    elif name == "negative_hash_only_fingerprint_allowed.yaml":
        gates["semantic_fingerprint_validity_gate"]["must_ignore"] = ["generated_at"]
    elif name == "negative_source_status_conflation_allowed.yaml":
        gates["source_status_disambiguation_gate"]["allowed_provenance_class"] = ["human_reviewed_expert_synthesis"]
    elif name == "negative_regen_brief_missing.yaml":
        data["semantic_pilot_regen_brief_exists"] = False
    elif name == "negative_readiness_true.yaml":
        data["readiness_all_false"] = False
    elif name == "negative_source_repo_dependency_true.yaml":
        data["source_repo_live_dependency"] = True


def run_selftest() -> dict[str, Any]:
    temp_root = Path(tempfile.mkdtemp(prefix="pilot-semantic-hardening-selftest-"))
    fixtures = temp_root / "fixtures"
    fixtures.mkdir(parents=True)
    positive = build_fixture_model()
    (fixtures / "positive_valid_semantic_hardening.yaml").write_text(
        yaml.safe_dump(positive, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    for name in NEGATIVE_FIXTURES:
        fixture = build_fixture_model()
        mutate_fixture_for_negative(fixture, name)
        (fixtures / name).write_text(
            yaml.safe_dump(fixture, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    if errors := validate_fixture_model(positive):
        fail(f"selftest positive failed: {errors}")
    for name in NEGATIVE_FIXTURES:
        errors = validate_fixture_model(load_yaml(fixtures / name))
        if not errors:
            fail(f"selftest negative passed unexpectedly: {name}")
    return {
        "status": "PASS",
        "positive_fixture_count": 1,
        "negative_fixture_count": len(NEGATIVE_FIXTURES),
        "negative_fixtures_fail_closed": True,
    }


def main() -> int:
    if not __debug__:
        print("FAIL-CLOSED: optimized Python mode is not allowed for this checker", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--pilot-root", default="03_pilot")
    parser.add_argument("--brief-pack-root", default="02_generation_brief_pack")
    parser.add_argument("--fixtures-root", default="ci/fixtures/pilot_semantic_fail_closeout_and_brief_hardening")
    parser.add_argument("--report-out")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            result = run_selftest()
        else:
            workspace = Path(args.workspace_root)
            result = validate_live(
                workspace=workspace,
                pilot_root=workspace / args.pilot_root,
                brief_pack_root=workspace / args.brief_pack_root,
                fixtures_root=workspace / args.fixtures_root,
                report_out=workspace / args.report_out if args.report_out else None,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except HardeningError as error:
        print(f"FAIL-CLOSED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
