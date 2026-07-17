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
| `schema/launch_outcome.v1.schema.json`（原地增补，非取代）+ `tools/launcher.py` / `tools/receipts.py` | — | 发起人递延指令落地（journal seq17 → M2 开场）：①spawn cwd 显式钉工作区根；②会话非零退出诚实登记——launch_capability 枚举增 `AUTO_LAUNCHED_SESSION_EXIT_NONZERO`（须 TOP_LEVEL_FRESH + 非零 exit_status，伪装 exit 0 被 schema 拒），launcher --start 对该态以非零码收尾且不落 READY_TO_START、不自动重试 | 生效（M2 开场，commit 见 journal seq19 后首个绿色提交） |

## 6. 登记纪律

- 新增取代关系必须：新版本文件落盘 + 本账本行 + ACTIVE_CONTRACT_SET 成员更新，三者同提交。
- 禁止：删除/改写被取代文件原文；在被取代文件内插入"已作废"标注（历史文件零改写）。
- 校验：`tools/contract_set.py verify` 复算活跃成员摘要；checker `active_contract_set` 节消费。

## 7. 启动协议例外层（发起人裁决，单次有效）

| 被例外条款 | 例外内容 | 依据 | 范围与状态 |
|---|---|---|---|
| `FORMAL_MODEL_RUN_CONTRACT.v1.md` §1「启动只能由会话外监督器（tools/launcher.py）完成」+ launch_record.v2 先于 spawn 落盘 | M2 会话由发起人手动开启（全新 Fable 5 顶层会话 + 冻结 Prompt 逐字投放，digest 6a8acac7 与 READY_TO_START.v2 一致）；launcher --start 未运行，LAUNCH_RECORD.v2 缺位不补录（schema 常量使诚实补录不可能，伪造=假绿）；入口机械校验在会话内只读复算全部通过 | 发起人 2026-07-17 会话内 AskUserQuestion 三选一裁决『裁决登记后本会话继续』；journal seq 18 launch_ruling_facts；evidence/SESSION_IDENTITY.M2.v1.json launch_provenance | **仅限 M2 本次启动**；不修改合同文本、不降低 M3+ 要求；M3+ 仍须 launcher 启动（launcher 递延加固于 M2 完成）；生效 |
| `FORMAL_MODEL_RUN_CONTRACT.v1.md` §5「`.env*`/密钥零读取」（对 M2-S0 真实外部调用的密钥唯一来源） | S0 真实运行需 DeepSeek 套路评审调用（记账门要求完整 MODEL_CALL 回执）；`DEEPSEEK_API_KEY` 唯一存在于 `.env.deepseek`。发起人显式授权：**仅限本次 M2-S0**，由 sanctioned 脚本 `eval_audit_spine_001/scripts/run_deepseek_formulaic_judge.py`（`load_env_value`）在进程内读取该文件取密钥；密钥值不回显、不入日志、不入 Git、不入任何产物；主会话与子代理不得直接读 `.env*`；调用绑定 `external_llm_budget.v1.json`（FORMULAIC_SEMANTIC_JUDGE_DEVELOPMENT，30 元/UTC 日，预占-结算-失败留回执） | 发起人 2026-07-17 会话内 AskUserQuestion 裁决（同全局纪律「指令内部矛盾必先停先问」：授权注入方式选项 (a)）；journal seq 20 founder_rulings_this_capsule | **仅限 M2-S0 本次运行**；不修改合同文本；后续里程碑外部调用密钥注入须另行裁决或改为环境预注入；生效 |
| §5 表「FINAL 只认 v2 签字」条款（`schema/signer_receipt.v2.schema.json` 隔离声明 `auto_memory_disabled_before_launch` 常量 true） | 本环境下正式 Fable 审查者的两条无注入载体路径均被机械堵死（子代理：harness 向其上下文注入用户级 CLAUDE.md + 项目记忆索引，不可关闭；嵌套 headless 顶层会话：沙箱内 Bash 不可用致其诚实拒判，豁免沙箱被权限分类器拒绝）。发起人裁决采用子代理载体签字并豁免该常量：落地为 **`schema/signer_receipt.v2.1.schema.json`**——`before_launch` 改布尔，**为 false 时强制携带 `auto_memory_injection_disclosure`**（注入内容/来源/与被审对象关系/是否采用），其余必填与四键常量逐字承继 v2；`tools/receipts.py` 与 checker 版本分发同步注册，FINAL 接受 {v2, v2.1}；v1 仍拒 | 发起人 2026-07-17 会话内 AskUserQuestion 三选一裁决（风险「降低验收严格度、Codex 可能打回」已呈现，知情选择）；journal seq 25 founder_rulings_this_capsule | 诚实分层豁免（非删除字段）；v2 原文与 ACS 冻结成员不动；M3+ 若载体环境恢复无注入路径应回用 v2 全真声明；生效 |
| `FORMAL_MODEL_RUN_CONTRACT.v1.md` §1「启动只能由会话外监督器（tools/launcher.py）完成」+ 本节首行 M2 裁决「M3+ 仍须 launcher 启动」范围限定 | M3 会话由发起人手动开启（第二次 MANUAL_FOUNDER_LAUNCH：全新 Fable 5 顶层会话 + P3 渲染文本逐字投放，会话内转写 sha256 ae16ac3f == launcher --render M3 rendered_digest 逐字节一致）；launcher --start 未运行，LAUNCH_RECORD.v2 缺位不补录（schema 常量使诚实补录不可能，伪造=假绿）；入口机械校验在会话内只读复算全部通过（journal VALID 29 条 / M2 八件套 8/8 / typed PASS 双独立签字 / ready_set M3=READY / checker M3 PRE_REVIEW SHARED10/A5/B6+ARTIFACT_INTEGRITY PASS） | 执行侧在任何 M3 业务动作前 STOP + AskUserQuestion 三选一（关会话 launcher 重启[推荐] / 豁免继续 / 中止排查）；发起人 2026-07-17 裁决『豁免 M3 本次，本会话继续』（知情推翻本节首行「仅限 M2」范围限定；连续豁免弱化硬门 + Codex 或打回 + M3 密封里程碑主会话记忆未禁用之风险已呈现）；journal seq 30 launch_ruling_facts；evidence/SESSION_IDENTITY.M3.v1.json launch_provenance | **仅限 M3 本次启动**；不修改合同文本、不降低 M4+ 要求；M4+ 仍须 launcher 启动；附带承诺：主会话零接触 QUAL/密封载荷明文（明文只经 SEALED_CUSTODY_PROTOCOL 隔离会话处理）；生效 |

