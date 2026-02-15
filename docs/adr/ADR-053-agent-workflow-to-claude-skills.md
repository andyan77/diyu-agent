# ADR-053: Agent Workflow 路径方案变更 (.agent/workflows/ -> .claude/skills/ + .claude/commands/)

## Status

Accepted

## Context

governance-optimization-plan.md v2.0 (缺口 A, line 218-222) 规划了 `.agent/workflows/` 三级目录体系:

```
.agent/workflows/
  patterns/    # 8+ pattern 文件 (开发模式模板)
  guards/      # 6+ guard 文件 (编辑约束)
  workflows/   # 8+ workflow 编排文件
```

该设计基于早期对 Claude Code 上下文加载机制的假设：通过自定义目录结构向 Agent 注入行为约束。

实际工程落盘阶段发现 Claude Code 原生提供了两个一等公民机制:

- **Skills** (`.claude/skills/<name>/SKILL.md`): 可被 Skill 工具调用的结构化工作流，支持渐进披露
- **Commands** (`.claude/commands/<name>.md`): 可被 `/` 斜杠命令触发的自动化流程

两者均随仓库分发、被 Claude Code 自动发现、无需额外配置。

## Decision

**放弃 `.agent/workflows/` 自定义目录，改用 Claude Code 原生的 `.claude/skills/` + `.claude/commands/` 体系。**

具体映射:

| 原规划 (.agent/workflows/) | 实际落盘 (.claude/) | 说明 |
|---|---|---|
| `patterns/*.md` (开发模式) | 合并入 `CLAUDE.md` + `skills/` 内联 | 模式约束通过项目指令和 Skill 步骤描述传递 |
| `guards/*.md` (编辑约束) | `.claude/settings.json` hooks | Guard 逻辑由 hook 脚本 (`scripts/hooks/`) 实际执行 |
| `workflows/*.md` (流程编排) | `.claude/skills/taskcard-governance/SKILL.md` (W1-W4) | 4 个治理工作流合并为 1 个 Skill |
| (无对应) | `.claude/commands/gate-review.md` | 新增: Phase gate review 命令 |

governance-optimization-plan.md 中关于 `.agent/workflows/` 的描述视为历史设计稿，不再作为落盘要求。

## Consequences

### Positive

- 零配置: Claude Code 自动发现 `.claude/` 下的 skills 和 commands，无需手动注册
- 原生集成: Skill 工具和斜杠命令是 Claude Code 一等公民，比自定义目录有更好的上下文注入和执行语义
- 减少维护面: 从 22+ 个独立文件 (8 patterns + 6 guards + 8 workflows) 收敛为 3 个文件 (SKILL.md + gate-review.md + settings.json)
- Guard 可执行化: 原规划的 guards 是 markdown 描述，现在通过 hook 脚本实际执行 (exit 0/2 控制阻断)

### Negative

- Patterns 维度弱化: 原规划的 8 个 pattern 文件 (如"错误恢复模式"、"跨层修改模式") 没有独立文件承载，散落在 CLAUDE.md 和 Skill 步骤中，显式性降低
- 文档与实现口径漂移: governance-optimization-plan.md 的 scaffold-phase-0 文件清单、30-60-90 路线 Week 3 仍引用 `.agent/workflows/`，新参与者可能困惑

### Risks

- 如果未来需要更细粒度的 pattern 管理 (如按层、按 Phase 的模式模板)，当前 1 个 Skill + 1 个 Command 的结构可能不够。届时可拆分为多个 Skill 文件

## References

- governance-optimization-plan.md v2.0 Section 2 缺口 A (line 218-222): 原 `.agent/workflows/` 设计
- governance-optimization-plan.md v2.0 Section 3 Week 3 (line 623-625): 原路线承诺
- execution-plan-v1.0.md Section 3.2-3.4 (line 397-436): 实际落盘的 Skill + Command + Hooks 设计
- `.claude/skills/taskcard-governance/SKILL.md`: 实际 W1-W4 工作流
- `.claude/commands/gate-review.md`: 实际 gate review 命令
- `.claude/settings.json`: 实际 hook 配置
