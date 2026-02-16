# DIYU Agent 任务卡治理工程化 -- 完整执行实施计划 v1.0

> Owner: Faye
> Version: 1.0
> Date: 2026-02-13
> Status: Approved Baseline
> Scope: 从 Schema 冻结到 CI 门禁到工作流固化到运行治理的全链路闭环
> Inputs: task-card-schema-v1.0.md + governance-optimization-plan.md v2.0 + 实施差异分析
> Core Thesis: 治理闭环 (Stage 0-4) + 可执行基线 (Stage E) + 商业交付 (Stage C) 三线并行

---

## 0. 当前状态基线 (Stage 0 -- 已完成)

### 0.1 历史修复 (已闭环)

| 修复 | 内容 | 状态 |
|------|------|------|
| F1 | Admin Phase 0 L1 scope 重写 | Done |
| F2 | ImageGenerate 去 M1 化 (3 文件 + 矩阵) | Done |
| F3 | 4 项 controlled-pending 状态文档化 | Done (Section 10) |
| F4 | [ENV-DEP] 规则 + 7 A-class 命令化 + 68 B-class 标注 | Done |
| F5 | 5 项矩阵 index 计数修正 | Done |
| F6 | 字段命名统一 (关联矩阵条目 -> 矩阵条目) | Done |
| R1 | 8 条遗留自然语言验收命令 (4 命令化 + 4 ENV-DEP) | Done |
| R2 | 2 张孤儿卡补矩阵 ID + ImageGenerate Skill 层残留 | Done |

### 0.2 Stage 0 产出物 (已落盘)

| 产出 | 路径 | 状态 |
|------|------|------|
| Schema 规范 | `docs/governance/task-card-schema-v1.0.md` | Frozen (297 行, sha256: `a71adc21`) |
| 计数脚本 | `scripts/count_task_cards.py` | Done (378 行, sha256: `762ff413`) |
| 校验脚本 | `scripts/check_task_schema.py` | Done (669 行, sha256: `f84653ff`) |
| MANUAL-VERIFY 规则 | `governance-optimization-plan.md` Section 8.7 | Done |
| Tier 分层规则 | `governance-optimization-plan.md` Section 8.8 | Done |
| Exception 格式 | `governance-optimization-plan.md` Section 8.9 | Done |
| 矩阵模板更新 | `milestone-matrix.md` Section 3.2 | Done |
| 治理优化计划 v2.0 | `docs/governance/governance-optimization-plan.md` | Done (1062 行) |

### 0.3 精确基线数据

```
总卡数:        258
Tier-A:        211 (81.8%)
Tier-B:         47 (18.2%)
BLOCK 违规:    680
  - 范围外缺失:  258 (全部卡)
  - 决策记录缺失: 211 (全部 Tier-A)
  - 风险字段缺失: 211 (全部 Tier-A)
WARNING:       151 (目标非结果导向)
INFO:           70 ([ENV-DEP] CI 映射提醒)
孤儿卡:          0
[ENV-DEP]:      72
[MANUAL-VERIFY]: 0
```

### 0.4 未落盘资产清单 (Stage 0 后仍缺)

> [!NOTE] 以下为 Stage 0 (2026-02-10) 时的快照。截至 2026-02-14，表中全部 11 项已落盘。
> 保留此表作为历史参照，不删除。

以下列出仓库中 Stage 0 完成时**不存在**的关键文件 (历史快照)：

| 类别 | 缺失项 | 所属阶段 |
|------|--------|---------|
| 工程基线 | `Makefile` | Stage E |
| 工程基线 | `pyproject.toml` / `uv.lock` | Stage E |
| 工程基线 | `pnpm-workspace.yaml` / `turbo.json` | Stage E |
| 工程基线 | `.gitignore` / `.env.example` / `.editorconfig` | Stage E |
| 治理入口 | `CLAUDE.md` (项目级) | Stage E |
| CI/CD | `.github/workflows/*.yml` | Stage 2 |
| Hooks | `.claude/settings.json` (项目级) | Stage 3 |
| 审计 | `.audit/` 目录 | Stage 3 |
| 证据 | `evidence/` 目录 | Stage 2.5 |
| 交付 | `delivery/` 目录 | Stage C |
| 矩阵 YAML | `delivery/milestone-matrix.yaml` | Stage E |

---

## 1. Stage 1 -- 全量任务卡补齐 (4 波次)

### 1.0 编辑规范 (所有波次遵循)

**字段规范顺序 (Tier-A):**

```
| **目标** | ... |
| **范围 (In Scope)** | ... |
| **范围外 (Out of Scope)** | ... |
| **依赖** | ... |
| **风险** | 依赖: ... / 数据: ... / 兼容: ... / 回滚: ... |
| **兼容策略** | ... |
| **验收命令** | ... |
| **回滚方案** | ... |
| **证据** | ... |
| **决策记录** | 决策: ... / 理由: ... / 来源: ... |
```

**字段规范顺序 (Tier-B):**

```
| **目标** | ... |
| **范围 (In Scope)** | ... |
| **范围外 (Out of Scope)** | ... |
| **依赖** | ... |
| **兼容策略** | ... |
| **验收命令** | ... |
| **回滚方案** | ... |
| **证据** | ... |
```

**编辑原则:**

