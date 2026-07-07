# Execution Prompt

任务名称：`CODEX-KNOWLEDGE-GENERATION-CONTRACT-LOCK-001`

## 1. Objective

本任务目标：

```text
在不生成任何知识草案的前提下，把 W7 知识地图之后的 Codex 知识生成契约一次锁住，形成后续 Brief Pack、Pilot、微批次生成可复用的机器可检查规则。
```

本包只做：

```text
1. 锁定 W7 baseline digest 与 Founder Overlay digest。
2. 定义 Codex generation output schema。
3. 定义 candidate_kind / target_owner 枚举。
4. 定义 source_type boundary：source_type 只表示来源摄取分类，不决定最终落层。
5. 定义 layer_annotation 分层标注规则。
6. 定义 rich body quality standard 厚正文质量标准。
7. 定义 body entailment policy / checker 正文蕴含规则与检查器。
8. 定义 dedupe / semantic fingerprint 去重与语义指纹规则。
9. 定义 expert synthesis source policy 专家综合来源政策。
10. 定义 microbatch execution policy 微批次执行策略。
11. 定义 state machine mapping 状态机映射。
12. 落 fail-closed checker + positive / negative selftest。
13. 输出 report / receipt，供 Guardian Delivery Review。
14. 只更新 current_workspace_status.yaml 中本包允许的阶段字段。
15. 完成本任务 commit。
```

本包不做：

```text
- 不生成知识草案。
- 不生成 40-50 条 Pilot。
- 不生成 3600。
- 不生成 14 个宏批次 brief。
- 不创建 CandidatePack。
- 不跑 Four-Gate。
- 不写 KE / ABox / TBox / Evidence / L2 / L3。
- 不写 Serving Projection。
- 不写 RAG context_bundle。
- 不写 DIFY workflow。
- 不调用 LLM / embedding / external AI API。
- 不改 production / release / readiness 状态为 true。
- 不修改 /home/faye/笛语agent。
- 不改旧临时工作区。
```

完成后允许声明：

```yaml
codex_generation_contract_locked: true
codex_generation_checker_landed: true
ready_for_master_map_to_generation_brief_pack: true
```

必须保持：

```yaml
candidatepack_ready: false
KE_ready: false
RAG_ready: false
DIFY_ready: false
generation_allowed: false
generation_eligible: false
production_ready: false
release_ready: false
```

## 2. Execution Location

本任务必须在新 canonical workspace 执行：

```yaml
execution_workspace:
  path: /home/diyu/笛语领域通用数据库
  role: canonical_workspace
```

不得在以下位置执行写入：

```text
- /home/faye/笛语agent
- /tmp/codex-ipc/**
- 旧临时工作区
```

`/home/faye/笛语agent` 仅作为只读 reference：

```yaml
source_repo_reference:
  path: /home/faye/笛语agent
  expected_HEAD: d56e62abb7cbe831c8e67656746ee76397dd1042
  role: read_only_reference
```

## 3. Baseline

执行端必须先实测当前仓库状态。

```yaml
repository:
  path: /home/diyu/笛语领域通用数据库
  branch: master
  expected_HEAD: 90dc9ae7e28c3443702885e953edec88b6da9e78
  required_worktree_status: clean

source_repo_reference:
  path: /home/faye/笛语agent
  expected_HEAD: d56e62abb7cbe831c8e67656746ee76397dd1042
  required_worktree_status: clean
  write_policy: read_only

previous_step:
  task_id: GKB-WORKSPACE-ADOPTION-AND-MIGRATION-001
  expected_verdict: Guardian_PASS_or_CONDITIONAL_PASS_safe_to_continue
  adopted_workspace_HEAD: 90dc9ae7e28c3443702885e953edec88b6da9e78

task_phase: codex_knowledge_generation_preparation
task_category:
  - contract
  - schema
  - semantic_etl_policy
  - checker
  - ci_gate

commit_allowed: true
push_allowed: false
amend_allowed: false
```

如果当前 target HEAD / branch / worktree 或 source repo HEAD / worktree 与上述 baseline 不一致，必须停止并回报，不得自行适配。

## 4. Instruction Precedence

