# DIYU Agent 治理模块优化补全计划 v2.0

> version: v2.0
> date: 2026-02-13
> status: Discussion Baseline (v2)
> supersedes: v1.0-merged-baseline
> inputs: 治理规范 v1.1 + 架构文档 v3.6 + Anthropic 2026 Agentic Engineering Best Practices
> scope: 从规范文档到可执行工程的全链路治理落地
> core thesis: 不再加原则，而是补齐 4 个执行缺口

---

## 0. 治理六层模型

```
L1  Architecture SSOT (v3.6)              -- WHAT: 系统是什么样
    |
L2  Milestone Matrix (NEW)               -- WHEN+WHAT: 每层每阶段交付什么
    |                                        机器可判定 (YAML + CI 聚合)
L3  Governance Spec (v1.1 -> v1.2)        -- HOW: 质量规则 + 审查流程
    |                                        + Agentic Engineering 治理
L4  Policy-as-Code                        -- ENFORCE(hard): 红线与关键门禁
    |                                        AST/OPA/Conftest 可执行策略
L5  CI/CD Evidence                        -- ENFORCE(auto): 5-tier 验证格栅
    |                                        + 风险评分路由 + 证据归档
L6  Commercial Ops                        -- DELIVER: SLA/Runbook/Incident/
                                             SAT/成本仪表盘
```

v1.0 是 5 层。v2.0 拆分出 L4 Policy-as-Code（markdown 规则 vs 可执行策略是不同的东西）和 L6 Commercial Ops（To B 产品不可缺）。

---

## 1. 现状评估

### 1.1 已充分覆盖（有文档行号证据）

| # | 能力 | 证据位置 |
|---|------|---------|
| 1 | 三 SSOT 治理体系 | 治理规范.v1.1-正文.md:17 |
| 2 | CI 三层门禁 | 治理规范.v1.1-正文.md:105 |
| 3 | 风险分层测试覆盖率 | 治理规范.v1.1-正文.md:179 |
| 4 | 例外治理与红线 | 治理规范.v1.1-正文.md:238 |
| 5 | Phase 验收命令体系 | 治理规范.v1.1-Vibe执行附录.md:165 |
| 6 | AI guard/pattern/workflow 结构 | 治理规范.v1.1-Vibe执行附录.md:60 |
| 7 | 新手执行顺序 | 治理规范.v1.1-Vibe执行附录.md:269 |
| 8 | 架构 ADR 索引完整语义源 | 08-附录.md:53 |
| 9 | 代码审查矩阵 + SLA 升级 | 治理规范.v1.1-正文.md:158 |
| 10 | Migration 纪律 | 治理规范.v1.1-正文.md:198 |
| 11 | 失败恢复基线 | 治理规范.v1.1-正文.md:205 |
| 12 | 数据生命周期治理 | 治理规范.v1.1-正文.md:214 |
| 13 | 可观测性阶梯 | 治理规范.v1.1-正文.md:224 |
| 14 | 交付 SSOT manifest | 治理规范.v1.1-正文.md:232 |
| 15 | 脚手架命令 + 最小输出定义 | 治理规范.v1.1-Vibe执行附录.md:76 |
| 16 | 契约测试四层策略 | 00-系统定位与架构总览.md:666 |
| 17 | Port 演进策略 | 00-系统定位与架构总览.md:622 |
| 18 | 开发十诫 + DoD | 治理规范.v1.1-正文.md:271 |
| 19 | 分支策略 + 版本策略 | 治理规范.v1.1-正文.md:77 |
| 20 | 红线后果说明 | 治理规范.v1.1-Vibe执行附录.md:244 |

**结论**: 原则层（L1/L3）充分。缺口集中在执行层（L2/L4/L5/L6）。

### 1.2 还没真正落地的关键缺口（10 项）

| # | 缺口 | 对应层 | 说明 |
|---|------|-------|------|
| 1 | 仓库仅有 docs/，无可执行工程骨架 | L5 | Phase 0 停留在规范层 |
| 2 | 缺少 Layer x Phase 机器可读矩阵 | L2 | 无法自动计算 Go/No-Go |
| 3 | 缺少项目 CLAUDE.md + 分层加载硬实现 | L3/L5 | AI 治理无入口 |
| 4 | 缺少 hooks 真正执行 | L5 | PreToolUse/Stop 未配置 |
| 5 | 缺少风险评分公式与自动路由 | L5 | 目前仅标签路由 |
| 6 | 缺少 Agent 行为审计日志 | L5 | tool calls/决策轨迹/上下文使用率无记录 |
| 7 | 缺少 Policy-as-Code | L4 | markdown 规则无法强校验 |
| 8 | 缺少商业化必需包 | L6 | SLA/值班/事故复盘/客户验收/成本 |
| 9 | 缺少新手一键命令体系 | L5 | bootstrap/doctor/preflight/verify-json |
| 10 | 缺少质量证据归档标准 | L5/L6 | 发布时无法做客户审计证明 |

---

## 2. 四大执行缺口补全方案

> v2.0 核心变更：将 v1.0 的 Tier 1-4 重构为"4 个执行缺口 + 30-60-90 路线"。
> 原则性内容（Agent 权限分级、前端治理深化等）保留为 v1.2 增量 Section，
> 但不再作为独立执行单元，而是嵌入到 4 个执行缺口的落盘实现中。

### 缺口 A: Golden Path -- 从文档到仓库的一键启动

**问题**: 仓库只有 `docs/`，`make verify-phase-0` 跑不起来因为没有 Makefile。

**方案**: 建立 4 命令生命周期:

```
make bootstrap     环境准备（安装工具链 + 依赖 + 预检）
make doctor        诊断开发环境健康（Python/Node/Docker/PG 版本 + 端口可用性）
make scaffold-*    生成骨架（按模块/按 Phase）
make verify-*      验收（输出 JSON 证据）
```

#### bootstrap 命令

```makefile
bootstrap:
    @echo "=== DIYU Agent Bootstrap ==="
    # 1. 工具链检查
    command -v python3.12 || (echo "NEED: Python 3.12+"; exit 1)
    command -v uv         || (echo "NEED: uv"; exit 1)
    command -v node       || (echo "NEED: Node.js 22 LTS"; exit 1)
    command -v pnpm       || (echo "NEED: pnpm"; exit 1)
    command -v docker     || (echo "NEED: Docker 24+"; exit 1)
    # 2. 后端依赖
    uv sync
    # 3. 前端依赖
    cd frontend && pnpm install
    # 4. 环境配置
    cp -n .env.example .env || true
    # 5. 验证
    $(MAKE) doctor
```

#### doctor 命令

```makefile
doctor:
    @python3 scripts/doctor.py
    # 输出:
    # [OK] Python 3.12.4
    # [OK] uv 0.5.x
    # [OK] Node.js 22.x
    # [OK] pnpm 9.x
    # [OK] Docker 24.x
    # [OK] Docker Compose 2.x
    # [WARN] PostgreSQL not running (needed for Phase 1+)
    # [WARN] Redis not running (needed for Phase 1+)
    # Summary: 5 OK, 2 WARN, 0 FAIL
```

#### scaffold-phase-0 命令（完整文件清单）

```
make scaffold-phase-0 生成:

工程基础:
  pyproject.toml              # Python 项目配置 + ruff + mypy
  uv.lock                     # 依赖锁定
  Makefile                    # 所有 make 命令入口
  .env.example                # 环境变量模板（无真实密钥）
  .gitignore                  # Python + Node + IDE
  .editorconfig               # 编辑器统一配置

后端骨架:
  src/__init__.py
  src/ports/                  # Day 1 Port 接口定义
    __init__.py
    memory_core_port.py       # MemoryCorePort (空壳 + 类型签名)
    knowledge_port.py         # KnowledgePort
    llm_call_port.py          # LLMCallPort
    skill_registry.py         # SkillRegistry
    org_context.py            # OrgContext
    storage_port.py           # StoragePort
  src/shared/
    types/__init__.py         # OrganizationContext, MemoryItem 等
    errors/__init__.py        # 统一异常体系
  tests/
    unit/__init__.py
    isolation/
      smoke/__init__.py
    conftest.py               # pytest 配置 + 基础 fixture
  migrations/
    env.py                    # Alembic 配置
    script.py.mako

前端骨架:
  frontend/
    pnpm-workspace.yaml
    turbo.json
    package.json
    apps/web/                 # Next.js 用户端
    apps/admin/               # Next.js 管理端
    packages/ui/              # 共享 UI 组件
    packages/api-client/      # API 客户端（OpenAPI 生成）
    packages/shared/          # 共享类型/工具

Guard 脚本:
  scripts/
    check_layer_deps.sh       # 层间依赖检查
    check_port_compat.sh      # Port 契约兼容性
    check_migration.sh        # Migration 安全检查
    check_rls.sh              # RLS 隔离检查
    change_impact_router.sh   # 变更影响路由 (reviewer + CI gate 双路由) [UPGRADED]
    risk_scorer.sh            # 风险评分 (v2: 量化) [NEW]
    doctor.py                 # 开发环境诊断 [NEW]
    verify_phase.py           # Phase 验收 + JSON 输出 [NEW]

CI/CD:
  .github/
    workflows/ci.yml          # 4 层门禁 (PR硬/影响/阶段/发版)
    PULL_REQUEST_TEMPLATE.md  # PR 模板
    CODEOWNERS                # 按层路由

交付:
  delivery/
    manifest.yaml             # 交付 SSOT 骨架
    milestone-matrix.schema.yaml  # Schema 校验 (renamed from manifest.schema.yaml)
    milestone-matrix.yaml     # 里程碑矩阵 (机读) [NEW]
    preflight.sh              # 安装前置检查

治理:
  docs/
    governance/
      milestone-matrix.md     # 里程碑矩阵 (人读) [NEW]
    adr/
      README.md               # ADR 索引
      _template.md            # ADR 模板

AI Agent Context:
  CLAUDE.md                   # 项目治理入口 (<= 80 行) [NEW]
  .claude/
    settings.json             # hooks 配置 [NEW]
  .claude/skills/             # AI Agent Skills (迁移自 .agent/workflows/, ADR-053)
    taskcard-governance/      # Task card governance skill
```

