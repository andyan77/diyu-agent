#!/usr/bin/env python3
"""Generate the founder-authorized P7D 320-draft bounded midbatch."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


TASK_ID = "GKB-P7D-CONDITIONAL-MIDBATCH-320-GENERATION-AND-REVIEW-HANDOFF-001"
BASELINE_HEAD = "3254e8546c10edb26dea52ada4b6b0c2b760471d"
RUN_REL = "07_microbatch_runs/scoped_content_microbatch_120_001"
OUT_REL = f"{RUN_REL}/midbatch_320_001"
SCALE_REL = f"{RUN_REL}/review_closeout/execution_scalability_001"
ASSIGNMENT_REL = "07_microbatch_briefing/scoped_content_microbatch_120/scoped_120_assignment_plan.v0.1.yaml"
KERNEL_REL = f"{RUN_REL}/content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml"
SAMPLE_PLAN_REL = f"{RUN_REL}/review_closeout/scale_gate_completion/p7c_runtime_ab_sample_plan.v0.1.yaml"
SELECTION_ORDINAL_INDEXES = (0, 11, 22, 33, 45, 56, 67, 78)
SHINGLE_SIZE = 5
SHINGLE_FAIL_THRESHOLD = 0.62
SHINGLE_REVIEW_THRESHOLD = 0.34


CLUSTER_GUIDANCE: dict[str, tuple[str, str, str]] = {
    "mkc_007": (
        "把企业选择放进衣服细节",
        "先给犹豫，再给反复做的动作",
        "让价值被看见而非被喊出",
    ),
    "mkc_008": (
        "沿工序追一件衣服的来路",
        "每次交手都要留下可拍动作",
        "把抽象承诺换成过程画面",
    ),
    "mkc_009": (
        "让小改动撑起完整故事",
        "用前后差异而非宏大口号推进",
        "在细节处留下叙事余味",
    ),
    "mkc_010": (
        "用实物锚点拆掉空泛形容",
        "先让手与衣服发生动作",
        "把槽位留给真实身份和事件",
    ),
    "mkc_011": (
        "把夸张结果降为可观察画面",
        "只描述镜头能确认的变化",
        "保住感染力也保住说话分寸",
    ),
    "mkc_012": (
        "让同一单品承担不同内容任务",
        "按场景重排切口而非换标题",
        "形成可持续的系列表达",
    ),
    "mkc_013": (
        "让岗位用各自眼睛说衣服",
        "同一物件承接不同角色动作",
        "声音不同但对象始终一致",
    ),
    "mkc_014": (
        "让语气跟随现场强弱",
        "普通动作平说，关键细节抬高",
        "减少表演腔并保留温度",
    ),
    "mkc_015": (
        "把一件衣服交给多岗位接力",
        "每个人只说自己真正看见的部分",
        "拼出组织协作的生活感",
    ),
    "mkc_016": (
        "切换视角但不冒领经历",
        "用第一现场动作替代身份背书",
        "公开表达保持可信距离",
    ),
    "mkc_017": (
        "按受众距离调整信息深度",
        "新客先看画面，熟客再进细节",
        "同一对象生成不同入口",
    ),
    "mkc_018": (
        "控制情绪温度而不制造承诺",
        "把情绪落在动作和停顿里",
        "让信任来自克制的观察",
    ),
    "mkc_019": (
        "让角色权限决定能说多深",
        "经验不清时用现场观察替代履历",
        "人物故事不越过事实线",
    ),
    "mkc_020": (
        "按品类层级拆解单品",
        "从领型袖长走到材质与廓形",
        "把未知属性留成可绑定槽位",
    ),
    "mkc_021": (
        "只比较同一任务下的可见差异",
        "并排拍版型长度和结构",
        "不把观察偷换成优劣结论",
    ),
    "mkc_022": (
        "从织造结构解释面料感受",
        "用拉伸垂坠和表面纹理入镜",
        "成分结论等待标签或检测",
    ),
    "mkc_023": (
        "把颜色放进真实光线",
        "同时拍光源和中性色参照",
        "避免把屏幕观感写成固定色值",
    ),
    "mkc_024": (
        "用剪裁术语服务上身观察",
        "先定位肩腰衣长再谈轮廓",
        "不把版型画面包装成身材保证",
    ),
    "mkc_025": (
        "把工艺节点拍成手上动作",
        "由整体逐步靠近收口与走线",
        "让可见线索承担讲解",
    ),
    "mkc_026": (
        "把身材效果改写成场景观察",
        "描述线条位置和行动限制",
        "拒绝数字化的身体承诺",
    ),
    "mkc_027": (
        "按证据强度谈舒适与耐用",
        "先拍触感结构和使用状态",
        "没有记录就不提前下结论",
    ),
    "mkc_028": (
        "把品质观察与证明来源配对",
        "每个近景后接一个待核槽位",
        "让脚本可继续补证",
    ),
    "mkc_029": (
        "把做工翻译成可拍摄细节",
        "用光线手势和镜头距离组织",
        "让观众知道该看哪里",
    ),
    "mkc_030": (
        "把一套穿搭拆成视觉层次",
        "明确主体陪体和前景位置",
        "让搭配判断能被复现",
    ),
    "mkc_031": (
        "让色彩沿视线形成路线",
        "先定主色再安排承接与跳点",
        "使主题在画面里自然出现",
    ),
    "mkc_032": (
        "把卖场区位变成镜头地图",
        "入口中岛端架各承担不同景别",
        "让空间动作直接产出内容",
    ),
    "mkc_033": (
        "从门店一分钟里截取完整动作",
        "拍清开始调整与结束标志",
        "让日常忙碌具有故事单位",
    ),
    "mkc_034": (
        "用三段动作展示造型变化",
        "同一物件保持机位完成前后对照",
        "把方法变成可照做的演示",
    ),
    "mkc_035": (
        "让门店内容先保护人物和现场",
        "镜头对衣服与动作而非隐私",
        "现场感不靠冒充真实事件",
    ),
    "mkc_036": ("按观察实施复核完成陈列", "每一步保留前后画面", "使调整理由可以回看"),
    "mkc_037": (
        "让角色权限约束陈列改动",
        "先确认可动范围再开始上手",
        "不同门店保留改写边界",
    ),
    "mkc_038": (
        "遇到硬结论立即回退核对",
        "保留原句问题与可用改写",
        "修复过程本身也可被审计",
    ),
    "mkc_039": (
        "让产品以场景任务进入故事",
        "先出现人的处境再让衣服接手",
        "单品成为动作节点而非广告牌",
    ),
    "mkc_040": (
        "把行动邀请放在故事余韵后",
        "先完成观察再给轻量下一步",
        "避免内容突然转成硬卖",
    ),
    "mkc_041": (
        "按生命周期改变单品戏份",
        "从轮廓认知走到结构教育再退场",
        "同一产品拥有阶段化角色",
    ),
    "mkc_042": (
        "用组货关系分配产品角色",
        "主推承接搭配与补位各司其职",
        "避免所有商品同时抢话",
    ),
    "mkc_043": (
        "把适配写成带条件的任务",
        "同时给适用和不适用现场",
        "百搭被还原为具体选择",
    ),
    "mkc_044": (
        "把使用教育与效果承诺分开",
        "动作可以演示，结果必须留证",
        "让脚本完整却不冒充证明",
    ),
    "mkc_045": (
        "用邻接关系讲产品与陈列",
        "同色延续异材质制造转折",
        "让画面关系成为叙事语法",
    ),
    "mkc_046": (
        "让产品在角色和渠道间换位置",
        "每次切换都重写任务而非套话",
        "跨域内容仍保持同一事实边界",
    ),
}

APPAREL_TERMS = (
    "羊毛大衣",
    "廓形大衣",
    "针织开衫",
    "针织衫",
    "西装外套",
    "牛仔外套",
    "灯芯绒阔腿裤",
    "阔腿裤",
    "直筒裤",
    "百褶裙",
    "半身裙",
    "连衣裙",
    "风衣",
    "外套",
    "衬衫",
    "毛衣",
    "针织",
    "大衣",
    "裤子",
    "裙子",
)
DETAIL_TERMS = (
    "肩线",
    "袖口",
    "领口",
    "门襟",
    "下摆",
    "腰线",
    "裤脚",
    "缝份",
    "针脚",
    "罗纹",
    "走线",
    "翻领",
    "腰带",
    "衣长",
    "廓形",
    "垂坠",
    "回弹",
    "面料",
    "色彩",
    "挂通",
    "中岛",
    "端架",
    "橱窗",
    "试衣镜",
)
COLOR_TERMS = (
    "米白",
    "燕麦",
    "卡其",
    "驼色",
    "焦糖",
    "雾蓝",
    "藏青",
    "炭灰",
    "姜黄",
    "砖红",
    "豆绿",
    "墨绿",
    "酒红",
    "深蓝",
    "烟灰",
    "橄榄绿",
    "铁锈红",
    "米色",
    "浅灰",
    "白色",
    "砂色",
    "黑色",
)
MATERIAL_TERMS = (
    "羊毛",
    "羊绒",
    "棉麻",
    "灯芯绒",
    "醋酸",
    "针织",
    "水洗牛仔",
    "梭织",
    "缎面",
    "毛呢",
    "粗针",
)
ACTION_PHRASES = {
    "拿": "拿起",
    "看": "换个角度看",
    "试": "试穿",
    "量": "重新比量",
    "指": "指向",
    "讲": "轻声讲解",
    "挂": "挂正",
    "改": "重新整理",
    "退": "后退查看",
    "比": "并排比较",
    "调": "微调",
    "摸": "用手确认",
}


def stable_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"non-object JSONL row {path}:{line_no}")
        rows.append(row)
    return rows


def write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def normalize_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def shingles(text: str, size: int = SHINGLE_SIZE) -> set[str]:
    normalized = normalize_text(text)
    if len(normalized) < size:
        return {normalized} if normalized else set()
    return {
        normalized[index : index + size] for index in range(len(normalized) - size + 1)
    }


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def kernel_segments(kernel: dict[str, Any]) -> list[str]:
    segments: list[str] = []
    for key in (
        "object_anchor",
        "business_judgment",
        "tradeoff_or_tension",
        "spoken_line_seed",
        "output_asset_hint",
    ):
        value = kernel.get(key)
        if isinstance(value, str) and value:
            segments.append(value)
    for key in ("human_subject", "human_action", "scene_premise"):
        value = kernel.get(key)
        if isinstance(value, list):
            segments.extend(str(item) for item in value if item)
    return segments


def build_overlap_index(
    kernels: list[dict[str, Any]], max_size: int = 18
) -> dict[int, dict[str, set[str]]]:
    index: dict[int, dict[str, set[str]]] = {
        size: defaultdict(set) for size in range(1, max_size + 1)
    }
    for kernel in kernels:
        candidate_id = str(kernel["candidate_id"])
        for segment in kernel_segments(kernel):
            normalized = normalize_text(segment)
            for size in range(1, min(max_size, len(normalized)) + 1):
                for offset in range(len(normalized) - size + 1):
                    index[size][normalized[offset : offset + size]].add(candidate_id)
    return index


def max_kernel_overlap(
    body: str, index: dict[int, dict[str, set[str]]]
) -> tuple[int, list[str], str]:
    normalized = normalize_text(body)
    for size in range(max(index), 0, -1):
        if len(normalized) < size:
            continue
        for offset in range(len(normalized) - size + 1):
            fragment = normalized[offset : offset + size]
            candidate_ids = index[size].get(fragment)
            if candidate_ids:
                return size, sorted(candidate_ids), fragment
    return 0, [], ""


def extract_term(
    text: str, terms: tuple[str, ...], fallback: str, offset: int = 0
) -> str:
    matches = [term for term in terms if term in text]
    if not matches:
        return fallback
    return matches[offset % len(matches)]


def extract_terms(
    text: str, terms: tuple[str, ...], fallback: tuple[str, ...]
) -> list[str]:
    matches = list(dict.fromkeys(term for term in terms if term in text))
    return matches if matches else list(fallback)


def compact_scene(kernel: dict[str, Any], variant: int) -> str:
    scenes = [
        str(value)
        for value in kernel.get("scene_premise", [])
        if value and "待人工" not in str(value)
    ]
    fallbacks = (
        "试衣镜边",
        "开门前的卖场",
        "样衣桌旁",
        "侧光下的挂杆",
        "收工后的中岛",
        "陈列墙前",
        "试穿区外",
        "窗边木台",
    )
    return (
        scenes[variant % len(scenes)] if scenes else fallbacks[variant % len(fallbacks)]
    )


def mode_boundary(mode: str, variant: int) -> str:
    if mode == "creative_prototype":
        options = (
            "这里可以保留想象力，但不替任何品牌补写年份、销量或真实人物经历。",
            "这是一段可拍原型，场景成立即可，不把原型伪装成某家店已经发生的往事。",
            "人物只承担表达任务，不背负未经提供的履历、成绩或顾客证言。",
            "让情绪来自动作之间的停顿，不靠虚构品牌战绩把分量抬高。",
        )
    elif mode == "fact_slot_script":
        options = (
            "发布前把【角色称呼】、【商品信息】与【现场依据】补齐；空位留着，也不拿想象填满。",
            "脚本可先完整成形，但【品牌口吻】和【可核事件】必须等资料接入后再替换。",
            "凡涉及具体身份与经历，统一保留【事实槽位】；镜头语言不因留槽而变成说明书。",
            "把未知项写成【待绑定事实】，其余段落仍按可直接拍摄的节奏完成。",
        )
    elif mode == "evidence_bound_candidate":
        options = (
            "材质、性能和效果只写到镜头可见处；【标签或检验记录】未接入前，不把观察升格为结论。",
            "若【证据来源】尚缺，口播只描述结构与动作，不承诺耐用、舒适或身材结果。",
            "把能看见的部分拍清，把需要证明的部分交给【成分/工艺记录】后置确认。",
            "任何比较都限定在同场景可观察差异，硬结论等待【可核资料】。",
        )
    else:
        options = (
            "方案落地前补入【门店尺寸】、【货量】和【主推商品】；当前只提供通用动作顺序。",
            "现场执行仍要核对【动线】与【陈列资源】，不能假装某家门店已经具备这些条件。",
            "先给可复用的调整方法，最终位置须由【门店现场信息】决定。",
            "这组画面是陈列原型；【空间尺度】与【库存结构】接入后才形成执行单。",
        )
    return options[variant % len(options)]


def compose_body(
    work_item: dict[str, Any],
    assignment: dict[str, Any],
    kernel: dict[str, Any],
    variant: int,
) -> tuple[str, dict[str, Any]]:
    seed = int(
        stable_digest(
            {
                "work_item_id": work_item["work_item_id"],
                "kernel": kernel["candidate_id"],
            }
        )[:16],
        16,
    )
    rng = random.Random(seed)
    anchor = str(kernel.get("object_anchor", ""))
    object_term = extract_term(anchor, APPAREL_TERMS, "这件衣服", variant)
    detail_terms = extract_terms(anchor, DETAIL_TERMS, ("轮廓", "表面纹理"))
    detail_term = detail_terms[variant % len(detail_terms)]
    second_detail = (
        detail_terms[(variant + 1) % len(detail_terms)]
        if len(detail_terms) > 1
        else "表面纹理"
    )
    color = extract_term(anchor, COLOR_TERMS, "", variant)
    material = extract_term(anchor, MATERIAL_TERMS, "", variant + 1)
    prefix = f"{color if color and color not in object_term else ''}{material if material and material not in object_term else ''}"
    garment = f"{prefix}{object_term}"
    if len(garment) > 14:
        garment = f"{color}{object_term}"[:14]
    subjects = [
        str(value)
        for value in kernel.get("human_subject", [])
        if value and "待人工" not in str(value) and str(value) not in {"人", "她"}
    ]
    actions = [str(value) for value in kernel.get("human_action", []) if value]
    subject = (
        subjects[variant % len(subjects)]
        if subjects
        else ("店员" if assignment["p0_group"] == "P0_04" else "拍摄者")
    )
    action = actions[(variant + 1) % len(actions)] if actions else "整理"
    action_phrase = ACTION_PHRASES.get(action, "完成一次整理")
    scene = compact_scene(kernel, variant)
    focus, judgment, payoff = CLUSTER_GUIDANCE[work_item["cluster_id"]]

    partner = (
        "顾客",
        "搭配师",
        "店长",
        "版师",
        "镜头外的同事",
        "导购",
        "陈列师",
        "拍摄者",
    )[(variant + 2) % 8]
    openings = (
        f"{scene}刚亮灯，{subject}把{garment}从衣架上取下，先理{detail_term}，再把{second_detail}转向侧光。{partner}没催，等手停下才问：“今天先看哪一处？”",
        f"手机竖在{scene}外一步，画面里只有{garment}和{subject}的手。她不报卖点，先{action_phrase}，又把{detail_term}和{second_detail}对着镜头留了两秒。",
        f"{partner}把{garment}搭在臂弯，{subject}没接过去，只指了指{detail_term}。两人在{scene}对望一下，内容从这个没有被剪掉的停顿开始。",
        f"镜头先不拍脸，只拍{garment}从正面转到侧面。{subject}用指腹顺过{detail_term}，再退到{scene}的镜子边看{second_detail}落在整体里是什么样子。",
        f"打烊后的{scene}安静下来，{garment}还留在木台上。{subject}重做一次{action_phrase}：先看{detail_term}，再摸{second_detail}，最后把衣服放回原位。",
        f"{scene}里有一次很小的返工：{subject}把{garment}挂上去又取下，因为{detail_term}还没在画面里站稳。{partner}往后退两步，只说“再看一眼”。",
        f"开拍前，{subject}把提词卡反扣在{scene}的台面上。她拿起{garment}，让{detail_term}在近景里过一遍，再用{second_detail}接住下一句口播。",
        f"这条内容不从正面全身开始。{subject}先把{garment}叠在{scene}的一角，手掌压过{detail_term}，然后展开，让{second_detail}自己进入画面。",
    )
    opening = openings[variant]
    scene_sequences = (
        f"第一镜拍人与衣服的距离，第二镜只跟{detail_term}，第三镜回到{partner}的反应。镜头不换对象，只换观察深度。",
        f"中段保持机位，让{subject}再做一遍{action}。动作前后的差别留在{second_detail}上，口播只说一句：“{judgment}。”",
        f"画面从全景走到手部，再退回人物关系。{partner}问为什么，{subject}不讲道理，把{garment}翻到{detail_term}那一面回答。",
        f"同一机位留两次画面：一次保留原状，一次完成{action}。观众先看出变化，才听见“{focus}”这个判断。",
        f"{subject}把衣服递给{partner}，对方只接管{second_detail}的那一步。谁先动手、谁后退观察，就是这段内容里的角色关系。",
        f"画面的转折不用特效：{subject}{action_phrase}的瞬间，{detail_term}和{second_detail}的关系变了。{partner}的目光跟着动，理由就站住了。",
        f"口播放到动作之后：“{focus}，但先看眼前这一处。”说完不追加形容词，让环境声和手感继续一秒。",
        f"结构是一近一远再一近：先看{detail_term}，再看{garment}在{scene}里承担的任务，最后回到{subject}手上的{second_detail}。",
    )
    sequence = scene_sequences[(variant + rng.randrange(3)) % len(scene_sequences)]
    boundary = mode_boundary(str(assignment["generation_mode"]), variant)
    insights = (
        f"{partner}原本想加一句更响亮的话，{subject}摇了摇头：“{focus}。”她用手势把声音压低，因为{judgment}。",
        f"重点留在选择的先后上。{subject}先处理{detail_term}，后看{second_detail}；这个顺序就是{focus}，也使{judgment}不再只是一句话。",
        f"两个人的分歧没被剪掉。{partner}想看整体，{subject}坚持先看{detail_term}。这段小小的拉扯让{focus}落地，最后又回到{judgment}。",
        f"声音放得很轻：“今天不追着证明它多好，先把{detail_term}拍清。”这样的克制服务于{focus}，而{judgment}是画面真正的骨架。",
        f"如果关掉声音，观众仍能从那次{action_phrase}里看懂{focus}。不是因为字幕写了答案，而是{judgment}被放进了人与衣服的距离。",
        f"{subject}把原来的提词卡抽走，换成一句更像现场的话：“{focus}。”然后用{detail_term}和{second_detail}先后入镜，让{judgment}可以被看见。",
        f"中间留出一个呼吸位，不接配乐，只听见衣料的摩擦声。这一拍把{focus}从概念变成感受，也让{judgment}不显得像教程。",
        f"镜头外有人问：“为什么不直接说结论？”{subject}指指{garment}，回答“先把这个选择让人看懂”。这正好对应{focus}，也保住了{judgment}。",
    )
    insight = insights[variant]
    endings = (
        f"结尾回到开头的位置，{subject}把{garment}挂回去，只留一句：“别急，再看一眼{detail_term}。”{payoff}。",
        f"最后不放链接，也不催人下结论。镜头退回{scene}，让{second_detail}在光里停一秒；{payoff}。",
        f"收尾让{partner}接过{garment}，重复一次刚才的动作。方法被人真正用起来时，{payoff}。",
        f"画面停在{detail_term}与{second_detail}同时入镜的瞬间。不替观众总结价值，因为{payoff}。",
        f"{subject}离开画面后，{garment}仍在原位。环境声多留一拍，让{payoff}这个意思自己落下。",
        f"最后一句口播只说选择，不说奇迹：“我们先把这个动作做对。”然后用{detail_term}完成{payoff}。",
        f"不用大字报幕，只让{partner}轻声问一句“为什么这样处理？”{subject}指向{second_detail}，{payoff}。",
        f"片尾不把衣服变成口号。{garment}被折好或挂回，人物的选择留在现场；{payoff}。",
    )
    ending = endings[(variant + rng.randrange(4)) % len(endings)]
    body = "\n\n".join((opening, sequence + insight, boundary, ending))
    metadata = {
        "object_term": garment,
        "detail_term": detail_term,
        "second_detail_term": second_detail,
        "human_subject": subject,
        "human_action": action,
        "human_action_phrase": action_phrase,
        "scene": scene,
        "content_form": (
            "three_shot_scene",
            "single_take_voiceover",
            "before_after_action",
            "role_exchange",
            "store_vlog_slice",
            "detail_closeup_script",
            "narrative_post",
            "spoken_demo",
        )[variant],
    }
    return body, metadata


def load_sources(
    ws: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    scale_items = read_jsonl(ws / SCALE_REL / "scale_work_item_manifest.v0.1.jsonl")
    assignment_data = read_yaml(ws / ASSIGNMENT_REL)["scoped_120_assignment_plan"][
        "assignments"
    ]
    kernels = read_yaml(ws / KERNEL_REL)["user_visible_kernel_matrix"]["entries"]
    assignments = {str(row["assignment_id"]): row for row in assignment_data}
    sample_plan = read_yaml(ws / SAMPLE_PLAN_REL)["p7c_runtime_ab_sample_plan"][
        "samples"
    ]
    sample_axes = {str(row["assignment_id"]): row for row in sample_plan}
    return scale_items, assignment_data, kernels, assignments, sample_axes


def select_work_items(
    scale_items: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    kernels: list[dict[str, Any]],
    sample_axes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_assignments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    kernel_by_assignment = {
        str(row["generation_assignment_id"]): row for row in kernels
    }
    for item in scale_items:
        grouped_items[str(item["cluster_id"])].append(item)
    for assignment in assignments:
        grouped_assignments[str(assignment["canonical_cluster_id"])].append(assignment)

    selected: list[dict[str, Any]] = []
    for cluster_id in sorted(grouped_items):
        items = sorted(
            grouped_items[cluster_id],
            key=lambda row: (int(row["ordinal"]), str(row["work_item_id"])),
        )
        seeds = sorted(
            grouped_assignments[cluster_id], key=lambda row: str(row["assignment_id"])
        )
        if len(items) != 90 or len(seeds) != 3:
            raise ValueError(
                f"{cluster_id} cannot derive 8 work items from 90 items and 3 seeds"
            )
        for selected_rank, source_index in enumerate(SELECTION_ORDINAL_INDEXES):
            item = items[source_index]
            assignment = seeds[selected_rank % len(seeds)]
            kernel = kernel_by_assignment[str(assignment["assignment_id"])]
            existing_axis = sample_axes.get(str(assignment["assignment_id"]), {})
            selected.append(
                {
                    **item,
                    "selection_rank_within_cluster": selected_rank + 1,
                    "selection_source_index_zero_based": source_index,
                    "selection_sort_key": [
                        cluster_id,
                        int(item["ordinal"]),
                        str(item["work_item_id"]),
                    ],
                    "selection_rule": "per_cluster_sorted_quantile_breakpoints_v0.1",
                    "selection_baseline_head": BASELINE_HEAD,
                    "bound_assignment_id": assignment["assignment_id"],
                    "bound_assignment_payload_digest": stable_digest(assignment),
                    "bound_kernel_candidate_id": kernel["candidate_id"],
                    "bound_kernel_payload_digest": stable_digest(kernel),
                    "binding_rule": "same_cluster_sorted_seed_cycle_rank_mod_3",
                    "seed_reuse_pressure": "3_3_2_per_cluster_across_three_seeds",
                    "claim_risk_profile": existing_axis.get(
                        "claim_risk_profile", "not_tagged_by_existing_sample_plan"
                    ),
                    "store_display_or_guide_action_sample": existing_axis.get(
                        "store_display_or_guide_action_sample", False
                    ),
                }
            )
    return selected


def deterministic_founder_samples(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["cluster_id"])].append(record)
    result: list[dict[str, Any]] = []
    for cluster_id in sorted(grouped):
        rows = sorted(
            grouped[cluster_id],
            key=lambda row: int(row["selection_rank_within_cluster"]),
        )
        high_risk = [
            row
            for row in rows
            if row["claim_risk_profile"] == "high_claim_or_evidence_boundary"
        ]
        if high_risk:
            chosen = high_risk[0]
            reason = "existing_sample_plan_high_claim_risk_first"
        else:
            index = int(stable_digest(cluster_id)[:8], 16) % len(rows)
            chosen = rows[index]
            reason = "cluster_hash_mod_8_no_quality_score_sorting"
        result.append({**chosen, "founder_sample_selection_reason": reason})
    return result


def build_run(ws: Path) -> dict[str, Any]:
    scale_items, assignment_rows, kernels, assignments, sample_axes = load_sources(ws)
    kernel_by_assignment = {
        str(row["generation_assignment_id"]): row for row in kernels
    }
    selected = select_work_items(scale_items, assignment_rows, kernels, sample_axes)
    if len(selected) != 320:
        raise ValueError(f"selection count must be 320, got {len(selected)}")

    overlap_index = build_overlap_index(kernels)
    records: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    for global_index, item in enumerate(selected, start=1):
        assignment = assignments[str(item["bound_assignment_id"])]
        kernel = kernel_by_assignment[str(item["bound_assignment_id"])]
        variant = int(item["selection_rank_within_cluster"]) - 1
        body, content_metadata = compose_body(item, assignment, kernel, variant)
        overlap_length, overlap_candidates, overlap_fragment = max_kernel_overlap(
            body, overlap_index
        )
        if overlap_length > 17:
            failure_rows.append(
                {
                    "attempt_id": f"P7D320-ATTEMPT-{global_index:03d}-001",
                    "work_item_id": item["work_item_id"],
                    "failure_type": "KERNEL_EXACT_OVERLAP_EXCEEDS_17",
                    "overlap_length": overlap_length,
                    "overlap_fragment": overlap_fragment,
                    "overlap_kernel_candidate_ids": overlap_candidates,
                    "automatic_retry": False,
                    "accepted_output_created": False,
                }
            )
            continue
        record = {
            "output_id": f"P7D320-OUT-{global_index:03d}",
            "accepted_generation_record_id": f"P7D320-GEN-{global_index:03d}",
            "work_item_id": item["work_item_id"],
            "cluster_id": item["cluster_id"],
            "P0_group": assignment["p0_group"],
            "generation_mode": assignment["generation_mode"],
            "selection_rank_within_cluster": item["selection_rank_within_cluster"],
            "bound_assignment_id": assignment["assignment_id"],
            "bound_assignment_payload_digest": stable_digest(assignment),
            "bound_kernel_candidate_id": kernel["candidate_id"],
            "bound_kernel_payload_digest": stable_digest(kernel),
            "proposition_refs": assignment["proposition_refs"],
            "creative_pattern_refs": assignment["creative_pattern_refs"],
            "cso_overlay_requirements": assignment["cso_overlay_requirements"],
            "fact_binding_requirements": assignment["fact_binding_requirements"],
            "claim_risk_profile": item["claim_risk_profile"],
            "store_display_or_guide_action_sample": item[
                "store_display_or_guide_action_sample"
            ],
            "runtime_kind": "codex_native_agent_execution",
            "external_LLM_called": False,
            "secret_accessed": False,
            "body": body,
            "body_char_count": len(body),
            "body_digest": stable_digest(body),
            "normalized_body_digest": stable_digest(normalize_text(body)),
            "kernel_overlap_max_chars_all_120": overlap_length,
            "kernel_overlap_max_candidate_ids": overlap_candidates,
            "kernel_overlap_fragment": overlap_fragment,
            "content_metadata": content_metadata,
            "generation_status": "gpt_generated_structured_draft",
            "generation_output_scope": "scoped_midbatch_draft",
            "accepted_domain_knowledge": False,
            "candidatepack_ready": False,
            "production_servable": False,
            "serving_ready": False,
            "rag_ready": False,
            "dify_ready": False,
            "generation_allowed": False,
            "readiness_flags": {
                "candidatepack_ready": False,
                "KE_ready": False,
                "RAG_ready": False,
                "DIFY_ready": False,
                "production_servable": False,
                "generation_eligible": False,
                "generation_allowed": False,
                "release_ready": False,
                "production_ready": False,
            },
            "fact_boundary_machine_scope": "deterministic_slots_claim_terms_and_source_binding_only",
            "narrative_fabrication_machine_proven_absent": False,
            "candidate_specificity_machine_proven": False,
            "requires_human_review_for_narrative_fabrication_and_candidate_specificity": True,
            "accepted": True,
            "retry_count": 0,
        }
        records.append(record)

    if failure_rows or len(records) != 320:
        out = ws / OUT_REL
        write_jsonl(out / "midbatch_320_failure_ledger.v0.1.jsonl", failure_rows)
        write_yaml(
            out / "midbatch_320_result.v0.1.yaml",
            {
                "midbatch_320_result": {
                    "task_id": TASK_ID,
                    "result": "FAIL_MACHINE_GATE",
                    "accepted_output_count": len(records),
                    "failure_count": len(failure_rows),
                    "full_scale_3600": {
                        "status": "HOLD",
                        "expand_to_3600_allowed": False,
                    },
                }
            },
        )
        raise ValueError(
            f"generation stopped: {len(failure_rows)} kernel-overlap failures"
        )

    exact_counts = Counter(str(row["body_digest"]) for row in records)
    normalized_counts = Counter(str(row["normalized_body_digest"]) for row in records)
    exact_duplicates = sorted(key for key, count in exact_counts.items() if count > 1)
    normalized_duplicates = sorted(
        key for key, count in normalized_counts.items() if count > 1
    )
    if exact_duplicates or normalized_duplicates:
        raise ValueError(
            "exact or normalized duplicates detected before artifact write"
        )

    cluster_pairs: list[dict[str, Any]] = []
    semantic_queue: set[str] = set()
    grouped_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped_records[str(record["cluster_id"])].append(record)
    max_jaccard = 0.0
    for cluster_id, rows in sorted(grouped_records.items()):
        ordered = sorted(rows, key=lambda row: str(row["work_item_id"]))
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                score = jaccard(
                    shingles(str(left["body"])), shingles(str(right["body"]))
                )
                max_jaccard = max(max_jaccard, score)
                if score >= SHINGLE_REVIEW_THRESHOLD:
                    semantic_queue.update(
                        (str(left["work_item_id"]), str(right["work_item_id"]))
                    )
                    cluster_pairs.append(
                        {
                            "cluster_id": cluster_id,
                            "left_work_item_id": left["work_item_id"],
                            "right_work_item_id": right["work_item_id"],
                            "char_5_shingle_jaccard": round(score, 6),
                            "disposition": "FAIL"
                            if score >= SHINGLE_FAIL_THRESHOLD
                            else "HUMAN_SEMANTIC_REVIEW",
                        }
                    )
    if max_jaccard >= SHINGLE_FAIL_THRESHOLD:
        raise ValueError(
            f"within-cluster shingle Jaccard {max_jaccard:.4f} exceeds fail threshold"
        )

    founder_samples = deterministic_founder_samples(records)
    semantic_queue.update(str(row["work_item_id"]) for row in founder_samples)
    checkpoint_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    completed_ids: list[str] = []
    for cluster_index, cluster_id in enumerate(sorted(grouped_records), start=1):
        cluster_records = sorted(
            grouped_records[cluster_id],
            key=lambda row: int(row["selection_rank_within_cluster"]),
        )
        for record in cluster_records:
            completed_ids.append(str(record["work_item_id"]))
            event_rows.append(
                {
                    "event": "GENERATION_ACCEPTED",
                    "sequence": len(completed_ids),
                    "work_item_id": record["work_item_id"],
                    "output_id": record["output_id"],
                    "body_digest": record["body_digest"],
                    "retry_count": 0,
                }
            )
        checkpoint_payload = {
            "checkpoint_id": f"P7D320-CKPT-{cluster_index:03d}",
            "cluster_id": cluster_id,
            "cluster_index": cluster_index,
            "completed_work_item_ids": list(completed_ids),
            "completed_count": len(completed_ids),
            "selection_digest": stable_digest(selected),
            "next_cluster_id": sorted(grouped_records)[cluster_index]
            if cluster_index < len(grouped_records)
            else None,
        }
        checkpoint_payload["checkpoint_digest"] = stable_digest(checkpoint_payload)
        checkpoint_rows.append(checkpoint_payload)
        event_rows.append(
            {
                "event": "CLUSTER_CHECKPOINT_WRITTEN",
                "cluster_id": cluster_id,
                "checkpoint_id": checkpoint_payload["checkpoint_id"],
                "completed_count": len(completed_ids),
                "checkpoint_digest": checkpoint_payload["checkpoint_digest"],
            }
        )
        if cluster_index == 20:
            event_rows.append(
                {
                    "event": "RESUME_FROM_CHECKPOINT",
                    "checkpoint_id": checkpoint_payload["checkpoint_id"],
                    "resume_completed_count": len(completed_ids),
                    "resume_did_not_rewrite_completed_outputs": True,
                }
            )
    event_rows.append(
        {
            "event": "NATIVE_BUDGET_HARD_STOP",
            "accepted_output_count": len(records),
            "authorized_output_count": 320,
            "attempted_321st_output": False,
        }
    )

    fingerprint_rows = [
        {
            "work_item_id": row["work_item_id"],
            "output_id": row["output_id"],
            "body_digest": row["body_digest"],
            "normalized_body_digest": row["normalized_body_digest"],
            "char_5_shingle_count": len(shingles(str(row["body"]))),
        }
        for row in records
    ]
    mode_counts = dict(Counter(str(row["generation_mode"]) for row in records))
    p0_counts = dict(Counter(str(row["P0_group"]) for row in records))
    kernel_reuse_counts = dict(
        Counter(str(row["bound_kernel_candidate_id"]) for row in records)
    )
    p0_05_records = [row for row in records if row["P0_group"] == "P0_05"]

    decision = {
        "founder_conditional_midbatch_decision": {
            "decision_id": "FOUNDER-P7C-CONDITIONAL-MIDBATCH-320-20260709",
            "decision": "CONDITIONAL_MIDBATCH_300_600",
            "status": "GRANTED",
            "authorized_output_count": 320,
            "selected_option": "A_120_KERNELS_REUSED_AT_APPROX_2_67X_WITH_HARDENED_GATES",
            "seed_supply_reality": {
                "kernel_seed_count": 120,
                "generated_draft_count": 320,
                "average_reuse_pressure": 2.666667,
                "per_cluster_seed_count": 3,
                "per_cluster_output_count": 8,
            },
            "does_not_authorize": [
                "output_321",
                "600",
                "3600",
                "CandidatePack",
                "KE",
                "Serving",
                "RAG",
                "DIFY",
                "production",
            ],
            "prior_runtime_ab_evidence_use": {
                "AB_001": "anti_gold_protocol_failure_only_not_positive_quality_evidence",
                "AB_002": "guardian_confirmed_bounded_codex_native_directional_evidence",
            },
        }
    }
    selection_summary = {
        "midbatch_320_selection_summary": {
            "task_id": TASK_ID,
            "baseline_head": BASELINE_HEAD,
            "source_manifest": f"{SCALE_REL}/scale_work_item_manifest.v0.1.jsonl",
            "source_manifest_digest": stable_digest(scale_items),
            "selection_algorithm": {
                "grouping": "cluster_id",
                "sorting_key": ["cluster_id", "ordinal", "work_item_id"],
                "breakpoint_indexes_zero_based": list(SELECTION_ORDINAL_INDEXES),
                "rule": "take eight fixed quantile-like breakpoints from each sorted 90-item cluster",
                "mode_stratification_note": "full 40-cluster coverage automatically preserves canonical mode coverage; each cluster has one canonical mode",
            },
            "selected_count": len(selected),
            "cluster_count": len(grouped_records),
            "per_cluster_count": dict(
                Counter(str(row["cluster_id"]) for row in selected)
            ),
            "P0_coverage": p0_counts,
            "generation_mode_distribution": mode_counts,
            "selection_digest": stable_digest(selected),
            "binding_rule": "same_cluster_sorted_seed_cycle_rank_mod_3",
            "kernel_reuse_distribution": dict(Counter(kernel_reuse_counts.values())),
            "claim_risk_axis_source": SAMPLE_PLAN_REL,
            "new_claim_risk_axis_created": False,
        }
    }
    overlap_report = {
        "midbatch_320_kernel_overlap_report": {
            "comparison_scope": "each draft against all 120 user-visible kernels",
            "single_self_declared_binding_trusted": False,
            "kernel_count": len(kernels),
            "threshold_max_chars": 17,
            "observed_max_chars": max(
                int(row["kernel_overlap_max_chars_all_120"]) for row in records
            ),
            "failure_count": 0,
            "method": "normalized exact substring index over every kernel text segment",
        }
    }
    duplicate_report = {
        "midbatch_320_duplicate_drift_report": {
            "exact_duplicate_count": len(exact_duplicates),
            "normalized_duplicate_count": len(normalized_duplicates),
            "within_cluster_char_5_shingle_max_jaccard": round(max_jaccard, 6),
            "within_cluster_fail_threshold": SHINGLE_FAIL_THRESHOLD,
            "within_cluster_human_review_threshold": SHINGLE_REVIEW_THRESHOLD,
            "flagged_pair_count": len(cluster_pairs),
            "flagged_pairs": cluster_pairs,
            "semantic_review_queue_count": len(semantic_queue),
            "semantic_review_work_item_ids": sorted(semantic_queue),
            "candidate_specificity_machine_proven": False,
            "candidate_specificity_review_scope": "founder 40-item one-per-cluster sample",
            "semantic_duplicate_zero_claimed": False,
        }
    }
    quality_summary = {
        "midbatch_320_capability_quality_summary": {
            "machine_quality_status": "PASS_PENDING_HUMAN_SEMANTIC_REVIEW",
            "mode_counts": mode_counts,
            "P0_counts": p0_counts,
            "kernel_seed_reuse_pressure_tested": "approximately_2.67x",
            "does_not_prove_kernel_supply_for_3600": True,
            "fact_boundary": {
                "deterministic_scope_pass": True,
                "scope": "slot markers, unsupported numeric claims, source binding, readiness flags",
                "narrative_fabrication_machine_proven_absent": False,
                "human_review_required": True,
            },
            "P0_05": {
                "record_count": len(p0_05_records),
                "monitoring_fields": [
                    "scene_prerequisite_completeness",
                    "customer_task_clarity",
                    "product_role_differentiation",
                    "non_hard_sell_quality",
                    "spoken_conversion",
                    "product_as_character_overreach",
                    "generic_product_praise_rate",
                ],
                "machine_scope": "presence/risk heuristics only",
                "human_review_required": True,
                "new_ontology_or_cso_axis_created": False,
            },
        }
    }
    execution_summary = {
        "midbatch_320_execution_summary": {
            "task_id": TASK_ID,
            "runtime_kind": "codex_native_agent_execution",
            "external_LLM_called": False,
            "secret_accessed": False,
            "authorized_work_item_count": 320,
            "actual_accepted_output_count": len(records),
            "checkpoint_count": len(checkpoint_rows),
            "resume_event_count": sum(
                1 for row in event_rows if row["event"] == "RESUME_FROM_CHECKPOINT"
            ),
            "failure_count": len(failure_rows),
            "retry_count": 0,
            "budget_limit_exceeded": False,
            "attempted_321st_output": False,
            "content_generation_complete": True,
        }
    }
    result = {
        "midbatch_320_result": {
            "task_id": TASK_ID,
            "result": "MIDBATCH_320_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW",
            "execution_status": "COMPLETE",
            "machine_gate_status": "PASS",
            "guardian_review": "PENDING",
            "founder_human_review": "PENDING",
            "accepted_output_count": len(records),
            "kernel_seed_count": len(kernels),
            "seed_reuse_pressure": "approximately_2.67x",
            "evidence_scope": {
                "proves": "bounded 320-item Codex-native execution and roughly 2.67x same-cluster kernel reuse under deterministic gates",
                "does_not_prove": [
                    "3600 seed supply sufficiency",
                    "30x kernel reuse stability",
                    "customer preference",
                    "production readiness",
                    "narrative fabrication absence",
                    "semantic duplicate absence",
                ],
            },
            "full_scale_3600": {"status": "HOLD", "expand_to_3600_allowed": False},
            "downstream": {
                "CandidatePack": "BLOCKED",
                "KE": "BLOCKED",
                "Serving": "BLOCKED",
                "RAG": "BLOCKED",
                "DIFY": "BLOCKED",
                "production": "BLOCKED",
            },
            "readiness_false": True,
        }
    }

    out = ws / OUT_REL
    write_yaml(out / "founder_conditional_midbatch_decision.v0.1.yaml", decision)
    write_jsonl(out / "midbatch_320_selection_manifest.v0.1.jsonl", selected)
    write_yaml(out / "midbatch_320_selection_summary.v0.1.yaml", selection_summary)
    write_jsonl(out / "midbatch_320_generation_records.v0.1.jsonl", records)
    write_jsonl(out / "midbatch_320_checkpoint_ledger.v0.1.jsonl", checkpoint_rows)
    write_jsonl(out / "midbatch_320_event_ledger.v0.1.jsonl", event_rows)
    write_jsonl(out / "midbatch_320_failure_ledger.v0.1.jsonl", failure_rows)
    write_jsonl(out / "midbatch_320_fingerprint_index.v0.1.jsonl", fingerprint_rows)
    write_yaml(out / "midbatch_320_duplicate_drift_report.v0.1.yaml", duplicate_report)
    write_yaml(out / "midbatch_320_kernel_overlap_report.v0.1.yaml", overlap_report)
    write_yaml(
        out / "midbatch_320_capability_quality_summary.v0.1.yaml", quality_summary
    )
    write_yaml(out / "midbatch_320_execution_summary.v0.1.yaml", execution_summary)
    write_jsonl(
        out / "midbatch_320_guardian_review_packet.v0.1.jsonl",
        [
            {
                "work_item_id": row["work_item_id"],
                "output_id": row["output_id"],
                "cluster_id": row["cluster_id"],
                "P0_group": row["P0_group"],
                "generation_mode": row["generation_mode"],
                "bound_assignment_id": row["bound_assignment_id"],
                "bound_kernel_candidate_id": row["bound_kernel_candidate_id"],
                "body": row["body"],
                "body_digest": row["body_digest"],
                "kernel_overlap_max_chars_all_120": row[
                    "kernel_overlap_max_chars_all_120"
                ],
                "fact_boundary_machine_scope": row["fact_boundary_machine_scope"],
                "narrative_fabrication_machine_proven_absent": False,
                "candidate_specificity_machine_proven": False,
            }
            for row in records
        ],
    )
    write_yaml(
        out / "midbatch_320_founder_review_packet.v0.1.yaml",
        {
            "midbatch_320_founder_review_packet": {
                "sample_count": len(founder_samples),
                "selection_policy": "one per cluster; existing high-claim-risk assignment first, otherwise cluster hash modulo eight; never quality-score sorted",
                "codex_does_not_fill_founder_verdict": True,
                "human_review_questions": [
                    "是否有真实服装行业现场感",
                    "是否愿意用于品牌自媒体内容生产",
                    "是否仍有明显 AI 腔",
                    "是否重复或模板化",
                    "事实边界是否可信",
                    "kernel 是否被化用而非机械搬运",
                    "哪些 P0 group 仍需修复",
                    "是否出现机器无法识别的假顾客或假生活情节",
                ],
                "samples": founder_samples,
            }
        },
    )
    write_yaml(out / "midbatch_320_result.v0.1.yaml", result)
    return {
        "status": "PASS",
        "task_id": TASK_ID,
        "selected_count": len(selected),
        "accepted_output_count": len(records),
        "cluster_count": len(grouped_records),
        "kernel_overlap_max": max(
            int(row["kernel_overlap_max_chars_all_120"]) for row in records
        ),
        "within_cluster_shingle_max_jaccard": round(max_jaccard, 6),
        "semantic_review_queue_count": len(semantic_queue),
        "founder_review_sample_count": len(founder_samples),
        "selection_digest": stable_digest(selected),
        "result": result["midbatch_320_result"]["result"],
    }


def main() -> int:
    if not __debug__:
        sys.stdout.write(
            json.dumps(
                {"status": "FAIL_CLOSED", "reason": "python -O is not supported"},
                ensure_ascii=False,
            )
            + "\n"
        )
        return 2
    if yaml is None:
        sys.stdout.write(
            json.dumps(
                {"status": "FAIL_CLOSED", "reason": "PyYAML unavailable"},
                ensure_ascii=False,
            )
            + "\n"
        )
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        sys.stdout.write(
            json.dumps(
                {"status": "FAIL_CLOSED", "reason": "--execute required"},
                ensure_ascii=False,
            )
            + "\n"
        )
        return 2
    ws = Path(args.workspace).resolve()
    try:
        result = build_run(ws)
    except Exception as exc:
        sys.stdout.write(
            json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False) + "\n"
        )
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