```yaml
instruction_precedence:
  highest:
    - this_execution_prompt
    - root_AGENTS.md
    - project-infra/current_workspace_status.yaml
  canonical_route_source:
    - project-infra/current_workspace_status.yaml
    - project-infra/workspace_manifest.yaml
    - project-infra/canonical_source_digest_manifest.yaml
    - 00_source_inputs/**
  legacy_AGENTS_and_SKILL_role: retained_reference_only
  do_not_route_back_to: knowledge_intake/gpt55_gkb_enrichment_v1 as primary source
```

旧 `AGENTS.md` / `SKILL` 只作为安全护栏和参考，不得决定本任务的 canonical source、generation contract、readiness 或 route。

## 5. Accepted Facts Reused

```yaml
accepted_facts_reused:
  W1_W6_deep_research:
    status: completed
    scope: 六个 P0 能力组深研已完成
    workspace_path: /home/diyu/笛语领域通用数据库/00_source_inputs/W1_W6_provenance

  W7_integration:
    status: completed_and_machine_checked
    canonical_clusters: 46
    source_clusters: 58
    generation_assignments: 14
    unresolved_decisions: 12
    source_gap_seeds: 16
    readiness_true_count: 0
    workspace_path: /home/diyu/笛语领域通用数据库/00_source_inputs/W7_master_map

  founder_overlay:
    status: PASS
    resolved_high_sensitivity_decisions:
      - UD-004
      - UD-009
      - UD-010
      - UD-011
    remaining_unresolved_decisions: 8
    remaining_unresolved_decisions_policy: non_blocking_for_draft_generation
    source_gap_seed_policy: collection_or_expert_synthesis_hint
    workspace_path: /home/diyu/笛语领域通用数据库/00_source_inputs/founder_overlay

  workspace_adoption:
    task_id: GKB-WORKSPACE-ADOPTION-AND-MIGRATION-001
    target_workspace_HEAD: 90dc9ae7e28c3443702885e953edec88b6da9e78
    canonical_required_count: 18
    canonical_provenance_count: 19
    quarantine_count: 38
    excluded_count: 22
    ready_for_codex_generation_contract_lock: true

  route_policy:
    continue_24_subcard_deep_research: false
    rebuild_shared_cluster_registry: false
    direct_3600_generation: false
    pilot_required: true
    microbatch_required: true
    candidatepack_direct_creation: false
    KE_RAG_DIFY_direct_creation: false
```

## 6. Superseded Facts

执行端不得沿用以下旧路线：

```yaml
superseded_facts:
  - 继续做 24 个子卡全量深研
  - 重建共享知识簇注册表
  - 把 12 个 unresolved decisions 全部当作生成前 blocker
  - 把 16 个 source gap seeds 全部当作生成前 blocker
  - 直接一次性生成 3600 条
  - 把 14 个宏批次当成 14 次无检查大生成
  - Codex 只生成索引卡
  - 把语义自查字段写进 rich body 正文
  - Codex 草案可以直接叫 CandidatePack
  - 生成完成即可进入 KE / RAG / DIFY
  - source_type 决定最终落层
  - P0-00 控制面知识可混入 GeneralKnowledgeBase
```

## 7. Direct Inputs

执行端必须读取并验证当前 workspace 内的真实文件位置，不得根据聊天记录手写 digest。

必须读取：

```text
/home/diyu/笛语领域通用数据库/project-infra/current_workspace_status.yaml
/home/diyu/笛语领域通用数据库/project-infra/workspace_manifest.yaml
/home/diyu/笛语领域通用数据库/project-infra/canonical_source_digest_manifest.yaml
/home/diyu/笛语领域通用数据库/00_source_inputs/W7_master_map/master_knowledge_map.yaml
/home/diyu/笛语领域通用数据库/00_source_inputs/W7_master_map/shared_knowledge_cluster_registry.yaml
/home/diyu/笛语领域通用数据库/00_source_inputs/W7_master_map/_manifest/w7_machine_check_report.json
/home/diyu/笛语领域通用数据库/00_source_inputs/W7_master_map/_manifest/w7_split_manifest.json
/home/diyu/笛语领域通用数据库/00_source_inputs/founder_overlay/w7_class5_founder_decision_overlay.yaml
/home/diyu/笛语领域通用数据库/00_source_inputs/founder_overlay/_manifest/founder_decision_overlay_manifest.json
/home/diyu/笛语领域通用数据库/00_source_inputs/generation_assignments/generation_assignment_plan.yaml
/home/diyu/笛语领域通用数据库/00_source_inputs/source_gap_seeds/source_gap_seed_ledger.yaml
/home/diyu/笛语领域通用数据库/00_source_inputs/unresolved_decisions/unresolved_decision_ledger.yaml
/home/diyu/笛语领域通用数据库/00_source_inputs/W1_W6_provenance/**
```

