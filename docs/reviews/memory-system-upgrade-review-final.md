# DIYU AGENT 系统观察、思考与补全优化建议报告

> **版本:** v3.0 (Final Revised)
> **日期:** 2026-02-08
> **基于:** 四轮交互合并（P0 可行性评估 + 独立架构分析 + 差异合并 + 评审意见修订）
> **文档基线:** v3.3.2（00/01/06/07/08），v3.4 已落地变更
> **涉及文档:** 00(总览)、01(Brain)、06(基础设施)、07(部署安全)、08(附录)
>
> **v3.0 变更摘要 (相对 v2.0):**
> - 新增第三章: 治理架构（双 Loop + 共享治理层 + Policy Pack + 统一事件模型）
> - P0-2: recall@inject 补充为分阶段门禁（P0 观测 / P1 门禁），eval set 分阶段门槛 (200->500->1000)
> - P0-3: 新增不可压缩槽位显式定义 + safety_margin 规格 + fail-fast 启动检查 + TruncationPolicy 策略接口
> - P0-4: PIPL SLA 从"15 工作日硬编码"改为 legal_profile 可配置 + legal_profiles DDL
> - P0-5: idempotency_key 从单层改为双层幂等架构（outbox 生产者去重 + receipt 消费者去重）
> - 验收标准: 从 4 条文字描述升级为 11 项数值化 PASS/FAIL 阈值 + 灰区处理规则
> - ADR: 从 4 个独立 ADR (038-041) 合并为 2 个伞形 ADR (038-039) + 子编号
> - 全文章节重编号（共 10 章）

---

## 一、总体评估与架构定位

### 1.1 三项架构优势

| # | 优势 | 说明 |
|---|------|------|
| 1 | 双 SSOT 硬/软依赖定义明确 | Memory Core（硬依赖, 挂了停服）与 Knowledge Stores（软依赖, 拔了降级）的依赖级别清晰，降级矩阵可验证 |
| 2 | Port 契约体系完备 | ADR-033（语义契约兼容规则）+ ADR-034（Port 演进 Expand-Contract 迁移）已形成可执行的向后兼容保障 |
| 3 | 5 Loop 跨层业务闭环地图 | Loop A\~E（学习进化/知识沉淀/知识消费/计量反压/治理）明确了每条业务链路的涉及层、涉及契约和断裂影响 |

### 1.2 方案定位

提案目标——从"架构合理"升级到"生产可证伪、可观测、可回滚"——方向正确且切中当前阶段核心风险。5 项 P0 均有落地必要性。方案核心理念均有明确业界对标，非过度设计。

**业界对标参照:**

| 理念 | 对标实践 |
|------|---------|
| 注入正确性评测 | Mem0 LoCoMo benchmark (66.9%)、BudgetMem (ICLR 2025) |
| 确定性预算算法 | VMware Resource Governor (Reservation/Limit/Shares)、MemGPT 分层管理 |
| 删除状态机 | EventStoreDB tombstone + Temporal idempotency、AWS Step Functions |
| SLO burn-rate | Google SRE Workbook MWMBR 模式（已被 Grafana/Datadog 原生支持） |

### 1.3 潜在约束（五个隐含假设）

在系统规模增长与平台化演进中，架构存在五个"设计时合理、演进时受限"的隐含假设:

**假设 1: Brain 是运行时单体**

对话（GPU/CPU 密集）、记忆（I/O 密集）、技能调度（编排等待）混在同一进程，无法独立伸缩。当 100 用户并发对话时，记忆引擎的 I/O 等待会拖慢技能调度的编排吞吐。

> 建议: 不必拆微服务，但在 Brain 内部预设 Executor 分区——对话热路径（同步低延迟）与记忆进化冷路径（异步允许延迟）在线程池/协程层面隔离。Python 中可用 `asyncio.TaskGroup` + 独立线程池。

**假设 2: 单模型单窗口**

Context Assembler 的预算分配基于 `所有 slot 之和 <= model_context_window`，假设每次对话只调用一个模型的一个窗口。实际运行中一次对话可能触发多次异构 LLM 调用（意图理解用小模型、内容生成用大模型、合规检查用安全模型），每次的窗口和预算需求不同。

> 建议: 将 Context Assembler 从"每次对话调用一次"重构为"每次 LLM 调用前调用一次"，引入 `AssemblyProfile` 概念（类比 Resolver 的 Profile）。Port 层面非 breaking change。

**假设 3: Memory/Knowledge 单向流动**

Promotion Pipeline 设计了 Memory -> Knowledge 的上升通道，但缺乏 Knowledge -> Memory 的下行通道。场景: 品牌总部下发新搭配规则（Knowledge），门店运营者想"收藏"到个人工作备忘（Memory），当前只能通过对话间接"告诉" Brain。

> 建议: 不改变双 SSOT 架构，但预留 `BookmarkPort` 接口，允许用户将 Knowledge 条目创建为个人记忆引用（不复制数据，只建立引用关系），保持隐私硬边界。

**假设 4: 组织树深度硬编码**

Tier 语义与 RLS 策略深度绑定（`path <@ current_setting('app.current_org_path')::ltree`）。06 Section 1.6.1 已评估结论为"V2 规划"。

> 建议: v1 保持 5 层不变。RLS 层面: 只依赖 `path` 和 `depth`，不依赖 tier 名称，tier 变成纯展示信息由应用层映射。代码层面: 查询使用 ltree `<@` 操作符（天然支持任意深度），避免硬编码 tier 枚举判断。预留 `max_org_depth` + `tier_types` 配置字段但 v1 锁定为当前值。权限判定基于 permission codes 而非角色/tier 硬编码。

**假设 5: 对话模式假设为同步**

缺乏对长任务（批量文案生成、跨会话分析、持续监控任务）的异步编排能力。当前 content_tasks 有 `status` 字段可勉强支持，但 Brain 的对话引擎没有"长任务管理"能力。

> 建议: 在 Brain 的 5 大固有能力之外，预留第 6 个扩展能力槽位——**Task Orchestration**（异步启动 + 进度跟踪 + 中间结果交付 + 结果通知）。与 Skill Dispatch 的区别: Skill Dispatch 是同步"做一件事然后返回"，Task Orchestration 是异步"启动 -> 跟踪 -> 交付"。

---

## 二、核心升级方案: 生产可证伪、可观测、可回滚 (P0 级)

### 2.0 P0 执行优先级排序

| 优先级 | P0 项 | 理由 |
|--------|-------|------|
| #1 | P0-4 删除管线 | 数据删除合规硬约束（PIPL/GDPR），法域 SLA 可配置，法律风险最高 |
| #2 | P0-2 注入正确性 | 质量基线，其他 SLI 的度量依赖此项（如 injection_hit_rate） |
| #3 | P0-5 SLO 可观测性 | 度量基础设施，为其他 P0 提供验证手段和告警能力 |
| #4 | P0-3 动态预算分配 | 已有 01 Section 4.2 静态 hardcoded 方案兜底，不紧急 |
| #5 | P0-1 PK 命名统一 | 可通过 ADR-033/034 Expand-Contract 渐进迁移，风险最低 |

> 备选排序（按技术依赖分批）: **Batch 1** (P0-1 命名 + P0-5 可观测) -> **Batch 2** (P0-4 删除管线) -> **Batch 3** (P0-2 注入 + P0-3 预算)。两种排序可结合: 优先级排序指导"下一个做什么"，分批排序指导"一起做什么"。

---

### 2.1 P0-1: 统一数据契约命名 (Schema Alignment)

**现状分析（3 处分歧）:**

| 位置 | 当前命名 | 文档引用 |
|------|---------|---------|
| 01 Section 2.3.1 MemoryItem Schema v1 | `memory_id` | 契约层对外标识 |
| 01 Section 3.1 memory_items DDL | `item_id` | 存储层主键 |
| 01 Section 3.3 Qdrant personal_projection | `memory_item_id` | 向量投影 FK |

**v3.4 已落地的澄清（01:161-168）:** 已通过 ID 映射说明解决: `memory_id`（消费端）与 `item_id`（存储端）是同一实体的不同投影，MemoryCorePort 实现层负责双向映射。此映射关系不构成 schema v1 的一部分。

