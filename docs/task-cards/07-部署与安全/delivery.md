# Delivery/DevOps 任务卡集

> 治理规范: v1.1 Section 12 + Vibe 执行附录 Section 1
> 里程碑来源: `docs/governance/milestone-matrix-crosscutting.md` Section 1
> 影响门禁: `delivery/**`, `.github/**`, `scripts/**` -> CI 硬门禁
> 说明: Delivery 与 Obs&Security 共享架构文档 `07-部署与安全.md`，但作为独立维度管理

---

## Phase 0 -- 骨架与硬门禁（核心交付 Phase）

### TASK-D0-1: delivery/manifest.yaml 骨架

| 字段 | 内容 |
|------|------|
| **目标** | Schema 完整，值标 TBD，通过 schema 校验 |
| **范围 (In Scope)** | `delivery/manifest.yaml` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 基础设施内部 / 可观测性配置 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `python -c "import yaml; yaml.safe_load(open('delivery/manifest.yaml'))" && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | schema 校验通过 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯配置骨架 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: manifest.yaml 作为部署清单 SSOT / 理由: 声明式部署, Schema 可校验 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-1 | V-x: X0-2

### TASK-D0-2: milestone-matrix.schema.yaml

| 字段 | 内容 |
|------|------|
| **目标** | JSON Schema 定义存在且可解析 |
| **范围 (In Scope)** | `delivery/milestone-matrix.schema.yaml` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / manifest 值填充 / CI 流水线 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `python -c "import jsonschema; ..." && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | schema 可解析 |
| **风险** | 依赖: N/A / 数据: Schema 定义需稳定, 变更影响 milestone-matrix 校验 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: milestone-matrix.schema.yaml 定义里程碑矩阵 Schema / 理由: Schema 校验确保 milestone-matrix 结构完整性 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-2

### TASK-D0-3: preflight.sh 雏形

| 字段 | 内容 |
|------|------|
| **目标** | 检查 Docker/Compose/端口/磁盘，>= 4 项检查通过 |
| **范围 (In Scope)** | `delivery/preflight.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 安装器逻辑 / CI 流水线 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `bash delivery/preflight.sh` (>= 4 项检查通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 检查项完整 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯检查脚本 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: preflight.sh 预检 Docker/Compose/端口/磁盘 / 理由: 部署前环境验证, 避免安装失败 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-3 | V-x: X0-3

### TASK-D0-4: .github/workflows/ci.yml 硬门禁

| 字段 | 内容 |
|------|------|
| **目标** | PR -> CI 运行 ruff/mypy/pytest/guard 脚本 |
| **范围 (In Scope)** | `.github/workflows/ci.yml` |
| **范围外 (Out of Scope)** | 业务层代码实现 / 前端 CI 步骤 / 安全扫描 / 部署流程 |
| **依赖** | -- |
| **兼容策略** | 纯新增 CI 配置 |
| **验收命令** | [ENV-DEP] `gh pr create --draft --title test && gh pr checks` workflow: ci.yml 全部 step 通过 |
| **回滚方案** | `git revert <commit>` |
| **证据** | CI 流程完整 |
| **风险** | 依赖: GitHub Actions 运行时 / 数据: N/A -- 纯 CI 配置 / 兼容: 纯新增 CI 配置 / 回滚: git revert |
| **决策记录** | 决策: CI 硬门禁 ruff/mypy/pytest/guard 四道检查 / 理由: 质量前移, PR 合入前必须通过全部检查 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-4 | V-x: X0-2

### TASK-D0-5: check_layer_deps.sh

| 字段 | 内容 |
|------|------|
| **目标** | 检测层间依赖违规 |
| **范围 (In Scope)** | `scripts/check_layer_deps.sh` |
| **范围外 (Out of Scope)** | 业务层代码实现 / 前端依赖检查 / CI 流水线配置 / Port 兼容性检查 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `bash scripts/check_layer_deps.sh && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 违规检出率可验证 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯检查脚本 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: 层间依赖检查脚本自动化 / 理由: 架构分层约束需工具化保障, 防止违规依赖 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-5 | V-x: X0-2

### TASK-D0-6: check_port_compat.sh

