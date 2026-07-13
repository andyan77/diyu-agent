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

- **已实测**：标准 digest、master/PR SHA、Clean-120 数量、60 路线分布、86 组件、543 条 CP 边、PR #13 的 25/40 machine pass 与 0/40 人审完成。
- **基于静态仓库判断**：lexical validator 存在假阳性/假阴性；slot resolver 非类型安全；realization audit 构造性恒真；Profile 语义在 author request 中丢失。
- **待补证**：Clean-120 的真实 `N`、86 组件批准数 `M`、60 路线的人类黄金答案、当前核心的 v1.1 内容首次可接受率。
- **工作树状态**：报告分支仅新增本报告，业务资产和 readiness 未修改。

## 是否建议继续推进

- **建议**：停止沿当前开发门继续追加补丁，转入 E01-E12 和 S01-Sx 的 Gate 1 证据闭环。
- **前提**：Founder 批准路线；Guardian 先审每个 Execution Brief；独立人审角色真实就位。
- **不建议**：现在合并 PR #13、宣称 `N=120`、强制 86/86 组件晋升、解锁 runtime/production。

## 冲突 / 待裁决点

- 是否将 v1.1 确认为当前唯一 Gate 1 验收真源。
- 是否接受“86/86 有黄金裁决，但批准数 `M` 可小于 86”的口径。
- 是否批准最低 887 个组件 primary gold cases 和 15 至 18 个执行 Prompt 的路线。
- PR #13 是否继续保持 Draft 失败证据，等待独立归档/合并 Brief。

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
  fixed_execution_prompt_count: 12
  variable_positive_scale_prompt_count: ceil((240 - N - H) / 40)
  conservative_total_prompt_range: 15_to_18
  assumptions:
    N: v1_1审定后冻结120中可计入正向240的真实数量, 0_to_120
    H: 新隐藏资格探针中可依法计入基线的正向条数, 0_to_20
  component_gold_minimum_primary_case_count: 887
  force_all_86_components_to_pass: false
