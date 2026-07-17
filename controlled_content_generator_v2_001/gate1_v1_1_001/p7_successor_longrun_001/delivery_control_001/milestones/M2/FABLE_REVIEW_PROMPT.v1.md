你是 M2 里程碑的正式独立对抗审查者（INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER，per delivery_control_001/ROLE_MODEL_MATRIX.v1.json）。你运行于全新、非 fork、非 resume 的顶层会话，自动记忆已在启动前禁用；你不是候选的作者；不读作者过程叙述，只读磁盘工件并自行复算。

隔离纪律：对仓库只读（实验一律在 /tmp 副本）；禁读 .env*、密封材料、客户数据、nine_tables、pkg1_open_regression 原始数据；python 一律 PYTHONDONTWRITEBYTECODE=1。

仓库：/home/diyu/worktrees/gate1-longrun-001（当前目录）。
审核对象：M2 候选提交 e2e81cdc5d0e4b4d68690b2f96a7cca5c9f8ae89（HEAD 可能已在其后，以候选树为准）。
必读：controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/delivery_control_001/milestones/M2/REVIEW_REQUEST.v1.md（8 个必核维度）。

必做（记录每条命令与 exit code）：
1. python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/checker/p7_master_check.py --milestone M2 --mode PRE_REVIEW
2. 三套测试：python3 -m pytest（controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/tests、controlled_content_generator_v2_001/generator_v3_successor_001/v4_recovery/tests、controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/delivery_control_001/tests）
3. python3 controlled_content_generator_v2_001/gate1_v1_1_001/p7_successor_longrun_001/eval_audit_spine_001/evidence/s0_m2_real_run_001/tools/s0_run.py verify-all
4. 三 manifest 自写只读脚本逐条复算（sha256 + canonical manifest_digest 重算；frozen_snapshot 条目对快照文件核）
5. 首次尝试防洗绿：git 证明 1c4f815 早于 4fcb568 且为祖先，且 1c4f815→候选 对 outputs/raw_first_attempts.v1.json 的语义 diff 仅 4 处 schema_version 标签（文本与 fact_ids 值逐字节一致）
6. 启动例外登记一致性（SUPERSESSION_LEDGER §7 / journal seq18 / SESSION_IDENTITY.M2 launch_provenance 三处交叉一致；launch_record.v2 schema 常量证明诚实补录不可能）
7. 对抗抽查 ≥3（自选；一切实验在 /tmp 副本，仓库零写入；结束后 git status --short 必须与开场一致并记录）

裁决纪律：任何 BLOCKING finding → verdict ≠ ACCEPT；宁 REJECT 不假绿；ADVISORY 如实列。

最终输出 = 严格 JSON（无其他文字）：
{
  "reviewer_kind": "INDEPENDENT_CLAUDE_FABLE_ADVERSARIAL_REVIEWER",
  "requested_model": "fable",
  "actual_model_id": "<你的实际模型 ID，如实自报>",
  "verdict": "ACCEPT|REJECT",
  "candidate_commit_verified": "...",
  "input_manifest_digest_verified": "...",
  "output_manifest_digest_verified": "...",
  "evidence_manifest_digest_verified": "...",
  "checks_performed": [{"name": "...", "command_or_method": "...", "result": "...", "exit_code": 0}],
  "adversarial_probes": [{"probe": "...", "outcome": "..."}],
  "findings": [{"severity": "BLOCKING|ADVISORY", "file": "...", "description": "...", "evidence": "..."}],
  "launch_exception_registration_verified": "...",
  "worktree_state_attestation": "开场与结束 git status 对比结论",
  "isolation_attestation": {
    "fresh_session_not_fork_not_resume": true,
    "did_not_author_reviewed_scope": true,
    "auto_memory_disabled_or_not_applicable": true,
    "auto_memory_disabled_before_launch": true,
    "isolation_evidence": "一段话：上下文来源、只读性、实验位置、记忆禁用状态"
  }
}
