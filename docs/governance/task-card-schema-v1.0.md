# Task Card Schema v1.0

> Owner: Faye | Version: 1.0 | Status: Frozen
> Scope: `docs/task-cards/**/*.md`
> Authority: 本文件为任务卡唯一 Schema 标准。所有任务卡必须通过 `scripts/check_task_schema.py` 校验。
> References: milestone-matrix.md Section 3.2, governance-optimization-plan.md Section 11.1

---

## 1. Schema Tier 体系

任务卡分为两个 Tier，由卡特征自动判定（非作者自选）。

### 1.1 Tier 判定规则

```
RULE tier-assignment:
  Tier-A (Full) 触发条件 (满足任一):
    - Phase >= 2
    - 依赖字段引用其他层前缀 (跨层: B/MC/K/S/T/G/I/D/OS/FW/FA)
    - 范围涉及 src/ports/ 或 src/adapters/ (Port/Adapter 变更)
    - 范围涉及 Schema 迁移 (alembic/migrations)
    - 目标含"重构"/"迁移"/"替换"等变更关键词
    - 卡 ID 在关键卡清单中 (见 Section 1.3)

  Tier-B (Light) 条件:
    - 不满足任何 Tier-A 触发条件
    - 典型: Phase 0-1 纯新增、层内独立、脚手架类任务
```

### 1.2 字段对照表

| # | 字段 | Tier-A | Tier-B | 说明 |
|---|------|--------|--------|------|
| 1 | **目标** | 必填 | 必填 | 结果导向，描述可验证的业务/技术结果 |
| 2 | **范围 (In Scope)** | 必填 | 必填 | 影响的目录/文件路径 |
| 3 | **范围外 (Out of Scope)** | 必填 | 必填 | 明确不做什么，防止需求蔓延 |
| 4 | **依赖** | 必填 | 必填 | 前置任务 ID，无依赖填 `--` |
| 5 | **风险** | 必填 (分类) | 可选 | Tier-A 至少覆盖适用类别；Tier-B 仅非平凡风险需填写 |
| 6 | **兼容策略** | 必填 | 必填 | API/Schema 向后兼容声明 |
| 7 | **验收命令** | 必填 | 必填 | 可执行命令 + 期望输出 |
| 8 | **回滚方案** | 必填 | 必填 | 失败后撤回步骤 |
| 9 | **证据** | 必填 | 必填 | CI 链接 / 测试报告 / 产物路径 |
| 10 | **决策记录** | 必填 | -- | 关键取舍 + 理由 + ADR 引用 |

> 矩阵条目引用 (`> 矩阵条目: ...`) 为所有 Tier 强制要求，不计入字段表（属于卡片元数据）。

### 1.3 关键卡定义

以下类型的卡无论 Phase 均强制 Tier-A:

- Port 接口定义/变更卡 (范围含 `*_port.py` 或 `ports/`)
- Schema 迁移卡 (范围含 `alembic/` 或 `migrations/`)
- 跨层集成卡 (依赖引用 2+ 不同层前缀)
- ADR 落地卡 (目标引用 ADR-*)
- 安全相关卡 (ID 前缀 OS, 或范围含 `security/`/`auth/`/`rls/`)

---

## 2. 字段填写规范

### 2.1 目标

```
RULE objective-standard:
  required: 描述可验证的结果状态
  forbidden: 仅描述实现动作（如"编写代码实现..."）
  guidance:
    good: "Memory Core Port 完整契约定义完成，mypy --strict 通过"
    good: "Phase 0 全部交付物通过 CI 校验，zero TBD"
    bad:  "实现 Memory Core 功能"
    bad:  "编写测试用例"
  enforcement: REVIEW-TIME (CI 仅 WARNING，不阻断)
```

> 注: "结果导向"判定为语义级标准，无法 100% 机判。CI 通过关键词匹配输出 WARNING，
> 最终由 Phase gate review 人工审查裁决。

### 2.2 范围 (In Scope)

- 列出受影响的目录或文件路径
- 使用 backtick 包裹路径: `` `src/ports/memory_core_port.py` ``
- 多个路径用逗号或换行分隔

### 2.3 范围外 (Out of Scope)

