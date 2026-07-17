# Supersession 账本 v1（v2.5 生效链）

> 纪律：不篡改历史文件制造一致；一切取代关系在此登记，配合 `SOURCE_LOCK.v1.json` 与
> `ACTIVE_CONTRACT_SET.v1.json` 指针生效。被取代文件原文封存于 git 历史与工作树，仅作历史证据。

## 1. 方案层

| 被取代 | 取代者 | 依据 | 状态 |
|---|---|---|---|
| v2.3（`bbe4d111fb…`）授权语义（逐包 Prompt 启动 / S0 专项授权 / E0a 待启动） | v2.5 §〇/§壹-9 | 发起人 2026-07-16 第九项裁决（宽义默认授权，AskUserQuestion 知情选择） | 生效 |
| v2.4（`4328194ac2…`）P1–P7=授权令牌、D0 待发起人批准、停止线第 4 条"自动续跑=停" | v2.5 §三 3.1′、§四 4.1′、§七改写条 | 同上 | 生效 |
| v2.3 §壹 八项裁决原文、v2.3 §〇 真源优先表、v2.4 技术纪律（7 里程碑/全新会话/入口机械校验/关闭回执/Y 分叉/密封隔离/两层代理/Fable 不自签） | （不被取代——v2.5 显式维持） | v2.5 §壹"技术纪律全部保留" | 继续有效 |

## 2. 上位合同层（C1 vNext 迁移）

| 被取代 | 取代者 | 迁移内容 | 保留红线 |
|---|---|---|---|
| `contract/longrun_execution_contract.v1.1.md` | `contract/longrun_execution_contract.v2.md` | 执行结构从"执行包 1–5"映射为 v2.5 七里程碑；授权模型接 §壹-9 | 写面、绝对保护面、失败纪律、300/120/86 口径、merge/tag/release/部署禁令逐字承继 |
| `contract/execution_authorization.v1.1.yaml` | `contract/execution_authorization.v2.yaml` | 授权状态表按 v2.5 §〇 重写（流水线内仪式默认授权；升级通道唯一） | 写面/禁面/远程边界承继 |
| `eval_audit_spine_001/contract/implementation_authorization_record.v1.md` | `…/implementation_authorization_record.v2.md` | 实施授权挂接 v2.5；预算批准制表述 → 拨付制+记账 | DeepSeek 30 元/日窄授权、密封红线承继 |

## 3. 阶段合同 / 状态层（C2 执行，本账本先行登记方向）

| 被取代 | 取代者 | 关键增删（冻结方向） |
|---|---|---|
| `stage_and_kill.v1.json` | `stage_and_kill.v2.json` | Y 三状态机（S0 主干 / A 轨 S1 / B 轨 S2–S7）；S2 入口删 `S1_PASS`+`FOUNDER_APPROVED_BUDGET_CEILINGS`，增 `S0_PASS`+`FIVE_FAMILY_STRATEGIES_FROZEN`+`INDEPENDENT_REVIEW_ROLES_ASSIGNED`+`B_EVAL_ROUTE_FROZEN`+`NARRATIVE_FACT_REVIEW_CAPABILITY_READY`；S2 出口删 `PROJECTED_300_COST_WITHIN_ALL_APPROVED_CEILINGS`（保留 P50/P95 遥测键）；S3 → 诊断门；S4 入口 `S3_PASS` → `S3_DIAGNOSTIC_COMPLETE ∧ 安全出口全绿`；S6 入口删 `COST_REFORECAST_WITHIN_BUDGET` → 记账完整性；删 `STOP_BUDGET`、`STOP_S2_BUDGET_UNAPPROVED/EXCEEDED`；保留 `STOP_EXTERNAL_LLM_DAILY_BUDGET`、`STOP_DATA_LEAKAGE`、`STOP_FIRST_OUTPUT_LAUNDERING`、`REQUEST_STANDARD_REVISION`；新增记账缺失=停 |
| `cost_budget.v1.json` | `cost_accounting.v2.json` | 审批制 → 拨付制+全量记账+不设阻断门；`current_decision` 旧真相摘除；24 字段成本事件、费率卡复算、fail-closed 记账规则保留 |
| `EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.1.md` | `EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.2.md` | §10"总预算 UNAPPROVED → S2 后全部关闭失败"与 §8 S2 预算出口两处旧规则前瞻修订；其余原文承继 |
| `implementation_charter.v1.md` | `implementation_charter.v2.md` | 同步新合同（消预算阻断与 A→B 依赖表述） |
| `measurement_qualification.v1.json` cost 子门两条 ceiling-stop | C2 修订（同文件 v1 → v1.1 修订或 v2） | `actual_cost_at_or_above_any_hard_ceiling_stops`、`formal_p95_above_any_hard_ceiling_stops` → 记账完整性表述；`daily_external_llm_budget_cny=30.0` 保留 |