---

### 缺口 B: 里程碑矩阵的机器可判定版本

**问题**: Phase 划分只有叙事性描述，无法自动计算 Go/No-Go。

**方案**: YAML 定义 + JSON 验收报告 + CI 聚合

#### milestone-matrix.yaml 结构

```yaml
schema_version: "1.0"
phases:
  phase_0:
    name: "治理最小集 + 交付骨架"
    exit_criteria:
      hard:  # 全部必须 PASS 才能进入 Phase 1
        - id: "p0-toolchain"
          check: "make doctor --json | jq '.fail_count == 0'"
        - id: "p0-backend-skeleton"
          check: "test -f src/ports/memory_core_port.py"
        - id: "p0-frontend-skeleton"
          check: "test -f frontend/pnpm-workspace.yaml"
        - id: "p0-guards"
          check: "bash scripts/check_layer_deps.sh --dry-run"
        - id: "p0-ci"
          check: "test -f .github/workflows/ci.yml"
        - id: "p0-manifest"
          check: "python3 -c 'import yaml; yaml.safe_load(open(\"delivery/manifest.yaml\"))'"
        - id: "p0-claude-md"
          check: "test -f CLAUDE.md && wc -l < CLAUDE.md | xargs test 80 -ge"
        - id: "p0-skills"
          check: "ls .claude/skills/*/SKILL.md | wc -l | xargs test 1 -le"
        - id: "p0-milestone-matrix"
          check: "python3 -c 'import yaml; yaml.safe_load(open(\"delivery/milestone-matrix.yaml\"))'"
        - id: "p0-adr-index"
          check: "test -f docs/adr/README.md"
      soft:  # 应完成，不阻断
        - id: "p0-hooks"
          check: "test -f .claude/settings.json"
    go_no_go:
      hard_pass_rate: 1.0       # 100% hard 必须通过
      approver: "architect"     # GitHub Issue 签字

  phase_1:
    name: "安全与租户底座"
    depends_on: ["phase_0"]
    milestones:
      - layer: "infrastructure"
        deliverable: "organizations + users + org_members DDL"
        acceptance:
          - "migrations/ 含 organization 相关迁移"
          - "upgrade + downgrade 测试存在"
        risk_level: "critical"
      - layer: "security"
        deliverable: "OrgContext 全链路 + RLS 策略基线"
        acceptance:
          - "tests/isolation/ 核心用例 PASS"
          - "pytest tests/isolation/smoke/ 在 CI 中运行"
        risk_level: "critical"
      - layer: "brain_memory"
        deliverable: "Port 接口定义（签名 + 契约类型已定）"
        acceptance:
          - "Layer 1 Port Schema 断言测试 PASS"
          - "MemoryItem Schema v1 snapshot 存在"
        risk_level: "high"
      - layer: "gateway"
        deliverable: "认证中间件 + OrgContext 注入"
        acceptance:
          - "JWT 验证 + org_context 解析测试 PASS"
        risk_level: "high"
      - layer: "observability"
        deliverable: "统一日志格式 (trace_id + org_id + request_id)"
        acceptance:
          - "日志格式检查脚本存在"
        risk_level: "medium"
    exit_criteria:
      hard:
        - id: "p1-org-migration"
          check: "alembic heads | grep -q organization"
        - id: "p1-rls"
          check: "pytest tests/isolation/smoke/ --tb=short"
        - id: "p1-orgcontext"
          check: "pytest tests/unit/gateway/test_org_context.py"
        - id: "p1-audit"
          check: "test -f migrations/versions/*audit_events*"
        - id: "p1-port-contracts"
          check: "pytest tests/unit/ports/"
      soft:
        - id: "p1-sbom"
          check: "test -f delivery/sbom.json"
    go_no_go:
      hard_pass_rate: 1.0
      approver: "architect"

  # phase_2 ~ phase_5: 同结构，详见完整 YAML
```

#### verify-phase-N JSON 输出

```json
{
  "phase": "phase_0",
  "timestamp": "2026-02-13T10:30:00Z",
  "results": {
    "hard": [
      {"id": "p0-toolchain", "status": "PASS", "duration_ms": 1200},
      {"id": "p0-backend-skeleton", "status": "PASS", "duration_ms": 5},
      {"id": "p0-ci", "status": "FAIL", "error": "ci.yml not found"}
    ],
    "soft": [
      {"id": "p0-hooks", "status": "SKIP", "reason": "settings.json not found"}
    ]
  },
  "summary": {
    "hard_total": 10, "hard_pass": 9, "hard_fail": 1,
    "soft_total": 1, "soft_pass": 0, "soft_skip": 1,
    "pass_rate": 0.90,
    "go_no_go": "BLOCKED",
    "blocking_items": ["p0-ci"]
  }
}
```

#### CI 聚合

```yaml
# .github/workflows/milestone-check.yml
name: Milestone Progress
on:
  push: { branches: [main] }
  schedule: [{ cron: '0 8 * * 1' }]   # 每周一 08:00
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make verify-phase-current --json > evidence/milestone-report.json
      - run: python3 scripts/milestone_aggregator.py
      # 输出: Phase 0 进度 9/10 (90%), 阻断项: ci.yml
      - uses: actions/upload-artifact@v4
        with:
          name: milestone-evidence-${{ github.sha }}
          path: evidence/
```

#### 影响门禁路由逻辑（change_impact_router 双路由）

> 对齐治理规范 v1.1 Section 5.2。change_impact_router.sh 不仅路由 reviewer，还路由 CI 检查项。

```
输入: git diff --name-only origin/main...HEAD
输出:
  1. triggered_gates[]     -- 需要执行的 CI 检查项列表
  2. required_reviewers[]  -- 需要的 reviewer 角色列表

路径匹配规则 (优先级从高到低):

  docs/** | *.md           -> gates: []                    reviewers: [docs-owner]
  src/ports/**             -> gates: [check_port_compat]   reviewers: [architect]
  migrations/**            -> gates: [check_migration]     reviewers: [architect, data-safety]
  src/infra/org/**         -> gates: [isolation_smoke]     reviewers: [security-lead]
  src/**                   -> gates: [check_layer_deps]    reviewers: [same-layer-dev]
  frontend/**              -> gates: [fe_lint, fe_test]    reviewers: [fe-lead]
  frontend/packages/api-client/** -> gates: [fe_lint, fe_test, contract_test]
  openapi.yaml | openapi/** -> gates: [openapi_sync]      reviewers: [fe-lead, api-owner]
  delivery/**              -> gates: []                    reviewers: [devops]
  .github/**               -> gates: []                    reviewers: [devops]

阶段过滤:
  current_phase = yaml.safe_load('delivery/milestone-matrix.yaml')['current_phase']
  对每个 gate，检查其 activation_phase <= current_phase，否则跳过

输出格式 (JSON):
  {
    "changed_paths": ["src/ports/memory_core_port.py", "tests/unit/ports/test_memory.py"],
    "triggered_gates": ["check_port_compat"],
    "skipped_gates": [{"gate": "openapi_sync", "reason": "phase 0 < activation phase 2"}],
    "required_reviewers": ["architect"],
    "risk_score": 4   // 来自 risk_scorer.sh
  }
```

---

### 缺口 C: Agent 开发治理的可观测、审计与强制执行

**问题**: Agent 权限分级、会话治理写了规则，但没有实际可观测手段和代码级强制执行。

**方案**: hooks 驱动的审计 + 代码级门禁 + /full-audit 统一入口（不自建基础设施）

#### 实现原理

```
Claude Code hooks ----> JSON 日志 ----> verify 聚合 ----> CI 报告
   (已有机制)        (.audit/ 目录)    (scripts/)     (evidence/)
```

#### hooks 配置 (.claude/settings.json)

