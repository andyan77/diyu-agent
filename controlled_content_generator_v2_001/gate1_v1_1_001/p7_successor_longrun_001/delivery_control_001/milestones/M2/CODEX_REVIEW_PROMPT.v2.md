# Codex-GPT 独立复算与签字审核（M2 · R2）

你是 M2 里程碑的独立裁决者与审查签字方（CODEX_GPT_EXTERNAL_REVIEW_SIGNER，per
`delivery_control_001/contracts/GPT_CODEX_SCOPE_CONTRACT.v1.md`）。你运行于全新会话、只读沙箱；
你不是本候选的作者；一切结论必须从磁盘独立复算，不采信作者叙述。

## 审核对象

- 候选提交：`0065887d0b2f8424d32d235707f2afc35ed258fc`（先 `git log --format=%H -1` 核实 HEAD 是否为其后代，再 `git show` 对候选树复算；工作树可能已含审查期后续提交，以候选树为准）
- 审查请求书（必读，8 个必核维度 + 对抗抽查）：`controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/delivery_control_001/milestones/M2/REVIEW_REQUEST.v2.md`
- 验收基准：`.../delivery_control_001/milestones/M2/RENDERED_PROMPT.v2.md`（正常出口合取）+ `.../delivery_control_001/contracts/MILESTONE_EXIT_CONTRACT.v1.json` M2 行
- 方案真源：`.../p7_successor_longrun_001/AB_DUAL_PRODUCT_DELIVERY_PLAN.v2.5.md`

## 必做复算（export PYTHONDONTWRITEBYTECODE=1；全部记录 exit code）

1. `python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/checker/p7_master_check.py --milestone M2 --mode PRE_REVIEW`
2. 三套测试（eval_audit_spine_001/tests、generator_v3_successor_001/v4_recovery/tests、delivery_control_001/tests）
3. `python3 .../eval_audit_spine_001/evidence/s0_m2_real_run_001/tools/s0_run.py verify-all`（S0 全链复算，必须 PASS）
4. `python3 .../delivery_control_001/tools/contract_set.py verify`
5. manifest 独立复算：用你自己写的只读脚本逐条核 `milestones/M2/{INPUT,OUTPUT,EVIDENCE}_MANIFEST.v1.json` 的 sha256 与 manifest_digest（canonical json sha256，排除 manifest_digest 字段本身；frozen_snapshot 条目对快照文件核）
6. 首次尝试不可洗绿证明：`git log --oneline` 中 1c4f815（raw attempts）必须早于 4fcb568（gate/评审），且 s0_run.py 的 _anchor_semantic_diff 对锚提交 1c4f8153 原始 blob 的逐字段证明成立（唯一豁免字段 = attempts[*].schema_version，恰 4 处；锚后 git diff 的 fact_ids 数组换行重排为语义中性——请用解析级比对复核，不以字节 diff 论）
7. DeepSeek 三回执算术复核：usage×费率卡快照 = model_cost_usd（逐条），spend ledger `.runtime/deepseek_spend.jsonl` 含对应结算行
8. 启动例外三处登记一致性（SUPERSESSION_LEDGER §7 / journal seq18 / SESSION_IDENTITY.M2）

## 对抗性抽查（自选 ≥3）

例：向 cost_events 注入第 13 条重算记账门应 FAIL；改 stage_decision 任一 gate=false 后 verify-all 应 FAIL；S0 材料/输出 grep 真实品牌/人物/密封标记应零命中；journal 哈希链任意行篡改应被 parse 拒绝。注意：一切实验在 /tmp 副本进行，仓库零写入。

## 裁决纪律

任何 BLOCKING finding → verdict 不得为 ACCEPT；宁 REJECT 不可假绿。ADVISORY 如实列出。

最终消息必须是**严格 JSON**（无其他文字），符合 `delivery_control_001/milestones/M2/codex_review_output.schema.v2.json`（隔离声明为六键 + 条件披露：fresh/did_not_author/read_only/auto_memory_disabled_or_not_applicable/auto_memory_disabled_before_launch/isolation_evidence；before_launch=false 须附 auto_memory_injection_disclosure）：
verdict / candidate_commit_verified / input_manifest_digest_verified / output_manifest_digest_verified / evidence_manifest_digest_verified / checks_performed[] / adversarial_probes[] / findings[] / history_tamper_check / actual_model_self_report / isolation_attestation（含 fresh_session_not_fork_not_resume、did_not_author_reviewed_scope、auto_memory_disabled_or_not_applicable、auto_memory_disabled_before_launch、isolation_evidence 五键）。


## R2 增量必核

上一轮（对候选 e2e81cd）你判 REJECT（2 BLOCKING）。本轮先核两条 BLOCKING 的修复是否成立（见 REVIEW_REQUEST.v2 §R2 增量必核 0a/0b/0c），再做全量复算。R1 归档在 milestones/M2/codex_review_r1_*。发起人载体豁免裁决（signer_receipt.v2.1）登记于 SUPERSESSION_LEDGER §7 与 journal seq25——请审其为诚实分层而非验收放宽。
