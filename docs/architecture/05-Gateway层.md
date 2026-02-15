# Gateway 层（接入 + 认证 + LLM 网关）

> **所属层:** 网关层  
> **版本:** v3.6
> **验证标准:** 协议适配、认证鉴权、LLM 路由/Fallback、限流、WebSocket、内容安全各自可独立测试  

---

## 1. 接入协议

| 协议 | 路径 | 用途 |
|------|------|------|
| WebSocket | /ws/conversations/{conversation_id} | 实时对话（主交互方式） |
| REST (用户) | /api/v1/* (不含 /admin 子路径) | 用户端程序化调用 |
| REST (管理) | /api/v1/admin/* | 管理端操作（组织/成员/配置/实验/计费等） |
| SSE | /events/* | 事件推送 |

> **[裁决]** WebSocket 倾向按会话连接。

---

## 2. API 版本管理

> **[裁决]** URI 路径版本 /api/v1/。Alembic 做数据库迁移，expand/contract 模式。

---

## 3. 认证鉴权

```
Step 1: Token 验证（JWT）
Step 2: 组织上下文解析 -> 计算 org_chain -> 合并 Settings -> 设置 RLS session
Step 3: 权限校验（RBAC + Org Scope）
```

> **[裁决]** 初期 JWT 自建。AuthProvider 接口抽象，后期可接 SSO。

---

## 4. OrganizationContext

```
OrganizationContext:
+-- user_id, org_id, org_tier
+-- org_path: LTREE
+-- org_chain: List[UUID]
+-- brand_id, role, permissions
+-- org_settings（含 is_locked 过滤后）
+-- model_access
```

OrganizationContext 在 Gateway 层组装后，作为请求上下文贯穿 Brain -> Skill -> Tool -> Knowledge Stores 全链路。

### 4.1 API 分区与路由规则

> **[v3.2.1 新增]** 用户 API 和管理 API 共享同一 Gateway，但在中间件处理上有明确差异。

```
路由优先级: 最长前缀优先匹配

/api/v1/admin/* -> 管理 API 分区 [CP - Control Plane]
  中间件: JWT 认证 -> OrgContext 组装 -> RBAC 权限校验(需 *.manage 类权限码)
  消费者: Admin Console
  类型: 管理类操作（组织/成员/配置/实验/计费），v1 逻辑分离

/api/v1/*       -> 用户 API 分区 [DP - Data Plane]（匹配所有非 /admin 路径）
  中间件: JWT 认证 -> OrgContext 组装
  消费者: Frontend UI
  类型: 对话类操作，v1 逻辑分离

  用户端点明细（v3.5 新增）:
  +-- DELETE /api/v1/me/memories  -> 用户发起记忆删除（触发 01 Section 3.1.1 删除管线）
      权限: 仅限本人（user_id 所有权校验）
      返回: 202 + deletion_receipt（receipt_id, item_count, estimated_completion）

/ws/conversations/{conversation_id} -> WebSocket 分区
  认证: 首条消息携带 token
  消费者: Frontend UI

/events/*       -> SSE 分区
  认证: 查询参数或 Header 携带 token
  消费者: Frontend UI / Admin Console
```

> **设计约束:** 管理 API 和用户 API 的 RBAC 中间件共享同一权限码体系（见 06 Section 1.3 权限码映射表），区别在于管理 API 强制要求 `*.manage` 类权限码。

### 4.2 OrganizationContext 语义契约 v1

> **[v3.3 新增]** OrganizationContext 是 OrgContext Port 的输出结构，在 Gateway 组装后贯穿全链路。以下定义构成 schema v1，变更须遵守兼容规则（见 ADR-033）。

```
OrganizationContext Schema v1:

字段                 | 类型              | 必填 | 空值语义                          | 说明
user_id              | UUID              | YES  | 不允许为空                         | 当前请求用户
org_id               | UUID              | YES  | 不允许为空                         | 当前组织 ID
org_tier             | String            | YES  | 不允许为空                         | "platform" | "brand_hq" | "brand_dept" | "regional_agent" | "franchise_store"
                     |                   |      |                                    | v3.6 对齐 06 Section 1.1 SSOT tier 定义 (ADR-049)
                     |                   |      |                                    | Expand-Contract: v3.6 新增枚举值，旧值 2 minor versions 后移除
org_path             | LTREE             | YES  | 不允许为空                         | 组织路径（PostgreSQL ltree）
org_chain            | List[UUID]        | YES  | 不允许为空（至少含自身）             | 从根到当前组织的 ID 链
brand_id             | UUID              | NO   | null = 平台级用户（无品牌归属）      | 所属品牌 ID
role                 | String            | YES  | 不允许为空                         | 当前用户在当前组织的角色
permissions          | Set[String]       | YES  | 空 Set = 无任何权限                 | 权限码集合
org_settings         | Object            | YES  | 不允许为空                         | 合并后的组织配置（含 is_locked 过滤）
model_access         | Object            | YES  | 不允许为空                         | 模型访问配置（allowed_models, default_model, budget）
experiment_context   | Object            | NO   | null = 当前无实验分流               | Experiment Engine 分流信息（可选）

org_settings 子结构（关键字段）:
+-- content_policy          | String  | YES  | "relaxed" | "standard" | "strict"
+-- review_flow             | Object  | YES  | 结构见 06 Section 1.5
|   +-- auto_compliance_check   | Boolean | YES | 自动合规检查
|   +-- require_regional_review | Boolean | YES | 是否要求区域审核
|   +-- require_hq_review       | Boolean | YES | 是否要求总部审核
+-- budget_monthly_tokens   | Integer | YES  | 0 = 无预算限制（平台级）
+-- media_config            | Object  | YES  | v3.6 新增: 多模态媒体治理配置 (Loop E)
|   +-- allowed_media_types | List[String] | YES | 允许的媒体类型 (交集继承)
|   +-- file_size_limit     | Integer      | YES | 单文件大小上限 (bytes)
|   +-- media_quota         | Integer      | YES | 组织媒体存储总配额 (bytes)
+-- is_locked 字段          | Boolean | 每个 RULE 配置项均有  | true = 对子组织产生 LAW 效果
完整 OrganizationSettings key 列表见 06 Section 1.5（本节仅列关键字段，避免重复定义）。

model_access 子结构:
+-- allowed_models          | List[String] | YES  | 空 List = 无可用模型（应降级报错）
+-- default_model           | String       | YES  | 不允许为空
+-- budget_monthly_tokens   | Integer      | YES  | 同 org_settings 中的值
+-- budget_tool_amount      | Float        | YES  | v3.6 新增: 工具费用预算 (见 06 Section 1.5)

experiment_context 子结构（可选）:
+-- assignments             | Object       | NO   | key = dimension, value = variant
+-- updated_at              | DateTime     | NO   | 最近一次分流更新时间

兼容规则: 同 KnowledgeBundle（见 02 Section 5.4.1 / ADR-033）
```

---

## 5. LLM Gateway

### 5.1 设计定位

LLM Gateway 是 LLMCall Tool 的底层实现，也是基础设施层的核心组件。

```
职责: 模型注册 / 统一调用接口 / 租户级访问控制 / Fallback / Token 记录
不做: 意图理解 / Prompt 组装 / 内容审核
```

### 5.2 Model Registry

```
ModelDefinition:
+-- model_id, display_name, provider
+-- capabilities: Set[String]     {"text", "vision", "code", "multimodal"}
+-- tier: basic | standard | premium
+-- pricing: { input_per_1k, output_per_1k }
+-- endpoint_config: { base_url, api_key_ref, timeout }
+-- context_window, max_output_tokens
+-- status: active | deprecated | disabled
```

### 5.3 模型访问控制

> **[裁决]** 通过 OrganizationSettings.model_access 控制。上级 allowed_models 是下级上限。

```
模型访问判定:
  org_settings.model_access.allowed_models (子组织只能是父组织子集)
  -> 取交集计算当前组织可用模型
  -> default_model 为首选
  -> budget_monthly_tokens 控制消耗上限
```

### 5.4 路由与 Fallback

> **[裁决]** v1 只做租户级静态路由 + Fallback 链。语义路由和成本路由预留接口。

```
断路器: CLOSED -> OPEN（5分钟内失败5次）-> HALF_OPEN（5分钟后探测）
降级链: 主模型 -> 备选模型 -> 降级模型 -> 优雅错误提示
```

### 5.5 底层实现

> **[裁决]** 集成 LiteLLM 作为 Python SDK。不独立部署代理服务。后期可替换。

### 5.5.1 Provider 格式映射（LLMCallPort -> LiteLLM）

```
LLMCallPort 统一入参:
  prompt: string                    -- 系统/用户 prompt
  content_parts: ContentBlock[]     -- 多模态内容块（引用 08-附录 G.2.1）
  model_id: string                  -- Gateway Model Registry 注册的 model_id
  parameters: { temperature, max_tokens, ... }

LiteLLM SDK 统一转换层（Gateway 内部实现，不暴露到 Port 接口）:

  OpenAI 兼容格式（GPT-4o / DeepSeek / Qwen-Plus 等）:
    messages: [
      { role: "system", content: prompt },
      { role: "user", content: content_parts_to_openai(content_parts) }
    ]
    content_parts_to_openai 映射:
      ContentBlock.type = "text"  -> { type: "text", text: block.text }
      ContentBlock.type = "image" -> { type: "image_url", image_url: { url: presigned_url } }
      ContentBlock.type = "audio" -> 降级为 text_fallback（OpenAI 不支持音频输入时）
      ContentBlock.type = "document" -> 降级为 text_fallback

  Anthropic 格式（Claude 系列）:
    system: prompt
    messages: [
      { role: "user", content: content_parts_to_anthropic(content_parts) }
    ]
    content_parts_to_anthropic 映射:
      ContentBlock.type = "text"  -> { type: "text", text: block.text }
      ContentBlock.type = "image" -> { type: "image", source: { type: "url", url: presigned_url } }
      ContentBlock.type = "document" -> { type: "document", source: { type: "url", url: presigned_url } }

  降级规则 (LAW):
    +-- 所有 ContentBlock 必须有 text_fallback（08-附录 G.2.1 强制）
    +-- 当目标模型不支持某 ContentBlock.type 时，使用 text_fallback 替代
    +-- 降级时记录 degraded_reason: "content_type_unsupported"
    +-- LiteLLM SDK 已内置部分格式转换，Gateway 仅补充 ContentBlock -> provider 的映射层

Note: 具体映射实现由 LiteLLM SDK 版本决定。本规范定义语义映射规则，不锁定 SDK API。
      BYOM (Section 5.6) 自部署模型统一走 OpenAI 兼容格式。
```

### 5.6 BYOM（自部署模型）

> **[裁决]** 支持。企业注册自有 vLLM/Ollama 端点，数据不出客户网络。

---

### 5.7 Prometheus Exporter

> **[v3.5 新增]** Gateway 暴露 /metrics 端点供 Prometheus 采集 SLI 指标。

```
端点: GET /metrics
认证: 内部网络访问（不走 JWT 认证，通过网络策略限制）

暴露指标:
+-- 7 项 Memory Quality SLI（见 01 Section 2.3.2）
+-- LLM Gateway 指标: 请求延迟/错误率/模型调用量
+-- 限流指标: 429/402 响应计数
+-- WebSocket 指标: 活跃连接数/重连率

v3.6 多模态指标扩展:
+-- media_upload_success_rate: 媒体上传成功率 (按 org_tier 分维度)
+-- media_security_rejection_rate: 安全扫描拒绝率 (Stage 1 同步 + Stage 2 异步分别统计)
+-- media_upload_expiration_rate: 上传超时过期率 (pending 超 1h 回收比例)
+-- media_tool_latency_seconds: 多模态 Tool 调用延迟 (histogram, P50/P99)
+-- media_storage_bytes_total: Object Storage 存储量 (按 org_tier + media_domain 统计)
+-- media_storage_bandwidth_bytes: Object Storage 带宽 (上传/下载分维度)
+-- media_scan_queue_depth: 安全扫描队列深度 (Stage 2 异步 Worker 待处理量)
+-- media_scan_processing_latency_seconds: 安全扫描处理延迟 (histogram)
+-- media_quota_deviation_ratio: 配额预扣 vs 实际使用偏差率 (init 预扣 - complete 实际 / 预扣)

采集间隔: 15s（Prometheus 默认 scrape_interval）
```

---

## 6. 限流与重试

> **[v3.2 新增]** 限流是 Gateway 的核心防护职责。三级限流覆盖租户、用户、API 粒度；Token 预算作为业务层控制独立于 QPS 限流。

### 6.1 三级限流

```
Level 1: 租户级 (tenant_id)
  +-- QPS 上限（按套餐 tier 配置）
  +-- 并发连接数上限
  +-- 超限返回 429 Too Many Requests

Level 2: 用户级 (user_id)
  +-- QPS 上限（防止单用户占满租户配额）
  +-- 超限返回 429 Too Many Requests

Level 3: API 粒度
  +-- 按 endpoint 分类配置（对话接口 vs 管理接口）
  +-- 写操作比读操作限制更严格
  +-- 超限返回 429 Too Many Requests
```

### 6.2 Token 预算控制

```
Token 预算与 QPS 限流是两个独立维度:

+-- QPS 超限: 429 Too Many Requests（请求频率过高）
+-- Token 预算耗尽: 402 Payment Required（配额/预算不足）

Token 预算判定流程:
  请求到达 -> 检查 org_settings.budget_monthly_tokens
    -> 剩余充足: 放行，异步扣减（精确扣减在 LLM 响应后）
    -> 即将耗尽（< 10%）: 放行 + 返回 X-Budget-Remaining 头
    -> 已耗尽: 拒绝，返回 402

响应头:
+-- X-RateLimit-Limit / X-RateLimit-Remaining / X-RateLimit-Reset（QPS）
+-- X-Budget-Remaining（Token 预算剩余百分比）
```

### 6.3 客户端重试约定

```
重试策略（写入 API 文档，客户端遵守）:

429 响应:
+-- 遵守 Retry-After 头
+-- 指数退避: 1s -> 2s -> 4s（最大 30s）
+-- 最多重试 3 次

402 响应:
+-- 不重试（预算问题，需人工处理）

5xx 响应:
+-- 可重试，指数退避
+-- 幂等请求（GET/PUT/DELETE）最多 3 次
+-- 非幂等请求（POST）仅在有 Idempotency-Key 时重试

超时:
+-- 对话接口: 客户端超时建议 60s（含 LLM 生成时间）
+-- 管理接口: 客户端超时建议 30s
```

> API Contract (REST/WS/SSE 完整端点定义) 详见 05a-API-Contract.md

> entity_type_registry: 引用 02-Knowledge层, 前端 FE-04 memory 面板使用

---

## 7. WebSocket 规范

> **[v3.2 新增]** WebSocket 是主交互协议，需要明确生命周期语义和重连策略。字段级契约以 05a-API-Contract.md Section 4 为准。

### 7.1 连接生命周期

```
WebSocket 连接语义: 按会话（Session）连接
Endpoint: /ws/conversations/{conversation_id}

生命周期:
  连接建立 -> 认证（首条消息携带 token）
    -> 认证成功: 绑定 session_id，开始对话
    -> 认证失败: 关闭连接（4001 Unauthorized）

消息类型（语义级）:
+-- user_message: 用户输入文本/指令
+-- ai_response_chunk: 流式文本块
+-- task_complete: 任务完成标记 (含 task_id + result)
+-- tool_output: Skill 执行结果 (结构化 JSONB)
+-- 系统事件: Skill 执行状态、错误通知
+-- 心跳: 双向 ping/pong（间隔 30s）

命名约束 (LAW):
+-- 禁止新增 assistant_chunk / assistant_complete (v1/v2 错误命名，v3 废弃)
+-- 保留 ai_response_chunk / tool_output / task_complete 命名契约
+-- 新增消息类型必须经 ADR 审批

字段级契约权威来源:
+-- WS 精确字段定义以 05a-API-Contract.md Section 4.2 为准（Gateway 本文档不重复维护字段级 schema）
+-- v3.6 多模态通过 ContentBlock[] 扩展，遵循 Expand-Contract（新增可选字段不破坏旧客户端）
+-- 旧客户端兼容规则同 05a Section 4.2 与 08 附录 G.2.1

连接关闭码:
+-- 4001: 认证失败
+-- 4002: 会话过期
+-- 4003: 服务端主动断开（维护）
+-- 1000: 正常关闭
```

### 7.2 重连策略

```
客户端重连（写入 SDK 文档）:

断线检测:
+-- 心跳超时（连续 2 次未收到 pong）
+-- 网络错误事件

重连行为:
+-- 指数退避: 1s -> 2s -> 4s -> 8s（最大 30s）
+-- 重连时携带 last_event_id 实现消息续传
+-- 最多重连 10 次，超过后提示用户手动刷新
+-- 重连成功后恢复会话上下文（服务端通过 session_id 关联）

服务端保活:
+-- 断线后会话保持 5 分钟（可配置）
+-- 超时后会话归档（触发记忆引擎处理）
```

---

## 8. 媒体 API 端点与上传协议

> **[v3.6 新增]** 双路媒体 API 设计，个人域与企业域物理分离。三步上传协议保障安全。

### 8.1 REST API 端点: 双路分离

```
个人媒体 API (SSOT-A 域):
  POST   /api/v1/media/upload/init          -- 初始化上传
  POST   /api/v1/media/upload/complete       -- 确认上传完成
  GET    /api/v1/media/{media_id}/url        -- 获取临时访问 URL (短 TTL)
  DELETE /api/v1/media/{media_id}            -- 个人媒体删除

  权限: user_id + tenant_id 级别 (与 memory_items 对齐)
  认证: 用户 Token

企业媒体 API (SSOT-B 域):
  POST   /api/v1/admin/knowledge/media/upload/init
  POST   /api/v1/admin/knowledge/media/upload/complete
  GET    /api/v1/admin/knowledge/media/{media_id}/url
  DELETE /api/v1/admin/knowledge/media/{media_id}

  权限: org_id + role 级别 (与 Knowledge Write API ACL 对齐)
  认证: Admin Token + ACL 校验
  路径前缀: /admin/knowledge/ 标识属于 SSOT-B 管理域
```

### 8.2 三步上传协议

```
Step 1: init (文件未上传)
  可做:
    +-- MIME type 白名单预校验 (基于客户端声明的 Content-Type)
    +-- 文件大小上限预校验 (基于客户端声明的 size)
    +-- org_tier 权限校验 (该组织是否有多模态能力, 查 org_settings.media_config)
    +-- 配额预扣 (乐观预占存储配额, quota_reserved_bytes = size)
    +-- 客户端声明 checksum_sha256, 服务端记录 expected_checksum_sha256
  不可做:
    -- 无法做 AV 扫描 / EXIF 清洗 / magic bytes 校验 (文件不存在)
  产出:
    +-- 创建 media record: security_status = 'pending'
    +-- 返回 presigned upload URL (带 TTL, 含 x-amz-checksum-sha256 条件)
    +-- 写入 media_event (media.upload_initiated)

Step 2: 客户端直传 (S3 presigned URL)
  S3 层面执行:
    +-- Content-Length / Content-Type 限制 (presigned URL 中编码)
    +-- x-amz-checksum-sha256 原生校验 (不匹配直接 400)

Step 3: complete (文件已在 S3)
  必做 (同步, 阻断返回):
    +-- checksum 校验: HeadObject 获取 x-amz-checksum-sha256 vs expected
    +-- magic bytes 校验: 读取文件头验证实际类型 vs 声明类型
    +-- 文件大小实际值校验 vs init 时声明值
    +-- EXIF/元数据清洗: 移除隐私数据，覆写原文件
    +-- 快速 AV 扫描 (ClamAV 本地, < 5s)
    +-- 配额确认: 实际 size <= 预扣 -> 返还差额; 超出 -> 补扣或 reject
    +-- 校验通过: security_status -> 'safe'
    +-- 校验失败: security_status -> 'rejected', 删除 S3 对象, 返还配额, 返回 4xx
  产出:
    +-- 更新 media record: security_status, scan_result
    +-- 写入 media_event (media.upload_completed 或 media.rejected)

Checksum 校验规范 (LAW, ADR-052):
  禁止使用 ETag 做完整性校验 (ETag 在 multipart 场景下不是文件 hash)
  使用 S3 原生 x-amz-checksum-sha256 (S3 从 2022 起支持)
  分片上传兼容: 每个 part 携带 checksum, CompleteMultipartUpload 时 S3 计算整体

超时回收:
  触发: security_status = 'pending' AND created_at < now() - interval '1 hour'
  执行: 检查 S3 -> 删除文件 -> 返还配额 -> status -> 'expired' -> media_event
  频率: 每 15 分钟定时任务
  幂等性: 仅处理 status = 'pending' 的记录

三步协议设计依据:
  为何不用服务端中转上传:
    +-- 大文件占用服务端带宽和内存
    +-- presigned URL 让客户端直传 S3 = 零服务端 I/O
    +-- S3 presigned URL 天然支持 Content-Length / Content-Type / checksum 条件约束
  为何 init 阶段预扣配额:
    +-- 防止恶意用户并发 init 大量大文件消耗配额
    +-- 超时回收机制保证配额不被永久占用
  为何 complete 阶段做同步检查:
    +-- init 时文件不存在，无法做实际内容检查
    +-- complete 时文件已在 S3，可做 magic bytes/AV/EXIF 全套检查
    +-- 同步阻断保证客户端拿到的 media_id 一定是安全的
```

### 8.3 security_status 三层拦截 (LAW)

```
Layer 1 - Gateway (取 URL 时):
  GET /api/v1/media/{media_id}/url 和 /admin/knowledge/ 对应端点
    safe -> 生成 presigned download URL, 返回
    pending | scanning -> 403 + error: "media_processing"
    rejected -> 404 (视为不存在)
    quarantined -> 403 + error: "media_quarantined"
    expired -> 404

Layer 2 - Brain (写入 conversation_events 时):
  对 ContentBlock 中每个 media_id:
    查 security_status, 非 safe -> 拒绝整条消息

Layer 3 - LLMCallPort 实现 (构建 LLM payload 前):
  对 content_parts 中每个 media_id:
    查 security_status, 非 safe -> 替换为 text_fallback
    记录 degraded_reason: "media_security_blocked"
```

### 8.4 Token 预算 + Tool 预算双维度 (Loop D)

```
Pre-check 扩展:
  现有: 检查 budget_monthly_tokens
  新增: 检查 budget_tool_amount (工具费用预算)
  实现: Gateway 在路由到多模态 Skill 前，同时校验 token 和 tool 两个维度
  任一耗尽 -> 402 拒绝

Post-settle 扩展:
  现有: LLM 响应后异步扣减 token
  新增: Tool 执行后异步扣减 tool cost
  即将耗尽(< 10%): 返回 X-Tool-Budget-Remaining 告警头
```

---

## 9. LLMCallPort 签名迁移计划

> **[v3.6 新增]** LLMCallPort 扩展 content_parts 参数以支持多模态，遵循 ADR-046 Expand-Contract 迁移。

```
现有签名:
  async call(prompt: str, model_id: str, ...) -> LLMResponse

扩展签名 (Expand 阶段):
  async call(
    prompt: str,                         -- 保留，向后兼容
    model_id: str,
    content_parts: Optional[List[ContentBlock]] = None,  -- 新增可选参数
    ...
  ) -> LLMResponse

  调用方行为:
    纯文本: call(prompt="...", model_id="...")           -- 与现有一致
    多模态: call(prompt=text_fallback, model_id="...",
                content_parts=[ContentBlock,...])       -- 新调用方式

  实现逻辑:
    content_parts 为 None -> 按现有 prompt-only 逻辑
    content_parts 非 None -> 组装多模态 payload:
      - 对每个 ContentBlock.media_id 查表获取 ObjectRef (存储层内部)
      - 生成临时 presigned URL
      - 构建 provider-specific 格式（示例）:
        OpenAI Chat Completions:
          [{"type":"text","text":"..."},{"type":"image_url","image_url":{"url":"..."}}]
        Anthropic Messages:
          [{"type":"text","text":"..."},{"type":"image","source":{"type":"url","url":"..."}}]
      - text_fallback 用于日志和降级

  Expand-Contract 时间线 (ADR-046):
    Expand:   v1.x 新增 content_parts 可选参数, 默认 None
    Migrate:  v1.x+1 起 Skill 按需使用。Brain 在检测到多模态输入时使用。
    Contract: v2.0 (最小 2 minor versions 后) 评估是否将 prompt 合并入 content_parts。

  Model Registry 注意事项:
    ModelDefinition.capabilities 已含 "vision"/"multimodal" (Section 5.2)
    Brain 在 Generation 阶段根据输入是否含非 text ContentBlock
    优先选择具备相应 capability 的模型
    降级: 无多模态模型可用 -> 使用 text_fallback, 记录 degraded_reason
```

---

## 10. LLM 内容安全

> **[v3.2 新增]** LLM Gateway 需要对输出进行基本的内容安全检查，作为 PIPL 合规和品牌保护的最后一道防线。

```
LLM 内容安全检查（LLM Gateway 层，非 Brain 层）:

检查时机: LLM 响应返回后、发送给用户前

检查项:
+-- 有害内容检测: 暴力/色情/歧视等（调用内容安全 API 或规则引擎）
+-- 合规检查: PIPL 敏感信息泄露检测（身份证号/手机号/地址等）
+-- 品牌安全: 竞品提及/负面关联（基于 Knowledge Stores 中的品牌规则，可选）

处理策略:
+-- 检测到有害内容: 替换为安全回复，记录 audit_event
+-- 检测到敏感信息泄露: 脱敏后返回，记录 audit_event
+-- 品牌安全命中: 记录告警，不阻断（v1 仅监控）

性能约束:
+-- 内容安全检查不能显著增加响应延迟
+-- 流式场景: 按句/段检查，非逐 token 检查
+-- 可通过 org_settings 配置检查级别（strict / moderate / off）
```

---

> **验证方式:** 1) JWT 认证拦截未授权请求; 2) OrgContext 正确计算 org_chain; 3) LLM Fallback 链在主模型故障时自动切换; 4) 模型访问控制: 子组织不能使用父组织未授权的模型; 5) 限流: 超过 QPS 返回 429，Token 预算耗尽返回 402; 6) WebSocket: 认证失败返回 4001，断线重连恢复会话; 7) 内容安全: 有害内容被拦截替换; 8) 三步上传: init/complete 安全检查链完整执行; 9) security_status 三层拦截: 非 safe 媒体在 Gateway/Brain/LLMCallPort 均被拦截; 10) 双路 API: 个人/企业媒体端点权限隔离; 11) LLMCallPort: content_parts=None 时行为与旧签名一致。
