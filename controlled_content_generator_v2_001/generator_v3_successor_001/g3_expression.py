#!/usr/bin/env python3
"""G3 · 表达计划（反套路）：确定性档型分配 + 表面骨架分类器。

上一轮 28 条套路/近重复的病灶是"画像级跨场景骨架复用"
（CP05 履历台账、CP18 城市开场、CP09/07 先排除标题、CP01/06 角色许可收尾）。
本模块给每条请求分配互异的表达档型（作者义务），并提供
确定性骨架分类器供批级集中度门使用（V1.1 标准 L773-779 触发线的机器化）。

分配无随机：档型序列按 sha256(profile_id+batch_id) 取旋转偏移后轮转发牌，
同一 (批, 产品) 内相同档型出现次数 ≤2（标准触发线），重复运行零差异。
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

OPENING_ARCHETYPES = [
    "SCENE_MOMENT",       # 从一个正在发生的具体现场瞬间进入
    "OBJECT_CLOSEUP",     # 从一件具体物品/细节特写进入
    "QUESTION_FIRST",     # 从一个真实的问题进入（正文首段含问句）
    "RESULT_FIRST",       # 先给出结果/状态，再回溯过程
    "TIMELINE_MARKER",    # 从明确时间锚点进入
    "DIALOGUE_OR_QUOTE",  # 从一句现场原话/对话片段进入
]
ENDING_ARCHETYPES = [
    "NEXT_CONCRETE_STEP",  # 收在一个已排定的具体下一步动作
    "OPEN_OBSERVATION",    # 收在一个仍在持续的观察点
    "STATE_SNAPSHOT",      # 收在当下状态的静态快照
    "SENSORY_CLOSE",       # 收在一个感官细节（声音/触感/画面）
    "FORWARD_SCHEDULE",    # 收在时间表上的下一个节点
    "LIMIT_AS_FACT",       # 收在以事实形态陈述的适用限度（禁治理措辞）
]
TITLE_ARCHETYPES = [
    "DETAIL_HOOK",     # 具体细节钩子
    "QUESTION_HOOK",   # 问句钩子
    "CONTRAST_HOOK",   # 对照/反差钩子
    "PROCESS_HOOK",    # 过程动作钩子
    "RESULT_HOOK",     # 结果状态钩子
    "PLACE_TIME_HOOK", # 地点/时间钩子
]
# ---- v2（第2正式轮新增）：四个深层维度，治"边缘互异、内芯同构" ----
BODY_ARCHITECTURES = [
    "CHRONO_SINGLE_THREAD",  # 单线时序推进
    "CONTRAST_TWO_OBJECT",   # 双对象/双状态对照交替
    "MOSAIC_THREE_SCENES",   # 三个独立小画面拼合，无显式串词
    "CAUSAL_CHAIN",          # 因果链：现象→机制→后果
    "ZOOM_DETAIL_TO_WHOLE",  # 由一处细节逐层放大到整体
    "EVIDENCE_WALK",         # 跟随一件实物/一页记录走动线
]
SPOKEN_FORMATS = [
    "EMPTY_NO_SPOKEN",       # 无口播（声音轴改由 audio 表面承载核心事实）
    "SINGLE_OBSERVATION",    # 一句现场观察
    "TWO_VOICE_EXCHANGE",    # 两句一来一回
    "COUNTED_REPORT",        # 报数式（数值必须出自材料）
    "QUESTION_ECHO",         # 一句问＋一句答
    "PROCESS_MURMUR",        # 干活时的低声自语一句
]
AUDIO_SIGNATURES = [
    "AMBIENT_CONTINUOUS",    # 连续环境底声
    "ACTION_ACCENTS",        # 动作重音点缀
    "SINGLE_MARK_SOUND",     # 单一标志声贯穿
    "LAYERED_NEAR_FAR",      # 近景/远景双层声
    "QUIET_ONE_BREAK",       # 安静中一次声音破点
    "RHYTHMIC_TASK",         # 有节奏的作业声
]
BOUNDARY_POSITIONS = [
    "EARLY_WEAVE",           # 限度事实织进前两段
    "MID_WEAVE",             # 限度事实织进中段
    "LATE_FACT",             # 限度事实作末段事实句（非治理句）
    "SPLIT_TWO_POINTS",      # 限度拆成两处小点分布
    "VISUAL_CARRIED",        # 限度由画面表面承载，正文只留痕
    "SPOKEN_CARRIED",        # 限度由口播承载（spoken_format 非 EMPTY 时）
]
# v3（第3轮）：限度句"措辞风格"发牌——第2轮四位审查一致发现限度句族跨作者
# 收敛（根源=策展措辞单一文化），风格随请求发牌并先在策展层落实到边界事实本身。
BOUNDARY_STYLES = [
    "BS_NUM_LEDGER",     # 数字/清单对账式：已量三处，第四处空着
    "BS_SCHEDULE_NEXT",  # 工序排期式：复测排在面料回缩之后（具体工位/日期）
    "BS_SPATIAL_FRAME",  # 空间取景式：界限=镜头/空间没走到的位置
    "BS_RECORD_FIELD",   # 记录字段式：表上某一栏空着（以单据/表格承载）
    "BS_SENSORY_STATE",  # 感官状态式：以当下物理状态陈述界限
    "BS_QA_THIRDPARTY",  # 他人视角留白式：顾客/同事怎么看没人问过
]

# 第2轮判死的限度句族固定公式（语义可保留，固定措辞禁成套；per-CP cap=2；
# 按第2轮 120 条真实文本经验校准，见 evidence/gate_calibration_report.v0.2.json）
BOUNDARY_FAMILY_PATTERNS: dict[str, str] = {
    "BF_ONLY_TRIED": (r"只(在|对)[^，。；]{0,16}(上|里)?(试|用|走|看|量|测|放|穿)过"
                      r"|只(验|测|量|证)(了|过|得了)"),
    "BF_NOT_YET_VERB": r"还没(有)?[^，。；]{0,14}(试|测|验|看|排|做|问|洗|穿|比|动)",
    "BF_CANT_TELL": r"(看不出来|看不出|给不出答案|说不上|无从谈起)",
    "BF_NOT_EQUAL": r"(不代表|不等于|证不了|说明不了)",
    "BF_THIS_ONLY": r"这(只是|不过是)",
    "BF_SCOPE_ASIDE": (r"(另算|另论|另说|不掺|不在里面|排在这一?轮之外"
                       r"|只覆盖|只管这)"),
}
# 第2轮声音写法坍缩的两个模板家族（120 条中"记号声/破点"族与"近远双层"族
# 合计 ≥40 条命中；发明性行话名词族为锚，自然声景描写不会需要它们；per-CP cap=2）
AUDIO_TEMPLATE_PATTERNS: dict[str, str] = {
    "AT_SINGLE_MARK": (r"(记号声|记号音|标志声|声音落点|破点|断点)"
                       r"|唯一[^，。；]{0,8}(一下|一声|一记|一响)"
                       r"|(只留|只剩|只有)[^，。；]{0,10}(一声|一记|一响|一个)"),
    "AT_NEAR_FAR": r"近处[\s\S]{0,60}远处|远处[\s\S]{0,60}近处|远近两层|分两层|分成两层",
}
# 每产品允许的叙事弧（依据 V1.1 标准产品定义，避免弧型与产品指纹冲突）
NARRATIVE_ARCS: dict[str, list[str]] = {
    "CP01": ["TASK_ARC", "PROBLEM_FIX_ARC", "SHADOWING_ARC"],
    "CP02": ["OBSERVATION_SWEEP", "PARALLEL_THREADS", "RHYTHM_CYCLE"],
    "CP03": ["PROCESS_CHAIN", "MATERIAL_JOURNEY", "CRAFT_CLOSEUP_CHAIN"],
    "CP04": ["HANDOFF_CHAIN", "PARALLEL_ROLES", "SYNC_POINT_ARC"],
    "CP05": ["ARCHIVE_REVISIT", "TURNING_POINT", "SKILL_TRACE", "MENTOR_ECHO"],
    "CP06": ["SIGNAL_TO_JUDGMENT", "CASE_SLICE", "COMPARISON_JUDGMENT"],
    "CP07": ["QUESTION_TO_ANSWER", "ELIMINATION_TREE", "CONDITION_SPLIT"],
    "CP08": ["STRUCTURE_REVEAL", "CROSS_SECTION", "WEAR_CONSEQUENCE"],
    "CP09": ["FIT_BOUNDARY", "ALTERNATIVE_ROUTE", "CONDITION_MATRIX"],
    "CP10": ["EVIDENCE_TIMELINE", "TEST_PROTOCOL", "LIMIT_DISCLOSURE"],
    "CP11": ["TRADEOFF_STORY", "ORIGIN_TRACE", "REJECTED_OPTION"],
    "CP12": ["VERSION_DIFF", "FEEDBACK_LOOP", "CHANGELOG_WALK"],
    "CP13": ["WARDROBE_ROLE", "LIFE_SCENE_CHAIN", "COMPANION_OBJECT"],
    "CP14": ["OBJECT_SENSES", "MATERIAL_LIGHT", "MOTION_TEXTURE"],
    "CP15": ["ARRIVAL_TO_SHELF", "LIFECYCLE_STATIONS", "BACKSTAGE_FLOW"],
    "CP16": ["SERVICE_REPLAY", "EXPECTATION_GAP", "REPAIR_FOLLOWUP"],
    "CP17": ["SPACE_EXPERIMENT", "BEFORE_AFTER_FLOOR", "HYPOTHESIS_DISPLAY"],
    "CP18": ["NEIGHBORHOOD_SEASON", "LOCAL_TEXTURE", "CLIMATE_ADAPT"],
    "CP19": ["DECISION_REPLAY", "COST_VISIBLE", "PATH_NOT_TAKEN"],
    "CP20": ["PROMISE_TRACK", "CHECKPOINT_AUDIT", "GAP_DISCLOSURE"],
}

PROFILE_IDS = tuple(f"CP{n:02d}" for n in range(1, 21))


def _offset(profile_id: str, batch_id: str, kind: str, modulo: int) -> int:
    seed = hashlib.sha256(f"{profile_id}|{batch_id}|{kind}".encode()).hexdigest()
    return int(seed[:8], 16) % modulo


def assign_plans(
    profile_id: str, batch_id: str, count: int
) -> list[dict[str, Any]]:
    """为一个 (批, 产品) 的 count 条请求发牌互异表达计划（确定性）。"""
    assert profile_id in PROFILE_IDS, profile_id
    arcs = NARRATIVE_ARCS[profile_id]
    o_off = _offset(profile_id, batch_id, "opening", len(OPENING_ARCHETYPES))
    e_off = _offset(profile_id, batch_id, "ending", len(ENDING_ARCHETYPES))
    t_off = _offset(profile_id, batch_id, "title", len(TITLE_ARCHETYPES))
    a_off = _offset(profile_id, batch_id, "arc", len(arcs))
    b_off = _offset(profile_id, batch_id, "body", len(BODY_ARCHITECTURES))
    s_off = _offset(profile_id, batch_id, "spoken", len(SPOKEN_FORMATS))
    au_off = _offset(profile_id, batch_id, "audio", len(AUDIO_SIGNATURES))
    bp_off = _offset(profile_id, batch_id, "boundary", len(BOUNDARY_POSITIONS))
    bs_off = _offset(profile_id, batch_id, "bstyle", len(BOUNDARY_STYLES))
    plans = []
    for i in range(count):
        opening = OPENING_ARCHETYPES[(o_off + i) % len(OPENING_ARCHETYPES)]
        # ending 用不同步长错开，避免 (opening, ending) 对锁死
        ending = ENDING_ARCHETYPES[(e_off + i * 5) % len(ENDING_ARCHETYPES)]
        title = TITLE_ARCHETYPES[(t_off + i) % len(TITLE_ARCHETYPES)]
        arc = arcs[(a_off + i) % len(arcs)]
        spoken = SPOKEN_FORMATS[(s_off + i) % len(SPOKEN_FORMATS)]
        boundary_pos = BOUNDARY_POSITIONS[(bp_off + i) % len(BOUNDARY_POSITIONS)]
        if boundary_pos == "SPOKEN_CARRIED" and spoken == "EMPTY_NO_SPOKEN":
            boundary_pos = "MID_WEAVE"  # 确定性冲突消解
        plans.append(
            {
                "plan_id": f"G3-PLAN-{batch_id}-{profile_id}-{i + 1:03d}",
                "opening_archetype": opening,
                "ending_archetype": ending,
                "title_archetype": title,
                "narrative_arc": arc,
                "body_architecture": BODY_ARCHITECTURES[(b_off + i) % len(BODY_ARCHITECTURES)],
                "spoken_format": spoken,
                "audio_signature": AUDIO_SIGNATURES[(au_off + i) % len(AUDIO_SIGNATURES)],
                "boundary_position": boundary_pos,
                "boundary_style": BOUNDARY_STYLES[(bs_off + i) % len(BOUNDARY_STYLES)],
                "boundary_realization": "INTEGRATED_FACT_LIMIT",
                "forbidden_patterns": [
                    "仍由X决定/确认/批准 式收尾",
                    "年份台账式履历骨架（除非叙事弧为 ARCHIVE_REVISIT）",
                    "『先排除…』标题句式（除非标题档型为 CONTRAST_HOOK 且本批首次）",
                    "证据名录+否定边界+缺料静默 统一骨架",
                    "『这只是…还没…』收尾句族（同产品全批至多1条）",
                    "合成披露语句内嵌受众正文（披露只在专用披露表面）",
                    "与同批同产品其他条目复用同一正文段式/口播句式/声音设计/边界措辞",
                ],
            }
        )
    return plans


# ---------------------------------------------------------------- 分类器
_TIME_OPEN_RE = re.compile(
    r"^((19|20)\d{2}年|[一二三四五六七八九十\d]+月|周[一二三四五六日]|"
    r"(早上|清晨|上午|中午|下午|傍晚|晚上|夜里|凌晨|开店前|开门前|收店|闭店|午后))"
)
_QUOTE_OPEN_RE = re.compile(r'^[「"“『]')
_NUMBER_OPEN_RE = re.compile(r"^\d")
_PLACE_OPEN_RE = re.compile(r"^.{0,8}(门店|店里|店内|仓库|工作室|样衣室|货架|收银台|试衣间)")
_GOV_DEFER_RE = re.compile(
    r"(仍|均|都|全部)?(由|归|交)[^，。；]{0,12}(决定|确认|批准|定夺|裁决|把关)")
_PENDING_RE = re.compile(r"(等待|待|尚未|还没|下一次|下周|下个月|再看|再测|复测|回访)")
_SNAPSHOT_RE = re.compile(r"(停在|记录到|截至|目前|现在|暂时|当下)")
_XIAN_TITLE_RE = re.compile(r"先")
_STATUS_DISCLAIM_RE = re.compile(
    r"(没有|不|未|只)[^。]{0,20}(确认|结论|状态|保证|资格|量产|上岗|寿命|得出|等于)")
_CITY_ARRIVAL_RE = re.compile(r"^.{0,14}(市|镇|城)[^，。]{0,10}门店")


def classify_opening(body_first: str) -> str:
    s = body_first.strip()
    if _CITY_ARRIVAL_RE.search(s):
        return "OPEN_CITY_ARRIVAL"  # 上一轮 CP18 模板："城市+门店+到货/来客"
    if _TIME_OPEN_RE.search(s):
        return "OPEN_TIME"
    if _QUOTE_OPEN_RE.search(s):
        return "OPEN_QUOTE"
    if "？" in s.split("。")[0]:
        return "OPEN_QUESTION"
    if _NUMBER_OPEN_RE.search(s):
        return "OPEN_NUMBER"
    if _PLACE_OPEN_RE.search(s):
        return "OPEN_PLACE"
    return "OPEN_OTHER"


def classify_ending(body_last: str) -> str:
    s = body_last.strip()
    if _GOV_DEFER_RE.search(s[-40:]):
        return "END_GOV_DEFER"  # 禁用类：治理让渡收尾（结尾位置）
    if _STATUS_DISCLAIM_RE.search(s[-32:]):
        return "END_STATUS_DISCLAIM"  # 上一轮 CP01/06 模板："没有X确认/结论/状态"
    if s.endswith("？"):
        return "END_QUESTION"
    if _PENDING_RE.search(s[-30:]):
        return "END_PENDING"
    if _SNAPSHOT_RE.search(s[-30:]):
        return "END_SNAPSHOT"
    return "END_OTHER"


def classify_title(title: str) -> str:
    s = title.strip()
    if _XIAN_TITLE_RE.search(s):
        return "TITLE_XIAN"
    if "？" in s:
        return "TITLE_QUESTION"
    if "：" in s or ":" in s:
        return "TITLE_COLON"
    if re.search(r"\d", s):
        return "TITLE_NUMBER"
    return "TITLE_OTHER"


def skeleton_signature(output: Mapping[str, Any]) -> dict[str, str]:
    """一条序列化输出的骨架签名（供集中度门与前缀撞车门）。"""
    body = list(output["body"])
    return {
        "opening_class": classify_opening(body[0]),
        "ending_class": classify_ending(body[-1]),
        "title_class": classify_title(str(output["title"])),
        "opening_prefix6": re.sub(r"\s", "", body[0])[:6],
        "ending_suffix6": re.sub(r"\s", "", body[-1])[-6:],
        "title_prefix4": re.sub(r"\s", "", str(output["title"]))[:4],
    }


def concentration_findings(
    outputs: Sequence[Mapping[str, Any]], per_profile_cap: int = 2
) -> list[dict[str, Any]]:
    """批级骨架集中度：同产品内相同 opening/ending/title 类 > cap，
    或 6 字前后缀/4 字标题前缀精确撞车 → 触发发现（供门与人审）。"""
    by_profile: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for out in outputs:
        sig = skeleton_signature(out)
        by_profile.setdefault(str(out["profile_id"]), []).append(
            (str(out["request_id"]), sig))
    findings: list[dict[str, Any]] = []
    for profile_id in sorted(by_profile):
        rows = by_profile[profile_id]
        for key, kind in (
            ("opening_class", "OPENING_CLASS_CONCENTRATION"),
            ("ending_class", "ENDING_CLASS_CONCENTRATION"),
            ("title_class", "TITLE_CLASS_CONCENTRATION"),
        ):
            groups: dict[str, list[str]] = {}
            for rid, sig in rows:
                if not sig[key].endswith("_OTHER"):
                    groups.setdefault(sig[key], []).append(rid)
            for cls in sorted(groups):
                if len(groups[cls]) > per_profile_cap:
                    findings.append({"kind": kind, "profile_id": profile_id,
                                     "class": cls, "request_ids": sorted(groups[cls])})
        for key, kind in (
            ("opening_prefix6", "OPENING_PREFIX_COLLISION"),
            ("ending_suffix6", "ENDING_SUFFIX_COLLISION"),
            ("title_prefix4", "TITLE_PREFIX_COLLISION"),
        ):
            groups = {}
            for rid, sig in rows:
                if sig[key]:
                    groups.setdefault(sig[key], []).append(rid)
            for prefix in sorted(groups):
                if len(groups[prefix]) > 1:
                    findings.append({"kind": kind, "profile_id": profile_id,
                                     "class": prefix, "request_ids": sorted(groups[prefix])})
        # 治理让渡收尾单独归零（任何一条即发现）
        for rid, sig in rows:
            if sig["ending_class"] == "END_GOV_DEFER":
                findings.append({"kind": "GOV_DEFER_ENDING", "profile_id": profile_id,
                                 "class": "END_GOV_DEFER", "request_ids": [rid]})
    # v3：限度句族 / 声音写法模板家族 集中度（第2轮病灶机器化，per-CP cap 同上）
    findings += _family_concentration(outputs, per_profile_cap)
    return findings


def _audience_prose(out: Mapping[str, Any]) -> str:
    """限度句族扫描面：标题+正文+口播+CTA+画面（限度可由画面承载）。"""
    parts = [str(out["title"]), *map(str, out["body"]),
             *map(str, out["spoken_lines"]), str(out["cta"]),
             *map(str, out["visual_execution"])]
    return "\n".join(parts)


def _family_concentration(
    outputs: Sequence[Mapping[str, Any]],
    per_profile_cap: int = 2,
    batch_cap: int = 8,
) -> list[dict[str, Any]]:
    """限度句族 / 声音模板家族集中度，双层：
    - 同产品内同族 > per_profile_cap → *_CONCENTRATION（第2轮同产品成套复用）；
    - 全批同族 > batch_cap → *_BATCH_CONCENTRATION（第2轮声音写法跨产品坍缩：
      每产品仅 1-2 条被发牌到该签名，但批内 50/120 用同一行话公式）。"""
    specs = (
        ("BOUNDARY_FAMILY_CONCENTRATION", BOUNDARY_FAMILY_PATTERNS,
         _audience_prose),
        ("AUDIO_TEMPLATE_CONCENTRATION", AUDIO_TEMPLATE_PATTERNS,
         lambda o: "\n".join(map(str, o["audio_execution"]))),
    )
    findings: list[dict[str, Any]] = []
    by_profile: dict[str, list[Mapping[str, Any]]] = {}
    for out in outputs:
        by_profile.setdefault(str(out["profile_id"]), []).append(out)
    for kind, patterns, extractor in specs:
        for family in sorted(patterns):
            pattern = re.compile(patterns[family])
            batch_hits: list[str] = []
            for profile_id in sorted(by_profile):
                rows = by_profile[profile_id]
                hit_ids = sorted(str(o["request_id"]) for o in rows
                                 if pattern.search(extractor(o)))
                batch_hits += hit_ids
                if len(hit_ids) > per_profile_cap:
                    findings.append({"kind": kind, "profile_id": profile_id,
                                     "class": family, "request_ids": hit_ids})
            if len(batch_hits) > batch_cap:
                findings.append({"kind": f"{kind.rsplit('_', 1)[0]}"
                                 "_BATCH_CONCENTRATION",
                                 "profile_id": "BATCH", "class": family,
                                 "request_ids": sorted(batch_hits)})
    return findings


__all__ = [
    "ENDING_ARCHETYPES",
    "NARRATIVE_ARCS",
    "OPENING_ARCHETYPES",
    "PROFILE_IDS",
    "TITLE_ARCHETYPES",
    "AUDIO_TEMPLATE_PATTERNS",
    "BOUNDARY_FAMILY_PATTERNS",
    "BOUNDARY_STYLES",
    "assign_plans",
    "classify_ending",
    "classify_opening",
    "classify_title",
    "concentration_findings",
    "skeleton_signature",
]
