# GRC 3600 Execution Plan — Status Ledger

> ledger_version v0.1 · roadmap_authority: founder_approved 2026-07-08
> 机器可读真源：[grc_3600_execution_plan_status.v0.1.yaml](grc_3600_execution_plan_status.v0.1.yaml)
> **每个后续执行 prompt 的 delivery report 都必须同步更新这两个文件。**

**全局锁**：`generation_unlocked: false`；readiness 全 false（candidatepack/KE/RAG/DIFY/production/generation_allowed）。

## P1–P8 进度表

| Step | task_id | status | objective（大白话）| blocked_by | next |
|---|---|---|---|---|---|
| **P1** | GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001 | ✅ DONE | 把 tmp 语料锁进 `03_grc_goldset_corpus/` 货架 + 校验器 | — | P2 |
| **P2** | GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001 | ✅ DONE | 给合同补 `evidence_policy_candidate`/`EvidencePolicyOutbox` 两个枚举 + 对齐校验器，让 15 条 evidence 金样可当 judge fixture | — | P3 |
| **P3** | GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001 | ▶️ NEXT | 落地严格 judge 校准校验器，消费 formal_120 + P0-00 + 15 evidence | — | P4 |
| **P4** | GKB-CANARY-40-GENERATION-AND-GATE-001 | ⛔ BLOCKED_BY_P3 | canary 40 生成 + 闸（planned）| P3 | P5 |
| **P5** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ⛔ BLOCKED_BY_P4 | 3600 结构化草稿微批生成（planned）| P4 | P6 |
| **P6** | GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001 | ⛔ BLOCKED_BY_P5 | 3600 质量/去重/路由资格（planned）| P5 | P7 |
| **P7** | reserved_not_executable | ⛔ BLOCKED_BY_P6 | reserved（objective 待 founder 定）| P6 | P8 |
| **P8** | reserved_not_executable | ⛔ BLOCKED_BY_P7 | reserved（objective 待 founder 定）| P7 | — |

## head 记录

| Step | head_before | head_after |
|---|---|---|
| P1 | `09fdb37…` | `df2caca…` |
| P2 | `df2caca…` | 见本次 commit（`git rev-parse HEAD`）|

## 说明

- **P3 是唯一 NEXT**；P4–P6 是 founder 采纳的 Codex 建议路线名，标 `planned / BLOCKED_BY 前序`，**当前不可执行**。
- **P7/P8 = `reserved_not_executable`**，objective 待 founder 后续定义；执行端不得自行发明。
- 每步的 `readiness_claims_allowed` / `readiness_claims_forbidden` 见 YAML；**任何 generation/candidatepack/KE/RAG/DIFY/production ready 在 P2 阶段一律 forbidden**。
