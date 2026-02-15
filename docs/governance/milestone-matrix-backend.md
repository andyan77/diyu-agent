# DIYU Agent 里程碑矩阵 -- 后端维度 (Backend)

> parent: `docs/governance/milestone-matrix.md`
> scope: Brain / Memory Core / Knowledge / Skill / Tool / Gateway / Infrastructure
> version: v1.0

## 使用说明

> 矩阵层 7 字段格式 (D/AC/V-in/V-x/V-fb/M/DEP) 说明见 [索引文件](milestone-matrix.md) Section 0.5。
> 任务卡层采用双 Tier Schema (Tier-A: 10 字段, Tier-B: 8 字段)，详见 `task-card-schema-v1.0.md`。
> 跨层验证节点编号 (X/XF/XM) 定义见 [横切文件](milestone-matrix-crosscutting.md) Section 4。

---

## 1. Brain 层详细里程碑

> 架构文档: `01-对话Agent层-Brain.md` | 渐进式组合: Step 1

### Phase 0 -- 骨架与 Port

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| B0-1 | `src/brain/__init__.py` 模块骨架 | [FILE] 文件存在，`import src.brain` 无报错 | mypy 通过 | X0-1 | -- | 文件存在 | -- |
| B0-2 | Brain 层 Port 接口引用（消费 MemoryCorePort, LLMCallPort, KnowledgePort, SkillRegistry, OrgContext） | [TEST] `mypy --strict src/brain/` 通过 | 类型签名完整 | X0-1 | -- | 5 个 Port 引用无报错 | 各 Port 定义存在于 `src/ports/` |
| B0-3 | 对话引擎空壳 `src/brain/engine/conversation.py` | [FILE] 类定义存在，方法签名完整，逻辑为 pass/raise NotImplementedError | 方法签名对齐架构文档 | -- | -- | 类+方法存在 | -- |

### Phase 1 -- 无直接交付

> Brain 在 Phase 1 无新增交付。Phase 1 聚焦 Gateway（Auth/RLS）和 Infrastructure（组织模型），Brain 等待 Phase 2 启动。

### Phase 2 -- 首条对话闭环（核心交付 Phase）

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| B2-1 | 对话引擎完整实现 | [TEST] `pytest tests/unit/brain/test_conversation_engine.py` 全部通过 | 单元测试覆盖率 >= 85% | X2-1 | XF2-1 | 测试全通过 | LLMCallPort 真实实现 (T2-1) |
| B2-2 | 意图理解模块 | [TEST] 给定 10 条测试消息，正确区分"纯对话"和"需要做事" | 10 条测试集覆盖 | X2-1 | -- | 准确率 >= 90% | -- |
| B2-3 | Context Assembler v1 | [TEST] 同时读取 Memory Core (personal_context) + Knowledge (空降级)，组装 assembled_context | 组装逻辑单测 | X2-3 | -- | assembled_context 非空 | MemoryCorePort 真实实现 (MC2-1) |
| B2-4 | Context Assembler CE 增强 | [TEST] Query Rewriting + Hybrid Retrieval(FTS+pgvector+RRF) + Multi-Signal Reranking 五因子排序通过 | 五因子排序单测 | X2-3 | -- | RRF 排序输出稳定 | pgvector 启用 (ADR-042, I2-5) |
| B2-5 | Memory 写入管线（Observer -> Analyzer -> Evolver） | [TEST] 一次对话后 memory_items 表新增记录，含 observation + confidence | 管线 3 阶段各有单测 | X2-3 | -- | 写入成功率 100% | Memory Core CRUD (MC2-3) |
| B2-6 | injection_receipt + retrieval_receipt 写入 | [TEST] 每次对话后 memory_receipts 表有对应回执 | 回执 5 元组完整性检查 | X2-1 | -- | 每次对话产生 >= 1 条回执 | -- |
| B2-7 | 优雅降级：Knowledge 不可用时仍能对话 | [TEST] 断开 Knowledge 后端，对话仍正常，日志包含 `degraded_reason` | 降级路径单测 | X2-1 | -- | 降级对话成功率 100% | -- |
| B2-8 | WebSocket 实时对话集成 | [E2E] `pytest tests/e2e/brain/test_ws_chat.py -v` | WS 协议单测 | X2-2 | XF2-1 | 首字节延迟 < 500ms | Gateway WS 实现 (G2-2) |

