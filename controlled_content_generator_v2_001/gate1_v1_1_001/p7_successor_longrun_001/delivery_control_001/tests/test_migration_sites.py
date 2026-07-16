#!/usr/bin/env python3
"""v2.5 §五第 12 项：23 位点四家族最低迁移测试（对活仓复核，非扫描终点）。

家族 A（checker 主动阻塞）/ B（spine 休眠强制逻辑）/ C（测试放大器）/
D（合同与状态 JSON）逐位点验证迁移后语义 + 保留面零误伤。
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent
ES = P7 / "eval_audit_spine_001"
ROOT = P7.parents[2]
PRESERVATION_COMMIT = "f7d661995165f4d7a6559c40482e296b43781bd2"


def _j(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FamilyACheckerSites(unittest.TestCase):
    """A 家族：p7_master_check :313-320 / :353-371 / :407 / :267 钉死语义已摘除。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.master = _load(P7 / "checker/p7_master_check.py", "p7_master_check_ut")
        cls.v25 = _load(P7 / "checker/v25_state_checks.py", "v25_state_checks_ut")

    def test_budget_stage_gate_section_removed_and_replaced(self) -> None:
        self.assertNotIn("budget_stage_gate", self.master.SECTIONS)
        for section in ("stage_contract_v2", "cost_accounting",
                        "active_contract_set", "d0_status", "run_journal",
                        "final_receipts"):
            self.assertIn(section, self.master.SECTIONS)

    def test_m0_state_section_is_expectation_aware_not_pinned(self) -> None:
        ok, details = self.v25.check_m0_state_integrity(
            ROOT, {"milestone": "M1"})
        self.assertTrue(ok, details)
        # 同一实际状态在错误里程碑期望下必须能区分（参数化生效的证据）
        spec = _j(DC / "state/STATE_EXPECTATION.v1.json")
        self.assertIn("M4", spec["milestone_expectations"])
        self.assertNotEqual(
            spec["milestone_expectations"]["M1"]["m0_status"],
            spec["milestone_expectations"]["M4"]["m0_status"])

    def test_checker_cli_supports_milestone_product_mode(self) -> None:
        source = (P7 / "checker/p7_master_check.py").read_text(encoding="utf-8")
        for flag in ("--milestone", "--product", "--mode", "--state-file",
                     "--selftest"):
            self.assertIn(flag, source)
        self.assertIn("SECTION_SCOPES", source)

    def test_no_coupled_global_all_pass_between_products(self) -> None:
        scopes = self.master.SECTION_SCOPES
        self.assertEqual(scopes["eval_spine_selftest"], "A")
        self.assertEqual(scopes["v4_recovery_selftest"], "B")
        self.assertEqual(scopes["pkg1_reviews"], "B")


class FamilyBSpineSites(unittest.TestCase):
    """B 家族：cost.py :727-893 / stage_gate :15/:17 / runner :44/:54。"""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(ES))
        for name in [m for m in sys.modules if m == "spine" or m.startswith("spine.")]:
            del sys.modules[name]
        cls.cost = importlib.import_module("spine.cost")
        cls.stage_gate = importlib.import_module("spine.stage_gate")
        cls.runner = importlib.import_module("spine.runner")

    @classmethod
    def tearDownClass(cls) -> None:
        if sys.path and sys.path[0] == str(ES):
            sys.path.pop(0)

    def test_budget_gate_machinery_removed(self) -> None:
        self.assertFalse(hasattr(self.cost, "budget_gate"))
        self.assertFalse(hasattr(self.cost, "REQUIRED_CEILING_KEYS"))
        self.assertTrue(hasattr(self.cost, "accounting_integrity_gate"))
        decision = self.cost.accounting_integrity_gate([])
        self.assertEqual(decision["status"], "STOP_COST_ACCOUNTING_MISSING")
        self.assertFalse(decision["budget_blocking"])

    def test_stage_gate_s2_budget_key_removed_s3_diagnostic(self) -> None:
        self.assertNotIn("budget", self.stage_gate.STAGE_GATE_KEYS["S2"])
        self.assertEqual(self.stage_gate.S3_SAFETY_KEYS,
                         {"causal_interpretability", "hard_veto_zero",
                          "anomalies_reported"})
        no_lift = self.stage_gate.stage_decision(
            stage="S3",
            gates={"causal_interpretability": True,
                   "minimum_useful_effect": False,
                   "hard_veto_zero": True, "anomalies_reported": True},
            revision_count=0)
        self.assertEqual(no_lift["status"], "S3_DIAGNOSTIC_COMPLETE")

    def test_runner_echo_reads_actual_state_file(self) -> None:
        actual = _j(ES / "calibration/M0_STATUS.v1.json")["status"]
        self.assertEqual(self.runner._actual_m0_status(ROOT), actual)


