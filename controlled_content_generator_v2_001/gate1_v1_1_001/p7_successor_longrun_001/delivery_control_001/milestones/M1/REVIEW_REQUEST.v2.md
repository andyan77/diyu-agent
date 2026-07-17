# M1 独立审核请求 v2（R4 · 发起人八项加固指令回合）

## 0. 审核回路语境

- R3 已双 ACCEPT 的候选 `11b71e9`（关闭 `5cf3ea2`、锚 `4ddbd1f`）之后，发起人于 2026-07-16 下达**八项加固指令**并要求：新候选产生后，Claude/Fable 与 Codex **两份审核全部重跑**，重新生成 PASS、HANDOFF、P2 Prompt 与 origin anchor。
- 依 P1 §二十二回路纪律：**R3 两份审核与其签字回执随新候选自动作废**（封存于 git 历史，工作树留存仅作历史证据）。本请求开启 R4。
- 本轮审核会话要求（指令第 7 条）：**全新非 fork/非 resume 顶层会话 + 自动记忆在启动前即关闭**（`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 于 spawn 前注入）；签字回执按 **signer v2** schema，隔离声明含 `auto_memory_disabled_before_launch=true`。

## 1. 候选与绑定摘要

| 项 | 值 |
|---|---|
| 候选提交 candidate | `ccf27017c973a5359b2f7d0accfbb78851e43b32`（M1-C7） |
| 输入基线 | `23f5fea`（v2.5 冻结；须验证其为候选严格祖先） |
| INPUT_MANIFEST.v2 digest | `26f65629be3e6a6d4900049312e447bc1e7e9b6b8f0377c209db2bf95f93c117` |
| OUTPUT_MANIFEST.v2 digest（157 条） | `01cc3bae432e6dfea14c38f0d7c6c12200c37caac9169762bf7f3e6cad4f2f22` |
| EVIDENCE_MANIFEST.v2 digest（15 条） | `cdcb8178f498fbcf26aefec5d6f09b39d8facb1ef27b95048b5d0a72ef813178` |
| 电池回执 v4（候选头实跑 16 检查） | sha256 `e871679ea67f5596938926e591aa4e307e55a96549d24add67d3857d220c48f6` |
| 活跃合同集合摘要（R4 重冻结，17 成员） | `d7265a1852e4b44db1fae134f5d03e404629470ee7438c36d08b1cc00d85a7e4` |

送审面形态：与 R3 相同——manifests v2 / snapshots/r4 / 本请求 / 电池回执 v4 / 残留报告 v2 为**工作树未跟踪或新增文件**，关闭工件（typed 回执 v2、HANDOFF v2、出口证据、ready-set v2、签字回执）在两份审核 ACCEPT 之后落盘并于关闭提交入库。R3 关闭工件（v1 名）仍在盘：**已被 SUPERSESSION_LEDGER §5 声明取代**，版本解析 v2 优先。

## 2. 八项指令 → 实现映射（审核必须逐项对抗验证）

| # | 指令 | 实现 | 攻击面自证 |
|---|---|---|---|
| 1 | HANDOFF 全部跨文件、跨提交引用复算 | `handoff.v2.schema.json`（每摘要字段有唯一复算对象）+ `tools/closure.py::validate_handoff_full`（manifest 三摘要/出口证据/合同集/签字逐份/模板摘要/ready-set/候选祖先关系） | closure selftest：stale template / ready-set drift / exit-evidence drift 全拒 |
| 2 | candidate/closeout/origin-anchor 可重建闭包 | 提交不能自指 → 闭包规则=「锚提交第一父 == 锚内 closeout_commit」；`origin_anchor.v2.schema.json` + `closure.py::verify_closure` 从分支头零外部知识重建 anchor→closeout→candidate 全链 | closure selftest：detached anchor / tampered artifact digest 拒 |
| 3 | signer schema 绑定 milestone、产品域、三 manifest | `signer_receipt.v2.schema.json`（必填 milestone_id/product_scope/output+evidence manifest digest；隔离声明加 auto_memory_disabled_before_launch）；FINAL 只认 v2 | 攻击 32–35（v1 拒/移植拒/产品域拒/摘要失配拒） |
| 4 | FINAL 强制比较两份 typed 回执及里程碑专属出口 | `receipts.py::compare_typed_pair`（8 字段+旗标+绑定集合）；`MILESTONE_EXIT_CONTRACT.v1.json`（M1/M2 冻结，M3–M7 未冻结 FINAL fail-closed）+ `MILESTONE_EXIT_EVIDENCE` 逐键证据 | 攻击 31/36/37/40 |
| 5 | M2 FINAL 机械证明真实 S0 + 六项出口 | 出口合同 M2 行：S0 六项**镜像自 stage_and_kill.v2**（漂移=FAIL）+ BOUNDARY_SMOKE_PASS + 遥测模型落盘 + 双审；stage_actual_state 登记 + 摘要钉死阶段回执 + real_run_executed=true | 攻击 38/39 + 正向 test_m2_real_s0_proof_green |
| 6 | 启动记录 spawn 前原子落盘 + 绑实际 HEAD | `launch_record.v2.schema.json`（launched_at_head/record_written_before_spawn/ATOMIC_WRITE_TMP_FSYNC_RENAME）+ `launch_outcome.v1.schema.json`（回绑 record_digest）；launcher 记录先写后 spawn | launcher selftest：record_written_before_spawn（spawn 时点断言）/ forged head 拒 |
| 7 | 审核会话启动前关自动记忆 | 本轮两审核会话按此启动；signer v2 隔离声明新必填键 | schema 必填（缺=未签） |
| 8 | 双审核全部重跑 + PASS/HANDOFF/P2/anchor 重生成 | 本请求即 R4；关闭工件全部 v2 重生成；D0 条件 4/5 已重置待本轮 Fable 回执 | SUPERSESSION_LEDGER §5 |

## 3. 审核职责（两名审核者共同）

1. `git rev-parse HEAD` == 候选；`23f5fea` 为严格祖先；`git status` 中被跟踪文件零改动。
2. 三 manifest 逐条 sha256 复算 + manifest_digest canonical 复算 == 上表。
3. 全套电池独立重跑（三套测试 49+49+67、9 工具自测、master --selftest、PRE_REVIEW 三域、contract_set verify、残留扫描、区间空白豁免纪律 8/0）。
4. 对新机制做**对抗探针**（不少于：闭包锚分离、出口键移除/证据篡改、签字移植、launch 顺序/HEAD 伪造、M2 无真实 S0 关闭、S0 镜像漂移）。
5. 历史完整性：v2.3/v2.4/v1.x 与 R3 已提交工件零改写；候选区间只新增/修改加固面。
6. D0：五条件复算——当前 `d0_approved=false` 且条件 4/5 诚实待 R4 重签，须验证一致性；**Fable 审核者**另须审查 D0 章程全文并给出 `d0_verdict`。
7. 保留面复核：DeepSeek 30 元/UTC 日窄门、24 字段成本事件、M0/V11 双诚实 NOT_QUALIFIED、v4_recovery 全绿。

## 4. 签字（signer v2；缺任一必填字段 = 未签）

最终报告必须包含（供内容寻址签字回执逐字转录）：`verdict`、`actual_model_self_report`、`milestone_id=M1`、`product_scope=SHARED`、`input_commit=候选`、三 manifest digest、隔离声明五键（含 `auto_memory_disabled_before_launch`）、发现清单（severity 分级）；Fable 侧另附 `d0_verdict`。审核期间对仓库**零写入**；一切实验写入系统临时目录。

回路纪律：若任何 BLOCKING 发现成立 → 本候选作废 → 修复 → 新候选 → **两份审核全部重跑**。