1. 每张卡的新字段内容必须参考对应 L1 架构文档 (见 Section 1.0.1)
2. `范围` 字段标签统一改为 `范围 (In Scope)`
3. `范围外 (Out of Scope)` 可引用层级默认排除项 (见 Section 1.0.2)，亦可自定义
4. `风险` 四类中不适用的标注 `N/A: [一句话原因]`
5. `决策记录` 无关键取舍时填 `本卡无关键取舍，遵循层内默认约定`
6. Tier-B 卡若存在非平凡风险，仍需写风险字段 (非强制)
7. 每波次编辑后必须运行 `check_task_schema.py --mode full` 产出机器报告
8. Tier-A 卡的风险/决策内容必须参考 L1 架构文档，禁止机械模板填充

### 1.0.1 Layer -> L1 Architecture Doc 映射

| Layer | L1 架构文档 | 任务卡文件 |
|-------|-----------|-----------|
| Brain | `docs/architecture/01-对话Agent层-Brain.md` | `01-对话Agent层-Brain/brain.md` |
| MemoryCore | `docs/architecture/01-对话Agent层-Brain.md` (Section 2) | `01-对话Agent层-Brain/memory-core.md` |
| Knowledge | `docs/architecture/02-Knowledge层.md` | `02-Knowledge层/knowledge.md` |
| Skill | `docs/architecture/03-Skill层.md` | `03-Skill层/skill.md` |
| Tool | `docs/architecture/04-Tool层.md` | `04-Tool层/tool.md` |
| Gateway | `docs/architecture/05-Gateway层.md` + `05a-API-Contract.md` | `05-Gateway层/gateway.md` |
| Infrastructure | `docs/architecture/06-基础设施层.md` | `06-基础设施层/infrastructure.md` |
| Delivery + ObsSecurity | `docs/architecture/07-部署与安全.md` | `07-部署与安全/delivery.md` + `obs-security.md` |
| FE-Monorepo | `docs/frontend/01-monorepo-infrastructure.md` | `frontend/01-monorepo-infrastructure/task-cards.md` |
| FE-Transport | `docs/frontend/02-transport-layer.md` | `frontend/02-transport-layer/task-cards.md` |
| FE-Auth | `docs/frontend/03-auth-permission.md` | `frontend/03-auth-permission/task-cards.md` |
| FE-Dialog | `docs/frontend/04-dialog-engine.md` | `frontend/04-dialog-engine/task-cards.md` |
| FE-Pages | `docs/frontend/05-page-routes.md` | `frontend/05-page-routes/task-cards.md` |
| FE-Admin | `docs/frontend/06-admin-console.md` | `frontend/06-admin-console/task-cards.md` |
| FE-Deploy | `docs/frontend/07-deployment.md` | `frontend/07-deployment/task-cards.md` |
| FE-QE | `docs/frontend/08-quality-engineering.md` | `frontend/08-quality-engineering/task-cards.md` |

### 1.0.2 Per-Layer Default Out of Scope

| Layer | 默认排除项 |
|-------|-----------|
| Brain | Adapter 实现 / 前端集成 / Memory Core 内部存储 / 性能调优 |
| MemoryCore | 向量化实现细节 / 外部存储 Adapter / Brain 调度逻辑 |
| Knowledge | 内容审核逻辑 / 前端 UI / 文档解析器实现 |
| Skill | 具体 Skill 业务逻辑 / 前端表单 / Tool 调用实现 |
| Tool | LLM Provider 具体实现 / 计费逻辑 / 前端 |
| Gateway | 前端路由 / 数据库 Schema / 业务逻辑 |
| Infrastructure | 应用层业务逻辑 / 前端 / Gateway 路由 |
| Delivery | 应用层功能 / 前端部署 / 安全策略 |
| ObsSecurity | 应用层功能 / 前端 / 基础设施运维 |
| Frontend* | 后端 API 实现 / 数据库 Schema / DevOps |

---

### Wave 1: Brain 层 + FE-Monorepo (Pilot)

| 指标 | 数值 |
|------|------|
| 文件 | `brain.md` (24 卡) + `memory-core.md` (18 卡) + `frontend/01-monorepo-infrastructure/task-cards.md` (8 卡) |
| 总卡数 | 50 |
| Tier 分布 | A: 39, B: 11 |
| BLOCK 数 | 128 (范围外 50 + 决策记录 39 + 风险 39) |
| 参考 L1 | `01-对话Agent层-Brain.md` + `docs/frontend/01-monorepo-infrastructure.md` |

**执行步骤:**

1. 读取 `01-对话Agent层-Brain.md` 提取 Brain/MemoryCore 层架构约束
2. 读取 `01-monorepo-infrastructure.md` 提取前端 Monorepo 架构约束
3. 逐卡编辑 `brain.md`:
   - 2 张 Tier-B: 各加 1 字段 (范围外)
   - 22 张 Tier-A: 各加 3 字段 (范围外 + 风险 + 决策记录)
   - `范围` 标签改为 `范围 (In Scope)`
4. 逐卡编辑 `memory-core.md`:
   - 2 张 Tier-B: 各加 1 字段
   - 16 张 Tier-A: 各加 3 字段
5. 逐卡编辑 `frontend/01-monorepo-infrastructure/task-cards.md`:
   - 7 张 Tier-B: 各加 1 字段
   - 1 张 Tier-A: 加 3 字段
