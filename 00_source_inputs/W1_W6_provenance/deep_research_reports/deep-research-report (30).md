map_id: W6_P0_05_product_role_narrative_knowledge_map
map_version: v0_1
cell_id: W6
prompt_id: WEB-DEEP-RESEARCH-W6-P0-05-PRODUCT-ROLE-NARRATIVE-MAP-001
capability_group_id: P0-05
capability_group_name: 产品角色叙事方法知识地图
output_file: W6_P0_05_product_role_narrative_knowledge_map.yaml
status: research_planning_only

source_inputs:
  pack_id: web_gpt_upload_pack_v0_1
  authority_file: 09_upload_pack_manifest.json
  authority_note: >-
    09_upload_pack_manifest.json 为本轮上传包文件权威；上传包共 9 个文件；readiness_true_count
    为 0；excluded_materials 明确排除了 KE、Serving、RAG、DIFY、旧 route
    history 作为当前 truth。
  required_files_used:
    - file_name: 01_research_charter_and_redlines.md
      applied_for:
        - general_only 知识模式
        - selected P0-00 至 P0-05 scope
        - forbidden outputs redlines
        - readiness 必须保持 false
    - file_name: 02_p0_capability_and_subcards.yaml
      applied_for:
        - P0-05 四张 research subcard 的主题
        - target_count_budget
        - primary_batches 与 secondary_batches
        - forbidden_scope
    - file_name: 03_batch_allocation_matrix.csv
      applied_for:
        - P0-05 关联批次预算引用
        - batch_002、005、006、008、009、011、013、014 的合法性校验
        - count_policy 为 coverage_budget 而非 acceptance_kpi
    - file_name: 04_research_map_output_schema.yaml
      applied_for:
        - top_level_required_fields
        - cluster_required_fields
        - forbidden_object_types
        - readiness_required_false
    - file_name: 05_source_claim_evidence_policy.md
      applied_for:
        - hard claim routing
        - evidence_need 规则
        - instance fact boundary
        - source gap / decision required / excluded routing
    - file_name: 06_candidatepack_and_readiness_policy.md
      applied_for:
        - CandidatePack boundary
        - Four-Gate boundary
        - KE / Serving / RAG / DIFY boundary
        - readiness 全部保持 false
    - file_name: 07_dq_anti_homogeneity_policy.md
      applied_for:
        - anti-empty-language
        - anti-template
        - irreplaceable-anchor
        - filmability
        - platform-native 仅可作为 research hint
    - file_name: 08_optional_reference_digest.md
      applied_for:
        - optional reference only
        - 仅作格式与 redline 辅助，不得覆盖 canonical 约束
  source_precedence_rule:
    - 若 optional reference 与 charter / schema / matrix 冲突，以 charter / schema / matrix 为准。
    - 不得要求用户补传原始 29 个文件。
    - 不得把 optional reference 写成仓内 canonical truth。
  pack_scope_guard:
    knowledge_mode: general_only
    selected_scope_only: true
    not_full_part_a_coverage: true
    allowed_scenario_families:
      - content_generation
      - display_styling
    coordination_view_note: content_x_display 仅为协调视图，不新增第三场景轴。

p0_scope:
  selected_capability_group: P0-05
  capability_group_name: 产品角色叙事方法知识地图
  knowledge_mode: general_only
  scenario_families:
    - content_generation
    - display_styling
  coordination_view: content_x_display
  selected_scope_note: 仅为 selected P0 scope，不得表述为 full Part A coverage。
  not_formal_capability_card: true

research_subcard_refs:
  - research_card_id: P0-05-RS01
    p0_group: P0-05
    theme: product role narrative frame
    target_count_budget: 160
    primary_batches:
      - batch_002
      - batch_005
    secondary_batches:
      - batch_009
    knowledge_focus: product role, scene role, and non-hard-sell narrative structure
    forbidden_scope:
      - real_sku_fact
      - direct_sales_copy
      - unsupported_product_result
    required_cluster_ids:
      - P0-05-RS01-C01
      - P0-05-RS01-C02
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true

  - research_card_id: P0-05-RS02
    p0_group: P0-05
    theme: lifecycle and assortment role
    target_count_budget: 160
    primary_batches:
      - batch_005
      - batch_006
    secondary_batches:
      - batch_013
    knowledge_focus: lifecycle, assortment, channel, and product role boundaries
    forbidden_scope:
      - inventory_fact
      - promotion_fact
      - sales_status_fact
    required_cluster_ids:
      - P0-05-RS02-C01
      - P0-05-RS02-C02
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true

  - research_card_id: P0-05-RS03
    p0_group: P0-05
    theme: scene fit and usage boundary
    target_count_budget: 160
    primary_batches:
      - batch_008
      - batch_009
    secondary_batches:
      - batch_004
    knowledge_focus: scene fit, usage boundary, and source gap conditions
    forbidden_scope:
      - fit_guarantee
      - body_result_claim
      - use_case_fact_without_source
    required_cluster_ids:
      - P0-05-RS03-C01
      - P0-05-RS03-C02
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true

  - research_card_id: P0-05-RS04
    p0_group: P0-05
    theme: cross-domain product relation
    target_count_budget: 160
    primary_batches:
      - batch_011
      - batch_014
    secondary_batches:
      - batch_003
    knowledge_focus: product-to-display, product-to-role, and product-to-narrative relation hints
    forbidden_scope:
      - candidatepack_output
      - serving_passage_body
      - production_content
    required_cluster_ids:
      - P0-05-RS04-C01
      - P0-05-RS04-C02
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true

