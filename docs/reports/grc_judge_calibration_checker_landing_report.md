# GRC Judge Calibration Checker Landing — Delivery Report

任务 / task: `GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001`（P3）
下一步 / next: `GKB-CANARY-40-GENERATION-AND-GATE-001`（P4）

## 1. 一句话结论 / TL;DR

把 P1 语料 + 13 批专家评审编成**机器可消费的 judge 校准手册**（12 个 registry + 校验器），
给后续 canary/3600 当阅卷基线。**未生成新知识、未建 Object、未解锁 3600，readiness 全 false，只解锁 P4 canary。**

## 2. repo_after

| | |
|---|---|
| head_before | `9e590c287dfbf9f5f6401f6f687bb3c95bd2c1f9` |
| head_after | 见本次 commit |
| worktree_after | clean（断言门控提交）|

## 3. files_written

**新增**：`04_judge_calibration/`（README + 12 registry/policy/manifest）、
`ci/checkers/check_judge_calibration_against_grc.py`、`ci/fixtures/judge_calibration_against_grc/`（positive + 11 negative）、
`ci/reports/judge_calibration_against_grc_report.v0.1.json`、本报告 + receipt。

**修改**：`10_execution_progress/*.{yaml,md}`（P3 DONE / P4 NEXT + route authority）、
`ci/checkers/check_grc_contract_ontology_alignment.py`（P2 checker 协议缺陷修复，见 §7，founder 授权扩 allowed-writes）。

## 4. judge_calibration_counts（checker 独立重算）

| 计数 | 值 |
|---|---|
| formal_120 total / positive / anti / borderline | 120 / 40 / 40 / 40 |
| P0-00 total（pos/anti/bdr control）| 18（6/6/6），不计入 formal_120 |
| EvidencePolicyOutbox cases / 并入 GKB | 15 / **0** |
| expert_review batches indexed | 13（行区间 + digest 引用，不改判）|
| case_to_judge_rule_map / creative_metadata | 138 / 120 |

**绑定全部 source-traced**（Codex note 4）：anti 的 `failure_codes` 取自语料 `expected_judge_result.expected_failure_codes`；
borderline 的 `repair_reason` 取自 `body_contract.repair_instruction_if_failed`；无一条编造。

## 5. registry_outputs

12 canonical failure code（FC-01..FC-12，含 id/label/severity/detection_surface）；HG-001..HG-008 硬门；
creative/aesthetic metadata `eval_only: true`（评测维度 rubric，非预打分，非 ontology、非 production）；
`do_not_copy_surface_style_policy`（保留机制、禁抄句式、美学分不作生成门槛）。

## 6. checks

| 检查 | 结果 |
|---|---|
| P1 corpus checker live | PASS |
| P2 alignment checker live | PASS（修复后，见 §7）|
| contract lock checker live | PASS |
| P3 checker live / selftest | PASS / PASS（11/11 negative fail-closed）|
| P3 `python -O` | exit 2 `FAIL-CLOSED` |
| readiness_false / forbidden_scope_clean / exact_stage_only | ✓ / ✓ / ✓ |

## 7. P2 checker 协议缺陷修复（founder 授权扩 allowed-writes）

**发现**：P2 的 checker 硬编了 `P2 DONE ⇒ P3 必须是 NEXT`。P3 一完成（P3→DONE，本 Brief §11 强制），
该断言即被违反 → P2 checker 单独跑 FAIL（`ledger P2 DONE requires P3 = NEXT`），且 P3 checker 原设计以子进程跑
P2 checker → 连带 FAIL。**根因**：checker 断言了具体下游路线状态，是随路线推进即过期的快照（E7.1 同型陷阱），
每推进一步都会复现。

**处置**（founder 裁定"授权最小修复"）：
1. P2 checker 规则改成 `P2 DONE ⇒ P3 unblocked（NEXT 或已推进）`——**协议缺陷修工具**，1-2 行；
2. P3 自己的 checker 改成**独立重算 P1（32 文件字节一致）/ P2（枚举已落 + 15 evidence 不入 GKB）不开子进程**，
   且对 P3→P4 用同一 robust 规则。结果：四个 checker 全绿，流水线可推进到 P4。

这是对 P3 §5 allowed-writes 的一处最小扩展（`ci/checkers/check_grc_contract_ontology_alignment.py`），已 founder 显式批准。
未动 P2 契约 delta / 语料原文；`03_grc_goldset_corpus` 与 `01_generation_contracts` 内容未改。

## 8. execution_progress_ledger

P1 DONE / P2 DONE / P3 DONE / **P4 NEXT** / P5 PLANNED_BLOCKED_BY_P4 / P6 PLANNED_BLOCKED_BY_P5 /
P7-P8 RESERVED_NOT_EXECUTABLE。路线权威 = 本 ledger；`project-infra/current_workspace_status.yaml` 旧路线已知 stale，只读不改。

## 9. 允许声明 / must-not-claim

**允许**：judge_calibration_registry_landed / failure_code_registry_landed / hard_gate_namespace_registry_landed /
p0_00_control_plane_judge_ready / formal_120_judge_ready / **ready_for_canary_40_execution**；`generation_3600_unlocked: false`。

**禁止**：generation_3600_unlocked / candidatepack_ready / KE_ready / RAG_ready / DIFY_ready / production_ready。

## 10. next_real_action_unlocked

`GKB-CANARY-40-GENERATION-AND-GATE-001`（P4）。**不**解锁 3600 / CandidatePack / KE / Serving / RAG / DIFY。
