# GRC 3600 Execution Plan — Status Ledger
> ledger_version v0.1 · roadmap_authority: founder_approved 2026-07-08
> 机器可读真源：[grc_3600_execution_plan_status.v0.1.yaml](grc_3600_execution_plan_status.v0.1.yaml)
> **每个后续执行 prompt 的 delivery report 都必须同步更新这两个文件。**

**全局锁**：`generation_unlocked: false` / `generation_3600_unlocked: false`；readiness 全 false（candidatepack/KE/RAG/DIFY/production/generation_allowed）。
**路线权威**：本 ledger 是 GRC 序列 P1–P8 的**唯一路线真源**；`project-infra/current_workspace_status.yaml` 指向旧 HOLDOUT 路线、已知 stale，本序列只读不改。

## P1–P8 进度表

| Step | task_id | status | objective（大白话）| blocked_by | next |
|---|---|---|---|---|---|
| **P1** | GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001 | ✅ DONE | lock tmp GRC corpus into canonical 03_grc_goldset_corpus + registry + corpus checker | — | P2 |
| **P2** | GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001 | ✅ DONE | add evidence_policy_candidate / EvidencePolicyOutbox to contract enums + owner policy; align 15 formal evidence cases as strict judge fixtures; alignment checker | — | P3 |
| **P3** | GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001 | ✅ DONE | land judge calibration registries (positive/anti/borderline/control/failure_code/hard_gate/expert_index/creative/do_not_copy) + judge calibration checker | — | P4 |
| **P4** | GKB-CANARY-40-GENERATION-AND-GATE-001 | ✅ DONE | generate exactly 40 controlled canary drafts (one per formal cluster mkc_007..mkc_046) as gpt_generated_structured_draft + run canary gate (schema/judge/owner-layer/route/style-copy/dedupe/readiness) + reports | — | P5 |
| **P5** | GKB-CANARY-40-QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001 | ✅ DONE | absorb founder-provided two-expert consensus into a canary quality closeout (no re-review, no re-score) + extract proposition_pack_v1 (3-5 source-traced propositions per cluster) from the 40 canary bodies. Derived rev… | — | P6 |
| **P6** | GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001 | ✅ DONE | compile proposition_pack_v1 + Creative Content Principle into a 3600 pre-generation briefing (Governance Gate + Creative Gate + creative score rubric + 6 capability requirements + consumption plan + stop conditions) a… | — | P6R |
| **P6R** | GKB-GRC-LEGACY-LOCK-RETIRE-AND-GOVERNED-UNLOCK-001 | ✅ DONE | retire the legacy semantic-pilot batch-generation lock's block on the GRC route (additive supersession + inventory; no evidence deletion; no flag flip; central supersession, no 02_generation_brief_pack edits) and esta… | — | P7A |
| **P7A** | GKB-GENERATOR-CAPABILITY-PROOF-MICROBATCH-001 | ✅ DONE | AI-author 40 fresh, non-copied, proposition-grounded, dual-gate-passing structured drafts (one per formal cluster mkc_007..046) as an HONEST generator-capability quality PROBE. Founder Option 2 re-scope: proves an exe… | — | P7B |
| **P7B** | GKB-PROOF-MICROBATCH-CLOSEOUT-AND-GENERATION-MODE-CSO-ALIGNMENT-001 | ✅ DONE | Honestly close out P7A proof_microbatch_001 as an agent_authored_quality_probe_pass (NOT an automatic generator-capability proof; does NOT count toward 3600; does NOT unlock direct 3600) and compile the generation_mod… | — | P7C |
| **P7** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ▶️ NEXT | 3600 structured draft microbatch generation. RE-SCOPED by P6R (legacy-lock retirement + governed GRC unlock) from one-shot 3600 to governed incremental authored microbatch. Real generation requires a separate founder … | — | P8 |
| **P7C** | GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-001 | ▶️ NEXT | Scoped content-production microbatch to verify generation_mode + Ontology-x-CSO composition produces stable content-production value (not semantic checklist / courseware). Brief + go/no-go ONLY; this step does NOT aut… | — | P7C_execution_brief_and_go_nogo_only |
| **P7C-BRIEF** | GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-BRIEF-AND-GO-NOGO-001 | ✅ DONE | Design the scoped 120 content-production microbatch as an executable/checkable/stoppable brief: 120 future assignments across mkc_007..046 (>=3 each) by P0 group / generation_mode / creative_pattern / owner / proposit… | — | P7C-GEN |
| **P7C-GEN** | GKB-SCOPED-120-CONTENT-PRODUCTION-MICROBATCH-GENERATION-001 | ✅ DONE | Scoped 120 content-production microbatch GENERATION (up to 120 gpt_generated_structured_drafts per the P7C-BRIEF assignment plan). NOT authorized by P7C-BRIEF; requires a separate founder authorization + Codex three-g… | — | P7C-REVIEW |
| **P7C-REVIEW** | GKB-SCOPED-120-QUALITY-REVIEW-AND-CONTENT-KERNEL-EXTRACTION-001 | ✅ DONE | Absorb CPSS expert review, close out scoped 120 quality review, extract user_visible_kernel and review_packet_kernel, and build routing queues without generating or rewriting drafts. | — | P7C-AB |
| **P7C-AB** | GKB-CONTENT-KERNEL-RUNTIME-AB-PLAN-OR-SMOKE-001 | ▶️ NEXT | Plan or run a controlled runtime A/B smoke using extracted content kernels; no Serving/RAG/DIFY/production write unless separately authorized. | — | P7C-SCALE-DECISION |
| **P7C-SCALE-DECISION** | GKB-SCOPED-120-SCALE-DECISION-001 | ⛔ BLOCKED_BY_P7C_AB | Decide whether/how to scale beyond scoped 120 after runtime A/B evidence and human quality review. | P7C-AB | P7D |
| **P7D** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ⛔ BLOCKED_BY_P7C_SCALE_DECISION | 3600 structured-draft microbatch generation (canonical route node) remains blocked until content-kernel runtime A/B and explicit scale decision pass; direct 3600 remains forbidden. | P7C-SCALE-DECISION | P8 |
| **P8** | GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001 | ⛔ BLOCKED_BY_P7D | 3600 quality / dedupe / routing eligibility (planned; executable only after P7D 3600 governed generation, which is itself blocked by P7C; not yet authorized) | P7D | — |

