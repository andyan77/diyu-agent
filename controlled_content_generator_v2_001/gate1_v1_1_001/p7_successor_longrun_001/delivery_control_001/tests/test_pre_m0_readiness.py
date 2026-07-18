#!/usr/bin/env python3
"""R1 PRE_M0 数据就绪硬门测试。

覆盖 Prompt 四/R1「负向测试使用当前旧数据并必须失败；正向完整 fixture 必须通过」，
外加：verdict 手改防伪、模块 gold 覆盖缺失即败、A+B 合并凑数仍败、checker 集成。
纪律：不删断言、不 skip、不降阈值。
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent
TOOL = P7 / "m3_data_supply_001/tools/pre_m0_readiness.py"
SCHEMA = P7 / "m3_data_supply_001/schema/pre_m0_data_readiness.v1.schema.json"

sys.path.insert(0, str(HERE.parent))
import fixture_helpers as fh  # noqa: E402
receipts = fh.receipts


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


prm = _load(TOOL, "pre_m0_readiness")


def _full_counts(set_id: str) -> dict:
    """每键都达标的完整公开聚合 fixture → 应 PASS。"""
    mins = prm.load_minimums()
    counts = {}
    for key in prm.COUNT_KEYS:
        counts[key] = mins[key] + 5  # 略超要求
    coverage = {m: list(prm.MODULE_GOLD_FIELDS[m]) for m in prm.REQUIRED_MODULES}
    return {
        "set": set_id, "counts": counts,
        "deterministic_disclosure_obligation_types_present": 4,
        "known_r5_recall": 1.0,
        "module_gold_field_coverage": coverage,
        "family_coverage": list(prm.FAMILIES),
        "ab_mutually_exclusive": True, "dev_isolation": True,
        "qual_order_ok": True, "sealed_no_leak": True,
        "two_independent_labels_per_record": True,
        "adjudication_on_disagreement": True,
        "faces_sha256": "f" * 64, "gold_sha256": "0" * 64,
    }


class PreM0Readiness(unittest.TestCase):

    # --- 负测：旧真实数据必须 FAIL ---
    def test_old_qual_both_sets_fail(self) -> None:
        for s in ("A", "B"):
            r = prm.evaluate_set_readiness(s, prm.public_counts_from_old_qual(s))
            self.assertEqual(r["verdict"], "FAIL", s)
            self.assertGreater(len(r["failing_keys"]), 10, s)

    # --- 正测：完整 fixture 必须 PASS ---
    def test_full_fixture_passes(self) -> None:
        for s in ("A", "B"):
            r = prm.evaluate_set_readiness(s, _full_counts(s))
            self.assertEqual(r["verdict"], "PASS", (s, r["failing_keys"]))
            self.assertEqual(prm.recompute_verdict(r), "PASS", s)

    def test_missing_one_count_by_one_fails(self) -> None:
        pc = _full_counts("A")
        pc["counts"]["fact_chain_high_risk_unsafe_cases"] -= 6  # 差 1
        r = prm.evaluate_set_readiness("A", pc)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("fact_chain_high_risk_unsafe_cases", r["failing_keys"])

    def test_missing_module_gold_field_fails(self) -> None:
        pc = _full_counts("A")
        pc["module_gold_field_coverage"]["disclosure"] = ["gold_violation"]  # 缺 obligation_type
        r = prm.evaluate_set_readiness("A", pc)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("disclosure", r["failing_keys"])

    def test_governance_flag_false_fails(self) -> None:
        pc = _full_counts("A")
        pc["sealed_no_leak"] = False
        r = prm.evaluate_set_readiness("A", pc)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("governance:sealed_no_leak", r["failing_keys"])

    def test_forged_verdict_pass_recomputes_fail(self) -> None:
        # 手改 verdict:PASS 但 rows 有失败项 → recompute_verdict 必判 FAIL
        r = prm.evaluate_set_readiness("A", prm.public_counts_from_old_qual("A"))
        r["verdict"] = "PASS"
        self.assertEqual(prm.recompute_verdict(r), "FAIL")

    def test_ab_merge_does_not_help(self) -> None:
        # A+B 合并凑数：把两套计数相加当单套 → 仍须逐套判，单套 A 仍 FAIL
        a = prm.public_counts_from_old_qual("A")
        b = prm.public_counts_from_old_qual("B")
        merged = dict(a)
        merged["counts"] = {k: a["counts"].get(k, 0) + b["counts"].get(k, 0)
                            for k in prm.COUNT_KEYS}
        r = prm.evaluate_set_readiness("A", merged)
        # 即便合并，7 缺模块仍 0、gold 覆盖仍缺 → FAIL
        self.assertEqual(r["verdict"], "FAIL")

    # --- schema ---
    def test_pass_receipt_matches_schema(self) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema unavailable")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        r = receipts.close_record(prm.evaluate_set_readiness("A", _full_counts("A")),
                                  "record_digest")
        errs = list(Draft202012Validator(schema).iter_errors(r))
        self.assertEqual(errs, [], [e.message for e in errs])

    # --- 矩阵 ---
    def test_matrix_generation(self) -> None:
        m = prm.build_requirement_matrix()
        self.assertEqual(m["record_digest"],
                         receipts.canonical_digest(m, "record_digest"))
        modules = {e["module"] for e in m["entries"]}
        for mod in prm.REQUIRED_MODULES:
            self.assertIn(mod, modules, mod)
        self.assertEqual(len(m["m3_enforced_count_keys"]), 20)

    # --- checker 集成：真实仓 M3 FINAL 无回执 → FAIL；M2 → pass-through ---
    def test_checker_section_real_repo_m3_fail_m2_passthrough(self) -> None:
        checker = _load(P7 / "checker/p7_master_check.py", "p7_master_check")
        root = P7.parents[2]
        checker.CTX["milestone"] = "M3"
        ok_m3, _ = checker.check_qual_data_readiness(root)
        self.assertFalse(ok_m3, "M3 FINAL 无就绪回执必须 fail-closed")
        checker.CTX["milestone"] = "M2"
        ok_m2, _ = checker.check_qual_data_readiness(root)
        self.assertTrue(ok_m2, "M2 应 pass-through")

    # --- checker 集成：完整 temp 根 + PASS 回执 → PASS；篡改 verdict → FAIL ---
    def test_checker_section_temp_root_pass_and_forgery(self) -> None:
        import tempfile
        checker = _load(P7 / "checker/p7_master_check.py", "p7_master_check2")
        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            p7dir = troot / checker.P7
            tools = p7dir / "m3_data_supply_001/tools"
            qual = p7dir / "m3_data_supply_001/gold/qual"
            dctools = p7dir / "delivery_control_001/tools"
            tools.mkdir(parents=True)
            qual.mkdir(parents=True)
            dctools.mkdir(parents=True)
            shutil.copy(TOOL, tools / "pre_m0_readiness.py")
            shutil.copy(DC / "tools/receipts.py", dctools / "receipts.py")
            for s in ("A", "B"):
                r = receipts.close_record(
                    prm.evaluate_set_readiness(s, _full_counts(s)), "record_digest")
                (qual / f"QUAL_{s}_READINESS_RECEIPT.v1.json").write_text(
                    json.dumps(r, ensure_ascii=False), encoding="utf-8")
            checker.CTX["milestone"] = "M3"
            ok, details = checker.check_qual_data_readiness(troot)
            self.assertTrue(ok, details)
            # 篡改 A 的 verdict 为 FAIL（重算摘要）→ 段必 FAIL
            ra = json.loads((qual / "QUAL_A_READINESS_RECEIPT.v1.json").read_text())
            bad = _full_counts("A")
            bad["counts"]["fact_chain_natural_legal_cases"] = 0
            ra2 = receipts.close_record(prm.evaluate_set_readiness("A", bad), "record_digest")
            (qual / "QUAL_A_READINESS_RECEIPT.v1.json").write_text(
                json.dumps(ra2, ensure_ascii=False), encoding="utf-8")
            ok2, _ = checker.check_qual_data_readiness(troot)
            self.assertFalse(ok2, "一套 FAIL → 段必 FAIL")


if __name__ == "__main__":
    unittest.main()
