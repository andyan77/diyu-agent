# P7B — Proof-Microbatch Closeout + Generation-Mode × CSO Alignment · Delivery Report

任务 / task: `GKB-PROOF-MICROBATCH-CLOSEOUT-AND-GENERATION-MODE-CSO-ALIGNMENT-001`（账本 step **P7B**）
授权 / auth: founder 授权 + Codex Prompt Pre-Review **CONDITIONAL_PASS**（6 条必修项已全部应用）
性质 / kind: closeout + contract_alignment + route_replan + checker（**不生成任何新草稿**）

## 0. 一句话

把 P7A 的 40 条 proof 草稿**诚实收口**为 `agent_authored_quality_probe_pass`（AI 逐条撰写、已过机器闸；**不是**自动生成器能力证明、**不计入 3600**、**不解锁直接 3600**），并补上 P7A 没编译的 `generation_mode / fact_binding / Ontology×CSO / creative_pattern / P0 矩阵` 五层 **briefing 编排契约**。下一真实动作 = **P7C**（scoped 120，只 brief/go-no-go）。

## 1. repo_after

| | |
|---|---|
| branch | master |
| head_before | `eadf59a`（P7A）|
| head_after | 见本次 commit |
| worktree_after | clean（断言门控提交）|

## 2. Codex 6 条必修项 —— 逐条落实

| # | 必修项 | 落实 |
|---|---|---|
| 1 | route 命名用 **P7B**（非 P7A-2）+ ledger 加 `route_migration` | ✅ 本步=P7B；P7C=scoped microbatch；P7D=3600 gen；YAML 顶层 `route_migration` 记旧→新映射 |
| 2 | 旧 P7A checker route-sync（**option a**）| ✅ 保持 `P7A=DONE`/`P7=NEXT`（governed_incremental、gen_allowed=false）字段不动，**只新增** P7B/P7C/P7D；**未改** `check_generator_capability_proof_microbatch.py`（不在写面）；P7A 探针再定性由 `P7A.classification` 承载，非改 status |
| 3 | P7C 解锁口径 = brief/go-no-go，非授权生成 | ✅ `next_unlocked: P7C_execution_brief_and_go_nogo_only`、`generation_authorized_by_this_task: false` |
| 4 | P7C 规模收紧 | ✅ `default 120` / `max_without_additional_founder_decision 120` / `320_requires_separate_founder_authorization true` |
| 5 | 这些契约**非** 01 正式 schema | ✅ 每个文件 `contract_status: briefing_orchestration_contract`、`formal_schema_contract: false`、`ontology_truth_source: false` |
| 6 | P7A 原始产物不可变 | ✅ `P7A_original_artifacts_modified: false`；唯一写面 `closeout/**`；git 审计确认 0 个 P7A 原始产物被改 |

## 3. 落盘文件（54 项，全部在允许写面内）

**closeout（4）**：`07_microbatch_runs/proof_microbatch_001/closeout/` → identity_decision / not_3600_unlock_decision / closeout.yaml / closeout.md
**briefing（8）**：`07_microbatch_briefing/generation_mode_cso_alignment/` → README + generation_mode_contract / fact_binding_policy / ontology_cso_composition_contract / creative_pattern_requirements / p0_generation_mode_matrix / p7c_scoped_microbatch_route_plan / p7d_3600_deferral_decision
**checker（1）+ fixtures（36：positive+35 negative）+ report（1）**
**ledger（2，M）**：`10_execution_progress/*.yaml` + `.md`
**docs（2）**：本报告 + receipt
**零改**：`01_generation_contracts/** · 02_generation_brief_pack/** · 03_grc_goldset_corpus/** · 03_pilot/** · 04_judge_calibration/** · 06_canary_runs/** · 08_batch_unlock_reconciliation/** · project-infra/** · P7A 原始产物`

## 4. 五层契约要点（机器可验证）

