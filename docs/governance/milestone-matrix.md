# DIYU Agent 里程碑矩阵 (Milestone Matrix) -- 索引

> version: v1.0
> date: 2026-02-13
> status: Baseline
> inputs: 架构文档 v3.6 + 治理规范 v1.1 + 治理优化计划 v2.0
> scope: 全栈 12 维度 x 6 Phase + M-Track 交付矩阵（含 Observability & Security 独立维度）

## 0. 使用说明

### 0.1 本文档定位

```
架构文档 v3.6       -->  系统长什么样，每层职责是什么
里程碑矩阵(本文)     -->  每层在每个阶段交付什么，怎么验证
治理优化计划 v2.0    -->  治理能力差距分析与补全路径
治理规范 v1.1       -->  质量规则、门禁标准、审查流程
CI/CD 门禁          -->  治理规范的规则 + 里程碑矩阵的检查点
```

### 0.2 文档结构

本矩阵拆分为 3+1 结构:

| 文件 | 内容 | 维度数 |
|------|------|--------|
| **本文 (索引)** | 使用说明 + 总览矩阵 + Phase 检查清单 + 关联文档 | -- |
| [milestone-matrix-backend.md](milestone-matrix-backend.md) | Brain / Memory Core / Knowledge / Skill / Tool / Gateway / Infrastructure | 7 |
| [milestone-matrix-frontend.md](milestone-matrix-frontend.md) | FE-Web (apps/web) / FE-Admin (apps/admin) | 2 |
| [milestone-matrix-crosscutting.md](milestone-matrix-crosscutting.md) | Delivery/DevOps / Multimodal (M-Track) / Obs & Security / 跨层集成验证节点 | 3+跨层 |

### 0.3 阅读方式

- **纵向读（按列）**: 看某个 Phase 全系统需要交付什么
- **横向读（按行）**: 看某个层从 Phase 0 到 Phase 5 的演进路径
- **M-Track 读**: Multimodal 独立演进轨道 M0-M3，与 Phase 正交对齐
- **对角线读**: 看跨层集成验证节点（见 [横切文件](milestone-matrix-crosscutting.md) Section 4）

### 0.4 验收标准分级

| 标记 | 含义 | 谁来判断 |
|------|------|---------|
| [CMD] | 运行命令看输出 | 任何人 |
| [FILE] | 检查文件存在且内容合规 | 任何人 |
| [TEST] | 测试用例通过 | CI 自动判定 |
| [E2E] | 端到端场景通过 | 手动或 Playwright |
| [METRIC] | 指标达到阈值 | 监控系统 |

### 0.5 单元格 7 字段说明 (矩阵层)

每个**矩阵条目**包含以下 7 个字段（简写见表头）:

> 注: 此处 7 字段为**规划层 (矩阵)** 的格式。执行层 (任务卡) 采用双 Tier Schema (Tier-A: 10 字段, Tier-B: 8 字段)，
> 详见 `docs/governance/task-card-schema-v1.0.md`。

| 字段 | 简写 | 含义 |
|------|------|------|
| Deliverable | **D** | 交付物：具体产出什么 |
| Acceptance Criteria | **AC** | 验收标准：怎么判断做完了 |
| V-intra | **V-in** | 层内验证：本层独立可验证的检查点 |
| V-cross | **V-x** | 跨层验证：涉及其他层的集成检查点（引用 X/XF 编号） |
| V-fe-be | **V-fb** | 前后端验证：前端与后端的集成检查点（引用 XF 编号） |
| Metric | **M** | 成功指标：可量化的判定标准 |
| Dependency | **DEP** | 依赖：前置条件或依赖的其他里程碑项 |

> 当某字段不适用时标记 `--`。V-cross 和 V-fe-be 引用 [横切文件](milestone-matrix-crosscutting.md) Section 4 的跨层验证节点编号。

### 0.6 Phase 定义锚点（对齐治理规范 v1.1 Section 14）

