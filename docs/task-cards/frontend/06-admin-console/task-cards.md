# 前端管理后台 任务卡集

> 架构文档: `docs/frontend/06-admin-console.md`
> 里程碑来源: `docs/governance/milestone-matrix-frontend.md` Section 2
> 影响门禁: `apps/admin/**` -> pnpm test

---

## Phase 2 -- 基础管理

### TASK-FA2-1: 用户管理 DataTable

| 字段 | 内容 |
|------|------|
| **目标** | 搜索/筛选/分页/批量操作 |
| **范围 (In Scope)** | `apps/admin/app/users/page.tsx`, `apps/admin/components/DataTable.tsx` |
| **范围外 (Out of Scope)** | 后端 Admin API / 用户模型 DDL / RBAC / DevOps |
| **依赖** | Admin API |
| **兼容策略** | 纯新增页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/users/datatable.spec.ts` (4 操作全通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | DataTable E2E 通过 |
| **风险** | 依赖: Admin API / 数据: 用户数据需脱敏展示 / 兼容: 纯新增页面 / 回滚: git revert |
| **决策记录** | 决策: 用户管理 DataTable (搜索/筛选/分页/批量) / 理由: Admin 基础管理功能 / 来源: FE-06 Section 1 |

> 矩阵条目: FA2-1

### TASK-FA2-2: 组织管理

| 字段 | 内容 |
|------|------|
| **目标** | CRUD 组织 + 查看成员 + 查看用量 |
| **范围 (In Scope)** | `apps/admin/app/organizations/page.tsx` |
| **范围外 (Out of Scope)** | 后端组织模型 / ltree 路径 / RLS 策略 / 数据库 |
| **依赖** | -- |
| **兼容策略** | 纯新增页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/orgs/management.spec.ts` (组织 CRUD 全覆盖) |
| **回滚方案** | `git revert <commit>` |
| **证据** | CRUD 逻辑 E2E 通过 |
| **风险** | 依赖: N/A / 数据: 组织 CRUD 影响全局 / 兼容: 纯新增页面 / 回滚: git revert |
| **决策记录** | 决策: 组织管理 (CRUD+成员+用量) / 理由: Admin 组织树管理入口 / 来源: FE-06 Section 1 |

> 矩阵条目: FA2-2

### TASK-FA2-3: 审计日志查看

