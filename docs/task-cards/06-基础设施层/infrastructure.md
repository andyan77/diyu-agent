# Infrastructure 层任务卡集

> 架构文档: `docs/architecture/06-基础设施层.md`
> 里程碑来源: `docs/governance/milestone-matrix-backend.md` Section 7
> 影响门禁: `src/infra/**`, `alembic/**`, `docker-compose*.yml` -> check_migration + check_layer_deps
> 渐进式组合 Step 6

---

## Phase 0 -- 开发环境

### TASK-I0-1: Docker Compose 全栈环境

| 字段 | 内容 |
|------|------|
| **目标** | `docker-compose up` 一键启动 PG/Neo4j/Qdrant/Redis/MinIO，5 个服务全部 healthy |
| **范围 (In Scope)** | `docker-compose.yml`, `docker-compose.dev.yml` |
| **范围外 (Out of Scope)** | 业务层逻辑 (Brain/Skill/Tool/Knowledge) / 前端实现 / CI/CD 流水线 / 生产环境编排 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | [ENV-DEP] `docker-compose up -d && docker-compose ps` (5 个服务全部 healthy) |
| **回滚方案** | `docker-compose down -v` |
| **证据** | 全部容器 healthy 截图 |
| **风险** | 依赖: Docker 运行时环境 / 数据: N/A -- 开发环境容器, 无生产数据 / 兼容: 纯新增 / 回滚: docker-compose down -v |
| **决策记录** | 决策: 5 服务 (PG/Neo4j/Qdrant/Redis/MinIO) 统一 Docker Compose 管理 / 理由: 一键启动开发环境, 降低入门成本 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I0-1 | V-x: X0-3

### TASK-I0-2: pyproject.toml + uv.lock

| 字段 | 内容 |
|------|------|
| **目标** | `uv sync` 安装所有依赖无报错 |
| **范围 (In Scope)** | `pyproject.toml`, `uv.lock` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端依赖管理 / CI/CD 流水线 / Docker 配置 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `uv sync && echo PASS` (0 error) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 依赖解析无冲突 |
| **风险** | 依赖: N/A -- 无外部依赖 / 数据: N/A -- 纯配置文件 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: uv 作为 Python 包管理器 / 理由: 速度快, lock 文件确保可重现构建 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I0-2 | V-x: X0-2

### TASK-I0-3: Alembic Migration 骨架

| 字段 | 内容 |
|------|------|
| **目标** | `alembic upgrade head` 无报错，Migration 链完整 |
| **范围 (In Scope)** | `alembic/`, `alembic.ini` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 具体表 DDL (后续任务) / 前端实现 / CI/CD 流水线 |
| **依赖** | TASK-I0-1 (PG) |
| **兼容策略** | 纯新增骨架 |
| **验收命令** | [ENV-DEP] `alembic upgrade head && echo PASS` |
| **回滚方案** | `alembic downgrade base` |
| **证据** | upgrade 0 error |
| **风险** | 依赖: I0-1 (PG 容器) 未就绪时阻塞 / 数据: N/A -- 纯骨架, 无业务数据 / 兼容: 纯新增 / 回滚: alembic downgrade base |
| **决策记录** | 决策: Alembic 作为数据库迁移工具 / 理由: Python 生态标准, 支持 upgrade/downgrade 双向迁移 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I0-3

### TASK-I0-4: Makefile 标准命令

| 字段 | 内容 |
|------|------|
| **目标** | `make help` 列出 dev/test/lint/typecheck/migrate 等命令 |
| **范围 (In Scope)** | `Makefile` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端构建命令 / CI/CD 流水线 / Docker 编排 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `make help` (>= 5 个命令可用) |
| **回滚方案** | `git revert <commit>` |
| **证据** | help 输出截图 |
| **风险** | 依赖: N/A -- 无外部依赖 / 数据: N/A -- 纯构建工具 / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: Makefile 统一开发命令入口 / 理由: 降低 onboarding 门槛, 标准化 dev/test/lint/migrate 命令 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I0-4

### TASK-I0-5: .env.example

| 字段 | 内容 |
|------|------|
| **目标** | 包含所有必需环境变量及注释 |
| **范围 (In Scope)** | `.env.example` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 真实密钥管理 / CI/CD 流水线 / 前端环境变量 |
| **依赖** | -- |
| **兼容策略** | 纯新增 |
| **验收命令** | `grep -c TBD .env.example` (= 0, 无未定义占位) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 所有必需变量有文档 |
| **风险** | 依赖: N/A -- 无外部依赖 / 数据: 禁止包含真实密钥 (安全红线) / 兼容: 纯新增 / 回滚: git revert |
| **决策记录** | 决策: .env.example 模板化所有必需变量 / 理由: 环境变量文档化, 降低配置遗漏风险 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I0-5

