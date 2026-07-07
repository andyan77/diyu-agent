map_id: W4_P0_03_process_material_quality_knowledge_map
map_version: v0.1
output_file: W4_P0_03_process_material_quality_knowledge_map.yaml
status: research_planning_only
cell_id: W4
prompt_id: WEB-DEEP-RESEARCH-W4-P0-03-PROCESS-MATERIAL-QUALITY-MAP-001
capability_group_id: P0-03
capability_group_name: 工艺 / 面料 / 版型内容科普知识地图
knowledge_mode: general_only

source_inputs:
  pack_id: web_gpt_upload_pack_v0_1
  authority_manifest: 09_upload_pack_manifest.json
  mandatory_files:
    - 01_research_charter_and_redlines.md
    - 02_p0_capability_and_subcards.yaml
    - 03_batch_allocation_matrix.csv
    - 04_research_map_output_schema.yaml
    - 05_source_claim_evidence_policy.md
    - 06_candidatepack_and_readiness_policy.md
    - 07_dq_anti_homogeneity_policy.md
    - 08_optional_reference_digest.md
    - 09_upload_pack_manifest.json
  precedence_rules:
    - "09_upload_pack_manifest.json 为当前上传包文件权威。"
    - "charter / schema / matrix 优先于 optional reference。"
    - "optional reference 只可作为格式启发，不能视为 canonical truth。"
    - "所有 readiness-like state 必须保持 false。"
  scope_attestation:
    - "仅处理 P0-03 general_only 研究地图。"
    - "不生成 CandidatePack、KE、Serving projection、RAG context bundle、DIFY workflow、approved_passage_text。"
    - "不写真实品牌、真实 SKU、真实门店、真实人物、真实顾客反馈。"

p0_scope:
  selected_scope:
    - P0-03
  scope_note: "selected general-only P0 scope only; not full Part A coverage"

research_subcard_refs:
  - research_card_id: P0-03-RS01
    p0_group: P0-03
    theme: apparel category and product schema
    target_count_budget: 180
    primary_batches:
      - batch_002
      - batch_003
    secondary_batches:
      - batch_005
    knowledge_focus: "apparel category schema and general product attribute boundaries"
    forbidden_scope:
      - real_sku_fact
      - product_master_data
      - price_or_inventory_fact
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true
  - research_card_id: P0-03-RS02
    p0_group: P0-03
    theme: material craft and construction
    target_count_budget: 180
    primary_batches:
      - batch_003
      - batch_005
    secondary_batches:
      - batch_011
    knowledge_focus: "material family, craft construction, color, silhouette, and fit methods"
    forbidden_scope:
      - unsupported_performance_claim
      - lab_result_claim
      - brand_material_fact
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true
  - research_card_id: P0-03-RS03
    p0_group: P0-03
    theme: body effect and claim boundary
    target_count_budget: 180
    primary_batches:
      - batch_004
      - batch_001
    secondary_batches:
      - batch_014
    knowledge_focus: "body effect, fit result, and claim evidence boundaries"
    forbidden_scope:
      - body_effect_guarantee
      - medical_or_sensitive_claim
      - no_evidence_claim
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true
  - research_card_id: P0-03-RS04
    p0_group: P0-03
    theme: process and quality story
    target_count_budget: 180
    primary_batches:
      - batch_003
      - batch_009
    secondary_batches:
      - batch_012
    knowledge_focus: "process storytelling, quality observation, and evidence routing"
    forbidden_scope:
      - quality_guarantee
      - unverifiable_factory_fact
      - production_certificate_claim
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true

