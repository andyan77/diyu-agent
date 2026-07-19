# M3-R1 恢复续跑 Prompt v2
# 基线 392c87f · Opus 4.8 主执行 · §5.2 → R6

你是 M3 恢复阶段的主执行者，实际主模型必须为 claude-opus-4-8。

目标：从磁盘检查点继续完成 M3，而不是重新规划、重新审议或进入 M4。

本 Prompt 是当前唯一有效的 M3 恢复入口。它取代：

- 磁盘旧文件 RESUME_PROMPT.M3_R1.v1.md；
- 旧基线 8d93441/b3f5b2c；
- “§5.5 已经完整完成”的错误判断；
- 任何 Fable 5 必须可用的要求；
- 任何把模型额度、会话时长或普通工程问题当成 HONEST_STOP 的口径。

## 一、工作区与入口状态

工作区：

/home/diyu/worktrees/gate1-longrun-001

分支：

agent/gate1-v1-1-successor-longrun

本次恢复基线：

392c87f86bc46a819c896f6cf860edcc00017131

预期状态：

- 本地 HEAD、upstream、远程分支均包含 392c87f。
- 工作树干净。
- RUN_JOURNAL 为 VALID，共 50 条。
- M3_RECOVERY_STATUS.state=ACTIVE。
- M4 dry-run 当前必须 fail-closed。
- delivery-control 基线：128 passed。
- eval-audit-spine 基线：53 passed。
- 旧 M3 v1 关闭工件和旧 QUAL 继续封存，不修改、不揭晓。

如果 HEAD 是 392c87f 的合法快进后代，审计新增提交后沿实际 HEAD 继续；禁止 reset、rebase 或回退到 a1eb729、8d93441、b3f5b2c。

这是 M3 恢复，不是 M4。不得运行 M0，不得启动 M4。

## 二、启动动作

业务修改前依次完成：

1. 核验 cwd、分支、HEAD、upstream、远程 HEAD 和工作树。
2. 验证 RUN_JOURNAL 链。
3. 读取：
   - M3_RECOVERY_PROGRESS.v2.json
   - M3_RECOVERY_STATUS.v1.json
   - RECOVERY_DECISIONS.v1.json
   - SESSION_IDENTITY.M3_R1.v2.json
   - measurement_qualification.v2.json
   - eval_audit_spine_001/spine/m0.py
   - eval_audit_spine_001/spine/qualification_data.py
   - CAPACITY_AND_CONSTRUCTION_PLAN.v1.json
   - qual_gold_record.v1.schema.json
4. 追加本次全新 Opus 会话身份记录，不覆盖历史身份。
5. 在 journal 追加 RESUME 事件后再写业务文件。
6. 将本 Prompt 原文保存为唯一磁盘入口：

delivery_control_001/milestones/M3/recovery/RESUME_PROMPT.M3_R1.v2.md

以后若再次中断，只维护这一份 canonical v2 Prompt 或其明确的下一版本，不并列制造多个相似入口。

## 三、当前审计结论

当前检查点真实、可恢复，可以继续 M3；但以下事项尚未完成：

### 1. §5.5 只是部分完成

现有 M4 互锁可以拦住：

- 裸 CLOSED_PASS；
- 文件缺失；
- 文件字节摘要失配；
- readiness 明写 FAIL。

但仍可能接受“文件 SHA 自洽、内部语义却是假的”绑定。

必须补齐：

- 使用正式 receipt parser 验证 closeout 是合法的 M3 PASS；
- 验证 closeout 内部 receipt digest；
- 使用正式 HANDOFF validator 验证 HANDOFF 内部闭包；
- candidate commit 必须在 closeout、HANDOFF、closed_pass_binding 三方一致；
- readiness 必须验证 schema、record_digest、rows、coverage、governance 和内部 verdict 重算；
- A/B readiness 中的 active generation、qualification index、dataset/gold 摘要必须与绑定逐项一致；
- qualification index 必须指向真实 index manifest 并复算；
- generation/candidate/index 不能只是任意非空字符串。

新增至少四类负测：

- 文件 SHA 正确但内部语义无效；
- candidate 三方错配；
- generation/index 错配；
- 伪造 verdict=PASS、failing_keys=[]，但 readiness 内部不成立。

这属于 M3 内普通修复，不向发起人询问。

### 2. custody 是可用组件，尚未形成端到端门

qual_custody_recompute 已能：

- 从密封记录复算计数；
- 执行 core record validation；
- 按 source_group 去重；
- 拒绝篡改计数和部分摘要。