required_knowledge_clusters:
  - cluster_id: P0-05-RS01-C01
    cluster_name: 产品作为叙事角色的入场框架
    p0_group: P0-05
    research_card_id: P0-05-RS01
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - relation_hint
      - evidence_requirement
    object_type: CapabilityResearchCluster
    definition: >-
      定义产品如何不以真实 SKU 事实、价格、库存、销量为前提，而以“角色功能”“场景任务”“对比位置”“观看顺序”进入叙事；
      研究对象是产品如何成为故事中的角色节点，而不是实例商品说明。
    applies_when: >-
      需要研究产品如何作为故事角色、镜头对象、陈列锚点或教育节点进入内容时适用；尤其适用于非硬卖、非直接叫卖的产品叙事结构。
    does_not_apply_when: >-
      当内容依赖真实商品名称、真实功效、真实顾客反馈、真实门店动作、真实价格库存促销或真实销售状态时不适用。
    counter_boundary: >-
      不得把“角色入场”偷换成商品事实介绍、效果承诺、导购话术或品牌实例案例；如需要实例锚点，转入 source gap 或 decision required。
    output_influence: >-
      影响后续研究如何拆分产品在开场、转场、比较、教育、收束中的角色位次；仅影响研究结构，不生成可发布文案。
    source_dependency: >-
      依赖通用叙事方法、内容结构方法、零售展示与视觉入口方法类来源；不得杜撰真实商品数据，也不得默认实例事实有效。
    evidence_need: >-
      若只讨论方法结构，可使用方法类与教材类来源；一旦出现功效、体感、适配结果、销量、转化提升等硬 claim，必须提升证据等级或转 source gap。
    risk_flags:
      - genericness_risk
      - hard_sell_leakage
      - real_instance_fact_leakage
      - filmability_weakness_if_no_anchor
    duplicate_check_key: p0_05_product_role_entry_frame
    body_structure_consistency_note: >-
      正文结构必须同时写明角色定义、适用条件、不适用条件、反边界、输出影响、证据需求与风险标记，避免空泛方法句。
    domain_module: 产品叙事入口模块
    why_required_for_capability: >-
      P0-05 研究重点要求产品进入叙事的机制；若没有入场框架，后续场景、陈列、CTA 关系都会退化为泛化卖货话术。
    expected_body_topics:
      - 角色功能命名方式
      - 产品在镜头中的首出现位置
      - 产品与场景任务的绑定方式
      - 产品作为对比项、解决项、过渡项的结构位置
      - 产品与叙事节奏的先后关系
      - 去 SKU 化的对象锚点写法
    required_relations:
      - 产品角色 -> 场景任务
      - 产品角色 -> 叙事段落
      - 产品角色 -> 视觉锚点
      - 产品角色 -> 教育节点
      - 产品角色 -> CTA 前置条件
    risk_boundaries:
      - 不得写真实品牌、真实 SKU、真实价格库存
      - 不得写功效结论或身材结果
      - 不得把 narrative frame 变成 direct sales copy
      - 不得把门店实例当作通用事实
    evidence_classes:
      - 通用叙事方法来源
      - 零售展示/视觉营销方法来源
      - 内容结构方法来源
      - 边界政策来源
    source_research_priority: high
    shared_with_capability_cards:
      - P0-01
      - P0-04
    batch_refs:
      primary:
        - batch_002
        - batch_005
      secondary:
        - batch_009
    candidate_output_effect: >-
      为后续候选研究提供“产品以什么角色进入故事”的拆解槽位，帮助形成可检查的 narrative skeleton，而不是产出成稿。
    forbidden_knowledge_leakage:
      - 真实商品名称
      - 真实 SKU 层事实
      - 真实推广语
      - 真实顾客反馈
      - 真实门店陈列效果
    source_gap_likelihood: medium

  - cluster_id: P0-05-RS01-C02
    cluster_name: 从叙事到 CTA 的非硬卖过渡边界
    p0_group: P0-05
    research_card_id: P0-05-RS01
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - routing_hint
      - evidence_requirement
    object_type: CapabilityResearchCluster
    definition: >-
      定义产品叙事如何进入提示性 CTA，而不滑向直接销售文案；核心是 CTA 的出现条件、信息密度、位置边界与禁入信息。
    applies_when: >-
      研究产品叙事收束、导向下一动作、提示比较、了解、查看、延伸阅读等低承诺 CTA 机制时适用。
    does_not_apply_when: >-
      需要真实价格、促销、库存、下单时效、平台玩法、门店活动或销售承诺时不适用。
    counter_boundary: >-
      不得把 CTA 机制写成真实转化话术、真实平台投流策略、真实促销节点或销售 SOP。
    output_influence: >-
      约束后续研究在 CTA 段只保留方法位而不落到具体卖点承诺，降低 production leakage 风险。
    source_dependency: >-
      依赖 CTA 方法论、内容路径设计、平台内容结构来源；凡涉及转化效果或业务 KPI，不得作为通用结论写入。
    evidence_need: >-
      可研究 CTA 位置与信息层级原则；若涉及转化提升、成交率、点击率等事实效果，需独立证据并通常转出本图范围。
    risk_flags:
      - sales_copy_leakage
      - platform_specific_overreach
      - performance_claim_without_evidence
      - readiness_leakage
    duplicate_check_key: p0_05_narrative_to_cta_boundary
    body_structure_consistency_note: >-
      必须同时给出可进入 CTA 的前提、不可进入 CTA 的信息类型、与
      P0-04/P0-01 的关系，避免模板化“结尾带行动号召”空话。
    domain_module: 叙事收束与 CTA 边界模块
    why_required_for_capability: >-
      产品角色叙事若没有 CTA 边界，会直接越界成销售文案或转化承诺，不符合 research-only 边界。
    expected_body_topics:
      - CTA 的前置教育条件
      - CTA 的信息密度控制
      - CTA 与商品事实的隔离
      - CTA 与陈列/场景的连接点
      - CTA 的低承诺动作类型
      - CTA 的禁入字段清单
    required_relations:
      - 叙事完成度 -> CTA 可出现条件
      - 教育节点 -> CTA 信息层级
      - 产品角色 -> CTA 触发方式
      - display cue -> CTA 位置
      - 风险边界 -> 降级路由
    risk_boundaries:
      - 不得写直接下单口播
      - 不得写成交承诺
      - 不得写真实渠道玩法
      - 不得写真实营销节点
    evidence_classes:
      - CTA 方法来源
      - 内容路径设计来源
      - 边界政策来源
    source_research_priority: high
    shared_with_capability_cards:
      - P0-01
      - P0-04
      - P0-00
    batch_refs:
      primary:
        - batch_002
        - batch_005
      secondary:
        - batch_009
    candidate_output_effect: >-
      帮助后续候选研究把 CTA 作为方法节点而非销售句输出，形成非 production-ready 的收束控制。
    forbidden_knowledge_leakage:
      - 真实促销机制
      - 真实下单路径
      - 真实转化 KPI
      - 真实渠道活动
    source_gap_likelihood: high

  - cluster_id: P0-05-RS02-C01
    cluster_name: 产品生命周期阶段的角色窗口
    p0_group: P0-05
    research_card_id: P0-05-RS02
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - boundary_rule
      - source_gap_candidate
    object_type: CapabilityResearchCluster
    definition: >-
      抽象研究产品在生命周期不同阶段可承担的叙事角色窗口，如引入期、解释期、搭配扩展期、维护期、退出/替换提示期；
      只研究方法形态，不写真实上新、库存、售罄或波段事实。
    applies_when: >-
      需要研究生命周期如何改变产品在内容中的角色、信息密度、陈列位置、教育重心时适用。
    does_not_apply_when: >-
      依赖真实上新节奏、库存深度、波段计划、渠道订货、售罄速度或促销清仓事实时不适用。
    counter_boundary: >-
      不得把生命周期阶段直接等同于真实经营状态；所有阶段命名都应保持抽象层，不能倒推出品牌运营事实。
    output_influence: >-
      决定后续研究是否将同一产品角色拆分为不同阶段的不同叙事任务，避免静态化产品叙事。
    source_dependency: >-
      依赖生命周期与零售方法来源、陈列更新方法来源、内容教育节奏来源；业务经营数据不在本图内。
    evidence_need: >-
      方法层允许来自零售通用方法来源；阶段效果、销售变化、库存结构等硬事实必须外置，缺失则进 source gap。
    risk_flags:
      - operational_fact_leakage
      - inventory_inference_risk
      - channel_strategy_overreach
      - false_stage_certainty
    duplicate_check_key: p0_05_lifecycle_role_window
    body_structure_consistency_note: >-
      需显式写明阶段抽象性、与真实运营解耦、以及何时必须降级为 source gap，避免把生命周期写成经营报告。
    domain_module: 生命周期角色窗口模块
    why_required_for_capability: >-
      研究重点明确要求覆盖产品生命周期；该 cluster 负责建立“生命周期改变内容中的角色”这一总框架。
    expected_body_topics:
      - 阶段抽象命名
      - 阶段与叙事密度关系
      - 阶段与教育重心关系
      - 阶段与陈列更新关系
      - 阶段与 CTA 强弱关系
      - 阶段与 source gap 的触发条件
    required_relations:
      - 生命周期阶段 -> 产品角色强度
      - 生命周期阶段 -> 教育内容比重
      - 生命周期阶段 -> 陈列更新提示
      - 生命周期阶段 -> CTA 强度上限
      - 生命周期阶段 -> source gap 触发
    risk_boundaries:
      - 不得写真实上新日期
      - 不得写库存、售罄、滞销事实
      - 不得写真实促销处置
      - 不得写渠道订货结论
    evidence_classes:
      - 零售生命周期方法来源
      - 陈列更新方法来源
      - 内容节奏方法来源
      - 边界政策来源
    source_research_priority: high
    shared_with_capability_cards:
      - P0-04
      - P0-00
    batch_refs:
      primary:
        - batch_005
        - batch_006
      secondary:
        - batch_013
    candidate_output_effect: >-
      使后续研究能在不同生命周期阶段下改变产品叙事任务，构造可比较的 role window，而非生成经营结论。
    forbidden_knowledge_leakage:
      - 真实波段计划
      - 真实库存深浅
      - 真实渠道分货
      - 真实售罄判断
    source_gap_likelihood: high

  - cluster_id: P0-05-RS02-C02
    cluster_name: 组货角色与渠道边界矩阵
    p0_group: P0-05
    research_card_id: P0-05-RS02
    knowledge_type: relation_hint
    knowledge_types:
      - relation_hint
      - boundary_rule
      - decision_required_candidate
    object_type: CapabilityResearchCluster
    definition: >-
      研究产品在组货中可承担的角色关系，如支点项、陪衬项、补位项、对比项、主题承接项，以及这些角色如何在不同渠道表达为不同叙事边界；
      不写真实配货事实。
    applies_when: >-
      需要抽象描述组货如何影响产品被讲述、被摆放、被比较、被引导时适用。
    does_not_apply_when: >-
      需要真实渠道策略、真实门店授权、真实加盟政策、真实分货比重、真实陈列执行结果时不适用。
    counter_boundary: >-
      不得把组货角色矩阵扩展成完整陈列系统、完整渠道运营系统或加盟管理知识库；
      A2 仅可作为 support context。
    output_influence: >-
      帮助后续研究把单一产品从孤立对象转为组货关系中的一个角色节点，增强产品叙事的关系性与差异化。
    source_dependency: >-
      依赖组货与视觉陈列方法、零售角色关系方法、内容选品逻辑方法；凡属于真实经营、授权、配货制度的内容均外置。
    evidence_need: >-
      允许沉淀关系框架；若出现渠道绩效、最佳配比、销售提升、加盟执行成效等内容，必须转出。
    risk_flags:
      - a2_full_system_overreach
      - channel_policy_leakage
      - franchise_fact_leakage
      - template_matrix_risk
    duplicate_check_key: p0_05_assortment_channel_role_matrix
    body_structure_consistency_note: >-
      矩阵类 cluster 必须含角色定义、关系类型、边界、反例与共享卡位，不能只列概念名。
    domain_module: 组货与渠道关系模块
    why_required_for_capability: >-
      研究重点中明确包含组货角色；若缺少该 cluster，产品角色叙事无法解释“为什么这个产品要与别的产品一起被讲”。
    expected_body_topics:
      - 组货角色类型
      - 主次关系与陪衬关系
      - 渠道差异下的信息删减规则
      - 产品角色与主题化组合关系
      - 边界内可研究的渠道表达
      - 与 A2 support-only 的切分点
    required_relations:
      - 组货角色 -> 产品叙事视角
      - 组货角色 -> display 邻接关系
      - 组货角色 -> CTA 信息稀疏度
      - 渠道边界 -> 可使用的信息类型
      - A2 support context -> 边界限制
    risk_boundaries:
      - 不得扩展为完整门店系统
      - 不得写真实渠道战术
      - 不得写真实加盟、授权事实
      - 不得写真实连带销售结论
    evidence_classes:
      - 组货方法来源
      - 零售角色关系来源
      - 视觉陈列方法来源
      - 边界政策来源
    source_research_priority: high
    shared_with_capability_cards:
      - P0-04
      - P0-02
      - P0-00
    batch_refs:
      primary:
        - batch_005
        - batch_006
      secondary:
        - batch_013
    candidate_output_effect: >-
      支持后续研究用“产品之间的角色关系”组织候选内容结构，降低单品空讲的模板化风险。
    forbidden_knowledge_leakage:
      - 真实配货表
      - 真实渠道策略
      - 真实加盟门店制度
      - 真实陈列执行结果
    source_gap_likelihood: medium

  - cluster_id: P0-05-RS03-C01
    cluster_name: 场景适配条件与不适配条件
    p0_group: P0-05
    research_card_id: P0-05-RS03
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - general_method
      - evidence_requirement
    object_type: CapabilityResearchCluster
    definition: >-
      研究产品进入某类场景时，可被描述的条件锚点与不可被描述的效果锚点；核心是“在什么场景中承担什么任务”，而非“对谁一定有效”。
    applies_when: >-
      需要将产品与工作、通勤、居家、社交、移动、切换等抽象场景任务匹配，并控制语言边界时适用。
    does_not_apply_when: >-
      一旦涉及真实人群标签、真实身材保证、真实体感效果、医学化/性能化结论或无证据的使用结果时不适用。
    counter_boundary: >-
      不得把场景适配写成对具体人、具体体型、具体效果的保证；不得从抽象场景直接推具体顾客满意度。
    output_influence: >-
      约束后续研究只沉淀场景条件和任务关系，不沉淀结果承诺，从而保护 general_only 边界。
    source_dependency: >-
      依赖场景叙事方法、任务导向内容方法、零售使用情境方法；不依赖真实用户评价。
    evidence_need: >-
      若仅写场景任务与注意事项，可保持方法层；若涉及 fit guarantee、body result、comfort、performance 结论，必须有更高证据或转 source gap。
    risk_flags:
      - body_result_claim_risk
      - persona_specificity_risk
      - customer_feedback_projection_risk
      - overgeneralized_scene_fit
    duplicate_check_key: p0_05_scene_fit_boundary
    body_structure_consistency_note: >-
      必须同时列出适配条件与不适配条件，避免单向夸大；并给出场景锚点，保证可拍摄但不越界。
    domain_module: 场景适配边界模块
    why_required_for_capability: >-
      研究重点要求覆盖产品进入场景的机制；该 cluster 负责把场景关系沉淀为条件边界，而非效果承诺。
    expected_body_topics:
      - 场景任务锚点
      - 场景切换条件
      - 场景中的动作限制
      - 不适配条件表达
      - 抽象人群与具体人群边界
      - 场景到教育内容的转接
    required_relations:
      - 场景任务 -> 产品角色
      - 场景限制 -> 不适配条件
      - 产品角色 -> 使用说明级教育
      - 场景匹配度 -> CTA 上限
      - 场景表述 -> 风险降级
    risk_boundaries:
      - 不得写真实顾客画像事实
      - 不得写身材、功效保证
      - 不得写无证据舒适、性能结论
      - 不得写真实反馈
    evidence_classes:
      - 场景叙事方法来源
      - 任务导向内容来源
      - 边界政策来源
    source_research_priority: high
    shared_with_capability_cards:
      - P0-02
      - P0-03
      - P0-01
    batch_refs:
      primary:
        - batch_008
        - batch_009
      secondary:
        - batch_004
    candidate_output_effect: >-
      让后续候选研究围绕“场景条件 -> 动作任务 -> 产品角色”而不是“效果保证”展开。
    forbidden_knowledge_leakage:
      - 真实用户场景反馈
      - 真实身材效果
      - 真实功效判断
      - 真实适用人群承诺
    source_gap_likelihood: high

  - cluster_id: P0-05-RS03-C02
    cluster_name: 使用教育与结果 claim 的分界机制
    p0_group: P0-05
    research_card_id: P0-05-RS03
    knowledge_type: evidence_requirement
    knowledge_types:
      - evidence_requirement
      - boundary_rule
      - routing_hint
    object_type: CapabilityResearchCluster
    definition: >-
      研究产品可以被如何教育性说明、演示、提醒、比较，而不跨入身体结果、性能结论、质量耐久度结论等需高证据支持的 claim 区。
    applies_when: >-
      研究产品在内容中承担说明、演示、注意事项、搭配提醒、使用前提等教育性职责时适用。
    does_not_apply_when: >-
      出现效果增强、体感提升、性能优于他项、耐久更高、质量更好、适合特定身体结果等表述时不适用。
    counter_boundary: >-
      不得把教育提示写成结论性评价；不得把镜头演示自动上升为产品功效证明。
    output_influence: >-
      为后续研究建立“可教育说明”与“需证据 claim”之间的拆分规则，减少 unsupported claim 进入 cluster。
    source_dependency: >-
      依赖教育内容方法、风险语言边界、比较方法来源；不能以 GPT 草稿或演绎语句作为证据锚。
    evidence_need: >-
      凡涉 fabric behavior、fit effect、body result、quality、durability、comfort、performance 等均需显式证据支持；无支持则 route away。
    risk_flags:
      - unsupported_claim_risk
      - demo_equals_proof_fallacy
      - quality_inference_risk
      - production_serving_leakage
    duplicate_check_key: p0_05_education_vs_claim_boundary
    body_structure_consistency_note: >-
      本 cluster 必须把“可以教育说明的内容”和“必须转 source gap 的内容”并排列出，避免模糊地带。
    domain_module: 教育内容与 claim 分界模块
    why_required_for_capability: >-
      产品角色叙事很容易滑向产品效果结论；该 cluster 是 P0-05 的核心风控模块。
    expected_body_topics:
      - 教育性说明的允许范围
      - 演示与证明的区别
      - 比较语言的边界
      - 注意事项表达
      - 高风险 claim 清单
      - source gap 触发规则
    required_relations:
      - 教育说明 -> 可接受叙事节点
      - 演示动作 -> 非证明边界
      - 比较关系 -> 证据等级要求
      - claim 类型 -> routing 结果
      - 风险等级 -> founder review
    risk_boundaries:
      - 不得输出产品功效结论
      - 不得输出质量、耐久、舒适、性能结论
      - 不得输出可直接发布比较文案
      - 不得将演示等同证据
    evidence_classes:
      - 证据边界政策来源
      - 教育内容方法来源
      - 比较语言规范来源
    source_research_priority: highest
    shared_with_capability_cards:
      - P0-03
      - P0-00
    batch_refs:
      primary:
        - batch_008
        - batch_009
      secondary:
        - batch_004
    candidate_output_effect: >-
      为后续研究提供强约束路由，把高风险结论隔离出候选方法簇，保持研究图安全。
    forbidden_knowledge_leakage:
      - 真实功效数据
      - 真实性能测试结果
      - 真实质量结论
      - 真实身体效果描述
    source_gap_likelihood: highest

  - cluster_id: P0-05-RS04-C01
    cluster_name: 产品到陈列叙事的关系语法
    p0_group: P0-05
    research_card_id: P0-05-RS04
    knowledge_type: relation_hint
    knowledge_types:
      - relation_hint
      - general_method
      - boundary_rule
    object_type: CapabilityResearchCluster
    definition: >-
      研究产品如何通过位置、邻接、重复、对比、主题色块、层级顺序等一般化 display 关系进入叙事，而不依赖真实门店和真实陈列结果。
    applies_when: >-
      需要把产品角色与陈列动作、视觉层级、主题化分组建立抽象连接时适用。
    does_not_apply_when: >-
      需要真实门店照片、真实导购执行、真实动线数据、真实销售响应或完整陈列系统知识时不适用。
    counter_boundary: >-
      不得把产品到陈列关系语法扩展为完整 display ontology；A2 support-only 仅可提供辅助语义，不能变成独立完整系统。
    output_influence: >-
      帮助后续研究以可视关系而非抽象口号组织产品叙事，提高 filmability 与可检查性。
    source_dependency: >-
      依赖视觉陈列方法、展示层级方法、主题化组合方法；真实门店运营信息不在本图可接受范围。
    evidence_need: >-
      方法层可研究陈列关系语法；涉及门店执行成效、转化结果、真实客流反馈则转出本图范围。
    risk_flags:
      - store_fact_leakage
      - a2_overreach
      - generic_display_language
      - execution_result_inference
    duplicate_check_key: p0_05_product_to_display_grammar
    body_structure_consistency_note: >-
      必须写明产品与陈列关系的可视锚点，如位置、邻接、层级、重复、对比；若无可视锚点则为弱 cluster。
    domain_module: 产品-陈列关系语法模块
    why_required_for_capability: >-
      研究重点要求覆盖产品进入陈列机制；此 cluster 负责把产品角色翻译成可视结构关系。
    expected_body_topics:
      - 位置关系
      - 邻接关系
      - 主次层级
      - 主题化组合
      - 颜色、材质、轮廓在陈列中的抽象关系
      - 产品与陈列转场接口
    required_relations:
      - 产品角色 -> display 位置
      - 产品角色 -> 邻接对象
      - grouping rule -> narrative emphasis
      - display cue -> 拍摄镜头线索
      - display relation -> CTA 前置条件
    risk_boundaries:
      - 不得写真实门店案例
      - 不得写完整 display 系统
      - 不得写陈列执行 SOP
      - 不得写真实客流、成交推断
    evidence_classes:
      - 视觉陈列方法来源
      - 展示层级方法来源
      - 主题化组合方法来源
      - 边界政策来源
    source_research_priority: high
    shared_with_capability_cards:
      - P0-04
      - P0-03
    batch_refs:
      primary:
        - batch_011
        - batch_014
      secondary:
        - batch_003
    candidate_output_effect: >-
      为后续研究输出产品与 display 的关系槽位，使内容具备可视结构但不落到门店实例。
    forbidden_knowledge_leakage:
      - 真实门店照片事实
      - 真实陈列动作 SOP
      - 真实导购执行反馈
      - 真实展示结果数据
    source_gap_likelihood: medium

  - cluster_id: P0-05-RS04-C02
    cluster_name: 产品到角色到叙事的跨域关系图
    p0_group: P0-05
    research_card_id: P0-05-RS04
    knowledge_type: relation_hint
    knowledge_types:
      - relation_hint
      - routing_hint
      - decision_required_candidate
    object_type: CapabilityResearchCluster
    definition: >-
      研究产品如何同时与角色语言、组织生态视角、内容叙事轴发生关系，形成“产品 -> 角色视角 -> 叙事功能 -> CTA/Display”的跨域语义图。
    applies_when: >-
      需要跨 P0-01、P0-02、P0-04 连接产品叙事，且仍保持 general_only 与 research-only 边界时适用。
    does_not_apply_when: >-
      需要真实人物经历、真实组织流程、真实门店岗位话术、真实渠道战术或 production-ready 脚本时不适用。
    counter_boundary: >-
      不得把跨域关系图写成正式 capability composition 规则引擎、Serving projection 或 DIFY workflow；此处仅保留 relation hints。
    output_influence: >-
      为后续研究提供跨卡共享语义节点，减少不同 capability 各自孤立、重复或冲突建模。
    source_dependency: >-
      依赖跨域关系规则、角色表达方法、叙事结构方法与 display 关系来源；实现细则与 runtime 归 P0-00 及后续授权路径。
    evidence_need: >-
      只可沉淀关系型 hint；凡涉及运行逻辑、路由引擎、生成器配置、平台投放效果，一律不在本图。
    risk_flags:
      - p0_00_control_plane_leakage
      - serving_projection_leakage
      - dify_workflow_leakage
      - ontology_conflict_risk
    duplicate_check_key: p0_05_cross_domain_product_relation_map
    body_structure_consistency_note: >-
      必须明确哪些只是 relation hint，哪些需要 decision required；不得把研究子卡写成正式 capability card 或实现设计。
    domain_module: 跨域关系映射模块
    why_required_for_capability: >-
      产品角色叙事天然跨越 narrative、role、display；如果没有跨域关系图，P0-05 会出现重复研究与冲突命名。
    expected_body_topics:
      - 产品与角色语气的关系
      - 产品与组织生态视角的连接
      - 产品与 display 动作的接口
      - 产品与 narrative arc 的关系
      - 跨卡共享命名
      - 冲突时的 strictest-wins 提示
    required_relations:
      - 产品角色 -> P0-01 叙事轴
      - 产品角色 -> P0-02 角色视角
      - 产品角色 -> P0-04 陈列动作
      - cross-domain conflict -> P0-00 decision required
      - 共享节点 -> merge 建议
    risk_boundaries:
      - 不得写 runtime artifact
      - 不得写 workflow
      - 不得写 approved passage body
      - 不得写正式 capability composition 规则
    evidence_classes:
      - 跨域关系规则来源
      - 角色表达方法来源
      - 叙事结构来源
      - 边界政策来源
    source_research_priority: high
    shared_with_capability_cards:
      - P0-01
      - P0-02
      - P0-04
      - P0-00
    batch_refs:
      primary:
        - batch_011
        - batch_014
      secondary:
        - batch_003
    candidate_output_effect: >-
      支持后续候选研究按共享节点合并，减少同名异义和重复 cluster，但不产生生产可用编排件。
    forbidden_knowledge_leakage:
      - workflow 设计
      - serving 字段
      - RAG bundle
      - 真实角色故事
    source_gap_likelihood: medium

