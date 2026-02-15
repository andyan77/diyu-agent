# Knowledge 层任务卡集

> 架构文档: `docs/architecture/02-Knowledge层.md`
> 里程碑来源: `docs/governance/milestone-matrix-backend.md` Section 3
> 影响门禁: `src/knowledge/**` -> check_layer_deps + check_port_compat
> SSOT-B | 软依赖 | 渐进式组合 Step 4

---

## Phase 0 -- Port 定义

### TASK-K0-1: KnowledgePort 接口定义

| 字段 | 内容 |
|------|------|
| **目标** | 定义 Knowledge 层契约（返回 KnowledgeBundle 类型），使 Brain 可基于 Port 编程 |
| **范围 (In Scope)** | `src/ports/knowledge_port.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Memory Core 内部存储 / Skill 实现 / 前端集成 |
| **依赖** | -- |
| **兼容策略** | 纯新增接口定义 |
| **验收命令** | `mypy --strict src/ports/knowledge_port.py && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | mypy 通过日志 |
| **风险** | 依赖: N/A -- 无外部依赖 / 数据: N/A -- 纯接口定义 / 兼容: Port 接口一旦发布需保持稳定 (ADR-033) / 回滚: git revert |
| **决策记录** | 决策: KnowledgePort 返回 KnowledgeBundle 类型作为跨层契约 / 理由: Brain 基于 Port 编程, 与具体实现解耦 / 来源: ADR-033, 架构文档 02 Section 5.4.1 |

> 矩阵条目: K0-1 | V-x: X0-1

### TASK-K0-2: KnowledgePort Stub

