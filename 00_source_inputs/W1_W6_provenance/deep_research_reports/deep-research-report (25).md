map_id: W1_P0_00_control_plane_consumption_map
map_version: "0.1"
output_file: W1_P0_00_control_plane_consumption_map.yaml
cell_id: W1
prompt_id: WEB-DEEP-RESEARCH-W1-P0-00-CONTROL-PLANE-MAP-001
status: research_planning_only
not_formal_capability_card: true
not_registry: true
not_candidatepack: true
not_KE: true

source_inputs:
  pack_id: web_gpt_upload_pack_v0_1
  authority_rule:
    file_name: 09_upload_pack_manifest.json
    note: 上传包文件清单以 manifest 为权威；optional reference 仅可作结构参考，不得覆盖 charter、schema、matrix 或当前任务边界。
    citation: "fileciteturn0file1"
  mandatory_files_used:
    - file_name: 01_research_charter_and_redlines.md
      role: 全局范围、P0-00 控制面边界、general_only 红线
      citation: "fileciteturn0file2"
    - file_name: 02_p0_capability_and_subcards.yaml
      role: P0-00 四张 research subcard 识别与覆盖
      citation: internal_upload_file_only
    - file_name: 03_batch_allocation_matrix.csv
      role: batch 约束与 batch_014 边界
      citation: internal_upload_file_only
    - file_name: 04_research_map_output_schema.yaml
      role: research map 输出结构思路与 readiness false 约束
      citation: internal_upload_file_only
    - file_name: 05_source_claim_evidence_policy.md
      role: claim/evidence/source_gap/decision_required/founder_review 路由边界
      citation: "fileciteturn0file3"
    - file_name: 06_candidatepack_and_readiness_policy.md
      role: CandidatePack 与 KE/Serving/RAG/DIFY/readiness 禁区
      citation: "fileciteturn0file4"
    - file_name: 07_dq_anti_homogeneity_policy.md
      role: DQ、反空洞、反模板、锚点与可执行影响约束
      citation: "fileciteturn0file5"
    - file_name: 08_optional_reference_digest.md
      role: 仅作格式参考，不视为仓内 canonical truth
      citation: "fileciteturn0file0"

p0_scope:
  selected_scope:
    - P0-00
  capability_group_id: P0-00
  capability_group_name: 低数据品牌资产总控编排 / 控制面消费地图
  knowledge_mode: general_only
  scope_guardrails:
    - 仅研究 route / degradation / checker / asset binding / slot intake
    - 不输出普通服装行业知识
    - 不将 P0-00 扩写为面料、产品、陈列、品牌故事等领域知识
    - 不新增 P0 之外能力组
    - 不新增 batch_014 之外的 batch
    - 不生成任何 production-ready 知识
  full_part_a_claim: false
  basis_citations:
    - "fileciteturn0file2"
    - "fileciteturn0file3"
    - "fileciteturn0file4"

research_subcard_refs:
  - research_card_id: P0-00-RS01
    theme: control-plane route conditions
    status: research_planning_only
    batch_refs:
      - batch_014
    required_knowledge_clusters:
      - P0-00-RS01-C01
      - P0-00-RS01-C02
  - research_card_id: P0-00-RS02
    theme: evidence and claim routing
    status: research_planning_only
    batch_refs:
      - batch_014
    required_knowledge_clusters:
      - P0-00-RS02-C01
      - P0-00-RS02-C02
  - research_card_id: P0-00-RS03
    theme: capability composition and conflict
    status: research_planning_only
    batch_refs:
      - batch_014
    required_knowledge_clusters:
      - P0-00-RS03-C01
      - P0-00-RS03-C02
  - research_card_id: P0-00-RS04
    theme: review-only downgrade control
    status: research_planning_only
    batch_refs:
      - batch_014
    required_knowledge_clusters:
      - P0-00-RS04-C01
      - P0-00-RS04-C02

