#!/usr/bin/env python3
"""Validate isolated Creative Author responses without rewriting them."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from typing import Any


FORBIDDEN_SURFACE_TERMS = (
    "CP01",
    "CP02",
    "CP03",
    "CP04",
    "CP05",
    "CP06",
    "CP07",
    "CP08",
    "CP09",
    "CP10",
    "CP11",
    "CP12",
    "CP13",
    "CP14",
    "CP15",
    "CP16",
    "CP17",
    "CP18",
    "CP19",
    "CP20",
    "role_task_vlog",
    "store_time_slice_micro_documentary",
    "qualification",
    "hidden",
    "内部审查",
    "预期分数",
)

STYLE_AXES = (
    "information_order",
    "narrative_distance",
    "language_register",
    "sentence_rhythm",
    "visual_subject",
    "shot_continuity",
    "sound_subject",
    "ending_mode",
    "CTA_policy",
)

SURFACE_LIST_FIELDS = (
    "body_blocks",
    "spoken_lines",
    "visual_beats",
    "capture_instructions",
)

SURFACE_SCALAR_FIELDS = ("title", "CTA", "audio_grammar", "editing_grammar")


def _surface_map(response: Mapping[str, Any]) -> dict[str, str]:
    surfaces = response.get("surfaces")
    if not isinstance(surfaces, Mapping):
        return {}
    result: dict[str, str] = {}
    for field in SURFACE_SCALAR_FIELDS:
        value = surfaces.get(field)
        if value is None:
            value = ""
        if isinstance(value, str):
            result[f"surfaces.{field}"] = value
    for field in SURFACE_LIST_FIELDS:
        values = surfaces.get(field)
        if not isinstance(values, list):
            continue
        for index, value in enumerate(values):
            if isinstance(value, str):
                result[f"surfaces.{field}[{index}]"] = value
    return result


def _normalized_lines(value: str) -> set[str]:
    lines: set[str] = set()
    for line in value.splitlines():
        normalized = re.sub(r"[\W_]+", "", line, flags=re.UNICODE).lower()
        if normalized:
            lines.add(normalized)
    return lines


def validate_response(request: Mapping[str, Any], response: Mapping[str, Any]) -> list[str]:
    """Return all structural and safety failures; never edit the response."""

    errors: list[str] = []
    if response.get("request_id") != request.get("request_id"):
        errors.append("E_REQUEST_ID_MISMATCH")
    if response.get("request_digest") != request.get("request_digest"):
        errors.append("E_REQUEST_DIGEST_MISMATCH")
    if response.get("backend_class") != "CONTROLLED_EXECUTION_AGENT":
        errors.append("E_BACKEND_CLASS")
    if response.get("one_request_one_response") is not True:
        errors.append("E_ONE_REQUEST_ONE_RESPONSE")
    if response.get("paired_output_visible") is not False:
        errors.append("E_PAIRED_OUTPUT_VISIBLE")
    if response.get("review_envelope_visible") is not False:
        errors.append("E_REVIEW_ENVELOPE_VISIBLE")
    if response.get("expected_score_visible") is not False:
        errors.append("E_EXPECTED_SCORE_VISIBLE")
    if response.get("chain_of_thought_stored") is not False:
        errors.append("E_CHAIN_OF_THOUGHT_STORED")

    surface_map = _surface_map(response)
    expected_paths = set(surface_map)
    if not expected_paths:
        errors.append("E_EMPTY_SURFACE")

    output_contract = request.get("content_product_contract", {}).get("output_contract", {})
    if not isinstance(output_contract, Mapping):
        errors.append("E_OUTPUT_CONTRACT")
        output_contract = {}
    for field in SURFACE_LIST_FIELDS:
        values = response.get("surfaces", {}).get(field)
        if not isinstance(values, list):
            errors.append(f"E_SURFACE_TYPE:{field}")
    for field in SURFACE_SCALAR_FIELDS:
        value = response.get("surfaces", {}).get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"E_SURFACE_TYPE:{field}")

    for path, text in surface_map.items():
        for term in FORBIDDEN_SURFACE_TERMS:
            if term.lower() in text.lower():
                errors.append(f"E_INTERNAL_LABEL_LEAK:{path}:{term}")

    bindings = response.get("surface_bindings")
    if not isinstance(bindings, list):
        errors.append("E_SURFACE_BINDINGS_TYPE")
        bindings = []
    binding_paths: list[str] = []
    atom_ids = {
        str(atom.get("atom_id"))
        for atom in request.get("immutable_evidence_atoms", [])
        if isinstance(atom, Mapping)
    }
    allowed_licenses = set(request.get("creative_license", []))
    for binding in bindings:
        if not isinstance(binding, Mapping):
            errors.append("E_SURFACE_BINDING_SHAPE")
            continue
        path = str(binding.get("surface_path", ""))
        binding_paths.append(path)
        if path not in surface_map:
            errors.append(f"E_UNKNOWN_SURFACE_BINDING:{path}")
            continue
        if binding.get("text") != surface_map[path]:
            errors.append(f"E_EXACT_JOIN:{path}")
        source_refs = binding.get("source_atom_refs")
        semantic_license = binding.get("semantic_license")
        if not isinstance(source_refs, list) or not set(map(str, source_refs)).issubset(atom_ids):
            errors.append(f"E_SOURCE_BINDING:{path}")
        if not source_refs and semantic_license not in allowed_licenses:
            errors.append(f"E_CREATIVE_LICENSE:{path}")
        if source_refs and not semantic_license:
            errors.append(f"E_SEMANTIC_LICENSE_MISSING:{path}")
    duplicates = [path for path, count in Counter(binding_paths).items() if count != 1]
    for path in duplicates:
        errors.append(f"E_SURFACE_BINDING_COUNT:{path}")
    for path in sorted(expected_paths.difference(binding_paths)):
        errors.append(f"E_UNBOUND_SURFACE:{path}")

    style_evidence = response.get("style_realization_evidence")
    if not isinstance(style_evidence, list):
        errors.append("E_STYLE_EVIDENCE_TYPE")
        style_evidence = []
    style_by_axis = {
        str(item.get("axis")): item
        for item in style_evidence
        if isinstance(item, Mapping)
    }
    for axis in STYLE_AXES:
        item = style_by_axis.get(axis)
        if item is None:
            errors.append(f"E_STYLE_AXIS_MISSING:{axis}")
            continue
        refs = item.get("actual_surface_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"E_STYLE_AXIS_NO_REFS:{axis}")
        elif not set(map(str, refs)).issubset(expected_paths):
            errors.append(f"E_STYLE_AXIS_BAD_REFS:{axis}")

    obligation_evidence = response.get("required_obligation_evidence")
    if not isinstance(obligation_evidence, list):
        errors.append("E_OBLIGATION_EVIDENCE_TYPE")
        obligation_evidence = []
    obligation_by_id = {
        str(item.get("obligation_id")): item
        for item in obligation_evidence
        if isinstance(item, Mapping)
    }
    obligations = request.get("content_product_contract", {}).get("required_obligations", [])
    for obligation in obligations:
        obligation_id = str(obligation.get("obligation_id"))
        item = obligation_by_id.get(obligation_id)
        if item is None:
            errors.append(f"E_OBLIGATION_MISSING:{obligation_id}")
            continue
        refs = item.get("actual_surface_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"E_OBLIGATION_NO_REFS:{obligation_id}")
        elif not set(map(str, refs)).issubset(expected_paths):
            errors.append(f"E_OBLIGATION_BAD_REFS:{obligation_id}")

    spoken_lines = response.get("surfaces", {}).get("spoken_lines", [])
    body_blocks = response.get("surfaces", {}).get("body_blocks", [])
    if isinstance(spoken_lines, list) and isinstance(body_blocks, list):
        body_normalized = set().union(*(_normalized_lines(str(item)) for item in body_blocks))
        for line in spoken_lines:
            if _normalized_lines(str(line)).intersection(body_normalized):
                errors.append("E_SPOKEN_BODY_EXACT_COPY")

    if output_contract.get("spoken_policy") == "OPTIONAL_OR_NONE" and request.get(
        "content_product_contract", {}
    ).get("profile_id") == "CP14":
        pass
    elif not response.get("surfaces", {}).get("body_blocks"):
        errors.append("E_BODY_REQUIRED")

    return sorted(set(errors))


if __name__ == "__main__":
    raise SystemExit(2)
