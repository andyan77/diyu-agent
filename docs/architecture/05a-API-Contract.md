# 05a API Contract

> **所属层:** Gateway层 (05-Gateway 补充文档)
> **版本:** v1.0 (对应 05-Gateway v3.6)
> **验证标准:** 前端 FE-00~FE-08 Phase 0 + Phase 1 全部 API 需求有对应定义
> **引用关系:** 本文档被 05-Gateway层.md 引用; Schema 定义引用 06-基础设施层.md 和 08-附录.md
> **变更策略:** Expand-Contract; 新增端点需 ADR 审批; 废弃端点保留至少 2 个版本

---

## Section 1. User API (Data Plane, /api/v1/*)

> 面向全部已认证用户。无 org_tier/role 限制 (权限由 Gateway OrgContext 注入后各服务自行校验)。

### 1.1 Chat / Conversation

```
POST /api/v1/conversations
  Description: 创建会话
  Request:
    {
      model_id?: string,           -- 可选, 不传则使用 org default_model
      initial_message?: string     -- 可选, 创建并发送首条消息
    }
  Response 201:
    {
      conversation_id: UUID,
      session_id: UUID,
      created_at: ISO8601
    }
  Closes: H-8

POST /api/v1/conversations/{conversation_id}/messages
  Description: 发送消息 (REST fallback, 主路径走 WS)
  Request:
    {
      content: ContentBlock[],     -- 引用 08-附录 G.2.1 ContentBlock Schema v1.1
                                   -- text_fallback: 所有类型必填 (08-附录:236 权威定义)
      reply_to?: UUID              -- 引用某条消息
    }
  Response 202:
    {
      message_id: UUID,
      status: "queued"
    }
  Closes: H-8, C-4

GET /api/v1/conversations/{conversation_id}/messages
  Description: 历史消息列表
  Query: cursor?: string, limit?: number (default 50, max 200)
  Response 200:
    {
      messages: Message[],
      next_cursor: string | null
    }

GET /api/v1/conversations/{conversation_id}/events
  Description: 会话事件列表（含 tool_output，用于 Artifact 跨会话回溯）
  Query: type?: "message" | "tool_output" | "task", cursor?: string, limit?: number (default 50, max 200)
  Response 200:
    {
      events: Event[],
      next_cursor: string | null
    }
  Note: 前端跨会话 Artifact 查询统一使用 conversation_id（非 session_id）

GET /api/v1/conversations
  Description: 会话列表
  Query: status?: "active" | "archived", cursor?: string, limit?: number
  Response 200:
    {
      conversations: Conversation[],
      next_cursor: string | null
    }
  Closes: M-18

PATCH /api/v1/conversations/{conversation_id}
  Description: 会话更新 (归档/恢复/重命名)
  Request:
    {
      status?: "active" | "archived",
      title?: string                 -- 会话标题, 1~120 chars
    }
  Response 200:
    {
      conversation_id: UUID,
      title: string,
      status: string,
      updated_at: ISO8601
    }
  Closes: M-18

DELETE /api/v1/conversations/{conversation_id}
  Description: 永久删除会话
  Response 204: (no body)
  Closes: M-18
```

### 1.2 Memory

