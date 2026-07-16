# 可信评测脊柱与 v4 恢复实现 · 独立审核请求 v1

## 审核对象

本请求针对同一候选实现提交及 `release/candidate_manifest.v1.json` 的同一摘要。提交哈希在实现提交完成后写入两份审核报告；候选清单排除审核报告和生成证据自身，确保两名评审看到相同代码、合同、量规、模式与测试。

审核范围包括：

- `EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.1.md`；
- `eval_audit_spine_001/{contract,rubric,schema,spine,fixtures,tests,calibration}`；
- `generator_v3_successor_001/v4_recovery/**`；
- v4 事实到 UTF-8 原文片段的闭包，以及纤维/成分/结构/耐久已知风险词注册门；
- 唯一总检查入口 `p7_master_check.py` 的新增检查节；
- R5 只读影子复算与候选清单。

旧 R1–R5、冻结 `g3_*` 模块和 V1.1 标准不在可改范围，只能作为只读证据。

## 必需的两份独立审核

1. `METHODOLOGY`：检查自然/挑战与开发/验证/隐藏隔离、参考断言与主张原子化各自校准、FP/FN和置信上界、套路构念量规、弃权、披露/省略误导、成本与 kill 条件；
2. `IMPLEMENTATION`：重新运行测试和总检查，检查摘要闭包、唯一测试分配真源、首次尝试、全批硬否决门、遥测、分母、历史只读和反向自测。

两名评审不得参与各自审核范围的实现，不得在提交前读取对方报告。报告必须符合 `schema/independent_review.v1.schema.json`，绑定相同 `target_commit` 与 `target_manifest_digest`。

## 重算命令

```bash
python3 controlled_content_generator_v2_001/generator_v3_successor_001/tests/test_g3.py
python3 -m unittest discover controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/tests -p 'test_*.py'
python3 -m unittest discover controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/tests -p 'test_*.py'
python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/checker/p7_master_check.py
python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/checker/p7_master_check.py --selftest
```

## 判定边界

审核可以批准“实现工件进入 M0 数据建设/资格准备”，但不得批准或暗示：M0 已通过、评测器已可信、生成器已达到 V1.1、预算已批准、开放120/隐藏40/300已运行。若发现阻断项，只允许对原阻断项进行一次定向复审。
