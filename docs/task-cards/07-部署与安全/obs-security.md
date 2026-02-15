# Observability & Security 任务卡集

> 架构文档: `docs/architecture/07-部署与安全.md`
> 治理规范: v1.1 Section 5/7/11
> 里程碑来源: `docs/governance/milestone-matrix-crosscutting.md` Section 3
> 影响门禁: 横切关注点，贯穿所有层
> 说明: 与 Delivery 共享架构文档 `07-部署与安全.md`，但作为独立维度管理

---

## Phase 0 -- 基线可观测性 + 安全扫描

### TASK-OS0-1: 统一日志格式 (JSON)

| 字段 | 内容 |
|------|------|
| **目标** | 所有 API 请求日志含 trace_id / org_id / request_id 三个必需字段 |
| **范围 (In Scope)** | `src/gateway/middleware/logging.py`, 日志配置 |
| **范围外 (Out of Scope)** | 业务层日志内容 / 前端日志采集 / 监控告警规则 / 日志存储方案 |
| **依赖** | Gateway |
| **兼容策略** | 新增日志中间件 |
| **验收命令** | [ENV-DEP] `curl localhost:8000/healthz && grep trace_id logs/app.json` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 日志含 3 个必需字段 |
| **风险** | 依赖: Gateway 中间件链 / 数据: 日志需脱敏, 禁止记录密钥和 PII / 兼容: 新增日志中间件 / 回滚: git revert |
| **决策记录** | 决策: 统一 JSON 日志格式含 trace_id/org_id/request_id / 理由: 全链路追踪基座, 支持跨层日志关联 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS0-1

### TASK-OS0-2: ruff + mypy --strict CI 集成

| 字段 | 内容 |
|------|------|
| **目标** | CI 中两项检查通过 |
| **范围 (In Scope)** | `.github/workflows/ci.yml` |
| **范围外 (Out of Scope)** | 业务层代码实现 / 前端 ESLint / 安全扫描 / 测试框架 |
| **依赖** | CI |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | `ruff check src/ && mypy --strict src/ && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | CI 日志 |
| **风险** | 依赖: CI 运行时 / 数据: N/A -- 纯静态检查 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: ruff + mypy --strict CI 集成 / 理由: 代码质量门禁, 静态分析前移 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS0-2

### TASK-OS0-3: secret scanning (gitleaks/trufflehog)

| 字段 | 内容 |
|------|------|
| **目标** | CI 中 secret 扫描通过，无硬编码密钥 |
| **范围 (In Scope)** | `.github/workflows/ci.yml`, `.gitleaks.toml` |
| **范围外 (Out of Scope)** | 密钥管理系统 / SAST 扫描 / 依赖漏洞扫描 / 运行时密钥检测 |
| **依赖** | CI |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | `gitleaks detect --source . --no-banner && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 扫描报告 |
| **风险** | 依赖: gitleaks/trufflehog 工具 / 数据: 硬编码密钥=安全事故 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: gitleaks/trufflehog secret 扫描 CI 门禁 / 理由: 禁止密钥入库, 安全红线 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS0-3

### TASK-OS0-4: SAST 基础扫描 (Bandit/Semgrep)

| 字段 | 内容 |
|------|------|
| **目标** | CI 中 SAST 通过，无 Critical 漏洞 |
| **范围 (In Scope)** | `.github/workflows/ci.yml`, SAST 配置 |
| **范围外 (Out of Scope)** | secret scanning / 依赖漏洞扫描 / 渗透测试 / 运行时安全监控 |
| **依赖** | CI |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | `bandit -r src/ -ll && echo PASS` (0 Critical) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 扫描报告 |
| **风险** | 依赖: Bandit/Semgrep 工具 / 数据: N/A -- 纯静态分析 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: Bandit/Semgrep SAST 基础扫描 / 理由: 代码层安全漏洞前置拦截 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS0-4

### TASK-OS0-5: 依赖漏洞扫描 (safety/pip-audit)

