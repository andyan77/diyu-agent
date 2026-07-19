"""Public market references frozen for the 20-product qualification."""

from __future__ import annotations

import dataclasses
from typing import Final


@dataclasses.dataclass(frozen=True)
class MarketReference:
    """One public reference and its truthful publication metadata."""

    product_id: str
    title: str
    publisher: str
    url: str
    published_date: str
    summary: str
    comparability: str
    content_format: str


MARKET_REFERENCES: Final = (
    MarketReference(
        "CP01",
        "A day in the life of a Trainee Merchandiser at NEXT",
        "NEXT",
        "https://www.linkedin.com/posts/"
        "lifeatnext_a-day-in-the-life-of-a-trainee-merchandiser-activity-7186683784090525696-so41",
        "2024-04-18",
        "跟随两名见习商品人员完成服装零售岗位的一天，以实际任务呈现岗位内容。",
        "同为服装零售商品岗位的单日工作流程视频。",
        "短视频",
    ),
    MarketReference(
        "CP02",
        "The Retail Life",
        "Patagonia / Craig Holloway",
        "https://www.patagonia.com/stories/culture/community/the-retail-life/story-19765.html",
        "2009-07-24",
        "以开店前叠衣、闭店结账和顾客片段表现门店时段生活。",
        "围绕明确营业时段和小事件，不是泛化门店宣传。",
        "图文",
    ),
    MarketReference(
        "CP03",
        "53rd Collection",
        "Balenciaga",
        "https://www.balenciaga.com/en-us/53rd-collection",
        "SOURCE_DOES_NOT_STATE",
        "逐层呈现高级定制服装手绘工艺及投入时间。",
        "聚焦单一手艺、连续步骤和时间成本。",
        "短视频",
    ),
    MarketReference(
        "CP04",
        "The Lines That Connect Us",
        "adidas / Ken Tseng",
        "https://www.adidas-group.com/en/magazine/behind-the-scenes/"
        "the-lines-that-connect-us-how-cross-functional-teamwork-made-the-adidas-zne-relaunch-a-reality",
        "2024-11-27",
        "设计、产品、传播、零售、社媒及工厂围绕一次产品重启协同。",
        "角色、交接、困难和共同结果均可追踪。",
        "图文",
    ),
    MarketReference(
        "CP05",
        "From Apprentice to Senior Manager",
        "adidas / Niklas Bohne",
        "https://www.adidas-group.com/en/magazine/innovation/"
        "from-apprentice-to-senior-manager-my-journey-as-a-shoemaker-at-adidas",
        "2025-01-20",
        "主人公从制鞋学徒成长为鞋类开发高级经理，以作品和岗位转换串联轨迹。",
        "具有人物弧线、技能身份和长期成长节点。",
        "图文",
    ),
    MarketReference(
        "CP06",
        "Field Notes from a Gear Tester",
        "Patagonia / Jenny Abegg",
        "https://www.patagonia.com/stories/sports/field-notes-from-a-gear-tester/story-155802.html",
        "2025-02-21",
        "测试员从袖口起球、背包压点和口袋突起等细节作判断并反馈设计。",
        "同为由可见细节、判断理由和适用限制组成的专业解释图文。",
        "图文",
    ),
    MarketReference(
        "CP07",
        "Tightness Across the Shirt’s Back When Reaching Forward",
        "Proper Cloth",
        "https://propercloth.com/reference/tightness-across-the-back-when-reaching-forward/",
        "SOURCE_DOES_NOT_STATE",
        "从前伸时后背过紧的症状出发，给出多种调整方案及外观代价。",
        "同为包含症状、成因诊断、解法和取舍边界的建议图文。",
        "图文",
    ),
    MarketReference(
        "CP08",
        "How Does Waterproof Rain Gear Work?",
        "REI Co-op / Ken Knapp",
        "https://www.rei.com/learn/expert-advice/rainwear-how-it-works.html",
        "SOURCE_DOES_NOT_STATE",
        "拆解防水膜、涂层、透湿机制和不同层数结构。",
        "同为解释材料、结构与使用影响逻辑的解构图文。",
        "图文",
    ),
    MarketReference(
        "CP09",
        "How to Choose Rainwear",
        "REI Co-op / Ken Knapp",
        "https://www.rei.com/learn/expert-advice/rainwear.html",
        "2025-06-13",
        "按天气、活动、预算和结构选择雨具，并明确多种反选条件。",
        "同为说明选什么、何时不要选及替代方向的指南图文。",
        "图文",
    ),
    MarketReference(
        "CP10",
        "Worn Wear: The Hand-Me-Down",
        "Patagonia / Shari Williamson",
        "https://www.patagonia.com/stories/culture/worn-wear/worn-wear-the-hand-me-down/story-18131.html",
        "2013-05-13",
        "一件抓绒衣经过长期户外使用并在多名儿童间传递。",
        "对象、使用年限、用户链和磨损经历可追踪。",
        "图文",
    ),
    MarketReference(
        "CP11",
        "Alpine Suit",
        "Patagonia / MaiLee Hung",
        "https://www.patagonia.com/stories/culture/design/alpine-suit/story-145885.html",
        "2023-12-13",
        "从使用痛点出发，经历多年实验并处理材料、结构和制造取舍。",
        "痛点、原型、约束和取舍共同解释产品诞生。",
        "图文",
    ),
    MarketReference(
        "CP12",
        "From Prototype to the Pitch",
        "adidas / Hannes Schäfke、Harry Miles",
        "https://www.adidas-group.com/en/magazine/innovation/"
        "from-prototype-to-the-pitch-how-we-created-a-football-supershoe",
        "2024-09-11",
        "展示初始模型、功能原型、版本迭代和测试反馈。",
        "版本、变更、验证方法及原因均显式记录。",
        "图文",
    ),
    MarketReference(
        "CP13",
        "What Makes A Great Wardrobe Staple?",
        "Saint + Sofia",
        "https://euro.saintandsofia.com/blogs/style/what-makes-a-great-wardrobe-staple",
        "2025-02-05",
        "讨论基础单品如何跨越工作、周末和季节并形成长期衣橱角色。",
        "关注产品在真实生活和长期衣橱中的位置。",
        "图文",
    ),
    MarketReference(
        "CP14",
        "Fashion Film - Only Vimal",
        "Vimal / matt wilson films",
        "https://vimeo.com/210717663",
        "SOURCE_DOES_NOT_STATE",
        "60秒影像通过运动、光线和声音展示面料的褶皱防护等可见属性。",
        "同为以面料物性、动作和感官画面承担表达的短视频。",
        "短视频",
    ),
    MarketReference(
        "CP15",
        "Macy’s Supply Chain: Behind-The-Scenes",
        "Macy’s, Inc.",
        "https://vimeo.com/993585494",
        "SOURCE_DOES_NOT_STATE",
        "展示仓储团队怎样让商品按时完好到达门店或顾客。",
        "同为服装零售商品从后台到门店端的状态流转视频。",
        "短视频",
    ),
    MarketReference(
        "CP16",
        "Stitch in Time",
        "Patagonia / Brad Wieners",
        "https://www.patagonia.com/stories/culture/worn-wear/stitch-in-time/story-95186.html",
        "2021-01-12",
        "记录一件旧衬衫二次维修、延误、交付和结果。",
        "同为需求、受理、异常、调整和结果完整呈现的服务复盘图文。",
        "图文",
    ),
    MarketReference(
        "CP17",
        "The 5 Steps of Visual Merchandising at M&S",
        "Marks & Spencer Careers",
        "https://jobs.marksandspencer.com/our-stories/visual-merchandising",
        "2025-01-16",
        "视觉陈列团队以五步把时装系列转化为门店展示。",
        "同为陈列假设、调整步骤和空间结果组成的门店实践图文。",
        "图文",
    ),
    MarketReference(
        "CP18",
        "Covent Garden: A Love Affair",
        "Saint + Sofia",
        "https://uk.saintandsofia.com/blogs/culture/covent-garden-a-love-affair",
        "2024-11-13",
        "从街区晨昏、文化场所和本地氛围切入，将门店放进城市生活。",
        "城市、社区与门店共同成为主角。",
        "图文",
    ),
    MarketReference(
        "CP19",
        "Bring Back Clean Climbing",
        "Patagonia / MaiLee Hung",
        "https://www.patagonia.com/stories/sports/climbing/bring-back-clean-climbing/story-116308.html",
        "2022-02-04",
        "回看停用畅销岩钉、转向清洁攀登装备的企业经营决定及影响。",
        "同为品牌企业故事中的选项、取舍、代价、结果和反思。",
        "图文",
    ),
    MarketReference(
        "CP20",
        "Our Targets",
        "adidas",
        "https://www.adidas-group.com/en/sustainability/our-gameplan/our-targets",
        "SOURCE_DOES_NOT_STATE",
        "并列目标基线、目标年度、实际结果和完成状态。",
        "承诺、量化口径、当前证据和兑现状态可核对。",
        "图文",
    ),
)
