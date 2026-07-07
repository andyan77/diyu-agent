--- FILE: shared_knowledge_cluster_registry.yaml
registry_id: W7_shared_knowledge_cluster_registry
registry_version: v0_1
status: integration_only
normalization_basis:
- stable canonical_cluster_id rewrite
- source_cluster_ids preserved
- dedupe only where semantic overlap is explicit in W1-W6
- owner assignment resolved or preserved with boundary notes
- all readiness-like states remain false
clusters:
- canonical_cluster_id: mkc_001
  source_cluster_ids:
  - P0-00-RS01-C01
  canonical_cluster_name: 入口槽位契约
  owner_capability_group: P0-00
  secondary_capability_groups:
  - P0-01
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-00
  research_subcard_refs:
  - P0-00-RS01
  batch_refs:
  - batch_014
  knowledge_types:
  - general_method
  - boundary_rule
  - routing_hint
  expected_body_topics:
  - 最小入口槽位族
  - 槽位完备度定义
  - 槽位缺失分层
  - 入口 checker 触发顺序
  required_relations:
  - slot_completeness -> route_ladder
  - instance_fact_presence -> blocking_or_gap
  - claim_risk_level -> evidence_checker
  - requested_asset_type -> asset_binding_gate
  risk_boundaries:
  - 不允许把真实品牌字段设计成通用槽位
  - 不允许把业务运行状态写成已知事实
  - 不允许把控制面槽位扩张为全域 ontology
  evidence_classes:
  - structure_only_slot_definition
  - source_anchor_presence_check
  - evidence_need_label_only
  - instance_fact_prohibited
  candidate_output_effect:
  - 使后续研究产物只能以控制面可消费槽位进入，不得越权直接形成领域正文或实例知识。
  source_gap_likelihood: medium
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_002
  source_cluster_ids:
  - P0-00-RS01-C02
  canonical_cluster_name: 路由阶梯与降级触发
  owner_capability_group: P0-00
  secondary_capability_groups:
  - P0-01
  - P0-03
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-00
  research_subcard_refs:
  - P0-00-RS01
  batch_refs:
  - batch_014
  knowledge_types:
  - boundary_rule
  - routing_hint
  - relation_hint
  expected_body_topics:
  - route 梯级定义
  - degradation 类型
  - soft fallback 与 hard block 区分
  - review-only 与 source-gap 分流
  required_relations:
  - checker_result -> route_decision
  - evidence_need_missing -> source_gap
  - ontology_conflict -> decision_required
  - risk_sensitive_override -> founder_review
  risk_boundaries:
  - 不允许从 research map 推导 runtime 配置
  - 不允许把降级描述成产线可执行发布策略
  - 不允许把“coverage budget”当作 acceptance KPI
  evidence_classes:
  - route_trigger_definition
  - evidence_missing_to_gap_rule
  - conflict_to_decision_rule
  - risk_sensitive_to_founder_review_rule
  candidate_output_effect:
  - 让任何候选研究片段都必须先通过控制面路由阶梯判断，不能直接被误读为可用知识。
  source_gap_likelihood: medium
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_003
  source_cluster_ids:
  - P0-00-RS02-C01
  canonical_cluster_name: 全局 claim 与证据边界检查
  owner_capability_group: P0-00
  secondary_capability_groups:
  - P0-03
  - P0-05
  source_p0_groups:
  - P0-00
  research_subcard_refs:
  - P0-00-RS02
  batch_refs:
  - batch_014
  knowledge_types:
  - evidence_requirement
  - boundary_rule
  - routing_hint
  expected_body_topics:
  - claim 强度分层
  - 方法陈述与事实断言切分
  - source support 与 evidence support 区分
  - GPT 草稿不可作 source anchor
  required_relations:
  - claim_strength -> evidence_need_class
  - evidence_absence -> source_gap
  - instance_fact -> excluded_or_decision_required
  - claim_risk_override -> founder_review
  risk_boundaries:
  - 不可把风险 claim 改写成看似中性的通用知识
  - 不可把 source type 当成 readiness 开关
  - 不可将弱证据提升为仓内真值
  evidence_classes:
  - source_supported_hard_claim_required
  - evidence_supported_effect_claim_required
  - method_only_no_fact
  - unsupported_claim_to_gap
  candidate_output_effect:
  - 防止控制面把 claim 类片段误消化为一般知识，确保高风险断言都被分流到正确账本。
  source_gap_likelihood: high
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_004
  source_cluster_ids:
  - P0-00-RS02-C02
  - P0-00-RS04-C02
  canonical_cluster_name: 异常分发与再进入规则
  owner_capability_group: P0-00
  secondary_capability_groups:
  - P0-01
  - P0-02
  - P0-03
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-00
  research_subcard_refs:
  - P0-00-RS02
  - P0-00-RS04
  batch_refs:
  - batch_014
  knowledge_types:
  - routing_hint
  - boundary_rule
  - decision_required_candidate
  - source_gap_candidate
  expected_body_topics:
  - source_gap 触发模式
  - decision_required 触发模式
  - founder_review 触发模式
  - excluded 触发模式
  required_relations:
  - missing_source -> source_gap
  - modeling_conflict -> decision_required
  - risk_sensitive_item -> founder_review
  - forbidden_output_request -> excluded
  risk_boundaries:
  - 不允许把 founder_review 当作通用兜底
  - 不允许把 excluded 伪装成 source_gap
  - 不允许在 map 中声明任何事项已通过 review
  - 不得写被阻断事项已恢复可用
  evidence_classes:
  - routing_reason_label
  - missing_source_marker
  - modeling_conflict_marker
  - founder_review_risk_marker
  candidate_output_effect:
  - 将异常研究项分发到后续可验证的不同账本，避免控制面地图把问题隐藏在模糊说明里。
  source_gap_likelihood: high
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_005
  source_cluster_ids:
  - P0-00-RS03-C01
  canonical_cluster_name: 能力组合与 strictest-wins 裁定
  owner_capability_group: P0-00
  secondary_capability_groups:
  - P0-01
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-00
  research_subcard_refs:
  - P0-00-RS03
  batch_refs:
  - batch_014
  knowledge_types:
  - relation_hint
  - boundary_rule
  - routing_hint
  expected_body_topics:
  - strictest-wins 原则
  - control-plane 保留条件
  - shared cluster 拆分条件
  - 新轴新增禁令
  required_relations:
  - multi_capability_request -> composition_check
  - composition_conflict -> decision_required
  - support_only_context -> no_full_ontology
  - strictest_rule -> final_route
  risk_boundaries:
  - 不允许把 content_x_display 建模成新 scenario family
  - 不允许把 A2 support-only 误写成完整陈列系统
  - 不允许把 shared cluster 变成全局真值
  evidence_classes:
  - composition_rule_definition
  - ownership_unclear_marker
  - support_only_boundary_label
  - strictest_wins_relation
  candidate_output_effect:
  - 为多能力交叉请求建立统一冲突裁决面，防止研究产物在能力归属上漂移。
  source_gap_likelihood: medium
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
  - boundary_note_attached