```
GET /api/v1/me/memories
  Description: 个人记忆列表
  Query: memory_type?: string, cursor?: string, limit?: number
  Response 200:
    {
      memories: MemoryItem[],
      next_cursor: string | null
    }

DELETE /api/v1/me/memories
  Description: 批量删除记忆 (无 path 参数)
  Request:
    {
      memory_ids: UUID[]
    }
  Response 202:
    {
      receipt_id: UUID,
      item_count: number,
      estimated_completion: ISO8601
    }
  Closes: M-12

DELETE /api/v1/me/memories/{memory_id}
  Description: 单条删除记忆
  Response 202:
    {
      receipt_id: UUID,
      item_count: 1,
      estimated_completion: ISO8601
    }
  Closes: M-12 (兼容前端 FE-04 当前用法)

GET /api/v1/me/memories/deletion/{receipt_id}
  Description: 删除进度查询（异步管线状态）
  Response 200:
    {
      receipt_id: UUID,
      status: "requested" | "verified" | "tombstoned" | "queued" | "processing" |
              "completed" | "failed" | "retry_pending" | "escalated",
      item_count: number,
      completed_count: number,
      estimated_completion: ISO8601
    }
  Note: 状态机与 01-Brain Section 3.1.1 对齐（tombstone 8 态 + retry_pending 重试态）

Note: 两种 DELETE 路径并存。Gateway 路由: 无 path 参数走批量，有 path 参数走单条。
      两种路径均为异步受理语义（202 + deletion_receipt），通过 receipt_id 查询进度。
```

### 1.3 Knowledge (User-facing)

```
GET /api/v1/knowledge/search
  Description: 知识检索
  Query: q: string, scope?: "personal" | "brand" | "global", top_k?: number (default 5)
  Response 200:
    {
      results: [
        {
          chunk_id: UUID,
          content: string,
          score: number,
          source: string
        }
      ]
    }
```

### 1.4 Media Upload (Three-Step Protocol)

> 路径严格对齐 05-Gateway Section 8.1 (lines 356-359)。

```
POST /api/v1/media/upload/init
  Description: Stage 0 -- 初始化上传
  Request:
    {
      filename: string,
      content_type: string,        -- MIME type
      size: number,                -- 字节数
      checksum_sha256: string      -- 客户端计算的 SHA-256
    }
  Response 201:
    {
      media_id: UUID,
      upload_url: string,          -- presigned URL (短 TTL)
      security_status: "pending"
    }
  Note: Stage 1 (直传) 客户端使用 upload_url 直传至 Object Storage,
        非 Gateway 路由, 不在此列。
  Closes: H-13

POST /api/v1/media/upload/complete
  Description: Stage 2 -- 确认上传完成, 触发安全扫描
  Request:
    {
      media_id: UUID
    }
  Response 200:
    {
      media_id: UUID,
      security_status: "scanning"
    }
  Note: 两阶段语义:
        - 同步快速检查（checksum/magic-bytes/基础 AV）失败会直接返回 4xx
        - 同步检查通过后进入异步深度扫描，返回 scanning；后续通过 SSE media_event 推送状态
  Closes: H-13

GET /api/v1/media/{media_id}/url
  Description: 获取 presigned 访问 URL (短 TTL)
  Response 200:
    {
      url: string,
      expires_at: ISO8601
    }

DELETE /api/v1/media/{media_id}
  Description: 个人媒体删除
  Response 204: (no body)

security_status 6态状态机: pending | scanning | safe | rejected | quarantined | expired
引用 05-Gateway Section 8.3 (ADR-051)
Closes: H-13, H-14
```

### 1.5 Usage & Budget

```
GET /api/v1/me/usage
  Description: 个人用量概览
  Response 200:
    {
      tokens_used: number,
      budget_remaining_pct: number,  -- 0-100
      points_balance: number,        -- 当前积分余额（并入 usage 响应，避免额外请求）
      period_start: ISO8601,
      period_end: ISO8601
    }

Note: X-Budget-Remaining header 在每次 REST 响应中附带 (见 Section 7)
Budget 告警统一口径:
  - Header 预警: X-Budget-Remaining < 10
  - SSE 预警: budget_warning threshold_pct = 80 | 95 | 100
  - 前端本地体验预警: <20 可提示“预算偏低”（非后端告警阈值）
Closes: H-2
```

### 1.6 Organization (Data Plane)

```
GET /api/v1/organizations
  Description: 当前用户可访问的组织列表
  Response 200:
    {
      organizations: [
        {
          org_id: UUID,
          org_name: string,
          org_tier: OrgTier,
          role: string
        }
      ]
    }
  Note: 非 admin 路径。regional_agent 等无 admin 权限的角色使用此接口。
  Closes: H-11
```