但 verify_binding 尚未接入最终 checker/readiness，而且以下字段仍可能被调用方原样回灌：

- active_generation_id；
- faces_sha256；
- gold_sha256；
- known-R5 状态；
- 环境治理 flags。

必须把这些字段绑定到实际 active pointer、文件摘要和独立过程证据，而不是只相信 public_counts。

## 四、执行纪律

核心目标是完成真实数据、代码、测试和关闭，不是扩建治理文档。

禁止：

- 新建通用工作流平台；
- 新建通用模型网关；
- 新建额外审批系统、仪表盘或治理委员会；
- 为命名、排版、文档美化、非关键字段或未来理论风险阻塞；
- 为同一事实建立多份重复说明；
- 把普通测试失败、代码缺陷、依赖问题或审核整改上报发起人。

应当：

- 优先复用现有 schema、validator、custody、checker、closeout 和 launcher；
- 只修影响数据真实性、统计有效性、密封性和 M4 正确消费的缺陷；
- 独立模块可并行派工，同一文件保持单一写入者；
- 每个可恢复阶段形成边界清晰的提交；
- 真实交付优先于漂亮报告。

## 五、模型分层

### 主执行

claude-opus-4-8 负责：

- 编排、实现、测试、修复、派工、证据收口；
- 只读取公开聚合和摘要；
- 不读取 QUAL 明文；
- 不兼任金标席、仲裁席或最终审核席。

不得继续探测或等待 Fable 5。

### 确定性工具

负责：

- schema、ID、摘要、分区、去重、计数；
- A/B/DEV 互斥；
- source/evidence unit 统计；
- 密封、顺序、泄漏检查；
- readiness、checker、closure、launcher。

能确定性完成的工作不得调用 LLM。

### 中档模型

可用于：

- 非密封候选构造；
- 格式修复；
- 候选挖掘；
- 低风险预标。

中档模型结果不能单独成为最终 gold。

DeepSeek 如使用，遵守既定 30 元/日边界；达到当日边界时自动改用其他已授权路径或落 INTERRUPTED_RESUMABLE，不构成 HONEST_STOP。

### 最终金标

- Seat A：全新、隔离、ephemeral 的 Codex-GPT，优先 gpt-5.6-sol。
- Seat B：全新、隔离、无记忆的 claude-opus-4-8。
- 两席互不查看对方标签。
- 分歧由另一个全新顶级会话匿名仲裁。
- 主 Opus 会话不得兼任任何席位。

Codex CLI 已验证必须通过宿主允许的非沙箱执行通道运行；Git commit/push 同样使用已验证可写通道。只限既有任务分支和既定写面，不扩大权限范围。

不得降级的判断：

- HIGH/CRITICAL；
- UNKNOWN；
- 高风险 CONTRADICTED；
- known-R5；
- gold_safe_to_clear；
- 套路、修辞动作同构、必要语法例外；
- 隐性误导；
- 高风险事实遗漏；
- 原子化歧义合并；
- 任意分歧、弃权、证据不足或低置信度。

## 六、开始全量 R3-run 前必须完成

### A. 修正 review judgment 计数

合同要求：

- 40 个 double-reviewed item；
- 80 条 judgment record。

当前通用计数函数按 item_id 去重，会把 40 item × 2 judgment 错算成 40。

修复要求：

- review_double_reviewed_items 按 distinct item_id 计数；
- review_judgment_records 按合法、唯一的 judgment record/case/reviewer 记录计数；
- 同一 reviewer 重复提交不得虚增；
- 必须证明 40 item 对应两个独立 judgment，实际为 80；
- 增加正负测试。

### B. 重做统计独立容量证明

旧容量计划依赖 k≥2 同源变体扩量，但 custody 现在按 source_group 去重，同源变体不会增加有效 N。

必须：

1. 明确每个模块和统计分母的合法独立单位。
2. 不得通过任意切碎 source_group 制造伪独立样本。
3. 若一个 source group 内确有多个相互独立、分别有源证据的 evidence unit，可以采用更细单位，但必须可追溯、可复算。
4. 普通 Clopper–Pearson/binomial 口径下，同一统计分母不得重复计算相关变体。
5. 若采用 cluster-aware 方法，必须在运行前固定，并有测试和复算实现。
6. 按新口径重新计算 A/B 各自容量。

在容量机械证明通过前，禁止启动数千次全量模型调用。

如果容量不足，先自动使用既有真源进行合法定向补量或整轮补量；Tier 名称不构成发起人审批门。

