# S0 真实运行计划 v1（M2-C1b · S0_DETERMINISTIC_HYGIENE）

> 授权链：`delivery_control_001/milestones/M2/S0_REAL_RUN_AUTHORIZATION.v1.json`。
> 本运行是 **S0 确定性卫生阶段的真实执行**，不构成 M0/V1.1 任何资格声明；
> 批内全部对象为全新合成控制材料（gate1_test_assignment 语义，非正式内容编排计划）。

## 运行身份（冻结）

| 键 | 值 |
|---|---|
| run_id | `S0M2-RUN-001` |
| batch_id | `S0M2-BATCH-001` |
| assignment_set_id | `S0M2-ASSIGNMENT-SET-001` |
| profiles | CP01, CP02（冻结覆盖路径）+ CP04, CP07（family 默认路径） |
| 场景数 | 4（每场景恰一次首次尝试） |
| stage_scope | S0_DETERMINISTIC_HYGIENE（GATE1_QUALIFICATION 机器语义，仅作 S0 卫生证明） |

## 角色与模型

| 角色 | 承载 | 登记 |
|---|---|---|
| 作者（AUTHOR） | 本会话 claude-fable-5（`M2-S0-AUTHOR-FABLE5`，model_config_ref=`MODEL-CONFIG-S0M2-001`） | 每请求恰一次首次尝试；先提交后过门；不看门结果重写 = 禁止 |
| 内容评审（CONTENT_REVIEW） | 全新子代理（显式 model，AGENT_LEDGER.M2 登记） | 评审工时 = 子代理墙钟，计入 HUMAN_REVIEW 事件 |
| 事实评审（FACT_REVIEW） | 全新子代理（独立于内容评审与作者） | 同上 |
| 批级度量审计（METRICS_AUDIT） | 全新子代理（EVIDENCE_AUDITOR 角色） | 同上 |
| 套路语义评审 | DeepSeek（sanctioned 脚本，预算代理 30 元/UTC 日） | 3 次真实调用，MODEL_CALL 事件（回执完整） |

## 成本账范围声明（诚实边界）

eval-spine 成本账（`cost/`）只登记**可计费资源**：
1. 外部提供方调用（DeepSeek ×3，MODEL_CALL：令牌/费用可从费率卡快照精确复算）；
2. 模型角色评审工时（HUMAN_REVIEW ×9：4 内容 + 4 事实 + 1 批级度量审计；
   labor 费率 = 0 USD/小时——模型角色无人类劳务支出，这是真实劳务成本而非未知成本占位；
   角色推理发生在 Claude Code 会话/子代理内，无独立计费回执，属会话资源，
   以本节文字显式披露，不以零值伪造为 MODEL_CALL 事件）。

作者生成与确定性门/度量聚合的会话内计算**不进入**成本账（同上披露），
其完整过程账在 v4 遥测事件流（`telemetry/`）：usage/cost 以显式 unavailable 理由登记，
provider_call_id 采用**运行内标识符方案**（`s0m2:<event>:<对象>`，标识生成/计算行为本身，
非提供方签发回执号；DeepSeek 事件用提供方真实 provider_call_id）。

预登记（预占）纪律：`cost/expected_event_manifest.v1.json` 在任何生成/调用发生前落盘并提交，
12 条事件身份六元组冻结；`source_run_manifest_digest` 绑定值 = 冻结请求 bundle 的 `bundle_digest`
（运行前唯一可用的运行身份摘要；来源清单以同一值回绑）。实际事件与预登记不符 = 记账门 FAIL = S0 诚实失败。

## S0 六项出口 → 证据映射

| 出口键（冻结镜像） | 机器证据 |
|---|---|
| SINGLE_TEST_ASSIGNMENT_SOURCE_100_PERCENT | bundle 内 4 请求逐一绑定同一 allocate_test_assignments(assignment_set_id) 输出；`tools/s0_run.py verify-all` 复算 100% |
| ASSIGNMENT_MATERIAL_MISMATCH_COUNT_ZERO | 请求/分配/材料摘要三向闭合复算，错配计数 = 0 |
| WHOLE_BATCH_HARD_VETO_METRIC_PRESENT | gate_report.whole_batch_machine_hard_veto_zero + metrics.whole_batch_hard_veto_count 在位 |
| FIRST_PROVIDER_RESPONSE_IMMUTABLY_RETAINED | 首次尝试在门运行前提交（Git 不可变锚）+ 内容寻址 output_digest；DeepSeek 首个响应回执 response_digest 内容寻址落盘禁覆盖 |
| CALL_AND_COST_PROVENANCE_COMPLETE | accounting_integrity_gate PASS（12/12 完整事件，预登记/来源清单双匹配，费率卡复算） |
| GATE1_PLAN_IMPERSONATION_COUNT_ZERO | 每条 assignment 通过反冒充固定字段校验（not_formal_content_composition_plan=true 等）+ 禁用伪装字段名扫描，命中计数 = 0 |

六门布尔 → `spine.stage_gate.stage_decision(stage="S0")` → PASS/FAIL。
失败处置：STOP_S0_DETERMINISTIC_INTEGRITY 诚实关闭（FAIL/HONEST_STOP），不得重试洗绿。

## 材料红线自查

- 全部场景/材料/来源文本为本里程碑全新合成（工作台/陈列/库房/打包台操作记录体裁）；
- 零密封载荷、零隐藏材料、零真实客户数据、零旧 120/86/路线 60 引用；
- 零真实品牌/SKU/门店/人物事实；受众文本避开确定性已知风险声明注册表全部词条；
- 合成披露仅在 synthetic_disclosure 面，受众面零披露语（HF_DISCLOSURE_ON_AUDIENCE_SURFACE 防线）。
