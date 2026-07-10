# GRC 3600 Execution Plan — Status Ledger

> ledger_version v0.1 · roadmap_authority: founder_approved 2026-07-08
> 机器可读真源：[grc_3600_execution_plan_status.v0.1.yaml](grc_3600_execution_plan_status.v0.1.yaml)

**全局锁**：`generation_unlocked: false` / `expand_to_3600_allowed: false`；readiness 全 false。

## P1–P8 进度表

| Step | task_id | status | objective | blocked_by | next |
|---|---|---|---|---|---|
| **P1** | GKB-GRC-CORPUS-LOCK-AND-NORMALIZATION-001 | ✅ DONE | lock tmp GRC corpus into canonical 03_grc_goldset_corpus + registry + corpus checker | — | P2 |
| **P2** | GKB-GRC-EVIDENCEPOLICY-OWNER-CONTRACT-DELTA-AND-ALIGNMENT-001 | ✅ DONE | add evidence_policy_candidate / EvidencePolicyOutbox to contract enums + owner policy; align 15 formal evidence cases as strict judge fixtures; alignment checker | — | P3 |
| **P3** | GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001 | ✅ DONE | land judge calibration registries (positive/anti/borderline/control/failure_code/hard_gate/expert_index/creative/do_not_copy) + judge calibration checker | — | P4 |
| **P4** | GKB-CANARY-40-GENERATION-AND-GATE-001 | ✅ DONE | generate exactly 40 controlled canary drafts (one per formal cluster mkc_007..mkc_046) as gpt_generated_structured_draft + run canary gate (schema/judge/owner-layer/route/style-copy/dedup… | — | P5 |
| **P5** | GKB-CANARY-40-QUALITY-CLOSEOUT-AND-PROPOSITION-PACK-V1-001 | ✅ DONE | absorb founder-provided two-expert consensus into a canary quality closeout (no re-review, no re-score) + extract proposition_pack_v1 (3-5 source-traced propositions per cluster) from the… | — | P6 |
| **P6** | GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001 | ✅ DONE | compile proposition_pack_v1 + Creative Content Principle into a 3600 pre-generation briefing (Governance Gate + Creative Gate + creative score rubric + 6 capability requirements + consump… | — | P6R |
| **P6R** | GKB-GRC-LEGACY-LOCK-RETIRE-AND-GOVERNED-UNLOCK-001 | ✅ DONE | retire the legacy semantic-pilot batch-generation lock's block on the GRC route (additive supersession + inventory; no evidence deletion; no flag flip; central supersession, no 02_generat… | — | P7A |
| **P7A** | GKB-GENERATOR-CAPABILITY-PROOF-MICROBATCH-001 | ✅ DONE | AI-author 40 fresh, non-copied, proposition-grounded, dual-gate-passing structured drafts (one per formal cluster mkc_007..046) as an HONEST generator-capability quality PROBE. Founder Op… | — | P7B |
| **P7B** | GKB-PROOF-MICROBATCH-CLOSEOUT-AND-GENERATION-MODE-CSO-ALIGNMENT-001 | ✅ DONE | Honestly close out P7A proof_microbatch_001 as an agent_authored_quality_probe_pass (NOT an automatic generator-capability proof; does NOT count toward 3600; does NOT unlock direct 3600) … | — | P7C |
| **P7** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ▶️ NEXT | 3600 structured draft microbatch generation. RE-SCOPED by P6R (legacy-lock retirement + governed GRC unlock) from one-shot 3600 to governed incremental authored microbatch. Real generatio… | — | P8 |
| **P7C** | GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-001 | ▶️ NEXT | Scoped content-production microbatch to verify generation_mode + Ontology-x-CSO composition produces stable content-production value (not semantic checklist / courseware). Brief + go/no-g… | — | P7C_execution_brief_and_go_nogo_only |
| **P7C-BRIEF** | GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-BRIEF-AND-GO-NOGO-001 | ✅ DONE | Design the scoped 120 content-production microbatch as an executable/checkable/stoppable brief: 120 future assignments across mkc_007..046 (>=3 each) by P0 group / generation_mode / creat… | — | P7C-GEN |
| **P7C-GEN** | GKB-SCOPED-120-CONTENT-PRODUCTION-MICROBATCH-GENERATION-001 | ✅ DONE | Scoped 120 content-production microbatch GENERATION (up to 120 gpt_generated_structured_drafts per the P7C-BRIEF assignment plan). NOT authorized by P7C-BRIEF; requires a separate founder… | — | P7C-REVIEW |
| **P7C-REVIEW** | GKB-SCOPED-120-QUALITY-REVIEW-AND-CONTENT-KERNEL-EXTRACTION-001 | ✅ DONE | Absorb CPSS expert review, close out scoped 120 quality review, extract user_visible_kernel and review_packet_kernel, and build routing queues without generating or rewriting drafts. | — | P7C-AB |
| **P7C_SCALE_PREP** | GKB-P7C-SCALE-GATE-COMPLETION-AND-RUNTIME-AB-HANDOFF-001 | ✅ DONE | Complete scoped-120 scale gate standard, capability heatmap, runtime A/B sample plan, execution scalability gate, and scale HOLD handoff without generation or downstream materialization. | — | P7C-AB |
| **P7C-AB** | GKB-CONTENT-KERNEL-REAL-RUNTIME-AB-001 | ▶️ NEXT | Real runtime A/B execution brief and separate authorization only; must not be inferred from P7C scale prep completion. | — | P7C_SCALE |
| **P7C-SCALE-DECISION** | GKB-SCOPED-120-SCALE-DECISION-001 | ⛔ BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY | Decide whether/how to scale beyond scoped 120 after runtime A/B evidence and human quality review. | P7C-AB, execution_scalability_gate | P7D |
| **P7C_SCALE** | GKB-SCOPED-120-TO-SCALE-DECISION-001 | ⛔ BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY | Founder scale decision after real runtime A/B and execution scalability assessment. Not issued by P7C scale prep. | P7C-AB, execution_scalability_gate | P7D |
| **P7D** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ⛔ BLOCKED_BY_P7C_SCALE_DECISION | 3600 structured-draft microbatch generation remains blocked until real runtime A/B, execution scalability gate, and founder final scale decision pass; direct 3600 remains forbidden. | P7C_SCALE | P8 |
| **P8** | GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001 | ⛔ BLOCKED_BY_P7D | 3600 quality / dedupe / routing eligibility (planned; executable only after P7D 3600 governed generation, which is itself blocked by P7C; not yet authorized) | P7D | — |

## P7C Scale Gate Completion

- `GKB-P7C-SCALE-GATE-COMPLETION-AND-RUNTIME-AB-HANDOFF-001` 固化 P7C 扩量裁决标准、能力热力图、12 条 Runtime A/B 样本计划、execution scalability gate 与 SCALE HOLD。
- 本任务不重新评分 120 条、不生成、不运行真实 LLM/DIFY、不创建 Serving/RAG/DIFY/KE/CandidatePack。
- `P7D.status` 保持 `BLOCKED_BY_P7C_SCALE_DECISION` 以兼容已提交 P7C-REVIEW checker；语义上由新增 `P7C_SCALE` 阻塞。
- 下一步仅为 `P7C-AB` / `GKB-CONTENT-KERNEL-REAL-RUNTIME-AB-001` 的单独授权流程；`expand_to_3600_allowed=false`。

## P7C Codex-Native Content Kernel A/B

- `GKB-CONTENT-KERNEL-REAL-RUNTIME-AB-001` 已按修订语义执行为 `codex_native_content_kernel_paired_ab`：12 个冻结样本、24 条 paired 输出，`control=12` / `treatment=12`。
- 本任务不调用外部 LLM、不读取密钥、不产生 API 成本；`runtime_kind=codex_native_agent_execution`。
- 结果状态只记录为 `CODEX_NATIVE_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN`；需 Claude Code 先盲评 X/Y，再读取 arm key。
- 方法学 caveat：founder 已授权在 kernel preview 风险被报告后继续执行；该结果只作为 Codex-native 方向性信号，不是无偏 RCT，不证明外部 runtime、不证明 3600 扩量稳定性。
- `P7C-AB.status` 仍保持 `NEXT`，`P7D.status` 仍保持 `BLOCKED_BY_P7C_SCALE_DECISION`；本次仅通过 `route_migration_6` 记录执行事实，不翻 readiness，不关闭 execution scalability gate。

## P7C Fair A/B Rerun 002

- `GKB-CONTENT-KERNEL-FAIR-RERUN-AB-002` 按 Guardian 建议重跑公平版 A/B：保留 12 个冻结样本，新增 24 条 paired 输出。
- 本轮修复两个 `runtime_ab_001` 混杂点：treatment 不得整段搬运 kernel，control 必须逐候选生成且互不相同。
- 新 checker 强制 `treatment` 与对应 user-visible kernel 最长逐字重合 `<18` 字，并强制 control 输出唯一、无模式模板复用。
- 结果状态仍只写 `CODEX_NATIVE_FAIR_AB_EXECUTED_PENDING_CLAUDE_GUARDIAN`；需 Claude Code 再次盲评 X/Y 后揭盲。
- `runtime_ab_001` 历史保留为 confounded/not-confirmed，不删除、不翻案；`P7C-AB.status`、`P7D.status`、readiness 与扩量锁均保持不变。

## P7C Execution Scalability Proof

- `GKB-P7C-EXECUTION-SCALABILITY-PROOF-AND-SCALE-DECISION-PACKET-001` 执行本地确定性 no-content 控制面测试：从 `microbatch_allocation_update.v0.1.yaml` 派生 40 簇 × 90 = 3600 个 execution-only work item。
- runner 只返回 `NO_CONTENT_EXECUTION_ACK`，不生成任何知识正文、不调用外部 LLM、不读取密钥、不创建 CandidatePack/KE/Serving/RAG/DIFY。
- 7 项 execution capability 均为 PASS：确定性派工消费、checkpoint/resume、microbatch 边界 stop、provenance trace、native execution budget guard、duplicate/drift monitor、failure/resume protocol。
- `cost_guard` 在 Codex/Claude 原生路线下仅表示 work-item/microbatch/retry/failure 额度守卫，不表示外部 API 金额、算力或时间成本已验证。
- `founder_scale_decision_packet` 已生成，`founder_final_decision` 仍为 `PENDING`；`final_scale_decision=HOLD`，`expand_to_3600_allowed=false`。
- 旧状态字面保持不变：`P7C-AB.status=NEXT`，`P7C_SCALE.status=BLOCKED_BY_RUNTIME_AB_AND_EXECUTION_SCALABILITY`，`P7D.status=BLOCKED_BY_P7C_SCALE_DECISION`。

## P7D Conditional Midbatch 320

- Founder 已选择 `CONDITIONAL_MIDBATCH_300_600`，本次仅授权 320 条 Codex-native scoped drafts；未授权第 321 条、600 或 3600。
- 从原始 3600 planning-only manifest 按每簇固定分位点重算选取 `40 x 8 = 320`，再在簇内绑定 3 个真实 assignment/kernel 种子，复用压力为约 `2.67x`。
- 机器闸对每条正文与全部 120 个 user-visible kernel 实算最长逐字重合，并进行簇内 5-shingle Jaccard 近似去重；不信任单一自报绑定。
- 320 条已执行完成，但结果仅为 `MIDBATCH_320_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW`；候选专属性与叙事编造风险不声称机器已证，交 40 条每簇一条的 founder 人审样本。
- 这一结果只证明约 `2.67x` 核化用与有界中批执行，不证明 3600 需要的种子供给或约 `30x` 复用稳定性。
- `route_migration_9` 仅 additive 记录运行事实；`route_migration_8.founder_final_decision=PENDING`、旧 step status、readiness 与 `expand_to_3600_allowed=false` 均保持不变。

## P7D Founder 40 Creative Repair

- `GKB-P7D-FOUNDER-40-CREATIVE-REPAIR-AND-SCOPED-GATE-PATCH-001` 只处理既有 founder 40 样本，为每条创建独立 `repair_id` 和 `body_text / content_kernel / review_metadata / execution_card` 四层修复资产；原 320 与原 40 不改。
- 40 条由 Codex 逐条创作并确定性封装，状态为 `REPAIR_40_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW`；机器闸通过不等于内容质量已由人审确认。
- scoped capture mode 为 `daily_native=32 / lightly_guided=6 / campaign_directed=2`；该参数不登记为本体真值或正式 CSO 轴。
- Claude Code Guardian Review 与 founder 第二次人审均为 `PENDING`；`expand_80=false`、`expand_600=false`、`expand_3600=false`，不得自动执行 80。
- `route_migration_10` 只 additive 记录修复事实；旧 step status、`route_migration_5–9`、readiness 和下游阻塞全部保持不变。

## P7D Everyday-Native Platform Variant 5x2

- `GKB-P7D-EVERYDAY-NATIVE-PLATFORM-VARIANT-CONTRACT-AND-10-PROBE-001` 从既有 40 条 repaired assets 中按可复算规则冻结 5 个父内容核，每个 P0 组 1 个。
- 每个父核保持同一 Event Spine、事实边界、核心判断和账号角色，仅编译为 2 种不同平台表达，共 10 个 expression variants；知识计数增量为 0。
- 10 条全部为 `daily_native`：一人一手机、20 分钟内、不超过 5 个简单片段，不依赖演员、假顾客、假冲突或专门布光。
- 机器闸只确认绑定、复制/重复阈值、payload shape、明确事实边界和低成本执行约束；平台原生度、自然口语和真实可拍性仍待 Claude Code 与 Founder 人审。
- 当前结果仅为 `PLATFORM_NATIVE_10_EXECUTED_PENDING_GUARDIAN_AND_FOUNDER_REVIEW`；`expand_80/600/3600=false`，下游与 readiness 全部保持关闭。
- 只有平台 10 条与 founder 40 条两组人审阈值同时满足，才可起草 80 条验证批 Brief；不得自动执行 80。