| Phase | 主题 | 渐进式组合步骤 |
|-------|------|---------------|
| Phase 0 | 治理最小集 + 交付骨架 | Step 0: 脚手架 |
| Phase 1 | 安全与租户底座 | Step 5: Gateway (Auth/RLS) + Step 6: Infra |
| Phase 2 | 首条端到端业务闭环 | Step 1: Brain+Memory + Step 2: Tool(LLM) |
| Phase 3 | 知识与技能接入 | Step 3: Skill + Step 4: Knowledge |
| Phase 4 | 可靠性 + 可观测性 | Step 7: Deployment 产品化 |
| Phase 5 | 治理自动化闭环 | 持续运营 |

---

## 1. 总览矩阵（12 维度 x 10 轴）

> 每个单元格列出该阶段最关键的 1-3 项交付物。完整定义见各子文件的详细章节。
> Phase 0-5 为时序主轴；M0-M3 为 Multimodal 正交轴（与 Phase 对齐但独立演进）。

### 1.1 Phase 主轴 (12 x 6)

| 维度 | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|------|---------|---------|---------|---------|---------|---------|
| **Brain** | Port Stub + 空壳 | -- | 对话引擎 + 意图 + Context Assembler | 技能调度 + 角色适配 | CE 精细化 + SLO | 策略自动调优 |
| **Memory Core** | MemoryCorePort Stub | -- | CRUD + Evolution Pipeline + pgvector | Promotion Pipeline | 删除管线 + 备份恢复 | 自动 Consolidation |
| **Knowledge** | KnowledgePort Stub | -- | -- | Neo4j+Qdrant+FK+Resolver | 性能基线 + 缓存 | Capability Registry |
| **Skill** | SkillRegistry Stub | -- | -- | ContentWriter + Merchandising | 熔断 + 缓存 | A/B + 自发现 |
| **Tool** | LLMCallPort Stub | -- | LLMCall 真实实现 | WebSearch + Image/Audio | SLA 监控 | 成本治理 |
| **Gateway** | FastAPI 骨架 + CI | Auth+RLS+OrgContext | REST API + WS + 限流 | Knowledge/Skill API | SLO + HA + 多区域 | API 生命周期 |
| **Infrastructure** | Docker Compose + PG | 组织模型 + RBAC + 审计 | Redis + Event Bus + 计费 | 全栈依赖就位 | Prometheus + 故障注入 | GitOps + 合规 |
| **FE-Web** | Monorepo 骨架 | 登录 + 组织切换 | 对话主界面 + 流式 + 记忆面板 | 知识浏览 + Skill 渲染 | 性能 + a11y + 暗色模式 + 快捷键 + 充值 | 语音 |
| **FE-Admin** | Admin App 骨架 | Admin 登录 + 权限 | 用户/组织管理 | 知识管理 + 审核 | 监控 + 备份 + 配额 | 合规报告 |
| **Delivery** | manifest.yaml 骨架 + CI 硬门禁 | SBOM + 镜像扫描 | Dogfooding + 资源数据 | manifest 实值 + 安装器 | 升级回滚 + DR + 诊断包 | 离线包 + LTS |
| **Obs & Security** | 日志格式 + trace_id + SAST | RLS 隔离测试 + secret scan | 4 黄金信号 + 基础告警 | 内容安全管线 + 审计闭环 | SLI/SLO + 告警分级 + 故障注入 | 自动偏差审计 + 合规报告 |
| **Multimodal** | M0: Schema + DDL + Port | -- | -- | M1: 个人多模态 | M2: 企业多模态 | M3: 视频 + 跨模态 |

### 1.2 M-Track 正交轴 (12 x 4)

> M-Track 与 Phase 对齐关系: M0=Phase 0, M1=Phase 3, M2=Phase 4, M3=Phase 5

