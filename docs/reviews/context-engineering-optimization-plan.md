# DIYU Agent Context Engineering 优化方案

> **版本:** v1.1
> **日期:** 2026-02-09
> **基于:** 01-对话Agent层-Brain.md v3.5 + memory-system-upgrade-review-final.md v3.0
> **定位:** 现有架构内的工程优化，不新增组件、不改 Port 契约、不破坏解耦性
> **参考:** Anthropic Context Engineering (2025.09), LangChain Context Engineering (2025.07), Zep SOTA Paper (2025.01)

---

## 0. 核心原则

> "找到最小的高信号 token 集合，最大化期望输出的可能性。" -- Anthropic

本方案不改架构，而是在现有 Context Assembler 管线的 5 个环节中逐一优化信噪比。

---

## 1. 数据流全景

```
用户输入 -> [1.检索] -> [2.组装] -> [3.生成] -> [4.后处理] -> [5.进化]
              |            |           |            |             |
              v            v           v            v             v
          找对记忆     排好上下文    LLM调用    闭环信号采集   生成更好的记忆
```

每个环节的优化方向和具体措施如下。

---

## 2. 环节 1: 检索 -- "找对记忆" (ROI 最高)

### 现状

01 Section 4.1 Step 1:
```
read_personal_memories(user_id, query)
  +-- FTS (pg_trgm + tsquery)
  +-- 精确匹配 (user_id + memory_type)
  +-- 时序过滤 (valid_at/invalid_at)
  +-- (可选) Qdrant personal_projection 语义检索
```

### 问题

用户说"帮我推荐一套今天穿的"，直接搜这句话，FTS 可能什么记忆都命中不了。但该用户上周说过"我最近喜欢运动风"，这条记忆才是关键。

### 优化 1.1: 向量检索从可选升级为默认启用

> **前置决策变更 (ADR-042 级)**

```
当前:
  PG memory_items (硬依赖) + Qdrant projection (软依赖，可选增强)

调整为:
  PG memory_items (持久真值源, ACID 保证, 硬依赖)
    +
  pgvector 扩展 (向量检索能力, 同库内嵌, 默认启用)

  故障语义:
    pgvector 正常: Hybrid Retrieval (FTS + 向量)
    pgvector 异常: 降级为 FTS-only, 记录 degraded_reason: "pgvector_unavailable"
    系统不停服 (Memory Core 故障域 = PostgreSQL 实例, 不因扩展异常而扩大)

  Qdrant personal_projection -> Day-2 性能增强选项 (不变)

依据:
  - 业内零方案把向量当可选 (Letta 用 pgvector, Mem0 用 vector store 做主存储, Zep 图节点自带 embedding)
  - pgvector 与 memory_items 同库同事务, 零额外组件, 一致性天然保证
  - pgvector 性能对 V1 量级 (百万级以内) 足够, Letta 自托管版同方案
  - 降级策略对齐 01 Section 2.4 现有模式 (degraded_reason 语义)
```

### 优化 1.2: Query Rewriting (查询改写)

```
用户原话: "帮我推荐一套今天穿的"
             |
             v
低成本 LLM 一次调用 (约 100 tokens), 改写为多个检索查询:
  -> "用户穿衣偏好"
  -> "最近喜欢的风格"
  -> "体型/场景/季节偏好"
             |
             v
用改写后的多个 query 分别检索, 合并结果

成本: 一次小模型调用 (~100 tokens)
效果: 模糊查询召回率显著提升
实现位置: Context Assembler Step 1 前置处理
```

### 优化 1.3: Hybrid Retrieval + RRF 融合

