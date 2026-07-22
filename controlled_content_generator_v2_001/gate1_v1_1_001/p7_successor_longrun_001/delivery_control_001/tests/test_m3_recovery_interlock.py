#!/usr/bin/env python3
"""M3-R1 恢复活动态硬门（fail-closed）测试。

要求（M3-R1 Prompt 四.6 / R0.6）：M3 recovery 为 ACTIVE 时，M4 必须拒绝启动；
恢复 CLOSED_PASS 后放行；record_digest 被篡改亦 fail-closed（不安全=拦）。

纪律：不删断言、不 skip、不降阈值制造绿——每条以真实机制（摘要复算 + ready-set
值匹配 + launcher LaunchRefused）证明。
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

sys.path.insert(0, str(HERE.parent))
import fixture_helpers as fh  # noqa: E402

receipts = fh.receipts
ready_set_mod = fh.load_tool("ready_set")


# §三.1 语义互锁需要真 readiness 回执 + 完整 handoff：加载真实 pre_m0_readiness
def _load_p7_tool(rel: str, name: str):
    P7 = DC.parent
    spec = importlib.util.spec_from_file_location(name, P7 / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


prm = _load_p7_tool("m3_data_supply_001/tools/pre_m0_readiness.py", "prm_interlock_test")
qgen = _load_p7_tool("m3_data_supply_001/tools/qual_generation.py", "qgen_interlock_test")
fx = _load_p7_tool("m3_data_supply_001/tools/qual_core_fixtures.py", "fx_interlock_test")

_GOLD_SHA = "0" * 64
_FACES_SHA = "f" * 64

_HANDOFF_CLOSURE_RULE = (
    "关闭提交不自指：由 ORIGIN_ANCHOR.v2 锚定——锚提交的第一父提交必须等于锚文件内记录的 "
    "closeout_commit；tools/closure.py verify_closure 从分支头零外部知识机械重建 "
    "anchor→closeout→candidate 全链")


def _full_public_counts(set_id: str, *, failing: bool = False,
                        gold_sha: str = _GOLD_SHA, faces_sha: str = _FACES_SHA) -> dict:
    mins = prm.load_minimums()
    counts = {k: mins[k] + 5 for k in prm.COUNT_KEYS}
    if failing:
        counts["risk_classification_high_risk_cases"] = 0
    # §四.6 cluster-power：各统计率门分母类 cluster N 略超冻结 n_min → cluster-power PASS。
    cp_req = prm.cluster_power_requirements()["per_class_min_clusters"]
    cluster_counts = {k: cp_req[k] + 5 for k in cp_req}
    return {
        "set": set_id, "counts": counts, "cluster_counts": cluster_counts,
        "deterministic_disclosure_obligation_types_present": 4,
        "known_r5_input_binding_completeness": 1.0,
        "cost_expected_event_manifests": 1, "cost_rate_cards": 1,
        "module_gold_field_coverage": {m: list(prm.MODULE_GOLD_FIELDS[m])
                                       for m in prm.REQUIRED_MODULES},
        "family_coverage": list(prm.FAMILIES),
        "ab_mutually_exclusive": True, "dev_isolation": True,
        "qual_order_ok": True, "sealed_no_leak": True,
        "two_independent_labels_per_record": True,
        "adjudication_on_disagreement": True,
        "faces_sha256": faces_sha, "gold_sha256": gold_sha,
    }


def _mk_closeout(milestone: str, result: str, flags: dict | None = None) -> dict:
    value = {
        "schema_version": "p7-typed-receipt-v1",
        "receipt_kind": "CLOSEOUT_RECEIPT",
        "milestone_id": milestone,
        "product_scope": "SHARED",
        "result": result,
        "terminal": True,
        "qualification_flags": flags or {},
        "candidate_commit": "c" * 40,
        "output_manifest_digest": "d" * 64,
        "evidence_manifest_digest": "e" * 64,
        "review_bindings": [
            {"receipt_path": "r1.json", "receipt_digest": "1" * 64,
             "reviewer_kind": "INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER",
             "verdict": "ACCEPT"},
            {"receipt_path": "r2.json", "receipt_digest": "2" * 64,
             "reviewer_kind": "CODEX_GPT_EXTERNAL_REVIEW_SIGNER",
             "verdict": "ACCEPT"},
        ],
        "issued_at": "T", "issued_by_role": "M_PRINCIPAL",
        "receipt_digest": "",
    }
    return receipts.close_record(value, "receipt_digest")


def _write_closeouts(mdir: Path, rows: dict[str, dict]) -> None:
    for milestone, receipt in rows.items():
        d = mdir / milestone
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLOSEOUT_RECEIPT.v1.json").write_text(
            json.dumps(receipt, ensure_ascii=False), encoding="utf-8")


def _make_closed_pass_artifacts(mdir: Path, *, corrupt: str | None = None) -> dict:
    """在 p7 根（mdir.parents[1]）落 §5.5/§三.1 CLOSED_PASS 硬绑定所需**语义完整**工件，
    返回绑定块。工件均通过正式 parser/validator（typed receipt / handoff / readiness）。

    corrupt 负测：
      'closeout_digest'          文件内容篡改，绑定仍写旧摘要 → 逐字节复算失配
      'readiness_fail'           QUAL-A 就绪 verdict!=PASS（首过门拦）
      'closeout_result_fail'     closeout 文件 SHA 正确但 result=FAIL（语义非 M3 PASS）
      'candidate_mismatch'       handoff.accepted_candidate_commit != closeout/binding
      'index_arbitrary'          qualification_index_digest 为任意非摘要字符串
      'readiness_internally_invalid'  就绪 verdict=PASS/failing_keys=[] 但 rows 内有 pass=False
      §四.4 真实 generation 链负测：
      'wrong_generation'         binding.qual_a_active_generation 格式正确但≠盘上真 generation
      'index_tampered'           index 文件内容被改，文件 sha≠manifest 声明（内容篡改）
      'gold_faces_mismatch'      readiness gold/faces≠active generation manifest（gold/faces 不一致）
    """
    import hashlib
    p7 = mdir.parents[1]
    candidate = "c" * 40
    qual_dir = p7 / "m3_data_supply_001/gold/qual"
    qual_dir.mkdir(parents=True, exist_ok=True)

    def _write(rel: str, obj: dict) -> tuple[Path, str]:
        target = p7 / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        blob = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        target.write_bytes(blob)
        return target, hashlib.sha256(blob).hexdigest()

    # §四.4：落真实 generation 链（active pointer→manifest→index），gold/faces 与就绪回执一致。
    records = fx.build_core_gold_records()
    built = {}
    for sid in ("A", "B"):
        built[sid] = qgen.build_generation(
            records, set_id=sid, generation_id=f"QUAL_{sid}_GEN_R3_001",
            dataset_manifest_digest=fx.DMD, faces_sha256=_FACES_SHA,
            gold_sha256=_GOLD_SHA, qual_dir=qual_dir)
    if corrupt == "index_tampered":
        ipath = qual_dir / built["A"]["manifest"]["qualification_index_path"]
        ipath.write_text(ipath.read_text(encoding="utf-8") + " ", encoding="utf-8")

    # closeout：完整 typed 回执（candidate_commit="c"*40）；负测 result=FAIL
    co_result = "FAIL" if corrupt == "closeout_result_fail" else "PASS"
    closeout = _mk_closeout("M3", co_result)
    _, closeout_digest = _write(
        "delivery_control_001/milestones/M3/CLOSEOUT_RECEIPT.v2.json", closeout)

    # readiness A/B：完整就绪回执（真 evaluate_set_readiness + close_record）；
    # gold/faces 与 generation manifest 一致（gold_faces_mismatch 负测下 A 侧故意错开）。
    a_gold = "9" * 64 if corrupt == "gold_faces_mismatch" else _GOLD_SHA
    ra = receipts.close_record(prm.evaluate_set_readiness(
        "A", _full_public_counts("A", failing=(corrupt == "readiness_fail"),
                                 gold_sha=a_gold)), "record_digest")
    if corrupt == "readiness_internally_invalid":
        ra["rows"][0]["pass"] = False       # 内部 rows 有失败项
        ra["verdict"] = "PASS"              # 但 verdict/failing_keys 洗成 PASS/[]
        ra["failing_keys"] = []
        ra = receipts.close_record(ra, "record_digest")  # 自洽摘要，欺骗首过门
    _, ra_digest = _write(
        "m3_data_supply_001/gold/qual/QUAL_A_READINESS_RECEIPT.v1.json", ra)
    rb = receipts.close_record(prm.evaluate_set_readiness(
        "B", _full_public_counts("B")), "record_digest")
    _, rb_digest = _write(
        "m3_data_supply_001/gold/qual/QUAL_B_READINESS_RECEIPT.v1.json", rb)

    # handoff：完整 handoff.v2（from M3 / to [M4] / accepted_candidate_commit 三方一致）
    ho_candidate = "b" * 40 if corrupt == "candidate_mismatch" else candidate
    handoff = receipts.close_record({
        "schema_version": "p7-handoff-v2", "from_milestone": "M3",
        "to_milestone": ["M4"], "accepted_candidate_commit": ho_candidate,
        "active_contract_set_digest": "1" * 64, "input_manifest_digest": "2" * 64,
        "output_manifest_digest": "3" * 64, "evidence_manifest_digest": "4" * 64,
        "exit_evidence_digest": "5" * 64,
        "last_green_test_summary": "delivery_control + eval_audit_spine green",
        "review_receipt_bindings": [
            {"receipt_path": "r1.json", "receipt_digest": "1" * 64,
             "reviewer_kind": "OPUS_ADVERSARIAL", "verdict": "ACCEPT"},
            {"receipt_path": "r2.json", "receipt_digest": "2" * 64,
             "reviewer_kind": "CODEX_GPT_SIGNER", "verdict": "ACCEPT"}],
        "qualification_flags": {}, "route_binding": "a",
        "next_entry_contract": "M4_ENTRY",
        "next_prompt_template_digest": "6" * 64, "ready_set_result_digest": "7" * 64,
        "closure_rule": _HANDOFF_CLOSURE_RULE, "issued_at": "T",
        "handoff_digest": "",
    }, "handoff_digest")
    _, handoff_digest = _write(
        "delivery_control_001/milestones/M3/HANDOFF.v2.json", handoff)

    if corrupt == "closeout_digest":
        (p7 / "delivery_control_001/milestones/M3/CLOSEOUT_RECEIPT.v2.json"
         ).write_text('{"tampered": true}', encoding="utf-8")

    if corrupt == "index_arbitrary":
        index_digest = "not-a-real-index-digest"
    else:
        index_digest = qgen.combined_index_digest(
            built["A"]["manifest"], built["B"]["manifest"])
    a_gen = ("QUAL_A_GEN_WRONG_999" if corrupt == "wrong_generation"
             else "QUAL_A_GEN_R3_001")
    return {
        "closeout_receipt_path": "delivery_control_001/milestones/M3/CLOSEOUT_RECEIPT.v2.json",
        "closeout_receipt_digest": closeout_digest,
        "qual_a_readiness_path": "m3_data_supply_001/gold/qual/QUAL_A_READINESS_RECEIPT.v1.json",
        "qual_a_readiness_digest": ra_digest,
        "qual_b_readiness_path": "m3_data_supply_001/gold/qual/QUAL_B_READINESS_RECEIPT.v1.json",
        "qual_b_readiness_digest": rb_digest,
        "handoff_path": "delivery_control_001/milestones/M3/HANDOFF.v2.json",
        "handoff_digest": handoff_digest,
        "qual_a_active_generation": a_gen,
        "qual_b_active_generation": "QUAL_B_GEN_R3_001",
        "qualification_index_digest": index_digest,
        "closure_candidate_commit": candidate,
        "dataset_manifest_digest": fx.DMD,
        "gold_sha256": _GOLD_SHA, "faces_sha256": _FACES_SHA,
    }


def _write_recovery_status(mdir: Path, state: str, *, tamper: bool = False,
                           with_binding: bool = False,
                           corrupt_binding: str | None = None) -> None:
    rec_dir = mdir / "M3" / "recovery"
    rec_dir.mkdir(parents=True, exist_ok=True)
    status = {
        "schema_version": "p7-m3-recovery-status-v1",
        "milestone_id": "M3", "recovery_id": "M3_R1", "state": state,
        "opened_at": "T", "record_digest": "",
    }
    if with_binding or corrupt_binding:
        status["closed_pass_binding"] = _make_closed_pass_artifacts(
            mdir, corrupt=corrupt_binding)
    status = receipts.close_record(status, "record_digest")
    if tamper:
        # 翻 state 但不重算摘要（伪装 CLOSED_PASS 洗绿面）
        status["state"] = "CLOSED_PASS"
    (rec_dir / "M3_RECOVERY_STATUS.v1.json").write_text(
        json.dumps(status, ensure_ascii=False), encoding="utf-8")


def _fully_closed_milestones(mdir: Path) -> None:
    """M1/M2/M3 全 PASS 关闭（M3 带 LOGICAL_CORE_SEPARATED）→ 无恢复时 M4 应 READY。"""
    _write_closeouts(mdir, {
        "M1": _mk_closeout("M1", "PASS"),
        "M2": _mk_closeout("M2", "PASS"),
        "M3": _mk_closeout("M3", "PASS", {"LOGICAL_CORE_SEPARATED": True}),
    })


class M3RecoveryInterlock(unittest.TestCase):

    def test_helper_absent_is_inactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            mdir.mkdir()
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertFalse(active, why)

    def test_helper_active_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "ACTIVE")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("ACTIVE", why)

    def test_helper_tampered_digest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "ACTIVE", tamper=True)
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("tamper", why.lower())

    def test_helper_bare_closed_pass_fails_closed(self) -> None:
        # §5.5 加固：仅 state=CLOSED_PASS（无 closed_pass_binding）不足以放行。
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("binding", why.lower())

    def test_helper_closed_pass_with_binding_allows(self) -> None:
        # §5.5：CLOSED_PASS + 完整有效绑定（工件在盘、摘要吻合、两套就绪 PASS）→ 放行。
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS", with_binding=True)
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertFalse(active, why)

    def test_helper_closed_pass_forged_file_digest_fails_closed(self) -> None:
        # §5.5 负测：绑定在场但 closeout 文件内容被篡改（逐字节复算失配）→ fail-closed。
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="closeout_digest")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("digest mismatch", why.lower())

    def test_helper_closed_pass_readiness_not_pass_fails_closed(self) -> None:
        # §5.5 负测：绑定完整、摘要吻合，但 QUAL-A 就绪回执 verdict!=PASS → fail-closed。
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="readiness_fail")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("not pass", why.lower())

    def test_helper_closed_pass_missing_file_fails_closed(self) -> None:
        # §5.5 负测：绑定声明工件但文件被删（缺工件）→ fail-closed。
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS", with_binding=True)
            p7 = mdir.parents[1]
            (p7 / "delivery_control_001/milestones/M3/HANDOFF.v2.json").unlink()
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("absent", why.lower())

    # ---- §三.1 语义互锁负测（文件 SHA 自洽但内部语义无效必须 fail-closed） ----

    def test_helper_closeout_file_sha_ok_but_result_not_pass_fails_closed(self) -> None:
        # 负测1：closeout 文件字节摘要正确，但正式 parser 见 result=FAIL（非 M3 PASS）
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="closeout_result_fail")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("m3 pass closeout", why.lower())

    def test_helper_candidate_3way_mismatch_fails_closed(self) -> None:
        # 负测2：candidate 在 closeout/HANDOFF/binding 三方不一致
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="candidate_mismatch")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("candidate", why.lower())

    def test_helper_index_arbitrary_string_fails_closed(self) -> None:
        # 负测3：qualification_index_digest 为任意非摘要字符串（非 64-hex）
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="index_arbitrary")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("qualification_index_digest", why.lower())

    def test_helper_readiness_internally_invalid_fails_closed(self) -> None:
        # 负测4：就绪 verdict=PASS、failing_keys=[]（骗过首过门），但 rows 内有 pass=False
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="readiness_internally_invalid")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("recompute", why.lower())

    # ---- §四.4 真实 generation/index 绑定 3 类负测 ----

    def test_helper_wrong_generation_fails_closed(self) -> None:
        # §四.4 负测A：binding.qual_a_active_generation 格式正确但≠盘上真 generation id
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="wrong_generation")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("active generation", why.lower())

    def test_helper_index_tampered_content_fails_closed(self) -> None:
        # §四.4 负测B：index digest 格式正确但 index 文件内容被改（文件 sha≠manifest 声明）
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="index_tampered")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("generation chain", why.lower())

    def test_helper_gold_faces_mismatch_fails_closed(self) -> None:
        # §四.4 负测C：readiness gold/faces 与 active generation manifest 不一致
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS",
                                   corrupt_binding="gold_faces_mismatch")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertTrue(active, why)
            self.assertIn("gold/faces", why.lower())

    def test_ready_set_m4_ready_without_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mdir = root / "milestones"
            _fully_closed_milestones(mdir)
            rs = ready_set_mod.compute_ready_set(root, milestones_dir=mdir, route="a")
            self.assertTrue(rs["M4"]["ready"], rs["M4"]["reasons"])
            self.assertFalse(rs.get("_m3_recovery_active"))

    def test_ready_set_recovery_active_blocks_m4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mdir = root / "milestones"
            _fully_closed_milestones(mdir)
            _write_recovery_status(mdir, "ACTIVE")
            rs = ready_set_mod.compute_ready_set(root, milestones_dir=mdir, route="a")
            self.assertFalse(rs["M4"]["ready"],
                             "recovery ACTIVE must fail-closed M4")
            self.assertEqual(rs["M3"]["status"], "RECOVERY_ACTIVE")
            self.assertTrue(rs["_m3_recovery_active"])

    def test_ready_set_tampered_status_blocks_m4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mdir = root / "milestones"
            _fully_closed_milestones(mdir)
            _write_recovery_status(mdir, "ACTIVE", tamper=True)
            rs = ready_set_mod.compute_ready_set(root, milestones_dir=mdir, route="a")
            self.assertFalse(rs["M4"]["ready"],
                             "tampered CLOSED_PASS must still fail-closed")

    def test_ready_set_bare_closed_pass_still_blocks_m4(self) -> None:
        # §5.5：无绑定的 CLOSED_PASS 在 ready-set 层仍必须 fail-closed。
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mdir = root / "milestones"
            _fully_closed_milestones(mdir)
            _write_recovery_status(mdir, "CLOSED_PASS")
            rs = ready_set_mod.compute_ready_set(root, milestones_dir=mdir, route="a")
            self.assertFalse(rs["M4"]["ready"],
                             "bare CLOSED_PASS (no binding) must fail-closed M4")
            self.assertTrue(rs["_m3_recovery_active"])

    def test_ready_set_closed_pass_with_binding_reopens_m4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mdir = root / "milestones"
            _fully_closed_milestones(mdir)
            _write_recovery_status(mdir, "CLOSED_PASS", with_binding=True)
            rs = ready_set_mod.compute_ready_set(root, milestones_dir=mdir, route="a")
            self.assertTrue(rs["M4"]["ready"],
                            "CLOSED_PASS + verified binding must re-enable M4")
            self.assertFalse(rs["_m3_recovery_active"])

    def test_launcher_validate_entry_refuses_m4_on_recovery(self) -> None:
        launcher_mod = fh.load_tool("launcher")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dc = fh.build_launch_fixture(root)  # M1→M2 fixture (registry incl. M4)
            # 注入 M3 恢复 ACTIVE；M4 以 M3 为前置 → launcher 显式硬门须拒
            _write_recovery_status(dc / "milestones", "ACTIVE")
            with self.assertRaises(launcher_mod.LaunchRefused) as ctx:
                launcher_mod.validate_entry(root, "M4", dc=dc, env={})
            self.assertIn("recovery active", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
