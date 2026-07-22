# M3-R1 一次性收敛与连续交付 Prompt
# 基线 d147894｜一次解决全部已知 pilot 缺陷｜连续执行至 R6

你是 M3-R1 的唯一主执行者，主模型为 claude-opus-4-8。

本次任务不是再完成一个小阶段，而是一次性解决当前已知的全部问题，然后连续执行：

已知缺陷收敛
→ 完整 QUAL-A/B 真实 pilot
→ 正式 R3-run 全量建标
→ R4 readiness
→ R5 独立终审
→ R6 M3重关闭

R6 完成前，不得因为完成某个子阶段、任务预计耗时较长、需要付费调用、已经提交代码或形成检查点而主动退出。

不得运行 M0，不得启动 M4。

## 一、当前唯一基线

工作区：

/home/diyu/worktrees/gate1-longrun-001

分支：

agent/gate1-v1-1-successor-longrun

起点：

d1478944e359a75ab70d8d17265b1abe5e07dad8

当前已知状态：

- HEAD = upstream = d147894；
- M3_RECOVERY_STATUS=ACTIVE；
- journal VALID，共 56 条；
- 当前回归测试共 260 passed；
- M4 正确 fail-closed；
- R3-build 主干代码已经存在；
- 已发生真实 Codex Seat A、Opus Seat B 和隔离 Opus 仲裁调用；
- 仅完成 QUAL-A 技术 pilot；
- review/formulaic 仍使用确定性覆盖单元；
- 正式 QUAL-A/B gold 仍为 0；
- 正式 R3-run 尚未启动。

当前工作树并非完全干净，存在 pilot active pointer、generation manifest 和 index 未跟踪文件。

这不是发起人阻塞项。启动后自行检查这些文件：

- 如果只含 HIDDEN case_id、摘要、pointer、manifest 和 index，不含答案、密钥或明文，则作为 pilot 可复算证据显式提交；
- 如果包含不应进入 Git 的明文，则移入既有 sealed_custody_001 保全区并保持 gitignored；
- 不得丢弃无法复算的证据；
- 不得因此单独退出或提交一份状态报告。

启动只做上述最小检查，不重跑历史全套测试，不重新审议已完成架构。

追加本会话身份和 journal RESUME 后直接实现。

## 二、唯一 canonical Prompt

用本 Prompt 完整覆盖：

delivery_control_001/milestones/M3/recovery/RESUME_PROMPT.M3_R1.v3.md

不得创建：

- v4；
- 新的 resume Prompt；
- SESSION ADDENDUM；
- 第二份执行入口；
- 并列状态说明。

Git 历史已经保存旧版本，不需要通过多个文件保存历史。

## 三、当前 pilot 的准确结论

当前 `pilot_pass=true` 不得作为完整 pilot PASS 使用。

它只证明：

- 七模块富标签主链可以真实调用；
- 双席、仲裁、assemble、core、generation、custody 可以串起来；
- 六种 challenge kind 可以进入生产路径；
- 同源变体可以继承相同 source_group。

它没有证明：

- QUAL-B 对称路径；
- review 真实双模型标注；
- formulaic 真实双模型轴标注；
- 正确的逐模块一致性；
- expected cost manifest 与 rate card；
- known-R5 输入绑定；
- 实际 evidence-unit 容量；
- 远程可复算的完整 generation chain。

必须删除或修正任何把这些缺口归类成"只是规模不足"的逻辑。

## 四、一次性解决全部已知缺陷

以下项目必须在同一修复闭环完成，不再拆成新的阶段审核。

### 1. 将整-face一致改为逐模块、逐字段一致

当前 `_rich_key` 把十个字段捆绑成整张 face exact match，导致任一字段不同就整张仲裁。

改为现有 schema 内的字段→模块映射：

- risk：risk
- entailment：entailment
- reference：reference_present / reference_attributes
- atomization：atom_present / atom_partition
- fact_chain：safe_to_clear
- disclosure：disclosure_obligation / disclosure_violation
- omission：misleading

处理规则：

