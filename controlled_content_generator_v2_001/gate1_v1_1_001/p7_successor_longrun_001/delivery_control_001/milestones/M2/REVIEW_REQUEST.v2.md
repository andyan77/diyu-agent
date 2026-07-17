# M2 独立审核请求书 v2（R2：候选 v4）

审核对象：**M2 候选提交 `0065887d0b2f8424d32d235707f2afc35ed258fc`**（分支 agent/gate1-v1-1-successor-longrun）。
三 manifest：INPUT `493a1841d55f7f13…`（11 项）/ OUTPUT `1d8e09036b36f64e…`（46 项）/ EVIDENCE `e9a60ac80d458223…`（17 项），完整摘要见 `milestones/M2/*_MANIFEST.v1.json`。

## R2 增量必核（R1 双审后修复）

0a. Codex R1 BLOCKING-1 修复：s0_run.py `_anchor_semantic_diff` 对锚提交 blob 的逐字段证明是否严密（豁免面是否恰好一个标签字段）；stage_decision gate_notes 是否登记锚证据。
0b. Codex R1 BLOCKING-2 修复：codex_review_output.schema.v2.json 隔离五键 + 条件披露是否自洽。
0c. 发起人载体豁免落地（journal seq25 + SUPERSESSION_LEDGER §7 第三行）：signer_receipt.v2.1 是否为诚实分层（false 强制披露）而非放宽四键常量；receipts/checker 分发与 5 条正负测试。

## 必核维度（8）

1. **启动形态例外的登记完备性**：M2 会话为发起人手动启动（launcher --start 未运行）。核 SUPERSESSION_LEDGER §7 + journal seq18 + SESSION_IDENTITY.M2 launch_provenance 三处登记一致、例外范围仅限 M2、launch_record.v2 常量确使诚实补录不可能（不是作者偷懒）。
2. **入口面**：M1 CLOSED_PASS 链有效（八件套/typed/双签/ready-set）；checker M2 PRE_REVIEW 三域 PASS 可复算。
3. **真实 S0 六键逐项**：`eval_audit_spine_001/evidence/s0_m2_real_run_001/` 全链可复算（`python3 …/tools/s0_run.py verify-all` 必须 PASS）；首次尝试在门运行前提交（git log 顺序 1c4f815 → 4fcb568 可证）；S0 first_response_retained 门现已机械绑定首次尝试锚提交 1c4f8153 的原始 blob：逐字段语义一致（唯一豁免字段 = attempts[*].schema_version 解析标签，恰 4 处；文本与 fact_ids 值逐字节一致，但注意锚后 git diff 还含 fact_ids 数组换行重排——语义中性，已由门做解析级证明而非字节 diff 声明）。请复算该门与锚 blob。
4. **记账门**：12 事件与预登记清单精确匹配、费率卡复算、DeepSeek 三回执真实（provider_call_id/usage/cost 与费率算术一致）；密钥零回显零入库（grep 全 run 目录无 key 形态字符串）。
5. **诚实基线**：内容评审判全批套路化（first_acceptance_rate=0.0）未被洗绿、未重写；批质量与 S0 卫生门的边界解释是否成立（S0 六键不含批质量门，真源 stage_and_kill.v2 exit_requires）。
6. **遥测非阻断**：cost_throughput_model 的 blocking_semantics=NONE_DIAGNOSTIC_ONLY；全库无预算阻断门复辟（STOP_BUDGET 等键零出现于活跃合同）。
7. **边界冒烟**：BOUNDARY_SMOKE_REPORT 五子检查可复跑；标记字面量自引用白名单规则是否过宽（10 处逐一核对）。
8. **M1 时代绑定演进**：候选 v2 对 3 个测试与 spine 候选清单的重绑定是否合法演进而非放宽验收（对照 e2e81cd 提交信息与 STATE_EXPECTATION 真源）。

## 对抗性抽查（自选 ≥3）

例：伪造 12 事件之外的第 13 条能否被记账门拦；改 stage_decision gates 任一为 false 后 verify-all 是否 FAIL；S0 材料是否夹带真实品牌/人物/密封内容；DeepSeek spend ledger 与回执金额是否一致；журnal 哈希链断点检测。

## 裁决纪律

任何 BLOCKING finding → verdict 不得为 ACCEPT；宁 REJECT 不假绿。ADVISORY 如实列出。签字按 `schema/signer_receipt.v2.schema.json`（绑定 milestone_id=M2、product_scope=SHARED、候选提交、三 manifest 摘要、隔离声明五键）。


## 签字 schema 说明（R2）

Fable 审查者以子代理为载体时按 `schema/signer_receipt.v2.1.schema.json` 签字（发起人 2026-07-17 裁决）：`auto_memory_disabled_before_launch` 如实填写；为 false 必须在 `auto_memory_injection_disclosure` 披露注入内容/来源/关系/是否采用。Codex 按 v2 全真声明签字，最终消息符合 `milestones/M2/codex_review_output.schema.v2.json`。
