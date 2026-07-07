map_id: W2_P0_01_enterprise_narrative_knowledge_map
map_version: v0_1
status: research_planning_only
cell_id: W2
prompt_id: WEB-DEEP-RESEARCH-W2-P0-01-ENTERPRISE-NARRATIVE-MAP-001
knowledge_mode: general_only
output_file: W2_P0_01_enterprise_narrative_knowledge_map.yaml
not_formal_capability_card: true
not_registry: true
not_candidatepack: true
not_KE: true

source_inputs:
  pack_id: web_gpt_upload_pack_v0_1
  manifest_authority_file: 09_upload_pack_manifest.json
  upload_file_count: 9
  required_files_loaded:
    - 01_research_charter_and_redlines.md
    - 02_p0_capability_and_subcards.yaml
    - 03_batch_allocation_matrix.csv
    - 04_research_map_output_schema.yaml
    - 05_source_claim_evidence_policy.md
    - 06_candidatepack_and_readiness_policy.md
    - 07_dq_anti_homogeneity_policy.md
    - 08_optional_reference_digest.md
    - 09_upload_pack_manifest.json
  source_precedence_rules:
    - 如 optional reference 与 charter / schema / matrix 冲突，以 charter / schema / matrix 为准
    - 09_upload_pack_manifest.json 是本轮上传包文件权威
    - optional reference 仅作结构参考，不得写成 canonical truth
    - selected P0 scope 不得表述为 full Part A coverage
  source_trace_refs:
    manifest: "fileciteturn0file0"
    charter_and_redlines: "fileciteturn0file1"
    source_claim_evidence_policy: "fileciteturn0file2"
    candidatepack_and_readiness_policy: "fileciteturn0file3"
    dq_anti_homogeneity_policy: "fileciteturn0file4"
    optional_reference_digest: "fileciteturn0file5"

p0_scope:
  - P0-01

research_subcard_refs:
  - research_card_id: P0-01-RS01
    theme: enterprise narrative structure
    target_count_budget: 120
    primary_batches:
      - batch_009
      - batch_007
    secondary_batches:
      - batch_013
    knowledge_focus: reusable enterprise narrative patterns without real brand facts
    required_knowledge_clusters:
      - W2-P0-01-RS01-CL01
      - W2-P0-01-RS01-CL02
    status: research_planning_only
    not_formal_capability_card: true
  - research_card_id: P0-01-RS02
    theme: brand story method boundary
    target_count_budget: 120
    primary_batches:
      - batch_009
      - batch_005
    secondary_batches:
      - batch_002
    knowledge_focus: story arcs, value expression, and source requirements
    required_knowledge_clusters:
      - W2-P0-01-RS02-CL01
      - W2-P0-01-RS02-CL02
    status: research_planning_only
    not_formal_capability_card: true
  - research_card_id: P0-01-RS03
    theme: anti-homogeneity narrative rules
    target_count_budget: 120
    primary_batches:
      - batch_010
      - batch_011
    secondary_batches:
      - batch_014
    knowledge_focus: differentiation rules that prevent generic enterprise narratives
    required_knowledge_clusters:
      - W2-P0-01-RS03-CL01
      - W2-P0-01-RS03-CL02
    status: research_planning_only
    not_formal_capability_card: true
  - research_card_id: P0-01-RS04
    theme: topic and series planning
    target_count_budget: 120
    primary_batches:
      - batch_007
      - batch_009
    secondary_batches:
      - batch_012
    knowledge_focus: topic axis, series sequencing, and cross-format translation
    required_knowledge_clusters:
      - W2-P0-01-RS04-CL01
      - W2-P0-01-RS04-CL02
    status: research_planning_only
    not_formal_capability_card: true