- canonical_cluster_id: mkc_006
  source_cluster_ids:
  - P0-00-RS03-C02
  - P0-00-RS04-C01
  canonical_cluster_name: 研究资产绑定与非生产封印
  owner_capability_group: P0-00
  secondary_capability_groups:
  - P0-01
  - P0-02
  - P0-03
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-00
  research_subcard_refs:
  - P0-00-RS03
  - P0-00-RS04
  batch_refs:
  - batch_014
  knowledge_types:
  - boundary_rule
  - relation_hint
  - routing_hint
  - exclusion_note
  expected_body_topics:
  - 研究型资产类型
  - 资产前置槽位
  - 资产绑定排他条件
  - 多资产冲突处理
  required_relations:
  - route_decision -> allowed_asset_stub
  - slot_completeness -> bindability
  - review_only_label -> non_production_asset_only
  - conflict_pair -> block_or_split
  risk_boundaries:
  - 不允许把 stub 资产描述成可上线对象
  - 不允许把 output schema 禁止对象重新包装后输出
  - 不允许把 source_gap 或 decision_required 直接绑定成下游可消费成品
  - 不允许把 review-only 翻译成“半可用”
  evidence_classes:
  - asset_bindability_rule
  - forbidden_object_type_guard
  - non_production_binding_label
  - conflict_split_marker
  candidate_output_effect:
  - 把研究输出限制在控制面允许组合的 research-only 资产占位体，避免越权产生成品化知识。
  source_gap_likelihood: medium
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_007
  source_cluster_ids:
  - W2-P0-01-RS01-CL01
  canonical_cluster_name: 企业叙事骨架
  owner_capability_group: P0-01
  secondary_capability_groups:
  - P0-02
  - P0-03
  - P0-05
  source_p0_groups:
  - P0-01
  research_subcard_refs:
  - P0-01-RS01
  batch_refs:
  - batch_009
  - batch_007
  - batch_013
  knowledge_types:
  - general_method
  - relation_hint
  - boundary_rule
  expected_body_topics:
  - 企业所回应的问题场景
  - 组织性方法与长期选择
  - 供应链 / 组织 / 过程证明的预留槽位
  - 价值表达与可观察差异
  required_relations:
  - problem_domain -> operating_method
  - operating_method -> proof_slot
  - proof_slot -> value_expression
  - value_expression -> series_axis
  risk_boundaries:
  - 禁止滑入真实品牌起源史、扩张史、节点史
  - 禁止用无来源愿景、使命、行业地位充当证明
  - 禁止把研究子卡误写为正式 capability card
  evidence_classes:
  - official_corporate_profile_type
  - official_operating_method_overview_type
  - official_process_explainer_type
  - organization_role_description_type
  candidate_output_effect:
  - 仅提升 research map 中企业叙事的结构复用性、系列拆分能力与证据槽位规划能力。
  source_gap_likelihood: medium
  decision_required_likelihood: low
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_008
  source_cluster_ids:
  - W2-P0-01-RS01-CL02
  - W2-P0-01-RS02-CL02
  canonical_cluster_name: 证明槽位与价值转译
  owner_capability_group: P0-01
  secondary_capability_groups:
  - P0-03
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-01
  research_subcard_refs:
  - P0-01-RS01
  - P0-01-RS02
  batch_refs:
  - batch_009
  - batch_007
  - batch_013
  - batch_005
  - batch_002
  knowledge_types:
  - evidence_requirement
  - relation_hint
  - boundary_rule
  - general_method
  expected_body_topics:
  - 角色分工与协作边界
  - 关键工序或流程节点的叙事位置
  - 质量门、复核门、交接门
  - 供应链选择与约束处理的通用叙事位
  required_relations:
  - organization_role -> process_node
  - process_node -> quality_gate
  - supply_chain_choice -> constraint
  - constraint -> method_credibility
  risk_boundaries:
  - 禁止写具体工厂、供应商、产地、认证、奖项等实例信息
  - 禁止把机密流程、未披露 SOP、内部授权写成通用知识
  - 禁止把 proof slot 扩大成完整 display system 或 training system
  - 禁止把抽象价值直接升级为真实产品效果或经营事实
  evidence_classes:
  - official_process_overview_type
  - official_quality_method_note_type
  - official_supply_chain_principle_disclosure_type
  - organization_or_role_document_type
  candidate_output_effect:
  - 仅形成 proof-slot taxonomy、evidence need labels 与 cross-card relation hints。
  source_gap_likelihood: high
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_009
  source_cluster_ids:
  - W2-P0-01-RS02-CL01
  canonical_cluster_name: 故事弧线适用边界
  owner_capability_group: P0-01
  secondary_capability_groups:
  - P0-05
  source_p0_groups:
  - P0-01
  research_subcard_refs:
  - P0-01-RS02
  batch_refs:
  - batch_009
  - batch_005
  - batch_002
  knowledge_types:
  - boundary_rule
  - general_method
  - source_gap_candidate
  expected_body_topics:
  - 不同叙事弧线对应的问题类型
  - 弧线与证据要求的绑定
  - 弧线与价值表达、proof slot 的兼容性
  - 不适用弧线的识别信号
  required_relations:
  - story_arc -> required_proof_intensity
  - story_arc -> compatible_value_expression
  - story_arc -> forbidden_fact_zone
  - arc_mismatch -> source_gap_or_downgrade
  risk_boundaries:
  - 禁止以真实人物命运、真实品牌里程碑作为默认弧线素材
  - 禁止无证构造起点困境、逆袭、传承、行业见证等桥段
  - 禁止将弧线方法误判为可生成 production copy
  evidence_classes:
  - story_method_reference_type
  - organization_process_or_capability_explainer_type
  - official_milestone_disclosure_type_if_later_instance_authorized
  candidate_output_effect:
  - 仅提供 arc taxonomy、适用条件与 downgrade routing，不输出 story scripts。
  source_gap_likelihood: medium_high
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_010
  source_cluster_ids:
  - W2-P0-01-RS03-CL01
  canonical_cluster_name: 反模板叙事锚点
  owner_capability_group: P0-01
  secondary_capability_groups:
  - P0-02
  - P0-03
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-01
  research_subcard_refs:
  - P0-01-RS03
  batch_refs:
  - batch_010
  - batch_011
  - batch_014
  knowledge_types:
  - general_method
  - boundary_rule
  - relation_hint
  expected_body_topics:
  - 对象锚点类型
  - 动作锚点与处理逻辑
  - 约束锚点与取舍表达
  - 节点锚点与前后台衔接
  required_relations:
  - anchor_object -> anchor_action
  - anchor_action -> visible_cue
  - constraint -> tradeoff_expression
  - process_node -> narrative_sceneability
  risk_boundaries:
  - 禁止用 generic slogan 充当锚点
  - 禁止用真实人物、真实顾客、真实门店作为默认锚点来源
  - 禁止把锚点系统误写成 production-ready 选题库
  evidence_classes:
  - process_scene_or_object_reference_type
  - organization_role_action_reference_type
  - method_or_choice_explainer_type
  candidate_output_effect:
  - 用于 DQ gate 的 narrative anchor checklist、anti-template split 规则与 sceneability hints。
  source_gap_likelihood: medium
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_011
  source_cluster_ids:
  - W2-P0-01-RS03-CL02
  canonical_cluster_name: 叙事放大禁区与风险路由
  owner_capability_group: P0-01
  secondary_capability_groups:
  - P0-00
  - P0-03
  - P0-05
  source_p0_groups:
  - P0-01
  research_subcard_refs:
  - P0-01-RS03
  batch_refs:
  - batch_010
  - batch_011
  - batch_014
  knowledge_types:
  - routing_hint
  - boundary_rule
  - decision_required_candidate
  expected_body_topics:
  - 高风险 narrative zone 分类
  - 不同风险 zone 对应的路由动作
  - 风险放大词与禁用表达类别
  - 需要 founder review 的典型边界
  required_relations:
  - risk_zone -> routing_target
  - authority_signal -> evidence_requirement
  - instance_fact_dependency -> source_gap
  - sensitive_promise -> founder_review
  risk_boundaries:
  - 禁止洞穿为真实品牌荣誉、排名、认证、授权、顾客反馈事实
  - 禁止把 founder review 理解为可直接通过生产的绿色通道
  - 禁止借本 cluster 生成 publishable risk-managed copy
  evidence_classes:
  - risk_policy_reference_type
  - source_gap_route_reference_type
  - founder_review_trigger_reference_type
  candidate_output_effect:
  - 只产生 risk routing ledger、forbidden amplification cues 与 downgrade conditions。
  source_gap_likelihood: high
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_012
  source_cluster_ids:
  - W2-P0-01-RS04-CL01
  - W2-P0-01-RS04-CL02
  canonical_cluster_name: 系列轴与跨形态资产单元
  owner_capability_group: P0-01
  secondary_capability_groups:
  - P0-02
  - P0-03
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-01
  research_subcard_refs:
  - P0-01-RS04
  batch_refs:
  - batch_007
  - batch_009
  - batch_012
  knowledge_types:
  - general_method
  - relation_hint
  - boundary_rule
  - evidence_requirement
  expected_body_topics:
  - 系列轴的类型与选用条件
  - 序列编排逻辑与去重复机制
  - proof cadence 与 topic cascade 的绑定
  - 前台价值与后台能力穿插规则
  required_relations:
  - master_narrative -> series_axis
  - series_axis -> episode_unit
  - episode_unit -> proof_slot_distribution
  - sequence_order -> repetition_control
  risk_boundaries:
  - 禁止写成内容排期、增长策略或发布任务单
  - 禁止在没有 proof slot 的情况下先规划多期价值宣讲
  - 禁止把 series axis 误写为新增 capability group
  - 不得把 asset unit 写成可直接发布文案
  evidence_classes:
  - topic_axis_reference_type
  - series_structure_reference_type
  - proof_slot_distribution_reference_type
  - asset_unit_reference_type
  candidate_output_effect:
  - 用于 later intake 的 topic-axis grid、episode-unit rules 与 anti-repetition notes。
  source_gap_likelihood: medium
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
- canonical_cluster_id: mkc_013
  source_cluster_ids:
  - P0-02-RS01-C01
  canonical_cluster_name: 角色发声寄存器
  owner_capability_group: P0-02
  secondary_capability_groups:
  - P0-01
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-02
  research_subcard_refs:
  - P0-02-RS01
  batch_refs:
  - batch_008
  - batch_010
  - batch_007
  knowledge_types:
  - general_method
  - relation_hint
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
  evidence_classes:
  - charter_constraint
  - subcard_scope_reference
  - dq_policy_anchor
  candidate_output_effect:
  - 为后续候选观察提供 role voice 分桶与降噪规则，不构成 CandidatePack。
  source_gap_likelihood: medium
  decision_required_likelihood: low
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_014
  source_cluster_ids:
  - P0-02-RS01-C02
  canonical_cluster_name: 语气校准与去人物化
  owner_capability_group: P0-02
  secondary_capability_groups:
  - P0-01
  - P0-03
  - P0-04
  source_p0_groups:
  - P0-02
  research_subcard_refs:
  - P0-02-RS01
  batch_refs:
  - batch_008
  - batch_010
  - batch_007
  knowledge_types:
  - general_method
  - boundary_rule
  - evidence_requirement
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
  evidence_classes:
  - charter_constraint
  - source_boundary_policy
  - dq_policy_anchor
  candidate_output_effect:
  - 为后续候选观察建立 tone 梯度与 persona downgrade，不形成任何人物素材或发布文案。
  source_gap_likelihood: medium
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_015
  source_cluster_ids:
  - P0-02-RS02-C01
  canonical_cluster_name: 组织生态角色网格
  owner_capability_group: P0-02
  secondary_capability_groups:
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-02
  research_subcard_refs:
  - P0-02-RS02
  batch_refs:
  - batch_010
  - batch_013
  - batch_006
  knowledge_types:
  - general_method
  - relation_hint
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
  evidence_classes:
  - subcard_scope_reference
  - batch_budget_reference
  - dq_policy_anchor
  candidate_output_effect:
  - 为后续生态内容提供 role grid，不产出真实组织资料。
  source_gap_likelihood: medium
  decision_required_likelihood: low
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_016
  source_cluster_ids:
  - P0-02-RS02-C02
  canonical_cluster_name: 视角切换与公开安全边界
  owner_capability_group: P0-02
  secondary_capability_groups:
  - P0-00
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-02
  research_subcard_refs:
  - P0-02-RS02
  batch_refs:
  - batch_010
  - batch_013
  - batch_006
  knowledge_types:
  - relation_hint
  - boundary_rule
  - routing_hint
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
  evidence_classes:
  - source_boundary_policy
  - batch_budget_reference
  - readiness_boundary_policy
  candidate_output_effect:
  - 为后续跨角色编排保留 relation hint 与 downgrade 规则，不形成运行时流程。
  source_gap_likelihood: high
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_017
  source_cluster_ids:
  - P0-02-RS03-C01
  canonical_cluster_name: 受众距离与信息深浅轴
  owner_capability_group: P0-02
  secondary_capability_groups:
  - P0-01
  - P0-05
  source_p0_groups:
  - P0-02
  research_subcard_refs:
  - P0-02-RS03
  batch_refs:
  - batch_008
  - batch_009
  - batch_011
  knowledge_types:
  - general_method
  - relation_hint
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
  evidence_classes:
  - subcard_scope_reference
  - dq_policy_anchor
  candidate_output_effect:
  - 为后续 role-to-audience 研究提供安全维度，不生成真实用户画像。
  source_gap_likelihood: medium
  decision_required_likelihood: low
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_018
  source_cluster_ids:
  - P0-02-RS03-C02
  canonical_cluster_name: 情绪温度层与信任门控
  owner_capability_group: P0-02
  secondary_capability_groups:
  - P0-00
  - P0-03
  - P0-05
  source_p0_groups:
  - P0-02
  research_subcard_refs:
  - P0-02-RS03
  batch_refs:
  - batch_008
  - batch_009
  - batch_011
  knowledge_types:
  - general_method
  - evidence_requirement
  - boundary_rule
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
  evidence_classes:
  - source_boundary_policy
  - dq_policy_anchor
  - charter_constraint
  candidate_output_effect:
  - 为后续候选观察补上 evidence gate 与 downgrade 触发条件，不生成 claim 成稿。
  source_gap_likelihood: high
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_019
  source_cluster_ids:
  - P0-02-RS04-C01
  - P0-02-RS04-C02
  canonical_cluster_name: 角色授权表面与人物故事红线
  owner_capability_group: P0-02
  secondary_capability_groups:
  - P0-00
  - P0-04
  source_p0_groups:
  - P0-02
  research_subcard_refs:
  - P0-02-RS04
  batch_refs:
  - batch_013
  - batch_001
  - batch_014
  knowledge_types:
  - boundary_rule
  - general_method
  - routing_hint
  - source_gap_candidate
  - decision_required_candidate
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
  - 不得把真实人员故事包装成方法层
  evidence_classes:
  - source_boundary_policy
  - readiness_boundary_policy
  - subcard_scope_reference
  candidate_output_effect:
  - 为后续 role-based 研究建立 speakable / not_speakable 分层，不生成任何真实授权材料。
  source_gap_likelihood: high
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_020
  source_cluster_ids:
  - P0-03-RS01-CL01
  - P0-03-RS01-CL02
  canonical_cluster_name: 品类解释与属性槽位骨架
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS01
  batch_refs:
  - batch_002
  - batch_003
  - batch_014
  knowledge_types:
  - general_method
  - boundary_rule
  - relation_hint
  expected_body_topics:
  - 上装/下装/连衣类/外搭类等抽象品类分层
  - 单品解释时可使用的通用属性槽位
  - 品类说明与真实 SKU 事实的切断规则
  - 面料/材质槽位
  required_relations:
  - 连接 RS01-CL02 属性槽位体系
  - 为 RS02 面料/工艺与 RS03 claim 边界提供对象入口
  - 承接 RS01-CL01 的品类入口
  - 向 RS02/RS03/RS04 分发属性研究任务
  risk_boundaries:
  - 不得落入真实 SKU、价格、库存、上新节奏、门店配货事实
  - 不得把品类定义写成某品牌专属产品线
  - 不得把属性槽位误写成正式 ontology 或正式 capability card
  - 不得将品质证明自动等同于真实认证已存在
  evidence_classes:
  - terminology_definition_source
  - apparel_category_reference
  - attribute_taxonomy_reference
  - attribute_schema_reference
  candidate_output_effect:
  - 约束后续候选内容以类别—属性—边界结构组织，减少泛化空话与实例混入。
  source_gap_likelihood: 中
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
- canonical_cluster_id: mkc_021
  source_cluster_ids:
  - P0-03-RS01-CL03
  canonical_cluster_name: 同类比较维度与禁比边界
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-05
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS01
  batch_refs:
  - batch_002
  - batch_003
  - batch_004
  knowledge_types:
  - boundary_rule
  - general_method
  - evidence_requirement
  expected_body_topics:
  - 同类之间可比的维度
  - 不可直接比较的维度
  - 比较时如何显示未知项
  - 何时必须触发 source gap
  required_relations:
  - 依赖 RS01-CL02 属性槽位
  - 与 RS03-CL02 claim 证据阶梯联动
  risk_boundaries:
  - 不得把比较写成优劣承诺
  - 不得出现实验结果、耐用性、舒适性、显瘦或保暖结论
  evidence_classes:
  - comparison_dimension_reference
  - evidence_policy_reference
  - risk_boundary_reference
  candidate_output_effect:
  - 让候选内容形成比较维度—能看见什么—不能推出什么的结构。
  source_gap_likelihood: 中
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_022
  source_cluster_ids:
  - P0-03-RS02-CL01
  canonical_cluster_name: 面料家族与属性边界
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS02
  batch_refs:
  - batch_003
  - batch_005
  knowledge_types:
  - general_method
  - boundary_rule
  - evidence_requirement
  expected_body_topics:
  - 纤维/纱线/面料层级区分
  - 梭织/针织等结构差异的解释入口
  - 常见观察项与不可直接外推的性能项
  - 手感词与事实词的边界
  required_relations:
  - 承接 RS01-CL02 面料槽位
  - 向 RS03-CL02 传递性能 claim 风险
  - 向 RS04-CL02 提供质量观察项
  risk_boundaries:
  - 不得把透气、抗皱、保暖、耐磨、舒适等写为默认特性
  - 不得把某材料家族说成在所有情境下都优于另一材料家族
  evidence_classes:
  - textile_terminology_source
  - fabric_structure_reference
  - evidence_policy_reference
  candidate_output_effect:
  - 帮助后续候选内容把材料家族→结构特点→可观察线索→不可直接承诺的效果→需补源项串起来。
  source_gap_likelihood: 高
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_023
  source_cluster_ids:
  - P0-03-RS02-CL02
  canonical_cluster_name: 颜色表达与视觉解释边界
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS02
  batch_refs:
  - batch_003
  - batch_011
  knowledge_types:
  - general_method
  - boundary_rule
  - relation_hint
  expected_body_topics:
  - 颜色基础维度
  - 色彩家族与中性/冷暖等通用表达
  - 颜色在镜头与光线下的观察提醒
  - 颜色故事与品质/显白/显瘦等结论切断
  required_relations:
  - 连接 RS01-CL02 颜色槽位
  - 连接 RS04-CL04 可拍摄表达
  - 与 RS03-CL01 体型效果边界联动
  risk_boundaries:
  - 不得把某颜色写成对所有人都显白、显瘦、显气色
  - 不得把色差、染色牢度、耐洗结果写成既成事实
  evidence_classes:
  - color_theory_reference
  - visual_observation_reference
  - evidence_policy_reference
  candidate_output_effect:
  - 让后续候选内容在色彩解释里有锚点、有镜头线索、无越界结果承诺。
  source_gap_likelihood: 中
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_024
  source_cluster_ids:
  - P0-03-RS02-CL03
  canonical_cluster_name: 版型廓形剪裁术语
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS02
  batch_refs:
  - batch_003
  - batch_005
  - batch_011
  knowledge_types:
  - general_method
  - relation_hint
  - boundary_rule
  expected_body_topics:
  - 版型与廓形区别
  - 轮廓线、长度、宽窄、松量、重心等表达
  - 结构节点与视觉结果的关系提示
  - 版型词与身材效果承诺的切断
  required_relations:
  - 连接 RS01-CL02 版型槽位
  - 连接 RS03-CL01 体型效果语言阶梯
  - 连接 RS04-CL04 画面示意方式
  risk_boundaries:
  - 不得把版型术语直接等同于显瘦、显高、遮肉、修饰某部位结果
  - 不得把适合所有身材写成通用结论
  evidence_classes:
  - pattern_cut_reference
  - fashion_terminology_source
  - evidence_policy_reference
  candidate_output_effect:
  - 让后续候选内容形成术语定义—结构节点—视觉变化—风险边界的段落。
  source_gap_likelihood: 高
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_025
  source_cluster_ids:
  - P0-03-RS02-CL04
  - P0-03-RS04-CL01
  canonical_cluster_name: 工艺观察线索与讲解节点
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-04
  - P0-05
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS02
  - P0-03-RS04
  batch_refs:
  - batch_003
  - batch_005
  - batch_011
  - batch_009
  - batch_012
  knowledge_types:
  - general_method
  - relation_hint
  - evidence_requirement
  - boundary_rule
  expected_body_topics:
  - 可见工艺节点清单
  - 观察顺序：外观→结构→细节→不可直接外推的质量结论
  - 工艺名词与功能/耐用结论的风险切断
  - 工艺节点的叙事先后顺序
  required_relations:
  - 连接 RS04-CL01 工艺叙事节点
  - 连接 RS04-CL02 质量观察项
  - 连接 RS03-CL02 质量/耐用 claim 证据阶梯
  - process_node -> explanation_order
  risk_boundaries:
  - 不得把某工艺存在等同于更耐穿、更高端、更专业
  - 不得把无来源的生产工艺故事当作事实
  - 不得写真实工厂流程、真实质检结果、真实认证状态
  evidence_classes:
  - garment_construction_reference
  - visual_inspection_reference
  - evidence_policy_reference
  - process_story_method_reference
  candidate_output_effect:
  - 提升后续候选内容的细节锚点与镜头对象选择，但不越过质量承诺边界。
  source_gap_likelihood: 高
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_026
  source_cluster_ids:
  - P0-03-RS03-CL01
  - P0-03-RS03-CL03
  canonical_cluster_name: 身材效果语言阶梯与场景化观察
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-05
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS03
  batch_refs:
  - batch_004
  - batch_001
  - batch_014
  knowledge_types:
  - boundary_rule
  - general_method
  - routing_hint
  expected_body_topics:
  - 观察词/关系词/结果词分层
  - 能说视觉线条变化与不能保证身体结果的边界
  - 替代表达与回避表达
  - 场景化但非结论化的观察方式
  required_relations:
  - 承接 RS02-CL02 与 RS02-CL03
  - 连接 RS03-CL03 场景化观察方法
  - 向 P0-00 证据路由提供触发点但不吸收控制面内容
  - scene cue -> non-conclusive observation
  risk_boundaries:
  - 不得出现保证式效果词、医学词、身体焦虑导向词
  - 不得把个体主观感受包装成普适结果
  - 不得把场景化表达写成实际 body result
  evidence_classes:
  - claim_policy_reference
  - sensitive_claim_boundary_reference
  - content_risk_reference
  - scene_observation_reference
  candidate_output_effect:
  - 约束后续候选内容优先使用观察语言，降低敏感断言风险。
  source_gap_likelihood: 高
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_027
  source_cluster_ids:
  - P0-03-RS03-CL02
  canonical_cluster_name: 舒适性能耐用品质证据阶梯
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-00
  - P0-05
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS03
  batch_refs:
  - batch_004
  - batch_001
  - batch_014
  knowledge_types:
  - evidence_requirement
  - boundary_rule
  - routing_hint
  expected_body_topics:
  - claim 分级
  - 不同 claim 对应的证据类别
  - 无证据时允许保留的最低表达层级
  - source gap 触发阈值
  required_relations:
  - 承接 RS02-CL01 与 RS02-CL04 的材料和工艺名词
  - 连接 RS04-CL02 与 RS04-CL03 的品质证明类型
  - 连接 P0-00 但不重写为控制面卡
  risk_boundaries:
  - 不得把舒适、性能、耐用、品质结论写成默认事实
  evidence_classes:
  - standard_reference_type
  - test_method_reference_type
  - expert_method_reference_type
  - evidence_policy_reference
  candidate_output_effect:
  - 直接决定后续候选内容哪些句子只能写成观察、哪些必须标注待补源、哪些必须禁出。
  source_gap_likelihood: high
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_028
  source_cluster_ids:
  - P0-03-RS04-CL02
  - P0-03-RS04-CL03
  canonical_cluster_name: 品质观察项与证明类型路由
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-01
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS04
  batch_refs:
  - batch_003
  - batch_009
  - batch_012
  knowledge_types:
  - general_method
  - evidence_requirement
  - boundary_rule
  - routing_hint
  expected_body_topics:
  - 可观察品质线索
  - proof-type taxonomy
  - certification / standard claim 的 route-away 规则
  - 不得把局部观察写成整体保证
  required_relations:
  - quality_observation -> proof_type
  - proof_type -> claim_routing
  - certification_signal -> higher_evidence_need
  - unsupported_proof -> source_gap
  risk_boundaries:
  - 不得把局部细节观察直接写成整体品质保证
  - 不得引用真实证书、真实检测结果、真实执行标准状态
  - 不得将研究提示扩写为 production-ready 文案、脚本或培训成稿
  evidence_classes:
  - quality_observation_reference
  - proof_type_reference
  - certification_claim_policy_reference
  - evidence_policy_reference
  candidate_output_effect:
  - 使后续候选内容把 quality cue、proof-type 与 route-away 条件明确拆开。
  source_gap_likelihood: 高
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_029
  source_cluster_ids:
  - P0-03-RS04-CL04
  canonical_cluster_name: 工艺品质内容的可拍摄表达
  owner_capability_group: P0-03
  secondary_capability_groups:
  - P0-01
  - P0-04
  source_p0_groups:
  - P0-03
  research_subcard_refs:
  - P0-03-RS04
  batch_refs:
  - batch_003
  - batch_009
  - batch_012
  knowledge_types:
  - general_method
  - relation_hint
  - boundary_rule
  expected_body_topics:
  - 可拍摄对象
  - 可拍摄动作
  - 画面层级
  - 说明与非结论化提示
  required_relations:
  - object cue -> camera cue
  - camera cue -> explanation slot
  - explanation slot -> claim boundary
  - process detail -> filmability
  risk_boundaries:
  - 不得生成脚本
  - 不得把镜头对象等同于质量证明
  evidence_classes:
  - filmability_reference
  - process_visualization_reference
  - risk_boundary_reference
  candidate_output_effect:
  - 使后续研究保留可拍摄表达方式，而不落成生产级内容。
  source_gap_likelihood: medium
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_030
  source_cluster_ids:
  - W5_P0_04_RS01_CL01
  canonical_cluster_name: Look 拆解观察骨架
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-03
  - P0-05
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS01
  batch_refs:
  - batch_011
  - batch_012
  - batch_003
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
  candidate_output_effect:
  - 影响后续候选研究条目如何描述Look拆解、画面重点与动作入口，减少空泛形容词。
  source_gap_likelihood: medium
  decision_required_likelihood: low
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_031
  source_cluster_ids:
  - W5_P0_04_RS01_CL02
  canonical_cluster_name: 主题与色彩故事关系网
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-01
  - P0-03
  - P0-05
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS01
  batch_refs:
  - batch_011
  - batch_003
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
  candidate_output_effect:
  - 影响候选研究条目如何把配色关系写成可解释的观察结构，而不是产出可直接发布文案。
  source_gap_likelihood: medium
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
  - boundary_note_attached
