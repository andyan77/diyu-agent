# Memory Core 层任务卡集

> 架构文档: `docs/architecture/01-对话Agent层-Brain.md` Section 2-3
> 里程碑来源: `docs/governance/milestone-matrix-backend.md` Section 2
> 影响门禁: `src/memory/**`, `src/ports/memory_core_port.py` -> check_port_compat + check_migration
> 说明: Memory Core 与 Brain 共享架构文档，但作为 SSOT-A 独立维度管理

---

## Phase 0 -- Port 定义与骨架

### TASK-MC0-1: MemoryCorePort 完整接口定义

| 字段 | 内容 |
|------|------|
| **目标** | 定义 Memory Core 的完整契约 (read_personal_memories / write_observation / write_conversation_event 等)，使各层可基于 Port 编程 |
| **范围 (In Scope)** | `src/ports/memory_core_port.py` |
| **范围外 (Out of Scope)** | Port 实现 (Adapter) / 向量化细节 / Brain 调度逻辑 |
| **依赖** | -- |
| **风险** | 依赖: N/A (无前置) / 数据: N/A (纯接口定义) / 兼容: 新增接口，无破坏性 / 回滚: git revert |
| **兼容策略** | 纯新增接口定义；方法签名对齐 01 Section 2.3 |
| **验收命令** | `mypy --strict src/ports/memory_core_port.py && echo PASS` (接口方法 >= 5 个) |
| **回滚方案** | `git revert <commit>` |
| **证据** | mypy 通过日志 |
| **决策记录** | 决策: Port 层使用 memory_id 命名，Storage 层使用 item_id / 理由: 对外语义统一，内部可独立演进 (v3.5 迁移中) / 来源: 架构文档 Section 2.3.1 |

> 矩阵条目: MC0-1 | V-x: X0-1

### TASK-MC0-2: MemoryCorePort Stub 实现 (SQLite 内存)

| 字段 | 内容 |
|------|------|
| **目标** | 提供内存级 Stub 实现，使 Brain 层可在无 PG 环境下进行单元测试 |
| **范围 (In Scope)** | `src/memory/pg_adapter.py`, `tests/unit/memory/test_pg_adapter.py` |
| **范围外 (Out of Scope)** | 向量检索 / 性能基准测试 |
| **依赖** | TASK-MC0-1 |
| **兼容策略** | Phase 0 Stub 已被 PgMemoryCoreAdapter 替换 (Phase 2) |
| **验收命令** | `pytest tests/unit/memory/test_pg_adapter.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | pytest 通过日志 |

> 矩阵条目: MC0-2 | V-x: X0-1

### TASK-MC0-3: MemoryItem v1 Schema

| 字段 | 内容 |
|------|------|
| **目标** | 定义 MemoryItem 数据模型 (content_schema_version, memory_type, confidence, embedding 等)，作为 Memory 层的数据契约 |
| **范围 (In Scope)** | `src/shared/types/memory_item.py` |
| **范围外 (Out of Scope)** | MemoryItem 业务逻辑 / 数据库 Migration / Epistemic Tagging (v3.5.2) |
| **依赖** | -- |
| **兼容策略** | 纯新增类型定义 |
| **验收命令** | `mypy --strict src/shared/types/memory_item.py && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | Schema 字段完整性检查通过 |

> 矩阵条目: MC0-3

---

## Phase 1 -- 无直接交付

> Memory Core 跟随 Brain 在 Phase 2 启动。Phase 1 的 RLS 策略在 Infrastructure 层定义，Memory Core 被动受益。

---

## Phase 2 -- 完整实现（核心交付 Phase）

### TASK-MC2-1: PG 真实实现替换 Stub

| 字段 | 内容 |
|------|------|
| **目标** | 实现 MemoryCorePort 的 PostgreSQL Adapter，替换 SQLite Stub，确保全量 Stub 测试通过 |
| **范围 (In Scope)** | `src/memory/pg_adapter.py`, `tests/unit/memory/test_pg_adapter.py` |
| **范围外 (Out of Scope)** | 向量化实现 / Brain 调度逻辑 / 数据迁移脚本 |
| **依赖** | PG (I0-1) + StoragePort |
| **风险** | 依赖: I0-1 PG 就绪 / 数据: Stub->PG 切换需确保数据一致性 / 兼容: Adapter 实现 Port 接口，消费方不变 / 回滚: 配置切回 Stub |
| **兼容策略** | Adapter 实现 Port 接口，消费方无需修改 |
| **验收命令** | `pytest tests/unit/memory/ -v` (100% Stub 测试通过) |
| **回滚方案** | 配置切回 Stub 实现 (`MEMORY_BACKEND=stub`) |
| **证据** | Adapter 通过 Stub 全量用例 |
| **决策记录** | 决策: PostgreSQL 作为 Memory Core 主存储 / 理由: ACID + pgvector 内嵌 + append-mostly 友好 + 运维协同 / 来源: 架构文档 Section 2.1 |

