#!/usr/bin/env python3
"""G3 · 受众表面治理语言与标签泄漏词典。

上一轮 10 条尝试层硬否决全部是治理/权限/内部批准语言泄漏进受众表面
（GOVERNANCE_LANGUAGE_IN_AUDIENCE_SURFACE），而旧词典只有 10 个短语。
本词典按失败证据系统化扩充，并用上一轮 211 条真实输出校准
（校准报告见 evidence/gate_calibration_report.v0.1.yaml）。

分级：
- HARD  命中即机器硬失败（进入分母，不许改稿救回首次状态）
- FLAG  命中进入人审复核队列，由内容主审裁决
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------- 治理语言
# HARD：批准/授权/权限/发布状态类——受众内容里出现即内部治理视角泄漏
GOVERNANCE_HARD_PATTERNS: list[tuple[str, str]] = [
    ("GOV_APPROVAL", r"(获准|批准|审批|签批|放行)"),
    ("GOV_AUTHORITY", r"(权限|决定权|审批权|无权|有权(?!威))"),
    ("GOV_PUBLISH_STATE", r"(上线|已发布|待发布|发布(由|流程|状态|权))"),
    ("GOV_REVIEW_PROCESS", r"(审查|复审|合规|治理|口径|免责)"),
    # 作者元写作：谈论"写/说/标"这个行为本身（"没有把它写成/说成……"）；
    # 允许 ≤6 字宾语插入（"没有把它说成"、"没有给它补上、没有写进画面"）
    ("GOV_META_WRITING", r"(没有|不|未)(被)?[^，。；]{0,10}"
                         r"(写成|说成|标成|算成|计成|归成|换算成|写进|说进|补上)"),
    ("GOV_EXTRAPOLATE", r"(外推|推广到|代表(所有|全部|整体))"),
    ("GOV_TEST_IDENTITY", r"(资格测试|测试批次|合成测试|本测试|本请求|字段|元数据|占位符)"),
]

# FLAG：可能合法但高危——进入人审
# （"由X决定/确认"仅在正文结尾位置升 HARD，由 g3_expression END_GOV_DEFER 处理）
GOVERNANCE_FLAG_PATTERNS: list[tuple[str, str]] = [
    ("GOVF_INTERNAL_STATE", r"(内部|记录在案|存档)"),
    ("GOVF_PERMISSION_ADJ", r"(允许|许可|准许|核准|审核)"),
    ("GOVF_AUTHORIZATION", r"(授权(书|范围|方)?|未授权|已授权)"),
    ("GOVF_ROLE_SCOPE", r"(职责范围|岗位范围|不越过|越权|不代表)"),
    ("GOVF_DEFER_MIDBODY", r"(仍|均|都|全部)?(由|归|交)[^，。；]{0,12}"
                           r"(决定|确认|批准|定夺|裁决|把关)"),
]

# ---------------------------------------------------------------- 标签泄漏
# 用于盲审包与受众表面：内容产品编号、内部 ID、路线标签、产品官方名称
_PRODUCT_NAMES = [
    "岗位任务VLOG", "门店时段微纪录", "单项手艺全过程", "多岗位协作纪实",
    "人物成长与职业史", "专业判断切片", "用户问题诊断室", "工艺面料版型解构",
    "适用边界与反选指南", "证据与长期验证档案", "产品诞生与设计取舍档案",
    "产品迭代与版本日志", "产品的生活与衣橱角色", "物性影像与感官短片",
    "商品到店生命周期", "真实服务复盘", "陈列换陈与空间实验",
    "城市门店生活志", "经营取舍与决策复盘", "承诺—兑现追踪",
]
LABEL_LEAK_PATTERNS: list[tuple[str, str]] = [
    ("LEAK_CP_CODE", r"\bCP(?:0[1-9]|1\d|20)\b"),
    ("LEAK_INTERNAL_ID", r"(G1V11|G3V11|P5-CUR|G3-CUR|P7-|LANE-[AB]\b)"),
    ("LEAK_SLOT_ID", r"(?:^|[^A-Za-z])(?:FACT|AUTH|SRC|CORE|SURFACE|CLAIM)-[A-Za-z0-9-]+"),
    ("LEAK_LANE_LABEL", r"(甲级|乙级|丙级|[甲乙]路径|路线标签|lane_[ab])"),
    ("LEAK_PRODUCT_NAME", "(" + "|".join(map(re.escape, _PRODUCT_NAMES)) + ")"),
    ("LEAK_ROUTE_ACTION", r"(BLOCK|REQUEST_INPUT|DEGRADE)\b"),
]

_COMPILED_HARD = [(code, re.compile(p)) for code, p in GOVERNANCE_HARD_PATTERNS]
_COMPILED_FLAG = [(code, re.compile(p)) for code, p in GOVERNANCE_FLAG_PATTERNS]
_COMPILED_LEAK = [(code, re.compile(p)) for code, p in LABEL_LEAK_PATTERNS]


def scan_governance(text: str) -> tuple[list[str], list[str]]:
    """返回 (hard_codes, flag_codes)，稳定排序、去重。"""
    hard = sorted({code for code, rx in _COMPILED_HARD if rx.search(text)})
    flag = sorted({code for code, rx in _COMPILED_FLAG if rx.search(text)})
    return hard, flag


def scan_label_leak(text: str) -> list[str]:
    return sorted({code for code, rx in _COMPILED_LEAK if rx.search(text)})


__all__ = [
    "GOVERNANCE_FLAG_PATTERNS",
    "GOVERNANCE_HARD_PATTERNS",
    "LABEL_LEAK_PATTERNS",
    "scan_governance",
    "scan_label_leak",
]
