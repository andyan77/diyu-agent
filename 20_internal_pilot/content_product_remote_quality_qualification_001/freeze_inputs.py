#!/usr/bin/env python3
"""Build and verify the one-time frozen inputs for the 20-product qualification."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Final

from market_reference_catalog import MARKET_REFERENCES


TASK_ROOT: Final = Path(__file__).resolve().parent
TASKS_PATH: Final = TASK_ROOT / "frozen_tasks.v1.jsonl"
REFERENCES_PATH: Final = TASK_ROOT / "market_references.v1.jsonl"
MANIFEST_PATH: Final = TASK_ROOT / "freeze_manifest.v1.json"
BASE_COMMIT: Final = "a588ca5c44d8243927f1d0b2d2349c29f14f8a4a"
FROZEN_AT: Final = "2026-07-19T01:17:57Z"

TOPIC_BRAND: Final = "品牌和企业故事"
TOPIC_FOUNDER: Final = "创始人或主理人的工作日常与观点"
TOPIC_PRODUCT: Final = "商品为什么这样设计"
TOPIC_STYLING: Final = "穿搭、试穿和选购建议"
TOPIC_STORE: Final = "门店日常与顾客服务"
TOPIC_TEAM: Final = "团队幕后、跨岗位协作和岗位成长"
TOPIC_DISPLAY: Final = "陈列调整与空间经营"
TOPIC_CITY: Final = "城市、区域与本地生活"
TOPIC_CONVERSION: Final = "活动、直播、咨询、到店、私域和复购承接"
TOPIC_ORGANIZATION: Final = "招商、招聘与组织信任"
# fmt: off
TOPICS: Final = frozenset(
    {
        TOPIC_BRAND, TOPIC_FOUNDER, TOPIC_PRODUCT, TOPIC_STYLING, TOPIC_STORE,
        TOPIC_TEAM, TOPIC_DISPLAY, TOPIC_CITY, TOPIC_CONVERSION, TOPIC_ORGANIZATION,
    }
)

SCENARIOS: Final = (
    "EXPLICIT_REQUIREMENT",
    "AMBIGUOUS_REQUIREMENT",
    "SCOPED_BRAND_MATERIAL",
    "NO_MATERIAL_CREATION",
    "SELECT_THEN_REVISE",
)
SCENARIO_LABELS: Final = {
    "EXPLICIT_REQUIREMENT": "明确需求",
    "AMBIGUOUS_REQUIREMENT": "模糊需求",
    "SCOPED_BRAND_MATERIAL": "品牌资料辅助",
    "NO_MATERIAL_CREATION": "无资料创作",
    "SELECT_THEN_REVISE": "选择后修改",
}

ACCOUNT_OFFICIAL: Final = "笛语童装"
ACCOUNT_FOUNDER: Final = "林知远｜笛语"
ACCOUNT_PRODUCT: Final = "许闻川的产品记录"
ACCOUNT_DISPLAY: Final = "周静宜｜门店与陈列"
ACCOUNT_CONTENT: Final = "唐予安｜内容现场"
ACCOUNT_HANGZHOU: Final = "笛语杭州滨江店"
ACCOUNT_JIANGSU: Final = "笛语江苏"
ACCOUNT_REGIONAL_LEAD: Final = "顾知夏｜江苏笛语"
ACCOUNT_STYLING: Final = "许知宁｜搭配与门店服务"
ACCOUNT_SUZHOU: Final = "笛语苏州园区店"
ACCOUNT_WUXI: Final = "笛语无锡滨湖店"

ACCOUNT_METADATA: Final = {
    "笛语童装": ("品牌总部", "品牌价值判断者"),
    "林知远｜笛语": ("品牌总部", "品牌价值判断者"),
    "许闻川的产品记录": ("品牌总部", "产品验证记录者"),
    "周静宜｜门店与陈列": ("品牌总部", "门店与陈列观察者"),
    "唐予安｜内容现场": ("品牌总部", "品牌价值判断者"),
    "笛语杭州滨江店": ("门店", "门店与陈列观察者"),
    "笛语江苏": ("区域组织", "门店与陈列观察者"),
    "顾知夏｜江苏笛语": ("区域组织", "品牌价值判断者"),
    "许知宁｜搭配与门店服务": ("区域组织", "门店与陈列观察者"),
    "笛语苏州园区店": ("门店", "门店与陈列观察者"),
    "笛语无锡滨湖店": ("门店", "门店与陈列观察者"),
}

CONTEXT_BY_TOPIC: Final = {
    TOPIC_BRAND: ("希望了解品牌选择与长期行动的用户", "品牌认知"),
    TOPIC_FOUNDER: ("关注品牌经营判断与负责人观点的用户", "品牌认知"),
    TOPIC_PRODUCT: ("重视童装结构、工艺与验证依据的家长", "商品理解"),
    TOPIC_STYLING: ("需要按孩子生活场景做选购判断的家长", "引发咨询"),
    TOPIC_STORE: ("关注门店服务与真实零售日常的本地用户", "到店"),
    TOPIC_TEAM: ("关注真实岗位协作与职业成长的用户", "建立信任"),
    TOPIC_DISPLAY: ("关注童装陈列、空间与门店经营的从业者", "到店"),
    TOPIC_CITY: ("关注本地生活与社区门店的城市用户", "到店"),
    TOPIC_CONVERSION: ("正在咨询、到店或持续关注服务进度的用户", "复购"),
    TOPIC_ORGANIZATION: ("关注团队成长、招聘或区域合作的伙伴", "招聘"),
}
CONTEXT_BY_FORMAT: Final = {
    "直播内容包": ("正在直播间提问的家长与门店伙伴", "引发咨询"),
    "私域沟通内容": ("正在微信一对一或社群咨询的家长", "引发咨询"),
    "培训与门店话术": ("门店一线伙伴与带教负责人", "建立信任"),
    "陈列搭配": ("负责陈列执行与复看的门店伙伴", "到店"),
}
STORYLINES: Final = (
    ("内容为什么成立、何时应该停止", "这条内容凭什么成立"),
    ("一件商品怎样被验证和取舍", "为什么这次改了"),
    ("孩子当下真实使用与选择", "一个细节讲明白"),
    ("门店、陈列与服务的真实条件", "门店调整前后"),
)


@dataclasses.dataclass(frozen=True)
class ProductSpec:
    product_id: str
    label: str
    task_title: str
    topics: tuple[str, str, str, str, str]
    accounts: tuple[str, str, str, str, str]
    formats: tuple[str, str, str, str, str]
    messages: tuple[str, str, str, str, str]
    fuzzy_confirmation: str
    revision_instruction: str
    success_judgment: str


PRODUCTS: Final = (
    ProductSpec(
        "CP01",
        "岗位任务视频日志",
        "样衣复核的一个工作日",
        (TOPIC_TEAM, TOPIC_TEAM, TOPIC_TEAM, TOPIC_TEAM, TOPIC_TEAM),
        (ACCOUNT_PRODUCT, ACCOUNT_CONTENT, ACCOUNT_PRODUCT, ACCOUNT_CONTENT, ACCOUNT_PRODUCT),
        ("短视频", "短视频", "图文", "短视频", "短视频"),
        (
            "给商品同事做一条60秒工作记录：从收到一件样衣、核对活动量，到标记返改并留下当天结论。想看到真实动作和判断，不要企业宣传腔。",
            "想拍一下商品同事今天到底在忙什么，真实一点。",
            "请只结合这个账号当前有权看到的研发资料，记录商品同事完成的一项样衣复核；资料没有写到的细节不要冒充真实发生。",
            "不调用品牌资料。请把一家虚构童装团队里商品助理完成一次样衣尺寸复核的过程写成可拍的工作记录，并明确这是演绎场景。",
            "记录商品同事复核一件样衣的半天：开箱、试活动量、写返改点、交给版师；重点放在动作和判断。",
        ),
        "就按一次样衣复核来做，保留现场感和完整任务链。",
        "把旁白减少一半，多保留手上动作、环境声和最后的返改交接，其他任务节点不要丢。",
        "能辨认一个具体岗位围绕单一任务完成动作、判断和交接，而不是泛泛介绍团队。",
    ),
    ProductSpec(
        "CP02",
        "门店时段微纪录",
        "雨天开门后的四十分钟",
        (TOPIC_STORE, TOPIC_CITY, TOPIC_STORE, TOPIC_CITY, TOPIC_STORE),
        (ACCOUNT_HANGZHOU, ACCOUNT_HANGZHOU, ACCOUNT_HANGZHOU, ACCOUNT_HANGZHOU, ACCOUNT_HANGZHOU),
        ("短视频", "短视频", "图文", "短视频", "短视频"),
        (
            "拍杭州门店雨天开门后的40分钟：擦门口水迹、开灯、整理童装、迎来第一位顾客。做成30秒微纪录，不要硬卖货。",
            "想拍店里的一小会儿，让人觉得是真的门店生活。",
            "只用当前门店账号能访问的日常资料，写一个明确时段的门店微纪录；用真实可见的小事，不补造顾客隐私。",
            "不使用品牌资料。设定一个虚构童装店闭店前半小时的中性场景，写出空间、收尾任务和自然节奏，并标明演绎。",
            "做一条早班开门后的短纪录，跟着一名店员完成门口、货架和试衣区的三件小事。",
        ),
        "就拍开门后的前40分钟，按时间顺序做成短视频。",
        "改成固定机位和少量手持混合，删掉解释性口号，保留时间推进和三件真实小事。",
        "内容围绕一个清楚时段展开，空间、任务和人物节奏可感，不退化为门店宣传片。",
    ),
    ProductSpec(
        "CP03",
        "单项手艺全过程",
        "一件童装整烫上架",
        (TOPIC_DISPLAY, TOPIC_DISPLAY, TOPIC_DISPLAY, TOPIC_DISPLAY, TOPIC_DISPLAY),
        (ACCOUNT_DISPLAY, ACCOUNT_HANGZHOU, ACCOUNT_HANGZHOU, ACCOUNT_WUXI, ACCOUNT_DISPLAY),
        ("短视频", "图文", "培训与门店话术", "短视频", "短视频"),
        (
            "把一件童装从拆包装、检查、低温整烫、冷却到上架的全过程拍清楚，60秒，手部动作和关键判断都要看得到。",
            "店里有个小手艺想拍清楚，但我不知道怎么讲。",
            "结合这个门店账号当前可用的商品处理资料，做一份单项整烫上架全过程；只写资料支持的步骤和门店可执行动作。",
            "不用任何品牌资料。以虚构服装店的一条棉质长裤为例，演示从检查到整烫完成的完整过程，避免虚构性能承诺。",
            "做一条整烫上架的全过程，观众要看懂输入状态、每一步判断和最后的合格状态。",
        ),
        "就选整烫上架这个手艺，完整做出来。",
        "增加手部和熨斗移动的近景，并标出温度判断来自洗标；不要删掉冷却和复查两个步骤。",
        "单一工作对象从输入到结果的完整步骤连续，关键动作、判断点和完成状态均可执行。",
    ),
    ProductSpec(
        "CP04",
        "多岗位协作纪实",
        "一批新货的三次交接",
        (TOPIC_TEAM, TOPIC_ORGANIZATION, TOPIC_TEAM, TOPIC_ORGANIZATION, TOPIC_TEAM),
        (ACCOUNT_JIANGSU, ACCOUNT_CONTENT, ACCOUNT_JIANGSU, ACCOUNT_SUZHOU, ACCOUNT_JIANGSU),
        ("短视频", "图文", "培训与门店话术", "图文", "短视频"),
        (
            "记录一批新货到店后，收货、商品核对和陈列三个岗位怎样接力，重点拍清每次交接什么、谁确认、最后如何上架。",
            "想拍团队幕后，但别变成大家一起喊口号。",
            "只结合江苏账号有权访问的组织和到店资料，讲清一次跨岗位协作；不公开个人隐私，也不把资料外的冲突写成事实。",
            "不查品牌资料。设定一家虚构童装门店筹备周末上新的中性协作场景，写清三个岗位的权限、交接和共同结果。",
            "用一批到货商品做主线，记录仓储、店员和陈列人员从验收到上架的协作。",
        ),
        "就沿着一批货的流转拍，三次交接都要清楚。",
        "压缩人物对白，改用物品和单据推动故事，但保留每个岗位的动作、责任边界和交接结果。",
        "同一对象贯穿多个岗位，职责、交接和共同结果具体，不用集体口号代替协作。",
    ),
    ProductSpec(
        "CP05",
        "人物成长与职业史",
        "从理货新人到搭配顾问",
        (TOPIC_BRAND, TOPIC_ORGANIZATION, TOPIC_BRAND, TOPIC_ORGANIZATION, TOPIC_BRAND),
        (ACCOUNT_CONTENT, ACCOUNT_CONTENT, ACCOUNT_CONTENT, ACCOUNT_JIANGSU, ACCOUNT_CONTENT),
        ("图文", "短视频", "直播内容包", "图文", "图文"),
        (
            "讲一名门店伙伴三年的成长：最初只会理货，后来能独立判断搭配，再到带新人。请用三个时间节点和具体技能变化写成图文。",
            "想讲讲一个同事是怎么慢慢成长起来的，别太煽情。",
            "只使用当前账号获权的人物岗位资料，写一份职业成长故事；没得到确认的私人经历不要补写。",
            "不调用品牌资料。以虚构人物为主角，给出入行、第一次独立服务和带教三个明确节点，写成诚实标注的演绎职业史。",
            "写一个门店伙伴从理货新人到能够独立做搭配建议的三年变化，靠技能和选择推动，不靠苦情。",
        ),
        "就用三个职业节点来讲，重点放在技能怎么形成。",
        "去掉煽情形容和逆袭口号，每个阶段补一个具体学会的技能与一次选择，时间线保持不变。",
        "人物历程有真实或明确演绎的时间节点、技能形成与角色变化，不靠空泛励志完成成长。",
    ),
    ProductSpec(
        "CP06",
        "专业判断切片",
        "三个细节判断穿着场景",
        (TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_CONVERSION, TOPIC_CONVERSION),
        (ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT),
        ("图文", "短视频", "直播内容包", "培训与门店话术", "图文"),
        (
            "用领口开度、肩部余量和下摆长度三个可见细节，说明一件童装更适合什么活动场景，也说清判断的限制。",
            "想让这个账号显得专业一点，帮我找个不装腔的讲法。",
            "结合产品账号当前可访问的版型资料，从三个可见细节判断穿着场景：说明观察、理由和不能据此下的结论。",
            "不使用品牌资料。以一件虚构基础卫衣的三个可见结构为输入，写一段普通人听得懂的场景判断，并标注演绎边界。",
            "做一份从三个衣服细节判断日常活动适配的内容，先给观察，再给判断和限制。",
        ),
        "就讲三个看得见的细节，给普通家长听得懂的判断。",
        "把术语都换成人话，并把适用限制提前到每个判断后面；保留三个观察依据。",
        "可观察信号、专业判断、理由和适用限制一一对应，专业性来自判断过程而非头衔。",
    ),
    ProductSpec(
        "CP07",
        "用户问题诊断室",
        "雨天上学裤装怎么选",
        (TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING),
        (ACCOUNT_STYLING, ACCOUNT_STYLING, ACCOUNT_STYLING, ACCOUNT_SUZHOU, ACCOUNT_STYLING),
        ("图文", "直播内容包", "私域沟通内容", "培训与门店话术", "图文"),
        (
            "家长问雨天上学该选哪类裤装。请先分清路程、活动量和是否方便更换，再给条件化建议，不要直接推某一款。",
            "家长总问怎么选裤子，我也不知道该从哪问起。",
            "结合当前搭配服务账号有权访问的常见问题资料，完成一次问题诊断；资料不足时用条件问题而不是编造商品事实。",
            "不用品牌资料。针对‘孩子久坐后裤腰不舒服’这个通用问题，做一份中性诊断和选择路径，不推荐具体品牌。",
            "把雨天上学裤装选择做成诊断卡：先问三个条件，再排除不合适方案，最后给两条选择路径。",
        ),
        "就按路程、活动量和换衣条件来诊断，再做成完整内容。",
        "不要再列三条万能建议，改成条件决策树；保留用户问题、排除理由和两个可选方向。",
        "从用户症状或问题出发，经过条件追问、成因判断、排除和选择，而不是泛化推荐。",
    ),
    ProductSpec(
        "CP08",
        "工艺、面料、版型解构",
        "领口结构为什么这样做",
        (TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT),
        (ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT),
        ("图文", "短视频", "直播内容包", "培训与门店话术", "图文"),
        (
            "拆解一件童装领口：包边、领围开度和肩部连接分别看什么，它们可能怎样影响穿脱；不要从局部直接保证整件性能。",
            "这件衣服看起来没什么特别，想讲讲它为什么这样做。",
            "只结合产品账号当前可访问的结构资料，做一次部件解构；把可见结构、设计意图和未经验证的性能分开。",
            "不查品牌资料。以一件虚构圆领上衣为对象，解构三个通用结构细节，全部结论限定在演绎和可观察层。",
            "做一份领口结构解构，普通人能看懂每个部位、设计意图和使用影响。",
        ),
        "就从领口三个局部开始拆，图文要能照着拍。",
        "增加三个微距示意和结构对照，删除任何整件质量背书；保留设计意图与实际测试结论的区别。",
        "真实或明确演绎的部件、材料与结构被微观拆解，影响逻辑清楚且不越过局部证据边界。",
    ),
    ProductSpec(
        "CP09",
        "适用边界与反选指南",
        "什么时候别选宽松长裤",
        (TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING),
        (ACCOUNT_STYLING, ACCOUNT_STYLING, ACCOUNT_STYLING, ACCOUNT_WUXI, ACCOUNT_STYLING),
        ("图文", "直播内容包", "私域沟通内容", "培训与门店话术", "图文"),
        (
            "做一份宽松长裤反选指南：哪些活动、身高阶段和穿脱习惯可能不适合，分别给替代方向，不要把任何版型说成万能。",
            "这次不想一味推荐，能不能诚实讲讲什么人不适合。",
            "只用当前账号可访问的产品适用资料，写清适合、不适合和替代选择；资料外不虚构库存或尺码。",
            "不使用品牌资料。围绕通用宽松长裤写一份中性反选指南，条件和替代方案都来自用户给出的场景假设。",
            "把一条裤子的适用边界写成选购指南，先讲不适合，再讲适合和替代方案。",
        ),
        "就做诚实的反选指南，别回避不适合的情况。",
        "把三种不适合条件移到开头，每种紧跟一个替代方向；保留适合条件但不要弱化反选。",
        "条件、适合、不适合及替代选择完整，明确拒绝万能推荐并帮助用户主动排除。",
    ),
    ProductSpec(
        "CP10",
        "长期验证档案",
        "四周洗穿观察记录",
        (TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT),
        (ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT),
        ("图文", "短视频", "图文", "图文", "图文"),
        (
            "整理一件测试样衣四周的洗穿观察：每周条件、看到的变化、没法下的结论都写清，做成可继续追加的图文档案。",
            "想长期看看一件东西到底怎么样，但现在只有零散记录。",
            "结合产品账号当前获权的验证记录，按时间节点整理观察档案；不得把尚未记录的周次或测试结果补成事实。",
            "不用品牌资料。用户提供一件虚构样衣四个时间点的完整观察，请整理为演绎验证档案，不外推到同类商品。",
            "把四周洗穿记录做成一份长期档案，读者能看懂条件、变化和还不知道什么。",
        ),
        "就按四个时间点整理，明确哪些只是观察、哪些还待验证。",
        "给每个时间点补上使用条件和局限，删掉普遍化结论；保留可继续追加记录的结构。",
        "同一对象的条件、时间节点、记录、结果和局限连续可追踪，不用一次体验冒充长期结论。",
    ),
    ProductSpec(
        "CP11",
        "产品诞生与设计取舍",
        "两个门襟方案的取舍",
        (TOPIC_PRODUCT, TOPIC_BRAND, TOPIC_BRAND, TOPIC_BRAND, TOPIC_PRODUCT),
        (ACCOUNT_PRODUCT, ACCOUNT_FOUNDER, ACCOUNT_PRODUCT, ACCOUNT_OFFICIAL, ACCOUNT_PRODUCT),
        ("图文", "短视频", "直播内容包", "图文", "图文"),
        (
            "讲一件外套门襟从两个方案中选出最终方案的过程：需求是什么、放弃了什么、付出什么代价，做成图文幕后。",
            "想讲讲一个产品幕后，但不想只说设计师很用心。",
            "仅依据产品账号可访问的设计取舍资料，呈现需求、候选方案与最终选择；未记录的设计冲突不要补写。",
            "不查品牌资料。使用用户给出的虚构设计简报和两个门襟方案，写成明确标注的演绎取舍档案。",
            "做一份外套门襟方案的诞生记录，要看得到被放弃的方案、原因和最终代价。",
        ),
        "就沿着两个方案的比较来讲，别写成设计理念口号。",
        "把被放弃方案和它原本的优点提前，再说明最终方案付出的代价；需求和结果保持不变。",
        "需求、多个方案、最终选择、放弃项和代价构成完整决策过程，设计诚意由取舍体现。",
    ),
    ProductSpec(
        "CP12",
        "产品迭代与版本日志",
        "样衣从第一版到第二版",
        (TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT, TOPIC_PRODUCT),
        (ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT, ACCOUNT_PRODUCT),
        ("图文", "短视频", "私域沟通内容", "图文", "图文"),
        (
            "记录样衣V1到V2的三处变化：袖口、下摆和口袋分别为什么改、改后还要验证什么，做成版本日志。",
            "这次样衣改了不少，但我不知道怎么讲才不流水账。",
            "只使用当前账号有权访问的版本资料，整理变更点、触发原因和待验证项；不要虚构第三版。",
            "不用品牌资料。用户提供一件虚构童装两版差异，请整理为演绎版本日志，并保留未验证项。",
            "把V1到V2的三处变化写成版本日志，读者要知道为什么改和下一步看什么。",
        ),
        "就按三处变化来做，原因和待验证项都要保留。",
        "压缩背景说明，把时间线和三处变化做成更清楚的对照；每一项都补上下一步验证。",
        "版本、变更点、触发原因和待验证事项清楚对应，不把一次修改包装成最终定论。",
    ),
    ProductSpec(
        "CP13",
        "产品的生活与衣橱角色",
        "一件外套的三个生活任务",
        (TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING),
        (ACCOUNT_STYLING, ACCOUNT_STYLING, ACCOUNT_STYLING, ACCOUNT_SUZHOU, ACCOUNT_STYLING),
        ("短视频", "图文", "直播内容包", "私域沟通内容", "陈列搭配"),
        (
            "用上学路上、周末公园和室内阅读三个场景，讲一件轻外套在孩子衣橱里分别承担什么角色，不做万能穿搭。",
            "想拍这件衣服怎么融进日常，而不是只拍三套搭配。",
            "结合当前搭配账号有权访问的商品与场景资料，讲清一件单品的衣橱角色；未确认的尺码和库存不写。",
            "不使用品牌资料。以通用轻外套和三个虚构生活场景为输入，写一份中性衣橱角色内容。",
            "做一份轻外套的生活角色内容，用三个真实感场景说明它为什么会被反复拿出来。",
        ),
        "就用三个生活任务来讲，不要只做搭配清单。",
        "把室内阅读替换为短途旅行收纳场景，但保持‘生活任务—衣橱角色’逻辑和另外两个场景。",
        "产品与场景、季节、动作和已有衣橱形成关系，内容回答它在生活中承担什么而非只列搭配。",
    ),
    ProductSpec(
        "CP14",
        "物性影像与感官短片",
        "光线、回弹和摩擦声",
        (TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING, TOPIC_STYLING),
        (ACCOUNT_PRODUCT, ACCOUNT_CONTENT, ACCOUNT_PRODUCT, ACCOUNT_CONTENT, ACCOUNT_PRODUCT),
        ("短视频", "短视频", "图文", "陈列搭配", "短视频"),
        (
            "拍一条15秒低旁白质感短片：侧光看纹理、手压看回弹、近距离收摩擦声。只表现可拍到的物性，不加功能承诺。",
            "想把一块面料拍得有质感，但不想全靠慢镜头和空话。",
            "只结合产品账号有权访问的材质资料，设计一条以光、动作和真实声音为主的短片；资料未证实的性能不写。",
            "不用品牌资料。以一块虚构中性针织面料为对象，设计明确标注演绎的感官画面和原声方案。",
            "做一条面料质感短片，重点是侧光纹理、回弹动作和摩擦原声，语言尽量少。",
        ),
        "就用光线、动作和原声三个层次来做，15秒内完成。",
        "去掉背景音乐和大部分字幕，加强原声、微距和一次完整回弹动作；不要新增性能结论。",
        "光线、动作和真实声音承担主要表达，观众能感到物性而非只听到抽象质感形容。",
    ),
    ProductSpec(
        "CP15",
        "商品到店生命周期",
        "一批商品从到货到上架",
        (TOPIC_STORE, TOPIC_STORE, TOPIC_CONVERSION, TOPIC_CONVERSION, TOPIC_TEAM),
        (ACCOUNT_HANGZHOU, ACCOUNT_JIANGSU, ACCOUNT_HANGZHOU, ACCOUNT_JIANGSU, ACCOUNT_HANGZHOU),
        ("短视频", "图文", "私域沟通内容", "培训与门店话术", "短视频"),
        (
            "跟拍一批商品到店后的验收、拆包、整烫、上架和补货记录，讲清每一步由谁接手、什么状态才进入下一步。",
            "新货到了想拍一条，但不想只是开箱。",
            "只使用当前门店账号获权的到货资料，做一份商品流转记录；不公开内部单号和未授权库存。",
            "不用品牌资料。设定一批虚构童装从到货到上架的中性流程，标明演绎且不冒充真实库存。",
            "做一条新货到店全流程，跟着同一批货从后门一直到货架。",
        ),
        "就沿着同一批货的状态变化来拍，不停在开箱。",
        "补清验收后交给整烫人员的交接点，降低促销感；保留从到货到上架的完整状态链。",
        "同一商品批次跨越到货、验收、处理、上架及后续状态，岗位接力与状态门槛明确。",
    ),
    ProductSpec(
        "CP16",
        "服务复盘",
        "一次尺码选择怎样调整",
        (TOPIC_STORE, TOPIC_STYLING, TOPIC_CONVERSION, TOPIC_CONVERSION, TOPIC_STYLING),
        (ACCOUNT_WUXI, ACCOUNT_STYLING, ACCOUNT_WUXI, ACCOUNT_WUXI, ACCOUNT_STYLING),
        ("短视频", "图文", "直播内容包", "私域沟通内容", "培训与门店话术"),
        (
            "匿名复盘一次尺码选择服务：家长原本想买大一码，店员问了穿着场景后调整方案，最后保留了什么选择。不要写成导购英雄故事。",
            "想复盘一次接待，但又怕像在表扬自己。",
            "只用当前门店账号获权的匿名服务资料，复盘需求、判断、方案调整和结果；不得补写可识别顾客信息。",
            "不用品牌资料。以虚构匿名服务情境写一次平等视角的选择复盘，清楚标注演绎。",
            "复盘一次家长和店员共同调整尺码方案的过程，重点是问题怎么被重新理解。",
        ),
        "就按需求变化来复盘，别把店员写成拯救者。",
        "改成顾客与店员共同判断的平等视角，压缩自我表扬；保留原需求、调整理由和最终结果。",
        "匿名需求、判断、方案调整与结果完整，服务者不被英雄化，用户选择权清楚。",
    ),
    ProductSpec(
        "CP17",
        "陈列换陈与空间实验",
        "入口一米区域的换陈实验",
        (TOPIC_DISPLAY, TOPIC_DISPLAY, TOPIC_DISPLAY, TOPIC_DISPLAY, TOPIC_DISPLAY),
        (ACCOUNT_DISPLAY, ACCOUNT_HANGZHOU, ACCOUNT_DISPLAY, ACCOUNT_SUZHOU, ACCOUNT_WUXI),
        ("陈列搭配", "短视频", "图文", "陈列搭配", "陈列搭配"),
        (
            "对门店入口一米区域做一次换陈实验：先提出通道更清楚的假设，用固定机位记录调整前后，并说明还要观察什么。",
            "想把橱窗和入口调一下，但现在只有‘看着有点乱’这个感觉。",
            "结合陈列账号当前有权访问的空间与商品资料，设计一次可复核的换陈实验；未确认库存只列待核对。",
            "不使用品牌资料。用户提供一个虚构小店入口尺寸和五件中性商品，请做明确标注演绎的空间实验。",
            "做一份入口一米区域的陈列调整，必须有假设、动作、前后固定视点和复看计划。",
        ),
        "就先解决入口视觉拥挤，做一次能前后对比的实验。",
        "把主色从同色聚合改为深浅分层，但保留通道假设、固定视点和复看指标，不新增库存。",
        "空间假设、调整动作、前后固定视点和谨慎复核闭环完整，陈列不是纯审美描述。",
    ),
    ProductSpec(
        "CP18",
        "城市门店生活志",
        "苏州雨天早班的街区声景",
        (TOPIC_CITY, TOPIC_STORE, TOPIC_CITY, TOPIC_CITY, TOPIC_STORE),
        (ACCOUNT_SUZHOU, ACCOUNT_SUZHOU, ACCOUNT_SUZHOU, ACCOUNT_SUZHOU, ACCOUNT_SUZHOU),
        ("短视频", "短视频", "图文", "私域沟通内容", "短视频"),
        (
            "记录苏州雨天早班：街区雨声、门口伞架、第一轮整理和店员对湿滑通道的处理，让门店真正处在城市生活里。",
            "想拍出本地门店的味道，又不想硬贴城市标签。",
            "只使用苏州门店账号可访问的本地生活资料，写一段城市门店记录；资料没有的地方习惯和常客关系不要编。",
            "不用品牌资料。用户给出一个虚构江南城市雨天街区与门店线索，请写成明确标注演绎的生活志。",
            "做一条雨天早班门店生活短片，城市声音、门口变化和店员动作都要在场。",
        ),
        "就从雨声和门口变化切入，拍成一段本地生活记录。",
        "删掉总部式品牌口号，增加街区雨声、伞架和湿滑通道三个细节；不要编地方习俗。",
        "城市、气候、街区声景与门店日常形成真实或明确演绎的本地关系，不靠地名贴纸。",
    ),
    ProductSpec(
        "CP19",
        "经营取舍与决策复盘",
        "一次延期活动的选择",
        (TOPIC_BRAND, TOPIC_FOUNDER, TOPIC_BRAND, TOPIC_CONVERSION, TOPIC_FOUNDER),
        (ACCOUNT_REGIONAL_LEAD, ACCOUNT_REGIONAL_LEAD, ACCOUNT_REGIONAL_LEAD, ACCOUNT_JIANGSU, ACCOUNT_FOUNDER),
        ("图文", "短视频", "直播内容包", "私域沟通内容", "图文"),
        (
            "复盘一次因连续降雨而延期门店活动的决定：原方案、备选项、放弃什么、承担什么代价以及后来结果都要写清。",
            "想讲一次不容易的决定，但不想写成老板英明。",
            "只结合江苏账号获权的经营记录，做一次决策复盘；资料没给出的损失数字和结果不要补写。",
            "不调用品牌资料。用户提供一个虚构门店活动延期的完整选择过程，请写成标注演绎的经营复盘。",
            "复盘一次活动延期决定，重点讲被放弃的方案、实际代价和事后怎么看。",
        ),
        "就围绕延期这个决定做完整复盘，不给决策者贴英雄标签。",
        "把放弃项和实际代价前置，压缩背景口号；保留备选方案、执行结果和仍有争议的部分。",
        "背景、选项、选择、放弃、代价与结果完整，经营判断可以被复核而非事后神化。",
    ),
    ProductSpec(
        "CP20",
        "承诺与兑现追踪",
        "一项交付承诺的三次核对",
        (TOPIC_BRAND, TOPIC_ORGANIZATION, TOPIC_CONVERSION, TOPIC_ORGANIZATION, TOPIC_BRAND),
        (ACCOUNT_OFFICIAL, ACCOUNT_JIANGSU, ACCOUNT_OFFICIAL, ACCOUNT_JIANGSU, ACCOUNT_OFFICIAL),
        ("图文", "短视频", "私域沟通内容", "培训与门店话术", "图文"),
        (
            "追踪一项‘每周五更新门店问题处理进度’的公开承诺：谁承诺、三个节点做了什么、哪里偏差、怎样修正、下次何时复核。",
            "想跟大家交代一件之前答应过的事，不知道怎么说才不空。",
            "只使用总部账号有权访问的承诺和进度资料，做一份兑现追踪；不要把未完成写成已经完成。",
            "不用品牌资料。用户提供一个虚构组织的承诺及三个时间点结果，请写成明确标注演绎的追踪记录。",
            "把一项每周更新进度的承诺做成三节点追踪，偏差和修正都要诚实出现。",
        ),
        "就按承诺、三个节点、偏差和下一次复核来写。",
        "补清第二个节点的偏差、修正责任人和下一次复核日期；不要改变原承诺或把未完成包装成完成。",
        "承诺主体、节点、执行、偏差、修正与下次复核完整，完成和未完成状态诚实可核对。",
    ),
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(_json_bytes(row) for row in rows)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _product_spec(product_id: str) -> ProductSpec:
    matches = [spec for spec in PRODUCTS if spec.product_id == product_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one product specification for {product_id}")
    return matches[0]


def _market_task_index(spec: ProductSpec) -> int:
    matches = [
        reference
        for reference in MARKET_REFERENCES
        if reference.product_id == spec.product_id
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one market reference for {spec.product_id}")
    try:
        return spec.formats.index(matches[0].content_format)
    except ValueError as exc:
        raise ValueError(
            f"Market format is absent from frozen tasks for {spec.product_id}"
        ) from exc


def _platform_for(content_format: str, scenario_index: int) -> str:
    if content_format == "短视频":
        return "抖音" if scenario_index % 2 == 0 else "视频号"
    if content_format == "图文":
        return "小红书" if scenario_index % 2 == 0 else "公众号或图文"
    if content_format == "直播内容包":
        return "视频号"
    if content_format == "陈列搭配":
        return "小红书"
    return "其他"


def _duration_for(content_format: str) -> str:
    return {
        "短视频": "60秒左右",
        "图文": "1至3分钟",
        "直播内容包": "15至30分钟",
        "私域沟通内容": "1至3分钟",
        "培训与门店话术": "5至15分钟",
        "陈列搭配": "1至3分钟",
    }[content_format]


def _message_for(message: str, content_format: str) -> str:
    delivery_hint = {
        "私域沟通内容": "成品用于微信一对一或社群，请按真实对话节奏组织。",
        "培训与门店话术": "成品用于门店晨会或内部培训，请给出可执行的话术与步骤。",
    }.get(content_format)
    return f"{message} {delivery_hint}" if delivery_hint is not None else message


FUZZY_NULL_FIELDS: Final = frozenset(
    {
        "topic_label", "primary_audience", "content_goal", "key_takeaway", "speaker_role_name",
        "storyline_name", "column_name", "organization_level", "business_goal", "content_direction",
        "content_identity", "long_term_storyline", "expression_method",
    }
)


def _fuzzy_prelude(source: dict[str, Any], message: str) -> dict[str, Any]:
    defaults = {
        **source,
        "operation": "找点灵感",
        "message": message,
        "target_platform": "其他",
        "duration_label": "由系统建议",
        "expression_feeling": "由系统建议",
        "content_format": "图文",
        "localization_allowed": False,
    }
    return {key: None if key in FUZZY_NULL_FIELDS else value for key, value in defaults.items()}


def _expression_fields(product_number: int) -> dict[str, str]:
    if product_number in {1, 2, 4, 5, 15, 18, 19, 20}:
        direction, storyline, method, feeling = "真实组织与幕后", "一群人如何把品牌做好", "纪实", "真实记录"
        identity = "区域经营身份" if product_number in {18, 19} else "品牌价值身份"
    elif product_number in {3, 6, 8, 10, 11, 12, 14}:
        direction, identity, storyline = "商品专业解释", "专业身份", "商品为什么这样设计"
        method = "演示" if product_number in {3, 8, 14} else "对比"
        feeling = "专业讲明白" if product_number != 14 else "质感画面"
    elif product_number in {7, 9, 13, 16}:
        direction, identity, storyline, feeling = "消费者生活与穿搭判断", "门店关系身份", "衣服如何服务真实生活", "生活分享"
        method = "问答" if product_number in {7, 9, 16} else "故事"
    else:
        direction, identity, storyline, method, feeling = (
            "真实组织与幕后", "商品或栏目身份", "一群人如何把品牌做好", "观察", "门店日常"
        )
    return {
        "content_direction": direction,
        "content_identity": identity,
        "long_term_storyline": storyline,
        "expression_method": method,
        "expression_feeling": feeling,
    }

# fmt: on


def build_tasks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for product_index, spec in enumerate(PRODUCTS):
        product_number = product_index + 1
        market_task_index = _market_task_index(spec)
        expression = _expression_fields(product_number)
        storyline_name, column_name = STORYLINES[product_index % len(STORYLINES)]
        for scenario_index, scenario in enumerate(SCENARIOS):
            account = spec.accounts[scenario_index]
            organization_level, speaker_role_name = ACCOUNT_METADATA[account]
            content_format = spec.formats[scenario_index]
            topic = spec.topics[scenario_index]
            audience, business_goal = CONTEXT_BY_FORMAT.get(
                content_format, CONTEXT_BY_TOPIC[topic]
            )
            task_id = f"Q20-{spec.product_id}-S{scenario_index + 1}"
            material_kinds = {
                "EXPLICIT_REQUIREMENT": ["一段故事或概要"],
                "AMBIGUOUS_REQUIREMENT": ["一个想法"],
                "SCOPED_BRAND_MATERIAL": ["商品或活动事实"],
                "NO_MATERIAL_CREATION": ["什么都没有"],
                "SELECT_THEN_REVISE": ["一段故事或概要"],
            }[scenario]
            author_visible = {
                "account_display_name": account,
                "operation": "直接做内容",
                "topic_label": topic,
                "primary_audience": audience,
                "message": _message_for(spec.messages[scenario_index], content_format),
                "target_platform": _platform_for(content_format, scenario_index),
                "candidate_number": None,
                "content_goal": spec.task_title,
                "key_takeaway": spec.success_judgment,
                "speaker_role_name": speaker_role_name,
                "storyline_name": storyline_name,
                "column_name": column_name,
                "continue_previous": False,
                "localization_allowed": organization_level != "品牌总部",
                "duration_label": _duration_for(content_format),
                "content_format": content_format,
                "organization_level": organization_level,
                "business_goal": business_goal,
                "existing_material_kinds": material_kinds,
                **expression,
            }
            rows.append(
                {
                    "schema": "diyu.q20.frozen_task.v1",
                    "task_id": task_id,
                    "ordinal": len(rows) + 1,
                    "frozen_at": FROZEN_AT,
                    "frozen_before_official_output": True,
                    "internal": {
                        "expected_product_id": spec.product_id,
                        "expected_product_label": spec.label,
                        "hidden_from_author": True,
                        "hidden_from_first_blind_review": True,
                    },
                    "scenario": {
                        "id": scenario,
                        "label": SCENARIO_LABELS[scenario],
                        "browser_session_group": f"BROWSER-{scenario_index + 1:02d}",
                    },
                    "task_title": f"{spec.task_title}·{SCENARIO_LABELS[scenario]}",
                    "author_visible_request": author_visible,
                    "fuzzy_prelude": (
                        _fuzzy_prelude(author_visible, spec.messages[scenario_index])
                        if scenario == "AMBIGUOUS_REQUIREMENT"
                        else None
                    ),
                    "fuzzy_confirmation": (
                        spec.fuzzy_confirmation
                        if scenario == "AMBIGUOUS_REQUIREMENT"
                        else None
                    ),
                    "revision_instruction": (
                        spec.revision_instruction
                        if scenario == "SELECT_THEN_REVISE"
                        else None
                    ),
                    "selection_policy": "BLIND_ORDINARY_USER_BEFORE_REVIEW",
                    "success_judgment": spec.success_judgment,
                    "market_comparison_task": scenario_index == market_task_index,
                    "automatic_publish": False,
                    "real_customer_data": False,
                }
            )
    return rows


def build_references() -> list[dict[str, Any]]:
    return [
        {
            "schema": "diyu.q20.market_reference.v1",
            "reference_id": f"Q20-MARKET-{row.product_id}",
            "product_id": row.product_id,
            "matched_task_id": (
                f"Q20-{row.product_id}-"
                f"S{_market_task_index(_product_spec(row.product_id)) + 1}"
            ),
            "title": row.title,
            "publisher": row.publisher,
            "url": row.url,
            "published_date": row.published_date,
            "summary": row.summary,
            "comparability": row.comparability,
            "content_format": row.content_format,
            "frozen_at": FROZEN_AT,
            "frozen_before_official_output": True,
            "full_copyrighted_body_copied": False,
            "private_access_used": False,
        }
        for row in MARKET_REFERENCES
    ]


def expected_files() -> tuple[bytes, bytes, bytes]:
    task_rows = build_tasks()
    covered_topics = {
        str(row["author_visible_request"]["topic_label"]) for row in task_rows
    }
    if covered_topics != TOPICS:
        raise ValueError(
            "Frozen tasks must cover exactly the ten current portal topics"
        )
    reference_rows = build_references()
    task_by_id = {str(row["task_id"]): row for row in task_rows}
    for reference in reference_rows:
        matched = task_by_id[str(reference["matched_task_id"])]
        request = matched["author_visible_request"]
        if reference["content_format"] != request["content_format"]:
            raise ValueError("Market references must match the frozen task format")
    tasks = _jsonl_bytes(task_rows)
    references = _jsonl_bytes(reference_rows)
    manifest = _json_bytes(
        {
            "schema": "diyu.q20.freeze_manifest.v1",
            "task_id": "DIYU_20_CONTENT_PRODUCTS_REMOTE_QUALITY_QUALIFICATION_001",
            "frozen_at": FROZEN_AT,
            "base_commit": BASE_COMMIT,
            "official_task_count": 100,
            "content_product_count": 20,
            "tasks_per_product": 5,
            "market_reference_count": 20,
            "official_model_calls_before_freeze": 0,
            "frozen_once": True,
            "tasks_sha256": _sha256(tasks),
            "market_references_sha256": _sha256(references),
            "old_package10_results_consumed": False,
        }
    )
    return tasks, references, manifest


def write_once() -> None:
    targets = (TASKS_PATH, REFERENCES_PATH, MANIFEST_PATH)
    if any(path.exists() for path in targets):
        raise FileExistsError("Frozen inputs already exist; overwrite is forbidden")
    tasks, references, manifest = expected_files()
    for path, value in zip(targets, (tasks, references, manifest), strict=True):
        path.write_bytes(value)


def check() -> None:
    expected = expected_files()
    for path, value in zip(
        (TASKS_PATH, REFERENCES_PATH, MANIFEST_PATH), expected, strict=True
    ):
        if not path.is_file() or path.read_bytes() != value:
            raise ValueError(f"Frozen input drift: {path.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    arguments = parse_args()
    try:
        if arguments.write:
            write_once()
            logging.info("Frozen 100 tasks and 20 market references")
        else:
            check()
            logging.info("Frozen inputs verified")
    except (FileExistsError, OSError, ValueError) as exc:
        logging.error("Freeze operation failed: %s", type(exc).__name__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