### TASK-I0-6: ruff + mypy --strict 配置

| 字段 | 内容 |
|------|------|
| **目标** | `make lint && make typecheck` 通过，0 error 0 warning |
| **范围 (In Scope)** | `pyproject.toml` (ruff/mypy 配置段) |
| **范围外 (Out of Scope)** | 业务层代码实现 / 前端 ESLint 配置 / CI/CD 流水线 / 测试框架配置 |
| **依赖** | TASK-I0-2 |
| **兼容策略** | 纯新增配置 |
| **验收命令** | `make lint && make typecheck` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 配置文件正确 |
| **风险** | 依赖: I0-2 (pyproject.toml) / 数据: N/A -- 纯配置 / 兼容: 纯新增配置段 / 回滚: git revert |
| **决策记录** | 决策: ruff + mypy --strict 作为代码质量门禁 / 理由: 静态分析前移, 阻止低质量代码入库 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I0-6 | V-x: X0-2

### TASK-I0-7: ContentBlock Schema v1.1 + JSON Schema 验证 (ADR-043) [M-Track M0]

| 字段 | 内容 |
|------|------|
| **目标** | 定义 ContentBlock 多模态数据模型 v1.1，通过 JSON Schema 验证，为全层多模态内容提供统一类型 |
| **范围 (In Scope)** | `src/shared/types/content_block.py`, `schemas/content_block.v1.1.json`, `tests/unit/shared/test_content_block.py` |
| **范围外 (Out of Scope)** | 业务层消费逻辑 (Brain/Skill/Tool) / 前端渲染组件 / 存储 Adapter 实现 / LLM 模型调用 |
| **依赖** | -- |
| **兼容策略** | 纯新增 Schema 定义；v1.0 不存在，无兼容问题 |
| **验收命令** | `mypy --strict src/shared/types/content_block.py && python -m jsonschema -i tests/fixtures/sample_block.json schemas/content_block.v1.1.json && echo PASS` |
| **回滚方案** | `git revert <commit>` |
| **证据** | mypy + JSON Schema 验证通过 |
| **风险** | 依赖: N/A -- 纯类型定义 / 数据: Schema 一旦发布需保持向后兼容 / 兼容: v1.0 不存在, 无兼容问题 / 回滚: git revert |
| **决策记录** | 决策: ContentBlock v1.1 作为全层多模态统一类型 / 理由: 统一数据模型避免各层自定义导致不一致 / 来源: ADR-043, 架构文档 08 附录 |

> 矩阵条目: MM0-1 | M-Track: MM0-1
> 主卡归属: Infrastructure (shared types) | 引用层: Brain, Gateway, Tool

### TASK-I0-8: personal_media_objects / enterprise_media_objects DDL + RLS [M-Track M0]

| 字段 | 内容 |
|------|------|
| **目标** | 两张媒体对象表存在 + RLS 租户隔离通过，表结构对齐 08-附录.md DDL 定义 |
| **范围 (In Scope)** | `alembic/versions/xxx_media_objects.py`, `tests/isolation/test_media_rls.py` |
| **范围外 (Out of Scope)** | 业务层媒体处理逻辑 / ObjectStorage Adapter / 前端上传组件 / 安全扫描流水线 |
| **依赖** | TASK-I0-3 (Alembic), TASK-I1-3 (RLS 基线) |
| **兼容策略** | 纯新增 DDL；Phase 1 RLS 策略基线扩展至媒体表 |
| **验收命令** | [ENV-DEP] `alembic upgrade head && pytest tests/isolation/test_media_rls.py -v` (2 张表存在 + RLS 隔离通过) |
| **回滚方案** | `alembic downgrade -1` |
| **证据** | 表存在 + 租户隔离测试通过 |
| **风险** | 依赖: I0-3 (Alembic) + I1-3 (RLS 基线) 双依赖 / 数据: personal/enterprise 物理隔离 (LAW 约束) / 兼容: 纯新增 DDL / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: personal_media_objects 与 enterprise_media_objects 物理分表 / 理由: 个人/企业媒体隔离, 删除策略不同 (LAW 约束) / 来源: 架构文档 06 Section 1.6, 08 附录 DDL |

> 矩阵条目: MM0-3 | M-Track: MM0-3
> 主卡归属: Infrastructure (DDL) | 引用层: Knowledge (FK 联动), Gateway (上传写入)

---

## Phase 1 -- 安全底座（核心交付 Phase）

### TASK-I1-1: organizations + users + org_members DDL