| 维度 | M0 (基座) | M1 (个人多模态) | M2 (企业多模态) | M3 (成熟) |
|------|-----------|----------------|----------------|-----------|
| **Brain** | -- | 多模态模型选择逻辑 | -- | AssemblyProfile 多模态 |
| **Memory Core** | -- | -- | -- | 跨模态语义索引 |
| **Knowledge** | -- | -- | media_contents 扩展 | 跨模态语义检索 |
| **Skill** | -- | -- | multimodal I/O 声明 | 视频生成 Skill |
| **Tool** | -- | Image/Audio Tool | DocumentExtract | 版权检测 Tool |
| **Gateway** | 三步上传协议 | WS media payload | Admin media API | -- |
| **Infrastructure** | ObjectStoragePort + DDL | -- | enterprise_media RLS | -- |
| **FE-Web** | -- | 文件上传 + 预览 | -- | 语音交互 |
| **FE-Admin** | -- | -- | 媒体资源管理 | -- |
| **Delivery** | 契约测试 L1-4 | -- | -- | -- |
| **Obs & Security** | 安全管线 Stage 1 | 媒体安全扫描 | NSFW 检测 + 审计 | 版权合规审计 |
| **Multimodal** | Schema + DDL + Port (8 项) | 个人媒体 6 项闭环 | 企业媒体 6 项闭环 | 成熟期 3 项 |

---

## 2. 维度详情导航

> 以下链接指向各维度的详细里程碑表（矩阵层 7 字段格式: D/AC/V-in/V-x/V-fb/M/DEP）。

### 后端 7 维度

详见 [milestone-matrix-backend.md](milestone-matrix-backend.md):

1. Brain 层 (B0-x ~ B5-x)
2. Memory Core 层 (MC0-x ~ MC5-x)
3. Knowledge 层 (K0-x ~ K5-x)
4. Skill 层 (S0-x ~ S5-x)
5. Tool 层 (T0-x ~ T5-x)
6. Gateway 层 (G0-x ~ G5-x)
7. Infrastructure 层 (I0-x ~ I5-x)

### 前端 2 维度

详见 [milestone-matrix-frontend.md](milestone-matrix-frontend.md):

1. FE-Web / apps/web (FW0-x ~ FW5-x)
2. FE-Admin / apps/admin (FA0-x ~ FA5-x)

### 横切维度 + 跨层验证

详见 [milestone-matrix-crosscutting.md](milestone-matrix-crosscutting.md):

1. Delivery/DevOps (D0-x ~ D5-x)
2. Multimodal / M-Track (MM0-x ~ MM3-x)
3. Observability & Security (OS0-x ~ OS5-x)
4. 跨层集成验证节点 (X0-x ~ X5-x, XF2-x ~ XF4-x, XM0-x ~ XM3-x)

---

## 3. 规划层与执行层的关系

### 3.1 两层分离

```
规划层 (本矩阵)          执行层 (任务卡)
  12 维度 x 6 Phase         当前 Phase 的聚焦任务
  一次性完整                 按阶段逐步激活
  7 字段: D/AC/V-in/...     双 Tier: Tier-A 10 字段 / Tier-B 8 字段
  ID 如 B0-1, MC2-3         ID 如 TASK-P0-001
  颗粒度: 交付物             颗粒度: 可独立执行的工作单元
```

规划层定义"做什么、怎么验证"，执行层定义"怎么做、出问题怎么退"。
每个任务卡关联一个或多个矩阵条目 ID。

### 3.2 任务执行卡模板（双 Tier Schema）

> 完整 Schema 规范: `docs/governance/task-card-schema-v1.0.md`
> 校验脚本: `scripts/check_task_schema.py`

激活新 Phase 时，从矩阵条目展开为任务卡。每张卡必须独立可验证、可回滚、向后兼容。
任务卡分为 Tier-A (10 字段, Phase 2+/跨层/Port) 和 Tier-B (8 字段, Phase 0-1/纯新增)。

**共用字段 (Tier-A + Tier-B):**

