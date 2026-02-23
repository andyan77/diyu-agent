# 架构文档 - Phase 交付物映射表

> **版本:** v1.0
> **生成日期:** 2026-02-23
> **状态:** Baseline
> **数据来源:**
> - L1 架构文档: `docs/architecture/00~08` + `docs/frontend/00~08`
> - L2 里程碑矩阵: `docs/governance/milestone-matrix*.md`
> - L3 任务卡: `docs/task-cards/**/*.md`

---

## 表 1: 架构文档 → 里程碑维度 → 任务卡 总览

| 架构文档 | 层级 | 里程碑维度 (节点前缀) | 任务卡文件 | 任务卡数 |
|---------|------|---------------------|-----------|---------|
| `architecture/00-系统定位与架构总览.md` | 全局跨层 | 所有维度 (总纲) | — (为所有维度提供设计约束) | 0 |
| `architecture/01-对话Agent层-Brain.md` | Brain + MemoryCore | Brain (B), MemoryCore (MC) | `task-cards/01-对话Agent层-Brain/brain.md` | 24 |
| *(同上)* | *(同上)* | *(同上)* | `task-cards/01-对话Agent层-Brain/memory-core.md` | 18 |
| `architecture/02-Knowledge层.md` | Knowledge | Knowledge (K) | `task-cards/02-Knowledge层/knowledge.md` | 15 |
| `architecture/03-Skill层.md` | Skill | Skill (S) | `task-cards/03-Skill层/skill.md` | 10 |
| `architecture/04-Tool层.md` | Tool | Tool (T) | `task-cards/04-Tool层/tool.md` | 15 |
| `architecture/05-Gateway层.md` | Gateway | Gateway (G) | `task-cards/05-Gateway层/gateway.md` | 25 |
| `architecture/05a-API-Contract.md` | Gateway (补充) | Gateway (G) | *(同上，共用)* | — |
| `architecture/06-基础设施层.md` | Infrastructure | Infrastructure (I) | `task-cards/06-基础设施层/infrastructure.md` | 30 |
| `architecture/07-部署与安全.md` | 部署/安全 (跨层) | Delivery (D), Obs&Sec (OS) | `task-cards/07-部署与安全/delivery.md` | 33 |
| *(同上)* | *(同上)* | *(同上)* | `task-cards/07-部署与安全/obs-security.md` | 39 |
| `architecture/08-附录.md` | 跨层参考 | — | — (ADR/术语表/契约索引) | 0 |
| `frontend/00-architecture-overview.md` | 前端全局 | FE-Web (FW), FE-Admin (FA) | *(8个前端任务卡文件总纲)* | 0 |
| `frontend/01-monorepo-infrastructure.md` | 前端基础设施 | FW0, FA0 | `task-cards/frontend/01-monorepo-infrastructure/task-cards.md` | 8 |
| `frontend/02-transport-layer.md` | 前端传输层 | FW2 (WS/SSE) | `task-cards/frontend/02-transport-layer/task-cards.md` | 3 |
| `frontend/03-auth-permission.md` | 前端认证权限 | FW1, FA1 | `task-cards/frontend/03-auth-permission/task-cards.md` | 6 |
| `frontend/04-dialog-engine.md` | 前端对话引擎 | FW2, FW3 | `task-cards/frontend/04-dialog-engine/task-cards.md` | 7 |
| `frontend/05-page-routes.md` | 前端页面路由 | FW3, FW4, FW5 | `task-cards/frontend/05-page-routes/task-cards.md` | 6+1closed |
| `frontend/06-admin-console.md` | 管理后台 | FA2, FA3, FA4, FA5 | `task-cards/frontend/06-admin-console/task-cards.md` | 11 |
| `frontend/07-deployment.md` | 前端部署 | D2-FE, DEPLOY-FE | `task-cards/frontend/07-deployment/task-cards.md` | 4 |
| `frontend/08-quality-engineering.md` | 前端质量工程 | FW0, FW4 | `task-cards/frontend/08-quality-engineering/task-cards.md` | 5 |
| — (跨层集成，无独立架构文档) | 跨层验证 | X, XF, XM | `task-cards/00-跨层集成/phase-{2,3,4}-integration.md` | 16 |
| — (多模态，跨层) | M-Track | MM | `task-cards/08-多模态/multimodal.md` | 6 |

**后端任务卡合计:** 231 | **前端任务卡合计:** 48+1closed | **总计:** 279+16(跨层)=295

---

## 表 2: 按 Phase 分解的交付规格表

### Phase 0 — Skeleton & Port Definition