**建议:**
- 统一收敛为 **`memory_id`**（消费端视角，符合 DDD ubiquitous language）
- Port 接口（MemoryItem schema v1）已用此名，这是对外契约
- `item_id` 降级为 DDL 内部实现细节（Port 实现层负责映射）
- Qdrant payload 中的 `memory_item_id` 改为 `memory_id`
- 兼容别名弃用期: **2 个 minor version**（对齐 ADR-034 deprecation 周期）

**迁移路径（遵循 ADR-033 + ADR-034）:**
1. **Expand:** Qdrant payload 中新增 `memory_id` 字段，保留 `memory_item_id`
2. **Migrate:** 消费者切换到 `memory_id`
3. **Contract:** 移除 `memory_item_id`（>= 标记废弃后 2 个 minor version）

**影响范围:** 01（MemoryItem schema）、06（DDL 注释）、01 Section 3.3（Qdrant payload）。无需改 07。

---

### 2.2 P0-2: 记忆注入正确性闭环 (Injection Correctness)

**优化目标:** 解决缺乏完整注入判定记录、离线评测集和发布门槛的问题。

#### 注入决策记录（五元组，写入 memory_receipts.details）

| 字段 | 类型 | 说明 |
|------|------|------|
| `candidate_score` | Float | 候选记忆的相关性得分 |
| `decision_reason` | Enum | 注入/不注入的判定原因标签 |
| `policy_version` | String | 当前注入策略版本号（联动 Experiment Engine） |
| `guardrail_hit` | Boolean + String | 是否触发安全护栏 + 原因 |
| `context_position` | String | 注入到上下文的位置区间（应对 Lost-in-the-middle） |

> `context_position` 是关键新增。业界研究证实 LLM 对上下文中间位置的信息注意力下降（Claude 2.1 中间位置 accuracy 降至 27%）。记录注入位置是后续优化排序策略的数据基础。

#### 评测集建设（分阶段门槛）

评测集规模不应成为 P0 阻塞点，采用分阶段门槛:

| Phase | 样本量 | 精度 95% CI | 可检测最小退化 | 门禁阈值 |
|-------|--------|------------|---------------|---------|
| Phase 0 (P0 Launch) | 200 条 | +/-4.2% | 90%->82% (灾难级) | precision >= 0.80, recall 观测不门禁 |
| Phase 1 (稳定运行) | 500 条 | +/-2.6% | 90%->85% (明显退化) | precision >= 0.85, recall >= 0.70 |
| Phase 2 (成熟期) | 1000+ 条 | +/-1.9% | 90%->87% (微妙退化) | F1@inject >= 0.80, 按场景分层 |

> **关键约束:** 每个 Phase 的 gate 阈值必须与样本量匹配。200 条样本不应判 2% 的精度差异。

- **样本构成:** 正样本 40% + 负样本 40% + 边界样本 20%
- 覆盖: 单轮/多轮、4 种 memory_type x 5 种 intent_type 组合、冲突/无冲突场景
- **评测集版本化:** 评测数据集本身需版本管理（`eval_set_version`），确保不同时期的正确率指标可横向比较。版本变更须记录: 新增/删除/修改的样本数及原因
- **持续维护机制（双通道）:**
  - 被动收集: 每次 `user_correction_rate` 触发熔断时，自动将脱敏样本加入评测集
  - 主动审计: **月度审计评测集分布**，确保覆盖度均衡（避免偏向"失败案例"，缺少"正确注入"的持续补充）

#### 发布门槛（precision + recall 双轨）

只追 precision 会制造退化陷阱——最安全的策略是什么都不注入（precision=100%, recall=0%）。对记忆系统而言，"该想起来的没想起来" 和 "不该想起来的乱想" 都是故障。

| 指标 | P0 阈值 | P1 阈值 | 说明 |
|------|---------|---------|------|
| `precision@inject` | >= 0.80 (门禁) | >= 0.85 | 注入精确率 |
| `recall@inject` | 观测记录 (不门禁) | >= 0.70 (门禁) | 注入召回率 |
| `F1@inject` | 观测记录 | >= 0.75 (门禁) | precision 和 recall 的调和平均 |
| `false_injection_rate` | <= 0.10 | <= 0.05 | 误注入率 |
| `user_correction_rate` | <= 0.05 | <= 0.03 | 用户纠正率（已在 SLI 中定义） |

> **为什么 recall P0 只观测不门禁:** recall 评估需要 ground truth（本轮对话"应该"注入哪些记忆），需要人工标注，成本高。P0 阶段标注数据不足，强行门禁会因样本偏差产生误判。但必须从 P0 开始采集数据，为 P1 门禁积累基线。

**recall 数据采集策略（P0 即启动）:**
- 对话结束后采样人工标注 "本轮应注入记忆集合"
- 利用用户显式反馈（"你忘了我说过的X"）作为 recall miss 信号
- 利用 memory_receipt 中 utilized=false 高频项作为 precision miss 候选

**与 01 Section 2.3.2 的关系:** `injection_hit_rate` SLI（SLO > 60%）度量的是线上生产数据；`precision@inject` / `recall@inject` 度量的是标注数据集上的准确率。两者互补: 前者监控线上漂移，后者验证策略变更的离线效果。

#### 与 Experiment Engine 联动

注入策略变更和预算算法变更**必须通过 Experiment Engine（06 Section 5）灰度发布，不可全量直切**。具体:
- 注入策略变更走"Brain 路由策略"实验维度
- 预算算法变更走"Knowledge 检索策略"实验维度
- 灰度比例: 初始 10% 流量（按 tenant 分流），SLI 达标后逐步放量
- 回滚条件: 任一门槛指标跌破阈值，自动回滚到旧策略版本

---

### 2.3 P0-3: 动态预算器工程化 (Dynamic Budgeting)

#### 两种预算概念辨析

| 维度 | Context Window Budget（上下文窗口预算） | Token Cost Budget（Token 消耗预算） |
|------|---------------------------------------|--------------------------------------|
| 归属 | Brain 层 (01 Section 4.2 / 4.2.1) | Gateway/Billing (05 Section 6.2 / 06 Section 3) |
| 粒度 | per-request | per-org-month |
| 目的 | 质量控制（防上下文溢出导致生成质量下降） | 成本控制（防超支） |
| 控制方式 | 各 slot 的 min/max + 运行时弹性分配 | budget_monthly_tokens + Redis 实时计数 + PG 日对账 |

> P0-3 聚焦 Context Window Budget（Brain 层），与 Token Cost Budget（Gateway/Billing 层）是**正交的两个维度**。

#### 不可压缩槽位与 safety_margin 定义

不可压缩槽位 = 任何预算压力下不可截断的槽位。若未显式定义，buggy 的预算分配器可能截断 system_prompt 来腾出空间给记忆注入——这是灾难性故障。

```
incompressible_slots (硬约束，不可截断):
  - system_prompt:     Agent 身份和行为规则，截断 = Agent 人格崩塌
  - last_user_turn:    当前正在回答的问题，截断 = 答非所问
  - generation_buffer:  模型生成空间，截断 = 输出被截断或拒绝生成

compressible_slots (软约束，按优先级截断):
  - knowledge_context, summary_blocks, entity_slots,
    active_window, personal_context, memory_items
```

**safety_margin 规格:**

```
safety_margin = max(5% of total_budget, 200 tokens)

依据:
  - tokenizer 估算 vs 实际编码差异: 中文场景不同 tokenizer 差异可达 3-5%
  - 动态内容（tool_results）可能在组装后膨胀
  - 200 tokens 下限: 防止小窗口模型 (4K) 的 margin 过小导致溢出
```

**启动时 fail-fast 检查:**

```
incompressible_total = sum(len(slot) for slot in incompressible_slots)
min_generation = generation_buffer.min  # 最小生成空间

if incompressible_total + safety_margin + min_generation > context_window:
  raise ConfigurationError(
    f"Incompressible slots ({incompressible_total} tokens) + margin ({safety_margin}) "
    f"+ min generation ({min_generation}) exceed context window ({context_window}). "
    f"Reduce system_prompt or use a larger model."
  )
```