1. 对结构字段先做确定性规范化：对象 key 排序；无语义顺序的列表排序；atom partition 内部顺序规范化；保留真正影响原子分组的差异。
2. Seat A/B 某字段规范化后相同：直接采用一致值；该字段标记 CROSS_MODEL_AGREED。
3. 某字段不同：只把该字段及其必要上下文送仲裁；只采用该字段的仲裁结果；标记 FIELD_ADJUDICATED。
4. 只有实际消费了仲裁字段的模块记录才增加 ADJ provenance。
5. 不得因为 atom_partition 分歧，把 risk、entailment 等本来一致的模块全部标成仲裁。
6. 不建立新 schema、checker或第二套流水线。

新增最小测试：某 face 只有 atom_partition 不同→risk 记录保持 CROSS_MODEL_AGREED；某 face risk 不同→只有 risk 及真正依赖 risk 的记录使用仲裁值；结构顺序不同但语义相同不得触发仲裁；真正不同的 atom partition 必须触发 atomization 仲裁；未解决字段不得进入 goldfreeze。

### 2. 检查真实risk分歧

当前 11 条中 risk 有 6 条分歧，不能全部归因于结构格式。对这 6 条执行一次针对性分析：是标签解析差异 / 是风险等级定义不清 / 是材料证据不足 / 还是模型真实判断分歧。只允许一次最小校准：修正现有 labeler Prompt 中含糊的风险定义或输出约束；不新建第二套 rubric；不开展开放式研究；不重复无限调参。修正后用现有 pilot faces 进行针对性复核。

### 3. 建设真实review标注路径

删除 pilot 对 review 的确定性 `_coverage_units()` 占位。使用真实材料产生 review item，并由独立席位实际作出 decision / hard_veto / reviewer_id / reviewer provenance / evidence binding。必须真实形成：一个 item 对应两个独立 judgment；双席不互看；分歧时按既有仲裁路径裁决；计数仍按 distinct item 和 `(item_id, reviewer_id)` 计算。不得把主编排模型生成的固定 APPROVE/REJECT 写成真实 gold。

### 4. 建设真实formulaic标注路径

删除 pilot 对 formulaic 三元组的确定性占位。复用现有 formulaic rubric、necessary grammar registry 和 candidate miner，建立真实路径：真实内容 pair → Seat A/B 独立轴标注 → 逐轴一致性 → 必要字段仲裁 → final verdict → candidate audit → manifest/rubric/exception闭包。必须真实产生 FORMULAIC / NOT_FORMULAIC / NECESSARY_GRAMMAR 三类最小 pilot 样本。必须按 measurement_qualification.v2 既有门计算 raw agreement / positive agreement / negative agreement / kappa（可解释时）/ adjudication rate。不得发明新的全局 agreement 门槛。

### 5. 修正pilot PASS计算

`pilot_pass` 必须同时检查：QUAL-A 和 QUAL-B 均完成；九模块都是真实标注路径；六种 challenge kind 均覆盖；两席独立；分歧全部字段级解决；review/formulaic 不再是确定性占位；source/evidence 可复算；generation/index/custody 可复算；A/B/DEV 互斥；expected cost manifest 已登记；rate card 已绑定；known-R5 输入案例与合法变体已绑定；密封和泄漏检查通过；不存在其他非规模失败。只有正式样本数量和类别数量不足可以列为 pilot 的允许失败。以下不得再归入 scale/count failure：cost_expected_event_manifests；cost_rate_cards；known-R5 input binding；provenance；custody；source/evidence；agreement/adjudication；generation/index；module-role coverage。

### 6. 修正统计独立性与容量

禁止继续把每个 claim_id 自动当成独立 source_group。按真实证据聚类：source_group_id = 稳定的 scenario范围 + fact_ids/source_ids集合 + 证据跨度或等价证据单元摘要。规则：共享同一组事实/来源的多轮表达属于同一 cluster；同源 challenge 变体继承 base cluster；只有事实来源或证据单元真正不同，才允许不同 independent evidence unit；不得仅通过不同轮次、不同措辞、不同 claim_id 增加有效 N；同一 source_evidence_digest 跨多个 source_group 出现时必须聚并或拒绝；cross-module reuse 可在不同模块分母中使用，但不能在同一模块同一类别重复增加 N。从实际 QUAL-A/B split 直接枚举：distinct evidence unit / 每模块 / 每类别 / 每家族 / known-R5 / F5。当前 510 只保留为旧数量上界，不再作为最终 FEASIBLE 证据。如果真实容量不足：自动执行既有 Tier1 真源补量；优先补 B 侧、F5 和低供给类别；不询问发起人；只有穷尽现有真源仍不足才允许 HONEST_STOP。

