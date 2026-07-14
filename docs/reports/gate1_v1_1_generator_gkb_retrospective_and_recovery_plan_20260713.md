# 笛语 Gate 1 生成器与 GKB 原子组件体系复盘及修复方案

## 0. 报告身份

| 字段 | 值 |
|---|---|
| 报告类型 | 体系级复盘、根因分析、修复路线与报审提案 |
| 报告日期 | 2026-07-13 |
| 审查场景 | `proposal_review` / `architecture_design` |
| 报告基线 | `master@f5e458730aca52e63748f597e007352b72d7bb63` |
| 当前失败证据 | PR #13，`head=d2a9225d4fafea6651a53d8f02a489629a81ef84` |
| 标准真源 | `C:\Users\Administrator\Documents\笛语agent\planning\笛语内容编排生成器与人审评价标准体系_v1.1.md` |
| 标准 SHA-256 | `022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542` |
| 写面 | 仅本报告；未修改生成器、GKB、KE、ORCH、账本、CI 或 readiness |

证据状态约定：

- **已实测**：由当前仓库、Git 历史、PR/API 或实际命令重算。
- **静态判断**：由代码、Schema、合同和产物结构审计得出。
- **待补证**：现有证据不足，必须通过后续执行 Prompt 或独立人审确定。

## 审查场景

- `primary_scene`: `proposal_review`
- `secondary_scene`: `architecture_consistency`
- `mapped_engineering_scenes`: `architecture_design`、`data_model_change`、`ci_cd_delivery`
- `inference_basis`: v1.1 标准真源、`master` 静态仓库、PR #13 失败证据、现有 120/60/86 资产重算

## 审查结论

- **当前系统**：`FAIL_GATE1_NOT_ESTABLISHED`，不可宣称生成器合格或受控生产就绪。
- **修复方案**：`PASS_FOR_GUARDIAN_AND_FOUNDER_REVIEW`，方向与 v1.1 第一门一致。
- **架构一致性**：当前实现保留了安全隔离和失败诚实性，但在计数、类型合同、组件证据、生成请求和人审闭环上发生结构漂移。

## 证据罗列

- **已实测**：标准 digest、master/PR SHA、Clean-120、路线候选、86 组件、全部旧关系和 PR #13 的失败证据均仍可重算。
- **基于静态仓库判断**：lexical validator 存在假阳性/假阴性；slot resolver 非类型安全；realization audit 构造性恒真；Profile 语义在 author request 中丢失。
- **待补证**：Clean-120 的真实 `N`、86 组件批准数 `M`、60 路线的人类黄金答案、当前核心的 v1.1 内容首次可接受率。
- **工作树状态**：报告分支仅新增本报告，业务资产和 readiness 未修改。

## 是否建议继续推进

- **建议**：停止沿当前开发门继续追加补丁，转入“六个工作包、八份实际执行指令”的 Gate 1 证据闭环。
- **前提**：Founder 批准路线；Guardian 先审每个 Execution Brief；独立人审角色真实就位。
- **不建议**：现在合并 PR #13、宣称 `N=120`、强制 86/86 组件晋升、解锁 runtime/production。

## 冲突 / 待裁决点

- 路线已收敛为六个工作包；第一包必须由 1A 建包与 1B 消费身份隔离、可追溯的审查记录并冻结 `N` 两份合同组成。
- v1.1 必须在 1A Phase 0 以字节快照、摘要和机器合同入库；外部 Windows 路径不再是执行时唯一真源。
- 86/86 必须有最终裁决，但批准数 `M` 可小于 86；全部旧关系仅作历史证据，未复核关系不得留在 active 使用面。
- PR #13 的处置仍须独立 Guardian 绑定；本报告不授权合并。

## 1. 总结论

### 1.1 当前系统裁决

```yaml
current_system_verdict:
  gate_1_generator_and_300_baseline: FAIL_NOT_ESTABLISHED
  generator_qualified: false
  v1_1_counted_positive_parent_count: N_PENDING_REVIEW
  route_60_machine_candidate_set: EXISTS_NOT_GOLD_FROZEN
  component_candidate_count: 86
  component_gold_test_coverage: NOT_ESTABLISHED
  production_entry_allowed: false
  runtime_readiness_transition_allowed: false
```

当前不是“再微调几句就能生产”的状态，也不是 LLM 已触及能力天花板。真正问题是：**评价对象、事实合同、组件证据、生成请求、人审组织和计数口径尚未形成同一条闭合证据链**。继续在现有 ORCH/Generator 开发门上逐轮补丁，会增加治理复杂度，却不会自动建立 v1.1 要求的 240 条正向父级内容、60 条路线案例和 86 个组件黄金测试基线。

### 1.2 修复提案裁决

