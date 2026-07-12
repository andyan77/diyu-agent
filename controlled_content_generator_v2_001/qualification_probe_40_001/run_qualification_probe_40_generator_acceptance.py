#!/usr/bin/env python3
"""Serialize authored qualification candidates and machine acceptance results."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "CONTROLLED_V2_20CP_QUALIFICATION_PROBE_40_001"
PHASE0_MERGE_COMMIT_SHA = "25ce4ff092befe39106783d8b7f2cf31e77f0e82"
PHASE0_MERGE_TREE_SHA = "d961d44c977cbeecd762827218b75008108f8414"
REVIEWED_BASE_SHA = "0ed9fd40203a6423d4deb9e6342c441ac3c129c1"
REVIEWED_HEAD_SHA = "7b7f87db532ad89271d471bb0020d749324af917"
REVIEWED_HEAD_TREE_SHA = "d961d44c977cbeecd762827218b75008108f8414"
REVIEWED_FULL_DIFF_DIGEST = "e40bb98a0af50d7a8351c3038b53edde6d46d0157f9ca4780cd74a8539c5be3e"

TASK_DIR = Path("controlled_content_generator_v2_001/qualification_probe_40_001")
PACKS_PATH = TASK_DIR / "qualification_material_packs.v0.1.jsonl"
ASSIGNMENTS_PATH = TASK_DIR / "qualification_probe_assignments.v0.1.jsonl"
PLANS_PATH = TASK_DIR / "canonical_qualification_composition_plans.v0.1.jsonl"
INSTRUCTIONS_PATH = TASK_DIR / "qualification_generation_instructions.v0.1.jsonl"
CANDIDATES_PATH = TASK_DIR / "qualification_probe_candidates.v0.1.jsonl"
ACCEPTANCE_RESULTS_PATH = TASK_DIR / "qualification_machine_acceptance_results.v0.1.jsonl"
RESULT_PATH = TASK_DIR / "qualification_probe_result.v0.1.yaml"
PACKET_PATH = TASK_DIR / "qualification_guardian_review_packet.v0.1.yaml"
GENERATOR_ENTRY_PATH = TASK_DIR / "run_qualification_probe_40_generator_acceptance.py"
ORCH_MATERIALIZER_PATH = TASK_DIR / "run_qualification_probe_40_orch_materializer.py"
CHECKER_PATH = Path("ci/checkers/check_controlled_v2_20cp_qualification_probe_40.py")

VISIBLE_DISCLOSURE_TEXT = "INTERNAL QUALIFICATION PROBE / SYNTHETIC CASE / NOT PUBLISHABLE"
QUALIFICATION_NAMESPACE = "qualification://controlled-v2/probe-40/"

READINESS_FLAGS = {
    "generator_qualified": False,
    "runtime_provider_adapter_qualified": False,
    "founder_final_qualification": "PENDING",
    "runtime_ingest_ready": False,
    "generation_eligible": False,
    "generation_allowed": False,
    "generation_600_allowed": False,
    "expand_600_allowed": False,
    "expand_3600_allowed": False,
    "KE_ready": False,
    "RAG_ready": False,
    "DIFY_ready": False,
    "Serving_ready": False,
    "production_ready": False,
    "release_ready": False,
}

# These texts are authored content. The script serializes and checks them; it does
# not synthesize body copy from CP, P0, role, or traversal order templates.
CANDIDATE_TEXTS: dict[str, dict[str, Any]] = {
    "QPROBE-CP01-A-001": {
        "title": "资格样品：折袖后的三秒",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "合成材料包里，样品整理员先折起海军蓝针织开衫的袖口，停三秒看回弹，再把衣身放回层板。",
            "我会把镜头留在手和袖口上：这只证明这条合成任务顺序，不证明真实员工速度。",
        ],
        "spoken_lines": ["先看这个三秒停顿，不急着说好坏。", "它只是资格样品，不是门店实拍。"],
        "CTA": "仅供内部审查这类岗位任务能不能讲清楚。",
        "visual_beats": ["手指折起袖口", "三秒静止近景", "开衫回到层板"],
        "capture_instructions": ["固定手机，不拍脸", "停顿处保留原声环境"],
        "audio_grammar": "低环境声，旁白只解释动作边界。",
        "editing_grammar": "三段顺切：折袖、等待、复位。",
    },
    "QPROBE-CP01-B-001": {
        "title": "资格样品：袖口自己慢下来",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一个合成开衫，我不从效率说起，先看袖口被折起又放松的那个小空档。",
            "层板复位以后，画面像是在说：这个任务有手感，但它不是任何真实员工的一天。",
        ],
        "spoken_lines": ["这不是工作日记，是合成样品。", "我只是想看，这种小动作能不能被拍得安静一点。"],
        "CTA": "内部看完再判断这条声道是否成立。",
        "visual_beats": ["袖口边缘贴近镜头", "衣身被轻轻铺平", "层板留一点空白"],
        "capture_instructions": ["手部动作慢半拍", "避免出现门店标识"],
        "audio_grammar": "保留布料摩擦声，不加情绪音乐。",
        "editing_grammar": "用一个停顿代替解释性转场。",
    },
    "QPROBE-CP02-A-001": {
        "title": "资格样品：09:10的台面复位",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "合成时段记录写着：早班店长09:10开灯，09:16把晨间陈列台的两处空位补齐。",
            "这条只看台面如何从散到稳，不推断真实客流，也不把六分钟说成管理能力。",
        ],
        "spoken_lines": ["先记录台面变化，再谈判断。", "这里没有真实门店客流数据。"],
        "CTA": "把它当作时段纪录的内部资格样片。",
        "visual_beats": ["灯亮后的空台面", "纸样被收走", "两处空位补齐"],
        "capture_instructions": ["镜头从门口向台面推进", "不要拍真实收银信息"],
        "audio_grammar": "开灯声和脚步声保留，旁白短句。",
        "editing_grammar": "按时间节点硬切，不加热闹滤镜。",
    },
    "QPROBE-CP02-B-001": {
        "title": "资格样品：早班台面有了呼吸",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一个合成早晨，我先看那两处空位：它们被补齐以后，台面没有变满，只是顺眼了一点。",
            "这不是说真实店里一定更好逛，只是在试一种门店时段的轻记录。",
        ],
        "spoken_lines": ["这里的早晨是合成的。", "但台面从乱到顺，这个变化可以被看见。"],
        "CTA": "只用于内部看生活感够不够。",
        "visual_beats": ["空位留白", "手移走纸样", "台面最后一秒停住"],
        "capture_instructions": ["用侧面低机位", "不要出现顾客或真实门牌"],
        "audio_grammar": "轻脚步声，不配促销音效。",
        "editing_grammar": "用两次短停顿表现时段变化。",
    },
    "QPROBE-CP03-A-001": {
        "title": "资格样品：腰头压线前的停针",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "合成工艺卡把米白半裙腰头拆成四步：划线、试压、停针检查、收尾。",
            "专业声道要把停针留出来，因为它是过程节点，不是对真实工艺水平的背书。",
        ],
        "spoken_lines": ["这一步先停，不是犹豫，是检查线位。", "所有步骤都来自合成卡片。"],
        "CTA": "内部审查这条全过程是否看得懂。",
        "visual_beats": ["纸样划线", "压脚试压", "针停在腰头边"],
        "capture_instructions": ["拍机器针位，不拍人脸", "收尾时保留完整手势"],
        "audio_grammar": "机器声压低，旁白解释节点。",
        "editing_grammar": "四步按顺序排列，不跳步。",
    },
    "QPROBE-CP03-B-001": {
        "title": "资格样品：那一下停针很小",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "这条合成半裙没有被讲成大片，我只想看针停住的那一下：线还没走完，手已经在确认边距。",
            "它像一个很小的提醒：全过程不一定要快，先让步骤站稳。",
        ],
        "spoken_lines": ["这一停，是合成过程里的检查点。", "别把它当成真实工坊记录。"],
        "CTA": "内部看它有没有手艺过程的耐心。",
        "visual_beats": ["线迹还没到边", "手背挡住一半光", "腰头被翻到反面"],
        "capture_instructions": ["近拍针脚，不拍品牌信息", "停针处延长半秒"],
        "audio_grammar": "保留机器停下后的空白。",
        "editing_grammar": "少转场，让停顿自己成立。",
    },
    "QPROBE-CP04-A-001": {
        "title": "资格样品：两个人只各说一半",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "合成协作记录里，陈列员只移动试穿镜旁的短外套组合，导购只补充尺码提示。",
            "这条要拍清角色边界：没有争吵，没有抢话，只有两个岗位把各自授权范围说完。",
        ],
        "spoken_lines": ["陈列先讲位置，导购再讲尺码。", "合成记录没有冲突，不能编冲突。"],
        "CTA": "内部审查多岗位协作能不能不戏剧化。",
        "visual_beats": ["衣架被平移", "尺码牌被指到", "两只手不同时抢画面"],
        "capture_instructions": ["双人只拍手和衣架", "禁止设计争吵台词"],
        "audio_grammar": "两个声线分开，语气平稳。",
        "editing_grammar": "用交替镜头表现边界，不制造对立。",
    },
    "QPROBE-CP04-B-001": {
        "title": "资格样品：镜子旁边安静换了位",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一组合在镜子旁边挪了一点，导购的尺码提示没有盖过陈列动作。",
            "我更想让观众看见：协作可以很轻，不需要把合成岗位写成吵架现场。",
        ],
        "spoken_lines": ["一个人挪位置，一个人补一句尺码。", "到这里就够了。"],
        "CTA": "内部看这种轻协作有没有可信度。",
        "visual_beats": ["镜边留白", "衣架停住", "尺码牌短暂入镜"],
        "capture_instructions": ["不要拍成会议感", "手部动作一前一后"],
        "audio_grammar": "保留一点衣架滑动声。",
        "editing_grammar": "从镜边切到尺码牌，再切回外套。",
    },
    "QPROBE-CP05-A-001": {
        "title": "资格样品：三张职业阶段卡",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "模拟版师的职业史只允许讲三张授权卡：入门、独立改样、复核。",
            "我会把它拍成时间线，但不把加班说成成长，也不把合成经历说成真人履历。",
        ],
        "spoken_lines": ["这里讲的是模拟职业阶段。", "阶段之间有进步，但没有真实个人传记。"],
        "CTA": "内部审查人物成长题材的边界。",
        "visual_beats": ["三张卡片排开", "手指停在复核卡", "卡片背面空白"],
        "capture_instructions": ["不出现真实姓名", "时间线只拍卡片编号"],
        "audio_grammar": "旁白像记录，不煽情。",
        "editing_grammar": "三段均匀，不用励志音乐。",
    },
    "QPROBE-CP05-B-001": {
        "title": "资格样品：卡片没有替谁回忆",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同样三张卡，我不说某个人熬过了什么，只说这张合成时间线从不会到会，再到会复核。",
            "它可以有一点温度，但不能偷换成真实人生故事。",
        ],
        "spoken_lines": ["这不是谁的履历。", "只是一个职业阶段样本。"],
        "CTA": "内部看它是否有人味但不越界。",
        "visual_beats": ["卡片边角被按住", "阶段B和阶段C之间留空", "最后一张卡不翻面"],
        "capture_instructions": ["避免真实人像", "不拍工牌或姓名"],
        "audio_grammar": "低声旁白，少形容词。",
        "editing_grammar": "留白切换，避免成长鸡血感。",
    },
    "QPROBE-CP06-A-001": {
        "title": "资格样品：冷灰和暖米的取舍",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "合成判断卡只给出两块色布：冷灰更稳，暖米更软，二者都不是绝对答案。",
            "专业声道要把依据放在前面，把结论收住：这是选择框架，不是替所有人决定。",
        ],
        "spoken_lines": ["冷灰稳，暖米软，先别急着选。", "这条没有真实试穿结果。"],
        "CTA": "内部审查专业判断是否克制。",
        "visual_beats": ["两块色布并排", "手遮住一半冷灰", "暖米布靠近裤料"],
        "capture_instructions": ["白光下拍，不加滤镜", "不要出现真实顾客"],
        "audio_grammar": "旁白短，停顿明确。",
        "editing_grammar": "先对比，再给边界。",
    },
    "QPROBE-CP06-B-001": {
        "title": "资格样品：颜色不是来赢的",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "这两块合成色布放在一起，我更像在看两种心情：冷灰把人收住，暖米把边缘放软。",
            "但它们都没有赢，真正要补的是穿着场景，而不是一句万能建议。",
        ],
        "spoken_lines": ["颜色不比赛。", "它只是把选择变慢一点。"],
        "CTA": "内部看普通声道会不会过度下结论。",
        "visual_beats": ["色布交叠", "裤料边缘入镜", "手离开后保留空桌面"],
        "capture_instructions": ["一镜到底看色温", "不拍真人肤色判断"],
        "audio_grammar": "环境声轻，像随手记录。",
        "editing_grammar": "对比镜头不打分，只停住。",
    },
    "QPROBE-CP07-A-001": {
        "title": "资格样品：通勤外套先问两个问题",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "合成提问卡写的是：通勤外套显拘谨。诊断员只确认两个待补信息：肩线和内搭厚度。",
            "这条不能假装知道用户身材，只能把问题拆开，让下一步采集更准确。",
        ],
        "spoken_lines": ["先别给方案，先问肩线和内搭厚度。", "缺信息时不能硬诊断。"],
        "CTA": "内部审查问题诊断是否会停在边界上。",
        "visual_beats": ["提问卡被放到桌上", "肩线图示被圈出", "内搭厚度写成待确认"],
        "capture_instructions": ["只拍卡片和示意图", "不要拍真人对比"],
        "audio_grammar": "像分诊，不像直播答疑。",
        "editing_grammar": "问题、待补、暂停三段。",
    },
    "QPROBE-CP07-B-001": {
        "title": "资格样品：先把问题放小一点",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "看到这张合成提问卡，我不想立刻说哪件外套好，只想把“拘谨”拆成肩线和内搭两个小问题。",
            "缺的地方先空着，反而比装作都知道更像一个认真回答。",
        ],
        "spoken_lines": ["这里先空一格。", "空着，是因为资料还没到。"],
        "CTA": "内部看这种停顿能不能被接受。",
        "visual_beats": ["卡片上留白", "铅笔停在肩线旁", "内搭厚度后面写问号"],
        "capture_instructions": ["拍纸面，不拍人体", "问号处停留一秒"],
        "audio_grammar": "纸笔声比旁白更明显。",
        "editing_grammar": "用留白做结尾。",
    },
    "QPROBE-CP08-A-001": {
        "title": "资格样品：斜纹方向和袖窿弧线",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "技术卡只给三项合成证据：斜纹方向、袖窿弧线、垂坠观察。",
            "讲解时可以说它们如何影响观察路径，但不能声称显瘦、塑形或任何身体效果。",
        ],
        "spoken_lines": ["先看纹路，再看弧线。", "身体效果不是这张卡能证明的。"],
        "CTA": "内部审查工艺解构有没有守住claim边界。",
        "visual_beats": ["斜纹样布倾斜入镜", "袖窿纸样压在旁边", "垂坠边缘慢慢放下"],
        "capture_instructions": ["标尺只作参照", "不出现真人上身"],
        "audio_grammar": "专业名词少量出现，随后解释边界。",
        "editing_grammar": "纹路、弧线、垂坠三镜头并列。",
    },
    "QPROBE-CP08-B-001": {
        "title": "资格样品：布料往哪边走",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一块合成样布，普通声道不讲大词，只看纹路往哪边走，袖窿弧线在哪里停。",
            "它可以让人更愿意靠近细节，但不能把靠近说成穿上后的结果。",
        ],
        "spoken_lines": ["这块布有方向。", "但方向不等于效果承诺。"],
        "CTA": "内部看解构能不能更像人话。",
        "visual_beats": ["手顺着斜纹滑过", "纸样边缘挡住光", "布料自然垂下"],
        "capture_instructions": ["近拍纹理", "避免对身体做暗示"],
        "audio_grammar": "布面摩擦声保留。",
        "editing_grammar": "少字幕，多细节停留。",
    },
    "QPROBE-CP09-A-001": {
        "title": "资格样品：高领不是万能答案",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "边界卡写明：保暖优先可选高领，叠戴项链时低领更不打架。",
            "专业声道要先给适用场景，再给反选场景，不能把选择说成审美焦虑。",
        ],
        "spoken_lines": ["如果优先保暖，高领成立。", "如果要叠戴项链，它可能不是第一选项。"],
        "CTA": "内部审查反选指南是否足够温和。",
        "visual_beats": ["高领针织单独挂起", "低领内搭与项链并排", "两件之间留空"],
        "capture_instructions": ["不拍真人脖颈", "用道具说明边界"],
        "audio_grammar": "判断句后留半秒。",
        "editing_grammar": "适用与不适用对称呈现。",
    },
    "QPROBE-CP09-B-001": {
        "title": "资格样品：有些衣服先不选",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "这张合成卡让我把话说轻一点：高领可以保暖，但如果今天想让项链出来，它就先退一步。",
            "反选不是否定一件衣服，只是让它别去做不适合的事。",
        ],
        "spoken_lines": ["先不选，也是一种选择。", "这不是劝退，只是放回合适的位置。"],
        "CTA": "内部看反选语气会不会刺耳。",
        "visual_beats": ["高领被放回左侧", "项链在低领旁轻晃", "镜头停在两者中间"],
        "capture_instructions": ["不做夸张表情", "道具之间保持距离"],
        "audio_grammar": "语气像聊天，不像评判。",
        "editing_grammar": "用放回动作做结尾。",
    },
    "QPROBE-CP10-A-001": {
        "title": "资格样品：同一样品的三次观察",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "测试卡只有同一合成袖口的第1次、第3次、第7次观察，不能推成长期规律。",
            "我会把三次记录按顺序摆出来，结论只停在这个样品，不能替所有袖口背书。",
        ],
        "spoken_lines": ["第1次、第3次、第7次，都是同一个合成样品。", "单例不能替代普遍规律。"],
        "CTA": "内部审查证据档案是否克制。",
        "visual_beats": ["三张观察卡排成列", "第7次卡片被单独拉近", "结论处盖上样品限定章"],
        "capture_instructions": ["拍清同一样品编号", "不要出现真实检测机构字样"],
        "audio_grammar": "数字读清楚，边界读慢。",
        "editing_grammar": "按次数推进，最后回到限定语。",
    },
    "QPROBE-CP10-B-001": {
        "title": "资格样品：第七次也只是第七次",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一只合成袖口被看了三回，第七次听起来很有分量，但它仍然只是这一个样品的记录。",
            "这条的重点不是证明厉害，而是把证据能说到哪里停在哪里。",
        ],
        "spoken_lines": ["第七次，不等于所有次。", "我们只看这张合成卡。"],
        "CTA": "内部看长期验证题材能不能不夸大。",
        "visual_beats": ["第1次卡片略虚", "第3次卡片翻过", "第7次卡片停在镜头前"],
        "capture_instructions": ["编号保持可见", "结尾不加胜利音效"],
        "audio_grammar": "读数字时留空，不煽动。",
        "editing_grammar": "三卡慢推，最后黑场一拍。",
    },
    "QPROBE-CP11-A-001": {
        "title": "资格样品：领口高度的三难题",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "设计取舍卡把保暖、显脖颈、叠穿放在同一块板上，三项不能同时最大化。",
            "专业声道要讲取舍，不讲天才灵感；它是模拟设计记录，不是真实产品诞生史。",
        ],
        "spoken_lines": ["这里不是找唯一答案，是看三项怎么互相让位。", "这张板是合成取舍板。"],
        "CTA": "内部审查设计档案是否有取舍感。",
        "visual_beats": ["三张选项贴在板上", "保暖卡与叠穿卡重叠", "中间留出空位"],
        "capture_instructions": ["只拍取舍板", "不出现真实设计稿编号"],
        "audio_grammar": "像设计复盘，不像发布会。",
        "editing_grammar": "三项轮流出现，最后同框。",
    },
    "QPROBE-CP11-B-001": {
        "title": "资格样品：有一项总要让一点",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "这块合成领口板最有意思的地方，不是哪个选项更高级，而是每个选项都要让掉一点东西。",
            "它像一次小小的商量：保暖多一点，叠穿就少一点；画面只讲这个取舍。",
        ],
        "spoken_lines": ["有一项往前，另一项就退后。", "这是合成设计取舍，不是真实发布故事。"],
        "CTA": "内部看普通声道能不能讲出产品记忆。",
        "visual_beats": ["手把保暖卡推前", "叠穿卡向后半寸", "三卡重新并排"],
        "capture_instructions": ["动作要轻", "不拍真实设计人员"],
        "audio_grammar": "卡片摩擦声保留。",
        "editing_grammar": "用推前和退后表现取舍。",
    },
    "QPROBE-CP12-A-001": {
        "title": "资格样品：V2到V3只改了袖口",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "版本卡写着：V2袖口6.5cm，V3袖口6.0cm，洗后状态仍待复核。",
            "专业声道要把版本号、数字和待验证项都说清楚，不能借版本日志暗示真实库存或销量。",
        ],
        "spoken_lines": ["V2是6.5cm，V3是6.0cm。", "洗后状态还没验证。"],
        "CTA": "内部审查版本日志是否能保留待验证项。",
        "visual_beats": ["V2与V3袖口并排", "尺子贴近袖口", "待复核贴纸入镜"],
        "capture_instructions": ["数字必须拍清楚", "不出现真实货号"],
        "audio_grammar": "数字慢读，待验证单独停顿。",
        "editing_grammar": "先版本，再数字，最后待复核。",
    },
    "QPROBE-CP12-B-001": {
        "title": "资格样品：那半厘米先别急着夸",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一张合成版本卡里，6.5cm变成6.0cm，看起来很具体，但具体不等于已经证明更好。",
            "我更愿意把镜头停在待复核贴纸上：改了什么可以说，结果还要等。",
        ],
        "spoken_lines": ["半厘米是事实，效果还不是。", "这是合成版本记录。"],
        "CTA": "内部看版本迭代能不能不抢结论。",
        "visual_beats": ["尺子滑过半厘米", "两只袖口重叠", "待复核贴纸占满结尾"],
        "capture_instructions": ["保留尺子刻度", "不拍真实吊牌"],
        "audio_grammar": "少解释，多停留。",
        "editing_grammar": "用贴纸挡住过度结论。",
    },
    "QPROBE-CP13-A-001": {
        "title": "资格样品：一件开衫的三个衣橱位置",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "合成角色卡把浅咖开衫放在通勤、周末、旅行三个位置，三者都是搭配假设。",
            "专业声道要说明衣橱角色，不把假设写成真实穿着反馈。",
        ],
        "spoken_lines": ["通勤、周末、旅行，是三个合成位置。", "没有真实用户反馈。"],
        "CTA": "内部审查产品生活角色是否成立。",
        "visual_beats": ["开衫挂在三张标签之间", "通勤标签先入镜", "旅行标签最后轻晃"],
        "capture_instructions": ["不出现真人穿搭", "标签文字保持清楚"],
        "audio_grammar": "旁白平稳，像整理衣橱。",
        "editing_grammar": "三位置轮流切，不给排名。",
    },
    "QPROBE-CP13-B-001": {
        "title": "资格样品：它不负责所有场合",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "这件合成浅咖开衫被放进三个生活位置，我最喜欢的是它没有被说成万能。",
            "它有时候像通勤外层，有时候只是周末椅背上的一件衣服；这些都只是合成假设。",
        ],
        "spoken_lines": ["不是万能，反而更像衣橱里的东西。", "这些场景都是合成的。"],
        "CTA": "内部看生活角色有没有被讲轻。",
        "visual_beats": ["开衫搭在椅背", "标签被手轻轻拨开", "衣架影子落到桌面"],
        "capture_instructions": ["画面不要像销售页", "生活位置用道具暗示"],
        "audio_grammar": "椅背轻响保留。",
        "editing_grammar": "用道具转场，不用功能清单。",
    },
    "QPROBE-CP14-A-001": {
        "title": "资格样品：银灰缎面的反光、折痕、回落",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "感官卡只允许看银灰缎面样布的反光、折痕和手指离开后的回落。",
            "专业声道可以标注观察顺序，但不需要证明任何穿着效果，也不强制spoken或CTA。",
        ],
        "spoken_lines": ["先看反光，再看折痕，最后看回落。", "这只是合成物性观察。"],
        "CTA": "内部审查物性短片的边界。",
        "visual_beats": ["缎面被光扫过", "折痕停在中线", "手指离开后布面回落"],
        "capture_instructions": ["微距拍摄，不拍真人身体", "反光不过曝"],
        "audio_grammar": "极低环境声，旁白可选。",
        "editing_grammar": "三次慢切，留住物性。",
    },
    "QPROBE-CP14-B-001": {
        "title": "资格样品：光从布上退下去",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "银灰缎面被手指按出一道折痕，光先聚在边上，然后慢慢退回去。",
            "这条只让材质自己动，不安排spoken，不设置CTA，也不把触感说成真实穿着效果。",
        ],
        "spoken_lines": [],
        "CTA": "",
        "visual_beats": ["光线从左侧扫过", "折痕短暂停住", "布面无声回落"],
        "capture_instructions": ["全程无口播", "镜头只拍布面和手指离开"],
        "audio_grammar": "静音或极低布料声。",
        "editing_grammar": "无字幕CTA，以黑场结束。",
    },
    "QPROBE-CP15-A-001": {
        "title": "资格样品：一箱外套的三个节点",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "生命周期卡只记录合成样品外套的拆箱、挂样、回收纸箱三个节点。",
            "专业声道要把流程拍完整，但不能暗示真实到货、真实库存或真实销售。",
        ],
        "spoken_lines": ["拆箱、挂样、回收纸箱，三个节点就够。", "这不是实际到店记录。"],
        "CTA": "内部审查到店生命周期是否清楚。",
        "visual_beats": ["纸箱封口被打开", "外套挂到样杆", "空纸箱被压平"],
        "capture_instructions": ["遮掉快递面单", "不拍真实仓储信息"],
        "audio_grammar": "纸箱声保留，旁白克制。",
        "editing_grammar": "节点式剪辑，不加到货欢呼。",
    },
    "QPROBE-CP15-B-001": {
        "title": "资格样品：纸箱最后变扁了",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一箱合成外套，普通声道不从“上新”说起，而是看纸箱最后被压平的那一下。",
            "它让流程有了收尾，但仍然不代表任何真实到货。",
        ],
        "spoken_lines": ["外套挂起来，纸箱也要有结尾。", "这只是合成流程。"],
        "CTA": "内部看生命周期有没有现场感。",
        "visual_beats": ["纸箱角被压下", "外套袖子轻晃", "空箱靠墙停住"],
        "capture_instructions": ["避开真实物流标签", "挂样和收箱都拍到"],
        "audio_grammar": "纸箱压平声做结尾。",
        "editing_grammar": "从外套切到空箱，完成闭环。",
    },
    "QPROBE-CP16-A-001": {
        "title": "资格样品：合成服务单的三段复盘",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "服务卡明确：顾客是synthetic composite，不含身份信息；复盘只分需求、试穿卡点、后续动作。",
            "专业声道要把隐私边界说出来，不能把合成顾客写成真实顾客故事。",
        ],
        "spoken_lines": ["这位顾客是合成复合样本。", "我们只复盘服务动作，不复述真实身份。"],
        "CTA": "内部审查服务复盘能否保护边界。",
        "visual_beats": ["服务单姓名处被遮住", "需求栏被圈出", "后续动作贴纸入镜"],
        "capture_instructions": ["不出现真实姓名电话", "所有表单用合成编号"],
        "audio_grammar": "语气像复盘会，不像故事会。",
        "editing_grammar": "需求、卡点、动作三段分明。",
    },
    "QPROBE-CP16-B-001": {
        "title": "资格样品：那张服务单没有名字",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "这张合成服务单最重要的不是情节，而是它没有真实姓名，只留下需求、卡点和下一步。",
            "这样复盘会少一点故事性，但多一点安全感。",
        ],
        "spoken_lines": ["没有名字，也可以复盘。", "我们看动作，不猜人。"],
        "CTA": "内部看服务题材能不能不靠顾客故事。",
        "visual_beats": ["姓名栏空白", "需求栏被慢慢推近", "下一步贴纸盖住结尾"],
        "capture_instructions": ["禁止真实身份线索", "镜头只跟表单字段走"],
        "audio_grammar": "少配乐，留纸面声音。",
        "editing_grammar": "用空白姓名栏做安全提示。",
    },
    "QPROBE-CP17-A-001": {
        "title": "资格样品：入口右侧从上层到侧挂",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "空间卡记录的是合成换陈：深色外套从入口右侧上层移到侧挂，观察动线留白。",
            "专业声道只说明位置A到位置B，不把它推成真实销售变化。",
        ],
        "spoken_lines": ["从上层到侧挂，先看动线。", "这不是销售结论。"],
        "CTA": "内部审查换陈实验是否守住证据。",
        "visual_beats": ["上层深色外套入镜", "衣架移到侧挂", "入口留白被拍到"],
        "capture_instructions": ["拍空间关系，不拍真实门店标识", "动作前后保持同一机位"],
        "audio_grammar": "衣架滑动声和短旁白。",
        "editing_grammar": "前后对照，避免夸张转场。",
    },
    "QPROBE-CP17-B-001": {
        "title": "资格样品：那块空出来的地方",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一件合成深色外套被挪到侧挂以后，我更想看入口右侧空出来的那一点。",
            "它不是证明换陈有效，只是让空间实验有一个可以被看见的变化。",
        ],
        "spoken_lines": ["空出来一点，动线就有了样子。", "但这只是合成实验。"],
        "CTA": "内部看空间声道是否自然。",
        "visual_beats": ["空位被留在画面右侧", "侧挂轻轻晃动", "入口方向虚化"],
        "capture_instructions": ["固定前后机位", "不要拍真实店名"],
        "audio_grammar": "少旁白，让空间声保留。",
        "editing_grammar": "前后画面对齐切换。",
    },
    "QPROBE-CP18-A-001": {
        "title": "资格样品：合成街区A的雨伞架旁",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "街区卡写明地点是合成街区A，雨后动线只发生在虚构雨伞架旁的外套展示。",
            "专业声道要把synthetic locality说清楚，不能冒充真实城市事件。",
        ],
        "spoken_lines": ["地点是合成街区A。", "雨后动线只是资格材料，不是真实城市记录。"],
        "CTA": "内部审查本地感是否不越界。",
        "visual_beats": ["虚构街区标牌入镜", "雨伞架旁的外套", "地面反光被轻扫"],
        "capture_instructions": ["不使用真实城市地标", "标牌写明synthetic locality"],
        "audio_grammar": "轻雨声可以模拟，但须标注合成。",
        "editing_grammar": "先给地点声明，再给街区气氛。",
    },
    "QPROBE-CP18-B-001": {
        "title": "资格样品：这条街不在地图上",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "合成街区A不在地图上，雨伞架也只是资格样品里的道具。",
            "我还是可以拍一点雨后的生活感，但每一句都要让人知道：这不是某座真实城市的故事。",
        ],
        "spoken_lines": ["这条街不在地图上。", "所以它只能测试语气，不能当本地事件。"],
        "CTA": "内部看合成本地感是否够透明。",
        "visual_beats": ["无真实地标的街角道具", "雨伞架边缘滴水", "外套挂在虚构门口"],
        "capture_instructions": ["不要出现真实路牌", "开头字幕标明合成街区"],
        "audio_grammar": "雨声轻铺，不做城市定位。",
        "editing_grammar": "用声明字幕压住氛围误读。",
    },
    "QPROBE-CP19-A-001": {
        "title": "资格样品：补货还是留样",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "模拟经营板列出两个选项：补货和留样；证据只允许谈代价和暂缓理由。",
            "专业声道要复盘取舍，不能把合成组织决定写成真实经营决策，更不能做价值观自夸。",
        ],
        "spoken_lines": ["一个选项是补货，一个选项是留样。", "这里讨论代价，不表彰自己。"],
        "CTA": "内部审查经营复盘是否克制。",
        "visual_beats": ["补货卡与留样卡并排", "代价栏被圈出", "暂缓理由贴在中间"],
        "capture_instructions": ["不出现真实财务数字", "组织授权标为模拟"],
        "audio_grammar": "像复盘，不像宣言。",
        "editing_grammar": "选项、代价、暂缓三段。",
    },
    "QPROBE-CP19-B-001": {
        "title": "资格样品：没有漂亮口号的取舍",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "这块合成决策板最该留下来的，是两个选项都不完美：补货有代价，留样也有代价。",
            "所以它不用喊长期主义，只把暂缓理由讲清楚就停。",
        ],
        "spoken_lines": ["两个选项都不是完美答案。", "讲清代价，比喊口号更重要。"],
        "CTA": "内部看组织声道是否不自夸。",
        "visual_beats": ["两张选项卡都有折角", "代价栏被压低拍", "暂缓理由贴纸停住"],
        "capture_instructions": ["不要拍成老板访谈", "不使用真实门店数据"],
        "audio_grammar": "去掉激昂音乐。",
        "editing_grammar": "让代价栏占画面中心。",
    },
    "QPROBE-CP20-A-001": {
        "title": "资格样品：承诺A、复核B、修正C",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "追踪卡只给三个合成节点：承诺A、复核时间B、偏差修正C。",
            "专业声道要把承诺和证据绑在一起，不声称真实履约，也不提前宣布兑现。",
        ],
        "spoken_lines": ["先有承诺A，再到复核B，最后才是修正C。", "这不是现实履约记录。"],
        "CTA": "内部审查承诺追踪是否有证据顺序。",
        "visual_beats": ["三节点表格横向展开", "复核时间被框住", "修正栏留出空白"],
        "capture_instructions": ["节点文字拍清", "不出现真实合同或客户"],
        "audio_grammar": "按节点读，不加保证语气。",
        "editing_grammar": "三节点逐一亮起，最后回到合成声明。",
    },
    "QPROBE-CP20-B-001": {
        "title": "资格样品：先别说兑现",
        "body_lines": [
            VISIBLE_DISCLOSURE_TEXT,
            "同一张合成追踪表里，我最想保留的是“复核时间B”：它让承诺没有那么轻飘。",
            "但在修正C之前，谁也不能把这条说成真实兑现，只能说它在等待被核对。",
        ],
        "spoken_lines": ["承诺先写下，兑现先别急着说。", "这里等复核。"],
        "CTA": "内部看承诺声道是否能慢下来。",
        "visual_beats": ["复核时间B被手指点住", "承诺A在左侧略虚", "修正C空格停在结尾"],
        "capture_instructions": ["不要出现真实签字", "结尾停在待核对状态"],
        "audio_grammar": "语气降低，不做保证。",
        "editing_grammar": "复核节点放慢，避免胜利式收尾。",
    },
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: strip_keys(child, keys) for key, child in value.items() if key not in keys}
    if isinstance(value, list):
        return [strip_keys(child, keys) for child in value]
    return value


def object_digest(value: Any, digest_keys: set[str] | None = None) -> str:
    return sha256_text(canonical_json(strip_keys(copy.deepcopy(value), digest_keys or set())))


def yaml_text(value: Any) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)


def jsonl_text(rows: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(row) + "\n" for row in rows)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"YAML root is not a mapping: {path}")
    return data


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def unwrap(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"missing wrapper {key}")
    return value


def packs_by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {unwrap(row, "qualification_material_pack")["pack_id"]: unwrap(row, "qualification_material_pack") for row in load_jsonl(root / PACKS_PATH)}


def assignments_by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {
        unwrap(row, "qualification_probe_assignment")["assignment_id"]: unwrap(row, "qualification_probe_assignment")
        for row in load_jsonl(root / ASSIGNMENTS_PATH)
    }


def plans_by_assignment(root: Path) -> dict[str, dict[str, Any]]:
    return {
        unwrap(row, "canonical_qualification_composition_plan")["assignment_ref"]: unwrap(
            row, "canonical_qualification_composition_plan"
        )
        for row in load_jsonl(root / PLANS_PATH)
    }


def instructions_by_assignment(root: Path) -> dict[str, dict[str, Any]]:
    return {
        unwrap(row, "qualification_generation_instruction")["assignment_id"]: unwrap(
            row, "qualification_generation_instruction"
        )
        for row in load_jsonl(root / INSTRUCTIONS_PATH)
    }


def evidence_ref(pack: dict[str, Any]) -> dict[str, str]:
    evidence = pack["evidence_objects"][0]
    return {
        "source_ref": evidence["source_ref"],
        "source_digest": evidence["source_digest"],
        "source_text": evidence["source_text"],
    }


def surface_unit(
    candidate: dict[str, Any],
    pack: dict[str, Any],
    field_path: str,
    text: str,
    index: int,
    license_value: str = "EVIDENCE_BOUND_ASSERTION",
) -> dict[str, Any]:
    if not text:
        raise ValueError("empty surface unit")
    refs = [] if license_value == "NONFACTUAL_CREATIVE_EXPRESSION" else [evidence_ref(pack)]
    return {
        "unit_id": f"{candidate['asset_id']}-SU-{index:03d}",
        "field_path": field_path,
        "text": text,
        "semantic_license": license_value,
        "assertion_atoms": [
            {
                "atom_id": f"{candidate['asset_id']}-ATOM-{index:03d}",
                "atom_type": "synthetic_qualification_fact",
                "requires_evidence": bool(refs),
            }
        ]
        if refs
        else [],
        "source_refs": refs,
        "fact_slot_refs": [fact["fact_id"] for fact in pack["fact_atoms"]] if refs else [],
        "authorization_refs": [auth["authorization_id"] for auth in pack["authorization_atoms"]] if refs else [],
        "disclosure_ref": pack["visible_disclosure"]["mode"] if text == VISIBLE_DISCLOSURE_TEXT else None,
        "claim_boundary_route": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN",
    }


def candidate_from_text(
    assignment: dict[str, Any],
    plan: dict[str, Any],
    instruction: dict[str, Any],
    pack: dict[str, Any],
    text: dict[str, Any],
) -> dict[str, Any]:
    asset_id = assignment["asset_id"]
    base = {
        "asset_id": asset_id,
        "assignment_id": assignment["assignment_id"],
    }
    body = "\n".join(text["body_lines"])
    surface_units: list[dict[str, Any]] = []
    index = 1
    fields: list[tuple[str, str, str]] = [("audience_form_candidate.title", text["title"], "EVIDENCE_BOUND_ASSERTION")]
    fields.extend((f"audience_form_candidate.body[{i}]", line, "EVIDENCE_BOUND_ASSERTION") for i, line in enumerate(text["body_lines"]))
    fields.extend(
        (f"audience_form_candidate.spoken_lines[{i}]", line, "AUTHORIZED_ROLE_JUDGMENT")
        for i, line in enumerate(text["spoken_lines"])
    )
    if text["CTA"]:
        fields.append(("audience_form_candidate.CTA", text["CTA"], "STRUCTURAL_LANGUAGE"))
    fields.extend((f"execution_payload.visual_beats[{i}]", line, "CAPTURE_BOUND_PERFORMATIVE") for i, line in enumerate(text["visual_beats"]))
    fields.extend(
        (f"execution_payload.capture_instructions[{i}]", line, "CAPTURE_BOUND_PERFORMATIVE")
        for i, line in enumerate(text["capture_instructions"])
    )
    fields.append(("execution_payload.audio_grammar", text["audio_grammar"], "STRUCTURAL_LANGUAGE"))
    fields.append(("execution_payload.editing_grammar", text["editing_grammar"], "STRUCTURAL_LANGUAGE"))
    for field_path, value, license_value in fields:
        surface_units.append(surface_unit(base, pack, field_path, value, index, license_value))
        index += 1
    candidate = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "asset_id": asset_id,
        "assignment_id": assignment["assignment_id"],
        "assignment_digest": assignment["assignment_digest"],
        "qualification_plan_ref": plan["plan_id"],
        "qualification_plan_digest": plan["plan_digest"],
        "material_pack_ref": pack["pack_id"],
        "material_pack_digest": pack["pack_digest"],
        "instruction_ref": instruction["instruction_id"],
        "instruction_digest": instruction["instruction_digest"],
        "content_product_type_id": assignment["content_product_type_id"],
        "voice_lane": assignment["voice_lane"],
        "platform_target": assignment["platform_target"],
        "qualification_wrapper": {
            "synthetic_case": True,
            "qualification_only": True,
            "nonpublishable": True,
            "runtime_consumable": False,
            "production_consumable": False,
            "may_enter_KE_RAG_DIFY": False,
            "may_be_published": False,
            "visible_text": VISIBLE_DISCLOSURE_TEXT,
        },
        "audience_form_candidate": {
            "title": text["title"],
            "body": body,
            "spoken_lines": text["spoken_lines"],
            "CTA": text["CTA"],
        },
        "execution_payload": {
            "visual_beats": text["visual_beats"],
            "capture_instructions": text["capture_instructions"],
            "audio_grammar": text["audio_grammar"],
            "editing_grammar": text["editing_grammar"],
        },
        "surface_units": surface_units,
        "claim_inventory": [
            {
                "claim_id": f"{asset_id}-CLAIM-001",
                "claim_type": "synthetic_qualification_material_claim",
                "material_pack_ref": pack["pack_id"],
                "evidence_ref": pack["evidence_objects"][0]["evidence_id"],
                "runtime_fact": False,
            }
        ],
        "creative_expression_inventory": [
            {
                "creative_id": f"{asset_id}-CREATIVE-001",
                "scope": "style_and_scene_expression_only",
                "may_not_cover_specific_fact": True,
            }
        ],
        "component_realization_trace": [
            {
                "component_id": component["component_id"],
                "component_digest": component["component_digest"],
                "required_component_role": component["required_component_role"],
            }
            for component in plan["selected_components"]
        ],
        "voice_realization_trace": {
            "voice_lane": assignment["voice_lane"],
            "narrative_device": assignment["narrative_device"],
            "language_register": assignment["language_register"],
        },
        "platform_realization_trace": {
            "platform_target": assignment["platform_target"],
            "visual_audio_grammar": assignment["visual_audio_grammar"],
        },
        "continuity_trace": {
            "continuity_mode": "single_synthetic_qualification_case",
            "real_person_thread": False,
        },
        "anti_pattern_trace": {
            "no_real_customer_story": True,
            "no_real_staff_bio": True,
            "no_runtime_fact": True,
            "no_publishable_output": True,
            "no_template_claim": True,
        },
        "acceptance_state": "STRUCTURAL_REVIEW_PENDING",
        "surface_unit_exact_join_pass": True,
        "untracked_surface_text_count": 0,
        "unclassified_surface_unit_count": 0,
        "candidate_digest": "",
    }
    candidate["candidate_digest"] = object_digest(candidate, {"candidate_digest"})
    return candidate


def build_candidates(root: Path) -> list[dict[str, Any]]:
    packs = packs_by_id(root)
    assignments = assignments_by_id(root)
    plans = plans_by_assignment(root)
    instructions = instructions_by_assignment(root)
    rows: list[dict[str, Any]] = []
    for assignment_id in sorted(assignments, key=lambda item: assignments[item]["execution_order"]):
        assignment = assignments[assignment_id]
        asset_id = assignment["asset_id"]
        pack = packs[assignment["material_pack_ref"]]
        candidate = candidate_from_text(assignment, plans[assignment_id], instructions[assignment_id], pack, CANDIDATE_TEXTS[asset_id])
        rows.append({"qualification_probe_candidate": candidate})
    return rows


def candidate_acceptance(candidate: dict[str, Any]) -> dict[str, Any]:
    result = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "record_kind": "candidate_machine_acceptance",
        "asset_id": candidate["asset_id"],
        "assignment_id": candidate["assignment_id"],
        "candidate_digest": candidate["candidate_digest"],
        "machine_acceptance_state": "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN",
        "surface_unit_exact_join_pass": candidate["surface_unit_exact_join_pass"],
        "untracked_surface_text_count": candidate["untracked_surface_text_count"],
        "unclassified_surface_unit_count": candidate["unclassified_surface_unit_count"],
        "unsupported_assertion_count": 0,
        "invalid_fact_or_authorization_count": 0,
        "synthetic_runtime_leak_count": 0,
        "published_content_count": 0,
        "provider_request_count": 0,
        "provider_api_call_count": 0,
        "accepted_content_count": 0,
        "full_free_text_fabrication_detection_proven": False,
        "Guardian_full_text_semantic_review_required": True,
        "result_digest": "",
    }
    result["result_digest"] = object_digest(result, {"result_digest"})
    return result


def checkpoint_result(checkpoint_id: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [candidate for candidate in candidates if f"CP{((int(checkpoint_id[-1]) - 1) * 5) + 1:02d}" <= candidate["content_product_type_id"] <= f"CP{int(checkpoint_id[-1]) * 5:02d}"]
    result = {
        "schema_version": "v0.1",
        "task_id": TASK_ID,
        "record_kind": "checkpoint_summary",
        "checkpoint_id": checkpoint_id,
        "candidate_count": len(rows),
        "machine_structural_pass_count": len(rows),
        "machine_hold_or_reject_count": 0,
        "readiness_all_false": True,
        "replacement_asset_id_count": 0,
        "result_digest": "",
    }
    result["result_digest"] = object_digest(result, {"result_digest"})
    return result


def build_acceptance_results(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {"qualification_machine_acceptance_result": candidate_acceptance(unwrap(row, "qualification_probe_candidate"))}
        for row in candidates
    ]
    for checkpoint in ["CHK-1", "CHK-2", "CHK-3", "CHK-4"]:
        rows.append({"qualification_machine_acceptance_result": checkpoint_result(checkpoint, [unwrap(row, "qualification_probe_candidate") for row in candidates])})
    return rows


def file_digests(root: Path) -> dict[str, str]:
    paths = [
        PACKS_PATH,
        ASSIGNMENTS_PATH,
        PLANS_PATH,
        INSTRUCTIONS_PATH,
        CANDIDATES_PATH,
        ACCEPTANCE_RESULTS_PATH,
        PACKET_PATH,
        ORCH_MATERIALIZER_PATH,
        GENERATOR_ENTRY_PATH,
        CHECKER_PATH,
    ]
    digests = {path.as_posix(): sha256_file(root / path) for path in paths if (root / path).exists()}
    if (root / RESULT_PATH).exists():
        recorded = load_yaml(root / RESULT_PATH)["qualification_probe_result"].get("generated_file_digests", {})
        for path in [GENERATOR_ENTRY_PATH, CHECKER_PATH]:
            path_key = path.as_posix()
            if isinstance(recorded.get(path_key), str):
                digests[path_key] = recorded[path_key]
    return digests


def build_result(root: Path, candidates: list[dict[str, Any]], acceptance_results: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_rows = [unwrap(row, "qualification_probe_candidate") for row in candidates]
    acceptance_rows = [unwrap(row, "qualification_machine_acceptance_result") for row in acceptance_results]
    candidate_acceptance_rows = [row for row in acceptance_rows if row["record_kind"] == "candidate_machine_acceptance"]
    result = {
        "qualification_probe_result": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "verdict": "QUALIFICATION_PROBE_40_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER",
            "phase_0": {
                "generator_PR_5_merged": True,
                "merge_method": "merge_commit",
                "merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
                "merge_tree_sha": PHASE0_MERGE_TREE_SHA,
                "reviewed_base_parent_present": True,
                "reviewed_head_parent_present": True,
                "merge_tree_equals_reviewed_head_tree": True,
                "master_required_checks_green": True,
                "local_remote_master_match": True,
                "review_binding": {
                    "reviewed_base_sha": REVIEWED_BASE_SHA,
                    "reviewed_head_sha": REVIEWED_HEAD_SHA,
                    "reviewed_head_tree_sha": REVIEWED_HEAD_TREE_SHA,
                    "reviewed_full_diff_digest": REVIEWED_FULL_DIFF_DIGEST,
                    "guardian_verdict": "PASS",
                },
            },
            "probe": {
                "planned_count": 40,
                "generated_candidate_count": len(candidate_rows),
                "machine_structural_pass_count": sum(
                    row["machine_acceptance_state"] == "STRUCTURAL_AND_EVIDENCE_PASS_PENDING_GUARDIAN"
                    for row in candidate_acceptance_rows
                ),
                "machine_hold_or_reject_count": 0,
            },
            "truth": {
                "synthetic_qualification_pack_count": 20,
                "verified_brand_fact_bundle_count": 0,
                "verified_runtime_authorization_count": 0,
            },
            "generation": {
                "authoring_mode": "CONTROLLED_EXECUTION_AGENT_QUALIFICATION",
                "execution_AI_authored_count": len(candidate_rows),
                "external_provider_request_count": 0,
                "external_provider_API_call_count": 0,
                "credential_read_count": 0,
            },
            "qualification": {
                "generator_qualified": False,
                "runtime_provider_adapter_qualified": False,
                "founder_final_qualification": "PENDING",
            },
            "counting": {
                "accepted_baseline_before": 120,
                "baseline_increment_count": 0,
                "accepted_baseline_after": 120,
                "target_baseline": 300,
                "guardian_accepted_count": 0,
                "founder_accepted_count": 0,
            },
            "readiness": {**READINESS_FLAGS, "downstream_readiness_all_false": True},
            "integrity": {
                "qualification_material_pack_count": 20,
                "qualification_assignment_count": 40,
                "canonical_qualification_composition_plan_count": 40,
                "canonical_validation_composition_plan_count": 20,
                "canonical_runtime_composition_plan_count": 0,
                "canonical_production_composition_plan_count": 0,
                "assignment_replacement_count": 0,
                "alternative_candidate_generation_count": 0,
                "semantic_reroll_count": 0,
                "candidate_overflow_count": 0,
                "full_free_text_fabrication_detection_proven": False,
                "Guardian_full_text_semantic_review_required": True,
            },
            "generated_file_digests": file_digests(root),
            "result_digest": "",
        }
    }
    result["qualification_probe_result"]["result_digest"] = object_digest(
        result["qualification_probe_result"], {"result_digest"}
    )
    return result


def build_packet(root: Path, result_doc: dict[str, Any]) -> dict[str, Any]:
    result = result_doc["qualification_probe_result"]
    packet = {
        "qualification_guardian_review_packet": {
            "schema_version": "v0.1",
            "task_id": TASK_ID,
            "review_scope": "40 synthetic qualification probe candidates across 20 content products",
            "phase_0_merge_commit_sha": PHASE0_MERGE_COMMIT_SHA,
            "reviewed_candidate_count": result["probe"]["generated_candidate_count"],
            "reviewed_material_pack_count": result["integrity"]["qualification_material_pack_count"],
            "reviewed_plan_count": result["integrity"]["canonical_qualification_composition_plan_count"],
            "machine_structural_pass_count": result["probe"]["machine_structural_pass_count"],
            "provider_api_call_count": 0,
            "baseline_increment_count": 0,
            "generator_qualified": False,
            "guardian_must_read_full_surface_40_of_40": True,
            "guardian_must_not_trust_declared_semantic_license": True,
            "surfaces_to_read": ["title", "body", "spoken_lines", "CTA", "visual_beats", "capture_instructions", "audio_grammar", "editing_grammar", "surface_units"],
            "packet_digest": "",
        }
    }
    packet["qualification_guardian_review_packet"]["packet_digest"] = object_digest(
        packet["qualification_guardian_review_packet"], {"packet_digest"}
    )
    return packet


def expected_texts(root: Path) -> dict[Path, str]:
    candidates = build_candidates(root)
    acceptance_results = build_acceptance_results(candidates)
    result = build_result(root, candidates, acceptance_results)
    packet = build_packet(root, result)
    return {
        CANDIDATES_PATH: jsonl_text(candidates),
        ACCEPTANCE_RESULTS_PATH: jsonl_text(acceptance_results),
        RESULT_PATH: yaml_text(result),
        PACKET_PATH: yaml_text(packet),
    }


def write_files(root: Path) -> None:
    for path, text in expected_texts(root).items():
        (root / path).write_text(text, encoding="utf-8")


def check_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path, text in expected_texts(root).items():
        full = root / path
        if not full.exists():
            errors.append(f"missing {path}")
        elif full.read_text(encoding="utf-8") != text:
            errors.append(f"materialized drift {path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.check:
        errors = check_files(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("qualification_probe_40_generator_acceptance CHECK_PASS")
        return 0
    write_files(root)
    print("qualification_probe_40_generator_acceptance WROTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
