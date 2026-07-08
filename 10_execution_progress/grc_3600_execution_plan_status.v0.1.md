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
| **P4** | GKB-CANARY-40-GENERATION-AND-GATE-001 | ✅ DONE | 生成 40 条受控 canary 草稿（每簇 1 条，`gpt_generated_structured_draft`）+ 过机器闸（数量/覆盖/owner-layer/路由/抄袭/去重/readiness）| — | P5 |
| **P5** | GKB-CANARY-40-FOUNDER-QUALITY-REVIEW-CLOSEOUT-001 | ▶️ NEXT | founder 对 40 条 canary 做质量复审 + 收口裁决（唯一被 P4 解锁的一步；3600 仍锁）| — | P6 |
| **P6** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ⛔ PLANNED_BLOCKED_BY_P5 | 3600 结构化草稿微批生成（planned；**只有 P5 复审收口后才解锁，P4 不解锁 3600**）| P5 | P7 |
| **P7** | GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001 | ⛔ PLANNED_BLOCKED_BY_P6 | 3600 质量/去重/路由资格（planned）| P6 | P8 |
| **P8** | reserved_not_executable | ⛔ RESERVED_NOT_EXECUTABLE | reserved（objective 待 founder 定）| P7 | — |

## head 记录

| Step | head_before | head_after |
|---|---|---|
| P1 | `09fdb37…` | `df2caca…` |
| P2 | `df2caca…` | `9e590c2…` |
| P3 | `9e590c2…` | `4692785…` |
| P4 | `4692785…` | 见本次 commit（`git rev-parse HEAD`）|

## 说明

- **P5 是唯一 NEXT**（founder 质量复审收口）；P4 机器闸绿≠3600 解锁，**3600 微批（P6）仍 blocked，须先过 P5 复审**（Codex Prompt Pre-Review note 1，见 YAML `canary_p4_route_note`）。
- **P6–P7 = 3600 路线**，标 `PLANNED_BLOCKED_BY 前序`，当前不可执行；**P8 = `RESERVED_NOT_EXECUTABLE`**，objective 待 founder 定，执行端不得自行发明。
- 每步的 `readiness_claims_allowed` / `readiness_claims_forbidden` 见 YAML；**任何 generation_3600/candidatepack/KE/RAG/DIFY/production ready 在 P4 阶段一律 forbidden**（P4 只解锁 P5 founder 复审一步）。
- P4 允许声明：`canary_40_generated` / `canary_40_machine_gated` / `ready_for_canary_40_quality_review`；`generation_3600_unlocked: false` 保持。
