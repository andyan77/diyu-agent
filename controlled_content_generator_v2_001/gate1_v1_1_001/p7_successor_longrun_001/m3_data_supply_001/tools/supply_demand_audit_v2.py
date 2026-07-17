#!/usr/bin/env python3
"""M3 胶囊① 供需审计 v2（链锚口径修正 + 分阶段补给模型）。

v1→v2 修正依据（机器真源，非事后合理化）：
- eval_audit_spine_001/spine/calibration.py CHAIN_ROLES =
  (source_evidence, reference_assertion, claim_atom, risk_classification,
   entailment, final_action)——事实链用例的摘要闭包锚在【单条 claim_atom】，
  v1 将链锚保守记为整件（ITEM）系口径错误；600 链需求应对 claim 供给 1356 复核。
- spine/m0.py 逐模块 family_coverage 最小量（20/20/40/40/20/16 每族）为逐族硬门。
- data_isolation CHALLENGE 格的用途即「已知风险召回测量」——对既有 claim 做
  受控扰动构造的变体（矛盾注入/降类诱饵/省略注入）是合同内的 CHALLENGE 供给
  来源，属发起人已授权的『扩建题库』最廉价路径；变体归属其源组（组不可分）。

v2 结论结构：
- 双卷在【claim 锚 + 变体扩增】下条件可行；决定变量=自然标签分布（UNKNOWN_UNTIL_LABELED，
  由胶囊② 小试实测）与 F5 族薄供给；
- 补给分三级：Tier0 变体构造（无需新整件）→ Tier1 F5 定向补轮 → Tier2 全族新轮
  （按小试实测缺口触发，逐级审批已由发起人裁决覆盖）。
"""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
M3DS = HERE.parents[1]
P7 = HERE.parents[2]
SPINE = P7 / "eval_audit_spine_001"

FAMILY_MIN = {  # spine/calibration.py family_coverage 调用点逐模块最小量（每族）
    "reference_extraction": 20,
    "claim_atomization": 20,
    "risk_classification": 40,
    "entailment_or_chain": 40,
    "disclosure_and_omission": 20,
    "formulaic_construct": 16,
}


