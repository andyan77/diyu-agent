#!/usr/bin/env python3
"""§5.1/§5.3 保全直算：在密封区内直接读金标记录 → 记录级 core 校验 → cluster-aware
聚合 → 产出绑定 active generation + 摘要的公开计数回执。

动机（M3-R1 §5.1）：pre_m0_readiness.evaluate_set_readiness 原本信任调用方递来的任意
public_counts JSON——可被伪造洗绿。本工具把「计数」从可信输入变成**由密封明文复算**：
custody 侧读 sealed 金标记录、跑 spine.validate_qualification_records、按 §5.3 独立
source/evidence 单位去重后计数，回执带 custody_binding（active generation + faces/gold/
index 摘要）。checker/就绪门必须调 verify_binding 复核「计数==复算 且 摘要吻合」，
而不是只重算回执里的布尔（§5.1 硬要求）。

主编排会话零明文：本工具由保全/隔离会话在密封区调用；stdout 只吐聚合与摘要。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve()
P7 = HERE.parents[2]
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(HERE.parent))
from spine.canonical import digest_json  # noqa: E402
from spine import qualification_data as qd  # noqa: E402
import pre_m0_readiness as R  # noqa: E402

HIGH = {"HIGH", "CRITICAL"}
LEGAL_LOW = {"LOW", "MEDIUM"}


def _is(rec: dict, module: str, role: str | None = None) -> bool:
    if rec.get("module") != module:
        return False
    return role is None or rec.get("record_role") == role


# 每个 COUNT_KEY 的 (predicate, count_mode)。count_mode 显式声明该分母的合法独立统计单位，
# 取代原先会误算的隐式 pair_id/item_id 启发式（§5.3 + §六A）：
#   "source_group"    —— distinct source_group_id：同一 source_group 只计一个独立单位
#                        （cluster-aware，同源变体不虚增有效 N）。用于全部「cases」类分母。
#   "distinct_unit"      —— distinct 被评单元（pair_id→item_id→case_id）：如 formulaic 双审 pair 数。
#   "double_reviewed_item" —— distinct item_id 且该 item 具 >=2 互异 reviewer_id（真正被双审的条目，
#                        与 calibration.py double_reviewed_item_count 语义一致；单评 item 不计入）。
#   "judgment_record"    —— distinct (被评单元, reviewer_id) 判断记录：如 review judgment 记录数
#                        （40 item × 2 reviewer = 80；同一 reviewer 对同一 item 重复提交不虚增）。
# 注（§六A 修复）：review 记录角色在 m0 仅有 "judgment"（min 80），无 "review_item"。
#   review_double_reviewed_items = role=judgment 中具 >=2 reviewer 的 distinct item_id（=40）；
#   review_judgment_records      = role=judgment 的 distinct (item_id,reviewer_id)（=80）。
CLASS_PREDICATES: dict[str, tuple[Callable[[dict], bool], str]] = {
    "reference_extraction_positive_cases":
        (lambda r: _is(r, "reference_extraction") and r.get("gold_present") is True, "source_group"),
    "reference_extraction_negative_controls":
        (lambda r: _is(r, "reference_extraction") and r.get("gold_present") is False, "source_group"),
    "claim_atomization_positive_cases":
        (lambda r: _is(r, "claim_atomization") and r.get("gold_present") is True, "source_group"),
    "claim_atomization_negative_controls":
        (lambda r: _is(r, "claim_atomization") and r.get("gold_present") is False, "source_group"),
    "risk_classification_high_risk_cases":
        (lambda r: _is(r, "risk_classification") and r.get("gold_risk") in HIGH, "source_group"),
    "risk_classification_legal_controls":
        (lambda r: _is(r, "risk_classification") and r.get("case_origin") == "NATURAL"
         and r.get("gold_risk") in LEGAL_LOW, "source_group"),
    "high_risk_contradicted_cases":
        (lambda r: _is(r, "entailment") and r.get("gold_label") == "CONTRADICTED"
         and r.get("gold_risk") in HIGH, "source_group"),
    "high_risk_unknown_cases":
        (lambda r: _is(r, "entailment") and r.get("gold_label") == "UNKNOWN"
         and r.get("gold_risk") in HIGH, "source_group"),
    "natural_legal_supported_cases":
        (lambda r: _is(r, "entailment") and r.get("gold_label") == "SUPPORTED"
         and r.get("case_origin") == "NATURAL", "source_group"),
    "fact_chain_high_risk_unsafe_cases":
        (lambda r: _is(r, "fact_chain") and r.get("gold_safe_to_clear") is False
         and r.get("gold_risk") in HIGH, "source_group"),
    "fact_chain_natural_legal_cases":
        (lambda r: _is(r, "fact_chain") and r.get("case_origin") == "NATURAL"
         and r.get("gold_safe_to_clear") is True, "source_group"),
    "formulaic_double_reviewed_pairs_total":
        (lambda r: _is(r, "formulaic", "judgment"), "distinct_unit"),
    "formulaic_positive_pairs_minimum":
        (lambda r: _is(r, "formulaic", "adjudication") and r.get("final_verdict") == "FORMULAIC", "distinct_unit"),
    "formulaic_negative_pairs_minimum":
        (lambda r: _is(r, "formulaic", "adjudication") and r.get("final_verdict") == "NOT_FORMULAIC", "distinct_unit"),
    "formulaic_necessary_grammar_pairs_minimum":
        (lambda r: _is(r, "formulaic", "adjudication") and r.get("final_verdict") == "NECESSARY_GRAMMAR", "distinct_unit"),
    "deterministic_disclosure_cases_total":
        (lambda r: _is(r, "disclosure"), "source_group"),
    "omission_misleading_high_risk_cases":
        (lambda r: _is(r, "omission") and r.get("gold_misleading") is True
         and r.get("gold_risk") in HIGH, "source_group"),
    "omission_nonmisleading_controls":
        (lambda r: _is(r, "omission") and r.get("gold_misleading") is False, "source_group"),
    "review_double_reviewed_items":
        (lambda r: _is(r, "review_calibration", "judgment"), "double_reviewed_item"),
    "review_judgment_records":
        (lambda r: _is(r, "review_calibration", "judgment"), "judgment_record"),
}


def _independent_key(rec: dict) -> tuple[str, str]:
    """§六B 合法独立统计单位：默认 = source_group_id（同一 source_group 的变体/记录只计一个
    独立单位——同源变体不虚增有效 N）；仅当记录显式标 independent_evidence_unit=true 且带
    非空 source_evidence_digest（分别有源、可追溯可复算）时，才细化到 evidence 单位。
    禁止把一个 source_group 随意切成 per-claim/per-variant 伪独立样本（见 _reject_pseudo_independent）。"""
    if rec.get("independent_evidence_unit") is True:
        ev = rec.get("source_evidence_digest")
        if isinstance(ev, str) and ev:
            return ("EV", ev)
    return ("SG", str(rec.get("source_group_id")))


def _reject_pseudo_independent(records: list[dict]) -> list[str]:
    """§六B 反伪独立：同一 source_group 内被标 independent_evidence_unit=true 的记录，必须
    各带互异 source_evidence_digest（分别有源）。重复=把一份证据切成伪独立样本 → 报错 fail-closed。"""
    by_group: dict[str, list[str]] = {}
    for r in records:
        if r.get("independent_evidence_unit") is True:
            by_group.setdefault(str(r.get("source_group_id")), []).append(
                str(r.get("source_evidence_digest")))
    return sorted({f"pseudo_independent_evidence_unit:{sg}"
                   for sg, evs in by_group.items() if len(evs) != len(set(evs))})


def _count_class(records: list[dict], predicate: Callable[[dict], bool],
                 count_mode: str) -> int:
    """按 count_mode 计该分母的合法独立统计单位（§5.3 + §六A + §六B）。"""
    matched = [r for r in records if predicate(r)]
    if count_mode == "source_group":
        # §5.3+§六B：distinct 合法独立单位（默认 source_group；仅显式独立证据单位才细化）
        return len({_independent_key(r) for r in matched})
    if count_mode == "judgment_record":
        # §六A：独立单位=(被评单元, reviewer_id)；同一 reviewer 对同一单元重复提交只计一次
        return len({(str(r.get("pair_id") or r.get("item_id") or r.get("case_id")),
                     str(r.get("reviewer_id"))) for r in matched})
    if count_mode == "double_reviewed_item":
        # §六A：真正被双审的 item = 具 >=2 互异 reviewer_id 的 distinct item_id（单评 item 不计）
        by_item: dict[str, set] = {}
        for r in matched:
            by_item.setdefault(str(r.get("item_id")), set()).add(str(r.get("reviewer_id")))
        return sum(1 for reviewers in by_item.values() if len(reviewers) >= 2)
    # "distinct_unit"：distinct 被评单元（pair_id→item_id→case_id）——item/pair 维度，不含 reviewer
    keyfield = "pair_id" if any("pair_id" in r for r in matched) else "item_id"
    if any(keyfield in r for r in matched):
        return len({str(r.get(keyfield)) for r in matched})
    return len({str(r.get("case_id")) for r in matched})


def _count_raw_class(records: list[dict], predicate: Callable[[dict], bool],
                     count_mode: str) -> int:
    """§四.6 发起人裁决：raw case 覆盖数（300/100 下限对此计）。source_group 类的 raw 单位 =
    distinct (source_group_id, mechanism)——NATURAL + 每个不同挑战机制的合法变体各计 1，同机制不增
    覆盖。非 source_group 类（formulaic pair / review item）无机制变体维度，raw == cluster。"""
    if count_mode == "source_group":
        matched = [r for r in records if predicate(r)]
        # raw 单位在 cluster 独立键（_independent_key：默认 source_group，显式 independent_evidence_unit
        # 时细化到 EV 单位）之上再叠加 mechanism 维度（不同挑战机制的合法变体各计 1）。
        return len({(_independent_key(r), str(r.get("mechanism") or "NATURAL")) for r in matched})
    return _count_class(records, predicate, count_mode)


def _module_gold_field_coverage(records: list[dict]) -> dict[str, list[str]]:
    cov: dict[str, set[str]] = {}
    for r in records:
        module = r.get("module")
        if module not in R.MODULE_GOLD_FIELDS:
            continue
        present = {f for f in R.MODULE_GOLD_FIELDS[module] if f in r}
        cov.setdefault(module, set()).update(present)
    return {m: sorted(v) for m, v in cov.items()}


def _derive_two_independent_labels(records: list[dict]) -> bool:
    """每条记录须 >=2 条互异身份的 gold_review_provenance（validate 已强制；此处冗余复核）。"""
    for r in records:
        reviews = r.get("gold_review_provenance") or []
        identities = {str(rv.get("reviewer_identity")) for rv in reviews
                      if isinstance(rv, dict)}
        if len(reviews) < 2 or len(identities) < 2:
            return False
    return True


def recompute_public_counts(records: list[dict], *, set_id: str,
                            active_generation_id: str,
                            dataset_manifest_digest: str,
                            faces_sha256: str, gold_sha256: str,
                            environmental_flags: dict[str, bool] | None = None,
                            known_r5_input_binding_completeness: float = 0.0,
                            cost_expected_event_manifests: int = 0,
                            cost_rate_cards: int = 0) -> dict[str, Any]:
    """密封记录 → 记录级 core 校验 → cluster-aware 计数 → 绑定生成/摘要的公开计数。

    environmental_flags: custody 侧独立证明的过程旗标（ab 互斥/DEV 隔离/顺序/无泄漏）；
    计数与覆盖一律**由本函数从密封记录复算**，不接受调用方递入（§5.1 反伪造核心）。
    """
    # 记录级 core 校验须**逐 (module, record_role) 组**跑：不同模块/角色 gold 字段不同，
    # 一个统一 gold_field_names 会误拒（validate 要求 expected ⊆ 每条 supplied）。
    # 每组以该组共有 gold_field_names 交集为下限 + 该组独立 index。
    index = qd.build_qualification_record_index(
        records, dataset_manifest_digest=dataset_manifest_digest)
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        groups.setdefault((r.get("module"), r.get("record_role")), []).append(r)
    val_passed = True
    val_errors: list[str] = []
    total_unique = 0
    for (module, role), grp in sorted(groups.items(), key=lambda kv: str(kv[0])):
        common = set.intersection(*[set(r.get("gold_field_names") or [])
                                    for r in grp]) if grp else set()
        grp_index = qd.build_qualification_record_index(
            grp, dataset_manifest_digest=dataset_manifest_digest)
        grp_val = qd.validate_qualification_records(
            grp, expected_dataset_manifest_digest=dataset_manifest_digest,
            gold_field_names=sorted(common) or ["gold_field_names"],
            qualification_record_index=grp_index,
            require_gold_review_provenance=True)
        val_passed &= grp_val["passed"]
        val_errors.extend(f"{module}/{role}:{e}" for e in grp_val["errors"])
        total_unique += grp_val["unique_case_count"]
    # §六B 反伪独立：同源被切成伪独立样本 → core 校验失败 fail-closed
    pseudo_errors = _reject_pseudo_independent(records)
    if pseudo_errors:
        val_passed = False
        val_errors.extend(pseudo_errors)
    validation = {"passed": val_passed, "errors": sorted(set(val_errors)),
                  "unique_case_count": total_unique}

    # §四.6 双计数：counts=raw case N（300/100 覆盖门）；cluster_counts=distinct source-group N
    #（统计独立分母，驱动 cluster-aware CI/功效；同源变体不增 cluster N）。资格报告须双披露。
    counts = {}
    cluster_counts = {}
    for key, (predicate, count_mode) in CLASS_PREDICATES.items():
        counts[key] = _count_raw_class(records, predicate, count_mode)
        cluster_counts[key] = _count_class(records, predicate, count_mode)

    obligation_types = sorted({r.get("obligation_type") for r in records
                               if r.get("module") == "disclosure"
                               and r.get("obligation_type")})
    families = sorted({r.get("family_id") for r in records if r.get("family_id")})
    module_cov = _module_gold_field_coverage(records)

    flags = dict(environmental_flags or {})
    flags["two_independent_labels_per_record"] = _derive_two_independent_labels(records)

    public_counts = {
        "schema_version": "p7-qual-custody-public-counts-v1",
        "set": set_id,
        "counts": counts,
        # §四.6 双披露：cluster_counts = distinct source-group 独立单位数（同源变体不增）；
        # 供 cluster-aware CI/功效与资格报告披露。counts(raw) ≥ 下限门；cluster ≥ 功效 n_min 门。
        "cluster_counts": cluster_counts,
        "deterministic_disclosure_obligation_types_present": len(obligation_types),
        "obligation_types": obligation_types,
        # §5.4 边界：known-R5 在 M3 只证「输入案例+注册变体绑定完备」（input binding），
        # 不是运行后 recall（后者 M4 盲预测才产生）。字段名如实反映 M3 冻结属性。
        "known_r5_input_binding_completeness": known_r5_input_binding_completeness,
        # §5.4 M3 冻结成本输入：expected 事件 manifest + 费率卡（M3 冻结）；
        # source event manifest / 实际 cost events 属 M4 运行产物，M3 不产不检。
        "cost_expected_event_manifests": int(cost_expected_event_manifests),
        "cost_rate_cards": int(cost_rate_cards),
        "module_gold_field_coverage": module_cov,
        "family_coverage": families,
        "faces_sha256": faces_sha256,
        "gold_sha256": gold_sha256,
        # governance（环境旗标由 custody 证明；记录级 two_independent 已复算）
        "ab_mutually_exclusive": bool(flags.get("ab_mutually_exclusive")),
        "dev_isolation": bool(flags.get("dev_isolation")),
        "qual_order_ok": bool(flags.get("qual_order_ok")),
        "sealed_no_leak": bool(flags.get("sealed_no_leak")),
        "two_independent_labels_per_record": flags["two_independent_labels_per_record"],
        "adjudication_on_disagreement": bool(flags.get("adjudication_on_disagreement")),
        # §5.1 custody 绑定：受信来源=密封记录复算，非调用方输入
        "custody_binding": {
            "active_generation_id": active_generation_id,
            "dataset_manifest_digest": dataset_manifest_digest,
            "record_count": len(records),
            "records_recompute_digest": _records_recompute_digest(records),
            "qualification_index_digest": index["index_digest"],
            "core_validation_passed": validation["passed"],
            "core_validation_errors": validation["errors"][:20],
            "unique_case_count": validation["unique_case_count"],
            "main_session_plaintext_contact": "NONE",
        },
        "counts_source": "RECOMPUTED_FROM_SEALED_RECORDS (not caller-provided)",
    }
    return public_counts


def _records_recompute_digest(records: list[dict]) -> str:
    """密封记录集的确定性摘要（case_digest 排序）——绑定回执与实际密封内容。"""
    return digest_json(sorted(str(r.get("case_digest")) for r in records))


def verify_binding(public_counts: dict, records: list[dict]) -> list[str]:
    """checker/就绪门侧硬复核（§5.1）：计数/覆盖/摘要必须==从密封记录复算，且 core 校验 PASS。

    伪造 public_counts（手改数字/摘要）→ 与复算不符 → 返回非空错误 → fail-closed。
    """
    errors: list[str] = []
    binding = public_counts.get("custody_binding") or {}
    dmd = binding.get("dataset_manifest_digest")
    if not isinstance(dmd, str) or len(dmd) != 64:
        return ["custody_binding.dataset_manifest_digest_invalid"]
    fresh = recompute_public_counts(
        records, set_id=public_counts.get("set", "?"),
        active_generation_id=binding.get("active_generation_id", ""),
        dataset_manifest_digest=dmd,
        faces_sha256=public_counts.get("faces_sha256", ""),
        gold_sha256=public_counts.get("gold_sha256", ""),
        environmental_flags={
            k: public_counts.get(k) for k in
            ("ab_mutually_exclusive", "dev_isolation", "qual_order_ok",
             "sealed_no_leak", "adjudication_on_disagreement")},
        known_r5_input_binding_completeness=public_counts.get(
            "known_r5_input_binding_completeness", 0.0),
        cost_expected_event_manifests=public_counts.get(
            "cost_expected_event_manifests", 0),
        cost_rate_cards=public_counts.get("cost_rate_cards", 0))
    if not fresh["custody_binding"]["core_validation_passed"]:
        errors.append("core_validation_failed:" + ";".join(
            fresh["custody_binding"]["core_validation_errors"][:5]))
    if public_counts.get("counts") != fresh["counts"]:
        errors.append("counts_mismatch_vs_recompute")
    if public_counts.get("cluster_counts") != fresh["cluster_counts"]:
        errors.append("cluster_counts_mismatch_vs_recompute")
    if (public_counts.get("module_gold_field_coverage")
            != fresh["module_gold_field_coverage"]):
        errors.append("module_coverage_mismatch_vs_recompute")
    if sorted(public_counts.get("family_coverage", [])) != fresh["family_coverage"]:
        errors.append("family_coverage_mismatch_vs_recompute")
    if (public_counts.get("deterministic_disclosure_obligation_types_present")
            != fresh["deterministic_disclosure_obligation_types_present"]):
        errors.append("obligation_types_mismatch_vs_recompute")
    for bkey in ("records_recompute_digest", "qualification_index_digest",
                 "record_count"):
        if binding.get(bkey) != fresh["custody_binding"][bkey]:
            errors.append(f"custody_binding.{bkey}_mismatch_vs_recompute")
    if public_counts.get("two_independent_labels_per_record") is not \
            fresh["two_independent_labels_per_record"]:
        errors.append("two_independent_labels_flag_mismatch_vs_recompute")
    return errors


_ENV_FLAGS = ("ab_mutually_exclusive", "dev_isolation", "qual_order_ok",
              "sealed_no_leak", "adjudication_on_disagreement")


def verify_public_evidence_binding(public_counts: dict, set_id: str,
                                   anchors: dict | None) -> list[str]:
    """§六E/§三.2 端到端绑定（主会话零明文，只读公开锚证据）：把原本调用方可随意回灌的
    faces/gold/known-R5/环境旗标/active generation 绑定到**独立过程证据** anchors，而非只信
    public_counts 自述。anchors 缺项/不符 → 返回非空 → fail-closed（绝非 pass-through）。

    与 verify_binding 分工：verify_binding 在密封区从明文记录复算计数（需 records）；本函数
    在主会话侧只用公开摘要，把 verify_binding 无法覆盖的「调用方自述字段」钉到独立锚。

    anchors（R4 由密封区 custody 从真密封回执装配；此处只读公开摘要）:
      active_generation_id: str                     ACTIVE 指针
      faces_sha256 / gold_sha256: str               face/gold 冻结的独立摘要
      known_r5_input_binding_completeness: float     独立影子核算的输入绑定完备度
      env_evidence: {flag: bool}                    每个环境旗标的独立证据
    """
    if not isinstance(anchors, dict):
        return ["public_evidence_anchors_absent"]  # fail-closed，非 pass-through
    errors: list[str] = []
    binding = public_counts.get("custody_binding") or {}
    anchor_gen = anchors.get("active_generation_id")
    if not isinstance(anchor_gen, str) or not anchor_gen.strip():
        errors.append("active_generation_pointer_absent")
    elif binding.get("active_generation_id") != anchor_gen:
        errors.append("active_generation_id_not_bound_to_active_pointer")
    for field, slug in (("faces_sha256", "faces_sha256_not_bound_to_face_freeze"),
                        ("gold_sha256", "gold_sha256_not_bound_to_gold_freeze")):
        anchor_val = anchors.get(field)
        if (not isinstance(anchor_val, str) or len(anchor_val) != 64
                or public_counts.get(field) != anchor_val):
            errors.append(slug)
    pub_r5 = float(public_counts.get("known_r5_input_binding_completeness", 0.0))
    anchor_r5 = anchors.get("known_r5_input_binding_completeness")
    if anchor_r5 is None or float(anchor_r5) < pub_r5:
        errors.append("known_r5_not_bound_to_independent_evidence")
    env_ev = anchors.get("env_evidence") or {}
    for flag in _ENV_FLAGS:
        if public_counts.get(flag) is True and env_ev.get(flag) is not True:
            errors.append(f"governance:{flag}_not_evidenced")
    return sorted(set(errors))


def _load_records(path: Path) -> list[dict]:
    if path.is_dir():
        rows: list[dict] = []
        for p in sorted(path.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            rows.extend(data if isinstance(data, list) else [data])
        return rows
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True, help="密封金标记录 JSON 文件或目录（保全区）")
    ap.add_argument("--set", choices=["A", "B"], required=True)
    ap.add_argument("--active-generation", required=True)
    ap.add_argument("--dataset-manifest-digest", required=True)
    ap.add_argument("--faces-sha256", default="")
    ap.add_argument("--gold-sha256", default="")
    ap.add_argument("--out", help="公开计数回执输出路径（只聚合/摘要）")
    args = ap.parse_args()
    records = _load_records(Path(args.records))
    pc = recompute_public_counts(
        records, set_id=args.set, active_generation_id=args.active_generation,
        dataset_manifest_digest=args.dataset_manifest_digest,
        faces_sha256=args.faces_sha256, gold_sha256=args.gold_sha256)
    if args.out:
        Path(args.out).write_text(json.dumps(pc, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    summary = {"set": pc["set"], "record_count": pc["custody_binding"]["record_count"],
               "core_validation_passed": pc["custody_binding"]["core_validation_passed"],
               "counts": pc["counts"], "families": pc["family_coverage"],
               "index_digest": pc["custody_binding"]["qualification_index_digest"][:16]}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if pc["custody_binding"]["core_validation_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
