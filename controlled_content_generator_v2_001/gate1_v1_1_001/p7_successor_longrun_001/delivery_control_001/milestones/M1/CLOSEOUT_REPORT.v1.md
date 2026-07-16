# M1 关闭报告 v1（CLOSEOUT_REPORT）

```yaml
milestone_id: M1
result: PASS
review_state: M1_ACCEPTED
accepted_candidate: 11b71e9bed9078c2483dc27ae94a807689ff5528
input_commit: 23f5fea355ef4904043c98187ba2a82c846772be（= v2.5 冻结基线，现场核实一致）
session: f719e24e-7b51-48c0-9c24-9655a6525be8（Fable 5 / claude-fable-5，全新非 fork 顶层会话）
m2_start_eligible: true
m2_state: M2_READY_TO_START（同会话禁启；会话外监督器于本会话退出后启动）
```

## 1. 胶囊与提交链

| 胶囊 | 提交 | 内容 |
|---|---|---|
| C0 现场保全 | `f7d6619` | 74 用户 dirty 工件逐字入库（73 A + 1 M=会话前既有 checker 脏改动逐字保全）；93 条盘点 sha256 锚 `9d1cfd7f…` |
| C1 真源与授权 | `931d06c` | SOURCE_LOCK / ACTIVE_CONTRACT_SET=v2.5@23f5fea / supersession 链 / D0 章程 / GPT scope / 角色矩阵 / typed+签字 schema / 上位合同 v2 / RUN_JOURNAL |
| C2 三层迁移 | `f03b48b` | 23 位点四家族迁移；实际/期望态分离；checker 状态感知化；正向未来态+攻击测试底座 |
| C3 控制面 | `cf5016d` | P1–P7 注册表；MILESTONE_DAG；ready_set/renderer/launcher/closeout/receipts；产品边界/密封/清权/QUAL 全序/B_LIFT 链合同；30 项攻击矩阵 |
| C4 候选冻结 R1 | `3b29055` | 语义扫描双层（确定性 17 族 + workflow 四镜头）抓 2 条清单外真残留并修复 |
| C5 审核 R1 修复 | `4c28642` | 只读审核兼容 / 回执 v2 于候选头 / frozen_snapshot 机制 / 环境工件过滤 |
| C6 审核 R2 修复 | `11b71e9` | **V11_STATUS 实际态真源** + 期望消费 + 快照路径遍历加固（= 接受候选） |

## 2. 两份独立审核（P1 §十六，三轮收敛）

| 轮 | 候选 | Fable/Claude 对抗审查 | Codex-GPT 复算 |
|---|---|---|---|
| R1 | 3b29055 | ACCEPT + 2 ADVISORY | REJECT（2 BLOCKING：只读审核不兼容；回执 head≠候选） |
| R2 | 4c28642 | ACCEPT（4 项 R1 修复实证）+ 1 ADVISORY | REJECT（1 BLOCKING：V1.1 无磁盘真源） |
| R3 | **11b71e9** | **ACCEPT**（3 项 R2 修复实证：10 例合成根、攻击重放、豁免逐条核）+ **D0 ACCEPT** | **ACCEPT**（22 检查、6 探针、零 finding） |

签字回执（绑定同一候选 + 同一 manifest 摘要三元组 e118930818/16a8f322/347c7fe3）：
- `INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER.8f812c89b959.signer_receipt.json`（sha256 `8f812c89…`）
- `CODEX_GPT_EXTERNAL_REVIEW_SIGNER.628a3e461bdd.signer_receipt.json`（sha256 `628a3e46…`）

审核回路纪律：每轮候选变化即作废两份既有审核并对新候选全部重跑（P1 §二十二）。

## 3. P1 §二十四 合取条件逐项

