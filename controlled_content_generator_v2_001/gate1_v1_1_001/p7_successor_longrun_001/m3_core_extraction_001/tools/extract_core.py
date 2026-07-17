#!/usr/bin/env python3
"""M3 胶囊⑥ core 逻辑抽取（D0 §②③⑤ + CORE_EXPORT_ALLOWLIST）。

抽取源（allowlist）→ 顶层暂存 product_core_staging_001/：
- eval_audit_spine_001/spine/*.py     字节等同（排除 runner.py——P7 检查器胶水，
  内嵌 p7 私有路径，属源仓诊断面不属 core）
- eval_audit_spine_001/schema/*.json  字节等同
- eval_audit_spine_001/rubric/*       字节等同（量规模板，不含金标实例）
- eval_audit_spine_001/tests/*        字节等同（排除 test_s0_anchor_gate.py——
  模块级依赖 evidence/ 私有工具；另以 pytest deselect 剔除 2 个引用
  calibration//fixtures/ 的用例，文件本体不改）
暂存新增（NEW_STAGING_ONLY，非抽取物）：
- adapters/corpus_adapter.py  语料经显式注入路径挂载（D0 §⑤ 单向测试协议接口）
- dev_samples/*.jsonl         合成非密封开发样例（新造，非任何轮次数据）
- core_boot_check.py          三判据机械验证（审计钩子证零私有路径读取）
- pytest.ini / README.md      暂存配置与边界声明

输出：EXTRACTION_MANIFEST.v1.json（逐文件 sha256 三态：IDENTICAL / NEW_STAGING_ONLY / EXCLUDED+理由）
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
M3CE = HERE.parents[1]
P7 = HERE.parents[2]
SPINE = P7 / "eval_audit_spine_001"
STAGING = P7.parents[1] / "product_core_staging_001"

EXCLUDED = {
    "tests/test_s0_anchor_gate.py": "模块级依赖 evidence/s0_m2_real_run_001 私有工具，无法自含",
    "tests/test_external_llm.py": ("依赖 contract/deepseek_rate_card.v1.json——contract/ 不在 "
                                   "CORE_EXPORT_ALLOWLIST 前缀内（零字节出仓硬规则）；external_llm 模块"
                                   "本体仍在 core，其费率/密钥装载按 allowlist 注记于 M5 换产品配置层"
                                   "并配套产品侧测试"),
}
DECOUPLED = {
    "spine/runner.py": ("混合体解耦（D0 allowlist：引用 denylist 路径不得原样导出，须先解耦）："
                        "integrity_snapshot 为纯 core 逻辑，从源文件逐字切片保留；"
                        "_actual_m0_status（硬编码 p7 calibration 路径）删除；"
                        "r5_shadow_audit（P7 私有只读诊断，内嵌 pkg1 路径）以声明式拒调桩保留符号"
                        "——仅为自含测试套件导入闭包，调用即 NotImplementedError"),
}
DESELECTED_TESTS = [
    "tests/test_eval_audit_spine.py::ContractTests::test_conditional_schemas_reject_semantic_contradictions",
    "tests/test_eval_audit_spine.py::LegacyShadowTests::test_r5_known_veto_shadow_is_read_only_and_not_qualification",
    "tests/test_eval_audit_spine.py::OperationsTests::test_candidate_manifest_is_recomputable",
]
DESELECT_REASONS = {
    DESELECTED_TESTS[0]: "读源仓 calibration/qualification_manifest.v1.json（denylist 前缀，不随 core 出仓）",
    DESELECTED_TESTS[1]: "读源仓 fixtures/r5_known_veto_regression.v1.jsonl + calibration/M0_STATUS（denylist 前缀）",
    DESELECTED_TESTS[2]: "候选清单重建断言源仓树形（p7 .gitignore 等）；产品侧同类保证由 EXTRACTION_MANIFEST + M5 RELEASE_EQUIVALENCE 承载",
}

PYTEST_INI = ("[pytest]\naddopts =" +
              "".join(f" --deselect {t}" for t in DESELECTED_TESTS) + "\n")

README = """# product_core_staging_001（产品 A core 暂存）