> **matcher 语法说明**: matcher 是正则表达式，匹配**工具名**（如 `Bash`、`Edit`、`Write`）。
> 用 `|` 分隔多个工具名，用 `.*` 通配，用 `*` 匹配所有工具。
> 命令级过滤（如只拦截 `git commit`）需在 hook 脚本内通过 stdin JSON 的
> `tool_input.command` 字段判断，而非写在 matcher 中。
> 每个 hook 条目必须包含 `hooks` 数组（含 `type` + `command`/`prompt`），
> 不支持顶层 `"command"` 或 `"blocking"` 字段。
> 阻断行为通过 hook 脚本的退出码控制：`exit 2` = 阻断，`exit 0` = 放行。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash scripts/hooks/pre_edit_audit.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash scripts/hooks/pre_commit_gate.sh",
            "timeout": 120
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash scripts/hooks/post_edit_format.sh"
          }
        ]
      }
    ]
  }
}
```

> **Note**: `permissions` (allow/deny 规则) 配置在 `~/.claude.json` 或项目
> `.claude/settings.json` 的 `permissions` 顶层键中，与 `hooks` 同级但独立管理。
> 详见 [Claude Code Hooks 文档](https://docs.anthropic.com/en/docs/claude-code/hooks)。

#### 审计日志格式 (.audit/session-{timestamp}.jsonl)

```jsonl
{"ts":"2026-02-13T10:30:01Z","tool":"Edit","file":"src/brain/engine.py","layer":"brain","tier":2,"guard_triggered":null}
{"ts":"2026-02-13T10:30:05Z","tool":"Edit","file":"src/ports/memory_core_port.py","layer":"ports","tier":4,"guard_triggered":"port-contract-guard"}
{"ts":"2026-02-13T10:31:00Z","tool":"Bash","cmd":"git commit","blocked":true,"reason":"test-smoke failed"}
```

#### 审计聚合命令

```makefile
audit-report:
    @python3 scripts/audit_aggregator.py .audit/
    # 输出:
    # Session: 2026-02-13T10:30
    # Tool calls: 47 (Edit: 32, Bash: 12, Read: 3)
    # Layer distribution: brain 40%, gateway 25%, ports 20%, infra 15%
    # Permission tier: T0=3, T1=5, T2=30, T3=2, T4=0
    # Guard triggers: 3 (layer-dep: 1, port-contract: 2)
    # Blocks: 1 (test-smoke failure)
    # Context window usage: 68% peak
