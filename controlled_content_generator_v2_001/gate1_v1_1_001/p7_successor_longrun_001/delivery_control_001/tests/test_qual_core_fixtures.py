#!/usr/bin/env python3
"""§5.2 九通道 core fixture 测试：证明「装配 → 真验证器」端到端贯通（R3 批量前置门）。

纪律：不删断言、不 skip、不降阈值。全部对**真** spine 验证器断言，非重实现。
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

sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(TOOLS))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


fx = _load(TOOLS / "qual_core_fixtures.py", "qual_core_fixtures")
cust = _load(TOOLS / "qual_custody_recompute.py", "qual_custody_recompute")
prm = _load(TOOLS / "pre_m0_readiness.py", "pre_m0_readiness")
from spine import formulaic, m0  # noqa: E402
from spine import qualification_data as qd  # noqa: E402

ENV = {k: True for k in cust._ENV_FLAGS}
_M0_MODULE = {c: s["m0_module"] for c, s in fx.GOLD_CHANNELS.items()}
_M0_MODULE["review_calibration"] = "review_calibration"
_M0_MODULE["formulaic"] = "formulaic_construct"


def _all_records():
    core = fx.build_core_gold_records()
    mb = fx.build_formulaic_minibatch()
    form = mb["judgments"] + mb["adjudications"] + mb["candidate_audit"]
    return core, mb, core + form


class QualCoreFixtures(unittest.TestCase):

    def test_nine_channel_records_pass_custody_core_and_coverage(self) -> None:
        _core, _mb, records = _all_records()
        pc = cust.recompute_public_counts(
            records, set_id="A", active_generation_id="QUAL_A_GEN_R3_001",
            dataset_manifest_digest=fx.DMD, faces_sha256="f" * 64, gold_sha256="0" * 64,
            environmental_flags=ENV, known_r5_input_binding_completeness=1.0)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"][:8])
        cov = pc["module_gold_field_coverage"]
        for mod in prm.REQUIRED_MODULES:
            needed = set(prm.MODULE_GOLD_FIELDS[mod])
            self.assertTrue(needed <= set(cov.get(mod, [])),
                            f"{mod} 缺 gold 覆盖 {sorted(needed - set(cov.get(mod, [])))}")

    def test_every_record_role_maps_to_m0_minimum(self) -> None:
        _core, _mb, records = _all_records()
        for rec in records:
            m0mod = _M0_MODULE[rec["module"]]
            self.assertIn(rec["record_role"], m0.MODULE_RECORD_ROLE_MINIMUMS[m0mod],
                          f"{rec['module']}/{rec['record_role']} 非 m0 合法角色")

    def test_each_gold_record_passes_validate_qualification_records(self) -> None:
        core = fx.build_core_gold_records()
        for rec in core:
            idx = qd.build_qualification_record_index([rec], dataset_manifest_digest=fx.DMD)
            res = qd.validate_qualification_records(
                [rec], expected_dataset_manifest_digest=fx.DMD,
                gold_field_names=rec["gold_field_names"],
                qualification_record_index=idx, require_gold_review_provenance=True)
            self.assertTrue(res["passed"], (rec["case_id"], res["errors"]))

    def test_review_channel_double_reviewed_semantics(self) -> None:
        # review 通道 1 item × 2 reviewer → double_reviewed_items=1, judgment_records=2
        core = fx.build_core_gold_records()
        pc = cust.recompute_public_counts(
            core, set_id="A", active_generation_id="QUAL_A_GEN_R3_001",
            dataset_manifest_digest=fx.DMD, faces_sha256="f" * 64, gold_sha256="0" * 64,
            environmental_flags=ENV, known_r5_input_binding_completeness=1.0)
        self.assertEqual(pc["counts"]["review_double_reviewed_items"], 1)
        self.assertEqual(pc["counts"]["review_judgment_records"], 2)

    def test_formulaic_six_roles_structural_gates_pass(self) -> None:
        mb = fx.build_formulaic_minibatch()
        idx = qd.build_qualification_record_index(
            mb["judgments"] + mb["adjudications"] + mb["candidate_audit"],
            dataset_manifest_digest=fx.DMD)
        res = formulaic.qualify_formulaic_construct(
            mb["judgments"], adjudications=mb["adjudications"],
            candidate_audit_records=mb["candidate_audit"],
            candidate_audit_manifest=mb["candidate_manifest"],
            rubric_manifest=mb["rubric_manifest"],
            necessary_grammar_exceptions=mb["necessary_grammar_exceptions"],
            dataset_manifest_digest=fx.DMD, qualification_record_index=idx)
        g = res["gates"]
        # 三类记录 evidence bound + 形状 + 三注册表 valid + 裁决记录 valid（结构门；计数门 R3-run 补）
        for gate in ("judgment_qualification_evidence_bound",
                     "adjudication_qualification_evidence_bound",
                     "candidate_audit_qualification_evidence_bound",
                     "candidate_audit_shape_valid", "candidate_audit_manifest_valid",
                     "rubric_frozen_before_qualification", "adjudication_records_valid",
                     "review_coverage_valid", "reviewer_independence_valid",
                     "registry_cross_binding"):
            self.assertTrue(g.get(gate), f"formulaic 结构门 {gate} 未过")

    def test_formulaic_registry_roles_present_in_m0(self) -> None:
        # 六角色齐全：judgment/adjudication/candidate_audit（记录）+ 三注册表（结构）
        roles = m0.MODULE_RECORD_ROLE_MINIMUMS["formulaic_construct"]
        for role in ("judgment", "adjudication", "candidate_audit",
                     "candidate_audit_manifest", "rubric_registry",
                     "necessary_grammar_exception_registry"):
            self.assertIn(role, roles)


if __name__ == "__main__":
    unittest.main()
