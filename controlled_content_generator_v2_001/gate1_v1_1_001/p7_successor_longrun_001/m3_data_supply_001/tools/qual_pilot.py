#!/usr/bin/env python3
"""§六 R3-run 真实小批 pilot：真源→构造→双盲富标注→仲裁→assemble→九模块 core→generation→
custody 复算→readiness 预检。证「§四.1/§四.2 富标签链」端到端可跑（席A=Codex/席B=Claude/仲裁隔离）。

密封纪律：faces/labels 明文只落 sealed_custody_001/pilot_A/（gitignore）；本脚本 stdout 与 pilot
回执只吐**数量/摘要/verdict**，编排会话零接触明文。回执落 gold/qual/pilot/（可提交证据）。

范围（bounded）：6 kind 各≥1；base0 带 2 变体（同 source_group，证 raw↑ 而有效 N 不变）；review
1 item×2 judgment；formulaic 最小三元（覆盖用；真 formulaic/review 建标属全量 R3-run）。readiness
预检允许失败仅规模/类下限（小批必不达 300 等下限）。
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
P7 = M3DS.parents[0]
GT = M3DS / "gold/tools"
sys.path.insert(0, str(GT))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
import labeling_lib as L                # noqa: E402
import qual_runner as QR                # noqa: E402
import qual_gold_derivation as GD       # noqa: E402
import qual_generation as GEN           # noqa: E402
import qual_custody_recompute as CUS    # noqa: E402
import pre_m0_readiness as PRM          # noqa: E402
from spine.canonical import digest_json  # noqa: E402

ANNEXC = M3DS / "annotation/annotation_protocol_annexC_qual.v1.json"
SEAL = P7 / "sealed_custody_001"
PILOT_SEAL = SEAL / "pilot_A"
PILOT_QUAL = M3DS / "gold/qual/pilot"
FAMS = ("F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
        "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
        "F5_ENTERPRISE_LONG_TERM_TRUST")
KINDS = ("CONTRADICTION_INJECT", "RISK_ELEVATE", "EVIDENCE_INSUFFICIENT",
         "BOUNDARY_OMIT", "OMISSION_MISLEAD", "LEGAL_NEGATIVE_CONTROL")


def now():
    return datetime.now(timezone.utc).isoformat()


def _pick_real_bases() -> list[dict]:
    """从真实抽样框取 5 个自然 claim（每族 1，确定性首个），作为构造 base（真源）。"""
    cases = QR._cases_for_set("A")
    by_fam: dict[str, dict] = {}
    for c in sorted(cases, key=lambda c: c["case_id"]):
        by_fam.setdefault(c["family_id"], c)
    return [by_fam[f] for f in FAMS if f in by_fam]


def _construct_variants(bases: list[dict]) -> list[dict]:
    """真构造席（Claude）按 annexC qual_variant_constructor 从真源 base 造 6 变体（6 kind 各 1；
    base0 带 2 变体证同 source_group）。"""
    tmpl = L.load_template(ANNEXC, "qual_variant_constructor")
    # base0 承载 2 kind（CONTRADICTION_INJECT + RISK_ELEVATE），其余 base 各 1 kind
    plan = [(0, "CONTRADICTION_INJECT"), (0, "RISK_ELEVATE"),
            (1, "EVIDENCE_INSUFFICIENT"), (2, "BOUNDARY_OMIT"),
            (3, "OMISSION_MISLEAD"), (4, "LEGAL_NEGATIVE_CONTROL")]
    tasks = []
    for bi, kind in plan:
        b = bases[bi % len(bases)]
        tasks.append({"variant_id": f"PILOT-V-{b['case_id']}-{kind[:4]}",
                      "base_case_id": b["case_id"], "variant_kind": kind,
                      "base_claim_text": b["claim_text"], "claim_boundary": b["claim_boundary"],
                      "authorization_scope": b["authorization_scope"], "slot_facts": b["slot_facts"],
                      "source_summary_a": b["source_summary_a"], "source_summary_b": b["source_summary_b"],
                      "family_id": b["family_id"]})
    expected = {t["variant_id"] for t in tasks}

    def ok(rows):
        return (isinstance(rows, list)
                and {r.get("variant_id") for r in rows if isinstance(r, dict)} == expected
                and all(r.get("variant_claim_text") for r in rows))

    prompt = tmpl.replace("{batch_json}", json.dumps(tasks, ensure_ascii=False, indent=1))
    PILOT_SEAL.mkdir(parents=True, exist_ok=True)
    rows = L.attempt_call(prompt, ok, PILOT_SEAL / "construct", "cons_000",
                          PILOT_SEAL / "REGISTRY.jsonl",
                          {"kind": "PILOT_VARIANT_CONSTRUCT", "batch": "cons_000",
                           "visible_material_count": len(expected),
                           "retention": "明文留存 pilot 保全区"}, carrier="claude")
    if rows is None:
        raise SystemExit("pilot 构造失败（constructor 未产合格批）")
    task_by_id = {t["variant_id"]: t for t in tasks}
    variants = []
    for r in rows:
        t = task_by_id[r["variant_id"]]
        variants.append({"case_id": r["variant_id"], "case_kind": "CHALLENGE_VARIANT",
                         "challenge_kind": QR.normalize_kind(t["variant_kind"]),
                         "source_group_id": t["base_case_id"], "family_id": t["family_id"],
                         "claim_text": r["variant_claim_text"], "claim_boundary": t["claim_boundary"],
                         "authorization_scope": t["authorization_scope"], "slot_facts": t["slot_facts"],
                         "source_summary_a": t["source_summary_a"], "source_summary_b": t["source_summary_b"],
                         "item_title": ""})
    return variants


def _slim(face: dict) -> dict:
    return {k: face.get(k, "") for k in ("case_id", "claim_text", "claim_boundary",
                                         "authorization_scope", "slot_facts",
                                         "source_summary_a", "source_summary_b", "item_title")}


CHUNK = 4  # 小批（富标签输出大，分块更快更稳，逐块缓存断点续跑）


def _label_seat(faces: list[dict], seat: str) -> dict[str, dict]:
    out_dir = PILOT_SEAL / f"labels_{seat}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cached = out_dir / "labels.json"
    if cached.is_file():
        labels = json.loads(cached.read_text(encoding="utf-8"))
        if {f["case_id"] for f in faces}.issubset(set(labels)):
            print(f"[pilot] seat {seat}: reused cached labels ({len(labels)})")
            return labels
    carrier = "codex" if seat == "A" else "claude"
    tmpl = L.load_template(ANNEXC, "qual_rich_labeler")
    seat_label = "A(Codex-GPT)" if seat == "A" else "B(Opus-4.8)"
    labels: dict[str, dict] = {}
    chunks = [faces[i:i + CHUNK] for i in range(0, len(faces), CHUNK)]
    for ci, batch in enumerate(chunks):
        stem = f"fb_{ci:03d}"
        part_path = out_dir / f"{stem}.labels.json"
        if part_path.is_file():  # 逐块断点续跑
            for r in json.loads(part_path.read_text(encoding="utf-8")):
                labels[r["case_id"]] = r
            print(f"[pilot] seat {seat} chunk {stem}: reused")
            continue
        expected = {f["case_id"] for f in batch}

        def ok(rows):
            return QR._rich_rows_ok(rows, expected)

        prompt = tmpl.replace("{seat}", seat_label).replace(
            "{batch_json}", json.dumps([_slim(f) for f in batch], ensure_ascii=False, indent=1))
        rows = L.attempt_call(prompt, ok, out_dir, stem, PILOT_SEAL / "REGISTRY.jsonl",
                              {"kind": f"PILOT_LABEL_{seat}", "seat": seat, "batch": stem,
                               "visible_material_count": len(expected),
                               "retention": "标签明文留存 pilot 保全区"}, carrier=carrier)
        if rows is None:
            raise SystemExit(f"pilot 席{seat} 标注失败 chunk {stem}")
        part_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        for r in rows:
            labels[r["case_id"]] = r
        print(f"[pilot] seat {seat} chunk {stem}: OK ({len(rows)})")
    cached.write_text(json.dumps(labels, ensure_ascii=False, indent=1), encoding="utf-8")
    return labels


def _adjudicate(faces: dict[str, dict], a: dict, b: dict) -> dict[str, dict]:
    cached = PILOT_SEAL / "adjudication" / "adj.json"
    if cached.is_file():
        adj = json.loads(cached.read_text(encoding="utf-8"))
        print(f"[pilot] adjudication: reused cached ({len(adj)})")
        return adj
    disputes = []
    for cid in sorted(set(a) & set(b)):
        if QR._rich_key(a[cid]) != QR._rich_key(b[cid]):
            c = faces[cid]
            disputes.append({"case_id": cid,
                             **{k: c.get(k) for k in ("claim_text", "claim_boundary",
                                                      "authorization_scope", "slot_facts",
                                                      "source_summary_a", "source_summary_b")},
                             "label_jia": {k: a[cid].get(k) for k in QR._RICH_FIELDS},
                             "label_yi": {k: b[cid].get(k) for k in QR._RICH_FIELDS}})
    if not disputes:
        return {}
    tmpl = L.load_template(ANNEXC, "qual_rich_adjudicator")
    expected = {d["case_id"] for d in disputes}

    def ok(rows):
        return QR._rich_rows_ok(rows, expected)

    prompt = tmpl.replace("{batch_json}", json.dumps(disputes, ensure_ascii=False, indent=1))
    rows = L.attempt_call(prompt, ok, PILOT_SEAL / "adjudication", "adj_000",
                          PILOT_SEAL / "REGISTRY.jsonl",
                          {"kind": "PILOT_ADJUDICATE", "batch": "adj_000",
                           "visible_material_count": len(expected),
                           "retention": "明文留存 pilot 保全区"}, carrier="claude")
    if rows is None:
        raise SystemExit("pilot 仲裁失败")
    adj = {r["case_id"]: r for r in rows}
    (PILOT_SEAL / "adjudication").mkdir(parents=True, exist_ok=True)
    (PILOT_SEAL / "adjudication" / "adj.json").write_text(
        json.dumps(adj, ensure_ascii=False, indent=1), encoding="utf-8")
    return adj


# ---- review + formulaic 覆盖用最小单元（确定性；真 formulaic/review 建标属全量 R3-run）----
def _coverage_units():
    review_units = [{"item_id": "PILOT-I0", "family_id": FAMS[0],
                     "source_group_id": "pilot-rev-I0", "author_identity": "PILOT-AUTHOR",
                     "judgments": [{"reviewer_id": "PILOT-RV1", "decision": "APPROVE", "hard_veto": False},
                                   {"reviewer_id": "PILOT-RV2", "decision": "REJECT", "hard_veto": True}]}]
    AX = {"FORMULAIC": {"argument_spine": "SAME", "evidence_progression": "SAME",
                        "limitation_function": "DIFFERENT", "viewpoint_anchor": "SAME",
                        "closing_function": "DIFFERENT", "transformation_depth": "SURFACE_ONLY"},
          "NOT_FORMULAIC": {"argument_spine": "DIFFERENT", "evidence_progression": "DIFFERENT",
                            "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                            "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"},
          "NECESSARY_GRAMMAR": {"argument_spine": "NECESSARY_GRAMMAR", "evidence_progression": "DIFFERENT",
                                "limitation_function": "DIFFERENT", "viewpoint_anchor": "DIFFERENT",
                                "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"}}
    fu = [{"left_id": "PL0", "right_id": "PR0", "family_id": FAMS[0], "source_group_id": "pilot-p0",
           "verdict": "FORMULAIC", "axes": AX["FORMULAIC"], "necessary_grammar_exception_id": None,
           "is_formulaic": True, "left_author_identity": "PAL0", "right_author_identity": "PAR0",
           "reviewers": ["PFR1", "PFR2"]},
          {"left_id": "PL1", "right_id": "PR1", "family_id": FAMS[0], "source_group_id": "pilot-p1",
           "verdict": "NOT_FORMULAIC", "axes": AX["NOT_FORMULAIC"], "necessary_grammar_exception_id": None,
           "is_formulaic": False, "left_author_identity": "PAL1", "right_author_identity": "PAR1",
           "reviewers": ["PFR1", "PFR2"]},
          {"left_id": "PL2", "right_id": "PR2", "family_id": FAMS[0], "source_group_id": "pilot-p2",
           "verdict": "NECESSARY_GRAMMAR", "axes": AX["NECESSARY_GRAMMAR"],
           "necessary_grammar_exception_id": "NG-1", "is_formulaic": False,
           "left_author_identity": "PAL2", "right_author_identity": "PAR2", "reviewers": ["PFR1", "PFR2"]}]
    return review_units, fu


def run_pilot() -> int:
    QR.assert_sealed_ignored()  # pilot_A 在 sealed_custody_001 下，gitignore 已覆盖
    PILOT_SEAL.mkdir(parents=True, exist_ok=True)
    PILOT_QUAL.mkdir(parents=True, exist_ok=True)

    bases = _pick_real_bases()
    faces_path = PILOT_SEAL / "faces_frozen.json"
    if faces_path.is_file():  # 断点续跑：faces 已冻结则复用（构造不重跑）
        faces = json.loads(faces_path.read_text(encoding="utf-8"))
        variants = [f for f in faces if f.get("case_kind") == "CHALLENGE_VARIANT"]
        print(f"[pilot] reused frozen faces: {len(faces)} (variants {len(variants)})")
    else:
        print(f"[pilot] real bases: {len(bases)} (families {[b['family_id'] for b in bases]})")
        variants = _construct_variants(bases)
        print(f"[pilot] constructed variants: {len(variants)} "
              f"(kinds {sorted(set(v['challenge_kind'] for v in variants))})")
        faces = []
        for b in bases:
            faces.append({"case_id": b["case_id"], "case_kind": "NATURAL",
                          "source_group_id": b["source_group_id"], "family_id": b["family_id"],
                          "claim_text": b["claim_text"], "claim_boundary": b["claim_boundary"],
                          "authorization_scope": b["authorization_scope"], "slot_facts": b["slot_facts"],
                          "source_summary_a": b["source_summary_a"], "source_summary_b": b["source_summary_b"],
                          "item_title": b.get("item_title", "")})
        faces += variants
        faces_path.write_text(json.dumps(faces, ensure_ascii=False, indent=1), encoding="utf-8")
    faces_sha = digest_json(faces)
    print(f"[pilot] faces total: {len(faces)} (natural {len(faces) - len(variants)} + variant {len(variants)})")

    a = _label_seat(faces, "A")
    b = _label_seat(faces, "B")
    face_by_id = {f["case_id"]: f for f in faces}
    disputes_before = sum(1 for cid in set(a) & set(b) if QR._rich_key(a[cid]) != QR._rich_key(b[cid]))
    adj = _adjudicate(face_by_id, a, b)
    print(f"[pilot] labeled both seats: {len(set(a) & set(b))}; disputes: {disputes_before}; "
          f"adjudicated: {len(adj)}")

    # resolve
    resolved, adjudicated_ids, unresolved = {}, set(), []
    for f in faces:
        cid = f["case_id"]
        ra, rb = a.get(cid), b.get(cid)
        if not ra or not rb:
            unresolved.append(cid)
        elif QR._rich_key(ra) == QR._rich_key(rb):
            resolved[cid] = ra
        elif cid in adj:
            resolved[cid] = adj[cid]
            adjudicated_ids.add(cid)
        else:
            unresolved.append(cid)
    if unresolved:
        raise SystemExit(f"pilot 未决 {len(unresolved)} 条")

    # derive
    dmd = digest_json({"pilot": "A", "faces_sha256": faces_sha})
    labeler_pd = digest_json({"tmpl": "qual_rich_labeler",
                              "sha": L.sha_text(L.load_template(ANNEXC, "qual_rich_labeler"))})
    adj_pd = digest_json({"tmpl": "qual_rich_adjudicator",
                          "sha": L.sha_text(L.load_template(ANNEXC, "qual_rich_adjudicator"))})

    def sp_for(rec_cid):
        fc = rec_cid.split("::")[0]
        return QR._seat_provenance(fc, fc in adjudicated_ids, labeler_pd, adj_pd)

    der = GD.derive_perclaim_records(faces, resolved, dataset_manifest_digest=dmd,
                                     seat_provenance_for=sp_for)
    records = list(der["records"])
    review_units, formulaic_units = _coverage_units()
    records += GD.derive_review_records(review_units, dataset_manifest_digest=dmd,
                                        seat_provenance_for=sp_for)
    formu = GD.derive_formulaic_records(formulaic_units, dataset_manifest_digest=dmd,
                                        seat_provenance_for=sp_for, batch_id="PILOT")
    for k in ("judgments", "adjudications", "candidate_audit"):
        records += formu[k]
    (PILOT_SEAL / "gold_records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    gold_sha = digest_json(records)

    # generation chain
    generation_id = f"QUAL_A_GEN_PILOT_{faces_sha[:12]}"
    gen = GEN.build_generation(records, set_id="A", generation_id=generation_id,
                               dataset_manifest_digest=dmd,
                               faces_sha256=faces_sha, gold_sha256=gold_sha, qual_dir=PILOT_QUAL)
    res = GEN.resolve_active_generation(PILOT_QUAL, "A")
    gen_ok = res.get("errors", []) == []

    # custody recompute + readiness precheck
    pc = CUS.recompute_public_counts(
        records, set_id="A", active_generation_id=generation_id, dataset_manifest_digest=dmd,
        faces_sha256=faces_sha, gold_sha256=gold_sha,
        environmental_flags={k: True for k in CUS._ENV_FLAGS})
    readiness = PRM.evaluate_set_readiness("A", pc)
    count_keys = (set(PRM.COUNT_KEYS)
                  | {"deterministic_disclosure_obligation_types_required",
                     "known_r5_hard_veto_cases_and_registered_variants_recall"}
                  | set(PRM.M3_MANIFEST_KEYS))
    non_scale_failures = [k for k in readiness["failing_keys"] if k not in count_keys]

    receipt = {
        "schema_version": "p7-m3-qual-pilot-receipt-v1",
        "at": now(), "set": "A_PILOT", "generation_id": generation_id,
        "real_source_bases": len(bases),
        "constructed_variants": len(variants),
        "challenge_kinds_present": sorted({v["challenge_kind"] for v in variants}),
        "faces_total": len(faces),
        "same_source_group_demo": {
            "note": "base0 承载 2 变体，同 source_group → raw 变体计 2 而独立单位仍 1",
            "base0_source_group": bases[0]["case_id"],
            "variants_on_base0": sum(1 for v in variants
                                     if v["source_group_id"] == bases[0]["case_id"])},
        "labeled_both_seats": len(set(a) & set(b)),
        "cross_model_disputes": disputes_before, "adjudicated": len(adj),
        "gold_record_count": len(records),
        "core_validation_passed": pc["custody_binding"]["core_validation_passed"],
        "core_validation_errors": pc["custody_binding"]["core_validation_errors"][:10],
        "counts_recomputed": pc["counts"],
        "module_gold_field_coverage_present": {
            m: c["present"] for m, c in readiness["module_gold_field_coverage"].items()},
        "families_present": pc["family_coverage"],
        "generation_chain_resolves": gen_ok,
        "generation_errors": res.get("errors", []),
        "readiness_verdict": readiness["verdict"],
        "readiness_failing_keys": readiness["failing_keys"],
        "non_scale_failures": non_scale_failures,
        "pilot_pass": (pc["custody_binding"]["core_validation_passed"] and gen_ok
                       and not non_scale_failures
                       and len({v["challenge_kind"] for v in variants}) == 6),
        "seats": "A=Codex-GPT(gpt-5.6-sol) / B=Opus-4.8；仲裁=隔离 Opus 会话",
        "review_formulaic_note": "review 1item×2judgment + formulaic 三元为覆盖用最小单元（确定性）；"
        "真 review/formulaic 跨模型建标属全量 R3-run。6 kind 富标注为真跨模型双盲。",
        "sealed_discipline": "faces/labels 明文只落 sealed_custody_001/pilot_A/（gitignore）；本回执零明文",
        "cost": L.registry_cost(PILOT_SEAL / "REGISTRY.jsonl"),
    }
    (PILOT_QUAL / "PILOT_RECEIPT.v1.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in (
        "pilot_pass", "faces_total", "challenge_kinds_present", "labeled_both_seats",
        "cross_model_disputes", "adjudicated", "core_validation_passed",
        "generation_chain_resolves", "readiness_verdict", "non_scale_failures",
        "counts_recomputed")}, ensure_ascii=False, indent=1))
    return 0 if receipt["pilot_pass"] else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.parse_args()
    sys.exit(run_pilot())
