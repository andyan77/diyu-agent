map_id: W5_P0_04_store_daily_display_knowledge_map
map_version: v0_1
source_inputs:
  pack_id: web_gpt_upload_pack_v0_1
  authority_manifest: 09_upload_pack_manifest.json
  required_files_used:
    - 01_research_charter_and_redlines.md
    - 02_p0_capability_and_subcards.yaml
    - 03_batch_allocation_matrix.csv
    - 04_research_map_output_schema.yaml
    - 05_source_claim_evidence_policy.md
    - 06_candidatepack_and_readiness_policy.md
    - 07_dq_anti_homogeneity_policy.md
    - 08_optional_reference_digest.md
    - 09_upload_pack_manifest.json
  conflict_resolution_order:
    - 01_research_charter_and_redlines.md
    - 04_research_map_output_schema.yaml
    - 03_batch_allocation_matrix.csv
    - 02_p0_capability_and_subcards.yaml
    - 05_source_claim_evidence_policy.md
    - 06_candidatepack_and_readiness_policy.md
    - 07_dq_anti_homogeneity_policy.md
    - 09_upload_pack_manifest.json
    - 08_optional_reference_digest.md
  optional_reference_status: structure_only_not_canonical_truth
  research_mode: upload_pack_bounded_general_only

p0_scope:
  cell_id: W5
  prompt_id: WEB-DEEP-RESEARCH-W5-P0-04-STORE-DISPLAY-CONTENTIZATION-MAP-001
  selected_p0_group: P0-04
  selected_p0_group_name: 门店日常 / 陈列动作内容化知识地图
  output_file: W5_P0_04_store_daily_display_knowledge_map.yaml
  knowledge_mode: general_only
  selected_scope_note: 仅覆盖所选P0范围内的P0-04研究子卡，不构成完整Part A，不构成正式capability card。
  scenario_family_boundary:
    allowed_scenario_families:
      - content_generation
      - display_styling
    coordination_view_only: content_x_display
    not_new_scenario_family: true

research_subcard_refs:
  - research_card_id: P0-04-RS01
    p0_group: P0-04
    theme: display scene and look structure
    target_count_budget: 240
    status: research_planning_only
    knowledge_focus: look, display, theme, and color story structures
    batch_refs:
      primary_batches:
        - batch_011
        - batch_012
      secondary_batches:
        - batch_003
    required_knowledge_clusters:
      - W5_P0_04_RS01_CL01
      - W5_P0_04_RS01_CL02
      - W5_P0_04_RS01_CL03
    required_execution_asset_types:
      - Look拆解观察表
      - 陈列区位-镜头锚点表
      - 色彩故事节点关系图
      - source_gap台账
    required_dq_checks:
      - anti_empty_language
      - anti_template
      - irreplaceable_anchor
      - filmability
      - claim_evidence_separation
      - duplicate_cluster_split
    fallback_conditions:
      - 若缺少通用陈列术语来源，则仅保留观察骨架与证据需求，不写动作优劣结论。
      - 若色彩故事只能依赖真实品牌季节主题，则改写为一般化配色叙事结构。
    blocking_conditions:
      - 出现真实门店名称、真实销售结果、真实陈列记录时阻断。
      - 一旦外推为完整陈列系统ontology，则阻断并转decision_required。
    unresolved_decisions:
      - Look层级与陈列区位的最小共用术语集是否需要后续统一词表。
      - 色彩故事层级是否由P0-03共享词库承接仍待后续决策。
    source_gap_seed:
      - 通用Look分解术语公开来源不足。
      - 通用陈列区位与镜头锚点的跨平台共识不足。
    self_check:
      - 所有cluster均为general_only。
      - 未写真实品牌、真实SKU、真实门店、真实人物。
      - 未把数量预算写成验收KPI。

  - research_card_id: P0-04-RS02
    p0_group: P0-04
    theme: store daily contentization
    target_count_budget: 240
    status: research_planning_only
    knowledge_focus: store daily observation and content translation methods
    batch_refs:
      primary_batches:
        - batch_010
        - batch_012
      secondary_batches:
        - batch_013
    required_knowledge_clusters:
      - W5_P0_04_RS02_CL01
      - W5_P0_04_RS02_CL02
      - W5_P0_04_RS02_CL03
    required_execution_asset_types:
      - 门店日常动作观察卡
      - 动作-镜头-文案槽位映射表
      - 风险边界红线表
      - source_gap台账
    required_dq_checks:
      - anti_empty_language
      - anti_template
      - irreplaceable_anchor
      - filmability
      - platform_native_hint_only
      - persona_brand_customer_risk
    fallback_conditions:
      - 若动作无法脱离真实店员或真实顾客关系链，则降级为source_gap。
      - 若无法确认动作与内容段落关系，则只保留观察节点，不写成内容公式。
    blocking_conditions:
      - 出现顾客故事、门店身份事实、员工隐私信息时阻断。
      - 出现可发布脚本、门店经营表现推断时阻断。
    unresolved_decisions:
      - 门店日常与本地生活表达的边界，是否允许保留极轻量场景标签。
      - 培训片段与日常片段的最小切分粒度仍待统一。
    source_gap_seed:
      - 通用门店日常动作词表公开来源分散。
      - 动作转内容单元的跨平台时长切分缺少稳定来源。
    self_check:
      - 仅研究可内容化方法，不输出可直接发布内容。
      - 所有readiness保持false。

  - research_card_id: P0-04-RS03
    p0_group: P0-04
    theme: merchandising and SOP translation
    target_count_budget: 240
    status: research_planning_only
    knowledge_focus: merchandising, training, sales SOP, and display-to-content patterns
    batch_refs:
      primary_batches:
        - batch_012
        - batch_006
      secondary_batches:
        - batch_011
    required_knowledge_clusters:
      - W5_P0_04_RS03_CL01
      - W5_P0_04_RS03_CL02
      - W5_P0_04_RS03_CL03
    required_execution_asset_types:
      - 陈列动作SOP节点表
      - 培训演示三段式骨架
      - 异常与复核路由表
      - source_gap台账
    required_dq_checks:
      - anti_empty_language
      - anti_template
      - claim_evidence_separation
      - filmability
      - counter_boundary_present
      - duplicate_cluster_split
    fallback_conditions:
      - 若SOP仅存在真实门店运营记录形式，则改为一般化流程节点。
      - 若出现销售效果或库存联动判断，则移出本子卡并标记decision_required。
    blocking_conditions:
      - 出现运营记录、真实销售结果、route mutation时阻断。
      - 出现把A2 support-only写成完整陈列系统时阻断。
    unresolved_decisions:
      - 培训SOP与销售SOP的共享节点是否应拆成两个后续词表。
      - 陈列前中后检查项是否需要单独沉淀为跨卡共享规则。
    source_gap_seed:
      - 公开可验证的通用陈列培训SOP资料可能不足。
      - 销售SOP与内容转译之间的证据链可能只停留在方法层。
    self_check:
      - 只写转译关系，不写真实业绩或真实执行结果。
      - 未越权生成Serving、RAG、DIFY资产。

  - research_card_id: P0-04-RS04
    p0_group: P0-04
    theme: retail franchise and authorization
    target_count_budget: 240
    status: research_planning_only
    knowledge_focus: retail role, franchise boundary, authorization, and review routing
    batch_refs:
      primary_batches:
        - batch_013
        - batch_014
      secondary_batches:
        - batch_007
    required_knowledge_clusters:
      - W5_P0_04_RS04_CL01
      - W5_P0_04_RS04_CL02
      - W5_P0_04_RS04_CL03
    required_execution_asset_types:
      - 零售角色-动作-权限矩阵
      - 授权与复核节点图
      - 实例事实排除清单
      - decision_required台账
    required_dq_checks:
      - anti_empty_language
      - anti_template
      - persona_brand_customer_risk
      - claim_evidence_separation
      - control_plane_leak_guard
      - boundary_completeness
    fallback_conditions:
      - 若授权边界需要真实合同或真实加盟制度，则转source_gap或decision_required。
      - 若角色边界开始承载控制面编排逻辑，则回退并标记P0-00泄漏风险。
    blocking_conditions:
      - 出现加盟事实、门店合同事实、真实员工事实时阻断。
      - 出现全链路显示系统主张或越权授权结论时阻断。
    unresolved_decisions:
      - 授权边界中哪些节点属于P0-04方法层，哪些应回P0-00控制层。
      - 加盟体系的泛化方法是否需要更严格 founder review。
    source_gap_seed:
      - 公开来源对通用零售授权复核链条定义可能不一致。
      - 角色矩阵与内容权限矩阵的抽象粒度可能需要后续统一。
    self_check:
      - 只输出一般化角色/授权边界，不含任何真实组织事实。
      - 未把research_subcard误写为正式capability card。