| 字段 | 内容 |
|------|------|
| **目标** | `alembic upgrade head` -> 3 张表存在，表结构对齐架构文档 |
| **范围 (In Scope)** | `alembic/versions/xxx_org_model.py` |
| **范围外 (Out of Scope)** | 业务层逻辑 / RBAC 权限实现 / RLS 策略 / 前端组织管理 UI / 审计逻辑 |
| **依赖** | TASK-I0-3 |
| **兼容策略** | 纯新增 DDL |
| **验收命令** | [ENV-DEP] `alembic upgrade head && psql -c "\\dt" | grep -c "organizations\|users\|org_members"` (= 3) |
| **回滚方案** | `alembic downgrade -1` |
| **证据** | 3 张表全部存在 |
| **风险** | 依赖: I0-3 (Alembic 骨架) / 数据: 组织树固定 5 层 (LAW 约束), ltree 路径需维护一致性 / 兼容: 纯新增 DDL / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: organizations + users + org_members 三表组织模型 + ltree 物化路径 / 理由: 组织树是系统基础数据模型, ltree 支持高效层级查询 / 来源: 架构文档 06 Section 1.1-1.2 |

> 矩阵条目: I1-1 | V-x: X1-1

### TASK-I1-2: org_settings 继承链 (is_locked BRIDGE 机制)