### Phase 3 -- 技能调度与角色适配

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| B3-1 | Skill Router 实现 | [TEST] 意图 "帮我写产品文案" 路由到 ContentWriterSkill | 路由表配置单测 | X3-1 | XF3-1 | 路由准确率 >= 95% | SkillRegistry 真实注册 (S3-3) |
| B3-2 | Brain 编排 Skill 执行流 | [E2E] `pytest tests/e2e/brain/test_skill_orchestration.py -v` | 编排状态机单测 | X3-1 | XF3-1 | 端到端成功率 >= 90% | Knowledge Layer (K3-5) + Skill Layer (S3-1) |
| B3-3 | 角色适配模块 | [TEST] 品牌总部用户和门店店员对相同输入得到不同风格回复 | 角色配置单测 | -- | -- | 两种角色差异可辨别 | OrgContext 含 role 信息 (G1-2) |
| B3-4 | 负反馈熔断 | [TEST] 用户连续 3 次否定某记忆后，该记忆 confidence 降至 0，不再注入 | 熔断逻辑单测 | X3-3 | -- | 熔断后注入率 = 0% | Memory Core Evolution (MC2-5) |

### Phase 4 -- 可靠性与 CE 精细化

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| B4-1 | Context Assembler 性能优化 | [METRIC] 并发读两个 SSOT 延迟 P95 < 200ms | 缓存命中率测试 | X4-1 | -- | P95 < 200ms | Redis 缓存 (I2-1) |
| B4-2 | 动态预算分配器 v1 (ADR-035) | [TEST] 根据 token 预算动态分配 personal_context 和 knowledge_context 比例 | 分配算法单测 | -- | -- | 预算利用率 >= 90% | -- |
| B4-3 | TruncationPolicy: FixedPriorityPolicy | [TEST] 超出 token 上限时按优先级截断 | 截断逻辑单测 | -- | -- | 截断后 token <= 上限 | -- |
| B4-4 | 7 项 SLI 埋点 (ADR-038) | [METRIC] Grafana 看板展示 injection_precision, retrieval_recall 等 | 埋点完整性验证 | X4-1 | -- | 7 项指标全部可视 | Prometheus (I4-1), OS4-1 |
| B4-5 | Sanitization pattern-based | [TEST] 恶意 prompt 输入被清洗，不进入 LLM 调用 | 清洗规则单测 | -- | -- | 恶意输入拦截率 >= 99% | OS4-7 |

### Phase 5 -- 治理自动化

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| B5-1 | Memory Governor 组件 | [TEST] 治理逻辑独立封装，可配置阈值触发清理 Job | 阈值配置单测 | X5-2 | -- | 清理 Job 可触发 | -- |
| B5-2 | Confidence Calibration 批量校准 | [TEST] 200 条评测集校准后，injection_precision 提升 | 校准算法单测 | -- | -- | precision 提升 >= 5% | 评测集 |
| B5-3 | AssemblyProfile 多次异构 LLM 调用 | [TEST] 单次对话可调用不同模型处理不同子任务 | 多模型调度单测 | -- | -- | 子任务分发正确 | -- |
| B5-4 | Memory Consolidation 相似记忆合并 | [TEST] 3 条相似 memory_items 合并为 1 条，保留溯源链 | 合并逻辑单测 | -- | -- | 合并后溯源链完整 | -- |

---

## 2. Memory Core 层详细里程碑

> 架构文档: `01-对话Agent层-Brain.md` Section 2-3 | SSOT-A | 硬依赖

### Phase 0 -- Port 定义与骨架

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| MC0-1 | `src/ports/memory_core_port.py` 完整接口定义 | [FILE] read_personal_memories / write_observation / write_conversation_event 等方法签名完整，mypy 通过 | 方法签名对齐 01 Section 2.3 | X0-1 | -- | 接口方法 >= 5 个 | -- |
| MC0-2 | MemoryCorePort Stub 实现（SQLite 内存） | [TEST] Stub 实现所有方法，pytest 基础用例通过 | Stub 覆盖率 100% | X0-1 | -- | 全部基础用例通过 | -- |
| MC0-3 | `src/shared/types/memory_item.py` MemoryItem v1 Schema | [FILE] content_schema_version, memory_type, confidence, embedding 等字段定义 (01 Section 2.3.1) | Schema 字段完整性检查 | -- | -- | 必需字段全部定义 | -- |

### Phase 1 -- 无直接交付

> Memory Core 跟随 Brain 在 Phase 2 启动。Phase 1 的 RLS 策略在 Infrastructure 层定义，Memory Core 被动受益。

