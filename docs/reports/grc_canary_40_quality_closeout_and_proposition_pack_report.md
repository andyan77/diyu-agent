# GRC Canary-40 Quality Closeout & Proposition Pack v1 — Delivery Report

任务 / task: `GKB-CANARY-40-QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001`（P5，supersede 原 `...FOUNDER-QUALITY-REVIEW-CLOSEOUT-001`）
下一步 / next: `GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001`（P6，**唯一**被 P5 解锁；3600 generation 仍锁）

## 1. 一句话结论 / TL;DR

**不重复评审、不重新打分**：吸收 founder 汇总的两位专家共识做质量收口，并把 40 条 canary 抽成
`proposition_pack_v1`（**160 条命题**，每簇 4 条）。每条命题带**可机器核验的 source_text_span**（逐字子串 + 偏移），
owner 做了**命题层拆分**（GKB/EvidencePolicyOutbox/GovernanceOutbox/ExecutionAssetOutbox/SourceGapLedger）。
**未建 Object、未解锁 3600、readiness 全 false，只解锁 P6 briefing。**

## 2. repo_after

| | |
|---|---|
| branch | master |
| head_before | `9b8769fae54c71501372e68f8876aa28d8edb24f` |
| head_after | 见本次 commit |
| worktree_after | clean（断言门控提交）|

## 3. files_written

**新增**：`06_canary_runs/canary_40_001/review_closeout/`（quality_closeout yaml+md + expert_review_input_digest + decision）、
`06_canary_runs/canary_40_001/proposition_pack_v1/`（manifest + cluster_propositions + owner/epistemic 矩阵 +
source_trace/failure_signal/downstream_effect 三 index + closeout）、
`ci/checkers/check_canary_40_quality_closeout_and_proposition_pack.py`、
`ci/fixtures/canary_40_quality_closeout_and_proposition_pack/`（positive + 20 negative）、
`ci/reports/canary_40_quality_closeout_and_proposition_pack_report.v0.1.json`、本报告 + receipt。

**修改**：`10_execution_progress/*.{yaml,md}`（P5 DONE superseded / P6 briefing NEXT / 3600-gen 降 P7 blocked + `canary_p5_route_note`）、
`ci/checkers/check_canary_40_generation_and_gate.py`（P4 checker 快照过期缺陷修复，见 §7，**founder 授权扩 allowed-writes**）。

## 4. quality_closeout（Brief §8）

| 项 | 值 |
|---|---|
| expert_review_count | 2 |
| review_mode / repeated_review_performed | absorbed_existing_expert_reviews / **false** |
| review_input_form（Codex note 4）| founder_provided_expert_consensus_summary；`raw_expert_review_files_available: false` |
| canary_as_generation_probe / as_formal_knowledge | pass / **false** |
| candidatepack_ready / generation_3600_unlocked | false / false |
| next_required_asset | proposition_pack_v1 |

保留专家共识：P0-03/P0-04 最强；P0-02/P0-05 需命题层 owner 拆分；boundary language 偏重（后续分 domain body 与 risk sidecar）；relation=design hints 非 ontology edges；下一步是抽命题不是再评审。

## 5. proposition_pack_v1（checker 独立重算）

| 项 | 值 |
|---|---|
| cluster_count / coverage | 40 / mkc_007..mkc_046 |
| total / per-cluster | **160** / 4（范围 3–5，闸校 clusters×3..5 = 120..200）|
| owner_candidate 分布 | GeneralKnowledgeBase 60 · EvidencePolicyOutbox 42 · GovernanceOutbox 34 · ExecutionAssetOutbox 15 · SourceGapLedger 9 |
| epistemic_class 分布 | 与 owner 一一对齐（0 不一致）|
| **source_text_span** | 160/160 **逐字子串 + 偏移正确**（Codex note 3 机器核验）|
| EvidencePolicyOutbox → GKB 违规 | **0** |
| accepted_domain_knowledge=true / candidatepack_ready=true | 0 / 0 |

owner 命题层拆分：GKB 簇里 claim/证据边界命题拆到 EvidencePolicyOutbox、风险红线命题拆到 GovernanceOutbox、缺来源命题拆到 SourceGapLedger——正是专家要的拆分。

## 6. checks

| 检查 | 结果 |
|---|---|
| P1 / P2 / P3 / P4 / contract-lock live | PASS ×5 |
| P5 checker live | PASS（error_count=0）|
| P5 checker --selftest | PASS（positive + 20 negative 全 fail-closed）|
| P5 checker `python -O`（live / selftest）| exit 2 `FAIL-CLOSED` |
| yaml/json parse · forbidden_scope_clean · exact_stage_only | ✓ / ✓ / ✓ |

## 7. P4 checker 快照过期缺陷修复（founder 授权扩 allowed-writes）

**发现**：P4 的 checker 硬编了「下一步必须叫 `GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001` 且状态=NEXT」。
P5 按 Codex note 1+2 把该步 supersede 改名并推进为 DONE、下一步换成 3600 briefing → P4 checker 报「step missing」。
**根因**：checker 断言了具体下游路线的名字与 NEXT 状态，是随路线推进即过期的快照（E7.1 同型，与 P3 修 P2 checker 完全同类）。

**处置**（founder 裁定「授权最小修复」，AskUserQuestion）：把该断言改成
「P4 DONE ⇒ P5（复审收口任务**或其 supersede 后的任务**）已解锁（NEXT 或已推进），不写死具体名字」。
1 处 ~6 行，未动 P4 其他逻辑；P4 checker live + selftest（原 fixtures 不变）+ `python -O` exit 2 全绿。这是对 P5 §6 allowed-writes 的一处 founder 显式批准的最小扩展（`ci/checkers/check_canary_40_generation_and_gate.py`）。

## 8. execution_progress_ledger（Codex note 1+2）

P1/P2/P3/P4/P5 DONE / **P6 = GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001（NEXT）** /
P7 = GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001（PLANNED_BLOCKED_BY_P6，**3600 generation 仍锁**）/
P8 = GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001（PLANNED_BLOCKED_BY_P7）。
P5 supersede 记录在 `supersedes_task_id` + `canary_p5_route_note`。checker fail-closed：3600 generation 被置 NEXT 即失败（negative_16 实测）。

## 9. 允许声明 / must-not-claim

**允许**：`canary_40_quality_closeout_landed` / `expert_review_input_absorbed` / `proposition_pack_v1_landed` / `ready_for_p6_microbatch_briefing`。

**禁止（仍锁）**：`generation_3600_completed` / `generation_3600_unlocked` / `candidatepack_ready` / `KE_ready` / `RAG_ready` / `DIFY_ready` / `production_ready`。

## 10. next_real_action_unlocked

`GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001`（P6）。proposition_pack_v1 是**派生审查资产**（derived_review_asset），
**非** accepted domain knowledge、**非** CandidatePack-ready、**非** production；**本身不是 3600 生成授权**，3600 由 P6 briefing/go-no-go 裁决。
