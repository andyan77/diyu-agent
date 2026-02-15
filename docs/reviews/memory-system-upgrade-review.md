# DIYU AGENT 系统观察、思考与补全优化建议报告

> **版本:** v1.0 (Final)
> **日期:** 2026-02-08
> **范围:** 基于 v3.4 架构文档的生产化升级方案可行性论证 + 系统深层观察
> **涉及文档:** 00(总览)、01(Brain)、06(基础设施)、07(部署安全)、08(附录)

---

## 一、总体评估与架构定位

### 1.1 方案定位

当前 v3.4 文档的架构设计质量在上游水平（双 SSOT、Port 抽象、降级矩阵、ADR 体系），准确识别了从"设计合理"到"生产可运维"在"可证伪性"维度的缺口。方案核心理念（注入评测、确定性预算、删除状态机、SLO burn-rate）均有明确业界对标，非过度设计。

**业界对标参照:**

| 理念 | 对标实践 |
|------|---------|
| 注入正确性评测 | Mem0 LoCoMo benchmark (66.9%)、BudgetMem (ICLR 2025) |
| 确定性预算算法 | VMware Resource Governor (Reservation/Limit/Shares)、MemGPT 分层管理 |
| 删除状态机 | EventStoreDB tombstone + Temporal idempotency、AWS Step Functions |
| SLO burn-rate | Google SRE Workbook MWMBR 模式（已被 Grafana/Datadog 原生支持） |

### 1.2 潜在约束（隐含假设）

尽管质量上乘，但在系统规模增长与平台化演进中，架构存在五个"设计时合理、演进时受限"的隐含假设:

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

Tier 语义与 RLS 策略深度绑定（`path <@ current_setting('app.current_org_path')::ltree`）。06 Section 1.6.1 已评估结论为"V2 规划"，但平台化要求更早准备。

> 建议: v1 保持 5 层不变，但将 tier 语义从 RLS 中解耦——RLS 只依赖 `path` 和 `depth`，不依赖 tier 名称。tier 名称变成纯展示信息，由应用层映射。

**假设 5: 对话模式假设为同步**

缺乏对长任务（批量文案生成、跨会话分析、持续监控任务）的异步编排能力。当前 content_tasks 有 `status` 字段可勉强支持，但 Brain 的对话引擎没有"长任务管理"能力。

> 建议: 在 Brain 的 5 大固有能力之外，预留第 6 个扩展能力槽位——**Task Orchestration**（异步启动 + 进度跟踪 + 中间结果交付 + 结果通知）。与 Skill Dispatch 的区别: Skill Dispatch 是同步"做一件事然后返回"，Task Orchestration 是异步"启动 -> 跟踪 -> 交付"。

---

## 二、核心升级方案: 生产可证伪、可观测、可回滚 (P0 级)

### P0-1: 统一数据契约命名 (Schema Alignment)

**现状:** `memory_id` (Brain 消费端)、`item_id` (DDL 存储端)、`memory_item_id` (Qdrant payload) 三名并存。v3.4 澄清了映射关系，但三个名字仍是实现歧义源。

**建议:**
- 统一收敛为 **`memory_id`**（消费端视角，符合 DDD ubiquitous language）
- Port 接口（MemoryItem schema v1）已用此名，这是对外契约
- `item_id` 降级为 DDL 内部实现细节（Port 实现层负责映射）
- Qdrant payload 中的 `memory_item_id` 改为 `memory_id`
- 兼容别名弃用期: **2 个 minor version**（对齐 ADR-034 deprecation 周期）

**影响范围:** 01（MemoryItem schema）、06（DDL 注释）、01 Section 3.3（Qdrant payload）。无需改 07。

---

### P0-2: 记忆注入正确性闭环 (Injection Correctness)

**优化目标:** 解决缺乏完整注入判定记录、离线评测集和发布门槛的问题。

#### 判定记录扩展（五元组）

