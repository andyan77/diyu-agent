# Opus 执行任务书：SKILLS 缺口补全（治理对齐 + 官方最佳实践）

日期：2026-02-15  
目标：按 `docs/governance/governance-optimization-plan.md` 的 SKILLS 要求完成真实落盘、真实运行、可审计闭环，并对齐官方 Skills 构建最佳实践。

---

## 0. 权威依据（必须逐条对齐）

1. `docs/governance/governance-optimization-plan.md:616`  
   `.claude/skills/` 至少 4 个核心 pattern
2. `docs/governance/governance-optimization-plan.md:617`  
   `.claude/skills/ guards` 至少 4 个核心 guard
3. `docs/governance/governance-optimization-plan.md:980-1008`  
   SKILLS 工作流固化要求（W1-W4 + 渐进披露 + 子 Agent 专职 + 交接产物 + session 审计可回放）
4. `docs/governance/execution-plan-v1.0.md:401-449`  
   Stage 3 退出条件（Skill 可执行、/gate-review 可输出、Agent 扩展、hooks 可运行、.audit 有日志）

官方最佳实践依据（按 Skill Creator）：

1. SKILL frontmatter 仅保留 `name` + `description`
2. 技能目录采用渐进披露：`SKILL.md` + `references/` + `scripts/` + `agents/openai.yaml`
3. 用脚本保证可重复执行，避免“文字流程不可执行”
4. 对技能做结构与契约校验（quick validate + repo 本地测试）

---

## 1. 当前阻断缺口（需全部关闭）

1. `taskcard-governance` 仅有流程描述，缺少“每步交接产物”与“session 可回放”落盘契约。  
2. “至少 4 个 guard”未在 Skills 层形成清晰、可调用、可验证的 guard 技能集合。  
3. 3 个 Agent 的 task-card-aware 扩展要求未形成可验证证据链（文档有要求，仓库缺显式落盘与测试）。  
4. Skills 目录结构未完全对齐官方实践（frontmatter、agents/openai.yaml、references/scripts 的一致性与校验未体系化）。

---

## 2. 强制交付（DoD）

以下 D1-D12 任一不满足，判定未完成。

### D1. 保证 4 个核心 pattern（可执行）

保留并规范以下 4 个技能：

1. `.claude/skills/taskcard-governance/SKILL.md`
2. `.claude/skills/systematic-review/SKILL.md`
3. `.claude/skills/cross-reference-audit/SKILL.md`
4. `.claude/skills/adversarial-fix-verification/SKILL.md`

要求：

1. 每个 SKILL frontmatter 仅含 `name`、`description`。  
2. `description` 必须包含“何时触发”语义，不把触发条件放在正文。

### D2. 新增 4 个核心 guard skills（满足治理 616/617）

新增目录（每个都含 `SKILL.md` + `agents/openai.yaml` + 可执行脚本）：

1. `.claude/skills/guard-layer-boundary/`
2. `.claude/skills/guard-port-compat/`
3. `.claude/skills/guard-migration-safety/`
4. `.claude/skills/guard-taskcard-schema/`

要求：

1. 每个 guard skill 必须绑定现有脚本真实执行（不得 echo 占位）。  
2. 每个 guard skill 必须定义输入、输出、失败条件、修复建议。

### D3. taskcard-governance 技能补齐“闭环执行层”

在 `.claude/skills/taskcard-governance/` 新增：

1. `scripts/run_w1_schema_normalization.sh`
2. `scripts/run_w2_traceability_link.sh`
3. `scripts/run_w3_acceptance_normalizer.sh`
4. `scripts/run_w4_evidence_gate.sh`
5. `scripts/run_all.sh`（按 W1->W2->W3->W4 顺序执行）
6. `references/`（把冗长规则移出 SKILL.md，保持正文精简）

每个 W* 脚本必须落盘以下产物（session 级）：

`evidence/skills/taskcard-governance/<session-id>/W*/`

1. `input.json`
2. `output.json`
3. `failure.md`（失败时必须存在）
4. `next-step.md`

### D4. 渐进披露与专职角色落盘

在 `taskcard-governance/SKILL.md` 中明确：

1. 每一轮仅加载当前步骤必要 references（渐进披露）  
2. W1/W2/W3/W4 对应专职角色（拆卡/追踪/验收/门禁）  
3. 禁止职责混用规则

### D5. session 审计与回放

新增：

1. `scripts/skills/skill_session_logger.py`
2. `scripts/skills/replay_skill_session.py`

要求：

