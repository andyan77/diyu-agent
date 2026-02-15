# 前端部署 任务卡集

> 架构文档: `docs/frontend/07-deployment.md`
> 里程碑来源: `docs/governance/milestone-matrix-frontend.md` + crosscutting
> 影响门禁: `apps/web/next.config.js`, `apps/admin/next.config.js`, `Dockerfile.web`, `Dockerfile.admin`
> 说明: 前端部署相关任务卡，与后端 Delivery 维度互补

---

## Phase 0 -- 构建基线

> 前端部署基线由 Monorepo 基础设施 (01-monorepo) 覆盖。
> 本文件聚焦 Phase 2+ 的部署产品化。

---

## Phase 2 -- Dogfooding 前端集成

### TASK-D2-1-FE: 前端 CI 集成

| 字段 | 内容 |
|------|------|
| **目标** | pnpm lint + typecheck + test + a11y 全部在 CI 中通过 |
| **范围 (In Scope)** | `.github/workflows/ci.yml` (前端步骤) |
| **范围外 (Out of Scope)** | 后端 CI 步骤 / 安全扫描 / 部署流程 / 数据库 |
| **依赖** | Monorepo (FW0-2) |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | [ENV-DEP] CI-job: lint-frontend + test-frontend + typecheck-frontend (前端 PR CI 全部通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | CI 4 项检查齐全 |
| **风险** | 依赖: FW0-2 (Monorepo) / 数据: N/A -- 纯 CI 步骤 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: 前端 CI 4 道检查 (lint/typecheck/test/a11y) / 理由: 前端质量门禁 / 来源: FE-07 Section 1 |

> 矩阵条目: D2-1 | V-fb: XF2-4

### TASK-D2-2-FE: OpenAPI 类型同步 CI 硬门禁

| 字段 | 内容 |
|------|------|
| **目标** | `pnpm openapi:generate` 后 diff 为空，作为 CI 硬门禁 |
| **范围 (In Scope)** | `.github/workflows/ci.yml`, `scripts/check_openapi_sync.sh` |
| **范围外 (Out of Scope)** | 后端 OpenAPI Schema / Gateway API / 数据库 / DevOps |
| **依赖** | FW2-8 |
| **兼容策略** | 新增 CI 硬门禁 |
| **验收命令** | `pnpm openapi:generate && git diff --exit-code` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 同步检查通过 |
| **风险** | 依赖: FW2-8 (OpenAPI 类型同步) / 数据: 不同步=前后端类型不一致 / 兼容: 新增 CI 硬门禁 / 回滚: git revert |
| **决策记录** | 决策: OpenAPI 类型同步 CI 硬门禁 / 理由: 前后端契约一致性强制保障 / 来源: FE-07 Section 1 |

> 矩阵条目: D2-2 | V-fb: XF2-4

---

## Phase 3 -- 产品化部署

### TASK-DEPLOY-FE-1: 前端 Docker 镜像

| 字段 | 内容 |
|------|------|
| **目标** | Web + Admin 两个 Next.js App 各有独立 Docker 镜像 |
| **范围 (In Scope)** | `Dockerfile.web`, `Dockerfile.admin` |
| **范围外 (Out of Scope)** | 后端 Docker 镜像 / CI/CD 流水线 / 数据库 / 可观测性 |
| **依赖** | FW0-2, FA0-1 |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `docker build -f Dockerfile.web . && docker build -f Dockerfile.admin .` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 镜像构建成功 |
| **风险** | 依赖: FW0-2 + FA0-1 / 数据: N/A -- 构建产物 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: Web + Admin 独立 Docker 镜像 / 理由: 独立构建与部署, 权限边界清晰 / 来源: FE-07 Section 2 |

> 矩阵条目: D3-2 (前端子实现)

### TASK-DEPLOY-FE-2: 前端环境变量管理

| 字段 | 内容 |
|------|------|
| **目标** | 运行时注入 API_URL / WS_URL / DEPLOY_MODE 等环境变量 |
| **范围 (In Scope)** | `apps/web/env.ts`, `apps/admin/env.ts` |
| **范围外 (Out of Scope)** | 后端环境变量 / 密钥管理 / 数据库 / DevOps |
| **依赖** | -- |
| **兼容策略** | Next.js publicRuntimeConfig 模式 |
| **验收命令** | [ENV-DEP] `docker compose -f docker-compose.yml up -d && curl -s localhost:3000/api/health` staging: 不同环境变量下应用正确连接对应后端 |
| **回滚方案** | `git revert <commit>` |
| **证据** | 环境变量注入验证 |
| **风险** | 依赖: N/A / 数据: 环境变量禁止包含密钥 / 兼容: Next.js publicRuntimeConfig 模式 / 回滚: git revert |
| **决策记录** | 决策: 运行时环境变量注入 (API_URL/WS_URL/DEPLOY_MODE) / 理由: 构建时与运行时解耦, 支持多环境部署 / 来源: FE-07 Section 2 |

> 矩阵条目: D3-2 (前端子实现)

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
