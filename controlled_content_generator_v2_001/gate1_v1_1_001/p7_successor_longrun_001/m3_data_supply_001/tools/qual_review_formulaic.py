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