relation_hints:
  - relation_id: RH-P0-05-01
    from_cluster: P0-05-RS01-C01
    to_cluster: P0-05-RS03-C01
    relation_type: precondition
    hint: 产品先以角色入场，再根据场景任务决定适配条件；不能先给出场景效果承诺再反推角色。

  - relation_id: RH-P0-05-02
    from_cluster: P0-05-RS02-C01
    to_cluster: P0-05-RS01-C02
    relation_type: constraint
    hint: 生命周期阶段会限制 CTA 强度与信息密度；越接近经营事实的阶段描述，越应降级或转 source gap。

  - relation_id: RH-P0-05-03
    from_cluster: P0-05-RS02-C02
    to_cluster: P0-05-RS04-C01
    relation_type: support_context
    hint: 组货角色为 display 关系提供原因解释，但不得扩展成完整陈列系统。

  - relation_id: RH-P0-05-04
    from_cluster: P0-05-RS03-C02
    to_cluster: P0-05-RS01-C02
    relation_type: strictest_wins
    hint: 凡 CTA 处出现质量、功效、身材、舒适、性能等结果性语言，以证据边界更严格的 RS03-C02 为准。

  - relation_id: RH-P0-05-05
    from_cluster: P0-05-RS04-C02
    to_cluster: P0-00
    relation_type: decision_required_handoff
    hint: 跨域关系若触及 control-plane、runtime、workflow 或 ontology ownership，则转 P0-00 decision required。

  - relation_id: RH-P0-05-06
    from_cluster: P0-05-RS04-C02
    to_capability_group: P0-01/P0-02/P0-04
    relation_type: shared_cluster_merge_hint
    hint: 仅共享命名、关系节点与边界，不共享实例事实、脚本、店务或人物材料。

