#!/usr/bin/env python3
"""§六 full runner review/formulaic 生产命令接线测试（mock 语料 + mock 席位）。

证 cmd_review / cmd_formulaic 把真 RF 子管线接进全量 runner，写出 cmd_goldfreeze 可消费的
review_units.json / formulaic_units.json，且经真 GD.derive_* + 真 custody core 校验。
纪律：不删断言、不 skip；断言直打真验证器。miner 真实性（≥300 对 / NG 合法）另由脚本核。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
P7 = HERE.parents[1].parent
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(P7 / "m3_data_supply_001/tools"))
sys.path.insert(0, str(P7 / "m3_data_supply_001/gold/tools"))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


CUS = _load(P7 / "m3_data_supply_001/tools/qual_custody_recompute.py", "qual_custody_recompute")
GD = _load(P7 / "m3_data_supply_001/tools/qual_gold_derivation.py", "qual_gold_derivation")
QR = _load(P7 / "m3_data_supply_001/gold/tools/qual_runner.py", "qual_runner_sub")

FAMS = ("F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
        "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
        "F5_ENTERPRISE_LONG_TERM_TRUST")
AX = {"FORMULAIC": {"argument_spine": "SAME", "evidence_progression": "SAME",
                    "limitation_function": "DIFFERENT", "viewpoint_anchor": "SAME",
                    "closing_function": "DIFFERENT", "transformation_depth": "SURFACE_ONLY"},
      "NOT_FORMULAIC": {"argument_spine": "DIFFERENT", "evidence_progression": "DIFFERENT",
                        "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                        "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"},
      "NG": {"argument_spine": "NECESSARY_GRAMMAR", "evidence_progression": "DIFFERENT",
             "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
             "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"}}


class RunnerSubpipelineWiring(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._saved = (QR.SEAL, QR.REG, QR.assert_sealed_ignored, QR.L.attempt_call,
                       QR._review_items_for_set, QR._formulaic_pairs_for_set)
        QR.SEAL = tmp / "sealed"
        QR.REG = tmp / "reg.jsonl"
        (tmp / "sealed").mkdir(parents=True, exist_ok=True)
        QR.assert_sealed_ignored = lambda: None

    def tearDown(self):
        (QR.SEAL, QR.REG, QR.assert_sealed_ignored, QR.L.attempt_call,
         QR._review_items_for_set, QR._formulaic_pairs_for_set) = self._saved
        self._tmp.cleanup()

    def test_cmd_review_writes_valid_units(self):
        items = [{"item_id": f"QUALA-REV-C{i}", "family_id": FAMS[i % 5],
                  "source_group_id": f"rev-sg{i}", "author_identity": f"GEN_AUTHOR::C{i}",
                  "content": f"content {i}", "claim_boundary": "", "authorization_scope": "",
                  "source_summary_a": "", "source_summary_b": ""} for i in range(6)]
        QR._review_items_for_set = lambda s, target=50: items

        def fake(prompt, ok, raw_dir, stem, reg, meta, carrier="claude"):
            # seat A all APPROVE; seat B rejects one → real disagreement
            rej = (carrier == "claude")
            rows = [{"item_id": it["item_id"],
                     "decision": ("REJECT" if (rej and it["item_id"].endswith("C1")) else "APPROVE"),
                     "hard_veto": False} for it in items]
            return rows if ok(rows) else None
        QR.L.attempt_call = fake

        rc = QR.cmd_review("A", 99)
        self.assertEqual(rc, 0)
        units = json.loads((QR.SEAL / "qual_A" / "review_units.json").read_text())
        self.assertEqual(len(units), 6)
        for u in units:
            self.assertEqual(len(u["judgments"]), 2)
            self.assertNotIn(u["author_identity"], {j["reviewer_id"] for j in u["judgments"]})
        recs = GD.derive_review_records(units, dataset_manifest_digest="d" * 64,
                                        seat_provenance_for=lambda c: QR._base_seat_provenance("a" * 64))
        pc = CUS.recompute_public_counts(recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
                                         dataset_manifest_digest="d" * 64,
                                         faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"])
        self.assertEqual(pc["counts"]["review_double_reviewed_items"], 6)
        self.assertEqual(pc["counts"]["review_judgment_records"], 12)

    def test_cmd_formulaic_writes_valid_units_incl_ng(self):
        def mkpair(ref, exc, sg):
            return {"pair_ref": ref, "left_id": f"{ref}L", "right_id": f"{ref}R",
                    "family_id": FAMS[0], "source_group_id": sg,
                    "left_content": "L", "right_content": "R",
                    "left_author_identity": f"AUL::{ref}", "right_author_identity": f"AUR::{ref}",
                    "necessary_grammar_exception_id": exc}
        pairs = [mkpair("SS-0", "NG-1", "fp0"), mkpair("SS-1", "NG-1", "fp1"),
                 mkpair("CP-0", None, "fp2"), mkpair("CP-1", None, "fp3")]
        QR._formulaic_pairs_for_set = lambda s: pairs
        # verdicts: SS-0=FORMULAIC, SS-1=NECESSARY_GRAMMAR(NG), CP-0/CP-1=NOT_FORMULAIC; seats agree
        table = {"SS-0": AX["FORMULAIC"], "SS-1": AX["NG"],
                 "CP-0": AX["NOT_FORMULAIC"], "CP-1": AX["NOT_FORMULAIC"]}

        def fake(prompt, ok, raw_dir, stem, reg, meta, carrier="claude"):
            rows = [{"pair_ref": p["pair_ref"], "axes": table[p["pair_ref"]]} for p in pairs]
            return rows if ok(rows) else None
        QR.L.attempt_call = fake

        rc = QR.cmd_formulaic("A", 99)
        self.assertEqual(rc, 0)
        units = json.loads((QR.SEAL / "qual_A" / "formulaic_units.json").read_text())
        self.assertEqual(len(units), 4)
        verdicts = sorted(u["final_verdict"] for u in units)
        self.assertEqual(verdicts, ["FORMULAIC", "NECESSARY_GRAMMAR",
                                    "NOT_FORMULAIC", "NOT_FORMULAIC"])
        out = GD.derive_formulaic_records(units, dataset_manifest_digest="d" * 64,
                                          seat_provenance_for=lambda c: QR._base_seat_provenance("a" * 64),
                                          batch_id="TEST")
        recs = out["judgments"] + out["adjudications"] + out["candidate_audit"]
        pc = CUS.recompute_public_counts(recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
                                         dataset_manifest_digest="d" * 64,
                                         faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"])
        self.assertEqual(pc["counts"]["formulaic_double_reviewed_pairs_total"], 4)
        self.assertEqual(pc["counts"]["formulaic_positive_pairs_minimum"], 1)      # SS-0
        self.assertEqual(pc["counts"]["formulaic_negative_pairs_minimum"], 2)      # CP-0/1
        self.assertEqual(pc["counts"]["formulaic_necessary_grammar_pairs_minimum"], 1)  # SS-1


if __name__ == "__main__":
    unittest.main(verbosity=2)