- canonical_cluster_id: mkc_032
  source_cluster_ids:
  - W5_P0_04_RS01_CL03
  canonical_cluster_name: 陈列区位与可拍摄视觉锚点
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-02
  - P0-05
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS01
  batch_refs:
  - batch_011
  - batch_012
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
  candidate_output_effect:
  - 影响候选研究条目如何设置观察入口、镜头顺序与画面重心，提升filmability而不输出脚本。
  source_gap_likelihood: high
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_033
  source_cluster_ids:
  - W5_P0_04_RS02_CL01
  canonical_cluster_name: 门店日常动作观察切片
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-02
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS02
  batch_refs:
  - batch_010
  - batch_012
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
  candidate_output_effect:
  - 影响候选研究条目如何识别“可内容化动作”，避免只剩空泛“门店日常氛围”。
  source_gap_likelihood: medium
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_034
  source_cluster_ids:
  - W5_P0_04_RS02_CL02
  - W5_P0_04_RS03_CL02
  canonical_cluster_name: 动作转内容槽位与演示三段式
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-01
  - P0-02
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS02
  - P0-04-RS03
  batch_refs:
  - batch_010
  - batch_012
  - batch_013
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
  - 依赖SOP节点化框架
  risk_boundaries:
  - 不得输出发布级脚本
  - 不得固化平台模板为仓内canonical truth
  - 不得引入真实门店口播
  - 不得写真实培训口径
  evidence_classes:
  - 内容结构方法资料
  - 短视频与图文内容切片资料
  - 培训演示转内容的方法资料
  - 通用培训演示设计资料
  candidate_output_effect:
  - 影响候选研究条目如何描述“动作-解释-镜头”的映射关系，为后续CandidatePack准备研究结构而非生产内容。
  source_gap_likelihood: high
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_035
  source_cluster_ids:
  - W5_P0_04_RS02_CL03
  canonical_cluster_name: 门店日常内容化风险红线
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-00
  - P0-02
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS02
  batch_refs:
  - batch_010
  - batch_013
  - batch_014
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
  candidate_output_effect:
  - 影响候选研究条目如何在内容化前进行剔除、重写或升级决策，避免实例事实渗漏。
  source_gap_likelihood: low
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_036
  source_cluster_ids:
  - W5_P0_04_RS03_CL01
  canonical_cluster_name: 陈列动作 SOP 节点框架
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-02
  - P0-05
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS03
  batch_refs:
  - batch_012
  - batch_006
  - batch_011
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
  candidate_output_effect:
  - 影响候选研究条目如何从“陈列动作”升级为“节点化流程知识”，提升可复核性。
  source_gap_likelihood: medium
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_037
  source_cluster_ids:
  - W5_P0_04_RS04_CL01
  - W5_P0_04_RS04_CL02
  canonical_cluster_name: 零售角色动作权限与加盟改写边界
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-02
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS04
  batch_refs:
  - batch_013
  - batch_014
  - batch_007
  knowledge_types:
  - general_method
  - boundary_rule
  - relation_hint
  - routing_hint
  - decision_required_candidate
  - exclusion_note
  expected_body_topics:
  - 零售角色、动作、权限关系
  - speakable 的一般化授权表面
  - 加盟/授权信息的泛化改写条件
  - 真实制度与方法层的切断
  required_relations:
  - role -> action -> permission
  - instance authorization -> route_away
  - franchise info -> generic rewrite gate
  - retail permission -> review boundary
  risk_boundaries:
  - 不得出现加盟事实、门店合同事实、真实员工事实
  - 不得出现全链路显示系统主张或越权授权结论
  - 不得把真实授权、真实同意、真实身份写成方法层
  evidence_classes:
  - 零售角色关系通用资料
  - 权限边界方法资料
  - 授权改写风险资料
  - 章程/证据政策资料
  candidate_output_effect:
  - 使后续研究可保留零售角色与改写边界，但不沉淀任何实例授权信息。
  source_gap_likelihood: high
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_038
  source_cluster_ids:
  - W5_P0_04_RS03_CL03
  - W5_P0_04_RS04_CL03
  canonical_cluster_name: 异常回退与前复核路由提示
  owner_capability_group: P0-04
  secondary_capability_groups:
  - P0-00
  source_p0_groups:
  - P0-04
  research_subcard_refs:
  - P0-04-RS03
  - P0-04-RS04
  batch_refs:
  - batch_012
  - batch_014
  - batch_013
  - batch_007
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
  - precheck -> review routing
  risk_boundaries:
  - 不得写route mutation
  - 不得给出真实组织复核结论
  - 不得把例外处理写成系统实现方案
  evidence_classes:
  - 上传包章程与证据政策
  - 流程异常管理的一般方法资料
  - 复核节点方法资料
  candidate_output_effect:
  - 影响候选研究条目在遇到证据缺口、边界冲突、控制面泄漏时的停机与转向方式。
  source_gap_likelihood: low
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - merged_2_source_clusters
  - boundary_note_attached
- canonical_cluster_id: mkc_039
  source_cluster_ids:
  - P0-05-RS01-C01
  canonical_cluster_name: 产品叙事角色入场框架
  owner_capability_group: P0-05
  secondary_capability_groups:
  - P0-01
  - P0-04
  source_p0_groups:
  - P0-05
  research_subcard_refs:
  - P0-05-RS01
  batch_refs:
  - batch_002
  - batch_005
  - batch_009
  knowledge_types:
  - general_method
  - relation_hint
  - evidence_requirement
  expected_body_topics:
  - 角色功能命名方式
  - 产品在镜头中的首出现位置
  - 产品与场景任务的绑定方式
  - 产品作为对比项、解决项、过渡项的结构位置
  required_relations:
  - 产品角色 -> 场景任务
  - 产品角色 -> 叙事段落
  - 产品角色 -> 视觉锚点
  - 产品角色 -> 教育节点
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
  candidate_output_effect:
  - 为后续候选研究提供“产品以什么角色进入故事”的拆解槽位，帮助形成可检查的 narrative skeleton，而不是产出成稿。
  source_gap_likelihood: medium
  decision_required_likelihood: low
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_040
  source_cluster_ids:
  - P0-05-RS01-C02
  canonical_cluster_name: 叙事到 CTA 的非硬卖边界
  owner_capability_group: P0-05
  secondary_capability_groups:
  - P0-00
  - P0-01
  - P0-04
  source_p0_groups:
  - P0-05
  research_subcard_refs:
  - P0-05-RS01
  batch_refs:
  - batch_002
  - batch_005
  - batch_009
  knowledge_types:
  - boundary_rule
  - routing_hint
  - evidence_requirement
  expected_body_topics:
  - CTA 的前置教育条件
  - CTA 的信息密度控制
  - CTA 与商品事实的隔离
  - CTA 与陈列/场景的连接点
  required_relations:
  - 叙事完成度 -> CTA 可出现条件
  - 教育节点 -> CTA 信息层级
  - 产品角色 -> CTA 触发方式
  - display cue -> CTA 位置
  risk_boundaries:
  - 不得写直接下单口播
  - 不得写成交承诺
  - 不得写真实渠道玩法
  - 不得写真实营销节点
  evidence_classes:
  - CTA 方法来源
  - 内容路径设计来源
  - 边界政策来源
  candidate_output_effect:
  - 帮助后续候选研究把 CTA 作为方法节点而非销售句输出，形成非 production-ready 的收束控制。
  source_gap_likelihood: high
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_041
  source_cluster_ids:
  - P0-05-RS02-C01
  canonical_cluster_name: 产品生命周期角色窗口
  owner_capability_group: P0-05
  secondary_capability_groups:
  - P0-00
  - P0-04
  source_p0_groups:
  - P0-05
  research_subcard_refs:
  - P0-05-RS02
  batch_refs:
  - batch_005
  - batch_006
  - batch_013
  knowledge_types:
  - general_method
  - boundary_rule
  - source_gap_candidate
  expected_body_topics:
  - 阶段抽象命名
  - 阶段与叙事密度关系
  - 阶段与教育重心关系
  - 阶段与陈列更新关系
  required_relations:
  - 生命周期阶段 -> 产品角色强度
  - 生命周期阶段 -> 教育内容比重
  - 生命周期阶段 -> 陈列更新提示
  - 生命周期阶段 -> CTA 强度上限
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
  candidate_output_effect:
  - 使后续研究能在不同生命周期阶段下改变产品叙事任务，构造可比较的 role window，而非生成经营结论。
  source_gap_likelihood: high
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_042
  source_cluster_ids:
  - P0-05-RS02-C02
  canonical_cluster_name: 组货角色与渠道边界矩阵
  owner_capability_group: P0-05
  secondary_capability_groups:
  - P0-00
  - P0-02
  - P0-04
  source_p0_groups:
  - P0-05
  research_subcard_refs:
  - P0-05-RS02
  batch_refs:
  - batch_005
  - batch_006
  - batch_013
  knowledge_types:
  - relation_hint
  - boundary_rule
  - decision_required_candidate
  expected_body_topics:
  - 组货角色类型
  - 主次关系与陪衬关系
  - 渠道差异下的信息删减规则
  - 产品角色与主题化组合关系
  required_relations:
  - 组货角色 -> 产品叙事视角
  - 组货角色 -> display 邻接关系
  - 组货角色 -> CTA 信息稀疏度
  - 渠道边界 -> 可使用的信息类型
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
  candidate_output_effect:
  - 支持后续研究用“产品之间的角色关系”组织候选内容结构，降低单品空讲的模板化风险。
  source_gap_likelihood: medium
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
  - boundary_note_attached