source_gap_items:
  - gap_id: SG-P0-05-01
    object_type: SourceGapItem
    title: 生命周期阶段与真实经营状态之间缺乏可安全泛化的桥接来源
    why_gap: >-
      多数阶段语义在实际使用中会牵连真实上新、库存、销售状态或渠道计划，难以仅凭 general-only 直接下结论。
    affected_clusters:
      - P0-05-RS02-C01
    route: source_gap
    suggested_next_source_types:
      - 零售生命周期方法来源
      - 陈列更新方法来源
      - 风险边界政策来源

  - gap_id: SG-P0-05-02
    object_type: SourceGapItem
    title: 组货角色与渠道边界常被实例运营事实污染
    why_gap: >-
      组货关系容易被误写成真实分货、加盟、授权、陈列执行制度。
    affected_clusters:
      - P0-05-RS02-C02
      - P0-05-RS04-C01
    route: source_gap
    suggested_next_source_types:
      - 组货方法来源
      - 视觉陈列方法来源
      - 渠道边界方法来源

  - gap_id: SG-P0-05-03
    object_type: SourceGapItem
    title: 场景适配表达与身材、功效、性能结果表达之间存在高混淆风险
    why_gap: >-
      很多常见表述会从场景任务自然滑向穿着效果、舒适度、性能或身体结果。
    affected_clusters:
      - P0-05-RS03-C01
      - P0-05-RS03-C02
    route: source_gap
    suggested_next_source_types:
      - 场景叙事方法来源
      - 证据边界政策来源
      - 高风险语言清单来源

  - gap_id: SG-P0-05-04
    object_type: SourceGapItem
    title: 叙事到 CTA 的有效机制缺少可直接沿用的通用证据模板
    why_gap: >-
      CTA 效果常依赖平台、渠道、受众和业务上下文，难以抽象为稳定普遍规律。
    affected_clusters:
      - P0-05-RS01-C02
    route: source_gap
    suggested_next_source_types:
      - CTA 方法来源
      - 内容结构来源
      - 平台无关内容路径来源

  - gap_id: SG-P0-05-05
    object_type: SourceGapItem
    title: 产品到 display 的关系语法与完整 display ontology 的边界仍需持续校准
    why_gap: >-
      研究对象允许使用 A2 support context，但不授权完整系统建模，边界容易漂移。
    affected_clusters:
      - P0-05-RS04-C01
      - P0-05-RS04-C02
    route: source_gap_or_decision_required
    suggested_next_source_types:
      - 视觉陈列通用方法来源
      - 跨域关系规则来源
      - 边界政策来源