6. 运行校验: `python scripts/check_task_schema.py --mode full --json`
7. 确认 Wave 1 文件 BLOCK = 0
8. 运行 WARNING 审查: 检查目标结果导向 WARNING，必要时微调目标措辞
9. 产出: Wave 1 差异报告

**Wave 1 退出条件:**

- 3 个文件 BLOCK = 0
- `check_task_schema.py` 无 `required-field` / `risk-field-required` 违规
- 范围外字段 100% 覆盖
- Schema v1.0 实际可行性确认 (若需微调 -> v1.1)

**Wave 1 附加任务 (仅 Pilot 波):**

- 评估编辑效率，估算后续波次工作量
- 评估 `check_task_schema.py` 误报/漏报率，必要时调整脚本
- 确认字段顺序规范是否需微调
- 确认风险/决策记录的"N/A"和"默认约定"表述是否引发误报

---

### Wave 2: 核心业务层

| 指标 | 数值 |
|------|------|
| 文件 | `knowledge.md` (15) + `skill.md` (10) + `tool.md` (15) + `gateway.md` (24) |
| 总卡数 | 64 |
| Tier 分布 | A: 53, B: 11 |
| BLOCK 数 | 170 |
| 参考 L1 | `02-Knowledge层.md` + `03-Skill层.md` + `04-Tool层.md` + `05-Gateway层.md` + `05a-API-Contract.md` |

**执行步骤:**

1. 读取 4 份 L1 架构文档，提取每层约束
2. 逐文件、逐卡编辑 (顺序: knowledge -> skill -> tool -> gateway)
3. 每文件编辑后立即运行单文件校验
4. 全部完成后运行 Wave 2 整体校验
5. 产出: Wave 2 差异报告

**Wave 2 退出条件:** 4 个文件 BLOCK = 0

---

### Wave 3: 基础设施/运维层

| 指标 | 数值 |
|------|------|
| 文件 | `infrastructure.md` (31) + `delivery.md` (32) + `obs-security.md` (39) |
| 总卡数 | 102 |
| Tier 分布 | A: 82, B: 20 |
| BLOCK 数 | 266 |
| 参考 L1 | `06-基础设施层.md` + `07-部署与安全.md` |

**执行步骤:**

1. 读取 L1 架构文档
2. 逐文件编辑 (顺序: infrastructure -> delivery -> obs-security)
3. `obs-security` 全部 39 卡均为 Tier-A，工作量最大
4. 每文件编辑后运行校验
5. 产出: Wave 3 差异报告

**Wave 3 退出条件:** 3 个文件 BLOCK = 0

---

### Wave 4: 前端层

| 指标 | 数值 |
|------|------|
| 文件 | 7 个前端子目录 `task-cards.md` (FE-Monorepo 已在 Wave 1 完成) |
| 总卡数 | 42 |
| Tier 分布 | A: 37, B: 5 |
| BLOCK 数 | 116 |
| 参考 L1 | `docs/frontend/02~08-*.md` (7 份) |

**文件清单:**

| 文件 | 卡数 | A/B | BLOCK |
|------|------|-----|-------|
| `02-transport-layer/task-cards.md` | 3 | 3/0 | 9 |
| `03-auth-permission/task-cards.md` | 6 | 4/2 | 14 |
| `04-dialog-engine/task-cards.md` | 7 | 7/0 | 21 |
| `05-page-routes/task-cards.md` | 6 | 6/0 | 18 |
| `06-admin-console/task-cards.md` | 11 | 11/0 | 33 |
| `07-deployment/task-cards.md` | 4 | 4/0 | 12 |
| `08-quality-engineering/task-cards.md` | 5 | 2/3 | 9 |

**执行步骤:**

1. 读取 7 份前端 L1 架构文档
2. 逐文件编辑 (按上表顺序)
3. 每文件编辑后运行校验
4. 产出: Wave 4 差异报告

**Wave 4 退出条件:** 7 个文件 BLOCK = 0

---

### Stage 1 全量退出条件

```bash
python scripts/check_task_schema.py --mode full
# Expected: RESULT: PASS (0 blocking violations)
```

| 检查项 | 目标值 |
|--------|--------|
| BLOCK violations | 0 |
| 范围外覆盖率 | 258/258 (100%) |
| 风险覆盖率 (Tier-A) | 211/211 (100%) |
| 决策记录覆盖率 (Tier-A) | 211/211 (100%) |
| 孤儿卡 | 0 |
| WARNING (目标结果导向) | 审查通过或已微调 |

---

## 2. Stage 2 -- CI 门禁上线 (渐进 3 步)

### Step 2.1: Warning 模式 (与 Wave 1 同步启动)

**产出:** `.github/workflows/task-card-check.yml`

```yaml
# 核心逻辑:
# - 触发: PR 修改 docs/task-cards/**/*.md
# - 运行: python scripts/check_task_schema.py --mode warning
# - 结果: 输出 WARNING 报告到 PR comment，不阻断合并
```

**执行步骤:**

1. 创建 `.github/workflows/task-card-check.yml`
2. 配置触发条件 (paths filter: `docs/task-cards/**`)
3. 运行 `check_task_schema.py --mode warning`
4. 输出结果为 PR annotation (GitHub Actions)
5. 验证: 提交一个 task card 修改 PR，确认 CI job 正常运行

