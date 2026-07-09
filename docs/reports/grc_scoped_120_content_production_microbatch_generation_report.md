# P7C-GEN — Scoped 120 Content-Production Microbatch · Generation · Delivery Report

任务 / task: `GKB-SCOPED-120-CONTENT-PRODUCTION-MICROBATCH-GENERATION-001`（账本 step **P7C-GEN**）
授权 / auth: founder 授权 + Codex Prompt Pre-Review **CONDITIONAL_PASS**（`safe_to_execute: yes_after_required_fixes`；6 条必修项已应用）
性质 / kind: controlled_generation + mode/creative gate + checker（**真实生成 120 条**，不授权 320/3600/CandidatePack/Four-Gate/KE/Serving/RAG/DIFY/production）

## 0. 一句话

真实生成 **120 条** scoped 内容生产结构化草稿（每条对应 1 个 P7C-BRIEF assignment），mode 分布 **36/36/24/24**，逐条正文过**确定性机器闸**（≥350 字 / 反抄 LCS gold<16·canary<18·proof<18·跨稿<18 / 无治理元词汇 / 无价格货号真实事实 / 簇指纹锚定 / 按模式的事实-槽位-降级规则 / 引用完整性）。**创意「动人」质量不由本任务证明，全部留待 P7C-REVIEW（人审）**；readiness 全 false；不计入 3600；未解锁任何下游。

## 1. repo_after

| | |
|---|---|
| branch | master |
| head_before | `f99e960`（P7C-BRIEF）|
| head_after | 见本次 commit |
| worktree_after | clean（断言门控提交）|

## 2. Codex 6 条必修项 —— 逐条落实

| # | 必修项 | 落实 |
|---|---|---|
| 1 | 路线相位快照 | P7C-GEN checker 对已提交 **P7C-BRIEF / P7A / P7B** 三闸用**生成前快照**（移除 `scoped_content_microbatch_120_001`、账本重置到 HEAD），使它们硬读的 `P7C-GEN==NEXT`/`P7D==BLOCKED_BY_P7C_GEN`/`run_dirs=={proof}` 仍成立；**未改任何已提交 checker** |
| 2 | P7A 锚点不动 | `P7A.status=DONE`、`classification=agent_authored_quality_probe_pass` 原样（Brief §14 的 `DONE_AS_QUALITY_PROBE` 按 Codex 覆盖为保锚点）|
| 3 | assignment 不可变 | checker 校验 `07_microbatch_briefing/scoped_content_microbatch_120/**`+P7B 对齐+proof+全部已提交 checker 在 live git 面**未被改动** |
| 4 | 引用完整性 | 逐条重校 `assignment_id/target_output_id/cluster/p0_group/mode/proposition_refs/gold+anti/creative_pattern/owner` 与所消费的 P7C-BRIEF assignment **完全一致** |
| 5 | 正文重算不信报告 | 每条质量闸**从正文重算**（字数/反抄LCS/元词汇/真实事实/抽象堆叠/簇指纹/课件脚手架/按模式事实规则）；9 份 gate 报告须同时声明 PASS 且与重算一致 |
| 6 | 来路诚实 | `generation_receipt.execution_ai_authored=true`、`automatic_generator_capability_proven=false`；**未**重新包装成"自动生成器能力已证明" |

## 3. 120 条生成（核心）

- **总数**：120（mkc_007..046 各 3；每 assignment exactly 一条草稿；无孤儿/无缺漏/无重复 target_output_id）
- **模式分布**：creative_prototype **36** / fact_slot_script **36** / evidence_bound_candidate **24** / display_solution **24**
- **P0-00 / mkc_001..006**：未作任何正文草稿 ✓
- **owner 路由**：GeneralKnowledgeBase 57 / EvidencePolicyOutbox 32 / GovernanceOutbox 14 / ExecutionAssetOutbox 15 / SourceGapLedger 2；owner→kind/layer 一致；EvidencePolicyOutbox 不落 GKB/TBox ✓
- **按模式事实规则**：creative_prototype 无需品牌事实 · fact_slot_script 缺事实写成显式 `【…】` 槽位不编造 · evidence_bound_candidate 无源硬结论降级/挂证据槽 · display_solution 最终落地场景事实留槽

