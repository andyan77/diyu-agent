from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from spine.canonical import digest_json
from spine.external_llm import (DailyBudgetExceeded, DailySpendLedger,
                                DeepSeekFormulaicJudge, ExternalJudgeError,
                                load_external_budget, load_provider_rate_card,
                                validate_formulaic_response)


PACKAGE = Path(__file__).resolve().parents[1]


class ExternalLlmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rate_card = load_provider_rate_card(
            PACKAGE / "contract" / "deepseek_rate_card.v1.json")
        self.budget = load_external_budget(
            PACKAGE / "contract" / "external_llm_budget.v1.json",
            rate_card_digest=self.rate_card["rate_card_digest"])
        self.assertEqual(self.budget["daily_hard_ceiling_cny"], 30)
        schema = json.loads((PACKAGE / "schema" /
                             "external_judge.v1.schema.json").read_text())
        validator = Draft202012Validator(schema)
        validator.validate(self.rate_card)
        validator.validate(self.budget)

    def test_daily_budget_is_reserved_before_call_and_digest_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = DailySpendLedger(Path(directory) / "spend.jsonl",
                                      daily_budget_cny=30)
            now = datetime(2026, 7, 15, tzinfo=timezone.utc)
            reservation = ledger.reserve(
                request_digest="a" * 64, reserved_cost_cny=20, now=now)
            with self.assertRaises(DailyBudgetExceeded):
                ledger.reserve(request_digest="b" * 64,
                               reserved_cost_cny=10.0000001, now=now)
            ledger.settle(reservation_id=reservation, request_digest="a" * 64,
                          actual_cost_cny=2, provider_call_id="CALL-1", now=now)
            ledger.reserve(request_digest="b" * 64,
                           reserved_cost_cny=28, now=now)
            rows = [json.loads(line) for line in
                    (Path(directory) / "spend.jsonl").read_text().splitlines()]
            schema = json.loads((PACKAGE / "schema" /
                                 "external_judge.v1.schema.json").read_text())
            validator = Draft202012Validator(schema)
            for row in rows:
                unsigned = dict(row)
                supplied = unsigned.pop("record_digest")
                self.assertEqual(supplied, digest_json(unsigned))
                validator.validate(row)

    def test_formulaic_call_returns_replayable_receipt_without_credential(self) -> None:
        captured: dict = {}

        def transport(url: str, headers: dict, payload: dict, timeout: float) -> dict:
            captured.update({"url": url, "headers": headers, "payload": payload,
                             "timeout": timeout})
            result = {
                "axes": {
                    "argument_spine": "DIFFERENT",
                    "evidence_progression": "DIFFERENT",
                    "limitation_function": "DIFFERENT",
                    "viewpoint_anchor": "DIFFERENT",
                    "closing_function": "DIFFERENT",
                    "transformation_depth": "STRUCTURAL_CHANGE",
                },
                "necessary_grammar_exception_id": None,
                "evidence_notes": ["论证和收尾功能不同"],
            }
            return {
                "id": "CALL-2", "model": "deepseek-v4-flash",
                "choices": [{"finish_reason": "stop", "message": {
                    "content": json.dumps(result, ensure_ascii=False)}}],
                "usage": {"prompt_tokens": 100,
                          "prompt_cache_hit_tokens": 20,
                          "prompt_cache_miss_tokens": 80,
                          "completion_tokens": 40, "total_tokens": 140},
            }

        with tempfile.TemporaryDirectory() as directory:
            ledger = DailySpendLedger(Path(directory) / "spend.jsonl",
                                      daily_budget_cny=30)
            judge = DeepSeekFormulaicJudge(
                api_key="test-only-key", rate_card=self.rate_card,
                external_budget=self.budget,
                ledger=ledger, transport=transport)
            receipt = judge.judge(
                left_id="L", left_text="先按工序解释", right_id="R",
                right_text="从顾客判断切入", family_id="JUDGMENT",
                reviewer_identity="AI-JUDGE-A", prompt_revision="RUBRIC-1")
        self.assertEqual(captured["url"],
                         "https://api.deepseek.com/chat/completions")
        self.assertEqual(receipt["formulaic_result"]["derived_verdict"],
                         "NOT_FORMULAIC")
        self.assertNotIn("test-only-key", json.dumps(receipt, ensure_ascii=False))
        unsigned = dict(receipt)
        supplied = unsigned.pop("receipt_digest")
        self.assertEqual(supplied, digest_json(unsigned))
        schema = json.loads((PACKAGE / "schema" /
                             "external_judge.v1.schema.json").read_text())
        Draft202012Validator(schema).validate(receipt)

    def test_malformed_response_and_corrupt_ledger_fail_closed(self) -> None:
        with self.assertRaises(ExternalJudgeError):
            validate_formulaic_response({"axes": {}})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spend.jsonl"
            path.write_text("{}\n", encoding="utf-8")
            ledger = DailySpendLedger(path, daily_budget_cny=30)
            with self.assertRaises(ExternalJudgeError):
                ledger.reserve(request_digest="a" * 64, reserved_cost_cny=1)

    def test_invalid_provider_content_is_settled_but_not_a_judgment(self) -> None:
        def invalid_transport(*_args) -> dict:
            return {
                "id": "CALL-BAD", "model": "deepseek-v4-flash",
                "choices": [{"finish_reason": "stop",
                             "message": {"content": "{\"axes\":{}}"}}],
                "usage": {"prompt_tokens": 10, "prompt_cache_hit_tokens": 0,
                          "prompt_cache_miss_tokens": 10,
                          "completion_tokens": 2, "total_tokens": 12},
            }

        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "spend.jsonl"
            judge = DeepSeekFormulaicJudge(
                api_key="test-only-key", rate_card=self.rate_card,
                external_budget=self.budget,
                ledger=DailySpendLedger(ledger_path, daily_budget_cny=30),
                transport=invalid_transport)
            receipt = judge.judge(
                left_id="L", left_text="甲", right_id="R", right_text="乙",
                family_id="JUDGMENT", reviewer_identity="AI-JUDGE-A",
                prompt_revision="RUBRIC-1")
            self.assertEqual(receipt["call_status"], "INVALID_RESPONSE")
            self.assertIsNone(receipt["formulaic_result"])
            rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
            self.assertEqual([row["record_type"] for row in rows],
                             ["RESERVATION", "SETTLEMENT"])


if __name__ == "__main__":
    unittest.main()