| 字段 | 内容 |
|------|------|
| **目标** | 上级 lock 的配置下级不可覆盖 |
| **范围 (In Scope)** | `src/infra/org/settings.py`, `tests/unit/infra/test_org_settings.py` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端 Admin 配置面板 / RBAC 权限检查 / 审计写入 |
| **依赖** | TASK-I1-1 |
| **兼容策略** | 新增继承逻辑 |
| **验收命令** | `pytest tests/unit/infra/test_org_settings.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 继承逻辑单测通过 |
| **风险** | 依赖: I1-1 (组织模型 DDL) / 数据: is_locked 机制需正确传递, 错误可导致配置泄漏 / 兼容: 新增继承逻辑, 不影响已有表结构 / 回滚: git revert |
| **决策记录** | 决策: BRIDGE 机制 -- is_locked 对当前组织=RULE, 对子组织=LAW / 理由: 上级锁定配置不可被下级覆盖, 保障管控一致性 / 来源: ADR-029, 架构文档 06 Section 1.5-1.6 |

> 矩阵条目: I1-2 | V-x: X1-1 | V-fb: XF3-3

### TASK-I1-3: RLS 策略基线 (所有业务表)

| 字段 | 内容 |
|------|------|
| **目标** | `SET LOCAL app.org_id = 'A'; SELECT * FROM memory_items;` 只返回 A 的数据，跨租户泄露 = 0 |
| **范围 (In Scope)** | `alembic/versions/xxx_rls.py`, `tests/isolation/test_rls.py` |
| **范围外 (Out of Scope)** | 业务层数据访问逻辑 / 前端实现 / RBAC 权限逻辑 / 应用层鉴权 |
| **依赖** | TASK-I1-1 |
| **兼容策略** | 新增 RLS 策略 |
| **验收命令** | [ENV-DEP] `pytest tests/isolation/test_rls.py -v` (正向+反向隔离测试) |
| **回滚方案** | `alembic downgrade -1` (移除 RLS 策略) |
| **证据** | 跨租户泄露 = 0 |
| **风险** | 依赖: I1-1 (组织模型 DDL) / 数据: RLS 策略是数据隔离核心 (LAW 约束), 配置错误=数据泄露 / 兼容: 新增 RLS 策略 / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: PostgreSQL RLS 作为多租户数据隔离基座 / 理由: 数据库级强制隔离, 应用层无法绕过 (LAW 约束) / 来源: 架构文档 06 Section 1.6 |

> 矩阵条目: I1-3 | V-x: X1-1

### TASK-I1-4: RBAC 权限检查骨架

| 字段 | 内容 |
|------|------|
| **目标** | 11 列权限码 -> 角色 -> 用户链路通过 |
| **范围 (In Scope)** | `alembic/versions/xxx_rbac.py`, `src/infra/auth/rbac.py`, `tests/unit/infra/test_rbac.py` |
| **范围外 (Out of Scope)** | 业务层鉴权逻辑 / Gateway JWT 验证 / 前端权限 UI / 审计写入 |
| **依赖** | TASK-I1-1 |
| **兼容策略** | 新增 RBAC 表 + 逻辑 |
| **验收命令** | `pytest tests/unit/infra/test_rbac.py -v` (权限链路通过) |
| **回滚方案** | `alembic downgrade -1` |
| **证据** | 映射完整性单测通过 |
| **风险** | 依赖: I1-1 (组织模型 DDL) / 数据: 5 角色定义为 LAW 约束, 权限判定公式不可参数化 / 兼容: 新增 RBAC 表 + 逻辑 / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: RBAC 5 角色 + 11 权限码 + 组织树约束判定 / 理由: 权限判定基于 permission codes 解耦角色硬编码, 为未来自定义角色留路径 / 来源: 架构文档 06 Section 1.3-1.4 |

> 矩阵条目: I1-4 | V-x: X1-2

### TASK-I1-5: audit_events 表 + 审计写入

| 字段 | 内容 |
|------|------|
| **目标** | 关键操作后 audit_events 有记录，覆盖率 100% |
| **范围 (In Scope)** | `alembic/versions/xxx_audit.py`, `src/infra/audit/writer.py`, `tests/unit/infra/test_audit.py` |
| **范围外 (Out of Scope)** | 业务层审计触发逻辑 / 前端审计查看 UI / 可观测性日志 / PIPL 合规删除 |
| **依赖** | TASK-I1-1 |
| **兼容策略** | 新增审计表 + 写入逻辑 |
| **验收命令** | `pytest tests/unit/infra/test_audit.py -v` |
| **回滚方案** | `alembic downgrade -1` |
| **证据** | 关键操作审计覆盖率 100% |
| **风险** | 依赖: I1-1 (组织模型 DDL) / 数据: 审计记录不可篡改, 需 append-only 写入 / 兼容: 新增审计表 / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: audit_events 表 + 写入器实现审计追踪 / 理由: 关键操作可追溯, PIPL/GDPR 合规要求 / 来源: 架构文档 06 Section 1 |

> 矩阵条目: I1-5 | V-x: X1-3

### TASK-I1-6: event_outbox 表 + Outbox Pattern

| 字段 | 内容 |
|------|------|
| **目标** | 写入 outbox -> poller 投递 -> at-least-once 保证，投递成功率 >= 99.9% |
| **范围 (In Scope)** | `alembic/versions/xxx_outbox.py`, `src/infra/events/outbox.py`, `tests/unit/infra/test_outbox.py` |
| **范围外 (Out of Scope)** | 业务层事件消费逻辑 / 前端实现 / Event Mesh 高级演进 / 消息队列中间件 |
| **依赖** | TASK-I1-1 |
| **兼容策略** | 新增 Outbox 机制 |
| **验收命令** | `pytest tests/unit/infra/test_outbox.py -v` |
| **回滚方案** | `alembic downgrade -1` |
| **证据** | at-least-once 单测通过 |
| **风险** | 依赖: I1-1 (组织模型 DDL) / 数据: outbox 表需与业务写入同事务, 保证 at-least-once / 兼容: 新增 Outbox 机制 / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: PG Outbox Pattern 实现事件可靠投递 / 理由: 异构存储禁止假设分布式事务 (LAW 约束), Outbox 保证事件不丢 / 来源: 架构文档 06 Section 1.6 |

> 矩阵条目: I1-6

### TASK-I1-7: secret scanning + SAST + 依赖漏洞扫描

| 字段 | 内容 |
|------|------|
| **目标** | CI 中 3 项扫描通过，0 Critical 漏洞 |
| **范围 (In Scope)** | `.github/workflows/ci.yml` (扫描步骤) |
| **范围外 (Out of Scope)** | 业务层代码实现 / 前端安全扫描 / 运行时安全监控 / 渗透测试 |
| **依赖** | CI (D0-4) |
| **兼容策略** | 新增 CI 步骤 |
| **验收命令** | [ENV-DEP] CI-job: security-scan (gitleaks + semgrep + pip-audit 3 项扫描全通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 3 项独立验证 |
| **风险** | 依赖: D0-4 (CI 流水线) / 数据: N/A -- 纯扫描逻辑 / 兼容: 新增 CI 步骤 / 回滚: git revert |
| **决策记录** | 决策: secret scanning + SAST + 依赖漏洞扫描三道防线 / 理由: 安全前移, CI 阶段拦截已知漏洞 / 来源: 架构文档 06 Section 1 |

> 矩阵条目: I1-7 | V-x: X1-3

---

## Phase 2 -- 运行时基础

### TASK-I2-1: Redis 缓存 + Session 管理

| 字段 | 内容 |
|------|------|
| **目标** | 写入缓存 -> TTL 过期 -> 自动清除 |
| **范围 (In Scope)** | `src/infra/cache/redis.py`, `tests/unit/infra/test_redis.py` |
| **范围外 (Out of Scope)** | 业务层缓存策略 / Celery 任务队列 / 前端缓存 / Session 业务逻辑 |
| **依赖** | Redis 7+ (docker-compose) |
| **兼容策略** | 新增缓存层 |
| **验收命令** | [ENV-DEP] `pytest tests/unit/infra/test_redis.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | TTL 逻辑单测通过 |
| **风险** | 依赖: Redis 7+ (Docker Compose) / 数据: 缓存数据非持久化, 丢失可重建 / 兼容: 新增缓存层 / 回滚: git revert |
| **决策记录** | 决策: Redis 统一缓存 + Session 管理 / 理由: 高性能 KV 存储, TTL 原生支持 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I2-1

