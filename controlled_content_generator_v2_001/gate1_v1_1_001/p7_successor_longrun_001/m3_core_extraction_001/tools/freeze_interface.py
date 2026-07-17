#!/usr/bin/env python3
"""M3 胶囊⑥ 接口冻结：AST 普查暂存 core 公共接口 + 三判据机械核证汇总。"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
M3CE = HERE.parents[1]
P7 = HERE.parents[2]
STAGING = P7.parents[1] / "product_core_staging_001"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_symbols(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                out.append(node.name)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and not t.id.startswith("_") and t.id.isupper():
                    out.append(t.id)
    return sorted(set(out))


def main() -> int:
    manifest = json.loads((M3CE / "EXTRACTION_MANIFEST.v1.json").read_text(encoding="utf-8"))
    boot = json.loads((STAGING / "CORE_BOOT_REPORT.v1.json").read_text(encoding="utf-8"))
    if not boot.get("logical_core_separated"):
        raise SystemExit("boot report says logical_core_separated != true — refuse to freeze")

    proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                          capture_output=True, text=True, cwd=str(STAGING))
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if proc.returncode != 0 or "failed" in tail:
        raise SystemExit(f"staged tests not green: {tail}")

    modules = {}
    for py in sorted((STAGING / "spine").glob("*.py")):
        if py.stem == "__init__":
            continue
        modules[f"spine/{py.name}"] = {
            "sha256": sha(py),
            "public_symbols": public_symbols(py),
        }
    adapters = {f"adapters/{p.name}": {"sha256": sha(p),
                                       "public_symbols": public_symbols(p)}
                for p in sorted((STAGING / "adapters").glob("*.py")) if p.stem != "__init__"}

    freeze = {
        "schema_version": "p7-core-interface-freeze-v1",
        "milestone_id": "M3",
        "capsule": "M3_C6_CORE_EXTRACTION",
        "staging_root": "controlled_content_generator_v2_001/product_core_staging_001",
        "extraction_manifest_digest": manifest["manifest_digest"],
        "frozen_modules": modules,
        "adapter_interface": adapters,
        "criteria": {
            "core_starts_without_domain_private_reads": {
                "verdict": boot["criterion_1_no_private_dir_reads"]["passed"],
                "evidence": "product_core_staging_001/CORE_BOOT_REPORT.v1.json criterion_1（audithook 全 open 记录，私有路径样式零命中）",
            },
            "test_corpus_mounted_via_adapter": {
                "verdict": boot["criterion_2_corpus_via_adapter"]["passed"],
                "evidence": "CORE_BOOT_REPORT criterion_2（CorpusMount 显式注入路径挂载合成开发样例，family_coverage 端到端）",
            },
            "audit_events_free_of_gate1_private_paths": {
                "verdict": boot["criterion_3_audit_events_path_free"]["passed"],
                "evidence": "CORE_BOOT_REPORT criterion_3（演示证据对象文本私有路径标记零命中）",
            },
        },
        "staged_test_summary": tail,
        "core_boot_report_sha256": sha(STAGING / "CORE_BOOT_REPORT.v1.json"),
        "logical_core_separated": True,
        "flag_registration": "LOGICAL_CORE_SEPARATED 于 M3 关闭 PASS 回执 qualification_flags 登记（MILESTONE_EXIT_CONTRACT M3 required_exit_keys 成员）",
        "d0_boundary_note": "不建正式产品仓、不推远程（属 M5）；暂存零领域数据（DOMAIN_DATA_DENYLIST 类别零命中，见 EXTRACTION_MANIFEST 三态清单）",
    }
    blob = json.dumps(freeze, ensure_ascii=False, sort_keys=True).encode("utf-8")
    freeze["freeze_digest"] = hashlib.sha256(blob).hexdigest()
    (M3CE / "INTERFACE_FREEZE.v1.json").write_text(
        json.dumps(freeze, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"logical_core_separated": True,
                      "modules": len(modules), "adapters": len(adapters),
                      "staged_tests": tail,
                      "freeze_digest": freeze["freeze_digest"][:16]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
