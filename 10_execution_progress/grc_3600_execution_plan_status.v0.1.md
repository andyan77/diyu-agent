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
| **P6R** | GKB-GRC-LEGACY-LOCK-RETIRE-AND-GOVERNED-UNLOCK-001 | ✅ DONE | **旧 semantic-pilot 失败线退役 + GRC 受治理解锁**（Phase A）：登记旧线 superseded_failed（不删证据/不翻案）、记 P4/P5/P6 为有效解锁依据、建路线级受治理增量微批解锁（`mkc_007..046`）；**零生成/零授权生成**；one-shot/`direct_3600` 仍禁；P0-00 held | — | P7A |
| **P7A** | GKB-GENERATOR-CAPABILITY-PROOF-MICROBATCH-001 | ✅ DONE | **诚实 AI 逐条撰写质量探针**（founder Option 2）：执行 AI（多子代理，非人）逐条撰写 **40 条**全新/非抄袭/命题锚定/过确定性双门的结构化草稿（每簇 1 条 `mkc_007..046`）。**只证"AI 能产过门草稿"，不证"自动/稳定生成"**（仓库无自动生成器）；`generator_capability_proven=false`、`ready_for_P7B_3600=false`、`counts_toward_3600=false`；反抄袭 LCS vs gold<16 / vs canary<18 / 跨簇<18、聚类专属指纹、红线扫描（无品牌/SKU/价格）；零 3600、readiness 全 false | — | P7B |
| **P7B** | GKB-PROOF-MICROBATCH-CLOSEOUT-AND-GENERATION-MODE-CSO-ALIGNMENT-001 | ✅ DONE | **P7A 诚实收口 + 生成模式/CSO 对齐**：把 proof_microbatch_001 定性为 `agent_authored_quality_probe_pass`（**非**自动生成器能力证明、不计入 3600、不解锁直接 3600），并补 P7A 没编译的 `generation_mode`（4 模式）/`fact_binding`（无事实≠不能生成；BrandKB slot 仅接口边界）/`Ontology×CSO`（正交横切+运行时叠加）/`creative_pattern`（≥6 类）/`P0 矩阵`（P0-00 控制面不进正文）层。**零新草稿**；`briefing_orchestration_contract`（非 01 正式 schema）；P7A 原始产物不可变；readiness 全 false | — | P7C |
| **P7** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ▷ NEXT（**legacy 锚点 / = 规范节点 P7D**）| 旧 3600 生成步；status/unlock_kind/generation_allowed 字段**保持不变仅为兼容已提交的 P7A checker**（该 checker 不在本任务写面）。**规范的 3600 节点已迁移为 P7D（现 BLOCKED_BY_P7C_GEN）**，活跃链 = P7C-BRIEF→P7C-GEN→P7D。本锚点不授权任何事。详见 YAML `route_migration` / `route_migration_2` | — | （见 P7C-GEN/P7D）|
| **P7C** | GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-001 | ▷ NEXT（**legacy 锚点**）| scoped 内容生产微批锚点；status/next_unlocked/generation_authorized 字段**保持不变仅为兼容已提交 P7B checker**。其 brief=**P7C-BRIEF**（本次已 DONE），实际生成节点=**P7C-GEN**。详见 YAML `route_migration_2` | — | P7C-GEN |
| **P7C-BRIEF** | GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-BRIEF-AND-GO-NOGO-001 | ✅ DONE | **scoped 120 brief + go/no-go**：120 个 future assignment（mkc_007..046 各 ≥3），按 P0 组/生成模式(36/36/24/24)/创意模式(6 类≥10)/owner/命题锚定/事实绑定分配，**引用全部真实**（P5 命题/goldset/P7B 模式与模式）。go/no-go=**GO_TO_SCOPED_120_GENERATION_BRIEF**（只解锁下一步 brief，不授权生成）。**零草稿生成**；`briefing_orchestration_contract`；readiness 全 false | — | P7C-GEN |
| **P7C-GEN** | GKB-SCOPED-120-CONTENT-PRODUCTION-MICROBATCH-GENERATION-001 | ▶️ NEXT | scoped 120 真实生成（最多 120 条 `gpt_generated_structured_draft`）。**本任务未授权**；须单独 founder 授权 + Codex 三关；120 为免新授权上限，320 需另权，绝不 one-shot 3600 | — | P7D |
| **P7D** | GKB-3600-STRUCTURED-DRAFT-MICROBATCH-GENERATION-001 | ⛔ BLOCKED_BY_P7C_GEN | 3600 结构化草稿微批生成（规范节点，与 legacy P7 锚点同一底层任务）。被 **P7C-GEN** 阻塞（scoped 120 须先跑）；P7A/P7B/P7C 后直接 3600 不允许；真实生成须单独 founder 授权 + Codex 三关，绝不 one-shot | P7C-GEN | P8 |
| **P8** | GKB-3600-QUALITY-DEDUPE-ROUTING-ELIGIBILITY-001 | ⛔ BLOCKED_BY_P7D | 3600 质量/去重/路由资格（planned；被 P7D 阻塞，P7D 又被 P7C-GEN 阻塞，未授权）| P7D | — |