```

推荐以 **12 个固定执行 Prompt + 3 至 6 个正向扩量 Prompt** 收口。保守总量为 **15 至 18 个执行 Prompt**。人审本身是独立职责，不算执行 Prompt；后续 Prompt 只消费已签署的人审结果并做确定性收口。

## 2. v1.1 对当前阶段的真实要求

v1.1 明确规定当前生效的是第一门“生成器与 300 条基线”，不是正式 ORCH/runtime 门：

- 20 个产品各至少 12 条正向父级内容，共 240 条。
- 20 个产品各至少 3 条非 ALLOW 路线案例，共 60 条。
- 组件不能替代父级内容数量。
- 冻结 120 只代表字节冻结，不代表自动计入 240；必须得到真实合格数 `N`。
- 密封批次首次可接受率总体至少 90%，每个 CP 达到 12 条时至少 11/12 首次可接受。
- 240 条最终正向内容必须全部批准；失败样本保留并继续计入首次通过率分母。
- 机器检查 100%，内容主审 100%，第二专家至少 48 条且每个 CP 至少 2 条。
- 生成器、规则、案例集、输出、检查器、人审批次均须有不可变清单与摘要。

因此，当前阶段不需要把正式 `CompositionPlan`、企业真实输入库、DIFY、RAG、云端部署或生产发布提前建完。当前应优先完成的是 **父级内容质量、路线行为、组件黄金测试、生成器资格和人审证据**。

## 3. 当前事实盘点

| 对象 | 已实测状态 | 正确解读 |
|---|---:|---|
| 冻结 Clean-120 | 120 条 | 历史只读参考集，不等于 v1.1 已批准 120 条 |
| Clean-120 的 v1.1 合格数 | `N_PENDING` | 需要 20CP 映射、去重、来源核验和 v1.1 人审后冻结 |
| 现有路线回归 | 60 条：BLOCK 27 / DEGRADE 20 / REQUEST_INPUT 13 | 已有很好的机器候选集，但尚缺 v1.1 标准答案复核和黄金冻结 |
| 组件 Registry | 86 个候选 | 64 个继承候选 + 22 个 Founder 设计候选，不等于 86 个黄金批准组件 |
| 组件 CP 适用边 | 543 条 | 平均每组件 6.31 条，必须逐边验证，不能只验组件 ID 存在 |
| v1.1 组件评分字段 | 0/86 | 当前没有按 80+20、关键项最低线形成黄金评分记录 |
| 新增 22 组件父级证据 | 22/22 无父资产和源文本区间 | 可作为设计假设进入测试，不可冒充内容派生组件 |
| PR #13 开发批次 | 40 条，25 machine pass / 15 machine fail | 质量人审因超时未完成，不能把 25/40 或 15/40当最终内容真值 |
| PR #13 人审 | 0/40 完成 | `E_REVIEW_EXECUTION_TIMEOUTEXPIRED`，当前内容质量结论未闭合 |
| 生成器资格 | false | 与证据一致，应保持 false |
| 正式生产/发布/readiness | 全关 | 应继续保持全关 |

## 4. 已经做对、应当保留的能力

1. **失败诚实入账**：治理 CI 允许“诚实记录失败”通过，没有把内容失败洗成内容通过。
2. **隔离边界清晰**：synthetic、development、runtime、production、publishable 分账总体守住。
3. **无 reroll 挑绿**：PR #13 记录了 80 次物理派发、40 个评价对象、0 reroll、0 replacement。
4. **职责边界已有基础**：GKB 不写事实，Generator 不应选组件，ORCH/规划层和表达层已经分离。
5. **路线候选集有价值**：60 条当前行为全部落在 BLOCK、REQUEST_INPUT、DEGRADE，且没有 audience/runtime 输出。
6. **20CP Profile 本身较丰富**：产品价值、角色、平台、风格、事实槽和硬门已有较完整定义。
7. **远程 CI 与分支保护有效**：检查器能防多类结构篡改，且当前失败证据仍保持 Draft、未合并。

这些成果应作为历史证据和回归资产保留，不应推倒重做。

## Findings

1. **[GOV]** (CRITICAL) 阶段顺序倒置，历史 120 被反复当成当前批准基线
   - 位置: v1.1 第 194-215 行；`PR#13@d2a9225:controlled_content_generator_v2_001/b_channel_claim_closure_dev_gate_authorized_transport_replay_001/result/development_gate_result.v0.1.json`
   - 问题描述: 标准要求先得到真实 `N`，PR #13 却继续记录 `accepted_baseline_count: 120`；现有 120 没有 v1.1 的 20CP 映射、70+30 评分、第二复审和批准链。
   - 建议操作: 历史文件保持只读，新增 `legacy_reference_count:120` 与 `gate1_v1_1_eligible_positive_parent_count:N_PENDING`；仅在 E03 消费签署人审后冻结 `N`。
   - 参考: v1.1 第 6.2、18.1、23 章；本报告 E01-E03。

2. **[EVIDENCE]** (CRITICAL) 事实闭合验证器同时存在假阳性和假阴性
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/fc_claim_closure_validator.py:184`
   - 问题描述: 验证器以全材料包词表代替逐引用蕴含；`undeclared_assertion_count`、`unsupported_fact_count` 和 `unclassified_atomic_clause_count` 实质为常量 0。忠实改写会被误杀，无来源的“样衣获得长期价值”篡改却可 machine pass。
   - 建议操作: 以 typed claim unit 重建 successor validator，逐原子断言绑定精确来源、授权和确定性；机器无法确定的语义进入 `HOLD_SEMANTIC`。
   - 参考: v1.1 第 7、8、13、21 章；本报告 E08。

3. **[LAYER]** (HIGH) 组件槽位绑定依赖字符串猜测和首项匹配
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/orch_component_planner_successor.py:85`
   - 问题描述: `_slot_class()` 以字段名子串猜类型，`_bind_component_slots()` 选择字典序第一条原子；当前 654 个槽位中有 68 个 authorization-like 槽位未绑定真实授权对象。
   - 建议操作: 分离 `FactAtom`、`AuthorizationGrant`、`EditorialAffordance`、`ClaimBoundary` 和 `ComponentFormOperator`，让槽位声明对象类型、基数和约束。
   - 参考: v1.1 第 7.3、7.5、9、23 章；本报告 E05、E08、E09。