### Step 2.2: 增量阻断 (Wave 1 完成后)

**变更:** CI 配置改为 `--mode incremental --diff-base main`

- 仅新增/修改的卡强制 BLOCK
- 存量未修复卡继续 WARNING
- 目的: 确保不退化，同时不阻断无关 PR

### Step 2.3: 全量阻断 (Stage 1 全量完成后)

**变更:** CI 配置改为 `--mode full`

- 全量卡 BLOCK
- 所有 PR 必须通过
- 前提: Stage 1 全部 4 波完成，BLOCK = 0

### Stage 2 退出条件

- CI workflow 文件存在且可运行
- Full 模式下 BLOCK = 0
- PR 提交 task card 修改时 CI 自动运行

---

## 2.5 Stage 2.5 -- 证据基础设施

> 来源: 融合优化 -- 证据与卡片修复解耦。
> 原因: 170+ 张卡的证据字段标记 TBD/CI-link-pending，证据回填依赖 CI 基础设施就位。
> 前置: Stage 2 CI 门禁上线完成。

### 产出

```
evidence/
  phase-0/
    verify-phase-0-{sha}.json       # Phase 验收报告
    ci-run-{sha}.json               # CI 运行结果
  phase-1/
    ...
  release/
    v0.1.0/
      all-gates-pass.json           # 全门禁通过证据
      sbom.json                     # 软件物料清单
      manifest-frozen.yaml          # 冻结的交付清单
```

### 执行步骤

1. 创建 `evidence/` 目录结构 (按 Phase 分层)
2. 配置 CI 自动归档: GitHub Actions artifact upload 到 `evidence/`
3. 回填 170+ 张卡的证据字段:
   - CI 可产出的: 填入 `evidence/phase-N/` 路径模板
   - 尚无 CI job 的: 标注 `[证据待 CI 就位后回填]` + 对应 Phase
4. 运行 `check_task_schema.py --mode full` 确认无新增 BLOCK

### Stage 2.5 退出条件

- `evidence/` 目录结构存在
- CI 产出的报告自动归档到 `evidence/`
- 证据字段 TBD 比例降至 < 10%

---

## 3. Stage 3 -- 工作流固化

### 3.1 扩展现有 Agent (非新建)

> 说明: 项目级 Agent 位于 `.claude/agents/` (随仓库分发)，用户级 Agent 位于 `$HOME/.claude/agents/` (个人配置，不入仓库)。
> 扩展方式: 在现有 Agent 的 prompt 中增加 task-card-aware section。
> 协作模型: 全部 Agent 有全局只读权限，仅写入权限受限于各自边界 (Pipeline 模型)。
> 注: 项目已有 `.claude/agents/diyu-architect.md`、`diyu-security-reviewer.md`、`diyu-tdd-guide.md`。

| Agent | 扩展内容 | 写入边界 |
|-------|---------|---------|
| `.claude/agents/diyu-architect.md` | 新增 L1->L2 traceability check: 架构变更时验证矩阵条目同步 | `docs/governance/milestone-matrix-*.md` |
| `.claude/agents/diyu-tdd-guide.md` | 新增 task-card-aware planning section: TDD 流程中检查卡片覆盖 | `docs/task-cards/` |
| `.claude/agents/diyu-security-reviewer.md` | 新增 task card review: 安全变更涉及 task card 文件时自动校验 schema | 只读 (输出 review comment) |

### 3.2 新建 1 个 Skill: skill-taskcard-governance

**路径:** 项目级 `.claude/skills/taskcard-governance/SKILL.md` (随仓库分发)

**功能合并 (原计划 4 个 -> 合并为 1 个):**

| Workflow | 功能 | 输入 | 输出 |
|----------|------|------|------|
| W1 schema-normalization | 补字段 + 标准化格式 | 现有 task cards | schema-compliant cards |
| W2 traceability-link | 校验 L1/L2/L3 链路 | milestone-matrix + task cards | 双向链路报告 |
| W3 acceptance-normalizer | 命令化 + 标签标注 | 验收命令 | 标注后的命令 |
| W4 evidence-and-gate | 生成 Gate 审查报告 | acceptance + evidence | gate report (PASS/FAIL) |

**触发方式:** 通过 Skill 工具调用，渐进披露每步所需上下文。

### 3.3 新建 1 个 Command: /gate-review

**路径:** 项目级 `.claude/commands/gate-review.md` (随仓库分发)

**功能:**

1. 运行 `check_task_schema.py --mode full --json`
2. 运行 `count_task_cards.py --json`
3. 汇总 BLOCK/WARNING/Exception 清单
4. 检查 Section 10 controlled-pending 到期状态
5. 输出 Gate Review 报告 (PASS/FAIL + blockers + exceptions)

### 3.4 Hooks 配置 (项目级)

**路径:** 项目级 `.claude/settings.json`

> 来源: governance-optimization-plan.md Section 缺口 C。
> 已设计完整的 hooks 方案 (PreToolUse/PostToolUse)，Stage 3 落盘。

**核心配置:**