允许只读参考：

```text
/home/faye/笛语agent/contracts/**
/home/faye/笛语agent/candidatepack_etl/*.yaml
/home/faye/笛语agent/ci/checkers/**
```

禁止读取：

```text
/home/faye/笛语agent/.env
任何 secret / key / token 内容
```

## 8. Provenance Safety Rule

W1-W6 provenance 原文因 digest 要求必须保持不改写。历史 provenance 文本中可能包含 readiness / generation true 示例，这不是 blocker，但不得被任何 checker 或 contract 解释成当前状态。

本任务必须把以下规则写入 contract 或 checker：

```yaml
provenance_safety_rule:
  historical_provenance_text_may_contain_example_true_flags: true
  active_readiness_authority:
    - project-infra/current_workspace_status.yaml
    - generated contract fixtures
    - checker reports
  checker_must_not_treat_provenance_examples_as_active_flags: true
  provenance_only_must_not_participate_in_readiness_transition: true
```

checker 必须只检查 active manifest / active contracts / active generated outputs / fixtures，不得把 `00_source_inputs/W1_W6_provenance/**` 中的历史示例当作 active readiness authority。

必须包含一个负例或检查项：

```text
若 provenance-only 文本中出现历史 true flag 示例，checker 不应因此失败；若 active fixture / active generated output / active status manifest 出现 readiness true，则必须 fail-closed。
```

## 9. Allowed Write Surface

只允许修改 / 新增：

```text
/home/diyu/笛语领域通用数据库/01_generation_contracts/**
/home/diyu/笛语领域通用数据库/ci/checkers/**
/home/diyu/笛语领域通用数据库/ci/fixtures/**
/home/diyu/笛语领域通用数据库/ci/reports/**
/home/diyu/笛语领域通用数据库/docs/reports/**
/home/diyu/笛语领域通用数据库/project-infra/current_workspace_status.yaml
```

`project-infra/current_workspace_status.yaml` 只允许更新：

```yaml
allowed_status_update:
  phase.previous_step: CODEX-KNOWLEDGE-GENERATION-CONTRACT-LOCK-001
  phase.current_next_step: MASTER-MAP-TO-CODEX-GENERATION-BRIEF-PACK-001
  contract_lock_status: completed
```

禁止改 readiness / generation / production flags 为 true。

建议产物清单：

```text
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/w7_generation_baseline_lock.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_generation_output_contract.v0.1.schema.json
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_candidate_kind_target_owner_policy.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_source_type_boundary_policy.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_layer_annotation_policy.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_rich_body_quality_standard.v0.1.md
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_body_entailment_policy.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_dedupe_fingerprint_policy.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_expert_synthesis_source_policy.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_microbatch_execution_policy.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_state_machine_mapping_policy.v0.1.yaml
01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts/codex_provenance_safety_policy.v0.1.yaml
ci/checkers/check_codex_generation_contract_lock.py
ci/fixtures/codex_generation_contract_lock/positive_minimal_valid_candidate.yaml
ci/fixtures/codex_generation_contract_lock/negative_readiness_true.yaml
ci/fixtures/codex_generation_contract_lock/negative_missing_candidate_kind.yaml
ci/fixtures/codex_generation_contract_lock/negative_source_type_decides_layer.yaml
ci/fixtures/codex_generation_contract_lock/negative_empty_rich_body.yaml
ci/fixtures/codex_generation_contract_lock/negative_selfcheck_leaked_into_body.yaml
ci/fixtures/codex_generation_contract_lock/negative_body_not_entailed.yaml
ci/fixtures/codex_generation_contract_lock/negative_hard_claim_expert_synthesis.yaml
ci/fixtures/codex_generation_contract_lock/negative_real_instance_fact_leak.yaml
ci/fixtures/codex_generation_contract_lock/negative_p0_00_general_kb_leak.yaml
ci/fixtures/codex_generation_contract_lock/negative_candidatepack_claim.yaml
ci/fixtures/codex_generation_contract_lock/negative_KE_RAG_DIFY_claim.yaml
ci/fixtures/codex_generation_contract_lock/negative_provenance_example_treated_as_active.yaml
ci/reports/codex_generation_contract_lock_report.json
docs/reports/codex_generation_contract_lock_report.md
docs/reports/codex_generation_contract_lock_receipt.json
```

