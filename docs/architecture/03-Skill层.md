# Skill 层（可插拔领域能力）

> **所属层:** 能力层（四肢）  
> **依赖性:** 可逐个插拔，不影响 Brain 内核  
> **版本:** v3.6
> **验证标准:** 单个 Skill 注册/卸载不影响 Brain 对话能力；Skill 间互不感知  

---

## 1. Skill 的本质

```
Skill = 可插拔的领域能力积木

Skill 拥有:
+-- 自己的业务逻辑
+-- 自己的 prompt 模板
+-- 自己的实体类型定义（注册到 Knowledge Stores）
+-- 自己的 Knowledge Profile（注册到 Resolver）
+-- 自己的 Tool 依赖声明

Skill 不拥有:
+-- 自己的数据库（所有持久化数据在 Knowledge Stores 中）
+-- 自己的记忆管理（由 Brain 的记忆引擎统一处理）
+-- 对话管理能力（对话是 Brain 的固有能力）
+-- 对其他 Skill 的依赖（Skill 之间互不感知）
```

---

## 2. SkillProtocol

```python
class SkillProtocol:
    name: str
    version: str
    capabilities: List[str]
    required_permissions: Set[str]
    required_tools: List[str]

    # Skill 的知识注册声明
    entity_types: List[EntityTypeDefinition]    # 该 Skill 需要的实体类型
    knowledge_profiles: List[ProfileDefinition]  # 该 Skill 需要的 Resolver Profile

    async def execute(
        self,
        intent: Intent,
        context: SessionContext,
        knowledge: KnowledgeBundle,    # Resolver 已按 Profile 组装好的知识包
        tool_registry: ToolRegistry,
    ) -> SkillResult

    async def can_handle(self, intent: Intent) -> float  # 0-1 置信度
```

**SkillResult Schema v1 (v4.4 新增, 05a-API-Contract 对齐):**

```
SkillResult:
  skill_name: string              -- Skill 标识符
  skill_version: string           -- Skill 版本 (内部)
  status: "success" | "partial" | "error" | "rate_limited"
  output: any                     -- Skill 输出 (结构化)
  text_summary: string            -- 人类可读摘要
  tool_calls: ToolCall[]          -- 内部 Tool 调用记录
  error?: { code, message }       -- status=error 时必填

ToolCall:
  tool_name: string               -- Tool 标识符 (引用 04-Tool Section 5)
  tool_version: string            -- Tool 版本
  status: "success" | "error" | "rate_limited"
  input_summary: string           -- 脱敏后的输入摘要
  output_summary: string          -- 脱敏后的输出摘要
  duration_ms: number             -- 执行耗时
  cost_amount?: number            -- 计费金额 (如适用)
  execution_ms: number            -- 执行耗时 (内部)
  metadata?: Dict                 -- 扩展元数据 (内部)

字段暴露分级:
  @api-exposed: skill_name, status, output, text_summary, error
  @api-internal: skill_version, tool_calls, execution_ms, metadata

rate_limited 语义说明:
  Skill-level rate_limited: Skill 自身被限流 (如外部 API 配额耗尽)
  Tool-level rate_limited: Skill 内部某 Tool 被限流，Skill 可能 partial 成功
  区分: status=rate_limited -> Skill 整体未执行;
        status=partial + tool_calls 含 rate_limited -> Tool 级别限流
```

**Experiment Engine 分流切入点（Skill 层）:**

```
实验维度（引用 06 Section 5.2）:
  - Skill 执行策略: Skill 内部流程、工具编排变体

分流接入方式:
  SessionContext 透传 experiment_context（由 Brain 从 OrgContext 转发）:
    context.experiment_context.dimensions.skill_strategy?: string

  切入点 -- execute() 内部:
    if context.experiment_context?.dimensions.skill_strategy:
      使用 variant 对应的执行策略（Tool 调用顺序、并行度、prompt 变体等）
    else:
      使用默认执行策略

  Trace 关联:
    SkillResult.metadata 记录 experiment_id + variant
    通过 trace_id 关联实验指标与 Skill 输出质量
```

**v3.6 多模态能力扩展:**

```
capabilities 新增枚举值:
  "multimodal_input"   -- Skill 可处理多模态输入 (ContentBlock type!=text)
  "multimodal_output"  -- Skill 可生成多模态输出

optional_tools 新增可选项:
  "image_analyze"        -- 图片理解
  "audio_transcribe"     -- 语音转文字
  "document_extract"     -- 文档解析

向后兼容:
  无 multimodal_input/output 能力的 Skill 行为不变
  Brain Skill Router 仅在用户输入包含 ContentBlock (type!=text) 时
  才将 multimodal 能力作为路由条件
  无多模态能力的 Skill 仍可被路由 -> 降级使用 text_fallback
```

