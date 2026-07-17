# P2 / M2 · 治理关闭 + 真实 S0 + 遥测（启动模板）

<!-- 渲染绑定（由 tools/renderer.py 在真正启动时填充；模板本体不含启动记录/回执/签字 -->
执行主体：Claude Code 中的 Fable 5（全新顶层会话）
当前里程碑：M2　当前 Prompt：P2
输入提交：`de83d92cac695cd3e8c603e8817e875f3d567bfa`　控制面提交：`caa489f9cd6616d7a2066caea1cd21e11e50939f`
前序：M1 结果 PASS（回执摘要 `ecff2dcfc87cedfe335a74073093d6027e9dd971e8835abace7bd13816419d15`）
HANDOFF 摘要：`e3a72ffd778aadd672f09212e9ea907649386df6b749a8b33f1490e0f662840f`　活跃合同集摘要：`d7265a1852e4b44db1fae134f5d03e404629470ee7438c36d08b1cc00d85a7e4`
B 评测路线：UNFROZEN
会话要求：全新、非 fork、非 resume 的 Fable 5 顶层会话；由会话外监督器启动；CLAUDE_CODE_DISABLE_AUTO_MEMORY=1；关闭即退出，同会话跨里程碑续跑=停

共同纪律：逐字执行 `delivery_control_001/FORMAL_MODEL_RUN_CONTRACT.v1.md`（会话身份/journal/写面/签字/密封/关闭/停止线）。

## 目标

覆盖 E0b+E0c（v2.4 §三 3.2 M2 行）：治理预检 → **真实 S0 运行**（执行流水线内默认授权，v2.5 §〇）→ 冻结与两份独立审核 → 调用量/令牌/墙钟/吞吐遥测落盘 → `BOUNDARY_SMOKE_PASS`。

## 胶囊

1. **M2-C1**：治理预检 → S0 真实运行（S0 六项出口冻结原样：单一分配真源 100%、分配-材料错配零、全批硬否决指标在位、首个响应不可变保全、调用与成本溯源完整、GATE1 计划冒充计数零）→ 两份独立审核。
2. **M2-C2**：遥测模型（E0c：只要求完整、可复算，不作阻断门）+ `BOUNDARY_SMOKE_PASS`（里程碑级出口键，不进冻结 S0 六键）。

## 写面

allowlist：
- `controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/**`
- `controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/**`

denylist（除 FORMAL_MODEL_RUN_CONTRACT §3/§5 外特别强调）：
- 顶层产品 core 暂存（product_core_staging_001/** 直至 M3 依 D0 解锁）
- 历史 P1–P6、R1–R5 证据；p5_p6_300_baseline_scale_and_freeze_001/**
- 旧 120 原文、86 历史候选、路线 60 黄金答案、组件基座
- 真实 QUAL、隐藏材料、客户数据目录（按里程碑合同揭示的除外）
- 其他 worktree、主分支、全局检查器、.github/workflows/**
- .env*、密钥、凭据、生产配置、外部服务

## 入口机械校验（launcher 已验，会话内复核）

- M1 关闭八件套 + typed PASS + 两份有效审核；`checker --milestone M2 --mode PRE_REVIEW` 基线绿；
- 实际状态满足 STATE_EXPECTATION[M2] 入口面（M0/V1.1 双 NOT_QUALIFIED、零阶段已执行）。

## 正常出口（全部满足才可写 PASS）

- S0 六项逐项通过 + 摘要闭合 + `stage_actual_state` 登记 S0 与回执；
- 成本事件全量记账且 `accounting_integrity_gate` PASS；遥测模型落盘；
- `BOUNDARY_SMOKE_PASS`；两份独立审核绑定同一候选；八件套 + HANDOFF（含 ready-set 结果：路线 (a) 时 M3/M6 应同时 ready）。

## 里程碑专属停止线

- S0 真实运行触及任何密封/隐藏材料 = 停；
- 遥测数据被用作阻断门（预算门复辟）= 停；
- S0 失败按 `STOP_S0_DETERMINISTIC_INTEGRITY` 诚实关闭（FAIL/HONEST_STOP），不得重试洗绿。

M2 关闭后立即退出会话；M3/M6 只能由会话外监督器另启。
