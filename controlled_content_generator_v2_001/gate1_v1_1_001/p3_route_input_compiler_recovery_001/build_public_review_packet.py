#!/usr/bin/env python3
"""Build the open P3 recovery materials that independent reviewers will sign."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from route_contract import (
    CONTRACT_VERSION,
    ROOT,
    TASK_ID,
    TASK_ROOT,
    jsonl_bytes,
    object_digest,
    profile_rows,
    required_slots,
    sha256_bytes,
    sha256_file,
)


if not __debug__:
    sys.stderr.write("build_public_review_packet refuses python -O\n")
    raise SystemExit(2)


PUBLIC_INPUTS = TASK_ROOT / "public/open_route_inputs_20.v1.0.jsonl"
PROPOSED_GOLD = TASK_ROOT / "review/open_route_gold_proposed_20.v1.0.jsonl"
REVIEW_PACKET = TASK_ROOT / "review/open_route_review_packet.v1.0.yaml"
CONTRACT_DOC = TASK_ROOT / "contract/canonical_route_input_contract.v1.0.yaml"


def _provided_item(case_id: str, slot_id: str) -> dict[str, str]:
    value_ref = f"synthetic://p3-route-recovery/{case_id}/{slot_id}"
    return {
        "slot_id": slot_id,
        "value_ref": value_ref,
        "value_digest": sha256_bytes(value_ref.encode("utf-8")),
    }


def _case_policy(index: int, profile: dict[str, Any]) -> dict[str, Any]:
    if index <= 3:
        guard = str(profile["anti_pattern_rule_refs"][0])
        return {"kind": "BLOCK_GUARD", "guard": guard}
    if index <= 5:
        return {"kind": "BLOCK_AUTH", "risk": "ROLE_AUTHORITY_EXPANSION"}
    if index <= 7:
        return {"kind": "BLOCK_FACT", "risk": "FABRICATED_EVENT"}
    if index <= 13:
        slot_class = ("authorization", "fact", "source")[(index - 8) % 3]
        return {"kind": "REQUEST", "slot_class": slot_class}
    slot_class = ("authorization", "fact", "source")[(index - 14) % 3]
    return {"kind": "DEGRADE", "slot_class": slot_class}


def _allowed_output(profile: dict[str, Any], slot_class: str) -> str:
    route_id = f"required_{slot_class}_missing"
    for route in profile["input_sufficiency_routes"]:
        if route["route_id"] == route_id:
            return str(route["allowed_outputs"][0])
    raise ValueError(route_id)


def build_rows(root: Path = ROOT) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inputs: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    for index, profile in enumerate(profile_rows(root), 1):
        profile_id = str(profile["content_product_type_id"])
        policy = _case_policy(index, profile)
        case_id = f"P3R-OPEN-{profile_id}-{index:02d}"
        required = required_slots(profile)
        missing = {slot_class: [] for slot_class in ("source", "fact", "authorization")}
        risks: list[str] = []
        guards: list[str] = []
        degrade = {"enabled": False, "artifact_type": "", "payload": {}}
        action = "BLOCK"
        reason = "输入冲突"
        if policy["kind"] == "BLOCK_GUARD":
            guards = [policy["guard"]]
        elif policy["kind"] == "BLOCK_AUTH":
            risks = [policy["risk"]]
            reason = "授权缺失"
        elif policy["kind"] == "BLOCK_FACT":
            risks = [policy["risk"]]
            reason = "事实缺失"
        else:
            slot_class = str(policy["slot_class"])
            missing[slot_class] = [required[slot_class][0]]
            reason = "授权缺失" if slot_class == "authorization" else "事实缺失"
            if policy["kind"] == "REQUEST":
                action = "REQUEST_INPUT"
            else:
                action = "DEGRADE"
                artifact_type = _allowed_output(profile, slot_class)
                degrade = {
                    "enabled": True,
                    "artifact_type": artifact_type,
                    "payload": {
                        "artifact_purpose": f"collect_{profile_id.lower()}_{slot_class}_gap",
                        "items": [
                            f"Collect the declared missing {slot_class} slot before any audience-facing output."
                        ],
                    },
                }
        provided = {
            slot_class: [
                _provided_item(case_id, slot_id)
                for slot_id in required[slot_class]
                if slot_id not in missing[slot_class]
            ]
            for slot_class in ("source", "fact", "authorization")
        }
        record: dict[str, Any] = {
            "schema_version": CONTRACT_VERSION,
            "task_id": TASK_ID,
            "case_id": case_id,
            "profile_id": profile_id,
            "provided": provided,
            "missing": missing,
            "risk_codes": risks,
            "hard_guard_hits": guards,
            "degrade_request": degrade,
            "provenance": {
                "source_kind": "SYNTHETIC_OPEN_DEVELOPMENT",
                "record_refs": [
                    f"profile://{profile_id}/input_requirements",
                    f"profile://{profile_id}/input_sufficiency_routes",
                ],
            },
            "input_digest": "",
        }
        record["input_digest"] = object_digest(record, "input_digest")
        inputs.append(record)
        gold_row = {
            "schema_version": "gate1-open-route-gold-v1.0",
            "task_id": TASK_ID,
            "case_id": case_id,
            "profile_id": profile_id,
            "gold_primary_action": action,
            "gold_primary_reason_category": reason,
            "bound_input_digest": record["input_digest"],
            "gold_digest": "",
        }
        gold_row["gold_digest"] = object_digest(gold_row, "gold_digest")
        gold.append(gold_row)
    return inputs, gold


def expected_files(root: Path = ROOT) -> dict[Path, bytes]:
    inputs, gold = build_rows(root)
    contract = {
        "schema_version": CONTRACT_VERSION,
        "task_id": TASK_ID,
        "one_contract": True,
        "one_compiler_entrypoint": "route_contract.compile_route_input",
        "slot_classes": ["source", "fact", "authorization"],
        "explicit_state_required": True,
        "unknown_fields_fail_closed": True,
        "gold_or_expected_fields_forbidden": True,
        "audience_content_allowed": False,
        "contract_digest": "",
    }
    contract["contract_digest"] = object_digest(contract, "contract_digest")
    packet = {
        "schema_version": "gate1-open-route-review-packet-v1.0",
        "task_id": TASK_ID,
        "review_stage": "PRE_IMPLEMENTATION_GOLD_REVIEW",
        "input_count": 20,
        "gold_count": 20,
        "profile_coverage": [f"CP{index:02d}" for index in range(1, 21)],
        "allowed_actions": ["BLOCK", "REQUEST_INPUT", "DEGRADE"],
        "allowed_reasons": ["输入冲突", "事实缺失", "授权缺失"],
        "reviewers_must_not_read": [
            "route_contract.py",
            "compiler_actuals",
            "other_reviewer_report",
        ],
        "input_sha256": sha256_bytes(jsonl_bytes(inputs)),
        "proposed_gold_sha256": sha256_bytes(jsonl_bytes(gold)),
        "packet_digest": "",
    }
    packet["packet_digest"] = object_digest(packet, "packet_digest")
    return {
        PUBLIC_INPUTS: jsonl_bytes(inputs),
        PROPOSED_GOLD: jsonl_bytes(gold),
        CONTRACT_DOC: yaml.safe_dump(contract, allow_unicode=True, sort_keys=False).encode("utf-8"),
        REVIEW_PACKET: yaml.safe_dump(packet, allow_unicode=True, sort_keys=False).encode("utf-8"),
    }


def materialize(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    for relative_path, payload in expected_files(root).items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        paths.append(path)
    return paths


def check(root: Path = ROOT) -> int:
    errors: list[str] = []
    for relative_path, payload in expected_files(root).items():
        path = root / relative_path
        if not path.is_file() or path.read_bytes() != payload:
            errors.append(relative_path.as_posix())
    if errors:
        print(json.dumps({"status": "FAIL", "drift": errors}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "input_count": 20,
                "gold_count": 20,
                "input_sha256": sha256_file(root / PUBLIC_INPUTS),
                "gold_sha256": sha256_file(root / PROPOSED_GOLD),
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("materialize", "check"))
    args = parser.parse_args()
    if args.command == "materialize":
        paths = materialize(ROOT)
        print(json.dumps({"status": "MATERIALIZED", "paths": [str(path) for path in paths]}))
        return 0
    return check(ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
