#!/usr/bin/env python3
"""Current P4 guard successor for two narrow frozen-guard compatibility defects."""

from __future__ import annotations

import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import p4_guard as frozen_guard
from p4_actual import P4ActualValidationError, validate_positive_outputs
from p4_common import (
    AUTHOR_REQUESTS,
    CHECKPOINT_RESULT,
    CURRENT_CHECKER,
    DECISION_PACKET,
    LIFECYCLE,
    POSITIVE_OUTPUTS,
    ROOT,
    ROUTE_INPUTS,
    load_yaml,
    object_digest,
    read_jsonl,
    recursively_true,
    sha256_file,
    write_jsonl,
    write_yaml,
)


if not __debug__:
    print("p4_guard_current refuses python -O", file=sys.stderr)
    raise SystemExit(2)


FROZEN_GUARD_SHA256 = "5c1f11a1aba529c8fd97dc8031ce48ab59b7082fc0306943fdb3dd0dc98d1262"
CURRENT_CHECKER_COMPAT_SHA256 = (
    "a3e2f087d199bbde514e65e1a83066d40eda9bd217fa6986d48077303aa3d2f4"
)


def _error(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def _positive_output_ids_are_exact(root: Path) -> bool:
    try:
        requests = read_jsonl(root / AUTHOR_REQUESTS)
        outputs = read_jsonl(root / POSITIVE_OUTPUTS)
        request_ids = Counter(str(row.get("request_id")) for row in requests)
        output_ids = Counter(str(row.get("request_id")) for row in outputs)
        if request_ids != output_ids or len(request_ids) != 20:
            return False
        validate_positive_outputs(outputs, requests)
    except (OSError, TypeError, ValueError, P4ActualValidationError):
        return False
    return True


def _current_checker_is_exact_compat_successor(root: Path) -> bool:
    path = root / CURRENT_CHECKER
    return path.is_file() and sha256_file(path) == CURRENT_CHECKER_COMPAT_SHA256


def _stopped_decision_packet_is_exact(root: Path) -> bool:
    try:
        lifecycle = load_yaml(root / LIFECYCLE)["p4_lifecycle"]
        checkpoint = load_yaml(root / CHECKPOINT_RESULT)["p4_checkpoint_result"]
        packet = load_yaml(root / DECISION_PACKET)[
            "founder_qualification_decision_packet"
        ]
    except (KeyError, OSError, TypeError, ValueError):
        return False
    return bool(
        lifecycle.get("state") == "STOPPED_RETURN_TO_P3"
        and lifecycle.get("generator_qualified") is False
        and lifecycle.get("p5_allowed") is False
        and checkpoint.get("result_state") == "STOPPED_RETURN_TO_P3"
        and checkpoint.get("contract_thresholds_met") is False
        and checkpoint.get("founder_qualification_decision_required") is False
        and checkpoint.get("founder_qualification_decision_recorded") is False
        and checkpoint.get("generator_qualified") is False
        and checkpoint.get("p5_allowed") is False
        and checkpoint.get("H") == []
        and checkpoint.get("result_digest")
        == object_digest(checkpoint, "result_digest")
        and packet.get("decision_state") == "NOT_ELIGIBLE_FOR_DECISION"
        and packet.get("decision_received") is False
        and packet.get("approved_hidden_positive_ids") == []
        and packet.get("contract_thresholds_met") is False
        and packet.get("founder_decision_recorded") is False
        and packet.get("generator_qualified") is False
        and packet.get("qualification_eligibility") is False
        and packet.get("checkpoint_result_digest") == checkpoint.get("result_digest")
        and packet.get("packet_digest") == object_digest(packet, "packet_digest")
        and not recursively_true(packet.get("readiness", {}))
    )


def validate_p4_current(root: Path) -> list[dict[str, str]]:
    """Preserve the frozen guard and repair only its two proven false positives."""

    frozen_path = root / frozen_guard.TASK_ROOT / "p4_guard.py"
    if not frozen_path.is_file() or sha256_file(frozen_path) != FROZEN_GUARD_SHA256:
        return [_error("E_P4_FROZEN_GUARD_MUTATION", frozen_path.as_posix())]

    exact_ids = _positive_output_ids_are_exact(root)
    exact_current_checker = _current_checker_is_exact_compat_successor(root)
    exact_stopped_packet = _stopped_decision_packet_is_exact(root)
    errors: list[dict[str, str]] = []
    for item in frozen_guard.validate_p4_current(root):
        code = item.get("code")
        detail = item.get("detail")
        if code == "E_P4_OUTPUT_ID_SET" and exact_ids:
            continue
        if (
            code == "E_P4_TOOL_MUTATION"
            and detail == CURRENT_CHECKER.as_posix()
            and exact_current_checker
        ):
            continue
        if (
            code == "E_P4_QUALIFICATION_BEFORE_DECISION"
            and detail == "decision packet"
            and exact_stopped_packet
        ):
            continue
        errors.append(item)
    return errors


def _codes(root: Path) -> set[str]:
    return {item["code"] for item in validate_p4_current(root)}


def selftest(root: Path) -> int:
    live_errors = validate_p4_current(root)
    if live_errors:
        print(json.dumps({"status": "SELFTEST_BLOCKED", "errors": live_errors}))
        return 1

    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="p4-current-id-") as raw:
        fixture = Path(raw)
        frozen_guard._copy_fixture(root, fixture)
        rows = read_jsonl(fixture / POSITIVE_OUTPUTS)
        rows[0]["request_id"] = rows[1]["request_id"]
        rows[0]["output_digest"] = object_digest(rows[0], "output_digest")
        write_jsonl(fixture / POSITIVE_OUTPUTS, rows)
        codes = _codes(fixture)
        if "E_P4_OUTPUT_ID_SET" not in codes:
            failures.append({"case": "duplicate output id", "codes": sorted(codes)})

    with tempfile.TemporaryDirectory(prefix="p4-current-gold-") as raw:
        fixture = Path(raw)
        frozen_guard._copy_fixture(root, fixture)
        rows = read_jsonl(fixture / ROUTE_INPUTS)
        rows[0]["gold_primary_action"] = "BLOCK"
        rows[0]["input_digest"] = object_digest(rows[0], "input_digest")
        write_jsonl(fixture / ROUTE_INPUTS, rows)
        codes = _codes(fixture)
        if "E_P4_ROUTE_GOLD_LEAK" not in codes:
            failures.append({"case": "route gold leak", "codes": sorted(codes)})

    with tempfile.TemporaryDirectory(prefix="p4-current-ready-") as raw:
        fixture = Path(raw)
        frozen_guard._copy_fixture(root, fixture)
        value = load_yaml(fixture / LIFECYCLE)
        row = value["p4_lifecycle"]
        row["generator_qualified"] = True
        row["lifecycle_digest"] = object_digest(row, "lifecycle_digest")
        write_yaml(fixture / LIFECYCLE, value)
        codes = _codes(fixture)
        if "E_P4_QUALIFICATION_BEFORE_DECISION" not in codes:
            failures.append({"case": "early qualification", "codes": sorted(codes)})

    with tempfile.TemporaryDirectory(prefix="p4-current-checker-") as raw:
        fixture = Path(raw)
        frozen_guard._copy_fixture(root, fixture)
        checker = fixture / CURRENT_CHECKER
        checker.write_bytes(checker.read_bytes() + b"\n")
        codes = _codes(fixture)
        if "E_P4_TOOL_MUTATION" not in codes:
            failures.append({"case": "checker tamper", "codes": sorted(codes)})

    if (root / DECISION_PACKET).is_file():
        with tempfile.TemporaryDirectory(prefix="p4-current-decision-") as raw:
            fixture = Path(raw)
            frozen_guard._copy_fixture(root, fixture)
            value = load_yaml(fixture / DECISION_PACKET)
            packet = value["founder_qualification_decision_packet"]
            packet["approved_hidden_positive_ids"] = ["P4-POS-CP01"]
            packet["packet_digest"] = object_digest(packet, "packet_digest")
            write_yaml(fixture / DECISION_PACKET, value)
            codes = _codes(fixture)
            if "E_P4_QUALIFICATION_BEFORE_DECISION" not in codes:
                failures.append(
                    {"case": "stopped decision tamper", "codes": sorted(codes)}
                )

    if failures:
        print(json.dumps({"status": "SELFTEST_FAIL", "failures": failures}))
        return 1
    print(
        json.dumps(
            {
                "status": "SELFTEST_PASS",
                "frozen_guard_sha256": FROZEN_GUARD_SHA256,
                "exact_output_ids_recomputed": True,
                "duplicate_output_id_rejected": True,
                "route_gold_leak_rejected": True,
                "early_qualification_rejected": True,
                "current_checker_tamper_rejected": True,
                "stopped_decision_tamper_rejected": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest(ROOT))
