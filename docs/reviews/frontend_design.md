# 笛语 (Diyu) Agent -- 前端架构设计方案

> **状态**: Frozen Snapshot (已拆分为模块文档)
> **版本**: v2.0
> **日期**: 2026-02-10
> **基于**: 后端架构文档 v3.5.1 + 前端设计 v1.1 讨论版 + v1.1 文档版 + 架构审查融合意见
> **定位**: Step 8 (Frontend UI) + Step 9 (Admin Console) 外部消费者 (00 Section 12.2)
>
> **FROZEN**: 本文档已作为 baseline 冻结。所有后续编辑请前往模块文档:
> **[docs/frontend/README.md](../frontend/README.md)** -- 模块导航索引 (FE-00 ~ FE-08)

---

## 1. 概述

本文档定义 **笛语 (Diyu) Agent** 平台的前端架构。前端是系统的**外部消费者**（00 Section 12.2 Step 8/9），通过 Gateway 暴露的 API 契约与系统交互，不改变任何内部层。

覆盖范围:
- `apps/web` -- 用户端应用 (Step 8)
- `apps/admin` -- 管理控制台 (Step 9)
- `packages/*` -- 共享基础设施

---

## 2. 核心原则

1. **严格解耦 (Type A)**: 前端仅知道 Gateway API 契约 (`/api/v1/*`, `/chat/stream`, `/events/*`)。对 Brain 内部结构、Memory Core Schema、Skill 实现一无所知。
2. **组件驱动**: 建立共享设计系统 (`packages/ui`)，确保用户端和管理端一致性。
3. **生成式 UI (Generative UI)**: 支持渲染 Skill 返回的动态结构化内容（商品卡片、搭配方案、数据图表），不仅限于纯文本。
4. **乐观更新与实时性**: 聊天交互即时响应。WebSocket 承载对话，SSE 承载通知。
5. **安全设计**: SaaS 端使用 HttpOnly Cookie + BFF（防 XSS）；Private 端降级为内存 Bearer Token（安全性由私有网络隔离保障）。详见 Section 5.1 认证策略工厂。
6. **双栏工作台**: 借鉴 Claude.ai Artifacts 模式处理内容生产场景，通过标准组件库保持轻量。
7. **降级优先**: 后端任何非硬依赖组件不可用时，前端显示降级 UI 而非崩溃。
8. **部署适配**: 通过 DEPLOY_MODE 环境变量适配 SaaS/Private/Hybrid 三种部署模式（FE-001）。

---

## 3. 当前状态分析

### 3.1 后端架构核心特征

笛语后端是一个 7 层 + 双 SSOT 的解耦架构, v3.5.1 定稿:

```
Level 0 (不可分核心对): Brain + Memory Core (硬依赖)
Level 1 (Port 耦合功能层): Knowledge / Skill / Tool / Gateway
Level 2 (可插拔环境层): Infrastructure / Deployment
---
外部消费者 (Step 8/9): Frontend UI / Admin Console
```

关键架构约束对前端的影响:

| 后端约束 | 前端影响 |
|---------|---------|
| Type A 接口级完全解耦 | 前端只消费 Gateway API 契约, 对 Brain/Memory/Knowledge 零感知 |
| WebSocket /chat/stream 为主交互 | 前端必须以 WS 流式为核心通信模式 |
| Skill 返回结构化数据 | 前端需要 Generative UI / Component Registry 渲染动态内容 |
| 多租户 5 层组织树 + RBAC | 前端需要精细的权限控制 + 组织切换 |
| CP/DP 分区 | 用户端和管理端消费不同 API 子集 |
| Port 演进 Expand-Contract | 前端需要优雅处理未知字段/消息类型 |
| Memory Core 自动进化 + PIPL/GDPR 删除权 | 前端需要记忆可视化 + 删除申请追踪 |
| 软依赖降级 (degraded_reason) | 前端需要展示降级状态, 隐藏不可用功能 |
| Experiment Engine 灰度 | 前端需要 Feature Flag 条件渲染 + 实验变体标识 |
| 三部署模式 (SaaS/Private/Hybrid) | 前端构建产物需适配多种部署环境 (FE-001) |

### 3.2 业内最佳实践调研

| 平台 | 前端栈 | 核心模式 | 关键启示 |
|------|--------|---------|---------|
| Dify | React + 自定义 | Workflow Canvas + Prompt IDE | 可视化编排 + BaaS 思维 |
| Coze Studio | React + TS (Rush.js monorepo) + @coze/coze-design | DDD + No-code Builder | 自研 UI 库 + 严格依赖管控 |
| Claude.ai | React | Chat + Artifacts 双栏 | 内容预览 + 轻量级代码执行 |
| ChatGPT | React + Next.js | Chat-first + Canvas | 多模态 + 实时协作 |
| LobeChat | Next.js + Zustand + Ant Design + tRPC | 全栈 AI 平台 | 前端即平台 (与笛语定位不同) |
| LangSmith | React | Dashboard + Trace Viewer | 可观测性优先 |

关键区分: Claude.ai / LobeChat 是"前端即 AI 平台"（前端包含模型管理、知识库、Agent 编排）。笛语前端是"薄客户端"（所有智能在后端 7 层架构, 前端只做展示和交互）。不可直接 fork 或轻量化这些平台, 应借鉴 UX 模式 + 自建适配架构。

技术趋势 (2025-2026):

1. Vercel AI SDK 6 已成为 React AI 应用的事实标准: useChat / streamText / Generative UI / Tool Loop
2. assistant-ui (YC 投资) 作为 AI Chat 组件层的新标准, 原生支持 AI SDK + shadcn/ui
3. Turborepo + pnpm 是 Multi-app Monorepo 的成熟方案
4. Feature-Sliced Design (FSD) 在大型前端项目中获得广泛采用
5. React Server Components 用于 Admin 数据密集型页面, 减少客户端 JS

---

## 4. 技术栈

| 层级 | 选型 | 理由 |
|------|------|------|
| **框架** | **Next.js 15 (App Router)** | RSC 提升首屏、AI SDK 原生支持、业内 AI 应用标配; 私有化通过 output:'export' 降级为静态 (FE-001) |
| **语言** | **TypeScript 5.x (strict)** | 不可协商 |
| **Monorepo** | **Turborepo + pnpm** | 增量构建、远程缓存、并行任务、依赖隔离 |
| **样式** | **Tailwind CSS v4** | 原子化、AI 友好、主题系统 |
| **UI 基础 (Chat/通用)** | **shadcn/ui (Radix Primitives)** | 代码所有权、可访问性、AI 可维护; 适用于 apps/web 及 packages/ui |
| **UI 补充 (Admin 企业组件)** | **Ant Design 5 (按需引入)** | 5 层组织树、级联选择器、复杂表单布局、审批工作流 -- 企业级开箱即用; 仅在 apps/admin 引入 (FE-008) |
| **AI Chat 组件** | **assistant-ui** | 专业 AI Chat UX、原生 AI SDK 集成、streaming/retry/中断; 如稳定性或定制深度不满足需求, 降级为自研 Hook (FE-009) |
| **AI SDK** | **Vercel AI SDK 6** | useChat / Generative UI / Tool Loop; 通过 Custom Runtime 适配笛语 WebSocket (FE-009) |
| **状态 (服务端)** | **TanStack Query v5** | 缓存失效、乐观更新、后台重取 |
| **状态 (客户端)** | **Zustand** | 极简、TypeScript-first、无 boilerplate |
| **表单** | **React Hook Form + Zod** | 类型安全验证、性能优秀 |
| **Markdown** | **react-markdown + rehype-highlight** | AI 回复含 markdown, 需安全渲染 + 代码高亮 |
| **动效** | **Framer Motion** | 布局动画、页面过渡 |
| **图表** | **Recharts** | 可组合、React 生态成熟 |
| **图标** | **Lucide React** | 统一、轻量 |
| **测试** | **Vitest + Playwright + RTL** | 单元 / E2E / 组件 三层 |
| **i18n** | **next-intl (预埋)** | Phase 0-3 纯中文, 结构预埋多语言, Phase 4 启用 |

---

## 5. 架构拓扑

### 5.1 Monorepo 结构

```text
diyu-frontend/
|
+-- apps/
|   +-- web/                      # 用户端 (Step 8)
|   |   +-- app/                  # Next.js App Router
|   |   |   +-- (auth)/           # 认证路由组
|   |   |   +-- (main)/           # 主应用路由组
|   |   |   |   +-- chat/         # 对话 (场景1)
|   |   |   |   +-- content/      # 内容生产 (场景2)
|   |   |   |   +-- merchandising/# 陈列搭配 (场景3)
|   |   |   |   +-- training/     # 区域培训内容管理
|   |   |   |   +-- search/       # 全局搜索
|   |   |   |   +-- memory/       # 我的记忆 (查看/删除申请/PIPL追踪)
|   |   |   |   +-- history/      # 对话历史 + 文件夹管理 + 上传总部存档
|   |   |   |   |   +-- folders/
|   |   |   |   |   +-- upload/
|   |   |   |   +-- knowledge-edit/ # 知识编辑工作区
|   |   |   |   |   +-- templates/
|   |   |   |   |   +-- drafts/
|   |   |   |   |   +-- submitted/
|   |   |   |   +-- store-dashboard/ # 区域代理门店看板 (regional_agent)
|   |   |   |   +-- settings/     # 个人设置
|   |   |   +-- (bookmarks)/      # Artifact 收藏 (V1.1)
|   |   |   +-- api/              # BFF Route Handlers (SaaS 模式)
|   |   |   +-- layout.tsx
|   |   +-- components/           # 应用专属组件
|   |   +-- hooks/                # 应用专属 hooks
|   |   +-- stores/               # Zustand stores
|   |   +-- lib/                  # 工具函数
|   |   +-- next.config.ts        # 含 DEPLOY_MODE 条件 (FE-001)
|   |   +-- __tests__/            # E2E (Playwright)
|   |
|   +-- admin/                    # 管理端 (Step 9)
|   |   +-- app/                  # Next.js App Router
|   |   |   +-- (auth)/
|   |   |   +-- (dashboard)/              # 品牌总部 Admin 页面 (brand_hq owner/admin)
|   |   |   |   +-- organizations/        # 组织管理 + 审批队列
|   |   |   |   +-- members/              # 成员管理 (品牌全级)
|   |   |   |   +-- knowledge/            # 品牌知识管理
|   |   |   |   |   +-- import-review/    # 下级提交下载/导入状态
|   |   |   |   |   +-- local-life/       # 本地生活知识库
|   |   |   |   |   +-- store-nodes/      # 全国门店图谱节点
|   |   |   |   +-- content-review/       # 内容审核 (默认关闭, 条件显示)
|   |   |   |   +-- experiments/          # A/B 实验
|   |   |   |   +-- billing/              # 订阅+点数+用量报表
|   |   |   |   +-- settings/             # RULE/BRIDGE + BrandTone/人设/白名单
|   |   |   |   +-- audit/                # 审计日志
|   |   |   +-- (platform-ops)/       # 平台运营页面 (仅 platform tier 可见)
|   |   |   |   +-- tenant-overview/      # 租户总览
|   |   |   |   +-- tenant-detail/[org_id]/ # 单租户详情 + 配额 + 豁免
|   |   |   |   +-- model-registry/       # 模型注册表
|   |   |   |   +-- model-pricing/        # 官网价格映射
|   |   |   |   +-- subscription-plans/   # 套餐定义 + 点数包
|   |   |   |   +-- billing-global/       # 全平台账单
|   |   |   |   +-- global-config/        # 全局配置
|   |   |   |   +-- security-config/      # 安全与合规
|   |   |   |   +-- system-ops/           # 运维监控
|   |   |   |   +-- global-knowledge/     # 平台级知识模板
|   |   |   |   +-- layout.tsx            # PlatformGuard
|   |   |   +-- layout.tsx
|   |   +-- components/
|   |   +-- hooks/
|
+-- packages/
|   +-- ui/                       # 共享设计系统
|   |   +-- src/
|   |   |   +-- primitives/       # 基础组件 (shadcn/ui: Button, Input, Card...)
|   |   |   +-- composites/       # 组合组件 (DataTable, OrgTree...)
|   |   |   +-- chat/             # AI Chat 组件封装 (基于 assistant-ui)
|   |   |   +-- artifacts/        # Artifact 渲染组件
|   |   |   +-- commerce/         # 时尚领域组件 (ProductCard, OutfitGrid, StyleBoard...)
|   |   |   +-- memory/           # 记忆可视化 (ConfidenceBadge, ProvenanceTag, MemoryCard)
|   |   |   +-- status/           # 系统状态 (DegradationBanner, ExperimentIndicator)
|   |   |   +-- data/             # 数据展示 (Chart, MetricCard)
|   |   |   +-- themes/           # 主题 Token + 暗色/亮色
|   |   +-- package.json
|   |
|   +-- api-client/               # API 客户端 & 类型
|   |   +-- src/
|   |   |   +-- rest.ts           # 类型化 REST 客户端
|   |   |   +-- websocket.ts      # WS 连接管理器
|   |   |   +-- sse.ts            # SSE 客户端
|   |   |   +-- ai-runtime.ts     # AI SDK Custom Runtime 适配器 (FE-009)
|   |   |   +-- auth.ts           # 认证策略工厂 (FE-010)
|   |   |   +-- types/            # 从 OpenAPI Schema 生成的类型
|   |   |   |   +-- org-context.ts
|   |   |   |   +-- chat.ts
|   |   |   |   +-- knowledge.ts
|   |   |   |   +-- skill-output.ts
|   |   |   |   +-- memory.ts     # MemoryItem + injection_receipt 类型
|   |   |   |   +-- degradation.ts # degraded_reason 枚举
|   |   |   +-- hooks/            # useChat, useOrg 等 TanStack Query 封装
|   |   +-- package.json
|   |
|   +-- shared/                   # 共享工具
|   |   +-- src/
|   |   |   +-- constants.ts
|   |   |   +-- org-tiers.ts      # 组织层级常量 (对齐 06 Section 1.1)
|   |   |   +-- settings-constraints.ts  # LAW/RULE/BRIDGE 25 项枚举 (对齐 06 Section 1.6)
|   |   |   +-- validators.ts     # Zod schemas
|   |   |   +-- permissions.ts    # RBAC 权限工具
|   |   |   +-- formatters.ts
|   |   |   +-- feature-flags.ts  # Feature Flag 读取 + 条件判定
|   |   +-- package.json
|   |
|   +-- config/                   # 共享配置
|       +-- eslint/
|       +-- typescript/
|       +-- tailwind/
|
+-- turbo.json
+-- pnpm-workspace.yaml
+-- package.json
```

