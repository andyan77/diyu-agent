#!/usr/bin/env python3
"""G3 · 门校准装置：用上一轮 211 条真实输出验证 v3 门的捕获力与误报率。

只读上一轮冻结证据（p5_p6），产出确定性校准报告。
校准目标（执行包1 验收"CP01/CP06/CP07 盲判和指纹表现相对上一轮有可复算改善"
的机器可复算基线之一）：

1. 上一轮 10 条治理语言硬否决 → v3 治理门应全捕（recall=10/10）；
2. 上一轮 28 条套路/近重复 → 骨架集中度∪批内近重复∪治理门 覆盖率；
3. 上一轮 156 条直批干净项 → v3 HARD 门误报率（越低越好）；
4. 指纹谓词：盲判误判项 vs 判对项的谓词缺失率对照（区分力证明）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import g3_author_contract as contract  # noqa: E402
import g3_expression  # noqa: E402
import g3_fingerprint  # noqa: E402
import g3_lexicon  # noqa: E402
import g3_similarity  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
P5 = (ROOT / "controlled_content_generator_v2_001/gate1_v1_1_001"
      / "p5_p6_300_baseline_scale_and_freeze_001")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _audience_scan(output: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    raw_view = {
        "synthetic_disclosure": output["synthetic_disclosure"],
        "title": output["title"],
        "body": list(output["body"]),
        "spoken_lines": list(output["spoken_lines"]),
        "cta": output["cta"],
        "visual_execution": list(output["visual_execution"]),
        "audio_execution": list(output["audio_execution"]),
    }
    hard: set[str] = set()
    flag: set[str] = set()
    leak: set[str] = set()
    for _, text in contract.audience_texts(raw_view):
        h, f = g3_lexicon.scan_governance(text)
        hard.update(h)
        flag.update(f)
        leak.update(g3_lexicon.scan_label_leak(text))
    return sorted(hard), sorted(flag), sorted(leak)


def run_calibration() -> dict[str, Any]:
    outputs = _read_jsonl(P5 / "production/positive_first_outputs.v1.0.jsonl")
    reviews: dict[str, dict[str, Any]] = {}
    for path in sorted((P5 / "review/production").glob("content.group_*.jsonl")):
        for row in _read_jsonl(path):
            reviews[str(row["request_id"])] = row
    assert len(outputs) == 211 and len(reviews) == 211, (len(outputs), len(reviews))

    hard_veto_ids = sorted(r["request_id"] for r in reviews.values()
                           if r["hard_error_codes"])
    formulaic_ids = sorted(r["request_id"] for r in reviews.values()
                           if r["formulaic_or_near_duplicate"])
    clean_ids = sorted(r["request_id"] for r in reviews.values()
                       if r["first_acceptable"] and not r["formulaic_or_near_duplicate"]
                       and not r["hard_error_codes"])
    misjudged_ids = sorted(r["request_id"] for r in reviews.values()
                           if r["blind_profile_choice"] != r["profile_id"])

    gov_hits: dict[str, list[str]] = {}
    leak_hits: dict[str, list[str]] = {}
    for output in outputs:
        hard, _flag, leak = _audience_scan(output)
        if hard:
            gov_hits[str(output["request_id"])] = hard
        if leak:
            leak_hits[str(output["request_id"])] = leak

    concentration = g3_expression.concentration_findings(outputs)
    conc_ids = sorted({rid for f in concentration for rid in f["request_ids"]})
    near_dup = g3_similarity.pairwise_batch_findings(outputs)
    dup_ids = sorted({rid for f in near_dup for rid in f["request_ids"]})

    formulaic_covered = sorted(
        rid for rid in formulaic_ids
        if rid in conc_ids or rid in dup_ids or rid in gov_hits)
    veto_caught = sorted(rid for rid in hard_veto_ids if rid in gov_hits)
    clean_hard_fp = sorted(rid for rid in clean_ids
                           if rid in gov_hits or rid in leak_hits)

    predicate_miss: dict[str, list[str]] = {}
    for output in outputs:
        missing = g3_fingerprint.predicate_findings(output)
        if missing:
            predicate_miss[str(output["request_id"])] = missing
    focus = {}
    for cp in ("CP01", "CP02", "CP05", "CP06", "CP07", "CP09", "CP18"):
        cp_out = [o for o in outputs if o["profile_id"] == cp]
        mis = [o for o in cp_out if str(o["request_id"]) in misjudged_ids]
        cor = [o for o in cp_out if str(o["request_id"]) not in misjudged_ids]
        focus[cp] = {
            "outputs": len(cp_out),
            "misjudged": len(mis),
            "misjudged_predicate_miss": sum(
                1 for o in mis if str(o["request_id"]) in predicate_miss),
            "correct_predicate_miss": sum(
                1 for o in cor if str(o["request_id"]) in predicate_miss),
        }

    report = {
        "schema_version": "gate1-g3-gate-calibration-report-v0.1",
        "task_id": contract.TASK_ID,
        "corpus": "p5_p6 positive_first_outputs.v1.0.jsonl (211, frozen)",
        "hard_veto_baseline": {"count": len(hard_veto_ids), "ids": hard_veto_ids},
        "governance_gate": {
            "hit_count": len(gov_hits),
            "veto_recall": f"{len(veto_caught)}/{len(hard_veto_ids)}",
            "veto_caught_ids": veto_caught,
            "veto_missed_ids": sorted(set(hard_veto_ids) - set(veto_caught)),
        },
        "formulaic_baseline": {"count": len(formulaic_ids)},
        "formulaic_coverage": {
            "covered": f"{len(formulaic_covered)}/{len(formulaic_ids)}",
            "via_concentration": len([r for r in formulaic_ids if r in conc_ids]),
            "via_near_dup": len([r for r in formulaic_ids if r in dup_ids]),
            "via_governance": len([r for r in formulaic_ids if r in gov_hits]),
            "missed_ids": sorted(set(formulaic_ids) - set(formulaic_covered)),
        },
        "clean_set": {
            "count": len(clean_ids),
            "hard_false_positive_count": len(clean_hard_fp),
            "hard_false_positive_ids": clean_hard_fp,
            "hard_false_positive_hits": {
                rid: gov_hits.get(rid, []) + leak_hits.get(rid, [])
                for rid in clean_hard_fp},
        },
        "near_dup_stats": {
            "pair_findings": len(near_dup),
            "max_jaccard": near_dup[0]["jaccard"] if near_dup else 0.0,
            "flagged_output_count": len(dup_ids),
        },
        "concentration_findings_count": len(concentration),
        "fingerprint_focus_cps": focus,
    }
    report["report_digest"] = contract.object_digest(report, "report_digest")
    return report


if __name__ == "__main__":
    result = run_calibration()
    out = Path(__file__).resolve().parent / "evidence"
    out.mkdir(exist_ok=True)
    text = contract.canonical_json(result)
    (out / "gate_calibration_report.v0.1.json").write_text(text + "\n",
                                                           encoding="utf-8")
    print(text[:2000])
