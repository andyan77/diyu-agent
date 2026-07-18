# M3-R1 恢复续跑 Prompt（唯一 resume 入口 · R3→R6）

> 本文件 = 发起人 2026-07-18 裁定「会话确不能续 → 落盘完整 INTERRUPTED_RESUMABLE 检查点 + 唯一 resume Prompt，新会话从磁盘续」的 resume 入口。
> 一个全新顶层会话逐字投放本 Prompt 即可从磁盘状态继续，无需任何会话记忆。

## 0. 身份与工作区

- 工作区：`/home/diyu/worktrees/gate1-longrun-001`
- 分支：`agent/gate1-v1-1-successor-longrun`
- 续跑基线 HEAD（预期）：`b3f5b2c`（M3-R1-R2 提交；如已合法快进则审计新增提交后绑定实际基线，不 reset）
- 任务性质：**M3 追加式恢复 R3-R6，不是 M4，不得运行 M0**
- 载体：本恢复由 claude-opus-4-8 承担（发起人 2026-07-18 Q1 记偏差，见 SUPERSESSION_LEDGER §7 与 recovery/SESSION_IDENTITY.M3_R1.v1.json）；跨模型双盲的两标注席/仲裁仍须隔离子代理独立。

## 1. 续跑前必读（磁盘真源，勿凭记忆）

1. `delivery_control_001/journal/RUN_JOURNAL.v1.jsonl` —— 末条应为 M3_R1_INTERRUPTED_RESUMABLE / state ACTIVE；先 `run_journal.py verify` 确认链 VALID。
2. `delivery_control_001/milestones/M3/recovery/M3_RECOVERY_STATUS.v1.json`（state=ACTIVE；M4 fail-closed 由此驱动）
3. `delivery_control_001/milestones/M3/recovery/RECOVERY_DECISIONS.v1.json` —— **发起人三裁定，续跑纪律的约束真源**（成本非停工门 / 会话额度耗尽=可恢复中断非 HONEST_STOP / HONEST_STOP 仅限三条件 / M4 拦截至全 close / 不得提前冻结或批量标注 schema 未完成数据）。
4. `delivery_control_001/milestones/M3/recovery/M3_RECOVERY_PROGRESS.v1.json` —— R0-R2 已完成清单 + R3-R6 待办 + 精确续跑点。
5. `m3_data_supply_001/plan/CAPACITY_AND_CONSTRUCTION_PLAN.v1.json` —— **R3 蓝图**：逐套逐模块目标、6 档 cross-module 复用档案、k≥2 高风险偏置变体构造、F5 Tier1、统计口径、密封双盲协议、逐套容量可行性（760≤1530 CONDITIONALLY_FEASIBLE）。
6. `m3_data_supply_001/schema/qual_gold_record.v1.schema.json` —— 9 模块 gold 记录契约（R3 建标须逐条合规）。
7. `eval_audit_spine_001/contract/measurement_qualification.v2.json` —— 逐套逐模块 M0 下限硬真源。
8. `m3_data_supply_001/tools/pre_m0_readiness.py` + checker `qual_data_readiness` 节 —— R4/R6 就绪硬门（缺回执/任一 FAIL/摘要篡改 → M3 FINAL fail-closed）。
9. `delivery_control_001/FORMAL_MODEL_RUN_CONTRACT.v1.md`（journal-before-write / 断言门控提交 / 密封红线 / 关闭八件套 / 双审）。
10. `delivery_control_001/milestones/M3/recovery/M3_RECOVERY_EXIT_ADDENDUM.v1.json`（原 23 出口键 + 就绪三键，只加严）。

## 2. 已完成（R0-R2，勿重做，勿改动）

| 提交 | 内容 |
|---|---|
| `8af997f` R0 | 恢复启动 + M4 fail-closed 硬门（ready_set.m3_recovery_active + launcher，9 测）+ 旧 QUAL 机械失败基线（6 测）+ SUPERSESSION_LEDGER §7 偏差登记 |
| `c96bb80` R1 | 供需矩阵 PRE_M0_DATA_REQUIREMENT_MATRIX + pre_m0_readiness 就绪评估器 + checker FINAL scope-A 节 qual_data_readiness + pre_m0_data_readiness schema + 出口附录（11 测） |
| `b3f5b2c` R2 | 9 模块 qual_gold_record schema + CAPACITY_AND_CONSTRUCTION_PLAN + qual_runner 0.4→_build_variant_tasks 修复 + RECOVERY_DECISIONS（12 测） |

**旧 M3 v1 关闭工件全部封存不改不揭晓**（candidate 84f8fc50 / closeout 07414172 / anchor 1fbddc48 / HANDOFF a343b7ae / 旧 QUAL 回执）；旧 QUAL=SUPERSEDED_UNREVEALED_INSUFFICIENT_FOR_M0；旧 HANDOFF 已追加式暂停。

## 3. 待做（R3→R6，本次续跑目标）

