# Opus 执行任务书：审查能力体系加固（v1.0）

审查背景日期：2026-02-15  
目标：解决“多轮审查仍片面、TDD 无法闭环、文档对照漏项、端到端修复宣称不可信”四类根因。

---

## 1. 目标与边界

### 1.1 目标（必须同时满足）

1. 审查流程从“建议性文字”升级为“可执行命令 + 可校验产物”。
2. 审查结论从“主观完成”升级为“结构化证据可机审”。
3. 修复流程必须具备逐项闭环能力：`finding -> criterion -> scope -> evidence -> verdict`。
4. 支持大清单分批执行与跨会话续跑，避免上下文衰减导致漏项。

### 1.2 非目标（本任务不做）

1. 不改业务功能逻辑（仅限审查/验证体系）。
2. 不新增与本任务无关的治理条款。
3. 不修改已有发现结论的严重度定义。

---

## 2. 强制交付项（DoD）

以下 R1-R12 任一不满足，视为未完成。

### R1. 新增三条可执行命令（Command 层）

新增：

1. `.claude/commands/systematic-review.md`
2. `.claude/commands/cross-reference-audit.md`
3. `.claude/commands/adversarial-fix-verify.md`

要求：

1. 三个命令均包含 YAML frontmatter，且必须含 `allowed-tools`。
2. 命令描述必须声明输出到固定产物文件（见 R4）。
3. 命令正文不得只给“建议步骤”，必须给可执行命令序列。

### R2. Skill 与 Command 打通

修改：

1. `.claude/skills/SKILL.md`
2. `.claude/skills/cross-reference-audit/SKILL.md`
3. `.claude/skills/adversarial-fix-verification/SKILL.md`

要求：

1. 三份 skill 明确引用对应 command 名称（`/systematic-review`、`/cross-reference-audit`、`/adversarial-fix-verify`）。
2. 禁止出现无法落地的悬空引用（例如引用不存在的 `/verify`）。

### R3. 统一结构化产物 Schema

新增：

1. `scripts/schemas/review-report.schema.json`
2. `scripts/schemas/cross-audit-report.schema.json`
3. `scripts/schemas/fix-verification-report.schema.json`

要求：

1. 三个 schema 均定义 `required` 字段。
2. `fix-verification` schema 必须强制每个 finding 含：
   - `id`
   - `criterion`
   - `scope`（文件列表）
   - `evidence`（命令 + 输出摘要）
   - `verdict`（`CLOSED|OPEN|PRE_RESOLVED`）

### R4. 固定证据产物路径

约定并落实：

1. `evidence/review-report.json`
2. `evidence/cross-audit-report.json`
3. `evidence/fix-verification-report.json`
4. `evidence/fix-progress.md`（分批与续跑记录）

要求：

1. 产物路径必须在三个 command 文档中明确写死。
2. 命令运行后产物必须存在且可解析。

### R5. 新增统一校验器

新增：

1. `scripts/validate_audit_artifacts.py`

要求：

1. 校验三个 JSON 产物符合各自 schema。
2. 交叉校验数量一致性（至少包括）：
   - review 的 findings 数量 == fix-verification 的处理项数量（允许 `OPEN`，但不可丢项）
   - 每个 `CLOSED` finding 必须有 evidence。
3. 校验失败退出码必须非 0。

### R6. 命令执行脚本化入口

新增（可为 shell 或 python）：

1. `scripts/run_systematic_review.sh`（或 `.py`）
2. `scripts/run_cross_audit.sh`
3. `scripts/run_fix_verify.sh`

要求：

1. 三个入口脚本必须调用并写出 R4 产物。
2. 失败必须透传退出码（不得 `|| true`、不得吞错）。

### R7. Makefile 集成

修改 `Makefile`，新增至少两个目标：

1. `make audit-artifacts`：运行 `scripts/validate_audit_artifacts.py`
2. `make audit-e2e`：串行执行三类产物生成 + artifacts 校验

要求：