### Phase 2 -- 完整实现（核心交付 Phase）

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| MC2-1 | PG 真实实现替换 Stub | [TEST] MemoryCorePort PG Adapter 通过所有 Stub 测试 | Adapter 通过 Stub 全量用例 | X2-1 | -- | 100% Stub 测试通过 | PG (I0-1) + StoragePort |
| MC2-2 | conversation_events 表 CRUD | [TEST] 写入对话事件 -> 按 session_id 查询 -> 返回时序有序列表 | 时序排序正确性 | X2-1 | -- | CRUD 4 操作全覆盖 | Migration (I2-4) |
| MC2-3 | memory_items 表 CRUD + versioned | [TEST] 创建 -> 更新(version+1) -> 读取最新版 -> 查历史版本 | 版本号自增正确性 | X2-3 | XF2-2 | 版本链完整 | Migration (I2-5) |
| MC2-4 | pgvector 语义检索 (ADR-042) | [TEST] 写入 embedding -> 相似度查询 Top-5 -> 返回相关记忆，RRF 融合通过 | RRF 融合排序单测 | X2-3 | -- | Top-5 召回率 >= 80% | pgvector 扩展 (I2-5) |
| MC2-5 | Evolution Pipeline: Observer -> Analyzer -> Evolver | [TEST] 对话自动提取 observation -> 分析模式 -> 写入/更新 memory_items | 3 阶段各有单测 | X2-3 | -- | 提取成功率 >= 90% | LLMCallPort (T2-1) |
| MC2-6 | injection_receipt / retrieval_receipt 写入 | [TEST] memory_receipts 表记录每次注入的 5 元组 (what/why/from/confidence/version) | 5 元组完整性 | X2-1 | -- | 每次注入产生回执 | -- |
| MC2-7 | confidence_effective 衰减计算 | [TEST] 旧记忆的 effective confidence 随时间衰减 (01 Section 2.3.2.4) | 衰减公式单测 | -- | -- | 30 天后衰减可观测 | -- |

### Phase 3 -- Promotion Pipeline

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| MC3-1 | Promotion Pipeline: Memory -> Knowledge 提案流 | [TEST] 达阈值的 personal memory -> sanitize -> conflict check -> 生成 proposal | 提案生成单测 | X3-3 | -- | 提案通过率可追踪 | Knowledge Write API (K3-4) |
| MC3-2 | promotion_receipt 写入 | [TEST] 提案审批后 promotion_receipt + knowledge_write_receipt 各一条 | 回执完整性检查 | X3-3 | -- | 每次提案产生 2 条回执 | -- |

### Phase 4 -- 删除管线与可靠性

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| MC4-1 | 删除管线 8 态状态机 (ADR-039) | [TEST] tombstone 创建 -> 8 态流转 -> 物理删除完成，每步可审计 | 8 态转换单测 | X4-4 | XF4-3 | 每步审计完整 | Outbox (I1-6) |
| MC4-2 | 备份恢复演练 | [CMD] `make backup-memory` -> 删数据 -> `make restore-memory` -> 数据恢复 | 恢复数据完整性校验 | X4-2 | -- | 恢复后数据一致 | PG 备份 (I4-3) |
| MC4-3 | deletion_timeout_rate SLI = 0% | [METRIC] 所有 tombstone 在 SLA 内完成删除 | SLI 埋点验证 | X4-4 | -- | timeout_rate = 0% | 监控 (OS4-1) |

### Phase 5 -- 自动治理

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| MC5-1 | Memory Consolidation 自动合并 | [TEST] 相似度 > 0.95 的记忆自动合并 | 合并算法单测 | -- | -- | 合并后去重率 >= 90% | -- |
| MC5-2 | Contextual Chunking embedding 前缀增强 | [TEST] 增强后检索精度提升 (对比实验) | A/B 对比单测 | -- | -- | 精度提升 >= 5% | 评测集 |
| MC5-3 | Crypto Shredding per-user 加密 (07 Section 5.2) | [TEST] 删除用户密钥后，该用户所有记忆不可解密 | 加密/销毁单测 | -- | -- | 销毁后不可逆 | -- |

---

## 3. Knowledge 层详细里程碑

> 架构文档: `02-Knowledge层.md` | SSOT-B | 软依赖 | 渐进式组合: Step 4

### Phase 0 -- Port 定义

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| K0-1 | `src/ports/knowledge_port.py` KnowledgePort 接口 | [FILE] 接口定义完整，返回 KnowledgeBundle 类型 | mypy 通过 | X0-1 | -- | 接口方法签名完整 | -- |
| K0-2 | KnowledgePort Stub（返回空 KnowledgeBundle） | [TEST] Stub 实现调用不报错，返回空结果 | Stub 覆盖率 100% | X0-1 | -- | 全部方法可调用 | -- |
| K0-3 | `src/shared/types/knowledge_bundle.py` KnowledgeBundle v1 Schema | [FILE] 字段定义对齐 02 Section 5.4.1 | Schema 完整性检查 | -- | -- | 必需字段全部定义 | -- |