### 7. 收口generation与远程复算

generation builder 必须：从真实 faces/gold 文件直接计算摘要；从真实 records 复算 records digest；与 qualification index 条目闭包；dataset_manifest_digest 缺失即 fail-closed；pointer、manifest、index、receipt 一致；安全公共索引证据在远程可复算；密封明文永远不进入 Git。当前 pilot 成本数字存在 receipt/progress 不一致时，以原始 registry 重算，统一写回唯一公开汇总；不得同时保留两个互相矛盾的成本数字。

## 五、重跑完整QUAL-A/B pilot

完成上述修复后不得退出，立即重跑完整 pilot。

### QUAL-A

复用已冻结 faces、Seat A/B 原始标签和已有仲裁输出。不得修改旧 pilot 冻结件；建立新的 superseding pilot generation。仅补充：新的逐字段合并；必要的风险定向复核；真实 review；真实 formulaic；cost/rate/known-R5；新 generation/index/custody/readiness。除非原始标签损坏，否则不重新支付已有七模块双标调用。

### QUAL-B

运行一个对称的真实小批：五家族覆盖；六种 challenge kind；Seat A/B 独立；字段级仲裁；九模块真实标注；generation/index/custody/readiness；与 A、DEV 完全互斥。

### 完整pilot通过条件

同时满足：A pilot PASS；B pilot PASS；九模块全为真实路径；non_scale_failures=[]；source/evidence独立性复算通过；formulaic既有agreement门通过；review真实双审通过；全部分歧解决；generation chain远程可复算；密封明文零入Git；readiness只因正式规模下限而NOT_READY。如果 pilot 失败：直接修复失败原因；复用已有未污染数据；只重跑受影响部分；继续执行；不输出最终报告；不退出会话。

## 六、pilot通过后立即进入正式R3-run

A/B pilot 全部通过后，不等待发起人或新的 Codex 审核。直接启动正式 R3-run。执行前只生成一份最小批次缺口表：当前有效独立 N；各模块/类别/家族合同下限；需要生成的剩余数量；每个真实源单元可合法服务的模块；预计模型调用批次。该表仅用于避免过量生成，不建立新治理框架。正式运行要求：QUAL-A/B 分别建新正式 generation；每批带 batch ID、set、模块、类别和证据范围；使用有界并行调用；Seat A/B独立；字段级仲裁；review/formulaic使用真实子管线；每批完成即运行记录级 schema/core/custody；每批更新实际有效 N 和剩余缺口；不在每批后运行全套测试；不在每批后停止；不在每批后提交最终式总结。完成一个批次、一个 set、一个模块或一次 push 都不是退出条件。调用失败：有限重试；只重跑失败批；不污染整套数据；generation 污染时标记 superseded 并新建 generation；不修改冻结 generation。持续执行直到两套全部达到 measurement_qualification.v2 下限。

## 七、自动执行R4→R6

### R4

用真实 custody 数据生成：A/B readiness；public counts；custody anchors；generation/index/gold/faces/dataset绑定；独立N；类别与家族覆盖；review/formulaic报告；双标与仲裁完整性；cost/rate；known-R5；A/B/DEV互斥；顺序和泄漏证明。A、B readiness 必须都为 PASS。失败则自动修复受影响数据或代码并重算，不询问发起人。

### R5

候选稳定后：运行一次 delivery_control 全套；运行一次 eval_audit_spine 全套；运行当前变化对应的负测；运行 checker M3 candidate 检查；全新 Opus 对抗审核；全新 Codex GPT 复算签字。只做两份正式审核。发现实质问题：自动修复；只重跑原失败项及受影响回归；只进行一次针对性复审。命名、格式、文档美化和未来增强不得阻塞。

### R6

完成：recovered candidate冻结；新v2 closeout；两份审核绑定同一candidate；checker M3 FINAL全绿；M3_RECOVERY_STATUS=CLOSED_PASS；完整closed_pass_binding；ORIGIN_ANCHOR新版本；本地/远程closure复算；工作树干净；快进推送；本地HEAD=远程HEAD；launcher --dry-run M4 输出 would_launch=true。随后立即退出，等待Codex复审。不得启动M4。

## 八、禁止过度工程化