---

## 3. Skill 完整生命周期

### 3.1 安装（注册）

```
1. Skill 代码部署到 Skill 目录
2. Brain 扫描 Skill -> 调用 Skill.entity_types -> 注册实体类型到 Knowledge Stores
3. Brain 扫描 Skill -> 调用 Skill.knowledge_profiles -> 注册 Profile 到 Resolver
4. Brain 注册 Skill 到 Skill Registry（capabilities 标签）
5. 完成。Router 自动发现新 Skill。
```

### 3.2 运行

```
1. Brain 意图判断 -> "需要做事" -> Router 匹配 Skill
2. Brain 调用 Resolver 按 Skill 的 Profile 加载知识 -> KnowledgeBundle
3. Brain 调度 Skill.execute(intent, context, knowledge, tools)
4. Skill 内部: 使用 knowledge + 调用 Tool + 执行业务逻辑
5. 结果返回 Brain -> Brain 整合后回复用户
6. Brain 记忆引擎: 从结果中提取观察 -> 写入 Memory Core
```

### 3.3 卸载（拔掉）

```
1. 从 Skill Registry 移除
2. Knowledge Stores 中该 Skill 注册的实体类型标记为 registered_by = "skill:xxx(removed)"
3. 已有数据保留（不删除）
4. Brain 的 Router 不再匹配到该 Skill
5. 当用户请求相关能力时 -> Brain 优雅降级回复

拔掉后:
  [PASS] 对话正常
  [PASS] 记忆正常
  [PASS] 该 Skill 创建的知识仍可被 Brain 在对话中引用
  [FAIL] 不能再执行该 Skill 的专业操作
```

---

## 4. Prompt 管理

> **[裁决 已定稿]** Prompt 模板归属各 Skill，公共能力抽为 shared/prompt_toolkit。Experiment Engine 做 A/B 测试。

---

## 5. 内容生产 Skill（ContentWriterSkill）

```
ContentWriterSkill:
+-- name: "content_writer"
+-- capabilities: ["content_create", "content_refine", "content_matrix"]
+-- required_tools: ["llm_call"]
+-- optional_tools: ["web_search", "image_generate (远期)", "image_analyze", "audio_transcribe", "document_extract"]
|
+-- entity_types:                    <- 注册到 Knowledge Stores
|     Persona（人设）
|     ContentType（内容类型）
|     ContentBlueprint（内容蓝图）
|     Campaign（活动）
|     ContentMatrix（内容矩阵）
|     PlatformAdapter（平台适配）
|
+-- knowledge_profiles:              <- 注册到 Resolver
|     content_production（FK 策略: parallel）
|     brand_compliance（FK 策略: none，纯图谱）
|
+-- execute(intent, org_context, knowledge: KnowledgeBundle):
      注: knowledge 由 Brain 按本 Skill 注册的 profiles 预取后传入。
      Brain 对多 Profile 的处理: 按 knowledge_profiles 列表依次预取，
      合并为单个 KnowledgeBundle（content_production + brand_compliance）。
      Skill 不直接调用 Resolver（见 02 Section 4）。

      1. 解析意图: 确定 ContentType + Platform + Persona
      2. 从 knowledge 中提取内容生产知识:
         +-- 图谱: Persona 配置 + BrandTone + ContentType 约束 + Campaign 信息
         +-- 向量: 品牌知识语义内容 + 区域话术 + 历史优秀作品
         +-- FK 联动: 人设->关联的范例作品向量；产品->关联的卖点描述向量
      3. 组装 Prompt（prompt_toolkit 渲染）
      4. 调用 LLMCall Tool
      5. 从 knowledge 中提取品牌合规规则 -> Brand Compliance Check
      6. 分级审核判定（按 content_policy）
      7. 返回结果
```

### 5.1 ContentType 注册

```
ContentType 实体的 schema:
+-- type_id, name, category, platform
+-- template_structure, constraints
+-- persona_compatible: [String]
+-- tone_profile, evaluation_criteria
+-- prompt_template_ref, knowledge_profile_ref
+-- 关系: (:ContentType)-[:COMPATIBLE_WITH]->(:Persona)
         (:ContentType)-[:TARGETS]->(:PlatformAdapter)

初期注册的内容类型:
+-- xhs_ootd（小红书穿搭日记）
+-- xhs_product_review（小红书产品评测）
+-- xhs_lifestyle（小红书生活方式）
+-- dy_product_short（抖音产品短视频脚本）
+-- dy_vlog_script（抖音 VLOG 脚本）
+-- wechat_article（微信公众号文章）
+-- store_daily（门店日常）
+-- training_material（培训材料）
+-- product_copy_general（通用产品文案）
```

### 5.2 Persona 实体存储示例

