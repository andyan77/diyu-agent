#!/usr/bin/env python3
"""Y 形 ready-set 计算器（P1 §十三）。

从磁盘复算：typed 关闭回执（按具体状态值）、资格旗标（只认 PASS 回执上的
显式 true）、B 评测路线冻结记录——按 MILESTONE_DAG 计算哪些里程碑 ready。
禁止按 P1..P7 编号机械串行。

用法：
  ready_set.py [--root R] [--milestones-dir 覆盖] [--json]
  ready_set.py --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

DC = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


receipts = _load(DC / "tools/receipts.py", "p7_receipts")

# CLOSED_PASS 放行硬绑定（M3-R1 §5.5 M4 互锁加固）：仅把 state 改成 CLOSED_PASS 并
# 重算 record_digest 不足以放行 M4——必须同时携带以下绑定，且 launcher/ready-set 侧
# 逐条复核绑定所指工件在盘且摘要吻合、两套就绪回执 verdict==PASS。缺任一 → fail-closed。
#   文件绑定（path+digest，逐字节复算）：new closeout / QUAL-A 就绪 / QUAL-B 就绪 / HANDOFF
#   标量绑定（并入 record_digest，防篡改）：两套 active generation / qualification index 摘要 /
#                                          closure candidate 提交
_CLOSED_PASS_FILE_BINDINGS = (
    ("closeout_receipt_path", "closeout_receipt_digest"),
    ("qual_a_readiness_path", "qual_a_readiness_digest"),
    ("qual_b_readiness_path", "qual_b_readiness_digest"),
    ("handoff_path", "handoff_digest"),
)
_CLOSED_PASS_SCALAR_BINDINGS = (
    "qual_a_active_generation", "qual_b_active_generation",
    "qualification_index_digest", "closure_candidate_commit",
)
_READINESS_PATH_KEYS = ("qual_a_readiness_path", "qual_b_readiness_path")


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _readiness_verdict_pass(receipt: dict) -> bool:
    """就绪回执 PASS 复核：不只信 verdict 字段，另复算 failing_keys 为空。"""
    if not isinstance(receipt, dict):
        return False
    if receipt.get("verdict") != "PASS":
        return False
    failing = receipt.get("failing_keys")
    return isinstance(failing, list) and len(failing) == 0


def _verify_closed_pass_binding(status: dict,
                                milestones_dir: Path) -> tuple[bool, str]:
    """CLOSED_PASS 硬绑定复核。绑定路径相对 p7 根解析（milestones_dir.parents[1]）。"""
    binding = status.get("closed_pass_binding")
    if not isinstance(binding, dict):
        return False, ("CLOSED_PASS lacks closed_pass_binding block "
                       "(status-only forge insufficient) -> fail-closed")
    p7 = milestones_dir.parents[1]
    for path_key, digest_key in _CLOSED_PASS_FILE_BINDINGS:
        rel = binding.get(path_key)
        want = binding.get(digest_key)
        if not isinstance(rel, str) or not rel or not isinstance(want, str):
            return False, f"closed_pass_binding.{path_key}/{digest_key} missing"
        target = p7 / rel
        got = _sha256_file(target)
        if got is None:
            return False, (f"closed_pass_binding target absent: {rel} "
                           "-> fail-closed")
        if got != want:
            return False, (f"closed_pass_binding digest mismatch for {rel} "
                           f"({got[:12]}!={str(want)[:12]}) -> fail-closed")
    for scalar_key in _CLOSED_PASS_SCALAR_BINDINGS:
        val = binding.get(scalar_key)
        if not isinstance(val, str) or not val.strip():
            return False, f"closed_pass_binding.{scalar_key} missing/empty"
    # 两套就绪回执必须 verdict==PASS（且 failing_keys 空）
    for rk in _READINESS_PATH_KEYS:
        target = p7 / binding[rk]
        try:
            receipt = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return False, f"readiness receipt unreadable {binding[rk]} ({exc})"
        if not _readiness_verdict_pass(receipt):
            return False, (f"readiness receipt {binding[rk]} not PASS "
                           "-> fail-closed")
    return True, "closed_pass_binding verified (files+digests+readiness PASS)"


def m3_recovery_active(milestones_dir: Path | None = None) -> tuple[bool, str]:
    """M3-R1 恢复活动态硬门（fail-closed）。

    读 milestones/M3/recovery/M3_RECOVERY_STATUS.v1.json：
      - 不存在 → (False)：未处于恢复，正常行为（向后兼容既有测试）。
      - 存在但不可读 / record_digest 被篡改 → (True)：不安全，一律 fail-closed。
      - state != CLOSED_PASS（ACTIVE / HONEST_STOP）→ (True)：M3 v1 关闭被暂停，
        凡以 M3 为前置的里程碑（M4 首当其冲）不得放行。
      - state == CLOSED_PASS 但缺/坏 closed_pass_binding → (True)：仅伪造状态文件
        不足以放行 M4（§5.5 加固）；必须绑定 new closeout/两套就绪 PASS/HANDOFF/
        active generation/qualification index/closure candidate 且逐条在盘吻合。
      - state == CLOSED_PASS 且摘要自洽 且绑定复核通过 → (False)：诚实关闭，正常放行。
    """
    if milestones_dir is None:
        milestones_dir = DC / "milestones"
    path = milestones_dir / "M3" / "recovery" / "M3_RECOVERY_STATUS.v1.json"
    if not path.is_file():
        return False, "no M3 recovery status (not in recovery)"
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return True, f"M3 recovery status unreadable ({exc}) -> fail-closed"
    if status.get("record_digest") != receipts.canonical_digest(
            status, "record_digest"):
        return True, "M3 recovery status record_digest mismatch (tampered) -> fail-closed"
    state = status.get("state")
    if state != "CLOSED_PASS":
        return True, (f"M3-R1 recovery state={state} (not CLOSED_PASS): "
                      "M3 v1 close superseded, downstream fail-closed")
    binding_ok, binding_why = _verify_closed_pass_binding(status, milestones_dir)
    if not binding_ok:
        return True, f"M3-R1 CLOSED_PASS binding unverified: {binding_why}"
    return False, f"M3-R1 recovery CLOSED_PASS ({binding_why})"


def compute_ready_set(root: Path, milestones_dir: Path | None = None,
                      route: str | None = None) -> dict:
    """返回 {milestone: {status, ready, reasons}}。

    status ∈ CLOSED_<result> / ACTIVE / READY / WAITING；
    ready=True 仅当全部依赖以正确的 typed 值满足且本里程碑未关闭未激活。
    无效回执（缺字段/摘要不符/失败带旗标）→ 该前置视为不满足并记录原因。
    """
    dag = json.loads((DC / "MILESTONE_DAG.v1.json").read_text(encoding="utf-8"))
    results: dict[str, dict | None] = {}
    invalid: dict[str, str] = {}
    for milestone in dag["nodes"]:
        try:
            results[milestone] = receipts.milestone_result(
                root, milestone, milestones_dir=milestones_dir)
        except receipts.ReceiptError as exc:
            results[milestone] = None
            invalid[milestone] = str(exc)
    if route is None:
        route = receipts.route_binding(root)

    # M3-R1 恢复活动态硬门：恢复未 CLOSED_PASS 时，M3 v1 关闭回执不满足任何下游入口。
    # 置 results["M3"]=None → M4 的 TYPED_RESULT M3:PASS 与 QUALIFICATION_FLAG 均 UNMET。
    rec_active, rec_why = m3_recovery_active(
        milestones_dir if milestones_dir is not None else DC / "milestones")
    if rec_active:
        results["M3"] = None

    def requirement_met(req: dict) -> tuple[bool, str]:
        kind = req["kind"]
        if kind == "TYPED_RESULT":
            receipt = results.get(req["milestone"])
            got = receipt.get("result") if receipt else None
            ok = receipt is not None and got == req["value"]
            return ok, f"{req['milestone']}:{req['value']} got={got}"
        if kind == "TYPED_RESULT_ANY":
            receipt = results.get(req["milestone"])
            got = receipt.get("result") if receipt else None
            ok = receipt is not None and got in req["values"]
            return ok, f"{req['milestone']} in {req['values']} got={got}"
        if kind == "QUALIFICATION_FLAG":
            receipt = results.get(req["milestone"])
            ok = receipts.qualification_flag(receipt, req["flag"])
            return ok, f"{req['milestone']}.{req['flag']}=={ok} (PASS-receipt only)"
        if kind == "QUALIFICATION_FLAG_ANY_RESULT":
            receipt = results.get(req["milestone"])
            ok = (receipt is not None
                  and receipt.get("result") in req["allowed_results"]
                  and (receipt.get("qualification_flags") or {}).get(
                      req["flag"]) is True)
            return ok, f"{req['milestone']}.{req['flag']}=={ok}"
        if kind == "ROUTE_FROZEN":
            ok = route in req["any_of"]
            return ok, f"route_frozen={route}"
        return False, f"unknown requirement kind {kind}"

    out: dict[str, dict] = {}
    edges = {edge["to"]: edge for edge in dag["edges"]}
    for milestone in dag["nodes"]:
        receipt = results.get(milestone)
        reasons: list[str] = []
        if milestone in invalid:
            reasons.append(f"own receipt invalid: {invalid[milestone][:120]}")
        if receipt is not None:
            out[milestone] = {"status": f"CLOSED_{receipt['result']}",
                              "ready": False, "reasons": reasons}
            continue
        edge = edges.get(milestone)
        if edge is None:  # M1 无前置
            out[milestone] = {"status": "NO_PREDECESSOR_EDGE", "ready": False,
                              "reasons": ["M1 launches via P1 record, "
                                          "not via ready-set"]}
            continue
        met_all = True
        for req in edge.get("requires", []):
            ok, why = requirement_met(req)
            met_all &= ok
            reasons.append(("OK " if ok else "UNMET ") + why)
        if milestone == "M6" and route in ("a", "b"):
            for req in edge.get("route_conditional", {}).get(route, []):
                ok, why = requirement_met(req)
                met_all &= ok
                reasons.append(("OK " if ok else "UNMET ") + f"route({route}) " + why)
        for dep_milestone in invalid:
            pass  # 无效前置回执已通过 requirement_met 的 got=None 体现
        out[milestone] = {"status": "READY" if met_all else "WAITING",
                          "ready": met_all, "reasons": reasons}
    if rec_active:
        out["M3"] = {"status": "RECOVERY_ACTIVE", "ready": False,
                     "reasons": [rec_why,
                                 "M3 v1 close superseded during M3-R1 recovery; "
                                 "downstream (M4…) fail-closed until CLOSED_PASS"]}
    out["_invalid_receipts"] = invalid
    out["_route"] = route
    out["_m3_recovery_active"] = rec_active
    return out


# ---------------------------------------------------------------- selftest

def _mk_receipt(milestone: str, result: str, flags: dict | None = None) -> dict:
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


def selftest() -> int:
    import tempfile
    failures: list[str] = []

    def expect(name: str, cond: bool) -> None:
        print(f"[{'ok' if cond else 'FAIL'}] ready_set_selftest:{name}")
        if not cond:
            failures.append(name)

    def write_receipts(mdir: Path, rows: dict[str, dict]) -> None:
        for milestone, receipt in rows.items():
            d = mdir / milestone
            d.mkdir(parents=True, exist_ok=True)
            (d / "CLOSEOUT_RECEIPT.v1.json").write_text(
                json.dumps(receipt, ensure_ascii=False), encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mdir = root / "milestones"

        # M1 PASS → M2 ready（且只有 M2）
        write_receipts(mdir, {"M1": _mk_receipt("M1", "PASS")})
        rs = compute_ready_set(root, milestones_dir=mdir, route=None)
        expect("m1_pass_makes_m2_ready", rs["M2"]["ready"])
        expect("m3_waits_m2", not rs["M3"]["ready"])
        expect("numbered_serialism_rejected", not rs["M4"]["ready"]
               and not rs["M5"]["ready"] and not rs["M6"]["ready"])

        # M2 PASS + 路线(a) → M3 与 M6 同时 ready（Y 分叉并行）
        write_receipts(mdir, {"M2": _mk_receipt("M2", "PASS")})
        rs = compute_ready_set(root, milestones_dir=mdir, route="a")
        expect("route_a_m3_and_m6_parallel_ready",
               rs["M3"]["ready"] and rs["M6"]["ready"])

        # 路线(b) → M6 等待 M4:A2_QUALIFIED
        rs = compute_ready_set(root, milestones_dir=mdir, route="b")
        expect("route_b_m6_waits_a2", not rs["M6"]["ready"])
        # 未冻结路线 → M6 不 ready
        rs = compute_ready_set(root, milestones_dir=mdir, route=None)
        expect("unfrozen_route_blocks_m6", not rs["M6"]["ready"])

        # 通用 M4 PASS 回执（无 A2_QUALIFIED 旗标）不满足路线(b)
        write_receipts(mdir, {
            "M3": _mk_receipt("M3", "PASS", {"LOGICAL_CORE_SEPARATED": True}),
            "M4": _mk_receipt("M4", "PASS")})
        rs = compute_ready_set(root, milestones_dir=mdir, route="b")
        expect("generic_m4_closeout_rejected_for_route_b", not rs["M6"]["ready"])

        # A2_DIAGNOSTIC_FINAL 冒充 A2_QUALIFIED → 拒绝
        write_receipts(mdir, {"M4": _mk_receipt(
            "M4", "DIAGNOSTIC_FINAL",
            {"A2_DIAGNOSTIC_FINAL": True, "A_LIFT_READY": True})})
        rs = compute_ready_set(root, milestones_dir=mdir, route="b")
        expect("a2_diagnostic_final_rejected_for_route_b", not rs["M6"]["ready"])
        # 但 DIAGNOSTIC_FINAL + A_LIFT_READY 使 M5 ready（M4 有效最终结果）
        expect("m4_diagnostic_final_enables_m5", rs["M5"]["ready"])

        # 真 A2_QUALIFIED（PASS 回执）→ 路线(b) M6 ready
        write_receipts(mdir, {"M4": _mk_receipt(
            "M4", "PASS", {"A2_QUALIFIED": True, "A_LIFT_READY": True})})
        rs = compute_ready_set(root, milestones_dir=mdir, route="b")
        expect("a2_qualified_receipt_enables_route_b_m6", rs["M6"]["ready"])

        # M6 FAIL（即使伪造 B_LIFT_READY 旗标）→ 回执整体无效 → M7 永不 ready
        write_receipts(mdir, {"M6": _mk_receipt(
            "M6", "FAIL", {"B_LIFT_READY": True})})
        rs = compute_ready_set(root, milestones_dir=mdir, route="b")
        expect("m6_fail_with_forged_flag_rejected",
               not rs["M7"]["ready"] and "M6" in rs["_invalid_receipts"])

        # M6 HONEST_STOP → M7 不 ready
        write_receipts(mdir, {"M6": _mk_receipt("M6", "HONEST_STOP")})
        rs = compute_ready_set(root, milestones_dir=mdir, route="b")
        expect("m6_honest_stop_blocks_m7", not rs["M7"]["ready"])

        # M6 PASS + B_LIFT_READY=true → M7 ready
        write_receipts(mdir, {"M6": _mk_receipt(
            "M6", "PASS", {"B_LIFT_READY": True})})
        rs = compute_ready_set(root, milestones_dir=mdir, route="b")
        expect("m6_pass_blift_enables_m7", rs["M7"]["ready"])

        # M6 PASS 但无 B_LIFT_READY → M7 不 ready（普通关闭回执不放行搬仓）
        write_receipts(mdir, {"M6": _mk_receipt("M6", "PASS")})
        rs = compute_ready_set(root, milestones_dir=mdir, route="b")
        expect("m6_pass_without_blift_blocks_m7", not rs["M7"]["ready"])

        # 伪造 typed 状态（摘要不符）→ 回执视为不存在
        forged = _mk_receipt("M2", "PASS")
        forged["result"] = "PASS"
        forged["issued_at"] = "TAMPERED"  # 摘要未重算
        write_receipts(mdir, {"M2": forged})
        rs = compute_ready_set(root, milestones_dir=mdir, route="a")
        expect("forged_receipt_digest_detected",
               "M2" in rs["_invalid_receipts"] and not rs["M3"]["ready"])

        # REVIEW_READY 冒充 PASS → schema/终态校验拒绝
        review_ready = _mk_receipt("M2", "PASS")
        review_ready["result"] = "IMPLEMENTATION_COMPLETE_REVIEW_READY"
        review_ready = receipts.close_record(review_ready, "receipt_digest")
        write_receipts(mdir, {"M2": review_ready})
        rs = compute_ready_set(root, milestones_dir=mdir, route="a")
        expect("review_ready_cannot_satisfy_entry",
               "M2" in rs["_invalid_receipts"] and not rs["M3"]["ready"])

    print("READY_SET_SELFTEST:", "ALL_PASS" if not failures else f"FAILED {failures}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DC.parents[3]))
    ap.add_argument("--milestones-dir")
    ap.add_argument("--route", choices=["a", "b"])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    rs = compute_ready_set(
        Path(args.root),
        milestones_dir=Path(args.milestones_dir) if args.milestones_dir else None,
        route=args.route)
    print(json.dumps(rs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