```yaml
repair_proposal_verdict:
  verdict: PASS_FOR_GUARDIAN_AND_FOUNDER_REVIEW
  recommended_direction: RETURN_TO_GATE_1_AND_CLOSE_EVIDENCE_CHAIN
  execution_package_count: 6
  actual_execution_instruction_count: 8
  package_1_split_contracts: [P1A_BUILD_REVIEW_PACKETS, P1B_CONSUME_SIGNED_REVIEWS]
  scale_execution_prompt_count: 1
  assumptions:
    N: v1_1审定后冻结120中可计入正向240的真实数量, 0_to_120
    H: 新隐藏资格探针中可依法计入基线的正向条数, 0_to_20
  component_gold_case_count: DERIVED_AFTER_RETAINED_COMPONENT_AND_EDGE_REVIEW
  legacy_component_relationships: ALL_HISTORICAL_NON_ACTIVE_UNTIL_REVIEWED
  unreviewed_legacy_edges_active: false
  force_all_86_components_to_pass: false
```

推荐以 **六个工作包、八份实际执行指令** 收口。第一包分为 1A 和 1B，中间设置不可绕过的身份隔离审查 Checkpoint；本次 P1A 定向修复如实计为第八份指令。第五包只维护一份可恢复执行 Prompt，按真实缺口追加密封运行实例，不为每批新建合同、checker、schema 或账本项。

## 2. v1.1 对当前阶段的真实要求

v1.1 明确规定当前生效的是第一门“生成器与 300 条基线”，不是正式 ORCH/runtime 门：

- 20 个产品各至少 12 条正向父级内容，共 240 条。
- 20 个产品各至少 3 条非 ALLOW 路线案例，共 60 条。
- 组件不能替代父级内容数量。
- 冻结 120 只代表字节冻结，不代表自动计入 240；必须得到真实合格数 `N`。
- 密封批次首次可接受率总体至少 90%，每个 CP 达到 12 条时至少 11/12 首次可接受。
- 240 条最终正向内容必须全部批准；失败样本保留并继续计入首次通过率分母。
- 机器检查 100%，内容主审 100%，第二专家至少 48 条且每个 CP 至少 2 条。
- 两类人审不得同质：内容主审负责内容质量、用户价值和 20CP 归属，第二专家负责事实支持、授权边界和高风险复核；结论冲突必须保留并进入独立裁决。
- 两类正式审查可由人工或 AI 承担；AI 计入正式审查时，两个审查方必须使用不同身份、隔离实例或会话与独立运行记录，且不能是内容作者、P1A 建包方或 P1B 冻结方。两方在形成各自结论前不得读取对方结论。
- 生成器、规则、案例集、输出、检查器、人审批次均须有不可变清单与摘要。

因此，当前阶段不需要把正式 `CompositionPlan`、企业真实输入库、DIFY、RAG、云端部署或生产发布提前建完。当前应优先完成的是 **父级内容质量、路线行为、组件黄金测试、生成器资格和人审证据**。

## 3. 当前事实盘点

| 对象 | 已实测状态 | 正确解读 |
|---|---:|---|
| 冻结 Clean-120 | 120 条 | 历史只读参考集，不等于 v1.1 已批准 120 条 |
| Clean-120 的 v1.1 合格数 | `N_PENDING` | 需要 20CP 映射、去重、来源核验和 v1.1 人审后冻结 |
| 现有路线回归 | 60 条候选 | 已有机器候选集，但尚缺 v1.1 标准答案复核和黄金冻结 |
| 组件 Registry | 86 个候选 | 同时含继承候选和 Founder 设计候选，不等于 86 个黄金批准组件 |
| 历史组件 CP 适用关系 | 全部旧关系 | 仅作历史声明证据；未经独立复核的关系全部撤出 active，不得被生成器消费 |
| v1.1 组件评分字段 | 未建立 | 当前没有按 80+20、关键项最低线形成黄金评分记录 |
| 设计型组件父级证据 | 未建立 | 可作为设计假设进入测试，不可冒充内容派生组件 |
| PR #13 开发批次 | 失败证据已保留 | 质量人审未闭合，机器状态不能当作最终内容真值 |
| PR #13 人审 | 未完成 | `E_REVIEW_EXECUTION_TIMEOUTEXPIRED`，当前内容质量结论未闭合 |
| 生成器资格 | false | 与证据一致，应保持 false |
| 正式生产/发布/readiness | 全关 | 应继续保持全关 |

## 4. 已经做对、应当保留的能力

1. **失败诚实入账**：治理 CI 允许“诚实记录失败”通过，没有把内容失败洗成内容通过。
2. **隔离边界清晰**：synthetic、development、runtime、production、publishable 分账总体守住。
3. **无 reroll 挑绿**：PR #13 保留了派发身份与失败记录，没有用替换样本洗高通过率。
4. **职责边界已有基础**：GKB 不写事实，Generator 不应选组件，ORCH/规划层和表达层已经分离。
5. **路线候选集有价值**：60 条当前行为全部落在 BLOCK、REQUEST_INPUT、DEGRADE，且没有 audience/runtime 输出。
6. **20CP Profile 本身较丰富**：产品价值、角色、平台、风格、事实槽和硬门已有较完整定义。
7. **远程 CI 与分支保护有效**：检查器能防多类结构篡改，且当前失败证据仍保持 Draft、未合并。

