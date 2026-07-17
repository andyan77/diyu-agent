#!/usr/bin/env python3
"""signer_receipt v2.1（发起人 2026-07-17 载体豁免裁决）的正/负向测试。

v2.1 唯一放宽点：session_isolation_attestation.auto_memory_disabled_before_launch
从常量 true 改布尔；为 false 时必须携带非空 auto_memory_injection_disclosure。
其余必填字段与四键常量逐字承继 v2；v2 原 schema 与 v1 拒绝面不变。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]
P7 = DC.parent


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = _load(DC / "tools/receipts.py", "p7_receipts_v21_tests")
V25 = _load(P7 / "checker/v25_state_checks.py", "v25_v21_tests")

HEX = "e" * 64


def _base_receipt(schema_version: str) -> dict:
    value = {
        "schema_version": schema_version,
        "reviewer_kind": "INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER",
        "provider": "anthropic",
        "actual_model_id": "claude-opus-4-8",
        "model_version": {"value": "UNAVAILABLE",
                          "unavailable_reason": "provider does not expose revision",
                          "evidence_ref": "self-report"},
        "task_thread_session_id": "agent-abc123def456",
        "milestone_id": "M2",
        "product_scope": "SHARED",
        "input_commit": "e" * 40,
        "input_manifest_digest": HEX,
        "output_manifest_digest": HEX,
        "evidence_manifest_digest": HEX,
        "prompt_digest": HEX,
        "config_digest": "subagent dispatch, read-only",
        "tool_summary": "read-only recompute",
        "output_report_digest": HEX,
        "call_receipt": "{\"agent_id\": \"abc\"}",
        "exit_status": 0,
        "findings_summary": [],
        "signed_at": "2026-07-17T00:00:00+00:00",
        "session_isolation_attestation": {
            "fresh_session_not_fork_not_resume": True,
            "did_not_author_reviewed_scope": True,
            "auto_memory_disabled_or_not_applicable": True,
            "auto_memory_disabled_before_launch": True,
            "isolation_evidence": "fresh isolated agent; read-only recompute",
        },
        "verdict": "ACCEPT",
        "receipt_digest": "",
    }
    return receipts.close_record(value, "receipt_digest")


def _write(receipt: dict, directory: Path) -> Path:
    path = directory / "X.signer_receipt.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
    return path


class SignerReceiptV21Tests(unittest.TestCase):
    def _reclose(self, receipt: dict) -> dict:
        unsigned = {k: v for k, v in receipt.items() if k != "receipt_digest"}
        unsigned["receipt_digest"] = ""
        return receipts.close_record(unsigned, "receipt_digest")

    def test_v21_false_with_disclosure_is_signed(self) -> None:
        receipt = _base_receipt("p7-signer-receipt-v2.1")
        att = receipt["session_isolation_attestation"]
        att["auto_memory_disabled_before_launch"] = False
        att["auto_memory_injection_disclosure"] = (
            "harness 注入用户级 CLAUDE.md 与 GKB 项目记忆索引；与被审对象无关；未采用。")
        receipt = self._reclose(receipt)
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(receipt, Path(tmp))
            loaded = receipts.load_signer_receipt(path)
            self.assertEqual(loaded["verdict"], "ACCEPT")
            errors = V25.validate_signer_receipt(P7.parents[2], path)
            self.assertEqual(errors, [])

    def test_v21_false_without_disclosure_is_unsigned(self) -> None:
        receipt = _base_receipt("p7-signer-receipt-v2.1")
        receipt["session_isolation_attestation"][
            "auto_memory_disabled_before_launch"] = False
        receipt = self._reclose(receipt)
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(receipt, Path(tmp))
            with self.assertRaises(receipts.ReceiptError):
                receipts.load_signer_receipt(path)
            self.assertTrue(V25.validate_signer_receipt(P7.parents[2], path))

    def test_v2_false_stays_unsigned(self) -> None:
        """v2 原 schema 的常量约束不受 v2.1 影响（未放宽既有面）。"""
        receipt = _base_receipt("p7-signer-receipt-v2")
        receipt["session_isolation_attestation"][
            "auto_memory_disabled_before_launch"] = False
        receipt = self._reclose(receipt)
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(receipt, Path(tmp))
            with self.assertRaises(receipts.ReceiptError):
                receipts.load_signer_receipt(path)

    def test_v21_core_four_keys_still_const_true(self) -> None:
        receipt = _base_receipt("p7-signer-receipt-v2.1")
        att = receipt["session_isolation_attestation"]
        att["did_not_author_reviewed_scope"] = False
        att["auto_memory_disabled_before_launch"] = False
        att["auto_memory_injection_disclosure"] = "x" * 30
        receipt = self._reclose(receipt)
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(receipt, Path(tmp))
            with self.assertRaises(receipts.ReceiptError):
                receipts.load_signer_receipt(path)

    def test_v1_still_rejected_by_final_versions(self) -> None:
        self.assertNotIn("p7-signer-receipt-v1",
                         V25.FINAL_SIGNER_SCHEMA_VERSIONS)
        self.assertEqual(V25.FINAL_SIGNER_SCHEMA_VERSIONS,
                         {"p7-signer-receipt-v2", "p7-signer-receipt-v2.1"})


if __name__ == "__main__":
    unittest.main(verbosity=1)
