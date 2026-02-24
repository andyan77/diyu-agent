# DIYU Agent 深度审计报告 — 全 Phase 缺失清单

> **版本:** v3.1 (治理基础设施补全版)
> **审计日期:** 2026-02-23
> **方法论:** 四视角交叉审计 + 3 层验证法 + 独立再验证 + **治理基础设施审计**
> **审计范围:** 323 节点 (254 层维度 + 23 M-Track + 46 验证) + **7 项基础设施缺陷**
> **参考标准:** `docs/governance/architecture-phase-delivery-map.md` v1.0

---

## 审计方法论演进

### V1 → V2 → V3 → V3.1 方法论对比

| 维度 | V1 审计 | V2 审计 | V3 审计 | V3.1 审计 (本版) |
|------|---------|---------|---------|-----------------|
| 审计路径 | 矩阵→代码 (单向) | 矩阵→代码 (3层深度) | 四视角交叉 | 四视角 + **治理基础设施审计** |
| 检查深度 | L1 文件存在 | L1+L2+L3 | L1+L2+L3 + L4 验证可信度 | L1-L4 + **L5 基础设施自洽性** |
| 偏差修正 | — | 7 种偏差 | 7 种 + 第8种 | 8 种 + **第9种: 门禁覆盖率偏差** |
| Agent 结论 | 直接采信 | 交叉验证14项 | 全部独立再验证 | 全部再验证 + **基础设施可执行验证** |
| 审计对象 | 代码 | 代码 | 代码 + 验证体系 | 代码 + 验证体系 + **验证基础设施本身** |

### V3 四视角审计框架

四条独立审计路径，每条从不同 SSOT 出发，同时收敛到生产代码：

```
视角1: 设计文档 (docs/architecture/) → 提取"承诺" → 验证代码是否兑现
视角2: 任务卡 (docs/task-cards/)     → 提取"验收标准" → 验证代码是否满足
视角3: 里程碑矩阵 (milestone-matrix.yaml) → status:done 的 check 命令 → 验证 check 是否真测了实质
视角4: Gate 脚本 (verify_phase.py)   → 逆向分析 → check 到底能发现什么问题
```

### 第 8-9 种偏差: 验证体系自身偏差

| # | 偏差类型 | 表现 | 发现版本 |
|---|---------|------|---------|
| 8 | **验证体系信任偏差** | V2 从未质疑"测试通过=功能正确""Gate PASS=可交付" | V3: Gate 91.4% 表面检查；RLS 测试=正则匹配；性能测试=空 stub 计时 |
| 9 | **门禁覆盖率偏差** | V3 统计了 221 个 DONE 节点，但从未计算"多少 DONE 有 gate check 覆盖"。"DONE" 给人"已验证"印象，实际 50%+ 节点为自我声明无门禁背书 | V3.1: Phase 1 覆盖率 29% (8/28)，Phase 2 覆盖率 48% (25/52)，47 个 done 节点无任何 gate |

---

## 全局统计

### V2 统计 (保留，基于矩阵节点)

| Phase | 总节点 | DONE | PARTIAL | GAP | 完成率 |
|-------|-------|------|---------|-----|-------|
| Phase 0 | 64 | 59 | 3 | 2 | 92.2% |
| Phase 1 | 33 | 27 | 4 | 2 | 81.8% |
| Phase 2 | 62 | 55 | 4 | 3 | 88.7% |
| Phase 3 | 61 | 46 | 6 | 9 | 75.4% |
| Phase 4 | 63 | 34 | 13 | 16 | 54.0% |
| Phase 5 | 40 | 0 | 3 | 37 | 0.0% |
| **合计** | **323** | **221** | **33** | **69** | **68.4%** |

### V3 补充: "DONE 的可信度" 维度

上述 221 个 DONE 节点中，经四视角验证，部分 DONE 的验证基础不牢固：

| 验证可信度 | DONE 节点数 | 占比 | 说明 |
|-----------|-----------|------|------|
| **高可信**: 真实逻辑 + 有意义测试 | ~170 | 77% | Port 定义、核心引擎、RLS DDL |
| **中可信**: 存在但测试用 stub/fake | ~35 | 16% | 性能基线、outbox、resilience |
| **低可信**: Gate check 仅表面验证 | ~16 | 7% | RLS 运行时、migration 结构、SLI 集成 |

---

## Phase 0 缺失清单 (2 GAP + 3 PARTIAL)

| # | 节点 | 类型 | 缺失描述 | 证据 | 严重度 |
|---|------|------|---------|------|--------|
| 1 | T0-3 | GAP | **ToolProtocol 基类不存在** — Tool 实现 (web_search/image_analyze/audio_transcribe) 存在但无统一 Protocol | 无 `src/tool/core/protocol.py` | P1 |
| 2 | D0-9 | GAP | **PR 模板 + CODEOWNERS 不存在** — 治理完整性缺失 | 无 `.github/pull_request_template.md`, 无 `CODEOWNERS` | P2 |
| 3 | K0-2 | PARTIAL | KnowledgePort 无显式 Stub 类 — Brain 用降级路径替代 | `conversation.py:142` 检查 None | P3 |
| 4 | S0-2 | PARTIAL | SkillRegistry 无显式 Stub — Brain 用 None 检查替代 | `conversation.py:148` | P3 |
| 5 | MM0-3 | PARTIAL | personal/enterprise_media_objects DDL **未找到迁移** | 无 migration 007+ 创建此表 | P1-M |

---

## Phase 1 缺失清单 (2 GAP + 4 PARTIAL)

| # | 节点 | 类型 | 缺失描述 | 证据 | 严重度 |
|---|------|------|---------|------|--------|
| 6 | G1-3 / I1-4 | GAP | **RBAC 角色不一致** — Gateway 3 角色 (admin/member/viewer) vs Infra 5 角色 (super_admin/org_admin/manager/member/viewer) | `gateway/middleware/rbac.py` vs `infra/auth/rbac.py` | **P0-BLOCKING** |
| 7 | I1-6 | PARTIAL | event_outbox 仅 **内存实现** — `self._events: dict[UUID, OutboxEvent] = {}`, 无 SQL adapter, 无持久化 | `infra/events/outbox.py:54` 用 dict 存储 | P1 |
| 8 | OS1-4 | PARTIAL | JWT **仅实现过期检查** — 缺 refresh token rotation 和 revocation | `gateway/middleware/auth.py:54-66` | P1 |
| 9 | OS1-6 | PARTIAL | 前端 XSS 防护 — CSP 已配置, **DOMPurify 未验证** | 后端 `security_headers.py` 有 CSP | P2 |
| 10 | FW1-2 | PARTIAL | AuthProvider + PermissionGate — 未深度验证前端实现 | 目录存在但未逐行审查 | P3 |
| 11 | I1-4 | GAP | **Infra RBAC 5 角色未被 Gateway 消费** — check_permission() 函数孤立 | `infra/auth/rbac.py` 有 151 行但未接入 | P0 |

