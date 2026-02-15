# DIYU Agent 里程碑矩阵 -- 前端维度 (Frontend)

> parent: `docs/governance/milestone-matrix.md`
> scope: FE-Web (apps/web) / FE-Admin (apps/admin)
> version: v1.0

## 说明

> 矩阵层 7 字段格式 (D/AC/V-in/V-x/V-fb/M/DEP) 说明见 [索引文件](milestone-matrix.md) Section 0.5。
> 任务卡层采用双 Tier Schema (Tier-A: 10 字段, Tier-B: 8 字段)，详见 `task-card-schema-v1.0.md`。
> 跨层验证节点编号 (X/XF/XM) 定义见 [横切文件](milestone-matrix-crosscutting.md) Section 4。

---

## 1. Frontend Web (apps/web) 详细里程碑

> 架构文档: `frontend/00-08` | 渐进式组合: Step 8 (外部消费者)

### Phase 0 -- Monorepo 骨架

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FW0-1 | Next.js 15 + TypeScript strict + Tailwind | [CMD] `pnpm dev --filter web` -> localhost:3000 可访问 | dev server 启动 | X0-2 | -- | 页面可访问 | -- |
| FW0-2 | Turborepo + pnpm workspace | [CMD] `pnpm build` 全部 package 构建通过 | 全量构建通过 | X0-2 | -- | 0 build error | -- |
| FW0-3 | packages/ui (Button/Input/Card + Storybook) | [CMD] `pnpm storybook` -> 组件可预览 | 组件渲染正确 | -- | -- | 基础组件 >= 3 个 | -- |
| FW0-4 | packages/api-client (Axios 封装 + 类型) | [TEST] `pnpm test --filter api-client` 通过 | 类型定义完整 | -- | XF2-4 | 测试全通过 | -- |
| FW0-5 | packages/shared (常量/工具函数/类型) | [TEST] `pnpm test --filter shared` 通过 | 导出完整 | -- | -- | 测试全通过 | -- |
| FW0-6 | ESLint + Prettier + eslint-plugin-jsx-a11y | [CMD] `pnpm lint` 通过 | 配置正确 | X0-2 | -- | 0 error | -- |
| FW0-7 | Vitest 配置 | [CMD] `pnpm test` 运行不报错 | 配置可用 | -- | -- | 测试框架可运行 | -- |
| FW0-8 | Playwright E2E 基础设施配置 | [CMD] `pnpm exec playwright test --project=setup` 框架启动 + 空测试通过 | 框架可用 | X0-2 | -- | E2E 框架就绪 | FW0-1, FW0-2 |

### Phase 1 -- Auth 与组织上下文

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FW1-1 | 登录页 `/login` | [E2E] `pnpm exec playwright test tests/e2e/web/auth/login.spec.ts` | 表单校验单测 | X1-1 | XF2-1 | 登录成功跳转 | Gateway Auth API (G1-1) |
| FW1-2 | AuthProvider + PermissionGate | [TEST] 未登录自动跳转; 无权限显示 403 组件 | Provider 单测 | X1-2 | XF2-1 | 拦截率 100% | -- |
| FW1-3 | 组织切换器 | [E2E] `pnpm exec playwright test tests/e2e/web/auth/org-switch.spec.ts` | 切换逻辑单测 | X1-1 | XF2-1 | 切换后数据正确 | OrgContext (G1-2) |
| FW1-4 | SaaS: HttpOnly Cookie / Private: in-memory Token | [TEST] 两种模式各自测试通过 (FE-03 ADR FE-010) | 双模式单测 | -- | -- | 两种模式全通过 | DEPLOY_MODE |

