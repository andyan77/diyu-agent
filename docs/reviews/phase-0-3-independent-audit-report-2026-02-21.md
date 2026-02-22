# Phase 0-3 独立审查报告（代码落盘 + 运行态探针）

- 审查日期: 2026-02-22
- 审查人: Codex（独立复核）
- 审查范围: Phase 0-3
- 审查输入: `docs/task-cards/**`、`docs/governance/milestone-matrix*.md`、`delivery/**`、`src/**`、`tests/**`、`frontend/**`
- 审查约束: **未读取或引用任何审计类文档内容**（`docs/reviews/**` 仅作为本报告写入路径）

## 1. 关键发现（按严重级）

### [High] Phase 2/3 硬门禁被 `lint` 阻塞，当前无法 GO
- 现象:
  - `phase_2`：hard `16/17`，阻塞项 `p2-lint`
  - `phase_3`：hard `13/14`，阻塞项 `p3-lint`
- 直接证据:
  - `Makefile:44` (`lint` 目标)
  - `scripts/eval-gen/validate.py:15`
  - `scripts/eval-gen/validate.py:17`
  - `scripts/eval-gen/validate.py:184`
  - `scripts/eval-gen/validate.py:289`
  - `scripts/eval-gen/validate.py:681`
  - `scripts/eval-gen/validate.py:942`
  - `scripts/eval-gen/validate.py:1027`
- 失败类型:
  - Ruff `RUF001/RUF002/W605/SIM102/F841` 共 19 项
- 影响:
  - `verify_phase.py` 的 P2/P3 hard gate 无法通过，发布判断为 `BLOCKED`

### [Medium] 交付 preflight 对 Python 版本校验过宽，可能放过不满足项目要求的环境
- 现象:
  - `pyproject.toml` 要求 `>=3.12`
  - `delivery/preflight.sh` 仅按主版本比较（`python3` 只要 major >= 3 即 PASS）
- 直接证据:
  - `pyproject.toml:6`
  - `delivery/preflight.sh:41`
  - `delivery/preflight.sh:43`
  - `delivery/preflight.sh:106`
- 影响:
  - 可能在 Python 3.10/3.11 环境误判“可部署”，增加运行时不一致风险

### [Low] FastAPI `on_event` 生命周期 API 已弃用（当前不阻塞）
- 现象:
  - 组合根集成测试产生 deprecation warnings
- 直接证据:
  - `src/main.py:267`
  - `src/main.py:295`
- 影响:
  - 当前功能可用，但后续 FastAPI 升级会积累迁移成本

## 2. 总体结论

- **Phase 0: GO**（hard 10/10, soft 2/2）
- **Phase 1: GO**（hard 9/9）
- **Phase 2: BLOCKED**（hard 16/17，唯一阻塞 `p2-lint`）
- **Phase 3: BLOCKED**（hard 13/14，唯一阻塞 `p3-lint`）

结论: 代码主体与跨层链路基本落盘，Phase 2/3 的核心阻塞为同一质量门禁问题（lint），非业务链路断裂。

## 3. 运行态探针（真实启动 + HTTP 实打）

### 3.1 启动方式
- 命令: `JWT_SECRET_KEY=... uv run uvicorn src.main:app --host 127.0.0.1 --port 18080`
- 结果: 服务可启动；Neo4j/Qdrant 不可达时按 `optional` 模式降级（非致命）

### 3.2 路由探针结果
- `GET /healthz` -> `200`
- `GET /api/v1/me`（无 token） -> `401`
- `POST /api/v1/auth/login`（无 body） -> `422`（说明为 JWT-exempt 路由，不是 401）
- `GET /api/v1/me`（member token） -> `200`
- `GET /api/v1/admin/status`（member token） -> `403`
- `GET /api/v1/admin/status`（admin token） -> `200`
- `GET /api/v1/this-route-does-not-exist`（带 auth） -> `404`
- RateLimit 压测：`GET /api/v1/me` 在第 57 次触发 `429`，含 `Retry-After` 与 `X-RateLimit-Remaining: 0`

### 3.3 中间件链路证据
- 安全头全局注入:
  - 所有探针响应均含 `Strict-Transport-Security`
- 鉴权生效:
  - 无 token 命中 `401`
  - 登录路由免鉴权命中 `422`
