map_id: W3_P0_02_role_perspective_knowledge_map
output_file: W3_P0_02_role_perspective_knowledge_map.yaml
map_version: v0.1
status: research_planning_only
cell_id: W3
prompt_id: WEB-DEEP-RESEARCH-W3-P0-02-ROLE-PERSPECTIVE-MAP-001
pack_id: web_gpt_upload_pack_v0_1
knowledge_mode: general_only
capability_group_id: P0-02
capability_group_name: 角色视角 / 组织生态内容知识地图
not_formal_capability_card: true
not_registry: true
not_candidatepack: true
not_KE: true

source_inputs:
  - file_name: 09_upload_pack_manifest.json
    usage_role: 上传包文件权威
    authority_note: 本轮上传包文件清单唯一权威
  - file_name: 01_research_charter_and_redlines.md
    usage_role: 总体 redlines
    authority_note: general_only、P0 选定范围、A2 support-only、禁止输出、readiness false
  - file_name: 04_research_map_output_schema.yaml
    usage_role: 输出 schema
    authority_note: 顶层字段、cluster 必填字段、禁用对象类型、validation rules
  - file_name: 02_p0_capability_and_subcards.yaml
    usage_role: P0-02 子卡范围
    authority_note: 锁定 P0-02-RS01 至 P0-02-RS04
  - file_name: 03_batch_allocation_matrix.csv
    usage_role: batch 预算引用
    authority_note: 仅可引用 batch_001 至 batch_014，count 仅是 coverage budget
  - file_name: 05_source_claim_evidence_policy.md
    usage_role: claim / evidence / routing 边界
    authority_note: 实例事实、hard claim、evidence need、source gap、decision required
  - file_name: 06_candidatepack_and_readiness_policy.md
    usage_role: readiness 与下游边界
    authority_note: 不得产出 CandidatePack、KE、Serving、RAG、DIFY、approved passage
  - file_name: 07_dq_anti_homogeneity_policy.md
    usage_role: DQ 与 anti-generic 质量约束
    authority_note: anti-empty、anti-template、anchor、filmability、persona risk
  - file_name: 08_optional_reference_digest.md
    usage_role: optional reference only
    authority_note: 仅可作结构灵感，不得覆盖 charter / schema / matrix

source_precedence_policy:
  - 09_upload_pack_manifest.json 为本轮上传包文件权威
  - optional reference 不得写成 canonical truth
  - 若 optional reference 与 charter / schema / matrix 冲突，以 charter / schema / matrix 为准

p0_scope:
  selected_scope: [P0-02]
  selected_scope_note: 仅覆盖 P0-02，不得宣称 full Part A coverage
  forbidden_scope_expansions:
    - 不得新增 P0 之外能力组
    - 不得把 research_subcard 写成正式 capability card
    - 不得让 P0-00 生成普通领域知识
    - 不得把 A2 support-only 误写成完整陈列系统