### 1.7 Auth Helper (Optional, Private Deployment)

```
GET /api/v1/auth/ws-token
  Description: 获取短时 WS token（Private 模式可选；默认可直接复用 access_token）
  Response 200:
    {
      ws_token: string,
      expires_at: ISO8601
    }
```

---

## Section 2. Admin API (Control Plane, /api/v1/admin/*)

> 权限要求: 全部需要 org_tier in [platform, brand_hq] 且 role in [owner, admin]
> (TierGate 规则引用 FE-03 Section 4.1)

### 2.1 Organization Management

```
GET    /api/v1/admin/organizations               -- 管理视图组织树
POST   /api/v1/admin/organizations               -- 创建子组织
PATCH  /api/v1/admin/organizations/{org_id}      -- 更新组织信息
DELETE /api/v1/admin/organizations/{org_id}      -- 删除组织

Organization status enum: active | suspended | archived
引用 06-基础设施层.md line 24 (SSOT)
Closes: M-9
```

### 2.2 Member Management

```
GET    /api/v1/admin/members                     -- 成员列表
POST   /api/v1/admin/members/invite              -- 邀请成员
PATCH  /api/v1/admin/members/{member_id}/role    -- 变更角色
DELETE /api/v1/admin/members/{member_id}         -- 移除成员
```

### 2.3 Settings

```
GET /api/v1/admin/effective-settings
  Description: 合并继承后的有效配置 (只读)
  Response 200:
    {
      org_id: UUID,
      org_name: string,
      org_tier: OrgTier,
      settings: {
        "<key>": {
          value: any,                    -- 当前有效值
          source: "self" | "inherited" | "default",
          source_org_id: UUID | null,    -- source=inherited 时为父级 org_id
          source_org_name: string | null,
          constraint: "LAW" | "RULE" | "BRIDGE",
          is_locked: boolean,            -- BRIDGE 锁定标记
          admin_ui: "readonly" | "control" | "hidden"
        }
      }
    }
  Settings key 完整列表: 引用 06-基础设施层.md Section 1.5 OrganizationSettings (~25 keys, 7 groups)
  前端消费注: FE-06 Section 4.11 effective-settings 面板直接渲染此响应
  Closes: H-12 [裁决]

PUT /api/v1/admin/settings
  Description: 修改本级设置 (仅 RULE/BRIDGE 级别可修改)
  Request:
    {
      settings: { "<key>": any }
    }
  Response 200:
    {
      updated_keys: string[],
      rejected_keys: [
        { key: string, reason: string }
      ]
    }
  Closes: M-8
```

### 2.4 Knowledge Management (Admin)

```
POST   /api/v1/admin/knowledge/import            -- 导入知识
DELETE /api/v1/admin/knowledge/{knowledge_id}    -- 删除知识条目
GET    /api/v1/admin/knowledge/visibility         -- 知识可见性配置
  Query: scope?: "brand" | "region" | "store"
  Response 200:
    {
      items: [
        {
          knowledge_id: UUID,
          title: string,
          visibility: "global" | "brand" | "region" | "store",
          inheritable: boolean,          -- 引用 02-Knowledge Section 3.2
          override_allowed: boolean,
          owner_org_id: UUID,
          owner_org_name: string
        }
      ],
      total: number,
      cursor?: string
    }
  Closes: M-20

企业媒体 API (引用 05-Gateway Section 8.1 lines 364-368):
POST   /api/v1/admin/knowledge/media/upload/init
POST   /api/v1/admin/knowledge/media/upload/complete
GET    /api/v1/admin/knowledge/media/{media_id}/url
DELETE /api/v1/admin/knowledge/media/{media_id}
```

### 2.5 Model Registry