### Phase 1-2 -- 无直接交付

> Knowledge 层在 Phase 3 才启动真实实现。Phase 0-2 Brain 通过 Stub 降级运行。

### Phase 3 -- 完整实现（核心交付 Phase）

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| K3-1 | Neo4j 图谱 Schema + 种子数据 | [CMD] `make seed-knowledge` -> Neo4j Browser 可查询 SKU/品类/搭配关系 | Schema 定义完整 | X3-2 | -- | 种子节点 >= 50 | Neo4j 5.x (I3-1) |
| K3-2 | Qdrant 向量库初始化 + 种子数据 | [CMD] Qdrant Dashboard 显示 collection 和 vector 数量 | collection 参数正确 | X3-2 | -- | 种子向量 >= 50 | Qdrant 1.x (I3-2) |
| K3-3 | FK 联动机制（Neo4j node_id <-> Qdrant point_id） | [TEST] 写入图谱节点 -> 同步写入向量 -> FK 一致性检查通过 | 双写事务单测 | X3-2 | -- | FK 一致率 = 100% | FK Registry |
| K3-4 | Knowledge Write API | [TEST] POST 知识条目 -> Neo4j + Qdrant 双写 + FK 一致 + 审计回执 | 写入链路单测 | X3-4 | XF3-2 | 双写成功率 100% | Gateway Admin API (G3-1) |
| K3-5 | Diyu Resolver 最小实现 (1-2 Profile) | [TEST] 按 Resolver Profile 查询 -> 返回 KnowledgeBundle (图谱结构 + 向量语义) | Profile 路由单测 | X3-1 | XF3-1 | 查询响应 < 200ms | -- |
| K3-6 | 实体类型注册机制 | [TEST] 注册新实体类型 -> Resolver 可查询该类型 | 注册/查询单测 | -- | -- | 注册后立即可查 | -- |
| K3-7 | ERP/PIM 变更集(ChangeSet)接口 | [TEST] 批量导入 -> 幂等 -> 审计 -> 可回滚 | 幂等性单测 | -- | -- | 幂等键去重率 100% | -- |

### Phase 4 -- 性能与可靠性

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| K4-1 | 图谱查询性能基线 | [METRIC] Neo4j 查询 P95 < 100ms (1M 节点) | 性能测试脚本 | X4-1 | -- | P95 < 100ms | -- |
| K4-2 | 向量检索性能基线 | [METRIC] Qdrant 查询 P95 < 50ms (1M vectors) | 性能测试脚本 | X4-1 | -- | P95 < 50ms | -- |
| K4-3 | FK 一致性 Reconciliation Job | [TEST] 人为破坏 FK -> Job 检测并修复 -> sync_status 恢复 | 修复逻辑单测 | X4-3 | -- | 修复后一致率 = 100% | -- |

### Phase 5 -- 平台化

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| K5-1 | Capability Registry 统一注册中心 | [TEST] Skill/Tool/Model/EntityType 统一注册查询 | 注册/查询单测 | X5-2 | -- | 4 类资源全可查 | -- |
| K5-2 | 可解释性面板 injection_receipt.explanation_trace | [E2E] `pytest tests/e2e/knowledge/test_explanation_trace.py -v` | 溯源链完整性 | -- | -- | 溯源链可追溯 | -- |

---

## 4. Skill 层详细里程碑

> 架构文档: `03-Skill层.md` | 渐进式组合: Step 3

### Phase 0 -- Port 定义

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| S0-1 | `src/skill/core/protocol.py` SkillProtocol 基类 | [FILE] 定义 execute() / describe() / validate_params() 签名 | mypy 通过 | X0-1 | -- | 3 个方法签名完整 | -- |
| S0-2 | SkillRegistry Stub（空注册表） | [TEST] 匹配任何请求返回"未找到" | Stub 单测通过 | X0-1 | -- | 全部方法可调用 | -- |

### Phase 1-2 -- 无直接交付

