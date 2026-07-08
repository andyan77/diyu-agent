# 07_microbatch_briefing — 3600 微批次开工 Briefing + Go/No-Go (P6)

任务 / task: `GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001`（P6，路线台账 `10_execution_progress/grc_3600_execution_plan_status.v0.1.yaml`）

## 这是什么 / What

P5 把 40 条 canary 抽成了 `proposition_pack_v1`（160 命题）。P6 **不直接生成 3600**，而是把命题包 + founder 新提出的 Creative Content Principle 编译成 **3600 开工前 briefing** 与 **go/no-go 门**。

核心转向：笛语不只是治理系统，而是**服装行业内容生产系统**。于是在原有 **Governance Gate（不犯错，否决权）** 旁边新增 **Creative Gate（有没有内容生产价值）**，两门并列、正交、都要过、谁也不能替代谁。

## 成员 / Members

| 文件 | 作用 |
|---|---|
| [creative_content_principle.v0.1.md](creative_content_principle.v0.1.md) | 核心原则：笛语=内容生产系统；治理门 vs 创意门分工；正文语言 vs 治理话术边界 |
| [creative_gate_for_3600.v0.1.yaml](creative_gate_for_3600.v0.1.yaml) | Creative Gate 8 维（视觉场景/单品细节/真实感/审美/叙事节拍/口吻/平台适配/灵感可执行）|
| [governance_gate_for_3600.v0.1.yaml](governance_gate_for_3600.v0.1.yaml) | Governance Gate 10 检（路由/readiness/无真实事实/硬主张挂证据/无治理话术污染正文/无抄袭/无模板/无下游物化/不碰KE·RAG·DIFY/不开生成）|
| [creative_score_rubric.v0.1.yaml](creative_score_rubric.v0.1.yaml) | Creative Score：只排序内容价值，**不作 production/readiness 条件** |
| [creative_production_capability_requirements.v0.1.yaml](creative_production_capability_requirements.v0.1.yaml) | 6 类生产能力（AestheticFrame/VisualScene/StylingLogic/NarrativeBeat/HumanVoice/CreativePattern），**briefing_requirement_only，不注册 ontology** |
| [proposition_pack_consumption_plan.v0.1.yaml](proposition_pack_consumption_plan.v0.1.yaml) | 命题包消费规则：非 accepted knowledge、非 CandidatePack-ready、P7 须引 proposition_id、控制面命题不进正文 |
| [microbatch_generation_constraints.v0.1.yaml](microbatch_generation_constraints.v0.1.yaml) | P7 allowed / forbidden |
| [microbatch_allocation_update.v0.1.yaml](microbatch_allocation_update.v0.1.yaml) | 3600 分配 planning（不物化 draft）|
| [p7_execution_readiness_checklist.v0.1.yaml](p7_execution_readiness_checklist.v0.1.yaml) | P7 前置清单 RC-01..RC-18 |
| [stop_conditions_for_p7.v0.1.yaml](stop_conditions_for_p7.v0.1.yaml) | P7 stop conditions |
| [p6_go_no_go_decision.v0.1.yaml](p6_go_no_go_decision.v0.1.yaml) | go/no-go 裁决 = **GO_TO_P7**（仅解锁 P7 brief/授权流程，**非**授权真实生成）|
| [microbatch_3600_briefing_manifest.v0.1.yaml](microbatch_3600_briefing_manifest.v0.1.yaml) | 顶层 manifest + readiness 全 false |

## 裁决 / Decision

**GO_TO_P7** —— 可以起草/提交 P7 的 3600 generation Execution Brief。

> ⚠ **GO_TO_P7 ≠ 授权生成 3600。** 真实 3600 生成需要**单独的 founder 授权 + Codex 三关**。本 briefing 保持 `generation_allowed: false`、`generation_3600_executed: false`、readiness 全 false，未创建任何 3600 生成物或 `07_microbatch_runs/`。

## Gate / checker

`ci/checkers/check_3600_microbatch_briefing_go_nogo.py`（`--live` / `--selftest`；`python -O` fail-closed exit 2）：独立重算 6 前置 checker + briefing 结构 + 6 能力族不注册 ontology + 消费规则 + go/no-go 前置 + readiness/forbidden 扫描 + P5 hash hygiene 守卫 + ledger 路线。