这些成果应作为历史证据和回归资产保留，不应推倒重做。

## Findings

1. **[GOV]** (CRITICAL) 阶段顺序倒置，历史 120 被反复当成当前批准基线
   - 位置: v1.1 第 194-215 行；`PR#13@d2a9225:controlled_content_generator_v2_001/b_channel_claim_closure_dev_gate_authorized_transport_replay_001/result/development_gate_result.v0.1.json`
   - 问题描述: 标准要求先得到真实 `N`，PR #13 却继续记录 `accepted_baseline_count: 120`；现有 120 没有 v1.1 的 20CP 映射、70+30 评分、第二复审和批准链。
   - 建议操作: 历史文件保持只读，新增 `legacy_reference_count:120` 与 `gate1_v1_1_eligible_positive_parent_count:N_PENDING`；P1A 只建审查包，只有 P1B 可以消费合同之外、身份隔离且可追溯的审查记录并冻结 `N`。
   - 参考: v1.1 第 6.2、18.1、23 章；本报告 P1A、P1B。

2. **[EVIDENCE]** (CRITICAL) 事实闭合验证器同时存在假阳性和假阴性
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/fc_claim_closure_validator.py:184`
   - 问题描述: 验证器以全材料包词表代替逐引用蕴含；`undeclared_assertion_count`、`unsupported_fact_count` 和 `unclassified_atomic_clause_count` 实质为常量 0。忠实改写会被误杀，无来源的“样衣获得长期价值”篡改却可 machine pass。
   - 建议操作: 以 typed claim unit 重建 successor validator，逐原子断言绑定精确来源、授权和确定性；机器无法确定的语义进入 `HOLD_SEMANTIC`。
   - 参考: v1.1 第 7、8、13、21 章；本报告 P2。

3. **[LAYER]** (HIGH) 组件槽位绑定依赖字符串猜测和首项匹配
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/orch_component_planner_successor.py:85`
   - 问题描述: `_slot_class()` 以字段名子串猜类型，`_bind_component_slots()` 选择字典序第一条原子；授权类槽位没有稳定绑定到真实授权对象。
   - 建议操作: 分离 `FactAtom`、`AuthorizationGrant`、`EditorialAffordance`、`ClaimBoundary` 和 `ComponentFormOperator`，让槽位声明对象类型、基数和约束。
   - 参考: v1.1 第 7.3、7.5、9、23 章；本报告 P1B、P2。

4. **[EVIDENCE]** (HIGH) 组件 realization audit 是构造性恒真证明
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/run_component_consumption_dev_gate.py:706`
   - 问题描述: 脚本把候选全部非空 surface refs 原样挂给每一个组件，同一候选的所有组件因此拥有相同证据，`metadata_only_consumption_count` 按构造恒为 0。
   - 建议操作: 按组件记录真实 surface span、机制实现、toggle 对照和独立语义裁决；无可观察贡献时标为 `METADATA_ONLY` 或 `HOLD`。
   - 参考: v1.1 第 14、16、23 章；本报告 P1B、P2。

5. **[LAYER]** (HIGH) Profile 语义在进入作者请求前被投影丢失
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/generator_plan_consumer.py:53`
   - 问题描述: author request 缺少平台、时长、受众、业务目的和 Founder hard guard 文本，仅保留 Profile ID、规划轴、组件和 opaque guard IDs。
   - 建议操作: 建立第一门专用 `ParentContentGenerationRequest`，完整传递 CP 目的、角色、平台、受众、时长、风格、事实边界和 hard guard 语义；不得冒充正式 `CompositionPlan`。
   - 参考: v1.1 第 5.1、9、10、11 章；本报告 P2。

6. **[EVIDENCE]** (HIGH) 安全 fixture 被同时当成创意质量父材料
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/materials/development_material_packs.v0.1.jsonl:1`
   - 问题描述: 每个 CP 固定使用 CONTEXT/ROLE/ACTION/STATE/RECORD/SOUND/BOUNDARY 七类薄材料，适合验证安全合同，却不足以承载服装业务具体性、平台原生性和用户价值评分。
   - 建议操作: 强制分区 `RouteCase`、`PositiveParentCase`、`ComponentGoldCase`；组件和路线测试不得计入 240 条父级内容。
   - 参考: v1.1 第 5.1、6、10、15 章；本报告 P1A、P3、P5。

7. **[GOV]** (HIGH) 人审执行粒度过大且 Schema 未对齐 v1.1
   - 位置: `PR#13@d2a9225:controlled_content_generator_v2_001/b_channel_claim_closure_dev_gate_authorized_transport_replay_001/run_independent_content_reviews.py:79`
   - 问题描述: PRIMARY 与 FACT 审查任务过大，两个角色全完成后才持久化；审查已因超时未形成可用记录，人审 Schema 也缺 70+30、关键项最低线、等级、缺陷、第二复审和裁决。
   - 建议操作: 按 5 至 10 条分片，逐条 append-only 持久化并支持恢复；主审、第二专家和裁决使用 v1.1 完整 review record。
   - 参考: v1.1 第 10-13、19、20、22 章；本报告 P1A、P1B、P2、P3-P5。

