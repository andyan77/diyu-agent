# GRC EvidencePolicy Owner Contract Delta & Alignment — Delivery Report

任务 / task: `GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001`（P2）
下一步 / next real action: `GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001`（P3）

## 1. 一句话结论 / TL;DR

给现有 generation contract 最小补两个枚举值（`evidence_policy_candidate` / `EvidencePolicyOutbox`）+ 一条 owner
rule + 状态机映射，让 P1 语料里 15 条 EvidencePolicy 金样从"schema 不认"变成"严格 judge/canary 前置可消费"，
并新增独立对齐校验器。**未生成新知识、未建 Object、未解锁 generation，readiness 全 false。**

大白话：P1 把语料搬上货架时发现 15 箱货的"分类标签"（EvidencePolicyOutbox）不在合同的允许清单里。
本任务就是往合同的允许清单里**补上这个标签**——不改货、不新建东西、不放行生产，只是让机器认得这个标签。

## 2. 侦察修正的关键事实 / recon correction

Brief 假设整个 EvidencePolicy 层缺失；实测**只缺 2 个枚举值**：schema 的 `layer_annotation` 早已含
`EvidencePolicy_candidate`（合法目标层），`codex_layer_annotation_policy.v0.1.yaml` 也已登记。所以：

- 缺口仅在 `candidate_kind` 与 `proposed_target_owner` 两个枚举 → 各补 1 值。
- **未修改** `codex_layer_annotation_policy.v0.1.yaml`（forbidden-from-allowed，且无需改）。
- Codex note #1（lock checker 会不会因 enum 白名单 stale 而挂）实测：lock checker 的 `EXPECTED_COUNTS`
  是 W7 簇/决策计数，**不数** enum；delta 纯 additive → lock checker delta 前后均 PASS。

## 3. repo_after

| | |
|---|---|
| head_before | `df2cacacfdd49c232e3b496b1205f3f78a0eca63` |
| head_after | 见本次 commit（`git rev-parse HEAD`）|
| worktree_after | clean（断言门控提交）|

## 4. contract_delta（additive only）

| 项 | 值 |
|---|---|
| candidate_kind 新增 | `evidence_policy_candidate` |
| proposed_target_owner 新增 | `EvidencePolicyOutbox` |
| state_machine 新增 | `evidence_policy_candidate`：`gpt_generated_structured_draft` → 5 条 draft 分流路由 |
| schema 改 | `codex_generation_output_contract.v0.1.schema.json`（各 enum +1 值）|
| policy 改 | `codex_candidate_kind_target_owner_policy.v0.1.yaml`（+2 enum +1 rule）；`codex_state_machine_mapping_policy.v0.1.yaml`（+1 映射）|
| owner rule 语义 | owner=EvidencePolicyOutbox；allowed_layer=EvidencePolicy_candidate；forbidden_layer 含 ABox/TBox_Object/BrandInstance/…；禁 map_to_GeneralKnowledgeBase / map_to_general_knowledge_candidate / object_creation |

## 5. alignment_counts（checker 独立重算）

| | |
|---|---|
| formal_120_total | 120（75 GKB + 18 ExecAssetOutbox + 15 EvidencePolicyOutbox + 12 GovernanceOutbox）|
| all_formal_120_mappable | true（补 delta 后 15 条 evidence 从不可映射→可映射）|
| evidence_policy_outbox / candidate case_count | 15 / 15（**同一** 15 例，P0-03×12 + P0-05×3）|
| evidence 映射到 GeneralKnowledgeBase 数 | **0** |
| p0_00_total | 18（不计入 formal_120，簇 mkc_001..006 与 formal 不重叠）|
| p0_00 pos/borderline → GKB 违规数 | **0** |
| p0_00 anti_control_gold 演示 GKB 误路由数 | 2（`MKC002-ANTI` / `MKC003-ANTI`，**故意的反例**，合同 `P0_00_control_plane_content_must_not_target_GeneralKnowledgeBase` 的负样本）|
| object_count | **0** |

**P0-00 诚实处理（E8）**：P0-00 用更宽的控制面 artifact 词表（route_contract / asset_binding_policy_candidate 等），
不套 generation candidate_kind 模子；唯二指向 GKB 的是 anti 反例（演示"控制面内容误入 GKB"这一被禁行为），
不是违规。checker 因此只对 **positive/borderline** 控制样本强制"不得 →GKB"（0 违规），anti 反例合法允许。

## 6. checks

| 检查 | 结果 |
|---|---|
| P1 corpus checker live / selftest | PASS / PASS（delta + ledger 编辑未破坏 P1）|
| P2 alignment checker live / selftest | PASS / PASS（9/9 negative fail-closed）|
| P2 `python -O`（防 assert 绕过）| exit 2 `FAIL-CLOSED` |
| contract lock checker live / selftest | PASS / PASS（证明 delta 纯 additive）|
| readiness_false | 全 false |
| forbidden_scope_clean | 00_source / normalized / corpus 四 manifest / tmp / current_workspace_status / README 均未动；KE/Serving/RAG/DIFY/CandidatePack 目录未建 |
| exact_stage_only | 仅精确 stage allowed 面，无 `git add .`/`-A`/`commit -a` |

## 7. blocking_gap_ledger 与 P1 checker 的并存处理

P1 checker 从 gap 对象读 `resolved_in_this_task`（须 false）与 `requires_next_task`（须为本 P2 任务名）。
为让**两个 checker 同绿**，本任务对 `blocking_gap_ledger.v0.1.yaml` 只做**纯 additive** 编辑：新增
`p2_contract_delta_status` 同级块记录 P2 落地，**不改** gap 对象里 P1 读的任何字段。实测 P1 checker 编辑后仍 PASS。

## 8. execution_progress_ledger（P1–P8，founder 批准路线）

`10_execution_progress/grc_3600_execution_plan_status.v0.1.{yaml,md}`：

| Step | status |
|---|---|
| P1 GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001 | DONE |
| P2 GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001 | DONE |
| P3 GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001 | **NEXT** |
| P4 GKB-CANARY-40-GENERATION-AND-GATE-001 | BLOCKED_BY_P3（planned）|
| P5 GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | BLOCKED_BY_P4（planned）|
| P6 GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001 | BLOCKED_BY_P5（planned）|
| P7 / P8 | reserved_not_executable（objective 待 founder 定）|

## 9. 允许声明 / must-not-claim

**允许**：`grc_evidence_policy_owner_contract_delta_landed`、`grc_contract_ontology_alignment_checker_landed`、
`formal_120_strict_mapping_ready`、`judge_calibration_unlocked`；`generation_unlocked: false`。

**禁止声明**：generation_unlocked / candidatepack_ready / KE_ready / RAG_ready / DIFY_ready / production_ready。

## 10. next_real_action_unlocked

`GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001`（P3）。**不**解锁 canary / 3600 / CandidatePack / KE / Serving / RAG / DIFY。
