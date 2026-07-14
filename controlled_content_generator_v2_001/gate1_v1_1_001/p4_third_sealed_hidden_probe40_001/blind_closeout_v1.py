#!/usr/bin/env python3
"""Build a neutral blind-review projection without mutating third-P4 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


if not __debug__:
    raise SystemExit(2)


REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_third_sealed_hidden_probe40_001"
)
SOURCE_OUTPUTS = TASK_ROOT / "run/positive_20_first_outputs.v1.0.jsonl"
ALLOWED_INPUT = TASK_ROOT / "contract/curator_allowed_input.v1.0.json"
SUCCESSOR_ROOT = TASK_ROOT / "review_successor"
BLIND_PACKET = SUCCESSOR_ROOT / "neutral_blind_packet.v1.0.jsonl"
BLIND_MAPPING = SUCCESSOR_ROOT / "neutral_blind_mapping.v1.0.jsonl"
PRODUCT_CATALOG = SUCCESSOR_ROOT / "product_catalog.v1.0.jsonl"
PREFLIGHT_RESULTS = SUCCESSOR_ROOT / "preflight_results.v1.0.jsonl"
DERIVATION_MANIFEST = SUCCESSOR_ROOT / "blind_derivation_manifest.v1.0.yaml"
AS_BUILT_MANIFEST = SUCCESSOR_ROOT / "original_third_p4_as_built_manifest.v1.0.yaml"

EVENT_CODE_RE = re.compile(r"P4T3-EVT-CP(?:0[1-9]|1\d|20)-[0-9A-Za-z-]+")
ANY_CP_CODE_RE = re.compile(r"CP\d{2}")
SURFACE_FIELDS = (
    "synthetic_disclosure",
    "title",
    "body",
    "spoken_lines",
    "cta",
    "visual_execution",
    "audio_execution",
)


class BlindCloseoutError(ValueError):
    """Stable fail-closed blind closeout error."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def bind_digest(value: dict[str, Any], digest_key: str) -> dict[str, Any]:
    value[digest_key] = object_digest(value, digest_key)
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(canonical_json(row) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def write_yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(value), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def scalar_strings(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return [item for child in value.values() for item in scalar_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in scalar_strings(child)]
    return [value] if isinstance(value, str) else []


def profile_rows(root: Path) -> list[dict[str, Any]]:
    allowed = json.loads((root / ALLOWED_INPUT).read_text(encoding="utf-8"))
    profiles = allowed.get("profile_schemas")
    if not isinstance(profiles, list) or len(profiles) != 20:
        raise BlindCloseoutError("E_PROFILE_COUNT")
    return sorted(profiles, key=lambda row: str(row["content_product_type_id"]))


def product_labels(profiles: Sequence[Mapping[str, Any]]) -> set[str]:
    return {
        str(value)
        for row in profiles
        for value in (row["content_product_type_id"], row["chinese_label"])
    }


def event_mapping(outputs: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    found: set[str] = set()
    for output in outputs:
        audience = {field: output[field] for field in SURFACE_FIELDS}
        found.update(EVENT_CODE_RE.findall(canonical_json(audience)))
    if len(found) != 20:
        raise BlindCloseoutError(f"E_EVENT_CODE_COUNT:{len(found)}")
    return {
        code: f"P4T3-EVT-BLIND-{sha256_bytes(code.encode('utf-8'))[:12]}"
        for code in sorted(found)
    }


def replace_exact(value: Any, replacements: Mapping[str, str]) -> Any:
    if isinstance(value, Mapping):
        return {key: replace_exact(child, replacements) for key, child in value.items()}
    if isinstance(value, list):
        return [replace_exact(child, replacements) for child in value]
    if isinstance(value, str):
        result = value
        for source, target in replacements.items():
            result = result.replace(source, target)
        return result
    return value


def leak_codes(value: Any, labels: set[str]) -> list[str]:
    text = "\n".join(scalar_strings(value))
    codes: set[str] = set()
    if ANY_CP_CODE_RE.search(text):
        codes.add("INTERNAL_CP_CODE")
    if any(label in text for label in labels):
        codes.add("PRODUCT_LABEL")
    if EVENT_CODE_RE.search(text):
        codes.add("UNNEUTRALIZED_EVENT_CODE")
    return sorted(codes)


def blind_rows(
    outputs: Sequence[Mapping[str, Any]],
    replacements: Mapping[str, str],
    labels: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blind: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    projected: list[tuple[Mapping[str, Any], dict[str, Any]]] = []
    for output in outputs:
        audience = {field: output[field] for field in SURFACE_FIELDS}
        neutral = replace_exact(audience, replacements)
        if leak_codes(neutral, labels):
            raise BlindCloseoutError(
                f"E_DERIVED_LABEL_LEAK:{output['request_id']}:{leak_codes(neutral, labels)}"
            )
        projection_digest = sha256_bytes(canonical_json(neutral).encode("utf-8"))
        projected.append((output, {**neutral, "projection_digest": projection_digest}))
    projected.sort(key=lambda pair: pair[1]["projection_digest"])
    for index, (output, neutral) in enumerate(projected, 1):
        blind_id = f"P4T3-NEUTRAL-{index:02d}-{neutral['projection_digest'][:12]}"
        row = bind_digest(
            {
                "schema_version": "gate1-third-p4-neutral-blind-v1.0",
                "blind_item_id": blind_id,
                **neutral,
                "content_product_identity_hidden": True,
                "request_identity_hidden": True,
                "blind_row_digest": "",
            },
            "blind_row_digest",
        )
        blind.append(row)
        mapping.append(
            bind_digest(
                {
                    "schema_version": "gate1-third-p4-neutral-mapping-v1.0",
                    "blind_item_id": blind_id,
                    "request_id": output["request_id"],
                    "profile_id": output["profile_id"],
                    "source_output_digest": output["output_digest"],
                    "mapping_digest": "",
                },
                "mapping_digest",
            )
        )
    return blind, mapping


def catalog_rows(profiles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        bind_digest(
            {
                "schema_version": "gate1-third-p4-neutral-profile-catalog-v1.0",
                "profile_id": profile["content_product_type_id"],
                "chinese_label": profile["chinese_label"],
                "business_purpose": profile["business_purpose"],
                "founder_core_inputs": profile["founder_core_inputs"],
                "catalog_row_digest": "",
            },
            "catalog_row_digest",
        )
        for profile in profiles
    ]


def preflight_rows(
    outputs: Sequence[Mapping[str, Any]],
    replacements: Mapping[str, str],
    labels: set[str],
) -> list[dict[str, Any]]:
    sample = {field: outputs[0][field] for field in SURFACE_FIELDS}
    neutral = replace_exact(sample, replacements)
    restored = replace_exact(neutral, {target: source for source, target in replacements.items()})
    cases = [
        {
            "case_id": "PREFLIGHT_EXACT_REGISTERED_CODE_NEUTRALIZED",
            "passed": not leak_codes(neutral, labels) and neutral != sample,
        },
        {
            "case_id": "PREFLIGHT_NON_CODE_FACT_TEXT_PRESERVED",
            "passed": restored == sample,
        },
        {
            "case_id": "PREFLIGHT_UNKNOWN_INTERNAL_CODE_REJECTED",
            "passed": "INTERNAL_CP_CODE" in leak_codes(
                {"body": ["未知代号P4T3-EVT-CP77-999不得放行"]}, labels
            ),
        },
        {
            "case_id": "PREFLIGHT_REAL_PRODUCT_LABEL_REJECTED",
            "passed": "PRODUCT_LABEL" in leak_codes(
                {"body": ["内部答案为CP12"]}, labels
            ),
        },
    ]
    if not all(row["passed"] for row in cases):
        raise BlindCloseoutError("E_PREFLIGHT")
    return [bind_digest({**row, "case_digest": ""}, "case_digest") for row in cases]


def original_as_built(root: Path) -> dict[str, Any]:
    task = root / TASK_ROOT
    excluded = {Path("blind_closeout_v1.py")}
    rows: list[dict[str, str]] = []
    for path in sorted(task.rglob("*")):
        relative = path.relative_to(task)
        if not path.is_file() or relative in excluded or relative.is_relative_to(Path("review_successor")):
            continue
        if "__pycache__" in relative.parts:
            continue
        rows.append({"path": relative.as_posix(), "sha256": sha256_file(path)})
    return bind_digest(
        {
            "schema_version": "gate1-third-p4-original-as-built-v1.0",
            "source_head": "17753363612bc45446b709107c7d277d266b0024",
            "file_count": len(rows),
            "files": rows,
            "manifest_digest": "",
        },
        "manifest_digest",
    )


def expected_payload(root: Path) -> dict[str, Any]:
    outputs = read_jsonl(root / SOURCE_OUTPUTS)
    if len(outputs) != 20:
        raise BlindCloseoutError("E_OUTPUT_COUNT")
    profiles = profile_rows(root)
    labels = product_labels(profiles)
    replacements = event_mapping(outputs)
    blind, mapping = blind_rows(outputs, replacements, labels)
    catalog = catalog_rows(profiles)
    preflight = preflight_rows(outputs, replacements, labels)
    manifest = bind_digest(
        {
            "schema_version": "gate1-third-p4-neutral-blind-derivation-v1.0",
            "task_id": "GATE1_V11_300_BASELINE_SCALE_AND_INDEPENDENT_FREEZE_001",
            "source_outputs_sha256": sha256_file(root / SOURCE_OUTPUTS),
            "source_allowed_input_sha256": sha256_file(root / ALLOWED_INPUT),
            "replacement_policy": "EXACT_REGISTERED_EVENT_CODES_ONLY",
            "replacement_count": len(replacements),
            "replacements": replacements,
            "blind_count": len(blind),
            "catalog_count": len(catalog),
            "preflight_count": len(preflight),
            "blind_packet_sha256": sha256_bytes(
                "".join(canonical_json(row) + "\n" for row in blind).encode("utf-8")
            ),
            "mapping_sha256": sha256_bytes(
                "".join(canonical_json(row) + "\n" for row in mapping).encode("utf-8")
            ),
            "catalog_sha256": sha256_bytes(
                "".join(canonical_json(row) + "\n" for row in catalog).encode("utf-8")
            ),
            "all_20_leak_scan_pass": all(not leak_codes(row, labels) for row in blind),
            "source_outputs_mutated": False,
            "derivation_digest": "",
        },
        "derivation_digest",
    )
    return {
        "blind": blind,
        "mapping": mapping,
        "catalog": catalog,
        "preflight": preflight,
        "manifest": manifest,
        "as_built": original_as_built(root),
    }


def build(root: Path) -> None:
    payload = expected_payload(root)
    write_jsonl(root / BLIND_PACKET, payload["blind"])
    write_jsonl(root / BLIND_MAPPING, payload["mapping"])
    write_jsonl(root / PRODUCT_CATALOG, payload["catalog"])
    write_jsonl(root / PREFLIGHT_RESULTS, payload["preflight"])
    write_yaml(root / DERIVATION_MANIFEST, {"neutral_blind_derivation": payload["manifest"]})
    write_yaml(root / AS_BUILT_MANIFEST, {"original_third_p4_as_built": payload["as_built"]})


def check(root: Path) -> None:
    payload = expected_payload(root)
    expected_jsonl = {
        BLIND_PACKET: payload["blind"],
        BLIND_MAPPING: payload["mapping"],
        PRODUCT_CATALOG: payload["catalog"],
        PREFLIGHT_RESULTS: payload["preflight"],
    }
    for relative, rows in expected_jsonl.items():
        if read_jsonl(root / relative) != rows:
            raise BlindCloseoutError(f"E_MATERIALIZATION_DRIFT:{relative}")
    manifest = yaml.safe_load((root / DERIVATION_MANIFEST).read_text(encoding="utf-8"))
    if manifest != {"neutral_blind_derivation": payload["manifest"]}:
        raise BlindCloseoutError("E_DERIVATION_MANIFEST_DRIFT")
    as_built = yaml.safe_load((root / AS_BUILT_MANIFEST).read_text(encoding="utf-8"))
    if as_built != {"original_third_p4_as_built": payload["as_built"]}:
        raise BlindCloseoutError("E_AS_BUILT_DRIFT")


def selftest(root: Path) -> None:
    payload = expected_payload(root)
    manifest = payload["manifest"]
    if manifest["blind_count"] != 20 or manifest["replacement_count"] != 20:
        raise BlindCloseoutError("E_SELFTEST_COUNTS")
    if manifest["all_20_leak_scan_pass"] is not True:
        raise BlindCloseoutError("E_SELFTEST_SCAN")


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.build:
            build(REPO_ROOT)
        elif args.check:
            check(REPO_ROOT)
        else:
            selftest(REPO_ROOT)
    except (BlindCloseoutError, KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