> 矩阵条目: MC2-1 | V-x: X2-1

### TASK-MC2-2: conversation_events 表 CRUD

| 字段 | 内容 |
|------|------|
| **目标** | 写入对话事件 -> 按 session_id 查询 -> 返回时序有序列表 |
| **范围 (In Scope)** | `src/memory/events.py`, `tests/unit/memory/test_events.py` |
| **范围外 (Out of Scope)** | 事件分析管线 / 前端对话历史 UI / 事件归档策略 |
| **依赖** | Migration (I2-4) |
| **风险** | 依赖: I2-4 Migration 就绪 / 数据: 时序正确性关键 -- 乱序写入导致上下文错乱 / 兼容: 新增 CRUD / 回滚: git revert + alembic downgrade |
| **兼容策略** | 新增 CRUD 操作，不影响现有表 |
| **验收命令** | `pytest tests/unit/memory/test_events.py -v` (CRUD 4 操作全覆盖) |
| **回滚方案** | `git revert <commit>` + `alembic downgrade -1` |
| **证据** | 时序排序正确性测试通过 |
| **决策记录** | 决策: conversation_events 按 session_id 分区存储 / 理由: 对话事件为 append-mostly，按 session 查询为主路径 / 来源: 架构文档 Section 2.1 |

> 矩阵条目: MC2-2 | V-x: X2-1

### TASK-MC2-3: memory_items 表 CRUD + versioned

| 字段 | 内容 |
|------|------|
| **目标** | 创建 -> 更新(version+1) -> 读取最新版 -> 查历史版本，版本链完整 |
| **范围 (In Scope)** | `src/memory/items.py`, `tests/unit/memory/test_items.py` |
| **范围外 (Out of Scope)** | 向量检索 / Evolution Pipeline / Epistemic Tagging |
| **依赖** | Migration (I2-5) |
| **风险** | 依赖: I2-5 Migration 就绪 / 数据: 版本链断裂导致数据不一致 / 兼容: 新增版本化 CRUD / 回滚: git revert + alembic downgrade |
| **兼容策略** | 新增版本化 CRUD，不影响 conversation_events |
| **验收命令** | `pytest tests/unit/memory/test_items.py -v` (版本链完整) |
| **回滚方案** | `git revert <commit>` + `alembic downgrade -1` |
| **证据** | 版本号自增正确性测试通过 |
| **决策记录** | 决策: MemoryItem 版本化存储 (content_schema_version) / 理由: 支持 Expand-Contract 迁移，版本链可追溯 (ADR-033) / 来源: ADR-033, 架构文档 Section 2.3.1 |

> 矩阵条目: MC2-3 | V-x: X2-3 | V-fb: XF2-2

### TASK-MC2-4: pgvector 语义检索 (ADR-042)

| 字段 | 内容 |
|------|------|
| **目标** | 写入 embedding -> 相似度查询 Top-5 -> RRF 融合排序，Top-5 召回率 >= 80% |
| **范围 (In Scope)** | `src/memory/vector_search.py`, `tests/unit/memory/test_vector.py` |
| **范围外 (Out of Scope)** | Qdrant 外部向量库 / Embedding 模型选择 / 前端检索 UI |
| **依赖** | pgvector 扩展 (I2-5) |
| **风险** | 依赖: I2-5 pgvector 就绪 / 数据: 向量维度不匹配导致检索失败 / 兼容: 新增检索通道，FTS 不变 / 回滚: 回退纯 FTS |
| **兼容策略** | 新增检索通道，不影响 FTS 检索 |
| **验收命令** | `pytest tests/unit/memory/test_vector.py -v` (Top-5 召回率 >= 80%) |
| **回滚方案** | `git revert <commit>` -- 回退为纯 FTS |
| **证据** | RRF 融合排序单测通过 |
| **决策记录** | 决策: pgvector 为 Day-1 默认向量检索，Qdrant 为 Day-2 扩展 / 理由: pgvector 内嵌 PG，运维简单；>1M items 时考虑 Qdrant personal_projection / 来源: ADR-042 |

> 矩阵条目: MC2-4 | V-x: X2-3

### TASK-MC2-5: Evolution Pipeline (Observer -> Analyzer -> Evolver)