| 字段 | 说明 | 示例 |
|------|------|------|
| **目标** | 可验证的结果状态 | "Memory Core Port 完整契约定义完成，mypy --strict 通过" |
| **范围 (In Scope)** | 改哪些目录/模块 | `src/ports/`, `tests/unit/ports/` |
| **范围外 (Out of Scope)** | 明确不做什么 | "Adapter 实现 / 前端集成 / 性能调优" |
| **依赖** | 前置任务 ID | TASK-MC0-1, 或 `--` |
| **兼容策略** | API/Schema 是否向后兼容 | "新增接口，无破坏性变更" |
| **验收命令** | 可直接运行的命令 + 期望输出。标签: `[ENV-DEP]` / `[MANUAL-VERIFY]` / `[E2E]` (见治理优化计划 Section 8.6-8.7) | `mypy --strict src/ports/ && pytest tests/unit/ports/ -v` |
| **回滚方案** | 失败后如何撤回 | `git revert <commit>`, 无 DDL 变更无需额外回滚 |
| **证据** | CI 链接 / 测试报告 / 产物路径 | `evidence/phase-0/verify-phase-0-{sha}.json` |

**Tier-A 额外字段:**

| 字段 | 说明 | 示例 |
|------|------|------|
| **风险** | 依赖/数据/兼容/回滚四类 | "依赖: MC0-1 未就绪 / 数据: N/A / 兼容: 新增接口 / 回滚: git revert" |
| **决策记录** | 关键取舍 + 理由 + 来源 | "决策: Expand-Contract / 理由: 灰度演进 / 来源: ADR-033" |

> 矩阵条目的 D/AC/V-in/V-x/V-fb/M/DEP 自动继承到任务卡，无需重复填写。
> 任务卡模板用于实际执行时填写，不修改矩阵子文件。
> Tier 判定规则见 `task-card-schema-v1.0.md` Section 1.1。

### 3.3 Phase 聚焦维度表

> 一人公司线性推进指引：当前 Phase 只需关注"聚焦"列的维度任务卡，"活跃"列维度有增量时才处理，"休眠"列暂不涉及。

| Phase | 聚焦维度 | 活跃维度 | 休眠维度 |
|-------|---------|---------|---------|
| Phase 0 | Gateway(骨架), Infrastructure(Docker/PG), Delivery(manifest) | Brain/MC/Knowledge/Skill/Tool(仅 Port Stub), FE-Web/FE-Admin(骨架) | Obs & Security(日志格式除外), Multimodal(仅 Schema) |
| Phase 1 | Infrastructure(Org/RBAC/审计), Gateway(Auth/RLS/OrgContext) | Obs & Security(RLS 隔离测试), FE-Web(登录), Delivery(SBOM) | Brain, MC, Knowledge, Skill, Tool, Multimodal |
| Phase 2 | Brain, Memory Core, Tool(LLMCall) | Gateway(REST/WS), FE-Web(对话界面), Obs(4 黄金信号) | Knowledge, Skill, FE-Admin(基础管理), Multimodal |
| Phase 3 | Knowledge, Skill | Brain(技能调度), Gateway(Knowledge/Skill API), FE-Web(知识/Skill), FE-Admin(知识管理), Delivery(安装器), Obs(内容安全) | Multimodal(M1 启动) |
| Phase 4 | Obs & Security(SLI/SLO/故障注入), Delivery(升级回滚/DR) | All(稳定性加固), Multimodal(M2) | -- |
| Phase 5 | Delivery(离线包/LTS), Obs(合规) | All(自动化治理), Multimodal(M3) | -- |

---

## 4. 每 Phase 完成度检查清单

### Phase 0 检查清单

```bash
make verify-phase-0
```

期望输出:

```
[PASS] pyproject.toml 存在且 uv sync 成功
[PASS] Docker Compose 全栈可启动 (PG/Neo4j/Qdrant/Redis/MinIO)
[PASS] ruff check + mypy --strict 通过
[PASS] src/ports/ 至少 6 个 Port 定义 (Memory/Knowledge/LLM/Skill/OrgContext/Storage)
[PASS] 所有 Port 有 Stub 实现且 pytest 通过
[PASS] Makefile 含 dev/test/lint/typecheck/migrate 命令
[PASS] .github/workflows/ci.yml 存在且含硬门禁
[PASS] 4 个 Guard 脚本可执行
[PASS] delivery/manifest.yaml + milestone-matrix.schema.yaml 存在
[PASS] 前端 Monorepo 基础文件存在 (pnpm-workspace/turbo.json/package.json)
[PASS] 前端 pnpm build 通过
[PASS] secret scanning + SAST + 依赖扫描 CI 集成 (OS0-3/4/5)
[PASS] 日志格式含 trace_id/org_id/request_id (OS0-1)

Phase 0 完成度: 13/13 (100%)
```

### Phase 1 检查清单

```bash
make verify-phase-1
```

期望输出:

```
[PASS] organizations/users/org_members 表存在
[PASS] OrgContext 中间件链路可运行
[PASS] RLS 策略已启用且隔离测试通过
[PASS] RBAC 权限检查通过
[PASS] audit_events 表存在且可写入
[PASS] tests/isolation/smoke/ 在 CI 中通过
[PASS] 前端登录 -> 组织切换闭环可运行
[PASS] SBOM 生成成功
[PASS] RLS 隔离测试正向+反向通过 (OS1-1)
[PASS] JWT 安全 (过期/轮换/revocation) 通过 (OS1-4)

Phase 1 完成度: 10/10 (100%)
```

### Phase 2 检查清单

```bash
make verify-phase-2
```

期望输出:

```
[PASS] API/WS -> Brain -> Memory Core -> LLMCall 闭环通过
[PASS] Memory Core CRUD + Evolution Pipeline 通过
[PASS] pgvector Hybrid Retrieval + RRF 通过
[PASS] 对话场景端到端 smoke 通过
[PASS] 前端对话界面可流式收发消息
[PASS] Token 预算 Pre-check 通过
[PASS] OpenAPI 类型同步无漂移
[PASS] 4 黄金信号指标在 Prometheus 中有数据 (OS2-1)
[PASS] 前端错误边界 + 错误上报可用 (OS2-5)

Phase 2 完成度: 9/9 (100%)
```

### Phase 3 检查清单

```bash
make verify-phase-3
```

期望输出:

```
[PASS] Knowledge Write API (Neo4j + Qdrant + FK) 链路通过
[PASS] 至少 1 个 Skill 端到端可触发并有回执
[PASS] Resolver 按 Profile 查询返回 KnowledgeBundle
[PASS] 前端对话触发 Skill 并渲染 Artifact
[PASS] delivery/manifest.yaml TBD 核心项回填完成
[PASS] 前后端知识相关契约测试通过
[PASS] 安装器可在全新服务器部署
[PASS] 内容安全管线 security_status 6 态安全检查子集可用 (OS3-1, ADR-051)
[PASS] 审计闭环: 关键操作 100% 有审计记录 (OS3-2)
[PASS] 租户隔离 runtime: 跨 org 查询阻断 100% (OS3-6)
[PASS] SBOM attestation 签名验证 (D3-5, soft)
[PASS] env vars 完整性检查通过

Phase 3 完成度: 12/12 (100%)
```

### Phase 4 检查清单

```bash
make verify-phase-4
```

期望输出 (29 hard + 0 soft, 12 X-nodes bound):