- `PreToolUse: Edit|Write` -> `scripts/hooks/pre_edit_audit.sh` (审计日志)
- `PreToolUse: Bash` -> `scripts/hooks/pre_commit_gate.sh` (commit 前门禁)
- `PostToolUse: Edit|Write` -> `scripts/hooks/post_edit_format.sh` (格式化)

**审计日志目录:** `.audit/session-{timestamp}.jsonl`

### Stage 3 退出条件

- [x] Skill 可被 Claude Code 调用并正确执行 W1-W4
  - 证据: `bash .claude/skills/taskcard-governance/scripts/run_all.sh`
- [x] `/gate-review` 可输出完整报告
  - 证据: `.claude/commands/gate-review.md` 已落盘
- [x] 3 个 Agent 扩展已集成并测试
  - 证据: `ANCHOR:task-card-aware` in diyu-architect/tdd-guide/security-reviewer
- [x] `.claude/settings.json` hooks 配置可运行
  - 证据: hooks 已在 `.claude/settings.json` 配置
- [x] `.audit/` 目录有审计日志输出
  - 证据: `python3 scripts/skills/replay_skill_session.py --latest`

---

## E. Stage E -- 可执行基线 (与 Stage 1 并行)

> 来源: 融合优化 -- 补充可执行基线。
> 定位: 与治理闭环 (Stage 0-4) 并行推进，不阻塞 Stage 1 卡片补齐。
> 原因: 258 张卡中 ~170 条验收命令引用 pytest/pnpm/docker 等工具链，
>        当前仓库无任何包管理配置，验收命令为纸面声明。
> 约束: 必须在 Phase 0 代码实现前完成。
> 详细设计: 见 governance-optimization-plan.md Section 2 (缺口 A/B)。

### E.1 工程骨架 (已落盘)

| 产出 | 路径 | 说明 |
|------|------|------|
| Makefile | `Makefile` | bootstrap / doctor / scaffold / verify 入口 |
| Python 项目配置 | `pyproject.toml` + `uv.lock` | 后端依赖管理 |
| 前端 Monorepo | `pnpm-workspace.yaml` + `turbo.json` | 前端工程结构 |
| 环境模板 | `.env.example` + `.gitignore` + `.editorconfig` | 开发环境标准化 |
| 治理入口 | `CLAUDE.md` (项目级, <= 80 行) | AI Agent 上下文入口 |
| 环境诊断 | `scripts/doctor.py` | `make doctor` 实现 |
| Phase 验收 | `scripts/verify_phase.py` | `make verify-phase-N` 实现 |

### E.1.1 技术决策: Python 依赖管理分层

> ADR-E1: `[dependency-groups]` vs `[project.optional-dependencies]`
> Date: 2026-02-15
> Status: Decided

**决策:** 开发依赖使用 PEP 735 `[dependency-groups]`，可选功能依赖使用 `[project.optional-dependencies]`。

| 类别 | pyproject.toml Section | 安装命令 | 示例 |
|------|----------------------|---------|------|
| 核心运行依赖 | `[project] dependencies` | `uv sync` | fastapi, sqlalchemy, pydantic |
| 开发工具依赖 | `[dependency-groups] dev` | `uv sync --dev` | pytest, ruff, mypy, pip-audit |
| 可选功能依赖 | `[project.optional-dependencies]` | `uv sync --extra vector` | pgvector |

**理由:** `uv sync --dev` 映射到 `[dependency-groups] dev`，而非 `[project.optional-dependencies] dev`。
混用会导致 CI 环境中 dev 工具未安装（`uv sync --dev --frozen` 找不到 dev 组），本地环境因缓存而不暴露问题。

**CI 约束:** 所有 CI job 使用 `uv sync --dev --frozen`，`--frozen` 禁止修改锁文件，`--dev` 安装开发依赖组。

### E.2 里程碑矩阵 YAML (已落盘)

| 产出 | 路径 | 说明 |
|------|------|------|
| 机读矩阵 | `delivery/milestone-matrix.yaml` | Phase 0-5 退出条件 YAML 化 |
| 矩阵 Schema | `delivery/milestone-matrix.schema.yaml` | YAML 校验 Schema |

### E.3 Guard 脚本集 (已落盘)

| 脚本 | 功能 | 来源 |
|------|------|------|
| `scripts/check_layer_deps.sh` | 层间依赖检查 | governance-optimization-plan.md |
| `scripts/check_port_compat.sh` | Port 契约兼容性 | governance-optimization-plan.md |
| `scripts/check_migration.sh` | Migration 安全检查 | governance-optimization-plan.md |
| `scripts/check_rls.sh` | RLS 隔离检查 | governance-optimization-plan.md |
| `scripts/change_impact_router.sh` | 变更影响路由 | governance-optimization-plan.md |
| `scripts/risk_scorer.sh` | 风险评分量化 | governance-optimization-plan.md |

### Stage E 与 Stage 1 的关系

```
并行:
  Stage 1 (卡片补齐) ---不依赖--- Stage E (工程骨架)
  Stage 1 只改 docs/ 下的 markdown 文件
  Stage E 创建工程配置文件

串行约束:
  Stage E 必须在 Phase 0 代码实现前完成
  Stage 2 的 CI workflow 依赖 Stage E 的 .github/ 目录
  Stage 3 的 hooks 依赖 Stage E 的 scripts/ 目录
```

### Stage E 退出条件