| 字段 | 内容 |
|------|------|
| **目标** | 按时间/用户/操作类型筛选 |
| **范围 (In Scope)** | `apps/admin/app/audit/page.tsx` |
| **范围外 (Out of Scope)** | 后端审计写入 / audit_events DDL / 数据库 / DevOps |
| **依赖** | audit_events (I1-5) |
| **兼容策略** | 纯新增页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/audit/log-viewer.spec.ts` (3 维度筛选可用) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 筛选逻辑 E2E 通过 |
| **风险** | 依赖: I1-5 (audit_events) / 数据: 审计日志只读, 不可删除 / 兼容: 纯新增页面 / 回滚: git revert |
| **决策记录** | 决策: 审计日志查看 (时间/用户/操作类型筛选) / 理由: 合规审计可视化 / 来源: FE-06 Section 1 |

> 矩阵条目: FA2-3

---

## Phase 3 -- 知识管理

### TASK-FA3-1: 知识编辑工作台 /admin/knowledge

| 字段 | 内容 |
|------|------|
| **目标** | 创建/编辑/发布知识条目 |
| **范围 (In Scope)** | `apps/admin/app/knowledge/page.tsx`, `apps/admin/components/KnowledgeEditor.tsx` |
| **范围外 (Out of Scope)** | 后端 Knowledge Write API / 知识存储 / 数据库 / DevOps |
| **依赖** | Knowledge Write API (K3-4) |
| **兼容策略** | 纯新增页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/knowledge/editor.spec.ts` (CRUD 全操作通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 编辑器 E2E 通过 |
| **风险** | 依赖: K3-4 (Knowledge Write API) / 数据: 知识发布需审核流程 / 兼容: 纯新增页面 / 回滚: git revert |
| **决策记录** | 决策: 知识编辑工作台 CRUD / 理由: Admin 知识管理入口 / 来源: FE-06 Section 2 |

> 矩阵条目: FA3-1 | V-x: X3-4 | V-fb: XF3-2

### TASK-FA3-2: 内容审核队列

| 字段 | 内容 |
|------|------|
| **目标** | 待审内容列表 -> 通过/拒绝 -> 状态更新 |
| **范围 (In Scope)** | `apps/admin/app/knowledge/review/page.tsx` |
| **范围外 (Out of Scope)** | 后端审核逻辑 / 内容安全管线 / 数据库 / DevOps |
| **依赖** | TASK-FA3-1 |
| **兼容策略** | 新增审核流程 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/knowledge/review-queue.spec.ts` (审核状态转换正确) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 审核流程 E2E 通过 |
| **风险** | 依赖: FA3-1 (知识编辑) / 数据: 审核状态转换需幂等 / 兼容: 新增审核流程 / 回滚: git revert |
| **决策记录** | 决策: 内容审核队列 (通过/拒绝) / 理由: 知识发布质量门禁 / 来源: FE-06 Section 2 |

> 矩阵条目: FA3-2 | V-fb: XF3-2

### TASK-FA3-3: org_settings 配置管理

| 字段 | 内容 |
|------|------|
| **目标** | 修改配置 -> 继承链生效 -> 子组织受影响 |
| **范围 (In Scope)** | `apps/admin/app/settings/page.tsx` |
| **范围外 (Out of Scope)** | 后端 org_settings 继承逻辑 / BRIDGE 机制 / 数据库 / DevOps |
| **依赖** | org_settings (I1-2) |
| **兼容策略** | 新增配置页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/knowledge/org-settings.spec.ts` (lock 机制 UI 可操作) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 继承逻辑 E2E 通过 |
| **风险** | 依赖: I1-2 (org_settings) / 数据: lock 机制需正确展示, 错误配置影响子组织 / 兼容: 新增配置页面 / 回滚: git revert |
| **决策记录** | 决策: org_settings 配置管理 + 继承链可视化 / 理由: Admin 配置管控入口 / 来源: FE-06 Section 2 |

> 矩阵条目: FA3-3 | V-fb: XF3-3

---

## Phase 4 -- 运维

### TASK-FA4-1: 系统监控看板

| 字段 | 内容 |
|------|------|
| **目标** | 实时指标 + 错误跟踪 + 性能图表 |
| **范围 (In Scope)** | `apps/admin/app/monitoring/page.tsx` |
| **范围外 (Out of Scope)** | 后端监控实现 / Prometheus/Grafana / 数据库 / DevOps |
| **依赖** | Prometheus/Grafana (I4-1) |
| **兼容策略** | 新增看板页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/ops/monitoring.spec.ts` (实时数据可展示) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 看板交互 E2E 通过 |
| **风险** | 依赖: I4-1 (Prometheus/Grafana) / 数据: 监控数据实时刷新 / 兼容: 新增看板页面 / 回滚: git revert |
| **决策记录** | 决策: 系统监控看板 (指标+错误+性能) / 理由: Admin 运维可视化 / 来源: FE-06 Section 3 |

> 矩阵条目: FA4-1 | V-x: X4-1 | V-fb: XF4-2

### TASK-FA4-2: 配额管理

| 字段 | 内容 |
|------|------|
| **目标** | 设置 org/user 配额 -> 超额告警 |
| **范围 (In Scope)** | `apps/admin/app/quotas/page.tsx` |
| **范围外 (Out of Scope)** | 后端配额逻辑 / 计费系统 / 数据库 / DevOps |
| **依赖** | -- |
| **兼容策略** | 新增管理页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/ops/quota.spec.ts` (配额设置即时生效) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 配额逻辑 E2E 通过 |
| **风险** | 依赖: N/A / 数据: 配额设置即时生效, 需确认操作 / 兼容: 新增管理页面 / 回滚: git revert |
| **决策记录** | 决策: 配额管理 (org/user 配额+超额告警) / 理由: 资源管控入口 / 来源: FE-06 Section 3 |

> 矩阵条目: FA4-2

### TASK-FA4-3: 备份管理

| 字段 | 内容 |
|------|------|
| **目标** | 触发备份 + 查看历史 + 恢复操作 |
| **范围 (In Scope)** | `apps/admin/app/backups/page.tsx` |
| **范围外 (Out of Scope)** | 后端备份恢复实现 / PG WAL / 数据库 / DevOps |
| **依赖** | I4-3 |
| **兼容策略** | 新增管理页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/ops/backup.spec.ts` (3 操作全可用) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 备份流程 E2E 通过 |
| **风险** | 依赖: I4-3 (备份恢复) / 数据: 恢复操作高风险, 需二次确认 / 兼容: 新增管理页面 / 回滚: git revert |
| **决策记录** | 决策: 备份管理 (触发+历史+恢复) / 理由: Admin 灾难恢复入口 / 来源: FE-06 Section 3 |

> 矩阵条目: FA4-3 | V-x: X4-2

---

## Phase 5 -- 治理

### TASK-FA5-1: 合规报告

| 字段 | 内容 |
|------|------|
| **目标** | 生成 GDPR/数据保留审计报告 |
| **范围 (In Scope)** | `apps/admin/app/compliance/page.tsx` |
| **范围外 (Out of Scope)** | 后端合规报告生成 / 删除管线 / 审计逻辑 / 数据库 |
| **依赖** | OS5-5 |
| **兼容策略** | 新增报告页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/compliance/report.spec.ts` (报告含必需章节) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 报告生成 E2E 通过 |
| **风险** | 依赖: OS5-5 (合规报告) / 数据: 合规数据需准确 / 兼容: 新增报告页面 / 回滚: git revert |
| **决策记录** | 决策: GDPR/数据保留合规报告页 / 理由: 合规审计可视化 / 来源: FE-06 Section 4 |

> 矩阵条目: FA5-1 | V-x: X5-2

### TASK-FA5-2: Exception Register UI

| 字段 | 内容 |
|------|------|
| **目标** | 查看/审批/关闭例外申请 |
| **范围 (In Scope)** | `apps/admin/app/exceptions/page.tsx` |
| **范围外 (Out of Scope)** | 后端 Exception 审计逻辑 / Cron Job / 数据库 / DevOps |
| **依赖** | OS5-3 |
| **兼容策略** | 新增管理页面 |
| **验收命令** | `pnpm exec playwright test tests/e2e/admin/compliance/exception-register.spec.ts` (CRUD 全操作通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 审批流程 E2E 通过 |
| **风险** | 依赖: OS5-3 (Exception Register) / 数据: 审批操作需权限验证 / 兼容: 新增管理页面 / 回滚: git revert |
| **决策记录** | 决策: Exception Register UI (查看/审批/关闭) / 理由: 例外管理可视化 / 来源: FE-06 Section 4 |

> 矩阵条目: FA5-2 | V-x: X5-1

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
