#!/usr/bin/env python3
"""§5.2 九条静态数据通道最小 core fixture：证明「装配 → 真验证器」端到端贯通。

R3 批量构造前置门：每模块产最小记录（gold 记录一律经 assemble_gold_record 装配，
formulaic 三类记录同源 + 三注册表按 spine 结构），逐条过**真**验证器：
  - spine.qualification_data.validate_qualification_records（记录级闭包）
  - spine.formulaic.qualify_formulaic_construct 的结构门（judgment/adjudication/
    candidate_audit/candidate_audit_manifest/rubric_registry/necessary_grammar_exception）
  - m0.MODULE_RECORD_ROLE_MINIMUMS 记录角色映射
  - pre_m0_readiness.MODULE_GOLD_FIELDS 覆盖 + qual_custody_recompute 计数

不建平行 schema、不含 LLM；由保全/隔离会话（或测试）调用，主编排会话零明文。
measurement_qualification.v2 与 m0.py 较严者为准（本 fixture 只证「最小一条可过」，
不凑下限——下限由容量计划 + R3-run 批量满足）。
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
from spine import calibration as cal  # noqa: E402
from spine import qualification_data as qd  # noqa: E402
import qual_record_assembly as asm  # noqa: E402

DMD = "d" * 64
FAM = "F1_PEOPLE_AND_REAL_SCENE"
_ATTRS = {"polarity": "AFFIRMATIVE", "modality": "ASSERTED",
          "time_scope": "PRESENT", "preconditions": None}

# 模块（pre_m0/custody 名） → (m0 module_id, record_role, gold_fields, extra_payload)
# gold 通道（各经 assemble_gold_record）：8 模块 + review（双审 2 条）。
GOLD_CHANNELS: dict[str, dict[str, Any]] = {
    "reference_extraction": {
        "m0_module": "reference_assertion_extraction", "record_role": "qualification_case",
        "gold_fields": {"gold_present": True, "gold_risk": "HIGH",
                        "gold_attributes": {"polarity": "AFFIRMATIVE", "modality": "ASSERTED",
                                            "time_scope": "PRESENT", "preconditions": None}},
        "payload": {"case_origin": "CHALLENGE"}},
    "claim_atomization": {
        "m0_module": "claim_atomization", "record_role": "qualification_case",
        "gold_fields": {"gold_present": True, "gold_risk": "HIGH",
                        "gold_atom_partition": [["a1", "a2"], ["a3"]]},
        "payload": {"case_origin": "CHALLENGE"}},
    "risk_classification": {
        "m0_module": "risk_classification", "record_role": "qualification_case",
        "gold_fields": {"gold_risk": "HIGH"}, "payload": {"case_origin": "CHALLENGE"}},
    "entailment": {
        "m0_module": "entailment", "record_role": "qualification_case",
        "gold_fields": {"gold_label": "CONTRADICTED", "gold_risk": "HIGH"},
        "payload": {"case_origin": "CHALLENGE"}},
    "fact_chain": {
        "m0_module": "fact_chain_end_to_end", "record_role": "qualification_case",
        "gold_fields": {"gold_risk": "HIGH", "gold_safe_to_clear": False},
        "payload": {"case_origin": "CHALLENGE"}},
    "disclosure": {
        "m0_module": "disclosure_and_omission", "record_role": "disclosure_case",
        "gold_fields": {"gold_violation": True},
        "payload": {"case_origin": "CHALLENGE",
                    "obligation_type": "SYNTHETIC_IDENTITY_DISCLOSURE"}},
    "omission": {
        "m0_module": "disclosure_and_omission", "record_role": "omission_case",
        "gold_fields": {"gold_misleading": True, "gold_risk": "HIGH"},
        "payload": {"case_origin": "CHALLENGE"}},
}


def _seats(case_id: str) -> list[dict[str, Any]]:
    return [
        {"review_id": f"A-{case_id}", "reviewer_identity": "SEAT_A::codex-gpt",
         "reviewer_kind": "AI", "model_revision": "gpt-5.6-sol",
         "prompt_digest": digest_json({"p": "A", "c": case_id}),
         "evidence_digest": digest_json({"e": case_id, "s": "A"})},
        {"review_id": f"B-{case_id}", "reviewer_identity": "SEAT_B::opus-4-8",
         "reviewer_kind": "AI", "model_revision": "claude-opus-4-8",
         "prompt_digest": digest_json({"p": "B", "c": case_id}),
         "evidence_digest": digest_json({"e": case_id, "s": "B"})}]


def _gold(case_id: str, module: str, record_role: str, gold_fields: dict,
          extra_payload: dict, *, source_group: str) -> dict[str, Any]:
    payload = {"module": module, "record_role": record_role, "family_id": FAM}
    payload.update(extra_payload)
    return asm.assemble_gold_record(
        case_id=case_id, source_group_id=source_group,
        source_evidence_digest=digest_json({"src": source_group, "cid": case_id}),
        dataset_manifest_digest=DMD, gold_fields=gold_fields, payload_fields=payload,
        reviews_meta=_seats(case_id))


def build_core_gold_records() -> list[dict[str, Any]]:
    """8 通道各 1 条 + review 双审 2 条（40item→80judgment 语义的最小样例：1 item×2 reviewer）。"""
    records: list[dict[str, Any]] = []
    for module, spec in GOLD_CHANNELS.items():
        records.append(_gold(f"core-{module}", module, spec["record_role"],
                             spec["gold_fields"], spec["payload"],
                             source_group=f"sg-{module}"))
    # review_calibration：1 item × 2 reviewer = 2 条 judgment（证角色 + 双审 item 语义）
    for reviewer in ("RV1", "RV2"):
        cid = f"core-review-{reviewer}"
        records.append(asm.assemble_gold_record(
            case_id=cid, source_group_id="sg-review-I0",
            source_evidence_digest=digest_json({"item": "I0"}), dataset_manifest_digest=DMD,
            gold_fields={"decision": "APPROVE", "hard_veto": False},
            payload_fields={"module": "review_calibration", "record_role": "judgment",
                            "family_id": FAM, "case_origin": "NATURAL",
                            "item_id": "I0", "reviewer_id": reviewer,
                            "author_identity": "AUTHOR_X",
                            "reviewer_provenance": {"reviewer_identity": reviewer,
                                                    "reviewer_kind": "AI",
                                                    "model_revision": "m1",
                                                    "prompt_digest": digest_json({"r": reviewer})}},
            reviews_meta=_seats(cid)))
    return records


_FORMULAIC_AXES = {
    "FORMULAIC": {"argument_spine": "SAME", "evidence_progression": "SAME",
                  "limitation_function": "DIFFERENT", "viewpoint_anchor": "SAME",
                  "closing_function": "DIFFERENT", "transformation_depth": "SURFACE_ONLY"},
    "NOT_FORMULAIC": {"argument_spine": "DIFFERENT", "evidence_progression": "DIFFERENT",
                      "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                      "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"},
    "NECESSARY_GRAMMAR": {"argument_spine": "NECESSARY_GRAMMAR", "evidence_progression": "DIFFERENT",
                          "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                          "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"},
}


def _formulaic_judgment(pair_id, left, right, reviewer, verdict, axes, exc_id):
    cid = f"form-j-{pair_id}-{reviewer}"
    return asm.assemble_gold_record(
        case_id=cid, source_group_id=f"sg-{pair_id}",
        source_evidence_digest=digest_json({"pair": pair_id, "rv": reviewer}),
        dataset_manifest_digest=DMD,
        gold_fields={"axes": axes, "necessary_grammar_exception_id": exc_id, "verdict": verdict},
        payload_fields={"module": "formulaic", "record_role": "judgment", "family_id": FAM,
                        "case_origin": "NATURAL", "pair_id": pair_id, "left_id": left,
                        "right_id": right, "reviewer_id": reviewer,
                        "left_author_identity": f"AL-{pair_id}",
                        "right_author_identity": f"AR-{pair_id}",
                        "reviewer_provenance": {"reviewer_identity": reviewer,
                                                "reviewer_kind": "AI", "model_revision": "m1",
                                                "prompt_digest": digest_json({"r": reviewer, "p": pair_id})}},
        reviews_meta=_seats(cid))


def _formulaic_adjudication(pair_id, left, right, verdict, exc_id):
    cid = f"form-a-{pair_id}"
    return asm.assemble_gold_record(
        case_id=cid, source_group_id=f"sg-{pair_id}",
        source_evidence_digest=digest_json({"pair": pair_id, "adj": True}),
        dataset_manifest_digest=DMD,
        gold_fields={"final_verdict": verdict, "necessary_grammar_exception_id": exc_id},
        payload_fields={"module": "formulaic", "record_role": "adjudication", "family_id": FAM,
                        "case_origin": "NATURAL", "pair_id": pair_id, "left_id": left,
                        "right_id": right, "adjudicator_identity": None,
                        "adjudication_evidence_digest": None},
        reviews_meta=_seats(cid))


def _formulaic_candidate_audit(pair_id, left, right, selected, gold_formulaic):
    cid = f"form-c-{pair_id}"
    return asm.assemble_gold_record(
        case_id=cid, source_group_id=f"sg-{pair_id}",
        source_evidence_digest=digest_json({"pair": pair_id, "cand": True}),
        dataset_manifest_digest=DMD, gold_fields={"gold_formulaic": gold_formulaic},
        payload_fields={"module": "formulaic", "record_role": "candidate_audit", "family_id": FAM,
                        "case_origin": "NATURAL", "pair_id": pair_id, "left_id": left,
                        "right_id": right, "candidate_selected": selected,
                        "audit_scope": "RANDOM_RECALL_AUDIT"},
        reviews_meta=_seats(cid))


def build_formulaic_minibatch() -> dict[str, Any]:
    """formulaic 六角色最小内部自洽批：judgment/adjudication/candidate_audit + 三注册表。

    仅证结构门（evidence bound / shape valid / manifest+rubric+exception valid /
    adjudication_records_valid）可过；计数门（>=300 pair 等）由 R3-run 批量满足，不在此。
    """
    specs = [("FORMULAIC", None, True), ("FORMULAIC", None, True),
             ("NOT_FORMULAIC", None, False), ("NECESSARY_GRAMMAR", "NG-1", False)]
    judgments, adjudications, candidate_audit = [], [], []
    reviewed_ids, cand_ids = [], []
    for i, (verdict, exc_id, is_formulaic) in enumerate(specs):
        left, right = f"L{i}", f"R{i}"
        pid = canonical_pair_id(left, right)
        reviewed_ids.append(pid)
        axes = _FORMULAIC_AXES[verdict]
        assert verdict_from_axes(axes, exc_id) == verdict  # 自洽守卫
        for reviewer in ("R1", "R2"):
            judgments.append(_formulaic_judgment(pid, left, right, reviewer, verdict, axes, exc_id))
        adjudications.append(_formulaic_adjudication(pid, left, right, verdict, exc_id))
        candidate_audit.append(_formulaic_candidate_audit(pid, left, right, is_formulaic, is_formulaic))
        cand_ids.append(pid)
    reviewed_sorted = sorted(reviewed_ids)
    cand_sorted = sorted(cand_ids)
    candidate_manifest = {
        "schema_version": "eval-spine-formulaic-candidate-audit-manifest-v1",
        "status": "SEALED", "registered_before_miner_run": True,
        "batch_id": "CORE-FIX-BATCH", "miner_run_id": "CORE-MINER-1",
        "custodian_identity": "DATA-CUSTODIAN", "registry_manifest_digest": "7" * 64,
        "sampling_algorithm": "PREREGISTERED_STRATIFIED_RANDOM_SAMPLE_V1",
        "population_pair_ids_digest": digest_json(reviewed_sorted),
        "sampled_pair_ids_digest": digest_json(cand_sorted),
        "sample_count": len(candidate_audit),
        "randomization_seed_commitment": "9" * 64,
        "candidate_miner_blinded_to_gold": True,
        "gold_attached_after_candidate_run": True, "manifest_digest": ""}
    unsigned = {k: v for k, v in candidate_manifest.items() if k != "manifest_digest"}
    candidate_manifest["manifest_digest"] = digest_json(unsigned)
    rubric = {"schema_version": "eval-spine-formulaic-rubric-freeze-v1", "status": "FROZEN",
              "frozen_before_qualification": True, "rubric_version": "v1",
              "batch_id": "CORE-FIX-BATCH", "rubric_content_digest": "6" * 64,
              "registry_manifest_digest": "7" * 64, "custodian_identity": "DATA-CUSTODIAN",
              "frozen_at": "2026-07-18T00:00:00Z", "rubric_digest": ""}
    rubric["rubric_digest"] = digest_json({k: v for k, v in rubric.items() if k != "rubric_digest"})
    grammar_pairs = sorted(canonical_pair_id(f"L{i}", f"R{i}")
                           for i, (v, _e, _f) in enumerate(specs) if v == "NECESSARY_GRAMMAR")
    exception = {"exception_id": "NG-1", "registered_before_batch": True,
                 "batch_id": "CORE-FIX-BATCH", "approved_by": "PRODUCT-OWNER",
                 "product_definition_ref": "CP-PROFILE-V1",
                 "applicable_pair_ids_digest": digest_json(grammar_pairs),
                 "maximum_pair_count": 20, "registry_manifest_digest": "7" * 64,
                 "exception_digest": ""}
    exception["exception_digest"] = digest_json(
        {k: v for k, v in exception.items() if k != "exception_digest"})
    return {"judgments": judgments, "adjudications": adjudications,
            "candidate_audit": candidate_audit, "candidate_manifest": candidate_manifest,
            "rubric_manifest": rubric, "necessary_grammar_exceptions": [exception]}


# ---------------------------------------------------------------- §四.3 真实 core 路径
# 上面的 GOLD_CHANNELS 记录是**金标（gold-only）**，用于 custody 复算/validate 记录级门。
# 但 measurement_qualification.v2 的模块门（calibration.qualify_*）是 M0-run 语义：需要
# 每条记录同时带 predicted_*（被测评测器输出）才能算指标。§四.3 要求「九模块测试实际调用
# 各模块生产 core，而非只走通用 validate」——本节构造带 gold+predicted 的最小 eval 记录
# （predicted=gold，平凡正确），逐条经 assemble_gold_record 装配（仍是验证器合规记录），
# 供测试直接喂 qualify_reference_extraction / qualify_entailment / … 等真 core。
# 计数门（sample>=300 等）在小批必 False（属允许的规模下限失败）；本节只证结构/证据门可过、
# 且缺字段/未调 core 时会失败（防「通用 envelope 假绿」）。


def _chain_manifest(case_id: str) -> dict[str, Any]:
    """构造一条通过 calibration.verify_chain_manifest 的合法端到端链清单。"""
    roles = cal.CHAIN_ROLES
    objs = {role: digest_json({"chain": case_id, "role": role}) for role in roles}
    links = [{"from_role": left, "to_role": right,
              "from_digest": objs[left], "to_digest": objs[right]}
             for left, right in zip(roles, roles[1:])]
    manifest = {"schema_version": "eval-spine-e2e-chain-manifest-v1",
                "object_digests": objs, "links": links, "chain_digest": ""}
    manifest["chain_digest"] = digest_json(
        {k: v for k, v in manifest.items() if k != "chain_digest"})
    return manifest


def _eval(case_id: str, module: str, role: str, gold_fields: dict,
          predicted_payload: dict, *, source_group: str,
          case_origin: str = "CHALLENGE") -> dict[str, Any]:
    payload = {"module": module, "record_role": role, "family_id": FAM,
               "case_origin": case_origin}
    payload.update(predicted_payload)
    return asm.assemble_gold_record(
        case_id=case_id, source_group_id=source_group,
        source_evidence_digest=digest_json({"src": source_group, "cid": case_id}),
        dataset_manifest_digest=DMD, gold_fields=gold_fields, payload_fields=payload,
        reviews_meta=_seats(case_id))


def _index(records: list[dict]) -> dict[str, Any]:
    return qd.build_qualification_record_index(records, dataset_manifest_digest=DMD)


def build_core_eval_records() -> dict[str, Any]:
    """九模块（除 formulaic 见 build_formulaic_minibatch）最小 eval 记录 + 各自 index。

    返回按测试消费口径分组；每组记录带 gold+predicted，predicted=gold（平凡正确），
    经 assemble_gold_record 装配，可直接喂对应生产 core。缺字段/篡改由测试负例覆盖。
    """
    out: dict[str, Any] = {}

    # reference_extraction —— detection(base) + 属性正确性；matched 行需 gold/predicted attributes
    ref = [
        _eval(f"ev-ref-p{i}", "reference_extraction", "qualification_case",
              {"gold_present": True, "gold_risk": "HIGH", "gold_attributes": dict(_ATTRS)},
              {"predicted_present": True, "predicted_risk": "HIGH",
               "predicted_attributes": dict(_ATTRS), "field_type": "PERFORMANCE_CLAIM"},
              source_group=f"sg-ref-p{i}")
        for i in range(2)] + [
        _eval("ev-ref-n0", "reference_extraction", "qualification_case",
              {"gold_present": False, "gold_risk": "LOW", "gold_attributes": dict(_ATTRS)},
              {"predicted_present": False, "predicted_risk": "LOW",
               "predicted_attributes": dict(_ATTRS), "field_type": "GENERIC"},
              source_group="sg-ref-n0", case_origin="NATURAL")]
    out["reference_extraction"] = {"records": ref, "index": _index(ref)}

    # claim_atomization —— detection(base) + 原子划分；predicted 行需 gold/predicted partition
    atom = [
        _eval(f"ev-atom-p{i}", "claim_atomization", "qualification_case",
              {"gold_present": True, "gold_risk": "HIGH",
               "gold_atom_partition": [["a1", "a2"], ["a3"]]},
              {"predicted_present": True, "predicted_risk": "HIGH",
               "predicted_atom_partition": [["a1", "a2"], ["a3"]], "field_type": "COMPOUND"},
              source_group=f"sg-atom-p{i}")
        for i in range(2)] + [
        _eval("ev-atom-n0", "claim_atomization", "qualification_case",
              {"gold_present": False, "gold_risk": "LOW",
               "gold_atom_partition": [["b1"]]},
              {"predicted_present": False, "predicted_risk": "LOW",
               "predicted_atom_partition": [["b1"]], "field_type": "GENERIC"},
              source_group="sg-atom-n0", case_origin="NATURAL")]
    out["claim_atomization"] = {"records": atom, "index": _index(atom)}

    # risk_classification
    risk = [
        _eval("ev-risk-h0", "risk_classification", "qualification_case",
              {"gold_risk": "HIGH"},
              {"predicted_risk": "HIGH"}, source_group="sg-risk-h0"),
        _eval("ev-risk-l0", "risk_classification", "qualification_case",
              {"gold_risk": "LOW"},
              {"predicted_risk": "LOW"}, source_group="sg-risk-l0",
              case_origin="NATURAL")]
    out["risk_classification"] = {"records": risk, "index": _index(risk)}

    # entailment —— 需 predicted_label/abstain/action
    ent = [
        _eval("ev-ent-c0", "entailment", "qualification_case",
              {"gold_label": "CONTRADICTED", "gold_risk": "HIGH"},
              {"predicted_label": "CONTRADICTED", "predicted_risk": "HIGH",
               "abstain": False, "action": "HARD_VETO"}, source_group="sg-ent-c0"),
        _eval("ev-ent-s0", "entailment", "qualification_case",
              {"gold_label": "SUPPORTED", "gold_risk": "LOW"},
              {"predicted_label": "SUPPORTED", "predicted_risk": "LOW",
               "abstain": False, "action": "ALLOW"}, source_group="sg-ent-s0",
              case_origin="NATURAL")]
    out["entailment"] = {"records": ent, "index": _index(ent)}

    # fact_chain (qualify_end_to_end) —— 需 gold_safe_to_clear/final_action/chain_manifest
    fc = [
        _eval("ev-fc-h0", "fact_chain", "qualification_case",
              {"gold_risk": "HIGH", "gold_safe_to_clear": False},
              {"predicted_risk": "HIGH", "final_action": "HARD_VETO",
               "chain_manifest": _chain_manifest("ev-fc-h0")}, source_group="sg-fc-h0"),
        _eval("ev-fc-n0", "fact_chain", "qualification_case",
              {"gold_risk": "LOW", "gold_safe_to_clear": True},
              {"predicted_risk": "LOW", "final_action": "ALLOW",
               "chain_manifest": _chain_manifest("ev-fc-n0")}, source_group="sg-fc-n0",
              case_origin="NATURAL")]
    out["fact_chain"] = {"records": fc, "index": _index(fc)}

    # disclosure + omission —— 联合 core，共享一个 index（须含两侧记录）
    disclosure = [
        _eval(f"ev-disc-{ot[:6]}", "disclosure", "disclosure_case",
              {"gold_violation": True},
              {"predicted_hard": True, "obligation_type": ot},
              source_group=f"sg-disc-{ot[:6]}")
        for ot in ("SYNTHETIC_IDENTITY_DISCLOSURE",
                   "PROHIBITED_REAL_IDENTITY_IMPERSONATION",
                   "EXPLICIT_AUTHORIZATION_BOUNDARY", "PRIVACY_REDACTION_OR_BLOCK")]
    omission = [
        _eval("ev-omis-m0", "omission", "omission_case",
              {"gold_misleading": True, "gold_risk": "HIGH"},
              {"predicted_flagged": True, "predicted_risk": "HIGH"},
              source_group="sg-omis-m0"),
        _eval("ev-omis-c0", "omission", "omission_case",
              {"gold_misleading": False, "gold_risk": "LOW"},
              {"predicted_flagged": False, "predicted_risk": "LOW"},
              source_group="sg-omis-c0", case_origin="NATURAL")]
    out["disclosure_and_omission"] = {
        "disclosure": disclosure, "omission": omission,
        "index": _index(disclosure + omission)}

    # review_calibration —— 复用 gold 通道的 1 item × 2 reviewer judgment
    review = [r for r in build_core_gold_records()
              if r.get("module") == "review_calibration"]
    out["review_calibration"] = {"judgments": review, "index": _index(review)}
    return out