required_knowledge_clusters:
  - cluster_id: P0-00-RS01-C01
    cluster_name: 低数据入口槽位摄取契约
    p0_group: P0-00
    research_card_id: P0-00-RS01
    domain_module: control_plane.slot_intake
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - boundary_rule
      - routing_hint
    object_type: CapabilityResearchCluster
    definition: 规定控制面在低数据场景下允许消费的最小输入槽位集合，以及槽位缺失时触发的检查与降级入口；该契约只描述控制面可消费结构，不描述领域内容本体。
    why_required_for_capability: 若无最小槽位契约，控制面无法稳定判断是继续路由、降级、阻断，还是转 source_gap / decision_required / founder_review。
    applies_when:
      - 请求进入 P0-00 控制面且来源信息稀疏
      - 需要决定 route、degradation 或 checker 调用顺序
      - 需要判断是否允许后续 asset binding
    does_not_apply_when:
      - 任务要求落地 CandidatePack、KE、RAG、DIFY、Serving 或可发布正文
      - 任务试图引入真实品牌、SKU、门店、人物、顾客反馈事实
      - 任务试图把槽位定义扩写为普通服装类目知识
    counter_boundary: 此 cluster 不是服装品类 schema，不是陈列系统本体，不是品牌故事结构，不是运行时实现文档。
    output_influence:
      - 约束可被控制面读取的输入轴
      - 为 route checker 提供统一入口
      - 为 fallback 与 blocking 条件提供可判定字段
      - 为 source_gap_seed 提供最小缺口枚举面
    source_dependency: 依赖 charter 的 P0-00 控制面边界、general_only 边界与 research-only 输出限制；不依赖任何真实品牌实例源。
    evidence_need: 仅需为槽位中的 claim_risk、source_presence、instance_fact_presence 等判定项打上 evidence_need 标签；不得把 GPT 草稿当作 source anchor。
    risk_flags:
      - p0_00_domain_leak
      - slot_overexpansion
      - implicit_instance_fact_intake
      - runtime_artifact_drift
    expected_body_topics:
      - 最小入口槽位族
      - 槽位完备度定义
      - 槽位缺失分层
      - 入口 checker 触发顺序
      - 槽位与路由阶梯关系
      - 槽位与 asset binding 前置关系
    required_relations:
      - slot_completeness -> route_ladder
      - instance_fact_presence -> blocking_or_gap
      - claim_risk_level -> evidence_checker
      - requested_asset_type -> asset_binding_gate
      - review_sensitivity -> founder_review_gate
    risk_boundaries:
      - 不允许把真实品牌字段设计成通用槽位
      - 不允许把业务运行状态写成已知事实
      - 不允许把控制面槽位扩张为全域 ontology
    evidence_classes:
      - structure_only_slot_definition
      - source_anchor_presence_check
      - evidence_need_label_only
      - instance_fact_prohibited
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-01
      - P0-04
      - P0-05
    batch_refs:
      - batch_014
    candidate_output_effect: 使后续研究产物只能以控制面可消费槽位进入，不得越权直接形成领域正文或实例知识。
    forbidden_knowledge_leakage:
      - 品牌故事事实
      - 产品属性事实
      - 门店运营事实
      - 人物与顾客事实
      - 完整陈列系统 ontology
    source_gap_likelihood: medium
    duplicate_check_key: p0_00.slot_intake.minimal_contract.v1
    body_structure_consistency_note: 以“槽位定义 -> 完备度 -> checker -> route -> fallback -> block”顺序组织，避免空泛原则句。
    basis_citations:
      - "fileciteturn0file2"
      - "fileciteturn0file3"
      - "fileciteturn0file5"

  - cluster_id: P0-00-RS01-C02
    cluster_name: 路由条件阶梯与降级触发面
    p0_group: P0-00
    research_card_id: P0-00-RS01
    domain_module: control_plane.route_degradation
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - routing_hint
      - relation_hint
    object_type: CapabilityResearchCluster
    definition: 定义从继续处理、软降级、硬降级、转 source_gap、转 decision_required、转 founder_review、转 excluded 的条件阶梯；仅描述控制面判定，不描述执行系统实现。
    why_required_for_capability: P0-00 的核心价值是“如何选择、降级、组合、阻断”，没有阶梯就无法形成可审查的控制面消费地图。
    applies_when:
      - 入口槽位不完整
      - claim 级别高于 source/evidence 可支持范围
      - asset binding 前置条件不满足
      - 存在 scope 或 ontology 冲突
    does_not_apply_when:
      - 需要输出直接可服务内容
      - 任务要求写真实品牌事实或实例验证结论
      - 任务试图绕过 review-only 边界
    counter_boundary: 此 cluster 不是工作流引擎配置，不是 runtime route mutation，不是 readiness 升级规则。
    output_influence:
      - 决定 checker 结果如何映射为 route
      - 决定弱证据请求的降级去向
      - 决定何时直接阻断而非继续处理
      - 决定何时转 founder_review
    source_dependency: 依赖 P0-00 控制面边界、source/evidence 路由政策、CandidatePack 与 readiness 禁区；不依赖实例源。
    evidence_need: 对任何带有 hard claim、performance claim、body-effect claim、quality claim 的输入，必须要求显式 evidence_need 标签；若缺失则不得保持主路线。
    risk_flags:
      - hidden_readiness_escalation
      - unsupported_claim_carryover
      - downgrade_without_trace
      - founder_review_undertrigger
    expected_body_topics:
      - route 梯级定义
      - degradation 类型
      - soft fallback 与 hard block 区分
      - review-only 与 source-gap 分流
      - strictest-wins 的前置触发点
    required_relations:
      - checker_result -> route_decision
      - evidence_need_missing -> source_gap
      - ontology_conflict -> decision_required
      - risk_sensitive_override -> founder_review
      - forbidden_output_request -> excluded
    risk_boundaries:
      - 不允许从 research map 推导 runtime 配置
      - 不允许把降级描述成产线可执行发布策略
      - 不允许把“coverage budget”当作 acceptance KPI
    evidence_classes:
      - route_trigger_definition
      - evidence_missing_to_gap_rule
      - conflict_to_decision_rule
      - risk_sensitive_to_founder_review_rule
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-01
      - P0-03
      - P0-04
      - P0-05
    batch_refs:
      - batch_014
    candidate_output_effect: 让任何候选研究片段都必须先通过控制面路由阶梯判断，不能直接被误读为可用知识。
    forbidden_knowledge_leakage:
      - 真实 claim 结论
      - 直接发布逻辑
      - route mutation 文件
      - 运行时注册信息
    source_gap_likelihood: medium
    duplicate_check_key: p0_00.route_ladder.degradation.v1
    body_structure_consistency_note: 必须显式区分“继续、降级、阻断、转 gap、转 decision、转 founder review、排除”，避免混用。
    basis_citations:
      - "fileciteturn0file2"
      - "fileciteturn0file3"
      - "fileciteturn0file4"

  - cluster_id: P0-00-RS02-C01
    cluster_name: claim 强度分级与证据边界检查器
    p0_group: P0-00
    research_card_id: P0-00-RS02
    domain_module: control_plane.claim_checker
    knowledge_type: evidence_requirement
    knowledge_types:
      - evidence_requirement
      - boundary_rule
      - routing_hint
    object_type: CapabilityResearchCluster
    definition: 建立控制面可使用的 claim 强度分级，并把每一级映射到 source support、evidence support、禁止处理或转 gap 的边界；该检查器只做路由判定，不形成 claim 本身。
    why_required_for_capability: P0-00 必须决定何种 claim 可继续作为一般方法研究，何种 claim 必须转 source_gap，何种 claim 必须被阻断。
    applies_when:
      - 输入包含 hard claim
      - 输入暗含 fabric、fit、body-effect、quality、durability、comfort、performance 等高风险含义
      - 需要将“方法性描述”与“事实性断言”分离
    does_not_apply_when:
      - 输入仅为控制面结构问题，且不含 claim 性表达
      - 输入已明确是排除项或实例事实，不进入一般 research cluster
    counter_boundary: 此 cluster 不是证据仓、不是 claim 验证报告、不是实例事实审批单。
    output_influence:
      - 决定是否可保留为 general_method
      - 决定是否必须显式 evidence_need
      - 决定是否直接转 source_gap 或 excluded
      - 为 founder_review 提供高风险升级触发
    source_dependency: 直接依赖 claim/evidence policy、charter 中 hard claim 与 evidence 要求、DQ 的 claim/evidence 分离要求。
    evidence_need: 任何高风险 claim 都需要显式 evidence_need；任何缺失 source support 的 hard claim 只能转 source_gap 或 excluded，不得进入接受性 clusters。
    risk_flags:
      - unsupported_hard_claim
      - evidence_label_omission
      - method_fact_blur
      - instance_fact_smuggling
    expected_body_topics:
      - claim 强度分层
      - 方法陈述与事实断言切分
      - source support 与 evidence support 区分
      - GPT 草稿不可作 source anchor
      - unsupported claim 的路由去向
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
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-03
      - P0-05
    batch_refs:
      - batch_014
    candidate_output_effect: 防止控制面把 claim 类片段误消化为一般知识，确保高风险断言都被分流到正确账本。
    forbidden_knowledge_leakage:
      - 实际产品功效结论
      - 身材效果结论
      - 质量耐久结论
      - 真实顾客反馈
    source_gap_likelihood: high
    duplicate_check_key: p0_00.claim_strength.evidence_boundary.v1
    body_structure_consistency_note: 先写 claim 分级，再写 evidence gate，再写去向；不得直接给“可接受 claim 清单”。
    basis_citations:
      - "fileciteturn0file2"
      - "fileciteturn0file3"
      - "fileciteturn0file5"

  - cluster_id: P0-00-RS02-C02
    cluster_name: source_gap / decision_required / founder_review 分发表
    p0_group: P0-00
    research_card_id: P0-00-RS02
    domain_module: control_plane.exception_routing
    knowledge_type: routing_hint
    knowledge_types:
      - routing_hint
      - boundary_rule
      - decision_required_candidate
    object_type: CapabilityResearchCluster
    definition: 描述控制面在发现证据缺失、建模冲突、实例事实、边界越权、风险敏感请求时，如何在 source_gap、decision_required、founder_review、excluded 之间分发。
    why_required_for_capability: 若无异常分发表，控制面会把不同性质的问题混为一类，导致后续 intake 无法区分“缺 source”“需决策”“需创始人审阅”“应直接排除”。
    applies_when:
      - hard claim 缺少 source/evidence
      - 出现 P0-00 控制面泄漏到普通领域知识
      - 出现 full display-system overreach
      - 出现 CSO/DIFY/ontology ownership 不清
      - 出现风险敏感要求
    does_not_apply_when:
      - 输入已被明确排除且无后续讨论必要
      - 仅是内部措辞润色，不涉及路由性质判断
    counter_boundary: 此 cluster 不是审批流程图，不是组织权限表，不是仓库路线状态写入文件。
    output_influence:
      - 提供异常类型与去向的一致命名
      - 降低 source_gap 与 decision_required 混淆
      - 为 founder_review 增加单独门槛
      - 为后续 intake 预留清晰账本
    source_dependency: 依赖 source/evidence policy、charter 中 risk-sensitive 路由原则、readiness policy 的下游隔离边界。
    evidence_need: 对“为什么被分发到某账本”需要最小解释标签，但不得写成已完成审批事实。
    risk_flags:
      - gap_decision_confusion
      - founder_review_overuse
      - excluded_underuse
      - hidden_scope_expansion
    expected_body_topics:
      - source_gap 触发模式
      - decision_required 触发模式
      - founder_review 触发模式
      - excluded 触发模式
      - 触发优先级
      - 多触发并存时 strictest-wins
    required_relations:
      - missing_source -> source_gap
      - modeling_conflict -> decision_required
      - risk_sensitive_item -> founder_review
      - forbidden_output_request -> excluded
      - multiple_trigger_collision -> strictest_wins
    risk_boundaries:
      - 不允许把 founder_review 当作通用兜底
      - 不允许把 excluded 伪装成 source_gap
      - 不允许在 map 中声明任何事项已通过 review
    evidence_classes:
      - routing_reason_label
      - missing_source_marker
      - modeling_conflict_marker
      - founder_review_risk_marker
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-01
      - P0-02
      - P0-03
      - P0-04
      - P0-05
    batch_refs:
      - batch_014
    candidate_output_effect: 将异常研究项分发到后续可验证的不同账本，避免控制面地图把问题隐藏在模糊说明里。
    forbidden_knowledge_leakage:
      - 审批已完成的表述
      - 实时 route 状态
      - 组织权限与私人流程信息
    source_gap_likelihood: high
    duplicate_check_key: p0_00.exception_dispatch.v1
    body_structure_consistency_note: 必须先列触发条件，再列去向，再列优先级，不得只给抽象定义。
    basis_citations:
      - "fileciteturn0file2"
      - "fileciteturn0file3"
      - "fileciteturn0file4"

  - cluster_id: P0-00-RS03-C01
    cluster_name: 能力组合优先级与 strictest-wins 冲突格
    p0_group: P0-00
    research_card_id: P0-00-RS03
    domain_module: control_plane.capability_composition
    knowledge_type: relation_hint
    knowledge_types:
      - relation_hint
      - boundary_rule
      - routing_hint
    object_type: CapabilityResearchCluster
    definition: 定义 P0-00 在与其他 P0 capability cards 共现时，如何用 strictest-wins、越权阻断、边界保留与共享 cluster 方式处理组合与冲突。
    why_required_for_capability: 控制面本质上处理“组合、冲突、阻断”；若没有组合优先级，route 与 degradation 无法稳定落地为研究地图。
    applies_when:
      - 一个请求同时触及多个 P0 能力面
      - route 需要判断谁拥有解释权
      - shared cluster 需要去重或拆分
    does_not_apply_when:
      - 请求完全停留在单一控制面结构问题
      - 任务试图把 P0-00 抬升为全局领域 ontology
    counter_boundary: 此 cluster 不是能力注册表，不是 capability card 正式定义，不是新的 scenario family。
    output_influence:
      - 决定 shared_with_capability_cards 的使用原则
      - 决定何时保留 P0-00 为控制面节点
      - 决定何时必须拆分并转 decision_required
      - 决定 merge suggestion 的边界
    source_dependency: 依赖 charter 中 scenario family 边界、P0-00 control-plane-only policy、optional reference 不得覆盖 canonical truth 的规则。
    evidence_need: 不要求实例证据，但要求冲突说明标签与 ownership 不清标签，以支持后续 decision_required。
    risk_flags:
      - new_axis_invention
      - full_display_system_overreach
      - ownership_blur
      - merge_without_boundary
    expected_body_topics:
      - strictest-wins 原则
      - control-plane 保留条件
      - shared cluster 拆分条件
      - 新轴新增禁令
      - 支持性上下文与完整系统边界
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
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-01
      - P0-04
      - P0-05
    batch_refs:
      - batch_014
    candidate_output_effect: 为多能力交叉请求建立统一冲突裁决面，防止研究产物在能力归属上漂移。
    forbidden_knowledge_leakage:
      - 正式能力注册信息
      - 新增场景族
      - 完整 display-system ontology
    source_gap_likelihood: medium
    duplicate_check_key: p0_00.capability_composition.strictest_wins.v1
    body_structure_consistency_note: 先写组合场景，再写冲突类型，再写 strictest-wins，再写决策去向。
    basis_citations:
      - "fileciteturn0file0"
      - "fileciteturn0file2"
      - "fileciteturn0file3"

  - cluster_id: P0-00-RS03-C02
    cluster_name: 执行资产绑定兼容矩阵
    p0_group: P0-00
    research_card_id: P0-00-RS03
    domain_module: control_plane.asset_binding
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - relation_hint
      - routing_hint
    object_type: CapabilityResearchCluster
    definition: 定义研究阶段允许绑定的执行资产类型、每类资产的前置槽位、禁止绑定条件与冲突后的阻断规则；资产仅限 research-only stub，不含任何 production runtime artifact。
    why_required_for_capability: P0-00 需要决定不同 route 最终可组合到哪些研究资产占位体，否则控制面无法体现“组合”和“阻断”的消费地图价值。
    applies_when:
      - 入口已通过基本槽位检查
      - 需要把请求映射到研究型执行资产
      - 存在多资产并发需求或绑定冲突
    does_not_apply_when:
      - 请求要求实体化 CandidatePack、KE、RAG、DIFY、Serving、approved passage
      - 请求要求绑定真实品牌实例材料
      - 请求要求直接生成最终工作流
    counter_boundary: 此 cluster 不是 runtime asset registry，不是工程 binding spec，不是下游发布映射表。
    output_influence:
      - 决定 research-only asset stub 的可绑定性
      - 决定 slot completeness 对 asset binding 的约束
      - 决定多资产冲突时的阻断与拆分
      - 为 required_execution_asset_types 提供结构依据
    source_dependency: 依赖 schema 的 forbidden object types、readiness false 边界、charter 的 forbidden outputs。
    evidence_need: 若绑定对象涉及 claim routing 或 review-only 标志，则需保留 evidence_need 与 route reason 标签；否则仅纳入结构性绑定说明。
    risk_flags:
      - production_asset_leak
      - hidden_dify_generation
      - unsupported_multi_bind
      - asset_scope_confusion
    expected_body_topics:
      - 研究型资产类型
      - 资产前置槽位
      - 资产绑定排他条件
      - 多资产冲突处理
      - 绑定失败后的去向
    required_relations:
      - route_decision -> allowed_asset_stub
      - slot_completeness -> bindability
      - review_only_label -> non_production_asset_only
      - conflict_pair -> block_or_split
    risk_boundaries:
      - 不允许把 stub 资产描述成可上线对象
      - 不允许把 output schema 禁止对象重新包装后输出
      - 不允许把 source_gap 或 decision_required 直接绑定成下游可消费成品
    evidence_classes:
      - asset_bindability_rule
      - forbidden_object_type_guard
      - non_production_binding_label
      - conflict_split_marker
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-01
      - P0-02
      - P0-03
      - P0-04
      - P0-05
    batch_refs:
      - batch_014
    candidate_output_effect: 把研究输出限制在控制面允许组合的 research-only 资产占位体，避免越权产生成品化知识。
    forbidden_knowledge_leakage:
      - CandidatePack
      - KEItem
      - ApprovedPassageText
      - RAGContextBundle
      - DIFYWorkflow
      - ServingProjectionRecord
    source_gap_likelihood: medium
    duplicate_check_key: p0_00.asset_binding.compatibility_matrix.v1
    body_structure_consistency_note: 应以“资产类型 -> 前置条件 -> 禁止绑定 -> 冲突去向”的固定骨架表述。
    basis_citations:
      - "fileciteturn0file2"
      - "fileciteturn0file4"

  - cluster_id: P0-00-RS04-C01
    cluster_name: review-only 降级标签与非生产封印
    p0_group: P0-00
    research_card_id: P0-00-RS04
    domain_module: control_plane.review_only
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - routing_hint
      - exclusion_note
    object_type: CapabilityResearchCluster
    definition: 定义何种条件下输出只能带 review-only 标签存在，以及 review-only 与 readiness false、non-production boundary、blocked-to-gap 的关系。
    why_required_for_capability: P0-00 必须能把不可直接消费但仍有研究价值的内容留在 review-only 区域，避免被误判为可下游使用。
    applies_when:
      - 存在未解冲突但不宜直接排除
      - 存在高风险控制面越权可能
      - 存在待创始人审阅的边界敏感项
    does_not_apply_when:
      - 输入已满足 excluded 条件
      - 输入缺 source 且应直接进入 source_gap
      - 输入要求任何 readiness 启用
    counter_boundary: 此 cluster 不是质量验收流程，不是 readiness 开关，不是生产白名单。
    output_influence:
      - 给异常但可保留的问题加 review-only 封印
      - 阻断其进入下游 KE/Serving/RAG/DIFY 讨论
      - 为 blocked-to-gap 提供中间态语义
    source_dependency: 依赖 readiness policy、source/evidence policy 中 non-production 边界、charter 的 all readiness disabled。
    evidence_need: 需要最小化记录“为何 review-only”的原因标签；不得表述为已完成审查。
    risk_flags:
      - review_only_as_soft_ready
      - hidden_generation_eligibility
      - non_production_boundary_blur
      - gap_review_misroute
    expected_body_topics:
      - review-only 触发条件
      - review-only 与 source_gap 的区别
      - review-only 与 founder_review 的衔接
      - readiness false 封印
      - 非生产输出约束
    required_relations:
      - unresolved_conflict -> review_only
      - review_only -> no_downstream_ready
      - founder_review_pending -> review_only_hold
      - hard_missing_source -> prefer_source_gap
    risk_boundaries:
      - 不允许把 review-only 翻译成“半可用”
      - 不允许把 review-only 视为后续下游默认可读
      - 不允许在 review-only 上增加任何 readiness true
    evidence_classes:
      - review_reason_label
      - non_production_seal
      - pending_review_marker
      - readiness_false_guard
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-01
      - P0-02
      - P0-03
      - P0-04
      - P0-05
    batch_refs:
      - batch_014
    candidate_output_effect: 为高风险未决研究信息提供可保留但不可消费的封装面，降低误下游风险。
    forbidden_knowledge_leakage:
      - generation_allowed: true
      - production_ready: true
      - release_ready: true
      - 任何可直接部署表述
    source_gap_likelihood: medium
    duplicate_check_key: p0_00.review_only.non_production_seal.v1
    body_structure_consistency_note: 必须同时写出触发、封印、禁止下游、退出条件，避免只写“待审”。
    basis_citations:
      - "fileciteturn0file2"
      - "fileciteturn0file3"
      - "fileciteturn0file4"

  - cluster_id: P0-00-RS04-C02
    cluster_name: blocked-to-gap 转写与再进入条件
    p0_group: P0-00
    research_card_id: P0-00-RS04
    domain_module: control_plane.reentry_control
    knowledge_type: source_gap_candidate
    knowledge_types:
      - source_gap_candidate
      - routing_hint
      - decision_required_candidate
    object_type: CapabilityResearchCluster
    definition: 规定被阻断的研究项何时应转写为 source_gap、何时保持 excluded、何时升级为 decision_required，以及满足何种补充条件后才可重新进入控制面判定。
    why_required_for_capability: 若无 blocked-to-gap 与再进入条件，控制面只能“挡住”，不能形成可追踪的后续处理地图。
    applies_when:
      - 初始请求被阻断
      - 被阻断原因可通过补 source、补决策、补边界说明而解除
      - 需要保留再进入前置条件
    does_not_apply_when:
      - 被阻断原因属于永久禁止项
      - 输入包含真实实例事实且当前包不允许任何实例路径
      - 输入要求跳过补证据直接恢复主路线
    counter_boundary: 此 cluster 不是 intake 执行 SOP，不是回流系统，不是生产排队表。
    output_influence:
      - 让阻断结果具备可追踪后续条件
      - 决定 source_gap_seed 的构成方式
      - 决定 decision_required 与 source_gap 的再进入前置差异
    source_dependency: 依赖 source/evidence policy 的 routing summary、readiness policy 的四门隔离、DQ 的锚点缺失即标 gap 原则。
    evidence_need: 再进入只能声明“需要什么”，不得声明“已经补齐”；缺失 source/evidence 的项仍保持 gap。
    risk_flags:
      - premature_reentry
      - gap_without_condition
      - excluded_softening
      - undocumented_retry_path
    expected_body_topics:
      - 阻断原因分类
      - blocked-to-gap 转写条件
      - blocked-to-decision 转写条件
      - 永久 excluded 保持条件
      - 再进入最小前置
      - retry 不等于 readiness
    required_relations:
      - block_reason -> reentry_channel
      - missing_source -> source_gap_seed
      - missing_ownership_decision -> decision_required_seed
      - permanent_forbidden -> excluded
      - reentry_prerequisite_met -> control_plane_recheck
    risk_boundaries:
      - 不允许把“可再进入”解释成“可直接下游”
      - 不允许用模糊语句替代最小前置条件
      - 不允许续写任何实例事实来解除阻断
    evidence_classes:
      - reentry_prerequisite_label
      - missing_source_seed
      - missing_decision_seed
      - permanent_exclusion_marker
    source_research_priority: high
    shared_with_capability_cards:
      - P0-00
      - P0-01
      - P0-02
      - P0-03
      - P0-04
      - P0-05
    batch_refs:
      - batch_014
    candidate_output_effect: 使控制面地图能表达“阻断后的下一步需要什么”，而不是仅给出不可操作的拒绝结论。
    forbidden_knowledge_leakage:
      - 已补齐 source 的假定
      - 已解决冲突的假定
      - 实例路径的越权恢复
    source_gap_likelihood: high
    duplicate_check_key: p0_00.blocked_to_gap.reentry.v1
    body_structure_consistency_note: 必须显式写出“阻断原因 -> 去向 -> 再进入条件”，避免把 gap 与 retry 写成口头建议。
    basis_citations:
      - "fileciteturn0file2"
      - "fileciteturn0file3"
      - "fileciteturn0file4"
      - "fileciteturn0file5"