- canonical_cluster_id: mkc_043
  source_cluster_ids:
  - P0-05-RS03-C01
  canonical_cluster_name: 场景适配条件与不适配条件
  owner_capability_group: P0-05
  secondary_capability_groups:
  - P0-01
  - P0-02
  - P0-03
  source_p0_groups:
  - P0-05
  research_subcard_refs:
  - P0-05-RS03
  batch_refs:
  - batch_008
  - batch_009
  - batch_004
  knowledge_types:
  - boundary_rule
  - general_method
  - evidence_requirement
  expected_body_topics:
  - 场景任务锚点
  - 场景切换条件
  - 场景中的动作限制
  - 不适配条件表达
  required_relations:
  - 场景任务 -> 产品角色
  - 场景限制 -> 不适配条件
  - 产品角色 -> 使用说明级教育
  - 场景匹配度 -> CTA 上限
  risk_boundaries:
  - 不得写真实顾客画像事实
  - 不得写身材、功效保证
  - 不得写无证据舒适、性能结论
  - 不得写真实反馈
  evidence_classes:
  - 场景叙事方法来源
  - 任务导向内容来源
  - 边界政策来源
  candidate_output_effect:
  - 让后续候选研究围绕“场景条件 -> 动作任务 -> 产品角色”而不是“效果保证”展开。
  source_gap_likelihood: high
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_044
  source_cluster_ids:
  - P0-05-RS03-C02
  canonical_cluster_name: 使用教育与结果 claim 分界
  owner_capability_group: P0-05
  secondary_capability_groups:
  - P0-00
  - P0-03
  source_p0_groups:
  - P0-05
  research_subcard_refs:
  - P0-05-RS03
  batch_refs:
  - batch_008
  - batch_009
  - batch_004
  knowledge_types:
  - evidence_requirement
  - boundary_rule
  - routing_hint
  expected_body_topics:
  - 教育性说明的允许范围
  - 演示与证明的区别
  - 比较语言的边界
  - 注意事项表达
  required_relations:
  - 教育说明 -> 可接受叙事节点
  - 演示动作 -> 非证明边界
  - 比较关系 -> 证据等级要求
  - claim 类型 -> routing 结果
  risk_boundaries:
  - 不得输出产品功效结论
  - 不得输出质量、耐久、舒适、性能结论
  - 不得输出可直接发布比较文案
  - 不得将演示等同证据
  evidence_classes:
  - 证据边界政策来源
  - 教育内容方法来源
  - 比较语言规范来源
  candidate_output_effect:
  - 为后续研究提供强约束路由，把高风险结论隔离出候选方法簇，保持研究图安全。
  source_gap_likelihood: highest
  decision_required_likelihood: medium
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
- canonical_cluster_id: mkc_045
  source_cluster_ids:
  - P0-05-RS04-C01
  canonical_cluster_name: 产品到陈列叙事关系语法
  owner_capability_group: P0-05
  secondary_capability_groups:
  - P0-03
  - P0-04
  source_p0_groups:
  - P0-05
  research_subcard_refs:
  - P0-05-RS04
  batch_refs:
  - batch_011
  - batch_014
  - batch_003
  knowledge_types:
  - relation_hint
  - general_method
  - boundary_rule
  expected_body_topics:
  - 位置关系
  - 邻接关系
  - 主次层级
  - 主题化组合
  required_relations:
  - 产品角色 -> display 位置
  - 产品角色 -> 邻接对象
  - grouping rule -> narrative emphasis
  - display cue -> 拍摄镜头线索
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
  candidate_output_effect:
  - 为后续研究输出产品与 display 的关系槽位，使内容具备可视结构但不落到门店实例。
  source_gap_likelihood: medium
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
  - boundary_note_attached
- canonical_cluster_id: mkc_046
  source_cluster_ids:
  - P0-05-RS04-C02
  canonical_cluster_name: 产品到角色到叙事跨域关系
  owner_capability_group: P0-05
  secondary_capability_groups:
  - P0-00
  - P0-01
  - P0-02
  - P0-04
  source_p0_groups:
  - P0-05
  research_subcard_refs:
  - P0-05-RS04
  batch_refs:
  - batch_011
  - batch_014
  - batch_003
  knowledge_types:
  - relation_hint
  - routing_hint
  - decision_required_candidate
  expected_body_topics:
  - 产品与角色语气的关系
  - 产品与组织生态视角的连接
  - 产品与 display 动作的接口
  - 产品与 narrative 段落的跨域对齐
  required_relations:
  - product role -> role perspective
  - product role -> display action
  - product role -> narrative sequence
  - cross-domain overlap -> strictest_wins_note
  risk_boundaries:
  - 不得写 workflow、serving、runtime、DIFY 结构
  - 不得把 cross-domain relation map 写成控制面实现
  - 不得让产品簇接管 P0-00 规则主权
  evidence_classes:
  - relation-map method reference
  - cross-domain boundary policy
  - routing policy reference
  candidate_output_effect:
  - 为后续 research planning 提供跨域接口提示，但不形成执行图或产线对象。
  source_gap_likelihood: high
  decision_required_likelihood: high
  normalization_notes:
  - canonical_id_rewritten
  - single_source_cluster_normalized
  - boundary_note_attached
readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false
--- FILE: cluster_ownership_arbitration_matrix.csv
canonical_cluster_id,canonical_cluster_name,source_cluster_ids,owner_capability_group,secondary_capability_groups,owner_rationale,shared_reason,conflict_notes,arbitration_status
mkc_001,入口槽位契约,P0-00-RS01-C01,P0-00,P0-01|P0-04|P0-05,主责在控制面、route、seal、reentry、strictest-wins 或 research-only bindability。,作为入口契约被多个 P0 消费，但不下沉为领域知识。,none_material_to_owner_assignment,resolved
mkc_002,路由阶梯与降级触发,P0-00-RS01-C02,P0-00,P0-01|P0-03|P0-04|P0-05,主责在控制面、route、seal、reentry、strictest-wins 或 research-only bindability。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_003,全局 claim 与证据边界检查,P0-00-RS02-C01,P0-00,P0-03|P0-05,主责在控制面、route、seal、reentry、strictest-wins 或 research-only bindability。,P0-03 与 P0-05 均依赖此全局证据门，但不得在业务簇内重写。,none_material_to_owner_assignment,resolved
mkc_004,异常分发与再进入规则,P0-00-RS02-C02|P0-00-RS04-C02,P0-00,P0-01|P0-02|P0-03|P0-04|P0-05,主责在控制面、route、seal、reentry、strictest-wins 或 research-only bindability。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,合并保留“触发去向”与“再进入条件”两层；未把两者折叠为单一审批流。,resolved
mkc_005,能力组合与 strictest-wins 裁定,P0-00-RS03-C01,P0-00,P0-01|P0-04|P0-05,主责在控制面、route、seal、reentry、strictest-wins 或 research-only bindability。,多能力请求需共享 strictest-wins 规则。,none_material_to_owner_assignment,resolved
mkc_006,研究资产绑定与非生产封印,P0-00-RS03-C02|P0-00-RS04-C01,P0-00,P0-01|P0-02|P0-03|P0-04|P0-05,主责在控制面、route、seal、reentry、strictest-wins 或 research-only bindability。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,合并后仅保留 research-only bindability 与 non-production seal；未引入任何 runtime artifact。,resolved
mkc_007,企业叙事骨架,W2-P0-01-RS01-CL01,P0-01,P0-02|P0-03|P0-05,主责在 enterprise narrative framing、proof-slot narrative use、series planning 或 anti-template narrative method。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_008,证明槽位与价值转译,W2-P0-01-RS01-CL02|W2-P0-01-RS02-CL02,P0-01,P0-03|P0-04|P0-05,主责在 enterprise narrative framing、proof-slot narrative use、series planning 或 anti-template narrative method。,P0-01 需要 proof slot，P0-03/04/05 需要 observable translation 接口。,与 P0-03 的 process / quality proof ontology 相邻；本簇仅保留 narrative framing 与 observable translation。,resolved_with_boundary_note
mkc_009,故事弧线适用边界,W2-P0-01-RS02-CL01,P0-01,P0-05,主责在 enterprise narrative framing、proof-slot narrative use、series planning 或 anti-template narrative method。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_010,反模板叙事锚点,W2-P0-01-RS03-CL01,P0-01,P0-02|P0-03|P0-04|P0-05,主责在 enterprise narrative framing、proof-slot narrative use、series planning 或 anti-template narrative method。,DQ anti-template anchor 被多卡复用但不等于 topic library。,none_material_to_owner_assignment,resolved
mkc_011,叙事放大禁区与风险路由,W2-P0-01-RS03-CL02,P0-01,P0-00|P0-03|P0-05,主责在 enterprise narrative framing、proof-slot narrative use、series planning 或 anti-template narrative method。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_012,系列轴与跨形态资产单元,W2-P0-01-RS04-CL01|W2-P0-01-RS04-CL02,P0-01,P0-02|P0-03|P0-04|P0-05,主责在 enterprise narrative framing、proof-slot narrative use、series planning 或 anti-template narrative method。,series axis 与 cross-format asset unit 跨多卡复用。,none_material_to_owner_assignment,resolved
mkc_013,角色发声寄存器,P0-02-RS01-C01,P0-02,P0-01|P0-04|P0-05,主责在 role voice、persona surface、organization perspective 或 role authorization boundary。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_014,语气校准与去人物化,P0-02-RS01-C02,P0-02,P0-01|P0-03|P0-04,主责在 role voice、persona surface、organization perspective 或 role authorization boundary。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_015,组织生态角色网格,P0-02-RS02-C01,P0-02,P0-04|P0-05,主责在 role voice、persona surface、organization perspective 或 role authorization boundary。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_016,视角切换与公开安全边界,P0-02-RS02-C02,P0-02,P0-00|P0-04|P0-05,主责在 role voice、persona surface、organization perspective 或 role authorization boundary。,public-safe 边界与 P0-00、P0-04 共用。,none_material_to_owner_assignment,resolved
mkc_017,受众距离与信息深浅轴,P0-02-RS03-C01,P0-02,P0-01|P0-05,主责在 role voice、persona surface、organization perspective 或 role authorization boundary。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_018,情绪温度层与信任门控,P0-02-RS03-C02,P0-02,P0-00|P0-03|P0-05,主责在 role voice、persona surface、organization perspective 或 role authorization boundary。,trust signal 需要与全局证据边界共振。,none_material_to_owner_assignment,resolved
mkc_019,角色授权表面与人物故事红线,P0-02-RS04-C01|P0-02-RS04-C02,P0-02,P0-00|P0-04,主责在 role voice、persona surface、organization perspective 或 role authorization boundary。,generic role authorization 与 retail authorization 共享红线。,P0-02 保持 generic role authorization；零售/加盟具体权限仍由 P0-04 二级承接。,resolved_with_boundary_note
mkc_020,品类解释与属性槽位骨架,P0-03-RS01-CL01|P0-03-RS01-CL02,P0-03,P0-04|P0-05,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,作为 P0-03 对象骨架被 P0-04/P0-05 消费。,none_material_to_owner_assignment,resolved
mkc_021,同类比较维度与禁比边界,P0-03-RS01-CL03,P0-03,P0-05,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_022,面料家族与属性边界,P0-03-RS02-CL01,P0-03,P0-04|P0-05,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_023,颜色表达与视觉解释边界,P0-03-RS02-CL02,P0-03,P0-04|P0-05,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,色彩模块与 P0-04 主题色彩故事共享词汇但 owner 不变。,none_material_to_owner_assignment,resolved
mkc_024,版型廓形剪裁术语,P0-03-RS02-CL03,P0-03,P0-04|P0-05,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_025,工艺观察线索与讲解节点,P0-03-RS02-CL04|P0-03-RS04-CL01,P0-03,P0-04|P0-05,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,工艺观察节点被 narrative 与 display 侧复用。,合并保留“可见工艺节点”与“讲解顺序”；未扩展为完整工艺本体。,resolved_with_boundary_note
mkc_026,身材效果语言阶梯与场景化观察,P0-03-RS03-CL01|P0-03-RS03-CL03,P0-03,P0-05,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,scene observation 与 product scene-fit 存在共享边缘。,与 P0-05 场景适配相邻；本簇主责 claim-language stair 与 non-conclusive scene observation。,resolved_with_boundary_note
mkc_027,舒适性能耐用品质证据阶梯,P0-03-RS03-CL02,P0-03,P0-00|P0-05,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_028,品质观察项与证明类型路由,P0-03-RS04-CL02|P0-03-RS04-CL03,P0-03,P0-01,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,proof-type taxonomy 被 enterprise narrative 引用，但 quality routing 主权仍归 P0-03。,合并保留 proof-type taxonomy 与 certification-claim routing；未声明任何真实认证存在。,resolved_with_boundary_note
mkc_029,工艺品质内容的可拍摄表达,P0-03-RS04-CL04,P0-03,P0-01|P0-04,主责在 apparel/material/fit/craft/quality/claim-evidence domain boundary。,filmability 方法与 P0-01/P0-04 共用。,none_material_to_owner_assignment,resolved
mkc_030,Look 拆解观察骨架,W5_P0_04_RS01_CL01,P0-04,P0-03|P0-05,主责在 display/store-daily/SOP/contentization/retail permission frame。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_031,主题与色彩故事关系网,W5_P0_04_RS01_CL02,P0-04,P0-01|P0-03|P0-05,主责在 display/store-daily/SOP/contentization/retail permission frame。,主题-色彩关系与 P0-03/P0-01/P0-05 相邻，但仍以 display contentization 为主。,none_material_to_owner_assignment,resolved_with_boundary_note
mkc_032,陈列区位与可拍摄视觉锚点,W5_P0_04_RS01_CL03,P0-04,P0-02|P0-05,主责在 display/store-daily/SOP/contentization/retail permission frame。,display zone anchor 为 role/product 侧提供 filmable interface。,none_material_to_owner_assignment,resolved
mkc_033,门店日常动作观察切片,W5_P0_04_RS02_CL01,P0-04,P0-02,主责在 display/store-daily/SOP/contentization/retail permission frame。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_034,动作转内容槽位与演示三段式,W5_P0_04_RS02_CL02|W5_P0_04_RS03_CL02,P0-04,P0-01|P0-02,主责在 display/store-daily/SOP/contentization/retail permission frame。,动作到内容的结构槽位被 narrative/role 侧消费。,动作转内容与演示三段式只共享结构槽位；不生成脚本。,resolved_with_boundary_note
mkc_035,门店日常内容化风险红线,W5_P0_04_RS02_CL03,P0-04,P0-00|P0-02,主责在 display/store-daily/SOP/contentization/retail permission frame。,门店日常风险红线与 P0-00/P0-02 共享。,none_material_to_owner_assignment,resolved
mkc_036,陈列动作 SOP 节点框架,W5_P0_04_RS03_CL01,P0-04,P0-02|P0-05,主责在 display/store-daily/SOP/contentization/retail permission frame。,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_037,零售角色动作权限与加盟改写边界,W5_P0_04_RS04_CL01|W5_P0_04_RS04_CL02,P0-04,P0-02,主责在 display/store-daily/SOP/contentization/retail permission frame。,retail permission boundary 与 generic role authorization 共边界。,零售角色矩阵与加盟改写边界并置；真实授权、合同、组织事实仍 route away。,resolved_with_boundary_note
mkc_038,异常回退与前复核路由提示,W5_P0_04_RS03_CL03|W5_P0_04_RS04_CL03,P0-04,P0-00,主责在 display/store-daily/SOP/contentization/retail permission frame。,局部 review/precheck 与 P0-00 总路由共享词汇。,P0-04 仅保留局部 precheck/review hint；控制面总路由仍归 P0-00。,resolved_with_boundary_note
mkc_039,产品叙事角色入场框架,P0-05-RS01-C01,P0-05,P0-01|P0-04,主责在 product role narrative、CTA boundary、scene-fit、assortment relation 或 product-display relation.,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_040,叙事到 CTA 的非硬卖边界,P0-05-RS01-C02,P0-05,P0-00|P0-01|P0-04,主责在 product role narrative、CTA boundary、scene-fit、assortment relation 或 product-display relation.,CTA 边界与 P0-00 route gate、P0-04 收束接口互相关联。,none_material_to_owner_assignment,resolved
mkc_041,产品生命周期角色窗口,P0-05-RS02-C01,P0-05,P0-00|P0-04,主责在 product role narrative、CTA boundary、scene-fit、assortment relation 或 product-display relation.,共享发生在 source_p0_groups 或 shared_with_capability_cards，owner 不转移。,none_material_to_owner_assignment,resolved
mkc_042,组货角色与渠道边界矩阵,P0-05-RS02-C02,P0-05,P0-00|P0-02|P0-04,主责在 product role narrative、CTA boundary、scene-fit、assortment relation 或 product-display relation.,assortment/channel relation 同时触碰 P0-02 角色网格与 P0-04 display support-only。,A2 support-only 边界保留为 conflict note；未扩成完整 display / channel system。,resolved_with_boundary_note
mkc_043,场景适配条件与不适配条件,P0-05-RS03-C01,P0-05,P0-01|P0-02|P0-03,主责在 product role narrative、CTA boundary、scene-fit、assortment relation 或 product-display relation.,scene-fit 语言与 P0-01/P0-02/P0-03 共享边界。,none_material_to_owner_assignment,resolved
mkc_044,使用教育与结果 claim 分界,P0-05-RS03-C02,P0-05,P0-00|P0-03,主责在 product role narrative、CTA boundary、scene-fit、assortment relation 或 product-display relation.,education-vs-claim 与 P0-03/P0-00 的证据门共用。,none_material_to_owner_assignment,resolved
mkc_045,产品到陈列叙事关系语法,P0-05-RS04-C01,P0-05,P0-03|P0-04,主责在 product role narrative、CTA boundary、scene-fit、assortment relation 或 product-display relation.,product-display grammar 与 P0-04 display frame 共享视觉关系。,产品为主语、陈列为关系语法；未接管 P0-04 display-system ownership。,resolved_with_boundary_note
mkc_046,产品到角色到叙事跨域关系,P0-05-RS04-C02,P0-05,P0-00|P0-01|P0-02|P0-04,主责在 product role narrative、CTA boundary、scene-fit、assortment relation 或 product-display relation.,product-role-narrative crosswalk 与 P0-00/P0-01/P0-02/P0-04 均有接口。,可共享 cross-domain 节点；strictest-wins 与 workflow 禁令仍由 P0-00 控制。,resolved_with_boundary_note
--- FILE: capability_to_cluster_crosswalk.csv
canonical_cluster_id,canonical_cluster_name,owner_capability_group,secondary_capability_groups,source_cluster_ids
mkc_001,入口槽位契约,P0-00,P0-01|P0-04|P0-05,P0-00-RS01-C01
mkc_002,路由阶梯与降级触发,P0-00,P0-01|P0-03|P0-04|P0-05,P0-00-RS01-C02
mkc_003,全局 claim 与证据边界检查,P0-00,P0-03|P0-05,P0-00-RS02-C01
mkc_004,异常分发与再进入规则,P0-00,P0-01|P0-02|P0-03|P0-04|P0-05,P0-00-RS02-C02|P0-00-RS04-C02
mkc_005,能力组合与 strictest-wins 裁定,P0-00,P0-01|P0-04|P0-05,P0-00-RS03-C01
mkc_006,研究资产绑定与非生产封印,P0-00,P0-01|P0-02|P0-03|P0-04|P0-05,P0-00-RS03-C02|P0-00-RS04-C01
mkc_007,企业叙事骨架,P0-01,P0-02|P0-03|P0-05,W2-P0-01-RS01-CL01
mkc_008,证明槽位与价值转译,P0-01,P0-03|P0-04|P0-05,W2-P0-01-RS01-CL02|W2-P0-01-RS02-CL02
mkc_009,故事弧线适用边界,P0-01,P0-05,W2-P0-01-RS02-CL01
mkc_010,反模板叙事锚点,P0-01,P0-02|P0-03|P0-04|P0-05,W2-P0-01-RS03-CL01
mkc_011,叙事放大禁区与风险路由,P0-01,P0-00|P0-03|P0-05,W2-P0-01-RS03-CL02
mkc_012,系列轴与跨形态资产单元,P0-01,P0-02|P0-03|P0-04|P0-05,W2-P0-01-RS04-CL01|W2-P0-01-RS04-CL02
mkc_013,角色发声寄存器,P0-02,P0-01|P0-04|P0-05,P0-02-RS01-C01
mkc_014,语气校准与去人物化,P0-02,P0-01|P0-03|P0-04,P0-02-RS01-C02
mkc_015,组织生态角色网格,P0-02,P0-04|P0-05,P0-02-RS02-C01
mkc_016,视角切换与公开安全边界,P0-02,P0-00|P0-04|P0-05,P0-02-RS02-C02
mkc_017,受众距离与信息深浅轴,P0-02,P0-01|P0-05,P0-02-RS03-C01
mkc_018,情绪温度层与信任门控,P0-02,P0-00|P0-03|P0-05,P0-02-RS03-C02
mkc_019,角色授权表面与人物故事红线,P0-02,P0-00|P0-04,P0-02-RS04-C01|P0-02-RS04-C02
mkc_020,品类解释与属性槽位骨架,P0-03,P0-04|P0-05,P0-03-RS01-CL01|P0-03-RS01-CL02
mkc_021,同类比较维度与禁比边界,P0-03,P0-05,P0-03-RS01-CL03
mkc_022,面料家族与属性边界,P0-03,P0-04|P0-05,P0-03-RS02-CL01
mkc_023,颜色表达与视觉解释边界,P0-03,P0-04|P0-05,P0-03-RS02-CL02
mkc_024,版型廓形剪裁术语,P0-03,P0-04|P0-05,P0-03-RS02-CL03
mkc_025,工艺观察线索与讲解节点,P0-03,P0-04|P0-05,P0-03-RS02-CL04|P0-03-RS04-CL01
mkc_026,身材效果语言阶梯与场景化观察,P0-03,P0-05,P0-03-RS03-CL01|P0-03-RS03-CL03
mkc_027,舒适性能耐用品质证据阶梯,P0-03,P0-00|P0-05,P0-03-RS03-CL02
mkc_028,品质观察项与证明类型路由,P0-03,P0-01,P0-03-RS04-CL02|P0-03-RS04-CL03
mkc_029,工艺品质内容的可拍摄表达,P0-03,P0-01|P0-04,P0-03-RS04-CL04
mkc_030,Look 拆解观察骨架,P0-04,P0-03|P0-05,W5_P0_04_RS01_CL01
mkc_031,主题与色彩故事关系网,P0-04,P0-01|P0-03|P0-05,W5_P0_04_RS01_CL02
mkc_032,陈列区位与可拍摄视觉锚点,P0-04,P0-02|P0-05,W5_P0_04_RS01_CL03
mkc_033,门店日常动作观察切片,P0-04,P0-02,W5_P0_04_RS02_CL01
mkc_034,动作转内容槽位与演示三段式,P0-04,P0-01|P0-02,W5_P0_04_RS02_CL02|W5_P0_04_RS03_CL02
mkc_035,门店日常内容化风险红线,P0-04,P0-00|P0-02,W5_P0_04_RS02_CL03
mkc_036,陈列动作 SOP 节点框架,P0-04,P0-02|P0-05,W5_P0_04_RS03_CL01
mkc_037,零售角色动作权限与加盟改写边界,P0-04,P0-02,W5_P0_04_RS04_CL01|W5_P0_04_RS04_CL02
mkc_038,异常回退与前复核路由提示,P0-04,P0-00,W5_P0_04_RS03_CL03|W5_P0_04_RS04_CL03
mkc_039,产品叙事角色入场框架,P0-05,P0-01|P0-04,P0-05-RS01-C01
mkc_040,叙事到 CTA 的非硬卖边界,P0-05,P0-00|P0-01|P0-04,P0-05-RS01-C02
mkc_041,产品生命周期角色窗口,P0-05,P0-00|P0-04,P0-05-RS02-C01
mkc_042,组货角色与渠道边界矩阵,P0-05,P0-00|P0-02|P0-04,P0-05-RS02-C02
mkc_043,场景适配条件与不适配条件,P0-05,P0-01|P0-02|P0-03,P0-05-RS03-C01
mkc_044,使用教育与结果 claim 分界,P0-05,P0-00|P0-03,P0-05-RS03-C02
mkc_045,产品到陈列叙事关系语法,P0-05,P0-03|P0-04,P0-05-RS04-C01
mkc_046,产品到角色到叙事跨域关系,P0-05,P0-00|P0-01|P0-02|P0-04,P0-05-RS04-C02
--- FILE: batch_to_cluster_crosswalk.csv
batch_ref,canonical_cluster_ids,canonical_cluster_names,owner_capability_groups
batch_001,mkc_019|mkc_026|mkc_027,角色授权表面与人物故事红线|身材效果语言阶梯与场景化观察|舒适性能耐用品质证据阶梯,P0-02|P0-03
batch_002,mkc_008|mkc_009|mkc_020|mkc_021|mkc_039|mkc_040,证明槽位与价值转译|故事弧线适用边界|品类解释与属性槽位骨架|同类比较维度与禁比边界|产品叙事角色入场框架|叙事到 CTA 的非硬卖边界,P0-01|P0-03|P0-05
batch_003,mkc_020|mkc_021|mkc_022|mkc_023|mkc_024|mkc_025|mkc_028|mkc_029|mkc_030|mkc_031|mkc_045|mkc_046,品类解释与属性槽位骨架|同类比较维度与禁比边界|面料家族与属性边界|颜色表达与视觉解释边界|版型廓形剪裁术语|工艺观察线索与讲解节点|品质观察项与证明类型路由|工艺品质内容的可拍摄表达|Look 拆解观察骨架|主题与色彩故事关系网|产品到陈列叙事关系语法|产品到角色到叙事跨域关系,P0-03|P0-04|P0-05
batch_004,mkc_021|mkc_026|mkc_027|mkc_043|mkc_044,同类比较维度与禁比边界|身材效果语言阶梯与场景化观察|舒适性能耐用品质证据阶梯|场景适配条件与不适配条件|使用教育与结果 claim 分界,P0-03|P0-05
batch_005,mkc_008|mkc_022|mkc_024|mkc_025|mkc_039|mkc_040|mkc_041|mkc_042,证明槽位与价值转译|面料家族与属性边界|版型廓形剪裁术语|工艺观察线索与讲解节点|产品叙事角色入场框架|叙事到 CTA 的非硬卖边界|产品生命周期角色窗口|组货角色与渠道边界矩阵,P0-01|P0-03|P0-05
batch_006,mkc_015|mkc_016|mkc_036,组织生态角色网格|视角切换与公开安全边界|陈列动作 SOP 节点框架,P0-02|P0-04
batch_007,mkc_007|mkc_008|mkc_012|mkc_013|mkc_014|mkc_037|mkc_038,企业叙事骨架|证明槽位与价值转译|系列轴与跨形态资产单元|角色发声寄存器|语气校准与去人物化|零售角色动作权限与加盟改写边界|异常回退与前复核路由提示,P0-01|P0-02|P0-04
batch_008,mkc_013|mkc_014|mkc_017|mkc_018|mkc_043|mkc_044,角色发声寄存器|语气校准与去人物化|受众距离与信息深浅轴|情绪温度层与信任门控|场景适配条件与不适配条件|使用教育与结果 claim 分界,P0-02|P0-05
batch_009,mkc_007|mkc_008|mkc_012|mkc_025|mkc_028|mkc_029|mkc_017|mkc_018|mkc_039|mkc_040|mkc_043|mkc_044,企业叙事骨架|证明槽位与价值转译|系列轴与跨形态资产单元|工艺观察线索与讲解节点|品质观察项与证明类型路由|工艺品质内容的可拍摄表达|受众距离与信息深浅轴|情绪温度层与信任门控|产品叙事角色入场框架|叙事到 CTA 的非硬卖边界|场景适配条件与不适配条件|使用教育与结果 claim 分界,P0-01|P0-03|P0-02|P0-05
batch_010,mkc_010|mkc_011|mkc_013|mkc_014|mkc_015|mkc_016|mkc_033|mkc_034|mkc_035,反模板叙事锚点|叙事放大禁区与风险路由|角色发声寄存器|语气校准与去人物化|组织生态角色网格|视角切换与公开安全边界|门店日常动作观察切片|动作转内容槽位与演示三段式|门店日常内容化风险红线,P0-01|P0-02|P0-04
batch_011,mkc_010|mkc_011|mkc_017|mkc_018|mkc_023|mkc_024|mkc_025|mkc_030|mkc_031|mkc_032|mkc_036|mkc_045|mkc_046,反模板叙事锚点|叙事放大禁区与风险路由|受众距离与信息深浅轴|情绪温度层与信任门控|颜色表达与视觉解释边界|版型廓形剪裁术语|工艺观察线索与讲解节点|Look 拆解观察骨架|主题与色彩故事关系网|陈列区位与可拍摄视觉锚点|陈列动作 SOP 节点框架|产品到陈列叙事关系语法|产品到角色到叙事跨域关系,P0-01|P0-02|P0-03|P0-04|P0-05
batch_012,mkc_012|mkc_025|mkc_028|mkc_029|mkc_030|mkc_032|mkc_033|mkc_034|mkc_036|mkc_038,系列轴与跨形态资产单元|工艺观察线索与讲解节点|品质观察项与证明类型路由|工艺品质内容的可拍摄表达|Look 拆解观察骨架|陈列区位与可拍摄视觉锚点|门店日常动作观察切片|动作转内容槽位与演示三段式|陈列动作 SOP 节点框架|异常回退与前复核路由提示,P0-01|P0-03|P0-04
batch_013,mkc_007|mkc_008|mkc_015|mkc_016|mkc_019|mkc_034|mkc_035|mkc_037|mkc_038|mkc_041|mkc_042,企业叙事骨架|证明槽位与价值转译|组织生态角色网格|视角切换与公开安全边界|角色授权表面与人物故事红线|动作转内容槽位与演示三段式|门店日常内容化风险红线|零售角色动作权限与加盟改写边界|异常回退与前复核路由提示|产品生命周期角色窗口|组货角色与渠道边界矩阵,P0-01|P0-02|P0-04|P0-05
batch_014,mkc_001|mkc_002|mkc_003|mkc_004|mkc_005|mkc_006|mkc_010|mkc_011|mkc_019|mkc_020|mkc_026|mkc_027|mkc_035|mkc_038|mkc_045|mkc_046,入口槽位契约|路由阶梯与降级触发|全局 claim 与证据边界检查|异常分发与再进入规则|能力组合与 strictest-wins 裁定|研究资产绑定与非生产封印|反模板叙事锚点|叙事放大禁区与风险路由|角色授权表面与人物故事红线|品类解释与属性槽位骨架|身材效果语言阶梯与场景化观察|舒适性能耐用品质证据阶梯|门店日常内容化风险红线|异常回退与前复核路由提示|产品到陈列叙事关系语法|产品到角色到叙事跨域关系,P0-00|P0-01|P0-02|P0-03|P0-04|P0-05
--- FILE: master_knowledge_map.yaml
map_id: W7_shared_cluster_master_map
map_version: v0_1
status: integration_only
integration_role: W1-W6 normalization_dedupe_cluster_ownership_arbitration_batch_alignment_schema_rewrite_only
scope_guardrails:
  adds_new_industry_knowledge: false
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  production_ready: false
  release_ready: false
