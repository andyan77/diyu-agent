# 对话 Agent 层 (Brain)

> **所属层:** 核心对（Brain + Memory Core）
> **依赖关系:** SSOT-A(Memory Core) 硬依赖；SSOT-B(Knowledge Stores) 软依赖
> **版本:** v3.6
> **验证标准:** 拔掉所有 Skill 和 Knowledge Stores，系统仍能对话、记忆、理解

---

## 1. Brain 的定位

> **[v3.0+ 根本变更]** Brain 不再只是路由器和调度器。Brain 就是对话 Agent 本身——它能对话、能理解、能记忆、能进化。调度 Skill 只是 Brain 的一个子功能。

```
Brain = 对话 Agent 内核

固有能力（不依赖任何 Skill）:
  1. 对话引擎（Conversation Engine）
  2. 意图理解（Intent Understanding）
  3. 记忆引擎（Memory Engine）
  4. 角色适配（Role Adaptation）
  5. 技能调度（Skill Dispatch）—— 仅当需要"做事"时

关键区分:
  能力 1-4 是 Brain 的固有能力，没有任何 Skill 也能运行。
  能力 5 是 Brain 的扩展机制，让 Brain 能借助外部 Skill "做事"。
```

---

## 2. 五大固有能力

### 2.1 对话引擎（Conversation Engine）

**能力:** 多轮对话、上下文追踪、语气适配、主动追问、优雅降级  
**依赖:** LLMCall Tool + Context Assembler

```
对话引擎核心流程:

用户输入
  -> 上下文组装 (Context Assembler):
      +-- system_prompt（角色定义 + 行为指南）
      +-- personal_context（从 Memory Core 加载: 偏好/记忆/历史洞察）
      +-- knowledge_context（从 Knowledge Stores 加载: 企业知识, 可选）
      +-- entity_slots（当前对话追踪的关键实体）
      +-- conversation_history（摘要 + 近期对话）
      +-- user_input（当前输入）
  -> 意图判断:
      +-- 纯对话 -> 直接调 LLMCall Tool 生成回复
      +-- 需要做事 -> 调度 Skill（见 2.5）
  -> 后处理:
      +-- 响应返回用户
      +-- 实体追踪更新
      +-- 触发记忆引擎（异步）

system_prompt 结构化指引（v3.5.1 新增）:
+-- 角色定义 + 行为指南（已有）
+-- Memory-Aware Instruction（记忆使用指引，P0，v3.5.2 增强 Epistemic Tagging）:
    <memory_usage_guide>
    置信度维度:
    confidence >= 0.8 的记忆可直接引用（"您之前提到喜欢..."）
    confidence 0.5-0.8 的记忆用试探性语气（"如果我没记错, 您好像..."）
    confidence < 0.5 的记忆仅作为参考, 不主动提及

    认知类型维度（v3.5.2，见 Section 3.1.0.2）:
    epistemic_type=fact: 作为确定信息直接使用
    epistemic_type=opinion: 标注为用户观点，不作为唯一推荐依据
    epistemic_type=preference: 结合 confidence + recency 决定引用语气
    epistemic_type=outdated: 不主动引用，仅用户追问历史时作为参考

    通用规则:
    若记忆与用户当前发言矛盾, 以当前发言为准
    自然融入回复, 不要逐条复述
    </memory_usage_guide>
    成本: ~250 tokens 固定开销（v3.5.2 增加 ~50 tokens，含 epistemic_type 指引）
+-- Phase-Aware Prompt（对话阶段感知指引，P2）:
    根据 Intent Understanding 分类结果动态调整指引重点:
    开场阶段: "参考用户偏好, 给出个性化问候"
    深入讨论/推荐: "结合历史行为和偏好做个性化推荐"
    任务执行: "精确执行指令, 简洁回复"
    偏好确认: "仔细核对记忆, 逐条确认"
    与 Step 3 动态注入量共享 Intent 分类信号源

对话风格适配（优先从 Knowledge Stores 读取规则，降级使用默认规则）:
+-- org_tier -> brand_hq: 专业战略 / regional_agent: 务实执行 / franchise_store: 友好通俗
+-- role -> owner/admin: 多选项决策支持 / editor/viewer: 直接建议
+-- 个人偏好 -> Memory Core 中的 personal memories
+-- 品牌调性 -> Knowledge Stores 中的 BrandTone 实体（可降级缺省）
```

### 2.2 意图理解（Intent Understanding）

**能力:** 理解用户想做什么、分类为"纯对话"或"需要做事"  
**依赖:** LLMCall Tool

```
意图分类输出:
{
  action_required: Boolean,     // 是否需要调用 Skill
  intent_type: String,          // "chat" | "create_content" | "recommend_outfit" | ...
  confidence: Float,            // 0-1
  extracted_entities: Dict,     // 从输入中提取的关键实体
  context_hints: List[String]   // 辅助 Skill 匹配的上下文提示
}
```

### 2.2.1 Experiment Engine 分流切入点（Brain 层）

```
实验维度（引用 06 Section 5.2）:
  - Brain 路由策略: 意图分发、Skill 选择逻辑
  - Prompt 版本: system_prompt 模板变体

分流接入方式:
  Brain 在 OrgContext 中读取 experiment_context（05-Gateway Section 4 OrgContext 组装时注入）:
    experiment_context: {
      experiment_id: UUID,
      variant: string,           -- "control" | "treatment_a" | "treatment_b" | ...
      dimensions: {
        brain_routing?: string,  -- 路由策略变体标识
        prompt_version?: string  -- prompt 模板版本标识
      }
    } | null                     -- null = 当前无实验分流

  切入点 1 -- 意图分类:
    if experiment_context.dimensions.brain_routing:
      使用 variant 对应的路由策略（Skill 选择权重、分类阈值等）
    else:
      使用默认路由策略

  切入点 2 -- system_prompt 组装:
    if experiment_context.dimensions.prompt_version:
      从 Prompt Registry 加载 variant 对应的 prompt 模板
    else:
      使用默认 prompt 模板

  Trace 关联:
    experiment_id + variant 写入 generation_metadata（06 Section 4）
    通过 trace_id 关联实验指标与对话质量
```

### 2.3 记忆引擎（Memory Engine）

> **[裁决]** 自建。记忆是核心差异化能力。借鉴 Zep 的时序知识管理设计。

**记忆引擎是 Brain 和 SSOT-A（Memory Core）之间的桥梁——Brain 产生观察数据，记忆引擎将其分析、进化后写入 Memory Core。**

