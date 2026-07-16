"""攻击矩阵与 launcher 测试共用的合成里程碑关闭 fixture。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve()
DC = HERE.parents[1]


def load_tool(name: str):
    spec = importlib.util.spec_from_file_location(
        f"p7_fixture_{name}", DC / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = load_tool("receipts")
journal_mod = load_tool("run_journal")


def build_m1_closeout_fixture(tmp: Path, *, predecessor_result: str = "PASS",
                              with_reviews: bool = True,
                              journal_state: str = "CLOSED_PASS",
                              flags: dict | None = None) -> Path:
    """构造带完整八件套 + journal 的合成控制面；返回其 delivery_control 目录。"""
    dc = tmp / "delivery_control_001"
    for sub in ("schema", "prompts", "tools", "journal", "milestones/M1",
                "state"):
        (dc / sub).mkdir(parents=True, exist_ok=True)
    for name in ("typed_receipt.v1.schema.json", "signer_receipt.v1.schema.json",
                 "handoff.v1.schema.json", "launch_record.v1.schema.json"):
        shutil.copy(DC / "schema" / name, dc / "schema" / name)
    shutil.copy(DC / "PROMPT_REGISTRY.v1.json", dc / "PROMPT_REGISTRY.v1.json")
    shutil.copy(DC / "MILESTONE_DAG.v1.json", dc / "MILESTONE_DAG.v1.json")
    for template in (DC / "prompts").glob("P*.template.md"):
        shutil.copy(template, dc / "prompts" / template.name)

    reviews = []
    if with_reviews:
        for i, kind in enumerate((
                "INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER",
                "CODEX_GPT_EXTERNAL_REVIEW_SIGNER")):
            signer = receipts.close_record({
                "schema_version": "p7-signer-receipt-v1",
                "reviewer_kind": kind, "provider": f"prov{i}",
                "actual_model_id": f"model-{i}", "model_version": "v",
                "task_thread_session_id": f"reviewer-session-{i}",
                "input_commit": "c" * 40, "input_manifest_digest": "d" * 64,
                "prompt_digest": "e" * 64, "config_digest": "cfg",
                "tool_summary": "read-only recompute",
                "output_report_digest": "f" * 64,
                "call_receipt": "receipt-evidence", "exit_status": 0,
                "signed_at": "T",
                "session_isolation_attestation": {
                    "fresh_session_not_fork_not_resume": True,
                    "did_not_author_reviewed_scope": True,
                    "auto_memory_disabled_or_not_applicable": True,
                    "isolation_evidence": "fresh"},
                "verdict": "ACCEPT", "receipt_digest": ""}, "receipt_digest")
            rp = dc / "milestones/M1" / f"review_{i}.signer_receipt.json"
            rp.write_text(json.dumps(signer, ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":")),
                          encoding="utf-8")
            reviews.append({
                "receipt_path": str(rp.relative_to(tmp)),
                "receipt_digest": hashlib.sha256(rp.read_bytes()).hexdigest(),
                "reviewer_kind": kind, "verdict": "ACCEPT"})

    mdir = dc / "milestones/M1"
    anchor = mdir / "MILESTONE_CONTRACT.v1.md"
    anchor.write_text("contract", encoding="utf-8")
    entry_row = [{"path": str(anchor.relative_to(tmp)),
                  "sha256": hashlib.sha256(b"contract").hexdigest()}]

    def manifest(name: str) -> dict:
        value = receipts.close_record({
            "schema_version": "p7-manifest-v1", "entry_count": len(entry_row),
            "entries": entry_row, "manifest_digest": ""}, "manifest_digest")
        (mdir / name).write_text(json.dumps(value, ensure_ascii=False),
                                 encoding="utf-8")
        return value

    manifest("INPUT_MANIFEST.v1.json")
    out_manifest = manifest("OUTPUT_MANIFEST.v1.json")
    ev_manifest = manifest("EVIDENCE_MANIFEST.v1.json")

    closeout = receipts.close_record({
        "schema_version": "p7-typed-receipt-v1",
        "receipt_kind": "CLOSEOUT_RECEIPT", "milestone_id": "M1",
        "product_scope": "SHARED", "result": predecessor_result,
        "terminal": True, "qualification_flags": flags or {},
        "candidate_commit": "c" * 40,
        "output_manifest_digest": out_manifest["manifest_digest"],
        "evidence_manifest_digest": ev_manifest["manifest_digest"],
        "review_bindings": reviews, "issued_at": "T",
        "issued_by_role": "M1_PRINCIPAL", "receipt_digest": ""},
        "receipt_digest")
    decision = dict(closeout)
    decision["receipt_kind"] = "STAGE_DECISION"
    decision = receipts.close_record(decision, "receipt_digest")
    (mdir / "CLOSEOUT_RECEIPT.v1.json").write_text(
        json.dumps(closeout, ensure_ascii=False), encoding="utf-8")
    (mdir / "STAGE_DECISION.v1.json").write_text(
        json.dumps(decision, ensure_ascii=False), encoding="utf-8")
    (mdir / "CLOSEOUT_REPORT.v1.md").write_text("report", encoding="utf-8")
    handoff = receipts.close_record({
        "schema_version": "p7-handoff-v1", "from_milestone": "M1",
        "to_milestone": ["M2"],
        "accepted_candidate_commit": "c" * 40,
        "control_plane_commit": "b" * 40,
        "active_contract_set_digest": "a" * 64,
        "input_manifest_digest": "d" * 64,
        "output_manifest_digest": out_manifest["manifest_digest"],
        "last_green_test_summary": "all green",
        "review_receipt_bindings": reviews or [
            {"receipt_path": "x", "receipt_digest": "0" * 64,
             "reviewer_kind": "K", "verdict": "ACCEPT"},
            {"receipt_path": "y", "receipt_digest": "0" * 64,
             "reviewer_kind": "K2", "verdict": "ACCEPT"}],
        "qualification_flags": flags or {},
        "route_binding": None,
        "next_entry_contract": "prompts/P2.M2.template.md",
        "next_prompt_template_digest": "1" * 64,
        "ready_set_result_digest": "2" * 64,
        "issued_at": "T", "handoff_digest": ""}, "handoff_digest")
    (mdir / "HANDOFF.v1.json").write_text(
        json.dumps(handoff, ensure_ascii=False), encoding="utf-8")
    journal_mod.append_record(dc / "journal/RUN_JOURNAL.v1.jsonl", {
        "session_id": "author-session-M1", "run_id": "R",
        "input_commit": "c" * 40, "dirty_tree_digest": "d" * 64,
        "capsule": "CLOSE", "state": journal_state,
        "requested_model": "fable", "actual_model": "claude-fable-5",
        "subagent_ids": [], "last_green_commit": "c" * 40,
        "verification_state": "GREEN", "next_action": "exit",
        "stop_reason": None}, None)
    return dc