### Phase 2 -- 对话主界面（核心交付 Phase）

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FW2-1 | 对话界面 `/chat` 双栏布局 | [E2E] `pnpm exec playwright test tests/e2e/web/chat/layout.spec.ts` | 布局响应式单测 | -- | XF2-1 | 双栏正确渲染 | -- |
| FW2-2 | 流式消息渲染 (SSE/WS) | [E2E] `pnpm exec playwright test tests/e2e/web/chat/streaming.spec.ts` | Markdown 渲染单测 | X2-2 | XF2-1 | 首字节渲染 < 500ms | Gateway WS (G2-2) |
| FW2-3 | 对话历史管理 | [E2E] `pnpm exec playwright test tests/e2e/web/chat/history.spec.ts` | CRUD 逻辑单测 | -- | XF2-1 | 4 操作全通过 | -- |
| FW2-4 | 记忆面板 (Memory Context Panel) | [E2E] `pnpm exec playwright test tests/e2e/web/chat/memory-panel.spec.ts` | 面板交互单测 | X2-3 | XF2-2 | 记忆列表可加载 | Memory Core API (MC2-3) |
| FW2-5 | 消息操作 (复制/重试/反馈) | [E2E] `pnpm exec playwright test tests/e2e/web/chat/message-actions.spec.ts` | 操作逻辑单测 | -- | -- | 3 操作全可用 | -- |
| FW2-6 | 文件上传 (拖拽 + 进度条) | [E2E] `pnpm exec playwright test tests/e2e/web/chat/file-upload.spec.ts` | 上传流程单测 | -- | XF2-3 | 上传成功率 >= 99% | 三步上传协议 (G2-6) |
| FW2-7 | WebSocket 连接管理 (自动重连 < 5s P95) | [TEST] 断网 -> 恢复 -> 自动重连 -> 不丢消息 | 重连逻辑单测 | X2-2 | -- | 重连 P95 < 5s | -- |
| FW2-8 | OpenAPI 类型同步 | [CMD] `pnpm openapi:generate` 后 diff 为空 | 生成脚本可用 | -- | XF2-4 | diff 为空 | OpenAPI spec (G0-2) |
| FW2-9 | SSE EventSource 客户端 + 事件分发 | [TEST] 6 种事件类型分发 + 重连 + 认证 | SSE 客户端单测 | -- | -- | 6 事件类型全覆盖 | Gateway SSE (G2-7), FW1-2 |

### Phase 3 -- 知识与 Skill

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FW3-1 | 知识浏览页 `/knowledge` | [E2E] `pnpm exec playwright test tests/e2e/web/knowledge/browse.spec.ts` | 搜索逻辑单测 | X3-4 | XF3-1 | 搜索结果可展示 | Knowledge API (G3-1) |
| FW3-2 | Skill 结构化渲染 (右侧面板 Artifact) | [E2E] `pnpm exec playwright test tests/e2e/web/knowledge/skill-artifact.spec.ts` | Artifact 渲染单测 | X3-1 | XF3-1 | 结构化内容正确渲染 | Skill API (G3-2) |
| FW3-3 | 商品组件 (ProductCard/OutfitGrid/StyleBoard) | [CMD] Storybook 中组件可预览 | 组件 props 单测 | -- | -- | 3 组件全可预览 | packages/ui |

### Phase 4 -- 完整功能

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FW4-1 | 性能预算达标 | [METRIC] LCP < 2.5s, FID < 100ms, CLS < 0.1, 首屏 < 200KB | Lighthouse CI 集成 | X4-1 | -- | 4 项指标全达标 | -- |
| FW4-2 | a11y 检查通过 | [CMD] axe-core 扫描 0 critical violations | a11y CI 集成 | -- | -- | 0 critical violations | OS4-8 |
| FW4-3 | 暗色/亮色模式 | [E2E] `pnpm exec playwright test tests/e2e/web/settings/theme.spec.ts` | 主题切换单测 | -- | -- | 两种模式全组件正确 | -- |
| FW4-4 | 键盘快捷键 (Cmd+K/N/Shift+M 等) | [E2E] `pnpm exec playwright test tests/e2e/web/settings/keyboard-shortcuts.spec.ts` | 快捷键映射单测 | -- | -- | >= 5 个快捷键可用 | -- |
| FW4-5 | 积分充值页 `/billing` | [E2E] `pnpm exec playwright test tests/e2e/web/billing/recharge.spec.ts` | 支付流程单测 | X2-4 | XF4-1 | 充值 -> 余额更新 | 计费 API (I2-3) |

### Phase 5 -- 高级体验

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FW5-1 | 语音交互 | [E2E] `pnpm exec playwright test tests/e2e/web/voice/interaction.spec.ts` | 语音流程单测 | -- | -- | 语音转文字可用 | AudioTranscribe Tool (T3-3) |
| FW5-2 | ~~PWA 离线支持~~ **[Closed]** | 架构决策: 00-architecture-overview.md L242 明确关闭 PWA ("Not needed. No PWA planned.") | -- | -- | -- | -- | -- |

---

## 2. Frontend Admin (apps/admin) 详细里程碑

> 架构文档: `frontend/06-admin-console.md` | 渐进式组合: Step 9 (外部消费者)

