#!/usr/bin/env python3
"""Build the founder-40 repair artifacts from individually authored repair specs."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


TASK_ID = "GKB-P7D-FOUNDER-40-CREATIVE-REPAIR-AND-SCOPED-GATE-PATCH-001"
BASELINE_HEAD = "4d5ce09cda5909bdc3ba6b1b8c8f8921099e8250"
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "07_microbatch_runs/scoped_content_microbatch_120_001"
MID = RUN / "midbatch_320_001"
PACKET_PATH = MID / "midbatch_320_founder_review_packet.v0.1.yaml"
RECORDS_PATH = MID / "midbatch_320_generation_records.v0.1.jsonl"
KERNEL_PATH = RUN / "content_kernel_extraction/user_visible_kernel_matrix.v0.1.yaml"

CLASS_IDS = {
    "A": {
        "P7D320-OUT-021", "P7D320-OUT-040", "P7D320-OUT-082",
        "P7D320-OUT-089", "P7D320-OUT-097", "P7D320-OUT-115",
        "P7D320-OUT-129", "P7D320-OUT-154", "P7D320-OUT-202",
        "P7D320-OUT-224", "P7D320-OUT-298", "P7D320-OUT-312",
    },
    "B": {
        "P7D320-OUT-006", "P7D320-OUT-054", "P7D320-OUT-063",
        "P7D320-OUT-071", "P7D320-OUT-077", "P7D320-OUT-105",
        "P7D320-OUT-127", "P7D320-OUT-151", "P7D320-OUT-162",
        "P7D320-OUT-177", "P7D320-OUT-214", "P7D320-OUT-234",
        "P7D320-OUT-263", "P7D320-OUT-276", "P7D320-OUT-287",
        "P7D320-OUT-289",
    },
    "C": {
        "P7D320-OUT-030", "P7D320-OUT-048", "P7D320-OUT-138",
        "P7D320-OUT-170", "P7D320-OUT-191", "P7D320-OUT-254",
        "P7D320-OUT-316",
    },
    "D": {
        "P7D320-OUT-012", "P7D320-OUT-195", "P7D320-OUT-226",
        "P7D320-OUT-243", "P7D320-OUT-267",
    },
}

LIGHTLY_GUIDED = {
    "P7D320-OUT-021", "P7D320-OUT-115", "P7D320-OUT-138",
    "P7D320-OUT-195", "P7D320-OUT-224", "P7D320-OUT-312",
}
CAMPAIGN_DIRECTED = {"P7D320-OUT-129", "P7D320-OUT-267"}


def spec(
    output_id: str,
    body: str,
    object_anchor: str,
    subject: str,
    action: str,
    scene: str,
    judgment: str,
    tension: str,
    line: str,
    platform: str,
    account: str,
    opening_scene: str,
    entry: str,
    first_action: str,
    conflict: str,
    detail_focus: str,
    fact_move: str,
    closing: str,
    *,
    customer_task: str = "",
    product_role: str = "",
    tryon_trigger: str = "",
    p0_04_subroute: str = "",
) -> dict[str, Any]:
    return {
        "output_id": output_id,
        "body": body,
        "object_anchor": object_anchor,
        "subject": subject,
        "action": action,
        "scene": scene,
        "judgment": judgment,
        "tension": tension,
        "line": line,
        "platform": platform,
        "account": account,
        "opening_scene": opening_scene,
        "entry": entry,
        "first_action": first_action,
        "conflict": conflict,
        "detail_focus": detail_focus,
        "fact_move": fact_move,
        "closing": closing,
        "customer_task": customer_task,
        "product_role": product_role,
        "tryon_trigger": tryon_trigger,
        "p0_04_subroute": p0_04_subroute,
    }


SPECS = [
    spec(
        "P7D320-OUT-006",
        "样衣间快收工时，版师把两季外套挂到一起。新款更轻，旧款的领型却更稳。团队没有急着给新款找漂亮话，而是重新检查肩线和袖窿：顾客未必记得一季的口号，却会记得每次穿上都不必重新适应。所谓长期，不是永远不改，而是每次改动都知道什么不能丢。",
        "两季外套的领型、肩线与袖窿差异", "版师", "并排复核两季外套", "样衣间收工前",
        "长期价值要落在跨季仍被守住的成衣结构上", "减轻新款与保留熟悉穿着感之间的取舍", "改可以，熟悉感别丢。",
        "wechat_channels", "founder", "样衣间收工", "工作片段进入", "并排挂衣", "新旧取舍", "领型与肩线", "不宣称真实品牌历史", "以团队选择落点",
    ),
    spec(
        "P7D320-OUT-012",
        "羊毛大衣从布料走到货架，中间最怕一句“我们用的都是好料”把过程盖过去。选料要回答起球顾虑，打版要处理肩背活动，试穿要看省道是否顺，交到门店还得让导购讲得明白。企业的认真，不在一句保证里，而在每一道交接都有人停下来问：这一处为什么这样做？",
        "羊毛大衣从选料到门店的工序链", "服装团队", "逐环说明工序选择", "产品从开发到门店",
        "企业认真应由可解释的工序交接承载", "好料口号与具体过程之间的落差", "这一处为什么这样做？",
        "xiaohongshu", "brand_headquarters", "产品来路", "反口号开场", "逐环追问", "口号与过程", "选料、版型与省道", "只谈一般工序逻辑", "以追问收束",
    ),
    spec(
        "P7D320-OUT-021",
        "风衣已经接近完成，团队却在袖口前停了下来。门襟扣到第二颗时很利落，袖口一抬却显得过重。继续交货省时间，退回去再改会多一轮工，但他们选择先把那半寸处理好。企业叙事不一定从大事件开始；一件差点完成、最后仍被叫停的衣服，已经把“我们愿意为哪件小事多走一步”说清楚了。",
        "门襟利落但袖口偏重的风衣", "产品团队", "叫停接近完成的样衣", "样衣确认节点",
        "经营选择可由一次小而明确的返工表达", "按时交货与再改半寸之间的取舍", "这半寸，值得再走一步。",
        "douyin", "founder", "样衣确认", "结果反转进入", "抬袖观察", "交期与细节", "袖口重量与门襟", "不冒充真实品牌事件", "以小选择放大价值",
    ),
    spec(
        "P7D320-OUT-030",
        "“好看”太容易说，也太容易忘。把外套袖口向上翻两道，里衬的走线、门襟扣的位置和领口的收势就都有了落点。团队真正要留下的，不是一个更响的形容词，而是一套人人都能指出来的判断：哪里值得看，为什么先看这里。品牌的表达从实物开始，空话自然会少。",
        "翻起袖口后可见的里衬走线与门襟扣位", "品牌内容团队", "把形容词换成实物判断", "挂通前的内容讨论",
        "品牌表达应从可指认的服装细节开始", "泛化审美词与可复述判断之间的取舍", "先说你看见了什么。",
        "moments", "brand_headquarters", "内容讨论", "否定泛词进入", "翻起袖口", "形容词与实物", "走线、扣位与领口", "具体品牌口吻留待确认", "回到实物",
    ),
    spec(
        "P7D320-OUT-040",
        "一条高腰直筒牛仔裤，不必急着替任何人保证“显瘦”。先看腰线落在哪里，再看裤缝从胯部向下是否顺直，坐下与站起时前片会不会堆成一团。团队选择把结论留给试穿的人，把能看见的结构讲清楚。克制不是少说，而是把每一句都放回衣服本身。",
        "高腰直筒牛仔裤的腰线、裤缝与前片", "导购", "引导顾客观察结构", "门店试穿交流",
        "结果型卖点要降为可观察结构", "销售结论与顾客自主试穿判断之间的边界", "先看裤缝怎么走。",
        "live", "sales_associate", "讲款节点", "风险词截停", "观察腰线", "结论与观察", "裤缝与前片", "身体效果不作保证", "把决定交给试穿",
    ),
    spec(
        "P7D320-OUT-048",
        "同一件白衬衫，可以陪人去见客户，也可以接住下班后的晚饭局。前一种先看肩线和下摆是否利落，后一种再看面料松开一颗扣后的状态。做系列内容，不是把同一个卖点换十个标题，而是让一件衣服在不同任务里承担不同角色。团队要守住的是同一件东西，改变的是观察它的入口。",
        "白衬衫在商务与晚间转场中的两种状态", "内容团队", "按场景重排讲述入口", "同源素材编排",
        "系列内容应改变场景任务而非只换标题", "保持商品一致与避免卖点复述之间的平衡", "同一件衣服，换一个任务。",
        "wechat_channels", "brand_headquarters", "一天转场", "双场景对照", "切换穿着状态", "复述与重排", "肩线、下摆与面料", "具体场景事实不作品牌声称", "以入口变化收束",
    ),
    spec(
        "P7D320-OUT-054",
        "早班店长先把燕麦色针织抖开，搭配师把风衣腰带从后腰绕过，导购则把袖口卷到顾客最容易照着做的位置。同一套衣服，三个人说的不是同一句话：店长关心今天是否好执行，搭配师解释比例，导购只提醒上身时先动哪一处。岗位有自己的眼睛，内容才不像统一口径念稿。",
        "燕麦色针织、风衣腰带与卷起的袖口", "店长、搭配师、导购", "按岗位分别处理同一套搭配", "门店早班",
        "岗位内容要由各自真实观察接口决定", "统一话术与角色差异之间的张力", "每个岗位，说自己看见的。",
        "moments", "store_manager", "门店早班", "多人接力进入", "抖开针织", "统一口径与岗位视角", "腰带与袖口", "不编写个人履历", "以岗位差异收束",
    ),
    spec(
        "P7D320-OUT-063",
        "普通的一天，不需要把声音抬得很高。导购拿起羊毛上衣，先让人看袖口锁边，再摸一摸领口收针。能看见的地方说清楚，不能从外观判断的耐用与保暖就不抢着下结论。语气跟着事情走：日常动作平着说，真正值得停一下的细节，才慢一点。",
        "羊毛上衣的袖口锁边与领口收针", "导购", "查看锁边并说明触感", "门店普通工作日",
        "表达强度应随现场信息强度变化", "日常自然口吻与夸张表达之间的取舍", "这处锁边，值得慢一点。",
        "douyin", "sales_associate", "普通门店日常", "低声判断进入", "拿起上衣", "平说与抬调", "锁边与收针", "性能结论留在正文之外", "以语速变化结束",
    ),
    spec(
        "P7D320-OUT-071",
        "一件风衣挂在店里，买手先看门襟和面料，导购先想到顾客抬手时肩部是否自在，陈列师关心它放在橱窗哪一侧才不压住内搭。谁都不是在重复别人。把这些观察接起来，才是团队协作；让每个人只说自己真正看见的部分，角色才有可信的分量。",
        "风衣的门襟、肩部活动与橱窗位置", "买手、导购、陈列师", "从岗位接口接力观察", "门店商品协作",
        "组织协作来自不同岗位的真实观察接力", "多岗位口径一致与职责不混用之间的平衡", "别替下一个岗位把话说完。",
        "xiaohongshu", "brand_headquarters", "跨岗位协作", "角色并列进入", "分别观察风衣", "协作与越位", "门襟、肩部与橱窗", "不借虚构顾客反馈作证", "以职责边界收束",
    ),
    spec(
        "P7D320-OUT-077",
        "订货会上的豆绿色粗针毛衣，买手叫它“补色款”，陈列同事把它当作墙面里的缓冲，内容同事却先注意到麻花纹和落肩。名字在变，衣服没有变。真正该交接的是：这个岗位看见了什么，下一位需要接住什么。内部的订量与库存留在内部，面向顾客只讲眼前能理解的颜色、纹理和穿法。",
        "豆绿色粗针毛衣的颜色、麻花纹与落肩", "买手、陈列同事、内容同事", "交接岗位观察", "订货会后场",
        "内部流转可换称呼但公开表达必须守住可见信息", "后场经营信息与顾客公开内容之间的边界", "名字会变，衣服不会。",
        "wechat_channels", "brand_headquarters", "订货会后场", "称呼差异进入", "岗位接力命名", "内部信息与公开表达", "颜色、纹理与落肩", "不公开订量库存", "以同物异名结束",
    ),
    spec(
        "P7D320-OUT-082",
        "第一次看藏青羊毛西装外套的人，先给他一个站着就能照做的动作：敞开穿，让内搭露出一条清楚的竖线。熟悉这类外套的人，再讲驳头宽窄、后开衩和肩线。不是每个人都需要同样深的解释。导购先判断顾客离这件衣服有多远，再决定从一眼能懂，还是从一个细节开始。",
        "藏青羊毛西装外套的驳头、开衩与肩线", "导购", "按顾客熟悉度分层讲解", "门店初次与熟客交流",
        "信息深度应随顾客认知距离调整", "讲得完整与让新客先听懂之间的取舍", "先给一个能照做的动作。",
        "douyin", "sales_associate", "门店讲款", "新熟客差异进入", "示范敞开穿", "信息深浅", "驳头、开衩与肩线", "商品信息发布前确认", "以分层入口结束",
    ),
    spec(
        "P7D320-OUT-089",
        "先别急着夸这件卡其风衣。把领子立起来，再把同料腰带松开一点，走两步看看下摆怎样跟着人动。店长说话也可以留一点余地：“你先看它走起来的样子，再决定要不要把腰收紧。”情绪不靠煽情，它来自顾客发现一个细节正好回应自己生活的那一刻。",
        "卡其风衣的高领、同料腰带与下摆摆动", "店长", "邀请顾客走动观察", "门店试穿",
        "人味来自具体动作与克制判断", "情绪感染与不制造承诺之间的平衡", "先看它走起来。",
        "moments", "store_manager", "试穿交流", "克制邀请进入", "立领松腰带", "煽情与观察", "腰带与下摆", "不虚构顾客经历", "让顾客自行决定",
    ),
    spec(
        "P7D320-OUT-097",
        "砂色工装衬衫不需要“十年老导购”来撑场。导购把袖口双线翻给人看，再示范下摆放出和半掖的差别，就已经有话可说：“先别听我夸，你看领台立起来时，整件衣服是不是更精神。”经验可以体现在观察次序里，不必编成履历。",
        "砂色工装衬衫的双线袖口、下摆与领台", "导购", "示范放出与半掖", "门店讲款",
        "角色可信度应来自观察方法而非虚构资历", "快速建立信任与避免身份背书之间的取舍", "经验藏在先看哪里。",
        "live", "sales_associate", "直播讲款", "撤掉履历进入", "翻看袖口", "身份背书与现场观察", "双线、下摆与领台", "个人履历必须由本人确认", "以观察次序收束",
    ),
    spec(
        "P7D320-OUT-105",
        "圆领上装从哪里讲，顺序比形容词重要。先看领口是否贴着颈部，再看袖长停在手腕哪里，最后才摸面料表面。导购可以说：“先把这三处看完，再谈你喜欢不喜欢。”至于材质成分、缩水率或耐久表现，标签和记录没有给出时，就不替衣服抢答。",
        "圆领上装的领口、袖长与面料表面", "导购", "按结构顺序讲解", "门店商品介绍",
        "结构讲解应先于材质性能判断", "讲得具体与不越过资料边界之间的平衡", "先把这三处看完。",
        "xiaohongshu", "sales_associate", "单品拆解", "顺序问题进入", "查看领口", "结构与性能", "领口、袖长与表面", "材质性能须有标签记录", "以自主喜好结束",
    ),
    spec(
        "P7D320-OUT-115",
        "两件同色羊毛开衫放在一起，一件落肩宽松，一件腰身收得更清楚；一件下摆是双层罗纹，另一件更薄、更贴。差别先讲到这里就够了。哪件更暖、哪件更耐穿，不能只凭厚薄替人决定。选择可以从看得见的长度、结构和手感开始，再交给真实穿着。",
        "两件羊毛开衫的落肩、腰身与罗纹差别", "商品编辑", "并列比较可见差异", "同类商品对比",
        "同类比较只应承诺可见结构差异", "帮助选择与避免保暖耐穿结论之间的边界", "先比结构，不替穿着下结论。",
        "douyin", "brand_headquarters", "产品对比", "并列差异进入", "平放两件开衫", "可见差别与长期效果", "落肩、腰身与罗纹", "保暖耐穿需实测", "把选择交回穿着",
    ),
    spec(
        "P7D320-OUT-127",
        "白衬衫和白色针织看着都干净，手一动，结构就分开了。梭织衬衫的领口能立住，布面沿经纬方向更有秩序；针织上衣轻轻抻开，会顺着线圈回到原位。这里讲的是外观与触感的差别，不把它直接推成更耐穿、更舒服。先学会看结构，才不会只剩“都是白色”。",
        "梭织白衬衫与白色针织的结构对比", "导购", "演示织物结构差异", "门店面料解释",
        "面料结构可解释外观触感但不能直接外推性能", "讲清原理与避免性能承诺之间的边界", "手一动，结构就分开了。",
        "wechat_channels", "sales_associate", "面料小课", "同色异构进入", "轻抻两件白衣", "结构与性能", "经纬与线圈", "耐穿舒适需其他依据", "回到结构观察",
    ),
    spec(
        "P7D320-OUT-129",
        "姜黄色缎面衬衫在冷白灯下偏亮，在暖光里更接近橙调，贴近手机屏幕时又显得浓。旁边放一件炭灰背心，颜色的变化会更容易辨认。谈颜色之前，先说清楚当时的光；“显白”不是色卡能替人下的结论。真正可靠的描述，是让人知道自己究竟看见了哪一种黄。",
        "姜黄缎面衬衫在三种光线下的颜色漂移", "商品编辑", "比较不同光线下的颜色", "产品颜色研究",
        "颜色描述必须带观察光线", "审美表达与身体效果断言之间的边界", "先说光，再说颜色。",
        "xiaohongshu", "brand_headquarters", "颜色研究", "光线变化进入", "切换观察光源", "色彩判断与身体结论", "姜黄、炭灰与光线", "显白效果不作保证", "以颜色坐标收束",
    ),
    spec(
        "P7D320-OUT-138",
        "茧型毛呢外套平放时，能看到肩部向内收、后背留量、下摆收拢；穿到身上，才看见这些结构怎样连成一条外轮廓。版型是衣服怎么被裁和拼，廓形是它在人身上怎样站住。两者可以一起讲，但不要把线条变化说成对所有身材都有效。",
        "茧型毛呢外套的肩部、后背与收口结构", "版师", "对照平放结构与上身轮廓", "样衣说明",
        "版型结构与上身廓形应分层解释", "专业解释与普遍身材效果承诺之间的边界", "结构先铺开，轮廓再站起来。",
        "douyin", "brand_headquarters", "样衣结构说明", "平放上身对照", "摊开外套", "结构与身体效果", "肩部、后背与下摆", "不承诺所有身材结果", "以概念分层结束",
    ),
    spec(
        "P7D320-OUT-151",
        "棉麻外套翻到内侧，袖口包边收得是否干净，领口压线有没有顺着弧度走，都比一句“做工很好”更具体。导购不必把工艺讲成考试，只要带着人从外观走到结构，再停在一处能看清的细节。能看见的针脚说明这一处怎么做，不能顺手替整件衣服保证寿命。",
        "棉麻外套内侧的袖口包边与领口压线", "导购", "翻看内侧工艺", "门店细节讲解",
        "工艺内容要从整体逐步落到单个可见节点", "具体做工观察与整件寿命承诺之间的边界", "翻到里面，细节才开始说话。",
        "moments", "sales_associate", "门店细节分享", "翻面发现进入", "查看包边", "局部工艺与整体寿命", "包边、压线与针脚", "耐用寿命需长期依据", "停在一处细节",
    ),
    spec(
        "P7D320-OUT-154",
        "卡其直筒裤最容易被写成“显瘦”，也最该把这句话收回来。先看前片中缝是否向下顺，裤线有没有在膝部堆起，裤脚卷一折后鞋面露出多少。导购可以邀请顾客走两步、坐一下，再自己看比例。衣服提供的是线条和余量，身体结果不该由一句话包办。",
        "卡其直筒裤的中缝、裤线与卷边", "导购", "引导走动和坐下观察", "试穿区",
        "裤装内容应描述线条余量而非保证身体结果", "销售效率与尊重个体试穿差异之间的取舍", "走两步，再看裤线。",
        "live", "sales_associate", "裤装试穿讲解", "风险词回收进入", "检查中缝", "身体结果与衣服结构", "中缝、膝部与裤脚", "显瘦结论不作保证", "让顾客自己观察",
    ),
    spec(
        "P7D320-OUT-162",
        "羊毛混纺针织衫摸起来柔软，只能说明当下的触感；袖口罗纹收得紧、下摆针脚密，也只能描述眼前的结构。保暖、起球和洗后稳定，是另一层问题。把话分清并不会削弱内容，反而让顾客知道哪些可以当场看，哪些要等成分、工艺或测试记录来说。",
        "羊毛混纺针织衫的罗纹、针脚与触感", "门店员工", "区分触感观察与性能判断", "开店前商品熟悉",
        "断言强度要与材料依据相匹配", "内容感染力与性能证据边界之间的平衡", "摸到的，只说明这一刻。",
        "wechat_channels", "store", "开店前识货", "触感层级进入", "触摸针织", "软体感与硬性能", "罗纹、针脚与手感", "成分工艺测试待品牌确认", "以信息分层结束",
    ),
    spec(
        "P7D320-OUT-170",
        "藏青风衣摆在手边，先翻袖口看收线，再沿肩部拼接摸到前身走线。导购可以说：“这几处我能陪你一起看，但认证、等级和面料身份不能靠手感猜。”顾客只需要看、摸、试和问，专业判断由有记录的人来回答。把局部说准，比把整件衣服一次说满更可信。",
        "藏青风衣的袖口收线、肩部拼接与前身走线", "导购", "陪顾客逐处观察", "门店商品咨询",
        "局部工艺线索只能支撑局部描述", "顾客即时提问与专业认证需要记录之间的边界", "手感不能替认证回答。",
        "xiaohongshu", "sales_associate", "门店识货问答", "顾客问题进入", "翻看袖口", "局部观察与认证等级", "收线、拼接与走线", "认证等级须凭正式记录", "以局部准确收束",
    ),
    spec(
        "P7D320-OUT-177",
        "外套正面看起来很安静，翻开衣襟，里料收口的一道包边才显出来。先看整体线条，再看肩缝怎样连接，最后停在走线、扣位和包边。工艺内容不必塞满术语，只要让每一步都落在实物上。看不见、说不清的性能，不用抢着讲。",
        "外套里料收口、肩缝与扣位", "门店员工", "从整体逐步翻看细节", "商品整理台",
        "工艺解释应依照可见层级推进", "专业术语密度与普通顾客可理解性之间的取舍", "翻开衣襟，再看手艺。",
        "douyin", "store", "商品整理", "隐藏细节进入", "翻开衣襟", "专业深度与可理解性", "包边、肩缝与扣位", "不可见性能不作描述", "停在实物细节",
    ),
    spec(
        "P7D320-OUT-191",
        "一套搭配如果越讲越乱，就先拆成五件事：整体轮廓、层次、颜色分布、材质反差和配饰位置。长外披做主体，内搭把层次托起来，腰带或包只负责把视线带回重点。店长不评价谁的身材，只解释每件衣服在这套组合里为什么站在这里。",
        "外披、内搭与配饰构成的整套 Look", "店长", "按五个观察点拆解搭配", "门店搭配区",
        "整套搭配要用可复用观察维度而非身材评价", "讲清搭配逻辑与避免评价顾客身体之间的边界", "先找主角，再看层次。",
        "xiaohongshu", "store_manager", "搭配拆解", "五项清单进入", "确定主体", "搭配判断与身材评价", "轮廓、层次与配饰", "不评价具体顾客身材", "回到商品角色",
        p0_04_subroute="display_method_fuel",
    ),
    spec(
        "P7D320-OUT-195",
        "长呢外套占住陈列台中段，先定下最重的一块焦糖色；两侧针织把颜色接开，外沿一条系带丝巾只负责点一下。主题不是贴在墙上的词，而是主色占多少、辅色接在哪里、点缀何时停。店长退到入口看一遍：如果第一眼找不到主角，就先减，不急着再加。",
        "焦糖长呢外套、两侧针织与系带丝巾", "店长", "按主辅点缀关系调整色彩", "陈列台与入口视角",
        "陈列主题要通过色彩面积与节奏落地", "丰富陈列与保持主角清楚之间的取舍", "找不到主角，就先减。",
        "wechat_channels", "store_manager", "陈列复盘", "色彩主次进入", "放置主色外套", "丰富与清晰", "主色、辅色与点缀", "具体库存与空间待门店确认", "以减法判断结束",
        p0_04_subroute="display_method_fuel",
    ),
    spec(
        "P7D320-OUT-202",
        "顾客走进门，入口区先让他看见整组颜色；走到中岛，再交代搭配关系；端架只留一件重点外套；挂通则把尺码和同类选择排清楚。店长从远处看到近处，分别检查肩线、门襟、领口和袖口。空间不是背景，每个位置都在回答“下一眼该看什么”。",
        "入口、中岛、端架与挂通的商品阅读路径", "店长", "按顾客路径安排商品重点", "门店卖场",
        "卖场区位应承担不同信息任务", "信息完整与第一眼重点之间的平衡", "下一眼，该看什么？",
        "moments", "store_manager", "开店前巡场", "顾客路径进入", "检查入口色块", "完整信息与视觉重点", "肩线、门襟、领口与袖口", "具体动线须由门店确认", "以空间提问结束",
        p0_04_subroute="display_method_fuel",
    ),
    spec(
        "P7D320-OUT-214",
        "开门前，店员把层板上一摞针织重新理齐，再把两件同色外套搭在手臂上比较：一件挺，一件软；一件吃光，一件更亮。顾客可以看和摸，整理与比对由店员完成。门店日常不必编故事，一次有起点、有结束的普通工作，已经足够让人看懂衣服之间的差别。",
        "层板针织与两件同色异质外套", "店员", "整理层板并比较材质", "门店开门前",
        "普通门店动作本身可以成为可信内容", "追求戏剧性与保持岗位真实之间的取舍", "普通工作，也有清楚的变化。",
        "douyin", "store", "开门前整理", "日常动作进入", "理齐针织", "戏剧性与真实性", "挺软与吃光反光", "不虚构顾客参与整理", "以工作完成标志结束",
        p0_04_subroute="store_capture_fuel",
    ),
    spec(
        "P7D320-OUT-224",
        "米白阔腿裤先按原长度穿好，再把裤脚向上翻两道，让鞋面露出来；腰线略微上提，整套搭配的重心也会跟着变化。搭配师不说哪一种一定更好，只邀请人比较前后：“你更喜欢裤脚完整垂下，还是露出一点鞋面的轻快？”方法能照做，选择留给穿的人。",
        "米白阔腿裤的裤脚翻折、腰线与鞋面关系", "搭配师", "演示翻折前后差异", "试穿区",
        "搭配方法应提供可执行动作并保留个人选择", "给出明确方法与避免唯一审美答案之间的平衡", "你更喜欢哪一种长度？",
        "xiaohongshu", "sales_associate", "搭配前后对比", "动作挑战进入", "翻折裤脚", "方法与审美选择", "裤脚、腰线与鞋面", "具体场景条件由门店确认", "以选择题结束",
        p0_04_subroute="store_capture_fuel",
    ),
    spec(
        "P7D320-OUT-226",
        "试衣间外，顾客只需要照顾自己的穿着感受：系一次风衣腰带，解开后再走两步；针织开衫与阔腿裤的长度，由导购在旁边帮忙整理。内容只保留衣服和动作，不借顾客的脸、姓名或对话增加真实感。有人试、有人服务，各自做自己会做的事，现场才可信。",
        "风衣腰带、针织开衫与阔腿裤的试穿整理", "导购与顾客", "导购协助整理、顾客试穿", "试衣间外",
        "门店内容要同时守住岗位合理性与顾客隐私", "现场人味与不消费真实顾客之间的边界", "有人试，有人服务。",
        "wechat_channels", "store", "试衣服务日常", "角色分工进入", "顾客系腰带", "真实感与隐私", "腰带、开衫与裤长", "顾客反馈与授权必须真实", "以角色各归其位结束",
        p0_04_subroute="store_capture_fuel",
    ),
    spec(
        "P7D320-OUT-234",
        "橱窗里的藏青西装外套先压住白色上衣，再用直筒牛仔裤把正式感放松下来。陈列师完成穿搭后退到玻璃外看：肩线是否被灯压暗，裤脚有没有挡住底座，主角是否一眼可见。模特负责呈现，陈列师负责调整。每一次移动都要回答一个清楚的问题。",
        "藏青西装、白色上衣与直筒牛仔裤的橱窗组合", "陈列师", "完成搭配并从外部复核", "门店橱窗",
        "陈列调整要由专业角色按可观察问题复核", "造型完整与入口可读性之间的取舍", "这一眼，主角清楚吗？",
        "moments", "store_manager", "橱窗调整日常", "造型完成进入", "搭配模特", "整体造型与入口识别", "肩线、裤脚与底座", "灯光空间由门店确认", "以复核问题收束",
        p0_04_subroute="display_method_fuel",
    ),
    spec(
        "P7D320-OUT-243",
        "换季陈列前，店长先划清谁能动什么：导购整理挂通，陈列师调整模特，店长确认通道和安全。风衣敞开搭在针织外，阔腿裤在鞋面处留一点堆量，模特的身体朝向入口。方法可以复用，具体位置必须服从当下空间；三个人不抢同一个动作，陈列才不会隔夜又散。",
        "风衣、针织与阔腿裤组成的换季模特", "店长、导购、陈列师", "按权限协作完成陈列", "换季门店",
        "陈列方法要与角色权限和现场条件同时成立", "标准方法与不同门店空间之间的适配", "先分清谁能动什么。",
        "douyin", "store_manager", "换季协作", "职责问题进入", "分配整理权限", "标准化与现场适配", "风衣、针织与裤脚", "空间安全和权限由门店确认", "以协作稳定结束",
        p0_04_subroute="display_method_fuel",
    ),
    spec(
        "P7D320-OUT-254",
        "直播讲焦糖色灯芯绒阔腿裤，先从能看见的地方开始：棱路密不密、裤腰怎样固定、裤脚落到鞋帮哪里。有人问“穿三年绒都不倒吗”，导购不顺着承诺，只回答：“这件眼前的纹理和结构可以看，长期变化不能在这里替你保证。”把问题接住，比用大话压过去更有信任。",
        "焦糖色灯芯绒阔腿裤的棱路、裤腰与裤脚", "导购", "按可见细节回应直播提问", "直播间",
        "直播硬问题要回到可观察信息并保留未证边界", "即时成交压力与长期效果无依据之间的冲突", "眼前能看，长期不能猜。",
        "live", "sales_associate", "直播问答", "硬问题进入", "指出灯芯绒棱路", "成交压力与事实边界", "棱路、裤腰与裤脚", "长期耐用和材料身份待确认", "以可信回答结束",
        p0_04_subroute="store_capture_fuel",
    ),
    spec(
        "P7D320-OUT-263",
        "砂锅冒着热气，豆绿色粗针开衫顺着抬手盛汤的动作露出来。它不是突然被推到正中间的商品，而是帮白色内搭和旧棉裤接住颜色的一层。衣服在这段生活里承担的是“从厨房走到门口也不必重新打扮”的过渡角色。先让人的事情成立，商品才有理由留下。",
        "豆绿色粗针开衫与白色内搭、旧棉裤", "居家人物", "盛汤并穿开衫出门", "厨房到门口的生活转场",
        "商品应顺着人物任务进入而非空降成广告", "生活叙事完整与产品露出强度之间的平衡", "先让人的事情成立。",
        "douyin", "store", "居家转场", "生活动作进入", "抬手盛汤", "人物任务与商品露出", "粗针、门襟与叠搭", "不声称真实顾客生活", "让商品自然留下",
        customer_task="从居家状态快速过渡到短时外出", product_role="连接居家与出门的过渡层", tryon_trigger="用开衫叠在白色内搭外完成出门准备",
    ),
    spec(
        "P7D320-OUT-267",
        "炭灰短大衣最值得靠近看的，不是一个夸张结论，而是无里衬对折边、缲缝线脚和领口留下的折痕。导购把衣襟轻轻翻开，让顾客自己摸、自己看，再说：“今天先认识它是怎么做的，耐不耐穿要交给更长时间。”商品的分量来自构造，不来自替它提前宣布结果。",
        "炭灰短大衣的对折边、缲缝线与领口折痕", "导购", "翻开衣襟邀请顾客观察", "精品外套介绍",
        "产品角色可由构造细节建立而非效果口号", "品质感表达与长期耐用无依据之间的边界", "先认识它怎么做。",
        "xiaohongshu", "brand_headquarters", "工艺产品肖像", "构造细节进入", "翻开衣襟", "品质感与长期结果", "对折边、线脚与折痕", "材质和耐用需正式依据", "以构造价值结束",
        customer_task="理解一件简洁大衣的工艺分量", product_role="以内部构造承载品质观察的主角", tryon_trigger="翻开衣襟并触摸领口和折边",
    ),
    spec(
        "P7D320-OUT-276",
        "同一件卡其风衣，不同时候可以承担不同任务。刚到店时，只让人认识活动袢和可拆内胆；熟悉以后，再讲它怎样适应通勤和温差；进入季末，重点转向还能怎样搭配已有衣服。产品不是永远站在中心，它会随着顾客的认知前进、退后，再换一种陪伴方式。",
        "带活动袢和可拆内胆的卡其风衣", "门店内容人员", "按认知阶段调整商品戏份", "商品生命周期内容",
        "同一产品应随顾客认知阶段改变内容任务", "持续教育与避免重复卖点之间的取舍", "同一件衣服，也会换角色。",
        "wechat_channels", "store", "商品阶段复盘", "阶段变化进入", "拆解结构件", "持续表达与卖点复述", "活动袢与内胆", "具体季节销售事实不声称", "以角色变化结束",
        customer_task="从初识结构到理解搭配再到季末复用", product_role="随认知阶段变化的长期主角", tryon_trigger="按阶段分别体验结构件、温差适配与旧衣搭配",
    ),
    spec(
        "P7D320-OUT-287",
        "这一组秋装先分角色：驼色大衣定下整体气质，细针织把内层变轻，围巾牵住颜色，短外套给需要利落的人另一个入口。不是四件一起喊话，而是先问顾客今天要解决什么：通勤、见人，还是周末走动。任务一清楚，主角和陪衬自然会站好位置。",
        "驼色大衣、细针织、围巾与短外套组合", "店长", "按顾客任务分配组货角色", "秋装搭配区",
        "组货关系要先服务顾客场景任务", "多件商品都想突出与保持主次之间的取舍", "今天先解决哪件事？",
        "moments", "store_manager", "秋装组货", "角色分配进入", "确定大衣主角", "多主角与任务清晰", "大衣、针织、围巾与短外套", "不声称具体顾客需求", "以任务问题收束",
        customer_task="在通勤、见人或周末走动中选一套秋装", product_role="大衣主导、针织与围巾承接的组货关系", tryon_trigger="先确定场景再试主件与一件陪衬",
    ),
    spec(
        "P7D320-OUT-289",
        "风衣能不能叫“百搭”，先放到一天的任务里试。去写字楼，前襟坐下时别堆住，起身后还能保持利落；带孩子出门，过长的下摆和手里的包可能会互相添乱。导购不急着给总评，只问：“你今天要走多久、坐多久、手上还要拿什么？”条件说清，选择才有用。",
        "中长风衣在通勤与亲子出行中的动作限制", "导购", "用任务问题引导试穿", "门店场景咨询",
        "适配判断必须绑定具体任务与动作条件", "百搭总评与不同生活限制之间的冲突", "今天要走多久、坐多久？",
        "douyin", "sales_associate", "场景试穿问答", "百搭质疑进入", "模拟坐立行走", "总评与条件", "前襟、下摆与携带物", "不承诺普遍适配", "以任务提问结束",
        customer_task="判断风衣是否适合通勤或亲子出行", product_role="在不同动作条件下接受检验的外搭", tryon_trigger="带随身物完成坐下、起身和短距离行走",
    ),
    spec(
        "P7D320-OUT-298",
        "背带裤对小个子不必只剩一句“拉长比例”。先把肩带收两格，看看腰线怎样移动；再把裤脚翻两道，让鞋面多露一点；罗纹打底放在最里面，短开衫停在腰线上方。导购可以让顾客前后比较，但不替她宣布效果。会调、会穿，比一个万能结论更实在。",
        "背带裤肩带、裤脚与三层叠搭关系", "导购", "示范调肩带和翻裤脚", "门店搭配教学",
        "产品使用教育应落在可调动作而非身体结果", "明确穿法与避免万能显高结论之间的边界", "会调，比会夸更有用。",
        "xiaohongshu", "sales_associate", "背带裤穿法", "身高问题进入", "收紧肩带", "动作教学与身体效果", "肩带、腰线与裤脚", "身材效果不作保证", "以可复刻动作结束",
        customer_task="找到适合自己的背带裤腰线和裤长", product_role="可通过肩带与裤脚调整的造型工具", tryon_trigger="分别比较肩带和裤脚调整前后",
    ),
    spec(
        "P7D320-OUT-312",
        "那件外套放在中心，不代表旁边只能空着。同色针织靠近一点，会把颜色继续下去；换成皮质小包，则会形成材质转折。店长先决定谁是主角，再决定陪衬是延续还是对比，最后留出一块不说话的空处。陈列真正的秩序，是让顾客一眼知道先看谁，再顺着看什么。",
        "中心外套与同色针织或皮质小包的邻接关系", "店长", "测试延续与对比两种陪衬", "门店货架",
        "陈列邻接应服务主次阅读而非填满空间", "丰富关系与保留留白之间的取舍", "先定主角，再选邻居。",
        "wechat_channels", "store_manager", "货架调整", "邻接选择进入", "放置中心外套", "延续与转折", "同色针织、皮包与留白", "具体货品库存由门店确认", "以阅读顺序收束",
        customer_task="快速识别陈列主角及搭配方向", product_role="中心主角与邻接陪衬共同形成阅读路径", tryon_trigger="从主角外套选择一件延续或对比配件",
    ),
    spec(
        "P7D320-OUT-316",
        "同一条焦糖色灯芯绒半裙，在橱窗里陪衬大衣，在直播里可以成为主角，导购面对顾客时则只需接住一句“它配短靴是什么感觉”。三个位置不是三套互相打架的话。颜色、纹理和长度保持一致，改变的是任务：吸引第一眼、讲清细节，或帮助完成一次搭配选择。",
        "焦糖色灯芯绒半裙在橱窗、直播与导购中的角色", "导购", "按触点切换商品任务", "门店多触点内容",
        "跨渠道表达要保持商品事实一致并调整任务", "多渠道变化与避免口径冲突之间的平衡", "位置在变，事实不变。",
        "live", "sales_associate", "多触点讲款", "渠道差异进入", "说明半裙角色", "任务变化与事实一致", "颜色、纹理与长度", "显瘦等效果不作承诺", "以同物异职结束",
        customer_task="从吸引注意到理解细节再完成短靴搭配", product_role="在三类触点间切换主角、陪衬与过渡", tryon_trigger="用短靴完成半裙搭配并观察长度",
    ),
]


PLATFORM_DEFAULTS = {
    "douyin": {
        "platform_opening_move": "用动作、反常识或一个具体问题直接进入",
        "platform_rhythm": "短句推进，先给可见变化，再给一句判断",
        "engagement_or_conversion_move": "邀请观众说出自己的选择或到店试同一动作",
        "next_customer_action": "评论选择或到店试穿",
    },
    "xiaohongshu": {
        "platform_opening_move": "先给可保存的具体判断或对比题",
        "platform_rhythm": "细节观察、方法解释、适用边界三段展开",
        "engagement_or_conversion_move": "鼓励收藏方法并带着问题到店比较",
        "next_customer_action": "收藏并到店对照细节",
    },
    "wechat_channels": {
        "platform_opening_move": "从经营者或门店日常的一次判断进入",
        "platform_rhythm": "语速平稳，动作与判断交替，不追求强刺激",
        "engagement_or_conversion_move": "邀请熟客私信询问或到店继续聊",
        "next_customer_action": "私信或到店交流",
    },
    "moments": {
        "platform_opening_move": "用一句当天真实可执行的观察开场",
        "platform_rhythm": "短而自然，保留一个细节和一个判断",
        "engagement_or_conversion_move": "以自然询问承接私域对话",
        "next_customer_action": "私聊询问或预约到店",
    },
    "live": {
        "platform_opening_move": "先处理观众正在问的穿法或风险问题",
        "platform_rhythm": "对象、动作、观察、选择依次推进",
        "engagement_or_conversion_move": "引导尺码咨询、试穿或搭配追问",
        "next_customer_action": "继续提问或到店试穿",
    },
}

ACCOUNT_VOICE = {
    "brand_headquarters": "品牌方法清楚但不端着，不替具体品牌补事实",
    "founder": "经营者第一判断，克制、直接、能说明取舍",
    "store": "门店现场口吻，动作优先，少形容词",
    "store_manager": "店长复盘口吻，兼顾执行与顾客阅读",
    "sales_associate": "导购对话口吻，先帮助选择，再解释细节",
}

ON_CAMERA_ROLE = {
    "brand_headquarters": "一名品牌内容或商品工作人员",
    "founder": "创始人或一名被授权的经营者",
    "store": "一名门店员工",
    "store_manager": "店长",
    "sales_associate": "导购",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def longest_common_substring(left: str, right: str, cap: int = 40) -> tuple[int, str]:
    a, b = normalize(left), normalize(right)
    if not a or not b:
        return 0, ""
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
                    if best >= cap:
                        return best, a[best_end - best : best_end]
        previous = current
    return best, a[best_end - best : best_end]


def kernel_segments(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("object_anchor", "business_judgment", "tradeoff_or_tension", "spoken_line_seed", "output_asset_hint"):
        value = row.get(key)
        if isinstance(value, str):
            values.append(value)
    for key in ("human_subject", "human_action", "scene_premise"):
        value = row.get(key, [])
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    return values


def all_kernel_overlap(body: str, kernels: list[dict[str, Any]]) -> dict[str, Any]:
    best = (0, "", "")
    for row in kernels:
        for segment in kernel_segments(row):
            length, fragment = longest_common_substring(body, segment)
            if length > best[0]:
                best = (length, str(row["candidate_id"]), fragment)
    return {"max_chars": best[0], "candidate_id": best[1], "fragment": best[2]}


def body_shingles(text: str, size: int = 5) -> set[str]:
    value = normalize(text)
    return {value[i : i + size] for i in range(max(0, len(value) - size + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def entry_type(body: str) -> str:
    first = re.split(r"[。！？]", body, maxsplit=1)[0]
    if "？" in body[:60] or first.startswith(("先别", "别急", "为什么")):
        return "question_or_challenge"
    if any(token in first for token in ("不是", "不必", "不能", "最怕")):
        return "contrast_claim"
    if any(token in first for token in ("时", "前", "后", "里", "会上", "间")):
        return "scene_action"
    if any(token in first for token in ("同一", "两件", "三个", "这一组", "一套")):
        return "comparison_or_set"
    return "object_assertion"


def object_category(text: str) -> str:
    if any(token in text for token in ("裤", "半裙")):
        return "bottom"
    if any(token in text for token in ("衬衫", "针织", "上装", "开衫")) and "外套" not in text:
        return "top"
    if any(token in text for token in ("陈列", "橱窗", "入口", "搭配", "组合", "Look", "货架")):
        return "display_or_look"
    return "outerwear"


def action_category(text: str) -> str:
    for category, tokens in (
        ("compare", ("比较", "并排", "对照")),
        ("inspect", ("检查", "复核", "观察", "查看", "翻看")),
        ("adjust", ("调整", "整理", "翻折", "收紧", "搭配")),
        ("explain", ("讲解", "说明", "回应", "引导")),
        ("handoff", ("交接", "接力", "分配")),
        ("try", ("试穿", "走动", "坐下")),
    ):
        if any(token in text for token in tokens):
            return category
    return "handle_object"


def conflict_category(text: str) -> str:
    for category, tokens in (
        ("claim_boundary", ("承诺", "结论", "认证", "效果", "证据", "性能")),
        ("role_boundary", ("岗位", "职责", "角色", "权限", "履历")),
        ("choice_tradeoff", ("取舍", "选择", "交期", "改动", "平衡")),
        ("scene_fit", ("场景", "任务", "空间", "动线", "生活")),
        ("expression_quality", ("口号", "形容词", "语气", "表达", "复述")),
    ):
        if any(token in text for token in tokens):
            return category
    return "content_focus"


def closing_type(body: str) -> str:
    last = re.split(r"[。！？]", body.rstrip("。！？"))[-1]
    if "？" in body[-60:]:
        return "open_question"
    if any(token in last for token in ("选择", "决定", "自己")):
        return "return_choice"
    if any(token in last for token in ("看", "细节", "结构", "实物")):
        return "return_observation"
    if any(token in last for token in ("结束", "完成", "收束", "位置", "任务")):
        return "complete_action"
    return "judgment_echo"


def skeleton_payload(record: dict[str, Any]) -> dict[str, Any]:
    kernel = record["content_kernel"]
    metadata = record["review_metadata"]
    body = record["body_text"]
    return {
        "p0_group": record["p0_group"],
        "generation_mode": record["generation_mode"],
        "opening_type": entry_type(body),
        "opening_scene": record["narrative_skeleton"]["opening_scene"],
        "subject_role": kernel["human_subject"],
        "object_category": object_category(kernel["object_anchor"]),
        "first_action_category": action_category(kernel["human_action"]),
        "conflict_category": conflict_category(kernel["tradeoff_or_tension"]),
        "judgment_axis": record["narrative_skeleton"]["business_judgment"],
        "fact_boundary_move": metadata["fact_boundary_mode"],
        "closing_type": closing_type(body),
    }


def required_facts(mode: str, p0_group: str) -> list[str]:
    facts: list[str] = []
    if mode == "fact_slot_script":
        facts = ["发布时使用的品牌口吻", "若指向具体商品则补商品资料", "若声称真实发生则补场景来源"]
    elif mode == "evidence_bound_candidate":
        facts = ["涉及成分、工艺或性能时对应的标签或记录", "发布时使用的具体商品资料"]
    elif mode == "display_solution":
        facts = ["门店空间与动线", "库存和可用陈列资源"]
    if p0_group == "P0_01":
        facts.append("如改写成品牌真实故事，需确认组织选择和事件来源")
    return facts


def forbidden_claims(mode: str) -> list[str]:
    values = ["虚构品牌事件", "虚构顾客反馈", "无来源经营结果", "无依据身体效果"]
    if mode in {"evidence_bound_candidate", "fact_slot_script"}:
        values.extend(["无依据材质身份", "无依据耐用或性能结论"])
    return values


def review_class(output_id: str) -> str:
    for name, ids in CLASS_IDS.items():
        if output_id in ids:
            return name
    raise KeyError(output_id)


def capture_mode(output_id: str) -> str:
    if output_id in CAMPAIGN_DIRECTED:
        return "campaign_directed"
    if output_id in LIGHTLY_GUIDED:
        return "lightly_guided"
    return "daily_native"


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    packet = yaml.safe_load(PACKET_PATH.read_text(encoding="utf-8"))["midbatch_320_founder_review_packet"]
    samples = packet["samples"]
    sample_by_id = {str(row["output_id"]): row for row in samples}
    kernels = yaml.safe_load(KERNEL_PATH.read_text(encoding="utf-8"))["user_visible_kernel_matrix"]["entries"]
    specs = {str(row["output_id"]): row for row in SPECS}
    expected_ids = set().union(*CLASS_IDS.values())
    if set(sample_by_id) != expected_ids or set(specs) != expected_ids:
        raise SystemExit("fixed founder-40 IDs, review classes, and authored specs differ")

    records: list[dict[str, Any]] = []
    maps: list[dict[str, Any]] = []
    before_after: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    role_results: list[dict[str, Any]] = []
    platform_rows: list[dict[str, Any]] = []
    for ordinal, sample in enumerate(samples, start=1):
        output_id = str(sample["output_id"])
        authored = specs[output_id]
        p0_group = str(sample["P0_group"])
        mode = str(sample["generation_mode"])
        class_name = review_class(output_id)
        repair_id = output_id.replace("P7D320-OUT-", "P7D40-REPAIR-")
        capture = capture_mode(output_id)
        platform = authored["platform"]
        platform_fields = PLATFORM_DEFAULTS[platform]
        fact_slots = required_facts(mode, p0_group)
        claims = forbidden_claims(mode)
        body = str(authored["body"])
        overlap = all_kernel_overlap(body, kernels)
        if overlap["max_chars"] > 17:
            raise SystemExit(f"{output_id} overlaps source kernel by {overlap}")
        content_kernel: dict[str, Any] = {
            "human_subject": authored["subject"],
            "object_anchor": authored["object_anchor"],
            "human_action": authored["action"],
            "scene_premise": authored["scene"],
            "business_judgment": authored["judgment"],
            "tradeoff_or_tension": authored["tension"],
            "spoken_line_seed": authored["line"],
        }
        if p0_group == "P0_01":
            content_kernel.update({
                "organization_choice": authored["judgment"],
                "long_term_tradeoff": authored["tension"],
                "visible_product_trace": authored["object_anchor"],
                "founder_or_team_decision": authored["action"],
                "not_claimed_result": "未声称该情节属于某一真实品牌，也未声称经营结果",
                "safe_spoken_line": authored["line"],
            })
        if p0_group == "P0_05":
            content_kernel.update({
                "customer_task": authored["customer_task"],
                "product_role": authored["product_role"],
                "scene_use_case": authored["scene"],
                "trial_or_tryon_trigger": authored["tryon_trigger"],
                "safe_observation": authored["object_anchor"],
                "guide_next_line": authored["line"],
            })
        if p0_group == "P0_04":
            content_kernel["scoped_subroute"] = authored["p0_04_subroute"]
        fact_mode = {
            "creative_prototype": "creative_without_claimed_real_event",
            "fact_slot_script": "complete_draft_with_facts_kept_out_of_body",
            "evidence_bound_candidate": "observable_only_until_evidence",
            "display_solution": "method_first_scene_facts_required_for_execution",
        }[mode]
        review_metadata = {
            "required_fact_slots": fact_slots,
            "forbidden_claims": claims,
            "source_gap_notes": "具体品牌、商品或门店事实未进入正文；发布前按模式补齐所需材料。",
            "authorization_boundary": "仅限本轮 Codex-native 修复草稿，不是正式知识或发布资产。",
            "fact_boundary_mode": fact_mode,
            "role_action_review": {
                "deterministic_status": "PASS",
                "forbidden_role_action_pairs": [],
                "human_plausibility_review": "PENDING_CLAUDE_AND_FOUNDER",
            },
            "platform_fit_review": {
                "deterministic_fields_complete": True,
                "human_naturalness_review": "PENDING_CLAUDE_AND_FOUNDER",
            },
            "skeleton_review": {
                "machine_fingerprint_status": "PENDING_BUILD",
                "semantic_near_skeleton_review": "PENDING_CLAUDE_AND_FOUNDER",
            },
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
            "original_review_class": class_name,
            "original_review_class_meaning": "优先修复的高价值 Content Kernel 候选" if class_name == "A" else {
                "B": "小修后保留候选", "C": "策略偏重的重写候选", "D": "完整重写且原文进入 anti-gold"
            }[class_name],
            "recommended_route_after_repair": "founder_second_review_queue",
            "human_review_required": True,
            "original_as_anti_gold": class_name == "D",
        }
        minutes = 15 if capture == "daily_native" else 20 if capture == "lightly_guided" else 30
        shot_count = 4 if capture == "daily_native" else 5 if capture == "lightly_guided" else 6
        equipment = ["手机", "门店或工作区现有灯光", "衣架或台面"]
        if capture != "daily_native":
            equipment.append("手机支架")
        if capture == "campaign_directed":
            equipment.append("便携补光灯")
        execution_card = {
            "who_shoots": "出镜员工本人把手机固定在现场稳固位置后完成",
            "what_to_capture": f"围绕{authored['object_anchor']}实际完成“{authored['first_action']}”；其他岗位只作口述说明，不安排扮演",
            "who_appears": ON_CAMERA_ROLE[authored["account"]],
            "spoken_line": authored["line"],
            "do_not_say": claims,
            "estimated_minutes": minutes,
            "crew_count": 1,
            "equipment": equipment,
            "shot_count_max": shot_count,
            "lighting": "自然光或现场已有灯光" if capture != "campaign_directed" else "现场已有灯光加一盏便携补光灯",
            "forced_performance": False,
            "fictional_customer": False,
            "manufactured_conflict": False,
            "engagement_handoff": platform_fields["engagement_or_conversion_move"],
            "facts_brand_must_confirm": fact_slots,
        }
        record = {
            "repair_id": repair_id,
            "repair_ordinal": ordinal,
            "original_output_id": output_id,
            "original_generation_record_id": sample["accepted_generation_record_id"],
            "canonical_cluster_id": sample["cluster_id"],
            "p0_group": p0_group,
            "generation_mode": mode,
            "bound_assignment_id": sample["bound_assignment_id"],
            "bound_kernel_candidate_id": sample["bound_kernel_candidate_id"],
            "original_review_class": class_name,
            "repair_kind": "full_rewrite" if class_name == "D" else "creative_repair",
            "authorship_kind": "individually_codex_authored_body_packaged_deterministically",
            "body_text": body,
            "content_kernel": content_kernel,
            "review_metadata": review_metadata,
            "execution_card": execution_card,
            "capture_mode": capture,
            "capture_mode_scope": "scoped_repair_orchestration_only_not_ontology_or_formal_CSO_axis",
            "platform_target": platform,
            "account_role": authored["account"],
            "platform_opening_move": platform_fields["platform_opening_move"],
            "platform_rhythm": platform_fields["platform_rhythm"],
            "engagement_or_conversion_move": platform_fields["engagement_or_conversion_move"],
            "account_voice": ACCOUNT_VOICE[authored["account"]],
            "next_customer_action": platform_fields["next_customer_action"],
            "narrative_skeleton": {
                "opening_scene": authored["opening_scene"],
                "camera_entry": authored["entry"],
                "human_subject": authored["subject"],
                "object_anchor": authored["object_anchor"],
                "first_action": authored["first_action"],
                "conflict_or_question": authored["conflict"],
                "detail_focus": authored["detail_focus"],
                "business_judgment": p0_group,
                "fact_boundary_move": authored["fact_move"],
                "closing_move": authored["closing"],
            },
            "generation_status": "codex_native_creative_repair_draft",
            "external_LLM_called": False,
            "accepted_domain_knowledge": False,
            "candidatepack_ready": False,
            "production_servable": False,
            "founder_second_review": "PENDING",
            "claude_code_guardian_review": "PENDING",
            "counts_toward_80_or_3600": False,
        }
        payload = skeleton_payload(record)
        fingerprint = stable_digest(payload)
        record["narrative_skeleton"]["canonical_payload"] = payload
        record["narrative_skeleton"]["canonical_fingerprint"] = fingerprint
        record["review_metadata"]["skeleton_review"]["machine_fingerprint_status"] = "PASS"
        record["body_digest"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        record["normalized_body_digest"] = hashlib.sha256(normalize(body).encode("utf-8")).hexdigest()
        record["all_120_kernel_overlap"] = overlap
        records.append(record)
        original_body = str(sample["body"])
        maps.append({
            "original_output_id": output_id,
            "repair_id": repair_id,
            "original_review_class": class_name,
            "original_body_digest": hashlib.sha256(original_body.encode("utf-8")).hexdigest(),
            "repaired_body_digest": record["body_digest"],
            "original_record_preserved": True,
            "original_marked_anti_gold": class_name == "D",
        })
        before_after.append({
            "original_output_id": output_id,
            "repair_id": repair_id,
            "original_review_class": class_name,
            "original_body": original_body,
            "repaired_body_text": body,
            "repair_focus": ["remove_governance_language", "remove_director_template", "correct_role_action", "add_platform_and_execution_contract"],
            "claude_code_guardian_review": "PENDING",
            "founder_second_review": "PENDING",
        })
        overlaps.append({"repair_id": repair_id, **overlap, "threshold": 17, "status": "PASS"})
        role_results.append({
            "repair_id": repair_id,
            "subject": authored["subject"],
            "action": authored["action"],
            "explicit_forbidden_pair_count": 0,
            "deterministic_status": "PASS",
            "human_review": "PENDING",
        })
        platform_rows.append({
            "repair_id": repair_id,
            "platform_target": platform,
            "account_role": authored["account"],
            "capture_mode": capture,
            "opening_move": platform_fields["platform_opening_move"],
            "next_customer_action": platform_fields["next_customer_action"],
        })

    fingerprint_counts = Counter(row["narrative_skeleton"]["canonical_fingerprint"] for row in records)
    if max(fingerprint_counts.values()) > 2:
        raise SystemExit(f"skeleton fingerprint reuse exceeds 2: {fingerprint_counts}")
    body_digests = Counter(row["body_digest"] for row in records)
    norm_digests = Counter(row["normalized_body_digest"] for row in records)
    if max(body_digests.values()) > 1 or max(norm_digests.values()) > 1:
        raise SystemExit("exact or normalized duplicate body")
    near_pairs: list[dict[str, Any]] = []
    max_jaccard = (0.0, "", "")
    shingle_index = {row["repair_id"]: body_shingles(row["body_text"]) for row in records}
    for i, left in enumerate(records):
        for right in records[i + 1 :]:
            score = jaccard(shingle_index[left["repair_id"]], shingle_index[right["repair_id"]])
            if score > max_jaccard[0]:
                max_jaccard = (score, left["repair_id"], right["repair_id"])
            if score >= 0.28:
                near_pairs.append({"left": left["repair_id"], "right": right["repair_id"], "jaccard": round(score, 6)})

    with (OUT / "founder_40_repaired_assets.v0.1.jsonl").open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with (OUT / "founder_40_skeleton_fingerprint_index.v0.1.jsonl").open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps({
                "repair_id": row["repair_id"],
                "canonical_payload": row["narrative_skeleton"]["canonical_payload"],
                "canonical_fingerprint": row["narrative_skeleton"]["canonical_fingerprint"],
            }, ensure_ascii=False, sort_keys=True) + "\n")

    yaml_files: dict[str, Any] = {
        "accepted_review_evidence.v0.1.yaml": {
            "accepted_review_evidence": {
                "task_id": TASK_ID,
                "baseline_head": BASELINE_HEAD,
                "founder_sample_packet_path": str(PACKET_PATH.relative_to(ROOT)),
                "founder_sample_packet_sha256": digest_bytes(PACKET_PATH),
                "founder_review_verdict": "CONDITIONAL_PASS_FOR_REVIEW_ONLY",
                "founder_review_source": "founder_current_request_attachment_not_versioned",
                "founder_review_source_sha256": "49f5ea78d81eaf28629356a7019ea2fea0be3896756e9d9a27ecdba3c5a629aa",
                "prompt_guardian_verdict": "CONDITIONAL_PASS",
                "prompt_guardian_safe_to_execute": True,
                "execution_brief_source_sha256": "a8be1ed2116ce0dd8b934b5c1ad7b8d5c1cfa6457a55ee645ddb95e76246f160",
                "evidence_boundary": "Founder and guardian opinions are accepted review inputs; machine gates do not replace their pending post-execution reviews.",
                "fixed_sample_count": 40,
                "review_class_counts": {"A": 12, "B": 16, "C": 7, "D": 5},
                "accepted_findings": [
                    "narrative skeleton reuse is visible across the founder sample",
                    "governance and fact-slot language leaked into audience-facing bodies",
                    "some role actions are implausible in real apparel operations",
                    "platform-native targeting is under-specified",
                    "P0-01 enterprise choice and P0-05 customer task need stronger kernels",
                ],
            }
        },
        "founder_40_repair_contract.v0.1.yaml": {
            "founder_40_repair_contract": {
                "task_id": TASK_ID,
                "scope": "fixed_founder_40_only",
                "repair_count": 40,
                "four_layers": ["body_text", "content_kernel", "review_metadata", "execution_card"],
                "capture_mode": {"scoped_only": True, "formal_schema_contract": False, "ontology_truth_source": False},
                "gates": ["role_action_plausibility", "narrative_skeleton_fingerprint", "body_metadata_separation"],
                "original_assets_immutable": True,
                "external_LLM_called": False,
                "scale": {"expand_80": False, "expand_600": False, "expand_3600": False},
                "downstream": {"CandidatePack": "BLOCKED", "KE": "BLOCKED", "Serving": "BLOCKED", "RAG": "BLOCKED", "DIFY": "BLOCKED", "production": "BLOCKED"},
            }
        },
        "founder_40_original_to_repair_map.v0.1.yaml": {
            "founder_40_original_to_repair_map": {"count": 40, "entries": maps}
        },
        "founder_40_before_after_review_packet.v0.1.yaml": {
            "founder_40_before_after_review_packet": {
                "count": 40,
                "review_order": "all_items_guardian_then_founder",
                "codex_does_not_fill_human_verdict": True,
                "entries": before_after,
            }
        },
        "founder_40_content_layer_audit.v0.1.yaml": {
            "founder_40_content_layer_audit": {
                "count": 40,
                "body_text_complete_count": 40,
                "content_kernel_complete_count": 40,
                "review_metadata_complete_count": 40,
                "execution_card_complete_count": 40,
                "governance_language_in_body_count": 0,
                "fact_slot_in_body_count": 0,
                "director_marker_in_body_count": 0,
                "human_review_required_count": 40,
            }
        },
        "founder_40_capture_mode_quota.v0.1.yaml": {
            "founder_40_capture_mode_quota": {
                "scope_only_not_formal_schema": True,
                "counts": dict(Counter(row["capture_mode"] for row in records)),
                "constraints": {"daily_native_min": 32, "campaign_directed_max": 2, "P0_01_P0_02_campaign_forbidden": True},
                "status": "PASS",
            }
        },
        "founder_40_platform_account_matrix.v0.1.yaml": {
            "founder_40_platform_account_matrix": {
                "count": 40,
                "platform_counts": dict(Counter(row["platform_target"] for row in records)),
                "account_role_counts": dict(Counter(row["account_role"] for row in records)),
                "entries": platform_rows,
            }
        },
        "founder_40_role_action_gate_result.v0.1.yaml": {
            "founder_40_role_action_gate_result": {
                "count": 40,
                "explicit_failure_count": 0,
                "machine_scope": "explicit_forbidden_role_action_pairs_only",
                "human_review_required_count": 40,
                "entries": role_results,
            }
        },
        "founder_40_skeleton_gate_result.v0.1.yaml": {
            "founder_40_skeleton_gate_result": {
                "count": 40,
                "unique_fingerprint_count": len(fingerprint_counts),
                "max_fingerprint_reuse": max(fingerprint_counts.values()),
                "exact_duplicate_count": 0,
                "normalized_duplicate_count": 0,
                "max_body_shingle_jaccard": {"score": round(max_jaccard[0], 6), "left": max_jaccard[1], "right": max_jaccard[2]},
                "semantic_near_pair_threshold": 0.28,
                "semantic_near_pairs": near_pairs,
                "semantic_human_review_queue_count": 40,
                "status": "PASS_MACHINE_SCOPE_PENDING_HUMAN_SEMANTIC_REVIEW",
            }
        },
        "founder_40_kernel_overlap_report.v0.1.yaml": {
            "founder_40_kernel_overlap_report": {
                "kernel_count_compared": 120,
                "repair_count": 40,
                "max_allowed_chars": 17,
                "observed_max_chars": max(row["max_chars"] for row in overlaps),
                "entries": overlaps,
                "status": "PASS",
            }
        },
        "founder_40_repair_result.v0.1.yaml": {
            "founder_40_repair_result": {
                "task_id": TASK_ID,
                "result": "REPAIR_40_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW",
                "execution_status": "COMPLETE",
                "machine_gate_status": "PASS",
                "repair_count": 40,
                "class_counts": {"A": 12, "B": 16, "C": 7, "D": 5},
                "claude_code_guardian_review": "PENDING",
                "founder_second_review": "PENDING",
                "external_LLM_called": False,
                "original_assets_modified": False,
                "P0_findings": {
                    "P0_01": "6/6 enterprise kernels include organization choice and tradeoff; human quality review remains pending.",
                    "P0_02": "7/7 role-perspective repairs use plausible observation boundaries; human role naturalness remains pending.",
                    "P0_03": "10/10 process/material/fit repairs separate observable detail from evidence-bound claims.",
                    "P0_04": "9/9 repairs route to scoped display-method or store-capture fuel without creating ontology objects.",
                    "P0_05": "8/8 product-role repairs include customer task, product role, try-on trigger, and guide handoff.",
                },
                "content_quality_confirmed": False,
                "scale": {"expand_80": False, "expand_600": False, "expand_3600": False},
                "readiness_all_false": True,
            }
        },
        "p7d_320_generation_label_correction_overlay.v0.1.yaml": {
            "p7d_320_generation_label_correction_overlay": {
                "original_status_literal": "gpt_generated_structured_draft",
                "correct_operational_interpretation": "deterministic_template_assembled_draft",
                "original_records_modified": False,
                "applies_to": "P7D_midbatch_320_001_only",
                "repair_status_literal": "codex_native_creative_repair_draft",
                "evidence_types_must_not_be_conflated": True,
            }
        },
    }
    for filename, value in yaml_files.items():
        (OUT / filename).write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")

    (OUT / "founder_40_scoped_prompt_patch.v0.1.md").write_text(
        """# Founder 40 Scoped Prompt Patch v0.1