```
记忆级别（两级，全部存储在 Memory Core 中）:

| 级别 | 存储位置 | 写入方式 |
|------|---------|---------|
| 会话记忆 (session) | 内存（Session），结束后归档为事件 | 自动 |
| 个人记忆 (personal) | Memory Core 持久化 | Observer -> Analyzer -> Evolver 自动进化 |

注意: store/region/brand/global 级别的知识属于 Knowledge Stores (SSOT-B)，
不在 Memory Core 中。跨域提案通过 Promotion Pipeline 处理。

Promotion Candidate 触发阈值（跨域提案最小门槛）:
  +-- candidate_confidence >= 0.75
  +-- frequency_30d >= 3（30 天内被命中/验证次数）
  +-- source_session_count >= 2（至少来自 2 个独立会话）
  +-- epistemic_type IN {"fact","preference"} 且 != "outdated"
  +-- conflict_ratio < 0.3（与现有企业知识冲突比例）
  满足门槛 -> 进入 EvolutionProposal（Promotion Pipeline）
  不满足门槛 -> 保留在 Memory Core，继续观察

记忆进化流水线:
  Observation（每次对话自动产生）
    -> Analysis（异步，低成本模型）
      -> 识别: 偏好信号、行为模式
        -> Evolution（达到阈值时触发）
          -> Quality Gateway（过滤低质量）
            -> 写入 Memory Core:
                memory_items (versioned, append-mostly)

  负反馈熔断:
    若注入的记忆导致用户负反馈 -> 自动降权/撤销
    防止正反馈毒化循环

  冲突解决双层定位（v3.4 澄清）:
    (1) Context Assembly 热路径冲突（personal_context vs knowledge_context）:
        遵循 ADR-022 硬规则（Knowledge 优先），O(1) 判定，不涉及 LLM 调用。
        见 Section 4.3。
    (2) Memory Evolution 冷路径冲突（memory_items 间的语义矛盾）:
        在 Analysis 阶段（异步，低成本模型）检测并解决。
        如同一偏好出现矛盾版本，由低成本 LLM 判定保留/合并/废弃，
        结果写入新 memory_item（superseded_by 指向旧条目）。
        此路径不影响对话 P95 延迟。

时序管理（每条记忆的元数据）:
+-- valid_at: DateTime       生效时间
+-- invalid_at: DateTime     失效时间（null = 仍有效）
+-- confidence: Float        置信度
+-- source_sessions: [UUID]  来源会话
+-- superseded_by: UUID      被哪条新记忆替代
+-- version: Integer         版本号（支持回滚）
+-- provenance: Object       来源追溯信息
+-- epistemic_type: String   认知类型（v3.5.2 新增，见 Section 3.1.0.2）

Agent Experience Memory（v3.5.2 新增，Phase 2 预留）:

  当前记忆仅记录用户侧信息（偏好、行为、事实）。
  Phase 2 扩展: 记录 Agent 自身的推理经验，用于长期性能优化。

  新增 memory_type 枚举值:
  +-- "agent_experience": Agent 推理经验记忆
      存储内容: 哪些工具调用组合对特定意图有效/无效、
                哪些检索策略对特定用户画像召回率更高、
                哪些推荐策略被用户采纳/拒绝
      写入触发: Evolution Pipeline Analysis 阶段，
                从 injection_receipt + tool_execution_receipt 中提取模式
      消费方式: Context Assembler 在 system_prompt 中注入 Agent 经验提示
                （类似 Memory-Aware Instruction，但面向 Agent 自身决策）

  与用户记忆的隔离:
  +-- memory_items.scope 保持 "session" | "personal" 不变
  +-- agent_experience 通过 item_type="agent_experience" 区分，不污染用户记忆检索
  +-- RLS 策略: agent_experience 按 tenant_id 隔离（非 user_id），
      同租户下所有用户的 Agent 经验共享（组织级学习）

  学术依据:
  Hindsight (2025.12) 区分 World Memory（外部知识）和 Bank Memory（Agent 经验），
  在 LongMemEval 上 OSS 20B 模型 (83.6%) 超越 full-context GPT-4o (60.2%)，
  证实 Agent 经验记忆对长期性能提升显著。

  Phase 2 前置条件:
  +-- injection_receipt utilized + user_feedback_signal 数据积累（Section 4.1.1）
  +-- tool_execution_receipt 体系建立（与 Skill 层协同，见 04）
  +-- 评测集覆盖 Agent 经验注入场景
```

#### 2.3.0.1 Evolution Pipeline CE 增强

> **[v3.5.1 新增]** 在现有 Evolution Pipeline 三阶段（Observation -> Analysis -> Evolution）基础上的工程优化，不改变架构。

```
增强 A: 纠正检测 + 快速通道（Phase 1）

当前: 偏好变更通过 Evolution Pipeline 异步处理（冷路径，分钟级）

增强: 检测到偏好变更信号时走高优先级快速通道:

  用户: "不是运动风, 我现在喜欢简约的"
    -> 纠正检测器（Pattern-based: "不是X,是Y" / "现在喜欢" / "不再" / "换成"）
    -> 高优先级 Observation (priority=urgent)
    -> Evolution Pipeline 快速通道:
       跳过 Analysis 排队, 直接进入 Evolver:
         旧记忆: invalid_at = now(), superseded_by = 新ID
         新记忆: provenance = confirmed_by_user, confidence = 0.9
    -> 秒级生效（不等批量 Evolution 周期）

效果: 偏好变更同会话 + 下一次会话均立即使用新偏好
价值: 在现有 Evolution 架构内通过快速通道解决时效性问题
实现位置: Observer 阶段 + Evolution Pipeline 优先级队列

增强 B: 结构化 Analysis Prompt（Phase 0）

当前: Analysis prompt = "从对话中提取用户偏好"（模糊）

增强为结构化提取指令:
  1. 显式偏好: provenance=confirmed_by_user, confidence 上限 1.0
  2. 隐式偏好: provenance=observation, confidence 上限 0.6
  3. 偏好变更: 标注新旧对比, 标记旧记忆需 invalidate
  4. 约束条件: provenance=confirmed_by_user（如"超过500的不要"）
  5. 无需提取: 闲聊/寒暄等无偏好信号内容
  6. 认知类型标注（v3.5.2 新增，见 Section 3.1.0.2）:
     每条提取结果必须标注 epistemic_type = fact | opinion | preference | outdated
     判定规则: 可验证客观信息 -> fact; 主观评价 -> opinion; 偏好倾向 -> preference

输出: JSON 数组，每条含 type, content, provenance, confidence, epistemic_type, related_existing_memory_id
效果: 与 Provenance 分级（Section 3.1.0.1）+ Epistemic Tagging（Section 3.1.0.2）对齐
实现位置: Evolution Pipeline Analysis 阶段的 prompt 模板

增强 C: Contextual Chunking（上下文化存储，Phase 1）

当前: memory_item.content = "简约风"

增强: 写入时补充上下文前缀:
  memory_item.content =
    "[用户偏好/穿衣风格/2026-01确认] 用户明确表示喜欢简约风格的穿搭"

效果:
  embedding 质量更高（包含类别信息），检索语义匹配更精确
  不会与无关记忆混淆
成本: Evolution Pipeline 写入时多一步格式化（已有低成本 LLM 调用，不增加额外调用）
实现位置: Evolution Pipeline Evolver 阶段写入前

增强 D: Memory Consolidation（记忆合并，Phase 2）

当前: 每次对话产生新 observation，同一偏好可能积累多条相似记忆

增强: Evolver 阶段增加合并逻辑:
  触发条件: 同一 user_id 下语义相似度 > 0.85 的 memory_items 数量 >= 3
  合并结果: provenance=analysis, confidence 综合计算, supersedes 原记忆集
  执行方式: 定期批量检查（Evolution Pipeline 的一部分）

效果: 减少记忆条数，提高检索信噪比
前置条件: pgvector 默认启用（Section 3.2.1）用于相似度计算
实现位置: Evolution Pipeline Evolver 阶段
```

#### 2.3.1 MemoryItem 语义契约 v1

> **[v3.3 新增]** MemoryItem 是 MemoryCorePort.read_personal_memories() 的返回元素，是 Brain 消费记忆数据的契约边界。以下定义构成 schema v1，变更须遵守兼容规则（见 ADR-033）。

```
MemoryItem Schema v1:

字段                 | 类型          | 必填 | 空值语义                      | 说明
memory_id            | UUID          | YES  | 不允许为空                     | 唯一标识
user_id              | UUID          | YES  | 不允许为空                     | 所属用户
memory_type          | String        | YES  | 不允许为空                     | "observation" | "preference" | "pattern" | "summary" | "agent_experience"(Phase 2)
content              | String        | YES  | 不允许为空                     | 记忆内容文本
valid_at             | DateTime      | YES  | 不允许为空                     | 生效时间
invalid_at           | DateTime      | NO   | null = 仍有效                  | 失效时间
confidence           | Float         | YES  | 不允许为空                     | 0.0-1.0 置信度
source_sessions      | List[UUID]    | YES  | 空 List [] = 无关联会话        | 来源会话列表
superseded_by        | UUID          | NO   | null = 当前版本有效            | 替代者 ID
version              | Integer       | YES  | 不允许为空                     | 版本号（>=1）
provenance           | Object        | YES  | 不允许为空                     | 来源追溯信息
epistemic_type       | String        | NO   | null = 视为 "preference"       | v3.5.2 Expand 兼容新增。"fact" | "opinion" | "preference" | "outdated"（见 Section 3.1.0.2）

WriteReceipt Schema v1:

字段                 | 类型          | 必填 | 空值语义
receipt_id           | UUID          | YES  | 不允许为空
memory_id            | UUID          | YES  | 不允许为空（写入的目标记忆）
written_at           | DateTime      | YES  | 不允许为空
status               | String        | YES  | "accepted" | "rejected" | "merged"

兼容规则: 同 KnowledgeBundle（见 02 Section 5.4.1 / ADR-033）
```