## 4. 标准层（沿 v2.3 既有登记，未变）

- V1.1 标准"人类专家复审"默认假设 → 由发起人 2026-07-16 裁决 supersede 为模型角色承担（四硬前提下）；成文见 v2.3 §壹-3。本账本转录登记，不重开。

## 5. 控制面加固层（发起人 2026-07-16 八项加固指令回合）

| 被取代 | 取代者 | 关键增删 | 状态 |
|---|---|---|---|
| `schema/signer_receipt.v1.schema.json` | `schema/signer_receipt.v2.schema.json` | 新增必填 `milestone_id` / `product_scope` / `output_manifest_digest` / `evidence_manifest_digest`；隔离声明新增必填 `auto_memory_disabled_before_launch`；可选 `d0_verdict`。FINAL 只认 v2 签字（v1 = 缺绑定 = 不满足关闭）；v1 schema 保留仅供历史回执分发校验 | 生效 |
| `schema/handoff.v1.schema.json` | `schema/handoff.v2.schema.json` | 删不可复算的 `control_plane_commit`（提交不能自指→改由 ORIGIN_ANCHOR.v2 锚定）；增 `evidence_manifest_digest` / `exit_evidence_digest` / `closure_rule`；每个摘要字段有唯一复算对象（tools/closure.py validate_handoff_full 逐项复算） | 生效 |
| `schema/launch_record.v1.schema.json` | `schema/launch_record.v2.schema.json` + `schema/launch_outcome.v1.schema.json` | 记录/结果分离：记录只承载 spawn 前事实，必须先于 spawn 原子落盘（tmp+fsync+rename）并绑定实际 HEAD（`launched_at_head`）；会话结果落 LAUNCH_OUTCOME 且经 `launch_record_digest` 回绑 | 生效 |
| M1 关闭工件 R3 集（`HANDOFF.v1.json`、R3 `STAGE_DECISION`/`CLOSEOUT_RECEIPT`/`READY_SET_RESULT.v1`/`ORIGIN_ANCHOR.v1.json`、R3 两份签字回执） | R4 重生成集（HANDOFF.v2 / 新 typed 回执 / MILESTONE_EXIT_EVIDENCE.v1 / READY_SET_RESULT.v2 / ORIGIN_ANCHOR.v2 / 新签字回执 ×2） | 指令第 8 条：新候选产生 → 两份审核全部作废重跑 → PASS/HANDOFF/P2 Prompt/origin anchor 全部重生成；R3 工件封存于 git 历史（5cf3ea2/4ddbd1f），工作树留存仅作历史证据、不再满足任何入口（版本解析 v2 优先） | 生效 |
| （新增，无被取代者）`contracts/MILESTONE_EXIT_CONTRACT.v1.json` + `schema/milestone_exit_evidence.v1.schema.json` + `schema/origin_anchor.v2.schema.json` + `tools/closure.py` | — | 里程碑专属出口逐键强制（M1/M2 冻结；M2 = S0 六项镜像 + BOUNDARY_SMOKE_PASS + 遥测模型落盘 + 双审；未冻结里程碑 FINAL fail-closed）；candidate/closeout/anchor 可重建闭包验证器 | 生效 |

## 6. 登记纪律

- 新增取代关系必须：新版本文件落盘 + 本账本行 + ACTIVE_CONTRACT_SET 成员更新，三者同提交。
- 禁止：删除/改写被取代文件原文；在被取代文件内插入"已作废"标注（历史文件零改写）。
- 校验：`tools/contract_set.py verify` 复算活跃成员摘要；checker `active_contract_set` 节消费。
