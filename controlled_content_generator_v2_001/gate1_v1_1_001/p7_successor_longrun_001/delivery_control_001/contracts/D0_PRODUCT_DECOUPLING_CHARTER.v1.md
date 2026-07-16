# D0 · 产品解耦章程 v1（D0_PRODUCT_DECOUPLING_CHARTER）

> 性质：授权工具（非里程碑，不计 Prompt）。真源：v2.4 §四 4.1 八项冻结域 + v2.5 §四 4.1′ 生效方式修订 + P1 §十-C1。
> 生效方式（v2.5 §壹-9 授权）：**不再等待发起人批准仪式**——本章程文书落盘 + 文本摘要冻结 + 活跃合同摘要冻结 +
> 独立审核通过 + 审核者隔离声明有效，五条件合取达成后 `D0_PRODUCT_DECOUPLING_CHARTER_APPROVED` 成立。
> 条件合取状态唯一登记处：`delivery_control_001/state/D0_STATUS.v1.json`（禁止只写一个布尔值宣布已批准）。
> 发起人可随时叫停或收回（v2.5 §壹-9）。

## 冻结八项

### ① A/B 目标仓与独立远程原则

- 产品 A（评测与审计脊柱应用）与产品 B（V1.1 内容生成资格应用 + 基线资产集）**最终各自交付于独立产品仓 + 独立私有远程**。
- 两仓互相独立：不同仓、不同远程、不共享 Git 历史；B 仓禁止 import 产品 A（v2.4 §二-2）。
- 新仓与新远程的**创建时点**：产品 A 属 M5、产品 B 属 M7（流程内默认授权，v2.5 §〇）；M1–M4/M6 一律不得创建。
- 仓与远程创建动作必须登记于当时里程碑的启动记录与 CLOSEOUT 证据，绑定创建者会话身份。

### ② 源仓临时产品 core 顶层暂存写面（登记，不创建）

- 未来 core 抽取（M3）允许使用的源仓临时暂存写面**预登记**为：`controlled_content_generator_v2_001/product_core_staging_001/**`（顶层暂存目录，路径措辞=相机，边界=冻结）。
- **M1 仅登记此边界，不创建目录、不放置任何文件**（P1 §八：M1 创建顶层 A core 暂存 = 越权，负向测试 #20）。
- 暂存写面只见接口、schema、非密封开发样例；此后 P7 只放执行证据与摘要，不再生长产品代码（v2.4 §四 4.3）。

### ③ 可抽取代码范围（allowlist 原则）

- 唯一授权抽取来源：`CORE_EXPORT_ALLOWLIST`（delivery_control_001/contracts/CORE_EXPORT_ALLOWLIST.v1.json）。
- allowlist 只允许列入：评测/审计逻辑代码、schema、量规模板、自含验证套件、产品文档模板。
- 抽取以逐文件 sha256 的 `EXTRACTION_MANIFEST` 执行（v2.5 §四 4.4′-①：新仓首提交必须复现全部摘要一致，机械同一性与行为等价双证，签字绑定双摘要）。

### ④ 必须留源仓的领域数据（denylist 原则）

- 唯一禁运清单：`DOMAIN_DATA_DENYLIST`（delivery_control_001/contracts/DOMAIN_DATA_DENYLIST.v1.json）。
- 永不出仓：QUAL-A/B、隐藏 40、G1/G2 金标、round/R1–R5 数据、领域事实账本、编造样本、审计内档、失败轮次证据、旧 120 原文、86 历史候选、路线 60 黄金答案、组件基座。
- 240+60 基线资产集是产品 B 交付物，随 B 仓交付（v2.4 §二-3），不属 denylist。

### ⑤ 产品仓 ↔ 源仓单向测试协议

- 唯一协议：`SOURCE_TO_PRODUCT_TEST_PROTOCOL`（delivery_control_001/contracts/SOURCE_TO_PRODUCT_TEST_PROTOCOL.v1.md）。
- 方向唯一：源仓 → 产品仓（测试语料经适配器挂载）；产品运行输出**不得反向写入源仓**（v2.4 §二-4）。

### ⑥ 客户数据不得进任何 Git 仓

- 含源仓与产品仓；当前执行阶段零客户数据（红线维持）。
- 扩展边界（v2.5 §二 #11）：产品默认配置中日志/遥测/缓存/备份不得落客户数据明文；外部模型路径登记提供方数据保留条件并在交付文档披露；交付验收含合成数据负向测试。承载模板：`customer_data_governance.template.v1.md`。

### ⑦ 新仓许可、权限与签字边界

- 新产品仓许可证、第三方代码许可证、模型/API 条款再分发权、素材与派生资产权利链：交付出口逐项清点（`RIGHTS_CLEARANCE.template.v1.md`）；清权未闭合 = 交付出口不过（v2.5 §二 #12）。
- 新远程为**私有**；权限最小化；签字边界按 `GPT_CODEX_SCOPE_CONTRACT` 与 `ROLE_MODEL_MATRIX`（签字权源 = 发起人授权，HUMAN_OR_LEGAL_SIGNER_REQUIRED=NO，v2.3 §壹-1）。

### ⑧ 搬仓后语义变化必须重新资格化

- 搬仓中改动语义代码/阈值/依赖行为/模型编排 → `A_LIFT_READY` / `B_LIFT_READY` 失效，重跑相应资格（v2.4 §四 4.4）。
- E9 之后任何代码、资产、配置或依赖改变使资格失效（P1 §十九）；机械判据由 `RELEASE_EQUIVALENCE_ATTESTATION` 与 B_LIFT 链合同承载。

## 生效条件（合取，禁止布尔速记）

```text
D0_TEXT_ON_DISK                     # 本文件落盘
AND D0_TEXT_DIGEST_FROZEN           # 本文件 sha256 冻结于 D0_STATUS
AND ACTIVE_CONTRACT_DIGEST_FROZEN   # ACTIVE_CONTRACT_DIGESTS.v1.json 集合摘要冻结
AND INDEPENDENT_REVIEW_PASS         # 独立审核回执（含 D0 审查范围）verdict=ACCEPT
AND REVIEWER_ISOLATION_VALID        # 签字回执 session_isolation_attestation 有效
```

任一条件缺失时，`D0_PRODUCT_DECOUPLING_CHARTER_APPROVED` 不成立，M1 边界胶囊之外不得引用 D0 效力。

## 边界重申

D0 只批授权与边界：不建正式产品仓、不搬代码、不复制历史、不推新远程（v2.4 §四 4.1）。
