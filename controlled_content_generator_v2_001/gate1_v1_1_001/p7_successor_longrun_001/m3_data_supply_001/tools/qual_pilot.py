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
import qual_review_formulaic as RF      # noqa: E402  §四.3/§四.4 真 review+formulaic 子管线
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
        df = GD.field_disputes(a[cid], b[cid])
        if df:
            c = faces[cid]
            disputes.append({"case_id": cid, "disputed_fields": df,
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


# ---- review + formulaic 真实子管线（§四.3/§四.4；取代确定性占位）----
# 内容素材取自真源 base/variant（真实可评审内容 / 真实可比对内容对）；标签由真双席（A=Codex/
# B=Opus）独立产出，分歧走既有仲裁路径。verdict/axes 由真席标注决定，绝不预置。

def _mk_cached_call(carrier: str, subdir: str, count: int):
    """seat 调用适配器：绑定真 L.attempt_call + 密封 registry；按 stem 落缓存，重跑不重复付费。"""
    d = PILOT_SEAL / subdir
    d.mkdir(parents=True, exist_ok=True)

    def call(prompt, ok, stem):
        cache = d / f"{stem}.rows.json"
        if cache.is_file():
            rows = json.loads(cache.read_text(encoding="utf-8"))
            if ok(rows):
                print(f"[pilot] {subdir}/{stem}: reused cached")
                return rows
        rows = L.attempt_call(prompt, ok, d, stem, PILOT_SEAL / "REGISTRY.jsonl",
                              {"kind": f"PILOT_{subdir.upper()}", "seat": stem.rsplit("_", 1)[-1],
                               "batch": stem, "visible_material_count": count,
                               "retention": "标签明文留存 pilot 保全区"}, carrier=carrier)
        if rows is not None:
            cache.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        return rows
    return call


def _build_review_items(bases: list[dict]) -> list[dict]:
    """真实可评审内容单元（每族 1，取真源 base 内容）。author_identity ≠ 审核席（role_collision_absent）。"""
    return [{"item_id": f"PILOT-REV-{b['case_id']}", "family_id": b["family_id"],
             "source_group_id": f"pilot-rev-{b['source_group_id']}",
             "author_identity": f"PILOT_GEN_AUTHOR::{b['case_id']}",
             "content": b["claim_text"], "claim_boundary": b["claim_boundary"],
             "authorization_scope": b["authorization_scope"],
             "source_summary_a": b["source_summary_a"], "source_summary_b": b["source_summary_b"]}
            for b in bases]


def _mkpair(ref: str, lv: dict, rv: dict, sg: str) -> dict:
    return {"pair_ref": ref, "left_id": lv["case_id"], "right_id": rv["case_id"],
            "family_id": lv["family_id"], "source_group_id": sg,
            "left_content": lv["claim_text"], "right_content": rv["claim_text"],
            "left_author_identity": f"PILOT_AUTHOR_L::{lv['case_id']}",
            "right_author_identity": f"PILOT_AUTHOR_R::{rv['case_id']}",
            "necessary_grammar_exception_id": None}


def _build_formulaic_pairs(variants: list[dict]) -> list[dict]:
    """真实可比对内容对：同 source_group 变体成 1 对（结构相关），其余跨 base 变体两两配。"""
    by_sg: dict[str, list[dict]] = {}
    for v in sorted(variants, key=lambda v: v["case_id"]):
        by_sg.setdefault(v["source_group_id"], []).append(v)
    pairs, idx = [], 0
    for sg in sorted(sg for sg, vs in by_sg.items() if len(vs) >= 2):
        vs = by_sg[sg]
        pairs.append(_mkpair(f"PILOT-P{idx}", vs[0], vs[1], sg))
        idx += 1
    singles = [vs[0] for sg, vs in sorted(by_sg.items()) if len(vs) == 1]
    for i in range(0, len(singles) - 1, 2):
        pairs.append(_mkpair(f"PILOT-P{idx}", singles[i], singles[i + 1], f"pilot-fpair-{idx}"))
        idx += 1
    return pairs


def _run_review(items: list[dict], dmd: str) -> dict:
    """真双席 review 标注 → assemble → derive + spine 一致门（§四.3）。"""
    tmpl = L.load_template(ANNEXC, "qual_review_labeler")
    pd = digest_json({"tmpl": "qual_review_labeler", "sha": L.sha_text(tmpl)})
    dec_a = RF.label_review_seat(items, "A", template=tmpl,
                                 call=_mk_cached_call("codex", "review", len(items)))
    dec_b = RF.label_review_seat(items, "B", template=tmpl,
                                 call=_mk_cached_call("claude", "review", len(items)))
    units = RF.assemble_review_units(items, dec_a, dec_b, prompt_digest_a=pd, prompt_digest_b=pd)
    out = RF.review_agreement_report(units, dataset_manifest_digest=dmd,
                                     seat_provenance_for=lambda _c: QR._base_seat_provenance(pd))
    out["units"] = units
    return out


def _run_formulaic(pairs: list[dict], dmd: str) -> dict:
    """真双席逐轴 formulaic 标注 → verdict 分歧仲裁 → assemble → derive + spine 一致门（§四.4）。"""
    tmpl = L.load_template(ANNEXC, "qual_formulaic_axis_labeler")
    adj_tmpl = L.load_template(ANNEXC, "qual_formulaic_axis_adjudicator")
    pd = digest_json({"tmpl": "qual_formulaic_axis_labeler", "sha": L.sha_text(tmpl)})
    axes_a = RF.label_formulaic_seat(pairs, "A", template=tmpl,
                                     call=_mk_cached_call("codex", "formaxis", len(pairs)))
    axes_b = RF.label_formulaic_seat(pairs, "B", template=tmpl,
                                     call=_mk_cached_call("claude", "formaxis", len(pairs)))
    need = RF.pairs_needing_adjudication(pairs, axes_a, axes_b)
    adj_axes = RF.adjudicate_formulaic_axes(
        need, axes_a, axes_b, template=adj_tmpl,
        call=_mk_cached_call("claude", "formaxis_adj", len(need)))
    units = RF.assemble_formulaic_units(pairs, axes_a, axes_b, adj_axes,
                                        prompt_digest_a=pd, prompt_digest_b=pd)
    out = RF.formulaic_agreement_report(units, dataset_manifest_digest=dmd,
                                        seat_provenance_for=lambda _c: QR._base_seat_provenance(pd),
                                        batch_id="PILOT")
    out["adjudicated_pairs"] = len(need)
    out["units"] = units
    return out


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
    disputes_before = sum(1 for cid in set(a) & set(b) if GD.field_disputes(a[cid], b[cid]))
    adj = _adjudicate(face_by_id, a, b)
    print(f"[pilot] labeled both seats: {len(set(a) & set(b))}; disputes: {disputes_before}; "
          f"adjudicated: {len(adj)}")

    # resolve —— §四.1 逐字段：结构规范化后一致采一致值，分歧字段只采该字段仲裁值。
    resolutions, unresolved, adjudicated_faces = {}, [], 0
    for f in faces:
        cid = f["case_id"]
        ra, rb = a.get(cid), b.get(cid)
        if not ra or not rb:
            unresolved.append(cid)
            continue
        try:
            rlabel, adj_fields = GD.resolve_label_fields(ra, rb, adj.get(cid), where=cid)
        except GD.DerivationError:
            unresolved.append(cid)
            continue
        resolutions[cid] = {"label": rlabel, "adjudicated_fields": adj_fields}
        if adj_fields:
            adjudicated_faces += 1
    if unresolved:
        raise SystemExit(f"pilot 未决 {len(unresolved)} 条")

    # derive
    dmd = digest_json({"pilot": "A", "faces_sha256": faces_sha})
    labeler_pd = digest_json({"tmpl": "qual_rich_labeler",
                              "sha": L.sha_text(L.load_template(ANNEXC, "qual_rich_labeler"))})
    adj_pd = digest_json({"tmpl": "qual_rich_adjudicator",
                          "sha": L.sha_text(L.load_template(ANNEXC, "qual_rich_adjudicator"))})
    base_sp = QR._base_seat_provenance(labeler_pd)
    adj_sp = QR._adj_seat_provenance(adj_pd)

    der = GD.derive_perclaim_records(faces, resolutions, dataset_manifest_digest=dmd,
                                     base_seat_provenance=base_sp, adj_seat_provenance=adj_sp)
    records = list(der["records"])
    # §四.3/§四.4 真 review + formulaic 子管线（真双席标注 → assemble → derive；取代占位）
    review_items = _build_review_items(bases)
    formulaic_pairs = _build_formulaic_pairs(variants)
    rev = _run_review(review_items, dmd)
    records += rev["records"]
    form = _run_formulaic(formulaic_pairs, dmd)
    for k in ("judgments", "adjudications", "candidate_audit"):
        records += form["derived"][k]
    print(f"[pilot] real review units: {len(rev['units'])}; formulaic pairs: {len(form['units'])} "
          f"(adjudicated {form['adjudicated_pairs']})")
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
    # §四.6：cluster_power:* 与规模/类下限同属 scale 失败（小批 raw/cluster 必不达 300/59 等下限），
    # 不算 pipeline 结构缺陷。non_scale_failures 只收「非规模」失败（覆盖/治理/家族/生成链）。
    non_scale_failures = [k for k in readiness["failing_keys"]
                          if not (k in count_keys or k.startswith("cluster_power:"))]

    # §四.5 pilot_pass 收口：pipeline 端到端结构正确性（规模/类下限之外全绿）。逐条披露判据。
    kinds_present = sorted({v["challenge_kind"] for v in variants})
    ab_complete = (len(set(a) & set(b)) == len(faces)) and not unresolved
    nine_modules_covered = all(c["present"]
                               for c in readiness["module_gold_field_coverage"].values())
    review_real = (len(rev["units"]) > 0
                   and all(len(u["judgments"]) == 2 for u in rev["units"]))
    # formulaic 真实性：每 pair 两条 per-reviewer judgment 且各带自身 verdict（≠ 旧单 verdict 占位）
    formulaic_real = (len(form["units"]) > 0
                      and all(len(u["judgments"]) == 2 for u in form["units"])
                      and all("verdict" in j for u in form["units"] for j in u["judgments"]))
    governance_ok = all(readiness["governance"].values())
    pilot_pass_conditions = {
        "core_validation_passed": pc["custody_binding"]["core_validation_passed"],
        "generation_chain_resolves": gen_ok,
        "no_non_scale_failures": not non_scale_failures,
        "six_challenge_kinds": len(kinds_present) == 6,
        "ab_seats_complete_and_resolved": ab_complete,
        "nine_modules_covered": nine_modules_covered,
        "review_subpipeline_real": review_real,
        "formulaic_subpipeline_real": formulaic_real,
        "governance_flags_all_true": governance_ok,
    }
    pilot_pass = all(pilot_pass_conditions.values())

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
        # §四.6 双计数双披露：raw case N（覆盖门）+ distinct source-group cluster N（CI 功效门）
        "counts_recomputed": pc["counts"],
        "cluster_counts_recomputed": pc["cluster_counts"],
        "module_gold_field_coverage_present": {
            m: c["present"] for m, c in readiness["module_gold_field_coverage"].items()},
        "families_present": pc["family_coverage"],
        "generation_chain_resolves": gen_ok,
        "generation_errors": res.get("errors", []),
        "readiness_verdict": readiness["verdict"],
        "readiness_failing_keys": readiness["failing_keys"],
        "non_scale_failures": non_scale_failures,
        # §四.3/§四.4 真子管线报表（既有 spine 一致门指标；结构门 pilot 查，率阈达标属正式规模）
        "review_subpipeline": {"items": len(rev["units"]), "report": rev["report"]},
        "formulaic_subpipeline": {"pairs": len(form["units"]),
                                  "adjudicated_pairs": form["adjudicated_pairs"],
                                  "report": form["report"]},
        "pilot_pass_conditions": pilot_pass_conditions,
        "pilot_pass": pilot_pass,
        "seats": "A=Codex-GPT(gpt-5.6-sol) / B=Opus-4.8；仲裁=隔离 Opus 会话",
        "review_formulaic_note": "§四.3/§四.4：review + formulaic 均为真双席跨模型标注（非占位）——"
        "review 每 item 两独立 decision；formulaic 每 pair 双席逐 6 轴→verdict，分歧走隔离仲裁席；"
        "verdict/axes 由真席决定，绝不预置。规模/率阈达标属全量 R3-run。",
        "sealed_discipline": "faces/labels 明文只落 sealed_custody_001/pilot_A/（gitignore）；本回执零明文",
        "cost": L.registry_cost(PILOT_SEAL / "REGISTRY.jsonl"),
    }
    (PILOT_QUAL / "PILOT_RECEIPT.v1.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in (
        "pilot_pass", "pilot_pass_conditions", "faces_total", "challenge_kinds_present",
        "labeled_both_seats", "cross_model_disputes", "adjudicated", "core_validation_passed",
        "generation_chain_resolves", "readiness_verdict", "non_scale_failures",
        "counts_recomputed")}, ensure_ascii=False, indent=1))
    return 0 if receipt["pilot_pass"] else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.parse_args()
    sys.exit(run_pilot())