```
当前: FTS 或 向量, 单路检索

优化为:
  Query -> 并行双路检索:
    +-- 路径 A: pgvector 语义检索 (top_k=20)
    +-- 路径 B: FTS 关键词检索 (top_k=20)
    -> RRF (Reciprocal Rank Fusion) 合并排序
    -> 输出候选集 (top_k=15)

RRF 公式:
  score(d) = sum(1 / (k + rank_i(d)))  -- k=60 (经验值)

成本: 零额外基础设施 (pgvector + pg_trgm 同一 PG 实例)
效果: Anthropic Contextual Retrieval 报告显示 hybrid 比单路向量检索失败率降低 49%
实现位置: MemoryCorePort 实现层
```

### 优化 1.4: Multi-Signal Reranking (多维信号重排序)

```
RRF 合并后的 top_k=15 候选记忆
       |
       v
多维信号精排:

final_score = semantic_score        -- 语义相关度 (向量距离)
            * recency_boost         -- 时效性加权 (近期记忆优先)
            * confidence_effective  -- 有效置信度 (含衰减, 见 5.4)
            * provenance_weight     -- 来源可信度 (见 01:442-467)
            * frequency_factor      -- 使用频率 (常被引用的记忆更可靠)
       |
       v
精排后 top_k=5~8 送入 Context Assembler Step 2

各因子权重:
  recency_boost:
    0-7 天: 1.2
    7-30 天: 1.0
    30-90 天: 0.8
    90+ 天: 0.6

  provenance_weight (对齐 01 Section 3.1.0.1):
    observation: 0.6
    analysis: 0.8
    confirmed_by_user: 1.0

  frequency_factor:
    被注入 >= 5 次且正面反馈率 > 70%: 1.1
    被注入 >= 5 次且正面反馈率 < 30%: 0.7
    其他: 1.0

成本: 零 (纯计算逻辑)
实现位置: Context Assembler Step 1 后置处理
```

---

## 3. 环节 2: 组装 -- "排好上下文"

### 现状

01 Section 4.1 Step 3: 合并组装 + 预算分配
- 结构化标签已有 (v3.5: `<user_memory>`, `<knowledge>`)
- Token 预算静态分配 (4.2) + 动态预算器设计 (review-final P0-3)

### 优化 2.1: 动态注入量 (按意图调整)

```
当前: personal_context 固定 ~4K tokens

优化为: 根据 Intent Understanding (Brain 固有能力 #2) 结果动态调整:

  intent_type          | 注入策略                      | 预算
  闲聊/寒暄            | 仅注入 1-2 条核心偏好          | ~500 tokens
  购物咨询/推荐        | 注入偏好 + 历史购买 + 风格    | ~3K tokens
  投诉/售后            | 注入服务历史 + 问题记录        | ~2K tokens
  知识问答             | 少注入个人记忆, 多留给 knowledge | ~1K tokens
  偏好确认 ("我是不是说过...") | 尽可能多注入相关记忆   | ~4K tokens

依据:
  Context Rot 效应 -- token 越多, 模型对每条信息的注意力越分散
  少而精 > 多而杂 (Anthropic: "smallest possible set of high-signal tokens")

成本: 零 (Intent 判断已有, 只需传递结果给预算分配器)
实现位置: Context Assembler Step 3, 作为动态预算分配器 (review-final P0-3) 的输入信号
```

### 优化 2.2: U-shaped 位置排布 (对抗 Lost-in-the-Middle)

```
当前: 记忆按相关性或时间顺序排入 personal_context

优化为: 利用 LLM 的 U-shaped Attention Bias:
  +-- 位置 1 (开头): 最高相关性的记忆
  +-- 位置 2 (末尾, personal_context 段落最后): 次高相关性的记忆
  +-- 中间位置: 补充性记忆

依据:
  Claude 2.1 中间位置 accuracy 降至 27%, 首尾 > 90%
  review-final.md P0-2 已设计 context_position 五元组字段,
  现在是基于该字段做主动排布策略

成本: 零 (纯排序逻辑)
实现位置: Context Assembler Step 3 的记忆排序逻辑
```

### 优化 2.3: Memory-Aware Instruction (教 LLM 使用记忆)

