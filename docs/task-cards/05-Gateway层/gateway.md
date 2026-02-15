# Gateway 层任务卡集

> 架构文档: `docs/architecture/05-Gateway层.md` + `05a-API-Contract.md`
> 里程碑来源: `docs/governance/milestone-matrix-backend.md` Section 6
> 影响门禁: `src/gateway/**` -> check_layer_deps + OpenAPI sync check
> 渐进式组合 Step 5

---

## Phase 0 -- 骨架与 CI

### TASK-G0-1: FastAPI + Uvicorn 最小运行

| 字段 | 内容 |
|------|------|
| **目标** | `/healthz` 端点返回 200，确保应用骨架可启动 |
| **范围 (In Scope)** | `src/gateway/api/main.py`, `src/gateway/api/health.py` |
| **范围外 (Out of Scope)** | Brain 意图理解 / Skill Prompt 组装 / Knowledge Stores / 前端 UI |
| **依赖** | pyproject.toml (I0-2) |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `uvicorn src.gateway.api.main:app --host 0.0.0.0 --port 8000 & sleep 2 && curl -s localhost:8000/healthz` |
| **回滚方案** | `git revert <commit>` |
| **证据** | healthz 返回 200 |
| **风险** | 依赖: I0-2 (pyproject.toml) / 数据: N/A -- 纯骨架 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: FastAPI + Uvicorn 作为 Gateway 运行时 / 理由: 异步性能 + 自动 OpenAPI 生成 / 来源: 架构文档 05 Section 1 |

> 矩阵条目: G0-1 | V-x: X0-3

### TASK-G0-2: OpenAPI spec 自动生成

| 字段 | 内容 |
|------|------|
| **目标** | 访问 `/docs` 看到 Swagger UI，为前端类型同步提供基础 |
| **范围 (In Scope)** | `src/gateway/api/main.py` (FastAPI 自动) |
| **范围外 (Out of Scope)** | Brain 意图理解 / Skill Prompt 组装 / 前端类型生成工具 / API 业务逻辑 |
| **依赖** | TASK-G0-1 |
| **兼容策略** | FastAPI 内置功能 |
| **验收命令** | [ENV-DEP] `curl -s localhost:8000/openapi.json | python -m json.tool` |
| **回滚方案** | 不适用（FastAPI 内置） |
| **证据** | Swagger 页面截图 |
| **风险** | 依赖: G0-1 (FastAPI 骨架) / 数据: N/A / 兼容: FastAPI 内置 / 回滚: 不适用 |
| **决策记录** | 决策: OpenAPI spec 自动生成 (FastAPI 内置) / 理由: 前端类型同步 SSOT / 来源: 架构文档 05 Section 1 |

> 矩阵条目: G0-2 | V-fb: XF2-4

### TASK-G0-3: 请求日志中间件 (trace_id + request_id)

| 字段 | 内容 |
|------|------|
| **目标** | 所有请求日志包含 trace_id, request_id, org_id 三个必需字段 |
| **范围 (In Scope)** | `src/gateway/middleware/logging.py`, `tests/unit/gateway/test_logging.py` |
| **范围外 (Out of Scope)** | Brain 意图理解 / 日志存储基础设施 / 告警规则 / 前端 UI |
| **依赖** | TASK-G0-1 |
| **兼容策略** | 新增中间件 |
| **验收命令** | `pytest tests/unit/gateway/test_logging.py -v` (日志含 3 必需字段) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 日志格式单测通过 |
| **风险** | 依赖: G0-1 / 数据: 日志需脱敏, 不记录敏感字段 / 兼容: 新增中间件 / 回滚: git revert |
| **决策记录** | 决策: trace_id + request_id + org_id 三字段必需 / 理由: 分布式追踪 + 租户级日志隔离 / 来源: 架构文档 05 Section 1 |

> 矩阵条目: G0-3

---

## Phase 1 -- 安全与租户底座（核心交付 Phase）

### TASK-G1-1: JWT 认证中间件