> **[v3.4 澄清]** MemoryItem 契约层使用 `memory_id` 作为对外标识（Port 接口消费端视角），Memory Core 内部数据模型和 DDL 使用 `item_id` 作为存储主键。两者是同一实体的不同投影:
>
> - **Brain 侧（消费端）:** 通过 MemoryCorePort 获取 MemoryItem，使用 `memory_id`
> - **Memory Core 侧（实现端）:** 存储表 memory_items 使用 `item_id`
> - **映射:** MemoryCorePort 实现层负责 `item_id` <-> `memory_id` 的双向映射
> - **内部操作（Evolution Pipeline / 删除管线 / 回执）:** 统一使用 `item_id`
>
> 此映射关系不构成 schema v1 的一部分，属于 Port 实现细节。
>
> **[v3.5 补充] 兼容别名弃用期:** 若外部消费方历史代码直接使用 `item_id` 访问 Port 接口，须提供 `item_id` -> `memory_id` 的兼容别名，弃用期为 2 个 minor version（对齐 ADR-034 Expand-Contract deprecation 周期）。弃用期内两个字段名均可使用，弃用期后仅保留 `memory_id`。

#### 2.3.1.1 PK 命名统一迁移路径

> **[v3.5 新增]** 对齐 ADR-033 兼容规则 + ADR-034 Expand-Contract 三阶段迁移策略。

```
Expand-Migrate-Contract 三阶段迁移:

Phase 1 (Expand):
  +-- Port 接口同时接受 memory_id 和 item_id 两个字段名
  +-- 新代码统一使用 memory_id
  +-- 旧代码中 item_id 引用标记 @deprecated

Phase 2 (Migrate):
  +-- 逐模块替换 item_id -> memory_id（Port 消费端）
  +-- CI 增加 lint rule：禁止新增 item_id 引用（Port 层）
  +-- 持续时间: 最多 2 个 minor version

Phase 3 (Contract):
  +-- 移除 item_id 兼容别名
  +-- Port 接口仅接受 memory_id
  +-- Memory Core 内部 DDL 保持 item_id 不变（实现细节）

注意: 此迁移仅影响 Port 接口层命名，不影响 DDL 物理字段名。
```

#### 2.3.2 Memory Quality 度量框架

> **[v3.4 新增]** Memory 质量直接影响对话效果。以下度量框架提供可观测性基础，指标定义遵循 SLI/SLO 规范。

```
统一 7 项 SLI 定义（v3.5 修订，替代原 5 项 SLI，见 ADR-038 amends ADR-036）:

+-- staleness_rate（过期率）[保留]
    分子: invalid_at < now() 且未被物理删除的 memory_items 数
    分母: 同 tenant_id + scope="personal" 的全量 memory_items 数
    窗口: 滚动 7 天快照
    SLO: < 15%
    聚合维度: tenant_id / org_id
    关联 Loop: A (Runtime Governance)

+-- conflict_rate（冲突率）[保留]
    分子: 同 user_id 下存在 superseded_by 链长 >= 3 的条目数
    分母: 同 user_id 的活跃 memory_items 数（invalid_at IS NULL）
    窗口: 滚动 30 天
    SLO: < 10%
    聚合维度: tenant_id
    关联 Loop: A (Runtime Governance)

+-- injection_quality（注入质量）[合并，替代原 injection_hit_rate + user_correction_rate]
    公式: hit_rate * (1 - correction_rate)
      hit_rate = injection_receipt 中 status="accepted" 数 / 全部 injection_receipt 数
      correction_rate = 负反馈熔断触发次数 / 同周期总注入次数
    窗口: 滚动 7 天
    SLO: > 0.55
    聚合维度: tenant_id / org_id
    关联 Loop: A (Runtime Governance), C (Context Assembly)

+-- retrieval_latency_p95（检索延迟 P95）[保留]
    数据源: retrieval_receipt.latency_ms
    窗口: 滚动 1 小时
    SLO: < 200ms
    聚合维度: tenant_id
    关联 Loop: C (Context Assembly)

+-- context_overflow_rate（上下文溢出率）[新增]
    分子: injection_receipt 中 budget_exceeded=true 的记录数
    分母: 同周期内全部 injection_receipt 数
    窗口: 滚动 24 小时
    SLO: < 5%
    聚合维度: tenant_id / org_id
    关联 Loop: C (Context Assembly)

+-- deletion_timeout_rate（删除超时率）[新增]
    分子: tombstones 中 status != "completed" 且 age > legal_profile.deletion_sla 的记录数
    分母: 同周期内全部 tombstones 数
    窗口: 滚动 7 天
    SLO: 0%（零容忍，合规硬指标）
    聚合维度: tenant_id
    关联 Loop: E (Data Lifecycle)

+-- receipt_completeness_rate（回执完整率）[新增]
    分子: 具有完整 details（含五元组或对应 receipt_type 必填字段）的 memory_receipts 数
    分母: 同周期内全部 memory_receipts 数
    窗口: 滚动 24 小时
    SLO: > 99%
    聚合维度: tenant_id
    关联 Loop: all（全局可观测性基础）

告警策略（遵循 Google SRE Multi-Window Multi-Burn-Rate 模式）:
+-- 快速消耗告警: 1h 长窗口 + 5m 短窗口，burn rate >= 14.4x -> 立即告警
+-- 缓慢消耗告警: 6h 长窗口 + 30m 短窗口，burn rate >= 6x -> 工单告警
+-- 短窗口为长窗口的 1/12（Google SRE Workbook 推荐比例）
+-- 低流量最小样本量阈值: 窗口内样本数 < 30 时，告警降级为 OBSERVE（不触发 PagerDuty），
    避免冷启动和低流量租户的假阳性

时间衰减:
+-- confidence 存储值不自动衰减（避免系统行为不可预测）
+-- 检索排序时计算 confidence_effective = confidence * decay_factor（见 Section 2.3.2.4）
    原始值不变，但排序行为等效于衰减
    此变更记录于 ADR-042.2 (CE Retrieval Optimization)
+-- 与 invalid_at 的关系:
    invalid_at 处理"已确认失效"的记忆（硬淘汰）
    decay_factor 处理"可能过时但未确认"的记忆（软降权），两者互补
+-- 长期未命中的记忆在 retrieval_receipt 中体现为 miss_count 递增
     -> 达到阈值时由 Evolution Pipeline 评估是否标记 invalid_at

治理规则:
+-- staleness_rate > 20%: 触发异步清理 Job（标记 invalid_at）
+-- conflict_rate > 10%: 触发 LLM conflict resolution batch（Evolution Pipeline）
+-- 所有阈值可通过 org_settings 按租户配置
```

#### 2.3.2.1 评测集与发布门禁

> **[v3.5 新增]** injection_quality 和 retrieval_latency_p95 需要评测集驱动的持续验证。

```
评测集分阶段门槛:
+-- Phase 0: 200 条标注样本（最小可行评测集）
+-- Phase 1: 500 条标注样本（覆盖长尾场景）
+-- Phase 2: 1000+ 条标注样本（统计显著性保障）

precision/recall 双轨发布门禁:
+-- 注入策略变更前，必须在评测集上同时满足:
    precision >= 阈值（避免噪声注入）
    recall >= 阈值（避免遗漏关键记忆）
+-- 具体阈值由 Phase 决定（Phase 0 宽松，逐步收紧）
+-- 不通过门禁的变更不允许发布

Experiment Engine 联动:
+-- 注入策略变更必须通过 Experiment Engine 灰度发布（见 06 Section 5, ADR-023）
+-- 预算算法变更（Section 4.2.1）同样强制走 Experiment Engine
+-- 灰度期间 injection_quality SLI 作为护栏指标，低于阈值自动回滚
```

#### 2.3.2.2 数值化验收标准

> **[v3.5 新增]** 11 项数值化验收标准，覆盖 Memory Quality 全链路。