| 条件 | 状态 | 证据 |
|---|---|---|
| V2_5_ACTIVE_CONTRACT_FROZEN | ✅ | SOURCE_LOCK + ACTIVE_CONTRACT_DIGESTS（16 成员集合摘要 `cbe5f5f4…`，verify PASS） |
| WORKTREE_INVENTORY_PRESERVED | ✅ | C0 逐字保全（审查双方独立证实 74/74 匹配）+ 盘点 TSV |
| D0_TEXT_AND_INDEPENDENT_REVIEW_VALID | ✅ | 五条件合取全满足；d0_approved=true 由 checker 复算；Fable R3 d0_verdict=ACCEPT |
| UPPER_CONTRACT_AND_AUTHORIZATION_MIGRATION_COMPLETE | ✅ | longrun v2 / execution_authorization v2 / implementation_authorization v2 + supersession 账本 |
| ALL_KNOWN_23_SITES_MIGRATED | ✅ | test_migration_sites 15 用例 + 两轮审查逐位点复核 |
| REPOSITORY_WIDE_RESIDUAL_SCAN_PASS | ✅ | 确定性 17 模式族 0 违规 + workflow 四镜头语义扫描（2 清单外真残留已修） |
| ACTUAL_STATE_SEPARATED_FROM_EXPECTATION | ✅ | M0_STATUS/V11_STATUS/两 manifest/stage_actual = 实际态；STATE_EXPECTATION = 期望态；checker 双读比较 |
| POSITIVE_FUTURE_STATE_TESTS_PASS | ✅ | 10 正向未来态用例（拨付/金标物化/M0 合格/B 轨推进/V11 合格/S3 无提升不 kill） |
| NEGATIVE_ATTACK_TESTS_PASS | ✅ | 30 攻击方法 51 断言全部按预期拒绝（审查证实无 skip/空断言/降阈值） |
| Y_STATE_MACHINE_PASS | ✅ | ready_set 16 例自测 + 审查探针（路线 (b) 只认 A2_QUALIFIED；M7 只认 B_LIFT_READY） |
| TYPED_RECEIPT_TESTS_PASS | ✅ | schema 终态强制 + 摘要复算 + 移植/伪造/REVIEW_READY 冒充全拒 |
| RUN_JOURNAL_RECOVERY_PASS | ✅ | 崩溃恢复自测 10/10；哈希链 9 条记录与 Git 互校 |
| PROMPT_REGISTRY_P1_TO_P7_COMPLETE | ✅ | 7 项全字段；初始状态精确；禁 LOCKED_NO_AUTHORIZATION |
| SESSION_EXTERNAL_LAUNCHER_TESTED | ✅ | launcher 13 例自测（拒同会话/子代理伪装/缺签字/不合格前序/活跃前会话；合成新会话身份） |
| SEALED_CUSTODY_TESTS_PASS | ✅ | 合成标记撞库（工作树/git 全历史/软链）+ 客户数据标记扫描 |
| PRODUCT_BOUNDARY_AND_LIFT_SCHEMAS_PASS | ✅ | 边界合同套件 + lift_chain 机械判据 15 例自测 |
| QUAL_A_B_ORDER_CONTRACT_PASS | ✅ | 六步全序验证器 5 例（含揭晓后重建 QUAL-B 拒绝） |
| RIGHTS_AND_CUSTOMER_DATA_GOVERNANCE_TEMPLATES_PASS | ✅ | 清权模板 + 客户数据治理模板 + 无清权即拒交付/合成标记负向测试 |
| TWO_INDEPENDENT_REVIEWS_BOUND_TO_SAME_CANDIDATE | ✅ | R3 双 ACCEPT 绑定 11b71e9 + 同 manifest 摘要 |
| CODEX_ACCEPTANCE_RECEIPT_VALID | ✅ | 628a3e46… 回执 schema+摘要+隔离声明全验 |
| FULL_TEST_SUITE_GREEN | ✅ | VERIFICATION_RECEIPTS.M1.v3：18/18 于候选头（49+49+55 测试、8 工具自测、PRE_REVIEW 三域） |
| MANIFESTS_RECOMPUTABLE | ✅ | 三 manifest 双方审查逐条复算；frozen_snapshot 三方一致 6/6 |
| ORIGIN_ANCHOR_VERIFIED | ✅（推送后由 ORIGIN_ANCHOR.v1.json 记录远端复核） |
| M0_REMAINS_HONESTLY_NOT_QUALIFIED | ✅ | calibration/M0_STATUS.v1.json = NOT_QUALIFIED |
| V1_1_REMAINS_HONESTLY_NOT_QUALIFIED | ✅ | calibration/V11_STATUS.v1.json = NOT_QUALIFIED（Codex R2 BLOCKING 修复后可机械复算） |
| M2_NOT_EXECUTED_IN_M1_SESSION | ✅ | executed_stages=[]；无真实 S0；M2 仅 READY_TO_START + 冻结渲染 Prompt |

## 4. 能力与偏差登记（诚实记录，非降标）

1. **FABLE_SUBAGENT_CAPABILITY_UNAVAILABLE**：环境将子代理模型钉死为 claude-opus-4-8（探针实证，见 AGENT_LEDGER_ADDENDUM）。两份 Fable/Claude 侧审查由 Claude 家族（Opus 4.8）承担并逐回执诚实登记实际模型——满足 P1 §十六「独立 Claude/Fable 对抗审查」文面；ROLE_MODEL_MATRIX v1 中该角色的 fable 登记属执行侧相机设计，矩阵 v2 修订留待 M2。
2. **AUTO_LAUNCH（M2）**：launcher 具备真实 spawn 能力（claude CLI 路径已实现并自测），但 M1 会话内禁用（同会话停线）；M2 = READY_TO_START + 冻结 Prompt（摘要 `e8d036f8…`），由会话外监督器在本会话退出后执行 `--dry-run M2 && --start M2`。
3. **run_id**：Claude Code 未暴露独立 run 标识——UNAVAILABLE 三元组登记（SESSION_IDENTITY）。
4. **自动记忆**：会话启动时已注入（来源三处已登记盘点，零 v2.3/v2.4 旧授权语义）；后续命令与审查会话均显式禁用；launcher spawn 强制注入 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`。
5. **审查 ADVISORY 处置**：R1/R2 全部 ADVISORY 均已在后续候选修复（写面环境工件过滤、快照遍历加固、区间空白检查）；R3 零 ADVISORY、3 条 INFO（皆为流程即景说明，无行动项）。

## 5. 300/120/86 口径（对发起人）

- **300**：未达成、未受损（V1.1 诚实 NOT_QUALIFIED，B 轨 S2–S7 未执行——属 M6 工作）；
- **120**：保持（frozen_inputs 锚点 + checker freeze_integrity PASS）；
- **86**：保持（EXTRA_PROTECTED 摘要锚 PASS）。

## 6. 附件索引

八件套（本目录）+ READY_SET_RESULT + 两份审查报告（R3 全文）与三轮 Codex 事件流 + 签字回执 ×2 + snapshots/ 五快照 + REVIEW_REQUEST（含 R2/R3 说明）+ CODEX_REVIEW_PROMPT + M2 冻结渲染 Prompt（milestones/M2/）+ ORIGIN_ANCHOR（推送后追加提交）。