| 字段 | 类型 | 说明 |
|------|------|------|
| `candidate_score` | Float | 候选记忆的相关性得分 |
| `decision_reason` | Enum | 注入/不注入的判定原因 |
| `policy_version` | String | 当前注入策略版本号（联动 Experiment Engine） |
| `guardrail_hit` | Boolean + String | 是否触发安全护栏 + 原因 |
| `context_position` | String | 注入到上下文的位置区间（应对 Lost-in-the-middle） |

> `context_position` 是关键新增。业界研究明确证实 LLM 对上下文中间位置的信息注意力下降（Claude 2.1 中间位置 accuracy 降至 27%）。记录注入位置是后续优化排序策略的数据基础。

#### 评测集建设

- **最小可行集: 500 条**（200 正样本 + 200 负样本 + 100 边界样本）
- 覆盖: 单轮/多轮、preference/pattern/insight 三种 memory_type、冲突/无冲突场景
- **持续维护机制（双通道）:**
  - 被动收集: 每次 `user_correction_rate` 触发熔断时，自动将脱敏样本加入评测集
  - 主动审计: **月度审计评测集分布**，确保覆盖度均衡（避免偏向"失败案例"，缺少"正确注入"的持续补充）

#### 发布门槛

| 指标 | 阈值 | 说明 |
|------|------|------|
| `precision@inject` | >= 0.75 | 注入精确率（参照 Mem0 66.9% + 改进空间） |
| `recall@inject` | >= 0.60 | 注入召回率（避免过于保守导致记忆形同虚设） |
| `false_injection_rate` | <= 0.10 | 误注入率 |
| `user_correction_rate` | <= 0.05 | 用户纠正率（已在 SLI 中定义） |

#### 与 Experiment Engine 联动（关键补充）

注入策略变更和预算算法变更**必须通过 Experiment Engine（06 Section 5）灰度发布，不可全量直切**。具体:
- 注入策略变更走"Brain 路由策略"实验维度
- 预算算法变更走"Knowledge 检索策略"实验维度
- 灰度比例: 初始 10% 流量（按 tenant 分流），SLI 达标后逐步放量
- 回滚条件: 任一门槛指标跌破阈值，自动回滚到旧策略版本

---

### P0-3: 动态预算器工程化 (Dynamic Budgeting)

#### 核心算法: hard_reserved + dynamic_pool

```
total_budget = model_context_window - safety_margin(15%)
hard_reserved = sum(slot.min for slot in all_slots)
dynamic_pool = total_budget - hard_reserved

for each elastic_slot ordered by priority:
  allocation = slot.min + dynamic_pool * slot.weight * signal_modifier
  allocation = clamp(allocation, slot.min, slot.max)
```

#### 稳定性控制

- **EWMA:** 平滑系数 alpha = 0.3（经验值，平衡响应速度与稳定性）
- **Hysteresis:** Slot 在 `target +/- 10%` 范围内不触发重分配
- 具体数值作为 RULE 级配置（可按租户调整），默认值硬编码

#### 超窗截断优先级（由先截断到最后截断）

| 优先级 | Slot | 原因 |
|--------|------|------|
| 1 | knowledge_context | 软依赖，降级影响最小 |
| 2 | summary_blocks | 可重新摘要 |
| 3 | entity_slots | 可从近期对话重建 |
| 4 | active_window | 压缩最早的 turn |
| 5 | personal_context | 核心差异化，尽可能保留 |
| 6 | system_prompt | **不可截断** |
| 7 | user_input | **不可截断** |
| 8 | generation_budget | **不可截断** |

> **关键策略:** 截断 active_window 时采用**"首尾保留 + 中间摘要"**策略——保留最早 1 turn + 最近 N turn，中间部分摘要化。利用 LLM 的 U-shaped attention bias（对首尾信息注意力最高）。

#### 回退机制

- 分配算法异常 -> 退回 Section 4.2 静态基线（硬编码兜底）
- 模型窗口探测失败 -> 查本地静态表（按 `model_family` 维护，非按 model_id，避免新模型发布时都需更新）
- 探测方式: 首选 LiteLLM SDK 的 `model_info` API，失败则查静态表

---

### P0-4: 删除管线闭环 (PIPL/GDPR Deletion)

#### 状态机优化（统一为 6 状态）