**目标:** 6层骨架 + Day-1 Port接口 + CI硬门禁 + 开发环境 + 前端Monorepo

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| **00 §12.3 Day-1 Port** | — | — | *设计约束: 6个Day-1 Port接口定义* |
| 01 §6 Ports & Adapters | B0-1 | TASK-B0-1 | Brain 模块骨架 `src/brain/__init__.py` |
| 01 §6 | B0-2 | TASK-B0-2 | Brain 层 Port 接口引用 (MemoryCorePort, LLMCallPort 等) |
| 01 §2.1 | B0-3 | TASK-B0-3 | 对话引擎空壳 `src/brain/engine/conversation.py` |
| 01 §3.1 | MC0-1 | TASK-MC0-1 | MemoryCorePort 完整接口定义 |
| 01 §3.1 | MC0-2 | TASK-MC0-2 | MemoryCorePort Stub 实现 (SQLite 内存) |
| 01 §3.1 | MC0-3 | TASK-MC0-3 | MemoryItem v1 Schema |
| 02 §1 | K0-1 | TASK-K0-1 | KnowledgePort 接口定义 |
| 02 §1 | K0-2 | TASK-K0-2 | KnowledgePort Stub (返回空 KnowledgeBundle) |
| 02 §5.4 | K0-3 | TASK-K0-3 | KnowledgeBundle v1 Schema |
| 03 §2 | S0-1 | TASK-S0-1 | SkillProtocol 基类 |
| 03 §2 | S0-2 | TASK-S0-2 | SkillRegistry Stub (空注册表) |
| 04 §2 | T0-1 | TASK-T0-1 | LLMCallPort 接口定义 |
| 04 §2 | T0-2 | TASK-T0-2 | LLMCallPort Stub (返回固定文本) |
| 04 §2 | T0-3 | TASK-T0-3 | ToolProtocol 基类 |
| 04 §2 (M-Track M0) | MM0-6 | TASK-T0-4 | LLMCallPort content_parts 可选参数 Expand (ADR-046) |
| 05 §1 | G0-1 | TASK-G0-1 | FastAPI + Uvicorn 最小运行 |
| 05 §1 | G0-2 | TASK-G0-2 | OpenAPI spec 自动生成 |
| 05 §1 | G0-3 | TASK-G0-3 | 请求日志中间件 (trace_id + request_id) |
| 06 §8-9 | I0-1 | TASK-I0-1 | Docker Compose 全栈环境 |
| 06 §8 | I0-2 | TASK-I0-2 | pyproject.toml + uv.lock |
| 06 §9 | I0-3 | TASK-I0-3 | Alembic Migration 骨架 |
| 06 §8 | I0-4 | TASK-I0-4 | Makefile 标准命令 |
| 06 §8 | I0-5 | TASK-I0-5 | .env.example |
| 06 §8 | I0-6 | TASK-I0-6 | ruff + mypy --strict 配置 |
| 06 §9 (M-Track M0) | MM0-1 | TASK-I0-7 | ContentBlock Schema v1.1 + JSON Schema 验证 (ADR-043) |
| 06 §9 (M-Track M0) | MM0-3 | TASK-I0-8 | personal/enterprise_media_objects DDL + RLS |
| 07 §1 | D0-1 | TASK-D0-1 | delivery/manifest.yaml 骨架 |
| 07 §1 | D0-2 | TASK-D0-2 | milestone-matrix.schema.yaml |
| 07 §1 | D0-3 | TASK-D0-3 | preflight.sh 雏形 |
| 07 §1 | D0-4 | TASK-D0-4 | .github/workflows/ci.yml 硬门禁 |
| 07 §1 | D0-5 | TASK-D0-5 | check_layer_deps.sh |
| 07 §1 | D0-6 | TASK-D0-6 | check_port_compat.sh |
| 07 §1 | D0-7 | TASK-D0-7 | check_migration.sh |
| 07 §1 | D0-8 | TASK-D0-8 | change_impact_router.sh |
| 07 §1 | D0-9 | TASK-D0-9 | PR 模板 + CODEOWNERS + commit lint |
| 07 §1 | D0-10 | TASK-D0-10 | make verify-phase-0 |
| 07 §5 | OS0-1 | TASK-OS0-1 | 统一日志格式 (JSON with trace_id/org_id/request_id) |
| 07 §5 | OS0-2 | TASK-OS0-2 | ruff + mypy --strict CI 集成 |
| 07 §5 | OS0-3 | TASK-OS0-3 | secret scanning (gitleaks/trufflehog) |
| 07 §5 | OS0-4 | TASK-OS0-4 | SAST 基础扫描 (Bandit/Semgrep) |
| 07 §5 | OS0-5 | TASK-OS0-5 | 依赖漏洞扫描 (safety/pip-audit) |
| 07 §5 | OS0-6 | TASK-OS0-6 | 前端 ESLint security rules + pnpm audit |
| 07 §5 (M-Track M0) | MM0-7 | TASK-OS0-7 | 安全管线 Stage 1 同步预检 |
| 07 §5 (M-Track M0) | MM0-8 | TASK-OS0-8 | 契约测试 Layer 1-4 全量新增条目 |
| FE-01 §1-2 | FW0-1 | TASK-FW0-1 | Next.js 15 + TypeScript strict + Tailwind |
| FE-01 §2 | FW0-2 | TASK-FW0-2 | Turborepo + pnpm workspace |
| FE-01 §2 | FW0-3 | TASK-FW0-3 | packages/ui (Button/Input/Card + Storybook) |
| FE-01 §2 | FW0-4 | TASK-FW0-4 | packages/api-client (Axios 封装 + 类型) |
| FE-01 §2 | FW0-5 | TASK-FW0-5 | packages/shared (常量/工具函数/类型) |
| FE-08 §1-2 | FW0-6 | TASK-FW0-6 | ESLint + Prettier + eslint-plugin-jsx-a11y |
| FE-08 §1 | FW0-7 | TASK-FW0-7 | Vitest 配置 |
| FE-08 §1 | FW0-8 | TASK-FW0-8 | Playwright E2E 基础设施配置 |
| FE-06 §1 | FA0-1 | TASK-FA0-1 | Next.js Admin App 独立构建 |
| FE-06 §1 | FA0-2 | TASK-FA0-2 | Admin Layout (侧边栏 + 面包屑) |
| FE-06 §1 | FA0-3 | TASK-FA0-3 | TierGate — 非 Admin 角色重定向 |

**Phase 0 跨层验证节点:**

| 验证节点 | 参与层 | 验证场景 |
|---------|-------|---------|
| X0-1 | All Ports | 所有 Port Stub 可独立实例化 |
| X0-2 | Delivery + CI | CI 硬门禁完整运行 |
| X0-3 | Infra + Gateway | Docker Compose 全栈启动 |
| X0-4 | Obs + CI | 安全扫描三件套 CI 集成 |
| X0-5 | Obs + Gateway | 日志格式标准化验证 |
| XM0-1 | Multimodal + Ports | M0 契约测试全量通过 |

---

### Phase 1 — Security & Tenant Foundation

