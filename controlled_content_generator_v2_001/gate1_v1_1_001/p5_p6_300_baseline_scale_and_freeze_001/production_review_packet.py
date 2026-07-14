#!/usr/bin/env python3
"""Build and verify the neutral production content-review packet."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


if not __debug__:
    sys.stderr.write("production_review_packet refuses python -O\n")
    raise SystemExit(2)


SCRIPT_PATH = Path(__file__).resolve()


def _load_base() -> ModuleType:
    path = SCRIPT_PATH.with_name("p5_p6_baseline.py")
    spec = importlib.util.spec_from_file_location("gate1_review_packet_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("E_REVIEW_PACKET_BASE_IMPORT")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load_base()
ROOT: Path = BASE.ROOT
TASK_ID: str = BASE.TASK_ID
TASK_ROOT: Path = BASE.TASK_ROOT
BLIND_ROOT = TASK_ROOT / "review/production/blind"
PACKET = BLIND_ROOT / "neutral_packet.v1.0.jsonl"
MAPPING = BLIND_ROOT / "neutral_mapping.v1.0.jsonl"
FREEZE = BLIND_ROOT / "neutral_packet_freeze.v1.0.yaml"
GROUP_COUNT = 4


def _neutral_id(output_digest: str) -> str:
    token = hashlib.sha256(
        f"gate1-production-blind-v1:{output_digest}".encode("utf-8")
    ).hexdigest()[:16]
    return f"G1-PROD-NEUTRAL-{token}"


def _rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    outputs = BASE.read_jsonl(ROOT / BASE.FIRST_OUTPUTS)
    ordered = sorted(
        outputs,
        key=lambda row: hashlib.sha256(
            f"gate1-production-order-v1:{row['output_digest']}".encode("utf-8")
        ).hexdigest(),
    )
    packet_rows = []
    mapping_rows = []
    for index, output in enumerate(ordered):
        blind_id = _neutral_id(str(output["output_digest"]))
        group_id = f"GROUP-{index % GROUP_COUNT + 1:02d}"
        packet = {
            "schema_version": "gate1-v1.1-production-neutral-item-v1.0",
            "task_id": TASK_ID,
            "blind_item_id": blind_id,
            "review_group_id": group_id,
            "title": output["title"],
            "body": output["body"],
            "spoken_lines": output["spoken_lines"],
            "cta": output["cta"],
            "visual_execution": output["visual_execution"],
            "audio_execution": output["audio_execution"],
            "synthetic_disclosure": output["synthetic_disclosure"],
            "packet_item_digest": "",
        }
        packet["packet_item_digest"] = BASE.object_digest(packet, "packet_item_digest")
        mapping = {
            "schema_version": "gate1-v1.1-production-neutral-mapping-v1.0",
            "task_id": TASK_ID,
            "blind_item_id": blind_id,
            "review_group_id": group_id,
            "request_id": output["request_id"],
            "profile_id": output["profile_id"],
            "output_digest": output["output_digest"],
            "mapping_digest": "",
        }
        mapping["mapping_digest"] = BASE.object_digest(mapping, "mapping_digest")
        packet_rows.append(packet)
        mapping_rows.append(mapping)
    BASE.require(
        len(packet_rows) == len(mapping_rows) == len(outputs),
        "E_REVIEW_PACKET_COUNT",
    )
    BASE.require(
        len({row["blind_item_id"] for row in packet_rows}) == len(packet_rows),
        "E_REVIEW_PACKET_ID_DUPLICATE",
    )
    serialized = "\n".join(BASE.canonical_json(row) for row in packet_rows)
    BASE.require(
        BASE.AUDIENCE_INTERNAL_ID_RE.search(serialized) is None,
        "E_REVIEW_PACKET_LABEL_LEAK",
    )
    return packet_rows, mapping_rows


def materialize() -> None:
    packet_rows, mapping_rows = _rows()
    BASE.write_jsonl(ROOT / PACKET, packet_rows)
    BASE.write_jsonl(ROOT / MAPPING, mapping_rows)
    for group_number in range(1, GROUP_COUNT + 1):
        group_id = f"GROUP-{group_number:02d}"
        BASE.write_jsonl(
            ROOT / BLIND_ROOT / f"neutral_packet.group_{group_number:02d}.v1.0.jsonl",
            [row for row in packet_rows if row["review_group_id"] == group_id],
        )
    freeze = {
        "schema_version": "gate1-v1.1-production-neutral-packet-freeze-v1.0",
        "task_id": TASK_ID,
        "source_first_outputs_sha256": BASE.sha256_file(ROOT / BASE.FIRST_OUTPUTS),
        "packet_sha256": BASE.sha256_file(ROOT / PACKET),
        "mapping_sha256": BASE.sha256_file(ROOT / MAPPING),
        "packet_count": len(packet_rows),
        "mapping_count": len(mapping_rows),
        "group_counts": {
            f"GROUP-{number:02d}": sum(
                row["review_group_id"] == f"GROUP-{number:02d}" for row in packet_rows
            )
            for number in range(1, GROUP_COUNT + 1)
        },
        "profile_or_request_mapping_present_in_packet": False,
        "author_or_review_judgment_present_in_packet": False,
        "materializer_sha256": BASE.sha256_file(SCRIPT_PATH),
        "freeze_digest": "",
    }
    freeze["freeze_digest"] = BASE.object_digest(freeze, "freeze_digest")
    BASE.write_yaml(ROOT / FREEZE, freeze)


def check() -> None:
    packet_rows, mapping_rows = _rows()
    BASE.require(
        BASE.canonical_json(packet_rows)
        == BASE.canonical_json(BASE.read_jsonl(ROOT / PACKET)),
        "E_REVIEW_PACKET_NONDETERMINISTIC",
    )
    BASE.require(
        BASE.canonical_json(mapping_rows)
        == BASE.canonical_json(BASE.read_jsonl(ROOT / MAPPING)),
        "E_REVIEW_MAPPING_NONDETERMINISTIC",
    )
    freeze = BASE.read_yaml(ROOT / FREEZE)
    BASE.require(
        freeze.get("materializer_sha256") == BASE.sha256_file(SCRIPT_PATH)
        and freeze.get("packet_sha256") == BASE.sha256_file(ROOT / PACKET)
        and freeze.get("mapping_sha256") == BASE.sha256_file(ROOT / MAPPING),
        "E_REVIEW_PACKET_FREEZE",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("materialize", "check"))
    args = parser.parse_args()
    if args.command == "materialize":
        materialize()
    else:
        check()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BASE.BaselineError as error:
        sys.stderr.write(f"{error}\n")
        raise SystemExit(1) from error