禁止新增：第二套runner；第二套schema；第二套状态机；checker-of-checker；模型网关；批次审批系统；新委员会或角色；无直接消费者的receipt；每批一份审核报告；全历史重复扫描；为测试工具建设测试治理体系；与当前失败无关的架构重构。

验证纪律：实现阶段只跑目标测试；A/B pilot稳定后跑一次完整260基线回归；R3-run批次只跑记录级校验；R5候选稳定后跑一次最终完整回归；修复后只重跑原失败项和受影响范围；R6只做一次必要的最终泄漏扫描。

## 九、连续执行与停止条件

以下不是停止理由：工作量大；需要数千次调用；每批Claude调用需要数分钟；会话已经很长；完成一个自然阶段；担心留下半成品；已经形成干净提交；已经完成pilot；后续需要付费；主执行者主观认为下一会话更稳；上下文发生正常compact。发生compact时从磁盘状态继续，不输出最终报告。

### INTERRUPTED_RESUMABLE仅允许平台事实触发

必须提供可核验机器证据之一：Claude/Codex/API明确返回额度耗尽或服务不可用；所有已授权载体在有限重试后都不可用；执行环境强制终止工具；Git或磁盘故障在常规修复后仍无法安全保存；上下文压缩实际失败并由平台要求结束。不得以预计、担心、体量大或"责任边界"为依据写 INTERRUPTED_RESUMABLE。若真实平台中断：完成当前原子写入；更新同一个 v3 Prompt、progress和journal；提交并快进推送；输出具体错误、最后完成批次和唯一恢复动作；不创建新Prompt版本。

### HONEST_STOP仅允许

1. 穷尽现有真源和Tier1补量后，A/B独立容量仍机械不足；
2. 数据泄漏或顺序污染无法通过作废generation重建恢复；
3. 缺少只能由用户提供的外部事实、凭据或权限。

## 十、提交与报告

允许长任务中多次实质提交并推送，但每次推送后继续执行。禁止：git add -A；force-push；rebase；tag；merge master；修改其他工作区；密封明文、API key或客户数据进入Git。执行过程中只报告：当前阶段；A/B真实完成量；当前阻塞失败；调用数与成本；正在执行的下一动作。只有 R6 PASS、真实 HONEST_STOP 或带机器证据的平台强制中断，才允许输出最终报告（M3_RECOVERY_RESULT 模板：BASELINE_HEAD / FINAL_LOCAL_HEAD / FINAL_REMOTE_HEAD / R3_BUILD / PILOT_A / PILOT_B / REAL_REVIEW_PATH / REAL_FORMULAIC_PATH / FIELD_LEVEL_AGREEMENT / RISK_DISPUTE_RESULT / EFFECTIVE_INDEPENDENT_N_A / EFFECTIVE_INDEPENDENT_N_B / REAL_GOLD_A / REAL_GOLD_B / R3_RUN_BATCHES / READINESS_A / READINESS_B / MODEL_CALLS_AND_COST / TESTS / SEALED_LEAK_SCAN / OPUS_REVIEW / CODEX_REVIEW / CHECKER_M3_FINAL / M3_RECOVERY_STATUS / CLOSURE_VERIFY / M4_DRY_RUN / HARD_INTERRUPTION_EVIDENCE / CANONICAL_RESUME_PROMPT_PATH / REMAINING_BLOCKERS / NEXT_ACTION）。只有R6全部完成才能写 M3_RECOVERY_RESULT: PASS / NEXT_ACTION: WAIT_FOR_CODEX_M3_REVIEW，然后立即退出，绝不启动M4。

---
<!-- 磁盘续跑指针（本块为 canonical Prompt 的执行辅助，不改变上文合同）：
运维真值：席A(codex)/本地 commit/push 须沙箱外（dangerouslyDisableSandbox；沙箱内 gitdir/app-server 只读 FS）；git 读沙箱内可跑。席B(claude)/富标注/仲裁走 claude -p --model claude-opus-4-8；富标注分块（CHUNK=4）更稳。密封明文只落 sealed_custody_001/**（gitignore）；Git 仅代码/测试/config/回执聚合/sealed=HIDDEN index。
机读进度：M3_RECOVERY_PROGRESS.v3.json。骨架复用勿重建：qual_gold_derivation / qual_runner / qual_pilot / qual_core_fixtures / qual_generation / qual_custody_recompute / qual_capacity_precheck / pre_m0_readiness。
-->