---

## Phase 2 缺失清单 (3 GAP + 4 PARTIAL)

| # | 节点 | 类型 | 缺失描述 | 证据 | 严重度 |
|---|------|------|---------|------|--------|
| 12 | MC2-7 | **GAP** | **confidence_effective 衰减从未调用** — `read_personal_memories()` 返回原始 confidence, 不做时间衰减 | `pg_adapter.py:64-176` 无衰减调用 | P0 |
| 13 | MC2-5 | **GAP** | **Evolution Pipeline 不调用 LLM** — `llm: LLMCallable` 参数被接受但**从未 .call()** | `evolution/pipeline.py:85-160` 纯规则 | P0 |
| 14 | B2-5 | **GAP** | Memory 写入管线 Observer→Analyzer→Evolver **纯规则** — 架构要求 LLM 驱动提取 | 同上 | P0 |
| 15 | B2-4 | PARTIAL | Context Assembler CE 增强 — Query Rewriting 有, RRF 有, **5 因子重排序缺失** | `context_assembler.py:272-290` 线性拼接 | P1 |
| 16 | B2-1 | PARTIAL | 对话引擎 **硬编码 [-10:] 历史** — 无 token budget 动态裁切 | `conversation.py:351` | P1 |
| 17 | MC2-6 | PARTIAL | MemoryReceipt 字段语义与 ADR-038 5 元组不完全对齐 | `receipt.py:25-42` | P2 |
| 18 | D2-3 | PARTIAL | 内部 dogfooding 环境 — docker-compose 存在但无专用 dogfooding 配置 | 无 `make verify-dogfooding` | P3 |

---

## Phase 3 缺失清单 (9 GAP + 6 PARTIAL)

| # | 节点 | 类型 | 缺失描述 | 证据 | 严重度 |
|---|------|------|---------|------|--------|
| 19 | S3-1 | **GAP** | **ContentWriterSkill 纯模板** — `_build_content()` 是 f-string, **未调用 LLMCallPort** | `content_writer.py:128-154` | P0 |
| 20 | S3-2 | **GAP** | **MerchandisingSkill 硬编码规则** — 无 Neo4j 图谱查询, 注释说 "for now rule-based" | `merchandising.py:146-183` | P0 |
| 21 | B3-4 | **GAP** | **NegativeFeedbackFuse 已实现但从未被调用** — conversation.py, context_assembler.py 均未 import | `brain/memory/feedback.py` 孤立 | P0 |
| 22 | MC3-1 | **GAP** | Promotion Pipeline `_check_conflict()` **硬编码 False** — "Real implementation would embed content" | `promotion/pipeline.py:302-313` | P1 |
| 23 | K3-5 | **GAP** | Resolver `vector_first` 策略 **返回空 KnowledgeBundle** — "Real implementation needs embedding model call" | `resolver/resolver.py:250-279` | P1 |
| 24 | K3-7 | **GAP** | ChangeSet **违反层边界** — 直接访问 `_fk_registry._neo4j` 私有字段 | `importer/changeset.py:191-196` | P1 |
| 25 | K3-6 | PARTIAL | 实体类型注册 — CORE_TYPE_IDS 有 8 类型, **缺 PlatformTone/RegionInsight** | `entity_type.py:38-49` | P2 |
| 26 | S0-1 | PARTIAL | SkillProtocol **缺 5 个扩展字段** — capabilities, required_permissions, required_tools, entity_types, knowledge_profiles | `protocol.py:56-122` | P2 |
| 27 | K3-3 | PARTIAL | FK 联动 — 存在但**并行 FK 一致性未验证** | `fk_registry.py` 无并行场景测试 | P2 |
| 28 | MM0-7 | PARTIAL | 安全管线 Stage 1 — 测试存在但**无生产代码** | `test_media_safety.py` 有, `src/` 无 | P2-M |
| 29 | MM1-2 | GAP | WS payload 媒体扩展 — **未实现** | 无 ai_response_chunk media 字段 | P2-M |
| 30 | MM1-4 | GAP | Brain 多模态模型选择逻辑 — **未实现** | Brain 层无多模态路由 | P2-M |
| 31 | MM1-5 | PARTIAL | security_status 三层拦截 — 测试有, **生产代码缺** | 同 #28 | P2-M |
| 32 | K3-8 (ACL) | GAP | Resolver **无 ACL JSONB 验证** — 仅 org_chain 过滤, 无 JSONB 级字段级权限 | `resolver.py:118-152` | P2 |

---

## Phase 4 缺失清单 (16 GAP + 13 PARTIAL)