## 4. 生成来路（诚实披露，全部 120 条均过确定性整型闸）

> **整型闸（integrity gate）= 已提交的确定性 checker**。它证明**结构 + 反抄 + 治理合规 + 引用完整 + 反课件启发式**通过；**它不证明创意质量**——这是设计上的诚实边界（确定性审计对叙事型质量是"瞎子"）。

| 来路 | 条数 | 说明 |
|---|---|---|
| 子代理生成/修复 + **独立对抗质检 PASS** | **111** | 240 agent 初生成 + 两轮对抗修复；对抗质检员默认怀疑，专抓课件腔/治理话术漏入/编造事实/无画面 |
| 子代理修复、正文已更新、**独立对抗复检待补** | **2** | A033/A102：会话额度限制致对抗复检未及重跑，仅过确定性闸 |
| **执行 AI 主循环亲撰**（rate-limit fallback）、过确定性闸、未经独立对抗复检 | **7** | A032/A035/A037/A059/A062/A101/A106：会话额度用尽后由主循环撰写，逐条对着确定性闸迭代至干净 |

**后两类共 9 条列为 P7C-REVIEW 首查项。** 创意质量对全部 120 条一律留待 P7C-REVIEW 人审。

## 5. 修复循环（防假绿实证）

| 轮 | verify-FAIL | 确定性机器闸-FAIL |
|---|---|---|
| 初生成（240 agent）| 44/120 | 11/120 |
| 第1轮修复（48 条，带具体反馈）| 9 | 4 |
| 第2轮修复（11 条，带逐字 avoid 片段）| 命中额度限制部分完成 | — |
| 主循环补齐 7 条 + 合并 | — | **0/120** |

典型抓点：mkc_017 三条抄了 gold 里的英文词 `interaction intensity`；A037 与 A038 撞同一句槽位措辞；元框架术语被当旁白标签点名（课件腔）——均已修掉或改写。

## 6. checks（全绿）

| 检查 | 结果 |
|---|---|
| P1–P5 + contract-lock live | **PASS** |
| P6 / P6R live | **PASS**（无 `07_microbatch_runs` 快照）|
| P7A / P7B / P7C-BRIEF live | **PASS**（生成前快照，账本重置到 HEAD）|
| **P7C-GEN checker live** | **PASS**（error_count=0；11/11 上游 priors exit 0；draft 120；mode 36/36/24/24）|
| P7C-GEN checker --selftest | **PASS**（positive + **49 negative** 全 fail-closed）|
| P7C-GEN checker `python -O` | **exit 2 FAIL_CLOSED** |
| git_changed_outside_allowed / 已提交产物被改 | `[]` / `[]` |
| exact stage（无 `git add .`/`-A`/`commit -a`）| ✅ |

## 7. execution_progress_ledger

P1–P6R + P7A + P7B + P7C-BRIEF + **P7C-GEN = DONE**；**P7C-REVIEW = NEXT**；**P7D = BLOCKED_BY_P7C_REVIEW**；**P8 = BLOCKED_BY_P7D**；锚点 P7A（DONE+classification）/P7/P7B/P7C 原样；`generation_unlocked: false`；readiness 全 false；`route_migration_3.no_old_checker_edited=true`、`no_readiness_flipped=true`。

## 8. next_real_action

**P7C-REVIEW = `GKB-SCOPED-120-QUALITY-REVIEW-AND-SCALE-DECISION-001`**：scoped 120 质量评审（**首查上述 9 条待补/fallback**）+ 规模决策（是否/如何扩到 320/3600）。**须单独 founder 授权 + Codex 三关**；不生成、不翻 readiness。**禁止声明**：`generation_3600_completed` / `generation_3600_unlocked` / `candidatepack_ready` / `KE_ready` / `RAG_ready` / `DIFY_ready` / `production_ready`。
