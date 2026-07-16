# Eval & Audit Spine 001

本目录承载可信评测与审计脊柱的合同、参考实现、反向测试和审核包。它把既有 P7 的冻结、失败留痕和指标复算能力，与待资格化的概率评测体系连接起来。

## 当前状态

```yaml
implementation_scope: contracts_schemas_reference_runtime_negative_tests_and_review_package
m0_status: NOT_QUALIFIED
runtime_modules_artifact_selftest_status: PASS
runtime_modules_measurement_qualification_status: NOT_QUALIFIED
gold_data_present: false
qualification_report_present: false
generator_repair_authorized_by_this_directory: false
external_calls_authorized: deepseek_formulaic_judge_only
external_daily_hard_ceiling: 30_CNY_per_UTC_day
external_connectivity_smoke: PASS_NOT_QUALIFICATION
```

这里的文件不能证明评测器已可信，也不能证明生成器已达到 V1.1。`calibration/M0_STATUS.v1.json` 是当前唯一资格状态真源。

## 目录职责

- `contract/`：实施边界、测量资格、阶段与停止、角色隔离、六格数据和成本合同；
- `rubric/`：事实证据、套路构念和披露义务的可执行判定程序；
- `schema/`：未来运行对象的机器可检验形状；
- `calibration/`：开发与密封资格清单，只存状态和摘要，不存伪造金标。
- `spine/`：确定性闭包、概率弃权边界、校准统计、成对套路度量、真实双审证据、分派、成本和阶段门参考实现；
- `scripts/`：受日预算保护的外部套路语义评审入口；密钥和运行账本不进入 Git 或候选清单；
- `fixtures/` 与 `tests/`：R5 已知风险种子及正反向测试；
- `evidence/`、`release/` 与 `review/`：只读影子复算、冻结清单和审核交付。

上述实现存在并不改变 M0 状态；它仍须真实独立金标、密封资格运行和预算审批。

## 权威顺序

1. 项目发起人的最新明确裁决（现行生效链：`AB_DUAL_PRODUCT_DELIVERY_PLAN.v2.5.md` @ 23f5fea，活跃合同指针见 `../delivery_control_001/ACTIVE_CONTRACT_SET.v1.json`）；
2. `diyu_content_composition_standard.v1.1.md`；
3. `EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.2.md`（v1.1 封存为历史）；
4. 本目录 `contract/`（活跃版本：`stage_and_kill.v2.json`、`cost_accounting.v2.json`、`measurement_qualification.v2.json`、`implementation_charter.v2.md`；v1 封存为历史）；
5. `rubric/` 与 `schema/`；
6. 校准和运行产物。

若发生冲突，必须显式修订后续版本，不得静默解释或追溯改写历史失败。

## 第一门边界

`gate1_test_assignment` 是合成资格测试的内部控制对象，不是正式内容编排计划。它不能绑定企业运行输入、不能进入发布链、不能自行批准候选、不能作为 300 条中的内容对象计数。

## 下一步进入条件

只有以下事项全部具备，才能从本地参考实现进入 M0 资格运行：

1. 密封数据保全角色到位；成本按拨付制全量记账（发起人按需拨付，无总体预算阻断门，记账缺失=停——裁决 #4）；已批准的 30 元/日 DeepSeek 开发调用预算仍为独立窄授权，不能替代记账义务；
2. 六格数据责任人与独立评审角色到位；
3. 开发金标和密封资格金标由不同流程物化（六步全序：题面冻结→双盲建标→金标冻结→方法冻结→盲预测→揭晓）；
4. M0 运行器与反向测试接受独立实现审核；
5. `M0_STATUS` 仍保持 `NOT_QUALIFIED`，直至真实资格报告合取通过。
