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
    """在 p7 根（mdir.parents[1]）落 §5.5 CLOSED_PASS 硬绑定所需真实工件，返回绑定块。

    corrupt: None=全真；'closeout_digest'=改 closeout 内容使摘要失配；
             'readiness_fail'=就绪回执 verdict!=PASS。用于负测。
    """
    import hashlib
    p7 = mdir.parents[1]

    def _write(rel: str, obj: dict) -> tuple[Path, str]:
        target = p7 / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        blob = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        target.write_bytes(blob)
        return target, hashlib.sha256(blob).hexdigest()

    _, closeout_digest = _write(
        "delivery_control_001/milestones/M3/CLOSEOUT_RECEIPT.v2.json",
        {"schema_version": "p7-typed-receipt-v1", "milestone_id": "M3",
         "result": "PASS", "receipt_kind": "CLOSEOUT_RECEIPT"})
    ra_verdict = "FAIL" if corrupt == "readiness_fail" else "PASS"
    ra_failing = ["risk_classification_high_risk_cases"] if corrupt == "readiness_fail" else []
    _, ra_digest = _write("m3_data_supply_001/gold/qual/QUAL_A_READINESS_RECEIPT.v1.json",
                          {"set": "A", "verdict": ra_verdict, "failing_keys": ra_failing})
    _, rb_digest = _write("m3_data_supply_001/gold/qual/QUAL_B_READINESS_RECEIPT.v1.json",
                          {"set": "B", "verdict": "PASS", "failing_keys": []})
    _, handoff_digest = _write(
        "delivery_control_001/milestones/M3/HANDOFF.v2.json",
        {"schema_version": "p7-handoff-v2", "milestone_id": "M3"})
    if corrupt == "closeout_digest":
        # 篡改文件内容但绑定仍写旧摘要 → 逐字节复算失配
        (p7 / "delivery_control_001/milestones/M3/CLOSEOUT_RECEIPT.v2.json"
         ).write_text('{"tampered": true}', encoding="utf-8")
    return {
        "closeout_receipt_path": "delivery_control_001/milestones/M3/CLOSEOUT_RECEIPT.v2.json",
        "closeout_receipt_digest": closeout_digest,
        "qual_a_readiness_path": "m3_data_supply_001/gold/qual/QUAL_A_READINESS_RECEIPT.v1.json",
        "qual_a_readiness_digest": ra_digest,
        "qual_b_readiness_path": "m3_data_supply_001/gold/qual/QUAL_B_READINESS_RECEIPT.v1.json",
        "qual_b_readiness_digest": rb_digest,
        "handoff_path": "delivery_control_001/milestones/M3/HANDOFF.v2.json",
        "handoff_digest": handoff_digest,
        "qual_a_active_generation": "QUAL_A_GEN_R3_001",
        "qual_b_active_generation": "QUAL_B_GEN_R3_001",
        "qualification_index_digest": "f" * 64,
        "closure_candidate_commit": "a" * 40,
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
