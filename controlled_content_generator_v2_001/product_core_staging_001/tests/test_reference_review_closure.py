#!/usr/bin/env python3
"""Reference assertion 双审与独立裁决证据闭包。"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
sys.path.insert(0, str(PACKAGE))

from spine.canonical import digest_json
from spine.source_index import (make_source_evidence_unit,
                                validate_reference_assertions)


SOURCE_TEXT = "四条空号，改发站内信。"
UNIT_A = make_source_evidence_unit(
    "SRC-1", SOURCE_TEXT, 0, len("四条空号".encode("utf-8")),
    authorization_ids=["AUTH-1"])
UNIT_B_START = len("四条空号，改发".encode("utf-8"))
UNIT_B = make_source_evidence_unit(
    "SRC-1", SOURCE_TEXT, UNIT_B_START,
    UNIT_B_START + len("站内信".encode("utf-8")),
    authorization_ids=["AUTH-1"])
EVIDENCE_UNITS = {
    UNIT_A["evidence_unit_id"]: UNIT_A,
    UNIT_B["evidence_unit_id"]: UNIT_B,
}


def make_assertion(review_ids: list[str], *, status: str = "DUAL_ADJUDICATED") -> dict:
    row = {
        "schema_version": "eval-spine-reference-assertion-v1",
        "assertion_id": "RA-1",
        "subject": "四条空号",
        "predicate": "can_call",
        "object_value": False,
        "unit": None,
        "time_scope": None,
        "polarity": "NEGATIVE",
        "modality": "OBSERVED",
        "preconditions": [],
        "evidence_unit_ids": list(EVIDENCE_UNITS),
        "authorization_ids": ["AUTH-1"],
        "risk_class": "HIGH",
        "extraction_origin": "HUMAN",
        "engine_provenance": {
            "engine_kind": "HUMAN",
            "engine_id": "CURATOR-1",
            "engine_revision": "v1",
            "prompt_or_rule_digest": None,
            "provider_call_id": None,
        },
        "verification_status": status,
        "review_ids": review_ids,
        "object_digest": "",
    }
    unsigned = dict(row)
    unsigned.pop("object_digest")
    row["object_digest"] = digest_json(unsigned)
    return row


def make_review(assertion: dict, review_id: str, identity: str, decision: str,
                *, role: str = "REVIEWER", reviewer_kind: str = "HUMAN") -> dict:
    evidence_ids = list(reversed(assertion["evidence_unit_ids"]))
    row = {
        "schema_version": "eval-spine-reference-assertion-review-v1",
        "review_id": review_id,
        "assertion_id": assertion["assertion_id"],
        "assertion_object_digest": assertion["object_digest"],
        "evidence_unit_ids": evidence_ids,
        "evidence_set_digest": digest_json({
            "assertion_id": assertion["assertion_id"],
            "assertion_object_digest": assertion["object_digest"],
            "evidence_unit_ids": sorted(assertion["evidence_unit_ids"]),
        }),
        "reviewer_identity": identity,
        "reviewer_kind": reviewer_kind,
        "model_revision": "deepseek-reviewer-v1" if reviewer_kind == "AI" else None,
        "prompt_digest": "a" * 64 if reviewer_kind == "AI" else None,
        "reviewer_role": role,
        "decision": decision,
        "evidence_digest": digest_json([
            {"evidence_unit_id": evidence_id,
             "object_digest": EVIDENCE_UNITS[evidence_id]["object_digest"]}
            for evidence_id in sorted(assertion["evidence_unit_ids"])
        ]),
        "review_digest": "",
    }
    unsigned = dict(row)
    unsigned.pop("review_digest")
    row["review_digest"] = digest_json(unsigned)
    return row


def validate(assertion: dict, reviews: list[dict]) -> dict:
    return validate_reference_assertions(
        [assertion],
        evidence_units_by_id=EVIDENCE_UNITS,
        source_text_by_source_id={"SRC-1": SOURCE_TEXT},
        review_records_by_id={row["review_id"]: row for row in reviews},
    )


def reseal_review(review: dict) -> None:
    unsigned = dict(review)
    unsigned.pop("review_digest")
    review["review_digest"] = digest_json(unsigned)


class ReferenceReviewClosureTests(unittest.TestCase):
    def test_two_digest_closed_confirms_pass(self) -> None:
        assertion = make_assertion(["REV-1", "REV-2"])
        reviews = [
            make_review(assertion, "REV-1", "reviewer-A", "CONFIRM"),
            make_review(assertion, "REV-2", "reviewer-B", "CONFIRM",
                        reviewer_kind="AI"),
        ]
        result = validate(assertion, reviews)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["referenced_review_record_count"], 2)

        schema = json.loads((PACKAGE / "schema/evidence_chain.v1.schema.json").read_text(
            encoding="utf-8"))
        Draft202012Validator(schema).validate(reviews[0])
        Draft202012Validator(schema).validate(reviews[1])

    def test_disagreement_requires_distinct_confirming_adjudicator(self) -> None:
        assertion = make_assertion(["REV-1", "REV-2", "ADJ-1"])
        reviews = [
            make_review(assertion, "REV-1", "reviewer-A", "CONFIRM"),
            make_review(assertion, "REV-2", "reviewer-B", "REJECT"),
            make_review(assertion, "ADJ-1", "adjudicator-C", "CONFIRM",
                        role="ADJUDICATOR"),
        ]
        self.assertTrue(validate(assertion, reviews)["passed"])

        missing = make_assertion(["REV-1", "REV-2"])
        missing_reviews = [
            make_review(missing, "REV-1", "reviewer-A", "CONFIRM"),
            make_review(missing, "REV-2", "reviewer-B", "REJECT"),
        ]
        result = validate(missing, missing_reviews)
        self.assertFalse(result["passed"])
        self.assertIn("disagreement_requires_confirming_adjudicator:RA-1",
                      result["errors"])

    def test_same_person_and_self_reported_identity_map_fail_closed(self) -> None:
        assertion = make_assertion(["REV-1", "REV-2"])
        same_person = [
            make_review(assertion, "REV-1", "same-person", "CONFIRM"),
            make_review(assertion, "REV-2", "same-person", "CONFIRM"),
        ]
        result = validate(assertion, same_person)
        self.assertFalse(result["passed"])
        self.assertIn("independent_reviewer_identity_unproven:RA-1", result["errors"])

        legacy = validate_reference_assertions(
            [assertion], evidence_units_by_id=EVIDENCE_UNITS,
            source_text_by_source_id={"SRC-1": SOURCE_TEXT},
            reviewer_identity_by_review_id={"REV-1": "A", "REV-2": "B"})
        self.assertFalse(legacy["passed"])
        self.assertIn("legacy_self_reported_reviewer_identity_not_accepted:RA-1",
                      legacy["errors"])
        self.assertIn("review_records_missing:RA-1", legacy["errors"])

    def test_decision_assertion_and_evidence_tampering_fail_closed(self) -> None:
        assertion = make_assertion(["REV-1", "REV-2"])
        baseline = [
            make_review(assertion, "REV-1", "reviewer-A", "CONFIRM"),
            make_review(assertion, "REV-2", "reviewer-B", "CONFIRM"),
        ]
        mutations = []

        changed_decision = copy.deepcopy(baseline)
        changed_decision[0]["decision"] = "REJECT"
        reseal_review(changed_decision[0])
        mutations.append((changed_decision,
                          "disagreement_requires_confirming_adjudicator:RA-1"))

        changed_assertion = copy.deepcopy(baseline)
        changed_assertion[0]["assertion_id"] = "RA-OTHER"
        reseal_review(changed_assertion[0])
        mutations.append((changed_assertion,
                          "review_assertion_binding_mismatch:RA-1:REV-1"))

        changed_evidence = copy.deepcopy(baseline)
        changed_evidence[0]["evidence_unit_ids"] = ["EV-1"]
        changed_evidence[0]["evidence_set_digest"] = digest_json({
            "assertion_id": assertion["assertion_id"],
            "assertion_object_digest": assertion["object_digest"],
            "evidence_unit_ids": ["EV-1"],
        })
        reseal_review(changed_evidence[0])
        mutations.append((changed_evidence,
                          "review_evidence_binding_mismatch:RA-1:REV-1"))

        changed_evidence_digest = copy.deepcopy(baseline)
        changed_evidence_digest[0]["evidence_digest"] = "f" * 64
        reseal_review(changed_evidence_digest[0])
        mutations.append((changed_evidence_digest,
                          "review_evidence_digest_mismatch:RA-1:REV-1"))

        for reviews, expected_error in mutations:
            with self.subTest(expected_error=expected_error):
                result = validate(assertion, reviews)
                self.assertFalse(result["passed"])
                self.assertIn(expected_error, result["errors"])

    def test_adjudicator_must_be_a_third_identity(self) -> None:
        assertion = make_assertion(["REV-1", "REV-2", "ADJ-1"])
        reviews = [
            make_review(assertion, "REV-1", "reviewer-A", "CONFIRM"),
            make_review(assertion, "REV-2", "reviewer-B", "REJECT"),
            make_review(assertion, "ADJ-1", "reviewer-A", "CONFIRM",
                        role="ADJUDICATOR"),
        ]
        result = validate(assertion, reviews)
        self.assertFalse(result["passed"])
        self.assertIn("independent_reviewer_identity_unproven:RA-1", result["errors"])

    def test_malformed_assertion_evidence_fails_without_crashing(self) -> None:
        assertion = make_assertion(["REV-1", "REV-2"])
        reviews = [
            make_review(assertion, "REV-1", "reviewer-A", "CONFIRM"),
            make_review(assertion, "REV-2", "reviewer-B", "CONFIRM"),
        ]
        assertion["evidence_unit_ids"] = None
        unsigned = dict(assertion)
        unsigned.pop("object_digest")
        assertion["object_digest"] = digest_json(unsigned)
        result = validate(assertion, reviews)
        self.assertFalse(result["passed"])
        self.assertIn("invalid_evidence_unit_ids:RA-1", result["errors"])


if __name__ == "__main__":
    unittest.main()