| 字段 | 内容 |
|------|------|
| **目标** | CI 中依赖扫描通过 |
| **范围 (In Scope)** | `.github/workflows/ci.yml` |
| **范围外 (Out of Scope)** | SAST / secret scanning / 前端依赖审计 / 漏洞修复 |
| **依赖** | CI |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | `pip-audit --strict && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 扫描报告 |
| **风险** | 依赖: pip-audit/safety 工具 / 数据: N/A -- 纯依赖检查 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: pip-audit 依赖漏洞扫描 CI 门禁 / 理由: 供应链安全, 已知漏洞依赖前置拦截 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS0-5

### TASK-OS0-6: 前端 ESLint security rules + pnpm audit

| 字段 | 内容 |
|------|------|
| **目标** | `pnpm lint` 含安全规则，`pnpm audit` 无 Critical |
| **范围 (In Scope)** | `.eslintrc.js`, `.github/workflows/ci.yml` |
| **范围外 (Out of Scope)** | 后端安全扫描 / 前端业务逻辑 / XSS 防护实现 / CSP 配置 |
| **依赖** | CI |
| **兼容策略** | 新增前端安全规则 |
| **验收命令** | [ENV-DEP] `pnpm lint && pnpm audit --audit-level=critical` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 前端安全检查通过 |
| **风险** | 依赖: pnpm + ESLint 运行时 / 数据: N/A -- 纯静态检查 / 兼容: 新增前端安全规则 / 回滚: git revert |
| **决策记录** | 决策: ESLint security rules + pnpm audit 前端安全门禁 / 理由: 前端安全与后端对齐, 依赖漏洞前置拦截 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS0-6

### TASK-OS0-7: 安全管线 Stage 1 同步预检 [M-Track M0]

| 字段 | 内容 |
|------|------|
| **目标** | 文件上传时同步执行轻量安全预检 (文件类型/大小/magic bytes)，恶意文件在入口即拦截，拦截率 >= 99% |
| **范围 (In Scope)** | `src/gateway/security/precheck.py`, `tests/unit/gateway/test_precheck.py` |
| **范围外 (Out of Scope)** | 异步深度扫描 (OS3-1) / Gateway 上传 API / ObjectStorage Adapter / 前端上传组件 |
| **依赖** | Gateway (G2-6 三步上传协议) |
| **兼容策略** | 新增预检层；预检通过后进入异步深度扫描 (OS3-1) |
| **验收命令** | `pytest tests/unit/gateway/test_precheck.py -v` (恶意文件拦截率 >= 99%) |
| **回滚方案** | `git revert <commit>` -- 预检层移除，文件直接进入异步扫描 |
| **证据** | 同步预检拦截测试通过 |
| **风险** | 依赖: G2-6 (三步上传协议) / 数据: 安全扫描 Stage 1 同步预检不可旁路 (LAW 约束) / 兼容: 新增预检层 / 回滚: git revert, 降级为仅异步扫描 |
| **决策记录** | 决策: Stage 1 同步预检 (文件类型/大小/magic bytes) / 理由: 恶意文件入口即拦截, 不可旁路 (LAW 约束) / 来源: ADR-051, 架构文档 06 Section 1.6 |

> 矩阵条目: MM0-7 | M-Track: MM0-7
> 主卡归属: Obs & Security | 引用层: Gateway (上传入口)
> 与 OS3-1 (Phase 3 异步安全管线) 关系: Stage 1 同步预检 -> Stage 2 异步深度扫描 (OS3-1)

### TASK-OS0-8: 契约测试 Layer 1-4 全量新增条目 [M-Track M0]

| 字段 | 内容 |
|------|------|
| **目标** | M-Track M0 新增的所有 Port/Schema 契约测试全部通过，覆盖 ContentBlock Schema + ObjectStoragePort + LLMCallPort content_parts |
| **范围 (In Scope)** | `tests/contract/`, `tests/contract/test_m0_contracts.py` |
| **范围外 (Out of Scope)** | Port/Schema 实现逻辑 / 业务层集成 / 前端契约 / 性能测试 |
| **依赖** | TASK-I0-7 (ContentBlock), TASK-I3-3 (ObjectStoragePort), TASK-T0-4 (LLMCallPort Expand) |
| **兼容策略** | 纯新增契约测试；不影响业务逻辑 |
| **验收命令** | `pytest tests/contract/test_m0_contracts.py -v` (全部新增契约测试通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | M0 契约测试全部通过 |
| **风险** | 依赖: I0-7 + I3-3 + T0-4 三依赖 / 数据: 契约测试是 Port 兼容性保障 / 兼容: 纯新增契约测试 / 回滚: git revert |
| **决策记录** | 决策: M-Track M0 契约测试全量覆盖 / 理由: Port/Schema 契约变更需自动验证, 防止破坏性变更 / 来源: ADR-033, 架构文档 07 Section 2 |

> 矩阵条目: MM0-8 | M-Track: MM0-8 | V-x: XM0-1
> 主卡归属: Obs & Security (横切测试) | 引用层: Infrastructure, Tool, Gateway

---

## Phase 1 -- 隔离安全验证 + 审计基线

### TASK-OS1-1: RLS 隔离测试框架

| 字段 | 内容 |
|------|------|
| **目标** | 租户 A 不能读取租户 B 数据（正向+反向） |
| **范围 (In Scope)** | `tests/isolation/`, `tests/isolation/smoke/` |
| **范围外 (Out of Scope)** | RLS 策略实现 / 业务层数据逻辑 / 前端权限 UI / RBAC 权限检查 |
| **依赖** | PG RLS |
| **兼容策略** | 纯测试框架 |
| **验收命令** | `pytest tests/isolation/ -v` |
| **回滚方案** | 不适用 |
| **证据** | 隔离测试通过 |
| **风险** | 依赖: PG RLS 策略就绪 / 数据: 隔离测试失败=数据泄露风险 / 兼容: 纯测试框架 / 回滚: 不适用 |
| **决策记录** | 决策: RLS 隔离测试框架 (正向+反向) / 理由: 多租户数据隔离是安全基石, 需自动验证 / 来源: 架构文档 06 Section 1.6 |

> 矩阵条目: OS1-1

### TASK-OS1-2: 隔离 smoke 测试 CI 硬门禁

| 字段 | 内容 |
|------|------|
| **目标** | `pytest tests/isolation/smoke/` 在每次 PR CI 中通过 |
| **范围 (In Scope)** | `.github/workflows/ci.yml` |
| **范围外 (Out of Scope)** | 隔离测试实现 / RLS 策略 / 业务层逻辑 / 前端实现 |
| **依赖** | TASK-OS1-1 |
| **兼容策略** | 新增 CI 硬门禁 |
| **验收命令** | [ENV-DEP] CI-job: guard-checks (`pytest tests/isolation/smoke/ -v` 在 PR CI 中通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | CI 日志 |
| **风险** | 依赖: OS1-1 (隔离测试框架) / 数据: N/A -- 纯 CI 步骤 / 兼容: 新增 CI 硬门禁 / 回滚: git revert |
| **决策记录** | 决策: 隔离 smoke 测试 CI 硬门禁 / 理由: 每次 PR 自动验证租户隔离, 防止回归 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS1-2

### TASK-OS1-3: audit_events 写入 + 查询基线

| 字段 | 内容 |
|------|------|
| **目标** | 关键操作(登录/数据变更/权限变更)自动写入审计 |
| **范围 (In Scope)** | `src/infra/audit/`, `tests/unit/infra/test_audit_write.py` |
| **范围外 (Out of Scope)** | 审计表 DDL / 审计查询 UI / 合规删除 / 业务层触发逻辑 |
| **依赖** | Infra (I1-5) |
| **兼容策略** | 新增审计写入 |
| **验收命令** | `pytest tests/unit/infra/test_audit_write.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 关键操作有审计记录 |
| **风险** | 依赖: I1-5 (audit_events 表) / 数据: 审计记录不可篡改, append-only / 兼容: 新增审计写入 / 回滚: git revert |
| **决策记录** | 决策: 关键操作自动写入审计 (登录/数据变更/权限变更) / 理由: PIPL/GDPR 合规要求, 操作可追溯 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS1-3

