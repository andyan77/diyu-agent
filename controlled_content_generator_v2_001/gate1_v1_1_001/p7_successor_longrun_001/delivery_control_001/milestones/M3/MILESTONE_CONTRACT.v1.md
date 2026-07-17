# M3 里程碑合同 v1（MILESTONE_CONTRACT）

```yaml
milestone_id: M3
prompt_id: P3
title: 数据供给与逻辑解耦（E1-S/D/Q + core 抽取）
workspace: /home/diyu/worktrees/gate1-longrun-001
branch: agent/gate1-v1-1-successor-longrun
input_commit: 5ce595de7eb48fcf04178651f84400b0411134be
control_plane_commit: 002db4559c4f9f1881525a4dda32d94a1062c3c8
launch: MANUAL_FOUNDER_LAUNCH（第二次；发起人裁决，journal seq30 + SUPERSESSION_LEDGER §7 第4行；投放 Prompt 逐字节核验 ae16ac3f）
session: 374b677b-6537-465f-bab1-993e8a9d75aa（Fable 5 / claude-fable-5，全新非 fork 顶层会话）
active_contract_set: v2.5@23f5fea（入口绑定集合摘要 d7265a1852e4b44db1fae134f5d03e404629470ee7438c36d08b1cc00d85a7e4；M3-C0 出口合同 M3 行冻结后重冻结为 516fe73bd37a82fc58973c517131da4e53262eec564287c9ea6cff731e30ae8f，见 SUPERSESSION_LEDGER §8）
b_route: UNFROZEN（B 评测路线选择属 M6，本里程碑不冻结）
```

## 写面（RENDERED_PROMPT.v1 冻结 + D0 解锁派生）

allowlist：
- `controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/**`
- `controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/**`
- `controlled_content_generator_v2_001/product_core_staging_001/**`（**M3 解锁**：D0 五条件合取 d0_approved=true，state/D0_STATUS.v1.json；仅限接口、schema、非密封开发样例与自含验证套件——D0 §②；胶囊⑥专用）

