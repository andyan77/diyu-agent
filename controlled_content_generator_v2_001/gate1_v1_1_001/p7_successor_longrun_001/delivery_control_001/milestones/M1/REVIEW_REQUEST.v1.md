# M1 独立审核请求书 v1

## 审核对象（候选绑定）

```yaml
candidate_commit: 11b71e9bed9078c2483dc27ae94a807689ff5528
input_manifest_digest: 见 milestones/M1/INPUT_MANIFEST.v1.json manifest_digest 字段
output_manifest_digest: 见 milestones/M1/OUTPUT_MANIFEST.v1.json manifest_digest 字段
evidence_manifest_digest: 见 milestones/M1/EVIDENCE_MANIFEST.v1.json manifest_digest 字段
active_contract_set_digest: cbe5f5f4e65a7766e328c5c676ecad2958fb4fdaacc9d17d44350a60cd46dee9
```

## 审核者要求（P1 §十六）

- 全新、只读、非 fork、非 resume 会话；不得为本候选的作者；
- 独立从磁盘复算，不采信作者叙述；结论绑定上述候选提交与 manifest 摘要；
- 回执按 `delivery_control_001/schema/signer_receipt.v1.schema.json`：缺任一必填字段 = 未签；
- 不可得字段写 `{value: UNAVAILABLE, unavailable_reason, evidence_ref}`；禁止伪造模型修订号或调用 ID。

## 必核维度

1. **真源与授权**：SOURCE_LOCK / ACTIVE_CONTRACT_SET / SUPERSESSION_LEDGER 与 v2.5@23f5fea 一致；历史文件零改写（v2.3/v2.4/v1.x 逐字封存）；
2. **D0 章程**（本审核同时构成 D0 独立审核）：八项边界与 v2.4 §四 4.1 一致；生效五条件机制无布尔速记；
3. **23 位点迁移**：v2.5 §五第 12 项四家族语义落实；保留面无误伤（DeepSeek 30 元/日、24 字段成本事件、v4_recovery 测试、模块门阈值）；
4. **实际态/期望态分离**：实际状态文件只записыв真实结果；期望在 STATE_EXPECTATION；checker 比较两者；无"把实际证据改成期望值"；
5. **状态机**：typed 回执按值匹配；Y 图 ready-set（路线 (b) 只认 A2_QUALIFIED；M7 只认 B_LIFT_READY=true）；launcher 拒绝面（同会话/子代理伪装/缺签字/不合格前序）；
6. **测试真实性**：正向未来态 + 30 项负向攻击矩阵非假绿（无 skip/空断言/删断言/降阈值）；
7. **诚实基线**：M0 与 V1.1 保持 NOT_QUALIFIED；M1 未执行 M2、未运行真实 S0、未建产品仓/远程/core 暂存；
8. **工作树保全**：74 个用户工件逐字保全（C0 diff 零内容改写）。

## 建议复算命令（只读；PYTHONDONTWRITEBYTECODE=1）

```bash
python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/checker/p7_master_check.py --milestone M1 --mode PRE_REVIEW
python3 -m unittest discover controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/tests -p "test_*.py"
python3 controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/tests/test_v4_recovery.py
python3 -m unittest discover controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/delivery_control_001/tests -p "test_*.py"
python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/delivery_control_001/tools/residual_scan.py
python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/delivery_control_001/tools/contract_set.py verify
git diff f7d661995165f4d7a6559c40482e296b43781bd2 23f5fea355ef4904043c98187ba2a82c846772be --stat  # 保全逐字性反查
```

## Verdict 语义

`ACCEPT` = 全部维度通过；`REJECT`/`CONDITIONAL_REJECT` = 列出阻断项（候选将修复并形成新候选，两份审核对新候选重跑）。

## 第二轮说明（R2）

第一轮（候选 3b29055）：Fable=ACCEPT+2 ADVISORY；Codex=REJECT（2 BLOCKING）。四项修复已入新候选 `4c28642`：
1. Codex B-1：`check_pkg1_reviews` 按可写性分支——可写环境保持完整破坏性重算+还原（真门）；只读审核环境降级为对 HEAD 字节锚定（未提交篡改仍被抓），完整重算由可写侧记入 VERIFICATION_RECEIPTS.M1.v2；
2. Codex B-2：`VERIFICATION_RECEIPTS.M1.v2.json` 于候选头签发（git_head_at_run==候选），含完整 PRE_REVIEW 入口运行（exit 0，三域 PASS）；v1 保留为 C4 时点历史；
3. 主负责人自查缺陷：活体演进文件（journal/D0_STATUS/PROMPT_REGISTRY/CAPSULE_LEDGER/STOP_LEDGER）manifest 改用 `frozen_snapshot` 锚定（milestones/M1/snapshots/，字节==候选提交）——否则关闭阶段状态更新会使 M2 启动时八件套复算漂移；
4. Fable ADVISORY：`check_write_surface` 过滤不可提交环境工件（设备节点/纯设备目录）与 P1 §八 允许的未跟踪 `.claude/**`；已提交面维持全严。

模型能力登记：子代理模型被环境钉死为 claude-opus-4-8（探针证据见 AGENT_LEDGER_ADDENDUM）；审查人按 P1 §十六 如实自报实际模型即可，Claude 家族满足"Claude/Fable 对抗审查"文面。

## 第三轮说明（R3）

第二轮（候选 4c28642）：Fable=ACCEPT（四项 R1 修复全部实证 + 1 ADVISORY）；Codex=REJECT（1 BLOCKING + 1 ADVISORY）。三项修复入新候选 `11b71e9`：
1. Codex R2 BLOCKING：新建 `eval_audit_spine_001/calibration/V11_STATUS.v1.json` 为 V1.1 实际资格态唯一磁盘真源（诚实 NOT_QUALIFIED）；`check_m0_state_integrity` 消费 STATE_EXPECTATION.v11_status 并强制「QUALIFIED 须全 B 轨已执行 + 独立终验证据」不变量——`V1_1_REMAINS_HONESTLY_NOT_QUALIFIED` 现可机械复算；
2. Fable R2 ADVISORY：closeout.py frozen_snapshot 路径遍历加固（resolve + is_relative_to 里程碑 snapshots/ 目录）；
3. Codex R2 ADVISORY：验证电池 v3 增加里程碑区间 `git diff --check 23f5fea..HEAD`（带逐字保全豁免口径：P1 逐字 Prompt 的 markdown 硬换行与 C0 字节保全用户工件的 EOF 约定属原文语义，豁免逐条列出，其余零容忍）。