decision_required_items:
  - decision_id: DR-P0-05-01
    object_type: DecisionRequiredItem
    title: 生命周期阶段命名粒度是否统一为抽象阶段族
    decision_question: 是否只允许使用抽象阶段族命名，禁止更细经营阶段词汇，以避免误入真实运营事实。
    why_decision_required: 阶段命名越细，越可能携带上新、清货、库存等经营含义。
    affected_clusters:
      - P0-05-RS02-C01
    default_until_resolved: 采用抽象阶段族，不写细经营词。

  - decision_id: DR-P0-05-02
    object_type: DecisionRequiredItem
    title: 组货角色与 A2 support-only 的切分边界
    decision_question: P0-05 可研究的组货、陈列关系语法上限在哪里，何时必须停在 support context 而不能进入完整 display system。
    why_decision_required: 跨域扩张极易把 support-only 误写为完整陈列系统。
    affected_clusters:
      - P0-05-RS02-C02
      - P0-05-RS04-C01
    default_until_resolved: 仅允许 relation hint，不允许系统化 ontology。

  - decision_id: DR-P0-05-03
    object_type: DecisionRequiredItem
    title: CTA 术语口径是否统一降级为动作提示
    decision_question: 是否在研究图中统一弱化 CTA 为“动作提示、下一步提示”，以进一步防止 direct sales copy leakage。
    why_decision_required: CTA 一词容易被执行层误读为销售动作。
    affected_clusters:
      - P0-05-RS01-C02
    default_until_resolved: 保留 CTA 术语，但所有定义按低承诺动作提示解释。

  - decision_id: DR-P0-05-04
    object_type: DecisionRequiredItem
    title: 跨域关系图的命名归属与冲突处理
    decision_question: 跨域关系命名冲突出现时，由 P0-05 内部临时命名，还是统一交由 P0-00 strictest-wins 决策。
    why_decision_required: 避免 P0-05 自行扩张为控制平面。
    affected_clusters:
      - P0-05-RS04-C02
    default_until_resolved: 冲突即上交 P0-00，不在 P0-05 内部固化。