### TASK-OS1-4: JWT 安全 (token 过期/轮换/revocation)

| 字段 | 内容 |
|------|------|
| **目标** | 过期 token 返回 401; 被 revoke 的 token 返回 401 |
| **范围 (In Scope)** | `src/gateway/middleware/auth.py` (增强), `tests/unit/gateway/test_jwt_security.py` |
| **范围外 (Out of Scope)** | JWT 生成逻辑 / 用户注册登录 / 前端 Token 管理 / RBAC 权限 |
| **依赖** | Gateway (G1-1) |
| **兼容策略** | 增强已有认证中间件 |
| **验收命令** | `pytest tests/unit/gateway/test_jwt_security.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 过期/revoke 场景通过 |
| **风险** | 依赖: G1-1 (JWT 中间件) / 数据: token 过期/revoke 是安全基线, 失败=未授权访问 / 兼容: 增强已有中间件 / 回滚: git revert |
| **决策记录** | 决策: JWT 安全增强 (过期/轮换/revocation) / 理由: token 生命周期管理是认证安全基线 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS1-4

### TASK-OS1-5: CORS + 安全头

| 字段 | 内容 |
|------|------|
| **目标** | 响应头包含 HSTS/CSP/X-Content-Type-Options |
| **范围 (In Scope)** | `src/gateway/middleware/security_headers.py` |
| **范围外 (Out of Scope)** | JWT 认证 / RBAC 权限 / 前端 CSP 策略消费 / XSS 防护 |
| **依赖** | Gateway |
| **兼容策略** | 与 G1-6 联合交付 |
| **验收命令** | `curl -I localhost:8000/healthz` (包含所有安全头) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 响应头完整 |
| **风险** | 依赖: Gateway 中间件链 / 数据: N/A -- 纯响应头配置 / 兼容: 与 G1-6 联合交付 / 回滚: git revert |
| **决策记录** | 决策: CORS + 安全头 (HSTS/CSP/X-Content-Type-Options) / 理由: OWASP 安全头最佳实践 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS1-5

### TASK-OS1-6: 前端 XSS 防护 (DOMPurify + CSP)

| 字段 | 内容 |
|------|------|
| **目标** | 注入脚本标签 -> 被净化/拦截 |
| **范围 (In Scope)** | `apps/web/lib/sanitize.ts`, `tests/unit/web/test_xss.ts` |
| **范围外 (Out of Scope)** | 后端输入验证 / CSP 头配置 / 前端业务逻辑 / 安全扫描 CI |
| **依赖** | FE-Web |
| **兼容策略** | 新增安全层 |
| **验收命令** | `pnpm test --filter web -- --grep xss` |
| **回滚方案** | `git revert <commit>` |
| **证据** | XSS 防护测试通过 |
| **风险** | 依赖: FE-Web 基础设施 / 数据: 未净化输入=XSS 漏洞 / 兼容: 新增安全层 / 回滚: git revert |
| **决策记录** | 决策: DOMPurify + CSP 双重 XSS 防护 / 理由: 客户端 XSS 是 OWASP Top 10, 双重防线 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS1-6

---

## Phase 2 -- 4 黄金信号 + 基础告警

### TASK-OS2-1: 4 黄金信号埋点

| 字段 | 内容 |
|------|------|
| **目标** | FastAPI middleware 自动采集延迟/流量/错误/饱和度 |
| **范围 (In Scope)** | `src/gateway/metrics/golden_signals.py` |
| **范围外 (Out of Scope)** | Grafana 看板 / 告警规则 / 业务层自定义指标 / 前端性能监控 |
| **依赖** | Prometheus client |
| **兼容策略** | 新增指标埋点 |
| **验收命令** | [ENV-DEP] `curl localhost:9090/api/v1/query?query=http_requests_total` (结果非空) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 4 项指标有数据 |
| **风险** | 依赖: Prometheus client 库 / 数据: 指标采集需低开销, 避免影响请求延迟 / 兼容: 新增指标埋点 / 回滚: git revert |
| **决策记录** | 决策: FastAPI middleware 自动采集 4 黄金信号 / 理由: 标准可观测性基线, 延迟/流量/错误/饱和度 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS2-1

### TASK-OS2-2: 基础告警规则

| 字段 | 内容 |
|------|------|
| **目标** | 错误率 > 1% 或 P95 > 2s 时触发告警 |
| **范围 (In Scope)** | `deploy/monitoring/alerts.yml` |
| **范围外 (Out of Scope)** | 指标埋点实现 / Grafana 看板 / 通知渠道配置 / 业务层告警 |
| **依赖** | Prometheus |
| **兼容策略** | 纯新增告警规则 |
| **验收命令** | [ENV-DEP] `curl -s localhost:9090/api/v1/rules \| python3 -c "import sys,json; r=json.load(sys.stdin); assert r['status']=='success'"` staging: 告警规则 Prometheus 加载成功 |
| **回滚方案** | 删除告警规则文件 |
| **证据** | 告警规则加载成功 |
| **风险** | 依赖: Prometheus 运行时 / 数据: 告警阈值需基于基线调整, 避免误报 / 兼容: 纯新增告警规则 / 回滚: 删除告警规则文件 |
| **决策记录** | 决策: 基础告警规则 (错误率>1% / P95>2s) / 理由: 异常快速发现, 降低 MTTD / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS2-2

### TASK-OS2-3: Token 消耗异常告警

| 字段 | 内容 |
|------|------|
| **目标** | 单次对话 token > 阈值 -> 触发告警 |
| **范围 (In Scope)** | `deploy/monitoring/alerts.yml` (追加) |
| **范围外 (Out of Scope)** | Token 计费实现 / LLM 调用逻辑 / 前端用量展示 / 预算管控 |
| **依赖** | llm_usage_records |
| **兼容策略** | 纯新增告警 |
| **验收命令** | [ENV-DEP] `curl -s localhost:9090/api/v1/alerts \| python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"` staging: Token 消耗告警规则可触发 |
| **回滚方案** | 删除规则 |
| **证据** | 告警触发截图 |
| **风险** | 依赖: llm_usage_records 数据 / 数据: 异常 token 消耗=成本失控信号 / 兼容: 纯新增告警 / 回滚: 删除规则 |
| **决策记录** | 决策: Token 消耗异常告警 / 理由: 防止 LLM 调用成本失控, 异常模式早发现 / 来源: ADR-047, 架构文档 07 Section 2 |

