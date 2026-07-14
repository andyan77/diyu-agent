#!/usr/bin/env python3
"""Independent fail-closed guard for the Gate 1 P4 sealed probe."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import yaml

from p4_common import (
    ALLOWED_ACTIONS,
    ALLOWED_INPUT,
    ALLOWED_REASONS,
    AUTHOR_RECEIPT,
    AUTHOR_REQUESTS,
    BASELINE_MANIFEST,
    BLIND_CATALOG,
    BLIND_MAPPING,
    BLIND_PACKET,
    CHECKPOINT_RESULT,
    CURATED_ANOMALY,
    CURATED_POSITIVE,
    CURATION_CONTRACT,
    CURATION_VALIDATION,
    CURATOR_RECEIPT,
    CURRENT_CHECKER,
    CURRENT_OWNER,
    DECISION_PACKET,
    DELIVERY_RECEIPT,
    EXPECTED_PROFILES,
    EXPECTED_VARIANTS,
    EXIT_EVENTS,
    FROZEN_HASHES,
    HIDDEN_FREEZE,
    LIFECYCLE,
    MACHINE_REPORT,
    MODEL_CAPABILITY,
    POSITIVE_OUTPUTS,
    PROMPT_REVISION,
    REASONING_EFFORT,
    REVIEW_CONTRACT,
    REVIEW_ONE,
    REVIEW_ONE_STAGE,
    REVIEW_PACKET,
    REVIEW_TWO,
    REVIEW_TWO_STAGE,
    ROOT,
    ROUTE_ACTUAL_FREEZE,
    ROUTE_ACTUALS,
    ROUTE_COMPARISONS,
    ROUTE_GOLD,
    ROUTE_INPUTS,
    RUN_ORDER,
    SERVICE_TIER,
    TASK_ID,
    TASK_ROOT,
    TOOL_FREEZE,
    load_json,
    load_yaml,
    object_digest,
    read_jsonl,
    recursively_true,
    sha256_bytes,
    sha256_file,
    write_jsonl,
    write_yaml,
)


if not __debug__:
    print("p4_guard refuses python -O", file=sys.stderr)
    raise SystemExit(2)


Error = dict[str, str]
PRE_HIDDEN_STATES = {"TOOLS_PREPARED_PENDING_FREEZE_COMMIT", "TOOLS_FROZEN"}
HIDDEN_STATES = {
    "HIDDEN_FROZEN_PENDING_COMMIT",
    "HIDDEN_FROZEN",
    "RUN_FROZEN",
    "REVIEW_CLOSED",
    "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION",
    "STOPPED_RETURN_TO_P3",
}
RUN_STATES = {
    "RUN_FROZEN",
    "REVIEW_CLOSED",
    "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION",
    "STOPPED_RETURN_TO_P3",
}
REVIEW_STATES = {
    "REVIEW_CLOSED",
    "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION",
    "STOPPED_RETURN_TO_P3",
}


def _error(errors: list[Error], code: str, detail: str) -> None:
    errors.append({"code": code, "detail": detail})


def _required(root: Path, paths: tuple[Path, ...], errors: list[Error]) -> bool:
    missing = [path.as_posix() for path in paths if not (root / path).is_file()]
    if missing:
        _error(errors, "E_P4_REQUIRED_FILE", str(missing))
    return not missing


def _safe_yaml(root: Path, path: Path, errors: list[Error]) -> dict[str, Any] | None:
    try:
        return load_yaml(root / path)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        _error(errors, "E_P4_YAML", f"{path}:{exc}")
        return None


def _safe_rows(root: Path, path: Path, errors: list[Error]) -> list[dict[str, Any]]:
    try:
        return read_jsonl(root / path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        _error(errors, "E_P4_JSONL", f"{path}:{exc}")
        return []


def _validate_frozen(root: Path, errors: list[Error]) -> None:
    for path, expected in FROZEN_HASHES.items():
        absolute = root / path
        if not absolute.is_file() or sha256_file(absolute) != expected:
            _error(errors, "E_P4_FROZEN_BASELINE", path.as_posix())


def _validate_baseline(root: Path, errors: list[Error]) -> None:
    value = _safe_yaml(root, BASELINE_MANIFEST, errors)
    if value is None:
        return
    manifest = value.get("p4_frozen_baseline")
    if not isinstance(manifest, dict):
        _error(errors, "E_P4_BASELINE", "root")
        return
    if (
        manifest.get("task_id") != TASK_ID
        or manifest.get("prompt_revision") != PROMPT_REVISION
        or manifest.get("manifest_digest") != object_digest(manifest, "manifest_digest")
        or manifest.get("core_numbers")
        != {"300": "UNCHANGED", "120": "UNCHANGED", "86": "UNCHANGED"}
        or manifest.get("readiness_transition_authorized") is not False
    ):
        _error(errors, "E_P4_BASELINE", "identity, digest, numbers, or readiness")
    if manifest.get("frozen_files") != {
        path.as_posix(): digest for path, digest in FROZEN_HASHES.items()
    }:
        _error(errors, "E_P4_BASELINE", "frozen file map")


def _validate_tool_freeze(
    root: Path, lifecycle: Mapping[str, Any], errors: list[Error]
) -> None:
    state = lifecycle.get("state")
    if state == "TOOLS_PREPARED_PENDING_FREEZE_COMMIT":
        if (root / TOOL_FREEZE).exists():
            _error(errors, "E_P4_STAGE_ORDER", "tool freeze before commit binding")
        return
    value = _safe_yaml(root, TOOL_FREEZE, errors)
    if value is None:
        return
    freeze = value.get("p4_tool_freeze")
    if not isinstance(freeze, dict):
        _error(errors, "E_P4_TOOL_FREEZE", "root")
        return
    if (
        freeze.get("task_id") != TASK_ID
        or freeze.get("freeze_digest") != object_digest(freeze, "freeze_digest")
        or freeze.get("hidden_material_absent_from_tool_commit") is not True
        or freeze.get("frozen_before_hidden_creation") is not True
    ):
        _error(errors, "E_P4_TOOL_FREEZE", "identity or digest")
    files = freeze.get("tool_files")
    if not isinstance(files, dict) or not files:
        _error(errors, "E_P4_TOOL_FREEZE", "tool files")
        return
    for raw_path, expected in files.items():
        path = Path(str(raw_path))
        if not (root / path).is_file() or sha256_file(root / path) != expected:
            _error(errors, "E_P4_TOOL_MUTATION", path.as_posix())
    commit = freeze.get("tool_freeze_commit")
    if (root / ".git").exists() and isinstance(commit, str):
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if ancestor.returncode != 0:
            _error(errors, "E_P4_TOOL_FREEZE", "commit is not ancestor")
        for raw_path, expected in files.items():
            shown = subprocess.run(
                ["git", "show", f"{commit}:{raw_path}"],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if shown.returncode != 0 or sha256_bytes(shown.stdout) != expected:
                _error(errors, "E_P4_TOOL_FREEZE_COMMIT_BYTES", str(raw_path))
    if freeze.get("allowed_input_sha256") != sha256_file(root / ALLOWED_INPUT):
        _error(errors, "E_P4_ALLOWED_INPUT_MUTATION", "digest")
    if freeze.get("curation_contract_sha256") != sha256_file(root / CURATION_CONTRACT):
        _error(errors, "E_P4_TOOL_MUTATION", "curation contract")
    if freeze.get("review_contract_sha256") != sha256_file(root / REVIEW_CONTRACT):
        _error(errors, "E_P4_TOOL_MUTATION", "review contract")


def _validate_curated_positive(rows: list[dict[str, Any]], errors: list[Error]) -> None:
    if len(rows) != 20:
        _error(errors, "E_P4_POSITIVE_COUNT", str(len(rows)))
        return
    if {row.get("profile_id") for row in rows} != set(EXPECTED_PROFILES):
        _error(errors, "E_P4_POSITIVE_COVERAGE", "profiles")
    if Counter(str(row.get("assigned_variant")) for row in rows) != Counter(
        EXPECTED_VARIANTS
    ):
        _error(errors, "E_P4_VARIANT_DISTRIBUTION", "not 5 each")
    if sorted(row.get("run_order") for row in rows) != list(range(1, 21)):
        _error(errors, "E_P4_RUN_ORDER", "positive")
    for row in rows:
        if (
            row.get("task_id") != TASK_ID
            or row.get("schema_version") != "gate1-p4-curated-positive-v0.1"
            or row.get("case_digest") != object_digest(row, "case_digest")
        ):
            _error(errors, "E_P4_POSITIVE_DIGEST", str(row.get("case_id")))
        material = row.get("typed_material")
        if not isinstance(material, dict):
            _error(errors, "E_P4_TYPED_MATERIAL", str(row.get("case_id")))
            continue
        if (
            material.get("material_digest")
            != object_digest(material, "material_digest")
            or material.get("namespace") != "P4_SYNTHETIC_HIDDEN_QUALIFICATION"
            or material.get("profile_id") != row.get("profile_id")
            or material.get("synthetic_test_only") is not True
            or material.get("publishable") is not False
            or material.get("runtime_consumable") is not False
            or material.get("may_enter_300") is not False
        ):
            _error(errors, "E_P4_TYPED_MATERIAL", str(row.get("case_id")))
            continue
        sources = material.get("sources", [])
        auths = material.get("authorizations", [])
        facts = material.get("facts", [])
        source_ids = {
            item.get("source_id") for item in sources if isinstance(item, dict)
        }
        auth_ids = {
            item.get("authorization_id") for item in auths if isinstance(item, dict)
        }
        if not source_ids or not auth_ids or not facts:
            _error(errors, "E_P4_MATERIAL_CLOSURE", str(row.get("case_id")))
            continue
        kinds: set[str] = set()
        for fact in facts:
            if not isinstance(fact, dict):
                _error(errors, "E_P4_FACT", str(row.get("case_id")))
                continue
            kinds.add(str(fact.get("semantic_kind")))
            expected = sha256_bytes(str(fact.get("value", "")).encode("utf-8"))
            if (
                fact.get("fact_value_digest") != expected
                or not set(fact.get("source_ids", [])).issubset(source_ids)
                or not set(fact.get("authorization_ids", [])).issubset(auth_ids)
            ):
                _error(errors, "E_P4_FACT_BINDING", str(fact.get("fact_id")))
        required = {
            "setting",
            "actor",
            "object",
            "observation",
            "action",
            "result",
            "visual",
            "sound",
        }
        if not required.issubset(kinds):
            _error(errors, "E_P4_FACT_KIND_COVERAGE", str(row.get("profile_id")))


def _validate_hidden(root: Path, errors: list[Error]) -> None:
    paths = (
        CURATED_POSITIVE,
        CURATED_ANOMALY,
        CURATOR_RECEIPT,
        CURATION_VALIDATION,
        AUTHOR_REQUESTS,
        ROUTE_INPUTS,
        ROUTE_GOLD,
        RUN_ORDER,
        HIDDEN_FREEZE,
    )
    if not _required(root, paths, errors):
        return
    positives = _safe_rows(root, CURATED_POSITIVE, errors)
    anomalies = _safe_rows(root, CURATED_ANOMALY, errors)
    requests = _safe_rows(root, AUTHOR_REQUESTS, errors)
    inputs = _safe_rows(root, ROUTE_INPUTS, errors)
    gold = _safe_rows(root, ROUTE_GOLD, errors)
    order = _safe_rows(root, RUN_ORDER, errors)
    _validate_curated_positive(positives, errors)
    if len(anomalies) != 20 or {row.get("profile_id") for row in anomalies} != set(
        EXPECTED_PROFILES
    ):
        _error(errors, "E_P4_ANOMALY_COVERAGE", str(len(anomalies)))
    if len(requests) != 20 or len(inputs) != 20 or len(gold) != 20 or len(order) != 40:
        _error(
            errors,
            "E_P4_HIDDEN_COUNTS",
            f"{len(requests)}/{len(inputs)}/{len(gold)}/{len(order)}",
        )
    request_ids: set[str] = set()
    for row in requests:
        request_ids.add(str(row.get("request_id")))
        if (
            row.get("task_id") != TASK_ID
            or row.get("model_capability_id") != MODEL_CAPABILITY
            or row.get("reasoning_effort") != REASONING_EFFORT
            or row.get("service_tier") != SERVICE_TIER
            or row.get("request_digest") != object_digest(row, "request_digest")
            or row.get("author_output_contract", {}).get(
                "one_first_semantic_output_only"
            )
            is not True
        ):
            _error(errors, "E_P4_AUTHOR_REQUEST", str(row.get("request_id")))
        forbidden = {
            "gold_primary_action",
            "gold_primary_reason_category",
            "expected_score",
            "review_feedback",
        }
        if forbidden.intersection(row):
            _error(errors, "E_P4_AUTHOR_CONTEXT_LEAK", str(row.get("request_id")))
    input_ids: set[str] = set()
    for row in inputs:
        input_ids.add(str(row.get("case_id")))
        if (
            row.get("gold_fields_present") is not False
            or row.get("input_digest") != object_digest(row, "input_digest")
            or any(
                key.startswith("gold_") and key != "gold_fields_present"
                for key in row
            )
        ):
            _error(errors, "E_P4_ROUTE_GOLD_LEAK", str(row.get("case_id")))
    gold_ids: set[str] = set()
    actions: Counter[str] = Counter()
    for row in gold:
        gold_ids.add(str(row.get("case_id")))
        actions[str(row.get("gold_primary_action"))] += 1
        if (
            row.get("gold_primary_action") not in ALLOWED_ACTIONS
            or row.get("gold_primary_reason_category") not in ALLOWED_REASONS
            or row.get("gold_digest") != object_digest(row, "gold_digest")
        ):
            _error(errors, "E_P4_ROUTE_GOLD", str(row.get("case_id")))
    if input_ids != gold_ids or len(request_ids) != 20:
        _error(errors, "E_P4_HIDDEN_ID_SET", "request/input/gold")
    if (
        set(actions) != set(ALLOWED_ACTIONS)
        or max(actions.values(), default=0) - min(actions.values(), default=0) > 1
    ):
        _error(errors, "E_P4_ROUTE_BALANCE", str(dict(actions)))
    freeze_value = _safe_yaml(root, HIDDEN_FREEZE, errors)
    if freeze_value is not None:
        freeze = freeze_value.get("p4_hidden_input_freeze")
        if not isinstance(freeze, dict):
            _error(errors, "E_P4_HIDDEN_FREEZE", "root")
        else:
            if freeze.get("freeze_digest") != object_digest(freeze, "freeze_digest"):
                _error(errors, "E_P4_HIDDEN_FREEZE", "digest")
            hashes = freeze.get("frozen_file_hashes")
            if not isinstance(hashes, dict):
                _error(errors, "E_P4_HIDDEN_FREEZE", "hash map")
            else:
                for raw_path, expected in hashes.items():
                    path = Path(str(raw_path))
                    if (
                        not (root / path).is_file()
                        or sha256_file(root / path) != expected
                    ):
                        _error(errors, "E_P4_HIDDEN_MUTATION", path.as_posix())


def _validate_positive_outputs(
    requests: list[dict[str, Any]], outputs: list[dict[str, Any]], errors: list[Error]
) -> None:
    if len(outputs) != 20:
        _error(errors, "E_P4_OUTPUT_COUNT", str(len(outputs)))
        return
    request_by_id = {str(row["request_id"]): row for row in requests}
    if Counter(str(row.get("request_id")) for row in outputs) != Counter(request_by_id):
        _error(errors, "E_P4_OUTPUT_ID_SET", "missing duplicate or replacement")
    for output in outputs:
        request = request_by_id.get(str(output.get("request_id")))
        if request is None:
            continue
        case_id = str(output.get("request_id"))
        if (
            output.get("task_id") != TASK_ID
            or output.get("model_capability_id") != MODEL_CAPABILITY
            or output.get("request_digest") != request.get("request_digest")
            or output.get("output_digest") != object_digest(output, "output_digest")
            or output.get("profile_id") != request.get("profile_id")
            or output.get("assigned_variant") != request.get("assigned_variant")
            or output.get("publishable") is not False
            or output.get("runtime_consumable") is not False
            or output.get("counts_toward_300") is not False
        ):
            _error(errors, "E_P4_OUTPUT_IDENTITY", case_id)
        surfaces = output.get("surface_units")
        if not isinstance(surfaces, list) or not surfaces:
            _error(errors, "E_P4_OUTPUT_SURFACE", case_id)
            continue
        material = request["typed_material"]
        facts = {row["fact_id"] for row in material["facts"]}
        sources = {row["source_id"] for row in material["sources"]}
        auths = {row["authorization_id"] for row in material["authorizations"]}
        surface_ids: set[str] = set()
        for surface in surfaces:
            if not isinstance(surface, dict):
                _error(errors, "E_P4_OUTPUT_SURFACE", case_id)
                continue
            surface_ids.add(str(surface.get("surface_unit_id")))
            if surface.get("surface_kind") == "synthetic_disclosure":
                continue
            if (
                not surface.get("text")
                or not set(surface.get("fact_ids", [])).issubset(facts)
                or not set(surface.get("source_ids", [])).issubset(sources)
                or not set(surface.get("authorization_ids", [])).issubset(auths)
                or not surface.get("fact_ids")
                or not surface.get("source_ids")
                or not surface.get("authorization_ids")
            ):
                _error(
                    errors, "E_P4_UNBOUND_SURFACE", str(surface.get("surface_unit_id"))
                )
        usage = output.get("component_usage")
        approved = {row["component_id"] for row in request["approved_components"]}
        if (
            not isinstance(usage, list)
            or {row.get("component_id") for row in usage} != approved
        ):
            _error(errors, "E_P4_COMPONENT_USAGE", case_id)
        else:
            pointers: list[str] = []
            for item in usage:
                ids = item.get("implementation_surface_unit_ids", [])
                if not ids or not set(ids).issubset(surface_ids):
                    _error(
                        errors, "E_P4_COMPONENT_USAGE", str(item.get("component_id"))
                    )
                pointers.extend(map(str, ids))
            if len(set(pointers)) < max(2, len(usage) // 3):
                _error(errors, "E_P4_COMPONENT_EVIDENCE_COLLAPSE", case_id)
        attestation = output.get("author_attestation")
        if not isinstance(attestation, dict) or any(
            attestation.get(key) is not False
            for key in (
                "external_service_called",
                "input_backfilled_after_authoring",
                "review_performed_by_author",
                "second_candidate_generated",
                "unbound_fact_added",
            )
        ):
            _error(errors, "E_P4_AUTHOR_ATTESTATION", case_id)


def _validate_run(root: Path, errors: list[Error]) -> None:
    paths = (
        POSITIVE_OUTPUTS,
        AUTHOR_RECEIPT,
        ROUTE_ACTUALS,
        ROUTE_ACTUAL_FREEZE,
        ROUTE_COMPARISONS,
        EXIT_EVENTS,
        MACHINE_REPORT,
    )
    if not _required(root, paths, errors):
        return
    requests = _safe_rows(root, AUTHOR_REQUESTS, errors)
    outputs = _safe_rows(root, POSITIVE_OUTPUTS, errors)
    actuals = _safe_rows(root, ROUTE_ACTUALS, errors)
    comparisons = _safe_rows(root, ROUTE_COMPARISONS, errors)
    events = _safe_rows(root, EXIT_EVENTS, errors)
    _validate_positive_outputs(requests, outputs, errors)
    if len(actuals) != 20 or len(comparisons) != 20:
        _error(errors, "E_P4_ROUTE_COUNTS", f"{len(actuals)}/{len(comparisons)}")
    actions = Counter(str(row.get("actual_primary_action")) for row in actuals)
    if actions == Counter({"BLOCK": 20}):
        _error(errors, "E_P4_ALL_BLOCK", "20")
    for row in actuals:
        if any(key.startswith("gold_") for key in row):
            _error(errors, "E_P4_ROUTE_GOLD_LEAK", str(row.get("case_id")))
        if row.get("route_result_digest") != object_digest(row, "route_result_digest"):
            _error(errors, "E_P4_ROUTE_ACTUAL_DIGEST", str(row.get("case_id")))
    if len(events) < 4:
        _error(errors, "E_P4_EXIT_AUDIT", "missing role events")
    else:
        for event in events:
            if event.get("event_digest") != object_digest(event, "event_digest"):
                _error(errors, "E_P4_EXIT_AUDIT", str(event.get("event_id")))
            for key in (
                "external_provider_request_count",
                "external_api_call_count",
                "network_dispatch_count",
                "credential_read_count",
            ):
                if not isinstance(event.get(key), int) or int(event[key]) < 0:
                    _error(errors, "E_P4_EXIT_AUDIT", f"{event.get('event_id')}:{key}")
        if any(
            sum(int(event.get(key, 0)) for event in events) != 0
            for key in (
                "external_provider_request_count",
                "external_api_call_count",
                "network_dispatch_count",
                "credential_read_count",
            )
        ):
            _error(errors, "E_P4_EXTERNAL_EXIT", "nonzero")


def _validate_review(root: Path, errors: list[Error]) -> None:
    paths = (
        BLIND_PACKET,
        BLIND_CATALOG,
        BLIND_MAPPING,
        REVIEW_PACKET,
        REVIEW_ONE_STAGE,
        REVIEW_TWO_STAGE,
        REVIEW_ONE,
        REVIEW_TWO,
        CHECKPOINT_RESULT,
        DECISION_PACKET,
        DELIVERY_RECEIPT,
    )
    if not _required(root, paths, errors):
        return
    blind = _safe_rows(root, BLIND_PACKET, errors)
    mapping = _safe_rows(root, BLIND_MAPPING, errors)
    if len(blind) != 20 or len(mapping) != 20:
        _error(errors, "E_P4_BLIND_COUNTS", f"{len(blind)}/{len(mapping)}")
    forbidden_keys = {
        "profile_id",
        "content_product_type_id",
        "assigned_variant",
        "request_id",
    }
    for row in blind:
        if forbidden_keys.intersection(row):
            _error(errors, "E_P4_BLIND_LABEL_LEAK", str(row.get("blind_id")))
    reports: list[dict[str, Any]] = []
    for path, role in (
        (REVIEW_ONE, "CONTENT_VALUE"),
        (REVIEW_TWO, "FACT_AUTHORIZATION"),
    ):
        try:
            report = load_json(root / path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            _error(errors, "E_P4_REVIEW", f"{path}:{exc}")
            continue
        reports.append(report)
        if (
            report.get("task_id") != TASK_ID
            or report.get("review_role") != role
            or report.get("signed_record_digest")
            != object_digest(report, "signed_record_digest")
            or len(report.get("positive_reviews", [])) != 20
            or len(report.get("route_reviews", [])) != 20
        ):
            _error(errors, "E_P4_REVIEW", role)
    if len(reports) == 2:
        identity_fields = (
            "reviewer_identity",
            "reviewer_platform_agent_id",
            "reviewer_session_id",
            "review_run_id",
        )
        for field in identity_fields:
            if not reports[0].get(field) or reports[0].get(field) == reports[1].get(
                field
            ):
                _error(errors, "E_P4_REVIEWER_COLLISION", field)
        for report in reports:
            if report.get("reviewer_identity") in {
                "P4-ISOLATED-CURATOR-001",
                "P4-CONTROLLED-AUTHOR-GPT56SOL-001",
                "P4-EXECUTION-FREEZER-001",
            }:
                _error(
                    errors,
                    "E_P4_REVIEWER_COLLISION",
                    str(report.get("reviewer_identity")),
                )
            top1 = sum(
                1
                for row in report["positive_reviews"]
                if row.get("blind_top1_correct") is True
            )
            if top1 < 17:
                _error(errors, "E_P4_BLIND_TOP1", f"{report.get('review_role')}:{top1}")
    checkpoint_value = _safe_yaml(root, CHECKPOINT_RESULT, errors)
    if checkpoint_value is not None:
        result = checkpoint_value.get("p4_checkpoint_result")
        if not isinstance(result, dict):
            _error(errors, "E_P4_CHECKPOINT", "root")
        elif (
            result.get("result_digest") != object_digest(result, "result_digest")
            or result.get("generator_qualified") is not False
            or result.get("p5_allowed") is not False
            or result.get("H") != []
        ):
            _error(errors, "E_P4_QUALIFICATION_BEFORE_DECISION", "checkpoint")
    decision = _safe_yaml(root, DECISION_PACKET, errors)
    if decision is not None:
        packet = decision.get("founder_qualification_decision_packet")
        if not isinstance(packet, dict) or (
            packet.get("decision_state") != "PENDING_EXTERNAL_COORDINATOR_DECISION"
            or packet.get("decision_received") is not False
            or packet.get("approved_hidden_positive_ids") != []
        ):
            _error(errors, "E_P4_QUALIFICATION_BEFORE_DECISION", "decision packet")


def validate_p4_current(root: Path) -> list[Error]:
    errors: list[Error] = []
    if not (root / TASK_ROOT).is_dir():
        return errors
    required = (
        BASELINE_MANIFEST,
        ALLOWED_INPUT,
        CURATION_CONTRACT,
        REVIEW_CONTRACT,
        LIFECYCLE,
    )
    if not _required(root, required, errors):
        return errors
    _validate_frozen(root, errors)
    _validate_baseline(root, errors)
    lifecycle_value = _safe_yaml(root, LIFECYCLE, errors)
    if lifecycle_value is None:
        return errors
    lifecycle = lifecycle_value.get("p4_lifecycle")
    if not isinstance(lifecycle, dict):
        _error(errors, "E_P4_LIFECYCLE", "root")
        return errors
    if lifecycle.get("task_id") != TASK_ID or lifecycle.get(
        "lifecycle_digest"
    ) != object_digest(lifecycle, "lifecycle_digest"):
        _error(errors, "E_P4_LIFECYCLE", "identity or digest")
    state = str(lifecycle.get("state"))
    valid_states = PRE_HIDDEN_STATES | HIDDEN_STATES
    if state not in valid_states:
        _error(errors, "E_P4_LIFECYCLE", state)
    if (
        lifecycle.get("generator_qualified") is not False
        or lifecycle.get("p5_allowed") is not False
    ):
        _error(errors, "E_P4_QUALIFICATION_BEFORE_DECISION", state)
    if recursively_true(lifecycle):
        _error(errors, "E_P4_READINESS", str(recursively_true(lifecycle)))
    _validate_tool_freeze(root, lifecycle, errors)
    hidden_paths = (
        CURATED_POSITIVE,
        CURATED_ANOMALY,
        AUTHOR_REQUESTS,
        ROUTE_INPUTS,
        ROUTE_GOLD,
        HIDDEN_FREEZE,
    )
    if state in PRE_HIDDEN_STATES:
        unexpected = [
            path.as_posix() for path in hidden_paths if (root / path).exists()
        ]
        if unexpected:
            _error(errors, "E_P4_STAGE_ORDER", str(unexpected))
    if state in HIDDEN_STATES:
        _validate_hidden(root, errors)
    run_paths = (POSITIVE_OUTPUTS, ROUTE_ACTUALS, ROUTE_COMPARISONS)
    if state not in RUN_STATES and any((root / path).exists() for path in run_paths):
        _error(errors, "E_P4_STAGE_ORDER", "run files before RUN_FROZEN")
    if state in RUN_STATES:
        _validate_run(root, errors)
    if state not in REVIEW_STATES and any(
        (root / path).exists() for path in (REVIEW_ONE, REVIEW_TWO, CHECKPOINT_RESULT)
    ):
        _error(errors, "E_P4_STAGE_ORDER", "review files before review state")
    if state in REVIEW_STATES:
        _validate_review(root, errors)
    owner_value = _safe_yaml(root, CURRENT_OWNER, errors)
    if owner_value is not None:
        owner = owner_value.get("current_gate1_owner", {})
        if owner.get("owner_id") != "GATE1_V11_P3_OPEN_PROBE_FINAL_OWNER":
            _error(errors, "E_P4_OWNER_EARLY_ADVANCE", str(owner.get("owner_id")))
    return errors


def _copy_fixture(root: Path, target: Path) -> None:
    for path in FROZEN_HASHES:
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, destination)
    for path in (CURRENT_OWNER, CURRENT_CHECKER):
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, destination)
    shutil.copytree(root / TASK_ROOT, target / TASK_ROOT)


def selftest(root: Path) -> int:
    if validate_p4_current(root):
        print(
            json.dumps(
                {"status": "SELFTEST_BLOCKED", "reason": "live P4 invalid"},
                ensure_ascii=False,
            )
        )
        return 1
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="p4-guard-") as raw:
        fixture = Path(raw)
        _copy_fixture(root, fixture)
        lifecycle_path = fixture / LIFECYCLE
        original = load_yaml(lifecycle_path)
        mutated = copy.deepcopy(original)
        row = mutated["p4_lifecycle"]
        row["generator_qualified"] = True
        row["lifecycle_digest"] = object_digest(row, "lifecycle_digest")
        write_yaml(lifecycle_path, mutated)
        codes = {error["code"] for error in validate_p4_current(fixture)}
        if "E_P4_QUALIFICATION_BEFORE_DECISION" not in codes:
            failures.append({"case": "early qualification", "codes": sorted(codes)})
        write_yaml(lifecycle_path, original)
        frozen_path = next(iter(FROZEN_HASHES))
        (fixture / frozen_path).write_bytes(
            (fixture / frozen_path).read_bytes() + b"\n"
        )
        codes = {error["code"] for error in validate_p4_current(fixture)}
        if "E_P4_FROZEN_BASELINE" not in codes:
            failures.append({"case": "frozen tamper", "codes": sorted(codes)})
        route_input_path = fixture / ROUTE_INPUTS
        if route_input_path.is_file():
            shutil.rmtree(fixture)
            _copy_fixture(root, fixture)
            rows = read_jsonl(fixture / ROUTE_INPUTS)
            rows[0]["gold_primary_action"] = "BLOCK"
            rows[0]["input_digest"] = object_digest(rows[0], "input_digest")
            write_jsonl(fixture / ROUTE_INPUTS, rows)
            codes = {error["code"] for error in validate_p4_current(fixture)}
            if "E_P4_ROUTE_GOLD_LEAK" not in codes:
                failures.append(
                    {"case": "route gold leak", "codes": sorted(codes)}
                )
    if failures:
        print(
            json.dumps(
                {"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "SELFTEST_PASS",
                "early_qualification_rejected": True,
                "frozen_baseline_tamper_rejected": True,
                "route_gold_leak_rejected_when_hidden_exists": True,
                "dynamic_stage_checks_enabled": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest(ROOT)
    errors = validate_p4_current(ROOT)
    print(
        json.dumps(
            {"status": "PASS" if not errors else "FAIL", "errors": errors},
            ensure_ascii=False,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