```
GET    /api/v1/admin/models                      -- 可用模型列表
POST   /api/v1/admin/models                      -- 注册新模型 [Phase 2 reserved]
PATCH  /api/v1/admin/models/{model_id}           -- 启用/禁用/配置 [Phase 2 reserved]
DELETE /api/v1/admin/models/{model_id}           -- 移除模型 [Phase 2 reserved]
Closes: M-17 [Phase 2 reserved]
```

### 2.6 Experiment Engine

```
POST   /api/v1/admin/experiments                 -- [Phase 2 reserved]
GET    /api/v1/admin/experiments                 -- [Phase 2 reserved]
PATCH  /api/v1/admin/experiments/{experiment_id} -- [Phase 2 reserved]
Closes: M-21 [Phase 2 reserved]
```

### 2.7 Content Review Pipeline

```
POST   /api/v1/admin/content/submissions         -- [Phase 2 reserved] 跨组织内容提交
GET    /api/v1/admin/content/submissions         -- [Phase 2 reserved] 提交列表
PATCH  /api/v1/admin/content/submissions/{id}    -- [Phase 2 reserved] 审核 approve/reject
Closes: M-4 [Phase 2 reserved]
```

### 2.8 Billing

```
GET /api/v1/admin/billing/usage                  -- 用量统计
GET /api/v1/admin/billing/invoices               -- 账单列表
[Phase 2 reserved] -- 完整计费模型
Closes: M-13 [Phase 2 reserved]
```

### 2.9 Onboarding

```
GET /api/v1/admin/onboarding-status              -- [Phase 2 reserved]
PUT /api/v1/admin/onboarding-status              -- [Phase 2 reserved]
Closes: M-19 [Phase 2 reserved]
```

### 2.10 Branding

```
GET /api/v1/admin/branding                       -- [Phase 2 reserved]
PUT /api/v1/admin/branding                       -- [Phase 2 reserved]
org_settings.branding 扩展字段: 引用 06-基础设施层.md
Closes: L-8, B5
```

---

## Section 3. Platform-Ops API (/api/v1/platform-ops/*)

> 权限要求: org_tier === 'platform' 且 role === 'owner'

```
GET    /api/v1/platform-ops/tenants              -- 租户列表
  Response 200: { items: [{ tenant_id, org_name, org_tier, status, created_at, member_count }], total, cursor? }

POST   /api/v1/platform-ops/tenants              -- 创建租户
  Request: { org_name: string, org_tier: OrgTier, parent_org_id?: UUID, admin_email: string }
  Response 201: { tenant_id: UUID, org_id: UUID, status: "active" }

PATCH  /api/v1/platform-ops/tenants/{tenant_id}  -- 更新租户配置
  Request: { status?: "active" | "suspended", org_tier?: OrgTier }
  Response 200: { tenant_id, status, updated_at }

GET    /api/v1/platform-ops/audit-logs           -- 审计日志
  Query: actor_id?, action?, resource_type?, since?: ISO8601, cursor?, limit?
  Response 200: { items: [{ log_id, actor_id, actor_name, action, resource_type, resource_id, detail, created_at }], total, cursor? }

GET    /api/v1/platform-ops/global-settings      -- 全局 LAW 级设置 (只读)
  Response 200: { settings: { "<key>": { value, constraint: "LAW" } } }

PUT    /api/v1/platform-ops/global-settings      -- 修改 LAW 级设置
  Request: { settings: { "<key>": any } }
  Response 200: { updated_keys: string[], effective_at: ISO8601 }

GET    /api/v1/platform-ops/billing/overview     -- 平台级计费概览（billing-global）
  Response 200: {
    period_start: ISO8601,
    period_end: ISO8601,
    total_revenue: number,
    total_cost: number,
    active_tenants: number,
    overdue_tenants: number
  }

GET    /api/v1/platform-ops/billing/tenants      -- 租户计费明细列表
  Query: cursor?, limit?, status?: "active" | "overdue"
  Response 200: {
    items: [{ tenant_id, org_name, usage_cost, subscription_fee, points_balance, status }],
    total: number,
    cursor?: string
  }

Closes: M-22
```