```

#### Agent 权限分级（通过 hooks + 代码级门禁实现）

```
Tier 检测逻辑 (scripts/hooks/pre_edit_audit.sh):

  hook 通过 stdin 接收 JSON，从 tool_input.file_path 提取文件路径，
  按路径匹配 Tier 级别，将审计记录写入 .audit/ 目录。

  文件路径匹配:
    tests/**           -> Tier 1 (log only, exit 0)
    docs/**            -> Tier 1 (log only, exit 0)
    src/shared/**      -> Tier 2 (log + guard check, exit 0)
    src/brain/**       -> Tier 2 (log + guard check, exit 0)
    src/ports/**       -> Tier 4 (log + guard check + WARN to stderr, exit 0)
    migrations/**      -> Tier 3 (log + WARN "needs human review", exit 0)
    src/infra/org/**   -> Tier 4 (log + WARN "security sensitive", exit 0)
    .github/**         -> Tier 3 (log + WARN, exit 0)
    delivery/**        -> Tier 3 (log + WARN, exit 0)

  阻断策略采用分阶段渐进执行 (per H7 audit fix):
    Tier 1 (tests/docs): exit 0 (log only)
    Tier 2 (src/shared, src/brain): exit 0 (log + guard check)
    Tier 3 (migrations, .github, delivery): exit 0 (log + WARN)
    Tier 4 (src/ports, src/infra/org): 按 Phase 条件阻断:
      - src/infra/org/*: Phase 1+ -> exit 2 BLOCK, Phase 0 -> WARN only
      - src/ports/*:     Phase 2+ -> exit 2 BLOCK, Phase 0-1 -> WARN only
      - delivery/manifest*: Phase 3+ -> exit 2 BLOCK, Phase 0-2 -> WARN only

  WARN 通过 stderr 输出提示信息，Claude 会将 stderr 内容作为上下文感知。
  额外阻断点在 commit 阶段: pre_commit_gate.sh 检测到 tool_input.command
  匹配 "git commit" 时执行 make lint && make test-smoke，失败则 exit 2 阻断。
```

---

### 缺口 D: 商业化交付模板落盘

**问题**: To B 产品缺少 SLA/合规/运维/成本 交付套件。

**方案**: 分阶落盘，证据归档从 Day 1 开始

#### 证据归档标准（Day 1 开始）

```
evidence/
  phase-0/
    verify-phase-0-{sha}.json       # Phase 验收报告
    ci-run-{sha}.json               # CI 运行结果
    audit-session-{ts}.jsonl        # Agent 审计日志
  phase-1/
    isolation-test-report-{sha}.html  # 隔离测试报告
    rls-evidence-{sha}.json           # RLS 测试证据
    migration-drill-{sha}.json        # Migration 演练记录
  release/
    v0.1.0/
      all-gates-pass.json            # 全门禁通过证据
      sbom.json                      # 软件物料清单
      perf-baseline.json             # 性能基线
      backup-drill.json              # 备份恢复演练
      manifest-frozen.yaml           # 冻结的交付清单
```

**规则**: CI 产出的每个报告自动归档到 `evidence/`。发布时 `evidence/release/vX.Y.Z/` 必须包含完整证据链。

#### 商业化模板套件（Day 61-90）

```
delivery/commercial/
  sla-template.md               # SLA 模板
    - 可用性目标: 99.9% (月度)
    - 响应时间: P0 < 30min, P1 < 2h, P2 < 8h, P3 < next release
    - RPO/RTO: 基于 delivery/manifest.yaml 中定义
    - 补偿条款框架

  incident-template.md          # 事故复盘模板
    - 时间线
    - 影响范围 (用户/数据/服务)
    - 根因分析 (5 Whys)
    - 修复措施
    - 预防措施
    - 告警改进

  sat-checklist.md              # 客户验收清单 (SAT)
    - 安装时长验证
    - 升级回滚验证
    - 隔离证明 (tests/isolation 全量 PASS 报告)
    - 审计证明 (全链路 trace_id 追溯)
    - 备份恢复证明
    - 性能基线验证

  runbook/                      # 运维手册
    common-issues.md            # 常见故障处理
    upgrade-procedure.md        # 升级步骤
    backup-restore.md           # 备份恢复步骤
    alert-playbook.md           # 告警处置手册

  cost-model.yaml               # 成本模型
    - 资源消耗基线 (CPU/Memory/Storage/Token)
    - 按租户规模的资源估算公式
    - LLM Token 成本计量与预算模型
```

---

## 3. 30-60-90 执行路线

### Day 1-30: Golden Path + 里程碑矩阵

> 退出标准: `make verify-phase-0 --json` 全绿，且输出 JSON 证据。

```
Week 1:
  [x] make bootstrap 可运行（工具链检查 + 依赖安装）
  [x] make doctor 可运行（环境诊断 JSON 输出）
  [x] make scaffold-phase-0 生成全量骨架
  [x] CLAUDE.md 落盘（<= 80 行）
  [x] .claude/settings.json hooks 配置

Week 2:
  [x] 6 个 Port 接口空壳 + 类型签名
  [x] 6 个 guard 脚本可执行（--dry-run 模式）
  [x] delivery/milestone-matrix.yaml (Phase 0-2 详细)
  [x] docs/governance/milestone-matrix.md (人读版)
  [x] docs/adr/README.md 索引 + _template.md

Week 3:
  [x] .github/workflows/ci.yml (L1 Deterministic + L3 Security)
  [x] .claude/skills/ (至少 4 个核心 pattern) -- 4 pattern: taskcard-governance, systematic-review, cross-reference-audit, adversarial-fix-verification
  [x] .claude/skills/ guards (至少 4 个核心 guard) -- 4 guard: guard-layer-boundary, guard-port-compat, guard-migration-safety, guard-taskcard-schema
  [x] make verify-phase-0 --json 可运行
  [x] evidence/ 目录结构 + CI 证据自动归档 (2026-02-15: verify_phase.py --archive + CI upload-artifact)

Week 4:
  [x] make verify-phase-0 全绿 (2026-02-14: hard 10/10, soft 2/2)
  [x] 所有 scaffold-* 命令可运行（生成空壳）
  [x] 治理规范 v1.2 增量草案完成
  [x] make scaffold-adr 可用
  [x] Go/No-Go: Phase 0 验收 -> 进入 Phase 1 (2026-02-14: GO)
```

### Day 31-60: 安全底座 + CI 完整 + Agent 审计

> 退出标准: RLS 隔离测试全绿 + 风险评分自动路由可复现 + Agent 审计日志可查。

```
Week 5-6:
  [ ] organizations + users + org_members DDL + Migration
  [ ] OrgContext 全链路 (JWT -> 中间件 -> Context -> RLS)
  [ ] RLS 策略基线 + tests/isolation/ 核心用例
  [ ] 审计日志最小集 (audit_events)
  [x] hooks 审计日志输出 (.audit/*.jsonl)

Week 7-8:
  [x] CI 升级: L2 Semantic (契约测试 + isolation smoke) (2026-02-15: ci.yml 独立 semantic-checks job)
  [x] scripts/risk_scorer.sh 实现 (4 维量化评分)
  [x] PR 模板含 risk_score/triggered_gates/证据命令块 (2026-02-15: PULL_REQUEST_TEMPLATE.md 更新)
  [x] CODEOWNERS 按层 + 按风险路由
  [x] make audit-report 可运行 (2026-02-14: 已实现)
  [x] make verify-phase-1 全绿 (2026-02-14: hard 5/5)
  [ ] Go/No-Go: Phase 1 验收 -> 进入 Phase 2
```

### Day 61-90: 商业化交付 + 运营治理

> 退出标准: 完成一次"升级-回滚-恢复-审计取证"全流程演练。

```
Week 9-10:
  [ ] SLA 模板框架（基于 Phase 2 真实数据填值）
  [ ] 事故复盘模板
  [ ] 值班升级流程: L1 自动诊断 -> L2 运维 -> L3 研发
  [ ] 告警分级: P0/P1/P2/P3

Week 11-12:
  [ ] SAT 套件（客户验收清单 + 证据包）
  [ ] Runbook 初版（常见故障 + 升级 + 备份恢复）
  [ ] 成本模型 v1（资源基线 + Token 成本）
  [ ] 执行"升级-回滚-恢复-审计取证"演练
  [ ] evidence/release/ 完整证据链
```

---

## 4. 原则性内容去向

v1.0 中的原则性内容不丢弃，嵌入到治理规范 v1.2 增量 Section:

| 原 v1.0 位置 | v2.0 去向 | 落地方式 |
|-------------|----------|---------|
| 2.2 Verification Lattice | v1.2 Section 5 升级 | CI Pipeline 实现 (缺口 B) |
| 2.3 Risk Scoring | v1.2 Section 6 增量 | risk_scorer.sh (缺口 B) |
| 2.4 Agent Permission Tiers | v1.2 新增 Section 18 | hooks 实现 (缺口 C) |
| 2.5 Agent Session & Audit | v1.2 新增 Section 18 | hooks + 审计日志 (缺口 C) |
| 2.6 Frontend Governance | v1.2 新增 Section 20 | CI 门禁 (Day 31-60) |
| 4.1 Eval-Driven Dev | v1.2 迭代入口 Section | Day 90+ 路线图 |
| 4.2 Policy-as-Code | L4 层落地 | Day 90+ 渐进迁移 |
| 4.3 CE Quality Gates | v1.2 迭代入口 Section | Phase 2+ |
| 4.4 Multi-Agent Protocol | v1.2 迭代入口 Section | Phase 2+ |
| 4.5 SLO 治理流程 | v1.2 新增 Section 21 | Day 61-90 (缺口 D) |
| 4.6 知识管理治理 | v1.2 新增 Section 22 | Phase 3 |

---

## 5. 与现有文档的关系

```
本计划产出 (NEW):
  docs/governance/governance-optimization-plan.md  <- 本文件
  docs/governance/milestone-matrix.md              <- 缺口 B (人读)
  delivery/milestone-matrix.yaml                   <- 缺口 B (机读)
  docs/adr/README.md + _template.md                <- ADR 索引
  CLAUDE.md                                        <- 缺口 A
  .claude/settings.json                            <- 缺口 C (hooks)
  evidence/                                        <- 缺口 D (证据归档)
  delivery/commercial/                             <- 缺口 D (商业模板)
  scripts/doctor.py                                <- 缺口 A
  scripts/verify_phase.py                          <- 缺口 A
  scripts/risk_scorer.sh                           <- 缺口 B
  scripts/audit_aggregator.py                      <- 缺口 C
  scripts/hooks/pre_edit_audit.sh                  <- 缺口 C
  scripts/hooks/pre_commit_gate.sh                 <- 缺口 C (commit 门禁, 含结构化审计日志)
  scripts/hooks/post_edit_schema_check.sh          <- 缺口 C (原 post_edit_format.sh, 重命名 per GAP-M11)
  scripts/hooks/user_prompt_guard.sh               <- 缺口 C (密钥泄露检测, 超额交付)
  scripts/hooks/post_tool_failure_log.sh           <- 缺口 C (工具失败日志, 超额交付)

本计划修改 (AMEND):
  docs/reviews/治理规范.v1.1-正文.md -> v1.2 增量:
    Section 5: 3-tier -> 5-tier Verification Lattice
    Section 6: 增加风险评分路由
    Section 18 (NEW): Agentic Engineering 治理 (权限/会话/审计)
    Section 19 (NEW): CLAUDE.md & Context Engineering 治理
    Section 20 (NEW): 前端治理深化
    Section 21 (NEW): SLO 治理与事件管理
    Section 22 (NEW): 知识管理治理

  docs/reviews/治理规范.v1.1-Vibe执行附录.md -> v1.2 增量:
    Section 1: 增加 CLAUDE.md + hooks + 里程碑矩阵 + evidence/
    Section 5: verify-phase-0 增加新检查项 + JSON 输出
    Section 9 (NEW): Agent 权限分级与审计实现
    Section 10 (NEW): 一键命令体系 (bootstrap/doctor/scaffold/verify)

不修改 (PRESERVE):
  docs/architecture/*.md (v3.6)
  docs/frontend/*.md
  docs/reviews/治理规范.md (v1.0 历史稿)
```

---

## 6. 成功标准

```
Day 30 退出:
  [x] make bootstrap && make doctor 可运行 (2026-02-14: nvm fallback 修复, GO 10/10)
  [x] make scaffold-phase-0 生成完整骨架
  [x] make verify-phase-0 --json 全绿 (2026-02-14: hard 10/10, soft 2/2)
  [x] evidence/phase-0/ 包含验收 JSON
  [x] delivery/milestone-matrix.yaml 可被 CI 解析
  [x] CLAUDE.md + hooks + patterns 可被 Claude Code 加载

Day 60 退出:
  [x] RLS 隔离测试全绿 (2026-02-14: 20 tests passed)
  [x] risk_scorer.sh 输出 JSON 并接入 PR 模板 (2026-02-15: PULL_REQUEST_TEMPLATE.md 含 risk_score 字段)
  [x] .audit/ 目录有 Agent 会话审计日志 (2026-02-15: hooks 写入 session-*.jsonl，session ID 确定性生成)
  [x] make audit-report 可输出聚合报告 (2026-02-14: 已实现)
  [x] make verify-phase-1 --json 全绿 (2026-02-14: hard 5/5)

Day 90 退出:
  [ ] 完成"升级-回滚-恢复-审计取证"全流程演练 -- Phase 2 未启动
  [x] evidence/release/ 包含完整证据链 (2026-02-14: v0.1.0/ 含 5 文件)
  [x] delivery/commercial/ 模板套件就位 (2026-02-14: SLA/SAT/Runbook/Cost Model 已落盘)
  [x] SLA/SAT/Runbook 可交付给种子客户 (2026-02-14: 模板已落盘)
```

---

---

## 7. 里程碑矩阵评审待办 (L2 改进项)

> 来源: 任务卡交叉审查 (2026-02-13)
> 说明: 以下为前端架构文档中定义但当前里程碑矩阵无对应条目的功能。
> 不影响任务卡对齐率 (~98%)，但影响架构 vs 矩阵+任务卡完整度 (~93%)。
> **决策追踪已迁移至 Section 10** (含 Owner + 截止时间)。

| # | 架构来源 | 缺口描述 |
|---|---------|---------|
| A | FE-05 Section 3 (非对话路由) | Web App `/settings` 页 (个人偏好/profile) 无矩阵条目 |
| B | FE-02 Section 2 (SSE 事件) | SSE 通知中心 UI (system_notification 事件的用户端展示/管理) 无矩阵条目 |
| C | FE-06 (platform-ops) | Admin Model Registry / Model Pricing 页面无矩阵条目 |
| D | FE-06 (platform-ops) | Admin Plugin/Tool Management 无矩阵条目 |

---

## 8. 验收命令机器可判定性规则

> 来源: 任务卡交叉审查 (2026-02-13) Issue 7
> 优先级: MID
> Owner: Faye
> 触发条件: FW0-8 (Playwright E2E 基础设施) 合并后

### 8.1 问题

里程碑矩阵中部分条目验收命令标记为 `[E2E]` 但实际是自然语言描述 (如 "输入凭证 -> 提交 -> 跳转到主页")，
CI 无法自动判定 PASS/FAIL。Phase 0 无 E2E 基础设施时此为合理占位，但 FW0-8 合并后必须命令化。

### 8.2 硬规则

```
RULE acceptance-command-no-placeholder:
  scope: docs/governance/milestone-matrix-*.md
  condition: FW0-8 已合并 (Playwright E2E 基础设施就绪)
  check: grep -Pn '^\| .+ \| \[E2E\] [^`|]' docs/governance/milestone-matrix-*.md
  expected: 0 matches (所有 [E2E] 验收命令必须包含可执行命令，非纯文本描述)
  enforcement: Phase gate review 前执行，非零匹配数阻断 Go/No-Go
```

### 8.3 CI 脚本规格

```bash
# scripts/check_acceptance_commands.sh
# 用途: 检查里程碑矩阵验收命令是否含文本占位
# 触发: Phase gate review CI job
# 退出码: 0 = 全部命令化, 1 = 存在文本占位

FW08_MERGED=$(git log --oneline --all --grep="FW0-8" | head -1)
if [ -z "$FW08_MERGED" ]; then
  echo "SKIP: FW0-8 not yet merged, E2E placeholders allowed"
  exit 0
fi

# 匹配 [E2E] 后紧跟非反引号字符的行 (即纯文本描述，非命令)
VIOLATIONS=$(grep -Pn '^\| .+ \| \[E2E\] [^`|]' docs/governance/milestone-matrix-*.md || true)
if [ -n "$VIOLATIONS" ]; then
  echo "FAIL: E2E acceptance commands contain text placeholders:"
  echo "$VIOLATIONS"
  echo ""
  echo "ACTION: Replace text descriptions with executable Playwright commands"
  echo "  Example: [E2E] \`pnpm exec playwright test tests/e2e/login.spec.ts\`"
  exit 1
fi

echo "PASS: All [E2E] acceptance commands are machine-judgeable"
exit 0
```

### 8.4 命令化转换示例

| Before (文本占位) | After (命令化) |
|---|---|
| `[E2E] 输入凭证 -> 提交 -> 跳转到主页` | `[E2E] \`pnpm exec playwright test tests/e2e/auth/login.spec.ts\`` |
| `[E2E] 左栏历史列表 + 右栏对话区域` | `[E2E] \`pnpm exec playwright test tests/e2e/chat/layout.spec.ts\`` |

### 8.5 时间线

- FW0-8 合并前: `[E2E]` 文本占位合法，脚本输出 SKIP
- FW0-8 合并后: 下一次 Phase gate review 前完成所有 `[E2E]` 条目命令化
- 永久: 新增矩阵条目禁止引入 `[E2E]` 文本占位 (必须同时提供 spec 文件路径)

### 8.6 [ENV-DEP] 例外标注规则

部分任务卡验收命令虽为可执行命令格式，但依赖外部环境 (CI、Docker、Neo4j、Qdrant、S3 等)，
在纯本地环境无法直接运行。此类命令需加 `[ENV-DEP]` 前缀标注。

```
RULE acceptance-command-env-dep:
  scope: docs/task-cards/**/*.md
  definition: 验收命令含 docker/docker-compose/gh/curl localhost/make deploy/
              k6/artillery 等外部依赖关键词
  annotation: 在命令前加 [ENV-DEP] 前缀
  example: | **验收命令** | [ENV-DEP] `docker compose up -d && curl ...` |
  ci-behavior: CI 脚本识别 [ENV-DEP] 后跳过本地验证，
               仅在对应环境 (staging/CI runner) 中执行
  enforcement: Phase gate review 检查所有 ENV-DEP 命令在 CI 中有对应 job
