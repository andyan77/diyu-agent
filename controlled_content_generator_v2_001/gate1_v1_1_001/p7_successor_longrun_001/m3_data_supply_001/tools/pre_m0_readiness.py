#!/usr/bin/env python3
"""PRE_M0 数据就绪硬门（R1）——把「逐套逐模块 M0 下限 + 模块 gold 字段覆盖 + 抽样互斥/
DEV 隔离/顺序/无泄漏」变成机器门，杜绝 M3 v1 那种「回执在场即绿」的形式假绿。

三产物：
  1. PRE_M0_DATA_REQUIREMENT_MATRIX —— 从 measurement_qualification.v2 + m0 spine 机械生成
     逐键映射（key/module/counter-or-gold-field/per-set required/reuse/统计口径/family/产生阶段）。
  2. evaluate_set_readiness(set, public_counts) —— 逐键 required/actual/delta/pass + 模块覆盖 +
     治理旗标；verdict=PASS 仅当全部达标。输入为**公开聚合计数**（保全工具产出，零明文）。
  3. PRE_M0_DATA_READINESS 回执（A/B 各一）—— evaluate 的落盘证据，checker FINAL 消费。

真源：eval_audit_spine_001/contract/measurement_qualification.v2.json（下限） +
      spine/{calibration,formulaic,m0}.py 的 gold_field_names/REQUIRED_MODULES/记录角色下限。
main-session 零明文：本工具只接受聚合计数字典，不读密封 gold 明文。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 本文件 = repo/ccg_v2/gate1/p7/m3_data_supply_001/tools/ → repo 根为 parents[5]
ROOT = Path(__file__).resolve().parents[5]
P7 = ROOT / "controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001"
sys.path.insert(0, str(P7 / "delivery_control_001/tools"))
import receipts  # noqa: E402

CONTRACT = P7 / "eval_audit_spine_001/contract/measurement_qualification.v2.json"
QUAL_DIR = P7 / "m3_data_supply_001/gold/qual"

REQUIRED_MODULES = (
    "reference_extraction", "claim_atomization", "risk_classification",
    "entailment", "fact_chain", "formulaic", "disclosure", "omission",
    "review_calibration",
)

# 每个模块的 gold 字段（spine gold_field_names 抽取；模块存在=其全部 gold 字段在场）
MODULE_GOLD_FIELDS = {
    "reference_extraction": ("gold_present", "gold_risk", "gold_attributes"),
    "claim_atomization": ("gold_present", "gold_risk", "gold_atom_partition"),
    "risk_classification": ("gold_risk",),
    "entailment": ("gold_label", "gold_risk"),
    "fact_chain": ("gold_risk", "gold_safe_to_clear"),
    "formulaic": ("axes", "verdict", "gold_formulaic"),
    "disclosure": ("gold_violation", "obligation_type"),
    "omission": ("gold_misleading", "gold_risk"),
    "review_calibration": ("decision", "hard_veto"),
}

# key -> (module, counter/gold-field 口径, reuse_allowed, statistic, stage)
# stage: M3 = 恢复内冻结（本门强制）；M4 = 运行产物（本门不计入 per-set 就绪）。
KEY_MAP = {
    "reference_extraction_positive_cases": ("reference_extraction", "gold_present=true 正样", True, "detection_positive", "M3"),
    "reference_extraction_negative_controls": ("reference_extraction", "gold_present=false 负控", True, "detection_negative", "M3"),
    "claim_atomization_positive_cases": ("claim_atomization", "gold_atom_partition 正样", True, "detection_positive", "M3"),
    "claim_atomization_negative_controls": ("claim_atomization", "负控", True, "detection_negative", "M3"),
    "risk_classification_high_risk_cases": ("risk_classification", "gold_risk∈{HIGH,CRITICAL}", True, "class_count", "M3"),
    "risk_classification_legal_controls": ("risk_classification", "NATURAL∩gold_risk∈{LOW,MEDIUM}", True, "class_count", "M3"),
    "high_risk_contradicted_cases": ("entailment", "high_risk∩gold_label=CONTRADICTED", True, "class_count", "M3"),
    "high_risk_unknown_cases": ("entailment", "high_risk∩gold_label=UNKNOWN", True, "class_count", "M3"),
    "natural_legal_supported_cases": ("entailment", "NATURAL_legal∩gold_label=SUPPORTED", True, "class_count", "M3"),
    "fact_chain_high_risk_unsafe_cases": ("fact_chain", "gold_safe_to_clear=false∩HIGH/CRITICAL", True, "class_count", "M3"),
    "fact_chain_natural_legal_cases": ("fact_chain", "NATURAL_legal 链", True, "class_count", "M3"),
    "formulaic_double_reviewed_pairs_total": ("formulaic", "fresh 双审 pair 总数", False, "pair_count", "M3"),
    "formulaic_positive_pairs_minimum": ("formulaic", "final_verdict=FORMULAIC", False, "pair_count", "M3"),
    "formulaic_negative_pairs_minimum": ("formulaic", "final_verdict=NOT_FORMULAIC", False, "pair_count", "M3"),
    "formulaic_necessary_grammar_pairs_minimum": ("formulaic", "final_verdict=NECESSARY_GRAMMAR", False, "pair_count", "M3"),
    "deterministic_disclosure_cases_total": ("disclosure", "确定性 disclosure gold", True, "det_count", "M3"),
    "omission_misleading_high_risk_cases": ("omission", "gold_misleading=true∩HIGH/CRITICAL", True, "class_count", "M3"),
    "omission_nonmisleading_controls": ("omission", "gold_misleading=false 控制", True, "class_count", "M3"),
    "review_double_reviewed_items": ("review_calibration", "双审 item", False, "item_count", "M3"),
    "review_judgment_records": ("review_calibration", "judgment 记录(2×item)", False, "record_count", "M3"),
    # 特殊键
    "deterministic_disclosure_obligation_types_required": ("disclosure", "distinct obligation_type 数", False, "type_coverage", "M3"),
    "known_r5_hard_veto_cases_and_registered_variants_recall": ("entailment", "已知 R5 硬否决+注册变体召回", False, "recall", "M3"),
    # cost：M4 运行产物（本 per-set 门不计）；矩阵登记阶段以备追踪
    "cost_events": ("cost", "完整成本事件", False, "event_count", "M4"),
    "cost_expected_event_manifests": ("cost", "expected 事件 manifest", False, "manifest", "M3"),
    "cost_source_event_manifests": ("cost", "source 事件 manifest", False, "manifest", "M3"),
    "cost_rate_cards": ("cost", "费率卡", False, "manifest", "M3"),
}

# per-set 就绪门只强制 stage==M3 且 statistic 为可计数/覆盖类的键；这些是「逐套逐模块数量硬门」
COUNT_KEYS = tuple(k for k, v in KEY_MAP.items()
                   if v[4] == "M3" and v[3] in
                   ("detection_positive", "detection_negative", "class_count",
                    "pair_count", "det_count", "item_count", "record_count"))
FAMILIES = ("F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
            "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
            "F5_ENTERPRISE_LONG_TERM_TRUST")


def load_minimums() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))["qualification_set_minimums"]


def evaluate_set_readiness(set_id: str, public_counts: dict,
                           mins: dict | None = None) -> dict:
    """对单套（A 或 B）以公开聚合计数评估就绪。返回未 close 的回执（调用方补 record_digest）。"""
    mins = mins or load_minimums()
    counts = public_counts.get("counts", {})
    rows = []
    all_pass = True

    for key in COUNT_KEYS:
        req = mins[key]
        actual = int(counts.get(key, 0))
        ok = actual >= req
        all_pass &= ok
        module, caliber, reuse, stat, stage = KEY_MAP[key]
        rows.append({"key": key, "module": module, "required": req,
                     "actual": actual, "delta": actual - req, "pass": ok,
                     "reuse_allowed": reuse, "statistic": stat})

    # obligation type coverage (>=4 distinct) —— 顶层聚合（同 known_r5_recall）
    obl_req = mins["deterministic_disclosure_obligation_types_required"]
    obl_actual = int(public_counts.get("deterministic_disclosure_obligation_types_present", 0))
    obl_ok = obl_actual >= obl_req
    all_pass &= obl_ok
    rows.append({"key": "deterministic_disclosure_obligation_types_required",
                 "module": "disclosure", "required": obl_req, "actual": obl_actual,
                 "delta": obl_actual - obl_req, "pass": obl_ok, "reuse_allowed": False,
                 "statistic": "type_coverage"})

    # known-R5 recall (>=1.0)
    r5_req = mins["known_r5_hard_veto_cases_and_registered_variants_recall"]
    r5_actual = float(public_counts.get("known_r5_recall", 0.0))
    r5_ok = r5_actual >= r5_req
    all_pass &= r5_ok
    rows.append({"key": "known_r5_hard_veto_cases_and_registered_variants_recall",
                 "module": "entailment", "required": r5_req, "actual": r5_actual,
                 "delta": round(r5_actual - r5_req, 4), "pass": r5_ok,
                 "reuse_allowed": False, "statistic": "recall"})

    # 模块 gold 字段覆盖（9 模块全部 gold 字段须在场）
    coverage = public_counts.get("module_gold_field_coverage", {})
    module_cov = {}
    for module in REQUIRED_MODULES:
        present = set(coverage.get(module, []))
        needed = set(MODULE_GOLD_FIELDS[module])
        cov_ok = needed.issubset(present)
        module_cov[module] = {"required_fields": sorted(needed),
                              "present": cov_ok,
                              "missing": sorted(needed - present)}
        all_pass &= cov_ok

    # 5 家族覆盖
    fam_present = set(public_counts.get("family_coverage", []))
    fam_ok = set(FAMILIES).issubset(fam_present)
    all_pass &= fam_ok

    # 治理旗标（保全工具证明；缺失=False=fail-closed）
    gov = {
        "ab_mutually_exclusive": bool(public_counts.get("ab_mutually_exclusive")),
        "dev_isolation": bool(public_counts.get("dev_isolation")),
        "qual_order_ok": bool(public_counts.get("qual_order_ok")),
        "sealed_no_leak": bool(public_counts.get("sealed_no_leak")),
        "two_independent_labels_per_record": bool(
            public_counts.get("two_independent_labels_per_record")),
        "adjudication_on_disagreement": bool(
            public_counts.get("adjudication_on_disagreement")),
    }
    gov_ok = all(gov.values())
    all_pass &= gov_ok

    failing = [r["key"] for r in rows if not r["pass"]]
    failing += [m for m, c in module_cov.items() if not c["present"]]
    if not fam_ok:
        failing.append("required_content_families")
    failing += [f"governance:{k}" for k, v in gov.items() if not v]

    return {
        "schema_version": "p7-pre-m0-data-readiness-v1",
        "set": set_id,
        "contract_id": "EAS-M0-QUALIFICATION-V2",
        "reads_public_aggregates_only": True,
        "main_session_plaintext_contact": "NONE",
        "rows": rows,
        "module_gold_field_coverage": module_cov,
        "family_coverage_ok": fam_ok,
        "family_present": sorted(fam_present),
        "governance": gov,
        "public_counts_faces_sha256": public_counts.get("faces_sha256"),
        "public_counts_gold_sha256": public_counts.get("gold_sha256"),
        "failing_keys": failing,
        "verdict": "PASS" if all_pass else "FAIL",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "record_digest": "",
    }


def recompute_verdict(receipt: dict) -> str:
    """从 rows/coverage/governance 重算 verdict —— 防手改 verdict:PASS 而 rows 有失败项。"""
    ok = all(r.get("pass") for r in receipt.get("rows", []))
    ok &= all(c.get("present") for c in
              receipt.get("module_gold_field_coverage", {}).values())
    ok &= bool(receipt.get("family_coverage_ok"))
    ok &= all(receipt.get("governance", {}).values())
    return "PASS" if ok else "FAIL"


def public_counts_from_old_qual(set_id: str) -> dict:
    """从旧冻结回执 class_counts 提取公开聚合（只 risk+entailment；其余模块 0/缺）——负测基线。"""
    rc = json.loads((QUAL_DIR / f"QUAL_{set_id}_GOLD_FROZEN_RECEIPT.v1.json")
                    .read_text(encoding="utf-8"))
    cc = rc["class_counts"]
    risk = cc.get("risk", {})
    ent = cc.get("entailment", {})
    fam = cc.get("per_family", {})
    counts = {k: 0 for k in COUNT_KEYS}
    # 上界填入（在场模块）——即便给上界仍不达标，证明确定性失败
    counts["risk_classification_high_risk_cases"] = risk.get("HIGH", 0) + risk.get("CRITICAL", 0)
    counts["high_risk_contradicted_cases"] = ent.get("CONTRADICTED", 0)
    counts["high_risk_unknown_cases"] = ent.get("UNKNOWN", 0)
    counts["natural_legal_supported_cases"] = ent.get("SUPPORTED", 0)
    counts["risk_classification_legal_controls"] = risk.get("LOW", 0) + risk.get("MEDIUM", 0)
    return {
        "set": set_id, "counts": counts,
        "deterministic_disclosure_obligation_types_present": 0,
        "known_r5_recall": 0.0,
        "module_gold_field_coverage": {"risk_classification": ["gold_risk"],
                                       "entailment": ["gold_label", "gold_risk"]},
        "family_coverage": sorted(fam.keys()),
        "ab_mutually_exclusive": True, "dev_isolation": True,
        "qual_order_ok": True, "sealed_no_leak": True,
        "two_independent_labels_per_record": True,
        "adjudication_on_disagreement": True,
        "faces_sha256": rc.get("faces_sha256"), "gold_sha256": rc.get("gold_sha256"),
        "source": "OLD_QUAL_v1 class_counts（负测基线，只读公开聚合）",
    }


def build_requirement_matrix(actuals: dict | None = None) -> dict:
    """机械生成 PRE_M0_DATA_REQUIREMENT_MATRIX。actuals={set: public_counts}；缺则填旧 QUAL 快照。"""
    mins = load_minimums()
    if actuals is None:
        actuals = {s: public_counts_from_old_qual(s) for s in ("A", "B")}
    entries = []
    for key, (module, caliber, reuse, stat, stage) in KEY_MAP.items():
        req = mins.get(key)
        per_set = {}
        for s in ("A", "B"):
            if isinstance(req, (int, float)) and stat not in ("manifest",):
                act = actuals[s].get("counts", {}).get(key)
                if act is None and key == "deterministic_disclosure_obligation_types_required":
                    act = actuals[s].get("deterministic_disclosure_obligation_types_present", 0)
                if act is None:
                    act = 0 if stage == "M3" else None
                delta = (act - req) if isinstance(act, (int, float)) and isinstance(req, (int, float)) else None
                per_set[s] = {"required": req, "actual": act, "delta": delta}
            else:
                per_set[s] = {"required": req, "actual": None, "delta": None}
        entries.append({
            "requirement_key": key, "module": module, "m0_caliber": caliber,
            "cross_module_reuse_allowed": reuse, "statistic": stat,
            "production_stage": stage, "per_set": per_set,
        })
    result = {
        "schema_version": "p7-pre-m0-requirement-matrix-v1",
        "contract_id": "EAS-M0-QUALIFICATION-V2",
        "generated_from": ["measurement_qualification.v2.json/qualification_set_minimums",
                            "spine gold_field_names + m0 REQUIRED_MODULES/record-role minimums"],
        "required_content_families": list(FAMILIES),
        "qualification_sets": ["A", "B"],
        "note": "actual 为 pre-recovery 快照（旧 QUAL 公开聚合，7 模块=0）；R4 由保全工具以新数据重填",
        "entries": entries,
        "m3_enforced_count_keys": list(COUNT_KEYS),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_digest": "",
    }
    return receipts.close_record(result, "record_digest")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", action="store_true", help="生成 PRE_M0_DATA_REQUIREMENT_MATRIX")
    ap.add_argument("--baseline", action="store_true", help="对旧 QUAL 评就绪（应两套 FAIL）")
    ap.add_argument("--readiness", choices=["A", "B"], help="对指定套以 --counts 评就绪并落回执")
    ap.add_argument("--counts", help="公开聚合计数 JSON 文件（保全工具产出）")
    ap.add_argument("--out", help="输出路径")
    args = ap.parse_args()
    if args.matrix:
        m = build_requirement_matrix()
        out = Path(args.out) if args.out else QUAL_DIR / "PRE_M0_DATA_REQUIREMENT_MATRIX.v1.json"
        out.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
        print("MATRIX entries", len(m["entries"]), "| m3_count_keys", len(m["m3_enforced_count_keys"]),
              "| record_digest", m["record_digest"][:16])
        return 0
    if args.baseline:
        for s in ("A", "B"):
            r = evaluate_set_readiness(s, public_counts_from_old_qual(s))
            print(f"QUAL-{s} readiness verdict={r['verdict']} failing={len(r['failing_keys'])}")
        return 0
    if args.readiness:
        pc = json.loads(Path(args.counts).read_text(encoding="utf-8"))
        r = receipts.close_record(evaluate_set_readiness(args.readiness, pc), "record_digest")
        out = Path(args.out) if args.out else QUAL_DIR / f"QUAL_{args.readiness}_READINESS_RECEIPT.v1.json"
        out.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"QUAL-{args.readiness} readiness verdict={r['verdict']} | record_digest {r['record_digest'][:16]}")
        return 0 if r["verdict"] == "PASS" else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
