#!/usr/bin/env python3
"""M3 胶囊⑤ QUAL-A/B 密封管线执行器（顺序硬门 + 保全纪律，可断点续跑）。

密封承载区：p7/sealed_custody_001/（gitignore 强制；明文零入 Git）。
编排会话（本工具的调用方）只见 stdout 的数量/摘要/回执；一切题面与标签
实体只落承载区。事件按 QUAL_ORDER_CONTRACT 六步前三步 ×2 集出带单调序号回执。

子命令（按序）：
  split        90 组池 → A/B 各 45（族内分层 + 难度平衡贪心配对，确定性种子）
  faces --set A|B     题面物化（自然 claims + 密封变体构造）→ 冻结回执 + 事件 ①
  label --set A|B --seat A|B [--max-batches N]   双盲建标（A=Codex/B=Fable 席位）
  labelfreeze --set A|B    建标完成回执 + 事件 ②
  adjudicate --set A|B [--max-batches N]         分歧裁决（密封）
  goldfreeze --set A|B     金标冻结：装配+密封+denylist 登记 + 事件 ③
  finalize     qual_order 全序校验 + qualification_manifest 物化 + 保全总回执
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
GOLD = HERE.parents[1]
M3DS = HERE.parents[2]
P7 = HERE.parents[3]
ANN = M3DS / "annotation"
PK = P7 / "pkg1_open_regression"
SPINE = P7 / "eval_audit_spine_001"
DCC = P7 / "delivery_control_001"
SEAL = P7 / "sealed_custody_001"          # gitignored 明文承载区
QOPEN = GOLD / "qual"                     # 开放证据区（回执/数量/摘要）
EVENTS = DCC / "state/QUAL_ORDER_EVENTS.v1.json"
REG = QOPEN / "SESSION_REGISTRY.v1.jsonl"
ANNEXC = ANN / "annotation_protocol_annexC_qual.v1.json"

sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(SPINE))
sys.path.insert(0, str(M3DS / "tools"))
import labeling_lib as L                  # noqa: E402
from spine.canonical import digest_json   # noqa: E402
import qual_gold_derivation as GD         # noqa: E402  §四.2 逐模块合规派生
import qual_generation as GEN             # noqa: E402  §四.4 真 generation 链
import qual_custody_recompute as CUS      # noqa: E402  §5.1 密封复算（class_counts 复用）

BATCH = 10
# R3-build §四.1：6 种 challenge kind（真源 = CAPACITY_AND_CONSTRUCTION_PLAN.variant_construction.kinds
# + annexC.challenge_kinds；此常量为文档/回退，实际数量由 plan 驱动 _build_variant_tasks）。
CHALLENGE_KINDS = ("CONTRADICTION_INJECT", "RISK_ELEVATE", "EVIDENCE_INSUFFICIENT",
                   "BOUNDARY_OMIT", "OMISSION_MISLEAD", "LEGAL_NEGATIVE_CONTROL")
# 旧冻结 generation（G2 等）用 HIGH_RISK_INJECT；新 generation 用 RISK_ELEVATE。
# 读旧变体时经此映射对齐语义，绝不回写旧冻结数据（annexC.legacy_kind_compat_map 真源）。
LEGACY_KIND_MAP = {"HIGH_RISK_INJECT": "RISK_ELEVATE"}
VARIANT_KINDS = CHALLENGE_KINDS  # 向后兼容旧引用名


def normalize_kind(kind: str) -> str:
    """把旧冻结 generation 的 legacy kind 映射到当前 6-kind 家族（只读向对齐，不回写旧数据）。"""
    return LEGACY_KIND_MAP.get(kind, kind)
ROUND_FILES = {
    "round1_top": ("inputs/requests.g3.v1.jsonl", "outputs/first_outputs.g3.v1.jsonl"),
    "round2": ("round2/inputs/requests.g3.v1.jsonl", "round2/outputs/first_outputs.g3.v1.jsonl"),
    "round3": ("round3/inputs/requests.g3.v1.jsonl", "round3/outputs/first_outputs.g3.v1.jsonl"),
    "round5": ("round5/inputs/requests.g3.v1.jsonl", "round5/outputs/first_outputs.g3.v1.jsonl"),
}


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _batch_ready(p: Path) -> bool:
    """真批文件就绪 = 存在且能解析为非空 JSON 数组。
    进程被杀会留下截断/空的 qvb_NNN.json；裸 exists() 会把它当已完成而永久跳过，
    故构造/续跑/组装三处一律用本判据（截断文件视为未完成，触发重建）。"""
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(data, list) and len(data) > 0


def assert_sealed_ignored() -> None:
    r = subprocess.run(["git", "-C", str(P7.parents[2]), "check-ignore",
                        str(SEAL / "probe")], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("STOP_DATA_LEAKAGE_RISK: sealed_custody_001 未被 gitignore 覆盖，拒绝任何密封写入")


def append_event(code: str, receipt_path: str) -> dict:
    events = json.loads(EVENTS.read_text(encoding="utf-8")) if EVENTS.is_file() else []
    if any(e["code"] == code for e in events):
        return next(e for e in events if e["code"] == code)
    ev = {"code": code, "seq": len(events) + 1, "at": now(),
          "receipt_path": receipt_path}
    events.append(ev)
    EVENTS.write_text(json.dumps(events, ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8")
    return ev


def _qual_pool_groups() -> list[dict]:
    part = json.loads((GOLD / "DEV_PARTITION.v1.json").read_text(encoding="utf-8"))
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    by_id = {g["scenario_id"]: g for g in frame["groups"]}
    return [by_id[s] for s in part["qual_pool_groups"]]


def cmd_split() -> int:
    frame_digest = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text())["frame_digest"]
    pool = _qual_pool_groups()
    per_fam: dict[str, list[dict]] = {}
    for g in pool:
        g["_claims"] = sum(i["claims_n"] for i in g["items"])
        per_fam.setdefault(g["family_id"], []).append(g)
    setA, setB = [], []
    for fam in sorted(per_fam):
        # 难度平衡：族内按 claims 数降序，贪心把当前组分给累计 claims 较少的一侧；
        # 平局用确定性哈希定向（分层随机等价面：序由 sha256(frame_digest+sid) 打散同额组）
        groups = sorted(per_fam[fam],
                        key=lambda g: (-g["_claims"], L.sha_text(frame_digest + "SPLIT" + g["scenario_id"])))
        ca = cb = 0
        na = nb = 0
        half = len(groups) // 2
        for g in groups:
            side_a = (ca < cb) or (ca == cb and L.sha_text(
                frame_digest + "TIE" + g["scenario_id"])[0] < "8")
            if na >= len(groups) - half:
                side_a = False
            if nb >= len(groups) - half + (len(groups) % 2):
                side_a = True
            if side_a:
                setA.append(g); ca += g["_claims"]; na += 1
            else:
                setB.append(g); cb += g["_claims"]; nb += 1
    def stat(s):
        return {"groups": len(s),
                "claims": sum(g["_claims"] for g in s),
                "per_family": dict(sorted(Counter(g["family_id"] for g in s).items()))}
    QOPEN.mkdir(parents=True, exist_ok=True)
    SEAL.mkdir(exist_ok=True)
    assert_sealed_ignored()
    membership = {"QUAL_A": sorted(g["scenario_id"] for g in setA),
                  "QUAL_B": sorted(g["scenario_id"] for g in setB)}
    assert not (set(membership["QUAL_A"]) & set(membership["QUAL_B"]))
    (SEAL / "membership.json").write_text(
        json.dumps(membership, ensure_ascii=False, indent=1), encoding="utf-8")
    receipt = {
        "schema_version": "p7-m3-qual-split-receipt-v1",
        "rule": "共同抽样框（SAMPLING_FRAME b20a9ae3）扣除 DEV 30 组后的 90 组池；族内分层 + 难度平衡贪心（难度代理=组 claims 数）+ 确定性平局哈希；两集互不相交",
        "at": now(),
        "QUAL_A": stat(setA), "QUAL_B": stat(setB),
        "disjoint": True,
        "balance_proof": {
            "claims_delta_abs": abs(stat(setA)["claims"] - stat(setB)["claims"]),
            "per_family_group_delta_max": max(
                abs(stat(setA)["per_family"].get(f, 0) - stat(setB)["per_family"].get(f, 0))
                for f in set(stat(setA)["per_family"]) | set(stat(setB)["per_family"])),
        },
        "membership_sha256": sha_file(SEAL / "membership.json"),
        "membership_location": "sealed_custody_001/membership.json（保全区；本回执只载数量/摘要）",
    }
    (QOPEN / "QUAL_SPLIT_RECEIPT.v1.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("QUAL_A", "QUAL_B", "balance_proof")},
                     ensure_ascii=False, indent=1))
    return 0


def _cases_for_set(set_id: str) -> list[dict]:
    membership = json.loads((SEAL / "membership.json").read_text(encoding="utf-8"))
    chosen = set(membership[f"QUAL_{set_id}"])
    scen = {s["scenario_id"]: s for s in jl(PK / "round5/inputs/scenarios.g3.v2.jsonl")}
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    fam = {g["scenario_id"]: g["family_id"] for g in frame["groups"]}
    cases = []
    for rname, (req_rel, out_rel) in ROUND_FILES.items():
        reqs = {r["request_id"]: r for r in jl(PK / req_rel)}
        for o in jl(PK / out_rel):
            sid = reqs[o["request_id"]]["scenario_id"]
            if sid not in chosen:
                continue
            s = scen[sid]
            for c in o.get("claims", []):
                cases.append({
                    "case_id": f"Q{set_id}-{rname}-{c['claim_id']}",
                    "case_kind": "NATURAL",
                    # §四.2 统计独立单位：source_group = claim 级（此自然 claim 自身）；
                    # 其挑战变体继承本 source_group（cmd_faces），同源变体不增有效 N（§六B）。
                    "source_group_id": f"Q{set_id}-{rname}-{c['claim_id']}",
                    "scenario_id": sid, "family_id": fam[sid], "round": rname,
                    "item_title": o.get("title", ""),
                    "claim_text": c["claim_text"],
                    "claim_boundary": c.get("claim_boundary", ""),
                    "authorization_scope": s.get("authorization_scope", ""),
                    "slot_facts": s.get("slot_facts", {}),
                    "source_summary_a": s.get("source_summary_a", ""),
                    "source_summary_b": s.get("source_summary_b", ""),
                })
    return cases


def _build_variant_tasks(by_fam: dict, frame_digest: str, plan: dict) -> list:
    """密封变体任务构造：per-class-target-driven, k>=2 变体/claim, 高风险偏置。

    替代 M3 v1 的 `take = max(10, int(0.4 * len(ranked)))` 固定 40% 比例缺陷
    （as-built ~206/199 变体、注释谎称 ~400、每 claim 单 kind）。改由
    CAPACITY_AND_CONSTRUCTION_PLAN 的 per-class 目标驱动数量、k>=2、按族供给分摊 +
    F5 保底。确定性（sha 序），零 0.4。R3 须同步对齐 annexC 构造模板以支持扩展 kinds。"""
    vc = plan["variant_construction"]
    if not vc.get("no_fixed_ratio"):
        raise SystemExit("variant_construction.no_fixed_ratio!=true；拒绝回退固定比例")
    k = int(vc["k_variants_per_claim"])
    if k < 2:
        raise SystemExit("k_variants_per_claim 必须 >=2（每 claim 至少两变体）")
    kinds = list(vc["kinds"])
    et = plan["per_set_module_targets"]["entailment"]
    hi_target = (et["high_risk_contradicted"]["target"]
                 + et["high_risk_unknown"]["target"])
    total = sum(len(v) for v in by_fam.values()) or 1
    tasks = []
    for famname in sorted(by_fam):
        ranked = sorted(by_fam[famname],
                        key=lambda c: L.sha_text(frame_digest + "QV" + c["case_id"]))
        share = len(ranked) / total
        claims_to_perturb = min(len(ranked),
                                max(8, -(-int(hi_target * share) // k)))  # F5 保底 8
        for c in ranked[:claims_to_perturb]:
            for kk in range(k):
                h = int(L.sha_text(frame_digest + c["case_id"] + str(kk))[:8], 16)
                kind = kinds[h % len(kinds)]
                tasks.append({"variant_id": f"V-{c['case_id']}-{kind[:4]}-{kk}",
                              "base_case_id": c["case_id"], "variant_kind": kind,
                              "base_claim_text": c["claim_text"],
                              "claim_boundary": c["claim_boundary"],
                              "authorization_scope": c["authorization_scope"],
                              "slot_facts": c["slot_facts"],
                              "source_summary_a": c["source_summary_a"],
                              "source_summary_b": c["source_summary_b"],
                              "family_id": c["family_id"]})
    return tasks


def cmd_faces(set_id: str, max_batches: int) -> int:
    assert_sealed_ignored()
    spec = json.loads(ANNEXC.read_text(encoding="utf-8"))
    cons_tmpl = spec["prompt_templates"]["qual_variant_constructor"]
    if L.sha_text(cons_tmpl["text"]) != cons_tmpl["sha256"]:
        raise SystemExit("annexC constructor template drift")
    sdir = SEAL / f"qual_{set_id}"
    sdir.mkdir(parents=True, exist_ok=True)
    natural = _cases_for_set(set_id)
    nat_path = sdir / "faces_natural.json"
    if not nat_path.exists():
        nat_path.write_text(json.dumps(natural, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    # 密封变体构造：per-class-target-driven, k>=2, 高风险偏置（替代固定 40%；
    # 见 CAPACITY_AND_CONSTRUCTION_PLAN.variant_construction）
    frame_digest = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text())["frame_digest"]
    plan_path = M3DS / "plan/CAPACITY_AND_CONSTRUCTION_PLAN.v1.json"
    if not plan_path.is_file():
        raise SystemExit("CAPACITY_AND_CONSTRUCTION_PLAN.v1 缺失；拒绝回退固定 0.4 比例（R2 前置）")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    by_fam: dict[str, list[dict]] = {}
    for c in natural:
        by_fam.setdefault(c["family_id"], []).append(c)
    tasks = _build_variant_tasks(by_fam, frame_digest, plan)
    (sdir / "variant_tasks.json").write_text(
        json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
    batches = [tasks[i:i + BATCH] for i in range(0, len(tasks), BATCH)]
    cdir = sdir / "variant_constructed"
    done = 0
    for i, batch in enumerate(batches):
        if done >= max_batches:
            break
        out_path = cdir / f"qvb_{i:03d}.json"
        if _batch_ready(out_path):
            continue
        expected = {t["variant_id"] for t in batch}

        def ok(rows: list) -> bool:
            return ({r.get("variant_id") for r in rows if isinstance(r, dict)} == expected
                    and all(r.get("variant_claim_text") for r in rows))

        prompt = cons_tmpl["text"].replace(
            "{batch_json}", json.dumps(batch, ensure_ascii=False, indent=1))
        rows = L.attempt_call(prompt, ok, cdir, f"qvb_{i:03d}", REG,
                              {"kind": f"QUAL{set_id}_VARIANT_CONSTRUCT",
                               "batch": f"qvb_{i:03d}",
                               "visible_material_count": len(expected),
                               "retention": "明文留存于保全区（gitignore）；registry 零内容"})
        if rows is None:
            print(f"FAILED faces {set_id} qvb_{i:03d}")
            continue
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        done += 1
        print(f"OK faces {set_id} qvb_{i:03d}")
    remaining = [i for i in range(len(batches))
                 if not _batch_ready(cdir / f"qvb_{i:03d}.json")]
    if remaining:
        print(json.dumps({"set": set_id, "variant_batches_remaining": remaining}))
        return 0
    # 全部构造完成 → 组装题面（faces = 自然 + 变体正文；构造意图另存 gold 侧，不入题面）
    # glob 精确到三位数字批号，排除同目录 qvb_NNN.raw.tryN.json 原始留存（否则拿原始串当字典）
    variants_faces, variant_intents = [], []
    for p in sorted(cdir.glob("qvb_[0-9][0-9][0-9].json")):
        for r in json.loads(p.read_text(encoding="utf-8")):
            t = next(t for t in tasks if t["variant_id"] == r["variant_id"])
            variants_faces.append({
                "case_id": r["variant_id"], "case_kind": "CHALLENGE_VARIANT",
                # §四.1：把 challenge kind 钉在题面（经 normalize_kind 对齐 6-kind 家族），
                # 供 pilot/审计核「六种 kind 各至少运行一次」（真源仍在 variant_intents_goldside）。
                "challenge_kind": normalize_kind(r.get("variant_kind", t["variant_kind"])),
                # §四.2 统计独立单位：变体继承 base claim 的 source_group（同源变体不增有效 N，§六B）。
                "source_group_id": t["base_case_id"],
                "scenario_id": t["base_case_id"], "family_id": t["family_id"],
                "item_title": "", "claim_text": r["variant_claim_text"],
                "claim_boundary": t["claim_boundary"],
                "authorization_scope": t["authorization_scope"],
                "slot_facts": t["slot_facts"],
                "source_summary_a": t["source_summary_a"],
                "source_summary_b": t["source_summary_b"]})
            variant_intents.append({"variant_id": r["variant_id"],
                                    "variant_kind": r.get("variant_kind", t["variant_kind"]),
                                    "intended_risk": r.get("intended_risk"),
                                    "intended_entailment": r.get("intended_entailment"),
                                    "construction_note": r.get("construction_note", "")})
    faces = natural + variants_faces
    faces_path = sdir / "faces_frozen.json"
    faces_path.write_text(json.dumps(faces, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    (sdir / "variant_intents_goldside.json").write_text(
        json.dumps(variant_intents, ensure_ascii=False, indent=1), encoding="utf-8")
    batches_dir = sdir / "face_batches"
    batches_dir.mkdir(exist_ok=True)
    fb = [faces[i:i + BATCH] for i in range(0, len(faces), BATCH)]
    for i, b in enumerate(fb):
        (batches_dir / f"fb_{i:03d}.json").write_text(
            json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    receipt = {
        "schema_version": "p7-m3-qual-face-freeze-receipt-v1",
        "set": f"QUAL_{set_id}", "at": now(),
        "natural_cases": len(natural), "challenge_variants": len(variants_faces),
        "faces_total": len(faces), "face_batches": len(fb),
        "per_family": dict(sorted(Counter(c["family_id"] for c in faces).items())),
        "per_kind": dict(sorted(Counter(c["case_kind"] for c in faces).items())),
        "per_challenge_kind": dict(sorted(Counter(
            c["challenge_kind"] for c in faces if c.get("challenge_kind")).items())),
        "faces_sha256": sha_file(faces_path),
        "faces_location": f"sealed_custody_001/qual_{set_id}/faces_frozen.json（保全区）",
        "intents_sha256": sha_file(sdir / "variant_intents_goldside.json"),
    }
    rpath = QOPEN / f"QUAL_{set_id}_FACE_FROZEN_RECEIPT.v1.json"
    rpath.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    ev = append_event(f"{set_id}1_FACE_FROZEN",
                      f"m3_data_supply_001/gold/qual/{rpath.name}")
    print(json.dumps({"faces_total": len(faces), "natural": len(natural),
                      "variants": len(variants_faces), "event": ev["code"],
                      "seq": ev["seq"], "faces_sha256": receipt["faces_sha256"][:16]},
                     ensure_ascii=False))
    return 0


def _rich_rows_ok(rows: list, expected: set) -> bool:
    """富标签批合格判据：覆盖全部 case_id 且每条经 GD.validate_rich_label（九模块字段齐全合法）。"""
    if not isinstance(rows, list):
        return False
    if {r.get("case_id") for r in rows if isinstance(r, dict)} != expected:
        return False
    for r in rows:
        try:
            GD.validate_rich_label(r, where=str(r.get("case_id")))
        except GD.DerivationError:
            return False
    return True


def cmd_label(set_id: str, seat: str, max_batches: int) -> int:
    assert_sealed_ignored()
    carrier = "codex" if seat == "A" else "claude"
    # §四.1：富标签路径——九模块金标字段（旧二字段 labeler 保留供已冻结 G2，不在新 generation 用）。
    tmpl = L.load_template(ANNEXC, "qual_rich_labeler")
    sdir = SEAL / f"qual_{set_id}"
    out_dir = sdir / f"labels_{seat}"
    done = 0
    batch_files = sorted((sdir / "face_batches").glob("fb_*.json"))
    for bpath in batch_files:
        if done >= max_batches:
            break
        out_path = out_dir / (bpath.stem + ".labels.json")
        if _batch_ready(out_path):
            continue
        cases = json.loads(bpath.read_text(encoding="utf-8"))
        slim = [{k: c[k] for k in ("case_id", "claim_text", "claim_boundary",
                                   "authorization_scope", "slot_facts",
                                   "source_summary_a", "source_summary_b", "item_title")}
                for c in cases]
        expected = {c["case_id"] for c in cases}

        def ok(rows: list) -> bool:
            return _rich_rows_ok(rows, expected)

        seat_label = "A(Codex-GPT)" if seat == "A" else seat
        prompt = tmpl.replace("{seat}", seat_label).replace(
            "{batch_json}", json.dumps(slim, ensure_ascii=False, indent=1))
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = L.attempt_call(prompt, ok, out_dir, bpath.stem, REG,
                              {"kind": f"QUAL{set_id}_LABEL", "seat": seat,
                               "batch": bpath.stem,
                               "visible_material_count": len(expected),
                               "retention": "标签明文留存保全区；registry 零内容"},
                              carrier=carrier)
        if rows is None:
            (out_dir / (bpath.stem + ".FAILED")).write_text("", encoding="utf-8")
            print(f"FAILED {set_id}/{seat} {bpath.stem}")
            continue
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        done += 1
        print(f"OK {set_id}/{seat} {bpath.stem}")
    remaining = sum(1 for p in batch_files
                    if not (out_dir / (p.stem + ".labels.json")).exists())
    print(json.dumps({"set": set_id, "seat": seat, "remaining": remaining}))
    return 0


def _seal_collect(set_id: str, sub: str) -> dict[str, dict]:
    out = {}
    d = SEAL / f"qual_{set_id}" / sub
    if d.is_dir():
        for p in sorted(d.glob("*.labels.json")):
            for r in json.loads(p.read_text(encoding="utf-8")):
                out[r["case_id"]] = r
    return out


def _rich_key(label: dict) -> tuple:
    """富标签的可比较键（全九模块字段）——用于双盲一致/分歧判定与摘要。"""
    return (
        label.get("risk"), label.get("entailment"),
        label.get("reference_present"),
        digest_json(label.get("reference_attributes")),
        label.get("atom_present"), digest_json(label.get("atom_partition")),
        label.get("safe_to_clear"), label.get("disclosure_obligation"),
        label.get("disclosure_violation"), label.get("misleading"))


def cmd_labelfreeze(set_id: str) -> int:
    sdir = SEAL / f"qual_{set_id}"
    faces = json.loads((sdir / "faces_frozen.json").read_text(encoding="utf-8"))
    a, b = _seal_collect(set_id, "labels_A"), _seal_collect(set_id, "labels_B")
    total = len(faces)
    both = len(set(a) & set(b))
    if both < total:
        raise SystemExit(f"labelfreeze 拒绝：双席完成 {both}/{total}")
    # §四.1 富标签双盲：任一九模块金标字段不一致即分歧（走裁决）。
    disputes = sum(1 for cid in set(a) & set(b)
                   if _rich_key(a[cid]) != _rich_key(b[cid]))
    receipt = {
        "schema_version": "p7-m3-qual-doubleblind-receipt-v1",
        "set": f"QUAL_{set_id}", "at": now(),
        "faces_total": total, "labeled_both_seats": both,
        "seats": "A=Codex-GPT(gpt-5.6-sol) / B=Opus-4.8（跨模型双盲；载体裁决 seq41）",
        "label_schema": "rich_nine_module (qual_rich_labeler)",
        "dispute_count": disputes,
        "dispute_rate": round(disputes / max(1, both), 4),
        "labels_A_sha256": digest_json(sorted(
            (k, _rich_key(v)) for k, v in a.items())),
        "labels_B_sha256": digest_json(sorted(
            (k, _rich_key(v)) for k, v in b.items())),
        "location": f"sealed_custody_001/qual_{set_id}/labels_*（保全区）",
    }
    rpath = QOPEN / f"QUAL_{set_id}_DOUBLE_BLIND_RECEIPT.v1.json"
    rpath.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    ev = append_event(f"{set_id}2_DOUBLE_BLIND_LABELED",
                      f"m3_data_supply_001/gold/qual/{rpath.name}")
    print(json.dumps({"labeled": both, "disputes": disputes,
                      "event": ev["code"], "seq": ev["seq"]}, ensure_ascii=False))
    return 0


_RICH_FIELDS = GD.RICH_LABEL_FIELDS + ("rationale",)


def cmd_adjudicate(set_id: str, max_batches: int) -> int:
    assert_sealed_ignored()
    # §四.1 富标签裁决：隔离仲裁席对九模块字段分歧裁断（旧二字段 adjudicator 保留供 G2）。
    tmpl = L.load_template(ANNEXC, "qual_rich_adjudicator")
    sdir = SEAL / f"qual_{set_id}"
    faces = {c["case_id"]: c for c in json.loads(
        (sdir / "faces_frozen.json").read_text(encoding="utf-8"))}
    a, b = _seal_collect(set_id, "labels_A"), _seal_collect(set_id, "labels_B")
    disputes = []
    for cid in sorted(set(a) & set(b)):
        if _rich_key(a[cid]) != _rich_key(b[cid]):
            c = faces[cid]
            disputes.append({"case_id": cid,
                             **{k: c[k] for k in ("claim_text", "claim_boundary",
                                                  "authorization_scope", "slot_facts",
                                                  "source_summary_a", "source_summary_b")},
                             "label_jia": {k: a[cid].get(k) for k in _RICH_FIELDS},
                             "label_yi": {k: b[cid].get(k) for k in _RICH_FIELDS}})
    adir = sdir / "adjudication"
    adir.mkdir(exist_ok=True)
    (adir / "disputes.json").write_text(
        json.dumps(disputes, ensure_ascii=False, indent=1), encoding="utf-8")
    batches = [disputes[i:i + BATCH] for i in range(0, len(disputes), BATCH)]
    done = 0
    for i, batch in enumerate(batches):
        if done >= max_batches:
            break
        out_path = adir / f"adj_{i:03d}.labels.json"
        if out_path.exists():
            continue
        expected = {c["case_id"] for c in batch}

        def ok(rows: list) -> bool:
            return _rich_rows_ok(rows, expected)

        prompt = tmpl.replace("{batch_json}",
                              json.dumps(batch, ensure_ascii=False, indent=1))
        rows = L.attempt_call(prompt, ok, adir, f"adj_{i:03d}", REG,
                              {"kind": f"QUAL{set_id}_ADJUDICATE", "batch": f"adj_{i:03d}",
                               "visible_material_count": len(expected),
                               "retention": "明文留存保全区"})
        if rows is None:
            print(f"FAILED {set_id} adj_{i:03d}")
            continue
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        done += 1
        print(f"OK {set_id} adj_{i:03d}")
    remaining = sum(1 for i in range(len(batches))
                    if not (adir / f"adj_{i:03d}.labels.json").exists())
    print(json.dumps({"set": set_id, "disputes": len(disputes),
                      "adj_remaining": remaining}))
    return 0


def _seat_provenance(cid: str, adjudicated: bool, labeler_pd: str,
                     adj_pd: str) -> list[dict]:
    """本 face（或单元）的席位溯源：A=Codex-GPT / B=Opus-4.8（+ ADJ 隔离仲裁席，若裁决）。

    >=2 条互异身份满足 validate_qualification_records 的双独立评审门；AI 席须 model_revision +
    prompt_digest（labeler/adjudicator 模板 sha 摘要，绑定实际标注/裁决 prompt）。
    """
    sp = [{"tag": "A", "reviewer_identity": "SEAT_A::codex-gpt", "reviewer_kind": "AI",
           "model_revision": "gpt-5.6-sol", "prompt_digest": labeler_pd},
          {"tag": "B", "reviewer_identity": "SEAT_B::opus-4-8", "reviewer_kind": "AI",
           "model_revision": "claude-opus-4-8", "prompt_digest": labeler_pd}]
    if adjudicated:
        sp.append({"tag": "ADJ", "reviewer_identity": "ADJ::opus-4-8-isolated",
                   "reviewer_kind": "AI", "model_revision": "claude-opus-4-8",
                   "prompt_digest": adj_pd})
    return sp


def cmd_goldfreeze(set_id: str) -> int:
    """§四.2：逐 case 经 assemble_gold_record 派生**逐模块验证器合规**金标记录（含 cross-module
    reuse 登记 + 真 generation 链），取代旧简化非合规写入路径（risk+entailment 二字段、无摘要闭包）。
    """
    assert_sealed_ignored()
    sdir = SEAL / f"qual_{set_id}"
    faces = json.loads((sdir / "faces_frozen.json").read_text(encoding="utf-8"))
    a, b = _seal_collect(set_id, "labels_A"), _seal_collect(set_id, "labels_B")
    adj = _seal_collect(set_id, "adjudication")

    # 1) 逐 face 解析富标签（一致→A席，分歧→裁决席；缺席位或缺裁决→未决 fail-closed）。
    resolved: dict[str, dict] = {}
    adjudicated_ids: set[str] = set()
    unresolved: list[str] = []
    for c in faces:
        cid = c["case_id"]
        ra, rb = a.get(cid), b.get(cid)
        if not ra or not rb:
            unresolved.append(cid)
            continue
        if _rich_key(ra) == _rich_key(rb):
            resolved[cid] = ra
        elif cid in adj:
            resolved[cid] = adj[cid]
            adjudicated_ids.add(cid)
        else:
            unresolved.append(cid)
    if unresolved:
        raise SystemExit(f"goldfreeze 拒绝：未决 {len(unresolved)} 条（缺席位标签或缺裁决）")

    # 2) dataset_manifest_digest + generation_id（确定性绑 faces 内容）。
    faces_sha = sha_file(sdir / "faces_frozen.json")
    generation_id = f"QUAL_{set_id}_GEN_{faces_sha[:16]}"
    dmd = digest_json({"set": set_id, "faces_sha256": faces_sha,
                       "generation": generation_id})
    labeler_pd = digest_json({"tmpl": "qual_rich_labeler",
                              "sha": L.sha_text(L.load_template(ANNEXC, "qual_rich_labeler"))})
    adj_pd = digest_json({"tmpl": "qual_rich_adjudicator",
                          "sha": L.sha_text(L.load_template(ANNEXC, "qual_rich_adjudicator"))})

    def sp_for(record_cid: str) -> list[dict]:
        face_cid = record_cid.split("::")[0] if "::" in record_cid else record_cid
        # review::item::rv 与 form-*::pair::rv 的 face_cid 头段不是 per-claim face；
        # 其席位溯源统一为 A/B（review/formulaic 单元自带内部 reviewer_id，另与席位正交）。
        return _seat_provenance(face_cid, face_cid in adjudicated_ids, labeler_pd, adj_pd)

    # 3) 逐 claim 七模块派生 + cross-module reuse 登记。
    der = GD.derive_perclaim_records(faces, resolved, dataset_manifest_digest=dmd,
                                     seat_provenance_for=sp_for)
    records = list(der["records"])
    cross_module_reuse = der["cross_module_reuse"]

    # 4) review_calibration / formulaic：读密封解析单元（若在场；由 review/formulaic 子管线产出）。
    review_units_path = sdir / "review_units.json"
    formulaic_units_path = sdir / "formulaic_units.json"
    review_count = formulaic_count = 0
    if review_units_path.is_file():
        ru = json.loads(review_units_path.read_text(encoding="utf-8"))
        rrecs = GD.derive_review_records(ru, dataset_manifest_digest=dmd,
                                         seat_provenance_for=sp_for)
        records.extend(rrecs)
        review_count = len(rrecs)
    if formulaic_units_path.is_file():
        fu = json.loads(formulaic_units_path.read_text(encoding="utf-8"))
        frecs = GD.derive_formulaic_records(fu, dataset_manifest_digest=dmd,
                                            seat_provenance_for=sp_for,
                                            batch_id=f"QUAL_{set_id}_R3")
        for k in ("judgments", "adjudications", "candidate_audit"):
            records.extend(frecs[k])
            formulaic_count += len(frecs[k])
        (sdir / "formulaic_registries.json").write_text(
            json.dumps({k: frecs[k] for k in ("candidate_manifest", "rubric_manifest",
                                              "necessary_grammar_exceptions")},
                       ensure_ascii=False, indent=1), encoding="utf-8")

    # 5) 密封合规金标记录落盘（永不入 Git；gitignore 已核）。
    gold_path = sdir / "gold_records.json"
    gold_path.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    gold_sha = sha_file(gold_path)

    # 6) 真 generation 链（pointer→manifest→index；index 仅 case_id+摘要，无明文答案）。
    gen = GEN.build_generation(records, set_id=set_id, generation_id=generation_id,
                               dataset_manifest_digest=dmd, faces_sha256=faces_sha,
                               gold_sha256=gold_sha, qual_dir=QOPEN)

    # 7) 密封摘要 denylist 登记（撞库扫描输入）。
    deny_path = DCC / "state/SEALED_PAYLOAD_DENYLIST.v1.json"
    deny = json.loads(deny_path.read_text(encoding="utf-8"))
    for sha, kind in ((faces_sha, f"QUAL_{set_id}_FACES"), (gold_sha, f"QUAL_{set_id}_GOLD")):
        if not any(e["sha256"] == sha for e in deny["entries"]):
            deny["entries"].append({"sha256": sha, "kind": kind,
                                    "note": f"M3 密封载荷（sealed_custody_001/qual_{set_id}）；登记于 goldfreeze"})
    deny_path.write_text(json.dumps(deny, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")

    # 8) class_counts 由 custody 复算（与就绪门同口径，杜绝手算漂移）。
    pc = CUS.recompute_public_counts(
        records, set_id=set_id, active_generation_id=generation_id,
        dataset_manifest_digest=dmd, faces_sha256=faces_sha, gold_sha256=gold_sha)
    receipt = {
        "schema_version": "p7-m3-qual-gold-freeze-receipt-v2",
        "set": f"QUAL_{set_id}", "at": now(),
        "generation_id": generation_id,
        "gold_record_count": len(records),
        "resolved_faces": len(resolved),
        "adjudicated_faces": len(adjudicated_ids),
        "review_records": review_count, "formulaic_records": formulaic_count,
        "class_counts_recomputed": pc["counts"],
        "module_gold_field_coverage": pc["module_gold_field_coverage"],
        "obligation_types_present": pc["deterministic_disclosure_obligation_types_present"],
        "per_family": dict(sorted(Counter(
            f for f in (r.get("family_id") for r in records) if f).items())),
        "cross_module_reuse_source_groups": len(cross_module_reuse),
        "cross_module_reuse_digest": digest_json(cross_module_reuse),
        "core_validation_passed": pc["custody_binding"]["core_validation_passed"],
        "gold_sha256": gold_sha, "faces_sha256": faces_sha,
        "dataset_manifest_digest": dmd,
        "qualification_index_digest": pc["custody_binding"]["qualification_index_digest"],
        "sealed_denylist_registered": True,
        "location": f"sealed_custody_001/qual_{set_id}/gold_records.json（保全区；永不入 Git）",
        "custodian_view": "本回执仅数量/摘要；编排会话零接触明文（工具 stdout 纪律）",
    }
    (sdir / "cross_module_reuse.json").write_text(
        json.dumps(cross_module_reuse, ensure_ascii=False, indent=1), encoding="utf-8")
    rpath = QOPEN / f"QUAL_{set_id}_GOLD_FROZEN_RECEIPT.v2.json"
    rpath.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    ev = append_event(f"{set_id}3_GOLD_FROZEN",
                      f"m3_data_supply_001/gold/qual/{rpath.name}")
    print(json.dumps({"gold_records": len(records), "generation_id": generation_id,
                      "core_validation_passed": receipt["core_validation_passed"],
                      "counts": pc["counts"], "event": ev["code"], "seq": ev["seq"],
                      "gold_sha256": gold_sha[:16]}, ensure_ascii=False, indent=1))
    return 0 if receipt["core_validation_passed"] else 1


def cmd_finalize() -> int:
    events = json.loads(EVENTS.read_text(encoding="utf-8"))
    r = subprocess.run([sys.executable, str(DCC / "tools/qual_order.py")],
                       input=json.dumps(events), capture_output=True, text=True)
    verdict = json.loads(r.stdout)
    if verdict["verdict"] != "PASS":
        raise SystemExit(f"STOP_QUALIFICATION_ORDER_VIOLATION: {verdict['violations']}")
    # sealed_scan 撞库（当前树 + 历史）
    scan = subprocess.run([sys.executable, str(DCC / "tools/sealed_scan.py")],
                          capture_output=True, text=True)
    scan_out = scan.stdout.strip().splitlines()[-1] if scan.stdout.strip() else ""
    ra = json.loads((QOPEN / "QUAL_A_GOLD_FROZEN_RECEIPT.v1.json").read_text())
    rb = json.loads((QOPEN / "QUAL_B_GOLD_FROZEN_RECEIPT.v1.json").read_text())
    # qualification_manifest 物化
    mpath = SPINE / "calibration/qualification_manifest.v1.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    manifest["content_status"] = "MATERIALIZED"
    manifest["case_count"] = ra["gold_count"] + rb["gold_count"]
    manifest["class_counts"] = {"QUAL_A": ra["class_counts"], "QUAL_B": rb["class_counts"]}
    manifest["dataset_manifest_digest"] = digest_json(
        {"A_faces": ra["faces_sha256"], "B_faces": rb["faces_sha256"]})
    manifest["source_manifest_digest"] = json.loads(
        (QOPEN / "QUAL_SPLIT_RECEIPT.v1.json").read_text())["membership_sha256"]
    manifest["gold_manifest_digest"] = digest_json(
        {"A_gold": ra["gold_sha256"], "B_gold": rb["gold_sha256"]})
    manifest["record_manifest_digests"] = {
        "A_double_blind": sha_file(QOPEN / "QUAL_A_DOUBLE_BLIND_RECEIPT.v1.json"),
        "B_double_blind": sha_file(QOPEN / "QUAL_B_DOUBLE_BLIND_RECEIPT.v1.json"),
    }
    manifest["qualification_record_index_digest"] = digest_json(
        [e for e in events])
    manifest["leakage_status"] = "SEALED_NO_REVEAL"
    manifest["notes"] = [
        "M3-C5 物化：QUAL-A/B 双密封（题面冻结→跨模型双盲建标→金标冻结，每步带单调序号回执）",
        "明文全部留 sealed_custody_001（gitignore + denylist 撞库扫描）；本 manifest 只载数量/摘要",
        "揭晓步（A6/B6）属 M4+；本里程碑零揭晓、零方法冻结",
    ]
    unsigned = dict(manifest)
    unsigned.pop("manifest_digest", None)
    manifest["manifest_digest"] = digest_json(unsigned)
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    custody = {
        "schema_version": "p7-m3-sealed-custody-receipt-v1",
        "at": now(),
        "qual_order_verdict": verdict,
        "sealed_scan_tail": scan_out,
        "sets": {"QUAL_A": {"gold": ra["gold_count"], "gold_sha256": ra["gold_sha256"]},
                 "QUAL_B": {"gold": rb["gold_count"], "gold_sha256": rb["gold_sha256"]}},
        "custodian_discipline": "编排会话全程只见数量/摘要/回执（registry visible_material_count 零内容清单）；明文承载区 gitignore + denylist 撞库；接触明文的 headless 会话逐叫登记（thread/session id + ephemeral/无记忆）",
        "cost": L.registry_cost(REG),
    }
    (QOPEN / "SEALED_CUSTODY_RECEIPT.v1.json").write_text(
        json.dumps(custody, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"qual_order": verdict["verdict"],
                      "manifest_cases": manifest["case_count"],
                      "manifest_digest": manifest["manifest_digest"][:16],
                      "sealed_scan": scan_out[:120]}, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("split")
    for name in ("faces", "labelfreeze", "goldfreeze"):
        p = sub.add_parser(name)
        p.add_argument("--set", choices=["A", "B"], required=True)
        if name == "faces":
            p.add_argument("--max-batches", type=int, default=99)
    lp = sub.add_parser("label")
    lp.add_argument("--set", choices=["A", "B"], required=True)
    lp.add_argument("--seat", choices=["A", "B"], required=True)
    lp.add_argument("--max-batches", type=int, default=99)
    adp = sub.add_parser("adjudicate")
    adp.add_argument("--set", choices=["A", "B"], required=True)
    adp.add_argument("--max-batches", type=int, default=99)
    sub.add_parser("finalize")
    args = ap.parse_args()
    if args.cmd == "split":
        return cmd_split()
    if args.cmd == "faces":
        return cmd_faces(args.set, args.max_batches)
    if args.cmd == "label":
        return cmd_label(args.set, args.seat, args.max_batches)
    if args.cmd == "labelfreeze":
        return cmd_labelfreeze(args.set)
    if args.cmd == "adjudicate":
        return cmd_adjudicate(args.set, args.max_batches)
    if args.cmd == "goldfreeze":
        return cmd_goldfreeze(args.set)
    if args.cmd == "finalize":
        return cmd_finalize()
    return 2


if __name__ == "__main__":
    sys.exit(main())
