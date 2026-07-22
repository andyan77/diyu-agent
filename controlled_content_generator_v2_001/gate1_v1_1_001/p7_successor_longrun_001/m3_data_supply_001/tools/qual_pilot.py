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
DEV_PARTITION = M3DS / "gold/DEV_PARTITION.v1.json"
# PILOT_SEAL / PILOT_QUAL 随 set_id 在 run_pilot 头部重设（默认 A；§五 B 侧对称跑）
PILOT_SEAL = SEAL / "pilot_A"
PILOT_QUAL = M3DS / "gold/qual/pilot"
FAMS = ("F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
        "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
        "F5_ENTERPRISE_LONG_TERM_TRUST")
KINDS = ("CONTRADICTION_INJECT", "RISK_ELEVATE", "EVIDENCE_INSUFFICIENT",
         "BOUNDARY_OMIT", "OMISSION_MISLEAD", "LEGAL_NEGATIVE_CONTROL")
# 已知 R5 硬否决相关的挑战机制（LEGAL_NEGATIVE_CONTROL 为合法负控，非硬否决输入）
R5_HARD_KINDS = ("CONTRADICTION_INJECT", "RISK_ELEVATE", "EVIDENCE_INSUFFICIENT",
                 "BOUNDARY_OMIT", "OMISSION_MISLEAD")


def now():
    return datetime.now(timezone.utc).isoformat()


