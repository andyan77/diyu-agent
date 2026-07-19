#!/usr/bin/env python3
"""§5.1/§5.3 保全直算测试。

证明：
  - 计数由密封记录复算（非调用方输入）；记录级 core 校验闭合。
  - §5.3 cluster-aware：同一 source_group 的多变体在同一分母只计 1 个独立单位。
  - §5.1 反伪造：手改 public_counts（膨胀数字/改摘要）→ verify_binding fail-closed。
  - 篡改记录（摘要失配）→ core 校验失败 → 复算标记不通过。
  - 与 pre_m0_readiness 集成：custody 输出的计数逐键==就绪门读到的 actual。
纪律：不删断言、不 skip、不降阈值。
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


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(TOOLS))
asm = _load(TOOLS / "qual_record_assembly.py", "qual_record_assembly")
cust = _load(TOOLS / "qual_custody_recompute.py", "qual_custody_recompute")
prm = _load(TOOLS / "pre_m0_readiness.py", "pre_m0_readiness")
from spine.canonical import digest_json  # noqa: E402

DMD = "d" * 64
ENV_FLAGS = {"ab_mutually_exclusive": True, "dev_isolation": True,
             "qual_order_ok": True, "sealed_no_leak": True,
             "adjudication_on_disagreement": True}


def _mk(case_id: str, *, module: str, source_group: str, gold_fields: dict,
        payload_extra: dict | None = None, case_origin: str = "CHALLENGE",
        record_role: str = "qualification_case", family: str = "F1_PEOPLE_AND_REAL_SCENE"):
    payload = {"module": module, "family_id": family, "record_role": record_role,
               "case_origin": case_origin, "claim_text": f"text::{case_id}"}
    payload.update(payload_extra or {})
    return asm.assemble_gold_record(
        case_id=case_id, source_group_id=source_group,
        source_evidence_digest=digest_json({"src": source_group, "cid": case_id}),
        dataset_manifest_digest=DMD, gold_fields=gold_fields, payload_fields=payload,
        reviews_meta=[
            {"review_id": f"A-{case_id}", "reviewer_identity": "SEAT_A::codex-gpt",
             "reviewer_kind": "AI", "model_revision": "gpt-5.6-sol",
             "prompt_digest": digest_json({"p": "A"}),
             "evidence_digest": digest_json({"e": case_id, "s": "A"})},
            {"review_id": f"B-{case_id}", "reviewer_identity": "SEAT_B::opus-4-8",
             "reviewer_kind": "AI", "model_revision": "claude-opus-4-8",
             "prompt_digest": digest_json({"p": "B"}),
             "evidence_digest": digest_json({"e": case_id, "s": "B"})}])


def _recompute(records):
    return cust.recompute_public_counts(
        records, set_id="A", active_generation_id="QUAL_A_GEN_R3_001",
        dataset_manifest_digest=DMD, faces_sha256="f" * 64, gold_sha256="0" * 64,
        environmental_flags=ENV_FLAGS, known_r5_recall=1.0)


def _mk_judgment(item_id: str, reviewer_id: str, *, decision: str = "APPROVE",
                 hard_veto: bool = False, submission: str = "s1",
                 source_group: str | None = None):
    """review_calibration judgment 记录（role=judgment；含 item_id/reviewer_id）——§六A 计数。"""
    case_id = f"rc-{item_id}-{reviewer_id}-{submission}"
    payload = {"module": "review_calibration", "record_role": "judgment",
               "family_id": "F1_PEOPLE_AND_REAL_SCENE", "case_origin": "NATURAL",
               "item_id": item_id, "reviewer_id": reviewer_id,
               "author_identity": "AUTHOR_X", "submission_tag": submission,
               "reviewer_provenance": {"reviewer_identity": reviewer_id,
                                       "reviewer_kind": "AI", "model_revision": "m1",
                                       "prompt_digest": digest_json({"p": reviewer_id})}}
    return asm.assemble_gold_record(
        case_id=case_id, source_group_id=source_group or f"sg-{item_id}",
        source_evidence_digest=digest_json({"item": item_id}),
        dataset_manifest_digest=DMD,
        gold_fields={"decision": decision, "hard_veto": hard_veto},
        payload_fields=payload,
        reviews_meta=[
            {"review_id": f"A-{case_id}", "reviewer_identity": "SEAT_A::codex-gpt",
             "reviewer_kind": "AI", "model_revision": "gpt-5.6-sol",
             "prompt_digest": digest_json({"p": "A"}),
             "evidence_digest": digest_json({"e": case_id, "s": "A"})},
            {"review_id": f"B-{case_id}", "reviewer_identity": "SEAT_B::opus-4-8",
             "reviewer_kind": "AI", "model_revision": "claude-opus-4-8",
             "prompt_digest": digest_json({"p": "B"}),
             "evidence_digest": digest_json({"e": case_id, "s": "B"})}])


class QualCustodyRecompute(unittest.TestCase):

    def test_counts_recomputed_and_core_valid(self) -> None:
        records = [
            _mk("QA-e-0", module="entailment", source_group="sg-0",
                gold_fields={"gold_label": "CONTRADICTED", "gold_risk": "HIGH"}),
            _mk("QA-e-1", module="entailment", source_group="sg-1",
                gold_fields={"gold_label": "CONTRADICTED", "gold_risk": "CRITICAL"}),
            _mk("QA-r-0", module="risk_classification", source_group="sg-2",
                gold_fields={"gold_risk": "HIGH"}),
        ]
        pc = _recompute(records)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"])
        self.assertEqual(pc["counts"]["high_risk_contradicted_cases"], 2)
        self.assertEqual(pc["counts"]["risk_classification_high_risk_cases"], 1)
        self.assertEqual(pc["custody_binding"]["record_count"], 3)

    def test_cluster_aware_dedup_same_source(self) -> None:
        # 3 条同 source_group 的 high-risk contradicted 变体 → distinct 单位=1（非 3）
        records = [
            _mk(f"QA-v-{k}", module="entailment", source_group="sg-shared",
                gold_fields={"gold_label": "CONTRADICTED", "gold_risk": "HIGH"},
                payload_extra={"variant_k": k})
            for k in range(3)]
        pc = _recompute(records)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"])
        self.assertEqual(pc["counts"]["high_risk_contradicted_cases"], 1,
                         "同源 3 变体只能计 1 个独立统计单位（§5.3）")
        # 而记录数仍为 3（记录在场，但不虚增独立 N）
        self.assertEqual(pc["custody_binding"]["record_count"], 3)

    def test_verify_binding_genuine_passes(self) -> None:
        records = [_mk("QA-e-0", module="entailment", source_group="sg-0",
                       gold_fields={"gold_label": "CONTRADICTED", "gold_risk": "HIGH"})]
        pc = _recompute(records)
        self.assertEqual(cust.verify_binding(pc, records), [])

    def test_forged_inflated_counts_rejected(self) -> None:
        # §5.1 反伪造：手改 public_counts 膨胀数字 → 与密封复算不符 → fail-closed
        records = [_mk("QA-e-0", module="entailment", source_group="sg-0",
                       gold_fields={"gold_label": "CONTRADICTED", "gold_risk": "HIGH"})]
        pc = _recompute(records)
        pc["counts"]["high_risk_contradicted_cases"] = 999
        errs = cust.verify_binding(pc, records)
        self.assertIn("counts_mismatch_vs_recompute", errs)

    def test_forged_binding_digest_rejected(self) -> None:
        records = [_mk("QA-e-0", module="entailment", source_group="sg-0",
                       gold_fields={"gold_label": "CONTRADICTED", "gold_risk": "HIGH"})]
        pc = _recompute(records)
        pc["custody_binding"]["qualification_index_digest"] = "e" * 64
        errs = cust.verify_binding(pc, records)
        self.assertTrue(any("qualification_index_digest_mismatch" in e for e in errs), errs)

    def test_tampered_record_fails_core_validation(self) -> None:
        records = [_mk("QA-e-0", module="entailment", source_group="sg-0",
                       gold_fields={"gold_label": "CONTRADICTED", "gold_risk": "HIGH"})]
        records[0] = dict(records[0])
        records[0]["gold_risk"] = "LOW"  # 篡改 gold 字段但不重算摘要 → 摘要失配
        pc = _recompute(records)
        self.assertFalse(pc["custody_binding"]["core_validation_passed"])
        errs = cust.verify_binding(pc, records)
        self.assertTrue(any(e.startswith("core_validation_failed") for e in errs), errs)

    def test_integration_with_pre_m0_readiness(self) -> None:
        # custody 计数逐键==就绪门读到的 actual（两工具契约对齐；小 fixture 判 FAIL 合理）
        records = [
            _mk("QA-e-0", module="entailment", source_group="sg-0",
                gold_fields={"gold_label": "CONTRADICTED", "gold_risk": "HIGH"}),
            _mk("QA-r-0", module="risk_classification", source_group="sg-1",
                gold_fields={"gold_risk": "CRITICAL"}),
        ]
        pc = _recompute(records)
        readiness = prm.evaluate_set_readiness("A", pc)
        by_key = {row["key"]: row for row in readiness["rows"]}
        self.assertEqual(by_key["high_risk_contradicted_cases"]["actual"],
                         pc["counts"]["high_risk_contradicted_cases"])
        self.assertEqual(by_key["risk_classification_high_risk_cases"]["actual"],
                         pc["counts"]["risk_classification_high_risk_cases"])
        # 小 fixture 远低于下限 → FAIL（就绪门不因 custody 来源而放松）
        self.assertEqual(readiness["verdict"], "FAIL")

    # ---- §六A：review judgment 计数（40 item / 80 judgment 记录） ----

    def test_review_counts_items_and_judgments_40x2_is_80(self) -> None:
        records = [_mk_judgment(f"I{i:02d}", rv)
                   for i in range(40) for rv in ("RV1", "RV2")]
        pc = _recompute(records)
        self.assertTrue(pc["custody_binding"]["core_validation_passed"],
                        pc["custody_binding"]["core_validation_errors"][:5])
        self.assertEqual(pc["counts"]["review_double_reviewed_items"], 40,
                         "40 个 distinct item_id")
        self.assertEqual(pc["counts"]["review_judgment_records"], 80,
                         "40 item × 2 reviewer = 80 judgment 记录（禁按 item_id 去重成 40）")

    def test_review_duplicate_reviewer_submission_not_inflated(self) -> None:
        # §六A：同一 (item, reviewer) 重复提交（不同 case_id/payload）→ judgment 记录数不虚增
        records = [_mk_judgment(f"I{i:02d}", rv)
                   for i in range(40) for rv in ("RV1", "RV2")]
        records.append(_mk_judgment("I00", "RV1", submission="s2"))
        pc = _recompute(records)
        self.assertEqual(pc["custody_binding"]["record_count"], 81)
        self.assertEqual(pc["counts"]["review_judgment_records"], 80,
                         "同一 reviewer 对同一 item 重复提交仍计 80（非 81）")
        self.assertEqual(pc["counts"]["review_double_reviewed_items"], 40)

    def test_review_single_reviewer_items_are_not_double_reviewed(self) -> None:
        # 每 item 仅 1 reviewer → judgment=40 < 80 且 double_reviewed_items=0（防"单评冒充双审"假绿）
        records = [_mk_judgment(f"I{i:02d}", "RV1") for i in range(40)]
        pc = _recompute(records)
        self.assertEqual(pc["counts"]["review_judgment_records"], 40)
        self.assertEqual(pc["counts"]["review_double_reviewed_items"], 0,
                         "无 item 具 >=2 reviewer → 双审 item=0（非 40）")


if __name__ == "__main__":
    unittest.main()