```
验收标准（三态判定: PASS / FAIL / OBSERVE）:

| #  | 指标                        | PASS 条件             | FAIL 条件              | OBSERVE 条件           |
|----|---------------------------|----------------------|----------------------|----------------------|
| 1  | staleness_rate            | < 15%                | > 25%                | 15%-25%              |
| 2  | conflict_rate             | < 10%                | > 15%                | 10%-15%              |
| 3  | injection_quality         | > 0.55               | < 0.40               | 0.40-0.55            |
| 4  | retrieval_latency_p95     | < 200ms              | > 500ms              | 200ms-500ms          |
| 5  | context_overflow_rate     | < 5%                 | > 15%                | 5%-15%               |
| 6  | deletion_timeout_rate     | 0%                   | > 0%                 | N/A（零容忍）           |
| 7  | receipt_completeness_rate | > 99%                | < 95%                | 95%-99%              |
| 8  | Evolution Pipeline 吞吐     | > 100 items/min      | < 20 items/min       | 20-100 items/min     |
| 9  | tombstone 完成时间            | < 15 工作日（默认 SLA）  | > SLA                | > 80% SLA            |
| 10 | injection_receipt 五元组完整性  | 100% 字段非 null       | < 95%                | 95%-100%             |
| 11 | Memory Core HA 切换         | RTO < 30s, RPO < 1s | 超出 SLA              | 接近 SLA 80%          |

灰区处理规则:
+-- OBSERVE 状态: 不阻断发布，但必须创建跟踪 Issue
+-- 连续 3 个版本 OBSERVE 同一指标: 升级为 FAIL 阻断
+-- 所有判定结果写入发布报告，审计可追溯
```

#### 2.3.2.3 MemoryGovernor 组件

> **[v3.5 新增, Phase 1 预留]** 将治理规则（staleness_rate > 20% 触发清理、conflict_rate > 10% 触发 LLM resolution 等）封装为独立 MemoryGovernor 组件，与 ContextAssemblyPipeline 的 Stage 分解协同设计。

```
MemoryGovernor:
  职责: 封装 Memory Quality 治理逻辑，与业务路径解耦
  输入: SLI 实时指标 + org_settings 配置
  输出: 治理动作（清理 Job / LLM resolution batch / 告警升级）

  与 ContextAssemblyPipeline 的关系:
  +-- ContextAssemblyPipeline 负责"读"路径（组装上下文）
  +-- MemoryGovernor 负责"治"路径（质量治理）
  +-- 两者共享 SLI 数据源，但执行路径独立
  +-- Phase 1 实现: 独立组件，定时触发
  +-- Phase 2 演进: 可能与 Event Mesh 集成（事件驱动触发）
```

#### 2.3.2.4 Confidence Effective 计算（检索时衰减）

> **[v3.5.1 新增]** 检索排序时动态计算有效置信度，不修改 Memory Core 存储值。

```
confidence_effective = confidence * decay_factor(days_since_last_validated)

decay_factor:
  0-30 天:  1.0  (不衰减)
  30-90 天: 0.85
  90-180 天: 0.6
  180+ 天:  0.3

last_validated 定义:
  +-- 用户显式确认 (provenance 升级为 confirmed_by_user)
  +-- 注入后被利用且用户正面反馈 (utilized=true + positive signal)
  +-- 注入后用户未纠正: 中性，不刷新 last_validated

计算位置: Context Assembler Step 1 Reranking 阶段（见 Section 4.1）
存储影响: 零（原始 confidence 不变，confidence_effective 仅用于排序）
```

#### 2.3.2.5 Confidence Calibration（Evolution 主动校准）

> **[v3.5.1 新增, Phase 2]** 利用 injection_receipt 的反馈数据主动校准 confidence 存储值。

```
校准逻辑（定期批量，Evolution Pipeline 的一部分）:

统计每条 memory_item 的注入表现:
  injection_count: 被注入次数
  positive_rate: 注入后正面反馈占比
  correction_count: 被用户纠正次数

校准规则:
  injection_count >= 10 且 positive_rate > 0.8:
    confidence = min(confidence + 0.1, provenance 上限)

  injection_count >= 5 且 correction_count >= 2:
    confidence = max(confidence - 0.15, 0.1)

  injection_count >= 5 且 positive_rate < 0.3:
    confidence = max(confidence - 0.2, 0.1)
    若 confidence < 0.2 -> 标记为候选淘汰

与 Decay 的关系:
  Decay (2.3.2.4): 被动衰减（时间维度），检索时计算，不改存储值
  Calibration (本节): 主动校准（反馈维度），修改存储值，需数据积累

前置条件: injection_receipt utilized 字段 + 隐式反馈数据积累（Section 4.1.1）
实现位置: Evolution Pipeline 定期校准 Job
Phase: P2（需 injection_receipt 数据积累）
```

---

### 2.4 角色适配（Role Adaptation）

```
角色适配的数据来源（按优先级）:

1. Knowledge Stores 中的规则（若可用）:
   +-- RoleAdaptationRule 实体
   +-- BrandTone 实体
   +-- PlatformTone 实体

2. Memory Core 中的个人偏好（始终可用）:
   +-- UserPreference 类型的 memory_items

3. 默认规则（硬编码兜底）:
   +-- 按 org_tier 的默认语气映射

降级行为:
  Knowledge Stores 不可用时:
    角色适配退化为: Memory Core 个人偏好 + 默认规则
    记录 degraded_reason: "knowledge_stores_unavailable"
```

### 2.5 技能调度（Skill Dispatch）

```
技能调度流程（仅当意图判断为"需要做事"时触发）:

意图分类结果: { action_required: true, intent_type: "create_content", ... }
  -> Skill Registry 查询:
      +-- 遍历已注册 Skill 的 capabilities 标签
      +-- 每个匹配 Skill 调用 can_handle(intent) -> 置信度 0-1
      +-- 选择最高置信度（阈值 0.3+）
  -> 找到 Skill:
      +-- 权限检查: role + org_tier + skill_whitelist
      +-- Tool 依赖检查: Skill 依赖的 Tool 是否可用
      +-- 参数组装: org_context + 用户输入 + Context Assembler 输出
      +-- 调度执行 -> 结果返回 Brain -> 整合后回复用户
  -> 未找到:
      +-- Brain 直接回复（优雅降级）:
          "关于这个需求，我目前的能力还覆盖不到，但我可以和你聊聊..."
```

### 2.6 Task Orchestration（Phase 2 预留）

> **[v3.5 新增, Phase 2 预留]** Brain 第 6 个扩展能力槽位。与 Skill Dispatch（同步"做一件事然后返回"）不同，Task Orchestration 是异步长任务编排。

```
Task Orchestration（Phase 2 预留）:
  场景: 异步启动 -> 进度跟踪 -> 中间结果交付 -> 结果通知

  与 Skill Dispatch 的区别:
  +-- Skill Dispatch: 同步调用，等待返回，适合秒级操作
  +-- Task Orchestration: 异步启动，适合分钟/小时级操作
      例: "帮我分析上周的所有客户反馈" -> 启动 -> 中间进度 -> 最终报告

  接口预留（不实现）:
  +-- start_task(intent, params) -> task_id
  +-- get_task_status(task_id) -> TaskStatus
  +-- get_task_result(task_id) -> TaskResult（部分/完整）
  +-- cancel_task(task_id) -> CancelReceipt
```

---

## 3. SSOT-A: Memory Core

> Memory Core 是 Brain 的心脏，硬依赖。挂了 = 系统不可用。

### 3.1 数据模型

```
Memory Core 管理的数据:
+-- conversation_events       对话事件流（append-only）
+-- memory_items              个人偏好/行为模式（versioned）
+-- session_summaries         会话摘要
+-- receipts                  检索回执/注入回执
+-- tombstones                删除标记（GDPR/PIPL 合规）

memory_items 结构:
+-- item_id: UUID
+-- user_id: UUID
+-- tenant_id: UUID
+-- scope: "session" | "personal"
+-- item_type: String          "preference" | "behavior_pattern" | "insight" | "agent_experience"(Phase 2)
+-- content: JSONB             记忆内容
+-- confidence: Float          置信度
+-- version: Integer           版本号
+-- valid_at: DateTime
+-- invalid_at: DateTime       失效时间
+-- superseded_by: UUID        被替代的条目
+-- source_sessions: [UUID]    来源会话
+-- provenance: JSONB          来源追溯
+-- created_at / updated_at
```

#### 3.1.0.1 Provenance 可信度分级

> **[v3.5 新增]** memory_items.provenance 字段的可信度分级规则，用于 Context Assembler 注入排序和 Evolution Pipeline 冲突仲裁。

```
Provenance 可信度分级（由低到高）:

+-- observation（低）: 单次对话自动提取的观察
    置信度上限: 0.6
    典型来源: 记忆引擎 Observation 阶段

+-- analysis（中）: 多次观察聚合分析的结论
    置信度上限: 0.8
    典型来源: 记忆引擎 Analysis -> Evolution 阶段

+-- confirmed_by_user（高）: 用户显式确认/纠正后的记忆
    置信度上限: 1.0
    典型来源: 用户反馈界面 / 负反馈熔断后的用户修正

补充规则:
+-- 声明性记忆（用户说"我喜欢..."）置信度上限低于行为性记忆（多次行为模式）
    声明性记忆 provenance=observation: 置信度上限 0.5
    行为性记忆 provenance=analysis: 置信度上限 0.8
+-- Evolution Pipeline 冲突仲裁时，高可信度等级胜出
+-- 同等级时，较新的记忆胜出（valid_at 比较）
```

