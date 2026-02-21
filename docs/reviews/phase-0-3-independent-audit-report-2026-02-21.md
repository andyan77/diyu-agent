# Phase 0-3 全量独立审查报告（2026-02-21）

## 1. 审查范围与基线
- 范围：`phase_0` 到 `phase_3` 的落盘实现（代码、测试、CI/Gate、证据归档、任务卡追溯）。
- 基线文档：
  - `docs/governance/milestone-matrix.md`
  - `docs/governance/milestone-matrix-backend.md`
  - `docs/governance/milestone-matrix-frontend.md`
  - `docs/governance/milestone-matrix-crosscutting.md`
  - `docs/task-cards/00-跨层集成/phase-2-integration.md`
  - `docs/task-cards/00-跨层集成/phase-3-integration.md`
  - `docs/governance/decisions/2026-02-20-phase3-build-roadmap-v1.3.1.md`
  - `delivery/milestone-matrix.yaml`
  - `delivery/manifest.yaml`

## 2. 审查结论（总览）
- 机器门禁口径（`verify_phase` / `xnode_coverage`）：`phase_0~3` 均为 `GO`。
- 文档治理口径（任务卡验收路径 + Go/No-Go 硬条件）：存在阻断差异，尤其 `phase_3`。
- 独立审查判定：**有阻断项（BLOCKED）**。

## 3. 分阶段结果
- Phase 0：`verify_phase` 10/10 hard, 2/2 soft，全通过。
- Phase 1：`verify_phase` 9/9 hard，全通过。
- Phase 2：`verify_phase` 17/17 hard 全通过；soft 6 项中 2 项失败（不阻断）。
  - 失败项：`p2-streaming`、`p2-xf2-1-login-to-streaming`。
  - 独立复现结果：Playwright 登录 401（测试用户未种子）。
- Phase 3：`verify_phase` 14/14 hard, 2/2 soft，全通过；`xnode_coverage` 100%（阈值 0.70）。

## 4. 关键阻断发现（按严重度）

### [HIGH] F1：Phase 3 跨层集成卡定义的验收文件未落盘
- 事实：`phase-3-integration` 中 5 张卡的关键验收文件不存在。
- 文档证据：`docs/task-cards/00-跨层集成/phase-3-integration.md:22`, `docs/task-cards/00-跨层集成/phase-3-integration.md:83`, `docs/task-cards/00-跨层集成/phase-3-integration.md:104`
- 现状证据：
  - `tests/e2e/cross/test_skill_e2e.py` 不存在
  - `tests/e2e/cross/test_media_upload.py` 不存在
  - `frontend/tests/e2e/cross/web/skill-artifact.spec.ts` 不存在
  - `frontend/tests/e2e/cross/admin/knowledge-workflow.spec.ts` 不存在
  - `frontend/tests/e2e/cross/admin/org-config-inherit.spec.ts` 不存在
- 影响：与 Phase 3 Go/No-Go 的“5 张集成卡全部有可执行证据”硬条件冲突。
- 对应硬条件：`docs/governance/decisions/2026-02-20-phase3-build-roadmap-v1.3.1.md:549`

### [HIGH] F2：Phase 3 证据目录未覆盖“5 张集成卡逐条证据”
- 文档要求：`docs/governance/decisions/2026-02-20-phase3-build-roadmap-v1.3.1.md:549`
- 实际目录：`evidence/phase-3` 仅见 `verify-phase_3*.json`、`xnode-coverage*.json`、附录文档，未见上述 5 张集成卡对应测试产物（如 skill/media/admin cross e2e 的独立证据）。
- 影响：按治理文档硬条件，Phase 3 放行证据链不完整。

### [MEDIUM] F3：Phase 2 软门禁失败可稳定复现，根因为 E2E 凭据准备不足
- 复现命令：
  - `frontend/tests/e2e/web/chat/streaming.spec.ts`
  - `frontend/tests/e2e/cross/web/login-to-streaming.spec.ts`
- 复现结果：登录 401，报错提示“Ensure backend is running ... and dev user is seeded”。
- 影响：虽然不阻断 hard gate，但表明前端关键链路 E2E 的环境准备不稳定。

### [MEDIUM] F4：任务卡治理脚本可“语法通过但语义失真”
- `check_acceptance_gate.py` / `check_task_schema.py` 只校验命令格式、标签、空值，不校验命令引用文件是否存在。
- 代码证据：`scripts/check_acceptance_gate.py:127`, `scripts/check_acceptance_gate.py:148`, `scripts/check_task_schema.py:326`
- 影响：任务卡可在引用失效路径的情况下仍被 gate 判定 PASS。

### [MEDIUM] F5：`task_card_traceability_check --phase N` 的 `dangling_refs` 受全局引用污染
- 行为：phase 过滤时，`dangling_refs` 仍用全量任务卡引用集合计算，导致输出大量跨 phase 噪声。
- 代码证据：`scripts/task_card_traceability_check.py:185`, `scripts/task_card_traceability_check.py:186`
- 影响：phase 级审查可读性和诊断精度下降。

## 5. 非阻断观察
- `delivery/milestone-matrix.yaml` 与 `delivery/manifest.yaml` 当前阶段一致为 `phase_3`。
  - `delivery/milestone-matrix.yaml:7`
  - `delivery/manifest.yaml:58`
- CI 已包含 `verify_phase.py --phase 3` 与 `--phase 2` 回归步骤。
  - `.github/workflows/ci.yml:282`
  - `.github/workflows/ci.yml:284`
- 但 `ci.yml` 中未见独立前端 Playwright 全量 job（仍主要依赖阶段脚本和少量 E2E）。

## 6. 审查命令摘要（本次执行）
- `uv run python scripts/verify_phase.py --phase 0 --json` -> GO
- `uv run python scripts/verify_phase.py --phase 1 --json` -> GO
- `uv run python scripts/verify_phase.py --phase 2 --json` -> GO（soft 2 fail）
- `uv run python scripts/verify_phase.py --phase 3 --json` -> GO
- `uv run python scripts/check_xnode_coverage.py --phase 2 --json` -> GO
- `uv run python scripts/check_xnode_coverage.py --phase 3 --json` -> GO
- `uv run python scripts/check_task_schema.py --mode full --json` -> block=0
- `uv run python scripts/check_acceptance_gate.py --json` -> PASS
- `uv run python scripts/task_card_traceability_check.py --json` -> PASS（all_coverage 100%）

## 7. 建议整改优先级
1. 先决修复（阻断解除）
- 对齐 `phase-3-integration` 与真实实现：
  - 方案 A：补齐缺失测试文件与证据归档。
  - 方案 B：若改用替代测试，回写任务卡 + 横切矩阵 + 路线图，统一验收命令。

2. 门禁增强
- 在 `check_acceptance_gate.py` 增加“命令路径存在性”检查（至少校验 `tests/`、`scripts/`、`frontend/tests/`）。
- 在 `task_card_traceability_check.py` 的 phase 模式下，按 phase 过滤 `dangling_refs`。

3. E2E 稳定性
- 固化 Playwright 账号种子流程（测试前自动 seed dev user），避免 401 软失败常态化。

---
审查时间：2026-02-21（本地执行）
审查类型：独立复核（文档基线 + 落盘核验 + 命令复现）