D0 §② 预登记写面的 M3 物化。只见接口、schema、量规模板、自含验证套件与合成非密封开发样例。
零领域数据：无 QUAL/G1/G2/round/R1-R5/隐藏材料/审计内档（DOMAIN_DATA_DENYLIST 逐字节零命中）。
语料只经 adapters/corpus_adapter.py 显式注入路径挂载（源仓→产品单向，产品输出不回写源仓）。
接口冻结与三判据验证：见 p7_successor_longrun_001/m3_core_extraction_001/INTERFACE_FREEZE.v1.json。
本目录在 M5 前不建正式产品仓、不推远程（D0 边界重申）。
"""

CORPUS_ADAPTER = '''"""语料适配器：core 唯一的领域语料入口（D0 §⑤ 单向测试协议）。

core 不知道任何 GATE1 私有路径；调用方（源仓或产品装配层）把语料路径
显式注入。适配器只做行级读取与形状透传，不做任何领域推断。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


class CorpusMount:
    """显式路径挂载的只读语料源。"""

    def __init__(self, corpus_path: str | Path):
        self._path = Path(corpus_path)
        if not self._path.is_file():
            raise FileNotFoundError(f"corpus not mounted: {self._path}")

    def rows(self) -> Iterator[dict[str, Any]]:
        with open(self._path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)
'''

DEV_SAMPLE_ROWS = [
    {"sample_kind": "SYNTHETIC_STAGING_DEV_SAMPLE", "case_id": "CORE-DEV-0001",
     "family_id": "F1_PEOPLE_AND_REAL_SCENE",
     "note": "合成暂存开发样例：非任何轮次/金标/密封数据；仅供 core 启动自检使用"},
    {"sample_kind": "SYNTHETIC_STAGING_DEV_SAMPLE", "case_id": "CORE-DEV-0002",
     "family_id": "F2_PROFESSIONAL_AND_SEARCH", "note": "同上"},
    {"sample_kind": "SYNTHETIC_STAGING_DEV_SAMPLE", "case_id": "CORE-DEV-0003",
     "family_id": "F3_PRODUCT_RELATION_AND_AESTHETIC", "note": "同上"},
    {"sample_kind": "SYNTHETIC_STAGING_DEV_SAMPLE", "case_id": "CORE-DEV-0004",
     "family_id": "F4_STORE_LOCAL_AND_RETAIL", "note": "同上"},
    {"sample_kind": "SYNTHETIC_STAGING_DEV_SAMPLE", "case_id": "CORE-DEV-0005",
     "family_id": "F5_ENTERPRISE_LONG_TERM_TRUST", "note": "同上"},
]

BOOT_CHECK = '''#!/usr/bin/env python3
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
    json.dumps(report, ensure_ascii=False, indent=1) + "\\n", encoding="utf-8")
print(json.dumps({"logical_core_separated": report["logical_core_separated"],
                  "modules": len(imported), "private_opens": len(private_opens)},
                 ensure_ascii=False))
sys.exit(0 if report["logical_core_separated"] else 1)
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_decoupled_runner(src: Path) -> str:
    """从源 runner.py 逐字切片 integrity_snapshot，装配解耦版暂存 runner。"""
    lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines)
                 if l.startswith("def integrity_snapshot"))
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("def ")), len(lines))
    snapshot_src = "".join(lines[start:end]).rstrip() + "\n"
    header = (
        '"""core 完整性快照（自 eval_audit_spine_001/spine/runner.py 解耦抽取）。\n'
        "\n"
        "integrity_snapshot 为逐字切片保留的纯 core 逻辑；\n"
        "P7 私有诊断（_actual_m0_status / r5_shadow_audit 实现）不属产品面，未导出。\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from pathlib import Path\n"
        "from typing import Any\n"
        "\n"
        "from .canonical import read_jsonl\n"
        "from .contracts import validate_dataset_rows\n"
        "from .m0 import build_m0_decision\n"
        "\n\n")
    stub = (
        "\n\n"
        "def r5_shadow_audit(root: Path, fixture_path: Path) -> dict[str, Any]:\n"
        '    """P7 私有只读诊断；产品 core 无此功能。符号仅为自含测试套件的\n'
        "    导入闭包保留（对应用例已 deselect），调用即拒。\"\"\"\n"
        "    raise NotImplementedError(\n"
        '        "r5_shadow_audit is P7-private diagnostics; excluded from product core")\n')
    return header + snapshot_src + stub


