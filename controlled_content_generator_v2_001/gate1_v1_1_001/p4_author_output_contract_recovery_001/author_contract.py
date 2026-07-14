#!/usr/bin/env python3
"""Fail-closed author interface and semantic-preserving serializer for Gate 1."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


if not __debug__:
    sys.stderr.write("author_contract refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "GATE1_V11_P5_PREREQUISITE_P4_AUTHOR_OUTPUT_RECOVERY_001"
OUTPUT_SCHEMA = "gate1-p4-author-output-contract-recovery-v1.0"
RAW_SCHEMA = "gate1-p4-author-semantic-output-v1.0"
MODEL_CAPABILITY = "gpt-5.6-sol"
REASONING_EFFORT = "high"
SERVICE_TIER = "priority"
FROZEN_P4_ROOT = ROOT / (
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_sealed_hidden_probe40_001"
)

RAW_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "run_id",
        "title",
        "body",
        "spoken_lines",
        "cta",
        "visual_execution",
        "audio_execution",
        "synthetic_disclosure",
        "semantic_surfaces",
        "semantic_claims",
        "semantic_component_usage",
        "author_attestation",
    }
)
RAW_SURFACE_FIELDS = frozenset(
    {
        "surface_kind",
        "text",
        "fact_ids",
        "source_ids",
        "authorization_ids",
    }
)
RAW_CLAIM_FIELDS = frozenset(
    {
        "claim_text",
        "fact_ids",
        "source_ids",
        "authorization_ids",
        "claim_boundary",
    }
)
RAW_COMPONENT_FIELDS = frozenset(
    {"component_id", "implementation_note", "surface_ordinals"}
)
EXPECTED_ATTESTATION = {
    "unbound_fact_added": False,
    "input_backfilled_after_authoring": False,
    "external_service_called": False,
    "second_candidate_generated": False,
    "review_performed_by_author": False,
}
ROLE_ALLOWED_SURFACE_KINDS = {
    "scene": ["body", "title", "visual_execution"],
    "trigger": ["body", "spoken_line", "title", "visual_execution"],
    "observable_action": ["body", "spoken_line", "visual_execution"],
    "transition": ["body", "visual_execution"],
    "visual_beat": ["body", "visual_execution"],
    "capture_instruction": ["audio_execution", "visual_execution"],
    "professional_judgment": ["body", "spoken_line"],
    "audience_facing_reasoning_move": [
        "body",
        "spoken_line",
        "visual_execution",
    ],
    "closing": ["body", "cta", "spoken_line", "visual_execution"],
    "narrative_mechanism_operator": [
        "body",
        "spoken_line",
        "visual_execution",
    ],
    "information_order_operator": [
        "body",
        "spoken_line",
        "title",
        "visual_execution",
    ],
    "visual_subject_operator": ["body", "visual_execution"],
    "sound_subject_operator": ["audio_execution", "spoken_line"],
    "rhythm_operator": [
        "audio_execution",
        "body",
        "spoken_line",
        "visual_execution",
    ],
    "ending_operator": ["body", "cta", "spoken_line", "visual_execution"],
}


class AuthorContractError(ValueError):
    """Stable fail-closed author-contract error."""


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        suffix = f":{detail}" if detail else ""
        raise AuthorContractError(f"{code}{suffix}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def object_digest(value: Mapping[str, Any], digest_key: str) -> str:
    payload = {key: child for key, child in value.items() if key != digest_key}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        require(isinstance(value, dict), "E_JSONL_OBJECT", f"{path}:{number}")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(canonical_json(row) for row in rows) + "\n"
    path.write_text(payload, encoding="utf-8")


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    require(isinstance(value, Mapping), code)
    return value


def _text(value: Any, code: str, *, allow_empty: bool = False) -> str:
    require(isinstance(value, str), code)
    require(allow_empty or bool(value.strip()), code)
    return value


def _text_list(value: Any, code: str, *, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), code)
    rows = [_text(item, code) for item in value]
    require(allow_empty or bool(rows), code)
    return rows


def _unique_text_list(
    value: Any, code: str, *, allow_empty: bool = False
) -> list[str]:
    rows = _text_list(value, code, allow_empty=allow_empty)
    require(len(rows) == len(set(rows)), code)
    return rows


def surface_sequence(raw: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows = [
        ("synthetic_disclosure", str(raw["synthetic_disclosure"])),
        ("title", str(raw["title"])),
    ]
    rows.extend(("body", text) for text in raw["body"])
    rows.extend(("spoken_line", text) for text in raw["spoken_lines"])
    if raw["cta"]:
        rows.append(("cta", str(raw["cta"])))
    rows.extend(("visual_execution", text) for text in raw["visual_execution"])
    rows.extend(("audio_execution", text) for text in raw["audio_execution"])
    return rows


def validate_request(request: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "task_id",
        "request_id",
        "request_digest",
        "profile_id",
        "assigned_variant",
        "run_order",
        "author_identity",
        "author_session_logical_id",
        "author_platform_agent_id",
        "model_capability_id",
        "reasoning_effort",
        "service_tier",
        "typed_material",
        "product_core_requirements",
        "approved_components",
        "structure_contract",
        "author_output_contract",
        "exact_author_contract",
    }
    require(required.issubset(request), "E_REQUEST_FIELDS")
    require(request.get("task_id") == TASK_ID, "E_REQUEST_TASK")
    require(request.get("model_capability_id") == MODEL_CAPABILITY, "E_MODEL")
    require(request.get("reasoning_effort") == REASONING_EFFORT, "E_REASONING")
    require(request.get("service_tier") == SERVICE_TIER, "E_SERVICE_TIER")
    require(
        request.get("request_digest") == object_digest(request, "request_digest"),
        "E_REQUEST_DIGEST",
    )
    contract = _mapping(request.get("exact_author_contract"), "E_EXACT_CONTRACT")
    require(contract.get("raw_top_level_fields") == sorted(RAW_FIELDS), "E_RAW_CONTRACT")
    require(
        contract.get("semantic_surface_fields") == sorted(RAW_SURFACE_FIELDS),
        "E_SURFACE_CONTRACT",
    )
    require(
        contract.get("semantic_claim_fields") == sorted(RAW_CLAIM_FIELDS),
        "E_CLAIM_CONTRACT",
    )
    require(
        contract.get("semantic_component_usage_fields")
        == sorted(RAW_COMPONENT_FIELDS),
        "E_COMPONENT_CONTRACT",
    )
    require(
        contract.get("author_attestation_fields_and_values")
        == EXPECTED_ATTESTATION,
        "E_ATTESTATION_CONTRACT",
    )
    require(
        contract.get("surface_kind_enum")
        == [
            "audio_execution",
            "body",
            "cta",
            "spoken_line",
            "synthetic_disclosure",
            "title",
            "visual_execution",
        ],
        "E_SURFACE_KIND_CONTRACT",
    )
    for key in (
        "component_pointer_must_bind_core_or_required_slot_fact",
        "component_pointer_must_use_role_compatible_surface",
    ):
        require(contract.get(key) is True, "E_COMPONENT_EVIDENCE_CONTRACT", key)
    require(
        contract.get("role_allowed_surface_kinds") == ROLE_ALLOWED_SURFACE_KINDS,
        "E_ROLE_SURFACE_CONTRACT",
    )
    require(contract.get("run_id_unique_across_batch") is True, "E_RUN_ID_CONTRACT")
    output_contract = _mapping(
        request.get("author_output_contract"), "E_OUTPUT_CONTRACT"
    )
    for key in (
        "one_first_semantic_output_only",
        "author_may_not_review_or_approve",
    ):
        require(output_contract.get(key) is True, "E_OUTPUT_CONTRACT", key)
    for key in ("publishable", "runtime_consumable", "may_enter_300"):
        require(output_contract.get(key) is False, "E_OUTPUT_BOUNDARY", key)
    requirements = request.get("product_core_requirements")
    require(isinstance(requirements, list) and bool(requirements), "E_CORE_REQUIREMENTS")
    for raw_requirement in requirements:
        requirement = _mapping(raw_requirement, "E_CORE_REQUIREMENT")
        _text(requirement.get("requirement_id"), "E_CORE_REQUIREMENT_ID")
        _unique_text_list(requirement.get("fact_ids"), "E_CORE_FACT_IDS")


def validate_raw(raw: Mapping[str, Any], request: Mapping[str, Any]) -> None:
    validate_request(request)
    require(set(raw) == RAW_FIELDS, "E_RAW_FIELD_SET")
    require(raw.get("schema_version") == RAW_SCHEMA, "E_RAW_SCHEMA")
    require(raw.get("request_id") == request.get("request_id"), "E_RAW_REQUEST")
    _text(raw.get("run_id"), "E_RAW_RUN_ID")
    _text(raw.get("title"), "E_RAW_TITLE")
    _text_list(raw.get("body"), "E_RAW_BODY")
    _text_list(raw.get("spoken_lines"), "E_RAW_SPOKEN", allow_empty=True)
    _text(raw.get("cta"), "E_RAW_CTA", allow_empty=True)
    _text_list(raw.get("visual_execution"), "E_RAW_VISUAL")
    _text_list(raw.get("audio_execution"), "E_RAW_AUDIO", allow_empty=True)
    disclosure = _text(raw.get("synthetic_disclosure"), "E_RAW_DISCLOSURE")
    require("合成" in disclosure and ("测试" in disclosure or "非真实" in disclosure), "E_RAW_DISCLOSURE")
    require(raw.get("author_attestation") == EXPECTED_ATTESTATION, "E_RAW_ATTESTATION")

    expected_surfaces = surface_sequence(raw)
    surfaces = raw.get("semantic_surfaces")
    require(isinstance(surfaces, list), "E_RAW_SURFACES")
    require(len(surfaces) == len(expected_surfaces), "E_RAW_SURFACE_COUNT")
    for raw_surface, expected in zip(surfaces, expected_surfaces, strict=True):
        surface = _mapping(raw_surface, "E_RAW_SURFACE_OBJECT")
        require(set(surface) == RAW_SURFACE_FIELDS, "E_RAW_SURFACE_FIELDS")
        require(
            (surface.get("surface_kind"), surface.get("text")) == expected,
            "E_RAW_SURFACE_EXACT_JOIN",
        )
        kind = str(surface["surface_kind"])
        _unique_text_list(
            surface.get("fact_ids"),
            "E_RAW_SURFACE_FACT_IDS",
            allow_empty=kind == "synthetic_disclosure",
        )
        _unique_text_list(
            surface.get("source_ids"),
            "E_RAW_SURFACE_SOURCE_IDS",
            allow_empty=kind == "synthetic_disclosure",
        )
        _unique_text_list(
            surface.get("authorization_ids"),
            "E_RAW_SURFACE_AUTH_IDS",
            allow_empty=kind == "synthetic_disclosure",
        )

    claims = raw.get("semantic_claims")
    require(isinstance(claims, list) and bool(claims), "E_RAW_CLAIMS")
    surface_text = "\n".join(text for _, text in expected_surfaces)
    for raw_claim in claims:
        claim = _mapping(raw_claim, "E_RAW_CLAIM_OBJECT")
        require(set(claim) == RAW_CLAIM_FIELDS, "E_RAW_CLAIM_FIELDS")
        claim_text = _text(claim.get("claim_text"), "E_RAW_CLAIM_TEXT")
        require(claim_text in surface_text, "E_RAW_CLAIM_NOT_ON_SURFACE")
        _unique_text_list(claim.get("fact_ids"), "E_RAW_CLAIM_FACT_IDS")
        _unique_text_list(claim.get("source_ids"), "E_RAW_CLAIM_SOURCE_IDS")
        _unique_text_list(claim.get("authorization_ids"), "E_RAW_CLAIM_AUTH_IDS")
        _text(claim.get("claim_boundary"), "E_RAW_CLAIM_BOUNDARY")

    usage = raw.get("semantic_component_usage")
    require(isinstance(usage, list), "E_RAW_COMPONENT_USAGE")
    component_ids: set[str] = set()
    for raw_usage in usage:
        row = _mapping(raw_usage, "E_RAW_COMPONENT_OBJECT")
        require(set(row) == RAW_COMPONENT_FIELDS, "E_RAW_COMPONENT_FIELDS")
        component_id = _text(row.get("component_id"), "E_RAW_COMPONENT_ID")
        require(component_id not in component_ids, "E_RAW_COMPONENT_DUPLICATE")
        component_ids.add(component_id)
        _text(row.get("implementation_note"), "E_RAW_COMPONENT_NOTE")
        ordinals = row.get("surface_ordinals")
        require(isinstance(ordinals, list) and bool(ordinals), "E_RAW_SURFACE_ORDINALS")
        require(
            all(isinstance(item, int) and not isinstance(item, bool) for item in ordinals),
            "E_RAW_SURFACE_ORDINALS",
        )
        require(len(ordinals) == len(set(ordinals)), "E_RAW_SURFACE_ORDINALS")
        require(
            all(1 <= item <= len(expected_surfaces) for item in ordinals),
            "E_RAW_SURFACE_ORDINAL_RANGE",
        )


def serialize(raw: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    """Build the machine envelope without changing author-owned semantics."""

    validate_raw(raw, request)
    request_id = str(request["request_id"])
    surfaces = []
    for index, raw_surface in enumerate(raw["semantic_surfaces"], 1):
        surface = copy.deepcopy(dict(raw_surface))
        surface["surface_unit_id"] = f"{request_id}-SURFACE-{index:02d}"
        surfaces.append(
            {
                "surface_unit_id": surface["surface_unit_id"],
                "surface_kind": surface["surface_kind"],
                "text": surface["text"],
                "fact_ids": surface["fact_ids"],
                "source_ids": surface["source_ids"],
                "authorization_ids": surface["authorization_ids"],
            }
        )
    claims = []
    for index, raw_claim in enumerate(raw["semantic_claims"], 1):
        claim = copy.deepcopy(dict(raw_claim))
        claims.append(
            {
                "claim_id": f"{request_id}-CLAIM-{index:02d}",
                "claim_text": claim["claim_text"],
                "fact_ids": claim["fact_ids"],
                "source_ids": claim["source_ids"],
                "authorization_ids": claim["authorization_ids"],
                "claim_boundary": claim["claim_boundary"],
            }
        )
    usage = []
    for raw_usage in raw["semantic_component_usage"]:
        row = copy.deepcopy(dict(raw_usage))
        usage.append(
            {
                "component_id": row["component_id"],
                "implementation_surface_unit_ids": [
                    surfaces[index - 1]["surface_unit_id"]
                    for index in row["surface_ordinals"]
                ],
                "implementation_note": row["implementation_note"],
            }
        )
    output: dict[str, Any] = {
        "schema_version": OUTPUT_SCHEMA,
        "task_id": TASK_ID,
        "request_id": request_id,
        "request_digest": request["request_digest"],
        "profile_id": request["profile_id"],
        "assigned_variant": request["assigned_variant"],
        "run_order": request["run_order"],
        "run_id": raw["run_id"],
        "author_identity": request["author_identity"],
        "author_session_logical_id": request["author_session_logical_id"],
        "author_platform_agent_id": request["author_platform_agent_id"],
        "model_capability_id": request["model_capability_id"],
        "reasoning_effort": request["reasoning_effort"],
        "service_tier": request["service_tier"],
        "title": raw["title"],
        "body": copy.deepcopy(raw["body"]),
        "spoken_lines": copy.deepcopy(raw["spoken_lines"]),
        "cta": raw["cta"],
        "visual_execution": copy.deepcopy(raw["visual_execution"]),
        "audio_execution": copy.deepcopy(raw["audio_execution"]),
        "synthetic_disclosure": raw["synthetic_disclosure"],
        "surface_units": surfaces,
        "claims": claims,
        "component_usage": usage,
        "author_attestation": copy.deepcopy(raw["author_attestation"]),
        "synthetic_qualification_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "counts_toward_300": False,
        "output_digest": "",
    }
    output["output_digest"] = object_digest(output, "output_digest")
    return output


def frozen_strict_module() -> Any:
    """Load the immutable P4 validator and bind only this successor identity."""

    module_path = str(FROZEN_P4_ROOT)
    sys.path[:] = [entry for entry in sys.path if entry != module_path]
    sys.path.insert(0, module_path)
    for name in ("p4_actual", "p4_common"):
        sys.modules.pop(name, None)
    importlib.invalidate_caches()
    module = importlib.import_module("p4_actual")
    module.TASK_ID = TASK_ID
    module.POSITIVE_OUTPUT_SCHEMA = OUTPUT_SCHEMA
    return module


def strict_validate(
    outputs: Sequence[Mapping[str, Any]], requests: Sequence[Mapping[str, Any]]
) -> None:
    module = frozen_strict_module()
    module.validate_positive_outputs(outputs, requests)


def serialize_all(
    raws: Sequence[Mapping[str, Any]], requests: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    require(len(raws) == len(requests) == 20, "E_BATCH_COUNT")
    request_by_id = {str(row.get("request_id")): row for row in requests}
    require(len(request_by_id) == 20, "E_REQUEST_ID_UNIQUE")
    outputs = []
    seen: set[str] = set()
    seen_run_ids: set[str] = set()
    for raw in raws:
        request_id = str(raw.get("request_id"))
        require(request_id in request_by_id, "E_RAW_REQUEST_UNKNOWN")
        require(request_id not in seen, "E_RAW_REQUEST_DUPLICATE")
        run_id = str(raw.get("run_id"))
        require(run_id not in seen_run_ids, "E_RAW_RUN_ID_DUPLICATE", run_id)
        seen.add(request_id)
        seen_run_ids.add(run_id)
        outputs.append(serialize(raw, request_by_id[request_id]))
    strict_validate(outputs, requests)
    return outputs


def selftest(requests_path: Path, raws_path: Path) -> None:
    requests = read_jsonl(requests_path)
    raws = read_jsonl(raws_path)
    first = serialize_all(raws, requests)
    second = serialize_all(raws, requests)
    require(canonical_json(first) == canonical_json(second), "E_NONDETERMINISTIC")

    def expect_fail(mutator: Any, code: str) -> None:
        changed = copy.deepcopy(raws)
        mutator(changed)
        try:
            serialize_all(changed, requests)
        except (AuthorContractError, ValueError) as exc:
            require(code in str(exc), "E_SELFTEST_WRONG_FAILURE", str(exc))
            return
        raise AuthorContractError(f"E_SELFTEST_FALSE_NEGATIVE:{code}")

    expect_fail(lambda rows: rows[0].update({"surface_id": "alias"}), "E_RAW_FIELD_SET")
    expect_fail(
        lambda rows: rows[0]["semantic_surfaces"][0].update({"extra": True}),
        "E_RAW_SURFACE_FIELDS",
    )
    expect_fail(
        lambda rows: rows[0]["semantic_claims"][0].update(
            {"claim_text": "not present on any surface"}
        ),
        "E_RAW_CLAIM_NOT_ON_SURFACE",
    )
    expect_fail(
        lambda rows: rows[0]["semantic_component_usage"][0].update(
            {"surface_ordinals": [999]}
        ),
        "E_RAW_SURFACE_ORDINAL_RANGE",
    )
    expect_fail(
        lambda rows: rows[0]["semantic_surfaces"][0].update({"text": "changed"}),
        "E_RAW_SURFACE_EXACT_JOIN",
    )

    changed = copy.deepcopy(raws)
    changed[0]["semantic_surfaces"][1]["fact_ids"] = []
    try:
        serialize_all(changed, requests)
    except (AuthorContractError, ValueError):
        pass
    else:
        raise AuthorContractError("E_SELFTEST_FALSE_NEGATIVE:fact coverage")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--raws", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        requests = read_jsonl(args.requests)
        raws = read_jsonl(args.raws)
        outputs = serialize_all(raws, requests)
        if args.output:
            write_jsonl(args.output, outputs)
        if args.selftest:
            selftest(args.requests, args.raws)
    except (AuthorContractError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"FAIL {exc}\n")
        return 1
    print(f"PASS outputs={len(outputs)} deterministic=true strict=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