class FamilyCTestAmplifierSites(unittest.TestCase):
    """C 家族：test_cost_schema :19/:199、test_eval_audit_spine :1077/:1102/:1132/:1378。"""

    def test_module_level_imports_migrated(self) -> None:
        for name in ("test_cost_schema.py", "test_eval_audit_spine.py"):
            source = (ES / "tests" / name).read_text(encoding="utf-8")
            self.assertNotIn("budget_gate", source, name)
            self.assertNotIn("REQUIRED_CEILING_KEYS", source, name)
            self.assertIn("accounting_integrity_gate", source, name)

    def test_cost_schema_targets_v2(self) -> None:
        source = (ES / "tests/test_cost_schema.py").read_text(encoding="utf-8")
        self.assertIn("cost.v2.schema.json", source)
        self.assertIn("accounting_decision", source)

    def test_shadow_echo_assertion_reads_actual_state(self) -> None:
        source = (ES / "tests/test_eval_audit_spine.py").read_text(encoding="utf-8")
        self.assertIn("calibration/M0_STATUS.v1.json", source)


class FamilyDContractStateSites(unittest.TestCase):
    """D 家族：stage_and_kill / cost_budget / measurement_qualification /
    M0_STATUS / qualification_manifest / dev_manifest 逐键。"""

    def test_stage_and_kill_v2_topology(self) -> None:
        v2 = _j(ES / "contract/stage_and_kill.v2.json")
        stages = {s["stage_id"]: s for s in v2["stages"]}
        s2_entry = set(stages["S2_FEASIBILITY_AND_COST_TELEMETRY"]["entry_requires"])
        self.assertNotIn("S1_PASS", s2_entry)                      # 位点 :54
        self.assertNotIn("FOUNDER_APPROVED_BUDGET_CEILINGS", s2_entry)  # 位点 :55
        self.assertEqual(s2_entry, {
            "S0_PASS", "FIVE_FAMILY_STRATEGIES_FROZEN",
            "INDEPENDENT_REVIEW_ROLES_ASSIGNED", "B_EVAL_ROUTE_FROZEN",
            "NARRATIVE_FACT_REVIEW_CAPABILITY_READY"})
        s2_exit = stages["S2_FEASIBILITY_AND_COST_TELEMETRY"]["exit_requires"]
        self.assertNotIn("PROJECTED_300_COST_WITHIN_ALL_APPROVED_CEILINGS",
                         s2_exit)                                   # 位点 :61
        self.assertIn("P50_AND_P95_COST_AND_LATENCY_REPORTED", s2_exit)
        s4_entry = set(stages["S4_OPEN_REGRESSION_120"]["entry_requires"])
        self.assertNotIn("S3_PASS", s4_entry)                       # 位点 :92
        self.assertIn("S3_SAFETY_EXIT_ALL_GREEN", s4_entry)
        s6_entry = set(stages["S6_BASELINE_240_PLUS_60"]["entry_requires"])
        self.assertNotIn("COST_REFORECAST_WITHIN_BUDGET", s6_entry)  # 位点 :127
        self.assertIn("COST_ACCOUNTING_COMPLETE_AND_RECOMPUTABLE", s6_entry)
        kills = {rule["code"] for rule in v2["global_kill_rules"]}
        self.assertNotIn("STOP_BUDGET", kills)                      # 位点 :168
        self.assertIn("STOP_COST_ACCOUNTING_MISSING", kills)
        self.assertIn("STOP_EXTERNAL_LLM_DAILY_BUDGET", kills)      # 保留面
        s3 = stages["S3_CAUSAL_PILOT_60"]
        self.assertEqual(s3["gate_type"], "DIAGNOSTIC")             # 位点 :67-68/:86
        self.assertNotIn("STOP_S3_NO_CAUSAL_LIFT", s3.get("kill_codes", []))
        self.assertNotIn("current_state", v2)                       # 实际态分离

    def test_cost_accounting_v2_and_retained_faces(self) -> None:
        v2 = _j(ES / "contract/cost_accounting.v2.json")
        v1 = _j(ES / "contract/cost_budget.v1.json")
        for dead in ("approval_status", "hard_ceilings", "current_decision"):
            self.assertNotIn(dead, v2)                              # 位点 :4/:101
        rules = set(v2["fail_closed_rules"])
        self.assertNotIn("NO_SCALE_WHILE_APPROVAL_STATUS_IS_NOT_APPROVED",
                         rules)                                     # 位点 :95
        self.assertIn("NO_MISSING_CALL_OR_REVIEW_COSTS", rules)
        self.assertIn("NO_ZERO_COST_PLACEHOLDERS_FOR_UNKNOWN_COSTS", rules)
        self.assertEqual(v2["required_cost_event_fields"],
                         v1["required_cost_event_fields"])          # 24 字段保留
        self.assertEqual(len(v2["required_cost_event_fields"]), 24)
        ext = _j(ES / "contract/external_llm_budget.v1.json")
        self.assertEqual(ext["daily_hard_ceiling_cny"], 30.0)       # DeepSeek 保留

    def test_measurement_qualification_v2_ceiling_stops_migrated(self) -> None:
        v2 = _j(ES / "contract/measurement_qualification.v2.json")
        v1 = _j(ES / "contract/measurement_qualification.v1.json")
        self.assertNotIn("current_status", v2)                      # 位点 :4
        cost_gate = v2["module_gates"]["cost"]
        self.assertNotIn("actual_cost_at_or_above_any_hard_ceiling_stops",
                         cost_gate)                                 # 位点 :135
        self.assertNotIn("formal_p95_above_any_hard_ceiling_stops", cost_gate)
        self.assertTrue(cost_gate["accounting_missing_is_stop"])
        self.assertEqual(cost_gate["daily_external_llm_budget_cny"], 30.0)
        self.assertEqual(cost_gate["minimum_complete_events"], 12)
        for module in ("reference_assertion_extraction", "claim_atomization",
                       "risk_classification", "entailment",
                       "fact_chain_end_to_end", "formulaic_construct",
                       "disclosure_and_omission", "review_calibration"):
            self.assertEqual(v2["module_gates"][module],
                             v1["module_gates"][module], module)    # 非 cost 门零改动
        self.assertEqual(v2["qualification_set_minimums"],
                         v1["qualification_set_minimums"])

    def test_actual_state_files_are_honest_and_separated(self) -> None:
        m0 = _j(ES / "calibration/M0_STATUS.v1.json")
        self.assertEqual(m0["status"], "NOT_QUALIFIED")             # 诚实维持
        self.assertNotIn("BUDGET_UNAPPROVED", m0["reason_codes"])   # 位点 :12
        qm = _j(ES / "calibration/qualification_manifest.v1.json")
        self.assertEqual(qm["case_count"], 0)                       # 位点 :5-7（真实空集）
        self.assertEqual(qm["content_status"], "NOT_MATERIALIZED")
        dm = _j(ES / "calibration/dev_manifest.v1.json")
        self.assertEqual(dm["content_status"], "NOT_MATERIALIZED")  # 位点 :5
        sa = _j(ES / "calibration/stage_actual_state.v1.json")
        self.assertEqual(sa["executed_stages"], [])
        self.assertFalse(sa["real_run_executed"])
        v11 = _j(ES / "calibration/V11_STATUS.v1.json")
        self.assertEqual(v11["status"], "NOT_QUALIFIED")   # V1.1 诚实维持
        self.assertIn("READY_FOR_300", v11["claims_forbidden"])
        # 期望映射的 v11_status 已被 checker 消费（Codex R2 BLOCKING 回归护栏）
        checker_source = (P7 / "checker/v25_state_checks.py").read_text(
            encoding="utf-8")
        self.assertIn('exp.get("v11_status"', checker_source)

    def test_sealed_v1_history_untouched_since_preservation(self) -> None:
        for rel in ("eval_audit_spine_001/contract/stage_and_kill.v1.json",
                    "eval_audit_spine_001/contract/cost_budget.v1.json",
                    "eval_audit_spine_001/contract/measurement_qualification.v1.json",
                    "eval_audit_spine_001/contract/external_llm_budget.v1.json",
                    "eval_audit_spine_001/spine/external_llm.py",
                    "eval_audit_spine_001/tests/test_external_llm.py"):
            diff = subprocess.run(
                ["git", "-C", str(ROOT), "diff", PRESERVATION_COMMIT, "--",
                 str((P7 / rel).relative_to(ROOT))],
                capture_output=True, text=True)
            self.assertEqual(diff.stdout, "", f"{rel} drifted after preservation")


if __name__ == "__main__":
    unittest.main(verbosity=1)