subcard_maps:
  - research_card_id: P0-03-RS01
    p0_group: P0-03
    theme: apparel category and product schema
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true
    target_count_budget: 180
    knowledge_focus: "apparel category schema and general product attribute boundaries"
    batch_refs:
      primary_batches:
        - batch_002
        - batch_003
      secondary_batches:
        - batch_005
    forbidden_scope:
      - real_sku_fact
      - product_master_data
      - price_or_inventory_fact
    required_knowledge_clusters:
      - *c_rs01_01
      - *c_rs01_02
      - *c_rs01_03
    required_execution_asset_types: &common_assets
      - 术语归一表
      - 属性槽位与关系映射表
      - claim-证据阶梯对照表
      - 可观察线索采集清单
      - 风险边界判定卡
      - source gap 台账
      - decision required 台账
      - DQ 去同质化审查清单
      - 可拍摄表达方式观察板
    required_dq_checks: &common_dq
      - "每个 cluster 必须同时包含定义、适用条件、不适用条件、反边界、输出影响、证据需求、风险标记。"
      - "每个 cluster 必须有不可替代锚点：对象、动作、结构节点、观察差异、场景或约束至少一项。"
      - "不得出现对任意行业都通用的空模板句；服装/零售语境必须可见。"
      - "claim 与 evidence 必须分离；高风险 claim 无证据时只能降级或转 source gap。"
      - "优先保留可拍、可比、可观察的知识；无法影响可见输出的 cluster 视为弱簇。"
      - "平台提示只作为研究提示，不得演化成脚本、直播话术或发布文案。"
      - "任何真实品牌、SKU、门店、人物、顾客反馈一律判定为越界。"
    fallback_conditions:
      - "若品类术语存在多套并行叫法，先保留上位中性称谓，并把细分命名差异写入 unresolved_decisions。"
      - "若某属性槽位无法证明是 P0-03 独立归属，则只保留关系提示，不下沉为硬定义。"
      - "若比较维度会自然导向功效结论，则回退为可观察差异级别。"
    blocking_conditions:
      - "需要真实 SKU 主数据、价格、库存或品牌商品资料才能成立。"
      - "将属性槽位写成仓内正式 ontology 或正式 capability card。"
      - "把 comparison 直接写成优劣承诺。"
    unresolved_decisions:
      - "颜色主归属在 RS01 属性槽位还是 RS02 材料/视觉模块，需要后续 intake 确认 ontology ownership。"
      - "品类 schema 的最细粒度是否只到抽象单品层，不进入真实款式变体层，需要后续决策。"
    source_gap_seed:
      - "缺少一套被后续 intake 接受的通用服装品类术语来源样本。"
      - "缺少属性槽位与证据需求之间的一对多关系样本。"
    self_check:
      covers_required_subcard: true
      uses_general_only_mode: true
      contains_real_instance_fact: false
      contains_production_ready_output: false
      readiness_all_false: true
      requires_later_repository_validation: true
      notes_open_questions: true

  - research_card_id: P0-03-RS02
    p0_group: P0-03
    theme: material craft and construction
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true
    target_count_budget: 180
    knowledge_focus: "material family, craft construction, color, silhouette, and fit methods"
    batch_refs:
      primary_batches:
        - batch_003
        - batch_005
      secondary_batches:
        - batch_011
    forbidden_scope:
      - unsupported_performance_claim
      - lab_result_claim
      - brand_material_fact
    required_knowledge_clusters:
      - *c_rs02_01
      - *c_rs02_02
      - *c_rs02_03
      - *c_rs02_04
    required_execution_asset_types: *common_assets
    required_dq_checks: *common_dq
    fallback_conditions:
      - "若某材料、颜色、版型术语只能通过营销语出现，先退回到更上位的中性术语。"
      - "若工艺节点不可见或无法通用解释，则只保留 source_gap_seed，不写成正向 cluster。"
      - "若版型词容易被误解为身材结果词，则直接引用 RS03 的语言阶梯降级处理。"
    blocking_conditions:
      - "需要真实品牌面料配方、实验结果、专利工艺或工厂事实才能成立。"
      - "把材料名词直接等同于性能、舒适度、耐用性或品质等级。"
      - "输出无法被拍摄或观察验证的纯空泛工艺描述。"
    unresolved_decisions:
      - "颜色模块与材料肌理模块的边界深度需统一，否则可能在 RS02 内部重复建模。"
      - "手感词是否允许作为独立子维度，还是必须始终挂到观察/主观声明边界下，需后续确认。"
    source_gap_seed:
      - "缺少面料家族术语与性能 claim 分离的示例型权威来源。"
      - "缺少可见工艺节点与不可直接外推质量结论之间的方法学来源样本。"
    self_check:
      covers_required_subcard: true
      uses_general_only_mode: true
      contains_real_instance_fact: false
      contains_production_ready_output: false
      readiness_all_false: true
      requires_later_repository_validation: true
      notes_open_questions: true

  - research_card_id: P0-03-RS03
    p0_group: P0-03
    theme: body effect and claim boundary
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true
    target_count_budget: 180
    knowledge_focus: "body effect, fit result, and claim evidence boundaries"
    batch_refs:
      primary_batches:
        - batch_004
        - batch_001
      secondary_batches:
        - batch_014
    forbidden_scope:
      - body_effect_guarantee
      - medical_or_sensitive_claim
      - no_evidence_claim
    required_knowledge_clusters:
      - *c_rs03_01
      - *c_rs03_02
      - *c_rs03_03
    required_execution_asset_types: *common_assets
    required_dq_checks: *common_dq
    fallback_conditions:
      - "若无法确认某表达的风险等级，按更严格等级处理。"
      - "若效果词不能被改写为中性观察词，则整句不进入 cluster，转 source gap 或 excluded。"
      - "若证据类别无法判定最低门槛，则将对应 claim 统一降级为不可直接断言。"
    blocking_conditions:
      - "出现医学、治疗、矫正、身体保证或焦虑导向表述。"
      - "把 GPT 草稿、镜头表现、主观印象当作证据。"
      - "任何 readiness 被写成 true 或暗示可直接用于生产。"
    unresolved_decisions:
      - "舒适性中纯主观体感与需要客观证据的边界，是否单列子层级，需后续 intake 定义。"
      - "某些常用风格词若被公众默认理解为身材结果词，是否应整体列入敏感词表，需后续决策。"
    source_gap_seed:
      - "缺少被后续 intake 接受的 claim 风险词分级词表。"
      - "缺少观察词—关系词—结果词转换准则的示例来源。"
    self_check:
      covers_required_subcard: true
      uses_general_only_mode: true
      contains_real_instance_fact: false
      contains_production_ready_output: false
      readiness_all_false: true
      requires_later_repository_validation: true
      notes_open_questions: true

  - research_card_id: P0-03-RS04
    p0_group: P0-03
    theme: process and quality story
    status: research_planning_only
    not_formal_capability_card: true
    not_registry: true
    not_candidatepack: true
    not_KE: true
    target_count_budget: 180
    knowledge_focus: "process storytelling, quality observation, and evidence routing"
    batch_refs:
      primary_batches:
        - batch_003
        - batch_009
      secondary_batches:
        - batch_012
    forbidden_scope:
      - quality_guarantee
      - unverifiable_factory_fact
      - production_certificate_claim
    required_knowledge_clusters:
      - *c_rs04_01
      - *c_rs04_02
      - *c_rs04_03
      - *c_rs04_04
    required_execution_asset_types: *common_assets
    required_dq_checks: *common_dq
    fallback_conditions:
      - "若品质讲解只能依赖真实工厂或真实认证事实，则退回 source_gap_seed，不输出正向内容。"
      - "若 quality 观察项无法区分可观察与可证明，则只保留观察动作，不保留评价词。"
      - "若可拍摄表达方式开始接近脚本化，则回退为镜头对象与动作级别。"
    blocking_conditions:
      - "引用真实证书、真实检测结果、真实执行标准状态或真实工厂事实。"
      - "把局部细节观察直接写成整体品质保证。"
      - "将研究提示扩写为 production-ready 文案、脚本、直播话术或培训成稿。"
    unresolved_decisions:
      - "RS04 secondary_batch 标注为 batch_012，但 batch allocation matrix 中 P0-03 对 batch_012 计数为 0；该冲突需要后续确认是支持性引用还是录入口径差异。"
      - "品质证明是否允许只保留类型学描述而完全不触及标准编号粒度，需后续 intake 明确。"
    source_gap_seed:
      - "缺少品质观察项与证明类型一一或一对多映射的示例来源。"
      - "缺少可拍摄表达方式与非脚本化研究提示之间的界线示例。"
    self_check:
      covers_required_subcard: true
      uses_general_only_mode: true
      contains_real_instance_fact: false
      contains_production_ready_output: false
      readiness_all_false: true
      requires_later_repository_validation: true
      notes_open_questions: true