- Post-auth 链路真实串接:
  - 成功业务请求含 `X-RateLimit-*` 与 `X-Budget-Remaining`
  - member 访问 admin 返回 `403`，且仍带 `X-RateLimit-*`（RBAC 在链中生效）
  - 429 返回含限流头（RateLimit 生效）

## 4. 真实组合根级集成测试

已执行:
- `tests/integration/test_composition_root.py`
- `tests/integration/test_gateway_rest_integration.py`
- `tests/e2e/cross/*`

结果:
- 34 passed, 0 failed
- 说明组合根装配、路由挂载、跨层链路（conversation/skill/memory/token/golden-signals/media）可运行

## 5. 文档-落盘一致性（任务卡/矩阵/构建）

### 5.1 矩阵门禁执行（delivery SSOT）
- 执行: `scripts/verify_phase.py --phase 0/1/2/3 --json`
- 结果:
  - P0/P1 全通过
  - P2/P3 仅 `lint` 阻塞

### 5.2 追踪与覆盖
- `scripts/task_card_traceability_check.py --json`
  - `main_coverage: 96.3%`（阈值 98% 按规则仍 PASS）
  - `all_coverage: 100%`
- `scripts/check_xnode_coverage.py`
  - P2: direct coverage `100%`（阈值 0.4，GO）
  - P3: direct coverage `100%`（阈值 0.7，GO）

### 5.3 任务卡质量
- `scripts/check_task_schema.py --mode full --json`
  - `block: 0`
  - `warning: 161`
  - `info: 65`
- 说明:
  - 主要为文案类 warning（目标表述“结果导向”不足），非结构性阻塞

### 5.4 构建交付文档对应检查
- `bash scripts/check_manifest_drift.sh` -> PASS（无漂移）
- `bash delivery/preflight.sh --json` -> PASS（但存在 Python 版本比较逻辑过宽问题，见 High/Medium 发现）

## 6. 对 P2 soft fail 的复核说明

初次 `verify_phase.py --phase 2` 中 soft fail:
- `p2-streaming`
- `p2-xf2-1-login-to-streaming`

复核后判定:
- 失败主因是环境未种子用户（`dev@diyu.ai / devpass123` 登录 401）
- 执行 `uv run python scripts/seed_dev_user.py` 后，相关 Playwright 用例可通过

备注:
- 在无有效 LLM API key 场景，后端日志会出现 provider 401 与降级日志；当前 UI E2E 仍可通过，属于环境依赖风险而非门禁定义内硬失败。

## 7. 审查结论与建议

### 7.1 阶段结论
- 当前仓库的 Phase 0-3 落盘实现已具备完整主干能力与跨层联通性。
- 阻塞 GO 的唯一硬问题是 lint 基线不洁（集中在 `scripts/eval-gen/validate.py`）。

### 7.2 最小整改清单（可直接执行）
1. 修复 `scripts/eval-gen/validate.py` 的 Ruff 违规（19 项），恢复 `make lint` 通过。
2. 收紧 `delivery/preflight.sh` 的 Python 版本校验到 `>=3.12`（至少比较 major+minor）。
3. 将 `scripts/seed_dev_user.py` 纳入前端 E2E 前置步骤（或在 Playwright `globalSetup` 自动种子），避免 soft gate 假失败。
4. 规划将 `@app.on_event` 迁移到 lifespan API，消除升级风险。

---

## 附: 本次执行的关键命令（节选）
- `uv run python scripts/verify_phase.py --phase 0 --json`
- `uv run python scripts/verify_phase.py --phase 1 --json`
- `uv run python scripts/verify_phase.py --phase 2 --json`
- `uv run python scripts/verify_phase.py --phase 3 --json`
- `make lint`
- `uv run pytest tests/integration/test_composition_root.py tests/integration/test_gateway_rest_integration.py tests/e2e/cross/ -q --tb=short`
- 运行态探针（启动 uvicorn + curl 200/401/403/404/429）
- `uv run python scripts/task_card_traceability_check.py --json`
- `uv run python scripts/check_task_schema.py --mode full --json`
- `uv run python scripts/check_xnode_coverage.py --phase 2 --json`
- `uv run python scripts/check_xnode_coverage.py --phase 3 --json`
- `bash scripts/check_manifest_drift.sh`
- `bash delivery/preflight.sh --json`