4. **[EVIDENCE]** (HIGH) 组件 realization audit 是构造性恒真证明
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/run_component_consumption_dev_gate.py:706`
   - 问题描述: 脚本把候选全部非空 surface refs 原样挂给每一个组件，40/40 候选中同一候选的所有组件因此拥有相同证据，`metadata_only_consumption_count` 按构造恒为 0。
   - 建议操作: 按组件记录真实 surface span、机制实现、toggle 对照和独立语义裁决；无可观察贡献时标为 `METADATA_ONLY` 或 `HOLD`。
   - 参考: v1.1 第 14、16、23 章；本报告 E06、E07。

5. **[LAYER]** (HIGH) Profile 语义在进入作者请求前被投影丢失
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/core/generator_plan_consumer.py:53`
   - 问题描述: author request 缺少平台、时长、受众、业务目的和 Founder hard guard 文本，仅保留 Profile ID、规划轴、组件和 opaque guard IDs。
   - 建议操作: 建立第一门专用 `ParentContentGenerationRequest`，完整传递 CP 目的、角色、平台、受众、时长、风格、事实边界和 hard guard 语义；不得冒充正式 `CompositionPlan`。
   - 参考: v1.1 第 5.1、9、10、11 章；本报告 E09。

6. **[EVIDENCE]** (HIGH) 安全 fixture 被同时当成创意质量父材料
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/materials/development_material_packs.v0.1.jsonl:1`
   - 问题描述: 每个 CP 固定使用 CONTEXT/ROLE/ACTION/STATE/RECORD/SOUND/BOUNDARY 七类薄材料，适合验证安全合同，却不足以承载服装业务具体性、平台原生性和用户价值评分。
   - 建议操作: 强制分区 `RouteCase`、`PositiveParentCase`、`ComponentGoldCase`；组件和路线测试不得计入 240 条父级内容。
   - 参考: v1.1 第 5.1、6、10、15 章；本报告 E02、E04、E06。

7. **[GOV]** (HIGH) 人审执行粒度过大且 Schema 未对齐 v1.1
   - 位置: `PR#13@d2a9225:controlled_content_generator_v2_001/b_channel_claim_closure_dev_gate_authorized_transport_replay_001/run_independent_content_reviews.py:79`
   - 问题描述: PRIMARY 一次审 40 候选加 20 Pair，FACT 一次审 40 候选，两个角色全完成后才持久化；当前已因 1800 秒超时得到 0/40，人审 Schema 也缺 70+30、关键项最低线、等级、缺陷、第二复审和裁决。
   - 建议操作: 按 5 至 10 条分片，逐条 append-only 持久化并支持恢复；主审、第二专家和裁决使用 v1.1 完整 review record。
   - 参考: v1.1 第 10-13、19、20、22 章；本报告 E03、E07、E09。

8. **[GOV]** (MEDIUM) 检查器累积正在替代单一当前合同
   - 位置: `ci/checkers/`；`.github/workflows/ci.yml:1`
   - 问题描述: 当前约 57 个 Python checker、约 4.6 万行，required CI 直接调用与 `python -O` 循环合计约 82 次；历史 checker 多次硬编码账本终点并触发兼容修复。
   - 建议操作: 建立一个版本化 Gate 1 manifest 和当前 live checker；历史 checker 转为归档完整回归，required fast path 不再嵌套重跑全部历史门。
   - 参考: v1.1 第 5.4、17、18.4 章；本报告 E01、E12。

9. **[EVIDENCE]** (MEDIUM) 生成运行缺少模型/引擎配置身份
   - 位置: `controlled_content_generator_v2_001/b_channel_component_consumption_and_claim_closure_dev_gate_001/run_isolated_author_sessions.py:144`
   - 问题描述: runner 调用 `codex exec --ephemeral`，但未固定或记录 model/version/config，现有产物未满足 `model_or_engine_config_ref`。
   - 建议操作: 每次探针和扩量批次冻结 generator、prompt、model/engine config、randomization、input/output manifest；配置变化视为核心变化并重新资格验证。
   - 参考: v1.1 第 6.3、21、23 章；本报告 E09-E12。

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