> 矩阵条目: OS2-3

### TASK-OS2-4: 结构化错误日志

| 字段 | 内容 |
|------|------|
| **目标** | 触发错误 -> 日志含 error_code + stack_trace + context |
| **范围 (In Scope)** | `src/shared/logging/error_handler.py` |
| **范围外 (Out of Scope)** | 业务层错误定义 / 前端错误展示 / 告警规则 / 日志存储 |
| **依赖** | -- |
| **兼容策略** | 新增错误处理器 |
| **验收命令** | `pytest tests/unit/shared/test_error_handler.py -v` (日志含 error_code + stack_trace + context) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 错误日志含 error_code 字段 |
| **风险** | 依赖: N/A / 数据: 错误日志需脱敏, 禁止记录 PII / 兼容: 新增错误处理器 / 回滚: git revert |
| **决策记录** | 决策: 结构化错误日志 (error_code + stack_trace + context) / 理由: 标准化错误排查, 支持告警关联 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS2-4

### TASK-OS2-5: 前端错误边界 + Sentry/等效方案

| 字段 | 内容 |
|------|------|
| **目标** | 组件崩溃 -> ErrorBoundary 捕获 -> 上报错误 |
| **范围 (In Scope)** | `apps/web/components/ErrorBoundary.tsx`, `apps/web/lib/error-reporting.ts` |
| **范围外 (Out of Scope)** | 后端错误处理 / 前端业务逻辑 / 告警规则 / 日志存储 |
| **依赖** | FE-Web |
| **兼容策略** | 新增错误边界 |
| **验收命令** | `pnpm test --filter web -- --grep ErrorBoundary` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 错误上报测试通过 |
| **风险** | 依赖: FE-Web 基础设施 / 数据: 错误上报需脱敏 / 兼容: 新增错误边界 / 回滚: git revert |
| **决策记录** | 决策: ErrorBoundary + Sentry 等效方案 / 理由: 前端崩溃可恢复, 错误自动上报 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS2-5

---

## Phase 3 -- 内容安全管线 + 审计闭环

### TASK-OS3-1: 内容安全检查管线 (security_status 6 态模型 -- 安全检查子集)

