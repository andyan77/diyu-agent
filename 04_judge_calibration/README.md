# GRC Judge Calibration (P3)

任务 / task: `GKB-JUDGE-CALIBRATION-CHECKER-LANDING-001`

把 P1 锁定的 GRC 语料（formal_120 + P0-00）与 13 批专家评审，转成**机器可消费的 judge 校准基线**，
作为后续 canary / 3600 的质量裁判输入。**不生成新知识、不建 Object、不解锁生成，readiness 全 false。**

大白话：P1/P2 把"考题+标准答案"锁进了货架。P3 是把这些考题**编成阅卷手册**——哪些是满分范例、
哪些是必扣分反例、哪些是可修边界，配上扣分代码表与硬门表，让后面的 AI 阅卷官照着打分。手册**只用于阅卷**，
不写进知识真源、不当生产内容、不让 AI 照抄范文句式。

## 目录内容 / registries

| 文件 | 作用 | 来源 |
|---|---|---|
| `judge_calibration_registry.v0.1.yaml` | 顶层 registry，串起全部子表 + 判决策略 | — |
| `judge_calibration_manifest.v0.1.yaml` | 汇总清单（计数 / exactly-once / object_count 0）供 checker 交叉核 | 派生 |
| `positive_gold_registry.v0.1.yaml` | 40 正样本 → `accept_gold_candidate` | formal_120 |
| `anti_gold_fixture_registry.v0.1.yaml` | 40 反样本 → `reject_or_blocking_revise`，每条带 `failure_codes` | formal_120 `expected_judge_result.expected_failure_codes` |
| `borderline_repair_registry.v0.1.yaml` | 40 边界样本 → `accept_with_minor_fix`，每条带 `repair_reason` | formal_120 `body_contract.repair_instruction_if_failed` |
| `control_plane_calibration_registry.v0.1.yaml` | 18 P0-00 控制面样本（不计入 formal_120）| P0-00 |
| `failure_code_registry.v0.1.yaml` | 12 canonical 失败类目（id/label/severity/detection surface）| 手工 + 语料 F##/GRCF |
| `hard_gate_namespace_registry.v0.1.yaml` | HG-001..HG-008 canonical 硬门 | batch_manifest hard_gate namespace |
| `expert_review_13_index.v0.1.yaml` | 13 批评审的**行区间索引 + dominant failure codes**（原文不改判）| expert_review TXT |
| `case_to_judge_rule_map.v0.1.yaml` | 138 条 case → registry + 期望判决 + 失败/修复引用 | 派生 |
| `creative_inspiration_aesthetic_metadata.v0.1.yaml` | 120 条**仅评测用**创意/美学 rubric（非分数、非 ontology）| formal_120 `codex_usage` |
| `do_not_copy_surface_style_policy.v0.1.yaml` | 保留机制、禁抄句式；美学分**不**作生成门槛 | formal_120 `codex_usage` |

## 硬边界 / boundaries

- 全部 registry `eval_only: true` / `ontology_truth: false`；**不写 KE / Serving / RAG / DIFY / ABox / TBox**。
- 创意/启发/美学字段只是**阅卷 rubric**（评测维度，非预打分），不作 `production_servable`、不作 `generation_allowed` 条件。
- expert review 原文**只索引不改判**（行区间 + digest 引用）。
- 每条 anti 至少 1 个 `failure_code`；每条 borderline 至少 1 个 `repair_reason`；P0-00 anti 绑控制面失败码。
- EvidencePolicyOutbox 15 例保持 owner，**0 条**并入 GeneralKnowledgeBase。

## 校验 / checker

```bash
python3 ci/checkers/check_judge_calibration_against_grc.py --live --report-out ci/reports/judge_calibration_against_grc_report.v0.1.json
python3 ci/checkers/check_judge_calibration_against_grc.py --selftest
```

checker **独立重算** P1（32 文件字节一致）+ P2（枚举已落 + 15 evidence 不入 GKB）不开子进程；对 registry 做
exactly-once 覆盖 + 无跨表重复 + 字段级校验；fail-closed（`python -O` 拒跑）；positive + 11 negative fixtures。

## 下一步 / next

`ready_for_canary_40_execution: true`；`generation_3600_unlocked: false`。下一步 = P4 `GKB-CANARY-40-GENERATION-AND-GATE-001`
（在其自有 brief + 授权下）。**不**解锁 3600 / CandidatePack / KE / Serving / RAG / DIFY。
