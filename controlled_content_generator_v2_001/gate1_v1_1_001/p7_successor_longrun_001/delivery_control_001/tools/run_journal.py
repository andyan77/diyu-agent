#!/usr/bin/env python3
"""RUN_JOURNAL v1 — 胶囊级只追加运行日志（哈希链 / 原子写入 / 崩溃可恢复 / 与 Git 互校）。

真源：AB_DUAL_PRODUCT_DELIVERY_PLAN.v2.5.md §三 3.3′ 与 P1/M1 §十一。

不变量：
  1. 只追加：既有字节永不改写（repair 仅允许截断"半写尾巴"，且必须显式调用并留审计记录）。
  2. 原子写入：单条记录一次 os.write 写入（O_APPEND），随后 fsync。
  3. 单调序号：seq 从 1 起严格 +1，不可倒退、不可跳号。
  4. 哈希链：record_digest = sha256(canonical_json(record 去 record_digest 字段))；
     每条记录携带 prev_record_digest（首条为 "GENESIS"）。
  5. 崩溃恢复：文件尾部无换行/不可解析 = 半写记录，可识别、可显式截断；
     链中间任何损坏 = journal 无效，返回 STOP_RUN_JOURNAL_INVALID。
  6. Git 互校：记录携带 git_head 与 dirty-tree 摘要；verify --git-root 时与 live git 对照。

用法：
  run_journal.py append --journal J.jsonl --git-root R --json '{...业务字段...}'
  run_journal.py verify --journal J.jsonl [--git-root R]
  run_journal.py head   --journal J.jsonl
  run_journal.py repair --journal J.jsonl        # 仅截断半写尾巴
  run_journal.py selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

JOURNAL_SCHEMA = "p7-run-journal-v1"
GENESIS = "GENESIS"

# 业务必填字段（P1 §十一 最低清单）
REQUIRED_BUSINESS_FIELDS = (
    "session_id", "run_id", "input_commit", "dirty_tree_digest",
    "capsule", "state", "requested_model", "actual_model",
    "subagent_ids", "last_green_commit", "verification_state",
    "next_action", "stop_reason",
)


def canonical_digest(record: dict) -> str:
    unsigned = {k: v for k, v in record.items() if k != "record_digest"}
    blob = json.dumps(unsigned, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _git(root: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", root, *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def git_facts(root: str) -> dict:
    head = _git(root, "rev-parse", "HEAD").strip()
    porcelain = _git(root, "status", "--porcelain")
    dirty_digest = hashlib.sha256(porcelain.encode("utf-8")).hexdigest()
    return {"git_head": head, "dirty_tree_digest": dirty_digest}


def parse_journal(path: Path) -> dict:
    """解析并验链。返回:
    {status: VALID|EMPTY|MISSING|PARTIAL_TAIL|INVALID,
     records: [完整且验链通过的记录],
     partial_tail_bytes: int, errors: [...]}
    PARTIAL_TAIL = 尾部存在半写记录但其前全部有效（崩溃场景，可显式 repair）。
    INVALID     = 链中任何完整行损坏/断链/倒序（不可自动修复 → STOP_RUN_JOURNAL_INVALID）。
    """
    if not path.exists():
        return {"status": "MISSING", "records": [], "partial_tail_bytes": 0,
                "errors": ["journal file missing"]}
    raw = path.read_bytes()
    if not raw:
        return {"status": "EMPTY", "records": [], "partial_tail_bytes": 0,
                "errors": []}
    lines = raw.split(b"\n")
    partial = lines[-1]  # 完整文件以 \n 结尾 → 最后应为空
    complete = [l for l in lines[:-1]]
    records: list[dict] = []
    errors: list[str] = []
    prev_digest = GENESIS
    for i, line in enumerate(complete, start=1):
        try:
            rec = json.loads(line.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            errors.append(f"line {i}: unparseable complete line")
            return {"status": "INVALID", "records": records,
                    "partial_tail_bytes": len(partial), "errors": errors}
        if rec.get("journal_schema") != JOURNAL_SCHEMA:
            errors.append(f"line {i}: wrong journal_schema")
        if rec.get("seq") != i:
            errors.append(f"line {i}: seq {rec.get('seq')} != {i} (monotonic breach)")
        if rec.get("prev_record_digest") != prev_digest:
            errors.append(f"line {i}: prev_record_digest chain mismatch")
        if rec.get("record_digest") != canonical_digest(rec):
            errors.append(f"line {i}: record_digest recompute mismatch")
        missing = [f for f in REQUIRED_BUSINESS_FIELDS if f not in rec]
        if missing:
            errors.append(f"line {i}: missing fields {missing}")
        if errors:
            return {"status": "INVALID", "records": records,
                    "partial_tail_bytes": len(partial), "errors": errors}
        prev_digest = rec["record_digest"]
        records.append(rec)
    if partial:
        return {"status": "PARTIAL_TAIL", "records": records,
                "partial_tail_bytes": len(partial),
                "errors": [f"half-written tail of {len(partial)} bytes "
                           "(crash artifact; run repair to truncate)"]}
    return {"status": "VALID" if records else "EMPTY", "records": records,
            "partial_tail_bytes": 0, "errors": []}


def append_record(path: Path, business: dict, git_root: str | None) -> dict:
    state = parse_journal(path)
    if state["status"] in ("INVALID",):
        raise SystemExit("STOP_RUN_JOURNAL_INVALID: refuse append on corrupt chain: "
                         + "; ".join(state["errors"]))
    if state["status"] == "PARTIAL_TAIL":
        raise SystemExit("STOP_RUN_JOURNAL_INVALID: half-written tail present; "
                         "run explicit repair before append")
    missing = [f for f in REQUIRED_BUSINESS_FIELDS if f not in business]
    if missing:
        raise SystemExit(f"missing required business fields: {missing}")
    records = state["records"]
    rec = dict(business)
    rec["journal_schema"] = JOURNAL_SCHEMA
    rec["seq"] = len(records) + 1
    rec["prev_record_digest"] = (records[-1]["record_digest"] if records
                                 else GENESIS)
    rec["written_at"] = datetime.now(timezone.utc).isoformat()
    if git_root:
        facts = git_facts(git_root)
        rec["git_head"] = facts["git_head"]
        # dirty_tree_digest 由调用方传入时保留（记录"动作前"快照）；未传则取现值
        if not rec.get("dirty_tree_digest") or rec["dirty_tree_digest"] == "LIVE":
            rec["dirty_tree_digest"] = facts["dirty_tree_digest"]
    rec["record_digest"] = canonical_digest(rec)
    line = (json.dumps(rec, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        n = os.write(fd, line)
        if n != len(line):
            raise SystemExit("short write; journal may hold partial tail")
        os.fsync(fd)
    finally:
        os.close(fd)
    return rec


def verify(path: Path, git_root: str | None) -> int:
    state = parse_journal(path)
    out = {"status": state["status"], "record_count": len(state["records"]),
           "errors": state["errors"]}
    if git_root and state["records"]:
        last = state["records"][-1]
        try:
            head_exists = subprocess.run(
                ["git", "-C", git_root, "cat-file", "-e",
                 f"{last['git_head']}^{{commit}}"],
                capture_output=True).returncode == 0
        except OSError:
            head_exists = False
        out["last_record_git_head"] = last.get("git_head")
        out["last_record_git_head_exists_in_repo"] = head_exists
        if not head_exists:
            out["status"] = "INVALID"
            out["errors"] = out["errors"] + [
                "last record git_head not found in repository "
                "(journal contradicts git) -> STOP_RUN_JOURNAL_INVALID"]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["status"] in ("VALID", "EMPTY") else 1


def repair(path: Path) -> int:
    state = parse_journal(path)
    if state["status"] != "PARTIAL_TAIL":
        print(f"nothing to repair (status={state['status']})")
        return 0 if state["status"] in ("VALID", "EMPTY") else 1
    raw = path.read_bytes()
    keep = raw[: len(raw) - state["partial_tail_bytes"]]
    fd = os.open(path, os.O_WRONLY)
    try:
        os.ftruncate(fd, len(keep))
        os.fsync(fd)
    finally:
        os.close(fd)
    print(json.dumps({"repaired": True,
                      "truncated_bytes": state["partial_tail_bytes"],
                      "surviving_records": len(state["records"])},
                     ensure_ascii=False))
    return 0


def _biz(seq_tag: str) -> dict:
    return {"session_id": "S", "run_id": "R", "input_commit": "c" * 40,
            "dirty_tree_digest": "d" * 64, "capsule": seq_tag,
            "state": "ACTIVE", "requested_model": "fable",
            "actual_model": "claude-fable-5", "subagent_ids": [],
            "last_green_commit": "c" * 40, "verification_state": "GREEN",
            "next_action": "next", "stop_reason": None}


def selftest() -> int:
    failures: list[str] = []

    def expect(name: str, cond: bool) -> None:
        print(f"[{'ok' if cond else 'FAIL'}] run_journal_selftest:{name}")
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        j = Path(tmp) / "J.jsonl"
        r1 = append_record(j, _biz("C1"), None)
        r2 = append_record(j, _biz("C2"), None)
        s = parse_journal(j)
        expect("two_records_valid", s["status"] == "VALID" and len(s["records"]) == 2)
        expect("chain_links", s["records"][1]["prev_record_digest"] == r1["record_digest"])
        expect("digest_recomputable",
               canonical_digest(s["records"][1]) == r2["record_digest"])

        # 崩溃：半写尾巴可识别，且 append 拒绝
        with open(j, "ab") as f:
            f.write(b'{"half":')
        s = parse_journal(j)
        expect("partial_tail_detected", s["status"] == "PARTIAL_TAIL"
               and len(s["records"]) == 2)
        try:
            append_record(j, _biz("C3"), None)
            expect("append_refused_on_partial_tail", False)
        except SystemExit:
            expect("append_refused_on_partial_tail", True)
        expect("repair_truncates_partial", repair(j) == 0
               and parse_journal(j)["status"] == "VALID")

        # 篡改中间记录 → INVALID
        lines = j.read_bytes().split(b"\n")
        tampered = lines[0].replace(b'"capsule":"C1"', b'"capsule":"CX"')
        j.write_bytes(b"\n".join([tampered] + lines[1:]))
        expect("mid_chain_tamper_detected", parse_journal(j)["status"] == "INVALID")

        # 序号倒退 → INVALID
        j2 = Path(tmp) / "J2.jsonl"
        a = append_record(j2, _biz("C1"), None)
        forged = dict(a)
        forged["seq"] = 1  # 重复/倒退序号
        forged["prev_record_digest"] = a["record_digest"]
        forged["record_digest"] = canonical_digest(forged)
        with open(j2, "ab") as f:
            f.write((json.dumps(forged, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")) + "\n").encode())
        expect("seq_regression_detected", parse_journal(j2)["status"] == "INVALID")

        # 缺必填业务字段 → append 拒绝
        j3 = Path(tmp) / "J3.jsonl"
        bad = _biz("C1")
        bad.pop("stop_reason")
        try:
            append_record(j3, bad, None)
            expect("missing_field_refused", False)
        except SystemExit:
            expect("missing_field_refused", True)

        # journal 缺失可识别
        expect("missing_journal_detected",
               parse_journal(Path(tmp) / "NO.jsonl")["status"] == "MISSING")

    print("RUN_JOURNAL_SELFTEST:", "ALL_PASS" if not failures else f"FAILED {failures}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("append", "verify", "head", "repair"):
        p = sub.add_parser(name)
        p.add_argument("--journal", required=True)
        if name in ("append", "verify"):
            p.add_argument("--git-root")
        if name == "append":
            p.add_argument("--json", required=True,
                           help="业务字段 JSON（P1 §十一 必填清单）")
    sub.add_parser("selftest")
    args = ap.parse_args()
    if args.cmd == "selftest":
        return selftest()
    path = Path(args.journal)
    if args.cmd == "append":
        rec = append_record(path, json.loads(args.json), args.git_root)
        print(json.dumps({"appended_seq": rec["seq"],
                          "record_digest": rec["record_digest"]},
                         ensure_ascii=False))
        return 0
    if args.cmd == "verify":
        return verify(path, args.git_root)
    if args.cmd == "head":
        state = parse_journal(path)
        last = state["records"][-1] if state["records"] else None
        print(json.dumps({"status": state["status"], "head": last},
                         ensure_ascii=False, indent=2))
        return 0 if state["status"] in ("VALID", "EMPTY") else 1
    if args.cmd == "repair":
        return repair(path)
    return 2


if __name__ == "__main__":
    sys.exit(main())
