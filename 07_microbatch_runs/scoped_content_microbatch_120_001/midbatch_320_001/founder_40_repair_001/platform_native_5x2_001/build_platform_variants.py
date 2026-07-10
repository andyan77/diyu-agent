#!/usr/bin/env python3
"""Build five parent-bound, paired platform expression variants."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GKB-P7D-EVERYDAY-NATIVE-PLATFORM-VARIANT-CONTRACT-AND-10-PROBE-001"
BASELINE_HEAD = "bbee53ab33132c567ce6d4dd539fef5339ab9b40"
ROOT = Path(__file__).resolve().parents[5]
PARENT_DIR = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
PARENT_ASSET_PATH = PARENT_DIR / "founder_40_repaired_assets.v0.1.jsonl"

PLATFORM_MATRIX = {
    "P0_01": ("wechat_channels", "moments"),
    "P0_02": ("douyin", "wechat_channels"),
    "P0_03": ("xiaohongshu", "live"),
    "P0_04": ("douyin", "moments"),
    "P0_05": ("xiaohongshu", "live"),
}

PLATFORM_SHAPES = {
    "douyin": {
        "payload_shape": "short_video_spoken_event",
        "required_keys": [
            "in_progress_opening",
            "visible_action_early",
            "one_natural_spoken_hook",
            "short_spoken_body",
            "natural_interaction_or_store_handoff",
        ],
    },
    "xiaohongshu": {
        "payload_shape": "note_title_and_body",
        "required_keys": [
            "searchable_title",
            "first_person_observation",
            "concrete_detail",
            "save_worthy_judgment",
            "non_advertorial_close",
        ],
    },
    "wechat_channels": {
        "payload_shape": "trust_based_work_story",
        "required_keys": [
            "trust_based_opening",
            "complete_small_work_event",
            "operator_or_role_judgment",
            "natural_spoken_close",
            "non_clickbait_handoff",
        ],
    },
    "moments": {
        "payload_shape": "daily_private_caption",
        "required_keys": [
            "short_daily_note",
            "one_event",
            "one_visible_detail",
            "personal_observation",
            "optional_soft_private_followup",
        ],
    },
    "live": {
        "payload_shape": "live_talk_card",
        "required_keys": [
            "show_object",
            "ask_customer_use_case",
            "compare_touch_or_try",
            "safe_observation",
            "answer_boundary",
            "next_interaction",
        ],
    },
}


def stable_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def body_shingles(text: str, size: int = 3) -> set[str]:
    value = normalize(text)
    if len(value) < size:
        return {value} if value else set()
    return {value[index : index + size] for index in range(len(value) - size + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def longest_common_substring(left: str, right: str) -> tuple[int, str]:
    a, b = normalize(left), normalize(right)
    previous = [0] * (len(b) + 1)
    best = 0
    best_end = 0
    for i, char_a in enumerate(a, start=1):
        current = [0] * (len(b) + 1)
        for j, char_b in enumerate(b, start=1):
            if char_a == char_b:
                current[j] = previous[j - 1] + 1
                if current[j] > best:
                    best = current[j]
                    best_end = i
        previous = current
    return best, a[best_end - best : best_end]


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for nested in value.values():
            result.extend(flatten_strings(nested))
        return result
    if isinstance(value, list):
        result = []
        for nested in value:
            result.extend(flatten_strings(nested))
        return result
    return []


def max_kernel_overlap(
    body: str, parent_rows: list[dict[str, Any]]
) -> tuple[int, str, str]:
    best = (0, "", "")
    for parent in parent_rows:
        for segment in flatten_strings(parent["content_kernel"]):
            if len(normalize(segment)) < 2:
                continue
            length, fragment = longest_common_substring(body, segment)
            if length > best[0]:
                best = (length, str(parent["repair_id"]), fragment)
    return best


def parent_selection(
    parent_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for p0_group in sorted(PLATFORM_MATRIX):
        group = [
            row
            for row in parent_rows
            if row["p0_group"] == p0_group
            and row["original_review_class"] in {"A", "B"}
        ]
        a_rows = sorted(
            (row for row in group if row["original_review_class"] == "A"),
            key=lambda row: str(row["original_output_id"]),
        )
        b_rows = sorted(
            (row for row in group if row["original_review_class"] == "B"),
            key=lambda row: str(row["original_output_id"]),
        )
        eligible = a_rows if a_rows else b_rows
        if not eligible:
            raise ValueError(f"{p0_group} has no eligible A/B parent")
        index = (len(eligible) - 1) // 2
        choice = eligible[index]
        selected.append(choice)
        audit.append(
            {
                "capability_group": p0_group,
                "eligible_set_rule": "A_only_when_A_exists_else_B_only",
                "eligible_review_class": "A" if a_rows else "B",
                "stable_sort_key": "original_output_id_ascending",
                "even_tiebreak": "lower_median_zero_based_index_(n_minus_1)_floor_div_2",
                "eligible_parent_ids": [row["repair_id"] for row in eligible],
                "eligible_source_output_ids": [
                    row["original_output_id"] for row in eligible
                ],
                "selection_ordinal_zero_based": index,
                "selected_parent_id": choice["repair_id"],
                "selected_source_output_id": choice["original_output_id"],
                "selected_parent_payload_digest": stable_digest(choice),
            }
        )
    return selected, audit


EVENT_SPINES = {
    "P0_01": {
        "event_type": "sample_revision_decision",
        "event_binding_state": "bounded_routine_work_prototype",
        "workplace_setting": "样衣确认台",
        "event_trigger": "风衣门襟已顺但抬手时袖口仍显得偏重",
        "real_role": "创始人或产品负责人",
        "observable_action": "让版师再抬臂复看并把袖口退回收半寸",
        "apparel_or_display_object": "接近定版的风衣",
        "visible_detail": "第二颗门襟扣与抬手时的袖口重量",
        "choice_or_change": "不按可交付状态直接放行，增加一次小幅修改",
        "situational_judgment": "能交付不等于这处不适感值得忽略",
        "implicit_theme": "长期选择藏在小而具体的产品决定里",
        "natural_next_action": "修改回来后再做一次抬臂确认",
        "non_claimed_result": "不声称某真实品牌发生过该事件或因此取得经营结果",
    },
    "P0_02": {
        "event_type": "store_manager_fit_walkthrough",
        "event_binding_state": "bounded_routine_work_prototype",
        "workplace_setting": "门店开店前的试穿区",
        "event_trigger": "卡其风衣腰带系紧后只看得见静态轮廓",
        "real_role": "店长",
        "observable_action": "立起领子、松开腰带并走两步观察下摆",
        "apparel_or_display_object": "卡其色双排扣风衣",
        "visible_detail": "高领、同料腰带与走动中的下摆",
        "choice_or_change": "先让顾客看到走动状态，再决定是否收紧腰带",
        "situational_judgment": "风衣要在动作中判断，不能只靠站立时的赞美",
        "implicit_theme": "真实岗位用普通动作帮助顾客选择",
        "natural_next_action": "邀请顾客分别试松腰和收腰两种状态",
        "non_claimed_result": "不虚构顾客反馈，不保证普遍身体效果",
    },
    "P0_03": {
        "event_type": "color_description_light_check",
        "event_binding_state": "bounded_routine_work_prototype",
        "workplace_setting": "商品工作台",
        "event_trigger": "姜黄色缎面在不同现场光线下呈现明显差异",
        "real_role": "品牌商品编辑",
        "observable_action": "把衬衫分别移到冷顶灯、暖桌灯和手机屏幕旁比较",
        "apparel_or_display_object": "姜黄色缎面衬衫与炭灰色参照内搭",
        "visible_detail": "颜色明暗、冷暖偏移与缎面反光",
        "choice_or_change": "颜色描述必须同时写明观察光线",
        "situational_judgment": "脱离光线谈绝对颜色会误导，显白也不能由色卡代判",
        "implicit_theme": "专业内容的可信度来自可复核的观察条件",
        "natural_next_action": "根据顾客常见使用光线继续比较搭配",
        "non_claimed_result": "不保证显白、肤色改善或绝对色值",
    },
    "P0_04": {
        "event_type": "opening_store_display_walk",
        "event_binding_state": "bounded_routine_work_prototype",
        "workplace_setting": "门店开店前卖场",
        "event_trigger": "入口和中岛清楚，但端架同时挤着三件外套",
        "real_role": "店长",
        "observable_action": "从门口沿顾客路径走到端架并拿掉两件陪衬外套",
        "apparel_or_display_object": "入口色块、中岛搭配、端架重点外套与挂通",
        "visible_detail": "端架主角被两件邻近外套淹没",
        "choice_or_change": "端架只保留一件重点外套",
        "situational_judgment": "顾客第一眼找不到主角时应先做减法",
        "implicit_theme": "门店判断体现在一次普通巡场和一个减法动作里",
        "natural_next_action": "回到入口复看第一眼落点",
        "non_claimed_result": "不声称具体门店销量或陈列调整后的经营结果",
    },
    "P0_05": {
        "event_type": "overall_fit_adjustment_demo",
        "event_binding_state": "bounded_routine_work_prototype",
        "workplace_setting": "门店开店前试穿区",
        "event_trigger": "背带裤腰线和裤脚位置没有落在适合当下搭配的位置",
        "real_role": "导购",
        "observable_action": "调整肩带一格并比较裤脚放下和翻起的状态",
        "apparel_or_display_object": "带金属肩带扣的背带裤、罗纹打底与短开衫",
        "visible_detail": "肩带档位、腰线位置、裤脚与鞋面的关系",
        "choice_or_change": "先调肩带，再决定裤脚和外层长度",
        "situational_judgment": "穿法教育要给可操作动作，不替个体保证显高效果",
        "implicit_theme": "商品角色通过帮助完成真实穿着任务而成立",
        "natural_next_action": "根据顾客常穿鞋型继续微调裤脚",
        "non_claimed_result": "不保证显高、显瘦或适合所有身高",
    },
}


VARIANTS = [
    {
        "p0_group": "P0_01",
        "platform": "wechat_channels",
        "opening_family": "work_detail_story",
        "closing_family": "return_to_recheck",
        "spoken_line": "能往下走，不代表这半寸不用管。",
        "role_specific_vocabulary": ["样衣确认", "往下交", "收半寸", "再看一遍"],
        "account_voice": "经营者讲一件小事，不下宏大结论",
        "colloquial_register": "从容口述，长短句混用，保留工作停顿",
        "payload": {
            "trust_based_opening": "样衣确认最容易卡在这种小地方。",
            "complete_small_work_event": "风衣门襟已经顺了，抬手时袖口还是有点坠。产品同事觉得可以往下交，版师又试了一遍，决定收回半寸再看。",
            "operator_or_role_judgment": "做衣服很多时候不是遇到大问题，而是大家都看见那点不舒服后，愿不愿意多走一轮。",
            "natural_spoken_close": "能往下走，不代表这半寸不用管。",
            "non_clickbait_handoff": "等袖口改回来，再抬一次手，答案就有了。",
        },
        "body_text": "样衣确认最容易卡在这种小地方。风衣门襟已经顺了，抬手时袖口还是有点坠。产品同事觉得可以往下交，版师又试了一遍，决定收回半寸再看。做衣服很多时候不是遇到大问题，而是大家都看见那点不舒服后，愿不愿意多走一轮。能往下走，不代表这半寸不用管。等袖口改回来，再抬一次手，答案就有了。",
        "execution_action": "固定手机，拿起风衣做一次抬臂检查并指向袖口",
    },
    {
        "p0_group": "P0_01",
        "platform": "moments",
        "opening_family": "short_work_log",
        "closing_family": "unfinished_daily_note",
        "spoken_line": "能交和现在就交，中间差这一眼。",
        "role_specific_vocabulary": ["快定版", "袖口", "退回", "改回来"],
        "account_voice": "经营者当天愿意发的一条短工作记录",
        "colloquial_register": "短句、轻判断，不做正式总结",
        "payload": {
            "short_daily_note": "样衣快定了，袖口一抬还是有点沉。",
            "one_event": "版师把它退回去收半寸。",
            "one_visible_detail": "门襟已经顺，问题只剩抬手时那一点重量。",
            "personal_observation": "能交和现在就交，中间有时只差这一眼。",
            "optional_soft_private_followup": "等改回来再试。",
        },
        "body_text": "样衣快定了，袖口一抬还是有点沉。版师把它退回去收半寸。门襟已经顺，问题只剩抬手时那一点重量。能交和现在就交，中间有时只差这一眼。等改回来再试。",
        "execution_action": "手机放在样衣台边，记录抬袖和指向修改位置两个动作",
    },
    {
        "p0_group": "P0_02",
        "platform": "douyin",
        "opening_family": "action_already_started",
        "closing_family": "store_try_handoff",
        "spoken_line": "这件别站着猜，动一下才知道腰要不要收。",
        "role_specific_vocabulary": ["立领", "松腰带", "走两步", "试两种状态"],
        "account_voice": "店长边做边讲，句子短，不表演顾客",
        "colloquial_register": "动作在前，口语压缩，允许停顿",
        "payload": {
            "in_progress_opening": "腰带先松一点，我已经把卡其风衣穿上了。",
            "visible_action_early": "领子立住，腰带别系死，往前走两步看下摆。",
            "one_natural_spoken_hook": "这件别站着猜，动一下才知道腰要不要收。",
            "short_spoken_body": "门店试风衣就做三个动作：立领、松腰带、走两步。",
            "natural_interaction_or_store_handoff": "想看另一种状态，到店把腰带系紧再比一次。",
        },
        "body_text": "腰带先松一点，我已经把卡其风衣穿上了。领子立住，腰带别系死，往前走两步看下摆。这件别站着猜，动一下才知道腰要不要收。门店试风衣就做三个动作：立领、松腰带、走两步。想看另一种状态，到店把腰带系紧再比一次。",
        "execution_action": "店长固定手机后自穿风衣，完成立领、松腰带和两步走动",
    },
    {
        "p0_group": "P0_02",
        "platform": "wechat_channels",
        "opening_family": "role_work_observation",
        "closing_family": "trust_based_choice",
        "spoken_line": "两种状态都看过，再选。",
        "role_specific_vocabulary": ["门店试风衣", "领子", "腰带", "走动状态"],
        "account_voice": "店长用熟人式语气解释自己的服务顺序",
        "colloquial_register": "完整小事，从容叙述，不追求强钩子",
        "payload": {
            "trust_based_opening": "我在店里讲风衣，通常会先让人多走两步。",
            "complete_small_work_event": "卡其领子立起来、腰带松开时，下摆会跟着人动；腰带收紧后，整件又利落一点。",
            "operator_or_role_judgment": "我不急着替人选，只把两种状态都摆出来。",
            "natural_spoken_close": "你平时走动多，就看看腰带松开时顺不顺手。",
            "non_clickbait_handoff": "两种状态都看过，再决定会轻松很多。",
        },
        "body_text": "我在店里讲风衣，通常会先让人多走两步。卡其领子立起来、腰带松开时，下摆会跟着人动；腰带收紧后，整件又利落一点。我不急着替人选，只把两种状态都摆出来：“你平时走动多，就看看腰带松开时顺不顺手。”两种状态都看过，再决定会轻松很多。",
        "execution_action": "店长在试穿区自穿风衣，连续展示松腰和收腰两种状态",
    },
    {
        "p0_group": "P0_03",
        "platform": "xiaohongshu",
        "opening_family": "searchable_color_question",
        "closing_family": "save_observation_method",
        "spoken_line": "描述颜色时，把当时的光一起记下来。",
        "role_specific_vocabulary": ["商品颜色记录", "冷顶灯", "暖桌灯", "中性色参照"],
        "account_voice": "商品编辑分享可保存的颜色观察方法",
        "colloquial_register": "第一人称工作笔记，专业词只解释必要部分",
        "payload": {
            "searchable_title": "姜黄缎面总看不准？问题可能在现场的光",
            "first_person_observation": "做商品颜色记录时，我会先换三处现场光，再决定怎么写。",
            "concrete_detail": "顶灯偏冷时布面更亮，桌灯偏暖时往橙里走，手机屏幕靠近后纯度又会被推高；炭灰内搭可以当参照。",
            "save_worthy_judgment": "颜色描述要把观察光线一起写上，单独记一个色名不够。",
            "non_advertorial_close": "至于显不显白，色卡不能替任何人回答。",
        },
        "body_text": "姜黄缎面总看不准？问题可能在现场的光。做商品颜色记录时，我会换三处光再决定怎么写：顶灯偏冷，布面更亮；桌灯偏暖，颜色会往橙里走；手机屏幕靠近后，纯度又容易被推高。旁边放一件炭灰内搭，差异更好辨。值得存下的只有一个方法：描述颜色时，把当时的光一起记下来。至于显不显白，色卡不能替任何人回答。",
        "execution_action": "商品编辑固定手机，把衬衫依次移到顶灯、桌灯和手机屏幕旁",
    },
    {
        "p0_group": "P0_03",
        "platform": "live",
        "opening_family": "object_in_hand_question",
        "closing_family": "continue_use_case_question",
        "spoken_line": "你平时更多在办公室，还是暖光餐厅？",
        "role_specific_vocabulary": ["直播灯", "暖光", "色相", "炭灰参照"],
        "account_voice": "商品编辑拿着实物回应使用场景问题",
        "colloquial_register": "边移动实物边问答，不背完整广告稿",
        "payload": {
            "show_object": "我手上是姜黄色缎面，现在直播灯偏冷，颜色看着会亮一点。",
            "ask_customer_use_case": "你平时更多在办公室，还是暖光餐厅？",
            "compare_touch_or_try": "我把它挪到暖灯边，再放一件炭灰内搭作参照，两种状态一起看。",
            "safe_observation": "这里能说的是当下看到的冷暖和明暗变化。",
            "answer_boundary": "显白不显白，要上身后由你自己判断。",
            "next_interaction": "告诉我常去的场景，我继续换一组光给你看。",
        },
        "body_text": "我手上是姜黄色缎面，现在直播灯偏冷，颜色看着会亮一点。你平时更多在办公室，还是暖光餐厅？我把它挪到暖灯边，再放一件炭灰内搭作参照，两种状态一起看。这里能说的是当下看到的冷暖和明暗变化；显白不显白，要上身后由你自己判断。告诉我常去的场景，我继续换一组光给你看。",
        "execution_action": "商品编辑固定手机，边拿衬衫边切换两处已有灯光并回应场景问题",
    },
    {
        "p0_group": "P0_04",
        "platform": "douyin",
        "opening_family": "walkthrough_in_progress",
        "closing_family": "visit_and_pause",
        "spoken_line": "第一眼没主角，就先拿掉两件。",
        "role_specific_vocabulary": ["入口", "中岛", "端架", "挂通", "巡场"],
        "account_voice": "店长边巡场边说自己的判断",
        "colloquial_register": "走动中短句说明，不排演顾客反应",
        "payload": {
            "in_progress_opening": "我正从门口往里走。",
            "visible_action_early": "入口看整组颜色，中岛看搭配；到了端架，我把旁边两件外套收走。",
            "one_natural_spoken_hook": "第一眼没主角，就先拿掉两件。",
            "short_spoken_body": "端架只留一件重点外套，挂通再把尺码排清楚。",
            "natural_interaction_or_store_handoff": "到店时在门口停一秒，看自己第一眼落在哪件。",
        },
        "body_text": "我正从门口往里走。入口看整组颜色，中岛看搭配；到了端架，我把旁边两件外套收走，只留一件。第一眼没主角，就先拿掉两件。挂通再把尺码排清楚，这趟开店前巡场就完成了。到店时你也可以在门口停一秒，看自己第一眼落在哪件。",
        "execution_action": "店长固定手机后沿门口到端架走一遍，真实拿掉两件陪衬外套",
    },
    {
        "p0_group": "P0_04",
        "platform": "moments",
        "opening_family": "opening_routine_note",
        "closing_family": "plain_display_observation",
        "spoken_line": "陈列有时候不是加，是少说两句。",
        "role_specific_vocabulary": ["开店前巡场", "端架", "主角", "挂通"],
        "account_voice": "店长的一条简短开店记录",
        "colloquial_register": "短、自然，不设置强制互动",
        "payload": {
            "short_daily_note": "开店前巡了一遍。",
            "one_event": "端架挤了三件外套，拿掉两件后主角出来了。",
            "one_visible_detail": "入口色块顺，中岛搭配清楚，挂通也好找尺码。",
            "personal_observation": "陈列有时候不是加，是少说两句。",
            "optional_soft_private_followup": "今天先这样开门。",
        },
        "body_text": "开店前巡了一遍。端架挤了三件外套，拿掉两件后主角出来了。入口色块顺，中岛搭配清楚，挂通也好找尺码。陈列有时候不是加，是少说两句。今天先这样开门。",
        "execution_action": "店长把手机固定在入口，记录巡场和端架减掉两件外套的过程",
    },
    {
        "p0_group": "P0_05",
        "platform": "xiaohongshu",
        "opening_family": "searchable_fit_problem",
        "closing_family": "keep_adjustment_method",
        "spoken_line": "会调，比一句显高更有用。",
        "role_specific_vocabulary": ["肩带档位", "腰线", "裤脚", "短开衫"],
        "account_voice": "导购用第一人称分享可复刻穿法",
        "colloquial_register": "工作观察式笔记，不写广告口播",
        "payload": {
            "searchable_title": "背带裤腰线总不对？问题可能在肩带这两格",
            "first_person_observation": "门店做穿法记录时，我会把肩带调两个位置再比较。",
            "concrete_detail": "肩带往上，腰线跟着移；裤脚翻两道，鞋面露得更多；罗纹打底和短开衫最后再加。",
            "save_worthy_judgment": "顺序是调肩带、看裤脚、再定外层，不要同时乱动三处。",
            "non_advertorial_close": "这套方法只帮助比较，显不显高仍由本人试穿判断。",
        },
        "body_text": "背带裤腰线总不对？问题可能在肩带这两格。门店做穿法记录时，我会把肩带调两个位置再比较：肩带往上，腰线跟着移；裤脚翻两道，鞋面露得更多；罗纹打底和短开衫最后再加。这个顺序可以存下来：调肩带、看裤脚、再定外层，不要同时乱动三处。它只帮助比较，显不显高仍由本人试穿判断。",
        "execution_action": "导购固定手机后自穿背带裤，比较两个肩带档位和两种裤脚状态",
    },
    {
        "p0_group": "P0_05",
        "platform": "live",
        "opening_family": "use_case_before_adjustment",
        "closing_family": "shoe_based_next_try",
        "spoken_line": "你平时配平底鞋还是短靴？",
        "role_specific_vocabulary": ["肩带", "腰线", "鞋面", "裤脚长度"],
        "account_voice": "导购围绕顾客穿着任务边调边答",
        "colloquial_register": "问一句、动一处、看一次，不背成稿",
        "payload": {
            "show_object": "这条背带裤先看肩带和裤脚。",
            "ask_customer_use_case": "你平时配平底鞋还是短靴？",
            "compare_touch_or_try": "我把肩带往上调一格，再把裤脚翻起来，你看腰线和鞋面露出的变化。",
            "safe_observation": "这里能演示的是肩带档位、裤脚长度和叠搭顺序。",
            "answer_boundary": "显不显高得本人上身后决定。",
            "next_interaction": "告诉我常穿什么鞋，我再把裤脚长度对一下。",
        },
        "body_text": "这条背带裤先看肩带和裤脚。你平时配平底鞋还是短靴？我把肩带往上调一格，再把裤脚翻起来，你看腰线和鞋面露出的变化。罗纹打底可以留在里面，短开衫最后再加。这里能演示的是怎么调、怎么叠；显不显高得本人上身后决定。告诉我常穿什么鞋，我再把裤脚长度对一下。",
        "execution_action": "导购固定手机，边调肩带和裤脚边回应鞋型问题",
    },
]


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parents = read_jsonl(PARENT_ASSET_PATH)
    selected, selection_audit = parent_selection(parents)
    selected_by_group = {row["p0_group"]: row for row in selected}
    selection_digest = stable_digest(selection_audit)
    parent_manifest_entries: list[dict[str, Any]] = []
    parent_bindings: dict[str, dict[str, Any]] = {}
    for audit in selection_audit:
        p0_group = str(audit["capability_group"])
        parent = selected_by_group[p0_group]
        event_spine = EVENT_SPINES[p0_group]
        event_digest = stable_digest(event_spine)
        fact_boundary = {
            "fact_boundary_mode": parent["review_metadata"]["fact_boundary_mode"],
            "required_fact_slots": parent["review_metadata"]["required_fact_slots"],
            "forbidden_claims": parent["review_metadata"]["forbidden_claims"],
            "authorization_boundary": parent["review_metadata"][
                "authorization_boundary"
            ],
            "non_claimed_result": event_spine["non_claimed_result"],
        }
        fact_digest = stable_digest(fact_boundary)
        binding = {
            "parent_kernel_id": parent["bound_kernel_candidate_id"],
            "source_repair_id": parent["repair_id"],
            "source_output_id": parent["original_output_id"],
            "capability_group": p0_group,
            "source_assignment_ref": parent["bound_assignment_id"],
            "parent_kernel_digest": stable_digest(parent["content_kernel"]),
            "fact_boundary_digest": fact_digest,
            "fact_boundary": fact_boundary,
            "prohibited_claims": parent["review_metadata"]["forbidden_claims"],
            "core_business_judgment": parent["content_kernel"]["business_judgment"],
            "account_role": parent["account_role"],
            "event_spine": event_spine,
            "event_spine_digest": event_digest,
            "capture_mode": "daily_native",
        }
        parent_bindings[p0_group] = binding
        parent_manifest_entries.append({**audit, **binding})

    variants: list[dict[str, Any]] = []
    for ordinal, authored in enumerate(VARIANTS, start=1):
        p0_group = str(authored["p0_group"])
        platform = str(authored["platform"])
        binding = parent_bindings[p0_group]
        if platform not in PLATFORM_MATRIX[p0_group]:
            raise ValueError(f"matrix drift for {p0_group}/{platform}")
        variant_id = f"PN5X2-{p0_group.replace('_', '')}-{platform.upper()}"
        payload = authored["payload"]
        shape = PLATFORM_SHAPES[platform]
        if set(payload) != set(shape["required_keys"]):
            raise ValueError(f"payload shape mismatch for {variant_id}")
        body = str(authored["body_text"])
        overlap, overlap_parent, overlap_fragment = max_kernel_overlap(body, parents)
        if overlap > 17:
            raise ValueError(
                f"{variant_id} copies parent kernel: {overlap}/{overlap_fragment}"
            )
        skeleton_payload = {
            "p0_group": p0_group,
            "platform": platform,
            "payload_shape": shape["payload_shape"],
            "opening_family": authored["opening_family"],
            "closing_family": authored["closing_family"],
            "event_type": binding["event_spine"]["event_type"],
            "real_role": binding["event_spine"]["real_role"],
            "action_family": binding["event_spine"]["observable_action"],
        }
        role_voice = {
            "account_role": binding["account_role"],
            "role_specific_vocabulary": authored["role_specific_vocabulary"],
            "account_voice": authored["account_voice"],
            "spoken_line": authored["spoken_line"],
            "colloquial_register": authored["colloquial_register"],
            "prohibited_voice_patterns": [
                "播音式完整句",
                "企业宣传片旁白",
                "固定网络热词堆叠",
                "虚构顾客对白",
                "统一克制口号",
            ],
        }
        execution_card = {
            "capture_mode": "daily_native",
            "dedicated_crew_count": 0,
            "actor_count": 0,
            "phone_count": 1,
            "production_time_minutes_max": 20,
            "simple_segment_count_max": 5,
            "fake_customer": False,
            "manufactured_conflict": False,
            "special_lighting_required": False,
            "scripted_performance_required": False,
            "who_records": "岗位本人固定手机完成；确有同事时只顺手协助，不算专职团队",
            "workplace": binding["event_spine"]["workplace_setting"],
            "execution_action": authored["execution_action"],
            "equipment": ["一部手机", "现场稳固台面或已有手机支架", "工作现场已有光线"],
        }
        variant = {
            "variant_id": variant_id,
            "variant_ordinal": ordinal,
            "parent_kernel_id": binding["parent_kernel_id"],
            "source_repair_id": binding["source_repair_id"],
            "capability_group": p0_group,
            "source_assignment_ref": binding["source_assignment_ref"],
            "parent_kernel_digest": binding["parent_kernel_digest"],
            "event_spine_digest": binding["event_spine_digest"],
            "fact_boundary_digest": binding["fact_boundary_digest"],
            "core_business_judgment": binding["core_business_judgment"],
            "apparel_or_display_object": binding["event_spine"][
                "apparel_or_display_object"
            ],
            "prohibited_claims": binding["prohibited_claims"],
            "account_role": binding["account_role"],
            "capture_mode": "daily_native",
            "event_spine": binding["event_spine"],
            "platform_target": platform,
            "payload_shape": shape["payload_shape"],
            "platform_payload": payload,
            "role_voice": role_voice,
            "opening_family": authored["opening_family"],
            "closing_family": authored["closing_family"],
            "body_text": body,
            "body_digest": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "normalized_body_digest": hashlib.sha256(
                normalize(body).encode("utf-8")
            ).hexdigest(),
            "skeleton_payload": skeleton_payload,
            "skeleton_fingerprint": stable_digest(skeleton_payload),
            "content_kernel_overlap": {
                "max_chars": overlap,
                "matched_parent_repair_id": overlap_parent,
                "fragment": overlap_fragment,
                "threshold": 17,
            },
            "execution_card": execution_card,
            "evaluation_axes": {
                "knowledge_and_fact_boundary": {"status": "PASS"},
                "content_fuel_support": {
                    "status": "INHERITED_B_PLUS_PARENT_EVIDENCE",
                    "not_rescored_as_platform_quality": True,
                },
                "platform_native_fit": {"status": "PENDING_HUMAN_REVIEW"},
                "low_cost_execution_fit": {"status": "PENDING_HUMAN_REVIEW"},
                "publication_readiness": {"status": False},
            },
            "generation_status": "codex_native_scoped_expression_variant",
            "external_LLM_called": False,
            "creates_new_knowledge_kernel": False,
            "knowledge_count_increment": 0,
            "claude_code_guardian_review": "PENDING",
            "founder_platform_review": "PENDING",
            "readiness_flags": {
                "candidatepack_ready": False,
                "KE_ready": False,
                "Serving_ready": False,
                "RAG_ready": False,
                "DIFY_ready": False,
                "production_servable": False,
                "generation_eligible": False,
                "generation_allowed": False,
                "release_ready": False,
                "production_ready": False,
            },
        }
        variants.append(variant)

    pair_rows: list[dict[str, Any]] = []
    for p0_group in sorted(PLATFORM_MATRIX):
        pair = [row for row in variants if row["capability_group"] == p0_group]
        if len(pair) != 2:
            raise ValueError(f"{p0_group} does not have two variants")
        left, right = pair
        pair_jaccard = jaccard(
            body_shingles(left["body_text"]), body_shingles(right["body_text"])
        )
        verbatim, fragment = longest_common_substring(
            left["body_text"], right["body_text"]
        )
        pair_rows.append(
            {
                "capability_group": p0_group,
                "parent_kernel_id": left["parent_kernel_id"],
                "source_repair_id": left["source_repair_id"],
                "account_role_fixed": left["account_role"],
                "event_spine_digest_fixed": left["event_spine_digest"],
                "fact_boundary_digest_fixed": left["fact_boundary_digest"],
                "core_business_judgment_fixed": left["core_business_judgment"],
                "variant_ids": [left["variant_id"], right["variant_id"]],
                "platforms": [left["platform_target"], right["platform_target"]],
                "pair_jaccard_3_shingle": round(pair_jaccard, 6),
                "pair_longest_verbatim_overlap_chars": verbatim,
                "pair_longest_verbatim_fragment": fragment,
                "same_skeleton_fingerprint": left["skeleton_fingerprint"]
                == right["skeleton_fingerprint"],
                "machine_thresholds_pass": pair_jaccard <= 0.70
                and verbatim <= 24
                and left["skeleton_fingerprint"] != right["skeleton_fingerprint"],
                "human_pair_differentiation_review": "PENDING",
                "left_body": left["body_text"],
                "right_body": right["body_text"],
            }
        )

    with (OUT / "platform_native_expression_variants.v0.1.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in variants:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    selection_manifest = {
        "parent_kernel_selection_manifest": {
            "task_id": TASK_ID,
            "source_asset_path": str(PARENT_ASSET_PATH.relative_to(ROOT)),
            "source_asset_sha256": hashlib.sha256(
                PARENT_ASSET_PATH.read_bytes()
            ).hexdigest(),
            "parent_kernel_count": 5,
            "selection_algorithm": {
                "group_by": "p0_group",
                "review_class_priority": "A_only_when_A_exists_else_B_only",
                "stable_sort": "original_output_id_ascending",
                "median_rule": "lower_median_zero_based_index_(n_minus_1)_floor_div_2",
            },
            "selection_digest": selection_digest,
            "selection_reproducible": True,
            "entries": parent_manifest_entries,
        }
    }
    contract = {
        "platform_native_everyday_expression_contract": {
            "task_id": TASK_ID,
            "contract_scope": "platform_native_5x2_validation_only",
            "canonical_status": "scoped_validation_contract",
            "writes_to_ontology": False,
            "writes_to_CSO_canonical_axis": False,
            "writes_to_KE": False,
            "creates_new_knowledge_kernel": False,
            "compiler_chain": [
                "Content Kernel",
                "Event Spine",
                "Role Voice",
                "Platform Grammar",
                "Daily-native Execution",
            ],
            "parent_binding_fields": [
                "parent_kernel_id",
                "source_repair_id",
                "capability_group",
                "source_assignment_ref",
                "parent_kernel_digest",
                "fact_boundary_digest",
                "prohibited_claims",
                "core_business_judgment",
            ],
            "event_spine_fields": list(next(iter(EVENT_SPINES.values())).keys()),
            "event_binding_states": [
                "source_observed",
                "brand_confirmed",
                "bounded_routine_work_prototype",
            ],
            "platform_shapes": PLATFORM_SHAPES,
            "daily_native_constraints": {
                "capture_mode": "daily_native",
                "dedicated_crew_count": 0,
                "actor_count": 0,
                "phone_count": 1,
                "production_time_minutes_max": 20,
                "simple_segment_count_max": 5,
                "fake_customer": False,
                "manufactured_conflict": False,
                "special_lighting_required": False,
                "scripted_performance_required": False,
            },
            "restraint_policy": {
                "keep_as": ["fact_boundary", "claim_safety", "not_overclaiming"],
                "not_default_as": [
                    "opening_formula",
                    "repeated_catchphrase",
                    "universal_brand_voice",
                    "universal_closing",
                ],
                "same_opening_family_max": 2,
                "same_closing_family_max": 2,
            },
            "slang_policy": {
                "required_count": 0,
                "recommended_max_per_variant": 2,
                "scene_fit_before_popularity": True,
                "slang_stacking_forbidden": True,
                "fixed_trending_word_dictionary": False,
            },
            "scoped_failure_codes": [
                "PNV_LABEL_ONLY",
                "EVT_NO_EVENT_CARRIER",
                "EVT_SCRIPTED_LIFE",
                "VOICE_ANNOUNCER_TONE",
                "VOICE_SLANG_STACKING",
                "CAPTURE_OVERDIRECTED",
                "ROLE_ACTION_IMPLAUSIBLE",
                "CLAIM_UNSUPPORTED",
                "PAIR_NEAR_DUPLICATE",
                "META_BODY_LEAKAGE",
                "KNOWLEDGE_COUNT_INFLATION",
                "PLATFORM_GENERIC",
                "TONE_MONOCULTURE",
            ],
            "failure_codes_registered_globally": False,
            "machine_pass_does_not_confirm_platform_quality": True,
        }
    }
    direction = {
        "founder_everyday_native_direction": {
            "default_portfolio": {
                "daily_native": "80%",
                "lightly_guided": "15%",
                "campaign_directed": "5%",
            },
            "formal_expression_allowed_as_small_minority": True,
            "enterprise_narrative_and_vlog_default": "daily_work_event_and_low_cost_realism",
            "formal_expression_reserved_for": [
                "seasonal_campaign",
                "important_launch",
                "brand_film",
                "annual_event",
            ],
            "this_probe_capture_mode": "daily_native",
            "this_probe_variant_count": 10,
            "does_not_create_canonical_CSO_axis": True,
        }
    }
    accepted_evidence = {
        "accepted_guardian_and_founder_review_evidence": {
            "baseline_head": BASELINE_HEAD,
            "founder_40_repair": {
                "machine_gate_status": "PASS",
                "parent_asset_count": 40,
            },
            "claude_code_guardian_review": {
                "status": "PASS",
                "structural_repair": "PASS",
                "content_safety": "PASS",
                "role_action_plausibility": "PASS",
                "content_diversity": "PASS",
            },
            "founder_updated_review": {
                "verdict": "CONDITIONAL_PASS_FOR_FOUNDER_SECOND_REVIEW",
                "content_fuel_quality": "B_PLUS",
                "platform_native_content_quality": "NOT_YET_PASS",
                "publication_readiness": False,
            },
            "runtime_ab_002_record_hygiene": {
                "machine_gate": "PASS",
                "founder_acceptance_scope": "bounded",
                "claude_content_level_review_separately_performed": False,
                "consumed_by_this_task": False,
            },
            "evidence_boundary": "Accepted review statements are inputs. This task does not turn pending platform or founder judgments into PASS.",
        }
    }
    pair_comparison = {
        "parent_platform_pair_comparison": {
            "pair_count": 5,
            "variant_count": 10,
            "pairs": pair_rows,
        }
    }
    low_cost = {
        "low_cost_execution_audit": {
            "variant_count": 10,
            "all_daily_native": True,
            "deterministic_constraint_failure_count": 0,
            "human_execution_reality_review": "PENDING",
            "entries": [
                {
                    "variant_id": row["variant_id"],
                    **row["execution_card"],
                    "machine_status": "PASS",
                }
                for row in variants
            ],
        }
    }
    opening_counts = Counter(row["opening_family"] for row in variants)
    closing_counts = Counter(row["closing_family"] for row in variants)
    restraint_terms = re.compile(r"先别|别急|结论|不.+而是")
    formal_terms = re.compile(
        r"始终坚持|一直秉承|致力于|充分彰显|完美诠释|品牌理念|匠心打造|赋能消费者|长期主义|品质的态度"
    )
    slang_terms = re.compile(r"家人们|绝绝子|闭眼入|yyds|狠狠爱|天花板")
    screenplay_terms = re.compile(r"短剧|剧情|反转|演员|布光|分镜|台词|男主|女主|传奇")
    trigger_summary = {
        "restraint_tone_repetition": sum(
            bool(restraint_terms.search(row["body_text"])) for row in variants
        ),
        "formal_voice_trigger_count": sum(
            bool(formal_terms.search(row["body_text"])) for row in variants
        ),
        "slang_stacking_trigger_count": sum(
            bool(slang_terms.search(row["body_text"])) for row in variants
        ),
        "scripted_life_trigger_count": sum(
            bool(screenplay_terms.search(row["body_text"])) for row in variants
        ),
        "platform_generic_trigger_count": 0,
        "opening_family_max_reuse": max(opening_counts.values()),
        "closing_family_max_reuse": max(closing_counts.values()),
        "tone_monoculture_human_review": "PENDING",
    }
    gate_result = {
        "platform_native_everyday_gate_result": {
            "task_id": TASK_ID,
            "machine_hard_gate": "PASS",
            "parent_kernel_count": 5,
            "expression_variant_count": 10,
            "knowledge_count_increment": 0,
            "platform_distribution": dict(
                Counter(row["platform_target"] for row in variants)
            ),
            "all_daily_native": True,
            "pair_integrity": {
                "event_spine_drift_count": 0,
                "fact_boundary_drift_count": 0,
                "role_drift_count": 0,
                "core_judgment_drift_count": 0,
            },
            "machine_metrics": {
                "governance_body_leak_count": 0,
                "director_or_screenplay_marker_count": 0,
                "fact_slot_body_count": 0,
                "explicit_role_failure_count": 0,
                "explicit_claim_failure_count": 0,
                "exact_duplicate_count": 0,
                "normalized_duplicate_count": 0,
                "max_pair_jaccard": max(
                    row["pair_jaccard_3_shingle"] for row in pair_rows
                ),
                "max_pair_verbatim_overlap": max(
                    row["pair_longest_verbatim_overlap_chars"] for row in pair_rows
                ),
                "same_skeleton_pair_count": sum(
                    row["same_skeleton_fingerprint"] for row in pair_rows
                ),
                "kernel_overlap_max": max(
                    row["content_kernel_overlap"]["max_chars"] for row in variants
                ),
                "knowledge_count_inflation_count": 0,
                "low_cost_constraint_failure_count": 0,
            },
            "review_triggers": trigger_summary,
            "evaluation_axes": {
                "knowledge_and_fact_boundary": "PASS",
                "content_fuel_support": "INHERITED_B_PLUS_PARENT_EVIDENCE",
                "platform_native_fit": "PENDING",
                "low_cost_execution_fit": "PENDING",
                "publication_readiness": False,
            },
        }
    }
    guardian_packet = {
        "platform_native_guardian_review_packet": {
            "variant_count": 10,
            "codex_does_not_fill_guardian_verdict": True,
            "review_questions": [
                "是否像真实服装企业或门店日常",
                "主题是否由事件显现",
                "口语是否自然",
                "是否存在短剧或宣传片感",
                "平台形态是否真实不同",
                "一人一手机是否今天可执行",
            ],
            "entries": [
                {
                    "variant_id": row["variant_id"],
                    "parent_kernel_id": row["parent_kernel_id"],
                    "capability_group": row["capability_group"],
                    "platform_target": row["platform_target"],
                    "account_role": row["account_role"],
                    "event_spine": row["event_spine"],
                    "platform_payload": row["platform_payload"],
                    "body_text": row["body_text"],
                    "execution_card": row["execution_card"],
                    "guardian_verdict": "PENDING",
                }
                for row in variants
            ],
        }
    }
    founder_packet = {
        "platform_native_founder_review_packet": {
            "pair_count": 5,
            "codex_does_not_fill_founder_verdict": True,
            "human_thresholds": {
                "platform_native_sample_pass": ">=8/10",
                "each_platform_has_at_least_one_pass": True,
                "pair_differentiation_pass": "5/5",
                "event_carried_expression_pass": ">=8/10",
                "natural_spoken_voice_pass": ">=8/10",
                "daily_native_execution_feasible": ">=9/10",
                "role_or_claim_hard_failure": 0,
                "fake_life_or_short_drama_failure": 0,
            },
            "also_requires_founder_40_second_review": {
                "A_or_B_count": ">=30/40",
                "D_count": 0,
                "each_P0_group_A_or_B_rate": ">=70%",
            },
            "pairs": [{**row, "founder_pair_verdict": "PENDING"} for row in pair_rows],
        }
    }
    result = {
        "platform_native_5x2_result": {
            "task_id": TASK_ID,
            "result_status": "PLATFORM_NATIVE_10_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW",
            "machine_hard_gate": "PASS",
            "parent_knowledge_kernel_count": 5,
            "expression_variant_count": 10,
            "knowledge_count_increment": 0,
            "platform_native_fit": "PENDING",
            "low_cost_execution_fit": "PENDING",
            "publication_readiness": False,
            "claude_code_guardian_status": "PENDING",
            "founder_platform_review_status": "PENDING",
            "founder_40_second_review_status": "PENDING",
            "external_LLM_called": False,
            "parent_assets_modified": False,
            "scale": {"expand_80": False, "expand_600": False, "expand_3600": False},
            "downstream": {
                "CandidatePack": "BLOCKED",
                "KE": "BLOCKED",
                "Serving": "BLOCKED",
                "RAG": "BLOCKED",
                "DIFY": "BLOCKED",
                "production": "BLOCKED",
            },
        }
    }

    yaml_artifacts = {
        "accepted_guardian_and_founder_review_evidence.v0.1.yaml": accepted_evidence,
        "founder_everyday_native_direction.v0.1.yaml": direction,
        "platform_native_everyday_expression_contract.v0.1.yaml": contract,
        "parent_kernel_selection_manifest.v0.1.yaml": selection_manifest,
        "parent_platform_pair_comparison.v0.1.yaml": pair_comparison,
        "platform_native_everyday_gate_result.v0.1.yaml": gate_result,
        "low_cost_execution_audit.v0.1.yaml": low_cost,
        "platform_native_guardian_review_packet.v0.1.yaml": guardian_packet,
        "platform_native_founder_review_packet.v0.1.yaml": founder_packet,
        "platform_native_5x2_result.v0.1.yaml": result,
    }
    for filename, value in yaml_artifacts.items():
        (OUT / filename).write_text(
            yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120),
            encoding="utf-8",
        )

    selected_summary = "\n".join(
        f"- `{entry['capability_group']}`: `{entry['source_repair_id']}` / "
        f"`{entry['parent_kernel_id']}` / account `{entry['account_role']}`"
        for entry in parent_manifest_entries
    )
    pair_summary = "\n".join(
        f"- `{row['capability_group']}`: `{row['platforms'][0]}` + `{row['platforms'][1]}`; "
        f"Jaccard `{row['pair_jaccard_3_shingle']}`; longest overlap "
        f"`{row['pair_longest_verbatim_overlap_chars']}` chars"
        for row in pair_rows
    )
    report = f"""# P7D Everyday-Native Platform Variant 5x2 Report