relation_hints:
  - relation_id: RH-001
    from_cluster_id: P0-00-RS01-C01
    relation: gates
    to_cluster_id: P0-00-RS01-C02
    note: 入口槽位完备度先于 route 梯级判断。
  - relation_id: RH-002
    from_cluster_id: P0-00-RS01-C01
    relation: feeds
    to_cluster_id: P0-00-RS02-C01
    note: claim_risk_level、source_presence 等槽位进入证据边界检查器。
  - relation_id: RH-003
    from_cluster_id: P0-00-RS02-C01
    relation: dispatches_to
    to_cluster_id: P0-00-RS02-C02
    note: claim 强度与 evidence_need 结果决定异常分发去向。
  - relation_id: RH-004
    from_cluster_id: P0-00-RS03-C01
    relation: overrides
    to_cluster_id: P0-00-RS01-C02
    note: 多能力冲突场景下由 strictest-wins 覆盖一般 route 梯级。
  - relation_id: RH-005
    from_cluster_id: P0-00-RS03-C02
    relation: requires
    to_cluster_id: P0-00-RS01-C01
    note: asset binding 只能在前置槽位满足后执行。
  - relation_id: RH-006
    from_cluster_id: P0-00-RS03-C02
    relation: constrained_by
    to_cluster_id: P0-00-RS04-C01
    note: review-only 封印会限制可绑定资产仅为 non-production stub。
  - relation_id: RH-007
    from_cluster_id: P0-00-RS04-C01
    relation: hands_off_to
    to_cluster_id: P0-00-RS04-C02
    note: review-only 无法消解缺口时，应转写为 source_gap 或 decision_required。
  - relation_id: RH-008
    from_cluster_id: P0-00-RS02-C02
    relation: escalates_to
    to_cluster_id: P0-00-RS04-C01
    note: 风险敏感且暂不排除的项可先封印为 review-only。
  - relation_id: RH-009
    from_cluster_id: P0-00-RS04-C02
    relation: rechecks_via
    to_cluster_id: P0-00-RS01-C01
    note: 仅在最小再进入前置满足后重新进入控制面检查。
  - relation_id: RH-010
    from_cluster_id: P0-00-RS03-C01
    relation: bounds
    to_cluster_id: P0-00-RS03-C02
    note: asset binding 的兼容性必须受能力归属与冲突裁决束缚。

