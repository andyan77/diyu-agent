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


def _write_recovery_status(mdir: Path, state: str, *, tamper: bool = False) -> None:
    rec_dir = mdir / "M3" / "recovery"
    rec_dir.mkdir(parents=True, exist_ok=True)
    status = {
        "schema_version": "p7-m3-recovery-status-v1",
        "milestone_id": "M3", "recovery_id": "M3_R1", "state": state,
        "opened_at": "T", "record_digest": "",
    }
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

    def test_helper_closed_pass_allows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mdir = Path(tmp) / "milestones"
            _write_recovery_status(mdir, "CLOSED_PASS")
            active, why = ready_set_mod.m3_recovery_active(mdir)
            self.assertFalse(active, why)

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

    def test_ready_set_closed_pass_reopens_m4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mdir = root / "milestones"
            _fully_closed_milestones(mdir)
            _write_recovery_status(mdir, "CLOSED_PASS")
            rs = ready_set_mod.compute_ready_set(root, milestones_dir=mdir, route="a")
            self.assertTrue(rs["M4"]["ready"],
                            "CLOSED_PASS recovery must re-enable M4")
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