```
requested -> active -> processing -> completed
                                  -> failed -> retry_pending -> processing (loop)
                                            -> escalated (重试耗尽)
```

| 状态 | 含义 | 时效 |
|------|------|------|
| `requested` | API 收到请求 | 同步，秒级 |
| `active` | tombstone 已写入，数据对用户不可见 | 同步，秒级 |
| `processing` | Worker 正在执行物理删除 | 异步 |
| `completed` | 全部存储位置删除完成 | -- |
| `failed` / `retry_pending` | 某存储位置失败，等待重试 | 指数退避 |
| `escalated` | 重试耗尽（上限 5 次），需人工介入 | -- |

#### 写端屏障 (Deletion Epoch)

当前竞态防护仅在 Evolution Pipeline 侧做 tombstone 检查（读端屏障）。增加**写端屏障**:

- `deletion_epoch`: 单调递增版本号，每次删除请求 bump
- 所有写入操作携带当前 epoch，写入时对比存储侧 epoch
- 若 `request_epoch < storage_epoch`，拒绝写入（被删除请求覆盖）
- 与 ADR-024 的 FK `version` 防冲突模式一致
- **Epoch 按 `user_id` 分片**，避免全局热点

#### Worker 幂等与断点恢复

- **幂等:** 基于 `request_id`，通过 inbox 表检查已处理状态
- **断点恢复:** Worker 执行时维护 `progress` 字段（JSON，记录每个存储位置的完成状态）。重启后从 `progress` 恢复，跳过已完成的存储位置，避免重复执行已完成的删除操作（幂等 + 增量）

#### SLA 阶梯告警

| 时间点 | 动作 |
|--------|------|
| Day 7 | 首次检查，`processing` 超 7 天 -> 内部告警 |
| Day 14 | 仍在 `processing` -> 升级告警（团队 Lead） |
| Day 25 | 仍未完成 -> 紧急告警（合规团队） |
| Day 30 | PIPL 硬限，必须完成 |

#### Day-2 增强: Crypto Shredding

物理删除在分布式系统中很难保证 100% 覆盖（备份、日志、CDN 缓存等）。Crypto shredding 作为补充方案:
- 为每个 user 生成独立加密密钥（HashiCorp Vault 管理）
- PII 字段使用用户密钥加密存储
- 删除时销毁密钥 = 数据不可访问
- 纳入 P2 路线图

---

### P0-5: 可观测性升级到 SLO 级

#### 指标对齐（7 项 SLI）

| SLI | 定义 | SLO | 来源 |
|-----|------|-----|------|
| `staleness_rate` | invalid_at < now() 且未物理删除的占比 | < 15% | 保留（原有） |
| `conflict_rate` | superseded_by 链长 >= 3 的条目占比 | < 10% | 保留（原有） |
| `injection_quality` | hit_rate * (1 - correction_rate) | > 0.57 | 合并（原 hit_rate + correction_rate） |
| `retrieval_latency_p95` | retrieval_receipt.latency_ms P95 | < 200ms | 保留（原有） |
| `context_overflow_rate` | budget_allocation 中任一 slot 被截断的请求占比 | < 5% | **新增** |
| `deletion_timeout_rate` | tombstone.status != 'completed' && age > 25 days 的占比 | 0% | **新增** |
| `receipt_completeness_rate` | 对话请求中缺少对应 injection_receipt 的占比 | < 1% | **新增** |

#### 字段优化

- `idempotency_key`: 放入 **`event_outbox`** 表（投递保障职责），而非 receipt 表（观测记录职责）
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

## 三、鲁棒性、兼容性与安全性增强

### 3.1 鲁棒性问题与解法

#### 问题 1: 级联失败的隐蔽路径

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

#### 问题 2: OLTP/OLAP 负载冲突

Memory Core 的 PG 实例同时承受:
- **OLTP 热路径:** Context Assembler 每次对话读取、Observer 每次对话写入
- **近 OLAP 冷路径:** Evolution Pipeline 批量分析、Reconciliation Job 对账

两种负载在同一 PG 实例竞争资源。Evolution Pipeline 的全表扫描可能拖慢 Context Assembler 的索引查询。