```

### 8.7 [MANUAL-VERIFY] 人工验证标注规则

部分验收命令确实无法命令化（如 "团队成员可实际使用系统完成对话"），需标注
`[MANUAL-VERIFY]` 并提供替代验证方式。

```
RULE acceptance-command-manual-verify:
  scope: docs/task-cards/**/*.md
  definition: 验收标准为主观体验、可用性评估、或跨系统端到端流程，
              无法用单条 shell 命令判定通过/失败
  annotation: 在验收描述前加 [MANUAL-VERIFY] 前缀
  required: 必须附带替代验证方式 (录屏/截图/检查清单/用户反馈表)
  example: |
    | **验收命令** | [MANUAL-VERIFY] 团队成员可使用系统完成一轮完整对话
    (替代: 录屏截图存入 evidence/phase-2/dogfooding/) |
  ci-behavior: CI 脚本识别 [MANUAL-VERIFY] 后输出 SKIP，
               不计入自动化通过率
  enforcement: Phase gate review 检查所有 MANUAL-VERIFY 条目
               具备替代验证证据
```

### 8.8 Schema Tier 分层规则

任务卡按特征分为 Tier-A (Full, 10 字段) 和 Tier-B (Light, 8 字段)。
完整规则见 `docs/governance/task-card-schema-v1.0.md` Section 1。

```
RULE schema-tier-assignment:
  scope: docs/task-cards/**/*.md
  tier-a-triggers (满足任一):
    - Phase >= 2
    - 跨层依赖 (依赖字段引用其他层前缀)
    - Port/Adapter/Migration 变更
    - 安全相关卡 (TASK-OS-*)
    - 关键卡清单 (见 schema 文档 Section 1.3)
  tier-b-default:
    - 不满足任何 Tier-A 触发条件
  enforcement:
    - scripts/check_task_schema.py 自动判定 Tier 并校验对应字段集
    - 字段要求: Tier-A = 10 字段, Tier-B = 8 字段
```

### 8.9 Exception 声明格式

任务卡无法满足某必填字段时，允许声明例外。
完整规则见 `docs/governance/task-card-schema-v1.0.md` Section 3。

```
RULE exception-declaration:
  format: "> EXCEPTION: [EXC-ID] | Field: [字段] | Owner: [name] | Deadline: [Phase X gate] | Alt: [替代验证]"
  required: EXC-ID + Field + Owner(非TBD) + Deadline(关联Phase gate) + Alt(非空)
  ci-behavior: check_task_schema.py 遇合法 EXCEPTION 行跳过该字段检查
  enforcement: Phase gate review 审查所有活跃 Exception
```

---

## 9. M-Track 待补记录

> 来源: 任务卡交叉审查 (2026-02-13) M-Track 覆盖缺口分析

### MM3-1: 版权风险检测 (Phase 5 治理)

| 字段 | 内容 |
|------|------|
| **矩阵条目** | MM3-1 (milestone-matrix-crosscutting.md Section 3.4 Phase 5) |
| **状态** | 已落卡 -- TASK-MM3-1 已创建于 `docs/task-cards/07-部署与安全/obs-security.md` Phase 5 段末 |
| **原因** | 原延期理由 (Phase 5 交付物、依赖未实现) 仍成立，但为闭环 L2->L3 SSOT 链路提前建卡 |
| **Owner** | Faye |
| **截止** | Phase 4 gate review 前完成任务卡创建 |
| **主卡归属** | Obs & Security (版权合规检测) |
| **引用层** | Knowledge (内容源), Tool (检测工具) |

---

## 10. Section 7 待办项决策追踪

> 来源: 任务卡交叉审查 (2026-02-13)
> 规则: 每项必须有 决策/Owner/截止，禁止 TBD owner
> 状态: 4 项均为受控未决 (controlled-pending)，将在对应 Phase gate review 裁决落盘

| # | 架构来源 | 缺口描述 | 决策 | Owner | 截止 |
|---|---------|---------|------|-------|------|
| A | FE-05 Section 3 (非对话路由) | Web App `/settings` 页无矩阵条目 | 待评审: 是否归入现有 FW 条目子实现 | Faye | Phase 2 gate review |
| B | FE-02 Section 2 (SSE 事件) | SSE 通知中心 UI 无矩阵条目 | 待评审: 后端 G2-7 已补充，前端消费方 FW2-9 已补充，评估是否需独立通知中心 UI 条目 | Faye | Phase 2 gate review |
| C | FE-06 (platform-ops) | Admin Model Registry / Model Pricing 页面无矩阵条目 | 待评审: 是否新增 FA 条目 | Faye | Phase 3 gate review |
| D | FE-06 (platform-ops) | Admin Plugin/Tool Management 无矩阵条目 | 待评审: 是否新增 FA 条目 | Faye | Phase 3 gate review |

---

## 11. 执行补全附录（Task Card / SKILLS / CI）

> 来源: 本轮全量审查结论 (2026-02-13)
> 目的: 将“建议项”转化为可执行、可机判、可审计规则，消除治理口径漂移

### 11.1 Task Card 统一 Schema（双 Tier + 结果导向 + 可验证）

> 完整 Schema 规范已独立落盘: `docs/governance/task-card-schema-v1.0.md`
> 校验脚本: `scripts/check_task_schema.py`
> 计数校准: `scripts/count_task_cards.py`

核心变更 (v1.0):

1. **双 Tier 体系**: Tier-A (10 字段, Phase 2+/跨层/Port) + Tier-B (8 字段, Phase 0-1/纯新增)
2. **三类验收标签**: `[ENV-DEP]` (环境依赖) + `[MANUAL-VERIFY]` (人工验证) + `[E2E]` (端到端测试)
3. **Exception 声明**: 合法例外需完整 5 要素 (EXC-ID/Field/Owner/Deadline/Alt)
4. **渐进门禁**: Warning -> Incremental Block -> Full Block
5. **结果导向**: 目标字段结果导向检查为 WARNING 级别（非 BLOCK），最终由 gate review 人工裁决

字段要求汇总:

| 字段 | Tier-A | Tier-B |
|---|---|---|
| 目标 / 范围 / 范围外 / 依赖 / 兼容策略 / 验收命令 / 回滚方案 / 证据 | 必填 | 必填 |
| 风险 (分类) | 必填 | 可选 (非平凡时填写) |
| 决策记录 | 必填 | -- |
| 矩阵条目 | 必填 (元数据) | 必填 (元数据) |

### 11.2 SKILLS 工作流固化（渐进披露 + 子 Agent 专职）

```
WORKFLOW task-card-governance:
  W1 schema-normalization:
    input: existing task cards
    output: schema-compliant cards (v1)
  W2 traceability-link:
    input: milestone-matrix-*.md + task cards
    output: bidirectional links (L2 <-> L3)
  W3 acceptance-normalizer:
    input: task cards with acceptance commands
    output: executable or tagged acceptance criteria
  W4 evidence-and-gate:
    input: acceptance commands + evidence files
    output: gate report (PASS/FAIL + blockers)