research_subcard_refs:
  - research_card_id: P0-02-RS01
    theme: role language and tone
    knowledge_focus: role voice, role tone, and general persona expression
    primary_batches: [batch_008, batch_010]
    secondary_batches: [batch_007]
    forbidden_scope: [real_person_quote, staff_fact, authorization_claim]
    required_execution_asset_types: [role_voice_register_matrix, tone_risk_calibration_grid, persona_surface_boundary_note]
    required_dq_checks: [anti_empty_language, anti_template_with_apparel_retail_anchor, role_anchor_present, claim_evidence_separation, no_real_person_quote]
    required_knowledge_clusters: [P0-02-RS01-C01, P0-02-RS01-C02]
    fallback_conditions:
      - 角色口吻缺锚点时，只保留任务姿态、信息密度、限制语
      - 不能安全 role 化时，降级为 role-neutral 方法说明
    blocking_conditions:
      - 需要真实员工言论、真实培训记录、真实授权背书时阻断
      - 接近可直接发布脚本或广告口播时阻断
    unresolved_decisions:
      - 是否需要后续 repository-side 统一 role naming vocabulary
    source_gap_seed:
      - 若未来需要真实角色语料，必须转实例 source intake
    self_check:
      covers_subcard_scope: true
      contains_required_cluster_refs: true
      contains_instance_facts: false
      contains_readiness_true: false

  - research_card_id: P0-02-RS02
    theme: organization ecosystem perspective
    knowledge_focus: organization role views and ecosystem content perspectives
    primary_batches: [batch_010, batch_013]
    secondary_batches: [batch_006]
    forbidden_scope: [real_org_fact, employee_story, private_operation_fact]
    required_execution_asset_types: [org_ecology_role_grid, perspective_handoff_map, public_safe_vs_private_ops_boundary_sheet]
    required_dq_checks: [anti_empty_language, anti_template_with_org_action_anchor, ecosystem_role_anchor_present, public_safe_boundary_check, no_real_org_fact]
    required_knowledge_clusters: [P0-02-RS02-C01, P0-02-RS02-C02]
    fallback_conditions:
      - 生态职责无法细分时，仅保留通用角色功能层
      - 关系证据不足时，仅保留 relation hint
    blocking_conditions:
      - 需要真实组织架构、加盟条款、库存或渠道事实时阻断
    unresolved_decisions:
      - 门店角色与加盟角色的主责词表由 P0-02 还是 P0-04 维护
    source_gap_seed:
      - 若后续要落 franchise / channel / partner 实例授权，需独立 source path
    self_check:
      covers_subcard_scope: true
      contains_required_cluster_refs: true
      contains_instance_facts: false
      contains_readiness_true: false

  - research_card_id: P0-02-RS03
    theme: audience and emotion axis
    knowledge_focus: audience framing, emotion control, and role-to-trust patterns
    primary_batches: [batch_008, batch_009]
    secondary_batches: [batch_011]
    forbidden_scope: [customer_feedback, demographic_fact, sensitive_person_data]
    required_execution_asset_types: [audience_distance_matrix, emotion_temperature_ladder, trust_signal_evidence_gate]
    required_dq_checks: [anti_empty_language, anti_template_with_audience_stage_anchor, no_customer_feedback_as_fact, no_sensitive_person_data, evidence_gate_present]
    required_knowledge_clusters: [P0-02-RS03-C01, P0-02-RS03-C02]
    fallback_conditions:
      - 受众画像无法安全细化时，仅保留 knowledge distance 与 decision stage
      - 情绪策略可能被误读为承诺时，降级为中性说明
    blocking_conditions:
      - 需要真实顾客反馈、敏感属性、身体结果案例、转化证明时阻断
    unresolved_decisions:
      - audience stage 是否要与 P0-05 共建共享字典
    source_gap_seed:
      - 若未来要引入评论、互动、问答实例，需单独做隐私与实例边界
    self_check:
      covers_subcard_scope: true
      contains_required_cluster_refs: true
      contains_instance_facts: false
      contains_readiness_true: false

  - research_card_id: P0-02-RS04
    theme: role authorization boundary
    knowledge_focus: role authorization, consent boundary, and source gap triggers
    primary_batches: [batch_013, batch_001]
    secondary_batches: [batch_014]
    forbidden_scope: [consent_claim, real_person_fact, publishable_role_story]
    required_execution_asset_types: [authorization_surface_matrix, story_reference_redline_table, escalation_trigger_map]
    required_dq_checks: [anti_empty_language, strict_authorization_boundary, instance_fact_route_away, consent_claim_block, readiness_false_lock]
    required_knowledge_clusters: [P0-02-RS04-C01, P0-02-RS04-C02]
    fallback_conditions:
      - 授权边界无实例证据时，只保留可说方法与不可说事实的切分
      - consent 不明确时，直接降级到 source gap 或 excluded
    blocking_conditions:
      - 需要真实同意、真实授权、真实身份、真实合作关系时阻断
      - 把角色内容包装成真实人物故事或真实组织声明时阻断
    unresolved_decisions:
      - 是否需要单独维护 role authorization trigger vocabulary
    source_gap_seed:
      - 若未来需要真实培训、真实顾客、真实加盟、真实门店授权，需单列 intake and review
    self_check:
      covers_subcard_scope: true
      contains_required_cluster_refs: true
      contains_instance_facts: false
      contains_readiness_true: false