## head 记录

| Step | head_before | head_after |
|---|---|---|
| P1 | `09fdb37ce4e47f1d277420f606a44395e5b4132a` | `df2cacacfdd49c232e3b496b1205f3f78a0eca63` |
| P2 | `df2cacacfdd49c232e3b496b1205f3f78a0eca63` | `recorded_in_git_log_for_this_commit` |
| P3 | `9e590c287dfbf9f5f6401f6f687bb3c95bd2c1f9` | `recorded_in_git_log_for_this_commit` |
| P4 | `46927856bc04222a3188aab6120acf823fc59c6c` | `recorded_in_git_log_for_this_commit` |
| P5 | `9b8769fae54c71501372e68f8876aa28d8edb24f` | `f71f4425b3f54458f5f65889ce9101d6ff66bb68` |
| P6 | `f71f4425b3f54458f5f65889ce9101d6ff66bb68` | `recorded_in_git_log_for_this_commit` |
| P6R | `0433feb7fb84f4be3bbb6aefc95833cacf58cd52` | `recorded_in_git_log_for_this_commit` |
| P7A | `f8015a4308cb21529ddd429b991bc36ae5d566db` | `recorded_in_git_log_for_this_commit` |
| P7B | `eadf59a352bd34bb4f5c8d3e36fa5102de75c356` | `recorded_in_git_log_for_this_commit` |
| P7C-BRIEF | `651d80fdeaaa1b523c2fe7bf76a2932f36bf6c7b` | `recorded_in_git_log_for_this_commit` |
| P7C-GEN | `f99e9608238e799d6647df2c6aee8945844ad491` | `recorded_in_git_log_for_this_commit` |
| P7C-REVIEW | `022324017c7c761495a4d56e6f51adda8efd72f9` | `recorded_in_git_log_for_this_commit` |
| P7C-AB | `recorded_after_P7C_REVIEW_commit` | `None` |

## P7C-REVIEW 本次说明

- 本次任务 `GKB-SCOPED-120-QUALITY-REVIEW-AND-CONTENT-KERNEL-EXTRACTION-001` 已把 scoped 120 的 CPSS 专家评审收口落盘，并抽取 `user_visible_kernel` / `review_packet_kernel` / content-kernel routing matrix。
- 原 120 条 `knowledge_candidate_cards.yaml` / `rich_body_blocks.yaml` 等源产物未修改；本任务零新草稿、零 Serving/RAG/DIFY/KE/CandidatePack。
- CPSS 92.2 是外部 `/tmp` 专家/代理评审输入，不是真 DIFY runtime 或生产验证；runtime proxy A/B 只有 12 条抽样。
- `P7A.status` 保持 `DONE`，质量探针语义由 `P7A.classification=agent_authored_quality_probe_pass` 承载；旧 checker 锚点不改。
- 下一步仅为 `P7C-AB` runtime A/B plan/smoke；P7D 3600 仍被 `P7C-SCALE-DECISION` 阻塞，direct 3600 和 readiness 仍 false。