```
当前 system_prompt: 角色定义 + 行为指南

优化: 在 system_prompt 中新增记忆使用指引:

  <memory_usage_guide>
  以下 <user_memory> 标签内的内容是该用户的已知偏好和历史。
  使用规则:
  - confidence >= 0.8 的记忆可直接引用 ("您之前提到喜欢...")
  - confidence 0.5-0.8 的记忆用试探性语气 ("如果我没记错, 您好像...")
  - confidence < 0.5 的记忆仅作为参考, 不主动提及
  - 若记忆与用户当前发言矛盾, 以当前发言为准
  - 自然融入回复, 不要逐条复述
  - 发现记忆可能过时时, 主动确认 ("您之前提到偏好X, 现在还是吗?")
  </memory_usage_guide>

成本: 零 (~200 tokens 固定开销)
效果: LLM 能区分高/低置信度记忆, 回复语气更自然
实现位置: system_prompt 模板, 与 01 Section 2.4 角色适配协同
```

### 优化 2.4: Structured Tags 增强 (已有基础上细化)

```
01 v3.5 已有:
  <user_memory source="personal" confidence="0.8">...</user_memory>

增强为:
  <user_memory
    source="personal"
    confidence="0.85"
    provenance="confirmed_by_user"
    valid_since="2026-01-15"
    category="style_preference">
    用户明确表示喜欢运动风格穿搭
  </user_memory>

  <user_memory
    source="personal"
    confidence="0.45"
    provenance="observation"
    valid_since="2025-11-20"
    category="brand_preference">
    用户可能对 Nike 品牌感兴趣 (基于单次浏览行为推断)
  </user_memory>

效果:
  - LLM 可根据 provenance 和 confidence 自行判断引用语气
  - 防止 Prompt Injection (结构化标签界定边界, 对齐 01:597-603 Sanitization)
  - 为后处理环节的记忆利用检测提供可解析锚点
```

### 优化 2.5: Phase-Aware System Prompt (对话阶段感知指引)

```
当前: system_prompt 是静态的角色定义 + Memory-Aware Instruction (2.3)

问题: 不同对话阶段对记忆的使用重点不同, 静态指引无法覆盖

优化: 根据对话阶段动态调整 system_prompt 中的指引重点:

  对话阶段         | system_prompt 指引重点
  开场阶段         | "参考用户偏好, 给出个性化问候, 体现你记得这位用户"
  深入讨论/推荐    | "结合用户历史行为和偏好做个性化推荐, 主动关联相关记忆"
  任务执行         | "精确执行用户指令, 简洁回复, 减少闲聊"
  偏好确认         | "仔细核对记忆, 逐条与用户确认, 必要时追问"
  售后/投诉        | "优先引用服务历史, 表达理解, 提供解决方案"

  阶段检测方式:
    +-- 基于 Intent Understanding (Brain 固有能力 #2) 的分类结果
    +-- 与 2.1 动态注入量共享同一信号源, 不重复计算

成本: 零 (阶段检测已有, 只需维护一组 prompt 模板片段)
前置依赖: Intent 分类稳定 (与 2.1 同前置条件)
实现位置: system_prompt 模板, 与 2.3 Memory-Aware Instruction 同层
```

---

## 4. 环节 3: 生成 -- LLM 调用

### 优化 4.1: 生成后记忆利用检测

```
LLM 生成回复后, 检测回复是否实际引用了注入的记忆:

检测方式 (轻量级, 非 LLM 调用):
  对每条注入的 memory_item, 检查回复中是否出现相关语义片段:
    +-- 关键词匹配 (memory content 的核心实体词)
    +-- 回复中是否有 "您之前提到" / "根据您的偏好" 等引用信号

检测结果写入 injection_receipt:
  +-- utilized: Boolean     -- 该记忆是否被实际使用
  +-- utilization_signal: String  -- "keyword_match" | "reference_phrase" | "none"

价值:
  - 未被利用的记忆 = 可能不相关 = 下次可以不注入 (减少 context rot)
  - 利用率数据是优化检索排序的直接反馈信号

实现位置: Context Assembler 或 Brain 对话引擎的后处理钩子
```