### TASK-I2-2: Celery Worker + Redis Broker

| 字段 | 内容 |
|------|------|
| **目标** | 发送异步任务 -> Worker 执行 -> 结果回写 |
| **范围 (In Scope)** | `src/infra/tasks/celery_app.py`, `tests/unit/infra/test_celery.py` |
| **范围外 (Out of Scope)** | 具体业务任务实现 / 前端任务状态展示 / 消息队列高级配置 / 监控告警 |
| **依赖** | TASK-I2-1 |
| **兼容策略** | 新增异步任务框架 |
| **验收命令** | [ENV-DEP] `pytest tests/unit/infra/test_celery.py -v` (任务执行成功率 >= 99%) |
| **回滚方案** | `git revert <commit>` |
| **证据** | Worker 启动单测通过 |
| **风险** | 依赖: I2-1 (Redis Broker) / 数据: 任务结果需持久化, 防止丢失 / 兼容: 新增异步框架 / 回滚: git revert |
| **决策记录** | 决策: Celery + Redis Broker 异步任务框架 / 理由: Python 生态成熟方案, 支持任务重试和结果回写 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I2-2

### TASK-I2-3: Token Billing 最小闭环

| 字段 | 内容 |
|------|------|
| **目标** | LLM 调用 -> token 计量 -> usage_budgets 扣减 -> 预算耗尽拒绝，计费误差 = 0 |
| **范围 (In Scope)** | `src/infra/billing/`, `tests/unit/infra/test_billing.py` |
| **范围外 (Out of Scope)** | LLM 调用实现 / Tool 计费逻辑 / 前端计费面板 / 支付系统集成 |
| **依赖** | TASK-I2-1 |
| **兼容策略** | 新增计费闭环 |
| **验收命令** | [ENV-DEP] `pytest tests/unit/infra/test_billing.py -v` (计费误差 = 0) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 计费链路单测通过 |
| **风险** | 依赖: I2-1 (Redis) / 数据: 计费数据精度要求高, 误差=0 为硬指标 / 兼容: 新增计费闭环 / 回滚: git revert |
| **决策记录** | 决策: Token 计量 + usage_budgets 预算管控最小闭环 / 理由: 预算耗尽即拒绝, 防止成本失控 / 来源: ADR-047, 架构文档 06 Section 1.5 |

> 矩阵条目: I2-3 | V-x: X2-4 | V-fb: XF4-1

### TASK-I2-4: conversation_events 表

| 字段 | 内容 |
|------|------|
| **目标** | 表存在且含 content_schema_version 列 (v3.6) |
| **范围 (In Scope)** | `alembic/versions/xxx_conversation_events.py` |
| **范围外 (Out of Scope)** | 业务层对话逻辑 / Memory Core 内部存储 / 前端对话 UI / Brain 调度 |
| **依赖** | TASK-I0-3 |
| **兼容策略** | 纯新增 DDL |
| **验收命令** | [ENV-DEP] `alembic upgrade head && psql -c "\\d conversation_events"` |
| **回滚方案** | `alembic downgrade -1` |
| **证据** | 表存在 + 列齐全 |
| **风险** | 依赖: I0-3 (Alembic 骨架) / 数据: content_schema_version 列为多模态基座, Schema 需稳定 / 兼容: 纯新增 DDL / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: conversation_events 含 content_schema_version 列 / 理由: 多模态内容版本化, 支持 Schema 演进 (M-Track MM0-5) / 来源: 架构文档 08 附录 DDL |

> 矩阵条目: I2-4 | M-Track: MM0-5 (content_schema_version 列为 M-Track 多模态基座)

### TASK-I2-5: memory_items 表 (含 embedding + last_validated_at)