required_knowledge_clusters:
  - cluster_id: P0-02-RS01-C01
    cluster_name: 角色发声寄存器矩阵
    p0_group: P0-02
    research_card_id: P0-02-RS01
    knowledge_type: general_method
    knowledge_types: [general_method, relation_hint]
    object_type: CapabilityResearchCluster
    domain_module: role_voice_system
    definition: 定义角色在组织生态内容中的通用发声寄存器，只讨论表达机制，不指向真实人物、真实头衔、真实组织身份。
    why_required_for_capability: 角色视角内容若无 role voice 结构，容易滑入真人语录、员工故事或虚假背书。
    applies_when:
      - 需要用角色视角组织通用内容
      - 需要区分讲解型、说明型、观察型、培训型、协同型等 role shell
    does_not_apply_when:
      - 需要复现真实发言、真实口头禅、真实组织声明
      - 需要证明某角色真的拥有某种发言权
    counter_boundary: 允许 role expression，不允许真实人物表达；允许口吻结构，不允许真实立场背书。
    expected_body_topics:
      - 主语选择与叙述站位
      - 信息密度与限制语
      - 动作词、观察词、解释词边界
      - apparel / retail 场景中的 role anchor
    required_relations:
      - depends_on:P0-02-RS04-C01
      - modulated_by:P0-02-RS03-C01
      - shares_boundary_with:P0-01
    risk_boundaries:
      - 不得出现真实人物、真实员工、真实门店角色语料
      - 不得把口吻写成授权 claim
      - 不得生成可直接发布话术
    evidence_classes: [charter_constraint, subcard_scope_reference, dq_policy_anchor]
    source_research_priority: high
    shared_with_capability_cards: [P0-01, P0-04, P0-05]
    batch_refs: [batch_008, batch_010, batch_007]
    candidate_output_effect: 为后续候选观察提供 role voice 分桶与降噪规则，不构成 CandidatePack。
    forbidden_knowledge_leakage: [real_person_quote, staff_fact, brand_statement_fact, publishable_script]
    source_gap_likelihood: medium
    output_influence:
      - 规范后续 role tone 的命名方式
      - 为短视频、图文、培训类研究提示提供角色外壳
      - 只影响 research framing，不产出成稿
    source_dependency: [01_research_charter_and_redlines.md, 02_p0_capability_and_subcards.yaml, 07_dq_anti_homogeneity_policy.md]
    evidence_need: 方法层无需实例佐证；一旦涉及真实角色、授权或真实语录，必须转 source gap / decision required。
    risk_flags: [fake_authority, real_person_quote_leakage, staff_fact_leakage, template_tone_without_anchor]
    duplicate_check_key: role_voice_register_matrix_general_only
    body_structure_consistency_note: 每个寄存器必须同时给出定义、适用条件、不适用条件、反边界与输出影响，避免空泛口吻词。

  - cluster_id: P0-02-RS01-C02
    cluster_name: 语气校准与去人物化边界
    p0_group: P0-02
    research_card_id: P0-02-RS01
    knowledge_type: boundary_rule
    knowledge_types: [general_method, boundary_rule, evidence_requirement]
    object_type: CapabilityResearchCluster
    domain_module: tone_calibration_and_persona_surface
    definition: 建立角色语气与风险梯度的校准方法，并限定只允许任务姿态、观察方式、职责角度等人设表面层，不允许 biography、员工故事、创始人语录、顾客故事。
    why_required_for_capability: P0-02 需要差异化角色表达，但不得把“像一个角色”写成“一个真人”。
    applies_when:
      - 需要校准教育型、提醒型、陪伴型、中性说明型语气
      - 需要处理 persona risk 而不引入人物事实
    does_not_apply_when:
      - 需要真实岗位经历、真实人物故事、真实顾客反馈
      - 需要用情绪热度替代证据或承诺
    counter_boundary: 允许 role surface，不允许 person fact；允许情绪调温，不允许结果承诺。
    expected_body_topics:
      - 语气强度与场景强度匹配
      - 允许的人设表面层
      - 不可写的真人痕迹
      - 高风险 claim 前的降调与限制语
    required_relations:
      - constrained_by:P0-02-RS04-C02
      - modulated_by:P0-02-RS03-C02
      - intersects_with:P0-03
    risk_boundaries:
      - 不得生成员工故事、顾客故事、创始人语录
      - 不得用语气暗示质量、身体效果、舒适度、性能保证
      - 不得让人设表面层变成真实人物画像
    evidence_classes: [charter_constraint, source_boundary_policy, dq_policy_anchor]
    source_research_priority: high
    shared_with_capability_cards: [P0-01, P0-03, P0-04]
    batch_refs: [batch_008, batch_010, batch_007]
    candidate_output_effect: 为后续候选观察建立 tone 梯度与 persona downgrade，不形成任何人物素材或发布文案。
    forbidden_knowledge_leakage: [employee_story, customer_story, founder_quote, body_effect_hint_without_evidence]
    source_gap_likelihood: medium
    output_influence:
      - 约束后续 tone 标签与风险降级方式
      - 避免角色内容滑入故事体或功效体
    source_dependency: [01_research_charter_and_redlines.md, 05_source_claim_evidence_policy.md, 07_dq_anti_homogeneity_policy.md]
    evidence_need: 凡语气中暗含 quality / body effect / comfort / performance / trust proof，必须显式转 evidence need。
    risk_flags: [employee_story_fabrication, customer_story_leakage, emotional_overreach, claim_by_tone_inference]
    duplicate_check_key: tone_calibration_and_depersonalization_boundary
    body_structure_consistency_note: 必须同时给出允许表面层和禁止实例层，不能只写“更温暖”“更专业”。

  - cluster_id: P0-02-RS02-C01
    cluster_name: 组织生态角色网格
    p0_group: P0-02
    research_card_id: P0-02-RS02
    knowledge_type: general_method
    knowledge_types: [general_method, relation_hint]
    object_type: CapabilityResearchCluster
    domain_module: org_ecology_role_grid
    definition: 抽象内容相关角色网格，如上游定义/策划、中游协同/培训、前台讲解/展示、支持/复核、渠道/合作边界等，只保留功能层，不写真实组织架构。
    why_required_for_capability: 组织生态内容如果没有角色网格，会退化成单一口吻，失去生态视角。
    applies_when:
      - 需要分析同一对象在不同角色位置的叙述差异
      - 需要把 apparel / retail 内容拆解为通用组织模块
    does_not_apply_when:
      - 需要真实公司架构图、真实部门职责、真实门店编制
      - 需要真实加盟或渠道合作关系说明
    counter_boundary: 允许职责方向，不允许真实组织事实；允许通用模块，不允许实例 org chart。
    expected_body_topics:
      - 角色功能层级
      - 内容职责与观察接口
      - 不同角色的信息颗粒度
      - 公开可复用的生态视角
    required_relations:
      - feeds:P0-02-RS02-C02
      - constrained_by:P0-02-RS04-C01
      - shared_with:P0-04
    risk_boundaries:
      - 不得写真实组织结构、真实门店运营配置、真实加盟关系
      - 不得把角色网格写成私域经营资料
    evidence_classes: [subcard_scope_reference, batch_budget_reference, dq_policy_anchor]
    source_research_priority: high
    shared_with_capability_cards: [P0-04, P0-05]
    batch_refs: [batch_010, batch_013, batch_006]
    candidate_output_effect: 为后续生态内容提供 role grid，不产出真实组织资料。
    forbidden_knowledge_leakage: [real_org_fact, private_operation_fact, franchise_contract_fact]
    source_gap_likelihood: medium
    output_influence:
      - 支持后续系列化角色分流
      - 避免所有内容都落到单一“店员口吻”
    source_dependency: [02_p0_capability_and_subcards.yaml, 03_batch_allocation_matrix.csv, 07_dq_anti_homogeneity_policy.md]
    evidence_need: 仅允许功能层抽象；任何真实组织、真实岗位、真实合作关系都需独立 source anchor。
    risk_flags: [real_org_fact_leakage, org_chart_invention, over_template_ecology_language]
    duplicate_check_key: org_ecology_role_grid_general_only
    body_structure_consistency_note: 必须体现 apparel / retail 中的对象、动作、过程节点，不能成为通用组织学空模板。

  - cluster_id: P0-02-RS02-C02
    cluster_name: 视角切换与公开安全边界
    p0_group: P0-02
    research_card_id: P0-02-RS02
    knowledge_type: boundary_rule
    knowledge_types: [relation_hint, boundary_rule, routing_hint]
    object_type: CapabilityResearchCluster
    domain_module: perspective_handoff_and_public_safe_boundary
    definition: 描述对象在不同角色间如何发生视角切换与交接，并明确只允许公开安全的职责关系提示，不允许真实流程、真实审批、真实经营数据、真实员工安排。
    why_required_for_capability: 组织生态内容的难点不只是角色列表，更是交接关系与边界；没有边界，生态内容易偷渡运营事实。
    applies_when:
      - 需要把对象从观察、解释、培训、展示等视角进行转译
      - 需要决定某生态素材是 accepted cluster 还是 source gap
    does_not_apply_when:
      - 需要真实 SOP、真实审批流、真实会议结论、真实门店经营参数
    counter_boundary: 允许 relation hint，不允许 process fact；允许公开安全关系，不允许 private ops。
    expected_body_topics:
      - 对象在不同角色中的命名变化
      - 交接节点与上下文切换
      - public-safe 与 private-ops 切断规则
      - accepted / gap / excluded 路由
    required_relations:
      - depends_on:P0-02-RS02-C01
      - downgraded_by:P0-02-RS04-C02
      - shared_boundary_with:P0-00
      - shared_boundary_with:P0-04
    risk_boundaries:
      - 不得写真实 SOP、审批链、培训记录、运营记录
      - 不得以生态视角包装库存、销售、加盟、渠道事实
    evidence_classes: [source_boundary_policy, batch_budget_reference, readiness_boundary_policy]
    source_research_priority: high
    shared_with_capability_cards: [P0-00, P0-04, P0-05]
    batch_refs: [batch_010, batch_013, batch_006]
    candidate_output_effect: 为后续跨角色编排保留 relation hint 与 downgrade 规则，不形成运行时流程。
    forbidden_knowledge_leakage: [operational_record, sales_result_fact, inventory_fact, approval_chain_fact]
    source_gap_likelihood: high
    output_influence:
      - 帮助识别哪些关系只能停留在框架提示层
      - 降低生态内容越界到运营事实的概率
    source_dependency: [01_research_charter_and_redlines.md, 05_source_claim_evidence_policy.md, 06_candidatepack_and_readiness_policy.md]
    evidence_need: 凡涉及真实流程、真实运营或真实合作边界，必须转实例路径，不得留在本图 accepted cluster。
    risk_flags: [operational_fact_leakage, private_ops_overreach, sop_overreach, relation_without_anchor]
    duplicate_check_key: perspective_handoff_and_public_safe_boundary
    body_structure_consistency_note: 交接关系必须对应对象或过程节点锚点，且必须同时给出 route-away 条件。

  - cluster_id: P0-02-RS03-C01
    cluster_name: 受众距离与信息深浅轴
    p0_group: P0-02
    research_card_id: P0-02-RS03
    knowledge_type: general_method
    knowledge_types: [general_method, relation_hint]
    object_type: CapabilityResearchCluster
    domain_module: audience_distance_axis
    definition: 用 knowledge distance、decision stage、interaction intensity 三个安全维度刻画受众，不使用真实人口统计、真实顾客标签或敏感个人数据。
    why_required_for_capability: role tone 与 trust pattern 必须受受众距离控制，否则会滑入想象式用户画像。
    applies_when:
      - 需要区分初识型、比较型、学习型、协同型等非敏感受众阶段
      - 需要为 role voice 和信息颗粒度建立安全受众轴
    does_not_apply_when:
      - 需要真实用户分群、年龄职业收入标签、真实评论分层
    counter_boundary: 允许阶段模型，不允许人群事实；允许信息距离，不允许敏感画像。
    expected_body_topics:
      - knowledge distance
      - decision stage
      - interaction intensity
      - 不同阶段对应的信息深浅
    required_relations:
      - modulates:P0-02-RS01-C01
      - modulates:P0-02-RS01-C02
      - feeds:P0-02-RS03-C02
    risk_boundaries:
      - 不得使用敏感个人数据
      - 不得使用真实顾客反馈替代受众模型
    evidence_classes: [subcard_scope_reference, dq_policy_anchor]
    source_research_priority: high
    shared_with_capability_cards: [P0-01, P0-05]
    batch_refs: [batch_008, batch_009, batch_011]
    candidate_output_effect: 为后续 role-to-audience 研究提供安全维度，不生成真实用户画像。
    forbidden_knowledge_leakage: [customer_feedback, demographic_fact, sensitive_person_data]
    source_gap_likelihood: medium
    output_influence:
      - 提供受众轴标签与信息深浅控制
      - 避免以真实人群事实驱动角色内容
    source_dependency: [02_p0_capability_and_subcards.yaml, 07_dq_anti_homogeneity_policy.md]
    evidence_need: 该轴只可作方法变量；若绑定真实反馈或转化数据，必须转实例路径。
    risk_flags: [demographic_fact_leakage, sensitive_person_data, customer_feedback_as_proxy]
    duplicate_check_key: audience_distance_information_depth_axis
    body_structure_consistency_note: 必须采用非敏感维度，并显式写出 does_not_apply_when。

  - cluster_id: P0-02-RS03-C02
    cluster_name: 情绪温度层与信任信号门控
    p0_group: P0-02
    research_card_id: P0-02-RS03
    knowledge_type: evidence_requirement
    knowledge_types: [general_method, evidence_requirement, boundary_rule]
    object_type: CapabilityResearchCluster
    domain_module: emotion_temperature_and_trust_gate
    definition: 建立中性说明、陪伴指引、审慎提醒、观察拆解等情绪温度层，并区分哪些 trust signal 可作为通用方法保留，哪些一旦出现就必须挂接 evidence need。
    why_required_for_capability: role-to-trust patterns 的关键不在“显得可信”，而在“可信度来源是否被正确分流”。
    applies_when:
      - 需要设计角色与受众的信任距离
      - 需要控制教育、陪伴、提醒等情绪强度
      - 需要识别情绪表达是否侵入 hard claim
    does_not_apply_when:
      - 需要用情绪叙述证明质量、身体效果、舒适度、性能、真实客户满意度
    counter_boundary: 情绪只可调节理解节奏，不得承担事实证明责任。
    expected_body_topics:
      - 情绪温度分层
      - 低风险信任信号
      - 强证据信号
      - 从 accepted cluster 到 source gap 的触发条件
    required_relations:
      - depends_on:P0-02-RS03-C01
      - modulates:P0-02-RS01-C02
      - gated_by:P0-02-RS04-C01
      - intersects_with:P0-03
    risk_boundaries:
      - 不得用情绪替代证据
      - 不得模拟真实顾客感受
      - 不得暗示确定性结果
    evidence_classes: [source_boundary_policy, dq_policy_anchor, charter_constraint]
    source_research_priority: high
    shared_with_capability_cards: [P0-00, P0-03, P0-05]
    batch_refs: [batch_008, batch_009, batch_011]
    candidate_output_effect: 为后续候选观察补上 evidence gate 与 downgrade 触发条件，不生成 claim 成稿。
    forbidden_knowledge_leakage: [customer_story, quality_claim_without_evidence, body_result_claim, authorization_claim]
    source_gap_likelihood: high
    output_influence:
      - 增强信任表达的可审阅性
      - 减少角色话语中的隐性 hard claim 漏检
    source_dependency: [01_research_charter_and_redlines.md, 05_source_claim_evidence_policy.md, 07_dq_anti_homogeneity_policy.md]
    evidence_need: 凡出现 fabric behavior、fit effect、body result、quality、durability、comfort、performance、真实顾客证明或授权背书，都必须有实例证据。
    risk_flags: [hard_claim_without_source, emotional_promise, customer_story_simulation, authorization_by_implication]
    duplicate_check_key: emotion_temperature_and_trust_signal_gate
    body_structure_consistency_note: 必须显式区分低风险信号与强证据信号，不能只写“更有信任感”。

  - cluster_id: P0-02-RS04-C01
    cluster_name: 角色授权表面矩阵
    p0_group: P0-02
    research_card_id: P0-02-RS04
    knowledge_type: boundary_rule
    knowledge_types: [boundary_rule, general_method, routing_hint]
    object_type: CapabilityResearchCluster
    domain_module: authorization_surface_matrix
    definition: 把角色可说的方法层与必须有实例授权的事实层剥离：可说的是观察方法、任务接口、解释结构、风险提示；不可说的是代表权、批准权、同意事实、身份事实、品牌实例声明。
    why_required_for_capability: 角色内容最容易通过头衔感、组织语气、陪伴语气制造默认授权感，本 cluster 用于阻断越权。
    applies_when:
      - 需要定义角色视角的 speakable surface
      - 需要为组织生态内容设定授权边界
    does_not_apply_when:
      - 任务明确进入真实授权、真实身份、真实组织关系
    counter_boundary: 允许表达方法，不允许表达被授权事实；允许职责视角，不允许真实代表权。
    expected_body_topics:
      - 可说的方法层
      - 不可说的事实层
      - 默认背书的危险信号
      - 越权表述拆解
    required_relations:
      - constrains:P0-02-RS01-C01
      - constrains:P0-02-RS02-C01
      - feeds:P0-02-RS04-C02
      - shares_boundary_with:P0-00
    risk_boundaries:
      - 不得输出真实授权、真实同意、真实身份
      - 不得把角色视角写成官方声明或真实组织立场
    evidence_classes: [source_boundary_policy, readiness_boundary_policy, subcard_scope_reference]
    source_research_priority: high
    shared_with_capability_cards: [P0-00, P0-04]
    batch_refs: [batch_013, batch_001, batch_014]
    candidate_output_effect: 为后续 role-based 研究建立 speakable / not_speakable 分层，不生成任何真实授权材料。
    forbidden_knowledge_leakage: [authorization_claim, consent_fact, identity_fact, official_statement_fact]
    source_gap_likelihood: high
    output_influence:
      - 为所有 role cluster 提供授权降级护栏
      - 阻断把 research map 误当成对外可发言材料
    source_dependency: [02_p0_capability_and_subcards.yaml, 05_source_claim_evidence_policy.md, 06_candidatepack_and_readiness_policy.md]
    evidence_need: 所有授权、同意、身份、关系、代表性事实都需实例证据；本图不接收此类已落地事实。
    risk_flags: [authorization_claim, consent_claim, identity_fact_leakage, representative_stance_without_source]
    duplicate_check_key: authorization_surface_matrix_general_only
    body_structure_consistency_note: 必须同时写清“能说什么”与“不能说什么”，不可只停留在抽象警告。

  - cluster_id: P0-02-RS04-C02
    cluster_name: 人物故事红线与升级阻断触发器
    p0_group: P0-02
    research_card_id: P0-02-RS04
    knowledge_type: routing_hint
    knowledge_types: [boundary_rule, routing_hint, source_gap_candidate, decision_required_candidate]
    object_type: CapabilityResearchCluster
    domain_module: story_redline_and_escalation_trigger
    definition: 明确 role 相关内容何时必须 route away：真实员工故事、真实顾客故事、真实创始人语录、真实岗位经历、真实门店人员行为、真实合作或加盟人物事实，以及任何把研究输出包装成 production-ready 的行为。
    why_required_for_capability: P0-02 的主要风险不是缺内容，而是过度完成；该 cluster 将何时停手、何时降级变成显式规则。
    applies_when:
      - 需要判断某素材还能否留在本知识地图
      - 出现 story claim、authorization claim、ops claim、readiness claim 的迹象
    does_not_apply_when:
      - 无；本 cluster 为全图 route-away 护栏，但不替代正式 repository gate
    counter_boundary: 允许 role method，不允许人物故事；允许 routing rule，不允许 readiness 打开。
    expected_body_topics:
      - 人物与故事禁区
      - source gap 触发词
      - decision required 触发词
      - excluded 触发词
      - founder review 触发词
    required_relations:
      - depends_on:P0-02-RS04-C01
      - constrains:P0-02-RS01-C02
      - constrains:P0-02-RS02-C02
      - constrains:P0-02-RS03-C02
      - intersects_with:P0-00
    risk_boundaries:
      - 不得出现真人经历与真实故事
      - 不得打开任何 readiness
      - 不得输出 CandidatePack、KE、RAG、DIFY、approved passage、Serving projection
      - 不得把 research_subcard 当正式 capability card
    evidence_classes: [charter_constraint, schema_contract, source_boundary_policy, readiness_boundary_policy]
    source_research_priority: high
    shared_with_capability_cards: [P0-00, P0-01, P0-03, P0-04, P0-05]
    batch_refs: [batch_013, batch_001, batch_014]
    candidate_output_effect: 将高风险候选观察导向 gap / decision / excluded，避免误入后续生产链路。
    forbidden_knowledge_leakage: [real_person_fact, employee_story, customer_feedback_fact, candidatepack_ready_claim, production_ready_claim]
    source_gap_likelihood: high
    output_influence:
      - 为整个 P0-02 map 提供 stop / downgrade / review 规则
      - 防止 research map 被误当成 downstream-ready 材料
    source_dependency: [01_research_charter_and_redlines.md, 04_research_map_output_schema.yaml, 05_source_claim_evidence_policy.md, 06_candidatepack_and_readiness_policy.md]
    evidence_need: 该 cluster 不证明任何事实；它要求一旦出现高风险触发，就转入 gap / decision / excluded，并保持 readiness false。
    risk_flags: [readiness_escalation, p0_00_domain_leak, candidatepack_confusion, production_boundary_break]
    duplicate_check_key: story_redline_and_escalation_trigger_map
    body_structure_consistency_note: 触发器必须可执行、可审核、可路由，不能只写“谨慎处理”。