required_knowledge_clusters:
  - &c_rs01_01
    cluster_id: P0-03-RS01-CL01
    cluster_name: 服装品类与解释范围边界
    p0_group: P0-03
    research_card_id: P0-03-RS01
    domain_module: category_schema
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - boundary_rule
      - relation_hint
    object_type: CapabilityResearchCluster
    definition: "定义通用品类层级、可解释对象边界与属性入口，仅生成研究用解释骨架，不生成真实商品事实。"
    why_required_for_capability: "为 P0-03 建立先解释对象、再解释属性、最后解释风险边界的基础结构，防止科普内容滑向真实商品主数据。"
    expected_body_topics:
      - 上装/下装/连衣类/外搭类等抽象品类分层
      - 单品解释时可使用的通用属性槽位
      - 品类说明与真实 SKU 事实的切断规则
    applies_when: "需要建立某类服装一般如何被描述、常见属性有哪些、哪些属性需要证据的研究地图时。"
    does_not_apply_when: "需要填写品牌商品库、真实 SKU 参数、价格库存或渠道策略时。"
    counter_boundary: "若品类差异只能依赖真实商品实例才能成立，则降级为 source gap 或 decision required。"
    required_relations:
      - 连接 RS01-CL02 属性槽位体系
      - 为 RS02 面料/工艺与 RS03 claim 边界提供对象入口
    output_influence: "帮助后续研究将内容拆成稳定说明单元，避免把多个对象混在一段里。"
    source_dependency: "依赖后续引入通用服装分类术语来源与属性定义来源；当前地图只定义检索方向，不证明任何商品事实。"
    evidence_need: "至少需要术语定义类来源；若属性带有性能、舒适、耐用或身材效果色彩，则需追加证据类来源要求。"
    risk_boundaries:
      - 不得落入真实 SKU、价格、库存、上新节奏、门店配货事实
      - 不得把品类定义写成某品牌专属产品线
    evidence_classes:
      - terminology_definition_source
      - apparel_category_reference
      - attribute_taxonomy_reference
    risk_flags:
      - instance_fact_risk
      - schema_overreach_risk
    source_research_priority: 高
    shared_with_capability_cards:
      - P0-05
      - P0-04
    batch_refs:
      - batch_002
      - batch_003
    candidate_output_effect: "约束后续候选内容以类别—属性—边界结构组织，减少泛化空话与实例混入。"
    forbidden_knowledge_leakage:
      - real_sku_fact
      - product_master_data
      - price_or_inventory_fact
      - publishable_script
    source_gap_likelihood: 中
    duplicate_check_key: P0-03|RS01|category_schema_boundary
    body_structure_consistency_note: "正文顺序保持对象定义→适用范围→不适用范围→与属性槽位关系→风险提示。"

  - &c_rs01_02
    cluster_id: P0-03-RS01-CL02
    cluster_name: 产品属性槽位与通用描述骨架
    p0_group: P0-03
    research_card_id: P0-03-RS01
    domain_module: product_attribute_schema
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - relation_hint
      - boundary_rule
    object_type: CapabilityResearchCluster
    definition: "定义 P0-03 研究中允许出现的通用属性槽位及其调用顺序，用于组织知识而不是宣告正式数据模型。"
    why_required_for_capability: "将面料、颜色、版型、廓形、工艺、品质证明、claim 边界统一纳入同一属性槽位体系，便于后续拆分研究任务。"
    expected_body_topics:
      - 面料/材质槽位
      - 颜色/色调/视觉感受槽位
      - 版型/廓形/剪裁槽位
      - 工艺/结构槽位
      - 品质证明/证据槽位
      - claim 风险槽位
    applies_when: "需要建立内容科普模板的抽象骨架，并保证每段内容都能回到明确属性槽位时。"
    does_not_apply_when: "需要输出正式注册表、仓内 canonical 数据结构或运行时字段时。"
    counter_boundary: "若某槽位必须依赖 P0-00 控制逻辑才能定义，则记入 decision required，防止控制面泄漏。"
    required_relations:
      - 承接 RS01-CL01 的品类入口
      - 向 RS02/RS03/RS04 分发属性研究任务
      - 与 P0-00 证据路由只建立关系，不吸收控制面知识为领域知识
    output_influence: "影响候选内容的段落次序、镜头切换点、比对维度与审稿清单。"
    source_dependency: "依赖后续对属性命名规范、关系规范、证据路由规范进行补源；当前仅做研究地图级别结构定义。"
    evidence_need: "需要术语定义来源与证据政策来源双重支撑；涉及高风险 claim 的槽位需单独挂证据要求。"
    risk_boundaries:
      - 不得把属性槽位误写成正式 ontology 或正式 capability card
      - 不得将品质证明自动等同于真实认证已存在
    evidence_classes:
      - attribute_schema_reference
      - content_structure_reference
      - evidence_policy_reference
    risk_flags:
      - control_plane_leak_risk
      - empty_template_risk
    source_research_priority: 高
    shared_with_capability_cards:
      - P0-00
      - P0-05
      - P0-04
    batch_refs:
      - batch_002
      - batch_003
      - batch_014
    candidate_output_effect: "让后续内容候选能够按槽位组合，形成可审查的解释结构，而不是无锚点的泛泛描述。"
    forbidden_knowledge_leakage:
      - formal_capability_card_rewrite
      - ontology_overclaim
      - real_certification_fact
    source_gap_likelihood: 低
    duplicate_check_key: P0-03|RS01|attribute_slot_schema
    body_structure_consistency_note: "正文顺序保持槽位名称→可说内容→不可说内容→需要连接的证据或关系→输出影响。"

  - &c_rs01_03
    cluster_id: P0-03-RS01-CL03
    cluster_name: 同类比较维度与禁比边界
    p0_group: P0-03
    research_card_id: P0-03-RS01
    domain_module: comparison_method
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - general_method
      - evidence_requirement
    object_type: CapabilityResearchCluster
    definition: "定义同类服装或相邻属性之间的通用比较方法，只允许比较观察维度、结构差异和表达方式，不允许无证据地比较效果与结果。"
    why_required_for_capability: "P0-03 内容常含如何区分、如何看差异、如何理解取舍等教育需求；该簇用于定义可比维度与禁比边界，避免偷渡功效结论。"
    expected_body_topics:
      - 同类之间可比的维度
      - 不可直接比较的维度
      - 比较时如何显示未知项
      - 何时必须触发 source gap
    applies_when: "需要做如何区分、如何理解差异、如何说明取舍的通用内容时。"
    does_not_apply_when: "对比结论会落到真实商品、真实品牌、实验数据或明确功效承诺时。"
    counter_boundary: "若比较维度无法与可观察对象对应，而只能靠主观结论成立，则回退为边界说明。"
    required_relations:
      - 依赖 RS01-CL02 属性槽位
      - 与 RS03-CL02 claim 证据阶梯联动
    output_influence: "让后续候选内容可以做教育型对比，但必须把可观察差异和不可直接下结论的效果切开。"
    source_dependency: "依赖通用比较方法来源、基础术语来源与证据政策来源。"
    evidence_need: "若比较进入性能、舒适、耐用、体感、品质优劣，则需单独证据要求；否则仅保留观察维度。"
    risk_boundaries:
      - 不得把比较写成优劣承诺
      - 不得出现实验结果、耐用性、舒适性、显瘦或保暖结论
    evidence_classes:
      - comparison_dimension_reference
      - evidence_policy_reference
      - risk_boundary_reference
    risk_flags:
      - comparison_overclaim_risk
    source_research_priority: 中
    shared_with_capability_cards:
      - P0-05
    batch_refs:
      - batch_002
      - batch_003
      - batch_004
    candidate_output_effect: "让候选内容形成比较维度—能看见什么—不能推出什么的结构。"
    forbidden_knowledge_leakage:
      - unsupported_performance_claim
      - quality_guarantee
      - body_effect_guarantee
    source_gap_likelihood: 中
    duplicate_check_key: P0-03|RS01|comparison_boundary
    body_structure_consistency_note: "正文顺序保持比较对象→允许维度→禁比维度→证据触发点→输出提醒。"

  - &c_rs02_01
    cluster_id: P0-03-RS02-CL01
    cluster_name: 面料家族解释与属性边界
    p0_group: P0-03
    research_card_id: P0-03-RS02
    domain_module: material_family
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - boundary_rule
      - evidence_requirement
    object_type: CapabilityResearchCluster
    definition: "定义面料家族、结构层级与可表达边界，强调材料描述不等于效果证明。"
    why_required_for_capability: "面料是 P0-03 的核心对象；需要把原料、织法/针法、手感与可观察结构分层，避免把常见印象写成性能事实。"
    expected_body_topics:
      - 纤维/纱线/面料层级区分
      - 梭织/针织等结构差异的解释入口
      - 常见观察项与不可直接外推的性能项
      - 手感词与事实词的边界
    applies_when: "需要解释某种常见材质、结构或手感为什么会在视觉或触感上呈现差异时。"
    does_not_apply_when: "需要宣称某真实商品因此更耐穿、更凉快、更显瘦或更适合特定人群时。"
    counter_boundary: "若研究只能获得营销词而无术语定义或证据方向，则退回 source gap seed，不产出正向 cluster。"
    required_relations:
      - 承接 RS01-CL02 面料槽位
      - 向 RS03-CL02 传递性能 claim 风险
      - 向 RS04-CL02 提供质量观察项
    output_influence: "帮助后续候选内容把面料是什么与效果是否成立分开，形成可拍可审的材料教育结构。"
    source_dependency: "依赖通用纺织术语来源、结构解释来源和证据政策；不依赖任何品牌产品资料。"
    evidence_need: "术语解释至少需要定义类来源；凡涉及性能、体感、质量优劣，均需追加标准、试验方法或专家方法来源。"
    risk_boundaries:
      - 不得把透气、抗皱、保暖、耐磨、舒适等写为默认特性
      - 不得把某材料家族说成在所有情境下都优于另一材料家族
    evidence_classes:
      - textile_terminology_source
      - fabric_structure_reference
      - evidence_policy_reference
    risk_flags:
      - hard_claim_risk
      - comfort_claim_risk
      - durability_claim_risk
    source_research_priority: 高
    shared_with_capability_cards:
      - P0-05
      - P0-04
    batch_refs:
      - batch_003
      - batch_005
    candidate_output_effect: "帮助后续候选内容把材料家族→结构特点→可观察线索→不可直接承诺的效果→需补源项串起来。"
    forbidden_knowledge_leakage:
      - unsupported_performance_claim
      - brand_material_fact
      - lab_result_claim
    source_gap_likelihood: 高
    duplicate_check_key: P0-03|RS02|material_family_boundary
    body_structure_consistency_note: "正文先区分材料层级，再写可观察表现，最后写不能直接推出的效果与证据需求。"

  - &c_rs02_02
    cluster_id: P0-03-RS02-CL02
    cluster_name: 颜色表达结构与视觉解释边界
    p0_group: P0-03
    research_card_id: P0-03-RS02
    domain_module: color_expression
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - boundary_rule
      - relation_hint
    object_type: CapabilityResearchCluster
    definition: "定义颜色研究的可用表达维度与视觉解释边界，只允许输出通用观察框架，不输出真人适配结论。"
    why_required_for_capability: "颜色内容容易滑向审美空话或色差事实；需要建立颜色名称、色相/明度/饱和度、搭配叙事与可拍摄线索的通用框架。"
    expected_body_topics:
      - 颜色基础维度
      - 色彩家族与中性/冷暖等通用表达
      - 颜色在镜头与光线下的观察提醒
      - 颜色故事与品质/显白/显瘦等结论切断
    applies_when: "需要解释一种颜色为什么看上去更沉稳、更轻盈、更有层次，或如何在画面中被识别时。"
    does_not_apply_when: "需要给出对肤色、身材、年龄、气质的确定性结果承诺时。"
    counter_boundary: "若颜色效果强依赖光线、面料肌理或真人对比而缺少中性观察条件，则仅保留方法，不下结论。"
    required_relations:
      - 连接 RS01-CL02 颜色槽位
      - 连接 RS04-CL04 可拍摄表达
      - 与 RS03-CL01 体型效果边界联动
    output_influence: "让后续候选内容能用色彩维度—视觉线索—场景提示—禁断效果词的方式组织。"
    source_dependency: "依赖通用色彩理论、视觉观察方法与证据政策，不依赖真实品牌配色事实。"
    evidence_need: "颜色术语可由定义类来源支撑；若延伸到牢度、耐晒、色差稳定性，则必须转入证据类来源。"
    risk_boundaries:
      - 不得把某颜色写成对所有人都显白、显瘦、显气色
      - 不得把色差、染色牢度、耐洗结果写成既成事实
    evidence_classes:
      - color_theory_reference
      - visual_observation_reference
      - evidence_policy_reference
    risk_flags:
      - visual_bias_risk
      - body_result_inference_risk
    source_research_priority: 中
    shared_with_capability_cards:
      - P0-04
      - P0-05
    batch_refs:
      - batch_003
      - batch_011
    candidate_output_effect: "让后续候选内容在色彩解释里有锚点、有镜头线索、无越界结果承诺。"
    forbidden_knowledge_leakage:
      - body_effect_guarantee
      - unsupported_quality_claim
    source_gap_likelihood: 中
    duplicate_check_key: P0-03|RS02|color_expression_boundary
    body_structure_consistency_note: "正文顺序保持颜色维度→视觉线索→拍摄或观察前提→不可外推结果。"

  - &c_rs02_03
    cluster_id: P0-03-RS02-CL03
    cluster_name: 版型廓形剪裁术语地图
    p0_group: P0-03
    research_card_id: P0-03-RS02
    domain_module: fit_and_silhouette
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - relation_hint
      - boundary_rule
    object_type: CapabilityResearchCluster
    definition: "定义版型、廓形与剪裁词汇之间的关系及其观察入口，强调术语解释不自动构成效果承诺。"
    why_required_for_capability: "版型与廓形是内容科普高频对象，需要把轮廓、松量、落肩、腰线、裤型等术语组织成可解释且不越界的地图。"
    expected_body_topics:
      - 版型与廓形区别
      - 轮廓线、长度、宽窄、松量、重心等表达
      - 结构节点与视觉结果的关系提示
      - 版型词与身材效果承诺的切断
    applies_when: "需要科普某种轮廓、裤型、肩线、腰位或长度处理时。"
    does_not_apply_when: "需要基于真人案例给出确定性身材优化结果、尺码推荐或个体适配结论时。"
    counter_boundary: "若一个版型词只能在真人实例或试穿反馈中被证明，则当前仅保留术语与观察方法，不产出结果结论。"
    required_relations:
      - 连接 RS01-CL02 版型槽位
      - 连接 RS03-CL01 体型效果语言阶梯
      - 连接 RS04-CL04 画面示意方式
    output_influence: "让后续候选内容能稳定回答版型是什么、轮廓怎么形成、看点在哪里、不能承诺什么。"
    source_dependency: "依赖服装结构术语来源、版型参考来源与 claim 政策来源。"
    evidence_need: "术语解释类来源为基础；进入修饰效果、遮挡效果、比例改善时必须升级为高风险证据需求。"
    risk_boundaries:
      - 不得把版型术语直接等同于显瘦、显高、遮肉、修饰某部位结果
      - 不得把适合所有身材写成通用结论
    evidence_classes:
      - pattern_cut_reference
      - fashion_terminology_source
      - evidence_policy_reference
    risk_flags:
      - body_effect_risk
      - size_recommendation_risk
    source_research_priority: 高
    shared_with_capability_cards:
      - P0-05
      - P0-04
    batch_refs:
      - batch_003
      - batch_005
      - batch_011
    candidate_output_effect: "让后续候选内容形成术语定义—结构节点—视觉变化—风险边界的段落。"
    forbidden_knowledge_leakage:
      - body_effect_guarantee
      - fit_result_overclaim
    source_gap_likelihood: 高
    duplicate_check_key: P0-03|RS02|fit_silhouette_taxonomy
    body_structure_consistency_note: "正文顺序保持术语定义→结构节点→可观察变化→禁断外推。"

  - &c_rs02_04
    cluster_id: P0-03-RS02-CL04
    cluster_name: 工艺与结构观察线索
    p0_group: P0-03
    research_card_id: P0-03-RS02
    domain_module: craft_and_construction
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - relation_hint
      - evidence_requirement
    object_type: CapabilityResearchCluster
    definition: "定义常见可见工艺与结构节点的研究入口、观察顺序与慎言边界。"
    why_required_for_capability: "工艺内容如果没有观察线索就会空泛；该簇用于沉淀缝线、包边、拼接、压线、里布、门襟等可见结构节点及其表达边界。"
    expected_body_topics:
      - 可见工艺节点清单
      - 观察顺序：外观→结构→细节→不可直接外推的质量结论
      - 工艺名词与功能/耐用结论的风险切断
    applies_when: "需要用镜头或图示讲清楚衣物细节、结构选择或制作节点时。"
    does_not_apply_when: "需要宣称背后真实工厂流程、具体生产标准、耐用寿命或品牌专属工艺事实时。"
    counter_boundary: "若工艺只存在于不可见环节且没有通用可验证解释路径，则优先标记为 source gap。"
    required_relations:
      - 连接 RS04-CL01 工艺叙事节点
      - 连接 RS04-CL02 质量观察项
      - 连接 RS03-CL02 质量/耐用 claim 证据阶梯
    output_influence: "提升后续候选内容的可拍性和可审稿性，使工艺科普能落到看哪里、怎么看、不能直接断什么。"
    source_dependency: "依赖服装结构参考、可视检查方法或行业通用工艺术语来源。"
    evidence_need: "可见节点可先由术语/观察来源支撑；涉及耐用寿命、功能结果、品质等级即需更高证据。"
    risk_boundaries:
      - 不得把某工艺存在等同于更耐穿、更高端、更专业
      - 不得把无来源的生产工艺故事当作事实
    evidence_classes:
      - garment_construction_reference
      - visual_inspection_reference
      - evidence_policy_reference
    risk_flags:
      - factory_fact_risk
      - durability_claim_risk
    source_research_priority: 高
    shared_with_capability_cards:
      - P0-04
      - P0-05
    batch_refs:
      - batch_003
      - batch_005
      - batch_011
    candidate_output_effect: "提升后续候选内容的细节锚点与镜头对象选择，但不越过质量承诺边界。"
    forbidden_knowledge_leakage:
      - quality_guarantee
      - unverifiable_factory_fact
      - unsupported_durability_claim
    source_gap_likelihood: 高
    duplicate_check_key: P0-03|RS02|craft_observation_cues
    body_structure_consistency_note: "正文顺序保持节点名称→能看见什么→可能意味着什么→不能直接推出什么→需补源项。"

  - &c_rs03_01
    cluster_id: P0-03-RS03-CL01
    cluster_name: 身材效果语言阶梯与替代表达
    p0_group: P0-03
    research_card_id: P0-03-RS03
    domain_module: claim_boundary
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - general_method
      - routing_hint
    object_type: CapabilityResearchCluster
    definition: "定义身材效果相关表达的风险阶梯与可替代表达路径，使研究输出停留在通用观察边界内。"
    why_required_for_capability: "P0-03 涉及版型与颜色时极易滑向显瘦显高等敏感表述，需要建立从低风险观察词到高风险结果词的分层。"
    expected_body_topics:
      - 观察词/关系词/结果词分层
      - 能说视觉线条变化与不能保证身体结果的边界
      - 替代表达与回避表达
    applies_when: "需要谈及视觉比例、线条、重心、轮廓感受或穿着观感时。"
    does_not_apply_when: "需要直接承诺遮肉、修身、矫正体态、改变身体结果或针对具体人群给出保证时。"
    counter_boundary: "若一个表达无法被重写为中性观察词，则不进入 accepted cluster，直接 route 为 source gap 或 excluded。"
    required_relations:
      - 承接 RS02-CL02 与 RS02-CL03
      - 连接 RS03-CL03 场景化观察方法
      - 向 P0-00 证据路由提供触发点但不吸收控制面内容
    output_influence: "约束后续候选内容将视觉重心变化、轮廓感受、线条走向与显瘦显高等结果性话术分离。"
    source_dependency: "依赖 claim 政策、敏感断言边界来源及内容风险规则来源。"
    evidence_need: "该簇主要需要政策与边界类来源；一旦进入效果证明，则需更高证据并可能不属于 general_only。"
    risk_boundaries:
      - 不得出现保证式效果词、医学词、身体焦虑导向词
      - 不得把个体主观感受包装成普适结果
    evidence_classes:
      - claim_policy_reference
      - sensitive_claim_boundary_reference
      - content_risk_reference
    risk_flags:
      - sensitive_effect_risk
      - hard_claim_risk
    source_research_priority: 高
    shared_with_capability_cards:
      - P0-00
      - P0-05
    batch_refs:
      - batch_004
      - batch_001
      - batch_014
    candidate_output_effect: "约束后续候选内容优先使用观察语言，降低敏感断言风险。"
    forbidden_knowledge_leakage:
      - medical_or_sensitive_claim
      - body_effect_guarantee
      - persona_harm_risk
    source_gap_likelihood: 高
    duplicate_check_key: P0-03|RS03|body_effect_language_ladder
    body_structure_consistency_note: "正文顺序保持高频说法→风险分层→可替代表达→禁止区域→路由动作。"

  - &c_rs03_02
    cluster_id: P0-03-RS03-CL02
    cluster_name: 舒适性性能耐用品质 claim 证据阶梯
    p0_group: P0-03
    research_card_id: P0-03-RS03
    domain_module: evidence_routing
    knowledge_type: evidence_requirement
    knowledge_types:
      - evidence_requirement
      - boundary_rule
      - routing_hint
    object_type: EvidenceNeed
    definition: "定义从低风险描述到高风险性能/品质 claim 的证据阶梯和路由动作。"
    why_required_for_capability: "任务明确要求研究 claim 边界；该簇负责把舒适、抗皱、保暖、挺括、耐穿、品质好等说法与所需证据类型对应起来。"
    expected_body_topics:
      - claim 分级
      - 不同 claim 对应的证据类别
      - 无证据时允许保留的最低表达层级
      - source gap 触发阈值
    applies_when: "需要评价手感、舒适、抗皱、保暖、耐穿、挺括、垂坠、恢复性等敏感属性时。"
    does_not_apply_when: "只是在做纯术语解释而未触及效果判断时。"
    counter_boundary: "若研究无法明确 claim 所需的最低证据类别，则该 claim 整体不得进入 accepted clusters。"
    required_relations:
      - 承接 RS02-CL01 与 RS02-CL04 的材料和工艺名词
      - 连接 RS04-CL02 与 RS04-CL03 的品质证明类型
      - 连接 P0-00 但不重写为控制面卡
    output_influence: "直接决定后续候选内容哪些句子只能写成观察、哪些必须标注待补源、哪些必须禁出。"
    source_dependency: "依赖标准、试验方法、专家方法和证据政策等来源类型定义；当前地图不宣称任何已具备这些来源。"
    evidence_need: "对所有 fabric / fit / body-effect / quality / performance claim 必须显式挂接证据需求；无证据时只能下沉为边界说明。"
    risk_boundaries:
      - 不得将有工艺或有面料名词视为已有证据
      - 不得以 GPT 草稿、营销图、非验证性描述替代证据
    evidence_classes:
      - evidence_policy_reference
      - test_method_reference
      - standard_reference
      - expert_method_reference
    risk_flags:
      - evidence_shortage_risk
      - serving_boundary_risk
    source_research_priority: 最高
    shared_with_capability_cards:
      - P0-00
    batch_refs:
      - batch_004
      - batch_001
      - batch_014
    candidate_output_effect: "保证后续候选内容在遇到高风险 claim 时自动降级为观察描述、待证据说明或 source gap。"
    forbidden_knowledge_leakage:
      - unsupported_performance_claim
      - unsupported_quality_claim
      - readiness_misinterpretation
    source_gap_likelihood: 高
    duplicate_check_key: P0-03|RS03|claim_evidence_ladder
    body_structure_consistency_note: "正文顺序保持 claim 类型→最低证据类别→无证据时降级动作→禁出条件。"

  - &c_rs03_03
    cluster_id: P0-03-RS03-CL03
    cluster_name: 场景化观察与非结论化表达
    p0_group: P0-03
    research_card_id: P0-03-RS03
    domain_module: observation_method
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - boundary_rule
      - relation_hint
    object_type: CapabilityResearchCluster
    definition: "定义面向图文/短视频的非结论化观察方法，只输出观察框架与风险边界。"
    why_required_for_capability: "为满足可拍摄表达方式要求，需要把镜头能观察到的线条、褶量、垂感、覆盖关系与不能推出的结论分离。"
    expected_body_topics:
      - 画面中可观察的版型/材料/颜色线索
      - 观察语句如何避免变成结果保证
      - 不同视角下的误判提醒
    applies_when: "需要说明如何通过镜头或静态图识别某种材质、轮廓或细节时。"
    does_not_apply_when: "需要通过镜头直接证明舒适度、耐洗性、耐磨性、显瘦效果或个体适配时。"
    counter_boundary: "若观察必须依赖真人反馈、实验数据或长周期使用结果，则只记录为 source gap seed。"
    required_relations:
      - 承接 RS03-CL01 语言阶梯
      - 连接 RS04-CL04 可拍摄表达
      - 回流 RS02-CL03 与 RS02-CL04 作为观察节点
    output_influence: "帮助后续候选内容建立镜头能证明什么、镜头不能证明什么的表达纪律。"
    source_dependency: "依赖视觉观察方法、镜头标注方法与 claim 边界来源。"
    evidence_need: "当观察会被观众自然理解为效果承诺时，必须附加风险提醒或降级。"
    risk_boundaries:
      - 不得借镜头看到之名偷渡功效或质量判断
      - 不得把真人个案试穿当成总规则
    evidence_classes:
      - visual_observation_reference
      - shot_annotation_reference
      - claim_policy_reference
    risk_flags:
      - visual_overinterpretation_risk
      - real_person_fact_risk
    source_research_priority: 中
    shared_with_capability_cards:
      - P0-04
    batch_refs:
      - batch_004
      - batch_003
      - batch_011
    candidate_output_effect: "让候选内容更可执行地展示观察动作，同时避免把展示动作误当成证据。"
    forbidden_knowledge_leakage:
      - visual_overclaim
      - real_person_fact
      - unsupported_body_effect_claim
    source_gap_likelihood: 中
    duplicate_check_key: P0-03|RS03|observation_without_conclusion
    body_structure_consistency_note: "正文顺序保持观察位置→可说现象→不可说结论→需要补源的 claim。"

  - &c_rs04_01
    cluster_id: P0-03-RS04-CL01
    cluster_name: 工艺叙事节点与讲解顺序
    p0_group: P0-03
    research_card_id: P0-03-RS04
    domain_module: process_story
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - relation_hint
      - boundary_rule
    object_type: CapabilityResearchCluster
    definition: "定义工艺科普的叙事骨架：从可讲对象到可见节点，再到可观察结果和不能确认的部分。"
    why_required_for_capability: "RS04 需要研究工艺如何被讲清楚而不编造工厂事实；该簇给出工艺叙事节点与安全讲解顺序。"
    expected_body_topics:
      - 从材料进入到结构节点再到可见结果的讲解顺序
      - 工艺故事中允许使用的中性动作词
      - 工艺叙事与真实工厂流程事实的切断
    applies_when: "需要做教育型工艺讲解、拆解看点或展示结构差异时。"
    does_not_apply_when: "需要描述真实工厂、真实产线、真实质量控制流程、真实认证状态时。"
    counter_boundary: "若叙事必须依赖不可见流程或专有工艺背景，则仅保留节点名称与 source gap seed。"
    required_relations:
      - 承接 RS02-CL04 工艺观察线索
      - 连接 RS04-CL04 可拍摄表达
      - 与 P0-01 叙事卡只共享结构方法，不共享品牌故事事实
    output_influence: "帮助后续候选内容把工艺内容讲成可观察节点串联，而不是制造神话。"
    source_dependency: "依赖工艺解释来源、演示方法来源和证据政策来源。"
    evidence_need: "只要叙事触及真实生产事实、真实制造资质、真实良品率等，就必须转出 accepted clusters。"
    risk_boundaries:
      - 不得编造打版、裁剪、车缝、整烫、质检等真实工厂流程细节
      - 不得宣称某品牌或某工厂采用某工艺
    evidence_classes:
      - process_description_reference
      - visual_demo_reference
      - evidence_policy_reference
    risk_flags:
      - factory_story_fabrication_risk
    source_research_priority: 高
    shared_with_capability_cards:
      - P0-01
      - P0-05
    batch_refs:
      - batch_003
      - batch_009
    candidate_output_effect: "让后续候选内容可按节点顺序讲工艺，而不跨越事实验证边界。"
    forbidden_knowledge_leakage:
      - unverifiable_factory_fact
      - brand_specific_process_fact
    source_gap_likelihood: 中
    duplicate_check_key: P0-03|RS04|process_story_nodes
    body_structure_consistency_note: "正文顺序保持对象→节点→可见差异→不能确认的部分→待补源。"

  - &c_rs04_02
    cluster_id: P0-03-RS04-CL02
    cluster_name: 品质观察项与证明类型地图
    p0_group: P0-03
    research_card_id: P0-03-RS04
    domain_module: quality_observation
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - evidence_requirement
      - relation_hint
    object_type: CapabilityResearchCluster
    definition: "定义品质观察项、观察顺序与可接受的证明类型分类，不将观察直接当作结论。"
    why_required_for_capability: "品质内容必须区分看得见的观察项和需要额外证明的品质结论；该簇定义两者的关系。"
    expected_body_topics:
      - 针脚、对位、平整度、边缘处理、辅料整合等可观察项
      - 观察项与可能关联的品质维度
      - 观察项不能单独证明的结果边界
      - 品质证明类型分类
    applies_when: "需要讲如何看一件衣物的做工、细节或完成度时。"
    does_not_apply_when: "需要直接判定优等、耐穿、高品质、严格质检通过等结论时。"
    counter_boundary: "若研究无法明确某观察项与品质维度之间的关系边界，则只保留观察动作，不保留价值判断。"
    required_relations:
      - 承接 RS02-CL04 工艺节点
      - 向 RS03-CL02 提供 claim 与证据映射
      - 向 RS04-CL03 输送证明类型边界
    output_influence: "让后续候选内容可以展示哪里能看、看到什么、但还不能断定什么，同时把证明责任留给后续证据。"
    source_dependency: "依赖通用视觉检查方法、基础质量评估方法与证据政策；当前不含真实检测结果。"
    evidence_need: "观察项至少需观察方法类来源；一旦涉及品质等级、稳定性、寿命，需追加更强证据来源。"
    risk_boundaries:
      - 不得由单一观察项直接推出耐用、品控稳定、整体做工更好等结论
      - 不得通过局部特写冒充完整品质证明
    evidence_classes:
      - visual_inspection_reference
      - quality_assessment_method_reference
      - evidence_policy_reference
    risk_flags:
      - quality_inference_risk
      - evidence_gap_risk
    source_research_priority: 最高
    shared_with_capability_cards:
      - P0-04
      - P0-05
    batch_refs:
      - batch_003
      - batch_009
      - batch_012
    candidate_output_effect: "使候选内容能输出更强的细节锚点，但自动避开绝对化品质承诺。"
    forbidden_knowledge_leakage:
      - quality_guarantee
      - unsupported_durability_claim
      - partial_observation_overclaim
    source_gap_likelihood: 高
    duplicate_check_key: P0-03|RS04|quality_observation_map
    body_structure_consistency_note: "正文顺序保持观察项→可能关联维度→不能单独证明的结论→所需证明类型。"

  - &c_rs04_03
    cluster_id: P0-03-RS04-CL03
    cluster_name: 品质证明与认证 claim 路由边界
    p0_group: P0-03
    research_card_id: P0-03-RS04
    domain_module: quality_proof_boundary
    knowledge_type: boundary_rule
    knowledge_types:
      - boundary_rule
      - evidence_requirement
      - routing_hint
    object_type: CapabilityResearchCluster
    definition: "定义品质证明、认证、检测和标准类说法的进入边界、降级条件和禁止条件。"
    why_required_for_capability: "任务明确要求研究品质证明与 claim 边界；该簇专门约束认证、检测、标准、吊牌、说明书等是否能进入内容。"
    expected_body_topics:
      - 证明材料类型分级
      - 能否在 general_only 地图中出现
      - 没有实例证据时如何写成 source gap seed
      - 何时升级 founder review
    applies_when: "需要解释什么类型的说法通常需要什么类型证明时。"
    does_not_apply_when: "需要引用真实证书、真实检测报告、真实标准编号、真实标签结论时。"
    counter_boundary: "若证明材料的对象、出处、时间和有效性无法分离清楚，则整体转 source gap 或 founder review。"
    required_relations:
      - 承接 RS04-CL02 证明类型分类
      - 连接 RS03-CL02 claim 证据阶梯
      - 与 P0-00 只做路由接口，不让控制面知识下沉为面料知识
    output_influence: "保证后续候选内容只会讨论什么类型的证明通常对应什么 claim，而不会伪造证书或检测结论。"
    source_dependency: "依赖证据政策、标准/认证类型定义来源与审核边界来源。"
    evidence_need: "凡触及真实证书状态、第三方报告结果、执行标准落地、合格证明，均为高风险并需强证据或 route away。"
    risk_boundaries:
      - 不得把真实认证、第三方检测、执行标准、合格率、证书状态写成已发生事实
      - 不得把任何泛称认证自动等同于某商品具备
    evidence_classes:
      - certification_type_reference
      - standard_type_reference
      - evidence_policy_reference
      - review_boundary_reference
    risk_flags:
      - proof_fabrication_risk
      - regulatory_misstatement_risk
    source_research_priority: 最高
    shared_with_capability_cards:
      - P0-00
    batch_refs:
      - batch_001
      - batch_004
      - batch_009
      - batch_014
    candidate_output_effect: "直接决定后续候选内容能否出现认证/证明/检测字眼，以及出现时只能停留在多抽象层。"
    forbidden_knowledge_leakage:
      - production_certificate_claim
      - lab_result_claim
      - readiness_leakage
    source_gap_likelihood: 高
    duplicate_check_key: P0-03|RS04|quality_proof_routing
    body_structure_consistency_note: "正文顺序保持证明类型→可谈抽象层级→禁谈实例层级→缺证据路由动作。"

  - &c_rs04_04
    cluster_id: P0-03-RS04-CL04
    cluster_name: 工艺品质内容的可拍摄表达方式
    p0_group: P0-03
    research_card_id: P0-03-RS04
    domain_module: filmable_expression
    knowledge_type: general_method
    knowledge_types:
      - general_method
      - relation_hint
      - boundary_rule
    object_type: CapabilityResearchCluster
    definition: "定义适用于工艺、面料、版型解释的可拍摄表达方式，仅保留镜头对象、观察动作和风险提醒。"
    why_required_for_capability: "任务要求只能研究可拍摄表达方式；该簇沉淀通用镜头对象、动作、对比方式和不可越界的旁白边界。"
    expected_body_topics:
      - 远景/中景/特写分别适合观察什么
      - 平铺、提拉、折叠、翻面、对位展示等动作提示
      - 镜头与字幕各自适合承载的信息层级
      - 避免脚本化与效果承诺化
    applies_when: "需要把研究结果转成可视化观察建议、拍摄提示或画面组织线索时。"
    does_not_apply_when: "需要直接写完整脚本、上镜台词、销售话术或发布文案时。"
    counter_boundary: "若表达方式无法与明确观察对象绑定，而只是抽象空话，则按 DQ 规则判弱并退回重写。"
    required_relations:
      - 承接 RS02-CL02、RS02-CL03、RS02-CL04 与 RS04-CL01、RS04-CL02
      - 向 P0-04 提供 support-only 的展示观察方法
    output_influence: "使后续候选内容具备可执行的观察动作提示，但仍保持研究态，不越过脚本与证明边界。"
    source_dependency: "依赖视觉演示方法、镜头设计方法与证据政策来源。"
    evidence_need: "该簇只需要方法类来源；但一旦镜头被用来证明品质、性能或身材效果，则必须回接证据阶梯。"
    risk_boundaries:
      - 不得输出 production-ready 脚本、直播话术、分镜稿
      - 不得用镜头动作暗示未经证明的品质或身材结果
    evidence_classes:
      - visual_demo_reference
      - shot_design_reference
      - evidence_policy_reference
    risk_flags:
      - script_leak_risk
      - platform_native_overreach
    source_research_priority: 高
    shared_with_capability_cards:
      - P0-04
    batch_refs:
      - batch_003
      - batch_009
      - batch_012
    candidate_output_effect: "使后续候选内容保留可视化潜力、镜头对象和动作锚点，但不可被误当成成片脚本。"
    forbidden_knowledge_leakage:
      - publishable_script
      - filmability_overreach
      - unsupported_visual_claim
    source_gap_likelihood: 中
    duplicate_check_key: P0-03|RS04|filmable_expression_methods
    body_structure_consistency_note: "正文顺序保持镜头对象→动作/视角→可观察信息→不可承诺信息。"