> 此检查在 Agent 初始化时执行，不留到运行时。配置错误应 fail-fast，不应静默截断系统提示。

#### 核心算法: hard_reserved + dynamic_pool

```
total_budget = model_context_window - safety_margin
hard_reserved = sum(incompressible_slots) + sum(slot.min for slot in compressible_slots)
dynamic_pool = total_budget - hard_reserved

for each compressible_slot ordered by priority:
  allocation = slot.min + dynamic_pool * slot.weight * signal_modifier
  allocation = clamp(allocation, slot.min, slot.max)
```

#### 稳定性控制

- **EWMA:** 平滑系数 alpha = 0.3（经验值，平衡响应速度与稳定性）
- **Hysteresis:** Slot 在 `target +/- 10%` 范围内不触发重分配
- 具体数值作为 RULE 级配置（可按租户调整），默认值硬编码
- v1 采用**确定性优先级分配**（规则驱动），v2 再考虑 ML-based 分配

#### 超窗截断优先级（由先截断到最后截断）

截断策略采用分阶段设计: P0 用固定优先级（行为可预测、可审计），接口按策略模式设计以支持后续升级。

```
接口层: BudgetAllocator 接受 TruncationPolicy (策略模式)
  |
  +-- Phase 0: FixedPriorityPolicy (下表 8 级规则，作为 greedy solver)
  |     行为可预测，可审计，实现简单
  |
  +-- Phase 1: ConstraintOptimizationPolicy (未来升级路径)
        硬约束: incompressible_slots 不可截断
        软约束: 各 slot utility score (基于 memory_receipt 反馈数据训练)
        求解: 线性规划或贪心近似 (context window 规模小，不需要重型 solver)
```

| 优先级 | Slot | 类型 | 原因 |
|--------|------|------|------|
| 1 | knowledge_context | 可压缩 | 软依赖，降级影响最小 |
| 2 | summary_blocks | 可压缩 | 可重新摘要 |
| 3 | entity_slots | 可压缩 | 可从近期对话重建 |
| 4 | active_window | 可压缩 | 压缩最早的 turn |
| 5 | personal_context | 可压缩 | 核心差异化，尽可能保留 |
| 6 | system_prompt | **不可压缩** | 截断 = Agent 人格崩塌 |
| 7 | user_input | **不可压缩** | 截断 = 答非所问 |
| 8 | generation_budget | **不可压缩** | 截断 = 无法生成输出 |

> **关键策略:** 截断 active_window 时采用**"首尾保留 + 中间摘要"**策略——保留最早 1 turn + 最近 N turn，中间部分摘要化。利用 LLM 的 U-shaped attention bias（对首尾信息注意力最高）。

#### 回退机制

- 分配算法异常 -> 退回 Section 4.2 静态基线（硬编码兜底）
- 模型窗口探测失败 -> 查本地静态表（按 `model_family` 维护，非按 model_id）
- 探测方式: 首选 LiteLLM SDK 的 `model_info` API，失败则查静态表

---

### 2.4 P0-4: 删除管线闭环 (PIPL/GDPR Deletion)

> **优先级: #1（法律风险最高）**

#### 删除 SLA: 法域可配置 (legal_profile)

**当前文档 01:352 写的 30 天为 GDPR 标准。《个保法》第 47 条原文为"应当主动删除"，强调"及时"，法条正文未写死具体天数。** "15 工作日" 来源于行业实践/TC260 推荐标准而非法定硬性要求。为避免法条口径争议，SLA 应按法域可配置，默认按最严格内部标准执行。

```sql
-- legal_profiles 配置表 (P0 落地)
CREATE TABLE legal_profiles (
  profile_id    TEXT PRIMARY KEY,       -- 'GDPR', 'PIPL', 'CCPA', 'DEFAULT'
  deletion_sla  INTERVAL NOT NULL,      -- '30 days', '15 business_days', '45 days'
  sla_type      TEXT NOT NULL            -- 'calendar_days' | 'business_days'
    CHECK (sla_type IN ('calendar_days', 'business_days')),
  source        TEXT NOT NULL,           -- 法条引用或内部SLA编号
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- 预置数据
INSERT INTO legal_profiles VALUES
  ('GDPR',    '30 days',  'calendar_days',  'Art.17 GDPR'),
  ('PIPL',    '15 days',  'business_days',  '内部SLA，参照TC260推荐标准'),
  ('DEFAULT', '15 days',  'business_days',  '默认按最严格标准');

-- 删除请求关联 legal_profile
ALTER TABLE deletion_requests
  ADD COLUMN legal_profile_id TEXT REFERENCES legal_profiles(profile_id)
  DEFAULT 'DEFAULT';
```

**SLA 计算逻辑:**

```
if sla_type == 'business_days':
  deadline = request_date + skip_weekends_and_holidays(deletion_sla, region_calendar)
else:
  deadline = request_date + deletion_sla

告警触发:
  SLA 剩余 < 25% 且 state NOT IN ('completed') -> P1 告警
  SLA 剩余 < 10%                                 -> P0 告警 + 自动升级
  SLA 超期                                        -> 合规事件，触发 escalated 状态
```

#### 完整删除范围矩阵

| 存储位置 | 逻辑删除方式 | 物理删除方式 | 物理删除时机 |
|---------|------------|------------|------------|
| memory_items (PG) | invalid_at = now() + tombstone | DELETE FROM | 异步 Worker |
| conversation_events (PG) | 关联 tombstone | content 字段置 null | 异步 Worker（保留事件骨架） |
| session_summaries (PG) | 关联 tombstone | content 字段置 null | 异步 Worker |
| Qdrant personal_projection | N/A | 按 user_id 过滤删除 points | 异步 Worker |
| Redis 缓存 | N/A | 按 user_id 前缀 FLUSH | **同步**（tombstone 创建时顺带执行） |
| memory_receipts (PG) | 不删除 | 不删除 | 永久保留（脱敏: 仅保留统计字段） |

> Redis 缓存行至关重要——不清除缓存会导致用户发起删除后短期内仍从缓存命中已删数据，违反 PIPL "删除后不可见" 预期。

#### 状态机优化（统一为 8 态，含前置校验与失败恢复）

```
requested -> verified -> tombstoned -> queued -> processing -> completed
                                                            -> failed -> retry_pending -> processing (loop)
                                                                      -> escalated (重试耗尽)
```

| 状态 | 含义 | 时效 |
|------|------|------|
| `requested` | API 收到请求 | 同步，秒级 |
| `verified` | 确认用户身份 + 所有权校验通过 | 同步，秒级 |
| `tombstoned` | 逻辑标记完成，读路径已过滤，数据对用户不可见 | 同步，秒级 |
| `queued` | 写入 event_outbox 等待投递 | 同步（同事务） |
| `processing` | Worker 正在执行物理删除 | 异步 |
| `completed` | 全部存储位置删除完成 | -- |
| `failed` / `retry_pending` | 某存储位置失败，等待重试 | 指数退避，上限 5 次 |
| `escalated` | 重试耗尽，需人工介入 | -- |

> 与 v3.4 已落地的 4 态映射: `active` = requested + verified + tombstoned; `processing` = queued + processing; completed / failed 不变。

#### 写端屏障 (Deletion Fence)

当前竞态防护仅在 Evolution Pipeline 侧做 tombstone 检查（读端屏障）。增加**写端屏障**:

- `deletion_fence_version`: 单调递增版本号，tombstone 创建时写入
- 所有写入路径在写前检查: 若 `target_user_id` 存在 active tombstone，丢弃写入
- 与 ADR-024 的 FK `version` 防冲突模式一致
- **Fence 按 `user_id` 分片**，避免全局热点

防护目标: 防止 "delete-then-resurrect" 场景——Evolution Pipeline 在 tombstone 生效后产出新 memory_item，或异步 Worker 尚未清理完毕时新数据写入。

#### Worker 幂等与断点恢复

- **幂等:** 基于 `request_id`，通过 inbox 表检查已处理状态
- **断点恢复:** Worker 执行时维护 `progress` 字段（JSON，记录每个存储位置的完成状态）。重启后从 `progress` 恢复，跳过已完成的存储位置，避免重复执行已完成的删除操作（幂等 + 增量）