- `make bootstrap && make doctor` 可运行
- `make scaffold-phase-0` 生成完整骨架
- `make verify-phase-0 --json` 输出 JSON 证据
- `CLAUDE.md` <= 80 行且可被 Claude Code 加载
- `delivery/milestone-matrix.yaml` 可被 Python yaml 解析

---

## C. Stage C -- 商业交付层

> 来源: 融合优化 -- 补充商业化交付。
> 定位: Stage 2 CI 就位后启动，与 Stage 3 并行或后置。
> 详细设计: 见 governance-optimization-plan.md Section 2 (缺口 D)。

### C.1 证据归档标准 (与 Stage 2.5 协同)

```
evidence/
  phase-0/
    verify-phase-0-{sha}.json
    ci-run-{sha}.json
    audit-session-{ts}.jsonl
  phase-1/
    isolation-test-report-{sha}.html
    rls-evidence-{sha}.json
    migration-drill-{sha}.json
  release/
    v0.1.0/
      all-gates-pass.json
      sbom.json
      perf-baseline.json
      backup-drill.json
      manifest-frozen.yaml
```

### C.2 商业化模板套件

| 产出 | 路径 | 说明 |
|------|------|------|
| SLA 模板 | `delivery/commercial/sla-template.md` | 可用性 / 响应时间 / RPO/RTO |
| 事故复盘模板 | `delivery/commercial/incident-template.md` | 时间线 / 根因 / 措施 |
| 客户验收清单 | `delivery/commercial/sat-checklist.md` | 安装 / 升级 / 隔离 / 审计 |
| 运维手册 | `delivery/commercial/runbook/` | 常见故障 / 升级 / 备份 / 告警 |
| 成本模型 | `delivery/commercial/cost-model.yaml` | 资源基线 / Token 成本 |

### Stage C 退出条件

- `delivery/commercial/` 模板套件就位
- 完成"升级-回滚-恢复-审计取证"全流程演练
- `evidence/release/` 包含完整证据链
- SLA/SAT/Runbook 可交付给种子客户

---

## 4. Stage 4 -- 运行治理 (持续)

### 4.1 Phase Gate Review 流程

每个 Phase gate (Phase 0 -> 1 -> 2 -> 3 -> 4 -> 5) 必须:

1. 运行 `/gate-review`，确认 BLOCK = 0
2. 审查所有活跃 Exception，到期未解决的阻断下一 gate
3. 审查 Section 10 controlled-pending 项，到期裁决落盘
4. 产出审计报告存入 `evidence/phase-N/gate-review-{date}.json`

### 4.2 增量卡管理

- 新增矩阵条目 -> 必须同步创建 task card (CI 强制)
- 关闭矩阵条目 -> task card 标注 `[Closed]` + 保留审计痕迹
- Exception 到期 -> 自动 WARNING (`check_task_schema.py` 可扩展)

### 4.3 Schema 版本演进

| 版本 | 变更 | 状态 |
|------|------|------|
| v1.0 | 初始版本: 双 Tier + 10/8 字段 + Exception + 渐进门禁 | Frozen |
| v1.1 (planned) | Wave 1 反馈后微调 (字段顺序/标签措辞) | Pending |
| v2.0 (planned) | Stage 2 CI 门禁全量启用后的正式版 | Pending |

### 4.4 漂移检测

> 来源: 融合优化 -- 补充漂移检测机制。

| 机制 | 实现 | 阶段 |
|------|------|------|
| PR 级检测 | `.github/workflows/task-card-check.yml` 自动触发 | Stage 2 |
| 矩阵 -> 卡片同步 | `/gate-review` 检查 L2->L3 覆盖率 | Stage 3 |
| 本地快速检测 | pre-commit hook (可选，非阻断) | Stage 4+ |

### 4.5 治理度量

> 来源: 融合优化 -- 补充度量采集。
> 实现方式: `/gate-review` 输出 JSON 追加到 `evidence/`，不单建度量系统。

| 度量 | 来源 | 频率 |
|------|------|------|
| Schema 合规率 | `check_task_schema.py --json` | 每次 PR + 每次 gate |
| Exception 密度 | `/gate-review` 输出 | 每次 gate |
| Phase gate 通过率 | `evidence/phase-N/gate-review-*.json` 累计 | 每次 gate |
| BLOCK 趋势 | CI 历史报告 | 周报 |

### 4.6 治理变更管理

> 来源: 融合优化 -- 治理系统本身的变更需要 ADR。

- Schema 变更 (v1.0 -> v1.1 -> v2.0) 必须经 gate review 审批
- 脚本行为变更必须附 diff 说明
- 治理降级 (放宽规则) 必须记录 ADR + 灰度期 + 回升路径
- 维护规则: 见 `task-card-schema-v1.0.md` 末尾维护声明

---

## 5. 跨阶段关注事项

### 5.1 Section 10 Controlled-Pending (4 项)

| # | 描述 | 截止 | 处置 |
|---|------|------|------|
| A | Web /settings 页无矩阵条目 | Phase 2 gate | Stage 1 不处理，Phase 2 gate 裁决 |
| B | SSE 通知中心 UI 独立条目评估 | Phase 2 gate | 同上 |
| C | Admin Model Registry/Pricing 页 | Phase 3 gate | Stage 1 不处理 |
| D | Admin Plugin/Tool Management 页 | Phase 3 gate | 同上 |

