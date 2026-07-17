#!/usr/bin/env python3
"""P1 §二十 负向攻击矩阵：30 项必须按预期被拒绝的攻击，逐项建档。

纪律：不得通过删除断言、skip、空测试或降低阈值制造绿色——每个攻击都以
真实机制（schema/摘要复算/状态机/扫描器）证明会被拒绝。
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent
ES = P7 / "eval_audit_spine_001"
ROOT = P7.parents[2]

sys.path.insert(0, str(HERE.parent))
import fixture_helpers as fh  # noqa: E402

receipts = fh.receipts
journal_mod = fh.journal_mod
ready_set_mod = fh.load_tool("ready_set")
closeout_mod = fh.load_tool("closeout")
launcher_mod = fh.load_tool("launcher")
qual_order_mod = fh.load_tool("qual_order")
lift_chain_mod = fh.load_tool("lift_chain")
sealed_scan_mod = fh.load_tool("sealed_scan")


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "v25_attacks", P7 / "checker/v25_state_checks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V25 = _load_checker()

EVAL_SPINE_REL = ("controlled_content_generator_v2_001/gate1_v1_1_001/"
                  "p7_successor_longrun_001/eval_audit_spine_001")
DC_REL = ("controlled_content_generator_v2_001/gate1_v1_1_001/"
          "p7_successor_longrun_001/delivery_control_001")


_git_init_commit = fh.git_init_commit
_final_fixture = fh.build_final_fixture


def _mk_receipt(milestone, result, flags=None, bindings=None):
    value = {
        "schema_version": "p7-typed-receipt-v1",
        "receipt_kind": "CLOSEOUT_RECEIPT", "milestone_id": milestone,
        "product_scope": "SHARED", "result": result, "terminal": True,
        "qualification_flags": flags or {}, "candidate_commit": "c" * 40,
        "output_manifest_digest": "d" * 64,
        "evidence_manifest_digest": "e" * 64,
        "review_bindings": bindings if bindings is not None else [
            {"receipt_path": "r1", "receipt_digest": "1" * 64,
             "reviewer_kind": "K1", "verdict": "ACCEPT"},
            {"receipt_path": "r2", "receipt_digest": "2" * 64,
             "reviewer_kind": "K2", "verdict": "ACCEPT"}],
        "issued_at": "T", "issued_by_role": "PRINCIPAL",
        "receipt_digest": ""}
    return receipts.close_record(value, "receipt_digest")


def _write_receipt(mdir, milestone, receipt):
    d = mdir / milestone
    d.mkdir(parents=True, exist_ok=True)
    (d / "CLOSEOUT_RECEIPT.v1.json").write_text(
        json.dumps(receipt, ensure_ascii=False), encoding="utf-8")


class NegativeAttackMatrix(unittest.TestCase):
    def test_attack_01_zero_review_reports(self) -> None:
        forged = _mk_receipt("M1", "PASS", bindings=[])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            path.write_text(json.dumps(forged), encoding="utf-8")
            with self.assertRaises(receipts.ReceiptError):
                receipts.load_typed_receipt(path)

    def test_attack_02_missing_evidence_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dc = fh.build_m1_closeout_fixture(Path(tmp))
            (dc / "milestones/M1/EVIDENCE_MANIFEST.v1.json").unlink()
            ok, details = closeout_mod.validate_eight_pieces(
                Path(tmp), dc / "milestones/M1")
            self.assertFalse(ok)
            self.assertTrue(any("EVIDENCE_MANIFEST" in d for d in details))

    def test_attack_03_missing_eight_piece_member(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dc = fh.build_m1_closeout_fixture(Path(tmp))
            (dc / "milestones/M1/HANDOFF.v2.json").unlink()
            ok, _ = closeout_mod.validate_eight_pieces(
                Path(tmp), dc / "milestones/M1")
            self.assertFalse(ok)

    def test_attack_04_forged_typed_status(self) -> None:
        receipt = _mk_receipt("M6", "FAIL")
        receipt["result"] = "PASS"  # 摘要未重算的直接篡改
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaises(receipts.ReceiptError):
                receipts.load_typed_receipt(path)

    def test_attack_05_review_ready_impersonates_pass(self) -> None:
        receipt = _mk_receipt("M1", "PASS")
        receipt["result"] = "IMPLEMENTATION_COMPLETE_REVIEW_READY"
        receipt = receipts.close_record(receipt, "receipt_digest")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaises(receipts.ReceiptError) as ctx:
                receipts.load_typed_receipt(path)
            self.assertIn("REVIEW_READY is not PASS", str(ctx.exception))

    def test_attack_06_generic_closeout_impersonates_qualification(self) -> None:
        generic_pass = _mk_receipt("M4", "PASS")  # 无 A2_QUALIFIED 旗标
        self.assertFalse(receipts.qualification_flag(generic_pass, "A2_QUALIFIED"))

    def test_attack_07_a2_diagnostic_final_impersonates_a2_qualified(self) -> None:
        diag = _mk_receipt("M4", "DIAGNOSTIC_FINAL",
                           flags={"A2_DIAGNOSTIC_FINAL": True,
                                  "A2_QUALIFIED": True})
        # 即使旗标被硬塞 true，非 PASS 回执一律不产生资格
        self.assertFalse(receipts.qualification_flag(diag, "A2_QUALIFIED"))

    def test_attack_08_m6_fail_receipt_impersonates_b_lift_ready(self) -> None:
        forged = _mk_receipt("M6", "FAIL", flags={"B_LIFT_READY": True})
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_receipt(mdir, "M6", forged)
            rs = ready_set_mod.compute_ready_set(Path(tmp),
                                                 milestones_dir=mdir, route="a")
            self.assertFalse(rs["M7"]["ready"])
            self.assertIn("M6", rs["_invalid_receipts"])

    def test_attack_09_same_session_enters_next_milestone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dc = fh.build_m1_closeout_fixture(Path(tmp))
            with self.assertRaises(launcher_mod.LaunchRefused) as ctx:
                launcher_mod.validate_entry(
                    Path(tmp), "M2", dc=dc,
                    env={"CLAUDE_CODE_SESSION_ID": "author-session-M1"})
            self.assertIn("same-session", str(ctx.exception))

    def test_attack_10_journal_missing_inverted_broken_or_contradicting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = journal_mod.parse_journal(Path(tmp) / "NO.jsonl")
            self.assertEqual(missing["status"], "MISSING")
            j = Path(tmp) / "J.jsonl"
            rec = journal_mod.append_record(j, {
                "session_id": "S", "run_id": "R", "input_commit": "c" * 40,
                "dirty_tree_digest": "d" * 64, "capsule": "C1",
                "state": "ACTIVE", "requested_model": "fable",
                "actual_model": "claude-fable-5", "subagent_ids": [],
                "last_green_commit": "c" * 40, "verification_state": "GREEN",
                "next_action": "n", "stop_reason": None}, None)
            forged = dict(rec)
            forged["seq"] = 1  # 倒序/重复
            forged["prev_record_digest"] = rec["record_digest"]
            forged["record_digest"] = journal_mod.canonical_digest(forged)
            with open(j, "ab") as f:
                f.write((json.dumps(forged, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n").encode())
            self.assertEqual(journal_mod.parse_journal(j)["status"], "INVALID")
            # 与 Git 矛盾：git_head 指向不存在的提交 → checker journal 节 FAIL
            with tempfile.TemporaryDirectory() as tmp2:
                dc2 = Path(tmp2) / DC_REL
                (dc2 / "tools").mkdir(parents=True)
                (dc2 / "journal").mkdir(parents=True)
                shutil.copy(DC / "tools/run_journal.py",
                            dc2 / "tools/run_journal.py")
                journal_mod.append_record(
                    dc2 / "journal/RUN_JOURNAL.v1.jsonl",
                    {"session_id": "S", "run_id": "R",
                     "input_commit": "c" * 40, "dirty_tree_digest": "d" * 64,
                     "capsule": "C1", "state": "ACTIVE",
                     "requested_model": "fable",
                     "actual_model": "claude-fable-5", "subagent_ids": [],
                     "last_green_commit": "c" * 40,
                     "verification_state": "GREEN", "next_action": "n",
                     "stop_reason": None, "git_head": "f" * 40}, None)
                ok, details = V25.check_run_journal(Path(tmp2),
                                                    {"milestone": "M1"})
                self.assertFalse(ok)
                self.assertTrue(any("unknown to repository" in d
                                    for d in details))

    def test_attack_11_auto_memory_not_disabled(self) -> None:
        record = _mk_receipt("M2", "PASS")  # 借结构；实际用 launch record
        launch = {
            "schema_version": "p7-launch-record-v1", "prompt_id": "P2",
            "milestone_id": "M2", "workspace": "/w",
            "input_commit": "c" * 40, "rendered_prompt_path": "p.md",
            "rendered_prompt_digest": "a" * 64, "template_digest": "b" * 64,
            "predecessor_receipt_digest": "c" * 64,
            "handoff_digest": "d" * 64,
            "write_surface_allowlist": ["x/**"],
            "write_surface_denylist": ["y/**"],
            "allowed_git_actions": ["commit"],
            "allowed_repo_and_remote_creation": [],
            "allowed_models_and_materials": ["fable"],
            "session_kind": "TOP_LEVEL_FRESH", "session_id": "new-session",
            "requested_model": "fable", "actual_model": "claude-fable-5",
            "auto_memory_disabled": False,
            "launched_by": "SESSION_EXTERNAL_SUPERVISOR",
            "launched_at": "T", "launch_capability": "AUTO_LAUNCHED",
            "record_digest": ""}
        launch = receipts.close_record(launch, "record_digest")
        errors = receipts.validate_launch_record(launch)
        self.assertTrue(any("auto" in e.lower() or "memory" in e.lower()
                            or "schema" in e for e in errors))

    def test_attack_12_author_signs_own_work(self) -> None:
        signer = receipts.close_record({
            "schema_version": "p7-signer-receipt-v1",
            "reviewer_kind": "INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER",
            "provider": "anthropic", "actual_model_id": "m",
            "model_version": "v", "task_thread_session_id": "author-session",
            "input_commit": "c" * 40, "input_manifest_digest": "d" * 64,
            "prompt_digest": "e" * 64, "config_digest": "cfg",
            "tool_summary": "t", "output_report_digest": "f" * 64,
            "call_receipt": "cr", "exit_status": 0, "signed_at": "T",
            "session_isolation_attestation": {
                "fresh_session_not_fork_not_resume": True,
                "did_not_author_reviewed_scope": False,  # 作者自签
                "auto_memory_disabled_or_not_applicable": True,
                "isolation_evidence": "x"},
            "verdict": "ACCEPT", "receipt_digest": ""}, "receipt_digest")
        with tempfile.TemporaryDirectory() as tmp:
            dc2 = Path(tmp) / DC_REL
            (dc2 / "schema").mkdir(parents=True)
            shutil.copy(DC / "schema/signer_receipt.v1.schema.json",
                        dc2 / "schema/signer_receipt.v1.schema.json")
            rp = Path(tmp) / "r.json"
            rp.write_text(json.dumps(signer), encoding="utf-8")
            errors = V25.validate_signer_receipt(Path(tmp), rp)
            self.assertTrue(errors)

    def test_attack_13_missing_signer_fields_or_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dc2 = Path(tmp) / DC_REL
            (dc2 / "schema").mkdir(parents=True)
            shutil.copy(DC / "schema/signer_receipt.v1.schema.json",
                        dc2 / "schema/signer_receipt.v1.schema.json")
            incomplete = {"schema_version": "p7-signer-receipt-v1",
                          "verdict": "ACCEPT", "receipt_digest": "0" * 64}
            rp = Path(tmp) / "r.json"
            rp.write_text(json.dumps(incomplete), encoding="utf-8")
            self.assertTrue(V25.validate_signer_receipt(Path(tmp), rp))

    def test_attack_14_program_budget_becomes_blocking_gate_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            es_dst = root / EVAL_SPINE_REL
            (es_dst / "contract").mkdir(parents=True)
            for rel in ("contract/cost_budget.v1.json",
                        "contract/external_llm_budget.v1.json"):
                shutil.copy(ES / rel, es_dst / rel)
            (es_dst / "spine").symlink_to(ES / "spine")
            accounting = json.loads((ES / "contract/cost_accounting.v2.json"
                                     ).read_text(encoding="utf-8"))
            accounting["fail_closed_rules"].append(
                "NO_SCALE_WHILE_APPROVAL_STATUS_IS_NOT_APPROVED")
            (es_dst / "contract/cost_accounting.v2.json").write_text(
                json.dumps(accounting, ensure_ascii=False), encoding="utf-8")
            ok, details = V25.check_cost_accounting_contract(
                root, {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("resurrected" in d for d in details))

    def test_attack_15_b_track_depends_on_s1_pass_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            es_dst = root / EVAL_SPINE_REL / "contract"
            es_dst.mkdir(parents=True)
            contract = json.loads((ES / "contract/stage_and_kill.v2.json"
                                   ).read_text(encoding="utf-8"))
            for stage in contract["stages"]:
                if stage["stage_id"] == "S2_FEASIBILITY_AND_COST_TELEMETRY":
                    stage["entry_requires"].append("S1_PASS")
            (es_dst / "stage_and_kill.v2.json").write_text(
                json.dumps(contract, ensure_ascii=False), encoding="utf-8")
            ok, _ = V25.check_stage_contract_v2(root, {"milestone": "M1"})
            self.assertFalse(ok)

    def test_attack_16_s3_no_lift_wrongly_killed(self) -> None:
        sys.path.insert(0, str(ES))
        try:
            for name in [m for m in sys.modules
                         if m == "spine" or m.startswith("spine.")]:
                del sys.modules[name]
            stage_gate = importlib.import_module("spine.stage_gate")
        finally:
            sys.path.pop(0)
        decision = stage_gate.stage_decision(
            stage="S3", gates={"causal_interpretability": True,
                               "minimum_useful_effect": False,
                               "hard_veto_zero": True,
                               "anomalies_reported": True}, revision_count=0)
        self.assertEqual(decision["status"], "S3_DIAGNOSTIC_COMPLETE")

    def test_attack_17_s3_safety_failure_continues(self) -> None:
        sys.path.insert(0, str(ES))
        try:
            for name in [m for m in sys.modules
                         if m == "spine" or m.startswith("spine.")]:
                del sys.modules[name]
            stage_gate = importlib.import_module("spine.stage_gate")
        finally:
            sys.path.pop(0)
        for broken in ("hard_veto_zero", "causal_interpretability",
                       "anomalies_reported"):
            gates = {"causal_interpretability": True,
                     "minimum_useful_effect": True, "hard_veto_zero": True,
                     "anomalies_reported": True, broken: False}
            self.assertEqual(stage_gate.stage_decision(
                stage="S3", gates=gates, revision_count=0)["status"], "FAIL",
                broken)

    def test_attack_18_qual_b_rebuilt_after_failure(self) -> None:
        events = [{"code": code, "seq": i + 1, "at": f"t{i}"} for i, code in
                  enumerate(("A1_FACE_FROZEN", "A2_DOUBLE_BLIND_LABELED",
                             "A3_GOLD_FROZEN", "B1_FACE_FROZEN",
                             "B2_DOUBLE_BLIND_LABELED", "B3_GOLD_FROZEN",
                             "M4_METHOD_V1_FROZEN",
                             "A5_QUAL_A_BLIND_PREDICTED", "A6_REVEALED",
                             "B1_FACE_FROZEN", "B2_DOUBLE_BLIND_LABELED",
                             "B3_GOLD_FROZEN"))]
        events[9]["seq"], events[10]["seq"], events[11]["seq"] = 10, 11, 12
        violations = qual_order_mod.validate_qual_order(events)
        self.assertTrue(any("rebuilt after QUAL-A reveal" in v
                            for v in violations))

    def test_attack_19_actual_state_rewritten_to_expectation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            es_dst = root / EVAL_SPINE_REL
            (es_dst / "calibration").mkdir(parents=True)
            (es_dst / "contract").mkdir(parents=True)
            shutil.copy(ES / "contract/stage_and_kill.v2.json",
                        es_dst / "contract/stage_and_kill.v2.json")
            dc_dst = root / DC_REL / "state"
            dc_dst.mkdir(parents=True)
            shutil.copy(DC / "state/STATE_EXPECTATION.v1.json",
                        dc_dst / "STATE_EXPECTATION.v1.json")
            # 攻击：把实际 M0 状态直接改写成未来期望值 QUALIFIED（无证据）
            forged_m0 = {"schema_version": "eval-spine-stage-decision-v1",
                         "decision_id": "X", "stage_id": "S1",
                         "status": "QUALIFIED", "reason_codes": [],
                         "evidence_manifest_digests": [],
                         "next_allowed_stage": None, "claims_allowed": [],
                         "claims_forbidden": [], "decided_by": None,
                         "decision_digest": None}
            (es_dst / "calibration/M0_STATUS.v1.json").write_text(
                json.dumps(forged_m0), encoding="utf-8")
            for name, grid in (("qualification_manifest.v1.json", True),
                               ("dev_manifest.v1.json", False)):
                shutil.copy(ES / "calibration" / name,
                            es_dst / "calibration" / name)
            shutil.copy(ES / "calibration/stage_actual_state.v1.json",
                        es_dst / "calibration/stage_actual_state.v1.json")
            shutil.copy(ES / "calibration/V11_STATUS.v1.json",
                        es_dst / "calibration/V11_STATUS.v1.json")
            ok, details = V25.check_m0_state_integrity(
                root, {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("QUALIFIED without evidence" in d
                                for d in details))
            self.assertTrue(any("outside expectation" in d for d in details))
            # 同一攻击的 V1.1 面：把 V11 实际态改写成期望值 QUALIFIED（无 B 轨执行）
            forged_v11 = json.loads(
                (ES / "calibration/V11_STATUS.v1.json").read_text(
                    encoding="utf-8"))
            forged_v11["status"] = "QUALIFIED"
            (es_dst / "calibration/V11_STATUS.v1.json").write_text(
                json.dumps(forged_v11), encoding="utf-8")
            ok2, details2 = V25.check_m0_state_integrity(
                root, {"milestone": "M1"})
            self.assertFalse(ok2)
            self.assertTrue(any("v11" in d and ("outside expectation" in d
                                                or "never executed" in d
                                                or "without evidence" in d)
                                for d in details2), details2)

    def test_attack_20_m1_creates_top_level_a_core_staging(self) -> None:
        staging = (ROOT / "controlled_content_generator_v2_001"
                   / "product_core_staging_001")
        self.assertFalse(staging.exists(),
                         "M1 must not create product core staging")
        spec = importlib.util.spec_from_file_location(
            "master_attack20", P7 / "checker/p7_master_check.py")
        master = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(master)
        offenders = master.surface_offenders(
            ["controlled_content_generator_v2_001/product_core_staging_001/x.py"])
        self.assertTrue(offenders, "staging path must be out of write surface")

    def test_attack_21_m1_creates_product_repo_or_remote(self) -> None:
        remotes = subprocess.run(["git", "-C", str(ROOT), "remote"],
                                 capture_output=True, text=True
                                 ).stdout.split()
        self.assertEqual(remotes, ["origin"],
                         "M1 must not create product remotes")
        for candidate in ("product_a_repo", "product_b_repo",
                          "product_core_staging_001"):
            self.assertFalse((ROOT / candidate).exists())

    def test_attack_22_sealed_digest_collision(self) -> None:
        denylist = sealed_scan_mod.load_denylist()
        self.assertTrue(denylist, "synthetic denylist must be non-empty")
        with tempfile.TemporaryDirectory() as tmp:
            leak = Path(tmp) / "innocent.bin"
            leak.write_bytes(b"SYNTHETIC-SEALED-PAYLOAD-QUAL-MARKER-001")
            hits = sealed_scan_mod.scan_worktree(Path(tmp), denylist)
            self.assertEqual(len(hits), 1)

    def test_attack_23_source_history_enters_product_candidate(self) -> None:
        violations = lift_chain_mod.check_no_source_history(
            [".git/objects/ab/cdef", "app/main.py"])
        self.assertTrue(violations)

    def test_attack_24_clean_room_borrows_source_paths(self) -> None:
        violations = lift_chain_mod.check_clean_room_env(
            {"PYTHONPATH": str(ROOT)}, [str(ROOT / "eval")], ["x.egg-link"])
        self.assertGreaterEqual(len(violations), 2)

    def test_attack_25_b_delivery_modifies_b_lift_executable(self) -> None:
        lift = {"app/generator.py": "a" * 64}
        delivery = {"app/generator.py": "b" * 64,
                    "assets/positive_240/x.json": "c" * 64}
        violations = lift_chain_mod.check_executable_tree_identity(
            lift, delivery)
        self.assertTrue(any("modified" in v for v in violations))

    def test_attack_26_delivery_without_rights_clearance(self) -> None:
        self.assertTrue(lift_chain_mod.check_rights_clearance_gate({}))
        self.assertTrue(lift_chain_mod.check_rights_clearance_gate(
            {"RIGHTS_CLEARANCE_CLOSED": False, "rows": [],
             "independent_review_receipt": "r"}))

    def test_attack_27_real_customer_data_in_current_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "logs"
            log_dir.mkdir()
            (log_dir / "run.log").write_bytes(
                b"processed SYNTH-CUSTOMER-MARKER-0000 record\n")
            hits = sealed_scan_mod.scan_customer_markers(Path(tmp))
            self.assertTrue(hits)

    def test_attack_28_checker_signs_itself(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dc2 = Path(tmp) / DC_REL
            (dc2 / "schema").mkdir(parents=True)
            shutil.copy(DC / "schema/signer_receipt.v1.schema.json",
                        dc2 / "schema/signer_receipt.v1.schema.json")
            forged = receipts.close_record({
                "schema_version": "p7-signer-receipt-v1",
                "reviewer_kind": "P7_MASTER_CHECKER",  # 不在枚举内
                "provider": "self", "actual_model_id": "m",
                "model_version": "v", "task_thread_session_id": "s",
                "input_commit": "c" * 40, "input_manifest_digest": "d" * 64,
                "prompt_digest": "e" * 64, "config_digest": "cfg",
                "tool_summary": "t", "output_report_digest": "f" * 64,
                "call_receipt": "cr", "exit_status": 0, "signed_at": "T",
                "session_isolation_attestation": {
                    "fresh_session_not_fork_not_resume": True,
                    "did_not_author_reviewed_scope": True,
                    "auto_memory_disabled_or_not_applicable": True,
                    "isolation_evidence": "x"},
                "verdict": "ACCEPT", "receipt_digest": ""}, "receipt_digest")
            rp = Path(tmp) / "r.json"
            rp.write_text(json.dumps(forged), encoding="utf-8")
            errors = V25.validate_signer_receipt(Path(tmp), rp)
            self.assertTrue(any("schema" in e for e in errors))
        checker_source = (P7 / "checker/p7_master_check.py").read_text(
            encoding="utf-8")
        self.assertIn("不给自身实现签字", checker_source)
        self.assertIn("不修改任何阶段状态", checker_source)
        self.assertNotIn("verdict\": \"ACCEPT", checker_source)

    def test_attack_29_launcher_subagent_impersonates_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dc = fh.build_launch_fixture(Path(tmp))
            fake_subagent_spawn = lambda path, cwd=None: {
                "capability": "AUTO_LAUNCHED", "session_id": "sub-1",
                "session_kind": "SUBAGENT", "actual_model": "claude-fable-5",
                "exit_status": 0, "auto_memory_disabled": True}
            with self.assertRaises(launcher_mod.LaunchRefused) as ctx:
                launcher_mod.start(Path(tmp), "M2", dc=dc, env={},
                                   spawn=fake_subagent_spawn)
            self.assertIn("impersonation", str(ctx.exception))
            outcome = json.loads(
                (dc / "milestones/M2/LAUNCH_OUTCOME.v1.json").read_text(
                    encoding="utf-8"))
            self.assertEqual(outcome["launch_capability"],
                             "REFUSED_SUBAGENT_IMPERSONATION")

    # ---- 指令第 3/4/5 条加固攻击面（2026-07-16 八项指令） ----

    def test_attack_31_typed_pair_divergence(self) -> None:
        """STAGE_DECISION 与 CLOSEOUT_RECEIPT 对不同候选作证 → FINAL 拒绝。"""
        with tempfile.TemporaryDirectory() as tmp:
            dc, _ = _final_fixture(Path(tmp))
            dp = dc / "milestones/M1/STAGE_DECISION.v1.json"
            decision = json.loads(dp.read_text(encoding="utf-8"))
            decision["candidate_commit"] = "f" * 40
            decision = receipts.close_record(
                {k: v for k, v in decision.items() if k != "receipt_digest"}
                | {"receipt_digest": ""}, "receipt_digest")
            dp.write_text(json.dumps(decision, ensure_ascii=False),
                          encoding="utf-8")
            ok, details = V25.check_final_receipts(Path(tmp),
                                                   {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("typed pair diverges" in d for d in details),
                            details)

    def test_attack_32_signer_v1_lacks_binding_in_final(self) -> None:
        """v1 签字回执（无 milestone/产品域/manifest 绑定）→ FINAL 拒绝。"""
        with tempfile.TemporaryDirectory() as tmp:
            dc, _ = _final_fixture(Path(tmp), signer_schema="v1")
            ok, details = V25.check_final_receipts(Path(tmp),
                                                   {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("lacks v2" in d for d in details), details)

    def test_attack_33_signer_milestone_transplant(self) -> None:
        """签字回执 milestone_id=M2 移植进 M1 关闭 → FINAL 拒绝。"""
        with tempfile.TemporaryDirectory() as tmp:
            dc, _ = _final_fixture(Path(tmp),
                                   signer_overrides={"milestone_id": "M2"})
            ok, details = V25.check_final_receipts(Path(tmp),
                                                   {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("transplant" in d and "milestone_id=M2" in d
                                for d in details), details)

    def test_attack_34_signer_product_scope_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dc, _ = _final_fixture(Path(tmp),
                                   signer_overrides={"product_scope": "A"})
            ok, details = V25.check_final_receipts(Path(tmp),
                                                   {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("product_scope mismatch" in d
                                for d in details), details)

    def test_attack_35_signer_manifest_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dc, _ = _final_fixture(Path(tmp), signer_overrides={
                "evidence_manifest_digest": "0" * 64})
            ok, details = V25.check_final_receipts(Path(tmp),
                                                   {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("evidence_manifest_digest != on-disk"
                                in d for d in details), details)

    def test_attack_36_exit_key_removed(self) -> None:
        """出口证据缺必需键 → FINAL 拒绝（即使摘要重新闭合）。"""
        with tempfile.TemporaryDirectory() as tmp:
            dc, _ = _final_fixture(Path(tmp))
            ep = dc / "milestones/M1/MILESTONE_EXIT_EVIDENCE.v1.json"
            evidence = json.loads(ep.read_text(encoding="utf-8"))
            evidence["exit_keys"].pop("REPOSITORY_WIDE_RESIDUAL_SCAN_PASS")
            evidence = receipts.close_record(
                {k: v for k, v in evidence.items() if k != "record_digest"}
                | {"record_digest": ""}, "record_digest")
            ep.write_text(json.dumps(evidence, ensure_ascii=False),
                          encoding="utf-8")
            ok, details = V25.check_final_receipts(Path(tmp),
                                                   {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("required exit key unsatisfied/absent" in d
                                for d in details), details)

    def test_attack_37_exit_evidence_file_tampered(self) -> None:
        """出口键指向的证据文件被改写 → 字节摘要复算拒绝。"""
        with tempfile.TemporaryDirectory() as tmp:
            dc, _ = _final_fixture(Path(tmp))
            ep = dc / "milestones/M1/MILESTONE_EXIT_EVIDENCE.v1.json"
            evidence = json.loads(ep.read_text(encoding="utf-8"))
            victim = Path(tmp) / evidence["exit_keys"][
                "FULL_TEST_SUITE_GREEN"]["evidence_path"]
            victim.write_text("TAMPERED", encoding="utf-8")
            ok, details = V25.check_final_receipts(Path(tmp),
                                                   {"milestone": "M1"})
            self.assertFalse(ok)
            self.assertTrue(any("exit key evidence digest mismatch" in d
                                for d in details), details)

    def test_attack_38_m2_final_without_real_s0(self) -> None:
        """M2 关闭却无真实 S0（未登记执行 / real_run=false）→ 机械拒绝。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / DC_REL / "contracts").mkdir(parents=True)
            (root / DC_REL / "schema").mkdir(parents=True)
            (root / EVAL_SPINE_REL / "contract").mkdir(parents=True)
            (root / EVAL_SPINE_REL / "calibration").mkdir(parents=True)
            shutil.copy(DC / "contracts/MILESTONE_EXIT_CONTRACT.v1.json",
                        root / DC_REL / "contracts/MILESTONE_EXIT_CONTRACT.v1.json")
            shutil.copy(DC / "schema/milestone_exit_evidence.v1.schema.json",
                        root / DC_REL / "schema/milestone_exit_evidence.v1.schema.json")
            shutil.copy(ES / "contract/stage_and_kill.v2.json",
                        root / EVAL_SPINE_REL / "contract/stage_and_kill.v2.json")
            (root / EVAL_SPINE_REL / "calibration/stage_actual_state.v1.json"
             ).write_text(json.dumps({
                 "schema_version": "eval-spine-stage-actual-state-v1",
                 "executed_stages": [], "stage_receipts": {},
                 "real_run_executed": False}), encoding="utf-8")
            closeout = _mk_receipt("M2", "PASS")
            errors = V25._check_milestone_exits(
                root, "M2", closeout, receipts, [])
            self.assertTrue(any("real_run_executed=true" in e
                                for e in errors), errors)
            self.assertTrue(any("never actually executed" in e
                                for e in errors), errors)

    def test_attack_39_m2_s0_mirror_drift(self) -> None:
        """出口合同的 S0 六项镜像与阶段合同漂移 → FINAL 拒绝复制漂移。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / DC_REL / "contracts").mkdir(parents=True)
            (root / DC_REL / "schema").mkdir(parents=True)
            (root / EVAL_SPINE_REL / "contract").mkdir(parents=True)
            (root / EVAL_SPINE_REL / "calibration").mkdir(parents=True)
            shutil.copy(DC / "contracts/MILESTONE_EXIT_CONTRACT.v1.json",
                        root / DC_REL / "contracts/MILESTONE_EXIT_CONTRACT.v1.json")
            shutil.copy(DC / "schema/milestone_exit_evidence.v1.schema.json",
                        root / DC_REL / "schema/milestone_exit_evidence.v1.schema.json")
            drifted = json.loads((ES / "contract/stage_and_kill.v2.json"
                                  ).read_text(encoding="utf-8"))
            for stage in drifted["stages"]:
                if stage["stage_id"] == "S0_DETERMINISTIC_HYGIENE":
                    stage["exit_requires"] = stage["exit_requires"][:-1]
            (root / EVAL_SPINE_REL / "contract/stage_and_kill.v2.json"
             ).write_text(json.dumps(drifted, ensure_ascii=False),
                          encoding="utf-8")
            (root / EVAL_SPINE_REL / "calibration/stage_actual_state.v1.json"
             ).write_text(json.dumps({
                 "schema_version": "eval-spine-stage-actual-state-v1",
                 "executed_stages": [], "stage_receipts": {},
                 "real_run_executed": True}), encoding="utf-8")
            closeout = _mk_receipt("M2", "PASS")
            errors = V25._check_milestone_exits(
                root, "M2", closeout, receipts, [])
            self.assertTrue(any("mirror drifted" in e for e in errors), errors)

    def test_attack_40_unfrozen_milestone_exit_fail_closed(self) -> None:
        """M3 出口定义未冻结 → FINAL 不可关闭（fail-closed）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / DC_REL / "contracts").mkdir(parents=True)
            shutil.copy(DC / "contracts/MILESTONE_EXIT_CONTRACT.v1.json",
                        root / DC_REL / "contracts/MILESTONE_EXIT_CONTRACT.v1.json")
            closeout = _mk_receipt("M3", "PASS")
            errors = V25._check_milestone_exits(
                root, "M3", closeout, receipts, [])
            self.assertTrue(any("not FROZEN" in e for e in errors), errors)

    def test_attack_41_forged_head_binding_survives_digest_reclose(self) -> None:
        """Codex R4 BLOCKING 攻击重放：改 launched_at_head 后重算 record_digest。

        自证摘要必然通过——防线在①仓库态复核（假提交拒）与②哈希链 journal
        交叉绑定（真提交伪造拒：链内独立采集的 git_head 失配）。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            dc = fh.build_launch_fixture(tmp_root)
            spawn = lambda path, cwd=None: {
                "capability": "AUTO_LAUNCHED", "session_id": "fresh-41",
                "session_kind": "TOP_LEVEL_FRESH",
                "actual_model": "claude-fable-5",
                "exit_status": 0, "auto_memory_disabled": True}
            launcher_mod.start(tmp_root, "M2", dc=dc, env={}, spawn=spawn)
            self.assertEqual(
                launcher_mod.verify_launch_binding(tmp_root, "M2", dc=dc), [])
            record_path = dc / "milestones/M2/LAUNCH_RECORD.v2.json"
            record = json.loads(record_path.read_text(encoding="utf-8"))
            # ①假提交 + 重算摘要 → 仓库态复核拒
            fake = receipts.close_record(
                {k: v for k, v in record.items() if k != "record_digest"}
                | {"launched_at_head": "0" * 40, "record_digest": ""},
                "record_digest")
            errors = receipts.validate_launch_record(fake, repo_root=tmp_root)
            self.assertTrue(any("unknown to repository" in e for e in errors),
                            errors)
            # ②真提交伪造 + 重算摘要 → journal 交叉绑定拒
            (tmp_root / "later.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "-qm", "later"], cwd=tmp,
                           capture_output=True)
            later = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp,
                                   capture_output=True,
                                   text=True).stdout.strip()
            forged = receipts.close_record(
                {k: v for k, v in record.items() if k != "record_digest"}
                | {"launched_at_head": later, "record_digest": ""},
                "record_digest")
            record_path.write_text(json.dumps(forged, ensure_ascii=False),
                                   encoding="utf-8")
            self.assertEqual(
                receipts.validate_launch_record(forged, repo_root=tmp_root),
                [])  # 自证面 + 仓库态均无法区分 → 必须靠链
            binding_errors = launcher_mod.verify_launch_binding(
                tmp_root, "M2", dc=dc)
            self.assertTrue(binding_errors, "journal cross-binding must fire")

    def test_attack_30_numbered_serialism_ignores_y_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_receipt(mdir, "M1", _mk_receipt("M1", "PASS"))
            _write_receipt(mdir, "M2", _mk_receipt("M2", "PASS"))
            rs = ready_set_mod.compute_ready_set(Path(tmp),
                                                 milestones_dir=mdir,
                                                 route="a")
            # 编号串行会先做 M3 再 M4/M5；Y 图真相：M3 与 M6 并行 ready，
            # M4/M5/M7 全部未 ready
            self.assertTrue(rs["M3"]["ready"] and rs["M6"]["ready"])
            self.assertFalse(rs["M4"]["ready"] or rs["M5"]["ready"]
                             or rs["M7"]["ready"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