```

> NOTE: intake-and-scope (originally W1) deferred to Phase 2.
> Aligned with actual SKILL implementation in .claude/skills/taskcard-governance/SKILL.md

执行要求:

| 项目 | 标准 |
|---|---|
| 渐进披露 | 每轮只暴露当前步骤必需上下文，避免一次性注入全量信息 |
| 子 Agent 职责 | 每个步骤一个专职角色（拆卡/校验/追踪/门禁），禁止职责混用 |
| 交接产物 | 每步必须落盘输入、输出、失败原因、下一步条件 |
| 审计记录 | 每次工作流执行生成 session 日志并可回放 |
| 自动化基线 | 所有 Skill/Workflow 必须有可执行脚本入口, /full-audit 可调用 (见 12.2/12.6) |
| 代码级门禁 | 工作流产出 JSON 报告, 符合 scripts/schemas/*.schema.json, CI 可消费 (见 12.1) |

### 11.3 CI 硬门禁接入（从“建议”到“阻断”）

新增 CI job（Phase gate review 必跑）:

```
1) task_card_schema_check
   - 校验 required-fields 完整性
   - 校验 In/Out Scope 与决策记录字段存在

2) task_card_traceability_check
   - 校验 "矩阵条目" 在 milestone-matrix-* 可解析
   - 校验 L2->L3 覆盖率阈值 (默认 >= 98%)

3) task_card_acceptance_check
   - 校验验收命令可执行性
   - [ENV-DEP] 条目必须映射到对应 CI/staging job
```

阻断条件:

```
BLOCK if:
  schema_missing_count > 0
  or all_coverage < 98%            # all_coverage = main refs + M-Track cross-refs
  or unmapped_env_dep_count > 0
  or gate_report contains HIGH unresolved findings

WARNING if:
  main_coverage < 90%              # main_coverage = primary "矩阵条目" refs only (auxiliary, non-blocking)