denylist：历史 P1–P6、R1–R5 证据；p5_p6_300_baseline_scale_and_freeze_001/**；旧 120 原文、86 历史候选、路线 60 黄金答案、组件基座；真实 QUAL、隐藏材料、客户数据目录（本合同密封承载区按保全协议处理，主会话不读）；其他 worktree、主分支、全局检查器、.github/workflows/**；.env*、密钥、凭据、生产配置、外部服务。

允许 Git 动作：显式路径 add、commit、push 既有 origin 任务分支；禁 tag/force-push/rebase/merge-master/历史重写/新产品 remote（产品 A/B 新仓属 M5/M7）。

## 入口（已核验）

M2 CLOSED_PASS（八件套 8/8 + typed PASS 5eaec1a6 + 双独立签字）；checker M3 PRE_REVIEW 三域绿 + ARTIFACT_INTEGRITY PASS；ready_set M3=READY；STATE_EXPECTATION[M3] 入口面（M0/V1.1 双 NOT_QUALIFIED、仅 S0 已执行、real_run_executed=true）；启动形态例外经发起人裁决登记（journal seq30 launch_ruling_facts）。

## 交付物（6 胶囊，v2.4 §三 3.2 M3 行）

- **①供需审计（E1-S）**：分格供需表（六格 NATURAL/CHALLENGE × DEV/VALIDATION/HIDDEN + 套路三层 L1/L2/L3 分层容量，需求锚 measurement_qualification.v2 qualification_set_minimums + 五内容族）+ 向量容量表（初版投影，P0-e）+ 抽样框/排除日志预登记（P0-i）+ 策展责任人登记。**容量缺口 = 合法停止（技术门）**——缺口成立时本里程碑以 HONEST_STOP 关闭，供需表即主交付物。
- **②标注协议+小试（E1-D 前段）**：标注协议冻结（量规版本、双盲流程、裁决规则、争议率与成本口径）+ 小试回执（协议在真实样本上走通，一致性/争议率/成本实测）。
- **③G1（E1-D）**：G1_REFERENCE_BUILD 金标（源证据切分+参考断言，独立双标+裁决）；出口=对向量容量表投影的覆盖校验、争议率、成本可复算、角色碰撞核查回执。
- **④G2（E1-D）**：G2_MEASUREMENT_DEV 开发金标（dev_manifest 物化合法）；出口同③；开发集允许模型提议留痕；G2 只可调方法、不可证 M0 资格。
- **⑤QUAL-A/B（E1-Q，顺序硬门）**：共同抽样框、分层随机、难度平衡、两集互不相交；每集依 QUAL_ORDER_CONTRACT 六步前三步 **①题面冻结→②双盲建标→③金标冻结**，每步出带单调序号回执；双集全部冻结先于任何 METHOD_FROZEN/揭晓；假通过率预算（family-wise，P0-f）预注册；密封摘要登记入 SEALED_PAYLOAD_DENYLIST + sealed_scan 撞库清洁。
- **⑥core 逻辑抽取+接口冻结（与①–⑤并行）**：按 CORE_EXPORT_ALLOWLIST 从 eval_audit_spine_001/{spine,schema,rubric,tests} 抽取至 product_core_staging_001/**（逐文件 sha256 EXTRACTION_MANIFEST）；接口冻结=core 可不读领域私有目录启动、测试语料经适配器挂载、审计事件不依赖 GATE1 私有路径（D0 §③⑤ + v2.4 附录 LOGICAL_CORE_SEPARATED 三判据，机械验证）；产出 `LOGICAL_CORE_SEPARATED` 旗标（写入 PASS 回执 qualification_flags）。

## 密封承载设计（SEALED_DATA_CUSTODIAN 指定，v2.5 §三 3.7′ + SEALED_CUSTODY_PROTOCOL）

- **保全角色承载**：`SEALED_DATA_CUSTODIAN = 确定性工具链`（p7 写面内 custody 工具 + 隔离明文承载区），非模型会话；工具结构性只输出数量/摘要/回执（技术强制，非提示词软约束）。
- **明文承载区**：`controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/sealed_custody_001/`——**gitignore 强制 + 断言门控提交前置扫描（staged 路径命中承载区 = 拒绝提交）**；明文零字节进 Git 历史；目录级隔离为本环境可达上限（单用户环境无独立文件系统边界，如实披露，双审核复核）。
- **主会话（M3_PRINCIPAL_ORCHESTRATOR）**：零接触 QUAL 明文（启动豁免附带承诺，journal seq30）；主会话只经工具 stdout 读取数量/摘要/回执。
- **接触明文的会话**（双盲标注/裁决）：全新非 fork 无工具 headless 单次调用，明文由确定性工具在进程内送入、标签回写承载区，逐会话登记（会话/线程标识、可见材料清单、销毁/留存方式）；载体可行性先证（胶囊②小试 + Codex 探针），不可行 = 停 + 报发起人。**席位承载（发起人 2026-07-17 双裁决，journal seq38）**：席位 A = Codex-GPT（`codex exec --ephemeral -s read-only`，scope v1.1；**本合同显式授予其 QUAL-A/B 题面标注期可见**——scope v1 §3-3 里程碑例外通道的行使；不见另一席位标签与金标终值）；席位 B = Fable（`claude -p` + `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`）；裁决席 = Fable（披露与 B 同模型，分歧材料匿名化）。
- **禁止消费方**（qualification_manifest）：主会话兼任 EVALUATOR_DEVELOPER/RUBRIC_DEVELOPER 身位，属 QUAL 金标禁止消费方——与零接触承诺一致。

## 出口（MILESTONE_EXIT_CONTRACT M3 行，本胶囊冻结）

v2.3 各步出口 + QUAL 双冻结保全回执（六步前三步 ×2 集）+ `LOGICAL_CORE_SEPARATED` + 供需表/向量容量表 + 八件套 + HANDOFF；两份独立审核（Fable 对抗 + Codex-GPT 复算签字）绑定同一候选（出口定义冻结本身在审核范围内）；checker `--milestone M3 --mode FINAL` 通过为任何 PASS 宣告前置。合法出口枚举：PASS / HONEST_STOP（容量缺口技术门）/ DIAGNOSTIC_FINAL / FAIL / INTERRUPTED_RESUMABLE。

## 里程碑专属停止线

- 密封明文入 Git 历史 / 泄漏给禁止角色 = 停（STOP_DATA_LEAKAGE，受影响集合整组失效）；
- QUAL 步序颠倒/补录（qual_order.py 违规非空）= 停（STOP_QUALIFICATION_ORDER_VIOLATION）；
- 在 M3 会话内运行 M0 资格（属 M4）= 停；
- 密封摘要 denylist 撞库命中 = 停。