required_knowledge_clusters:
  - cluster_id: W2-P0-01-RS01-CL01
    cluster_name: 企业叙事骨架模块
    p0_group: P0-01
    research_card_id: P0-01-RS01
    domain_module: enterprise_narrative_architecture
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - relation_hint
      - boundary_rule
    object_type: CapabilityResearchCluster
    definition: 定义企业叙事的通用骨架，由问题域、组织方法、证明槽位、价值表达、延续方向组成。
    why_required_for_capability: 用于把企业叙事从口号改为结构化研究对象，并为后续系列化拆分提供总纲。
    applies_when:
      - 需要搭建企业叙事总结构时
      - 需要把价值表达与组织/过程/证明连接时
      - 需要定义系列化总叙事时
    does_not_apply_when:
      - 直接写真实品牌历史、起源、节点事件时
      - 直接输出可发布品牌故事正文时
      - 只有抽象价值词、没有结构模块时
    counter_boundary:
      - 不等于真实品牌编年史
      - 不等于创始人传记或人物弧线
      - 不等于企业规模、销量、奖项、授权等实例事实清单
    output_influence:
      - 限制后续研究只产出结构模块而非成稿
      - 为 series 规划建立统一章节粒度
      - 提升 narrative cluster 的可审校性与去模板能力
    expected_body_topics:
      - 企业所回应的问题场景
      - 组织性方法与长期选择
      - 供应链 / 组织 / 过程证明的预留槽位
      - 价值表达与可观察差异
      - 连续性与未来方向的非承诺式表达
    required_relations:
      - problem_domain -> operating_method
      - operating_method -> proof_slot
      - proof_slot -> value_expression
      - value_expression -> series_axis
      - constraint_or_tradeoff -> credibility
    risk_boundaries:
      - 禁止滑入真实品牌起源史、扩张史、节点史
      - 禁止用无来源愿景、使命、行业地位充当证明
      - 禁止把研究子卡误写为正式 capability card
    source_dependency: 依赖后续仓侧 intake 验证结构模块可由公开企业介绍、公开方法说明、公开过程说明承托；当前地图本身不是 source intake。
    evidence_need:
      minimum_method_support:
        - 至少明确哪些来源类别可承载问题域、方法、证明、价值四类模块
        - 若未来落到具体企业，必须由实例来源重建，不能复用本地图为事实证明
      hard_claim_trigger:
        - 涉及质量、性能、规模、销量、排名、奖项、授权、产地时，必须改路由
    evidence_classes:
      - official_corporate_profile_type
      - official_operating_method_overview_type
      - official_process_explainer_type
      - organization_role_description_type
    risk_flags:
      - brand_history_fact_risk
      - founder_fact_risk
      - empty_values_risk
      - unsupported_scale_claim_risk
    source_research_priority: highest
    shared_with_capability_cards:
      - P0-02
      - P0-03
      - P0-05
    batch_refs:
      - batch_009
      - batch_007
      - batch_013
    candidate_output_effect: 仅提升 research map 中企业叙事的结构复用性、系列拆分能力与证据槽位规划能力。
    forbidden_knowledge_leakage:
      - 真实品牌历史事实
      - 真实创始人经历
      - 真实企业规模与经营事实
      - 真实顾客反馈或媒体评价
    source_gap_likelihood: medium
    duplicate_check_key: P0-01_enterprise_narrative_architecture_general_only
    body_structure_consistency_note: 若未来任何 cluster 无法映射到问题域、方法、证明、价值四个模块中的至少两个，应标记为空泛或重复。

  - cluster_id: W2-P0-01-RS01-CL02
    cluster_name: 供应链组织过程证明槽位
    p0_group: P0-01
    research_card_id: P0-01-RS01
    domain_module: proof_slot_and_capability_substantiation
    knowledge_type: evidence_requirement
    knowledge_types:
      - evidence_requirement
      - relation_hint
      - boundary_rule
    object_type: CapabilityResearchCluster
    definition: 定义企业叙事中的证明槽位，包括组织分工、过程节点、质量门、供应链选择、约束处理与交接逻辑。
    why_required_for_capability: 用于让企业叙事具备可信度来源，而不是只剩价值宣言。
    applies_when:
      - 需要把能力表达落到可观察节点时
      - 需要规划后续 sources 应证明什么时
      - 需要连接 P0-01 与 P0-02、P0-03 的共享能力证明位时
    does_not_apply_when:
      - 写具体工厂、具体供应商、具体认证时
      - 写未公开流程细节或内部授权时
      - 只剩概念词而无节点、动作、约束时
    counter_boundary:
      - 不构成完整供应链本体
      - 不构成完整工艺质量知识库
      - 不得替代实例证据来证明真实企业能力
    output_influence:
      - 使 enterprise story method 能预留组织、过程、供应链证明位置
      - 降低 narrative 过度依赖 founder myth 或 slogan 的风险
      - 帮助 series 规划形成可拆分的 proof episodes
    expected_body_topics:
      - 角色分工与协作边界
      - 关键工序或流程节点的叙事位置
      - 质量门、复核门、交接门
      - 供应链选择与约束处理的通用叙事位
      - 从后台流程到前台价值的映射逻辑
    required_relations:
      - organization_role -> process_node
      - process_node -> quality_gate
      - supply_chain_choice -> constraint
      - constraint -> method_credibility
      - proof_slot -> value_expression
    risk_boundaries:
      - 禁止写具体工厂、供应商、产地、认证、奖项等实例信息
      - 禁止把机密流程、未披露 SOP、内部授权写成通用知识
      - 禁止把 proof slot 扩大成完整 display system 或 training system
    source_dependency: 需要后续 source intake 定义哪些公开来源可以支撑 proof slot 的存在与强弱；当前只建立来源类别与关系要求。
    evidence_need:
      minimum_method_support:
        - 来源类别必须可对应组织说明、流程说明、质量说明或公开方法说明
        - 若未来实例引用涉及质量、性能、授权、合规，应升级到更高证据等级或 founder review
      hard_claim_trigger:
        - 任何涉及品质稳定性、性能结果、耐久表现、供应链能力结论的表述均不得无证转事实
    evidence_classes:
      - official_process_overview_type
      - official_quality_method_note_type
      - official_supply_chain_principle_disclosure_type
      - organization_or_role_document_type
      - authorized_third_party_standard_reference_type_if_later_allowed
    risk_flags:
      - process_confidentiality_risk
      - unsupported_quality_claim_risk
      - supply_chain_instance_fact_risk
      - authorization_boundary_risk
    source_research_priority: highest
    shared_with_capability_cards:
      - P0-02
      - P0-03
      - P0-04
    batch_refs:
      - batch_009
      - batch_007
      - batch_013
    candidate_output_effect: 仅形成 proof-slot taxonomy、evidence need labels 与 cross-card relation hints。
    forbidden_knowledge_leakage:
      - 真实工厂事实
      - 真实供应商事实
      - 真实工艺性能结论
      - 真实授权或合作事实
    source_gap_likelihood: high
    duplicate_check_key: P0-01_proof_slots_supply_chain_org_process_general
    body_structure_consistency_note: 任何 proof slot 必须能回答由谁做、在何节点做、处理何约束、如何影响前台价值；否则应降级为空洞表达。

  - cluster_id: W2-P0-01-RS02-CL01
    cluster_name: 故事弧线选择与适用边界
    p0_group: P0-01
    research_card_id: P0-01-RS02
    domain_module: story_arc_selection_boundary
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - general_method
      - source_gap_candidate
    object_type: CapabilityResearchCluster
    definition: 建立企业叙事可用弧线的通用选择规则，例如问题应对型、能力积累型、选择取舍型、组织协同型、场景响应型。
    why_required_for_capability: 没有 arc boundary，企业叙事会滑向无证的 origin myth、人物传奇或夸张转折。
    applies_when:
      - 需要选择企业叙事弧线时
      - 需要判断某弧线是否依赖高风险事实时
      - 需要限制 brand story method 不越界为实例剧情时
    does_not_apply_when:
      - 直接复述真实企业成长史、创始人史、扩张史时
      - 使用危机逆转、行业第一、传奇起点等强戏剧弧线但无证据时
      - 仅为制造情绪高潮而脱离组织、过程、价值关系时
    counter_boundary:
      - 不允许把 founder-hero arc 当默认模板
      - 不允许把未经证实的转折事件写进方法论
      - 不允许把弧线规则写成可直接发布的文案框架
    output_influence:
      - 减少企业叙事中的剧情模板化与夸大化
      - 为 source gap 路由建立更清晰触发条件
      - 帮助后续 series 规划保持结构一致性
    expected_body_topics:
      - 不同叙事弧线对应的问题类型
      - 弧线与证据要求的绑定
      - 弧线与价值表达、proof slot 的兼容性
      - 不适用弧线的识别信号
      - 从强戏剧化退回方法叙事的降级路径
    required_relations:
      - story_arc -> required_proof_intensity
      - story_arc -> compatible_value_expression
      - story_arc -> forbidden_fact_zone
      - arc_mismatch -> source_gap_or_downgrade
    risk_boundaries:
      - 禁止以真实人物命运、真实品牌里程碑作为默认弧线素材
      - 禁止无证构造起点困境、逆袭、传承、行业见证等桥段
      - 禁止将弧线方法误判为可生成 production copy
    source_dependency: 若未来需要把某类弧线用于实例企业，必须重新确认是否存在相应来源与证据强度；当前仅保留 method boundary。
    evidence_need:
      minimum_method_support:
        - 每类弧线至少绑定一种可接受的证明类别或降级策略
        - 强剧情弧线默认视为高风险，除非未来 intake 明确授权并具备实例证据
      hard_claim_trigger:
        - 一旦弧线依赖真实事件、真实人物、真实经营结果，本地图必须退出事实表达
    evidence_classes:
      - story_method_reference_type
      - organization_process_or_capability_explainer_type
      - official_milestone_disclosure_type_if_later_instance_authorized
    risk_flags:
      - origin_myth_risk
      - founder_story_risk
      - unsupported_turning_point_risk
      - template_drama_risk
    source_research_priority: high
    shared_with_capability_cards:
      - P0-02
      - P0-05
    batch_refs:
      - batch_009
      - batch_005
      - batch_002
    candidate_output_effect: 仅提供 arc taxonomy、适用条件与 downgrade routing，不输出 story scripts。
    forbidden_knowledge_leakage:
      - 真实品牌起源故事
      - 真实代际传承故事
      - 真实危机逆转故事
      - 真实行业地位叙事
    source_gap_likelihood: medium_high
    duplicate_check_key: P0-01_story_arc_selection_boundary_general_only
    body_structure_consistency_note: 任何弧线若不能明确对应 proof intensity 与 forbidden zone，应视为过泛模板并拆除。

  - cluster_id: W2-P0-01-RS02-CL02
    cluster_name: 抽象价值到可观察表达的转译规则
    p0_group: P0-01
    research_card_id: P0-01-RS02
    domain_module: value_expression_translation
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - evidence_requirement
      - relation_hint
    object_type: CapabilityResearchCluster
    definition: 把企业叙事中的抽象价值词转译为可观察的选择、动作、约束处理、流程节点与视觉线索。
    why_required_for_capability: 用于防止价值词堆叠，建立价值表达与证据语言的中间层。
    applies_when:
      - 存在质量、责任、稳定、效率、专业等价值词时
      - 需要把价值与 proof slot 连接时
      - 需要为平台化表达提供可见 cue 时
    does_not_apply_when:
      - 把价值词直接当事实结论时
      - 把顾客结果、性能结果、市场结果写成价值证明时
      - 没有任何选择、动作、约束、节点可承接价值时
    counter_boundary:
      - 不授权质量、性能、舒适、耐久等结果性 claim
      - 不等于真实企业价值观文本解析
      - 不等于可直接发布的宣传标语体系
    output_influence:
      - 提高 narrative 内容的可观察性与 filmability
      - 帮助 later intake 区分 value language 与 evidence language
      - 为 series 与 cross-format translation 提供稳定 asset unit
    expected_body_topics:
      - 抽象价值词的可观察载体类型
      - 价值词与组织选择、流程动作、质量门的映射
      - 价值语言的反证边界与降级策略
      - 视觉 cue、动作 cue、比较 cue 的连接方法
      - 从 value statement 到 proof slot 的桥接层
    required_relations:
      - abstract_value -> observable_choice
      - observable_choice -> process_or_role_cue
      - process_or_role_cue -> proof_slot
      - proof_slot -> restrained_value_expression
    risk_boundaries:
      - 禁止把抽象价值直接升级为真实产品效果或经营事实
      - 禁止用真实顾客评价替代 value translation
      - 禁止在无证情况下使用 best、first、only、premium 类地位化表达
    source_dependency: 未来若用于实例企业，必须验证相关 value 是否真能由公开组织、过程、质量说明承接；当前只保留转译规则。
    evidence_need:
      minimum_method_support:
        - 每个抽象价值至少可映射到一种可观察选择或节点类型
        - 若映射结果仍是抽象形容词，应判为空洞并路由到 DQ fail
      hard_claim_trigger:
        - 凡出现效果性、性能性、耐久性、身体结果等信号，必须移交边界或 source gap
    evidence_classes:
      - official_value_or_method_statement_type
      - official_process_or_quality_explainer_type
      - organization_choice_or_policy_description_type
    risk_flags:
      - empty_value_language_risk
      - claim_inflation_risk
      - customer_feedback_proxy_risk
      - quality_result_overreach_risk
    source_research_priority: highest
    shared_with_capability_cards:
      - P0-03
      - P0-04
      - P0-05
    batch_refs:
      - batch_009
      - batch_005
      - batch_002
    candidate_output_effect: 可形成 value translation ledger、observable cue categories 与 evidence dependency labels；不形成 slogan 库。
    forbidden_knowledge_leakage:
      - 真实品牌价值宣言作为事实收录
      - 真实产品体验结论
      - 真实顾客口碑
      - 真实经营口碑
    source_gap_likelihood: medium_high
    duplicate_check_key: P0-01_value_to_observable_translation_general_only
    body_structure_consistency_note: 若某价值词无法落到选择、动作、节点、线索中的至少一项，则不得保留为高优先研究依据。

  - cluster_id: W2-P0-01-RS03-CL01
    cluster_name: 反模板叙事锚点与差异化算子
    p0_group: P0-01
    research_card_id: P0-01-RS03
    domain_module: anti_template_anchor_system
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - boundary_rule
      - relation_hint
    object_type: CapabilityResearchCluster
    definition: 建立企业叙事的不可替代锚点体系，包括对象、动作、约束、过程节点、比较维度、时间切片、角色协作与可见线索。
    why_required_for_capability: 缺少 anchor 的企业叙事会变成空话；该 cluster 直接决定 grounded、differentiated、filmable 程度。
    applies_when:
      - 需要判定 narrative 是否为空泛模板时
      - 需要为 later intake 的 topic planning 提供可拍摄锚点时
      - 需要把企业能力表达与场景、动作、线索绑定时
    does_not_apply_when:
      - 只有品牌愿景、态度、情绪、格调等抽象词时
      - 没有对象、动作、约束、节点任一锚点时
      - 内容企图依赖真实人物故事或真实顾客反馈制造差异性时
    counter_boundary:
      - 不等于具体脚本 shot list
      - 不等于真实门店、真实工厂、真实人物的素材清单
      - 不等于完整 display 或直播作业系统
    output_influence:
      - 提升 narrative cluster 的可见性、可执行性与复核性
      - 为 cross-format translation 提供最小资产单元
      - 为 DQ 检查提供 anchor presence 判断
    expected_body_topics:
      - 对象锚点类型
      - 动作锚点与处理逻辑
      - 约束锚点与取舍表达
      - 节点锚点与前后台衔接
      - 比较锚点与差异化表达
      - 时间切片锚点与连续性表达
    required_relations:
      - anchor_object -> anchor_action
      - anchor_action -> visible_cue
      - constraint -> tradeoff_expression
      - process_node -> narrative_sceneability
      - comparison_dimension -> differentiation
    risk_boundaries:
      - 禁止用 generic slogan 充当锚点
      - 禁止用真实人物、真实顾客、真实门店作为默认锚点来源
      - 禁止把锚点系统误写成 production-ready 选题库
    source_dependency: 方法级可先建；若未来需要实例化锚点，必须重新引入实例来源与审查，不得从本图逆推出真实对象。
    evidence_need:
      minimum_method_support:
        - 每个 narrative cluster 至少应含一种 anchor 类型，否则应判为弱知识
        - anchor 与 claim 必须拆开；锚点可存在，事实结论不可自动成立
      hard_claim_trigger:
        - 锚点若被用来证明质量、性能、组织能力结论，仍需额外证据路径
    evidence_classes:
      - process_scene_or_object_reference_type
      - organization_role_action_reference_type
      - method_or_choice_explainer_type
    risk_flags:
      - generic_template_risk
      - anchor_missing_risk
      - persona_leakage_risk
      - false_filmability_risk
    source_research_priority: highest
    shared_with_capability_cards:
      - P0-02
      - P0-03
      - P0-04
      - P0-05
    batch_refs:
      - batch_010
      - batch_011
      - batch_014
    candidate_output_effect: 用于 DQ gate 的 narrative anchor checklist、anti-template split 规则与 sceneability hints。
    forbidden_knowledge_leakage:
      - 真实角色故事
      - 真实门店场景
      - 真实工厂画面事实
      - 真实顾客互动事实
    source_gap_likelihood: medium
    duplicate_check_key: P0-01_anti_template_anchor_system_general_only
    body_structure_consistency_note: 若 cluster 只能给出形容词而无法指出锚点对象、动作或约束，则应拆分或剔除。

  - cluster_id: W2-P0-01-RS03-CL02
    cluster_name: 叙事过度放大与禁区路由
    p0_group: P0-01
    research_card_id: P0-01-RS03
    domain_module: narrative_risk_boundary_and_routing
    knowledge_type: routing_hint
    knowledge_types:
      - routing_hint
      - boundary_rule
      - decision_required_candidate
    object_type: CapabilityResearchCluster
    definition: 识别创始人传奇、排名奖项、销量规模、外部背书、授权身份、客户口碑、工艺性能结果、社会责任等高风险叙事区，并定义降级与路由。
    why_required_for_capability: 用于防止 P0-01 误产出具有事实感的高风险 narrative fragments。
    applies_when:
      - 内容试图通过权威、传奇、成果、口碑、责任、认证增强说服力时
      - 需要判断某 narrative element 是否已越出 general_only 时
      - 需要把 narrative 风险路由到正确账本时
    does_not_apply_when:
      - 仅讨论纯方法级骨架、关系、锚点时
      - 未产生任何事实性、效果性、地位性暗示时
      - 只在描述 research process 而非 narrative 内容时
    counter_boundary:
      - 不替代 P0-00 的控制面总路由
      - 不允许把 founder review 当作真实性豁免
      - 不允许把风险列表改写成可用宣传点清单
    output_influence:
      - 建立 narrative items 的降级与剔除纪律
      - 防止 unsupported claims 进入 later intake
      - 把高风险叙事从通用知识中预先剥离
    expected_body_topics:
      - 高风险 narrative zone 分类
      - 不同风险 zone 对应的路由动作
      - 风险放大词与禁用表达类别
      - 需要 founder review 的典型边界
      - 从高风险表达回退到方法层表达的范式
    required_relations:
      - risk_zone -> routing_target
      - authority_signal -> evidence_requirement
      - instance_fact_dependency -> source_gap
      - sensitive_promise -> founder_review
    risk_boundaries:
      - 禁止洞穿为真实品牌荣誉、排名、认证、授权、顾客反馈事实
      - 禁止把 founder review 理解为可直接通过生产的绿色通道
      - 禁止借本 cluster 生成 publishable risk-managed copy
    source_dependency: 仅定义风险分类与路由条件；任何实例风险判断都需后续 source intake 与审查流程确认。
    evidence_need:
      minimum_method_support:
        - 每个高风险 zone 必须绑定明确 routing target
        - 不得出现既高风险又无路由定义的 narrative element
      hard_claim_trigger:
        - 排名、销量、奖项、认证、社会责任、顾客结果、性能结果、授权身份均触发实例事实路径
    evidence_classes:
      - risk_policy_reference_type
      - source_gap_route_reference_type
      - founder_review_trigger_reference_type
    risk_flags:
      - authority_overclaim_risk
      - customer_feedback_fact_risk
      - award_or_ranking_risk
      - compliance_and_authorization_risk
      - quality_and_performance_claim_risk
    source_research_priority: highest
    shared_with_capability_cards:
      - P0-03
      - P0-05
    batch_refs:
      - batch_010
      - batch_011
      - batch_014
    candidate_output_effect: 只产生 risk routing ledger、forbidden amplification cues 与 downgrade conditions。
    forbidden_knowledge_leakage:
      - 真实奖项与排名事实
      - 真实客户评价
      - 真实授权或合作背书
      - 真实效果承诺
    source_gap_likelihood: high
    duplicate_check_key: P0-01_narrative_risk_boundary_and_routing_general_only
    body_structure_consistency_note: 任何高风险 signal 若未指定 source gap、decision required、founder review 之一，应视为未完成 cluster。

  - cluster_id: W2-P0-01-RS04-CL01
    cluster_name: 企业叙事系列轴与序列编排
    p0_group: P0-01
    research_card_id: P0-01-RS04
    domain_module: series_axis_and_sequence_principles
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - relation_hint
      - boundary_rule
    object_type: CapabilityResearchCluster
    definition: 按角色轴、过程轴、价值-选择轴、问题场景轴、前后台映射轴、时间切片轴组织企业叙事的系列化拆分，但不生成发布计划。
    why_required_for_capability: 用于让企业叙事具备系列化能力，而不是停留在单篇说辞。
    applies_when:
      - 需要拆分多期研究选题时
      - 需要控制内容重复时
      - 需要建立 topic axis 与 proof cadence 关系时
    does_not_apply_when:
      - 直接输出内容日历、投放策略、发布 SOP 时
      - 把 series planning 写成 workflow 或 production plan 时
      - 没有统一骨架与 proof slot 前置约束时
    counter_boundary:
      - 不等于 full generation plan
      - 不等于 release calendar
      - 不等于 RAG context bundle 或 DIFY workflow
    output_influence:
      - 提升同一企业叙事跨多期研究的结构一致性
      - 帮助 later intake 形成 topic family 而不是孤立片段
      - 为 cross-format translation 提供稳定 episode unit
    expected_body_topics:
      - 系列轴的类型与选用条件
      - 序列编排逻辑与去重复机制
      - proof cadence 与 topic cascade 的绑定
      - 前台价值与后台能力穿插规则
      - 单期单位的最小结构约束
    required_relations:
      - master_narrative -> series_axis
      - series_axis -> episode_unit
      - episode_unit -> proof_slot_distribution
      - sequence_order -> repetition_control
      - frontstage_value -> backstage_capability_episode
    risk_boundaries:
      - 禁止写成内容排期、增长策略或发布任务单
      - 禁止在没有 proof slot 的情况下先规划多期价值宣讲
      - 禁止把 series axis 误写为新增 capability group
    source_dependency: 系列规则可先做方法研究；未来若实例化任何 series unit，需重新匹配到具体来源和证据，不得从本图自动落地。
    evidence_need:
      minimum_method_support:
        - 每条 series axis 至少应对应一种可重复的 proof 或 anchor distribution 规则
        - 若 sequence 只能按情绪变化推进而没有结构锚点，应判为弱方法
      hard_claim_trigger:
        - 单期若含效果性、经营性或人物性事实，则必须退出本 cluster
    evidence_classes:
      - topic_axis_reference_type
      - series_structure_reference_type
      - proof_slot_distribution_reference_type
    risk_flags:
      - series_repetition_risk
      - empty_topic_axis_risk
      - production_plan_leakage_risk
      - cross_card_scope_confusion_risk
    source_research_priority: high
    shared_with_capability_cards:
      - P0-02
      - P0-03
      - P0-04
      - P0-05
    batch_refs:
      - batch_007
      - batch_009
      - batch_012
    candidate_output_effect: 用于 later intake 的 topic-axis grid、episode-unit rules 与 anti-repetition notes。
    forbidden_knowledge_leakage:
      - 发布排期
      - 渠道策略
      - 投放策略
      - production workflow
    source_gap_likelihood: medium
    duplicate_check_key: P0-01_series_axis_and_sequence_general_only
    body_structure_consistency_note: 任何 series axis 若不能说明为何分期、每期承接何 proof 或 anchor、如何避免重复，则不得保留。

  - cluster_id: W2-P0-01-RS04-CL02
    cluster_name: 跨形态转译资产单元
    p0_group: P0-01
    research_card_id: P0-01-RS04
    domain_module: cross_format_translation_assets
    knowledge_type: relation_hint
    knowledge_types:
      - relation_hint
      - general_method
      - evidence_requirement
    object_type: CapabilityResearchCluster
    definition: 定义可在短视频、图文、直播讲解、培训辅助、陈列支持语境中复用的最小叙事资产单元，如对象 cue、动作 cue、节点 cue、比较 cue、图解 cue、角色协作 cue。
    why_required_for_capability: 用于覆盖系列化转译要求，让企业叙事跨平台复用而不落成 workflow 或成稿。
    applies_when:
      - 需要把同一企业叙事拆成多形态可承接的研究资产时
      - 需要评估某叙事元素是否具备 filmability、diagramability、explainability 时
      - 需要为 P0-04 support-only 场景提供叙事支持位时
    does_not_apply_when:
      - 直接写直播话术、脚本、培训提纲、门店指引时
      - 把 asset unit 直接变成 DIFY workflow、RAG bundle、serving projection 时
      - 缺少锚点与 proof slot、只剩情绪口号时
    counter_boundary:
      - 不构成完整 display-system ontology
      - 不构成 training SOP
      - 不构成 short video script library
    output_influence:
      - 提升企业叙事跨形态复用能力
      - 增强主题资产的 filmability 与 explainability
      - 为 P0-04 提供 support-only 的 narrative bridge，而非完整陈列系统
    expected_body_topics:
      - 最小叙事资产单元类型
      - 单元与平台形态的适配关系
      - 单元与锚点、证明槽位的绑定规则
      - 转译时应删除或保留的信息层
      - support-only 协同边界
    required_relations:
      - anchor_unit -> format_adaptability
      - proof_slot -> explainability_asset
      - series_episode -> reusable_asset_unit
      - support_only_bridge -> P0-04_boundary
    risk_boundaries:
      - 禁止输出 production-ready 脚本、直播话术、SOP、工作流
      - 禁止把 P0-04 support-only 误写成完整陈列系统
      - 禁止把 raw research asset 误写成可直接 serving 的知识块
    source_dependency: 方法研究可先完成；但任何具体平台落地都需后续独立 source intake、capability routing 与 repository gate。
    evidence_need:
      minimum_method_support:
        - 每类资产单元至少说明可见锚点、适配形态、需承接的 proof level
        - 如无法说明为何能被看见、讲清、比较或解释，则应降级为弱资产
      hard_claim_trigger:
        - 一旦资产单元承载具体效果、具体背书、具体经营事实，应退出本图
    evidence_classes:
      - platform_native_expression_hint_type
      - visual_cue_or_sceneability_reference_type
      - support_only_translation_boundary_reference_type
    risk_flags:
      - workflow_leakage_risk
      - support_only_overreach_risk
      - rag_or_serving_boundary_risk
      - asset_without_proof_risk
    source_research_priority: high
    shared_with_capability_cards:
      - P0-04
      - P0-02
      - P0-05
    batch_refs:
      - batch_007
      - batch_009
      - batch_012
    candidate_output_effect: 仅形成 cross-format asset taxonomy、adaptation hints 与 support-only boundary notes。
    forbidden_knowledge_leakage:
      - 直播话术成稿
      - 图文成稿
      - 培训 SOP
      - DIFY workflow
      - RAG context bundle
    source_gap_likelihood: medium_high
    duplicate_check_key: P0-01_cross_format_translation_assets_general_only
    body_structure_consistency_note: 每个资产单元都必须能说明自身来自哪个锚点、承接哪个 proof level、适配哪些形态；否则应视为过泛转译词。