| 字段 | 内容 |
|------|------|
| **目标** | 恶意内容 -> quarantined -> 审计记录；实现 6 态模型 (ADR-051) 中安全检查子集: `pending` -> `scanning` -> `safe` / `rejected` / `quarantined` |
| **范围 (In Scope)** | `src/gateway/security/content_pipeline.py`, `tests/unit/gateway/test_content_pipeline.py` |
| **范围外 (Out of Scope)** | Stage 1 同步预检 (OS0-7) / 生命周期 expired 态 / 前端安全状态展示 / ObjectStorage 存储 |
| **依赖** | Gateway |
| **兼容策略** | 新增安全管线 |
| **验收命令** | `pytest tests/unit/gateway/test_content_pipeline.py -v` (安全检查子集 5 态转换全覆盖) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 安全检查子集状态转换测试通过 |
| **风险** | 依赖: Gateway 安全中间件 / 数据: security_status != safe 的 media_id 不可被引用 (LAW 约束) / 兼容: 新增安全管线 / 回滚: git revert |
| **决策记录** | 决策: security_status 6 态模型安全检查子集 (ADR-051) / 理由: 三层拦截保障内容安全, 恶意内容 quarantined / 来源: ADR-051, 架构文档 06 Section 1.6 |

> **security_status 6 态模型 (ADR-051)**: `pending` -> `scanning` -> `safe` / `rejected` / `quarantined` -> `expired`
> 本卡负责安全检查子集 (pending / scanning / safe / rejected / quarantined)，`expired` 态由生命周期管理层处理
> 各层职责: 上传入 `pending` (G2-6) -> 本卡执行 `scanning` 并输出 `safe`/`rejected`/`quarantined` -> 后续处理 (T3-2/T3-3) -> 存储 (I3-3)

> 矩阵条目: OS3-1 | M-Track: MM1-5 (security_status 三层拦截复用此管线)

### TASK-OS3-2: 审计闭环 (所有 CRUD + 权限变更)

| 字段 | 内容 |
|------|------|
| **目标** | 抽样 10 个关键操作 -> 全部有审计记录 |
| **范围 (In Scope)** | `tests/audit/test_audit_coverage.py` |
| **范围外 (Out of Scope)** | 审计写入实现 / 审计表 DDL / 前端审计查看 / 合规删除 |
| **依赖** | Infra (I1-5) |
| **兼容策略** | 纯测试验证 |
| **验收命令** | `pytest tests/audit/test_audit_coverage.py -v` |
| **回滚方案** | 不适用 |
| **证据** | 审计覆盖率测试通过 |
| **风险** | 依赖: I1-5 (audit_events 表) / 数据: 审计覆盖率不足=合规风险 / 兼容: 纯测试验证 / 回滚: 不适用 |
| **决策记录** | 决策: 审计闭环验证 (抽样 10 个关键 CRUD + 权限变更) / 理由: 审计覆盖率 100% 为合规硬指标 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS3-2

### TASK-OS3-3: 知识写入安全校验 (XSS/注入防护)

| 字段 | 内容 |
|------|------|
| **目标** | 知识条目含脚本标签 -> 写入时被净化 |
| **范围 (In Scope)** | `src/knowledge/security/sanitizer.py`, `tests/unit/knowledge/test_sanitizer.py` |
| **范围外 (Out of Scope)** | Knowledge 业务逻辑 / 前端输入净化 / CSP 配置 / 安全扫描 CI |
| **依赖** | Knowledge |
| **兼容策略** | 新增安全层 |
| **验收命令** | `pytest tests/unit/knowledge/test_sanitizer.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 注入防护测试通过 |
| **风险** | 依赖: Knowledge 层 / 数据: 未净化知识条目=XSS/注入漏洞 / 兼容: 新增安全层 / 回滚: git revert |
| **决策记录** | 决策: 知识写入安全校验 (XSS/注入防护) / 理由: 知识条目是用户输入, 需净化后存储 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS3-3

### TASK-OS3-4: Resolver 查询审计 (who/when/what/why)

| 字段 | 内容 |
|------|------|
| **目标** | 每次 Resolver 查询 -> 审计日志含 4W |
| **范围 (In Scope)** | `src/knowledge/resolver/audit.py`, `tests/unit/knowledge/test_resolver_audit.py` |
| **范围外 (Out of Scope)** | Resolver 查询逻辑 / Knowledge 业务实现 / 前端查询 UI / 告警规则 |
| **依赖** | Knowledge |
| **兼容策略** | 新增审计层 |
| **验收命令** | `pytest tests/unit/knowledge/test_resolver_audit.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 4W 审计测试通过 |
| **风险** | 依赖: Knowledge Resolver / 数据: 查询审计需脱敏, 禁止记录完整知识内容 / 兼容: 新增审计层 / 回滚: git revert |
| **决策记录** | 决策: Resolver 查询审计 (who/when/what/why) / 理由: 知识访问可追溯, 支持安全审计 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS3-4

### TASK-OS3-5: API 限流告警 (429 频率监控)

| 字段 | 内容 |
|------|------|
| **目标** | 429 响应率超阈值 -> 告警 |
| **范围 (In Scope)** | `deploy/monitoring/alerts.yml` (追加) |
| **范围外 (Out of Scope)** | 限流实现逻辑 / Gateway API 实现 / 前端限流展示 / 基础告警规则 |
| **依赖** | Gateway |
| **兼容策略** | 纯新增告警 |
| **验收命令** | [ENV-DEP] `curl -s localhost:9090/api/v1/alerts \| python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"` staging: 429 限流告警规则可触发 |
| **回滚方案** | 删除规则 |
| **证据** | 告警截图 |
| **风险** | 依赖: Gateway 限流中间件 / 数据: 429 频率异常=潜在攻击信号 / 兼容: 纯新增告警 / 回滚: 删除规则 |
| **决策记录** | 决策: API 限流告警 (429 频率监控) / 理由: 异常限流=潜在滥用或攻击, 需及时发现 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS3-5