relation_hints:
  - relation_id: RH-P0-02-001
    relation_type: constrains
    from_cluster_id: P0-02-RS04-C01
    to_cluster_id: P0-02-RS01-C01
    note: 先划 speakable surface，再定义 role voice
  - relation_id: RH-P0-02-002
    relation_type: modulates
    from_cluster_id: P0-02-RS03-C01
    to_cluster_id: P0-02-RS01-C02
    note: 语气强度必须由受众距离控制，不能由想象中的 customer emotion 决定
  - relation_id: RH-P0-02-003
    relation_type: feeds
    from_cluster_id: P0-02-RS02-C01
    to_cluster_id: P0-02-RS02-C02
    note: 先有角色网格，才有视角切换和公开安全边界
  - relation_id: RH-P0-02-004
    relation_type: downgrades_to_gap
    from_cluster_id: P0-02-RS03-C02
    to_cluster_id: P0-02-RS04-C02
    note: 一旦 trust signal 进入 hard claim 或授权暗示，必须 route away
  - relation_id: RH-P0-02-005
    relation_type: shared_boundary
    from_cluster_id: P0-02-RS01-C02
    to_cluster_id: P0-02-RS04-C02
    note: 去人物化边界和人物故事红线处于同一风险面

source_gap_items:
  - item_id: SGI-P0-02-001
    object_type: SourceGapItem
    scope: 真实角色语料与真实组织口径
    gap_reason: 上传包仅授权 general_only；真实语录、真实组织声明、真实员工表达均为实例事实
    trigger_clusters: [P0-02-RS01-C01, P0-02-RS04-C02]
    required_next_step: 实例 source intake 或 review-only path
  - item_id: SGI-P0-02-002
    object_type: SourceGapItem
    scope: 真实授权 / consent / representative stance
    gap_reason: 上传包禁止 authorization_claim 与 consent_claim，且未提供实例证据
    trigger_clusters: [P0-02-RS04-C01, P0-02-RS04-C02]
    required_next_step: 独立授权证据与审阅边界
  - item_id: SGI-P0-02-003
    object_type: SourceGapItem
    scope: 真实组织生态与私域运营事实
    gap_reason: 上传包不接纳 real_org_fact、private_operation_fact、inventory / sales / channel fact
    trigger_clusters: [P0-02-RS02-C01, P0-02-RS02-C02]
    required_next_step: 实例经营资料路径，且不属于本图
  - item_id: SGI-P0-02-004
    object_type: SourceGapItem
    scope: 真实顾客反馈与信任证明
    gap_reason: 真实 feedback 会把受众轴与信任轴拖入实例事实和隐私边界
    trigger_clusters: [P0-02-RS03-C01, P0-02-RS03-C02]
    required_next_step: 单独 customer evidence 与 privacy review