**解法:**
- 短期: Evolution Pipeline 配置为低优先级，使用 PG 的 `statement_timeout` 和 `idle_in_transaction_session_timeout` 防止长事务阻塞热路径
- 中期: 利用 Streaming Replication 的 **Read Replica** 分流——OLTP 走 Primary，分析管线走 Standby。MemoryCorePort 内部按方法路由，Brain 层无感知

#### 问题 3: 分布式时钟漂移

多处关键逻辑依赖时间戳（valid_at/invalid_at、tombstone requested_at、PIPL 30 天 SLA、EWMA 窗口）。容器环境中 Worker 节点时钟偏差可达数秒。

**解法:** 所有业务时间戳统一使用 **PG 的 `now()`**（在事务中执行）。Worker 本地时钟仅用于日志和调试，不参与业务逻辑。

---

### 3.2 向后兼容的工程底盘

ADR-033（兼容规则）和 ADR-034（Port 演进）已建立良好框架。平台化需要更深层的补充:

#### Schema Versioning

| 表 | 新增字段 | 用途 |
|----|---------|------|
| `memory_items` | `content_schema_version INTEGER DEFAULT 1` | 应对 preference 结构演进（v1 可能只有 {key,value}，v2 增加 {confidence_source, extraction_method}） |
| `event_outbox` | `payload_version INTEGER DEFAULT 1` | 应对 Worker 升级时未消费的旧版本事件兼容 |
| `memory_receipts` | `details_schema_version` 从 2 升 3 | 容纳注入五元组扩展字段 |

#### 兼容性测试矩阵

建立**持久化数据兼容测试套件**:
- 保存每个版本的样本数据（Fixture）
- CI 中验证 N+1 版本代码能正确处理所有历史版本的数据
- 覆盖: memory_items、event_outbox payload、receipt details
- 这比接口测试更难但更关键（数据一旦写入就无法轻易迁移）

#### MemoryItem Schema v2 迁移

注入五元组需要扩展 injection_receipt 的 details 结构，触发 `details_schema_version` 从 2 升到 3。迁移步骤（遵循 ADR-033 Expand-Contract）:

1. **Expand:** 新增字段（五元组），`details_schema_version = 3`。旧代码忽略新字段
2. **Migrate:** 逐步将新写入切换到 v3 格式。旧数据保持 v2 不迁移
3. **Contract:** 待所有消费端升级后，移除 v2 兼容分支（最小 2 个 minor version 后）

---

### 3.3 AI 安全 (非信息安全)

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
- 经 Promotion 提案到 Knowledge Stores
- 成为该品牌下所有用户可访问的知识
- 若竞争品牌的人有交叉组织成员身份...

**防御:**
- PII 脱敏: 已知模式（姓名、电话、地址）——当前已有
- **商业敏感信息脱敏:** 更难自动化，需行业特定规则
- Promotion Pipeline 审批流程中增加**"敏感信息分类标签"**，由审批者确认信息类别（个人偏好 / 商业机密 / 公开信息）
- 标记为"商业机密"的条目禁止通过 Promotion

---

## 四、平台化底盘与未来演进 (Phase 0-3)

### Phase 0: 设计与基础（立即执行）

实施 P0-1 至 P0-5 的核心工程，以及以下预防性基础设施:

| 项目 | 说明 | 复杂度 |
|------|------|--------|
| 数据库 version 字段 | memory_items 增加 `content_schema_version`，event_outbox 增加 `payload_version` | 低 |
| 业务时间戳统一 | 全部使用 PG `now()`，Worker 不用本地时钟 | 低 |
| Tier 语义解耦 | RLS 只依赖 `path` + `depth`，tier 名称由应用层映射 | 中 |
| 降级免疫机制 | `degraded_reason` 非空时排除负反馈 SLI | 低（一行判断） |
| Skill Registry 扩展 | 预留 `skill_api_version` + `required_permissions` + `resource_quota` 字段 | 低 |

### Phase 1: 稳定性与 v1 实现

