# 前端认证与权限 任务卡集

> 架构文档: `docs/frontend/03-auth-permission.md`
> 里程碑来源: `docs/governance/milestone-matrix-frontend.md` (Phase 1)
> 影响门禁: `apps/web/lib/auth/**`, `apps/admin/lib/auth/**` -> pnpm test

---

## Phase 1 -- Auth 与组织上下文

### TASK-FW1-1: 登录页 /login

| 字段 | 内容 |
|------|------|
| **目标** | 输入凭证 -> 提交 -> 跳转到主页 |
| **范围 (In Scope)** | `apps/web/app/login/page.tsx`, `tests/e2e/login.spec.ts` |
| **范围外 (Out of Scope)** | 后端 Auth API / JWT 生成 / 数据库 / DevOps |
| **依赖** | Gateway Auth API (G1-1) |
| **兼容策略** | 纯新增页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/auth/login.spec.ts` (登录成功跳转) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 登录 E2E 截图 |
| **风险** | 依赖: G1-1 (Gateway Auth API) / 数据: 凭证传输需 HTTPS / 兼容: 纯新增页面 / 回滚: git revert |
| **决策记录** | 决策: 登录页 /login / 理由: 认证入口, E2E 验证登录跳转 / 来源: FE-03 Section 1 |

> 矩阵条目: FW1-1 | V-x: X1-1 | V-fb: XF2-1

### TASK-FW1-2: AuthProvider + PermissionGate

| 字段 | 内容 |
|------|------|
| **目标** | 未登录自动跳转; 无权限显示 403 组件 |
| **范围 (In Scope)** | `apps/web/providers/AuthProvider.tsx`, `apps/web/components/PermissionGate.tsx` |
| **范围外 (Out of Scope)** | 后端 Auth 逻辑 / JWT 验证 / RBAC 策略 / 数据库 |
| **依赖** | TASK-FW1-1 |
| **兼容策略** | 新增 Provider |
| **验收命令** | `pnpm test --filter web -- --grep Auth` (拦截率 100%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | Provider 单测通过 |
| **风险** | 依赖: FW1-1 (登录页) / 数据: 未登录拦截失败=未授权访问 / 兼容: 新增 Provider / 回滚: git revert |
| **决策记录** | 决策: AuthProvider + PermissionGate 双重拦截 / 理由: 客户端认证+权限双保障 / 来源: FE-03 Section 1 |

> 矩阵条目: FW1-2 | V-x: X1-2 | V-fb: XF2-1

### TASK-FW1-3: 组织切换器

| 字段 | 内容 |
|------|------|
| **目标** | 切换组织 -> API 请求头 org_id 变更 -> 数据刷新 |
| **范围 (In Scope)** | `apps/web/components/OrgSwitcher.tsx`, `tests/e2e/org-switch.spec.ts` |
| **范围外 (Out of Scope)** | 后端 OrgContext / 组织模型 DDL / RLS 策略 / 数据库 |
| **依赖** | OrgContext (G1-2) |
| **兼容策略** | 新增组件 |
| **验收命令** | `pnpm exec playwright test tests/e2e/web/auth/org-switch.spec.ts` (切换后数据正确) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 切换逻辑 E2E 通过 |
| **风险** | 依赖: G1-2 (OrgContext) / 数据: 组织切换需刷新全部数据 / 兼容: 新增组件 / 回滚: git revert |
| **决策记录** | 决策: 组织切换器 org_id 请求头模式 / 理由: 多租户前端切换基座 / 来源: FE-03 Section 1 |

> 矩阵条目: FW1-3 | V-x: X1-1 | V-fb: XF2-1

### TASK-FW1-4: SaaS/Private 双模式 Token 管理

| 字段 | 内容 |
|------|------|
| **目标** | SaaS: HttpOnly Cookie / Private: in-memory Token，两种模式各自测试通过 |
| **范围 (In Scope)** | `apps/web/lib/auth/token.ts`, `tests/unit/web/token.test.ts` |
| **范围外 (Out of Scope)** | 后端 Token 签发 / JWT 密钥管理 / 数据库 / DevOps |
| **依赖** | DEPLOY_MODE 环境变量 |
| **兼容策略** | 运行时切换，互不影响 |
| **验收命令** | `pnpm test --filter web -- --grep token` (两种模式全通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 双模式单测通过 |
| **风险** | 依赖: DEPLOY_MODE 环境变量 / 数据: Token 泄露=安全事故 / 兼容: 运行时切换, 互不影响 / 回滚: git revert |
| **决策记录** | 决策: SaaS HttpOnly Cookie / Private in-memory Token / 理由: 双模式安全策略, 按部署模式切换 / 来源: FE-03 Section 2 |

> 矩阵条目: FW1-4

### TASK-FA1-1: Admin 登录 (含 2FA 预留)

| 字段 | 内容 |
|------|------|
| **目标** | Admin 凭证登录 + 审计日志 |
| **范围 (In Scope)** | `apps/admin/app/login/page.tsx`, `tests/e2e/admin-login.spec.ts` |
| **范围外 (Out of Scope)** | 后端 Auth API / 2FA 实现 / 审计写入 / 数据库 |
| **依赖** | Gateway Auth (G1-1) |
| **兼容策略** | 新增页面，2FA 预留接口 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/auth/login.spec.ts` (登录后审计记录存在) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 登录 E2E 截图 |
| **风险** | 依赖: G1-1 (Gateway Auth) / 数据: Admin 登录需审计记录 / 兼容: 新增页面, 2FA 预留接口 / 回滚: git revert |
| **决策记录** | 决策: Admin 独立登录 + 审计日志 + 2FA 预留 / 理由: Admin 安全等级高于 Web / 来源: FE-03 Section 3 |

> 矩阵条目: FA1-1 | V-x: X1-1

### TASK-FA1-2: 权限矩阵管理

| 字段 | 内容 |
|------|------|
| **目标** | 查看/编辑角色权限 |
| **范围 (In Scope)** | `apps/admin/app/permissions/page.tsx`, `tests/e2e/permissions.spec.ts` |
| **范围外 (Out of Scope)** | 后端 RBAC 实现 / 权限判定逻辑 / 数据库 DDL / DevOps |
| **依赖** | RBAC (I1-4) |
| **兼容策略** | 新增管理页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/auth/permissions.spec.ts` (CRUD 全操作通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 权限编辑 E2E 截图 |
| **风险** | 依赖: I1-4 (RBAC) / 数据: 权限编辑错误=越权风险 / 兼容: 新增管理页面 / 回滚: git revert |
| **决策记录** | 决策: 权限矩阵管理 UI / 理由: Admin 可视化管理角色权限 / 来源: FE-03 Section 3 |

> 矩阵条目: FA1-2 | V-x: X1-2

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
