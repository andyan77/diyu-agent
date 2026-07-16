"""Shared fail-closed contracts for the isolated Gate1 v4 recovery."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

TASK_ID = "GATE1_V11_V4_RECOVERY_001"
GENERATOR_VERSION = "gate1-v1.1-v4-recovery-v0.1"
RULE_VERSION = "gate1-v1.1-v4-recovery-rules-v0.2"
TEST_ASSIGNMENT_SCHEMA = "gate1-test-assignment-v1"
MATERIAL_SCHEMA = "gate1-v4-material-v1"
POLICY_SCHEMA = "gate1-v4-material-policy-v1"
REQUEST_SCHEMA = "gate1-v4-author-request-v1"
RAW_OUTPUT_SCHEMA = "gate1-v4-author-raw-v1"
OUTPUT_SCHEMA = "gate1-v4-author-output-v1"
GATE_REPORT_SCHEMA = "gate1-v4-deterministic-gate-report-v1"
METRICS_SCHEMA = "gate1-v4-qualification-metrics-v1"
TELEMETRY_EVENT_SCHEMA = "gate1-v4-telemetry-event-v1"
RUN_MANIFEST_SCHEMA = "gate1-v4-run-manifest-v1"

SURFACE_POLICIES = frozenset({"MUST_SURFACE", "MAY_SURFACE", "CONTROL_ONLY"})
VERDICT_GRADES = frozenset({"A", "B", "C", "D"})


class ContractError(ValueError):
    """Stable fail-closed contract error."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ContractError(f"{code}:{detail}" if detail else code)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def digest_object(value: Mapping[str, Any], digest_field: str) -> str:
    reduced = {key: item for key, item in value.items() if key != digest_field}
    return sha256_text(canonical_json(reduced))


def close_digest(value: dict[str, Any], digest_field: str) -> dict[str, Any]:
    value[digest_field] = digest_object(value, digest_field)
    return value


def validate_digest(value: Mapping[str, Any], digest_field: str, code: str) -> None:
    digest = value.get(digest_field)
    require(isinstance(digest, str) and len(digest) == 64, code, "missing_or_bad_digest")
    require(digest == digest_object(value, digest_field), code, "digest_mismatch")


def as_mapping(value: Any, code: str) -> Mapping[str, Any]:
    require(isinstance(value, Mapping), code)
    return value


def as_text(value: Any, code: str, *, allow_empty: bool = False) -> str:
    require(isinstance(value, str), code)
    if not allow_empty:
        require(bool(value.strip()), code)
    return value


def as_bool(value: Any, code: str) -> bool:
    require(isinstance(value, bool), code)
    return value


def as_int(value: Any, code: str, *, minimum: int | None = None) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), code)
    if minimum is not None:
        require(value >= minimum, code)
    return value


def as_number(value: Any, code: str, *, minimum: float | None = None) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), code)
    number = float(value)
    if minimum is not None:
        require(number >= minimum, code)
    return number


def text_list(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), code)
    if not allow_empty:
        require(bool(value), code)
    result: list[str] = []
    for item in value:
        result.append(as_text(item, code))
    return result


def unique_text_list(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    result = text_list(value, code, allow_empty=allow_empty)
    require(len(result) == len(set(result)), code, "duplicate")
    return result


def exact_fields(value: Mapping[str, Any], expected: Iterable[str], code: str) -> None:
    expected_set = set(expected)
    actual = set(value)
    require(actual == expected_set, code, ",".join(sorted(actual ^ expected_set)))


def unique_by(rows: Iterable[Mapping[str, Any]], key: str, code: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        item_id = as_text(row.get(key), code)
        require(item_id not in result, code, item_id)
        result[item_id] = row
    return result


def load_jsonl(path: Any) -> list[dict[str, Any]]:
    """Read JSONL without mutating the source path."""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), "E_JSONL_OBJECT", str(line_number))
        rows.append(value)
    return rows