| 字段 | 内容 |
|------|------|
| **目标** | 表存在且 pgvector 扩展启用 |
| **范围 (In Scope)** | `alembic/versions/xxx_memory_items.py` |
| **范围外 (Out of Scope)** | Memory Core 业务逻辑 / Qdrant 向量存储 / 前端记忆展示 / Brain 检索逻辑 |
| **依赖** | pgvector |
| **兼容策略** | 纯新增 DDL + 扩展 |
| **验收命令** | [ENV-DEP] `psql -c "SELECT * FROM pg_extension WHERE extname='vector'"` |
| **回滚方案** | `alembic downgrade -1` |
| **证据** | pgvector 可用 |
| **风险** | 依赖: pgvector 扩展需 PG 容器预装 / 数据: embedding 列维度需与模型输出对齐 / 兼容: 纯新增 DDL / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: memory_items 含 embedding + last_validated_at 列 / 理由: PG 内向量检索支持 Memory Core 近线查询 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I2-5

---

## Phase 3 -- 全栈依赖

### TASK-I3-1: Neo4j 连接 + 基础 CRUD adapter

| 字段 | 内容 |
|------|------|
| **目标** | 写入节点 -> 查询 -> 删除，CRUD 全操作通过 |
| **范围 (In Scope)** | `src/infra/graph/neo4j_adapter.py`, `tests/unit/infra/test_neo4j.py` |
| **范围外 (Out of Scope)** | Knowledge 图谱业务逻辑 / StylingRule 数据模型 / 前端图谱可视化 / Brain 检索逻辑 |
| **依赖** | Neo4j 5.x (docker-compose) |
| **兼容策略** | 新增 adapter |
| **验收命令** | [ENV-DEP] `pytest tests/unit/infra/test_neo4j.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 连接池单测通过 |
| **风险** | 依赖: Neo4j 5.x (Docker Compose) / 数据: 连接池需正确管理, 防止泄漏 / 兼容: 新增 adapter / 回滚: git revert |
| **决策记录** | 决策: Neo4j Adapter 封装 CRUD + 连接池管理 / 理由: Knowledge 图谱存储基座, 品类/搭配关系天然图结构 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I3-1 | V-x: X3-2

### TASK-I3-2: Qdrant 连接 + 基础 CRUD adapter

| 字段 | 内容 |
|------|------|
| **目标** | 写入向量 -> 相似度查询 -> 返回结果 |
| **范围 (In Scope)** | `src/infra/vector/qdrant_adapter.py`, `tests/unit/infra/test_qdrant.py` |
| **范围外 (Out of Scope)** | Knowledge 向量检索业务逻辑 / Embedding 模型选择 / 前端搜索 UI / Memory Core 检索 |
| **依赖** | Qdrant 1.x (docker-compose) |
| **兼容策略** | 新增 adapter |
| **验收命令** | [ENV-DEP] `pytest tests/unit/infra/test_qdrant.py -v` (查询结果非空) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 连接池单测通过 |
| **风险** | 依赖: Qdrant 1.x (Docker Compose) / 数据: 向量维度需与 Embedding 模型对齐 / 兼容: 新增 adapter / 回滚: git revert |
| **决策记录** | 决策: Qdrant Adapter 封装向量 CRUD + 相似度查询 / 理由: Knowledge 向量检索基座, 专用向量数据库性能优于 PG pgvector / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I3-2 | V-x: X3-2

### TASK-I3-3: ObjectStoragePort 实现 (S3/MinIO) [M-Track M0]

| 字段 | 内容 |
|------|------|
| **目标** | generate_upload_url -> upload -> generate_download_url -> download，5 方法全通过 |
| **范围 (In Scope)** | `src/infra/storage/s3_adapter.py`, `tests/unit/infra/test_storage.py` |
| **范围外 (Out of Scope)** | Gateway 上传 API / 安全扫描流水线 / 前端上传组件 / Knowledge 媒体索引 |
| **依赖** | MinIO (docker-compose) |
| **兼容策略** | 新增 adapter |
| **验收命令** | [ENV-DEP] `pytest tests/unit/infra/test_storage.py -v` (5 方法全通过) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 5 方法契约测试通过 |
| **风险** | 依赖: MinIO (Docker Compose) / 数据: presigned_url 禁止持久化 (LAW 约束), 外部接口禁止暴露 ObjectRef / 兼容: 新增 adapter / 回滚: git revert |
| **决策记录** | 决策: ObjectStoragePort + S3/MinIO Adapter 实现 5 方法契约 / 理由: Port/Adapter 模式解耦存储实现, 支持 S3/MinIO 切换 / 来源: ADR-045, 架构文档 06 Section 2 |

> 矩阵条目: I3-3 | V-fb: XF2-3 | M-Track: MM0-2

### TASK-I3-4: tool_usage_records DDL (v3.6) [M-Track M0]

| 字段 | 内容 |
|------|------|
| **目标** | 表存在，DDL 对齐架构文档 |
| **范围 (In Scope)** | `alembic/versions/xxx_tool_usage.py` |
| **范围外 (Out of Scope)** | Tool 层业务逻辑 / 计费扣减逻辑 / 前端用量展示 / Brain 调度 |
| **依赖** | TASK-I0-3 |
| **兼容策略** | 纯新增 DDL |
| **验收命令** | [ENV-DEP] `alembic upgrade head && psql -c "\\d tool_usage_records"` |
| **回滚方案** | `alembic downgrade -1` |
| **证据** | 表存在 |
| **风险** | 依赖: I0-3 (Alembic 骨架) / 数据: DDL 需对齐架构文档, Schema 变更需迁移 / 兼容: 纯新增 DDL / 回滚: alembic downgrade -1 |
| **决策记录** | 决策: tool_usage_records 表记录 Tool 调用明细 / 理由: Tool 计费和审计追踪基座 (M-Track MM0-4) / 来源: ADR-047, 架构文档 08 附录 DDL |

> 矩阵条目: I3-4 | M-Track: MM0-4

---

## Phase 4 -- 可靠性

### TASK-I4-1: Prometheus + Grafana 监控栈

| 字段 | 内容 |
|------|------|
| **目标** | Grafana 看板展示 4 黄金信号 |
| **范围 (In Scope)** | `deploy/monitoring/`, Grafana dashboard JSON |
| **范围外 (Out of Scope)** | 业务层指标定义 / 前端用户面板 / SLI/SLO 配置 / 告警规则 |
| **依赖** | -- |
| **兼容策略** | 纯新增监控栈 |
| **验收命令** | [ENV-DEP] `curl localhost:3000/api/health` (Grafana healthy) |
| **回滚方案** | `docker-compose -f deploy/monitoring/docker-compose.yml down` |
| **证据** | 4 黄金信号看板截图 |
| **风险** | 依赖: Docker 运行时 / 数据: 监控数据非业务数据, 丢失可重建 / 兼容: 纯新增监控栈 / 回滚: docker-compose down |
| **决策记录** | 决策: Prometheus + Grafana 监控栈展示 4 黄金信号 / 理由: 云原生标准监控方案, 支持自定义看板 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I4-1 | V-x: X4-1 | V-fb: XF4-2

### TASK-I4-2: PG failover 实际演练

| 字段 | 内容 |
|------|------|
| **目标** | 主库故障 -> 自动切换 -> 应用恢复，切换时间 < 30s |
| **范围 (In Scope)** | `scripts/failover_drill.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 备份恢复流程 / 监控告警配置 |
| **依赖** | -- |
| **兼容策略** | 纯运维脚本 |
| **验收命令** | [ENV-DEP] `make failover-drill` (切换时间 < 30s) |
| **回滚方案** | 手动恢复主库 |
| **证据** | failover 脚本可用 |
| **风险** | 依赖: PG 主从架构 / 数据: failover 期间可能丢失未同步 WAL / 兼容: 纯运维脚本 / 回滚: 手动恢复主库 |
| **决策记录** | 决策: PG failover 自动切换 < 30s / 理由: 高可用要求, 减少服务中断时间 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I4-2 | V-x: X4-2