---

## Section 4. WS Message Schema (/ws/*)

### 4.1 连接建立

```
URL: /ws/conversations/{conversation_id}

认证方式: 首条消息 JSON 认证 (非 URL 参数)
  -> Client sends:  { type: "auth", token: "<jwt_or_ws_token>" }
  -> Server responds (success): { type: "auth_result", success: true, session_id: "..." }
  -> Server responds (failure): { type: "auth_result", success: false, error: "..." }
     + close(4001 Unauthorized)

Note: SaaS 模式 token 通过 BFF /api/auth/ws-token 获取;
      Private 模式复用 access_token，或调用 GET /api/v1/auth/ws-token（Section 1.7，可选）
ID 语义:
  conversation_id: 持久化对话主键（URL 路由与深链使用）
  session_id: WS 连接级会话标识（短生命周期，由 auth_result 返回）
Closes: C-1 [裁决: 后端侧落盘完成; 前端侧 FE-02 WS 握手变更为前端 backlog]
```

### 4.2 消息类型

> 命名 LAW (引用 05-Gateway:302-305)。禁止新增 assistant_chunk / assistant_complete (v1/v2 废弃命名)。

```
Client -> Server:

  user_message:
    {
      type: "user_message",
      content: ContentBlock[],         -- 引用 08-附录 G.2.1 (text_fallback 所有类型必填)
      reply_to?: UUID,                 -- 引用消息 ID
      request_id: UUID                 -- 幂等键
    }

  pong:
    { type: "pong" }

Server -> Client:

  ai_response_chunk:
    {
      type: "ai_response_chunk",
      message_id: UUID,
      delta: string,                   -- 流式文本增量
      content_version: number,         -- WS 消息级版本号 (Schema 版本协商, ADR-050 三层分离)
      finish_reason?: "stop" | "length" | "content_filter",
      suggested_actions?: SuggestedAction[]  -- [Phase 3 reserved] 上下文建议动作，缺失时前端降级静态建议
    }
    Closes: M-25

  tool_output:
    {
      type: "tool_output",
      message_id: UUID,
      skill_name: string,
      status: "running" | "success" | "partial" | "error" | "rate_limited",
                                         -- 对齐 03-Skill:62 SkillResult Schema v1
                                         -- rate_limited: Skill 整体被限流 (外部 API 配额耗尽)
                                         -- partial: Tool 级限流但 Skill 部分成功
      output?: any,
      text_summary?: string            -- 人类可读摘要
    }

  task_complete:
    {
      type: "task_complete",
      task_id: UUID,
      result: any
    }

  error:
    {
      type: "error",
      error: ErrorResponse             -- 引用 Section 6 Error Format
    }

  ping:
    { type: "ping" }

Closes: C-2
```

```
SuggestedAction (Phase 3 reserved):
  {
    id: string,
    label: string,
    intent: string,
    priority: number,
    expires_at?: ISO8601
  }
```

### 4.3 心跳与断线检测

```
协议: 双向 ping/pong

参数 [裁决]:
  ping_interval: 30s
  disconnect_threshold: 2 (count-based, 连续 2 次未收到 pong)
  disconnect_timeout: ~60s (= interval x threshold)

服务端行为: 连续 2 次 missed pong -> 清理 session -> 关闭连接
客户端建议: 前端检测 2 missed pings (非时间阈值) -> RECONNECTING 状态

Closes: M-16 [裁决]
```

### 4.4 重连策略

```
最大重试: 10 次 (引用 05-Gateway Section 7.1)
退避策略: 指数退避 1s -> 2s -> 4s ... 最大 30s
terminal 状态: FAILED (超过 max attempts)
session 保持: 断线后 5 分钟内可恢复 (05-Gateway:342)
```

---

## Section 5. SSE Event Schema (/events/*)