def main() -> int:
    v1 = json.loads((M3DS / "SUPPLY_DEMAND_TABLE.v1.json").read_text(encoding="utf-8"))
    inv = v1["supply_inventory"]
    mins = v1["demand_source"]["qualification_set_minimums_verbatim"]
    fam = inv["per_family"]

    # 机器证据引用（修正的锚）
    calib = (SPINE / "spine/calibration.py").read_text(encoding="utf-8")
    assert 'CHAIN_ROLES = ("source_evidence", "reference_assertion", "claim_atom"' in calib, \
        "CHAIN_ROLES 证据缺失——v2 修正失去机器依据"

    claims_total = inv["distinct_claims"]

    # ---- 每集 claim 锚需求（复用口径：链用例内生复用 risk+entailment 标签）----
    natural_demand = max(mins["natural_legal_supported_cases"],       # 300 supported
                         mins["risk_classification_legal_controls"],  # 300 legal
                         mins["fact_chain_natural_legal_cases"])      # 300 legal chain
    challenge_demand = (mins["high_risk_contradicted_cases"]          # 300
                        + mins["high_risk_unknown_cases"])            # 100
    challenge_demand = max(challenge_demand,
                           mins["risk_classification_high_risk_cases"],   # 300
                           mins["fact_chain_high_risk_unsafe_cases"],     # 300
                           mins["high_risk_contradicted_cases"]
                           + mins["high_risk_unknown_cases"])             # 400 决定
    per_set = {"natural_label_claim_demand_reuse": natural_demand,        # 300
               "challenge_variant_claim_demand_reuse": challenge_demand,  # 400
               "atomization_positive": mins["claim_atomization_positive_cases"]}

    # ---- 分区模型：120 组 → QUAL-A / QUAL-B / DEV(G1+G2) ----
    # 分层随机按族均衡分配；此处用族级 claims 按组数占比线性投影（初版投影口径）
    partition = {"QUAL_A_groups": 45, "QUAL_B_groups": 45, "DEV_groups": 30}
    total_groups = sum(partition.values())
    assert total_groups == inv["distinct_source_groups"] == 120
    share = {k: v / total_groups for k, v in partition.items()}

    per_family_rows = []
    binding_notes = []
    for fid, f in sorted(fam.items()):
        row = {"family_id": fid, "groups": f["groups"], "claims_total": f["claims"]}
        for setname in ("QUAL_A", "QUAL_B"):
            c = f["claims"] * share[f"{setname}_groups"]
            row[f"{setname}_claims_projected"] = round(c, 1)
            # 逐族硬门：risk/entailment-or-chain 每族 ≥40（自然+变体可混），
            # 变体扩增系数 k=2（每基础 claim 两类受控扰动）下的族容量：
            row[f"{setname}_capacity_with_k2_variants"] = round(c * 3, 1)  # 原生 + 2 变体
        per_family_rows.append(row)
        worst = min(row["QUAL_A_claims_projected"], row["QUAL_B_claims_projected"])
        if worst * 3 < FAMILY_MIN["risk_classification"] * 2:  # 自然+挑战两侧各要门
            binding_notes.append(f"{fid}: 族容量吃紧（{worst}×3 < 80）")

    # 集级可行性（k=2 变体）：
    feasibility = {}
    for setname in ("QUAL_A", "QUAL_B"):
        c = claims_total * share[f"{setname}_groups"]
        nat_ok_requires = ("自然标签分布中 supported/legal 占比 ≥ "
                           f"{round(natural_demand / c, 2)}（{natural_demand}/{round(c)}）"
                           "——UNKNOWN_UNTIL_LABELED，胶囊② 小试实测")
        chal_ok = c * 2 >= challenge_demand
        feasibility[setname] = {
            "claims_projected": round(c, 1),
            "natural_demand_reuse": natural_demand,
            "natural_condition": nat_ok_requires,
            "challenge_capacity_k2": round(c * 2, 1),
            "challenge_demand_reuse": challenge_demand,
            "challenge_ok_count_wise": chal_ok,
        }

    # ---- 分阶段补给模型（发起人『扩建题库』裁决的落地分级）----
    tiers = [
        {"tier": "TIER0_CHALLENGE_VARIANTS",
         "what": "对既入格 claim 做受控扰动变体（矛盾注入/降类诱饵/省略注入/合并拆分负对照），变体随源组入格",
         "adds": "CHALLENGE 格用例容量 ×k（k=每 claim 扰动类数，预设 2）与全部负对照类需求",
         "new_whole_items": 0,
         "trigger": "默认执行（②协议冻结后、⑤题面冻结前，由建标流程按协议构造）"},
        {"tier": "TIER1_F5_TARGETED_TOPUP",
         "what": "F5（企业长期信任族，12 组/129 claims）定向新增场景组+整件",
         "adds": "F5 族级余量（当前逐族门最紧）",
         "new_whole_items": "~48（12 新组 × 4 件）",
         "trigger": "小试实测 F5 自然标签分布不足以同时喂饱双卷逐族门（≥40/族/卷）时"},
        {"tier": "TIER2_FULL_NEW_ROUNDS",
         "what": "全族新增生成轮（新场景组，走 pkg1 轮次机制）",
         "adds": "全局 claim 供给",
         "new_whole_items": "120/轮",
         "trigger": "小试实测自然 supported/legal 占比 < 需求占比（任一卷 natural_condition 失败）时，按缺口轮数触发"},
    ]

    v2 = {
        "schema_version": "p7-m3-supply-demand-table-v2",
        "supersedes": {"path": "SUPPLY_DEMAND_TABLE.v1.json",
                       "reason": "v1 将 fact_chain 锚记为整件（ITEM）；机器真源 spine/calibration.py CHAIN_ROLES 证明链锚为单条 claim_atom 的六角色摘要闭包。v1 的『双卷/单卷整件锚硬缺口』判定随之作废；v1 其余供给计数（480/1356/5546/1200 对）与抽样框不变，仍为真源。",
                       "v1_supply_counts_carried": True},
        "milestone_id": "M3",
        "capsule": "M3_C1B_FOUNDER_SUPPLY_EXPANSION_RULING",
        "chain_anchor_evidence": {
            "path": "eval_audit_spine_001/spine/calibration.py",
            "symbol": "CHAIN_ROLES",
            "value": ["source_evidence", "reference_assertion", "claim_atom",
                      "risk_classification", "entailment", "final_action"],
        },
        "family_coverage_minimums_per_module": FAMILY_MIN,
        "per_set_claim_anchor_demand_reuse": per_set,
        "partition_projection": partition,
        "per_family_projection": per_family_rows,
        "family_binding_notes": binding_notes or ["无族级即时红线；F5 为最紧族，Tier1 预案覆盖"],
        "set_feasibility": feasibility,
        "verdict": {
            "dual_sets_count_wise": "CONDITIONALLY_FEASIBLE（claim 锚 + k=2 变体扩增下计数可行）",
            "unknowns": ["自然标签分布（supported/legal/contradicted 占比）——胶囊② 小试实测",
                          "F5 族薄供给的逐族门余量"],
            "expansion_tiers": tiers,
            "honest_note": "v1 的硬缺口结论在整件锚口径下为真；口径修正后计数缺口消失，但可行性仍悬于标签分布——在小试实测前不得宣布任何『供给已足』结论（E1 纪律）。",
        },
    }
    out = M3DS / "SUPPLY_DEMAND_TABLE.v2.json"
    out.write_text(json.dumps(v2, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(out.name),
                      "dual_sets": v2["verdict"]["dual_sets_count_wise"],
                      "family_binding_notes": v2["family_binding_notes"],
                      "QUAL_A": feasibility["QUAL_A"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
