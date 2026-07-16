"""First-attempt-only author output contract for v4 recovery."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from . import contract, request_builder

SURFACE_KINDS = (
    "synthetic_disclosure", "title", "body", "spoken_line", "cta",
    "visual_execution", "audio_execution",
)
EXPECTED_ATTESTATION = {
    "feedback_received_before_submission": False,
    "prior_attempt_seen": False,
    "second_candidate_generated": False,
    "unbound_fact_added": False,
    "review_performed_by_author": False,
    "external_service_called": False,
}
RAW_FIELDS = {
    "schema_version", "request_id", "run_id", "attempt_id", "attempt_index",
    "title", "body", "spoken_lines", "cta", "visual_execution", "audio_execution",
    "synthetic_disclosure", "surface_units", "author_attestation",
}
SURFACE_FIELDS = {"surface_kind", "text", "fact_ids"}


def surface_sequence(raw: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows = [("synthetic_disclosure", str(raw["synthetic_disclosure"])),
            ("title", str(raw["title"]))]
    rows.extend(("body", str(text)) for text in raw["body"])
    rows.extend(("spoken_line", str(text)) for text in raw["spoken_lines"])
    if raw["cta"]:
        rows.append(("cta", str(raw["cta"])))
    rows.extend(("visual_execution", str(text)) for text in raw["visual_execution"])
    rows.extend(("audio_execution", str(text)) for text in raw["audio_execution"])
    return rows


def audience_text(output: Mapping[str, Any]) -> str:
    parts = [str(output["title"]), *map(str, output["body"]),
             *map(str, output["spoken_lines"])]
    if output["cta"]:
        parts.append(str(output["cta"]))
    parts.extend(map(str, output["visual_execution"]))
    parts.extend(map(str, output["audio_execution"]))
    return "\n".join(parts)


def validate_raw(raw: Mapping[str, Any], request: Mapping[str, Any]) -> None:
    request_builder.validate_request(request)
    contract.exact_fields(raw, RAW_FIELDS, "E_V4_RAW_FIELDS")
    contract.require(raw["schema_version"] == contract.RAW_OUTPUT_SCHEMA,
                     "E_V4_RAW_SCHEMA")
    contract.require(raw["request_id"] == request["request_id"], "E_V4_RAW_REQUEST")
    contract.require(raw["run_id"] == request["run_id"], "E_V4_RAW_RUN")
    contract.require(raw["attempt_index"] == 1, "E_V4_FIRST_ATTEMPT_ONLY")
    contract.require(raw["attempt_id"] == f"{request['request_id']}:attempt:1",
                     "E_V4_ATTEMPT_ID")
    contract.as_text(raw["title"], "E_V4_RAW_TITLE")
    contract.text_list(raw["body"], "E_V4_RAW_BODY")
    contract.text_list(raw["spoken_lines"], "E_V4_RAW_SPOKEN", allow_empty=True)
    contract.as_text(raw["cta"], "E_V4_RAW_CTA", allow_empty=True)
    contract.text_list(raw["visual_execution"], "E_V4_RAW_VISUAL")
    contract.text_list(raw["audio_execution"], "E_V4_RAW_AUDIO", allow_empty=True)
    disclosure = contract.as_text(raw["synthetic_disclosure"], "E_V4_RAW_DISCLOSURE")
    contract.require("合成" in disclosure and ("测试" in disclosure or "非真实" in disclosure),
                     "E_V4_RAW_DISCLOSURE")
    contract.require(raw["author_attestation"] == EXPECTED_ATTESTATION,
                     "E_V4_RAW_ATTESTATION")
    expected_surfaces = surface_sequence(raw)
    surfaces = raw["surface_units"]
    contract.require(isinstance(surfaces, list), "E_V4_RAW_SURFACES")
    contract.require(len(surfaces) == len(expected_surfaces), "E_V4_RAW_SURFACE_COUNT")
    known_fact_ids = {fact["fact_id"] for fact in request["typed_material"]["facts"]}
    for index, (raw_surface, expected) in enumerate(
            zip(surfaces, expected_surfaces, strict=True), 1):
        surface = contract.as_mapping(raw_surface, "E_V4_RAW_SURFACE")
        contract.exact_fields(surface, SURFACE_FIELDS, "E_V4_RAW_SURFACE_FIELDS")
        contract.require((surface["surface_kind"], surface["text"]) == expected,
                         "E_V4_RAW_SURFACE_EXACT_JOIN", str(index))
        contract.require(surface["surface_kind"] in SURFACE_KINDS,
                         "E_V4_RAW_SURFACE_KIND")
        fact_ids = contract.unique_text_list(
            surface["fact_ids"], "E_V4_RAW_SURFACE_FACTS", allow_empty=True)
        contract.require(set(fact_ids).issubset(known_fact_ids),
                         "E_V4_RAW_SURFACE_FACT_UNKNOWN", str(index))
        if surface["surface_kind"] == "synthetic_disclosure":
            contract.require(fact_ids == [], "E_V4_DISCLOSURE_FACT_BINDING")


def serialize(raw: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    validate_raw(raw, request)
    surfaces = []
    for index, surface in enumerate(raw["surface_units"], 1):
        surfaces.append({
            "surface_unit_id": f"{request['request_id']}:surface:{index:02d}",
            "surface_kind": surface["surface_kind"],
            "text": surface["text"],
            "fact_ids": list(surface["fact_ids"]),
        })
    output: dict[str, Any] = {
        "schema_version": contract.OUTPUT_SCHEMA,
        "task_id": contract.TASK_ID,
        "generator_version": contract.GENERATOR_VERSION,
        "rule_version": contract.RULE_VERSION,
        "request_id": request["request_id"],
        "request_digest": request["request_digest"],
        "batch_id": request["batch_id"],
        "run_id": request["run_id"],
        "attempt_id": raw["attempt_id"],
        "attempt_index": 1,
        "profile_id": request["profile_id"],
        "scenario_id": request["scenario_id"],
        "scenario_digest": request["scenario_digest"],
        "assignment_digest": request["assignment_digest"],
        "material_digest": request["material_digest"],
        "policy_digest": request["policy_digest"],
        "title": raw["title"],
        "body": copy.deepcopy(raw["body"]),
        "spoken_lines": copy.deepcopy(raw["spoken_lines"]),
        "cta": raw["cta"],
        "visual_execution": copy.deepcopy(raw["visual_execution"]),
        "audio_execution": copy.deepcopy(raw["audio_execution"]),
        "synthetic_disclosure": raw["synthetic_disclosure"],
        "surface_units": surfaces,
        "author_attestation": copy.deepcopy(raw["author_attestation"]),
        "qualification_only": True,
        "publishable": False,
        "runtime_consumable": False,
        "counts_toward_300": False,
        "output_digest": "",
    }
    contract.close_digest(output, "output_digest")
    validate_output(output, request)
    return output


def validate_output(output: Mapping[str, Any], request: Mapping[str, Any]) -> None:
    request_builder.validate_request(request)
    expected_fields = {
        "schema_version", "task_id", "generator_version", "rule_version",
        "request_id", "request_digest", "batch_id", "run_id", "attempt_id",
        "attempt_index", "profile_id", "scenario_id", "scenario_digest",
        "assignment_digest", "material_digest", "policy_digest", "title", "body",
        "spoken_lines", "cta", "visual_execution", "audio_execution",
        "synthetic_disclosure", "surface_units", "author_attestation",
        "qualification_only", "publishable", "runtime_consumable", "counts_toward_300",
        "output_digest",
    }
    contract.exact_fields(output, expected_fields, "E_V4_OUTPUT_FIELDS")
    contract.require(output.get("schema_version") == contract.OUTPUT_SCHEMA,
                     "E_V4_OUTPUT_SCHEMA")
    contract.require(output.get("task_id") == contract.TASK_ID,
                     "E_V4_OUTPUT_TASK")
    contract.require(output.get("generator_version") == contract.GENERATOR_VERSION and
                     output.get("rule_version") == contract.RULE_VERSION,
                     "E_V4_OUTPUT_VERSION")
    contract.require(output.get("request_id") == request["request_id"] and
                     output.get("request_digest") == request["request_digest"],
                     "E_V4_OUTPUT_REQUEST_JOIN")
    for field in ("batch_id", "run_id", "profile_id", "scenario_id"):
        contract.require(output.get(field) == request[field],
                         f"E_V4_OUTPUT_REQUEST_JOIN:{field}")
    for field in ("scenario_digest", "assignment_digest", "material_digest",
                  "policy_digest"):
        contract.require(output.get(field) == request[field],
                         f"E_V4_OUTPUT_CLOSURE:{field}")
    contract.require(output.get("attempt_index") == 1 and
                     output.get("attempt_id") == f"{request['request_id']}:attempt:1",
                     "E_V4_OUTPUT_ATTEMPT")
    contract.require(output.get("qualification_only") is True,
                     "E_V4_OUTPUT_QUALIFICATION")
    for field in ("publishable", "runtime_consumable", "counts_toward_300"):
        contract.require(output.get(field) is False, "E_V4_OUTPUT_BOUNDARY", field)
    contract.as_text(output["title"], "E_V4_OUTPUT_TITLE")
    contract.text_list(output["body"], "E_V4_OUTPUT_BODY")
    contract.text_list(output["spoken_lines"], "E_V4_OUTPUT_SPOKEN", allow_empty=True)
    contract.as_text(output["cta"], "E_V4_OUTPUT_CTA", allow_empty=True)
    contract.text_list(output["visual_execution"], "E_V4_OUTPUT_VISUAL")
    contract.text_list(output["audio_execution"], "E_V4_OUTPUT_AUDIO", allow_empty=True)
    disclosure = contract.as_text(output["synthetic_disclosure"],
                                  "E_V4_OUTPUT_DISCLOSURE")
    contract.require("合成" in disclosure and
                     ("测试" in disclosure or "非真实" in disclosure),
                     "E_V4_OUTPUT_DISCLOSURE")
    contract.require(output["author_attestation"] == EXPECTED_ATTESTATION,
                     "E_V4_OUTPUT_ATTESTATION")
    expected_sequence = surface_sequence(output)
    contract.require(isinstance(output["surface_units"], list) and
                     len(output["surface_units"]) == len(expected_sequence),
                     "E_V4_OUTPUT_SURFACE_COUNT")
    known_fact_ids = {fact["fact_id"] for fact in request["typed_material"]["facts"]}
    for index, (surface, expected) in enumerate(
            zip(output["surface_units"], expected_sequence, strict=True), 1):
        contract.exact_fields(surface,
                              {"surface_unit_id", "surface_kind", "text", "fact_ids"},
                              "E_V4_OUTPUT_SURFACE_FIELDS")
        contract.require(surface["surface_unit_id"] ==
                         f"{request['request_id']}:surface:{index:02d}",
                         "E_V4_OUTPUT_SURFACE_ID")
        contract.require((surface["surface_kind"], surface["text"]) == expected,
                         "E_V4_OUTPUT_SURFACE_JOIN")
        contract.require(surface["surface_kind"] in SURFACE_KINDS,
                         "E_V4_OUTPUT_SURFACE_KIND")
        fact_ids = contract.unique_text_list(surface["fact_ids"],
                                             "E_V4_OUTPUT_SURFACE_FACTS",
                                             allow_empty=True)
        contract.require(set(fact_ids).issubset(known_fact_ids),
                         "E_V4_OUTPUT_SURFACE_FACT_UNKNOWN")
        if surface["surface_kind"] == "synthetic_disclosure":
            contract.require(fact_ids == [], "E_V4_DISCLOSURE_FACT_BINDING")
    contract.validate_digest(output, "output_digest", "E_V4_OUTPUT_DIGEST")


__all__ = ["EXPECTED_ATTESTATION", "audience_text", "serialize", "surface_sequence",
           "validate_output", "validate_raw"]
