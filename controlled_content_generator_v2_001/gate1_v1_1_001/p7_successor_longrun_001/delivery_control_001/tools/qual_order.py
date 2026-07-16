#!/usr/bin/env python3
"""资格材料六步全序验证器（QUAL_ORDER_CONTRACT.v1.json 的机械执行）。

输入：步骤回执事件序列 [{code, seq, at}]；seq 为全局单调登记序号。
输出：违规清单；非空 = STOP_QUALIFICATION_ORDER_VIOLATION。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DC = Path(__file__).resolve().parents[1]

FREEZE_STEPS = {"A1_FACE_FROZEN", "A2_DOUBLE_BLIND_LABELED", "A3_GOLD_FROZEN",
                "B1_FACE_FROZEN", "B2_DOUBLE_BLIND_LABELED", "B3_GOLD_FROZEN"}
METHOD_STEPS = {"M4_METHOD_V1_FROZEN", "M4_METHOD_V2_FROZEN"}
REVEAL_STEPS = {"A6_REVEALED", "B6_REVEALED"}
PREDICT_STEPS = {"A5_QUAL_A_BLIND_PREDICTED", "B5_QUAL_B_BLIND_PREDICTED"}
IN_SET_ORDER = {
    "A": ["A1_FACE_FROZEN", "A2_DOUBLE_BLIND_LABELED", "A3_GOLD_FROZEN",
          "A5_QUAL_A_BLIND_PREDICTED", "A6_REVEALED"],
    "B": ["B1_FACE_FROZEN", "B2_DOUBLE_BLIND_LABELED", "B3_GOLD_FROZEN",
          "B5_QUAL_B_BLIND_PREDICTED", "B6_REVEALED"],
}


def validate_qual_order(events: list[dict]) -> list[str]:
    violations: list[str] = []
    seqs = [e.get("seq") for e in events]
    if any(not isinstance(s, int) for s in seqs):
        return ["event without monotonic seq (missing receipt = step never happened)"]
    if sorted(seqs) != seqs or len(set(seqs)) != len(seqs):
        violations.append("seq not strictly monotonic (backfill/补录 detected)")
    order = {e["code"]: e["seq"] for e in events}

    def before(a: str, b: str) -> bool:
        return a in order and b in order and order[a] < order[b]

    # 集内五步顺序
    for set_id, chain in IN_SET_ORDER.items():
        present = [code for code in chain if code in order]
        for left, right in zip(present, present[1:]):
            if order[left] > order[right]:
                violations.append(f"in-set order inverted: {right} before {left}")

    # 双集冻结（①②③×2）先于任何方法冻结与任何揭晓
    freeze_max = max((order[c] for c in FREEZE_STEPS if c in order), default=None)
    for gate_code in sorted((METHOD_STEPS | REVEAL_STEPS) & set(order)):
        if freeze_max is None:
            violations.append(f"{gate_code} occurred with no frozen QUAL sets at all")
            continue
        missing_freeze = sorted(FREEZE_STEPS - set(order))
        if missing_freeze:
            violations.append(
                f"{gate_code} occurred before both QUAL sets fully frozen "
                f"(missing {missing_freeze})")
            break
        if order[gate_code] < freeze_max:
            violations.append(
                f"{gate_code} occurred before both QUAL sets fully frozen")

    # 盲预测必须在方法冻结之后、揭晓之前
    if "A5_QUAL_A_BLIND_PREDICTED" in order:
        if not before("M4_METHOD_V1_FROZEN", "A5_QUAL_A_BLIND_PREDICTED"):
            violations.append("QUAL-A predicted before method v1 frozen")
        if "A6_REVEALED" in order and not before(
                "A5_QUAL_A_BLIND_PREDICTED", "A6_REVEALED"):
            violations.append("QUAL-A revealed before blind prediction")
    if "B5_QUAL_B_BLIND_PREDICTED" in order:
        if not before("M4_METHOD_V2_FROZEN", "B5_QUAL_B_BLIND_PREDICTED"):
            violations.append("QUAL-B predicted before method v2 frozen")
        if "B6_REVEALED" in order and not before(
                "B5_QUAL_B_BLIND_PREDICTED", "B6_REVEALED"):
            violations.append("QUAL-B revealed before blind prediction")

    # QUAL-B 首次使用前从未揭晓
    if ("B6_REVEALED" in order and "B5_QUAL_B_BLIND_PREDICTED" in order
            and order["B6_REVEALED"] < order["B5_QUAL_B_BLIND_PREDICTED"]):
        violations.append("QUAL-B revealed before its first blind use")

    # R2 禁止重建 QUAL-B：A6 揭晓之后出现任何 B1/B2/B3 = 看到结果后重建
    if "A6_REVEALED" in order:
        rebuilt = sorted(code for code in
                         ("B1_FACE_FROZEN", "B2_DOUBLE_BLIND_LABELED",
                          "B3_GOLD_FROZEN")
                         if code in order and order[code] > order["A6_REVEALED"])
        if rebuilt:
            violations.append(
                f"QUAL-B rebuilt after QUAL-A reveal: {rebuilt} "
                "(rebuild-after-failure forbidden)")

    return violations


def selftest() -> int:
    failures: list[str] = []

    def expect(name: str, cond: bool) -> None:
        print(f"[{'ok' if cond else 'FAIL'}] qual_order_selftest:{name}")
        if not cond:
            failures.append(name)

    def ev(*codes: str) -> list[dict]:
        return [{"code": code, "seq": i + 1, "at": f"t{i}"}
                for i, code in enumerate(codes)]

    legal_full = ev("A1_FACE_FROZEN", "B1_FACE_FROZEN",
                    "A2_DOUBLE_BLIND_LABELED", "B2_DOUBLE_BLIND_LABELED",
                    "A3_GOLD_FROZEN", "B3_GOLD_FROZEN",
                    "M4_METHOD_V1_FROZEN", "A5_QUAL_A_BLIND_PREDICTED",
                    "A6_REVEALED",
                    "M4_METHOD_V2_FROZEN", "B5_QUAL_B_BLIND_PREDICTED",
                    "B6_REVEALED")
    expect("legal_full_sequence_clean", validate_qual_order(legal_full) == [])

    reveal_first = ev("A1_FACE_FROZEN", "A2_DOUBLE_BLIND_LABELED",
                      "A3_GOLD_FROZEN", "M4_METHOD_V1_FROZEN", "A6_REVEALED",
                      "A5_QUAL_A_BLIND_PREDICTED")
    expect("reveal_before_prediction_detected",
           any("revealed before" in v for v in validate_qual_order(reveal_first)))

    method_before_freeze = ev("A1_FACE_FROZEN", "M4_METHOD_V1_FROZEN",
                              "A2_DOUBLE_BLIND_LABELED", "A3_GOLD_FROZEN",
                              "B1_FACE_FROZEN", "B2_DOUBLE_BLIND_LABELED",
                              "B3_GOLD_FROZEN")
    expect("method_frozen_before_double_freeze_detected",
           any("before both QUAL sets fully frozen" in v
               for v in validate_qual_order(method_before_freeze)))

    rebuild = legal_full[:9] + [
        {"code": "B1_FACE_FROZEN", "seq": 10, "at": "t9"},
        {"code": "B2_DOUBLE_BLIND_LABELED", "seq": 11, "at": "t10"},
        {"code": "B3_GOLD_FROZEN", "seq": 12, "at": "t11"},
        {"code": "M4_METHOD_V2_FROZEN", "seq": 13, "at": "t12"},
        {"code": "B5_QUAL_B_BLIND_PREDICTED", "seq": 14, "at": "t13"},
        {"code": "B6_REVEALED", "seq": 15, "at": "t14"}]
    expect("qual_b_rebuild_after_reveal_detected",
           any("rebuilt after QUAL-A reveal" in v
               for v in validate_qual_order(rebuild)))

    backfill = list(legal_full)
    backfill[3] = dict(backfill[3], seq=99)
    expect("backfill_seq_detected",
           any("monotonic" in v for v in validate_qual_order(backfill)))

    print("QUAL_ORDER_SELFTEST:", "ALL_PASS" if not failures
          else f"FAILED {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    events = json.load(sys.stdin)
    violations = validate_qual_order(events)
    print(json.dumps({"violations": violations,
                      "verdict": ("PASS" if not violations
                                  else "STOP_QUALIFICATION_ORDER_VIOLATION")},
                     ensure_ascii=False, indent=2))
    sys.exit(0 if not violations else 1)