```
RULE out-of-scope-standard:
  required: 至少 1 条明确排除项
  purpose: 防止需求蔓延 + 明确交付边界
  per-layer-defaults:
    Brain:      "Adapter 实现 / 前端集成 / 性能调优"
    MemoryCore: "向量化实现 / 外部存储 Adapter"
    Knowledge:  "内容审核逻辑 / 前端 UI"
    Skill:      "具体 Skill 业务逻辑 / 前端表单"
    Tool:       "LLM Provider 实现 / 计费逻辑"
    Gateway:    "前端路由 / 数据库 Schema"
    Infra:      "应用层业务逻辑 / 前端"
    Delivery:   "应用层功能 / 前端部署"
    ObsSecurity:"应用层功能 / 前端"
    Frontend:   "后端 API 实现 / 数据库"
  note: 默认排除项可直接引用，亦可自定义补充
```

### 2.4 风险

```
RULE risk-standard:
  tier-a:
    categories:
      - 依赖风险: 上游未就绪 / 版本不兼容
      - 数据风险: 数据丢失 / 不一致 / 隐私泄露
      - 兼容风险: 破坏性变更 / API 不兼容
      - 回滚风险: 不可逆操作 / 数据迁移
    rule: 覆盖所有适用类别；不适用的标注 "N/A: [原因]"
    example: |
      - 依赖风险: MC0-1 Port 未定义时本卡无法启动
      - 数据风险: N/A (纯接口定义，无数据操作)
      - 兼容风险: 新增接口，无破坏性
      - 回滚风险: git revert 即可，无 DDL

  tier-b:
    rule: 仅当存在非平凡风险时填写，否则可省略
    example: "风险: 依赖 pnpm workspace 版本，需锁定 >= 9.0"
```

### 2.5 验收命令

```
RULE acceptance-command-standard:
  format: 可执行的 shell 命令 + 期望输出描述
  tags:
    [ENV-DEP]:       依赖外部环境 (Docker/CI/数据库/外部服务)
    [MANUAL-VERIFY]: 无法命令化，需人工验证 (附替代验证方式)
    [E2E]:           E2E 测试命令 (依赖 Playwright/浏览器)

  rules:
    - 无标签命令: 必须在本地可直接执行
    - [ENV-DEP] 命令: CI 跳过本地验证，在 staging/CI runner 执行
    - [MANUAL-VERIFY] 命令: 必须附带替代验证描述
    - [E2E] 命令: 依赖 FW0-8 (Playwright 基础设施) 落地

  hard-fail:
    - 验收命令为空
    - 自然语言描述无任何标签

  examples:
    local:  "mypy --strict src/ports/ && pytest tests/unit/ports/ -v"
    envdep: "[ENV-DEP] docker compose up -d && curl -sf localhost:8000/health"
    manual: "[MANUAL-VERIFY] 团队成员可使用系统完成一轮完整对话 (替代: 录屏截图存入 evidence/)"
    e2e:    "[E2E] pnpm exec playwright test tests/e2e/chat/layout.spec.ts"
```

### 2.6 决策记录 (Tier-A Only)

```
RULE decision-record-standard:
  required-for: Tier-A cards only
  format: "决策: [结论] | 理由: [why] | 影响: [scope] | 来源: [ADR-XXX / 架构文档 Section]"
  example: |
    决策: 使用 Expand-Contract 模式演进 Port
    理由: 避免一次性破坏性变更，支持灰度
    影响: 所有 Adapter 需同时支持新旧接口直到旧版废弃
    来源: ADR-033
  fallback: 无关键决策时填 "本卡无关键取舍，遵循层内默认约定"
```

---

## 3. Exception 声明格式

当任务卡无法满足某必填字段要求时，允许声明例外，但必须完整。

```
RULE exception-declaration:
  format: "> EXCEPTION: [EXC-ID] | Field: [字段] | Owner: [name] | Deadline: [Phase X gate] | Alt: [替代验证]"
  required-fields:
    - EXC-ID: 唯一标识 (格式: EXC-[LAYER]-[SEQ], 如 EXC-BRAIN-001)
    - Field: 哪个必填字段无法满足
    - Owner: 负责人 (禁止 TBD)
    - Deadline: 解决截止 (必须关联 Phase gate)
    - Alt: 替代验证方式 (不能为空)
  hard-fail:
    - 缺少任一项 → 例外无效 → 字段视为缺失
  ci-behavior:
    - check_task_schema.py 遇到合法 EXCEPTION 行 → 跳过该字段检查
    - 输出 EXCEPTION 清单供 gate review 审查
  example: |
    > EXCEPTION: EXC-BRAIN-001 | Field: 风险 | Owner: Faye | Deadline: Phase 2 gate | Alt: 纯接口定义无运行时风险，Phase 2 集成时补充
```