relation_hints:
  - relation_id: REL-P0-03-001
    from_cluster_id: P0-03-RS01-CL01
    to_cluster_id: P0-03-RS01-CL02
    relation_type: schema_contains
    note: "品类边界决定属性槽位可附着的对象范围。"
  - relation_id: REL-P0-03-002
    from_cluster_id: P0-03-RS01-CL02
    to_cluster_id: P0-03-RS02-CL01
    relation_type: slot_routes_to_module
    note: "面料槽位进入材料家族解释，但不自动授予性能事实。"
  - relation_id: REL-P0-03-003
    from_cluster_id: P0-03-RS01-CL02
    to_cluster_id: P0-03-RS02-CL03
    relation_type: slot_routes_to_module
    note: "版型/廓形槽位进入术语地图，再由 claim 边界约束说法。"
  - relation_id: REL-P0-03-004
    from_cluster_id: P0-03-RS02-CL01
    to_cluster_id: P0-03-RS03-CL02
    relation_type: high_risk_claim_requires_evidence
    note: "材料名词若延伸到舒适/性能/耐用 claim，必须走证据阶梯。"
  - relation_id: REL-P0-03-005
    from_cluster_id: P0-03-RS02-CL03
    to_cluster_id: P0-03-RS03-CL01
    relation_type: effect_language_constrained_by
    note: "版型术语可进入视觉观察，但不能直连结果性身材承诺。"
  - relation_id: REL-P0-03-006
    from_cluster_id: P0-03-RS02-CL04
    to_cluster_id: P0-03-RS04-CL01
    relation_type: observation_feeds_story
    note: "工艺观察线索是工艺叙事节点的素材来源。"
  - relation_id: REL-P0-03-007
    from_cluster_id: P0-03-RS04-CL02
    to_cluster_id: P0-03-RS04-CL03
    relation_type: proof_type_gated_by
    note: "质量观察项可以连接证明类型，但证明类型不等于已具备实例证明。"
  - relation_id: REL-P0-03-008
    from_cluster_id: P0-03-RS03-CL03
    to_cluster_id: P0-03-RS04-CL04
    relation_type: filmability_supports_expression
    note: "镜头观察方法为可拍摄表达提供边界，不为结果 claim 背书。"
  - relation_id: REL-P0-03-009
    from_cluster_id: P0-03-RS04-CL03
    to_cluster_id: P0-03-RS03-CL02
    relation_type: proof_boundary_inherits_evidence_ladder
    note: "认证、证明、检测类说法必须继承证据阶梯与禁止条件。"
  - relation_id: REL-P0-03-010
    from_cluster_id: P0-03-RS01-CL03
    to_cluster_id: P0-03-RS03-CL02
    relation_type: comparison_may_trigger_claim_routing
    note: "同类比较一旦进入优劣、耐用、舒适等判断，必须升级证据要求。"

