#!/usr/bin/env python3
"""S0 首次尝试不可变锚门的本地 fail-closed 测试（Codex R2 ADVISORY 固化）。

门的豁免面 = 恰好 4 处 schema_version 标签修正、且修正后全部等于合同标签
gate1-v4-author-raw-v1；少改 / 多改 / 改错标签 / 任何语义差异都必须在本门
即失败，不得依赖下游 E_V4_RAW_SCHEMA 兜底。
"""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
S0_RUN = (HERE.parents[1] / "evidence/s0_m2_real_run_001/tools/s0_run.py")


def _load():
    spec = importlib.util.spec_from_file_location("s0_anchor_tests", S0_RUN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S0AnchorGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.s0 = _load()
        self.real_read = self.s0._read

    def tearDown(self) -> None:
        self.s0._read = self.real_read

    def _patch_raw(self, mutate):
        real_read = self.real_read

        def patched(rel: str):
            value = real_read(rel)
            if rel.endswith("raw_first_attempts.v1.json"):
                value = copy.deepcopy(value)
                mutate(value)
            return value

        self.s0._read = patched

    def test_baseline_passes_with_exactly_four_label_changes(self) -> None:
        ok, notes = self.s0._anchor_semantic_diff()
        self.assertTrue(ok, notes)
        self.assertIn("schema_version_label_changes=4 (required==4)", notes)

    def test_one_label_reverted_fails_locally(self) -> None:
        self._patch_raw(lambda v: v["attempts"][0].__setitem__(
            "schema_version", "gate1-v4-raw-output-v1"))
        ok, notes = self.s0._anchor_semantic_diff()
        self.assertFalse(ok, notes)

    def test_wrong_target_label_fails_locally(self) -> None:
        self._patch_raw(lambda v: v["attempts"][1].__setitem__(
            "schema_version", "gate1-v4-author-raw-v2"))
        ok, notes = self.s0._anchor_semantic_diff()
        self.assertFalse(ok, notes)

    def test_semantic_content_change_fails(self) -> None:
        self._patch_raw(lambda v: v["attempts"][0].__setitem__(
            "text", v["attempts"][0].get("text", "") + " 洗绿"))
        ok, notes = self.s0._anchor_semantic_diff()
        self.assertFalse(ok, notes)


if __name__ == "__main__":
    unittest.main(verbosity=1)
