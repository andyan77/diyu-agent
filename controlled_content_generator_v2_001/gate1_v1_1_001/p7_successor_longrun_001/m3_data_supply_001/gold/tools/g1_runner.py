#!/usr/bin/env python3
"""M3 胶囊③ G1 参考断言金标执行器（附录 B 流程，可断点续跑）。

出口门：spine.source_index.validate_reference_assertions 对最终金标（断言+
digest 闭合审查记录+证据单元）零错误；G1_RECEIPT 汇总覆盖/争议率/成本。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
GOLD = HERE.parents[1]              # m3_data_supply_001/gold/
M3DS = HERE.parents[2]
P7 = HERE.parents[3]
ANN = M3DS / "annotation"
ANNEX = ANN / "annotation_protocol_annexB_g1.v1.json"
PK = P7 / "pkg1_open_regression"
G1 = GOLD / "g1"
REG = G1 / "SESSION_REGISTRY.v1.jsonl"

sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
import labeling_lib as L                                    # noqa: E402
from spine.canonical import digest_json, digest_text        # noqa: E402
from spine.source_index import (make_source_evidence_unit,  # noqa: E402
                                validate_reference_assertions)

BATCH_SOURCES = 5
BATCH_ASSERTIONS = 15
PROP_KEYS = ("source_id", "subject", "predicate", "object_value", "unit",
             "time_scope", "polarity", "modality", "preconditions", "quote",
             "risk_class")


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def cmd_partition() -> int:
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    pilot = json.loads((ANN / "pilot/PILOT_SAMPLE.v1.json").read_text(encoding="utf-8"))
    fd = frame["frame_digest"]
    pilot_ids = set(pilot["dev_assigned_groups"])
    extra_per_family = {"F1_PEOPLE_AND_REAL_SCENE": 5, "F2_PROFESSIONAL_AND_SEARCH": 5,
                        "F3_PRODUCT_RELATION_AND_AESTHETIC": 4,
                        "F4_STORE_LOCAL_AND_RETAIL": 4, "F5_ENTERPRISE_LONG_TERM_TRUST": 2}
    per_family: dict[str, list[dict]] = {}
    for g in frame["groups"]:
        per_family.setdefault(g["family_id"], []).append(g)
    dev = sorted(pilot_ids)
    for fam, extra in sorted(extra_per_family.items()):
        pool = [g for g in per_family[fam] if g["scenario_id"] not in pilot_ids]
        ranked = sorted(pool, key=lambda g: L.sha_text(fd + "DEV2" + g["scenario_id"]))
        dev.extend(g["scenario_id"] for g in ranked[:extra])
    dev = sorted(dev)
    assert len(dev) == 30
    qual_pool = sorted(g["scenario_id"] for g in frame["groups"]
                       if g["scenario_id"] not in set(dev))
    assert len(qual_pool) == 90
    out = {
        "schema_version": "p7-m3-dev-partition-v1",
        "rule": "DEV=小试 10 组（强制保留）+ 每族 sha256(frame_digest+'DEV2'+scenario_id) 升序补 {F1:5,F2:5,F3:4,F4:4,F5:2}；QUAL 池=其余 90 组（A/B 切分属胶囊⑤题面冻结回执）",
        "frame_digest": fd,
        "dev_groups": dev,
        "dev_per_family": dict(sorted(Counter(
            next(g["family_id"] for g in frame["groups"] if g["scenario_id"] == s)
            for s in dev).items())),
        "qual_pool_groups": qual_pool,
        "partition_digest": L.sha_text(json.dumps({"dev": dev, "qual": qual_pool})),
    }
    (GOLD / "DEV_PARTITION.v1.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("dev_per_family", "partition_digest")},
                     ensure_ascii=False))
    return 0


def _dev_sources() -> list[dict]:
    part = json.loads((GOLD / "DEV_PARTITION.v1.json").read_text(encoding="utf-8"))
    scen = {s["scenario_id"]: s for s in jl(PK / "round5/inputs/scenarios.g3.v2.jsonl")}
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    fam = {g["scenario_id"]: g["family_id"] for g in frame["groups"]}
    sources = []
    for sid in part["dev_groups"]:
        s = scen[sid]
        for tag in ("a", "b"):
            text = s.get(f"source_summary_{tag}", "")
            if not text:
                continue
            sources.append({
                "source_id": f"G1SRC-{sid}-{tag.upper()}",
                "scenario_id": sid, "family_id": fam[sid],
                "authorization_scope": s.get("authorization_scope", ""),
                "slot_facts": s.get("slot_facts", {}),
                "source_text": text,
            })
    return sources


def cmd_propose(seat: str, max_batches: int) -> int:
    tmpl = L.load_template(ANNEX, "g1_proposer")
    sources = _dev_sources()
    batches = [sources[i:i + BATCH_SOURCES] for i in range(0, len(sources), BATCH_SOURCES)]
    out_dir = G1 / f"propose_{seat}"
    done = 0
    for i, batch in enumerate(batches):
        if done >= max_batches:
            break
        out_path = out_dir / f"pb_{i:03d}.props.json"
        if out_path.exists():
            continue
        expected_sids = {s["source_id"] for s in batch}
        text_by_sid = {s["source_id"]: s["source_text"] for s in batch}

        def ok(rows: list) -> bool:
            if not all(isinstance(r, dict) and all(k in r for k in PROP_KEYS)
                       for r in rows):
                return False
            sids = {r["source_id"] for r in rows}
            if not sids <= expected_sids or sids != expected_sids:
                return False
            # 批级接受门 0.8（防系统性编造）；条目级逐字过滤在保存时执行，
            # 非逐字 quote 一律不入库（真正的硬门在 assemble 的 validator 零错误）
            good = sum(1 for r in rows if r["quote"] in text_by_sid.get(r["source_id"], ""))
            return good >= max(1, int(0.8 * len(rows)))

        prompt = tmpl.replace("{seat}", seat).replace(
            "{batch_json}", json.dumps(batch, ensure_ascii=False, indent=1))
        rows = L.attempt_call(prompt, ok, out_dir, f"pb_{i:03d}", REG,
                              {"kind": "G1_PROPOSE", "seat": seat, "batch": f"pb_{i:03d}",
                               "visible_material": sorted(expected_sids),
                               "retention": "raw 留存（开发格非密封）"})
        if rows is None:
            (out_dir / f"pb_{i:03d}.FAILED").write_text("", encoding="utf-8")
            print(f"FAILED {seat} pb_{i:03d}")
            continue
        rows = [r for r in rows if r["quote"] in text_by_sid.get(r["source_id"], "")]
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
        print(f"OK {seat} pb_{i:03d} assertions={len(rows)}")
    remaining = [i for i in range(len(batches))
                 if not (out_dir / f"pb_{i:03d}.props.json").exists()]
    print(json.dumps({"seat": seat, "remaining_batches": remaining}))
    return 0


def cmd_merge(max_batches: int) -> int:
    tmpl = L.load_template(ANNEX, "g1_merger")
    sources = _dev_sources()
    props = {}
    for seat in ("A", "B"):
        rows = []
        for p in sorted((G1 / f"propose_{seat}").glob("pb_*.props.json")):
            rows.extend(json.loads(p.read_text(encoding="utf-8")))
        props[seat] = rows
    by_sid: dict[str, dict] = {s["source_id"]: {"source": s, "jia": [], "yi": []}
                               for s in sources}
    for r in props["A"]:
        by_sid[r["source_id"]]["jia"].append(r)
    for r in props["B"]:
        by_sid[r["source_id"]]["yi"].append(r)
    items = [{"source_id": sid, "source_text": v["source"]["source_text"],
              "authorization_scope": v["source"]["authorization_scope"],
              "proposals_jia": v["jia"], "proposals_yi": v["yi"]}
             for sid, v in sorted(by_sid.items())]
    batches = [items[i:i + BATCH_SOURCES] for i in range(0, len(items), BATCH_SOURCES)]
    out_dir = G1 / "merged"
    done = 0
    for i, batch in enumerate(batches):
        if done >= max_batches:
            break
        out_path = out_dir / f"mb_{i:03d}.merged.json"
        if out_path.exists():
            continue
        expected_sids = {s["source_id"] for s in batch}
        text_by_sid = {s["source_id"]: s["source_text"] for s in batch}

        def ok(rows: list) -> bool:
            return (all(isinstance(r, dict) and all(k in r for k in PROP_KEYS)
                        for r in rows)
                    and {r["source_id"] for r in rows} == expected_sids
                    and all(r["quote"] in text_by_sid[r["source_id"]] for r in rows))

        prompt = tmpl.replace("{batch_json}",
                              json.dumps(batch, ensure_ascii=False, indent=1))
        rows = L.attempt_call(prompt, ok, out_dir, f"mb_{i:03d}", REG,
                              {"kind": "G1_MERGE", "batch": f"mb_{i:03d}",
                               "visible_material": sorted(expected_sids),
                               "retention": "raw 留存"})
        if rows is None:
            (out_dir / f"mb_{i:03d}.FAILED").write_text("", encoding="utf-8")
            print(f"FAILED mb_{i:03d}")
            continue
        for j, r in enumerate(rows):
            r["assertion_id"] = f"RA-{r['source_id']}-{j+1:02d}"
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
        print(f"OK mb_{i:03d} merged={len(rows)}")
    remaining = [i for i in range(len(batches))
                 if not (out_dir / f"mb_{i:03d}.merged.json").exists()]
    print(json.dumps({"remaining_batches": remaining}))
    return 0


def _merged() -> list[dict]:
    rows = []
    for p in sorted((G1 / "merged").glob("mb_*.merged.json")):
        rows.extend(json.loads(p.read_text(encoding="utf-8")))
    return rows


def cmd_confirm(seat: str, max_batches: int) -> int:
    # 席位路由（发起人双裁决 journal seq38 + scope v1.1）：A=Codex-GPT，B=Fable
    carrier = "codex" if seat == "A" else "claude"
    tmpl = L.load_template(ANNEX, "g1_confirmer")
    sources = {s["source_id"]: s for s in _dev_sources()}
    cand = _merged()
    items = [{"assertion_id": r["assertion_id"], "source_id": r["source_id"],
              "source_text": sources[r["source_id"]]["source_text"],
              **{k: r[k] for k in PROP_KEYS if k != "source_id"}} for r in cand]
    batches = [items[i:i + BATCH_ASSERTIONS]
               for i in range(0, len(items), BATCH_ASSERTIONS)]
    out_dir = G1 / f"confirm_{seat}"
    done = 0
    for i, batch in enumerate(batches):
        if done >= max_batches:
            break
        out_path = out_dir / f"cb_{i:03d}.decisions.json"
        if out_path.exists():
            continue
        expected = {c["assertion_id"] for c in batch}

        def ok(rows: list) -> bool:
            return ({r.get("assertion_id") for r in rows if isinstance(r, dict)} == expected
                    and all(r.get("decision") in ("CONFIRM", "REJECT") for r in rows))

        seat_label = "A(Codex-GPT)" if seat == "A" else seat
        prompt = tmpl.replace("{seat}", seat_label).replace(
            "{batch_json}", json.dumps(batch, ensure_ascii=False, indent=1))
        rows = L.attempt_call(prompt, ok, out_dir, f"cb_{i:03d}", REG,
                              {"kind": "G1_CONFIRM", "seat": seat, "batch": f"cb_{i:03d}",
                               "visible_material": sorted(expected),
                               "retention": "raw 留存"},
                              carrier=carrier)
        if rows is None:
            (out_dir / f"cb_{i:03d}.FAILED").write_text("", encoding="utf-8")
            print(f"FAILED {seat} cb_{i:03d}")
            continue
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
        print(f"OK {seat} cb_{i:03d}")
    remaining = [i for i in range(len(batches))
                 if not (out_dir / f"cb_{i:03d}.decisions.json").exists()]
    print(json.dumps({"seat": seat, "remaining_batches": remaining}))
    return 0


def _decisions(seat: str) -> dict[str, dict]:
    out = {}
    for p in sorted((G1 / f"confirm_{seat}").glob("cb_*.decisions.json")):
        for r in json.loads(p.read_text(encoding="utf-8")):
            out[r["assertion_id"]] = r
    return out


def cmd_adjudicate(max_batches: int) -> int:
    tmpl = L.load_template(ANNEX, "g1_adjudicator")
    sources = {s["source_id"]: s for s in _dev_sources()}
    cand = {r["assertion_id"]: r for r in _merged()}
    da, db = _decisions("A"), _decisions("B")
    disputes = []
    for aid in sorted(set(da) & set(db)):
        if da[aid]["decision"] != db[aid]["decision"]:
            r = cand[aid]
            disputes.append({"assertion_id": aid, "source_id": r["source_id"],
                             "source_text": sources[r["source_id"]]["source_text"],
                             **{k: r[k] for k in PROP_KEYS if k != "source_id"},
                             "decision_jia": da[aid], "decision_yi": db[aid]})
    (G1 / "adjudication").mkdir(parents=True, exist_ok=True)
    (G1 / "adjudication/disputes.json").write_text(
        json.dumps(disputes, ensure_ascii=False, indent=1), encoding="utf-8")
    batches = [disputes[i:i + BATCH_ASSERTIONS]
               for i in range(0, len(disputes), BATCH_ASSERTIONS)]
    done = 0
    for i, batch in enumerate(batches):
        if done >= max_batches:
            break
        out_path = G1 / "adjudication" / f"ab_{i:03d}.decisions.json"
        if out_path.exists():
            continue
        expected = {c["assertion_id"] for c in batch}

        def ok(rows: list) -> bool:
            return ({r.get("assertion_id") for r in rows if isinstance(r, dict)} == expected
                    and all(r.get("decision") in ("CONFIRM", "REJECT") for r in rows))

        prompt = tmpl.replace("{batch_json}",
                              json.dumps(batch, ensure_ascii=False, indent=1))
        rows = L.attempt_call(prompt, ok, G1 / "adjudication", f"ab_{i:03d}", REG,
                              {"kind": "G1_ADJUDICATE", "batch": f"ab_{i:03d}",
                               "visible_material": sorted(expected),
                               "retention": "raw 留存"})
        if rows is None:
            (G1 / "adjudication" / f"ab_{i:03d}.FAILED").write_text("", encoding="utf-8")
            print(f"FAILED ab_{i:03d}")
            continue
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
        print(f"OK ab_{i:03d}")
    print(json.dumps({"disputes": len(disputes), "batches": len(batches)}))
    return 0


def cmd_assemble() -> int:
    annex = json.loads(ANNEX.read_text(encoding="utf-8"))
    conf_digest = {s: annex["prompt_templates"]["g1_confirmer"]["sha256"] for s in ("A", "B")}
    adj_digest = annex["prompt_templates"]["g1_adjudicator"]["sha256"]
    sources = {s["source_id"]: s for s in _dev_sources()}
    cand = _merged()
    da, db = _decisions("A"), _decisions("B")
    adj = {}
    for p in sorted((G1 / "adjudication").glob("ab_*.decisions.json")):
        for r in json.loads(p.read_text(encoding="utf-8")):
            adj[r["assertion_id"]] = r
    reg = [json.loads(l) for l in open(REG, encoding="utf-8")]

    def session_for(kind: str, seat: str | None, aid_batchless: str) -> str:
        rows = [r for r in reg if r["kind"] == kind and (seat is None or r.get("seat") == seat)]
        return rows[-1]["session_id"] if rows else "UNKNOWN"

    units_by_id: dict[str, dict] = {}
    assertions, reviews_by_id = [], {}
    stats = Counter()
    for r in cand:
        aid = r["assertion_id"]
        src = sources[r["source_id"]]
        text = src["source_text"]
        b = text.encode("utf-8")
        q = r["quote"].encode("utf-8")
        start = b.find(q)
        if start < 0:
            stats["quote_lost"] += 1
            continue
        unit = make_source_evidence_unit(
            r["source_id"], text, start, start + len(q),
            authorization_ids=[src["authorization_scope"] or "SCOPE-UNSPECIFIED"],
            synthetic_test_only=True)
        units_by_id[unit["evidence_unit_id"]] = unit
        dec_a, dec_b = da.get(aid), db.get(aid)
        if not dec_a or not dec_b:
            stats["missing_confirm"] += 1
            continue
        decs = (dec_a["decision"], dec_b["decision"])
        if decs == ("CONFIRM", "CONFIRM"):
            status, use_adj = "DUAL_ADJUDICATED", False
        elif "CONFIRM" in decs:
            a_dec = adj.get(aid)
            if not a_dec:
                stats["missing_adjudication"] += 1
                continue
            if a_dec["decision"] == "CONFIRM":
                status, use_adj = "DUAL_ADJUDICATED", True
            else:
                status, use_adj = "REJECTED", True
        else:
            status, use_adj = "REJECTED", False
        row = {
            "schema_version": "eval-spine-reference-assertion-v1",
            "assertion_id": aid,
            "subject": r["subject"], "predicate": r["predicate"],
            "object_value": r["object_value"], "unit": r["unit"],
            "time_scope": r["time_scope"], "polarity": r["polarity"],
            "modality": r["modality"], "preconditions": r["preconditions"],
            "evidence_unit_ids": [unit["evidence_unit_id"]],
            "authorization_ids": unit["authorization_ids"],
            "risk_class": r["risk_class"],
            "extraction_origin": "MODEL_PROPOSED_DUAL_REVIEWED",
            "engine_provenance": {
                "engine_kind": "MODEL", "engine_id": "G1-PIPELINE",
                "engine_revision": "claude-fable-5",
                "prompt_or_rule_digest": annex["prompt_templates"]["g1_proposer"]["sha256"],
                "provider_call_id": session_for("G1_MERGE", None, aid),
            },
            "verification_status": status,
            "review_ids": [], "object_digest": "",
        }
        rids = []
        review_specs = [(f"REV-{aid}-A", "G1-CONFIRM-A", "REVIEWER", dec_a["decision"], conf_digest["A"]),
                        (f"REV-{aid}-B", "G1-CONFIRM-B", "REVIEWER", dec_b["decision"], conf_digest["B"])]
        if use_adj:
            review_specs.append((f"ADJ-{aid}", "G1-ADJUDICATOR", "ADJUDICATOR",
                                 adj[aid]["decision"], adj_digest))
        row["review_ids"] = [rid for rid, *_ in review_specs]
        unsigned = dict(row)
        unsigned.pop("object_digest")
        row["object_digest"] = digest_json(unsigned)
        for rid, identity, role, decision, pdigest in review_specs:
            ev_ids = list(row["evidence_unit_ids"])
            rev = {
                "schema_version": "eval-spine-reference-assertion-review-v1",
                "review_id": rid, "assertion_id": aid,
                "assertion_object_digest": row["object_digest"],
                "evidence_unit_ids": ev_ids,
                "evidence_set_digest": digest_json({
                    "assertion_id": aid,
                    "assertion_object_digest": row["object_digest"],
                    "evidence_unit_ids": sorted(set(map(str, ev_ids)))}),
                "reviewer_identity": identity, "reviewer_kind": "AI",
                "model_revision": "claude-fable-5", "prompt_digest": pdigest,
                "reviewer_role": role, "decision": decision,
                "evidence_digest": digest_json(
                    [{"evidence_unit_id": u, "object_digest": units_by_id[u]["object_digest"]}
                     for u in sorted(ev_ids)]),
                "review_digest": "",
            }
            unsigned_r = dict(rev)
            unsigned_r.pop("review_digest")
            rev["review_digest"] = digest_json(unsigned_r)
            reviews_by_id[rid] = rev
        assertions.append(row)
        stats[status] += 1

    gold = [a for a in assertions if a["verification_status"] == "DUAL_ADJUDICATED"]
    result = validate_reference_assertions(
        assertions,
        evidence_units_by_id=units_by_id,
        source_text_by_source_id={s["source_id"]: s["source_text"]
                                  for s in sources.values()},
        review_records_by_id=reviews_by_id)
    def src_of(aid: str) -> str:
        return aid[len("RA-"):aid.rindex("-")]

    fam_counts = Counter(sources[src_of(a["assertion_id"])]["family_id"] for a in gold)
    (G1 / "G1_EVIDENCE_UNITS.v1.json").write_text(
        json.dumps(units_by_id, ensure_ascii=False, indent=1), encoding="utf-8")
    (G1 / "G1_REFERENCE_GOLD.v1.json").write_text(
        json.dumps(assertions, ensure_ascii=False, indent=1), encoding="utf-8")
    (G1 / "G1_REVIEW_RECORDS.v1.json").write_text(
        json.dumps(reviews_by_id, ensure_ascii=False, indent=1), encoding="utf-8")
    disputes = json.loads((G1 / "adjudication/disputes.json").read_text(encoding="utf-8")) \
        if (G1 / "adjudication/disputes.json").is_file() else []
    receipt = {
        "schema_version": "p7-m3-g1-receipt-v1",
        "sources_covered": len({a["assertion_id"].rsplit("-", 1)[0] for a in assertions}),
        "sources_total": len(sources),
        "assertions_total": len(assertions),
        "gold_dual_adjudicated": len(gold),
        "rejected": stats.get("REJECTED", 0),
        "confirm_dispute_count": len(disputes),
        "confirm_dispute_rate": round(len(disputes) / max(1, len(cand)), 4),
        "validator_errors": result["errors"],
        "validator_clean": not result["errors"],
        "per_family_gold": dict(sorted(fam_counts.items())),
        "assembly_stats": dict(stats),
        "cost": L.registry_cost(REG),
        "gold_digest": digest_json([a["object_digest"] for a in gold]),
    }
    (G1 / "G1_RECEIPT.v1.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in
                      ("assertions_total", "gold_dual_adjudicated", "rejected",
                       "confirm_dispute_rate", "validator_clean", "per_family_gold")},
                     ensure_ascii=False, indent=1))
    return 0 if receipt["validator_clean"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("partition")
    for name in ("propose", "confirm"):
        p = sub.add_parser(name)
        p.add_argument("--seat", choices=["A", "B"], required=True)
        p.add_argument("--max-batches", type=int, default=99)
    for name in ("merge", "adjudicate"):
        p = sub.add_parser(name)
        p.add_argument("--max-batches", type=int, default=99)
    sub.add_parser("assemble")
    args = ap.parse_args()
    if args.cmd == "partition":
        return cmd_partition()
    if args.cmd == "propose":
        return cmd_propose(args.seat, args.max_batches)
    if args.cmd == "confirm":
        return cmd_confirm(args.seat, args.max_batches)
    if args.cmd == "merge":
        return cmd_merge(args.max_batches)
    if args.cmd == "adjudicate":
        return cmd_adjudicate(args.max_batches)
    if args.cmd == "assemble":
        return cmd_assemble()
    return 2


if __name__ == "__main__":
    sys.exit(main())
