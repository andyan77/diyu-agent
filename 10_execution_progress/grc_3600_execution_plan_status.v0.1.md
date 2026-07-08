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
| **P6** | GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001 | ▶️ NEXT | 3600 微批 briefing + go/no-go 裁决（唯一被 P5 解锁；消费 proposition_pack_v1；**3600 generation 本身仍锁**）| — | P7 |
| **P7** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ⛔ PLANNED_BLOCKED_BY_P6 | 3600 结构化草稿微批生成（planned；**只有 P6 go 决策后才解锁，P5 不解锁 3600 generation**）| P6 | P8 |
| **P8** | GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001 | ⛔ PLANNED_BLOCKED_BY_P7 | 3600 质量/去重/路由资格（planned）| P7 | — |

## head 记录

| Step | head_before | head_after |
|---|---|---|
| P1 | `09fdb37…` | `df2caca…` |
| P2 | `df2caca…` | `9e590c2…` |
| P3 | `9e590c2…` | `4692785…` |
| P4 | `4692785…` | `9b8769f…` |
| P5 | `9b8769f…` | 见本次 commit（`git rev-parse HEAD`）|

## 说明

- **P6 是唯一 NEXT**（3600 微批 briefing / go-no-go）；P5 命题包完成≠3600 解锁，**3600 generation（P7）仍 blocked，须先过 P6 go 决策**（Codex Prompt Pre-Review note 1，见 YAML `canary_p5_route_note`）。
- **P5 supersede**：原 ledger P5 名 `GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001` 被扩展为 `...QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001`（Codex note 2；见 YAML `supersedes_task_id`）。
- **P7–P8 = 3600 路线**，标 `PLANNED_BLOCKED_BY 前序`，当前不可执行。
- 每步 `readiness_claims_*` 见 YAML；**任何 generation_3600/candidatepack/KE/RAG/DIFY/production ready 在 P5 阶段一律 forbidden**（P5 只解锁 P6 briefing 一步）。
- P5 允许声明：`canary_40_quality_closeout_landed` / `expert_review_input_absorbed` / `proposition_pack_v1_landed` / `ready_for_p6_microbatch_briefing`；`generation_3600_unlocked: false` 保持。
