# P7C-BRIEF — Scoped 120 Content-Production Microbatch · Brief / Go-No-Go · Delivery Report

任务 / task: `GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-BRIEF-AND-GO-NOGO-001`（账本 step **P7C-BRIEF**）
授权 / auth: founder 授权 + Codex Prompt Pre-Review **CONDITIONAL_PASS**（6 条必修项已应用；note 1 分叉由 founder 裁定 = **加锚点**）
性质 / kind: route_planning + generation_assignment + go_no_go_checker（**不生成任何草稿**）

## 0. 一句话

把 scoped 120 内容生产微批设计成**可执行/可检查/可停机**的施工包:**120 个 future assignment**(mkc_007..046 各 ≥3),按 P0 组 / 生成模式(36/36/24/24) / 6 类创意模式(每类≥10) / owner / 命题锚定 / 事实绑定 分配,**引用全部真实**;go/no-go = **GO_TO_SCOPED_120_GENERATION_BRIEF**(只解锁下一步 brief + founder 授权,**不授权当前生成**)。**0 / 120 草稿已生成。**

## 1. repo_after

| | |
|---|---|
| branch | master |
| head_before | `651d80f`（P7B）|
| head_after | 见本次 commit |
| worktree_after | clean（断言门控提交）|

## 2. Codex 6 条必修项 —— 逐条落实

| # | 必修项 | 落实 |
|---|---|---|
| 1 | ledger route-sync（二选一）| **founder 裁定 = 加锚点**。Codex 推荐改已提交 P7B checker,但它不在本任务写面且 §6 禁自扩写面 → 保留 P7A/P7/P7B/P7C 锚点、**新增 P7C-BRIEF(DONE)/P7C-GEN(NEXT)**,P7D→`BLOCKED_BY_P7C_GEN`,`route_migration_2` 记录 |
| 2 | P7A 不改 status | ✅ `P7A.status=DONE`、`classification=agent_authored_quality_probe_pass` 原样 |
| 3 | P7C-GEN 只解锁下一步 brief | ✅ go/no-go `next_unlocked=P7C_GEN_execution_brief_and_founder_authorization_only`、`generation_authorized_now=false` |
| 4 | 引用必须真实存在 | ✅ checker 逐条查:`proposition_refs`∈P5(160)、gold/anti∈goldset、pattern∈P7B(6)、mode∈P7B(4)、owner∈P5、cluster∈mkc_007..046 |
| 5 | 独立重算不信 manifest | ✅ checker 从 assignment plan 重算 120/覆盖/每簇≥2/模式≥10/pattern≥10/P0-00 缺席/每模式事实规则/readiness |
| 6 | 上游 checker 快照策略 | ✅ 10 上游走**双快照**(P1–P6R+contract-lock 无 `07_microbatch_runs` 快照;P7A+P7B 保留 proof+alignment 快照);无白名单 |

## 3. 120-assignment 计划（核心，全部真实引用）

- **总数**:120（mkc_007..046 各 3；每簇 ≥2 ✓）
- **生成模式分布**:creative_prototype **36** / fact_slot_script **36** / evidence_bound_candidate **24** / display_solution **24**（每模式 ≥10 ✓，且遵守 P0 default_modes：display 只在 P0_04、evidence_bound 只在 P0_03、creative_prototype 不在 P0_03）
- **创意模式**:6 类全部 ≥10（enterprise_narrative 10 / role_voice 11 / visual_scene 12 / display_to_content 23 / product_role_story 27 / platform_expression 37；遵守 P0→pattern 允许集）
- **P0-00 / mkc_001..006**:未进任何正文 assignment ✓
- **每模式事实规则**:creative_prototype 不要求品牌事实 · fact_slot_script 缺事实留槽不编造 · evidence_bound_candidate 要求证据 · display_solution 最终落地需场景事实
- **引用真实性**:所有 `proposition_refs`（PROP-V1-NNN）、`gold_reference_case_refs`/`anti_gold_avoidance_refs`（GRC-P001-MKCxxx-{POS,ANTI,BDR}-001）、`creative_pattern_refs`、`generation_mode`、owner 均为真实已提交 id，checker 查真存在，**无编造**

## 4. go/no-go

**GO_TO_SCOPED_120_GENERATION_BRIEF** —— 只解锁下一步 `GKB-SCOPED-120-CONTENT-PRODUCTION-MICROBATCH-GENERATION-001`（P7C-GEN）的 **execution brief + founder 授权**,`generation_authorized_now=false`。**不等于**现在可生成 120。

## 5. checks（全绿）

| 检查 | 结果 |
|---|---|
| P1–P5 + contract-lock live | **PASS** |
| P6 / P6R live | **PASS**（无 `07_microbatch_runs` 快照）|
| P7A / P7B live | **PASS**（保留 proof+alignment 快照）|
| **P7C checker live** | **PASS**（error_count=0；10/10 上游 priors exit 0）|
| P7C checker --selftest | **PASS**（positive + **35 negative** 全 fail-closed）|
| P7C checker `python -O` | **exit 2 FAIL_CLOSED** |
| git_changed_outside_allowed / 已提交 P7A·P7B 产物被改 | `[]` / `[]` |
| exact stage（无 `git add .`/`-A`/`commit -a`）| ✅ |

## 6. execution_progress_ledger

steps = `[P1..P6R, P7A, P7B, P7(anchor), P7C(anchor), P7C-BRIEF, P7C-GEN, P7D, P8]`；P1–P6R + P7A + P7B + **P7C-BRIEF = DONE**；**P7C-GEN = NEXT**（生成未授权）；**P7D = BLOCKED_BY_P7C_GEN**；**P8 = BLOCKED_BY_P7D**；锚点 P7A/P7/P7B/P7C 原样；`generation_unlocked: false`；`route_migration_2.no_old_checker_edited=true`、`no_readiness_flipped=true`。

## 7. next_real_action

**P7C-GEN = `GKB-SCOPED-120-CONTENT-PRODUCTION-MICROBATCH-GENERATION-001`**：scoped 120 真实生成的 execution brief + **单独 founder 授权 + Codex 三关**;最多 **120**(320 需另行 founder 授权);绝不 one-shot 3600;`proof_microbatch_001` 与本 scoped 120 除非另行授权**不计入 3600**。**禁止声明**:`scoped_120_generated` / `generation_3600_completed` / `candidatepack_ready` / `KE_ready` / `RAG_ready` / `DIFY_ready` / `production_ready`。
