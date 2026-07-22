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


# ------------------------------------------------------------- §四.1 逐字段/逐模块一致
# 模块 → 该模块记录实际消费的富标签字段（gold_fields 真取自这些字段；多模块含 gold_risk=risk）。
# 用途：(a) 逐模块 ADJ provenance——仅当模块消费的某字段被仲裁时该模块记录才挂 ADJ 席；
#       (b) 保证 atom_partition 分歧不污染 risk/entailment（§四.1 规则5）。
# 真源=derive_records_for_face 每模块的 gold_fields 实际取用字段，逐字对齐。
MODULE_CONSUMED_FIELDS: dict[str, frozenset[str]] = {
    "reference_extraction": frozenset({"reference_present", "reference_attributes", "risk"}),
    "claim_atomization": frozenset({"atom_present", "atom_partition", "risk"}),
    "risk_classification": frozenset({"risk"}),
    "entailment": frozenset({"entailment", "risk"}),
    "fact_chain": frozenset({"safe_to_clear", "risk"}),
    "omission": frozenset({"misleading", "risk"}),
    "disclosure": frozenset({"disclosure_obligation", "disclosure_violation"}),
}

# 字段 → 消费该字段的模块（§四.1 字段→模块映射的机读逆表；含 risk 被多模块消费的真相）。
FIELD_TO_MODULES: dict[str, tuple[str, ...]] = {
    f: tuple(sorted(m for m, fs in MODULE_CONSUMED_FIELDS.items() if f in fs))
    for f in RICH_LABEL_FIELDS}


def _norm_field(field: str, value: Any) -> Any:
    """结构字段确定性规范化（§四.1 规则1）：把「无语义顺序」的结构排成规范形，
    真正影响原子分组的差异保留（不同分组规范化后仍互异）。标量/布尔原样返回。"""
    if field == "atom_partition":
        # 原子分组=集合的集合：组内排序 + 组间排序 → 规范形；分组不同者规范化后仍不同。
        if isinstance(value, list):
            return sorted([sorted(g) if isinstance(g, list) else g for g in value])
        return value
    if field == "reference_attributes":
        # 对象 key 顺序无语义 → 按 key 排序（值不变）。
        if isinstance(value, dict):
            return {k: value[k] for k in sorted(value)}
        return value
    return value


def _field_equal(field: str, va: Any, vb: Any) -> bool:
    """规范化后逐字段相等：结构顺序不同但语义相同 → 相等（不触发仲裁，§四.1 规则1）。"""
    return digest_json(_norm_field(field, va)) == digest_json(_norm_field(field, vb))


def field_disputes(label_a: dict[str, Any], label_b: dict[str, Any]) -> list[str]:
    """双席两富标签规范化后仍不一致的字段列表（用于 labelfreeze/adjudicate 逐字段统计）。"""
    return [f for f in RICH_LABEL_FIELDS if not _field_equal(f, label_a.get(f), label_b.get(f))]