### 优化 4.2: Intent-Based Model Routing (意图驱动模型路由)

```
当前: 所有对话轮次使用同一模型

优化: 根据意图分类选择不同能力/成本的模型:

  意图类型              | 模型选择策略             | 依据
  简单闲聊/寒暄        | 快速/低成本模型          | 不需要复杂推理
  复杂推荐/风格诊断    | 强模型                  | 需要跨记忆关联 + 创造性推荐
  意图不明/需追问      | 强模型                  | 追问质量直接影响后续体验
  知识问答 (有检索结果) | 中等模型               | 有 context 辅助, 不需要最强推理
  偏好确认/简单确认    | 快速/低成本模型          | 回复模式固定

  路由信号源:
    +-- Intent Understanding 分类结果 (与 2.1/2.5 共享)
    +-- 检索结果质量 (top-1 score 高 -> 可降级模型)

  降级保护:
    +-- 快速模型回复如触发用户纠正 (5.1 隐式反馈) -> 下一轮自动升级为强模型
    +-- 路由决策写入 session context, 可追溯

成本: 预期降低 30-50% 模型调用成本 (闲聊/确认类对话占比通常 > 40%)
前置依赖: Intent 分类稳定 + 多模型接入能力
实现位置: Brain 对话引擎, LLM 调用前的模型选择逻辑
```

---

## 5. 环节 4: 后处理 -- "闭环信号采集" (ROI 第二高)

### 现状

01 已有:
- injection_receipt 五元组 (v3.5)
- 负反馈熔断机制

缺失: 对用户回复的细粒度信号采集。

### 优化 5.1: 隐式反馈捕获

```
当前: 仅靠用户显式负反馈 ("不对"/"错了") 触发熔断

优化: 从用户回复中推断记忆有效性 (被动采集):

用户回复信号             | 推断                    | 动作
"对, 就是这种风格"       | 记忆命中, 偏好确认       | confidence 小幅上调
继续追问/深入讨论         | 记忆相关, 对话有效       | 标记 utilized=true
"不是, 我现在不喜欢了"    | 记忆过时, 需要更新       | 触发快速通道 (见 5.2)
沉默/转移话题             | 推荐不相关               | 标记 utilized=false
复述/纠正                 | 记忆可能有误             | confidence 下调

这些信号写入 Observation, 进入 Evolution Pipeline。

信号采集方式:
  +-- Pattern-based: 正则匹配确认/否定/纠正关键词
  +-- LLM-based (Phase 1): 低成本模型判定回复情感倾向
  +-- 初期建议用 Pattern-based (零额外成本), 积累数据后评估是否需要 LLM-based

实现位置: Brain 对话引擎, 每轮回复后的 Observation 产生阶段
```

### 优化 5.2: 纠正检测 + 快速通道

```
当前: 偏好变更通过 Evolution Pipeline 异步处理 (冷路径)

优化: 检测到偏好变更信号时, 走高优先级快速通道:

用户: "不是运动风, 我现在喜欢简约的"
       |
       v
纠正检测器 (Pattern-based):
  匹配模式: "不是X, 是Y" / "现在喜欢" / "不再" / "换成"
       |
       v
检测到偏好变更信号
       |
       v
高优先级 Observation (标记 priority=urgent)
       |
       v
Evolution Pipeline 快速通道:
  跳过 Analysis 排队, 直接进入 Evolver:
    +-- 旧记忆: "喜欢运动风" -> invalid_at = now(), superseded_by = 新ID
    +-- 新记忆: "喜欢简约风" -> provenance = confirmed_by_user, confidence = 0.9
       |
       v
  秒级生效 (不等批量 Evolution 周期)

效果: 用户说了偏好变更, 同一会话后续对话 + 下一次会话均立即使用新偏好
价值: 不需要引入"Agent 自编辑记忆"新范式, 通过快速通道在现有 Evolution 架构内解决时效性问题
实现位置: Observer 阶段 + Evolution Pipeline 优先级队列
```

