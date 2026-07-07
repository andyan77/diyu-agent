#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

READINESS_FLAGS = (
    "candidatepack_ready",
    "KE_ready",
    "RAG_ready",
    "DIFY_ready",
    "production_servable",
    "generation_eligible",
    "generation_allowed",
    "release_ready",
    "production_ready",
)

REQUIRED_RELATIVE_PATHS = (
    "00_contracts/gpt55_gkb_intake_manifest.yaml",
    "00_contracts/gpt55_gkb_card_contract.v1.yaml",
    "00_contracts/rich_body_blocks_contract.v1.yaml",
    "00_contracts/relation_edge_candidate_contract.v1.yaml",
    "00_contracts/cso_signal_candidate_contract.v1.yaml",
    "00_contracts/l2_l3_execution_asset_candidate_contract.v1.yaml",
    "00_contracts/serving_passage_spec_candidate_contract.v1.yaml",
    "00_contracts/gold_hook_candidate_contract.v1.yaml",
    "00_contracts/knowledge_runtime_readiness_assertions.v1.yaml",
    "00_contracts/forbidden_scope_policy.v1.yaml",
    "01_source_packs/source_pack_manifest.yaml",
    "01_source_packs/source_pack_registry.csv",
    "01_source_packs/source_excerpt_ledger.csv",
    "01_source_packs/source_digest_ledger.csv",
    "02_batch_briefs/batch_plan.yaml",
    "02_batch_briefs/batch_manifest_registry.csv",
    "02_batch_briefs/batch_000.yaml",
    "02_batch_briefs/batch_001.yaml",
    "07_fingerprints/semantic_fingerprint_registry.csv",
    "07_fingerprints/semantic_fingerprint_delta.csv",
    "12_ledger/review_queue.csv",
    "12_ledger/failure_ledger.yaml",
    "12_ledger/source_gap_ledger.yaml",
    "12_ledger/decision_packet_ledger.yaml",
    "12_ledger/human_decision_required.yaml",
)

CSV_HEADERS = {
    "01_source_packs/source_pack_registry.csv": [
        "source_pack_id",
        "source_pack_type",
        "source_title",
        "source_owner",
        "source_license_or_usage_status",
        "source_scope",
        "source_file_ref",
        "source_digest",
        "excerpt_count",
        "allowed_usage",
        "forbidden_usage",
        "privacy_or_consent_status",
        "ingestion_status",
    ],
    "01_source_packs/source_excerpt_ledger.csv": [
        "source_excerpt_id",
        "source_pack_id",
        "section_ref",
        "excerpt_text",
        "excerpt_digest",
        "declared_topic",
        "declared_layer_hint",
        "claim_type_hint",
        "usable_for_general_kb",
        "usable_for_brand_kb",
        "hard_claim_present",
        "personal_data_present",
        "requires_human_review",
    ],
    "01_source_packs/source_digest_ledger.csv": [
        "source_digest_id",
        "source_pack_id",
        "source_file_ref",
        "hash_algorithm",
        "source_digest",
        "created_at",
        "notes",
    ],
    "07_fingerprints/semantic_fingerprint_registry.csv": [
        "semantic_fingerprint",
        "candidate_id",
        "batch_id",
        "status",
        "supersedes",
        "conflict_status",
        "notes",
    ],
    "07_fingerprints/semantic_fingerprint_delta.csv": [
        "semantic_fingerprint",
        "candidate_id",
        "batch_id",
        "delta_action",
        "reason",
    ],
    "12_ledger/review_queue.csv": [
        "candidate_id",
        "issue_type",
        "reviewer_needed",
        "machine_reason",
        "allowed_actions",
        "current_route",
        "decision_packet_ref",
    ],
}