---

## 4. 矩阵条目引用规范

```
RULE matrix-reference:
  format: "> 矩阵条目: [ID] | V-x: [cross-ref] | V-fb: [fe-be-ref]"
  required: 每张卡必须有至少一个矩阵条目 ID
  validation:
    - ID 必须在 milestone-matrix-*.md 中存在
    - V-x / V-fb / M-Track 为可选补充引用
  orphan-detection:
    - ### TASK-* 标题后 20 行内必须出现 "矩阵条目"
    - 脚本: scripts/check_task_schema.py --orphan-check
```

---

## 5. Tier-A 完整模板

```markdown
### TASK-[ID]: [标题]

| 字段 | 内容 |
|------|------|
| **目标** | [结果导向的业务/技术目标] |
| **范围 (In Scope)** | `[affected/paths]` |
| **范围外 (Out of Scope)** | [明确排除项] |
| **依赖** | [前置任务 ID] 或 -- |
| **风险** | 依赖: [desc] / 数据: [desc] / 兼容: [desc] / 回滚: [desc] |
| **兼容策略** | [向后兼容声明] |
| **验收命令** | `[executable command]` |
| **回滚方案** | `git revert <commit>` [+ 额外步骤] |
| **证据** | [CI 链接 / 测试报告 / 产物路径] |
| **决策记录** | 决策: [X] / 理由: [Y] / 影响: [Z] / 来源: [ADR-NNN] |

> 矩阵条目: [ID] | V-x: [ref]
```

## 6. Tier-B 精简模板

```markdown
### TASK-[ID]: [标题]

| 字段 | 内容 |
|------|------|
| **目标** | [结果导向的业务/技术目标] |
| **范围 (In Scope)** | `[affected/paths]` |
| **范围外 (Out of Scope)** | [明确排除项] |
| **依赖** | [前置任务 ID] 或 -- |
| **兼容策略** | [向后兼容声明] |
| **验收命令** | `[executable command]` |
| **回滚方案** | `git revert <commit>` |
| **证据** | [CI 链接 / 测试报告] |

> 矩阵条目: [ID] | V-x: [ref]
```

---

## 7. CI 校验行为

| 检查项 | Tier-A | Tier-B | 阻断级别 |
|--------|--------|--------|----------|
| 必填字段完整性 | 10 字段 | 8 字段 | BLOCK |
| 矩阵条目存在性 | 校验 | 校验 | BLOCK |
| 验收命令非空 | 校验 | 校验 | BLOCK |
| 自然语言无标签 | 校验 | 校验 | BLOCK |
| 目标结果导向 | 关键词 WARNING | 关键词 WARNING | WARNING |
| Exception 完整性 | 校验 | 校验 | BLOCK (缺项则例外无效) |
| Out of Scope 非空 | 校验 | 校验 | BLOCK |

---

## 8. 渐进式门禁上线

```
Phase 1 (Warning):
  - 所有检查输出 WARNING，不阻断 PR
  - 目的: 校准误报率，收集反馈

Phase 2 (Incremental Block):
  - 仅对新增/修改的任务卡启用 BLOCK
  - 存量卡继续 WARNING
  - 目的: 增量保障不退化

Phase 3 (Full Block):
  - 全量卡启用 BLOCK
  - 前提: Stage 1 全量修复完成
  - 存量卡通过率 >= 98% (允许合法 EXCEPTION)
```

---

## 9. 版本演进

| 版本 | 变更 | 状态 |
|------|------|------|
| v1.0 | 初始版本：双 Tier + 10/8 字段 + Exception + 渐进门禁 | Frozen |
| v1.1 (planned) | Stage 1 Wave 1 反馈后的字段微调 | Pending |
| v2.0 (planned) | Stage 2 CI 门禁全量启用后的正式版 | Pending |

---

> 维护规则: 本文件变更必须经 Phase gate review 审批。任何字段增减需同步更新
> `scripts/check_task_schema.py` 和 `milestone-matrix.md` Section 3.2。
