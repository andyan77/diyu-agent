#!/usr/bin/env python3
"""§四.1/§四.2 富标签金标派生测试：富标签 → 逐模块**验证器合规**记录（唯一装配入口）→
真 custody 复算 + generation 链；并证旧简化非合规写入路径已删（v2 goldfreeze）。

纪律：不删断言、不 skip、不降阈值；对**真** spine 验证器 / custody / generation 断言。
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
GEN = _load(TOOLS / "qual_generation.py", "qual_generation")
PRM = _load(TOOLS / "pre_m0_readiness.py", "pre_m0_readiness")
from spine.canonical import digest_json  # noqa: E402
from spine import qualification_data as qd  # noqa: E402

DMD = "d" * 64
FAMS = ("F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
        "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
        "F5_ENTERPRISE_LONG_TERM_TRUST")
ATTRS = {"polarity": "AFFIRMATIVE", "modality": "ASSERTED",
         "time_scope": "PRESENT", "preconditions": None}


def _sp(adjudicated=False):
    def f(cid):
        sp = [{"tag": "A", "reviewer_identity": "SEAT_A::codex-gpt", "reviewer_kind": "AI",
               "model_revision": "gpt-5.6-sol", "prompt_digest": digest_json({"p": "A"})},
              {"tag": "B", "reviewer_identity": "SEAT_B::opus-4-8", "reviewer_kind": "AI",
               "model_revision": "claude-opus-4-8", "prompt_digest": digest_json({"p": "B"})}]
        if adjudicated and cid.split("::")[0].endswith("ADJ"):
            sp.append({"tag": "ADJ", "reviewer_identity": "ADJ::opus-iso", "reviewer_kind": "AI",
                       "model_revision": "claude-opus-4-8", "prompt_digest": digest_json({"p": "ADJ"})})
        return sp
    return f


def _rich(risk="HIGH", ent="CONTRADICTED", ref_present=True, atom_present=True,
          safe=False, obl="NONE", violation=False, mislead=False):
    return {"risk": risk, "entailment": ent, "reference_present": ref_present,
            "reference_attributes": dict(ATTRS), "atom_present": atom_present,
            "atom_partition": [["a1", "a2"], ["a3"]] if atom_present else [["b1"]],
            "safe_to_clear": safe, "disclosure_obligation": obl,
            "disclosure_violation": violation, "misleading": mislead,
            "rationale": "t"}


def _face(cid, sg, fam=FAMS[0], kind="CHALLENGE_VARIANT"):
    return {"case_id": cid, "case_kind": kind, "family_id": fam, "source_group_id": sg}


class TestRichLabelValidation(unittest.TestCase):
    def test_valid_label_passes(self):
        GD.validate_rich_label(_rich(), where="x")  # no raise

    def test_missing_field_rejected(self):
        lab = _rich()
        del lab["safe_to_clear"]
        with self.assertRaises(GD.DerivationError):
            GD.validate_rich_label(lab, where="x")

    def test_bad_risk_enum_rejected(self):
        with self.assertRaises(GD.DerivationError):
            GD.validate_rich_label(_rich(risk="SUPER"), where="x")

    def test_bad_entailment_enum_rejected(self):
        with self.assertRaises(GD.DerivationError):
            GD.validate_rich_label(_rich(ent="MAYBE"), where="x")

    def test_bad_atom_partition_shape_rejected(self):
        lab = _rich()
        lab["atom_partition"] = ["a1", "a2"]  # not list-of-lists
        with self.assertRaises(GD.DerivationError):
            GD.validate_rich_label(lab, where="x")

    def test_bad_reference_attributes_rejected(self):
        lab = _rich()
        lab["reference_attributes"] = {"polarity": "AFFIRMATIVE"}  # missing keys
        with self.assertRaises(GD.DerivationError):
            GD.validate_rich_label(lab, where="x")

    def test_nonbool_flag_rejected(self):
        lab = _rich()
        lab["misleading"] = "yes"
        with self.assertRaises(GD.DerivationError):
            GD.validate_rich_label(lab, where="x")

    def test_bad_obligation_rejected(self):
        with self.assertRaises(GD.DerivationError):
            GD.validate_rich_label(_rich(obl="MYSTERY"), where="x")


class TestPerClaimDerivation(unittest.TestCase):
    def _derive(self, faces, labels, adjudicated=False):
        return GD.derive_perclaim_records(
            faces, labels, dataset_manifest_digest=DMD,
            seat_provenance_for=_sp(adjudicated))

    def test_derived_records_pass_real_validator(self):
        faces = [_face("C0", "sg0"), _face("C1", "sg1", kind="NATURAL")]
        labels = {"C0": _rich(risk="HIGH", ent="CONTRADICTED", obl="SYNTHETIC_IDENTITY_DISCLOSURE",
                              violation=True),
                  "C1": _rich(risk="LOW", ent="SUPPORTED", ref_present=False, atom_present=False,
                              safe=True)}
        out = self._derive(faces, labels)
        recs = out["records"]
        # disclosure only for C0 (obligation != NONE); C1 no disclosure record
        modules = sorted({r["module"] for r in recs})
        self.assertIn("disclosure", modules)
        # per (module, role) group must pass real validate_qualification_records
        groups = {}
        for r in recs:
            groups.setdefault((r["module"], r["record_role"]), []).append(r)
        for (mod, role), grp in groups.items():
            common = sorted(set.intersection(*[set(r["gold_field_names"]) for r in grp]))
            idx = qd.build_qualification_record_index(grp, dataset_manifest_digest=DMD)
            res = qd.validate_qualification_records(
                grp, expected_dataset_manifest_digest=DMD, gold_field_names=common,
                qualification_record_index=idx, require_gold_review_provenance=True)
            self.assertTrue(res["passed"], f"{mod}/{role} validate failed: {res['errors']}")

    def test_disclosure_absent_when_obligation_none(self):
        faces = [_face("C0", "sg0")]
        labels = {"C0": _rich(obl="NONE")}
        recs = self._derive(faces, labels)["records"]
        self.assertNotIn("disclosure", {r["module"] for r in recs})

    def test_cross_module_reuse_registered(self):
        faces = [_face("C0", "sg0")]
        labels = {"C0": _rich()}
        out = self._derive(faces, labels)
        self.assertIn("sg0", out["cross_module_reuse"])
        # one source_group serves multiple modules (reuse), each gold predicate stands alone
        self.assertGreaterEqual(len(out["cross_module_reuse"]["sg0"]), 5)

    def test_missing_resolved_label_rejected(self):
        faces = [_face("C0", "sg0")]
        with self.assertRaises(GD.DerivationError):
            self._derive(faces, {})  # no label for C0

    def test_variants_sharing_source_group_do_not_inflate_effective_N(self):
        # base + 2 variants all sharing sg0, all HIGH risk -> risk_high counts sg0 ONCE.
        faces = [_face("C0::base", "sg0"), _face("C0::v1", "sg0"), _face("C0::v2", "sg0")]
        labels = {f["case_id"]: _rich(risk="HIGH", ent="CONTRADICTED") for f in faces}
        recs = self._derive(faces, labels)["records"]
        pc = CUS.recompute_public_counts(
            recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
            dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"])
        # 3 variants, same source_group -> exactly 1 independent unit for risk_high & contradicted
        self.assertEqual(pc["counts"]["risk_classification_high_risk_cases"], 1)
        self.assertEqual(pc["counts"]["high_risk_contradicted_cases"], 1)

    def test_distinct_source_groups_each_count(self):
        faces = [_face(f"C{i}", f"sg{i}") for i in range(4)]
        labels = {f["case_id"]: _rich(risk="HIGH", ent="CONTRADICTED") for f in faces}
        recs = self._derive(faces, labels)["records"]
        pc = CUS.recompute_public_counts(
            recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
            dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertEqual(pc["counts"]["risk_classification_high_risk_cases"], 4)


class TestReviewDerivation(unittest.TestCase):
    def test_one_item_two_judgments_counts(self):
        units = [{"item_id": "I0", "family_id": FAMS[0], "source_group_id": "rev-I0",
                  "author_identity": "AX",
                  "judgments": [{"reviewer_id": "RV1", "decision": "APPROVE", "hard_veto": False},
                                {"reviewer_id": "RV2", "decision": "REJECT", "hard_veto": True}]}]
        recs = GD.derive_review_records(units, dataset_manifest_digest=DMD,
                                        seat_provenance_for=_sp())
        self.assertEqual(len(recs), 2)
        pc = CUS.recompute_public_counts(
            recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
            dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"])
        self.assertEqual(pc["counts"]["review_double_reviewed_items"], 1)
        self.assertEqual(pc["counts"]["review_judgment_records"], 2)

    def test_bad_decision_rejected(self):
        units = [{"item_id": "I0", "family_id": FAMS[0], "source_group_id": "rev-I0",
                  "author_identity": "AX",
                  "judgments": [{"reviewer_id": "RV1", "decision": "MAYBE", "hard_veto": False}]}]
        with self.assertRaises(GD.DerivationError):
            GD.derive_review_records(units, dataset_manifest_digest=DMD,
                                     seat_provenance_for=_sp())


class TestFormulaicDerivation(unittest.TestCase):
    AX = {"FORMULAIC": {"argument_spine": "SAME", "evidence_progression": "SAME",
                        "limitation_function": "DIFFERENT", "viewpoint_anchor": "SAME",
                        "closing_function": "DIFFERENT", "transformation_depth": "SURFACE_ONLY"},
          "NOT_FORMULAIC": {"argument_spine": "DIFFERENT", "evidence_progression": "DIFFERENT",
                            "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                            "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"},
          "NECESSARY_GRAMMAR": {"argument_spine": "NECESSARY_GRAMMAR", "evidence_progression": "DIFFERENT",
                                "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                                "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"}}

    def _units(self):
        return [{"left_id": "L0", "right_id": "R0", "family_id": FAMS[0], "source_group_id": "p0",
                 "verdict": "FORMULAIC", "axes": self.AX["FORMULAIC"],
                 "necessary_grammar_exception_id": None, "is_formulaic": True,
                 "left_author_identity": "AL0", "right_author_identity": "AR0", "reviewers": ["R1", "R2"]},
                {"left_id": "L1", "right_id": "R1b", "family_id": FAMS[0], "source_group_id": "p1",
                 "verdict": "NOT_FORMULAIC", "axes": self.AX["NOT_FORMULAIC"],
                 "necessary_grammar_exception_id": None, "is_formulaic": False,
                 "left_author_identity": "AL1", "right_author_identity": "AR1", "reviewers": ["R1", "R2"]},
                {"left_id": "L2", "right_id": "R2b", "family_id": FAMS[0], "source_group_id": "p2",
                 "verdict": "NECESSARY_GRAMMAR", "axes": self.AX["NECESSARY_GRAMMAR"],
                 "necessary_grammar_exception_id": "NG-1", "is_formulaic": False,
                 "left_author_identity": "AL2", "right_author_identity": "AR2", "reviewers": ["R1", "R2"]}]

    def test_formulaic_records_valid_and_counted(self):
        out = GD.derive_formulaic_records(self._units(), dataset_manifest_digest=DMD,
                                          seat_provenance_for=_sp(), batch_id="T")
        recs = out["judgments"] + out["adjudications"] + out["candidate_audit"]
        pc = CUS.recompute_public_counts(
            recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
            dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"])
        self.assertEqual(pc["counts"]["formulaic_double_reviewed_pairs_total"], 3)
        self.assertEqual(pc["counts"]["formulaic_positive_pairs_minimum"], 1)
        self.assertEqual(pc["counts"]["formulaic_negative_pairs_minimum"], 1)
        self.assertEqual(pc["counts"]["formulaic_necessary_grammar_pairs_minimum"], 1)
        # registries present + self-consistent digests
        self.assertEqual(out["candidate_manifest"]["manifest_digest"],
                         digest_json({k: v for k, v in out["candidate_manifest"].items()
                                      if k != "manifest_digest"}))

    def test_axes_verdict_inconsistency_rejected(self):
        u = self._units()
        u[0]["verdict"] = "NOT_FORMULAIC"  # axes say FORMULAIC -> inconsistent
        with self.assertRaises(GD.DerivationError):
            GD.derive_formulaic_records(u, dataset_manifest_digest=DMD,
                                        seat_provenance_for=_sp(), batch_id="T")


class TestFullModuleCoverageAndReadiness(unittest.TestCase):
    """九模块齐备时：custody core PASS + module coverage 全在场 + readiness 仅规模/类下限失败。"""

    def _all_records(self):
        faces, labels = [], {}
        for i in range(5):
            fam = FAMS[i % len(FAMS)]
            faces.append(_face(f"N{i}", f"sg{i}", fam, "NATURAL"))
            labels[f"N{i}"] = _rich(risk="LOW", ent="SUPPORTED", ref_present=False,
                                    atom_present=False, safe=True)
            faces.append(_face(f"V{i}", f"sg{i}", fam))
            labels[f"V{i}"] = _rich(risk="HIGH", ent="CONTRADICTED",
                                    obl="EXPLICIT_AUTHORIZATION_BOUNDARY", violation=True,
                                    mislead=True)
        recs = GD.derive_perclaim_records(faces, labels, dataset_manifest_digest=DMD,
                                          seat_provenance_for=_sp())["records"]
        review = GD.derive_review_records(
            [{"item_id": "I0", "family_id": FAMS[0], "source_group_id": "rev-I0",
              "author_identity": "AX",
              "judgments": [{"reviewer_id": "RV1", "decision": "APPROVE", "hard_veto": False},
                            {"reviewer_id": "RV2", "decision": "APPROVE", "hard_veto": False}]}],
            dataset_manifest_digest=DMD, seat_provenance_for=_sp())
        tf = TestFormulaicDerivation()
        formu = GD.derive_formulaic_records(tf._units(), dataset_manifest_digest=DMD,
                                            seat_provenance_for=_sp(), batch_id="T")
        recs += review + formu["judgments"] + formu["adjudications"] + formu["candidate_audit"]
        return recs

    def test_coverage_pass_counts_fail_on_scale(self):
        recs = self._all_records()
        pc = CUS.recompute_public_counts(
            recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
            dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64,
            environmental_flags={k: True for k in CUS._ENV_FLAGS})
        self.assertTrue(pc["custody_binding"]["core_validation_passed"])
        # all 9 modules covered
        for m in PRM.REQUIRED_MODULES:
            self.assertIn(m, pc["module_gold_field_coverage"], m)
            self.assertEqual(sorted(PRM.MODULE_GOLD_FIELDS[m]),
                             pc["module_gold_field_coverage"][m], m)
        # readiness: coverage/governance/families pass; verdict FAIL only on scale/class minimums
        r = PRM.evaluate_set_readiness("A", pc)
        self.assertEqual(r["verdict"], "FAIL")  # small batch under class minimums
        self.assertTrue(r["family_coverage_ok"])
        self.assertTrue(all(c["present"] for c in r["module_gold_field_coverage"].values()))
        self.assertTrue(all(r["governance"].values()))
        # every failing key is a count/class-minimum key (not coverage/governance/family)
        count_keys = set(PRM.COUNT_KEYS) | {
            "deterministic_disclosure_obligation_types_required",
            "known_r5_hard_veto_cases_and_registered_variants_recall"} | set(PRM.M3_MANIFEST_KEYS)
        for k in r["failing_keys"]:
            self.assertIn(k, count_keys, f"unexpected non-scale failing key: {k}")


class TestGoldfreezeIntegration(unittest.TestCase):
    """cmd_goldfreeze 端到端（合成密封 set 目录）：富标签 → v2 合规记录 + 真 generation 链。"""

    def _setup_sealed(self, tmp: Path):
        qr = _load(GTOOLS / "qual_runner.py", "qr_gf_test")
        # 重定向 SEAL/QOPEN/DCC 到 tmp；noop assert_sealed_ignored（测试不写真密封区）
        seal = tmp / "sealed"
        qopen = tmp / "qopen"
        dcc = tmp / "dcc"
        (dcc / "state").mkdir(parents=True)
        (dcc / "state/SEALED_PAYLOAD_DENYLIST.v1.json").write_text(
            json.dumps({"entries": []}), encoding="utf-8")
        qr.SEAL = seal
        qr.QOPEN = qopen
        qr.DCC = dcc
        qr.EVENTS = dcc / "state/QUAL_ORDER_EVENTS.v1.json"
        qr.assert_sealed_ignored = lambda: None
        qopen.mkdir(parents=True)
        sdir = seal / "qual_A"
        for sub in ("labels_A", "labels_B", "adjudication"):
            (sdir / sub).mkdir(parents=True)
        # faces: 1 natural + 1 variant (shared source_group), 1 more variant distinct sg
        faces = [_face("QA-n0", "QA-n0", FAMS[0], "NATURAL"),
                 _face("V-QA-n0-CONT", "QA-n0", FAMS[0]),
                 _face("QA-n1", "QA-n1", FAMS[1], "NATURAL")]
        (sdir / "faces_frozen.json").write_text(json.dumps(faces), encoding="utf-8")
        # labels A/B: agree on n0/n1; DISPUTE on the variant -> adjudicated
        la = {"QA-n0": _rich(risk="LOW", ent="SUPPORTED", ref_present=False, atom_present=False, safe=True),
              "V-QA-n0-CONT": _rich(risk="HIGH", ent="CONTRADICTED"),
              "QA-n1": _rich(risk="MEDIUM", ent="UNKNOWN", ref_present=False, atom_present=False, safe=True)}
        lb = dict(la)
        lb["V-QA-n0-CONT"] = _rich(risk="CRITICAL", ent="CONTRADICTED")  # dispute risk
        for cid, lab in la.items():
            (sdir / "labels_A" / f"{cid}.labels.json").write_text(
                json.dumps([{**lab, "case_id": cid}]), encoding="utf-8")
        for cid, lab in lb.items():
            (sdir / "labels_B" / f"{cid}.labels.json").write_text(
                json.dumps([{**lab, "case_id": cid}]), encoding="utf-8")
        # adjudication resolves the variant dispute
        adj = _rich(risk="HIGH", ent="CONTRADICTED")
        (sdir / "adjudication" / "adj_000.labels.json").write_text(
            json.dumps([{**adj, "case_id": "V-QA-n0-CONT"}]), encoding="utf-8")
        # review + formulaic units for full coverage
        (sdir / "review_units.json").write_text(json.dumps(
            [{"item_id": "I0", "family_id": FAMS[0], "source_group_id": "rev-I0",
              "author_identity": "AX",
              "judgments": [{"reviewer_id": "RV1", "decision": "APPROVE", "hard_veto": False},
                            {"reviewer_id": "RV2", "decision": "APPROVE", "hard_veto": False}]}]),
            encoding="utf-8")
        tf = TestFormulaicDerivation()
        (sdir / "formulaic_units.json").write_text(json.dumps(tf._units()), encoding="utf-8")
        return qr, sdir, qopen

    def test_goldfreeze_produces_compliant_records_and_generation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qr, sdir, qopen = self._setup_sealed(tmp)
            rc = qr.cmd_goldfreeze("A")
            self.assertEqual(rc, 0)
            # v2 receipt written; v1 NOT overwritten (old superseded receipt untouched)
            self.assertTrue((qopen / "QUAL_A_GOLD_FROZEN_RECEIPT.v2.json").is_file())
            receipt = json.loads((qopen / "QUAL_A_GOLD_FROZEN_RECEIPT.v2.json").read_text())
            self.assertTrue(receipt["core_validation_passed"])
            self.assertEqual(receipt["adjudicated_faces"], 1)
            self.assertGreater(receipt["review_records"], 0)
            self.assertGreater(receipt["formulaic_records"], 0)
            self.assertTrue(receipt["generation_id"].startswith("QUAL_A_GEN_"))
            # gold records file is compliant (has source_group_id + gold_review_provenance)
            recs = json.loads((sdir / "gold_records.json").read_text())
            self.assertTrue(all("source_group_id" in r and "gold_review_provenance" in r
                                and "case_digest" in r for r in recs))
            # NO legacy simplified field 'source': "CROSS_MODEL_AGREED" style record survives
            self.assertFalse(any(set(r.keys()) == {"case_id", "case_kind", "family_id",
                                                   "risk", "entailment", "source"} for r in recs))
            # generation chain resolves + binds (pointer->manifest->index self-consistent)
            res = GEN.resolve_active_generation(qopen, "A")
            self.assertEqual(res.get("errors", []), [], res)
            self.assertIsNotNone(res["manifest"])
            self.assertEqual(res["manifest"]["generation_id"], receipt["generation_id"])
            self.assertEqual(res["manifest"]["record_count"], len(recs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