```
图谱节点:
  (:Persona {
    graph_node_id: "persona_001",
    name: "时尚买手小A",
    persona_type: "fashion_buyer",
    core_attributes: { personality_traits: [...], speaking_style: "...", ... },
    vocabulary_preferences: { preferred_words: [...], prohibited_words: [...] },
    platform_adaptations: { xiaohongshu: {...}, douyin: {...} },
    owner_org_id: "...",
    visibility: "brand"
  })

关联向量:
  Qdrant entry: {
    vector: embed("时尚买手小A的范例输出: 姐妹们！今天给你们带来一件超绝的..."),
    payload: {
      graph_node_id: "persona_001",    // [FK]
      source_type: "enterprise",
      content_type: "persona_example_output",
      org_chain: [...],
      visibility: "brand"
    }
  }
  // 可以有多个范例输出向量，都 FK 到同一个 Persona 图谱节点
```

### 5.3 分级审核流

```
合规检查结果
+-- 未通过 -> 标注违规点 + 修正建议 -> 返回用户
+-- 通过 -> 查 content_policy
    +-- relaxed  -> 直接可发布
    +-- standard -> 系统自动通过
    +-- strict   -> 进入上级审核队列
```

---

## 6. 陈列搭配 Skill（MerchandisingSkill）

```
MerchandisingSkill:
+-- name: "merchandising"
+-- capabilities: ["outfit_recommend", "display_guide", "training_generate",
|                   "inventory_match", "style_consult"]
+-- required_tools: ["llm_call"]
+-- optional_tools: ["external_api", "image_analyze"]
|
+-- entity_types:                    <- 注册到 Knowledge Stores
|     Product（商品）
|     Category（分类，层级结构）
|     Attribute（属性: 颜色/材质/风格/季节/场合）
|     Collection（系列）
|     StylingRule（搭配规则）
|     DisplayGuide（陈列指南）
|     TrainingMaterial（培训材料）
|
+-- relationships:                   <- 注册到 Knowledge Stores
|     (:Product)-[:BELONGS_TO]->(:Category)
|     (:Product)-[:HAS_ATTRIBUTE]->(:Attribute)
|     (:Product)-[:IN_COLLECTION]->(:Collection)
|     (:Product)-[:COMPATIBLE_WITH {score, pairing_type}]->(:Product)
|     (:Product)-[:AVAILABLE_AT {stock_qty, last_sync}]->(:Store)
|     (:StylingRule)-[:APPLIES_TO]->(:Category)
|     (:StylingRule)-[:USES]->(:Attribute)
|
+-- knowledge_profiles:
|     merchandising_recommend（FK 策略: graph_first）
|     merchandising_training（FK 策略: vector_first）
|
+-- execute():
      场景 1: 搭配推荐
        1. 图谱查询: Product -> COMPATIBLE_WITH -> Products（带库存过滤）
        2. FK 联动: graph_node_ids -> 向量库获取搭配理由/描述
        3. LLM 生成推荐话术

      场景 2: 培训内容
        1. 向量检索: "春季搭配技巧" -> 命中 StylingRule/TrainingMaterial 向量
        2. FK 联动: graph_node_ids -> 图谱获取关联的 Product/Category/Attribute
        3. LLM 生成培训文档
```

### 6.1 Product 实体存储示例

```
图谱节点:
  (:Product {
    graph_node_id: "prod_001",
    name: "双排扣羊毛大衣",
    sku_prefix: "COAT-WL-001",
    owner_org_id: "brand_a",
    visibility: "brand"
  })
  -[:HAS_ATTRIBUTE]-> (:Attribute { type: "color", value: "藏青" })
  -[:HAS_ATTRIBUTE]-> (:Attribute { type: "material", value: "100%羊毛" })
  -[:HAS_ATTRIBUTE]-> (:Attribute { type: "style", value: "经典商务" })
  -[:HAS_ATTRIBUTE]-> (:Attribute { type: "season", value: "秋冬" })
  -[:COMPATIBLE_WITH { score: 0.92, pairing_type: "style_match" }]-> (:Product { name: "直筒西裤" })
  -[:AVAILABLE_AT { stock_qty: 15, last_sync: "2026-02-07" }]-> (:Store { name: "杭州旗舰店" })

关联向量:
  {
    vector: embed("双排扣羊毛大衣，100%澳洲美利奴羊毛..."),
    payload: { graph_node_id: "prod_001", source_type: "enterprise", content_type: "product_description", ... }
  }
  {
    vector: embed("这件大衣的卖点: 1.面料手感极佳 2.版型修身不紧绷..."),
    payload: { graph_node_id: "prod_001", source_type: "enterprise", content_type: "product_selling_points", ... }
  }
```

---

## 7. 新增 Skill 的完整流程