required_execution_asset_types:
  - asset_type: slot_intake_contract_stub
    purpose: 为低数据请求提供控制面可消费的最小槽位结构
    production_ready: false
  - asset_type: route_condition_matrix_stub
    purpose: 表达 route / downgrade / block / gap / decision / founder_review 的条件格
    production_ready: false
  - asset_type: claim_evidence_checker_stub
    purpose: 表达 claim 强度分级与 evidence need 判定占位
    production_ready: false
  - asset_type: exception_dispatch_ledger_stub
    purpose: 表达 source_gap / decision_required / founder_review / excluded 的分发表
    production_ready: false
  - asset_type: capability_conflict_matrix_stub
    purpose: 表达 strictest-wins 与能力归属冲突处理
    production_ready: false
  - asset_type: asset_binding_matrix_stub
    purpose: 表达研究型资产绑定兼容条件
    production_ready: false
  - asset_type: review_only_label_ledger_stub
    purpose: 表达 review-only 封印与非生产边界
    production_ready: false
  - asset_type: reentry_prerequisite_stub
    purpose: 表达 blocked-to-gap 与控制面再进入前置
    production_ready: false

required_dq_checks:
  - check_id: DQ-P0-00-001
    check_name: no_empty_control_phrase
    rule: 任何 cluster 不得只写“很重要”或“需要路由”，必须包含适用条件、反例边界、输出影响与风险标记。
    citation: "fileciteturn0file5"
  - check_id: DQ-P0-00-002
    check_name: no_template_industry_knowledge
    rule: 任何 cluster 不得退化为普通服装、陈列、品牌故事知识。
    citation: "fileciteturn0file2"
  - check_id: DQ-P0-00-003
    check_name: claim_evidence_separation
    rule: claim、evidence_need、route outcome 必须分写，不能混成一句结论。
    citation: "fileciteturn0file3"
  - check_id: DQ-P0-00-004
    check_name: control_plane_anchor_presence
    rule: 每个 cluster 至少包含一个不可替代的控制面锚点，如 slot、checker、route、degradation、binding、block。
    citation: "fileciteturn0file5"
  - check_id: DQ-P0-00-005
    check_name: no_readiness_leak
    rule: 不得出现任何 readiness true 或任何可生产、可发布、可下游直接消费措辞。
    citation: "fileciteturn0file4"
  - check_id: DQ-P0-00-006
    check_name: no_instance_fact
    rule: 不得出现真实品牌、SKU、门店、人物、顾客反馈或操作事实。
    citation: "fileciteturn0file2"
  - check_id: DQ-P0-00-007
    check_name: batch_scope_lock
    rule: 所有 batch_refs 只能为 batch_014，不得扩写其他 batch。
    citation: internal_upload_file_only
  - check_id: DQ-P0-00-008
    check_name: support_only_guard
    rule: 不得把 support-only 的 display 语境误写成完整显示系统。
    citation: "fileciteturn0file2"

