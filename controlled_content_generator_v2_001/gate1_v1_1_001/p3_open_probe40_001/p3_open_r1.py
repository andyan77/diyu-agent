#!/usr/bin/env python3
"""Validate and evidence the single P3 repair-run outputs."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from p3_common import (
    AUTHORIZED_AUTHOR_CAPABILITY_ID,
    AUTHORIZED_AUTHOR_IDENTITY,
    AUTHORIZED_AUTHOR_MODEL_LABEL,
    AUTHORIZED_AUTHOR_SESSION,
    P2_ROOT,
    ROOT,
    ROUTE_GOLD_PATH,
    TASK_ID,
    TASK_ROOT,
    canonical_json,
    jsonl_bytes,
    load_jsonl,
    load_yaml,
    object_digest,
    profile_rows,
    require,
    sha256_file,
    yaml_bytes,
)
from p3_repair import (
    ATTEMPT_0_FAILURE_COMMIT,
    AUTHOR_PLATFORM_AGENT_ID,
    AUTHOR_REQUEST_R1_PATH,
    ROUTE_INPUT_R1_PATH,
)


P2_ABSOLUTE = ROOT / P2_ROOT
if str(P2_ABSOLUTE) not in sys.path:
    sys.path.insert(0, str(P2_ABSOLUTE))

import p2_generator_core_r6 as p2_core  # noqa: E402


REPAIR_FREEZE_COMMIT = "817d35105be95f027465951e524496728f9bcaa5"
ATTEMPT_0_OUTPUT_PATH = (
    TASK_ROOT / "open_probe/attempt_0/positive_20_first_outputs.v0.1.jsonl"
)
POSITIVE_OUTPUT_R1_PATH = (
    TASK_ROOT / "open_probe/attempt_1/positive_20_first_outputs.v0.2.jsonl"
)
AUTHOR_RECEIPT_R1_PATH = TASK_ROOT / "open_probe/attempt_1/author_run_receipt.v0.2.yaml"
ROUTE_ACTUAL_R1_PATH = TASK_ROOT / "open_probe/attempt_1/route_20_actuals.v0.2.jsonl"
ROUTE_FREEZE_R1_PATH = (
    TASK_ROOT / "open_probe/attempt_1/route_actual_freeze_receipt.v0.2.yaml"
)
ROUTE_COMPARISON_R1_PATH = (
    TASK_ROOT / "open_probe/attempt_1/route_20_comparisons.v0.2.jsonl"
)
EXIT_EVENT_R1_PATH = TASK_ROOT / "open_probe/attempt_1/execution_exit_events.v0.2.jsonl"
MACHINE_REPORT_R1_PATH = (
    TASK_ROOT / "open_probe/attempt_1/machine_acceptance_report.v0.2.yaml"
)

SURFACE_KINDS = (
    "synthetic_disclosure",
    "title",
    "body",
    "spoken_line",
    "cta",
    "visual_execution",
    "audio_execution",
)
ROLE_ALLOWED_SURFACES = {
    "scene": {"title", "body", "visual_execution"},
    "trigger": {"title", "body", "spoken_line", "visual_execution"},
    "observable_action": {"body", "spoken_line", "visual_execution"},
    "transition": {"body", "visual_execution"},
    "visual_beat": {"body", "visual_execution"},
    "capture_instruction": {"visual_execution", "audio_execution"},
    "professional_judgment": {"body", "spoken_line"},
    "audience_facing_reasoning_move": {"body", "spoken_line", "visual_execution"},
    "closing": {"body", "spoken_line", "cta", "visual_execution"},
}


def _text(value: Any, code: str, allow_empty: bool = False) -> str:
    require(isinstance(value, str), code)
    if not allow_empty:
        require(bool(value.strip()), code)
    return value


def _text_list(value: Any, code: str, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), code)
    rows = [_text(item, code) for item in value]
    if not allow_empty:
        require(bool(rows), code)
    return rows


def _surface_sequence(output: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows = [
        ("synthetic_disclosure", str(output["synthetic_disclosure"])),
        ("title", str(output["title"])),
    ]
    rows.extend(("body", text) for text in output["body"])
    rows.extend(("spoken_line", text) for text in output["spoken_lines"])
    if output["cta"]:
        rows.append(("cta", str(output["cta"])))
    rows.extend(("visual_execution", text) for text in output["visual_execution"])
    rows.extend(("audio_execution", text) for text in output["audio_execution"])
    return rows


def validate_positive_output_r1(
    output: Mapping[str, Any], request: Mapping[str, Any]
) -> None:
    required_fields = {
        "schema_version",
        "task_id",
        "request_id",
        "request_digest",
        "profile_id",
        "assigned_variant",
        "attempt",
        "run_order",
        "run_id",
        "author_identity",
        "author_session_logical_id",
        "author_platform_agent_id",
        "model_capability_id",
        "title",
        "body",
        "spoken_lines",
        "cta",
        "visual_execution",
        "audio_execution",
        "synthetic_disclosure",
        "surface_units",
        "claims",
        "component_usage",
        "author_attestation",
        "synthetic_qualification_only",
        "publishable",
        "runtime_consumable",
        "counts_toward_300",
        "output_digest",
    }
    require(set(output) == required_fields, "E_P3_R1_OUTPUT_FIELD_SET")
    require(
        output.get("schema_version") == "gate1-p3-positive-first-output-v0.2",
        "E_P3_R1_OUTPUT_SCHEMA",
    )
    require(output.get("task_id") == TASK_ID, "E_P3_R1_OUTPUT_TASK")
    for field in (
        "request_id",
        "request_digest",
        "profile_id",
        "assigned_variant",
        "run_order",
    ):
        require(
            output.get(field) == request.get(field),
            "E_P3_R1_OUTPUT_REQUEST_BINDING",
            field,
        )
    require(output.get("attempt") == request.get("attempt") == 1, "E_P3_R1_ATTEMPT")
    require(
        output.get("run_id") == f"P3-AUTHOR-R1-RUN-{int(request['run_order']):02d}",
        "E_P3_R1_RUN_ID",
    )
    require(
        output.get("author_identity") == AUTHORIZED_AUTHOR_IDENTITY,
        "E_P3_R1_AUTHOR_IDENTITY",
    )
    require(
        output.get("author_session_logical_id") == AUTHORIZED_AUTHOR_SESSION,
        "E_P3_R1_AUTHOR_SESSION",
    )
    require(
        output.get("author_platform_agent_id") == AUTHOR_PLATFORM_AGENT_ID,
        "E_P3_R1_AUTHOR_AGENT",
    )
    require(
        output.get("model_capability_id") == AUTHORIZED_AUTHOR_CAPABILITY_ID,
        "E_P3_R1_AUTHOR_MODEL",
    )
    require(output.get("synthetic_qualification_only") is True, "E_P3_R1_NAMESPACE")
    for field in ("publishable", "runtime_consumable", "counts_toward_300"):
        require(output.get(field) is False, "E_P3_R1_BOUNDARY", field)
    title = _text(output.get("title"), "E_P3_R1_TITLE")
    body = _text_list(output.get("body"), "E_P3_R1_BODY")
    spoken = _text_list(output.get("spoken_lines"), "E_P3_R1_SPOKEN", True)
    cta = _text(output.get("cta"), "E_P3_R1_CTA", True)
    visual = _text_list(output.get("visual_execution"), "E_P3_R1_VISUAL")
    audio = _text_list(output.get("audio_execution"), "E_P3_R1_AUDIO", True)
    disclosure = _text(output.get("synthetic_disclosure"), "E_P3_R1_DISCLOSURE")
    require(
        "合成" in disclosure and ("测试" in disclosure or "非真实" in disclosure),
        "E_P3_R1_DISCLOSURE_MEANING",
    )
    audience_text = [title, *body, *spoken, cta, *visual, *audio]
    forbidden_scaffold = ("内部审查", "不进入发布", "材料未提供则", "本条只用于资格")
    require(
        all(
            all(fragment not in text for fragment in forbidden_scaffold)
            for text in audience_text
        ),
        "E_P3_R1_META_SCAFFOLD",
    )
    expected_sequence = _surface_sequence(output)
    units = output.get("surface_units")
    require(
        isinstance(units, list) and len(units) == len(expected_sequence),
        "E_P3_R1_SURFACE_COUNT",
    )
    material = request["typed_material"]
    fact_by_id = {str(row["fact_id"]): row for row in material["facts"]}
    source_ids = {str(row["source_id"]) for row in material["sources"]}
    authorization_ids = {
        str(row["authorization_id"]) for row in material["authorizations"]
    }
    surface_by_id: dict[str, Mapping[str, Any]] = {}
    referenced_fact_ids: set[str] = set()
    for index, (unit, expected) in enumerate(
        zip(units, expected_sequence, strict=True), 1
    ):
        require(isinstance(unit, Mapping), "E_P3_R1_SURFACE_OBJECT")
        require(
            set(unit)
            == {
                "surface_unit_id",
                "surface_kind",
                "text",
                "fact_ids",
                "source_ids",
                "authorization_ids",
            },
            "E_P3_R1_SURFACE_FIELDS",
        )
        unit_id = str(unit["surface_unit_id"])
        require(
            unit_id == f"{output['request_id']}-SURFACE-{index:02d}",
            "E_P3_R1_SURFACE_ID",
        )
        require(unit_id not in surface_by_id, "E_P3_R1_SURFACE_DUPLICATE")
        require(unit["surface_kind"] in SURFACE_KINDS, "E_P3_R1_SURFACE_KIND")
        require(
            (unit["surface_kind"], unit["text"]) == expected,
            "E_P3_R1_SURFACE_EXACT_JOIN",
        )
        facts = set(map(str, unit.get("fact_ids", [])))
        sources = set(map(str, unit.get("source_ids", [])))
        authorizations = set(map(str, unit.get("authorization_ids", [])))
        if unit["surface_kind"] != "synthetic_disclosure":
            require(bool(facts), "E_P3_R1_SURFACE_FACT_EMPTY", unit_id)
            require(bool(sources), "E_P3_R1_SURFACE_SOURCE_EMPTY", unit_id)
            require(bool(authorizations), "E_P3_R1_SURFACE_AUTH_EMPTY", unit_id)
        require(facts.issubset(fact_by_id), "E_P3_R1_SURFACE_FACT_REF", unit_id)
        require(sources.issubset(source_ids), "E_P3_R1_SURFACE_SOURCE_REF", unit_id)
        require(
            authorizations.issubset(authorization_ids),
            "E_P3_R1_SURFACE_AUTH_REF",
            unit_id,
        )
        for fact_id in facts:
            fact = fact_by_id[fact_id]
            require(
                sources.issubset(set(map(str, fact["source_ids"]))),
                "E_P3_R1_FACT_SOURCE_SCOPE",
                unit_id,
            )
            require(
                authorizations.issubset(
                    set(map(str, fact["authorization_ids"]))
                ),
                "E_P3_R1_FACT_AUTH_SCOPE",
                unit_id,
            )
        referenced_fact_ids.update(facts)
        surface_by_id[unit_id] = unit
    for requirement in request["product_core_surface_requirements"]:
        require(
            set(map(str, requirement["fact_ids"])).issubset(referenced_fact_ids),
            "E_P3_R1_PRODUCT_CORE_FACT_COVERAGE",
            str(requirement["requirement_id"]),
        )
    combined_surface = "\n".join(text for _, text in expected_sequence)
    claims = output.get("claims")
    require(isinstance(claims, list) and bool(claims), "E_P3_R1_CLAIMS")
    claim_ids: set[str] = set()
    for claim in claims:
        require(isinstance(claim, Mapping), "E_P3_R1_CLAIM_OBJECT")
        require(
            set(claim)
            == {
                "claim_id",
                "claim_text",
                "fact_ids",
                "source_ids",
                "authorization_ids",
                "claim_boundary",
            },
            "E_P3_R1_CLAIM_FIELDS",
        )
        claim_id = str(claim["claim_id"])
        require(claim_id not in claim_ids, "E_P3_R1_CLAIM_DUPLICATE")
        claim_ids.add(claim_id)
        claim_text = _text(claim["claim_text"], "E_P3_R1_CLAIM_TEXT")
        require(claim_text in combined_surface, "E_P3_R1_CLAIM_NOT_ON_SURFACE")
        require(
            bool(claim["fact_ids"])
            and set(map(str, claim["fact_ids"])).issubset(fact_by_id),
            "E_P3_R1_CLAIM_FACT_REF",
        )
        require(
            bool(claim["source_ids"])
            and set(map(str, claim["source_ids"])).issubset(source_ids),
            "E_P3_R1_CLAIM_SOURCE_REF",
        )
        require(
            bool(claim["authorization_ids"])
            and set(map(str, claim["authorization_ids"])).issubset(
                authorization_ids
            ),
            "E_P3_R1_CLAIM_AUTH_REF",
        )
        require(
            claim["claim_boundary"] == material["claim_boundary"],
            "E_P3_R1_CLAIM_BOUNDARY",
        )
    usage = output.get("component_usage")
    require(isinstance(usage, list), "E_P3_R1_COMPONENT_USAGE")
    expected_component_ids = {
        str(row["component_id"])
        for row in request["structure_contract"]["component_contributions"]
    }
    require(
        {str(row.get("component_id")) for row in usage} == expected_component_ids,
        "E_P3_R1_COMPONENT_USAGE_COVERAGE",
    )
    usage_by_id: dict[str, Mapping[str, Any]] = {}
    for row in usage:
        require(isinstance(row, Mapping), "E_P3_R1_COMPONENT_USAGE_OBJECT")
        require(
            set(row)
            == {
                "component_id",
                "implementation_surface_unit_ids",
                "implementation_note",
            },
            "E_P3_R1_COMPONENT_USAGE_FIELDS",
        )
        pointers = list(map(str, row["implementation_surface_unit_ids"]))
        require(
            bool(pointers) and set(pointers).issubset(surface_by_id),
            "E_P3_R1_COMPONENT_USAGE_POINTER",
        )
        _text(row["implementation_note"], "E_P3_R1_COMPONENT_USAGE_NOTE")
        usage_by_id[str(row["component_id"])] = row
    for requirement in request["component_realization_requirements"]:
        component_id = str(requirement["component_id"])
        row = usage_by_id[component_id]
        units_for_component = [
            surface_by_id[pointer]
            for pointer in row["implementation_surface_unit_ids"]
        ]
        evidence_refs = {
            str(fact_id)
            for unit in units_for_component
            for fact_id in unit["fact_ids"]
        }
        product_core_fact_ids = {
            str(fact_id)
            for core_requirement in request["product_core_surface_requirements"]
            for fact_id in core_requirement["fact_ids"]
        }
        allowed_evidence_fact_ids = set(
            map(str, requirement["evidence_fact_ids"])
        ).union(product_core_fact_ids)
        require(
            bool(evidence_refs.intersection(allowed_evidence_fact_ids)),
            "E_P3_R1_COMPONENT_EVIDENCE_FACT",
            component_id,
        )
        allowed = ROLE_ALLOWED_SURFACES[str(requirement["component_role"])]
        require(
            any(str(unit["surface_kind"]) in allowed for unit in units_for_component),
            "E_P3_R1_COMPONENT_SURFACE_ROLE",
            component_id,
        )
    require(
        output.get("author_attestation")
        == {
            "unbound_fact_added": False,
            "input_backfilled_after_authoring": False,
            "external_service_called": False,
            "second_candidate_generated": False,
            "review_performed_by_author": False,
        },
        "E_P3_R1_AUTHOR_ATTESTATION",
    )
    require(
        output.get("output_digest")
        == object_digest(dict(output), "output_digest"),
        "E_P3_R1_OUTPUT_DIGEST",
    )


def validate_positive_file_r1(root: Path = ROOT) -> list[dict[str, Any]]:
    requests = load_jsonl(root / AUTHOR_REQUEST_R1_PATH)
    outputs = load_jsonl(root / POSITIVE_OUTPUT_R1_PATH)
    require(len(requests) == len(outputs) == 20, "E_P3_R1_POSITIVE_COUNT")
    request_by_id = {str(row["request_id"]): row for row in requests}
    require(len(request_by_id) == 20, "E_P3_R1_REQUEST_UNIQUE")
    seen: set[str] = set()
    for output in outputs:
        request_id = str(output.get("request_id"))
        require(request_id not in seen, "E_P3_R1_OUTPUT_DUPLICATE")
        seen.add(request_id)
        require(request_id in request_by_id, "E_P3_R1_OUTPUT_UNKNOWN_REQUEST")
        validate_positive_output_r1(output, request_by_id[request_id])
    require(seen == set(request_by_id), "E_P3_R1_OUTPUT_COVERAGE")
    require(
        [row["run_order"] for row in outputs] == list(range(1, 21)),
        "E_P3_R1_RUN_ORDER",
    )
    require(
        {row["author_platform_agent_id"] for row in outputs}
        == {AUTHOR_PLATFORM_AGENT_ID},
        "E_P3_R1_MULTIPLE_AUTHORS",
    )
    return outputs


def build_route_actuals_r1(root: Path = ROOT) -> list[dict[str, Any]]:
    inputs = load_jsonl(root / ROUTE_INPUT_R1_PATH)
    profiles = {str(row["content_product_type_id"]): row for row in profile_rows(root)}
    require(len(inputs) == 20, "E_P3_R1_ROUTE_INPUT_COUNT")
    return [
        p2_core.evaluate_route(row, profiles[str(row["profile_id"])])
        for row in inputs
    ]


def materialize_route_actuals_r1(root: Path = ROOT) -> list[Path]:
    actuals = build_route_actuals_r1(root)
    path = root / ROUTE_ACTUAL_R1_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(jsonl_bytes(actuals))
    receipt = {
        "schema_version": "gate1-p3-route-actual-freeze-v0.2",
        "task_id": TASK_ID,
        "attempt": 1,
        "actual_engine_inputs": ROUTE_INPUT_R1_PATH.as_posix(),
        "actual_engine_input_sha256": sha256_file(root / ROUTE_INPUT_R1_PATH),
        "actual_result_path": ROUTE_ACTUAL_R1_PATH.as_posix(),
        "actual_result_sha256": sha256_file(path),
        "actual_result_count": 20,
        "gold_answer_loaded_by_actual_engine": False,
        "gold_answer_compared_after_actual_freeze_only": True,
    }
    receipt["receipt_digest"] = object_digest(receipt, "receipt_digest")
    receipt_path = root / ROUTE_FREEZE_R1_PATH
    receipt_path.write_bytes(yaml_bytes({"route_actual_freeze_receipt": receipt}))
    return [path, receipt_path]


def build_route_comparisons_r1(root: Path = ROOT) -> list[dict[str, Any]]:
    actuals = load_jsonl(root / ROUTE_ACTUAL_R1_PATH)
    require(len(actuals) == 20, "E_P3_R1_ROUTE_ACTUAL_COUNT")
    gold_by_case = {
        str(row["case_id"]): row for row in load_jsonl(root / ROUTE_GOLD_PATH)
    }
    rows: list[dict[str, Any]] = []
    for actual in actuals:
        gold = gold_by_case.get(str(actual["case_id"]))
        require(gold is not None, "E_P3_R1_ROUTE_GOLD_MISSING")
        row = {
            "case_id": actual["case_id"],
            "profile_id": actual["profile_id"],
            "attempt": 1,
            "actual_route_result_digest": actual["route_result_digest"],
            "gold_answer_digest": gold["gold_answer_digest"],
            "actual_primary_action": actual["actual_primary_action"],
            "gold_primary_action": gold["gold_primary_action"],
            "primary_action_matches_gold": actual["actual_primary_action"]
            == gold["gold_primary_action"],
            "actual_primary_reason_category": actual[
                "actual_primary_reason_category"
            ],
            "gold_reason_code": gold["gold_reason_code"],
            "primary_reason_matches_gold": actual[
                "actual_primary_reason_category"
            ]
            == gold["gold_reason_code"],
            "audience_content_created": any(
                actual[field]
                for field in (
                    "audience_title_created",
                    "audience_body_created",
                    "spoken_script_created",
                )
            ),
        }
        row["comparison_digest"] = object_digest(row, "comparison_digest")
        rows.append(row)
    return rows


def materialize_route_comparisons_r1(root: Path = ROOT) -> Path:
    path = root / ROUTE_COMPARISON_R1_PATH
    path.write_bytes(jsonl_bytes(build_route_comparisons_r1(root)))
    return path


def _normalized_text(output: Mapping[str, Any]) -> str:
    values = [output["title"], *output["body"], *output["spoken_lines"], output["cta"]]
    return re.sub(r"[\W_\d]+", "", "".join(map(str, values)), flags=re.UNICODE)


def _build_author_receipt(root: Path) -> dict[str, Any]:
    validate_positive_file_r1(root)
    receipt: dict[str, Any] = {
        "schema_version": "gate1-p3-author-run-receipt-v0.2",
        "task_id": TASK_ID,
        "attempt": 1,
        "author_identity": AUTHORIZED_AUTHOR_IDENTITY,
        "logical_session_id": AUTHORIZED_AUTHOR_SESSION,
        "platform_agent_id": AUTHOR_PLATFORM_AGENT_ID,
        "model_display_name": AUTHORIZED_AUTHOR_MODEL_LABEL,
        "model_capability_id": AUTHORIZED_AUTHOR_CAPABILITY_ID,
        "reasoning_effort": "high",
        "service_tier": "priority",
        "attempt_1_run_count": 1,
        "total_authorized_complete_run_count": 2,
        "request_count": 20,
        "first_output_count": 20,
        "second_candidate_count": 0,
        "reroll_count": 0,
        "author_review_count": 0,
        "external_provider_request_count": 0,
        "external_api_call_count": 0,
        "credential_read_count": 0,
        "attempt_0_output_artifacts_provided_to_run": False,
        "same_agent_context_may_have_been_retained": True,
        "prior_review_scores_provided_to_run": False,
        "output_path": POSITIVE_OUTPUT_R1_PATH.as_posix(),
        "output_sha256": sha256_file(root / POSITIVE_OUTPUT_R1_PATH),
        "attempt_0_output_sha256": sha256_file(root / ATTEMPT_0_OUTPUT_PATH),
        "attempt_0_failure_commit": ATTEMPT_0_FAILURE_COMMIT,
        "repair_freeze_commit": REPAIR_FREEZE_COMMIT,
        "author_identity_changed": False,
        "model_identity_changed": False,
    }
    receipt["receipt_digest"] = object_digest(receipt, "receipt_digest")
    return receipt


def _build_exit_events(root: Path) -> list[dict[str, Any]]:
    rows = [
        {
            "event_id": "P3-R1-EXIT-AUTHOR-001",
            "task_id": TASK_ID,
            "attempt": 1,
            "exit_class": "CONTROLLED_EXECUTION_AGENT",
            "platform_agent_id": AUTHOR_PLATFORM_AGENT_ID,
            "model_capability_id": AUTHORIZED_AUTHOR_CAPABILITY_ID,
            "request_count": 20,
            "response_count": 20,
            "external_provider": False,
            "network_dispatch": False,
            "api_request": False,
            "credential_read": False,
            "evidence_sha256": sha256_file(root / POSITIVE_OUTPUT_R1_PATH),
        },
        {
            "event_id": "P3-R1-EXIT-ROUTE-001",
            "task_id": TASK_ID,
            "attempt": 1,
            "exit_class": "LOCAL_DETERMINISTIC_ROUTE_ENGINE",
            "platform_agent_id": "P3-EXECUTOR-CODEX-001",
            "model_capability_id": None,
            "request_count": 20,
            "response_count": 20,
            "external_provider": False,
            "network_dispatch": False,
            "api_request": False,
            "credential_read": False,
            "evidence_sha256": sha256_file(root / ROUTE_ACTUAL_R1_PATH),
        },
    ]
    for row in rows:
        row["event_digest"] = object_digest(row, "event_digest")
    return rows


def build_exit_audit_r1(root: Path = ROOT) -> dict[str, Any]:
    events = load_jsonl(root / EXIT_EVENT_R1_PATH)
    require(len(events) == 2, "E_P3_R1_EXIT_EVENT_COUNT")
    for event in events:
        require(event.get("task_id") == TASK_ID, "E_P3_R1_EXIT_TASK")
        require(event.get("attempt") == 1, "E_P3_R1_EXIT_ATTEMPT")
        require(event.get("external_provider") is False, "E_P3_R1_EXTERNAL_PROVIDER")
        require(event.get("network_dispatch") is False, "E_P3_R1_NETWORK")
        require(event.get("api_request") is False, "E_P3_R1_API")
        require(event.get("credential_read") is False, "E_P3_R1_CREDENTIAL")
        require(
            event.get("event_digest") == object_digest(event, "event_digest"),
            "E_P3_R1_EXIT_DIGEST",
        )
    return {
        "event_count": len(events),
        "controlled_execution_agent_run_count": sum(
            event["exit_class"] == "CONTROLLED_EXECUTION_AGENT" for event in events
        ),
        "external_provider_request_count": sum(
            event["exit_class"] == "EXTERNAL_PROVIDER" for event in events
        ),
        "external_api_call_count": sum(bool(event["api_request"]) for event in events),
        "credential_read_count": sum(bool(event["credential_read"]) for event in events),
        "network_dispatch_count": sum(bool(event["network_dispatch"]) for event in events),
    }


def build_machine_report_r1(root: Path = ROOT) -> dict[str, Any]:
    outputs = validate_positive_file_r1(root)
    comparisons = load_jsonl(root / ROUTE_COMPARISON_R1_PATH)
    require(
        canonical_json(comparisons) == canonical_json(build_route_comparisons_r1(root)),
        "E_P3_R1_ROUTE_COMPARISON_DRIFT",
    )
    texts = {str(row["profile_id"]): _normalized_text(row) for row in outputs}
    exact: list[list[str]] = []
    similar: list[dict[str, Any]] = []
    profile_ids = sorted(texts)
    for left_index, left in enumerate(profile_ids):
        for right in profile_ids[left_index + 1 :]:
            if texts[left] == texts[right]:
                exact.append([left, right])
            ratio = difflib.SequenceMatcher(None, texts[left], texts[right]).ratio()
            if ratio >= 0.82:
                similar.append(
                    {"left": left, "right": right, "similarity": round(ratio, 4)}
                )
    route_counts = Counter(row["actual_primary_action"] for row in comparisons)
    report: dict[str, Any] = {
        "schema_version": "gate1-p3-machine-acceptance-v0.2",
        "task_id": TASK_ID,
        "attempt": 1,
        "positive_first_output_count": len(outputs),
        "positive_profile_coverage_count": len({row["profile_id"] for row in outputs}),
        "single_author_platform_agent_count": len(
            {row["author_platform_agent_id"] for row in outputs}
        ),
        "product_core_fact_reference_coverage": 1.0,
        "component_realization_reference_coverage": 1.0,
        "exact_duplicate_pair_count": len(exact),
        "exact_duplicate_pairs": exact,
        "machine_similarity_review_queue_count": len(similar),
        "machine_similarity_review_queue": similar,
        "machine_similarity_is_not_human_near_duplicate_verdict": True,
        "route_case_count": len(comparisons),
        "route_action_counts": dict(sorted(route_counts.items())),
        "route_action_mismatch_count": sum(
            not row["primary_action_matches_gold"] for row in comparisons
        ),
        "route_reason_mismatch_count": sum(
            not row["primary_reason_matches_gold"] for row in comparisons
        ),
        "route_audience_content_count": sum(
            row["audience_content_created"] for row in comparisons
        ),
        "exit_audit": build_exit_audit_r1(root),
        "machine_can_prove_full_free_text_fabrication_absence": False,
        "machine_can_prove_semantic_component_realization": False,
        "independent_full_surface_review_required": True,
    }
    report["machine_report_digest"] = object_digest(report, "machine_report_digest")
    return report


def materialize_machine_evidence_r1(root: Path = ROOT) -> list[Path]:
    receipt = _build_author_receipt(root)
    receipt_path = root / AUTHOR_RECEIPT_R1_PATH
    receipt_path.write_bytes(yaml_bytes({"author_run_receipt": receipt}))
    events = _build_exit_events(root)
    event_path = root / EXIT_EVENT_R1_PATH
    event_path.write_bytes(jsonl_bytes(events))
    report = build_machine_report_r1(root)
    report_path = root / MACHINE_REPORT_R1_PATH
    report_path.write_bytes(yaml_bytes({"machine_acceptance_report": report}))
    return [receipt_path, event_path, report_path]


def check_all_r1(root: Path = ROOT) -> None:
    validate_positive_file_r1(root)
    require(
        load_jsonl(root / ROUTE_ACTUAL_R1_PATH) == build_route_actuals_r1(root),
        "E_P3_R1_ROUTE_ACTUAL_DRIFT",
    )
    require(
        load_jsonl(root / ROUTE_COMPARISON_R1_PATH)
        == build_route_comparisons_r1(root),
        "E_P3_R1_ROUTE_COMPARISON_DRIFT",
    )
    require(
        load_yaml(root / AUTHOR_RECEIPT_R1_PATH)["author_run_receipt"]
        == _build_author_receipt(root),
        "E_P3_R1_AUTHOR_RECEIPT_DRIFT",
    )
    require(
        load_jsonl(root / EXIT_EVENT_R1_PATH) == _build_exit_events(root),
        "E_P3_R1_EXIT_EVENT_DRIFT",
    )
    require(
        load_yaml(root / MACHINE_REPORT_R1_PATH)["machine_acceptance_report"]
        == build_machine_report_r1(root),
        "E_P3_R1_MACHINE_REPORT_DRIFT",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate-positive", action="store_true")
    group.add_argument("--route-actuals", action="store_true")
    group.add_argument("--route-compare", action="store_true")
    group.add_argument("--machine", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.validate_positive:
        outputs = validate_positive_file_r1()
        print(json.dumps({"status": "P3_R1_POSITIVE_VALID", "count": len(outputs)}))
    elif args.route_actuals:
        changed = materialize_route_actuals_r1()
        print(json.dumps({"status": "P3_R1_ROUTE_ACTUALS_FROZEN", "paths": [str(path) for path in changed]}))
    elif args.route_compare:
        path = materialize_route_comparisons_r1()
        print(json.dumps({"status": "P3_R1_ROUTE_COMPARED", "path": str(path)}))
    elif args.machine:
        paths = materialize_machine_evidence_r1()
        print(json.dumps({"status": "P3_R1_MACHINE_EVIDENCE", "paths": [str(path) for path in paths]}))
    else:
        check_all_r1()
        print(json.dumps({"status": "P3_R1_CHECK_PASS"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