8. **[GOV]** (MEDIUM) 检查器累积正在替代单一当前合同
   - 位置: `ci/checkers/`；`.github/workflows/ci.yml:1`
   - 问题描述: 历史 checker 多次硬编码账本终点并触发兼容修复；required CI 同时承担历史归档回归和当前快速门。PR #14 对本报告路径实测触发 `E_CURRENT_WRITE_SURFACE`，进一步证明 current-live 写面和历史快照边界尚未收口。
   - 建议操作: 建立一个版本化 Gate 1 manifest 和当前 live checker；历史 checker 转为归档完整回归，required fast path 不再嵌套重跑全部历史门；账本移动终点统一委托 Current Ledger Owner 从显式 horizon 派生。
   - 参考: v1.1 第 5.4、17、18.4 章；本报告 P1A、P6。

9. **[EVIDENCE]** (MEDIUM) 生成运行缺少模型/引擎配置身份
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/run_isolated_author_sessions.py:144`
   - 问题描述: runner 调用 `codex exec --ephemeral`，但未固定或记录 model/version/config，现有产物未满足 `model_or_engine_config_ref`。
   - 建议操作: 每次探针和扩量批次冻结 generator、prompt、model/engine config、randomization、input/output manifest；配置变化视为核心变化并重新资格验证。
   - 参考: v1.1 第 6.3、21、23 章；本报告 P2-P6。

## 6. 核心根因树

```text
R0: Gate 1 证据链未闭合
|
+-- R1 阶段顺序错误
|   +-- 先扩 ORCH/控制面，后补 240 正向父内容和 v1.1 人审
|   +-- 历史120数量被当成当前批准数
|
+-- R2 领域对象未类型化
|   +-- 事实、授权、边界、编辑动作、组件槽位混在字符串/ID中
|   +-- source ref 存在被误当成 source ref 蕴含
|
+-- R3 测试对象混装
|   +-- route fixture 被拿来评创意质量
|   +-- component test 被拿来替代 parent content
|
+-- R4 Profile 到 Author 的语义投影损失
|   +-- 平台、受众、时长、用户价值、硬门语义未送达作者
|
+-- R5 证据证明方式退化
|   +-- selection/reference 被当成 realization
|   +-- 常量0、全表面引用全集和词表匹配产生假绿/假红
|
+-- R6 人审架构未工程化
|   +-- 超大单任务、全有或全无落盘
|   +-- Schema 早于 v1.1，缺正式评分和复审链
|
+-- R7 治理资产不断叠加
    +-- 每任务新增永久 checker
    +-- required CI 兼任历史归档回归和当前快速门
```

### 6.1 是否超出当前 LLM 能力边界

**结论：没有证据支持这个判断。**

当前作者没有得到完整平台、受众、时长、产品价值和 hard guard 语义，却被要求产出可按这些维度评分的内容；事实验证器又同时误杀忠实改写、漏放无根据主张；材料还是偏安全测试的薄 fixture。在这个条件下，换任何 LLM 都无法形成可信基线。

反过来，更强的 LLM 也不能修复：计数口径错误、组件假 realization、字符串槽位绑定、人审记录缺字段、超时后 0 落盘。这是架构与知识工程问题，不是单纯模型问题。

## 7. 目标体系

### 7.1 七层目标架构

| 层 | 核心对象 | 所有者 | 当前 Gate 1 要求 |
|---|---|---|---|
| L1 标准与计数 | Standard Snapshot、Baseline Ledger、Run Manifest | Governance | 冻结 v1.1、分清 120/N/240/60/86/M |
| L2 证据合同 | FactAtom、AuthorizationGrant、ClaimBoundary、EditorialAffordance | GKB/Contract | 类型、来源、授权、时间和适用范围闭合 |
| L3 原子组件 | ComponentCandidate、ComponentGoldDecision、CP Edge | GKB | 组件只组织形式，不当事实源 |
| L4 第一门生成请求 | ParentContentGenerationRequest | Gate 1 Planner | 完整携带 CP、平台、受众、时长、风格、硬门；不冒充正式 Plan |
| L5 受控作者 | Claim Skeleton -> Creative Realization | Generator | 先闭合断言，再完成表达；不得自选事实和组件 |
| L6 校验 | Structure Validator、Semantic Claim Reviewer、Diversity Checker | Technical/Independent | 机器可判项确定性，语义未知进入 HOLD |
| L7 人审与冻结 | Primary Review、Second Review、Adjudication、Gold Manifest | Human reviewers/Founder | v1.1 全字段、append-only、失败保留 |

### 7.2 关键合同修复

```yaml
typed_claim_unit:
  claim_unit_id:
  surface_pointer:
  verbatim_text:
  claim_type: OBSERVATION|STATE|ACTION|NUMBER|ENTITY|CAUSALITY|OPINION|EDITORIAL
  source_supports:
  authorization_refs:
  certainty:
  forbidden_inference_refs:
  machine_status: PASS|FAIL|HOLD_SEMANTIC
  human_review_ref:
