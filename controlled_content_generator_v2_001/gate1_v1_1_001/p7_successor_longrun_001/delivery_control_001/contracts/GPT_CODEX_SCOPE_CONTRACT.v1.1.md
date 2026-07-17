# GPT-via-Codex Scope + 回执合同 v1.1（增补层）

> 性质：对 v1 的**增补层**（v1 原文与 ACS 冻结成员逐字不动，本文件只增不改——M2 signer v2.1 先例）。
> 授权源：发起人 2026-07-17 会话内 AskUserQuestion 两连裁决（『改用 Codex-GPT 标注（需重开合同）』+
> 『双模型分席 GPT+Fable』）；登记：journal seq38 launch_ruling_facts + SUPERSESSION_LEDGER §7。
> 未在本文件出现的条款一律沿 v1 逐字生效。

## 1′. 新增角色

| 角色 | 代号 | 说明 |
|---|---|---|
| 金标标注席位 A | GOLD_LABELING_SEAT_A | 双盲金标建标的 A 席（与 Fable B 席跨模型交叉）：独立标注 / 独立复核；每叫全新 ephemeral 线程 |

## 2′. 允许用途增补

5. **金标双盲标注与独立复核（席位 A）**：对 G1/G2 开发金标与 QUAL 资格金标的题面进行独立标注/复核；
   与 Fable 席位 B 构成跨模型双盲；分歧由裁决席终裁（G1/G2 裁决席=Fable，逐处披露其与 B 席同模型）。

## 3′. 禁止用途第 3 条的里程碑例外（v1 预留通道的行使）

v1 §3-3「读取密封载荷明文——除非当时里程碑合同显式将其列为该角色可见材料」：
M3 里程碑合同（milestones/M3/MILESTONE_CONTRACT.v1.md 密封承载设计段修订版）**显式授予
GOLD_LABELING_SEAT_A 对 QUAL-A/B 题面（不含另一席位标签、不含金标终值）的标注期可见**；
承载纪律：全新 ephemeral 线程 + 仓外中性目录 + read-only 沙箱 + 题面经确定性工具进程内送入 +
逐叫登记（thread_id、可见材料清单、留存方式）；线程不持久化（--ephemeral）即销毁。

## 5′. 签字方与标注席位的关系（利益冲突处置）

- EXTERNAL_REVIEW_SIGNER 出具 M3 关闭签字时**必须披露** GOLD_LABELING_SEAT_A 的参与范围
  （席位 A 标签均经 Fable B 席跨模型独立复核、分歧经裁决席终裁；签字自审面=其单侧标签）；
- v1 §3-5（作者同 scope 实现后不得签字）不因本增补放宽：席位 A 仅产出标注决定，
  不承担实现/编排/manifest 工作；
- Fable 对抗审查（另一份独立审核）对全部金标（含席位 A 标签）负全量复核责任。

## 4′. 记账增补

- 席位 A 调用沿 v1 §4 订阅制只记账不设门；逐叫登记：thread_id、用途、批 id、可见材料清单、
  输入/输出 token 用量（事件流 turn.completed.usage 实测）、退出状态；
- 模型名以调用事件流实测为准（当前配置 gpt-5.6-sol）；**禁止杜撰模型修订号或线程 ID**（沿 v1）。