relation_hints:
  - relation_id: RH01
    relation_type: foundation_for
    from_cluster_id: W2-P0-01-RS01-CL01
    to_cluster_id: W2-P0-01-RS04-CL01
    note: 企业叙事骨架先于系列轴；无总骨架不应先分期。
  - relation_id: RH02
    relation_type: proof_requirement_for
    from_cluster_id: W2-P0-01-RS01-CL02
    to_cluster_id: W2-P0-01-RS02-CL02
    note: 价值转译必须绑定 proof slot，避免抽象价值漂浮。
  - relation_id: RH03
    relation_type: boundary_constraint_on
    from_cluster_id: W2-P0-01-RS02-CL01
    to_cluster_id: W2-P0-01-RS04-CL01
    note: series 规划只能使用已通过弧线适用性检查的 narrative arc。
  - relation_id: RH04
    relation_type: dq_strengthener_for
    from_cluster_id: W2-P0-01-RS03-CL01
    to_cluster_id: W2-P0-01-RS04-CL02
    note: 跨形态转译资产单元必须继承 anti-template anchors。
  - relation_id: RH05
    relation_type: routing_override_on
    from_cluster_id: W2-P0-01-RS03-CL02
    to_cluster_id: W2-P0-01-RS01-CL02
    note: 任何高风险放大信号都可覆盖普通 proof-slot 研究路径并转入 source gap、decision required 或 founder review。
  - relation_id: RH06
    relation_type: shared_with_other_capabilities
    from_cluster_id: W2-P0-01-RS01-CL02
    to_capability_cards:
      - P0-02
      - P0-03
      - P0-04
    note: 组织、过程、供应链证明槽位与角色叙事、工艺质量叙事、support-only 转译存在共享边界。