### Phase 3 -- 核心 Skill 实现（核心交付 Phase）

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| S3-1 | ContentWriterSkill 内容写手 | [E2E] `pytest tests/e2e/skill/test_content_writer.py -v` | 输出格式校验单测 | X3-1 | XF3-1 | 生成内容含必需字段 | KnowledgeBundle (K3-5), LLMCallPort (T2-1) |
| S3-2 | MerchandisingSkill 搭配助手 | [E2E] `pytest tests/e2e/skill/test_merchandising.py -v` | 评分逻辑单测 | X3-1 | XF3-1 | 搭配方案 >= 1 个 | StylingRule 图谱 (K3-1) |
| S3-3 | Skill 生命周期管理 | [TEST] 注册 -> 启用 -> 执行 -> 禁用 -> 重新启用 | 状态转换单测 | -- | -- | 5 态转换全覆盖 | SkillRegistry |
| S3-4 | Skill 参数校验 | [TEST] 缺失必填参数返回明确错误 | 校验逻辑单测 | -- | -- | 错误消息含缺失字段名 | -- |

### Phase 4 -- 可靠性

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| S4-1 | Skill 熔断器 | [TEST] Skill 连续失败 5 次 -> 自动熔断 -> 优雅降级回复 | 熔断逻辑单测 | X4-1 | -- | 熔断后降级成功率 100% | -- |
| S4-2 | Skill 执行超时 | [TEST] Skill 执行超过 30s -> 超时终止 -> 返回 timeout 错误 | 超时逻辑单测 | -- | -- | 超时终止响应 < 1s | -- |

### Phase 5 -- 高级能力

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| S5-1 | Skill A/B Testing | [TEST] 同一 Skill 两个版本按流量比例执行 | 流量分配单测 | -- | -- | 流量比例偏差 < 5% | -- |
| S5-2 | Skill multimodal 能力声明 (03 Section 2) | [TEST] Skill 声明 multimodal_input/output 支持 | 声明格式单测 | -- | -- | 声明可解析 | M2 (MM2-4) |

---

## 5. Tool 层详细里程碑

> 架构文档: `04-Tool层.md` | 渐进式组合: Step 2

### Phase 0 -- Port 定义

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| T0-1 | `src/ports/llm_call_port.py` LLMCallPort 接口 | [FILE] 方法签名含 model_id, messages, temperature 等 | mypy 通过 | X0-1 | -- | 方法签名完整 | -- |
| T0-2 | LLMCallPort Stub（返回固定文本） | [TEST] 调用返回 "stub response" | Stub 单测通过 | X0-1 | -- | 全部方法可调用 | -- |
| T0-3 | ToolProtocol 基类 | [FILE] execute() / describe() 签名定义 | mypy 通过 | -- | -- | 2 个方法签名完整 | -- |

### Phase 1 -- 无直接交付

### Phase 2 -- LLMCall 真实实现

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| T2-1 | LLMCallPort -> LLM Gateway 真实实现 | [TEST] 调用 LiteLLM -> 收到 LLM 回复 -> token 计量记录写入 | 集成测试通过 | X2-1 | -- | 调用成功率 >= 99% | LLM Gateway (G2-3), LiteLLM |
| T2-2 | Model Registry + Fallback | [TEST] 主模型 down -> 自动 fallback 到备选模型 | fallback 逻辑单测 | X2-1 | -- | fallback 延迟 < 2s | -- |
| T2-3 | Token 计量写入 llm_usage_records | [TEST] 每次调用后 llm_usage_records 有记录（含 prompt/completion tokens） | 计量准确性单测 | X2-4 | -- | 计量缺失率 = 0% | -- |

### Phase 3 -- 扩展 Tool

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| T3-1 | WebSearch Tool | [TEST] 搜索关键词 -> 返回结构化搜索结果 | 输出格式单测 | X3-1 | -- | 结果非空 | -- |
| T3-2 | ImageAnalyze Tool (M1) | [TEST] 输入图片 -> 返回描述文本 | 输入校验单测 | X3-1 | -- | 描述文本长度 > 0 | ObjectStoragePort (I3-3) |
| T3-3 | AudioTranscribe Tool (M1) | [TEST] 输入音频 -> 返回转写文本 | 输入校验单测 | X3-1 | -- | 转写文本长度 > 0 | ObjectStoragePort (I3-3) |

### Phase 4 -- 可靠性

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| T4-1 | Tool 独立计费 (ADR-047) | [TEST] Tool 调用费用独立于 LLM token 费用计量 | 计费逻辑单测 | X4-1 | -- | 计费独立且准确 | tool_usage_records (I3-4) |
| T4-2 | Tool 重试 + 指数退避 | [TEST] 失败后 100ms/500ms/2000ms 重试 | 退避逻辑单测 | -- | -- | 重试间隔符合预期 | -- |