### TASK-I4-3: 备份恢复演练 (PG 全量 + WAL/PITR)

| 字段 | 内容 |
|------|------|
| **目标** | 备份 -> 模拟灾难 -> 恢复 -> 数据完整 |
| **范围 (In Scope)** | `scripts/backup.sh`, `scripts/restore.sh` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / failover 流程 / 监控告警 |
| **依赖** | -- |
| **兼容策略** | 纯运维脚本 |
| **验收命令** | [ENV-DEP] `make dr-drill` (数据完整率 = 100%) |
| **回滚方案** | 脚本级回退 |
| **证据** | 恢复数据校验通过 |
| **风险** | 依赖: PG WAL 归档配置 / 数据: RPO 取决于 WAL 归档频率, 需定期验证 / 兼容: 纯运维脚本 / 回滚: 脚本级回退 |
| **决策记录** | 决策: PG 全量备份 + WAL/PITR 恢复演练 / 理由: 灾难恢复能力验证, 数据完整率 100% 为硬指标 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I4-3 | V-x: X4-2

### TASK-I4-4: 故障注入测试 (删除管线每步注入失败)

| 字段 | 内容 |
|------|------|
| **目标** | 8 步注入测试全部可恢复 |
| **范围 (In Scope)** | `tests/chaos/test_deletion_fault.py` |
| **范围外 (Out of Scope)** | 业务层逻辑 / 前端实现 / 监控告警 / 删除管线业务实现 |
| **依赖** | MC4-1, OS4-5 |
| **兼容策略** | 纯测试 |
| **验收命令** | [ENV-DEP] `pytest tests/chaos/test_deletion_fault.py -v` (8 步全部可恢复) |
| **回滚方案** | 不适用 |
| **证据** | 8 步注入测试通过 |
| **风险** | 依赖: MC4-1 + OS4-5 双依赖 / 数据: 故障注入需隔离环境, 防止影响正常数据 / 兼容: 纯测试 / 回滚: 不适用 (测试环境) |
| **决策记录** | 决策: 删除管线每步注入失败验证可恢复性 / 理由: 删除管线不可逆操作必须排在最后 (LAW 约束), 每步失败需可恢复 / 来源: 架构文档 06 Section 1.6 |