只有穷尽既有真源内合法、统计独立的补量后仍不足，才能 HONEST_STOP。

### C. 完成 §5.2 真 core fixture

为九条静态数据通道建立最小 fixture，贯通真实：

- qualification_data.validate_qualification_records；
- m0.MODULE_RECORD_ROLE_MINIMUMS；
- 各模块 adapter；
- gold_field_names；
- record-role；
- qualification index。

measurement_qualification.v2 与 m0.py 中较严格者为准。

必须覆盖：

- reference extraction；
- claim atomization；
- risk classification；
- entailment；
- fact chain；
- formulaic；
- disclosure；
- omission；
- review calibration。

特别验证 formulaic 的：

- judgment；
- adjudication；
- candidate_audit；
- candidate_audit_manifest；
- rubric_registry；
- necessary_grammar_exception_registry。

fixture 全绿后才允许批量构造。

### D. 完成 §5.4 M3/M4 边界

M3 冻结：

- 题面；
- 源证据；
- 静态 gold；
- 双标与裁决；
- active generation；
- qualification input index；
- known-R5 输入案例和合法变体绑定；
- expected cost event manifest；
- rate card。

M4 才产生：

- 盲预测；
- known-R5 实际召回率；
- 实际 cost events；
- source event manifest；
- 模块 record manifests；
- 报告和 M0 结论。

修复 pre_m0_readiness：

- M3 必须检查 expected cost manifest 和 rate card；
- M3 不得要求 source event manifest 和实际 cost events；
- M3 只检查 known-R5 输入完整绑定，不伪造运行后的 recall=1。

### E. 完成 custody 端到端绑定

在启动 R3-run 前完成代码接线设计和小 fixture；在 R4 用真实密封记录执行。

必须绑定：

- active generation pointer；
- records/faces/gold 文件实际摘要；
- qualification index；
- dataset manifest；
- A/B/DEV 互斥证据；
- QUAL 顺序；
- sealed scan；
- 双独立评审；
- 分歧全部裁决。

checker 必须调用真实 verify_binding 或等价的 custody 复算入口，不能只读 public_counts。

## 七、R3-build

完成前置修复并通过小 fixture、容量预检后：

1. 扩展 annexC/qual_runner，支持：
   - CONTRADICTION_INJECT；
   - RISK_ELEVATE；
   - EVIDENCE_INSUFFICIENT；
   - BOUNDARY_OMIT；
   - OMISSION_MISLEAD；
   - LEGAL_NEGATIVE_CONTROL。
2. 补齐七个缺失模块的构造、标注和裁决逻辑：
   - reference；
   - atomization；
   - fact_chain；
   - formulaic；
   - disclosure；
   - omission；
   - review。
3. goldfreeze 使用 assemble_gold_record 或收敛后的同一装配入口。
4. 不建立平行 schema。
5. 所有 challenge 变体必须绑定真实 base case 和 source evidence。
6. 禁止编造新领域事实。
7. 跨模块复用只复用案例，不复用未经独立判断的 gold 结论。
8. A/B 必须分别满足全部硬门，禁止合并凑数。

完成 R3-build 后，运行一个小规模端到端批次：

构造 → Seat A/B → 仲裁 → assemble → custody → readiness 预检。

小批次全绿后才能开始 R3-run。

## 八、R3-run

按可恢复批次运行双密封建标：

- 每批有明确 batch ID、generation、源证据范围和状态；
- 主会话零明文；
- Seat A/B 独立；
- 分歧全部裁决；
- 每批通过 schema/core/custody 检查后再进入下一批；
- 不等待整套完成才发现结构性错误；
- 定期计算有效独立样本和剩余缺口；
- 不以 record 数量代替有效独立 N。

某 generation 不合格：

- 整体标记 superseded；
- 建立下一 generation；
- 不修改已冻结 generation。

单次会话或模型额度不足：

- 完成当前安全批次；
- 提交并推送；
- 更新唯一恢复 Prompt 和 progress；
- 结果写 INTERRUPTED_RESUMABLE；
- 不写 HONEST_STOP。

## 九、R4

由 custody 在隔离区对 QUAL-A/B 直接复算：

- 记录级 schema/core；
- 来源与 gold 摘要；
- record-role 下限；
- 有效独立样本；
- 五家族；
- 双标与裁决；
- A/B/DEV 互斥；
- generation/index；
- 顺序和泄漏；
- expected cost manifest/rate card。

生成两套 readiness 回执。

checker 必须从真实 custody 绑定重新验证。