excluded_items:
  - excluded_id: EX-P0-05-01
    object_type: ExcludedResearchItem
    title: 真实品牌、真实 SKU、真实商品名、真实价格库存促销销量事实
    reason: 属于 instance fact，超出 general_only。
    route: excluded

  - excluded_id: EX-P0-05-02
    object_type: ExcludedResearchItem
    title: 可直接发布的产品口播稿、货盘文案、详情页文案、直播话术
    reason: 属于 publishable 或 production-ready 内容，不是 research map。
    route: excluded

  - excluded_id: EX-P0-05-03
    object_type: ExcludedResearchItem
    title: 真实门店 SOP、真实渠道策略、真实加盟授权制度
    reason: 属于运营实例和系统执行知识，超出当前包授权。
    route: excluded

  - excluded_id: EX-P0-05-04
    object_type: ExcludedResearchItem
    title: CandidatePack、KE、Serving projection、RAG context bundle、DIFY workflow、approved_passage_text
    reason: 被 charter、schema 与 readiness policy 明确禁止。
    route: excluded

shared_cluster_merge_items:
  - merge_id: SCM-P0-05-01
    object_type: SharedClusterMergeCandidate
    shared_cluster_candidate: 产品角色入场框架
    merge_with:
      - P0-01 narrative structure
    merge_rule_hint: 只共享叙事段落与角色位次，不共享品牌故事事实或可发布表达。

  - merge_id: SCM-P0-05-02
    object_type: SharedClusterMergeCandidate
    shared_cluster_candidate: 产品到陈列关系语法
    merge_with:
      - P0-04 display/action contentization
    merge_rule_hint: 只共享视觉关系与动作接口，不共享门店执行事实。

  - merge_id: SCM-P0-05-03
    object_type: SharedClusterMergeCandidate
    shared_cluster_candidate: 教育内容与 claim 分界机制
    merge_with:
      - P0-03 process/material/quality story
      - P0-00 evidence routing
    merge_rule_hint: P0-05 只保留产品角色层风险边界，不接管材料、性能证据裁定权。

  - merge_id: SCM-P0-05-04
    object_type: SharedClusterMergeCandidate
    shared_cluster_candidate: 产品到角色到叙事的跨域关系图
    merge_with:
      - P0-02 role perspective
      - P0-00 composition/conflict
    merge_rule_hint: 交叉节点可共享，控制平面规则不可在 P0-05 内落地。