1. `make audit-e2e` 任一步失败必须整体失败。

### R8. CI 增加审查体系自检 Job

修改 `.github/workflows/ci.yml`，新增 `audit-system-check` job。

要求：

1. 触发条件至少包含以下文件改动：
   - `.claude/skills/**`
   - `.claude/commands/**`
   - `scripts/validate_audit_artifacts.py`
   - `scripts/schemas/**`
2. job 必须执行：
   - `make audit-artifacts`（若 evidence 不存在，应输出清晰提示并失败）
   - 相关单测（见 R9）
3. 不得 `continue-on-error`。

### R9. 单元测试覆盖（强制）

新增测试文件：

1. `tests/unit/scripts/test_audit_artifact_schema.py`
2. `tests/unit/scripts/test_audit_command_contracts.py`

要求：

1. 覆盖 schema 必填字段检查。
2. 覆盖 command frontmatter 中 `allowed-tools` 存在性。
3. 覆盖“悬空命令引用”检测（skill 中引用的命令必须存在）。
4. 覆盖“禁止吞错”检测（运行脚本不得包含 `|| true` / `exit 0` 强行放行模式）。

### R10. 文档化执行协议

新增：

1. `docs/reviews/audit-execution-protocol-v1.0.md`

要求：

1. 明确三阶段顺序：`/systematic-review -> /cross-reference-audit -> /adversarial-fix-verify`
2. 明确“完成宣称禁用词”：不得宣称“全部完成”，只能“SUBMITTED FOR REVIEW”。
3. 明确批次上限（每批 <= 5 findings）与续跑策略（必须更新 `evidence/fix-progress.md`）。

### R11. 与现有 gate-review 不冲突

要求：

1. 不得破坏 `.claude/commands/gate-review.md` 现有能力。
2. 新增命令与 `gate-review` 职责清晰：`gate-review` 是治理门禁检查，不替代三条新命令。

### R12. 变更最小化与可审计

要求：

1. 每个新增文件必须有最小必要注释，解释用途。
2. 不允许“只改文档不改可执行层”。
3. 提交说明中必须列出“新增文件清单 + 验收命令结果”。

---

## 3. Opus 执行时必须输出的证据

Opus 执行完成后，必须提供以下原始输出（不可只给摘要）：

1. `git diff --name-only`
2. `make audit-e2e`
3. `make lint`
4. `make test`
5. `uv run python scripts/validate_audit_artifacts.py`

---

## 4. 我将用于复核的验收命令

以下命令任一失败即判未通过：

```bash
make lint
make test
make audit-e2e
uv run python scripts/validate_audit_artifacts.py
rg -n "/verify" .claude/skills .claude/commands
rg -n "continue-on-error:\\s*true|\\|\\|\\s*true" .github/workflows scripts .claude/commands
```

并进行人工抽查：

1. `.claude/skills/*.md` 是否仍有不可执行的悬空指令。
2. `evidence/*.json` 是否真实可解析、字段齐全且数量一致。
3. 关键 finding 是否存在逐项 evidence，而非批量笼统结论。

---

## 5. 失败判定规则（硬性）

出现任一条，直接判定“未完成”：

1. 仅新增文档，未新增执行脚本/校验器。
2. 仅跑“总测试通过”，但无结构化 evidence 产物。
3. finding 数量不一致，或存在 dropped finding。
4. 任意命令/脚本通过 `|| true`、强制 `exit 0` 吞错。
5. skill 仍引用不存在的命令。

---

## 6. 交付格式（Opus 回传模板）

Opus 最终回复必须按如下结构：

1. `变更清单`（文件路径列表）
2. `实现说明`（按 R1-R12 对照）
3. `命令原始输出`（第 3 节 5 条命令）
4. `风险与未决项`（如有）
5. `Status: SUBMITTED FOR REVIEW`

---

## 7. 备注

这是“执行任务书”，不是讨论稿。  
若实现与本任务书冲突，以本任务书为准；如确有必要偏离，需在回传中逐条解释并给替代证据。