source_gap_items:
  - item_id: SG01
    object_type: SourceGapItem
    p0_group: P0-01
    related_clusters:
      - W2-P0-01-RS01-CL02
      - W2-P0-01-RS02-CL02
    gap: 缺少企业叙事 proof slot 强弱分级的统一来源类别细化规则。
    route: source_gap
    why_blocking: 弱来源容易被误当强证明。
  - item_id: SG02
    object_type: SourceGapItem
    p0_group: P0-01
    related_clusters:
      - W2-P0-01-RS03-CL02
    gap: 缺少叙事高风险区与 founder review 的细颗粒触发表。
    route: source_gap_or_decision_required
    why_blocking: 路由不一致风险高。
  - item_id: SG03
    object_type: SourceGapItem
    p0_group: P0-01
    related_clusters:
      - W2-P0-01-RS04-CL02
    gap: 缺少跨形态最小资产单元的 sufficiency threshold 定义。
    route: source_gap
    why_blocking: 空泛转译词可能被错误保留。
  - item_id: SG04
    object_type: SourceGapItem
    p0_group: P0-01
    related_clusters:
      - W2-P0-01-RS02-CL01
    gap: 缺少强戏剧化企业叙事弧线的统一降级标准。
    route: source_gap
    why_blocking: 方法层容易被故事化冲动侵蚀。

