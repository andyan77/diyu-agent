# Creative Content Principle — 3600 微批次开工核心原则 (v0.1)

任务 / task: `GKB-3600-MICROBATCH-BRIEFING-AND-GO-NOGO-001` (P6)
状态 / status: `briefing_requirement_only`（开工前 briefing 原则，不是 ontology、不是分数、不是 production 条件）

---

## 0. 一句话 / TL;DR

笛语不是安全合规模型，笛语是服装行业内容生产系统。治理门负责不犯错，Creative Gate 负责判断有没有内容生产价值。两个门并列，都要过，谁也不能替代谁。

---

## 1. 定位纠偏 / What 笛语 actually is

- **笛语不是安全合规模型。** 只会"不越权、不胡说、不错层、不伪闭环"是必要底线，不是产品价值本身。
- **笛语是服装行业内容生产系统。** 它的产出最终要变成能看、能拍、能穿、能带货的服装内容：视觉场景、单品细节、真实生活场景、审美判断、叙事节拍、角色口吻、内容玩法。
- 只强化治理系统 = 造了一个不会犯错但也不会创作的空壳。P6 之后的所有生成，必须同时被治理门和 Creative Gate 约束。

## 2. 两个门的分工 / Two gates, orthogonal

| 门 / gate | 负责判断 | 判据本质 |
|---|---|---|
| **治理门 / Governance Gate** | 内容有没有犯错：越权 / 胡说 / 错层 / 伪闭环 / 泄露真实实例事实 / 硬主张无证据 | 不犯错才能进入后续；这是**否决权**，不是加分项 |
| **创意门 / Creative Gate** | 内容有没有生产价值：好不好看、好不好拍、真不真实、有没有情绪审美生活感转化力 | 有内容生产价值才算好知识；这是**内容价值判断**，不产生 production readiness |

**关键规则**：

- **只过治理门，不算好知识。** 一条"绝对安全但毫无内容生产价值"的知识，治理门放行，但 Creative Gate 判为无价值，它不是好知识。
- **只过创意门但越权，也不能进入后续。** 一条"很好看很会写但泄露了真实门店/顾客/SKU 事实或越权解锁下游"的内容，Creative Gate 再高分也被治理门否决，不得进入后续。
- **Creative Gate 不替代 Governance Gate，也不弱化它。** 两门是并列的、正交的；创意分高不能抵消任何一条治理红线。

## 3. 治理知识 vs 面向正文的知识 / Governance knowledge vs body-facing knowledge

- **治理知识只进入 compiler / judge / sidecar / route。** owner 为 GovernanceOutbox / EvidencePolicyOutbox / SourceGapLedger 的知识是控制面，它们进入编译器、裁判、旁车、路由决策，**不写进面向读者的正文 body**。
- **面向正文的知识必须使用服装内容生产语言。** 进入正文的知识（GeneralKnowledgeBase / ExecutionAssetOutbox 语义）要说人话、说服装话：场景、单品、搭配、材质、光线、身形、情绪、玩法，而不是治理术语。
- **正文不得被治理话术污染。** 正文里不允许出现 checker / source_gap / route_decision / readiness / owner_candidate / epistemic_class 等治理话术；这些词只属于 sidecar 与 route，不属于读者看到的内容。

## 4. 对 P7 3600 生成的硬约束 / Hard constraints on P7 generation

- 生成正文时**必须引用 proposition_id**，不得在 proposition 之外编造新事实。
- SourceGapLedger 命题只能作 gap / routing hint，**不得**当正向领域事实写进正文。
- GovernanceOutbox 命题只能作 control / route / stop rule，**不得**写进正文。
- EvidencePolicyOutbox 命题只能作 claim / evidence policy，**不得**误写成普通 GeneralKnowledgeBase 正文内容。
- Creative Score 只用于内容生产价值排序与生成要求引导，**不得**变成 production / readiness 条件。

## 5. 这份原则不做什么 / What this principle is NOT

- **不**把 AestheticFrame / VisualScene / StylingLogic / NarrativeBeat / HumanVoice / CreativePattern 注册为 ontology Object / TBox / ABox / KE。它们只是 briefing 阶段的生产能力要求（`briefing_requirement_only`）。
- **不**解锁 3600 生成、**不**解锁 CandidatePack / Four-Gate / KE / Serving / RAG / DIFY。
- **不**把 proposition_pack_v1 标为 accepted domain knowledge。
- **不**翻任何 readiness flag。

> 本文件是 P6 briefing 的原则声明。它约束 P7 将来"怎么生成"，但它本身不授权 P7 生成。真实 3600 生成需要单独的 founder 授权 + Codex 三关。