source_gap_items:
  - source_gap_id: SG-P0-03-001
    related_subcards:
      - P0-03-RS02
      - P0-03-RS03
    gap_summary: "缺少用于分离材料术语与性能 claim 的通用权威来源样本。"
    trigger: "一旦出现透气、抗皱、保暖、耐穿、舒适等词而无明确证据类型。"
    route: "保留边界说明；具体 claim 不进入 accepted cluster。"
  - source_gap_id: SG-P0-03-002
    related_subcards:
      - P0-03-RS03
    gap_summary: "缺少可被 intake 接受的 claim 风险分级词表。"
    trigger: "需要把高频口语说法稳定映射到观察词/结果词/禁用词时。"
    route: "先用更严格风险等级处理，并写入 unresolved_decisions。"
  - source_gap_id: SG-P0-03-003
    related_subcards:
      - P0-03-RS04
    gap_summary: "缺少品质观察项与证明类型之间的方法学样本。"
    trigger: "需要说明看到什么细节通常对应何类证明需求时。"
    route: "只保留观察项，不保留品质结论。"
  - source_gap_id: SG-P0-03-004
    related_subcards:
      - P0-03-RS04
    gap_summary: "缺少非脚本化可拍摄表达方式与脚本化产物之间的边线样本。"
    trigger: "研究提示开始接近台词、分镜或销售话术时。"
    route: "回退为镜头对象、动作、观察点三级结构。"
  - source_gap_id: SG-P0-03-005
    related_subcards:
      - P0-03-RS01
      - P0-03-RS02
    gap_summary: "缺少一套后续 intake 认可的服装品类与版型术语归一表样本。"
    trigger: "同义词、多译名或上下位关系冲突时。"
    route: "先保留上位中性词并记录待决策项。"

