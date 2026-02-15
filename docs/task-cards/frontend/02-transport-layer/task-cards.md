# 前端传输层 任务卡集

> 架构文档: `docs/frontend/02-transport-layer.md`
> 里程碑来源: `docs/governance/milestone-matrix-frontend.md`
> 影响门禁: `packages/api-client/**`, `apps/web/lib/ws/**` -> pnpm test + OpenAPI sync

---

## Phase 2 -- WebSocket + OpenAPI

### TASK-FW2-7: WebSocket 连接管理 (自动重连)

| 字段 | 内容 |
|------|------|
| **目标** | 断网 -> 恢复 -> 自动重连 -> 不丢消息，重连 P95 < 5s |
| **范围 (In Scope)** | `apps/web/lib/ws/connection.ts`, `tests/unit/web/ws.test.ts` |
| **范围外 (Out of Scope)** | 后端 WebSocket 实现 / Gateway 路由 / 数据库 / DevOps |
| **依赖** | Gateway WS (G2-2) |
| **兼容策略** | 新增 WS 管理模块 |
| **验收命令** | `pnpm test --filter web -- --grep ws` (重连 P95 < 5s) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 重连逻辑单测通过 |
| **风险** | 依赖: G2-2 (Gateway WS) / 数据: WS 消息不持久化, 重连需恢复 / 兼容: 新增 WS 管理模块 / 回滚: git revert |
| **决策记录** | 决策: WebSocket 自动重连 P95 < 5s / 理由: 用户体验要求断网恢复无感 / 来源: FE-02 Section 1 |

> 矩阵条目: FW2-7 | V-x: X2-2

### TASK-FW2-8: OpenAPI 类型同步

| 字段 | 内容 |
|------|------|
| **目标** | `pnpm openapi:generate` 后 diff 为空，前后端契约零漂移 |
| **范围 (In Scope)** | `packages/api-client/scripts/generate.ts`, `packages/api-client/src/generated/` |
| **范围外 (Out of Scope)** | 后端 OpenAPI Schema 定义 / Gateway API 实现 / 数据库 / DevOps |
| **依赖** | OpenAPI spec (G0-2) |
| **兼容策略** | 自动生成，不手动修改 |
| **验收命令** | `pnpm openapi:generate && git diff --exit-code packages/api-client/src/generated/` |
| **回滚方案** | `git checkout -- packages/api-client/src/generated/` |
| **证据** | diff 为空 |
| **风险** | 依赖: G0-2 (OpenAPI spec) / 数据: 类型同步不一致=前后端契约漂移 / 兼容: 自动生成, 不手动修改 / 回滚: git checkout |
| **决策记录** | 决策: OpenAPI 类型自动生成零漂移 / 理由: 前后端契约一致性强制保障 / 来源: FE-02 Section 2 |

> 矩阵条目: FW2-8 | V-fb: XF2-4

### TASK-FW2-9: SSE EventSource 客户端 + 事件分发

| 字段 | 内容 |
|------|------|
| **目标** | 建立 SSE 连接 -> 接收 6 种事件类型 (task_status_update / system_notification / budget_warning / knowledge_update / media_event / experiment_update) -> 分发到对应 UI handler |
| **范围 (In Scope)** | `apps/web/lib/sse/event-source.ts`, `apps/web/lib/sse/dispatcher.ts`, `tests/unit/web/sse.test.ts` |
| **范围外 (Out of Scope)** | 后端 SSE 实现 / Gateway 路由 / 数据库 / DevOps |
| **依赖** | Gateway SSE (G2-7), AuthProvider (FW1-2) |
| **兼容策略** | 新增 SSE 客户端模块；SaaS 模式走 BFF 代理，Private 模式直连 + token 参数 |
| **验收命令** | `pnpm test --filter web -- --grep sse` (6 种事件类型分发 + 重连逻辑 + 认证头) |
| **回滚方案** | `git revert <commit>` |
| **证据** | SSE 客户端单测通过 |
| **风险** | 依赖: G2-7 (Gateway SSE) + FW1-2 (AuthProvider) / 数据: SSE 事件丢失需重连补偿 / 兼容: 新增 SSE 客户端模块 / 回滚: git revert |
| **决策记录** | 决策: SSE EventSource 6 种事件分发 / 理由: 实时通知基座, SaaS/Private 双模式支持 / 来源: FE-02 Section 2 |

> 矩阵条目: FW2-9 (新增) | 前端消费方规格: FE-02 Section 2 | 后端生产方: G2-7

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