decision_required_items:
  - item_id: DRI-P0-02-001
    object_type: DecisionRequiredItem
    topic: 角色词表共享与主责边界
    why_decision_required: P0-01 / P0-02 / P0-04 / P0-05 都会使用 role-like 语言，需后续决定共享还是拆分
    affected_clusters: [P0-02-RS01-C01, P0-02-RS02-C01, P0-02-RS03-C01]
  - item_id: DRI-P0-02-002
    object_type: DecisionRequiredItem
    topic: channel / franchise / partner 的通用边界
    why_decision_required: 上传包允许研究授权边界，但不授权真实合作事实；需决定这些角色是否长期停留在抽象层
    affected_clusters: [P0-02-RS02-C02, P0-02-RS04-C01]
  - item_id: DRI-P0-02-003
    object_type: DecisionRequiredItem
    topic: role trust signal 与 P0-03 claim gate 的挂接深度
    why_decision_required: 需决定后续 intake 中是引用 P0-03 证据门控，还是维护 P0-02 轻量 gate
    affected_clusters: [P0-02-RS03-C02]

excluded_items:
  - item_id: EX-P0-02-001
    object_type: ExcludedResearchItem
    title: 任何真实品牌、真实 SKU、真实门店、真实人物、真实顾客反馈
    reason: 非 general_only 知识，违反 charter 与 schema
  - item_id: EX-P0-02-002
    object_type: ExcludedResearchItem
    title: CandidatePack、KE、Serving projection、RAG context_bundle、DIFY workflow、approved_passage_text
    reason: 上传包明确禁止 production-side artifact
  - item_id: EX-P0-02-003
    object_type: ExcludedResearchItem
    title: 可直接发布的脚本、口播稿、店播话术、角色故事文本
    reason: 本任务仅产出 research map，不得输出 publishable material
  - item_id: EX-P0-02-004
    object_type: ExcludedResearchItem
    title: 把 research_subcard 写成 capability card 或把 count budget 写成 acceptance KPI
    reason: 违反 schema 与 charter validation rules

