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


AX = {"FORMULAIC": {"argument_spine": "SAME", "evidence_progression": "SAME",
                    "limitation_function": "DIFFERENT", "viewpoint_anchor": "SAME",
                    "closing_function": "DIFFERENT", "transformation_depth": "SURFACE_ONLY"},
      "NOT_FORMULAIC": {"argument_spine": "DIFFERENT", "evidence_progression": "DIFFERENT",
                        "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                        "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"},
      "NECESSARY_GRAMMAR": {"argument_spine": "NECESSARY_GRAMMAR", "evidence_progression": "DIFFERENT",
                            "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                            "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"}}


def _pairs():
    def pair(ref, li, ri, sg, exc=None):
        return {"pair_ref": ref, "left_id": li, "right_id": ri, "family_id": FAMS[0],
                "source_group_id": sg, "left_content": "L", "right_content": "R",
                "left_author_identity": f"AUL::{sg}", "right_author_identity": f"AUR::{sg}",
                "necessary_grammar_exception_id": exc}
    return [pair("P0", "l0", "r0", "fsg0"), pair("P1", "l1", "r1", "fsg1"),
            pair("P2", "l2", "r2", "fsg2", exc="NG-1"), pair("P3", "l3", "r3", "fsg3")]


def _axis_call(table):
    def call(prompt, ok, stem):
        rows = [{"pair_ref": ref, "axes": axes, "rationale": "r"} for ref, axes in table.items()]
        return rows if ok(rows) else None
    return call


class TestRealFormulaic(unittest.TestCase):
    def test_full_formulaic_path_with_adjudication(self):
        pairs = _pairs()
        a_tab = {"P0": AX["FORMULAIC"], "P1": AX["NOT_FORMULAIC"],
                 "P2": AX["NECESSARY_GRAMMAR"], "P3": AX["FORMULAIC"]}
        b_tab = {"P0": AX["FORMULAIC"], "P1": AX["NOT_FORMULAIC"],
                 "P2": AX["NECESSARY_GRAMMAR"], "P3": AX["NOT_FORMULAIC"]}  # P3 disagree
        axes_a = RF.label_formulaic_seat(pairs, "A", call=_axis_call(a_tab), template="{seat}|{batch_json}")
        axes_b = RF.label_formulaic_seat(pairs, "B", call=_axis_call(b_tab), template="{seat}|{batch_json}")
        need = RF.pairs_needing_adjudication(pairs, axes_a, axes_b)
        self.assertEqual({p["pair_ref"] for p in need}, {"P3"})
        adj = RF.adjudicate_formulaic_axes(need, axes_a, axes_b,
                                           call=_axis_call({"P3": AX["FORMULAIC"]}),
                                           template="{batch_json}")
        units = RF.assemble_formulaic_units(pairs, axes_a, axes_b, adj,
                                            prompt_digest_a=PD_A, prompt_digest_b=PD_B)
        by_ref = {u["left_id"]: u for u in units}
        self.assertIsNone(by_ref["l0"]["adjudicator_identity"])       # agreed pair, no adjudicator
        self.assertEqual(by_ref["l3"]["adjudicator_identity"], "ADJ::opus-4-8-isolated")  # disputed
        self.assertEqual(by_ref["l3"]["final_verdict"], "FORMULAIC")
        out = RF.formulaic_agreement_report(units, dataset_manifest_digest=DMD,
                                            seat_provenance_for=_sp_units(), batch_id="T")
        recs = out["derived"]["judgments"] + out["derived"]["adjudications"] + out["derived"]["candidate_audit"]
        pc = CUS.recompute_public_counts(recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
                                         dataset_manifest_digest=DMD, faces_sha256="f" * 64,
                                         gold_sha256="0" * 64)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"])
        self.assertEqual(pc["counts"]["formulaic_double_reviewed_pairs_total"], 4)
        self.assertEqual(pc["counts"]["formulaic_positive_pairs_minimum"], 2)      # P0, P3
        self.assertEqual(pc["counts"]["formulaic_negative_pairs_minimum"], 1)      # P1
        self.assertEqual(pc["counts"]["formulaic_necessary_grammar_pairs_minimum"], 1)  # P2
        rep = out["report"]
        self.assertEqual(rep["final_verdict_distribution"],
                         {"FORMULAIC": 2, "NECESSARY_GRAMMAR": 1, "NOT_FORMULAIC": 1})
        self.assertEqual(rep["raw_agreement"], 3 / 4)          # P0,P1,P2 agree; P3 disagree
        self.assertEqual(rep["adjudication_rate"], 1 / 4)      # only P3
        self.assertTrue(rep["reviewer_independence_valid"])
        self.assertIn("formulaic_construct", rep["gate_source"])

    def test_per_reviewer_verdicts_measured_not_forced_identical(self):
        # judgment records must carry each reviewer's OWN verdict (P3 A=FORMULAIC, B=NOT_FORMULAIC)
        pairs = [p for p in _pairs() if p["pair_ref"] == "P3"]
        axes_a = {"P3": AX["FORMULAIC"]}
        axes_b = {"P3": AX["NOT_FORMULAIC"]}
        adj = {"P3": AX["FORMULAIC"]}
        units = RF.assemble_formulaic_units(pairs, axes_a, axes_b, adj,
                                            prompt_digest_a=PD_A, prompt_digest_b=PD_B)
        jverdicts = sorted(j["verdict"] for j in units[0]["judgments"])
        self.assertEqual(jverdicts, ["FORMULAIC", "NOT_FORMULAIC"])

    def test_necessary_grammar_without_exception_rejected(self):
        # NG axis on a pair with no preregistered exception -> SystemExit (post-hoc forbidden)
        pairs = [{"pair_ref": "PX", "left_id": "lx", "right_id": "rx", "family_id": FAMS[0],
                  "source_group_id": "sgx", "left_content": "L", "right_content": "R",
                  "left_author_identity": "AUL", "right_author_identity": "AUR",
                  "necessary_grammar_exception_id": None}]
        with self.assertRaises(SystemExit):
            RF.assemble_formulaic_units(pairs, {"PX": AX["NECESSARY_GRAMMAR"]},
                                        {"PX": AX["NECESSARY_GRAMMAR"]}, {},
                                        prompt_digest_a=PD_A, prompt_digest_b=PD_B)


if __name__ == "__main__":
    unittest.main(verbosity=2)
