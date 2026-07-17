# M1 关闭报告 v2（R5 · 发起人八项加固指令回合收束）

```yaml
milestone_id: M1
result: PASS
review_state: M1_ACCEPTED
accepted_candidate: de83d92cac695cd3e8c603e8817e875f3d567bfa   # M1-C8
input_commit: 23f5fea355ef4904043c98187ba2a82c846772be          # v2.5 冻结基线（候选严格祖先）
session: f719e24e-7b51-48c0-9c24-9655a6525be8（Fable 5 / claude-fable-5，全新非 fork 顶层会话）
supersedes: 关闭报告 v1（R3 集，SUPERSESSION_LEDGER §5）
closeout_commit: 本文件所在提交（不自指；由 ORIGIN_ANCHOR.v2 以「锚提交第一父 == closeout_commit」规则锚定）
m2_start_eligible: true
m2_state: M2_READY_TO_START（同会话禁启；会话外监督器于本会话退出后启动）
```

## 1. 本轮语境：发起人八项加固指令（2026-07-16）

R3 双 ACCEPT（候选 `11b71e9`、关闭 `5cf3ea2`、锚 `4ddbd1f`）之后，发起人下达八项加固指令并要求全链重跑。实现与验证映射见 `REVIEW_REQUEST.v2.md` §2（指令→实现→攻击面自证）与 `REVIEW_REQUEST.v3.md` §0（R4 回路与 C8 修复）。

| 胶囊 | 提交 | 内容 |
|---|---|---|
| C7 加固实现 | `ccf27017` | signer v2（绑 milestone/产品域/三 manifest + 启动前禁记忆声明）；HANDOFF v2（全引用可复算，删自指的 control_plane_commit）；closure.py（可重建闭包 + 全引用复算器）；MILESTONE_EXIT_CONTRACT（M1/M2 冻结、M3–M7 fail-closed）；出口证据 schema；launcher 记录/结果分离（spawn 前原子落盘 + HEAD 绑定）；FINAL 双 typed 逐字段比对 + M2 真实 S0 机械证明；攻击矩阵 30→40；合同集 17 成员重冻结 |
| C8 回路修复 | `de83d92`（=接受候选） | Codex R4 BLOCKING#1 修复：`launched_at_head` 三重锚（现场比对 / 仓库态复核 / spawn 前哈希链 journal 交叉绑定 + `verify_launch_binding`）；攻击 41；spine.manifest 排除审核会话缓存（Fable R4 ADVISORY） |

## 2. 审核轮次（P1 §二十二回路全程执行）

| 轮 | 候选 | Fable/Claude 对抗审查 | Codex-GPT 复算 |
|---|---|---|---|
| R1 | 3b29055 | ACCEPT | REJECT（2 BLOCKING） |
| R2 | 4c28642 | ACCEPT | REJECT（1 BLOCKING） |
| R3 | 11b71e9 | ACCEPT + D0 ACCEPT | ACCEPT（原关闭 5cf3ea2/4ddbd1f） |
| R4 | ccf27017 | ACCEPT（ADVISORY 独立命中 launch-head 洞） | **REJECT**（BLOCKING#1 launch-head 自证洞=真缺陷；#2 read-only 沙箱无 /tmp=环境因） |
| **R5** | **de83d92** | **ACCEPT + d0_verdict ACCEPT**（claude-fable-5，session be2aec5a…，八指令 8/8 verified，零 B/A） | **ACCEPT**（GPT-5 Codex，workspace-write 沙箱全电池复跑，八指令 8/8 verified，零 B/A） |

R5 签字回执（signer v2，绑定候选 + 三 manifest 摘要 + milestone/产品域；隔离声明五键含 `auto_memory_disabled_before_launch`）：
- `INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER.bf75def209d8.signer_receipt.json`（sha256 `cb6bae7b94c81dac…`；含 d0_verdict=ACCEPT）
- `CODEX_GPT_EXTERNAL_REVIEW_SIGNER.c8e0f3eb2104.signer_receipt.json`（sha256 `2470247e7804e730…`）

