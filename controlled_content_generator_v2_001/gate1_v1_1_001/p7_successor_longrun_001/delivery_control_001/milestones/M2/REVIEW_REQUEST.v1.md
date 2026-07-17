# M2 独立审核请求书 v1

审核对象：**M2 候选提交 `e2e81cdc5d0e4b4d68690b2f96a7cca5c9f8ae89`**（分支 agent/gate1-v1-1-successor-longrun）。
三 manifest：INPUT `e38f83835db3d02f…`（11 项）/ OUTPUT `6b526c910d7ed649…`（41 项）/ EVIDENCE `95abebfbc9bf9a5d…`（13 项），完整摘要见 `milestones/M2/*_MANIFEST.v1.json`。

## 必核维度（8）

1. **启动形态例外的登记完备性**：M2 会话为发起人手动启动（launcher --start 未运行）。核 SUPERSESSION_LEDGER §7 + journal seq18 + SESSION_IDENTITY.M2 launch_provenance 三处登记一致、例外范围仅限 M2、launch_record.v2 常量确使诚实补录不可能（不是作者偷懒）。
2. **入口面**：M1 CLOSED_PASS 链有效（八件套/typed/双签/ready-set）；checker M2 PRE_REVIEW 三域 PASS 可复算。
3. **真实 S0 六键逐项**：`eval_audit_spine_001/evidence/s0_m2_real_run_001/` 全链可复算（`python3 …/tools/s0_run.py verify-all` 必须 PASS）；首次尝试在门运行前提交（git log 顺序 1c4f815 → 4fcb568 可证）；schema_version 标签修正是否真的未触内容（git diff 逐字核）。
4. **记账门**：12 事件与预登记清单精确匹配、费率卡复算、DeepSeek 三回执真实（provider_call_id/usage/cost 与费率算术一致）；密钥零回显零入库（grep 全 run 目录无 key 形态字符串）。
5. **诚实基线**：内容评审判全批套路化（first_acceptance_rate=0.0）未被洗绿、未重写；批质量与 S0 卫生门的边界解释是否成立（S0 六键不含批质量门，真源 stage_and_kill.v2 exit_requires）。
6. **遥测非阻断**：cost_throughput_model 的 blocking_semantics=NONE_DIAGNOSTIC_ONLY；全库无预算阻断门复辟（STOP_BUDGET 等键零出现于活跃合同）。
7. **边界冒烟**：BOUNDARY_SMOKE_REPORT 五子检查可复跑；标记字面量自引用白名单规则是否过宽（10 处逐一核对）。
8. **M1 时代绑定演进**：候选 v2 对 3 个测试与 spine 候选清单的重绑定是否合法演进而非放宽验收（对照 e2e81cd 提交信息与 STATE_EXPECTATION 真源）。

## 对抗性抽查（自选 ≥3）

例：伪造 12 事件之外的第 13 条能否被记账门拦；改 stage_decision gates 任一为 false 后 verify-all 是否 FAIL；S0 材料是否夹带真实品牌/人物/密封内容；DeepSeek spend ledger 与回执金额是否一致；журnal 哈希链断点检测。

## 裁决纪律

任何 BLOCKING finding → verdict 不得为 ACCEPT；宁 REJECT 不假绿。ADVISORY 如实列出。签字按 `schema/signer_receipt.v2.schema.json`（绑定 milestone_id=M2、product_scope=SHARED、候选提交、三 manifest 摘要、隔离声明五键）。
