# 笛语第一门 V1.1 后继质量长程执行合同 v2（v2.5-native）

> 取代关系：本合同 supersede `longrun_execution_contract.v1.1.md` 中与 v2.5 冲突的执行结构与授权语义；
> v1.1 原文封存不改。登记：`delivery_control_001/SUPERSESSION_LEDGER.v1.md` §2。
> 冲突解释顺位：`delivery_control_001/SOURCE_LOCK.v1.json` truth_precedence。

## 0. 身份

```yaml
task_id: GATE1_V11_SUCCESSOR_LONGRUN_001
contract_version: v2
active_plan: AB_DUAL_PRODUCT_DELIVERY_PLAN.v2.5.md @ 23f5fea355ef4904043c98187ba2a82c846772be
executor: Claude Code Fable 5
task_branch: agent/gate1-v1-1-successor-longrun
task_workspace: /home/diyu/worktrees/gate1-longrun-001
source_baseline_commit: b4c40beb509d81db30b497abf38af1da6dc797da
```

## 1. 目标（v2.5 重述）

执行侧唯一目标 = 交付两个彼此独立的产品应用（v2.3 §壹 顶层交付定义，冻结）：

- **产品 A**：可复算评测与审计脊柱应用；
- **产品 B**：符合 V1.1 的内容生成资格应用及其基线资产集（240+60）。

核心口径承继 v1.1 §1 逐字：`300: 240条批准正向内容 + 60条异常处置案例`、`120: 已冻结历史参考内容库存`、
`86: 历史组件候选库存`。M0 与 V1.1 当前均 `NOT_QUALIFIED`（诚实状态，待 M4/M6 资格化）。

## 2. 执行结构（supersede v1.1 §4 执行包 1–5）

七里程碑 M1–M7 + Y 依赖图（v2.4 §三 3.8 + v2.5 §三 3.1′）：

```text
M1 地基硬化 → M2 治理关闭+真实S0 → ┬ M3 数据供给 → M4 首次M0资格化 → M5 产品A交付
                                    └ M6 B资格主门 → M7 产品B交付
```

- 每里程碑 = 一个全新 Fable 5 顶层会话，关闭即退出；**同一会话内跨里程碑续跑 = 停**（v2.5 §七）。
- 里程碑启动 = 执行侧默认授权（v2.5 §壹-9）：前序八件套关闭 + typed 回执合格 + 全新会话 + 入口机械校验通过。
- 跨里程碑状态完全由 Git + manifest + 证据包 + handoff + RUN_JOURNAL 承担，不靠会话记忆。
- 胶囊带宽 23（+2）不变；两层代理封顶；Fable 不签自身工作。

## 3. 写面与保护面（承继 v1.1 §2/§3 全部 + P1 §八 里程碑级收窄）

- 合同级写面：`p7_successor_longrun_001/**` + `generator_v3_successor_001/**`；
- 每个里程碑启动记录冻结该里程碑的收窄写面（M1 见 P1 §八）；
- v1.1 §3 绝对保护面全部承继（P1–P4 历史、p5_p6 证据、全局检查器、workflows、公共基础、旧 120/86/路线 60、组件基座、外部工作区、密钥、生产配置）；
- 未来 core 暂存写面 `product_core_staging_001/**` 仅登记（D0 §②），M3 前不创建。

## 4. 授权与预算（supersede v1.1 预算相关表述）

- 授权模型：`contract/execution_authorization.v2.yaml`；
- 预算：**拨付制 + 成本事件全量记账 + 不设阻断门**（v2.3 §壹-4 / v2.5 §五）；记账缺失 = 停；
- DeepSeek 30 元人民币/UTC 日窄授权与 24 字段成本事件 schema 保留不变；
- Codex-GPT 订阅制只记账（`delivery_control_001/contracts/GPT_CODEX_SCOPE_CONTRACT.v1.md`）。

## 5. 失败纪律（承继 v1.1 §5 逐字 + v2.5 增补）

降低/绕过 V1.1 标准；删除/替换/隐藏失败样本；改黄金答案迎合实现；重抽直到成功；改稿冒充首次输出；
只补成功样本操纵分母；结构测试/异常案例/未批准内容计入 240；擅改 300/120/86；改组件基座或跨入产品化主线；
自评冒充独立审查。**增补（v2.5）**：伪造/混淆/缺失 typed 状态值；凭无效签字过门；REVIEW_READY 冒充 PASS；
把实际状态文件改写为期望值；密封摘要 denylist 撞库命中仍继续。

## 6. 检查与反假绿（承继 v1.1 §6 + P1 §十七）

P7 唯一总检查入口 `checker/p7_master_check.py`（可拆内部模块、禁平行总检查器）；
`--milestone/--product/--mode/--state-file/--selftest`；PRE_REVIEW 只证送审条件，FINAL 需 typed PASS + 有效外部审核；
A/B 分开判断、无全局互相牵连 ALL_PASS；负向攻击测试为门的一部分；hooks 仅加固层。

## 7. 提交、推送与远程边界（承继 v1.1 §7 逐字）

允许推送任务分支；草稿 PR 仅限 stacked（base=agent/gate1-v1-1-300-quality-baseline，标记不得合并）。
禁止合并/关闭/修改 PR14、PR15 及产品化合并请求；禁止合并到主分支、改分支保护、打标签、发布、部署、强推、
重写历史、删除失败提交。产品仓新远程创建仅 M5/M7 依 D0 边界执行。

## 8. 停止与交付（承继 v1.1 §8 + v2.5 §七）

停止线清单以 P1 §二十五为准（本里程碑）与 v2.5 §七（全程）；停止时先写 RUN_JOURNAL、STOP_LEDGER、
当前 Git 状态、最后绿色提交、可复算证据与 `HONEST_STOP`/`FAIL` typed 回执。
对发起人的阶段摘要仍先报告 300/120/86 是否达成、改变或受损。