执行端不得自行扩大 allowlist。

## 10. Forbidden Scope

禁止修改：

```text
00_source_inputs/**
archive/**
KE/**
serving_projection/**
rag/**
dify/**
candidatepack_etl/candidatepack_instances/**
candidatepack_etl/gate_reports/**
release/**
runtime/**
external_runtime/**
project-infra/workspace_manifest.yaml
project-infra/canonical_source_digest_manifest.yaml
README.md
CURRENT_MAINLINE.md
docs/笛语项目路线图*
docs/笛语项目总体阶段控制表*
/home/faye/笛语agent/**
/tmp/codex-ipc/**
```

禁止触碰资源：

```text
external services
ECS / nginx / DIFY runtime
Qdrant
Postgres / database
LLM / embedding / external AI API
secrets / .env / keys / tokens
production endpoint
```

禁止命令：

```text
git add .
git add -A
git commit -a
git commit --amend
git push
git clean
git reset
rm / unlink
```

## 11. Contract Requirements

### 11.1 W7 Baseline Digest Lock

必须落 `w7_generation_baseline_lock.v0.1.yaml`。

最低字段：

```yaml
w7_generation_baseline_lock:
  schema_version: v0.1
  status: locked_for_codex_generation_contract
  source_authority:
    workspace_manifest: project-infra/workspace_manifest.yaml
    canonical_source_digest_manifest: project-infra/canonical_source_digest_manifest.yaml
  w7_map:
    version:
    digest:
    source_files:
      - path:
        digest:
    canonical_cluster_count: 46
    source_cluster_count: 58
    generation_assignment_count: 14
    unresolved_decision_count: 12
    source_gap_seed_count: 16
    readiness_true_count: 0
  founder_overlay:
    version:
    digest:
    resolved_high_sensitivity_decisions:
      - UD-004
      - UD-009
      - UD-010
      - UD-011
    remaining_unresolved_decisions_count: 8
    remaining_unresolved_decisions_policy: non_blocking_for_draft_generation
    source_gap_seed_policy: collection_or_expert_synthesis_hint
  generation_policy:
    direct_3600_generation_allowed: false
    pilot_required: true
    microbatch_required: true
    candidatepack_direct_creation_allowed: false
    KE_RAG_DIFY_direct_creation_allowed: false
```

如果 workspace 实际 W7 counts 不等于 46 / 58 / 14 / 12 / 16，必须停止。

### 11.2 Generation Output Schema

必须定义 `codex_generation_output_contract.v0.1.schema.json`。

每条生成草案必须至少具备：

```yaml
required_conceptual_fields:
  identity:
    - candidate_id
    - candidate_name
    - schema_version
    - generation_status
  w7_trace:
    - w7_map_digest
    - founder_overlay_digest
    - canonical_cluster_id
    - generation_assignment_id
    - input_digest
  ownership:
    - candidate_kind
    - proposed_target_owner
    - target_owner_reason
  source_policy:
    - source_type
    - source_type_boundary_status
    - source_refs
    - expert_synthesis_allowed
    - expert_synthesis_policy_ref
  layer_annotation:
    - declared_layer
    - target_layer_candidate
    - allowed_landing_layers
    - forbidden_landing_layers
    - layer_confidence
    - layer_boundary_note
    - if_layer_uncertain_route
  semantic_structure:
    - definition
    - applicable_when
    - not_applicable_when
    - output_effect
    - risk_boundary
    - evidence_requirement
  rich_body:
    - body_text
    - body_sections
    - body_proposition_refs
  dedupe:
    - duplicate_check_key
    - semantic_fingerprint
    - proposition_fingerprint
    - runtime_effect_fingerprint
  readiness_flags:
    - candidatepack_ready
    - KE_ready
    - serving_ready
    - RAG_ready
    - DIFY_ready
    - generation_eligible
    - production_servable
    - production_ready
  state_machine:
    - current_state
    - route_after_review
    - route_reason
  review:
    - human_review_required
    - reviewer_status
```

