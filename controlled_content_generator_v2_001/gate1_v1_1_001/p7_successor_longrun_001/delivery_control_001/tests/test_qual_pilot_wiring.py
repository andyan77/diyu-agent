#!/usr/bin/env python3
"""§四.5 pilot 真 review/formulaic 接线测试（seat 调用 mock；真 RF 子管线 + 真 GD derive +
真 custody core 校验 + 真 spine 一致门）。

目的：在 §五 真付费跑 pilot 前，用零成本 mock 证 pilot 已把确定性占位换成**真子管线接线**，
且产出记录过真 custody core 校验、per-reviewer verdict/2-judgment schema 正确。纪律：不删断言、
不 skip、不降阈值；断言直打真验证器返回。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(P7 / "m3_data_supply_001/gold/tools"))
sys.path.insert(0, str(P7 / "m3_data_supply_001/tools"))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


CUS = _load(P7 / "m3_data_supply_001/tools/qual_custody_recompute.py", "qual_custody_recompute")
PILOT = _load(P7 / "m3_data_supply_001/tools/qual_pilot.py", "qual_pilot_wiring")

DMD = "d" * 64
FAMS = PILOT.FAMS
AX = {"FORMULAIC": {"argument_spine": "SAME", "evidence_progression": "SAME",
                    "limitation_function": "DIFFERENT", "viewpoint_anchor": "SAME",
                    "closing_function": "DIFFERENT", "transformation_depth": "SURFACE_ONLY"},
      "NOT_FORMULAIC": {"argument_spine": "DIFFERENT", "evidence_progression": "DIFFERENT",
                        "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                        "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"}}


def _bases():
    return [{"case_id": f"B{i}", "family_id": FAMS[i], "source_group_id": f"sg{i}",
             "claim_text": f"claim text {i}", "claim_boundary": "", "authorization_scope": "",
             "source_summary_a": "", "source_summary_b": ""} for i in range(5)]


def _variants():
    # base0 承载 2 变体（同 source_group）；其余各 1 → 6 变体 → 3 formulaic pair
    v = [{"case_id": "B0-V0", "source_group_id": "B0", "family_id": FAMS[0], "claim_text": "v0"},
         {"case_id": "B0-V1", "source_group_id": "B0", "family_id": FAMS[0], "claim_text": "v1"}]
    for i in range(1, 5):
        v.append({"case_id": f"B{i}-V", "source_group_id": f"B{i}",
                  "family_id": FAMS[i], "claim_text": f"v{i}"})
    return v


class PilotRealSubpipelineWiring(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        PILOT.PILOT_SEAL = tmp / "pilot_A"
        PILOT.PILOT_QUAL = tmp / "qual/pilot"
        PILOT.PILOT_SEAL.mkdir(parents=True, exist_ok=True)
        self._real_attempt = PILOT.L.attempt_call

    def tearDown(self):
        PILOT.L.attempt_call = self._real_attempt
        self._tmp.cleanup()

    def _patch(self, review_a, review_b, form_a, form_b, form_adj):
        def fake(prompt, ok, raw_dir, stem, registry, meta, carrier="claude"):
            if stem.startswith("review"):
                tab = review_a if carrier == "codex" else review_b
                rows = [{"item_id": iid, "decision": d, "hard_veto": hv, "rationale": "r"}
                        for iid, (d, hv) in tab.items()]
            elif stem == "formaxis_adj":
                rows = [{"pair_ref": ref, "axes": ax, "rationale": "r"}
                        for ref, ax in form_adj.items()]
            else:  # formaxis_A / formaxis_B
                tab = form_a if carrier == "codex" else form_b
                rows = [{"pair_ref": ref, "axes": ax, "rationale": "r"}
                        for ref, ax in tab.items()]
            return rows if ok(rows) else None
        PILOT.L.attempt_call = fake

    def test_review_and_formulaic_real_wiring(self):
        bases, variants = _bases(), _variants()
        items = PILOT._build_review_items(bases)
        pairs = PILOT._build_formulaic_pairs(variants)
        self.assertEqual(len(items), 5)
        self.assertEqual(len(pairs), 3)  # B0 同源对 + 2 跨 base 对
        iid = [it["item_id"] for it in items]
        pref = [p["pair_ref"] for p in pairs]

        review_a = {iid[0]: ("APPROVE", False), iid[1]: ("APPROVE", False),
                    iid[2]: ("APPROVE", False), iid[3]: ("REJECT", False), iid[4]: ("REJECT", True)}
        review_b = dict(review_a)
        review_b[iid[1]] = ("REJECT", False)  # 1 项分歧 → adjudication_rate=1/5
        form_a = {pref[0]: AX["FORMULAIC"], pref[1]: AX["NOT_FORMULAIC"], pref[2]: AX["FORMULAIC"]}
        form_b = {pref[0]: AX["FORMULAIC"], pref[1]: AX["NOT_FORMULAIC"], pref[2]: AX["NOT_FORMULAIC"]}
        form_adj = {pref[2]: AX["FORMULAIC"]}  # P2 分歧 → 仲裁 → FORMULAIC
        self._patch(review_a, review_b, form_a, form_b, form_adj)

        rev = PILOT._run_review(items, DMD)
        self.assertEqual(len(rev["units"]), 5)
        for u in rev["units"]:
            self.assertEqual(len(u["judgments"]), 2)
            self.assertNotIn(u["author_identity"], {j["reviewer_id"] for j in u["judgments"]})
        self.assertEqual(rev["report"]["double_reviewed_item_count"], 5)
        self.assertEqual(rev["report"]["adjudication_rate"], round(1 / 5, 4))
        self.assertIn("review_calibration", rev["report"]["gate_source"])

        form = PILOT._run_formulaic(pairs, DMD)
        self.assertEqual(form["adjudicated_pairs"], 1)
        self.assertEqual(len(form["units"]), 3)
        for u in form["units"]:
            self.assertEqual(len(u["judgments"]), 2)
            for j in u["judgments"]:
                self.assertIn("verdict", j)  # per-reviewer verdict（真 schema，非旧占位）
        self.assertEqual(form["report"]["final_verdict_distribution"],
                         {"FORMULAIC": 2, "NOT_FORMULAIC": 1})
        self.assertEqual(form["report"]["raw_agreement"], 2 / 3)

        # 真 custody core 校验：review + formulaic 记录合并入库均过 core validation
        recs = list(rev["records"])
        for k in ("judgments", "adjudications", "candidate_audit"):
            recs += form["derived"][k]
        pc = CUS.recompute_public_counts(
            recs, set_id="A", active_generation_id="QUAL_A_GEN_T",
            dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"])
        self.assertEqual(pc["counts"]["review_double_reviewed_items"], 5)
        self.assertEqual(pc["counts"]["formulaic_double_reviewed_pairs_total"], 3)
        self.assertEqual(pc["counts"]["formulaic_positive_pairs_minimum"], 2)

    def test_env_flags_derived_from_real_membership_and_dev(self):
        # §四.7：A/B/DEV 互斥旗标从真源 membership + DEV_PARTITION 派生（非硬写 True）
        for s in ("A", "B"):
            fl = PILOT._env_flags(s)
            self.assertTrue(fl["ab_mutually_exclusive"])  # QUAL_A ∩ QUAL_B == ∅
            self.assertTrue(fl["dev_isolation"])          # 本套 ∩ DEV_groups == ∅
            self.assertEqual(set(fl), set(CUS._ENV_FLAGS))

    def test_known_r5_binding_completeness(self):
        # §5.4：已知 R5 硬否决输入+注册变体全在 faces → completeness=1.0；缺一 → <1.0
        variants = [{"case_id": "V-CONT", "source_group_id": "B0", "family_id": FAMS[0],
                     "challenge_kind": "CONTRADICTION_INJECT", "claim_text": "c"},
                    {"case_id": "V-NEG", "source_group_id": "B1", "family_id": FAMS[1],
                     "challenge_kind": "LEGAL_NEGATIVE_CONTROL", "claim_text": "n"}]
        faces = [{"case_id": "V-CONT"}, {"case_id": "V-NEG"}]
        m, comp = PILOT._bind_known_r5(faces, variants, "A")
        self.assertEqual(comp, 1.0)  # 唯一硬否决输入 V-CONT 已绑定；负控不计入 known
        self.assertTrue(m["all_inputs_bound_in_faces"])
        self.assertEqual(m["known_r5_hard_veto_input_cases"], ["V-CONT"])
        # 缺失硬否决输入 → 不完备
        _, comp2 = PILOT._bind_known_r5([{"case_id": "V-NEG"}], variants, "A")
        self.assertLess(comp2, 1.0)

    def test_freeze_cost_inputs_single_source(self):
        # §四.7：冻结费率卡 + expected manifest；成本唯一以 registry 重算，两文件在盘
        (PILOT.PILOT_QUAL).mkdir(parents=True, exist_ok=True)
        reg = PILOT.PILOT_SEAL / "REGISTRY.jsonl"
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text('{"cost_usd": 0.5, "duration_ms": 10}\n'
                       '{"cost_usd": 0.25, "duration_ms": 5}\n', encoding="utf-8")
        out = PILOT._freeze_cost_inputs("A", reg)
        self.assertEqual(out["cost_rate_cards"], 1)
        self.assertEqual(out["cost_expected_event_manifests"], 1)
        self.assertEqual(out["unified_cost"]["total_usd"], 0.75)  # registry 重算
        self.assertEqual(out["expected_manifest"]["reconciled_against_registry"]["total_usd"], 0.75)
        self.assertTrue((PILOT.PILOT_QUAL / "RATE_CARD_A.v1.json").is_file())
        self.assertTrue((PILOT.PILOT_QUAL / "EXPECTED_COST_MANIFEST_A.v1.json").is_file())

    def test_cached_call_no_double_pay(self):
        # _mk_cached_call：首次调用付费+落缓存；二次同 stem 命中缓存不再调 attempt_call
        calls = {"n": 0}

        def fake(prompt, ok, raw_dir, stem, registry, meta, carrier="claude"):
            calls["n"] += 1
            rows = [{"item_id": "X", "decision": "APPROVE", "hard_veto": False}]
            return rows if ok(rows) else None
        PILOT.L.attempt_call = fake
        call = PILOT._mk_cached_call("claude", "review", 1)
        ok = lambda r: isinstance(r, list) and r and r[0].get("item_id") == "X"
        r1 = call("PROMPT", ok, "review_A")
        r2 = call("PROMPT", ok, "review_A")
        self.assertEqual(r1, r2)
        self.assertEqual(calls["n"], 1)  # 二次命中缓存


if __name__ == "__main__":
    unittest.main(verbosity=2)
