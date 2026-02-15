# 前端 Monorepo 基础设施 任务卡集

> 架构文档: `docs/frontend/01-monorepo-infrastructure.md`
> 里程碑来源: `docs/governance/milestone-matrix-frontend.md` Section 1 (Phase 0)
> 影响门禁: `pnpm-workspace.yaml`, `turbo.json`, `packages/**` -> pnpm build + lint

---

## Phase 0 -- Monorepo 骨架

### TASK-FW0-1: Next.js 15 + TypeScript strict + Tailwind

| 字段 | 内容 |
|------|------|
| **目标** | `pnpm dev --filter web` -> localhost:3000 可访问 |
| **范围 (In Scope)** | `apps/web/` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps / Admin App |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `pnpm dev --filter web & sleep 5 && curl -s localhost:3000` |
| **回滚方案** | `git revert <commit>` |
| **证据** | dev server 启动截图 |

> 矩阵条目: FW0-1 | V-x: X0-2

### TASK-FW0-2: Turborepo + pnpm workspace

| 字段 | 内容 |
|------|------|
| **目标** | `pnpm build` 全部 package 构建通过 |
| **范围 (In Scope)** | `pnpm-workspace.yaml`, `turbo.json`, `package.json` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps / 各 package 内部业务逻辑 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `pnpm build` (0 build error) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 全量构建通过 |

> 矩阵条目: FW0-2 | V-x: X0-2

### TASK-FW0-3: packages/ui (Button/Input/Card + Storybook)

| 字段 | 内容 |
|------|------|
| **目标** | 基础 UI 组件库 >= 3 个组件，Storybook 可预览 |
| **范围 (In Scope)** | `packages/ui/` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps / 业务组件 (非通用 UI) |
| **依赖** | TASK-FW0-2 |
| **兼容策略** | 纯新增 |
| **验收命令** | `pnpm storybook` (组件可预览) |
| **回滚方案** | `git revert <commit>` |
| **证据** | Storybook 截图 |

> 矩阵条目: FW0-3

### TASK-FW0-4: packages/api-client (Axios 封装 + 类型)

| 字段 | 内容 |
|------|------|
| **目标** | API Client 封装完成，类型定义完整 |
| **范围 (In Scope)** | `packages/api-client/` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps / 具体业务请求逻辑 |
| **依赖** | TASK-FW0-2 |
| **兼容策略** | 纯新增 |
| **验收命令** | `pnpm test --filter api-client` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 测试全通过 |

> 矩阵条目: FW0-4 | V-fb: XF2-4

### TASK-FW0-5: packages/shared (常量/工具函数/类型)

| 字段 | 内容 |
|------|------|
| **目标** | 共享包导出完整 |
| **范围 (In Scope)** | `packages/shared/` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps / 业务逻辑实现 |
| **依赖** | TASK-FW0-2 |
| **兼容策略** | 纯新增 |
| **验收命令** | `pnpm test --filter shared` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 测试全通过 |

> 矩阵条目: FW0-5

### TASK-FA0-1: Next.js Admin App 独立构建

| 字段 | 内容 |
|------|------|
| **目标** | `pnpm dev --filter admin` -> localhost:3001 可访问 |
| **范围 (In Scope)** | `apps/admin/` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps / Web App 内部逻辑 |
| **依赖** | TASK-FW0-2 |
| **兼容策略** | 纯新增 |
| **验收命令** | `pnpm dev --filter admin & sleep 5 && curl -s localhost:3001` |
| **回滚方案** | `git revert <commit>` |
| **证据** | dev server 启动截图 |
| **风险** | 依赖: FW0-2 workspace 配置未就绪时阻塞 / 数据: N/A -- Phase 0 无数据层 / 兼容: 新增独立 App, 不影响 Web / 回滚: git revert |
| **决策记录** | 决策: Admin 与 Web 独立 App 分离部署 / 理由: 权限边界清晰, 独立构建与发布周期 (FE-005) / 来源: FE-005, 架构文档 Section 2.2 |

> 矩阵条目: FA0-1 | V-x: X0-2

### TASK-FA0-2: Admin Layout (侧边栏 + 面包屑)

| 字段 | 内容 |
|------|------|
| **目标** | Admin 专用导航布局完整 |
| **范围 (In Scope)** | `apps/admin/components/layout/` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps / Web App 布局 |
| **依赖** | TASK-FA0-1 |
| **兼容策略** | 纯新增 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/layout/navigation.spec.ts` (导航完整) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 布局渲染截图 |

> 矩阵条目: FA0-2

### TASK-FA0-3: TierGate -- 非 Admin 角色重定向

| 字段 | 内容 |
|------|------|
| **目标** | 普通用户访问 /admin -> 302 到 Web App |
| **范围 (In Scope)** | `apps/admin/middleware.ts` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps / 认证服务实现 |
| **依赖** | TASK-FA0-1 |
| **兼容策略** | 新增中间件 |
| **验收命令** | `pnpm test --filter admin -- --grep TierGate` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 重定向逻辑测试通过 |

> 矩阵条目: FA0-3

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