#### SLA 阶梯告警（由 legal_profile 驱动）

告警阶梯根据 tenant 关联的 `legal_profile` 自动选择模板:

| 法域 | SLA 剩余 75% | SLA 剩余 50% | SLA 剩余 33% | 截止日 |
|------|-------------|-------------|-------------|--------|
| PIPL (15 工作日) | Day 4 内部告警 | Day 8 升级告警 | Day 10 紧急告警 | Day 15 |
| GDPR (30 自然日) | Day 7 内部告警 | Day 14 升级告警 | Day 20 紧急告警 | Day 30 |

> 系统按 `deletion_requests.legal_profile_id` 关联 `legal_profiles.deletion_sla` 计算各阶梯时间点，不硬编码具体天数。新增法域只需插入 `legal_profiles` 配置行。

#### Day-2 增强: Crypto Shredding

物理删除在分布式系统中很难保证 100% 覆盖（备份、日志、CDN 缓存等）。Crypto shredding 作为补充方案:
- 为每个 user 生成独立加密密钥（HashiCorp Vault 管理）
- PII 字段使用用户密钥加密存储
- 删除时销毁密钥 = 数据不可访问
- 纳入 P2 路线图

---

### 2.5 P0-5: 可观测性升级到 SLO 级

#### 指标对齐（7 项 SLI + Loop 映射）

| SLI | 定义 | SLO | 关联 Loop | 来源 |
|-----|------|-----|-----------|------|
| `staleness_rate` | invalid_at < now() 且未物理删除的占比 | < 15% | A | 保留（原有） |
| `conflict_rate` | superseded_by 链长 >= 3 的条目占比 | < 10% | A | 保留（原有） |
| `injection_quality` | hit_rate * (1 - correction_rate) | > 0.57 | A, C | 合并（原 hit_rate + correction_rate） |
| `retrieval_latency_p95` | retrieval_receipt.latency_ms P95 | < 200ms | C | 保留（原有） |
| `context_overflow_rate` | budget_allocation 中任一 slot 被截断的请求占比 | < 5% | C | **新增** |
| `deletion_timeout_rate` | tombstone.status != 'completed' && age > SLA 阈值的占比 | < 1% | E | **新增** |
| `receipt_completeness_rate` | 对话请求中缺少对应 injection_receipt 的占比 | < 0.1% | all | **新增** |

#### burn-rate 告警配置

| 窗口 | burn-rate | 告警类型 | 说明 |
|------|-----------|---------|------|
| 1h 长窗口 + 5m 短窗口 | >= 14.4x | **Critical (Page)** | 快速消耗，立即告警 |
| 6h 长窗口 + 30m 短窗口 | >= 6x | **Warning (Ticket)** | 缓慢消耗，工单告警 |

> 短窗口 = 长窗口 x 1/12（Google SRE Workbook 推荐比例）。

**低流量场景注意:** ToB 产品初期 tenant 数量有限，部分 SLI 窗口内样本量不足时 burn-rate 告警可能过于灵敏。建议: 设置**最小样本量阈值**（如单窗口内 >= 50 次事件才触发 burn-rate 计算），低于阈值时仅记录不告警。

#### 技术栈补充

当前 08 附录 D 技术栈总览缺少可观测性基础设施。建议补充:

| 能力 | 方案 | 自建/借力 |
|------|------|---------|
| 指标采集 + 告警 | Prometheus + Alertmanager | 借力 |
| 指标可视化 | Grafana | 借力 |

> 私有部署 Docker Compose（07 Section 3）中已有 prometheus，与此处一致。

#### 字段优化

**双层幂等架构 (idempotency_key):**

`idempotency_key` 不是"主副"关系，而是**不同系统边界的独立幂等保障**:

```
写入链路 (两阶段):

  Stage 1: Application -> DB Transaction (生产者去重)
    写 memory_items + event_outbox (同一事务)
    event_outbox.idempotency_key = 防止重复事件产生
    UNIQUE 约束在源头拦截重复

  Stage 2: Relay -> Event Bus -> Consumer (消费者去重)
    Consumer 写 memory_receipts
    memory_receipts.idempotency_key = 防止重复消费处理

缺失 outbox 层幂等的危害:
  应用层重试 (网络超时) -> outbox 写入两条相同事件
  -> Relay 发布两次 -> 下游消费者收到重复事件
  -> 即使 receipt 层去重，中间链路的重复消费浪费资源且增加延迟
  -> 对删除操作: 可能重复执行物理删除，产生混乱状态
```

```sql
-- event_outbox 增加幂等约束 (P0)
ALTER TABLE event_outbox
  ADD COLUMN idempotency_key TEXT NOT NULL,
  ADD CONSTRAINT uq_outbox_idempotency UNIQUE (idempotency_key);

-- memory_receipts 保留消费侧幂等 + 关联 outbox 事件
ALTER TABLE memory_receipts
  ADD COLUMN outbox_event_id BIGINT REFERENCES event_outbox(id);
-- memory_receipts.idempotency_key 已有，保留用于消费侧去重
```

> outbox 的 idempotency_key 是**生产者去重**（防止重复产生事件），receipt 的 idempotency_key 是**消费者去重**（防止重复处理事件）。两者都需要，outbox 层缺失的危害更大——污染扩散到整个下游链路。

**error_code 枚举化:**

- `error_code`: 使用枚举，不允许自由文本

```
error_code 枚举:
  RETRIEVAL_TIMEOUT
  INJECTION_BUDGET_EXCEEDED
  INJECTION_GUARDRAIL_HIT
  KNOWLEDGE_DEGRADED
  MEMORY_CORE_UNAVAILABLE
  EVOLUTION_BLOCKED_BY_ERASURE
  BUDGET_ALLOCATOR_FALLBACK
```

- `details_schema_version`: 注入五元组导致 details 结构扩展，version 从 2 升到 3。需按 ADR-033 兼容规则执行 Expand-Contract 迁移。

#### 降级免疫机制

**当 `injection_receipt.degraded_reason` 不为空时，该会话的用户反馈不计入 `user_correction_rate` SLI。** 记忆引擎的负反馈熔断排除降级期间的样本。

> 原因: 防止级联失败路径（Qdrant 慢 -> Knowledge 降级 -> 对话质量下降 -> 负反馈增加 -> 记忆被误判撤销 -> 恶性循环）。一行逻辑判断，防止自毁循环。

---

### 2.6 验收标准: 数值化 PASS/FAIL 判定

没有数值阈值的验收标准等于没有验收标准。以下 11 项指标均可自动化判定。

#### 数值化验收指标表

| # | 验收项 | 指标 | PASS 阈值 | FAIL 阈值 | 测量方法 | 闭合 P0 项 |
|---|--------|------|-----------|-----------|---------|-----------|
| 1 | 注入精确率 | precision@inject | >= 80% | < 70% | 200 条 eval set (Phase 0) | P0-2 |
| 2 | 注入召回率 | recall@inject | 观测记录 (OBSERVE) | - | 人工标注子集 | P0-2 |
| 3 | 预算溢出率 | budget_overflow_rate | < 1% | > 5% | 生产流量采样 | P0-3 |
| 4 | 截断质量 | truncation_quality | >= 4.0/5.0 | < 3.0/5.0 | 截断前后人工对比评审 | P0-3 |
| 5 | 删除 SLA 达标率 | sla_compliance_rate | >= 99% | < 95% | 删除请求按时完成比例 | P0-4 |
| 6 | 删除完整性 | deletion_completeness | 100% | < 100% | 删除后 PG/Qdrant/Redis 数据残留扫描 | P0-4 |
| 7 | 删除幂等性 | duplicate_execution_rate | 0% | > 0% | event_outbox 重复检测 | P0-4 |
| 8 | 注入延迟 | p99_injection_latency | < 200ms | > 500ms | Prometheus histogram | P0-5 |
| 9 | 端到端延迟 | p99_e2e_latency | < 3s | > 5s | 全链路 trace | P0-5 |
| 10 | 记忆可用性 | memory_core_availability | >= 99.9% | < 99.5% | uptime 监控 | P0-5 |
| 11 | PK 命名一致性 | naming_consistency | 100% | < 100% | DDL 扫描脚本 | P0-1 |