decision_required_items:
  - item_id: DR01
    object_type: DecisionRequiredItem
    p0_group: P0-01
    related_clusters:
      - W2-P0-01-RS01-CL02
      - W2-P0-01-RS02-CL02
    decision_question: 供应链、组织、过程证明槽位的 ontology ownership 应以 P0-01 为主还是拆分给 P0-02 与 P0-03 维护？
    why_decision_required: ownership 不清会导致重复 cluster 与冲突 merge。
  - item_id: DR02
    object_type: DecisionRequiredItem
    p0_group: P0-01
    related_clusters:
      - W2-P0-01-RS04-CL02
    decision_question: 跨形态转译资产单元允许延伸到何种 training / store support 深度，才能保持 A2 support-only 而不越权为完整 display system？
    why_decision_required: 边界不清会直接触发 support-only overreach。
  - item_id: DR03
    object_type: DecisionRequiredItem
    p0_group: P0-01
    related_clusters:
      - W2-P0-01-RS03-CL02
    decision_question: 认证、授权、社会责任、可持续等 narrative risk zone 是否统一进入 founder review，还是允许部分仅以 source gap 处理？
    why_decision_required: 不同风险类别的治理强度可能不同，需显式决策。

excluded_items:
  - item_id: EX01
    object_type: ExcludedResearchItem
    p0_group: P0-01
    excluded_content: 任何真实品牌故事正文、品牌历史稿、创始人经历稿
    reason: 属于实例事实与 publishable script 禁区。
  - item_id: EX02
    object_type: ExcludedResearchItem
    p0_group: P0-01
    excluded_content: 任何真实 SKU、真实门店、真实工厂、真实顾客反馈、真实销售或奖项事实
    reason: 实例事实需单独路径与证据政策。
  - item_id: EX03
    object_type: ExcludedResearchItem
    p0_group: P0-01
    excluded_content: CandidatePack、KE、Serving projection、approved passage、RAG context bundle、DIFY workflow
    reason: research-only 边界明确禁止。
  - item_id: EX04
    object_type: ExcludedResearchItem
    p0_group: P0-01
    excluded_content: 把 3600 写成验收 KPI，或把 research subcard 写成正式 capability card
    reason: 违反 charter、schema 与 matrix 规则。