```

落地时间窗（硬约束）:

| 事项 | Owner | 状态 | 截止 |
|---|---|---|---|
| Task Card Schema v1.0 落盘 | Faye | Done (task-card-schema-v1.0.md) | 2026-02-13 |
| 计数校准脚本 (count_task_cards.py) | Faye | Done | 2026-02-13 |
| Schema 校验脚本 (check_task_schema.py) | Faye | Done | 2026-02-13 |
| [MANUAL-VERIFY] + Exception + Tier 规则落盘 | Faye | Done (Section 8.7-8.9) | 2026-02-13 |
| Stage 1 Wave 1 (Brain + MC + FE-Monorepo, 50 卡) | Faye | Pending | 下一个 Phase gate review 前 |
| Stage 1 Wave 2 (K/S/T/G, 64 卡) | Faye | Pending | Wave 1 验证后 |
| Stage 1 Wave 3 (I/D/OS, 103 卡) | Faye | Pending | Wave 2 完成后 |
| Stage 1 Wave 4 (FE 剩余, 41 卡) | Faye | Pending | Wave 3 完成后 |
| Stage E 工程基线 (Makefile/pyproject/CLAUDE.md) | Faye | Pending | 与 Stage 1 并行 |
| Stage 2 CI 门禁 Warning 模式启用 | Faye | Pending | Stage 1 Wave 1 同步 |
| Stage 2 CI 门禁 Full Block 启用 | Faye | Pending | Stage 1 全量完成后 |
| Stage 2.5 证据基础设施 (evidence/) | Faye | Pending | Stage 2 Warning 启用后 |
| Stage 3 SKILLS 工作流固化 (skill-taskcard-governance) | Faye | Done (2026-02-15: 4 workflows + role isolation + trap-based fallback) | Stage 2 完成后 |
| Stage C 商业交付模板 (SLA/运维/SAT) | Faye | Pending | Stage 2 完成后 |

---

> v2.0 核心变更: 从"补原则"转向"补执行"。
> 4 个执行缺口 = Golden Path + 机器可判定矩阵 + Agent 审计与代码级强制 + 商业化模板。
> 30-60-90 路线每段有明确退出标准，可验证。
> v2.1 补充: Stage 0 产出物 (Schema + 脚本 + 规则) 已落盘 (2026-02-13)。
> v2.2 补充: 执行边界规范 (Section 12, 12.1-12.9) + 实施计划 (Section 13) -- 代码级强制 + /full-audit + 语义触发 + G1-G7 裁决追溯 (2026-02-15)。

---

## 12. 执行边界规范

> 来源: GAP 审查对照分析 (2026-02-15)
> 修订: 2026-02-15 (v2: 代码级强制 + 自动化基线 + /full-audit + 语义触发)
> 目的: 为每个组件类型划定完成标准、触发机制和强制执行要求，
> 确保 Agent/Skill/Hook/Workflow 全部具备自动化基线和代码级门禁能力。

### 12.1 CI 门禁脚本退出码规范

> 适用范围: 所有 `scripts/check_*.py`、`scripts/check_*.sh`、`scripts/hooks/*.sh`

```
被 CI 调用时 (GitHub Actions):
  exit 0 = PASS
  exit 1 = FAIL (CI job 失败, PR 阻断)
  exit 2 = ERROR (配置错误, fail-closed)

被 Claude Code hooks 调用时:
  exit 0 = 放行
  exit 1 = 软告警 (stderr 输出但不阻断操作)
  exit 2 = 硬阻断 (阻断当前编辑/命令)

fail-closed 原则:
  两种上下文下, 搞不清状态时都用最高退出码 (CI=1, hooks=2)。
  宁可误报也不放行。
```

### 12.2 组件完成标准

> 每种产出物的"完成"定义。所有组件必须同时满足: 自动化基线 + 代码级门禁 + 触发机制。

```
Agent 定义 (.claude/agents/*.md):
  完成 =
    (1) YAML frontmatter 有正确 tools 列表 + 职责描述 + 写边界声明
    (2) 代码级门禁: hooks 验证 Agent 行为边界 (见 12.5)
    (3) 触发机制: /full-audit 可调用 + 语义关键词可激活 (见 12.7)
    (4) 自动化验证: 对应测试文件验证 frontmatter 一致性
        (tests/unit/scripts/test_agent_permissions.py)
  不包含 = 独立的 Agent 行为监控服务 (不自建基础设施)

Hook 脚本 (scripts/hooks/*.sh):
  完成 =
    (1) settings.json 正确触发 + 按 12.1 退出码工作 + 写审计日志到 .audit/
    (2) 代码级门禁: 对高危操作执行阻断 (exit 2)
    (3) 触发机制: 自动触发 (Claude Code 平台机制) + /full-audit 可调用
    (4) 自动化验证: 对应测试文件验证 hook 行为
  不包含 = 替代 CI 门禁或测试套件的深度验证功能 (hooks 是实时轻量拦截层)

Guard 脚本 (scripts/check_*.sh):
  完成 =
    (1) 静态/文本级检查 + JSON 输出 + CI 可调用 + 符合 12.1 退出码
    (2) 代码级门禁: CI 中作为 PR 门禁运行 (见 12.4 能力矩阵)
    (3) 触发机制: CI 自动触发 + /full-audit 可调用
    (4) 自动化验证: 对应测试文件验证检查逻辑
  不包含 = 运行时验证 (运行时验证是测试套件的职责, 见 12.3)

Skill 定义 (.claude/skills/*/SKILL.md):
  完成 = 所有 Skill 必须实现自动化基线:
    (1) 有对应脚本入口 (scripts/run_*.sh 或 scripts/skills/*.sh)
    (2) 脚本能跑、产出 JSON 报告、符合 12.1 退出码
    (3) JSON 输出符合 scripts/schemas/*.schema.json 约束
    (4) /full-audit 可调用 + 语义关键词可激活 (见 12.7)
  自动化基线覆盖可机判子集; LLM 判断力覆盖不可机判子集。
  两者共存于同一 Skill 中, 不再区分"自动化型"和"方法论型"。

Workflow 定义 (.claude/skills/*/scripts/run_w*.sh):
  完成 =
    (1) 脚本可独立运行 (bash scripts/skills/*/run_w*.sh)
    (2) 支持 WORKFLOW_ROLE 环境变量做角色隔离
    (3) 有 trap 机制确保失败时也产出状态文件
    (4) /full-audit 可调用 (通过 run_all.sh 编排)
    (5) 自动化验证: 对应测试文件验证工作流行为
```

### 12.3 Guard 脚本 vs 测试套件职责分层

> 解决"guard 脚本是否应该做运行时验证"的争议。

```
Guard 脚本 (scripts/check_*.sh):
  定位: 轻量静态检查, 秒级完成, CI 每次 PR 都跑
  方法: 文本匹配、文件存在性检查、方法签名列表 diff
  举例:
    check_rls.sh      -> 验证迁移文件中有 CREATE POLICY 语句
    check_layer_deps.sh -> 验证 import 语句无跨层违规
    check_port_compat.sh -> 验证 Port 方法未被删除

测试套件 (tests/):
  定位: 深度运行时验证, 可能需要环境依赖
  方法: 实际执行代码、连接数据库、模拟请求
  举例:
    tests/isolation/smoke/ -> 验证 RLS 策略实际隔离租户数据
    tests/unit/ports/      -> 验证 Port 接口签名和契约类型

两者互补: guard 先拦住明显问题 (快、每次跑),
          测试再验证深层正确性 (慢、按需跑)。
Guard 不需要做测试的活, 测试不需要做 guard 的活。
```

### 12.4 工具能力矩阵 (能力层 vs 执行层分离)

> 核心原则: 工具**能力**应尽早建设 (能做), **执行级别**可分阶段提升 (做了阻断还是告警)。
> 工具能力 = 脚本能检测到问题; 执行级别 = 检测到后是 WARN 还是 BLOCK。

```
Guard 脚本能力矩阵:

  check_layer_deps.sh:
    当前能力: regex import 检测 (5 层规则)
    能力目标: AST 级 import 检测 (消除 regex 漏报)
    执行级别: Phase 0 = CI BLOCK (已实现) | hooks = Phase 2+ 启用
    能力建设: Phase 2 扩展为 AST 检测

  check_port_compat.sh:
    当前能力: git diff 方法名删除检测 (文本级)
    能力目标: 签名级兼容检测 (参数类型 + 返回类型 + 新增必填参数)
    执行级别: Phase 0 = CI WARN | Phase 2+ = CI BLOCK
    能力建设: Phase 1 补 tests/unit/ports/ 签名断言;
              Phase 2 扩展脚本为 AST 签名检测

  check_rls.sh:
    当前能力: 迁移文件 CREATE POLICY 文本扫描
    能力目标: 迁移文件扫描 + 实际 DB 策略验证
    执行级别: Phase 0 = CI BLOCK (文本级) | Phase 1+ = 测试套件 BLOCK (DB 级)
    能力建设: Phase 1 补 tests/isolation/ 真实 DB 连接测试
              (测试代码已就绪, 缺环境依赖; 环境就绪后立即可跑)

  check_acceptance_commands.sh / check_acceptance_gate.py:
    当前能力: E2E 占位检测 + 验收命令可执行性检测 (4 规则)
    能力目标: 当前能力已满足 Phase 0-1 需求
    执行级别: Phase 0 = CI BLOCK (已实现)

Hook 脚本能力矩阵:

  pre_edit_audit.sh:
    当前能力: 文件 -> 层 -> Tier 映射 + 审计日志 + Phase 阶段性阻断
    能力目标: 当前能力已满足
    执行级别: Tier 1-2 = log only | Tier 3 = WARN | Tier 4 = Phase 条件阻断

  pre_commit_gate.sh:
    当前能力: lint + test-smoke + schema + layer-deps + migration + port-compat
    能力目标: 增加覆盖率门禁 (--cov-fail-under)
    执行级别: Phase 0-1 = 当前 6 项检查 | Phase 2+ = 加覆盖率门禁
    能力建设: Phase 2 加 pytest --cov-fail-under 参数 (工具能力已有, 只需配置)

  post_edit_schema_check.sh:
    当前能力: task-card 文件 schema 快检
    能力目标: 当前能力已满足
    执行级别: 非阻断 (exit 0, stderr 反馈)

  PostToolUse 跨层检测 hook (待建):
    当前能力: 不存在 (check_layer_deps.sh 具备检测能力, 缺 hook 调用壳)
    能力目标: 编辑后即时检测跨层导入违规
    执行级别: Phase 0-1 = log only (exit 0) | Phase 2+ = WARN (exit 1)
    能力建设: 编写 post_edit_layer_check.sh 调用 check_layer_deps.sh
              脚本应现在建设 (成本极低), 执行级别分阶段提升
```

### 12.5 Agent 代码级强制执行

> Agent 行为通过三层机制实现代码级强制 (非仅可观测性):
> (1) hooks 实时拦截; (2) CI 门禁静态验证; (3) /full-audit 全量审计。

```
第一层 -- hooks 实时拦截 (已实现):
  pre_edit_audit.sh:
    - 按文件路径分 Tier, 记录审计日志
    - Tier 4 (src/ports/, src/infra/org/) 执行 Phase 条件阻断
    - Agent 触碰高危文件时 exit 2 硬阻断
  pre_commit_gate.sh:
    - 6 项门禁 (lint/test-smoke/schema/layer-deps/migration/port-compat)
    - 任一失败 exit 2 阻断 commit
  user_prompt_guard.sh:
    - 密钥泄露模式检测, 命中即 exit 2 阻断

第二层 -- CI 门禁静态验证 (已实现):
  ci.yml semantic-checks job:
    - check_layer_deps.sh 跨层导入检测
    - check_port_compat.sh Port 兼容检测
    - check_task_schema.py Schema 完整性
    - check_rls.sh RLS 策略存在性
  ci.yml task-card-check job:
    - task_card_traceability_check.py 追溯覆盖率
  tests/unit/scripts/test_agent_permissions.py:
    - Agent frontmatter tools 列表一致性验证
    - read-only Agent 无 Write/Edit 工具验证

第三层 -- /full-audit 全量审计 (待建, 见 12.6):
  统一入口调用所有检测脚本 + Skill 审计 + Agent 验证
  产出合并报告, 作为 Phase gate review 前置条件

Agent 写边界强制:
  security-reviewer: tools 列表不含 Write/Edit (代码级: test_agent_permissions.py 验证)
  architect: tools 列表仅含 Read/Grep/Glob (代码级: test_agent_permissions.py 验证)
  tdd-guide: tools 列表含 Write/Edit (需要修改测试文件, 合理)

  不做:
    - 不做独立的 Agent 行为监控服务 (不自建基础设施, hooks + CI + /full-audit 足够)
```

### 12.6 /full-audit 统一审计入口

> 所有 Agent/Skill/Hook/Workflow/Guard 的自动化基线通过单一命令可验证。
> 作为 Phase gate review 前置条件; 日常开发可随时运行自检。

```
命令: make full-audit

等价于依次执行:
  1) Guard 脚本全量:
     bash scripts/check_layer_deps.sh --json
     bash scripts/check_port_compat.sh --json
     bash scripts/check_rls.sh --json
     bash scripts/check_migration.sh --json
     uv run python scripts/check_task_schema.py --mode full --json
     uv run python scripts/check_acceptance_gate.py --json

  2) Skill 审计全量:
     bash scripts/run_systematic_review.sh
     bash scripts/run_cross_audit.sh
     bash scripts/run_fix_verify.sh

  3) Agent 验证:
     uv run pytest tests/unit/scripts/test_agent_permissions.py -v

  4) Hook 验证:
     uv run pytest tests/unit/scripts/test_gap_regressions.py -v

  5) Workflow 验证:
     uv run pytest tests/unit/scripts/test_taskcard_workflow_handoff.py -v

  6) 治理一致性:
     uv run pytest tests/unit/scripts/test_governance_consistency.py -v

  7) 报告聚合:
     uv run python scripts/audit_aggregator.py .audit/ --full

输出: evidence/full-audit-{timestamp}.json
退出码: 0 = 全 PASS | 1 = 有 FAIL 项 | 2 = 有 ERROR (配置问题)

触发时机:
  - Phase gate review 前: 必须运行, 全 PASS 才能 Go/No-Go
  - 日常: 开发者随时可跑 (make full-audit)
  - CI: 可作为 scheduled job (每周/每次 main push)
```

### 12.7 语义关键词触发机制

> 组件不仅通过命令显式调用, 还通过语义关键词自动激活。
> 当用户 prompt 或变更文件路径匹配关键词时, Claude Code 自动建议对应组件。

```
Agent 语义激活:
  diyu-architect:
    关键词: "架构审查", "层边界", "Port 接口", "跨层依赖"
    文件触发: src/ports/*, 同时变更多个 src/{layer}/ 目录
  diyu-security-reviewer:
    关键词: "安全审查", "RLS", "JWT", "认证", "授权", "org_id"
    文件触发: migrations/*, src/infra/org/*, src/gateway/*
  diyu-tdd-guide:
    关键词: "测试", "覆盖率", "TDD", "验收命令"
    文件触发: tests/*, docs/task-cards/* (验收命令变更时)

Skill 语义激活:
  systematic-review:
    关键词: "全量审查", "系统审查", "代码审查", "review"
    命令: /systematic-review
  cross-reference-audit:
    关键词: "交叉审查", "文档对齐", "cross-reference"
    命令: /cross-reference-audit
  adversarial-fix-verification:
    关键词: "修复验证", "adversarial", "fix-verify"
    命令: /adversarial-fix-verify

统一入口:
  /full-audit 或 make full-audit: 触发全量审计 (见 12.6)
  语义: "全量审计", "full audit", "gate review"

实现方式:
  UserPromptSubmit hook 中的 user_prompt_guard.sh 扩展:
    - 当前: 仅检测密钥泄露
    - 扩展: 检测语义关键词, 通过 stderr 输出建议
      (如: "SUGGEST: 检测到安全相关变更, 建议运行 /security-review")
    - 非阻断 (exit 0), 仅输出建议到 stderr 供 Claude 感知
```

### 12.8 Phase 边界 (执行级别调度)

> 与 Section 3 (30-60-90 执行路线) 的 exit criteria 互补。
> 本节只管**执行级别** (WARN/BLOCK), 工具**能力**由 12.4 管理。
> 工具能力应尽早建设; 执行级别分阶段提升。

```
Phase 0 (治理最小集 + 交付骨架):
  执行级别:
    - Guard 脚本: CI BLOCK (check_layer_deps, check_rls, check_acceptance)
    - Hooks: 审计日志 + Tier 4 条件阻断
    - /full-audit: 可运行 (作为自检, 非门禁)
  能力建设 (本阶段完成):
    - post_edit_layer_check.sh hook 脚本 (调用 check_layer_deps.sh, exit 0 log only)
    - /full-audit Makefile target + 报告聚合脚本
    - user_prompt_guard.sh 语义关键词建议扩展
  不做的执行级别:
    - 覆盖率门禁 BLOCK (代码骨架阶段覆盖率无意义)
    - PostToolUse hook BLOCK (层边界未冻结, 误报噪音大)

Phase 1 (安全与租户底座):
  执行级别:
    - 继承 Phase 0 全部
    - tests/isolation/ 真实 DB 测试 BLOCK (环境就绪后)
    - tests/unit/ports/ 签名断言 BLOCK
  能力建设 (本阶段完成):
    - pre_commit_gate.sh 增加 Port 签名变更检测 (基于 tests/unit/ports/)
  不做的执行级别:
    - E2E 门禁 BLOCK (Phase 2: Playwright 基础设施)
    - PostToolUse hook BLOCK (仍 log only)

Phase 2+ (核心业务 + 前端联调):
  执行级别:
    - 继承 Phase 1 全部
    - PostToolUse hook WARN (exit 1, 跨层导入检测)
    - 覆盖率门禁 BLOCK (--cov-fail-under)
    - check_port_compat.sh BLOCK (Port 接口冻结, 签名级)
  能力建设 (本阶段完成):
    - check_port_compat.sh AST 签名检测扩展
    - E2E 门禁脚本
```

### 12.9 Agent 治理实现路径

> 替代原 12.5, 明确 Agent 治理通过 hooks + CI + /full-audit 三层实现代码级强制。
> "代码级强制"指: Agent 违反边界时, 有代码 (非仅文档) 检测并阻断/告警。

```
三层强制机制:

  (1) hooks 实时拦截 (已实现):
      pre_edit_audit.sh 根据 Agent 编辑路径执行 Tier 级阻断
      pre_commit_gate.sh 6 项门禁阻断违规 commit
      user_prompt_guard.sh 密钥泄露阻断

  (2) CI 静态验证 (已实现):
      test_agent_permissions.py:
        - 验证所有 Agent frontmatter 有 tools 列表
        - 验证 read-only Agent (security-reviewer) 无 Write/Edit
        - 验证 security-reviewer 有必需 review 工具 (Read/Grep/Glob)
      ci.yml semantic-checks:
        - check_layer_deps.sh 跨层导入
        - check_port_compat.sh Port 兼容
        - check_rls.sh RLS 策略

  (3) /full-audit 全量审计 (12.6):
      统一入口, Phase gate review 前置条件

Agent 写边界规则:
  security-reviewer: READ-ONLY (tools 不含 Write/Edit, 代码验证: test_agent_permissions.py)
  architect: READ-ONLY (tools 仅 Read/Grep/Glob)
  tdd-guide: READ-WRITE (需修改测试文件/任务卡, 合理)

  写边界违规检测:
    test_agent_permissions.py 在 CI 中自动运行
    /full-audit 中包含 Agent 验证步骤

Security Reviewer 安全规则:
  当前: 依赖 LLM 通用安全知识 + CLAUDE.md 红线 + CI guard/test 门禁
  扩展触发点: SOC 2 / 等保认证时追加项目安全规则文件
  Owner: Faye | 复审: Phase 3 gate review
```

---

## 13. Section 12 实施计划

> 来源: Section 12 执行边界规范 (2026-02-15)
> 目的: 将 Section 12 定义的规范落地为可执行代码和自动化验证
> 依赖: Section 12 定义完成 (Done)
> 验收: make full-audit 全 PASS

### 13.1 实施项清单

```
基础设施层 (使 /full-audit 可运行):

  P1: Makefile 增加 full-audit target
    产出: Makefile 新 target
    来源: 12.6
    依赖: 无

  P2: scripts/full_audit.sh 编排脚本
    产出: 编排脚本, 依次调用 7 类检查, 聚合 JSON 报告
    来源: 12.6
    依赖: 无

  P3: scripts/hooks/post_edit_layer_check.sh
    产出: PostToolUse hook 脚本, 调用 check_layer_deps.sh, exit 0 log only
    来源: 12.4 (PostToolUse 待建项)
    依赖: 无

  P4: .claude/settings.json 注册 P3 hook
    产出: PostToolUse 增加 layer check entry
    来源: 12.4
    依赖: P3

  P5: scripts/hooks/user_prompt_guard.sh 语义关键词扩展
    产出: stderr 输出组件建议 (非阻断, exit 0)
    来源: 12.7
    依赖: 无

  P6: .claude/commands/full-audit.md
    产出: /full-audit slash command 定义
    来源: 12.6
    依赖: P1

验证闭环层 (确保自动化基线有测试覆盖):

  P7: tests/unit/scripts/test_skill_automation_baseline.py
    产出: 验证所有 Skill 有对应脚本入口 + JSON schema
    来源: 12.2 (Skill 完成标准)
    依赖: 无

  P8: tests/unit/scripts/test_hook_behavior.py
    产出: 验证所有 hook 退出码符合 12.1 + 审计日志写入
    来源: 12.2 (Hook 完成标准)
    依赖: 无

  P9: tests/unit/scripts/test_workflow_completeness.py
    产出: 验证 W1-W4 + run_all.sh 完整性和角色隔离
    来源: 12.2 (Workflow 完成标准)
    依赖: 无

  P10: scripts/schemas/full-audit-report.schema.json
    产出: /full-audit JSON 输出格式定义
    来源: 12.6 (输出格式)
    依赖: 无

一致性修复层 (消除仓库内交叉引用歧义):

  P11: docs/governance/governance-optimization-plan.md 内部交叉引用校验
    产出: 所有 12.x 引用指向正确子节
    来源: Section 12 重构
    状态: Done (12.6->12.4 已修复, 12.8 重复已删除)

  P12: CI 增加 full-audit scheduled job
    产出: .github/workflows/ci.yml 新增 scheduled/manual full-audit job
    来源: 12.6 (触发时机)
    依赖: P1, P2
```

### 13.2 执行顺序

```
批次 A (基础设施, 可并行):
  P1 + P2 + P3 + P5 + P10  -- 脚本/配置, 互不依赖

批次 B (注册, 依赖 A):
  P4 (依赖 P3) + P6 (依赖 P1)

批次 C (验证测试, 可并行):
  P7 + P8 + P9  -- 独立测试文件

批次 D (CI 集成):
  P12 (依赖 P1 + P2)

验收: make full-audit 全 PASS + uv run pytest tests/ 全 PASS
```

### 13.3 不在本批的项目 (Phase 边界, 见 12.8)

```
Phase 2 能力建设:
  - check_port_compat.sh AST 签名检测扩展
  - E2E 门禁脚本

Phase 2 执行级别提升:
  - PostToolUse hook 从 log only (exit 0) 升级为 WARN (exit 1)
  - pre_commit_gate.sh 覆盖率门禁 (pytest --cov-fail-under=80)
  - check_port_compat.sh 从 CI WARN 升级为 CI BLOCK

Phase 3 复审:
  - Security Reviewer 是否绑定项目安全规则文件 (12.9 G2 裁决)
```

### 13.4 G1-G7 裁决追溯

> 每个 Gap 的最终裁决和实施对应关系, 确保可审计。

```
G1 (Agent 无 enforcement):
  裁决: 三层代码级强制 (hooks + CI + /full-audit)
  实施: P2 (full-audit 含 Agent 验证), P8 (hook 行为测试)
  文档: 12.5, 12.9

G2 (Security reviewer 无项目 checklist):
  裁决: 当前不绑定, Phase 3 复审
  实施: 无 (有意裁决)
  文档: 12.9 G2 裁决说明

G3 (Port 兼容性只查方法删除):
  裁决: 承认能力差距, 能力建设排入 Phase 2
  实施: Phase 2 (check_port_compat.sh AST 扩展)
  文档: 12.4 能力矩阵

G5 (编辑后无跨层导入即时检测):
  裁决: 脚本现在建, 执行级别分阶段提升
  实施: P3 (hook 脚本) + P4 (注册)
  文档: 12.4 PostToolUse 待建项

G6 (TDD guide 无覆盖率门禁):
  裁决: 工具能力已有, Phase 2 开启
  实施: Phase 2 (pre_commit_gate.sh 加参数)
  文档: 12.4 pre_commit_gate.sh 能力目标, 12.8 Phase 2+ 执行级别

Hooks 部分覆盖:
  裁决: P3 补 PostToolUse 跨层检测, P5 补语义关键词
  实施: P3 + P4 + P5
  文档: 12.4, 12.7

工作流三层自动化:
  裁决: /full-audit 统一入口串联全部组件
  实施: P1 + P2 + P6 + P12
  文档: 12.6
```
