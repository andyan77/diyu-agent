# GRC Legacy Lock Retirement & Governed Unlock — Delivery Report

任务 / task: `GKB-GRC-LEGACY-LOCK-RETIRE-AND-GOVERNED-UNLOCK-001`（账本 step **P6R**）
= 原合并任务 `GKB-LEGACY-LOCK-RETIRE-AND-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001` 的 **Phase A**（founder 拆包裁定）
下一步 / next: `GKB-3600 batch-001` 真实增量微批（~20-40 条人工撰写，**须单独 founder 授权 + Codex 三关，绝不 one-shot**）

## 1. 一句话结论 / TL;DR

Phase A **只退役旧锁 + 建 GRC 受治理解锁，零生成**。旧 semantic-pilot 失败线（44 cross-type / holdout-14 / 20-regen / v3–v4.7）登记为 `superseded_failed_line`（`use_as_p7_evidence: false`，**证据不删、无一翻案**）；GRC 新线 **P4/P5/P6** 记为有效解锁依据；建**路线级**受治理增量微批解锁（`mkc_007..046`）。**真实 3600 一条未产、零授权生成**；`direct_3600_generation` / one-shot / `generate_without_grc_pilot` 仍 forbidden；P0-00（`mkc_001..006`）held；readiness 全 false。

## 2. repo_after

| | |
|---|---|
| branch | master |
| head_before | `0433feb7fb84f4be3bbb6aefc95833cacf58cd52`（P6）|
| head_after | 见本次 commit |
| worktree_after | clean（断言门控提交）|

## 3. files_written

**新增**：`08_batch_unlock_reconciliation/`（README + reconciliation + unlock_decision + lock_surface_inventory + failed_line_provenance + unlock_evidence_index + p0_00_hold，共 7 文件）、`ci/checkers/check_grc_legacy_lock_retire_and_governed_unlock.py`、`ci/fixtures/grc_legacy_lock_retire_and_governed_unlock/`（positive + **26 negative**）、`ci/reports/…report.v0.1.json`、本报告 + receipt。
**修改**：`10_execution_progress/grc_3600_execution_plan_status.v0.1.{yaml,md}`（加 P6R 步 + route-note + re-scope P7）。
**零改**：`02_generation_brief_pack/**`、`01_generation_contracts/**`、`03_pilot/**`、`project-infra/current_workspace_status.yaml`（中央取代 + 只读登记）。

## 4. legacy_lock_retirement

| 项 | 值 |
|---|---|
| old_semantic_pilot_line_status | **superseded_failed_line**（44=semantic_fail / holdout-14=NO_GO_FOR_BATCH / 20-regen=stale / v3–v4.7=superseded）|
| legacy_line_rewritten_as_pass | **false**（无一翻案）|
| legacy_evidence_preserved | **true**（证据文件不删）|
| old_20_regen_used_as_p7_evidence | **false** |
| direct_one_shot_generation_still_forbidden | **true**（合约层 `w7_generation_baseline_lock:direct_3600_generation_allowed=false` + `shared_rules.global_forbidden` 均原样保留）|
| p0_00_held | **true**（`mkc_001..006` 不进 GKB 正文、不进解锁范围）|
| governed_microbatch_generation_allowed_under_grc | **true**（路线级；不授权生成）|

## 5. lock_surface_inventory（Codex 必修项：discovered 计数，非硬编 10）

| 锁面 | 分类 | 本任务动作 |
|---|---|---|
| `02_generation_brief_pack/00_*.yaml`（4 顶层）| legacy_read_only_superseded_by_grc_route | **none**（中央取代）|
| `02_generation_brief_pack/batch_001..014`（14 batch brief）| legacy_read_only_superseded_by_grc_route | **none**（清单登记）|
| `project-infra/current_workspace_status.yaml` | legacy_read_only_not_active_route_authority | **none**；`batch_generation_unlocked: false` 计数 = **23（live grep 重算，非硬编）** |
| `01_generation_contracts/w7_generation_baseline_lock.v0.1.yaml` | contract_immutable_preserved | **none**（direct-3600 禁令天然保留）|

## 6. generation（零生成）

`any_draft_generated: false` / `microbatch_runs_created: false` / `actual_3600_draft_count: 0` / `generation_authorized_by_this_task: false`。

## 7. checks

| 检查 | 结果 |
|---|---|
| P1 / P2 / P3 / P4 / P5 / P6 / contract-lock live | PASS ×7（checker 内 subprocess 重跑）|
| P6R checker live | PASS（error_count=0）|
| P6R checker --selftest | PASS（positive + **26 negative** 全 fail-closed，1:1 命中意图检测器）|
| P6R checker `python -O`（live / selftest）| exit 2 `FAIL-CLOSED` |
| readiness_all_false · forbidden_scope_clean | ✓ / ✓ |
| project_infra_unmodified · brief_pack_unmodified · git_changed_outside_allowed | ✓ / ✓ / `[]` |

## 8. E7.1 快照陷阱：落盘前捕获（第 4 次同型，未 trip）

**发现**：Brief §13 字面要把 `P7.status` 写成 `RE_SCOPED_TO_INCREMENTAL_MICROBATCH`。但 P6 checker（[check_3600_microbatch_briefing_go_nogo.py:343](../../ci/checkers/check_3600_microbatch_briefing_go_nogo.py#L343)）因 `go_decision=GO_TO_P7` **硬要求 `P7.status ∈ {NEXT,IN_PROGRESS,DONE}`**；该 checker 在禁改区、且本任务 §10.1 又要求它 live PASS —— **Brief 内部自相矛盾**。

**处置**（founder AskUserQuestion 裁定「status 保持 NEXT + 加 re-scoping 字段」）：`P7.status` 维持 `NEXT`；re-scope 用 `unlock_kind=governed_incremental_microbatch` + `one_shot_3600_generation_allowed=false` 等字段表达。**零 checker 改动**；治理含义 100% 保留；实测 P4/P5/P6 三 checker 推进后仍 exit 0。**教训固化**：写账本 status 永远用不 trip 下游 UNBLOCKED_STATES 守卫的编码，绝不为一个字面 label 破坏上游 checker。

## 9. execution_progress_ledger

新增 **P6R**（GKB-GRC-LEGACY-LOCK-RETIRE-AND-GOVERNED-UNLOCK-001，DONE）+ `grc_legacy_lock_retire_route_note`；
**P7 re-scoped**：`unlock_kind: governed_incremental_microbatch`，status 仍 `NEXT`（未开工），`one_shot_3600_generation_allowed: false`；
`generation_unlocked: false` 全局锁保持；P8 仍 `PLANNED_BLOCKED_BY_P7`。

## 10. 允许声明 / must-not-claim

**允许**：`legacy_semantic_pilot_lock_retired` / `grc_route_recorded_as_valid_unlock_evidence` / `governed_microbatch_generation_allowed_under_grc`。

**禁止（仍锁）**：`generation_3600_completed` / `generation_3600_unlocked` / `generation_allowed` / `one_shot_3600_generation` / `candidatepack_ready` / `KE_ready` / `RAG_ready` / `DIFY_ready` / `production_ready`。

## 11. next_real_action_unlocked

`GKB-3600 batch-001` 真实增量微批（~20-40 条人工撰写、非模板、`mkc_007..046`、逐条双门）—— **须单独 founder 授权 + Codex Prompt Pre-Review 三关；绝不 one-shot 3600。** P6R 未授权、未执行任何生成。