fallback_conditions:
  - condition_id: FB-001
    trigger: 入口槽位不完整但仍可识别控制面意图
    fallback_route: 降级到最小 route_condition_matrix_stub
  - condition_id: FB-002
    trigger: claim 风险存在但 source/evidence 暂缺
    fallback_route: 转 source_gap_seed，保留 evidence_need 标签
  - condition_id: FB-003
    trigger: 多能力组合但 ownership 不清
    fallback_route: 转 decision_required，保留 strictest-wins 冲突说明
  - condition_id: FB-004
    trigger: 风险敏感但尚未满足排除条件
    fallback_route: 转 review-only 封印并等待 founder_review 判断
  - condition_id: FB-005
    trigger: asset binding 条件不满足
    fallback_route: 仅保留绑定前置缺口，不继续绑定
  - condition_id: FB-006
    trigger: 被阻断项具备可补证据或可补决策空间
    fallback_route: blocked-to-gap 或 blocked-to-decision，并记录再进入前置

blocking_conditions:
  - condition_id: BL-001
    trigger: 请求要求 CandidatePack、KE、RAG、DIFY、Serving、approved passage 或其他 production-ready 知识
    block_action: excluded
  - condition_id: BL-002
    trigger: 出现真实品牌、SKU、门店、人物、顾客反馈、授权或运营实例事实
    block_action: excluded_or_source_gap
  - condition_id: BL-003
    trigger: 试图把 P0-00 扩写成普通服装、面料、陈列、品牌故事知识
    block_action: decision_required_or_excluded
  - condition_id: BL-004
    trigger: 试图新增 P0 之外能力组或 batch_014 之外 batch
    block_action: excluded
  - condition_id: BL-005
    trigger: 试图启用任何 readiness true
    block_action: excluded
  - condition_id: BL-006
    trigger: 试图把 A2 support-only 误写成完整陈列系统
    block_action: decision_required_or_excluded
  - condition_id: BL-007
    trigger: 试图将 unsupported hard claim 继续留在主 route
    block_action: source_gap