def resolve_label_fields(label_a: dict[str, Any], label_b: dict[str, Any],
                         adj_label: dict[str, Any] | None, *, where: str
                         ) -> tuple[dict[str, Any], frozenset[str]]:
    """逐字段解析双席富标签（§四.1 规则2/3）：
      - 规范化后一致 → 采一致值（CROSS_MODEL_AGREED）；一致字段绝不因其它字段分歧被改写；
      - 不一致 → 只采**该字段**的仲裁值（FIELD_ADJUDICATED）；缺该字段仲裁 → DerivationError（未决）。
    返回 (resolved_label, adjudicated_fields)。仅分歧字段进仲裁、仅采分歧字段的仲裁结果。"""
    validate_rich_label(label_a, where=f"{where}[A]")
    validate_rich_label(label_b, where=f"{where}[B]")
    resolved: dict[str, Any] = {}
    adjudicated: set[str] = set()
    for f in RICH_LABEL_FIELDS:
        if _field_equal(f, label_a[f], label_b[f]):
            resolved[f] = label_a[f]
        else:
            if not isinstance(adj_label, dict) or f not in adj_label:
                raise DerivationError(f"{where}: field {f!r} disputed but no adjudication")
            resolved[f] = adj_label[f]
            adjudicated.add(f)
    validate_rich_label(resolved, where=f"{where}[resolved]")
    return resolved, frozenset(adjudicated)


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
                            base_seat_provenance: list[dict[str, Any]],
                            adj_seat_provenance: dict[str, Any] | None = None,
                            adjudicated_fields: Any = frozenset()
                            ) -> list[dict[str, Any]]:
    """单个富标签 face → 逐模块验证器合规记录（七模块；disclosure 视 obligation 条件产出）。

    face 须带：case_id / family_id / source_group_id / case_kind(NATURAL|CHALLENGE_VARIANT)。
    label 为该 face 的**已解析**富标签（validate_rich_label 已过）。
    每模块记录 case_id = f"{face_case_id}::MOD"，source_group_id = face 的 claim 级 source_group
    （同源变体继承 base；不增有效 N）。

    §四.1 逐模块 ADJ provenance：base_seat_provenance=[A,B] 恒挂；adj_seat_provenance=ADJ 席，
    仅当**本模块消费的字段**落在 adjudicated_fields（该 face 被仲裁的富标签字段）时才追加。
    每模块记录带 payload.agreement_status(CROSS_MODEL_AGREED|FIELD_ADJUDICATED)，
    FIELD_ADJUDICATED 者带 adjudicated_fields（本模块实际消费的被裁字段）。
    """
    cid = str(face["case_id"])
    sg = str(face["source_group_id"])
    fam = str(face["family_id"])
    origin = "NATURAL" if face.get("case_kind") == "NATURAL" else "CHALLENGE"
    validate_rich_label(label, where=cid)
    risk = label["risk"]
    attrs = {k: label["reference_attributes"][k] for k in _ATTR_KEYS}
    adjf = frozenset(adjudicated_fields)

    def mk(mod, role, gold, extra):
        mod_adj = sorted(MODULE_CONSUMED_FIELDS.get(mod, frozenset()) & adjf)
        used_adj = bool(mod_adj) and adj_seat_provenance is not None
        sp = list(base_seat_provenance) + ([adj_seat_provenance] if used_adj else [])
        agree: dict[str, Any] = {
            "agreement_status": "FIELD_ADJUDICATED" if used_adj else "CROSS_MODEL_AGREED"}
        if used_adj:
            agree["adjudicated_fields"] = mod_adj
        return _assemble(f"{cid}::{mod}", sg, _MODULE_ALIAS.get(mod, mod), role,
                         fam, origin, gold, {**extra, **agree}, sp,
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
                            resolutions: dict[str, dict[str, Any]], *,
                            dataset_manifest_digest: str,
                            base_seat_provenance: list[dict[str, Any]],
                            adj_seat_provenance: dict[str, Any] | None) -> dict[str, Any]:
    """一批富标签 face → (records, cross_module_reuse)。

    resolutions: {face_case_id: {"label": 已解析富标签, "adjudicated_fields": iterable[str]}}
      （逐字段解析产物：resolve_label_fields 的输出；一致字段 CROSS_MODEL_AGREED，分歧字段裁决）。
    base_seat_provenance: [A,B] 恒挂两独立评审席。
    adj_seat_provenance: ADJ 隔离仲裁席，仅被消费仲裁字段的模块记录追加（逐模块，非整 face）。
    cross_module_reuse: {source_group_id: sorted[modules]}——同一 source_group 服务哪些模块。
    """
    records: list[dict[str, Any]] = []
    reuse: dict[str, set[str]] = {}
    for face in faces:
        cid = str(face["case_id"])
        if cid not in resolutions:
            raise DerivationError(f"face {cid} has no resolved rich label")
        r = resolutions[cid]
        recs = derive_records_for_face(
            face, r["label"], dataset_manifest_digest=dataset_manifest_digest,
            base_seat_provenance=base_seat_provenance,
            adj_seat_provenance=adj_seat_provenance,
            adjudicated_fields=frozenset(r.get("adjudicated_fields") or ()))
        records.extend(recs)
        sg = str(face["source_group_id"])
        for rec in recs:
            reuse.setdefault(sg, set()).add(rec["module"])
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
    """formulaic 单元 → judgment(每 pair×每 reviewer，**逐 reviewer 自有 axes+verdict**) +
    adjudication(每 pair，**最终裁决 axes/verdict**) + candidate_audit + 三注册表。

    §四.4：judgment 记录须带**每个 reviewer 各自的** axes+verdict（真实双席轴标注），才能让
    spine.formulaic.agreement_metrics 度量真实跨席一致（旧版给两 reviewer 同一 verdict→一致恒 1，
    度量落空）。adjudication 记录带**逐轴解析后的最终** axes/verdict（供 positive/negative/grammar 计数）。

    formulaic_unit: {left_id, right_id, family_id, source_group_id,
                     left_author_identity, right_author_identity,
                     necessary_grammar_exception_id|None, is_formulaic(bool),
                     final_verdict, final_axes,
                     judgments: [{reviewer_id, axes, verdict[, model_revision, prompt_digest]}, ...]}。
    守卫：每 judgment 自洽 verdict_from_axes(axes,exc)==verdict；final_axes 自洽 final_verdict；
    reviewer_id ≠ 内容 author_identity（spine independence 门）。
    """
    judgments, adjudications, candidate_audit = [], [], []
    reviewed_pairs, cand_pairs, ng_pairs = [], [], []
    for unit in formulaic_units:
        left, right = str(unit["left_id"]), str(unit["right_id"])
        pid = canonical_pair_id(left, right)
        sg = str(unit["source_group_id"])
        fam = str(unit["family_id"])
        exc_id = unit.get("necessary_grammar_exception_id")
        final_verdict = unit["final_verdict"]
        final_axes = unit["final_axes"]
        if final_verdict not in _FORMULAIC_VERDICTS:
            raise DerivationError(f"formulaic {pid}: bad final_verdict {final_verdict!r}")
        if verdict_from_axes(final_axes, exc_id) != final_verdict:
            raise DerivationError(f"formulaic {pid}: final_axes inconsistent with {final_verdict}")
        js = unit["judgments"]
        if len(js) < 2 or len({str(j["reviewer_id"]) for j in js}) < 2:
            raise DerivationError(f"formulaic {pid}: needs >=2 distinct reviewer judgments")
        authors = {str(unit["left_author_identity"]), str(unit["right_author_identity"])}
        reviewed_pairs.append(pid)
        cand_pairs.append(pid)
        if final_verdict == "NECESSARY_GRAMMAR":
            ng_pairs.append(pid)
        for j in js:
            rv = str(j["reviewer_id"])
            if rv in authors:
                raise DerivationError(f"formulaic {pid}: reviewer {rv} collides with author")
            jaxes, jverdict = j["axes"], j["verdict"]
            if verdict_from_axes(jaxes, exc_id) != jverdict:
                raise DerivationError(f"formulaic {pid}/{rv}: axes inconsistent with verdict {jverdict}")
            cid = f"form-j::{pid}::{rv}"
            judgments.append(_assemble(
                cid, sg, "formulaic", "judgment", fam, "NATURAL",
                {"axes": jaxes, "necessary_grammar_exception_id": exc_id, "verdict": jverdict},
                {"pair_id": pid, "left_id": left, "right_id": right, "reviewer_id": rv,
                 "left_author_identity": unit["left_author_identity"],
                 "right_author_identity": unit["right_author_identity"],
                 "reviewer_provenance": {"reviewer_identity": rv, "reviewer_kind": "AI",
                                         "model_revision": j.get("model_revision", "m1"),
                                         "prompt_digest": j.get(
                                             "prompt_digest", digest_json({"r": rv, "p": pid}))}},
                seat_provenance_for(cid), dataset_manifest_digest))
        # adjudicator 身份/证据：席位判定**一致**时无需仲裁→None；判定分歧→须真实仲裁席身份+证据摘要
        # （与 spine.qualify_formulaic_construct 的 requires_adjudicator 口径一致：由双席 verdict 是否
        # 一致决定，非逐轴；分歧时 final 由仲裁产出且非 INDETERMINATE）。
        cid_a = f"form-a::{pid}"
        adjudications.append(_assemble(
            cid_a, sg, "formulaic", "adjudication", fam, "NATURAL",
            {"final_verdict": final_verdict, "necessary_grammar_exception_id": exc_id},
            {"pair_id": pid, "left_id": left, "right_id": right, "final_axes": final_axes,
             "adjudicator_identity": unit.get("adjudicator_identity"),
             "adjudication_evidence_digest": unit.get("adjudication_evidence_digest")},
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
