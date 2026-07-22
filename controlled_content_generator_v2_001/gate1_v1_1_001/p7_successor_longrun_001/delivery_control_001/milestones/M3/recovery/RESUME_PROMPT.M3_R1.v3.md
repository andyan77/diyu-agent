# M3-R1 恢复续跑 Prompt v3（canonical 磁盘入口）
# session5 检查点 · Opus 4.8 主执行 · R3-run 全量 → R4 → R5 → R6

---
## ⟪最新磁盘态（session5，先读本块）⟫

- **权威 Prompt**：顶层《M3R3–M3R6 恢复续跑 Prompt · Opus 4.8 完整替换版》为里程碑权威；本 v3 是其**磁盘续跑指针**，与之冲突以顶层 Prompt 为准。取代 v1/v2.md。
- **当前 HEAD**：session5 检查点提交（含 587c9df R3-build 剩余 + 本 pilot/检查点提交）。以实际 HEAD 为准（含声明基线 8d93441 为祖先）。禁止 reset/rebase 回 8d93441/b3f5b2c/96d5084。
- **RUN_JOURNAL**：VALID（session5 追加 RESUME/DELIVERY/CHECKPOINT 事件）。M3_RECOVERY_STATUS=ACTIVE 未改。M4 保持 fail-closed（checker M3 FINAL qual_data_readiness+qual_custody_binding ABSENT→RESULT[A]=FAILED；launcher dry-run refused=true）。
- **测试基线**：delivery_control **207 passed** + eval_audit_spine **53**；ready_set selftest ALL_PASS；checker selftest ALL_NEGATIVE_CASES_ENFORCED。

### session5 已交付（确定性代码已机器验证 + 真实小批 pilot 已贯通）
- **§四.1 富标签**：annexC `qual_rich_labeler`/`qual_rich_adjudicator`（九模块金标字段，sha 自洽；旧二字段 labeler_ref/adjudicator_ref 保留供 G2）；`qual_runner` cmd_label/labelfreeze/adjudicate 转富路径；cmd_faces 加 `source_group_id`（claim 级，变体继承 base）。
- **§四.2 金标派生**：新增 `m3_data_supply_001/tools/qual_gold_derivation.py`（富标签→逐模块 `assemble_gold_record` 合规记录 + cross_module_reuse 登记）；`cmd_goldfreeze` 重写为逐 face 派生 → `qual_generation.build_generation` 真链 → custody 复算 class_counts → **v2** GOLD_FROZEN_RECEIPT（不覆盖 v1 封存件）；删旧简化非合规写入路径。测试 `test_qual_gold_derivation` 20 测。commit `587c9df`。
- **§六 pilot（真实跨模型）**：新增 `qual_pilot.py`（断点续跑）。**pilot_pass=true**：真源 5 base→真构造 6 变体(6 kind 各1，base0 承2变体证同 source_group)→席A(Codex)+席B(Claude)富标注→隔离仲裁(11 分歧全裁)→derive→九模块真 core(core_validation_passed=true)→真 generation 链(resolves=true)→custody→readiness(FAIL 但 **non_scale_failures=[]**，仅规模/类下限，符合『允许失败仅规模/类下限』)。回执 `m3_data_supply_001/gold/qual/pilot/PILOT_RECEIPT.v1.json`（零明文）。

### R3-run 前必读发现（session5 pilot 实证）
1. **100% 跨模型分歧**：`_rich_key` 要求九模块全字段精确一致，结构字段（atom_partition/reference_attributes）跨模型几乎不逐字相同 → 每 face 走仲裁（3x 建标成本）。**建议全量前先做 §四.1 精修**：把『全字段 all-or-nothing 一致』改为**逐模块/逐字段一致**（某 face 可 risk 一致=CROSS_MODEL_AGREED 而 atom_partition 分歧=该模块 ADJUDICATED），降仲裁量 + 贴合『每模块 gold 谓词分别独立成立』。加负测。
2. **review/formulaic 真标注子管线未建**：pilot 用确定性覆盖单元；全量须建真 review（item×reviewer approve/veto）与 formulaic（pair 轴标注 + rubric 冻结 + candidate 挖掘）标注路径。
3. **延迟/成本**：Claude 富标注 4-face 块 ~250-305s，codex 12-face ~58s。全量按可恢复批 `--max-batches` 分批 + 断点续跑；`| tail` 会吞被杀进程输出（重定向到文件读）。

