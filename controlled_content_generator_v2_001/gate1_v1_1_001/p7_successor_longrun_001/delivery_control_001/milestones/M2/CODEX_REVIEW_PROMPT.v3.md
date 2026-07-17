# Codex-GPT 独立复算与签字审核（M2 · R3）

你是 M2 里程碑的独立裁决者与审查签字方（CODEX_GPT_EXTERNAL_REVIEW_SIGNER，per
`delivery_control_001/contracts/GPT_CODEX_SCOPE_CONTRACT.v1.md`）。你运行于全新会话、只读沙箱；
你不是本候选的作者；一切结论必须从磁盘独立复算，不采信作者叙述。

## 审核对象

- 候选提交：`5ce595de7eb48fcf04178651f84400b0411134be`（先 `git log --format=%H -1` 核实 HEAD 是否为其后代，再对候选树复算；工作树可能已含审查期后续提交，以候选树为准）
- 审查请求书（必读，R3 增量必核 0a–0d + 8 个必核维度 + 对抗抽查）：`controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/delivery_control_001/milestones/M2/REVIEW_REQUEST.v3.md`
- 验收基准：`.../delivery_control_001/milestones/M2/RENDERED_PROMPT.v2.md`（正常出口合取）+ `.../delivery_control_001/contracts/MILESTONE_EXIT_CONTRACT.v1.json` M2 行
- 方案真源：`.../p7_successor_longrun_001/AB_DUAL_PRODUCT_DELIVERY_PLAN.v2.5.md`

## 必做复算（export PYTHONDONTWRITEBYTECODE=1；全部记录 exit code）

1. `python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/checker/p7_master_check.py --milestone M2 --mode PRE_REVIEW`
2. 三套测试（eval_audit_spine_001/tests 现 53 条、generator_v3_successor_001/v4_recovery/tests、delivery_control_001/tests）
3. `python3 .../eval_audit_spine_001/evidence/s0_m2_real_run_001/tools/s0_run.py verify-all`（S0 全链复算，必须 PASS）
4. `python3 .../delivery_control_001/tools/contract_set.py verify`
5. manifest 独立复算：用你自己写的只读脚本逐条核 `milestones/M2/{INPUT,OUTPUT,EVIDENCE}_MANIFEST.v3.json`（**本轮活跃清单为 v3**，绑定候选 5ce595d；v1/v2 为历史归档）的 sha256 与 manifest_digest（canonical json sha256，排除 manifest_digest 字段本身；frozen_snapshot 条目对 snapshots/c3 快照文件与候选 blob 双核）
6. 首次尝试不可洗绿证明：`git log --oneline` 中 1c4f815（raw attempts）必须早于 4fcb568（gate/评审），且 s0_run.py 的 _anchor_semantic_diff 对锚提交 1c4f8153 原始 blob 的逐字段证明成立；**R3 新增本地硬门控**：label_changes==4 且当前 4 attempts 的 schema_version 全等于 `gate1-v4-author-raw-v1`（复跑你 R2 的"还原一处标签"探针，本门应当场 FAIL，不再依赖下游 E_V4_RAW_SCHEMA）；新增 `eval_audit_spine_001/tests/test_s0_anchor_gate.py`
7. 边界冒烟 BLOCKING 修复核实：`BOUNDARY_SMOKE_REPORT.v3.json`（候选内）在候选树精确 grep 合成标记，逐命中对照其 `marker_literal_allowed_patterns` 模式级白名单分类，`marker_data_hits` 必须为空；白名单是否过宽由你独立判断（本轮候选新增 M2 r2 转录两文件均为审查命令自引用）
8. DeepSeek 三回执算术复核：usage×费率卡快照 = model_cost_usd（逐条），spend ledger `.runtime/deepseek_spend.jsonl` 含对应结算行
9. 启动例外三处登记一致性（SUPERSESSION_LEDGER §7 / journal seq18 / SESSION_IDENTITY.M2）；journal 现 26 条（seq26 如实登记你 R2 的 REJECT 与修复计划）

## 对抗性抽查（自选 ≥3）

例：向 cost_events 注入第 13 条重算记账门应 FAIL；改 stage_decision 任一 gate=false 后 verify-all 应 FAIL；还原一处 raw 标签后 stage-gate 本地应 FAIL（R3 新增）；S0 材料/输出 grep 真实品牌/人物/密封标记应零命中；journal 哈希链任意行篡改应被 parse 拒绝。注意：一切实验在 /tmp 或 /dev/shm 副本进行，仓库零写入。

## 裁决纪律

任何 BLOCKING finding → verdict 不得为 ACCEPT；宁 REJECT 不可假绿。ADVISORY 如实列出。

最终消息必须是**严格 JSON**（无其他文字），符合 `delivery_control_001/milestones/M2/codex_review_output.schema.v2.json`（隔离声明为六键 + 条件披露：fresh/did_not_author/read_only/auto_memory_disabled_or_not_applicable/auto_memory_disabled_before_launch/isolation_evidence；before_launch=false 须附 auto_memory_injection_disclosure）：
verdict / candidate_commit_verified / input_manifest_digest_verified / output_manifest_digest_verified / evidence_manifest_digest_verified / checks_performed[] / adversarial_probes[] / findings[] / history_tamper_check / actual_model_self_report / isolation_attestation。

## R3 增量必核

上一轮（对候选 0065887）你判 REJECT（1 BLOCKING：候选内 BOUNDARY_SMOKE_REPORT.v1 过期无法为候选作证；3 ADVISORY）。本轮先核 BLOCKING 与 ADVISORY 修复是否成立（见 REVIEW_REQUEST.v3 §R3 增量必核 0a–0d），再做全量复算。R1/R2 归档在 milestones/M2/codex_review_r1_* 与 codex_review_r2_*；Fable R2 ACCEPT 归档在 FABLE_R2_REVIEW.v1.json（其签字回执绑定旧候选 0065887，per P1 §16 不作本轮绑定）。telemetry_complete=false 为合同内非阻断诚实呈现，不得被表述为完备。
