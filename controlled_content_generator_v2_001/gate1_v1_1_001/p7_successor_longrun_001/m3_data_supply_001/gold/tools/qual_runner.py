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
import qual_review_formulaic as RF        # noqa: E402  §六 review/formulaic 真子管线（全量生产）

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


DISCLOSURE_FAMS = ("F1_PEOPLE_AND_REAL_SCENE", "F2_PROFESSIONAL_AND_SEARCH",
                   "F3_PRODUCT_RELATION_AND_AESTHETIC", "F4_STORE_LOCAL_AND_RETAIL",
                   "F5_ENTERPRISE_LONG_TERM_TRUST")
# §六 build-4 确定性 disclosure 覆盖。disclosure obligation 按 rubric
# (disclosure_obligation_matrix.v1：SYNTHETIC_IDENTITY_AND_NO_IMPERSONATION_REMAIN_DETERMINISTIC)
# 是**确定性触发**：给定明确 trigger 内容，对应义务必然成立。旧路径靠标注员对普通 face 有机标出
# obligation → 脆弱（新证据锚 faces 不涉披露 → 0 覆盖，pilot nine_modules 失守）。build-4：确定性构造
# 无歧义触发 4 义务类型的**行业通用** face（不涉真品牌/真顾客真事实——案例为构造演示），走同一真 AI
# 双席标注管线 → obligation 被真席标出 → 派生真 disclosure 记录（非硬写 label，非假绿）。trigger 只落
# claim_text/slot_facts 的**事实陈述**，绝不写 obligation enum 名（防泄漏偏置标注独立性）。
_DISCLOSURE_TEMPLATES = (
    ("SYNTHETIC_IDENTITY_DISCLOSURE",
     "这条秋冬穿搭讲解视频由本店人工智能合成的虚拟数字主播出镜，全程以真人口吻讲解并与观众互动，"
     "页面与视频内均未任何标注该出镜形象为合成的虚拟身份。",
     "判定该内容就『出镜者为合成虚拟身份』一事是否负有向读者披露的义务及是否违反",
     ["出镜讲解者为人工智能合成的虚拟数字主播", "页面与视频均未标注其为合成虚拟身份"]),
    ("PROHIBITED_REAL_IDENTITY_IMPERSONATION",
     "这篇种草文以某位当红女明星『本人亲测、每天都穿这件』的第一人称口吻撰写推荐语，实际并未获得"
     "该公众人物任何授权，系门店文案单方面虚构其为品牌代言人。",
     "判定该内容就『假冒真实公众人物身份代言』一事是否负有义务及是否违反",
     ["以某真实公众人物第一人称口吻撰写代言推荐", "未获该公众人物任何授权，系文案虚构代言"]),
    ("EXPLICIT_AUTHORIZATION_BOUNDARY",
     "该素材获授权的范围明确仅限门店内部陈列图文使用；但发布方却以品牌总部官方名义对外发布面向"
     "全国消费者的统一售后与退换承诺，超出被授权的内容用途与主体范围。",
     "判定该内容就『发布主体与用途超出显式授权边界』一事是否负有义务及是否违反",
     ["授权范围仅限门店内部陈列图文使用", "实际以总部名义对外发布全国统一售后承诺"]),
    ("PRIVACY_REDACTION_OR_BLOCK",
     "这条成交案例分享中直接展示了一位到店顾客的真实姓名、完整手机号码与消费小票截图，未做任何"
     "隐私打码或脱敏处理即公开发布（案例为合规演示构造，非真实顾客数据）。",
     "判定该内容就『公开发布个人隐私信息前须打码/拦截』一事是否负有义务及是否违反",
     ["展示到店顾客真实姓名、手机号与消费小票截图", "未做任何隐私打码或脱敏即公开发布"]),
)


# 正式 R3-run 每义务类型 face 数：ceil(100/4)=25 达 disclosure_case≥100/套下限，+3 冗余防个别标注 miss。
DISCLOSURE_PER_TYPE = 28


def build_disclosure_faces(set_id: str, per_type: int = 1) -> list[dict]:
    """§六 build-4：确定性构造 disclosure obligation-triggering faces（4 义务类型 × per_type）。

    每 face 独立合成证据锚（distinct source_group cluster，不复用/不膨胀他类 N）；case_kind=NATURAL
    （披露义务生于真实内容，非挑战注入）；行业通用、不涉真品牌/真顾客真事实。真 AI 双席标注这些 face →
    obligation 被标出 → GD.derive_records_for_face 在 disclosure_obligation!=NONE 时派生真 disclosure 记录。
    per_type：pilot 用 1（模块覆盖即可，obligation 类型数 pilot scale 豁免）；正式用 ≥ ceil(合同下限/4)。
    """
    faces: list[dict] = []
    n = 0
    for obl, claim, boundary, slot_facts in _DISCLOSURE_TEMPLATES:
        for k in range(per_type):
            sid = f"DISC-{set_id}-{obl[:6]}-{k:03d}"
            src_ids = [f"{sid}-SRC1", f"{sid}-SRC2"]
            fact_ids = [f"{sid}-FACT1"]
            auth_ids = [f"{sid}-AUTH1"]
            sg = GD.evidence_anchor_digest(sid, src_ids, fact_ids, auth_ids)
            face = {
                "case_id": f"Q{set_id}-DISC-{obl[:6]}-{k:03d}",
                "case_kind": "NATURAL",
                "source_group_id": sg, "scenario_id": sid,
                "family_id": DISCLOSURE_FAMS[n % len(DISCLOSURE_FAMS)],
                "claim_text": (claim if per_type == 1 else f"{claim}（合规演示案例 {k + 1}）"),
                "claim_boundary": boundary,
                "authorization_scope": "内容合规审核授权：判定该 claim 触发的披露义务及是否违反",
                "slot_facts": list(slot_facts),
                "source_summary_a": "内容合规样例来源 A（行业通用构造演示，非真实品牌/顾客数据）",
                "source_summary_b": "内容合规样例来源 B（行业通用构造演示，非真实品牌/顾客数据）",
                "item_title": "", "source_ids": src_ids, "fact_ids": fact_ids,
                "authorization_ids": auth_ids,
                # disclosure 专用 face：只产 disclosure 记录，不冒充其他模块独立证据
                # （防模板化 face 伪膨胀 risk/entailment 等模块有效 cluster N → 伪独立假绿）。
                "disclosure_only": True}
            face["frozen_input_face_digest"] = GD.frozen_input_face_digest(face)
            faces.append(face)
            n += 1
    return faces


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