required_knowledge_clusters:
  - cluster_id: W5_P0_04_RS01_CL01
    cluster_name: Look拆解与陈列观察骨架
    p0_group: P0-04
    research_card_id: P0-04-RS01
    knowledge_type: general_method
    object_type: CapabilityResearchCluster
    domain_module: display_scene_look_structure
    why_required_for_capability: 该能力需要先把陈列画面拆成可观察、可比较、可转译的Look元素，否则后续内容化只能停留在空泛“好看”描述。
    knowledge_types:
      - general_method
      - relation_hint
      - evidence_requirement
    expected_body_topics:
      - Look层级拆解维度
      - 单套搭配与成组陈列的观察节点
      - 轮廓/层次/搭配位的命名边界
      - 可拍摄的前景-主体-陪体结构
    required_relations:
      - 关联色彩故事节点
      - 关联陈列区位节点
      - 关联可拍摄动作节点
    risk_boundaries:
      - 不得引入真实品牌Look事实
      - 不得把具体门店橱窗记录写成通用规则
      - 不得将A2 support-only扩展成完整陈列系统
    evidence_classes:
      - 通用视觉陈列方法资料
      - 服装造型观察框架资料
      - 内容拍摄可视锚点资料
    source_research_priority: high
    shared_with_capability_cards:
      - P0-03
      - P0-05
    batch_refs:
      - batch_011
      - batch_012
      - batch_003
    candidate_output_effect: 影响后续候选研究条目如何描述Look拆解、画面重点与动作入口，减少空泛形容词。
    forbidden_knowledge_leakage:
      - 真实品牌季度Look
      - 真实SKU搭配清单
      - 真实门店Look复盘
    source_gap_likelihood: medium
    definition: 用于定义从单套搭配到成组陈列的最小观察单元与拆解顺序。
    applies_when: 当研究对象是一般化门店陈列、搭配展示、可视观察方法时适用。
    does_not_apply_when: 当内容依赖真实品牌系列、真实门店拍摄记录、真实商品组合时不适用。
    counter_boundary: 该cluster只定义观察骨架，不评判商业成效，不下结论性销售判断。
    output_influence: 决定后续研究文本是否能以结构化方式描述Look，而非以口号化语言替代。
    source_dependency: 依赖通用视觉陈列与服装Look观察来源；若来源只支持实例展示，则需降级为source_gap。
    evidence_need: 需要方法类证据与术语一致性证据；若出现“显瘦/提气质/显贵”等效果claim，必须额外证据支持。
    risk_flags:
      - unsupported_claim_detected
      - real_instance_fact_detected
      - full_part_a_overclaim
    duplicate_check_key: look_decomposition__display_observation_frame
    body_structure_consistency_note: 正文结构应保持“观察对象-拆解维度-可见差异-转译用途-边界”五段式。

  - cluster_id: W5_P0_04_RS01_CL02
    cluster_name: 主题与色彩故事关系网
    p0_group: P0-04
    research_card_id: P0-04-RS01
    knowledge_type: general_method
    object_type: CapabilityResearchCluster
    domain_module: display_theme_color_story
    why_required_for_capability: 门店陈列内容化若缺少主题-色彩-层次关系网，后续只能列颜色名，无法形成稳定的叙事骨架。
    knowledge_types:
      - general_method
      - relation_hint
      - boundary_rule
      - evidence_requirement
    expected_body_topics:
      - 主题词与色彩组的关系
      - 主色/辅色/点缀色的观察顺序
      - 系列感与节奏感的表达边界
      - 色彩故事如何回扣Look结构
    required_relations:
      - 依赖Look拆解骨架
      - 连到主题命名边界
      - 连到培训解释节点
    risk_boundaries:
      - 不得写真实品牌季度主题
      - 不得造真实门店陈列计划
      - 不得把色彩偏好写成普遍消费者反馈
    evidence_classes:
      - 色彩叙事方法资料
      - 视觉陈列主题组织资料
      - 服装搭配色彩层次资料
    source_research_priority: high
    shared_with_capability_cards:
      - P0-03
      - P0-01
      - P0-05
    batch_refs:
      - batch_011
      - batch_003
    candidate_output_effect: 影响候选研究条目如何把配色关系写成可解释的观察结构，而不是产出可直接发布文案。
    forbidden_knowledge_leakage:
      - 真实品牌季节主题名
      - 真实销售导向配色策略
      - 真实顾客偏好总结
    source_gap_likelihood: medium
    definition: 用于定义主题与色彩故事在门店陈列内容化中的关系单元、层级顺序与回扣方式。
    applies_when: 当研究需要把门店画面中的色彩、主题、节奏关系转成一般化知识时适用。
    does_not_apply_when: 当主题依赖品牌世界观、具体企划案、真实季节投放计划时不适用。
    counter_boundary: 该cluster只处理关系网，不输出风格定论，不生成品牌主题故事。
    output_influence: 决定后续研究是否能形成“主题词-色彩节点-Look回扣”的内容骨架。
    source_dependency: 依赖通用色彩搭配与视觉陈列资料；缺少通用来源时，只保留层级框架与证据空位。
    evidence_need: 需要能支持色彩层级与主题关系的方法证据；任何情绪功效或人群偏好claim都需额外证据。
    risk_flags:
      - unsupported_claim_detected
      - real_instance_fact_detected
    duplicate_check_key: theme_color_story__display_relation_graph
    body_structure_consistency_note: 正文结构应保持“主题节点-色彩角色-画面节奏-内容转译提示-禁区”五段式。

  - cluster_id: W5_P0_04_RS01_CL03
    cluster_name: 陈列区位与可拍摄视觉锚点
    p0_group: P0-04
    research_card_id: P0-04-RS01
    knowledge_type: general_method
    object_type: CapabilityResearchCluster
    domain_module: display_scene_filmable_anchor
    why_required_for_capability: P0-04要求知识可内容化；若不定义陈列区位与视觉锚点，后续难以将陈列观察转成可拍摄、可复核的内容单位。
    knowledge_types:
      - general_method
      - relation_hint
      - routing_hint
    expected_body_topics:
      - 入口区/中岛/端架/挂通等一般化区位表达
      - 远景-中景-近景的观察切换
      - 静态陈列中的可拍摄重点
      - 从区位到镜头的最小映射
    required_relations:
      - 连接Look拆解
      - 连接日常动作观察
      - 连接SOP演示结构
    risk_boundaries:
      - 不得写真实门店平面信息
      - 不得写真实动线表现
      - 不得写真实陈列执行记录
    evidence_classes:
      - 通用陈列区位术语资料
      - 零售空间视觉观察资料
      - 内容拍摄镜头语法资料
    source_research_priority: medium
    shared_with_capability_cards:
      - P0-02
      - P0-05
    batch_refs:
      - batch_011
      - batch_012
    candidate_output_effect: 影响候选研究条目如何设置观察入口、镜头顺序与画面重心，提升filmability而不输出脚本。
    forbidden_knowledge_leakage:
      - 真实门店平面图
      - 真实巡店视频记录
      - 真实客流热点分析
    source_gap_likelihood: high
    definition: 用于定义一般化陈列区位如何被转译为可视观察和拍摄锚点。
    applies_when: 当研究需要把静态陈列转为可执行的观察/拍摄提示时适用。
    does_not_apply_when: 当区位信息来自真实门店地图、真实动线测试或运营资料时不适用。
    counter_boundary: 该cluster只提供锚点方法，不生成拍摄脚本，不给出发布级镜头表。
    output_influence: 决定后续研究条目能否从抽象陈列描述落到可见、可复核的视觉入口。
    source_dependency: 依赖一般化零售空间观察术语与镜头方法资料；不足时应改写为粗粒度“远中近”分层。
    evidence_need: 需要区位术语、镜头层级和可拍摄性证据；不需要真实门店效率数据。
    risk_flags:
      - real_instance_fact_detected
      - forbidden_object_type
    duplicate_check_key: display_zone__filmable_anchor_map
    body_structure_consistency_note: 正文结构应保持“区位-可见锚点-镜头切换-内容作用-排除项”五段式。

  - cluster_id: W5_P0_04_RS02_CL01
    cluster_name: 门店日常动作观察与切片框架
    p0_group: P0-04
    research_card_id: P0-04-RS02
    knowledge_type: general_method
    object_type: CapabilityResearchCluster
    domain_module: store_daily_action_observation
    why_required_for_capability: 门店日常要被内容化，必须先定义哪些动作属于可观察、可切片、可一般化的动作单元。
    knowledge_types:
      - general_method
      - boundary_rule
      - relation_hint
    expected_body_topics:
      - 开场准备类动作
      - 整理/比对/讲解/递示等一般化动作
      - 动作前提与结束标志
      - 动作与场景道具的最小关系
    required_relations:
      - 连接陈列区位锚点
      - 连接SOP节点
      - 连接风险边界cluster
    risk_boundaries:
      - 不得写真实店员行为记录
      - 不得写真实顾客互动细节
      - 不得写真实经营繁忙度
    evidence_classes:
      - 零售服务与陈列动作的一般方法资料
      - 培训示范动作资料
      - 内容切片方法资料
    source_research_priority: high
    shared_with_capability_cards:
      - P0-02
    batch_refs:
      - batch_010
      - batch_012
    candidate_output_effect: 影响候选研究条目如何识别“可内容化动作”，避免只剩空泛“门店日常氛围”。
    forbidden_knowledge_leakage:
      - 真实员工排班行为
      - 真实顾客咨询过程
      - 真实店铺运营节奏
    source_gap_likelihood: medium
    definition: 用于定义门店日常中可被抽象为内容观察单元的动作类型、起止标记与环境依赖。
    applies_when: 当研究目标是提炼可复用的门店日常动作方法时适用。
    does_not_apply_when: 当动作依赖真实员工身份、真实顾客反馈或具体经营流水时不适用。
    counter_boundary: 该cluster只抽象动作单元，不定义谁做过、不定义好坏绩效。
    output_influence: 决定后续研究能否将“门店日常”转为可比较、可拍摄、可复核的动作结构。
    source_dependency: 依赖通用零售动作、培训、展示场景资料；若只能得到实例视频，则降级为source_gap。
    evidence_need: 需要动作定义、起止标记、道具依赖和可视证据需求；不允许基于情节想象补全。
    risk_flags:
      - real_instance_fact_detected
      - unsupported_claim_detected
    duplicate_check_key: store_daily_action__observation_slice_frame
    body_structure_consistency_note: 正文结构应保持“动作单元-触发条件-可见标记-内容用途-禁区”五段式。

  - cluster_id: W5_P0_04_RS02_CL02
    cluster_name: 动作到内容单元的转译槽位
    p0_group: P0-04
    research_card_id: P0-04-RS02
    knowledge_type: general_method
    object_type: CapabilityResearchCluster
    domain_module: action_to_content_unit_translation
    why_required_for_capability: P0-04不是记录动作本身，而是研究动作如何被转译为内容单元；没有槽位设计，动作知识无法进入内容链路。
    knowledge_types:
      - general_method
      - relation_hint
      - routing_hint
      - evidence_requirement
    expected_body_topics:
      - 动作镜头起承转合
      - 动作对应的解释槽位
      - 强观察/弱解释的组合方式
      - 平台提示仅作为研究注释
    required_relations:
      - 依赖动作观察框架
      - 依赖Look/色彩/区位锚点
      - 受授权边界约束
    risk_boundaries:
      - 不得输出发布级脚本
      - 不得固化平台模板为仓内canonical truth
      - 不得引入真实门店口播
    evidence_classes:
      - 内容结构方法资料
      - 短视频与图文内容切片资料
      - 培训演示转内容的方法资料
    source_research_priority: high
    shared_with_capability_cards:
      - P0-01
      - P0-02
    batch_refs:
      - batch_010
      - batch_012
      - batch_013
    candidate_output_effect: 影响候选研究条目如何描述“动作-解释-镜头”的映射关系，为后续CandidatePack准备研究结构而非生产内容。
    forbidden_knowledge_leakage:
      - 真实脚本文本
      - 真实门店口播
      - 真实发布表现数据
    source_gap_likelihood: high
    definition: 用于定义一般化门店动作如何映射为内容单元中的镜头位、解释位、过渡位与收束位。
    applies_when: 当研究需要把动作方法转成可复核的内容结构提示时适用。
    does_not_apply_when: 当任务已要求生成可直接发布脚本、具体标题或成片结构时不适用。
    counter_boundary: 该cluster只给研究槽位，不给成片文本，不给平台投放结论。
    output_influence: 决定后续研究文本是否能从动作知识自然过渡到内容结构知识。
    source_dependency: 依赖通用内容结构与培训演示方法来源；若来源高度平台化且不稳定，应仅保留抽象槽位。
    evidence_need: 需要槽位定义、可见动作依赖、解释强度边界和平台提示来源；平台提示不能升级为canonical truth。
    risk_flags:
      - forbidden_object_type
      - unsupported_claim_detected
    duplicate_check_key: action_content_slot__translation_map
    body_structure_consistency_note: 正文结构应保持“动作输入-槽位映射-镜头提示-说明边界-不可直出项”五段式。

  - cluster_id: W5_P0_04_RS02_CL03
    cluster_name: 门店日常内容化风险红线
    p0_group: P0-04
    research_card_id: P0-04-RS02
    knowledge_type: boundary_rule
    object_type: CapabilityResearchCluster
    domain_module: store_daily_contentization_risk_boundary
    why_required_for_capability: 门店日常最容易越界到真实员工、真实顾客、真实门店事实；没有红线cluster，前述动作与转译知识无法安全落在general_only范围内。
    knowledge_types:
      - boundary_rule
      - routing_hint
      - decision_required_candidate
    expected_body_topics:
      - 隐私与实例事实边界
      - 不可写的经营表现与顾客反馈
      - 可保留的一般化角色表达
      - 何时转source_gap或decision_required
    required_relations:
      - 约束所有RS02 cluster
      - 连接授权复核cluster
      - 连接source_gap与excluded items
    risk_boundaries:
      - 不得把风险红线写成授权已通过结论
      - 不得把一般化角色误写成真实员工肖像
      - 不得写成合规法律意见
    evidence_classes:
      - 上传包章程与证据政策
      - 角色/客户风险边界资料
      - 内容风险管理的一般方法资料
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-02
    batch_refs:
      - batch_010
      - batch_013
      - batch_014
    candidate_output_effect: 影响候选研究条目如何在内容化前进行剔除、重写或升级决策，避免实例事实渗漏。
    forbidden_knowledge_leakage:
      - 真实员工隐私
      - 真实顾客对话
      - 真实门店身份标签
    source_gap_likelihood: low
    definition: 用于定义门店日常内容化中的必拦截边界、改写条件和升级路由。
    applies_when: 当研究对象涉及动作展示、角色表达、场景观察时适用。
    does_not_apply_when: 当需要给出法律意见、合同意见或真实主体授权结论时不适用。
    counter_boundary: 该cluster是风险路由，不是生产准入，不等于任何readiness提升。
    output_influence: 决定后续研究地图能否稳定停留在general_only而不触发实例泄漏。
    source_dependency: 主要依赖上传包中的章程、证据、readiness与DQ政策；外部来源仅作一般风险方法参考。
    evidence_need: 需要明确哪些信息一律排除、哪些进入source_gap、哪些进入decision_required。
    risk_flags:
      - real_instance_fact_detected
      - enabled_readiness_value
      - p0_00_domain_leak
    duplicate_check_key: store_daily_contentization__risk_redline
    body_structure_consistency_note: 正文结构应保持“风险对象-触发条件-处理动作-替代表达-不可越权项”五段式。

  - cluster_id: W5_P0_04_RS03_CL01
    cluster_name: 陈列动作SOP节点化框架
    p0_group: P0-04
    research_card_id: P0-04-RS03
    knowledge_type: general_method
    object_type: CapabilityResearchCluster
    domain_module: merchandising_action_sop_nodes
    why_required_for_capability: 若不把陈列动作拆成SOP节点，门店动作只能被笼统描述，无法用于培训转译、内容观察或后续复核。
    knowledge_types:
      - general_method
      - relation_hint
      - evidence_requirement
    expected_body_topics:
      - 陈列前检查/实施/复核的一般节点
      - 节点输入与节点输出
      - 节点之间的依赖顺序
      - 节点可见化表达
    required_relations:
      - 连接日常动作观察
      - 连接培训演示结构
      - 连接异常处理cluster
    risk_boundaries:
      - 不得写真实门店SOP文档
      - 不得写真实库存或上新流程
      - 不得写真实销售转化结果
    evidence_classes:
      - 通用陈列SOP方法资料
      - 培训流程设计资料
      - 零售操作分解资料
    source_research_priority: high
    shared_with_capability_cards:
      - P0-02
      - P0-05
    batch_refs:
      - batch_012
      - batch_006
      - batch_011
    candidate_output_effect: 影响候选研究条目如何从“陈列动作”升级为“节点化流程知识”，提升可复核性。
    forbidden_knowledge_leakage:
      - 真实SOP截图
      - 真实操作记录
      - 真实补货与销售联动数据
    source_gap_likelihood: medium
    definition: 用于定义陈列动作在一般化SOP中的最小节点、触发条件、前后依赖和观察标记。
    applies_when: 当研究需要把陈列动作转为培训、演示、观察或内容提示节点时适用。
    does_not_apply_when: 当流程依赖真实门店运营数据、真实库存策略或真实制度时不适用。
    counter_boundary: 该cluster只保留可泛化节点，不承诺节点在任何组织内都等价。
    output_influence: 决定后续研究能否把陈列动作说清楚到“能观察、能检查、能转译”的粒度。
    source_dependency: 依赖一般化SOP与陈列方法资料；来源若仅为组织内部手册则应降级。
    evidence_need: 需要节点定义、输入输出、先后约束和可视标记证据；结果性claim不在此cluster内。
    risk_flags:
      - unsupported_claim_detected
      - real_instance_fact_detected
    duplicate_check_key: merchandising_sop__node_framework
    body_structure_consistency_note: 正文结构应保持“节点名-触发条件-动作内容-复核标记-边界”五段式。

  - cluster_id: W5_P0_04_RS03_CL02
    cluster_name: 培训与讲解SOP的演示三段式
    p0_group: P0-04
    research_card_id: P0-04-RS03
    knowledge_type: general_method
    object_type: CapabilityResearchCluster
    domain_module: training_sop_demo_triptych
    why_required_for_capability: 培训与SOP若不能转成演示三段式，后续只能落在抽象说明，缺少filmability与reviewability。
    knowledge_types:
      - general_method
      - relation_hint
      - routing_hint
    expected_body_topics:
      - 演示前提示/演示中动作/演示后复核
      - 讲解与动作的同步关系
      - 镜头与站位的最小提示
      - 非发布级训练内容边界
    required_relations:
      - 依赖SOP节点化框架
      - 依赖动作到内容槽位
      - 受授权边界约束
    risk_boundaries:
      - 不得写真实培训口径
      - 不得写真实销售话术
      - 不得生成可直接播出的培训脚本
    evidence_classes:
      - 通用培训演示设计资料
      - 动作示范方法资料
      - 内容镜头组织方法资料
    source_research_priority: high
    shared_with_capability_cards:
      - P0-01
      - P0-02
    batch_refs:
      - batch_012
      - batch_010
    candidate_output_effect: 影响候选研究条目如何定义培训/讲解内容的可见组织方式，为后续验证提供结构提示。
    forbidden_knowledge_leakage:
      - 真实培训录音
      - 真实店员销售话术
      - 真实考核标准
    source_gap_likelihood: high
    definition: 用于定义培训与讲解类陈列知识如何按“前提示-中演示-后复核”转译为非发布级研究结构。
    applies_when: 当研究需要抽象演示组织方式、而非生成脚本时适用。
    does_not_apply_when: 当任务意图转向直接培训材料、直播台词或实际门店话术时不适用。
    counter_boundary: 该cluster是研究型演示结构，不是生产型培训材料，不构成任何授权。
    output_influence: 决定后续研究文本是否足够filmable，同时不越界到生产级脚本。
    source_dependency: 依赖通用培训演示与说明结构资料；若只来自实例培训视频，则应抽象化后保留。
    evidence_need: 需要演示段落关系、动作/说明同步规则与复核节点证据需求。
    risk_flags:
      - forbidden_object_type
      - enabled_readiness_value
    duplicate_check_key: training_sop__demo_triptych
    body_structure_consistency_note: 正文结构应保持“前提示-中演示-后复核-转内容用途-禁区”五段式。

  - cluster_id: W5_P0_04_RS03_CL03
    cluster_name: 异常、回退与复核切换规则
    p0_group: P0-04
    research_card_id: P0-04-RS03
    knowledge_type: boundary_rule
    object_type: CapabilityResearchCluster
    domain_module: sop_exception_review_handoff
    why_required_for_capability: SOP转译最怕把例外当常规；需要定义何时停、何时回退、何时升级复核，才能保持研究地图可执行且不越权。
    knowledge_types:
      - boundary_rule
      - routing_hint
      - decision_required_candidate
    expected_body_topics:
      - 节点缺失时的回退
      - 证据不足时的source_gap路由
      - 授权不明时的decision_required路由
      - 异常项的最小记录格式
    required_relations:
      - 约束所有RS03 cluster
      - 连接RS04授权边界
      - 连接全图decision_required items
    risk_boundaries:
      - 不得写route mutation
      - 不得给出真实组织复核结论
      - 不得把例外处理写成系统实现方案
    evidence_classes:
      - 上传包章程与证据政策
      - 流程异常管理的一般方法资料
    source_research_priority: medium
    shared_with_capability_cards:
      - P0-00
    batch_refs:
      - batch_012
      - batch_014
    candidate_output_effect: 影响候选研究条目在遇到证据缺口、边界冲突、控制面泄漏时的停机与转向方式。
    forbidden_knowledge_leakage:
      - 真实审批流
      - 真实运营异常单
      - 真实门店复核记录
    source_gap_likelihood: low
    definition: 用于定义研究层SOP转译中的回退条件、升级条件与复核切换条件。
    applies_when: 当研究需要处理例外、缺证或边界冲突时适用。
    does_not_apply_when: 当任务要求直接配置系统工作流、运行时路由或组织审批流程时不适用。
    counter_boundary: 该cluster只定义研究路由原则，不实现DIFY或任何runtime artifact。
    output_influence: 决定研究地图遇到不确定项时能否停在合规边界内，而不是靠猜测补全。
    source_dependency: 主要依赖上传包的路由与readiness边界政策；外部资料只可补充通用异常管理方法。
    evidence_need: 需要异常分类、回退触发、升级触发和证据不足判断标准。
    risk_flags:
      - p0_00_domain_leak
      - enabled_readiness_value
      - forbidden_object_type
    duplicate_check_key: sop_exception__review_handoff_rule
    body_structure_consistency_note: 正文结构应保持“异常触发-处理分流-保留信息-禁做事项-升级点”五段式。

  - cluster_id: W5_P0_04_RS04_CL01
    cluster_name: 零售角色-动作-权限的一般化矩阵
    p0_group: P0-04
    research_card_id: P0-04-RS04
    knowledge_type: general_method
    object_type: CapabilityResearchCluster
    domain_module: retail_role_action_authorization_matrix
    why_required_for_capability: 门店日常与陈列动作内容化会接触角色表达，但P0-04只允许general_only；因此必须先有角色-动作-权限的一般化矩阵。
    knowledge_types:
      - general_method
      - boundary_rule
      - relation_hint
    expected_body_topics:
      - 角色类型的抽象层
      - 哪些动作可被一般化表达
      - 哪些信息必须脱敏或排除
      - 权限与动作的最小耦合
    required_relations:
      - 约束RS02与RS03
      - 连接授权复核路由
      - 连接excluded items
    risk_boundaries:
      - 不得写真实岗位制度
      - 不得写真实员工层级
      - 不得写真实加盟组织结构
    evidence_classes:
      - 角色表达的一般方法资料
      - 内容权限边界资料
      - 上传包章程与证据政策
    source_research_priority: high
    shared_with_capability_cards:
      - P0-02
      - P0-00
    batch_refs:
      - batch_013
      - batch_014
    candidate_output_effect: 影响候选研究条目如何安全使用“角色”作为方法锚点，而不滑向真实组织事实。
    forbidden_knowledge_leakage:
      - 真实员工姓名与职责
      - 真实加盟门店角色结构
      - 真实组织授权信息
    source_gap_likelihood: medium
    definition: 用于定义一般化零售角色、可关联动作类型与权限边界之间的最小矩阵。
    applies_when: 当研究需要表达“某类角色可执行某类一般动作”时适用。
    does_not_apply_when: 当表达依赖真实岗位编制、真实人事制度或真实组织授权关系时不适用。
    counter_boundary: 该cluster输出的是抽象矩阵，不是组织架构，也不是合规结论。
    output_influence: 决定后续研究是否能够保留角色视角，同时不越界到实例事实。
    source_dependency: 主要依赖上传包边界政策与一般化角色表达资料；实例型用工或授权资料不可直接吸收。
    evidence_need: 需要角色抽象层级、动作类型、权限边界和排除项的明确定义。
    risk_flags:
      - real_instance_fact_detected
      - p0_00_domain_leak
    duplicate_check_key: retail_role_action__authorization_matrix
    body_structure_consistency_note: 正文结构应保持“角色抽象-可关联动作-权限边界-排除项-复核提示”五段式。

  - cluster_id: W5_P0_04_RS04_CL02
    cluster_name: 加盟与授权信息的泛化改写规则
    p0_group: P0-04
    research_card_id: P0-04-RS04
    knowledge_type: boundary_rule
    object_type: CapabilityResearchCluster
    domain_module: franchise_authorization_generalization_rule
    why_required_for_capability: 研究对象会触碰加盟、授权、门店归属等高风险信息；必须提前规定只保留方法层，实例事实一律转source_gap或decision_required。
    knowledge_types:
      - boundary_rule
      - routing_hint
      - decision_required_candidate
      - exclusion_note
    expected_body_topics:
      - 加盟相关信息的抽象层级
      - 合同/归属/授权事实的一律排除
      - 允许保留的泛化描述
      - 何时升级 founder review
    required_relations:
      - 约束所有RS04 cluster
      - 连接source_gap items
      - 连接founder_review items
    risk_boundaries:
      - 不得写真实加盟事实
      - 不得写合同义务
      - 不得提供法律或经营意见
    evidence_classes:
      - 上传包章程与证据政策
      - 授权边界方法资料
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
    batch_refs:
      - batch_013
      - batch_014
      - batch_007
    candidate_output_effect: 影响候选研究条目如何在涉及加盟/授权语义时自动降级，防止实例泄漏。
    forbidden_knowledge_leakage:
      - 真实加盟协议
      - 真实品牌授权链
      - 真实门店归属事实
    source_gap_likelihood: low
    definition: 用于定义加盟与授权相关信息在general_only研究中的改写、排除与升级规则。
    applies_when: 当研究文本出现加盟、授权、门店归属、审阅权限等词汇时适用。
    does_not_apply_when: 当任务要求判断某真实主体是否被授权、是否合规、是否可发布时不适用。
    counter_boundary: 该cluster不是合规结论，不提供合同解释，只给研究改写与排除规则。
    output_influence: 决定研究地图能否在高风险语义区仍保持一般化、可复核、可路由。
    source_dependency: 主要依赖上传包政策；外部资料只能补充一般授权边界概念，不可替代实例审查。
    evidence_need: 需要明确一律排除项、可改写项、升级项及其触发条件。
    risk_flags:
      - real_instance_fact_detected
      - forbidden_object_type
      - enabled_readiness_value
    duplicate_check_key: franchise_authorization__generalization_rule
    body_structure_consistency_note: 正文结构应保持“高风险词-可保留抽象-必须排除-升级条件-不可越权项”五段式。

  - cluster_id: W5_P0_04_RS04_CL03
    cluster_name: 内容前复核与授权路由提示
    p0_group: P0-04
    research_card_id: P0-04-RS04
    knowledge_type: routing_hint
    object_type: CapabilityResearchCluster
    domain_module: content_precheck_review_routing
    why_required_for_capability: 门店陈列与培训内容化在进入后续仓内流程前，需要最小的“前复核”研究提示，否则容易把研究文本误送到生产链路。
    knowledge_types:
      - routing_hint
      - boundary_rule
      - decision_required_candidate
    expected_body_topics:
      - 进入后续仓路前的前复核提示
      - 授权不明的升级路径
      - 控制面与业务面分界
      - readiness恒为false的约束
    required_relations:
      - 约束全图所有cluster
      - 连接decision_required items
      - 连接forbidden_output_attestation
    risk_boundaries:
      - 不得实现工作流
      - 不得暗示CandidatePack已创建
      - 不得生成任何production-ready资产
    evidence_classes:
      - 上传包readiness政策
      - source/claim/evidence政策
      - 控制面边界政策
    source_research_priority: medium
    shared_with_capability_cards:
      - P0-00
    batch_refs:
      - batch_014
      - batch_013
    candidate_output_effect: 影响候选研究条目如何在研究阶段被正确标注为未就绪、待验证、待决策。
    forbidden_knowledge_leakage:
      - 真实审批路径
      - 真实系统路由
      - 真实授权状态
    source_gap_likelihood: low
    definition: 用于定义研究地图在未来进入仓内验证前的前复核提示、升级条件与readiness锁定方式。
    applies_when: 当研究输出需要明确“还不能进入生产链路”时适用。
    does_not_apply_when: 当任务要求生成DIFY工作流、Serving投影、RAG bundle或任何落地工件时不适用。
    counter_boundary: 该cluster只提供研究期前复核提示，不构成运行时路由或系统实现。
    output_influence: 决定本图能否持续保持research-only状态，不被误读为可直接落地资产。
    source_dependency: 主要依赖上传包中的readiness与边界政策，不依赖实例数据。
    evidence_need: 需要明确前复核触发、升级点、readiness锁定与禁止输出类型。
    risk_flags:
      - enabled_readiness_value
      - forbidden_object_type
      - p0_00_domain_leak
    duplicate_check_key: research_precheck__review_routing
    body_structure_consistency_note: 正文结构应保持“前复核对象-触发条件-升级路由-锁定状态-禁出物”五段式。