### 5.1 连接

```
SaaS 模式:   /api/events/* (BFF 路由; Cookie 自动附带, BFF 转换为 auth header)
Private 模式: /events/?token=<access_token> (直连)

Note: SaaS 模式通过 BFF 代理，与 REST 认证链一致。无需额外 token 获取方法。
      (引用 FE-02:138, FE-03:111-116, C-3 RESOLVED)
```

### 5.2 Event Types

```
event: task_status_update
  data: {
    task_id: UUID,
    status: "pending" | "running" | "completed" | "failed",
    progress_pct?: number,
    result?: any
  }

event: system_notification
  data: {
    notification_id: UUID,
    level: "info" | "warning" | "critical",
    title: string,
    body: string,
    action_url?: string
  }

event: budget_warning
  data: {
    org_id: UUID,
    threshold_pct: 80 | 95 | 100,
    budget_remaining_pct: number,
    period_end: ISO8601
  }
  Closes: H-2, M-23

event: knowledge_update
  data: {
    knowledge_id: UUID,
    action: "created" | "updated" | "deleted",
    scope: string
  }

event: media_event
  data: {
    media_id: UUID,
    subtype: "media.upload_initiated" | "media.upload_completed" | "media.upload_expired" |
             "media.scan_completed" | "media.rejected" | "media.deletion_requested" |
             "media.deletion_completed",
    payload: { ... }                   -- subtype 权威定义见 06 Section 6.3; 传输语义见 05-Gateway Section 8
  }
  Closes: M-26, H-14

event: experiment_update               -- [Phase 2 reserved]
  data: {
    experiment_id: UUID,
    status: string,
    traffic_allocation?: number
  }
```

### 5.3 Event-to-System-Event Mapping

```
引用 08-附录 G.3 event types table (10 system events)
SSE 是这些事件的前端传输通道; 内部事件通过 event_outbox -> SSE Gateway 投递
映射规则: domain_event.type -> SSE event name (1:1 映射)
v3.6 新增: media_event (7 subtypes) 作为单一 SSE event 类型, 通过 subtype 字段区分

Closes: M-7, H-9
```

---

## Section 6. Error Response Format

### 6.1 Standard Error Response

```
{
  error: {
    code: string,                      -- 机器可读 (如 "rate_limited", "unauthorized")
    message: string,                   -- 人类可读描述
    details?: any,                     -- 结构化补充信息
    request_id: UUID,                  -- 请求追踪 ID (全链路 trace_id)
    retry_after?: number               -- 429 时必填 (秒)
  }
}
```

### 6.2 HTTP Status 语义

```
400 Bad Request         -- 请求格式错误
401 Unauthorized        -- 认证失败/过期
402 Payment Required    -- 预算/额度不足（Token 或 Tool 预算耗尽）
403 Forbidden           -- 权限不足 (TierGate / PermissionGate)
404 Not Found           -- 资源不存在
409 Conflict            -- 版本冲突 (content_version mismatch)
422 Unprocessable       -- 业务规则违反
429 Rate Limited        -- 限流 (必含 Retry-After + X-RateLimit-* headers)
500 Internal Error      -- 服务端错误
503 Service Unavailable -- 降级中 (含 degraded_reason)
```

### 6.3 重试策略

> 对齐 05-Gateway Section 6.3 (lines 268-271)

```
429 响应:
  遵守 Retry-After 头
  指数退避: 1s -> 2s -> 4s (最大 30s)
  最多重试 3 次

5xx 响应:
  幂等请求 (GET / PUT / DELETE): 指数退避重试, 最多 3 次
  非幂等请求 (POST): 仅在携带 Idempotency-Key header 时重试

402 响应:
  不重试 (预算问题, 需人工处理)

Closes: M-15
```

### 6.4 degraded_reason 枚举（v1）

