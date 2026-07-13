#!/usr/bin/env python3
"""Fail-closed owner for the explicitly authorized current ledger horizon."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


if not __debug__:
    print("check_current_ledger_owner refuses python -O", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = Path("10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml")
HORIZON_PATH = Path(
    "controlled_content_generator_v2_001/b_lane_independent_composition_dev_gate_001/"
    "phase_0/current_ledger_horizon.v0.1.yaml"
)
ROUTE_LINE = re.compile(r"^  route_migration_([^:]+):$")
TOP_LEVEL_LINE = re.compile(r"^  [A-Za-z0-9_]+:$")
READY_KEYS = frozenset(
    {
        "candidatepack_ready",
        "KE_ready",
        "RAG_ready",
        "DIFY_ready",
        "Serving_ready",
        "production_servable",
        "generation_eligible",
        "generation_allowed",
        "release_ready",
        "production_ready",
        "generator_qualified",
        "runtime_provider_adapter_qualified",
        "runtime_ingest_ready",
        "generation_600_allowed",
        "expand_3600_allowed",
    }
)


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_digest(value: dict[str, Any], excluded: set[str]) -> str:
    payload = {key: child for key, child in value.items() if key not in excluded}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_yaml_unique(path: Path) -> dict[str, Any]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"expected mapping in {path}")
    return value


def add_error(errors: list[dict[str, str]], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def route_blocks(text: str) -> tuple[dict[int, str], list[int], list[str]]:
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    order: list[int] = []
    shadows: list[str] = []
    for index, line in enumerate(lines):
        match = ROUTE_LINE.fullmatch(line)
        if match is None:
            continue
        suffix = match.group(1)
        if not suffix.isdigit():
            shadows.append(suffix)
            continue
        route_id = int(suffix)
        order.append(route_id)
        starts.append((route_id, index))
    blocks: dict[int, str] = {}
    for route_id, start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if TOP_LEVEL_LINE.fullmatch(lines[index]):
                end = index
                break
        blocks[route_id] = "\n".join(lines[start:end]) + "\n"
    return blocks, order, shadows


def recursive_values(value: Any, key_name: str) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == key_name:
                values.append(child)
            values.extend(recursive_values(child, key_name))
    elif isinstance(value, list):
        for child in value:
            values.extend(recursive_values(child, key_name))
    return values


def validate(root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    ledger_path = root / LEDGER_PATH
    horizon_path = root / HORIZON_PATH
    for path in (ledger_path, horizon_path):
        if not path.exists():
            add_error(errors, "E_REQUIRED_FILE", path.as_posix())
    if errors:
        return errors

    try:
        horizon_doc = load_yaml_unique(horizon_path)
        ledger_doc = load_yaml_unique(ledger_path)
    except (TypeError, ValueError, yaml.YAMLError) as exc:
        add_error(errors, "E_LEDGER_PARSE", str(exc))
        return errors

    horizon = horizon_doc.get("ledger_horizon")
    ledger = ledger_doc.get("grc_3600_execution_plan_status")
    if not isinstance(horizon, dict) or not isinstance(ledger, dict):
        add_error(errors, "E_SCHEMA", "missing ledger_horizon or ledger root")
        return errors

    if horizon.get("horizon_digest") != object_digest(horizon, {"horizon_digest"}):
        add_error(errors, "E_HORIZON_DIGEST", "digest mismatch")
    expected_policy = {
        "authorization_mode": "EXPLICIT_BOUNDED",
        "derivation_source": "FOUNDER_AUTHORIZED_HORIZON_FILE",
        "unknown_future_successor_allowed": False,
        "ledger_path": LEDGER_PATH.as_posix(),
    }
    for key, expected in expected_policy.items():
        if horizon.get(key) != expected:
            add_error(errors, "E_HORIZON_POLICY", f"{key}={horizon.get(key)}")

    start = horizon.get("frozen_route_start_id")
    previous = horizon.get("previous_terminal_route_id")
    terminal = horizon.get("authorized_terminal_route_id")
    authorized = horizon.get("authorized_new_route_ids")
    task_id = horizon.get("authorization_task_id")
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in (start, previous, terminal)):
        add_error(errors, "E_HORIZON_TYPES", "route bounds must be integers")
        return errors
    if not isinstance(authorized, list) or not all(
        isinstance(value, int) and not isinstance(value, bool) for value in authorized
    ):
        add_error(errors, "E_HORIZON_TYPES", "authorized_new_route_ids must be integer list")
        return errors
    if not isinstance(task_id, str) or not task_id:
        add_error(errors, "E_HORIZON_TYPES", "authorization_task_id missing")
        return errors
    expected_authorized = list(range(previous + 1, terminal + 1))
    if authorized != expected_authorized or start > previous or previous >= terminal:
        add_error(errors, "E_HORIZON_BOUNDS", str({"start": start, "previous": previous, "terminal": terminal}))

    text = ledger_path.read_text(encoding="utf-8")
    blocks, route_order, shadows = route_blocks(text)
    if shadows:
        add_error(errors, "E_ROUTE_SHADOW_KEY", str(shadows))
    owned_order = [route_id for route_id in route_order if route_id >= start]
    expected_order = list(range(start, terminal + 1))
    if owned_order != expected_order:
        add_error(errors, "E_ROUTE_SEQUENCE", str(owned_order))

    frozen_digests = horizon.get("frozen_route_sha256")
    if not isinstance(frozen_digests, dict):
        add_error(errors, "E_FROZEN_ROUTE_DIGESTS", "mapping missing")
        frozen_digests = {}
    expected_digest_keys = {str(route_id) for route_id in expected_order}
    if set(frozen_digests) != expected_digest_keys:
        add_error(errors, "E_FROZEN_ROUTE_DIGESTS", f"keys={sorted(frozen_digests)}")
    for route_id in expected_order:
        block = blocks.get(route_id)
        expected_digest = frozen_digests.get(str(route_id))
        if block is None or expected_digest != sha256_text(block):
            add_error(errors, "E_FROZEN_ROUTE_DIGEST", f"route_migration_{route_id}")

    for route_id in expected_order:
        migration = ledger.get(f"route_migration_{route_id}")
        if not isinstance(migration, dict):
            add_error(errors, "E_ROUTE_SCHEMA", f"route_migration_{route_id}")
            continue
        if "migration_digest" in migration and migration.get("migration_digest") != object_digest(
            migration, {"migration_digest"}
        ):
            add_error(errors, "E_ROUTE_OBJECT_DIGEST", f"route_migration_{route_id}")
    for route_id in authorized:
        migration = ledger.get(f"route_migration_{route_id}")
        if not isinstance(migration, dict) or migration.get("applied_by_task") != task_id:
            add_error(errors, "E_ROUTE_TASK_BINDING", f"route_migration_{route_id}")
        elif migration.get("additive_only") is not True or migration.get("no_readiness_flipped") is not True:
            add_error(errors, "E_ROUTE_DECLARATION", f"route_migration_{route_id}")

    latest = ledger.get(f"route_migration_{terminal}")
    if isinstance(latest, dict):
        for key in READY_KEYS:
            if any(value is True for value in recursive_values(latest, key)):
                add_error(errors, "E_READINESS_TRUE", key)
        baseline_values = recursive_values(latest, "accepted_baseline_count")
        if not baseline_values or any(value != 120 for value in baseline_values):
            add_error(errors, "E_BASELINE_COUNT", str(baseline_values))
        hidden_values = recursive_values(latest, "hidden_created_count")
        if not hidden_values or any(value != 0 for value in hidden_values):
            add_error(errors, "E_HIDDEN_COUNT", str(hidden_values))
    return errors


def remove_route(text: str, route_id: int) -> str:
    lines = text.splitlines()
    marker = f"  route_migration_{route_id}:"
    start = lines.index(marker)
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if TOP_LEVEL_LINE.fullmatch(lines[index]):
            end = index
            break
    return "\n".join(lines[:start] + lines[end:]) + "\n"


def mutate_route(text: str, route_id: int, old: str, new: str) -> str:
    blocks, _, _ = route_blocks(text)
    block = blocks[route_id]
    if old not in block:
        raise ValueError(f"mutation token absent from route {route_id}: {old}")
    return text.replace(block, block.replace(old, new, 1), 1)


def selftest(root: Path) -> int:
    baseline_errors = validate(root)
    if baseline_errors:
        print(
            json.dumps({"status": "SELFTEST_BASE_INVALID", "errors": baseline_errors}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    ledger_text = (root / LEDGER_PATH).read_text(encoding="utf-8")
    blocks, _, _ = route_blocks(ledger_text)
    tests: list[tuple[str, str, str]] = [
        (
            "append_route_migration_32",
            "E_ROUTE_SEQUENCE",
            ledger_text
            + "  route_migration_32:\n"
            + "    applied_by_task: UNAUTHORIZED\n"
            + "    additive_only: true\n"
            + "    no_readiness_flipped: true\n"
            + "    migration_digest: invalid\n",
        ),
        ("delete_route_migration_31", "E_ROUTE_SEQUENCE", remove_route(ledger_text, 31)),
        ("delete_lower_bound_entry", "E_ROUTE_SEQUENCE", remove_route(ledger_text, 19)),
        (
            "mutate_frozen_entry",
            "E_FROZEN_ROUTE_DIGEST",
            mutate_route(ledger_text, 19, "additive_only: true", "additive_only: false"),
        ),
        ("create_sequence_gap", "E_ROUTE_SEQUENCE", remove_route(ledger_text, 29)),
        ("duplicate_route_key", "E_LEDGER_PARSE", ledger_text + blocks[31]),
        (
            "add_shadow_key",
            "E_ROUTE_SHADOW_KEY",
            ledger_text + "  route_migration_31_shadow:\n    additive_only: true\n",
        ),
        (
            "readiness_tamper",
            "E_FROZEN_ROUTE_DIGEST",
            mutate_route(ledger_text, 31, "generator_qualified: false", "generator_qualified: true"),
        ),
        (
            "baseline_tamper",
            "E_FROZEN_ROUTE_DIGEST",
            mutate_route(ledger_text, 31, "accepted_baseline_count: 120", "accepted_baseline_count: 121"),
        ),
    ]
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ledger-owner-selftest-") as temporary:
        temp_root = Path(temporary)
        for path in (LEDGER_PATH, HORIZON_PATH):
            destination = temp_root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / path, destination)
        for name, expected_code, mutated_ledger in tests:
            (temp_root / LEDGER_PATH).write_text(mutated_ledger, encoding="utf-8")
            errors = validate(temp_root)
            codes = {error["code"] for error in errors}
            if expected_code not in codes:
                failures.append({"name": name, "expected": expected_code, "actual": sorted(codes)})
    if failures:
        print(json.dumps({"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": "SELFTEST_PASS", "case_count": len(tests)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest(ROOT)
    errors = validate(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 1
    horizon = load_yaml_unique(ROOT / HORIZON_PATH)["ledger_horizon"]
    print(
        json.dumps(
            {"status": "PASS", "authorized_terminal_route_id": horizon["authorized_terminal_route_id"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