input_validation_summary:
  w1_w6_identified_as_p0_00_to_p0_05: true
  each_p0_has_4_research_subcards: true
  all_source_batch_refs_in_allowed_range: true
  all_source_readiness_false: true
  total_source_clusters: 58
  total_canonical_clusters: 46
normalization_issue_ledger:
- issue_id: NI-001
  issue_type: cluster_id_convention_mismatch
  severity: medium
  observed_in:
  - W1
  - W2
  - W3
  - W4
  - W5
  - W6
  description: Raw cluster_id styles mix plain P0 ids, W2-prefixed ids, and W5 underscore-prefixed ids; canonical ids rewritten to mkc_###.
  action: fixed_in_w7
  notes: source ids retained only in source_cluster_ids.
- issue_id: NI-002
  issue_type: batch_ref_shape_mismatch
  severity: medium
  observed_in:
  - W1
  - W2
  - W3
  - W4
  - W5
  - W6
  description: batch_refs appear as flat lists in some maps and primary/secondary dicts in others; W7 normalizes to flat allowed batch set only.
  action: fixed_in_w7
  notes: No batch outside batch_001~batch_014 retained.
- issue_id: NI-003
  issue_type: yaml_anchor_alias_forward_reference
  severity: high
  observed_in:
  - W4
  description: W4 uses forward alias references for subcard maps; anchors/aliases are removed in W7 output.
  action: fixed_in_w7
  notes: Final output contains no YAML anchor or alias structure.
- issue_id: NI-004
  issue_type: subcard_batch_collapse
  severity: high
  observed_in:
  - W1
  description: W1 subcard-level batch refs collapse to batch_014, while uploaded capability/batch references indicate broader allocation patterns.
  action: carried_to_unresolved_decision_ledger
  notes: Cluster-level source batch_refs are preserved; authority reconciliation is not invented.
- issue_id: NI-005
  issue_type: top_level_knowledge_mode_inconsistency
  severity: low
  observed_in:
  - W1
  - W6
  description: knowledge_mode is not consistently surfaced at top level; W7 normalizes all master structures to general_only.
  action: fixed_in_w7
  notes: No readiness state was enabled during rewrite.
- issue_id: NI-006
  issue_type: ledger_shape_mismatch
  severity: medium
  observed_in:
  - W1
  - W5
  - W6
  description: unresolved_decisions and source_gap_seed mix dict-list and string-list patterns.
  action: fixed_in_w7
  notes: All downstream ledgers rewritten to stable id-based records.
- issue_id: NI-007
  issue_type: shared_cluster_overlap_not_fully_mergeable
  severity: medium
  observed_in:
  - W2
  - W3
  - W4
  - W5
  - W6
  description: Several source clusters share vocabulary but not identical ownership scope, especially proof-slot, color-story, authorization, and precheck-routing families.
  action: split_preserved_with_ownership_notes
  notes: Unclear cases routed to unresolved_decision_ledger, not silently collapsed.
clusters_by_owner:
  P0-00:
  - canonical_cluster_id: mkc_001
    canonical_cluster_name: 入口槽位契约
  - canonical_cluster_id: mkc_002
    canonical_cluster_name: 路由阶梯与降级触发
  - canonical_cluster_id: mkc_003
    canonical_cluster_name: 全局 claim 与证据边界检查
  - canonical_cluster_id: mkc_004
    canonical_cluster_name: 异常分发与再进入规则
  - canonical_cluster_id: mkc_005
    canonical_cluster_name: 能力组合与 strictest-wins 裁定
  - canonical_cluster_id: mkc_006
    canonical_cluster_name: 研究资产绑定与非生产封印
  P0-01:
  - canonical_cluster_id: mkc_007
    canonical_cluster_name: 企业叙事骨架
  - canonical_cluster_id: mkc_008
    canonical_cluster_name: 证明槽位与价值转译
  - canonical_cluster_id: mkc_009
    canonical_cluster_name: 故事弧线适用边界
  - canonical_cluster_id: mkc_010
    canonical_cluster_name: 反模板叙事锚点
  - canonical_cluster_id: mkc_011
    canonical_cluster_name: 叙事放大禁区与风险路由
  - canonical_cluster_id: mkc_012
    canonical_cluster_name: 系列轴与跨形态资产单元
  P0-02:
  - canonical_cluster_id: mkc_013
    canonical_cluster_name: 角色发声寄存器
  - canonical_cluster_id: mkc_014
    canonical_cluster_name: 语气校准与去人物化
  - canonical_cluster_id: mkc_015
    canonical_cluster_name: 组织生态角色网格
  - canonical_cluster_id: mkc_016
    canonical_cluster_name: 视角切换与公开安全边界
  - canonical_cluster_id: mkc_017
    canonical_cluster_name: 受众距离与信息深浅轴
  - canonical_cluster_id: mkc_018
    canonical_cluster_name: 情绪温度层与信任门控
  - canonical_cluster_id: mkc_019
    canonical_cluster_name: 角色授权表面与人物故事红线
  P0-03:
  - canonical_cluster_id: mkc_020
    canonical_cluster_name: 品类解释与属性槽位骨架
  - canonical_cluster_id: mkc_021
    canonical_cluster_name: 同类比较维度与禁比边界
  - canonical_cluster_id: mkc_022
    canonical_cluster_name: 面料家族与属性边界
  - canonical_cluster_id: mkc_023
    canonical_cluster_name: 颜色表达与视觉解释边界
  - canonical_cluster_id: mkc_024
    canonical_cluster_name: 版型廓形剪裁术语
  - canonical_cluster_id: mkc_025
    canonical_cluster_name: 工艺观察线索与讲解节点
  - canonical_cluster_id: mkc_026
    canonical_cluster_name: 身材效果语言阶梯与场景化观察
  - canonical_cluster_id: mkc_027
    canonical_cluster_name: 舒适性能耐用品质证据阶梯
  - canonical_cluster_id: mkc_028
    canonical_cluster_name: 品质观察项与证明类型路由
  - canonical_cluster_id: mkc_029
    canonical_cluster_name: 工艺品质内容的可拍摄表达
  P0-04:
  - canonical_cluster_id: mkc_030
    canonical_cluster_name: Look 拆解观察骨架
  - canonical_cluster_id: mkc_031
    canonical_cluster_name: 主题与色彩故事关系网
  - canonical_cluster_id: mkc_032
    canonical_cluster_name: 陈列区位与可拍摄视觉锚点
  - canonical_cluster_id: mkc_033
    canonical_cluster_name: 门店日常动作观察切片
  - canonical_cluster_id: mkc_034
    canonical_cluster_name: 动作转内容槽位与演示三段式
  - canonical_cluster_id: mkc_035
    canonical_cluster_name: 门店日常内容化风险红线
  - canonical_cluster_id: mkc_036
    canonical_cluster_name: 陈列动作 SOP 节点框架
  - canonical_cluster_id: mkc_037
    canonical_cluster_name: 零售角色动作权限与加盟改写边界
  - canonical_cluster_id: mkc_038
    canonical_cluster_name: 异常回退与前复核路由提示
  P0-05:
  - canonical_cluster_id: mkc_039
    canonical_cluster_name: 产品叙事角色入场框架
  - canonical_cluster_id: mkc_040
    canonical_cluster_name: 叙事到 CTA 的非硬卖边界
  - canonical_cluster_id: mkc_041
    canonical_cluster_name: 产品生命周期角色窗口
  - canonical_cluster_id: mkc_042
    canonical_cluster_name: 组货角色与渠道边界矩阵
  - canonical_cluster_id: mkc_043
    canonical_cluster_name: 场景适配条件与不适配条件
  - canonical_cluster_id: mkc_044
    canonical_cluster_name: 使用教育与结果 claim 分界
  - canonical_cluster_id: mkc_045
    canonical_cluster_name: 产品到陈列叙事关系语法
  - canonical_cluster_id: mkc_046
    canonical_cluster_name: 产品到角色到叙事跨域关系
relation_index:
- relation_id: REL-001
  from: mkc_001
  to: mkc_002
  relation_type: precedes_route_evaluation
- relation_id: REL-002
  from: mkc_003
  to: mkc_004
  relation_type: feeds_exception_dispatch
- relation_id: REL-003
  from: mkc_005
  to: mkc_046
  relation_type: strictest_wins_applies_to_cross_domain_product_relations
- relation_id: REL-004
  from: mkc_008
  to: mkc_028
  relation_type: proof_slot_references_quality_proof_types_without_owning_them
- relation_id: REL-005
  from: mkc_010
  to: mkc_029
  relation_type: shared_anchor_and_filmability_boundary
- relation_id: REL-006
  from: mkc_019
  to: mkc_037
  relation_type: generic_authorization_boundary_intersects_retail_permission_boundary
- relation_id: REL-007
  from: mkc_020
  to: mkc_039
  relation_type: product_role_entry_consumes_object_schema
- relation_id: REL-008
  from: mkc_027
  to: mkc_044
  relation_type: global_claim_ladder_constrains_product_education_boundary
- relation_id: REL-009
  from: mkc_031
  to: mkc_045
  relation_type: display_theme_color_supports_product_display_grammar
- relation_id: REL-010
  from: mkc_032
  to: mkc_034
  relation_type: visual_anchor_feeds_action_to_content_translation
- relation_id: REL-011
  from: mkc_036
  to: mkc_038
  relation_type: sop_nodes_feed_exception_and_precheck_handling
- relation_id: REL-012
  from: mkc_043
  to: mkc_044
  relation_type: scene_fit_expression_is_constrained_by_claim_boundary
registry_ref: shared_knowledge_cluster_registry.yaml
ownership_ref: cluster_ownership_arbitration_matrix.csv
capability_crosswalk_ref: capability_to_cluster_crosswalk.csv
batch_crosswalk_ref: batch_to_cluster_crosswalk.csv
generation_assignment_plan_ref: generation_assignment_plan.yaml
unresolved_decision_ledger_ref: unresolved_decision_ledger.yaml
source_gap_seed_ledger_ref: source_gap_seed_ledger.yaml
forbidden_output_attestation:
  no_candidatepack: true
  no_source_pack: true
  no_KE: true
  no_serving_projection: true
  no_RAG_context_bundle: true
  no_DIFY_workflow: true
  no_approved_passage_text: true
  no_production_ready_knowledge: true
  no_real_brand_or_sku_or_store_or_person_or_customer_fact: true
  no_yaml_anchor_or_alias: true
  no_raw_filecite_in_master_map: true
readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false
--- FILE: generation_assignment_plan.yaml
plan_id: W7_generation_assignment_plan
plan_version: v0_1
status: planning_stub_only
assignments:
- assignment_id: GA-001
  source_cluster_ids:
  - P0-00-RS01-C01
  - P0-00-RS01-C02
  - P0-00-RS02-C01
  target_capability_group: P0-00
  suggested_generation_scope: 仅规划 control-plane intake / route / evidence gate 的后续 codex scaffold，不生成 runtime rule 或 domain knowledge。
  prerequisite_source_gaps:
  - SG-001
  - SG-002
  prerequisite_decisions:
  - UD-005
  forbidden_outputs:
  - CandidatePack
  - KE
  - RAG context_bundle
  - DIFY workflow
  - route mutation
  readiness_required_false: true
- assignment_id: GA-002
  source_cluster_ids:
  - P0-00-RS02-C02
  - P0-00-RS04-C02
  - P0-00-RS03-C01
  - P0-00-RS03-C02
  - P0-00-RS04-C01
  target_capability_group: P0-00
  suggested_generation_scope: 仅规划 exception / reentry / strictest-wins / non-production sealing 的结构化编排提示。
  prerequisite_source_gaps:
  - SG-003
  - SG-004
  - SG-005
  prerequisite_decisions:
  - UD-004
  - UD-011
  forbidden_outputs:
  - production rule set
  - serving projection
  - approved passage text
  readiness_required_false: true
- assignment_id: GA-003
  source_cluster_ids:
  - W2-P0-01-RS01-CL01
  - W2-P0-01-RS01-CL02
  - W2-P0-01-RS02-CL02
  - W2-P0-01-RS02-CL01
  target_capability_group: P0-01
  suggested_generation_scope: 仅规划 enterprise narrative skeleton、proof-slot use、arc boundary 的后续研究拆解。
  prerequisite_source_gaps:
  - SG-006
  prerequisite_decisions:
  - UD-001
  forbidden_outputs:
  - brand story copy
  - real brand facts
  - founder story
  readiness_required_false: true
- assignment_id: GA-004
  source_cluster_ids:
  - W2-P0-01-RS03-CL01
  - W2-P0-01-RS03-CL02
  - W2-P0-01-RS04-CL01
  - W2-P0-01-RS04-CL02
  target_capability_group: P0-01
  suggested_generation_scope: 仅规划 anti-template anchor、risk routing、series/cross-format unit 的研究结构。
  prerequisite_source_gaps:
  - SG-007
  prerequisite_decisions:
  - UD-012
  forbidden_outputs:
  - topic calendar
  - publishable script
  - platform workflow
  readiness_required_false: true
- assignment_id: GA-005
  source_cluster_ids:
  - P0-02-RS01-C01
  - P0-02-RS01-C02
  - P0-02-RS03-C01
  - P0-02-RS03-C02
  target_capability_group: P0-02
  suggested_generation_scope: 仅规划 role voice、tone、audience distance、trust gate 的 method bundles。
  prerequisite_source_gaps:
  - SG-008
  prerequisite_decisions: []
  forbidden_outputs:
  - real person quote
  - customer story
  - authorization claim
  readiness_required_false: true
- assignment_id: GA-006
  source_cluster_ids:
  - P0-02-RS02-C01
  - P0-02-RS02-C02
  - P0-02-RS04-C01
  - P0-02-RS04-C02
  target_capability_group: P0-02
  suggested_generation_scope: 仅规划 org ecology、public-safe handoff、generic authorization boundary 的结构化稿架。
  prerequisite_source_gaps:
  - SG-008
  - SG-014
  prerequisite_decisions:
  - UD-003
  forbidden_outputs:
  - org chart
  - private ops record
  - retail contract fact
  readiness_required_false: true
- assignment_id: GA-007
  source_cluster_ids:
  - P0-03-RS01-CL01
  - P0-03-RS01-CL02
  - P0-03-RS01-CL03
  - P0-03-RS02-CL01
  - P0-03-RS02-CL02
  - P0-03-RS02-CL03
  target_capability_group: P0-03
  suggested_generation_scope: 仅规划 apparel object schema、material/color/fit terminology、comparison boundary 的后续研究包。
  prerequisite_source_gaps:
  - SG-009
  - SG-010
  prerequisite_decisions:
  - UD-002
  forbidden_outputs:
  - real SKU attribute sheet
  - effect claim
  - fit guarantee
  readiness_required_false: true
- assignment_id: GA-008
  source_cluster_ids:
  - P0-03-RS02-CL04
  - P0-03-RS04-CL01
  - P0-03-RS03-CL01
  - P0-03-RS03-CL03
  - P0-03-RS03-CL02
  - P0-03-RS04-CL02
  - P0-03-RS04-CL03
  - P0-03-RS04-CL04
  target_capability_group: P0-03
  suggested_generation_scope: 仅规划 craft/quality observability、body-effect language ladder、quality proof routing 的后续研究 scaffold。
  prerequisite_source_gaps:
  - SG-010
  - SG-011
  prerequisite_decisions:
  - UD-001
  - UD-006
  - UD-012
  forbidden_outputs:
  - quality guarantee
  - certification fact
  - publishable education copy
  readiness_required_false: true
- assignment_id: GA-009
  source_cluster_ids:
  - W5_P0_04_RS01_CL01
  - W5_P0_04_RS01_CL02
  - W5_P0_04_RS01_CL03
  target_capability_group: P0-04
  suggested_generation_scope: 仅规划 Look / theme-color / display-zone 的观察结构与 filmable interface。
  prerequisite_source_gaps:
  - SG-012
  prerequisite_decisions:
  - UD-002
  - UD-010
  forbidden_outputs:
  - real store lookbook
  - display ontology
  - store map
  readiness_required_false: true
- assignment_id: GA-010
  source_cluster_ids:
  - W5_P0_04_RS02_CL01
  - W5_P0_04_RS02_CL02
  - W5_P0_04_RS03_CL02
  - W5_P0_04_RS02_CL03
  target_capability_group: P0-04
  suggested_generation_scope: 仅规划 store-daily action slicing、action-to-content slots、risk redlines 的结构化研究输入。
  prerequisite_source_gaps:
  - SG-013
  prerequisite_decisions:
  - UD-004
  forbidden_outputs:
  - publishable script
  - employee story
  - customer interaction fact
  readiness_required_false: true
- assignment_id: GA-011
  source_cluster_ids:
  - W5_P0_04_RS03_CL01
  - W5_P0_04_RS04_CL01
  - W5_P0_04_RS04_CL02
  - W5_P0_04_RS03_CL03
  - W5_P0_04_RS04_CL03
  target_capability_group: P0-04
  suggested_generation_scope: 仅规划 merchandising SOP nodes、retail permission boundary、exception/review hints 的研究框架。
  prerequisite_source_gaps:
  - SG-014
  prerequisite_decisions:
  - UD-003
  - UD-004
  forbidden_outputs:
  - training script
  - sales SOP
  - franchise fact
  readiness_required_false: true
- assignment_id: GA-012
  source_cluster_ids:
  - P0-05-RS01-C01
  - P0-05-RS01-C02
  target_capability_group: P0-05
  suggested_generation_scope: 仅规划 product role entry 与 CTA boundary 的 narrative skeleton。
  prerequisite_source_gaps:
  - SG-002
  prerequisite_decisions:
  - UD-007
  forbidden_outputs:
  - direct sales copy
  - real SKU narrative
  - CTA playbook
  readiness_required_false: true
- assignment_id: GA-013
  source_cluster_ids:
  - P0-05-RS02-C01
  - P0-05-RS02-C02
  - P0-05-RS03-C01
  - P0-05-RS03-C02
  target_capability_group: P0-05
  suggested_generation_scope: 仅规划 lifecycle / assortment / scene-fit / education-vs-claim 的边界化研究结构。
  prerequisite_source_gaps:
  - SG-015
  - SG-016
  - SG-010
  prerequisite_decisions:
  - UD-008
  - UD-009
  forbidden_outputs:
  - inventory fact
  - channel strategy fact
  - body result claim
  readiness_required_false: true
- assignment_id: GA-014
  source_cluster_ids:
  - P0-05-RS04-C01
  - P0-05-RS04-C02
  target_capability_group: P0-05
  suggested_generation_scope: 仅规划 product-display / product-role cross-domain relation hints，不生成 runtime structure。
  prerequisite_source_gaps:
  - SG-016
  prerequisite_decisions:
  - UD-009
  - UD-010
  - UD-011
  forbidden_outputs:
  - display system ontology
  - serving projection
  - workflow graph
  readiness_required_false: true
readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false
--- FILE: unresolved_decision_ledger.yaml
ledger_id: W7_unresolved_decision_ledger
ledger_version: v0_1
status: integration_only
items:
- decision_id: UD-001
  decision_type: owner_unclear
  priority: high
  title: 企业 proof slot 与质量/认证 proof-type 的 owner 分界
  affected_canonical_clusters:
  - mkc_008
  - mkc_028
  source_cluster_ids:
  - W2-P0-01-RS01-CL02
  - W2-P0-01-RS02-CL02
  - P0-03-RS04-CL02
  - P0-03-RS04-CL03
  why_unresolved: P0-01 负责 narrative proof-slot framing，P0-03 负责 quality / certification routing；共享 vocabulary 明显，但不宜强行单簇化。
  required_decision: 确认 proof-slot taxonomy 是共享上位字典还是由 P0-03 维护、P0-01 只引用。
  proposed_current_handling: keep_split_with_P0-01_secondary_to_P0-03
  readiness_required_false: true
- decision_id: UD-002
  decision_type: owner_unclear
  priority: medium
  title: 颜色表达与主题色彩故事的 owner 分界
  affected_canonical_clusters:
  - mkc_023
  - mkc_031
  source_cluster_ids:
  - P0-03-RS02-CL02
  - W5_P0_04_RS01_CL02
  why_unresolved: P0-03 处理 color expression boundary，P0-04 处理 display theme-color graph；词汇共享但视角不同。
  required_decision: 确认是否需要共享词表层，而保留 display-story ownership 在 P0-04。
  proposed_current_handling: keep_split_with_shared_vocabulary_note
  readiness_required_false: true
- decision_id: UD-003
  decision_type: owner_unclear
  priority: high
  title: generic role authorization 与 retail permission boundary 的切分
  affected_canonical_clusters:
  - mkc_019
  - mkc_037
  source_cluster_ids:
  - P0-02-RS04-C01
  - P0-02-RS04-C02
  - W5_P0_04_RS04_CL01
  - W5_P0_04_RS04_CL02
  why_unresolved: P0-02 是 generic role surface，P0-04 是 retail role-action / franchise rewrite；存在同类红线但不等价。
  required_decision: 确认是否建立 shared authorization vocabulary，或保持双维护。
  proposed_current_handling: keep_split_with_P0-02_owner_on_generic_role
  readiness_required_false: true
- decision_id: UD-004
  decision_type: P0-00_domain_leak
  priority: high
  title: P0-04 的 precheck/review hints 与 P0-00 控制路由的边界
  affected_canonical_clusters:
  - mkc_004
  - mkc_038
  source_cluster_ids:
  - P0-00-RS02-C02
  - P0-00-RS04-C02
  - W5_P0_04_RS03_CL03
  - W5_P0_04_RS04_CL03
  why_unresolved: 两侧都处理 exception/review vocabulary，但 P0-04 不能落成控制面总路由。
  required_decision: 确认 P0-04 是否只允许局部 review note，不允许 route taxonomy 扩展。
  proposed_current_handling: P0-00_owner_strictest
  readiness_required_false: true
- decision_id: UD-005
  decision_type: batch_alignment_conflict
  priority: high
  title: W1 子卡批次压缩为 batch_014 与上传 capability / matrix 参考的冲突
  affected_canonical_clusters:
  - mkc_001
  - mkc_002
  - mkc_003
  - mkc_004
  - mkc_005
  - mkc_006
  source_cluster_ids:
  - P0-00-RS01-C01
  - P0-00-RS01-C02
  - P0-00-RS02-C01
  - P0-00-RS02-C02
  - P0-00-RS03-C01
  - P0-00-RS03-C02
  - P0-00-RS04-C01
  - P0-00-RS04-C02
  why_unresolved: W1 source clusters only expose batch_014, while uploaded allocation references indicate broader P0-00 batch presence.
  required_decision: 确认 W7 是否应以后续 repository authority 回填 P0-00 non-014 batch coverage。
  proposed_current_handling: preserve_source_cluster_batch_refs_only
  readiness_required_false: true
- decision_id: UD-006
  decision_type: batch_alignment_conflict
  priority: medium
  title: P0-03-RS04 secondary batch_012 与上传 allocation reference 的零计数冲突
  affected_canonical_clusters:
  - mkc_025
  - mkc_028
  - mkc_029
  source_cluster_ids:
  - P0-03-RS04-CL01
  - P0-03-RS04-CL02
  - P0-03-RS04-CL03
  - P0-03-RS04-CL04
  why_unresolved: W4 自述已标记该冲突；W7 不能自行发明 authoritative correction。
  required_decision: 确认 batch_012 是 support-only 引用还是录入差异。
  proposed_current_handling: carry_forward_as_decision_required
  readiness_required_false: true
- decision_id: UD-007
  decision_type: term_normalization
  priority: medium
  title: CTA 术语是否统一降级为动作提示
  affected_canonical_clusters:
  - mkc_040
  source_cluster_ids:
  - P0-05-RS01-C02
  why_unresolved: W6 明确提出 CTA vocabulary 可能需要进一步降级，以降低执行层误读。
  required_decision: 确认后续 intake 是否统一使用 action-prompt vocabulary。
  proposed_current_handling: retain_cta_boundary_term_with_risk_note
  readiness_required_false: true