```
degraded_reason（Error.details 或 WS metadata）:
  knowledge_stores_unavailable
  knowledge_timeout
  pgvector_unavailable
  query_rewrite_failed
  budget_allocator_fallback
  llm_fallback
  media_security_blocked

兼容策略:
  新增枚举值 = Expand 兼容变更
  前端收到未知值: 记录日志 + 不阻断主流程
```

### 6.5 Budget Alert 统一定义

```
Budget 告警体系统一规范（跨端权威定义）:

1. Token 预算告警（SSE budget_warning 事件）:
   +-- 80% 消耗: threshold_pct=80, level="info"      -- 前端: "Monthly quota running low"
   +-- 95% 消耗: threshold_pct=95, level="warning"    -- 前端: "Monthly quota approaching limit"
   +-- 100% 消耗: threshold_pct=100, level="critical" -- 前端: "Monthly quota exhausted"
   触发层: Gateway TokenBillingService (06 Section 3)
   投递: SSE budget_warning 事件 (Section 5.2)

2. Token 预算 HTTP 响应头:
   +-- X-Budget-Remaining < 10%: Gateway 在每个 LLM 响应中附带 (05-Gateway Section 6.2)
   +-- X-Budget-Remaining = 0: 拒绝请求, 返回 402
   Note: 10% 是 Gateway 附带响应头的阈值，非前端告警阈值

3. Tool 预算告警:
   +-- Tool budget < 20%: 前端本地计算, 展示 "Tool budget running low"
   +-- 数据源: X-Tool-Budget-Remaining 响应头
   Note: Tool 预算独立于 Token 预算 (06 Section 3 dual-budget model)

各层职责:
  Gateway (05-Gateway):  触发 SSE 事件 + 附带 HTTP 响应头 (X-Budget-Remaining)
  SSE (05a Section 5.2): 投递 budget_warning (80/95/100 三档)
  前端 (FE-04):          消费 SSE 事件 + 响应头, 展示对应 UI 提示
```

---

## Section 7. Standard Headers

### 7.1 请求头

```
Gateway 自动注入:
  X-Request-ID: UUID                   -- 全链路追踪
  X-Org-ID: UUID                       -- 当前组织 (OrgContext.org_id)
  X-Org-Tier: OrgTier                  -- 当前组织层级

客户端可选携带:
  Idempotency-Key: UUID                -- POST 请求幂等键 (携带时 5xx 可重试)
```

### 7.2 响应头

```
X-RateLimit-Limit: number             -- QPS 上限
X-RateLimit-Remaining: number         -- 剩余配额
X-RateLimit-Reset: timestamp          -- 重置时间 (Unix epoch seconds)
X-Budget-Remaining: number            -- Token 预算剩余百分比 (0-100)
X-Tool-Budget-Remaining: number       -- 工具调用预算剩余 (引用 06-Infrastructure)

Closes: H-2, M-23
```

### 7.3 DEPLOY_MODE

```
非 header 传递; 前端读取环境变量 / 构建注入
合法值: "saas" | "private" | "hybrid"
形式化定义: 见 07-部署与安全.md Section 1.1

Closes: H-10
```

---

> **验证方式:** 1) 每个 Section 1/2/3 端点至少被一个 FE 文档引用; 2) Schema 引用 06/08 不复制 (防 drift); 3) 55 gaps 全量 disposition 无遗漏; 4) 命名 LAW 约束 (Section 4.2) 与 05-Gateway:302-305 一致; 5) 媒体路径与 05-Gateway:356-359 字符级一致。
>
> **FE 引用校验结果 (v4.4):** 87 API surfaces 中 64 有明确 FE 消费者 (73.6%)。23 缺失中 17 为 Phase 2/3 reserved (FE 已有 skeleton/backlog)；6 为隐含消费 (media URL/delete 由图片渲染隐含调用; branding Phase 3; content submissions Phase 2; X-Tool-Budget-Remaining 已由 budget_warning SSE 覆盖)。无未追踪的遗漏。