### 5.2 核心分层架构

```
+-------------------------------------------------------------------+
|                     前端架构分层                                     |
|                                                                     |
|  +-- View Layer (视图层) -------------------------------------------+
|  |  apps/web/app/    各路由页面 + 布局                               |
|  |  apps/admin/app/  各路由页面 + 布局                               |
|  +-----------------------------------------------------------------+
|                            |
|  +-- Component Layer (组件层) --------------------------------------+
|  |                                                                  |
|  |  packages/ui/primitives/   基础原子组件 (shadcn/ui)               |
|  |  packages/ui/composites/   业务组合组件                            |
|  |  packages/ui/chat/         AI Chat 组件 (assistant-ui 封装)       |
|  |  packages/ui/artifacts/    Artifact 渲染 (Component Registry)     |
|  |  packages/ui/commerce/     时尚领域组件 (ProductCard, OutfitGrid)  |
|  |  packages/ui/memory/       记忆可视化 (ConfidenceBadge 等)         |
|  |  packages/ui/status/       系统状态 (DegradationBanner 等)         |
|  |  packages/ui/data/         数据展示 (Chart, MetricCard)            |
|  +-----------------------------------------------------------------+
|                            |
|  +-- State Layer (状态层) ------------------------------------------+
|  |                                                                  |
|  |  Server State: TanStack Query (API 数据缓存/失效/乐观更新)         |
|  |  Client State: Zustand (UI 状态: 侧栏/主题/通知/OrgContext)       |
|  |  Chat State:   AI SDK useChat via Custom Runtime (FE-009)        |
|  |  Form State:   React Hook Form + Zod (表单验证)                   |
|  +-----------------------------------------------------------------+
|                            |
|  +-- Transport Layer (传输层) --------------------------------------+
|  |                                                                  |
|  |  packages/api-client/rest.ts       REST /api/v1/*                |
|  |  packages/api-client/websocket.ts  WebSocket /chat/stream        |
|  |  packages/api-client/sse.ts        SSE /events/*                 |
|  |  packages/api-client/ai-runtime.ts AI SDK <-> 笛语 WS 适配器      |
|  |  packages/api-client/auth.ts       认证策略工厂 (FE-010)           |
|  +-----------------------------------------------------------------+
|                            |
|                     [ Gateway API ]
```

### 5.3 数据流拓扑

```
浏览器 (apps/web or apps/admin)
   |
   +-- HTTP 请求
   |       |
   |       +-- SaaS 模式: Cookie 自动附带
   |       |       |
   |       |       v
   |       |   Next.js BFF (app/api/)
   |       |       |  职责: Cookie->Bearer 转换, 响应格式适配, 敏感字段过滤
   |       |       |  不重复 Gateway 逻辑 (不做认证/限流/路由)
   |       |       v
   |       |   后端 Gateway (/api/v1/*, /api/v1/admin/*)
   |       |
   |       +-- Private 模式: 内存 Bearer Token 直接附带
   |               |
   |               v
   |           后端 Gateway (/api/v1/*, /api/v1/admin/*)
   |
   +-- WebSocket (对话通道)
   |       浏览器 -> wss://api.diyu/chat/stream
   |       SaaS: BFF 签发短效一次性 WS token
   |       Private: 复用 access_token 或 Gateway /api/v1/auth/ws-token
   |       双向: 用户消息 up / AI 流式回复 down
   |
   +-- SSE (通知通道)
           浏览器 -> https://api.diyu/events/?token=<jwt>
           单向: 任务完成、系统告警、异步事件
           自动重连 (SSE 协议内建)
```

---

## 6. 认证与组织上下文

### 6.1 认证策略工厂 (FE-010)

> **[裁决]** BFF + output:'export' 兼容性冲突通过认证策略工厂模式解决。SaaS 模式使用 HttpOnly Cookie + BFF (安全性最高)；Private 模式降级为内存 Bearer Token (安全性由私有网络隔离保障)。

```
认证策略工厂 (packages/api-client/auth.ts):

  interface AuthStrategy {
    getHeaders(): Record<string, string>   // 获取认证头
    handleUnauthorized(): Promise<boolean>  // 处理401刷新
    getWsToken(): Promise<string>           // 获取WebSocket令牌
  }

  SaaS 模式 (CookieAuthStrategy):
    getHeaders()          -> 空 (Cookie由浏览器自动附带, BFF转换)
    handleUnauthorized()  -> 空 (BFF拦截处理)
    getWsToken()          -> POST /api/auth/ws-token (BFF端点)

  Private 模式 (BearerAuthStrategy):
    getHeaders()          -> { Authorization: `Bearer ${memoryToken}` }
    handleUnauthorized()  -> 用refresh_token换新access_token, 存内存
    getWsToken()          -> 直接复用当前access_token (短有效期)
                             或 Gateway提供等效端点 GET /api/v1/auth/ws-token

  工厂:
    const strategy = DEPLOY_MODE === 'private'
      ? new BearerAuthStrategy()
      : new CookieAuthStrategy()

  上层代码:
    const headers = strategy.getHeaders()  // 无感知
    fetch('/api/v1/...', { headers })      // 统一调用
```

#### 6.1.1 SaaS 认证流 (BFF)

```
登录:
  用户提交凭证 -> BFF /api/auth/login -> 后端认证
    -> 后端返回 JWT
    -> BFF 写入 HttpOnly Secure SameSite=Strict Cookie
    -> 前端无法通过 JS 读取 token (XSS 防护)

请求链:
  浏览器自动附带 Cookie -> BFF 读取 Cookie
    -> 提取 JWT -> 添加 Authorization: Bearer <jwt>
    -> 转发给后端 Gateway

Token 刷新:
  Cookie 含 refresh_token -> BFF 拦截 401 响应
    -> 自动用 refresh_token 获取新 access_token
    -> 更新 Cookie -> 重试原请求
    -> 用户无感知

WebSocket 认证:
  BFF 提供短效一次性 WS token (/api/auth/ws-token)
    -> 前端用此 token 建立 WS 连接
    -> 避免在 URL 中暴露长效 JWT
```

#### 6.1.2 Private 认证流 (Bearer)

```
登录:
  用户提交凭证 -> 直接调用 Gateway /api/v1/auth/login
    -> Gateway 返回 { access_token, refresh_token }
    -> access_token 存内存 (页面关闭即失效)
    -> refresh_token 存内存 (不持久化)

请求链:
  BearerAuthStrategy.getHeaders() -> { Authorization: Bearer <token> }
    -> 直接请求后端 Gateway

Token 刷新:
  api-client 拦截器检测 401 -> handleUnauthorized()
    -> 用 refresh_token 获取新 access_token
    -> 更新内存中的 token -> 重试原请求
    -> 用户无感知

WebSocket 认证:
  方式 1 (默认): 复用 access_token 做 WS 认证
    -> 私有网络内可接受, 安全性由网络隔离保障
    -> Gateway 已支持 Bearer 认证 WS, 无需改动
  方式 2 (可选, 更安全): Gateway 暴露 /api/v1/auth/ws-token 端点
    -> 需后端配合, 但改动小 (一个签发短效JWT的端点)
```

#### 6.1.3 安全性差异 (ADR FE-010)

| 维度 | SaaS (BFF) | Private (Bearer) |
|------|-----------|-----------------|
| XSS防护 | HttpOnly Cookie (JS不可读) | 内存Token (XSS可窃取) |
| 缓解措施 | -- | 私有网络隔离 + CSP严格策略 |
| Token泄露窗口 | Cookie过期时间 | 内存Token (页面关闭即失效) |
| CSRF | SameSite=Strict Cookie + CSRF Token | N/A (无Cookie) |
| 可接受性 | 公网部署标准 | 私有内网可接受 |

### 6.2 组织上下文 (OrgContext) 管理

后端定义:
- 组织树: `platform > brand_hq > brand_dept/regional_agent > franchise_store`
- RBAC: `owner/admin/editor/reviewer/viewer`
- 配置继承: `LAW / RULE / BRIDGE(is_locked)`

前端处理:
- Org Switcher 切换组织时刷新 OrgContext、重建 WS、清理本地临时态。
- 权限守卫分层: `TierGate` 控制入口，`PermissionGate` 控制按钮/动作。
- 前端权限仅用于 UI 可见性；真实权限校验始终在 Gateway。
- 配置继承可视化保留: LAW 只读、RULE 可改、BRIDGE 锁子级。

#### 6.2.1 TierGate 访问规则 (Admin Console)

```ts
if (org_tier === 'platform') allowAdmin();
else if (org_tier === 'brand_hq' && role in ['owner', 'admin']) allowAdmin();
else redirectToWebApp(); // 302 到 apps/web
```

关键约束:
- 全平台成员管理仅 `platform` + `brand_hq(owner/admin)` 可操作。
- `brand_dept/regional_agent/franchise_store` 无 Admin Console 入口。
- `brand_hq(editor/viewer)` 无 Admin Console 入口，仅 Web App。