### Phase 5 -- 治理

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| T5-1 | Tool 成本看板 | [METRIC] 按 Tool 类型和租户维度展示成本 | 看板数据源验证 | -- | -- | 2 维度数据可查 | Grafana (I4-1) |
| T5-2 | LLMCallPort Contract 阶段评估 (ADR-046) | [FILE] 评估报告: 是否可移除 content_parts 兼容层 | 报告完整性检查 | X5-2 | -- | 评估报告存在 | -- |

---

## 6. Gateway 层详细里程碑

> 架构文档: `05-Gateway层.md` + `05a-API-Contract.md` | 渐进式组合: Step 5

### Phase 0 -- 骨架与 CI

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| G0-1 | FastAPI + Uvicorn 最小运行 | [CMD] `uvicorn src.gateway.api.main:app` -> `/healthz` 返回 200 | healthz 端点单测 | X0-3 | -- | 200 响应 | pyproject.toml (I0-2) |
| G0-2 | OpenAPI spec 自动生成 | [CMD] 访问 `/docs` 看到 Swagger UI | spec 可解析 | -- | XF2-4 | Swagger 页面可访问 | -- |
| G0-3 | 请求日志中间件（trace_id + request_id） | [CMD] 发请求 -> 日志含 trace_id 字段 | 日志格式单测 | -- | -- | 日志含 3 必需字段 | -- |

### Phase 1 -- 安全与租户底座（核心交付 Phase）

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| G1-1 | JWT 认证中间件 | [TEST] 无 token 返回 401; 无效 token 返回 401; 有效 token 提取 user_id + org_id | 3 场景单测 | X1-1 | XF2-1 | 认证拒绝率准确 | -- |
| G1-2 | OrgContext 中间件完整链路 | [TEST] JWT -> 解析 org_chain -> 注入 OrgContext 到请求上下文 -> RLS 生效 | org_chain 解析单测 | X1-1 | XF2-1 | OrgContext 注入成功率 100% | Infra 组织模型 (I1-1) |
| G1-3 | RBAC 权限检查 | [TEST] 无权限用户访问 Admin API 返回 403 | 权限码映射单测 | X1-2 | -- | 403 响应准确 | RBAC 表 (I1-4) |
| G1-4 | RLS 策略基线 | [TEST] 租户 A 的 API 请求只能访问租户 A 的数据 | 隔离测试通过 | X1-1 | -- | 跨租户泄露 = 0 | PG RLS (I1-3) |
| G1-5 | API 分区规则 (ADR-029) | [FILE] 用户 API `/api/v1/*` 和管理 API `/api/v1/admin/*` 分离 | 路由注册检查 | -- | -- | 分区明确 | -- |
| G1-6 | 安全头配置 | [CMD] 响应包含 HSTS + X-Content-Type-Options + CSP | 响应头单测 | -- | -- | 安全头齐全 | -- |

### Phase 2 -- 业务 API

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| G2-1 | 对话 REST API | [E2E] `pytest tests/e2e/gateway/test_conversation_api.py -v` | API 契约测试 | X2-1 | XF2-1 | API 响应 < 2s | Brain (B2-1) |
| G2-2 | WebSocket 实时对话 | [E2E] `pytest tests/e2e/gateway/test_ws_streaming.py -v` | WS 协议单测 | X2-2 | XF2-1 | 首字节延迟 < 500ms | -- |
| G2-3 | LLM Gateway (LiteLLM 集成) | [TEST] 统一路由到不同 LLM provider + 计费 + 审计 | 路由逻辑单测 | X2-1 | -- | 路由成功率 100% | LiteLLM |
| G2-4 | Token 预算 Pre-check (Loop D Phase 1) | [TEST] 预算耗尽返回 402 + X-Budget-Remaining 告警头 | 预算计算单测 | X2-4 | XF4-1 | 402 响应准确 | usage_budgets (I2-3) |
| G2-5 | 限流中间件 | [TEST] 超过阈值返回 429 | 限流算法单测 | -- | -- | 429 响应准确 | Redis (I2-1) |
| G2-6 | 三步文件上传协议 (ADR-045, M0) | [TEST] 申请 URL -> 上传 -> 确认 -> 文件可访问 | 3 步协议单测 | -- | XF2-3 | 上传成功率 >= 99% | ObjectStoragePort (I3-3) |
| G2-7 | SSE 通知端点 `/events/*` (6 种事件类型) | [TEST] 6 种事件类型注册 + 租户隔离推送 | SSE 单测 | -- | -- | 6 事件类型全覆盖 | G1-1, G1-2 |

