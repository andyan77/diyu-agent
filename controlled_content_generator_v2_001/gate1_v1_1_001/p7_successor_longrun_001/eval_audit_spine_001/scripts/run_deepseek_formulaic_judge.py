#!/usr/bin/env python3
"""执行一次受日预算保护的 DeepSeek 套路六轴评审并写摘要闭合回执。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
P7_ROOT = PACKAGE.parent
sys.path.insert(0, str(PACKAGE))

from spine.external_llm import (DailySpendLedger, DeepSeekFormulaicJudge,
                                load_env_value, load_external_budget,
                                load_provider_rate_card)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left-id", required=True)
    parser.add_argument("--left-text", required=True)
    parser.add_argument("--right-id", required=True)
    parser.add_argument("--right-text", required=True)
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--reviewer-identity", required=True)
    parser.add_argument("--prompt-revision", default="FORMULAIC-RUBRIC-V1.1")
    parser.add_argument("--max-output-tokens", type=int, default=800)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    rate_card = load_provider_rate_card(
        PACKAGE / "contract" / "deepseek_rate_card.v1.json")
    budget = load_external_budget(
        PACKAGE / "contract" / "external_llm_budget.v1.json",
        rate_card_digest=rate_card["rate_card_digest"])
    api_key = os.environ.get("DEEPSEEK_API_KEY") or load_env_value(
        P7_ROOT / ".env.deepseek", "DEEPSEEK_API_KEY")
    ledger = DailySpendLedger(
        P7_ROOT / ".runtime" / "deepseek_spend.jsonl",
        daily_budget_cny=budget["daily_hard_ceiling_cny"])
    receipt = DeepSeekFormulaicJudge(
        api_key=api_key, rate_card=rate_card, external_budget=budget,
        ledger=ledger).judge(
            left_id=args.left_id, left_text=args.left_text,
            right_id=args.right_id, right_text=args.right_text,
            family_id=args.family_id,
            reviewer_identity=args.reviewer_identity,
            prompt_revision=args.prompt_revision,
            max_output_tokens=args.max_output_tokens)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.receipt.with_suffix(args.receipt.suffix + ".tmp")
    temporary.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    temporary.replace(args.receipt)
    print(json.dumps({
        "call_status": receipt["call_status"],
        "provider_call_id": receipt["provider_call_id"],
        "cost_cny_budget_basis": receipt["cost_cny_budget_basis"],
        "receipt_digest": receipt["receipt_digest"],
    }, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["call_status"] == "VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
