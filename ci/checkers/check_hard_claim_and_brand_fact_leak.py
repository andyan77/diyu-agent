#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from gkb_intake_common import Finding, build_result, emit_result, iter_data_files, load_structured, walk

GATE_ID = "check_hard_claim_and_brand_fact_leak"
SCANNED_DIRS = ("03_raw_drafts", "04_aligned_candidates", "05_rich_body_blocks", "08_outbox", "09_serving_specs")

RULES = {
    "KIG_CONCRETE_BRAND_FACT": re.compile(r"\b(Nike|Adidas|Apple|Gucci|Uniqlo|Lululemon|Zara|H&M)\b", re.I),
    "KIG_CONCRETE_PRODUCT_OR_SKU": re.compile(r"\bSKU\b|A123|货号|款号|specific product", re.I),
    "KIG_CONCRETE_STORE_OR_CITY": re.compile(r"Beijing|Shanghai|Guangzhou|Shenzhen|New York|London|具体门店|门店名称|named store", re.I),
    "KIG_PERSON_OR_CUSTOMER_FEEDBACK": re.compile(r"customer feedback|named person|real person|客户反馈|真人|创始人说", re.I),
    "KIG_TEST_REPORT_OR_CERTIFICATION": re.compile(r"test report|inspection report|检测报告|认证|certified", re.I),
    "KIG_HARD_CLAIM_LEAK": re.compile(
        r"guarantee|definitely|will increase|must improve|cure|医学|法律|金融|功效承诺|转化率提升|销量提升",
        re.I,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local rule-based checker for hard claims and concrete facts.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def scan_value(path: Path, value: object, location: str) -> list[Finding]:
    if not isinstance(value, str):
        return []
    findings: list[Finding] = []
    for code, pattern in RULES.items():
        match = pattern.search(value)
        if match:
            findings.append(
                Finding(
                    code=code,
                    path=str(path),
                    location=location,
                    message=f"blocked text matched local rule: {match.group(0)!r}",
                )
            )
    return findings


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        data = load_structured(path)
        for _key, value, location in walk(data):
            findings.extend(scan_value(path, value, location))
    return findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_candidate_with_source_anchor.yaml")
    negative_claim = Path("fixtures/gkb_intake/negative/hard_claim_leak.yaml")
    negative_brand = Path("fixtures/gkb_intake/negative/concrete_brand_fact.yaml")
    return not check_paths([positive]) and bool(check_paths([negative_claim, negative_brand]))


def main() -> int:
    args = parse_args()
    files = iter_data_files(args.root, SCANNED_DIRS)
    findings = check_paths(files)
    result = build_result(GATE_ID, len(files), findings)
    if args.selftest and not run_selftest():
        result = build_result(
            GATE_ID,
            len(files),
            findings
            + [
                Finding(
                    code="KIG_SELFTEST_FAILED",
                    path="fixtures/gkb_intake",
                    message="positive fixture must pass and hard claim / brand fact fixtures must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
