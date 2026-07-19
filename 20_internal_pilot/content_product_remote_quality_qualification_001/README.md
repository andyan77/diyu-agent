# 20 项内容产品远程质量资格测试

终态：`FAIL_20_PRODUCT_REMOTE_QUALITY_QUALIFICATION`。

真实远程链已完成 100/100 项首次内容生产、100 次选择与审核导出，以及 20 次选择后局部修改。最终 100 项批次使用 246 次 DeepSeek 调用、费用 ¥0.897012；包含前置输出契约恢复在内，本任务共 382 次、¥1.369708。只发生 1 次无模型输出的同输入传输重试；质量重抽、旧第 10 包复用、真实客户数据和自动发布均为 0。

两名隔离审查者均盲判正确 100/100。服装品牌自媒体审查均分 84.79，企业新手审查均分 80.16；双审正式均分 82.48，100 项中 44 项达到 85 分。20 个产品没有一个同时满足“至少 4/5 达到 85 且产品均分不低于 85”，明显套话或近重复的两审并集为 68 项，固定结构支配多数；因此 Q20-A04、A05、A07、A09 失败。市场保守比较 15/20 至少基本相当，盲辨识和市场标准通过。

首次运行暴露的 Dify 输出契约问题及后续变体均已保留。按后续用户指令完成最小运行修复后，最终 100 项从头执行，没有复用失败输出。审查评分不使用证据编号、来源绑定或逐句证明作为扣分或硬否决依据。

主要证据：

- `evidence/official_remote_run/official_task_records.v1.jsonl`：100 项首次候选、选择、修改、审核导出、调用费用与错误
- `review/apparel_media_review.v1.json` 与 `review/enterprise_novice_review.v1.json`：两份独立百分制审查
- `result/remote_quality_qualification_result.v1.json`：20 项产品矩阵与 Q20-A01 至 A15
- `evidence/official_remote_run/model_cost_reconciliation.v1.json`：246 / 382 / 590 三层调用费用对账

本地复核：

```bash
python3 freeze_inputs.py --check
python3 qualification_runner.py selftest
python3 check_remote_quality_qualification.py
python3 check_remote_quality_qualification.py --selftest
```

`python3 -O check_remote_quality_qualification.py` 必须拒绝运行。所有 readiness flags 保持 `false`，“门店线下物料”仍为“暂未开放”。
