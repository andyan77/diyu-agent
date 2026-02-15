# Brain 层任务卡集

> 架构文档: `docs/architecture/01-对话Agent层-Brain.md`
> 里程碑来源: `docs/governance/milestone-matrix-backend.md` Section 1
> 影响门禁: `src/brain/**` -> check_layer_deps + check_port_compat

---

## Phase 0 -- 骨架与 Port

### TASK-B0-1: Brain 模块骨架

| 字段 | 内容 |
|------|------|
| **目标** | 建立 Brain 层目录结构，使 `import src.brain` 可用，后续开发有着陆点 |
| **范围 (In Scope)** | `src/brain/__init__.py`, `src/brain/engine/`, `src/brain/intent/` |
| **范围外 (Out of Scope)** | Adapter 实现 / 前端集成 / Memory Core 内部存储 / 性能调优 |
| **依赖** | -- (无前置) |
| **兼容策略** | 纯新增，无破坏性变更 |
| **验收命令** | `python -c "import src.brain" && echo PASS` |
| **回滚方案** | `git revert <commit>` -- 纯文件新增，无副作用 |
| **证据** | CI 构建日志，`evidence/phase-0/verify-phase-0-{sha}.json` |

> 矩阵条目: B0-1 | V-x: X0-1

### TASK-B0-2: Brain 层 Port 接口引用