| 字段 | 内容 |
|------|------|
| **目标** | 返回空 KnowledgeBundle 的 Stub 实现，使 Brain 在 Phase 0-2 降级运行 |
| **范围 (In Scope)** | `src/knowledge/stub.py`, `tests/unit/knowledge/test_stub.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Memory Core 内部存储 / Skill 实现 / 真实数据存储 |
| **依赖** | TASK-K0-1 |
| **兼容策略** | Stub 实现所有方法；Phase 3 被真实实现替换 |
| **验收命令** | `pytest tests/unit/knowledge/test_stub.py -v` (Stub 覆盖率 100%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | pytest 通过日志 |

> 矩阵条目: K0-2 | V-x: X0-1

### TASK-K0-3: KnowledgeBundle v1 Schema

| 字段 | 内容 |
|------|------|
| **目标** | 定义 KnowledgeBundle 数据模型，字段对齐 02 Section 5.4.1 |
| **范围 (In Scope)** | `src/shared/types/knowledge_bundle.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Memory Core 内部存储 / Resolver 实现 / 前端集成 |
| **依赖** | -- |
| **兼容策略** | 纯新增类型定义 |
| **验收命令** | `mypy --strict src/shared/types/knowledge_bundle.py && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | Schema 完整性检查通过 |

> 矩阵条目: K0-3

---

## Phase 1-2 -- 无直接交付

> Knowledge 层在 Phase 3 才启动真实实现。Phase 0-2 Brain 通过 Stub 降级运行。

---

## Phase 3 -- 完整实现（核心交付 Phase）

### TASK-K3-1: Neo4j 图谱 Schema + 种子数据

| 字段 | 内容 |
|------|------|
| **目标** | 建立 Neo4j 图谱 Schema，导入 >= 50 个种子节点（SKU/品类/搭配关系），验证图谱查询可用 |
| **范围 (In Scope)** | `src/knowledge/graph/schema.py`, `scripts/seed_knowledge.py`, `data/seeds/` |
| **范围外 (Out of Scope)** | Qdrant 向量库初始化 / Brain 调度逻辑 / Memory Core 内部存储 / 前端集成 |
| **依赖** | Neo4j 5.x (I3-1) |
| **兼容策略** | 纯新增 Schema + 数据；不影响其他层 |
| **验收命令** | `make seed-knowledge && python -c "from neo4j import GraphDatabase; ..." && echo PASS` |
| **回滚方案** | `make clean-knowledge` 清除种子数据 |
| **证据** | Neo4j Browser 查询截图 |
| **风险** | 依赖: Neo4j 5.x (I3-1) 未部署时阻塞 / 数据: 种子数据需脱敏, 不含真实业务数据 / 兼容: 纯新增 Schema / 回滚: make clean-knowledge |
| **决策记录** | 决策: Neo4j 作为结构化资产图谱 SSOT (关系密集型) / 理由: 品类/搭配关系天然图结构 / 来源: 架构文档 02 Section 3 |

> 矩阵条目: K3-1 | V-x: X3-2

### TASK-K3-2: Qdrant 向量库初始化 + 种子数据

| 字段 | 内容 |
|------|------|
| **目标** | 初始化 Qdrant collection，导入 >= 50 条种子向量 |
| **范围 (In Scope)** | `src/knowledge/vector/init.py`, `scripts/seed_vectors.py` |
| **范围外 (Out of Scope)** | Neo4j 图谱 Schema / Brain 调度逻辑 / Memory Core 内部存储 / FK 联动 |
| **依赖** | Qdrant 1.x (I3-2) |
| **兼容策略** | 纯新增 collection + 数据 |
| **验收命令** | `python scripts/seed_vectors.py && curl localhost:6333/collections && echo PASS` |
| **回滚方案** | `curl -X DELETE localhost:6333/collections/knowledge` |
| **证据** | Qdrant Dashboard 截图 |
| **风险** | 依赖: Qdrant 1.x (I3-2) 未部署时阻塞 / 数据: 种子向量需脱敏 / 兼容: 纯新增 collection / 回滚: DELETE collection |
| **决策记录** | 决策: Qdrant 作为语义资产真值 (双用途: enterprise + personal_projection) / 理由: 高性能向量检索, 支持 payload 过滤 / 来源: 架构文档 02 Section 3 |

> 矩阵条目: K3-2 | V-x: X3-2

### TASK-K3-3: FK 联动机制 (Neo4j node_id <-> Qdrant point_id)

| 字段 | 内容 |
|------|------|
| **目标** | 写入图谱节点 -> 同步写入向量 -> FK 一致性检查，一致率 = 100% |
| **范围 (In Scope)** | `src/knowledge/sync/fk_registry.py`, `tests/unit/knowledge/test_fk.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Resolver Profile 路由 / Memory Core 存储 / Reconciliation Job |
| **依赖** | TASK-K3-1, TASK-K3-2 |
| **兼容策略** | 双写事务；失败时两侧均回滚 |
| **验收命令** | `pytest tests/unit/knowledge/test_fk.py -v` (FK 一致率 = 100%) |
| **回滚方案** | `git revert <commit>` + 运行 reconciliation 脚本 |
| **证据** | 双写事务单测通过 |
| **风险** | 依赖: K3-1 (Neo4j) + K3-2 (Qdrant) 双依赖 / 数据: 双写失败需两侧回滚, 一致性关键 / 兼容: 新增 FK 注册机制 / 回滚: git revert + reconciliation |
| **决策记录** | 决策: Write-Through + sync_status 双写一致性保障 / 理由: graph_node_id 为全局唯一 FK (ADR-024) / 来源: ADR-024, 架构文档 02 Section 7.3 |

> 矩阵条目: K3-3 | V-x: X3-2 | M-Track: MM2-3 (enterprise_media_objects 与 Neo4j FK 联动)

### TASK-K3-4: Knowledge Write API

