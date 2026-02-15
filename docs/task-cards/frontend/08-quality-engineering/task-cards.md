# 前端质量工程 任务卡集

> 架构文档: `docs/frontend/08-quality-engineering.md`
> 里程碑来源: `docs/governance/milestone-matrix-frontend.md` (Phase 0, Phase 4)
> 影响门禁: `.eslintrc.js`, `vitest.config.ts`, `playwright.config.ts` -> pnpm lint + test

---

## Phase 0 -- 质量工具链

### TASK-FW0-6: ESLint + Prettier + eslint-plugin-jsx-a11y

| 字段 | 内容 |
|------|------|
| **目标** | `pnpm lint` 通过，0 error |
| **范围 (In Scope)** | `.eslintrc.js`, `.prettierrc`, `packages/eslint-config/` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps CI 配置 / 可观测性实现 |
| **依赖** | FW0-2 |
| **兼容策略** | 纯新增配置 |
| **验收命令** | `pnpm lint` (0 error) |
| **回滚方案** | `git revert <commit>` |
| **证据** | lint 配置正确 |
| **风险** | 依赖: ESLint/Prettier 版本兼容性 / 数据: N/A / 兼容: 纯新增, 不影响现有代码 / 回滚: git revert |
| **决策记录** | 决策: ESLint + Prettier + jsx-a11y 统一配置 / 理由: 代码风格一致性 + 无障碍前置 / 来源: FE-08 质量工程规范 |

> 矩阵条目: FW0-6 | V-x: X0-2

### TASK-FW0-7: Vitest 配置

| 字段 | 内容 |
|------|------|
| **目标** | `pnpm test` 运行不报错，测试框架可用 |
| **范围 (In Scope)** | `vitest.config.ts`, `packages/*/vitest.config.ts` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps CI 配置 / 可观测性实现 |
| **依赖** | FW0-2 |
| **兼容策略** | 纯新增配置 |
| **验收命令** | `pnpm test` (测试框架可运行) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 配置可用 |
| **风险** | 依赖: Vitest 版本与 Turborepo 兼容 / 数据: N/A / 兼容: 纯新增, 与 Playwright 并行不冲突 / 回滚: git revert |
| **决策记录** | 决策: Vitest 作为单元测试框架 / 理由: Vite 生态原生, 与 Next.js + Turborepo 兼容好 / 来源: FE-08 质量工程规范 |

> 矩阵条目: FW0-7

### TASK-FW0-8: Playwright E2E 基础设施配置

| 字段 | 内容 |
|------|------|
| **目标** | Playwright 测试框架就绪，为 20+ 张 [E2E] 验收卡提供硬前置条件 |
| **范围 (In Scope)** | `playwright.config.ts`, `apps/web/__tests__/`, `apps/admin/__tests__/`, CI 配置 |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / 具体 E2E 测试用例编写 / 可观测性实现 |
| **依赖** | FW0-1 (Next.js), FW0-2 (Turborepo) |
| **兼容策略** | 纯新增配置；与 Vitest (FW0-7) 并行不冲突 |
| **验收命令** | `pnpm exec playwright test --project=setup` (框架启动 + 浏览器下载 + 空测试通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | Playwright 空测试通过 + CI 中 E2E job 可触发 |
| **风险** | 依赖: Playwright 浏览器二进制下载 / 数据: N/A / 兼容: 纯新增, 与 Vitest 并行 / 回滚: git revert |
| **决策记录** | 决策: Playwright + axe-core 作为 E2E + a11y 基础设施 / 理由: FE-08 Section 5 定义 10 条关键路径, 需框架先行 / 来源: FE-08 质量工程规范 |

> 矩阵条目: FW0-8 (新增) | 与 FW0-6 (ESLint) / FW0-7 (Vitest) 同级
> 说明: FE-08 Section 5 定义 10 条关键 E2E 路径 (100% 覆盖目标)，本卡确保 Playwright + axe-core 基础设施在 Phase 2 E2E 卡激活前就绪

---

## Phase 4 -- 性能与无障碍

### TASK-FW4-1: 性能预算达标

| 字段 | 内容 |
|------|------|
| **目标** | LCP < 2.5s, FID < 100ms, CLS < 0.1, 首屏 < 200KB |
| **范围 (In Scope)** | `apps/web/next.config.js` (优化), `.lighthouserc.js` |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / DevOps CI 配置 / 功能逻辑变更 |
| **依赖** | -- |
| **兼容策略** | 性能优化不改功能 |
| **验收命令** | `pnpm lighthouse:ci` (4 项指标全达标) |
| **回滚方案** | `git revert <commit>` |
| **证据** | Lighthouse CI 报告 |
| **风险** | 依赖: Lighthouse CI 环境 / 数据: N/A / 兼容: 性能优化不改功能逻辑 / 回滚: git revert |
| **决策记录** | 决策: Core Web Vitals 四项阈值作为性能预算 / 理由: Google 标准, 直接影响 SEO 和用户体验 / 来源: FE-08 质量工程规范 Section 3 |

> 矩阵条目: FW4-1 | V-x: X4-1

### TASK-FW4-2: a11y 检查通过

| 字段 | 内容 |
|------|------|
| **目标** | axe-core 扫描 0 critical violations |
| **范围 (In Scope)** | `tests/a11y/`, CI 配置 |
| **范围外 (Out of Scope)** | 后端 API 实现 / 数据库 Schema / 性能优化 / 功能逻辑变更 |
| **依赖** | FW0-6 (jsx-a11y) |
| **兼容策略** | 新增 a11y CI |
| **验收命令** | `pnpm a11y:check` (0 critical violations) |
| **回滚方案** | `git revert <commit>` |
| **证据** | axe-core 报告 |
| **风险** | 依赖: axe-core + Playwright 集成 / 数据: N/A / 兼容: 纯新增 CI 检查 / 回滚: git revert |
| **决策记录** | 决策: axe-core 作为 a11y 自动化扫描工具 / 理由: WCAG 2.1 AA 合规, 与 Playwright 原生集成 / 来源: FE-08 质量工程规范 Section 4 |

> 矩阵条目: FW4-2

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
