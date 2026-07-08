# GRC Canary-40 Generation & Gate — Delivery Report

任务 / task: `GKB-CANARY-40-GENERATION-AND-GATE-001`（P4）
下一步 / next: `GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001`（P5，**唯一**被 P4 解锁的一步；3600 仍锁）

## 1. 一句话结论 / TL;DR

按 canonical 语料 + judge 校准，**生成 40 条受控 canary 草稿**（每个 formal 簇 `mkc_007..mkc_046` 恰好 1 条），
全部状态 `gpt_generated_structured_draft`，并过机器闸（数量/覆盖/owner-layer/证据路由/抄袭/去重/治理泄漏/readiness）。
**未生成 3600、未建 CandidatePack、未建 Object、readiness 全 false，只解锁 P5 founder 质量复审。**

## 2. repo_after

| | |
|---|---|
| branch | master |
| head_before | `46927856bc04222a3188aab6120acf823fc59c6c` |
| head_after | 见本次 commit |
| worktree_after | clean（断言门控提交）|

## 3. files_written

**新增**：`06_canary_runs/canary_40_001/`（candidate_cards + rich_body_blocks + relation_candidates.csv +
manifest + receipt + judge/dedupe/owner_layer/style_copy/readiness 五份报告 + closeout）、
`ci/checkers/check_canary_40_generation_and_gate.py`、`ci/fixtures/canary_40_generation_and_gate/`（positive + 18 negative）、
`ci/reports/canary_40_generation_and_gate_report.v0.1.json`、本报告 + receipt。

**修改**：`10_execution_progress/*.{yaml,md}`（P4 DONE / P5=founder 复审 NEXT / 3600 微批降为 P6 blocked + `canary_p4_route_note`）。

## 4. canary_counts（checker 独立重算）

| 计数 | 值 |
|---|---|
| expected_total / actual_total | 40 / 40 |
| cluster_coverage / per_cluster | mkc_007..mkc_046 / 每簇恰好 1 |
| generation_status | 全部 `gpt_generated_structured_draft` |
| owner 分布 | GeneralKnowledgeBase 25 · EvidencePolicyOutbox 5 · ExecutionAssetOutbox 6 · GovernanceOutbox 4 |
| EvidencePolicyOutbox 簇 / 并入 GKB | mkc_021/026/027/028/044（5）/ **0** |

owner / candidate_kind 逐簇与金样 `routing_contract` 一致（source-traced，非硬贴）。

## 5. quality_gate（机器闸）

| 检查 | 结果 |
|---|---|
| judge（每条有 expected verdict 字段 + hard gates 引用）| PASS |
| owner_layer（owner/kind/layer 契约合法 + owner-layer 一致 + EPO 不入 GKB）| PASS |
| dedupe（40 条 body 哈希唯一，最大跨簇公共子串 14 < 18）| PASS |
| style_copy（gold 抄袭：去标题最大公共子串 12 < 16；无抽象风格词堆叠）| PASS |
| no_template_reuse（跨簇模板复用 14 < 18）| PASS |
| no_governance_text（正文无治理/控制面词）| PASS |
| no_real_instance_fact（无品牌/货号/价格/库存/门店/人物事实）| PASS |
| body 标准（每条 ≥350 字，最短 380；含 cluster-specific 机制 + 领域密度指纹）| PASS |
| readiness_false | PASS（9 flag 全 false）|

## 6. checks

| 检查 | 结果 |
|---|---|
| P1 corpus / P2 alignment / P3 judge / contract-lock live | PASS / PASS / PASS / PASS |
| P4 checker live | PASS（error_count=0）|
| P4 checker --selftest | PASS（positive + 18 negative 全 fail-closed）|
| P4 checker `python -O`（--live / --selftest）| exit 2 `FAIL-CLOSED` |
| yaml/json/csv parse · forbidden_scope_clean · exact_stage_only | ✓ / ✓ / ✓ |

## 7. Codex Prompt Pre-Review 四条必修项落实

1. **note1（3600 路由歧义）**：P4 PASS 只解锁 `GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001`（新 P5）；
   3600 微批（`GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001`）降为 P6 `PLANNED_BLOCKED_BY_P5`，**checker fail-closed**：
   若该任务被置 `NEXT` 直接失败（negative_14 实测拦下）。ledger 新增 `canary_p4_route_note`。
2. **note2（canary 专项授权边界）**：manifest/receipt/checker 断言
   `canary_generation_authorized_for_this_task_only: true` / `global_generation_allowed: false` / `generation_3600_unlocked: false`。
3. **note3（外部资源禁令）**：`external_resources_allowed` / `embedding_allowed` / `web_access_allowed` / `source_repo_live_dependency` 全 false（manifest + 卡内 source_policy）。
4. **note4（路由负例）**：新增 fixture `negative_14_3600_marked_next_after_canary_pass` → checker 实测 FAIL。

## 8. execution_progress_ledger

P1 DONE / P2 DONE / P3 DONE / P4 DONE / **P5 NEXT（founder 质量复审）** / P6 PLANNED_BLOCKED_BY_P5（3600 微批）/
P7 PLANNED_BLOCKED_BY_P6（3600 质量去重）/ P8 RESERVED_NOT_EXECUTABLE。路线权威 = 本 ledger。

## 9. 允许声明 / must-not-claim

**允许**：`canary_40_generated` / `canary_40_machine_gated` / `ready_for_canary_40_quality_review`。

**禁止（仍锁）**：`generation_3600_unlocked` / `global_generation_allowed` / `candidatepack_ready` /
`KE_ready` / `RAG_ready` / `DIFY_ready` / `production_ready` / `generation_eligible` / `production_servable`。

## 10. next_real_action_unlocked

`GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001`（P5，founder 质量复审收口）。
**不**解锁 3600 / CandidatePack / Four-Gate / KE / Serving / RAG / DIFY / production。
这 40 条是 `gpt_generated_structured_draft` 探针，**非** accepted domain knowledge、**非** CandidatePack-ready、**非** production；
是否可作后续训练正样本，须经 P5 founder 复审裁定。