| 字段 | 内容 |
|------|------|
| **目标** | 无 token 返回 401; 无效 token 返回 401; 有效 token 提取 user_id + org_id |
| **范围 (In Scope)** | `src/gateway/middleware/auth.py`, `tests/unit/gateway/test_auth.py` |
| **范围外 (Out of Scope)** | SSO 集成 / Brain 意图理解 / RBAC 权限 / 前端登录 UI |
| **依赖** | -- |
| **兼容策略** | 新增中间件；healthz 端点豁免 |
| **验收命令** | `pytest tests/unit/gateway/test_auth.py -v` (3 场景单测) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 认证拒绝率准确 |
| **风险** | 依赖: N/A / 数据: JWT 密钥需安全存储 / 兼容: 新增中间件, healthz 豁免 / 回滚: git revert |
| **决策记录** | 决策: JWT 自建认证 (后期可接 SSO) / 理由: 初期快速启动, 保留 SSO 扩展能力 / 来源: 架构文档 05 Section 3 |

> 矩阵条目: G1-1 | V-x: X1-1 | V-fb: XF2-1

### TASK-G1-2: OrgContext 中间件完整链路

| 字段 | 内容 |
|------|------|
| **目标** | JWT -> 解析 org_chain -> 注入 OrgContext 到请求上下文 -> RLS 生效 |
| **范围 (In Scope)** | `src/gateway/middleware/org_context.py`, `tests/unit/gateway/test_org_context.py` |
| **范围外 (Out of Scope)** | Brain 意图理解 / RLS 策略实现 / 组织模型管理 / 前端 UI |
| **依赖** | Infra 组织模型 (I1-1) |
| **兼容策略** | 新增中间件 |
| **验收命令** | `pytest tests/unit/gateway/test_org_context.py -v` (OrgContext 注入成功率 100%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | org_chain 解析单测通过 |
| **风险** | 依赖: I1-1 (组织模型) / 数据: OrgContext 贯穿全链路, 错误影响范围大 / 兼容: 新增中间件 / 回滚: git revert |
| **决策记录** | 决策: OrgContext Schema v1 贯穿 Gateway->Brain->Skill->Tool->Knowledge (ADR-033) / 理由: 统一组织上下文, 支持 RLS 租户隔离 / 来源: ADR-033, ADR-049, 架构文档 05 Section 4.2 |

> 矩阵条目: G1-2 | V-x: X1-1 | V-fb: XF2-1

### TASK-G1-3: RBAC 权限检查

| 字段 | 内容 |
|------|------|
| **目标** | 无权限用户访问 Admin API 返回 403 |
| **范围 (In Scope)** | `src/gateway/middleware/rbac.py`, `tests/unit/gateway/test_rbac.py` |
| **范围外 (Out of Scope)** | Brain 意图理解 / RBAC 表管理 / 前端权限渲染 / Skill 权限 |
| **依赖** | RBAC 表 (I1-4) |
| **兼容策略** | 新增中间件 |
| **验收命令** | `pytest tests/unit/gateway/test_rbac.py -v` (403 响应准确) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 权限码映射单测通过 |
| **风险** | 依赖: I1-4 (RBAC 表) / 数据: 权限配置错误可导致越权 / 兼容: 新增中间件 / 回滚: git revert |
| **决策记录** | 决策: RBAC + Org Scope 权限校验 / 理由: Admin API 需严格权限控制 / 来源: 架构文档 05 Section 3 |

> 矩阵条目: G1-3 | V-x: X1-2

### TASK-G1-4: RLS 策略基线

| 字段 | 内容 |
|------|------|
| **目标** | 租户 A 的 API 请求只能访问租户 A 的数据，跨租户泄露 = 0 |
| **范围 (In Scope)** | `tests/isolation/test_rls.py` |
| **范围外 (Out of Scope)** | RLS 策略定义 / Brain 意图理解 / 业务代码变更 / 前端 UI |
| **依赖** | PG RLS (I1-3) |
| **兼容策略** | 测试层面验证，不改业务代码 |
| **验收命令** | `pytest tests/isolation/test_rls.py -v` (跨租户泄露 = 0) |
| **回滚方案** | 不适用（测试代码） |
| **证据** | 隔离测试通过 |
| **风险** | 依赖: I1-3 (PG RLS) / 数据: 跨租户泄露为安全事件 / 兼容: 纯测试 / 回滚: 不适用 |
| **决策记录** | 决策: RLS 策略基线 -- 跨租户泄露 = 0 / 理由: 多租户隔离是安全底线 / 来源: 架构文档 05 Section 3 |

> 矩阵条目: G1-4 | V-x: X1-1

### TASK-G1-5: API 分区规则 (ADR-029)

| 字段 | 内容 |
|------|------|
| **目标** | 用户 API `/api/v1/*` 和管理 API `/api/v1/admin/*` 分离 |
| **范围 (In Scope)** | `src/gateway/api/router.py` |
| **范围外 (Out of Scope)** | Brain 意图理解 / Skill 实现 / 具体 API 业务逻辑 / 前端路由 |
| **依赖** | TASK-G0-1 |
| **兼容策略** | 路由注册规范化 |
| **验收命令** | `python -c "from src.gateway.api.router import app; routes=[r.path for r in app.routes]; assert any('/api/v1/admin/' in r for r in routes) and any('/api/v1/' in r and '/admin/' not in r for r in routes); print('PASS')"` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 路由列表截图 |
| **风险** | 依赖: G0-1 / 数据: N/A / 兼容: 路由规范化 / 回滚: git revert |
| **决策记录** | 决策: API 分区 -- 用户 /api/v1/* vs 管理 /api/v1/admin/* (ADR-029) / 理由: 权限边界清晰, 可独立限流 / 来源: ADR-029, 架构文档 05 Section 1 |

> 矩阵条目: G1-5

### TASK-G1-6: 安全头配置

| 字段 | 内容 |
|------|------|
| **目标** | 响应包含 HSTS + X-Content-Type-Options + CSP |
| **范围 (In Scope)** | `src/gateway/middleware/security_headers.py` |
| **范围外 (Out of Scope)** | Brain 意图理解 / 前端 CSP 策略 / WAF 配置 / SSL 证书 |
| **依赖** | TASK-G0-1 |
| **兼容策略** | 新增中间件 |
| **验收命令** | [ENV-DEP] `curl -I localhost:8000/healthz` (响应头含安全字段) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 安全头齐全 |
| **风险** | 依赖: G0-1 / 数据: N/A / 兼容: 新增中间件 / 回滚: git revert |
| **决策记录** | 决策: HSTS + X-Content-Type-Options + CSP 安全头 / 理由: OWASP 推荐安全头配置 / 来源: 架构文档 05 Section 3 |

> 矩阵条目: G1-6

---

## Phase 2 -- 业务 API

### TASK-G2-1: 对话 REST API

| 字段 | 内容 |
|------|------|
| **目标** | POST /api/v1/conversations/{id}/messages -> Brain 处理 -> 返回回复，API 响应 < 2s |
| **范围 (In Scope)** | `src/gateway/api/conversations.py`, `tests/unit/gateway/test_conversations.py` |
| **范围外 (Out of Scope)** | Brain 内部对话逻辑 / Skill 执行 / Knowledge 检索 / 前端 UI |
| **依赖** | Brain (B2-1) |
| **兼容策略** | 新增 API 端点 |
| **验收命令** | `pytest tests/unit/gateway/test_conversations.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | API 契约测试通过 |
| **风险** | 依赖: B2-1 (Brain 对话引擎) / 数据: 对话内容需安全检查 / 兼容: 新增 API / 回滚: git revert |
| **决策记录** | 决策: REST API 作为对话备选通道 (主通道为 WebSocket) / 理由: 兼容不支持 WS 的客户端 / 来源: 架构文档 05 Section 1 |

> 矩阵条目: G2-1 | V-x: X2-1 | V-fb: XF2-1

### TASK-G2-2: WebSocket 实时对话

| 字段 | 内容 |
|------|------|
| **目标** | WS /ws/conversations/{id} -> 流式接收 ai_response_chunk，首字节延迟 < 500ms |
| **范围 (In Scope)** | `src/gateway/ws/conversation.py`, `tests/unit/gateway/test_ws.py` |
| **范围外 (Out of Scope)** | Brain 流式生成逻辑 / 前端 WS 客户端 / REST API / SSE |
| **依赖** | TASK-G2-1 |
| **兼容策略** | 新增 WS 端点；REST 保持不变 |
| **验收命令** | `pytest tests/unit/gateway/test_ws.py -v` (首字节延迟 < 500ms) |
| **回滚方案** | `git revert <commit>` |
| **证据** | WS 协议单测通过 |
| **风险** | 依赖: G2-1 (REST API) 作为降级 / 数据: WS 连接需认证 / 兼容: 新增 WS, REST 不变 / 回滚: git revert |
| **决策记录** | 决策: WebSocket 作为主交互通道, 命名禁止 assistant_chunk/assistant_complete / 理由: 流式体验 + 低延迟 / 来源: 架构文档 05 Section 7 |

> 矩阵条目: G2-2 | V-x: X2-2 | V-fb: XF2-1 | M-Track: MM1-2 (ai_response_chunk 含 media 字段扩展)

### TASK-G2-3: LLM Gateway (LiteLLM 集成)

| 字段 | 内容 |
|------|------|
| **目标** | 统一路由到不同 LLM provider + 计费 + 审计 |
| **范围 (In Scope)** | `src/gateway/llm/router.py`, `tests/unit/gateway/test_llm_router.py` |
| **范围外 (Out of Scope)** | Brain 意图理解 / Skill Prompt 组装 / LLM provider 内部 / 前端 UI |
| **依赖** | LiteLLM |
| **兼容策略** | 新增路由层 |
| **验收命令** | `pytest tests/unit/gateway/test_llm_router.py -v` (路由成功率 100%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 路由逻辑单测通过 |
| **风险** | 依赖: LiteLLM 外部库 / 数据: API Key 需安全存储 / 兼容: 新增路由层 / 回滚: git revert |
| **决策记录** | 决策: LiteLLM 集成 (不独立部署代理服务) + Model Registry / 理由: 统一多 provider 路由 + fallback + 计费 / 来源: 架构文档 05 Section 5 |

> 矩阵条目: G2-3 | V-x: X2-1

### TASK-G2-4: Token 预算 Pre-check (Loop D Phase 1)

| 字段 | 内容 |
|------|------|
| **目标** | 预算耗尽返回 402 + X-Budget-Remaining 告警头 |
| **范围 (In Scope)** | `src/gateway/middleware/budget.py`, `tests/unit/gateway/test_budget.py` |
| **范围外 (Out of Scope)** | 计费结算逻辑 / Brain 意图理解 / 前端预算展示 / Tool 计费 |
| **依赖** | usage_budgets (I2-3) |
| **兼容策略** | 新增中间件 |
| **验收命令** | `pytest tests/unit/gateway/test_budget.py -v` (402 响应准确) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 预算计算单测通过 |
| **风险** | 依赖: I2-3 (usage_budgets) / 数据: 预算计算需准确, 误判影响用户体验 / 兼容: 新增中间件 / 回滚: git revert |
| **决策记录** | 决策: 402 (预算耗尽) vs 429 (限流) 语义区分 / 理由: 客户端需区分两种拒绝原因 / 来源: 架构文档 05 Section 6 |

> 矩阵条目: G2-4 | V-x: X2-4 | V-fb: XF4-1

### TASK-G2-5: 限流中间件

| 字段 | 内容 |
|------|------|
| **目标** | 超过阈值返回 429 |
| **范围 (In Scope)** | `src/gateway/middleware/rate_limit.py`, `tests/unit/gateway/test_rate_limit.py` |
| **范围外 (Out of Scope)** | Brain 意图理解 / Redis 基础设施 / 精细化限流 (per-org) / 前端 UI |
| **依赖** | Redis (I2-1) |
| **兼容策略** | 新增中间件 |
| **验收命令** | `pytest tests/unit/gateway/test_rate_limit.py -v` (429 响应准确) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 限流算法单测通过 |
| **风险** | 依赖: I2-1 (Redis) / 数据: N/A / 兼容: 新增中间件 / 回滚: git revert |
| **决策记录** | 决策: 三级限流 (租户/用户/API 粒度) / 理由: 防止单租户耗尽资源 / 来源: 架构文档 05 Section 6 |

> 矩阵条目: G2-5

### TASK-G2-6: 三步文件上传协议 (ADR-045) [M-Track M0]

| 字段 | 内容 |
|------|------|
| **目标** | 申请 URL -> 上传 -> 确认 -> 文件可访问，上传成功率 >= 99% |
| **范围 (In Scope)** | `src/gateway/api/upload.py`, `tests/unit/gateway/test_upload.py` |
| **范围外 (Out of Scope)** | 对象存储内部 / Brain 意图理解 / 前端上传 UI / 安全扫描实现 |
| **依赖** | ObjectStoragePort (I3-3) |
| **兼容策略** | 新增 API 端点 |
| **验收命令** | `pytest tests/unit/gateway/test_upload.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 3 步协议单测通过 |
| **风险** | 依赖: I3-3 (ObjectStoragePort) / 数据: 文件需安全扫描 + Checksum 校验 (ADR-052) / 兼容: 新增 API / 回滚: git revert |
| **决策记录** | 决策: 三步上传协议 (init->直传 S3->complete) (ADR-045) / 理由: 大文件不经应用层, 减少带宽 / 来源: ADR-045, ADR-052, 架构文档 05 Section 8.2 |

> 矩阵条目: G2-6 | V-fb: XF2-3 | M-Track: MM0-2

### TASK-G2-7: SSE 通知端点 `/events/*`

| 字段 | 内容 |
|------|------|
| **目标** | 注册 SSE 端点，推送 6 种事件类型 (task_status_update / system_notification / budget_warning / knowledge_update / media_event / experiment_update) |
| **范围 (In Scope)** | `src/gateway/sse/events.py`, `tests/unit/gateway/test_sse.py` |
| **范围外 (Out of Scope)** | 前端 SSE 消费实现 / Brain 意图理解 / WS 通道 / polling fallback |
| **依赖** | TASK-G1-1 (JWT), TASK-G1-2 (OrgContext) |
| **兼容策略** | 新增端点；SaaS 模式经 BFF 代理，Private 模式直连 + token 参数 |
| **验收命令** | `pytest tests/unit/gateway/test_sse.py -v` (6 种事件类型注册 + 租户隔离推送) |
| **回滚方案** | `git revert <commit>` |
| **证据** | SSE 连接建立 + 事件推送单测通过 |
| **风险** | 依赖: G1-1 (JWT) + G1-2 (OrgContext) / 数据: 事件推送需租户隔离 / 兼容: 新增端点 / 回滚: git revert |
| **决策记录** | 决策: SSE /events/* 端点推送 6 种事件 (含 SaaS/Private 双模式) / 理由: 前端实时通知, 避免轮询 / 来源: 架构文档 05a Section 5.2 |

> 矩阵条目: G2-7 (新增) | 前端消费方规格: FE-02 Section 2
> 说明: 05a-API-Contract Section 5.2 定义 SSE 事件协议，前端 FE-02 有完整消费方实现 (含 polling fallback)，本卡补全 Gateway 生产方

---

## Phase 3 -- Knowledge/Skill API

### TASK-G3-1: Knowledge Admin API

| 字段 | 内容 |
|------|------|
| **目标** | `/api/v1/admin/knowledge/*` CRUD 知识条目 -> 双写 Neo4j+Qdrant |
| **范围 (In Scope)** | `src/gateway/api/admin/knowledge.py`, `tests/unit/gateway/test_knowledge_api.py` |
| **范围外 (Out of Scope)** | Knowledge 双写内部实现 / Brain 意图理解 / 前端 Admin UI / FK 联动 |
| **依赖** | Knowledge Layer (K3-4) |
| **兼容策略** | 新增 Admin API 端点 |
| **验收命令** | `pytest tests/unit/gateway/test_knowledge_api.py -v` (CRUD 全覆盖) |
| **回滚方案** | `git revert <commit>` |
| **证据** | API 契约测试通过 |
| **风险** | 依赖: K3-4 (Knowledge Write API) / 数据: CRUD 需 RBAC 权限控制 / 兼容: 新增 Admin API / 回滚: git revert |
| **决策记录** | 决策: Knowledge Admin API 通过 Gateway Admin 路由 / 理由: 知识管理需 RBAC + 审计 / 来源: 架构文档 05 Section 1 |

> 矩阵条目: G3-1 | V-x: X3-4 | V-fb: XF3-2 | M-Track: MM2-1 (企业媒体通过 /admin/knowledge/ 上传)

### TASK-G3-2: Skill API

| 字段 | 内容 |
|------|------|
| **目标** | 列出可用 Skill -> 触发执行 -> 返回结果 |
| **范围 (In Scope)** | `src/gateway/api/skills.py`, `tests/unit/gateway/test_skill_api.py` |
| **范围外 (Out of Scope)** | Skill 内部执行逻辑 / Brain Router / Knowledge 检索 / 前端 UI |
| **依赖** | Skill Layer (S3-3) |
| **兼容策略** | 新增 API 端点 |
| **验收命令** | `pytest tests/unit/gateway/test_skill_api.py -v` (Skill 列表非空) |
| **回滚方案** | `git revert <commit>` |
| **证据** | API 契约测试通过 |
| **风险** | 依赖: S3-3 (Skill 生命周期) / 数据: N/A / 兼容: 新增 API / 回滚: git revert |
| **决策记录** | 决策: Skill API 暴露列表+执行接口 / 理由: 前端需展示可用 Skill / 来源: 架构文档 05 Section 1 |

> 矩阵条目: G3-2 | V-x: X3-1 | V-fb: XF3-1

### TASK-G3-3: 内容安全检查 (05 Section 8)

| 字段 | 内容 |
|------|------|
| **目标** | 恶意内容被拦截 -> security_status 状态更新，拦截率 >= 99% |
| **范围 (In Scope)** | `src/gateway/security/content_check.py`, `tests/unit/gateway/test_content_check.py` |
| **范围外 (Out of Scope)** | Brain Prompt 清洗 / Skill 品牌合规 / 外部安全 API / 前端 UI |
| **依赖** | -- |
| **兼容策略** | 新增安全层 |
| **验收命令** | `pytest tests/unit/gateway/test_content_check.py -v` (拦截率 >= 99%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 安全检查单测通过 |
| **风险** | 依赖: N/A / 数据: security_status 三层拦截 (Gateway/Brain/LLMCallPort) / 兼容: 新增安全层 / 回滚: git revert |
| **决策记录** | 决策: LLM Gateway 层为内容安全最后防线 / 理由: 有害内容/PIPL 敏感信息/品牌安全三重检查 / 来源: 架构文档 05 Section 10 |

> 矩阵条目: G3-3

---

## Phase 4 -- 可靠性

### TASK-G4-1: SLO 指标 + 告警

| 字段 | 内容 |
|------|------|
| **目标** | API P95 延迟 < 500ms, 错误率 < 0.1% |
| **范围 (In Scope)** | `src/gateway/metrics/`, 告警规则文件 |
| **范围外 (Out of Scope)** | Prometheus 基础设施 / Grafana 看板 / Brain 性能 / 前端 UI |
| **依赖** | Prometheus (I4-1), OS4-2 |
| **兼容策略** | 纯新增指标 |
| **验收命令** | [ENV-DEP] `curl localhost:9090/api/v1/query?query=gateway_request_duration_seconds` |
| **回滚方案** | `git revert <commit>` |
| **证据** | P95 < 500ms, err < 0.1% |
| **风险** | 依赖: I4-1 (Prometheus) + OS4-2 / 数据: 指标数据需持续采集 / 兼容: 纯新增指标 / 回滚: git revert |
| **决策记录** | 决策: SLO -- API P95 < 500ms, err < 0.1% / 理由: 用户体验底线 / 来源: 架构文档 05 Section 5.7 |

> 矩阵条目: G4-1 | V-x: X4-1

### TASK-G4-2: HA 验证

| 字段 | 内容 |
|------|------|
| **目标** | 单节点故障 -> 自动切换 -> 用户无感知，切换时间 < 30s |
| **范围 (In Scope)** | 故障切换测试脚本 |
| **范围外 (Out of Scope)** | K8s 基础设施 / Brain 内部 / 数据库 HA / 前端 UI |
| **依赖** | -- |
| **兼容策略** | 纯测试 |
| **验收命令** | [ENV-DEP] `bash tests/chaos/failover_test.sh --timeout 30` staging: 故障切换测试 (切换时间 < 30s) |
| **回滚方案** | 不适用 |
| **证据** | 故障切换测试报告 |
| **风险** | 依赖: 部署环境 (K8s/Docker) / 数据: N/A -- 纯测试 / 兼容: 纯测试 / 回滚: 不适用 |
| **决策记录** | 决策: HA 验证 -- 单节点故障切换 < 30s / 理由: SaaS 服务可用性要求 / 来源: 架构文档 05 Section 6 |

> 矩阵条目: G4-2 | V-x: X4-2

### TASK-G4-3: 限流精细化 (per-org/per-user)

| 字段 | 内容 |
|------|------|
| **目标** | 不同租户不同限流阈值 |
| **范围 (In Scope)** | `src/gateway/middleware/rate_limit.py` (扩展), `tests/unit/gateway/test_rate_limit_multi.py` |
| **范围外 (Out of Scope)** | 租户配置管理 / Brain 意图理解 / Redis 基础设施 / 前端 UI |
| **依赖** | org_settings (I1-2) |
| **兼容策略** | 向后兼容 -- 未配置阈值使用默认值 |
| **验收命令** | `pytest tests/unit/gateway/test_rate_limit_multi.py -v` |
| **回滚方案** | `git revert <commit>` -- 回退为统一限流 |
| **证据** | 多租户限流单测通过 |
| **风险** | 依赖: I1-2 (org_settings) / 数据: 配置错误可导致误限流 / 兼容: 向后兼容, 未配置用默认值 / 回滚: git revert |
| **决策记录** | 决策: 精细化限流 per-org/per-user / 理由: 不同租户等级不同配额 (ADR-049) / 来源: ADR-049, 架构文档 05 Section 6 |

> 矩阵条目: G4-3

---

## Phase 5 -- API 生命周期

### TASK-G5-1: API 版本协商

| 字段 | 内容 |
|------|------|
| **目标** | Accept-Version header 路由到正确版本 |
| **范围 (In Scope)** | `src/gateway/middleware/versioning.py`, `tests/unit/gateway/test_versioning.py` |
| **范围外 (Out of Scope)** | API 业务逻辑 / Brain 意图理解 / 前端版本管理 / 废弃告警 |
| **依赖** | -- |
| **兼容策略** | 无 header 时默认最新版本 |
| **验收命令** | `pytest tests/unit/gateway/test_versioning.py -v` (路由准确率 100%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 版本路由单测通过 |
| **风险** | 依赖: N/A / 数据: N/A / 兼容: 无 header 默认最新 / 回滚: git revert |
| **决策记录** | 决策: Accept-Version header 版本协商 / 理由: API 生命周期管理, 平滑升级 / 来源: 架构文档 05 Section 1 |

> 矩阵条目: G5-1

### TASK-G5-2: API 废弃告警

| 字段 | 内容 |
|------|------|
| **目标** | 调用废弃 API -> 响应头含 Deprecation + Sunset |
| **范围 (In Scope)** | `src/gateway/middleware/deprecation.py`, `tests/unit/gateway/test_deprecation.py` |
| **范围外 (Out of Scope)** | API 业务逻辑 / Brain 意图理解 / 前端废弃提示 / 版本协商 |
| **依赖** | -- |
| **兼容策略** | 新增告警头，不影响 API 功能 |
| **验收命令** | `pytest tests/unit/gateway/test_deprecation.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 废弃头信息完整 |
| **风险** | 依赖: N/A / 数据: N/A / 兼容: 新增告警头, 不影响功能 / 回滚: git revert |
| **决策记录** | 决策: Deprecation + Sunset 响应头告警 / 理由: API 废弃需提前通知客户端 / 来源: 架构文档 05 Section 1 |

> 矩阵条目: G5-2 | V-x: X5-1

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
