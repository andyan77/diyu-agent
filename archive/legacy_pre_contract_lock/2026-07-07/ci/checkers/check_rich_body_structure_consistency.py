#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from gkb_intake_common import Finding, build_result, emit_result, iter_data_files, load_structured

GATE_ID = "check_rich_body_structure_consistency"
SCANNED_DIRS = ("05_rich_body_blocks",)

REQUIRED_BLOCKS = (
    "concept_mechanism",
    "domain_logic",
    "content_generation_usage",
    "merchandising_or_retail_usage",
    "transformation_rules",
    "generic_micro_scenarios",
    "anti_patterns",
    "boundary_language",
    "retrieval_phrases",
    "capability_consumption_hint",
)

CONCRETE_PATTERN = re.compile(r"\b(Nike|Adidas|SKU|Beijing|Shanghai|named store|customer feedback|货号)\b|具体门店|门店名称", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate rich_body_blocks structure and generic boundary.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def iter_rich_bodies(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        bodies: list[dict[str, Any]] = []
        if isinstance(value.get("rich_body_blocks"), dict):
            bodies.append(value["rich_body_blocks"])
        elif any(key in value for key in REQUIRED_BLOCKS):
            bodies.append(value)
        for child in value.values():
            bodies.extend(iter_rich_bodies(child))
        return bodies
    if isinstance(value, list):
        bodies = []
        for child in value:
            bodies.extend(iter_rich_bodies(child))
        return bodies
    return []


def contains_concrete_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(CONCRETE_PATTERN.search(value))
    if isinstance(value, list):
        return any(contains_concrete_value(item) for item in value)
    if isinstance(value, dict):
        return any(contains_concrete_value(item) for item in value.values())
    return False


def check_body(path: Path, body: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for block in REQUIRED_BLOCKS:
        if block not in body:
            findings.append(Finding("KIG_RICH_BODY_MISSING_BLOCK", str(path), f"missing required block: {block}"))
    retrieval_phrases = body.get("retrieval_phrases")
    if not isinstance(retrieval_phrases, list) or not retrieval_phrases:
        findings.append(Finding("KIG_RETRIEVAL_PHRASES_INVALID", str(path), "retrieval_phrases must be a non-empty list"))
    else:
        for phrase in retrieval_phrases:
            if not isinstance(phrase, str) or len(phrase) > 80 or "." in phrase:
                findings.append(
                    Finding(
                        "KIG_RETRIEVAL_PHRASE_AS_PASSAGE",
                        str(path),
                        "retrieval_phrases must be short phrases, not passage text",
                    )
                )
    if contains_concrete_value(body.get("generic_micro_scenarios", [])):
        findings.append(
            Finding(
                "KIG_RICH_BODY_OVERREACH",
                str(path),
                "generic_micro_scenarios contains concrete brand, SKU, city, store, or feedback text",
            )
        )
    return findings


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        bodies = iter_rich_bodies(load_structured(path))
        if not bodies:
            findings.append(Finding("KIG_RICH_BODY_NOT_FOUND", str(path), "no rich_body_blocks object found"))
        for body in bodies:
            findings.extend(check_body(path, body))
    return findings


def run_selftest() -> bool:
    positive = Path("fixtures/gkb_intake/positive/valid_rich_body_blocks.yaml")
    negative = Path("fixtures/gkb_intake/negative/concrete_brand_fact.yaml")
    return not check_paths([positive]) and bool(check_paths([negative]))


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
                    message="positive rich body fixture must pass and concrete fact rich body fixture must fail",
                )
            ],
        )
    emit_result(result, args.report_json)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