### Phase 0 -- 骨架

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FA0-1 | Next.js Admin App 独立构建 | [CMD] `pnpm dev --filter admin` -> localhost:3001 可访问 | dev server 启动 | X0-2 | -- | 页面可访问 | -- |
| FA0-2 | Admin Layout (侧边栏 + 面包屑) | [E2E] `pnpm exec playwright test tests/e2e/admin/layout/navigation.spec.ts` | 布局渲染单测 | -- | -- | 导航完整 | -- |
| FA0-3 | TierGate: 非 Admin 角色访问 -> 302 到 Web App | [TEST] 普通用户访问 /admin -> 重定向 | 重定向逻辑单测 | -- | -- | 302 响应准确 | -- |

### Phase 1 -- Admin Auth

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FA1-1 | Admin 登录 (含 2FA 预留) | [E2E] `pnpm exec playwright test tests/e2e/admin/auth/login.spec.ts` | 登录流程单测 | X1-1 | -- | 登录后审计记录存在 | Gateway Auth (G1-1) |
| FA1-2 | 权限矩阵管理 | [E2E] `pnpm exec playwright test tests/e2e/admin/auth/permissions.spec.ts` | 权限编辑单测 | X1-2 | -- | CRUD 全操作通过 | RBAC (I1-4) |

### Phase 2 -- 基础管理

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FA2-1 | 用户管理 DataTable | [E2E] `pnpm exec playwright test tests/e2e/admin/users/datatable.spec.ts` | DataTable 单测 | -- | -- | 4 操作全通过 | Admin API |
| FA2-2 | 组织管理 | [E2E] `pnpm exec playwright test tests/e2e/admin/orgs/management.spec.ts` | CRUD 逻辑单测 | -- | -- | 组织 CRUD 全覆盖 | -- |
| FA2-3 | 审计日志查看 | [E2E] `pnpm exec playwright test tests/e2e/admin/audit/log-viewer.spec.ts` | 筛选逻辑单测 | -- | -- | 3 维度筛选可用 | audit_events (I1-5) |

### Phase 3 -- 知识管理

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FA3-1 | 知识编辑工作台 `/admin/knowledge` | [E2E] `pnpm exec playwright test tests/e2e/admin/knowledge/editor.spec.ts` | 编辑器单测 | X3-4 | XF3-2 | CRUD 全操作通过 | Knowledge Write API (K3-4) |
| FA3-2 | 内容审核队列 | [E2E] `pnpm exec playwright test tests/e2e/admin/knowledge/review-queue.spec.ts` | 审核流程单测 | -- | XF3-2 | 审核状态转换正确 | -- |
| FA3-3 | org_settings 配置管理 | [E2E] `pnpm exec playwright test tests/e2e/admin/knowledge/org-settings.spec.ts` | 继承逻辑单测 | -- | XF3-3 | lock 机制 UI 可操作 | org_settings (I1-2) |

### Phase 4 -- 运维

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FA4-1 | 系统监控看板 | [E2E] `pnpm exec playwright test tests/e2e/admin/ops/monitoring.spec.ts` | 看板交互单测 | X4-1 | XF4-2 | 实时数据可展示 | Prometheus/Grafana (I4-1) |
| FA4-2 | 配额管理 | [E2E] `pnpm exec playwright test tests/e2e/admin/ops/quota.spec.ts` | 配额逻辑单测 | -- | -- | 配额设置即时生效 | -- |
| FA4-3 | 备份管理 | [E2E] `pnpm exec playwright test tests/e2e/admin/ops/backup.spec.ts` | 备份流程单测 | X4-2 | -- | 3 操作全可用 | I4-3 |

### Phase 5 -- 治理

| # | D | AC | V-in | V-x | V-fb | M | DEP |
|---|---|----|----|-----|------|---|-----|
| FA5-1 | 合规报告 | [E2E] `pnpm exec playwright test tests/e2e/admin/compliance/report.spec.ts` | 报告生成单测 | X5-2 | -- | 报告含必需章节 | OS5-5 |
| FA5-2 | Exception Register UI | [E2E] `pnpm exec playwright test tests/e2e/admin/compliance/exception-register.spec.ts` | 审批流程单测 | X5-1 | -- | CRUD 全操作通过 | OS5-3 |

---

> **文档版本:** v1.0
> **维护规则:** 与 [索引文件](milestone-matrix.md) Section 9-10 保持同步。前端维度变更应同时更新本文件。
