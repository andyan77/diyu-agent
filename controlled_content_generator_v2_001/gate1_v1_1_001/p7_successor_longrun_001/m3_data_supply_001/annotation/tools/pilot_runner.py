#!/usr/bin/env python3
"""M3 胶囊② 双盲小试执行器（可断点续跑）。

子命令：
  select      确定性选样（每族 sha256(frame_digest+scenario_id) 升序前 2 组，永久划 DEV）
              → PILOT_SAMPLE.v1.json + batches/
  label       --seat A|B [--max-batches N]  对未完成批次跑 headless 标注叫
  adjudicate  构造分歧批并跑裁决叫
  metrics     汇总 → PILOT_RECEIPT.v1.json（一致性/κ/争议率/成本/自然标签分布）

会话纪律（协议 §1/§2）：每叫 = 全新 `claude -p`，单轮无工具，
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1，cwd=仓外中性目录，逐叫登记 SESSION_REGISTRY。
提示词模板从 annotation_protocol.v1.json 读取并核对摘要（漂移=拒跑）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
ANN = HERE.parents[1]                    # annotation/
M3DS = HERE.parents[2]                   # m3_data_supply_001/
P7 = HERE.parents[3]
PK = P7 / "pkg1_open_regression"
PILOT = ANN / "pilot"
NEUTRAL_CWD = Path(os.environ.get("TMPDIR", "/tmp/claude-1000")) / "m3_neutral"

BATCH_SIZE = 10
MODEL = "claude-fable-5"

ROUND_FILES = {
    "round1_top": ("inputs/requests.g3.v1.jsonl", "outputs/first_outputs.g3.v1.jsonl"),
    "round2": ("round2/inputs/requests.g3.v1.jsonl", "round2/outputs/first_outputs.g3.v1.jsonl"),
    "round3": ("round3/inputs/requests.g3.v1.jsonl", "round3/outputs/first_outputs.g3.v1.jsonl"),
    "round5": ("round5/inputs/requests.g3.v1.jsonl", "round5/outputs/first_outputs.g3.v1.jsonl"),
}


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def sha_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def load_protocol() -> dict:
    return json.loads((ANN / "annotation_protocol.v1.json").read_text(encoding="utf-8"))


def template(proto: dict, key: str) -> str:
    entry = proto["prompt_templates"][key]
    text = entry["text"]
    if sha_text(text) != entry["sha256"]:
        raise SystemExit(f"prompt template {key} digest drift — refuse to run")
    return text


def cmd_select() -> int:
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    fd = frame["frame_digest"]
    per_family: dict[str, list[dict]] = {}
    for g in frame["groups"]:
        per_family.setdefault(g["family_id"], []).append(g)
    chosen = []
    for fam in sorted(per_family):
        ranked = sorted(per_family[fam], key=lambda g: sha_text(fd + g["scenario_id"]))
        chosen.extend(ranked[:2])
    assert len(chosen) == 10
    chosen_ids = {g["scenario_id"] for g in chosen}

    scen_meta = {s["scenario_id"]: s for s in jl(PK / "round5/inputs/scenarios.g3.v2.jsonl")}
    cases = []
    for rname, (req_rel, out_rel) in ROUND_FILES.items():
        reqs = {r["request_id"]: r for r in jl(PK / req_rel)}
        for o in jl(PK / out_rel):
            req = reqs[o["request_id"]]
            sid = req["scenario_id"]
            if sid not in chosen_ids:
                continue
            scen = scen_meta[sid]
            for c in o.get("claims", []):
                cases.append({
                    "case_id": f"PILOT-{rname}-{c['claim_id']}",
                    "scenario_id": sid,
                    "family_id": next(g["family_id"] for g in chosen if g["scenario_id"] == sid),
                    "round": rname,
                    "item_title": o.get("title", ""),
                    "claim_id": c["claim_id"],
                    "claim_text": c["claim_text"],
                    "claim_boundary": c.get("claim_boundary", ""),
                    "authorization_scope": scen.get("authorization_scope", ""),
                    "slot_facts": scen.get("slot_facts", {}),
                    "source_summary_a": scen.get("source_summary_a", ""),
                    "source_summary_b": scen.get("source_summary_b", ""),
                })
    case_ids = [c["case_id"] for c in cases]
    assert len(case_ids) == len(set(case_ids)), "case_id 重复"
    batches = [cases[i:i + BATCH_SIZE] for i in range(0, len(cases), BATCH_SIZE)]
    PILOT.mkdir(parents=True, exist_ok=True)
    (PILOT / "batches").mkdir(exist_ok=True)
    for i, b in enumerate(batches):
        (PILOT / "batches" / f"batch_{i:03d}.json").write_text(
            json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    sample = {
        "schema_version": "p7-m3-pilot-sample-v1",
        "preregistered_rule": "每族 sha256(frame_digest + scenario_id) 升序前 2 组；该 10 组永久划入 DEV 可见性分区，禁入任何 QUAL 抽样框",
        "frame_digest": fd,
        "dev_assigned_groups": sorted(chosen_ids),
        "groups_per_family": {fam: sorted(g["scenario_id"] for g in per_family[fam]
                                          if g["scenario_id"] in chosen_ids)
                              for fam in sorted(per_family)},
        "case_count": len(cases),
        "cases_per_family": dict(sorted(Counter(c["family_id"] for c in cases).items())),
        "batch_size": BATCH_SIZE,
        "batch_count": len(batches),
        "cases_digest": sha_text(json.dumps(case_ids, ensure_ascii=False)),
    }
    (PILOT / "PILOT_SAMPLE.v1.json").write_text(
        json.dumps(sample, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(sample, ensure_ascii=False, indent=1))
    return 0


def _run_call(prompt: str, tag: str) -> dict:
    NEUTRAL_CWD.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    proc = subprocess.run(
        ["claude", "-p", "--model", MODEL, "--output-format", "json", "--max-turns", "1"],
        input=prompt, capture_output=True, text=True, env=env,
        cwd=str(NEUTRAL_CWD), timeout=420)
    if proc.returncode != 0:
        raise RuntimeError(f"{tag}: claude exit {proc.returncode}: {proc.stderr[-300:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _parse_labels(result_text: str, expected_ids: set[str], label_keys: tuple) -> list[dict] | None:
    text = result_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("["):text.rfind("]") + 1]
    try:
        rows = json.loads(text)
    except json.JSONDecodeError:
        try:
            rows = json.loads(text[text.find("["):text.rfind("]") + 1])
        except Exception:
            return None
    if not isinstance(rows, list):
        return None
    got = {r.get("case_id") for r in rows if isinstance(r, dict)}
    if got != expected_ids:
        return None
    for r in rows:
        for k in label_keys:
            if k not in r:
                return None
    return rows


def _register(row: dict) -> None:
    with open(PILOT / "SESSION_REGISTRY.v1.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def cmd_label(seat: str, max_batches: int) -> int:
    proto = load_protocol()
    tmpl = template(proto, "labeler")
    out_dir = PILOT / f"labels_{seat}"
    out_dir.mkdir(parents=True, exist_ok=True)
    done = 0
    for bpath in sorted((PILOT / "batches").glob("batch_*.json")):
        if done >= max_batches:
            break
        out_path = out_dir / (bpath.stem + ".labels.json")
        if out_path.exists():
            continue
        cases = json.loads(bpath.read_text(encoding="utf-8"))
        slim = [{k: c[k] for k in ("case_id", "claim_text", "claim_boundary",
                                   "authorization_scope", "slot_facts",
                                   "source_summary_a", "source_summary_b", "item_title")}
                for c in cases]
        prompt = tmpl.replace("{seat}", seat).replace(
            "{batch_json}", json.dumps(slim, ensure_ascii=False, indent=1))
        expected = {c["case_id"] for c in cases}
        attempts = 0
        rows = None
        while attempts < 2 and rows is None:
            attempts += 1
            res = _run_call(prompt, f"{seat}/{bpath.stem}/try{attempts}")
            raw_path = out_dir / f"{bpath.stem}.raw.try{attempts}.json"
            raw_path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            _register({
                "kind": "LABEL", "seat": seat, "batch": bpath.stem, "attempt": attempts,
                "session_id": res.get("session_id"),
                "visible_material": sorted(expected),
                "raw_output_path": str(raw_path.relative_to(ANN)),
                "cost_usd": res.get("total_cost_usd"),
                "duration_ms": res.get("duration_ms"),
                "num_turns": res.get("num_turns"),
                "retention": "raw JSON 留存于 labels_ 目录；无销毁（开发格非密封）",
            })
            rows = _parse_labels(res.get("result", ""), expected, ("risk", "entailment"))
        if rows is None:
            (out_dir / f"{bpath.stem}.FAILED").write_text("parse failed after retry", encoding="utf-8")
            print(f"FAILED {seat} {bpath.stem}")
            continue
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
        print(f"OK {seat} {bpath.stem} cases={len(rows)}")
    remaining = [p.stem for p in sorted((PILOT / 'batches').glob('batch_*.json'))
                 if not (out_dir / (p.stem + '.labels.json')).exists()]
    print(json.dumps({"seat": seat, "completed_this_run": done, "remaining": remaining}))
    return 0


def _collect(seat: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted((PILOT / f"labels_{seat}").glob("batch_*.labels.json")):
        for r in json.loads(p.read_text(encoding="utf-8")):
            out[r["case_id"]] = r
    return out


def cmd_adjudicate(max_batches: int) -> int:
    proto = load_protocol()
    tmpl = template(proto, "adjudicator")
    a, b = _collect("A"), _collect("B")
    cases_by_id = {}
    for p in sorted((PILOT / "batches").glob("batch_*.json")):
        for c in json.loads(p.read_text(encoding="utf-8")):
            cases_by_id[c["case_id"]] = c
    disputes = []
    for cid in sorted(set(a) & set(b)):
        ra, rb = a[cid], b[cid]
        if ra["risk"] != rb["risk"] or ra["entailment"] != rb["entailment"]:
            c = cases_by_id[cid]
            disputes.append({
                "case_id": cid,
                "claim_text": c["claim_text"], "claim_boundary": c["claim_boundary"],
                "authorization_scope": c["authorization_scope"],
                "slot_facts": c["slot_facts"],
                "source_summary_a": c["source_summary_a"],
                "source_summary_b": c["source_summary_b"],
                "label_jia": {"risk": ra["risk"], "entailment": ra["entailment"],
                              "rationale": ra.get("rationale", "")},
                "label_yi": {"risk": rb["risk"], "entailment": rb["entailment"],
                             "rationale": rb.get("rationale", "")},
            })
    (PILOT / "disputes.json").write_text(
        json.dumps(disputes, ensure_ascii=False, indent=1), encoding="utf-8")
    adj_dir = PILOT / "adjudication"
    adj_dir.mkdir(exist_ok=True)
    batches = [disputes[i:i + BATCH_SIZE] for i in range(0, len(disputes), BATCH_SIZE)]
    done = 0
    for i, batch in enumerate(batches):
        if done >= max_batches:
            break
        out_path = adj_dir / f"adj_{i:03d}.labels.json"
        if out_path.exists():
            continue
        prompt = tmpl.replace("{batch_json}", json.dumps(batch, ensure_ascii=False, indent=1))
        expected = {c["case_id"] for c in batch}
        rows = None
        attempts = 0
        while attempts < 2 and rows is None:
            attempts += 1
            res = _run_call(prompt, f"adj/{i}/try{attempts}")
            raw_path = adj_dir / f"adj_{i:03d}.raw.try{attempts}.json"
            raw_path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            _register({
                "kind": "ADJUDICATE", "batch": f"adj_{i:03d}", "attempt": attempts,
                "session_id": res.get("session_id"),
                "visible_material": sorted(expected),
                "raw_output_path": str(raw_path.relative_to(ANN)),
                "cost_usd": res.get("total_cost_usd"),
                "duration_ms": res.get("duration_ms"),
                "num_turns": res.get("num_turns"),
                "retention": "raw JSON 留存；无销毁（开发格非密封）",
            })
            rows = _parse_labels(res.get("result", ""), expected, ("risk", "entailment"))
        if rows is None:
            (adj_dir / f"adj_{i:03d}.FAILED").write_text("parse failed", encoding="utf-8")
            print(f"FAILED adj_{i:03d}")
            continue
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
        print(f"OK adj_{i:03d} cases={len(rows)}")
    print(json.dumps({"disputes": len(disputes), "adj_batches": len(batches),
                      "completed_this_run": done}))
    return 0


def _kappa(pairs: list[tuple[str, str]], classes: list[str]) -> float | str:
    n = len(pairs)
    if n == 0:
        return "NOT_INTERPRETABLE"
    po = sum(1 for x, y in pairs if x == y) / n
    pe = sum((sum(1 for x, _ in pairs if x == c) / n)
             * (sum(1 for _, y in pairs if y == c) / n) for c in classes)
    if pe >= 1.0:
        return "NOT_INTERPRETABLE"
    return round((po - pe) / (1 - pe), 4)


def cmd_metrics() -> int:
    a, b = _collect("A"), _collect("B")
    common = sorted(set(a) & set(b))
    sample = json.loads((PILOT / "PILOT_SAMPLE.v1.json").read_text(encoding="utf-8"))
    adj: dict[str, dict] = {}
    for p in sorted((PILOT / "adjudication").glob("adj_*.labels.json")):
        for r in json.loads(p.read_text(encoding="utf-8")):
            adj[r["case_id"]] = r
    fam_by_case = {}
    for p in sorted((PILOT / "batches").glob("batch_*.json")):
        for c in json.loads(p.read_text(encoding="utf-8")):
            fam_by_case[c["case_id"]] = c["family_id"]

    risk_pairs = [(a[c]["risk"], b[c]["risk"]) for c in common]
    ent_pairs = [(a[c]["entailment"], b[c]["entailment"]) for c in common]
    disputes = [c for c in common
                if a[c]["risk"] != b[c]["risk"] or a[c]["entailment"] != b[c]["entailment"]]
    gold, unresolved = {}, []
    for c in common:
        if c not in disputes:
            gold[c] = {"risk": a[c]["risk"], "entailment": a[c]["entailment"], "source": "AGREED"}
        elif c in adj:
            gold[c] = {"risk": adj[c]["risk"], "entailment": adj[c]["entailment"], "source": "ADJUDICATED"}
        else:
            unresolved.append(c)

    nat = [c for c, g in gold.items()
           if g["entailment"] == "SUPPORTED" and g["risk"] in ("LOW", "MEDIUM")]
    reg = [json.loads(l) for l in open(PILOT / "SESSION_REGISTRY.v1.jsonl", encoding="utf-8")]
    cost = round(sum(r.get("cost_usd") or 0 for r in reg), 4)
    wall_ms = sum(r.get("duration_ms") or 0 for r in reg)

    fam_nat = Counter(fam_by_case[c] for c in nat)
    fam_gold = Counter(fam_by_case[c] for c in gold)
    receipt = {
        "schema_version": "p7-m3-pilot-receipt-v1",
        "sample_ref": {"cases_digest": sample["cases_digest"],
                       "case_count": sample["case_count"],
                       "dev_assigned_groups": sample["dev_assigned_groups"]},
        "completion": {"labeled_both_seats": len(common),
                       "completion_rate": round(len(common) / sample["case_count"], 4),
                       "unresolved": unresolved},
        "agreement": {
            "risk_raw": round(sum(1 for x, y in risk_pairs if x == y) / len(risk_pairs), 4),
            "entailment_raw": round(sum(1 for x, y in ent_pairs if x == y) / len(ent_pairs), 4),
            "risk_kappa": _kappa(risk_pairs, ["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "entailment_kappa": _kappa(ent_pairs, ["SUPPORTED", "CONTRADICTED", "UNKNOWN"]),
            "dispute_rate": round(len(disputes) / len(common), 4),
            "dispute_count": len(disputes),
        },
        "gold": {"count": len(gold),
                 "risk_distribution": dict(sorted(Counter(g["risk"] for g in gold.values()).items())),
                 "entailment_distribution": dict(sorted(Counter(g["entailment"] for g in gold.values()).items()))},
        "natural_label_share": {
            "definition": "entailment=SUPPORTED ∧ risk∈{LOW,MEDIUM} 占金标比例（供需 v2 表 0.59 阈值判定输入）",
            "count": len(nat), "share": round(len(nat) / len(gold), 4) if gold else None,
            "per_family_share": {f: round(fam_nat[f] / fam_gold[f], 4)
                                 for f in sorted(fam_gold)},
            "threshold": 0.59,
            "meets_threshold": (len(nat) / len(gold) >= 0.59) if gold else None,
        },
        "cost": {"total_usd": cost, "total_wall_clock_ms": wall_ms,
                 "calls": len(reg),
                 "amortized_usd_per_case_both_seats": round(cost / len(common), 4) if common else None},
        "protocol_ref": {"path": "annotation/annotation_protocol.v1.json"},
    }
    (PILOT / "PILOT_RECEIPT.v1.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select")
    lp = sub.add_parser("label")
    lp.add_argument("--seat", choices=["A", "B"], required=True)
    lp.add_argument("--max-batches", type=int, default=99)
    adp = sub.add_parser("adjudicate")
    adp.add_argument("--max-batches", type=int, default=99)
    sub.add_parser("metrics")
    args = ap.parse_args()
    if args.cmd == "select":
        return cmd_select()
    if args.cmd == "label":
        return cmd_label(args.seat, args.max_batches)
    if args.cmd == "adjudicate":
        return cmd_adjudicate(args.max_batches)
    if args.cmd == "metrics":
        return cmd_metrics()
    return 2


if __name__ == "__main__":
    sys.exit(main())