### Phase 3 -- Knowledge/Skill API

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| G3-1 | Knowledge Admin API `/api/v1/admin/knowledge/*` | [E2E] `pytest tests/e2e/gateway/test_knowledge_admin_api.py -v` | API 契约测试 | X3-4 | XF3-2 | CRUD 全覆盖 | Knowledge Layer (K3-4) |
| G3-2 | Skill API | [TEST] 列出可用 Skill -> 触发执行 -> 返回结果 | API 契约测试 | X3-1 | XF3-1 | Skill 列表非空 | Skill Layer (S3-3) |
| G3-3 | 内容安全检查 (05 Section 8) | [TEST] 恶意内容被拦截 -> security_status 状态更新 | 安全检查单测 | -- | -- | 拦截率 >= 99% | -- |

### Phase 4 -- 可靠性

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| G4-1 | SLO 指标 + 告警 | [METRIC] API P95 延迟 < 500ms, 错误率 < 0.1% | 指标采集验证 | X4-1 | -- | P95 < 500ms, err < 0.1% | Prometheus (I4-1), OS4-2 |
| G4-2 | HA 验证 | [TEST] 单节点故障 -> 自动切换 -> 用户无感知 | 故障切换测试 | X4-2 | -- | 切换时间 < 30s | -- |
| G4-3 | 限流精细化（per-org/per-user） | [TEST] 不同租户不同限流阈值 | 多租户限流单测 | -- | -- | 阈值按配置生效 | org_settings (I1-2) |

### Phase 5 -- API 生命周期

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| G5-1 | API 版本协商 | [TEST] Accept-Version header 路由到正确版本 | 版本路由单测 | -- | -- | 路由准确率 100% | -- |
| G5-2 | API 废弃告警 | [CMD] 调用废弃 API -> 响应头含 Deprecation + Sunset | 响应头验证 | X5-1 | -- | 废弃头信息完整 | -- |

---

## 7. Infrastructure 层详细里程碑

> 架构文档: `06-基础设施层.md` + `07-部署与安全.md` | 渐进式组合: Step 6

### Phase 0 -- 开发环境

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| I0-1 | Docker Compose 全栈环境 | [CMD] `docker-compose up` -> PG/Neo4j/Qdrant/Redis/MinIO 全部 healthy | 全部容器 healthy | X0-3 | -- | 5 个服务全部 healthy | -- |
| I0-2 | `pyproject.toml` + `uv.lock` | [CMD] `uv sync` 安装所有依赖无报错 | 依赖解析无冲突 | X0-2 | -- | 安装 0 error | -- |
| I0-3 | Alembic Migration 骨架 | [CMD] `alembic upgrade head` 无报错 | Migration 链完整 | -- | -- | upgrade 0 error | -- |
| I0-4 | `Makefile` 标准命令 | [CMD] `make help` 列出 dev/test/lint/typecheck/migrate 等命令 | help 输出完整 | -- | -- | >= 5 个命令可用 | -- |
| I0-5 | `.env.example` | [FILE] 包含所有必需环境变量及注释 | 变量名完整 | -- | -- | 所有必需变量有文档 | -- |
| I0-6 | `ruff` + `mypy --strict` 配置 | [CMD] `make lint && make typecheck` 通过 | 配置文件正确 | X0-2 | -- | 0 error, 0 warning | -- |

### Phase 1 -- 安全底座（核心交付 Phase）

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| I1-1 | organizations + users + org_members DDL + Migration | [CMD] `alembic upgrade head` -> 3 张表存在 | 表结构对齐架构文档 | X1-1 | -- | 3 张表全部存在 | -- |
| I1-2 | org_settings 继承链 (is_locked BRIDGE 机制) | [TEST] 上级 lock 的配置下级不可覆盖 | 继承逻辑单测 | X1-1 | XF3-3 | lock 机制生效 | -- |
| I1-3 | RLS 策略基线 (所有业务表) | [TEST] `SET LOCAL app.org_id = 'A'; SELECT * FROM memory_items;` 只返回 A 的数据 | 正向+反向隔离测试 | X1-1 | -- | 跨租户泄露 = 0 | -- |
| I1-4 | RBAC 权限检查骨架 (11 列 + 权限码映射) | [TEST] 权限码 -> 角色 -> 用户 链路通过 | 映射完整性单测 | X1-2 | -- | 权限链路通过 | -- |
| I1-5 | audit_events 表 + 审计写入 | [TEST] 关键操作后 audit_events 有记录 | 写入单测 | X1-3 | -- | 关键操作审计覆盖率 100% | -- |
| I1-6 | event_outbox 表 + Outbox Pattern | [TEST] 写入 outbox -> poller 投递 -> at-least-once 保证 | at-least-once 单测 | -- | -- | 投递成功率 >= 99.9% | -- |
| I1-7 | secret scanning + SAST + 依赖漏洞扫描 | [CMD] CI 中 3 项扫描通过 | 3 项独立验证 | X1-3 | -- | 0 Critical 漏洞 | CI (D0-4) |