### 5.2 WARNING 目标结果导向 (151 项)

- 非阻断，Stage 1 每波编辑时顺带审查
- 明显非结果导向的微调目标措辞
- 模糊地带保留，交由 Phase gate review 人工裁决

### 5.3 MANUAL-VERIFY 标注 (当前 0 项)

- Stage 1 编辑过程中若发现验收命令确实无法命令化，标注 `[MANUAL-VERIFY]`
- 预期数量: < 10 (大部分已通过前几轮命令化或 ENV-DEP 处理)

### 5.4 L1 -> L2 反向标注 (增强项)

- Stage 1 不包含 L1 架构文档修改
- Stage 3 `/gate-review` 可输出 L1->L2 覆盖率报告
- 后续视需求决定是否在 L1 文档中添加矩阵锚点

### 5.5 Policy-as-Code 演进 (远期)

> 来源: 融合优化 -- Schema 规则从硬编码迁移到数据化。
> 时机: v2.0 Schema 稳定后再投入。

当前 `check_task_schema.py` 将规则硬编码在 Python 中 (557 行)。
v2.0 稳定后可考虑重构为:

```
governance/schema/task-card.schema.yaml   <- 规则数据
governance/policies/tier-a.yaml           <- Tier 特定策略
scripts/validate.py                       <- 通用验证引擎
```

**不在本计划范围内**，记录为后续演进方向。

---

## 6. 执行顺序总览

```
Stage 0 [DONE]
  |
  v
Stage 1 Wave 1 (50 卡, 128 BLOCK) --+--> Stage 2 Step 1 (CI Warning)
  |                                   |
  |                                   +--> Stage E (工程骨架, 并行)
  v                                   |
  [Wave 1 验证 + 脚本微调]            |
  |                                   |
  v                                   |
Stage 1 Wave 2 (64 卡, 170 BLOCK) ---+
  |
  v
Stage 1 Wave 3 (102 卡, 266 BLOCK)
  |
  v
Stage 1 Wave 4 (42 卡, 116 BLOCK)
  |
  v
  [Full BLOCK = 0 验证]
  |
  +--> Stage 2 Step 2 (CI Incremental Block)
  |
  +--> Stage 2 Step 3 (CI Full Block)
  |
  v
Stage 2.5 (证据基建)
  |
  +--> Stage C (商业交付层, 可并行)
  |
  v
Stage 3 (Skill + Command + Agent 扩展 + Hooks)
  |
  v
Stage 4 (持续运行治理)
```

---

## 7. 完成判定 (Definition of Done)

### 输出指标

| # | 检查项 | 目标 | 验证命令 |
|---|--------|------|---------|
| 1 | Schema 校验通过 | 258/258 | `python scripts/check_task_schema.py --mode full` -> PASS |
| 2 | 矩阵映射完整 | 258/258 | `python scripts/count_task_cards.py` -> orphan = 0 |
| 3 | 范围外覆盖 | 258/258 (100%) | 校验报告 `missing_out_of_scope` = 0 |
| 4 | 风险覆盖 (Tier-A) | 211/211 (100%) | 校验报告 `risk-field-required` = 0 |
| 5 | 决策记录 (Tier-A) | 211/211 (100%) | 校验报告 `required-field (决策记录)` = 0 |
| 6 | 非法验收命令 | 0 | 校验报告 `acceptance-not-executable` = 0 |
| 7 | Exception 合规 | 100% | 所有 EXCEPTION 声明含 5 要素 |
| 8 | CI 门禁全绿 | PASS | GitHub Actions `task-card-check` job 通过 |
| 9 | Skill 可执行 | 1 次试运行 | `skill-taskcard-governance` W1-W4 完成 |
| 10 | Gate Review 可生成 | 报告完整 | `/gate-review` 输出 PASS |

### 过程约束

| # | 约束 | 说明 |
|---|------|------|
| 11 | 每波次附机器报告 | `check_task_schema.py` 输出作为审计产物 |
| 12 | Tier-A 修复附领域审查 | 风险/决策内容参考 L1 架构文档，非机械填充 |
| 13 | Schema 变更有 ADR | v1.0 -> v1.1 -> v2.0 每次变更记录决策理由 |
| 14 | CI 可离线复现 | 非 [ENV-DEP] 的校验命令在无网络环境下可重复执行 |
| 15 | 治理有回滚路径 | Schema 降级 (放宽) 有记录的 ADR + 灰度期 |

---

## 8. 实施纪律 (强制)

1. **先冻结再改卡**: Schema v1.0 已 Frozen，未经 gate review 不得修改
2. **两阶段编辑策略**:
   - **阶段 A (每波主操作)**: 仅新增缺失字段 (范围外/风险/决策记录) + `范围` 标签统一
   - **阶段 B (每波 WARNING 审查)**: 允许微调目标措辞以消除明显的非结果导向 WARNING
   - 阶段 B 变更范围: 仅限目标字段，且仅限"明显非结果导向"项 (如"编写代码实现..." -> "...可用/通过/...")
   - 模糊地带 (无法确定是否结果导向): 保留原文，交由 Phase gate review 人工裁决
   - 每波的阶段 A 和阶段 B 在校验报告中分别记录变更数
