#!/usr/bin/env python3
"""P3 output envelope, route execution, and machine evidence validators."""

from __future__ import annotations

import difflib
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from p3_common import (
    AUTHORIZED_AUTHOR_CAPABILITY_ID,
    AUTHORIZED_AUTHOR_IDENTITY,
    AUTHORIZED_AUTHOR_SESSION,
    P2_ROOT,
    ROOT,
    ROUTE_GOLD_PATH,
    TASK_ID,
    TASK_ROOT,
    canonical_json,
    jsonl_bytes,
    load_jsonl,
    object_digest,
    profile_rows,
    require,
    sha256_file,
    yaml_bytes,
)
from p3_prepare import AUTHOR_REQUEST_PATH, ROUTE_INPUT_FREEZE_PATH


P2_ABSOLUTE = ROOT / P2_ROOT
if str(P2_ABSOLUTE) not in sys.path:
    sys.path.insert(0, str(P2_ABSOLUTE))

import p2_generator_core_r6 as p2_core  # noqa: E402


POSITIVE_OUTPUT_PATH = TASK_ROOT / "open_probe/attempt_0/positive_20_first_outputs.v0.1.jsonl"
AUTHOR_RUN_RECEIPT_PATH = TASK_ROOT / "open_probe/attempt_0/author_run_receipt.v0.1.yaml"
ROUTE_ACTUAL_PATH = TASK_ROOT / "open_probe/attempt_0/route_20_actuals.v0.1.jsonl"
ROUTE_ACTUAL_FREEZE_PATH = TASK_ROOT / "open_probe/attempt_0/route_actual_freeze_receipt.v0.1.yaml"
ROUTE_COMPARISON_PATH = TASK_ROOT / "open_probe/attempt_0/route_20_comparisons.v0.1.jsonl"
EXIT_EVENT_PATH = TASK_ROOT / "open_probe/attempt_0/execution_exit_events.v0.1.jsonl"
MACHINE_REPORT_PATH = TASK_ROOT / "open_probe/attempt_0/machine_acceptance_report.v0.1.yaml"

SURFACE_KINDS = (
    "synthetic_disclosure",
    "title",
    "body",
    "spoken_line",
    "cta",
    "visual_execution",
    "audio_execution",
)


def _require_text(value: Any, code: str, allow_empty: bool = False) -> str:
    require(isinstance(value, str), code)
    if not allow_empty:
        require(bool(value.strip()), code)
    return value


def _require_text_list(value: Any, code: str, allow_empty: bool = False) -> list[str]:
    require(isinstance(value, list), code)
    rows = []
    for item in value:
        rows.append(_require_text(item, code))
    if not allow_empty:
        require(bool(rows), code)
    return rows


def _surface_sequence(output: Mapping[str, Any]) -> list[tuple[str, str]]:
    sequence: list[tuple[str, str]] = [
        ("synthetic_disclosure", str(output["synthetic_disclosure"])),
        ("title", str(output["title"])),
    ]
    sequence.extend(("body", text) for text in output["body"])
    sequence.extend(("spoken_line", text) for text in output["spoken_lines"])
    if output["cta"]:
        sequence.append(("cta", str(output["cta"])))
    sequence.extend(("visual_execution", text) for text in output["visual_execution"])
    sequence.extend(("audio_execution", text) for text in output["audio_execution"])
    return sequence