#### 灰区处理

PASS 和 FAIL 阈值之间存在灰区（如 precision 在 70%-80% 之间）。灰区判定规则:
- **条件通过:** 需人工评审确认是数据质量问题还是策略问题，附 action plan 后可放行
- **不可用于全量发布:** 灰区通过的版本仅允许在 Experiment Engine 灰度环境运行，不可全量切换

#### 验收流程

```
1. 自动化脚本跑全部 11 项指标
2. 每项输出三态判定: PASS / FAIL / OBSERVE (观测项不判定)
3. 门禁规则: 所有非 OBSERVE 项必须 PASS 或灰区条件通过，0 个 FAIL
4. OBSERVE 项记录基线值，用于 P1 门禁基准
5. 输出验收报告 (JSON + 人类可读摘要)
6. 报告存档: 每次发布关联验收报告版本，可追溯
```

#### 闭合性声明

| # | 业务验收标准 | 对应指标项 | 闭合 P0 项 |
|---|-------------|-----------|-----------|
| 1 | "记忆被注入且注入正确" | #1 precision + #2 recall (OBSERVE) | P0-1 + P0-2 |
| 2 | "不会挤爆窗口且波动可控" | #3 overflow_rate + #4 truncation_quality | P0-3 |
| 3 | "删除可追踪、可完成、不可恢复" | #5 sla_compliance + #6 completeness + #7 idempotency | P0-4 |
| 4 | "故障时可降级、可告警、可回滚" | #8 latency + #9 e2e_latency + #10 availability | P0-5 |

> 4 条业务验收标准均有数值化指标覆盖，每项可自动判定 PASS/FAIL。

---

## 三、治理架构: 双 Loop + 共享治理层

### 3.1 设计理念

P0 的 5 项变更不应作为分散的独立优化，而应统一在一个可解释的治理架构下。但运行时路径（注入/预算/SLO）和数据生命周期（删除/保留/合规）是两个正交关注点，强行塞进同一个 Loop 会导致语义泄漏。

### 3.2 双 Loop 架构

```
Runtime Governance Loop (运行时路径, per-request):
  Retrieve -> Decide -> Inject -> Observe -> Evaluate -> Adapt
  |           |          |         |           |          |
  |           |          |         |           |          +-- 策略更新 (policy_version++)
  |           |          |         |           +-- 离线 eval (precision/recall/F1)
  |           |          |         +-- 写 receipt (五元组 + context_position)
  |           |          +-- 组装上下文窗口 (BudgetAllocator)
  |           +-- 注入决策 (candidate_score, guardrail_hit)
  +-- 检索候选记忆 + 知识

  覆盖 P0 项: P0-2 注入正确性, P0-3 动态预算, P0-5 SLO 观测
  执行上下文: 同步 per-request (Retrieve->Observe) + 异步 batch (Evaluate->Adapt)

Data Lifecycle Pipeline (数据生命周期, per-event):
  Request -> Verify -> Execute -> Audit -> Comply
  |           |          |         |         |
  |           |          |         |         +-- 法域 SLA 合规检查
  |           |          |         +-- 审计记录 (deletion_event)
  |           |          +-- 物理删除 (Worker, 断点恢复)
  |           +-- 身份/所有权校验 (verified 状态)
  +-- API 收到删除请求

  覆盖 P0 项: P0-4 删除管线, Worker 幂等, legal_profile SLA
  执行上下文: 同步 (Request->Verify) + 异步 (Execute->Comply)
```

> **为什么不合并为一个 Loop:** 尝试将删除映射到 Runtime Loop 时，"Inject" 步骤在删除场景下语义为空。改名为 "Execute" 则运行时路径的精确描述力丧失。双 Loop 让每个流程保持语义精确，共享治理层实现一体化。

### 3.3 共享治理层 (Shared Governance Layer)

两个 Loop 共享以下治理原语:

```
Shared Governance Layer:
  +-- Policy Pack
  |     policy_version:     注入策略版本 (Runtime Loop)
  |     legal_profile:      法域合规配置 (Lifecycle Pipeline)
  |     allocator_profile:  预算分配策略 (Runtime Loop)
  |     guardrail_profile:  安全护栏配置 (两者共用)
  |
  +-- Unified Event Model
  |     decision_event:   注入决策事件 (Runtime Loop -> Observe)
  |     deletion_event:   删除生命周期事件 (Lifecycle Pipeline -> Audit)
  |     degrade_event:    降级事件 (两者共用)
  |     共享字段: event_id, trace_id, tenant_id, timestamp, policy_version
  |
  +-- Observability
  |     统一 trace_id 贯穿两个 Loop
  |     统一 SLI 框架 (7 项 SLI)
  |     统一 burn-rate 告警
  |
  +-- Experiment Engine
        灰度发布入口 (Runtime Loop 的策略变更)
        法域配置变更的灰度验证 (Lifecycle Pipeline)
```

### 3.4 P0 变更到 Loop 的映射

| P0 项 | 归属 Loop | 映射步骤 |
|-------|----------|---------|
| P0-1 PK 命名统一 | 基础设施 (两者共用) | 无特定步骤，DDL 层变更 |
| P0-2 注入正确性 | Runtime Loop | Decide (五元组) + Evaluate (eval set) |
| P0-3 动态预算 | Runtime Loop | Inject (BudgetAllocator + truncation) |
| P0-4 删除管线 | Lifecycle Pipeline | 全流程 (Request->Comply) |
| P0-5 SLO 观测 | 共享治理层 | Observe (Runtime) + Audit (Lifecycle) |

### 3.5 ADR 合并建议

4 个独立 ADR 存在治理碎片化风险。建议合并为 2 个伞形 ADR + 内部子决策编号:

```
ADR-038: Runtime Governance (注入 + 预算 + SLO)
  038.1: Injection Correctness Gate
         五元组记录规范, eval set 分阶段门槛, precision/recall 双轨门禁
  038.2: Dynamic Budget Allocator
         不可压缩槽位定义, safety_margin, EWMA/Hysteresis, TruncationPolicy 接口
  038.3: SLO/SLI Framework
         7 SLIs, burn-rate 告警, 最小样本量阈值, 降级免疫

ADR-039: Data Lifecycle Governance (删除 + 幂等 + 法域)
  039.1: Deletion State Machine
         8-state, deletion_fence_version, verified 前置校验
  039.2: Worker Idempotency
         双层幂等 (outbox + receipt), 断点恢复 (progress checkpoint)
  039.3: Legal Profile Configuration
         legal_profiles 表, 法域可配置 SLA, 阶梯告警模板
```

> 好处: 治理聚合 (2 个 ADR)，决策可追溯 (子编号)，评审粒度可控。每个子决策仍有独立的 Context/Decision/Consequences 结构。

---

## 四、结构性风险分析（5 项）

### 4.1 风险 1: Context Assembler 的"上帝组件"趋势

**现状:** Context Assembler（01 Section 4）是唯一同时读取两个 SSOT 的组件，当前承担: Memory 检索 -> Knowledge 检索 -> 冲突解决 -> 预算分配 -> 回执写入，职责持续膨胀。

**风险:** 单组件承担过多职责，测试复杂度 O(n^2)，任何子功能变更波及整体。

**建议 -- Pipeline 模式分解为 5 个 Stage:**

```
ContextAssemblyPipeline:
  Stage 1: MemoryRetriever     -- 读 Memory Core, 输出 personal_context
  Stage 2: KnowledgeRetriever  -- 读 Knowledge Stores, 输出 knowledge_context
  Stage 3: ConflictResolver    -- 冲突解决 (ADR-022 Knowledge 优先)
  Stage 4: BudgetAllocator     -- 动态预算分配 (ADR-035)
  Stage 5: ReceiptWriter       -- 写 retrieval_receipt + injection_receipt

每个 Stage:
  +-- 独立可测试（输入/输出明确）
  +-- Stage 1 & 2 可并行（已有设计, 01 Section 4.4）
  +-- Stage 3-5 顺序执行
  +-- 任意 Stage 故障有独立降级策略
```

> v1 代码按 Pipeline 组织（函数级拆分），v2 再考虑是否需要独立进程/服务。