---

## Phase 4 -- SLI/SLO + 告警分级 + 故障注入

### TASK-OS4-1: 7 项 Brain SLI 定义 + Grafana 看板

| 字段 | 内容 |
|------|------|
| **目标** | injection_precision / retrieval_recall 等 7 项指标可视 |
| **范围 (In Scope)** | Grafana dashboard JSON |
| **范围外 (Out of Scope)** | Brain 业务逻辑 / SLI 指标采集实现 / 告警规则 / SLO 定义 |
| **依赖** | Prometheus + Grafana |
| **兼容策略** | 纯新增看板 |
| **验收命令** | [ENV-DEP] `curl -s localhost:3000/api/dashboards/uid/brain-sli \| python3 -c "import sys,json; d=json.load(sys.stdin); assert 'dashboard' in d"` staging: Grafana 7 项 Brain SLI 指标可视 |
| **回滚方案** | 删除看板 JSON |
| **证据** | 7 项指标全部可视 |
| **风险** | 依赖: Prometheus + Grafana 运行时 / 数据: SLI 指标需准确, 错误指标=误导决策 / 兼容: 纯新增看板 / 回滚: 删除看板 JSON |
| **决策记录** | 决策: 7 项 Brain SLI Grafana 看板 / 理由: Brain 核心质量可视化, 支持 SLO 达成监控 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS4-1

### TASK-OS4-2: SLO 定义

| 字段 | 内容 |
|------|------|
| **目标** | API P95 < 500ms, 错误率 < 0.1%, 可用性 > 99.5% |
| **范围 (In Scope)** | `docs/slo/slo_definition.md`, 告警规则 |
| **范围外 (Out of Scope)** | SLI 埋点实现 / Grafana 看板 / 告警通知渠道 / 性能优化 |
| **依赖** | -- |
| **兼容策略** | 纯文档 + 告警 |
| **验收命令** | [ENV-DEP] `test -f docs/slo/slo_definition.md && curl -s localhost:9090/api/v1/rules \| python3 -c "import sys,json; print('ok')"` staging: SLO 定义存在且告警规则对齐 |
| **回滚方案** | 不适用 |
| **证据** | SLO 文档存在 |
| **风险** | 依赖: N/A / 数据: SLO 定义需基于基线数据, 过高/过低均不合理 / 兼容: 纯文档 + 告警 / 回滚: 不适用 |
| **决策记录** | 决策: SLO 三指标 (P95<500ms, 错误率<0.1%, 可用性>99.5%) / 理由: 量化服务质量目标, 驱动优先级决策 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS4-2

### TASK-OS4-3: 告警分级 (P0/P1/P2) + 升级规则

| 字段 | 内容 |
|------|------|
| **目标** | P0-Critical/P1-Warning/P2-Info 分级，升级流程清晰 |
| **范围 (In Scope)** | `docs/ops/alert_levels.md` |
| **范围外 (Out of Scope)** | 告警规则实现 / 通知渠道配置 / SLO 定义 / Grafana 看板 |
| **依赖** | -- |
| **兼容策略** | 纯文档 |
| **验收命令** | `test -f docs/ops/alert_levels.md && grep -qc "P0\|P1\|P2" docs/ops/alert_levels.md && echo PASS` |
| **回滚方案** | 不适用 |
| **证据** | 告警分级文档存在 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯文档 / 兼容: 纯文档 / 回滚: 不适用 |
| **决策记录** | 决策: 告警分级 P0/P1/P2 + 升级规则 / 理由: 标准化事件响应, 明确升级路径 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS4-3

### TASK-OS4-4: 全链路 trace_id 验证

| 字段 | 内容 |
|------|------|
| **目标** | 一次对话的 trace_id 在 Gateway -> Brain -> Memory -> Tool 所有层日志中可查 |
| **范围 (In Scope)** | E2E 测试 |
| **范围外 (Out of Scope)** | trace_id 生成逻辑 / 日志中间件实现 / Grafana Trace 看板 / 业务层逻辑 |
| **依赖** | -- |
| **兼容策略** | 纯测试验证 |
| **验收命令** | [ENV-DEP] `pytest tests/e2e/cross/test_trace_id_propagation.py -v` (一次对话全链路 trace_id 可查) |
| **回滚方案** | 不适用 |
| **证据** | 全链路日志截图 |
| **风险** | 依赖: 全栈部署就绪 / 数据: trace_id 断裂=排障困难 / 兼容: 纯测试验证 / 回滚: 不适用 |
| **决策记录** | 决策: 全链路 trace_id 传播验证 / 理由: 跨层日志关联是排障基础 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS4-4

### TASK-OS4-5: 故障注入 -- 删除管线每步注入失败

| 字段 | 内容 |
|------|------|
| **目标** | 8 态状态机每步注入故障 -> 正确恢复 |
| **范围 (In Scope)** | `tests/chaos/test_deletion_fault.py` |
| **范围外 (Out of Scope)** | 删除管线业务实现 / Memory Core 内部 / 前端实现 / 监控告警 |
| **依赖** | 删除管线 (MC4-1) |
| **兼容策略** | 纯测试 |
| **验收命令** | [ENV-DEP] `pytest tests/chaos/test_deletion_fault.py -v` |
| **回滚方案** | 不适用 |
| **证据** | 8 步注入全通过 |
| **风险** | 依赖: MC4-1 (删除管线) / 数据: 故障注入需隔离环境 / 兼容: 纯测试 / 回滚: 不适用 |
| **决策记录** | 决策: 删除管线故障注入测试 (8 步) / 理由: 不可逆操作必须排在最后 (LAW 约束), 每步需可恢复 / 来源: 架构文档 06 Section 1.6 |

