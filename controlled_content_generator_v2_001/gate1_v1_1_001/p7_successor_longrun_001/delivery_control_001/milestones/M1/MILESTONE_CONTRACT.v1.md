# M1 里程碑合同 v1（MILESTONE_CONTRACT）

```yaml
milestone_id: M1
prompt_id: P1
title: v2.5-native 可信地基、磁盘状态机与自主接力机制
workspace: /home/diyu/worktrees/gate1-longrun-001
branch: agent/gate1-v1-1-successor-longrun
input_commit: 23f5fea355ef4904043c98187ba2a82c846772be
preservation_commit: f7d661995165f4d7a6559c40482e296b43781bd2
candidate_commit: 11b71e9bed9078c2483dc27ae94a807689ff5528
launch_record: prompts/P1.M1.prompt.md（发起人直发，sha256 58c63864d7a4471aaeee933a1a479e4e37023802d6b158f3bbca345f32fd68de）
session: f719e24e-7b51-48c0-9c24-9655a6525be8（Fable 5 / claude-fable-5，全新非 fork 顶层会话）
active_contract_set: v2.5@23f5fea（集合摘要 cbe5f5f4e65a7766e328c5c676ecad2958fb4fdaacc9d17d44350a60cd46dee9）
```

## 写面（P1 §八冻结）

allowlist：
- `controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/**`
- `controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/**`

denylist：顶层产品 core 暂存 / 产品仓与新远程 / 真实 QUAL、隐藏材料、客户数据 / 历史 P1–P6、R1–R5 证据 / 旧 120、86、路线 60 / 领域事实正文与组件基座 / 其他 worktree / 主分支 / `.env*` 密钥凭据。

允许 Git 动作：显式路径 add、commit、push 既有 origin 任务分支；禁 tag/force-push/rebase/merge-master/历史重写/新产品 remote。

## 入口

P1 里程碑启动记录（v2.5 §壹-9 执行侧默认授权）；冻结基线 `23f5fea` 现场核实一致；Fable 5 身份回执有效。

## 交付物（胶囊）

C0 现场保全（f7d6619）→ C1 真源/授权/D0/supersession（931d06c）→ C2 三层旧规则迁移（f03b48b）→ C3 控制面/接力/边界（cf5016d）→ C4 候选冻结（3b29055）。

## 出口

P1 §二十四 合取条件全部成立 → typed PASS；任何一项缺失不得写 PASS。
中间态 `IMPLEMENTATION_COMPLETE_REVIEW_READY` 不满足任何下游入口。

## 停止线

P1 §二十五 全集 + v2.5 §七 全集；停止时先写 RUN_JOURNAL / STOP_LEDGER / Git 状态 / 最后绿色提交 / typed 回执。