def _membership_path() -> Path:
    """发起人裁决：优先读证据锚均衡的 membership v2；缺则回退 v1（旧件保全不覆盖）。"""
    v2 = SEAL / "membership_v2.json"
    return v2 if v2.exists() else SEAL / "membership.json"


def _anchors_by_scenario() -> dict:
    """结构化只读：每 qual-pool scenario 的 {family, distinct evidence anchors}（跨轮）。
    编排会话零明文——只出 scenario_id/family/anchor 摘要，不出题面。"""
    part = json.loads((GOLD / "DEV_PARTITION.v1.json").read_text(encoding="utf-8"))
    qual_pool = set(part["qual_pool_groups"])
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    fam = {g["scenario_id"]: g["family_id"] for g in frame["groups"]}
    by_scen: dict[str, dict] = {}
    for _rname, (req_rel, out_rel) in ROUND_FILES.items():
        reqs = {r["request_id"]: r for r in jl(PK / req_rel)}
        for o in jl(PK / out_rel):
            sid = reqs[o["request_id"]]["scenario_id"]
            if sid not in qual_pool:
                continue
            d = by_scen.setdefault(sid, {"family": fam.get(sid, "?"), "anchors": set()})
            for c in o.get("claims", []):
                d["anchors"].add(GD.evidence_anchor_digest(
                    sid, c.get("source_ids"), c.get("fact_ids"), c.get("authorization_ids")))
    return by_scen


def cmd_split_v2() -> int:
    """发起人裁决 membership/split v2：按**结构化证据锚 + 家族配额**盲切（未看正式资格答案），
    使 A/B distinct 证据锚容量 ≈ 301/302（均 ≥299 → 满足 <1% 门 n_min=299）。scenario 级整切
    （同锚只属一 scenario → 锚天然不跨集）；家族内均衡 + 总量 swap-opt。旧 membership v1 保全、
    标 SUPERSEDED_BY_EVIDENCE_KEY_FIX，不覆盖。"""
    assert_sealed_ignored()
    frame_digest = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text())["frame_digest"]
    by_scen = _anchors_by_scenario()
    na = {sid: len(d["anchors"]) for sid, d in by_scen.items()}
    famof = {sid: d["family"] for sid, d in by_scen.items()}
    fam_scens: dict[str, list] = {}
    for sid, d in by_scen.items():
        fam_scens.setdefault(d["family"], []).append(sid)
    # 家族内贪心：按锚数降序、确定性哈希平局；分给该家族锚数较少侧（家族持平→总锚较少侧）。
    A: list[str] = []
    B: list[str] = []
    fa: dict[str, int] = {}
    fb: dict[str, int] = {}
    tA = tB = 0
    for famname in sorted(fam_scens):
        for sid in sorted(fam_scens[famname],
                          key=lambda s: (-na[s], L.sha_text(famname + s))):
            if (fa.get(famname, 0), tA) <= (fb.get(famname, 0), tB):
                A.append(sid); tA += na[sid]; fa[famname] = fa.get(famname, 0) + na[sid]
            else:
                B.append(sid); tB += na[sid]; fb[famname] = fb.get(famname, 0) + na[sid]
    # 同家族跨集 swap，缩总量差（保家族均衡）；确定性（候选按 (新差,a,b) 排序）。
    sA, sB = set(A), set(B)
    for _ in range(500):
        gap = tA - tB
        if abs(gap) <= 1:
            break
        best = None
        for a in sorted(sA):
            for b in sorted(sB):
                if famof[a] != famof[b]:
                    continue
                d = na[a] - na[b]
                newgap = gap - 2 * d
                if abs(newgap) < abs(gap):
                    key = (abs(newgap), a, b)
                    if best is None or key < best[0]:
                        best = (key, a, b, d)
        if best is None:
            break
        _, a, b, d = best
        sA.discard(a); sA.add(b); sB.discard(b); sB.add(a); tA -= d; tB += d
    setA = sorted(sA); setB = sorted(sB)

    def anchors_of(scen_list):
        s: set = set()
        for sid in scen_list:
            s |= by_scen[sid]["anchors"]
        return s
    aA, aB = anchors_of(setA), anchors_of(setB)
    if aA & aB:
        raise SystemExit("STOP: 证据锚跨集重叠（scenario 级整切不应发生）")
    membership = {"QUAL_A": setA, "QUAL_B": setB}
    QOPEN.mkdir(parents=True, exist_ok=True)
    SEAL.mkdir(exist_ok=True)
    (SEAL / "membership_v2.json").write_text(
        json.dumps(membership, ensure_ascii=False, indent=1), encoding="utf-8")

    def famcount(scen_list):
        c: dict[str, int] = {}
        for sid in scen_list:
            c[famof[sid]] = c.get(famof[sid], 0) + na[sid]
        return dict(sorted(c.items()))
    receipt = {
        "schema_version": "p7-m3-qual-split-v2-receipt-v1",
        "supersedes": "QUAL_SPLIT_RECEIPT.v1.json",
        "supersede_reason": "SUPERSEDED_BY_EVIDENCE_KEY_FIX：v1 按 (scenario,claim)/round 口径（161/152 伪独立）；"
                            "v2 按结构化证据锚 digest(scenario_id+source/fact/auth ids) 均衡切分。",
        "rule": "scenario 级整切（同锚只属一 scenario）；家族内均衡 + 总量 swap-opt；盲切（未看资格答案）。",
        "at": now(),
        "QUAL_A": {"scenarios": len(setA), "distinct_evidence_anchors": len(aA),
                   "per_family_anchors": famcount(setA)},
        "QUAL_B": {"scenarios": len(setB), "distinct_evidence_anchors": len(aB),
                   "per_family_anchors": famcount(setB)},
        "both_meet_strictest_gate_n_min_299": len(aA) >= 299 and len(aB) >= 299,
        "anchors_disjoint": True,
        "frame_digest": frame_digest,
        "membership_sha256": sha_file(SEAL / "membership_v2.json"),
        "membership_location": "sealed_custody_001/membership_v2.json（保全区；本回执只载数量/摘要）",
    }
    (QOPEN / "QUAL_SPLIT_RECEIPT.v2.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("QUAL_A", "QUAL_B",
                     "both_meet_strictest_gate_n_min_299")}, ensure_ascii=False, indent=1))
    return 0


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
    membership = json.loads(_membership_path().read_text(encoding="utf-8"))
    chosen = set(membership[f"QUAL_{set_id}"])
    scen = {s["scenario_id"]: s for s in jl(PK / "round5/inputs/scenarios.g3.v2.jsonl")}
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    fam = {g["scenario_id"]: g["family_id"] for g in frame["groups"]}
    cases = []
    seen_faces: set[str] = set()  # 发起人裁决：跨轮折叠规范化后相同的 NATURAL 题面（各锚仅留真不同题面）
    for rname, (req_rel, out_rel) in ROUND_FILES.items():
        reqs = {r["request_id"]: r for r in jl(PK / req_rel)}
        for o in jl(PK / out_rel):
            sid = reqs[o["request_id"]]["scenario_id"]
            if sid not in chosen:
                continue
            s = scen[sid]
            for c in o.get("claims", []):
                # 发起人证据身份裁决：source_group_id = 证据锚 digest(scenario_id + source/fact/auth ids)
                # ——非 round-bearing、非 (scenario,claim_id)。同 (scenario,claim) 跨轮再生 = 同锚（不增
                # cluster N）；同 scenario 内引不同 source/fact/auth 的不同 claim = 真不同证据（各成独立锚）。
                anchor = GD.evidence_anchor_digest(
                    sid, c.get("source_ids"), c.get("fact_ids"), c.get("authorization_ids"))
                face = {
                    # case_id 保留 round（区分不同 raw 输入实例）；source_group_id 走证据锚。
                    "case_id": f"Q{set_id}-{rname}-{c['claim_id']}",
                    "case_kind": "NATURAL",
                    "source_group_id": anchor,
                    "scenario_id": sid, "family_id": fam[sid], "round": rname,
                    "item_title": o.get("title", ""),
                    "claim_text": c["claim_text"],
                    "claim_boundary": c.get("claim_boundary", ""),
                    "authorization_scope": s.get("authorization_scope", ""),
                    "slot_facts": s.get("slot_facts", {}),
                    "source_summary_a": s.get("source_summary_a", ""),
                    "source_summary_b": s.get("source_summary_b", ""),
                    "source_ids": list(c.get("source_ids", [])),
                    "fact_ids": list(c.get("fact_ids", [])),
                    "authorization_ids": list(c.get("authorization_ids", [])),
                }
                ffd = GD.frozen_input_face_digest(face)
                if ffd in seen_faces:  # 规范化后相同题面折叠（raw NATURAL 不重复计）
                    continue
                seen_faces.add(ffd)
                face["frozen_input_face_digest"] = ffd
                cases.append(face)
    return cases


