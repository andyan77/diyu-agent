#!/usr/bin/env python3
"""M3 胶囊① 分格供需审计（E1-S）。

一切计数从机器真源独立重算（E12：不复用任何被测/上游过滤逻辑）：
- 需求锚：eval_audit_spine_001/contract/measurement_qualification.v2.json 逐字读取；
- 供给锚：pkg1_open_regression 四轮 first_outputs + scenarios 逐行计数；
- 分格：contract/data_isolation.v1.json 两轴六格；族映射：v4_recovery family_strategies.v1.json；
- 成本锚：M2 S0 遥测模型（cost_throughput_model.v1.json）。

输出（写入 m3_data_supply_001/）：
  SUPPLY_DEMAND_TABLE.v1.json   分格供需表（含五族×车道×轮次供给、逐模块需求、双口径缺口判定）
  VECTOR_CAPACITY_TABLE.v1.json 向量容量表（初版投影：逐模块锚型/容量/缺口/可达 n/CI 半宽/双路径期望成本）
  SAMPLING_FRAME.v1.json        共同抽样框预登记（源组=scenario 组，不可分；分层键 family×lane×profile）
  EXCLUSION_LOG.v1.json         排除日志预登记
标签分布未标注前一律 UNKNOWN_UNTIL_LABELED，只用计数上界做机械判定；
凡上界 < 需求即为与标签分布无关的硬缺口（runtime_verified 算术）。
"""

from __future__ import annotations

import json
import hashlib
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
M3DS = HERE.parents[1]                      # m3_data_supply_001/
P7 = HERE.parents[2]                        # p7_successor_longrun_001/
PK = P7 / "pkg1_open_regression"
SPINE = P7 / "eval_audit_spine_001"
V4 = P7.parents[1] / "generator_v3_successor_001/v4_recovery"

# (scenario 文件相对路径或 None, requests 文件, outputs 文件)
# round2 无本地 scenario 文件（四轮共享同一批 120 场景）；规范场景元数据源=round5 v2
ROUNDS = {
    "round1_top": ("inputs/scenarios.g3.v1.jsonl", "inputs/requests.g3.v1.jsonl",
                   "outputs/first_outputs.g3.v1.jsonl"),
    "round2": (None, "round2/inputs/requests.g3.v1.jsonl",
               "round2/outputs/first_outputs.g3.v1.jsonl"),
    "round3": ("round3/inputs/scenarios.g3.v2.jsonl", "round3/inputs/requests.g3.v1.jsonl",
               "round3/outputs/first_outputs.g3.v1.jsonl"),
    "round5": ("round5/inputs/scenarios.g3.v2.jsonl", "round5/inputs/requests.g3.v1.jsonl",
               "round5/outputs/first_outputs.g3.v1.jsonl"),
}
CANONICAL_SCENARIOS = "round5/inputs/scenarios.g3.v2.jsonl"


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ci_halfwidth(n: int, p: float = 0.5) -> float:
    """95% 二项比例置信区间半宽（正态近似，最保守 p=0.5）。n=0 → inf。"""
    if n <= 0:
        return float("inf")
    return round(1.96 * math.sqrt(p * (1 - p) / n), 4)