source_gap_items:
  - gap_id: SG-001
    gap_name: 控制面最小入口槽位字典未在上传包中给出 canonical 字段表
    affects_clusters:
      - P0-00-RS01-C01
    why_gap: 当前上传包提供边界与政策，但未提供最小字段字典。
    next_needed_source: 后续 repository-side intake 中的 canonical slot contract
  - gap_id: SG-002
    gap_name: claim 强度分级的统一命名表未在上传包中穷举
    affects_clusters:
      - P0-00-RS02-C01
    why_gap: 当前上传包给出需重点防护的 claim 类别，但未给出完整分级词表。
    next_needed_source: 后续 claim taxonomy contract
  - gap_id: SG-003
    gap_name: founder_review 触发清单未在上传包中给出穷举列表
    affects_clusters:
      - P0-00-RS02-C02
      - P0-00-RS04-C01
    why_gap: 仅能确定风险敏感项需 founder_review，无法穷举全部触发类。
    next_needed_source: 后续 founder review policy ledger
  - gap_id: SG-004
    gap_name: 研究型执行资产与下游 intake 的绑定白名单未在上传包中给出
    affects_clusters:
      - P0-00-RS03-C02
    why_gap: 当前只能输出 research-only stub，不足以定义正式白名单。
    next_needed_source: repository-side authorized asset binding contract
  - gap_id: SG-005
    gap_name: blocked-to-gap 再进入的最小字段表未在上传包中给出
    affects_clusters:
      - P0-00-RS04-C02
    why_gap: 当前可枚举原则，不能给出官方再进入字段模板。
    next_needed_source: reentry prerequisite contract