| 项目 | 说明 |
|------|------|
| Brain Executor 分区 | 对话热路径与记忆进化冷路径在协程/线程池层面隔离 |
| Memory Core 读写分离 | OLTP 走 Primary，Evolution/Reconciliation 走 Read Replica |
| 注入策略实施 | P0-2 评测集 + 五元组 + 发布门槛，通过 Experiment Engine 灰度发布 |
| 预算算法实施 | P0-3 确定性算法 + 截断顺序 + EWMA/Hysteresis，通过 Experiment Engine 灰度发布 |
| 删除管线完善 | P0-4 状态机 + Deletion Epoch + Worker 断点恢复 |
| 评测驱动开发 (EDD) | 建立 Golden Dataset（每核心场景维护"输入-预期输出"黄金样本），发版前自动跑评测作为发布门禁 |
| 记忆 Provenance 分级 | `observation(低) < analysis(中) < confirmed_by_user(高)` |
| 注入前 Sanitization | Pattern-based + LLM-based 双重清洗 |

### Phase 2: 增强与扩展

| 项目 | 说明 |
|------|------|
| 多模型多窗口支持 | 重构 Context Assembler，引入 AssemblyProfile，支持一次对话多次异构 LLM 调用 |
| 成本控制体系 | 三策略: (1) **模型降级策略**——意图理解/记忆分析/合规检查用小模型，仅内容生成用大模型，LLMCallPort 增加 `model_selection_hint` (quality/balanced/economy); (2) **语义缓存**——相似问题复用响应; (3) **Prompt 压缩**——接近窗口上限时先压缩低优先级 slot（摘要化），压缩比截断丢失信息少 |
| Skill 异步增强 | 支持异步执行 + 流式结果返回 + 中间状态回调（为 Multi-Agent 铺路） |
| Task Orchestration 预留 | Brain 第 6 个扩展能力槽位: 异步长任务管理（启动 -> 进度跟踪 -> 中间结果交付 -> 完成通知） |
| BookmarkPort 预留 | Knowledge -> Memory 引用通道（不复制数据），保持隐私硬边界 |
| P1 落地 | Memory Governor（复用 Gateway 限流基础设施 + Memory Core 侧 Semaphore 并发控制）; 长上下文片段排序（相关性最高放首尾，利用 U-shaped attention bias） |
| P2 落地 | 故障注入演练（删除 Worker 超时、重复投递 Outbox、Memory Core PG failover）; 冷热存储分层（`invalid_at` 超 90 天归档至冷存储） |
| 持久化兼容测试套件 | 每版本 Fixture + CI 验证跨版本数据读取 |

### Phase 3: 平台化启动

| 项目 | 说明 |
|------|------|
| 行业抽象层 | 引入 `IndustryTemplate`（配置化定义组织树深度、Tier 类型、Knowledge Schema 预设、Skill 套件、默认 Settings） |
| Skill SDK + 沙箱 | 第三方开发者开发框架 + 安全隔离执行环境 + 版本管理 + 权限/资源配额校验 |
| Public API | OAuth2 + API Key 认证; 显式版本路由 (/v1/, /v2/ 并行); per-API-key 限流; OpenAPI spec + 开发者门户 |
| Multi-Agent 编排 | Agent-to-Agent 通信协议; 图结构编排层（参照 LangGraph） |
| 可解释性面板 | injection_receipt 增加 `explanation_trace` 字段——记录每个注入记忆和知识片段对最终输出的影响权重（**零额外 LLM 调用成本**，只需 Context Assembler 记录"选了什么、为什么选、相关性分数是多少"）。前端据此展示"AI 决策依据" |
| Memory 运维仪表盘 | 核心维度对齐 7 项 SLI，按 tenant -> org -> user 下钻 |
| 自动根因分类 | 优先做"误注入原因分类"（积累 P0 评测数据后自然可做），其他延后 |

---

## 五、ADR (架构决策记录) 建议