decision_required_items:
  - decision_id: DR-P0-03-001
    topic: "RS04 secondary batch 与 batch matrix 的冲突处理"
    detail: "P0-03-RS04 在 subcard 文件中挂有 secondary_batch=batch_012，但 batch allocation matrix 中 P0-03 对 batch_012 计数为 0，需确认该 batch 是否仅作 support-only 引用。"
    severity: high
  - decision_id: DR-P0-03-002
    topic: "颜色模块主归属"
    detail: "颜色既可作为产品属性槽位，也可作为视觉/材料表现模块；需确认后续 intake 的主归属与去重策略。"
    severity: medium
  - decision_id: DR-P0-03-003
    topic: "手感词是否独立建模"
    detail: "手感词兼具主观体验与材料观察属性，需决定是否作为独立子维度，还是始终挂在 claim 边界下。"
    severity: medium
  - decision_id: DR-P0-03-004
    topic: "品质证明抽象层级上限"
    detail: "需确认 general_only 地图是否允许保留证明类型学到何种粒度，以避免逼近真实标准编号或真实证书状态。"
    severity: high

excluded_items:
  - excluded_id: EX-P0-03-001
    object_type: CandidatePack
    reason: "本任务只产出 research map，不进入 CandidatePack 路径。"
  - excluded_id: EX-P0-03-002
    object_type: KEItem
    reason: "Web Deep Research 不写 KE。"
  - excluded_id: EX-P0-03-003
    object_type: ServingProjectionRecord
    reason: "禁止生成 Serving projection。"
  - excluded_id: EX-P0-03-004
    object_type: RAGContextBundle
    reason: "禁止生成 RAG context bundle。"
  - excluded_id: EX-P0-03-005
    object_type: DIFYWorkflow
    reason: "禁止生成 DIFY workflow。"
  - excluded_id: EX-P0-03-006
    object_type: ApprovedPassageText
    reason: "禁止生成 approved_passage_text 或任何 production-ready 文本。"
  - excluded_id: EX-P0-03-007
    object_type: BrandFact
    reason: "general_only 范围内不得写真实品牌事实。"
  - excluded_id: EX-P0-03-008
    object_type: SKUFact
    reason: "general_only 范围内不得写真实 SKU 或商品主数据。"
  - excluded_id: EX-P0-03-009
    object_type: StoreFact
    reason: "general_only 范围内不得写真实门店事实。"
  - excluded_id: EX-P0-03-010
    object_type: PersonFact
    reason: "general_only 范围内不得写真实人物事实。"
  - excluded_id: EX-P0-03-011
    object_type: CustomerFeedbackFact
    reason: "general_only 范围内不得写真实顾客反馈。"
  - excluded_id: EX-P0-03-012
    object_type: PublishableScript
    reason: "可拍摄表达方式只能到研究提示层，不可变成脚本。"