强制值：

```yaml
generation_status: gpt_generated_structured_draft
human_review_required: true
readiness_flags:
  candidatepack_ready: false
  KE_ready: false
  serving_ready: false
  RAG_ready: false
  DIFY_ready: false
  generation_eligible: false
  production_servable: false
  production_ready: false
```

### 11.3 candidate_kind / target_owner Policy

必须定义以下枚举，不得让 `source_type` 决定落层。

```yaml
candidate_kind_allowed:
  - general_knowledge_candidate
  - control_plane_candidate
  - cso_outbox_candidate
  - execution_asset_outbox_candidate
  - governance_outbox_candidate
  - source_gap
  - decision_packet

proposed_target_owner_allowed:
  - GeneralKnowledgeBase
  - ControlPlaneContractSource
  - CSOOutbox
  - ExecutionAssetOutbox
  - GovernanceOutbox
  - SourceGapLedger
  - DecisionPacketLedger
```

最小映射约束：

```yaml
mapping_rules:
  - if candidate_kind == general_knowledge_candidate:
      allowed_target_owner: GeneralKnowledgeBase
      forbidden_content:
        - P0_00_control_plane_operation
        - route_authority
        - readiness_transition_rule
        - real_brand_fact
        - real_SKU_fact
        - real_store_fact
        - real_person_fact
  - if candidate_kind == control_plane_candidate:
      allowed_target_owner: ControlPlaneContractSource
      forbidden_target_owner:
        - GeneralKnowledgeBase
  - if candidate_kind in [source_gap, decision_packet]:
      allowed_target_owner:
        - SourceGapLedger
        - DecisionPacketLedger
      forbidden:
        - candidatepack_ready_true
        - KE_ready_true
        - generation_eligible_true
```

### 11.4 source_type Boundary

必须定义：

```yaml
source_type_boundary:
  source_type_semantics: intake_source_classification_only
  source_type_must_not_decide:
    - target_owner
    - KE_layer
    - production_servable
    - generation_eligible
    - CandidatePack readiness
  final_landing_decided_by:
    - candidate_kind
    - proposed_target_owner
    - layer_annotation
    - gate_result
    - human_review
```

负例必须能 fail-closed：

```text
如果样本只因为 source_type=expert_synthesis 就自动落 GeneralKnowledgeBase，checker 必须失败。
```

### 11.5 Layer Annotation Policy

允许的 `target_layer_candidate`：

```yaml
target_layer_candidate_allowed:
  - TBox_candidate
  - Rule_candidate
  - EvidencePolicy_candidate
  - L2_PlayCard_candidate
  - L3_ExecutionAsset_candidate
  - SlotContract_candidate
  - SourceIntakeContract_candidate
  - GovernanceContract_candidate
  - CSOOutbox_candidate
  - ExecutionAssetOutbox_candidate
  - SourceGapLedger
  - DecisionPacketLedger
  - Excluded
  - DraftBacklog
```

强制规则：

```yaml
layer_rules:
  - P0_00_control_plane_content_must_not_target_GeneralKnowledgeBase
  - hard_claim_without_source_must_route_to_source_gap_or_excluded
  - real_instance_fact_must_route_to_source_gap_or_excluded
  - layer_confidence_below_threshold_must_route_to_decision_required
```

### 11.6 Rich Body Quality Standard

最低要求：

```yaml
rich_body_quality:
  min_body_chars: 350
  must_include:
    - definition_or_core_principle
    - applicable_conditions
    - not_applicable_conditions
    - output_or_execution_implication
    - risk_boundary
    - evidence_or_source_requirement
  must_not_include:
    - semantic_self_check_field_names_as_body_text
    - YAML_key_dump
    - generic_adjective_stack
    - empty_expert_opinion
    - ungrounded_real_instance
    - production_ready_claim
```