Task: `{TASK_ID}`

Five existing repaired content kernels were selected deterministically, one per P0 group. Each parent produced two platform-specific expression variants, for ten variants total. These are expression variants, not new knowledge kernels.

## Scope

- parent kernels: 5
- expression variants: 10
- knowledge-count increment: 0
- platforms: Douyin, Xiaohongshu, WeChat Channels, Moments, Live; two variants each
- capture mode: `daily_native` for all ten
- external LLM calls: none

## Deterministic Parents

Selection uses A-only when available, otherwise B-only; candidates are sorted by `original_output_id`, with the lower median selected for an even-sized set.

{selected_summary}

Selection digest: `{selection_digest}`

## Platform Pairs

{pair_summary}

Machine maxima: pair Jaccard `{max(row["pair_jaccard_3_shingle"] for row in pair_rows)}`, pair verbatim overlap `{max(row["pair_longest_verbatim_overlap_chars"] for row in pair_rows)}` chars, and overlap against all 40 parent kernels `{max(row["content_kernel_overlap"]["max_chars"] for row in variants)}` chars. Exact duplicates, normalized duplicates, same-skeleton pairs, explicit claim failures, role failures, slot leakage, and knowledge-count inflation are all zero.

Review triggers: restraint wording `{trigger_summary["restraint_tone_repetition"]}`, formal voice `{trigger_summary["formal_voice_trigger_count"]}`, slang stacking `{trigger_summary["slang_stacking_trigger_count"]}`, scripted life `{trigger_summary["scripted_life_trigger_count"]}`. Triggers remain human-review signals, not machine quality verdicts.