decision_required_items:
  - decision_id: DR-001
    decision_name: content_x_display 协调视图在控制面上是否作为显式 route 标记出现
    affects_clusters:
      - P0-00-RS03-C01
    why_decision_required: charter 只允许其作为协调视图，不可被建模为新 scenario family；是否需要显式 route 标记仍需后续决策。
  - decision_id: DR-002
    decision_name: review-only 与 founder_review 的先后顺序是否固定
    affects_clusters:
      - P0-00-RS02-C02
      - P0-00-RS04-C01
    why_decision_required: 当前可确认两者相关，但未有 canonical 前后顺序契约。
  - decision_id: DR-003
    decision_name: 资产绑定冲突时是优先拆分为多个 research stub 还是统一阻断
    affects_clusters:
      - P0-00-RS03-C02
    why_decision_required: 上传包未提供冲突后默认处理优先级。
  - decision_id: DR-004
    decision_name: 被阻断项中哪些类别允许保留 review-only 中间态
    affects_clusters:
      - P0-00-RS04-C01
      - P0-00-RS04-C02
    why_decision_required: 需避免 review-only 过度泛化为兜底容器。

excluded_items:
  - excluded_id: EX-001
    excluded_name: 任何真实品牌事实、SKU 事实、门店事实、人物事实、顾客反馈事实
    reason: 超出 general_only 边界，属于实例路径。
  - excluded_id: EX-002
    excluded_name: CandidatePack、KE、ABox/TBox、Evidence landed、Serving、RAG、DIFY、approved passage
    reason: 任务只产出 research map，不得产出任何生产或下游对象。
  - excluded_id: EX-003
    excluded_name: 普通服装行业知识、面料知识、产品知识、陈列知识、品牌故事知识
    reason: P0-00 仅为控制面、编排面、路由治理面。
  - excluded_id: EX-004
    excluded_name: 新增 P0 之外能力组或新增 batch_014 之外 batch
    reason: 超出当前任务边界。
  - excluded_id: EX-005
    excluded_name: 把 A2 support-only 写成完整陈列系统
    reason: 上传包未授权完整 display-system ontology。
  - excluded_id: EX-006
    excluded_name: 任何 readiness true、production-ready、publishable、runtime-ready 表述
    reason: readiness 全禁用。