shared_cluster_merge_items:
  - merge_id: SM01
    object_type: SharedClusterMergeCandidate
    source_cluster_id: W2-P0-01-RS01-CL02
    shared_with_capability_cards:
      - P0-02
      - P0-03
      - P0-04
    merge_rule: 只共享证明槽位关系与来源类别，不共享任何实例流程、实例组织、实例门店事实。
    anti_duplication_note: 避免 P0-01 与 P0-03 同时建立完整 process ontology。
  - merge_id: SM02
    object_type: SharedClusterMergeCandidate
    source_cluster_id: W2-P0-01-RS03-CL01
    shared_with_capability_cards:
      - P0-02
      - P0-04
      - P0-05
    merge_rule: 共享锚点体系与 DQ 检查，不共享具体场景素材。
    anti_duplication_note: 保证 anti-template anchor 作为跨卡共用方法，而非重复 topic 库。
  - merge_id: SM03
    object_type: SharedClusterMergeCandidate
    source_cluster_id: W2-P0-01-RS04-CL02
    shared_with_capability_cards:
      - P0-04
    merge_rule: 仅允许 support-only translation bridge；不得升级为完整陈列系统、培训 SOP 或 workflow。
    anti_duplication_note: 防止 P0-01 narrative translation 抢占 P0-04 系统边界。