## 8. 86 个原子组件黄金测试基线

### 8.1 正确口径

“86 个组件黄金基线”应表示：

1. 86/86 均有来源类型、父级/设计来源、用途、边界和 v1.1 评分记录。
2. 543/543 条当前声称的 CP 适用边均有独立测试与裁决。
3. 每个组件至少覆盖 4 个负向测试族。
4. 每个组件得到 `APPROVE / HOLD / REPAIR / REJECT / RECLASSIFY_CONTROL_RULE` 之一。
5. 最终批准数记为 `M`，允许 `M < 86`，不设晋升率目标。

它**不表示** 86 个全部必须批准，也不表示 22 个 Founder 设计组件必须伪造父内容来源。

### 8.2 最低黄金案例规模

```text
当前声称的 CP 适用边正向案例 = 543
每组件最低负向案例族         = 4 × 86 = 344
最低 primary gold cases      = 543 + 344 = 887
```

四个负向测试族：

1. 缺 required input/fact/authorization slot。
2. 错 CP、错角色或未声明适用边。
3. forbidden combination、hard guard 或不允许 event-truth mode。
4. 把组件当事实源、伪造 realization、超出引用支持范围。

顺序置换、字段篡改和 schema mutation 作为同一 gold case 的 mutation battery，不靠增加“案例数”夸大覆盖。

### 8.3 组件黄金通过线

- v1.1 公共组件质量 80 + 当前类型专属质量 20。
- 甲级最低：原子性至少 13/15、可组合性至少 17/20、适用/兼容/禁配至少 13/15、类型专属至少 17/20。
- 致命/重大缺陷为 0。
- 来源型组件必须有父级和证据区间。
- 设计型机制必须诚实标为 design hypothesis，不冒充从 Clean-120 提取。
- CP edge 只有在 Profile 角色、输入类型、授权、hard guard 和输出机制都成立时才能 PASS。

## 9. 300 条内容测试集距离

### 9.1 真实公式

```text
N = 冻结120中按 v1.1 最终可计入正向240的真实数量，0 <= N <= 120
H = 新隐藏资格探针中可依法计入正向基线的数量，0 <= H <= 20

待补正向数量 = 240 - N - H
正向扩量 Prompt 数 = ceil((240 - N - H) / 40)
路线案例数量 = 60，当前已有机器候选集，仍需黄金复核
```

在 `N` 和 `H` 尚未冻结前，任何单一“还差 X 条”的说法都是假精确。

### 9.2 保守场景

| 场景 | N | H | 待补正向 | 40 条扩量 Prompt | 总执行 Prompt |
|---|---:|---:|---:|---:|---:|
| 最优保守 | 120 | 20 | 100 | 3 | 15 |
| 中位示例 | 80 | 20 | 140 | 4 | 16 |
| 较低合格 | 40 | 20 | 180 | 5 | 17 |
| 最坏保守 | 0 | 0 | 240 | 6 | 18 |

扩量批次不预先平均分配。每批根据 E03 冻结的逐 CP 缺口补齐，并保持密封输入、固定 core、失败不换样。

## 10. 推荐执行 Prompt 路线图

### E01 `GATE1_V11_STANDARD_SNAPSHOT_AND_ACCOUNTING_LOCK_001`

**目标**：把 v1.1 的 digest、对象类型、计数公式和 Gate 1 边界落成机器可查的当前合同；分开历史 120、真实 `N`、路线 60、组件候选 86 和批准组件 `M`。

**验证**：

- 标准 digest 精确吻合。
- 历史业务资产字节不变。
- 禁止 `legacy_reference_count` 自动赋给 `N`。
- readiness、runtime、KE、RAG、DIFY 均不变。
- 新合同 checker 具有正反 selftest，不新增第二套同义合同。

### E02 `CLEAN120_V11_20CP_MAPPING_AND_REVIEW_PACKET_001`

**目标**：只读映射 120/120 到主要 CP，重算 provenance、parent、dedup、适用性和机器硬门，生成盲化人审包。

**验证**：

- 120/120 均有主要 CP 或明确 NOT_APPLICABLE 决定。
- 近重复簇完整，不删失败条目。
- 不由脚本自动批准，不写 `N`。
- review packet 覆盖 v1.1 70+30、关键项最低线和否决项。