```
  [HARD]
    [PASS] p4-coverage: Test coverage >= 80%
    [PASS] p4-fe-build: Full frontend build passes
    [PASS] p4-lighthouse: Lighthouse CI performance budget (LCP<2.5s/FID<100ms/CLS<0.1/200KB) [XF4-1]
    [PASS] p4-a11y: Zero critical a11y violations (axe-core)
    [PASS] p4-trace-e2e: Full-chain trace_id propagation E2E [X4-1]
    [PASS] p4-ssot-drift: Triple SSOT consistency check [X4-3]
    [PASS] p4-delete-e2e: Delete pipeline E2E [X4-4]
    [PASS] p4-fault-injection: Fault injection + recovery [X4-6]
    [PASS] p4-billing-e2e: Billing flow E2E [XF4-1]
    [PASS] p4-memory-privacy-e2e: Memory privacy E2E [XF4-3]
    [PASS] p4-release-drill: Upgrade/rollback drill [X4-2]
    [PASS] p4-dr-restore: Backup restore drill
    [PASS] p4-dependency-chaos: Dependency chaos testing (CB-4)
    [PASS] p4-incident-readiness: Incident management readiness
    [PASS] p4-alert-routing: Alert routing validation
    [PASS] p4-compliance-artifacts: Compliance artifacts complete
    [PASS] p4-slo-metrics: SLI/SLO metrics + alerts operational [X4-5]
    [PASS] p4-slo-burn-rate: SLO burn-rate alert rules configured
    [PASS] p4-monitoring-dashboard: Admin monitoring dashboard E2E [XF4-2]
    [PASS] p4-xnode-coverage: XNode result coverage >= 90%
    [PASS] p4-pentest-report: Pentest OWASP Top 10 zero Critical/High [X4-7]
    [PASS] p4-sbom-attestation: SBOM cosign attestation (hard)
    [PASS] p4-perf-baseline: Performance baseline (Assembler/Graph/Vector P95)
    [PASS] p4-ha-validation: HA failover validation (<30s recovery)
    [PASS] p4-diag-package: One-click diagnostic package
    [PASS] p4-key-rotation: Key rotation + cert management
    [PASS] p4-enterprise-media: Enterprise media dual-write + FK [XM2-1]
    [PASS] p4-media-safety: Enterprise media NSFW + copyright precheck [XM2-2]
    [PASS] p4-postmortem-capa: Postmortem template + CAPA register

  Hard: 29/29 passed
  Soft: 0/0 passed
  XNode result coverage: 12/12 (100%) >= 90% threshold
  Go/No-Go: GO

Phase 4 完成度: 29/29 (100%)
```

### Phase 5 检查清单

```bash
make verify-phase-5
```

期望输出:

```
[PASS] Guard 自动阻断策略已启用
[PASS] 三 SSOT 自动一致性检查已启用
[PASS] Exception Register 有效期自动审计在运行
[PASS] 月度架构偏差审计模板可产出报告
[PASS] Capability Registry 统一注册可查询
[PASS] Guard 自动阻断 + 人话化输出可用 (OS5-2)
[PASS] GDPR/PIPL 合规报告可自动生成 (OS5-5)

Phase 5 完成度: 7/7 (100%)
```

---

## 5. 任务卡集导航

> 任务卡集按架构文档为单位组织，采用双 Tier Schema: Tier-A 10 必填字段 / Tier-B 8 必填字段（详见 `task-card-schema-v1.0.md`）。
> 规划层（本矩阵）定义"做什么、怎么验证"，执行层（任务卡）定义"怎么做、出问题怎么退"。

### 后端任务卡