### 优化 5.3: injection_receipt 闭环写入

```
对齐 review-final.md P0-2 五元组设计, 在后处理阶段补全:

每轮对话结束后, injection_receipt 包含:
  +-- candidate_score:    候选记忆相关性得分 (检索阶段产生)
  +-- decision_reason:    注入/拒绝原因 (组装阶段产生)
  +-- policy_version:     注入策略版本号 (灰度实验追溯)
  +-- guardrail_hit:      是否触发安全护栏
  +-- context_position:   注入位置索引 (U-shaped 排布的记录)
  +-- utilized:           是否被实际使用 (生成阶段产生, 本方案新增)
  +-- user_feedback_signal: 隐式反馈信号 (后处理阶段产生, 本方案新增)

这些数据是环节 5 (进化) 的输入燃料。
```

---

## 6. 环节 5: 进化 -- "生成更好的记忆"

### 现状

01 Section 2.3:
```
Observation -> Analysis (异步, 低成本模型) -> Evolution -> Quality Gateway -> 写入
```

### 优化 6.1: 结构化 Analysis Prompt

```
当前: Analysis prompt = "从对话中提取用户偏好" (模糊)

优化为结构化提取指令:

  <analysis_instruction>
  从以下对话中提取记忆, 按类型分类:

  1. 显式偏好 (用户明确表达的):
     标注 provenance=confirmed_by_user, confidence 上限 1.0
     示例: "我喜欢简约风" -> {type: preference, content: "简约风穿搭", provenance: confirmed_by_user}

  2. 隐式偏好 (从行为推断的):
     标注 provenance=observation, confidence 上限 0.6
     示例: 用户连续看了3个运动品牌 -> {type: preference, content: "可能对运动品牌感兴趣", provenance: observation}

  3. 偏好变更 (与已知偏好矛盾的):
     标注新旧对比, 标记旧记忆需 invalidate
     示例: 已知"喜欢简约", 用户说"现在更喜欢运动风" -> {type: update, old: "简约", new: "运动风", confidence: 0.9}

  4. 约束条件 (预算/禁忌/场景限制):
     标注 provenance=confirmed_by_user
     示例: "超过500的不要" -> {type: constraint, content: "价格上限500元", provenance: confirmed_by_user}

  5. 无需提取:
     闲聊/寒暄/与偏好无关的内容 -> 不生成记忆

  输出 JSON 数组, 每条包含: type, content, provenance, confidence, related_existing_memory_id (如有)
  </analysis_instruction>

效果: 记忆提取质量直接提升, 与 Provenance 分级 (01:442-467) 对齐
实现位置: Evolution Pipeline - Analysis 阶段的 prompt 模板
```

### 优化 6.2: Contextual Chunking (上下文化存储)

```
当前: memory_item.content = "简约风"

优化: 写入时给每条记忆补充上下文前缀:

  memory_item.content =
    "[用户偏好/穿衣风格/2026-01确认] 用户明确表示喜欢简约风格的穿搭,
     偏好黑白灰色系, 不喜欢过于鲜艳的颜色"

效果:
  - embedding 质量更高 (包含类别信息), 检索时语义匹配更精确
  - 不会与 "简约风装修" 之类无关记忆混淆
  - 人类可读性更强 (便于调试和审计)

成本: Evolution Pipeline 写入时多一步格式化 (已有低成本 LLM 调用, 不增加额外调用)
实现位置: Evolution Pipeline - Evolver 阶段写入前
```

### 优化 6.3: Memory Consolidation (记忆合并)

