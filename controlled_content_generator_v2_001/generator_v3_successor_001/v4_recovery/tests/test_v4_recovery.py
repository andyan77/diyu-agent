#!/usr/bin/env python3
"""Deterministic positive and negative tests for Gate1 v4 recovery."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
V4 = HERE.parents[1]
GENERATOR_DIR = HERE.parents[2]
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(GENERATOR_DIR))

from v4_recovery import (author_contract, contract, deterministic_gates,
                         material_policy, metrics, request_builder, runner,
                         telemetry, test_allocator)


def evidence_span(source_id: str, source_text: str, quote: str) -> dict:
    char_start = source_text.index(quote)
    byte_start = len(source_text[:char_start].encode("utf-8"))
    return {
        "source_id": source_id,
        "byte_start": byte_start,
        "byte_end": byte_start + len(quote.encode("utf-8")),
        "quote": quote,
    }


def raw_material(scenario_id: str = "CASE-CP01-001", profile_id: str = "CP01") -> dict:
    source_id = f"{scenario_id}-SRC-1"
    source_text = "工作台记录一件样衣已完成缝份检查；检查使用了一把镊子；颜色未复核。"
    return {
        "scenario_id": scenario_id,
        "profile_id": profile_id,
        "sources": [
            {"source_id": source_id, "source_text": source_text},
        ],
        "authorizations": [
            {"authorization_id": f"{scenario_id}-AUTH-1",
             "scope": "仅限合成资格测试，可公开去身份的工作台记录。"},
        ],
        "facts": [
            {"fact_id": f"{scenario_id}-F1", "slot_id": "observed_action",
             "fact_value": "工作台记录一件样衣已完成缝份检查。",
             "source_ids": [source_id],
             "evidence_spans": [evidence_span(
                 source_id, source_text, "工作台记录一件样衣已完成缝份检查")],
             "authorization_ids": [f"{scenario_id}-AUTH-1"],
             "surface_policy": "MUST_SURFACE", "conditions": [],
             "prohibited_surface_terms": []},
            {"fact_id": f"{scenario_id}-F2", "slot_id": "optional_context",
             "fact_value": "检查使用了一把镊子。",
             "source_ids": [source_id],
             "evidence_spans": [evidence_span(
                 source_id, source_text, "检查使用了一把镊子")],
             "authorization_ids": [f"{scenario_id}-AUTH-1"],
             "surface_policy": "MAY_SURFACE", "conditions": [],
             "prohibited_surface_terms": []},
            {"fact_id": f"{scenario_id}-F3", "slot_id": "control_boundary",
             "fact_value": "颜色没有复核，禁止称颜色准确。",
             "source_ids": [source_id],
             "evidence_spans": [evidence_span(
                 source_id, source_text, "颜色未复核")],
             "authorization_ids": [f"{scenario_id}-AUTH-1"],
             "surface_policy": "CONTROL_ONLY", "conditions": ["颜色未复核"],
             "prohibited_surface_terms": ["颜色准确"]},
        ],
    }


def scenario(scenario_id: str = "CASE-CP01-001", profile_id: str = "CP01") -> dict:
    return {"scenario_id": scenario_id, "profile_id": profile_id,
            "user_goal": "帮助读者看懂一次样衣检查。",
            "forbidden_inferences": ["不得外推颜色准确"]}


def allocation_case(case: dict, material: dict) -> dict:
    value = copy.deepcopy(case)
    value["scenario_digest"] = test_allocator.scenario_digest_for_case(case)
    value["material_packet_digest"] = material["material_digest"]
    value["evidence_surface_policy"] = [
        {"reference_assertion_id": fact["fact_id"],
         "policy": fact["surface_policy"],
         "reason_code": f"EXPLICIT_{fact['surface_policy']}"}
        for fact in material["facts"]
    ]
    value["paired_assignment_id"] = None
    return value


def make_request(batch_id: str = "BATCH-A") -> tuple[dict, dict, dict, dict]:
    case = scenario()
    material = material_policy.normalize_material(raw_material())
    assignment = test_allocator.allocate_test_assignments(
        [allocation_case(case, material)], "ASSIGNMENT-SET-1")[0]
    request = request_builder.build_request(
        case, material, assignment, batch_id=batch_id, run_id="RUN-1",
        author_identity="AUTHOR-1", model_config_ref="MODEL-CONFIG-1")
    return case, material, assignment, request


def make_raw(request: dict, *, body_text: str | None = None,
             body_fact_ids: list[str] | None = None) -> dict:
    must = request["surface_policy"]["must_surface_fact_ids"][0]
    body = body_text or "工作台记录显示，这一件样衣已经完成缝份检查。"
    body_ids = [must] if body_fact_ids is None else body_fact_ids
    disclosure = "本条为合成测试内容，不代表真实人物或门店。"
    title = "工作台上的一件检查记录"
    visual = ["镜头只拍工作台、样衣和检查记录。"]
    return {
        "schema_version": contract.RAW_OUTPUT_SCHEMA,
        "request_id": request["request_id"],
        "run_id": request["run_id"],
        "attempt_id": f"{request['request_id']}:attempt:1",
        "attempt_index": 1,
        "title": title,
        "body": [body],
        "spoken_lines": [],
        "cta": "",
        "visual_execution": visual,
        "audio_execution": [],
        "synthetic_disclosure": disclosure,
        "surface_units": [
            {"surface_kind": "synthetic_disclosure", "text": disclosure,
             "fact_ids": []},
            {"surface_kind": "title", "text": title, "fact_ids": [must]},
            {"surface_kind": "body", "text": body, "fact_ids": body_ids},
            {"surface_kind": "visual_execution", "text": visual[0],
             "fact_ids": [must]},
        ],
        "author_attestation": copy.deepcopy(author_contract.EXPECTED_ATTESTATION),
    }


def reviews(output: dict, *, content_grade: str = "B", formulaic: bool = False,
            fact_approved: bool = True, fact_vetoes: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    content = [{"request_id": output["request_id"],
                "output_digest": output["output_digest"],
                "grade": content_grade, "approved": content_grade in {"A", "B"},
                "formulaic_or_near_duplicate": formulaic,
                "hard_veto_codes": []}]
    fact = [{"request_id": output["request_id"],
             "output_digest": output["output_digest"],
             "fact_approved": fact_approved,
             "hard_veto_codes": fact_vetoes or []}]
    return content, fact


def full_event(request: dict, output: dict) -> dict:
    return telemetry.make_event(
        event_id="EVENT-1", run_id=request["run_id"], batch_id=request["batch_id"],
        stage="AUTHOR_GENERATION", operation_kind="AUTHOR_GENERATION",
        request_id=request["request_id"], attempt_index=1,
        status="SUCCESS", started_at="2026-07-16T12:00:00+00:00",
        completed_at="2026-07-16T12:00:01+00:00",
        input_digest=request["request_digest"], output_digest=output["output_digest"],
        provider_call_id="provider-call-0001",
        reviewer_minutes=0,
        model_config={"provider": "internal", "model_family": "test-model",
                      "model_revision": "test-model-2026-07-16",
                      "reasoning_effort": "high", "temperature": 0,
                      "top_p": 1, "seed": 7},
        usage={"input_tokens": 10, "cached_input_tokens": 2,
               "output_tokens": 5, "reasoning_tokens": 1, "total_tokens": 15},
        cost={"amount": 0.0123, "currency": "USD", "rate_card_ref": "RATE-1"},
    )


def stage_event(request: dict, *, event_id: str, operation_kind: str,
                request_id: str, input_digest: str, output_digest: str,
                reviewer_minutes: float = 0) -> dict:
    return telemetry.make_event(
        event_id=event_id, run_id=request["run_id"], batch_id=request["batch_id"],
        stage=telemetry.OPERATION_STAGES[operation_kind],
        operation_kind=operation_kind, request_id=request_id, attempt_index=0,
        status="SUCCESS", started_at="2026-07-16T12:00:01+00:00",
        completed_at="2026-07-16T12:00:02+00:00",
        input_digest=input_digest, output_digest=output_digest,
        provider_call_id=f"receipt-{event_id}", reviewer_minutes=reviewer_minutes,
        model_config={"provider": "local", "model_family": "deterministic-test",
                      "model_revision": "deterministic-test-v1",
                      "reasoning_effort": "none", "temperature": 0,
                      "top_p": 1, "seed": 0},
        usage={"input_tokens": 0, "cached_input_tokens": 0,
               "output_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0},
        cost={"amount": 0, "currency": "USD",
              "rate_card_ref": "LOCAL-ZERO-COST-V1"},
    )


def qualification_events(request: dict, output: dict, gate: dict,
                         content: list[dict], fact: list[dict],
                         batch_metrics: dict) -> list[dict]:
    return [
        full_event(request, output),
        stage_event(
            request, event_id="EVENT-GATE", operation_kind="DETERMINISTIC_GATE",
            request_id=request["request_id"], input_digest=output["output_digest"],
            output_digest=gate["report_digest"]),
        stage_event(
            request, event_id="EVENT-CONTENT", operation_kind="CONTENT_REVIEW",
            request_id=request["request_id"], input_digest=output["output_digest"],
            output_digest=telemetry.review_record_digest(content[0]),
            reviewer_minutes=1.25),
        stage_event(
            request, event_id="EVENT-FACT", operation_kind="FACT_REVIEW",
            request_id=request["request_id"], input_digest=output["output_digest"],
            output_digest=telemetry.review_record_digest(fact[0]),
            reviewer_minutes=1.0),
        stage_event(
            request, event_id="EVENT-METRICS", operation_kind="METRICS_AGGREGATION",
            request_id=f"BATCH::{request['batch_id']}",
            input_digest=telemetry.evaluation_input_digest(gate, content, fact),
            output_digest=batch_metrics["metrics_digest"]),
    ]


def run_manifest_for(request: dict, output: dict, summary: dict) -> dict:
    return telemetry.build_run_manifest(
        run_id=request["run_id"], stage_gate="GATE1_QUALIFICATION",
        batch_id=request["batch_id"], schema_version_ref=contract.REQUEST_SCHEMA,
        content_product_profile_version="CP-PROFILES-V1",
        evaluation_case_set_version="CASESET-V1",
        checker_versions={"v4_recovery": contract.RULE_VERSION},
        model_or_engine_config_ref=telemetry.model_config_binding_ref([request]),
        randomization_config={"seed": 7, "batch_id_affects_assignment": False},
        input_manifest_ref="memory://requests",
        input_manifest_digest=telemetry.object_manifest_digest(
            [request], id_field="request_id", digest_field="request_digest"),
        output_manifest_ref="memory://outputs",
        output_manifest_digest=telemetry.object_manifest_digest(
            [output], id_field="request_id", digest_field="output_digest"),
        started_at="2026-07-16T12:00:00+00:00",
        completed_at="2026-07-16T12:00:02+00:00",
        human_review_batch_ref="memory://reviews",
        telemetry_summary_digest=summary["summary_digest"],
    )


class AllocationTests(unittest.TestCase):
    def test_strategy_covers_all_profiles_once(self) -> None:
        config = test_allocator.load_family_strategies()
        profiles = [profile for family in config["families"] for profile in family["profiles"]]
        self.assertEqual(set(profiles), set(test_allocator.PROFILE_IDS))
        self.assertEqual(len(profiles), 20)
        overrides = {
            profile
            for family in config["families"]
            for profile in family["profile_strategy_overrides"]
        }
        self.assertEqual(overrides, set(test_allocator.FROZEN_LINEAR_PROFILES))

    def test_focus_profiles_use_only_frozen_linear_overrides(self) -> None:
        config = test_allocator.load_family_strategies()
        override_axes = {
            profile_id: override["assignment_axes"]
            for family in config["families"]
            for profile_id, override in family["profile_strategy_overrides"].items()
        }
        family_entry_values = {
            value
            for family in config["families"]
            for value in family["assignment_axes"]["entry_lens"]
        }
        cases = []
        for index, profile_id in enumerate(test_allocator.PROFILE_IDS, 1):
            scenario_id = f"CASE-{profile_id}-001"
            case = scenario(scenario_id, profile_id)
            material = material_policy.normalize_material(
                raw_material(scenario_id, profile_id))
            cases.append(allocation_case(case, material))
        assignments = test_allocator.allocate_test_assignments(cases, "SET-ALL-PROFILES")
        for assignment in assignments:
            dna = assignment["test_dna"]
            if assignment["profile_id"] in test_allocator.FROZEN_LINEAR_PROFILES:
                self.assertEqual(dna["strategy_source"], "PROFILE_OVERRIDE")
                self.assertTrue(dna["strategy_frozen"])
                for axis in test_allocator.AXES:
                    self.assertIn(dna[axis], override_axes[assignment["profile_id"]][axis])
                self.assertNotIn(dna["entry_lens"], family_entry_values)
            else:
                self.assertEqual(dna["strategy_source"], "FAMILY_DEFAULT")
                self.assertFalse(dna["strategy_frozen"])

    def test_assignment_is_batch_independent_and_control_aligned(self) -> None:
        case, material, assignment, request_a = make_request("BATCH-A")
        assignment_again = test_allocator.allocate_test_assignments(
            [allocation_case(case, material)], "ASSIGNMENT-SET-1")[0]
        request_b = request_builder.build_request(
            case, material, assignment_again, batch_id="BATCH-B", run_id="RUN-2",
            author_identity="AUTHOR-1", model_config_ref="MODEL-CONFIG-1")
        self.assertEqual(assignment, assignment_again)
        self.assertEqual(request_a["assignment_digest"], request_b["assignment_digest"])
        self.assertNotIn("batch_id", assignment)
        fixed = {
            "object_type": "gate1_test_assignment",
            "stage_scope": "GATE1_QUALIFICATION_ONLY",
            "not_formal_content_composition_plan": True,
            "runtime_consumable": False, "publishable": False,
            "binds_enterprise_runtime_input": False, "counts_toward_300": False,
        }
        for key, value in fixed.items():
            self.assertEqual(assignment[key], value)
        self.assertEqual(assignment["material_packet_digest"], material["material_digest"])

    def test_assignment_allows_empty_forbidden_inferences(self) -> None:
        case = scenario()
        case["forbidden_inferences"] = []
        material = material_policy.normalize_material(raw_material())
        assignment = test_allocator.allocate_test_assignments(
            [allocation_case(case, material)], "SET-EMPTY-FORBIDDEN")[0]
        self.assertEqual(assignment["forbidden_inferences"], [])
        test_allocator.validate_assignment(assignment)

    def test_stale_scenario_digest_is_rejected(self) -> None:
        case = scenario()
        case["scenario_digest"] = test_allocator.scenario_digest_for_case(case)
        case["user_goal"] = "摘要冻结后被改写"
        with self.assertRaisesRegex(contract.ContractError, "SCENARIO_DIGEST"):
            test_allocator.scenario_digest_for_case(case)

    def test_assignment_input_order_is_deterministic_and_dna_unique(self) -> None:
        cases, materials = [], []
        for suffix in ("001", "002", "003"):
            case = scenario(f"CASE-CP01-{suffix}")
            material = material_policy.normalize_material(raw_material(case["scenario_id"]))
            cases.append(allocation_case(case, material))
            materials.append(material)
        first = test_allocator.allocate_test_assignments(cases, "SET-X")
        second = test_allocator.allocate_test_assignments(list(reversed(cases)), "SET-X")
        self.assertEqual(first, second)
        dna = [contract.canonical_json(row["test_dna"]) for row in first]
        self.assertEqual(len(dna), len(set(dna)))

    def test_assignment_rejected_if_masquerading_or_fixed_value_changes(self) -> None:
        _, _, assignment, _ = make_request()
        bad = copy.deepcopy(assignment)
        bad["not_formal_content_composition_plan"] = False
        contract.close_digest(bad, "assignment_digest")
        with self.assertRaisesRegex(contract.ContractError, "FORMAL_CONTENT|FIXED"):
            test_allocator.validate_assignment(bad)

    def test_r5_legacy_mismatch_is_90_of_120_and_read_only(self) -> None:
        scenarios_path, requests_path = runner.historical_r5_paths(REPO_ROOT)
        before = (scenarios_path.read_bytes(), requests_path.read_bytes())
        report = test_allocator.diagnose_legacy_r5_plan_mismatch(
            scenarios_path, requests_path)
        after = (scenarios_path.read_bytes(), requests_path.read_bytes())
        self.assertEqual(report["request_count"], 120)
        self.assertEqual(report["mismatch_count"], 90)
        self.assertEqual(report["match_count"], 30)
        self.assertEqual(before, after)

    def test_capacity_without_all_real_profile_material_is_not_evaluated(self) -> None:
        self.assertEqual(
            test_allocator.audit_profile_capacity([], [])["overall_status"],
            "NOT_EVALUATED",
        )

    def test_capacity_counts_observed_material_bound_assignments_not_cartesian_pool(self) -> None:
        cases, materials = [], []
        for profile_id in test_allocator.PROFILE_IDS:
            scenario_id = f"CAPACITY-{profile_id}-001"
            case = scenario(scenario_id, profile_id)
            material = material_policy.normalize_material(
                raw_material(scenario_id, profile_id))
            materials.append(material)
            cases.append(allocation_case(case, material))
        assignments = test_allocator.allocate_test_assignments(
            cases, "SET-CAPACITY-OBSERVED")
        material_by_id = {material["scenario_id"]: material for material in materials}
        legality = [test_allocator.make_capacity_legality_record(
            assignment, material_by_id[assignment["scenario_id"]],
            assessor_identity="CAPACITY-ASSESSOR-1",
            assessment_evidence_ref=f"memory://{assignment['assignment_id']}",
            material_and_constraints_support_assignment=True,
        ) for assignment in assignments]
        report = test_allocator.audit_profile_capacity(
            assignments, materials, legality_records=legality)
        self.assertEqual(report["overall_status"], "REQUEST_CURATION")
        self.assertFalse(report["theoretical_cartesian_capacity_used"])
        self.assertFalse(report["buffer_target_is_gate"])
        for row in report["profiles"].values():
            self.assertEqual(row["effective_capacity_count"], 1)
            self.assertEqual(row["minimum_required"], 12)
            self.assertEqual(row["buffer_target"], 15)
            self.assertEqual(row["status"], "REQUEST_CURATION")

    def test_capacity_rejects_id_renamed_semantic_material_clones(self) -> None:
        cases, materials = [], []
        for profile_id in test_allocator.PROFILE_IDS:
            for item_index in range(1, 13):
                scenario_id = f"CLONE-{profile_id}-{item_index:03d}"
                case = scenario(scenario_id, profile_id)
                material = material_policy.normalize_material(
                    raw_material(scenario_id, profile_id))
                materials.append(material)
                cases.append(allocation_case(case, material))
        assignments = test_allocator.allocate_test_assignments(
            cases, "SET-CAPACITY-CLONES")
        material_by_id = {material["scenario_id"]: material for material in materials}
        legality = [test_allocator.make_capacity_legality_record(
            assignment, material_by_id[assignment["scenario_id"]],
            assessor_identity="CAPACITY-ASSESSOR-1",
            assessment_evidence_ref=f"memory://{assignment['assignment_id']}",
            material_and_constraints_support_assignment=True,
        ) for assignment in assignments]
        report = test_allocator.audit_profile_capacity(
            assignments, materials, legality_records=legality)
        self.assertEqual(report["overall_status"], "REQUEST_CURATION")
        for row in report["profiles"].values():
            self.assertEqual(row["observed_valid_assignment_count"], 12)
            self.assertEqual(row["unique_semantic_material_count"], 1)
            self.assertEqual(row["effective_capacity_count"], 1)
            self.assertFalse(row["minimum_met"])


class MaterialAndRequestTests(unittest.TestCase):
    def test_surface_policy_is_sparse_but_control_dense(self) -> None:
        _, material, _, request = make_request()
        policy = request["surface_policy"]
        self.assertEqual(len(policy["must_surface_fact_ids"]), 1)
        self.assertEqual(len(policy["may_surface_fact_ids"]), 1)
        self.assertEqual(len(policy["control_only_fact_ids"]), 1)
        self.assertEqual(set(policy["author_visible_fact_ids"]),
                         {fact["fact_id"] for fact in material["facts"]})

    def test_fact_digest_tamper_is_rejected(self) -> None:
        raw = raw_material()
        raw["facts"][0]["fact_value_digest"] = "0" * 64
        with self.assertRaisesRegex(contract.ContractError, "FACT_DIGEST"):
            material_policy.normalize_material(raw)

    def test_fact_requires_exact_source_evidence_span(self) -> None:
        raw = raw_material()
        raw["facts"][0]["evidence_spans"][0]["quote"] = "粗棉纹"
        with self.assertRaisesRegex(contract.ContractError,
                                    "EVIDENCE_QUOTE_MISMATCH"):
            material_policy.normalize_material(raw)

    def test_reclosed_material_cannot_tamper_exact_evidence_span(self) -> None:
        material = material_policy.normalize_material(raw_material())
        bad = copy.deepcopy(material)
        bad["facts"][0]["evidence_spans"][0]["quote"] = "棉层"
        contract.close_digest(bad, "material_digest")
        with self.assertRaisesRegex(contract.ContractError,
                                    "EVIDENCE_QUOTE_MISMATCH"):
            material_policy.validate_material(bad)

    def test_reclosed_material_without_must_surface_is_rejected(self) -> None:
        material = material_policy.normalize_material(raw_material())
        bad = copy.deepcopy(material)
        for fact in bad["facts"]:
            if fact["surface_policy"] == "MUST_SURFACE":
                fact["surface_policy"] = "MAY_SURFACE"
        contract.close_digest(bad, "material_digest")
        with self.assertRaisesRegex(contract.ContractError, "MATERIAL_NO_MUST"):
            material_policy.validate_material(bad)

    def test_reclosed_material_with_duplicate_source_is_rejected(self) -> None:
        material = material_policy.normalize_material(raw_material())
        bad = copy.deepcopy(material)
        bad["sources"].append(copy.deepcopy(bad["sources"][0]))
        contract.close_digest(bad, "material_digest")
        with self.assertRaisesRegex(contract.ContractError, "SOURCE_DUP"):
            material_policy.validate_material(bad)

    def test_request_assignment_material_digest_closure(self) -> None:
        _, _, _, request = make_request()
        bad = copy.deepcopy(request)
        bad["material_digest"] = "0" * 64
        contract.close_digest(bad, "request_digest")
        with self.assertRaisesRegex(contract.ContractError, "MATERIAL_DIGEST"):
            request_builder.validate_request(bad)

    def test_feedback_retry_is_forbidden_even_with_recomputed_digest(self) -> None:
        _, _, _, request = make_request()
        bad = copy.deepcopy(request)
        bad["prior_feedback"] = ["改一下结尾"]
        contract.close_digest(bad, "request_digest")
        with self.assertRaisesRegex(contract.ContractError, "FEEDBACK_FORBIDDEN"):
            request_builder.validate_request(bad)

    def test_output_contract_cannot_add_feedback_escape_hatch(self) -> None:
        _, _, _, request = make_request()
        bad = copy.deepcopy(request)
        bad["author_output_contract"]["feedback_channel"] = "ALLOW_REWRITE"
        contract.close_digest(bad, "request_digest")
        with self.assertRaisesRegex(contract.ContractError, "OUTPUT_CONTRACT_FIELDS"):
            request_builder.validate_request(bad)


class AuthorAndGateTests(unittest.TestCase):
    def test_first_attempt_serializes_and_may_fact_can_be_omitted(self) -> None:
        _, _, _, request = make_request()
        raw = make_raw(request)
        output = author_contract.serialize(raw, request)
        report = deterministic_gates.gate_batch([output], [request])
        self.assertEqual(report["machine_hard_fail_count"], 0)
        self.assertTrue(report["whole_batch_machine_hard_veto_zero"])

    def test_known_risk_claims_without_source_support_are_hard_vetoes(self) -> None:
        _, _, _, request = make_request()
        body = "这件样衣呈粗棉纹，里面是绗缝的棉层，针脚密到反复套脱不走形。"
        output = author_contract.serialize(make_raw(request, body_text=body), request)
        report = deterministic_gates.gate_batch([output], [request])
        codes = report["per_output"][0]["hard_veto_codes"]
        for term in ("粗棉纹", "绗缝", "棉层", "针脚密", "反复套脱", "不走形"):
            self.assertTrue(any(code.endswith(f":{term}") for code in codes), term)
        self.assertFalse(report["whole_batch_machine_hard_veto_zero"])

    def test_fact_value_alone_cannot_authorize_known_risk_claim(self) -> None:
        raw = raw_material()
        raw["facts"][1]["fact_value"] = "检查记录称样衣有棉层。"
        material = material_policy.normalize_material(raw)
        case = scenario()
        assignment = test_allocator.allocate_test_assignments(
            [allocation_case(case, material)], "ASSIGNMENT-SET-CLAIM")[0]
        request = request_builder.build_request(
            case, material, assignment, batch_id="BATCH-CLAIM", run_id="RUN-CLAIM",
            author_identity="AUTHOR-1", model_config_ref="MODEL-CONFIG-1")
        may_id = request["surface_policy"]["may_surface_fact_ids"][0]
        output = author_contract.serialize(make_raw(
            request, body_text="检查记录称样衣有棉层。", body_fact_ids=[may_id]), request)
        codes = deterministic_gates.gate_batch(
            [output], [request])["per_output"][0]["hard_veto_codes"]
        self.assertIn("HV_UNSUPPORTED_DETERMINISTIC_CLAIM:fiber_or_composition:棉层",
                      codes)

    def test_source_and_fact_value_together_authorize_known_risk_claim(self) -> None:
        raw = raw_material()
        source = raw["sources"][0]
        source["source_text"] += "补充记录显示样衣有棉层。"
        raw["facts"][1]["fact_value"] = "补充记录显示样衣有棉层。"
        raw["facts"][1]["evidence_spans"] = [evidence_span(
            source["source_id"], source["source_text"], "补充记录显示样衣有棉层")]
        material = material_policy.normalize_material(raw)
        case = scenario()
        assignment = test_allocator.allocate_test_assignments(
            [allocation_case(case, material)], "ASSIGNMENT-SET-CLAIM-SUPPORTED")[0]
        request = request_builder.build_request(
            case, material, assignment, batch_id="BATCH-CLAIM-SUPPORTED",
            run_id="RUN-CLAIM-SUPPORTED", author_identity="AUTHOR-1",
            model_config_ref="MODEL-CONFIG-1")
        may_id = request["surface_policy"]["may_surface_fact_ids"][0]
        output = author_contract.serialize(make_raw(
            request, body_text="补充记录显示样衣有棉层。", body_fact_ids=[may_id]), request)
        codes = deterministic_gates.gate_batch(
            [output], [request])["per_output"][0]["hard_veto_codes"]
        self.assertNotIn(
            "HV_UNSUPPORTED_DETERMINISTIC_CLAIM:fiber_or_composition:棉层", codes)

    def test_second_attempt_is_rejected(self) -> None:
        _, _, _, request = make_request()
        raw = make_raw(request)
        raw["attempt_index"] = 2
        raw["attempt_id"] = f"{request['request_id']}:attempt:2"
        with self.assertRaisesRegex(contract.ContractError, "FIRST_ATTEMPT_ONLY"):
            author_contract.validate_raw(raw, request)

    def test_missing_must_surface_is_hard_failure(self) -> None:
        _, _, _, request = make_request()
        raw = make_raw(request, body_fact_ids=[])
        raw["surface_units"][1]["fact_ids"] = []
        raw["surface_units"][3]["fact_ids"] = []
        output = author_contract.serialize(raw, request)
        report = deterministic_gates.gate_batch([output], [request])
        self.assertTrue(any("HF_MUST_SURFACE_MISSING" in code
                            for code in report["per_output"][0]["hard_failure_codes"]))

    def test_control_only_binding_is_whole_batch_veto(self) -> None:
        _, _, _, request = make_request()
        control_id = request["surface_policy"]["control_only_fact_ids"][0]
        output = author_contract.serialize(make_raw(request, body_fact_ids=[control_id]), request)
        report = deterministic_gates.gate_batch([output], [request])
        self.assertFalse(report["whole_batch_machine_hard_veto_zero"])
        self.assertTrue(any("HV_CONTROL_ONLY_SURFACED" in code
                            for code in report["per_output"][0]["hard_veto_codes"]))

    def test_prohibited_control_term_without_binding_is_veto(self) -> None:
        _, _, _, request = make_request()
        output = author_contract.serialize(
            make_raw(request, body_text="这件样衣颜色准确。"), request)
        report = deterministic_gates.gate_batch([output], [request])
        self.assertTrue(any("HV_PROHIBITED_CONTROL_TERM" in code
                            for code in report["per_output"][0]["hard_veto_codes"]))

    def test_self_approval_is_veto(self) -> None:
        _, _, _, request = make_request()
        raw = make_raw(request)
        raw["title"] = "这条内容已经批准上线"
        raw["surface_units"][1]["text"] = raw["title"]
        output = author_contract.serialize(raw, request)
        report = deterministic_gates.gate_batch([output], [request])
        self.assertIn("HV_SELF_APPROVAL_OR_PUBLISH_STATE",
                      report["per_output"][0]["hard_veto_codes"])

    def test_output_surface_tamper_fails_even_if_digest_recomputed(self) -> None:
        _, _, _, request = make_request()
        output = author_contract.serialize(make_raw(request), request)
        bad = copy.deepcopy(output)
        bad["body"][0] = "被篡改但表面单元没改"
        contract.close_digest(bad, "output_digest")
        with self.assertRaisesRegex(contract.ContractError, "SURFACE_JOIN"):
            author_contract.validate_output(bad, request)

    def test_output_disclosure_and_request_identity_are_revalidated(self) -> None:
        _, _, _, request = make_request()
        output = author_contract.serialize(make_raw(request), request)
        bad_disclosure = copy.deepcopy(output)
        bad_disclosure["synthetic_disclosure"] = "普通说明"
        bad_disclosure["surface_units"][0]["text"] = "普通说明"
        contract.close_digest(bad_disclosure, "output_digest")
        with self.assertRaisesRegex(contract.ContractError, "OUTPUT_DISCLOSURE"):
            author_contract.validate_output(bad_disclosure, request)
        bad_identity = copy.deepcopy(output)
        bad_identity["run_id"] = "OTHER-RUN"
        contract.close_digest(bad_identity, "output_digest")
        with self.assertRaisesRegex(contract.ContractError, "REQUEST_JOIN:run_id"):
            author_contract.validate_output(bad_identity, request)

    def test_gate_report_cannot_hide_existing_failure(self) -> None:
        _, _, _, request = make_request()
        raw = make_raw(request, body_fact_ids=[])
        raw["surface_units"][1]["fact_ids"] = []
        raw["surface_units"][3]["fact_ids"] = []
        output = author_contract.serialize(raw, request)
        report = deterministic_gates.gate_batch([output], [request])
        bad = copy.deepcopy(report)
        bad["per_output"][0]["machine_first_fail"] = False
        bad["machine_hard_fail_ids"] = []
        bad["machine_hard_fail_count"] = 0
        contract.close_digest(bad, "report_digest")
        with self.assertRaisesRegex(contract.ContractError, "ROW_FAIL_RECOMPUTE"):
            deterministic_gates.validate_gate_report(bad, [output], [request])

    def test_gate_report_cannot_delete_veto_and_reclose(self) -> None:
        _, _, _, request = make_request()
        control_id = request["surface_policy"]["control_only_fact_ids"][0]
        output = author_contract.serialize(
            make_raw(request, body_fact_ids=[control_id]), request)
        report = deterministic_gates.gate_batch([output], [request])
        bad = copy.deepcopy(report)
        bad["per_output"][0]["hard_veto_codes"] = []
        bad["per_output"][0]["machine_first_fail"] = False
        bad["machine_hard_veto_ids"] = []
        bad["machine_hard_veto_count"] = 0
        bad["whole_batch_machine_hard_veto_zero"] = True
        bad["machine_hard_fail_ids"] = []
        bad["machine_hard_fail_count"] = 0
        contract.close_digest(bad, "report_digest")
        with self.assertRaisesRegex(contract.ContractError, "FULL_RECOMPUTE"):
            deterministic_gates.validate_gate_report(bad, [output], [request])


class MetricTests(unittest.TestCase):
    def setUp(self) -> None:
        _, _, _, self.request = make_request()
        self.output = author_contract.serialize(make_raw(self.request), self.request)
        self.gate = deterministic_gates.gate_batch([self.output], [self.request])

    def test_clean_batch_passes_three_conjunctive_gates(self) -> None:
        content, fact = reviews(self.output)
        result = metrics.compute_batch_metrics(
            [self.output], [self.request], self.gate, content, fact)
        self.assertTrue(result["gate_first_acceptance"])
        self.assertTrue(result["gate_formulaic"])
        self.assertTrue(result["gate_whole_batch_hard_veto_zero"])
        self.assertTrue(result["gate_qualified"])

    def test_veto_in_rejected_item_fails_whole_batch_not_acceptable_set(self) -> None:
        content, fact = reviews(self.output, content_grade="C", fact_approved=False,
                                fact_vetoes=["H_FABRICATED_FACT"])
        result = metrics.compute_batch_metrics(
            [self.output], [self.request], self.gate, content, fact)
        self.assertEqual(result["whole_batch_hard_veto_count"], 1)
        self.assertFalse(result["gate_whole_batch_hard_veto_zero"])
        self.assertEqual(result["hard_veto_count_in_acceptable_set"], 0)
        self.assertTrue(result["gate_hard_veto_zero_in_acceptable_set"])
        self.assertFalse(result["gate_qualified"])

    def test_duplicate_review_cannot_be_silently_overwritten(self) -> None:
        content, fact = reviews(self.output)
        with self.assertRaisesRegex(contract.ContractError, "CONTENT_REVIEW_DUP"):
            metrics.compute_batch_metrics([self.output], [self.request], self.gate,
                                          content + copy.deepcopy(content), fact)

    def test_formulaic_item_cannot_keep_acceptable_grade(self) -> None:
        content, fact = reviews(self.output, content_grade="B", formulaic=True)
        with self.assertRaisesRegex(contract.ContractError, "FORMULAIC_GRADE_CAP"):
            metrics.compute_batch_metrics(
                [self.output], [self.request], self.gate, content, fact)


class TelemetryAndRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        _, _, _, self.request = make_request()
        self.raw = make_raw(self.request)
        self.output = author_contract.serialize(self.raw, self.request)

    def test_complete_telemetry_and_manifest(self) -> None:
        gate = deterministic_gates.gate_batch([self.output], [self.request])
        content, fact = reviews(self.output)
        batch_metrics = metrics.compute_batch_metrics(
            [self.output], [self.request], gate, content, fact)
        events = qualification_events(
            self.request, self.output, gate, content, fact, batch_metrics)
        telemetry.validate_qualification_coverage(
            events, [self.request], [self.output], gate, content, fact, batch_metrics,
            run_id="RUN-1", batch_id="BATCH-A")
        summary = telemetry.summarize_events(events)
        self.assertTrue(summary["telemetry_complete"])
        manifest = run_manifest_for(self.request, self.output, summary)
        telemetry.validate_run_manifest(manifest)

    def test_unavailable_is_explicit_and_blocks_completeness(self) -> None:
        unavailable = telemetry.unavailable("provider does not expose this field")
        event = telemetry.make_event(
            event_id="EVENT-U", run_id="RUN-1", batch_id="BATCH-A",
            stage="AUTHOR_GENERATION", operation_kind="AUTHOR_GENERATION",
            request_id=self.request["request_id"],
            attempt_index=1, status="SUCCESS",
            started_at="2026-07-16T12:00:00+00:00",
            completed_at="2026-07-16T12:00:01+00:00",
            input_digest=self.request["request_digest"],
            output_digest=self.output["output_digest"],
            provider_call_id=unavailable,
            reviewer_minutes=unavailable,
            model_config={"provider": "internal", "model_family": "test-model",
                          "model_revision": unavailable, "reasoning_effort": "high",
                          "temperature": unavailable, "top_p": unavailable,
                          "seed": unavailable},
            usage={field: unavailable for field in telemetry.USAGE_FIELDS},
            cost={"amount": unavailable, "currency": unavailable,
                  "rate_card_ref": unavailable},
        )
        summary = telemetry.summarize_events([event])
        self.assertFalse(summary["telemetry_complete"])
        self.assertTrue(summary["unavailable_paths"])

    def test_qualification_retry_event_is_rejected(self) -> None:
        with self.assertRaisesRegex(contract.ContractError, "RETRY_FORBIDDEN"):
            telemetry.make_event(
                event_id="EVENT-R", run_id="RUN-1", batch_id="BATCH-A",
                stage="AUTHOR_GENERATION", operation_kind="AUTHOR_GENERATION",
                request_id=self.request["request_id"],
                attempt_index=1, status="SUCCESS",
                started_at="2026-07-16T12:00:00+00:00",
                completed_at="2026-07-16T12:00:01+00:00",
                input_digest=self.request["request_digest"],
                output_digest=self.output["output_digest"],
                provider_call_id="provider-call-retry",
                reviewer_minutes=0,
                model_config=full_event(self.request, self.output)["model_config"],
                usage=full_event(self.request, self.output)["usage"],
                cost=full_event(self.request, self.output)["cost"],
                retry_count=1, retry_reasons=["feedback retry"],
            )

    def test_generation_event_status_and_digest_must_join_output(self) -> None:
        event = full_event(self.request, self.output)
        bad_status = copy.deepcopy(event)
        bad_status["status"] = "FAILED"
        contract.close_digest(bad_status, "event_digest")
        with self.assertRaisesRegex(contract.ContractError, "GENERATION_STATUS"):
            telemetry.validate_generation_coverage(
                [bad_status], [self.request], [self.output],
                run_id="RUN-1", batch_id="BATCH-A")
        bad_digest = copy.deepcopy(event)
        bad_digest["output_digest"] = "0" * 64
        contract.close_digest(bad_digest, "event_digest")
        with self.assertRaisesRegex(contract.ContractError, "GENERATION_OUTPUT_JOIN"):
            telemetry.validate_generation_coverage(
                [bad_digest], [self.request], [self.output],
                run_id="RUN-1", batch_id="BATCH-A")

    def test_provider_call_id_is_required_and_unavailable_blocks_completeness(self) -> None:
        event = full_event(self.request, self.output)
        unavailable = telemetry.unavailable("provider did not return call receipt")
        event["provider_call_id"] = unavailable
        contract.close_digest(event, "event_digest")
        telemetry.validate_event(event)
        summary = telemetry.summarize_events([event])
        self.assertFalse(summary["telemetry_complete"])
        with self.assertRaisesRegex(contract.ContractError, "PROVIDER_CALL_REQUIRED"):
            telemetry.validate_generation_coverage(
                [event], [self.request], [self.output],
                run_id="RUN-1", batch_id="BATCH-A")

    def test_token_subsets_are_not_double_counted(self) -> None:
        event = full_event(self.request, self.output)
        bad_total = copy.deepcopy(event)
        bad_total["usage"]["total_tokens"] = 18
        contract.close_digest(bad_total, "event_digest")
        with self.assertRaisesRegex(contract.ContractError, "TOKEN_TOTAL"):
            telemetry.validate_event(bad_total)
        bad_cached = copy.deepcopy(event)
        bad_cached["usage"]["cached_input_tokens"] = 11
        contract.close_digest(bad_cached, "event_digest")
        with self.assertRaisesRegex(contract.ContractError, "CACHED_INPUT_SUBSET"):
            telemetry.validate_event(bad_cached)

    def test_v4_event_adapts_to_eval_spine_cost_contract(self) -> None:
        spine_root = (REPO_ROOT / "controlled_content_generator_v2_001" /
                      "gate1_v1_1_001" / "p7_successor_longrun_001" /
                      "eval_audit_spine_001")
        sys.path.insert(0, str(spine_root))
        from spine.contracts import validate_cost_event

        adapted = telemetry.to_eval_spine_cost_event(
            full_event(self.request, self.output),
            budget_category="causal_pilot_60_usd")
        self.assertEqual(validate_cost_event(adapted), [])

    def test_runner_end_to_end_clean_batch(self) -> None:
        content, fact = reviews(self.output)
        gate = deterministic_gates.gate_batch([self.output], [self.request])
        batch_metrics = metrics.compute_batch_metrics(
            [self.output], [self.request], gate, content, fact)
        events = qualification_events(
            self.request, self.output, gate, content, fact, batch_metrics)
        summary = telemetry.summarize_events(events)
        manifest = run_manifest_for(self.request, self.output, summary)
        result = runner.evaluate_qualification_batch(
            [self.request], [self.raw], content, fact, events, manifest)
        self.assertTrue(result["qualification_pass"])
        self.assertTrue(result["metrics"]["gate_whole_batch_hard_veto_zero"])

    def test_runner_rejects_missing_stage_and_unknown_review_event(self) -> None:
        content, fact = reviews(self.output)
        gate = deterministic_gates.gate_batch([self.output], [self.request])
        batch_metrics = metrics.compute_batch_metrics(
            [self.output], [self.request], gate, content, fact)
        events = qualification_events(
            self.request, self.output, gate, content, fact, batch_metrics)
        summary = telemetry.summarize_events(events)
        manifest = run_manifest_for(self.request, self.output, summary)
        without_metrics = [event for event in events
                           if event["operation_kind"] != "METRICS_AGGREGATION"]
        with self.assertRaisesRegex(contract.ContractError, "METRICS_COVERAGE"):
            runner.evaluate_qualification_batch(
                [self.request], [self.raw], content, fact, without_metrics, manifest)
        unknown = copy.deepcopy(next(
            event for event in events if event["operation_kind"] == "CONTENT_REVIEW"))
        unknown["event_id"] = "EVENT-UNKNOWN-REVIEW"
        unknown["request_id"] = "UNKNOWN"
        contract.close_digest(unknown, "event_digest")
        with self.assertRaisesRegex(contract.ContractError, "CONTENT_REVIEW_COVERAGE"):
            runner.evaluate_qualification_batch(
                [self.request], [self.raw], content, fact, events + [unknown], manifest)

    def test_runner_rejects_manifest_binding_tamper(self) -> None:
        content, fact = reviews(self.output)
        gate = deterministic_gates.gate_batch([self.output], [self.request])
        batch_metrics = metrics.compute_batch_metrics(
            [self.output], [self.request], gate, content, fact)
        events = qualification_events(
            self.request, self.output, gate, content, fact, batch_metrics)
        summary = telemetry.summarize_events(events)
        manifest = run_manifest_for(self.request, self.output, summary)
        for field, expected_error in (
                ("input_manifest_digest", "INPUT_MANIFEST_DIGEST"),
                ("output_manifest_digest", "OUTPUT_MANIFEST_DIGEST"),
                ("model_or_engine_config_ref", "MODEL_CONFIG_BINDING")):
            bad = copy.deepcopy(manifest)
            bad[field] = "0" * 64 if "digest" in field else "OTHER"
            contract.close_digest(bad, "manifest_digest")
            with self.assertRaisesRegex(contract.ContractError, expected_error):
                runner.evaluate_qualification_batch(
                    [self.request], [self.raw], content, fact, events, bad)

    def test_event_replacement_changes_root_telemetry_summary(self) -> None:
        content, fact = reviews(self.output)
        gate = deterministic_gates.gate_batch([self.output], [self.request])
        batch_metrics = metrics.compute_batch_metrics(
            [self.output], [self.request], gate, content, fact)
        events = qualification_events(
            self.request, self.output, gate, content, fact, batch_metrics)
        original = telemetry.summarize_events(events)
        replaced = copy.deepcopy(events)
        replaced[0]["provider_call_id"] = "different-provider-call-receipt"
        contract.close_digest(replaced[0], "event_digest")
        changed = telemetry.summarize_events(replaced)
        self.assertNotEqual(original["event_manifest_digest"],
                            changed["event_manifest_digest"])
        self.assertNotEqual(original["summary_digest"], changed["summary_digest"])

    def test_build_runner_copies_same_assignment_closure(self) -> None:
        case = scenario()
        bundle_a = runner.build_qualification_requests(
            [case], [raw_material()], assignment_set_id="SET-1", batch_id="A",
            run_id="RUN-A",
            authors_by_profile={"CP01": {"author_identity": "AUTHOR-1",
                                          "model_config_ref": "MODEL-1"}})
        bundle_b = runner.build_qualification_requests(
            [case], [raw_material()], assignment_set_id="SET-1", batch_id="B",
            run_id="RUN-B",
            authors_by_profile={"CP01": {"author_identity": "AUTHOR-1",
                                          "model_config_ref": "MODEL-1"}})
        self.assertEqual(bundle_a["assignments"], bundle_b["assignments"])
        self.assertEqual(bundle_a["requests"][0]["gate1_test_assignment"],
                         bundle_a["assignments"][0])
        self.assertEqual(bundle_a["requests"][0]["assignment_digest"],
                         bundle_a["assignments"][0]["assignment_digest"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
