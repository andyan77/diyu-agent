#!/usr/bin/env python3
"""Formal cost schema round-trip and fail-closed tests."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
sys.path.insert(0, str(PACKAGE))

from spine.canonical import digest_json
from spine.cost import (BUDGET_CATEGORY_KEYS, REQUIRED_CEILING_KEYS,
                        budget_gate, build_scale_projection, metering_report)


def _close(value: dict, digest_field: str) -> dict:
    unsigned = dict(value)
    unsigned.pop(digest_field)
    value[digest_field] = digest_json(unsigned)
    return value


def _cost_artifacts() -> dict[str, dict]:
    rate_card = _close({
        "schema_version": "eval-spine-rate-card-v1",
        "snapshot_id": "RATE-1",
        "captured_at": "2026-07-15T08:00:00+00:00",
        "currency": "USD",
        "rates": {
            "provider::model": {
                "input_per_million": 1.0,
                "cached_input_per_million": 0.5,
                "output_per_million": 2.0,
            }
        },
        "labor_rates": {"R1": 60.0},
        "rate_card_digest": "",
    }, "rate_card_digest")

    events: list[dict] = []
    for index in range(12):
        is_human = index >= 6
        event = {
            "schema_version": "eval-spine-cost-event-v1",
            "event_id": f"E-{index}",
            "stage_id": "M0",
            "task_kind": "REVIEW" if is_human else "MODEL",
            "object_id": f"O-{index}",
            "resource_kind": "HUMAN_REVIEW" if is_human else "MODEL_CALL",
            "budget_category": "one_time_gold_and_measurement_usd",
            "outcome_status": "SUCCEEDED",
            "source_telemetry_event_digest": digest_json(
                {"source_event": index}),
            "attempt_id": f"A-{index}",
            "provider": None if is_human else "provider",
            "model_revision": None if is_human else "model",
            "provider_call_id": None if is_human else f"CALL-{index}",
            "input_tokens": None if is_human else 10,
            "cached_input_tokens": None if is_human else 2,
            "output_tokens": None if is_human else 3,
            "price_snapshot_id": None if is_human else "RATE-1",
            "model_cost_usd": None if is_human else 15 / 1_000_000,
            "reviewer_minutes": 10 if is_human else 0,
            "reviewer_identity": "R1" if is_human else None,
            "labor_rate_snapshot_id": "RATE-1" if is_human else None,
            "human_cost_usd": 10 if is_human else 0,
            "wall_clock_seconds": 0.1,
            "unavailable_reasons": {},
            "event_digest": "",
        }
        events.append(_close(event, "event_digest"))

    expected_manifest = _close({
        "schema_version": "eval-spine-expected-cost-events-v1",
        "stage_scope": "M0",
        "registered_before_run": True,
        "custodian_identity": "COST-CUSTODIAN",
        "approved_by": "COST-OWNER",
        "approved_at": "2026-07-15T07:00:00+00:00",
        "source_run_manifest_digest": "d" * 64,
        "expected_events": [
            {
                "event_id": row["event_id"],
                "stage_id": row["stage_id"],
                "task_kind": row["task_kind"],
                "resource_kind": row["resource_kind"],
                "budget_category": row["budget_category"],
                "object_id": row["object_id"],
            }
            for row in events
        ],
        "manifest_digest": "",
    }, "manifest_digest")

    source_manifest = _close({
        "schema_version": "eval-spine-source-cost-events-v1",
        "run_id": "M0",
        "source_run_manifest_digest": "d" * 64,
        "generated_from_append_only_log": True,
        "includes_failed_attempts": True,
        "source_events": [
            {
                "event_id": row["event_id"],
                "resource_kind": row["resource_kind"],
                "outcome_status": row["outcome_status"],
                "source_telemetry_event_digest": row[
                    "source_telemetry_event_digest"],
                "provider_call_id": row["provider_call_id"],
                "wall_clock_seconds": row["wall_clock_seconds"],
            }
            for row in events
        ],
        "manifest_digest": "",
    }, "manifest_digest")

    report = metering_report(
        events,
        rate_card=rate_card,
        expected_event_manifest=expected_manifest,
        source_event_manifest=source_manifest,
    )
    if report["qualified"] is not True:
        raise AssertionError(report)

    workloads: dict[str, list[dict]] = {}
    for index, category in enumerate(sorted(BUDGET_CATEGORY_KEYS)):
        workloads[category] = [
            {
                "workload_id": f"MODEL-{index}",
                "resource_kind": "MODEL_CALL",
                "provider": "provider",
                "model_revision": "model",
                "p50_event_count": 1,
                "p95_event_count": 2,
                "p50_input_tokens_per_event": 10,
                "p95_input_tokens_per_event": 20,
                "p50_cached_input_tokens_per_event": 2,
                "p95_cached_input_tokens_per_event": 4,
                "p50_output_tokens_per_event": 3,
                "p95_output_tokens_per_event": 6,
                "p50_wall_clock_seconds_per_event": 0.1,
                "p95_wall_clock_seconds_per_event": 0.2,
            },
            {
                "workload_id": f"HUMAN-{index}",
                "resource_kind": "HUMAN_REVIEW",
                "reviewer_identity": "R1",
                "p50_event_count": 1,
                "p95_event_count": 2,
                "p50_reviewer_minutes_per_event": 1,
                "p95_reviewer_minutes_per_event": 2,
                "p50_wall_clock_seconds_per_event": 60,
                "p95_wall_clock_seconds_per_event": 120,
            },
        ]
    assumption = _close({
        "schema_version": "eval-spine-scale-assumption-manifest-v1",
        "scope": "FULL_PROGRAM_THROUGH_240_PLUS_60",
        "registered_before_scale": True,
        "custodian_identity": "COST-CUSTODIAN",
        "approved_by": "COST-OWNER",
        "approved_at": "2026-07-15T09:00:00+00:00",
        "price_snapshot_id": "RATE-1",
        "basis_metering_report_digest": report["report_digest"],
        "basis_event_record_manifest_digest": report[
            "event_record_manifest_digest"],
        "single_item_wall_clock_seconds": {"p50": 60, "p95": 120},
        "stage_workloads": workloads,
        "manifest_digest": "",
    }, "manifest_digest")

    projection = build_scale_projection(
        assumption_manifest=assumption,
        cost_events=events,
        expected_event_manifest=expected_manifest,
        source_event_manifest=source_manifest,
        rate_card=rate_card,
        generated_at="2026-07-15T10:00:00+00:00",
    )
    budget = _close({
        "schema_version": "eval-audit-spine-cost-budget-v1",
        "contract_id": "EAS-COST-BUDGET-V1",
        "currency": "USD",
        "approval_status": "APPROVED",
        "approved_by": "FOUNDER",
        "approved_at": "2026-07-15T09:00:00+00:00",
        "price_snapshot_id": "RATE-1",
        "price_snapshot_captured_at": "2026-07-15T08:00:00+00:00",
        "rate_card_digest": rate_card["rate_card_digest"],
        "cost_classification_manifest_digest": expected_manifest[
            "manifest_digest"],
        "hard_ceilings": {key: 1000 for key in REQUIRED_CEILING_KEYS},
        "budget_digest": "",
    }, "budget_digest")
    decision = budget_gate(
        projection,
        budget,
        assumption_manifest=assumption,
        cost_events=events,
        expected_event_manifest=expected_manifest,
        source_event_manifest=source_manifest,
        rate_card=rate_card,
        as_of="2026-07-15T12:00:00+00:00",
    )
    if decision["status"] != "PASS":
        raise AssertionError(decision)

    return {
        "rate_card": rate_card,
        "expected_event_manifest": expected_manifest,
        "source_event_manifest": source_manifest,
        "metering_report": report,
        "scale_assumption_manifest": assumption,
        "scale_projection": projection,
        "budget_decision": decision,
    }


class CostSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema_path = PACKAGE / "schema" / "cost.v1.schema.json"
        cls.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema, format_checker=FormatChecker())
        cls.artifacts = _cost_artifacts()

    def assertValid(self, value: dict) -> None:
        errors = sorted(
            self.validator.iter_errors(value), key=lambda error: list(error.path))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def assertInvalid(self, value: dict) -> None:
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_current_builders_round_trip_all_seven_cost_objects(self) -> None:
        for name, artifact in self.artifacts.items():
            with self.subTest(name=name):
                self.assertValid(artifact)

    def test_malformed_digest_is_rejected_for_every_cost_object(self) -> None:
        digest_fields = {
            "rate_card": "rate_card_digest",
            "expected_event_manifest": "manifest_digest",
            "source_event_manifest": "manifest_digest",
            "metering_report": "report_digest",
            "scale_assumption_manifest": "manifest_digest",
            "scale_projection": "projection_digest",
            "budget_decision": "decision_digest",
        }
        for name, digest_field in digest_fields.items():
            with self.subTest(name=name):
                tampered = copy.deepcopy(self.artifacts[name])
                tampered[digest_field] = "0" * 63
                self.assertInvalid(tampered)

    def test_exact_field_sets_reject_added_or_missing_fields(self) -> None:
        for name, artifact in self.artifacts.items():
            with self.subTest(name=name, mutation="added"):
                tampered = copy.deepcopy(artifact)
                tampered["unregistered_field"] = True
                self.assertInvalid(tampered)
            with self.subTest(name=name, mutation="missing"):
                tampered = copy.deepcopy(artifact)
                tampered.pop("schema_version")
                self.assertInvalid(tampered)

    def test_resource_type_branches_fail_closed(self) -> None:
        expected = copy.deepcopy(self.artifacts["expected_event_manifest"])
        expected["expected_events"][0]["resource_kind"] = "GPU"
        self.assertInvalid(expected)

        source = copy.deepcopy(self.artifacts["source_event_manifest"])
        source["source_events"][0]["resource_kind"] = "HUMAN_REVIEW"
        self.assertIsNotNone(source["source_events"][0]["provider_call_id"])
        self.assertInvalid(source)

        assumption = copy.deepcopy(
            self.artifacts["scale_assumption_manifest"])
        category = sorted(BUDGET_CATEGORY_KEYS)[0]
        assumption["stage_workloads"][category][0][
            "resource_kind"] = "HUMAN_REVIEW"
        self.assertInvalid(assumption)


if __name__ == "__main__":
    unittest.main()