# 发起人裁决：CONTRADICTION_INJECT 四个真不同矛盾轴（子机制），令 ~301 锚上 contradicted 达 300+margin
# （raw = distinct (evidence anchor, mechanism)；同锚不同子机制各计 1 覆盖，同子机制不增）。
# 其余 kind 下限 ≤115 ≤ 锚数，单机制即足；mechanism = kind（无子机制）。
_CONTRA_SUBS = ("POLARITY", "MAGNITUDE", "TEMPORAL_STATE", "ATTRIBUTION")


def _variant_task(f: dict, kind: str, sub: str | None, slot: int) -> dict:
    # variant_id 唯一键 = (证据锚, mechanism)——place() 保证同锚同 mechanism 不重复 → id 唯一。
    mech = f"{kind}:{sub}" if sub else kind
    return {"variant_id": f"V-{f['source_group_id']}-{mech}",
            "base_case_id": f["case_id"],
            # 变体继承 base 的证据锚（cluster 身份）+ 真 scenario + 证据 id 列表（供锚/题面摘要复算）。
            "base_source_group_id": f["source_group_id"],
            "base_scenario_id": f["scenario_id"],
            "variant_kind": kind, "mechanism": mech, "sub_mechanism": sub,
            "base_claim_text": f["claim_text"],
            "claim_boundary": f["claim_boundary"],
            "authorization_scope": f["authorization_scope"],
            "slot_facts": f["slot_facts"],
            "source_summary_a": f["source_summary_a"],
            "source_summary_b": f["source_summary_b"],
            "source_ids": list(f.get("source_ids", [])),
            "fact_ids": list(f.get("fact_ids", [])),
            "authorization_ids": list(f.get("authorization_ids", [])),
            "family_id": f["family_id"]}