relation_hints:
  - relation_id: RH01
    object_type: RelationHint
    from_cluster_id: W5_P0_04_RS01_CL01
    to_cluster_id: W5_P0_04_RS02_CL02
    relation_type: prerequisite
    note: Look拆解骨架为动作-内容转译提供可见对象与说明对象。
  - relation_id: RH02
    object_type: RelationHint
    from_cluster_id: W5_P0_04_RS01_CL02
    to_cluster_id: W5_P0_04_RS03_CL02
    relation_type: semantic_support
    note: 主题与色彩故事为培训/讲解中的解释层提供一般化语义节点。
  - relation_id: RH03
    object_type: RelationHint
    from_cluster_id: W5_P0_04_RS01_CL03
    to_cluster_id: W5_P0_04_RS02_CL01
    relation_type: scene_anchor
    note: 陈列区位与视觉锚点决定门店日常动作观察的场景入口。
  - relation_id: RH04
    object_type: RelationHint
    from_cluster_id: W5_P0_04_RS02_CL01
    to_cluster_id: W5_P0_04_RS03_CL01
    relation_type: shared_anchor
    note: 动作观察切片与SOP节点化共用“动作单元-触发条件-结束标记”。
  - relation_id: RH05
    object_type: RelationHint
    from_cluster_id: W5_P0_04_RS02_CL03
    to_cluster_id: W5_P0_04_RS04_CL01
    relation_type: constraint
    note: 门店日常风险红线需被角色-动作-权限矩阵进一步约束。
  - relation_id: RH06
    object_type: RelationHint
    from_cluster_id: W5_P0_04_RS03_CL03
    to_cluster_id: W5_P0_04_RS04_CL03
    relation_type: escalation
    note: SOP异常、缺证和边界冲突进入前复核与授权路由提示。
  - relation_id: RH07
    object_type: RelationHint
    from_cluster_id: W5_P0_04_RS04_CL02
    to_cluster_id: W5_P0_04_RS02_CL02
    relation_type: hard_boundary
    note: 任何涉及加盟/授权实例语义的内容单元转译都必须先降级。
  - relation_id: RH08
    object_type: RelationHint
    from_cluster_id: W5_P0_04_RS04_CL03
    to_cluster_id: W5_P0_04_RS01_CL01
    relation_type: global_lock
    note: 全图所有cluster均受readiness恒为false与research-only边界锁定。

