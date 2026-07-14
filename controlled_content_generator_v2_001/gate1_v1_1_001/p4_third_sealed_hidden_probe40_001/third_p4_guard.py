#!/usr/bin/env python3
"""Independent fail-closed guard for the third sealed P4 lifecycle."""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

import third_p4 as p4


if not __debug__:
    sys.stderr.write("third_p4_guard refuses python -O\n")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[3]
LIFECYCLE_FIELDS = {
    "schema_version", "task_id", "lifecycle_state", "previous_lifecycle_digest", "evidence_digests",
    "hidden_frozen", "hidden_exposed", "hidden_reusable", "technical_gate_pass",
    "reviews_pass", "decision_present", "approved_first_output_request_ids", "H",
    "generator_qualified", "p5_allowed", "target_baseline_count",
    "positive_target_count", "route_target_count", "legacy_reference_inventory_count",
    "counted_positive_parent_count", "historical_component_inventory_count",
    "active_component_count", "external_provider_request_count", "p5_executed",
    "readiness", "lifecycle_digest",
}


def add(errors: list[dict[str, str]], code: str, detail: str = "") -> None:
    errors.append({"code": code, "detail": detail})


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path.as_posix())
    return value


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )


def _validate_lifecycle(value: Mapping[str, Any], errors: list[dict[str, str]]) -> None:
    if set(value) != LIFECYCLE_FIELDS:
        add(errors, "E_T3_LIFECYCLE_FIELDS")
        return
    if value.get("schema_version") != "gate1-third-p4-lifecycle-v1.0" or value.get("task_id") != p4.TASK_ID:
        add(errors, "E_T3_LIFECYCLE_SCHEMA")
    if value.get("lifecycle_digest") != p4.object_digest(value, "lifecycle_digest"):
        add(errors, "E_T3_LIFECYCLE_DIGEST")
    previous = value.get("previous_lifecycle_digest")
    if not isinstance(previous, str) or (previous and re.fullmatch(r"[0-9a-f]{64}", previous) is None):
        add(errors, "E_T3_PREVIOUS_LIFECYCLE_DIGEST")
    try:
        contract = json.loads((ROOT / p4.THIRD_CONTRACT).read_text(encoding="utf-8"))
        expected = contract["lifecycle_states"][value["lifecycle_state"]]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        add(errors, "E_T3_LIFECYCLE_STATE")
        return
    h_expected = (
        len(value.get("approved_first_output_request_ids", []))
        if expected["h_count"] == "APPROVED_FIRST_OUTPUT_COUNT"
        else expected["h_count"]
    )
    checks = {
        "hidden_frozen": expected["hidden_frozen"],
        "hidden_exposed": expected["hidden_exposed"],
        "technical_gate_pass": expected["technical_gate_pass"],
        "reviews_pass": expected["reviews_pass"],
        "decision_present": expected["decision_present"],
        "generator_qualified": expected["generator_qualified"],
        "p5_allowed": expected["p5_allowed"],
        "H": h_expected,
    }
    for key, expected_value in checks.items():
        if value.get(key) != expected_value:
            add(errors, "E_T3_LIFECYCLE_BOUNDARY", key)
    if value.get("hidden_reusable") is not False or value.get("p5_executed") is not False:
        add(errors, "E_T3_LIFECYCLE_FORBIDDEN_ENABLE")
    if value.get("approved_first_output_request_ids") and value.get("lifecycle_state") != "PASS_TO_P5_POSITIVE_SCALE":
        add(errors, "E_T3_EARLY_H_ADMISSION")
    if (
        value.get("target_baseline_count") != 300
        or value.get("positive_target_count") != 240
        or value.get("route_target_count") != 60
        or value.get("legacy_reference_inventory_count") != 120
        or value.get("counted_positive_parent_count") != 29
        or value.get("historical_component_inventory_count") != 86
        or value.get("active_component_count") != 68
        or value.get("external_provider_request_count") != 0
        or value.get("readiness") != p4.READY_FALSE
    ):
        add(errors, "E_T3_GLOBAL_BOUNDARY")