### Phase 2 -- 运行时基础

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| I2-1 | Redis 缓存 + Session 管理 | [TEST] 写入缓存 -> TTL 过期 -> 自动清除 | TTL 逻辑单测 | -- | -- | 缓存命中率可监控 | Redis 7+ |
| I2-2 | Celery Worker + Redis Broker | [TEST] 发送异步任务 -> Worker 执行 -> 结果回写 | Worker 启动单测 | -- | -- | 任务执行成功率 >= 99% | -- |
| I2-3 | Token Billing 最小闭环 | [TEST] LLM 调用 -> token 计量 -> usage_budgets 扣减 -> 预算耗尽拒绝 | 计费链路单测 | X2-4 | XF4-1 | 计费误差 = 0 | -- |
| I2-4 | conversation_events 表 | [CMD] `alembic upgrade head` -> 表存在且含 content_schema_version 列 (v3.6) | DDL 对齐架构文档 | -- | -- | 表存在 + 列齐全 | -- |
| I2-5 | memory_items 表 (含 embedding + last_validated_at) | [CMD] 表存在且 pgvector 扩展启用 | pgvector extension 验证 | -- | -- | pgvector 可用 | pgvector |

### Phase 3 -- 全栈依赖

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| I3-1 | Neo4j 连接 + 基础 CRUD adapter | [TEST] 写入节点 -> 查询 -> 删除 | 连接池单测 | X3-2 | -- | CRUD 全操作通过 | Neo4j 5.x |
| I3-2 | Qdrant 连接 + 基础 CRUD adapter | [TEST] 写入向量 -> 相似度查询 -> 返回结果 | 连接池单测 | X3-2 | -- | 查询结果非空 | Qdrant 1.x |
| I3-3 | ObjectStoragePort 实现 (S3/MinIO) | [TEST] generate_upload_url -> upload -> generate_download_url -> download | 6 方法契约测试 | -- | XF2-3 | 6 方法全通过 | MinIO |
| I3-4 | tool_usage_records DDL (v3.6) | [CMD] 表存在 | DDL 对齐架构文档 | -- | -- | 表存在 | -- |

### Phase 4 -- 可靠性

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| I4-1 | Prometheus + Grafana 监控栈 | [E2E] `pytest tests/e2e/infra/test_monitoring_stack.py -v` | 4 黄金信号看板可用 | X4-1 | XF4-2 | 4 项指标全部可视 | OS4-1 |
| I4-2 | PG failover 实际演练 | [CMD] 主库故障 -> 自动切换 -> 应用恢复 | failover 脚本可用 | X4-2 | -- | 切换时间 < 30s | -- |
| I4-3 | 备份恢复演练 (PG 全量 + WAL/PITR) | [CMD] 备份 -> 模拟灾难 -> 恢复 -> 数据完整 | 恢复数据校验 | X4-2 | -- | 数据完整率 = 100% | -- |
| I4-4 | 故障注入测试 (删除管线每步注入失败) | [TEST] 每步失败都能正确处理并恢复 | 8 步注入测试 | X4-4 | -- | 8 步全部可恢复 | MC4-1, OS4-5 |
| I4-5 | PIPL/GDPR 删除管线完整实现 | [TEST] tombstone -> 物理删除 -> 审计保留 | 合规流程单测 | X4-4 | XF4-3 | SLA 内完成删除 | OS5-5 |

### Phase 5 -- 自动化

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| I5-1 | Event Mesh 演进 (PG Outbox -> NATS/Kafka) | [METRIC] 事件投递延迟 P99 < 100ms | 投递延迟测试 | -- | -- | P99 < 100ms | -- |
| I5-2 | Schema Registry | [TEST] schema 兼容性检查通过 | 兼容性检查单测 | X5-2 | -- | 兼容性检查可用 | -- |

---

> **文档版本:** v1.0
> **维护规则:** 架构文档或治理规范变更时，同步更新对应维度的里程碑条目。每个 Phase 完成后，更新对应列的实际交付状态。