1. 每次 run_all 都写入 `.audit/skill-session-<ts>.jsonl`  
2. `replay_skill_session.py` 可回放 session 并输出步骤摘要

### D6. Agent 扩展落盘（执行计划 Stage 3 对齐）

修改：

1. `.claude/agents/diyu-architect.md`
2. `.claude/agents/diyu-tdd-guide.md`
3. `.claude/agents/diyu-security-reviewer.md`

要求：

1. 显式加入 task-card-aware section（对应 execution-plan 3.1）  
2. 与写入边界一致（architect->matrix, tdd->task-cards, security->read-only review）  
3. 添加可测试关键字锚点，供自动化测试断言

### D7. Skills 元数据（官方实践）

每个 skill 目录新增或刷新：

`agents/openai.yaml`

要求：

1. 至少包含 `interface.display_name`、`interface.short_description`、`interface.default_prompt`  
2. `default_prompt` 必须显式包含 `$skill-name`  
3. 字符串字段全部加引号

### D8. 统一校验器

新增：

1. `scripts/skills/validate_skills_governance.py`

必须检查：

1. 4 pattern + 4 guard 技能存在  
2. 每个 SKILL frontmatter 合规（仅 name/description）  
3. 每个技能有 `agents/openai.yaml` 且字段合法  
4. `taskcard-governance` 每步有交接产物  
5. 最新 skill session 日志存在且可回放  
6. 3 个 Agent 的 task-card-aware 扩展锚点存在

### D9. 测试补齐

新增测试：

1. `tests/unit/scripts/test_skills_governance_requirements.py`
2. `tests/unit/scripts/test_skills_best_practices.py`
3. `tests/unit/scripts/test_taskcard_workflow_handoff.py`

测试必须覆盖：

1. 治理条款 616/617/980-1008/401-449 的落盘断言  
2. 8 个 skills 的存在与契约  
3. session 可回放  
4. 真实脚本调用（禁止 `echo` 假执行）

### D10. Makefile 与 CI 接入

修改：

1. `Makefile` 新增：
   - `skills-validate`
   - `skills-smoke`
2. `.github/workflows/ci.yml` 新增 `skills-governance-check` job

CI job 必跑：

1. `make skills-validate`
2. `make skills-smoke`
3. 以上测试文件

并要求：

1. 不得 `continue-on-error`  
2. 不得 `|| true` 吞错

### D11. 文档对齐

更新：

1. `docs/governance/governance-optimization-plan.md`（状态/说明更新，不改原则）
2. `docs/governance/execution-plan-v1.0.md`（Stage 3 证据链接补齐）
3. 新增 `docs/reviews/skills-gap-closure-report-v1.0.md`

报告必须列出：

1. 条款 -> 文件 -> 证据命令 -> 结果

### D12. 不允许伪闭环

禁止行为：

1. 仅补文档不补可执行脚本  
2. 仅补脚本不补测试  
3. 只给“通过”结论，不给原始命令输出

---

## 3. 推荐实现顺序（Opus 执行）

1. Skills 结构规范化（D1+D7）  
2. 4 guard skills 落盘（D2）  
3. taskcard-governance 执行层 + handoff（D3+D4）  
4. session logger + replay（D5）  
5. 3 个 Agent 扩展（D6）  
6. 校验器 + 测试（D8+D9）  
7. Make + CI（D10）  
8. 文档与收尾（D11）

---

## 4. Opus 必须回传的原始输出

以下命令输出必须完整回传（不可只贴摘要）：

```bash
git diff --name-only
make skills-validate
make skills-smoke
make lint
make test
python3 scripts/skills/validate_skills_governance.py
python3 scripts/skills/replay_skill_session.py --latest
```

---

## 5. 验收判定（Reviewer 使用）

通过条件：

1. D1-D12 全部满足  
2. 回传命令全绿  
3. `evidence/skills/taskcard-governance/<session-id>/W1..W4` 产物齐全  
4. `.audit/skill-session-*.jsonl` 可回放

失败条件（任一触发即不通过）：

1. 少于 4 个 guard skills  
2. 任一技能无 `agents/openai.yaml`  
3. 交接产物不完整（缺 input/output/failure/next-step 任一）  
4. 发现占位执行（`echo PASS` 等）替代真实检查  
5. CI 或 Make 通过依赖吞错逻辑

---

## 6. Opus 回传模板（固定）

1. `变更清单`（按 D1-D12 分组）  
2. `条款映射`（治理条款 -> 文件 -> 证据）  
3. `原始命令输出`（第 4 节）  
4. `残余风险`（若有）  
5. `Status: SUBMITTED FOR REVIEW`