```
当前: 每次对话产生新 observation, 同一偏好可能积累多条相似记忆

优化: Evolver 阶段增加合并逻辑:

  记忆1: "喜欢运动风" (confidence: 0.6, provenance: observation)
  记忆2: "最近经常看运动品牌" (confidence: 0.5, provenance: observation)
  记忆3: "买了两双跑鞋" (confidence: 0.8, provenance: observation)

  合并为:
  "运动风偏好 (强): 用户明确表达喜欢运动风, 浏览行为和购买行为均印证"
    confidence: 0.85
    provenance: analysis (多次观察聚合)
    source_sessions: [session1, session2, session3]
    supersedes: [记忆1.id, 记忆2.id, 记忆3.id]

合并触发条件:
  +-- 同一 user_id 下, 语义相似度 > 0.85 的 memory_items 数量 >= 3
  +-- 定期批量检查 (Evolution Pipeline 的一部分)

效果:
  - 减少记忆条数, 提高检索信噪比
  - 合并后的记忆更丰富更可靠
  - 检索时不会被重复记忆淹没

实现位置: Evolution Pipeline - Evolver 阶段
```

### 优化 6.4: Confidence Decay (置信度被动衰减)

> **设计变更说明:**
> 01 Section 2.3.2 声明 "confidence 不自动衰减（避免系统行为不可预测）"。
> 本方案不修改存储的 confidence 值，而是在检索排序时计算 confidence_effective
> (= confidence * decay_factor)。存储值不变，但排序行为等效于衰减。
> 此变更需记录在 ADR-038.3 SLI Framework 中，作为 retrieval 排序优化的一部分。
> 与 01 原有 "过期由 invalid_at 语义控制" 互补而非替代:
> invalid_at 处理"已确认失效"的记忆 (硬淘汰),
> decay_factor 处理"可能过时但未确认"的记忆 (软降权)。

```
当前: confidence 写入后不变

优化: 检索时动态计算有效置信度 (不修改存储值):

  confidence_effective = confidence * decay_factor(days_since_last_validated)

  decay_factor:
    0-30 天:  1.0  (不衰减)
    30-90 天: 0.85
    90-180 天: 0.6
    180+ 天:  0.3

  last_validated 定义:
    +-- 用户显式确认 (confirmed_by_user)
    +-- 注入后被利用且用户正面反馈 (utilized=true + positive signal)
    +-- 注入后用户未纠正 (中性, 不刷新 last_validated)

效果: 过时偏好自然退出检索结果顶部, 无需用户手动说"我不喜欢了"
成本: 零 (检索时计算, 不修改存储数据)
实现位置: Reranking 阶段的 confidence_effective 计算
```

### 优化 6.5: Confidence Calibration (置信度主动校准)

```
利用 injection_receipt 的反馈数据主动校准 confidence:

校准逻辑 (定期批量, Evolution Pipeline 的一部分):

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

效果: 用已有 SLI 数据做闭环优化, 无需额外基础设施
与 Decay 的关系: Decay 是被动衰减 (时间维度), Calibration 是主动校准 (反馈维度), 互补
实现位置: Evolution Pipeline - 定期校准 Job
```

---

## 7. 优化全景图