### R3 —— 构建新版双密封 QUAL-A/B（generation 独立编号，避免与 M4 方法版本混淆）
按 CAPACITY_AND_CONSTRUCTION_PLAN + qual_gold_record schema，为 A/B 各套建 9 模块 gold：
- **密封双盲纪律（硬）**：主编排会话零明文接触；明文只由 custody 工具 + 隔离标注会话读；两标注席（A=Codex-GPT / B=Opus-4.8）互不见标签；仲裁席看匿名化分歧；每会话记录模型/提供方/session/可见范围/成本事件；作者不签自身。
- 每 gold 记录：≥2 独立 gold_review_provenance（2 不同身份）+ 分歧裁决；cross_module_reuse 登记（禁同分母重复计数）；challenge 变体绑真源（可追溯矛盾注入/边界省略/风险提升/合法负控；**禁编造新领域事实**）。
- 变体构造用已修复的 `qual_runner._build_variant_tasks`（k≥2 高风险偏置，无 0.4）；**注意 R3 须先同步扩展 annexC 构造模板以支持新 kinds（CONTRADICTION_INJECT/RISK_ELEVATE/EVIDENCE_INSUFFICIENT/BOUNDARY_OMIT/OMISSION_MISLEAD/LEGAL_NEGATIVE_CONTROL）**，且为 7 个新模块（reference/atomization/fact_chain/formulaic/disclosure/omission/review）各建构造+标注逻辑（现 qual_runner 仅 risk+entailment）。
- 金标构建保留自身 FP/FN、争议率、独立审核预算；LLM 标签不当确定真值。
- 某 generation 冻结后计数不足：不改该冻结 generation，追加标记不足并建下一 generation；迭代至两套分别达标，或**机械证明合法材料容量不足**（含 Tier1 F5 补量后仍不足）→ HONEST_STOP。
- **不得提前冻结或批量标注 schema 未完成的数据**（schema 已在 R2 完成，可建）。

### R4 —— 预运行资格验证（保全工具零泄漏）
custody 工具为 A/B 分别输出**公开聚合计数**（零明文），喂 `pre_m0_readiness.evaluate_set_readiness` 落 `QUAL_{A,B}_READINESS_RECEIPT.v1.json`：每 required key required/actual/delta/pass、9 模块 gold 覆盖、5 家族、双标一致率/争议率、A/B 互斥、DEV 隔离、QUAL_ORDER 新 generation 顺序、denylist+sealed scan、主会话零明文证明。**两套 verdict 均 PASS 才可进候选审核**。

### R5 —— 测试全套 + 两份新独立审核
- 测试不得减少：eval spine / delivery control / v4 recovery 原测 + 本恢复新增（旧 QUAL 失败、逐类少 1 即败、缺任一模块 gold 即败、A+B 合并凑数仍败、recovery ACTIVE→M4 拒、superseded generation 不可被 M4 消费、完整双套正向过）；写派生状态的测试串行/隔离副本跑，避免竞争。
- 派两份新独立审核（作废旧审核，绑新候选）：①Claude 侧独立对抗审核者；②全新隔离 Codex-GPT 复算签字者。二者**直接复算**逐套逐类量/gold 覆盖/旧 generation supersession/无泄漏/顺序/主会话零明文/checker 拒旧接新/M3 未跑 M0/candidate+manifest+evidence digest 绑定。任一有效问题→自动修复并对新候选重新双审，不问发起人普通整改。

### R6 —— 版本化重新关闭（顺序硬）
recovered candidate commit → 两审绑该 candidate → checker M3 FINAL 全绿（**含 qual_data_readiness 两套 PASS**）→ v2 closeout 工件（INPUT/OUTPUT/EVIDENCE_MANIFEST.v2、STAGE_DECISION.v2、CLOSEOUT_RECEIPT.v2、CLOSEOUT_REPORT.v2、HANDOFF.v2、MILESTONE_EXIT_EVIDENCE.v2、READY_SET_RESULT、新签字回执 ×2、更新 ORIGIN_ANCHOR.v2 锚提交第一父==新 closeout）→ 推锚+验远程含它 → 追加 M3_RECOVERY_CLOSE/CLOSED_PASS journal 终态 → **M3_RECOVERY_STATUS.state 改 CLOSED_PASS（重算 record_digest）** → terminal-state commit+push → 从分支头 closure 复算（远程头含新 anchor）→ `launcher.py --dry-run M4` 允许启动（recovery CLOSED_PASS 后 M4 interlock 放行）→ **M4 dry-run 通过后立即退出，不同会话续 M4**。

## 4. 硬纪律（全程）

- 成本非停工门；会话/额度耗尽=再落一次 INTERRUPTED_RESUMABLE 检查点续跑，**非 HONEST_STOP**。
- HONEST_STOP 仅限：机械证明合法材料容量不足 / 不可恢复数据泄漏或顺序破坏 / 确缺只能由用户提供的外部权限与事实。禁伪造 PASS。
- 密封红线：明文零入作者可读 Git；denylist 撞库=停；主会话零接触 QUAL 明文；`.env*`/密钥零读；真实客户数据零输入。
- Git：只显式路径 staging；断言门控提交（断言不过 add/commit 物理不执行）；只推现有 origin 任务分支；零 tag/force-push/rebase/merge-master/`git add -A`。
- M4 始终 fail-closed 直至 R3-R6 + 双审 + 新关闭链 + M4 dry-run 全过。

## 5. 最终提交格式（R6 完成后交发起人/Codex）

按 M3-R1 原 Prompt 第九节 `M3_RECOVERY_RESULT: PASS | HONEST_STOP` 全字段；其中 CANONICAL_CLOSEOUT_REPORT_PATH / CANONICAL_HANDOFF_PATH 指向 v2 工件；REMAINING_BLOCKERS 诚实列出。完成后停止，等 Codex 对 M3 重新复审，不自行启动 M4。