def validate_positive_output(
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
    require(set(output) == required_fields, "E_P3_AUTHOR_OUTPUT_FIELD_SET")
    require(output.get("schema_version") == "gate1-p3-positive-first-output-v0.1", "E_P3_OUTPUT_SCHEMA")
    require(output.get("task_id") == TASK_ID, "E_P3_OUTPUT_TASK")
    for field in ("request_id", "request_digest", "profile_id", "assigned_variant", "run_order"):
        require(output.get(field) == request.get(field), "E_P3_OUTPUT_REQUEST_BINDING", field)
    require(output.get("attempt") == 0, "E_P3_OUTPUT_ATTEMPT")
    require(output.get("run_id") == f"P3-AUTHOR-RUN-{int(request['run_order']):02d}", "E_P3_OUTPUT_RUN_ID")
    require(output.get("author_identity") == AUTHORIZED_AUTHOR_IDENTITY, "E_P3_OUTPUT_AUTHOR_IDENTITY")
    require(output.get("author_session_logical_id") == AUTHORIZED_AUTHOR_SESSION, "E_P3_OUTPUT_AUTHOR_SESSION")
    require(isinstance(output.get("author_platform_agent_id"), str) and bool(output["author_platform_agent_id"]), "E_P3_OUTPUT_PLATFORM_AGENT")
    require(output.get("model_capability_id") == AUTHORIZED_AUTHOR_CAPABILITY_ID, "E_P3_OUTPUT_MODEL")
    require(output.get("synthetic_qualification_only") is True, "E_P3_OUTPUT_NAMESPACE")
    for field in ("publishable", "runtime_consumable", "counts_toward_300"):
        require(output.get(field) is False, "E_P3_OUTPUT_BOUNDARY", field)
    title = _require_text(output.get("title"), "E_P3_OUTPUT_TITLE")
    body = _require_text_list(output.get("body"), "E_P3_OUTPUT_BODY")
    spoken = _require_text_list(output.get("spoken_lines"), "E_P3_OUTPUT_SPOKEN", allow_empty=True)
    cta = _require_text(output.get("cta"), "E_P3_OUTPUT_CTA", allow_empty=True)
    visual = _require_text_list(output.get("visual_execution"), "E_P3_OUTPUT_VISUAL")
    audio = _require_text_list(output.get("audio_execution"), "E_P3_OUTPUT_AUDIO", allow_empty=True)
    disclosure = _require_text(output.get("synthetic_disclosure"), "E_P3_OUTPUT_DISCLOSURE")
    require("合成" in disclosure and ("不对应真实" in disclosure or "非真实" in disclosure), "E_P3_OUTPUT_DISCLOSURE_MEANING")
    require(all("内部审查" not in text and "不进入发布" not in text for text in [title, *body, *spoken, cta, *visual, *audio]), "E_P3_OUTPUT_META_SCAFFOLD")
    expected_sequence = _surface_sequence(output)
    surface_units = output.get("surface_units")
    require(isinstance(surface_units, list), "E_P3_SURFACE_UNITS")
    require(len(surface_units) == len(expected_sequence), "E_P3_SURFACE_COVERAGE_COUNT")
    material = request["typed_material"]
    fact_by_id = {str(row["fact_id"]): row for row in material["facts"]}
    source_ids = {str(row["source_id"]) for row in material["sources"]}
    authorization_ids = {str(row["authorization_id"]) for row in material["authorizations"]}
    surface_ids: set[str] = set()
    for index, (unit, expected) in enumerate(zip(surface_units, expected_sequence, strict=True), 1):
        require(isinstance(unit, Mapping), "E_P3_SURFACE_UNIT_OBJECT")
        require(set(unit) == {"surface_unit_id", "surface_kind", "text", "fact_ids", "source_ids", "authorization_ids"}, "E_P3_SURFACE_UNIT_FIELDS")
        unit_id = str(unit["surface_unit_id"])
        require(unit_id == f"{output['request_id']}-SURFACE-{index:02d}", "E_P3_SURFACE_UNIT_ID")
        require(unit_id not in surface_ids, "E_P3_SURFACE_UNIT_DUPLICATE")
        surface_ids.add(unit_id)
        require(unit["surface_kind"] in SURFACE_KINDS, "E_P3_SURFACE_KIND")
        require((unit["surface_kind"], unit["text"]) == expected, "E_P3_SURFACE_EXACT_JOIN")
        fact_ids = list(map(str, unit.get("fact_ids", [])))
        bound_sources = list(map(str, unit.get("source_ids", [])))
        bound_authorizations = list(map(str, unit.get("authorization_ids", [])))
        if unit["surface_kind"] != "synthetic_disclosure":
            require(bool(fact_ids), "E_P3_SURFACE_FACT_EMPTY", unit_id)
            require(bool(bound_sources), "E_P3_SURFACE_SOURCE_EMPTY", unit_id)
            require(bool(bound_authorizations), "E_P3_SURFACE_AUTH_EMPTY", unit_id)
        require(set(fact_ids).issubset(fact_by_id), "E_P3_SURFACE_FACT_REF", unit_id)
        require(set(bound_sources).issubset(source_ids), "E_P3_SURFACE_SOURCE_REF", unit_id)
        require(set(bound_authorizations).issubset(authorization_ids), "E_P3_SURFACE_AUTH_REF", unit_id)
        for fact_id in fact_ids:
            fact = fact_by_id[fact_id]
            require(set(bound_sources).issubset(set(map(str, fact["source_ids"]))) or not bound_sources, "E_P3_SURFACE_FACT_SOURCE_SCOPE", unit_id)
            require(set(bound_authorizations).issubset(set(map(str, fact["authorization_ids"]))) or not bound_authorizations, "E_P3_SURFACE_FACT_AUTH_SCOPE", unit_id)
    claims = output.get("claims")
    require(isinstance(claims, list) and bool(claims), "E_P3_CLAIMS")
    combined_surface = "\n".join(text for _, text in expected_sequence)
    claim_ids: set[str] = set()
    for claim in claims:
        require(isinstance(claim, Mapping), "E_P3_CLAIM_OBJECT")
        require(set(claim) == {"claim_id", "claim_text", "fact_ids", "source_ids", "authorization_ids", "claim_boundary"}, "E_P3_CLAIM_FIELDS")
        claim_id = str(claim["claim_id"])
        require(claim_id not in claim_ids, "E_P3_CLAIM_DUPLICATE")
        claim_ids.add(claim_id)
        claim_text = _require_text(claim["claim_text"], "E_P3_CLAIM_TEXT")
        require(claim_text in combined_surface, "E_P3_CLAIM_NOT_ON_SURFACE", claim_id)
        require(set(map(str, claim["fact_ids"])).issubset(fact_by_id) and bool(claim["fact_ids"]), "E_P3_CLAIM_FACT_REF", claim_id)
        require(set(map(str, claim["source_ids"])).issubset(source_ids) and bool(claim["source_ids"]), "E_P3_CLAIM_SOURCE_REF", claim_id)
        require(set(map(str, claim["authorization_ids"])).issubset(authorization_ids) and bool(claim["authorization_ids"]), "E_P3_CLAIM_AUTH_REF", claim_id)
        require(claim["claim_boundary"] == material["claim_boundary"], "E_P3_CLAIM_BOUNDARY", claim_id)
    usage = output.get("component_usage")
    require(isinstance(usage, list), "E_P3_COMPONENT_USAGE")
    expected_component_ids = {
        str(row["component_id"])
        for row in request["structure_contract"]["component_contributions"]
    }
    actual_component_ids = {str(row.get("component_id")) for row in usage if isinstance(row, Mapping)}
    require(actual_component_ids == expected_component_ids, "E_P3_COMPONENT_USAGE_COVERAGE")
    for row in usage:
        require(isinstance(row, Mapping), "E_P3_COMPONENT_USAGE_OBJECT")
        require(set(row) == {"component_id", "implementation_surface_unit_ids", "implementation_note"}, "E_P3_COMPONENT_USAGE_FIELDS")
        pointers = list(map(str, row["implementation_surface_unit_ids"]))
        require(bool(pointers) and set(pointers).issubset(surface_ids), "E_P3_COMPONENT_USAGE_POINTER")
        _require_text(row["implementation_note"], "E_P3_COMPONENT_USAGE_NOTE")
    attestation = output.get("author_attestation")
    require(
        attestation
        == {
            "unbound_fact_added": False,
            "input_backfilled_after_authoring": False,
            "external_service_called": False,
            "second_candidate_generated": False,
            "review_performed_by_author": False,
        },
        "E_P3_AUTHOR_ATTESTATION",
    )
    require(output.get("output_digest") == object_digest(dict(output), "output_digest"), "E_P3_OUTPUT_DIGEST")


def validate_positive_file(root: Path = ROOT) -> list[dict[str, Any]]:
    requests = load_jsonl(root / AUTHOR_REQUEST_PATH)
    outputs = load_jsonl(root / POSITIVE_OUTPUT_PATH)
    require(len(requests) == len(outputs) == 20, "E_P3_POSITIVE_COUNT")
    request_by_id = {str(row["request_id"]): row for row in requests}
    require(len(request_by_id) == 20, "E_P3_REQUEST_ID_UNIQUE")
    seen: set[str] = set()
    for output in outputs:
        request_id = str(output.get("request_id"))
        require(request_id not in seen, "E_P3_OUTPUT_REQUEST_DUPLICATE", request_id)
        seen.add(request_id)
        request = request_by_id.get(request_id)
        require(request is not None, "E_P3_OUTPUT_UNKNOWN_REQUEST", request_id)
        validate_positive_output(output, request)
    require(seen == set(request_by_id), "E_P3_OUTPUT_REQUEST_COVERAGE")
    require([row["run_order"] for row in outputs] == list(range(1, 21)), "E_P3_OUTPUT_RUN_ORDER")
    require(len({row["author_platform_agent_id"] for row in outputs}) == 1, "E_P3_MULTIPLE_AUTHOR_AGENTS")
    return outputs


def build_route_actuals(root: Path = ROOT) -> list[dict[str, Any]]:
    inputs = load_jsonl(root / ROUTE_INPUT_FREEZE_PATH)
    profiles = {str(row["content_product_type_id"]): row for row in profile_rows(root)}
    require(len(inputs) == 20, "E_P3_ROUTE_INPUT_COUNT")
    actuals = [p2_core.evaluate_route(row, profiles[str(row["profile_id"])]) for row in inputs]
    require(len(actuals) == 20, "E_P3_ROUTE_ACTUAL_COUNT")
    return actuals


def materialize_route_actuals(root: Path = ROOT) -> list[Path]:
    actuals = build_route_actuals(root)
    path = root / ROUTE_ACTUAL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = jsonl_bytes(actuals)
    path.write_bytes(payload)
    receipt = {
        "schema_version": "gate1-p3-route-actual-freeze-v0.1",
        "task_id": TASK_ID,
        "actual_engine_inputs": ROUTE_INPUT_FREEZE_PATH.as_posix(),
        "actual_engine_input_sha256": sha256_file(root / ROUTE_INPUT_FREEZE_PATH),
        "actual_result_path": ROUTE_ACTUAL_PATH.as_posix(),
        "actual_result_sha256": sha256_file(path),
        "actual_result_count": 20,
        "gold_answer_loaded_by_actual_engine": False,
        "gold_answer_compared_after_actual_freeze_only": True,
    }
    receipt["receipt_digest"] = object_digest(receipt, "receipt_digest")
    receipt_path = root / ROUTE_ACTUAL_FREEZE_PATH
    receipt_path.write_bytes(yaml_bytes({"route_actual_freeze_receipt": receipt}))
    return [path, receipt_path]


def build_route_comparisons(root: Path = ROOT) -> list[dict[str, Any]]:
    actuals = load_jsonl(root / ROUTE_ACTUAL_PATH)
    require(len(actuals) == 20, "E_P3_ROUTE_ACTUAL_COUNT")
    gold_by_case = {str(row["case_id"]): row for row in load_jsonl(root / ROUTE_GOLD_PATH)}
    rows: list[dict[str, Any]] = []
    for actual in actuals:
        gold = gold_by_case.get(str(actual["case_id"]))
        require(gold is not None, "E_P3_ROUTE_GOLD_MISSING", str(actual["case_id"]))
        row = {
            "case_id": actual["case_id"],
            "profile_id": actual["profile_id"],
            "actual_route_result_digest": actual["route_result_digest"],
            "gold_answer_digest": gold["gold_answer_digest"],
            "actual_primary_action": actual["actual_primary_action"],
            "gold_primary_action": gold["gold_primary_action"],
            "primary_action_matches_gold": actual["actual_primary_action"] == gold["gold_primary_action"],
            "actual_primary_reason_category": actual["actual_primary_reason_category"],
            "gold_reason_code": gold["gold_reason_code"],
            "primary_reason_matches_gold": actual["actual_primary_reason_category"] == gold["gold_reason_code"],
            "audience_content_created": any(
                actual[field]
                for field in ("audience_title_created", "audience_body_created", "spoken_script_created")
            ),
        }
        row["comparison_digest"] = object_digest(row, "comparison_digest")
        rows.append(row)
    return rows


def materialize_route_comparisons(root: Path = ROOT) -> Path:
    rows = build_route_comparisons(root)
    path = root / ROUTE_COMPARISON_PATH
    path.write_bytes(jsonl_bytes(rows))
    return path


def _normalized_text(output: Mapping[str, Any]) -> str:
    values = [output["title"], *output["body"], *output["spoken_lines"], output["cta"]]
    return re.sub(r"[\W_\d]+", "", "".join(map(str, values)), flags=re.UNICODE)


def build_exit_audit(root: Path = ROOT) -> dict[str, Any]:
    events = load_jsonl(root / EXIT_EVENT_PATH)
    require(bool(events), "E_P3_EXIT_EVENTS_EMPTY")
    for event in events:
        require(event.get("task_id") == TASK_ID, "E_P3_EXIT_EVENT_TASK")
        require(event.get("network_dispatch") is False, "E_P3_NETWORK_DISPATCH")
        require(event.get("api_request") is False, "E_P3_API_REQUEST")
        require(event.get("credential_read") is False, "E_P3_CREDENTIAL_READ")
    return {
        "event_count": len(events),
        "controlled_execution_agent_run_count": sum(event.get("exit_class") == "CONTROLLED_EXECUTION_AGENT" for event in events),
        "external_provider_request_count": sum(event.get("exit_class") == "EXTERNAL_PROVIDER" for event in events),
        "external_api_call_count": sum(bool(event.get("api_request")) for event in events),
        "credential_read_count": sum(bool(event.get("credential_read")) for event in events),
        "network_dispatch_count": sum(bool(event.get("network_dispatch")) for event in events),
    }


def build_machine_report(root: Path = ROOT) -> dict[str, Any]:
    outputs = validate_positive_file(root)
    comparisons = load_jsonl(root / ROUTE_COMPARISON_PATH)
    expected_comparisons = build_route_comparisons(root)
    require(canonical_json(comparisons) == canonical_json(expected_comparisons), "E_P3_ROUTE_COMPARISON_DRIFT")
    texts = {str(row["profile_id"]): _normalized_text(row) for row in outputs}
    exact_duplicates: list[list[str]] = []
    near_duplicates: list[dict[str, Any]] = []
    profile_ids = sorted(texts)
    for left_index, left in enumerate(profile_ids):
        for right in profile_ids[left_index + 1 :]:
            if texts[left] == texts[right]:
                exact_duplicates.append([left, right])
            ratio = difflib.SequenceMatcher(None, texts[left], texts[right]).ratio()
            if ratio >= 0.82:
                near_duplicates.append({"left": left, "right": right, "similarity": round(ratio, 4)})
    route_action_counts = Counter(row["actual_primary_action"] for row in comparisons)
    exit_audit = build_exit_audit(root)
    report: dict[str, Any] = {
        "schema_version": "gate1-p3-machine-acceptance-v0.1",
        "task_id": TASK_ID,
        "positive_first_output_count": len(outputs),
        "positive_profile_coverage_count": len({row["profile_id"] for row in outputs}),
        "single_author_platform_agent_count": len({row["author_platform_agent_id"] for row in outputs}),
        "exact_duplicate_pair_count": len(exact_duplicates),
        "exact_duplicate_pairs": exact_duplicates,
        "machine_similarity_review_queue_count": len(near_duplicates),
        "machine_similarity_review_queue": near_duplicates,
        "machine_similarity_is_not_human_near_duplicate_verdict": True,
        "route_case_count": len(comparisons),
        "route_action_counts": dict(sorted(route_action_counts.items())),
        "route_action_mismatch_count": sum(not row["primary_action_matches_gold"] for row in comparisons),
        "route_reason_mismatch_count": sum(not row["primary_reason_matches_gold"] for row in comparisons),
        "route_audience_content_count": sum(row["audience_content_created"] for row in comparisons),
        "exit_audit": exit_audit,
        "machine_can_prove_full_free_text_fabrication_absence": False,
        "independent_full_surface_review_required": True,
    }
    report["machine_report_digest"] = object_digest(report, "machine_report_digest")
    return report


def materialize_machine_report(root: Path = ROOT) -> Path:
    report = build_machine_report(root)
    path = root / MACHINE_REPORT_PATH
    path.write_bytes(yaml_bytes({"machine_acceptance_report": report}))
    return path


__all__ = [
    "AUTHOR_RUN_RECEIPT_PATH",
    "EXIT_EVENT_PATH",
    "MACHINE_REPORT_PATH",
    "POSITIVE_OUTPUT_PATH",
    "ROUTE_ACTUAL_FREEZE_PATH",
    "ROUTE_ACTUAL_PATH",
    "ROUTE_COMPARISON_PATH",
    "build_exit_audit",
    "build_machine_report",
    "build_route_actuals",
    "build_route_comparisons",
    "materialize_machine_report",
    "materialize_route_actuals",
    "materialize_route_comparisons",
    "validate_positive_file",
    "validate_positive_output",
]
