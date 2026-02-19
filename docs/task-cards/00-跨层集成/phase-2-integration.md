# Phase 2 Cross-Layer Integration Task Cards

## Phase 2: Core Conversation + Knowledge -- Cross-Layer Verification

---

### TASK-INT-P2-CONV: Conversation Loop Cross-Layer E2E

> 矩阵条目: X2-1
> 矩阵条目: X2-2
> 矩阵条目: X2-3

| Field | Value |
|-------|-------|
| **目标** | 对话闭环 + 流式回复 + Memory Evolution 三条跨层链路通过 E2E 验证 |
| **范围** | `tests/e2e/cross/test_conversation_loop.py`, `tests/e2e/cross/test_memory_evolution.py` |
| **范围外** | 前端 Playwright 测试 / 性能基准 / Token 计费链路 |
| **依赖** | TASK-B2-1, TASK-MC2-5, TASK-G2-2 |
| **风险** | 数据依赖: 需要 PG + Redis 全栈环境 [ENV-DEP]; 跨层耦合: Brain -> MemoryCore -> Gateway 三层交互; 测试稳定性: Fake adapter 精度不足可能导致假通过; 环境隔离: 测试间状态泄漏 |
| **兼容策略** | 新增测试文件, 无破坏性变更; Fake adapter 模式无外部服务依赖 |
| **验收命令** | `uv run pytest tests/e2e/cross/test_conversation_loop.py tests/e2e/cross/test_memory_evolution.py -v` |
| **回滚方案** | `git revert` (仅测试文件, 无 DDL) |
| **证据** | CI artifact / `evidence/phase-2/` |
| **决策记录** | 采用 Fake adapter 而非完整外部服务, 降低 CI 环境依赖 |

---

### TASK-INT-P2-TOKEN: Token Budget Backpressure Cross-Layer E2E

> 矩阵条目: X2-4

| Field | Value |
|-------|-------|
| **目标** | Token 预算反压链路 (消耗 -> 扣减 -> 耗尽 -> 402) 通过 E2E 验证 |
| **范围** | `tests/e2e/cross/test_token_backpressure.py` |
| **范围外** | 计费 UI / 充值流程 / 价格策略 |
| **依赖** | TASK-G2-4, TASK-I2-3 |
| **风险** | 数据依赖: 需要 token_billing 表有初始数据 [ENV-DEP]; 并发竞争: 多请求同时扣减可能产生竞态; 数值精度: 浮点扣减累积误差; 环境隔离: 测试间余额状态泄漏 |
| **兼容策略** | 新增测试文件, 无破坏性变更 |
| **验收命令** | `uv run pytest tests/e2e/cross/test_token_backpressure.py -v --tb=short` |
| **回滚方案** | `git revert` |
| **证据** | CI artifact |
| **决策记录** | -- |

---

### TASK-INT-P2-OBS: Observability Cross-Layer E2E

> 矩阵条目: X2-5
> 矩阵条目: X2-6

| Field | Value |
|-------|-------|
| **目标** | 4 黄金信号端到端 + 前端错误上报闭环通过验证 |
| **范围** | `tests/e2e/cross/test_golden_signals.py`, `frontend/tests/e2e/cross/web/error-boundary.spec.ts` |
| **范围外** | Grafana 看板 / 告警规则配置 / SLO 定义 |
| **依赖** | TASK-OS2-1, TASK-OS2-5 |
| **风险** | 环境依赖: 需要 Prometheus 可查询 [ENV-DEP]; 指标延迟: 异步采集可能导致测试 flaky; 前端运行时: 需要 Frontend dev server; 上报丢失: 错误上报到后端的链路可能断裂 |
| **兼容策略** | 新增测试文件 |
| **验收命令** | `uv run pytest tests/e2e/cross/test_golden_signals.py -v --tb=short` [ENV-DEP] |
| **回滚方案** | `git revert` |
| **证据** | CI artifact |
| **决策记录** | -- |

---

### TASK-INT-P2-FE: Frontend Integration Cross-Layer E2E

> 矩阵条目: XF2-1
> 矩阵条目: XF2-2
> 矩阵条目: XF2-3

| Field | Value |
|-------|-------|
| **目标** | 前后端集成三条链路 (登录->对话->流式 / 记忆面板 / 文件上传) Playwright E2E 通过 |
| **范围** | `frontend/tests/e2e/cross/web/login-to-streaming.spec.ts`, `frontend/tests/e2e/cross/web/memory-panel.spec.ts`, `frontend/tests/e2e/cross/web/file-upload.spec.ts` |
| **范围外** | Admin 前端 / 移动端 / 性能预算 |
| **依赖** | TASK-FW2-1, TASK-FW2-4, TASK-FW2-6 |
| **风险** | 环境依赖: 需要全栈运行 (Backend + Frontend) [ENV-DEP, E2E]; 测试稳定性: Playwright 超时/网络抖动; 认证链路: JWT 过期导致测试 flaky; 文件处理: 3-step upload 异步处理 |
| **兼容策略** | 新增测试文件 |
| **验收命令** | `cd frontend && pnpm exec playwright test tests/e2e/cross/web/` [ENV-DEP, E2E] |
| **回滚方案** | `git revert` |
| **证据** | Playwright trace + screenshots |
| **决策记录** | -- |

---

### TASK-INT-P2-OPENAPI: OpenAPI Type Sync Cross-Layer Gate

> 矩阵条目: XF2-4

| Field | Value |
|-------|-------|
| **目标** | OpenAPI 类型同步 (生成后 diff 为空) 作为跨层 gate 可追踪 |
| **范围** | `scripts/check_openapi_sync.sh` (已有) |
| **范围外** | 新增 API 端点 / API 版本策略 |
| **依赖** | TASK-D2-2 |
| **风险** | 脚本缺失: `check_openapi_sync.sh` 可能尚未实现; 生成器版本: OpenAPI 生成工具版本变化导致假阳性; CI 缓存: 缓存的旧生成物导致漏检; 编码差异: 换行符/编码差异导致 diff 非空 |
| **兼容策略** | 仅增加 xnodes 标记, 不改脚本逻辑 |
| **验收命令** | `bash scripts/check_openapi_sync.sh` |
| **回滚方案** | `git revert` xnodes 标记 |
| **证据** | CI 输出 |
| **决策记录** | 复用现有 check, 仅增加 xnodes 绑定 |
