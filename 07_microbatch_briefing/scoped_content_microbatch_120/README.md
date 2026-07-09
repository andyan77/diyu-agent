# Scoped 120 Content-Production Microbatch — Brief / Go-No-Go（P7C-BRIEF）

> 任务 / task: `GKB-SCOPED-CONTENT-PRODUCTION-MICROBATCH-BRIEF-AND-GO-NOGO-001`（账本 step **P7C-BRIEF**）
> 性质 / status: **briefing_orchestration_contract**（`formal_schema_contract: false` / `ontology_truth_source: false`）
> **本任务不生成任何草稿。0 / 120 已生成。**

## 这层做什么

把 scoped 120 内容生产微批设计成**可执行、可检查、可停机**的 brief/go-no-go 包:120 个 future assignment(未来草稿的施工单),按 **P0 组 / 生成模式 / 创意模式 / owner / 命题锚定 / 事实绑定** 分配好,并给下一步(生成)一个 go/no-go 裁决。**生成留给下一步 P7C-GEN,且仍须单独 founder 授权 + Codex 三关。**

## 关键事实

| 维度 | 值 |
|---|---|
| 目标条数 / target_count | **120**(默认;320 需另行 founder 授权)|
| assignment 数 | **120**(mkc_007..046 各 ≥3)|
| generation_mode 分布 | creative_prototype 36 / fact_slot_script 36 / evidence_bound_candidate 24 / display_solution 24 |
| creative_pattern | 6 类全部 ≥10 次 |
| P0-00 / mkc_001..006 | **不进正文生成 assignment**(仅路由/模式参考)|
| 本任务授权生成? | ❌ `generation_authorized_by_this_task: false` |
| 直接 3600? | ❌ `direct_3600_allowed: false` |
| go/no-go | **GO_TO_SCOPED_120_GENERATION_BRIEF**(只解锁下一步 brief + founder 授权,**不授权当前生成**)|

## 引用真实性(Codex 必修项 4)

每个 assignment 的引用都是**真实已提交 id**,非编造:
- `proposition_refs` ∈ P5 `cluster_propositions`(160 条 PROP-V1-NNN)
- `gold_reference_case_refs` / `anti_gold_avoidance_refs` ∈ gold set(GRC-P001-MKCxxx-{POS,ANTI,BDR}-001)
- `creative_pattern_refs` ∈ P7B `creative_pattern_requirements`(6 类)
- `generation_mode` ∈ P7B `generation_mode_contract`(4 模式)
- owner ∈ P5 owner_candidate(GeneralKnowledgeBase / EvidencePolicyOutbox / GovernanceOutbox / ExecutionAssetOutbox / SourceGapLedger)

## 文件清单

| 文件 | 作用 |
|---|---|
| `scoped_120_microbatch_manifest.v0.1.yaml` | 范围声明:120 / 不授权生成 / 320 需另权 / 不碰 3600 |
| `scoped_120_assignment_plan.v0.1.yaml` | **120 个 future assignment**(核心施工单)|
| `scoped_120_generation_mode_distribution.v0.1.yaml` | 4 模式分布 + 每模式覆盖/事实行为/门焦点 |
| `scoped_120_p0_group_distribution.v0.1.yaml` | P0_01..05 分布;P0-00 不进正文 |
| `scoped_120_cso_overlay_plan.v0.1.yaml` | 每 assignment 的 CSO 叠加;CSO≠本体真值 |
| `scoped_120_creative_pattern_assignment.v0.1.yaml` | 每 assignment≥1 pattern;每类≥10 |
| `scoped_120_fact_binding_assignment.v0.1.yaml` | 每 assignment 事实槽/缺事实行为;BrandKB slot 仅接口 |
| `scoped_120_gate_requirements.v0.1.yaml` | 未来草稿须过的 Governance/Creative 门 + P4 确定性尺子 |
| `scoped_120_stop_conditions.v0.1.yaml` | 本任务 + 未来生成任务的停机条件 |
| `scoped_120_go_no_go_decision.v0.1.yaml` | GO/NO_GO/HOLD;GO 只解锁下一步 brief |
| `scoped_120_generation_brief.v0.1.yaml` | 统合 brief |
| `scoped_120_next_execution_contract.v0.1.yaml` | 下一步 P7C-GEN 任务契约(本任务不授权)|

## 硬边界

不生成草稿 / 不生成 120 / 不生成 3600;不把 P7A proof 计入 3600;不建 CandidatePack / 不跑 Four-Gate / 不写 KE·Serving·RAG·DIFY;不新增 ontology Object;不翻 readiness;不改 P7A/P7B 已提交产物与 checker。