| 字段 | 内容 |
|------|------|
| **目标** | 对话自动提取 observation -> 分析模式 -> 写入/更新 memory_items，提取成功率 >= 90% |
| **范围 (In Scope)** | `src/memory/evolution/`, `tests/unit/memory/test_evolution.py` |
| **范围外 (Out of Scope)** | Confidence Calibration / Memory Consolidation / Promotion Pipeline |
| **依赖** | LLMCallPort (T2-1) |
| **风险** | 依赖: T2-1 LLM 就绪 / 数据: 低成本模型分析质量影响记忆准确性 / 兼容: 异步不影响对话 / 回滚: 禁用管线 |
| **兼容策略** | 新增管线，异步执行不影响对话响应 |
| **验收命令** | `pytest tests/unit/memory/test_evolution.py -v` (3 阶段各有单测) |
| **回滚方案** | `git revert <commit>` -- 禁用管线 |
| **证据** | 3 阶段单测全通过 |
| **决策记录** | 决策: 三阶段异步管线 + 质量门控 / 理由: Observation 可信度上限 0.6，Analysis 上限 0.8，confirmed_by_user 为 1.0 / 来源: 架构文档 Section 2.2 |

> 矩阵条目: MC2-5 | V-x: X2-3

### TASK-MC2-6: injection_receipt / retrieval_receipt 写入

| 字段 | 内容 |
|------|------|
| **目标** | memory_receipts 表记录每次注入的 5 元组 (what/why/from/confidence/version) |
| **范围 (In Scope)** | `src/memory/receipt.py`, `tests/unit/memory/test_receipt.py` |
| **范围外 (Out of Scope)** | 回执分析看板 / A/B 测试框架 / 前端回执展示 |
| **依赖** | TASK-MC2-3 |
| **风险** | 依赖: MC2-3 就绪 / 数据: 回执 schema v2->v3 需 Expand-Contract / 兼容: 纯追加写入 / 回滚: git revert |
| **兼容策略** | 纯追加写入 |
| **验收命令** | `pytest tests/unit/memory/test_receipt.py -v` (5 元组完整性) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 每次注入产生回执 |
| **决策记录** | 决策: 5 元组回执结构 (candidate_score, decision_reason, policy_version, guardrail_hit, context_position) / 理由: 为 Confidence Calibration 和实验引擎提供反馈数据 / 来源: ADR-038 |

> 矩阵条目: MC2-6 | V-x: X2-1

### TASK-MC2-7: confidence_effective 衰减计算

| 字段 | 内容 |
|------|------|
| **目标** | 旧记忆的 effective confidence 随时间衰减 (01 Section 2.3.2.4)，30 天后衰减可观测 |
| **范围 (In Scope)** | `src/memory/confidence.py`, `tests/unit/memory/test_confidence.py` |
| **范围外 (Out of Scope)** | Confidence Calibration 批量校准 / 存储层 confidence 修改 / 前端置信度展示 |
| **依赖** | TASK-MC2-3 |
| **风险** | 依赖: MC2-3 就绪 / 数据: 衰减参数需实测校准 / 兼容: 仅检索时计算，不修改存储值 / 回滚: git revert |
| **兼容策略** | 新增衰减计算，不修改原始 confidence 字段 |
| **验收命令** | `pytest tests/unit/memory/test_confidence.py -v` (衰减公式单测) |
| **回滚方案** | `git revert <commit>` -- 回退为不衰减 |
| **证据** | 30 天衰减曲线测试通过 |
| **决策记录** | 决策: Confidence Effective 仅检索时衰减，不修改存储值 / 理由: 避免破坏性修改，支持校准回滚 (ADR-042.2) / 来源: ADR-042.2 |

> 矩阵条目: MC2-7

---

## Phase 3 -- Promotion Pipeline

### TASK-MC3-1: Promotion Pipeline -- Memory -> Knowledge 提案流

| 字段 | 内容 |
|------|------|
| **目标** | 达阈值的 personal memory -> sanitize -> conflict check -> 生成 proposal，实现知识沉淀 |
| **范围 (In Scope)** | `src/memory/promotion/`, `tests/unit/memory/test_promotion.py` |
| **范围外 (Out of Scope)** | Knowledge 审批 UI / Knowledge Write 实现 / 前端提案管理 |
| **依赖** | Knowledge Write API (K3-4) |
| **风险** | 依赖: K3-4 跨层 / 数据: 提案阈值 (confidence>=0.75, frequency_30d>=3) 敏感度影响误推 / 兼容: 不影响现有记忆读写 / 回滚: 禁用提案流 |
| **兼容策略** | 新增提案流，不影响现有记忆读写 |
| **验收命令** | `pytest tests/unit/memory/test_promotion.py -v` (提案生成单测) |
| **回滚方案** | `git revert <commit>` -- 禁用提案流 |
| **证据** | 提案通过率可追踪 |
| **决策记录** | 决策: Promotion 经 sanitize + conflict check 门控 / 理由: 防止个人隐私泄露到组织知识库，Knowledge 优先原则 (ADR-022) / 来源: ADR-022, 架构文档 Section 2.4 |

