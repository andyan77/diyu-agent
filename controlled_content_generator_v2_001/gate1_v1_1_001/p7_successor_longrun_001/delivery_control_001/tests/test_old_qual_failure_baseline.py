#!/usr/bin/env python3
"""R0 机械失败基线测试：证明 M3 v1 旧 QUAL-A/B 确定性失败 M0 每套逐模块下限。

不允许「文档里写一句数量不足」冒充证明——这里以真实 old_qual_failure_baseline.compute_baseline()
对真实冻结回执复算，断言两套 verdict=FAIL 且关键缺模块/低量键在 definitive_fail 内。
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent
BASELINE = P7 / "m3_data_supply_001/tools/old_qual_failure_baseline.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


baseline = _load(BASELINE, "old_qual_failure_baseline")


class OldQualFailureBaseline(unittest.TestCase):

    def setUp(self) -> None:
        self.result = baseline.compute_baseline()

    def test_overall_old_qual_fails(self) -> None:
        self.assertEqual(self.result["overall_verdict"],
                         "OLD_QUAL_FAILS_M0_MINIMUMS")

    def test_both_sets_fail(self) -> None:
        for sid in ("A", "B"):
            self.assertEqual(self.result["per_set"][sid]["verdict"], "FAIL", sid)

    def test_seven_absent_modules_definitively_fail(self) -> None:
        for sid in ("A", "B"):
            fails = set(self.result["per_set"][sid]["definitive_fail_keys"])
            for key in ("reference_extraction_positive_cases",
                        "claim_atomization_positive_cases",
                        "fact_chain_high_risk_unsafe_cases",
                        "formulaic_double_reviewed_pairs_total",
                        "deterministic_disclosure_cases_total",
                        "omission_misleading_high_risk_cases",
                        "review_double_reviewed_items"):
                self.assertIn(key, fails, f"{sid}:{key}")

    def test_present_modules_below_minimum_fail(self) -> None:
        for sid in ("A", "B"):
            fails = set(self.result["per_set"][sid]["definitive_fail_keys"])
            self.assertIn("risk_classification_high_risk_cases", fails, sid)
            self.assertIn("high_risk_contradicted_cases", fails, sid)
            self.assertIn("high_risk_unknown_cases", fails, sid)

    def test_reads_only_public_aggregates(self) -> None:
        self.assertTrue(self.result["reads_only_public_aggregates"])
        self.assertEqual(self.result["plaintext_contact"], "NONE (只读 class_counts)")

    def test_record_digest_recomputes(self) -> None:
        import sys
        sys.path.insert(0, str(DC / "tools"))
        import receipts
        got = self.result["record_digest"]
        self.assertEqual(got, receipts.canonical_digest(self.result, "record_digest"))


if __name__ == "__main__":
    unittest.main()