| 字段 | 内容 |
|------|------|
| **目标** | 检测 Port 兼容性 |
| **范围 (In Scope)** | `scripts/check_port_compat.sh` |
| **范围外 (Out of Scope)** | 业务层代码实现 / 前端实现 / 层间依赖检查 / Migration 合规检查 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `bash scripts/check_port_compat.sh && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 兼容性检查通过 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯检查脚本 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: Port 兼容性检查脚本自动化 / 理由: Port 接口变更需向后兼容, 工具化检测防止破坏性变更 / 来源: ADR-033, 架构文档 07 Section 1 |

> 矩阵条目: D0-6 | V-x: X0-2

### TASK-D0-7: check_migration.sh

| 字段 | 内容 |
|------|------|
| **目标** | 检测 Migration 合规性 |
| **范围 (In Scope)** | `scripts/check_migration.sh` |
| **范围外 (Out of Scope)** | 具体 Migration 实现 / 业务层逻辑 / 前端实现 / 层间依赖检查 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `bash scripts/check_migration.sh && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 合规检查通过 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯检查脚本 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: Migration 合规性检查脚本自动化 / 理由: DDL 变更需可 downgrade, 工具化防止不可逆迁移 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-7

### TASK-D0-8: change_impact_router.sh

| 字段 | 内容 |
|------|------|
| **目标** | 自动标记 [CONTRACT]/[MIGRATION]/[SECURITY]，双路由 reviewer + CI gate |
| **范围 (In Scope)** | `scripts/change_impact_router.sh` |
| **范围外 (Out of Scope)** | 业务层代码实现 / 前端实现 / CI 具体步骤 / reviewer 分配策略 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `bash scripts/change_impact_router.sh && echo PASS` (3 类标记可触发) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 标记逻辑正确 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯标记逻辑 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: 变更影响路由器自动标记 3 类变更 / 理由: CONTRACT/MIGRATION/SECURITY 变更需额外审查, 自动分流降低遗漏风险 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-8

### TASK-D0-9: PR 模板 + CODEOWNERS + commit lint

