"""core 完整性快照（自 eval_audit_spine_001/spine/runner.py 解耦抽取）。

integrity_snapshot 为逐字切片保留的纯 core 逻辑；
P7 私有诊断（_actual_m0_status / r5_shadow_audit 实现）不属产品面，未导出。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import read_jsonl
from .contracts import validate_dataset_rows
from .m0 import build_m0_decision


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


def r5_shadow_audit(root: Path, fixture_path: Path) -> dict[str, Any]:
    """P7 私有只读诊断；产品 core 无此功能。符号仅为自含测试套件的
    导入闭包保留（对应用例已 deselect），调用即拒。"""
    raise NotImplementedError(
        "r5_shadow_audit is P7-private diagnostics; excluded from product core")