正文不得把治理字段当自然正文写进去。治理字段只能出现在结构区。

### 11.7 Body Entailment Policy

必须定义正文蕴含规则：

```yaml
body_entailment:
  principle: body_claims_must_be_entailed_by_structured_propositions
  structured_proposition_sources:
    - definition
    - applicable_when
    - not_applicable_when
    - output_effect
    - risk_boundary
    - evidence_requirement
  checker_behavior:
    - every_body_section_must_reference_at_least_one_structured_proposition
    - hard_claim_must_have_source_ref_or_route_to_source_gap
    - real_instance_fact_must_not_be_created_by_expert_synthesis
    - unsupported_body_claim_must_fail
```

负例必须覆盖：

```text
正文说“某面料经检测有功能效果”，但结构区无 evidence_requirement/source_ref，必须 fail。
```

### 11.8 Dedupe / Semantic Fingerprint Policy

必须定义三层去重：

```yaml
dedupe_layers:
  label_dedupe:
    fields:
      - candidate_name
      - canonical_cluster_id
      - duplicate_check_key
  proposition_dedupe:
    fields:
      - definition
      - applicable_when
      - not_applicable_when
      - risk_boundary
      - evidence_requirement
  runtime_effect_dedupe:
    fields:
      - content_generation_usage
      - display_styling_usage
      - output_effect
      - downstream_consumability
dedupe_outcomes:
  - keep_primary
  - merge_into_primary
  - split_candidate
  - mark_near_duplicate_review
  - supersede_draft
  - exclude_duplicate
```

### 11.9 Expert Synthesis Source Policy

必须定义专家综合边界：

```yaml
expert_synthesis_allowed_after_human_review_for:
  - creative_method
  - industry_common_sense
  - display_method
  - content_strategy
  - narrative_structure
  - role_expression_pattern

expert_synthesis_forbidden_for:
  - hard_claim
  - real_brand_fact
  - real_SKU_fact
  - real_store_fact
  - real_person_fact
  - real_customer_feedback
  - fabric_test_claim
  - body_effect_claim
  - product_performance_claim
```

checker 必须阻断：

```text
hard claim / 真实实例事实 / 检测功效 / 身体效果声明 由 GPT/Codex 专家综合兜底。
```

### 11.10 Microbatch Execution Policy

必须定义：

```yaml
microbatch_policy:
  macro_batches: 14
  target_total_budget: 3600
  budget_not_kpi: true
  quality_over_count: true
  microbatch_size: 20_to_40
  each_microbatch_must_run:
    - schema_parse
    - readiness_false_scan
    - candidate_kind_target_owner_check
    - layer_annotation_check
    - rich_body_quality_check
    - body_entailment_check
    - dedupe_check
    - hard_claim_leak_check
    - real_instance_fact_leak_check
    - P0_00_domain_leak_check
    - provenance_safety_check
    - microbatch_receipt
stop_microbatch_if:
  - readiness_true_count > 0
  - index_shell_rate > 0
  - hard_claim_without_evidence_as_fact > 0
  - real_instance_fact_leak > 0
  - P0_00_domain_leak > 0
  - body_entailment_fail_rate > 10%
  - rich_body_empty_or_generic_rate > 10%
```

### 11.11 State Machine Mapping

必须定义生成草案状态机：

```yaml
state_machine_mapping:
  initial_state:
    - gpt_generated_structured_draft
  after_semantic_alignment:
    - aligned_candidate_input
  split_routes:
    candidatepack_ready_after_review:
      meaning: 结构完整，有 source 或专家人审来源，可准备 CandidatePack Brief
      must_not_mean: already_CandidatePack
    source_workorder_needed:
      meaning: 有价值，但需要补来源或专家确认
    decision_required:
      meaning: 层级、词表、字段、target_owner 或能力归属仍不清
    excluded:
      meaning: 越界、重复、真实实例污染、hard claim 不合规
    draft_backlog:
      meaning: 有价值，但不进入本轮
```