#### 3.1.0.2 Epistemic Tagging（认知类型标记）

> **[v3.5.2 新增, Phase 0]** 在 Provenance 可信度分级（Section 3.1.0.1）基础上，为每条记忆增加认知类型维度。Provenance 回答"这条记忆从哪来、多可信"，Epistemic Tagging 回答"这条记忆是什么性质的知识"。两者正交互补，共同指导 Memory-Aware Instruction 的使用策略。

```
epistemic_type 枚举（memory_items 新增字段，DDL 见 06 Section 9）:

+-- fact: 客观事实（如"用户身高 175cm"、"上周买了羊毛大衣"）
    特征: 可验证、不随时间/语境变化
    Memory-Aware Instruction 策略: 可直接引用，无需试探

+-- opinion: 主观评价（如"觉得这款裙子太长了"、"认为价格偏贵"）
    特征: 用户主观判断，可能随场景变化
    Memory-Aware Instruction 策略: 引用时标注为用户观点，不作为推荐依据的唯一来源

+-- preference: 偏好倾向（如"喜欢简约风"、"不喜欢鲜艳颜色"）
    特征: 相对稳定但可被更新，是个性化推荐的核心信号
    Memory-Aware Instruction 策略: 结合 confidence + recency 决定引用语气

+-- outdated: 已知过时但未被新记忆替代（如"去年喜欢运动风"但今年无新偏好信号）
    特征: 由 Evolution Pipeline 标记，或 confidence_effective 衰减至阈值后自动标记
    Memory-Aware Instruction 策略: 不主动引用，仅在用户追问历史偏好时作为参考

默认值: preference（向后兼容，存量记忆不标注 epistemic_type 时视为 preference）

与 Provenance 的关系:
  Provenance = 来源维度（从哪来）: observation / analysis / confirmed_by_user
  Epistemic Type = 性质维度（是什么）: fact / opinion / preference / outdated
  两者独立标注，组合使用。例:
    provenance=confirmed_by_user + epistemic_type=fact -> 高可信事实，直接引用
    provenance=observation + epistemic_type=opinion -> 低可信观点，仅作参考

标注方式:
  +-- Evolution Pipeline Analysis 阶段的结构化提取指令（Section 2.3.0.1 增强 B）
      中增加 epistemic_type 分类维度
  +-- 快速通道（Section 2.3.0.1 增强 A）中用户显式纠正的记忆
      默认标注为 fact 或 preference（由纠正检测器根据内容判定）

学术依据:
  Hindsight (2025.12) 区分 World Memory / Opinion Memory，
  证实认知类型区分对长期记忆检索质量有显著提升（LongMemEval 91.4%）。
  本设计将其简化为 4 类枚举，适配 DIYU 的零售场景。
```

### 3.1.1 PIPL/GDPR 删除管线

> **[v3.4 新增]** 用户有权删除自己的记忆（见 07 Section 5.2）。删除管线复用现有 tombstone 语义（Section 3.1）和 Outbox Level 1 投递机制（06 Section 6.2）。内部操作统一使用 `item_id`（映射关系见 Section 2.3.1 ID 映射说明）。

```
删除范围矩阵:

存储位置               | 逻辑删除方式                        | 物理删除方式              | 物理删除时机
memory_items           | invalid_at = now() + tombstone 记录 | DELETE FROM memory_items  | 异步 Worker
conversation_events    | 关联 tombstone 记录                  | content 字段置为 null     | 异步 Worker（保留事件骨架用于审计）
session_summaries      | 关联 tombstone 记录                  | content 字段置为 null     | 异步 Worker
Qdrant personal_proj.  | N/A（无独立逻辑删除）                | 按 user_id 过滤删除 points | 异步 Worker
Redis 缓存             | N/A                                  | 按 user_id 前缀清除       | 同步（tombstone 时顺带）
memory_receipts        | 不删除                               | 不删除                    | 永久保留（脱敏: 仅保留统计字段）

删除流程:

  Step 1（同步）: API 请求 -> 验证 user_id 所有权 -> 创建 tombstone
    +-- 写入 tombstones 表: (tombstone_id, user_id, scope, requested_at, status="requested")
    +-- tombstone 8 态状态机（v3.5 修订，见 ADR-039 amends ADR-037）:
        requested -> verified -> tombstoned -> queued -> processing
          -> completed（终态）
          -> failed -> retry_pending -> escalated（异常路径）
    +-- Redis 缓存按 user_id 前缀清除，必须在 tombstone 创建事务内同步执行
       （异步清除会导致删除后短期内用户仍可见已删数据，违反 PIPL "立即不可见" 要求）
    +-- 标记后: 所有读取路径过滤 tombstone 关联数据，对用户立即不可见

  Step 2（同步，同事务）: 写入 event_outbox
    +-- event_type: "memory.erasure_requested"
    +-- aggregate_id: user_id
    +-- payload: { item_ids, scope, requested_at, retention_policy, tombstone_id }
    +-- idempotency_key: "erasure:{user_id}:{tombstone_id}"（防重复投递）
    +-- 复用 Level 1 关键事件保障（见 06 Section 6.2）

  Step 3（异步）: Physical Deletion Worker
    +-- Outbox poller 投递 -> Worker 消费
    +-- Worker 幂等检查: 按 idempotency_key 查 inbox 表，已处理则跳过
    +-- 按删除范围矩阵逐存储执行物理删除/内容置 null
    +-- 删除完成后写 audit_event（保留: user_id, deletion_time, item_count, 不保留内容）
    +-- 更新 tombstone.status = "completed"

  Step 4: 审计留存
    +-- audit_event 永久保留（证明执行了删除）
    +-- tombstones 表永久保留（标记 status 和完成时间）
    +-- 原始内容不可恢复（物理删除/置 null = 真删除）

竞态防护（v3.5 修订: 全局 fence 按 user_id 分片）:

  Deletion Fence 语义:
  +-- 定义: 一个 user_id 维度的逻辑栅栏，确保"删除中"的用户不会有新数据写入
  +-- 实现: 按 user_id 分片，避免全局锁热点（高并发场景下不同用户的删除互不阻塞）
  +-- 检查时机: Evolution Pipeline 写入 memory_items 前

  Evolution Pipeline 写入 memory_items 前，检查目标 user_id 的 Deletion Fence:
    +-- fence 存在（tombstone.status IN ('requested','verified','tombstoned','queued','processing')）
        -> 丢弃本次写入，记录 evolution_blocked_by_erasure 事件
    +-- fence 不存在 -> 正常写入

合规约束（v3.5 修订: SLA 从硬编码改为 legal_profile 可配置，见 ADR-039）:
+-- 默认 SLA: 15 工作日（legal_profiles.deletion_sla，可按 profile 配置）
+-- SLA 计算: 根据 legal_profiles.sla_type 区分工作日/自然日
+-- 告警触发: 基于 legal_profiles.alert_thresholds 配置:
    warn_pct=25%: 剩余 SLA < 25% 时 -> 工单告警
    critical_pct=10%: 剩余 SLA < 10% 时 -> PagerDuty 告警
+-- Worker 超过 SLA 未完成 -> tombstone.status 升级为 "escalated"
+-- 删除确认: 返回 deletion_receipt（receipt_id, item_count, estimated_completion）
+-- 不可删除: audit_events / tombstones / 脱敏后的 memory_receipts
+-- legal_profiles 配置详见 06 Section 8 DDL 定义
```

### 3.2 存储选型

> **[裁决]** PostgreSQL（与业务数据同实例），WAL 模式，append-mostly 友好。

```
优势:
+-- 事务保证（ACID）
+-- 与业务 PG 共享运维
+-- FTS 支持（pg_trgm + tsquery）
+-- pgvector 扩展支持（语义向量检索，同库同事务，见 Section 3.2.1）
+-- 时序查询友好（valid_at/invalid_at 索引）
+-- append-mostly 友好（memory_items 有 invalid_at 和 superseded_by 语义更新，非严格 append-only）

Memory Core 不使用 Neo4j/Qdrant:
+-- Memory Core 的数据是线性时序的，不需要图推理
+-- 个人记忆的语义检索需求通过 pgvector 扩展默认支持（同库内嵌）
+-- Qdrant personal_projection 作为 Day-2 性能增强选项（高量级场景外部向量库扩展）
```