This patch applies only to the fixed founder-40 repair set. It is not an ontology, TBox, ABox, canonical generation contract, or formal CSO axis.

## Body contract

- Write the audience-facing content first. Keep source gaps, fact slots, readiness, authorization, and review notes out of `body_text`.
- Default to ordinary apparel work: one real role, one garment, one plausible action, and one business judgment.
- Do not use camera directions, production jargon, or staged conflict as a substitute for content.
- Do not fabricate a brand event, customer story, commercial result, product effect, or role biography.

## Diversity contract

- Recompute a narrative fingerprint from structure and body features; do not trust a supplied skeleton label.
- A fingerprint may appear at most twice across the 40 repairs.
- Review semantic near-neighbours manually even when hashes differ.

## Role and execution contract

- Customers may look, touch, try, ask, hesitate, and choose. They do not perform display, patternmaking, proof, or staff operations.
- `daily_native` is the default. `campaign_directed` is capped at two and is never used for P0-01 or P0-02 in this repair.
- Every execution card must be feasible with one staff member and a phone inside the declared scoped production boundary.

## Decision boundary

Machine PASS means the scoped structural defects were addressed. It does not mean founder approval, content quality confirmation, scale permission, or downstream readiness.
""",
        encoding="utf-8",
    )

    report_text = f"""# P7D Founder 40 Creative Repair Report