founder_review_items:
  - item_id: FR01
    p0_group: P0-01
    trigger_zone: 认证、授权、合规、可持续、社会责任类叙事增强
    why_founder_review: 容易跨入高敏事实、外部背书或合规声明。
  - item_id: FR02
    p0_group: P0-01
    trigger_zone: 行业地位、第一、唯一、规模、排名、奖项类表达
    why_founder_review: 属于高风险 authority signal。
  - item_id: FR03
    p0_group: P0-01
    trigger_zone: 涉及真实人物、真实客户、真实合作方、真实门店或真实工厂的叙事素材
    why_founder_review: 直接跨入实例事实边界。

required_execution_asset_types:
  - asset_type: research_map_yaml
    purpose: 承载 P0-01 企业叙事 knowledge research map 本体
    production_ready: false
  - asset_type: subcard_cluster_matrix
    purpose: 对应四张 research subcard 与 cluster 覆盖关系
    production_ready: false
  - asset_type: proof_slot_taxonomy_sheet
    purpose: 整理组织、过程、供应链证明槽位与来源类别
    production_ready: false
  - asset_type: value_translation_rule_ledger
    purpose: 记录抽象价值到可观察表达的通用转译规则
    production_ready: false
  - asset_type: dq_anchor_and_risk_checklist
    purpose: 执行 anti-template、anchor presence 与 risk routing 检查
    production_ready: false
  - asset_type: series_axis_sequence_grid
    purpose: 记录系列轴、单期单位、proof cadence 与去重复规则
    production_ready: false

required_dq_checks:
  - check_id: DQ01
    name: anti_empty_language
    rule: 每个 cluster 必须包含定义、适用条件、不适用条件、反边界、关系、证据需求、风险标记。
  - check_id: DQ02
    name: anti_template
    rule: 任何 narrative method 若可不带对象、动作、约束、节点而成立，则应降级或剔除。
  - check_id: DQ03
    name: irreplaceable_anchor
    rule: 企业叙事必须具备至少一种不可替代锚点。
  - check_id: DQ04
    name: claim_evidence_separation
    rule: 价值表达、能力表达、效果表达必须与 evidence need 分离；无证不可上升为事实。
  - check_id: DQ05
    name: filmability_and_explainability
    rule: 优先保留能转成场景、动作、镜头线索、图解线索、比较线索的 cluster。
  - check_id: DQ06
    name: platform_native_non_script
    rule: 允许记录短视频、图文、直播、培训、陈列的 research hints，但不得写成脚本、SOP 或 workflow。
  - check_id: DQ07
    name: persona_brand_customer_risk
    rule: 真实人物、真实品牌、真实顾客、真实门店、真实 SKU 一律不得留在 accepted clusters。
  - check_id: DQ08
    name: anti_duplication_cross_card
    rule: 与 P0-02、P0-03、P0-04、P0-05 的共享方法应 merge，不得重复铺设完整系统。

