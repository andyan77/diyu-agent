#!/usr/bin/env python3
"""验证器合规 QUAL 金标记录装配（R3 goldfreeze + §5.1 custody 复算 + fixture 共用）。

产出的记录逐字段满足 spine.qualification_data.validate_qualification_records 的合同：
case/payload/gold_label 三摘要闭合 + >=2 独立 gold_review_provenance（互异身份、
CONFIRM 决定、逐字段绑定）+ 与 build_qualification_record_index 的索引条目一致。

关键：主编排会话不用本模块碰明文；本模块由保全会话/custody 工具在密封区内调用。
装配顺序（摘要依赖）：gold_label → payload → reviews(引用 payload/evidence/gold_label)
→ case_digest（覆盖整行）。任何一步顺序错都会被 validate_qualification_records 拒。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
P7 = HERE.parents[2]
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
from spine.canonical import digest_json  # noqa: E402

# validate_qualification_records 的 payload 排除集（逐字对齐 qualification_data）
_PAYLOAD_EXCLUDED = {
    "case_id", "case_digest", "case_payload_digest", "source_group_id",
    "visibility_partition", "dataset_manifest_digest", "gold_label_digest",
    "gold_field_names", "gold_review_provenance",
}


def _review_digest(review: dict[str, Any]) -> str:
    unsigned = dict(review)
    unsigned.pop("review_digest", None)
    return digest_json(unsigned)


def build_review(*, review_id: str, reviewer_identity: str, reviewer_kind: str,
                 case_id: str, case_payload_digest: str, source_evidence_digest: str,
                 gold_label_digest: str, evidence_digest: str,
                 model_revision: str | None = None,
                 prompt_digest: str | None = None) -> dict[str, Any]:
    """单条 gold_review_provenance（decision 恒 CONFIRM——记录级已裁决为金标）。

    AI 席须 model_revision + prompt_digest；HUMAN 席两者须为 None（验证器硬约束）。
    """
    review = {
        "review_id": review_id,
        "reviewer_identity": reviewer_identity,
        "reviewer_kind": reviewer_kind,
        "model_revision": model_revision,
        "prompt_digest": prompt_digest,
        "case_id": case_id,
        "case_payload_digest": case_payload_digest,
        "source_evidence_digest": source_evidence_digest,
        "gold_label_digest": gold_label_digest,
        "decision": "CONFIRM",
        "evidence_digest": evidence_digest,
        "review_digest": "",
    }
    review["review_digest"] = _review_digest(review)
    return review


def assemble_gold_record(*, case_id: str, source_group_id: str,
                         source_evidence_digest: str,
                         dataset_manifest_digest: str,
                         gold_fields: dict[str, Any],
                         payload_fields: dict[str, Any],
                         reviews_meta: list[dict[str, Any]]) -> dict[str, Any]:
    """装配一条验证器合规记录。

    gold_fields: {gold_field_name: value}（进 gold_label_digest 与 payload）。
    payload_fields: 题面/家族/模块等内容字段（进 payload，不进 gold_label_digest）；
                    禁与保留字段/gold_field 重名。
    reviews_meta: >=2 条 {review_id, reviewer_identity, reviewer_kind[, model_revision,
                  prompt_digest], evidence_digest}；互异 review_id 与 reviewer_identity。
    """
    if len(reviews_meta) < 2:
        raise ValueError("assemble_gold_record requires >=2 reviews")
    gold_field_names = sorted(gold_fields)
    gold_label_digest = digest_json({f: gold_fields[f] for f in gold_field_names})

    row: dict[str, Any] = {
        "case_id": case_id,
        "source_group_id": source_group_id,
        "visibility_partition": "HIDDEN",
        "dataset_manifest_digest": dataset_manifest_digest,
        "gold_field_names": gold_field_names,
        "source_evidence_digest": source_evidence_digest,
        "gold_label_digest": gold_label_digest,
    }
    overlap = (set(payload_fields) & (set(row) | set(gold_fields)
                                      | {"case_digest", "case_payload_digest",
                                         "gold_review_provenance"}))
    if overlap:
        raise ValueError(f"payload_fields collide with reserved/gold names: {sorted(overlap)}")
    row.update(gold_fields)
    row.update(payload_fields)

    # payload 摘要（排除保留集；此刻行内尚无 case_digest/case_payload_digest/reviews）
    case_payload_digest = digest_json(
        {k: v for k, v in row.items() if k not in _PAYLOAD_EXCLUDED})
    row["case_payload_digest"] = case_payload_digest

    reviews: list[dict[str, Any]] = []
    for meta in reviews_meta:
        reviews.append(build_review(
            review_id=meta["review_id"],
            reviewer_identity=meta["reviewer_identity"],
            reviewer_kind=meta["reviewer_kind"],
            model_revision=meta.get("model_revision"),
            prompt_digest=meta.get("prompt_digest"),
            evidence_digest=meta["evidence_digest"],
            case_id=case_id,
            case_payload_digest=case_payload_digest,
            source_evidence_digest=source_evidence_digest,
            gold_label_digest=gold_label_digest))
    row["gold_review_provenance"] = reviews

    # case_digest 覆盖整行（除自身）——最后一步
    row["case_digest"] = digest_json(
        {k: v for k, v in row.items() if k != "case_digest"})
    return row