3. **每波附机器报告**: 波次完成后运行 `check_task_schema.py`，报告作为审计产物
4. **未通过不合并**: CI Full Block 启用后，BLOCK > 0 不得合并
5. **渐进不跳级**: Wave 顺序执行，不跳波；CI 阶段顺序推进，不跳步
6. **并行不交叉**: Stage E / Stage C 与 Stage 1 并行但文件边界不重叠

---

## 9. 文档引用关系

```
本计划引用 (READ):
  docs/governance/task-card-schema-v1.0.md        <- Schema 标准 (Frozen)
  docs/governance/governance-optimization-plan.md  <- 缺口 A/B/C/D 详细设计
  docs/governance/milestone-matrix.md              <- 矩阵总览
  docs/governance/milestone-matrix-backend.md      <- 后端矩阵
  docs/governance/milestone-matrix-frontend.md     <- 前端矩阵
  docs/governance/milestone-matrix-crosscutting.md <- 横切矩阵
  scripts/check_task_schema.py                     <- 校验脚本
  scripts/count_task_cards.py                      <- 计数脚本

本计划产出 (WRITE -- 后续阶段):
  .github/workflows/task-card-check.yml            <- Stage 2
  evidence/                                        <- Stage 2.5
  .claude/skills/taskcard-governance/SKILL.md       <- Stage 3
  .claude/commands/gate-review.md                   <- Stage 3
  .claude/settings.json                             <- Stage 3
  scripts/hooks/pre_edit_audit.sh                   <- Stage 3
  scripts/hooks/pre_commit_gate.sh                  <- Stage 3
  scripts/hooks/post_edit_format.sh                 <- Stage 3
  Makefile                                          <- Stage E
  pyproject.toml / pnpm-workspace.yaml              <- Stage E
  CLAUDE.md                                         <- Stage E
  delivery/                                         <- Stage C

本计划已同步修正 (SYNC -- 口径对齐 dual-Tier Schema):
  docs/governance/milestone-matrix.md
    - line 49: "7 字段说明" -> 明确为"矩阵层"，增加任务卡双 Tier 注释
    - line 123: 补充 "矩阵层 7 字段格式" 限定词
    - line 163: 任务卡侧从 "7 字段" 改为 "双 Tier: Tier-A 10 / Tier-B 8"
    - line 360: 从 "7 必填字段" 改为 "双 Tier Schema" + 引用 schema 文档
  docs/governance/milestone-matrix-backend.md
    - line 9: 从 "7 字段格式" 改为 "矩阵层 7 字段格式" + 补任务卡双 Tier 说明
  docs/governance/milestone-matrix-frontend.md
    - line 9: 同上
  docs/governance/milestone-matrix-crosscutting.md
    - line 9: 同上
  docs/governance/governance-optimization-plan.md
    - line 1051: Wave 1 从 "~35 卡" 修正为 "50 卡"
    - line 1052: Wave 2-4 从 "~220 卡" 修正为 "208 卡"

不修改 (PRESERVE):
  docs/architecture/*.md (v3.6)
  docs/frontend/*.md
  docs/governance/task-card-schema-v1.0.md (Frozen)
```

---

## 10. Controlled-Pending 决策追踪

> 来源: 任务卡交叉审查 (2026-02-13)
> 规则: 每项必须有 决策/Owner/截止，禁止 TBD owner
> 状态: 4 项均为受控未决，将在对应 Phase gate review 裁决落盘

| # | 架构来源 | 缺口描述 | 决策 | Owner | 截止 |
|---|---------|---------|------|-------|------|
| A | FE-05 Section 3 | Web App `/settings` 页无矩阵条目 | 待评审: 是否归入现有 FW 条目子实现 | Faye | Phase 2 gate review |
| B | FE-02 Section 2 | SSE 通知中心 UI 无矩阵条目 | 待评审: 后端 G2-7 已补充，前端消费方 FW2-9 已补充，评估是否需独立通知中心 UI 条目 | Faye | Phase 2 gate review |
| C | FE-06 | Admin Model Registry / Model Pricing 页面无矩阵条目 | 待评审: 是否新增 FA 条目 | Faye | Phase 3 gate review |
| D | FE-06 | Admin Plugin/Tool Management 无矩阵条目 | 待评审: 是否新增 FA 条目 | Faye | Phase 3 gate review |

---

> **维护规则**: 本文件变更必须经 gate review 审批。
> 版本修订记录附在文件末尾。
>
> **版本历史:**
> - v1.0 (2026-02-13): 初始版本，融合任务卡治理计划 + 优化分析产出
> - v1.0.1 (2026-02-13): 修正 5 项 review findings:
>   - HIGH-1: milestone-matrix 4 文件共 7 处旧口径 (7 字段) 修正为矩阵层/任务卡层分离描述
>   - HIGH-2: governance-optimization-plan.md Wave 工作量从 ~35/~220 修正为 50/208
>   - MEDIUM-1: 实施纪律从"只补字段"改为两阶段策略 (A: 补字段 + B: 微调 WARNING 目标)
>   - MEDIUM-2: Section 9 新增 SYNC 修改记录，显式列出已同步的 7 处口径修正
>   - LOW-1: 基线文件行数修正 (557->556, 360->359) + 锁定 sha256 hash