| 字段 | 内容 |
|------|------|
| **目标** | 声明 Brain 层消费的 5 个 Port（MemoryCorePort, LLMCallPort, KnowledgePort, SkillRegistry, OrgContext），确保跨层契约可追踪 |
| **范围 (In Scope)** | `src/brain/deps.py` 或 `src/brain/__init__.py` 中的 import 声明 |
| **范围外 (Out of Scope)** | Port 接口实现 / Adapter 层代码 / Port 接口定义变更 |
| **依赖** | 各 Port 定义存在于 `src/ports/`（MC0-1, K0-1, T0-1, S0-1） |
| **风险** | 依赖: 上游 Port 未就绪时本卡阻塞 / 数据: N/A (纯接口引用) / 兼容: 新增引用，无破坏性 / 回滚: git revert 即可 |
| **兼容策略** | 纯引用声明，不实现逻辑；向后兼容 |
| **验收命令** | `mypy --strict src/brain/ && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | mypy 输出截图或 CI 日志 |
| **决策记录** | 决策: Brain 层声明 5 Port 消费关系 / 理由: 确保跨层契约显式可追踪，而非隐式依赖 / 来源: 架构文档 Section 1.2 |

> 矩阵条目: B0-2 | V-x: X0-1

### TASK-B0-3: 对话引擎空壳

| 字段 | 内容 |
|------|------|
| **目标** | 建立对话引擎类结构，方法签名对齐架构文档，为 Phase 2 实现预留骨架 |
| **范围 (In Scope)** | `src/brain/engine/conversation.py` |
| **范围外 (Out of Scope)** | 对话引擎业务逻辑实现 / LLM 调用 / Memory 读写 / 前端集成 |
| **依赖** | TASK-B0-1 |
| **兼容策略** | 方法体为 `raise NotImplementedError`，消费方不会在 Phase 0 调用 |
| **验收命令** | `python -c "from src.brain.engine.conversation import ConversationEngine; print('PASS')"` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 文件存在性检查 |

> 矩阵条目: B0-3

---

## Phase 1 -- 无直接交付

> Brain 在 Phase 1 无新增交付。Phase 1 聚焦 Gateway（Auth/RLS）和 Infrastructure（组织模型），Brain 等待 Phase 2 启动。

---

## Phase 2 -- 首条对话闭环（核心交付 Phase）

### TASK-B2-1: 对话引擎完整实现

| 字段 | 内容 |
|------|------|
| **目标** | 实现对话引擎核心逻辑：接收用户消息 -> 组装上下文 -> 调用 LLM -> 返回回复，完成首条对话闭环 |
| **范围 (In Scope)** | `src/brain/engine/conversation.py`, `tests/unit/brain/test_conversation_engine.py` |
| **范围外 (Out of Scope)** | Skill 调度 / 多模型路由 / 性能优化 / 前端集成 / Memory Core 内部存储 |
| **依赖** | LLMCallPort 真实实现 (T2-1), MemoryCorePort 真实实现 (MC2-1) |
| **风险** | 依赖: T2-1/MC2-1 未就绪时本卡阻塞 / 数据: N/A (通过 Port 读写) / 兼容: 接口签名不变，内部替换 / 回滚: git revert 恢复空壳 |
| **兼容策略** | 替换 NotImplementedError 为真实实现；对外接口签名不变 |
| **验收命令** | `pytest tests/unit/brain/test_conversation_engine.py -v --cov=src/brain/engine --cov-fail-under=85` |
| **回滚方案** | `git revert <commit>` -- 恢复为空壳实现 |
| **证据** | pytest 覆盖率报告，CI 链接 |
| **决策记录** | 决策: 对话引擎为 Brain 核心组件，直接消费 MemoryCorePort + LLMCallPort / 理由: Brain 是对话 Agent 本体，非路由器 (架构 v3.0+) / 来源: 架构文档 Section 1 |

> 矩阵条目: B2-1 | V-x: X2-1 | V-fb: XF2-1 | M-Track: MM1-4 (含图片输入时选择视觉模型)

### TASK-B2-2: 意图理解模块

| 字段 | 内容 |
|------|------|
| **目标** | 区分"纯对话"和"需要执行 Skill"两类意图，为后续 Skill 路由打基础 |
| **范围 (In Scope)** | `src/brain/intent/classifier.py`, `tests/unit/brain/test_intent.py` |
| **范围外 (Out of Scope)** | Skill 路由实现 (Phase 3) / 多轮意图追踪 / 前端表单 |
| **依赖** | TASK-B2-1 |
| **风险** | 依赖: 对话引擎就绪 / 数据: N/A (纯分类逻辑) / 兼容: 新增模块，Phase 2 默认全归"纯对话" / 回滚: git revert 无分类模式 |
| **兼容策略** | 新增模块，不影响现有对话流程；Phase 2 默认全部归类为"纯对话" |
| **验收命令** | `pytest tests/unit/brain/test_intent.py -v` (10 条测试集准确率 >= 90%) |
| **回滚方案** | `git revert <commit>` -- 移除意图模块，对话引擎回退为无分类模式 |
| **证据** | 测试集 10 条用例通过截图 |
| **决策记录** | 决策: Phase 2 仅做二分类 (对话/动作)，不做细粒度意图 / 理由: 最小可行交付，避免过早复杂化 / 来源: 架构文档 Section 1.2 意图理解 |

> 矩阵条目: B2-2 | V-x: X2-1

### TASK-B2-3: Context Assembler v1

| 字段 | 内容 |
|------|------|
| **目标** | 同时读取 Memory Core (personal_context) + Knowledge (空降级)，组装 assembled_context 输入 LLM |
| **范围 (In Scope)** | `src/brain/engine/context_assembler.py`, `tests/unit/brain/test_context_assembler.py` |
| **范围外 (Out of Scope)** | Query Rewriting / Hybrid Retrieval / 动态预算分配 / 性能优化 |
| **依赖** | MemoryCorePort 真实实现 (MC2-1) |
| **风险** | 依赖: MC2-1 未就绪时阻塞 / 数据: 隐私边界 -- Knowledge 不可直接读 Memory Core / 兼容: 新增模块 / 回滚: git revert |
| **兼容策略** | 新增模块；Knowledge 不可用时降级为空，不破坏对话 |
| **验收命令** | `pytest tests/unit/brain/test_context_assembler.py -v` |
| **回滚方案** | `git revert <commit>` -- 对话引擎回退为无上下文模式 |
| **证据** | assembled_context 非空断言通过 |
| **决策记录** | 决策: Context Assembler 为单组件同时读 SSOT-A + SSOT-B / 理由: 隐私边界要求 Knowledge 不直接访问 Memory Core (ADR-022) / 来源: ADR-022, 架构文档 Section 1.4 |

> 矩阵条目: B2-3 | V-x: X2-3

### TASK-B2-4: Context Assembler CE 增强

| 字段 | 内容 |
|------|------|
| **目标** | 实现 Query Rewriting + Hybrid Retrieval (FTS+pgvector+RRF) + Multi-Signal Reranking 五因子排序 |
| **范围 (In Scope)** | `src/brain/engine/context_assembler.py` (扩展), `tests/unit/brain/test_ce_enhanced.py` |
| **范围外 (Out of Scope)** | Qdrant 外部向量库集成 / 动态预算分配 / 性能基准测试 |
| **依赖** | TASK-B2-3, pgvector 启用 (ADR-042, I2-5) |
| **风险** | 依赖: pgvector 扩展未启用时 semantic 检索降级为 FTS-only / 数据: RRF 权重需实测校准 / 兼容: v1 接口不变 / 回滚: git revert 回退 v1 |
| **兼容策略** | 向后兼容 -- v1 接口不变，增强内部检索策略 |
| **验收命令** | `pytest tests/unit/brain/test_ce_enhanced.py -v` (RRF 排序输出稳定) |
| **回滚方案** | `git revert <commit>` -- 回退到 v1 简单检索 |
| **证据** | 五因子排序单测通过 |
| **决策记录** | 决策: Hybrid Retrieval 使用 pgvector + FTS + RRF 融合 / 理由: pgvector 为 Day-1 默认，避免引入外部依赖；RRF 平衡语义和关键词 / 来源: ADR-042, 架构文档 Section 1.4 |

> 矩阵条目: B2-4 | V-x: X2-3

### TASK-B2-5: Memory 写入管线 (Observer -> Analyzer -> Evolver)

| 字段 | 内容 |
|------|------|
| **目标** | 对话结束后自动提取 observation，分析模式，写入/更新 memory_items，实现"越聊越懂你" |
| **范围 (In Scope)** | `src/brain/memory/pipeline.py`, `tests/unit/brain/test_memory_pipeline.py` |
| **范围外 (Out of Scope)** | Memory Consolidation (Phase 5) / Confidence Calibration / 向量化实现细节 |
| **依赖** | Memory Core CRUD (MC2-3) |
| **风险** | 依赖: MC2-3 未就绪时无法写入 / 数据: observation 提取质量影响后续记忆准确性 / 兼容: 异步管线，失败不阻断对话 / 回滚: git revert |
| **兼容策略** | 新增模块，异步写入不影响对话响应；管线失败不阻断对话 |
| **验收命令** | `pytest tests/unit/brain/test_memory_pipeline.py -v` (写入成功率 100%) |
| **回滚方案** | `git revert <commit>` -- 禁用管线，对话仍可用但不记忆 |
| **证据** | memory_items 表新增记录截图 |
| **决策记录** | 决策: 三阶段管线 (Observation -> Analysis -> Evolution) 异步执行 / 理由: 解耦对话响应与记忆写入，避免写入延迟影响用户体验 / 来源: 架构文档 Section 2.2 Evolution Pipeline |

> 矩阵条目: B2-5 | V-x: X2-3

### TASK-B2-6: injection_receipt + retrieval_receipt 写入

| 字段 | 内容 |
|------|------|
| **目标** | 每次对话记录注入/检索回执（5 元组: what/why/from/confidence/version），为可解释性和调优提供数据 |
| **范围 (In Scope)** | `src/brain/memory/receipt.py`, `tests/unit/brain/test_receipt.py` |
| **范围外 (Out of Scope)** | 回执分析看板 / Confidence Calibration / 前端可解释性 UI |
| **依赖** | TASK-B2-5 |
| **风险** | 依赖: 管线就绪 / 数据: 回执 schema v2->v3 迁移需 Expand-Contract (ADR-034) / 兼容: 纯追加写入 / 回滚: git revert |
| **兼容策略** | 纯追加写入，不影响对话逻辑 |
| **验收命令** | `pytest tests/unit/brain/test_receipt.py -v` (每次对话产生 >= 1 条回执) |
| **回滚方案** | `git revert <commit>` -- 移除回执写入，不影响对话 |
| **证据** | memory_receipts 表查询截图 |
| **决策记录** | 决策: 5 元组回执 (candidate_score, decision_reason, policy_version, guardrail_hit, context_position) / 理由: 为 A/B 测试和 Confidence Calibration 提供反馈数据 / 来源: ADR-038, 架构文档 Section 2.3.2 |

> 矩阵条目: B2-6 | V-x: X2-1

### TASK-B2-7: 优雅降级 -- Knowledge 不可用时仍能对话

| 字段 | 内容 |
|------|------|
| **目标** | 断开 Knowledge 后端时对话仍正常，日志包含 `degraded_reason`，确保单点故障不扩散 |
| **范围 (In Scope)** | `src/brain/engine/context_assembler.py` (降级路径), `tests/unit/brain/test_degradation.py` |
| **范围外 (Out of Scope)** | Memory Core 降级 (硬依赖不可降级) / 前端降级 UI / LLM 降级策略 |
| **依赖** | TASK-B2-3 |
| **风险** | 依赖: Context Assembler 就绪 / 数据: N/A / 兼容: 增强容错，正常路径不变 / 回滚: git revert |
| **兼容策略** | 增强容错，不改变正常路径行为 |
| **验收命令** | `pytest tests/unit/brain/test_degradation.py -v` (降级对话成功率 100%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 降级日志含 degraded_reason 字段 |
| **决策记录** | 决策: Knowledge 为软依赖，不可用时降级为空 KnowledgeBundle / 理由: Memory Core (SSOT-A) 为硬依赖，Knowledge (SSOT-B) 可降级，保证核心对话不中断 / 来源: 架构文档 Section 1.4 |

> 矩阵条目: B2-7 | V-x: X2-1

### TASK-B2-8: WebSocket 实时对话集成

| 字段 | 内容 |
|------|------|
| **目标** | Brain 层对接 Gateway WS 端点，实现流式回复 + 会话持久化 |
| **范围 (In Scope)** | `src/brain/engine/ws_handler.py`, `tests/unit/brain/test_ws.py` |
| **范围外 (Out of Scope)** | 前端 WS 客户端 / Gateway WS 路由实现 / WS 认证鉴权 |
| **依赖** | Gateway WS 实现 (G2-2) |
| **风险** | 依赖: G2-2 未就绪时阻塞 / 数据: N/A / 兼容: REST 通道保持不变 / 回滚: git revert 回退仅 REST |
| **兼容策略** | 新增 WS 通道，REST 通道保持不变 |
| **验收命令** | `pytest tests/unit/brain/test_ws.py -v` (首字节延迟 < 500ms) |
| **回滚方案** | `git revert <commit>` -- 回退为仅 REST 模式 |
| **证据** | WS 消息延迟日志 |
| **决策记录** | 决策: Brain 层消费 Gateway WS 端点而非自建 WS 服务 / 理由: 网关统一管理连接、鉴权、限流 / 来源: 架构文档 Section 1.5 |

> 矩阵条目: B2-8 | V-x: X2-2 | V-fb: XF2-1

---

## Phase 3 -- 技能调度与角色适配

### TASK-B3-1: Skill Router 实现

| 字段 | 内容 |
|------|------|
| **目标** | 根据意图分类结果将请求路由到正确的 Skill，准确率 >= 95% |
| **范围 (In Scope)** | `src/brain/skill/router.py`, `tests/unit/brain/test_skill_router.py` |
| **范围外 (Out of Scope)** | Skill 业务逻辑实现 / SkillRegistry 注册机制 / 前端 Skill UI |
| **依赖** | SkillRegistry 真实注册 (S3-3), TASK-B2-2 |
| **风险** | 依赖: S3-3 未就绪时无 Skill 可路由 / 数据: 路由准确率依赖意图分类质量 / 兼容: 无匹配时回退纯对话 / 回滚: git revert |
| **兼容策略** | 新增路由层；无匹配 Skill 时回退为纯对话 |
| **验收命令** | `pytest tests/unit/brain/test_skill_router.py -v` (路由准确率 >= 95%) |
| **回滚方案** | `git revert <commit>` -- 禁用 Skill 路由，所有请求走纯对话 |
| **证据** | 路由测试集通过率报告 |
| **决策记录** | 决策: Skill Router 基于意图分类结果路由，非硬编码规则 / 理由: Brain 是 Agent 本体，Skill 为扩展机制 (架构 v3.0+) / 来源: 架构文档 Section 1.5 Skill Dispatch |

> 矩阵条目: B3-1 | V-x: X3-1 | V-fb: XF3-1

### TASK-B3-2: Brain 编排 Skill 执行流

| 字段 | 内容 |
|------|------|
| **目标** | 完整编排: 对话触发 Skill -> Resolver 预取 KnowledgeBundle -> Skill.execute() -> 结果返回用户 |
| **范围 (In Scope)** | `src/brain/skill/orchestrator.py`, `tests/unit/brain/test_skill_orchestration.py` |
| **范围外 (Out of Scope)** | Skill 内部业务逻辑 / Knowledge Resolver 实现 / 前端结果展示 |
| **依赖** | Knowledge Layer (K3-5) + Skill Layer (S3-1) |
| **风险** | 依赖: K3-5 + S3-1 跨层依赖 / 数据: KnowledgeBundle 为空时需降级 / 兼容: 纯对话路径不受影响 / 回滚: git revert |
| **兼容策略** | 新增编排逻辑；纯对话路径不受影响 |
| **验收命令** | `pytest tests/unit/brain/test_skill_orchestration.py -v` (端到端成功率 >= 90%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 编排状态机单测通过 |
| **决策记录** | 决策: Brain 编排 Skill 执行，Resolver 预取 Knowledge / 理由: Brain 作为 Agent 本体统一调度，避免 Skill 层直接访问 Knowledge (隐私边界) / 来源: 架构文档 Section 1.5 |

> 矩阵条目: B3-2 | V-x: X3-1 | V-fb: XF3-1

### TASK-B3-3: 角色适配模块

| 字段 | 内容 |
|------|------|
| **目标** | 根据 OrgContext 中的角色信息调整回复风格（品牌总部 vs 门店店员） |
| **范围 (In Scope)** | `src/brain/persona/adapter.py`, `tests/unit/brain/test_persona.py` |
| **范围外 (Out of Scope)** | OrgContext 数据模型定义 / 前端角色管理 UI / 多语言风格 |
| **依赖** | OrgContext 含 role 信息 (G1-2) |
| **风险** | 依赖: G1-2 OrgContext 就绪 / 数据: 角色配置数据驱动，需依赖 Knowledge Stores 或默认值 / 兼容: 无配置时使用默认风格 / 回滚: git revert |
| **兼容策略** | 新增适配层；无角色配置时使用默认风格 |
| **验收命令** | `pytest tests/unit/brain/test_persona.py -v` (两种角色差异可辨别) |
| **回滚方案** | `git revert <commit>` -- 回退为统一风格 |
| **证据** | 角色配置单测通过 |
| **决策记录** | 决策: 数据驱动角色适配，非硬编码风格模板 / 理由: Brain 第五能力 Role Adaptation，从 Knowledge Stores/defaults 读取风格参数 / 来源: 架构文档 Section 1.4 Role Adaptation |

> 矩阵条目: B3-3

### TASK-B3-4: 负反馈熔断

| 字段 | 内容 |
|------|------|
| **目标** | 用户连续 3 次否定某记忆后，该记忆 confidence 降至 0，不再注入上下文 |
| **范围 (In Scope)** | `src/brain/memory/feedback.py`, `tests/unit/brain/test_feedback.py` |
| **范围外 (Out of Scope)** | 前端反馈 UI / Confidence Calibration 批量校准 / Memory Consolidation |
| **依赖** | Memory Core Evolution (MC2-5) |
| **风险** | 依赖: MC2-5 就绪 / 数据: 误熔断有价值记忆需恢复机制 / 兼容: 不影响现有记忆读写 / 回滚: git revert 恢复原 confidence |
| **兼容策略** | 新增反馈逻辑；不影响现有记忆读写 |
| **验收命令** | `pytest tests/unit/brain/test_feedback.py -v` (熔断后注入率 = 0%) |
| **回滚方案** | `git revert <commit>` -- 移除熔断，记忆保持原 confidence |
| **证据** | 熔断逻辑单测通过 |
| **决策记录** | 决策: 3 次否定阈值触发熔断 / 理由: 平衡用户控制力与误操作风险，阈值可配置 / 来源: 架构文档 Section 2.3 Memory Quality |

> 矩阵条目: B3-4 | V-x: X3-3

---

## Phase 4 -- 可靠性与 CE 精细化

### TASK-B4-1: Context Assembler 性能优化

| 字段 | 内容 |
|------|------|
| **目标** | 并发读两个 SSOT 延迟 P95 < 200ms |
| **范围 (In Scope)** | `src/brain/engine/context_assembler.py` (缓存层), 性能测试脚本 |
| **范围外 (Out of Scope)** | Qdrant 外部向量库迁移 / Context Assembler 微服务拆分 / 前端性能优化 |
| **依赖** | Redis 缓存 (I2-1) |
| **风险** | 依赖: I2-1 Redis 就绪 / 数据: 缓存一致性 -- 记忆更新需缓存失效 / 兼容: 对外接口不变 / 回滚: 移除缓存层回退直接查询 |
| **兼容策略** | 内部优化，对外接口不变 |
| **验收命令** | `pytest tests/perf/test_assembler_latency.py -v` (P95 < 200ms) |
| **回滚方案** | `git revert <commit>` -- 移除缓存层，回退为直接查询 |
| **证据** | P95 延迟指标截图 |
| **决策记录** | 决策: pgvector 为 Day-1 默认，P95 < 200ms SLO / 理由: SLI retrieval_latency_p95 基线 (ADR-038)；超标时 Day-2 考虑 Qdrant / 来源: ADR-038, 架构文档 Section 2.3.2 |

> 矩阵条目: B4-1 | V-x: X4-1

### TASK-B4-2: 动态预算分配器 v1 (ADR-035)

| 字段 | 内容 |
|------|------|
| **目标** | 根据 token 预算动态分配 personal_context 和 knowledge_context 比例，提升预算利用率 |
| **范围 (In Scope)** | `src/brain/engine/budget_allocator.py`, `tests/unit/brain/test_budget.py` |
| **范围外 (Out of Scope)** | 截断策略 (B4-3) / LLM token 计费 / 前端预算展示 |
| **依赖** | TASK-B2-4 |
| **风险** | 依赖: CE 增强就绪 / 数据: 预算误分配可能导致关键上下文缺失 / 兼容: 可配置回退固定比例 / 回滚: 配置关闭 |
| **兼容策略** | 新增分配器；可通过配置关闭回退为固定比例 |
| **验收命令** | `pytest tests/unit/brain/test_budget.py -v` (预算利用率 >= 90%) |
| **回滚方案** | 配置 `BUDGET_ALLOCATOR=fixed` 回退 |
| **证据** | 分配算法单测通过 |
| **决策记录** | 决策: 动态预算基于意图类型分配 / 理由: 不同意图对 personal vs knowledge 上下文需求不同 (ADR-035) / 来源: ADR-035 |

> 矩阵条目: B4-2

### TASK-B4-3: TruncationPolicy: FixedPriorityPolicy

| 字段 | 内容 |
|------|------|
| **目标** | 超出 token 上限时按优先级截断上下文 |
| **范围 (In Scope)** | `src/brain/engine/truncation.py`, `tests/unit/brain/test_truncation.py` |
| **范围外 (Out of Scope)** | 动态预算分配 (B4-2) / LLM token 计数实现 / 前端截断提示 |
| **依赖** | TASK-B4-2 |
| **风险** | 依赖: 预算分配器就绪 / 数据: 截断可能丢失关键上下文 -- 需 U-shaped 定位缓解 / 兼容: 默认策略不截断 / 回滚: git revert |
| **兼容策略** | 新增截断策略；向后兼容（默认策略不截断） |
| **验收命令** | `pytest tests/unit/brain/test_truncation.py -v` (截断后 token <= 上限) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 截断逻辑单测通过 |
| **决策记录** | 决策: U-shaped 上下文定位 + FixedPriority 截断 / 理由: 缓解 Lost-in-the-Middle 注意力衰减 / 来源: 架构文档 Section 1.4 |

> 矩阵条目: B4-3

### TASK-B4-4: 7 项 SLI 埋点 (ADR-038)

| 字段 | 内容 |
|------|------|
| **目标** | Grafana 看板展示 injection_precision, retrieval_recall 等 7 项 Brain SLI |
| **范围 (In Scope)** | `src/brain/metrics/sli.py`, Grafana dashboard JSON |
| **范围外 (Out of Scope)** | Prometheus 服务端部署 / 告警规则配置 / 前端指标展示 |
| **依赖** | Prometheus (I4-1), OS4-1 |
| **风险** | 依赖: I4-1 Prometheus 就绪 / 数据: SLI 数据准确性依赖回执完整性 / 兼容: 纯新增指标 / 回滚: git revert |
| **兼容策略** | 纯新增指标，不影响业务逻辑 |
| **验收命令** | `curl localhost:9090/api/v1/query?query=brain_injection_precision` (结果非空) |
| **回滚方案** | `git revert <commit>` -- 移除埋点，看板无数据但系统不受影响 |
| **证据** | Grafana 7 项指标截图 |
| **决策记录** | 决策: 7 项 SLI (staleness/conflict/injection_quality/latency/overflow/deletion/receipt) / 理由: ADR-036 原 5 项扩展至 7 项 (ADR-038) / 来源: ADR-036, ADR-038 |

> 矩阵条目: B4-4 | V-x: X4-1

### TASK-B4-5: Sanitization pattern-based

| 字段 | 内容 |
|------|------|
| **目标** | 恶意 prompt 输入被清洗，不进入 LLM 调用，拦截率 >= 99% |
| **范围 (In Scope)** | `src/brain/security/sanitizer.py`, `tests/unit/brain/test_sanitizer.py` |
| **范围外 (Out of Scope)** | LLM-based 清洗 (Phase 5) / 前端输入过滤 / 安全审计日志 |
| **依赖** | OS4-7 |
| **风险** | 依赖: OS4-7 安全框架 / 数据: 误拦截正常输入影响用户体验 / 兼容: 新增安全层，正常输入不受影响 / 回滚: 移除清洗层需安全评估 |
| **兼容策略** | 新增安全层；正常输入不受影响 |
| **验收命令** | `pytest tests/unit/brain/test_sanitizer.py -v` (拦截率 >= 99%) |
| **回滚方案** | `git revert <commit>` -- 移除清洗层（需安全评估） |
| **证据** | 清洗规则单测通过 |
| **决策记录** | 决策: Pattern-based 清洗为 Day-1，LLM-based 为 Day-2 / 理由: Pattern 拦截低延迟高确定性，LLM 清洗作为补充 / 来源: 架构文档 Section 1.5 Sanitization |

> 矩阵条目: B4-5

---

## Phase 5 -- 治理自动化

### TASK-B5-1: Memory Governor 组件

| 字段 | 内容 |
|------|------|
| **目标** | 治理逻辑独立封装，可配置阈值触发清理 Job |
| **范围 (In Scope)** | `src/brain/governance/governor.py`, `tests/unit/brain/test_governor.py` |
| **范围外 (Out of Scope)** | Memory Consolidation 实现 (B5-4) / 删除管线 / 前端治理面板 |
| **依赖** | -- |
| **风险** | 依赖: N/A / 数据: 清理阈值误配可能删除有价值记忆 / 兼容: 不影响运行时对话 / 回滚: git revert |
| **兼容策略** | 新增组件，不影响运行时对话 |
| **验收命令** | `pytest tests/unit/brain/test_governor.py -v` (清理 Job 可触发) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 清理 Job 触发日志 |
| **决策记录** | 决策: 治理逻辑独立组件，非内嵌于 Evolution Pipeline / 理由: 关注点分离，治理策略可独立演进和配置 / 来源: 架构文档 Section 2.3 |

> 矩阵条目: B5-1 | V-x: X5-2

### TASK-B5-2: Confidence Calibration 批量校准

| 字段 | 内容 |
|------|------|
| **目标** | 200 条评测集校准后 injection_precision 提升 >= 5% |
| **范围 (In Scope)** | `src/brain/governance/calibration.py`, `tests/unit/brain/test_calibration.py`, 评测集 |
| **范围外 (Out of Scope)** | 在线实时校准 / Confidence Effective 衰减逻辑变更 / 前端校准 UI |
| **依赖** | 评测集 |
| **风险** | 依赖: 评测集质量 / 数据: 校准可能降低部分场景精度 -- 需 A/B 验证 / 兼容: 离线批量，不影响在线 / 回滚: 恢复校准前快照 |
| **兼容策略** | 校准为离线批量操作，不影响在线服务 |
| **验收命令** | `pytest tests/unit/brain/test_calibration.py -v` |
| **回滚方案** | 恢复校准前的 confidence 快照 |
| **证据** | injection_precision 前后对比报告 |
| **决策记录** | 决策: Confidence Effective 仅检索时衰减，不修改存储值 (ADR-042.2) / 理由: 避免破坏性修改，支持校准回滚 / 来源: ADR-042.2 |

> 矩阵条目: B5-2

### TASK-B5-3: AssemblyProfile 多次异构 LLM 调用

| 字段 | 内容 |
|------|------|
| **目标** | 单次对话可调用不同模型处理不同子任务 |
| **范围 (In Scope)** | `src/brain/engine/assembly_profile.py`, `tests/unit/brain/test_assembly_profile.py` |
| **范围外 (Out of Scope)** | LLM Provider 实现 / 计费逻辑 / 模型选择 UI |
| **依赖** | TASK-B2-1 |
| **风险** | 依赖: 对话引擎就绪 / 数据: 多模型调度增加延迟和成本 / 兼容: 默认不启用 / 回滚: 配置关闭 |
| **兼容策略** | 新增能力，默认不启用；配置开启后才生效 |
| **验收命令** | `pytest tests/unit/brain/test_assembly_profile.py -v` (子任务分发正确) |
| **回滚方案** | 配置关闭回退为单模型 |
| **证据** | 多模型调度单测通过 |
| **决策记录** | 决策: AssemblyProfile 支持异构模型调度 / 理由: 不同子任务 (意图理解/生成/分析) 适用不同模型，优化成本和质量 / 来源: 架构文档 Section 1.5, ADR-046 |

> 矩阵条目: B5-3

### TASK-B5-4: Memory Consolidation 相似记忆合并

| 字段 | 内容 |
|------|------|
| **目标** | 3 条相似 memory_items 合并为 1 条，保留溯源链 |
| **范围 (In Scope)** | `src/brain/governance/consolidation.py`, `tests/unit/brain/test_consolidation.py` |
| **范围外 (Out of Scope)** | 向量化实现细节 / Memory Core 内部存储优化 / 前端合并展示 |
| **依赖** | MC5-1 |
| **风险** | 依赖: MC5-1 就绪 / 数据: 误合并不同语义记忆需溯源链还原 / 兼容: 幂等操作，保留溯源 / 回滚: 合并前快照还原 |
| **兼容策略** | 合并操作幂等；保留溯源链可追溯原始记录 |
| **验收命令** | `pytest tests/unit/brain/test_consolidation.py -v` (溯源链完整) |
| **回滚方案** | 保留合并前快照，可还原 |
| **证据** | 合并后溯源链查询截图 |
| **决策记录** | 决策: 语义相似度阈值合并 + 溯源链保留 / 理由: 防止记忆膨胀同时保障可审计性 / 来源: 架构文档 Section 2.3 |

> 矩阵条目: B5-4

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。Phase 完成后在证据字段填入实际 CI 链接。