> 矩阵条目: I4-4 | V-x: X4-4

### TASK-I4-5: PIPL/GDPR 删除管线完整实现

| 字段 | 内容 |
|------|------|
| **目标** | tombstone -> 物理删除 -> 审计保留，SLA 内完成删除 |
| **范围 (In Scope)** | `src/infra/compliance/deletion.py`, `tests/unit/infra/test_compliance_deletion.py` |
| **范围外 (Out of Scope)** | 业务层数据管理 / 前端删除 UI / 故障注入测试 / 监控告警 |
| **依赖** | OS5-5 |
| **兼容策略** | 新增合规删除流程 |
| **验收命令** | [ENV-DEP] `pytest tests/unit/infra/test_compliance_deletion.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 合规流程单测通过 |
| **风险** | 依赖: OS5-5 (合规框架) / 数据: 删除操作不可逆, tombstone 禁止引用 (LAW 约束) / 兼容: 新增合规删除流程 / 回滚: git revert |
| **决策记录** | 决策: PIPL/GDPR 三阶段删除管线 (tombstone -> 物理删除 -> 审计保留) / 理由: 合规删除需可审计, SLA 内完成 / 来源: 架构文档 06 Section 1.6 |

> 矩阵条目: I4-5 | V-x: X4-4 | V-fb: XF4-3

---

## Phase 5 -- 自动化

### TASK-I5-1: Event Mesh 演进 (PG Outbox -> NATS/Kafka)

| 字段 | 内容 |
|------|------|
| **目标** | 事件投递延迟 P99 < 100ms |
| **范围 (In Scope)** | `src/infra/events/mesh.py`, 性能测试 |
| **范围外 (Out of Scope)** | 业务层事件消费逻辑 / 前端实现 / Schema Registry / 监控告警 |
| **依赖** | TASK-I1-6 |
| **兼容策略** | 向后兼容 -- 可配置回退为 PG Outbox |
| **验收命令** | [ENV-DEP] `pytest tests/isolation/perf/test_event_latency.py -v --benchmark-min-rounds=100` staging: 投递延迟 P99 < 100ms |
| **回滚方案** | 配置切回 PG Outbox |
| **证据** | 投递延迟指标 |
| **风险** | 依赖: I1-6 (Outbox Pattern) / 数据: 事件顺序保证需验证, 消息丢失=业务不一致 / 兼容: 向后兼容, 可配置回退 PG Outbox / 回滚: 配置切回 PG Outbox |
| **决策记录** | 决策: Event Mesh 从 PG Outbox 演进到 NATS/Kafka / 理由: P99 < 100ms 性能要求, PG Outbox 无法满足大规模事件投递 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I5-1

### TASK-I5-2: Schema Registry

| 字段 | 内容 |
|------|------|
| **目标** | schema 兼容性检查通过 |
| **范围 (In Scope)** | `src/infra/schema/registry.py`, `tests/unit/infra/test_schema_registry.py` |
| **范围外 (Out of Scope)** | 业务层 Schema 定义 / 前端实现 / Event Mesh / 消息队列 |
| **依赖** | -- |
| **兼容策略** | 新增注册中心 |
| **验收命令** | [ENV-DEP] `pytest tests/unit/infra/test_schema_registry.py -v` |
| **回滚方案** | `git revert <commit>` |
| **证据** | 兼容性检查单测通过 |
| **风险** | 依赖: N/A / 数据: Schema 兼容性规则需严格定义, 不兼容变更=破坏消费者 / 兼容: 新增注册中心 / 回滚: git revert |
| **决策记录** | 决策: Schema Registry 统一事件 Schema 兼容性管理 / 理由: Schema 演进需向后兼容检查, 防止消费者破坏 / 来源: 架构文档 06 Section 2 |

> 矩阵条目: I5-2 | V-x: X5-2

---

> **维护规则:** 里程碑矩阵条目变更时同步更新对应任务卡。
