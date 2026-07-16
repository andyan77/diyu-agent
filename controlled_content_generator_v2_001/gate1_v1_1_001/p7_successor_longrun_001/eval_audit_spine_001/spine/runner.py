"""供 P7 唯一总检查入口调用的纯诊断函数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import file_digest, read_jsonl
from .contracts import validate_dataset_rows
from .evidence_chain import known_risk_findings
from .m0 import build_m0_decision


def _actual_m0_status(root: Path) -> str:
    """回显值读实际状态真源（M0_STATUS.v1.json），不再硬编码（v2.5 §五 B 家族迁移）。"""
    status_path = (root / "controlled_content_generator_v2_001/gate1_v1_1_001"
                   "/p7_successor_longrun_001/eval_audit_spine_001"
                   "/calibration/M0_STATUS.v1.json")
    try:
        return str(json.loads(status_path.read_text(encoding="utf-8")).get(
            "status", "INVALID_STATE"))
    except (OSError, ValueError):
        return "INVALID_STATE"


def _surface(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "cta"):
        if row.get(key):
            parts.append(str(row[key]))
    for key in ("body", "spoken_lines", "visual_execution", "audio_execution"):
        value = row.get(key, [])
        parts.extend(map(str, value if isinstance(value, list) else [value]))
    return "\n".join(parts)


def r5_shadow_audit(root: Path, fixture_path: Path) -> dict[str, Any]:
    """历史R5只读影子诊断：证明旧门漏过已知5条，不把挑战种子当金标资格。"""
    p7 = root / "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001"
    r5 = p7 / "pkg1_open_regression/round5"
    outputs_path = r5 / "outputs/first_outputs.g3.v1.jsonl"
    machine_path = r5 / "outputs/machine_gate_report.v1.json"
    expected = read_jsonl(fixture_path)
    outputs = {str(row["request_id"]): row for row in read_jsonl(outputs_path)}
    detected: dict[str, list[str]] = {}
    for output_id, row in outputs.items():
        codes = [finding["code"] for finding in known_risk_findings(output_id, _surface(row))]
        if codes:
            detected[output_id] = sorted(codes)
    expected_ids = sorted(str(row["output_id"]) for row in expected)
    machine = json.loads(machine_path.read_text(encoding="utf-8"))
    hard_count = int(machine.get("hard_failure_count", 0))
    return {
        "audit_kind": "LEGACY_READ_ONLY_SHADOW",
        "qualification_use": False,
        "r5_output_digest": file_digest(outputs_path),
        "expected_known_veto_ids": expected_ids,
        "development_rule_detected_ids": sorted(set(expected_ids) & set(detected)),
        "known_veto_regression_recall":
            len(set(expected_ids) & set(detected)) / len(expected_ids) if expected_ids else None,
        "legacy_machine_hard_failure_count": hard_count,
        "legacy_machine_known_veto_recall": 0.0 if hard_count == 0 and expected_ids else None,
        "claim_completeness_warning":
            "author semantic_claims were not treated as an exhaustive claim inventory",
        "m0_qualification_status": _actual_m0_status(root),
    }


def integrity_snapshot(root: Path, dataset_manifest: Path | None = None) -> dict[str, Any]:
    dataset = validate_dataset_rows(read_jsonl(dataset_manifest)) if dataset_manifest else {
        "passed": True, "errors": [], "case_count": 0, "cell_counts": {}}
    decision = build_m0_decision(
        [], record_manifests=[], required_report_refs=None,
        qualification_manifest=None, independent_adjudication_report=None,
        audit_integrity_report=None)
    return {"dataset_integrity": dataset,
            "artifact_integrity_status": "PASS" if dataset["passed"] else "FAIL",
            "m0_qualification_status": decision["status"],
            "m0_decision_digest": decision["decision_digest"],
            "reason": "implementation exists; sealed qualification evidence is not materialized"}