### 4.2 风险 2: memory_items "append-only" 声明与 UPDATE 字段矛盾

**现状:** 01 Section 2.3 明确声明 `memory_items (versioned, append-only)`，但 DDL 中存在 `updated_at`、`invalid_at`（初始 null 后写入值）、`superseded_by`（初始 null 后写入值）——这些字段的写入语义是 UPDATE 而非 INSERT。

**风险:** 文档声明与实际数据操作不一致，影响审计可靠性和 CDC（Change Data Capture）设计。

**两种解决方案:**

| 方案 | 做法 | 适合场景 |
|------|------|---------|
| **A: 修正文档（推荐 v1）** | 将 "append-only" 改为 "append-mostly with controlled mutation"。明确允许 UPDATE 的字段白名单: `invalid_at`, `superseded_by`, `updated_at`。其余字段（content, confidence, version 等）仅通过新建版本实现变更 | 简单直接，实现成本低 |
| **B: 严格 append-only** | memory_items 完全不做 UPDATE。新增 `memory_item_events` 表记录状态变迁。物化视图或读模型计算最新有效状态 | 强审计需求，实现复杂度高 |

> 建议: v1 采用方案 A，v2 按审计需求评估是否演进为方案 B。

### 4.3 风险 3: 缺少 Control Plane / Data Plane 逻辑分离

**现状:** 管理操作（组织配置、成员管理、知识维护）和对话处理（Brain + Memory + Skill）共享同一进程/运行时。

**风险:**
- 管理操作的异常（如大批量知识导入）可能影响对话链路延迟
- 两类操作的 SLA 目标不同: 管理 99.9% 可接受，对话 99.95% 为底线
- 无法独立扩缩容

**建议:**

```
v1 逻辑分离（同进程，不同模块）:

  Control Plane (SLA: 99.9%):
    +-- 组织模型 CRUD (06 Section 2)
    +-- Settings 继承链计算 (06 Section 1.5)
    +-- Knowledge Write API (02 Section 7)
    +-- Experiment Engine (06 Section 5)
    +-- 用户/成员管理

  Data Plane (SLA: 99.95%):
    +-- 对话处理链路 (Brain -> Context Assembler -> Skill)
    +-- Memory Engine（读写）
    +-- Resolver 查询
    +-- LLM 调用

v2 物理分离:
  +-- Control Plane 独立服务，管理 API 路由到此
  +-- Data Plane 独立服务，对话/WebSocket 路由到此
  +-- 共享 PG（RLS 隔离）+ Redis + 事件总线
```

### 4.4 风险 4: Skill 框架缺少生命周期治理

**现状:** 03 Skill 层定义了 Skill 协议和能力标签，但缺少: 版本管理、健康检查、资源计量、上线/下线状态机。

**建议 -- SkillManifest + 状态机:**

```
SkillManifest:
  +-- skill_id, version, display_name
  +-- capabilities: Set[String]
  +-- dependencies: List[ToolId]
  +-- resource_budget: { max_tokens_per_call, max_tool_calls, max_execution_time_seconds }
  +-- required_permissions: [String]          -- "knowledge.read", "memory.write" 等
  +-- health_check: { endpoint, interval, timeout }
  +-- status: draft -> active -> deprecated -> disabled
  +-- registered_entity_types: List[EntityType]

状态机:
  draft      -> active      (部署 + 健康检查通过)
  active     -> deprecated  (标记废弃, 流量逐步迁移)
  deprecated -> disabled    (>= 2 个 minor version 后可禁用)
  active     -> disabled    (紧急下线, 需 owner/admin 权限)
  disabled   -> active      (重新启用)

计量:
  每次 Skill 调用记录:
    skill_id, version, org_id, token_consumed, tool_calls_count, latency_ms
  写入 skill_usage_records 表（类似 llm_usage_records）
```

### 4.5 风险 5: OLTP/OLAP 负载冲突

**现状:** Memory Core 的 PG 实例同时承受:
- **OLTP 热路径:** Context Assembler 每次对话读取、Observer 每次对话写入
- **近 OLAP 冷路径:** Evolution Pipeline 批量分析、Reconciliation Job 对账

**风险:** Evolution Pipeline 的全表扫描可能拖慢 Context Assembler 的索引查询。

**解法:**
- 短期: Evolution Pipeline 配置为低优先级，使用 PG 的 `statement_timeout` 和 `idle_in_transaction_session_timeout` 防止长事务阻塞热路径
- 中期: 利用 Streaming Replication 的 **Read Replica** 分流——OLTP 走 Primary，分析管线走 Standby。MemoryCorePort 内部按方法路由，Brain 层无感知

---

## 五、鲁棒性与安全性增强

### 5.1 级联失败的隐蔽路径

```
Qdrant 响应变慢（P95 从 50ms 涨到 2s，不是完全不可用）
-> Knowledge Stores 检索频繁超时
-> Context Assembler 频繁降级（缺少 knowledge_context）
-> 对话质量下降
-> 用户给出更多负反馈
-> 负反馈熔断误判: "这些记忆注入导致了坏结果"
-> 有效记忆被错误降权/撤销
-> 记忆质量退化
-> 对话质量进一步下降（即使 Qdrant 恢复了）
-> 恶性循环
```

**根因:** 负反馈熔断没有区分"记忆质量问题"和"知识降级导致的连带影响"。

**解法:** 引入降级免疫机制（见 P0-5）。降级期间的负反馈不触发熔断。

### 5.2 分布式时钟漂移

多处关键逻辑依赖时间戳（valid_at/invalid_at、tombstone requested_at、PIPL SLA、EWMA 窗口）。容器环境中 Worker 节点时钟偏差可达数秒。

**解法:** 所有业务时间戳统一使用 **PG 的 `now()`**（在事务中执行）。Worker 本地时钟仅用于日志和调试，不参与业务逻辑。

### 5.3 AI 安全（非信息安全）

当前 07 文档的安全设计聚焦于信息安全（RLS、加密、隔离）。AI Agent 有三个独特的安全威胁:

#### 威胁 1: 记忆投毒 (Memory Poisoning)

用户通过精心构造的对话向 Memory Core 注入虚假信息。例如反复暗示"我是 VIP 有特殊折扣"，记忆引擎可能将其提取为 preference。

**当前防御:** Quality Gateway + 负反馈熔断（被动）。

**缺失的主动防御:**
- 区分**声明性记忆**（用户说的）和**行为性记忆**（用户做的）
- 声明性记忆的置信度上限应低于行为性记忆
- "用户说'我喜欢简约风'" 不如 "用户过去 10 次选择都是简约风单品" 可信
- 与 Knowledge Stores 的事实矛盾时自动标记为可疑

#### 威胁 2: Prompt Injection via Memory

恶意用户在对话中嵌入 `Ignore all previous instructions...`，记忆引擎将其提取为 memory_item，下次对话 Context Assembler 注入该记忆，LLM 被劫持。

**防御:**
- memory_item 的 content 注入 context 前必须经过 **sanitization**（pattern-based + LLM-based 双重清洗）
- 注入时使用**结构化标签**界定记忆边界（`<user_memory>...</user_memory>`），严防与 system_prompt 混合
- 建立 **Provenance 可信度分级:** `observation(低) < analysis(中) < confirmed_by_user(高)`

#### 威胁 3: 跨租户信息泄露 via Promotion Pipeline

Promotion Pipeline 是跨 SSOT 的提案管线。若脱敏不完整:
- 个人记忆中的商业敏感信息（如"品牌 A 计划下季度转型运动品类"）
- 经 Promotion 提案到 Knowledge Stores，成为该品牌下所有用户可访问的知识
- 若竞争品牌的人有交叉组织成员身份...

**防御:**
- PII 脱敏: 已知模式（姓名、电话、地址）——当前已有
- **商业敏感信息脱敏:** 更难自动化，需行业特定规则
- Promotion Pipeline 审批流程中增加**"敏感信息分类标签"**，由审批者确认信息类别（个人偏好 / 商业机密 / 公开信息）
- 标记为"商业机密"的条目禁止通过 Promotion

---

## 六、向后兼容的工程底盘