founder_review_items:
  - founder_review_id: FR-P0-05-01
    title: 任何将产品场景适配写成身体结果、舒适、性能结论的倾向
    trigger: 出现 body result、comfort、performance、quality、durability 等高风险结论词。
    suggested_action: 立即降级为 founder review 与 source gap。

  - founder_review_id: FR-P0-05-02
    title: 任何将组货、渠道关系写成真实经营建议的倾向
    trigger: 出现真实库存、促销、加盟、授权、渠道分货等信息。
    suggested_action: 停止沉淀为 cluster，转 decision required 或 excluded。

  - founder_review_id: FR-P0-05-03
    title: 任何将跨域关系 hint 落成 workflow、serving、runtime 设计的倾向
    trigger: 出现字段映射、工作流节点、运行时消费关系、上下文打包等描述。
    suggested_action: 标记控制平面泄漏，转 P0-00 或 excluded。

required_execution_asset_types:
  - research_question_matrix
  - cluster_boundary_sheet
  - applies_vs_not_applies_examples_generalized
  - relation_graph_stub
  - source_gap_register
  - decision_required_register
  - duplicate_cluster_checklist
  - dq_anchor_checklist
  - negative_example_pack_generalized
  - shared_cluster_merge_note

required_dq_checks:
  - 每个 cluster 必须同时包含定义、适用条件、不适用条件、反边界、输出影响、证据需求、风险标记，避免空泛重要性陈述。
  - 每个 cluster 必须出现服装、零售语境下的对象、动作、场景、关系、约束锚点，避免可套用于任何行业的模板句。
  - 每个 cluster 至少包含一个可视或可执行锚点，如角色入场、比较动作、陈列关系、场景任务、CTA 前置条件，以保证 filmability。
  - 涉及 claim 的 cluster 必须显式区分方法层与证据层，不能让 GPT 草稿充当 source anchor。
  - 出现真实品牌、真实人物、真实门店、真实 SKU、真实顾客反馈时，必须 route away，不得作为一般知识吸收。
  - 不得把 research_subcard 误写成正式 capability card；不得把 coverage budget 写成 acceptance KPI。
  - 不得把 optional reference 写成 canonical truth；若冲突，以 charter、schema、matrix 为准。