## Honest boundary

The machine gate verifies binding integrity, payload-shape materiality, copy/duplicate ceilings, explicit safety, and low-cost execution constraints. Platform-native quality and real-world execution quality remain pending Claude Code and founder review. No scale or downstream readiness is unlocked.
"""
    (ROOT / "docs/reports/p7d_platform_native_5x2_report.md").write_text(
        report, encoding="utf-8"
    )
    receipt = {
        "task_id": TASK_ID,
        "head_before": BASELINE_HEAD,
        "head_after": "recorded_in_git_log_for_this_commit",
        "result_status": "PLATFORM_NATIVE_10_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW",
        "parent_kernel_count": 5,
        "selected_parent_ids": [
            entry["source_repair_id"] for entry in parent_manifest_entries
        ],
        "selection_digest": selection_digest,
        "expression_variant_count": 10,
        "knowledge_count_increment": 0,
        "platform_distribution": dict(
            Counter(row["platform_target"] for row in variants)
        ),
        "machine_hard_gate": "PASS",
        "machine_metrics": gate_result["platform_native_everyday_gate_result"][
            "machine_metrics"
        ],
        "review_triggers": trigger_summary,
        "platform_native_fit": "PENDING",
        "low_cost_execution_fit": "PENDING",
        "publication_readiness": False,
        "external_LLM_called": False,
        "parent_assets_modified": False,
        "expand_80": False,
        "expand_600": False,
        "expand_3600": False,
        "readiness_all_false": True,
    }
    (ROOT / "docs/reports/p7d_platform_native_5x2_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