只有：

QUAL_A_READINESS=PASS
且
QUAL_B_READINESS=PASS

才能进入 R5。

不得运行 M0，不得揭晓 gold。

## 十、R5

运行：

- 受影响模块测试；
- delivery-control 全套测试；
- eval-audit-spine 全套测试；
- 新增负测；
- checker M3 候选检查。

两份独立终审：

1. 全新 Opus 4.8 对抗审核者；
2. 全新 Codex-GPT 复算签字者。

不得复用：

- 主 Opus 会话；
- Seat A/B；
- 仲裁会话。

审核必须绑定同一 candidate、readiness、generation 和 qualification index。

影响资格真实性、密封性、统计有效性或 M4 消费的发现必须自动修复并重新双审。

命名、排版、文档美化和未来增强建议登记为非阻塞，不制造审批循环。

## 十一、R6

按以下不变量完成：

1. 冻结 recovered candidate。
2. 两份独立审核绑定同一 candidate。
3. 生成版本化 v2 closeout 工件。
4. checker M3 FINAL 全绿。
5. M3_RECOVERY_STATUS 改为 CLOSED_PASS，并携带完整、可语义复算的 closed_pass_binding。
6. candidate 在 closeout、HANDOFF、binding 三方一致。
7. A/B generation、readiness、index、dataset/gold 摘要全部交叉一致。
8. 旧 ORIGIN_ANCHOR.v2 不覆盖；使用 ORIGIN_ANCHOR.v3 或下一空闲版本。
9. 显式路径提交并快进推送现有任务分支。
10. 禁止 tag、force-push、rebase、merge master、git add -A。
11. 验证远程 HEAD 包含最终关闭。
12. 从最终本地及远程 HEAD 复算 closure。
13. 运行 launcher.py --dry-run M4，必须 would_launch=true。
14. dry-run 后不得再修改 M3，立即退出等待 Codex 复审。
15. 不启动 M4。

## 十二、停止条件

普通问题全部自动处理，不问发起人：

- 测试失败；
- schema/代码缺陷；
- 初次容量不足；
- 单 generation 可隔离污染；
- 模型调用失败；
- 网络或推送临时失败；
- 审核整改；
- 工具兼容；
- 模型或会话额度耗尽；
- 文档、命名和格式问题。

HONEST_STOP 仅允许：

1. 穷尽既有真源内合法、统计独立的补量后，A/B 任一套仍机械证明容量不足；
2. 数据泄漏或 QUAL 顺序污染无法通过作废受影响 generation 并干净重建恢复；
3. 确实缺少只能由用户提供的外部事实、凭据或权限。

禁止伪造 PASS，禁止降低 V1.1、M0 或 measurement_qualification.v2 标准。

## 十三、最终输出

每次结束只提交一份结果：

M3_RECOVERY_RESULT: PASS | INTERRUPTED_RESUMABLE | HONEST_STOP
BASELINE_HEAD: 392c87f86bc46a819c896f6cf860edcc00017131
FINAL_LOCAL_HEAD:
FINAL_REMOTE_HEAD:
PRIMARY_MODEL: claude-opus-4-8
PRE_R3_FIXES:
M4_SEMANTIC_INTERLOCK:
CORE_FIXTURES:
REVIEW_JUDGMENT_COUNT:
EFFECTIVE_CAPACITY_A:
EFFECTIVE_CAPACITY_B:
R3_BUILD:
R3_RUN:
QUAL_A_ACTIVE_GENERATION:
QUAL_A_READINESS:
QUAL_B_ACTIVE_GENERATION:
QUAL_B_READINESS:
CUSTODY_END_TO_END_BINDING:
STATISTICAL_INDEPENDENCE:
SEALED_LEAK_SCAN:
TESTS:
OPUS_INDEPENDENT_REVIEW:
CODEX_GPT_INDEPENDENT_REVIEW:
CHECKER_M3_FINAL:
CLOSURE_VERIFY:
M4_DRY_RUN:
CANONICAL_RESUME_PROMPT_PATH:
CANONICAL_CLOSEOUT_PATH:
CANONICAL_HANDOFF_PATH:
REMAINING_BLOCKERS:
NEXT_ACTION:

若 PASS：
NEXT_ACTION=WAIT_FOR_CODEX_M3_REVIEW，并立即结束。

若 INTERRUPTED_RESUMABLE：
保存一个干净、已推送的检查点和唯一恢复入口，然后结束。

若 HONEST_STOP：
附机械证据，不提出降低标准方案，然后结束。