> 矩阵条目: MC3-1 | V-x: X3-3

### TASK-MC3-2: promotion_receipt 写入

| 字段 | 内容 |
|------|------|
| **目标** | 提案审批后写入 promotion_receipt + knowledge_write_receipt |
| **范围 (In Scope)** | `src/memory/promotion/receipt.py`, `tests/unit/memory/test_promotion_receipt.py` |
| **范围外 (Out of Scope)** | 回执分析 / Knowledge 层回执管理 / 前端审批 UI |
| **依赖** | TASK-MC3-1 |
| **风险** | 依赖: MC3-1 就绪 / 数据: 回执写入失败需重试机制 / 兼容: 纯追加写入 / 回滚: git revert |
| **兼容策略** | 纯追加写入 |
| **验收命令** | `pytest tests/unit/memory/test_promotion_receipt.py -v` (每次提案产生 2 条回执) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 回执完整性检查通过 |
| **决策记录** | 决策: 每次 Promotion 产生双回执 (promotion_receipt + knowledge_write_receipt) / 理由: 完整审计链，支持提案通过率分析 / 来源: 架构文档 Section 2.4 |

> 矩阵条目: MC3-2 | V-x: X3-3

---

## Phase 4 -- 删除管线与可靠性

### TASK-MC4-1: 删除管线 8 态状态机 (ADR-039)

| 字段 | 内容 |
|------|------|
| **目标** | tombstone 创建 -> 8 态流转 -> 物理删除完成，每步可审计 |
| **范围 (In Scope)** | `src/memory/deletion/`, `tests/unit/memory/test_deletion.py` |
| **范围外 (Out of Scope)** | 前端删除 UI / 法务合规审批流 / 备份层物理删除 |
| **依赖** | Outbox (I1-6) |
| **风险** | 依赖: I1-6 Outbox 就绪 / 数据: 删除不可逆 -- 零容忍 SLA 违规 / 兼容: 不影响正常 CRUD / 回滚: 回退软删除模式 |
| **兼容策略** | 新增删除管线；不影响正常 CRUD |
| **验收命令** | `pytest tests/unit/memory/test_deletion.py -v` (8 态转换单测) |
| **回滚方案** | `git revert <commit>` -- 回退为软删除模式 |
| **证据** | 每步审计记录完整 |
| **决策记录** | 决策: 8 态 tombstone 状态机 + per-user_id 删除围栏 / 理由: PIPL/GDPR 合规要求，SLA 可配置 (默认 15 工作日) / 来源: ADR-037, ADR-039 |

> 矩阵条目: MC4-1 | V-x: X4-4 | V-fb: XF4-3 | M-Track: MM1-6 (个人媒体删除复用此状态机)

### TASK-MC4-2: 备份恢复演练

| 字段 | 内容 |
|------|------|
| **目标** | `make backup-memory` -> 删数据 -> `make restore-memory` -> 数据恢复 |
| **范围 (In Scope)** | `scripts/backup_memory.sh`, `scripts/restore_memory.sh` |
| **范围外 (Out of Scope)** | 全量数据库备份 / 跨区域复制 / 前端备份管理 |
| **依赖** | PG 备份 (I4-3) |
| **风险** | 依赖: I4-3 PG 备份就绪 / 数据: 恢复过程中数据一致性风险 / 兼容: 纯运维脚本 / 回滚: 脚本级别回退 |
| **兼容策略** | 纯运维脚本，不影响应用代码 |
| **验收命令** | `make backup-memory && make restore-memory && echo PASS` |
| **回滚方案** | 脚本级别回退 |
| **证据** | 恢复后数据完整性校验通过 |
| **决策记录** | 本卡无关键取舍，遵循层内默认约定 |

> 矩阵条目: MC4-2 | V-x: X4-2

### TASK-MC4-3: deletion_timeout_rate SLI = 0%