fallback_conditions:
  - 若无法安全证明某产品角色表达不含实例事实，则退回到更抽象的角色方法与边界描述。
  - 若场景适配容易滑向效果承诺，则仅保留场景任务与注意事项，不保留结果性语言。
  - 若组货、渠道关系无法与真实经营策略切割，则仅保留产品之间的相对角色关系。
  - 若 CTA 研究不可避免依赖真实转化机制，则仅保留下一步动作提示的抽象边界。
  - 若跨域关系命名发生冲突，则保留 relation hint，不固化命名，转 unresolved_decisions。

blocking_conditions:
  - 发现真实品牌、真实 SKU、真实商品名、真实门店、真实人物、真实顾客反馈。
  - 发现任何 readiness 被置为 true。
  - 发现 CandidatePack、KE、Serving、RAG、DIFY、approved_passage_text 或 publishable script 形态输出。
  - 发现把 P0-05 子卡上升为正式 capability card。
  - 发现把 A2 support-only 误写成完整陈列系统。
  - 发现把 coverage budget 写成验收 KPI。

unresolved_decisions:
  - CTA 术语是否应在后续 intake 阶段统一改写为动作提示，以继续降低执行层误用风险。
  - 生命周期阶段是否需要统一成更少的抽象层级，以降低与真实经营状态的映射风险。
  - 组货关系与陈列关系的共享命名由 P0-05 提供临时名称，还是完全依赖后续 merge 决策。
  - 跨域关系图中的 strictest-wins 提示是否仅保留文本提示，还是需要最小化结构字段。

source_gap_seed:
  - seed_id: SGS-P0-05-01
    seed_question: 产品进入叙事时，哪些“角色功能”命名既能保持可拍摄锚点，又不会偷渡真实商品事实。
    intended_clusters:
      - P0-05-RS01-C01

  - seed_id: SGS-P0-05-02
    seed_question: 生命周期阶段在通用零售方法中，哪些只属于抽象内容节奏，哪些一旦细化就会指向真实经营事实。
    intended_clusters:
      - P0-05-RS02-C01

  - seed_id: SGS-P0-05-03
    seed_question: 组货角色有哪些可一般化的相对关系语法，而不依赖真实货盘、分货和门店执行事实。
    intended_clusters:
      - P0-05-RS02-C02

  - seed_id: SGS-P0-05-04
    seed_question: 场景适配表达如何停留在任务、限制层，而不越界到身材、舒适、性能、功效等结果 claim。
    intended_clusters:
      - P0-05-RS03-C01
      - P0-05-RS03-C02

  - seed_id: SGS-P0-05-05
    seed_question: 产品到 display 的关系语法中，哪些视觉锚点具有跨场景复用性，且不会暗含真实门店执行效果。
    intended_clusters:
      - P0-05-RS04-C01

forbidden_output_attestation:
  attestation: >-
    本输出仅为 Knowledge Research Map，不生成 CandidatePack、Source Pack、KE、Serving Projection、
    RAG context_bundle、DIFY workflow、approved_passage_text 或任何 production-ready 知识；不写真实品牌、
    真实 SKU、真实门店、真实人物、真实顾客反馈；所有 readiness 保持 false。
  not_formal_capability_card: true
  not_candidatepack: true
  not_source_pack: true
  not_KE: true
  not_serving_projection: true
  not_rag_context_bundle: true
  not_dify_workflow: true
  not_approved_passage_text: true
  not_production_ready_knowledge: true

readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false

self_check:
  schema_required_fields_present: true
  covers_all_required_subcards:
    - P0-05-RS01
    - P0-05-RS02
    - P0-05-RS03
    - P0-05-RS04
  cluster_count: 8
  cluster_distribution_by_subcard:
    P0-05-RS01: 2
    P0-05-RS02: 2
    P0-05-RS03: 2
    P0-05-RS04: 2
  all_readiness_false: true
  real_instance_fact_included: false
  batches_outside_matrix_added: false
  p0_scope_outside_selected_range: false
  candidatepack_or_production_output_present: false
  count_used_as_acceptance_kpi: false
  a2_support_only_overreach_detected: false
  notes:
    - 已覆盖 P0-05 下 4 张 research subcard。
    - 每个 cluster 均包含 schema 要求字段与任务追加字段。
    - 输出维持 research_planning_only 语义，不构成正式 capability card 或生产资产。
    - 对不确定项已写入 unresolved_decisions 或 source_gap_seed。