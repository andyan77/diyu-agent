#!/usr/bin/env python3
"""Run or verify the deterministic P2 component-review checkpoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from p2_checkpoint_documents import build_documents, validate_documents
from p2_component_model import (
    AB_PATH,
    ADDITION_PATH,
    COMPONENT_CANDIDATES_PATH,
    CONTROL_RULES_PATH,
    CURRENT_OWNER_PATH,
    EDGE_PATH,
    RESULT_PATH,
    REVIEW_PACKET_PATH,
    ROOT,
    SUCCESSOR_PATH,
    TASK_ROOT,
    canonical_json,
    require,
)
from p2_final_materializer import (
    FINAL_RESULT_PATH,
    PRIMARY_IMPORT_DIR,
    build_final_documents,
    validate_final_documents,
)
from p2_targeted_repair import (
    TARGETED_RESULT_PATH,
    build_targeted_repair_documents,
    validate_targeted_repair_documents,
)


if not __debug__:
    sys.stderr.write("P2 materializer refuses python -O\n")
    raise SystemExit(2)


def selected_documents(root: Path, phase: str) -> dict[Path, bytes]:
    if phase == "final":
        documents = build_final_documents(root)
        validate_final_documents(documents)
        return documents
    if phase == "targeted-repair":
        documents = build_targeted_repair_documents(root)
        validate_targeted_repair_documents(documents)
        return documents
    documents = build_documents(root)
    validate_documents(documents)
    return documents


def write_outputs(root: Path, phase: str) -> list[str]:
    documents = selected_documents(root, phase)
    written: list[str] = []
    for relative_path, content in documents.items():
        require(
            relative_path == CURRENT_OWNER_PATH
            or relative_path.is_relative_to(TASK_ROOT),
            "E_WRITE_SURFACE",
            relative_path.as_posix(),
        )
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
            written.append(relative_path.as_posix())
    return written


def check_outputs(root: Path, phase: str) -> list[str]:
    documents = selected_documents(root, phase)
    return [
        path.as_posix()
        for path, content in documents.items()
        if not (root / path).is_file() or (root / path).read_bytes() != content
    ]


def checkpoint_selftest(root: Path) -> int:
    first = build_documents(root)
    second = build_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        ("component_activation", SUCCESSOR_PATH, '"active":false', '"active":true'),
        (
            "control_rule_supply",
            CONTROL_RULES_PATH,
            '"contributes_component_supply":false',
            '"contributes_component_supply":true',
        ),
        (
            "ab_shared_session",
            AB_PATH,
            '"INDEPENDENT_SESSION_B"',
            '"INDEPENDENT_SESSION_A"',
        ),
        ("p3_unlock", RESULT_PATH, "p3_allowed: false", "p3_allowed: true"),
        (
            "core_number_change",
            RESULT_PATH,
            "historical_component_inventory: 86",
            "historical_component_inventory: 87",
        ),
        (
            "source_provenance_removed",
            COMPONENT_CANDIDATES_PATH,
            '"parent_assets":[',
            '"parent_assets_missing":[',
        ),
        (
            "edge_component_unknown",
            EDGE_PATH,
            '"component_id":"',
            '"component_id":"UNKNOWN-',
        ),
        (
            "review_prefilled",
            REVIEW_PACKET_PATH,
            '"prefilled_decision":null',
            '"prefilled_decision":"APPROVE"',
        ),
        (
            "unsupported_addition",
            ADDITION_PATH,
            "necessary_addition_count: 0",
            "necessary_addition_count: 1",
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        text = mutated[path].decode("utf-8")
        require(before in text, "E_SELFTEST_PATTERN", name)
        mutated[path] = text.replace(before, after, 1).encode("utf-8")
        try:
            validate_documents(mutated)
        except (ValueError, KeyError, TypeError):
            continue
        failures.append(name)
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "negative_case_count": len(mutations),
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def final_selftest(root: Path) -> int:
    first = build_final_documents(root)
    second = build_final_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_final_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        (
            "result_readiness",
            FINAL_RESULT_PATH,
            "generator_qualified: false",
            "generator_qualified: true",
        ),
        (
            "result_p3_without_completion",
            FINAL_RESULT_PATH,
            "p2_complete: true",
            "p2_complete: false",
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        content = mutated[path].decode("utf-8")
        require(before in content, "E_FINAL_SELFTEST_PATTERN", name)
        mutated[path] = content.replace(before, after, 1).encode("utf-8")
        try:
            validate_final_documents(mutated)
        except (ValueError, KeyError, TypeError):
            continue
        failures.append(name)
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "phase": "final",
                "negative_case_count": len(mutations),
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def targeted_repair_selftest(root: Path) -> int:
    first = build_targeted_repair_documents(root)
    second = build_targeted_repair_documents(root)
    failures: list[str] = []
    if first != second:
        failures.append("deterministic_second_run")
    try:
        validate_targeted_repair_documents(first)
    except ValueError as exc:
        failures.append(f"valid_fixture:{exc}")
    mutations: list[tuple[str, Path, str, str]] = [
        (
            "early_p3",
            TARGETED_RESULT_PATH,
            "p3_allowed: false",
            "p3_allowed: true",
        ),
        (
            "number_target",
            TARGETED_RESULT_PATH,
            "historical_component_inventory: 86",
            "historical_component_inventory: 87",
        ),
    ]
    for name, path, before, after in mutations:
        mutated = dict(first)
        content = mutated[path].decode("utf-8")
        require(before in content, "E_REPAIR_SELFTEST_PATTERN", name)
        mutated[path] = content.replace(before, after, 1).encode("utf-8")
        try:
            validate_targeted_repair_documents(mutated)
        except (ValueError, KeyError, TypeError):
            continue
        failures.append(name)
    status = "SELFTEST_PASS" if not failures else "SELFTEST_FAIL"
    sys.stdout.write(
        canonical_json(
            {
                "status": status,
                "phase": "targeted-repair",
                "negative_case_count": len(mutations),
                "failures": failures,
            }
        )
        + "\n"
    )
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument(
        "--phase",
        choices=("auto", "checkpoint", "targeted-repair", "final"),
        default="auto",
    )
    args = parser.parse_args()
    phase = args.phase
    if phase == "auto":
        phase = "final" if (ROOT / PRIMARY_IMPORT_DIR).is_dir() else "checkpoint"
    if args.selftest:
        if phase == "final":
            return final_selftest(ROOT)
        if phase == "targeted-repair":
            return targeted_repair_selftest(ROOT)
        return checkpoint_selftest(ROOT)
    if args.check:
        mismatches = check_outputs(ROOT, phase)
        sys.stdout.write(
            canonical_json(
                {
                    "status": "PASS" if not mismatches else "FAIL",
                    "phase": phase,
                    "mismatches": mismatches,
                }
            )
            + "\n"
        )
        return 0 if not mismatches else 1
    written = write_outputs(ROOT, phase)
    sys.stdout.write(
        canonical_json(
            {
                "status": "MATERIALIZED",
                "phase": phase,
                "written": written,
            }
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