fallback_conditions:
  - condition_id: FB01
    when: 缺少可支撑 proof slot 的来源类别细分
    fallback_to: 仅保留 narrative skeleton 与 source gap item
    note: 不得用想象性事实填补证明槽位。
  - condition_id: FB02
    when: 抽象价值无法转译为可见选择、动作或节点
    fallback_to: 降级为 weak cluster 或直接剔除
    note: 保留 value word 但无 observable mapping 会触发 DQ fail。
  - condition_id: FB03
    when: series 轴无法说明单期 proof cadence 或 anti-repetition
    fallback_to: 仅保留 master narrative relation hint
    note: 避免空 series planning。
  - condition_id: FB04
    when: cross-format asset unit 缺少锚点与适配条件
    fallback_to: 退回 anti-template anchor cluster
    note: 不允许空泛平台适配词保留。

blocking_conditions:
  - condition_id: BL01
    block_if: 出现任何真实品牌、真实人物、真实 SKU、真实门店、真实工厂、真实顾客反馈事实
    reason: 违反 general_only 与 instance-fact redline。
  - condition_id: BL02
    block_if: 输出 CandidatePack、KE、Serving projection、approved passage、RAG context bundle、DIFY workflow 或任何 production-ready 内容
    reason: 违反 research-only 边界。
  - condition_id: BL03
    block_if: 把 research subcard 写成正式 capability card，或新增 P0 之外能力组
    reason: 违反 capability allocation boundary。
  - condition_id: BL04
    block_if: 把 3600 或任意 count budget 写成 acceptance KPI
    reason: 违反 charter 与 matrix 计数政策。
  - condition_id: BL05
    block_if: 将 A2 support-only 误写成完整陈列系统，或新增 batch_014 之外 batch
    reason: 违反 support-only 与 batch 边界。
  - condition_id: BL06
    block_if: 任何 readiness-like 状态被设置为 true
    reason: 违反 schema 与 readiness policy。

unresolved_decisions:
  - decision_id: UD01
    question: P0-01 中供应链、组织、过程证明槽位与 P0-03 工艺质量故事之间的最终 ontology ownership 如何定界？
    impact: 影响 shared cluster merge 与避免重复建设。
  - decision_id: UD02
    question: 组织文化或组织 ethos 若没有角色动作锚点时，应保留在 P0-01 还是转给 P0-02？
    impact: 影响 role-perspective 与 enterprise narrative 的交界。
  - decision_id: UD03
    question: 跨形态最小资产单元的 sufficiency threshold 由 P0-01 管理，还是由 P0-04 统一定义 support-only bridge？
    impact: 影响 narrative translation 与 display-support 的边界。
  - decision_id: UD04
    question: 认证、可持续、责任类 narrative zone 是否统一进入 founder review，还是按 source strength 分层处理？
    impact: 影响风险路由一致性。

source_gap_seed:
  - seed_id: SGS01
    seed_question: 企业叙事中哪些公开来源类别足以承接组织、过程、供应链 proof slot，而不泄漏实例机密？
  - seed_id: SGS02
    seed_question: 抽象价值词如何稳定转译为选择、动作、节点、视觉 cue，而不越界为效果 claim？
  - seed_id: SGS03
    seed_question: 哪些 anti-template anchors 最适合 apparel / retail 语境下的 enterprise narrative general method？
  - seed_id: SGS04
    seed_question: 企业叙事 series axis 的最小单期结构与 anti-repetition rule 应如何定义？
  - seed_id: SGS05
    seed_question: 跨短视频、图文、直播、培训 support、陈列 support 的最小 narrative asset unit 需要包含哪些字段？

self_check:
  - check_id: SC01
    item: 仅覆盖 P0-01 且未声称 full Part A
    result: true
  - check_id: SC02
    item: 四张 research subcard 已全部覆盖
    result: true
  - check_id: SC03
    item: 每个 subcard 均已产出 required_knowledge_clusters
    result: true
  - check_id: SC04
    item: 所有 readiness 维持 false
    result: true
  - check_id: SC05
    item: 未生成 CandidatePack、KE、RAG、DIFY 或 production-ready 内容
    result: true
  - check_id: SC06
    item: 未写入真实品牌、SKU、门店、人物、顾客反馈事实
    result: true
  - check_id: SC07
    item: 未把 3600 作为验收 KPI
    result: true
  - check_id: SC08
    item: 未把 optional reference 当作 canonical truth
    result: true
  - check_id: SC09
    item: 未新增 P0 之外能力组，未新增 batch_014 之外 batch
    result: true
  - check_id: SC10
    item: 不确定项已路由到 unresolved_decisions 或 source_gap_seed
    result: true

forbidden_output_attestation:
  candidatepack_generated: false
  KE_generated: false
  ABox_or_TBox_generated: false
  evidence_landed_item_generated: false
  serving_projection_generated: false
  approved_passage_text_generated: false
  rag_context_bundle_generated: false
  dify_workflow_generated: false
  publishable_script_generated: false
  route_mutation_generated: false
  real_brand_fact_generated: false
  real_sku_fact_generated: false
  real_store_fact_generated: false
  real_person_fact_generated: false
  real_customer_feedback_generated: false
  candidatepack_ready_claimed: false
  KE_ready_claimed: false
  RAG_ready_claimed: false
  DIFY_ready_claimed: false
  production_ready_claimed: false

readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false