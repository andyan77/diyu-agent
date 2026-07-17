# M2 独立审核请求书 v3（R3：候选 v5）

审核对象：**M2 候选提交 `5ce595de7eb48fcf04178651f84400b0411134be`**（分支 agent/gate1-v1-1-successor-longrun）。
三 manifest（完整摘要见 `milestones/M2/*_MANIFEST.v3.json`——本轮活跃清单为 **v3**；v1 绑定 e2e81cd、v2 绑定 0065887，均为历史归档不作本轮绑定）：

- INPUT `44612f0de6aa286d17979310359ac7718aae41626619e20e66dda22c454451f8`（11 项，输入面与 R1/R2 相同）
- OUTPUT `7fafe0441d5f3b0af5420c2a39176a7759b592638eacc8d42094ae9473974aba`（50 项，基线 6b21348 → 候选，journal/stage_actual_state 经 snapshots/c3 冻结）
- EVIDENCE `86f70c7599b82aa228f5934fa95b457c55bf319a325b56702a033c22788a9611`（19 项）

## R3 增量必核（Codex R2 REJECT 后修复）

0a. **Codex R2 BLOCKING-1 修复**：候选内 `BOUNDARY_SMOKE_REPORT.v3.json` 于本候选树现场重跑五子检查；标记字面量白名单升级为**模式级**（定义工具/攻击测试源码 + __pycache__ + M1/M2 codex 评审转录 events/last_message），`marker_data_hits` 必须为空。请在候选树上精确 grep 合成标记、逐命中对照 v3 的 `marker_literal_allowed_patterns` 分类；v1（冻结于 67eeb71、白名单仅 M1 转录）与 v2（未入候选的工作产物）均已归档不作绑定。
0b. **Codex R2 ADVISORY 修复**：`s0_run.py _anchor_semantic_diff` 现本地硬性要求 `label_changes==4` 且当前 4 个 attempts 的 schema_version 全等于合同标签 `gate1-v4-author-raw-v1`（少改/多改/改错在本门即 FAIL，不再依赖下游 E_V4_RAW_SCHEMA 兜底）；新增 `eval_audit_spine_001/tests/test_s0_anchor_gate.py` 4 条正负测试。请复跑 R2 的"还原一处标签"探针，确认 stage-gate 本地即拒。
0c. **清单指向修正**：本请求书指向 v3 清单文件（R2 请求书误指 v1 文件而广告 v2 摘要）。
0d. **R2 双审归档完整性**：Fable R2 ACCEPT（`FABLE_R2_REVIEW.v1.json` + v2.1 签字回执）与 Codex R2 REJECT（`codex_review_r2_*`）随候选归档、journal seq26 如实登记 REJECT 与修复计划；归档回执绑定旧候选 0065887，按 P1 §16 不作本轮绑定。

## 必核维度（8）

1. **启动形态例外的登记完备性**：M2 会话为发起人手动启动（launcher --start 未运行）。核 SUPERSESSION_LEDGER §7 + journal seq18 + SESSION_IDENTITY.M2 launch_provenance 三处登记一致、例外范围仅限 M2、launch_record.v2 常量确使诚实补录不可能。
2. **入口面**：M1 CLOSED_PASS 链有效（八件套/typed/双签/ready-set）；checker M2 PRE_REVIEW 三域 PASS 可复算。
3. **真实 S0 六键逐项**：`eval_audit_spine_001/evidence/s0_m2_real_run_001/` 全链可复算（`python3 …/tools/s0_run.py verify-all` 必须 PASS）；首次尝试在门运行前提交（git log 顺序 1c4f815 → 4fcb568 可证）；锚点门逐字段语义证明 + 本地标签硬门控（见 0b）。
4. **记账门**：12 事件与预登记清单精确匹配、费率卡复算、DeepSeek 三回执真实（provider_call_id/usage/cost 与费率算术一致）；密钥零回显零入库。
5. **诚实基线**：内容评审判全批套路化（first_acceptance_rate=0.0）未被洗绿、未重写；S0 六键不含批质量门（真源 stage_and_kill.v2 exit_requires）。
6. **遥测非阻断**：cost_throughput_model 的 blocking_semantics=NONE_DIAGNOSTIC_ONLY；telemetry_complete=false 如实保留；全库无预算阻断门复辟。
7. **边界冒烟**：BOUNDARY_SMOKE_REPORT.**v3** 五子检查在候选树可复跑；模式级白名单是否过宽（候选 grep 命中逐一核对；本轮候选新增 M2 r2 转录两文件均为审查命令自引用非密封载荷）。
8. **M1 时代绑定演进**：3 个测试与 spine 候选清单（现 80 项，含新锚点门测试）的重绑定是否合法演进而非放宽验收（对照 STATE_EXPECTATION 真源）。

## 对抗性抽查（自选 ≥3）

例：伪造 12 事件之外的第 13 条能否被记账门拦；改 stage_decision gates 任一为 false 后 verify-all 是否 FAIL；还原一处 raw 标签后 stage-gate 是否本地即拒（R3 新增门控）；S0 材料是否夹带真实品牌/人物/密封内容；DeepSeek spend ledger 与回执金额一致性；journal 哈希链断点检测（现 26 条）。

## 裁决纪律

任何 BLOCKING finding → verdict 不得为 ACCEPT；宁 REJECT 不假绿。ADVISORY 如实列出。

## 签字 schema 说明（R3）

Fable 审查者以子代理为载体时按 `schema/signer_receipt.v2.1.schema.json` 签字（发起人 2026-07-17 裁决）：`auto_memory_disabled_before_launch` 如实填写；为 false 必须在 `auto_memory_injection_disclosure` 披露注入内容/来源/关系/是否采用。Codex 按 v2 全真声明签字，最终消息符合 `milestones/M2/codex_review_output.schema.v2.json`。