| 编号 | 主题 | 核心内容 | 与现有 ADR 的关系 |
|------|------|---------|------------------|
| **ADR-038** | Memory Injection Correctness Gate | 定义评测集规范 + 发布门槛（precision/recall）+ 五元组记录 + Experiment Engine 灰度发布路径 | 与 ADR-036（SLI/SLO 定义）互补: 036 定义指标，038 定义评测与门禁 |
| **ADR-039** | Dynamic Budget Allocator Deterministic Algorithm | 明确公式、截断优先级、EWMA 参数、Hysteresis 带宽、回退策略、首尾保留截断策略 | 实现 ADR-035（框架级），039 是算法实现级 |
| **ADR-040** | Deletion State Machine & Idempotency | 形式化 6 状态机 + Deletion Epoch 写端屏障 + Worker 断点恢复 + SLA 阶梯告警 | 引用 ADR-037（删除范围和流程），040 定义状态机形式化和幂等保障 |
| **ADR-041** | Memory SLO & Alerting Policy | 7 项 SLI 具体阈值 + burn-rate 告警配置 + 升级链路 + On-call rotation + 降级免疫规则 | 基于 ADR-036 的 MWMBR 模式，041 定义具体运维策略 |

---

## 六、验收标准（可证伪性）

| 验收标准 | 证伪方法 | 判定依据 |
|---------|---------|---------|
| "记忆被注入且注入正确" | 跑评测集（500 条） | `precision@inject >= 0.75` 且 `recall@inject >= 0.60`，否则 FAIL |
| "不会挤爆窗口且波动可控" | 构造边界场景（超长对话 + 丰富记忆 + 密集知识） | 截断顺序正确执行，`context_overflow_rate` SLO 达标，否则 FAIL |
| "删除可追踪、可完成、不可恢复" | 执行删除后直接查 PG/Qdrant/Redis 确认数据不存在 | tombstone 状态完整流转至 `completed`，物理验证数据不存在，否则 FAIL |
| "故障时可降级、可告警、可回滚" | 模拟 PG Failover、Knowledge 超时、Budget Allocator 异常 | 降级行为正确触发，告警在预期时间内发出，Experiment Engine 自动回滚，否则 FAIL |

---

## 七、风险提示与管理要素

### 7.1 实施风险

| 风险 | 说明 | 缓解措施 |
|------|------|---------|
| P0 并行工作量 | 5 个 P0 全并行风险高 | 按依赖分批: **Batch 1** (P0-1 命名 + P0-5 可观测) -> **Batch 2** (P0-4 删除管线) -> **Batch 3** (P0-2 注入 + P0-3 预算) |
| 评测集瓶颈 | 500 条真实/脱敏样本需运营配合 | 尽早启动样本收集，不是纯工程任务 |
| Deletion Epoch 热点 | 全局 epoch 可能成为写入瓶颈 | 按 `user_id` 分片，不做全局 epoch |
| Schema 迁移复杂度 | details_schema_version 2->3 触发 Expand-Contract | 遵循 ADR-033 三阶段迁移，最小 2 个 minor version 过渡期 |

### 7.2 文档维护

从原计划的 **4 文档（01/06/07/08）扩充为 5 文档（00/01/06/07/08）**。

| 文档 | 需同步更新的内容 |
|------|----------------|
| **00-总览** | 降级矩阵增加"降级免疫"、Day 1 Port 引用更新 |
| **01-Brain** | MemoryItem schema、Context Assembler 五元组、预算算法、删除管线状态机 |
| **06-基础设施** | DDL（memory_items 增加 content_schema_version、event_outbox 增加 payload_version）、memory_receipts details v3 |
| **07-部署安全** | SLA 阶梯告警细化、AI 安全三威胁补充、Crypto Shredding 预留 |
| **08-附录** | ADR-038~041、契约索引表更新 |

### 7.3 核心判断

**DIYU 的双 SSOT 隐私架构 + 组织树治理模型 + 记忆进化管线是真正的差异化壁垒。** 平台化不是重建这些，而是给它们加上版本化、沙箱化、模板化的外壳，让第三方能在不破坏内核的前提下扩展系统能力。

---

> **审查校验:** 本报告覆盖两次交互讨论的全部内容，共计 P0 五项升级方案 + 五个隐含假设 + 三个鲁棒性问题 + 三个兼容性补充 + 三个 AI 安全威胁 + 四阶段平台化路线图 + 四项 ADR + 四项验收标准 + 四项风险提示。无遗漏。
