# P3 / M3 · 数据供给与逻辑解耦（启动模板）

执行主体：Claude Code 中的 Fable 5（全新顶层会话）
当前里程碑：M3　当前 Prompt：P3
输入提交：`5ce595de7eb48fcf04178651f84400b0411134be`　控制面提交：`002db4559c4f9f1881525a4dda32d94a1062c3c8`
前序：M2 结果 PASS（回执摘要 `5eaec1a640eac747e3dfe970a23f7f87f06b4df7b0c711725444fcdd9fe992fa`）
HANDOFF 摘要：`21ca688ed1de476ad5952c1c6fb61d217885f2cdf41450bea82802cc009f57d6`　活跃合同集摘要：`d7265a1852e4b44db1fae134f5d03e404629470ee7438c36d08b1cc00d85a7e4`
B 评测路线：UNFROZEN
会话要求：全新、非 fork、非 resume 的 Fable 5 顶层会话；由会话外监督器启动；CLAUDE_CODE_DISABLE_AUTO_MEMORY=1；关闭即退出，同会话跨里程碑续跑=停

共同纪律：逐字执行 `delivery_control_001/FORMAL_MODEL_RUN_CONTRACT.v1.md`。

## 目标

覆盖 E1-S/D/Q（v2.4 §三 3.2 M3 行，6 胶囊）：①供需审计 ②标注协议+小试 ③G1 ④G2 ⑤**QUAL-A/B 同框抽样+双冻结+保全** ⑥core 逻辑抽取+接口冻结（产出 `LOGICAL_CORE_SEPARATED`，与①–⑤并行）。

## 资格材料唯一顺序（硬门，QUAL_ORDER_CONTRACT.v1.json）

QUAL-A 与 QUAL-B 各自完成 **①题面冻结 → ②双盲建标 → ③金标冻结**，每步出回执；
两集互不相交、共同抽样框、分层随机、难度平衡；**都在任何方法结果和首次揭晓之前冻结**；
QUAL-B 冻结后从未揭晓、从未回传作者。任何步序颠倒或补录 → `STOP_QUALIFICATION_ORDER_VIOLATION`。

## 密封纪律（v2.5 §三 3.7′）

密封载荷明文不进作者可读 Git 历史；保全角色只见数量/摘要/回执；接触明文的会话一律全新非 fork + 自动记忆禁用 + 结束登记；目录/工作树级物理隔离（禁提示词软约束）。

## 逻辑解耦（D0 §②③④ 生效边界内）

core 接口可不读领域私有目录启动；测试语料经适配器挂载；审计事件不依赖 GATE1 私有路径；
core 暂存只见接口、schema、非密封开发样例；全部领域数据（G1/G2、QUAL-A/B、round、编造样本、领域事实账本、隐藏材料）留源仓。

## 写面

allowlist：
- `controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/**`
- `controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/**`

denylist：
- 顶层产品 core 暂存（product_core_staging_001/** 直至 M3 依 D0 解锁）
- 历史 P1–P6、R1–R5 证据；p5_p6_300_baseline_scale_and_freeze_001/**
- 旧 120 原文、86 历史候选、路线 60 黄金答案、组件基座
- 真实 QUAL、隐藏材料、客户数据目录（按里程碑合同揭示的除外）
- 其他 worktree、主分支、全局检查器、.github/workflows/**
- .env*、密钥、凭据、生产配置、外部服务

## 正常出口

v2.3 各步出口 + QUAL 双冻结保全回执（六步前三步 ×2 集）+ `LOGICAL_CORE_SEPARATED` 旗标（写入 PASS 回执 qualification_flags）+ 供需表/向量容量表 + 八件套 + HANDOFF。容量缺口 = 合法停止（技术门）。

## 里程碑专属停止线

- 密封明文入 Git 历史 / 泄漏给禁止角色 = 停（STOP_DATA_LEAKAGE）；
- QUAL 顺序破坏 = 停（STOP_QUALIFICATION_ORDER_VIOLATION）；
- 在 M3 会话内运行 M0 资格（属 M4）= 停。

M3 关闭后立即退出会话。