source_gap_items:
  - item_id: SG01
    object_type: SourceGapItem
    related_research_card_id: P0-04-RS01
    related_cluster_ids:
      - W5_P0_04_RS01_CL01
      - W5_P0_04_RS01_CL03
    gap_statement: 通用服装陈列区位术语与内容拍摄锚点之间缺少稳定、公开、非实例化的统一来源。
    why_it_matters: 若无统一术语，Look观察与镜头锚点难以做跨来源拼接。
    minimum_next_source_need: 需寻找一般化视觉陈列方法、零售空间观察方法、非品牌化拍摄方法三类来源。
    routing: source_gap

  - item_id: SG02
    object_type: SourceGapItem
    related_research_card_id: P0-04-RS01
    related_cluster_ids:
      - W5_P0_04_RS01_CL02
    gap_statement: 色彩故事在门店陈列内容化中的层级表达，公开来源可能停留在搭配建议层，缺少更稳的陈列叙事层。
    why_it_matters: 会影响主题-色彩-内容转译关系是否可精细化。
    minimum_next_source_need: 需补充一般化配色叙事、视觉陈列主题组织与服装Look关系资料。
    routing: source_gap

  - item_id: SG03
    object_type: SourceGapItem
    related_research_card_id: P0-04-RS02
    related_cluster_ids:
      - W5_P0_04_RS02_CL01
      - W5_P0_04_RS02_CL02
    gap_statement: 门店日常动作到内容单元的转译资料，公开来源可能高度平台化且分散。
    why_it_matters: 会影响动作-镜头-说明槽位是否能保持一般化而非模板化。
    minimum_next_source_need: 需补充门店动作观察、短内容结构、培训演示转内容三类非实例来源。
    routing: source_gap

  - item_id: SG04
    object_type: SourceGapItem
    related_research_card_id: P0-04-RS03
    related_cluster_ids:
      - W5_P0_04_RS03_CL01
      - W5_P0_04_RS03_CL02
    gap_statement: 公开可验证的通用陈列培训/SOP节点资料可能不足，且容易夹带真实组织流程。
    why_it_matters: 会影响SOP节点化与演示三段式的证据密度。
    minimum_next_source_need: 需优先寻找一般化培训设计、操作分解、演示结构来源，并剔除实例手册。
    routing: source_gap

  - item_id: SG05
    object_type: SourceGapItem
    related_research_card_id: P0-04-RS04
    related_cluster_ids:
      - W5_P0_04_RS04_CL01
      - W5_P0_04_RS04_CL02
    gap_statement: 零售角色-动作-权限的一般化来源，对加盟/授权边界的抽象颗粒度可能不一致。
    why_it_matters: 会影响角色矩阵与授权改写规则的统一程度。
    minimum_next_source_need: 需补充一般化角色表达、内容权限边界、非合同型授权方法资料。
    routing: source_gap