def _build_variant_tasks(by_fam: dict, frame_digest: str, plan: dict) -> list:
    """发起人裁决 breadth-first 变体构造（证据锚为 cluster 单位）。

    Pass 1（breadth）：**每个** distinct evidence anchor 各产 1 条主 CONTRADICTION_INJECT 高风险变体
      → risk_high/contradicted/unsafe 的 cluster N ≈ 全锚数（≥299，满足 <1% 门 n_min=299）。
      **不**在约150锚堆两条冒充299独立簇（发起人红线）——先全锚各1。
    Pass 2（depth）：按 plan 目标（含 build margin）给锚追加**不同 mechanism** 的第二/三挑战：
      contradicted margin 用 contradiction 子机制（真不同矛盾轴）；unknown/omission/控制类用相应 kind。
      raw = distinct (anchor, mechanism) 由此达标；同锚同 mechanism 绝不重复（不虚增 raw）。"""
    vc = plan["variant_construction"]
    if not vc.get("no_fixed_ratio"):
        raise SystemExit("variant_construction.no_fixed_ratio!=true；拒绝回退固定比例")
    if int(vc["k_variants_per_claim"]) < 2:
        raise SystemExit("k_variants_per_claim 必须 >=2（每 anchor 至少两变体）")
    t = plan["per_set_module_targets"]
    # 去重到 distinct evidence anchor（每锚取一确定性代表 face），跨家族全收；确定性排序。
    anchors: dict[str, dict] = {}
    for fam in sorted(by_fam):
        for f in sorted(by_fam[fam], key=lambda x: L.sha_text(frame_digest + "AF" + x["case_id"])):
            anchors.setdefault(f["source_group_id"], f)
    ordered = sorted(anchors.values(),
                     key=lambda f: L.sha_text(frame_digest + "QV" + f["source_group_id"]))
    n = len(ordered) or 1
    used: dict[str, set] = {f["source_group_id"]: set() for f in ordered}
    tasks: list[dict] = []

    def place(kind: str, sub: str | None) -> bool:
        """把一条 (kind,sub) 放到下一个尚未用过该 mechanism 的锚（round-robin 起点错开）。"""
        mech = f"{kind}:{sub}" if sub else kind
        start = int(L.sha_text(frame_digest + "START" + mech)[:8], 16) % n
        for j in range(n):
            f = ordered[(start + j) % n]
            sg = f["source_group_id"]
            if mech not in used[sg]:
                used[sg].add(mech)
                tasks.append(_variant_task(f, kind, sub, len(used[sg])))
                return True
        return False  # 全锚已用尽该 mechanism

    # Pass 1 breadth：全锚各一条主矛盾（POLARITY，最普适矛盾轴）。
    for f in ordered:
        used[f["source_group_id"]].add(f"CONTRADICTION_INJECT:{_CONTRA_SUBS[0]}")
        tasks.append(_variant_task(f, "CONTRADICTION_INJECT", _CONTRA_SUBS[0], 1))

    # Pass 2 depth：按 plan 目标（含 margin）逐 (kind,sub) 配额补足；每次 place 落到一个未用该
    # mechanism 的锚（round-robin）。同锚同 mechanism 绝不重复 → 不虚增 raw。
    en = t["entailment"]
    quotas: list[tuple[str, str | None]] = []
    # contradicted margin：POLARITY 已铺满 n 条，剩余用 MAGNITUDE/TEMPORAL_STATE/ATTRIBUTION 轮转补差。
    extra_contra = max(0, en["high_risk_contradicted"]["target"] - n)
    for i in range(extra_contra):
        quotas.append(("CONTRADICTION_INJECT", _CONTRA_SUBS[1 + (i % (len(_CONTRA_SUBS) - 1))]))
    # unknown：EVIDENCE_INSUFFICIENT（≤n，单机制足）
    quotas += [("EVIDENCE_INSUFFICIENT", None)] * en["high_risk_unknown"]["target"]
    # omission_misleading
    quotas += [("OMISSION_MISLEAD", None)] * t["omission"]["misleading_high_risk"]["target"]
    # unsafe margin（若 target>n）：RISK_ELEVATE 补差（contradiction 已覆盖 n 条 unsafe 意图）
    quotas += [("RISK_ELEVATE", None)] * max(0, t["fact_chain"]["high_risk_unsafe"]["target"] - n)
    # 负控 + 6-kind 覆盖：BOUNDARY_OMIT / LEGAL_NEGATIVE_CONTROL
    quotas += [("BOUNDARY_OMIT", None)] * t["reference_extraction"]["negative_control"]["target"]
    quotas += [("LEGAL_NEGATIVE_CONTROL", None)] * t["claim_atomization"]["negative_control"]["target"]
    for kind, sub in quotas:
        place(kind, sub)
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
            face = {
                "case_id": r["variant_id"], "case_kind": "CHALLENGE_VARIANT",
                # §四.1：challenge_kind 钉题面（6-kind 家族，供审计「六种各≥1」）；
                # mechanism（含 contradiction 子机制）驱动 raw = distinct (anchor, mechanism)。
                "challenge_kind": normalize_kind(r.get("variant_kind", t["variant_kind"])),
                "mechanism": t.get("mechanism") or normalize_kind(t["variant_kind"]),
                # 发起人裁决：变体继承 base 的证据锚（cluster 身份）+ 真 scenario + 证据 id 列表。
                "source_group_id": t["base_source_group_id"],
                "scenario_id": t["base_scenario_id"], "family_id": t["family_id"],
                "item_title": "", "claim_text": r["variant_claim_text"],
                "claim_boundary": t["claim_boundary"],
                "authorization_scope": t["authorization_scope"],
                "slot_facts": t["slot_facts"],
                "source_summary_a": t["source_summary_a"],
                "source_summary_b": t["source_summary_b"],
                "source_ids": list(t.get("source_ids", [])),
                "fact_ids": list(t.get("fact_ids", [])),
                "authorization_ids": list(t.get("authorization_ids", []))}
            face["frozen_input_face_digest"] = GD.frozen_input_face_digest(face)
            variants_faces.append(face)
            variant_intents.append({"variant_id": r["variant_id"],
                                    "variant_kind": r.get("variant_kind", t["variant_kind"]),
                                    "mechanism": t.get("mechanism"),
                                    "intended_risk": r.get("intended_risk"),
                                    "intended_entailment": r.get("intended_entailment"),
                                    "construction_note": r.get("construction_note", "")})
    # §六 build-4：确定性 disclosure 覆盖——合同下限 disclosure_case≥100/套、obligation 类型≥4。
    # per_type=ceil(100/4)+margin 保证四类型齐 + 冗余（个别标注 miss 不致缺类）。disclosure 是确定性
    # count 门（非统计 CI 门），distinct 合成锚 + k 变体即可；faces 走同一真 AI 双席标注管线。
    disclosure_faces = build_disclosure_faces(set_id, per_type=DISCLOSURE_PER_TYPE)
    faces = natural + variants_faces + disclosure_faces
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
        "deterministic_disclosure_faces": len(disclosure_faces),
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
        cases = json.loads(bpath.read_text(encoding="utf-8"))
        expected = {c["case_id"] for c in cases}
        # 续跑复用仅当输出覆盖本批全部 case（防批组成变化后旧标签漏标 disclosure 等新增 face）。
        if _batch_ready(out_path) and expected.issubset(
                {r.get("case_id") for r in json.loads(out_path.read_text(encoding="utf-8"))}):
            continue
        slim = [{k: c[k] for k in ("case_id", "claim_text", "claim_boundary",
                                   "authorization_scope", "slot_facts",
                                   "source_summary_a", "source_summary_b", "item_title")}
                for c in cases]

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
    # §四.1 富标签双盲逐字段一致（结构字段先规范化，顺序差异不算分歧）：
    #   per_field_dispute_counts[field] = 该字段跨席规范化后仍不一致的 face 数；
    #   face_any_field_dispute_count = 至少一个字段分歧的 face 数（这些 face 才进裁决）。
    per_field = {f: 0 for f in GD.RICH_LABEL_FIELDS}
    face_any = 0
    for cid in set(a) & set(b):
        d = GD.field_disputes(a[cid], b[cid])
        if d:
            face_any += 1
        for f in d:
            per_field[f] += 1
    receipt = {
        "schema_version": "p7-m3-qual-doubleblind-receipt-v1",
        "set": f"QUAL_{set_id}", "at": now(),
        "faces_total": total, "labeled_both_seats": both,
        "seats": "A=Codex-GPT(gpt-5.6-sol) / B=Opus-4.8（跨模型双盲；载体裁决 seq41）",
        "label_schema": "rich_nine_module (qual_rich_labeler)",
        "agreement_granularity": "PER_FIELD (结构字段规范化后比较；§四.1)",
        "dispute_count": face_any,
        "dispute_rate": round(face_any / max(1, both), 4),
        "face_any_field_dispute_count": face_any,
        "per_field_dispute_counts": per_field,
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
    print(json.dumps({"labeled": both, "faces_with_dispute": face_any,
                      "per_field_dispute_counts": per_field,
                      "event": ev["code"], "seq": ev["seq"]}, ensure_ascii=False))
    return 0


_RICH_FIELDS = GD.RICH_LABEL_FIELDS + ("rationale",)


# ============================================================ §六 review 子管线（全量生产）
# 全量 runner 缺 review 生产命令（cmd_goldfreeze 只消费 review_units.json）。本命令：
# 从真源自然 claim 装配 ≥40 可评审内容单元 → 双席(A=Codex/B=Opus)独立 decision+hard_veto →
# assemble → 写 sealed_custody_001/qual_{set}/review_units.json（cmd_goldfreeze 消费）。
# 复用 RF 真子管线 + cmd_label 的 batched/resume/registry 纪律；主会话零明文。

def _seat_call(carrier: str, cache_dir: Path, batch_stem: str, kind: str, count: int):
    """RF 席位调用适配器：绑定真 L.attempt_call + 密封 REG；按 batch_stem 落缓存，重跑不重复付费。"""
    cache_dir.mkdir(parents=True, exist_ok=True)

    def call(prompt, ok, _rf_stem):
        cache = cache_dir / f"{batch_stem}.rows.json"
        if cache.is_file():
            rows = json.loads(cache.read_text(encoding="utf-8"))
            if ok(rows):
                return rows
        rows = L.attempt_call(prompt, ok, cache_dir, batch_stem, REG,
                              {"kind": kind, "seat": batch_stem.rsplit("_", 1)[-1],
                               "batch": batch_stem, "visible_material_count": count,
                               "retention": "标签明文留存保全区；registry 零内容"}, carrier=carrier)
        if rows is not None:
            cache.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        return rows
    return call


REVIEW_TARGET = 50   # 合同 review_double_reviewed_items=40；建 50 留裕度
REVIEW_CHUNK = 10


def _review_items_for_set(set_id: str, target: int = REVIEW_TARGET) -> list[dict]:
    """从真源自然 claim 装配可评审内容单元（五家族均衡，确定性排序取前 target）。
    author_identity ≠ 审核席身份（满足 role_collision_absent）。"""
    cases = _cases_for_set(set_id)
    by_fam: dict[str, list[dict]] = {}
    for c in sorted(cases, key=lambda c: c["case_id"]):
        by_fam.setdefault(c["family_id"], []).append(c)
    fams = sorted(by_fam)
    picked: list[dict] = []
    idx = 0
    # 轮转五家族取，均衡覆盖，直到 target
    while len(picked) < target and any(idx < len(by_fam[f]) for f in fams):
        for f in fams:
            if idx < len(by_fam[f]) and len(picked) < target:
                picked.append(by_fam[f][idx])
        idx += 1
    return [{"item_id": f"QUAL{set_id}-REV-{c['case_id']}", "family_id": c["family_id"],
             "source_group_id": f"rev-{c['source_group_id']}",
             "author_identity": f"GEN_AUTHOR::{c['case_id']}",
             "content": c["claim_text"], "claim_boundary": c["claim_boundary"],
             "authorization_scope": c["authorization_scope"],
             "source_summary_a": c["source_summary_a"], "source_summary_b": c["source_summary_b"]}
            for c in picked]


def cmd_review(set_id: str, max_batches: int) -> int:
    assert_sealed_ignored()
    sdir = SEAL / f"qual_{set_id}"
    sdir.mkdir(parents=True, exist_ok=True)
    items = _review_items_for_set(set_id)
    (sdir / "review_items.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    tmpl = L.load_template(ANNEXC, "qual_review_labeler")
    pd = digest_json({"tmpl": "qual_review_labeler", "sha": L.sha_text(tmpl)})
    batches = [items[i:i + REVIEW_CHUNK] for i in range(0, len(items), REVIEW_CHUNK)]
    dec: dict[str, dict] = {"A": {}, "B": {}}
    for seat, carrier in (("A", "codex"), ("B", "claude")):
        done = 0  # per-seat：max_batches 不得让某席空缺（否则 assemble 失败）
        for bi, batch in enumerate(batches):
            if done >= max_batches:
                break
            call = _seat_call(carrier, sdir / f"review_{seat}", f"rb_{bi:03d}_{seat}",
                              f"QUAL{set_id}_REVIEW", len(batch))
            d = RF.label_review_seat(batch, seat, call=call, template=tmpl)
            dec[seat].update(d)
            done += 1
    units = RF.assemble_review_units(items, dec["A"], dec["B"],
                                     prompt_digest_a=pd, prompt_digest_b=pd)
    (sdir / "review_units.json").write_text(
        json.dumps(units, ensure_ascii=False, indent=1), encoding="utf-8")
    disagree = sum(1 for u in units
                   if u["judgments"][0]["decision"] != u["judgments"][1]["decision"])
    print(json.dumps({"set": set_id, "review_items": len(items),
                      "review_units": len(units), "judgment_records": len(units) * 2,
                      "cross_seat_disagree": disagree,
                      "written": "sealed_custody_001/qual_%s/review_units.json" % set_id},
                     ensure_ascii=False))
    return 0


# ========================================================= §六 formulaic 子管线（全量生产）
# 全量 runner 缺 formulaic 生产命令。本命令：从真源 generated content(body) 挖 pair（偏置三类
# 候选 → 拉平分布）→ 双席逐 6 轴 → verdict 分歧仲裁 → assemble → 写 formulaic_units.json。
# 分布靠偏置候选提高命中，真 verdict 仍由双席决定（绝不预置）；不足由 top-up 再跑补（剩余缺口）。
# NG：候选设 necessary_grammar_exception_id="NG-1"（derive_formulaic_records 自动注册该 exception）；
# 仅当双席真判 NECESSARY_GRAMMAR 轴时才落 NG verdict。

FORMULAIC_CHUNK = 8
# 语料结构：每 scenario = 4 个同 (profile,variant) 输出。故「同 scenario」即「同模板」。
# 同 scenario 对 = pos+NG 双偏置（同模板→多判 FORMULAIC，少数结构必需→NECESSARY_GRAMMAR），
# 全部设 exc=NG-1 使 NG verdict 合法；跨 profile 对 = neg 偏置（异构→NOT_FORMULAIC）。
# over-generate 到 ~340（≥300）；真 verdict 仍由双席决定，分布不足由 top-up 再跑补。
FORM_SAME_SCEN_CAP, FORM_CROSS_PROF_CAP = 180, 160


def _set_outputs(set_id: str) -> list[dict]:
    """本套 generated content 输出（保留 body 全文供 formulaic 结构比对）。"""
    membership = json.loads((SEAL / "membership.json").read_text(encoding="utf-8"))
    chosen = set(membership[f"QUAL_{set_id}"])
    frame = json.loads((M3DS / "SAMPLING_FRAME.v1.json").read_text(encoding="utf-8"))
    fam = {g["scenario_id"]: g["family_id"] for g in frame["groups"]}
    outs = []
    for rname, (req_rel, out_rel) in ROUND_FILES.items():
        reqs = {r["request_id"]: r for r in jl(PK / req_rel)}
        for o in jl(PK / out_rel):
            sid = reqs[o["request_id"]]["scenario_id"]
            if sid not in chosen:
                continue
            body = "\n".join(o.get("body", []))[:1200]
            if not body.strip():
                continue
            outs.append({"oid": f"{rname}:{o['request_id']}", "scenario_id": sid,
                         "profile_id": o.get("profile_id", ""),
                         "assigned_variant": o.get("assigned_variant", ""),
                         "family_id": fam.get(sid, "F1_PEOPLE_AND_REAL_SCENE"),
                         "author_identity": o.get("author_identity", f"AUTHOR::{o['request_id']}"),
                         "content": body})
    return outs


def _mk_form_pair(ref: str, lo: dict, ro: dict, exc: str | None) -> dict:
    return {"pair_ref": ref, "left_id": lo["oid"], "right_id": ro["oid"],
            "family_id": lo["family_id"], "source_group_id": f"fpair-{ref}",
            "left_content": lo["content"], "right_content": ro["content"],
            "left_author_identity": lo["author_identity"],
            "right_author_identity": ro["author_identity"],
            "necessary_grammar_exception_id": exc}


def _formulaic_pairs_for_set(set_id: str) -> list[dict]:
    """挖偏置 pair 候选（确定性排序）：
      SS = 同 scenario（同模板）全 C(n,2)，exc=NG-1 → pos+NG 偏置；
      CP = 跨 profile（异构）→ neg 偏置，exc=None。"""
    outs = sorted(_set_outputs(set_id), key=lambda o: o["oid"])
    by_prof: dict[str, list[dict]] = {}
    by_scen: dict[str, list[dict]] = {}
    for o in outs:
        by_prof.setdefault(o["profile_id"], []).append(o)
        by_scen.setdefault(o["scenario_id"], []).append(o)
    pairs, seen, idx = [], set(), 0

    def add(lo, ro, exc, tag):
        nonlocal idx
        key = tuple(sorted((lo["oid"], ro["oid"])))
        if lo["oid"] == ro["oid"] or key in seen:
            return False
        seen.add(key)
        pairs.append(_mk_form_pair(f"QUAL{set_id}-FP-{tag}-{idx:04d}", lo, ro, exc))
        idx += 1
        return True

    # SS：同 scenario 内全对（同模板→pos；结构必需→NG），exc=NG-1 使 NG verdict 合法
    n_ss = 0
    for sid in sorted(by_scen):
        g = sorted(by_scen[sid], key=lambda o: o["oid"])
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                if n_ss >= FORM_SAME_SCEN_CAP:
                    break
                if add(g[i], g[j], "NG-1", "SS"):
                    n_ss += 1
    # CP：跨 profile（不同 scenario）配 → 异构偏 NOT_FORMULAIC
    profs = sorted(by_prof)
    n_cp = 0
    for gap in range(1, len(profs)):
        for i in range(len(profs) - gap):
            if n_cp >= FORM_CROSS_PROF_CAP:
                break
            a, b = by_prof[profs[i]], by_prof[profs[i + gap]]
            for k in range(min(len(a), len(b))):
                if n_cp >= FORM_CROSS_PROF_CAP:
                    break
                if a[k]["scenario_id"] != b[k]["scenario_id"] and add(a[k], b[k], None, "CP"):
                    n_cp += 1
        if n_cp >= FORM_CROSS_PROF_CAP:
            break
    return pairs


def cmd_formulaic(set_id: str, max_batches: int) -> int:
    assert_sealed_ignored()
    sdir = SEAL / f"qual_{set_id}"
    sdir.mkdir(parents=True, exist_ok=True)
    pairs = _formulaic_pairs_for_set(set_id)
    (sdir / "formulaic_pairs.json").write_text(
        json.dumps(pairs, ensure_ascii=False, indent=1), encoding="utf-8")
    tmpl = L.load_template(ANNEXC, "qual_formulaic_axis_labeler")
    adj_tmpl = L.load_template(ANNEXC, "qual_formulaic_axis_adjudicator")
    pd = digest_json({"tmpl": "qual_formulaic_axis_labeler", "sha": L.sha_text(tmpl)})
    batches = [pairs[i:i + FORMULAIC_CHUNK] for i in range(0, len(pairs), FORMULAIC_CHUNK)]
    axes: dict[str, dict] = {"A": {}, "B": {}}
    for seat, carrier in (("A", "codex"), ("B", "claude")):
        done = 0
        for bi, batch in enumerate(batches):
            if done >= max_batches:
                break
            call = _seat_call(carrier, sdir / f"formaxis_{seat}", f"fb_{bi:03d}_{seat}",
                              f"QUAL{set_id}_FORMAXIS", len(batch))
            a = RF.label_formulaic_seat(batch, seat, call=call, template=tmpl)
            axes[seat].update(a)
            done += 1
    need = RF.pairs_needing_adjudication(pairs, axes["A"], axes["B"])
    adj_axes: dict[str, dict] = {}
    adj_batches = [need[i:i + FORMULAIC_CHUNK] for i in range(0, len(need), FORMULAIC_CHUNK)]
    for bi, batch in enumerate(adj_batches):
        call = _seat_call("claude", sdir / "formaxis_adj", f"fadj_{bi:03d}",
                          f"QUAL{set_id}_FORMADJ", len(batch))
        adj_axes.update(RF.adjudicate_formulaic_axes(batch, axes["A"], axes["B"],
                                                     call=call, template=adj_tmpl))
    units = RF.assemble_formulaic_units(pairs, axes["A"], axes["B"], adj_axes,
                                        prompt_digest_a=pd, prompt_digest_b=pd)
    (sdir / "formulaic_units.json").write_text(
        json.dumps(units, ensure_ascii=False, indent=1), encoding="utf-8")
    dist: dict[str, int] = {}
    for u in units:
        dist[u["final_verdict"]] = dist.get(u["final_verdict"], 0) + 1
    print(json.dumps({"set": set_id, "pairs": len(pairs), "adjudicated": len(need),
                      "final_verdict_distribution": dict(sorted(dist.items())),
                      "written": "sealed_custody_001/qual_%s/formulaic_units.json" % set_id},
                     ensure_ascii=False))
    return 0


def cmd_adjudicate(set_id: str, max_batches: int) -> int:
    assert_sealed_ignored()
    # §四.1 富标签裁决：隔离仲裁席对九模块字段分歧裁断（旧二字段 adjudicator 保留供 G2）。
    tmpl = L.load_template(ANNEXC, "qual_rich_adjudicator")
    sdir = SEAL / f"qual_{set_id}"
    faces = {c["case_id"]: c for c in json.loads(
        (sdir / "faces_frozen.json").read_text(encoding="utf-8"))}
    a, b = _seal_collect(set_id, "labels_A"), _seal_collect(set_id, "labels_B")
    # §四.1：仅把「规范化后仍分歧的字段」送裁；一致字段绝不进裁（不因它字段分歧被改写）。
    disputes = []
    for cid in sorted(set(a) & set(b)):
        df = GD.field_disputes(a[cid], b[cid])
        if df:
            c = faces[cid]
            disputes.append({"case_id": cid,
                             "disputed_fields": df,
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


def _base_seat_provenance(labeler_pd: str) -> list[dict]:
    """两独立评审席 A=Codex-GPT / B=Opus-4.8（恒挂）。AI 席须 model_revision + prompt_digest
    （labeler 模板 sha 摘要，绑定实际标注 prompt），满足 validate 的双独立评审门。"""
    return [{"tag": "A", "reviewer_identity": "SEAT_A::codex-gpt", "reviewer_kind": "AI",
             "model_revision": "gpt-5.6-sol", "prompt_digest": labeler_pd},
            {"tag": "B", "reviewer_identity": "SEAT_B::opus-4-8", "reviewer_kind": "AI",
             "model_revision": "claude-opus-4-8", "prompt_digest": labeler_pd}]


def _adj_seat_provenance(adj_pd: str) -> dict:
    """隔离仲裁席 ADJ（§四.1：仅被消费仲裁字段的模块记录追加此席）。"""
    return {"tag": "ADJ", "reviewer_identity": "ADJ::opus-4-8-isolated",
            "reviewer_kind": "AI", "model_revision": "claude-opus-4-8",
            "prompt_digest": adj_pd}


def _seat_provenance(cid: str, adjudicated: bool, labeler_pd: str,
                     adj_pd: str) -> list[dict]:
    """兼容旧签名（review/formulaic 单元用；这些单元不做字段级仲裁，恒 A/B 两席）。"""
    sp = _base_seat_provenance(labeler_pd)
    if adjudicated:
        sp.append(_adj_seat_provenance(adj_pd))
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

    # 1) 逐 face **逐字段**解析富标签（§四.1）：结构字段规范化后一致→采一致值(CROSS_MODEL_AGREED)；
    #    分歧字段→只采该字段仲裁值(FIELD_ADJUDICATED)；缺席位或某分歧字段缺裁决→未决 fail-closed。
    resolutions: dict[str, dict] = {}
    unresolved: list[str] = []
    for c in faces:
        cid = c["case_id"]
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
    if unresolved:
        raise SystemExit(f"goldfreeze 拒绝：未决 {len(unresolved)} 条（缺席位标签或某分歧字段缺裁决）")
    adjudicated_faces = sum(1 for r in resolutions.values() if r["adjudicated_fields"])

    # 2) dataset_manifest_digest + generation_id（确定性绑 faces 内容）。
    faces_sha = sha_file(sdir / "faces_frozen.json")
    generation_id = f"QUAL_{set_id}_GEN_{faces_sha[:16]}"
    dmd = digest_json({"set": set_id, "faces_sha256": faces_sha,
                       "generation": generation_id})
    labeler_pd = digest_json({"tmpl": "qual_rich_labeler",
                              "sha": L.sha_text(L.load_template(ANNEXC, "qual_rich_labeler"))})
    adj_pd = digest_json({"tmpl": "qual_rich_adjudicator",
                          "sha": L.sha_text(L.load_template(ANNEXC, "qual_rich_adjudicator"))})
    base_sp = _base_seat_provenance(labeler_pd)
    adj_sp = _adj_seat_provenance(adj_pd)

    def sp_for_units(_record_cid: str) -> list[dict]:
        # review/formulaic 单元恒 A/B 两席（不做字段级仲裁；单元自带内部 reviewer_id，与席位正交）。
        return _base_seat_provenance(labeler_pd)

    # 3) 逐 claim 七模块派生（逐模块 ADJ provenance）+ cross-module reuse 登记。
    der = GD.derive_perclaim_records(faces, resolutions, dataset_manifest_digest=dmd,
                                     base_seat_provenance=base_sp, adj_seat_provenance=adj_sp)
    records = list(der["records"])
    cross_module_reuse = der["cross_module_reuse"]

    # 4) review_calibration / formulaic：读密封解析单元（若在场；由 review/formulaic 子管线产出）。
    review_units_path = sdir / "review_units.json"
    formulaic_units_path = sdir / "formulaic_units.json"
    review_count = formulaic_count = 0
    if review_units_path.is_file():
        ru = json.loads(review_units_path.read_text(encoding="utf-8"))
        rrecs = GD.derive_review_records(ru, dataset_manifest_digest=dmd,
                                         seat_provenance_for=sp_for_units)
        records.extend(rrecs)
        review_count = len(rrecs)
    if formulaic_units_path.is_file():
        fu = json.loads(formulaic_units_path.read_text(encoding="utf-8"))
        frecs = GD.derive_formulaic_records(fu, dataset_manifest_digest=dmd,
                                            seat_provenance_for=sp_for_units,
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
        "resolved_faces": len(resolutions),
        "adjudicated_faces": adjudicated_faces,
        "agreement_granularity": "PER_FIELD (§四.1；逐模块 ADJ provenance)",
        "review_records": review_count, "formulaic_records": formulaic_count,
        # §四.6 发起人裁决双披露：raw case N（不同机制变体计入覆盖，管 300/100）
        # 与 distinct source-group cluster N（同源变体不增，管统计独立/CI 功效）并列。
        "class_counts_recomputed": pc["counts"],
        "cluster_class_counts_recomputed": pc["cluster_counts"],
        "dual_count_disclosure": "counts=raw case N（覆盖门）; cluster_counts=distinct "
                                 "source-group N（cluster-aware 单侧95%CI 功效门）",
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
    # cmd_goldfreeze 写 v2 回执（gold_record_count / class_counts_recomputed）；finalize 同读 v2。
    ra = json.loads((QOPEN / "QUAL_A_GOLD_FROZEN_RECEIPT.v2.json").read_text())
    rb = json.loads((QOPEN / "QUAL_B_GOLD_FROZEN_RECEIPT.v2.json").read_text())
    # qualification_manifest 物化
    mpath = SPINE / "calibration/qualification_manifest.v1.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    manifest["content_status"] = "MATERIALIZED"
    manifest["case_count"] = ra["gold_record_count"] + rb["gold_record_count"]
    manifest["class_counts"] = {"QUAL_A": ra["class_counts_recomputed"],
                                "QUAL_B": rb["class_counts_recomputed"]}
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
        "sets": {"QUAL_A": {"gold": ra["gold_record_count"], "gold_sha256": ra["gold_sha256"]},
                 "QUAL_B": {"gold": rb["gold_record_count"], "gold_sha256": rb["gold_sha256"]}},
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
    sub.add_parser("split_v2")  # 发起人裁决：证据锚均衡 membership v2
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
    for name in ("review", "formulaic"):  # §六 review/formulaic 真子管线（全量生产）
        rp = sub.add_parser(name)
        rp.add_argument("--set", choices=["A", "B"], required=True)
        rp.add_argument("--max-batches", type=int, default=99)
    sub.add_parser("finalize")
    args = ap.parse_args()
    if args.cmd == "split":
        return cmd_split()
    if args.cmd == "split_v2":
        return cmd_split_v2()
    if args.cmd == "faces":
        return cmd_faces(args.set, args.max_batches)
    if args.cmd == "label":
        return cmd_label(args.set, args.seat, args.max_batches)
    if args.cmd == "labelfreeze":
        return cmd_labelfreeze(args.set)
    if args.cmd == "adjudicate":
        return cmd_adjudicate(args.set, args.max_batches)
    if args.cmd == "review":
        return cmd_review(args.set, args.max_batches)
    if args.cmd == "formulaic":
        return cmd_formulaic(args.set, args.max_batches)
    if args.cmd == "goldfreeze":
        return cmd_goldfreeze(args.set)
    if args.cmd == "finalize":
        return cmd_finalize()
    return 2


if __name__ == "__main__":
    sys.exit(main())