```
以未来的 CustomerServiceSkill 为例:

Step 1: 开发 Skill 代码
  skills/customer_service/
  +-- __init__.py
  +-- skill.py                  实现 SkillProtocol
  +-- prompts/                  prompt 模板
  +-- entity_types/             实体类型定义（YAML）
  |   +-- faq_entry.yaml
  |   +-- faq_category.yaml
  |   +-- service_case.yaml
  +-- profiles/                 Knowledge Profile 定义（YAML）
      +-- faq_search.yaml
      +-- case_analysis.yaml

Step 2: 注册（自动）
  Brain 启动 / 热加载扫描新 Skill
    -> 读取 entity_types/*.yaml -> 注册到 Knowledge Stores
    -> 读取 profiles/*.yaml -> 注册到 Resolver
    -> 注册 Skill 到 Skill Registry

Step 3: 使用
  用户: "客户问这件衣服怎么洗，标准回复是什么？"
    -> Brain 意图判断: 需要做事 -> 匹配 CustomerServiceSkill
    -> Resolver("faq_search") -> 从 Knowledge Stores 查到 FAQEntry
    -> Skill 执行 -> 返回标准话术

Step 4: 学习
  Brain 记忆引擎: 观察到门店经常问洗涤相关问题
    -> 写入 Memory Core (personal/session scope)
    -> 达到阈值 -> Promotion Pipeline: "建议品牌级 FAQ 增加面料护理专题"

全程零核心代码修改。
```

### 7.1 实体类型注册示例

```yaml
# skills/customer_service/entity_types/faq_entry.yaml
entity_type_id: FAQEntry
label: FAQEntry
registered_by: "skill:customer_service"
schema:
  required_properties:
    - { name: question, type: string }
    - { name: answer, type: string }
    - { name: category, type: string }
  optional_properties:
    - { name: related_products, type: array, items: string }
relationships:
  - { type: ANSWERS_ABOUT, target_types: [Product], direction: out }
  - { type: BELONGS_TO_CATEGORY, target_types: [FAQCategory], direction: out }
vector_content_types:
  - { content_type: faq_question, embedding_field: question }
  - { content_type: faq_answer, embedding_field: answer }
visibility_rules:
  default_visibility: brand
org_scope:
  who_can_create: [brand_hq, regional_agent]
  who_can_read: [full_chain]
```

---

## Skill 治理

> **[v3.5 新增]** Skill 治理机制，确保 Skill 生态的健康和可管理性。

### SkillManifest 注册契约

```
SkillManifest（Skill 注册时必须提供的契约格式，见 08 附录 D）:

必填字段:
+-- skill_id: String           唯一标识
+-- name: String               显示名称
+-- version: String            语义版本号
+-- capabilities: List[String] 能力标签（用于 Router 匹配）
+-- entity_types: List[String] 注册的实体类型（写入 Knowledge Stores）

治理字段（v3.5 新增）:
+-- resource_limits:
    +-- max_llm_calls_per_turn: Integer    单次调用最大 LLM 请求数
    +-- max_execution_time_ms: Integer     执行超时（毫秒）
    +-- max_memory_mb: Integer             内存上限
+-- scope_restrictions:
    +-- allowed_org_tiers: List[String]    允许使用的组织层级
    +-- required_permissions: List[String] 所需权限码
+-- deprecation_date: DateTime | null      计划弃用日期（null = 无弃用计划）
```

### Skill 生命周期状态机

```
Skill 状态机:
  draft -> active -> deprecated -> disabled

  draft:       开发中，仅在开发/测试环境可用
  active:      正式上线，Skill Router 可匹配
  deprecated:  标记弃用（deprecation_date 已设置），仍可使用但不推荐
  disabled:    已禁用，Skill Router 不匹配

  状态转换:
  +-- draft -> active:      通过审核（capabilities 和 entity_types 验证）
  +-- active -> deprecated: 设置 deprecation_date
  +-- deprecated -> disabled: 到达 deprecation_date 或手动禁用
  +-- disabled -> active:   重新启用（需要重新审核）

使用统计:
+-- skill_usage_records: 按 skill_id + tenant_id + 日期 聚合
    调用次数 / 成功率 / 平均延迟 / LLM token 消耗
+-- 用于: 弃用决策、性能优化、成本分析
```

---

> **验证方式:** 1) 注册新 Skill 后 Skill Registry 可发现; 2) Skill 的实体类型可被 Knowledge Stores 查询和写入; 3) 卸载 Skill 后 Brain 对话测试仍通过; 4) Skill 之间无直接调用路径; 5) [v3.6] 声明 multimodal_input 的 Skill 可被 Router 在多模态输入时优先匹配; 6) [v3.6] 无 multimodal 能力的 Skill 在多模态输入时仍可降级使用 text_fallback。