decision_required_items:
  - item_id: DR01
    object_type: DecisionRequiredItem
    related_research_card_id: P0-04-RS04
    question: 授权与复核提示中，哪些内容仍属于P0-04方法层，哪些已构成P0-00控制面规则。
    why_decision_required: 若划分不清，容易出现p0_00_domain_leak或把P0-04写成编排系统。
    blocking_scope:
      - W5_P0_04_RS04_CL01
      - W5_P0_04_RS04_CL03
    suggested_route: decision_required

  - item_id: DR02
    object_type: DecisionRequiredItem
    related_research_card_id: P0-04-RS03
    question: 陈列培训SOP与销售SOP的共享节点是否要在后续仓内拆分为两个独立词表。
    why_decision_required: 若不决策，后续cluster merge可能产生同质化或边界混乱。
    blocking_scope:
      - W5_P0_04_RS03_CL01
      - W5_P0_04_RS03_CL02
    suggested_route: decision_required

  - item_id: DR03
    object_type: DecisionRequiredItem
    related_research_card_id: P0-04-RS01
    question: 色彩故事是否由P0-03共享术语承接，还是在P0-04内维持陈列语义层的局部词表。
    why_decision_required: 若不决策，RS01与P0-03/P0-05之间可能出现重复建模。
    blocking_scope:
      - W5_P0_04_RS01_CL02
    suggested_route: decision_required

  - item_id: DR04
    object_type: DecisionRequiredItem
    related_research_card_id: P0-04-RS02
    question: 门店日常片段是否允许保留极轻量场景标签，还是必须完全退化为动作+道具抽象层。
    why_decision_required: 这会影响filmability与risk boundary之间的平衡。
    blocking_scope:
      - W5_P0_04_RS02_CL01
      - W5_P0_04_RS02_CL02
    suggested_route: decision_required