shared_cluster_merge_items:
  - item_id: SCM-P0-02-001
    object_type: SharedClusterMergeCandidate
    shared_with_capability: P0-01
    merge_candidate_scope: tone / persona surface / narrative anti-homogeneity
    candidate_clusters: [P0-02-RS01-C01, P0-02-RS01-C02, P0-02-RS03-C01]
    merge_rule_hint: 共享边界，不共享故事化产物；P0-02 保留角色方法，P0-01 保留企业叙事结构
  - item_id: SCM-P0-02-002
    object_type: SharedClusterMergeCandidate
    shared_with_capability: P0-04
    merge_candidate_scope: store-role perspective / public-safe ops boundary / training translation
    candidate_clusters: [P0-02-RS02-C01, P0-02-RS02-C02, P0-02-RS04-C01]
    merge_rule_hint: P0-02 负责角色视角与授权边界，P0-04 负责门店动作与 display-to-content translation
  - item_id: SCM-P0-02-003
    object_type: SharedClusterMergeCandidate
    shared_with_capability: P0-03
    merge_candidate_scope: trust signal / claim evidence gate
    candidate_clusters: [P0-02-RS03-C02]
    merge_rule_hint: P0-02 负责角色话语触发，P0-03 负责面料 / 版型 / 功效 / 质量等证据边界
  - item_id: SCM-P0-02-004
    object_type: SharedClusterMergeCandidate
    shared_with_capability: P0-05
    merge_candidate_scope: audience stage / scene fit / product role relation
    candidate_clusters: [P0-02-RS03-C01, P0-02-RS02-C02]
    merge_rule_hint: P0-02 保留 role-to-audience 方法，P0-05 承接产品角色与使用场景