shared_cluster_merge_items:
  - merge_id: SM-001
    merge_candidate_name: 异常分发术语表共享
    source_clusters:
      - P0-00-RS02-C02
      - P0-00-RS04-C02
    merge_rule: 仅共享异常命名与去向术语；不得合并各自触发条件与再进入条件。
  - merge_id: SM-002
    merge_candidate_name: route 与 binding 前置关系共享
    source_clusters:
      - P0-00-RS01-C01
      - P0-00-RS03-C02
    merge_rule: 仅共享“槽位完备度 -> bindability”关系；不得把 slot 契约与资产白名单合成一张全域表。
  - merge_id: SM-003
    merge_candidate_name: review-only 与 founder-review 过渡关系共享
    source_clusters:
      - P0-00-RS02-C02
      - P0-00-RS04-C01
    merge_rule: 仅共享过渡关系，不合并为统一审批流程。

founder_review_items:
  - founder_review_id: FR-001
    item_name: 控制面边界可能被改写为普通领域知识的请求
    review_reason: 风险在于破坏 P0-00 control-plane-only policy。
  - founder_review_id: FR-002
    item_name: 试图用弱 source/evidence 支撑高风险 claim 的请求
    review_reason: 风险在于误把 unsupported claim 带入可消费研究面。
  - founder_review_id: FR-003
    item_name: 试图把 review-only 或 decision_required 事项描述成可下游使用
    review_reason: 风险在于 readiness 泄漏。
  - founder_review_id: FR-004
    item_name: 试图把 support-only 显示语境扩张为完整 display ontology
    review_reason: 风险在于 scope 失真与能力归属混乱。

forbidden_output_attestation:
  candidatepack_generated: false
  KE_generated: false
  abox_generated: false
  tbox_generated: false
  evidence_landed_generated: false
  serving_projection_generated: false
  approved_passage_generated: false
  rag_context_bundle_generated: false
  dify_workflow_generated: false
  publishable_content_generated: false
  real_brand_fact_generated: false
  real_sku_fact_generated: false
  real_store_fact_generated: false
  real_person_fact_generated: false
  real_customer_feedback_generated: false

unresolved_decisions:
  - UD-001: 是否需要单独的 canonical checker 顺序 contract，当前上传包未给出固定顺序。
  - UD-002: founder_review 是否只处理风险敏感项，还是也处理 ontology ownership 冲突，当前上传包未穷举。
  - UD-003: review-only 中间态是否允许承载 asset binding 失败说明的最小模板，当前上传包未给出。
  - UD-004: blocked-to-gap 的再进入是否需要单独的 source freshness 要求，当前上传包未给出。

source_gap_seed:
  - SGS-001: 最小 intake 字段字典缺失
  - SGS-002: claim 强度分级词表缺失
  - SGS-003: founder_review 触发条件清单缺失
  - SGS-004: 研究型执行资产绑定白名单缺失
  - SGS-005: reentry prerequisite 字段模板缺失

self_check:
  covered_required_subcards:
    - P0-00-RS01
    - P0-00-RS02
    - P0-00-RS03
    - P0-00-RS04
  every_subcard_has_required_knowledge_clusters: true
  only_p0_00_scope_used: true
  only_batch_014_used: true
  no_real_instance_fact: true
  no_candidatepack_or_downstream_artifact: true
  no_readiness_enabled: true
  no_p0_00_domain_leak_intended: true
  no_full_part_a_claim: true
  count_not_used_as_acceptance_kpi: true
  optional_reference_not_treated_as_canonical_truth: true

readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false