FORBIDDEN_ROOTS = (
    "KE",
    "serving_projection",
    "rag",
    "dify",
    "candidatepack_etl/candidatepack_instances",
    "candidatepack_instances",
    "runtime",
)


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    errors: list[str]
    warnings: list[str]
    checked_files: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate GKB intake workspace as a local gate.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--scaffold-only", action="store_true")
    parser.add_argument("--require-content", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    parser.add_argument("--report-json", type=Path)
    return parser.parse_args()


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_structured_files(workspace: Path) -> list[Path]:
    return sorted(path for path in workspace.rglob("*") if path.is_file() and path.suffix in {".yaml", ".yml", ".json"})


def walk(value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        rows: list[tuple[str, Any]] = []
        for key, child in value.items():
            rows.append((str(key), child))
            rows.extend(walk(child))
        return rows
    if isinstance(value, list):
        rows = []
        for child in value:
            rows.extend(walk(child))
        return rows
    return []


def is_true(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def validate_parseable(workspace: Path) -> tuple[int, list[str]]:
    errors: list[str] = []
    checked = 0
    for path in iter_structured_files(workspace):
        checked += 1
        try:
            if path.suffix == ".json":
                load_json(path)
            else:
                load_yaml(path)
        except Exception as exc:
            errors.append(f"{path}: parse failed: {exc}")
    for path in sorted(workspace.rglob("*.csv")):
        checked += 1
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                list(csv.DictReader(handle))
        except Exception as exc:
            errors.append(f"{path}: csv parse failed: {exc}")
    return checked, errors


def validate_csv_headers(workspace: Path) -> list[str]:
    errors: list[str] = []
    for relative, expected in CSV_HEADERS.items():
        path = workspace / relative
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            actual = csv.DictReader(handle).fieldnames or []
        if actual != expected:
            errors.append(f"{relative}: header mismatch: expected {expected}, got {actual}")
    return errors


def validate_contracts(workspace: Path) -> list[str]:
    errors: list[str] = []
    card_contract = load_yaml(workspace / "00_contracts/gpt55_gkb_card_contract.v1.yaml")
    required = card_contract.get("required_fields") if isinstance(card_contract, dict) else None
    if not isinstance(required, list) or len(required) < 20:
        errors.append("gpt55_gkb_card_contract.v1.yaml must define a substantial required_fields list")
    rich_contract = load_yaml(workspace / "00_contracts/rich_body_blocks_contract.v1.yaml")
    blocks = rich_contract.get("required_blocks") if isinstance(rich_contract, dict) else None
    if not isinstance(blocks, list) or "capability_consumption_hint" not in blocks:
        errors.append("rich_body_blocks_contract.v1.yaml must define required rich body blocks")
    return errors


def validate_readiness(workspace: Path) -> list[str]:
    errors: list[str] = []
    for path in iter_structured_files(workspace):
        data = load_json(path) if path.suffix == ".json" else load_yaml(path)
        for key, value in walk(data):
            if key in READINESS_FLAGS and is_true(value):
                errors.append(f"{path}: readiness flag is true: {key}")
    return errors


def validate_forbidden_roots(workspace: Path) -> list[str]:
    repo_root = workspace.parents[1]
    return [f"forbidden root exists: {root}" for root in FORBIDDEN_ROOTS if (repo_root / root).exists()]


def validate_content_presence(workspace: Path, require_content: bool, scaffold_only: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    content_dirs = ("03_raw_drafts", "04_aligned_candidates", "05_rich_body_blocks")
    content_files = [
        path
        for directory in content_dirs
        for path in (workspace / directory).rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    ]
    if scaffold_only and content_files:
        warnings.append("scaffold-only mode found candidate content files")
    if require_content and not content_files:
        errors.append("require-content mode needs candidate content files under raw/aligned/rich body directories")
    return errors, warnings


def run_gate_suite(workspace: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    root = Path(__file__).resolve().parents[2]
    summary_path = workspace / "11_reports" / "gkb_intake_gate_summary.json"
    command = [
        sys.executable,
        str(root / "tools/gkb_intake/run_gates.py"),
        "--workspace",
        str(workspace),
        "--selftest",
        "--summary-json",
        str(summary_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        errors.append(f"gate suite failed with code {completed.returncode}; see {summary_path}")
    if completed.stderr:
        warnings.append(completed.stderr.strip())
    return errors, warnings


def validate(workspace: Path, scaffold_only: bool, require_content: bool, run_gates: bool) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if not workspace.exists():
        return ValidationResult(False, [f"workspace missing: {workspace}"], warnings, 0)
    for relative in REQUIRED_RELATIVE_PATHS:
        if not (workspace / relative).exists():
            errors.append(f"required file missing: {relative}")
    checked_files, parse_errors = validate_parseable(workspace)
    errors.extend(parse_errors)
    errors.extend(validate_csv_headers(workspace))
    errors.extend(validate_contracts(workspace))
    errors.extend(validate_readiness(workspace))
    errors.extend(validate_forbidden_roots(workspace))
    content_errors, content_warnings = validate_content_presence(workspace, require_content, scaffold_only)
    errors.extend(content_errors)
    warnings.extend(content_warnings)
    manifest = load_yaml(workspace / "00_contracts/gpt55_gkb_intake_manifest.yaml")
    if scaffold_only and isinstance(manifest, dict) and manifest.get("status") != "scaffold_only":
        errors.append("manifest status must be scaffold_only in scaffold-only mode")
    if run_gates:
        gate_errors, gate_warnings = run_gate_suite(workspace)
        errors.extend(gate_errors)
        warnings.extend(gate_warnings)
    return ValidationResult(not errors, errors, warnings, checked_files)


def main() -> int:
    args = parse_args()
    result = validate(args.workspace, args.scaffold_only, args.require_content, args.run_gates)
    payload = result.__dict__
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
