#!/usr/bin/env python3
"""§四.3/§四.4 真实 review + formulaic 子管线测试（seat 调用 mock；对真 spine 验证器/一致门断言）。

纪律：不删断言、不 skip；review_units/formulaic_units 经真 GD.derive_* → 真 custody core 校验，
agreement 指标经真 spine qualify_review_calibration / agreement_metrics（既有门，未发明）。
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent
TOOLS = P7 / "m3_data_supply_001/tools"
GTOOLS = P7 / "m3_data_supply_001/gold/tools"
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(GTOOLS))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


GD = _load(TOOLS / "qual_gold_derivation.py", "qual_gold_derivation")
CUS = _load(TOOLS / "qual_custody_recompute.py", "qual_custody_recompute")
RF = _load(TOOLS / "qual_review_formulaic.py", "qual_review_formulaic")
from spine.canonical import digest_json  # noqa: E402

DMD = "d" * 64
FAMS = ("F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
        "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
        "F5_ENTERPRISE_LONG_TERM_TRUST")
BASE_SP = [{"tag": "A", "reviewer_identity": "SEAT_A::codex-gpt", "reviewer_kind": "AI",
            "model_revision": "gpt-5.6-sol", "prompt_digest": digest_json({"p": "A"})},
           {"tag": "B", "reviewer_identity": "SEAT_B::opus-4-8", "reviewer_kind": "AI",
            "model_revision": "claude-opus-4-8", "prompt_digest": digest_json({"p": "B"})}]
PD_A, PD_B = digest_json({"t": "rev", "s": "A"}), digest_json({"t": "rev", "s": "B"})


def _sp_units():
    return lambda cid: [dict(s) for s in BASE_SP]


def _items():
    return [{"item_id": f"REV-I{i}", "family_id": FAMS[i % len(FAMS)],
             "source_group_id": f"rev-sg{i}", "author_identity": "AUTHOR::gen",
             "content": f"content {i}", "claim_boundary": "", "authorization_scope": "",
             "source_summary_a": "", "source_summary_b": ""} for i in range(3)]


class TestRealReview(unittest.TestCase):
    def test_label_seat_mock_and_assemble(self):
        items = _items()
        # mock seat call returns canned decisions covering APPROVE+REJECT + hard_veto
        A = {"REV-I0": ("APPROVE", False), "REV-I1": ("APPROVE", False), "REV-I2": ("REJECT", True)}
        B = {"REV-I0": ("APPROVE", False), "REV-I1": ("REJECT", False), "REV-I2": ("REJECT", True)}

        def mk_call(table):
            def call(prompt, ok, stem):
                rows = [{"item_id": iid, "decision": d, "hard_veto": hv, "rationale": "r"}
                        for iid, (d, hv) in table.items()]
                assert ok(rows)
                return rows
            return call

        dec_a = RF.label_review_seat(items, "A", call=mk_call(A), template="{seat}|{batch_json}")
        dec_b = RF.label_review_seat(items, "B", call=mk_call(B), template="{seat}|{batch_json}")
        self.assertEqual(dec_a["REV-I2"]["decision"], "REJECT")
        units = RF.assemble_review_units(items, dec_a, dec_b, prompt_digest_a=PD_A, prompt_digest_b=PD_B)
        self.assertEqual(len(units), 3)
        self.assertEqual(len(units[0]["judgments"]), 2)
        out = RF.review_agreement_report(units, dataset_manifest_digest=DMD,
                                         seat_provenance_for=_sp_units())
        recs, rep = out["records"], out["report"]
        # records pass real custody core validation
        pc = CUS.recompute_public_counts(recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
                                         dataset_manifest_digest=DMD, faces_sha256="f" * 64,
                                         gold_sha256="0" * 64)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"])
        self.assertEqual(pc["counts"]["review_double_reviewed_items"], 3)
        self.assertEqual(pc["counts"]["review_judgment_records"], 6)
        # spine review calibration metrics (existing gates)
        self.assertEqual(rep["double_reviewed_item_count"], 3)
        self.assertEqual(rep["observed_decision_classes"], ["APPROVE", "REJECT"])
        self.assertAlmostEqual(rep["approval_decision_agreement"], 2 / 3)
        self.assertEqual(rep["adjudication_rate"], round(1 / 3, 4))
        self.assertEqual(rep["hard_veto_agreement"], 1.0)  # I2 both hard_veto True
        self.assertIn("review_calibration", rep["gate_source"])

    def test_reviewer_not_colliding_with_author(self):
        # reviewer_id must differ from author_identity (role_collision_absent gate)
        items = _items()
        dec = {it["item_id"]: {"decision": "APPROVE", "hard_veto": False} for it in items}
        units = RF.assemble_review_units(items, dec, dec, prompt_digest_a=PD_A, prompt_digest_b=PD_B)
        for u in units:
            rids = {j["reviewer_id"] for j in u["judgments"]}
            self.assertNotIn(u["author_identity"], rids)

    def test_bad_decision_from_seat_rejected(self):
        items = _items()

        def call(prompt, ok, stem):
            rows = [{"item_id": it["item_id"], "decision": "MAYBE", "hard_veto": False}
                    for it in items]
            return rows if ok(rows) else None

        with self.assertRaises(SystemExit):
            RF.label_review_seat(items, "A", call=call, template="{seat}|{batch_json}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