founder_review_items:
  - item_id: FR-P0-02-001
    topic: 可能被误读为真实官方授权、真实代表发言或真实 consent 的表述
    trigger_clusters: [P0-02-RS04-C01, P0-02-RS04-C02]
    review_reason: 授权与同意类风险一旦误出，会产生高强度实例责任
  - item_id: FR-P0-02-002
    topic: 任何 role trust signal 中暗含质量、身体效果、舒适度、性能、耐久等证明的表述
    trigger_clusters: [P0-02-RS03-C02, P0-02-RS01-C02]
    review_reason: 该类表述会与 claim 合规和证据边界直接相连
  - item_id: FR-P0-02-003
    topic: 任何试图以人物或故事方式提升角色可信度的素材
    trigger_clusters: [P0-02-RS01-C02, P0-02-RS04-C02]
    review_reason: 与 real person / customer / story redline 高度耦合

required_execution_asset_types:
  - role_voice_register_matrix
  - tone_risk_calibration_grid
  - persona_surface_boundary_note
  - org_ecology_role_grid
  - perspective_handoff_map
  - public_safe_vs_private_ops_boundary_sheet
  - audience_distance_matrix
  - emotion_temperature_ladder
  - trust_signal_evidence_gate
  - authorization_surface_matrix
  - story_reference_redline_table
  - escalation_trigger_map
  - shared_cluster_merge_sheet
  - source_gap_ledger
  - decision_required_ledger