### E03 `CLEAN120_V11_HUMAN_REVIEW_CLOSEOUT_AND_N_FREEZE_001`

**目标**：消费独立主审、第二专家和必要裁决结果，冻结真实 `N` 及 20CP 正向缺口。

**验证**：

- 120/120 有主审记录。
- 第二专家覆盖满足规则并至少每 CP 2 条，若某 CP 样本不足则全审并如实记录。
- 分歧和跨等级案例完成裁决。
- `N` 从签署记录独立重算，不能由常量或目标反推。
- 历史 120 原文不改，失败记录保留。

### E04 `GATE1_ROUTE60_GOLD_REBASELINE_001`

**目标**：把现有 60 条机器候选路线案例升级为 v1.1 黄金路线集；补设计者、独立复核者、标准原因码和隐藏标志。

**验证**：

- 60/60 唯一主动作和主原因码正确。
- BLOCK、REQUEST_INPUT、DEGRADE 三类均有真实覆盖，不机械追求均分。
- 高风险漏放 0，合法正向误阻率不超过 5%。
- expected 不由 route implementation 反算。
- 路线第二复核至少 12 条，所有高风险/分歧全复核。

### E05 `GKB_COMPONENT86_PROVENANCE_TYPE_AND_EDGE_RECLASS_001`

**目标**：对 86 个候选逐个重分类，区分内容派生组件、设计机制、Generator 控制规则、Planner/ORCH 操作符和不合格候选；建立 543 条 claimed edge 审计清单。

**验证**：

- 86/86 有逐条 readback 和真实裁决，不按 ID/顺序分桶。
- 22 个无 parent 的设计候选保持诚实身份。
- FC 规则不伪装成 GKB 内容组件。
- 543/543 claimed edges 均进入待测清单。
- 不设 86/86 晋升目标。

### E06 `GKB_COMPONENT86_GOLD_CASESET_887_BUILD_001`

**目标**：为 86 个候选建立至少 887 个 primary gold cases 和 mutation battery，冻结输入、预期来源和 reviewer packet。

**验证**：

- 543 条 claimed edge 各有独立案例。
- 每组件 4 类负例齐全。
- 实现代码不能作为 expected oracle。
- 输入乱序不改变 gold identity 和物化结果。
- 篡改 CP edge、source、authorization、realization 均 fail-closed。
- 案例不生成 audience 正文，不计入 240。

### E07 `GKB_COMPONENT86_GOLD_REVIEW_AND_BASELINE_FREEZE_001`

**目标**：完成 86 候选及 543 边的人审评分、裁决和黄金期望冻结，得到真实批准数 `M`。

**验证**：

- 86/86 有 80+20 评分、最低线、缺陷、decision 和 reviewer。
- 543/543 edge 有 PASS/HOLD/REJECT 结论。
- 887+ cases 的 gold expected 来自独立审查，不来自 materializer。
- 批准组件逐项满足 provenance、atomicity、composability 和 boundary。
- `M` 独立重算，允许小于 86。

### E08 `GATE1_TYPED_FACT_AUTHORIZATION_AND_CLAIM_VALIDATOR_V2_001`

**目标**：建立 typed evidence contract 和 successor validator，替代全包词表与存在性引用判断。

**验证**：

- 无来源“样衣获得长期价值”必须 FAIL/HOLD，不得 PASS。
- 有来源“两种”到“第二种”等忠实改写不得因字符变化误杀。
- 镜头指令“拍摄”不被误判成事件事实。
- `unsupported_fact_count`、`undeclared_assertion_count`、`unclassified` 均从真实单元重算，禁止常量 0。
- 每个 source ref 验证支持范围，授权对象和事实对象类型分离。
- 旧 PR 证据只读保留，不重写历史结果。

### E09 `GATE1_PARENT_GENERATOR_AND_REVIEW_HARNESS_V11_001`

**目标**：建立唯一 active Gate 1 generator successor、完整 `ParentContentGenerationRequest` 和可恢复的人审台。

**验证**：