| 字段 | 内容 |
|------|------|
| **目标** | 文件存在且 CI 校验通过 |
| **范围 (In Scope)** | `.github/PULL_REQUEST_TEMPLATE.md`, `CODEOWNERS`, `.commitlintrc.yml` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / CI 流水线配置 / Guard 脚本 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `test -f .github/PULL_REQUEST_TEMPLATE.md && test -f CODEOWNERS && test -f .commitlintrc.yml && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 文件全部存在 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯配置文件 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: PR 模板 + CODEOWNERS + commit lint 三件套 / 理由: 规范化 PR 流程, 自动分配 reviewer, 提交信息标准化 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-9 | V-x: X0-2

### TASK-D0-10: make verify-phase-0

| 字段 | 内容 |
|------|------|
| **目标** | 所有 P0 检查项输出 PASS |
| **范围 (In Scope)** | `Makefile` (verify-phase-0 target) |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 各检查脚本内部实现 / Phase 1+ 验证 |
| **依赖** | TASK-D0-1 ~ D0-9 |
| **兼容策略** | 纯新增 Make target |
| **验收命令** | [ENV-DEP] `make verify-phase-0` (完成度 100%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 全项通过 |
| **风险** | 依赖: D0-1~D0-9 全部就绪 / 数据: N/A -- 纯聚合验证 / 兼容: 纯新增 Make target / 回滚: git revert |
| **决策记录** | 决策: verify-phase-N 聚合验证命令 / 理由: 一键验证 Phase 完成度, 防止遗漏 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D0-10 | V-x: X0-2

---

## Phase 1 -- 安全扫描

### TASK-D1-1: 镜像安全扫描 (CI 软门禁)

| 字段 | 内容 |
|------|------|
| **目标** | Docker 镜像扫描无 Critical 漏洞 |
| **范围 (In Scope)** | `.github/workflows/ci.yml` (扫描步骤) |
| **范围外 (Out of Scope)** | 业务层代码实现 / 前端安全扫描 / SAST/secret scanning / 运行时安全 |
| **依赖** | -- |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | [ENV-DEP] CI-job: security-scan (Docker 镜像扫描无 Critical 漏洞) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 扫描报告可读 |
| **风险** | 依赖: CI 运行时 / 数据: N/A -- 纯扫描步骤 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: Docker 镜像安全扫描 CI 软门禁 / 理由: 生产镜像漏洞前置拦截 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D1-1 | V-x: X1-3

### TASK-D1-2: SBOM 生成

| 字段 | 内容 |
|------|------|
| **目标** | `make sbom` -> 生成 SPDX 格式 SBOM |
| **范围 (In Scope)** | `Makefile` (sbom target), SBOM 工具配置 |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 镜像扫描 / 依赖漏洞修复 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `make sbom` (SPDX 合规) |
| **回滚方案** | `git revert <commit>` |
| **证据** | SBOM 格式正确 |
| **风险** | 依赖: SBOM 工具 (syft 等) / 数据: N/A -- 纯生成工具 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: SPDX 格式 SBOM 生成 / 理由: 供应链安全合规要求, 依赖清单可审计 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D1-2

### TASK-D1-3: make verify-phase-1

| 字段 | 内容 |
|------|------|
| **目标** | 所有 P1 检查项输出 PASS |
| **范围 (In Scope)** | `Makefile` (verify-phase-1 target) |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 各扫描工具内部 / Phase 0/2+ 验证 |
| **依赖** | TASK-D1-1, TASK-D1-2 |
| **兼容策略** | 纯新增 |
| **验收命令** | `make verify-phase-1` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 全项通过 |
| **风险** | 依赖: D1-1 + D1-2 就绪 / 数据: N/A -- 纯聚合验证 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: verify-phase-1 聚合验证 / 理由: 一键验证 Phase 1 完成度 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D1-3 | V-x: X1-3

---

## Phase 2 -- Dogfooding

### TASK-D2-1: 前端 CI

| 字段 | 内容 |
|------|------|
| **目标** | pnpm lint + typecheck + test + a11y 全部通过 |
| **范围 (In Scope)** | `.github/workflows/ci.yml` (前端步骤) |
| **范围外 (Out of Scope)** | 后端 CI 步骤 / 前端业务逻辑 / 安全扫描 / 部署流程 |
| **依赖** | -- |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | [ENV-DEP] CI-job: lint-frontend + test-frontend + typecheck-frontend (0 error) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 4 项检查齐全 |
| **风险** | 依赖: pnpm + Node.js 运行时 / 数据: N/A -- 纯 CI 步骤 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: 前端 CI 4 道检查 (lint/typecheck/test/a11y) / 理由: 前端质量门禁与后端对齐 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D2-1 | V-x: X0-2 | V-fb: XF2-4

### TASK-D2-2: OpenAPI 类型同步检查 (CI 硬门禁)

| 字段 | 内容 |
|------|------|
| **目标** | 生成后 diff 为空 |
| **范围 (In Scope)** | `.github/workflows/ci.yml`, `scripts/check_openapi_sync.sh` |
| **范围外 (Out of Scope)** | OpenAPI Schema 内容定义 / 后端 API 实现 / 前端 API Client 内部逻辑 / 其他 CI 步骤 |
| **依赖** | -- |
| **兼容策略** | 新增 CI 硬门禁 |
| **验收命令** | `pnpm openapi:generate && git diff --exit-code` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 同步脚本可用 |
| **风险** | 依赖: OpenAPI Schema 定义 / 数据: Schema 不同步=前后端类型不一致 / 兼容: 新增 CI 硬门禁 / 回滚: git revert |
| **决策记录** | 决策: OpenAPI 类型同步 CI 硬门禁 / 理由: 前后端类型一致性强制保障, 生成后 diff=0 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D2-2 | V-fb: XF2-4

### TASK-D2-3: 内部 dogfooding 环境

| 字段 | 内容 |
|------|------|
| **目标** | 团队成员可实际使用系统对话 |
| **范围 (In Scope)** | `deploy/staging/` |
| **范围外 (Out of Scope)** | 业务层功能完整性 / 前端 UI 细节 / 生产部署 / 性能调优 |
| **依赖** | 全栈部署 |
| **兼容策略** | 独立环境 |
| **验收命令** | [ENV-DEP] `pytest tests/e2e/cross/test_dogfooding_env.py -v` (团队可使用) |
| **回滚方案** | 销毁 staging 环境 |
| **证据** | 环境可访问 |
| **风险** | 依赖: 全栈部署就绪 / 数据: staging 数据需与生产隔离 / 兼容: 独立环境, 不影响其他环境 / 回滚: 销毁 staging |
| **决策记录** | 决策: 内部 dogfooding 环境独立部署 / 理由: 团队实际使用验证, 提前发现问题 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D2-3 | V-x: X2-1 | V-fb: XF2-1

### TASK-D2-4: 资源消耗数据记录

| 字段 | 内容 |
|------|------|
| **目标** | CPU/内存/存储使用量有记录 |
| **范围 (In Scope)** | 监控配置 |
| **范围外 (Out of Scope)** | 业务层指标 / 前端性能监控 / Grafana 看板 / SLI/SLO 配置 |
| **依赖** | -- |
| **兼容策略** | 纯新增监控 |
| **验收命令** | [ENV-DEP] `curl -s localhost:9090/api/v1/query?query=process_cpu_seconds_total` staging: 3 项资源数据 (CPU/内存/存储) 有记录 |
| **回滚方案** | 不适用 |
| **证据** | 监控截图 |
| **风险** | 依赖: 监控栈就绪 / 数据: 资源消耗数据用于 manifest 填充 / 兼容: 纯新增监控 / 回滚: 不适用 |
| **决策记录** | 决策: CPU/内存/存储资源消耗记录 / 理由: 为 manifest.yaml 实值填充提供数据基础 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D2-4

### TASK-D2-5: make verify-phase-2

| 字段 | 内容 |
|------|------|
| **目标** | 所有 P2 检查项输出 PASS |
| **范围 (In Scope)** | `Makefile` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端业务功能 / 各检查项内部 / Phase 1/3+ 验证 |
| **依赖** | TASK-D2-1 ~ D2-4 |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `make verify-phase-2` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 全项通过 |
| **风险** | 依赖: D2-1~D2-4 就绪 / 数据: N/A -- 纯聚合验证 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: verify-phase-2 聚合验证 / 理由: 一键验证 Phase 2 完成度 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D2-5

---

## Phase 3 -- 安装器产品化

### TASK-D3-1: manifest.yaml TBD -> 实值

| 字段 | 内容 |
|------|------|
| **目标** | 所有核心字段有真实值，TBD 项 = 0 |
| **范围 (In Scope)** | `delivery/manifest.yaml` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 安装器脚本 / 漂移检查脚本 |
| **依赖** | 资源数据 (D2-4) |
| **兼容策略** | 填充已有字段 |
| **验收命令** | `grep -c TBD delivery/manifest.yaml` (= 0) |
| **回滚方案** | `git revert <commit>` |
| **证据** | schema 校验通过 |
| **风险** | 依赖: D2-4 (资源消耗数据) / 数据: 值需基于实际测量, 错误值=部署失败 / 兼容: 填充已有字段 / 回滚: git revert |
| **决策记录** | 决策: manifest TBD 全部填充实值 / 理由: 部署清单从骨架到产品化, 支持自动部署 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D3-1 | V-x: X4-3

### TASK-D3-2: 安装器 + preflight 产品化

| 字段 | 内容 |
|------|------|
| **目标** | 全新服务器运行安装脚本 -> 系统可用 |
| **范围 (In Scope)** | `delivery/install.sh`, `delivery/preflight.sh` (增强) |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / manifest 值定义 / 升级回滚流程 |
| **依赖** | TASK-D0-3 |
| **兼容策略** | 增强已有脚本 |
| **验收命令** | [ENV-DEP] `docker compose up -d && bash delivery/preflight.sh` staging: 全新机器可部署 |
| **回滚方案** | 卸载脚本 |
| **证据** | 安装脚本可执行 |
| **风险** | 依赖: D0-3 (preflight 雏形) / 数据: 安装脚本操作系统级资源, 需幂等 / 兼容: 增强已有脚本 / 回滚: 卸载脚本 |
| **决策记录** | 决策: 安装器 + preflight 产品化 / 理由: 全新服务器一键部署, 降低运维门槛 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D3-2

### TASK-D3-3: deploy/* 与 manifest 一致性检查

| 字段 | 内容 |
|------|------|
| **目标** | `scripts/check_manifest_drift.sh` 通过，漂移 = 0 |
| **范围 (In Scope)** | `scripts/check_manifest_drift.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / manifest 值填充 / deploy/ 目录内部 |
| **依赖** | TASK-D3-1 |
| **兼容策略** | 纯新增检查脚本 |
| **验收命令** | [ENV-DEP] `bash scripts/check_manifest_drift.sh` (漂移 = 0) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 漂移检测脚本可用 |
| **风险** | 依赖: D3-1 (manifest 实值) / 数据: 漂移=deploy 配置与 manifest 不一致 / 兼容: 纯新增检查脚本 / 回滚: git revert |
| **决策记录** | 决策: deploy/* 与 manifest 漂移检测自动化 / 理由: 部署配置 SSOT 一致性保障 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D3-3 | V-x: X4-3

### TASK-D3-4: make verify-phase-3

| 字段 | 内容 |
|------|------|
| **目标** | 所有 P3 检查项输出 PASS |
| **范围 (In Scope)** | `Makefile` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 各检查项内部 / Phase 2/4+ 验证 |
| **依赖** | TASK-D3-1 ~ D3-3 |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `make verify-phase-3` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 全项通过 |
| **风险** | 依赖: D3-1~D3-3 就绪 / 数据: N/A -- 纯聚合验证 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: verify-phase-3 聚合验证 / 理由: 一键验证 Phase 3 完成度 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D3-4

---

## Phase 4 -- 运维产品化

### TASK-D4-1: 升级回滚流程产品化

| 字段 | 内容 |
|------|------|
| **目标** | 升级 -> 回滚 -> 数据完整 -> 用时 < 5min |
| **范围 (In Scope)** | `delivery/upgrade.sh`, `delivery/rollback.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / Migration DDL / 备份恢复 |
| **依赖** | -- |
| **兼容策略** | 纯新增脚本 |
| **验收命令** | [ENV-DEP] `bash delivery/upgrade.sh && bash delivery/rollback.sh` (< 5min) |
| **回滚方案** | 脚本内置 |
| **证据** | 回滚脚本可用 |
| **风险** | 依赖: Docker Compose 环境 / 数据: 升级回滚需保证数据完整性 / 兼容: 纯新增脚本 / 回滚: 脚本内置回滚逻辑 |
| **决策记录** | 决策: 升级回滚流程产品化 (< 5min) / 理由: 生产环境升级需可回滚, 控制停机时间 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D4-1 | V-x: X4-2

### TASK-D4-2: 备份恢复演练门禁

| 字段 | 内容 |
|------|------|
| **目标** | `make dr-drill` -> upgrade->downgrade->upgrade 通过 |
| **范围 (In Scope)** | `Makefile` (dr-drill target), 演练脚本 |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / PG 备份实现 / 监控告警 |
| **依赖** | I4-3 |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `make dr-drill` (3 步演练全通过) |
| **回滚方案** | 脚本级回退 |
| **证据** | 演练脚本可用 |
| **风险** | 依赖: I4-3 (备份恢复能力) / 数据: 演练需隔离环境, 防止影响生产 / 兼容: 纯新增 / 回滚: 脚本级回退 |
| **决策记录** | 决策: DR 演练门禁 (upgrade->downgrade->upgrade) / 理由: 灾难恢复能力定期验证 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D4-2 | V-x: X4-2

### TASK-D4-3: 一键诊断包 diyu diagnose

| 字段 | 内容 |
|------|------|
| **目标** | 生成 tar.gz 含 logs/config/health/metrics |
| **范围 (In Scope)** | `delivery/diagnose.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 监控告警 / 密钥管理 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `bash delivery/diagnose.sh` (4 类信息全包含) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 诊断包内容完整 |
| **风险** | 依赖: N/A / 数据: 诊断包需脱敏, 禁止包含密钥 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: 一键诊断包 (logs/config/health/metrics) / 理由: 远程排障标准化, 降低支持成本 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D4-3

### TASK-D4-4: 密钥轮换 + 证书管理

| 字段 | 内容 |
|------|------|
| **目标** | 轮换密钥 -> 服务无中断 |
| **范围 (In Scope)** | `scripts/rotate_secrets.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 密钥存储系统 / 证书颁发 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `bash scripts/rotate_secrets.sh` (轮换无中断) |
| **回滚方案** | 恢复旧密钥 |
| **证据** | 轮换脚本可用 |
| **风险** | 依赖: N/A / 数据: 密钥轮换需零停机, 旧密钥需安全销毁 / 兼容: 纯新增 / 回滚: 恢复旧密钥 |
| **决策记录** | 决策: 密钥轮换 + 证书管理自动化 / 理由: 安全合规要求定期轮换, 零停机为硬指标 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D4-4

### TASK-D4-5: 轻量离线 (docker save/load)

| 字段 | 内容 |
|------|------|
| **目标** | save 镜像 -> 断网 -> load -> 服务启动 |
| **范围 (In Scope)** | `delivery/offline.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 在线部署流程 / 镜像仓库 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `docker compose -f docker-compose.yml up -d` staging: 离线流程验证 (docker save/load 后服务启动) |
| **回滚方案** | 不适用 |
| **证据** | 离线部署截图 |
| **风险** | 依赖: Docker save/load 能力 / 数据: 离线镜像需包含全部依赖 / 兼容: 纯新增 / 回滚: 不适用 |
| **决策记录** | 决策: 轻量离线部署 (docker save/load) / 理由: 支持无网络环境部署, 降低网络依赖 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D4-5

### TASK-D4-6: make verify-phase-4

| 字段 | 内容 |
|------|------|
| **目标** | 所有 P4 检查项输出 PASS |
| **范围 (In Scope)** | `Makefile` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 各检查项内部 / Phase 3/5+ 验证 |
| **依赖** | TASK-D4-1 ~ D4-5 |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `make verify-phase-4` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 全项通过 |
| **风险** | 依赖: D4-1~D4-5 就绪 / 数据: N/A -- 纯聚合验证 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: verify-phase-4 聚合验证 / 理由: 一键验证 Phase 4 完成度 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D4-6 | V-x: X4-2

---

## Phase 5 -- 自动化与合规

### TASK-D5-1: 三 SSOT 自动一致性检查

| 字段 | 内容 |
|------|------|
| **目标** | CI 自动检测 Decision/Runtime/Delivery SSOT 偏差 |
| **范围 (In Scope)** | `scripts/check_ssot_drift.sh`, `.github/workflows/ci.yml` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / SSOT 内容定义 / 偏差修复 |
| **依赖** | OS5-1 |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | [ENV-DEP] `bash scripts/check_ssot_drift.sh` (偏差自动检出) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 检测脚本可用 |
| **风险** | 依赖: OS5-1 (可观测性 SSOT 检查) / 数据: SSOT 偏差=架构腐化信号 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: 三 SSOT (Decision/Runtime/Delivery) 自动一致性检查 / 理由: 架构决策与运行时配置和部署清单需一致 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D5-1 | V-x: X5-2

### TASK-D5-2: Exception Register 到期自动审计

| 字段 | 内容 |
|------|------|
| **目标** | 过期例外自动标记并通知 |
| **范围 (In Scope)** | `src/governance/exception_audit.py`, Cron Job |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端通知 UI / Exception Register 内容管理 / 审计报告 |
| **依赖** | OS5-3 |
| **兼容策略** | 新增审计逻辑 |
| **验收命令** | [ENV-DEP] `pytest tests/unit/governance/test_exception_audit.py -v` staging: 到期例外自动通知 owner |
| **回滚方案** | 禁用 Cron Job |
| **证据** | 审计逻辑验证 |
| **风险** | 依赖: OS5-3 (Exception Register) / 数据: 到期例外需及时处理, 逾期=合规风险 / 兼容: 新增审计逻辑 / 回滚: 禁用 Cron Job |
| **决策记录** | 决策: Exception Register 到期自动审计 / 理由: 例外项有生命周期, 到期未处理需自动告警 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D5-2 | V-x: X5-1

### TASK-D5-3: 月度架构偏差审计模板

| 字段 | 内容 |
|------|------|
| **目标** | 生成审计报告 |
| **范围 (In Scope)** | `scripts/generate_audit_report.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端报告展示 / SSOT 检查 / Exception 审计 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `make audit-report` (报告可产出) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 模板完整性 |
| **风险** | 依赖: N/A / 数据: 报告需脱敏, 禁止包含密钥 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: 月度架构偏差审计模板 / 理由: 定期架构健康检查, 防止架构腐化 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D5-3 | V-x: X5-2

### TASK-D5-4: make verify-phase-5

| 字段 | 内容 |
|------|------|
| **目标** | 所有 P5 检查项输出 PASS |
| **范围 (In Scope)** | `Makefile` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 各检查项内部 / Phase 4 验证 |
| **依赖** | TASK-D5-1 ~ D5-3 |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `make verify-phase-5` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 全项通过 |
| **风险** | 依赖: D5-1~D5-3 就绪 / 数据: N/A -- 纯聚合验证 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: verify-phase-5 聚合验证 / 理由: 一键验证 Phase 5 完成度 / 来源: 架构文档 07 Section 1 |

> 矩阵条目: D5-4 | V-x: X5-2

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
