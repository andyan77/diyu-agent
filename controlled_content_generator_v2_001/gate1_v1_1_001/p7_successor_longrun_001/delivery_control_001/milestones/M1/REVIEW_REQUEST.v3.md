# M1 独立审核请求 v3（R5 · R4 审核回路修复后重跑）

## 0. 审核回路语境（含 R4 史）

- 发起人 2026-07-16 八项加固指令 → C7 实现（候选 `ccf27017`，R4 送审）。
- **R4 结果**：Fable ACCEPT（d0 ACCEPT；claude-fable-5 全新无记忆顶层会话）/ **Codex REJECT**（2 BLOCKING）→ 依 P1 §二十二候选作废、两审失效（史料：`FABLE_R4_REVIEW.v1.json`、`CODEX_R4_REVIEW.v1.json`、`codex_review_r4_events.jsonl`）。
  - **BLOCKING#1（真缺陷，Fable 亦独立命中为 ADVISORY）**：`launched_at_head` 伪造 + 重算 `record_digest` 可通过校验（自证摘要不能证明外部绑定）。
  - **BLOCKING#2（环境因）**：Codex read-only 沙箱无可写 /tmp → 电池无法独立复跑。本轮 Codex 改 workspace-write 沙箱（见 §4）。
- **C8 修复（本轮候选 `de83d92cac695cd3e8c603e8817e875f3d567bfa`）**：
  1. `launched_at_head` 三重锚：①启动现场 `expected_head` 逐字比对；②仓库态复核（提交存在、位于分支历史、`input_commit` 为其祖先）；③**spawn 前把 `record_digest` 交叉登记进哈希链 RUN_JOURNAL**（`git_head` 由 journal 独立采集）——伪造成任何真实提交也会被 `launcher.verify_launch_binding` 的链内 `git_head` 失配拒绝。攻击矩阵新增 #41（重放 Codex 攻击：假提交→仓库态拒；真提交伪造→链绑定拒）。
  2. `spine.manifest` 枚举排除 `.pytest_cache`/`.ruff_cache`/`.mypy_cache`（Fable R4 ADVISORY：审核者用 pytest 复跑会污染 A 域候选清单）。
- R3 及更早语境见 `REVIEW_REQUEST.v2.md` §0–§2（八项指令→实现映射不变，指令 6 实现升级为三重锚）。

## 1. 候选与绑定摘要（R5）

| 项 | 值 |
|---|---|
| 候选提交 candidate | `de83d92cac695cd3e8c603e8817e875f3d567bfa`（M1-C8） |
| 输入基线 | `23f5fea`（须为候选严格祖先） |
| INPUT_MANIFEST.v2 digest（9 条） | `ad112305ad295ce166e5d3e6f4a62aab3d9937c9c2b4766fc4be8efedfa3c791` |
| OUTPUT_MANIFEST.v2 digest（157 条） | `283c1fce90af37a5dacad0cf4855b3a7f80cb88b868934265742b238aca11ed2` |
| EVIDENCE_MANIFEST.v2 digest（16 条） | `d10b9f5ddd57fdfd2df51017ad7d77edc5ed514adaecbfab2478186ac74d402c` |
| 电池回执 v5（候选头实跑 16 检查） | sha256 `a6376e93fe90b1e696cd803f19718c3d5e9ad701b21a7faad480ce910670e861` |
| 活跃合同集合摘要（17 成员） | `d7265a1852e4b44db1fae134f5d03e404629470ee7438c36d08b1cc00d85a7e4` |

活体文件快照本轮位于 `snapshots/r5/`（r4/ 为 R4 史料）。电池构成精确表述：三套测试（49+49+68）+ **master --selftest + 8 个工具自测**（ready_set/launcher/closure/qual_order/lift_chain/sealed_scan/run_journal/contract_set）+ PRE_REVIEW 三域 + contract_set verify + 残留扫描 + 区间空白豁免纪律（8 豁免/0 违规）。

## 2. 审核职责

同 `REVIEW_REQUEST.v2.md` §3 全部条目（对本轮候选与本轮摘要执行），另加：
8. **R4 BLOCKING#1 修复的对抗验证**：重放"伪造 `launched_at_head` + 重算 `record_digest`"攻击——假提交必须被仓库态复核拒；真实其他提交必须被 journal 交叉绑定拒（`launcher.verify_launch_binding`）；并证明 LAUNCH_RECORD 于 spawn 前已在盘（spy spawn 时点断言，launcher selftest 已内置可复跑）。
9. 核验 R4 史料完整登记（三份 R4 文件在盘且与本请求叙述一致）。

## 3. 签字（signer v2；缺任一必填字段 = 未签）

同 `REVIEW_REQUEST.v2.md` §4：最终报告含 verdict / actual_model_self_report / milestone_id=M1 / product_scope=SHARED / input_commit=本轮候选 / 本轮三 manifest digest / 隔离声明五键（含 `auto_memory_disabled_before_launch`）/ findings；Fable 另附 `d0_verdict`。

## 4. 会话与沙箱要求

- 两审核会话：全新非 fork/非 resume + 自动记忆启动前禁用。
- Codex 本轮以 workspace-write 沙箱运行（修 R4 BLOCKING#2 环境因）——**对仓库零写入仍为硬纪律**：一切实验只写 /tmp，`PYTHONDONTWRITEBYTECODE=1`，结束前以 `git status --porcelain` 对照开场快照自证零改动并写入隔离声明。
- 回路纪律不变：任何 BLOCKING 成立 → 候选作废 → 修复 → 双审重跑。
