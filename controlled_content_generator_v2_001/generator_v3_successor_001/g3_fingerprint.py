#!/usr/bin/env python3
"""G3 · 20 内容产品指纹合同（入口信号 + 邻品对比义务 + 机器谓词）。

依据 V1.1 标准 L549-568 产品定义与上一轮盲判混淆矩阵
（CP01→CP03/CP17、CP07→CP13/CP09、CP06→CP08、CP02→CP17）。
机器谓词只判可确定性检测的表面信号（词族共现），不判语义好坏；
谓词不通过 → REVIEW_FLAG 进入人审复核，不直接机器硬失败。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

# 每产品：入口信号义务（作者义务，人审判据）、邻品对比义务、机器谓词
# 谓词格式: {"predicate_id", "scope"(title|body_head|full), "all_of": [regex...]}
FINGERPRINT_CONTRACTS: dict[str, dict[str, Any]] = {
    "CP01": {
        "entry_signal_duty": "前两段必须让'谁（岗位人格）在完成什么任务'可见：出场人物+岗位+任务目标，人不能退成工序旁白。",
        "neighbor_contrast_duties": [
            "区别于CP03：不是工序全过程，是一个人完成一件任务的动作链与判断，人的在场感必须贯穿。",
            "区别于CP17：陈列调整只是任务载体时，重心在执行者的动作与判断，不在空间实验假设。",
            "区别于CP06：判断为完成任务服务，不独立成切片。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP01_PERSON_EARLY", "scope": "body_head",
             "all_of": [r"(师|员|工|长|生|徒|[林沈岑陆闻][一-鿿])"]},
            {"predicate_id": "CP01_ACTION_CHAIN", "scope": "full",
             "all_of": [r"(先|再|然后|接着|随后)", r"(完成|停在|消失|通过|改成|达到|留下|收尾)"]},
        ],
    },
    "CP02": {
        "entry_signal_duty": "开场即建立'时段+空间'观察框架：几点到几点/哪个时段、店内哪个区域，多主体并行，不聚焦单人任务。",
        "neighbor_contrast_duties": [
            "区别于CP01：无单一主角任务线，是时段内多点位状态与节奏。",
            "区别于CP17：记录当下时段实况，不是陈列实验的假设与验证。",
            "区别于CP18：尺度在店内时段，不上升到城市街区。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP02_TIME_WINDOW", "scope": "body_head",
             "all_of": [r"(\d{1,2}[:：]\d{2}|点半?|时段|早班|晚班|高峰|开店|闭店|午后|傍晚)"]},
            {"predicate_id": "CP02_MULTI_SPOT", "scope": "full",
             "all_of": [r"(入口|货架|试衣间|收银|橱窗|通道|门口|桌|台)"]},
        ],
    },
    "CP03": {
        "entry_signal_duty": "以'一项手艺从起点到终点'为轴，工序完整不剪断，材料与手的接触细节可见。",
        "neighbor_contrast_duties": [
            "区别于CP01：主角是手艺与工序本身，人物服务于工序完整性。",
            "区别于CP08：呈现制作过程，不做结构解构与穿着结果推理。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP03_PROCESS_CHAIN", "scope": "full",
             "all_of": [r"(第[一二三四五六七八九十]+(步|道)|先.{1,30}(再|然后))",
                        r"(缝|裁|烫|织|钉|锁|绱|拼|熨|定型|走线)"]},
        ],
    },
    "CP04": {
        "entry_signal_duty": "至少两个岗位的真实分工与交接点可辨，交接物/交接时刻具体，不制造对立和假争吵。",
        "neighbor_contrast_duties": [
            "区别于CP01：重心在岗位之间的接口，不在单人任务弧。",
            "区别于CP02：有明确协作事件，不是时段全景观察。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP04_HANDOFF", "scope": "full",
             "all_of": [r"(交给|递给|转给|移交|接过|交接|通知|确认后)",
                        r"(师|员|工|长|组|岗)"]},
        ],
    },
    "CP05": {
        "entry_signal_duty": "跨时间的人物变化必须有时间证据（档案/记录/回访），但叙事入口不得固定为年份台账；变化本身（能做什么了）是主角。",
        "neighbor_contrast_duties": [
            "区别于CP06：是纵向成长史，不是单次判断切片。",
            "区别于CP10：证据服务于人的阶段变化，不是产品验证档案。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP05_TIME_EVIDENCE", "scope": "full",
             "all_of": [r"((19|20)\d{2}年|入职|第[一二三]年|[一二三四五六]年前|那年|当时)",
                        r"(记录|档案|台账|照片|留底|复盘纸|笔记)"]},
            {"predicate_id": "CP05_CHANGE_MARKER", "scope": "full",
             "all_of": [r"(从|开始|后来|如今|现在|变|第一次|不再)"]},
        ],
    },
    "CP06": {
        "entry_signal_duty": "'观察→判断→解释'三段可辨且判断主体（谁凭什么判断）明确；判断依据与适用边界都要落到具体信号。",
        "neighbor_contrast_duties": [
            "区别于CP08：判断是主角，工艺细节只是判断的证据，不做系统解构。",
            "区别于CP07：专家主动输出判断，不以用户提问开场。",
            "区别于CP03：不追工序完整，只切一个判断瞬间。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP06_OBSERVE_JUDGE", "scope": "full",
             "all_of": [r"(看|摸|听|量|捏|拉|比|对着光)",
                        r"(判断|看出|说明|意味着|可以确认|信号|就知道)"]},
            {"predicate_id": "CP06_BOUNDARY_SIGNAL", "scope": "full",
             "all_of": [r"(只|仅|除非|前提|范围|这种情况|不适用|另当别论)"]},
        ],
    },
    "CP07": {
        "entry_signal_duty": "必须以一个真实、具体的用户问题开场（问题原样出现），随后按条件给判断；适合搜索与收藏。",
        "neighbor_contrast_duties": [
            "区别于CP09：回答'我这个情况怎么办'，不是'什么人不适合什么'的反选规则。",
            "区别于CP13：解决具体提问，不铺陈衣橱角色叙事。",
            "区别于CP06：入口是用户的问题，不是专家的主动判断。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP07_QUESTION_ENTRY", "scope": "body_head",
             "all_of": [r"？"]},
            {"predicate_id": "CP07_CONDITION_ANSWER", "scope": "full",
             "all_of": [r"(如果|要是|取决于|分两种|先看|那就|情况)"]},
        ],
    },
    "CP08": {
        "entry_signal_duty": "结构/材料/工艺与穿着结果的因果关系是主角：把看不见的做法翻出来给人看，并回答'这对穿着意味着什么'。",
        "neighbor_contrast_duties": [
            "区别于CP03：解构已完成的结构，不追制作过程。",
            "区别于CP06：讲结构因果，不聚焦一次现场判断。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP08_STRUCTURE_REVEAL", "scope": "full",
             "all_of": [r"(缝|线|面料|版型|里料|衬|克重|组织|纱|织法)",
                        r"(翻到|拆开|截面|反面|内侧|透光|剖)"]},
            {"predicate_id": "CP08_WEAR_MEANING", "scope": "full",
             "all_of": [r"(穿|洗|磨|垂|贴|挺|变形|起球|舒适)"]},
        ],
    },
    "CP09": {
        "entry_signal_duty": "明确'适合谁、不适合谁、什么条件下、替代是什么'；语言坦白，不制造焦虑、不羞辱身体；标题句式不得批量复用'先排除'。",
        "neighbor_contrast_duties": [
            "区别于CP07：给稳定选择规则，不是诊断一个具体提问。",
            "区别于CP13：讲适用边界，不铺生活场景叙事。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP09_FIT_BOUNDARY", "scope": "full",
             "all_of": [r"(适合|不适合|不建议|更合适|换成|替代|另选)",
                        r"(如果|身高|肩|腰|场合|通勤|骑车|久坐|怕冷|条件)"]},
        ],
    },
    "CP10": {
        "entry_signal_duty": "测试条件、时间跨度、样本限制必须先于结论可见：什么条件下测了多久、看到什么、还不能说明什么。",
        "neighbor_contrast_duties": [
            "区别于CP05：验证的是产品/做法，不是人的成长。",
            "区别于CP20：是长期验证档案，不是对某句承诺的追踪兑现。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP10_TEST_PROTOCOL", "scope": "full",
             "all_of": [r"(测|洗|穿|挂|晒|记录)", r"(次|天|周|个月|小时)",
                        r"(条件|同一|对照|限于|样本)"]},
        ],
    },
    "CP11": {
        "entry_signal_duty": "至少一个真实取舍可见：曾有哪条路没走、为什么，代价说清楚。",
        "neighbor_contrast_duties": ["区别于CP12：讲诞生时的取舍，不是版本迭代日志。"],
        "machine_predicates": [
            {"predicate_id": "CP11_TRADEOFF", "scope": "full",
             "all_of": [r"(取舍|放弃|没有选|改成|换成|舍掉|保住|代价)"]},
        ],
    },
    "CP12": {
        "entry_signal_duty": "版本差异可对照：改了什么、为什么改、上一版的问题在哪。",
        "neighbor_contrast_duties": ["区别于CP11：从版本到版本的变化，不是初始设计取舍。"],
        "machine_predicates": [
            {"predicate_id": "CP12_VERSION_DIFF", "scope": "full",
             "all_of": [r"(版|批次|上一|这一版|第[一二三]版|改版)",
                        r"(改|调整|换|加|减|修)"]},
        ],
    },
    "CP13": {
        "entry_signal_duty": "衣物在真实生活里的角色可见：跟谁的生活、什么场景反复发生关系；不退化为普通穿搭种草。",
        "neighbor_contrast_duties": ["区别于CP09：讲陪伴与角色，不列适用规则。"],
        "machine_predicates": [
            {"predicate_id": "CP13_LIFE_SCENE", "scope": "full",
             "all_of": [r"(衣橱|一周|每天|通勤|周末|出差|家里|季节)",
                        r"(穿着|搭|换上|套上|带着)"]},
        ],
    },
    "CP14": {
        "entry_signal_duty": "物为主角、低旁白：光线、质地、运动中的物性细节是内容本体，声音真实。",
        "neighbor_contrast_duties": ["区别于CP08：呈现物性观感，不解构结构因果。"],
        "machine_predicates": [
            {"predicate_id": "CP14_OBJECT_SENSES", "scope": "full",
             "all_of": [r"(光|影|垂|摆|纹理|绒|滑|挺|皱|飘)",
                        r"(镜头|特写|慢|定格|贴近)"]},
        ],
    },
    "CP15": {
        "entry_signal_duty": "商品从到店到货架的站点链条可见：卸货/验收/挂烫/上架等真实后台动线。",
        "neighbor_contrast_duties": ["区别于CP02：跟随商品走动线，不是时段全景。"],
        "machine_predicates": [
            {"predicate_id": "CP15_LIFECYCLE", "scope": "full",
             "all_of": [r"(到店|卸|拆箱|验收|入库|挂烫|上架|补货|调拨)"]},
        ],
    },
    "CP16": {
        "entry_signal_duty": "一次真实服务的期望-实际-跟进可辨；尊重隐私，不把顾客工具化。",
        "neighbor_contrast_duties": ["区别于CP07：复盘一次服务过程，不是回答一个通用问题。"],
        "machine_predicates": [
            {"predicate_id": "CP16_SERVICE_REPLAY", "scope": "full",
             "all_of": [r"(顾客|客人|来店|进店|试穿|询问)",
                        r"(后来|跟进|回访|第二次|下次|之后)"]},
        ],
    },
    "CP17": {
        "entry_signal_duty": "空间假设与验证可辨：为什么这样摆、摆完观察到什么、下一步怎么调。",
        "neighbor_contrast_duties": [
            "区别于CP02：有明确陈列实验假设，不是时段记录。",
            "区别于CP01：重心在空间方案本身，不在执行者任务弧。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP17_SPACE_EXPERIMENT", "scope": "full",
             "all_of": [r"(陈列|橱窗|货架|动线|台面|模特|挂杆)",
                        r"(试|换|挪|调|对比|观察|假设|效果)"]},
        ],
    },
    "CP18": {
        "entry_signal_duty": "城市/街区/气候/人群的地方差异是主角，门店只是取景框；不得退化为'总部模板加地名'，声景要在地。",
        "neighbor_contrast_duties": [
            "区别于CP02：尺度在城市街区与季节，不在店内时段。",
            "区别于CP16：记录地方生活质感，不复盘单次服务。",
        ],
        "machine_predicates": [
            {"predicate_id": "CP18_LOCAL_TEXTURE", "scope": "full",
             "all_of": [r"(街|巷|码头|社区|城|镇|梅雨|海风|雪|潮|干燥|方言)",
                        r"(这里|本地|附近|街坊|常客|老城)"]},
        ],
    },
    "CP19": {
        "entry_signal_duty": "一次经营决策的取舍与代价可见：放弃了什么、为什么、结果如何；不自我感动。",
        "neighbor_contrast_duties": ["区别于CP11：经营层决策（订货/定价/排班/关档），不是产品设计取舍。"],
        "machine_predicates": [
            {"predicate_id": "CP19_DECISION_COST", "scope": "full",
             "all_of": [r"(决定|选择|放弃|砍掉|保留|押|赌|停掉)",
                        r"(成本|库存|销量|损耗|人手|租金|现金|订货)"]},
        ],
    },
    "CP20": {
        "entry_signal_duty": "对一句具体承诺的追踪：承诺原文、检查点、兑现证据或差距，证据优先。",
        "neighbor_contrast_duties": ["区别于CP10：跟踪的是承诺兑现，不是开放式长期验证。"],
        "machine_predicates": [
            {"predicate_id": "CP20_PROMISE_TRACK", "scope": "full",
             "all_of": [r"(承诺|答应|说过|保证|约定)",
                        r"(兑现|做到|差距|核对|检查|对照)"]},
        ],
    },
}


def fingerprint_contract(profile_id: str) -> dict[str, Any]:
    contract = FINGERPRINT_CONTRACTS[profile_id]
    return {
        "profile_id": profile_id,
        "entry_signal_duty": contract["entry_signal_duty"],
        "neighbor_contrast_duties": list(contract["neighbor_contrast_duties"]),
        "machine_predicates": [dict(p) for p in contract["machine_predicates"]],
    }


def _scope_text(output: Any, scope: str) -> str:
    body = list(output["body"])
    if scope == "title":
        return str(output["title"])
    if scope == "body_head":
        return str(output["title"]) + "\n" + "\n".join(body[:2])
    return "\n".join(
        [str(output["title"]), *body,
         *map(str, output.get("spoken_lines", [])),
         str(output.get("cta", ""))]
    )


def predicate_findings(output: Any) -> list[str]:
    """返回该输出未满足的指纹谓词 id 列表（REVIEW_FLAG 级）。"""
    profile_id = str(output["profile_id"])
    missing: list[str] = []
    for predicate in FINGERPRINT_CONTRACTS[profile_id]["machine_predicates"]:
        text = _scope_text(output, str(predicate["scope"]))
        if not all(re.search(pattern, text) for pattern in predicate["all_of"]):
            missing.append(str(predicate["predicate_id"]))
    return sorted(missing)


__all__ = ["FINGERPRINT_CONTRACTS", "fingerprint_contract", "predicate_findings"]