---

你是 M3 恢复主执行者，主模型 claude-opus-4-8。目标：从磁盘检查点续完成 M3（R3-run 全量→R4→R5→R6），不重规划、不进 M4。不得运行 M0，不得启动 M4。发起人已授权 Opus 4.8 完全替代 Fable 5，不得再探测/等待/询问模型替换。

## 启动动作
1. 核验 cwd/分支/HEAD/远程/工作树；验 RUN_JOURNAL 链 VALID。
2. 读 `M3_RECOVERY_PROGRESS.v3.json` + `M3_RECOVERY_STATUS.v1.json` + 本 v3 顶部块 + `measurement_qualification.v2.json` + `qual_gold_derivation.py`/`qual_runner.py`/`qual_pilot.py`/`qual_custody_recompute.py`/`pre_m0_readiness.py`。
3. 追加 session 身份记录（不覆盖历史）+ journal RESUME 事件后再改业务。

## 执行顺序（本 v3 续跑）
1. **§四.1 精修（建议先做）**：labelfreeze/adjudicate/goldfreeze 逐模块/逐字段一致（见上『发现1』）。
2. **review/formulaic 真标注子管线**：建真标注路径（见『发现2』）。
3. **R3-run 全量**（多会话，付费；成本非停工门）：QUAL-A/B 各套 split(membership 已存)→faces(plan 驱动 6 kind)→label --seat A/B(可恢复批)→labelfreeze→adjudicate→goldfreeze(逐模块派生+真 generation)。逐批 custody 复算有效独立 N 直至每类≥下限（risk_high≥300 等；供给 510≥300 已预检 FEASIBLE）。known-R5 五案例+合法变体绑定。某 generation 不合格→整体 superseded 建下一 generation，不改已冻结。额度耗尽→落 INTERRUPTED_RESUMABLE + 推安全检查点，不写 HONEST_STOP。
4. **R4**：custody 直算 A/B readiness，两套 verdict=PASS；checker M3 FINAL qual_data_readiness+qual_custody_binding 转 PASS（绑 custody anchors）。不运行 M0、不揭晓 gold。
5. **R5**：全测（不减）+§八负测 + 两份全新独立终审（Opus 对抗 + Codex 复算，绑同一 candidate/readiness/generation/index，不复用主/席/仲裁会话）。发现影响资格真实性/密封/统计有效/M4 消费者→修 + 双审重跑。
6. **R6**：v2 关闭工件 + ORIGIN_ANCHOR.v3（不覆盖 v2）+ 显式路径快进推送 + checker M3 FINAL 全绿 + STATUS→CLOSED_PASS（完整 closed_pass_binding 含真 generation 链）+ closure 复算（本地+远程 HEAD）+ `launcher --dry-run M4` would_launch=true → 退出等 Codex 复审，不启动 M4。

## 运维真值
- 席A(codex)/本地 commit/push **须沙箱外**（`dangerouslyDisableSandbox`；沙箱内 gitdir/app-server 只读 FS）；git 读沙箱内可跑。
- 席B(claude)/富标注/仲裁走 `claude -p --model claude-opus-4-8`；富标注分块（CHUNK=4）更稳。
- 密封明文只落 `sealed_custody_001/**`（gitignore）；Git 仅代码/测试/config/回执聚合/sealed=HIDDEN index（仅 case_id+摘要）。

## 停止条件
普通问题（测试/schema/代码/初次容量/单 generation 污染/模型调用/网络/审核整改/工具兼容/额度耗尽/文档命名）全自动处理，不问发起人。**HONEST_STOP 仅限**：①穷尽既有真源合法统计独立补量后 A/B 任一套仍机械证明容量不足；②数据泄漏/QUAL 顺序污染无法经作废 generation 干净重建恢复；③确缺只能由用户提供的外部事实/凭据/权限。禁伪造 PASS、禁降 V1.1/M0/measurement_qualification.v2 标准。

## 最终输出
按顶层 Prompt §十一 模板提交单份结果（M3_RECOVERY_RESULT + BASELINE/FINAL HEAD + 各阶段状态 + NEXT_ACTION）。PASS 则 NEXT_ACTION=WAIT_FOR_CODEX_M3_REVIEW 并立即结束；INTERRUPTED_RESUMABLE 则保存干净已推送检查点 + 唯一 resume 入口后结束。
