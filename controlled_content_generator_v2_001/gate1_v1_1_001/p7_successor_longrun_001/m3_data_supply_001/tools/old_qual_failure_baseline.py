#!/usr/bin/env python3
"""旧 QUAL-A/B 机械失败基线（R0）。

机器证明（非文档口述）：M3 v1 冻结 QUAL 数据无法通过 measurement_qualification.v2 的
每套逐模块下限。只读**公开聚合**（QUAL_{A,B}_GOLD_FROZEN_RECEIPT.v1.json 的 class_counts），
零明文接触。

判据分三档，绝不伪造：
  DEFINITIVE_FAIL   —— 实际值（或其上界）< 要求 ⇒ 确定不达标（如缺模块=0，或 CONTRADICTED
                       总数上界 < 300 已足以判败）。
  INDETERMINATE     —— 该聚合无法判定通过/失败（需保全工具全量 per-class 计数，如
                       legal_controls 要 NATURAL∩LOW/MED、natural_legal_supported 要 NATURAL 子集）。
  OUT_OF_SCOPE      —— 非本数据基线口径（cost 事件属 M4 运行产物）。

verdict=FAIL 仅当存在 DEFINITIVE_FAIL；本基线预期两套均 FAIL。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/diyu/worktrees/gate1-longrun-001")
P7REL = "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001"
P7 = ROOT / P7REL
sys.path.insert(0, str(P7 / "delivery_control_001/tools"))
import receipts  # noqa: E402

CONTRACT = P7 / "eval_audit_spine_001/contract/measurement_qualification.v2.json"
QUAL_DIR = P7 / "m3_data_supply_001/gold/qual"

# 缺模块（M3 v1 冻结 gold 只覆盖 risk+entailment；其余 7 模块 gold 字段整段缺失=0）
ABSENT_MODULE_KEYS = (
    "reference_extraction_positive_cases", "reference_extraction_negative_controls",
    "claim_atomization_positive_cases", "claim_atomization_negative_controls",
    "fact_chain_high_risk_unsafe_cases", "fact_chain_natural_legal_cases",
    "formulaic_double_reviewed_pairs_total", "formulaic_positive_pairs_minimum",
    "formulaic_negative_pairs_minimum", "formulaic_necessary_grammar_pairs_minimum",
    "deterministic_disclosure_cases_total", "deterministic_disclosure_obligation_types_required",
    "omission_misleading_high_risk_cases", "omission_nonmisleading_controls",
    "review_double_reviewed_items", "review_judgment_records",
)


def _load_counts(set_id: str) -> dict:
    rc = json.loads((QUAL_DIR / f"QUAL_{set_id}_GOLD_FROZEN_RECEIPT.v1.json")
                    .read_text(encoding="utf-8"))
    cc = rc["class_counts"]
    risk = cc.get("risk", {})
    ent = cc.get("entailment", {})
    fam = cc.get("per_family", {})
    return {
        "gold_count": rc.get("gold_count"),
        "risk_high_critical": risk.get("HIGH", 0) + risk.get("CRITICAL", 0),
        "risk_low_medium_upper": risk.get("LOW", 0) + risk.get("MEDIUM", 0),
        "entailment_contradicted_upper": ent.get("CONTRADICTED", 0),
        "entailment_unknown_upper": ent.get("UNKNOWN", 0),
        "entailment_supported_upper": ent.get("SUPPORTED", 0),
        "families_present": sorted(fam.keys()),
    }


def evaluate_set(set_id: str, mins: dict) -> dict:
    c = _load_counts(set_id)
    rows = []

    def row(key, actual, verdict, note=""):
        req = mins.get(key)
        rows.append({"key": key, "required": req, "actual_or_bound": actual,
                     "verdict": verdict, "note": note})

    # 在场模块（上界推理即可判败）
    row("risk_classification_high_risk_cases", c["risk_high_critical"],
        "DEFINITIVE_FAIL" if c["risk_high_critical"] < mins["risk_classification_high_risk_cases"] else "MET")
    row("high_risk_contradicted_cases", c["entailment_contradicted_upper"],
        "DEFINITIVE_FAIL" if c["entailment_contradicted_upper"] < mins["high_risk_contradicted_cases"] else "INDETERMINATE",
        "聚合仅总 CONTRADICTED；上界<300 已足判败")
    row("high_risk_unknown_cases", c["entailment_unknown_upper"],
        "DEFINITIVE_FAIL" if c["entailment_unknown_upper"] < mins["high_risk_unknown_cases"] else "INDETERMINATE",
        "聚合仅总 UNKNOWN；上界<100 已足判败")
    # 上界≥要求但聚合不足以确认「NATURAL 子集」→ INDETERMINATE（不伪造达标）
    row("natural_legal_supported_cases", c["entailment_supported_upper"], "INDETERMINATE",
        "SUPPORTED 总数上界≥300，但缺 NATURAL∩SUPPORTED 拆分；需保全工具全量计数")
    row("risk_classification_legal_controls", c["risk_low_medium_upper"], "INDETERMINATE",
        "LOW+MEDIUM 上界≥300，但缺 NATURAL∩(LOW/MED) 拆分；需保全工具全量计数")

    # 缺模块（0）
    for key in ABSENT_MODULE_KEYS:
        if key in mins:
            row(key, 0, "DEFINITIVE_FAIL", "模块整段缺失，gold 字段=0")

    # 家族覆盖（可从聚合确认）
    fams = set(mins.get("required_content_families", []))
    present = set(c["families_present"])
    row("required_content_families", sorted(present),
        "MET" if fams and fams.issubset(present) else "DEFINITIVE_FAIL")

    definitive_fail = [r["key"] for r in rows if r["verdict"] == "DEFINITIVE_FAIL"]
    return {"set": set_id, "gold_count": c["gold_count"], "rows": rows,
            "definitive_fail_keys": definitive_fail,
            "verdict": "FAIL" if definitive_fail else "INDETERMINATE_OR_PASS"}


def compute_baseline() -> dict:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    mins = contract["qualification_set_minimums"]
    result = {
        "schema_version": "p7-old-qual-failure-baseline-v1",
        "purpose": "机械证明 M3 v1 旧 QUAL-A/B 无法通过 measurement_qualification.v2 每套逐模块下限",
        "contract_id": contract.get("contract_id"),
        "reads_only_public_aggregates": True,
        "plaintext_contact": "NONE (只读 class_counts)",
        "per_set": {sid: evaluate_set(sid, mins) for sid in ("A", "B")},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_digest": "",
    }
    both_fail = all(result["per_set"][s]["verdict"] == "FAIL" for s in ("A", "B"))
    result["overall_verdict"] = "OLD_QUAL_FAILS_M0_MINIMUMS" if both_fail else "UNEXPECTED_NOT_FAILING"
    return receipts.close_record(result, "record_digest")


def main() -> int:
    result = compute_baseline()
    out = P7 / "m3_data_supply_001/gold/qual/OLD_QUAL_FAILURE_BASELINE.v1.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for sid in ("A", "B"):
        s = result["per_set"][sid]
        print(f"QUAL-{sid}: verdict={s['verdict']} definitive_fail={len(s['definitive_fail_keys'])} keys")
    print("OVERALL:", result["overall_verdict"], "| record_digest", result["record_digest"][:16])
    # exit 0 = 旧 QUAL 如期确定性失败（恢复前提成立）；exit 1 = 旧 QUAL 意外未败（异常）
    return 0 if result["overall_verdict"] == "OLD_QUAL_FAILS_M0_MINIMUMS" else 1


if __name__ == "__main__":
    sys.exit(main())