#### 6.2.2 Admin Console 功能暴露矩阵 (修订)

| 功能模块 | platform | brand_hq (owner/admin) | 其他角色/层级 |
|---------|----------|------------------------|---------------|
| 运营仪表盘 | 全局 | 品牌级 | 无 |
| 组织树管理 | 全局 | 品牌子树 | 无 |
| 成员管理 | 全局 | 品牌全级 | 无 |
| 品牌知识库 | 平台模板 | 品牌 CRUD + 导入 | 无 |
| 内容审核规则 | 规则模板 | 开关+配置(默认关闭) | 无 |
| 设置中心 (RULE/BRIDGE) | 全局 | 品牌级 | 无 |
| 用量/计费 | 全局账单 | 品牌账单(订阅+点数) | 无 |
| 审计日志 | 全局 | 品牌级 | 无 |
| 实验管理 | 全局 | 品牌级 | 无 |
| platform-ops/* | 全部 | 无 | 无 |

#### 6.2.3 Web App 功能暴露矩阵 (新增)

| 功能 | brand_hq 员工 | brand_dept | regional_agent | franchise_store |
|------|---------------|------------|----------------|-----------------|
| AI 对话 + 模型选择 | Y | Y | Y | Y |
| 内容创作 | Y | Y | Y(区域) | Y(本店) |
| 对话历史文件夹 + 上传总部 | Y | Y | Y | Y |
| 知识编辑工作区 | Y | 贡献 | 模板编辑+提交 | 本地文件夹+模板+提交 |
| 门店看板/门店增减申请 | - | - | Y | - |
| 本地知识文件夹 | - | - | - | Y |
| 用量与点数余额查看 | Y | Y | Y | Y |
| 充值入口 | owner/admin | - | - | - |
| 记忆管理 | Y | Y | Y | Y |

#### 6.2.4 Settings 约束枚举更新

`packages/shared/settings-constraints.ts` 以业务规则为准:
- 保留: `content_policy / review_flow / content_restrictions / allowed_models / default_model / fallback_chain / skill_whitelist / tool_whitelist / is_locked`
- 新增业务项: `brand_tone / personas / knowledge_visibility_acl`
- 移除编辑项: `budget_monthly_tokens / budget_hard_limit`（不再采用预算分配模型）
- 兼容策略: 若后端仍返回历史预算字段，前端仅只读展示并标记 `legacy`

---

## 7. 实时通信

### 7.1 WebSocket -- 对话通道

```
端点: wss://api.diyu/chat/stream
职责: 双向对话 (用户发消息 + AI 流式回复)

连接生命周期:
  1. 获取 WS token (通过 AuthStrategy.getWsToken())
  2. 前端 new WebSocket(url + ?token=<ws_token>)
  3. 后端验证 -> 绑定 session
  4. 心跳: 服务器 30s PING -> 客户端 PONG
  5. 断开: 指数退避重连 (1s -> 2s -> 4s -> ... -> 30s 上限)
  6. 重连: 携带 last_event_id 恢复流 (5 分钟内 session 保持)

消息类型 (下行):
  ai_response_chunk   -- AI 回复文本块 (流式追加到消息气泡)
  tool_output          -- Skill 结构化输出 (触发 Component Registry 渲染)
  task_complete        -- 长任务完成 (含 task_id + result)
  error                -- 错误信息

状态管理:
  - 乐观追加用户消息 (useOptimistic, React 19)
  - AI chunk 实时追加到最后一条 AI 消息
  - tool_output 触发右栏 Artifact 展开

客户端约束 (Append-Only):
  - SDK 不发送消息编辑/删除类型请求
  - 对话历史为追加模式, 前端不修改已发送消息内容
  - 对齐 01-Brain Section 5: 超阈值消息由后端摘要压缩至 summary_blocks, 前端不干预
  - 设计原因: 保护后端 KV cache 稳定前缀, 最大化推理缓存命中率
    (灵感来源: Manus Context Engineering 的 "stable prefix + append-only" 策略)
  - packages/api-client/websocket.ts 类型约束:
      上行消息类型仅允许: user_message | multimodal_message | ping | session_resume
      禁止: edit_message | delete_message | reorder_messages

WebSocket 连接管理器 (packages/api-client/websocket.ts):

  关闭码处理:
    4001 (auth failed)       -> 清除凭证, 跳转登录页
    4002 (session expired)   -> 静默刷新 token, 自动重连
    4003 (server maintenance)-> 显示维护页, 禁止重连
    1000 (normal close)      -> 正常关闭, 不重连

  状态机:
    CONNECTING -> AUTHENTICATED -> READY <-> STREAMING
                                    |
                                RECONNECTING -> READY
                                    |
                                  CLOSED
```

### 7.2 SSE -- 通知通道

```
端点: https://api.diyu/events/?token=<jwt>
职责: 单向推送 (任务完成、系统告警、异步事件)

事件类型:
  task_status_update   -- 异步任务进度 (内容审核通过/拒绝)
  system_notification  -- 系统级通知 (维护、版本更新)
  budget_warning       -- 额度告警 (80%/95%/100%)
  knowledge_update     -- 知识库变更通知

优势 (vs WebSocket):
  - SSE 协议内建自动重连
  - HTTP 原生, 穿透代理/防火墙
  - 单向推送场景不需要 WebSocket 的双向开销
```

---

## 8. 关键功能实现

### 8.1 对话系统 -- Chat + Streaming

核心技术选型: AI SDK useChat + assistant-ui 组件 + Custom Runtime 适配器

#### 8.1.1 AI SDK 与笛语 WebSocket 的桥接 (FE-009)

```
设计背景:
AI SDK 的 useChat 默认假设前端控制 LLM 调用 (前端 -> Next.js API Route -> streamText -> LLM)。
笛语的 LLM 调用由后端 Brain 控制, 前端只接收 WebSocket 流式结果。
这是根本性的协议差异, 需要显式适配层。

桥接方案: assistant-ui Custom Runtime

                    assistant-ui 组件层
                         |
                    useChat hook (AI SDK)
                         |
                    DiyuChatRuntime (自研适配器)
                         |
          +--- 协议转换 ---+--- 消息映射 ---+
          |                                 |
    笛语 WS 协议                     AI SDK 消息格式
    {                                {
      type: "text_chunk",              role: "assistant",
      content: "...",                  content: "...",
      event_id: "..."                  id: "..."
    }                                }
    {                                {
      type: "tool_output",             role: "tool",
      skill: "merchandising",          toolName: "merchandising_search",
      data: {...}                      result: {...}
    }                                }
          |                                 |
    WebSocket /chat/stream          assistant-ui 渲染

DiyuChatRuntime 职责:
1. 连接管理: 委托给 websocket.ts (认证/心跳/重连/续传)
2. 消息入站: 笛语 WS 消息 -> AI SDK Message 格式
3. 消息出站: 用户输入 -> 笛语 WS 发送格式
4. 流式状态: WS streaming -> AI SDK StreamState (ready/submitted/streaming/error)
5. Tool Output: 笛语 tool_output -> AI SDK ToolResult -> Component Registry
6. 元数据透传: injection_receipt / degraded_reason -> Zustand (供 UI 消费)

替代方案 (备选, 如 Custom Runtime 复杂度过高):
后端 Gateway 增加 /api/v1/chat HTTP 端点, 内部转发到 Brain WS, 再以 SSE 流返回。
前端 useChat 直接对接, 零适配。但增加了后端工作量和一跳延迟。
决策: 优先 Custom Runtime (前端适配); 如遇阻, 降级为后端 API Route。
```

#### 8.1.2 渲染

```
AI 回复使用 react-markdown + rehype-highlight
支持: 文本、代码块、列表、表格、加粗/斜体
不支持: HTML 内联 (安全考量, 对齐 01 Section 4.3 Sanitization)
```

#### 8.1.3 架构流

```
用户输入 -> DiyuChatRuntime -> WebSocket /chat/stream
                                  |
                                  v
                       Brain 流式响应
                                  |
                       +----------+-----------+
                       |                      |
                  纯文本块                 tool_output 块
                       |                      |
                  渲染为 Markdown         Component Registry
                  (assistant-ui 内置)     (Generative UI)
                                              |
                                  +--------- 元数据 ---------+
                                  |                          |
                            injection_receipt          degraded_reason
                                  |                          |
                            记忆透明面板              降级状态 Banner
                            (Artifact 右栏)          (全局顶部)
```

### 8.2 Generative UI -- Component Registry

```
Skill 返回结构化 tool_output, 前端通过注册表动态渲染:

Component Registry 设计:

registry = {
  // 搭配推荐
  "merchandising_search":  MerchandisingGrid,
  "merchandising_display": DisplayGuideCard,
  "store_dashboard":       StoreDashboardCard,

  // 内容生产
  "content_draft":         ContentEditor,
  "content_preview":       ContentPreview,
  "knowledge_template":    KnowledgeTemplateForm,

  // 搜索与数据
  "search_results":        SearchResultList,
  "data_chart":            DataVisualization,

  // 商品
  "product_card":          ProductCard,
  "image_generation":      GeneratedImageCard,

  // 培训与审批
  "training_material":     TrainingViewer,
  "approval_request":      ApprovalForm,

  // 记忆透明度 (DIYU 特有)
  "memory_context":        MemoryContextPanel,
}

降级策略:
  未知 type -> JsonViewer (原始 JSON 渲染)
  渲染异常 -> ErrorBoundary + 纯文本 fallback
  新增 Skill -> 前端无需改代码, 显示 JSON 直到注册组件
```

示例 Payload:
```json
{
  "type": "tool_output",
  "tool": "merchandising_search",
  "data": {
    "items": [{ "sku": "123", "name": "夏季连衣裙", "image": "..." }],
    "layout": "grid"
  }
}
```

前端处理:
```tsx
// SkillRenderer.tsx
const REGISTRY: Record<string, ComponentType<any>> = {
  merchandising_search: MerchandisingGrid,
  outfit_recommendation: OutfitGrid,
  content_preview: ContentPreview,
  web_search: SearchResultCard,
};

export function SkillRenderer({ payload }: { payload: ToolOutput }) {
  const Component = REGISTRY[payload.tool] ?? JsonViewer;
  return <Component data={payload.data} />;
}
```

### 8.3 双栏工作台 (Chat + Artifacts)

```
布局策略:

+--------------------+------------------------+
|                    |                         |
|   Chat Panel       |   Artifact Panel        |
|   (左栏, 固定)      |   (右栏, 动态)           |
|                    |                         |
|   - 对话消息流      |   - 长文案预览/编辑       |
|   - 搜索结果摘要    |   - 搭配方案可视化        |
|   - 简短问答        |   - 数据图表展示          |
|   - Agent 状态      |   - 商品详情/对比         |
|                    |   - 记忆注入透明面板       |
+--------------------+------------------------+

触发规则:
  - tool_output.layout === "artifact"  -> 右栏展开
  - tool_output.type === "memory_context" -> 右栏展示记忆面板
  - 纯文本长度 > 阈值                   -> 右栏展开
  - 用户手动切换                        -> 右栏展开/收起

移动端适配:
  - 本文档主实现为 PC 端, 移动端仅预留接口
  - Artifact Drawer / 手势交互放入 Phase 4
```

### 8.4 Artifact 持久化与跨会话引用

```
灵感来源: Manus 将文件系统作为 "无限上下文" 外部记忆 -- 长文本写入文件而非塞入 prompt,
需要时再读取。DIYU 将此理念应用于 Artifact: Skill 产生的中间结果不仅在当前气泡展示,
还可跨会话持久化、回溯引用。

持久化机制 (不引入新 Gateway Port):
  - 后端: tool_output 已作为 conversation_events 归档 (06 Section 9)
  - 前端: 通过 GET /api/v1/sessions/{id}/events?type=tool_output 查询历史 Artifact
  - 本地索引: IndexedDB 缓存最近 N 个 Artifact 的元数据 (title/type/session_id/timestamp)
    -> 加速跨会话搜索, 缓存失效时回源 Gateway

收藏与命名:
  - 用户可 "收藏" 任意 Artifact (右栏操作按钮)
  - 收藏 = 前端本地持久化 (IndexedDB) + 可选后端标记 (如 Gateway 提供 bookmark API)
  - 收藏列表入口: 侧边栏 "我的收藏" (Cmd+Shift+B)
  - 用户可为 Artifact 自定义标题 (默认: Skill 类型 + 时间戳)

跨会话引用 (V2):
  - 对话中输入 "@" 触发 Artifact 引用选择器
  - 搜索范围: 收藏的 Artifact + 最近 30 天的 tool_output
  - 选中后注入为对话上下文引用 (类似 "参考之前的搭配方案")
  - 后端处理: 将引用的 Artifact 内容作为 context 附加到当前消息

降级:
  - GET /sessions/{id}/events 不可用 -> 仅显示当前会话 Artifact
  - IndexedDB 不可用 -> 降级为仅当前会话 (内存模式)
  - 收藏功能依赖 IndexedDB; 不可用时隐藏收藏按钮
```

### 8.5 DIYU 特有 UI 关注点

#### 8.5.1 记忆注入透明面板

```
位置: Artifact 右栏 (用户可切换显示)

展示内容:
  本轮注入的记忆列表, 每条包含:
  +-- ConfidenceBadge: 置信度色阶 (绿 >=0.8 / 黄 0.5-0.8 / 灰 <0.5)
  +-- ProvenanceTag:   来源标签 (confirmed_by_user / analysis / observation)
  +-- 记忆内容摘要
  +-- valid_since 时间标签
  +-- utilized 标记 (本轮是否被实际引用)

数据来源:
  Brain 流式响应中的元数据字段 (injection_receipt 五元组):
    candidate_score, decision_reason, policy_version, guardrail_hit, context_position
  通过 DiyuChatRuntime 透传到 Zustand -> 记忆面板组件消费

价值:
  - 用户可理解 "AI 为什么这样回答"
  - 调试工具: 开发/测试阶段验证记忆检索质量
  - 可通过 Feature Flag 控制是否对终端用户可见
```

#### 8.5.2 降级状态展示

```
位置: 全局顶部 Banner (packages/ui/status/DegradationBanner)

触发条件:
  后端响应头或 WS 元数据包含 degraded_reason 字段

展示逻辑:
  degraded_reason                    | 用户提示                          | UI 行为
  "knowledge_unavailable"            | "知识库暂时不可用, 仅基于记忆回复"    | 隐藏知识推荐区域
  "pgvector_unavailable"             | (不展示, 用户无感)                 | 无可见变化
  "llm_fallback"                     | "当前使用备用模型"                  | 显示模型标识
  Memory Core down (硬依赖, 极端)      | 全局错误页                         | 阻断所有操作

实现:
  - Zustand 存储当前 degraded_reasons 集合
  - DegradationBanner 组件订阅, 条件渲染
  - REST 响应通过 api-client 拦截器统一提取
  - WS 响应通过 DiyuChatRuntime 透传
```

#### 8.5.3 PIPL/GDPR 记忆管理

```
位置: apps/web/(main)/memory/ 页面
入口: 侧边栏 "AI 对你的记忆" (Cmd+Shift+M)

功能:
  1. 我的记忆列表: 查看所有与自己相关的记忆条目
     - 按类型/时间/置信度过滤
     - 每条显示 provenance + confidence + valid_since
     - 置信度可视化:
         >= 0.8: 实心圆点 (高确信)
         0.5-0.8: 半实心圆点 (中等)
         < 0.5: 空心圆点 (低确信)
     - 来源标签:
         confirmed_by_user: "你确认的"
         observation: "AI 观察到的"
         analysis: "AI 推断的"
     - 视觉分离 (对齐隐私硬边界):
         个人记忆: 蓝色标签 "个人"
         品牌知识: 绿色标签 "品牌" (仅在对话中出现, 不在记忆面板)
         两者绝不混淆展示

  2. 删除申请: 用户选择记忆 -> 提交删除请求
     - 单条删除 / 全部清除
     - REST DELETE /api/v1/me/memories/{id}
     - 后端创建 tombstone, 进入删除流水线

  3. 删除状态追踪:
     tombstone -> processing -> completed
     - 列表中显示各条目的删除进度
     - 完成后从列表移除

  4. 合规提示: "您的删除请求将在 X 个工作日内完成" (对齐 legal_profile SLA)
```

#### 8.5.4 置信度感知渲染

```
当 AI 回复引用记忆时, 前端根据 confidence 差异化展示:

  confidence >= 0.8:
    正常语气, 无特殊标记
    例: "您之前提到喜欢运动风"

  confidence 0.5-0.8:
    浅色提示图标 + 试探语气
    例: (i) "如果我没记错, 您好像偏好简约风格"

  confidence < 0.5:
    不主动展示, 仅在记忆面板可查看
```

#### 8.5.5 实验变体指示器

```
位置: 用户端底部状态栏 (调试模式可见) / Admin 实验管理页

实现:
  - OrgContext 包含当前 org 的实验分配
  - packages/shared/feature-flags.ts 读取并判定
  - 调试模式 (开发者/内部用户): 底部显示 "Variant: B (exp-042)" 标签
  - 生产模式: 不显示, 但写入 console.debug
  - Admin 端: 实验管理页显示各 org 的分配情况 + 指标对比
```

#### 8.5.6 上下文感知建议芯片 (Context-Aware Suggestion Chips)

```
位置: 输入框下方

设计哲学:
  灵感来源: Manus 通过 token logits masking 在解码层动态启用/禁用工具调用,
  减少无关工具的 token 消耗。DIYU 将此理念映射到前端: 建议芯片不是静态列表,
  而是由后端根据当前对话上下文动态生成, 仅展示与当前场景相关的操作。

数据源 (后端驱动):
  WS 下行消息扩展字段: suggested_actions: SuggestedAction[]
  每条包含: { id, label, intent, priority, expires_at? }
  后端根据以下信号生成:
    - 当前对话意图 (时尚搭配 / 库存查询 / 内容创作 / 通用问答)
    - 最近 Skill 执行结果 (搭配完成 -> 推荐后续操作)
    - 用户历史偏好 (Memory Core personal 记忆)
    - 当前 Skill 可用性 (不可用的 Skill 不生成对应建议)

  后端契约依赖:
    需 Gateway WS 协议扩展 suggested_actions 字段
    (当前 05-Gateway 7.1 未定义此字段, 需后端迭代配合)

场景化示例:
  时尚搭配场景:
    [换个风格] [查看搭配详情] [搜索库存] [保存方案]

  库存查询场景:
    [筛选尺码] [查看详情] [相似推荐] [加入对比]

  内容创作场景:
    [调整语气] [生成更多版本] [翻译为英文] [复制文案]

  通用/首次用户 (降级):
    [帮我推荐穿搭] [品牌介绍] [创作内容]

降级策略:
  suggested_actions 为空/缺失/字段不存在:
    -> 回退为静态通用建议 (首次用户列表)
  回访用户 + 无 suggested_actions:
    -> 基于最近会话标题生成本地建议 [继续上次的搭配] [看看新品]
  对齐 Section 13 向后兼容: 前端不因后端未返回此字段而报错
```

#### 8.5.7 任务进度面板 (Task Progress Panel)

```
场景: 用户发出复合意图 -> Brain 分解为多步 Skill 调用 -> 前端实时展示执行进度

示例:
  用户: "帮我搭配一套商务休闲装并搜索库存"
  进度面板:
    [done]  理解意图: 商务休闲搭配 + 库存检索
    [done]  搭配推荐: 已生成 3 套方案
    [running]  库存查询: 正在检索...
    [pending]  汇总结果

灵感来源:
  Manus 的 todo.md 注意力操控模式 -- Agent 在每步开始时"朗读"任务列表,
  通过注意力机制将任务焦点强制注入上下文, 防止长对话中的任务漂移。
  DIYU 前端将此理念转化为用户可见的进度面板, 既是 UI 透明性,
  也为后端 Context Engineering 提供前端锚点。

数据源:
  消费现有 WebSocket 下行消息:
    - tool_output.status: "started" | "running" | "completed" | "failed"
    - task_complete: 标记整体任务完成
  无需新增 Gateway 端点 (对齐 Step 8 约束: 不引入新 Port)

UI 组件: <TaskProgressPanel />
  位置: 聊天气泡内折叠区域 (点击展开查看详细步骤)
  状态图标: spinner(running) / checkmark(done) / x(failed) / circle(pending)
  折叠逻辑: 单步任务不显示面板; >= 2 步自动展开

降级:
  后端未返回进度事件 -> 不显示面板 (静默降级)
  部分步骤失败 -> 失败步骤标红 + "重试" 按钮 (仅对可重试 Skill)

Phase 区分 (重要):
  V1.1 -- Skill 执行进度: 同步多步 Skill 调用的实时进度 (本节描述)
  Phase 2 -- Task Orchestration: 异步长任务编排 (对齐 01-Brain Section 2.6 预留接口)
  前端预留 TaskOrchestrationPanel 组件槽位, Phase 2 时实现
```

### 8.6 搜索体验

```
+-- 全局搜索栏 (Cmd+K / 顶部固定)
|     |
|     +-- 快速过滤: 全部 | 对话 | 知识 | 商品 | 内容
|     |
|     +-- 意图驱动: 自然语言 -> Chat 流 (走 WebSocket)
|     |
|     +-- 直接搜索: 关键词 -> REST /api/v1/search (若可用)
|
+-- 搜索结果渲染:
      +-- 在 Chat 流中: 使用 Component Registry 渲染
      +-- 在搜索模式中: 独立搜索结果页 (Grid/List 可切换)
```

### 8.7 订阅与点数计费感知

```
计费规则 (单租户):
  - 基础订阅: 299 元/月
  - 含额度: 100 元等值 Token (按千问官网价格 1:1 映射)
  - 超额购买: 最低 100 元起购
  - 点数价值: 100 元购买 -> 33 元等值千问 Token
  - 商业定价说明: 超额点数采用约 3:1 商业加价, 属于平台收入模型设计, 非计费换算 bug
  - 点数累积: 购买点数当月未用完可累积, 与订阅额度平行

UI 组件:
  - <UsageQuotaBar />: "本月额度 67/100 元"
  - <PointsBalance />: "点数余额 XX 元"
  - <RechargeEntry />: owner/admin 可见, 最低 100 元起购

数据源:
  - GET /api/v1/billing/usage
  - GET /api/v1/billing/points-balance
  - SSE: budget_warning (80%/95%/100%)

交互:
  - 80%: "本月额度即将用完"
  - 95%: "本月额度接近上限"
  - 100%: "本月额度已用完, 请购买点数继续使用"

HTTP 402 处理:
  - 显示计费专用弹窗, 文案包含:
    1) 本月订阅额度已耗尽
    2) 点数余额不足
    3) 购买入口 (最低 100 元)
  - 不作为通用错误 toast
```

### 8.8 限流处理

```
后端返回:
  X-RateLimit-Limit: 60
  X-RateLimit-Remaining: 3
  X-RateLimit-Reset: 1707465600

前端策略:
  Remaining < 5: 输入框下方显示 "请求频率接近上限"
  429 Too Many Requests:
    -> 显示 "请稍后再试" + 基于 Reset 的倒计时
    -> 指数退避重试 (1s -> 2s -> 4s, 最多 3 次)
    -> 超过重试次数: 提示用户稍后再试

  packages/api-client/rest.ts 内置限流拦截器:
    - 自动解析 X-RateLimit-* headers
    - 队列化请求以避免触发限流
```

### 8.9 状态管理策略

```
+-- Server State (TanStack Query)
|     +-- 组织列表/详情
|     +-- 成员列表
|     +-- 知识库条目
|     +-- 内容审核队列
|     +-- 计费用量数据
|     +-- 实验配置
|     +-- 我的记忆列表 + 删除状态
|     策略: staleTime 按数据类型配置, mutation 触发 invalidation
|
+-- Chat State (AI SDK useChat via DiyuChatRuntime)
|     +-- 当前对话消息列表
|     +-- streaming 状态 (ready/submitted/streaming/error)
|     +-- tool call 进度
|     +-- Artifact 数据
|     策略: 内存管理, 会话切换时清理/恢复
|
+-- Client State (Zustand)
|     +-- 当前组织上下文 (org_id, role, permissions)
|     +-- UI 偏好 (sidebar, theme, layout)
|     +-- 通知队列
|     +-- Feature Flags
|     +-- 降级状态 (degraded_reasons 集合)
|     +-- 当前轮次 injection_receipt (记忆透明面板数据)
|     策略: persist 到 localStorage (非敏感数据)
|
+-- Form State (React Hook Form)
      +-- 表单数据 (仅在表单生命周期内)
      +-- 验证状态
      策略: 局部状态, 提交后释放
```

### 8.10 降级 UI 总览

```
对齐后端降级策略 (00 Section 11):

  Knowledge Stores 不可用:
    -> 隐藏知识搜索入口
    -> 对话仍可用 (Brain + Memory Core 是硬依赖)
    -> 顶部 Banner: "部分功能暂不可用, 知识检索已暂停"

  某 Skill 不可用:
    -> 对应功能按钮灰化 + tooltip "该功能暂时不可用"
    -> 其他 Skill 不受影响

  LLM 超时/失败:
    -> 显示 "思考中..." 后接超时提示
    -> 提供 "重试" 按钮
    -> 部分回复保留 (已收到的 chunk 不丢弃)

  WebSocket 断开:
    -> 自动重连 (指数退避)
    -> 重连期间显示 "连接中..." 状态条
    -> 5 分钟内 session 可恢复

  网络完全断开:
    -> 所有发送按钮禁用
    -> 显示 "网络连接已断开" Banner
    -> 已加载的对话历史仍可浏览
```

### 8.11 浏览器原生能力与基础交互补全

```
A-1  多模态输入: 图片上传/粘贴/DnD + 预览删除 + capability 灰化
A-2  图片生成卡片: image_generation 组件 + 下载/收藏
A-3  复制能力: 消息/代码块 Clipboard API 一键复制 + Toast
A-4  粘贴策略: 富文本降级纯文本, 图片走上传, 代码保留缩进
A-5  通知能力: SSE system_notification -> Notification API (仅后台标签页)
A-6  页面可见性: visibilitychange 后心跳降频与回前台状态校验
A-7  网络检测: navigator.onLine + 自动重连 + 消息补发
A-8  全屏能力: Artifact Fullscreen API + ESC 退出
A-9  分享能力: 复制链接/二维码; Web Share 仅预留接口
A-10 导出能力: 对话/Artifact 导出 PDF/文本 + @media print
A-11 语音 I/O: 当前仅接口抽象预留, Phase 4 实装
A-12 存储监控: navigator.storage.estimate() + 80% 告警 + LRU 清理
A-13 输入增强: auto-resize、字数提示、Enter/Shift+Enter 规则
A-14 消息操作: 复制/重新生成/点赞/点踩 (最后一条 AI 才可重生)
A-15 滚动体验: 流式跟随、手动上滑暂停、回到底部按钮
A-16 加载反馈: 路由骨架、组件级 loading、typing indicator
```

### 8.12 补充交互规范 (D 类细化)

```
D-2 会话管理 UX:
  - Token 即将过期: 弹窗提示 "会话即将过期, 是否续期?"
  - 多设备互踢: 收到冲突登录事件后提示并回到登录页
  - 未保存内容离开: beforeunload 拦截 + 二次确认

D-3 多标签页协调:
  - 使用 BroadcastChannel 同步登录/登出状态
  - 主标签页维持 WS, 从标签页复用消息广播
  - 主标签页关闭时从标签页自动竞选新主标签页

D-5 表单草稿恢复:
  - knowledge-edit/content 表单每 30s 自动保存草稿 (IndexedDB)
  - 意外关闭后进入页面提示恢复
  - 脏数据检测: 路由离开二次确认

D-6 深度链接与 URL 状态:
  - 对话深链: /chat/{session_id}
  - Admin 列表页筛选/排序/分页状态持久化到 query string
  - 刷新后恢复页面状态, 支持复制链接协作排障
```

---

## 9. Admin Console 设计 (Step 9)

Admin Console (Step 9) 独立应用, 对齐后端 Admin API: /api/v1/admin/*

### 9.1 核心页面

```
Admin Console 入口规则:
  - platform: 完整 Admin
  - brand_hq(owner/admin): 品牌级 Admin
  - 其他层级与角色: 302 到 apps/web

(dashboard)/ 路由组 -- brand_hq(owner/admin) 可见:
+-- Dashboard         # 品牌概览
+-- Organizations     # 组织树管理 + 门店增减审批
+-- Members           # 品牌全级成员管理 (唯一业务层入口)
+-- Knowledge         # 品牌知识库
|   +-- import-review/ # 下级提交知识下载/导入状态
|   +-- local-life/    # 本地生活知识库
|   +-- store-nodes/   # 全国门店图谱节点
+-- Content Review    # 内容审核工作流 (默认关闭, 开启后展示)
+-- Experiments       # A/B 实验管理
+-- Billing           # 订阅/点数/用量报表
+-- Settings          # RULE + BRIDGE + BrandTone + 人设 + Skill/Tool 白名单
+-- Audit             # 品牌审计日志

(platform-ops)/ 路由组 -- 仅 platform 可见:
+-- tenant-overview/      # 租户总览
+-- tenant-detail/[org_id]/ # 租户详情 + 配额 + 豁免
+-- model-registry/       # 全局模型注册表
+-- model-pricing/        # 千问官网价格映射
+-- subscription-plans/   # 套餐和点数包配置
+-- billing-global/       # 全平台账单
+-- global-config/        # 全局默认配置
+-- security-config/      # 安全与合规
+-- system-ops/           # 运维监控
+-- global-knowledge/     # 平台级知识模板

路由守卫:
  apps/admin 入口 TierGate:
    if (org_tier === 'platform') allow
    else if (org_tier === 'brand_hq' && role in ['owner', 'admin']) allow
    else redirect to apps/web
  Phase 0: 骨架页面 + placeholder ("功能开发中")
  Phase 2: 接入后端 API 后实现完整功能
```

### 9.2 UI 库混合策略 (FE-008)

apps/admin 采用 shadcn/ui 基础 + Ant Design 企业组件:

| 组件需求 | 来源 | 理由 |
|---------|------|------|
| Button, Input, Card, Dialog | shadcn/ui | 与 packages/ui 统一 |
| 5 层组织树 (ltree) + 拖拽 | Ant Design Tree | 开箱即用, 自建成本 ~2 人周 |
| 复杂数据表 (服务端分页/排序/过滤) | TanStack Table + shadcn/ui | 灵活度高 |
| 级联选择器 (组织/区域/门店) | Ant Design Cascader | 开箱即用, 自建成本 ~1 人周 |
| 审批工作流状态 | Ant Design Steps + Timeline | 语义完整 |
| 复杂表单 (条件显隐/嵌套/数组) | React Hook Form + shadcn/ui | 控制力更强 |
| 日期范围/时间选择 | Ant Design DatePicker | 国际化完整 |
| 统计卡片/数据概览 | Ant Design Statistic | 开箱即用 |

样式隔离:
  - Ant Design 组件通过 CSS 前缀隔离 (ConfigProvider prefixCls="diyu-admin")
  - Tailwind 与 antd 样式不冲突 (Tailwind 的 preflight 对 antd 组件跳过)
  - packages/ui 的 shadcn/ui 组件在 Admin 中正常使用

依赖管控:
  - Ant Design 仅在 apps/admin/package.json 中声明
  - packages/ui 不依赖 Ant Design (保持纯净)
  - 按需引入: babel-plugin-import 或 Tree Shaking

### 9.3 技术特点

```
+-- RSC (React Server Components): 数据密集型表格/报表 (SaaS 模式)
+-- 私有化降级: output:'export' 时 RSC 降级为客户端渲染 (FE-001)
+-- DataTable: TanStack Table + 服务端分页/排序/过滤
+-- 组织树可视化: Ant Design Tree (5 层, LTREE 路径)
+-- 实时: SSE /events/* 接收配置变更通知
+-- 权限: 每个页面/操作绑定 *.manage 权限码
```

### 9.4 Admin 各模块详细设计

```
9.4.1 组织树导航 (organizations/)
  - 树形展示: brand_hq > brand_dept/regional_agent > franchise_store
  - brand_hq 可直接新增/调整区域代理与门店
  - regional_agent 门店增减仅可发起申请, 由 brand_hq 审批后执行
  - 约束说明: 门店增减申请不等于成员管理/人员变动; 区域团队人员变动统一由 brand_hq 在 members 模块处理

9.4.2 成员管理 (members/)
  - 仅 platform 与 brand_hq(owner/admin) 可见
  - brand_hq 负责品牌全级成员邀请/移除/角色变更
  - 门店账号遵循 1 主 + 1 备用, 由 brand_hq 统一管理

9.4.3 配置管理 (settings/)
  - 配置项列表, 每项标注约束类型:
      LAW:    灰色锁图标, 只读, "系统强制"
      RULE:   可编辑输入框
      BRIDGE: 可编辑 + "子组织不可覆盖" 标签
  - 继承来源: "继承自 [品牌名]" 提示
  - 品牌规则重点:
      content_policy / review_flow / content_restrictions
      allowed_models / fallback_chain / skill_whitelist / tool_whitelist
      brand_tone / personas / knowledge_visibility_acl
  - 保存时校验: is_locked 项阻止子组织修改
  - review_flow 默认值为 none (内容审核默认关闭)

9.4.4 知识库管理 (knowledge/)
  - 品牌知识库: 产品信息/品牌规范/SOP CRUD
  - import-review: 下级提交内容查看/下载(供运维人工格式转换)/手动导入/状态记录
  - local-life: 本地生活内容生产知识库
  - store-nodes: 全国门店图谱节点实体管理

9.4.5 实验管理 (experiments/)
  - 品牌级 A/B 实验 (Prompt 版本/模型选择/策略)
  - 实验列表: 名称、状态、分组比例、关键指标

9.4.6 计费与用量 (billing/)
  - 基础订阅: 299 元/月
  - 含额度: 100 元等值 Token (1:1 官网价格映射)
  - 超额点数: 最低 100 元起购; 100 元=33 元等值 Token
  - 商业定价说明: 超额点数约 3:1 加价, 作为平台利润模型; 订阅内额度仍按 1:1
  - 视图: 本月额度消耗、点数余额、下级组织用量汇总、充值记录
  - 预警: 80%/95%/100% 阶段提示

9.4.7 审计日志 (audit/)
  - 全链路操作记录 (时间、操作者、动作、目标)
  - 筛选: 时间范围、操作类型、操作者、敏感操作
  - 导出 (CSV)

9.4.8 模型配置 -- 品牌级 (settings/ 内嵌)  [Phase 0]
  - brand_hq 配置 allowed_models 范围 (受 platform 交集约束)
  - 终端用户在 Web 对话页自由切换, 中间层级不二次管控
  - 模型展示: 名称 + 能力标签 + 参考价格

9.4.9 模型注册表 -- 全局 (platform-ops/model-registry/)  [Phase 2]
  - 仅 platform 可见
  - CRUD: ModelDefinition (model_id, provider, capabilities, tier, pricing, status)
  - 默认供应商策略: 千问主力模型库作为默认模型池 (文本 + 多模态)
  - 价格策略: 自动拉取/同步千问官网定价并映射到 model-pricing
  - 平台可维护 fallback 链默认值; 品牌层仅在 allowed_models 范围内选择

9.4.10 知识可见性分区 (knowledge/)  [Phase 2]
  - visibility 标签: global | brand | region | store
  - 节点 ACL 矩阵: 哪些组织可见/可检索
  - 门店内容生产默认检索: 本店记忆 + 总部知识 + 门店图谱 + 本地生活知识

9.4.11 配置管理增强 (settings/)  [Phase 0]
  - effective-settings 只读面板: 展示当前组织的最终生效配置 (合并继承链后)
  - 来源标注: 每项配置标注 "本级设置" / "继承自 [父组织名]" / "系统默认(LAW)"
  - 需后端 GET /api/v1/admin/effective-settings API (见 Section 22 Backlog)

9.4.12 引导向导 (onboarding/)  [Phase 2]
  - 新品牌首次登录引导: 基本信息 -> 模型选择 -> 知识导入 -> 完成
  - 步骤状态持久化 (防中途退出丢失进度)
  - 可跳过, 跳过后 Dashboard 显示待完成提示

9.4.13 通知中心 (notifications/)  [Phase 2]
  - 消费 SSE /events/* 推送 (05 Section 1)
  - 通知类型: 配置变更 / 审核请求 / 额度告警 / 系统公告
  - 已读/未读状态, 全部标记已读
  - 铃铛图标 + 未读计数 badge

9.4.14 多会话管理 -- 用户端 (apps/web)  [Phase 2]
  - 侧边栏会话列表: 会话标题 + 最后消息时间 + 未读标记
  - 新建/切换/归档会话
  - 切换时清理当前 Chat State, 恢复目标会话上下文
  - 对齐 05 Section 7.1 WebSocket 按会话连接语义

9.4.15 人设管理 (settings/personas)  [Phase 2]
  - 多人设模板: 品牌官方 / VLOG / 培训 / 活动等
  - UI: 列表 CRUD + 默认人设标记 + Prompt 片段编辑器 + 适用场景标签
  - 发布策略: 草稿/生效版本双态; 生效版本进入 Web 模型辅助提示

9.4.16 培训内容管理 (training)  [Phase 2]
  - 入口: regional_agent Web App + brand_hq Admin 审阅页
  - 流程: 区域生成培训材料 -> 提交 -> 总部审核发布
  - UI: 模板选择、章节编辑、状态流转、导出与归档

9.4.17 库存关联能力 (store inventory)  [Phase 2]
  - 门店端在对话与搭配页可查看库存关联推荐 (有库存系统时启用)
  - UI: "库存可售/缺货/替代款" 标签 + 一键替换搭配项
  - 降级: 无库存集成时隐藏库存标签, 保留通用搭配推荐
```

### 9.5 Platform-Ops 各模块详细设计

```
9.5.1 tenant-detail/[org_id]
  - 字段: 租户状态(正常/暂停/欠费)、配额、豁免类型与有效期
  - 操作: 暂停/恢复/删除租户 (危险操作二次确认)
  - UI: 详情卡 + 操作抽屉 + 风险确认弹窗

9.5.2 model-pricing
  - 字段: provider/model_id/capabilities/官网单价/生效时间
  - 操作: 官网价格同步(手动触发 + 失败重试) + 差异对账
  - UI: 价格对照表 + 同步状态徽标

9.5.3 subscription-plans
  - 字段: 基础套餐(299/月含100元额度)、点数包(最低100元起购)、折算规则
  - 操作: 套餐启停、版本发布、生效时间控制
  - UI: 套餐卡片 + 规则表单 + 发布记录

9.5.4 billing-global
  - 字段: 平台收入、应收、欠费、租户消耗分布
  - 操作: 欠费策略配置(N天后降级/暂停)
  - UI: 总览图表 + 可穿透租户账单明细

9.5.5 security-config
  - 字段: 全局 forbidden_words(LAW)、登录安全策略、数据保留期
  - 操作: 策略版本化发布 + 回滚
  - UI: 分区表单 + 变更审计侧栏

9.5.6 system-ops
  - 字段: Gateway/Brain/Memory/Knowledge 健康状态、告警、维护窗口
  - 操作: 维护模式开关、全局公告发布
  - UI: 状态大屏 + 时间轴 + 公告编辑器

9.5.7 global-knowledge
  - 字段: 平台通用模板、行业模板、RAG 默认参数
  - 操作: 模板 CRUD、版本生效控制
  - UI: 模板列表 + 版本对比 + 发布按钮
```

---

## 10. UI/UX 设计规范

### 10.1 视觉基调

```
美学定位: "高级简约" -- 对齐时尚行业审美

色系:
  默认深色模式 (Dark mode)
  支持浅色模式切换
  玻璃拟态 (backdrop-blur) 面板效果

响应式: PC-first (移动端预留)
  - 当前主交付: 桌面端双栏工作台 + Admin 表格密集操作
  - 移动端策略: 保持路由与组件接口兼容, Phase 4 再启用完整适配
  - 触摸手势/语音输入: 仅预埋抽象层
```

### 10.2 时尚领域专属组件

```
packages/ui/commerce/:

  <ProductCard>       SKU 信息 + 图片 + 价格 + 兼容性标签
  <OutfitGrid>        搭配组合 (上装+下装+鞋+配饰), 可替换单品
  <StyleBoard>        风格灵感面板 (图片 + 关键词标签)
  <SizeGuide>         嵌入式尺码表
  <ColorPalette>      色系选择器
```

### 10.3 键盘快捷键

```
Cmd+K          全局搜索
Cmd+N          新对话
Cmd+Shift+M    查看 AI 记忆面板
Cmd+Shift+B    查看 Artifact 收藏
Cmd+Shift+H    对话历史文件夹
Cmd+Shift+K    知识编辑工作区
Enter          发送消息
Shift+Enter    换行
Escape         关闭右栏 Artifact / 关闭弹窗
```

---

## 11. 实验引擎集成

```
后端 Experiment Engine (06 Section 4) 提供 5 维度实验能力:
  Skill / Brain / Knowledge / Prompt / Model

前端集成:

  1. 获取实验分组:
     登录后 GET /api/v1/experiments/assignments
     -> 返回当前用户的所有活跃实验分组
     -> 存入 Zustand store

  2. 条件渲染:
     Hook: useExperiment(experimentId) -> { variant, metadata }

     不硬编码任何实验逻辑:
       const { variant } = useExperiment('new-chat-layout');
       if (variant === 'treatment') return <NewChatLayout />;
       return <DefaultChatLayout />;

  3. 事件上报:
     用户交互事件自动关联 experiment_assignment_id
     -> 后端用于分析实验效果

  4. Feature Flags:
     实验未启用时 = 默认变体
     新功能通过实验 Flag 关闭, 后端支持后渐进开放
```

---

## 12. 安全设计

| 威胁 | 防御 |
|------|------|
| XSS | DOMPurify 清洗所有 AI 生成内容; CSP 策略; HTML 内联禁止 (对齐 01 Section 4.3) |
| Token 泄露 | SaaS: HttpOnly Cookie (JS不可读); Private: 内存Token + CSP严格策略 |
| CSRF | SaaS: SameSite Cookie + CSRF Token (状态变更操作); Private: N/A (无Cookie) |
| 数据泄露 | 前端不缓存敏感数据; 切换组织清理全部状态 |
| 越权操作 | 前端仅做 UI 提示, 真实校验在 Gateway |
| Prompt Injection | 前端输入框基础过滤 + 后端 Sanitization (01 层) |
| WS 劫持 | WSS + Token 认证 + 心跳检测 |
| 记忆数据隐私 | 记忆面板仅展示当前用户自己的记忆; Admin 不展示 Memory Core 原始数据 |

---

## 13. 向后兼容策略

前端向后兼容三原则 (对齐后端 Expand-Contract):

```
1. 未知消息类型宽容:
   - 收到未知 tool_output.type -> Component Registry 查无匹配 -> JsonViewer (不崩溃)
   - 收到未知字段 -> 忽略 (TypeScript 用 Record<string, unknown> 兜底)
   - 收到新版本 Schema -> 仅使用已知字段
   - DiyuChatRuntime 收到未知 WS 消息类型 -> 记录 warning, 不中断流

2. Feature Flags 前置:
   - 新功能通过 org_settings 中的 Feature Flag 控制
   - 前端在 Flag=false 时隐藏入口, 不请求新 API
   - 后端升级 -> 打开 Flag -> 前端自动展示
   - packages/shared/feature-flags.ts 提供统一判定接口

3. API 版本感知:
   - api-client 层适配 /api/v1/ 和未来 /api/v2/
   - 切换版本在 api-client 内部完成, 不影响上层组件
   - 使用 OpenAPI 生成类型, 升级时 diff 检查 breaking changes
```

---

## 14. 部署策略

### 14.1 部署模式差异化 (FE-001)

```
+-----------+-----------------------------+------------------------------+
| 部署模式   | apps/web (用户端)            | apps/admin (管理端)           |
+-----------+-----------------------------+------------------------------+
| SaaS      | Vercel/Cloudflare 部署       | Vercel/内部集群部署            |
|           | 完整 Next.js (RSC 可用)      | 完整 Next.js (RSC 可用)       |
|           | CDN 边缘缓存                 | 内部网络, 不暴露公网           |
+-----------+-----------------------------+------------------------------+
| Private   | output:'export' -> 纯静态     | output:'export' -> 纯静态     |
|           | nginx:alpine 容器 (6MB)      | nginx:alpine 容器 (6MB)       |
|           | 零 Node.js 依赖              | RSC 降级为客户端渲染           |
|           | /api/* 反代到后端容器          | /api/* 反代到后端容器           |
+-----------+-----------------------------+------------------------------+
| Hybrid    | 同 Private                   | 同 Private                   |
+-----------+-----------------------------+------------------------------+
```

构建切换:

```
DEPLOY_MODE=saas    -> 标准 Next.js build (保留 RSC/SSR)
DEPLOY_MODE=private -> next.config.ts 设置 output:'export' (纯静态)

// next.config.ts
const config = {
  output: process.env.DEPLOY_MODE === 'private' ? 'export' : undefined,
  // ...
}
```

Docker 镜像策略:

```
SaaS:    node:22-slim 基础镜像, 运行 Next.js server
Private: nginx:alpine 基础镜像, 仅挂载 out/ 静态目录 + nginx.conf (反代)
```

影响评估:

```
Private 模式下 RSC 不可用 -> Admin 的数据表格退化为客户端渲染
影响: 首屏加载略慢 (JS bundle 包含表格渲染逻辑)
缓解: 代码分割 + 路由级懒加载, 实际体感差异可控 (Admin 面向内部用户)

Private 模式下 BFF 不可用 -> 认证降级为 BearerAuthStrategy
影响: XSS 防护从 HttpOnly Cookie 降级为内存 Token
缓解: 私有网络隔离 + CSP 严格策略 (见 FE-010)
```

### 14.2 SSR 策略表

| 页面类型 | 渲染策略 | 理由 |
|----------|---------|------|
| 登录/注册 | SSR | SEO + 首屏速度 |
| 聊天主界面 | CSR | 实时交互, 无 SEO 需求 |
| AI 记忆面板 | CSR | 个人数据, 无 SEO 需求 |
| Artifact 收藏 | CSR | 个人数据, IndexedDB 驱动 |
| 对话历史文件夹 | CSR | IndexedDB 驱动, 强交互 |
| 知识编辑工作区 | CSR | 表单密集交互, 无 SEO 需求 |
| 区域门店看板 | SSR + Hydration | 聚合展示, 首屏可读性高 |
| 充值/点数购买页 | CSR | 支付流程与安全交互优先 |
| Platform 租户管理 | SSR + Hydration | 数据量大, 首屏快 |
| Platform 运维监控 | CSR | 实时刷新/长连接驱动 |
| 公开知识页 (若有) | SSG/ISR | 内容稳定, 可缓存 |

> Private 模式下所有 SSR 页面自动降级为 CSR (output:'export' 约束)。

### 14.3 部署拓扑

```
apps/web   -> Docker 镜像 -> CDN 边缘 (SaaS) / nginx 容器 (Private)
                                |
apps/admin -> Docker 镜像 -> 内部网络 (SaaS) / nginx 容器 (Private)
                                |
                          Gateway API <------- 后端服务
```

### 14.4 CI/CD

```
PR -> Lint + TypeCheck + Unit Test (Turbo 增量) + Bundle Size Check + a11y Check
Merge to main -> Build (both DEPLOY_MODE) + E2E Test -> Deploy to Staging
Release Tag -> Production Deploy (SaaS + Private 双产物)
```

---

## 15. 工程质量

### 15.1 性能预算

```
Core Web Vitals 目标:
  LCP (Largest Contentful Paint):  < 2.5s
  FID (First Input Delay):        < 100ms
  CLS (Cumulative Layout Shift):  < 0.1

Bundle Size (gzipped):
  apps/web 首屏:  < 200KB
  packages/ui:    < 50KB (tree-shakeable)

流式性能:
  首个 AI chunk 到达后 < 50ms 渲染
  WS 重连: < 5s (P95)
```

### 15.2 无障碍 (Accessibility)

```
目标: WCAG 2.1 AA

Radix 提供基础无障碍原语 (focus management, aria attributes)

额外要求:
  - ESLint: eslint-plugin-jsx-a11y 强制检查
  - 测试: axe-core 集成到 CI (Playwright + @axe-core/playwright)
  - 聊天气泡: aria-live="polite" (AI 流式回复实时播报)
  - 颜色对比度: 深色/浅色模式均满足 4.5:1 比率
  - 键盘导航: 所有功能可通过键盘操作
```

### 15.3 错误边界

```
策略: 功能区域独立 ErrorBoundary

  全局 ErrorBoundary
    +-- Chat ErrorBoundary        (AI 失败不影响导航)
    |     +-- MessageList
    |     +-- StreamingIndicator
    |     +-- TaskProgressPanel
    +-- Artifact ErrorBoundary    (渲染失败降级为 JSON)
    |     +-- SkillRenderer
    |     +-- MemoryContextPanel
    +-- Memory ErrorBoundary      (记忆面板独立)
    +-- Admin ErrorBoundary       (管理功能独立)

错误上报:
  ErrorBoundary 捕获 -> 本地降级 UI + 上报到监控 (Sentry/自建)
  不显示技术细节给用户, 仅 "出了点问题, 请重试"
```

### 15.4 测试策略

```
层级          | 工具                    | 覆盖率目标
单元测试      | Vitest                  | 工具函数、api-client: > 80%
组件测试      | Vitest + Testing Library | 核心组件: > 70%
E2E 测试      | Playwright              | 关键用户路径: 100%
无障碍测试    | axe-core + Playwright   | 所有页面
契约测试      | 基于 OpenAPI spec 校验   | api-client types 与后端同步

关键 E2E 路径:
  1. 登录 -> 选择组织 -> 发起对话 -> 收到流式回复
  2. 对话中触发 Skill -> 右栏展示结构化内容
  3. 对话中上传图片 -> 模型识别并回复
  4. 创建历史文件夹 -> 拖拽归类 -> 切换文件夹视图验证
  5. 知识编辑 -> 填写模板 -> 提交 -> 总部查看提交列表
  6. 额度耗尽 -> 购买点数 -> 余额更新
  7. 区域代理 -> 门店看板 -> 申请新增门店 -> 总部审批
  8. TierGate: 门店账号访问 Admin -> 302 到 Web App
  9. 查看 AI 记忆 -> 删除一条记忆 -> 确认删除
  10. Admin: 切换组织 -> 修改配置 -> 子组织继承验证
```

### 15.5 API 契约生成

```
管线:
  后端发布 OpenAPI spec (YAML)
    -> CI: openapi-typescript 生成 packages/api-client/types/
    -> CI: 类型校验确保前后端一致
    -> 破坏性变更自动报警 (schema diff)

  WebSocket 消息类型:
    手动维护 TypeScript 类型 (packages/api-client/types/chat.ts)
    每个版本 tag 对应一份 ws-types snapshot
```

---

## 16. 权衡分析

### 16.1 框架选型

| 方案 | 优点 | 缺点 | 裁决 |
|------|------|------|------|
| Next.js 15 (App Router) | RSC 性能好、AI SDK 原生支持、SSR/SSG、成熟生态 | 私有化部署需 Node.js 或 static export 降级 | 选用, 私有化通过 FE-001 策略解决 |
| Vite + React SPA | 极速 HMR、轻量、纯静态部署 | 无 SSR、AI SDK 集成需额外工作、需自建路由 | 不选 |
| Remix | 优秀的数据加载模型、Progressive Enhancement | AI SDK 集成弱、生态小 | 不选 |

### 16.2 AI Chat 组件策略

| 方案 | 优点 | 缺点 | 裁决 |
|------|------|------|------|
| assistant-ui + AI SDK + Custom Runtime | 专业 Chat UX、streaming/retry 内置、shadcn 原生 | 需自研 DiyuChatRuntime 适配器 (约 1-2 人周) | 选用, 适配成本 << 自研 Chat UI 成本 |
| 自研 Chat UI (参考 AI SDK Data Stream Protocol) | 完全控制、无外部依赖 | 工程量大 (6-8 人周)、容易遗漏边界场景 | 备选 (FE-009 降级方案) |
| CopilotKit | 全功能 AI 交互框架 | 过重、侵入性强、与笛语架构冲突 | 不选 |

### 16.3 UI 库策略

| 方案 | 优点 | 缺点 | 裁决 |
|------|------|------|------|
| shadcn/ui (Web) + shadcn/ui + Ant Design 混合 (Admin) | 各场景最佳工具; Chat 轻量定制, Admin 企业开箱即用 | Admin 两套 UI 库需样式隔离 | 选用, 工程务实 |
| 全局 shadcn/ui | 统一一致 | Admin 企业组件 (Tree/Cascader/Steps) 需自建 ~3-5 人周 | 不选 (除非团队有充裕前端产能) |
| 全局 Ant Design | 企业组件齐全 | 与 assistant-ui/Tailwind 生态不一致, Chat UI 定制受限 | 不选 |

### 16.4 状态管理策略

| 方案 | 优点 | 缺点 | 裁决 |
|------|------|------|------|
| Zustand + TanStack Query + AI SDK + RHF | 四状态源各司其职、无冗余、类型安全 | 4 个状态源需要协调 | 选用 |
| Redux Toolkit | 统一模型、DevTools 强 | Boilerplate 多、对 AI Chat 场景过重 | 不选 |
| Jotai/Recoil | 原子化、细粒度 | 与 TanStack Query 功能重叠 | 不选 |

### 16.5 Monorepo 策略

| 方案 | 优点 | 缺点 | 裁决 |
|------|------|------|------|
| Turborepo + pnpm | 增量构建、远程缓存、简单配置 | 功能不如 Nx 丰富 | 选用 |
| Nx | 功能最全、依赖图分析 | 配置复杂、学习曲线陡 | 不选 |
| Rush.js (Coze 模式) | 大规模项目验证 | 配置繁琐、社区相对小 | 不选 |

### 16.6 实时通信策略

| 方案 | 优点 | 缺点 | 裁决 |
|------|------|------|------|
| WebSocket (Chat) + SSE (Events) + REST (CRUD) | 各协议匹配场景、与后端契约对齐 | 需维护 3 种客户端 | 选用 |
| 全 WebSocket | 协议统一 | CRUD 用 WS 不自然、缓存困难 | 不选 |
| 全 REST + Polling | 简单 | 延迟高、体验差 | 不选 |

### 16.7 认证策略

| 方案 | 优点 | 缺点 | 裁决 |
|------|------|------|------|
| 认证策略工厂 (SaaS: Cookie+BFF / Private: Bearer) | 安全性按部署模式最优化; 上层代码无感知 | 两套认证逻辑需维护 | 选用 (FE-010) |
| 全局 HttpOnly Cookie + BFF | 安全性最高 | output:'export' 下 BFF 不可用 | 不选 (与 FE-001 冲突) |
| 全局 Bearer Token | 简单统一 | SaaS 公网暴露下 XSS 风险 | 不选 |

---

## 17. 实施步骤

### Phase 0: 基础骨架 + Admin 骨架

```
1.  初始化 Turborepo + pnpm monorepo
2.  创建 apps/web (Next.js 15 App Router)
3.  创建 packages/ui (shadcn/ui + 主题 + 深色/亮色模式)
4.  创建 packages/api-client (REST + WebSocket 客户端 + 认证策略工厂 + DiyuChatRuntime 骨架)
5.  创建 packages/shared (Zod schemas, 权限工具, feature-flags, org-tiers, settings-constraints)
6.  搭建 CI pipeline (lint + type-check + test + bundle-size-check + a11y-check)
7.  验证 DEPLOY_MODE=private 纯静态构建 + nginx 容器部署
8.  验证认证策略工厂两种模式均可运行
9.  创建 apps/admin 骨架 (Next.js 15 + Ant Design + 样式隔离 + 路由组结构)
10. Admin: TierGate 落地 (platform 全开; brand_hq 仅 owner/admin; 其他 302 到 Web)
11. Admin: 配置管理基础 (LAW/RULE/BRIDGE 可视化 + review_flow 默认 none)
12. Admin: effective-settings 只读面板 (需后端 API, 见 Section 22)
```

### Phase 1: 核心对话

```
13. 实现 DiyuChatRuntime (AI SDK Custom Runtime 适配笛语 WS 协议)
14. 集成 assistant-ui, 实现 Chat 基础流
15. WebSocket 连接管理器 (认证/心跳/重连/续传 + Append-Only 约束)
16. 对话输入多模态支持 (图片上传/粘贴/DnD + multimodal_message 上行)
17. 对话消息列表 + streaming 渲染 + typing indicator
18. 消息复制/代码复制 + 重新生成 + 点赞/点踩
19. 流式自动滚动 + 回到底部按钮 + 输入框 auto-resize
20. 对话页模型选择器 + 点数余额/额度展示
21. 基础 Component Registry 扩展 (image_generation / knowledge_template / store_dashboard)
22. 双栏布局 (Chat + Artifact 切换) + DegradationBanner
23. 错误体验基础: ToastProvider + 路由级 ErrorBoundary + WS 断线横幅
```

### Phase 2: 三大场景 + 记忆 + Admin 完善

```
24. 搜索体验 (全局搜索栏 + 意图驱动)
25. 内容生产视图 (ContentEditor + Preview)
26. 陈列搭配视图 (MerchandisingGrid + DisplayGuide)
27. 对话历史文件夹管理 (history/folders + upload)
28. 知识编辑工作区 (knowledge-edit/templates/drafts/submitted)
29. 门店本地知识文件夹 (IndexedDB + 服务端同步)
30. 区域代理门店看板 + 门店增减申请流程
31. 总部知识库扩展 (import-review/local-life/store-nodes)
32. 计费模型重建 UI (订阅+点数+充值流程)
33. 浏览器通知 + 页面可见性管理 + 网络离线恢复
34. 组织切换 + OrgContext 管理 + PermissionGate
35. 记忆管理页 + 记忆注入透明面板
36. Context-Aware Suggestion Chips + Task Progress Panel
37. Admin: 组织/成员/审核/实验/审计页面完善
38. Admin: 平台运营扩展 (tenant-detail/model-pricing/subscription-plans/billing-global)
39. Admin: 通知中心 + 引导向导
40. 用户端: 多会话管理
41. 区域培训内容管理 (training 生成/提交/审核流)
42. 门店库存关联 UI (可售/缺货/替代款展示)
```

### Phase 3: 品牌定制 + 打磨

```
43. 分享功能 (链接/二维码) + 对话/Artifact 导出 PDF
44. 全屏 API + 长对话虚拟滚动
45. 客户端遥测 (Web Vitals/异常/关键路径埋点)
46. 性能优化 (代码分割、懒加载、Private 构建体积优化)
47. E2E 测试套件 (关键路径 100% 覆盖)
48. Storybook 组件文档
49. 实验变体指示器 (调试模式)
50. 品牌主题定制 (需后端 org_settings.branding 扩展)
51. Artifact 跨会话引用 ("@" 选择器)
52. 无障碍审计 + 修复
```

### Phase 4: 长期演进

```
53. 打印样式完善
54. 移动端适配 (响应式 + 触摸手势 + 语音输入)
55. i18n 多语言启用
56. 离线 PWA / Service Worker (评估后启用)
57. 高级分析面板 (跨组织对比/趋势预测)
```

---

## 18. 设计决策记录 (ADR)

| ADR | 决策 | 理由 |
|-----|------|------|
| FE-001 | Next.js 15 App Router + DEPLOY_MODE 双模式构建 | SaaS: 完整 RSC; Private: output:'export' 纯静态, nginx 部署, 零 Node.js 依赖 |
| FE-002 | assistant-ui (非自研 Chat UI), 自研 Hook 作降级备选 | 专业 AI Chat 组件, 减少 6-8 人周工作量; 保留完全控制退路 |
| FE-003 | 四状态源分治 (Zustand + TanStack + AI SDK + RHF) | 各司其职, 避免单一方案的妥协 |
| FE-004 | Component Registry (非硬编码 switch) | 新 Skill 可注册组件而非修改代码, 与后端"扩展通过注册"对齐 |
| FE-005 | Web/Admin 独立应用 (非统一 SPA) | 安全隔离、独立部署、权限模型不同 |
| FE-006 | WebSocket + SSE + REST 三协议并用 | 与 Gateway 契约对齐, 各协议匹配场景 |
| FE-007 | TypeScript strict + Zod runtime 双重校验 | 编译时 + 运行时双保险 |
| FE-008 | Admin 混合 UI 库 (shadcn/ui 基础 + Ant Design 企业组件) | 工程务实: Chat 场景 shadcn/ui 定制力强, Admin 场景 Ant Design 开箱即用; CSS 前缀隔离 |
| FE-009 | AI SDK Custom Runtime 适配笛语 WebSocket (备选: 后端 API Route / 自研 Hook) | 优先前端适配 (~1-2 人周); 如遇阻, 降级为后端增加 /api/v1/chat HTTP 端点或自研 Hook |
| FE-010 | 认证策略工厂 (SaaS: Cookie+BFF / Private: Bearer) | 解决 BFF + output:'export' 兼容性冲突; 安全性按部署模式最优化; 上层代码无感知 |
| FE-011 | Append-Only 客户端 WS 约束 | 保护后端 KV cache 稳定前缀, 对齐 Brain Context Engineering |
| FE-012 | Suggestion Chips 后端驱动 (静态列表降级) | 场景感知优先, 灵感: Manus token logits masking |
| FE-013 | Artifact 持久化 (IndexedDB + 后端历史查询) | 减少重复查询, 灵感: Manus 文件系统外部记忆 |
| FE-014 | Tier-Aware 导航 + 功能暴露矩阵 | org_tier 驱动菜单/功能可见性, packages/shared/org-tiers.ts 提供常量; 对齐 06 Section 1.1 层级定义 |
| FE-015 | Platform-Ops 路由组 (Phase 0 骨架 + Phase 2 实现) | 分阶段交付: 骨架不依赖后端新 API; 全局模型注册等待后端 model_registry API |
| FE-016 | Settings Constraints 前端枚举 (LAW/RULE/BRIDGE) | packages/shared/settings-constraints.ts 与 06 Section 1.6 保持同步; expand-contract 兼容 |

---

## 19. 与后端架构对齐表

| 本方案决策 | 对应后端架构 | 关系 |
|-----------|------------|------|
| Type A 解耦 (前端零感知 Brain/Memory) | 后端 7 层架构 Step 8/9 定位 | 对齐 |
| Component Registry | Skill 框架 "扩展通过注册" | 对齐 |
| DiyuChatRuntime | Gateway WebSocket /chat/stream 契约 | 适配层, 桥接 AI SDK 与笛语协议 |
| 降级状态展示 | 软依赖降级 degraded_reason | 对齐, 前端消费后端降级信号 |
| 记忆透明面板 | injection_receipt 五元组 + utilized | 可视化, 利用后端已有数据 |
| PIPL 删除追踪 | tombstone + deletion_event + legal_profile | 对齐, 前端展示后端删除流水线状态 |
| Feature Flags | Experiment Engine 灰度 | 对齐, org_settings 驱动 |
| OrgContext 贯穿 | Gateway OrgContext 组装 | 对齐, 前端每次请求携带 org_id |
| DEPLOY_MODE 双模式 | 三部署模式 (SaaS/Private/Hybrid) | 适配, 解决 Next.js 私有化部署约束 |
| Admin Ant Design 混合 | 5 层 ltree 组织树 + 三级审核工作流 | 务实选择, 匹配企业管理场景复杂度 |
| Append-Only WS 约束 | Brain Context Engineering KV cache | 对齐, 前端不干预后端上下文管理 |
| 认证策略工厂 | Gateway JWT 认证 + 三部署模式 | 适配, SaaS/Private 安全策略差异化 |
| Tier-Aware 导航 + 功能暴露矩阵 | 06 Section 1.1 五层 org_tier 定义 | 对齐, 前端常量与后端 enum 同源 |
| Platform-Ops 路由组 | 06 Section 1.3 platform-level 权限 | 对齐, PlatformGuard 校验 org_tier |
| Settings Constraints 枚举 (25 项) | 06 Section 1.6 LAW/RULE/BRIDGE 分类 | 对齐, 前端枚举与后端分类同步 |
| 模型配置品牌级 UI | 05 Section 4.2 OrganizationContext.model_access | 消费, 复用已有 org_settings API |
| 模型注册表全局 CRUD | 05 Section 5.2 ModelDefinition schema | 依赖, 需后端 model_registry CRUD API |
| 知识 visibility 分区 | 02 Section 5.3 KnowledgeEntry.visibility | 消费, 复用已有字段 |
| 通知中心 | 05 Section 1 SSE /events/* | 消费, 前端订阅后端事件推送 |
| 多会话管理 | 05 Section 7.1 WebSocket 按会话连接 | 对齐, 前端 session 管理与后端语义一致 |

---

## 20. 约束与边界

```
1. 前端是薄客户端: 所有智能 (LLM/记忆/知识/技能) 在后端, 前端只做展示和交互
2. 前端权限是 UX 级: 真实安全校验在 Gateway RLS, 前端仅隐藏无权限元素
3. 隐私硬边界: Admin Console 不展示 Memory Core 原始数据, 仅管理 Knowledge Stores
4. 不引入前端 AI 逻辑: 不在前端做记忆检索/排序/置信度计算, 这些是后端 Context Assembler 的职责
5. 渐进式上线: Phase 0-4 渐进交付, 每个 Phase 可独立验收
6. DEPLOY_MODE 双构建: CI 同时产出 SaaS 和 Private 两套产物, 确保私有化客户零 Node.js 依赖
7. 不引入新 Port: 前端不修改 Step 1~7 任何层, 不引入新的后端 Port
8. org_tier 常量同源: packages/shared/org-tiers.ts 是前端唯一 tier 定义源, 与 06 Section 1.1 保持同步
9. settings-constraints 同源: packages/shared/settings-constraints.ts 是前端唯一 LAW/RULE/BRIDGE 枚举, 与 06 Section 1.6 保持同步
10. expand-contract 兼容: 前端收到未知 org_tier 或未知配置项时 graceful degradation, 不崩溃
```

---

## 21. 开放问题

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| 1 | 品牌设计规范 (色板、字体、间距) 是否已确定? | 影响 packages/ui/themes | 待定 |
| 2 | PWA / Service Worker 是否需要? | 影响离线策略 | 倾向 Phase 4 |
| 3 | Admin Console Phase 0 范围是否需要调整? | 影响骨架交付 scope | 当前: 配置管理 + platform-ops 骨架 |
| 4 | 多语言是否需要英文? | 影响 i18n 优先级 | 倾向纯中文, Phase 4 启用 |
| 5 | Private 模式 WS Token 选择方式 1 (复用) 还是方式 2 (Gateway 新端点)? | 影响后端是否需要改动 | 倾向方式 1 (简单) |
| 6 | suggested_actions WS 字段何时由后端实现? | 影响 Suggestion Chips 上线时间 | 待后端迭代 |
| 7 | effective-settings API 何时可用? | 影响配置管理增强 (9.4.11) Phase 0 交付 | 见 Section 22 B1 |
| 8 | RBAC 权限码最终命名? | 影响 Tier-Aware 导航前端常量 | 前端当前用建议命名, 不锁定后端 |

---

## 22. 前端所需后端 Backlog 汇总

> 前端不引入新 Port, 但以下功能需要后端提供新 API 或扩展现有 API。此表供后端团队参考排期。

| # | 后端需求 | 前端消费方 | 对应前端 Phase | 后端归属层 | 备注 |
|---|---------|-----------|---------------|-----------|------|
| B1 | GET /api/v1/admin/effective-settings | 配置管理增强 (9.4.11) | Phase 0 | Gateway / 06 基础设施 | 返回合并继承链后的最终生效配置 |
| B2 | model_registry CRUD API | 模型注册表全局 (9.4.9) | Phase 2 | 05 Gateway / LLM Gateway | ModelDefinition 的增删改查 |
| B3 | SSE 事件类型扩展 (配置变更/审核请求/额度告警) | 通知中心 (9.4.13) | Phase 2 | 05 Gateway / SSE | 现有 /events/* 端点, 需定义新事件类型 |
| B4 | 会话列表 + 归档 API | 多会话管理 (9.4.14) | Phase 2 | 05 Gateway / Session | 会话 CRUD + 归档语义 |
| B5 | org_settings.branding 字段扩展 | 品牌主题定制 (Phase 3) | Phase 3 | 06 基础设施 | 新增 RULE 配置项: 主题色/Logo/字体 |
| B6 | 引导向导完成状态 API | 引导向导 (9.4.12) | Phase 2 | 06 基础设施 | 持久化 onboarding 步骤完成状态 |
| B7 | RBAC 权限码最终命名确认 | Tier-Aware 导航 (6.2) | Phase 0 | 06 基础设施 | 当前为建议命名, 前端不锁定后端命名空间 |
| B8 | 知识条目 visibility 筛选 API 参数 | 知识 visibility 分区 (9.4.10) | Phase 2 | 02 Knowledge | 现有 API 是否支持 visibility 过滤参数 |

---

> **文档版本:** v2.0
> **核心变更:** 统一权限矩阵与 TierGate 规则（仅 platform + brand_hq owner/admin 可进 Admin）; 成员管理集中化; 内容审核默认关闭; 计费模型重建为"299 订阅 + 100 元额度 + 超额点数最低 100 元起购且 100 元=33 元等值 Token"; 新增 history/knowledge-edit/store-dashboard 与 platform-ops 扩展路由; WS 上行新增 multimodal_message; 补全浏览器原生能力清单; 更新 SSR/E2E/Phase 排期。
>
> **本方案的本质:** 前端是后端 Gateway 的展示延伸, 不是第二个大脑。所有复杂度在后端 7 层架构中已解决, 前端的职责是把解决方案优雅地呈现给用户。