## 8. 里程碑出口定义冻结层（合同内预定动作，非例外）

| 动作 | 内容 | 依据 | 状态 |
|---|---|---|---|
| MILESTONE_EXIT_CONTRACT M3 行冻结（TO_BE_FROZEN_AT_MILESTONE_START → FROZEN 2026-07-17） | v2.4 §六 M3 行具体化为 23 个 required_exit_keys（E1-S 4 键 / E1-D 5 键 / E1-Q 11 键 / LOGICAL_CORE_SEPARATED / 双独立审核 2 键）；stage_execution_required=[]；real_run_required=false；容量缺口=合法 HONEST_STOP（required_exit_keys 仅约束 PASS）。成员摘要变更 → ACS 重冻结：集合摘要 d7265a1852e4b44db1fae134f5d03e404629470ee7438c36d08b1cc00d85a7e4 → 516fe73bd37a82fc58973c517131da4e53262eec564287c9ea6cff731e30ae8f（17 成员 0 pending，contract_set freeze+verify PASS）；D0_STATUS.active_contract_set_digest 同步 | 出口合同自身条款「冻结动作属 M3 启动会话职责，须经两份独立审核」（M3 关闭双审核绑定候选复核本冻结）；journal seq31 胶囊 M3_C0_CONTRACT_AND_EXIT_FREEZE | 生效（待 M3 关闭双审核复核） |