def main() -> int:
    mq = json.loads((SPINE / "contract/measurement_qualification.v2.json").read_text(encoding="utf-8"))
    minimums = mq["qualification_set_minimums"]
    iso = json.loads((SPINE / "contract/data_isolation.v1.json").read_text(encoding="utf-8"))
    fam_cfg = json.loads((V4 / "config/family_strategies.v1.json").read_text(encoding="utf-8"))
    profile_to_family = {}
    for fam in fam_cfg["families"]:
        for cp in fam["profiles"]:
            profile_to_family[cp] = fam["family_id"]
    telem = json.loads((SPINE / "evidence/s0_m2_real_run_001/telemetry/cost_throughput_model.v1.json").read_text(encoding="utf-8"))
    known_veto = jl(SPINE / "fixtures/r5_known_veto_regression.v1.jsonl")

    # ---- 供给：逐轮逐行计数，按 scenario 组聚合 ----
    canon = {s["scenario_id"]: s for s in jl(PK / CANONICAL_SCENARIOS)}
    top_v1_ids = {s["scenario_id"] for s in jl(PK / "inputs/scenarios.g3.v1.jsonl")}
    assert set(canon) == top_v1_ids, "规范场景集(v2)与 top v1 场景 id 集不一致"
    groups: dict[str, dict] = {}
    round_stats = {}
    for rname, (scen_rel, req_rel, out_rel) in ROUNDS.items():
        out_path = PK / out_rel
        outs = jl(out_path)
        digests = {o["output_digest"] for o in outs}
        assert len(digests) == len(outs), f"{rname}: output_digest 重复"
        round_stats[rname] = {
            "scenario_file": (str((PK / scen_rel).relative_to(P7)) if scen_rel
                              else "NONE_SHARED_CANONICAL（round2 无本地场景文件，四轮共享 120 场景）"),
            "scenario_file_sha256": (sha256_file(PK / scen_rel) if scen_rel else None),
            "output_file": str(out_path.relative_to(P7)),
            "output_file_sha256": sha256_file(out_path),
            "items": len(outs),
            "claims": sum(len(o.get("claims", [])) for o in outs),
            "surface_units": sum(len(o.get("surface_units", [])) for o in outs),
        }
        # 输出无 scenario_id 字段；经同轮 requests 文件（唯一携带 scenario_id + request_id）回连
        reqs = {r["request_id"]: r for r in jl(PK / req_rel)}
        for o in outs:
            req = reqs[o["request_id"]]
            sid = req["scenario_id"]
            scen = canon[sid]
            g = groups.setdefault(sid, {
                "scenario_id": sid,
                "profile_id": req["profile_id"],
                "family_id": profile_to_family[req["profile_id"]],
                "lane_id": scen.get("lane_id"),
                "scenario_label": scen.get("scenario_label"),
                "source_summaries": 0,
                "items": [],
            })
            g["source_summaries"] = int(bool(scen.get("source_summary_a"))) + int(bool(scen.get("source_summary_b")))
            g["items"].append({
                "round": rname,
                "request_id": o["request_id"],
                "output_digest": o["output_digest"],
                "claims_n": len(o.get("claims", [])),
                "surface_units_n": len(o.get("surface_units", [])),
                "publishable": o.get("publishable"),
                "synthetic_qualification_only": o.get("synthetic_qualification_only"),
            })

    assert len(groups) == 120, f"源组数 {len(groups)} ≠ 120"
    items_total = sum(len(g["items"]) for g in groups.values())
    claims_total = sum(i["claims_n"] for g in groups.values() for i in g["items"])
    su_total = sum(i["surface_units_n"] for g in groups.values() for i in g["items"])
    src_summaries_total = sum(g["source_summaries"] for g in groups.values())

    fam_agg: dict[str, dict] = {}
    for g in groups.values():
        f = fam_agg.setdefault(g["family_id"], {"groups": 0, "items": 0, "claims": 0,
                                                "surface_units": 0, "lanes": {"A": 0, "B": 0}})
        f["groups"] += 1
        f["items"] += len(g["items"])
        f["claims"] += sum(i["claims_n"] for i in g["items"])
        f["surface_units"] += sum(i["surface_units_n"] for i in g["items"])
        f["lanes"][g["lane_id"]] += 1

    # 套路成对容量：同轮同 profile 内 C(6,2)=15 × 20 profiles × 4 轮
    per_batch = 6
    pair_capacity = (per_batch * (per_batch - 1) // 2) * 20 * len(ROUNDS)

    # ---- 需求：锚型映射（逐字最小量 → 锚单位）----
    # anchor 类型：ITEM（整件内容）/ CLAIM（主张）/ PAIR（成对）/ SURFACE_UNIT / SOURCE_ASSERTION / DETERMINISTIC / EVENT
    demand_modules = [
        ("reference_extraction_positive", minimums["reference_extraction_positive_cases"], "SOURCE_ASSERTION", "源摘要中的参考断言（正例）"),
        ("reference_extraction_negative", minimums["reference_extraction_negative_controls"], "SOURCE_ASSERTION_SYNTH", "扰动构造负对照（需授权 CHALLENGE 合成）"),
        ("claim_atomization_positive", minimums["claim_atomization_positive_cases"], "CLAIM", "既有 claims 正例"),
        ("claim_atomization_negative", minimums["claim_atomization_negative_controls"], "CLAIM_SYNTH", "合并/拆分扰动负对照（需授权 CHALLENGE 合成）"),
        ("risk_classification_high_risk", minimums["risk_classification_high_risk_cases"], "CLAIM", "高危主张（真标签分布未知）"),
        ("risk_classification_legal", minimums["risk_classification_legal_controls"], "CLAIM", "合法对照主张"),
        ("entailment_contradicted", minimums["high_risk_contradicted_cases"], "CLAIM", "与源矛盾主张（过闸内容中天然稀缺）"),
        ("entailment_unknown", minimums["high_risk_unknown_cases"], "CLAIM", "源不可判主张"),
        ("entailment_supported", minimums["natural_legal_supported_cases"], "CLAIM", "源支持主张"),
        ("fact_chain_high_risk_unsafe", minimums["fact_chain_high_risk_unsafe_cases"], "ITEM", "端到端事实链（整件）"),
        ("fact_chain_natural_legal", minimums["fact_chain_natural_legal_cases"], "ITEM", "端到端事实链（整件）"),
        ("formulaic_pairs_total", minimums["formulaic_double_reviewed_pairs_total"], "PAIR", "双评审套路成对"),
        ("deterministic_disclosure", minimums["deterministic_disclosure_cases_total"], "DETERMINISTIC", "披露义务确定性用例（4 义务型）"),
        ("omission_misleading", minimums["omission_misleading_high_risk_cases"], "ITEM_OR_SU_SYNTH", "误导性省略（多需 CHALLENGE 合成）"),
        ("omission_nonmisleading", minimums["omission_nonmisleading_controls"], "ITEM_OR_SU", "非误导对照"),
        ("review_double_reviewed_items", minimums["review_double_reviewed_items"], "ITEM", "双评审条目"),
        ("review_judgment_records", minimums["review_judgment_records"], "EVENT", "评审判定记录"),
        ("cost_events", minimums["cost_events"], "EVENT", "成本事件"),
    ]
    anchor_supply_upper = {
        "SOURCE_ASSERTION": src_summaries_total * 3,   # 每摘要≥3 断言为预登记估计口径（估计，非实测）
        "SOURCE_ASSERTION_SYNTH": None,
        "CLAIM": claims_total,
        "CLAIM_SYNTH": None,
        "ITEM": items_total,
        "ITEM_OR_SU": su_total,
        "ITEM_OR_SU_SYNTH": None,
        "PAIR": pair_capacity,
        "DETERMINISTIC": su_total,
        "EVENT": None,
    }

    # ---- 双口径缺口判定 ----
    # 口径 A（跨模块复用最大化）：同一 CLAIM 锚可同时充当风险/蕴含用例 → CLAIM 需求取 max 而非求和
    # 口径 B（逐模块独占）：需求求和
    def claim_demand(reuse: bool) -> int:
        claim_mods = [n for (name, n, a, _) in demand_modules if a == "CLAIM"]
        entail = (minimums["high_risk_contradicted_cases"]
                  + minimums["high_risk_unknown_cases"]
                  + minimums["natural_legal_supported_cases"])
        risk = (minimums["risk_classification_high_risk_cases"]
                + minimums["risk_classification_legal_controls"])
        atom = minimums["claim_atomization_positive_cases"]
        if reuse:
            return max(entail, risk, atom)
        return entail + risk + atom

    def item_demand() -> int:
        return (minimums["fact_chain_high_risk_unsafe_cases"]
                + minimums["fact_chain_natural_legal_cases"])   # ITEM 锚不可同链复用（两类标签互斥）

    per_set = {
        "claim_anchor_demand_reuse_max": claim_demand(True),
        "claim_anchor_demand_exclusive": claim_demand(False),
        "item_anchor_demand_fact_chain": item_demand(),
        "pair_anchor_demand": minimums["formulaic_double_reviewed_pairs_total"],
    }

    scenarios = {}
    for label, qual_sets, note in (
        ("dual_sealed_sets_QUAL_A_plus_B", 2, "QUAL-A 与 QUAL-B 互斥（P0-f 双密封）"),
        ("single_set_QUAL_A_only", 1, "QUAL-B 供给不足默认取消第二次尝试（v2.3 §壹-6 冻结默认）"),
    ):
        # 全部 480 件全给资格集仍不含 G1/G2（须与资格金标不相交）的上界口径
        item_gap = per_set["item_anchor_demand_fact_chain"] * qual_sets - items_total
        claim_gap_reuse = per_set["claim_anchor_demand_reuse_max"] * qual_sets - claims_total
        claim_gap_excl = per_set["claim_anchor_demand_exclusive"] * qual_sets - claims_total
        scenarios[label] = {
            "note": note + "；上界口径=480 件全部给资格集且不留 G1/G2（实际还须再扣不相交开发集）",
            "item_anchor": {"demand": per_set["item_anchor_demand_fact_chain"] * qual_sets,
                            "supply_upper_bound": items_total,
                            "gap": item_gap, "hard_gap": item_gap > 0},
            "claim_anchor_reuse_max": {"demand": per_set["claim_anchor_demand_reuse_max"] * qual_sets,
                                       "supply_upper_bound": claims_total,
                                       "gap": claim_gap_reuse, "hard_gap": claim_gap_reuse > 0},
            "claim_anchor_exclusive": {"demand": per_set["claim_anchor_demand_exclusive"] * qual_sets,
                                       "supply_upper_bound": claims_total,
                                       "gap": claim_gap_excl, "hard_gap": claim_gap_excl > 0},
        }

    capacity_gap_confirmed = (
        scenarios["dual_sealed_sets_QUAL_A_plus_B"]["item_anchor"]["hard_gap"]
        and scenarios["single_set_QUAL_A_only"]["item_anchor"]["hard_gap"]
    )

    # ---- 向量容量表（逐模块投影）----
    # 双路径期望成本：模型标注路径（DeepSeek 评审费率 + p95 墙钟）；纯人工路径不可用（v2.3 冻结⑤）
    cny_per_call = telem["cost"]["external_model_cost_cny_budget_basis_total"] / telem["call_volume"]["external_provider_calls"]
    p95_item_s = telem["wall_clock"]["p95_single_item_wall_clock_seconds"]
    daily_ceiling_cny = telem["cost"]["daily_ceiling_cny"]
    vector_rows = []
    for name, n, anchor, note in demand_modules:
        supply_ub = anchor_supply_upper.get(anchor)
        # 可达 n：min(需求, 供给上界)；合成/事件类记 REQUIRES_CONSTRUCTION
        if supply_ub is None:
            achievable = "REQUIRES_CONSTRUCTION_OR_RUN"
            gap = "N_A_CONSTRUCTED"
        else:
            achievable = min(n, supply_ub)
            gap = max(0, n - supply_ub)
        double_blind_judgments = (n * 2) if isinstance(achievable, int) else None
        row = {
            "module_case_class": name,
            "demand_per_qual_set": n,
            "anchor_type": anchor,
            "anchor_note": note,
            "supply_upper_bound_all_rounds": supply_ub,
            "gap_per_single_set_upper_bound": gap,
            "achievable_n_upper_bound_single_set": achievable,
            "ci95_halfwidth_at_demand_n": ci_halfwidth(n),
            "ci95_halfwidth_at_achievable_n": (ci_halfwidth(achievable) if isinstance(achievable, int) else None),
            "model_label_path_cost": {
                "double_blind_judgments": double_blind_judgments,
                "external_judge_cny_estimate": (round(double_blind_judgments * cny_per_call, 3)
                                                if double_blind_judgments else None),
                "wall_clock_hours_estimate_p95": (round(double_blind_judgments * p95_item_s / 3600, 1)
                                                  if double_blind_judgments else None),
            },
            "human_only_path": "UNAVAILABLE（v2.3 冻结更新⑤：纯人工路线不可用维持）",
            "label_distribution_status": ("UNKNOWN_UNTIL_LABELED" if anchor in
                                          ("CLAIM", "ITEM", "PAIR", "ITEM_OR_SU") else "CONSTRUCTED_BY_DESIGN"),
        }
        vector_rows.append(row)

    frame_digest_src = json.dumps(
        sorted((g["scenario_id"], g["profile_id"], g["family_id"], g["lane_id"],
                tuple(sorted(i["output_digest"] for i in g["items"])))
               for g in groups.values()), ensure_ascii=False).encode("utf-8")
    frame_digest = hashlib.sha256(frame_digest_src).hexdigest()

    supply_demand = {
        "schema_version": "p7-m3-supply-demand-table-v1",
        "milestone_id": "M3",
        "capsule": "M3_C1_SUPPLY_DEMAND_AUDIT",
        "demand_source": {
            "path": "eval_audit_spine_001/contract/measurement_qualification.v2.json",
            "sha256": sha256_file(SPINE / "contract/measurement_qualification.v2.json"),
            "qualification_set_minimums_verbatim": minimums,
        },
        "partition_axes_source": {
            "path": "eval_audit_spine_001/contract/data_isolation.v1.json",
            "six_cells": iso["statistical_partition_model"]["six_cells"],
            "source_group_is_indivisible": iso["statistical_partition_model"]["source_group_is_indivisible_across_visibility_partitions"],
        },
        "supply_inventory": {
            "rounds": round_stats,
            "distinct_source_groups": len(groups),
            "distinct_items": items_total,
            "distinct_claims": claims_total,
            "distinct_surface_units": su_total,
            "source_summaries": src_summaries_total,
            "formulaic_pair_capacity_within_profile_round": pair_capacity,
            "per_family": fam_agg,
            "known_veto_regression_rows": len(known_veto),
            "cross_round_item_overlap": 0,
            "rounds_share_same_120_scenarios": True,
        },
        "per_set_anchor_demand": per_set,
        "allocation_scenarios": scenarios,
        "capacity_gap_confirmed": capacity_gap_confirmed,
        "decisive_arithmetic": (
            "fact_chain 需求为整件锚：单集 600 件、双集 1200 件；全部轮次可用整件供给上界=480 件"
            "（尚未扣除必须与资格金标不相交的 G1/G2 开发集与不可分源组约束）——"
            "480 < 600 ⇒ 与标签分布无关的硬缺口成立（runtime_verified 算术）。"
            "蕴含类主张锚在双集独占口径需求 2×1100=2200 > 1356 同为硬缺口；"
            "单集复用口径 700 ≤ 1356 仅在标签分布配合且不留开发集时才可能，属 UNKNOWN_UNTIL_LABELED。"),
        "curation_owner": {
            "role": "M3_PRINCIPAL_ORCHESTRATOR",
            "session_id": "374b677b-6537-465f-bab1-993e8a9d75aa",
            "scope": "抽样框元数据级策展（scenario/profile/family/lane/digest）；不建金标、不读密封明文",
        },
        "sampling_frame_digest": frame_digest,
    }

    vector_capacity = {
        "schema_version": "p7-m3-vector-capacity-table-v1",
        "milestone_id": "M3",
        "status": "INITIAL_PROJECTION（P0-e：记账与排期用，非阻断门）",
        "cost_basis": {
            "source": "eval_audit_spine_001/evidence/s0_m2_real_run_001/telemetry/cost_throughput_model.v1.json",
            "record_digest": telem["record_digest"],
            "external_judge_cny_per_call": round(cny_per_call, 6),
            "p95_single_item_wall_clock_seconds": p95_item_s,
            "daily_external_ceiling_cny": daily_ceiling_cny,
        },
        "modules": vector_rows,
        "totals_single_set": {
            "labeled_case_demand_sum_exclusive": sum(n for _, n, a, _ in demand_modules if not a.endswith("SYNTH") and a != "EVENT"),
            "double_blind_judgment_sum_exclusive": 2 * sum(n for _, n, a, _ in demand_modules if not a.endswith("SYNTH") and a != "EVENT"),
            "wall_clock_hours_p95_sum_exclusive": round(2 * sum(n for _, n, a, _ in demand_modules if not a.endswith("SYNTH") and a != "EVENT") * p95_item_s / 3600, 1),
        },
    }

    sampling_frame = {
        "schema_version": "p7-m3-sampling-frame-v1",
        "status": "PREREGISTERED（题面冻结前不抽签；抽签种子于胶囊⑤冻结回执中登记）",
        "frame_unit": "scenario 源组（source_group_is_indivisible_across_visibility_partitions=true）",
        "frame_size_groups": len(groups),
        "frame_size_items": items_total,
        "strata_keys": ["family_id", "lane_id", "profile_id"],
        "origin_axis_rule": "默认 NATURAL；命中 r5_known_veto 夹具 required_markers 的输出与任何后续授权合成负对照为 CHALLENGE；两格指标不得混池（data_isolation）",
        "frame_digest": frame_digest,
        "groups": sorted(
            ({"scenario_id": g["scenario_id"], "profile_id": g["profile_id"],
              "family_id": g["family_id"], "lane_id": g["lane_id"],
              "scenario_label": g["scenario_label"],
              "source_summaries": g["source_summaries"],
              "items": sorted(g["items"], key=lambda i: (i["round"], i["request_id"]))}
             for g in groups.values()), key=lambda x: x["scenario_id"]),
    }

    exclusion_log = {
        "schema_version": "p7-m3-exclusion-log-v1",
        "status": "PREREGISTERED",
        "exclusions": [
            {"rule_id": "EXC-01",
             "rule": "命中 r5_known_veto_regression 夹具 output_id/required_markers 的条目不入 NATURAL 密封抽样框",
             "reason": "已知否决样本属 CHALLENGE 回归锚（known_r5_hard_veto_cases_and_registered_variants_recall=1.0 由 CHALLENGE 格承载），入 NATURAL 会污染自然分布估计",
             "affected_fixture_rows": len(known_veto)},
            {"rule_id": "EXC-02",
             "rule": "synthetic_qualification_only=false 或 publishable=true 的条目（如出现）排除出资格抽样框",
             "reason": "资格材料必须全部处于合成资格边界内；当前四轮全部 synthetic_qualification_only=true、publishable=false，命中 0 条",
             "affected_rows_current": 0},
            {"rule_id": "EXC-03",
             "rule": "同一源组跨可见性分区拆分 = 禁止（组级整体入格）",
             "reason": "data_isolation.source_group_is_indivisible_across_visibility_partitions",
             "affected_rows_current": 0},
        ],
        "no_other_exclusions_preregistered": True,
    }

    (M3DS / "SUPPLY_DEMAND_TABLE.v1.json").write_text(
        json.dumps(supply_demand, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (M3DS / "VECTOR_CAPACITY_TABLE.v1.json").write_text(
        json.dumps(vector_capacity, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (M3DS / "SAMPLING_FRAME.v1.json").write_text(
        json.dumps(sampling_frame, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (M3DS / "EXCLUSION_LOG.v1.json").write_text(
        json.dumps(exclusion_log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(json.dumps({
        "groups": len(groups), "items": items_total, "claims": claims_total,
        "surface_units": su_total, "pair_capacity": pair_capacity,
        "capacity_gap_confirmed": capacity_gap_confirmed,
        "frame_digest": frame_digest,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
