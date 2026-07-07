#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_SOURCE_PACK_FIELDS = (
    "source_pack_id",
    "source_pack_type",
    "source_title",
    "source_owner",
    "source_license_or_usage_status",
    "source_scope",
    "source_file_ref",
    "source_digest",
    "allowed_usage",
    "ingestion_status",
)

REQUIRED_SOURCE_EXCERPT_FIELDS = (
    "source_excerpt_id",
    "source_pack_id",
    "section_ref",
    "excerpt_text",
    "excerpt_digest",
    "usable_for_general_kb",
    "hard_claim_present",
)

REQUIRED_LOCK_FIELDS = (
    "batch_id",
    "micro_batch_id",
    "source_pack_refs",
    "target_raw_count",
    "target_aligned_count",
    "allowed_output_files",
    "expected_checker_set",
    "run_status",
)


@dataclass(frozen=True)
class PilotReadiness:
    source_pack_surface: str
    real_source_pack_content: str
    source_pack_registry_rows: int
    source_excerpt_rows: int
    source_digest_rows: int
    source_pack_content_errors: list[str]
    batch_lockfile_status: dict[str, str]
    checker_real_content_status: str
    non_git_policy: dict[str, list[str]]
    next_allowed_mode: str
    blockers: list[str]
    readiness_flags: dict[str, bool]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Batch 000/001 pilot readiness without generating knowledge.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--report-md", type=Path)
    parser.add_argument("--fail-if-blocked", action="store_true")
    return parser.parse_args()


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def missing_fields(row: dict[str, str], required: tuple[str, ...]) -> list[str]:
    return [field for field in required if not (row.get(field) or "").strip()]


def audit_source_packs(workspace: Path) -> tuple[str, str, int, int, int, list[str]]:
    source_dir = workspace / "01_source_packs"
    required_files = [
        source_dir / "source_pack_manifest.yaml",
        source_dir / "source_pack_registry.csv",
        source_dir / "source_excerpt_ledger.csv",
        source_dir / "source_digest_ledger.csv",
    ]
    surface = "ready" if all(path.exists() for path in required_files) else "missing"
    pack_rows = load_csv(source_dir / "source_pack_registry.csv")
    excerpt_rows = load_csv(source_dir / "source_excerpt_ledger.csv")
    digest_rows = load_csv(source_dir / "source_digest_ledger.csv")
    errors: list[str] = []
    if not pack_rows:
        errors.append("source_pack_registry has no real rows")
    if not excerpt_rows:
        errors.append("source_excerpt_ledger has no real rows")
    if not digest_rows:
        errors.append("source_digest_ledger has no real rows")
    for index, row in enumerate(pack_rows, start=1):
        missing = missing_fields(row, REQUIRED_SOURCE_PACK_FIELDS)
        if missing:
            errors.append(f"source_pack_registry row {index} missing fields: {missing}")
    for index, row in enumerate(excerpt_rows, start=1):
        missing = missing_fields(row, REQUIRED_SOURCE_EXCERPT_FIELDS)
        if missing:
            errors.append(f"source_excerpt_ledger row {index} missing fields: {missing}")
    source_pack_ids = {row.get("source_pack_id", "") for row in pack_rows}
    for index, row in enumerate(excerpt_rows, start=1):
        if row.get("source_pack_id") not in source_pack_ids:
            errors.append(f"source_excerpt_ledger row {index} references unknown source_pack_id")
    content = "verified" if not errors and pack_rows and excerpt_rows and digest_rows else "unverified"
    return surface, content, len(pack_rows), len(excerpt_rows), len(digest_rows), errors


def audit_lockfile(path: Path, expected_batch_id: str) -> str:
    if not path.exists():
        return "missing"
    lock = load_yaml(path)
    missing = [field for field in REQUIRED_LOCK_FIELDS if field not in lock]
    if missing:
        return f"invalid_missing_fields:{','.join(missing)}"
    if lock.get("batch_id") != expected_batch_id:
        return "invalid_batch_id"
    if lock.get("run_status") not in {"not_started", "draft_generated", "alignment_passed", "review_pending", "failed"}:
        return "invalid_run_status"
    if lock.get("real_candidate_generation_allowed") is not False:
        return "invalid_generation_guard"
    return "ready_for_gate_only"