两审核会话均为全新非 fork/非 resume 顶层会话、自动记忆**启动前**禁用（指令第 7 条）；Fable 侧实际模型 **claude-fable-5**（CLI 顶层 spawn 突破了此前子代理被钉 Opus 的环境限制，R3 的 FABLE_SUBAGENT_CAPABILITY_UNAVAILABLE 登记就此收敛）。

## 3. 绑定摘要（R5 冻结）

| 项 | 值 |
|---|---|
| INPUT_MANIFEST.v2（9 条） | `ad112305ad295ce166e5d3e6f4a62aab3d9937c9c2b4766fc4be8efedfa3c791` |
| OUTPUT_MANIFEST.v2（157 条） | `283c1fce90af37a5dacad0cf4855b3a7f80cb88b868934265742b238aca11ed2` |
| EVIDENCE_MANIFEST.v2（16 条） | `d10b9f5ddd57fdfd2df51017ad7d77edc5ed514adaecbfab2478186ac74d402c` |
| MILESTONE_EXIT_EVIDENCE（M1 八键全证据） | `b98fad4314392b5b7965e675987884729fd21c234333430798bb7df8e7a24e22` |
| HANDOFF.v2 | `e3a72ffd778aadd672f09212e9ea907649386df6b749a8b33f1490e0f662840f` |
| CLOSEOUT_RECEIPT.v2（typed PASS） | `ecff2dcfc87cedfe335a74073093d6027e9dd971e8835abace7bd13816419d15` |
| 电池回执 v5（候选头 16 检查全绿） | `a6376e93fe90b1e696cd803f19718c3d5e9ad701b21a7faad480ce910670e861` |
| 活跃合同集合（17 成员） | `d7265a1852e4b44db1fae134f5d03e404629470ee7438c36d08b1cc00d85a7e4` |

FINAL 模式（加固后硬门）：`RESULT[SHARED] PASS (11)`（含 final_receipts：双 typed 逐字段比对、signer v2 三 manifest 绑定逐项、里程碑出口八键逐键、HANDOFF 全引用复算）/ `RESULT[A] PASS (5)` / `RESULT[B] PASS (6)` / `ARTIFACT_INTEGRITY PASS`。

## 4. 诚实基线与登记

- M0 与 V1.1 均 **NOT_QUALIFIED**（各自磁盘真源；出口证据键逐字节绑定）。
- M2 未执行、无真实 S0；M2 出口已按指令第 5 条冻结为机械证明条款（S0 六项镜像 + BOUNDARY_SMOKE_PASS + 遥测模型落盘 + 双审；文档在场 ≠ 执行）。
- D0：五条件合取全满足（条件 4/5 重绑 R5 Fable signer v2 回执），`d0_approved=true` 由 checker 复算。
- run_id 平台不暴露（UNAVAILABLE 三元组）；journal 哈希链 12 记录 + LAUNCH 交叉绑定机制在位。
- R3/R4 全部工件封存（git 历史 + SUPERSESSION_LEDGER §5 + 在盘史料），零改写。

## 5. 300/120/86 口径（对发起人）

- **300**：未达成、未受损（V1.1 诚实 NOT_QUALIFIED；B 轨 S2–S7 属 M6）；
- **120**：保持（frozen_inputs 锚 + checker freeze_integrity PASS）；
- **86**：保持（EXTRA_PROTECTED 摘要锚 PASS）。

## 6. 附件索引

八件套（v2 解析集）+ MILESTONE_EXIT_EVIDENCE + READY_SET_RESULT.v2 + R4/R5 审查报告与 Codex 事件流 ×2 + signer v2 回执 ×2 + snapshots/{r4,r5,r5_close} + REVIEW_REQUEST.{v2,v3} + 电池回执 v4/v5 + 残留报告 v2 + ORIGIN_ANCHOR.v2（锚提交内，本提交之子）+ M2 冻结渲染 Prompt v2（锚提交内）。