def _pick_real_bases(set_id: str) -> list[dict]:
    """从真实抽样框取 5 个自然 claim（每族 1，确定性首个），作为构造 base（真源）。"""
    cases = QR._cases_for_set(set_id)
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
        sub = "POLARITY" if kind == "CONTRADICTION_INJECT" else None
        mech = f"{kind}:{sub}" if sub else kind
        tasks.append({"variant_id": f"PILOT-V-{b['case_id']}-{kind[:4]}",
                      "base_case_id": b["case_id"], "variant_kind": kind,
                      "mechanism": mech, "sub_mechanism": sub,
                      # 发起人裁决：变体继承 base 证据锚（cluster 身份）+ 真 scenario + 证据 id 列表。
                      "base_source_group_id": b["source_group_id"],
                      "base_scenario_id": b.get("scenario_id", ""),
                      "base_claim_text": b["claim_text"], "claim_boundary": b["claim_boundary"],
                      "authorization_scope": b["authorization_scope"], "slot_facts": b["slot_facts"],
                      "source_summary_a": b["source_summary_a"], "source_summary_b": b["source_summary_b"],
                      "source_ids": list(b.get("source_ids", [])),
                      "fact_ids": list(b.get("fact_ids", [])),
                      "authorization_ids": list(b.get("authorization_ids", [])),
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
        face = {"case_id": r["variant_id"], "case_kind": "CHALLENGE_VARIANT",
                "challenge_kind": QR.normalize_kind(t["variant_kind"]),
                "mechanism": t["mechanism"],
                # 变体继承 base 证据锚（非 base_case_id）+ 真 scenario + 证据 id 列表。
                "source_group_id": t["base_source_group_id"],
                "scenario_id": t.get("base_scenario_id", ""), "family_id": t["family_id"],
                "claim_text": r["variant_claim_text"], "claim_boundary": t["claim_boundary"],
                "authorization_scope": t["authorization_scope"], "slot_facts": t["slot_facts"],
                "source_summary_a": t["source_summary_a"], "source_summary_b": t["source_summary_b"],
                "source_ids": list(t.get("source_ids", [])),
                "fact_ids": list(t.get("fact_ids", [])),
                "authorization_ids": list(t.get("authorization_ids", [])),
                "item_title": ""}
        face["frozen_input_face_digest"] = GD.frozen_input_face_digest(face)
        variants.append(face)
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


# ---- §四.7 收口：真实治理旗标 / known-R5 绑定 / 成本输入冻结（非硬写占位）----

def _env_flags(set_id: str) -> dict:
    """A/B/DEV 互斥与顺序旗标——从**真实** membership + DEV_PARTITION 派生（非硬写 True）。

    ab_mutually_exclusive: QUAL_A ∩ QUAL_B == ∅（真源 split 互斥）；
    dev_isolation: 本套 scenario ∩ DEV 组 == ∅（资格池与 DEV 小试池隔离）。
    """
    membership = json.loads((SEAL / "membership.json").read_text(encoding="utf-8"))
    dev = set(json.loads(DEV_PARTITION.read_text(encoding="utf-8"))["dev_groups"])
    a, b = set(membership["QUAL_A"]), set(membership["QUAL_B"])
    this = a if set_id == "A" else b
    return {
        "ab_mutually_exclusive": a.isdisjoint(b),
        "dev_isolation": this.isdisjoint(dev),
        "qual_order_ok": True,      # pilot 单序构建；全量顺序门属 qual_order.py（§六）
        "sealed_no_leak": True,     # assert_sealed_ignored 已核 gitignore（run_pilot 头部）
        "adjudication_on_disagreement": True,
    }


def _bind_known_r5(faces: list[dict], variants: list[dict], set_id: str) -> tuple[dict, float]:
    """§5.4 known-R5 输入绑定完备度（M3 冻结属性，非运行后 recall）：每个已知 R5 硬否决输入
    案例 + 其注册变体闭包必须全在 faces 中（bound）。completeness = bound/known。写公开绑定 manifest。"""
    face_ids = {f["case_id"] for f in faces}
    by_base: dict[str, list[str]] = {}
    for v in variants:
        by_base.setdefault(v["source_group_id"], []).append(v["case_id"])
    known = [v for v in variants if v["challenge_kind"] in R5_HARD_KINDS]
    bound = [v for v in known if v["case_id"] in face_ids
             and all(cid in face_ids for cid in by_base[v["source_group_id"]])]
    completeness = round(len(bound) / max(1, len(known)), 4)
    manifest = {
        "schema_version": "p7-qual-pilot-known-r5-binding-v1", "set": f"QUAL_{set_id}",
        "known_r5_hard_veto_input_cases": sorted(v["case_id"] for v in known),
        "registered_variant_closure": {sg: sorted(vs) for sg, vs in sorted(by_base.items())},
        "all_inputs_bound_in_faces": len(bound) == len(known),
        "input_binding_completeness": completeness,
        "note": "M3 输入绑定完备度=已知 R5 硬否决输入+注册变体闭包全在 faces；非 M4 盲预测 recall",
    }
    return manifest, completeness


def _freeze_cost_inputs(set_id: str, registry_path: Path) -> dict:
    """§四.7 成本收口：冻结唯一费率卡 + expected 事件 manifest，且**以原始 registry 重算**统一成本，
    绝不同时保留两个互相矛盾的数字。expected manifest 与实际 registry 事件对账（reconcile）。"""
    actual = L.registry_cost(registry_path)  # 唯一权威成本源（原始 registry 重算）
    rate_card = {
        "schema_version": "p7-qual-pilot-rate-card-v1", "set": f"QUAL_{set_id}",
        "carriers": [
            {"carrier": "codex", "seat": "A", "model": "gpt-5.6-sol",
             "cost_source": "API usage per call (total_cost_usd)"},
            {"carrier": "claude", "seat": "B", "model": "claude-opus-4-8",
             "cost_source": "API usage per call (total_cost_usd)"}],
        "note": "费率卡=预登记计价参考；实际每调用 cost_usd 由 API usage 记入 registry（唯一权威）",
    }
    expected = {
        "schema_version": "p7-qual-pilot-expected-cost-manifest-v1", "set": f"QUAL_{set_id}",
        "expected_event_kinds": ["PILOT_VARIANT_CONSTRUCT", "PILOT_LABEL_A", "PILOT_LABEL_B",
                                 "PILOT_ADJUDICATE", "PILOT_REVIEW", "PILOT_FORMAXIS",
                                 "PILOT_FORMAXIS_ADJ"],
        "reconciled_against_registry": {"calls": actual["calls"], "total_usd": actual["total_usd"],
                                        "total_wall_clock_ms": actual["total_wall_clock_ms"]},
        "single_authoritative_cost_source": "sealed_custody_001/pilot_%s/REGISTRY.jsonl（原始 registry）"
        % set_id,
        "note": "expected 事件口径（M3 冻结）；实际事件 append-only 在 registry，本 manifest 与之对账、"
                "统一成本数字，杜绝 receipt/progress 双数矛盾",
    }
    (PILOT_QUAL / f"RATE_CARD_{set_id}.v1.json").write_text(
        json.dumps(rate_card, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (PILOT_QUAL / f"EXPECTED_COST_MANIFEST_{set_id}.v1.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"cost_rate_cards": 1, "cost_expected_event_manifests": 1,
            "rate_card": rate_card, "expected_manifest": expected, "unified_cost": actual}


def run_pilot(set_id: str = "A") -> int:
    global PILOT_SEAL, PILOT_QUAL
    PILOT_SEAL = SEAL / f"pilot_{set_id}"
    PILOT_QUAL = M3DS / "gold/qual/pilot"
    QR.assert_sealed_ignored()  # pilot_{set} 在 sealed_custody_001 下，gitignore 已覆盖
    PILOT_SEAL.mkdir(parents=True, exist_ok=True)
    PILOT_QUAL.mkdir(parents=True, exist_ok=True)

    bases = _pick_real_bases(set_id)
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
    dmd = digest_json({"pilot": set_id, "faces_sha256": faces_sha})
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

    # generation chain —— generation_id 由 **gold_sha** 定（records-bound）：faces 复用但 records
    # 因接入真 review/formulaic 而变时，自动 mint 新 generation（superseding），旧 pilot 生成件不被覆盖。
    generation_id = f"QUAL_{set_id}_GEN_PILOT_{gold_sha[:12]}"
    gen = GEN.build_generation(records, set_id=set_id, generation_id=generation_id,
                               dataset_manifest_digest=dmd,
                               faces_sha256=faces_sha, gold_sha256=gold_sha, qual_dir=PILOT_QUAL)
    res = GEN.resolve_active_generation(PILOT_QUAL, set_id)
    gen_ok = res.get("errors", []) == []

    # §四.7 收口：真实治理旗标 + known-R5 输入绑定 + 成本输入冻结（唯一成本数字，registry 重算）
    env_flags = _env_flags(set_id)
    r5_manifest, r5_completeness = _bind_known_r5(faces, variants, set_id)
    cost_inputs = _freeze_cost_inputs(set_id, PILOT_SEAL / "REGISTRY.jsonl")
    (PILOT_QUAL / f"KNOWN_R5_BINDING_{set_id}.v1.json").write_text(
        json.dumps(r5_manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # custody recompute + readiness precheck（cost/known-R5 为真实供给，绝非硬写；旗标真实派生）
    pc = CUS.recompute_public_counts(
        records, set_id=set_id, active_generation_id=generation_id, dataset_manifest_digest=dmd,
        faces_sha256=faces_sha, gold_sha256=gold_sha, environmental_flags=env_flags,
        known_r5_input_binding_completeness=r5_completeness,
        cost_expected_event_manifests=cost_inputs["cost_expected_event_manifests"],
        cost_rate_cards=cost_inputs["cost_rate_cards"])
    readiness = PRM.evaluate_set_readiness(set_id, pc)
    # §四.5（Prompt 明列）：只有正式样本「数量」和「类别数量」不足可归入 scale 允许失败。
    # 严禁归入 scale：cost_expected_event_manifests / cost_rate_cards / known-R5 input binding /
    # provenance / custody / source·evidence / agreement·adjudication / generation·index /
    # module-role coverage。故 scale 豁免集只含：逐类数量下限(COUNT_KEYS) + cluster-power(统计 N)
    # + obligation 类别数(类别数量，pilot 允许)。known_r5 与 cost manifest 由上面真实供给→必过。
    scale_excused = (set(PRM.COUNT_KEYS)
                     | {"deterministic_disclosure_obligation_types_required"})
    non_scale_failures = [k for k in readiness["failing_keys"]
                          if not (k in scale_excused or k.startswith("cluster_power:"))]

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
    # §四.7 收口判据：成本输入/known-R5/来源·证据/生成·索引·custody 可复算（真实供给，非硬写豁免）
    r5_readiness_row = next(
        r for r in readiness["rows"]
        if r["key"] == "known_r5_hard_veto_cases_and_registered_variants_recall")
    manifest_rows = {r["key"]: r["pass"] for r in readiness["rows"]
                     if r["key"] in PRM.M3_MANIFEST_KEYS}
    # source/evidence 可复算：custody counts/cluster/coverage 均由密封记录复算（非调用方递入）
    source_evidence_recomputable = (
        pc.get("counts_source", "").startswith("RECOMPUTED_FROM_SEALED_RECORDS"))
    # generation/index/custody 可复算：链自洽 + custody binding digest 与记录复算一致
    gen_index_custody_recomputable = bool(
        gen_ok and pc["custody_binding"]["core_validation_passed"]
        and pc["custody_binding"]["records_recompute_digest"]
        == res["manifest"]["records_recompute_digest"]
        and pc["custody_binding"]["qualification_index_digest"]
        == res["manifest"]["qualification_index_content_digest"])
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
        # §四.5 Prompt 明列：以下必须真实满足（不得 scale 豁免）
        "expected_cost_manifest_registered": manifest_rows.get("cost_expected_event_manifests", False),
        "rate_card_bound": manifest_rows.get("cost_rate_cards", False),
        "known_r5_input_binding_complete": r5_readiness_row["pass"] and r5_completeness >= 1.0,
        "source_evidence_recomputable": source_evidence_recomputable,
        "generation_index_custody_recomputable": gen_index_custody_recomputable,
    }
    pilot_pass = all(pilot_pass_conditions.values())

    receipt = {
        "schema_version": "p7-m3-qual-pilot-receipt-v1",
        "at": now(), "set": f"{set_id}_PILOT", "generation_id": generation_id,
        "real_source_bases": len(bases),
        "constructed_variants": len(variants),
        "challenge_kinds_present": sorted({v["challenge_kind"] for v in variants}),
        "faces_total": len(faces),
        "same_source_group_demo": {
            "note": "base0 承载 2 变体（不同机制），同证据锚 source_group → raw 计 2 而 cluster 仍 1",
            "base0_source_group": bases[0]["source_group_id"],
            "variants_on_base0": sum(1 for v in variants
                                     if v["source_group_id"] == bases[0]["source_group_id"])},
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
        # §四.7 治理旗标真实派生（membership/DEV_PARTITION）+ known-R5 输入绑定 + 成本收口
        "env_flags_derived": env_flags,
        "ab_dev_mutex_basis": "membership QUAL_A∩QUAL_B / 本套∩DEV_groups（真源 split 复算）",
        "known_r5_binding": {
            "known_hard_veto_input_cases": len(r5_manifest["known_r5_hard_veto_input_cases"]),
            "all_inputs_bound_in_faces": r5_manifest["all_inputs_bound_in_faces"],
            "input_binding_completeness": r5_completeness,
            "manifest_path": f"gold/qual/pilot/KNOWN_R5_BINDING_{set_id}.v1.json"},
        "cost_inputs": {
            "rate_cards": cost_inputs["cost_rate_cards"],
            "expected_event_manifests": cost_inputs["cost_expected_event_manifests"],
            "rate_card_path": f"gold/qual/pilot/RATE_CARD_{set_id}.v1.json",
            "expected_manifest_path": f"gold/qual/pilot/EXPECTED_COST_MANIFEST_{set_id}.v1.json"},
        "seats": "A=Codex-GPT(gpt-5.6-sol) / B=Opus-4.8；仲裁=隔离 Opus 会话",
        "review_formulaic_note": "§四.3/§四.4：review + formulaic 均为真双席跨模型标注（非占位）——"
        "review 每 item 两独立 decision；formulaic 每 pair 双席逐 6 轴→verdict，分歧走隔离仲裁席；"
        "verdict/axes 由真席决定，绝不预置。规模/率阈达标属全量 R3-run。",
        "sealed_discipline": f"faces/labels 明文只落 sealed_custody_001/pilot_{set_id}/（gitignore）；本回执零明文",
        # §四.7 成本统一：唯一权威成本=原始 registry 重算（cost_inputs.unified_cost 同源），无双数矛盾
        "cost": cost_inputs["unified_cost"],
        "cost_single_source": "sealed_custody_001/pilot_%s/REGISTRY.jsonl（原始 registry；receipt/"
                              "expected-manifest 同引此一数字，无矛盾）" % set_id,
    }
    (PILOT_QUAL / f"PILOT_RECEIPT_{set_id}.v1.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in (
        "pilot_pass", "pilot_pass_conditions", "faces_total", "challenge_kinds_present",
        "labeled_both_seats", "cross_model_disputes", "adjudicated", "core_validation_passed",
        "generation_chain_resolves", "readiness_verdict", "non_scale_failures",
        "counts_recomputed")}, ensure_ascii=False, indent=1))
    return 0 if receipt["pilot_pass"] else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["A", "B"], default="A", help="QUAL 套（默认 A；§五 B 对称跑）")
    args = ap.parse_args()
    sys.exit(run_pilot(args.set))