def main() -> int:
    # 选择性清理：宿主沙箱会向目录绑定挂载 .mcp.json/.claude（不可删且非本工具产物），
    # 只清我们管理的内容件
    HOST_MOUNTS = {".mcp.json", ".claude"}
    if STAGING.exists():
        for child in STAGING.iterdir():
            if child.name in HOST_MOUNTS:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    entries = []

    def copy_tree(rel_dir: str, pattern: str) -> None:
        src_dir = SPINE / rel_dir
        dst_dir = STAGING / rel_dir
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(src_dir.glob(pattern)):
            if src.is_dir() or src.name == "__pycache__":
                continue
            rel = f"{rel_dir}/{src.name}"
            if rel in EXCLUDED:
                entries.append({"path": rel, "status": "EXCLUDED",
                                "reason": EXCLUDED[rel],
                                "source_sha256": sha(src)})
                continue
            dst = dst_dir / src.name
            if rel in DECOUPLED:
                dst.write_text(build_decoupled_runner(src), encoding="utf-8")
                entries.append({"path": rel, "status": "DECOUPLED",
                                "reason": DECOUPLED[rel],
                                "source_sha256": sha(src),
                                "staged_sha256": sha(dst)})
                continue
            shutil.copy2(src, dst)
            s_src, s_dst = sha(src), sha(dst)
            assert s_src == s_dst
            entries.append({"path": rel, "status": "IDENTICAL",
                            "source_sha256": s_src, "staged_sha256": s_dst})

    copy_tree("spine", "*.py")
    copy_tree("schema", "*")
    copy_tree("rubric", "*")
    copy_tree("tests", "*.py")

    def new_file(rel: str, text: str) -> None:
        dst = STAGING / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        entries.append({"path": rel, "status": "NEW_STAGING_ONLY",
                        "staged_sha256": sha(dst)})

    new_file("pytest.ini", PYTEST_INI)
    new_file("README.md", README)
    new_file("adapters/__init__.py", "")
    new_file("adapters/corpus_adapter.py", CORPUS_ADAPTER)
    new_file("dev_samples/synthetic_dataset_rows.v1.jsonl",
             "\n".join(json.dumps(r, ensure_ascii=False) for r in DEV_SAMPLE_ROWS) + "\n")
    new_file("core_boot_check.py", BOOT_CHECK)

    manifest = {
        "schema_version": "p7-core-extraction-manifest-v1",
        "milestone_id": "M3",
        "capsule": "M3_C6_CORE_EXTRACTION",
        "source_package": "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001",
        "staging_root": "controlled_content_generator_v2_001/product_core_staging_001",
        "allowlist_authority": "delivery_control_001/contracts/CORE_EXPORT_ALLOWLIST.v1.json",
        "deselected_tests_in_staging": [
            {"test_id": t, "reason": DESELECT_REASONS[t]} for t in DESELECTED_TESTS],
        "identical_count": sum(1 for e in entries if e["status"] == "IDENTICAL"),
        "decoupled_count": sum(1 for e in entries if e["status"] == "DECOUPLED"),
        "new_staging_only_count": sum(1 for e in entries if e["status"] == "NEW_STAGING_ONLY"),
        "excluded_count": sum(1 for e in entries if e["status"] == "EXCLUDED"),
        "entries": entries,
    }
    blob = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    manifest["manifest_digest"] = hashlib.sha256(blob).hexdigest()
    (M3CE / "EXTRACTION_MANIFEST.v1.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"identical": manifest["identical_count"],
                      "new": manifest["new_staging_only_count"],
                      "excluded": manifest["excluded_count"],
                      "manifest_digest": manifest["manifest_digest"][:16]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