#### 3.2.1 pgvector 向量检索能力（默认启用）

> **[v3.5.1 新增, ADR-042]** 个人记忆向量检索从"可选增强"调整为"默认启用，可降级"。

```
决策变更:

当前架构:
  PG memory_items (硬依赖) + Qdrant projection (软依赖，可选增强)

调整为:
  PG memory_items (持久真值源, ACID 保证, 硬依赖)
    +
  pgvector 扩展 (向量检索能力, 同库内嵌, 默认启用)

  故障语义:
    pgvector 正常: Hybrid Retrieval (FTS + 向量)
    pgvector 异常: 降级为 FTS-only, 记录 degraded_reason: "pgvector_unavailable"
    系统不停服 (Memory Core 故障域 = PostgreSQL 实例, 不因扩展异常而扩大)

  Qdrant personal_projection -> Day-2 性能增强选项 (当 pgvector 在百万级以上数据量性能不足时考虑)

依据:
  +-- pgvector 与 memory_items 同库同事务, 零额外组件, 一致性天然保证
  +-- pgvector 性能对 V1 量级 (百万级以内) 足够
  +-- 降级策略对齐 Section 2.4 现有模式 (degraded_reason 语义)

向量定位区分:
  +-- pgvector: Memory Core 内嵌向量能力（个人记忆语义检索，PG 同库）
  +-- Qdrant enterprise: Knowledge Stores 向量侧（企业知识语义检索，独立服务）
  +-- Qdrant personal_projection: Day-2 外部向量库扩展（个人记忆高性能语义检索）
  三者职责不交叉，层间边界不变
```

### 3.3 Qdrant 个人记忆语义投影（Day-2 性能增强）

```
Qdrant 中的 personal_projection:
+-- source_type: "personal_projection"（区别于 "enterprise"）
+-- 从 Memory Core 的 memory_items 异步投影
+-- 丢了可从 Memory Core 重建（仅此场景叫投影）
+-- 用于增强 Brain 对个人记忆的语义检索能力

payload 约束:
+-- source_type: "personal_projection"
+-- tenant_id: UUID
+-- user_id: UUID
+-- memory_id: UUID              FK -> Memory Core（v3.5 修订: 由 memory_item_id 更名，
                                 弃用期 2 个 minor version，对齐 Section 2.3.1.1 Expand-Contract）
+-- embedding_model_id: String
+-- normalizer_version: String
```

---

## 4. Context Assembler（Brain 内部组件）

> **唯一同时读取两个 SSOT 的组件。** 这是"隐私硬边界"实现的关键：Knowledge Stores 永远不直接读 Memory Core。
>
> **[v3.5 风险标注]** Context Assembler 当前作为单体 Pipeline 存在（extract/rank/assemble/budget 串联执行），存在可测试性和可替换性风险。标记 P1 考虑拆分为独立 Stage（每个 Stage 可独立测试/替换/Mock）。
>
> **[v3.5 v1 约束]** v1 保持函数级拆分（extract/rank/assemble/budget 纯函数），不做微服务化。Pipeline 复杂度通过单元测试覆盖，非服务拆分。

### 4.1 组装流程

```
Context Assembler (只读组装器):

Step 0.5 (v3.5.1 新增, v3.5.2 优先级调整 Phase 1 -> Phase 0): Query Rewriting（查询改写）
  +-- 用户原话（如"帮我推荐一套今天穿的"）通过低成本 LLM 改写为多个检索查询:
      -> "用户穿衣偏好" / "最近喜欢的风格" / "体型/场景/季节偏好"
  +-- 改写后的多个 query 分别送入 Step 1 检索，合并结果
  +-- 成本: 一次小模型调用 (~100 tokens)，可缓存相似查询
  +-- 效果: 模糊查询召回率显著提升
  +-- 降级: 改写失败 -> 使用原始 query，记录 degraded_reason: "query_rewrite_failed"
  +-- v3.5.2 优先级调整依据:
      检索质量的瓶颈往往在 query 本身而非检索算法（Manus KV-cache 优化实践、
      Supermemory LongMemEval 评测均证实 query 改写对召回率的杠杆效应最高）。
      Query Rewriting 应与 Hybrid Retrieval 同步上线，否则模糊查询场景下
      Hybrid Retrieval 的双路检索仍然无法命中正确记忆。

Step 1 (必须执行): Memory Core 检索
  +-- session window（内存）
  +-- personal memories -- Hybrid Retrieval（v3.5.1 调整）:
      路径 A: pgvector 语义检索 (top_k=20)
      路径 B: FTS 关键词检索 (top_k=20, pg_trgm + tsquery)
      -> RRF (Reciprocal Rank Fusion) 合并排序:
         score(d) = sum(1 / (k + rank_i(d)))  -- k=60 (经验值)
      -> 输出候选集 (top_k=15)
      pgvector 异常时: 降级为 FTS-only, 记录 degraded_reason: "pgvector_unavailable"
  +-- (Day-2) Qdrant personal_projection 语义检索（百万级以上数据量时启用）
  -> 输出: personal_context 候选集
  -> 失败: 系统不可用（硬依赖）

Step 1.3 (v3.5.1 新增): Multi-Signal Reranking（多维信号精排）
  +-- 对 Step 1 输出的 top_k=15 候选记忆做精排:
      final_score = semantic_score            -- 语义相关度（向量距离）
                  * recency_boost             -- 时效性加权
                  * confidence_effective      -- 有效置信度（含衰减，见 2.3.2.4）
                  * provenance_weight         -- 来源可信度（见 3.1.0.1）
                  * frequency_factor          -- 使用频率
  +-- 各因子权重:
      recency_boost: 0-7天 1.2 / 7-30天 1.0 / 30-90天 0.8 / 90+天 0.6
      provenance_weight: observation 0.6 / analysis 0.8 / confirmed_by_user 1.0
      frequency_factor: 注入>=5次且正面率>70% 1.1 / 注入>=5次且正面率<30% 0.7 / 其他 1.0
  +-- 精排后 top_k=5~8 送入 Step 3 组装
  +-- 成本: 零（纯计算逻辑）
  +-- Phase: P0 使用 recency + confidence_effective + provenance;
            P2 启用 frequency_factor（需 injection_receipt 数据积累）

Step 1.5 (v3.5 新增, v3.6 扩展): Sanitization（注入前清洗）
  +-- 对 personal_context 中每条 memory_item.content 执行双重清洗:
      (1) Pattern-based: 正则过滤已知危险模式（prompt injection 模板、SQL/代码片段、超长 token 序列）
      (2) LLM-based: 低成本模型判定内容是否包含操纵性指令（Phase 1 启用）
  +-- v3.6 新增输入来源: 多模态解析结果（OCR 文本、ASR 转录文本、文档提取文本）
      流程: media content -> OCR/ASR/Extract Tool -> 纯文本结果
            -> Step 1.5 Sanitization (Pattern-based + LLM-based)
            -> pass: 注入 Context (附 text_fallback)
            -> blocked: 记录 injection_receipt.sanitization_result, 使用 text_fallback 替代
      设计原则: 不新建清洗管线，复用 Step 1.5 现有能力；新增的是输入来源，不是清洗逻辑
  +-- 清洗结果: pass / sanitized（修改后通过）/ blocked（拦截）
  +-- blocked 记录写入 injection_receipt.sanitization_result
  +-- 不影响 Memory Core 原始数据（只读清洗，不修改源数据）

ContentBlock 在 Brain 中的处理 (v3.6 新增):
  +-- 接收: WS user_message 中可能包含 ContentBlock 数组 (见 05 Section 7.1)
  +-- 存储: 写入 conversation_events.content (content_schema_version=1)
  +-- 读取: Context Assembler Step 1 检索时，按 content_schema_version 分支解析
  +-- 传递: 调用 LLMCallPort 时通过 content_parts 参数传递 (见 05 Section 9)
  +-- 安全: 写入前对每个 media_id 查 security_status，非 safe -> 拒绝整条消息
  +-- 向后兼容: Brain 5 固有能力不受影响（Intent/Entity/Routing/Generation/Evolution）
      ContentBlock 仅影响数据载体格式，不改变推理逻辑
      降级: 不支持多模态的模型 -> 使用 text_fallback

Step 2 (可选增强): Knowledge Stores 检索（若 stores 可用）
  +-- 2a Qdrant enterprise semantic search (source_type=enterprise)
  +-- 2b Neo4j 图谱查询/推理（搭配、继承、约束）
  +-- 2c FK 联动: semantic_hits.graph_node_id <-> neo4j 扩展关系上下文
  -> 输出: knowledge_context
  -> 失败: 降级运行，记录 degraded_reason

Step 3: 合并组装 + 预算分配
  +-- 注入时使用结构化标签界定记忆边界（v3.5 新增，v3.5.1 增强属性，v3.5.2 增加 epistemic_type）:
      <user_memory source="personal" confidence="0.85"
        provenance="confirmed_by_user" valid_since="2026-01-15"
        category="style_preference" epistemic_type="preference">
        用户明确表示喜欢运动风格穿搭
      </user_memory>
      <knowledge source="enterprise" org_tier="brand_hq">...</knowledge>
      标签语义: LLM 可根据 provenance、confidence 和 epistemic_type 自行判断引用语气
      （epistemic_type 定义见 Section 3.1.0.2）
  +-- U-shaped 位置排布（v3.5.1 新增，对抗 Lost-in-the-Middle）:
      位置 1（开头）: 最高相关性记忆
      位置 N（末尾）: 次高相关性记忆
      中间位置: 补充性记忆
      依据: LLM 对首尾位置信息注意力显著高于中间位置
  +-- 动态注入量（v3.5.1 新增，按意图调整 personal_context 预算）:
      闲聊/寒暄: ~500 tokens（仅 1-2 条核心偏好）
      购物咨询/推荐: ~3K tokens（偏好 + 历史购买 + 风格）
      投诉/售后: ~2K tokens（服务历史 + 问题记录）
      知识问答: ~1K tokens（少注入个人记忆，多留给 knowledge）
      偏好确认: ~4K tokens（尽可能多注入相关记忆）
      输入信号: Intent Understanding 分类结果（Brain 固有能力 #2）
  +-- 冲突解决: Knowledge 优先（企业规则 > 个人偏好）
  +-- Token 预算分配
  +-- 写 retrieval_receipt（候选、得分、选中、stores_used、degraded_reason）
  +-- 写 injection_receipt（命中原因、阈值、预算、fail-closed 原因）
  +-- 注入决策后写五元组到 injection_receipt（v3.5 新增，B3 修复）:
      candidate_score:    候选记忆的相关性得分
      decision_reason:    注入/拒绝的决策原因（枚举: relevance/recency/confidence/budget_exceeded/blocked）
      policy_version:     当前注入策略版本号（用于 A/B 实验回溯）
      guardrail_hit:      是否触发护栏规则（布尔 + 规则 ID）
      context_position:   注入在 context 中的位置索引（U-shaped 排布的记录，
                          业界研究证实 LLM 对上下文中间位置的信息注意力下降）
  +-- 字段暴露分级 (v4.4 新增, 05a-API-Contract 对齐):
      @api-exposed (前端可消费):
        decision_reason     -- 记忆决策原因，Memory 面板展示
        context_position    -- 上下文位置，调试面板展示
        utilized            -- 是否被实际使用，反馈信号
        user_feedback_signal -- 用户反馈信号，反馈面板展示
      @api-internal (仅后端内部):
        candidate_score     -- 内部排序分数
        policy_version      -- 策略版本号
        guardrail_hit       -- 安全护栏命中
        utilization_signal  -- 利用率信号 (Brain 内部指标)
```