```
用户输入
  |
  v
[1. 检索] ── 找对记忆 ───────────────────────────────────────
  |  1.1 pgvector 默认启用, 可降级 (ADR-042)
  |  1.2 Query Rewriting: 低成本 LLM 改写多查询
  |  1.3 Hybrid Retrieval: FTS + pgvector 双路并行 + RRF 合并
  |  1.4 Multi-Signal Reranking: 语义 * 时效 * 置信度 * 来源 * 频率
  |
  v
[2. 组装] ── 排好上下文 ──────────────────────────────────────
  |  2.1 动态注入量: 按意图类型调整 personal_context 预算
  |  2.2 U-shaped 排布: 高相关记忆放首尾
  |  2.3 Memory-Aware Instruction: system_prompt 中教 LLM 使用记忆
  |  2.4 Structured Tags 增强: confidence + provenance + category 标注
  |  2.5 Phase-Aware System Prompt: 按对话阶段调整指引重点
  |  2.6 动态预算分配: review-final P0-3 (弹性 slot + 截断优先级)
  |
  v
[3. 生成] ── LLM 调用 ───────────────────────────────────────
  |  3.1 生成后记忆利用检测: 回复是否引用了注入记忆
  |  3.2 Intent-Based Model Routing: 按意图选择模型 (成本优化)
  |
  v
[4. 后处理] ── 闭环信号采集 ─────────────────────────────────
  |  4.1 隐式反馈捕获: 从用户回复推断记忆有效性
  |  4.2 纠正检测 + 快速通道: 偏好变更秒级生效
  |  4.3 injection_receipt 闭环写入: 五元组 + utilized + feedback_signal
  |
  v
[5. 进化] ── 生成更好的记忆 ─────────────────────────────────
     5.1 结构化 Analysis Prompt: 显式/隐式/变更/约束四分类
     5.2 Contextual Chunking: 写入时补充上下文前缀
     5.3 Memory Consolidation: 相似记忆合并
     5.4 Confidence Decay: 被动衰减 (时间维度)
     5.5 Confidence Calibration: 主动校准 (反馈维度)
```

---

## 8. 实施优先级

按 ROI (投入产出比) 排序:

### P0 -- 立即做 (零/低成本, 高收益)

| # | 优化项 | 改动位置 | 成本 | 预期效果 |
|---|--------|---------|------|---------|
| 1 | pgvector 默认启用(可降级) | MemoryCorePort + DDL | 低 | 语义检索从可选变默认, 异常时 FTS-only 降级 |
| 2 | U-shaped 位置排布 | Context Assembler Step 3 | 零 | 记忆利用率提升 |
| 3 | Memory-Aware Instruction | system_prompt 模板 | 零 | LLM 更好地利用记忆 |
| 4 | Structured Tags 增强 | Context Assembler Step 3 | 零 | 置信度感知 + 安全 |
| 5 | 结构化 Analysis Prompt | Evolution Pipeline | 零 | 记忆提取质量直接提升 |
| 6 | Confidence Decay | Reranking 计算逻辑 | 零 | 过时记忆自然退出 |

### P1 -- 尽快做 (低成本, 中高收益)

| # | 优化项 | 改动位置 | 成本 | 预期效果 |
|---|--------|---------|------|---------|
| 7 | Hybrid Retrieval + RRF | MemoryCorePort 实现 | 低 | 检索失败率降 ~50% |
| 8 | Query Rewriting | Context Assembler Step 1 前 | 低 | 模糊查询召回提升 |
| 9 | 纠正检测 + 快速通道 | Observer + Evolution | 低 | 偏好变更秒级生效 |
| 10 | 隐式反馈捕获 | Brain 对话引擎后处理 | 低 | recall 数据被动采集 |
| 11 | Contextual Chunking | Evolution Pipeline 写入 | 低 | embedding 质量提升 |

### P2 -- 数据积累后做 (需要反馈数据)

| # | 优化项 | 改动位置 | 前置条件 | 预期效果 |
|---|--------|---------|---------|---------|
| 12 | Multi-Signal Reranking | Context Assembler | injection_receipt 数据积累 | 精排精度提升 |
| 13 | Confidence Calibration | Evolution Pipeline | injection_receipt + 隐式反馈数据 | 置信度闭环校准 |
| 14 | Memory Consolidation | Evolution Pipeline | 单用户记忆量达到 20+ 条 | 信噪比提升 |
| 15 | 记忆利用检测 | 后处理钩子 | Structured Tags 已上线 | 注入效果可量化 |
| 16 | 动态注入量 | Context Assembler + Intent | Intent 分类稳定 | 减少 context rot |
| 17 | Phase-Aware System Prompt | system_prompt 模板 | Intent 分类稳定 | 对话阶段针对性指引 |
| 18 | Intent-Based Model Routing | Brain 对话引擎 | Intent 分类 + 多模型接入 | 模型调用成本降 30-50% |