excluded_items:
  - item_id: EX01
    object_type: ExcludedResearchItem
    reason: 真实门店陈列巡检记录属于实例事实与运营记录，超出general_only边界。
    excluded_example_type: real_store_display_record
  - item_id: EX02
    object_type: ExcludedResearchItem
    reason: 真实顾客反馈、真实导购对话、真实成交流程属于顾客/人员实例路径。
    excluded_example_type: customer_feedback_or_staff_dialogue
  - item_id: EX03
    object_type: ExcludedResearchItem
    reason: 任何可直接发布脚本、培训成片文案、直播话术都属于禁止输出。
    excluded_example_type: publishable_script_or_training_text
  - item_id: EX04
    object_type: ExcludedResearchItem
    reason: CandidatePack、KE、Serving Projection、RAG context bundle、DIFY workflow、approved_passage_text均不在本任务范围。
    excluded_example_type: production_or_repository_artifact

shared_cluster_merge_items:
  - item_id: SM01
    object_type: SharedClusterMergeCandidate
    candidate_clusters:
      - W5_P0_04_RS02_CL01
      - W5_P0_04_RS03_CL01
    merge_or_keep_split: keep_split_with_shared_anchor
    reason: 两者共享动作单元与触发条件，但前者面向观察切片，后者面向SOP节点，不能直接并为一个cluster。

  - item_id: SM02
    object_type: SharedClusterMergeCandidate
    candidate_clusters:
      - W5_P0_04_RS01_CL02
    shared_with_capability_cards:
      - P0-03
      - P0-05
    merge_or_keep_split: future_shared_lexicon_possible
    reason: 主题与色彩故事存在跨卡术语复用潜力，但P0-04仍需保留陈列转内容视角。

  - item_id: SM03
    object_type: SharedClusterMergeCandidate
    candidate_clusters:
      - W5_P0_04_RS02_CL02
      - W5_P0_04_RS03_CL02
    merge_or_keep_split: keep_split_with_relation_link
    reason: 一个处理动作到内容单元槽位，另一个处理培训演示三段式，关系紧密但职责不同。

  - item_id: SM04
    object_type: SharedClusterMergeCandidate
    candidate_clusters:
      - W5_P0_04_RS02_CL03
      - W5_P0_04_RS04_CL03
    merge_or_keep_split: keep_split
    reason: 前者是内容化风险红线，后者是前复核路由提示，边界与路由不可混写。

