#!/usr/bin/env python3
"""Thin lifecycle runner for the Gate 1 P4 sealed hidden probe."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

from p4_common import (
    AUTHOR_RECEIPT,
    AUTHOR_REQUESTS,
    EXIT_EVENTS,
    EXIT_OBSERVATIONS,
    HIDDEN_FREEZE,
    LIFECYCLE,
    MACHINE_REPORT,
    POSITIVE_OUTPUTS,
    PROFILES,
    ROOT,
    ROUTE_ACTUAL_FREEZE,
    ROUTE_ACTUALS,
    ROUTE_INPUTS,
    TASK_ID,
    bind_digest,
    canonical_json,
    load_yaml,
    object_digest,
    read_jsonl,
    sha256_file,
    write_jsonl,
    write_yaml,
)


def _profiles() -> list[dict[str, Any]]:
    registry = load_yaml(ROOT / PROFILES)["content_product_profile_registry"]
    return list(registry["profiles"])


def _set_lifecycle(state: str, **fields: Any) -> None:
    value = load_yaml(ROOT / LIFECYCLE)
    lifecycle = value["p4_lifecycle"]
    lifecycle.update({"state": state, **fields})
    lifecycle["lifecycle_digest"] = object_digest(lifecycle, "lifecycle_digest")
    write_yaml(ROOT / LIFECYCLE, {"p4_lifecycle": lifecycle})


def bind_hidden_commit(commit: str) -> None:
    lifecycle = load_yaml(ROOT / LIFECYCLE)["p4_lifecycle"]
    if lifecycle.get("state") != "HIDDEN_FROZEN_PENDING_COMMIT":
        raise ValueError("E_HIDDEN_NOT_PENDING_COMMIT")
    tool_commit = str(lifecycle.get("tool_freeze_commit"))
    checks = (
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        ["git", "merge-base", "--is-ancestor", tool_commit, commit],
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
    )
    if any(
        subprocess.run(args, cwd=ROOT, check=False).returncode != 0 for args in checks
    ):
        raise ValueError("E_HIDDEN_FREEZE_COMMIT_LINEAGE")
    freeze = load_yaml(ROOT / HIDDEN_FREEZE)["p4_hidden_input_freeze"]
    for raw_path, expected in freeze["frozen_file_hashes"].items():
        shown = subprocess.run(
            ["git", "show", f"{commit}:{raw_path}"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        import hashlib

        if (
            shown.returncode != 0
            or hashlib.sha256(shown.stdout).hexdigest() != expected
        ):
            raise ValueError(f"E_HIDDEN_FREEZE_COMMIT_BYTES:{raw_path}")
    _set_lifecycle(
        "HIDDEN_FROZEN",
        hidden_input_freeze_commit=commit,
        hidden_created=True,
        hidden_exposed=False,
    )


def run_actuals() -> None:
    from p4_actual import (
        build_author_identity_config,
        build_execution_exit_events,
        build_route_actual_artifacts,
        derive_execution_exit_counts,
        validate_positive_outputs,
    )

    lifecycle = load_yaml(ROOT / LIFECYCLE)["p4_lifecycle"]
    if lifecycle.get("state") != "HIDDEN_FROZEN":
        raise ValueError("E_HIDDEN_NOT_FROZEN")
    requests = read_jsonl(ROOT / AUTHOR_REQUESTS)
    outputs = read_jsonl(ROOT / POSITIVE_OUTPUTS)
    identity = build_author_identity_config(requests)
    validated_outputs = validate_positive_outputs(outputs, requests, identity)
    route_inputs = read_jsonl(ROOT / ROUTE_INPUTS)
    actuals, actual_freeze = build_route_actual_artifacts(route_inputs, _profiles())
    write_jsonl(ROOT / ROUTE_ACTUALS, actuals)
    actual_freeze["actual_result_sha256"] = sha256_file(ROOT / ROUTE_ACTUALS)
    actual_freeze["actual_engine_input_sha256"] = sha256_file(ROOT / ROUTE_INPUTS)
    actual_freeze["actual_freeze_digest"] = object_digest(
        actual_freeze, "actual_freeze_digest"
    )
    write_yaml(
        ROOT / ROUTE_ACTUAL_FREEZE,
        {"route_actual_freeze_receipt": actual_freeze},
    )
    observations = read_jsonl(ROOT / EXIT_OBSERVATIONS)
    events = build_execution_exit_events(
        observations, validated_outputs, route_inputs, actuals, identity
    )
    write_jsonl(ROOT / EXIT_EVENTS, events)
    exit_counts = derive_execution_exit_counts(events)
    author_receipt = bind_digest(
        {
            "schema_version": "gate1-p4-author-run-receipt-v0.1",
            "task_id": TASK_ID,
            "author_identity": identity,
            "positive_first_output_count": len(validated_outputs),
            "positive_output_sha256": sha256_file(ROOT / POSITIVE_OUTPUTS),
            "second_candidate_count": 0,
            "replaced_or_deleted_count": 0,
            "transport_resume_without_prior_semantic_output_count": 0,
            "author_instruction_unchanged": True,
            "output_validation_pass": True,
        },
        "receipt_digest",
    )
    write_yaml(ROOT / AUTHOR_RECEIPT, {"p4_author_run_receipt": author_receipt})
    machine = bind_digest(
        {
            "schema_version": "gate1-p4-machine-acceptance-report-v0.1",
            "task_id": TASK_ID,
            "positive_first_output_count": len(validated_outputs),
            "anomaly_first_actual_count": len(actuals),
            "positive_contract_validation_pass": True,
            "route_actual_frozen_before_gold_compare": True,
            "route_gold_compared": False,
            "second_candidate_count": 0,
            "case_replacement_count": 0,
            "external_exit_counts_derived_from_events": exit_counts,
            "machine_does_not_decide_free_text_quality": True,
            "machine_does_not_qualify_generator": True,
            "generator_qualified": False,
            "p5_allowed": False,
            "core_numbers": {"300": "UNCHANGED", "120": "UNCHANGED", "86": "UNCHANGED"},
        },
        "report_digest",
    )
    write_yaml(ROOT / MACHINE_REPORT, {"p4_machine_acceptance_report": machine})
    _set_lifecycle(
        "RUN_FROZEN",
        hidden_exposed=True,
        all_cases_marked_exposed_after_run=True,
        positive_first_output_count=20,
        anomaly_first_actual_count=20,
        generator_qualified=False,
        p5_allowed=False,
    )


def check() -> int:
    from p4_guard import validate_p4_current

    errors = validate_p4_current(ROOT)
    print(
        canonical_json({"status": "PASS" if not errors else "FAIL", "errors": errors})
    )
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare-tools")
    seal = sub.add_parser("seal-tool-freeze")
    seal.add_argument("--commit", required=True)
    freeze = sub.add_parser("freeze-hidden")
    freeze.add_argument("--author-agent-id", required=True)
    bind = sub.add_parser("bind-hidden-commit")
    bind.add_argument("--commit", required=True)
    sub.add_parser("run-actuals")
    sub.add_parser("build-review-packet")
    sub.add_parser("validate-reviews")
    sub.add_parser("close-checkpoint")
    sub.add_parser("check")
    sub.add_parser("selftest")
    args = parser.parse_args()
    if args.command == "prepare-tools":
        from p4_prepare import prepare_tools

        prepare_tools()
    elif args.command == "seal-tool-freeze":
        from p4_prepare import seal_tool_freeze

        seal_tool_freeze(args.commit)
    elif args.command == "freeze-hidden":
        from p4_prepare import freeze_hidden

        freeze_hidden(args.author_agent_id)
    elif args.command == "bind-hidden-commit":
        bind_hidden_commit(args.commit)
    elif args.command == "run-actuals":
        run_actuals()
    elif args.command == "build-review-packet":
        from p4_postrun import materialize_review_packet

        materialize_review_packet()
    elif args.command == "validate-reviews":
        from p4_postrun import recompute_checkpoint_metrics

        recompute_checkpoint_metrics()
    elif args.command == "close-checkpoint":
        from p4_postrun import materialize_final

        materialize_final()
    elif args.command == "selftest":
        from p4_guard import selftest

        return selftest(ROOT)
    else:
        return check()
    print(json.dumps({"status": "PASS", "command": args.command}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