> 矩阵条目: OS4-5

### TASK-OS4-6: 故障注入 -- LLM Provider 不可用

| 字段 | 内容 |
|------|------|
| **目标** | 主 Provider down -> fallback -> 用户无感 |
| **范围 (In Scope)** | `tests/chaos/test_llm_fault.py` |
| **范围外 (Out of Scope)** | LLM 调用实现 / Model Registry 内部 / 前端实现 / 告警规则 |
| **依赖** | Model Registry (T2-2) |
| **兼容策略** | 纯测试 |
| **验收命令** | [ENV-DEP] `pytest tests/chaos/test_llm_fault.py -v` |
| **回滚方案** | 不适用 |
| **证据** | fallback 测试通过 |
| **风险** | 依赖: T2-2 (Model Registry) / 数据: fallback 失败=服务中断 / 兼容: 纯测试 / 回滚: 不适用 |
| **决策记录** | 决策: LLM Provider 故障注入测试 / 理由: 多 Provider fallback 是高可用基线 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS4-6

### TASK-OS4-7: 渗透测试基线 (OWASP Top 10)

| 字段 | 内容 |
|------|------|
| **目标** | 渗透测试报告无 Critical/High 漏洞 |
| **范围 (In Scope)** | `docs/security/pentest_report.md` |
| **范围外 (Out of Scope)** | 漏洞修复实现 / 安全扫描 CI / 运行时防护 / 告警配置 |
| **依赖** | -- |
| **兼容策略** | 纯文档 |
| **验收命令** | [ENV-DEP] `test -f docs/security/pentest_report.md && grep -qcP "Critical\|High" docs/security/pentest_report.md && exit 1 \|\| echo PASS` staging: 渗透测试报告无 Critical/High |
| **回滚方案** | 不适用 |
| **证据** | 渗透测试报告 |
| **风险** | 依赖: N/A / 数据: 渗透测试需授权, 测试环境隔离 / 兼容: 纯文档 / 回滚: 不适用 |
| **决策记录** | 决策: OWASP Top 10 渗透测试基线 / 理由: 安全合规要求, 上线前漏洞验证 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS4-7

### TASK-OS4-8: 前端 a11y 无障碍审计

| 字段 | 内容 |
|------|------|
| **目标** | axe-core 扫描关键页面 -> 0 critical violations |
| **范围 (In Scope)** | `tests/a11y/`, CI 配置 |
| **范围外 (Out of Scope)** | 前端业务逻辑 / 后端 API / XSS 防护 / 安全扫描 |
| **依赖** | FE-Web |
| **兼容策略** | 新增 a11y CI |
| **验收命令** | [ENV-DEP] `pnpm a11y:check` (0 critical violations) |
| **回滚方案** | `git revert <commit>` |
| **证据** | axe-core 报告 |
| **风险** | 依赖: FE-Web 页面就绪 / 数据: N/A -- 纯无障碍检查 / 兼容: 新增 a11y CI / 回滚: git revert |
| **决策记录** | 决策: axe-core 无障碍审计 CI 门禁 / 理由: 无障碍合规要求, 关键页面 0 critical violations / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS4-8

---

## Phase 5 -- 自动偏差审计 + 合规

### TASK-OS5-1: 三 SSOT 自动一致性检查

| 字段 | 内容 |
|------|------|
| **目标** | CI 自动检测 Decision/Runtime/Delivery 3 个 SSOT 偏差 |
| **范围 (In Scope)** | `scripts/check_ssot_drift.sh` |
| **范围外 (Out of Scope)** | SSOT 内容定义 / 偏差修复 / Guard 阻断策略 / 审计报告 |
| **依赖** | CI |
| **兼容策略** | 新增检查脚本 |
| **验收命令** | [ENV-DEP] `bash scripts/check_ssot_drift.sh` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 偏差自动检出 |
| **风险** | 依赖: CI 运行时 / 数据: SSOT 偏差=架构腐化信号 / 兼容: 新增检查脚本 / 回滚: git revert |
| **决策记录** | 决策: 三 SSOT 自动一致性检查 / 理由: Decision/Runtime/Delivery SSOT 需保持一致 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS5-1

### TASK-OS5-2: Guard 自动阻断策略

| 字段 | 内容 |
|------|------|
| **目标** | 违规代码 -> CI 自动阻断 + 人话化错误 (问题/位置/影响/怎么修/参考) |
| **范围 (In Scope)** | `scripts/guard_policy.sh`, CI 配置 |
| **范围外 (Out of Scope)** | SSOT 检查 / Exception Register / 审计报告 / 业务层逻辑 |
| **依赖** | CI |
| **兼容策略** | 新增阻断策略 |
| **验收命令** | [ENV-DEP] CI-job: guard-checks (提交违规代码 -> 阻断 -> 输出含问题/位置/影响/修复/参考 5 段) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 阻断输出截图 |
| **风险** | 依赖: CI 运行时 / 数据: N/A -- 纯阻断策略 / 兼容: 新增阻断策略 / 回滚: git revert |
| **决策记录** | 决策: Guard 自动阻断 + 人话化错误输出 / 理由: 开发者友好的错误信息, 降低修复时间 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS5-2