def _validate_tool_freeze(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        freeze = load_yaml(root / p4.TOOL_FREEZE).get("third_p4_tool_freeze")
        if not isinstance(freeze, dict):
            raise TypeError("tool freeze root")
        if freeze.get("tool_freeze_digest") != p4.object_digest(freeze, "tool_freeze_digest"):
            add(errors, "E_T3_TOOL_FREEZE_DIGEST")
        for raw_path, expected in freeze.get("tool_file_sha256", {}).items():
            path = root / Path(raw_path)
            if not path.is_file() or p4.sha256_file(path) != expected:
                add(errors, "E_T3_TOOL_FILE_DRIFT", raw_path)
        for raw_path, expected in freeze.get("frozen_business_sha256", {}).items():
            path = root / Path(raw_path)
            if not path.is_file() or p4.sha256_file(path) != expected:
                add(errors, "E_T3_FROZEN_BUSINESS_DRIFT", raw_path)
        if p4.sha256_file(root / p4.ALLOWED_INPUT) != freeze.get("curator_allowed_input_sha256"):
            add(errors, "E_T3_ALLOWED_INPUT_DRIFT")
        builder = p4._module(
            p4.TASK_ROOT / "build_curator_allowed_input.py",
            "gate1_third_p4_curator_projection_guard",
        )
        allowed = json.loads((root / p4.ALLOWED_INPUT).read_text(encoding="utf-8"))
        builder.validate_allowed_input(allowed, root)
        if freeze.get("hidden_material_absent") is not True or freeze.get("six_lifecycle_states_predeclared") is not True:
            add(errors, "E_T3_TOOL_FREEZE_BOUNDARY")
        if freeze.get("model_config") != {
            "model_capability_id": p4.MODEL_CAPABILITY,
            "reasoning_effort": p4.REASONING_EFFORT,
            "service_tier": p4.SERVICE_TIER,
        }:
            add(errors, "E_T3_MODEL_CONFIG")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add(errors, "E_T3_TOOL_FREEZE_PARSE", str(exc))


def _validate_history(root: Path, errors: list[dict[str, str]]) -> None:
    if not (root / ".git").exists():
        return
    for relative, expected in (
        (p4.OLD_P4_ROOT, p4.OLD_P4_TREE),
        (p4.RESEALED_P4_ROOT, p4.RESEALED_P4_TREE),
        (p4.P3_RECOVERY_ROOT, p4.P3_RECOVERY_TREE),
    ):
        result = git(root, "rev-parse", f"HEAD:{relative.as_posix()}")
        if result.returncode != 0 or result.stdout.strip() != expected:
            add(errors, "E_T3_HISTORICAL_TREE_DRIFT", relative.as_posix())


def _validate_owner(root: Path, lifecycle: Mapping[str, Any], errors: list[dict[str, str]]) -> None:
    try:
        owner = load_yaml(root / p4.OWNER).get("current_gate1_owner")
        if not isinstance(owner, dict):
            raise TypeError("owner root")
        if owner.get("owner_digest") != p4.object_digest(owner, "owner_digest"):
            add(errors, "E_T3_OWNER_DIGEST")
            add(errors, "E_OWNER_POLICY", "third owner digest")
        if (
            owner.get("owner_id") != "GATE1_V11_P4_THIRD_SEALED_OWNER"
            or owner.get("task_id") != p4.TASK_ID
            or owner.get("current_task_root") != p4.TASK_ROOT.as_posix()
            or owner.get("current_checker") != p4.CURRENT_CHECKER.as_posix()
            or owner.get("result_state") != lifecycle.get("lifecycle_state")
            or owner.get("third_hidden_created") != lifecycle.get("hidden_frozen")
            or owner.get("third_hidden_exposed") != lifecycle.get("hidden_exposed")
            or owner.get("same_hidden_batch_may_be_reused") is not False
            or owner.get("H_admitted_count") != lifecycle.get("H")
            or owner.get("generator_qualified") != lifecycle.get("generator_qualified")
            or owner.get("p5_allowed") != lifecycle.get("p5_allowed")
            or owner.get("p5_executed") is not False
        ):
            add(errors, "E_T3_OWNER_BOUNDARY")
        if owner.get("core_numbers") != {
            "target_total": 300,
            "positive_target": 240,
            "route_target": 60,
            "reference_inventory": 120,
            "counted_positive_parent_count": 29,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        }:
            add(errors, "E_T3_OWNER_CORE_NUMBERS")
        readiness = owner.get("readiness")
        if not isinstance(readiness, Mapping):
            add(errors, "E_T3_OWNER_READINESS")
        else:
            for key, value in p4.READY_FALSE.items():
                if readiness.get(key) is not value:
                    add(errors, "E_T3_OWNER_READINESS", key)
            if readiness.get("runtime_ingest_ready") is not False or readiness.get("generator_qualified") != lifecycle.get("generator_qualified"):
                add(errors, "E_T3_OWNER_READINESS", "successor")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add(errors, "E_T3_OWNER_PARSE", str(exc))


def _validate_hidden(root: Path, errors: list[dict[str, str]]) -> None:
    required = (
        p4.CURATION_BUNDLE, p4.ROLE_MANIFEST, p4.TOOL_COMMIT_BINDING, p4.AUTHOR_REQUESTS,
        p4.ROUTE_INPUTS, p4.ROUTE_GOLD, p4.HIDDEN_FREEZE,
    )
    for path in required:
        if not (root / path).is_file():
            add(errors, "E_T3_HIDDEN_REQUIRED", path.as_posix())
    if errors:
        return
    try:
        bundle = json.loads((root / p4.CURATION_BUNDLE).read_text(encoding="utf-8"))
        role_manifest = json.loads((root / p4.ROLE_MANIFEST).read_text(encoding="utf-8"))
        p4.validate_role_manifest(role_manifest)
        if bundle.get("role_manifest") != role_manifest:
            add(errors, "E_T3_ROLE_MANIFEST_BINDING")
        p4.validate_curation_bundle(bundle)
        requests = p4.read_jsonl(root / p4.AUTHOR_REQUESTS)
        rebuilt = [
            p4._build_author_request(item["request"], bundle["role_manifest"])
            for item in sorted(bundle["positive_rows"], key=lambda row: row["request"]["run_order"])
        ]
        if requests != rebuilt:
            add(errors, "E_T3_AUTHOR_REQUEST_REBUILD")
        if p4.read_jsonl(root / p4.ROUTE_INPUTS) != [
            item["route_input"] for item in sorted(bundle["anomaly_rows"], key=lambda row: row["profile_id"])
        ]:
            add(errors, "E_T3_ROUTE_INPUT_REBUILD")
        if p4.read_jsonl(root / p4.ROUTE_GOLD) != sorted(bundle["gold_rows"], key=lambda row: row["profile_id"]):
            add(errors, "E_T3_GOLD_REBUILD")
        freeze = load_yaml(root / p4.HIDDEN_FREEZE).get("third_p4_hidden_input_freeze")
        binding = load_yaml(root / p4.TOOL_COMMIT_BINDING).get("third_p4_tool_commit_binding")
        if not isinstance(freeze, dict) or freeze.get("freeze_digest") != p4.object_digest(freeze, "freeze_digest"):
            add(errors, "E_T3_HIDDEN_FREEZE_DIGEST")
        elif (
            freeze.get("curation_bundle_sha256") != p4.sha256_file(root / p4.CURATION_BUNDLE)
            or freeze.get("role_manifest_sha256") != p4.sha256_file(root / p4.ROLE_MANIFEST)
            or freeze.get("positive_requests_sha256") != p4.sha256_file(root / p4.AUTHOR_REQUESTS)
            or freeze.get("anomaly_inputs_sha256") != p4.sha256_file(root / p4.ROUTE_INPUTS)
            or freeze.get("anomaly_gold_sha256") != p4.sha256_file(root / p4.ROUTE_GOLD)
            or freeze.get("positive_count") != 20
            or freeze.get("anomaly_count") != 20
            or freeze.get("gold_count") != 20
            or freeze.get("hidden_reusable") is not False
        ):
            add(errors, "E_T3_HIDDEN_FREEZE_BOUNDARY")
        if not isinstance(binding, dict) or binding.get("binding_digest") != p4.object_digest(binding, "binding_digest"):
            add(errors, "E_T3_TOOL_BINDING_DIGEST")
        elif (root / ".git").exists():
            commit = str(binding.get("tool_commit"))
            for path in (p4.CURATION_BUNDLE, p4.ROLE_MANIFEST, p4.AUTHOR_REQUESTS, p4.ROUTE_INPUTS, p4.ROUTE_GOLD, p4.HIDDEN_FREEZE):
                if git(root, "cat-file", "-e", f"{commit}:{path.as_posix()}").returncode == 0:
                    add(errors, "E_T3_HIDDEN_IN_TOOL_COMMIT", path.as_posix())
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        add(errors, "E_T3_HIDDEN_PARSE", str(exc))


def _recompute_machine(root: Path, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    required = (
        p4.RAW_OUTPUTS, p4.AUTHOR_RECEIPT, p4.COMPILED_ROUTES, p4.ROUTE_ACTUALS,
        p4.ROUTE_ACTUAL_FREEZE, p4.EXTERNAL_AUDIT, p4.MACHINE_REPORT,
        p4.ROUTE_COMPARISONS,
    )
    for path in required:
        if not (root / path).is_file():
            add(errors, "E_T3_RUN_REQUIRED", path.as_posix())
    if errors:
        return None
    try:
        requests = p4.read_jsonl(root / p4.AUTHOR_REQUESTS)
        raws = p4.read_jsonl(root / p4.RAW_OUTPUTS)
        positive_pass = False
        outputs: list[dict[str, Any]] = []
        try:
            outputs = p4.author_module().serialize_all(raws, requests)
            positive_pass = len(outputs) == 20
        except (OSError, TypeError, ValueError):
            positive_pass = False
        if positive_pass:
            if not (root / p4.NORMALIZED_OUTPUTS).is_file() or outputs != p4.read_jsonl(root / p4.NORMALIZED_OUTPUTS):
                add(errors, "E_T3_NORMALIZED_REBUILD")
        route_inputs = p4.read_jsonl(root / p4.ROUTE_INPUTS)
        compiled, actuals, route_errors = p4._route_actuals(route_inputs)
        if compiled != p4.read_jsonl(root / p4.COMPILED_ROUTES) or actuals != p4.read_jsonl(root / p4.ROUTE_ACTUALS):
            add(errors, "E_T3_ROUTE_ACTUAL_REBUILD")
        route_freeze = load_yaml(root / p4.ROUTE_ACTUAL_FREEZE).get("third_p4_route_actual_freeze")
        if not isinstance(route_freeze, dict) or route_freeze.get("freeze_digest") != p4.object_digest(route_freeze, "freeze_digest"):
            add(errors, "E_T3_ROUTE_FREEZE_DIGEST")
        elif (
            route_freeze.get("actuals_sha256") != p4.sha256_file(root / p4.ROUTE_ACTUALS)
            or route_freeze.get("compiled_sha256") != p4.sha256_file(root / p4.COMPILED_ROUTES)
            or route_freeze.get("gold_read_before_actual_freeze") is not False
            or route_freeze.get("route_errors") != route_errors
        ):
            add(errors, "E_T3_ROUTE_FREEZE_BOUNDARY")
        gold = p4.read_jsonl(root / p4.ROUTE_GOLD)
        comparisons = p4._comparison_rows(actuals, gold)
        if comparisons != p4.read_jsonl(root / p4.ROUTE_COMPARISONS):
            add(errors, "E_T3_ROUTE_COMPARISON_REBUILD")
        action = sum(row["action_match"] is True for row in comparisons)
        reason = sum(row["reason_match"] is True for row in comparisons)
        leaks = sum(row["audience_leak"] is True for row in comparisons)
        audit = load_yaml(root / p4.EXTERNAL_AUDIT).get("third_p4_external_exit_audit")
        if not isinstance(audit, dict) or audit.get("audit_digest") != p4.object_digest(audit, "audit_digest"):
            add(errors, "E_T3_EXTERNAL_AUDIT_DIGEST")
            external_zero = False
        else:
            external_zero = audit.get("external_provider_request_count") == len(audit.get("observed_content_exit_events", [])) == 0
            if not external_zero or any(audit.get(key) != 0 for key in ("external_provider_response_count", "external_api_call_count", "credential_read_count", "network_dispatch_count")):
                add(errors, "E_T3_EXTERNAL_EXIT")
        expected_pass = positive_pass and action == 20 and reason == 20 and leaks == 0 and external_zero
        report = load_yaml(root / p4.MACHINE_REPORT).get("third_p4_machine_acceptance")
        if not isinstance(report, dict) or report.get("report_digest") != p4.object_digest(report, "report_digest"):
            add(errors, "E_T3_MACHINE_REPORT_DIGEST")
            return None
        if (
            report.get("positive_strict_pass_count") != (20 if positive_pass else 0)
            or report.get("positive_first_raw_count") != len(raws)
            or report.get("normalized_output_count") != len(outputs)
            or report.get("route_action_match_count") != action
            or report.get("route_reason_match_count") != reason
            or report.get("route_audience_leak_count") != leaks
            or report.get("technical_gate_pass") is not expected_pass
            or report.get("second_candidate_count") != 0
            or report.get("replacement_count") != 0
        ):
            add(errors, "E_T3_MACHINE_REPORT_RECOMPUTE")
        return report
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        add(errors, "E_T3_MACHINE_RECOMPUTE", str(exc))
        return None


def _validate_reviews(root: Path, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    required = (
        p4.BLIND_PACKET, p4.BLIND_CATALOG, p4.BLIND_MAPPING, p4.REVIEW_PACKET,
        p4.CONTENT_STAGE, p4.FACT_STAGE, p4.CONTENT_REVIEW, p4.FACT_REVIEW,
        p4.REVIEW_METRICS,
    )
    for path in required:
        if not (root / path).is_file():
            add(errors, "E_T3_REVIEW_REQUIRED", path.as_posix())
    if errors:
        return None
    try:
        manifest = json.loads((root / p4.CURATION_BUNDLE).read_text(encoding="utf-8"))["role_manifest"]
        content = p4._validate_review(
            p4._load_json(root / p4.CONTENT_REVIEW),
            p4._load_json(root / p4.CONTENT_STAGE),
            "CONTENT_VALUE", manifest,
        )
        fact = p4._validate_review(
            p4._load_json(root / p4.FACT_REVIEW),
            p4._load_json(root / p4.FACT_STAGE),
            "FACT_AUTHORIZATION", manifest,
        )
        formula = sorted(set(content["formula"]) | set(fact["formula"]))
        hard = sorted(set(content["hard"]) | set(fact["hard"]))
        disagreement_ids = {
            blind_id
            for blind_id in content["per_item"]
            if content["per_item"][blind_id] != fact["per_item"][blind_id]
        }
        adjudication_digest = p4._validate_targeted_adjudication(manifest, disagreement_ids)
        common = sorted(set(content["acceptable_requests"]) & set(fact["acceptable_requests"]))
        reviews_pass = bool(content["pass"] and fact["pass"] and len(formula) <= 2 and not hard)
        metrics = load_yaml(root / p4.REVIEW_METRICS).get("third_p4_review_metrics")
        if not isinstance(metrics, dict) or metrics.get("metrics_digest") != p4.object_digest(metrics, "metrics_digest"):
            add(errors, "E_T3_REVIEW_METRICS_DIGEST")
            return None
        expected = {
            "content_value_first_acceptable_count": content["acceptable"],
            "fact_authorization_first_acceptable_count": fact["acceptable"],
            "content_value_blind_profile_correct_count": content["blind_correct"],
            "fact_authorization_blind_profile_correct_count": fact["blind_correct"],
            "formulaic_or_near_duplicate_union_ids": formula,
            "hard_error_union_codes": hard,
            "substantive_disagreement_blind_item_ids": sorted(disagreement_ids),
            "targeted_adjudication_digest": adjudication_digest,
            "common_acceptable_request_ids": common,
            "reviews_pass": reviews_pass,
        }
        if any(metrics.get(key) != value for key, value in expected.items()):
            add(errors, "E_T3_REVIEW_METRICS_RECOMPUTE")
        return metrics
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        add(errors, "E_T3_REVIEW_PARSE", str(exc))
        return None


def _validate_decision(root: Path, lifecycle: Mapping[str, Any], metrics: Mapping[str, Any], errors: list[dict[str, str]]) -> None:
    try:
        decision = json.loads((root / p4.QUALIFICATION_DECISION).read_text(encoding="utf-8"))
        if not isinstance(decision, dict) or decision.get("decision_digest") != p4.object_digest(decision, "decision_digest"):
            add(errors, "E_T3_DECISION_DIGEST")
            return
        manifest = json.loads((root / p4.CURATION_BUNDLE).read_text(encoding="utf-8"))["role_manifest"]
        coordinator = manifest["qualification_coordinator"]
        if (
            decision.get("decision_authority") != "EXTERNAL_INDEPENDENT_QUALIFICATION_COORDINATOR"
            or decision.get("coordinator_identity") != coordinator["identity"]
            or decision.get("coordinator_session_logical_id") != coordinator["session_logical_id"]
            or decision.get("coordinator_platform_agent_id") != coordinator["platform_agent_id"]
            or decision.get("review_metrics_digest") != metrics["metrics_digest"]
        ):
            add(errors, "E_T3_DECISION_BINDING")
        approved = list(map(str, decision.get("approved_first_output_request_ids", [])))
        if not set(approved).issubset(set(metrics["common_acceptable_request_ids"])):
            add(errors, "E_T3_DECISION_APPROVED_SCOPE")
        if lifecycle.get("lifecycle_state") == "PASS_TO_P5_POSITIVE_SCALE":
            if (
                decision.get("qualification_verdict") != "APPROVE"
                or decision.get("hard_veto") is not False
                or not isinstance(decision.get("qualification_score"), int)
                or decision["qualification_score"] < 90
                or len(approved) < 18
                or lifecycle.get("approved_first_output_request_ids") != approved
            ):
                add(errors, "E_T3_APPROVAL_GATE")
        elif (
            decision.get("qualification_verdict") != "REJECT"
            or approved
            or lifecycle.get("H") != 0
        ):
            add(errors, "E_T3_REJECTION_GATE")
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        add(errors, "E_T3_DECISION_PARSE", str(exc))


def validate_third_p4(root: Path = ROOT) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    _validate_tool_freeze(root, errors)
    _validate_history(root, errors)
    try:
        lifecycle = load_yaml(root / p4.LIFECYCLE).get("third_p4_lifecycle")
        if not isinstance(lifecycle, dict):
            raise TypeError("lifecycle root")
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        add(errors, "E_T3_LIFECYCLE_PARSE", str(exc))
        return errors
    _validate_lifecycle(lifecycle, errors)
    _validate_owner(root, lifecycle, errors)
    state = str(lifecycle.get("lifecycle_state"))
    hidden_paths = (p4.CURATION_BUNDLE, p4.ROLE_MANIFEST, p4.AUTHOR_REQUESTS, p4.ROUTE_INPUTS, p4.ROUTE_GOLD, p4.HIDDEN_FREEZE)
    if state == "TOOLS_FROZEN_PENDING_HIDDEN_CURATION":
        for path in hidden_paths:
            if (root / path).exists():
                add(errors, "E_T3_HIDDEN_TOO_EARLY", path.as_posix())
        return errors
    _validate_hidden(root, errors)
    if state == "HIDDEN_INPUTS_FROZEN":
        for path in (p4.RAW_OUTPUTS, p4.NORMALIZED_OUTPUTS, p4.ROUTE_ACTUALS, p4.CONTENT_REVIEW, p4.TARGETED_ADJUDICATION, p4.QUALIFICATION_DECISION):
            if (root / path).exists():
                add(errors, "E_T3_OUTPUT_TOO_EARLY", path.as_posix())
        return errors
    machine = _recompute_machine(root, errors)
    if machine is None:
        return errors
    if state == "STOPPED_RETURN_TO_P3":
        metrics = _validate_reviews(root, errors) if (root / p4.REVIEW_METRICS).is_file() else None
        if machine.get("technical_gate_pass") is True and metrics is not None and metrics.get("reviews_pass") is True:
            add(errors, "E_T3_FALSE_STOP")
        if (root / p4.QUALIFICATION_DECISION).exists():
            add(errors, "E_T3_DECISION_AFTER_PREDECISION_FAILURE")
        return errors
    if machine.get("technical_gate_pass") is not True:
        add(errors, "E_T3_FALSE_TECHNICAL_PASS")
        return errors
    metrics = _validate_reviews(root, errors)
    if metrics is None or metrics.get("reviews_pass") is not True:
        add(errors, "E_T3_FALSE_REVIEW_PASS")
        return errors
    if state == "PASS_PENDING_FOUNDER_QUALIFICATION_DECISION":
        if (root / p4.QUALIFICATION_DECISION).exists():
            add(errors, "E_T3_UNIMPORTED_DECISION_PRESENT")
        return errors
    if not (root / p4.QUALIFICATION_DECISION).is_file():
        add(errors, "E_T3_DECISION_REQUIRED")
        return errors
    _validate_decision(root, lifecycle, metrics, errors)
    for path in (p4.CHECKPOINT_RESULT, p4.DELIVERY_RECEIPT):
        if not (root / path).is_file():
            add(errors, "E_T3_FINAL_REQUIRED", path.as_posix())
    return errors


def selftest(root: Path = ROOT) -> int:
    baseline = validate_third_p4(root)
    if baseline:
        print(json.dumps({"status": "SELFTEST_SETUP_FAIL", "errors": baseline}, ensure_ascii=False))
        return 1
    failures: list[dict[str, str]] = []
    states = json.loads((root / p4.THIRD_CONTRACT).read_text(encoding="utf-8"))["lifecycle_states"]
    for state in states:
        approved = [f"P4T3-POS-CP{index:02d}" for index in range(1, 19)] if state == "PASS_TO_P5_POSITIVE_SCALE" else []
        record = p4.lifecycle_record(state, {}, approved)
        local_errors: list[dict[str, str]] = []
        _validate_lifecycle(record, local_errors)
        if local_errors:
            failures.append({"case": f"legal_state_{state}", "error": str(local_errors)})
    mutations = (
        ("H_flip", lambda value: value.__setitem__("H", 1)),
        ("p5_flip", lambda value: value.__setitem__("p5_allowed", True)),
        ("qualified_flip", lambda value: value.__setitem__("generator_qualified", True)),
        ("readiness_flip", lambda value: value["readiness"].__setitem__("generation_allowed", True)),
        ("core_number", lambda value: value.__setitem__("counted_positive_parent_count", 30)),
        ("external_count", lambda value: value.__setitem__("external_provider_request_count", 1)),
    )
    base = p4.lifecycle_record("TOOLS_FROZEN_PENDING_HIDDEN_CURATION")
    for name, mutate in mutations:
        changed = copy.deepcopy(base)
        mutate(changed)
        changed["lifecycle_digest"] = p4.object_digest(changed, "lifecycle_digest")
        local_errors = []
        _validate_lifecycle(changed, local_errors)
        if not local_errors:
            failures.append({"case": name, "error": "false negative"})
    freeze = load_yaml(root / p4.TOOL_FREEZE)["third_p4_tool_freeze"]
    changed_freeze = copy.deepcopy(freeze)
    changed_freeze["hidden_material_absent"] = False
    if changed_freeze.get("tool_freeze_digest") == p4.object_digest(changed_freeze, "tool_freeze_digest"):
        failures.append({"case": "tool_freeze_tamper", "error": "digest collision"})
    if failures:
        print(json.dumps({"status": "SELFTEST_FAIL", "failures": failures}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "SELFTEST_PASS", "negative_case_count": len(mutations) + 1, "six_state_count": len(states)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest(ROOT)
    errors = validate_third_p4(ROOT)
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, ensure_ascii=False))
        return 1
    lifecycle = load_yaml(ROOT / p4.LIFECYCLE)["third_p4_lifecycle"]
    print(json.dumps({"status": "PASS", "task_id": p4.TASK_ID, "state": lifecycle["lifecycle_state"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