def build_report(workspace: Path) -> PilotReadiness:
    surface, content, pack_count, excerpt_count, digest_count, source_errors = audit_source_packs(workspace)
    lock_status = {
        "batch_000": audit_lockfile(workspace / "02_batch_briefs/batch_000.lock.yaml", "batch_000"),
        "batch_001": audit_lockfile(workspace / "02_batch_briefs/batch_001.lock.yaml", "batch_001"),
    }
    blockers: list[str] = []
    if surface != "ready":
        blockers.append("source_pack_surface_missing")
    if content != "verified":
        blockers.append("real_source_pack_content_unverified")
    if any(status != "ready_for_gate_only" for status in lock_status.values()):
        blockers.append("batch_lockfile_not_ready")
    checker_status = "fixture_verified_only"
    if content == "verified":
        checker_status = "ready_for_real_content_pilot"
    return PilotReadiness(
        source_pack_surface=surface,
        real_source_pack_content=content,
        source_pack_registry_rows=pack_count,
        source_excerpt_rows=excerpt_count,
        source_digest_rows=digest_count,
        source_pack_content_errors=source_errors,
        batch_lockfile_status=lock_status,
        checker_real_content_status=checker_status,
        non_git_policy={
            "ok_for": ["scaffold", "batch_000_001_pilot", "local_gate_proof"],
            "not_recommended_for": ["120_micro_batches", "3600_candidates", "long_running_dedupe_registry"],
        },
        next_allowed_mode="gate_dry_run_only" if blockers else "batch_000_001_real_content_pilot",
        blockers=blockers,
        readiness_flags={
            "candidatepack_ready": False,
            "KE_ready": False,
            "RAG_ready": False,
            "DIFY_ready": False,
            "production_servable": False,
            "generation_eligible": False,
            "generation_allowed": False,
            "release_ready": False,
            "production_ready": False,
        },
    )


def write_markdown(report: PilotReadiness, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    blockers = "\n".join(f"- `{blocker}`" for blocker in report.blockers) or "- none"
    source_errors = "\n".join(f"- {error}" for error in report.source_pack_content_errors) or "- none"
    lock_lines = "\n".join(f"- `{batch}`: `{status}`" for batch, status in report.batch_lockfile_status.items())
    path.write_text(
        "\n".join(
            [
                "# GKB Intake Pilot Readiness Audit",
                "",
                f"- source_pack_surface: `{report.source_pack_surface}`",
                f"- real_source_pack_content: `{report.real_source_pack_content}`",
                f"- source_pack_registry_rows: `{report.source_pack_registry_rows}`",
                f"- source_excerpt_rows: `{report.source_excerpt_rows}`",
                f"- source_digest_rows: `{report.source_digest_rows}`",
                f"- checker_real_content_status: `{report.checker_real_content_status}`",
                f"- next_allowed_mode: `{report.next_allowed_mode}`",
                "",
                "## Batch Lockfiles",
                "",
                lock_lines,
                "",
                "## Source Content Errors",
                "",
                source_errors,
                "",
                "## Blockers",
                "",
                blockers,
                "",
                "## Non-Git Policy",
                "",
                "- ok for: scaffold, batch_000_001_pilot, local_gate_proof",
                "- not recommended for: 120_micro_batches, 3600_candidates, long_running_dedupe_registry",
                "",
                "## Readiness Flags",
                "",
                "All readiness, generation, release, and production flags remain false.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    report = build_report(args.workspace)
    payload = asdict(report)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(text + "\n", encoding="utf-8")
    if args.report_md is not None:
        write_markdown(report, args.report_md)
    print(text)
    return 1 if args.fail_if_blocked and report.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