```

```yaml
component_realization_record:
  component_id:
  candidate_id:
  intended_mechanism:
  realized_surface_span_refs:
  boundary_checks:
  toggle_test_ref:
  semantic_reviewer_decision: REALIZED|METADATA_ONLY|MISAPPLIED|HOLD
```

### 7.3 不应在本轮继续建设的内容

- 正式 runtime `CompositionPlan`。
- 企业真实输入库。
- DIFY/RAG/Serving/KE 正式写入。
- 发布、生产流量、自动批准。
- 为未来 route 预留新的永久 checker。
- 为凑 86 个黄金组件而强制晋升。

## 8. 86 个原子组件黄金基线

### 8.1 正确口径

“86 个组件黄金基线”表示 86/86 均有来源身份、用途、边界、v1.1 评分和最终 disposition。每个候选得到 `RETAIN / REPAIR / MERGE / HOLD / REJECT / RECLASSIFY_CONTROL_RULE` 之一，最终保留数记为 `M`，允许 `M < 86`。

旧 Registry 声称的全部 CP 关系只保留为历史证据。新 active Registry 从空 active edge set 开始，只恢复经过独立审查、被最终保留组件真实需要的关系；任何未复核关系均标为 historical/non-active，生成器不得消费。

### 8.2 测试规模按保留结果派生

黄金测试规模在 1B 得到 `M` 和 active edge set 后派生：

```text
A = 独立复核后恢复的 active CP edge 数
R = 最终保留组件数 M
G = A 的正向实现案例 + 每个保留组件适用的关键负向边界案例
```

关键负向边界至少覆盖缺输入/授权、错 CP 或角色、禁配/hard guard、组件冒充事实源或伪造 realization。历史槽位与授权错绑诊断保留在机器证据中，不作为项目发起人的规划配额。

### 8.3 组件黄金通过线

- v1.1 公共组件质量 80 + 当前类型专属质量 20。
- 甲级最低：原子性至少 13/15、可组合性至少 17/20、适用/兼容/禁配至少 13/15、类型专属至少 17/20。
- 来源型组件有父级和证据区间；设计型机制诚实标为 design hypothesis。
- 每个 active edge 有 Profile 角色、输入类型、授权、hard guard 和实现证据。
- 只检查最终保留组件对 20CP 的最低真实供给；若有缺口则诚实停止，不得为覆盖强留组件。

## 9. 300 条内容测试集距离

```text
N = 冻结120中按 v1.1 最终可计入正向240的真实数量，0 <= N <= 120
H = 隐藏资格测试中可依法计入正向基线的批准数量，0 <= H <= 20
初始最低新增候选数 = 240 - N - H
```

`240-N-H` 只是初始最低生成量，不是保证达到 240 条批准内容的最终数量。任何未批准候选永久保留并继续计入首次可接受率分母；为补齐批准数量可以新增后续密封 top-up 案例，但不得用新样本替换旧失败。

第五包只使用一份参数化、可恢复的执行 Prompt，内部每批最多 40 条；真实运行次数由 `N`、`H`、最终批准率和逐 CP 缺口决定，不再换算成新的 Prompt 数。

## 10. 六个工作包与八份实际执行指令

### P1A `GATE1_V11_STANDARD_BASELINE_REVIEW_PACKET_AND_GOVERNANCE_PREFLIGHT_001`

**目标范围与意图**：完成第一包的确定性建包阶段。把 v1.1 标准字节快照、摘要和机器合同纳入仓库；只读盘点 120/60/86；建立 120 映射包、Route-60 盲审包、86 组件审查包和全部旧关系撤活计划。Phase 0 同时修复当前合法报告/后继路径被任务级全局写面误阻的问题。

**落盘交付**：仓库内 v1.1 标准快照与 schema；基线计数合同；120/60/86 review packets；一个统一空白审查记录模板；内容/用户价值主审与事实/授权第二专家的差异化 role charter；全部旧关系的 historical manifest；PR #13 失败证据绑定；current Gate 1 checker 的 reference-safe 兼容修复及 before/after digest。

**验收标准**：外部 v1.1 与仓库快照 digest 一致；120/60/86 数量和来源重算一致；不得产生 `N`、`M` 或领域批准决定；路线答案在签署独立结论前不得看到当前实现；合法报告和后继新增通过，历史资产任一字节篡改仍失败。

**强制规范**：compat 只修 current-live 路径并恢复 b24 live 完整性覆盖；移动账本终点委托 `check_current_ledger_owner.py` 的 horizon 模式，禁止再硬编码 terminal；不改业务资产和 readiness。

**双通道承接边界**：甲／乙是后续创作与资格测试的质量要求，不是两份审查职责。P1A 只保留“同一事实、来源、授权和主张边界下的独立创作”这一后续硬要求；P2 至 P6 必须继续承接，不声明双通道已经合格，不规定配对数量，也不改变 300、120、86。历史路径中的 `b_channel` 仅表示来源或任务命名，不能推断为乙通道成品或第二审身份。

### P1B `GATE1_V11_SIGNED_REVIEW_CLOSEOUT_AND_BASELINE_FREEZE_001`

**目标范围与意图**：第一包的人审收口阶段，只消费 P1A 合同之外产生、具备身份隔离与运行留痕的审查记录，冻结真实 `N`、Route-60 黄金答案、86 组件 disposition、保留数 `M` 和新的 active edge set。

**落盘交付**：120 主审与第二专家记录；`N` 冻结清单及 20CP 缺口矩阵；Route-60 gold registry；86 组件 review decisions；successor active component registry；保留关系和派生测试清单；组件供给缺口报告。

**验收标准**：120/120 内容/用户价值主审；事实/授权第二专家累计至少 48 条且每 CP 至少 2 条，并覆盖高风险/分歧；Route 60/60 由设计者之外的审核人确认，第二复核至少 12 条；86/86 有真实 readback；两类审查冲突均保留并完成独立裁决；`N/M` 只能从身份留痕审查记录重算；所有未复核旧边 non-active。

**强制规范**：执行代理不得补写审查结论；若任何 CP 缺最低组件供给，状态必须为 `STOPPED_COMPONENT_SUPPLY_GAP`，不得强留组件或进入 P2。

### P2 `GATE1_V11_GENERATOR_CORE_REPAIR_AND_REVIEW_HARNESS_001`

**目标范围与意图**：一次修复当前真正影响生成结果的核心问题，不建设通用语义推理平台。完整传递平台、账号、用户目的、内容要求和禁止事项；类型化区分事实、授权、角色、组件和表达规则；修复错绑、假阳性、假阴性、假 realization、人审超时和模型身份缺失。

**落盘交付**：typed evidence schemas；完整 `ParentContentGenerationRequest`；typed slot binder；claim validator successor；逐组件 realization record；唯一 active generator pointer；model/prompt/input/rule manifests；5-10 条分片、append-only、可恢复的人审台；统一 current Gate 1 checker。

**验收标准**：无来源“样衣获得长期价值”必须 FAIL/HOLD；忠实数字/动作改写不得误杀；授权槽不能绑定普通事实原子；计数从真实 surface units 重算、禁止常量 0；每个组件必须有独立实现 span；20CP 完整输入送达作者；人审中断后已完成记录不丢失。

**强制规范**：`external_provider_API_call_count` 从真实 adapter/process 出口审计派生，不得硬写 0；同一包可有核心与回归两个原子提交，但不设外部审批断点；不创建正式 CompositionPlan，不解锁 runtime。

### P3 `GATE1_V11_OPEN_PROBE40_001`

**目标范围与意图**：运行 20 条正向 + 20 条异常处置的开放开发测试，允许发现问题；如修改核心，必须重新冻结并重跑整个 P3。

**落盘交付**：冻结输入 manifest；40 个首次输出；事实/授权检查；内容主审、第二专家和分歧裁决；直接生成与组件辅助的小规模非阻断观察；开放门 result。

**验收标准**：正向首次可接受率至少 90%；路线 20/20 主动作和原因码正确；编造、越权、泄露 0；CP 盲测至少 85%；明显套路/近重复不超过 10%；失败样本和所有修复前结果保留。

**强制规范**：生成前锁定 generator/prompt/model-config/input/rule digest；开放结果不得冒充隐藏资格；通过后冻结核心。

### P4 `GATE1_V11_SEALED_HIDDEN_PROBE40_001`

**目标范围与意图**：由独立 curator 在核心冻结后创建全新 20 条正向 + 20 条异常输入，验证没有针对开放材料过拟合。

**落盘交付**：curator 隔离审计；隐藏输入 freeze manifest；40 个首次输出；独立审查记录；core/input/output digest；Founder 资格裁决包。

**验收标准**：core、prompt、model-config、rule digest 与 P3 冻结值一致；hidden 未进入代码或开放材料；正向首次可接受率至少 90%；路线 20/20；硬性错误 0；零换样、重抽、反馈回灌和分母重算。

**强制规范**：执行代理和机器不得自行判 generator qualified；只有身份隔离审查闭合后可提交 Founder 决定。通过且核心未变的正向内容可计入 `H`。

### P5 `GATE1_V11_POSITIVE_SCALE_TO_240_001`

**目标范围与意图**：使用一份可恢复执行 Prompt，按最多 40 条的密封批次补齐正向 240，不为每批新建合同、schema、checker 或账本。

**落盘交付**：每批 input/output manifest、全部首次候选、失败档案、主审/第二复审/裁决、批准清单、累计 CP 缺口和 top-up 记录；一个持续更新但 append-only 的 scale ledger。

**验收标准**：每批首次可接受率至少 90%；最终每 CP 12 条且至少 11/12 首次可接受；240 条最终全部批准；累计第二专家至少 48 条且每 CP 至少 2 条；硬否决 0；失败不替换、不删除并持续留在分母。

**强制规范**：若任何批次需要修改 generator/prompt/model/rule 核心，立即停止并退回 P3/P4；新增 top-up 必须是后续新密封案例，不得回填或洗掉旧失败。

### P6 `GATE1_V11_300_FINAL_INDEPENDENT_CLOSEOUT_001`

**目标范围与意图**：只做最终独立验收，不修生成器、不补数据。冻结 240 正向、60 路线、保留组件黄金基线和唯一生成器版本。

**落盘交付**：唯一 300 条总 manifest；positive-240、route-60、component-gold 和 failure manifests；内容/评价终审报告；技术/治理终审报告；Founder Gate 1 决策包。

**验收标准**：240+60=300；每 CP 12 正向+3 路线；300/300 有来源、版本、CP、检查和审核记录；密封首次可接受率总体至少 90%；每 CP 至少 11/12；盲测至少 85%；近重复不超过 10%；Route 60/60；硬否决、越权、泄露、自批 0；所有 active 组件与关系均有黄金证据。

**强制规范**：两份终审报告职责不同且结论闭合；当前 Gate 1 checker 独立从真实文件重算；只有 Founder 可关闭 Gate 1。通过只允许启动后续 16-28 包的规划，不自动授权执行，更不代表 CompositionPlan、企业数据库、DIFY 或云端完成。

## 11. 数量与依赖关系

```text
工作包数量：6
实际执行指令：8（第一包 = P1A + 本次 P1A 定向修复 + 身份隔离审查 Checkpoint + P1B）
第五包执行 Prompt：1
第五包内部运行实例：由真实缺口决定，必要时追加 top-up
```

```text
P1A -> 身份隔离审查 -> P1B -> P2 -> P3 -> P4 -> P5 -> P6
```

P1A 与 P1B 的分离是防自证边界，不得合并。P2 内部可以使用两个原子提交，但不另拆执行 Prompt。P3/P4 必须串行并保持隐藏隔离。P5 的批次是同一合同下的运行实例，不是新 Prompt。

## 12. 验收指标总表

| 维度 | 最终硬门 |
|---|---|
| 正向父级内容 | 240 条批准，20CP 各 12 条 |
| 路线 | 60/60 主动作和原因码正确，20CP 各 3 条 |
| 首次可接受率 | 密封批次总体 >=90%，每 CP >=11/12 |
| 人审 | 主审 100%；第二专家 >=48 条且每 CP >=2；分歧全裁决 |
| 事实/权限 | 编造、越权、跨租户、泄密、自行批准均为 0 |
| 多样性 | 明显套话/近重复 <=10%；CP 盲测达到标准线 |
| 组件候选 | 86/86 有 gold decision，不强制全批准 |
| 历史组件边 | 全部旧关系标 historical/non-active；未复核 active 边为 0 |
| 当前组件边 | 仅恢复被保留组件经独立审查通过的 `A` 条 active 边，逐边有身份留痕结论 |
| 组件测试 | 覆盖全部保留组件 `M` 和全部 active 边 `A`；案例数由通过边与风险负例派生 |
| 可复现 | generator/rule/schema/model/input/output/review 全有版本与 digest |
| 状态 | Gate 1 通过仍不等于正式 DB、CompositionPlan、runtime 或 production ready |

## 13. 决策选项

### 方案 A：回到 Gate 1 闭环，推荐

执行本报告 P1A-P6 六个工作包、八份实际执行指令。保留现有 ORCH/Generator 产物为开发与失败证据，停止继续为当前开发门叠加新 checker 和新 route。

**优点**：最符合 v1.1；先建立可相信的内容、组件和评价基线；后续正式 ORCH 有稳定输入。

**代价**：短期看似“后退一层”，需要身份隔离的审查资源；工程合同收敛为八份实际执行指令，P5 内部按最多 40 条一批连续运行。

### 方案 B：继续修 PR #13 当前链路，不推荐

继续补 lexical validator、Pair、transport 和 reviewer timeout，再跑 40 条。

**问题**：即使跑绿，也仍没有 `N`、240 正向、v1.1 review records、86 组件 gold decisions 和完整 Profile 投影，无法证明 Gate 1。

### 方案 C：立即引入外部 provider，不建议作为当前根因修复

当前没有证据证明瓶颈是模型能力。先修对象合同、材料和评价链，再用 P3/P4 判断是否需要模型升级。若换模型，必须作为新的 engine config 重新资格验证。

## 14. Founder / Guardian 需要裁决的事项

1. 是否确认 v1.1 为当前 Gate 1 唯一验收标准，并授权 P1A 将其字节快照、来源和 digest 入库为机器可查合同。
2. 是否确认 P1A 只建映射/审查包，P1B 只能消费合同之外、身份隔离且可追溯的审查记录来冻结 `N`，两份 Prompt 永不合并。
3. 是否同意把历史 120 改称 `legacy_reference_count`，在 P1B 前不再声称 `N=120`。
4. 是否同意“86 个黄金基线”定义为 86/86 有测试和裁决，而不是 86/86 必须批准；组件缺口不得靠强留组件补齐。
5. 是否同意全部旧关系撤出 active，仅恢复独立复核通过的 `A` 条关系，并按 `M`、`A` 和风险派生测试。
6. 是否批准六个工作包、八份实际执行指令，以及 P5 在同一合同内按最多 40 条一批连续运行。
7. 是否维持 PR #13 为未合并失败证据，直到有单独的失败归档/合并 Brief 再处理。
8. 是否承诺配置身份隔离的主审、第二专家和裁决角色；AI 审查可以计入正式审查但不得自评；Guardian 不替代 240 条全量内容主审。

## 15. 执行纪律

- 每个 Prompt 必须固定 baseline HEAD、允许写面、不可变输入和停止条件。
- 规则作者、案例 expected 设计者、内容作者和最终审查者不得由同一产物自证。
- 内容/用户价值主审与事实/授权第二专家使用不同职责和证据面；第二专家不是重复打分，冲突不得自动取交集、平均或由执行代理裁定。
- 机器 checker 只证明结构与明确可判不变量，不声称证明自由文本最终质量。
- 不因失败换样、删分母、回填事实、修改 source atoms 或降低 hard gate。
- 不把组件数量、组件引用数、checker 绿灯或 synthetic fixture 数量计入 240 正向父内容。
- 不在本路线中改变 KE/RAG/DIFY/Serving/runtime/production readiness。
- 正式审查结果必须身份隔离、版本化、append-only，并保留身份、输入、指令与实例/模型配置摘要；执行 Prompt 只做独立重算和冻结。

## 16. 证据索引

### 标准

- v1.1 第一门与 300 条：第 114-247 行。
- 正向内容 70+30 与 20CP 专项：内容评分章节。
- 组件 80+20 与最低线：组件评分章节。
- 路线 60 标准：第 698-727 行。
- 批次整体通过线：第 810-826 行。
- 人审角色与覆盖：第 859-890 行。
- run manifest：第 921-950 行。
- review record：第 954-1008 行。
- Gate 1 最终准入：第 1012-1040 行。

### 仓库与 PR

- 冻结 120：`07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/clean_120_reference_corpus_freeze_001/founder_reviewed_clean_120_reference_corpus.v1.0.jsonl`
- 86 组件 Registry：`07_microbatch_runs/scoped_content_microbatch_120_001/midbatch_320_001/controlled_composition_v2_001/b_channel_component_review_and_handoff_001/reviewed_reusable_component_registry.v0.4.jsonl`
- 60 路线实际：`controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/route/route_regression_actuals.v0.1.jsonl`
- lexical validator：`controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/fc_claim_closure_validator.py`
- slot planner：`controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/orch_component_planner_successor.py`
- request projection：`controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/generator_plan_consumer.py`
- realization audit：`controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/run_component_consumption_dev_gate.py`
- 当前失败证据：PR #13，commit `d2a9225d4fafea6651a53d8f02a489629a81ef84`。

## 17. 最终结构化裁决

```yaml
system_retrospective:
  verdict: FAIL_GATE1_NOT_ESTABLISHED
  primary_root_cause: EVIDENCE_CHAIN_AND_STAGE_ORDER_FAILURE
  llm_capability_ceiling_proven: false
  preserve_current_failure_evidence: true
  merge_pr13_now: false
  stop_further_runtime_orch_expansion: true