| # | 节点 | 类型 | 缺失描述 | 证据 | 严重度 |
|---|------|------|---------|------|--------|
| 33 | B4-2 | **GAP** | **动态预算分配器** — 无 DynamicBudgetAllocator 实现 | grep 无结果 | P0 |
| 34 | K4-3 | **GAP** | **FK 一致性 Reconciliation Job** — 无修复逻辑、无 Celery task | grep `reconcil` 无结果 | P1 |
| 35 | OS4-7 | **GAP** | **渗透测试基线** — 无 OWASP Top 10 报告或 ZAP/Burp 配置 | 无文件 | P1 |
| 36 | D4-1 | **GAP** | **升级回滚流程产品化** — 无 upgrade/rollback 脚本 | 无文件 | P1 |
| 37 | D4-3 | **GAP** | **一键诊断包** — `scripts/doctor.py` 存在但非 `diyu diagnose` CLI | 命名不匹配 | P2 |
| 38 | D4-4 | **GAP** | **密钥轮换 + 证书管理** — 无轮换脚本 | 无文件 | P1 |
| 39 | D4-5 | **GAP** | **轻量离线** — 无 docker save/load 打包脚本 | 无文件 | P2 |
| 40 | FW4-3 | **GAP** | **暗色/亮色模式** — 无 theme toggle 组件 | grep 无结果 | P2 |
| 41 | FW4-4 | **GAP** | **键盘快捷键** — 无全局快捷键系统 | 仅 MemoryPanel 有局部 keydown | P2 |
| 42 | FA4-2 | **GAP** | **配额管理页** — Admin 无 quota 管理 UI | 无文件 | P2 |
| 43 | FA4-3 | **GAP** | **备份管理页** — Admin 无 backup 管理 UI | 无文件 | P2 |
| 44 | I4-1 | PARTIAL | Prometheus 已配, **Grafana 看板 JSON 缺失** | 无 `deploy/grafana/` 目录 | P1 |
| 45 | OS4-1 | PARTIAL | 7 项 Brain SLI 已埋点, **Grafana 看板缺失** | `sli.py` 有指标, 无看板 | P1 |
| 46 | B4-3 | PARTIAL | TruncationPolicy 已实现, **未集成到 ContextAssembler** | `truncation.py` 存在, 无调用方 | P1 |
| 47 | B4-5 | PARTIAL | Sanitizer 已实现, **未集成到 ConversationEngine** | `pattern_filter.py` 存在, 无调用方 | P1 |
| 48 | S4-1 | PARTIAL | 熔断器已实现, **与 SkillExecutor 集成未验证** | `circuit_breaker.py` 存在 | P2 |
| 49 | S4-2 | PARTIAL | 超时机制已实现, **与 SkillExecutor 集成未验证** | `timeout.py` 存在 | P2 |
| 50 | T4-1 | PARTIAL | Tool 独立计费 — DDL 存在, **Job 逻辑未验证** | `tool_usage_records` 表有 | P2 |
| 51 | T4-2 | PARTIAL | 重试退避已实现, **与 Tool Executor 集成未验证** | `retry.py` 存在 | P2 |
| 52 | G4-3 | PARTIAL | 限流 per-org 已实现, **per-user 缺失** | `rate_limit.py` key=org_id | P2 |
| 53 | MC4-3 | PARTIAL | deletion_timeout_rate SLI — **无专用计数器** | SLI 框架有, 此指标无; `src/` grep 零结果 | P2 |
| 54 | K4-1 | PARTIAL | 图谱查询基线 — **stub CI 基线, 非 1M 节点实测** | `test_graph_perf.py` 用 `InMemoryKnowledgeStub` 返回空列表 | P3 |
| 55 | K4-2 | PARTIAL | 向量检索基线 — **stub CI 基线, 非 1M 向量实测** | `test_vector_perf.py` 用 `InMemoryVectorStub` 返回空列表 | P3 |
| 56 | FW4-1 | PARTIAL | 性能预算 — Lighthouse 配置有, **无通过证据** | `lighthouserc.js` 存在 | P2 |
| 57 | OS4-8 | PARTIAL | a11y 审计 — 脚本存在, **执行结果未验证** | `frontend/scripts/axe-core-cli` | P2 |
| 58 | MM2-1~6 | GAP/PARTIAL | 企业多模态 M2 — **测试存在但生产代码缺失** | tests/integration 有 fake, src/ 无 | P2-M |

---

## Phase 5 缺失清单 (37 GAP + 3 PARTIAL) — 预期范围

> Phase 5 为设计目标阶段, 当前 `current_phase: "phase_3"`, 全部 GAP 属正常。仅列出关键节点。

| # | 节点组 | 数量 | 说明 |
|---|--------|------|------|
| 59 | B5-1~4 | 4 GAP | Memory Governor / Calibration / Multi-LLM / Consolidation |
| 60 | MC5-1~3 | 3 GAP | Auto-merge / Contextual Chunking / Crypto Shredding |
| 61 | K5-1~2 | 2 GAP | Capability Registry / Explainability Panel |
| 62 | S5-1~2 | 2 GAP | A/B Testing / Multimodal Capability |
| 63 | T5-1~2 | 2 GAP | Cost Dashboard / Contract Evaluation |
| 64 | G5-1~2 | 2 GAP | API Version Negotiation / Deprecation Warning |
| 65 | I5-1~2 | 1 GAP + 1 PARTIAL | Event Mesh (outbox 有但无 NATS/Kafka) / Schema Registry |
| 66 | OS5-1~6 | 4 GAP + 2 PARTIAL | SSOT Check (脚本有) / Guard (脚本有) / Exception Register / Audit Template / GDPR Report / Runbook |
| 67 | D5-1~4 | 4 GAP | 与 OS5 重叠 + verify-phase-5 |
| 68 | FA5-1~2 | 2 GAP | Compliance Report UI / Exception Register UI |
| 69 | FW5-1 | 1 GAP | Voice Interaction |
| 70 | MM3-1~3 | 3 GAP | Copyright Detection / Cross-modal Retrieval / Contract Eval |
| 71 | X5-1~4 + XM3-1~2 | 6 GAP | Phase 5 跨层验证全部未开始 |

**Phase 5 总计: 37 GAP + 3 PARTIAL = 40 节点**

---

## M-Track 汇总

| Stage | 节点数 | DONE | PARTIAL | GAP | 完成率 |
|-------|-------|------|---------|-----|-------|
| M0 基座 | 8 | 5 | 2 | 1 | 62.5% |
| M1 个人 | 6 | 1 | 2 | 3 | 16.7% |
| M2 企业 | 6 | 0 | 3 | 3 | 0% |
| M3 成熟 | 3 | 0 | 1 | 2 | 0% |
| **合计** | **23** | **6** | **8** | **9** | **26.1%** |

**M-Track 关键阻塞:** MM0-3 (media DDL 缺失) 阻塞所有 M1/M2/M3 节点。

---

## 跨层验证节点汇总

| Phase | 总验证节点 | DONE | PARTIAL | GAP |
|-------|---------|------|---------|-----|
| P0 (X0 + XM0) | 6 | 5 | 1 | 0 |
| P1 (X1) | 5 | 4 | 1 | 0 |
| P2 (X2 + XF2) | 10 | 9 | 1 | 0 |
| P3 (X3 + XM1 + XF3) | 11 | 7 | 3 | 1 |
| P4 (X4 + XM2 + XF4) | 12 | 8 | 3 | 1 |
| P5 (X5 + XM3) | 6 | 0 | 0 | 6 |
| **合计** | **50** | **33** | **9** | **8** |

---

## V3 新增: 四视角审计发现

> 以下为 V2 审计未覆盖的系统性盲区，经独立代码验证确认。

### 视角1: 设计文档承诺审计 (docs/architecture/ → 代码)

从 8 个架构文档中提取 45 个核心承诺，逐条验证兑现情况：

**总体: 38 FULFILLED / 7 PARTIAL / 0 BROKEN**

