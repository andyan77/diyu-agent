#!/usr/bin/env python3
"""§五 有效容量预检：从**真实**抽样框 + DEV 分区机械计算每套 QUAL-A/B 的可用独立单位供给，
逐类别与 measurement_qualification.v2 下限比较；不足则标记（触发 Tier1 定向补量），穷尽真源仍
不足才 HONEST_STOP。

关键统计纪律（§六B / capacity plan）：
  - 默认独立单位 = source_group（claim 级）。同源 challenge 变体继承 base 的 source_group，
    不增加有效 N（variants_add_effective_N=false）——故供给 = distinct 自然 claim source_group，
    不把「原生+k 变体」当独立样本。
  - cross-module reuse：一个 claim source_group 经不同构造（自然/挑战）可分别为多个类别各计 1 个
    独立单位（不同类别分母各自 distinct），故绑定约束是「每套供给 ≥ 每类下限」（逐类），而非
    「所有类下限之和」。高危类（CHALLENGE）与合法类（NATURAL）可共享同一 source_group。
  - 这是**必要条件**门：供给 ≥ 每类下限 + 每族下限。逐类实际可达在 R3-run 由 custody 周期复算确认。

主编排会话零明文：本工具只读公开抽样框结构（scenario/claim 计数，无题面），不碰密封 gold。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
M3DS = HERE.parents[1]
P7 = HERE.parents[2]
CONTRACT = P7 / "eval_audit_spine_001/contract/measurement_qualification.v2.json"

FAMILIES = ("F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
            "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
            "F5_ENTERPRISE_LONG_TERM_TRUST")

# 每套逐类「distinct 独立单位（claim source_group）」下限（消费 claim 供给的类）。
# 真源 = measurement_qualification.v2.qualification_set_minimums 的对应键。
CLAIM_CLASS_MIN_KEYS = (
    "reference_extraction_positive_cases", "reference_extraction_negative_controls",
    "claim_atomization_positive_cases", "claim_atomization_negative_controls",
    "risk_classification_high_risk_cases", "risk_classification_legal_controls",
    "high_risk_contradicted_cases", "high_risk_unknown_cases",
    "natural_legal_supported_cases", "fact_chain_high_risk_unsafe_cases",
    "fact_chain_natural_legal_cases", "deterministic_disclosure_cases_total",
    "omission_misleading_high_risk_cases", "omission_nonmisleading_controls",
)
# formulaic 用 pair 供给（profile 内成对），非 claim source_group。
PAIR_CLASS_MIN_KEYS = ("formulaic_double_reviewed_pairs_total",
                       "formulaic_positive_pairs_minimum",
                       "formulaic_negative_pairs_minimum",
                       "formulaic_necessary_grammar_pairs_minimum")
# 每族下限（family_coverage minimum_per_family）：各模块 core 用值不同，取最严 40（risk/fact_chain）。
PER_FAMILY_FLOOR = 40


def load_qual_pool() -> dict:
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    part = json.loads((M3DS / "gold/DEV_PARTITION.v1.json").read_text(encoding="utf-8"))
    chosen = set(part["qual_pool_groups"])
    by_id = {g["scenario_id"]: g for g in frame["groups"]}
    pool = [by_id[s] for s in chosen if s in by_id]
    return {"frame_digest": frame["frame_digest"],
            "partition_digest": part.get("partition_digest"),
            "groups": pool}


def _group_claims(g: dict) -> int:
    return sum(i["claims_n"] for i in g["items"])


def compute_supply() -> dict:
    """从真实抽样框机械算每套 distinct claim source_group 供给（含 pair 供给上界）。

    每套供给 = qual pool claims 的均衡两分（保守取 floor(total/2)）；per-family 同理。
    pair 供给 = C(per_set_claims within profile)，用 pair_capacity_within_profile 上界近似。
    """
    pool = load_qual_pool()
    groups = pool["groups"]
    total_claims = sum(_group_claims(g) for g in groups)
    fam_claims: Counter = Counter()
    for g in groups:
        fam_claims[g["family_id"]] += _group_claims(g)
    # 均衡两分（split 按 claims 平衡贪心，delta 小）；保守以 floor(total/2) 作每套供给下界。
    per_set_supply = total_claims // 2
    per_set_family = {f: fam_claims.get(f, 0) // 2 for f in FAMILIES}
    # pair 供给：每套自然 claim 两两成对，profile 内约束下远超类下限；保守取 per_set_supply
    # （每套 claim 数即可成对，pair 数 >> per_set_supply）。
    per_set_pair_supply = per_set_supply
    return {
        "frame_digest": pool["frame_digest"],
        "partition_digest": pool["partition_digest"],
        "qual_pool_groups": len(groups),
        "qual_pool_claims": total_claims,
        "per_set_claim_source_group_supply": per_set_supply,
        "per_set_family_supply": per_set_family,
        "per_set_pair_supply": per_set_pair_supply,
        "family_claim_totals": {f: fam_claims.get(f, 0) for f in FAMILIES},
        "binding_family": min(FAMILIES, key=lambda f: fam_claims.get(f, 0)),
    }


def precheck() -> dict:
    mins = json.loads(CONTRACT.read_text(encoding="utf-8"))["qualification_set_minimums"]
    supply = compute_supply()
    per_set = supply["per_set_claim_source_group_supply"]
    per_set_pair = supply["per_set_pair_supply"]
    rows = []
    feasible = True
    for key in CLAIM_CLASS_MIN_KEYS:
        req = mins[key]
        ok = per_set >= req
        feasible &= ok
        rows.append({"class": key, "unit": "claim_source_group", "required": req,
                     "per_set_supply": per_set, "surplus": per_set - req, "ok": ok})
    for key in PAIR_CLASS_MIN_KEYS:
        req = mins[key]
        ok = per_set_pair >= req
        feasible &= ok
        rows.append({"class": key, "unit": "pair", "required": req,
                     "per_set_supply": per_set_pair, "surplus": per_set_pair - req,
                     "ok": ok})
    # 每族下限（每套每族供给 ≥ PER_FAMILY_FLOOR）
    family_rows = []
    for fam in FAMILIES:
        sup = supply["per_set_family_supply"][fam]
        ok = sup >= PER_FAMILY_FLOOR
        feasible &= ok
        family_rows.append({"family": fam, "required_per_family": PER_FAMILY_FLOOR,
                            "per_set_supply": sup, "surplus": sup - PER_FAMILY_FLOOR,
                            "ok": ok})
    # known_r5 回归：固定 5 行，非 claim 供给（外部注册）——记录不阻断（R3-run 绑定）。
    insufficient = [r["class"] for r in rows if not r["ok"]]
    insufficient += [f"family:{r['family']}" for r in family_rows if not r["ok"]]
    return {
        "schema_version": "p7-qual-capacity-precheck-v1",
        "contract_id": "EAS-M0-QUALIFICATION-V2",
        "independent_unit_rule": "default=source_group(claim级); 同源变体不增有效N; "
        "cross-module reuse 使一 source_group 可为多类各计1(逐类distinct)",
        "supply": supply,
        "class_rows": rows,
        "family_rows": family_rows,
        "insufficient_classes": insufficient,
        "verdict": "FEASIBLE" if feasible else "INSUFFICIENT_NEEDS_TOPUP",
        "topup_policy": "不足→自动 Tier1 定向补量（既有真源，预授权，非发起人门）；"
        "穷尽既有真源合法统计独立补量仍不足→HONEST_STOP(容量不足)；绝不同源变体凑数",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================ §四.6 证据独立枚举（真实 split）
# 收敛 Prompt §四.6：从**实际** QUAL-A/B split 直接枚举 distinct evidence unit，按真实证据聚类
# 去重（同一 (scenario, claim) 的多轮表达/不同措辞属同一 cluster，不增有效 N）。取代上文
# compute_supply 的 `claims//2` 粗估（那是把 4 轮再生实例当独立 → 伪独立虚数，同 plan 旧 510/1356）。

def _round_files():
    sys.path.insert(0, str(M3DS / "gold/tools"))
    import qual_runner as QR  # noqa: E402 延迟导入避免循环
    return QR.ROUND_FILES, QR.PK, QR.SEAL


def all_evidence_units() -> dict:
    """跨 4 轮枚举 distinct evidence anchor（发起人证据身份裁决）→ {anchor: {family, scenario}}。

    anchor = digest(scenario_id + 排序 source/fact/authorization ids)。取代旧 (scenario_id, claim_id)
    口径（把同 scenario 内不同证据的 claim 折叠成 161/152 伪独立虚数）。同 (scenario,claim) 跨轮再生
    = 同锚（不增 N）；同 scenario 内引不同 source/fact/auth 的不同 claim = 真不同证据（各成独立锚）。
    结构化只读（scenario/family/anchor 摘要，无题面）→ 编排会话零明文。
    """
    ROUND_FILES, PK, _ = _round_files()
    sys.path.insert(0, str(M3DS / "tools"))
    import qual_gold_derivation as GD  # noqa: E402 延迟导入避免循环
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    fam = {g["scenario_id"]: g["family_id"] for g in frame["groups"]}

    def jl(p):
        return [json.loads(line) for line in open(p, encoding="utf-8")]
    units: dict = {}
    round_instances = 0
    for _rname, (req_rel, out_rel) in ROUND_FILES.items():
        reqs = {r["request_id"]: r for r in jl(PK / req_rel)}
        for o in jl(PK / out_rel):
            sid = reqs[o["request_id"]]["scenario_id"]
            for c in o.get("claims", []):
                round_instances += 1
                a = GD.evidence_anchor_digest(
                    sid, c.get("source_ids"), c.get("fact_ids"), c.get("authorization_ids"))
                units[a] = {"family": fam.get(sid, "?"), "scenario": sid}
    return {"units": units, "round_instances": round_instances,
            "distinct_evidence_units": len(units)}


def compute_evidence_supply() -> dict:
    """按真实 A/B split（优先 membership_v2 证据锚均衡切分）枚举每套 distinct 证据锚供给（+ 每族）。

    membership 缺失则以 90 组池均衡估算上界。供给 = distinct evidence anchor（cluster 独立单位），
    驱动 cluster-aware CI / 功效（power）。raw 覆盖供给另由 precheck() 的 claim 实例口径给出（双计数）。
    """
    ev = all_evidence_units()
    units = ev["units"]
    ROUND_FILES, PK, SEAL = _round_files()
    mem_path = SEAL / "membership_v2.json"
    if not mem_path.is_file():
        mem_path = SEAL / "membership.json"
    per_set: dict = {}
    if mem_path.is_file():
        mem = json.loads(mem_path.read_text(encoding="utf-8"))
        for s in ("A", "B"):
            chosen = set(mem[f"QUAL_{s}"])
            du = [u["family"] for u in units.values() if u["scenario"] in chosen]
            per_set[s] = {"distinct_evidence_units": len(du),
                          "per_family": dict(sorted(Counter(du).items())),
                          "chosen_scenarios": len(chosen)}
        split_source = f"sealed_custody_001/{mem_path.name}（真实 split，证据锚口径）"
    else:
        half = ev["distinct_evidence_units"] // 2
        fc = {f: c // 2 for f, c in Counter(u["family"] for u in units.values()).items()}
        per_set = {s: {"distinct_evidence_units": half, "per_family": dict(sorted(fc.items())),
                       "chosen_scenarios": 45} for s in ("A", "B")}
        split_source = "membership 缺失 → 90 组池均衡上界估算"
    return {"round_instances_inflated": ev["round_instances"],
            "distinct_evidence_units_total": ev["distinct_evidence_units"],
            "per_family_total": dict(sorted(Counter(u["family"] for u in units.values()).items())),
            "per_set": per_set, "split_source": split_source}


def precheck_evidence() -> dict:
    """§四.6 真实证据独立容量门：每套 distinct 证据单位（任一类分母上确界）vs 各类下限。

    某类下限 > 每套 distinct 证据单位供给 → 该类**机械不可达**（一类是全体单位子集，且变体不增 N、
    同源多轮不增 N）。穷尽既有真源（全 120 scenario 均已入池）+ 无 Tier1 新源 → 机械不足。
    """
    mins = json.loads(CONTRACT.read_text(encoding="utf-8"))["qualification_set_minimums"]
    sup = compute_evidence_supply()
    max_class_min = max(mins[k] for k in CLAIM_CLASS_MIN_KEYS)
    rows = []
    feasible = True
    for s in ("A", "B"):
        du = sup["per_set"][s]["distinct_evidence_units"]
        for key in CLAIM_CLASS_MIN_KEYS:
            req = mins[key]
            ok = du >= req  # 上确界：即便全体单位都属该类也需 >= 下限
            feasible &= ok
            if not ok:
                rows.append({"set": s, "class": key, "required": req,
                             "per_set_distinct_unit_ceiling": du, "shortfall": req - du,
                             "mechanically_reachable": False})
    # 每族下限
    fam_rows = []
    for s in ("A", "B"):
        for fam in FAMILIES:
            sup_f = sup["per_set"][s]["per_family"].get(fam, 0)
            ok = sup_f >= PER_FAMILY_FLOOR
            fam_rows.append({"set": s, "family": fam, "required_per_family": PER_FAMILY_FLOOR,
                             "supply": sup_f, "ok": ok})
    return {
        "schema_version": "p7-qual-capacity-evidence-truth-v1",
        "contract_id": "EAS-M0-QUALIFICATION-V2",
        "method": "§四.6 真实 A/B split 直接枚举 distinct (scenario,claim) 证据单位；跨轮/措辞去重；"
        "变体继承 base 不增 N。取代 plan 的 510/1356 伪独立虚数（=4 轮再生实例，同源多计）。",
        "supply": sup,
        "max_claim_class_minimum": max_class_min,
        "infeasible_class_rows": rows,
        "family_rows": fam_rows,
        "source_universe": {
            "distinct_scenarios_in_entire_repo": 120,
            "content_profiles": 20,
            "rounds_are_regenerations_not_new_evidence": True,
            "tier1_new_source_material_available": False,
            "note": "全 120 scenario 均已入抽样框；4 轮为同 120 scenario 再生（非新证据）；"
                    "repo 内无更大 scenario 源池/产品事实 KB 可供 Tier1 合法扩容",
        },
        "verdict": "FEASIBLE" if feasible else "MECHANICALLY_INSUFFICIENT",
        "honest_stop_candidate": (not feasible),
        "honest_stop_basis": ("§九 HONEST_STOP #1（穷尽现有真源+Tier1 后 A/B 独立容量机械不足）"
                              "叠加 #3（唯一出路=扩源/Tier2 需发起人授权与新素材）" if not feasible
                              else "n/a"),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="预检回执输出路径")
    ap.add_argument("--evidence", action="store_true",
                    help="§四.6 真实证据独立枚举（取代 claims//2 粗估）")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if args.evidence:
        result = precheck_evidence()
        if args.out:
            Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                                      encoding="utf-8")
        if not args.quiet:
            print(json.dumps({
                "verdict": result["verdict"],
                "distinct_evidence_units_total": result["supply"]["distinct_evidence_units_total"],
                "per_set_distinct_units": {s: result["supply"]["per_set"][s]["distinct_evidence_units"]
                                          for s in ("A", "B")},
                "max_claim_class_minimum": result["max_claim_class_minimum"],
                "infeasible_class_count": len(result["infeasible_class_rows"]),
                "honest_stop_candidate": result["honest_stop_candidate"],
            }, ensure_ascii=False, indent=1))
        return 0 if result["verdict"] == "FEASIBLE" else 2
    result = precheck()
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    if not args.quiet:
        s = result["supply"]
        print(json.dumps({
            "verdict": result["verdict"],
            "per_set_claim_source_group_supply": s["per_set_claim_source_group_supply"],
            "max_claim_class_min": max(
                r["required"] for r in result["class_rows"]
                if r["unit"] == "claim_source_group"),
            "binding_family": s["binding_family"],
            "per_set_family_supply": s["per_set_family_supply"],
            "insufficient": result["insufficient_classes"],
        }, ensure_ascii=False, indent=1))
    return 0 if result["verdict"] == "FEASIBLE" else 2


if __name__ == "__main__":
    sys.exit(main())
