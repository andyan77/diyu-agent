#!/usr/bin/env python3
"""八件套 manifest 校验的比对基准测试（M2→M3 转接修复，2026-07-17 发起人默认授权）。

缺陷：_verify_manifest 对无冻结快照的普通条目一律拿活树文件比对，
把关闭阶段合同内合法演进（双签后阶段登记 → spine 候选清单闭环重建）
误判为篡改，导致 M3 启动预检拒绝。

修复语义：普通条目摘要 = 活树文件 或 绑定候选提交处 blob，二者其一即放行；
两路皆败仍拦（fail-closed 不降）；快照条目不回退（快照即其冻结基准）。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
ROOT = DC.parents[3]
M2 = DC / "milestones/M2"
CAND = "5ce595de7eb48fcf04178651f84400b0411134be"
SPINE_MANIFEST_REL = ("controlled_content_generator_v2_001/gate1_v1_1_001/"
                      "p7_successor_longrun_001/eval_audit_spine_001/"
                      "release/candidate_manifest.v1.json")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


closeout = _load(DC / "tools/closeout.py", "closeout_basis_tests")


def _mk_manifest(directory: Path, entries: list[dict], bound: str = CAND) -> Path:
    (directory / "snapshots").mkdir(exist_ok=True)
    value = {"schema_version": "p7-milestone-manifest-v1",
             "bound_candidate_commit": bound,
             "entries": entries, "entry_count": len(entries),
             "note": "test", "manifest_digest": ""}
    value["manifest_digest"] = closeout.receipts.canonical_digest(
        value, "manifest_digest")
    path = directory / "OUTPUT_MANIFEST.v2.json"
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


class TransitionBasisTests(unittest.TestCase):
    def test_m2_eight_pieces_validate_after_closure(self) -> None:
        """真实 M2 八件套在关闭后的活树上必须通过（发起人报告的拒绝场景）。"""
        ok, details = closeout.validate_eight_pieces(ROOT, M2)
        self.assertTrue(ok, details)

    def test_plain_entry_evolved_live_file_passes_via_candidate_blob(self) -> None:
        """条目摘要 = 候选 blob、活树已合法演进 → 放行。"""
        import subprocess
        blob = subprocess.run(["git", "-C", str(ROOT), "show",
                               f"{CAND}:{SPINE_MANIFEST_REL}"],
                              capture_output=True, check=True).stdout
        entry = {"path": SPINE_MANIFEST_REL,
                 "sha256": hashlib.sha256(blob).hexdigest()}
        live = hashlib.sha256((ROOT / SPINE_MANIFEST_REL).read_bytes()).hexdigest()
        self.assertNotEqual(entry["sha256"], live,
                            "前提：活树确已演进（关闭阶段重建）")
        with tempfile.TemporaryDirectory() as tmp:
            path = _mk_manifest(Path(tmp), [entry])
            errors = closeout._verify_manifest(ROOT, path, "x/y.json")
            self.assertEqual(errors, [])

    def test_plain_entry_matching_neither_is_still_tamper(self) -> None:
        """条目摘要既非活树也非候选 blob → 依旧拦截（防伪面不降）。"""
        entry = {"path": SPINE_MANIFEST_REL, "sha256": "f" * 64}
        with tempfile.TemporaryDirectory() as tmp:
            path = _mk_manifest(Path(tmp), [entry])
            errors = closeout._verify_manifest(ROOT, path, "x/y.json")
            self.assertTrue(any("digest drift" in e for e in errors), errors)

    def test_bogus_bound_commit_gets_no_fallback(self) -> None:
        """绑定提交非 40 位十六进制 → 不回退，直接拦。"""
        entry = {"path": SPINE_MANIFEST_REL, "sha256": "f" * 64}
        with tempfile.TemporaryDirectory() as tmp:
            path = _mk_manifest(Path(tmp), [entry], bound="HEAD")
            errors = closeout._verify_manifest(ROOT, path, "x/y.json")
            self.assertTrue(any("digest drift" in e for e in errors), errors)

    def test_snapshot_entry_never_falls_back(self) -> None:
        """快照条目：快照文件被改 → 即便条目摘要等于候选 blob 也必须拦。"""
        import subprocess
        blob = subprocess.run(["git", "-C", str(ROOT), "show",
                               f"{CAND}:{SPINE_MANIFEST_REL}"],
                              capture_output=True, check=True).stdout
        good_sha = hashlib.sha256(blob).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp)
            (mdir / "snapshots").mkdir()
            snap = mdir / "snapshots/frozen.json"
            snap.write_bytes(b"tampered")
            # pathlib: root / <绝对路径> == 该绝对路径 → 落在本 manifest 的
            # snapshots/ 内，通过包含性检查后必须因摘要不符被拦
            entry = {"path": SPINE_MANIFEST_REL, "sha256": good_sha,
                     "frozen_snapshot": str(snap)}
            path = _mk_manifest(mdir, [entry])
            errors = closeout._verify_manifest(ROOT, path, "x/y.json")
            self.assertTrue(any("digest drift" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=1)