- author request 携带 CP 目的、角色、平台、时长、受众、风格、hard guard 文本、typed facts 和 output contract。
- 先生成 claim skeleton，再生成 creative realization。
- model/engine config、prompt、randomization 和 manifests 均冻结。
- 人审按 5 至 10 条分片、逐条 append-only、可恢复；Schema 完整覆盖 v1.1。
- 一次只有一个 active generator entrypoint。
- 不创建正式 CompositionPlan，不解锁 runtime。

### E10 `GATE1_OPEN_DEV_PROBE40_V11_001`

**目标**：使用 20 条正向 + 20 条路线的开放开发探针校准新核心，验证基础资格，不计最终隐藏成绩。

**验证**：

- 正向机器/语义否决为 0。
- 路线 20/20 主动作和原因码正确。
- 正向首次可接受率至少 90%。
- CP 盲测总体至少 85%，公式化和近重复不超过标准线。
- 主审 100%，第二复审按风险覆盖。
- 核心若改动，探针永久降级为 development evidence。

### E11 `GATE1_SEALED_HIDDEN_PROBE40_V11_001`

**目标**：在核心冻结后，由独立 curator 创建全新隐藏 20 正向 +20 路线，完成资格证明。

**验证**：

- hidden 输入在 core freeze 后生成，未烤入代码、prompt 或组件选择表。
- 无 reroll、替换、反馈回灌和分母重算。
- 正向首次可接受率至少 90%，硬否决 0。
- 路线 20/20 正确。
- v1.1 主审、第二复审、分歧裁决完整。
- 只有 Founder 可裁定 generator qualified；即使通过也不自动 runtime-ready。

### S01...Sx `GATE1_POSITIVE_PARENT_SCALE_BATCH40_<NNN>`

**数量**：`x = ceil((240 - N - H) / 40)`，当前保守为 3 至 6 个 Prompt。

**目标**：按 E03 的逐 CP 缺口，在同一冻结生成器核心上生产、审核并冻结剩余正向父级内容。

**每批验证**：

- 生成前冻结 40 个输入及 CP 分配，最后一批可小于 40。
- 首次可接受率总体至少 90%，失败不换样。
- 每条主审，第二专家覆盖满足累计 48 条且每 CP 至少 2 条。
- 一票否决 0，明显套话/近重复不超过 10%。
- 不得因批次失败静默改 core；core 一旦修改，必须回到 E10/E11 重新取得资格。
- 至少两个稳定性批次使用同一 core；首批暴露核心问题时停止第二批。

### E12 `GATE1_300_AND_COMPONENT_GOLD_BASELINE_CLOSEOUT_001`

**目标**：把批准的 240 正向、黄金 60 路线、86 组件候选的黄金裁决和生成器版本统一冻结为 Gate 1 最终基线。

**验证**：

- 300/300 有来源、版本、CP、机器检查和审核记录。
- 正向 240/240 最终批准；每 CP 12 条。
- 路线 60/60 正确；每 CP 3 条。
- 每 CP 至少 11/12 首次可接受，密封批次总体至少 90%。
- 86/86 组件有 gold decision，批准数 `M` 如实记录。
- 543/543 CP edges 和 887+ component cases 可追溯。
- 盲测、多样性、近重复、硬否决和错误阻止率通过。
- 运行清单、模型配置、输出摘要、人审批次和失败记录齐全。
- Founder 显式批准前，所有 runtime/production/readiness 仍为 false。

## 11. Prompt 数量与依赖关系

### 11.1 推荐数量

```text
固定 Prompt              = 12
正向扩量 Prompt          = ceil((240 - N - H) / 40) = 3..6
推荐总执行 Prompt        = 15..18
```

这不是“最少文件数”，而是可审计、可停损、避免单 Prompt 同时写规则又给自己打分的推荐原子任务数。

### 11.2 串并行关系

```text
E01
├── E02 -> 外部人审 -> E03 ------------------------┐
├── E04 --------------------------------------------|
└── E05 -> E06 -> 外部组件人审 -> E07 -> E08 -> E09
                                                  |
                                                  v
                                          E10 -> E11
                                                  |
                                                  v
                                             S01..Sx
                                                  |
                                                  v
                                                 E12
```