**目标:** JWT认证 + OrgContext + RLS隔离 + RBAC + 审计基线 + 前端Auth

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| 05 §3 认证鉴权 | G1-1 | TASK-G1-1 | JWT 认证中间件 |
| 05 §4 OrgContext | G1-2 | TASK-G1-2 | OrgContext 中间件完整链路 |
| 05 §4 | G1-3 | TASK-G1-3 | RBAC 权限检查 |
| 05 §3 | G1-4 | TASK-G1-4 | RLS 策略基线 |
| 05 §4.1 ADR-029 | G1-5 | TASK-G1-5 | API 分区规则 |
| 07 §5 | G1-6 | TASK-G1-6 | 安全头配置 |
| 06 §1.1-1.3 | I1-1 | TASK-I1-1 | organizations + users + org_members DDL + Migration |
| 06 §1.5-1.6 | I1-2 | TASK-I1-2 | org_settings 继承链 (is_locked BRIDGE) |
| 06 §1 + 07 §2 | I1-3 | TASK-I1-3 | RLS 策略基线 (所有业务表) |
| 06 §1.4 | I1-4 | TASK-I1-4 | RBAC 权限检查骨架 (11列 + 权限码映射) |
| 06 §4 | I1-5 | TASK-I1-5 | audit_events 表 + 审计写入 |
| 06 §6 | I1-6 | TASK-I1-6 | event_outbox 表 + Outbox Pattern |
| 07 §5 | I1-7 | TASK-I1-7 | secret scanning + SAST + 依赖漏洞扫描 |
| 07 §5.1 | OS1-1 | TASK-OS1-1 | RLS 隔离测试框架 (tests/isolation/) |
| 07 §5.1 | OS1-2 | TASK-OS1-2 | 隔离 smoke 测试 CI 硬门禁 |
| 06 §4 | OS1-3 | TASK-OS1-3 | audit_events 写入 + 查询基线 |
| 05 §3 | OS1-4 | TASK-OS1-4 | JWT 安全 (过期/轮换/revocation) |
| 07 §5 | OS1-5 | TASK-OS1-5 | CORS + 安全头 (HSTS/CSP/X-Content-Type-Options) |
| FE-08 §2 | OS1-6 | TASK-OS1-6 | 前端 XSS 防护 (DOMPurify + CSP) |
| 07 §1 | D1-1 | TASK-D1-1 | 镜像安全扫描 (CI 软门禁) |
| 07 §1 | D1-2 | TASK-D1-2 | SBOM 生成 |
| 07 §1 | D1-3 | TASK-D1-3 | make verify-phase-1 |
| FE-03 §1 | FW1-1 | TASK-FW1-1 | 登录页 /login |
| FE-03 §1 | FW1-2 | TASK-FW1-2 | AuthProvider + PermissionGate |
| FE-03 §1 | FW1-3 | TASK-FW1-3 | 组织切换器 |
| FE-03 §1 | FW1-4 | TASK-FW1-4 | SaaS/Private 双模式 Token 管理 |
| FE-03 §1 | FA1-1 | TASK-FA1-1 | Admin 登录 (含 2FA 预留) |
| FE-03 §1 | FA1-2 | TASK-FA1-2 | 权限矩阵管理 |

**Phase 1 跨层验证节点:**

| 验证节点 | 参与层 | 验证场景 |
|---------|-------|---------|
| X1-1 | Gateway + Infra | JWT -> OrgContext -> RLS 完整链路 |
| X1-2 | Gateway + Infra | RBAC 权限链 |
| X1-3 | Infra + Delivery | 隔离测试 CI 运行 |
| X1-4 | Obs + Gateway + Infra | 审计写入完整链路 |
| X1-5 | Obs + FE-Web | 前端安全防护验证 |

---

### Phase 2 — Core Conversation Loop