- **generation_mode（4 模式）**：`creative_prototype`（无事实可产高质创意原型，禁编造具体品牌事件/真实人物经历/产品事实）· `fact_slot_script`（缺事实**留槽不编造**）· `evidence_bound_candidate`（**必须**事实/证据）· `display_solution`（通用方法先行，**最终落地需门店/商品/素材场景事实**）。
- **fact_binding**：无事实≠不能生成；无事实只挡 specific claim / evidence_bound；**BrandKB slot = 接口边界**（不建实例、不写品牌事实、不写 KE、不挡 creative/slot 生成）。
- **Ontology×CSO**：`orthogonal_cross_cutting` + `compositional_overlay`；**CSO 字段禁入 ABox/TBox**；creative_gate ≠ production readiness。
- **creative_pattern**：≥6 类（企业叙事/角色口吻/视觉场景/陈列转内容/产品角色故事/平台表达）；是生成输入**非本体真值**、不进 KE、不等于 accepted gold、不复用 semantic-pilot 治理话术。
- **P0 矩阵**：P0_00..P0_05；**P0_00 = 控制面，不进 GKB 正文生成**（held）。

## 5. checks（全绿）

| 检查 | 结果 |
|---|---|
| P1–P5 + contract-lock live | **PASS** |
| P6 / P6R live | **PASS**（pre-microbatch 快照：`07_microbatch_runs` 相位不变量被 P7A 正当超越）|
| P7A proof checker live | **PASS**（proof-present 快照：保留 proof、去本任务在途文件）|
| **P7B checker live** | **PASS**（error_count=0；9/9 上游 priors exit 0，无白名单）|
| P7B checker --selftest | **PASS**（positive + **35 negative** 全 fail-closed）|
| P7B checker `python -O` | **exit 2 FAIL_CLOSED** |
| git_changed_outside_allowed / P7A originals modified | `[]` / `[]` |
| exact stage（无 `git add .`/`-A`/`commit -a`）| ✅ |

**双快照的诚实说明**：P6/P6R 有"无 `07_microbatch_runs`"零生成相位不变量，被 P7A 正当创建所超越 → 在**无 07_microbatch_runs 的 pre-microbatch 快照**里跑；P7A checker 需**看到** proof 才能校验 40 条 → 在**保留 proof、去本任务在途文件的快照**里跑。两快照都无 `.git`、ledger 回 HEAD，各自在其设计基线上全绿，**无任何白名单豁免**。

## 6. execution_progress_ledger

steps = `[P1..P6R, P7A, P7B, P7(anchor), P7C, P7D, P8]`；P1–P6R + **P7A + P7B = DONE**；`P7A.classification=agent_authored_quality_probe_pass`；**P7 保持 NEXT**（legacy 锚点，仅为兼容已提交 P7A checker，规范节点=P7D）；**P7C = NEXT**（brief/go-no-go）；**P7D = BLOCKED_BY_P7C**；**P8 = BLOCKED_BY_P7D**；`generation_unlocked: false` 全局锁保持；`route_migration.no_old_checker_edited=true`、`no_readiness_flipped=true`。

## 7. 允许 / 禁止声明

**允许**：`proof_microbatch_closeout_landed` / `P7A_classified_as_agent_authored_quality_probe` / `generation_mode_contract_landed` / `fact_binding_policy_landed` / `ontology_cso_composition_contract_landed` / `ready_for_scoped_content_microbatch_brief`。
**仍锁**：`automatic_generator_capability_proven` / `ready_for_direct_3600_generation` / `generation_3600_completed` / `candidatepack_ready` / `KE_ready` / `RAG_ready` / `DIFY_ready` / `production_ready`。

## 8. next_real_action

**P7C = `GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-001` 的 execution brief + go/no-go**，**只**起草/裁决，**不授权生成**；默认 **120**（320 需另行 founder 授权）。真实生成须**单独 founder 授权 + Codex 三关，绝不 one-shot**；`proof_microbatch_001` 除非另行授权**不计入 3600**。
