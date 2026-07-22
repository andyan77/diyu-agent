#!/usr/bin/env python3
"""§四.6（发起人裁决）机械功效检查 + cluster-aware 单侧 95% CI 方法冻结。

发起人裁决（CAPACITY_DECISION.v1.json）：300/100 下限按 **raw case N**（不同挑战机制变体计入覆盖）；
统计独立由 **distinct source-group cluster N** + **冻结的 cluster-aware 单侧 95% 置信下界** 保障；
**先机械功效检查**——某统计门即便零错误、以每类可用 cluster N 也达不到单侧 95% 下界阈 → 该缺口
家族定向 Tier2；否则可行，继续（不 HONEST_STOP、不笼统扩源）。

方法（看资格结果前冻结，预注册防事后选法）：
  - cluster = source_group_id；一个 cluster 在某类记为一次有效独立试验（保守：cluster 内相关性
    最大化，effective N = cluster 数，不用 record 数充数）。
  - 单侧 95% 置信**下界**用精确 Clopper-Pearson；零错误(x=n)时下界 = 0.05**(1/n)。
  - 达阈最小 cluster 数（零错误）: n_min(θ) = ceil( ln(0.05) / ln(θ) )。

本工具零明文：只读合同阈值 + 结构化 cluster 供给（capacity 枚举），不碰密封 gold。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
M3DS = HERE.parents[1]
P7 = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import qual_capacity_precheck as CAP  # noqa: E402

CONTRACT = P7 / "eval_audit_spine_001/contract/measurement_qualification.v2.json"
QUAL_DIR = M3DS / "gold/qual"
CI_ALPHA = 0.05  # 单侧 95%
FAMILIES = CAP.FAMILIES


def n_min_zero_error(theta: float) -> int:
    """零错误下单侧 95% Clopper-Pearson 下界 ≥ theta 所需最小 cluster 数。"""
    if theta >= 1.0:
        return math.inf  # 恒无法用有限样本证明 =1.0（属确定性门，不走统计 CI）
    return math.ceil(math.log(CI_ALPHA) / math.log(theta))


# 需功效检查的**统计率门**（recall/precision/accuracy/agreement 阈值）。
# 确定性 1.0 门（disclosure 四类 recall、review 硬门一致=1.0）不入统计功效（属机械必过）。
def _statistical_rate_gates(mg: dict) -> list[dict]:
    g = []

    def add(module, name, theta, denom_class):
        g.append({"module": module, "gate": name, "threshold": theta,
                  "denominator_class": denom_class})
    r = mg["reference_assertion_extraction"]
    add("reference_extraction", "critical_assertion_recall", r["critical_assertion_recall_minimum"],
        "reference_extraction_positive_cases")
    add("reference_extraction", "critical_assertion_precision", r["critical_assertion_precision_minimum"],
        "reference_extraction_positive_cases")
    add("reference_extraction", "attribute_accuracy",
        r["polarity_modality_time_and_precondition_accuracy_minimum"], "reference_extraction_positive_cases")
    a = mg["claim_atomization"]
    add("claim_atomization", "critical_claim_recall", a["critical_claim_recall_minimum"],
        "claim_atomization_positive_cases")
    add("claim_atomization", "critical_claim_precision", a["critical_claim_precision_minimum"],
        "claim_atomization_positive_cases")
    add("risk_classification", "overall_accuracy", mg["risk_classification"]["overall_accuracy_minimum"],
        "risk_classification_high_risk_cases")
    e = mg["entailment"]
    add("entailment", "contradicted_recall", e["contradicted_recall_minimum"], "high_risk_contradicted_cases")
    add("entailment", "contradicted_precision", e["contradicted_precision_minimum"], "high_risk_contradicted_cases")
    add("entailment", "supported_recall", e["supported_recall_minimum"], "natural_legal_supported_cases")
    add("entailment", "supported_precision", e["supported_precision_minimum"], "natural_legal_supported_cases")
    add("entailment", "unknown_recall", e["unknown_recall_minimum"], "high_risk_unknown_cases")
    add("entailment", "unknown_precision", e["unknown_precision_minimum"], "high_risk_unknown_cases")
    d = mg["disclosure_and_omission"]
    add("omission", "omission_misleading_recall", d["omission_misleading_recall_minimum"],
        "omission_misleading_high_risk_cases")
    add("omission", "omission_misleading_precision", d["omission_misleading_precision_minimum"],
        "omission_misleading_high_risk_cases")
    f = mg["formulaic_construct"]
    add("formulaic", "raw_agreement", f["raw_agreement_minimum"], "formulaic_double_reviewed_pairs_total")
    add("formulaic", "positive_agreement", f["positive_agreement_minimum"], "formulaic_positive_pairs_minimum")
    add("formulaic", "negative_agreement", f["negative_agreement_minimum"], "formulaic_negative_pairs_minimum")
    add("formulaic", "cohen_kappa_binary", f["cohen_kappa_binary_minimum_when_interpretable"],
        "formulaic_double_reviewed_pairs_total")
    add("review_calibration", "approval_decision_agreement",
        mg["review_calibration"]["approval_decision_agreement_minimum"], "review_double_reviewed_items")
    # 发起人裁决：**补齐真实 calibration 错误率上界门**（`_upper_95_maximum` / `_maximum`）。
    # 错误率上界 e 的功效等价「正确率下界门 θ=1-e」：n_min=ceil(ln0.05/ln(1-e))。
    # <1%(e=.01)→299、≤3%(e=.03)→99、≤5%(e=.05)→59（旧 power check 漏 0.01/299 门 → 误判 161 可行）。
    def add_errmax(module, name, e, denom_class):
        g.append({"module": module, "gate": name, "threshold": round(1.0 - e, 6),
                  "error_rate_upper_bound": e, "denominator_class": denom_class})
    rc = mg["risk_classification"]
    add_errmax("risk_classification", "high_or_critical_downclassification_upper_95",
               rc["high_or_critical_downclassification_upper_95_maximum"],   # 0.01 → n_min 299（最严门）
               "risk_classification_high_risk_cases")
    add_errmax("risk_classification", "legal_false_high_upper_95",
               rc["legal_false_high_upper_95_maximum"],                       # 0.05 → n_min 59
               "risk_classification_legal_controls")
    add_errmax("claim_atomization", "incorrect_merge_rate",
               mg["claim_atomization"]["incorrect_merge_rate_maximum"],       # 0.05 → n_min 59
               "claim_atomization_positive_cases")
    return g


def freeze_ci_method() -> dict:
    decision = json.loads((P7 / "delivery_control_001/milestones/M3/recovery/"
                           "CAPACITY_DECISION.v1.json").read_text(encoding="utf-8"))
    method = {
        "schema_version": "p7-cluster-aware-ci-method-freeze-v1",
        "frozen_before_qualification_results": True,
        "cluster_unit": "source_group_id",
        "cluster_unit_definition": "source_group_id = evidence_anchor_digest(scenario_id + source/fact/"
        "authorization ids)（发起人证据身份裁决）——非 (scenario,claim)/round；raw 覆盖走机制/题面维度。",
        "confidence_level": 0.95,
        "sidedness": "ONE_SIDED_LOWER_BOUND",
        "effective_n_rule": "每类 effective 独立试验数 = 该类 distinct evidence anchor（source_group_id）"
        "cluster 数（保守：cluster 内相关性最大化，不以 record/变体/题面 充 N）",
        "cluster_aggregation": "资格计算（M0 calibration）须先把记录按 source_group_id 聚为 cluster："
        "一个 cluster 在某类记 1 次试验；cluster 成功 iff 该 cluster 在该类全部记录判对（对 recall 保守）。"
        "即 CI 分母 = cluster N（非 record N）——cluster-aware 结果真接入资格计算，非仅 readiness 数量。",
        "lower_bound_method": "EXACT_CLOPPER_PEARSON_ONE_SIDED",
        "zero_error_lower_bound_formula": "0.05 ** (1/n)  （x=n 成功、0 失败）",
        "min_clusters_zero_error_formula": "ceil( ln(0.05) / ln(theta) )",
        "dual_disclosure_required": ["raw_case_N", "distinct_source_group_cluster_N"],
        "founder_ruling_ref": "CAPACITY_DECISION.v1.json",
        "founder_ruling_verbatim": decision["founder_ruling_verbatim"],
        "method_digest": "",
    }
    from spine.canonical import digest_json  # noqa: E402
    sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
    method["method_digest"] = digest_json({k: v for k, v in method.items() if k != "method_digest"})
    return method


def power_check() -> dict:
    mg = json.loads(CONTRACT.read_text(encoding="utf-8"))["module_gates"]
    gates = _statistical_rate_gates(mg)
    sup = CAP.compute_evidence_supply()
    per_set_cluster = {s: sup["per_set"][s]["distinct_evidence_units"] for s in ("A", "B")}
    per_set_family = {s: sup["per_set"][s]["per_family"] for s in ("A", "B")}
    # 每类可用 cluster 上界：类分母 clusters ≤ 每套 distinct source_group（变体构造可把类铺到全体 sg）。
    # 保守以每套 cluster N 作各类上界（pre-data，真类分布 R3-run custody 复算）。
    rows = []
    overall_feasible = True
    for g in gates:
        nmin = n_min_zero_error(g["threshold"])
        for s in ("A", "B"):
            avail = per_set_cluster[s]
            ok = avail >= nmin
            overall_feasible &= ok
            rows.append({"set": s, **g, "n_min_zero_error": nmin,
                         "available_cluster_ceiling": avail, "overall_power_feasible": ok})
    # 每族功效（uncertainty_reporting 要 per-family 披露；F5 最薄）——诊断非硬门（合同率门为整体）。
    # per-family bar 用 recall/precision 率门（排除 class 级错误率上界门如 downclass 0.99→299——那是
    # 整类门非 per-family），取其最严 θ（0.95→59）。
    family_gates = [g for g in gates if "error_rate_upper_bound" not in g]
    max_theta = max(g["threshold"] for g in family_gates)
    nmin_strict = n_min_zero_error(max_theta)
    family_power = []
    for s in ("A", "B"):
        for fam in FAMILIES:
            av = per_set_family[s].get(fam, 0)
            family_power.append({"set": s, "family": fam, "cluster_supply": av,
                                 "n_min_for_max_threshold": nmin_strict,
                                 "per_family_ci_reaches_max_threshold_at_zero_error": av >= nmin_strict})
    gap_families = sorted({r["family"] for r in family_power
                           if not r["per_family_ci_reaches_max_threshold_at_zero_error"]})
    return {
        "schema_version": "p7-qual-power-check-v1",
        "contract_id": "EAS-M0-QUALIFICATION-V2",
        "ci_method": freeze_ci_method(),
        "per_set_cluster_supply": per_set_cluster,
        "n_min_zero_error_by_threshold": {str(t): n_min_zero_error(t)
                                          for t in sorted({g["threshold"] for g in gates})},
        "gate_power_rows": rows,
        "overall_statistical_gates_power_feasible": overall_feasible,
        "family_power_diagnostic": family_power,
        "per_family_ci_gap_families": gap_families,
        "gates_are_overall_not_per_family": True,
        "gates_are_overall_basis": "measurement_qualification.v2 module_gates 率门为整体阈；per-family 仅"
        "uncertainty_reporting 披露（非 per-family 硬 PASS 门）→ 整体功效可行即不触发 Tier2",
        "tier2_required_now": (not overall_feasible),
        "tier2_target_families": gap_families if not overall_feasible else [],
        "verdict": ("POWER_FEASIBLE_PROCEED" if overall_feasible
                    else "TIER2_TARGETED_TOPUP_REQUIRED"),
        "note": ("整体统计率门在每套 %d/%d cluster 下、零错误时单侧 95%% 下界均达阈（各门 n_min ≤ %d）；"
                 "F5 per-family CI 较宽（cluster %d/套 < %d）属披露级限制、非硬门失败 → 不触发 Tier2。"
                 "按发起人裁决继续，不 HONEST_STOP、不笼统扩源。"
                 % (per_set_cluster["A"], per_set_cluster["B"], nmin_strict,
                    per_set_family["A"].get("F5_ENTERPRISE_LONG_TERM_TRUST", 0), nmin_strict)),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="功效检查回执输出路径")
    ap.add_argument("--freeze-ci-out", help="CI 方法冻结输出路径")
    args = ap.parse_args()
    result = power_check()
    if args.freeze_ci_out:
        Path(args.freeze_ci_out).write_text(
            json.dumps(result["ci_method"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    out = Path(args.out) if args.out else QUAL_DIR / "POWER_CHECK.v1.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": result["verdict"],
        "per_set_cluster_supply": result["per_set_cluster_supply"],
        "n_min_zero_error_by_threshold": result["n_min_zero_error_by_threshold"],
        "overall_statistical_gates_power_feasible": result["overall_statistical_gates_power_feasible"],
        "per_family_ci_gap_families": result["per_family_ci_gap_families"],
        "tier2_required_now": result["tier2_required_now"],
    }, ensure_ascii=False, indent=1))
    return 0 if not result["tier2_required_now"] else 2


if __name__ == "__main__":
    sys.exit(main())
