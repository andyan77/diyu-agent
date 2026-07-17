# M2 里程碑合同 v1（MILESTONE_CONTRACT）

```yaml
milestone_id: M2
prompt_id: P2
title: 治理关闭 + 真实 S0 + 遥测（E0b+E0c）
workspace: /home/diyu/worktrees/gate1-longrun-001
branch: agent/gate1-v1-1-successor-longrun
input_commit: de83d92cac695cd3e8c603e8817e875f3d567bfa
control_plane_commit: f7250acda663ef007d46ce8f1ee26208659ae86e
launch: MANUAL_FOUNDER_LAUNCH（发起人裁决，journal seq18 + SUPERSESSION_LEDGER §7；冻结 Prompt digest 6a8acac7 逐字核验）
session: 4d7e088b-945e-4903-844a-790379e740d2（Fable 5 / claude-fable-5，全新非 fork 顶层会话）
active_contract_set: v2.5@23f5fea（集合摘要 d7265a1852e4b44db1fae134f5d03e404629470ee7438c36d08b1cc00d85a7e4）
```

## 写面（RENDERED_PROMPT.v2 冻结）

allowlist：
- `controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/**`
- `controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/**`

denylist：顶层产品 core 暂存（product_core_staging_001/** 直至 M3 依 D0 解锁）/ 历史 P1–P6、R1–R5 证据；p5_p6_300_baseline_scale_and_freeze_001/** / 旧 120 原文、86 历史候选、路线 60 黄金答案、组件基座 / 真实 QUAL、隐藏材料、客户数据目录 / 其他 worktree、主分支、全局检查器、.github/workflows/** / .env*、密钥、凭据、生产配置、外部服务。

允许 Git 动作：显式路径 add、commit、push 既有 origin 任务分支；禁 tag/force-push/rebase/merge-master/历史重写/新产品 remote。

## 入口

M1 CLOSED_PASS（八件套 + typed PASS + 双签）；checker M2 PRE_REVIEW 三域绿；STATE_EXPECTATION[M2] 入口面（M0/V1.1 双 NOT_QUALIFIED、零阶段执行）；启动形态例外经发起人裁决登记（launch_ruling_facts）。

## 交付物（胶囊）

- 开场与裁决登记（37b7dd1）→ launcher 递延加固（fe9bfd2）→ C1a 治理预检 + S0 专项授权（baaedcf）
- C1b 真实 S0：输入冻结与预登记（2c56d39）→ 首次尝试先提交（1c4f815）→ 门/评审/度量/DeepSeek×3/记账/阶段门 PASS（4fcb568）
- C2 遥测模型 + BOUNDARY_SMOKE_PASS（67eeb71）→ 候选冻结（本提交）

## 出口（MILESTONE_EXIT_CONTRACT M2 行，FROZEN）

S0 六键镜像逐项 + BOUNDARY_SMOKE_PASS + COST_THROUGHPUT_TELEMETRY_MODEL_ON_DISK + 两份独立审核 ACCEPT；stage_actual_state 登记 S0 + 摘要钉死阶段回执 + real_run_executed=true；checker FINAL 通过后方可写 PASS。

## 里程碑专属停止线

S0 触及密封/隐藏材料 = 停；遥测用作阻断门 = 停；S0 失败按 STOP_S0_DETERMINISTIC_INTEGRITY 诚实关闭，不得重试洗绿。
