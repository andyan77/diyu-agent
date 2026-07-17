# M2 关闭报告 v1（CLOSED_PASS）

- 里程碑：M2（P2 阶段，覆盖 E0b + E0c，plan v2.4 §三 3.2 / v2.5）
- 被接受候选：`5ce595de7eb48fcf04178651f84400b0411134be`（v5）
- 会话：4d7e088b-945e-4903-844a-790379e740d2（claude-fable-5；发起人手动启动例外——SUPERSESSION_LEDGER §7 行 1 / journal seq18 三处登记）
- 结果：typed PASS ×2（STAGE_DECISION 03b8130b4843… / CLOSEOUT_RECEIPT 5eaec1a640ea…），逐字段比对零分叉

## 真实 S0 运行（S0M2-RUN-001）

六个确定性卫生门全部 PASS 且全链可复算（`s0_run.py verify-all`）：单一派工来源 100%、派工-材料零错配、整批硬否决指标在位、
首次响应不可变留存（锚提交 1c4f8153 逐字段语义证明 + 本地硬门控 label_changes==4 且全为合同标签 `gate1-v4-author-raw-v1`）、
调用与成本溯源完备（12 事件预登记精确匹配、DeepSeek 三回执费率算术复算、密钥零回显零入库）、Gate1 方案冒名计数为零。

**诚实基线**：内容质量按判全批套路化如实落盘（first_acceptance_rate=0.0 / formulaic_rate=1.0，4/4 评审 C 级不批准）——
S0 出口是卫生门不是质量门（真源 stage_and_kill.v2 exit_requires），未发生任何洗绿或重写。
M0 与 V1.1 均保持诚实 NOT_QUALIFIED。

**遥测**：cost_throughput_model 落盘且 blocking_semantics=NONE_DIAGNOSTIC_ONLY（拨付制，非阻断）；
`telemetry_complete=false` 如实保留（unavailable_paths 非空）——**不得被表述为完备**，两轮外审均确认此为合同内诚实呈现。

## 审核轮次（P1 §16：审查随候选更替失效）

| 轮 | Fable | Codex-GPT | 候选 |
|---|---|---|---|
| R1 | 载体三形态受阻（子代理注入→v2 不可签；嵌套 headless 无 Bash 诚实拒判；沙箱豁免被拒）→ 发起人裁决子代理载体 + v2.1 诚实分层 | REJECT（2 BLOCKING：锚证明不严、输出 schema 与隔离键互斥） | e2e81cd |
| R2 | ACCEPT（v2.1 签字，归档） | REJECT（1 BLOCKING：候选内 BOUNDARY_SMOKE_REPORT.v1 过期，白名单仅 M1 转录不能为含 R1 转录的候选作证；3 ADVISORY） | 0065887 |
| R3 | **ACCEPT**（回执 7dc3cb446583） | **ACCEPT**（回执 c8e0fc36633d） | **5ce595d** |

R3 双审对同一候选、同一三 manifest 摘要（INPUT 44612f0d… 11 项 / OUTPUT 7fafe044… 50 项 / EVIDENCE 86f70c75… 19 项）独立复算一致。
R2 修复：边界冒烟 v3（候选树现场重跑，模式级白名单=定义工具/攻击测试源码+pycache+M1/M2 codex 转录 events/last_message，零数据命中）；
锚点门本地 fail-closed（+4 条 spine 负测试，套件 49→53）；审查请求书清单指向修正。

## 遗留 ADVISORY（如实登记，均非阻断）

1. **Fable 载体模型**：requested=fable，actual=claude-opus-4-8（子代理载体运行时如实自报；发起人载体豁免裁决已知情此差异，回执与台账补遗均披露）。
2. **验证回执位于审查包提交**：VERIFICATION_RECEIPTS.M2.v3.json 在 b9e7c52 而非候选树内——既定"清单+回执在审查提交回指候选"模式（REVIEW_REQUEST.v3 §0d），双审判非缺陷。
3. **残留扫描计数时点**（Codex R3）：BOUNDARY_SMOKE_REPORT.v3/RESIDUAL v3 的 tracked=2893 为父树时点，候选树为 2904；11 个新增全部归类 DOCUMENTATION，Codex 现场对候选树复扫 exit 0，判定不变。**后续里程碑应在完整最终树暂存后再跑跟踪面扫描或登记候选树重放**。
4. **telemetry_complete=false**：见上，诚实保留。
5. **Codex R1 遗留 ADVISORORY**：M1 八件套重放需历史 HEAD（入口面复核时注意）；R3 已在历史入口头 6b21348 复验 M1 关闭链有效。
6. **Fable R2 遗留 ADVISORY**："五键"行文（v2.1 实为六键含条件披露）——本报告予以更正记载。

## 关闭机制注记

- **清单槽位**：本轮审查期清单以 *_MANIFEST.v3.json 命名（REVIEW_REQUEST.v3 所指）；关闭时按 M1 槽位复用惯例将**字节等同**内容落入 v2 槽（resolve_versioned 协议只认 v2/v1），manifest_digest 不变；R2 期 v2 槽原内容由 git 历史（4d36204）保存。v3 文件保留作审查期原名，与 v2 槽逐字节相同。
- **spine 候选清单闭环重建**：stage_actual_state 的 S0 登记按合同注记在双签后落盘，必然使候选期 spine 清单（80 项，含 calibration/ 钉扎）对活树漂移；关闭树上按其自有 build/verify 协议重建（80 项，digest 6fb6d7f6…），候选期 blob 由 OUTPUT 清单在候选提交 5ce595d 处永久钉扎、git 历史不可变。登记后的 stage_actual_state 与重建后清单另存 snapshots/close/ 审计快照。
- **单键澄清**：Fable R3 隔离声明 `auto_memory_disabled_or_not_applicable` 初报 false 系连词误读，审查者自行核验 schema 析取语义后出具 true（注入存在性由 before_launch=false + 披露专责承载）；全程问答 verbatim 见 FABLE_R3_ATTESTATION_CLARIFICATION.v1.md，裁决/findings/披露零改动。
- **发起人裁决 ×3**（均已三处登记）：手动启动例外（M2-only）；DeepSeek 密钥脚本进程内读（M2-S0 only，零回显零入库）；Fable 子代理载体豁免（v2.1 诚实分层）。
- **停机线纪律**：零 STOP 触发；零重试洗绿；journal 26 条链 VALID（关闭记录随关闭提交追加）。
- **就绪集**：M3 = READY（唯一后继）；M6 = WAITING（route_frozen 未冻结，正确阻塞）；其余按依赖 WAITING。M3/M6 只能由会话外监督器经加固后的 launcher 另启——本会话在关闭后立即退出。

## 遥测支出（非阻断登记）

DeepSeek 真实调用 3 次（S0），合计 USD 0.00037688 ≈ CNY 0.0030（30 元/UTC 日硬顶余量充足）；
Claude/Codex 审查令牌与墙钟遥测见 cost_throughput_model.v1.json 与各签字回执 call_receipt。