shared_cluster_merge_items:
  - merge_id: SCM-P0-03-001
    cluster_ids:
      - P0-03-RS02-CL03
      - P0-03-RS03-CL01
    shared_with_capability_cards:
      - P0-05
    merge_note: "版型术语与身材效果语言阶梯在后续 intake 可建立共享关系，但当前不合并为正式跨卡 ontology。"
  - merge_id: SCM-P0-03-002
    cluster_ids:
      - P0-03-RS02-CL04
      - P0-03-RS04-CL04
    shared_with_capability_cards:
      - P0-04
    merge_note: "工艺观察线索与可拍摄表达方式可共享为 support-only 展示方法，不能上升为完整陈列系统。"
  - merge_id: SCM-P0-03-003
    cluster_ids:
      - P0-03-RS03-CL02
      - P0-03-RS04-CL03
    shared_with_capability_cards:
      - P0-00
    merge_note: "claim 证据阶梯与品质证明路由可共享规则接口，但须防止 P0-00 控制面泄漏为普通领域知识。"

founder_review_items:
  - review_id: FR-P0-03-001
    topic: 身材效果与敏感表达
    reason: "涉及显瘦、显高、修饰、遮挡等语义时，可能触发身体焦虑或高风险断言。"
  - review_id: FR-P0-03-002
    topic: 品质保证类说法
    reason: "涉及高品质、耐穿、严格质检、做工优越等时，容易越过证据边界。"
  - review_id: FR-P0-03-003
    topic: 认证/检测/标准相关抽象表达
    reason: "即使只做类型学说明，也可能被误读为实例证明，需要高警惕。"
  - review_id: FR-P0-03-004
    topic: 可拍摄表达方式的脚本化风险
    reason: "研究提示可能在下游被误当作可直接发布内容，需保持研究态约束。"