## head 记录

| Step | head_before | head_after |
|---|---|---|
| P1 | `09fdb37…` | `df2caca…` |
| P2 | `df2caca…` | `9e590c2…` |
| P3 | `9e590c2…` | `4692785…` |
| P4 | `4692785…` | `9b8769f…` |
| P5 | `9b8769f…` | `f71f442…`（hash hygiene 已回填）|
| P6 | `f71f442…` | `0433feb…` |
| P6R | `0433feb…` | `f8015a4…` |
| P7A | `f8015a4…` | `eadf59a…` |
| P7B | `eadf59a…` | `651d80f…` |
| P7C-BRIEF | `651d80f…` | 见本次 commit（`git rev-parse HEAD`）|

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
- **P7A（本次）= 诚实 AI 逐条撰写质量探针**（founder Option 2）：详见 [07_microbatch_runs/proof_microbatch_001/](../07_microbatch_runs/proof_microbatch_001/)。侦察确认**仓库无自动生成器、P4 canary 系人工撰写**，能产 40 条的唯一主体是执行 AI 逐条撰写——按 Brief §9/§17 与 Codex 必修项本应 STOP；founder 裁定改成**诚实探针**：40 条全新草稿由多 AI 子代理逐条撰写，`generator_trace_manifest.human_authored=false`（AI 非人）、`limitations` 明写"不证自动/稳定生成"。**机器可验证**（非假绿）：反抄袭 LCS（vs gold<16 / vs P4 canary<18 / 跨簇<18）、聚类专属指纹、红线扫描（无品牌/SKU/价格/流水线元词）、owner 路由、命题锚定、readiness 全 false；**主观美学维度为 AI 自评、非机器打分**（诚实标注）。`generator_capability_proven=false` / `ready_for_P7B_3600=false` / `counts_toward_3600=false`；**零 3600、零下游物化**（无 CandidatePack/KE/RAG/DIFY）。P7A checker 的 8 个上游校验器在**pre-P7A 快照**（工作树副本减 P7A 产物、ledger 回 HEAD、无 .git）里跑，全绿——因为 P6/P6R 的"无 `07_microbatch_runs`"相位不变量被 P7A 正当地超越，须在其提交基线上校验。**P7A 只解锁 P7B 的 3600 brief 起草，不解锁真实生成。**
- **P7B（本次）= P7A 诚实收口 + 生成模式/CSO 对齐**：详见 [07_microbatch_runs/proof_microbatch_001/closeout/](../07_microbatch_runs/proof_microbatch_001/closeout/) 与 [07_microbatch_briefing/generation_mode_cso_alignment/](../07_microbatch_briefing/generation_mode_cso_alignment/)。把 proof_microbatch_001 定性为 `agent_authored_quality_probe_pass`（**非**自动生成器能力证明、`counts_toward_3600=false`、`direct_3600_unlocked=false`），并补 P7A 没编译的四层契约：**4 种 generation_mode**（creative_prototype 无事实可产 / fact_slot_script 缺事实留槽不编造 / evidence_bound_candidate 必须有事实证据 / display_solution 通用方法先行、最终落地需场景事实）、**fact_binding**（无事实≠不能生成；BrandKB slot 仅接口边界，不建实例/不写品牌事实/不写 KE）、**Ontology×CSO**（正交横切 + 运行时叠加；CSO 字段禁入 ABox/TBox）、**≥6 类 creative_pattern** + **P0 矩阵**（P0-00 控制面不进 GKB 正文生成）。全部标 `briefing_orchestration_contract`（`formal_schema_contract=false`、`ontology_truth_source=false`，**非** 01 正式 schema）。**Codex 必修项 1/2（option a）**：旧 P7A checker 硬读 `P7A=DONE`/`P7=NEXT`（不在本任务写面），故 **P7A/P7 字段原样保留、新增 P7B/P7C/P7D**（`route_migration` 记录旧→新映射；P7A 的探针再定性由 `P7A.classification` 承载而非改 status）。**零新草稿 / 零 3600 / 无 CandidatePack·KE·RAG·DIFY**；P7A 原始产物不可变（唯一写面 `closeout/**`）；readiness 全 false。P7B checker 用**双快照**跑 9 个上游（P6/P6R 在无 `07_microbatch_runs` 快照、P7A 在保留 proof 的快照）全绿 + selftest（positive + 35 negative 全 fail-closed）+ `python -O` fail-closed。**下一真实动作 = P7C**（scoped 120，只 brief/go-no-go，不授权生成；320 需另行 founder 授权）。
- **P7C-BRIEF（本次）= scoped 120 内容生产微批 brief + go/no-go**：详见 [07_microbatch_briefing/scoped_content_microbatch_120/](../07_microbatch_briefing/scoped_content_microbatch_120/)。把 scoped 120 设计成可执行/可检查/可停机的施工包：**120 个 future assignment**（mkc_007..046 各 ≥3），按 P0 组 / **生成模式(creative_prototype 36 / fact_slot_script 36 / evidence_bound_candidate 24 / display_solution 24)** / **6 类 creative_pattern（每类≥10）** / owner / 命题锚定 / 事实绑定 分配；**引用全部真实**（`proposition_refs`∈P5 160 命题、gold/anti-gold∈goldset、pattern∈P7B 6 类、mode∈P7B 4 模式、owner∈P5 owner_candidate），checker 逐条查真存在（Codex 必修项 4），**无编造**。P0-00/mkc_001..006 不进正文 assignment。go/no-go = **GO_TO_SCOPED_120_GENERATION_BRIEF**（只解锁下一步 brief + founder 授权，`generation_authorized_now=false`）。**Codex 必修项 1（founder 选加锚点）**：旧 P7B checker 硬读 `P7A=DONE`+classification / `P7C=NEXT`（不在本任务写面），故 **P7A/P7/P7B/P7C 锚点原样保留、新增 P7C-BRIEF(DONE)/P7C-GEN(NEXT)**，P7D→`BLOCKED_BY_P7C_GEN`（`route_migration_2`）。**零草稿生成 / 零 120 / 零 3600 / 无 CandidatePack·KE·RAG·DIFY**；readiness 全 false。P7C checker 用**双快照**跑 **10 个上游**（P1–P6R+contract-lock 在无 `07_microbatch_runs` 快照、P7A+P7B 在保留 proof+alignment 的快照）全绿 + selftest（positive + 35 negative 全 fail-closed）+ `python -O` fail-closed。**下一真实动作 = P7C-GEN**（scoped 120 生成，单独 founder 授权 + Codex 三关，最多 120，320 需另权，绝不 one-shot）。