| 文件夹 | 任务卡文件 | 覆盖维度 | 条目数 |
|--------|-----------|---------|--------|
| `docs/task-cards/01-对话Agent层-Brain/` | [brain.md](../task-cards/01-对话Agent层-Brain/brain.md) | Brain (B0-B5) | 24 |
| | [memory-core.md](../task-cards/01-对话Agent层-Brain/memory-core.md) | Memory Core (MC0-MC5) | 18 |
| `docs/task-cards/02-Knowledge层/` | [knowledge.md](../task-cards/02-Knowledge层/knowledge.md) | Knowledge (K0-K5) | 15 |
| `docs/task-cards/03-Skill层/` | [skill.md](../task-cards/03-Skill层/skill.md) | Skill (S0-S5) | 10 |
| `docs/task-cards/04-Tool层/` | [tool.md](../task-cards/04-Tool层/tool.md) | Tool (T0-T5) | 15 |
| `docs/task-cards/05-Gateway层/` | [gateway.md](../task-cards/05-Gateway层/gateway.md) | Gateway (G0-G5) | 24 |
| `docs/task-cards/06-基础设施层/` | [infrastructure.md](../task-cards/06-基础设施层/infrastructure.md) | Infrastructure (I0-I5) | 31 |

### 横切任务卡

| 文件夹 | 任务卡文件 | 覆盖维度 | 条目数 |
|--------|-----------|---------|--------|
| `docs/task-cards/07-部署与安全/` | [delivery.md](../task-cards/07-部署与安全/delivery.md) | Delivery/DevOps (D0-D5) | 32 |
| | [obs-security.md](../task-cards/07-部署与安全/obs-security.md) | Obs & Security (OS0-OS5) | 39 |

### 前端任务卡

| 文件夹 | 覆盖内容 |
|--------|---------|
| `docs/task-cards/frontend/01-monorepo-infrastructure/` | Monorepo 骨架 (FW0, FA0) |
| `docs/task-cards/frontend/02-transport-layer/` | WebSocket + OpenAPI 同步 |
| `docs/task-cards/frontend/03-auth-permission/` | 认证权限 (FW1, FA1) |
| `docs/task-cards/frontend/04-dialog-engine/` | 对话主界面 (FW2, FW3 Artifact) |
| `docs/task-cards/frontend/05-page-routes/` | 知识/商品/充值/语音页面 |
| `docs/task-cards/frontend/06-admin-console/` | 管理后台全部 (FA2-FA5) |
| `docs/task-cards/frontend/07-deployment/` | 前端部署产品化 |
| `docs/task-cards/frontend/08-quality-engineering/` | 质量工具链 + 性能 + a11y |

### Multimodal (M-Track) 分布

> Multimodal 无独立文件夹，以 `[M-Track]` 标记嵌入各层任务卡:
> - M0 基座: Infrastructure (I3-3/I3-4), Gateway (G2-6), Delivery (契约测试)
> - M1 个人: Tool (T3-2/T3-3), 前端对话引擎 (FW2-6), 前端页面路由 (FW5-1)
> - M2 企业: Skill (S5-2), Knowledge (K3 相关)
> - M3 成熟: Tool (T5-2), Knowledge (K5-2), Obs & Security (MM3-1)

---

## 6. 关联文档

| 文档 | 关系 |
|------|------|
| `docs/architecture/00-系统定位与架构总览.md` v3.6 | 架构定义来源 |
| `docs/reviews/治理规范.v1.1-正文.md` | 治理规则来源 |
| `docs/reviews/治理规范.v1.1-Vibe执行附录.md` | 执行指南来源 |
| `docs/governance/governance-optimization-plan.md` v2.0 | 治理优化计划来源 |
| `docs/governance/milestone-matrix-backend.md` | 后端 7 维度详细里程碑 |
| `docs/governance/milestone-matrix-frontend.md` | 前端 2 维度详细里程碑 |
| `docs/governance/milestone-matrix-crosscutting.md` | 横切维度 + 跨层验证详细里程碑 |
| `docs/task-cards/` | 执行层任务卡集（按架构文档组织） |
| `docs/frontend/README.md` | 前端架构索引 |
| `docs/frontend/08-quality-engineering.md` | 前端质量标准来源 |
| `docs/frontend/07-deployment.md` | 前端部署策略来源 |

---

> **文档版本:** v1.1
> **维护规则:** 架构文档或治理规范变更时，同步更新对应子文件的里程碑条目。每个 Phase 完成后，更新对应列的实际交付状态。
