# M3 标注协议 v1（ANNOTATION_PROTOCOL）

> 机器规格与冻结提示词模板：`annotation_protocol.v1.json`（模板逐字摘要冻结，执行器只认摘要匹配的模板）。
> 覆盖：双盲金标建标框架（角色、载体、批量、裁决、争议率/成本口径）+ 附录A（risk + entailment 量规，随小试冻结）。
> 附录 B–E（参考断言抽取 / 主张原子化 / 套路成对 / 披露与省略）在 G1/G2 各胶囊内按本框架增补冻结。

## 1. 角色与载体（3.7′ / E11 合规）

| 席位 | 承载 | 隔离 |
|---|---|---|
| GOLD_BUILDER_A / GOLD_BUILDER_B | `claude -p` 全新 headless 会话，每批一叫，单轮、无工具 | `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 命令级注入；cwd 钉在仓外中性目录；彼此不可见（双盲）；逐叫登记 session_id/成本/时长 |
| GOLD_ADJUDICATOR | 同载体，另起全新会话 | 只见分歧用例 + 匿名化双方标签（甲/乙），不知席位身份 |
| 编排（策展人） | 本顶层会话 | 只做元数据级编排；开发格（G1/G2）材料可见（非密封）；密封 QUAL 建标复用本协议时，用例包由确定性工具进程内送入 stdin，编排端零接触明文 |

**披露（诚实边界）**：本环境 headless 会话仍被注入用户级 CLAUDE.md（不可关闭；实测 ~28k cache_creation tokens）。该注入不含本项目旧里程碑授权语义（已核阅），对标注为潜在文风偏置项而非保全泄漏向（自动记忆写入已禁用）。双席位同为 claude-fable-5：席位独立性在会话/上下文层，不在模型层——开发金标治理仅要求双独立标注（two_independent_labels_required），模型多样性不在其列；此局限逐字披露给双独立审核。DeepSeek 不用于金标建标（其 scope 合同限定套路语义评审，越 scope=违约）。

## 2. 双盲流程（每模块通用）

1. **用例包构造**（确定性工具）：case_id + 判断所需最小材料；批量 10 用例/叫（降摊会话开销）。
2. **A/B 独立标注**：同一批次包分别送 A、B 席位；提示词=冻结模板+批次 JSON；输出=严格 JSON 数组。
3. **解析与重试**：输出不可解析或 case_id 集不匹配 → 同提示词重试一次（保留首次原始输出，登记 retry）；重试仍失败 → 该批 FAILED，不得静默丢弃。
4. **裁决**：任一标签不一致的用例进裁决批；裁决者见匿名双方标签+理由，出最终金标+裁决理由。
5. **登记**：每叫落 SESSION_REGISTRY 一行（席位、session_id、批 id、可见材料清单=批内 case_id、原始输出留存路径、cost_usd、时长、重试标记）。

## 3. 口径（冻结）

- **争议率** = 至少一个标签不一致的用例数 / 完成用例数（按模块分开报告；risk 相邻级不一致也计入）。
- **一致性** = 原始一致率（逐标签）+ 逐类一致率 + Cohen κ（risk 4 类、entailment 3 类分别算；不可解释时报 raw + 类别一致率，κ 记 NOT_INTERPRETABLE）。
- **成本** = Σ result.total_cost_usd（每叫机器回执直读）+ 墙钟 Σ duration_ms；按用例摊销另报。
- **金标产出** = A/B 一致值直取；分歧取裁决值；裁决亦分歧（缺席）→ 用例标 UNRESOLVED 不入金标（计入争议率分母）。

## 4. 小试预登记（PILOT）

- **样本**：每族按 `sha256(frame_digest + scenario_id)` 升序取前 2 组（确定性、无 RNG），共 10 组；该 10 组**永久划入 DEV 可见性分区**（组不可分；此后任何 QUAL 抽样框不得含这些组）——预登记于 `PILOT_SAMPLE.v1.json`，晚于本登记的任何改动=补录违规。
- **用例**：10 组全部 4 轮条目的全部 claims（预期 ~110±），每条出 risk + entailment 两标签。
- **小试目的**（回填供需 v2 表）：①自然标签分布实测（supported∧risk∈{LOW,MEDIUM} 占比 vs 0.59 阈值→定补给 Tier）②双盲一致性/争议率③摊销成本/吞吐。
- **成功判据**：完成率 ≥95%，争议率 ≤ 0.35（超限=协议量规须修订重小试，不得带病进 G1/G2），成本口径完整可复算。

## 5. 附录 A：risk + entailment 量规（随小试冻结）

- **risk（主张风险载荷）**：LOW 一般描述，失实伤害轻微；MEDIUM 可能误导购买判断；HIGH 涉身体效果/性能承诺/真实性背书/授权边界，失实致实质伤害；CRITICAL 失实致安全/健康/法律伤害。结合 claim_boundary 与 authorization_scope 评「主张本身的风险载荷」。绑定 spine `RISK_LEVELS`。
- **entailment（对源支持关系）**：SUPPORTED / CONTRADICTED / UNKNOWN，参照系=场景 slot_facts + source_summary_a/b。绑定 spine 语义标签集。