required_execution_asset_types: *common_assets

required_dq_checks: *common_dq

fallback_conditions:
  - "遇到术语冲突时，保留上位中性术语与关系提示，不擅自发明细分事实。"
  - "遇到性能、舒适、耐用、品质、身材效果等高风险 claim 且缺乏证据路径时，只保留边界说明或转 source gap。"
  - "遇到需要真实品牌、SKU、门店、人物、顾客反馈才能成立的知识时，直接 route away，不做 general_only 补写。"
  - "遇到可拍摄表达方式开始趋向脚本、话术、发布文案时，回退为镜头对象、动作、观察点三级提示。"
  - "遇到 batch、ontology ownership、粒度边界不清时，写入 unresolved_decisions，不自行补全。"

blocking_conditions:
  - "任何 readiness-like 字段被写成 true 或暗示已可生产使用。"
  - "任何真实品牌、SKU、门店、人物、顾客反馈或实例事实进入 cluster。"
  - "任何 CandidatePack、KE、Serving、RAG、DIFY、approved passage、publishable script 产物进入输出。"
  - "任何 fabric、fit、body-effect、quality、durability、comfort、performance claim 没有显式 evidence_need。"
  - "任何把 P0-00 控制面知识改写成普通面料、版型、工艺知识的行为。"
  - "任何把 A2 support-only 误写成完整陈列系统的行为。"

unresolved_decisions:
  - "RS04 secondary_batch 与 batch matrix 冲突的解释口径待确认。"
  - "颜色与手感在 P0-03 内的主归属粒度待确认。"
  - "品质证明类型学可保留到何种抽象层级待确认。"
  - "同类比较维度是否需要单独对接 P0-05 的产品角色叙事映射待确认。"

source_gap_seed:
  - "通用服装品类术语与属性槽位归一来源样本"
  - "面料家族术语与性能、舒适、耐用 claim 分离方法来源样本"
  - "版型、廓形术语与中性观察表达转换样本"
  - "工艺节点可视检查方法样本"
  - "品质观察项与证明类型映射样本"
  - "claim 风险分级词表与改写准则样本"
  - "非脚本化可拍摄表达方式边界样本"

self_check:
  required_subcards_covered:
    - P0-03-RS01
    - P0-03-RS02
    - P0-03-RS03
    - P0-03-RS04
  required_subcards_covered_complete: true
  all_clusters_with_required_fields: true
  all_readiness_false: true
  contains_real_brand_or_sku_or_store_or_person_or_customer_fact: false
  contains_candidatepack_or_ke_or_serving_or_rag_or_dify_or_approved_passage: false
  contains_production_ready_text: false
  count_used_as_acceptance_kpi: false
  p0_out_of_scope_added: false
  batches_beyond_batch_014_added: false
  notes_conflicts_in_unresolved_decisions: true
  final_state: research_map_only

forbidden_output_attestation:
  not_candidatepack: true
  not_KE: true
  not_serving_projection: true
  not_RAG_context_bundle: true
  not_DIFY_workflow: true
  not_approved_passage_text: true
  not_publishable_script: true
  not_runtime_artifact: true
  not_route_mutation: true
  not_formal_capability_card: true
  not_registry_write: true

readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_allowed: false
  generation_eligible: false
  production_ready: false
  release_ready: false