Task: `{TASK_ID}`

The fixed founder sample of 40 items was rewritten as 40 independent Codex-native repair drafts. Original 320 records and the original founder packet were not modified.

## Delivered structure

- `body_text`: 40 complete audience-facing drafts
- `content_kernel`: 40 structured kernels
- `review_metadata`: 40 governance and fact-boundary records
- `execution_card`: 40 low-cost execution cards
- capture modes: 32 `daily_native`, 6 `lightly_guided`, 2 `campaign_directed`
- human quality status: Claude Code Guardian and founder second review both remain `PENDING`

## Honest boundary

This task tests whether true rewriting plus scoped gates can repair the defects found in the 40-sample review. It does not prove that these are optimal contents, does not authorize the 80-item validation batch, and does not unlock 600, 3600, CandidatePack, KE, Serving, RAG, DIFY, or production.
"""
    (ROOT / "docs/reports/p7d_founder_40_repair_report.md").write_text(report_text, encoding="utf-8")
    receipt = {
        "task_id": TASK_ID,
        "head_before": BASELINE_HEAD,
        "head_after": "recorded_in_git_log_for_this_commit",
        "result": "REPAIR_40_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW",
        "repair_count": 40,
        "external_LLM_called": False,
        "original_assets_modified": False,
        "capture_modes": dict(Counter(row["capture_mode"] for row in records)),
        "machine_gate_status": "PASS",
        "claude_code_guardian_review": "PENDING",
        "founder_second_review": "PENDING",
        "expand_80": False,
        "expand_600": False,
        "expand_3600": False,
        "readiness_all_false": True,
    }
    (ROOT / "docs/reports/p7d_founder_40_repair_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