#### 4.1.1 后处理闭环（生成后信号采集）

> **[v3.5.1 新增]** LLM 生成回复后、Memory 写入前的信号采集环节，为 Evolution Pipeline 和检索排序提供闭环数据。

```
Step A: 记忆利用检测（Phase 2，需 Structured Tags 上线）
  +-- 检测 LLM 回复是否实际引用了注入的记忆:
      关键词匹配（memory content 的核心实体词）
      引用信号（"您之前提到" / "根据您的偏好"）
  +-- 检测结果写入 injection_receipt:
      utilized: Boolean          -- 该记忆是否被实际使用
      utilization_signal: String -- "keyword_match" | "reference_phrase" | "none"
  +-- 未被利用的记忆 = 可能不相关 = 下次检索排序降权

Step B: 隐式反馈捕获（Phase 1 Pattern-based, Phase 2 LLM-based）
  +-- 从用户回复推断记忆有效性（被动采集）:
      "对, 就是这种风格"      -> 记忆命中，confidence 小幅上调
      继续追问/深入讨论        -> 标记 utilized=true
      "不是, 我现在不喜欢了"   -> 触发快速通道（见 Section 2.3.3）
      沉默/转移话题            -> 标记 utilized=false
      复述/纠正                -> confidence 下调
  +-- 信号写入 Observation，进入 Evolution Pipeline
  +-- 初期 Pattern-based（零额外成本），积累数据后评估 LLM-based

Step C: injection_receipt 闭环写入
  +-- 对齐五元组（v3.5），补全后处理字段（v3.5.1 扩展）:
      v3 字段（已有）: candidate_score, decision_reason, policy_version, guardrail_hit, context_position
      v3.1 扩展: utilized, utilization_signal, user_feedback_signal
  +-- v3.1 扩展遵循 Expand 兼容变更规则（ADR-033），新字段可选
  +-- 这些数据是 Confidence Calibration (Section 2.3.2.5) 和 Reranking frequency_factor 的输入
```

> **[v3.5 B7 修复注释]** memory_receipts.details_schema_version 2->3 迁移说明: 注入五元组（candidate_score, decision_reason, policy_version, guardrail_hit, context_position）的加入使 details 结构从 v2 升级到 v3。迁移采用 Expand-Contract 三阶段: (1) Expand: v3 字段以可选方式加入，v2 消费端不受影响; (2) Migrate: 新写入统一使用 v3 格式，旧数据保持 v2; (3) Contract: 2 个 minor version 后移除 v2 兼容逻辑。DDL 变更详见 06 Section 8。

### 4.2 Token 预算分配

```
Token 预算分配:
+-- system_prompt:      ~2K tokens
+-- personal_context:   ~4K tokens（从 Memory Core 读取）
+-- knowledge_context:  ~8K tokens（从 Knowledge Stores 读取，降级时为 0）
+-- entity_slots:       ~1K tokens
+-- summary_blocks:     ~3K tokens
+-- active_window:      ~6K tokens
+-- user_input:         ~2K tokens
+-- generation_budget:  ~4K tokens
```

### 4.2.1 动态预算分配器（Day-2 增强）

> **[v3.4 新增]** 静态分配表（Section 4.2）作为基线和降级回退目标。动态分配器在运行时根据上下文特征弹性调整各 slot 配额。见 ADR-035。