架构核心承诺全部兑现:
- 6 层分离 + Port-based 依赖反转
- 双 SSOT (MemoryCore pg + Knowledge neo4j/qdrant) 物理隔离
- 隐私硬边界 (Knowledge Resolver 无 MemoryCorePort 依赖)
- pgvector 混合检索 (semantic + keyword + RRF)

**7 个 PARTIAL 承诺 (V2 未覆盖的新发现):**

| # | 来源文档 | 承诺 | 代码现实 | 证据 | V3 严重度 |
|---|---------|------|---------|------|----------|
| V3-1 | 05-Gateway | **三步媒体上传协议** (init/S3直传/complete, 含EXIF清洗+ClamAV扫描+checksum校验) | presigned URL 是拼接字符串非真实 S3 签名; complete 步骤无安全扫描; 存储用**内存 dict** `_uploads = {}` | `upload.py:117,143-144,197` | **P1** |
| V3-2 | 05-Gateway | **LLM Gateway Fallback 链** (断路器+降级矩阵+provider fallback) | 无断路器状态机, 无 provider fallback; 单 try/except 返回 502 | `gateway/llm/router.py:89-91` | **P1** |
| V3-3 | 06-基础设施 | **event_outbox Transactional Outbox 模式** (与业务写同事务, poller 投递, 幂等性) | 内存 dict 实现, 无 SQL adapter, 无 poller, 不可能与业务写同事务 | `infra/events/outbox.py:54` | P1 (已在 #7) |
| V3-4 | 03-Skill | **SkillResult 完整 Schema** (含 tool_calls 字段) | Port 定义简化版, 缺 tool_calls 字段 | `ports/skill_registry.py:52-61` | P2 |
| V3-5 | 07-部署安全 | **PostgreSQL HA** (Streaming Replication + 自动 Failover) | 架构承诺, docker-compose.ha.yml 存在, 但 HA 拓扑为模拟而非 Patroni 真实集群 | 部署配置级, 非代码级 | P2 |

### 视角2: 任务卡验收标准审计 (docs/task-cards/ → 代码)

从 21 个任务卡中抽样审计 60 个关键验收标准 (AC)：

**总体: 26 PASS / 26 PARTIAL / 8 FAIL**

**按验收类型分布 (关键发现):**

| AC 类型 | PASS | PARTIAL | FAIL | 通过率 | 评价 |
|---------|------|---------|------|--------|------|
| **安全关键** (RLS/跨租户泄露=0) | 4/4 | 0/4 | 0/4 | **100%** | Gate 门禁有效 |
| **性能关键** (延迟/P95) | 0/8 | 5/8 | 3/8 | **0%** | 见下详细分析 |
| **数据完整性** | 15/25 | 8/25 | 2/25 | 60% | 核心路径 OK |
| **测试覆盖率要求** | 7/23 | 13/23 | 3/23 | 30% | 无 CI gate |

**V2 未覆盖的新发现:**

| # | 任务卡 | AC 原文 | 代码现实 | 证据 | V3 严重度 |
|---|--------|--------|---------|------|----------|
| V3-6 | B4-1 | Context Assembler P95<200ms | 测试存在但用 `FakeMemoryCore`(内存), 测量**接口开销**而非真实 DB 延迟; 注释自述 "measures assembler overhead, not network/database latency" | `test_assembler_latency.py:8-9` | **P1** |
| V3-7 | K4-1 | Neo4j 图谱查询 P95<100ms (1M节点) | 测试用 `InMemoryKnowledgeStub` 返回**空列表 `[]`**, 实际测量 Python 函数调用开销(~0.01ms), 与 1M 节点图谱完全无关 | `test_graph_perf.py:19-31,67-71` | **P1** |
| V3-8 | K4-2 | Qdrant 向量检索 P95<50ms (1M向量) | 测试用 `InMemoryVectorStub` 返回**空列表 `[]`**, 零实际向量运算 | `test_vector_perf.py:19-35,74` | **P1** |
| V3-9 | B4-4 | 7 项 Brain SLI 全部埋点 | `BrainSLI` 类定义 7 指标, 但**仅 2/7 被集成**: `context_assembly_duration` 和 `memory_retrieval_count` 接入 `context_assembler.py`; **其余 5 项** (llm_call_duration, memory_write_duration, skill_execution_duration, conversation_turn_duration, knowledge_resolution_duration) **未被 conversation.py 调用** | `context_assembler.py:24,84,110,130` vs `conversation.py` grep BrainSLI 零结果 | **P1** |
| V3-10 | MC4-3 | deletion_timeout_rate SLI=0% | `src/` 全局 grep `deletion_timeout` 零结果, 无专用计数器 | grep 确认 | P2 (已在 #53) |
| V3-11 | I2-3 | Token 计费误差=0 (硬指标) | 无浮点精度测试, 无 Decimal 类型验证 | grep `decimal.*billing\|billing.*float` 零结果 | **P2** |
| V3-12 | — | **pytest --cov CI 门禁不存在** | AC 要求覆盖率>=80%, 但 `pyproject.toml` 和 `Makefile` 均无 coverage 配置; 无 `pytest-cov` 门禁 | grep `coverage\|--cov\|pytest-cov` in pyproject.toml 零结果 | **P1** |

### 视角3: 里程碑矩阵 check 可信度审计 (milestone-matrix.yaml)

78 个 status:done 节点的 check 命令深度分析：

| check 类型 | 数量 | 占比 | 检测能力 |
|-----------|------|------|---------|
| **pytest 测试** | 33 | 42% | 测试通过 (但测试本身可能测 stub) |
| **bash 脚本** | 15 | 19% | 脚本返回 0 |
| **前端构建** (pnpm build/playwright) | 14 | 18% | 类型检查+lint 通过 |
| **Python 脚本** | 15 | 19% | 脚本条件满足 |
| **文件存在** (test -f) | 11 | 14% | 文件在磁盘上 |
| **正则匹配** (grep -q) | 2 | 3% | 字符串出现 |

**关键发现: RLS 隔离测试的"表面性"**

| # | 节点 | check 声称 | check 实际 | 证据 | V3 严重度 |
|---|------|-----------|-----------|------|----------|
| V3-13 | I1-3 (Phase 1) | RLS policies 运行时隔离 | **纯正则匹配 migration 文件**: `re.search(rf"ENABLE ROW LEVEL SECURITY.*{table}", migration_source)` — 从未连接 PostgreSQL, 从未执行跨租户 SELECT 验证 | `test_rls_isolation.py:55-65`, 文件注释 L8-9: "without requiring a running PostgreSQL instance" | **P1** |
| V3-14 | OS3-6 (Phase 3) | `p3-tenant-isolation-runtime` 运行时隔离 | **同样是正则匹配**: `test_tenant_crossover.py` 完全复制 smoke 版逻辑, 注释 L12: "via static analysis of migration DDL (no live DB required)" | `test_tenant_crossover.py:11-14,55-65` | **P1** |
| V3-15 | — | `check_rls.sh` 脚本 | 同样是对 migration 文件做 `grep -ciE "ENABLE ROW LEVEL SECURITY"`, 无 DB 连接 | `scripts/check_rls.sh:91,120-123` | P2 |

> **风险评估**: 整个 RLS 验证链 (test_rls_isolation.py → test_tenant_crossover.py → check_rls.sh) 全部基于**静态正则匹配 migration 源码**。如果 migration DDL 语法正确但 PG session variable `app.current_org_id` 从未被正确设置, 或 RLS policy 有逻辑错误 (如 `USING(true)` 而非 `USING(org_id = current_setting(...))`), 所有测试仍会 PASS。

**Fake adapter 模式 (正面发现)**:
- Phase 2 exit criteria 包含 `p2-no-mock-py` 和 `p2-no-mock-ts` 检查
- 测试使用 `FakeLLM(LLMCallPort)`, `FakeMemoryCore(MemoryCorePort)` — 实现 Port ABC 的 Fake, 非 `unittest.mock.patch`
- `check_no_mock.py` + `check_no_vacuous_pass.py` 确保测试基本质量
- **这是架构合规的正面证据**, 但不能替代真实外部服务的集成测试

### 视角4: Gate 脚本逆向审计 (verify_phase.py)

**verify_phase.py 结构**: 337 行, 读 YAML exit_criteria → subprocess 执行 check → 看 exit code 0/非0

| 检查维度 | 有 | 无 |
|---------|---|---|
| 文件存在 | Y | — |
| 测试通过 (exit 0) | Y | — |
| 构建成功 | Y | — |
| mock 禁用 | Y (check_no_mock.py) | — |
| 空跳过检测 | Y (check_no_vacuous_pass.py) | — |
| **代码逻辑是否为 stub** | — | **X** |
| **函数是否被调用** | — | **X** |
| **跨层契约一致性** | — | **X** |
| **LLM 调用 vs 硬编码** | — | **X** |
| **运行时行为验证** | — | **X** |

**P0 问题检测能力测试**:

| P0 问题 | Gate 能否检测 | 原因 |
|---------|-------------|------|
| P0-1: RBAC 角色不一致 (3 vs 5) | **NO** | 无跨文件一致性检查, 两边测试各自 PASS |
| P0-2: confidence_effective 从未调用 | **NO** | 函数存在, 测试可不触发衰减路径而 PASS |
| P0-3: Evolution Pipeline 不调用 LLM | **NO** | Fake LLM 不报错, 规则路径走通即 PASS |
| P0-4: Memory 写入管线纯规则 | **NO** | 同上 |
| P0-5: ContentWriterSkill 纯模板 | **NO** | f-string 输出字符串, 测试可断言非空即 PASS |
| P0-6: MerchandisingSkill 硬编码 | **NO** | 硬编码规则返回结果, 测试 PASS |
| P0-7: NegativeFeedbackFuse 未集成 | **NO** | feedback.py 单元测试 PASS, 但无人调用 |
| P0-8: 动态预算分配器不存在 | **MAYBE** | 取决于是否有检查此文件存在的 check |

**检测率: 0-1/8 (0%-12.5%)**

**Gate PASS 的真实含义**:

当 `verify_phase.py --phase N` 报 GO 时:
- **证明了**: 文件存在, 测试 exit 0, 构建通过, 无 unittest.mock 滥用
- **未证明**: 代码逻辑非 stub, 函数被调用链消费, 跨层一致, LLM 真实调用, 运行时隔离生效

---

## 按严重度分类的行动清单 (V3.1 合并版)

### P0 — 阻塞级 (必须在当前 Phase 修复)

| # | 节点 | 描述 | 修复方向 | 来源 |
|---|------|------|---------|------|
| 6 | G1-3/I1-4 | RBAC 角色不一致 (3 vs 5) | 统一为 5 角色模型, Gateway 消费 Infra RBAC | V2 |
| 12 | MC2-7 | confidence_effective 从未调用 | pg_adapter.read_personal_memories() 加衰减计算 | V2 |
| 13 | MC2-5 | Evolution Pipeline 不调用 LLM | pipeline.py 的 Observer/Analyzer 调用 llm.call() | V2 |
| 14 | B2-5 | Memory 写入管线纯规则 | 同 #13 | V2 |
| 19 | S3-1 | ContentWriterSkill 纯模板 | _build_content() 调用 LLMCallPort.call() | V2 |
| 20 | S3-2 | MerchandisingSkill 硬编码规则 | 接入 Neo4j 图谱查询 | V2 |
| 21 | B3-4 | NegativeFeedbackFuse 从未集成 | conversation.py/context_assembler.py import 并调用 | V2 |
| 33 | B4-2 | 动态预算分配器不存在 | 新建 src/brain/budget/allocator.py | V2 |

### P1 — 重要级 (Phase 门禁前修复)

| # | 节点 | 描述 | 修复方向 | 来源 |
|---|------|------|---------|------|
| 1 | T0-3 | ToolProtocol 基类不存在 | 新建 src/tool/core/protocol.py | V2 |
| 7 | I1-6 | event_outbox 仅内存实现 | 新建 pg_outbox_adapter.py | V2 |
| 8 | OS1-4 | JWT 缺 rotation/revocation | 加 refresh token 机制 | V2 |
| 15 | B2-4 | CE 5 因子重排序缺失 | context_assembler.py 加 multi-signal reranking | V2 |
| 16 | B2-1 | 对话历史硬编码 [-10:] | 改为 token budget 动态裁切 | V2 |
| 22 | MC3-1 | Promotion _check_conflict() 返回 False | 实现向量相似度冲突检测 | V2 |
| 23 | K3-5 | vector_first 返回空 | 实现 embedding 查询 | V2 |
| 24 | K3-7 | ChangeSet 层边界违规 | 通过 public interface 访问 | V2 |
| 34 | K4-3 | FK Reconciliation Job 不存在 | 新建 Celery task | V2 |
| 35 | OS4-7 | 渗透测试基线不存在 | 运行 OWASP ZAP 扫描 | V2 |
| 36 | D4-1 | 升级回滚脚本不存在 | 新建 scripts/upgrade.sh + rollback.sh | V2 |
| 38 | D4-4 | 密钥轮换脚本不存在 | 新建 scripts/rotate_keys.sh | V2 |
| 44 | I4-1 | Grafana 看板缺失 | 新建 deploy/grafana/dashboards/ | V2 |
| 45 | OS4-1 | SLI Grafana 看板缺失 | 同上 | V2 |
| 46 | B4-3 | TruncationPolicy 未集成 | ContextAssembler 调用 FixedPriorityPolicy | V2 |
| 47 | B4-5 | Sanitizer 未集成 | ConversationEngine 输入管线调用 | V2 |
| 5 | MM0-3 | media_objects DDL 缺失 | 新建 migration 007 | V2 |
| V3-1 | G2-6 | **上传协议内存存储 + 无安全扫描** | 接入 ObjectStoragePort (真实 S3/MinIO presigned), complete 步加 checksum 校验 | **V3 视角1** |
| V3-2 | G2-3 | **LLM Gateway 无 Fallback 链** | 实现 provider fallback + 断路器状态机 | **V3 视角1** |
| V3-6~8 | B4-1/K4-1/K4-2 | **性能基线测试为空 stub 计时** | 补充 integration 级基线 (连接真实 DB/向量库, 至少 1K 条数据) | **V3 视角2** |
| V3-9 | B4-4 | **BrainSLI 5/7 指标未集成** | ConversationEngine 接入 llm_call_duration, memory_write_duration, skill_execution_duration, conversation_turn_duration, knowledge_resolution_duration | **V3 视角2** |
| V3-12 | — | **pytest --cov CI 门禁不存在** | pyproject.toml 加 `[tool.pytest.ini_options]` addopts `--cov=src --cov-fail-under=80` | **V3 视角2** |
| V3-13~14 | I1-3/OS3-6 | **RLS 测试全链路为正则匹配** | 补充 integration 测试: 连接真实 PG, 设置 session var, 执行跨租户 SELECT 验证返回 0 行 | **V3 视角3** |
| INF-1 | — | **里程碑门禁覆盖率: Phase 1=29%, Phase 2=48%** | 为 47+ 个无 gate 的 done 节点补充 exit_criteria | **V3.1 基础设施** |
| INF-2 | — | **验收命令从未执行** | check_acceptance_gate.py 增加 `--execute` 模式, 调用 `_run_check()` 执行可运行命令 | **V3.1 基础设施** |
| INF-4 | — | **层边界门禁缺 memory/infra/shared 规则** | check_layer_deps.sh 补充 3 层规则 + 隐私边界 (knowledge !→ memory) | **V3.1 基础设施** |
| INF-5 | — | **full_audit.sh --phase 参数未生效** | 修复 L161: `--current` 改为 `--phase $PHASE`, CI job 增加 service 容器 | **V3.1 基础设施** |

### P2 — 改进级 (下一迭代修复)

| # | 节点 | 描述 | 来源 |
|---|------|------|------|
| 2 | D0-9 | PR 模板 + CODEOWNERS | V2 |
| 9 | OS1-6 | 前端 DOMPurify 验证 | V2 |
| 17 | MC2-6 | MemoryReceipt 字段对齐 ADR-038 | V2 |
| 25 | K3-6 | 缺 PlatformTone/RegionInsight 类型 | V2 |
| 26 | S0-1 | SkillProtocol 缺 5 扩展字段 | V2 |
| 27 | K3-3 | FK 并行一致性未测试 | V2 |
| 32 | K3-8 | Resolver ACL JSONB 验证 | V2 |
| 37 | D4-3 | 一键诊断包命名 | V2 |
| 39 | D4-5 | 轻量离线打包 | V2 |
| 40 | FW4-3 | 暗色/亮色模式 | V2 |
| 41 | FW4-4 | 键盘快捷键 | V2 |
| 42 | FA4-2 | 配额管理页 | V2 |
| 43 | FA4-3 | 备份管理页 | V2 |
| 48-51 | S4-1/S4-2/T4-1/T4-2 | 4 个 resilience 组件集成验证 | V2 |
| 52 | G4-3 | per-user 限流 | V2 |
| 56 | FW4-1 | 性能预算通过证据 | V2 |
| 57 | OS4-8 | a11y 审计执行证据 | V2 |
| V3-4 | S0-1 | SkillResult 缺 tool_calls 字段 | V3 视角1 |
| V3-11 | I2-3 | Token 计费精度无量化测试 | V3 视角2 |
| V3-15 | — | check_rls.sh 同样为正则匹配 | V3 视角3 |
| INF-3 | — | 可追溯性仅检查链接存在, 不验证内容一致 | V3.1 基础设施 |
| INF-6 | — | Phase 4 门禁为 dry-run (需在进入 Phase 4 时升级) | V3.1 基础设施 |
| INF-7 | — | Phase 0 门禁 8/10 为 `test -f` (内容不验证) | V3.1 基础设施 |

### P2-M — M-Track 改进级

| # | 节点 | 描述 | 来源 |
|---|------|------|------|
| 28 | MM0-7 | 安全管线生产代码 | V2 |
| 29 | MM1-2 | WS payload 媒体扩展 | V2 |
| 30 | MM1-4 | Brain 多模态模型选择 | V2 |
| 31 | MM1-5 | security_status 生产代码 | V2 |
| 58 | MM2-1~6 | 企业多模态生产代码 | V2 |

---

## V3 新增: Gate 脚本改进建议

当前 Gate 检测率对 P0 问题仅 0-12.5%。建议增加以下检查类型:

| 检查类型 | 实现方式 | 能发现的问题 | 优先级 |
|---------|---------|------------|--------|
| **调用图验证** | AST 分析: 函数定义但无调用方 = WARNING | NegativeFeedbackFuse 孤立, BrainSLI 5/7 未接入 | P0 |
| **跨层一致性** | 提取 Gateway RBAC 角色列表 vs Infra RBAC 角色列表, 断言相等 | RBAC 3 vs 5 不一致 | P0 |
| **Stub 检测** | AST 分析: 函数体仅 `return []` / `return False` / f-string = WARNING | ContentWriter 纯模板, vector_first 返回空 | P0 |
| **RLS 运行时验证** | 连接 PG, `SET app.current_org_id = 'A'; SELECT FROM table WHERE org_id = 'B'` 断言 0 行 | RLS policy 逻辑错误 | P1 |
| **Coverage 门禁** | `pytest --cov=src --cov-fail-under=80` | 测试覆盖率不足 | P1 |
| **LLM 调用验证** | Grep `llm.call\|llm_adapter.call` in Skill 实现, 断言非零 | Skill 不调用 LLM | P1 |

---

## 已确认的代码级证据 (14 项已知问题交叉验证)

| # | 位置 | 描述 | 状态 |
|---|------|------|------|
| 1 | `conversation.py:351` | `[-10:]` 硬编码历史 | CONFIRMED |
| 2 | `context_assembler.py:272-290` | 线性拼接, 无 U-shaped/冲突检测 | CONFIRMED |
| 3 | `pg_adapter.py:64-176` | read_personal_memories() 不调用衰减 | CONFIRMED |
| 4 | `evolution/pipeline.py:85-160` | LLM callable 从未 .call() | CONFIRMED |
| 5 | `promotion/pipeline.py:302-313` | _check_conflict() 硬编码 False | CONFIRMED |
| 6 | `receipt.py:25-42` | 字段语义与 ADR-038 不完全对齐 | PARTIAL CONFIRM |
| 7 | `resolver/resolver.py:250-279` | vector_first 返回空 | CONFIRMED |
| 8 | `resolver/resolver.py:118-152` | 无 ACL JSONB 验证 | CONFIRMED |
| 9 | `importer/changeset.py:191-196` | 直接访问 _neo4j 私有字段 | CONFIRMED |
| 10 | `content_writer.py:128-154` | 纯 f-string 模板 | CONFIRMED |
| 11 | `merchandising.py:146-183` | 硬编码规则, 注释"for now" | CONFIRMED |
| 12 | `protocol.py:56-122` | 缺 5 个扩展字段 | CONFIRMED |
| 13 | `brain/memory/feedback.py` | NegativeFeedbackFuse 孤立 | CONFIRMED |
| 14 | `entity_type.py:38-49` | 缺 PlatformTone/RegionInsight | CONFIRMED |

**交叉验证结果: 13/14 CONFIRMED, 1/14 PARTIAL CONFIRM**

---

## V3 新增: 四层断裂根因分析

```
层1: 设计文档 (docs/architecture/)
   承诺: "双SSOT隐私硬边界" "LLM驱动提取" "5角色RBAC" "Fallback链"
     ↓ 断裂1: 承诺未被任务卡 AC 精确量化
       例: 文档说"LLM驱动", AC 只写"提取成功率>=90%", 不检查"LLM调用次数>0"

层2: 任务卡 (docs/task-cards/)
   AC: "跨租户泄露=0" "P95<200ms" "覆盖率>=80%"
     ↓ 断裂2: AC 存在但 check 只验表面
       例: AC 说"P95<200ms", check 用空 stub 计时

层3: 里程碑矩阵 (milestone-matrix.yaml)
   check: "pytest tests/isolation/smoke/" → status: done
     ↓ 断裂3: check 只看 exit code, 不验逻辑深度
       例: RLS 测试 PASS = 正则匹配到了"ENABLE ROW LEVEL SECURITY"字符串

层4: Gate 脚本 (verify_phase.py)
   结果: "GO" (但实际只证明了 L1 结构完整性)
     ↓ 断裂4: Gate 无代码逻辑验证能力
       例: 8个P0问题Gate全部漏过
```

**每一层都在降级验证深度**: 设计→量化→执行→判定，信息在传递中逐步丢失。

---

## V3.1 新增: 治理基础设施系统性缺陷

V3 审计发现了代码级问题，但未审计**治理基础设施本身**。V3.1 将审计对象从"被管理的代码"扩展到"管理代码的工具链"。

### 缺陷 INF-1: 里程碑门禁覆盖率断崖

**现象:** 大量 `status: done` 的里程碑节点无任何 `exit_criteria` 覆盖。

| Phase | done 节点数 | 有 gate 覆盖 | 无 gate 覆盖 | 覆盖率 |
|-------|-----------|-------------|-------------|--------|
| Phase 1 | 28 | 8 | 20 | **29%** |
| Phase 2 | 52 | 25 | 27 | **48%** |
| Phase 3 | ~50 | 12 | ~38 | **~24%** |

**影响:** 47+ 个 "done" 里程碑的完成状态仅基于人工标记，无自动化验证。`verify_phase.py --current` 的 "GO" 判定不覆盖这些节点。

**证据:** `delivery/milestone-matrix.yaml` Phase 1 示例 — MC1-1, MC1-2, MC1-3, MC1-4, MC1-5 等均为 `status: done` 但无 `exit_criteria`。

### 缺陷 INF-2: 验收命令从未执行

**现象:** `scripts/check_acceptance_gate.py` 仅验证任务卡验收命令的**语法格式**（非空、有反引号、路径存在），从未**执行**这些命令。

**代码证据:**
- `check_acceptance_gate.py` 的 `_validate_acceptance()` 函数只做格式检查
- 对比 `verify_phase.py` 的 `_run_check()` 函数——后者实际执行命令并捕获 exit code
- 约 60% 的验收命令可直接执行（`uv run pytest ...`、`bash scripts/...`）

**影响:** 任务卡写"运行 `uv run pytest tests/unit/brain/` 全部通过"，但无人验证该命令是否真的通过。

### 缺陷 INF-3: 可追溯性仅检查链接存在

**现象:** `scripts/task_card_traceability_check.py` 仅检查任务卡中是否存在指向里程碑矩阵的**双向链接**，不验证链接指向的内容是否一致。

**证据:** 该脚本的 `scan_task_cards()` 函数用正则 `MATRIX_REF_RE` 提取引用 ID，然后与 `load_milestone_ids()` 做集合交叉——纯 ID 匹配，不检查描述、状态或验收标准是否对齐。

**影响:** 任务卡可引用已变更/已删除的里程碑 ID 而不触发任何警告。

### 缺陷 INF-4: 层边界门禁存在 3 个结构性盲区

**现象:** `scripts/check_layer_deps.sh` 仅为 5 个层定义了 import 规则。

| 层 | 有规则 | 状态 |
|----|--------|------|
| brain | Y | 已覆盖 |
| knowledge | Y | 已覆盖 |
| skill | Y | 已覆盖 |
| gateway | Y | 已覆盖 |
| tool | Y | 已覆盖 |
| **memory** | **N** | **无约束** |
| **infra** | **N** | **无约束** |
| **shared** | **N** | **无约束** |

**额外盲区:** 架构文档声称"Knowledge 层不得直接读取 Memory Core"（隐私边界），但无任何 gate 脚本或测试强制执行此规则。

**影响:** `memory/`、`infra/`、`shared/` 三个层可任意交叉导入而不触发 CI 失败。隐私边界声明为纸面承诺。

### 缺陷 INF-5: CI 与本地环境分裂

**现象:** `scripts/full_audit.sh` 的 `--phase` 参数未生效。

**证据:** `full_audit.sh:161` 固定调用 `verify_phase.py --current --json`，而 `--current` 读取 `milestone-matrix.yaml` 的 `current_phase: "phase_3"`，完全忽略外部传入的 `--phase 0`。

**连锁问题:**
- 周调度的 `full-audit` CI job 使用 `--phase 0`，但实际运行 Phase 3 检查
- 该 job 无 postgres/redis service 容器，导致需要数据库的检查全部失败
- 结果: 远程 CI `full-audit` 100% 失败率，但主流程 CI 100% 绿色——掩盖了审计 job 的配置缺陷

### 缺陷 INF-6: Phase 4 门禁为 dry-run 占位符

**现象:** Phase 4 的 5 个 exit_criteria 命令为 dry-run 模式:

| Gate ID | 命令 | 实际行为 |
|---------|------|---------|
| p4-release-drill | `drill_release.sh --dry-run` | 检查脚本存在，不执行 |
| p4-dr-restore | `drill_dr_restore.sh --dry-run` | 同上 |
| p4-ha-validation | `validate_ha.sh --dry-run` | 同上 |
| p4-diag-package | `diag_package.sh --dry-run` | 同上 |
| p4-key-rotation | `rotate_keys.sh --dry-run` | 同上 |

**合理性评估:** Phase 4 尚未进入（当前 Phase 3），dry-run 作为 Phase 3 门禁的前置检查是合理模式。但需在 Phase 4 正式进入时升级为全量执行，否则门禁将永久停留在 dry-run 级别。

### 缺陷 INF-7: Phase 0 门禁质量基线过低

**现象:** Phase 0 的 10 个 hard exit_criteria 中，8 个为 `test -f <path>`（文件存在性检查）。

**证据:**
```
p0-alembic:    test -f migrations/env.py
p0-ruff:       test -f pyproject.toml
p0-schema:     test -f docs/governance/task-card-schema-v1.0.md
p0-taskcount:  test -f scripts/count_task_cards.py
p0-milestone:  test -f delivery/milestone-matrix.yaml
p0-sbom:       test -f delivery/sbom.json
p0-xnode:      test -f docs/governance/architecture-phase-delivery-map.md
p0-ports:      test -f src/ports/base.py
```

仅 2/10 执行了实质性验证：
- `p0-layer-deps`: `bash scripts/check_layer_deps.sh --json`
- `p0-port-compat`: `bash scripts/check_port_compat.sh --json`

**影响:** Phase 0 "GO" 门禁本质上仅证明了"8 个文件存在于磁盘"，不验证内容。

---

## 审计方法论 V3.1 总结

### V3.1 与前版本的核心差异

| 维度 | V2 审计 | V3 审计 | V3.1 审计 |
|------|---------|---------|-----------|
| 审计路径 | 矩阵→代码 (单向) | 4条独立路径交叉收敛 | 4条路径 + **治理基础设施审计** |
| 验证体系审计 | 未涉及 | Gate 脚本逆向分析 | Gate + **覆盖率量化 + 执行验证** |
| 测试可信度 | 未涉及 | RLS/性能/SLI 测试验证 | 同上 + **CI 环境一致性验证** |
| 基础设施审计 | 未涉及 | 未涉及 | **7 项治理基础设施缺陷** |
| Agent 结论 | 交叉验证14项 | 全部独立再验证 | 全部再验证 + **基础设施可执行验证** |
| P0 项 | 8 项 | 8 项 (不变) | 8 项 (不变) |
| P1 项 | 17 项 | **24 项** (+7) | 24 项 + **7 项 INF** |
| P2 项 | 17 项 | **20 项** (+3) | 20 项 (不变) |

### V3.1 方法论可复现步骤

1. **视角1 — 设计文档驱动**: 读 docs/architecture/*.md → 提取功能承诺 → Grep/Read 代码验证兑现
2. **视角2 — 任务卡驱动**: 读 docs/task-cards/*.md → 提取 AC → 验证代码+测试满足
3. **视角3 — 矩阵 check 驱动**: 读 milestone-matrix.yaml done 节点 → 读 check 命令指向的测试/脚本 → 分析测试了什么
4. **视角4 — Gate 逆向**: 读 verify_phase.py → 逐行分析检查类型 → 用已知 P0 列表测试检测率
5. **视角5 — 治理基础设施审计** (V3.1 新增): 审计治理工具链本身:
   - 量化里程碑→门禁覆盖率 (每 phase 的 done/covered/uncovered 统计)
   - 验证验收命令是否被执行 (check_acceptance_gate.py 行为分析)
   - 验证可追溯性检查深度 (task_card_traceability_check.py 行为分析)
   - 验证层边界规则完整性 (check_layer_deps.sh 覆盖的层 vs 全部层)
   - 验证 CI/本地环境一致性 (full_audit.sh 参数传递 + service 容器配置)
6. **交叉比对**: 5 条路径独立完成后, 合并去重, 标注来源版本
7. **独立再验证**: 对 agent 产出的每个 claim, Read 实际代码确认 (防止 Bias 7)
8. **修正 agent 错误**: V3 修正了 3 处 agent 错误:
   - 视角2 agent 称"降级测试缺失" → 实际 `test_degradation.py` 存在且完整 (200行, 6个测试)
   - 视角2 agent 称"DR演练脚本缺失" → 实际 `drill_dr_restore.sh` 存在
   - 视角2 agent 称"性能测试全面缺失" → 实际文件存在, 但测试空 stub (更精确的描述)

---

> **文档版本:** v3.1 (治理基础设施补全版)
> **生成日期:** 2026-02-23
> **审计方法:** 四视角交叉审计 + 独立再验证 + 治理基础设施审计
> **代码快照:** main branch (commit 15c6fd8)
> **V3.1 新增:** 7 项治理基础设施缺陷 (INF-1 ~ INF-7), 第 9 种偏差类型, 第 5 条审计路径
> **配套工具:** `scripts/check_cross_validation.py` (诊断脚本, 自动化交叉验证)
> **下次审计建议:** Phase 4 门禁前 (修复 8 个 P0 + 24 个 P1 + 4 个 P1-INF 后)