| 字段 | 内容 |
|------|------|
| **目标** | 所有 tombstone 在 SLA 内完成删除，timeout_rate = 0% |
| **范围 (In Scope)** | `src/memory/deletion/metrics.py`, 监控告警规则 |
| **范围外 (Out of Scope)** | Prometheus 部署 / 告警通知渠道 / 前端删除进度展示 |
| **依赖** | 监控 (OS4-1) |
| **风险** | 依赖: OS4-1 监控就绪 / 数据: 零容忍指标 -- 任何超时需立即升级 / 兼容: 纯新增指标 / 回滚: git revert |
| **兼容策略** | 纯新增指标 |
| **验收命令** | `curl localhost:9090/api/v1/query?query=memory_deletion_timeout_rate` (结果 = 0) |
| **回滚方案** | `git revert <commit>` |
| **证据** | SLI 埋点验证通过 |
| **决策记录** | 决策: deletion_timeout_rate 零容忍 SLO / 理由: PIPL/GDPR 法律合规硬约束，超时即升级处理 / 来源: ADR-037, ADR-039 |

> 矩阵条目: MC4-3 | V-x: X4-4

---

## Phase 5 -- 自动治理

### TASK-MC5-1: Memory Consolidation 自动合并

| 字段 | 内容 |
|------|------|
| **目标** | 相似度 > 0.95 的记忆自动合并，去重率 >= 90% |
| **范围 (In Scope)** | `src/memory/governance/consolidation.py`, `tests/unit/memory/test_consolidation.py` |
| **范围外 (Out of Scope)** | Brain 层合并触发逻辑 / 前端合并展示 / 跨用户合并 |
| **依赖** | -- |
| **风险** | 依赖: N/A / 数据: 误合并不同语义记忆 -- 需溯源链还原 / 兼容: 幂等操作 / 回滚: 合并前快照 |
| **兼容策略** | 合并操作幂等，保留溯源链 |
| **验收命令** | `pytest tests/unit/memory/test_consolidation.py -v` (去重率 >= 90%) |
| **回滚方案** | 保留合并前快照 |
| **证据** | 合并算法单测通过 |
| **决策记录** | 决策: 相似度 > 0.95 阈值 + 溯源链保留 / 理由: 防止记忆膨胀 (v3.5.1 Enhancement D)，阈值可配置 / 来源: 架构文档 Section 2.3 |

> 矩阵条目: MC5-1

### TASK-MC5-2: Contextual Chunking embedding 前缀增强

| 字段 | 内容 |
|------|------|
| **目标** | 增强后检索精度提升 >= 5% (A/B 对比实验) |
| **范围 (In Scope)** | `src/memory/embedding/chunking.py`, `tests/unit/memory/test_chunking.py` |
| **范围外 (Out of Scope)** | Embedding 模型更换 / 向量库迁移 / 前端检索 UI |
| **依赖** | 评测集 |
| **风险** | 依赖: 评测集质量 / 数据: 前缀策略可能降低部分场景精度 / 兼容: 可配置切换 / 回滚: 配置切回 |
| **兼容策略** | 可通过配置切换新旧策略 |
| **验收命令** | `pytest tests/unit/memory/test_chunking.py -v` |
| **回滚方案** | 配置切回原策略 |
| **证据** | A/B 对比精度报告 |
| **决策记录** | 决策: 记忆内容前缀加分类元数据 (v3.5.1 Enhancement C) / 理由: 提升 embedding 语义区分度 / 来源: 架构文档 Section 2.3 Enhancement C |

> 矩阵条目: MC5-2

### TASK-MC5-3: Crypto Shredding per-user 加密 (07 Section 5.2)

| 字段 | 内容 |
|------|------|
| **目标** | 删除用户密钥后，该用户所有记忆不可解密 |
| **范围 (In Scope)** | `src/memory/security/crypto_shredding.py`, `tests/unit/memory/test_crypto.py` |
| **范围外 (Out of Scope)** | KMS 集成 / 密钥轮换策略 / 前端加密管理 |
| **依赖** | -- |
| **风险** | 依赖: N/A / 数据: 加密迁移不可逆 -- 需加密前完整备份 / 兼容: 新用户自动启用，现有需迁移 / 回滚: 迁移前备份还原 |
| **兼容策略** | 新用户自动启用；现有数据需迁移脚本 |
| **验收命令** | `pytest tests/unit/memory/test_crypto.py -v` (销毁后不可逆) |
| **回滚方案** | 迁移脚本可逆（加密前备份） |
| **证据** | 加密/销毁单测通过 |
| **决策记录** | 决策: per-user 密钥 + Crypto Shredding / 理由: PIPL/GDPR 合规要求，密钥销毁即数据销毁 / 来源: 07-部署与安全 Section 5.2 |

> 矩阵条目: MC5-3

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。Phase 完成后在证据字段填入实际 CI 链接。