- decision_id: UD-008
  decision_type: taxonomy_granularity
  priority: medium
  title: 产品生命周期抽象阶段命名粒度
  affected_canonical_clusters:
  - mkc_041
  source_cluster_ids:
  - P0-05-RS02-C01
  why_unresolved: 阶段命名若过细，会滑向真实经营状态；过粗则失去 role-window 价值。
  required_decision: 确认只保留抽象阶段族还是允许更细的 method labels。
  proposed_current_handling: keep_abstract_stage_family_only
  readiness_required_false: true
- decision_id: UD-009
  decision_type: A2_full_display_system_overreach
  priority: high
  title: 组货/渠道边界与 A2 support-only 的切分
  affected_canonical_clusters:
  - mkc_042
  - mkc_045
  source_cluster_ids:
  - P0-05-RS02-C02
  - P0-05-RS04-C01
  why_unresolved: W6 明确警惕 A2 full system overreach；W7 不能把 display relation 扩成完整 display ontology。
  required_decision: 确认 display support context 仅保留 relation grammar 与 adjacency hints。
  proposed_current_handling: support_only_locked
  readiness_required_false: true
- decision_id: UD-010
  decision_type: CSO_axis_conflict
  priority: high
  title: content_x_display 是否会被误写成新 axis
  affected_canonical_clusters:
  - mkc_031
  - mkc_032
  - mkc_045
  - mkc_046
  source_cluster_ids:
  - W5_P0_04_RS01_CL02
  - W5_P0_04_RS01_CL03
  - P0-05-RS04-C01
  - P0-05-RS04-C02
  why_unresolved: charter 只允许 content_generation 与 display_styling 两个 scenario family，content_x_display 只能是 coordination view。
  required_decision: 确认任何 master structure 不新增第三场景轴。
  proposed_current_handling: coordination_view_only
  readiness_required_false: true
- decision_id: UD-011
  decision_type: DIFY_axis_conflict
  priority: high
  title: 跨域关系簇是否引入 workflow / serving / DIFY 结构字段
  affected_canonical_clusters:
  - mkc_046
  - mkc_006
  source_cluster_ids:
  - P0-05-RS04-C02
  - P0-00-RS03-C02
  - P0-00-RS04-C01
  why_unresolved: W6 与 charter 同时禁止 workflow/serving 化；W7 只能保留 research relation, 不保留 runtime structure。
  required_decision: 确认跨域关系图只输出 relation hints，不输出任何 execution graph fields。
  proposed_current_handling: runtime_fields_excluded
  readiness_required_false: true
- decision_id: UD-012
  decision_type: duplicate_requiring_merge
  priority: medium
  title: filmability / anchor vocabulary 是否需要共享上位字典
  affected_canonical_clusters:
  - mkc_010
  - mkc_029
  - mkc_032
  source_cluster_ids:
  - W2-P0-01-RS03-CL01
  - P0-03-RS04-CL04
  - W5_P0_04_RS01_CL03
  why_unresolved: 三者均强调 anchor / filmability，但 narrative、process-quality、display 三种 owner 视角不同。
  required_decision: 确认是否仅共享 DQ-level anchor vocabulary，不再进行更深合并。
  proposed_current_handling: keep_split_with_shared_anchor_lexicon_note
  readiness_required_false: true
readiness_required_false: true
--- FILE: source_gap_seed_ledger.yaml
ledger_id: W7_source_gap_seed_ledger
ledger_version: v0_1
status: integration_only
items:
- source_gap_id: SG-001
  gap_type: missing_source
  title: 控制面最小入口槽位 canonical 字典缺失
  affected_canonical_clusters:
  - mkc_001
  seed_origin:
  - W1
  missing_artifact: minimal intake slot dictionary
  next_source_needed: repository-side slot contract
  risk_tags:
  - missing_evidence
  - P0-00_domain_leak
  readiness_required_false: true
- source_gap_id: SG-002
  gap_type: missing_source
  title: claim 强度分级统一命名表缺失
  affected_canonical_clusters:
  - mkc_003
  - mkc_027
  - mkc_044
  seed_origin:
  - W1
  - W4
  - W6
  missing_artifact: claim taxonomy contract
  next_source_needed: cross-card claim ladder vocabulary
  risk_tags:
  - unsupported_hard_claim
  - missing_evidence
  readiness_required_false: true
- source_gap_id: SG-003
  gap_type: missing_source
  title: founder review 触发清单未穷举
  affected_canonical_clusters:
  - mkc_004
  - mkc_011
  - mkc_018
  seed_origin:
  - W1
  - W2
  - W3
  missing_artifact: founder review trigger ledger
  next_source_needed: review trigger policy
  risk_tags:
  - missing_evidence
  - owner_unclear
  readiness_required_false: true
- source_gap_id: SG-004
  gap_type: missing_source
  title: research-only 执行资产绑定白名单缺失
  affected_canonical_clusters:
  - mkc_006
  seed_origin:
  - W1
  missing_artifact: authorized asset binding contract
  next_source_needed: repository-side non-production asset whitelist
  risk_tags:
  - DIFY_axis_conflict
  readiness_required_false: true
- source_gap_id: SG-005
  gap_type: missing_source
  title: blocked-to-gap 再进入最小字段模板缺失
  affected_canonical_clusters:
  - mkc_004
  seed_origin:
  - W1
  missing_artifact: reentry prerequisite template
  next_source_needed: reentry contract
  risk_tags:
  - decision_required_likelihood_high
  readiness_required_false: true
- source_gap_id: SG-006
  gap_type: missing_source
  title: 企业叙事公开来源类别与 proof-slot 托底样本不足
  affected_canonical_clusters:
  - mkc_007
  - mkc_008
  - mkc_009
  seed_origin:
  - W2
  missing_artifact: public-safe narrative source class examples
  next_source_needed: enterprise narrative intake source taxonomy
  risk_tags:
  - missing_evidence
  - unsupported_hard_claim
  readiness_required_false: true
- source_gap_id: SG-007
  gap_type: missing_source
  title: 跨形态最小 narrative asset unit 字段不足
  affected_canonical_clusters:
  - mkc_012
  seed_origin:
  - W2
  missing_artifact: cross-format asset unit schema
  next_source_needed: later intake asset unit contract
  risk_tags:
  - DIFY_axis_conflict
  readiness_required_false: true
- source_gap_id: SG-008
  gap_type: missing_source
  title: role naming / authorization trigger 词表缺失
  affected_canonical_clusters:
  - mkc_013
  - mkc_019
  - mkc_037
  seed_origin:
  - W3
  - W5
  missing_artifact: shared role and authorization vocabulary
  next_source_needed: generic role lexicon and escalation trigger list
  risk_tags:
  - owner_unclear
  - real_person_risk
  readiness_required_false: true
- source_gap_id: SG-009
  gap_type: missing_source
  title: 通用服装品类/属性/材料/版型术语来源样本不足
  affected_canonical_clusters:
  - mkc_020
  - mkc_022
  - mkc_023
  - mkc_024
  seed_origin:
  - W4
  missing_artifact: apparel terminology anchor set
  next_source_needed: general apparel reference set
  risk_tags:
  - missing_evidence
  readiness_required_false: true
- source_gap_id: SG-010
  gap_type: missing_source
  title: 观察词—关系词—结果词转换准则与高风险词表不足
  affected_canonical_clusters:
  - mkc_021
  - mkc_026
  - mkc_027
  - mkc_044
  seed_origin:
  - W4
  - W6
  missing_artifact: claim risk lexicon
  next_source_needed: claim phrase ladder and rewrite rules
  risk_tags:
  - unsupported_hard_claim
  - missing_evidence
  readiness_required_false: true
- source_gap_id: SG-011
  gap_type: missing_source
  title: 品质观察项到 proof-type 的映射样本不足
  affected_canonical_clusters:
  - mkc_025
  - mkc_028
  - mkc_029
  seed_origin:
  - W4
  missing_artifact: quality observation to proof-type map
  next_source_needed: quality evidence mapping examples
  risk_tags:
  - quality_claim_risk
  - missing_evidence
  readiness_required_false: true
- source_gap_id: SG-012
  gap_type: missing_source
  title: 通用陈列区位、Look 拆解、镜头锚点共识来源不足
  affected_canonical_clusters:
  - mkc_030
  - mkc_031
  - mkc_032
  seed_origin:
  - W5
  missing_artifact: display observation lexicon
  next_source_needed: general display/look observation references
  risk_tags:
  - A2_full_display_system_overreach
  readiness_required_false: true
- source_gap_id: SG-013
  gap_type: missing_source
  title: 门店日常动作切片与动作转内容单元来源不足
  affected_canonical_clusters:
  - mkc_033
  - mkc_034
  - mkc_036
  seed_origin:
  - W5
  missing_artifact: store action slice and translation source set
  next_source_needed: general retail action/content method sources
  risk_tags:
  - store_risk
  - missing_evidence
  readiness_required_false: true
- source_gap_id: SG-014
  gap_type: missing_source
  title: 通用零售授权复核链条来源不一致
  affected_canonical_clusters:
  - mkc_037
  - mkc_038
  seed_origin:
  - W5
  missing_artifact: retail authorization/review generic references
  next_source_needed: public-safe retail authorization method sources
  risk_tags:
  - owner_unclear
  - real_store_risk
  readiness_required_false: true
- source_gap_id: SG-015
  gap_type: missing_source
  title: 产品生命周期抽象阶段与非实例经营状态的安全桥接来源不足
  affected_canonical_clusters:
  - mkc_041
  seed_origin:
  - W6
  missing_artifact: abstract lifecycle stage bridge
  next_source_needed: lifecycle method references without instance operations
  risk_tags:
  - missing_evidence
  - operational_fact_risk
  readiness_required_false: true
- source_gap_id: SG-016
  gap_type: missing_source
  title: 组货角色/渠道边界与产品-display 关系的通用化来源不足
  affected_canonical_clusters:
  - mkc_042
  - mkc_045
  - mkc_046
  seed_origin:
  - W6
  missing_artifact: generalized assortment-display relation references
  next_source_needed: non-instance product role relation sources
  risk_tags:
  - A2_full_display_system_overreach
  - missing_evidence
  readiness_required_false: true
readiness_required_false: true
--- FILE: merge_report.md
# merge_report

## scope_lock

本次 W7 仅对已上传的 W1-W6 研究地图做 normalization、dedupe、cluster ownership arbitration、batch alignment、schema rewrite、source_gap / decision ledger extraction 与 Master Knowledge Map 编译；未新增行业知识，且保持 general_only 与 readiness 全 false 边界。fileciteturn0file1 fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

## input_validation

已按文件内容识别出 W1=P0-00、W2=P0-01、W3=P0-02、W4=P0-03、W5=P0-04、W6=P0-05；六份地图均处于 research_planning_only / general-only 约束下。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

六份地图均声明 4 张 research subcard；W7 校验结果为 24/24 子卡存在，且未发现 P0-00 之外的新能力组声明。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

源 cluster 共 58 个，W7 归并为 46 个 canonical cluster；所有保留 batch_ref 均在 batch_001 至 batch_014 范围内；所有源文件 readiness 仍保持 false。前述 46 个 canonical cluster 只是集成层 registry，并非 CandidatePack、KE、RAG、DIFY、Serving 或 production-ready 知识。fileciteturn0file1 fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

## normalization_and_schema_rewrite

W7 统一改写了 raw cluster_id 命名风格，取消 W2/W5 前缀式 raw id 作为最终主键，改为稳定的 `mkc_001` 至 `mkc_046`；raw ids 仅保留在 `source_cluster_ids`。同时，batch_refs 被统一改写为扁平 allowed-batch 集合，mixed list/dict 形态已消除。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

W4 原始文件存在 forward alias / anchor 依赖；W7 已移除所有 YAML anchor / alias，不把该结构带入最终输出。W1 则存在 subcard 层 batch 覆盖被压缩为 batch_014 的现象，W7 未擅自发明 authority correction，而是把该冲突保留进 `unresolved_decision_ledger.yaml`。fileciteturn0file5 fileciteturn0file2

## dedupe_and_ownership

本轮明确执行了三类合并。第一类是同一 P0 内的父子重叠或同义重叠，例如 W1 的 exception dispatch 与 blocked-to-gap reentry、W2 的 proof-slot 与 value translation、W3 的 authorization surface 与人物故事红线、W5 的 action-to-content 与 demo triptych、以及 P0-03 的 quality proof-type 与 certification routing。第二类是共享结构但 owner 不变的收敛，例如 narrative anchor、filmability、display visual anchor 只共享 vocabulary，不共享 capability ownership。第三类是冲突保留型去重，即把可共享但不可完全合并的项写入 conflict_notes 与 unresolved decisions，而不是静默覆盖。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

owner arbitration 的原则是：控制面与 strictest-wins 归 P0-00；enterprise narrative framing 归 P0-01；role voice / org perspective / generic authorization 归 P0-02；apparel/material/fit/quality claim boundary 归 P0-03；display/store-daily/SOP/contentization 归 P0-04；product-role narrative、CTA boundary、scene-fit、assortment relation 与 product-display relation 归 P0-05。对 proof-slot、color-story、authorization、precheck-routing、A2 support-only 边界等争议点，W7 采取“owner 固定 + shared_reason + conflict_notes + unresolved decision”策略，而不是静默抢占主权。fileciteturn0file1 fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

## ledger_extraction

`source_gap_seed_ledger.yaml` 已抽出 16 个 gap seed，覆盖控制面字典缺失、claim taxonomy 缺失、proof-slot source class 不足、role authorization vocabulary 缺失、服装术语来源不足、claim 风险词表不足、quality observation to proof-type mapping 不足、display / store-daily / retail authorization 通用来源不足，以及 lifecycle / assortment / product-display relation 的安全泛化来源不足。fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

`unresolved_decision_ledger.yaml` 已抽出 12 个 decision 项，显式覆盖 owner unclear、duplicate requiring merge、batch alignment conflict、P0-00 domain leakage、A2 full display-system overreach、CSO axis conflict、DIFY axis conflict，以及 CTA vocabulary、lifecycle granularity、role authorization split 等未决口径。相关条目全部停留在 W7 ledger，不被冒充为已裁定事实。fileciteturn0file1 fileciteturn0file2turn0file3turn0file4turn0file5turn0file6turn0file0

## output_inventory

本次单回答输出 9 个逻辑文件内容：shared registry、ownership matrix、capability crosswalk、batch crosswalk、master map、generation assignment plan、unresolved decision ledger、source gap seed ledger、merge report。所有输出均保持 research-only、readiness false、non-production、non-instance-fact。fileciteturn0file1