recovery_plan:
  verdict: PASS_FOR_REVIEW
  execution_packages: 6
  actual_execution_instructions: 8
  prompt_1_split_boundary: P1A_EXTERNAL_REVIEW_CHECKPOINT_P1B
  scale_prompt_contracts: 1
  positive_target: 240
  route_target: 60
  component_candidates_covered: 86
  legacy_component_relationships: ALL_HISTORICAL_NON_ACTIVE_UNTIL_REVIEWED
  unreviewed_legacy_edges_active: false
  active_component_edges: DERIVED_AFTER_SIGNED_REVIEW
  component_gold_cases: DERIVED_FROM_RETAINED_COMPONENTS_ACTIVE_EDGES_AND_RISK
  all_86_forced_to_pass: false

readiness:
  candidatepack_ready: false
  KE_ready: false
  RAG_ready: false
  DIFY_ready: false
  production_servable: false
  generation_eligible: false
  generation_allowed: false
  release_ready: false
  production_ready: false
```

本报告只授权讨论和审查，不授权执行 P1A-P6、生成新内容、修改 86 组件、合并 PR #13 或改变任何 readiness。后续须由 Founder 明确批准首个执行 Brief，再按 Guardian Pre-Review -> Codex 执行 -> Guardian Domain Review 的分权流程推进。
