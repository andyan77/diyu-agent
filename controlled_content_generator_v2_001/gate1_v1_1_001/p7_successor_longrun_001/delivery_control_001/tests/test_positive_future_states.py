#!/usr/bin/env python3
"""正向未来状态演进测试（v2.5 §五 出口断言 (c) + P1 §二十）。

模拟"预算已拨付 / 金标已物化 / M0 已合格 / B 轨已合法推进 /
S3 无提升但安全出口通过"等合法未来状态——checker 必须 PASS，
杜绝 N3/N4 型"合法推进反而报错"复发。
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent
ES = P7 / "eval_audit_spine_001"
ROOT = P7.parents[2]

EVAL_SPINE_REL = ("controlled_content_generator_v2_001/gate1_v1_1_001/"
                  "p7_successor_longrun_001/eval_audit_spine_001")
DC_REL = ("controlled_content_generator_v2_001/gate1_v1_1_001/"
          "p7_successor_longrun_001/delivery_control_001")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V25 = _load(P7 / "checker/v25_state_checks.py", "v25_future_ut")
HEX = "ab12" * 16


def _write(root: Path, rel: str, value: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1),
                    encoding="utf-8")


def _base_future_root(tmp: Path) -> Path:
    """以真实合同/期望文件为底座搭建合成未来根。"""
    for rel in ("contract/stage_and_kill.v2.json",):
        dst = tmp / EVAL_SPINE_REL / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ES / rel, dst)
    dst = tmp / DC_REL / "state/STATE_EXPECTATION.v1.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(DC / "state/STATE_EXPECTATION.v1.json", dst)
    return tmp


def _m0(status: str, qualified_evidence: bool = False) -> dict:
    value = {
        "schema_version": "eval-spine-stage-decision-v1",
        "decision_id": "EAS-M0-STATUS-V1",
        "stage_id": "S1_M0_MEASUREMENT_QUALIFICATION",
        "status": status,
        "reason_codes": [] if status == "QUALIFIED" else ["NO_QUALIFICATION_RUN"],
        "evidence_manifest_digests": [HEX] if qualified_evidence else [],
        "next_allowed_stage": None,
        "claims_allowed": [],
        "claims_forbidden": ([] if status == "QUALIFIED"
                             else ["TRUSTED_EVALUATION", "READY_FOR_300"]),
        "decided_by": "INDEPENDENT_ADJUDICATOR" if qualified_evidence else None,
        "decision_digest": HEX if qualified_evidence else None,
    }
    return value


def _manifest(materialized: bool, sealed: bool) -> dict:
    return {
        "schema_version": "eval-spine-calibration-manifest-v1",
        "manifest_id": "T", "data_grid": "G",
        "content_status": "MATERIALIZED" if materialized else "NOT_MATERIALIZED",
        "sealed": sealed,
        "case_count": 100 if materialized else 0,
        "class_counts": {},
        "dataset_manifest_digest": HEX if materialized else None,
        "source_manifest_digest": HEX if materialized else None,
        "gold_manifest_digest": HEX if materialized else None,
        "allowed_consumers": [], "prohibited_consumers": [],
        "leakage_status": "NOT_EVALUATED", "notes": [], "manifest_digest": None,
    }


def _stage_actual(executed: list[str], real_run: bool) -> dict:
    return {
        "schema_version": "eval-spine-stage-actual-state-v1",
        "executed_stages": executed,
        "stage_receipts": {stage: {"receipt_path": f"r/{stage}.json",
                                   "receipt_digest": HEX}
                           for stage in executed},
        "reference_implementation_selftested": True,
        "real_run_executed": real_run,
        "notes": [],
    }


class PositiveFutureStates(unittest.TestCase):
    def _check(self, root: Path, milestone: str):
        return V25.check_m0_state_integrity(root, {"milestone": milestone})

    def test_m1_honest_baseline_passes(self) -> None:
        ok, details = V25.check_m0_state_integrity(ROOT, {"milestone": "M1"})
        self.assertTrue(ok, details)

    def test_m3_gold_materialized_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _base_future_root(Path(tmp))
            _write(root, f"{EVAL_SPINE_REL}/calibration/M0_STATUS.v1.json",
                   _m0("NOT_QUALIFIED"))
            _write(root, f"{EVAL_SPINE_REL}/calibration/qualification_manifest.v1.json",
                   _manifest(materialized=True, sealed=True))
            _write(root, f"{EVAL_SPINE_REL}/calibration/dev_manifest.v1.json",
                   _manifest(materialized=True, sealed=False))
            _write(root, f"{EVAL_SPINE_REL}/calibration/stage_actual_state.v1.json",
                   _stage_actual(["S0_DETERMINISTIC_HYGIENE"], real_run=True))
            ok, details = self._check(root, "M3")
            self.assertTrue(ok, details)

    def test_m4_m0_qualified_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _base_future_root(Path(tmp))
            _write(root, f"{EVAL_SPINE_REL}/calibration/M0_STATUS.v1.json",
                   _m0("QUALIFIED", qualified_evidence=True))
            _write(root, f"{EVAL_SPINE_REL}/calibration/qualification_manifest.v1.json",
                   _manifest(True, True))
            _write(root, f"{EVAL_SPINE_REL}/calibration/dev_manifest.v1.json",
                   _manifest(True, False))
            _write(root, f"{EVAL_SPINE_REL}/calibration/stage_actual_state.v1.json",
                   _stage_actual(["S0_DETERMINISTIC_HYGIENE",
                                  "S1_M0_MEASUREMENT_QUALIFICATION"], True))
            ok, details = self._check(root, "M4")
            self.assertTrue(ok, details)

    def test_m4_m0_diagnostic_final_also_legal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _base_future_root(Path(tmp))
            m0 = _m0("DIAGNOSTIC_FINAL")
            _write(root, f"{EVAL_SPINE_REL}/calibration/M0_STATUS.v1.json", m0)
            _write(root, f"{EVAL_SPINE_REL}/calibration/qualification_manifest.v1.json",
                   _manifest(True, True))
            _write(root, f"{EVAL_SPINE_REL}/calibration/dev_manifest.v1.json",
                   _manifest(True, False))
            _write(root, f"{EVAL_SPINE_REL}/calibration/stage_actual_state.v1.json",
                   _stage_actual(["S0_DETERMINISTIC_HYGIENE",
                                  "S1_M0_MEASUREMENT_QUALIFICATION"], True))
            ok, details = self._check(root, "M4")
            self.assertTrue(ok, details)

    def test_m6_b_track_advanced_without_s1_passes(self) -> None:
        """B 轨合法推进（S2→S4 已执行、S1 从未执行）在 M6 期望下必须 PASS——
        杜绝『B 未推进』被钉死为永恒正确答案（N4 家族 A 位点核心回归）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _base_future_root(Path(tmp))
            _write(root, f"{EVAL_SPINE_REL}/calibration/M0_STATUS.v1.json",
                   _m0("NOT_QUALIFIED"))
            _write(root, f"{EVAL_SPINE_REL}/calibration/qualification_manifest.v1.json",
                   _manifest(False, True))
            _write(root, f"{EVAL_SPINE_REL}/calibration/dev_manifest.v1.json",
                   _manifest(False, False))
            _write(root, f"{EVAL_SPINE_REL}/calibration/stage_actual_state.v1.json",
                   _stage_actual(["S0_DETERMINISTIC_HYGIENE",
                                  "S2_FEASIBILITY_AND_COST_TELEMETRY",
                                  "S3_CAUSAL_PILOT_60",
                                  "S4_OPEN_REGRESSION_120"], True))
            ok, details = self._check(root, "M6")
            self.assertTrue(ok, details)

    def test_b_track_stage_skip_still_fails(self) -> None:
        """正向测试的护栏对照：B 轨跳步（S2 未执行直接 S4）仍必须 FAIL。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = _base_future_root(Path(tmp))
            _write(root, f"{EVAL_SPINE_REL}/calibration/M0_STATUS.v1.json",
                   _m0("NOT_QUALIFIED"))
            _write(root, f"{EVAL_SPINE_REL}/calibration/qualification_manifest.v1.json",
                   _manifest(False, True))
            _write(root, f"{EVAL_SPINE_REL}/calibration/dev_manifest.v1.json",
                   _manifest(False, False))
            _write(root, f"{EVAL_SPINE_REL}/calibration/stage_actual_state.v1.json",
                   _stage_actual(["S0_DETERMINISTIC_HYGIENE",
                                  "S4_OPEN_REGRESSION_120"], True))
            ok, details = self._check(root, "M6")
            self.assertFalse(ok)
            self.assertTrue(any("skipped" in d for d in details), details)

    def test_budget_disbursed_does_not_block(self) -> None:
        """拨付发生（disbursement_ledger 非空）后成本合同检查必须仍 PASS。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            es_dst = root / EVAL_SPINE_REL
            (es_dst / "contract").mkdir(parents=True)
            for rel in ("contract/cost_budget.v1.json",
                        "contract/external_llm_budget.v1.json"):
                shutil.copy(ES / rel, es_dst / rel)
            (es_dst / "spine").symlink_to(ES / "spine")
            accounting = json.loads(
                (ES / "contract/cost_accounting.v2.json").read_text(
                    encoding="utf-8"))
            accounting["disbursement_ledger"] = [{
                "disbursement_id": "D-1", "disbursed_by": "FOUNDER",
                "disbursed_at": "2026-08-01T00:00:00+00:00", "amount": 500,
                "currency": "USD", "scope_note": "M3 gold build",
                "evidence_ref": "founder message 2026-08-01"}]
            _write(root, f"{EVAL_SPINE_REL}/contract/cost_accounting.v2.json",
                   accounting)
            ok, details = V25.check_cost_accounting_contract(
                root, {"milestone": "M3"})
            self.assertTrue(ok, details)

    def test_s3_no_lift_with_safety_green_not_killed(self) -> None:
        sys.path.insert(0, str(ES))
        try:
            for name in [m for m in sys.modules
                         if m == "spine" or m.startswith("spine.")]:
                del sys.modules[name]
            stage_gate = importlib.import_module("spine.stage_gate")
        finally:
            if sys.path and sys.path[0] == str(ES):
                sys.path.pop(0)
        decision = stage_gate.stage_decision(
            stage="S3",
            gates={"causal_interpretability": True,
                   "minimum_useful_effect": False,
                   "hard_veto_zero": True, "anomalies_reported": True},
            revision_count=0)
        self.assertEqual(decision["status"], "S3_DIAGNOSTIC_COMPLETE")
        self.assertNotEqual(decision["status"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=1)