必须写明：

```text
candidatepack_ready_after_review 只是“可准备 CandidatePack Brief”，不是 CandidatePack 实例，不得进入 Four-Gate / KE / RAG / DIFY。
```

## 12. Checker Requirements

必须新增或复用 checker：

```text
ci/checkers/check_codex_generation_contract_lock.py
```

checker 至少检查：

```yaml
live_checks:
  - W7 baseline lock exists and parses
  - W7 counts match 46 / 58 / 14 / 12 / 16
  - readiness_true_count == 0
  - generation output schema exists and parses
  - candidate_kind enum exists
  - target_owner enum exists
  - source_type boundary exists
  - layer_annotation policy exists
  - rich body quality standard exists
  - body entailment policy exists
  - dedupe policy exists
  - expert synthesis policy exists
  - microbatch policy exists
  - state machine mapping exists
  - provenance safety policy exists
  - all active readiness flags remain false in active fixtures and active status
  - provenance examples are not treated as active readiness flags
```

Selftest 必须包含正例和负例。

正例：

```text
ci/fixtures/codex_generation_contract_lock/positive_minimal_valid_candidate.yaml
```

负例至少包括：

```text
negative_readiness_true.yaml
negative_missing_candidate_kind.yaml
negative_source_type_decides_layer.yaml
negative_empty_rich_body.yaml
negative_selfcheck_leaked_into_body.yaml
negative_body_not_entailed.yaml
negative_hard_claim_expert_synthesis.yaml
negative_real_instance_fact_leak.yaml
negative_p0_00_general_kb_leak.yaml
negative_candidatepack_claim.yaml
negative_KE_RAG_DIFY_claim.yaml
negative_provenance_example_treated_as_active.yaml
```

所有负例必须 fail-closed。

## 13. Required Checks

执行端必须运行等价检查。若仓库已有官方 checker runner，可替换为官方命令，但必须在报告中写明替换原因。

建议命令：

```bash
set -euo pipefail

git -C "/home/diyu/笛语领域通用数据库" status --short
git -C "/home/diyu/笛语领域通用数据库" rev-parse --abbrev-ref HEAD
git -C "/home/diyu/笛语领域通用数据库" rev-parse HEAD
git -C "/home/faye/笛语agent" status --short
git -C "/home/faye/笛语agent" rev-parse HEAD

python3 -m py_compile ci/checkers/check_codex_generation_contract_lock.py

python3 ci/checkers/check_codex_generation_contract_lock.py \
  --contracts-root 01_generation_contracts/codex_gkb_draft_generation_v1/00_contracts \
  --fixtures-root ci/fixtures/codex_generation_contract_lock \
  --report-out ci/reports/codex_generation_contract_lock_report.json

python3 ci/checkers/check_codex_generation_contract_lock.py --selftest

python3 - <<'PY'
from pathlib import Path
import json
paths = [
  Path("ci/reports/codex_generation_contract_lock_report.json"),
  Path("docs/reports/codex_generation_contract_lock_receipt.json"),
]
for p in paths:
    if not p.exists():
        raise SystemExit(f"missing: {p}")
    json.loads(p.read_text(encoding="utf-8"))
print("json parse PASS")
PY

git diff --name-only
git diff --cached --name-only
```

提交前必须运行：

```bash
git diff --cached --name-only
```

staged files 只能包含 allowed write surface。

## 14. Stop Conditions

立即停止，不得提交：

```text
- target workspace 不是 /home/diyu/笛语领域通用数据库。
- 当前仓库不是 master。
- 当前 HEAD 不是 90dc9ae7e28c3443702885e953edec88b6da9e78。
- worktree 非 clean，且不是明确可排除的无关 dirty。
- source repo HEAD 不是 d56e62abb7cbe831c8e67656746ee76397dd1042。
- source repo worktree 非 clean。
- 找不到 W7 baseline / Founder Overlay / generation assignment 真源。
- W7 counts 与 46 / 58 / 14 / 12 / 16 不一致。
- 需要生成知识草案才能完成本包。
- 需要创建 CandidatePack。
- 需要修改 KE / Serving / RAG / DIFY。
- 需要修改 00_source_inputs / archive / workspace_manifest / canonical_source_digest_manifest。
- 需要调用 LLM / embedding / external API。
- 需要读取 secret / .env / token。
- 需要放宽现有 checker / schema 才能通过。
- 任一 readiness / generation / production flag 被置 true。
- P0-00 控制面内容被允许进入 GeneralKnowledgeBase。
- hard claim 或真实实例事实被 expert synthesis 兜底。
- source_type 被用来决定最终落层。
- rich body 只是字段清单、YAML key dump 或空泛套话。
- provenance-only 历史示例被当作 active readiness authority。
- selftest 负例不能 fail-closed。
```

