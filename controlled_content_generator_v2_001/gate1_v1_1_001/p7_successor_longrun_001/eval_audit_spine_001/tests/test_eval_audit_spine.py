#!/usr/bin/env python3
"""评测脊柱正向与反向自测。"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = HERE.parents[5]
sys.path.insert(0, str(PACKAGE))

from spine.calibration import (one_sided_binomial_upper,
                               qualify_claim_atomization,
                               qualify_disclosure_and_omission,
                               qualify_end_to_end, qualify_entailment,
                               qualify_reference_extraction,
                               qualify_review_calibration,
                               qualify_risk_classification)
from spine.adapters import adapt_v4_cost_event
from spine.canonical import digest_json
from spine.contracts import (ContractError, qualification_decision,
                             validate_dataset_rows, validate_gate1_test_assignment)
from spine.cost import (BUDGET_CATEGORY_KEYS, PROJECTION_METRIC_KEYS,
                        accounting_integrity_gate, build_scale_projection,
                        metering_report, project_scale)
from spine.disclosure import check_required_disclosures, omission_risk_action
from spine.evidence_chain import (covered_claim_candidates, known_risk_findings,
                                  make_claim_atom, runtime_action)
from spine.formulaic import (agreement_metrics, candidate_retrieval_metrics,
                             canonical_pair_id,
                             confirmed_item_rate, expand_group_to_pairs,
                             qualify_formulaic_construct)
from spine.m0 import (AUDIT_INTEGRITY_GATES, INDEPENDENT_ADJUDICATION_GATES,
                      METHOD_CONFIG_DIGESTS, MODULE_GATE_KEYS,
                      MODULE_RECORD_ROLE_MINIMUMS,
                      QUALIFICATION_CLASS_MINIMUMS, REQUIRED_MODULES,
                      REQUIRED_REPORT_REFS, build_m0_decision,
                      build_record_manifest, close_module_report,
                      verify_m0_decision, verify_module_report)
from spine.probabilistic_adapter import AbstainingAdapter, independent_claim_candidates
from spine.qualification_data import build_qualification_record_index
from spine.manifest import build_candidate_manifest, verify_candidate_manifest
from spine.review_assignment import assignment_audit, balanced_cross_assign
from spine.runner import integrity_snapshot, r5_shadow_audit
from spine.source_index import (make_source_evidence_unit,
                                validate_reference_assertions,
                                verify_source_evidence_unit)
from spine.stage_gate import stage_decision, whole_batch_metrics


QUALIFICATION_DATASET_DIGEST = "d" * 64
FAMILIES = (
    "F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
    "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
    "F5_ENTERPRISE_LONG_TERM_TRUST",
)
QUALIFICATION_META_FIELDS = {
    "case_id", "case_digest", "case_payload_digest", "source_group_id",
    "visibility_partition", "dataset_manifest_digest", "gold_label_digest",
    "gold_field_names", "gold_review_provenance", "source_evidence_digest",
}
GOLD_FIELD_CANDIDATES = {
    "gold_present", "gold_label", "gold_risk", "gold_safe_to_clear",
    "gold_violation", "gold_misleading", "decision", "hard_veto", "axes",
    "necessary_grammar_exception_id", "verdict", "final_verdict",
    "gold_formulaic", "gold_attributes", "gold_atom_partition",
}


def seal_qualification_rows(rows: list[dict], prefix: str) -> list[dict]:
    sealed = []
    for index, source in enumerate(rows):
        row = {key: copy.deepcopy(value) for key, value in source.items()
               if key not in QUALIFICATION_META_FIELDS}
        row["case_id"] = f"{prefix}-{index:04d}"
        row["source_group_id"] = f"{prefix}-GROUP-{index:04d}"
        row["visibility_partition"] = "HIDDEN"
        row["dataset_manifest_digest"] = QUALIFICATION_DATASET_DIGEST
        row["source_evidence_digest"] = digest_json(
            {"sealed_source": prefix, "source_index": index})
        row["gold_field_names"] = sorted(GOLD_FIELD_CANDIDATES & set(row))
        if not row["gold_field_names"]:
            raise ValueError("test qualification row has no bound gold fields")
        row["gold_label_digest"] = digest_json({
            field: row[field] for field in row["gold_field_names"]})
        payload_excluded = {
            "case_id", "case_digest", "case_payload_digest", "source_group_id",
            "visibility_partition", "dataset_manifest_digest", "gold_label_digest",
            "gold_field_names", "gold_review_provenance",
        }
        row["case_payload_digest"] = digest_json({
            key: value for key, value in row.items() if key not in payload_excluded})
        reviews = []
        for slot, reviewer in (("A", "GOLD-A"), ("B", "GOLD-B")):
            review = {
                "review_id": f"{prefix}-{slot}-{index}",
                "reviewer_identity": reviewer, "reviewer_kind": "HUMAN",
                "model_revision": None, "prompt_digest": None,
                "case_id": row["case_id"],
                "case_payload_digest": row["case_payload_digest"],
                "source_evidence_digest": row["source_evidence_digest"],
                "gold_label_digest": row["gold_label_digest"],
                "decision": "CONFIRM",
                "evidence_digest": digest_json(
                    {"case_id": row["case_id"], "reviewer": reviewer}),
                "review_digest": "",
            }
            unsigned_review = dict(review)
            unsigned_review.pop("review_digest")
            review["review_digest"] = digest_json(unsigned_review)
            reviews.append(review)
        row["gold_review_provenance"] = reviews
        unsigned = dict(row)
        row["case_digest"] = digest_json(unsigned)
        sealed.append(row)
    return sealed


def qualification_index(*record_sets: list[dict]) -> dict:
    rows = [row for record_set in record_sets for row in record_set]
    return build_qualification_record_index(
        rows, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST)


def cost_fixture() -> tuple[dict, list[dict], dict, dict]:
    rate_card = {
        "schema_version": "eval-spine-rate-card-v1", "snapshot_id": "RATE-1",
        "captured_at": "2026-07-15T08:00:00+00:00", "currency": "USD",
        "rates": {"provider::model": {
            "input_per_million": 1.0, "cached_input_per_million": .5,
            "output_per_million": 2.0}}, "labor_rates": {"R1": 60.0},
        "rate_card_digest": ""}
    unsigned_rate = dict(rate_card)
    unsigned_rate.pop("rate_card_digest")
    rate_card["rate_card_digest"] = digest_json(unsigned_rate)
    events: list[dict] = []
    expected_model_cost = 15 / 1_000_000
    for index in range(12):
        human = index >= 6
        event = {
            "schema_version": "eval-spine-cost-event-v1",
            "event_id": f"E-{index}", "stage_id": "M0",
            "task_kind": "REVIEW" if human else "MODEL",
            "resource_kind": "HUMAN_REVIEW" if human else "MODEL_CALL",
            "budget_category": "one_time_gold_and_measurement_usd",
            "outcome_status": "SUCCEEDED",
            "source_telemetry_event_digest": digest_json(
                {"source_event": index}),
            "object_id": f"O-{index}", "attempt_id": f"A-{index}",
            "provider": None if human else "provider",
            "model_revision": None if human else "model",
            "provider_call_id": None if human else f"CALL-{index}",
            "input_tokens": None if human else 10,
            "cached_input_tokens": None if human else 2,
            "output_tokens": None if human else 3,
            "price_snapshot_id": None if human else "RATE-1",
            "model_cost_usd": None if human else expected_model_cost,
            "reviewer_minutes": 10 if human else 0,
            "reviewer_identity": "R1" if human else None,
            "labor_rate_snapshot_id": "RATE-1" if human else None,
            "human_cost_usd": 10 if human else 0,
            "wall_clock_seconds": .1,
            "unavailable_reasons": {}, "event_digest": ""}
        unsigned = dict(event)
        unsigned.pop("event_digest")
        event["event_digest"] = digest_json(unsigned)
        events.append(event)
    expected_manifest = {
        "schema_version": "eval-spine-expected-cost-events-v1",
        "stage_scope": "M0", "registered_before_run": True,
        "custodian_identity": "COST-CUSTODIAN",
        "approved_by": "COST-OWNER",
        "approved_at": "2026-07-15T07:00:00+00:00",
        "source_run_manifest_digest": "d" * 64,
        "expected_events": [
            {"event_id": row["event_id"], "stage_id": row["stage_id"],
             "task_kind": row["task_kind"],
             "resource_kind": row["resource_kind"],
             "budget_category": row["budget_category"],
             "object_id": row["object_id"]} for row in events],
        "manifest_digest": ""}
    unsigned_manifest = dict(expected_manifest)
    unsigned_manifest.pop("manifest_digest")
    expected_manifest["manifest_digest"] = digest_json(unsigned_manifest)
    source_manifest = {
        "schema_version": "eval-spine-source-cost-events-v1", "run_id": "M0",
        "source_run_manifest_digest": "d" * 64,
        "generated_from_append_only_log": True,
        "includes_failed_attempts": True,
        "source_events": [
            {"event_id": row["event_id"],
             "resource_kind": row["resource_kind"],
             "outcome_status": row["outcome_status"],
             "source_telemetry_event_digest": row[
                 "source_telemetry_event_digest"],
             "provider_call_id": row["provider_call_id"],
             "wall_clock_seconds": row["wall_clock_seconds"]}
            for row in events],
        "manifest_digest": ""}
    unsigned_source = dict(source_manifest)
    unsigned_source.pop("manifest_digest")
    source_manifest["manifest_digest"] = digest_json(unsigned_source)
    return rate_card, events, expected_manifest, source_manifest


def scale_assumption_fixture(report: dict) -> dict:
    workloads: dict[str, list[dict]] = {}
    for index, category in enumerate(sorted(BUDGET_CATEGORY_KEYS)):
        workloads[category] = [
            {"workload_id": f"MODEL-{index}", "resource_kind": "MODEL_CALL",
             "provider": "provider", "model_revision": "model",
             "p50_event_count": 1, "p95_event_count": 2,
             "p50_input_tokens_per_event": 10,
             "p95_input_tokens_per_event": 20,
             "p50_cached_input_tokens_per_event": 2,
             "p95_cached_input_tokens_per_event": 4,
             "p50_output_tokens_per_event": 3,
             "p95_output_tokens_per_event": 6,
             "p50_wall_clock_seconds_per_event": .1,
             "p95_wall_clock_seconds_per_event": .2},
            {"workload_id": f"HUMAN-{index}",
             "resource_kind": "HUMAN_REVIEW", "reviewer_identity": "R1",
             "p50_event_count": 1, "p95_event_count": 2,
             "p50_reviewer_minutes_per_event": 1,
             "p95_reviewer_minutes_per_event": 2,
             "p50_wall_clock_seconds_per_event": 60,
             "p95_wall_clock_seconds_per_event": 120},
        ]
    manifest = {
        "schema_version": "eval-spine-scale-assumption-manifest-v1",
        "scope": "FULL_PROGRAM_THROUGH_240_PLUS_60",
        "registered_before_scale": True,
        "custodian_identity": "COST-CUSTODIAN", "approved_by": "COST-OWNER",
        "approved_at": "2026-07-15T09:00:00+00:00",
        "price_snapshot_id": "RATE-1",
        "basis_metering_report_digest": report["report_digest"],
        "basis_event_record_manifest_digest": report[
            "event_record_manifest_digest"],
        "single_item_wall_clock_seconds": {"p50": 60, "p95": 120},
        "stage_workloads": workloads, "manifest_digest": ""}
    unsigned = dict(manifest)
    unsigned.pop("manifest_digest")
    manifest["manifest_digest"] = digest_json(unsigned)
    return manifest


def closed_chain(index: int) -> dict:
    roles = ("source_evidence", "reference_assertion", "claim_atom",
             "risk_classification", "entailment", "final_action")
    objects = {role: digest_json({"role": role, "index": index}) for role in roles}
    manifest = {
        "schema_version": "eval-spine-e2e-chain-manifest-v1",
        "object_digests": objects,
        "links": [
            {"from_role": left, "to_role": right,
             "from_digest": objects[left], "to_digest": objects[right]}
            for left, right in zip(roles, roles[1:])],
        "chain_digest": "",
    }
    unsigned = dict(manifest)
    unsigned.pop("chain_digest")
    manifest["chain_digest"] = digest_json(unsigned)
    return manifest


def signed_assignment() -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "gate1-test-assignment-v1",
        "object_type": "gate1_test_assignment",
        "assignment_id": "A-1", "assignment_set_id": "AS-1",
        "case_id": "C-1", "scenario_id": "C-1", "scenario_digest": "c" * 64,
        "profile_id": "CP01", "family_id": "F1_PEOPLE_AND_REAL_SCENE",
        "material_packet_digest": "a" * 64, "allocation_version": "v1",
        "strategy_version": "v1", "strategy_digest": "b" * 64,
        "argument_spine": ["sequence"],
        "evidence_surface_policy": [
            {"reference_assertion_id": "F1", "policy": "MUST_SURFACE",
             "reason_code": "IDENTITY"},
            {"reference_assertion_id": "F2", "policy": "CONTROL_ONLY",
             "reason_code": "SAFETY_BOUNDARY"},
        ],
        "perspective_anchor": "maker", "limitation_carrier": "scene_state",
        "closing_function": "next_observation", "paired_assignment_id": None,
        "forbidden_inferences": ["durability"],
        "stage_scope": "GATE1_QUALIFICATION_ONLY",
        "not_formal_content_composition_plan": True, "runtime_consumable": False,
        "publishable": False, "binds_enterprise_runtime_input": False,
        "counts_toward_300": False,
        "test_dna": {"entry_lens": "maker", "evidence_route": "sequence",
                     "boundary_carrier": "scene_state",
                     "closing_function": "next_observation",
                     "strategy_id": "CP01_FROZEN_LINEAR_PROCESS_V1",
                     "strategy_source": "PROFILE_OVERRIDE", "strategy_frozen": True},
    }
    value["assignment_digest"] = digest_json(value)
    return value


class ContractTests(unittest.TestCase):
    def test_assignment_contract_and_digest(self) -> None:
        value = signed_assignment()
        validate_gate1_test_assignment(value)
        bad = copy.deepcopy(value)
        bad["expression_plan"] = {}
        unsigned = dict(bad)
        unsigned.pop("assignment_digest")
        bad["assignment_digest"] = digest_json(unsigned)
        with self.assertRaises(ContractError):
            validate_gate1_test_assignment(bad)

    def test_dataset_two_dimensional_isolation(self) -> None:
        rows = [
            {"case_id": "C1", "case_origin": "NATURAL",
             "visibility_partition": "DEVELOPMENT", "source_group_id": "G1",
             "case_digest": "1" * 64},
            {"case_id": "C2", "case_origin": "CHALLENGE",
             "visibility_partition": "VALIDATION", "source_group_id": "G1",
             "case_digest": "2" * 64},
            {"case_id": "H1", "case_origin": "CHALLENGE",
             "visibility_partition": "HIDDEN", "source_group_id": "G2",
             "case_digest": "3" * 64, "gold_label": "CONTRADICTED"},
        ]
        result = validate_dataset_rows(rows)
        self.assertFalse(result["passed"])
        self.assertTrue(any("source_group leakage" in e for e in result["errors"]))
        self.assertTrue(any("hidden payload leaked" in e for e in result["errors"]))

    def test_integrity_pass_does_not_forge_qualification(self) -> None:
        status = qualification_decision(True, {"a": True, "b": None})
        self.assertEqual(status["artifact_integrity_status"], "PASS")
        self.assertEqual(status["m0_qualification_status"], "BLOCKED")
        self.assertEqual(qualification_decision(True, {})["m0_qualification_status"],
                         "BLOCKED")

    def test_conditional_schemas_reject_semantic_contradictions(self) -> None:
        schemas = {path.name: Draft202012Validator(json.loads(
            path.read_text(encoding="utf-8"))) for path in (PACKAGE / "schema").glob("*.json")}
        stage = {"schema_version": "eval-spine-stage-decision-v1",
                 "decision_id": "D", "stage_id": "S", "status": "PASS",
                 "reason_codes": ["PASS"], "evidence_manifest_digests": [],
                 "next_allowed_stage": None, "claims_allowed": [],
                 "claims_forbidden": [], "decided_by": None,
                 "decision_digest": None}
        self.assertFalse(schemas["audit_run.v1.schema.json"].is_valid(stage))
        manifest = json.loads((PACKAGE / "calibration/qualification_manifest.v1.json").read_text(
            encoding="utf-8"))
        manifest.update({"content_status": "ADJUDICATED", "sealed": False})
        self.assertFalse(schemas["control.v1.schema.json"].is_valid(manifest))
        measurement_schema = schemas["measurement_report.v1.schema.json"]
        for module_id, gate_keys in MODULE_GATE_KEYS.items():
            module_report = {
                "schema_version": "eval-spine-m0-module-report-v1",
                "module_id": module_id, "method_version": 1,
                "visibility_partition": "HIDDEN",
                "dataset_manifest_digest": "1" * 64,
                "record_manifest_digest": "2" * 64,
                "method_config_digest": "3" * 64,
                "evaluator_revision_digest": "4" * 64,
                "execution_receipt_digest": "5" * 64,
                "qualified": False,
                "result": {"qualified": False,
                           "gates": {key: False for key in gate_keys}},
                "result_digest": "6" * 64, "report_digest": "7" * 64}
            self.assertTrue(measurement_schema.is_valid(module_report), module_id)
            module_report["result"]["gates"] = {"made_up_gate": False}
            self.assertFalse(measurement_schema.is_valid(module_report), module_id)
        reference = {"schema_version": "eval-spine-reference-assertion-v1",
                     "assertion_id": "R", "subject": "s", "predicate": "p",
                     "object_value": True, "unit": None, "time_scope": None,
                     "polarity": "POSITIVE", "modality": "OBSERVED",
                     "preconditions": [], "evidence_unit_ids": ["E"],
                     "authorization_ids": [], "risk_class": "HIGH",
                     "extraction_origin": "HUMAN",
                     "engine_provenance": {"engine_kind": "HUMAN", "engine_id": "H",
                                           "engine_revision": "v1",
                                           "prompt_or_rule_digest": None,
                                           "provider_call_id": None},
                     "verification_status": "DUAL_ADJUDICATED", "review_ids": [],
                     "object_digest": "a" * 64}
        self.assertFalse(schemas["evidence_chain.v1.schema.json"].is_valid(reference))
        finding = {"schema_version": "eval-spine-entailment-finding-v1",
                   "finding_id": "F", "claim_atom_id": "C",
                   "reference_assertion_ids": [], "semantic_label": None,
                   "abstain": False, "confidence": None, "risk_class": "HIGH",
                   "action": "NO_FINDING", "reason": "x",
                   "engine_provenance": {"engine_kind": "LLM", "engine_id": "M",
                                         "engine_revision": "v1",
                                         "prompt_or_rule_digest": "b" * 64,
                                         "provider_call_id": "CALL"},
                   "review_status": "UNREVIEWED", "review_ids": [],
                   "object_digest": "c" * 64}
        self.assertFalse(schemas["evidence_chain.v1.schema.json"].is_valid(finding))
        formulaic = {"schema_version": "eval-spine-formulaic-adjudication-v1",
                     "adjudication_id": "A", "edge_id": "E", "reviewer_id": "R",
                     "rubric_version": "v1",
                     "axes": {"argument_spine": "NECESSARY_GRAMMAR",
                              "evidence_progression": "DIFFERENT",
                              "limitation_function": "DIFFERENT",
                              "viewpoint_anchor": "DIFFERENT",
                              "closing_function": "DIFFERENT",
                              "transformation_depth": "STRUCTURAL_CHANGE"},
                     "necessary_grammar_exception_id": None,
                     "formulaic_decision": "NECESSARY_GRAMMAR",
                     "near_duplicate": False, "evidence": ["x"],
                     "review_status": "FIRST_REVIEW", "object_digest": "d" * 64}
        self.assertFalse(schemas["evaluation.v1.schema.json"].is_valid(formulaic))
        disclosure = {"schema_version": "eval-spine-disclosure-finding-v1",
                      "finding_id": "D", "output_id": "O", "obligation_id": "P",
                      "surface_policy": "BLOCK_OUTPUT", "decision_layer": "PROBABILISTIC",
                      "trigger_evidence": ["x"], "omission_may_mislead": True,
                      "confidence": .9, "action": "DETERMINISTIC_HARD",
                      "review_status": "UNREVIEWED", "object_digest": "e" * 64}
        self.assertFalse(schemas["evaluation.v1.schema.json"].is_valid(disclosure))
        review = {"schema_version": "eval-spine-independent-review-v1",
                  "review_id": "R", "reviewer_identity": "I",
                  "reviewer_role": "IMPLEMENTATION",
                  "independence_attestation": {"did_not_author_reviewed_scope": True,
                                               "did_not_read_peer_review_before_submission": True,
                                               "no_role_collision": True},
                  "target_commit": "abcdef0", "target_manifest_digest": "f" * 64,
                  "reviewed_evidence_refs": ["x"], "recompute_commands": ["x"],
                  "gate_decisions": {"tests": "FAIL"}, "findings": [],
                  "final_decision": "APPROVE_IMPLEMENTATION",
                  "reviewed_at": "2026-07-15", "review_digest": "0" * 64}
        self.assertFalse(schemas["independent_review.v1.schema.json"].is_valid(review))


class EvidenceTests(unittest.TestCase):
    def test_exact_source_span_and_tamper(self) -> None:
        source = "四条空号，改发站内信。"
        unit = make_source_evidence_unit("S1", source, 0, len("四条".encode("utf-8")),
                                         authorization_ids=["AUTH-1"])
        self.assertEqual(verify_source_evidence_unit(unit, source), [])
        self.assertIn("source_digest_mismatch",
                      verify_source_evidence_unit(unit, source + "改"))

    def test_reference_set_requires_independent_review(self) -> None:
        source_text = "四条空号，改发站内信。"
        unit = make_source_evidence_unit(
            "S1", source_text, 0, len("四条空号".encode("utf-8")),
            authorization_ids=["A1"])
        evidence_id = unit["evidence_unit_id"]
        row = {"schema_version": "eval-spine-reference-assertion-v1",
               "assertion_id": "R1", "subject": "四条空号", "predicate": "can_call",
               "object_value": False, "unit": None, "time_scope": None,
               "polarity": "NEGATIVE", "modality": "OBSERVED", "preconditions": [],
               "evidence_unit_ids": [evidence_id], "authorization_ids": ["A1"],
               "risk_class": "HIGH", "extraction_origin": "HUMAN",
               "engine_provenance": {"engine_kind": "HUMAN", "engine_id": "R",
                                     "engine_revision": "v1", "prompt_or_rule_digest": None,
                                     "provider_call_id": None},
               "verification_status": "DUAL_ADJUDICATED",
               "review_ids": ["REV-1", "REV-2"], "object_digest": ""}
        unsigned = dict(row)
        unsigned.pop("object_digest")
        row["object_digest"] = digest_json(unsigned)
        result = validate_reference_assertions(
            [row], evidence_units_by_id={evidence_id: unit},
            source_text_by_source_id={"S1": source_text},
            reviewer_identity_by_review_id={"REV-1": "same", "REV-2": "same"})
        self.assertFalse(result["passed"])
        self.assertIn("legacy_self_reported_reviewer_identity_not_accepted:R1",
                      result["errors"])
        evidence_set_digest = digest_json({
            "assertion_id": "R1", "assertion_object_digest": row["object_digest"],
            "evidence_unit_ids": [evidence_id]})
        reviews = {}
        for review_id, identity in (("REV-1", "A"), ("REV-2", "B")):
            review = {
                "schema_version": "eval-spine-reference-assertion-review-v1",
                "review_id": review_id, "assertion_id": "R1",
                "assertion_object_digest": row["object_digest"],
                "evidence_unit_ids": [evidence_id],
                "evidence_set_digest": evidence_set_digest,
                "reviewer_identity": identity, "reviewer_kind": "HUMAN",
                "model_revision": None, "prompt_digest": None,
                "reviewer_role": "REVIEWER", "decision": "CONFIRM",
                "evidence_digest": digest_json([
                    {"evidence_unit_id": evidence_id,
                     "object_digest": unit["object_digest"]}]),
                "review_digest": ""}
            unsigned_review = dict(review)
            unsigned_review.pop("review_digest")
            review["review_digest"] = digest_json(unsigned_review)
            reviews[review_id] = review
        accepted = validate_reference_assertions(
            [row], evidence_units_by_id={evidence_id: unit},
            source_text_by_source_id={"S1": source_text},
            review_records_by_id=reviews)
        self.assertTrue(accepted["passed"], accepted)

    def test_runtime_evidence_objects_match_their_schema(self) -> None:
        schema = json.loads((PACKAGE / "schema/evidence_chain.v1.schema.json").read_text(
            encoding="utf-8"))
        validator = Draft202012Validator(schema)
        source = "四条空号，改发站内信。"
        unit = make_source_evidence_unit(
            "S1", source, 0, len("四条空号".encode("utf-8")),
            authorization_ids=["AUTH-1"])
        validator.validate(unit)
        atom = make_claim_atom("O1", "颜色没有复核。", 0, len("颜色没有复核。"),
                               "rule-v1", risk_class="CRITICAL")
        validator.validate(atom)
        tampered = copy.deepcopy(unit)
        tampered["text"] = "四条"
        self.assertIn("quote_span_mismatch",
                      verify_source_evidence_unit(tampered, source))
        self.assertIn("object_digest_mismatch",
                      verify_source_evidence_unit(tampered, source))

    def test_author_claim_list_cannot_hide_omitted_claim(self) -> None:
        surface = "库存已复贴。客服会给四个空号逐个打电话。"
        candidates = independent_claim_candidates(surface, "dev-regex-v1")
        first = candidates[0]
        atoms = [{"start": first["start"], "end": first["end"]}]
        result = covered_claim_candidates(surface, candidates, atoms)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["missing_candidate_ids"]), 1)

    def test_probabilistic_unknown_and_abstain_never_auto_clear(self) -> None:
        self.assertEqual(runtime_action(relation="UNKNOWN", risk="HIGH",
                                        deterministic=False, reference_adjudicated=False,
                                        evaluator_qualified=False), "HUMAN_REVIEW")
        self.assertEqual(runtime_action(relation="SUPPORTED", risk="HIGH",
                                        deterministic=False, reference_adjudicated=False,
                                        evaluator_qualified=True), "HUMAN_REVIEW")
        self.assertEqual(runtime_action(relation="SUPPORTED", risk="LOW",
                                        deterministic=False, reference_adjudicated=False,
                                        evaluator_qualified=False), "HUMAN_REVIEW")
        self.assertEqual(runtime_action(relation="SUPPORTED", risk="MEDIUM",
                                        deterministic=False, reference_adjudicated=True,
                                        evaluator_qualified=True), "ALLOW")
        self.assertEqual(runtime_action(relation="SUPPORTED", risk="MEDIUM",
                                        deterministic=False, reference_adjudicated=False,
                                        evaluator_qualified=True), "HUMAN_REVIEW")
        finding = AbstainingAdapter().classify("claim", "reference")
        self.assertTrue(finding.abstain)
        self.assertIsNone(finding.label)

    def test_known_rules_are_development_only(self) -> None:
        findings = known_risk_findings("X", "粗棉纹")
        self.assertEqual([f["code"] for f in findings], ["R5_FIBER_UNSUPPORTED"])
        self.assertFalse(findings[0]["qualification_use"])


class CalibrationTests(unittest.TestCase):
    def test_reference_and_claim_extraction_need_their_own_qualification(self) -> None:
        records = [{"gold_present": index < 200,
                    "predicted_present": index < 200,
                    "gold_risk": "HIGH" if index < 200 else "LOW",
                    "predicted_risk": "HIGH" if index < 200 else "LOW",
                    "field_type": "POLARITY",
                    "family_id": FAMILIES[index % len(FAMILIES)],
                    "gold_attributes": {"polarity": "POSITIVE",
                                        "modality": "OBSERVED", "time_scope": None,
                                        "preconditions": []},
                    "predicted_attributes": {"polarity": "POSITIVE",
                                             "modality": "OBSERVED",
                                             "time_scope": None,
                                             "preconditions": []},
                    "gold_atom_partition": [[f"CLAIM-{index}"]],
                    "predicted_atom_partition": [[f"CLAIM-{index}"]]}
                   for index in range(300)]
        records = seal_qualification_rows(records, "EXTRACT")
        record_index = qualification_index(records)
        self.assertTrue(qualify_reference_extraction(
            records, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=record_index)["qualified"])
        self.assertTrue(qualify_claim_atomization(
            records, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=record_index)["qualified"])
        short = records[:10]
        self.assertFalse(qualify_reference_extraction(
            short, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(short))["qualified"])
        incomplete = copy.deepcopy(records)
        incomplete[0]["predicted_attributes"].pop("polarity")
        incomplete = seal_qualification_rows(incomplete, "EXTRACT-INCOMPLETE")
        self.assertFalse(qualify_reference_extraction(
            incomplete, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(incomplete))["qualified"])
        merged = copy.deepcopy(records)
        for index, row in enumerate(merged[:16]):
            row["gold_atom_partition"] = [[f"M-{index}-A"], [f"M-{index}-B"]]
            row["predicted_atom_partition"] = [[f"M-{index}-A", f"M-{index}-B"]]
        merged = seal_qualification_rows(merged, "ATOM-MERGED")
        self.assertFalse(qualify_claim_atomization(
            merged, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(merged))["qualified"])
        clones = [copy.deepcopy(records[0]) for _ in range(300)]
        with self.assertRaises(ValueError):
            qualification_index(clones)

    def test_exact_zero_event_upper_requires_300(self) -> None:
        upper = one_sided_binomial_upper(0, 300)
        self.assertIsNotNone(upper)
        self.assertLess(upper, .01)
        self.assertGreater(one_sided_binomial_upper(0, 298), .01)

    def test_entailment_joint_gate(self) -> None:
        records = [
            {"gold_label": "CONTRADICTED", "predicted_label": "CONTRADICTED",
             "gold_risk": "HIGH", "predicted_risk": "HIGH", "abstain": False,
             "action": "HUMAN_REVIEW", "case_origin": "CHALLENGE",
             "family_id": FAMILIES[index % len(FAMILIES)]}
            for index in range(300)
        ] + [
            {"gold_label": "UNKNOWN", "predicted_label": "UNKNOWN",
             "gold_risk": "HIGH", "predicted_risk": "HIGH", "abstain": True,
             "action": "HUMAN_REVIEW", "case_origin": "CHALLENGE",
             "family_id": FAMILIES[index % len(FAMILIES)]}
            for index in range(100)
        ] + [
            {"gold_label": "SUPPORTED", "predicted_label": "SUPPORTED",
             "gold_risk": "LOW", "predicted_risk": "LOW", "abstain": False,
             "action": "ALLOW", "case_origin": "NATURAL",
             "family_id": FAMILIES[index % len(FAMILIES)]}
            for index in range(300)
        ]
        known = [{"case_id": f"R5-{index}",
                  "fixture_digest": digest_json({"fixture": index}),
                  "output_digest": digest_json({"output": index}),
                  "expected_finding_codes": [f"R5-CODE-{index}"],
                  "observed_finding_codes": [f"R5-CODE-{index}"],
                  "registered_manifest_digest": "a" * 64}
                 for index in range(5)]
        records = seal_qualification_rows(records, "ENTAIL")
        record_index = qualification_index(records)
        result = qualify_entailment(
            records, known_risk_results=known,
            dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=record_index)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["auto_pass_false_negatives"], 0)
        self.assertEqual(result["false_hard_blocks"], 0)
        short = records[:20]
        self.assertFalse(qualify_entailment(
            short, known_risk_results=known,
            dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(short))["qualified"])
        mixed = [
            {"gold_label": "UNKNOWN", "predicted_label": "UNKNOWN",
             "gold_risk": "HIGH", "predicted_risk": "HIGH", "abstain": True,
             "action": "HUMAN_REVIEW", "case_origin": "CHALLENGE",
             "family_id": FAMILIES[index % len(FAMILIES)]}
            for index in range(300)
        ] + records[300:]
        mixed = seal_qualification_rows(mixed, "ENTAIL-MIXED")
        self.assertFalse(qualify_entailment(
            mixed, known_risk_results=known,
            dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(mixed))["qualified"])

    def test_end_to_end_is_a_separate_joint_gate(self) -> None:
        unsafe = [
            {"case_id": f"U-{index}", "gold_risk": "HIGH",
             "predicted_risk": "HIGH",
             "family_id": FAMILIES[index % len(FAMILIES)],
             "case_origin": "CHALLENGE", "gold_safe_to_clear": False,
             "final_action": "HUMAN_REVIEW", "chain_manifest": closed_chain(index)}
            for index in range(300)
        ]
        legal = [
            {"case_id": f"L-{index}", "gold_risk": "LOW",
             "predicted_risk": "LOW",
             "family_id": FAMILIES[index % len(FAMILIES)],
             "case_origin": "NATURAL", "gold_safe_to_clear": True,
             "final_action": "ALLOW", "chain_manifest": closed_chain(300 + index)}
            for index in range(300)
        ]
        records = seal_qualification_rows(unsafe + legal, "END2END")
        self.assertTrue(qualify_end_to_end(
            records, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(records))["qualified"])
        bad = copy.deepcopy(records)
        bad[0]["final_action"] = "ALLOW"
        bad = seal_qualification_rows(bad, "END2END-BAD")
        self.assertFalse(qualify_end_to_end(
            bad, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(bad))["qualified"])

    def test_risk_classification_cannot_downclassify_high_risk(self) -> None:
        rows = [
            {"gold_risk": "HIGH", "predicted_risk": "HIGH",
             "case_origin": "CHALLENGE",
             "family_id": FAMILIES[index % len(FAMILIES)]}
            for index in range(300)
        ] + [
            {"gold_risk": "LOW", "predicted_risk": "LOW",
             "case_origin": "NATURAL",
             "family_id": FAMILIES[index % len(FAMILIES)]}
            for index in range(300)
        ]
        rows = seal_qualification_rows(rows, "RISK")
        self.assertTrue(qualify_risk_classification(
            rows, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(rows))["qualified"])
        rows[0]["predicted_risk"] = "MEDIUM"
        rows = seal_qualification_rows(rows, "RISK-BAD")
        result = qualify_risk_classification(
            rows, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(rows))
        self.assertFalse(result["qualified"])
        self.assertEqual(result["downclassified_high_risk_count"], 1)

    def test_disclosure_and_omission_are_joint_but_separate_metrics(self) -> None:
        disclosure = []
        obligation_types = ["SYNTHETIC_IDENTITY_DISCLOSURE",
                            "PROHIBITED_REAL_IDENTITY_IMPERSONATION",
                            "EXPLICIT_AUTHORIZATION_BOUNDARY",
                            "PRIVACY_REDACTION_OR_BLOCK"]
        for index in range(100):
            disclosure.append({
                "case_id": f"D-{index}",
                "obligation_type": obligation_types[index % len(obligation_types)],
                "family_id": FAMILIES[index % len(FAMILIES)],
                "gold_violation": index < 80,
                "predicted_hard": index < 80,
            })
        omission = [
            {"case_id": f"OM-{index}", "gold_misleading": True,
             "predicted_flagged": True, "gold_risk": "HIGH",
             "predicted_risk": "HIGH",
             "family_id": FAMILIES[index % len(FAMILIES)]}
            for index in range(100)
        ] + [
            {"case_id": f"OC-{index}", "gold_misleading": False,
             "predicted_flagged": False, "gold_risk": "LOW",
             "predicted_risk": "LOW",
             "family_id": FAMILIES[index % len(FAMILIES)]}
            for index in range(100)
        ]
        disclosure = seal_qualification_rows(disclosure, "DISCLOSE")
        omission = seal_qualification_rows(omission, "OMISSION")
        self.assertTrue(qualify_disclosure_and_omission(
            disclosure, omission,
            dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(disclosure, omission))["qualified"])
        omission[0]["predicted_flagged"] = False
        omission = seal_qualification_rows(omission, "OMISSION-BAD")
        self.assertFalse(qualify_disclosure_and_omission(
            disclosure, omission,
            dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(disclosure, omission))["qualified"])

    def test_review_calibration_requires_real_cross_review(self) -> None:
        judgments = []
        for index in range(40):
            decision = "APPROVE" if index < 20 else "REJECT"
            hard = index >= 30
            for reviewer in ("R1", "R2"):
                judgments.append({"item_id": f"I-{index}", "reviewer_id": reviewer,
                                  "decision": decision, "hard_veto": hard,
                                  "family_id": FAMILIES[index % len(FAMILIES)],
                                  "author_identity": f"AUTHOR-{index}",
                                  "reviewer_provenance": {
                                      "reviewer_identity": reviewer,
                                      "reviewer_kind": "HUMAN",
                                      "model_revision": None, "prompt_digest": None}})
        judgments = seal_qualification_rows(judgments, "REVIEW")
        self.assertTrue(qualify_review_calibration(
            judgments, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(judgments))["qualified"])
        judgments[1]["reviewer_id"] = "R1"
        judgments = seal_qualification_rows(judgments, "REVIEW-BAD")
        self.assertFalse(qualify_review_calibration(
            judgments, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(judgments))["qualified"])
        skewed = []
        for index in range(40):
            for slot, reviewer in enumerate(("R1", "R2")):
                decision = "APPROVE" if index < 39 or slot == 0 else "REJECT"
                skewed.append({"item_id": f"S-{index}", "reviewer_id": reviewer,
                               "decision": decision, "hard_veto": index == 39,
                               "family_id": FAMILIES[index % len(FAMILIES)],
                               "author_identity": f"AUTHOR-S-{index}",
                               "reviewer_provenance": {
                                   "reviewer_identity": reviewer,
                                   "reviewer_kind": "HUMAN",
                                   "model_revision": None, "prompt_digest": None}})
        skewed = seal_qualification_rows(skewed, "REVIEW-SKEW")
        self.assertFalse(qualify_review_calibration(
            skewed, dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(skewed))["qualified"])


class FormulaicTests(unittest.TestCase):
    def test_edge_aggregation_uses_unique_endpoints(self) -> None:
        edges = [
            {"left_id": "A", "right_id": "B", "final_verdict": "FORMULAIC"},
            {"left_id": "B", "right_id": "A", "final_verdict": "FORMULAIC"},
            {"left_id": "B", "right_id": "C", "final_verdict": "FORMULAIC"},
        ]
        result = confirmed_item_rate(edges, ["A", "B", "C", "D"])
        self.assertEqual(result["confirmed_edge_count"], 2)
        self.assertEqual(result["formulaic_item_count"], 3)
        self.assertEqual(len(expand_group_to_pairs(["A", "B", "C"])), 3)
        self.assertEqual(canonical_pair_id("A", "B"), canonical_pair_id("B", "A"))

    def test_formulaic_measurement_cannot_qualify_on_tiny_sample(self) -> None:
        pair = canonical_pair_id("A", "B")
        judgments = [
            {"pair_id": pair, "reviewer_id": "R1", "verdict": "FORMULAIC"},
            {"pair_id": pair, "reviewer_id": "R2", "verdict": "FORMULAIC"},
        ]
        self.assertFalse(qualify_formulaic_construct(judgments)["qualified"])

    def test_formulaic_qualification_closes_sample_recall_and_review_coverage(self) -> None:
        judgments, adjudications, candidate_audit = [], [], []
        for index in range(300):
            left_id, right_id = f"LEFT-{index}", f"RIGHT-{index}"
            pair_id = canonical_pair_id(left_id, right_id)
            family_id = FAMILIES[index % len(FAMILIES)]
            if index < 100:
                verdict = "FORMULAIC"
                axes = {"argument_spine": "SAME", "evidence_progression": "SAME",
                        "limitation_function": "DIFFERENT", "viewpoint_anchor": "SAME",
                        "closing_function": "DIFFERENT",
                        "transformation_depth": "SURFACE_ONLY"}
                exception_id = None
            elif index >= 280:
                verdict = "NECESSARY_GRAMMAR"
                axes = {"argument_spine": "NECESSARY_GRAMMAR",
                        "evidence_progression": "DIFFERENT",
                        "limitation_function": "DIFFERENT",
                        "viewpoint_anchor": "DIFFERENT",
                        "closing_function": "DIFFERENT",
                        "transformation_depth": "STRUCTURAL_CHANGE"}
                exception_id = "NG-1"
            else:
                verdict = "NOT_FORMULAIC"
                axes = {"argument_spine": "DIFFERENT",
                        "evidence_progression": "DIFFERENT",
                        "limitation_function": "DIFFERENT",
                        "viewpoint_anchor": "DIFFERENT",
                        "closing_function": "DIFFERENT",
                        "transformation_depth": "STRUCTURAL_CHANGE"}
                exception_id = None
            for reviewer in ("R1", "R2"):
                judgments.append({"pair_id": pair_id, "reviewer_id": reviewer,
                                  "left_id": left_id, "right_id": right_id,
                                  "family_id": family_id,
                                  "left_author_identity": f"AUTHOR-L-{index}",
                                  "right_author_identity": f"AUTHOR-R-{index}",
                                  "reviewer_provenance": {
                                      "reviewer_identity": reviewer,
                                      "reviewer_kind": "HUMAN",
                                      "model_revision": None, "prompt_digest": None},
                                  "verdict": verdict, "axes": copy.deepcopy(axes),
                                  "necessary_grammar_exception_id": exception_id})
            if index < 100:
                candidate_audit.append({"pair_id": pair_id,
                                        "left_id": left_id, "right_id": right_id,
                                        "family_id": family_id,
                                        "candidate_selected": True,
                                        "gold_formulaic": True,
                                        "audit_scope": "RANDOM_RECALL_AUDIT"})
            elif index < 200:
                candidate_audit.append({"pair_id": pair_id,
                                        "left_id": left_id, "right_id": right_id,
                                        "family_id": family_id,
                                        "candidate_selected": False,
                                        "gold_formulaic": False,
                                        "audit_scope": "RANDOM_RECALL_AUDIT"})
            adjudications.append({"pair_id": pair_id,
                                  "left_id": left_id, "right_id": right_id,
                                  "family_id": family_id,
                                  "final_verdict": verdict,
                                  "necessary_grammar_exception_id": exception_id,
                                  "adjudicator_identity": None,
                                  "adjudication_evidence_digest": None})
        judgments = seal_qualification_rows(judgments, "FORM-JUDGMENT")
        adjudications = seal_qualification_rows(adjudications, "FORM-ADJ")
        candidate_audit = seal_qualification_rows(candidate_audit, "FORM-AUDIT")
        candidate_manifest = {
            "schema_version": "eval-spine-formulaic-candidate-audit-manifest-v1",
            "status": "SEALED", "registered_before_miner_run": True,
            "batch_id": "FORMULAIC-BATCH-1",
            "miner_run_id": "MINER-RUN-1", "custodian_identity": "DATA-CUSTODIAN",
            "registry_manifest_digest": "7" * 64,
            "sampling_algorithm": "PREREGISTERED_STRATIFIED_RANDOM_SAMPLE_V1",
            "population_pair_ids_digest": digest_json(
                sorted({row["pair_id"] for row in judgments})),
            "sampled_pair_ids_digest": digest_json(
                sorted({row["pair_id"] for row in candidate_audit})),
            "sample_count": len(candidate_audit),
            "randomization_seed_commitment": "9" * 64,
            "candidate_miner_blinded_to_gold": True,
            "gold_attached_after_candidate_run": True,
            "manifest_digest": "",
        }
        unsigned_candidate = dict(candidate_manifest)
        unsigned_candidate.pop("manifest_digest")
        candidate_manifest["manifest_digest"] = digest_json(unsigned_candidate)
        rubric = {"schema_version": "eval-spine-formulaic-rubric-freeze-v1",
                  "status": "FROZEN", "frozen_before_qualification": True,
                  "rubric_version": "v1", "batch_id": "FORMULAIC-BATCH-1",
                  "rubric_content_digest": "6" * 64,
                  "registry_manifest_digest": "7" * 64,
                  "custodian_identity": "DATA-CUSTODIAN",
                  "frozen_at": "2026-07-14T00:00:00Z", "rubric_digest": ""}
        unsigned = dict(rubric)
        unsigned.pop("rubric_digest")
        rubric["rubric_digest"] = digest_json(unsigned)
        exception = {"exception_id": "NG-1", "registered_before_batch": True,
                     "batch_id": "FORMULAIC-BATCH-1",
                     "approved_by": "PRODUCT-OWNER",
                     "product_definition_ref": "CP-PROFILE-V1",
                     "applicable_pair_ids_digest": digest_json(sorted(
                         row["pair_id"] for row in adjudications
                         if row["final_verdict"] == "NECESSARY_GRAMMAR")),
                     "maximum_pair_count": 20,
                     "registry_manifest_digest": "7" * 64,
                     "exception_digest": ""}
        unsigned_exception = dict(exception)
        unsigned_exception.pop("exception_digest")
        exception["exception_digest"] = digest_json(unsigned_exception)
        result = qualify_formulaic_construct(
            judgments, adjudications=adjudications,
            candidate_audit_records=candidate_audit,
            candidate_audit_manifest=candidate_manifest, rubric_manifest=rubric,
            necessary_grammar_exceptions=[exception],
            dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(
                judgments, adjudications, candidate_audit))
        self.assertTrue(result["qualified"], result)
        duplicate = copy.deepcopy(judgments)
        duplicate[1]["reviewer_id"] = "R1"
        duplicate = seal_qualification_rows(duplicate, "FORM-JUDGMENT-BAD")
        self.assertFalse(qualify_formulaic_construct(
            duplicate,
            adjudications=adjudications,
            candidate_audit_records=candidate_audit,
            candidate_audit_manifest=candidate_manifest, rubric_manifest=rubric,
            necessary_grammar_exceptions=[exception],
            dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(
                duplicate, adjudications, candidate_audit))["qualified"])
        fake_grammar = copy.deepcopy(adjudications)
        for row in fake_grammar:
            if row["final_verdict"] == "NECESSARY_GRAMMAR":
                row["final_verdict"] = "NOT_FORMULAIC"
        fake_grammar = seal_qualification_rows(fake_grammar, "FORM-ADJ-NO-GRAMMAR")
        self.assertFalse(qualify_formulaic_construct(
            judgments, adjudications=fake_grammar,
            candidate_audit_records=candidate_audit,
            candidate_audit_manifest=candidate_manifest, rubric_manifest=rubric,
            necessary_grammar_exceptions=[exception],
            dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
            qualification_record_index=qualification_index(
                judgments, fake_grammar, candidate_audit))["qualified"])


class OperationsTests(unittest.TestCase):
    def test_v4_telemetry_adapter_preserves_provider_receipt(self) -> None:
        event = {
            "event_id": "E1", "stage": "AUTHOR_GENERATION", "request_id": "R1",
            "attempt_index": 1, "duration_ms": 120,
            "provider_call_id": "CALL-1",
            "model_config": {"provider": "p", "model_revision": "m"},
            "usage": {"input_tokens": 10, "cached_input_tokens": 2,
                      "output_tokens": 3},
            "cost": {"amount": .02, "currency": "USD", "rate_card_ref": "RATE-1"},
        }
        adapted = adapt_v4_cost_event(
            event, budget_category="causal_pilot_60_usd",
            outcome_status="SUCCEEDED")
        self.assertEqual(adapted["provider_call_id"], "CALL-1")
        self.assertEqual(adapted["cached_input_tokens"], 2)

    def test_candidate_manifest_is_recomputable(self) -> None:
        manifest = build_candidate_manifest(ROOT)
        self.assertGreater(manifest["entry_count"], 10)
        self.assertTrue(verify_candidate_manifest(ROOT, manifest)["passed"])
        candidate_paths = {entry["path"] for entry in manifest["entries"]}
        self.assertIn(
            "controlled_content_generator_v2_001/gate1_v1_1_001/"
            "p7_successor_longrun_001/.gitignore", candidate_paths)
        self.assertFalse(any(
            "/.runtime/" in f"/{path}/" or Path(path).name.startswith(".env")
            or "secret" in Path(path).name.lower()
            or "credential" in Path(path).name.lower()
            for path in candidate_paths))
        empty = {"schema_version": "eval-spine-candidate-manifest-v1",
                 "scope": "IMPLEMENTATION_WITHOUT_REVIEW_OR_GENERATED_EVIDENCE",
                 "entry_count": 0, "entries": [], "manifest_digest": ""}
        unsigned = dict(empty)
        unsigned.pop("manifest_digest")
        empty["manifest_digest"] = digest_json(unsigned)
        self.assertFalse(verify_candidate_manifest(ROOT, empty)["passed"])

    def test_balanced_cross_assignment(self) -> None:
        items = [{"item_id": f"I{i}", "profile_id": f"CP{i % 3:02d}"}
                 for i in range(12)]
        assignments = balanced_cross_assign(items, ["R1", "R2", "R3", "R4"],
                                             seed="frozen", reviews_per_item=2)
        self.assertEqual(assignments,
                         balanced_cross_assign(items, ["R1", "R2", "R3", "R4"],
                                               seed="frozen", reviews_per_item=2))
        audit = assignment_audit(assignments, reviews_per_item=2)
        self.assertTrue(audit["passed"], audit)

    def test_whole_batch_hard_veto_is_not_acceptable_set_diagnostic(self) -> None:
        rows = [{"output_id": f"O{i}", "profile_id": f"CP{i:02d}",
                 "first_acceptable": i != 1, "formulaic": False,
                 "hard_veto": i == 1} for i in range(10)]
        result = whole_batch_metrics(rows, target_count=10)
        self.assertEqual(result["acceptable_set_hard_veto_count_diagnostic"], 0)
        self.assertEqual(result["whole_batch_veto_count"], 1)
        self.assertFalse(result["gate_batch_qualified"])

    def test_batch_and_stage_gates_reject_clone_denominators_and_empty_gates(self) -> None:
        clones = [{"output_id": "SAME", "profile_id": "CP01",
                   "first_acceptable": True, "formulaic": False,
                   "hard_veto": False} for _ in range(120)]
        result = whole_batch_metrics(clones, target_count=120)
        self.assertFalse(result["gate_batch_qualified"])
        self.assertEqual(result["duplicate_output_ids"], ["SAME"])
        self.assertEqual(stage_decision(stage="S6", gates={}, revision_count=0)["status"],
                         "BLOCKED")
        self.assertEqual(stage_decision(stage="TYPO", gates={"x": True},
                                        revision_count=0)["status"], "FAIL")
        s4 = {key: True for key in ("first_acceptance", "formulaic",
                                    "whole_batch_hard_veto_zero", "blind", "route", "audit")}
        self.assertEqual(stage_decision(stage="S4", gates=s4,
                                        revision_count=0)["status"], "PASS")

    def test_metering_and_accounting_do_not_invent_missing_numbers(self) -> None:
        event = {"schema_version": "eval-spine-cost-event-v1", "event_id": "E1",
                 "stage_id": "DEV", "task_kind": "MODEL",
                 "resource_kind": "MODEL_CALL",
                 "budget_category": "one_time_gold_and_measurement_usd",
                 "outcome_status": "SUCCEEDED",
                 "source_telemetry_event_digest": "a" * 64,
                 "object_id": "T1",
                 "attempt_id": "A1", "provider": "x", "model_revision": "m",
                 "provider_call_id": "C1", "input_tokens": 1,
                 "cached_input_tokens": 0, "output_tokens": 1,
                 "price_snapshot_id": "r", "model_cost_usd": .1,
                 "reviewer_minutes": 0, "reviewer_identity": None,
                 "labor_rate_snapshot_id": None, "human_cost_usd": 0,
                 "wall_clock_seconds": .01,
                 "unavailable_reasons": {}, "event_digest": "not-closed"}
        self.assertFalse(metering_report([event])["qualified"])
        projection = project_scale(fixed_cost=1, positive_items=240, route_items=60,
                                   average_claims=5, per_claim_cost=.01,
                                   per_pair_screen_cost=.001, human_item_cost=.1,
                                   human_pair_cost=.2, candidate_pair_rate=.1)
        self.assertEqual(projection["within_profile_pair_count"], 1320)
        self.assertTrue(projection["diagnostic_only"])
        gate = accounting_integrity_gate([event])
        self.assertEqual(gate["status"], "STOP_COST_ACCOUNTING_MISSING")
        self.assertFalse(gate["passed"])
        self.assertFalse(gate["budget_blocking"])
        unavailable = copy.deepcopy(event)
        unavailable["model_cost_usd"] = None
        unavailable["unavailable_reasons"] = {
            "model_cost_usd": "provider receipt omitted price"}
        unsigned = dict(unavailable)
        unsigned.pop("event_digest")
        unavailable["event_digest"] = digest_json(unsigned)
        self.assertFalse(metering_report([unavailable])["qualified"])

    def test_accounting_gate_passes_complete_events_and_fails_closed(self) -> None:
        rate_card, events, expected_manifest, source_manifest = cost_fixture()
        decision = accounting_integrity_gate(
            events, rate_card=rate_card,
            expected_event_manifest=expected_manifest,
            source_event_manifest=source_manifest,
            as_of="2026-07-15T12:00:00+00:00")
        self.assertEqual(decision["status"], "PASS")
        self.assertTrue(decision["passed"])
        self.assertFalse(decision["budget_blocking"])
        self.assertEqual(decision["failed_gates"], [])
        self.assertEqual(decision["diagnostic_telemetry"]["event_count"],
                         len(events))
        # 少一个已发生调用的成本事件 = 与预登记清单不符 → 记账缺失即停
        missing_one = accounting_integrity_gate(
            events[:-1], rate_card=rate_card,
            expected_event_manifest=expected_manifest,
            source_event_manifest=source_manifest)
        self.assertEqual(missing_one["status"], "STOP_COST_ACCOUNTING_MISSING")
        self.assertIn("expected_event_manifest_matches",
                      missing_one["failed_gates"])
        # 投影保留为诊断遥测：键集为 PROJECTION_METRIC_KEYS 且防篡改
        report = metering_report(
            events, rate_card=rate_card,
            expected_event_manifest=expected_manifest,
            source_event_manifest=source_manifest)
        assumption = scale_assumption_fixture(report)
        projection = build_scale_projection(
            assumption_manifest=assumption, cost_events=events,
            expected_event_manifest=expected_manifest,
            source_event_manifest=source_manifest, rate_card=rate_card,
            generated_at="2026-07-15T10:00:00+00:00")
        self.assertEqual(set(projection["p50"]), PROJECTION_METRIC_KEYS)
        tampered_assumption = copy.deepcopy(assumption)
        tampered_assumption["basis_metering_report_digest"] = "0" * 64
        unsigned_assumption = dict(tampered_assumption)
        unsigned_assumption.pop("manifest_digest")
        tampered_assumption["manifest_digest"] = digest_json(
            unsigned_assumption)
        with self.assertRaises(ValueError):
            build_scale_projection(
                assumption_manifest=tampered_assumption, cost_events=events,
                expected_event_manifest=expected_manifest,
                source_event_manifest=source_manifest, rate_card=rate_card,
                generated_at="2026-07-15T10:00:00+00:00")

    def test_s3_diagnostic_gate_and_s2_without_budget_key(self) -> None:
        gates = {"causal_interpretability": True,
                 "minimum_useful_effect": False,
                 "hard_veto_zero": True, "anomalies_reported": True}
        decision = stage_decision(stage="S3", gates=gates, revision_count=0)
        self.assertEqual(decision["status"], "S3_DIAGNOSTIC_COMPLETE")
        self.assertEqual(decision["gate_type"], "DIAGNOSTIC")
        self.assertTrue(decision["s3_safety_exit_all_green"])
        lifted = stage_decision(stage="S3", gates={**gates,
                                                   "minimum_useful_effect": True},
                                revision_count=0)
        self.assertEqual(lifted["status"], "PASS")
        safety_fail = stage_decision(stage="S3",
                                     gates={**gates, "hard_veto_zero": False},
                                     revision_count=0)
        self.assertEqual(safety_fail["status"], "FAIL")
        self.assertFalse(safety_fail["s3_safety_exit_all_green"])
        anomaly_unreported = stage_decision(
            stage="S3", gates={**gates, "anomalies_reported": False},
            revision_count=0)
        self.assertEqual(anomaly_unreported["status"], "FAIL")
        s2 = stage_decision(stage="S2",
                            gates={"profile_capacity": True,
                                   "supported_assignments": True,
                                   "cost_latency_forecast": True},
                            revision_count=0)
        self.assertEqual(s2["status"], "PASS")
        budget_key_regression = stage_decision(
            stage="S2", gates={"profile_capacity": True,
                               "supported_assignments": True,
                               "cost_latency_forecast": True, "budget": True},
            revision_count=0)
        self.assertEqual(budget_key_regression["status"], "FAIL")
        self.assertEqual(budget_key_regression["unknown_gate_keys"], ["budget"])

    def test_metering_recomputes_rate_card_and_rejects_duplicate_or_negative_events(self) -> None:
        rate_card, events, expected_manifest, source_manifest = cost_fixture()
        report = metering_report(
            events, rate_card=rate_card,
            expected_event_manifest=expected_manifest,
            source_event_manifest=source_manifest)
        self.assertTrue(report["qualified"], report)
        self.assertEqual(report["total_human_cost_usd"], 60)
        self.assertEqual(report["total_input_tokens"], 60)
        clones = [copy.deepcopy(events[0]) for _ in range(12)]
        self.assertFalse(metering_report(
            clones, rate_card=rate_card,
            expected_event_manifest=expected_manifest,
            source_event_manifest=source_manifest)["qualified"])
        negative = copy.deepcopy(events)
        negative[0]["model_cost_usd"] = -1
        unsigned = dict(negative[0])
        unsigned.pop("event_digest")
        negative[0]["event_digest"] = digest_json(unsigned)
        self.assertFalse(metering_report(
            negative, rate_card=rate_card,
            expected_event_manifest=expected_manifest,
            source_event_manifest=source_manifest)["qualified"])
        missing_digest = copy.deepcopy(events)
        missing_digest[0]["event_digest"] = None
        self.assertFalse(metering_report(
            missing_digest, rate_card=rate_card,
            expected_event_manifest=expected_manifest,
            source_event_manifest=source_manifest)["qualified"])

    def test_disclosure_and_omission_have_separate_actions(self) -> None:
        obligations = [{"obligation_id": "SYNTH", "required": True,
                        "check_kind": "MARKER_ANY",
                        "accepted_markers": ["合成内容"]}]
        manifest = {"schema_version": "eval-spine-disclosure-obligation-manifest-v1",
                    "source_input_digest": "a" * 64, "complete": True,
                    "obligations": obligations, "manifest_digest": ""}
        unsigned = dict(manifest)
        unsigned.pop("manifest_digest")
        manifest["manifest_digest"] = digest_json(unsigned)
        self.assertEqual(check_required_disclosures("真实口吻", manifest)["action"],
                         "HARD_VETO")
        self.assertEqual(check_required_disclosures("合成内容", manifest)["action"],
                         "ALLOW")
        self.assertEqual(check_required_disclosures("合成内容", {})["action"],
                         "HUMAN_REVIEW")
        self.assertEqual(omission_risk_action(detector_flagged=False,
                                              detector_qualified=False),
                         "HUMAN_REVIEW")
        self.assertEqual(omission_risk_action(detector_flagged=False,
                                              detector_qualified=True,
                                              risk="HIGH"),
                         "HUMAN_REVIEW")
        self.assertEqual(omission_risk_action(detector_flagged=False,
                                              detector_qualified=True,
                                              risk="LOW"), "ALLOW")


class M0ConjunctionTests(unittest.TestCase):
    @staticmethod
    def _qualification_manifest(
            record_manifest_digests: dict[str, str]) -> dict[str, object]:
        manifest: dict[str, object] = {
            "schema_version": "eval-spine-calibration-manifest-v1",
            "manifest_id": "M0-TEST-QUALIFICATION",
            "data_grid": "G3_MEASUREMENT_QUALIFICATION",
            "content_status": "ADJUDICATED", "sealed": True,
            "case_count": 700,
            "class_counts": dict(QUALIFICATION_CLASS_MINIMUMS),
            "dataset_manifest_digest": QUALIFICATION_DATASET_DIGEST,
            "source_manifest_digest": "a" * 64,
            "gold_manifest_digest": "b" * 64,
            "record_manifest_digests": dict(sorted(record_manifest_digests.items())),
            "qualification_record_index_digest": "c" * 64,
            "allowed_consumers": [
                "INDEPENDENT_AUDITOR", "QUALIFICATION_ADJUDICATOR",
                "QUALIFICATION_REVIEWER_A", "QUALIFICATION_REVIEWER_B",
                "QUALIFICATION_RUNNER", "SEALED_DATA_CUSTODIAN"],
            "prohibited_consumers": [
                "EVALUATOR_DEVELOPER", "GENERATOR_AUTHOR",
                "GENERATOR_DEVELOPER", "RUBRIC_DEVELOPER"],
            "leakage_status": "PASS", "notes": ["sealed test manifest"],
            "manifest_digest": "",
        }
        unsigned = dict(manifest)
        unsigned.pop("manifest_digest")
        manifest["manifest_digest"] = digest_json(unsigned)
        return manifest

    @staticmethod
    def _record_manifests() -> list[dict[str, object]]:
        manifests = []
        for module_id in REQUIRED_MODULES:
            records = []
            for role, minimum in MODULE_RECORD_ROLE_MINIMUMS[module_id].items():
                records.extend({
                    "case_id": f"{module_id}-{role}-{index}",
                    "case_digest": digest_json({
                        "module_id": module_id, "record_role": role, "index": index}),
                    "record_role": role,
                } for index in range(minimum))
            manifests.append(build_record_manifest(
                module_id=module_id, records=records,
                dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST))
        return manifests

    @staticmethod
    def _audit_integrity_report() -> dict[str, object]:
        report: dict[str, object] = {
            "schema_version": "eval-spine-audit-integrity-report-v1",
            "report_id": "M0-AUDIT-INTEGRITY-TEST",
            "dataset_manifest_digest": QUALIFICATION_DATASET_DIGEST,
            "visibility_partition": "HIDDEN",
            "gate_verdicts": {key: True for key in AUDIT_INTEGRITY_GATES},
            "evidence_manifest_digest": "8" * 64,
            "executed_by": "INDEPENDENT-INTEGRITY-RUNNER",
            "executed_at": "2026-07-15T00:00:00Z", "report_digest": "",
        }
        unsigned = dict(report)
        unsigned.pop("report_digest")
        report["report_digest"] = digest_json(unsigned)
        return report

    @staticmethod
    def _independent_report(
            qualification_manifest_digest: str,
            reports: list[dict[str, object]],
            record_manifests: list[dict[str, object]],
            audit_integrity_report_digest: str) -> dict[str, object]:
        report: dict[str, object] = {
            "schema_version": "eval-spine-m0-independent-adjudication-v1",
            "report_id": "M0-INDEPENDENT-ADJUDICATION",
            "reviewer_identity": "INDEPENDENT-M0-AUDITOR",
            "reviewer_provenance": {"reviewer_kind": "HUMAN",
                                    "model_revision": None, "prompt_digest": None},
            "independence_attestation": {
                "did_not_build_gold": True, "did_not_develop_evaluator": True,
                "did_not_develop_generator": True,
                "did_not_author_module_reports": True},
            "qualification_manifest_digest": qualification_manifest_digest,
            "module_report_digests": {
                row["module_id"]: row["report_digest"] for row in reports},
            "record_manifest_digests": {
                row["module_id"]: row["record_manifest_digest"]
                for row in record_manifests},
            "recomputed_module_result_digests": {
                row["module_id"]: row["result_digest"] for row in reports},
            "gate_verdicts": {key: True for key in INDEPENDENT_ADJUDICATION_GATES},
            "gate_evidence_digests": {
                key: digest_json({"gate": key, "evidence": "recomputed"})
                for key in INDEPENDENT_ADJUDICATION_GATES},
            "review_assignment_digest": "6" * 64,
            "reviewer_separation_digest": "7" * 64,
            "audit_integrity_report_digest": audit_integrity_report_digest,
            "open_finding_count": 0, "status": "PASS",
            "reviewed_at": "2026-07-15T00:00:00Z", "report_digest": "",
        }
        unsigned = dict(report)
        unsigned.pop("report_digest")
        report["report_digest"] = digest_json(unsigned)
        return report

    def test_fixed_module_set_and_report_refs_are_fail_closed(self) -> None:
        empty = build_m0_decision(
            [], record_manifests=[], required_report_refs={},
            qualification_manifest=None, independent_adjudication_report=None,
            audit_integrity_report=None)
        self.assertEqual(empty["status"], "BLOCKED")
        self.assertEqual(set(empty["missing_module_ids"]), set(REQUIRED_MODULES))

    def test_closed_module_reports_can_form_a_conjunctive_pass(self) -> None:
        record_manifests = self._record_manifests()
        record_by_module = {row["module_id"]: row for row in record_manifests}
        qualification_manifest = self._qualification_manifest({
            module_id: row["record_manifest_digest"]
            for module_id, row in record_by_module.items()})
        reports = [
            close_module_report(
                module_id=module_id,
                result={"qualified": True,
                        "gates": {key: True for key in MODULE_GATE_KEYS[module_id]}},
                dataset_manifest_digest=QUALIFICATION_DATASET_DIGEST,
                record_manifest=record_by_module[module_id],
                method_version=1, evaluator_revision_digest="4" * 64,
                execution_receipt_digest="5" * 64)
            for module_id in REQUIRED_MODULES
        ]
        self.assertEqual(verify_module_report(reports[0]), [])
        refs = {name: digest_json({"report": name}) for name in REQUIRED_REPORT_REFS}
        report_ref_by_module = {
            "reference_assertion_extraction": "reference_assertion_extraction_report",
            "claim_atomization": "claim_atomization_report",
            "risk_classification": "risk_classification_report",
            "entailment": "entailment_report",
            "fact_chain_end_to_end": "fact_chain_end_to_end_report",
            "formulaic_construct": "formulaic_construct_report",
            "disclosure_and_omission": "disclosure_and_omission_report",
            "review_calibration": "reviewer_agreement_report",
            "cost": "cost_report",
        }
        for report in reports:
            refs[report_ref_by_module[report["module_id"]]] = report["report_digest"]
        refs["immutable_qualification_manifest"] = qualification_manifest["manifest_digest"]
        audit_integrity = self._audit_integrity_report()
        refs["audit_integrity_report"] = audit_integrity["report_digest"]
        independent = self._independent_report(
            qualification_manifest["manifest_digest"], reports, record_manifests,
            audit_integrity["report_digest"])
        refs["independent_adjudication_report"] = independent["report_digest"]
        decision = build_m0_decision(
            reports, record_manifests=record_manifests,
            required_report_refs=refs,
            qualification_manifest=qualification_manifest,
            independent_adjudication_report=independent,
            audit_integrity_report=audit_integrity)
        self.assertEqual(decision["status"], "PASS", decision)
        self.assertEqual(verify_m0_decision(
            decision, module_reports=reports, record_manifests=record_manifests,
            required_report_refs=refs, qualification_manifest=qualification_manifest,
            independent_adjudication_report=independent,
            audit_integrity_report=audit_integrity), [])
        tampered = copy.deepcopy(reports)
        tampered[0]["result"]["qualified"] = False
        failed = build_m0_decision(
            tampered, record_manifests=record_manifests,
            required_report_refs=refs,
            qualification_manifest=qualification_manifest,
            independent_adjudication_report=independent,
            audit_integrity_report=audit_integrity)
        self.assertEqual(failed["status"], "FAIL")
        self.assertIn("reference_assertion_extraction",
                      failed["invalid_module_reports"])


class LegacyShadowTests(unittest.TestCase):
    def test_r5_known_veto_shadow_is_read_only_and_not_qualification(self) -> None:
        fixture = PACKAGE / "fixtures/r5_known_veto_regression.v1.jsonl"
        before = fixture.read_bytes()
        result = r5_shadow_audit(ROOT, fixture)
        self.assertEqual(result["expected_known_veto_ids"],
                         result["development_rule_detected_ids"])
        self.assertEqual(result["legacy_machine_hard_failure_count"], 0)
        # 回显值必须等于实际状态真源，而非硬编码常量（实际态/期望态分离）
        actual_status = json.loads(
            (PACKAGE / "calibration/M0_STATUS.v1.json").read_text(
                encoding="utf-8"))["status"]
        self.assertEqual(result["m0_qualification_status"], actual_status)
        self.assertIn(actual_status,
                      {"NOT_QUALIFIED", "QUALIFIED", "DIAGNOSTIC_FINAL"})
        self.assertEqual(fixture.read_bytes(), before)

    def test_empty_integrity_snapshot_is_not_m0_pass(self) -> None:
        snapshot = integrity_snapshot(ROOT)
        self.assertEqual(snapshot["artifact_integrity_status"], "PASS")
        self.assertEqual(snapshot["m0_qualification_status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
