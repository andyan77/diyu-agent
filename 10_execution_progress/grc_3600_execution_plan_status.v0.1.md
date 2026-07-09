# GRC 3600 Execution Plan — Status Ledger

> ledger_version v0.1 · roadmap_authority: founder_approved 2026-07-08
> 机器可读真源：[grc_3600_execution_plan_status.v0.1.yaml](grc_3600_execution_plan_status.v0.1.yaml)
> **每个后续执行 prompt 的 delivery report 都必须同步更新这两个文件。**

**全局锁**：`generation_unlocked: false` / `generation_3600_unlocked: false`；readiness 全 false（candidatepack/KE/RAG/DIFY/production/generation_allowed）。
**路线权威**：本 ledger 是 GRC 序列 P1–P8 的**唯一路线真源**；`project-infra/current_workspace_status.yaml` 指向旧 HOLDOUT 路线、已知 stale，本序列只读不改。

## P1–P8 进度表

| Step | task_id | status | objective（大白话）| blocked_by | next |
|---|---|---|---|---|---|
| **P1** | GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001 | ✅ DONE | 把 tmp 语料锁进 `03_grc_goldset_corpus/` 货架 + 校验器 | — | P2 |
| **P2** | GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001 | ✅ DONE | 给合同补 `evidence_policy_candidate`/`EvidencePolicyOutbox` 两个枚举 + 对齐校验器，让 15 条 evidence 金样可当 judge fixture | — | P3 |
| **P3** | GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001 | ✅ DONE | 落地 judge 校准 registry（正/反/边界/控制面/failure_code/hard_gate/expert_index/creative/do_not_copy）+ 校验器 | — | P4 |
| **P4** | GKB-CANARY-40-GENERATION-AND-GATE-001 | ✅ DONE | 生成 40 条受控 canary 草稿（每簇 1 条，`gpt_generated_structured_draft`）+ 过机器闸 | — | P5 |
| **P5** | GKB-CANARY-40-QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001 | ✅ DONE | 吸收两位专家共识做质量收口（不复评/不重打分）+ 从 40 条 canary 抽 `proposition_pack_v1`（每簇 3–5 条 source-traced 命题）（**supersede** 原 P5 复审名）| — | P6 |
| **P6** | GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001 | ✅ DONE | 把 proposition_pack_v1 + Creative Content Principle 编译成 3600 开工前 briefing（Governance Gate + Creative Gate + 创意分 + 6 类能力要求 + 消费计划 + stop conditions）+ go/no-go 裁决=**GO_TO_P7**（**仅解锁 P7 brief/授权流程，非授权真实生成**）| — | P6R |
| **P6R** | GKB-GRC-LEGACY-LOCK-RETIRE-AND-GOVERNED-UNLOCK-001 | ✅ DONE | **旧 semantic-pilot 失败线退役 + GRC 受治理解锁**（Phase A）：登记旧线 superseded_failed（不删证据/不翻案）、记 P4/P5/P6 为有效解锁依据、建路线级受治理增量微批解锁（`mkc_007..046`）；**零生成/零授权生成**；one-shot/`direct_3600` 仍禁；P0-00 held | — | P7 |
| **P7** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ▶️ NEXT（**re-scoped: governed incremental microbatch**）| 3600 结构化草稿微批生成，被 P6R **由 one-shot 3600 重定范围为受治理增量真实微批**（下一步=batch-001 ~20-40 条）。**真实生成须单独 founder 授权 + Codex 三关**，P6/P6R 均不授权 | — | P8 |
| **P8** | GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001 | ⛔ PLANNED_BLOCKED_BY_P7 | 3600 质量/去重/路由资格（planned）| P7 | — |

## head 记录

| Step | head_before | head_after |
|---|---|---|
| P1 | `09fdb37…` | `df2caca…` |
| P2 | `df2caca…` | `9e590c2…` |
| P3 | `9e590c2…` | `4692785…` |
| P4 | `4692785…` | `9b8769f…` |
| P5 | `9b8769f…` | `f71f442…`（hash hygiene 已回填）|
| P6 | `f71f442…` | `0433feb…` |
| P6R | `0433feb…` | 见本次 commit（`git rev-parse HEAD`）|

## 说明

- **P6 已 DONE，P7 是唯一 NEXT（brief-only）**。go/no-go 裁决 = **GO_TO_P7**：只表示可以起草/提交 P7 的 3600 generation Execution Brief，**不等于已授权真实 3600 生成**。真实生成须**单独 founder 授权 + Codex 三关**（Codex Prompt Pre-Review note 1+2，见 YAML `canary_p6_route_note`）。
- **P6 保持全锁**：`generation_allowed: false` / `generation_3600_executed: false` / `generation_3600_unlocked: false`；未创建 3600 生成物或 `07_microbatch_runs/`；未触碰 CandidatePack/KE/RAG/DIFY；readiness 全 false。
- **双门并列**：新增 Creative Gate（8 维内容生产价值）与既有 Governance Gate（10 检否决权）并列，Creative Gate/Creative Score **不替代不弱化**治理门，**不作 production/readiness 条件**（Codex note 3）。
- **6 类创意生产能力**（AestheticFrame/VisualScene/StylingLogic/NarrativeBeat/HumanVoice/CreativePattern）均 `briefing_requirement_only`，**不注册为 ontology object**（Codex note 4）。
- **P5 hash hygiene**：把 P5 step 与 P5 receipt 的 `recorded_in_git_log_for_this_commit` 占位回填为实际 P5 commit `f71f4425b3f54458f5f65889ce9101d6ff66bb68`；P5 counts/verdict/route/命题事实一律未改（Codex note 5）。
- **P5 supersede**：原 ledger P5 名 `GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001` 被扩展为 `...QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001`（见 YAML `supersedes_task_id`）。
- **P8 = 3600 质量/去重/路由**，标 `PLANNED_BLOCKED_BY_P7`，当前不可执行。
- P6 允许声明：`microbatch_3600_briefing_landed` / `creative_gate_landed` / `governance_gate_landed` / `proposition_pack_v1_consumed_for_briefing` / `ready_for_p7_3600_microbatch_generation_prompt`；`generation_allowed: false` 保持。
- **P6R（Phase A，本次）= 旧锁退役 + GRC 受治理解锁**：详见 [08_batch_unlock_reconciliation/](../08_batch_unlock_reconciliation/)。旧 semantic-pilot 失败线（44 cross-type / holdout-14 / 20-regen / v3–v4.7）登记为 `superseded_failed_line`（`use_as_p7_evidence: false`，证据不删/不翻案）；P4/P5/P6 记为有效解锁依据；建**路线级**受治理增量微批解锁（`mkc_007..046`），P0-00（`mkc_001..006`）held。**中央取代**：路线权威在本 ledger + `08` 目录，`02_generation_brief_pack/**` 与 `project-infra/current_workspace_status.yaml` 未改、按 legacy-read-only 登记；`direct_3600_generation`（合约层 immutable + `shared_rules.global_forbidden`）原样保留。
- **P7 已 re-scoped**：由 one-shot 3600 改为**受治理增量真实微批**（`unlock_kind: governed_incremental_microbatch`），status 仍 `NEXT`（未开工）。**P6R 零生成、零授权生成**；下一真实动作 = `GKB-3600 batch-001`（~20-40 条人工撰写、单独 founder 授权 + Codex 三关，绝不 one-shot）。`generation_unlocked: false` 全局锁保持。
