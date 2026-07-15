#!/usr/bin/env python3
"""执行包1 · 开放回归驱动器（freeze-inputs / shape-check / gate / blind-packet / metrics）。

用法（在仓库根运行）：
    python3 .../run_pkg1.py freeze-inputs   # 冻结场景+请求+计划（只能一次）
    python3 .../run_pkg1.py shape-check     # 作者原稿形状校验（只回错误码，无内容反馈）
    python3 .../run_pkg1.py gate            # 序列化+机器门（写 first_outputs + 报告）
    python3 .../run_pkg1.py blind-packet    # 构建去标签盲审包（含泄漏扫描）
    python3 .../run_pkg1.py metrics         # 从原始文件重算全部指标

确定性：全部输出 canonical json / 排序键，重复运行零差异。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
G3 = ROOT / "controlled_content_generator_v2_001/generator_v3_successor_001"
sys.path.insert(0, str(G3))

import g3_author_contract as contract  # noqa: E402
import g3_expression  # noqa: E402
import g3_gates  # noqa: E402
import g3_lexicon  # noqa: E402
import g3_request_builder as rb  # noqa: E402

PKG1 = Path(__file__).resolve().parent
GATE1 = ROOT / "controlled_content_generator_v2_001/gate1_v1_1_001"
P5 = GATE1 / "p5_p6_300_baseline_scale_and_freeze_001"

import os  # noqa: E402

ROUND = int(os.environ.get("PKG1_ROUND", "1"))
BATCH_ID = f"PKG1R{ROUND}"
_RD = PKG1 if ROUND == 1 else PKG1 / f"round{ROUND}"
# 场景基座跨轮冻结不变；round≥2 的请求/输出/审查/结果落在 round 子目录
SCENARIOS = PKG1 / "inputs/scenarios.g3.v1.jsonl"
REQUESTS = _RD / "inputs/requests.g3.v1.jsonl"
INPUT_FREEZE = _RD / "inputs/input_freeze.v1.yaml"
AUTHOR_RAW_DIR = _RD / "outputs/author_raw"
FIRST_OUTPUTS = _RD / "outputs/first_outputs.g3.v1.jsonl"
GATE_REPORT = _RD / "outputs/machine_gate_report.v1.json"
BLIND_PACKET = _RD / "review/blind/neutral_packet.v1.jsonl"
BLIND_MAPPING = _RD / "review/blind/neutral_mapping.v1.jsonl"
AUTHOR_INSTRUCTION = G3 / ("contract/g3_author_instruction.v2.0.md" if ROUND == 1
                           else "contract/g3_author_instruction.v2.1.md")
REVIEW_DIR = _RD / "review"
RESULT_DIR = _RD / "result"

G3_MODULES = [
    "g3_author_contract.py", "g3_lexicon.py", "g3_expression.py",
    "g3_fingerprint.py", "g3_similarity.py", "g3_request_builder.py",
    "g3_gates.py", "g3_route_driver.py", "g3_calibration.py",
]

MIDBATCH_320 = ROOT / ("07_microbatch_runs/scoped_content_microbatch_120_001"
                       "/midbatch_320_001/midbatch_320_generation_records.v0.1.jsonl")
REF29 = P5 / "production/reference_approved.v1.0.jsonl"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(contract.canonical_json(row) + "\n")


def frozen_corpus() -> dict[str, str]:
    """近原文复现冻结语料：320 中批 body（120 参考的超集，从严）+ 29 既有批准。"""
    corpus: dict[str, str] = {}
    for row in read_jsonl(MIDBATCH_320):
        corpus[f"MB320-{row['output_id']}"] = str(row["body"])
    for row in read_jsonl(REF29):
        corpus[f"REF29-{row['baseline_item_id']}"] = str(row["body_text"])
    return corpus


def authors_by_profile() -> dict[str, Any]:
    def author(cp: str, suffix: str) -> dict[str, str]:
        sid = f"G3-AUTHOR-SESSION-{BATCH_ID}-{cp}{suffix}"
        return {"author_identity": f"G3-AUTHOR-{BATCH_ID}-{cp}{suffix}",
                "author_session_logical_id": sid,
                "author_platform_agent_id": sid}
    if ROUND == 1:
        return {f"CP{n:02d}": author(f"CP{n:02d}", "") for n in range(1, 21)}
    # 第2轮起：每产品两名作者（前3条A、后3条B），打破单脑收敛
    return {f"CP{n:02d}": [author(f"CP{n:02d}", "-A"), author(f"CP{n:02d}", "-B")]
            for n in range(1, 21)}


def cmd_freeze_inputs() -> int:
    contract.require(not INPUT_FREEZE.exists(), "E_PKG1_ALREADY_FROZEN")
    scenarios = read_jsonl(SCENARIOS)
    contract.require(len(scenarios) == 120, "E_PKG1_SCENARIO_COUNT",
                     str(len(scenarios)))
    requests = rb.build_batch(
        scenarios, BATCH_ID, authors_by_profile(),
        sha256_file(AUTHOR_INSTRUCTION),
        AUTHOR_INSTRUCTION.relative_to(ROOT).as_posix(),
    )
    write_jsonl(REQUESTS, requests)
    # 每 CP 便利分片（内容与总文件一致，checker 复核）
    by_cp: dict[str, list[dict[str, Any]]] = {}
    for request in requests:
        by_cp.setdefault(request["profile_id"], []).append(request)
    for cp, rows in sorted(by_cp.items()):
        write_jsonl(_RD / f"inputs/requests_by_cp/{cp}.jsonl", rows)
    lines = [
        "schema: pkg1_open_regression_input_freeze.v1",
        f"task_id: {contract.TASK_ID}",
        f"batch_id: {BATCH_ID}",
        f"scenario_count: {len(scenarios)}",
        f"request_count: {len(requests)}",
        "coverage: 全部27条上一轮FRESH_TOPUP场景 + 全部28条套路场景 + 对照直批场景"
        " + CP08/CP13 全新补足场景（每产品6条）",
        f"scenarios_sha256: {sha256_file(SCENARIOS)}",
        f"requests_sha256: {sha256_file(REQUESTS)}",
        f"author_instruction_sha256: {sha256_file(AUTHOR_INSTRUCTION)}",
        "generator_modules:",
    ]
    for name in G3_MODULES:
        lines.append(f"  {name}: {sha256_file(G3 / name)}")
    lines += [
        "frozen_base_refs:",
        f"  active_ab_paths: {sha256_file(rb.AB_PATHS_FILE)}",
        f"  active_components: {sha256_file(rb.COMPONENTS_FILE)}",
        f"author_model_capability: {contract.MODEL_CAPABILITY}",
        f"author_reasoning_effort: {contract.REASONING_EFFORT}",
    ]
    INPUT_FREEZE.parent.mkdir(parents=True, exist_ok=True)
    INPUT_FREEZE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"FROZEN {len(requests)} requests; freeze manifest at {INPUT_FREEZE}")
    return 0


def _load_raws() -> tuple[list[dict[str, Any]], list[str]]:
    raws: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in sorted(AUTHOR_RAW_DIR.glob("raw.*.jsonl")):
        for index, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                raws.append(json.loads(line))
            except json.JSONDecodeError as error:
                errors.append(f"{path.name}:{index}:JSON:{error}")
    return raws, errors


def cmd_shape_check() -> int:
    requests = {r["request_id"]: r for r in read_jsonl(REQUESTS)}
    raws, errors = _load_raws()
    seen: set[str] = set()
    for raw in raws:
        rid = str(raw.get("request_id", "UNKNOWN"))
        if rid in seen:
            errors.append(f"{rid}:E_DUPLICATE_RAW")
            continue
        seen.add(rid)
        request = requests.get(rid)
        if request is None:
            errors.append(f"{rid}:E_UNKNOWN_REQUEST")
            continue
        try:
            contract.validate_raw(raw, request)
        except contract.AuthorContractError as error:
            errors.append(f"{rid}:{error}")
    missing = sorted(set(requests) - seen)
    print(f"raws={len(raws)} valid={len(raws) - len(errors)} "
          f"missing={len(missing)} errors={len(errors)}")
    for error in errors:
        print("ERR", error)
    for rid in missing:
        print("MISSING", rid)
    return 0 if not errors and not missing else 1


def cmd_gate() -> int:
    requests_list = read_jsonl(REQUESTS)
    requests = {r["request_id"]: r for r in requests_list}
    raws, errors = _load_raws()
    contract.require(not errors, "E_PKG1_RAW_JSON", ";".join(errors[:3]))
    outputs = []
    for raw in sorted(raws, key=lambda r: str(r["request_id"])):
        request = requests[str(raw["request_id"])]
        outputs.append(contract.serialize(raw, request))
    contract.require(len(outputs) == len(requests), "E_PKG1_OUTPUT_COUNT",
                     f"{len(outputs)}!={len(requests)}")
    write_jsonl(FIRST_OUTPUTS, outputs)
    report = g3_gates.gate_batch(outputs, requests_list, frozen_corpus())
    GATE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    GATE_REPORT.write_text(contract.canonical_json(report) + "\n", encoding="utf-8")
    print(f"outputs={report['output_count']} "
          f"machine_hard_fail={report['machine_hard_fail_count']}")
    return 0


def cmd_blind_packet() -> int:
    outputs = read_jsonl(FIRST_OUTPUTS)
    packet = []
    mapping = []
    rows = sorted(outputs,
                  key=lambda o: hashlib.sha256(
                      (str(o["output_digest"]) + f"{BATCH_ID}BLINDSALT").encode()
                  ).hexdigest())
    for index, output in enumerate(rows, 1):
        neutral_id = f"BLIND-{index:03d}"
        item = {
            "neutral_id": neutral_id,
            "title": output["title"],
            "body": output["body"],
            "spoken_lines": output["spoken_lines"],
            "cta": output["cta"],
            "visual_execution": output["visual_execution"],
            "audio_execution": output["audio_execution"],
        }
        leaks = []
        for text in [item["title"], *item["body"], *item["spoken_lines"],
                     item["cta"], *item["visual_execution"],
                     *item["audio_execution"]]:
            leaks += g3_lexicon.scan_label_leak(str(text))
        contract.require(not leaks, "E_PKG1_BLIND_LEAK",
                         f"{neutral_id}:{sorted(set(leaks))}")
        packet.append(item)
        mapping.append({"neutral_id": neutral_id,
                        "request_id": output["request_id"],
                        "profile_id": output["profile_id"]})
    write_jsonl(BLIND_PACKET, packet)
    write_jsonl(BLIND_MAPPING, mapping)
    print(f"blind packet {len(packet)} items, zero label leaks")
    return 0


def cmd_metrics() -> int:
    outputs = {o["request_id"]: o for o in read_jsonl(FIRST_OUTPUTS)}
    gate = json.loads(GATE_REPORT.read_text(encoding="utf-8"))
    gate_by_id = {row["request_id"]: row for row in gate["per_output"]}
    content: dict[str, dict[str, Any]] = {}
    for path in sorted((REVIEW_DIR).glob("content_review.*.jsonl")):
        for row in read_jsonl(path):
            content[str(row["request_id"])] = row
    fact: dict[str, dict[str, Any]] = {}
    for path in sorted((REVIEW_DIR).glob("fact_review.*.jsonl")):
        for row in read_jsonl(path):
            fact[str(row["request_id"])] = row
    blind_choices = {row["neutral_id"]: row
                     for row in read_jsonl(REVIEW_DIR / "blind_choices.v1.jsonl")}
    mapping = read_jsonl(BLIND_MAPPING)

    total = len(outputs)
    assert set(content) == set(outputs), "content review must cover 100%"
    assert set(fact) == set(outputs), "fact review must cover 100%"

    def acceptable(rid: str) -> bool:
        c = content[rid]
        f = fact[rid]
        machine_ok = not gate_by_id[rid]["machine_first_fail"]
        return (machine_ok and c["grade"] in ("A", "B")
                and not c["hard_error_codes"] and not f["hard_error_codes"]
                and f["fact_approved"])

    acceptable_ids = sorted(rid for rid in outputs if acceptable(rid))
    formulaic_ids = sorted(
        rid for rid in outputs if content[rid]["formulaic_or_near_duplicate"])
    hard_veto_ids = sorted(
        rid for rid in outputs
        if content[rid]["hard_error_codes"] or fact[rid]["hard_error_codes"]
        or gate_by_id[rid]["machine_first_fail"])
    per_cp_blind: dict[str, dict[str, int]] = {}
    blind_correct = 0
    for row in mapping:
        cp = row["profile_id"]
        choice = blind_choices[row["neutral_id"]]["blind_profile_choice"]
        entry = per_cp_blind.setdefault(cp, {"total": 0, "correct": 0})
        entry["total"] += 1
        if choice == cp:
            entry["correct"] += 1
            blind_correct += 1
    per_cp_acc: dict[str, dict[str, int]] = {}
    for rid, output in outputs.items():
        cp = str(output["profile_id"])
        entry = per_cp_acc.setdefault(cp, {"total": 0, "acceptable": 0})
        entry["total"] += 1
        if rid in acceptable_ids:
            entry["acceptable"] += 1

    # 上一轮基线（冻结证据重算）：CP01/06/07 盲判基线
    last_reviews: dict[str, dict[str, Any]] = {}
    for path in sorted((P5 / "review/production").glob("content.group_*.jsonl")):
        for row in read_jsonl(path):
            last_reviews[str(row["request_id"])] = row
    last_blind: dict[str, dict[str, int]] = {}
    for row in last_reviews.values():
        cp = row["profile_id"]
        entry = last_blind.setdefault(cp, {"total": 0, "correct": 0})
        entry["total"] += 1
        if row["blind_profile_choice"] == cp:
            entry["correct"] += 1

    rate = len(acceptable_ids) / total
    formulaic_rate = len(formulaic_ids) / total
    metrics = {
        "schema_version": "pkg1-open-regression-metrics-v1",
        "task_id": contract.TASK_ID,
        "batch_id": BATCH_ID,
        "formal_round": ROUND,
        "output_count": total,
        "first_acceptable_count": len(acceptable_ids),
        "first_acceptance_rate": round(rate, 6),
        "gate_first_acceptance": rate >= 0.90,
        "formulaic_count": len(formulaic_ids),
        "formulaic_rate": round(formulaic_rate, 6),
        "gate_formulaic": formulaic_rate <= 0.10,
        "hard_veto_approved_count": len(
            [r for r in hard_veto_ids if r in acceptable_ids]),
        "attempt_hard_or_machine_fail_count": len(hard_veto_ids),
        "gate_hard_veto_zero_in_acceptable": not any(
            r in acceptable_ids for r in hard_veto_ids),
        "blind_correct": blind_correct,
        "blind_total": len(mapping),
        "blind_rate": round(blind_correct / len(mapping), 6) if mapping else 0,
        "per_cp_blind": {cp: per_cp_blind[cp] for cp in sorted(per_cp_blind)},
        "per_cp_acceptance": {cp: per_cp_acc[cp] for cp in sorted(per_cp_acc)},
        "last_round_blind_baseline": {
            cp: last_blind.get(cp, {}) for cp in ("CP01", "CP06", "CP07")},
        "focus_cp_improvement": {
            cp: {
                "last_round": last_blind.get(cp, {}),
                "this_round": per_cp_blind.get(cp, {}),
                "improved": (
                    per_cp_blind.get(cp, {"correct": 0, "total": 1})["correct"]
                    / max(per_cp_blind.get(cp, {"total": 1})["total"], 1)
                    > last_blind.get(cp, {"correct": 0, "total": 1})["correct"]
                    / max(last_blind.get(cp, {"total": 1})["total"], 1)),
            }
            for cp in ("CP01", "CP06", "CP07")
        },
        "failed_ids_retained_in_denominator": sorted(
            set(outputs) - set(acceptable_ids)),
    }
    metrics["metrics_digest"] = contract.object_digest(metrics, "metrics_digest")
    out = RESULT_DIR / f"round{ROUND}_metrics.v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(contract.canonical_json(metrics) + "\n", encoding="utf-8")
    print(contract.canonical_json({k: metrics[k] for k in (
        "first_acceptance_rate", "gate_first_acceptance", "formulaic_rate",
        "gate_formulaic", "blind_rate", "focus_cp_improvement")}))
    return 0


COMMANDS = {
    "freeze-inputs": cmd_freeze_inputs,
    "shape-check": cmd_shape_check,
    "gate": cmd_gate,
    "blind-packet": cmd_blind_packet,
    "metrics": cmd_metrics,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print("usage: run_pkg1.py " + "|".join(COMMANDS))
        raise SystemExit(2)
    raise SystemExit(COMMANDS[sys.argv[1]]())