ADR-033（兼容规则）和 ADR-034（Port 演进）已建立良好框架。平台化需要更深层的补充:

### 6.1 Schema Versioning

| 表 | 新增字段 | 用途 |
|----|---------|------|
| `memory_items` | `content_schema_version INTEGER DEFAULT 1` | 应对 preference 结构演进 |
| `event_outbox` | `payload_version INTEGER DEFAULT 1` | 应对 Worker 升级时未消费的旧版本事件兼容 |
| `memory_receipts` | `details_schema_version` 从 2 升 3 | 容纳注入五元组扩展字段 |

### 6.2 兼容性测试矩阵

建立**持久化数据兼容测试套件**:
- 保存每个版本的样本数据（Fixture）
- CI 中验证 N+1 版本代码能正确处理所有历史版本的数据
- 覆盖: memory_items、event_outbox payload、receipt details
- 这比接口测试更难但更关键（数据一旦写入就无法轻易迁移）

### 6.3 MemoryItem Schema v2 迁移

注入五元组需要扩展 injection_receipt 的 details 结构，触发 `details_schema_version` 从 2 升到 3。迁移步骤（遵循 ADR-033 Expand-Contract）:

1. **Expand:** 新增字段（五元组），`details_schema_version = 3`。旧代码忽略新字段
2. **Migrate:** 逐步将新写入切换到 v3 格式。旧数据保持 v2 不迁移
3. **Contract:** 待所有消费端升级后，移除 v2 兼容分支（最小 2 个 minor version 后）

---

## 七、平台化底盘与未来演进

### 7.1 Phase 0: 设计与基础（立即执行）

实施 P0-1 至 P0-5 的核心工程，以及以下预防性基础设施:

| 项目 | 说明 | 复杂度 |
|------|------|--------|
| 数据库 version 字段 | memory_items 增加 `content_schema_version`，event_outbox 增加 `payload_version` | 低 |
| 业务时间戳统一 | 全部使用 PG `now()`，Worker 不用本地时钟 | 低 |
| Tier 语义解耦 | RLS 只依赖 `path` + `depth`，tier 名称由应用层映射 | 中 |
| 降级免疫机制 | `degraded_reason` 非空时排除负反馈 SLI | 低 |
| Skill Registry 扩展 | 预留 `skill_api_version` + `required_permissions` + `resource_quota` 字段 | 低 |
| 用户删除 API 端点 | `DELETE /api/v1/me/memories`（用户 API 分区，归属 Data Plane） | 低 |

### 7.2 Phase 1: 稳定性与 v1 实现

| 项目 | 说明 |
|------|------|
| Brain Executor 分区 | 对话热路径与记忆进化冷路径在协程/线程池层面隔离 |
| Memory Core 读写分离 | OLTP 走 Primary，Evolution/Reconciliation 走 Read Replica |
| CP/DP 逻辑分离 | 管理操作与对话处理在模块层面隔离（同进程），SLA 目标差异化 |
| Context Assembler Pipeline 分解 | 5 Stage 函数级拆分（MemoryRetriever / KnowledgeRetriever / ConflictResolver / BudgetAllocator / ReceiptWriter） |
| 注入策略实施 | P0-2 评测集 + 五元组 + 发布门槛，通过 Experiment Engine 灰度发布 |
| 预算算法实施 | P0-3 确定性算法 + 截断顺序 + EWMA/Hysteresis，通过 Experiment Engine 灰度发布 |
| 删除管线完善 | P0-4 状态机 + Deletion Fence + Worker 断点恢复 |
| 评测驱动开发 (EDD) | 建立 Golden Dataset，发版前自动跑评测作为发布门禁 |
| 记忆 Provenance 分级 | `observation(低) < analysis(中) < confirmed_by_user(高)` |
| 注入前 Sanitization | Pattern-based + LLM-based 双重清洗 + 结构化标签隔离 |
| append-only 文档修正 | 01 Section 2.3 改为 "append-mostly with controlled mutation"，明确 UPDATE 白名单 |

### 7.3 Phase 2: 增强与扩展

| 项目 | 说明 |
|------|------|
| 多模型多窗口支持 | 重构 Context Assembler，引入 AssemblyProfile，支持一次对话多次异构 LLM 调用 |
| 成本控制体系 | 三策略: (1) **模型降级策略**——意图理解/记忆分析/合规检查用小模型，仅内容生成用大模型，LLMCallPort 增加 `model_selection_hint` (quality/balanced/economy); (2) **语义缓存**——相似问题复用响应; (3) **Prompt 压缩**——接近窗口上限时先压缩低优先级 slot（摘要化），压缩比截断丢失信息少 |
| Skill 生命周期治理 | SkillManifest + 状态机（draft/active/deprecated/disabled）+ skill_usage_records 计量 |
| Skill 异步增强 | 支持异步执行 + 流式结果返回 + 中间状态回调（为 Multi-Agent 铺路） |
| Task Orchestration 预留 | Brain 第 6 个扩展能力槽位: 异步长任务管理 |
| BookmarkPort 预留 | Knowledge -> Memory 引用通道（不复制数据），保持隐私硬边界 |
| Memory Governor | 复用 Gateway 限流基础设施 + Memory Core 侧 Semaphore 并发控制; 封装 01 Section 2.3.2 治理规则为独立组件 |
| 长上下文片段排序 | 相关性最高放首尾，利用 U-shaped attention bias |
| 故障注入演练 | 删除 Worker 超时、重复投递 Outbox、Memory Core PG failover |
| 冷热存储分层 | `invalid_at` 超 90 天归档至冷存储 |
| 持久化兼容测试套件 | 每版本 Fixture + CI 验证跨版本数据读取 |
| CP/DP 物理分离 | Control Plane 和 Data Plane 拆为独立服务 |

### 7.4 Phase 3: 平台化启动

| 项目 | 说明 |
|------|------|
| Capability Registry | 统一注册中心，整合 Skill/Tool/Model/EntityType 四类注册。每个注册项含 id/version/status/health/dependencies/owner_org_id/metrics。支持按类型/状态/能力标签查询、依赖图可视化、健康看板 |
| 行业抽象层 | 引入 `IndustryTemplate`（配置化定义 org 深度、Tier 类型、Knowledge Schema 预设、Skill 套件、默认 Settings） |
| Tenant Lifecycle | 完整状态机: provisioning -> active -> suspended -> terminating -> terminated。含初始化（创建 org_tree + Knowledge namespace）、暂停（数据保留 30 天，API 返回 403）、终止（数据导出 + 逐存储清理，复用 P0-4 删除管线模式） |
| Skill SDK + 沙箱 | 第三方开发者开发框架 + 安全隔离执行环境 + 版本管理 + 权限/资源配额校验 |
| Public API | OAuth2 + API Key 认证; 显式版本路由 (/v1/, /v2/ 并行); per-API-key 限流; OpenAPI spec + 开发者门户 |
| Multi-Agent 编排 | Agent-to-Agent 通信协议; 图结构编排层（参照 LangGraph） |
| 可解释性面板 | injection_receipt 增加 `explanation_trace` 字段——记录每个注入记忆和知识片段对最终输出的影响权重（**零额外 LLM 调用成本**，只需 Context Assembler 记录"选了什么、为什么选、相关性分数是多少"）。前端据此展示"AI 决策依据" |
| Memory 运维仪表盘 | 核心维度对齐 7 项 SLI，按 tenant -> org -> user 下钻 |
| 自动根因分类 | 优先做"误注入原因分类"（积累 P0 评测数据后自然可做），其他延后 |
| Event Mesh 演进 | Phase 1: PG Outbox + Celery（当前，< 1000/s）; Phase 2: PG Outbox + NATS/Kafka（多消费者组、事件回放）; Phase 3: Event Mesh + Schema Registry（Avro/Protobuf 事件 schema、跨服务事件发现、事件血缘追踪） |

---

## 八、ADR（架构决策记录）建议

> 08 附录 B 当前 ADR 编至 037（PIPL/GDPR 删除管线）。后续新增从 038 起编。

采用伞形 ADR 合并方案（详见第三章 3.5 节），从 4 个独立 ADR 收敛为 2 个:

| 编号 | 主题 | 子决策 | 与现有 ADR 的关系 |
|------|------|--------|------------------|
| **ADR-038** | Runtime Governance | **038.1** Injection Correctness Gate: 五元组 + 分阶段 eval set (200->500->1000) + precision/recall 双轨门禁 + Experiment Engine 灰度 | 与 ADR-036 互补: 036 定义指标，038 定义评测与门禁 |
| | | **038.2** Dynamic Budget Allocator: 不可压缩槽位定义 + safety_margin + TruncationPolicy 策略接口 + EWMA/Hysteresis + 回退策略 | 实现 ADR-035（框架级），038.2 是算法实现级 |
| | | **038.3** SLO/SLI Framework: 7 SLIs + burn-rate 双窗口告警 + 最小样本量阈值 + 降级免疫 + SLI-to-Loop 映射 | 基于 ADR-036 的 MWMBR 模式 |
| **ADR-039** | Data Lifecycle Governance | **039.1** Deletion State Machine: 8 态 + deletion_fence_version + verified 前置校验 | 引用 ADR-037（删除范围），039.1 定义状态机形式化 |
| | | **039.2** Worker Idempotency: 双层幂等 (outbox UNIQUE + receipt 消费侧去重) + 断点恢复 (progress checkpoint) | 新增 |
| | | **039.3** Legal Profile Configuration: legal_profiles 表 + 法域可配置 SLA + 阶梯告警模板 | 新增，PIPL/GDPR 差异化处理 |

> 每个子决策保留独立的 Context/Decision/Consequences 结构，确保决策考古可追溯。

---

## 九、杂项与修正

### 9.1 Gateway 联动

05 Section 4.2 OrgContext Schema v1 已包含 model_access 子结构。P0-3 动态预算分配器（Brain 层）与 Gateway 层的 Token Cost Budget 是正交维度，无需修改 Gateway 层。但 P0-5 SLO 新增 SLI 的告警指标采集点可能需要在 Gateway 层增加 Prometheus exporter。

### 9.2 Memory Governor 预留

01 Section 2.3.2 已定义治理规则（staleness_rate > 20% 触发清理、conflict_rate > 10% 触发 LLM resolution）。建议后续将此治理逻辑封装为 MemoryGovernor 组件，与 ContextAssemblyPipeline 的 Stage 分解协同设计。

### 9.3 用户发起删除的 API 端点

07 Section 5.2 声明"用户有权删除自己的记忆"。建议明确 REST 端点: `DELETE /api/v1/me/memories`（用户 API 分区，非 admin），归属 Data Plane。

### 9.4 memory_receipts.details 的 JSONB schema_version

已落地（06 Section 9, 06:573）: `details_schema_version INTEGER DEFAULT 1`。读取时按 version 分支解析。details 内部按 receipt_type 结构化（retrieval / injection / promotion），兼容规则遵循 ADR-033。

---

## 十、风险提示与管理要素

### 10.1 实施风险

| 风险 | 说明 | 缓解措施 |
|------|------|---------|
| P0 并行工作量 | 5 个 P0 全并行风险高 | 按法律风险优先级排序（P0-4 > P0-2 > P0-5 > P0-3 > P0-1），可并行的技术批次: Batch 1 (P0-1 + P0-5) -> Batch 2 (P0-4) -> Batch 3 (P0-2 + P0-3) |
| 评测集瓶颈 | 500 条真实/脱敏样本需运营配合 | 尽早启动样本收集，不是纯工程任务 |
| Deletion Fence 热点 | 全局 fence 可能成为写入瓶颈 | 按 `user_id` 分片，不做全局 fence |
| Schema 迁移复杂度 | details_schema_version 2->3 触发 Expand-Contract | 遵循 ADR-033 三阶段迁移，最小 2 个 minor version 过渡期 |
| PIPL SLA 精度 | 当前文档写 30 天（GDPR），PIPL 法条原文为"及时"未写死天数 | legal_profile 可配置，默认按最严格内部 SLA (15 工作日) 执行 |

### 10.2 跨文档影响矩阵

从原计划的 **4 文档（01/06/07/08）扩充为 5 文档（00/01/06/07/08）**。

| 变更项 | 影响文档 | 变更类型 |
|--------|---------|---------|
| P0-1 PK 统一 | 01 (Section 2.3.1, 3.1, 3.3), 08 (ADR-038) | 兼容变更（Expand-Contract） |
| P0-2 注入正确性 | 01 (Section 4.1), 06 (Section 9), 08 (ADR-038.1) | 新增字段（兼容） |
| P0-3 动态预算 | 01 (Section 4.2.1) -- 已落地 v3.4 | 已完成（补充截断顺序） |
| P0-4 删除管线 | 01 (Section 3.1.1), 06 (Section 9), 07 (Section 5.2), 08 (ADR-037/039) | 增强（状态机扩展 + legal_profile 可配置 SLA） |
| P0-5 SLO | 01 (Section 2.3.2), 08 (附录 D, ADR-038.3) | 需补充 Prometheus/Grafana 到技术栈 |
| 风险 1 Pipeline 分解 | 01 (Section 4) | 实现层重构，不影响 Port 契约 |
| 风险 2 append-only 修正 | 01 (Section 2.3) | 文档措辞修正 |
| 风险 3 CP/DP 分离 | 05 (Section 4.1), 07 (Section 3) | v1 逻辑分离，v2 物理分离 |
| 风险 4 Skill 治理 | 03, 08 (附录 D) | 新增 SkillManifest + 状态机 |
| 风险 5 OLTP/OLAP | 07 (Section 6.1) | Read Replica 配置建议 |
| 降级免疫 | 00 (降级矩阵) | 新增降级免疫规则 |
| AI 安全 | 07 (Section 5) | 新增 3 威胁 + 防御策略 |
| 时钟纪律 | 06 (Section 9 注释) | 工程纪律补充 |

### 10.3 核心判断

**DIYU 的双 SSOT 隐私架构 + 组织树治理模型 + 记忆进化管线是真正的差异化壁垒。** 平台化不是重建这些，而是给它们加上版本化、沙箱化、模板化的外壳，让第三方能在不破坏内核的前提下扩展系统能力。

---

> **变更追踪清单:**
>
> **v2.0 合并 (报告 A + 报告 B):**
> - 报告 A 独有内容（14 处）-- 全部纳入
> - 报告 B 独有内容（18 处）-- 全部纳入
> - 冲突项协调（6 处）-- 全部裁决
>
> **v3.0 评审修订 (13 条评审意见):**
> - #1 PIPL SLA 可配置: legal_profile 表 + 法域驱动 SLA -- **已纳入 P0-4**
> - #2 评测集分阶段: 200->500->1000 + 每阶段绑定 gate 阈值 -- **已纳入 P0-2**
> - #3 截断约束优化: TruncationPolicy 策略接口，P0 固定优先级，P1 约束优化 -- **已纳入 P0-3**
> - #4 ADR 合并: 4 ADR -> 2 伞形 ADR + 子编号 -- **已纳入第八章**
> - #5 append-mostly: DDL 白名单注释 -- **已在 v2.0 纳入**
> - #6 Governance Loop: 双 Loop + 共享治理层 (部分不同意单一 Loop) -- **已纳入第三章**
> - #7 recall@inject: 分阶段门禁 (P0 观测 / P1 门禁) + F1 指标 -- **已纳入 P0-2**
> - #8 5-tuple context_position: 已在 v2.0 纳入，补充 Lost in the Middle 归因论证 -- **确认保留**
> - #9 SLA by legal_profile: 补充 DDL + SLA 计算逻辑 + 告警触发规则 -- **已纳入 P0-4**
> - #10 verified 删除状态: 已在 v2.0 纳入，补充授权决策显式化论证 -- **确认保留**
> - #11 idempotency_key 双层幂等: outbox 生产者去重 + receipt 消费者去重 + DDL -- **已纳入 P0-5**
> - #12 不可压缩槽位 + safety_margin: 显式定义 + fail-fast 启动检查 -- **已纳入 P0-3**
> - #13 验收标准数值化: 11 项 PASS/FAIL 阈值 + 灰区处理 + 验收流程 -- **已纳入 2.6**