founder_review_items:
  - item_id: FR01
    object_type: DecisionRequiredItem
    topic: 若后续希望把加盟/授权相关研究提升为可复用规则，需要额外确认其是否越过general_only边界。
    reason: 该主题极易滑入实例合同、真实授权与控制面编排。

forbidden_output_attestation:
  not_candidatepack: true
  not_source_pack: true
  not_KE: true
  not_serving_projection: true
  not_rag_context_bundle: true
  not_dify_workflow: true
  not_approved_passage_text: true
  not_publishable_script: true
  not_production_ready_knowledge: true
  not_formal_capability_card: true
  research_subcards_not_rewritten_as_capability_cards: true
  count_budget_not_acceptance_kpi: true

required_execution_asset_types:
  - 研究型cluster定义清单
  - 通用陈列观察术语表
  - Look/主题/色彩关系图
  - 动作-镜头-说明槽位映射表
  - SOP节点与演示三段式骨架
  - 角色-动作-权限矩阵
  - source_gap台账
  - decision_required台账
  - excluded item清单
  - DQ与边界自检表

required_dq_checks:
  - anti_empty_language
  - anti_template
  - irreplaceable_anchor
  - claim_evidence_separation
  - filmability
  - platform_native_hint_only
  - persona_brand_customer_risk
  - counter_boundary_present
  - duplicate_cluster_split
  - control_plane_leak_guard

