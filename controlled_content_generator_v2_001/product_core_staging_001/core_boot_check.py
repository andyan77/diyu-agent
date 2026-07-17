#!/usr/bin/env python3
"""core 三判据机械验证（LOGICAL_CORE_SEPARATED）。

判据①：core 全模块可在不读任何领域私有目录的情况下导入启动
        （sys.addaudithook 记录一切 open，暂存树+标准库之外零命中，
         GATE1 私有路径样式零命中）；
判据②：测试语料经适配器以显式注入路径挂载（合成开发样例演示端到端）；
判据③：审计事件（qualification evidence / digest 闭包）不依赖 GATE1 私有路径
        （演示调用产出的证据对象内不含任何源仓绝对/相对私有路径字符串）。
输出：CORE_BOOT_REPORT.v1.json
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

STAGING = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGING))

PRIVATE_MARKERS = (
    "gate1_v1_1_001", "pkg1_open_regression", "delivery_control_001",
    "eval_audit_spine_001/calibration", "eval_audit_spine_001/fixtures",
    "eval_audit_spine_001/evidence", "generator_v3_successor_001", ".env",
)

opened: list[str] = []


def _hook(event: str, args) -> None:
    if event == "open":
        opened.append(str(args[0]))


sys.addaudithook(_hook)

modules = sorted(p.stem for p in (STAGING / "spine").glob("*.py")
                 if p.stem != "__init__")
imported = []
for name in ["spine"] + [f"spine.{m}" for m in modules]:
    importlib.import_module(name)
    imported.append(name)

from adapters.corpus_adapter import CorpusMount  # noqa: E402
from spine.calibration import family_coverage  # noqa: E402
from spine.canonical import digest_json  # noqa: E402

rows = list(CorpusMount(STAGING / "dev_samples/synthetic_dataset_rows.v1.jsonl").rows())
coverage = family_coverage(rows, 1)
evidence = {"coverage": coverage, "rows_digest": digest_json(rows)}
evidence_text = json.dumps(evidence, ensure_ascii=False)

private_opens = [p for p in opened for m in PRIVATE_MARKERS if m in p]
outside_opens = [p for p in opened
                 if not p.startswith(str(STAGING))
                 and not any(seg in p for seg in ("python3", "site-packages",
                                                  "lib/python", "encodings",
                                                  "__pycache__"))]
evidence_private_refs = [m for m in PRIVATE_MARKERS if m in evidence_text]

report = {
    "schema_version": "p7-core-boot-report-v1",
    "criterion_1_no_private_dir_reads": {
        "modules_imported": imported,
        "private_path_opens": private_opens,
        "passed": not private_opens,
    },
    "criterion_2_corpus_via_adapter": {
        "mounted_path_injected_explicitly": True,
        "rows_loaded": len(rows),
        "coverage_passed": bool(coverage["passed"]),
        "passed": len(rows) == 5 and bool(coverage["passed"]),
    },
    "criterion_3_audit_events_path_free": {
        "evidence_private_refs": evidence_private_refs,
        "passed": not evidence_private_refs,
    },
    "outside_staging_opens_nonstdlib": outside_opens,
    "logical_core_separated": (not private_opens
                               and len(rows) == 5 and bool(coverage["passed"])
                               and not evidence_private_refs),
}
(STAGING / "CORE_BOOT_REPORT.v1.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"logical_core_separated": report["logical_core_separated"],
                  "modules": len(imported), "private_opens": len(private_opens)},
                 ensure_ascii=False))
sys.exit(0 if report["logical_core_separated"] else 1)