- E02/E03、E04、E05/E06/E07 在 E01 后可分三条工作流并行。
- E08 必须等组件类型和 gold decision 稳定后再冻结接口。
- E10、E11、扩量批次必须串行，禁止边看 hidden 结果边调 core。
- 人审 Checkpoint 不计为执行 Prompt，也不能由执行代理自签。

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
| 组件边 | 543/543 有独立结论 |
| 组件测试 | >=887 primary gold cases，mutation battery 另计 |
| 可复现 | generator/rule/schema/model/input/output/review 全有版本与 digest |
| 状态 | Gate 1 通过仍不等于正式 DB、CompositionPlan、runtime 或 production ready |

## 13. 决策选项

### 方案 A：回到 Gate 1 闭环，推荐

执行本报告 E01-E12 和 S01-Sx。保留现有 ORCH/Generator 产物为开发与失败证据，停止继续为当前开发门叠加新 checker 和新 route。

**优点**：最符合 v1.1；先建立可相信的内容、组件和评价基线；后续正式 ORCH 有稳定输入。

**代价**：短期看似“后退一层”，需要真实人审资源和 15 至 18 个原子执行 Prompt。

### 方案 B：继续修 PR #13 当前链路，不推荐

继续补 lexical validator、Pair、transport 和 reviewer timeout，再跑 40 条。

**问题**：即使跑绿，也仍没有 `N`、240 正向、v1.1 review records、86 组件 gold decisions 和完整 Profile 投影，无法证明 Gate 1。

### 方案 C：立即引入外部 provider，不建议作为当前根因修复

当前没有证据证明瓶颈是模型能力。先修对象合同、材料和评价链，再用 E10/E11 判断是否需要模型升级。若换模型，必须作为新的 engine config 重新资格验证。

## 14. Founder / Guardian 需要裁决的事项

1. 是否确认 v1.1 为当前 Gate 1 唯一验收标准，并暂停继续扩正式 ORCH/runtime。
2. 是否同意把历史 120 改称 `legacy_reference_count`，在 E03 前不再声称 `N=120`。
3. 是否同意“86 个黄金基线”定义为 86/86 有测试和裁决，而不是 86/86 必须批准。
4. 是否批准最低 887 个组件 primary gold cases 的口径。
5. 是否批准推荐的 15 至 18 个 Prompt 路线，并允许 E02/E04/E05 三线在 E01 后并行。
6. 是否维持 PR #13 为未合并失败证据，直到有单独的失败归档/合并 Brief 再处理。
7. 是否承诺配置真实主审、第二专家和裁决角色；Guardian 不替代 240 条全量内容主审。

## 15. 执行纪律

- 每个 Prompt 必须固定 baseline HEAD、允许写面、不可变输入和停止条件。
- 规则作者、案例 expected 设计者、内容作者和最终审查者不得由同一产物自证。
- 机器 checker 只证明结构与明确可判不变量，不声称证明自由文本最终质量。
- 不因失败换样、删分母、回填事实、修改 source atoms 或降低 hard gate。
- 不把组件数量、组件引用数、checker 绿灯或 synthetic fixture 数量计入 240 正向父内容。
- 不在本路线中改变 KE/RAG/DIFY/Serving/runtime/production readiness。
- 外部人审结果必须签署、版本化、append-only；执行 Prompt 只做独立重算和冻结。

## 16. 证据索引

### 标准

- v1.1 第一门与 300 条：第 114-247 行。
- 正向内容 70+30 与 20CP 专项：第 458-568 行。
- 组件 80+20 与最低线：第 654-694 行。
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
  fixed_prompts: 12
  variable_scale_prompts: 3_to_6
  total_prompts: 15_to_18
  positive_target: 240
  route_target: 60
  component_candidates_covered: 86
  component_claimed_edges_covered: 543
  minimum_component_gold_primary_cases: 887
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

本报告只授权讨论和审查，不授权执行 E01-E12、生成新内容、修改 86 组件、合并 PR #13 或改变任何 readiness。后续须由 Founder 明确批准首个执行 Brief，再按 Guardian Pre-Review -> Codex 执行 -> Guardian Domain Review 的分权流程推进。
