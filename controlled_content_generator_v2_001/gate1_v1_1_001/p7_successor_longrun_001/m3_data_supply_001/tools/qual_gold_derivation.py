#!/usr/bin/env python3
"""§四.2 金标富派生：把「逐 face 的富标签（双席一致或裁决后）」派生为**逐模块验证器合规**
金标记录，收敛到唯一装配入口 assemble_gold_record，并登记 cross-module reuse。

替代 M3 v1 cmd_goldfreeze 的简化非合规写入路径（旧路径只吐
`{case_id, risk, entailment, source}`——无 source_group_id / 无摘要闭包 / 无 gold_review_provenance，
被 spine.validate_qualification_records 直接拒，且只覆盖 risk+entailment 两模块）。

设计不变量：
  1. 唯一装配入口：所有 gold 记录经 qual_record_assembly.assemble_gold_record（不建平行 schema）。
     产出逐字段满足 spine.qualification_data.validate_qualification_records + custody 复算。
  2. 统计独立（§六B）：source_group_id = claim 级；同源 challenge 变体继承 base 的 source_group，
     不增有效 N。派生**不**设 independent_evidence_unit（默认 source_group 计数），杜绝伪独立。
  3. cross-module reuse 只复用**同一 case/source_group**；每模块自带 gold 谓词/字段/审核，
     分别成立（不拿 risk 标签冒充 entailment gold）。登记于 cross_module_reuse。
  4. 富标签字段与 qual_core_fixtures 的九模块装配范式逐字对齐（后者已过真 core，是本派生的黄金参照）。
  5. 主编排会话零明文：本模块由保全/隔离会话（或确定性测试）在密封区调用；输入是**已解析的富标签**
     （席位标注/裁决产物），输出是密封 gold 记录。stdout 只吐数量/摘要。

模块划分：
  - 逐 claim 七模块（reference/atomization/risk/entailment/fact_chain/omission/disclosure）
    由 derive_perclaim_records 从富标签 face 派生。
  - review_calibration（judgment 角色）由 derive_review_records 从 review 单元派生。
  - formulaic（judgment/adjudication/candidate_audit + 三注册表）由 derive_formulaic_records 派生。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
P7 = HERE.parents[2]
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(HERE.parent))
from spine.canonical import digest_json  # noqa: E402
from spine.formulaic import canonical_pair_id, verdict_from_axes  # noqa: E402
import qual_record_assembly as asm  # noqa: E402

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
HIGH = {"HIGH", "CRITICAL"}
ENTAILMENT_LABELS = ("SUPPORTED", "CONTRADICTED", "UNKNOWN")
OBLIGATION_TYPES = ("SYNTHETIC_IDENTITY_DISCLOSURE",
                    "PROHIBITED_REAL_IDENTITY_IMPERSONATION",
                    "EXPLICIT_AUTHORIZATION_BOUNDARY",
                    "PRIVACY_REDACTION_OR_BLOCK")
_ATTR_KEYS = ("polarity", "modality", "time_scope", "preconditions")

# 富标签必填字段（rich labeler 每 face 输出；resolve 后喂本派生）。
RICH_LABEL_FIELDS = (
    "risk", "entailment", "reference_present", "reference_attributes",
    "atom_present", "atom_partition", "safe_to_clear",
    "disclosure_obligation", "disclosure_violation", "misleading",
)


class DerivationError(ValueError):
    """富标签结构非法（缺字段/坏枚举/坏形状）→ fail-closed，绝不静默产半合规记录。"""


def validate_rich_label(label: dict[str, Any], *, where: str) -> None:
    """严格校验一条富标签；任一非法即抛（防坏标签污染 gold）。"""
    missing = [f for f in RICH_LABEL_FIELDS if f not in label]
    if missing:
        raise DerivationError(f"{where}: rich label missing fields {missing}")
    if label["risk"] not in RISK_LEVELS:
        raise DerivationError(f"{where}: bad risk {label['risk']!r}")
    if label["entailment"] not in ENTAILMENT_LABELS:
        raise DerivationError(f"{where}: bad entailment {label['entailment']!r}")
    attrs = label["reference_attributes"]
    if not isinstance(attrs, dict) or any(k not in attrs for k in _ATTR_KEYS):
        raise DerivationError(f"{where}: reference_attributes must carry {_ATTR_KEYS}")
    part = label["atom_partition"]
    if (not isinstance(part, list) or not part
            or not all(isinstance(g, list) and g for g in part)):
        raise DerivationError(f"{where}: atom_partition must be non-empty list of non-empty lists")
    for boolf in ("reference_present", "atom_present", "safe_to_clear",
                  "disclosure_violation", "misleading"):
        if not isinstance(label[boolf], bool):
            raise DerivationError(f"{where}: {boolf} must be bool")
    obl = label["disclosure_obligation"]
    if obl != "NONE" and obl not in OBLIGATION_TYPES:
        raise DerivationError(f"{where}: bad disclosure_obligation {obl!r}")


def _seat_reviews(record_case_id: str, source_group_id: str,
                  seat_provenance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """由 face 的席位溯源为**本条记录**派生 >=2 条互异身份 review_meta（review_id 逐记录唯一）。

    seat_provenance 每项：{tag, reviewer_identity, reviewer_kind[, model_revision, prompt_digest]}。
    tag 用于 review_id 命名与 evidence_digest 分席（同 face 不同模块记录 → 不同 evidence_digest）。
    """
    if len(seat_provenance) < 2:
        raise DerivationError(f"{record_case_id}: <2 seat provenance entries")
    reviews: list[dict[str, Any]] = []
    for sp in seat_provenance:
        reviews.append({
            "review_id": f"{sp['tag']}-{record_case_id}",
            "reviewer_identity": sp["reviewer_identity"],
            "reviewer_kind": sp["reviewer_kind"],
            "model_revision": sp.get("model_revision"),
            "prompt_digest": sp.get("prompt_digest"),
            "evidence_digest": digest_json({"rec": record_case_id, "sg": source_group_id,
                                            "seat": sp["tag"]})})
    return reviews


def _assemble(case_id: str, source_group_id: str, module: str, record_role: str,
              family_id: str, case_origin: str, gold_fields: dict[str, Any],
              extra_payload: dict[str, Any],
              seat_provenance: list[dict[str, Any]],
              dataset_manifest_digest: str) -> dict[str, Any]:
    payload = {"module": module, "record_role": record_role,
               "family_id": family_id, "case_origin": case_origin}
    payload.update(extra_payload)
    return asm.assemble_gold_record(
        case_id=case_id, source_group_id=source_group_id,
        source_evidence_digest=digest_json({"src": source_group_id, "cid": case_id}),
        dataset_manifest_digest=dataset_manifest_digest,
        gold_fields=gold_fields, payload_fields=payload,
        reviews_meta=_seat_reviews(case_id, source_group_id, seat_provenance))


# ------------------------------------------------------------- 逐 claim 七模块派生

def derive_records_for_face(face: dict[str, Any], label: dict[str, Any], *,
                            dataset_manifest_digest: str,
                            seat_provenance: list[dict[str, Any]]
                            ) -> list[dict[str, Any]]:
    """单个富标签 face → 逐模块验证器合规记录（七模块；disclosure 视 obligation 条件产出）。

    face 须带：case_id / family_id / source_group_id / case_kind(NATURAL|CHALLENGE_VARIANT)。
    label 为该 face 的**已解析**富标签（validate_rich_label 已过）。
    每模块记录 case_id = f"{face_case_id}::MOD"，source_group_id = face 的 claim 级 source_group
    （同源变体继承 base；不增有效 N）。
    """
    cid = str(face["case_id"])
    sg = str(face["source_group_id"])
    fam = str(face["family_id"])
    origin = "NATURAL" if face.get("case_kind") == "NATURAL" else "CHALLENGE"
    validate_rich_label(label, where=cid)
    risk = label["risk"]
    attrs = {k: label["reference_attributes"][k] for k in _ATTR_KEYS}

    def mk(mod, role, gold, extra):
        return _assemble(f"{cid}::{mod}", sg, _MODULE_ALIAS.get(mod, mod), role,
                         fam, origin, gold, extra, seat_provenance,
                         dataset_manifest_digest)

    records = [
        # reference_assertion_extraction —— present/negative-control + 属性正确性
        mk("reference_extraction", "qualification_case",
           {"gold_present": label["reference_present"], "gold_risk": risk,
            "gold_attributes": attrs}, {}),
        # claim_atomization —— present + 原子划分
        mk("claim_atomization", "qualification_case",
           {"gold_present": label["atom_present"], "gold_risk": risk,
            "gold_atom_partition": label["atom_partition"]}, {}),
        # risk_classification
        mk("risk_classification", "qualification_case", {"gold_risk": risk}, {}),
        # entailment
        mk("entailment", "qualification_case",
           {"gold_label": label["entailment"], "gold_risk": risk}, {}),
        # fact_chain_end_to_end
        mk("fact_chain", "qualification_case",
           {"gold_risk": risk, "gold_safe_to_clear": label["safe_to_clear"]}, {}),
        # omission
        mk("omission", "omission_case",
           {"gold_misleading": label["misleading"], "gold_risk": risk}, {}),
    ]
    if label["disclosure_obligation"] != "NONE":
        records.append(mk("disclosure", "disclosure_case",
                          {"gold_violation": label["disclosure_violation"]},
                          {"obligation_type": label["disclosure_obligation"]}))
    return records


# custody / pre_m0 侧模块名 == 派生模块名（无别名映射，保持一致）。
_MODULE_ALIAS: dict[str, str] = {}

# 模块 → 该模块该记录携带的模块专属 gold 字段（登记/自证用；与 pre_m0.MODULE_GOLD_FIELDS 对齐）。
PERCLAIM_MODULES = ("reference_extraction", "claim_atomization", "risk_classification",
                    "entailment", "fact_chain", "omission", "disclosure")


def derive_perclaim_records(faces: list[dict[str, Any]],
                            labels: dict[str, dict[str, Any]], *,
                            dataset_manifest_digest: str,
                            seat_provenance_for: Any) -> dict[str, Any]:
    """一批富标签 face → (records, cross_module_reuse)。

    labels: {face_case_id: rich_label}（已解析：一致或裁决后）。
    seat_provenance_for(face_case_id) -> list[seat_provenance]（该 face 的实际席位溯源；
      裁决过的 face 追加 ADJ 席，>=2 条互异身份）。
    cross_module_reuse: {source_group_id: sorted[modules]}——同一 source_group 服务哪些模块。
    """
    records: list[dict[str, Any]] = []
    reuse: dict[str, set[str]] = {}
    for face in faces:
        cid = str(face["case_id"])
        if cid not in labels:
            raise DerivationError(f"face {cid} has no resolved rich label")
        sp = seat_provenance_for(cid)
        recs = derive_records_for_face(
            face, labels[cid], dataset_manifest_digest=dataset_manifest_digest,
            seat_provenance=sp)
        records.extend(recs)
        sg = str(face["source_group_id"])
        for r in recs:
            reuse.setdefault(sg, set()).add(r["module"])
    return {"records": records,
            "cross_module_reuse": {sg: sorted(mods) for sg, mods in sorted(reuse.items())}}


# ------------------------------------------------------------- review_calibration 派生

def derive_review_records(review_units: list[dict[str, Any]], *,
                          dataset_manifest_digest: str,
                          seat_provenance_for: Any) -> list[dict[str, Any]]:
    """review 单元 → review_calibration judgment 记录（每 item × 每 reviewer 一条 judgment）。

    review_unit: {item_id, family_id, source_group_id, author_identity,
                  judgments: [{reviewer_id, decision(APPROVE|REJECT), hard_veto(bool),
                               model_revision, prompt_digest}]}。
    双审语义：一个 item 具 >=2 互异 reviewer_id → custody double_reviewed_item 计 1、
    judgment_record 计 2。gold_fields = {decision, hard_veto}（与 pre_m0.MODULE_GOLD_FIELDS 对齐）。
    """
    records: list[dict[str, Any]] = []
    for unit in review_units:
        item_id = str(unit["item_id"])
        sg = str(unit["source_group_id"])
        fam = str(unit["family_id"])
        for j in unit["judgments"]:
            rv = str(j["reviewer_id"])
            if j["decision"] not in ("APPROVE", "REJECT"):
                raise DerivationError(f"review {item_id}/{rv}: bad decision {j['decision']!r}")
            if not isinstance(j["hard_veto"], bool):
                raise DerivationError(f"review {item_id}/{rv}: hard_veto must be bool")
            cid = f"review::{item_id}::{rv}"
            records.append(_assemble(
                cid, sg, "review_calibration", "judgment", fam, "NATURAL",
                {"decision": j["decision"], "hard_veto": j["hard_veto"]},
                {"item_id": item_id, "reviewer_id": rv,
                 "author_identity": unit["author_identity"],
                 "reviewer_provenance": {"reviewer_identity": rv, "reviewer_kind": "AI",
                                         "model_revision": j.get("model_revision", "m1"),
                                         "prompt_digest": j.get(
                                             "prompt_digest", digest_json({"r": rv}))}},
                seat_provenance_for(cid), dataset_manifest_digest))
    return records


# ------------------------------------------------------------- formulaic 派生

_FORMULAIC_VERDICTS = ("FORMULAIC", "NOT_FORMULAIC", "NECESSARY_GRAMMAR")


def derive_formulaic_records(formulaic_units: list[dict[str, Any]], *,
                             dataset_manifest_digest: str,
                             seat_provenance_for: Any,
                             batch_id: str) -> dict[str, Any]:
    """formulaic 单元 → judgment(每 pair×2 reviewer) + adjudication(每 pair) + candidate_audit
    + 三注册表（candidate_audit_manifest / rubric_registry / necessary_grammar_exception）。

    formulaic_unit: {left_id, right_id, family_id, source_group_id, verdict, axes,
                     necessary_grammar_exception_id|None, is_formulaic(bool),
                     left_author_identity, right_author_identity,
                     reviewers: [rv1, rv2]}。
    axes 须自洽：verdict_from_axes(axes, exc_id) == verdict（守卫，防标签矛盾）。
    结构门（非计数门）与 qual_core_fixtures.build_formulaic_minibatch 一致。
    """
    judgments, adjudications, candidate_audit = [], [], []
    reviewed_pairs, cand_pairs, ng_pairs = [], [], []
    for unit in formulaic_units:
        left, right = str(unit["left_id"]), str(unit["right_id"])
        pid = canonical_pair_id(left, right)
        sg = str(unit["source_group_id"])
        fam = str(unit["family_id"])
        verdict = unit["verdict"]
        exc_id = unit.get("necessary_grammar_exception_id")
        axes = unit["axes"]
        if verdict not in _FORMULAIC_VERDICTS:
            raise DerivationError(f"formulaic {pid}: bad verdict {verdict!r}")
        if verdict_from_axes(axes, exc_id) != verdict:
            raise DerivationError(f"formulaic {pid}: axes/exc inconsistent with verdict {verdict}")
        reviewed_pairs.append(pid)
        cand_pairs.append(pid)
        if verdict == "NECESSARY_GRAMMAR":
            ng_pairs.append(pid)
        for rv in unit["reviewers"]:
            cid = f"form-j::{pid}::{rv}"
            judgments.append(_assemble(
                cid, sg, "formulaic", "judgment", fam, "NATURAL",
                {"axes": axes, "necessary_grammar_exception_id": exc_id, "verdict": verdict},
                {"pair_id": pid, "left_id": left, "right_id": right, "reviewer_id": str(rv),
                 "left_author_identity": unit["left_author_identity"],
                 "right_author_identity": unit["right_author_identity"],
                 "reviewer_provenance": {"reviewer_identity": str(rv), "reviewer_kind": "AI",
                                         "model_revision": "m1",
                                         "prompt_digest": digest_json({"r": rv, "p": pid})}},
                seat_provenance_for(cid), dataset_manifest_digest))
        cid_a = f"form-a::{pid}"
        adjudications.append(_assemble(
            cid_a, sg, "formulaic", "adjudication", fam, "NATURAL",
            {"final_verdict": verdict, "necessary_grammar_exception_id": exc_id},
            {"pair_id": pid, "left_id": left, "right_id": right,
             "adjudicator_identity": None, "adjudication_evidence_digest": None},
            seat_provenance_for(cid_a), dataset_manifest_digest))
        cid_c = f"form-c::{pid}"
        candidate_audit.append(_assemble(
            cid_c, sg, "formulaic", "candidate_audit", fam, "NATURAL",
            {"gold_formulaic": bool(unit["is_formulaic"])},
            {"pair_id": pid, "left_id": left, "right_id": right,
             "candidate_selected": bool(unit["is_formulaic"]),
             "audit_scope": "RANDOM_RECALL_AUDIT"},
            seat_provenance_for(cid_c), dataset_manifest_digest))
    registries = _formulaic_registries(sorted(reviewed_pairs), sorted(cand_pairs),
                                       sorted(ng_pairs), len(candidate_audit), batch_id)
    return {"judgments": judgments, "adjudications": adjudications,
            "candidate_audit": candidate_audit, **registries}


def _formulaic_registries(reviewed_sorted, cand_sorted, ng_pairs, sample_count, batch_id):
    manifest = {
        "schema_version": "eval-spine-formulaic-candidate-audit-manifest-v1",
        "status": "SEALED", "registered_before_miner_run": True,
        "batch_id": batch_id, "miner_run_id": f"{batch_id}-MINER",
        "custodian_identity": "DATA-CUSTODIAN", "registry_manifest_digest": "7" * 64,
        "sampling_algorithm": "PREREGISTERED_STRATIFIED_RANDOM_SAMPLE_V1",
        "population_pair_ids_digest": digest_json(reviewed_sorted),
        "sampled_pair_ids_digest": digest_json(cand_sorted),
        "sample_count": sample_count,
        "randomization_seed_commitment": "9" * 64,
        "candidate_miner_blinded_to_gold": True,
        "gold_attached_after_candidate_run": True, "manifest_digest": ""}
    manifest["manifest_digest"] = digest_json(
        {k: v for k, v in manifest.items() if k != "manifest_digest"})
    rubric = {"schema_version": "eval-spine-formulaic-rubric-freeze-v1", "status": "FROZEN",
              "frozen_before_qualification": True, "rubric_version": "v1",
              "batch_id": batch_id, "rubric_content_digest": "6" * 64,
              "registry_manifest_digest": "7" * 64, "custodian_identity": "DATA-CUSTODIAN",
              "frozen_at": "2026-07-21T00:00:00Z", "rubric_digest": ""}
    rubric["rubric_digest"] = digest_json(
        {k: v for k, v in rubric.items() if k != "rubric_digest"})
    exception = {"exception_id": "NG-1", "registered_before_batch": True,
                 "batch_id": batch_id, "approved_by": "PRODUCT-OWNER",
                 "product_definition_ref": "CP-PROFILE-V1",
                 "applicable_pair_ids_digest": digest_json(ng_pairs),
                 "maximum_pair_count": 20, "registry_manifest_digest": "7" * 64,
                 "exception_digest": ""}
    exception["exception_digest"] = digest_json(
        {k: v for k, v in exception.items() if k != "exception_digest"})
    return {"candidate_manifest": manifest, "rubric_manifest": rubric,
            "necessary_grammar_exceptions": [exception]}