fallback_conditions:
  - 若某一知识点只能由真实品牌、真实SKU、真实门店、真实人物、真实顾客反馈支撑，则转source_gap或excluded，不做一般化硬写。
  - 若某一关系只能借助实例合同、真实授权状态或真实运营记录成立，则转decision_required。
  - 若外部资料只能支持模板化表达而无法提供可见锚点，则降级为弱cluster或source_gap。
  - 若出现效果、性能、舒适度、销售结果等hard claim，则仅保留evidence_need，不接收为已成立知识。

blocking_conditions:
  - real_brand_or_sku_or_store_or_person_detected
  - real_customer_feedback_detected
  - unsupported_hard_claim_detected
  - full_display_system_claim_detected
  - p0_00_domain_leak_detected
  - candidatepack_or_ke_or_rag_or_dify_output_detected
  - enabled_readiness_value_detected
  - count_used_as_acceptance_kpi_detected

unresolved_decisions:
  - P0-04中的授权/复核提示与P0-00控制面边界需要后续明确切分。
  - 色彩故事术语是否由P0-03共享承接仍待决策。
  - 培训SOP与销售SOP共享节点是否拆分仍待决策。
  - 门店日常场景标签的允许粒度仍待决策。

source_gap_seed:
  - 通用视觉陈列术语与镜头锚点来源
  - 主题/色彩故事在服装陈列中的一般化结构来源
  - 门店日常动作切片与内容转译来源
  - 通用陈列培训与演示SOP来源
  - 零售角色与授权边界的一般化来源

self_check:
  - 已覆盖P0-04-RS01、P0-04-RS02、P0-04-RS03、P0-04-RS04四张research subcard。
  - 每张subcard均给出required_knowledge_clusters。
  - 所有cluster均包含用户要求字段与schema思路字段。
  - 未输出真实品牌、真实SKU、真实门店、真实人物、真实顾客反馈。
  - 未生成CandidatePack、Source Pack、KE、Serving Projection、RAG context bundle、DIFY workflow、approved_passage_text。
  - 所有readiness保持false。
  - 未把3600写成验收KPI。
  - 未把research_subcard误写为正式capability card。
  - 未新增P0之外能力组。
  - 仅使用上传矩阵中已存在且编号不超过batch_014的batch引用：batch_003、batch_006、batch_007、batch_010、batch_011、batch_012、batch_013、batch_014。

readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false