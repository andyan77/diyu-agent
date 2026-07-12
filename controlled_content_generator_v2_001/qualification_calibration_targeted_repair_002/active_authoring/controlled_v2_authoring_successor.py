#!/usr/bin/env python3
"""Active controlled authoring successor for qualification repair 002.

The module accepts only an authoring input projection. Review envelope metadata
is deliberately absent from the function signatures and generated surfaces.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


TASK_ID = "CONTROLLED_V2_QUALIFICATION_CALIBRATION_TARGETED_REPAIR_002"
AUTHORING_VERSION = "controlled-v2-authoring-successor-r002"
FORBIDDEN_META_TERMS = (
    "资格",
    "合成",
    "内部审查",
    "复审",
    "版本比较",
    "材料允许",
    "hidden",
    "qualification",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


CP_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "CP01": {
        "label": "岗位任务VLOG",
        "dev": {
            "role": "整理台当班同事",
            "object": "三摞待归位针织衫",
            "scene": "闭店前二十分钟，整理台上还剩三摞针织衫、两张补标卡和一只空周转箱。",
            "action": "先把颜色混放的一摞拆开，再按尺码把补标卡夹在领口内侧。",
            "judgment": "先处理会影响明早找码的混放件，暂缓只需要熨平的两件。",
            "result": "周转箱最后只留下两件待蒸汽处理的衣服，明早交接单能直接照着拿。",
            "constraint": "这只是岗位任务记录，不推断销售、顾客反馈或真实门店效率。",
        },
        "hidden": {
            "role": "开店前备货同事",
            "object": "雨天外套补挂车",
            "scene": "开店前十五分钟，补挂车上有六件雨天外套、四个空衣架和一张缺码便签。",
            "action": "先把M码和L码分到门口两侧，再把缺码便签贴到补货格。",
            "judgment": "门口先给可试穿的尺码，缺码信息留给后台补，不用口头猜库存。",
            "result": "开门前外套区能看见完整尺码段，补货格也知道下一步找哪一组。",
            "constraint": "不把这次备货写成销量或服务承诺。",
        },
    },
    "CP02": {
        "label": "门店时段微纪录",
        "dev": {
            "role": "午后时段记录员",
            "object": "14:10到14:35的试衣区门帘",
            "scene": "14:10门帘半开、凳子上有两只购物袋；14:25门帘全拉上，门口只剩一双短靴。",
            "action": "镜头从门帘缝、凳子、短靴三个位置扫过，不拍人脸。",
            "judgment": "这个时段更像试穿间隙，而不是高峰排队。",
            "result": "记录只说明空间状态变化，不替顾客动作补故事。",
            "constraint": "不写真实顾客、不写成交、不写客流统计。",
        },
        "hidden": {
            "role": "晚间时段记录员",
            "object": "19:00后的收银台旁雨伞桶",
            "scene": "19:02雨伞桶是空的，19:18多了三把湿伞，地垫边缘被踩出两道水印。",
            "action": "先拍雨伞桶，再带到地垫水印和门口风铃。",
            "judgment": "这段时段的重点是进店动线被雨打断，不是讲人多。",
            "result": "下一次可补拍门口擦脚垫和挂伞提示是否更顺手。",
            "constraint": "不把三把伞推成真实客流结论。",
        },
    },
    "CP03": {
        "label": "单项手艺全过程",
        "dev": {
            "role": "熨烫同事",
            "object": "羊毛围巾卷边",
            "scene": "围巾边缘有一段卷起，蒸汽喷头、压布和木夹都放在左侧。",
            "action": "先隔布压住卷边，再用低温蒸汽从中段推到尾端，最后用木夹定住两分钟。",
            "judgment": "不用高温硬压，是为了让边缘回平但不把毛面压亮。",
            "result": "尾端仍留一点自然弧度，交接时标为可上架但需避开强灯直照。",
            "constraint": "不声称永久定型或材质效果。",
        },
        "hidden": {
            "role": "修线同事",
            "object": "大衣袖口松开的三针线",
            "scene": "袖口内侧有三针线松开，旁边放着同色线轴、细针和一张修补记录卡。",
            "action": "先从原针脚背面入针，再沿旧孔补三针，末端只打一个小结藏在里布里。",
            "judgment": "顺旧孔走针，是为了让外侧看不出新线压过面料。",
            "result": "袖口能平放，记录卡写明只做线脚复位，不改版型。",
            "constraint": "不夸手艺神奇，也不承诺耐久年限。",
        },
    },
    "CP04": {
        "label": "多岗位协作纪实",
        "dev": {
            "role": "陈列与仓位交接记录员",
            "object": "门口短夹克换位单",
            "scene": "陈列同事标出门口缺轻外套，仓位同事在周转架上找到三件同色短夹克。",
            "action": "两人先核尺码牌，再把原来的厚外套退到中岛台后侧。",
            "judgment": "换位依据是温度和门口厚重感，不是临时争位置。",
            "result": "门口少了一层拥挤，仓位单上留下退回件的位置。",
            "constraint": "不编争吵、不编谁说服谁。",
        },
        "hidden": {
            "role": "试衣区与陈列协作记录员",
            "object": "长裙试穿后回挂动作",
            "scene": "试衣区交回两条长裙，陈列台同一色系只剩一条短裙。",
            "action": "试衣区先确认裙摆无拖地痕，陈列同事再把长裙挂回同色短裙旁边。",
            "judgment": "回挂是为了让同色长度差被看见，不是临时补满空位。",
            "result": "短裙和长裙形成对照，试衣区也知道下一次先看裙摆状态。",
            "constraint": "不把协作写成戏剧冲突。",
        },
    },
    "CP05": {
        "label": "人物成长与职业史",
        "dev": {
            "role": "培训记录整理员",
            "object": "三张学徒改针记录卡",
            "scene": "三张记录卡分别写着三月练直线、五月改袖口、六月独立补领口。",
            "action": "把三张卡按月份铺开，旁边放第一次歪线和最近一次平线的对照布。",
            "judgment": "成长证据来自同一动作反复变稳，不来自一句努力。",
            "result": "下一张卡预留给八月的复杂面料练习。",
            "constraint": "不把加班写成成长，也不编个人经历。",
        },
        "hidden": {
            "role": "岗位学习记录员",
            "object": "新同事三次叠裤脚记录",
            "scene": "第一周裤脚边对不齐，第三周能按裤缝折齐，第六周开始自己检查左右高度。",
            "action": "镜头依次拍三张练习纸、两条裤脚高度和一只被擦掉重画的粉笔线。",
            "judgment": "变化点是检查动作从别人提醒变成自己先做。",
            "result": "下一步只记录是否能在厚面料上保持同样高度。",
            "constraint": "不写真实姓名、不写励志结论。",
        },
    },
    "CP06": {
        "label": "专业判断切片",
        "dev": {
            "role": "版型判断同事",
            "object": "肩线略外移的西装样衣",
            "scene": "样衣挂在半身台上，肩线比台肩外出半指，袖山没有塌。",
            "action": "先看肩线，再看袖山和前片是否被拉斜。",
            "judgment": "外移半指可以留下松量；如果前片斜了，才需要回改肩宽。",
            "result": "这件先保留肩宽，下一轮只复看前片垂直线。",
            "constraint": "不把个人审美写成绝对标准。",
        },
        "hidden": {
            "role": "面料判断同事",
            "object": "轻薄风衣背部压痕",
            "scene": "风衣背部有一道折痕，喷雾后面料回弹慢，袖口却很快恢复。",
            "action": "先在背部压痕处做小范围蒸汽，再和袖口回弹速度对照。",
            "judgment": "背部要低温慢放，袖口可快速整理，不能一把温度处理全件。",
            "result": "复核卡只写处理顺序，不写面料一定耐皱。",
            "constraint": "不推成身体效果或性能承诺。",
        },
    },
    "CP07": {
        "label": "用户问题诊断室",
        "dev": {
            "role": "问题诊断同事",
            "object": "短外套压肩问题卡",
            "scene": "问题卡写着肩部被压、袖长合适、内搭是厚毛衣。",
            "action": "先分出两个条件：换薄内搭仍压肩，或只在厚毛衣下压肩。",
            "judgment": "前者看肩宽，后者看搭配层厚，不把两个问题混成尺码错误。",
            "result": "建议分别试大一码和换薄内搭，不直接下结论。",
            "constraint": "不冒充真实顾问诊断。",
        },
        "hidden": {
            "role": "穿搭问题拆分同事",
            "object": "半裙显胯问题卡",
            "scene": "问题卡写着腰围合适、坐下不紧、正面看胯线明显。",
            "action": "先拆成版型线条和上衣长度两条分支，再用一件短上衣和一件过胯衬衫对照。",
            "judgment": "如果过胯衬衫能遮住胯线，问题不一定在半裙尺码。",
            "result": "给出的下一步是两种搭配对照试穿，不是让人立刻换码。",
            "constraint": "不把身体评价写进结论。",
        },
    },
    "CP08": {
        "label": "工艺／面料／版型解构",
        "dev": {
            "role": "结构解构同事",
            "object": "罗纹袖口和袖身拼接",
            "scene": "袖口罗纹比袖身厚，拼接线被藏在内侧一圈压线后面。",
            "action": "先翻出拼接线，再用手指按压罗纹回弹和袖身垂感。",
            "judgment": "厚罗纹负责收口，袖身负责垂下去，两者不是同一种弹性。",
            "result": "镜头最后停在内侧压线，说明结构如何把厚薄接住。",
            "constraint": "不把结构说成黑科技。",
        },
        "hidden": {
            "role": "版型解构同事",
            "object": "风衣后背活动褶",
            "scene": "后背中线有一条活动褶，外层压住，里层留出半掌活动量。",
            "action": "先拉开活动褶，再让衣架轻轻转向侧面看背部余量。",
            "judgment": "活动褶给手臂前伸留空间，不是单纯装饰线。",
            "result": "观众能看到背部为什么不被拉平。",
            "constraint": "不宣称适合所有身形。",
        },
    },
    "CP09": {
        "label": "适用边界与反选指南",
        "dev": {
            "role": "反选说明同事",
            "object": "厚底短靴",
            "scene": "短靴鞋底厚、鞋口硬，旁边放着长走路清单和短距离通勤清单。",
            "action": "先踩压鞋口，再把两张清单放到鞋旁边对照。",
            "judgment": "适合短距离撑造型，不适合第一次就穿去长时间站立。",
            "result": "替代方案是先选软鞋口低跟靴。",
            "constraint": "不把边界写成劝退全部人。",
        },
        "hidden": {
            "role": "适用边界记录员",
            "object": "高领厚毛衣",
            "scene": "毛衣领口高、肩部厚，旁边有室内空调和外套叠穿两张场景卡。",
            "action": "先拍领口贴近下巴的高度，再把它放进一件窄领外套里试搭。",
            "judgment": "单穿能保暖，叠窄领外套会顶住脖子。",
            "result": "替代方案是换半高领或外套留更宽领口。",
            "constraint": "不把不适合说成产品缺点。",
        },
    },
    "CP10": {
        "label": "证据与长期验证档案",
        "dev": {
            "role": "长期验证记录员",
            "object": "棉衬衫三次洗后袖长记录",
            "scene": "同一件衬衫在第1、3、5次洗后分别量袖长，尺子起点都压在肩缝。",
            "action": "每次只量右袖同一位置，并记录晾干方式。",
            "judgment": "指标统一后，才能讨论袖长是否真的变化。",
            "result": "第五次比第一次短0.3厘米，但记录仍标为继续观察。",
            "constraint": "不把单件测试推广到全部产品。",
        },
        "hidden": {
            "role": "证据档案记录员",
            "object": "帆布包提手承重记录",
            "scene": "同一只包在空包、放入两本书、放入四本书后三次拍提手弧度。",
            "action": "每次把包放在同一张桌沿，尺子只量提手最高点到桌面的距离。",
            "judgment": "提手弧度变大是这只包的观察结果，不等于承诺承重。",
            "result": "四本书状态下弧度多了1.1厘米，下一次只复测提手缝线是否松。",
            "constraint": "不写性能保证或普遍化结论。",
        },
    },
    "CP11": {
        "label": "产品诞生与设计取舍档案",
        "dev": {
            "role": "设计取舍记录员",
            "object": "风衣下摆开衩方案",
            "scene": "设计板上有直下摆、短开衩、长开衩三个方案，旁边贴着骑车动作照片。",
            "action": "先把三张纸样叠在一起，再抽出短开衩方案。",
            "judgment": "短开衩保留行走余量，也少放弃下摆重量感。",
            "result": "放弃长开衩的代价是骑车余量更小，后续需再试一次。",
            "constraint": "不把取舍写成唯一正确。",
        },
        "hidden": {
            "role": "设计档案整理员",
            "object": "衬衫口袋高度方案",
            "scene": "三张样板分别把口袋上移1厘米、保持原位、下移1厘米。",
            "action": "先让纽扣线和口袋边对齐，再比较手放入口袋时的折痕。",
            "judgment": "保持原位牺牲一点视觉新鲜感，但手放进去不顶胸前折线。",
            "result": "档案留下放弃上移的理由：折痕比比例更影响穿着观感。",
            "constraint": "不把设计选择包装成品牌理念。",
        },
    },
    "CP12": {
        "label": "产品迭代与版本日志",
        "dev": {
            "role": "版本日志记录员",
            "object": "裤脚反折宽度从2.0到2.8厘米",
            "scene": "旧样反折2.0厘米会露出内侧线，新样反折2.8厘米刚好压住线迹。",
            "action": "把旧样和新样并排，尺子分别贴住反折边。",
            "judgment": "改宽不是为了显眼，而是为遮住内侧线迹。",
            "result": "待验证项是坐下后反折边会不会顶到脚踝。",
            "constraint": "允许版本数字，但不写真实上市版本。",
        },
        "hidden": {
            "role": "迭代日志记录员",
            "object": "外套袖袢从单扣改双扣",
            "scene": "旧样单扣收紧后袖口翘起，新样双扣能分两档收袖。",
            "action": "先扣旧样单扣，再扣新样内外两颗扣，让袖口平放对照。",
            "judgment": "触发原因是袖口翘起，不是为了多加装饰。",
            "result": "下一次验证只看双扣在厚内搭下会不会硌手腕。",
            "constraint": "不把迭代写成已上市事实。",
        },
    },
    "CP13": {
        "label": "产品的生活与衣橱角色",
        "dev": {
            "role": "衣橱角色记录员",
            "object": "灰色针织开衫",
            "scene": "开衫分别和白衬衫、黑裙、薄风衣放在同一衣架旁。",
            "action": "先拍三组搭配，再把开衫单独挂回中间。",
            "judgment": "它的角色是连接冷暖和正式度，不是抢主角。",
            "result": "边界是厚外套里会鼓，适合单层或薄外搭之间过渡。",
            "constraint": "不写成人人必备。",
        },
        "hidden": {
            "role": "生活场景记录员",
            "object": "深蓝直筒裤",
            "scene": "裤子分别放到通勤衬衫、周末卫衣、雨天短靴三组衣架旁。",
            "action": "先看裤腿和鞋口距离，再看上衣下摆是否压住腰线。",
            "judgment": "它承担的是把上衣风格收稳的角色，不是制造亮点。",
            "result": "边界是厚靴口会顶住裤脚，换低帮鞋更顺。",
            "constraint": "不把衣橱选择写成唯一答案。",
        },
    },
    "CP14": {
        "label": "物性影像与感官短片",
        "dev": {
            "role": "物性影像记录员",
            "object": "砂洗棉裙摆",
            "scene": "裙摆被手指轻轻拨开，边缘回落时有一小段滞后。",
            "action": "只拍布面起伏、指尖停顿和光从褶里滑过去。",
            "judgment": "重点是慢回落的质感，不需要口播解释。",
            "result": "声音只保留布料摩擦和衣架轻响。",
            "constraint": "不强制CTA、不强制spoken。",
        },
        "hidden": {
            "role": "感官影像记录员",
            "object": "细雨后的防泼水帽檐",
            "scene": "帽檐上有三颗水珠，手指从边缘掠过，水珠沿弧线滑到桌面。",
            "action": "镜头贴近水珠、帽檐弧度和桌面小水痕。",
            "judgment": "画面只呈现水珠滑落的速度，不说性能结论。",
            "result": "结尾停在桌面水痕散开的声音。",
            "constraint": "无口播、无CTA。",
        },
    },
    "CP15": {
        "label": "商品到店生命周期",
        "dev": {
            "role": "到店生命周期记录员",
            "object": "新到针织背心箱",
            "scene": "纸箱刚拆开，三件背心先放在待检台，旁边是蒸汽机和挂签。",
            "action": "先核箱单，再蒸汽整理肩线，最后挂到待检区而不是直接上墙。",
            "judgment": "生命周期还没到陈列，只到待检完成前一步。",
            "result": "下一节点是明早复核肩线是否回弹。",
            "constraint": "不声称真实到货量或库存。",
        },
        "hidden": {
            "role": "入店流程记录员",
            "object": "三件亚麻衬衫到店袋",
            "scene": "透明袋上有折痕，第一件肩部压皱，另外两件只需要补挂签。",
            "action": "先拆袋验肩，再蒸汽处理压皱件，最后把三件分到待检与可拍两格。",
            "judgment": "到店流程的重点是分流，不是把所有新货立即上架。",
            "result": "压皱件留待复看，另外两件进入下午拍摄清单。",
            "constraint": "不写真实库存或售卖状态。",
        },
    },
    "CP16": {
        "label": "真实服务复盘",
        "dev": {
            "role": "匿名服务复盘员",
            "object": "遮风需求卡",
            "scene": "需求卡只写怕风、袖口松、试过短围巾，姓名和联系方式被遮住。",
            "action": "先把袖口松量和围巾遮挡范围画在纸上，再记录调整动作。",
            "judgment": "服务判断是先解决风从袖口进的问题，不追问私人经历。",
            "result": "结果证据是袖口收紧后风口位置被遮住，仍需下一次试穿确认。",
            "constraint": "保护隐私，不冒充真实顾客故事。",
        },
        "hidden": {
            "role": "服务动作复盘员",
            "object": "匿名裤长调整卡",
            "scene": "卡片只保留裤脚拖地、鞋跟高度、试走三步三项信息。",
            "action": "先标出裤脚拖地的两厘米，再让裤脚离鞋面半指后复走三步。",
            "judgment": "判断依据是走路时裤脚不再扫地，不是主观说显高。",
            "result": "记录写明仍需坐下复核膝部余量。",
            "constraint": "不写身份、不写真实消费结果。",
        },
    },
    "CP17": {
        "label": "陈列换陈与空间实验",
        "dev": {
            "role": "空间实验记录员",
            "object": "中岛台围巾架",
            "scene": "围巾原来正面叠放，过道显得厚；侧向悬挂后中间露出一掌空隙。",
            "action": "先拍调整前后同一角度，再记录过道空隙和视线停留点。",
            "judgment": "实验目标是让入口更轻，不验证销售变化。",
            "result": "周三只复看围巾是否被频繁翻乱。",
            "constraint": "不写客流提升。",
        },
        "hidden": {
            "role": "换陈实验记录员",
            "object": "门口雨衣与伞架位置",
            "scene": "雨衣原来挂在伞架后面，进门先看到伞柄；换位后雨衣下摆露在门口灯下。",
            "action": "先拍换位前遮挡关系，再拍换位后下摆和伞架距离。",
            "judgment": "这次实验只看入口识别顺序，不判断购买。",
            "result": "复核时间定在下个雨天傍晚，看伞架是否挡住雨衣。",
            "constraint": "不把空间实验写成经营结论。",
        },
    },
    "CP18": {
        "label": "城市门店生活志",
        "dev": {
            "role": "街区生活记录员",
            "object": "架空槐影巷窗边薄风衣",
            "scene": "架空槐影巷午后潮气重，窗边地垫有水印，薄风衣挂在离门半步的位置。",
            "action": "先拍门垫水印，再拍风衣下摆离地和窗边反光。",
            "judgment": "这条生活志讲衣服和架空街区气候的关系，不冒充真实城市档案。",
            "result": "画面留下门口潮气和薄风衣轻摆的关系。",
            "constraint": "不写真实地理标签。",
        },
        "hidden": {
            "role": "门店生活记录员",
            "object": "架空苔桥路雨后橱窗针织衫",
            "scene": "架空苔桥路雨后路面发亮，橱窗里针织衫袖口被风吹得轻轻贴到玻璃。",
            "action": "先拍玻璃上的雨点，再拍袖口贴玻璃和门口灯影。",
            "judgment": "地方感来自架空雨后光线和门店摆位，不来自真实城市名声。",
            "result": "结尾让袖口和玻璃雨点同框。",
            "constraint": "不冒充真实街区运营事实。",
        },
    },
    "CP19": {
        "label": "经营取舍与决策复盘",
        "dev": {
            "role": "经营取舍记录员",
            "object": "周末橱窗位决策板",
            "scene": "决策板写着保留雨衣展示、放弃新包上墙、周二复看三个栏目。",
            "action": "先把两张方案卡放到橱窗位，再抽走新包卡留出雨衣卡。",
            "judgment": "选择雨衣是因为周末天气预报和门口动线更匹配，代价是新包少一次曝光。",
            "result": "后果只记录为周二复看橱窗完整度，不写价值观口号。",
            "constraint": "不做自夸。",
        },
        "hidden": {
            "role": "决策复盘记录员",
            "object": "中岛台主推位选择表",
            "scene": "选择表列着保留薄外套、撤下厚围巾、周五复看温度三项。",
            "action": "先把两件商品卡摆在主推位照片上，再用红笔圈出放弃厚围巾的理由。",
            "judgment": "取舍背景是店内温度和入口轻重，不是哪个商品更高级。",
            "result": "实际代价是围巾少一个正面位置，复看点是周五降温后是否换回。",
            "constraint": "不把经营选择写成品牌价值观。",
        },
    },
    "CP20": {
        "label": "承诺—兑现追踪",
        "dev": {
            "role": "承诺追踪记录员",
            "object": "纽扣复核承诺表",
            "scene": "承诺表写着周一补拍扣距、周三复核、未完成则标出偏差。",
            "action": "先拍周一扣距照片，再拍周三复核格和偏差栏。",
            "judgment": "兑现证据是同一位置被复拍，不是写了一个计划。",
            "result": "如果周三没拍到，就在偏差栏写原因和下一复核时间。",
            "constraint": "不让承诺替代完成。",
        },
        "hidden": {
            "role": "兑现追踪记录员",
            "object": "袖口修线回看表",
            "scene": "表上承诺周二补三针线，周四看袖口是否再松，偏差栏留空。",
            "action": "先拍周二补线位置，再拍周四同一袖口的背面小结。",
            "judgment": "兑现成立只看同一袖口有没有复核证据，不靠一句已经处理。",
            "result": "偏差栏如果发现松线，就写下一次补线方式和时间。",
            "constraint": "不把未验证的承诺写成完成。",
        },
    },
}


STYLE_PROFILES: dict[str, dict[str, str]] = {
    "field_note": {
        "narrative_distance": "close_observation",
        "information_order": "place_object_action",
        "language_register": "plain_record",
        "rhythm": "short_steps",
        "visual_grammar": "handheld_detail",
        "sound_grammar": "ambient_object_sound",
        "ending_mode": "open_next_step",
    },
    "diagnostic_split": {
        "narrative_distance": "role_diagnostic",
        "information_order": "condition_branch_result",
        "language_register": "professional_plain",
        "rhythm": "two_branch",
        "visual_grammar": "comparison_closeup",
        "sound_grammar": "quiet_voice_marker",
        "ending_mode": "bounded_recommendation",
    },
    "process_archive": {
        "narrative_distance": "process_witness",
        "information_order": "before_during_after",
        "language_register": "workbench_note",
        "rhythm": "sequenced",
        "visual_grammar": "stepwise_macro",
        "sound_grammar": "tool_and_fabric",
        "ending_mode": "logged_next_check",
    },
    "life_relation": {
        "narrative_distance": "ordinary_user_adjacent",
        "information_order": "use_scene_boundary",
        "language_register": "living_room_plain",
        "rhythm": "soft_turn",
        "visual_grammar": "wardrobe_relation",
        "sound_grammar": "low_room_tone",
        "ending_mode": "viewer_try_condition",
    },
    "evidence_file": {
        "narrative_distance": "record_keeper",
        "information_order": "metric_limit_next",
        "language_register": "evidence_plain",
        "rhythm": "measured",
        "visual_grammar": "same_angle_retake",
        "sound_grammar": "paper_and_measure",
        "ending_mode": "next_verification",
    },
}


STYLE_SELECTION: dict[str, str] = {
    "CP01": "process_archive",
    "CP02": "field_note",
    "CP03": "process_archive",
    "CP04": "field_note",
    "CP05": "process_archive",
    "CP06": "diagnostic_split",
    "CP07": "diagnostic_split",
    "CP08": "diagnostic_split",
    "CP09": "life_relation",
    "CP10": "evidence_file",
    "CP11": "process_archive",
    "CP12": "evidence_file",
    "CP13": "life_relation",
    "CP14": "field_note",
    "CP15": "process_archive",
    "CP16": "diagnostic_split",
    "CP17": "field_note",
    "CP18": "life_relation",
    "CP19": "evidence_file",
    "CP20": "evidence_file",
}


def cp_ids() -> list[str]:
    return list(CP_BLUEPRINTS)


def material_seed(cp_id: str, phase: str) -> dict[str, Any]:
    item = CP_BLUEPRINTS[cp_id][phase]
    return copy.deepcopy({**CP_BLUEPRINTS[cp_id], "phase": phase, "material": item})


def style_for(cp_id: str, lane: str) -> dict[str, Any]:
    style_id = STYLE_SELECTION[cp_id]
    style = copy.deepcopy(STYLE_PROFILES[style_id])
    if lane == "B":
        style["narrative_distance"] = "ordinary_observer_" + style["narrative_distance"]
        style["information_order"] = "felt_detail_then_boundary_" + style["information_order"]
        style["language_register"] = "near_life_" + style["language_register"]
        style["rhythm"] = "looser_two_turn_" + style["rhythm"]
        style["visual_grammar"] = "viewer_eye_" + style["visual_grammar"]
        style["ending_mode"] = "open_try_condition_" + style["ending_mode"]
    return {"style_id": style_id, **style}


def compose_candidate(authoring_projection: dict[str, Any]) -> dict[str, Any]:
    cp_id = authoring_projection["content_product_type_id"]
    lane = authoring_projection["voice_lane"]
    material = authoring_projection["material_atoms"]
    style = authoring_projection["style_realization_plan"]
    title = _title(cp_id, lane, material)
    body = _body(cp_id, lane, material)
    spoken = _spoken(cp_id, lane, material)
    cta = _cta(cp_id, lane, material)
    visual = _visual_beats(cp_id, lane, material)
    capture = _capture_instructions(cp_id, lane, material)
    audio = _audio(cp_id, lane, material, style)
    editing = _editing(cp_id, lane, style)
    _assert_no_meta([title, *body, *spoken, cta, *visual, *capture, audio, editing])
    return {
        "title": title,
        "body": "\n".join(body),
        "spoken_lines": spoken,
        "CTA": cta,
        "visual_beats": visual,
        "capture_instructions": capture,
        "audio_grammar": audio,
        "editing_grammar": editing,
    }


def _title(cp_id: str, lane: str, material: dict[str, Any]) -> str:
    obj = material["object"]
    titles = {
        "CP01": (f"{obj}先从哪一格开始", f"开门前，{obj}还差一步"),
        "CP02": (f"{obj}里的时段变化", f"雨后进门，先看见{obj}"),
        "CP03": (f"{obj}的三步复位", f"一段{obj}，慢慢回到原位"),
        "CP04": (f"{obj}怎么交到下一只手", f"两个人把{obj}接顺"),
        "CP05": (f"{obj}里的三次变化", f"{obj}不是一句努力"),
        "CP06": (f"{obj}该慢处理的地方", f"{obj}分两处处理更稳"),
        "CP07": (f"{obj}拆成两个判断", f"{obj}不是只有一个答案"),
        "CP08": (f"{obj}背后的结构关系", f"摸到{obj}才知道它怎么工作"),
        "CP09": (f"{obj}适合到哪里为止", f"{obj}也有不用它的时候"),
        "CP10": (f"{obj}只看同一指标", f"{obj}先留在记录里"),
        "CP11": (f"{obj}为什么选这一版", f"{obj}放弃了另一个好处"),
        "CP12": (f"{obj}这次为什么改", f"{obj}改动后还要看哪里"),
        "CP13": (f"{obj}在衣橱里负责什么", f"{obj}不抢主角的时候"),
        "CP14": (f"{obj}落下来的那一下", f"{obj}只让画面说话"),
        "CP15": (f"{obj}还没到上墙那一步", f"{obj}从拆袋到待检"),
        "CP16": (f"{obj}里保留了哪些判断", f"{obj}只讲动作，不讲人"),
        "CP17": (f"{obj}换位后先看什么", f"{obj}只是一次空间实验"),
        "CP18": (f"{obj}和街口的雨光", f"{obj}放在门边才成立"),
        "CP19": (f"{obj}里被放弃的那一项", f"{obj}不是一句价值观"),
        "CP20": (f"{obj}要看兑现证据", f"{obj}不能只留承诺"),
    }
    return titles[cp_id][0 if lane == "A" else 1]


def _body(cp_id: str, lane: str, material: dict[str, Any]) -> list[str]:
    scene = material["scene"]
    action = material["action"]
    judgment = material["judgment"]
    result = material["result"]
    constraint = material["constraint"]
    if lane == "A":
        variants = {
            0: [scene, action, judgment, result],
            1: [action, scene, judgment, result],
            2: [scene, judgment, action, result, constraint],
            3: [action, result, judgment],
        }
    else:
        variants = {
            0: [scene, f"先能看见的是：{action}", judgment, result],
            1: [f"如果只看{material['object']}，最容易漏掉的是这点：{scene}", action, result],
            2: [scene, result, f"这条内容留在一个边界内：{constraint}"],
            3: [action, judgment, f"看完以后，下一步不是下结论，而是：{result}"],
        }
    selector = (int(cp_id[2:]) + (0 if lane == "A" else 2)) % 4
    return variants[selector]


def _spoken(cp_id: str, lane: str, material: dict[str, Any]) -> list[str]:
    if cp_id == "CP14":
        return []
    obj = material["object"]
    if lane == "A":
        options = {
            0: [f"这里先看{obj}的动作顺序。"],
            1: [f"{obj}不是直接下结论，先看依据。", material["judgment"]],
            2: [material["judgment"]],
            3: [f"我会把{obj}的下一步写在记录里。", material["result"]],
        }
    else:
        options = {
            0: [f"我先看见的是{obj}旁边那个小变化。"],
            1: [material["result"]],
            2: [f"这件事先停在{obj}的动作证据上。", material["constraint"]],
            3: [],
        }
    return options[(int(cp_id[2:]) + (1 if lane == "B" else 0)) % 4]


def _cta(cp_id: str, lane: str, material: dict[str, Any]) -> str:
    if cp_id == "CP14":
        return ""
    obj = material["object"]
    actions = {
        "CP01": "下次看同类任务，先问它卡在哪个格子。",
        "CP02": "再看这类时段，别只数人，先看空间留下什么。",
        "CP03": "想判断手艺，先看它有没有按原来的线走完。",
        "CP04": "看协作时，留意交接依据有没有被留下来。",
        "CP05": "看成长记录，找同一动作在不同时间的变化。",
        "CP06": "遇到判断切片，先问依据是不是可被看见。",
        "CP07": "碰到同类问题，先把条件拆成两个分支。",
        "CP08": "看解构内容，顺着结构、材料、结果三步走。",
        "CP09": "看反选指南，重点找它不适合的条件。",
        "CP10": "看证据档案，只认同一指标和下一次复测。",
        "CP11": "看设计取舍，也要看被放弃的好处。",
        "CP12": "看版本迭代，别漏掉触发改动的原因。",
        "CP13": "看衣橱角色，问它和谁搭配时最有用。",
        "CP15": "看到店流程，先确认它走到哪一个节点。",
        "CP16": "看服务复盘，只保留匿名动作和证据。",
        "CP17": "看空间实验，记住它只回答一个观察问题。",
        "CP18": "看门店生活志，先找衣服和街口关系。",
        "CP19": "看决策复盘，别只看选了什么，也看放弃什么。",
        "CP20": "看承诺追踪，回到证据和下一次复核。",
    }
    if lane == "B" and cp_id in {"CP02", "CP09", "CP13", "CP18"}:
        return ""
    return actions.get(cp_id, f"再看{obj}时，先找它的证据。")


def _visual_beats(cp_id: str, lane: str, material: dict[str, Any]) -> list[str]:
    obj = material["object"]
    scene = material["scene"]
    action = material["action"]
    result = material["result"]
    beats = {
        0: [f"固定机位拍{obj}和周围环境。", f"近景跟到动作：{action}", f"收在结果证据：{result}"],
        1: [f"先拍{scene}", f"手部或物件动作进入画面：{action}"],
        2: [f"同角度前后对照{obj}。", f"切到依据细节。", f"最后只留下一项待复核信息。", f"环境声不盖过物件声。"],
        3: [f"从边缘细节切入{obj}。", f"动作发生时保留半秒停顿。", f"结果不做大字总结，只拍证据。"],
        4: [f"俯拍{obj}所在位置。", f"侧拍动作链。", f"特写判断依据。", f"远一点看它和空间的关系。", f"收在下一步记录。"],
    }
    if cp_id == "CP14":
        return [f"微距拍{obj}表面变化。", f"手指动作后停两秒。", f"只留物件声音和光线变化。"]
    return beats[(int(cp_id[2:]) + (1 if lane == "B" else 0)) % 5]


def _capture_instructions(cp_id: str, lane: str, material: dict[str, Any]) -> list[str]:
    return [
        f"只拍{material['object']}、工具、记录卡或空间关系，不拍可识别真人。",
        "每个判断都给一个可见依据镜头。",
    ]


def _audio(cp_id: str, lane: str, material: dict[str, Any], style: dict[str, Any]) -> str:
    if cp_id == "CP14":
        return "保留布料、水珠或衣架轻响；不加解释性旁白。"
    if lane == "A":
        return f"低音量现场声，必要时一句角色旁白；声音重点跟随{material['object']}的动作。"
    return f"保留环境声和物件声；旁白只说明看见的动作，不代替专业角色给结论。"


def _editing(cp_id: str, lane: str, style: dict[str, Any]) -> str:
    if cp_id in {"CP10", "CP12", "CP20"}:
        return "按证据时间点剪辑，同一指标用同一角度，不插入情绪总结。"
    if cp_id == "CP14":
        return "慢切，保留动作前后空隙，不叠结论字幕。"
    if lane == "A":
        return "按动作链剪辑：对象、依据、处理、结果。"
    return "按观察顺序剪辑：先看见什么，再理解边界。"


def _assert_no_meta(parts: list[str]) -> None:
    text = "\n".join(part for part in parts if part)
    for term in FORBIDDEN_META_TERMS:
        if term in text:
            raise ValueError(f"authoring surface contains forbidden metadata term: {term}")