required_dq_checks:
  - anti_empty_language
  - anti_template_with_apparel_retail_anchor
  - irreplaceable_anchor_present
  - claim_vs_evidence_separated
  - filmability_or_visible_output_influence_present
  - platform_native_hint_stays_research_only
  - no_real_brand_sku_store_person_customer_fact
  - no_story_fabrication
  - no_authorization_or_consent_claim
  - no_full_display_system_overreach
  - no_p0_00_domain_leak
  - no_readiness_escalation

fallback_conditions:
  - 上传包只能支持方法层与边界层时，保留为 general_method / boundary_rule / relation_hint，不补写实例事实
  - 角色、生态、受众、授权细节无法在上传包内稳定定义时，降级为 source_gap_seed 或 unresolved_decisions
  - cluster 缺少 apparel / retail 锚点时，不得泛化成跨行业空模板，必须补对象、动作、约束或场景锚点

blocking_conditions:
  - 任何需要真实品牌、真实 SKU、真实门店、真实人物、真实顾客反馈、真实员工行为、真实组织结构的内容全部阻断
  - 任何 CandidatePack、KE、Serving projection、RAG context_bundle、DIFY workflow、approved_passage_text、production-ready 文本全部阻断
  - 任何启用 readiness、把 research_subcard 当 capability card、把 count budget 当 acceptance KPI 的写法全部阻断
  - 任何把 A2 support-only 扩写为完整陈列系统的写法全部阻断

unresolved_decisions:
  - decision_id: UD-P0-02-001
    topic: P0-02 与 P0-04 的门店角色边界
    why_unresolved: 上传包给出了相邻主题，但未给统一词表来切分“角色视角”与“门店日常内容化”的主所有权
    required_future_input: repository-side vocabulary decision
  - decision_id: UD-P0-02-002
    topic: P0-02 与 P0-01 的 persona / narrative 分工
    why_unresolved: 角色可辨识表达与企业叙事调性有交叉，需确定哪些语气壳层可共享
    required_future_input: shared-cluster merge 审核与词表归属决策
  - decision_id: UD-P0-02-003
    topic: franchise / channel / partner 角色是否建立独立通用词层
    why_unresolved: batch_013 允许研究授权边界，但不授权真实合同、真实合作或真实经营事实
    required_future_input: 是否建立 separate instance path 与 founder review boundary
  - decision_id: UD-P0-02-004
    topic: role authorization trigger vocabulary 的统一所有权
    why_unresolved: P0-02、P0-00、P0-04 都涉及 downgrade 触发词，但上传包未给 canonical vocabulary
    required_future_input: repository-side governance decision

source_gap_seed:
  - gap_id: SG-P0-02-001
    seed_question: 若后续需要真实角色语料、真实培训话术、真实门店表达，哪些 source type 与 review boundary 才可接纳
    trigger: real_person_quote or staff_fact demand
    route: source_gap
  - gap_id: SG-P0-02-002
    seed_question: 若后续要研究真实授权、真实同意、真实代言关系，应由哪条实例路径与哪类证据承接
    trigger: authorization_claim or consent_claim demand
    route: source_gap
  - gap_id: SG-P0-02-003
    seed_question: 若后续要落真实组织生态、真实加盟、真实渠道权限，最小可接受证据包是什么
    trigger: real_org_fact or franchise_fact demand
    route: source_gap
  - gap_id: SG-P0-02-004
    seed_question: 若后续要使用真实顾客反馈、评论或互动数据来支持角色信任信号，需要什么隐私和实例审阅机制
    trigger: customer_feedback_fact demand
    route: source_gap

forbidden_output_attestation:
  research_only_output: true
  not_candidatepack: true
  not_KE: true
  not_ABox: true
  not_TBox: true
  not_evidence_landed_item: true
  not_serving_projection: true
  not_approved_passage_text: true
  not_RAG_context_bundle: true
  not_DIFY_workflow: true
  not_publishable_script: true
  not_brand_fact: true
  not_SKU_fact: true
  not_store_fact: true
  not_person_fact: true
  not_customer_feedback_fact: true
  not_formal_capability_card: true
  no_real_brand_real_sku_real_store_real_person_real_feedback: true
  count_budget_is_not_acceptance_kpi: true

self_check:
  schema_required_top_level_fields_present: true
  all_clusters_include_schema_required_fields: true
  p0_scope_within_allowed_range: true
  no_forbidden_object_type_used: true
  all_readiness_false: true
  no_real_instance_fact: true
  no_full_part_a_claim: true
  no_count_used_as_acceptance_kpi: true
  no_batches_outside_batch_014: true
  covers_required_subcards: [P0-02-RS01, P0-02-RS02, P0-02-RS03, P0-02-RS04]
  readiness_assertion: all_false

readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false