停止后返回 Stop Report，不得继续写入。

## 15. Commit Policy

```yaml
commit_allowed: true
commit_subject: "contracts: lock codex knowledge generation contract"
amend_allowed: false
push_allowed: false
```

只允许精确 stage allowed files。禁止 `git add .`、`git add -A`、`git commit -a`、`git commit --amend`、`git push`。

## 16. Delivery Report Required

执行完成或停止后，必须返回：

```text
## Execution Review Request

- task_id:
- task_category:
- repository:
- branch:
- commit_before:
- commit_after:
- worktree_before:
- worktree_after:
- accepted_facts_reused:
- superseded_facts:
- direct_inputs_found:
- direct_inputs_missing:
- files_added:
- files_modified:
- allowed_write_surface:
- forbidden_scope_touched:
- external_resources_touched:
- contracts_landed:
- schemas_landed:
- checker_landed:
- fixtures_landed:
- report_and_receipt:
- checks_run:
- checks_passed:
- checks_failed:
- selftest_result:
- provenance_safety_result:
- readiness_flags_result:
- generation_or_production_flags_result:
- stop_conditions_triggered:
- commit_created:
- exact_commands_run:
- risks_and_uncertainties:
- recommended_next_step:
- self_verdict:
```

## 17. Facts Required For Next Planning

必须返回：

```yaml
facts_required_for_next_planning:
  current_repository:
  current_branch:
  current_commit_before:
  current_commit_after:
  worktree_status_before:
  worktree_status_after:
  W7_baseline_digest:
  founder_overlay_digest:
  canonical_cluster_count_verified:
  source_cluster_count_verified:
  generation_assignment_count_verified:
  unresolved_decision_count_verified:
  source_gap_seed_count_verified:
  readiness_true_count_verified:
  contract_files_landed:
  schema_files_landed:
  checker_file:
  checker_selftest_passed:
  negative_fixture_count:
  positive_fixture_count:
  provenance_safety_checked:
  readiness_false_preserved:
  generated_knowledge_count:
  candidatepack_created:
  KE_touched:
  serving_touched:
  RAG_touched:
  DIFY_touched:
  external_resources_touched:
  recommended_next_step:
  human_decision_needed_next:
```

Expected recommended next step if PASS:

```text
MASTER-MAP-TO-CODEX-GENERATION-BRIEF-PACK-001
```

## 18. Completion Definition

本任务只有在以下条件全部满足时，执行端才可自评 PASS：

```text
1. W7 baseline lock 真实落盘且可解析。
2. generation output schema 真实落盘且可解析。
3. candidate_kind / target_owner policy 真实落盘。
4. source_type boundary policy 真实落盘。
5. layer annotation policy 真实落盘。
6. rich body quality standard 真实落盘。
7. body entailment policy 真实落盘。
8. dedupe / fingerprint policy 真实落盘。
9. expert synthesis source policy 真实落盘。
10. microbatch execution policy 真实落盘。
11. state machine mapping policy 真实落盘。
12. provenance safety policy 真实落盘。
13. checker 真实落盘。
14. positive / negative selftest 全部通过，负例 fail-closed。
15. checker 不把 provenance-only 历史 true flag 示例当 active readiness。
16. readiness / generation / production flags 全 false。
17. 未生成知识。
18. 未创建 CandidatePack。
19. 未触碰 KE / Serving / RAG / DIFY。
20. 未触碰外部服务 / secret / runtime。
21. diff / staged / commit 只包含 allowed files。
22. delivery report 足以供 Codex Guardian Review。
```
