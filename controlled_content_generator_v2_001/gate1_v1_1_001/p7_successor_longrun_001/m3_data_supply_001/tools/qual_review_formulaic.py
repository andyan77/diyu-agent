#!/usr/bin/env python3
"""§四.3/§四.4 真实 review + formulaic 标注子管线（producer）。

取代 pilot 的确定性占位 `_coverage_units()`：真实内容 → 双席独立标注 → 逐项/逐轴一致 →
分歧走既有仲裁路径 → 组装 review_units / formulaic_units（喂既有 derive_*）→ 按
measurement_qualification.v2 **既有** 门计算 agreement 指标（不发明新全局门）。

密封纪律同 labeler：题面/标签明文只落 sealed_custody_001/**（gitignore）；本模块由保全会话/
pilot/runner 在密封区调用，stdout 与公开回执只吐数量/一致率/verdict 分布，编排会话零明文。

seat 调用经注入 `call(prompt, ok_check, stem) -> rows|None`（pilot/runner 绑定真 L.attempt_call +
密封 registry；单测注入 mock）。producer 本体（构造/解析/一致/组装/报表）为确定性纯函数，可单测。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve()
P7 = HERE.parents[2]
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(P7 / "m3_data_supply_001/gold/tools"))
from spine.canonical import digest_json                       # noqa: E402
from spine.formulaic import (verdict_from_axes, canonical_pair_id,  # noqa: E402
                             agreement_metrics, AXES)
from spine import calibration as CAL                            # noqa: E402
from spine import qualification_data as QD                      # noqa: E402
import qual_gold_derivation as GD                               # noqa: E402

ANNEXC = P7 / "m3_data_supply_001/annotation/annotation_protocol_annexC_qual.v1.json"

REVIEW_DECISIONS = ("APPROVE", "REJECT")
_AX5 = {"SAME", "DIFFERENT", "UNCLEAR", "NECESSARY_GRAMMAR"}
_AXTD = {"SURFACE_ONLY", "STRUCTURAL_CHANGE", "UNCLEAR", "NECESSARY_GRAMMAR"}

Call = Callable[[str, Callable[[list], bool], str], "list | None"]


# =====================================================================  review (§四.3)

def review_rows_ok(rows: Any, expected: set[str]) -> bool:
    """review 席位输出合格判据：覆盖全部 item_id 且每条 decision∈{APPROVE,REJECT}+hard_veto bool。"""
    if not isinstance(rows, list):
        return False
    if {r.get("item_id") for r in rows if isinstance(r, dict)} != expected:
        return False
    for r in rows:
        if r.get("decision") not in REVIEW_DECISIONS or not isinstance(r.get("hard_veto"), bool):
            return False
    return True


def _review_slim(it: dict) -> dict:
    return {k: it.get(k, "") for k in ("item_id", "content", "claim_boundary",
                                       "authorization_scope", "source_summary_a",
                                       "source_summary_b")}


def label_review_seat(items: list[dict], seat: str, *, call: Call,
                      template: str) -> dict[str, dict]:
    """一个真实审核席位对每个 item 独立判 decision+hard_veto（双盲，不互看）。"""
    expected = {it["item_id"] for it in items}
    seat_label = "A(Codex-GPT)" if seat == "A" else "B(Opus-4.8)"
    prompt = template.replace("{seat}", seat_label).replace(
        "{batch_json}", json.dumps([_review_slim(it) for it in items],
                                   ensure_ascii=False, indent=1))
    rows = call(prompt, lambda r: review_rows_ok(r, expected), f"review_{seat}")
    if rows is None:
        raise SystemExit(f"review 席 {seat} 标注失败")
    return {r["item_id"]: {"decision": r["decision"], "hard_veto": bool(r["hard_veto"]),
                           "rationale": r.get("rationale", "")} for r in rows}


def assemble_review_units(items: list[dict], dec_a: dict[str, dict],
                          dec_b: dict[str, dict], *,
                          reviewer_a: str = "REVIEWER_A::codex-gpt",
                          reviewer_b: str = "REVIEWER_B::opus-4-8",
                          prompt_digest_a: str, prompt_digest_b: str) -> list[dict]:
    """items + 双席真实决定 → review_units（每 item 两条真实 judgment：A/B 各一，各自 decision）。

    reviewer_id 用**审核席身份**（≠ 内容 author_identity，满足 role_collision_absent）；
    双方决定按各自真实输出保留（review_calibration 度量的正是双审一致，不由主编排写死）。
    """
    units = []
    for it in items:
        iid = it["item_id"]
        if iid not in dec_a or iid not in dec_b:
            raise SystemExit(f"review item {iid} 缺一席决定")
        units.append({
            "item_id": iid, "family_id": it["family_id"],
            "source_group_id": it["source_group_id"],
            "author_identity": it["author_identity"],
            "judgments": [
                {"reviewer_id": reviewer_a, "decision": dec_a[iid]["decision"],
                 "hard_veto": dec_a[iid]["hard_veto"], "model_revision": "gpt-5.6-sol",
                 "prompt_digest": prompt_digest_a},
                {"reviewer_id": reviewer_b, "decision": dec_b[iid]["decision"],
                 "hard_veto": dec_b[iid]["hard_veto"], "model_revision": "claude-opus-4-8",
                 "prompt_digest": prompt_digest_b}]})
    return units


def review_agreement_report(units: list[dict], *, dataset_manifest_digest: str,
                            seat_provenance_for: Callable) -> dict:
    """由 review_units 派生记录并跑 spine 既有 qualify_review_calibration；返回既有门指标
    （approval 一致/正负特异一致/硬门一致/类分布/双审数）+ adjudication_rate（分歧率）。不发明新门。"""
    recs = GD.derive_review_records(units, dataset_manifest_digest=dataset_manifest_digest,
                                    seat_provenance_for=seat_provenance_for)
    index = QD.build_qualification_record_index(
        recs, dataset_manifest_digest=dataset_manifest_digest)
    cal = CAL.qualify_review_calibration(
        recs, dataset_manifest_digest=dataset_manifest_digest,
        qualification_record_index=index)
    disagree = sum(1 for u in units
                   if u["judgments"][0]["decision"] != u["judgments"][1]["decision"])
    report = {
        "double_reviewed_item_count": cal["double_reviewed_item_count"],
        "observed_decision_classes": cal["observed_decision_classes"],
        "approval_decision_agreement": cal["approval_decision_agreement"],
        "approval_positive_specific_agreement": cal["approval_positive_specific_agreement"],
        "approval_negative_specific_agreement": cal["approval_negative_specific_agreement"],
        "hard_veto_relevant_item_count": cal["hard_veto_relevant_item_count"],
        "hard_veto_agreement": cal["hard_veto_agreement"],
        "adjudication_rate": round(disagree / max(1, len(units)), 4),
        # 门（结构门 pilot 可查；一致率阈值达标属正式规模，pilot 报告不作阻断）
        "calibration_gates": cal["gates"],
        "calibration_qualified": cal["qualified"],
        "gate_source": "measurement_qualification.v2 module_gates.review_calibration（既有门，未发明）",
    }
    return {"records": recs, "report": report}


# ================================================================  formulaic (§四.4)

_ADJ_IDENTITY = "ADJ::opus-4-8-isolated"


def axis_rows_ok(rows: Any, expected_refs: set[str]) -> bool:
    """formulaic 轴标注席位输出合格判据：覆盖全 pair_ref 且 6 轴齐全、值合法枚举。"""
    if not isinstance(rows, list):
        return False
    if {r.get("pair_ref") for r in rows if isinstance(r, dict)} != expected_refs:
        return False
    for r in rows:
        ax = r.get("axes")
        if not isinstance(ax, dict) or set(ax) != set(AXES):
            return False
        if any(ax[a] not in _AX5 for a in AXES[:-1]):
            return False
        if ax["transformation_depth"] not in _AXTD:
            return False
    return True


def _pair_slim(p: dict) -> dict:
    return {"pair_ref": p["pair_ref"], "left_content": p["left_content"],
            "right_content": p["right_content"],
            "claim_boundary": p.get("claim_boundary", ""),
            "authorization_scope": p.get("authorization_scope", "")}


def label_formulaic_seat(pairs: list[dict], seat: str, *, call: Call,
                         template: str) -> dict[str, dict]:
    """一个真实席位对每个 pair 沿 6 轴独立标注（双盲，不互看）→ {pair_ref: axes}。"""
    expected = {p["pair_ref"] for p in pairs}
    seat_label = "A(Codex-GPT)" if seat == "A" else "B(Opus-4.8)"
    prompt = template.replace("{seat}", seat_label).replace(
        "{batch_json}", json.dumps([_pair_slim(p) for p in pairs],
                                   ensure_ascii=False, indent=1))
    rows = call(prompt, lambda r: axis_rows_ok(r, expected), f"formaxis_{seat}")
    if rows is None:
        raise SystemExit(f"formulaic 轴 席 {seat} 标注失败")
    return {r["pair_ref"]: r["axes"] for r in rows}


def _verdict(axes: dict, exc_id: str | None, where: str) -> str:
    try:
        return verdict_from_axes(axes, exc_id)
    except ValueError as e:
        raise SystemExit(f"formulaic {where}: 轴→verdict 非法（{e}）；"
                         f"含 NECESSARY_GRAMMAR 轴须预注册 exception（post-hoc 禁止）")


def adjudicate_formulaic_axes(pairs_needing: list[dict], axes_a: dict, axes_b: dict, *,
                              call: Call, template: str) -> dict[str, dict]:
    """双席 verdict 分歧的 pair → 隔离仲裁席重标 6 轴 → {pair_ref: final_axes}。无分歧则空。"""
    if not pairs_needing:
        return {}
    disputes = []
    for p in pairs_needing:
        ref = p["pair_ref"]
        disputes.append({"pair_ref": ref,
                         "disputed_axes": [ax for ax in AXES
                                           if axes_a[ref].get(ax) != axes_b[ref].get(ax)],
                         "left_content": p["left_content"], "right_content": p["right_content"],
                         "claim_boundary": p.get("claim_boundary", ""),
                         "authorization_scope": p.get("authorization_scope", ""),
                         "axes_jia": axes_a[ref], "axes_yi": axes_b[ref]})
    expected = {d["pair_ref"] for d in disputes}
    prompt = template.replace("{batch_json}", json.dumps(disputes, ensure_ascii=False, indent=1))
    rows = call(prompt, lambda r: axis_rows_ok(r, expected), "formaxis_adj")
    if rows is None:
        raise SystemExit("formulaic 轴 仲裁失败")
    return {r["pair_ref"]: r["axes"] for r in rows}


def pairs_needing_adjudication(pairs: list[dict], axes_a: dict, axes_b: dict) -> list[dict]:
    """双席 verdict 不一致（或含 INDETERMINATE）的 pair 才需仲裁（口径同 spine gate）。"""
    out = []
    for p in pairs:
        ref, exc = p["pair_ref"], p.get("necessary_grammar_exception_id")
        va = _verdict(axes_a[ref], exc, f"{ref}[A]")
        vb = _verdict(axes_b[ref], exc, f"{ref}[B]")
        if va != vb or "INDETERMINATE" in (va, vb):
            out.append(p)
    return out


def assemble_formulaic_units(pairs: list[dict], axes_a: dict, axes_b: dict,
                             adj_axes_map: dict[str, dict], *,
                             reviewer_a: str = "REVIEWER_A::codex-gpt",
                             reviewer_b: str = "REVIEWER_B::opus-4-8",
                             prompt_digest_a: str, prompt_digest_b: str) -> list[dict]:
    """双席逐轴标签 + 分歧仲裁 → formulaic_units（每 pair 两条 per-reviewer judgment + 最终裁决）。

    双席 verdict 一致→final=席A轴，无仲裁席；分歧→final=仲裁轴，挂真实仲裁席身份+证据摘要，
    且 final 非 INDETERMINATE（与 spine gate requires_adjudicator 口径一致）。
    """
    units = []
    for p in pairs:
        ref = p["pair_ref"]
        exc = p.get("necessary_grammar_exception_id")
        aa, ab = axes_a[ref], axes_b[ref]
        va = _verdict(aa, exc, f"{ref}[A]")
        vb = _verdict(ab, exc, f"{ref}[B]")
        if va == vb and va != "INDETERMINATE":
            final_axes, final_verdict = dict(aa), va
            adj_identity = adj_evidence = None
        else:
            if ref not in adj_axes_map:
                raise SystemExit(f"formulaic {ref}: verdict 分歧但缺仲裁轴")
            final_axes = adj_axes_map[ref]
            final_verdict = _verdict(final_axes, exc, f"{ref}[final]")
            if final_verdict == "INDETERMINATE":
                raise SystemExit(f"formulaic {ref}: 仲裁未能定论（final INDETERMINATE）")
            adj_identity = _ADJ_IDENTITY
            adj_evidence = digest_json({"pair": ref, "final_axes": final_axes})
        units.append({
            "left_id": p["left_id"], "right_id": p["right_id"],
            "family_id": p["family_id"], "source_group_id": p["source_group_id"],
            "left_author_identity": p["left_author_identity"],
            "right_author_identity": p["right_author_identity"],
            "necessary_grammar_exception_id": exc,
            "is_formulaic": final_verdict == "FORMULAIC",
            "final_verdict": final_verdict, "final_axes": final_axes,
            "adjudicator_identity": adj_identity,
            "adjudication_evidence_digest": adj_evidence,
            "judgments": [
                {"reviewer_id": reviewer_a, "axes": aa, "verdict": va,
                 "model_revision": "gpt-5.6-sol", "prompt_digest": prompt_digest_a},
                {"reviewer_id": reviewer_b, "axes": ab, "verdict": vb,
                 "model_revision": "claude-opus-4-8", "prompt_digest": prompt_digest_b}]})
    return units


def formulaic_agreement_report(units: list[dict], *, dataset_manifest_digest: str,
                               seat_provenance_for: Callable, batch_id: str) -> dict:
    """derive formulaic 记录 → 跑 spine 既有 agreement_metrics（judgment 逐 reviewer verdict）。
    返回既有门指标（raw/positive/negative 一致、cohen κ 可解释时、adjudication_rate）+ verdict 分布。"""
    out = GD.derive_formulaic_records(units, dataset_manifest_digest=dataset_manifest_digest,
                                      seat_provenance_for=seat_provenance_for, batch_id=batch_id)
    judg = out["judgments"]
    index = QD.build_qualification_record_index(judg, dataset_manifest_digest=dataset_manifest_digest)
    m = agreement_metrics(judg, dataset_manifest_digest=dataset_manifest_digest,
                          qualification_record_index=index)
    dist: dict[str, int] = {}
    for u in units:
        dist[u["final_verdict"]] = dist.get(u["final_verdict"], 0) + 1
    report = {
        "pairs": len(units),
        "final_verdict_distribution": dict(sorted(dist.items())),
        "raw_agreement": m["raw_agreement"],
        "positive_specific_agreement": m["positive_specific_agreement"],
        "negative_specific_agreement": m["negative_specific_agreement"],
        "cohen_kappa_pairwise": m["cohen_kappa_pairwise"],
        "kappa_interpretable": m["interpretable"],
        "adjudication_rate": m["adjudication_rate"],
        "reviewer_independence_valid": m["reviewer_independence_valid"],
        "review_coverage_valid": m["review_coverage_valid"],
        "gate_source": "measurement_qualification.v2 module_gates.formulaic_construct（既有门，未发明）",
    }
    return {"derived": out, "metrics": m, "report": report}