```
DynamicContextBudgetAllocator:
  输入: 静态基线分配 + 运行时信号
  输出: 调整后的各 slot token 配额

运行时信号:
+-- memory_richness: 用户记忆条目数量和质量分布
+-- knowledge_relevance: Knowledge 检索候选的相关性分布
+-- conversation_depth: 当前会话已有轮数
+-- model_context_window: 当前模型的可用窗口大小

不可压缩 slot（v3.5 显式定义）:
  incompressible_slots = {system_prompt, last_user_turn, generation_buffer}
+-- system_prompt:      min 1.5K / max 3K（包含角色定义，不可截断）
+-- last_user_turn:     min 1K   / max 4K（保证用户最近输入完整，即 user_input）
+-- generation_buffer:  min 2K   / max 6K（保证生成质量，即 generation_budget）

可压缩 slot（compressible_slots，按截断优先级排列）:
  compressible_slots = [knowledge_context, summary_blocks, entity_slots, active_window, personal_context]
+-- knowledge_context:  min 0  / max 14K  （默认 ~8K，降级时为 0）-- 最先截断
+-- summary_blocks:     min 1K / max 5K   （默认 ~3K）
+-- entity_slots:       min 0.5K / max 2K （默认 ~1K）
+-- active_window:      min 3K / max 10K  （默认 ~6K）
+-- personal_context:   min 2K / max 8K   （默认 ~4K）-- 最后截断

safety_margin（v3.5 新增）:
+-- safety_margin = max(5% of total_budget, 200 tokens)
+-- 依据: 防止 tokenizer 估算偏差导致实际超窗口，5% 是工程经验安全边界

启动时 fail-fast 检查（v3.5 新增）:
+-- incompressible_total = sum(incompressible_slots.min)
+-- 条件: incompressible_total + safety_margin + min_generation > model_context_window
    -> 抛出 ConfigurationError（配置不合法，无法满足最低要求）
+-- 此检查在服务启动时执行，非运行时

TruncationPolicy 策略模式（v3.5 新增）:
+-- 接口: TruncationPolicy.truncate(slots, available_budget) -> truncated_slots
+-- Phase 0 实现: FixedPriorityPolicy（按上述截断优先级依次压缩）
+-- Phase 1 实现: ConstraintOptimizationPolicy（基于运行时信号的约束求解）
+-- 默认截断优先级: knowledge_context > summary_blocks > entity_slots > active_window > personal_context

分配策略:
+-- 记忆丰富时: personal_context 上浮，压缩 summary_blocks
+-- 知识密集型查询: knowledge_context 上浮，压缩 active_window
+-- 长对话: active_window 上浮，压缩 knowledge_context
+-- 所有分配结果之和 + safety_margin 不得超过 model_context_window

降级回退:
+-- 分配算法异常 -> 退回 Section 4.2 静态基线（硬编码兜底）
+-- 退回后记录 degraded_reason: "budget_allocator_fallback" 到 injection_receipt

审计: 每次分配结果写入 injection_receipt.budget_allocation 字段（见 06 Section 9）
```

> **[v3.5 Phase 2 预留] AssemblyProfile:** 将 Context Assembler 从"每次对话调用一次"重构为"每次 LLM 调用前调用一次"，支持一次对话多次异构 LLM 调用（意图理解用小模型、内容生成用大模型、合规检查用安全模型）。Port 层面非 breaking change。
>
> **[v3.5.1 Phase 2 预留] Intent-Based Model Routing:** 根据 Intent Understanding 分类结果选择不同能力/成本的模型。简单闲聊/确认用快速低成本模型，复杂推荐/追问用强模型。预期降低 30-50% 模型调用成本（闲聊/确认类对话占比通常 > 40%）。降级保护: 快速模型回复触发用户纠正时自动升级。与 05 Section 5.4 "语义路由预留接口"呼应。前置条件: Intent 分类稳定 + 多模型接入能力。

### 4.3 冲突解决规则

```
当 personal_context 和 knowledge_context 发生语义冲突时:

规则: Knowledge 优先（企业规则 > 个人偏好）

示例:
  personal_context: "用户偏好使用网络流行语"
  knowledge_context: "品牌规范禁止使用网络流行语"
  -> 最终: 遵守品牌规范，记录冲突到 injection_receipt
```

### 4.4 性能策略

> **[v3.2 新增]** Context Assembler 是所有对话请求的必经路径，性能策略是架构决策。

```
1. 并行化:
   Step 1 (Memory Core) 与 Step 2 (Knowledge Stores) 并发执行
   +-- 两路请求同时发起
   +-- Memory Core 失败 -> 整体失败（硬依赖语义不变）
   +-- Knowledge Stores 失败/超时 -> 降级，使用已有 personal_context 继续
   +-- Step 2 内部: Qdrant 与 Neo4j 已通过 Resolver fk_strategy=parallel 并行

2. 超时控制:
   +-- Memory Core 查询: 硬超时（SLA 级约定，具体阈值由部署配置决定）
   +-- Knowledge Stores 查询: 硬超时（超时即降级，无企业知识注入）
   +-- 整体 Context Assembly: 硬上限
   +-- 超时时记录 degraded_reason: "knowledge_timeout" 到 injection_receipt

3. 缓存策略:
   +-- Knowledge 查询结果可缓存（品牌调性/角色规则等低变更频率数据）
   +-- Memory Core 查询不缓存（个人记忆实时性要求高）
   +-- 缓存失效: 统一失效入口，覆盖 Knowledge Write API / Promotion 审批 / 批量导入
   +-- cache_version: 按 tenant_id + org_id + profile_id 维度管理版本号
   +-- 任何 Knowledge 变更触发对应 cache_version 递增，命中旧版本的缓存自动失效
```

---

## 5. 上下文窗口管理

```
Session:
+-- session_id: UUID
+-- user_id / org_id
+-- org_context: OrganizationContext
+-- active_window: List[Message]        发送给 LLM 的部分
+-- summary_blocks: List[Summary]       历史摘要块
+-- entity_slots: Dict                  实体记忆槽（常驻上下文）
+-- ttl / created_at / expires_at

窗口管理:
+-- 超阈值 -> 旧消息用低成本模型摘要 -> 追加到 summary_blocks
+-- 从对话提取关键实体 -> 更新 entity_slots
+-- 话题回溯 -> 从 Memory Core / Knowledge Stores 语义检索相关历史 -> 临时注入
```

---

## 5.1 Executor 分区预留（Phase 1）

> **[v3.5 新增, Phase 1 预留]** Brain 内部 Executor 分区，隔离对话热路径和记忆进化冷路径。

```
Brain 内部 Executor 分区:

+-- 对话热路径（同步低延迟）:
    特征: GPU/CPU 密集，P95 < 200ms
    包含: Context Assembly, LLM 调用, 响应生成
    隔离: 独立 asyncio.TaskGroup

+-- 记忆进化冷路径（异步允许延迟）:
    特征: I/O 密集，延迟容忍度高（秒级~分钟级）
    包含: Observation, Analysis, Evolution, Quality Gateway
    隔离: 独立线程池（ThreadPoolExecutor）

实现约束:
+-- Python 实现: asyncio.TaskGroup + 独立线程池
+-- 不拆微服务: 进程内隔离，降低运维复杂度
+-- 线程池/协程层面隔离，共享进程资源
+-- 冷路径积压不影响热路径延迟（背压机制: 队列满时丢弃低优先级 Observation）
```

---

## 6. Ports & Adapters（依赖接口）

```
硬依赖（挂了 = 系统不可用）:
+-- MemoryCorePort
      read_personal_memories(user_id, query) -> List[MemoryItem]
      write_observation(user_id, observation) -> WriteReceipt
      get_session(session_id) -> Session
      archive_session(session_id) -> ArchiveReceipt

软依赖（可拔，降级运行）:
+-- KnowledgePort（层间契约，见 00-总览 12.3 Day 1 Port）
      |
      +-- KnowledgeGraphPort（内部子接口，封装 Neo4j）
      |     query(cypher, params, org_context) -> GraphResult
      |     capabilities() -> Set[Capability]
      |
      +-- VectorStorePort（内部子接口，封装 Qdrant）
            search(query_vector, filter, top_k) -> List[VectorHit]
            capabilities() -> Set[Capability]

      层间 Stub 策略: Day 1 仅实现 KnowledgePort 返回空 KnowledgeBundle；
      真实实现时 KnowledgePort 内部委托 Diyu Resolver 编排两个子接口。

工具调用 Port:
+-- LLMCallPort（v3.6 扩展签名, ADR-046, 详见 05 Section 9）:
      call(prompt: str, model_id: str,
           content_parts: Optional[List[ContentBlock]] = None,  -- v3.6 新增可选参数
           ...) -> LLMResponse
      纯文本: content_parts=None，与现有行为一致
      多模态: content_parts=[ContentBlock,...]，LLMCallPort 实现层解析 media_id -> ObjectRef

重点约束:
+-- Knowledge 适配器必须完全自足（写入/读/审计/权限），不能"回读 Memory Core"
+-- capabilities() + degrade receipts 必须成为协议的一部分（降级可解释）

Phase 2 预留 Port:
+-- BookmarkPort（v3.5 新增预留）:
      场景: 用户"收藏" Knowledge 条目到个人工作备忘
      语义: Knowledge -> Memory 引用通道（不复制数据，只建立引用关系）
      保持隐私硬边界: 不破坏双 SSOT 架构
      bookmark(user_id, knowledge_ref) -> BookmarkReceipt
      list_bookmarks(user_id) -> List[BookmarkRef]
      remove_bookmark(user_id, bookmark_id) -> RemoveReceipt
```

---

> **验证方式:** 拔掉 KnowledgeGraphPort 和 VectorStorePort 的实现（替换为 NoOp stub），Brain 仍应通过所有对话、记忆、理解相关的测试用例。
