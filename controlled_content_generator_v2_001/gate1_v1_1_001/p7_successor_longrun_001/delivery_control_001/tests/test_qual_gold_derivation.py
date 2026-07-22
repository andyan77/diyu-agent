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


BASE_SP = [{"tag": "A", "reviewer_identity": "SEAT_A::codex-gpt", "reviewer_kind": "AI",
            "model_revision": "gpt-5.6-sol", "prompt_digest": digest_json({"p": "A"})},
           {"tag": "B", "reviewer_identity": "SEAT_B::opus-4-8", "reviewer_kind": "AI",
            "model_revision": "claude-opus-4-8", "prompt_digest": digest_json({"p": "B"})}]
ADJ_SP = {"tag": "ADJ", "reviewer_identity": "ADJ::opus-iso", "reviewer_kind": "AI",
          "model_revision": "claude-opus-4-8", "prompt_digest": digest_json({"p": "ADJ"})}


def _resolutions(labels, adj_fields_map=None):
    """{cid: rich_label} → {cid: {label, adjudicated_fields}}（默认全 CROSS_MODEL_AGREED）。"""
    afm = adj_fields_map or {}
    return {cid: {"label": lab, "adjudicated_fields": frozenset(afm.get(cid, ()))}
            for cid, lab in labels.items()}