| 字段 | 内容 |
|------|------|
| **目标** | POST 知识条目 -> Neo4j + Qdrant 双写 + FK 一致 + 审计回执，双写成功率 100% |
| **范围 (In Scope)** | `src/knowledge/api/write.py`, `tests/unit/knowledge/test_write.py` |
| **范围外 (Out of Scope)** | Brain 调度逻辑 / Resolver 查询逻辑 / 前端 Admin UI / ChangeSet 批量导入 |
| **依赖** | Gateway Admin API (G3-1), TASK-K3-3 |
| **兼容策略** | 新增 API，不影响现有读取路径 |
| **验收命令** | `pytest tests/unit/knowledge/test_write.py -v` (双写成功率 100%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 写入链路单测通过 |
| **风险** | 依赖: G3-1 (Admin API) + K3-3 (FK 联动) 双依赖 / 数据: ACL + 幂等键 + 审计回执保障写入安全 / 兼容: 新增写入 API / 回滚: git revert |
| **决策记录** | 决策: Knowledge Write API 受控写入 (ACL + 幂等 + 审计) / 理由: 知识写入需审计追溯, 幂等防重复 / 来源: 架构文档 02 Section 7.1 |

> 矩阵条目: K3-4 | V-x: X3-4 | V-fb: XF3-2

### TASK-K3-5: Diyu Resolver 最小实现 (1-2 Profile)

| 字段 | 内容 |
|------|------|
| **目标** | 按 Resolver Profile 查询 -> 返回 KnowledgeBundle (图谱结构 + 向量语义)，响应 < 200ms |
| **范围 (In Scope)** | `src/knowledge/resolver/`, `tests/unit/knowledge/test_resolver.py` |
| **范围外 (Out of Scope)** | Brain Context Assembler / Memory Core 存储 / 实体类型注册 / 写入管线 |
| **依赖** | TASK-K3-3 |
| **兼容策略** | 替换 Stub 为真实实现；Port 接口不变 |
| **验收命令** | `pytest tests/unit/knowledge/test_resolver.py -v` (查询响应 < 200ms) |
| **回滚方案** | 配置切回 Stub (`KNOWLEDGE_BACKEND=stub`) |
| **证据** | Profile 路由单测通过 |
| **风险** | 依赖: K3-3 (FK 联动) 必须就绪 / 数据: 隐私边界 -- 永不直接读 Memory Core / 兼容: 替换 Stub, Port 接口不变 / 回滚: KNOWLEDGE_BACKEND=stub |
| **决策记录** | 决策: Profile 驱动统一查询入口, FK 策略可选 (graph_first/vector_first/parallel) / 理由: 不同业务场景需不同检索策略 (ADR-033) / 来源: ADR-033, 架构文档 02 Section 5 |

> 矩阵条目: K3-5 | V-x: X3-1 | V-fb: XF3-1 | M-Track: MM2-2 (KnowledgeBundle.media_contents 扩展)

### TASK-K3-6: 实体类型注册机制

| 字段 | 内容 |
|------|------|
| **目标** | 注册新实体类型 -> Resolver 可查询该类型 |
| **范围 (In Scope)** | `src/knowledge/registry/entity_type.py`, `tests/unit/knowledge/test_entity_registry.py` |
| **范围外 (Out of Scope)** | Skill 实现细节 / Brain 调度 / Memory Core / 前端集成 |
| **依赖** | TASK-K3-5 |
| **兼容策略** | 新增注册机制，不影响现有实体类型 |
| **验收命令** | `pytest tests/unit/knowledge/test_entity_registry.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 注册后立即可查 |
| **风险** | 依赖: K3-5 (Resolver) 必须就绪 / 数据: 拔掉 Skill 时数据保留 (registered_by 标记) / 兼容: 新增注册, 不影响内核自带类型 / 回滚: git revert |
| **决策记录** | 决策: Skill 向 Knowledge Stores 注册新实体类型, 无需修改核心代码 / 理由: 可扩展性 -- 内核自带 + Skill 注册两类 / 来源: 架构文档 02 Section 4 |

> 矩阵条目: K3-6

### TASK-K3-7: ERP/PIM 变更集 (ChangeSet) 接口

| 字段 | 内容 |
|------|------|
| **目标** | 批量导入 -> 幂等 -> 审计 -> 可回滚，幂等键去重率 100% |
| **范围 (In Scope)** | `src/knowledge/import/changeset.py`, `tests/unit/knowledge/test_changeset.py` |
| **范围外 (Out of Scope)** | ERP/PIM 系统对接细节 / Brain 调度 / Memory Core / 前端集成 |
| **依赖** | TASK-K3-4 |
| **兼容策略** | 新增导入接口，幂等操作 |
| **验收命令** | `pytest tests/unit/knowledge/test_changeset.py -v` (幂等键去重率 100%) |
| **回滚方案** | ChangeSet 内置回滚机制 |
| **证据** | 幂等性单测通过 |
| **风险** | 依赖: K3-4 (Write API) 必须就绪 / 数据: 批量导入需幂等键防重, 级联删除需谨慎 / 兼容: 新增导入接口 / 回滚: ChangeSet 内置回滚 |
| **决策记录** | 决策: ChangeSet 接口 -- 批量幂等导入 + 审计 + 内置回滚 / 理由: ERP/PIM 变更需批量处理且可追溯 / 来源: 架构文档 02 Section 7.1 |

> 矩阵条目: K3-7 | M-Track: MM2-6 (企业媒体删除 ChangeSet + 级联)

---

## Phase 4 -- 性能与可靠性

### TASK-K4-1: 图谱查询性能基线

| 字段 | 内容 |
|------|------|
| **目标** | Neo4j 查询 P95 < 100ms (1M 节点) |
| **范围 (In Scope)** | `tests/perf/knowledge/test_graph_perf.py`, 性能测试脚本 |
| **范围外 (Out of Scope)** | Qdrant 向量性能 / Brain 调度逻辑 / 业务逻辑变更 / 前端集成 |
| **依赖** | TASK-K3-5 |
| **兼容策略** | 纯性能测试 + 索引优化，不改业务逻辑 |
| **验收命令** | `pytest tests/perf/knowledge/test_graph_perf.py -v` (P95 < 100ms) |
| **回滚方案** | 索引可独立删除 |
| **证据** | P95 延迟指标 |
| **风险** | 依赖: K3-5 (Resolver) + 1M 节点测试数据准备 / 数据: 性能测试数据需模拟, 不用生产数据 / 兼容: 纯索引优化 / 回滚: 索引可独立删除 |
| **决策记录** | 决策: P95 < 100ms 作为图谱查询性能基线 / 理由: Resolver 响应 < 200ms 中图谱查询占主要耗时 / 来源: 架构文档 02 Section 5.3 |

> 矩阵条目: K4-1 | V-x: X4-1

### TASK-K4-2: 向量检索性能基线

| 字段 | 内容 |
|------|------|
| **目标** | Qdrant 查询 P95 < 50ms (1M vectors) |
| **范围 (In Scope)** | `tests/perf/knowledge/test_vector_perf.py` |
| **范围外 (Out of Scope)** | Neo4j 图谱性能 / Brain 调度逻辑 / 业务逻辑变更 / 前端集成 |
| **依赖** | TASK-K3-2 |
| **兼容策略** | 纯性能测试 + 参数调优 |
| **验收命令** | `pytest tests/perf/knowledge/test_vector_perf.py -v` (P95 < 50ms) |
| **回滚方案** | 参数可回退 |
| **证据** | P95 延迟指标 |
| **风险** | 依赖: K3-2 (Qdrant) + 1M 向量测试数据 / 数据: 性能测试数据需模拟 / 兼容: 纯参数调优 / 回滚: 参数可回退 |
| **决策记录** | 决策: P95 < 50ms 作为向量检索性能基线 / 理由: Resolver 响应 < 200ms 中向量检索需更低延迟 / 来源: 架构文档 02 Section 5.3 |

> 矩阵条目: K4-2 | V-x: X4-1

### TASK-K4-3: FK 一致性 Reconciliation Job

| 字段 | 内容 |
|------|------|
| **目标** | 人为破坏 FK -> Job 检测并修复 -> sync_status 恢复，修复后一致率 = 100% |
| **范围 (In Scope)** | `src/knowledge/sync/reconciliation.py`, `tests/unit/knowledge/test_reconciliation.py` |
| **范围外 (Out of Scope)** | 正常双写路径 / Brain 调度逻辑 / Memory Core / 前端集成 |
| **依赖** | TASK-K3-3 |
| **兼容策略** | 新增修复 Job，不影响正常双写路径 |
| **验收命令** | `pytest tests/unit/knowledge/test_reconciliation.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 修复逻辑单测通过 |
| **风险** | 依赖: K3-3 (FK 联动) 必须就绪 / 数据: 修复操作需幂等, 避免二次破坏 / 兼容: 新增 Job, 不影响正常写入 / 回滚: git revert |
| **决策记录** | 决策: Reconciliation Job 定期检测并修复 FK 不一致 / 理由: 双写无法保证 100% 原子, 需异步修复 (ADR-024) / 来源: ADR-024, 架构文档 02 Section 7.3 |

> 矩阵条目: K4-3 | V-x: X4-3

---

## Phase 5 -- 平台化

### TASK-K5-1: Capability Registry 统一注册中心

| 字段 | 内容 |
|------|------|
| **目标** | Skill/Tool/Model/EntityType 统一注册查询 |
| **范围 (In Scope)** | `src/knowledge/registry/capability.py`, `tests/unit/knowledge/test_capability.py` |
| **范围外 (Out of Scope)** | 各资源内部实现 / Brain 调度 / Memory Core / 前端集成 |
| **依赖** | -- |
| **兼容策略** | 新增注册中心，不影响现有注册机制 |
| **验收命令** | `pytest tests/unit/knowledge/test_capability.py -v` (4 类资源全可查) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 注册/查询单测通过 |
| **风险** | 依赖: N/A -- 独立新增 / 数据: 注册数据需与各层实际能力一致 / 兼容: 新增注册中心, 不影响现有 / 回滚: git revert |
| **决策记录** | 决策: 统一 Capability Registry 管理 4 类资源 / 理由: 避免各层独立注册导致不一致 / 来源: 架构文档 02 Section 4 |

> 矩阵条目: K5-1 | V-x: X5-2

### TASK-K5-2: 可解释性面板 injection_receipt.explanation_trace

| 字段 | 内容 |
|------|------|
| **目标** | 管理端可查看每次知识注入的溯源链 |
| **范围 (In Scope)** | `src/knowledge/explain/trace.py`, E2E 测试 |
| **范围外 (Out of Scope)** | Admin UI 前端实现 / Brain 调度 / Memory Core / 写入管线改动 |
| **依赖** | TASK-K3-4, Admin UI |
| **兼容策略** | 新增查询接口，不影响写入路径 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/knowledge/explanation-trace.spec.ts` (管理端查看溯源链完整性) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 溯源链可追溯截图 |
| **风险** | 依赖: K3-4 (Write API) + Admin UI 前端 / 数据: 溯源链数据需完整, injection_receipt 格式稳定 / 兼容: 新增查询接口 / 回滚: git revert |
| **决策记录** | 决策: injection_receipt.explanation_trace 提供可解释性溯源 / 理由: 企业级知识管理需审计追溯能力 / 来源: 架构文档 02 Section 7.2 |

> 矩阵条目: K5-2 | M-Track: MM3-2 (跨模态语义检索依赖此溯源链)

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。M-Track 中与 Knowledge 相关的条目 (MM2-2/MM2-3) 见各层任务卡的 [M-Track] 标记。