---

## 9. 与已有设计的关系

| 本方案优化项 | 对应 review-final.md 内容 | 关系 |
|-------------|--------------------------|------|
| pgvector 默认启用(可降级) | 未覆盖 (review-final 未质疑可选定位) | **新增决策**, 变更 01 Section 3.2/3.3 向量检索定位: 从"可选增强"调整为"默认启用, 可降级" |
| Hybrid + RRF | 未覆盖 | **新增** |
| Query Rewriting | 未覆盖 | **新增** |
| Multi-Signal Reranking | P0-2 五元组 candidate_score | **增强** (多维信号) |
| U-shaped 排布 | P0-2 context_position 字段 | **落地** (从记录到利用) |
| 动态注入量 | P0-3 动态预算分配器 | **细化** (按意图维度) |
| Memory-Aware Instruction | 未覆盖 | **新增** |
| Structured Tags 增强 | v3.5 已有基础标签 | **增强** |
| 记忆利用检测 | P0-2 injection_receipt | **扩展** (新增 utilized 字段) |
| 隐式反馈捕获 | P0-5 user_correction_rate SLI | **增强** (更细粒度信号) |
| 纠正检测 + 快速通道 | Evolution Pipeline 冷路径 | **增强** (热路径快速通道) |
| 结构化 Analysis Prompt | Provenance 分级 (01:442-467) | **落地** (从分级规则到提取指令) |
| Contextual Chunking | 未覆盖 | **新增** |
| Memory Consolidation | 未覆盖 | **新增** |
| Confidence Decay | 未覆盖 | **新增**, 演进 01 Section 2.3.2 "confidence 不自动衰减"立场: 存储值不变, 排序时计算 effective 值 |
| Confidence Calibration | P0-5 SLI 数据 | **闭环** (用 SLI 数据优化记忆) |
| Phase-Aware System Prompt | 未覆盖 | **新增**, 与 2.1 动态注入量同层, 按阶段调整指引 |
| Intent-Based Model Routing | 未覆盖 | **新增**, 成本优化, 依赖 Intent 分类 + 多模型接入 |

---

## 10. 验证指标

| 指标 | 基线 (优化前) | 目标 (优化后) | 测量方式 |
|------|-------------|-------------|---------|
| 记忆检索命中率 | 待测 | 提升 30%+ | 评测集 precision@inject |
| 检索失败率 | 待测 | 降低 50%+ | Hybrid vs 单路 A/B 对比 |
| 记忆利用率 | 未度量 | > 60% | utilized=true 占比 |
| 用户纠正率 | 待测 | < 5% (对齐 SLO) | user_correction_rate SLI |
| 偏好变更生效延迟 | 批量周期 (分钟级) | 秒级 | 快速通道 P95 延迟 |
| 过时记忆比例 | 未度量 | < 15% (对齐 SLO) | staleness_rate SLI |

---

## 11. 约束与边界

1. **不改 Port 契约:** MemoryCorePort 接口签名不变, 实现层内部优化
2. **不新增基础设施组件:** pgvector 是 PG 扩展, 不是新服务
3. **不破坏解耦性:** 所有优化在 01 Brain 层内部完成, 不越界到 02/03
4. **不增加热路径 LLM 调用:** Query Rewriting 用小模型, 且可缓存; Analysis Prompt 优化不增加调用次数
5. **渐进式上线:** 所有优化项通过 Experiment Engine 灰度发布, 不全量直切
6. **数据驱动:** P2 优化项依赖 P0/P1 积累的 injection_receipt 数据, 不盲目上线

---

> **本方案的本质: 不是让系统变复杂, 而是让每个 token 都物尽其用。**
