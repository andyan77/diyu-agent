#!/usr/bin/env python3
"""R2 测试：容量/构造蓝图 + 9模块 gold schema + 0.4 缺陷修复（k>=2 目标驱动）。

纪律：不删断言、不 skip、不降阈值。plan 目标须≥合同下限；复用覆盖 9 模块；
逐套容量可行；变体构造无固定比例且 k>=2；gold schema 逐模块校验；缺 gold 字段即败。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent
PLAN = P7 / "m3_data_supply_001/plan/CAPACITY_AND_CONSTRUCTION_PLAN.v1.json"
GOLD_SCHEMA = P7 / "m3_data_supply_001/schema/qual_gold_record.v1.schema.json"
CONTRACT = P7 / "eval_audit_spine_001/contract/measurement_qualification.v2.json"

sys.path.insert(0, str(HERE.parent))
import fixture_helpers as fh  # noqa: E402
receipts = fh.receipts


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class CapacityPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.mins = json.loads(CONTRACT.read_text(encoding="utf-8"))["qualification_set_minimums"]

    def test_plan_digest_recomputes(self) -> None:
        self.assertEqual(self.plan["record_digest"],
                         receipts.canonical_digest(self.plan, "record_digest"))

    def test_targets_meet_or_exceed_minimums(self) -> None:
        mt = self.plan["per_set_module_targets"]
        # 抽样若干关键类：target 须 ≥ 合同下限
        checks = [
            ("risk_classification", "high_risk", "risk_classification_high_risk_cases"),
            ("entailment", "high_risk_contradicted", "high_risk_contradicted_cases"),
            ("entailment", "high_risk_unknown", "high_risk_unknown_cases"),
            ("fact_chain", "high_risk_unsafe", "fact_chain_high_risk_unsafe_cases"),
            ("formulaic", "pairs_total", "formulaic_double_reviewed_pairs_total"),
            ("disclosure", "cases_total", "deterministic_disclosure_cases_total"),
            ("omission", "misleading_high_risk", "omission_misleading_high_risk_cases"),
            ("review_calibration", "judgment_records", "review_judgment_records"),
        ]
        for mod, cls_key, min_key in checks:
            tgt = mt[mod][cls_key]["target"]
            self.assertGreaterEqual(tgt, self.mins[min_key], f"{mod}.{cls_key}")

    def test_reuse_archetypes_cover_nine_modules(self) -> None:
        covered = set()
        for a in self.plan["cross_module_reuse_archetypes"]:
            for s in a["serves"]:
                covered.add(s["module"])
        nine = {"reference_extraction", "claim_atomization", "risk_classification",
                "entailment", "fact_chain", "formulaic", "disclosure", "omission",
                "review_calibration"}
        self.assertEqual(covered, nine, covered ^ nine)

    def test_capacity_feasible(self) -> None:
        # §六B：按每类『distinct 合法独立单位供给 ≥ 下限』判可行（非 sum/k2 伪独立虚数）
        f = self.plan["per_set_capacity_feasibility"]
        self.assertTrue(f["feasible"])
        self.assertNotIn("per_set_capacity_natural_plus_k2", f,
                         "k2 变体倍增虚数必须已作废（变体不增有效 N）")
        supply = f["per_set_distinct_claim_source_groups_approx"]
        self.assertIn("legal_independent_unit", f)
        self.assertIn("binomial_denominator_rule", f)
        for cls_key, row in f["per_class_feasibility"].items():
            self.assertGreaterEqual(supply, row["min"], cls_key)
            self.assertGreaterEqual(row["distinct_unit_supply_approx"], row["min"], cls_key)
            self.assertTrue(row["ok"], cls_key)

    def test_variant_construction_no_fixed_ratio_k_ge_2(self) -> None:
        vc = self.plan["variant_construction"]
        self.assertTrue(vc["no_fixed_ratio"])
        self.assertGreaterEqual(vc["k_variants_per_claim"], 2)
        self.assertGreaterEqual(len(vc["kinds"]), 4)
        # §六B：变体只增 RECORD 体量，不增有效独立 N
        self.assertFalse(vc["variants_add_effective_N"])


class GoldSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(GOLD_SCHEMA.read_text(encoding="utf-8"))

    def _validator(self):
        from jsonschema import Draft202012Validator
        return Draft202012Validator(self.schema)

    def _base(self, module: str, role: str = "qualification_case") -> dict:
        return {
            "record_id": f"r-{module}", "module": module, "set": "A",
            "record_role": role, "family_id": "F1_PEOPLE_AND_REAL_SCENE",
            "case_origin": "NATURAL", "visibility_partition": "HIDDEN",
            "source_group_id": "g1", "source_evidence_digest": "a" * 64,
            "gold_field_names": ["gold_risk"], "gold_label_digest": "b" * 64,
            "gold_review_provenance": [
                {"reviewer_id": "seatA", "reviewer_kind": "AI", "role": "SEAT_A"},
                {"reviewer_id": "seatB", "reviewer_kind": "AI", "role": "SEAT_B"}],
        }

    def test_each_module_valid_record_passes(self) -> None:
        try:
            v = self._validator()
        except ImportError:
            self.skipTest("jsonschema unavailable")
        samples = {
            "reference_extraction": {"gold_present": True, "gold_risk": "HIGH",
                "gold_attributes": {"polarity": "affirm", "modality": "assert",
                                    "time_scope": "present", "preconditions": None}},
            "claim_atomization": {"gold_present": True, "gold_risk": "HIGH",
                "gold_atom_partition": [["a1", "a2"], ["a3"]]},
            "risk_classification": {"gold_risk": "CRITICAL"},
            "entailment": {"gold_label": "CONTRADICTED", "gold_risk": "HIGH"},
            "fact_chain": {"gold_risk": "HIGH", "gold_safe_to_clear": False,
                "chain_manifest": {"source_evidence": "x", "reference_assertion": "x",
                    "claim_atom": "x", "risk_classification": "x", "entailment": "x",
                    "final_action": "HARD_VETO"}},
            "disclosure": {"obligation_type": "SYNTHETIC_IDENTITY_DISCLOSURE",
                           "gold_violation": True},
            "omission": {"gold_misleading": True, "gold_risk": "HIGH"},
            "review_calibration": {"item_id": "i1", "decision": "REJECT", "hard_veto": True},
        }
        for module, extra in samples.items():
            rec = self._base(module)
            rec.update(extra)
            errs = list(v.iter_errors(rec))
            self.assertEqual(errs, [], f"{module}: {[e.message for e in errs]}")
        # formulaic judgment role
        fj = self._base("formulaic", "judgment")
        fj.update({"pair_id": "p1", "left_id": "l", "right_id": "r",
                   "axes": {"a": "SAME"}, "verdict": "FORMULAIC"})
        self.assertEqual(list(v.iter_errors(fj)), [])

    def test_missing_module_gold_field_fails(self) -> None:
        try:
            v = self._validator()
        except ImportError:
            self.skipTest("jsonschema unavailable")
        rec = self._base("entailment")
        rec.update({"gold_risk": "HIGH"})  # 缺 gold_label
        self.assertNotEqual(list(v.iter_errors(rec)), [])

    def test_fewer_than_two_reviewers_fails(self) -> None:
        try:
            v = self._validator()
        except ImportError:
            self.skipTest("jsonschema unavailable")
        rec = self._base("risk_classification")
        rec["gold_risk"] = "HIGH"
        rec["gold_review_provenance"] = [rec["gold_review_provenance"][0]]  # 只 1
        self.assertNotEqual(list(v.iter_errors(rec)), [])


class VariantConstructionFix(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qr = _load(P7 / "m3_data_supply_001/gold/tools/qual_runner.py", "qual_runner")
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))

    def _synthetic_by_fam(self) -> dict:
        # 发起人证据身份裁决：face 带证据锚 source_group_id（每 2 claim 共 1 锚 → 测锚去重）。
        def claim(fam, i):
            return {"case_id": f"{fam}-{i}", "family_id": fam, "claim_text": f"t{i}",
                    "source_group_id": f"anchor-{fam}-{i // 2}", "scenario_id": f"scn-{fam}",
                    "claim_boundary": "b", "authorization_scope": "s",
                    "slot_facts": {}, "source_summary_a": "sa", "source_summary_b": "sb",
                    "source_ids": [f"src-{fam}-{i // 2}"], "fact_ids": [f"fac-{fam}-{i // 2}"],
                    "authorization_ids": [f"auth-{fam}-{i // 2}"]}
        return {"F1_PEOPLE_AND_REAL_SCENE":
                [claim("F1_PEOPLE_AND_REAL_SCENE", i) for i in range(200)],
                "F5_ENTERPRISE_LONG_TERM_TRUST":
                [claim("F5_ENTERPRISE_LONG_TERM_TRUST", i) for i in range(20)]}

    def test_breadth_first_every_anchor_gets_high_risk(self) -> None:
        # 发起人裁决 breadth-first：**每个** distinct evidence anchor 各先产 1 条高风险
        # CONTRADICTION_INJECT（cluster N=全锚数≥门），不在部分锚堆两条冒充独立簇。
        by_fam = self._synthetic_by_fam()
        tasks = self.qr._build_variant_tasks(by_fam, "framedigest", self.plan)
        all_anchors = {f["source_group_id"] for fs in by_fam.values() for f in fs}
        contra_anchors = {t["base_source_group_id"] for t in tasks
                          if t["variant_kind"] == "CONTRADICTION_INJECT"}
        self.assertEqual(contra_anchors, all_anchors)  # 全锚各得矛盾（breadth）

    def test_distinct_anchor_mechanism_no_raw_inflation(self) -> None:
        # raw = distinct (anchor, mechanism)：同锚同 mechanism 绝不重复（不虚增 raw 覆盖）。
        by_fam = self._synthetic_by_fam()
        tasks = self.qr._build_variant_tasks(by_fam, "framedigest", self.plan)
        pairs = [(t["base_source_group_id"], t["mechanism"]) for t in tasks]
        self.assertEqual(len(pairs), len(set(pairs)))  # 无重复 (anchor,mechanism)
        ids = [t["variant_id"] for t in tasks]
        self.assertEqual(len(ids), len(set(ids)))       # 变体 id 唯一

    def test_deterministic(self) -> None:
        by_fam = self._synthetic_by_fam()
        t1 = self.qr._build_variant_tasks(by_fam, "fd", self.plan)
        t2 = self.qr._build_variant_tasks(by_fam, "fd", self.plan)
        self.assertEqual([t["variant_id"] for t in t1], [t["variant_id"] for t in t2])

    def test_rejects_plan_without_no_fixed_ratio(self) -> None:
        bad = json.loads(json.dumps(self.plan))
        bad["variant_construction"]["no_fixed_ratio"] = False
        with self.assertRaises(SystemExit):
            self.qr._build_variant_tasks(self._synthetic_by_fam(), "fd", bad)


class CapacityPrecheckMechanical(unittest.TestCase):
    """§五：从**真实**抽样框机械复算每套供给，逐类/逐族与合同下限比较（非只读 plan 静态数）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cap = _load(P7 / "m3_data_supply_001/tools/qual_capacity_precheck.py",
                        "qual_capacity_precheck")
        cls.result = cls.cap.precheck()
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.mins = json.loads(CONTRACT.read_text(encoding="utf-8"))["qualification_set_minimums"]

    def test_verdict_feasible_and_no_insufficient(self) -> None:
        self.assertEqual(self.result["verdict"], "FEASIBLE",
                         self.result["insufficient_classes"])
        self.assertEqual(self.result["insufficient_classes"], [])

    def test_per_set_supply_meets_each_claim_class_minimum(self) -> None:
        for row in self.result["class_rows"]:
            self.assertGreaterEqual(row["per_set_supply"], row["required"],
                                    row["class"])
            self.assertTrue(row["ok"], row["class"])

    def test_frame_digest_bound_to_real_frame(self) -> None:
        frame = json.loads((P7 / "m3_data_supply_001/SAMPLING_FRAME.v1.json"
                            ).read_text(encoding="utf-8"))
        self.assertEqual(self.result["supply"]["frame_digest"], frame["frame_digest"])

    def test_mechanical_supply_matches_plan_order(self) -> None:
        # 机械复算的每套供给 应与 plan 记载的 ~510 同量级（真源一致性）
        mech = self.result["supply"]["per_set_claim_source_group_supply"]
        plan_supply = self.plan["per_set_capacity_feasibility"][
            "per_set_distinct_claim_source_groups_approx"]
        self.assertLessEqual(abs(mech - plan_supply), 20,
                             f"mechanical {mech} vs plan {plan_supply}")

    def test_binding_family_floor(self) -> None:
        # F5 最薄族每套供给 ≥ 每族下限（紧但可行）
        rows = {r["family"]: r for r in self.result["family_rows"]}
        self.assertTrue(rows["F5_ENTERPRISE_LONG_TERM_TRUST"]["ok"])
        self.assertEqual(self.result["supply"]["binding_family"],
                         "F5_ENTERPRISE_LONG_TERM_TRUST")

    def test_variants_do_not_inflate_supply(self) -> None:
        # 独立单位口径必须是 source_group（同源变体不增有效 N）
        self.assertIn("source_group", self.result["independent_unit_rule"])


if __name__ == "__main__":
    unittest.main()
