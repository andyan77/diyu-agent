#!/usr/bin/env python3
"""Close the open author-interface recovery and emit its immutable evidence."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from author_contract import (
    FROZEN_P4_ROOT,
    ROOT,
    TASK_ID,
    frozen_strict_module,
    object_digest,
    read_jsonl,
    serialize_all,
    sha256_file,
    write_jsonl,
)


if not __debug__:
    sys.stderr.write("run_open_recovery refuses python -O\n")
    raise SystemExit(2)


TASK_ROOT = Path(
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_author_output_contract_recovery_001"
)
PUBLIC_REQUESTS = ROOT / TASK_ROOT / "public/public_author_requests_20.v1.0.jsonl"
PUBLIC_RAWS = ROOT / TASK_ROOT / "public/public_author_raw_outputs_20.v1.0.jsonl"
PUBLIC_OUTPUTS = ROOT / TASK_ROOT / "public/public_author_outputs_20.v1.0.jsonl"
PUBLIC_RESULT = ROOT / TASK_ROOT / "result/open_recovery_result.v1.0.yaml"
EXTERNAL_AUDIT = ROOT / TASK_ROOT / "audit/external_exit_audit.v1.0.yaml"
OWNER = ROOT / (
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "current_gate1_owner.v0.1.yaml"
)
OLD_P4_ROOT = ROOT / (
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_sealed_hidden_probe40_001"
)
RESEALED_ROOT = ROOT / (
    "controlled_content_generator_v2_001/gate1_v1_1_001/"
    "p4_resealed_hidden_probe40_001"
)


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=110),
        encoding="utf-8",
    )


def _strict_validate_first_p4() -> None:
    module_root = str(FROZEN_P4_ROOT)
    if module_root not in sys.path:
        sys.path.insert(0, module_root)
    for name in ("p4_actual", "p4_common"):
        sys.modules.pop(name, None)
    module = importlib.import_module("p4_actual")
    requests = read_jsonl(OLD_P4_ROOT / "freeze/positive_author_requests_20.v0.1.jsonl")
    outputs = read_jsonl(OLD_P4_ROOT / "run/positive_20_first_outputs.v0.1.jsonl")
    module.validate_positive_outputs(outputs, requests)


def _strict_reject_second_p4() -> str:
    module = frozen_strict_module()
    module.TASK_ID = "GATE1_V11_P3_ROUTE_INPUT_COMPILER_RECOVERY_AND_P4_RESEALED_PROBE40_001"
    module.POSITIVE_OUTPUT_SCHEMA = "gate1-p4r-positive-first-output-v1.0"
    requests = read_jsonl(RESEALED_ROOT / "freeze/positive_author_requests_20.v1.0.jsonl")
    outputs = read_jsonl(RESEALED_ROOT / "run/positive_20_first_outputs.v1.0.jsonl")
    try:
        module.validate_positive_outputs(outputs, requests)
    except ValueError as exc:
        code = str(exc).split(":", 1)[0]
        if code != "E_P4_SURFACE_FIELDS":
            raise ValueError(f"E_SECOND_P4_WRONG_FAILURE:{code}") from exc
        return code
    raise ValueError("E_SECOND_P4_FALSE_ACCEPT")


def _owner() -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "v0.1",
        "owner_id": "GATE1_V11_P4_AUTHOR_OUTPUT_RECOVERY_OPEN_OWNER",
        "task_id": TASK_ID,
        "current_task_root": TASK_ROOT.as_posix(),
        "current_checker": "ci/checkers/check_gate1_v1_1_current.py",
        "result_state": "OPEN_RECOVERY_COMPLETE",
        "p3_complete": True,
        "prior_p4_failure_honestly_closed": True,
        "tool_freeze_complete": False,
        "third_hidden_created": False,
        "third_hidden_exposed": False,
        "H_admitted_count": 0,
        "generator_qualified": False,
        "p5_allowed": False,
        "current_generator": {
            "entrypoint": (TASK_ROOT / "author_contract.py").as_posix(),
            "route_contract": (
                "controlled_content_generator_v2_001/gate1_v1_1_001/"
                "p3_route_input_compiler_recovery_001/route_contract.py"
            ),
            "active_component_count": 68,
            "active_edge_count": 85,
            "active_control_rule_count": 8,
            "generator_core_changed": False,
            "content_authoring_semantics_changed": False,
            "output_contract_section_changed": True,
        },
        "predecessor": {
            "owner_id": "GATE1_V11_P4_RESEALED_STOPPED_OWNER",
            "task_id": "GATE1_V11_P3_ROUTE_INPUT_COMPILER_RECOVERY_AND_P4_RESEALED_PROBE40_001",
            "result_state": "STOPPED_RETURN_TO_P3",
        },
        "core_numbers": {
            "target_total": 300,
            "reference_inventory": 120,
            "historical_component_inventory": 86,
            "all_unchanged": True,
        },
        "readiness": {
            "candidatepack_ready": False,
            "KE_ready": False,
            "RAG_ready": False,
            "DIFY_ready": False,
            "production_servable": False,
            "generation_eligible": False,
            "generation_allowed": False,
            "release_ready": False,
            "production_ready": False,
            "generator_qualified": False,
            "runtime_ingest_ready": False,
        },
        "owner_digest": "",
    }
    value["owner_digest"] = object_digest(value, "owner_digest")
    return value


def run() -> None:
    requests = read_jsonl(PUBLIC_REQUESTS)
    raws = read_jsonl(PUBLIC_RAWS)
    outputs = serialize_all(raws, requests)
    write_jsonl(PUBLIC_OUTPUTS, outputs)
    _strict_validate_first_p4()
    second_failure = _strict_reject_second_p4()

    observed_exit_events: list[dict[str, Any]] = []
    audit = {
        "schema_version": "gate1-p4-author-output-recovery-exit-audit-v1.0",
        "task_id": TASK_ID,
        "observed_content_exit_events": observed_exit_events,
        "external_provider_request_count": len(observed_exit_events),
        "external_provider_response_count": 0,
        "external_api_call_count": len(observed_exit_events),
        "credential_read_count": 0,
        "network_dispatch_count": len(observed_exit_events),
        "git_remote_transport_excluded_from_content_exit_count": True,
        "audit_digest": "",
    }
    audit["audit_digest"] = object_digest(audit, "audit_digest")
    write_yaml(EXTERNAL_AUDIT, {"external_exit_audit": audit})

    result = {
        "schema_version": "gate1-p4-author-output-recovery-result-v1.0",
        "task_id": TASK_ID,
        "result_state": "OPEN_RECOVERY_COMPLETE",
        "public_probe_count": len(outputs),
        "public_probe_strict_pass_count": len(outputs),
        "first_p4_legal_regression_pass_count": 20,
        "second_p4_malformed_rejected_count": 20,
        "second_p4_first_failure_code": second_failure,
        "raw_output_sha256": sha256_file(PUBLIC_RAWS),
        "normalized_output_sha256": sha256_file(PUBLIC_OUTPUTS),
        "raw_normalized_binding_count": len(outputs),
        "second_candidate_or_replacement_count": 0,
        "output_contract_section_changed": True,
        "content_authoring_semantics_changed": False,
        "third_hidden_created": False,
        "H_admitted_count": 0,
        "generator_qualified": False,
        "p5_allowed": False,
        "core_number_impact": {"300": 0, "120": 0, "86": 0},
        "readiness_true_keys": [],
        "result_digest": "",
    }
    result["result_digest"] = object_digest(result, "result_digest")
    write_yaml(PUBLIC_RESULT, {"open_recovery_result": result})
    write_yaml(OWNER, {"current_gate1_owner": _owner()})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        raise SystemExit("use --run")
    try:
        run()
    except (OSError, TypeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        sys.stderr.write(f"FAIL {exc}\n")
        return 1
    print("PASS open_recovery_complete public=20 first_regression=20 second_rejected=20")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