def _sp():
    """review/formulaic 单元席位溯源（恒 A/B 两席；不做字段级仲裁）。"""
    return lambda cid: [dict(s) for s in BASE_SP]


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
    def _derive(self, faces, labels, adj_fields_map=None):
        return GD.derive_perclaim_records(
            faces, _resolutions(labels, adj_fields_map), dataset_manifest_digest=DMD,
            base_seat_provenance=BASE_SP, adj_seat_provenance=ADJ_SP)

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
        self.assertEqual(pc["cluster_counts"]["risk_classification_high_risk_cases"], 4)

    def test_dual_count_distinct_mechanism_raw_gt_cluster(self):
        # §四.6 发起人裁决：同 source_group 两个**不同挑战机制**变体 → raw case N=2（各计覆盖），
        # cluster N=1（同源不增独立簇）。资格报告双披露。
        faces = [{"case_id": "V-a", "case_kind": "CHALLENGE_VARIANT", "family_id": FAMS[0],
                  "source_group_id": "sg0", "challenge_kind": "CONTRADICTION_INJECT"},
                 {"case_id": "V-b", "case_kind": "CHALLENGE_VARIANT", "family_id": FAMS[0],
                  "source_group_id": "sg0", "challenge_kind": "RISK_ELEVATE"}]
        labels = {f["case_id"]: _rich(risk="HIGH", ent="CONTRADICTED") for f in faces}
        recs = self._derive(faces, labels)["records"]
        pc = CUS.recompute_public_counts(
            recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
            dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertEqual(pc["counts"]["risk_classification_high_risk_cases"], 2)          # raw
        self.assertEqual(pc["cluster_counts"]["risk_classification_high_risk_cases"], 1)  # cluster
        self.assertEqual(pc["counts"]["high_risk_contradicted_cases"], 2)
        self.assertEqual(pc["cluster_counts"]["high_risk_contradicted_cases"], 1)

    def test_same_mechanism_variants_no_raw_inflation(self):
        # 同 source_group 同机制的两个变体 → raw N=1（同机制不增覆盖）、cluster N=1
        faces = [{"case_id": "V-a", "case_kind": "CHALLENGE_VARIANT", "family_id": FAMS[0],
                  "source_group_id": "sg0", "challenge_kind": "RISK_ELEVATE"},
                 {"case_id": "V-b", "case_kind": "CHALLENGE_VARIANT", "family_id": FAMS[0],
                  "source_group_id": "sg0", "challenge_kind": "RISK_ELEVATE"}]
        labels = {f["case_id"]: _rich(risk="HIGH", ent="CONTRADICTED") for f in faces}
        recs = self._derive(faces, labels)["records"]
        pc = CUS.recompute_public_counts(
            recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
            dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertEqual(pc["counts"]["risk_classification_high_risk_cases"], 1)
        self.assertEqual(pc["cluster_counts"]["risk_classification_high_risk_cases"], 1)


class TestFieldLevelAgreement(unittest.TestCase):
    """§四.1：逐模块/逐字段一致。结构顺序差异不触发仲裁；某字段分歧只污染消费该字段的模块。"""

    ADJ_ID = "ADJ::opus-iso"

    def _mod(self, recs, cid, mod):
        return next(r for r in recs if r["case_id"] == f"{cid}::{mod}")

    def _identities(self, rec):
        return {rv["reviewer_identity"] for rv in rec["gold_review_provenance"]}

    def _derive_face(self, label, adjf):
        return GD.derive_records_for_face(
            _face("C", "sgC"), label, dataset_manifest_digest=DMD,
            base_seat_provenance=BASE_SP, adj_seat_provenance=ADJ_SP,
            adjudicated_fields=adjf)

    def test_full_agreement_no_adjudication(self):
        a, b = _rich(risk="HIGH"), _rich(risk="HIGH")
        resolved, adjf = GD.resolve_label_fields(a, b, None, where="C")
        self.assertEqual(adjf, frozenset())

    def test_structural_reorder_not_a_dispute(self):
        # same partition/attrs but reordered groups + within-group + object keys -> NOT a dispute
        a = _rich()
        a["atom_partition"] = [["a1", "a2"], ["a3"]]
        a["reference_attributes"] = {"polarity": "AFFIRMATIVE", "modality": "ASSERTED",
                                     "time_scope": "PRESENT", "preconditions": None}
        b = _rich()
        b["atom_partition"] = [["a3"], ["a2", "a1"]]
        b["reference_attributes"] = {"time_scope": "PRESENT", "preconditions": None,
                                     "modality": "ASSERTED", "polarity": "AFFIRMATIVE"}
        self.assertEqual(GD.field_disputes(a, b), [])
        resolved, adjf = GD.resolve_label_fields(a, b, None, where="C")  # no adjudication needed
        self.assertEqual(adjf, frozenset())

    def test_atom_partition_dispute_isolated_to_atomization(self):
        a = _rich(risk="HIGH", ent="CONTRADICTED")
        a["atom_partition"] = [["a1", "a2"]]
        b = _rich(risk="HIGH", ent="CONTRADICTED")
        b["atom_partition"] = [["a1"], ["a2"]]  # genuinely different grouping
        adj = _rich(risk="HIGH", ent="CONTRADICTED")
        adj["atom_partition"] = [["a1"], ["a2"]]
        resolved, adjf = GD.resolve_label_fields(a, b, adj, where="C")
        self.assertEqual(adjf, frozenset({"atom_partition"}))
        recs = self._derive_face(resolved, adjf)
        atom = self._mod(recs, "C", "claim_atomization")
        self.assertEqual(atom["agreement_status"], "FIELD_ADJUDICATED")
        self.assertIn(self.ADJ_ID, self._identities(atom))
        self.assertEqual(len(atom["gold_review_provenance"]), 3)
        # risk & entailment agreed -> stay CROSS_MODEL_AGREED (rule 5)
        for m in ("risk_classification", "entailment"):
            r = self._mod(recs, "C", m)
            self.assertEqual(r["agreement_status"], "CROSS_MODEL_AGREED", m)
            self.assertNotIn(self.ADJ_ID, self._identities(r))
            self.assertEqual(len(r["gold_review_provenance"]), 2)

    def test_risk_dispute_taints_only_risk_consuming_modules(self):
        a = _rich(risk="HIGH", ent="CONTRADICTED", obl="SYNTHETIC_IDENTITY_DISCLOSURE", violation=True)
        b = _rich(risk="CRITICAL", ent="CONTRADICTED", obl="SYNTHETIC_IDENTITY_DISCLOSURE", violation=True)
        adj = _rich(risk="HIGH", ent="CONTRADICTED", obl="SYNTHETIC_IDENTITY_DISCLOSURE", violation=True)
        resolved, adjf = GD.resolve_label_fields(a, b, adj, where="C")
        self.assertEqual(adjf, frozenset({"risk"}))
        recs = self._derive_face(resolved, adjf)
        by_mod = {r["case_id"].split("::")[1]: r for r in recs}
        for m in ("reference_extraction", "claim_atomization", "risk_classification",
                  "entailment", "fact_chain", "omission"):
            self.assertEqual(by_mod[m]["agreement_status"], "FIELD_ADJUDICATED", m)
            self.assertIn("risk", by_mod[m]["adjudicated_fields"], m)
            self.assertIn(self.ADJ_ID, self._identities(by_mod[m]), m)
        # disclosure does NOT consume risk -> agreed
        self.assertEqual(by_mod["disclosure"]["agreement_status"], "CROSS_MODEL_AGREED")
        self.assertNotIn(self.ADJ_ID, self._identities(by_mod["disclosure"]))

    def test_unresolved_field_raises(self):
        a, b = _rich(risk="HIGH"), _rich(risk="LOW")
        with self.assertRaises(GD.DerivationError):
            GD.resolve_label_fields(a, b, None, where="C")  # risk disputed, no adj
        with self.assertRaises(GD.DerivationError):
            GD.resolve_label_fields(a, b, {"entailment": "SUPPORTED"}, where="C")  # adj lacks risk

    def test_field_to_modules_mapping_consistent(self):
        # every rich-label field maps to >=1 consuming module; risk is multi-module
        for f in GD.RICH_LABEL_FIELDS:
            self.assertTrue(GD.FIELD_TO_MODULES[f], f)
        self.assertGreaterEqual(len(GD.FIELD_TO_MODULES["risk"]), 5)
        self.assertEqual(GD.FIELD_TO_MODULES["entailment"], ("entailment",))


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

    def _unit(self, left, right, sg, verdict, exc=None):
        # 双席一致（同 axes/verdict）→ final=该 axes、无仲裁席（对齐 spine requires_adjudicator 口径）
        axes = self.AX[verdict]
        return {"left_id": left, "right_id": right, "family_id": FAMS[0], "source_group_id": sg,
                "left_author_identity": f"AL::{sg}", "right_author_identity": f"AR::{sg}",
                "necessary_grammar_exception_id": exc, "is_formulaic": verdict == "FORMULAIC",
                "final_verdict": verdict, "final_axes": axes,
                "adjudicator_identity": None, "adjudication_evidence_digest": None,
                "judgments": [{"reviewer_id": "REVIEWER_A::codex-gpt", "axes": axes, "verdict": verdict},
                              {"reviewer_id": "REVIEWER_B::opus-4-8", "axes": axes, "verdict": verdict}]}

    def _units(self):
        return [self._unit("L0", "R0", "p0", "FORMULAIC"),
                self._unit("L1", "R1b", "p1", "NOT_FORMULAIC"),
                self._unit("L2", "R2b", "p2", "NECESSARY_GRAMMAR", exc="NG-1")]

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
        u[0]["final_verdict"] = "NOT_FORMULAIC"  # final_axes say FORMULAIC -> inconsistent
        with self.assertRaises(GD.DerivationError):
            GD.derive_formulaic_records(u, dataset_manifest_digest=DMD,
                                        seat_provenance_for=_sp(), batch_id="T")

    def test_per_reviewer_verdict_disagreement_flows_to_judgments(self):
        # two reviewers with DIFFERENT axes/verdict -> judgment records carry each own verdict
        u = self._unit("LX", "RX", "px", "FORMULAIC")
        u["judgments"][1] = {"reviewer_id": "REVIEWER_B::opus-4-8",
                             "axes": self.AX["NOT_FORMULAIC"], "verdict": "NOT_FORMULAIC"}
        # verdicts disagree -> must supply adjudicator identity + evidence + final
        u["adjudicator_identity"] = "ADJ::opus-4-8-isolated"
        u["adjudication_evidence_digest"] = digest_json({"x": 1})
        out = GD.derive_formulaic_records([u], dataset_manifest_digest=DMD,
                                          seat_provenance_for=_sp(), batch_id="T")
        jverdicts = sorted(r["verdict"] for r in out["judgments"])
        self.assertEqual(jverdicts, ["FORMULAIC", "NOT_FORMULAIC"])


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
        recs = GD.derive_perclaim_records(
            faces, _resolutions(labels), dataset_manifest_digest=DMD,
            base_seat_provenance=BASE_SP, adj_seat_provenance=ADJ_SP)["records"]
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
        # §四.6：cluster_power:* 亦属 scale 失败（cluster N 不足），非 coverage/governance/family。
        count_keys = set(PRM.COUNT_KEYS) | {
            "deterministic_disclosure_obligation_types_required",
            "known_r5_hard_veto_cases_and_registered_variants_recall"} | set(PRM.M3_MANIFEST_KEYS)
        for k in r["failing_keys"]:
            if k.startswith("cluster_power:"):
                self.assertIn(k.split(":", 1)[1], count_keys, k)
                continue
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

    def test_goldfreeze_blocks_when_dispute_unadjudicated(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qr, sdir, qopen = self._setup_sealed(tmp)
            # remove the adjudication → the risk dispute on the variant is now unresolved
            (sdir / "adjudication" / "adj_000.labels.json").unlink()
            with self.assertRaises(SystemExit):
                qr.cmd_goldfreeze("A")


if __name__ == "__main__":
    unittest.main(verbosity=2)