**目标:** 对话引擎 + Memory写入 + LLM调用 + Token计费 + WebSocket + 前端对话界面 + 管理后台基础

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| 01 §2.1 | B2-1 | TASK-B2-1 | 对话引擎完整实现 |
| 01 §2.2 | B2-2 | TASK-B2-2 | 意图理解模块 |
| 01 §4.1 | B2-3 | TASK-B2-3 | Context Assembler v1 |
| 01 §4.1-4.4 | B2-4 | TASK-B2-4 | Context Assembler CE 增强 (Query Rewriting + RRF) |
| 01 §2.3 | B2-5 | TASK-B2-5 | Memory 写入管线 (Observer -> Analyzer -> Evolver) |
| 01 §2.3 | B2-6 | TASK-B2-6 | injection_receipt + retrieval_receipt 写入 |
| 01 §2.1 | B2-7 | TASK-B2-7 | 优雅降级 — Knowledge 不可用时仍能对话 |
| 01 §2.1 + 05 §7 | B2-8 | TASK-B2-8 | WebSocket 实时对话集成 |
| 01 §3.1 | MC2-1 | TASK-MC2-1 | PG 真实实现替换 Stub |
| 01 §3.1 | MC2-2 | TASK-MC2-2 | conversation_events 表 CRUD |
| 01 §3.1 | MC2-3 | TASK-MC2-3 | memory_items 表 CRUD + versioned |
| 01 §3.2 | MC2-4 | TASK-MC2-4 | pgvector 语义检索 (ADR-042) |
| 01 §2.3 | MC2-5 | TASK-MC2-5 | Evolution Pipeline (Observer -> Analyzer -> Evolver) |
| 01 §3.1 | MC2-6 | TASK-MC2-6 | injection_receipt / retrieval_receipt 写入 |
| 01 §3.1 | MC2-7 | TASK-MC2-7 | confidence_effective 衰减计算 |
| 04 §3 | T2-1 | TASK-T2-1 | LLMCallPort -> LLM Gateway 真实实现 |
| 04 §3 + 05 §5.2 | T2-2 | TASK-T2-2 | Model Registry + Fallback |
| 04 §5 + 06 §3 | T2-3 | TASK-T2-3 | Token 计量写入 llm_usage_records |
| 05a §1.1 | G2-1 | TASK-G2-1 | 对话 REST API |
| 05 §7 | G2-2 | TASK-G2-2 | WebSocket 实时对话 |
| 05 §5 | G2-3 | TASK-G2-3 | LLM Gateway (LiteLLM 集成) |
| 05 §6.2 | G2-4 | TASK-G2-4 | Token 预算 Pre-check (Loop D Phase 1) |
| 05 §6.1 | G2-5 | TASK-G2-5 | 限流中间件 |
| 05 §8 (M-Track M0) | G2-6 | TASK-G2-6 | 三步文件上传协议 (ADR-045) |
| 05a §5 | G2-7 | TASK-G2-7 | SSE 通知端点 /events/* |
| 06 §8 | I2-1 | TASK-I2-1 | Redis 缓存 + Session 管理 |
| 06 §6 | I2-2 | TASK-I2-2 | Celery Worker + Redis Broker |
| 06 §3 | I2-3 | TASK-I2-3 | Token Billing 最小闭环 |
| 06 §9 | I2-4 | TASK-I2-4 | conversation_events 表 |
| 06 §9 | I2-5 | TASK-I2-5 | memory_items 表 (含 embedding + last_validated_at) |
| 07 §5 | OS2-1 | TASK-OS2-1 | 4 黄金信号埋点 (latency/traffic/errors/saturation) |
| 07 §5 | OS2-2 | TASK-OS2-2 | 基础告警规则 (error rate > 1%, P95 > 2s) |
| 06 §3 | OS2-3 | TASK-OS2-3 | Token 消耗异常告警 |
| 07 §5 | OS2-4 | TASK-OS2-4 | 结构化错误日志 (error_code + stack_trace) |
| FE-08 §2 | OS2-5 | TASK-OS2-5 | 前端错误边界 + Sentry/等效方案 |
| FE-07 §2 | D2-1 | TASK-D2-1 | 前端 CI (pnpm lint + typecheck + test + a11y) |
| FE-07 §2 | D2-2 | TASK-D2-2 | OpenAPI 类型同步检查 (CI 硬门禁) |
| 07 §1 | D2-3 | TASK-D2-3 | 内部 dogfooding 环境 |
| 06 §3 | D2-4 | TASK-D2-4 | 资源消耗数据记录 |
| 07 §1 | D2-5 | TASK-D2-5 | make verify-phase-2 |
| FE-04 §1 | FW2-1 | TASK-FW2-1 | 对话界面 /chat 双栏布局 |
| FE-04 §1 | FW2-2 | TASK-FW2-2 | 流式消息渲染 (SSE/WS) |
| FE-04 §1 | FW2-3 | TASK-FW2-3 | 对话历史管理 |
| FE-04 §1 | FW2-4 | TASK-FW2-4 | 记忆面板 (Memory Context Panel) |
| FE-04 §1 | FW2-5 | TASK-FW2-5 | 消息操作 (复制/重试/反馈) |
| FE-04 §1 (M-Track) | FW2-6 | TASK-FW2-6 | 文件上传 (拖拽 + 进度条) |
| FE-02 §1 | FW2-7 | TASK-FW2-7 | WebSocket 连接管理 (自动重连 < 5s P95) |
| FE-02 §1 | FW2-8 | TASK-FW2-8 | OpenAPI 类型同步 |
| FE-02 §1 | FW2-9 | TASK-FW2-9 | SSE EventSource 客户端 + 事件分发 |
| FE-06 §1 | FA2-1 | TASK-FA2-1 | 用户管理 DataTable |
| FE-06 §1 | FA2-2 | TASK-FA2-2 | 组织管理 |
| FE-06 §1 | FA2-3 | TASK-FA2-3 | 审计日志查看 |

**Phase 2 跨层验证节点:**

| 验证节点 | 参与层 | 验证场景 | 集成任务卡 |
|---------|-------|---------|-----------|
| X2-1 | Gateway + Brain + Memory + Tool | **对话完整闭环** | TASK-INT-P2-CONV |
| X2-2 | Gateway + Brain | 流式回复完整链路 | TASK-INT-P2-CONV |
| X2-3 | Brain + Memory + Infra | Memory Evolution 闭环 | TASK-INT-P2-CONV |
| X2-4 | Gateway + Infra | Token 预算背压 (Loop D) | TASK-INT-P2-TOKEN |
| X2-5 | Obs + Gateway + Infra | 4 黄金信号端到端验证 | TASK-INT-P2-OBS |
| X2-6 | Obs + FE-Web | 前端错误上报闭环 | TASK-INT-P2-OBS |
| XF2-1 | FE-Web + Gateway | **登录->选组织->对话->流式回复** | TASK-INT-P2-FE |
| XF2-2 | FE-Web + Gateway + Memory | 记忆面板查看与删除 | TASK-INT-P2-FE |
| XF2-3 | FE-Web + Gateway | 文件上传闭环 | TASK-INT-P2-FE |
| XF2-4 | FE-Web + Gateway | OpenAPI 类型一致性 | TASK-INT-P2-OPENAPI |

---

### Phase 3 — Knowledge & Skill Ecosystem

**目标:** Knowledge双库 + Skill核心实现 + 扩展Tool + 内容安全 + 知识管理 + M1个人多模态

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| 01 §2.5 | B3-1 | TASK-B3-1 | Skill Router 实现 |
| 01 §2.5 | B3-2 | TASK-B3-2 | Brain 编排 Skill 执行流 |
| 01 §2.4 | B3-3 | TASK-B3-3 | 角色适配模块 |
| 01 §2.3 | B3-4 | TASK-B3-4 | 负反馈熔断 |
| 01 §3.1 | MC3-1 | TASK-MC3-1 | Promotion Pipeline — Memory -> Knowledge 提案流 |
| 01 §3.1 | MC3-2 | TASK-MC3-2 | promotion_receipt 写入 |
| 02 §2.1 | K3-1 | TASK-K3-1 | Neo4j 图谱 Schema + 种子数据 |
| 02 §2.2 | K3-2 | TASK-K3-2 | Qdrant 向量库初始化 + 种子数据 |
| 02 §3 | K3-3 | TASK-K3-3 | FK 联动机制 (Neo4j node_id <-> Qdrant point_id) |
| 02 §7.1 | K3-4 | TASK-K3-4 | Knowledge Write API |
| 02 §5 | K3-5 | TASK-K3-5 | Diyu Resolver 最小实现 (1-2 Profile) |
| 02 §4 | K3-6 | TASK-K3-6 | 实体类型注册机制 |
| 02 §7.1 | K3-7 | TASK-K3-7 | ERP/PIM 变更集 (ChangeSet) 接口 |
| 03 §5 | S3-1 | TASK-S3-1 | ContentWriterSkill 内容写手 |
| 03 §6 | S3-2 | TASK-S3-2 | MerchandisingSkill 搭配助手 |
| 03 §3 | S3-3 | TASK-S3-3 | Skill 生命周期管理 |
| 03 §2 | S3-4 | TASK-S3-4 | Skill 参数校验 |
| 04 §3 | T3-1 | TASK-T3-1 | WebSearch Tool |
| 04 §3 (M-Track M1) | T3-2 | TASK-T3-2 | ImageAnalyze Tool |
| 04 §3 (M-Track M1) | T3-3 | TASK-T3-3 | AudioTranscribe Tool |
| 04 §3 (M-Track M2) | MM2-5 | TASK-T3-4 | DocumentExtract Tool |
| 05a §2.4 | G3-1 | TASK-G3-1 | Knowledge Admin API `/api/v1/admin/knowledge/*` |
| 05a §1 | G3-2 | TASK-G3-2 | Skill API |
| 05 §10 | G3-3 | TASK-G3-3 | 内容安全检查 |
| 06 §8 | I3-1 | TASK-I3-1 | Neo4j 连接 + 基础 CRUD adapter |
| 06 §8 | I3-2 | TASK-I3-2 | Qdrant 连接 + 基础 CRUD adapter |
| 06 §8 (M-Track M0) | I3-3 | TASK-I3-3 | ObjectStoragePort 实现 (S3/MinIO) |
| 06 §9 (M-Track M0) | I3-4 | TASK-I3-4 | tool_usage_records DDL (v3.6) |
| 05 §10 (M-Track M1) | OS3-1 | TASK-OS3-1 | 内容安全检查管线 (security_status 6态) |
| 06 §4 | OS3-2 | TASK-OS3-2 | 审计闭环 (所有 CRUD + 权限变更) |
| 07 §5 | OS3-3 | TASK-OS3-3 | 知识写入安全校验 (XSS/注入防护) |
| 02 §5 | OS3-4 | TASK-OS3-4 | Resolver 查询审计 (who/when/what/why) |
| 05 §6 | OS3-5 | TASK-OS3-5 | API 限流告警 (429 频率监控) |
| 07 §5.1 | OS3-6 | TASK-OS3-6 | 租户隔离运行时验证 |
| 07 §1 | D3-1 | TASK-D3-1 | manifest.yaml TBD -> 实值 |
| 07 §1 | D3-2 | TASK-D3-2 | 安装器 + preflight 产品化 |
| 07 §1 | D3-3 | TASK-D3-3 | deploy/* 与 manifest 一致性检查 |
| 07 §1 | D3-4 | TASK-D3-4 | make verify-phase-3 |
| 07 §1 | D3-5 | TASK-D3-5 | SBOM 签名与 attestation (cosign) |
| FE-05 §1 | FW3-1 | TASK-FW3-1 | 知识浏览页 /knowledge |
| FE-04 §1 | FW3-2 | TASK-FW3-2 | Skill 结构化渲染 (右侧面板 Artifact) |
| FE-05 §1 | FW3-3 | TASK-FW3-3 | 商品组件 (ProductCard/OutfitGrid/StyleBoard) |
| FE-06 §1 | FA3-1 | TASK-FA3-1 | 知识编辑工作台 /admin/knowledge |
| FE-06 §1 | FA3-2 | TASK-FA3-2 | 内容审核队列 |
| FE-06 §1 | FA3-3 | TASK-FA3-3 | org_settings 配置管理 |

**Phase 3 M-Track M1 (个人多模态) 节点:**

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| 05 §8.2 | MM1-1 | TASK-MM1-1 | Personal Media Upload API 三步协议 |
| 05 §7 + 05a §4 | MM1-2 | TASK-MM1-2 | WS Payload Media Extension |
| 04 §3 | MM1-3 | TASK-MM1-3 | ImageAnalyze + AudioTranscribe 集成 |
| 01 §2.1 | MM1-4 | TASK-MM1-4 | Brain 多模态模型选择逻辑 |
| 05 §8.3 | MM1-5 | TASK-MM1-5 | security_status 三层拦截 |
| 01 §3.1.1 | MM1-6 | TASK-MM1-6 | Personal Media Delete Tombstone |

**Phase 3 跨层验证节点:**

| 验证节点 | 参与层 | 验证场景 | 集成任务卡 |
|---------|-------|---------|-----------|
| X3-1 | Brain + Skill + Knowledge + Tool | **对话触发 Skill 完整闭环** | TASK-INT-P3-SKILL |
| X3-2 | Knowledge (Neo4j + Qdrant) | FK 一致性验证 | TASK-INT-P3-KNOWLEDGE |
| X3-3 | Memory + Knowledge | Promotion Pipeline 跨 SSOT | TASK-INT-P3-KNOWLEDGE |
| X3-4 | Gateway + Knowledge | Knowledge Admin API 完整链路 | TASK-INT-P3-KNOWLEDGE |
| X3-5 | Obs + Gateway + Knowledge | 内容安全管线闭环 | TASK-INT-P3-SECURITY |
| X3-6 | Obs + Knowledge | Resolver 查询审计闭环 | TASK-INT-P3-KNOWLEDGE |
| XM1-1 | Multimodal + Gateway + Tool | M1 个人媒体上传闭环 | TASK-INT-P3-MEDIA |
| XM1-2 | Multimodal + Obs | M1 媒体安全扫描闭环 | TASK-INT-P3-SECURITY |
| XF3-1 | FE-Web + Gateway + Skill | **对话触发 Skill -> Artifact 渲染** | TASK-INT-P3-FE |
| XF3-2 | FE-Admin + Gateway + Knowledge | **知识编辑 -> 提交 -> 总部查看** | TASK-INT-P3-FE |
| XF3-3 | FE-Admin + Gateway | 组织配置继承验证 | TASK-INT-P3-FE |

---

### Phase 4 — Reliability & Full Feature

**目标:** SLI/SLO + 故障注入 + 删除管线 + 备份演练 + 性能基线 + 运维产品化 + M2企业多模态

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| 01 §4.4 | B4-1 | TASK-B4-1 | Context Assembler 性能优化 |
| 01 §4.2.1 | B4-2 | TASK-B4-2 | 动态预算分配器 v1 (ADR-035) |
| 01 §5 | B4-3 | TASK-B4-3 | TruncationPolicy: FixedPriorityPolicy |
| 01 §4 | B4-4 | TASK-B4-4 | 7 项 SLI 埋点 (ADR-038) |
| 01 §4 | B4-5 | TASK-B4-5 | Sanitization pattern-based |
| 01 §3.1.1 | MC4-1 | TASK-MC4-1 | 删除管线 8态状态机 (ADR-039) |
| 07 §6 | MC4-2 | TASK-MC4-2 | 备份恢复演练 |
| 01 §3.1.1 | MC4-3 | TASK-MC4-3 | deletion_timeout_rate SLI = 0% |
| 02 §3.4 | K4-1 | TASK-K4-1 | 图谱查询性能基线 |
| 02 §2.2 | K4-2 | TASK-K4-2 | 向量检索性能基线 |
| 02 §3.5 | K4-3 | TASK-K4-3 | FK 一致性 Reconciliation Job |
| 03 §3 | S4-1 | TASK-S4-1 | Skill 熔断器 |
| 03 §3 | S4-2 | TASK-S4-2 | Skill 执行超时 |
| 04 §5 | T4-1 | TASK-T4-1 | Tool 独立计费 (ADR-047) |
| 04 §5 | T4-2 | TASK-T4-2 | Tool 重试 + 指数退避 |
| 05 §6 | G4-1 | TASK-G4-1 | SLO 指标 + 告警 |
| 07 §6 | G4-2 | TASK-G4-2 | HA 验证 |
| 05 §6.1 | G4-3 | TASK-G4-3 | 限流精细化 (per-org/per-user) |
| 06 §7 | I4-1 | TASK-I4-1 | Prometheus + Grafana 监控栈 |
| 07 §6.1 | I4-2 | TASK-I4-2 | PG failover 实际演练 |
| 07 §6.1 | I4-3 | TASK-I4-3 | 备份恢复演练 (PG 全量 + WAL/PITR) |
| 06 §6.2 | I4-4 | TASK-I4-4 | 故障注入测试 (删除管线每步注入失败) |
| 07 §5 | I4-5 | TASK-I4-5 | PIPL/GDPR 删除管线完整实现 |
| 01 §4 | OS4-1 | TASK-OS4-1 | 7 项 Brain SLI 定义 + Grafana 看板 |
| 07 §5 | OS4-2 | TASK-OS4-2 | SLO 定义 (P95 < 500ms, error < 0.1%, avail > 99.5%) |
| 07 §5 | OS4-3 | TASK-OS4-3 | 告警分级 (P0/P1/P2) + 升级规则 |
| 00 §8 | OS4-4 | TASK-OS4-4 | 全链路 trace_id 验证 (Gateway->Brain->Memory->Tool) |
| 06 §6.2 | OS4-5 | TASK-OS4-5 | 故障注入 — 删除管线每步注入失败 |
| 05 §5 | OS4-6 | TASK-OS4-6 | 故障注入 — LLM Provider 不可用 |
| 07 §5 | OS4-7 | TASK-OS4-7 | 渗透测试基线 (OWASP Top 10) |
| FE-08 §1 | OS4-8 | TASK-OS4-8 | 前端 a11y 无障碍审计 (axe-core 0 critical) |
| 07 §3 | D4-1 | TASK-D4-1 | 升级回滚流程产品化 |
| 07 §6 | D4-2 | TASK-D4-2 | 备份恢复演练门禁 |
| 07 §3 | D4-3 | TASK-D4-3 | 一键诊断包 diyu diagnose |
| 07 §5.2 | D4-4 | TASK-D4-4 | 密钥轮换 + 证书管理 |
| 07 §3 | D4-5 | TASK-D4-5 | 轻量离线 (docker save/load) |
| 07 §1 | D4-6 | TASK-D4-6 | make verify-phase-4 |
| FE-05 §1 | FW4-1 | TASK-FW4-1 | 性能预算达标 |
| FE-08 §1 | FW4-2 | TASK-FW4-2 | a11y 检查通过 |
| FE-05 §1 | FW4-3 | TASK-FW4-3 | 暗色/亮色模式 |
| FE-05 §1 | FW4-4 | TASK-FW4-4 | 键盘快捷键 |
| FE-05 §1 | FW4-5 | TASK-FW4-5 | 积分充值页 /billing |
| FE-06 §1 | FA4-1 | TASK-FA4-1 | 系统监控看板 |
| FE-06 §1 | FA4-2 | TASK-FA4-2 | 配额管理 |
| FE-06 §1 | FA4-3 | TASK-FA4-3 | 备份管理 |

**Phase 4 M-Track M2 (企业多模态) 节点:**

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| 05 §8 | MM2-1 | *(嵌入 G3-1/K3-4)* | Enterprise media upload API |
| 02 §5.4 | MM2-2 | *(嵌入 K3-5)* | KnowledgeBundle media_contents 扩展 |
| 02 §3.6 | MM2-3 | *(嵌入 K3-3)* | enterprise_media_objects + Neo4j FK 联动 |
| 03 §2 | MM2-4 | *(嵌入 S5-2)* | Skill multimodal_input/output 能力声明 |
| 04 §3 | MM2-5 | TASK-T3-4 | DocumentExtract Tool |
| 02 §7.1 | MM2-6 | *(嵌入 K3-7)* | Enterprise media deletion pipeline |

**Phase 4 跨层验证节点:**

| 验证节点 | 参与层 | 验证场景 | 集成任务卡 |
|---------|-------|---------|-----------|
| X4-1 | All | **全链路 trace_id 追踪** | TASK-INT-P4-TRACE |
| X4-2 | Infra + Delivery | 升级/回滚演练 | *(D4-1/D4-2 内含)* |
| X4-3 | All | 三 SSOT 一致性 | *(D3-1/D3-3 延续)* |
| X4-4 | Brain + Memory + Infra | **删除管线端到端** | TASK-INT-P4-DELETE |
| X4-5 | Obs + All | SLI/SLO 指标端到端验证 | TASK-INT-P4-SLO |
| X4-6 | Obs + Infra | 故障注入与恢复验证 | TASK-INT-P4-FAULT |
| X4-7 | Obs + Gateway | 渗透测试 OWASP Top 10 | *(OS4-7 内含)* |
| XM2-1 | Multimodal + Knowledge + Infra | M2 企业媒体双写 + FK 验证 | TASK-INT-P4-MEDIA |
| XM2-2 | Multimodal + Obs | M2 NSFW + 版权预检 | TASK-INT-P4-MEDIA |
| XF4-1 | FE-Web + Gateway | **积分耗尽 -> 充值 -> 余额更新** | TASK-INT-P4-FE |
| XF4-2 | FE-Admin + Infra | 系统监控看板 | TASK-INT-P4-FE |
| XF4-3 | FE-Web + Gateway + Memory | **查看AI记忆 -> 删除 -> 确认删除** | TASK-INT-P4-FE |

---

### Phase 5 — Governance & Automation

**目标:** 自动治理 + 合规 + 平台化 + API生命周期 + M3成熟度

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| 01 §2.3 | B5-1 | TASK-B5-1 | Memory Governor 组件 |
| 01 §4 | B5-2 | TASK-B5-2 | Confidence Calibration 批量校准 |
| 01 §4 | B5-3 | TASK-B5-3 | AssemblyProfile 多次异构 LLM 调用 |
| 01 §2.3 | B5-4 | TASK-B5-4 | Memory Consolidation 相似记忆合并 |
| 01 §3.1 | MC5-1 | TASK-MC5-1 | Memory Consolidation 自动合并 |
| 01 §3.2 | MC5-2 | TASK-MC5-2 | Contextual Chunking embedding 前缀增强 |
| 07 §5.2 | MC5-3 | TASK-MC5-3 | Crypto Shredding per-user 加密 |
| 02 §4 | K5-1 | TASK-K5-1 | Capability Registry 统一注册中心 |
| 02 §5 | K5-2 | TASK-K5-2 | 可解释性面板 injection_receipt.explanation_trace |
| 03 §2 | S5-1 | TASK-S5-1 | Skill A/B Testing |
| 03 §2 (M-Track M2) | S5-2 | TASK-S5-2 | Skill multimodal 能力声明 |
| 04 §5 | T5-1 | TASK-T5-1 | Tool 成本看板 |
| 04 §5 | T5-2 | TASK-T5-2 | LLMCallPort Contract 阶段评估 (ADR-046) |
| 05 §2 | G5-1 | TASK-G5-1 | API 版本协商 |
| 05 §2 | G5-2 | TASK-G5-2 | API 废弃告警 |
| 06 §6 | I5-1 | TASK-I5-1 | Event Mesh 演进 (PG Outbox -> NATS/Kafka) |
| 06 §6 | I5-2 | TASK-I5-2 | Schema Registry |
| 00 §13 | OS5-1 | TASK-OS5-1 | 三 SSOT 自动一致性检查 |
| 00 §14 | OS5-2 | TASK-OS5-2 | Guard 自动阻断策略 |
| 00 §14 | OS5-3 | TASK-OS5-3 | Exception Register 到期自动审计 |
| 00 §14 | OS5-4 | TASK-OS5-4 | 月度架构偏差审计模板 + 自动产出 |
| 07 §5 | OS5-5 | TASK-OS5-5 | GDPR/PIPL 合规报告自动生成 |
| 07 §5 | OS5-6 | TASK-OS5-6 | 安全事件响应手册 (Runbook) |
| 07 §1 | D5-1 | TASK-D5-1 | 三 SSOT 自动一致性检查 |
| 07 §1 | D5-2 | TASK-D5-2 | Exception Register 到期自动审计 |
| 07 §1 | D5-3 | TASK-D5-3 | 月度架构偏差审计模板 |
| 07 §1 | D5-4 | TASK-D5-4 | make verify-phase-5 |
| FE-06 §1 | FA5-1 | TASK-FA5-1 | 合规报告 |
| FE-06 §1 | FA5-2 | TASK-FA5-2 | Exception Register UI |
| FE-05 §1 (M-Track) | FW5-1 | TASK-FW5-1 | 语音交互 |

**Phase 5 M-Track M3 (成熟度) 节点:**

| 架构文档章节 | 矩阵节点 | 任务卡 ID | 交付物说明 |
|-------------|---------|----------|-----------|
| 07 §5 | MM3-1 | TASK-MM3-1 | 版权风险检测 |
| 02 §2.2 | MM3-2 | *(嵌入 K5-2)* | 跨模态语义检索 |
| 04 §5 | MM3-3 | *(嵌入 T5-2)* | LLMCallPort Contract 阶段评估 |

**Phase 5 跨层验证节点:**

| 验证节点 | 参与层 | 验证场景 |
|---------|-------|---------|
| X5-1 | Delivery + Governance | Guard 自动阻断策略生效 |
| X5-2 | All | 月度架构偏差审计 |
| X5-3 | Obs + Delivery + CI | 三 SSOT 自动一致性 + Guard 联动 |
| X5-4 | Obs + All | GDPR/PIPL 合规端到端验证 |
| XM3-1 | Multimodal + Knowledge | M3 跨模态语义检索 |
| XM3-2 | Multimodal + Obs | M3 版权合规审计 |

---

## 表 3: 统计汇总

### 3.1 维度 × Phase 节点分布

| 维度 | 前缀 | 总计 | P0 | P1 | P2 | P3 | P4 | P5 |
|------|------|-----|----|----|----|----|----|----|
| Brain | B | 24 | 3 | 0 | 8 | 4 | 5 | 4 |
| MemoryCore | MC | 18 | 3 | 0 | 7 | 2 | 3 | 3 |
| Knowledge | K | 15 | 3 | 0 | 0 | 7 | 3 | 2 |
| Skill | S | 10 | 2 | 0 | 0 | 4 | 2 | 2 |
| Tool | T | 13 | 3 | 0 | 3 | 3 | 2 | 2 |
| Gateway | G | 24 | 3 | 6 | 7 | 3 | 3 | 2 |
| Infrastructure | I | 31 | 6 | 7 | 5 | 4 | 5 | 2 |
| FE-Web | FW | 32 | 8 | 4 | 9 | 3 | 5 | 2(+1closed) |
| FE-Admin | FA | 16 | 3 | 2 | 3 | 3 | 3 | 2 |
| Delivery | D | 32 | 10 | 3 | 5 | 5 | 6 | 4 |
| Obs & Security | OS | 39 | 6 | 6 | 5 | 6 | 8 | 6 |
| **层维度小计** | — | **254** | **50** | **28** | **52** | **44** | **45** | **31(+2 embed)** |

| 跨域维度 | 前缀 | 总计 | M0/P0 | M1/P3 | M2/P4 | M3/P5 |
|---------|------|-----|-------|-------|-------|-------|
| Multimodal | MM | 23 | 8 | 6 | 6 | 3 |

| 验证维度 | 前缀 | 总计 | P0 | P1 | P2 | P3 | P4 | P5 |
|---------|------|-----|----|----|----|----|----|----|
| 跨层验证 | X | 30 | 5 | 5 | 6 | 6 | 7 | 4 |
| 前后端集成 | XF | 10 | 0 | 0 | 4 | 3 | 3 | 0 |
| 多模态跨层 | XM | 6 | 1 | 0 | 0 | 2 | 2 | 2 |
| **验证小计** | — | **46** | **6** | **5** | **10** | **11** | **12** | **6** |

**全量总计: 323 节点 (254 层维度 + 23 M-Track + 46 验证)**

### 3.2 架构文档覆盖范围

| 架构文档 | 覆盖 Phase | 高峰 Phase |
|---------|-----------|-----------|
| 00-系统定位与架构总览 | P0-P5 | P0 (Day-1 Port 定义) |
| 01-Brain | P0, P2-P5 | P2 (对话引擎 + Memory) |
| 02-Knowledge | P0, P3-P5 | P3 (双库全量实现) |
| 03-Skill | P0, P3-P5 | P3 (核心 Skill 实现) |
| 04-Tool | P0, P2-P5 | P2 (LLMCall) + P3 (扩展 Tool) |
| 05-Gateway + 05a | P0-P5 | P1 (安全基础) + P2 (业务 API) |
| 06-Infrastructure | P0-P5 | P1 (组织模型) + P2 (运行时) |
| 07-Deployment & Security | P0-P5 | P0 (CI) + P4 (运维产品化) |
| 08-Appendix | P0-P5 | — (参考文档) |
| FE-00~08 | P0-P5 | P0 (骨架) + P2 (对话界面) |

### 3.3 每个 Phase 的架构文档涉及度

| Phase | 涉及架构文档数 (后端) | 涉及架构文档数 (前端) | 总交付节点 |
|-------|---------------------|---------------------|-----------|
| Phase 0 | 00, 01-06, 07, 08 (全部) | FE-00, 01, 07, 08 | 64 |
| Phase 1 | 05, 06, 07 | FE-03 | 33 |
| Phase 2 | 01, 04, 05, 05a, 06, 07 | FE-02, 04, 06, 07, 08 | 62 |
| Phase 3 | 01, 02, 03, 04, 05, 05a, 06, 07 | FE-04, 05, 06 | 61 |
| Phase 4 | 00, 01, 02, 03, 04, 05, 06, 07 | FE-05, 06, 08 | 63 |
| Phase 5 | 00, 01, 02, 03, 04, 05, 06, 07 | FE-05, 06 | 40 |

---

## 附录: 文件路径速查

### L1 架构文档
```
docs/architecture/00-系统定位与架构总览.md
docs/architecture/01-对话Agent层-Brain.md
docs/architecture/02-Knowledge层.md
docs/architecture/03-Skill层.md
docs/architecture/04-Tool层.md
docs/architecture/05-Gateway层.md
docs/architecture/05a-API-Contract.md
docs/architecture/06-基础设施层.md
docs/architecture/07-部署与安全.md
docs/architecture/08-附录.md
docs/frontend/00-architecture-overview.md
docs/frontend/01-monorepo-infrastructure.md
docs/frontend/02-transport-layer.md
docs/frontend/03-auth-permission.md
docs/frontend/04-dialog-engine.md
docs/frontend/05-page-routes.md
docs/frontend/06-admin-console.md
docs/frontend/07-deployment.md
docs/frontend/08-quality-engineering.md
```

### L2 里程碑矩阵
```
docs/governance/milestone-matrix.md              (主索引)
docs/governance/milestone-matrix-backend.md       (后端 7 维度)
docs/governance/milestone-matrix-crosscutting.md   (跨切 3 维度 + 验证节点)
docs/governance/milestone-matrix-frontend.md       (前端 2 维度)
delivery/milestone-matrix.yaml                    (机器可读 YAML)
delivery/milestone-matrix.schema.yaml             (YAML Schema)
```

### L3 任务卡
```
docs/task-cards/00-跨层集成/phase-2-integration.md
docs/task-cards/00-跨层集成/phase-3-integration.md
docs/task-cards/00-跨层集成/phase-4-integration.md
docs/task-cards/01-对话Agent层-Brain/brain.md
docs/task-cards/01-对话Agent层-Brain/memory-core.md
docs/task-cards/02-Knowledge层/knowledge.md
docs/task-cards/03-Skill层/skill.md
docs/task-cards/04-Tool层/tool.md
docs/task-cards/05-Gateway层/gateway.md
docs/task-cards/06-基础设施层/infrastructure.md
docs/task-cards/07-部署与安全/delivery.md
docs/task-cards/07-部署与安全/obs-security.md
docs/task-cards/08-多模态/multimodal.md
docs/task-cards/frontend/01-monorepo-infrastructure/task-cards.md
docs/task-cards/frontend/02-transport-layer/task-cards.md
docs/task-cards/frontend/03-auth-permission/task-cards.md
docs/task-cards/frontend/04-dialog-engine/task-cards.md
docs/task-cards/frontend/05-page-routes/task-cards.md
docs/task-cards/frontend/06-admin-console/task-cards.md
docs/task-cards/frontend/07-deployment/task-cards.md
docs/task-cards/frontend/08-quality-engineering/task-cards.md
```