### TASK-OS5-3: Exception Register 到期自动审计

| 字段 | 内容 |
|------|------|
| **目标** | 到期例外 -> 自动标记 + 通知 owner |
| **范围 (In Scope)** | `src/governance/exception_audit.py`, Cron Job |
| **范围外 (Out of Scope)** | Exception Register 内容管理 / 通知渠道配置 / 审计报告 / SSOT 检查 |
| **依赖** | -- |
| **兼容策略** | 新增审计逻辑 |
| **验收命令** | [ENV-DEP] `pytest tests/unit/governance/test_exception_expiry.py -v` staging: 到期例外自动通知 owner |
| **回滚方案** | 禁用 Cron Job |
| **证据** | 审计逻辑验证 |
| **风险** | 依赖: N/A / 数据: 到期例外未处理=合规风险 / 兼容: 新增审计逻辑 / 回滚: 禁用 Cron Job |
| **决策记录** | 决策: Exception Register 到期自动审计 / 理由: 例外项有生命周期, 到期未处理需自动告警 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS5-3

### TASK-OS5-4: 月度架构偏差审计模板 + 自动产出

| 字段 | 内容 |
|------|------|
| **目标** | `make audit-report` -> 生成 Markdown 报告 |
| **范围 (In Scope)** | `scripts/generate_audit_report.sh` |
| **范围外 (Out of Scope)** | SSOT 检查 / Exception 审计 / 合规报告 / Guard 策略 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `make audit-report` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 报告产出 |
| **风险** | 依赖: N/A / 数据: 报告需脱敏 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: 月度架构偏差审计模板 + 自动产出 / 理由: 定期架构健康检查, 防止架构腐化 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS5-4

### TASK-OS5-5: GDPR/PIPL 合规报告自动生成

| 字段 | 内容 |
|------|------|
| **目标** | `make compliance-report` -> 含数据保留/删除/审计统计 |
| **范围 (In Scope)** | `scripts/compliance_report.sh` |
| **范围外 (Out of Scope)** | 删除管线实现 / 审计写入逻辑 / 架构偏差审计 / SSOT 检查 |
| **依赖** | 删除管线 + 审计 |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `make compliance-report` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 合规报告截图 |
| **风险** | 依赖: 删除管线 + 审计就绪 / 数据: 合规报告需准确, 错误数据=合规风险 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: GDPR/PIPL 合规报告自动生成 / 理由: 合规审计自动化, 降低人工成本 / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS5-5

### TASK-OS5-6: 安全事件响应手册 (Runbook)

| 字段 | 内容 |
|------|------|
| **目标** | 至少覆盖数据泄露/密钥泄露/DDoS/供应链攻击 4 场景 |
| **范围 (In Scope)** | `docs/security/incident_runbook.md` |
| **范围外 (Out of Scope)** | 安全防护实现 / 告警规则 / 合规报告 / 渗透测试 |
| **依赖** | -- |
| **兼容策略** | 纯文档 |
| **验收命令** | `test -f docs/security/incident_runbook.md && test $(grep -c "数据泄露\|密钥泄露\|DDoS\|供应链" docs/security/incident_runbook.md) -ge 4 && echo PASS` |
| **回滚方案** | 不适用 |
| **证据** | Runbook 文件存在 |
| **风险** | 依赖: N/A / 数据: N/A -- 纯文档 / 兼容: 纯文档 / 回滚: 不适用 |
| **决策记录** | 决策: 安全事件响应手册 (4 场景) / 理由: 标准化事件响应流程, 降低 MTTR / 来源: 架构文档 07 Section 2 |

> 矩阵条目: OS5-6

### TASK-MM3-1: 版权风险检测 [M-Track M3]

| 字段 | 内容 |
|------|------|
| **目标** | 已知版权图片被标记，检出率 >= 90% |
| **范围 (In Scope)** | `src/gateway/security/copyright_detect.py`, `tests/unit/gateway/test_copyright_detect.py` |
| **范围外 (Out of Scope)** | Knowledge 内容索引 / 安全管线内部 / 前端版权标记 UI / 法律合规判定 |
| **依赖** | Knowledge 层 (K3-5 Resolver), 安全管线 (OS3-1) |
| **兼容策略** | 新增检测模块；检测失败降级为 warning 不阻断上传 |
| **验收命令** | `pytest tests/unit/gateway/test_copyright_detect.py -v` (已知版权检出率 >= 90%) |
| **回滚方案** | `git revert <commit>` -- 检测模块移除，文件直接通过 |
| **证据** | 版权检测逻辑单测通过 |
| **风险** | 依赖: K3-5 + OS3-1 双依赖 / 数据: 检测失败降级为 warning, 不阻断上传 / 兼容: 新增检测模块 / 回滚: git revert, 模块移除 |
| **决策记录** | 决策: 版权风险检测模块 (检出率>=90%) / 理由: 版权合规预防, 降级为 warning 保障可用性 / 来源: M-Track M3, 架构文档 07 Section 2 |

> 矩阵条目: MM3-1 | M-Track: M3 成熟期
> 主卡归属: Obs & Security (版权合规检测) | 引用层: Knowledge (内容源), Tool (检测工具)

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
